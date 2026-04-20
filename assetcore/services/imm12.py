# Copyright (c) 2026, AssetCore Team
"""IMM-12 — Incident & CAPA orchestration service.

State machines:
  Incident: Open → Under Investigation → Resolved → Closed (Cancelled branch)
  RCA:      RCA Required → RCA In Progress → Completed
"""
from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import add_days, now_datetime, nowdate, today

from assetcore.services import imm00 as svc00

_DT_INCIDENT = "Incident Report"
_DT_RCA = "IMM RCA Record"
_DT_CAPA = "IMM CAPA Record"
_DT_ASSET = "AC Asset"

_STATUS_OPEN = "Open"
_STATUS_INVESTIGATING = "Under Investigation"
_STATUS_RESOLVED = "Resolved"
_STATUS_CLOSED = "Closed"
_STATUS_CANCELLED = "Cancelled"

_RCA_REQUIRED = "RCA Required"
_RCA_IN_PROGRESS = "RCA In Progress"
_RCA_COMPLETED = "Completed"

_HIGH_SEVERITY = ("High", "Critical")
_RCA_SEVERITY = ("Major", "Critical", "High")  # IMM-12 doc uses High/Critical for auto-RCA

_ASSET_OUT_OF_SERVICE = "Out of Service"
_ASSET_ACTIVE = "Active"

_VALID_TRANSITIONS: dict[str, list[str]] = {
    _STATUS_OPEN: [_STATUS_INVESTIGATING, _STATUS_CANCELLED],
    _STATUS_INVESTIGATING: [_STATUS_RESOLVED, _STATUS_CANCELLED],
    _STATUS_RESOLVED: [_STATUS_CLOSED],
}

_CHRONIC_WINDOW_DAYS = 90
_CHRONIC_MIN_COUNT = 3


class IncidentError(Exception):
    def __init__(self, message: str, code: int = 422) -> None:
        super().__init__(message)
        self.message = message
        self.code = code


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _get_incident(name: str) -> "frappe.Document":
    if not frappe.db.exists(_DT_INCIDENT, name):
        raise IncidentError(_("Không tìm thấy Incident Report: {0}").format(name), 404)
    return frappe.get_doc(_DT_INCIDENT, name)


def _get_rca(name: str) -> "frappe.Document":
    if not frappe.db.exists(_DT_RCA, name):
        raise IncidentError(_("Không tìm thấy RCA Record: {0}").format(name), 404)
    return frappe.get_doc(_DT_RCA, name)


def _assert_transition(doc: "frappe.Document", to_status: str) -> None:
    allowed = _VALID_TRANSITIONS.get(doc.status, [])
    if to_status not in allowed:
        raise IncidentError(
            _("Không thể chuyển từ '{0}' sang '{1}'").format(doc.status, to_status), 409,
        )


def _log(name: str, asset: str, summary: str, from_status: str, to_status: str) -> None:
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


def _map_severity(severity: str) -> str:
    return {"Low": "Minor", "Medium": "Minor", "High": "Major", "Critical": "Critical"}.get(severity, "Minor")


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
) -> dict:
    """Tạo mới Incident Report. BR-12-01: Critical → clinical_impact bắt buộc."""
    if severity == "Critical" and not clinical_impact.strip():
        raise IncidentError(_("Incident Critical bắt buộc nhập clinical_impact."), 422)
    if not frappe.db.exists(_DT_ASSET, asset):
        raise IncidentError(_("Asset không tồn tại: {0}").format(asset), 404)

    doc = frappe.new_doc(_DT_INCIDENT)
    doc.asset = asset
    doc.incident_type = incident_type
    doc.severity = severity
    doc.description = description
    doc.reported_by = frappe.session.user
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
    doc.rca_required = 1 if severity in ("High", "Critical") else 0
    doc.flags.ignore_permissions = True
    doc.insert()

    # BR-12-04: Critical → auto Out of Service
    if severity == "Critical":
        cur = frappe.db.get_value(_DT_ASSET, asset, "lifecycle_status") or ""
        if cur not in (_ASSET_OUT_OF_SERVICE, "Decommissioned"):
            try:
                svc00.transition_asset_status(
                    asset_name=asset, to_status=_ASSET_OUT_OF_SERVICE,
                    actor=frappe.session.user,
                    root_doctype=_DT_INCIDENT, root_record=doc.name,
                    reason=f"Critical Incident {doc.name}",
                )
            except Exception:
                frappe.log_error(frappe.get_traceback(), "IMM-12 auto Out of Service on Critical")

    frappe.db.commit()
    _log(doc.name, asset, f"Incident reported — {severity} — {incident_type}", "", _STATUS_OPEN)
    return {"name": doc.name, "status": doc.status, "severity": severity}


