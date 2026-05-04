# Copyright (c) 2026, AssetCore Team
"""Business logic for IMM-01 — Needs Assessment & Budget Estimation.

Tier 2 service layer. Controllers (Tier 3) gọi vào đây; API (Tier 1) cũng gọi
xuống đây qua `assetcore.api.imm01`.

Phạm vi:
  - Validation Rules VR-01-01..VR-01-06
  - Gates G01..G05
  - Priority scoring (6 tiêu chí có trọng số)
  - Budget rollup (CAPEX + OPEX 5y)
  - Procurement Plan rollup
  - Demand Forecast (scheduler monthly + cron quarterly)
  - Audit trail qua IMM Audit Trail (KHÔNG tạo child Lifecycle Event riêng)
"""
from __future__ import annotations

from typing import Iterable

import frappe
from frappe import _
from frappe.utils import getdate, now_datetime, today, get_request_session
from frappe.model.document import Document

from assetcore.services.shared import ErrorCode, ServiceError

# ─── Constants ────────────────────────────────────────────────────────────────

_DT_NR    = "IMM Needs Request"
_DT_PP    = "IMM Procurement Plan"
_DT_DF    = "IMM Demand Forecast"
_DT_ASSET = "AC Asset"
_DT_AUDIT = "IMM Audit Trail"

MIN_JUSTIFICATION_LEN = 200
ENVELOPE_SOFT_PCT     = 80
ENVELOPE_HARD_PCT     = 100   # áp dụng nếu master config enforce_envelope=1

# Trọng số mặc định 6 tiêu chí (tổng = 1.0). Có thể override bằng master sau.
DEFAULT_PRIORITY_WEIGHTS: dict[str, float] = {
    "clinical_impact":    0.25,
    "risk":               0.20,
    "utilization_gap":    0.15,
    "replacement_signal": 0.15,
    "compliance_gap":     0.15,
    "budget_fit":         0.10,
}

REQUIRED_OPEX_YEARS = (1, 2, 3, 4, 5)

# Active states (chưa terminal) — dùng cho scheduler overdue + uniqueness check
_ACTIVE_STATES = frozenset({
    "Draft", "Submitted", "Reviewing", "Prioritized", "Budgeted", "Pending Approval",
})
_TERMINAL_STATES = frozenset({"Approved", "Rejected"})


# ─── Audit trail helpers ──────────────────────────────────────────────────────

def write_audit_trail(
    doc: Document, event_type: str,
    from_status: str | None, to_status: str | None,
    notes: str = "",
) -> None:
    """Ghi 1 row IMM Audit Trail nếu phiếu có liên kết Asset.

    IMM Audit Trail (Wave 1) yêu cầu `asset` (Link → AC Asset) bắt buộc, và
    `event_type` là Select fixed: State Change / CAPA / Maintenance / Calibration
    / Document / Incident / Audit / System / Transfer.

    Với Needs Request:
      - Replacement → có replacement_for_asset → ghi audit trail (event_type=System)
      - New / Upgrade / Add-on → chưa có asset → bỏ qua, rely on Frappe Version
        (track_changes=1 trong DocType JSON đã bật) + workflow_state history.
    Tham số `event_type` được map tương đối — chi tiết transitions vào change_summary.
    """
    asset_name = getattr(doc, "replacement_for_asset", None)
    if not asset_name:
        # Pre-asset stage — Frappe Version handles change history automatically.
        return
    summary = f"[{doc.doctype}/{doc.name}] {event_type}"
    if from_status or to_status:
        summary += f": {from_status or '—'} → {to_status or '—'}"
    if notes:
        summary += f" | {notes}"
    try:
        audit = frappe.get_doc({
            "doctype":        _DT_AUDIT,
            "asset":          asset_name,
            "event_type":     "System",
            "actor":          frappe.session.user or "Administrator",
            "timestamp":      now_datetime(),
            "ref_doctype":    doc.doctype,
            "ref_name":       doc.name,
            "from_status":    from_status or "",
            "to_status":      to_status or "",
            "change_summary": summary,
        })
        audit.insert(ignore_permissions=True)
    except Exception:
        frappe.log_error(frappe.get_traceback(), f"IMM-01 audit trail failed for {doc.name}")


