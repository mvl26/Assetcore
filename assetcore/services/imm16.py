# Copyright (c) 2026, AssetCore Team
# IMM-16 Compliance Monitoring & CAPA — Service Layer.
from __future__ import annotations

import json
from typing import Any

import frappe
from frappe import _
from frappe.utils import getdate, now_datetime, nowdate, add_days

from assetcore.repositories.compliance_repo import (
    ComplianceFindingRepo,
    ComplianceRuleRepo,
    ComplianceScorecardRepo,
    InternalAuditRepo,
)
from assetcore.services.shared import ErrorCode, Roles, ServiceError, normalize_filters
from assetcore.utils.lifecycle import log_audit_event


# ─── Status constants ────────────────────────────────────────────────────────

class FindingStatus:
    OPEN = "Open"
    UNDER_REVIEW = "Under Review"
    CONFIRMED_NC = "Confirmed NC"
    FALSE_POSITIVE = "False Positive"
    RESOLVED = "Resolved"
    WAIVED = "Waived"
    CLOSED = "Closed"

    ACTIVE = (OPEN, UNDER_REVIEW, CONFIRMED_NC)


class AuditStatus:
    PLANNED = "Planned"
    IN_PROGRESS = "In Progress"
    REPORTING = "Reporting"
    CLOSED = "Closed"


class RuleCategory:
    DOCUMENT = "Document"
    PM = "PM"
    CALIBRATION = "Calibration"
    TRAINING = "Training"
    STOCK = "Stock"
    SLA = "SLA"
    SAFETY = "Safety"


# ─── Compliance Rules ─────────────────────────────────────────────────────────

def list_compliance_rules(filters: dict, *, page: int = 1,
                           page_size: int = 20) -> dict:
    """Liệt kê quy tắc tuân thủ."""
    rows, pg = ComplianceRuleRepo.list(
        filters=normalize_filters(filters),
        fields=["name", "rule_code", "rule_name", "source_module",
                "category", "severity", "evaluation_frequency", "is_active"],
        page=page, page_size=page_size,
    )
    return {"data": rows, "pagination": pg}


def create_compliance_rule(data: dict) -> dict:
    """Tạo quy tắc tuân thủ mới."""
    _require_qa_or_admin()
    if not data.get("rule_code"):
        raise ServiceError(ErrorCode.VALIDATION, "Mã quy tắc (rule_code) là bắt buộc")
    if ComplianceRuleRepo.exists(data["rule_code"]):
        raise ServiceError(ErrorCode.DUPLICATE,
                           f"Quy tắc {data['rule_code']} đã tồn tại")
    # Validate threshold JSON
    td = data.get("threshold_definition")
    if td:
        try:
            if isinstance(td, str):
                json.loads(td)
        except (ValueError, TypeError):
            raise ServiceError(ErrorCode.VALIDATION,
                               "threshold_definition phải là JSON hợp lệ")

    data.setdefault("is_active", 1)
    data.setdefault("version", "1.0")
    doc = ComplianceRuleRepo.create(data)
    frappe.db.commit()
    return {"name": doc.name, "rule_code": doc.rule_code}


# ─── Compliance Findings ──────────────────────────────────────────────────────

def list_compliance_findings(filters: dict, *, page: int = 1,
                              page_size: int = 20) -> dict:
    """Liệt kê temuan kepatuhan."""
    rows, pg = ComplianceFindingRepo.list(
        filters=normalize_filters(filters),
        fields=["name", "rule", "asset", "detected_date", "severity",
                "status", "capa_ref", "responsible_dept", "evaluation_date"],
        order_by="detected_date desc",
        page=page, page_size=page_size,
    )
    return {"data": rows, "pagination": pg}