def acknowledge_incident(name: str, notes: str = "", assigned_to: str = "") -> dict:
    """Open → Under Investigation."""
    doc = _get_incident(name)
    _assert_transition(doc, _STATUS_INVESTIGATING)

    prev = doc.status
    doc.status = _STATUS_INVESTIGATING
    if notes:
        doc.immediate_action = (doc.immediate_action or "") + f"\n[Acknowledged] {notes}"
    if assigned_to:
        doc.resolution_notes = (doc.resolution_notes or "") + f"\nAssigned to: {assigned_to}"
    doc.flags.ignore_permissions = True
    doc.save()
    frappe.db.commit()
    _log(name, doc.asset, f"Incident acknowledged — {notes or 'đang điều tra'}", prev, _STATUS_INVESTIGATING)

    # BR-12-04: High → transition asset Out of Service on acknowledge
    if doc.severity in _HIGH_SEVERITY:
        cur = frappe.db.get_value(_DT_ASSET, doc.asset, "lifecycle_status") or ""
        if cur not in (_ASSET_OUT_OF_SERVICE, "Decommissioned"):
            try:
                svc00.transition_asset_status(
                    asset_name=doc.asset, to_status=_ASSET_OUT_OF_SERVICE,
                    actor=frappe.session.user,
                    root_doctype=_DT_INCIDENT, root_record=name,
                    reason=f"Incident {doc.severity} — {name}",
                )
            except Exception:
                pass

    return {"name": name, "status": doc.status}


def resolve_incident(name: str, resolution_notes: str, root_cause: str = "") -> dict:
    """Under Investigation → Resolved. Auto-CAPA cho High/Critical."""
    doc = _get_incident(name)
    _assert_transition(doc, _STATUS_RESOLVED)

    if not resolution_notes.strip():
        raise IncidentError(_("Bắt buộc nhập ghi chú giải quyết (resolution_notes)."), 422)
    if doc.severity in ("High", "Critical") and not doc.rca_record:
        raise IncidentError(
            _("Incident {0} yêu cầu hoàn thành RCA trước khi Resolved.").format(name), 422
        )

    prev = doc.status
    doc.status = _STATUS_RESOLVED
    doc.resolution_notes = resolution_notes
    if root_cause:
        doc.root_cause_summary = root_cause
    doc.flags.ignore_permissions = True
    doc.save()
    frappe.db.commit()
    _log(name, doc.asset, f"Incident resolved — {resolution_notes[:120]}", prev, _STATUS_RESOLVED)

    if doc.severity in ("High", "Critical") and not doc.linked_capa:
        _auto_create_capa(doc)

    return {"name": name, "status": doc.status, "linked_capa": doc.linked_capa}