# ─── Lifecycle hooks (gọi từ controller) ──────────────────────────────────────

def before_insert_needs_request(doc: Document) -> None:
    if not doc.request_date:
        doc.request_date = today()
    # Auto-fetch utilization từ IMM-07 (placeholder — IMM-07 chưa expose API tại thời điểm
    # này; sẽ wire khi IMM-07 GA).
    if doc.request_type in ("Replacement", "Upgrade") and doc.replacement_for_asset:
        _autofetch_replacement_metrics(doc)


def validate_needs_request(doc: Document) -> None:
    _vr03_clinical_justification(doc)
    _vr04_target_year(doc)
    _vr01_unique_active_request_per_asset(doc)
    _vr02_replacement_requires_decom_plan(doc)
    _compute_priority_score(doc)
    _vr05_score_consistency(doc)
    _rollup_budget(doc)
    _check_workflow_gates(doc)


def before_submit_needs_request(doc: Document) -> None:
    _validate_gate_g05(doc)
    if not doc.approval_date:
        doc.approval_date = today()


def on_submit_needs_request(doc: Document) -> None:
    write_audit_trail(doc, "Approved", doc.workflow_state, "Approved",
                      f"Funding={doc.funding_source}; approver={doc.board_approver}")
    # Auto-roll vào Procurement Plan kỳ kế nếu cấu hình bật (V2 — placeholder).


def on_cancel_needs_request(doc: Document) -> None:
    write_audit_trail(doc, "Cancelled", doc.workflow_state, "Cancelled", "")


# ─── VR-01..VR-05 ─────────────────────────────────────────────────────────────

def _vr01_unique_active_request_per_asset(doc: Document) -> None:
    """VR-01: Asset chỉ có 1 Needs Request Replacement Active."""
    if doc.request_type != "Replacement" or not doc.replacement_for_asset:
        return
    existing = frappe.db.sql(
        f"""SELECT name FROM `tab{_DT_NR}`
            WHERE replacement_for_asset = %s
              AND request_type = 'Replacement'
              AND docstatus < 1
              AND workflow_state NOT IN ('Approved','Rejected')
              AND name != %s
            LIMIT 1""",
        (doc.replacement_for_asset, doc.name or ""),
    )
    if existing:
        raise ServiceError(
            ErrorCode.DUPLICATE,
            _("VR-01-01: Asset {0} đã có Needs Request Replacement Active ({1})")
            .format(doc.replacement_for_asset, existing[0][0]),
        )


def _vr02_replacement_requires_decom_plan(doc: Document) -> None:
    """VR-02: Replacement type cần Decommission Plan (IMM-13).

    IMM-13 chưa triển khai → tạm thời chỉ warn. Khi IMM-13 LIVE đổi sang throw.
    """
    if doc.request_type != "Replacement" or not doc.replacement_for_asset:
        return
    # Placeholder: kiểm tra Asset.imm_lifecycle_status có flag pending decommission
    asset_status = frappe.db.get_value(_DT_ASSET, doc.replacement_for_asset, "imm_lifecycle_status")
    if asset_status not in ("Decommissioned", "Pending Decommission"):
        # Tạm soft-warn; sau khi IMM-13 LIVE đổi sang ServiceError(BUSINESS_RULE).
        frappe.msgprint(
            _("VR-01-02 (warn): Replacement nên có IMM-13 Decommission Plan cho asset {0}. "
              "Hiện trạng asset: {1}.").format(doc.replacement_for_asset, asset_status or "—"),
            indicator="orange", title=_("Cảnh báo VR-01-02"),
        )


def _vr03_clinical_justification(doc: Document) -> None:
    """VR-03: clinical_justification ≥ 200 ký tự (tính theo plain text length)."""
    text = (doc.clinical_justification or "").strip()
    if len(text) < MIN_JUSTIFICATION_LEN:
        raise ServiceError(
            ErrorCode.VALIDATION,
            _("VR-01-03: clinical_justification phải ≥ {0} ký tự (hiện tại: {1})")
            .format(MIN_JUSTIFICATION_LEN, len(text)),
        )