def create_finding(rule_ref: str, asset_ref: str, work_order_ref: str,
                   severity: str, description: str,
                   evaluation_date: str = "") -> dict:
    """Tạo Compliance Finding. Auto-tạo CAPA nếu severity=Critical."""
    if not ComplianceRuleRepo.exists(rule_ref):
        raise ServiceError(ErrorCode.NOT_FOUND,
                           f"Không tìm thấy quy tắc: {rule_ref}")

    eval_date = evaluation_date or nowdate()
    # Idempotent check
    existing = ComplianceFindingRepo.find_existing(rule_ref, work_order_ref or asset_ref,
                                                    eval_date)
    if existing:
        return {"name": existing, "existing": True}

    doc = ComplianceFindingRepo.create({
        "rule": rule_ref,
        "asset": asset_ref,
        "source_record_doctype": "Asset Repair" if work_order_ref else "AC Asset",
        "source_record": work_order_ref or asset_ref,
        "detected_date": now_datetime(),
        "severity": severity,
        "status": FindingStatus.OPEN,
        "evaluation_date": eval_date,
        "notes": description,
    })

    capa_name = None
    if severity == "Critical":
        capa_name = _auto_create_capa_for_finding(doc.name, asset_ref, severity, description)
        if capa_name:
            ComplianceFindingRepo.set_values(doc.name, {"capa_ref": capa_name})

    try:
        log_audit_event(
            asset=asset_ref or "",
            event_type="compliance_finding_created",
            actor=frappe.session.user,
            ref_doctype=ComplianceFindingRepo.DOCTYPE,
            ref_name=doc.name,
            change_summary=f"IMM-16 Finding {doc.name} — severity: {severity}",
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMM-16 audit trail failed")
    frappe.db.commit()
    return {"name": doc.name, "capa_ref": capa_name}


def close_finding(finding_name: str, capa_ref: str, resolution_note: str) -> dict:
    """Đóng Finding sau khi CAPA hoàn thành."""
    _require_qa_or_admin()
    doc = ComplianceFindingRepo.get(finding_name)
    if not doc:
        raise ServiceError(ErrorCode.NOT_FOUND,
                           f"Không tìm thấy Finding: {finding_name}")
    if doc.status not in FindingStatus.ACTIVE:
        raise ServiceError(ErrorCode.BAD_STATE,
                           f"Finding đã ở trạng thái kết thúc: {doc.status}")

    doc.status = FindingStatus.RESOLVED
    doc.capa_ref = capa_ref or doc.capa_ref
    doc.notes = (doc.notes or "") + f"\nResolution: {resolution_note}"
    doc.review_date = now_datetime()
    doc.reviewer = frappe.session.user
    ComplianceFindingRepo.save(doc)

    try:
        log_audit_event(
            asset=doc.asset or "",
            event_type="compliance_finding_closed",
            actor=frappe.session.user,
            ref_doctype=ComplianceFindingRepo.DOCTYPE,
            ref_name=finding_name,
            change_summary=f"Finding closed. CAPA: {capa_ref}. {resolution_note}",
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMM-16 audit trail failed")
    frappe.db.commit()
    return {"name": finding_name, "status": FindingStatus.RESOLVED}


# ─── Internal Audit ───────────────────────────────────────────────────────────

def list_internal_audits(filters: dict, *, page: int = 1,
                          page_size: int = 20) -> dict:
    """Liệt kê audit nội bộ."""
    rows, pg = InternalAuditRepo.list(
        filters=normalize_filters(filters),
        fields=["name", "audit_code", "audit_type", "planned_start",
                "planned_end", "lead_auditor", "status", "findings_count"],
        order_by="planned_start desc",
        page=page, page_size=page_size,
    )
    return {"data": rows, "pagination": pg}


def create_internal_audit(data: dict) -> dict:
    """Tạo audit nội bộ mới."""
    _require_qa_or_admin()
    if not data.get("audit_code"):
        raise ServiceError(ErrorCode.VALIDATION, "audit_code là bắt buộc")
    data.setdefault("status", AuditStatus.PLANNED)
    doc = InternalAuditRepo.create(data)
    frappe.db.commit()
    return {"name": doc.name, "status": AuditStatus.PLANNED}


def submit_audit_findings(audit_name: str, findings: list[dict]) -> dict:
    """Ghi nhận kết quả audit — tạo Compliance Findings."""
    _require_qa_or_admin()
    doc = InternalAuditRepo.get(audit_name)
    if not doc:
        raise ServiceError(ErrorCode.NOT_FOUND,
                           f"Không tìm thấy audit: {audit_name}")
    if doc.status not in (AuditStatus.IN_PROGRESS, AuditStatus.PLANNED):
        raise ServiceError(ErrorCode.BAD_STATE,
                           f"Không thể ghi nhận kết quả ở trạng thái: {doc.status}")

    created_findings: list[str] = []
    for f in findings:
        rule_ref = f.get("rule_ref", "")
        if not rule_ref:
            continue
        result = create_finding(
            rule_ref=rule_ref,
            asset_ref=f.get("asset_ref", ""),
            work_order_ref=f.get("work_order_ref", ""),
            severity=f.get("severity", "Medium"),
            description=f.get("description", ""),
            evaluation_date=f.get("evaluation_date", nowdate()),
        )
        if result.get("name"):
            created_findings.append(result["name"])

    doc.status = AuditStatus.REPORTING
    doc.findings_count = (doc.findings_count or 0) + len(created_findings)
    InternalAuditRepo.save(doc)

    try:
        log_audit_event(
            asset="",
            event_type="audit_findings_submitted",
            actor=frappe.session.user,
            ref_doctype=InternalAuditRepo.DOCTYPE,
            ref_name=audit_name,
            change_summary=f"Audit {audit_name}: {len(created_findings)} findings created",
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMM-16 audit trail failed")
    frappe.db.commit()
    return {"name": audit_name, "findings_created": created_findings,
            "status": AuditStatus.REPORTING}


def close_internal_audit(audit_name: str) -> dict:
    """Đóng audit nội bộ."""
    _require_qa_or_admin()
    doc = InternalAuditRepo.get(audit_name)
    if not doc:
        raise ServiceError(ErrorCode.NOT_FOUND,
                           f"Không tìm thấy audit: {audit_name}")
    if doc.status == AuditStatus.CLOSED:
        raise ServiceError(ErrorCode.BAD_STATE, "Audit đã được đóng")

    doc.status = AuditStatus.CLOSED
    doc.actual_end = nowdate()
    InternalAuditRepo.save(doc)

    try:
        log_audit_event(
            asset="",
            event_type="internal_audit_closed",
            actor=frappe.session.user,
            ref_doctype=InternalAuditRepo.DOCTYPE,
            ref_name=audit_name,
            change_summary=f"Internal Audit {audit_name} closed",
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMM-16 audit trail failed")
    frappe.db.commit()
    return {"name": audit_name, "status": AuditStatus.CLOSED}


# ─── Compliance Scorecard ─────────────────────────────────────────────────────

def generate_scorecard(module_ref: str, period: str) -> dict:
    """Tính scorecard tuân thủ theo module và kỳ (YYYY-MM)."""
    try:
        year, month = int(period[:4]), int(period[5:7])
    except (ValueError, IndexError):
        raise ServiceError(ErrorCode.VALIDATION,
                           "Kỳ phải có định dạng YYYY-MM")

    start = f"{year}-{month:02d}-01"
    if month == 12:
        end = f"{year + 1}-01-01"
    else:
        end = f"{year}-{month + 1:02d}-01"

    filters: dict = {
        "evaluation_date": ("between", [start, end]),
        "status": ("!=", FindingStatus.FALSE_POSITIVE),
    }
    if module_ref:
        filters["rule"] = ("like", f"{module_ref}%")

    findings = frappe.get_all(
        ComplianceFindingRepo.DOCTYPE,
        filters=filters,
        fields=["name", "rule", "status", "severity", "responsible_dept"],
    )

    total = len(findings)
    non_compliant = sum(1 for f in findings if f.status in
                        (FindingStatus.CONFIRMED_NC,))
    compliant = total - non_compliant
    score_pct = round(compliant / total * 100, 2) if total else 100.0

    # Module breakdown
    by_module: dict[str, dict] = {}
    for f in findings:
        rule_module = (f.rule or "")[:6]  # IMM-XX
        entry = by_module.setdefault(rule_module, {"total": 0, "nc": 0})
        entry["total"] += 1
        if f.status == FindingStatus.CONFIRMED_NC:
            entry["nc"] += 1

    # Dept breakdown
    by_dept: dict[str, dict] = {}
    for f in findings:
        dept = f.responsible_dept or "Unknown"
        entry = by_dept.setdefault(dept, {"total": 0, "nc": 0})
        entry["total"] += 1
        if f.status == FindingStatus.CONFIRMED_NC:
            entry["nc"] += 1

    # CAPA counts
    open_capas = frappe.db.count("IMM CAPA Record",
                                   {"status": ("in", ["Open", "In Progress",
                                                       "Pending Verification"])})
    overdue_capas = frappe.db.count("IMM CAPA Record",
                                     {"status": ("not in", ["Closed"]),
                                      "due_date": ("<", nowdate())})

    sc_doc = frappe.get_doc({
        "doctype": "IMM Compliance Scorecard",
        "period_year": year,
        "period_month": month,
        "scope": "Hospital",
        "scope_value": module_ref or "All",
        "total_rules_evaluated": total,
        "compliant_count": compliant,
        "non_compliant_count": non_compliant,
        "score_pct": score_pct,
        "capa_open_count": open_capas,
        "capa_overdue_count": overdue_capas,
        "generated_at": now_datetime(),
        "is_published": 0,
    })
    sc_doc.flags.ignore_links = True
    sc_doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return {
        "scorecard": sc_doc.name,
        "period": period,
        "score_pct": score_pct,
        "total_findings": total,
        "non_compliant": non_compliant,
    }


# ─── Scheduler Jobs ───────────────────────────────────────────────────────────

def evaluate_all_compliance_rules() -> None:
    """Scheduler daily: chạy tất cả active rules và tạo findings."""
    rules = ComplianceRuleRepo.get_active_rules(
        evaluation_frequency=["Daily", "Realtime", "Hourly"]
    )
    for rule in rules:
        try:
            _evaluate_single_rule(rule)
        except Exception:
            frappe.log_error(frappe.get_traceback(),
                             f"IMM-16 rule evaluation failed: {rule.get('rule_code')}")


def check_capa_due() -> None:
    """Scheduler daily: kiểm tra CAPA quá hạn và escalate."""
    overdue = frappe.get_all(
        "IMM CAPA Record",
        filters={"status": ("not in", ["Closed"]),
                 "due_date": ("<", nowdate())},
        fields=["name", "responsible", "severity", "due_date",
                "asset", "description"],
    )
    for capa in overdue:
        try:
            _escalate_capa(capa)
        except Exception:
            frappe.log_error(frappe.get_traceback(), f"IMM-16 CAPA escalation failed: {capa.get('name')}")


# ─── Internal Audit service hooks ────────────────────────────────────────────

def validate_internal_audit(doc) -> None:
    """Validate date range và sync findings_count (gọi từ IMMInternalAudit.validate)."""
    if doc.planned_start and doc.planned_end:
        if doc.planned_end < doc.planned_start:
            frappe.throw(_("Ngày kết thúc phải sau ngày bắt đầu"))
    doc.findings_count = len(doc.findings or [])


def on_update_internal_audit(doc) -> None:
    """Recount findings on every save (gọi từ IMMInternalAudit.on_update)."""
    doc.findings_count = len(doc.findings or [])


# ─── Compliance Finding service hooks ────────────────────────────────────────

_VALID_SEVERITY = ("Low", "Medium", "High", "Critical")


def compliance_finding_validate(doc) -> None:
    """Validate severity (gọi từ IMMComplianceFinding.validate)."""
    if doc.severity not in _VALID_SEVERITY:
        frappe.throw(
            _("Severity phải là: {0}").format(", ".join(_VALID_SEVERITY))
        )


# ─── Compliance Rule service hooks ───────────────────────────────────────────

def compliance_rule_validate(doc) -> None:
    """Validate threshold_definition JSON (gọi từ IMMComplianceRule.validate)."""
    td = doc.threshold_definition
    if td:
        try:
            if isinstance(td, str):
                json.loads(td)
        except (ValueError, TypeError):
            frappe.throw(_("threshold_definition phải là JSON hợp lệ"))


def compliance_rule_before_save(doc) -> None:
    """Bump minor version khi threshold_definition hoặc severity thay đổi."""
    if (doc.has_value_changed("threshold_definition") or
            doc.has_value_changed("severity")):
        doc.previous_version = doc.version or "1.0"
        major, minor = (doc.version or "1.0").split(".")
        doc.version = f"{major}.{int(minor) + 1}"


# ─── CAPA integration (reuse imm00) ──────────────────────────────────────────

def capa_record_validate(doc, method=None) -> None:
    """Validate dates + workflow-gate VR-05/06 (gọi từ IMMCAPARecord.validate)."""
    from frappe.utils import getdate
    # Date range checks
    if doc.due_date and doc.opened_date and getdate(doc.due_date) < getdate(doc.opened_date):
        frappe.throw(_("due_date phải >= opened_date."))
    if doc.closed_date and doc.opened_date and getdate(doc.closed_date) < getdate(doc.opened_date):
        frappe.throw(_("closed_date phải >= opened_date."))
    # Auto-set capa_number from name on first save
    if not doc.capa_number:
        doc.capa_number = doc.name
    # VR-05/06/07 workflow gate
    ws = doc.workflow_state or ""
    if ws in ("Action Plan", "Implementation", "Verification", "Closed"):
        if not doc.get("imm_root_cause_method"):
            frappe.throw(_("VR-05: Phải chọn phương pháp phân tích root cause."))
    if doc.status == "Closed":
        if not doc.effectiveness_check:
            frappe.throw(_("VR-06: Effectiveness check chưa hoàn tất."))


def capa_record_before_submit(doc, method=None) -> None:
    """BR-00-08: enforce root_cause, corrective_action, preventive_action trước submit."""
    from frappe.utils import nowdate as _nowdate
    if not (doc.root_cause and doc.root_cause.strip()):
        frappe.throw(_("Phải điền Root Cause trước khi submit CAPA (BR-00-08)."))
    if not (doc.corrective_action and doc.corrective_action.strip()):
        frappe.throw(_("Phải điền Corrective Action trước khi submit CAPA (BR-00-08)."))
    if not (doc.preventive_action and doc.preventive_action.strip()):
        frappe.throw(_("Phải điền Preventive Action trước khi submit CAPA (BR-00-08)."))
    if doc.status != "Closed":
        doc.status = "Closed"
    if not doc.closed_date:
        doc.closed_date = _nowdate()


def capa_record_on_update(doc, method=None) -> None:
    """Cascade: Finding → Resolved khi CAPA Closed."""
    if doc.status == "Closed" and doc.source_type == "Compliance Finding":
        frappe.db.set_value(
            "IMM Compliance Finding", doc.source_ref, "status", FindingStatus.RESOLVED
        )


def check_asset_compliance_status(asset: str) -> dict:
    """BR-16-09: Kiểm tra asset có CAPA Critical mở không trước khi tạo WO."""
    if not asset:
        return {"blocked": False, "active_capas_count": 0}
    crit_open = frappe.get_all(
        "IMM CAPA Record",
        filters={"asset": asset,
                 "imm_risk_level": "Critical",
                 "status": ("in", ["Open", "In Progress", "Pending Verification"])},
        pluck="name",
    )
    if crit_open:
        return {
            "blocked": True,
            "reasons": [{"type": "CAPA_CRITICAL_OPEN", "ref": n} for n in crit_open],
            "active_capas_count": len(crit_open),
        }
    return {"blocked": False, "active_capas_count": 0}


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _auto_create_capa_for_finding(finding_name: str, asset: str,
                                   severity: str, description: str) -> str | None:
    """Auto-create CAPA when Critical finding created."""
    try:
        from assetcore.services.imm00 import create_capa
        capa_name = create_capa(
            asset=asset or "N/A",
            source_type="Compliance Finding",
            source_ref=finding_name,
            severity=_map_severity(severity),
            description=f"[Auto-IMM16] {description}",
        )
        return capa_name
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMM-16: auto_create_capa failed")
        return None


def _map_severity(s: str) -> str:
    return {"Low": "Minor", "Medium": "Major", "High": "Major",
            "Critical": "Critical"}.get(s, "Major")


def _evaluate_single_rule(rule: dict) -> None:
    """Đánh giá một rule và tạo finding nếu vi phạm."""
    category = rule.get("category", "")
    source_dt = rule.get("data_source_doctype", "")
    if not source_dt:
        return

    # Basic count-based evaluation
    threshold_def = rule.get("threshold_definition") or "{}"
    if isinstance(threshold_def, str):
        try:
            threshold_def = json.loads(threshold_def)
        except Exception:
            return

    current_count = frappe.db.count(source_dt) if source_dt else 0
    threshold = threshold_def.get("value", 0)
    op = threshold_def.get("op", ">")

    violated = _compare_values(current_count, op, threshold)
    if not violated:
        return

    create_finding(
        rule_ref=rule["name"],
        asset_ref="",
        work_order_ref="",
        severity=rule.get("severity", "Medium"),
        description=f"Rule {rule.get('rule_code')} violated. Current: {current_count}, threshold: {threshold}",
        evaluation_date=nowdate(),
    )


def _compare_values(current: Any, op: str, threshold: Any) -> bool:
    try:
        if op == ">":
            return current > threshold
        elif op == "<":
            return current < threshold
        elif op == ">=":
            return current >= threshold
        elif op == "<=":
            return current <= threshold
        elif op == "=":
            return current == threshold
        elif op == "!=":
            return current != threshold
    except Exception:
        pass
    return False


def _escalate_capa(capa: dict) -> None:
    overdue_days = (getdate(nowdate()) - getdate(capa["due_date"])).days
    severity = frappe.db.get_value("IMM CAPA Record", capa["name"], "imm_risk_level") or "Medium"
    if severity == "Critical" and overdue_days >= 1:
        _send_capa_escalation(capa, level=1)
    elif severity in ("High", "Critical") and overdue_days >= 3:
        _send_capa_escalation(capa, level=2)


def _send_capa_escalation(capa: dict, level: int) -> None:
    try:
        recipients = [capa.get("responsible")] if capa.get("responsible") else []
        if level >= 2:
            wl_emails = frappe.db.sql(
                """SELECT DISTINCT u.email FROM `tabHas Role` hr
                   JOIN `tabUser` u ON u.name = hr.parent
                   WHERE hr.role = %s AND u.enabled = 1""",
                (Roles.WORKSHOP,), as_dict=True,
            )
            recipients += [r.email for r in wl_emails if r.email]
        if recipients:
            frappe.sendmail(
                recipients=list(set(filter(None, recipients))),
                subject=f"[AssetCore] CAPA {capa['name']} quá hạn — Level {level}",
                message=f"CAPA {capa['name']} đã quá hạn. Vui lòng xử lý ngay.",
            )
    except Exception:
        pass


def _require_qa_or_admin() -> None:
    from assetcore.services.shared import has_any_role
    allowed = (Roles.QA, Roles.SYS_ADMIN, Roles.OPS_MANAGER, Roles.AUDITOR)
    if not has_any_role(allowed):
        raise ServiceError(ErrorCode.FORBIDDEN,
                           "Chỉ QA Officer hoặc Admin có thể thực hiện thao tác này")




# ─── Additional Scheduler Jobs ────────────────────────────────────────────────

def run_compliance_evaluation_hourly() -> None:
    """Scheduler hourly: đánh giá rules có evaluation_frequency=Hourly/Realtime (stock breach IMM-15)."""
    rules = ComplianceRuleRepo.get_active_rules(
        evaluation_frequency=["Hourly", "Realtime"]
    )
    for rule in rules:
        try:
            _evaluate_single_rule(rule)
        except Exception:
            frappe.log_error(frappe.get_traceback(),
                             f"IMM-16 hourly rule failed: {rule.get('rule_code')}")


def run_compliance_evaluation_weekly() -> None:
    """Scheduler weekly Monday: đánh giá rules có evaluation_frequency=Weekly (SLA review IMM-09/12)."""
    rules = ComplianceRuleRepo.get_active_rules(
        evaluation_frequency=["Weekly"]
    )
    for rule in rules:
        try:
            _evaluate_single_rule(rule)
        except Exception:
            frappe.log_error(frappe.get_traceback(),
                             f"IMM-16 weekly rule failed: {rule.get('rule_code')}")


def check_audit_milestones() -> None:
    """Scheduler daily 02:30: cảnh báo Lead Auditor 7 ngày trước khi audit bắt đầu."""
    from frappe.utils import add_days
    target_date = add_days(nowdate(), 7)
    upcoming = frappe.get_all(
        "IMM Internal Audit",
        filters={
            "status": "Planned",
            "planned_start": target_date,
        },
        fields=["name", "audit_code", "lead_auditor", "planned_start", "planned_end"],
    )
    for audit in upcoming:
        if not audit.lead_auditor:
            continue
        try:
            frappe.sendmail(
                recipients=[audit.lead_auditor],
                subject=f"[AssetCore] Nhắc nhở: Audit {audit.audit_code} bắt đầu trong 7 ngày",
                message=f"""<p>Audit nội bộ <b>{audit.audit_code}</b> sẽ bắt đầu vào <b>{audit.planned_start}</b>.</p>
                <p>Vui lòng chuẩn bị kế hoạch kiểm tra và checklist.</p>""",
            )
        except Exception:
            pass


def check_management_review_due() -> None:
    """Scheduler weekly Monday 08:00: cảnh báo nếu thiếu Management Review trong quý hiện tại."""
    from frappe.utils import getdate
    today = getdate(nowdate())
    current_quarter = f"Q{((today.month - 1) // 3) + 1}-{today.year}"
    # Check if MR exists for current quarter
    mr_exists = frappe.db.exists(
        "IMM Management Review",
        {"quarter": current_quarter, "status": ("not in", ["Draft"])},
    )
    if mr_exists:
        return
    # Alert if we're past week 4 of the quarter (month 2 of the quarter)
    quarter_month = ((today.month - 1) % 3) + 1
    if quarter_month < 2:
        return
    try:
        from assetcore.utils.helpers import _get_role_emails, _safe_sendmail
        from assetcore.services.shared import Roles
        recipients = _get_role_emails([Roles.QA, Roles.OPS_MANAGER])
        _safe_sendmail(
            recipients=recipients,
            subject=f"[AssetCore] Nhắc nhở: Chưa có Management Review cho {current_quarter}",
            message=f"<p>Quý <b>{current_quarter}</b> chưa có Management Review đã hoàn thành. "
                    f"Vui lòng lên lịch họp xem xét quản lý.</p>",
        )
    except Exception:
        pass


def update_compliance_scorecard() -> None:
    """Scheduler monthly 1st 03:00: tổng hợp Scorecard tháng trước."""
    from frappe.utils import getdate, add_months
    today = getdate(nowdate())
    # Get previous month
    prev_month = getdate(add_months(nowdate(), -1))
    year, month = prev_month.year, prev_month.month
    # Check if scorecard already exists for this period
    if ComplianceScorecardRepo.find_by_period(year, month):
        return
    try:
        result = generate_scorecard("", f"{year}-{month:02d}")
        from assetcore.utils.helpers import _get_role_emails, _safe_sendmail
        from assetcore.services.shared import Roles
        recipients = _get_role_emails([Roles.QA, Roles.WORKSHOP, Roles.OPS_MANAGER])
        _safe_sendmail(
            recipients=recipients,
            subject=f"[AssetCore] Compliance Scorecard {year}-{month:02d} đã được tạo",
            message=f"<p>Scorecard tháng {month}/{year}: score = <b>{result.get('score_pct', 0):.1f}%</b>. "
                    f"Findings: {result.get('total_findings', 0)}.</p>",
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMM-16: update_compliance_scorecard failed")


# ─── Doc-event real-time evaluators ──────────────────────────────────────────

def eval_imm04_realtime(doc, method=None) -> None:
    """Doc event Asset Commissioning.on_submit: tạo compliance finding nếu vi phạm."""
    try:
        rules = ComplianceRuleRepo.get_active_rules(evaluation_frequency=["Realtime"])
        imm04_rules = [r for r in rules if (r.get("source_module") or "").startswith("IMM-04")]
        asset = getattr(doc, "master_item", "") or getattr(doc, "asset_ref", "") or ""
        for rule in imm04_rules:
            _evaluate_single_rule_for_asset(rule, asset, doc.doctype, doc.name)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMM-16: eval_imm04_realtime failed")


def eval_imm05_realtime(doc, method=None) -> None:
    """Doc event Asset Document.on_update: tạo compliance finding nếu doc expired."""
    try:
        if getattr(doc, "workflow_state", "") != "Expired":
            return
        rules = ComplianceRuleRepo.get_active_rules(evaluation_frequency=["Realtime"])
        imm05_rules = [r for r in rules if (r.get("source_module") or "").startswith("IMM-05")]
        asset = getattr(doc, "asset_ref", "") or ""
        for rule in imm05_rules:
            _evaluate_single_rule_for_asset(rule, asset, doc.doctype, doc.name)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMM-16: eval_imm05_realtime failed")


def eval_imm08_09_realtime(doc, method=None) -> None:
    """Doc event Work Order.on_submit: đánh giá SLA rules."""
    try:
        rules = ComplianceRuleRepo.get_active_rules(evaluation_frequency=["Realtime"])
        wo_rules = [r for r in rules
                    if (r.get("source_module") or "").startswith(("IMM-08", "IMM-09"))]
        asset = getattr(doc, "asset_ref", "") or ""
        for rule in wo_rules:
            _evaluate_single_rule_for_asset(rule, asset, doc.doctype, doc.name)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMM-16: eval_imm08_09_realtime failed")


def gate_wo_submit(doc, method=None) -> None:
    """Doc event Work Order.validate: BR-16-09 — block submit nếu asset có Critical CAPA mở."""
    try:
        asset = getattr(doc, "asset_ref", "")
        if not asset:
            return
        result = check_asset_compliance_status(asset)
        if result.get("blocked"):
            capas = ", ".join(r["ref"] for r in result.get("reasons", []))
            frappe.throw(frappe._(
                f"BR-16-09: Thiết bị {asset} có CAPA Critical đang mở ({capas}). "
                f"Không thể tạo Work Order cho đến khi CAPA được đóng."
            ))
    except frappe.ValidationError:
        raise
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMM-16: gate_wo_submit failed")


def eval_imm11_realtime(doc, method=None) -> None:
    """Doc event Calibration Record.on_submit: đánh giá calibration compliance rules."""
    try:
        rules = ComplianceRuleRepo.get_active_rules(evaluation_frequency=["Realtime"])
        cal_rules = [r for r in rules if (r.get("source_module") or "").startswith("IMM-11")]
        asset = getattr(doc, "asset_ref", "") or ""
        for rule in cal_rules:
            _evaluate_single_rule_for_asset(rule, asset, doc.doctype, doc.name)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMM-16: eval_imm11_realtime failed")


# ─── Internal helper for doc-event evaluation ────────────────────────────────

def _evaluate_single_rule_for_asset(rule: dict, asset: str,
                                     source_doctype: str, source_record: str) -> None:
    """Evaluate một rule trong context của một asset + source record cụ thể."""
    threshold_def = rule.get("threshold_definition") or "{}"
    if isinstance(threshold_def, str):
        try:
            threshold_def = json.loads(threshold_def)
        except Exception:
            return
    current = 1  # For event-driven: violation is implicit (event fired = violation)
    threshold = threshold_def.get("value", 0)
    op = threshold_def.get("op", ">=")
    if not _compare_values(current, op, threshold):
        return
    create_finding(
        rule_ref=rule["name"],
        asset_ref=asset,
        work_order_ref=source_record if source_doctype != "AC Asset" else "",
        severity=rule.get("severity", "Medium"),
        description=f"Rule {rule.get('rule_code')} violated by {source_doctype} {source_record}",
        evaluation_date=nowdate(),
    )