def cancel_incident(name: str, reason: str) -> dict:
    """Open/Under Investigation → Cancelled (false alarm)."""
    doc = _get_incident(name)
    _assert_transition(doc, _STATUS_CANCELLED)
    if not reason.strip():
        raise IncidentError(_("Bắt buộc nhập lý do hủy."), 422)

    prev = doc.status
    doc.status = _STATUS_CANCELLED
    doc.resolution_notes = (doc.resolution_notes or "") + f"\n[Cancelled] {reason}"
    doc.flags.ignore_permissions = True
    doc.save()
    frappe.db.commit()
    _log(name, doc.asset, f"Incident cancelled — {reason[:120]}", prev, _STATUS_CANCELLED)
    return {"name": name, "status": doc.status}


def close_incident(name: str, verification_notes: str = "") -> dict:
    """Resolved → Closed. Khôi phục asset nếu Out of Service."""
    doc = _get_incident(name)
    _assert_transition(doc, _STATUS_CLOSED)

    prev = doc.status
    doc.status = _STATUS_CLOSED
    doc.closed_date = today()
    if verification_notes:
        doc.resolution_notes = (doc.resolution_notes or "") + f"\n[Closed] {verification_notes}"
    doc.flags.ignore_permissions = True
    doc.save()
    frappe.db.commit()
    _log(name, doc.asset, f"Incident closed — {verification_notes or 'verified'}", prev, _STATUS_CLOSED)

    if doc.asset:
        cur = frappe.db.get_value(_DT_ASSET, doc.asset, "lifecycle_status") or ""
        if cur == _ASSET_OUT_OF_SERVICE:
            try:
                svc00.transition_asset_status(
                    asset_name=doc.asset, to_status=_ASSET_ACTIVE,
                    actor=frappe.session.user,
                    root_doctype=_DT_INCIDENT, root_record=name,
                    reason=f"Incident {name} closed — verified",
                )
            except Exception:
                pass

    return {"name": name, "status": doc.status, "closed_date": doc.closed_date}


# ─── RCA orchestration ────────────────────────────────────────────────────────

def create_rca(incident_name: str, rca_method: str = "5-Why") -> dict:
    """Tạo RCA Record liên kết với Incident Report."""
    doc = _get_incident(incident_name)
    if doc.rca_record and frappe.db.exists(_DT_RCA, doc.rca_record):
        raise IncidentError(_("Incident đã có RCA Record: {0}").format(doc.rca_record), 409)

    rca = frappe.new_doc(_DT_RCA)
    rca.incident_report = incident_name
    rca.asset = doc.asset
    rca.rca_method = rca_method or "5-Why"
    rca.status = _RCA_REQUIRED
    rca.assigned_to = frappe.session.user
    # Seed 5 empty why steps
    for i in range(1, 6):
        rca.append("five_why_steps", {"why_number": i, "why_question": f"Why {i}?", "why_answer": ""})
    rca.flags.ignore_permissions = True
    rca.insert()

    frappe.db.set_value(_DT_INCIDENT, incident_name, "rca_record", rca.name)
    frappe.db.commit()
    return {"name": rca.name, "status": rca.status}


def get_rca(name: str) -> dict:
    """Chi tiết RCA Record."""
    doc = _get_rca(name)
    data = doc.as_dict()
    if doc.incident_report:
        data["incident_severity"] = frappe.db.get_value(_DT_INCIDENT, doc.incident_report, "severity")
    return data


