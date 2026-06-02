# Copyright (c) 2026, AssetCore Team
"""IMM-12 — Incident & CAPA orchestration service.

State machine Incident (khớp imm_12_incident_workflow.json + _VALID_TRANSITIONS):
  Open → Acknowledged → In Progress → Resolved → Closed
                                     ↘ (auto when High/Critical)
                                      RCA Required → [RCA flow] → Closed
  Open / Acknowledged / In Progress → Cancelled (false alarm)

  D3: "Tiếp nhận" (acknowledge: Open→Acknowledged) tách khỏi "Bắt đầu xử lý"
  (start_work: Acknowledged→In Progress). Triage/phân công ≠ bắt đầu xử lý.

State machine RCA:
  RCA Required → RCA In Progress → Completed (→ auto CAPA)
               ↘ Cancelled

Business Rules:
  BR-12-01  Critical → clinical_impact bắt buộc
  BR-12-02  Major/Critical Closed → rca phải Completed
  BR-12-03  ≥3 incidents/fault_code/90 ngày → auto tạo RCA Chronic
  BR-12-04  Critical → auto asset Out of Service
  BR-12-05  Mọi transition → IMM Audit Trail
  BR-12-06  RCA Submit → auto imm00.create_capa()
  BR-12-07  RCA root_cause + corrective_action bắt buộc trước Submit
"""
from __future__ import annotations

import frappe
from frappe.utils import add_days, now_datetime, nowdate, today

from assetcore.repositories.repair_repo import IncidentRepo, RCARepo
from assetcore.services import imm00 as svc00
from assetcore.utils.notify import nthrow, nthrow_in_hook
from assetcore.utils.messages import MSG

_DT_INCIDENT = "Incident Report"
_DT_RCA = "IMM RCA Record"
_DT_CAPA = "IMM CAPA Record"
_DT_ASSET = "AC Asset"

_STATUS_OPEN = "Open"
_STATUS_ACKNOWLEDGED = "Acknowledged"
_STATUS_INVESTIGATING = "In Progress"
_STATUS_RESOLVED = "Resolved"
_STATUS_CLOSED = "Closed"
_STATUS_CANCELLED = "Cancelled"

_RCA_REQUIRED = "RCA Required"
_RCA_IN_PROGRESS = "RCA In Progress"
_RCA_COMPLETED = "Completed"
_RCA_CANCELLED = "Cancelled"

_SEV_HIGH = "High"
_SEV_CRITICAL = "Critical"
_HIGH_SEVERITY = (_SEV_HIGH, _SEV_CRITICAL)

_ASSET_OUT_OF_SERVICE = "Out of Service"
_ASSET_ACTIVE = "Active"

# D3: khớp imm_12_incident_workflow.json — Open chỉ đi Acknowledged/Cancelled
# (KHÔNG nhảy thẳng In Progress). start_work() đưa Acknowledged → In Progress.
_VALID_TRANSITIONS: dict[str, list[str]] = {
    _STATUS_OPEN: [_STATUS_ACKNOWLEDGED, _STATUS_CANCELLED],
    _STATUS_ACKNOWLEDGED: [_STATUS_INVESTIGATING, _STATUS_CANCELLED],
    _STATUS_INVESTIGATING: [_STATUS_RESOLVED, _STATUS_CANCELLED, _RCA_REQUIRED],
    _STATUS_RESOLVED: [_STATUS_CLOSED, _RCA_REQUIRED],
}

_CHRONIC_WINDOW_DAYS = 90
_CHRONIC_MIN_COUNT = 3
_RCA_DUE_MAJOR = 7
_RCA_DUE_CHRONIC = 14

_ORDER_REPORTED_AT = "reported_at desc"


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _get_incident(name: str) -> "frappe.Document":
    doc = IncidentRepo.get(name)
    if not doc:
        nthrow(MSG.IMM12_INCIDENT_NOT_FOUND, name=name)
    return doc


def _get_rca(name: str) -> "frappe.Document":
    doc = RCARepo.get(name)
    if not doc:
        nthrow(MSG.IMM12_RCA_NOT_FOUND, name=name)
    return doc


def _assert_transition(doc: "frappe.Document", to_status: str) -> None:
    allowed = _VALID_TRANSITIONS.get(doc.status, [])
    if to_status not in allowed:
        nthrow(MSG.IMM12_BAD_STATE, from_state=doc.status, to_state=to_status)