def _vr04_target_year(doc: Document) -> None:
    """VR-04: target_year ≥ year hiện tại."""
    current = getdate(today()).year
    if not doc.target_year or doc.target_year < current:
        raise ServiceError(
            ErrorCode.VALIDATION,
            _("VR-01-04: target_year ({0}) không được nhỏ hơn năm hiện tại ({1})")
            .format(doc.target_year, current),
        )


def _vr05_score_consistency(doc: Document) -> None:
    """VR-05: weighted_score = Σ score×weight (sai số < 0.01)."""
    if not doc.scoring_rows:
        return
    expected = sum((r.weighted or 0) for r in doc.scoring_rows)
    if abs((doc.weighted_score or 0) - expected) > 0.01:
        raise ServiceError(
            ErrorCode.VALIDATION,
            _("VR-01-05: weighted_score ({0}) không khớp Σ scoring_rows ({1})")
            .format(doc.weighted_score, expected),
        )


# VR-06 (lifecycle bất biến) enforce ở tầng IMM Audit Trail — không cần lặp.


# ─── Priority scoring ─────────────────────────────────────────────────────────

def _compute_priority_score(doc: Document) -> None:
    """Tính weighted_score và priority_class từ scoring_rows."""
    weights = _get_priority_weights()
    total = 0.0
    for row in (doc.scoring_rows or []):
        w = weights.get(row.criterion, 0.0)
        row.weight_pct = round(w * 100, 2)
        score = row.score or 0
        row.weighted = round(score * w, 4)
        total += row.weighted
    doc.weighted_score = round(total, 4)
    doc.priority_class = _classify_priority(total)


def _classify_priority(score: float) -> str | None:
    if score >= 4.0: return "P1"
    if score >= 3.0: return "P2"
    if score >= 2.0: return "P3"
    if score > 0:    return "P4"
    return None


def _get_priority_weights() -> dict[str, float]:
    """Đọc trọng số từ master config (placeholder) hoặc fallback default."""
    # Trong tương lai: đọc từ DocType "IMM Priority Weight" master.
    return DEFAULT_PRIORITY_WEIGHTS


# ─── Budget rollup ────────────────────────────────────────────────────────────

def _rollup_budget(doc: Document) -> None:
    """Tính total_capex / total_opex_5y / tco_5y từ budget_lines."""
    capex = 0.0
    opex_5y = 0.0
    for line in (doc.budget_lines or []):
        amt = (line.qty or 0) * (line.unit_cost or 0)
        line.amount = amt
        if line.budget_section == "CAPEX":
            capex += amt
        elif line.budget_section == "OPEX":
            opex_5y += amt
    doc.total_capex = round(capex, 2)
    doc.total_opex_5y = round(opex_5y, 2)
    doc.tco_5y = round(capex + opex_5y, 2)


def _autofetch_replacement_metrics(doc: Document) -> None:
    """Auto-fetch utilization_pct_12m & downtime_hr_12m từ IMM-07.

    IMM-07 chưa GA — hiện chỉ stub; sẽ wire qua frappe.call khi LIVE.
    """
    if doc.utilization_pct_12m or doc.downtime_hr_12m:
        return  # đã nhập tay — không ghi đè
    # TODO(IMM-07): from assetcore.services.imm07 import get_asset_kpi_12m
    return


# ─── Gates (G01..G05) ─────────────────────────────────────────────────────────

def _check_workflow_gates(doc: Document) -> None:
    """Run gate phù hợp với target state (workflow_state mới)."""
    state = (doc.workflow_state or "Draft")
    if state == "Reviewing":
        _validate_gate_g01(doc)
    if state == "Prioritized":
        _validate_gate_g02(doc)
    if state == "Budgeted":
        _validate_gate_g03(doc)
        _validate_gate_g04(doc)