def submit_rca(name: str, root_cause: str, corrective_action: str, preventive_action: str = "",
               five_why_steps: list | None = None, rca_notes: str = "") -> dict:
    """Hoàn thành RCA → tự động tạo CAPA. BR-12-07: root_cause bắt buộc."""
    rca = _get_rca(name)
    if rca.status == _RCA_COMPLETED:
        raise IncidentError(_("RCA đã hoàn thành."), 409)
    if not root_cause.strip():
        raise IncidentError(_("Bắt buộc nhập nguyên nhân gốc rễ (root_cause)."), 422)
    if not corrective_action.strip():
        raise IncidentError(_("Bắt buộc nhập hành động khắc phục (corrective_action)."), 422)

    rca.status = _RCA_COMPLETED
    rca.root_cause = root_cause
    rca.corrective_action_summary = corrective_action
    if preventive_action:
        rca.preventive_action_summary = preventive_action
    if rca_notes:
        rca.rca_notes = rca_notes
    if five_why_steps:
        rca.set("five_why_steps", [])
        for step in five_why_steps:
            rca.append("five_why_steps", step)
    from frappe.utils import today as _today
    rca.completed_date = _today()
    rca.flags.ignore_permissions = True
    rca.save()

    # Auto CAPA via IMM-00
    try:
        incident = frappe.get_doc(_DT_INCIDENT, rca.incident_report)
        capa_name = svc00.create_capa(
            asset=rca.asset or incident.asset,
            source_type=_DT_RCA,
            source_ref=rca.name,
            severity=_map_severity(incident.severity),
            description=f"Auto-CAPA từ RCA {rca.name}: {root_cause[:200]}",
            responsible=frappe.session.user,
        )
        rca.linked_capa = capa_name
        rca.flags.ignore_permissions = True
        rca.save()
        if not incident.linked_capa:
            frappe.db.set_value(_DT_INCIDENT, rca.incident_report, "linked_capa", capa_name)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMM-12 submit_rca auto_capa")

    frappe.db.commit()
    return {"name": rca.name, "status": rca.status, "linked_capa": rca.linked_capa}


# ─── List / Detail ────────────────────────────────────────────────────────────