def _log(name: str, asset: str, summary: str, from_status: str, to_status: str) -> None:
    try:
        svc00.log_audit_event(
            asset=asset,
            event_type="Incident",
            actor=frappe.session.user,
            ref_doctype=_DT_INCIDENT,
            ref_name=name,
            change_summary=summary,
            from_status=from_status,
            to_status=to_status,
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMM-12 _log audit")


def _map_severity(severity: str) -> str:
    return {
        "Low": "Minor", "Medium": "Minor",
        "High": "Major", "Critical": "Critical",
    }.get(severity, "Minor")


# BR-12-08: IMM SLA Policy.priority dùng thang P1–P4; Incident dùng severity.
_SEVERITY_TO_SLA_PRIORITY = {
    "Critical": "P1", "High": "P2", "Medium": "P3", "Low": "P4",
}


def _severity_to_sla_priority(severity: str) -> str:
    return _SEVERITY_TO_SLA_PRIORITY.get(severity, "P4")


def _apply_sla_policy(doc) -> None:
    """BR-12-08: resolve IMM SLA Policy theo severity và set due-time trên doc.

    Đọc response/resolution time TỪ policy (không hardcode). Không có policy khớp
    → bỏ qua (không chặn report). Gọi TRƯỚC insert/save để due-time được lưu.
    """
    from frappe.utils import add_to_date

    priority = _severity_to_sla_priority(doc.severity)
    policy = svc00.get_sla_policy(priority)
    if not policy:
        return
    base = doc.reported_at or now_datetime()
    doc.sla_policy = policy.get("name")
    resp_min = policy.get("response_time_minutes")
    res_hr = policy.get("resolution_time_hours")
    if resp_min:
        doc.response_due_at = add_to_date(base, minutes=int(resp_min))
    if res_hr:
        doc.resolution_due_at = add_to_date(base, hours=int(res_hr))


def _needs_rca(severity: str) -> bool:
    return severity in _HIGH_SEVERITY


def _enrich_asset_names(rows: list) -> None:
    asset_ids = {r["asset"] for r in rows if r.get("asset")}
    if asset_ids:
        asset_map = {a.name: a.asset_name for a in frappe.get_all(
            _DT_ASSET, filters={"name": ["in", list(asset_ids)]}, fields=["name", "asset_name"],
        )}
        for r in rows:
            r["asset_name"] = asset_map.get(r.get("asset"), r.get("asset") or "")

    # Enrich user fields (Data Contract Wave 1: reporter_name, assigned_to_name)
    user_ids: set = set()
    for r in rows:
        if r.get("reported_by"):
            user_ids.add(r["reported_by"])
        if r.get("assigned_to"):
            user_ids.add(r["assigned_to"])
    if user_ids:
        user_map = {u.name: u.full_name for u in frappe.get_all(
            "User", filters={"name": ["in", list(user_ids)]},
            fields=["name", "full_name"],
        )}
        for r in rows:
            if r.get("reported_by"):
                r["reporter_name"] = user_map.get(r["reported_by"], r["reported_by"])
            if r.get("assigned_to"):
                r["assigned_to_name"] = user_map.get(r["assigned_to"], r["assigned_to"])


def _build_incident_filters(status: str, severity: str, asset: str) -> dict:
    f: dict = {}
    if status:
        f["status"] = status
    if severity:
        f["severity"] = severity
    if asset:
        f["asset"] = asset
    return f


# ─── Incident lifecycle ────────────────────────────────────────────────────────

def report_incident(
    asset: str,
    incident_type: str,
    severity: str,
    description: str,
    *,
    fault_code: str = "",
    workaround_applied: int = 0,
    clinical_impact: str = "",
    patient_affected: int = 0,
    patient_impact_description: str = "",
    immediate_action: str = "",
    linked_repair_wo: str = "",
    reported_by: str = "",
) -> dict:
    """Tạo Incident Report. BR-12-01: Critical → clinical_impact bắt buộc."""
    if severity == _SEV_CRITICAL and not clinical_impact.strip():
        nthrow(MSG.IMM12_CLINICAL_IMPACT_REQUIRED)
    if not frappe.db.exists(_DT_ASSET, asset):
        nthrow(MSG.IMM12_ASSET_NOT_FOUND, asset=asset)

    actor = reported_by or frappe.session.user
    doc = frappe.new_doc(_DT_INCIDENT)
    doc.asset = asset
    doc.incident_type = incident_type
    doc.severity = severity
    doc.description = description
    doc.reported_by = actor
    doc.reported_at = now_datetime()
    doc.status = _STATUS_OPEN
    if fault_code:
        doc.fault_code = fault_code
    doc.workaround_applied = workaround_applied
    if clinical_impact:
        doc.clinical_impact = clinical_impact
    doc.patient_affected = patient_affected
    if patient_impact_description:
        doc.patient_impact_description = patient_impact_description
    if immediate_action:
        doc.immediate_action = immediate_action
    if linked_repair_wo:
        doc.linked_repair_wo = linked_repair_wo
    doc.rca_required = 1 if _needs_rca(severity) else 0
    # BR-12-08: SLA due-times từ IMM SLA Policy (sau khi reported_at đã set).
    _apply_sla_policy(doc)
    doc.flags.ignore_permissions = True
    doc.insert()

    # BR-12-04: Critical → auto Out of Service
    if severity == _SEV_CRITICAL:
        _try_transition_asset(asset, _ASSET_OUT_OF_SERVICE, doc.name, actor)

    frappe.db.commit()
    _log(doc.name, asset, f"Incident reported — {severity} — {incident_type}", "", _STATUS_OPEN)
    return {"name": doc.name, "status": doc.status, "severity": severity}


def acknowledge_incident(name: str, notes: str = "", assigned_to: str = "") -> dict:
    """"Tiếp nhận": Open → Acknowledged. Triage + phân công.

    D3 fix: KHÔNG nhảy thẳng In Progress (đó là start_work()). BR-12-04 extended:
    High/Critical → auto Out of Service ngay khi tiếp nhận (thiết bị nguy hiểm
    không tiếp tục vận hành trong lúc chờ xử lý).
    """
    doc = _get_incident(name)
    _assert_transition(doc, _STATUS_ACKNOWLEDGED)

    actor = frappe.session.user
    prev = doc.status
    doc.status = _STATUS_ACKNOWLEDGED
    doc.acknowledged_by = actor
    doc.acknowledged_at = now_datetime()
    # BR-12-08: response SLA breach nếu tiếp nhận sau response_due_at.
    if doc.response_due_at and doc.acknowledged_at > frappe.utils.get_datetime(doc.response_due_at):
        doc.response_breached = 1
    if assigned_to:
        doc.assigned_to = assigned_to
    if notes:
        doc.immediate_action = ((doc.immediate_action or "") + f"\n[Ack] {notes}").strip()
    doc.flags.ignore_permissions = True
    doc.save()
    frappe.db.commit()
    _log(name, doc.asset, f"Tiếp nhận — {notes or 'đã phân công'}", prev, _STATUS_ACKNOWLEDGED)

    if doc.severity in _HIGH_SEVERITY:
        _try_transition_asset(doc.asset, _ASSET_OUT_OF_SERVICE, name, actor)

    return {"name": name, "status": doc.status}


def start_work(name: str, notes: str = "") -> dict:
    """"Bắt đầu xử lý": Acknowledged → In Progress.

    D3: KTV bắt đầu thực sự can thiệp thiết bị (tách khỏi triage ở acknowledge).
    """
    doc = _get_incident(name)
    _assert_transition(doc, _STATUS_INVESTIGATING)

    actor = frappe.session.user
    prev = doc.status
    doc.status = _STATUS_INVESTIGATING
    if not doc.assigned_to:
        doc.assigned_to = actor
    if notes:
        doc.immediate_action = ((doc.immediate_action or "") + f"\n[Start] {notes}").strip()
    doc.flags.ignore_permissions = True
    doc.save()
    frappe.db.commit()
    _log(name, doc.asset, f"Bắt đầu xử lý — {notes or 'đang xử lý'}", prev, _STATUS_INVESTIGATING)
    return {"name": name, "status": doc.status}


def resolve_incident(name: str, resolution_notes: str, root_cause: str = "") -> dict:
    """In Progress → Resolved. Auto-tạo RCA nếu High/Critical (không block)."""
    doc = _get_incident(name)
    _assert_transition(doc, _STATUS_RESOLVED)

    if not resolution_notes.strip():
        nthrow(MSG.IMM12_RESOLUTION_NOTES_REQUIRED)

    actor = frappe.session.user
    prev = doc.status
    doc.status = _STATUS_RESOLVED
    doc.resolved_by = actor
    doc.resolved_at = now_datetime()
    # BR-12-08: resolution SLA breach nếu xử lý xong sau resolution_due_at.
    if doc.resolution_due_at and doc.resolved_at > frappe.utils.get_datetime(doc.resolution_due_at):
        doc.resolution_breached = 1
    doc.resolution_notes = resolution_notes
    if root_cause:
        doc.root_cause_summary = root_cause
    doc.flags.ignore_permissions = True
    doc.save()
    frappe.db.commit()
    _log(name, doc.asset, f"Resolved — {resolution_notes[:120]}", prev, _STATUS_RESOLVED)

    # Auto-create RCA cho High/Critical nếu chưa có
    rca_name: str | None = None
    if _needs_rca(doc.severity) and not doc.rca_record:
        try:
            rca_name = _auto_create_rca(doc)
        except Exception:
            frappe.log_error(frappe.get_traceback(), "IMM-12 auto_rca on resolve")

    # Auto-CAPA cho High/Critical nếu không có RCA flow (fallback)
    if doc.severity in _HIGH_SEVERITY and not doc.linked_capa and not rca_name:
        _auto_create_capa(doc)

    return {"name": name, "status": doc.status, "rca_created": rca_name}


def close_incident(name: str, verification_notes: str = "") -> dict:
    """Resolved → Closed.
    BR-12-02: Major/Critical → phải có RCA Completed trước khi Close.
    """
    doc = _get_incident(name)
    _assert_transition(doc, _STATUS_CLOSED)

    # BR-12-02
    if _needs_rca(doc.severity) and doc.rca_required:
        rca_name = frappe.db.get_value(_DT_INCIDENT, name, "rca_record")
        if rca_name:
            rca_status = frappe.db.get_value(_DT_RCA, rca_name, "status")
            if rca_status != _RCA_COMPLETED:
                nthrow(MSG.IMM12_CLOSE_RCA_INCOMPLETE,
                       severity=doc.severity, rca=rca_name)
        else:
            nthrow(MSG.IMM12_CLOSE_RCA_REQUIRED, severity=doc.severity)

    actor = frappe.session.user
    prev = doc.status
    doc.status = _STATUS_CLOSED
    doc.closed_by = actor
    doc.closed_date = today()
    if verification_notes:
        doc.resolution_notes = ((doc.resolution_notes or "") + f"\n[Closed] {verification_notes}").strip()
    doc.flags.ignore_permissions = True
    doc.save()
    frappe.db.commit()
    _log(name, doc.asset, f"Closed — {verification_notes or 'verified'}", prev, _STATUS_CLOSED)

    # Khôi phục asset về Active nếu đang Out of Service do incident này
    if doc.asset:
        cur = frappe.db.get_value(_DT_ASSET, doc.asset, "lifecycle_status") or ""
        if cur == _ASSET_OUT_OF_SERVICE:
            _try_transition_asset(doc.asset, _ASSET_ACTIVE, name, actor)

    return {"name": name, "status": doc.status, "closed_date": doc.closed_date}


def cancel_incident(name: str, reason: str) -> dict:
    """Open / Acknowledged / In Progress → Cancelled (false alarm)."""
    doc = _get_incident(name)
    _assert_transition(doc, _STATUS_CANCELLED)
    if not reason.strip():
        nthrow(MSG.IMM12_CANCEL_REASON_REQUIRED)

    prev = doc.status
    doc.status = _STATUS_CANCELLED
    doc.resolution_notes = ((doc.resolution_notes or "") + f"\n[Cancelled] {reason}").strip()
    doc.flags.ignore_permissions = True
    doc.save()
    frappe.db.commit()
    _log(name, doc.asset, f"Cancelled — {reason[:120]}", prev, _STATUS_CANCELLED)
    return {"name": name, "status": doc.status}


# ─── RCA orchestration ────────────────────────────────────────────────────────

def create_rca(incident_name: str, rca_method: str = "5-Why") -> dict:
    """Tạo RCA Record liên kết Incident. Idempotent — raise 409 nếu đã có."""
    doc = _get_incident(incident_name)
    if doc.rca_record and frappe.db.exists(_DT_RCA, doc.rca_record):
        nthrow(MSG.IMM12_RCA_ALREADY_EXISTS, rca=doc.rca_record)

    trigger = "Critical Incident" if doc.severity == _SEV_CRITICAL else "Major Incident"
    due_days = _RCA_DUE_MAJOR

    rca = frappe.new_doc(_DT_RCA)
    rca.incident_report = incident_name
    rca.asset = doc.asset
    rca.rca_method = rca_method or "5-Why"
    rca.trigger_type = trigger
    rca.status = _RCA_REQUIRED
    rca.assigned_to = frappe.session.user
    rca.due_date = add_days(nowdate(), due_days)
    for i in range(1, 6):
        rca.append("five_why_steps", {"why_number": i, "why_question": f"Why {i}?", "why_answer": ""})
    rca.flags.ignore_permissions = True
    rca.insert()

    frappe.db.set_value(_DT_INCIDENT, incident_name, {
        "rca_record": rca.name,
        "rca_required": 1,
    })
    frappe.db.commit()
    return {"name": rca.name, "status": rca.status, "due_date": str(rca.due_date)}


def get_rca(name: str) -> dict:
    doc = _get_rca(name)
    data = doc.as_dict()
    if doc.incident_report:
        data["incident_severity"] = frappe.db.get_value(
            _DT_INCIDENT, doc.incident_report, "severity")
    return data


def list_rcas(
    method: str = "",
    status: str = "",
    asset: str = "",
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """Danh sách RCA Record cho RCAListView (route /rca). Read-safe, enrich names."""
    f: dict = {}
    if method:
        f["rca_method"] = method
    if status:
        f["status"] = status
    if asset:
        f["asset"] = asset
    total = frappe.db.count(_DT_RCA, filters=f)
    offset = (page - 1) * page_size
    rows = frappe.get_all(
        _DT_RCA,
        filters=f,
        fields=["name", "incident_report", "asset", "rca_method", "trigger_type",
                "status", "assigned_to", "due_date", "linked_capa", "completed_date"],
        order_by="creation desc",
        limit_start=offset,
        limit_page_length=page_size,
    )
    _enrich_asset_names(rows)
    # Enrich owner (assigned_to) display name
    user_ids = {r["assigned_to"] for r in rows if r.get("assigned_to")}
    if user_ids:
        user_map = {u.name: u.full_name for u in frappe.get_all(
            "User", filters={"name": ["in", list(user_ids)]}, fields=["name", "full_name"],
        )}
        for r in rows:
            if r.get("assigned_to"):
                r["assigned_to_name"] = user_map.get(r["assigned_to"], r["assigned_to"])
    return {
        "pagination": {
            "total": total, "page": page, "page_size": page_size,
            "total_pages": max(1, -(-total // page_size)), "offset": offset,
        },
        "items": rows,
    }


def submit_rca(
    name: str,
    root_cause: str,
    corrective_action: str,
    preventive_action: str = "",
    five_why_steps: list | None = None,
    rca_notes: str = "",
) -> dict:
    """Hoàn thành RCA → auto tạo CAPA. BR-12-07."""
    rca = _get_rca(name)
    if rca.status == _RCA_COMPLETED:
        nthrow(MSG.IMM12_RCA_ALREADY_COMPLETED)
    if not root_cause.strip():
        nthrow(MSG.IMM12_RCA_ROOT_CAUSE_REQUIRED)
    if not corrective_action.strip():
        nthrow(MSG.IMM12_RCA_CORRECTIVE_REQUIRED)

    actor = frappe.session.user
    rca.status = _RCA_COMPLETED
    rca.root_cause = root_cause
    rca.corrective_action_summary = corrective_action
    rca.preventive_action_summary = preventive_action or rca.preventive_action_summary
    rca.rca_notes = rca_notes or rca.rca_notes
    rca.completed_by = actor
    rca.completed_date = today()
    if five_why_steps:
        rca.set("five_why_steps", [])
        for step in five_why_steps:
            rca.append("five_why_steps", step)
    rca.flags.ignore_permissions = True
    rca.save()

    # BR-12-06: auto CAPA via IMM-16 canonical helper (RC-03 fix)
    capa_name: str | None = None
    if rca.incident_report:
        try:
            from assetcore.services.imm16 import create_capa_from_incident
            result = create_capa_from_incident(
                incident_name=rca.incident_report,
                rca_name=rca.name,
                responsible=actor,
            )
            capa_name = result.get("capa_name")
            # Refresh in-memory rca.linked_capa nếu vừa set qua db
            if capa_name and not rca.linked_capa:
                rca.linked_capa = capa_name
        except Exception:
            frappe.log_error(frappe.get_traceback(), "IMM-12 submit_rca auto_capa")

    frappe.db.commit()
    _log(name, rca.asset or "", f"RCA Completed — {root_cause[:80]}", _RCA_IN_PROGRESS, _RCA_COMPLETED)

    # RC-04: push incident workflow forward sau khi RCA hoàn tất
    if rca.incident_report:
        _advance_incident_after_rca(rca.incident_report)

    return {"name": rca.name, "status": rca.status, "linked_capa": capa_name}


# ─── Queries ──────────────────────────────────────────────────────────────────

def list_incidents(
    status: str = "",
    severity: str = "",
    asset: str = "",
    page: int = 1,
    page_size: int = 20,
) -> dict:
    filters = _build_incident_filters(status, severity, asset)
    total = frappe.db.count(_DT_INCIDENT, filters=filters)
    offset = (page - 1) * page_size
    rows = frappe.get_all(
        _DT_INCIDENT,
        filters=filters,
        fields=["name", "asset", "incident_type", "severity", "status", "fault_code",
                "reported_by", "reported_at", "description", "linked_capa", "linked_repair_wo",
                "rca_required", "rca_record", "chronic_failure_flag", "patient_affected",
                "closed_date", "assigned_to", "acknowledged_at", "resolved_at"],
        order_by=_ORDER_REPORTED_AT,
        limit_start=offset,
        limit_page_length=page_size,
    )
    _enrich_asset_names(rows)
    return {
        "pagination": {
            "total": total, "page": page, "page_size": page_size,
            "total_pages": max(1, -(-total // page_size)), "offset": offset,
        },
        "items": rows,
    }


def get_incident_detail(name: str) -> dict:
    doc = _get_incident(name)
    data = doc.as_dict()
    if doc.asset:
        data["asset_name"] = frappe.db.get_value(_DT_ASSET, doc.asset, "asset_name")
    data["allowed_transitions"] = _VALID_TRANSITIONS.get(doc.status, [])
    if doc.rca_record:
        rca = RCARepo.get(doc.rca_record)
        if rca:
            data["rca"] = {
                "name": rca.name,
                "status": rca.status,
                "root_cause": rca.root_cause,
                "due_date": str(rca.due_date) if rca.due_date else None,
                "trigger_type": rca.trigger_type,
            }
    return data


def get_incident_stats() -> dict:
    def _count(f: dict) -> int:
        try:
            return frappe.db.count(_DT_INCIDENT, filters=f)
        except Exception:
            return 0

    return {
        "total": _count({}),
        "open": _count({"status": _STATUS_OPEN}),
        "investigating": _count({"status": _STATUS_INVESTIGATING}),
        "resolved": _count({"status": _STATUS_RESOLVED}),
        "closed": _count({"status": _STATUS_CLOSED}),
        "cancelled": _count({"status": _STATUS_CANCELLED}),
        "critical": _count({"severity": _SEV_CRITICAL}),
        "high": _count({"severity": _SEV_HIGH}),
        "rca_pending": _count({"rca_required": 1, "rca_record": ("is", "not set")}),
        "chronic": _count({"chronic_failure_flag": 1}),
    }


def get_asset_incident_history(asset: str, limit: int = 10) -> dict:
    rows = frappe.get_all(
        _DT_INCIDENT,
        filters={"asset": asset},
        fields=["name", "incident_type", "severity", "status", "reported_at",
                "fault_code", "closed_date", "linked_capa", "rca_record"],
        order_by=_ORDER_REPORTED_AT,
        limit_page_length=limit,
    )
    return {"asset": asset, "items": rows}


def get_chronic_failures() -> list:
    """Asset có ≥3 sự cố cùng fault_code trong 90 ngày."""
    cutoff = add_days(nowdate(), -_CHRONIC_WINDOW_DAYS)
    return frappe.db.sql("""
        SELECT asset, fault_code, COUNT(*) AS count, MAX(reported_at) AS last_reported
        FROM `tabIncident Report`
        WHERE fault_code IS NOT NULL AND fault_code != ''
          AND reported_at >= %s
          AND status != 'Cancelled'
        GROUP BY asset, fault_code
        HAVING count >= %s
        ORDER BY count DESC
    """, (cutoff, _CHRONIC_MIN_COUNT), as_dict=True)


def get_dashboard() -> dict:
    stats = get_incident_stats()
    recent = frappe.get_all(
        _DT_INCIDENT,
        filters={"status": ["in", [_STATUS_OPEN, _STATUS_INVESTIGATING]]},
        fields=["name", "asset", "severity", "status", "reported_at", "fault_code"],
        order_by=_ORDER_REPORTED_AT,
        limit_page_length=10,
    )
    _enrich_asset_names(recent)
    rca_open = frappe.get_all(
        _DT_RCA,
        filters={"status": ["in", [_RCA_REQUIRED, _RCA_IN_PROGRESS]]},
        fields=["name", "incident_report", "asset", "status", "trigger_type", "due_date"],
        order_by="due_date asc",
        limit_page_length=10,
    )
    chronic = get_chronic_failures()[:5]
    return {
        "stats": stats,
        "active_incidents": recent,
        "open_rcas": rca_open,
        "chronic_failures": chronic,
    }


# ─── Scheduler ────────────────────────────────────────────────────────────────

def detect_chronic_failures() -> dict:
    """Daily scheduler — BR-12-03: flag mãn tính + tạo RCA tự động."""
    chronic_groups = get_chronic_failures()
    flagged = 0
    rca_created = 0
    for row in chronic_groups:
        n_flagged, created = _process_chronic_group(row["asset"], row["fault_code"])
        flagged += n_flagged
        rca_created += created
    if flagged or rca_created:
        frappe.db.commit()
    frappe.logger().info(
        f"IMM-12 detect_chronic_failures: {flagged} flagged, {rca_created} RCA created"
    )
    return {"flagged": flagged, "rca_created": rca_created, "groups": len(chronic_groups)}


def check_incident_sla_breach() -> dict:
    """Hourly scheduler — BR-12-08: đánh dấu SLA breach cho incident CHƯA đóng
    đã quá hạn (response/resolution) + ghi audit-trail (BR-12-05).

    Idempotent: chỉ set breach=1 cho incident chưa breach (tránh log trùng).
    """
    now = now_datetime()
    open_states = (_STATUS_OPEN, _STATUS_ACKNOWLEDGED, _STATUS_INVESTIGATING, _RCA_REQUIRED)
    candidates = frappe.get_all(
        _DT_INCIDENT,
        filters={"status": ["in", open_states]},
        fields=["name", "asset", "status", "response_due_at", "resolution_due_at",
                "response_breached", "resolution_breached", "acknowledged_at"],
    )
    resp_flagged = 0
    res_flagged = 0
    for row in candidates:
        updates: dict = {}
        # Response breach: chưa tiếp nhận và đã quá response_due_at.
        if (not row.get("response_breached") and not row.get("acknowledged_at")
                and row.get("response_due_at")
                and now > frappe.utils.get_datetime(row["response_due_at"])):
            updates["response_breached"] = 1
            resp_flagged += 1
        # Resolution breach: chưa đóng và đã quá resolution_due_at.
        if (not row.get("resolution_breached") and row.get("resolution_due_at")
                and now > frappe.utils.get_datetime(row["resolution_due_at"])):
            updates["resolution_breached"] = 1
            res_flagged += 1
        if updates:
            frappe.db.set_value(_DT_INCIDENT, row["name"], updates, update_modified=False)
            kinds = "+".join(k.replace("_breached", "") for k in updates)
            _log(row["name"], row.get("asset"), f"SLA breach ({kinds}) phát hiện bởi scheduler",
                 row["status"], row["status"])
    if resp_flagged or res_flagged:
        frappe.db.commit()
    frappe.logger().info(
        f"IMM-12 check_incident_sla_breach: response={resp_flagged}, resolution={res_flagged}"
    )
    return {"response_breached": resp_flagged, "resolution_breached": res_flagged}


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _process_chronic_group(asset: str, fault_code: str) -> tuple[int, int]:
    """Flag incidents + create chronic RCA for one (asset, fault_code) group."""
    cutoff = add_days(nowdate(), -_CHRONIC_WINDOW_DAYS)
    ir_list = frappe.get_all(
        _DT_INCIDENT,
        filters={
            "asset": asset, "fault_code": fault_code,
            "status": ["!=", _STATUS_CANCELLED],
            "reported_at": [">=", cutoff],
        },
        fields=["name", "chronic_failure_flag"],
    )
    flagged = 0
    for ir in ir_list:
        if not ir.get("chronic_failure_flag"):
            frappe.db.set_value(_DT_INCIDENT, ir["name"], {"chronic_failure_flag": 1, "rca_required": 1})
            flagged += 1
    existing_rca = frappe.db.exists(_DT_RCA, {
        "asset": asset, "trigger_type": "Chronic Failure",
        "status": ["in", [_RCA_REQUIRED, _RCA_IN_PROGRESS]],
    })
    if existing_rca:
        return flagged, 0
    try:
        rca = frappe.new_doc(_DT_RCA)
        rca.asset = asset
        rca.trigger_type = "Chronic Failure"
        rca.rca_method = "5-Why"
        rca.status = _RCA_REQUIRED
        rca.due_date = add_days(nowdate(), _RCA_DUE_CHRONIC)
        rca.incident_count = len(ir_list)
        for ir_item in ir_list:
            rca.append("related_incidents", {"incident_report": ir_item["name"]})
        for i in range(1, 6):
            rca.append("five_why_steps", {"why_number": i, "why_question": f"Why {i}?", "why_answer": ""})
        rca.flags.ignore_permissions = True
        rca.insert()
        if ir_list:
            frappe.db.set_value(_DT_INCIDENT, ir_list[0]["name"], "rca_record", rca.name)
        if frappe.db.has_column(_DT_ASSET, "chronic_failure_flag"):
            frappe.db.set_value(_DT_ASSET, asset, "chronic_failure_flag", 1)
        svc00.log_audit_event(
            asset=asset, event_type="chronic_failure_detected", actor="Administrator",
            ref_doctype=_DT_RCA, ref_name=rca.name,
            change_summary=f"{len(ir_list)} incidents same fault_code '{fault_code}' in 90 days",
        )
        return flagged, 1
    except Exception:
        frappe.log_error(frappe.get_traceback(), f"IMM-12 chronic RCA create {asset}/{fault_code}")
        return flagged, 0

def _auto_create_rca(doc: "frappe.Document") -> str:
    """Auto-tạo RCA sau resolve cho High/Critical."""
    trigger = "Critical Incident" if doc.severity == _SEV_CRITICAL else "Major Incident"
    rca = frappe.new_doc(_DT_RCA)
    rca.incident_report = doc.name
    rca.asset = doc.asset
    rca.rca_method = "5-Why"
    rca.trigger_type = trigger
    rca.status = _RCA_REQUIRED
    rca.assigned_to = frappe.session.user
    rca.due_date = add_days(nowdate(), _RCA_DUE_MAJOR)
    for i in range(1, 6):
        rca.append("five_why_steps", {"why_number": i, "why_question": f"Why {i}?", "why_answer": ""})
    rca.flags.ignore_permissions = True
    rca.insert()
    frappe.db.set_value(_DT_INCIDENT, doc.name, {
        "rca_record": rca.name,
        "rca_required": 1,
    })
    frappe.db.commit()
    return rca.name


def _auto_create_capa(doc: "frappe.Document") -> None:
    try:
        capa_name = svc00.create_capa(
            asset=doc.asset,
            source_type=_DT_INCIDENT,
            source_ref=doc.name,
            severity=_map_severity(doc.severity),
            description=f"Auto-CAPA từ Incident {doc.name}: {(doc.description or '')[:200]}",
            responsible=frappe.session.user,
        )
        frappe.db.set_value(_DT_INCIDENT, doc.name, "linked_capa", capa_name)
        frappe.db.commit()
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMM-12 _auto_create_capa")


# ─── RCA → Incident chain (RC-03 + RC-04) ─────────────────────────────────────

_WORKFLOW_NAME_INCIDENT = "IMM-12 Incident Workflow"
_ACTION_RCA_DONE_CLOSE = "RCA hoàn tất - đóng sự cố"


def on_rca_completed(incident_name: str, rca_name: str) -> dict:
    """Hook RCA Record on_submit → ensure CAPA + advance Incident workflow.

    Idempotent — re-uses existing linked_capa, skips workflow apply nếu state đã Closed.
    Wrap mọi side-effect trong try/except — KHÔNG fail RCA submit nếu chain lỗi.
    """
    out: dict = {"incident": incident_name, "rca": rca_name,
                 "capa_name": None, "workflow_advanced": False}
    if not incident_name or not frappe.db.exists(_DT_INCIDENT, incident_name):
        return out

    # 1. CAPA chain (RC-03)
    try:
        from assetcore.services.imm16 import create_capa_from_incident
        result = create_capa_from_incident(
            incident_name=incident_name,
            rca_name=rca_name or "",
            responsible=frappe.session.user,
        )
        out["capa_name"] = result.get("capa_name")
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMM-12 on_rca_completed CAPA chain")

    # 2. Incident workflow auto-advance (RC-04)
    try:
        out["workflow_advanced"] = _advance_incident_after_rca(incident_name)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMM-12 on_rca_completed workflow")

    return out


def _advance_incident_after_rca(incident_name: str) -> bool:
    """Đẩy Incident từ 'RCA Required' → 'Closed' qua action workflow chuẩn.

    Frappe Workflow KHÔNG cho phép gán workflow_state tùy ý — phải đi qua
    apply_workflow(action). Nếu incident không ở 'RCA Required' (đã closed
    rồi, hoặc workflow chưa tới đó), no-op an toàn.
    """
    from frappe.model.workflow import apply_workflow

    inc = frappe.get_doc(_DT_INCIDENT, incident_name)
    current_state = inc.get("workflow_state") or inc.get("status") or ""
    if current_state == _STATUS_CLOSED:
        return False  # đã đóng — không làm gì
    if current_state != "RCA Required":
        # Workflow chưa tới RCA Required (vd RCA tạo từ chronic, incident vẫn ở Resolved)
        # KHÔNG ép — log để observability.
        frappe.logger().info(
            f"IMM-12 _advance_incident_after_rca: incident {incident_name} "
            f"đang ở '{current_state}', skip apply_workflow"
        )
        return False

    try:
        apply_workflow(inc, _ACTION_RCA_DONE_CLOSE)
        # Workflow chỉ flip workflow_state field — sync status (Select) +
        # closed_by/closed_date để truy vấn list filter status="Closed" còn đúng.
        frappe.db.set_value(
            _DT_INCIDENT, incident_name,
            {
                "status": _STATUS_CLOSED,
                "closed_by": frappe.session.user,
                "closed_date": today(),
            },
            update_modified=False,
        )
        frappe.db.commit()
        _log(incident_name, inc.asset or "",
             "Auto-closed sau khi RCA hoàn tất",
             "RCA Required", _STATUS_CLOSED)
        return True
    except Exception as e:
        # Có thể fail vì permission (RCA submitter không có System Manager).
        # Thử fallback bằng cách close trực tiếp qua service close_incident()
        # với ignore_permissions — vì RCA đã đảm bảo gate BR-12-02 đạt.
        frappe.log_error(
            f"apply_workflow failed for {incident_name}: {e}",
            "IMM-12 _advance_incident_after_rca"
        )
        try:
            # Bypass workflow engine — direct field set + audit
            prev = inc.workflow_state or inc.status
            frappe.db.set_value(
                _DT_INCIDENT, incident_name,
                {
                    "workflow_state": _STATUS_CLOSED,
                    "status": _STATUS_CLOSED,
                    "closed_by": frappe.session.user,
                    "closed_date": today(),
                },
            )
            frappe.db.commit()
            _log(incident_name, inc.asset or "",
                 "Auto-closed (fallback direct) sau RCA hoàn tất",
                 prev, _STATUS_CLOSED)
            return True
        except Exception:
            frappe.log_error(frappe.get_traceback(),
                             "IMM-12 _advance_incident_after_rca fallback")
            return False


def validate_incident_close_gate(doc, method: str | None = None) -> None:
    """NEG-11: Hook 'Incident Report.validate' — chặn đóng High/Critical
    khi chưa có RCA Completed.

    Áp dụng khi workflow_state hoặc status đang chuyển sang Closed.
    """
    target_state = (doc.get("workflow_state") or "") or (doc.get("status") or "")
    if target_state != _STATUS_CLOSED:
        return
    severity = doc.get("severity") or ""
    if severity not in _HIGH_SEVERITY:
        return
    if not doc.get("requires_rca") and not doc.get("rca_required"):
        return  # User đã thủ công gỡ requires_rca (admin override) — không chặn
    rca_name = doc.get("rca_record")
    if not rca_name:
        nthrow_in_hook(MSG.IMM12_CLOSE_RCA_REQUIRED, severity=severity)
    rca_status = frappe.db.get_value(_DT_RCA, rca_name, "status")
    if rca_status != _RCA_COMPLETED:
        nthrow_in_hook(MSG.IMM12_CLOSE_RCA_INCOMPLETE,
                       severity=severity, rca=rca_name)


def _try_transition_asset(
    asset: str, to_status: str, incident_name: str, actor: str,
) -> None:
    cur = frappe.db.get_value(_DT_ASSET, asset, "lifecycle_status") or ""
    if cur in (to_status, "Decommissioned"):
        return
    try:
        svc00.transition_asset_status(
            asset_name=asset, to_status=to_status,
            actor=actor,
            root_doctype=_DT_INCIDENT, root_record=incident_name,
            reason=f"Incident {incident_name} → {to_status}",
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), f"IMM-12 asset transition {asset}→{to_status}")
