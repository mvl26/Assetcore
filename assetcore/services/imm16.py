# Copyright (c) 2026, AssetCore Team
# IMM-16 Compliance Monitoring & CAPA — Service Layer.
from __future__ import annotations

import json
import re
from typing import Any

import frappe
from frappe import _
from frappe.utils import getdate, now_datetime, nowdate, add_days

from assetcore.repositories.compliance_repo import (
    CAPARepo,
    ComplianceFindingRepo,
    ComplianceRuleRepo,
    ComplianceScorecardRepo,
    InternalAuditRepo,
    ManagementReviewRepo,
)
from assetcore.services.shared import ErrorCode, ServiceError, normalize_filters
from assetcore.services.shared import rbac
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

    # BR-16-11 — phân nhóm cho compliance-rate (SoT compute_compliance_rate):
    #   non_compliant         = chỉ Confirmed NC
    #   compliant_adjudicated = đã phân định-tuân-thủ (Resolved/Waived/Closed)
    #   pending               = chưa phân định (Open/Under Review) → ngoài mẫu số
    #   excluded              = False Positive (loại từ query filter)
    NON_COMPLIANT = (CONFIRMED_NC,)
    COMPLIANT_ADJUDICATED = (RESOLVED, WAIVED, CLOSED)
    PENDING = (OPEN, UNDER_REVIEW)


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
    # Enrich with asset_name
    for row in rows:
        if row.get("asset"):
            row["asset_name"] = frappe.db.get_value("AC Asset", row["asset"], "asset_name") or ""
    return {"data": rows, "pagination": pg}


def create_finding(rule_ref: str, asset_ref: str, work_order_ref: str,
                   severity: str, description: str,
                   evaluation_date: str = "",
                   actual_value: str = "",
                   threshold_value: str = "") -> dict:
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
        "current_value": actual_value or "",
        "threshold_value": threshold_value or "",
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
    for row in rows:
        if row.get("lead_auditor"):
            row["lead_auditor_name"] = frappe.db.get_value(
                "User", row["lead_auditor"], "full_name"
            ) or row["lead_auditor"]
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

# BR-16-12 — period-anchor canonical: field DUY NHẤT xác định "finding thuộc kỳ
# nào". MỌI view lọc finding theo kỳ (YYYY-MM) PHẢI dùng hằng này, KHÔNG dùng
# ``detected_date`` (Datetime event-timestamp có thể lệch kỳ do lag adjudication).
# Lý do: ``evaluation_date`` (Date) là ngày assessment khớp chu kỳ review tháng
# của Scorecard VÀ là thành phần khóa idempotency
# ``(rule, source_record, evaluation_date)`` = định nghĩa hệ thống. reqd=1 trên
# DocType nên mọi finding luôn có anchor (không cần null-fallback). COALESCE với
# detected_date là OUT-OF-SCOPE (chỉ mở nếu xuất hiện finding evaluation_date NULL).
PERIOD_ANCHOR_FIELD = "evaluation_date"


def _period_bounds(year: int, month: int) -> tuple[str, str]:
    """SoT cho biên kỳ (YYYY-MM) — dùng CHUNG bởi ``generate_scorecard`` VÀ
    ``get_compliance_heatmap`` để 2 view KHÔNG drift lại (chống tái phát
    divergence — gốc bug: bounds duplicate inline ở 2 nơi).

    Trả ``(start, end_inclusive)`` cho filter ``{PERIOD_ANCHOR_FIELD:
    ("between", [start, end_inclusive])}``. Semantics half-open ``[start,
    next_month_start)`` (doc 02:526): ngày đầu kỳ THUỘC, ngày đầu kỳ KẾ KHÔNG
    thuộc. Vì Frappe ``between`` inclusive CẢ 2 đầu, ``end_inclusive`` = NGÀY
    CUỐI tháng (không phải first-of-next-month) → tránh off-by-one cho finding
    rơi đúng ngày 01 của kỳ kế (BR-16-12 / TDD-4).

    - ``start`` = ngày đầu kỳ (``YYYY-MM-01``).
    - ``end_inclusive`` = ngày cuối kỳ (last day of month).
    """
    start = f"{year}-{month:02d}-01"
    # Ngày đầu kỳ kế − 1 ngày = ngày cuối kỳ hiện tại (xử lý tháng 28/29/30/31).
    next_month_start = (f"{year + 1}-01-01" if month == 12
                        else f"{year}-{month + 1:02d}-01")
    end_inclusive = add_days(next_month_start, -1)
    return start, end_inclusive


def compute_compliance_rate(findings: list) -> dict:
    """SoT BR-16-11 cho compliance-rate — dùng CHUNG bởi ``generate_scorecard``
    (scorecard immutable) VÀ ``get_compliance_heatmap`` (matrix Module×Dept) để
    CÙNG dataset cho CÙNG 1 score (không divergence). KHÔNG nhân bản công thức
    ``(total - nc) / total`` inline.

    ``findings`` là list các finding-like (có thuộc tính ``.status``), đã loại
    False Positive từ filter query. Phân loại theo 3 nhóm:

    - ``non_compliant`` = chỉ Confirmed NC.
    - ``compliant``     = đã phân định-tuân-thủ: Resolved | Waived | Closed.
    - ``pending``       = Open | Under Review (chưa phân định) → KHÔNG vào mẫu số.

    Mẫu số ``total_adjudicated = compliant + non_compliant``. ``pending`` báo
    riêng để UX không mất dấu. ``score_pct = round(compliant /
    total_adjudicated * 100, 2)``; nếu ``total_adjudicated == 0`` → ``100.0``
    (giữ semantics 'không có NC xác nhận').

    Trả: ``{total_adjudicated, compliant, non_compliant, pending, score_pct}``.
    """
    compliant = non_compliant = pending = 0
    for f in findings:
        status = f.get("status") if isinstance(f, dict) else getattr(f, "status", None)
        if status in FindingStatus.NON_COMPLIANT:
            non_compliant += 1
        elif status in FindingStatus.COMPLIANT_ADJUDICATED:
            compliant += 1
        elif status in FindingStatus.PENDING:
            pending += 1
        # False Positive (hoặc status lạ) → loại khỏi cả tử lẫn mẫu.

    total_adjudicated = compliant + non_compliant
    score_pct = (round(compliant / total_adjudicated * 100, 2)
                 if total_adjudicated else 100.0)
    return {
        "total_adjudicated": total_adjudicated,
        "compliant": compliant,
        "non_compliant": non_compliant,
        "pending": pending,
        "score_pct": score_pct,
    }


def generate_scorecard(module_ref: str, period: str) -> dict:
    """Tính scorecard tuân thủ theo module và kỳ (YYYY-MM)."""
    try:
        year, month = int(period[:4]), int(period[5:7])
    except (ValueError, IndexError):
        raise ServiceError(ErrorCode.VALIDATION,
                           "Kỳ phải có định dạng YYYY-MM")

    # BR-16-12: dùng CHUNG hằng + helper với get_compliance_heatmap → 2 view
    # KHÔNG drift lại (chống tái phát divergence).
    start, end = _period_bounds(year, month)
    filters: dict = {
        PERIOD_ANCHOR_FIELD: ("between", [start, end]),
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
    # BR-16-11: gọi SoT — pending (Open/Under Review) KHÔNG vào mẫu số.
    rate = compute_compliance_rate(findings)
    non_compliant = rate["non_compliant"]      # chỉ Confirmed NC
    compliant = rate["compliant"]              # adjudicated-compliant
    pending = rate["pending"]
    score_pct = rate["score_pct"]

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
    from assetcore.services.imm00 import _open_capa_filter, _overdue_capa_filter
    # SoT: _open_capa_filter() — scorecard capa_open_count == KPI dashboard.capa_open
    # == quality-dash == aging.total_open, byte-for-byte (status NOT IN Closed; 'Overdue'
    # vẫn đếm vì là open). KHÔNG inline status IN [Open, In Progress, ...] (bỏ sót Overdue).
    open_capas = frappe.db.count("IMM CAPA Record", _open_capa_filter())
    # SoT: _overdue_capa_filter() — scorecard capa_overdue_count khớp KPI/drill byte-for-byte.
    overdue_capas = frappe.db.count("IMM CAPA Record", _overdue_capa_filter())

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
        # BR-16-11: pending báo riêng (runtime only — không có field DocType).
        "pending_count": pending,
        "compliant_count": compliant,
    }