def list_incidents(
    status: str = "",
    severity: str = "",
    asset: str = "",
    page: int = 1,
    page_size: int = 20,
) -> dict:
    filters: dict = {}
    if status:
        filters["status"] = status
    if severity:
        filters["severity"] = severity
    if asset:
        filters["asset"] = asset

    total = frappe.db.count(_DT_INCIDENT, filters=filters)
    offset = (page - 1) * page_size
    rows = frappe.get_all(
        _DT_INCIDENT,
        filters=filters,
        fields=["name", "asset", "incident_type", "severity", "status", "fault_code",
                "reported_by", "reported_at", "description", "linked_capa", "linked_repair_wo",
                "rca_required", "rca_record", "chronic_failure_flag", "patient_affected", "closed_date"],
        order_by="reported_at desc",
        limit_start=offset,
        limit_page_length=page_size,
    )
    asset_ids = {r["asset"] for r in rows if r.get("asset")}
    if asset_ids:
        asset_map = {a.name: a.asset_name for a in frappe.get_all(
            _DT_ASSET, filters={"name": ["in", list(asset_ids)]}, fields=["name", "asset_name"]
        )}
        for r in rows:
            r["asset_name"] = asset_map.get(r.get("asset"), r.get("asset") or "")
    return {
        "pagination": {"total": total, "page": page, "page_size": page_size,
                       "total_pages": max(1, -(-total // page_size)), "offset": offset},
        "items": rows,
    }


def get_incident_detail(name: str) -> dict:
    doc = _get_incident(name)
    data = doc.as_dict()
    if doc.asset:
        data["asset_name"] = frappe.db.get_value(_DT_ASSET, doc.asset, "asset_name")
    data["allowed_transitions"] = _VALID_TRANSITIONS.get(doc.status, [])
    if doc.rca_record and frappe.db.exists(_DT_RCA, doc.rca_record):
        rca = frappe.get_doc(_DT_RCA, doc.rca_record)
        data["rca"] = {"name": rca.name, "status": rca.status, "root_cause": rca.root_cause}
    return data


def get_incident_stats() -> dict:
    def _count(f):
        return frappe.db.count(_DT_INCIDENT, filters=f)

    return {
        "total": _count({}),
        "open": _count({"status": _STATUS_OPEN}),
        "investigating": _count({"status": _STATUS_INVESTIGATING}),
        "resolved": _count({"status": _STATUS_RESOLVED}),
        "closed": _count({"status": _STATUS_CLOSED}),
        "critical": _count({"severity": "Critical"}),
        "high": _count({"severity": "High"}),
        "rca_pending": _count({"rca_required": 1, "rca_record": ("is", "not set")}),
        "chronic": _count({"chronic_failure_flag": 1}),
    }


def get_asset_incident_history(asset: str, limit: int = 10) -> dict:
    rows = frappe.get_all(
        _DT_INCIDENT,
        filters={"asset": asset},
        fields=["name", "incident_type", "severity", "status", "reported_at",
                "fault_code", "closed_date", "linked_capa"],
        order_by="reported_at desc",
        limit_page_length=limit,
    )
    return {"asset": asset, "items": rows}


def get_dashboard() -> dict:
    """KPI dashboard cho IMM-12."""
    stats = get_incident_stats()
    recent = frappe.get_all(
        _DT_INCIDENT,
        filters={"status": ["in", [_STATUS_OPEN, _STATUS_INVESTIGATING]]},
        fields=["name", "asset", "severity", "status", "reported_at", "fault_code"],
        order_by="reported_at desc",
        limit_page_length=10,
    )
    chronic = frappe.get_all(
        _DT_INCIDENT,
        filters={"chronic_failure_flag": 1, "status": ["!=", _STATUS_CLOSED]},
        fields=["name", "asset", "fault_code", "reported_at"],
        order_by="reported_at desc",
        limit_page_length=10,
    )
    return {"stats": stats, "active_incidents": recent, "chronic_failures": chronic}


def get_chronic_failures() -> list:
    """Danh sách asset có ≥3 sự cố cùng fault_code trong 90 ngày."""
    cutoff = add_days(nowdate(), -_CHRONIC_WINDOW_DAYS)
    rows = frappe.db.sql("""
        SELECT asset, fault_code, COUNT(*) AS count, MAX(reported_at) AS last_reported
        FROM `tabIncident Report`
        WHERE fault_code IS NOT NULL AND fault_code != ''
          AND reported_at >= %s
          AND status != 'Cancelled'
        GROUP BY asset, fault_code
        HAVING count >= %s
        ORDER BY count DESC
    """, (cutoff, _CHRONIC_MIN_COUNT), as_dict=True)
    return rows


# ─── Scheduler ────────────────────────────────────────────────────────────────

def detect_chronic_failures() -> dict:
    """Daily 02:00 — đánh dấu incident là mãn tính nếu ≥3 cùng fault_code/90 ngày."""
    chronic = get_chronic_failures()
    updated = 0
    for row in chronic:
        matching = frappe.get_all(
            _DT_INCIDENT,
            filters={"asset": row["asset"], "fault_code": row["fault_code"],
                     "status": ["!=", _STATUS_CANCELLED]},
            fields=["name", "chronic_failure_flag"],
        )
        for ir in matching:
            if not ir.get("chronic_failure_flag"):
                frappe.db.set_value(_DT_INCIDENT, ir["name"], {
                    "chronic_failure_flag": 1,
                    "rca_required": 1,
                })
                updated += 1

    if updated:
        frappe.db.commit()
    frappe.logger().info(f"IMM-12 detect_chronic_failures: {updated} flagged")
    return {"updated": updated, "chronic_groups": len(chronic)}


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _auto_create_capa(doc: "frappe.Document") -> None:
    try:
        capa_name = svc00.create_capa(
            asset=doc.asset,
            source_type=_DT_INCIDENT,
            source_ref=doc.name,
            severity=_map_severity(doc.severity),
            description=f"Auto-CAPA từ Incident {doc.name}: {doc.description or ''}",
            responsible=frappe.session.user,
        )
        frappe.db.set_value(_DT_INCIDENT, doc.name, "linked_capa", capa_name)
        frappe.db.commit()
        doc.linked_capa = capa_name
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMM-12 auto_create_capa")