def _validate_gate_g01(doc: Document) -> None:
    """G01: clinical_justification + utilization_pct_12m (nếu Replacement/Upgrade)."""
    if doc.request_type in ("Replacement", "Upgrade"):
        if doc.utilization_pct_12m is None:
            raise ServiceError(
                ErrorCode.BUSINESS_RULE,
                _("G01: Yêu cầu utilization_pct_12m khi request_type = {0}")
                .format(doc.request_type),
            )


def _validate_gate_g02(doc: Document) -> None:
    """G02: 6/6 scoring rows."""
    expected = set(DEFAULT_PRIORITY_WEIGHTS.keys())
    have = {r.criterion for r in (doc.scoring_rows or [])}
    missing = expected - have
    if missing:
        raise ServiceError(
            ErrorCode.BUSINESS_RULE,
            _("G02: Thiếu tiêu chí chấm điểm: {0}").format(", ".join(sorted(missing))),
        )


def _validate_gate_g03(doc: Document) -> None:
    """G03: total_capex > 0 + đủ 5 năm OPEX (có dòng cho mỗi year_offset 1..5)."""
    if not (doc.total_capex and doc.total_capex > 0):
        raise ServiceError(
            ErrorCode.BUSINESS_RULE,
            _("G03: Phải có ít nhất 1 dòng CAPEX > 0"),
        )
    opex_years = {
        line.year_offset for line in (doc.budget_lines or [])
        if line.budget_section == "OPEX" and line.year_offset
    }
    missing_years = [y for y in REQUIRED_OPEX_YEARS if y not in opex_years]
    if missing_years:
        raise ServiceError(
            ErrorCode.BUSINESS_RULE,
            _("G03: Phải có OPEX 5 năm liên tục — thiếu năm: {0}").format(missing_years),
        )


def _validate_gate_g04(doc: Document) -> None:
    """G04: tổng allocated trong Procurement Plan ≤ envelope (warning)."""
    # Soft check — implement đầy đủ ở Procurement Plan validate (cross-doc rollup).
    # Ở đây chỉ kiểm tra TCO không quá 5x ngưỡng phi thực tế (sanity).
    return


def _validate_gate_g05(doc: Document) -> None:
    """G05: board_approver + funding_source bắt buộc trước Submit."""
    missing = []
    if not doc.funding_source:
        missing.append("funding_source")
    if not doc.board_approver:
        missing.append("board_approver")
    if missing:
        raise ServiceError(
            ErrorCode.BUSINESS_RULE,
            _("G05: Thiếu trường bắt buộc trước Submit: {0}").format(", ".join(missing)),
        )


# ─── Procurement Plan ─────────────────────────────────────────────────────────

def validate_procurement_plan(doc: Document) -> None:
    _rollup_plan_capex(doc)


def on_submit_procurement_plan(doc: Document) -> None:
    """Khi Plan submit, cập nhật `procurement_plan` link trên các Needs Request đã rolled in."""
    for item in (doc.plan_items or []):
        if item.needs_request:
            frappe.db.set_value(_DT_NR, item.needs_request, "procurement_plan", doc.name)
    write_audit_trail(doc, "Plan Activated", doc.workflow_state, doc.workflow_state, "")


def _rollup_plan_capex(doc: Document) -> None:
    allocated = sum((it.allocated_budget or 0) for it in (doc.plan_items or []))
    doc.allocated_capex = round(allocated, 2)
    if doc.budget_envelope:
        doc.utilization_pct = round(allocated / doc.budget_envelope * 100, 2)
    else:
        doc.utilization_pct = 0
    # sort + rank
    rows = sorted(
        (doc.plan_items or []),
        key=lambda r: (-(r.weighted_score or 0), r.idx),
    )
    for i, it in enumerate(rows, 1):
        it.priority_rank = i