def validate_scorecard_immutability(doc) -> None:
    """VR-09: once published (is_published=1), score_pct and non_compliant_count
    become immutable. Create a new restate_of document to correct errors."""
    if not doc.get("name") or doc.is_new():
        return
    if not doc.get("is_published"):
        return
    try:
        prev = frappe.db.get_value(
            "IMM Compliance Scorecard",
            doc.name,
            ["score_pct", "non_compliant_count", "is_published"],
            as_dict=True,
        )
    except Exception:
        return
    if not prev:
        return
    if not prev.get("is_published"):
        return
    immutable_fields = ("score_pct", "non_compliant_count")
    for fld in immutable_fields:
        if doc.get(fld) != prev.get(fld):
            raise ServiceError(
                ErrorCode.VALIDATION,
                _("Scorecard đã publish — field {0} không thể thay đổi. "
                  "Tạo bản restate_of mới để điều chỉnh.").format(fld),
            )


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
    """Scheduler daily: kiểm tra CAPA quá hạn và escalate.

    SoT: dùng _overdue_capa_filter() (services/imm00) — cùng INVARIANT với KPI/drill/setter.
    """
    from assetcore.services.imm00 import _overdue_capa_filter
    # SoT fields select MỘT lần — fix RC-ESC-4 (N+1): _escalate_capa đọc
    # severity/imm_risk_level/escalation_level TỪ row này, KHÔNG db.get_value riêng.
    overdue = frappe.get_all(
        "IMM CAPA Record",
        filters=_overdue_capa_filter(),
        fields=["name", "responsible", "severity", "imm_risk_level",
                "escalation_level", "due_date", "asset", "description"],
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
    # BR-00-26 (round 12): cổng hiệu quả SoT — fire khi status=='Closed' BẤT KỂ
    # workflow_state (bỏ điều kiện kép cũ 'AND workflow_state==Closed' để mọi đường
    # save-to-Closed: controller UI, set_value submit đều qua cổng). Gọi CÙNG
    # predicate assert_capa_effectiveness_gate (imm00) — KHÔNG inline literal VR-06/07.
    if doc.status == "Closed":
        from assetcore.services.imm00 import assert_capa_effectiveness_gate
        try:
            assert_capa_effectiveness_gate(doc)
        except ServiceError as e:
            # Controller validate semantics: ServiceError → frappe.throw (rollback save).
            frappe.throw(e.message)


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
    """BR-16-09: Cross-module gate.

    Trả về:
      {
        "blocked": bool,
        "asset": str | None,
        "reasons": list[{type, ref, status, workflow_state, message}],
        "active_findings_count": int,
        "active_capas_count": int,
        "blocking_findings": list[str],
      }
    Gọi bởi IMM-04/08/09/13/14 trước khi commission/WO/decommission.
    """
    if not asset:
        return {"blocked": False, "asset": None,
                "active_findings_count": 0, "active_capas_count": 0,
                "blocking_findings": [], "reasons": []}

    # BR-16-09 ENFORCEMENT consumer của SoT capa_open (BR-00-15): membership
    # 'Critical CAPA mở' = is_capa_open ⟺ status NOT IN ('Closed'). 'Overdue' NẰM
    # TRONG tập block → INVARIANT dưới cron check_capa_overdue() flip Open→'Overdue'
    # (gate.blocked bất biến). KHÔNG inline literal IN [Open, In Progress, Pending
    # Verification] (bỏ sót 'Overdue' = lỗ cũ). Lazy import tránh circular (Vòng 10/11).
    from assetcore.services.imm00 import _open_capa_filter
    crit_capas = frappe.get_all(
        "IMM CAPA Record",
        filters={"asset": asset,
                 "imm_risk_level": "Critical",
                 **_open_capa_filter()},
        fields=["name", "status", "workflow_state"],
    )

    active_findings = frappe.get_all(
        ComplianceFindingRepo.DOCTYPE,
        filters={"asset": asset,
                 "status": ("in", list(FindingStatus.ACTIVE)),
                 "severity": ("in", ["High", "Critical"])},
        fields=["name", "severity", "status"],
    )

    reasons: list[dict] = []
    for c in crit_capas:
        reasons.append({
            "type": "CAPA_CRITICAL_OPEN",
            "ref": c["name"],
            "status": c.get("status"),
            "workflow_state": c.get("workflow_state"),
            "message": "CAPA Critical chưa close",
        })

    return {
        "blocked": bool(crit_capas),
        "asset": asset,
        "reasons": reasons,
        "active_findings_count": len(active_findings),
        "active_capas_count": len(crit_capas),
        "blocking_findings": [f["name"] for f in active_findings],
    }


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


# ─── CAPA escalation SoT severity (FIX RC-ESC-2 FIELD-SoT) ───────────────────
_ESC_RISK_VOCAB = ("Low", "Medium", "High", "Critical")  # thang tier escalation


def _severity_to_risk(severity: str | None) -> str:
    """Normalize field `severity` (Minor/Major/Critical) → thang risk tier.
    Minor→Low, Major→High, Critical→Critical. Rỗng/lạ → '' (no signal)."""
    return {"Minor": "Low", "Major": "High", "Critical": "Critical"}.get(
        (severity or "").strip(), "")


def _capa_escalation_severity(row: dict) -> str:
    """SoT effective-risk cho escalation (FIX RC-ESC-2).

    Ưu tiên imm_risk_level KHI nó là tín hiệu thật (High/Critical); ngược lại
    (rỗng / default-noise 'Medium' / 'Low') fall back severity-normalized.
    Trả 1 giá trị trong _ESC_RISK_VOCAB hoặc '' (không escalate).
    Predicate thuần (KHÔNG I/O) — nhận row đã select trong check_capa_due (fix RC-ESC-4)."""
    risk = (row.get("imm_risk_level") or "").strip()
    if risk in ("High", "Critical"):
        return risk                       # imm_risk_level đã là tín hiệu rõ → tin
    sev_risk = _severity_to_risk(row.get("severity"))
    if sev_risk in ("High", "Critical"):
        return sev_risk                   # severity THẬT vượt imm_risk_level default → dùng
    # cả 2 đều ≤ Medium → trả mức cao hơn để minh bạch, nhưng vẫn KHÔNG escalate
    return risk or sev_risk or "Medium"


def _escalate_capa(capa: dict) -> None:
    """Tiered escalation ĐỘC LẬP (FIX RC-ESC-1 TIER) + idempotency (RC-ESC-3).

    Nhận NGUYÊN row từ check_capa_due (severity/imm_risk_level/escalation_level
    đã select sẵn — fix RC-ESC-4 N+1). Tier KHÔNG if/elif loại trừ:
    Critical ≥1d→L1, ≥3d→L1+L2; High ≥3d→L2; Medium/Low→none.
    """
    overdue_days = (getdate(nowdate()) - getdate(capa["due_date"])).days
    if overdue_days < 1:
        return                                   # BVA: 0d → no escalate
    risk = _capa_escalation_severity(capa)        # SoT (FIX RC-ESC-2)
    already = int(capa.get("escalation_level") or 0)  # tier đã gửi (FIX RC-ESC-3)

    # Tính tier ĐÁNG LẼ phải đạt theo (risk × overdue) — ĐỘC LẬP, không elif
    target = 0
    if risk == "Critical":
        if overdue_days >= 1:
            target = max(target, 1)              # Critical ≥1d → Level-1
        if overdue_days >= 3:
            target = max(target, 2)              # Critical ≥3d → Level-2 (KÈM Level-1)
    elif risk == "High":
        if overdue_days >= 3:
            target = max(target, 2)              # High ≥3d → Level-2 (BVA: High <3d no escalate)
    # Medium/Low → target = 0 (KHÔNG escalate bất kỳ ngày — BVA)

    # CHỈ gửi các tier MỚI (level > already) → idempotency (FIX RC-ESC-3)
    for level in range(already + 1, target + 1):
        _send_capa_escalation(capa, level=level)
        _record_capa_escalation(capa, level=level)   # 1 audit record/tier (CLAUDE.md §5)
    if target > already:
        frappe.db.set_value("IMM CAPA Record", capa["name"],
                            "escalation_level", target, update_modified=False)


def _record_capa_escalation(capa: dict, level: int) -> None:
    """Ghi 1 IMM Audit Trail/tier escalation (CLAUDE.md §5 'mọi action có record').

    Best-effort — KHÔNG vỡ luồng cron nếu audit chain fail (INV-CAPA-ESC-3)."""
    try:
        log_audit_event(
            asset=capa.get("asset") or "",
            event_type="CAPA",                  # option hợp lệ sẵn trên IMM Audit Trail
            actor="Administrator",
            ref_doctype="IMM CAPA Record", ref_name=capa["name"],
            change_summary=_("CAPA {0} leo thang Level-{1} (quá hạn)").format(
                capa["name"], level),
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(),
                         f"IMM-16 CAPA escalation audit failed: {capa.get('name')}")


def _send_capa_escalation(capa: dict, level: int) -> None:
    # R21 dead-role fix: nhánh Level-2 lấy người nhận qua SSoT
    # (notify_roles.CAPA_ESCALATION_MANAGER) thay vì raw SQL `tabHas Role` với
    # role-literal hardcode. Mọi truy vấn role->email đi qua helpers._get_role_emails.
    from assetcore.utils.helpers import _get_role_emails, _safe_sendmail
    from assetcore.services.shared import notify_roles
    try:
        recipients = [capa.get("responsible")] if capa.get("responsible") else []
        if level >= 2:
            recipients += _get_role_emails(notify_roles.CAPA_ESCALATION_MANAGER)
        recipients = list(set(filter(None, recipients)))
        if recipients:
            _safe_sendmail(
                recipients=recipients,
                subject=f"[AssetCore] CAPA {capa['name']} quá hạn — Level {level}",
                message=f"CAPA {capa['name']} đã quá hạn. Vui lòng xử lý ngay.",
            )
    except Exception:
        pass


def _require_qa_or_admin() -> None:
    if not rbac.can(_CAP_COMPLIANCE_WRITE):
        raise ServiceError(ErrorCode.FORBIDDEN,
                           "Chỉ Compliance Manager/User mới được thực hiện thao tác này")




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
        recipients = _get_role_emails(["Compliance Manager"])
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
        recipients = _get_role_emails(["Compliance Manager", "PM Manager"])
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


# ════════════════════════════════════════════════════════════════════════════
# Canonical IMM-16 service surface (per docs/imm-16/05_API_Specification.md)
# ════════════════════════════════════════════════════════════════════════════

# Capability gates (Compliance domain) — quyen that do DocPerm quyet dinh.
_CAP_COMPLIANCE_APPROVE = "compliance.submit"  # waive/publish/finalize/close (Manager)
_CAP_COMPLIANCE_WRITE = "compliance.write"     # cap nhat Rule (User+)


# ─── Audit-trail helper (CLAUDE.md §5/§19 — mọi action sinh record) ───────────

def _log_record_event(ref_doctype: str, ref_name: str, event_type: str,
                       change_summary: str, *, asset: str = "",
                       from_status: str | None = None,
                       to_status: str | None = None) -> None:
    """Ghi 1 sự kiện vào IMM Audit Trail cho record IMM-16 (Finding/CAPA/MR/Rule).

    ``asset`` rỗng khi record không gắn thiết bị (audit trail vẫn truy được
    qua ref_doctype/ref_name). Không raise nếu ghi log thất bại — không chặn
    nghiệp vụ chính.
    """
    try:
        log_audit_event(
            asset=asset or "",
            event_type=event_type,
            actor=frappe.session.user,
            ref_doctype=ref_doctype,
            ref_name=ref_name,
            change_summary=change_summary,
            from_status=from_status,
            to_status=to_status,
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(),
                         f"IMM-16 audit trail failed for {ref_doctype} {ref_name}")


def get_record_history(ref_doctype: str, ref_name: str,
                       limit: int = 50) -> dict:
    """Trả lịch sử audit-trail của 1 record IMM-16 theo ref_doctype/ref_name.

    Dùng cho phần "Lịch sử" ở các trang chi tiết Finding / CAPA / MR / Rule.
    """
    if not ref_doctype or not ref_name:
        raise ServiceError(ErrorCode.VALIDATION,
                           "ref_doctype và ref_name là bắt buộc")
    rows = frappe.get_all(
        "IMM Audit Trail",
        filters={"ref_doctype": ref_doctype, "ref_name": ref_name},
        fields=["name", "event_type", "timestamp", "actor",
                "from_status", "to_status", "change_summary"],
        order_by="timestamp desc",
        limit_page_length=int(limit),
    )
    for r in rows:
        if r.get("actor"):
            r["actor_name"] = frappe.db.get_value(
                "User", r["actor"], "full_name") or r["actor"]
    return {"items": rows, "total": len(rows)}


# ─── Compliance Rule (canonical) ─────────────────────────────────────────────

def get_rule(name: str) -> dict:
    """Chi tiết Compliance Rule."""
    doc = ComplianceRuleRepo.get(name)
    if not doc:
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy Rule: {name}")
    return doc.as_dict()


def update_rule(name: str, rule_data: dict, change_summary: str = "") -> dict:
    """VR-11: enforce change_summary nếu threshold/severity đổi; bump version."""
    if not rbac.can(_CAP_COMPLIANCE_WRITE):
        raise ServiceError(ErrorCode.FORBIDDEN, "Không có quyền cập nhật Rule")

    doc = ComplianceRuleRepo.get(name)
    if not doc:
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy Rule: {name}")

    rule_data = rule_data or {}
    sensitive_changed = (
        ("threshold_definition" in rule_data and
         rule_data.get("threshold_definition") != doc.threshold_definition)
        or ("severity" in rule_data and
            rule_data.get("severity") != doc.severity)
    )
    if sensitive_changed and not (change_summary or "").strip():
        raise ServiceError("FIN-011",
                           "VR-11: Phải nhập change_summary khi đổi threshold/severity")

    previous_version = doc.version or "1.0"
    for field, val in rule_data.items():
        if hasattr(doc, field):
            setattr(doc, field, val)
    if sensitive_changed:
        try:
            major, minor = previous_version.split(".")
            doc.version = f"{major}.{int(minor) + 1}"
        except Exception:
            doc.version = "1.1"
        doc.previous_version = previous_version
        doc.change_summary = change_summary
    ComplianceRuleRepo.save(doc)
    _log_record_event(
        ComplianceRuleRepo.DOCTYPE, doc.name, "Document",
        (f"Rule {doc.name}: cập nhật"
         + (f" — version {previous_version} → {doc.version}: {change_summary}"
            if sensitive_changed else "")),
    )
    frappe.db.commit()
    return {"name": doc.name, "version": doc.version,
            "previous_version": previous_version}


def deactivate_rule(name: str) -> dict:
    """Deactivate Rule (set is_active=0)."""
    if not rbac.can(_CAP_COMPLIANCE_WRITE):
        raise ServiceError(ErrorCode.FORBIDDEN, "Không có quyền deactivate Rule")
    if not ComplianceRuleRepo.exists(name):
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy Rule: {name}")
    frappe.db.set_value(ComplianceRuleRepo.DOCTYPE, name, "is_active", 0)
    _log_record_event(
        ComplianceRuleRepo.DOCTYPE, name, "Document",
        f"Rule {name}: ngừng áp dụng (deactivate)",
        to_status="Inactive",
    )
    frappe.db.commit()
    return {"name": name, "is_active": 0}


def reactivate_rule(name: str) -> dict:
    """Kích hoạt lại Rule đã deactivate (set is_active=1). BUG-16-02."""
    if not rbac.can(_CAP_COMPLIANCE_WRITE):
        raise ServiceError(ErrorCode.FORBIDDEN, "Không có quyền kích hoạt Rule")
    if not ComplianceRuleRepo.exists(name):
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy Rule: {name}")
    frappe.db.set_value(ComplianceRuleRepo.DOCTYPE, name, "is_active", 1)
    _log_record_event(
        ComplianceRuleRepo.DOCTYPE, name, "Document",
        f"Rule {name}: kích hoạt lại (reactivate)",
        to_status="Active",
    )
    frappe.db.commit()
    return {"name": name, "is_active": 1}


# ─── Finding (canonical) ─────────────────────────────────────────────────────

def get_finding(name: str) -> dict:
    doc = ComplianceFindingRepo.get(name)
    if not doc:
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy Finding: {name}")
    data = doc.as_dict()
    if data.get("asset"):
        data["asset_name"] = frappe.db.get_value("AC Asset", data["asset"], "asset_name") or ""
    # BUG-16-04: resolve responsible_dept code -> readable name.
    if data.get("responsible_dept"):
        data["responsible_dept_name"] = frappe.db.get_value(
            "AC Department", data["responsible_dept"], "department_name"
        ) or data["responsible_dept"]
    if data.get("rule"):
        data["rule_name"] = frappe.db.get_value(
            ComplianceRuleRepo.DOCTYPE, data["rule"], "rule_name"
        ) or data["rule"]
    return data


def confirm_finding(name: str, reviewer_note: str = "") -> dict:
    _require_qa_or_admin()
    doc = ComplianceFindingRepo.get(name)
    if not doc:
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy Finding: {name}")
    if doc.status not in FindingStatus.ACTIVE:
        raise ServiceError(ErrorCode.BAD_STATE,
                           f"Finding đã ở trạng thái: {doc.status}")
    prev_status = doc.status
    doc.status = FindingStatus.CONFIRMED_NC
    doc.reviewer = frappe.session.user
    doc.review_date = now_datetime()
    if reviewer_note:
        doc.notes = (doc.notes or "") + f"\n[Confirmed] {reviewer_note}"
    ComplianceFindingRepo.save(doc)
    _log_record_event(
        ComplianceFindingRepo.DOCTYPE, name, "Audit",
        f"Finding {name}: xác nhận NC",
        asset=doc.asset or "",
        from_status=prev_status, to_status=FindingStatus.CONFIRMED_NC,
    )
    frappe.db.commit()
    return {"name": name, "status": FindingStatus.CONFIRMED_NC}


def mark_false_positive(name: str, reason: str) -> dict:
    _require_qa_or_admin()
    if not (reason or "").strip():
        raise ServiceError(ErrorCode.VALIDATION,
                           "Phải nhập lý do mark False Positive")
    doc = ComplianceFindingRepo.get(name)
    if not doc:
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy Finding: {name}")
    prev = doc.status
    doc.status = FindingStatus.FALSE_POSITIVE
    doc.reviewer = frappe.session.user
    doc.review_date = now_datetime()
    doc.notes = (doc.notes or "") + f"\n[False Positive] {reason}"
    ComplianceFindingRepo.save(doc)
    _log_record_event(
        ComplianceFindingRepo.DOCTYPE, name, "Audit",
        f"Finding {name}: đánh dấu sai — {reason}",
        asset=doc.asset or "", from_status=prev,
        to_status=FindingStatus.FALSE_POSITIVE,
    )
    frappe.db.commit()
    return {"name": name, "status": FindingStatus.FALSE_POSITIVE}


def waive_finding(name: str, waiver_reason: str,
                  waiver_evidence: str = "",
                  waiver_expiry: str = "") -> dict:
    """BR-16-06 + VR-04."""
    if not rbac.can(_CAP_COMPLIANCE_APPROVE):
        raise ServiceError("FIN-006",
                           "Chỉ Compliance Manager mới được phép waive")
    if not waiver_reason or len(waiver_reason.strip()) < 50:
        raise ServiceError("FIN-004",
                           "VR-04: waiver_reason phải >= 50 ký tự")
    if not waiver_evidence:
        raise ServiceError("FIN-004", "VR-04: waiver_evidence là bắt buộc")
    if not waiver_expiry or getdate(waiver_expiry) <= getdate(nowdate()):
        raise ServiceError("FIN-004",
                           "VR-04: waiver_expiry phải sau hôm nay")

    doc = ComplianceFindingRepo.get(name)
    if not doc:
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy Finding: {name}")
    prev = doc.status
    doc.status = FindingStatus.WAIVED
    doc.waiver_reason = waiver_reason
    doc.waiver_evidence = waiver_evidence
    doc.waiver_expiry = waiver_expiry
    doc.reviewer = frappe.session.user
    doc.review_date = now_datetime()
    ComplianceFindingRepo.save(doc)
    _log_record_event(
        ComplianceFindingRepo.DOCTYPE, name, "Audit",
        f"Finding {name}: miễn áp dụng — hết hạn {waiver_expiry}",
        asset=doc.asset or "", from_status=prev,
        to_status=FindingStatus.WAIVED,
    )
    frappe.db.commit()
    return {"name": name, "status": FindingStatus.WAIVED}


def link_finding_to_capa(name: str, capa_ref: str) -> dict:
    _require_qa_or_admin()
    doc = ComplianceFindingRepo.get(name)
    if not doc:
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy Finding: {name}")
    if not CAPARepo.exists(capa_ref):
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy CAPA: {capa_ref}")
    doc.capa_ref = capa_ref
    ComplianceFindingRepo.save(doc)
    _log_record_event(
        ComplianceFindingRepo.DOCTYPE, name, "Audit",
        f"Finding {name}: liên kết CAPA {capa_ref}",
        asset=doc.asset or "",
    )
    frappe.db.commit()
    return {"name": name, "capa_ref": capa_ref}


# ─── Internal Audit (canonical) ──────────────────────────────────────────────

def get_audit(name: str) -> dict:
    doc = InternalAuditRepo.get(name)
    if not doc:
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy Audit: {name}")
    data = doc.as_dict()
    if data.get("lead_auditor"):
        data["lead_auditor_name"] = frappe.db.get_value(
            "User", data["lead_auditor"], "full_name"
        ) or data["lead_auditor"]
    return data


def create_audit(audit_data: dict) -> dict:
    return create_internal_audit(audit_data)


def start_audit(name: str) -> dict:
    _require_qa_or_admin()
    doc = InternalAuditRepo.get(name)
    if not doc:
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy Audit: {name}")
    if doc.status != AuditStatus.PLANNED:
        raise ServiceError(ErrorCode.BAD_STATE,
                           f"Audit phải ở trạng thái Planned, hiện: {doc.status}")
    doc.status = AuditStatus.IN_PROGRESS
    doc.actual_start = nowdate()
    InternalAuditRepo.save(doc)
    frappe.db.commit()
    return {"name": name, "status": AuditStatus.IN_PROGRESS,
            "actual_start": doc.actual_start}


def complete_audit_checklist(audit_name: str, items: list[dict]) -> dict:
    """§3.3.4: Update checklist items + auto-sinh Finding cho Major/Minor NC."""
    _require_qa_or_admin()
    doc = InternalAuditRepo.get(audit_name)
    if not doc:
        raise ServiceError(ErrorCode.NOT_FOUND,
                           f"Không tìm thấy Audit: {audit_name}")
    if doc.status not in (AuditStatus.IN_PROGRESS, AuditStatus.PLANNED):
        raise ServiceError(ErrorCode.BAD_STATE,
                           f"Audit ở trạng thái {doc.status} — không thể nhập checklist")

    findings_created = 0
    items = items or []
    # Build idx -> payload map
    payload_map = {int(it.get("idx", 0)): it for it in items if it.get("idx")}

    for child in (doc.checklist_items or []):
        payload = payload_map.get(int(child.idx))
        if not payload:
            continue
        finding_status = payload.get("finding_status")
        if hasattr(child, "finding_status"):
            child.finding_status = finding_status
        if hasattr(child, "notes"):
            child.notes = payload.get("notes", "")
        if hasattr(child, "clause_ref"):
            child.clause_ref = payload.get("clause_ref", "")

        if finding_status in ("Major NC", "Minor NC"):
            severity = "High" if finding_status == "Major NC" else "Medium"
            try:
                finding_doc = ComplianceFindingRepo.create({
                    "rule": getattr(child, "rule_ref", "") or "",
                    "source_record_doctype": InternalAuditRepo.DOCTYPE,
                    "source_record": doc.name,
                    "detected_date": now_datetime(),
                    "severity": severity,
                    "status": FindingStatus.OPEN,
                    "evaluation_date": nowdate(),
                    "notes": payload.get("notes", ""),
                })
                if hasattr(child, "linked_finding"):
                    child.linked_finding = finding_doc.name
                findings_created += 1
            except Exception:
                frappe.log_error(frappe.get_traceback(),
                                 "IMM-16 complete_audit_checklist: finding create failed")

    doc.findings_count = (doc.findings_count or 0) + findings_created
    InternalAuditRepo.save(doc)
    frappe.db.commit()
    return {"audit_name": audit_name, "items_count": len(items),
            "findings_created": findings_created}


def close_audit(name: str, audit_report: str = "") -> dict:
    """§3.3.5: VR-08 enforce — block nếu còn Major NC chưa CAPA."""
    if not rbac.can(_CAP_COMPLIANCE_APPROVE):
        raise ServiceError(ErrorCode.FORBIDDEN, "Không có quyền đóng Audit")

    doc = InternalAuditRepo.get(name)
    if not doc:
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy Audit: {name}")
    if doc.status == AuditStatus.CLOSED:
        raise ServiceError(ErrorCode.BAD_STATE, "Audit đã đóng")

    # VR-08: block if any Major NC finding without CAPA link
    open_major = frappe.get_all(
        ComplianceFindingRepo.DOCTYPE,
        filters={
            "source_record_doctype": InternalAuditRepo.DOCTYPE,
            "source_record": name,
            "severity": ("in", ["High", "Critical"]),
            "capa_ref": ("in", ["", None]),
            "status": ("in", list(FindingStatus.ACTIVE)),
        },
        pluck="name",
    )
    if open_major:
        raise ServiceError("FIN-008",
                           f"VR-08: Còn {len(open_major)} Major NC chưa link CAPA: "
                           f"{', '.join(open_major[:3])}")

    doc.status = AuditStatus.CLOSED
    doc.actual_end = nowdate()
    if audit_report:
        doc.audit_report = audit_report
    InternalAuditRepo.save(doc)
    frappe.db.commit()
    return {"name": name, "status": AuditStatus.CLOSED,
            "actual_end": doc.actual_end}


# ─── CAPA (canonical) ─────────────────────────────────────────────────────────

def create_capa_from_incident(incident_name: str,
                               rca_name: str = "",
                               severity_override: str = "",
                               responsible: str = "",
                               due_days: int = 30) -> dict:
    """Tạo CAPA từ Incident Report (idempotent — re-use linked_capa nếu đã có).

    Wired từ:
      - IMM-12 RCA on_submit (RC-03 fix) → mọi RCA completed sinh CAPA.
      - imm12.submit_rca() service path (đã có sẵn).

    2-way link:
      - CAPA.linked_incident = incident_name
      - CAPA.source_type/source_ref = (Incident Report / incident_name)
      - Incident.linked_capa = capa_name
      - RCA.linked_capa = capa_name (nếu rca_name truyền vào)

    Trả về: {"capa_name", "incident_name", "rca_name", "reused": bool}
    """
    incident = frappe.db.get_value(
        "Incident Report", incident_name,
        ["name", "asset", "severity", "description", "linked_capa", "fault_code"],
        as_dict=True,
    )
    if not incident:
        raise ServiceError(ErrorCode.NOT_FOUND,
                           f"Không tìm thấy Incident: {incident_name}")

    # Idempotent: nếu Incident đã có CAPA hợp lệ → reuse
    if incident.linked_capa and frappe.db.exists("IMM CAPA Record", incident.linked_capa):
        # Bảo đảm 2-way link RCA → CAPA nếu có rca_name
        if rca_name and frappe.db.exists("IMM RCA Record", rca_name):
            cur = frappe.db.get_value("IMM RCA Record", rca_name, "linked_capa")
            if not cur:
                frappe.db.set_value("IMM RCA Record", rca_name,
                                    "linked_capa", incident.linked_capa)
        # Bảo đảm linked_incident chỉ ra incident
        cur_inc = frappe.db.get_value("IMM CAPA Record", incident.linked_capa,
                                       "linked_incident")
        if not cur_inc:
            frappe.db.set_value("IMM CAPA Record", incident.linked_capa,
                                "linked_incident", incident_name)
        return {"capa_name": incident.linked_capa, "incident_name": incident_name,
                "rca_name": rca_name, "reused": True}

    # Map severity: Incident (Low/Medium/High/Critical) → CAPA (Minor/Major/Critical)
    sev = severity_override or incident.severity or "High"
    capa_severity = _map_severity(sev) if sev != "Critical" else "Critical"

    description_parts = [f"[IMM-12 RCA→CAPA] Incident {incident_name}"]
    if rca_name:
        description_parts.append(f"RCA: {rca_name}")
    if incident.fault_code:
        description_parts.append(f"Fault code: {incident.fault_code}")
    if incident.description:
        description_parts.append((incident.description or "")[:300])
    capa_description = " | ".join(description_parts)

    from assetcore.services.imm00 import create_capa
    capa_name = create_capa(
        asset=incident.asset or "",
        source_type="Incident Report",
        source_ref=incident_name,
        severity=capa_severity,
        description=capa_description,
        responsible=responsible or frappe.session.user,
        due_days=due_days,
    )

    # 2-way link
    frappe.db.set_value("IMM CAPA Record", capa_name,
                        "linked_incident", incident_name)
    frappe.db.set_value("Incident Report", incident_name,
                        "linked_capa", capa_name)
    if rca_name and frappe.db.exists("IMM RCA Record", rca_name):
        frappe.db.set_value("IMM RCA Record", rca_name,
                            "linked_capa", capa_name)

    _log_record_event(
        "IMM CAPA Record", capa_name, "CAPA",
        f"CAPA {capa_name} tạo từ Incident {incident_name}"
        + (f" (RCA {rca_name})" if rca_name else ""),
        asset=incident.asset or "", to_status="Open",
    )
    frappe.db.commit()
    return {"capa_name": capa_name, "incident_name": incident_name,
            "rca_name": rca_name, "reused": False}


def create_capa_from_finding(finding_name: str,
                              imm_risk_level: str = "Medium",
                              imm_root_cause_method: str = "",
                              responsible: str = "",
                              due_date: str = "") -> dict:
    """§3.4.1: Tạo CAPA từ Finding, link 2-way."""
    _require_qa_or_admin()
    finding = ComplianceFindingRepo.get(finding_name)
    if not finding:
        raise ServiceError(ErrorCode.NOT_FOUND,
                           f"Không tìm thấy Finding: {finding_name}")

    from assetcore.services.imm00 import create_capa
    capa_name = create_capa(
        asset=finding.asset or "",
        source_type="IMM Compliance Finding",
        source_ref=finding_name,
        severity=_map_severity(finding.severity or "Medium"),
        description=f"[IMM-16] Finding {finding_name}: {finding.notes or ''}",
        responsible=responsible or frappe.session.user,
    )

    # Set IMM-16 specific custom fields
    update: dict = {
        "imm_compliance_finding_ref": finding_name,
        "imm_risk_level": imm_risk_level,
    }
    if imm_root_cause_method:
        update["imm_root_cause_method"] = imm_root_cause_method
    if responsible:
        update["responsible"] = responsible
    if due_date:
        update["due_date"] = due_date
    for k, v in update.items():
        try:
            frappe.db.set_value("IMM CAPA Record", capa_name, k, v)
        except Exception:
            pass

    # Link finding → capa
    ComplianceFindingRepo.set_values(finding_name, {"capa_ref": capa_name})
    _log_record_event(
        "IMM CAPA Record", capa_name, "CAPA",
        f"CAPA {capa_name} tạo từ Finding {finding_name}",
        asset=finding.asset or "", to_status="Open",
    )
    _log_record_event(
        ComplianceFindingRepo.DOCTYPE, finding_name, "Audit",
        f"Finding {finding_name}: liên kết CAPA {capa_name}",
        asset=finding.asset or "",
    )
    frappe.db.commit()
    return {"capa_name": capa_name, "finding_name": finding_name,
            "workflow_state": "Open"}


def get_capa(name: str) -> dict:
    """Chi tiết CAPA cho trang lifecycle IMM-16 (BUG-16-08).

    Enrich asset_name, responsible_name, và link Finding nguồn.
    """
    if not CAPARepo.exists(name):
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy CAPA: {name}")
    data = frappe.get_doc("IMM CAPA Record", name).as_dict()
    if data.get("asset"):
        data["asset_name"] = frappe.db.get_value(
            "AC Asset", data["asset"], "asset_name") or ""
    if data.get("responsible"):
        data["responsible_name"] = frappe.db.get_value(
            "User", data["responsible"], "full_name") or data["responsible"]
    finding_ref = data.get("imm_compliance_finding_ref")
    if not finding_ref and data.get("source_type") == "IMM Compliance Finding":
        finding_ref = data.get("source_ref")
    if finding_ref and frappe.db.exists(
            ComplianceFindingRepo.DOCTYPE, finding_ref):
        data["finding_ref"] = finding_ref
        data["finding_rule"] = frappe.db.get_value(
            ComplianceFindingRepo.DOCTYPE, finding_ref, "rule") or ""

    # B-IMM16-2 (2026-05-26): enrich linked_incident / source_ref khi nguồn là Incident
    incident_ref = data.get("linked_incident")
    if not incident_ref and data.get("source_type") == "Incident Report":
        incident_ref = data.get("source_ref")
    if incident_ref and frappe.db.exists("Incident Report", incident_ref):
        data["incident_ref"] = incident_ref
        desc = frappe.db.get_value(
            "Incident Report", incident_ref, "description") or ""
        # truncate dài mô tả cho UI hiển thị inline
        data["incident_subject"] = (desc[:120] + "…") if len(desc) > 120 else desc
    return data


def update_capa_fields(name: str, data: dict | None = None) -> dict:
    """Cập nhật nội dung CAPA (root cause, corrective/preventive action...).

    Cho phép biên tập narrative fields ở các state chưa Closed — tách khỏi
    state-machine của :func:`advance_capa_state`.
    """
    _require_qa_or_admin()
    data = data or {}
    if not CAPARepo.exists(name):
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy CAPA: {name}")
    doc = frappe.get_doc("IMM CAPA Record", name)
    if doc.workflow_state == "Closed":
        raise ServiceError(ErrorCode.BAD_STATE,
                           "CAPA đã Closed — không thể sửa nội dung")
    EDITABLE = ("description", "root_cause", "corrective_action",
                "preventive_action", "imm_root_cause_method",
                "imm_risk_level", "responsible", "due_date",
                "verification_notes")
    changed = []
    for field in EDITABLE:
        if field in data and hasattr(doc, field):
            setattr(doc, field, data[field])
            changed.append(field)
    doc.save(ignore_permissions=True)
    _log_record_event(
        "IMM CAPA Record", name, "CAPA",
        f"CAPA {name}: cập nhật nội dung ({', '.join(changed) or 'none'})",
        asset=doc.asset or "",
    )
    frappe.db.commit()
    return {"name": name, "updated_fields": changed,
            "workflow_state": doc.workflow_state}


_CAPA_TRANSITIONS = {
    "Open": {"Investigating"},
    "Investigating": {"Action Plan"},
    "Action Plan": {"Implementation"},
    "Implementation": {"Verification"},
    "Verification": {"Closed", "Re-opened"},
    "Re-opened": {"Investigating"},
}


def advance_capa_state(name: str, target_state: str,
                       payload: dict | None = None) -> dict:
    """§3.4.2: state-machine + VR-05/06/07/12 enforcement."""
    _require_qa_or_admin()
    payload = payload or {}
    if not CAPARepo.exists(name):
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy CAPA: {name}")
    doc = frappe.get_doc("IMM CAPA Record", name)

    current = doc.workflow_state or "Open"
    allowed = _CAPA_TRANSITIONS.get(current, set())
    if target_state not in allowed:
        raise ServiceError("INVALID_STATE",
                           f"Không thể chuyển từ {current} sang {target_state}")

    # State-specific validations
    if target_state == "Action Plan":
        method = payload.get("imm_root_cause_method") or getattr(doc, "imm_root_cause_method", "")
        if not method:
            raise ServiceError("FIN-005",
                               "VR-05: Phải chọn imm_root_cause_method")
        due = payload.get("due_date") or doc.due_date
        if not due or getdate(due) <= getdate(nowdate()):
            raise ServiceError("FIN-012",
                               "VR-12: due_date phải sau hôm nay")
        if method:
            doc.imm_root_cause_method = method
        if due:
            doc.due_date = due

    if target_state == "Implementation":
        action_plan = getattr(doc, "imm_action_plan", None) or []
        for row in action_plan:
            if not getattr(row, "owner", None) or not getattr(row, "planned_date", None):
                raise ServiceError(ErrorCode.VALIDATION,
                                   "Tất cả action plan rows phải có owner + planned_date")

    if target_state == "Verification":
        action_plan = getattr(doc, "imm_action_plan", None) or []
        for row in action_plan:
            if getattr(row, "status", "") != "Done":
                raise ServiceError(ErrorCode.VALIDATION,
                                   "Tất cả action plan rows phải status=Done")

    if target_state == "Closed":
        # BR-00-26 (round 12): cổng hiệu quả SoT — gọi CÙNG predicate với close_capa
        # (legacy) + capa_record_validate. Xoá literal VR-06/VR-07 trùng (1 SoT).
        from assetcore.services.imm00 import assert_capa_effectiveness_gate
        assert_capa_effectiveness_gate(doc)

    doc.workflow_state = target_state
    if target_state == "Closed":
        doc.status = "Closed"
        if not doc.closed_date:
            doc.closed_date = nowdate()
    elif target_state in ("Investigating", "Action Plan", "Implementation", "Verification"):
        doc.status = "In Progress"
    doc.save(ignore_permissions=True)
    _log_record_event(
        "IMM CAPA Record", name, "CAPA",
        f"CAPA {name}: {current} → {target_state}",
        asset=doc.asset or "",
        from_status=current, to_status=target_state,
    )
    frappe.db.commit()
    return {"name": name, "workflow_state": target_state,
            "status": doc.status}


def perform_effectiveness_check(name: str, result: str,
                                 effectiveness_evidence: str = "") -> dict:
    """§3.4.3: Effective → Close; Not Effective → Re-open + counter++.

    Effectiveness evidence is persisted on BOTH outcomes — the Effective
    (Close) branch and the Not/Partially Effective (Re-open) branch — so the
    effectiveness check always retains its supporting evidence for the audit
    trail (NĐ98/ISO 13485 §8.5.2). Empty evidence is never written (the field
    is left untouched), matching the historical Re-open guard.
    """
    _require_qa_or_admin()
    if result not in ("Effective", "Partially Effective", "Not Effective"):
        raise ServiceError(ErrorCode.VALIDATION,
                           "result phải là Effective/Partially Effective/Not Effective")
    if not CAPARepo.exists(name):
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy CAPA: {name}")
    reopen_count = int(frappe.db.get_value("IMM CAPA Record", name,
                                           "imm_reopen_count") or 0)
    if result == "Effective":
        patch: dict = {
            "effectiveness_check": result,
            "workflow_state": "Closed",
            "status": "Closed",
            "closed_date": nowdate(),
        }
        new_state = "Closed"
    else:
        # Workflow: Verification → Re-opened (next manual step → Investigating).
        reopen_count += 1
        patch = {
            "effectiveness_check": result,
            "workflow_state": "Re-opened",
            "status": "In Progress",
            "imm_reopen_count": reopen_count,
        }
        new_state = "Re-opened"
    # Persist evidence for EVERY outcome (single source of truth) — only when
    # supplied, so an empty value never clobbers an existing reference.
    if effectiveness_evidence:
        patch["imm_effectiveness_evidence"] = effectiveness_evidence
    # Use set_value to bypass Frappe's workflow transition guard — the service
    # is the authoritative state machine; workflow state is set programmatically.
    frappe.db.set_value("IMM CAPA Record", name, patch, update_modified=True)
    _log_record_event(
        "IMM CAPA Record", name, "CAPA",
        f"CAPA {name}: effectiveness check = {result} → {new_state}",
        asset=frappe.db.get_value("IMM CAPA Record", name, "asset") or "",
        from_status="Verification", to_status=new_state,
    )
    frappe.db.commit()
    return {"name": name, "new_state": new_state, "imm_reopen_count": reopen_count}


def reopen_capa(name: str, reason: str = "") -> dict:
    _require_qa_or_admin()
    if not CAPARepo.exists(name):
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy CAPA: {name}")
    doc = frappe.get_doc("IMM CAPA Record", name)
    doc.workflow_state = "Re-opened"
    doc.status = "In Progress"
    if hasattr(doc, "imm_reopen_count"):
        doc.imm_reopen_count = int(getattr(doc, "imm_reopen_count", 0) or 0) + 1
    if reason:
        doc.notes = (doc.notes or "") + f"\n[Reopen] {reason}"
    doc.save(ignore_permissions=True)
    _log_record_event(
        "IMM CAPA Record", name, "CAPA",
        f"CAPA {name}: mở lại — {reason or 'không nêu lý do'}",
        asset=doc.asset or "", to_status="Re-opened",
    )
    frappe.db.commit()
    return {"name": name, "workflow_state": "Re-opened"}


# ─── Scorecard (canonical) ───────────────────────────────────────────────────

def list_scorecards(filters: dict, *, page: int = 1, page_size: int = 20) -> dict:
    rows, pg = ComplianceScorecardRepo.list(
        filters=normalize_filters(filters),
        fields=["name", "period_year", "period_month", "scope", "score_pct",
                "is_published", "capa_open_count", "capa_overdue_count",
                "trend_vs_prev_month"],
        order_by="period_year desc, period_month desc",
        page=page, page_size=page_size,
    )
    return {"items": rows, "pagination": pg}


def get_current_scorecard(scope: str = "Hospital") -> dict:
    from frappe.utils import getdate
    today = getdate(nowdate())
    return get_scorecard_by_period(today.year, today.month, scope)


def get_scorecard_by_period(year: int, month: int, scope: str = "Hospital") -> dict:
    sc = ComplianceScorecardRepo.find_one(
        {"period_year": int(year), "period_month": int(month), "scope": scope},
        fields=["name"],
    )
    if not sc:
        return {"exists": False, "period_year": year, "period_month": month}
    doc = frappe.get_doc(ComplianceScorecardRepo.DOCTYPE, sc["name"])
    return doc.as_dict()


def publish_scorecard(name: str) -> dict:
    """§3.5.4: VR-09 immutable; VR-10 gate quý trước phải có MR Closed."""
    if not rbac.can(_CAP_COMPLIANCE_APPROVE):
        raise ServiceError(ErrorCode.FORBIDDEN, "Không có quyền publish Scorecard")
    doc = ComplianceScorecardRepo.get(name)
    if not doc:
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy Scorecard: {name}")
    if doc.is_published:
        raise ServiceError("FIN-009", "VR-09: Scorecard đã được publish")

    # VR-10 — quý trước phải có MR Closed
    pm, py = doc.period_month, doc.period_year
    prev_q = ((pm - 1) // 3)  # 0..3 — previous quarter index
    if prev_q == 0:
        prev_q_label = f"Q4-{py - 1}"
    else:
        prev_q_label = f"Q{prev_q}-{py}"
    has_mr = frappe.db.exists("IMM Management Review",
                               {"quarter": prev_q_label, "status": "Closed"})
    if not has_mr:
        raise ServiceError("FIN-010",
                           f"VR-10: Quý trước ({prev_q_label}) thiếu Management Review Closed")

    doc.is_published = 1
    doc.published_at = now_datetime()
    doc.approved_by_for_review = frappe.session.user
    ComplianceScorecardRepo.save(doc)
    frappe.db.commit()
    return {"name": name, "is_published": 1,
            "published_at": str(doc.published_at),
            "approved_by_for_review": doc.approved_by_for_review}


# ─── Management Review (canonical) ───────────────────────────────────────────

def list_management_reviews(filters: dict, *, page: int = 1,
                             page_size: int = 20) -> dict:
    rows, pg = ManagementReviewRepo.list(
        filters=normalize_filters(filters),
        fields=["name", "quarter", "review_date", "chair", "status",
                "scorecard_ref", "next_review_date"],
        order_by="review_date desc",
        page=page, page_size=page_size,
    )
    sc_ids = list({r["scorecard_ref"] for r in rows if r.get("scorecard_ref")})
    sc_map: dict[str, dict] = {}
    if sc_ids:
        for s in frappe.get_all(
            ComplianceScorecardRepo.DOCTYPE,
            filters={"name": ("in", sc_ids)},
            fields=["name", "score_pct", "period_year", "period_month"],
        ):
            sc_map[s.name] = s
    for row in rows:
        if row.get("chair"):
            row["chair_name"] = frappe.db.get_value(
                "User", row["chair"], "full_name"
            ) or row["chair"]
        sc = sc_map.get(row.get("scorecard_ref"))
        if sc:
            row["scorecard_score_pct"] = sc.score_pct
            row["scorecard_period"] = f"{sc.period_month:02d}/{sc.period_year}"
    return {"items": rows, "pagination": pg}


def get_management_review(name: str) -> dict:
    doc = ManagementReviewRepo.get(name)
    if not doc:
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy MR: {name}")
    data = doc.as_dict()
    if data.get("chair"):
        data["chair_name"] = frappe.db.get_value(
            "User", data["chair"], "full_name"
        ) or data["chair"]
    # BUG-16-10: enrich scorecard link so FE can show score instead of "—".
    if data.get("scorecard_ref"):
        sc = frappe.db.get_value(
            ComplianceScorecardRepo.DOCTYPE, data["scorecard_ref"],
            ["score_pct", "period_year", "period_month", "is_published"],
            as_dict=True,
        )
        if sc:
            data["scorecard_score_pct"] = sc.score_pct
            data["scorecard_period"] = f"{sc.period_month:02d}/{sc.period_year}"
            data["scorecard_published"] = sc.is_published
    for att in (data.get("attendees") or []):
        if att.get("user"):
            att["user_name"] = frappe.db.get_value(
                "User", att["user"], "full_name") or att["user"]
    for oa in (data.get("output_actions") or []):
        if oa.get("responsible"):
            oa["responsible_name"] = frappe.db.get_value(
                "User", oa["responsible"], "full_name") or oa["responsible"]
    return data


_QUARTER_RE = re.compile(r"^Q[1-4]-\d{4}$")


def _compute_quarter_from_date(d: Any) -> str:
    """Derive ``Q[1-4]-YYYY`` from a date-like value."""
    gd = getdate(d)
    q = (gd.month - 1) // 3 + 1
    return f"Q{q}-{gd.year}"


def _find_scorecard_for_quarter(quarter: str, scope: str = "Hospital") -> str | None:
    """BUG-017: tìm Compliance Scorecard mới nhất khớp quý MR.

    Quarter format ``Q[1-4]-YYYY``. Scorecard có period_month/year nên ta map:
    Q1 → tháng 1..3, Q2 → 4..6, Q3 → 7..9, Q4 → 10..12. Ưu tiên scorecard
    đã publish, sau đó tới tháng cao nhất trong quý.
    """
    if not quarter or not _QUARTER_RE.match(str(quarter)):
        return None
    try:
        q_idx = int(quarter[1])
        year = int(quarter.split("-", 1)[1])
    except (ValueError, IndexError):
        return None
    months = list(range((q_idx - 1) * 3 + 1, q_idx * 3 + 1))
    rows = frappe.get_all(
        ComplianceScorecardRepo.DOCTYPE,
        filters={
            "period_year": year,
            "period_month": ("in", months),
            "scope": scope,
        },
        fields=["name", "period_month", "is_published"],
        order_by="is_published desc, period_month desc",
        limit=1,
    )
    return rows[0]["name"] if rows else None


def create_management_review(data: dict) -> dict:
    if not rbac.can(_CAP_COMPLIANCE_APPROVE):
        raise ServiceError(ErrorCode.FORBIDDEN, "Không có quyền tạo Management Review")
    data.setdefault("status", "Draft")
    data.setdefault("review_date", nowdate())

    # Always re-compute quarter from review_date (override user input).
    # If user supplied quarter, validate format + plausible year window
    # before discarding it, so callers learn about bad input.
    review_date = data["review_date"]
    computed_quarter = _compute_quarter_from_date(review_date)
    user_quarter = data.get("quarter")
    if user_quarter:
        if not _QUARTER_RE.match(str(user_quarter)):
            raise ServiceError(
                ErrorCode.VALIDATION,
                "quarter sai định dạng (yêu cầu Q[1-4]-YYYY, vd: Q2-2026)",
            )
        try:
            user_year = int(str(user_quarter).split("-", 1)[1])
        except (IndexError, ValueError):
            raise ServiceError(
                ErrorCode.VALIDATION,
                "quarter sai định dạng năm (yêu cầu Q[1-4]-YYYY)",
            )
        current_year = getdate(nowdate()).year
        if not (current_year - 3 <= user_year <= current_year + 1):
            raise ServiceError(
                ErrorCode.VALIDATION,
                f"quarter năm {user_year} ngoài khoảng cho phép "
                f"[{current_year - 3}, {current_year + 1}]",
            )
    data["quarter"] = computed_quarter

    if ManagementReviewRepo.find_by_quarter(data["quarter"]):
        raise ServiceError(ErrorCode.DUPLICATE,
                           f"MR cho quý {data['quarter']} đã tồn tại")
    # BUG-017: auto-link scorecard cùng quý nếu caller chưa truyền.
    if not data.get("scorecard_ref"):
        auto_sc = _find_scorecard_for_quarter(data["quarter"])
        if auto_sc:
            data["scorecard_ref"] = auto_sc
    doc = ManagementReviewRepo.create(data)
    frappe.db.commit()
    return {"name": doc.name, "quarter": doc.quarter, "status": doc.status}


def finalize_management_review(name: str,
                                minutes_doc: str = "",
                                output_actions: list[dict] | None = None) -> dict:
    """§3.6.3: Closed + attach minutes_doc + output_actions."""
    if not rbac.can(_CAP_COMPLIANCE_APPROVE):
        raise ServiceError(ErrorCode.FORBIDDEN, "Không có quyền finalize MR")
    doc = ManagementReviewRepo.get(name)
    if not doc:
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy MR: {name}")
    if doc.status == "Closed":
        raise ServiceError(ErrorCode.BAD_STATE, "MR đã Closed")
    if not minutes_doc:
        raise ServiceError(ErrorCode.VALIDATION, "minutes_doc là bắt buộc")

    # VR: phải có ≥1 output action (skill R-2) khi đóng MR.
    has_existing = bool(getattr(doc, "output_actions", None))
    if not output_actions and not has_existing:
        raise ServiceError(ErrorCode.VALIDATION,
                            "Phải có tối thiểu 1 hành động đầu ra trước khi đóng MR")

    prev_status = doc.status
    doc.minutes_doc = minutes_doc
    doc.status = "Closed"
    doc.workflow_state = "Closed"
    # BUG-017: nếu MR chưa có scorecard_ref, thử auto-link trước khi đóng.
    if not getattr(doc, "scorecard_ref", None):
        auto_sc = _find_scorecard_for_quarter(doc.quarter)
        if auto_sc:
            doc.scorecard_ref = auto_sc
    if output_actions and hasattr(doc, "output_actions"):
        # Replace output_actions child rows. NB: child field is
        # ``responsible`` (``owner`` is a reserved Frappe column).
        doc.output_actions = []
        for action in output_actions:
            doc.append("output_actions", {
                "action_description": action.get("action", "")
                or action.get("action_description", ""),
                "responsible": action.get("responsible", "")
                or action.get("owner", ""),
                "due_date": action.get("due_date"),
            })
    ManagementReviewRepo.save(doc)
    _log_record_event(
        "IMM Management Review", name, "System",
        f"MR {doc.quarter}: đóng & xuất biên bản",
        from_status=prev_status, to_status="Closed",
    )
    frappe.db.commit()
    return {"name": name, "status": "Closed", "quarter": doc.quarter}


_MR_TRANSITIONS = {
    "Draft": {"Held"},
    "Held": {"Minutes Approved"},
    "Minutes Approved": {"Closed"},
}


def update_management_review(name: str, data: dict | None = None) -> dict:
    """Cập nhật nội dung MR (attendees, scorecard, summaries, output_actions).

    Chỉ cho phép khi MR chưa Closed. ``data`` là dict các field MR + 2 child
    list tuỳ chọn ``attendees`` / ``output_actions``.
    """
    if not rbac.can(_CAP_COMPLIANCE_APPROVE):
        raise ServiceError(ErrorCode.FORBIDDEN, "Không có quyền cập nhật MR")
    data = data or {}
    doc = ManagementReviewRepo.get(name)
    if not doc:
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy MR: {name}")
    if doc.status == "Closed":
        raise ServiceError(ErrorCode.BAD_STATE, "MR đã Closed — không thể sửa")

    SCALAR = ("review_date", "chair", "scorecard_ref", "inputs_summary",
              "audit_summary", "capa_summary", "capa_effectiveness",
              "training_compliance", "risk_review", "qms_changes_decided",
              "next_review_date", "minutes_doc")
    for field in SCALAR:
        if field in data:
            setattr(doc, field, data[field])

    if "attendees" in data and isinstance(data["attendees"], list):
        doc.attendees = []
        for a in data["attendees"]:
            doc.append("attendees", {
                "user": a.get("user", ""),
                "role_title": a.get("role_title", ""),
                "present": 1 if a.get("present", True) else 0,
                "signed": 1 if a.get("signed") else 0,
            })
    if "output_actions" in data and isinstance(data["output_actions"], list):
        doc.output_actions = []
        for ac in data["output_actions"]:
            doc.append("output_actions", {
                "action_description": ac.get("action_description",
                                             ac.get("action", "")),
                "responsible": ac.get("responsible", ac.get("owner", "")),
                "due_date": ac.get("due_date"),
                "priority": ac.get("priority", "Medium"),
                "status": ac.get("status", "Open"),
                "notes": ac.get("notes", ""),
            })
    ManagementReviewRepo.save(doc)
    _log_record_event(
        "IMM Management Review", name, "System",
        f"MR {doc.quarter}: cập nhật nội dung",
    )
    frappe.db.commit()
    return {"name": name, "status": doc.status, "quarter": doc.quarter}


def advance_mr_state(name: str, target_state: str) -> dict:
    """Chuyển trạng thái MR theo workflow JSON (Draft→Held→Minutes Approved→Closed).

    Action labels FE phải khớp workflow ``IMM-16 Management Review Workflow``.
    Bước cuối ``Closed`` đi qua :func:`finalize_management_review`.
    """
    if not rbac.can(_CAP_COMPLIANCE_APPROVE):
        raise ServiceError(ErrorCode.FORBIDDEN, "Không có quyền chuyển trạng thái MR")
    doc = ManagementReviewRepo.get(name)
    if not doc:
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy MR: {name}")
    current = doc.status or "Draft"
    if target_state not in _MR_TRANSITIONS.get(current, set()):
        raise ServiceError("INVALID_STATE",
                           f"Không thể chuyển MR từ {current} sang {target_state}")
    if target_state == "Closed":
        raise ServiceError(ErrorCode.VALIDATION,
                           "Dùng finalize_management_review để đóng MR")
    doc.status = target_state
    doc.workflow_state = target_state
    ManagementReviewRepo.save(doc)
    _log_record_event(
        "IMM Management Review", name, "System",
        f"MR {doc.quarter}: {current} → {target_state}",
        from_status=current, to_status=target_state,
    )
    frappe.db.commit()
    return {"name": name, "status": target_state, "quarter": doc.quarter}


# ─── Dashboard / Reports (canonical) ─────────────────────────────────────────

def get_dashboard_stats() -> dict:
    """§3.7.1: aggregated KPIs + 12m trend + top_modules_low + recent_findings."""
    from frappe.utils import getdate, add_months

    findings_open = ComplianceFindingRepo.count(
        {"status": ("in", list(FindingStatus.ACTIVE))})
    findings_critical = ComplianceFindingRepo.count(
        {"status": ("in", list(FindingStatus.ACTIVE)), "severity": "Critical"})
    from assetcore.services.imm00 import _open_capa_filter, _overdue_capa_filter
    # SoT: _open_capa_filter() — quality-dash capa_open == KPI/scorecard/aging byte-for-byte
    # (status NOT IN Closed). KHÔNG inline status IN [Open, In Progress] (bỏ sót Overdue +
    # Pending Verification → đếm thiếu so với dashboard KPI).
    capa_open = frappe.db.count("IMM CAPA Record", _open_capa_filter())
    # SoT: _overdue_capa_filter() — quality-dash capa_overdue khớp KPI/drill byte-for-byte.
    capa_overdue = frappe.db.count("IMM CAPA Record", _overdue_capa_filter())
    audits_in_progress = InternalAuditRepo.count(
        {"status": AuditStatus.IN_PROGRESS})

    # Overall compliance from latest scorecard
    latest_sc = frappe.get_all(
        ComplianceScorecardRepo.DOCTYPE,
        filters={"is_published": 1},
        fields=["name", "score_pct", "period_year", "period_month"],
        order_by="period_year desc, period_month desc",
        limit_page_length=1,
    )
    overall_pct = float(latest_sc[0].score_pct) if latest_sc else 0.0

    # MR quarterly status
    today = getdate(nowdate())
    q = ((today.month - 1) // 3) + 1
    q_label = f"Q{q}-{today.year}"
    mr_done = frappe.db.exists("IMM Management Review",
                                {"quarter": q_label, "status": "Closed"})
    mr_status = "Done" if mr_done else "Pending"

    # 12-month trend
    trend_12m = frappe.get_all(
        ComplianceScorecardRepo.DOCTYPE,
        filters={"is_published": 1},
        fields=["period_year", "period_month", "score_pct"],
        order_by="period_year desc, period_month desc",
        limit_page_length=12,
    )
    trend_12m_out = [
        {"month": f"{r.period_year}-{r.period_month:02d}",
         "score_pct": float(r.score_pct or 0)}
        for r in reversed(trend_12m)
    ]

    recent_findings = frappe.get_all(
        ComplianceFindingRepo.DOCTYPE,
        fields=["name", "rule", "asset", "severity", "status",
                "detected_date", "responsible_dept"],
        order_by="detected_date desc",
        limit_page_length=10,
    )

    return {
        "kpis": {
            "overall_compliance_pct": overall_pct,
            "findings_open": findings_open,
            "findings_critical": findings_critical,
            "capa_open": capa_open,
            "capa_overdue": capa_overdue,
            "audits_in_progress": audits_in_progress,
            "mr_quarterly_status": mr_status,
        },
        "trend_12m": trend_12m_out,
        "top_modules_low": [],
        "recent_findings": recent_findings,
    }


def get_compliance_heatmap(period_year: int | None = None,
                           period_month: int | None = None) -> dict:
    """§3.7.2: Module × Department score grid từ Compliance Finding.

    BUG-16-11: gom nhóm theo ``source_module`` thực của Rule (vd ``IMM-08``)
    thay vì cắt cụt docname (``CR-PM-``). BUG-16-04: trả kèm nhãn Khoa/phòng
    đọc được (``departments_labels``) thay vì hiển thị mã thô.
    """
    today = getdate(nowdate())
    py = int(period_year) if period_year else today.year
    pm = int(period_month) if period_month else today.month

    # BR-16-12: CÙNG hằng + helper với generate_scorecard → CÙNG TẬP finding cho
    # cùng module/kỳ (period-anchor canonical = evaluation_date, KHÔNG còn
    # detected_date — Datetime event-timestamp có thể lệch kỳ do lag adjudication).
    start, end = _period_bounds(py, pm)
    findings = frappe.get_all(
        ComplianceFindingRepo.DOCTYPE,
        filters={
            PERIOD_ANCHOR_FIELD: ("between", [start, end]),
            "status": ("!=", FindingStatus.FALSE_POSITIVE),
        },
        fields=["rule", "responsible_dept", "status", "severity"],
    )

    # Resolve rule -> source_module (fallback to docname prefix if unset).
    rule_ids = list({f.rule for f in findings if f.rule})
    rule_module: dict[str, str] = {}
    if rule_ids:
        for r in frappe.get_all(
            ComplianceRuleRepo.DOCTYPE,
            filters={"name": ("in", rule_ids)},
            fields=["name", "source_module"],
        ):
            rule_module[r.name] = r.source_module or (r.name or "")[:6] or "Khác"

    # Group by (module, dept) — gom status finding để dùng CHUNG SoT BR-16-11.
    by_cell: dict[tuple, list] = {}
    modules_set: set[str] = set()
    depts_set: set[str] = set()
    for f in findings:
        module = rule_module.get(f.rule) or (f.rule or "")[:6] or "Khác"
        dept = f.responsible_dept or "__none__"
        modules_set.add(module)
        depts_set.add(dept)
        by_cell.setdefault((module, dept), []).append(f)

    # BUG-16-04: dept code -> human readable department name.
    dept_codes = [d for d in depts_set if d != "__none__"]
    dept_label: dict[str, str] = {"__none__": "Chưa phân khoa"}
    if dept_codes:
        for d in frappe.get_all(
            "AC Department",
            filters={"name": ("in", dept_codes)},
            fields=["name", "department_name"],
        ):
            dept_label[d.name] = d.department_name or d.name
    for d in dept_codes:
        dept_label.setdefault(d, d)

    matrix = []
    for (module, dept), cell_findings in by_cell.items():
        # BR-16-11: per-cell dùng CÙNG SoT — mẫu số = adjudicated của cell;
        # cell không có adjudicated → 100.0. findings_count vẫn báo TỔNG (gồm
        # pending) để UX không mất dấu.
        rate = compute_compliance_rate(cell_findings)
        matrix.append({
            "module": module, "dept": dept,
            "module_label": module,
            "dept_label": dept_label.get(dept, dept),
            "score": rate["score_pct"],
            "findings_count": len(cell_findings),
            "pending_count": rate["pending"],
        })
    return {
        "modules": sorted(modules_set),
        "departments": sorted(depts_set),
        "module_labels": {m: m for m in modules_set},
        "department_labels": dept_label,
        "matrix": matrix,
    }


def get_capa_aging() -> dict:
    """§3.7.3: CAPA aging buckets.

    SoT: tập CAPA mở dùng _open_capa_filter() (status NOT IN Closed) — KHÔNG inline
    status IN [Open, In Progress] (bỏ sót Overdue/Pending Verification). INVARIANT:
    total_open == sum(buckets.values()) — record opened_date NULL bị loại khỏi CẢ HAI
    cách đếm (không để total_open != sum(buckets) do null-skip ở vòng bucket).
    """
    from assetcore.services.imm00 import _open_capa_filter
    open_capas = frappe.get_all(
        "IMM CAPA Record",
        filters=_open_capa_filter(),
        fields=["name", "due_date", "opened_date", "imm_risk_level"],
    )
    # Loại record opened_date NULL khỏi mẫu số (không thể tính tuổi) → total_open
    # đếm trên CÙNG tập đưa vào buckets ⟹ total_open == sum(buckets).
    ageable = [c for c in open_capas if c.opened_date]
    buckets = {"0-7": 0, "8-30": 0, "31-60": 0, "60+": 0}
    today = getdate(nowdate())
    for c in ageable:
        age = (today - getdate(c.opened_date)).days
        if age <= 7:
            buckets["0-7"] += 1
        elif age <= 30:
            buckets["8-30"] += 1
        elif age <= 60:
            buckets["31-60"] += 1
        else:
            buckets["60+"] += 1
    return {"buckets": buckets, "total_open": len(ageable)}


def get_overdue_actions() -> dict:
    """§3.7.4: Overdue findings + CAPAs."""
    overdue_findings = frappe.get_all(
        ComplianceFindingRepo.DOCTYPE,
        filters={
            "status": ("in", list(FindingStatus.ACTIVE)),
            "detected_date": ("<", add_days(nowdate(), -30)),
        },
        fields=["name", "rule", "severity", "detected_date", "asset"],
        limit_page_length=50,
    )
    from assetcore.services.imm00 import _overdue_capa_filter
    # SoT: _overdue_capa_filter() — get_overdue_actions overdue_capas khớp KPI/drill byte-for-byte.
    overdue_capas = frappe.get_all(
        "IMM CAPA Record",
        filters=_overdue_capa_filter(),
        fields=["name", "asset", "due_date", "responsible", "imm_risk_level"],
        limit_page_length=50,
    )
    return {
        "overdue_findings": overdue_findings,
        "overdue_capas": overdue_capas,
        "total": len(overdue_findings) + len(overdue_capas),
    }