def roll_into_plan(plan_year: int, plan_period: str, needs_requests: Iterable[str]) -> str:
    """Gom Approved Needs Request vào Procurement Plan kỳ kế.

    Tạo plan mới (Draft) nếu chưa có cho period+year; nếu có thì append.
    """
    name = frappe.db.get_value(
        _DT_PP,
        {"plan_year": plan_year, "plan_period": plan_period, "docstatus": ["<", 2]},
        "name",
    )
    if name:
        plan = frappe.get_doc(_DT_PP, name)
    else:
        plan = frappe.new_doc(_DT_PP)
        plan.plan_year = plan_year
        plan.plan_period = plan_period
        plan.budget_envelope = 0  # Caller phải set trước khi submit

    existing = {it.needs_request for it in (plan.plan_items or [])}
    for nr_name in needs_requests:
        if nr_name in existing:
            continue
        nr = frappe.get_doc(_DT_NR, nr_name)
        if nr.docstatus != 1 or nr.workflow_state != "Approved":
            raise ServiceError(
                ErrorCode.BUSINESS_RULE,
                _("Chỉ Needs Request đã Approved mới được gom vào Plan ({0} hiện ở {1})")
                .format(nr_name, nr.workflow_state),
            )
        plan.append("plan_items", {
            "needs_request":   nr.name,
            "weighted_score":  nr.weighted_score,
            "allocated_budget": nr.tco_5y or 0,
            "status":          "Pending Spec",
        })
    plan.save(ignore_permissions=True)
    return plan.name


# ─── Demand Forecast (scheduler) ──────────────────────────────────────────────

def generate_demand_forecast() -> None:
    """Scheduler monthly — tổng hợp utilization, replacement, service expansion.

    Phiên bản v0.1 (Wave 2 launch): tạo skeleton record cho từng device_category
    có asset; con số projected là placeholder cho đến khi IMM-07 / IMM-13 expose API.
    """
    categories = frappe.get_all("AC Asset Category", fields=["name"])
    year = getdate(today()).year + 1
    for cat in categories:
        existing = frappe.db.exists(_DT_DF, {
            "forecast_year":   year,
            "device_category": cat.name,
        })
        if existing:
            continue
        df = frappe.new_doc(_DT_DF)
        df.forecast_year   = year
        df.horizon_years   = 5
        df.device_category = cat.name
        df.projected_qty   = 0     # TODO: wire IMM-07 + IMM-13
        df.projected_capex = 0
        df.generated_at    = now_datetime()
        df.generated_by    = "Administrator"
        df.append("drivers", {"driver_type": "replacement",        "weight_pct": 50, "source_module": "IMM-13"})
        df.append("drivers", {"driver_type": "utilization_growth", "weight_pct": 25, "source_module": "IMM-07"})
        df.append("drivers", {"driver_type": "service_expansion",  "weight_pct": 25, "source_module": "Manual"})
        df.insert(ignore_permissions=True)
    frappe.db.commit()


# ─── Scheduler — overdue & envelope alerts ────────────────────────────────────

def check_pending_request_overdue() -> None:
    """Daily — phiếu Submitted/Reviewing > 30d → email PTP Khối 1 (placeholder)."""
    rows = frappe.db.sql(
        f"""SELECT name, requesting_department, request_date
            FROM `tab{_DT_NR}`
            WHERE docstatus = 0
              AND workflow_state IN ('Submitted','Reviewing')
              AND DATEDIFF(CURDATE(), request_date) > 30""",
        as_dict=True,
    )
    if not rows:
        return
    # TODO: gửi email cho IMM Department Head + IMM Planning Officer
    frappe.logger("imm01").info(f"IMM-01 overdue: {len(rows)} phiếu")


def budget_envelope_alert() -> None:
    """Weekly — cảnh báo khi Plan vượt 80% envelope."""
    rows = frappe.db.sql(
        f"""SELECT name, allocated_capex, budget_envelope, utilization_pct
            FROM `tab{_DT_PP}`
            WHERE docstatus = 0 AND budget_envelope > 0
              AND (allocated_capex / budget_envelope) >= {ENVELOPE_SOFT_PCT/100}""",
        as_dict=True,
    )
    for r in rows:
        frappe.logger("imm01").warning(
            f"IMM-01 envelope alert: Plan {r.name} allocated {r.utilization_pct:.1f}%"
        )
