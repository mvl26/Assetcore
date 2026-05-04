# Copyright (c) 2026, AssetCore Team
"""IMM-01 REST API — Wave 2.

Tier 1 — parse HTTP input → gọi services.imm01 → _ok / _err envelope.

Convention:
  GET   → frappe.whitelist(allow_guest=False)
  POST  → frappe.whitelist(methods=["POST"])
  Response envelope: {success, data} | {success: false, error, code}
  Error code: enum ErrorCode (assetcore.services.shared.constants).
"""
from __future__ import annotations

import json

import frappe
from frappe import _

from assetcore.services import imm01 as svc
from assetcore.services.shared import ErrorCode, ServiceError
from assetcore.utils.helpers import _ok, _err

_DT_NR = "IMM Needs Request"
_DT_PP = "IMM Procurement Plan"
_DT_DF = "IMM Demand Forecast"


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _parse_json(raw, *, default=None):
    if not raw:
        return default if default is not None else {}
    if not isinstance(raw, str):
        return raw
    try:
        return json.loads(raw)
    except (ValueError, TypeError) as e:
        raise ServiceError(ErrorCode.INVALID_PARAMS, f"JSON không hợp lệ: {e}")


def _handle(fn, *args, **kwargs) -> dict:
    try:
        return _ok(fn(*args, **kwargs))
    except ServiceError as e:
        return _err(e.message, e.code)
    except frappe.DoesNotExistError as e:
        # Phải bắt trước ValidationError vì DoesNotExistError là subclass.
        return _err(str(e), ErrorCode.NOT_FOUND)
    except frappe.PermissionError as e:
        return _err(str(e), ErrorCode.FORBIDDEN)
    except frappe.ValidationError as e:
        return _err(str(e), ErrorCode.VALIDATION)
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), f"IMM-01 {fn.__name__}")
        return _err(str(e), ErrorCode.INTERNAL)


# ─── Read endpoints ───────────────────────────────────────────────────────────

@frappe.whitelist()
def list_needs_requests(filters: str = "{}", page: int = 1, page_size: int = 20,
                         order_by: str = "request_date desc") -> dict:
    return _handle(_list_needs_requests, filters, int(page), int(page_size), order_by)


def _list_needs_requests(filters: str, page: int, page_size: int, order_by: str) -> dict:
    f = _parse_json(filters)
    fields = [
        "name", "request_type", "device_model_ref", "requesting_department",
        "quantity", "weighted_score", "priority_class", "workflow_state",
        "request_date", "total_capex", "tco_5y",
    ]
    page_size = max(1, min(int(page_size), 100))
    start = (max(1, int(page)) - 1) * page_size
    items = frappe.get_list(
        _DT_NR, filters=f or None, fields=fields,
        order_by=order_by, start=start, page_length=page_size,
    )
    total = frappe.db.count(_DT_NR, filters=f or None)
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@frappe.whitelist()
def get_needs_request(name: str) -> dict:
    return _handle(_get_needs_request, name)


def _get_needs_request(name: str) -> dict:
    doc = frappe.get_doc(_DT_NR, name)
    return doc.as_dict()


# ─── Mutating endpoints ───────────────────────────────────────────────────────

@frappe.whitelist(methods=["POST"])
def create_needs_request(payload: str = "{}") -> dict:
    return _handle(_create_needs_request, payload)


def _create_needs_request(payload: str) -> dict:
    data = _parse_json(payload)
    if not data:
        raise ServiceError(ErrorCode.INVALID_PARAMS, _("payload trống"))
    doc = frappe.new_doc(_DT_NR)
    for k, v in data.items():
        if k in ("scoring_rows", "budget_lines"):
            for row in v or []:
                doc.append(k, row)
        else:
            setattr(doc, k, v)
    doc.insert()
    return {"name": doc.name, "workflow_state": doc.workflow_state}


@frappe.whitelist(methods=["POST"])
def update_needs_request(name: str, payload: str = "{}") -> dict:
    return _handle(_update_needs_request, name, payload)


def _update_needs_request(name: str, payload: str) -> dict:
    data = _parse_json(payload)
    doc = frappe.get_doc(_DT_NR, name)
    if doc.docstatus != 0:
        raise ServiceError(ErrorCode.BAD_STATE, _("Phiếu đã submit/cancel — không sửa được"))
    for k, v in data.items():
        if k in ("scoring_rows", "budget_lines"):
            doc.set(k, [])
            for row in v or []:
                doc.append(k, row)
        else:
            setattr(doc, k, v)
    doc.save()
    return {"name": doc.name, "workflow_state": doc.workflow_state}


@frappe.whitelist(methods=["POST"])
def transition_workflow(name: str, action: str) -> dict:
    """Áp dụng 1 workflow transition lên Needs Request."""
    return _handle(_transition_workflow, name, action)


def _transition_workflow(name: str, action: str) -> dict:
    from frappe.model.workflow import apply_workflow
    apply_workflow(frappe.get_doc(_DT_NR, name), action)
    doc = frappe.get_doc(_DT_NR, name)
    return {"name": doc.name, "workflow_state": doc.workflow_state, "docstatus": doc.docstatus}


@frappe.whitelist(methods=["POST"])
def submit_needs_request(name: str) -> dict:
    return _handle(_submit_needs_request, name)


def _submit_needs_request(name: str) -> dict:
    doc = frappe.get_doc(_DT_NR, name)
    if doc.docstatus != 0:
        raise ServiceError(ErrorCode.BAD_STATE, _("Phiếu đã submit/cancel"))
    doc.submit()
    return {"name": doc.name, "workflow_state": doc.workflow_state}


@frappe.whitelist(methods=["POST"])
def score_needs_request(name: str, scoring_rows: str = "[]") -> dict:
    return _handle(_score_needs_request, name, scoring_rows)


def _score_needs_request(name: str, scoring_rows: str) -> dict:
    rows = _parse_json(scoring_rows, default=[])
    doc = frappe.get_doc(_DT_NR, name)
    if doc.docstatus != 0:
        raise ServiceError(ErrorCode.BAD_STATE, _("Phiếu đã submit"))
    doc.set("scoring_rows", [])
    for r in rows:
        doc.append("scoring_rows", r)
    doc.save()
    return {"weighted_score": doc.weighted_score, "priority_class": doc.priority_class}


@frappe.whitelist(methods=["POST"])
def submit_budget_estimate(name: str, budget_lines: str = "[]",
                            funding_source: str | None = None,
                            funding_evidence: str | None = None) -> dict:
    return _handle(_submit_budget_estimate, name, budget_lines, funding_source, funding_evidence)


def _submit_budget_estimate(name: str, budget_lines: str,
                             funding_source: str | None, funding_evidence: str | None) -> dict:
    lines = _parse_json(budget_lines, default=[])
    doc = frappe.get_doc(_DT_NR, name)
    if doc.docstatus != 0:
        raise ServiceError(ErrorCode.BAD_STATE, _("Phiếu đã submit"))
    doc.set("budget_lines", [])
    for line in lines:
        doc.append("budget_lines", line)
    if funding_source:
        doc.funding_source = funding_source
    if funding_evidence:
        doc.funding_evidence = funding_evidence
    doc.save()
    return {
        "total_capex":   doc.total_capex,
        "total_opex_5y": doc.total_opex_5y,
        "tco_5y":        doc.tco_5y,
    }


@frappe.whitelist(methods=["POST"])
def approve_needs_request(name: str, board_approver: str, remarks: str = "") -> dict:
    return _handle(_approve_needs_request, name, board_approver, remarks)


def _approve_needs_request(name: str, board_approver: str, remarks: str) -> dict:
    doc = frappe.get_doc(_DT_NR, name)
    if doc.workflow_state != "Pending Approval":
        raise ServiceError(
            ErrorCode.BAD_STATE,
            _("Chỉ phiếu ở state 'Pending Approval' mới Approve được (hiện: {0})")
            .format(doc.workflow_state),
        )
    doc.board_approver = board_approver
    doc.workflow_state = "Approved"
    doc.submit()
    if remarks:
        svc.write_audit_trail(doc, "Approval Note", "Pending Approval", "Approved", remarks)
    return {"name": doc.name, "workflow_state": "Approved"}


@frappe.whitelist(methods=["POST"])
def reject_needs_request(name: str, rejection_reason: str) -> dict:
    return _handle(_reject_needs_request, name, rejection_reason)


def _reject_needs_request(name: str, rejection_reason: str) -> dict:
    if not rejection_reason or not rejection_reason.strip():
        raise ServiceError(ErrorCode.VALIDATION, _("Phải nhập rejection_reason"))
    doc = frappe.get_doc(_DT_NR, name)
    if doc.workflow_state != "Pending Approval":
        raise ServiceError(
            ErrorCode.BAD_STATE,
            _("Chỉ phiếu Pending Approval mới Reject được (hiện: {0})")
            .format(doc.workflow_state),
        )
    doc.rejection_reason = rejection_reason
    doc.workflow_state = "Rejected"
    doc.submit()
    svc.write_audit_trail(doc, "Rejected", "Pending Approval", "Rejected", rejection_reason)
    return {"name": doc.name, "workflow_state": "Rejected"}


# ─── Procurement Plan endpoints ───────────────────────────────────────────────

@frappe.whitelist()
def list_procurement_plans(filters: str = "{}", page: int = 1, page_size: int = 20) -> dict:
    return _handle(_list_procurement_plans, filters, int(page), int(page_size))


def _list_procurement_plans(filters: str, page: int, page_size: int) -> dict:
    f = _parse_json(filters)
    fields = ["name", "plan_period", "plan_year", "budget_envelope",
              "allocated_capex", "utilization_pct", "workflow_state"]
    page_size = max(1, min(int(page_size), 100))
    start = (max(1, int(page)) - 1) * page_size
    items = frappe.get_list(
        _DT_PP, filters=f or None, fields=fields,
        order_by="plan_year desc, plan_period asc", start=start, page_length=page_size,
    )
    return {"items": items, "total": frappe.db.count(_DT_PP, filters=f or None),
            "page": page, "page_size": page_size}


@frappe.whitelist(methods=["POST"])
def roll_into_plan(plan_year: int, plan_period: str = "Annual",
                    needs_requests: str = "[]") -> dict:
    return _handle(_roll_into_plan, int(plan_year), plan_period, needs_requests)


def _roll_into_plan(plan_year: int, plan_period: str, needs_requests: str) -> dict:
    nrs = _parse_json(needs_requests, default=[])
    if not nrs:
        raise ServiceError(ErrorCode.INVALID_PARAMS, _("needs_requests không được rỗng"))
    name = svc.roll_into_plan(plan_year, plan_period, nrs)
    return {"name": name}


# ─── Demand forecast & dashboard ──────────────────────────────────────────────

@frappe.whitelist()
def get_demand_forecast(forecast_year: int, device_category: str | None = None) -> dict:
    return _handle(_get_demand_forecast, int(forecast_year), device_category)


def _get_demand_forecast(forecast_year: int, device_category: str | None) -> dict:
    filters = {"forecast_year": forecast_year}
    if device_category:
        filters["device_category"] = device_category
    items = frappe.get_list(_DT_DF, filters=filters, fields=[
        "name", "forecast_year", "horizon_years", "device_category",
        "projected_qty", "projected_capex", "accuracy_prev",
    ])
    return {"items": items}


@frappe.whitelist()
def dashboard_kpis(period: str | None = None) -> dict:
    """KPI tổng hợp IMM-01 (6 chỉ số mục 10 Module Overview).

    period: 'YYYY-Qx' (placeholder; v0.1 trả tổng hợp toàn bộ active).
    """
    return _handle(_dashboard_kpis, period)


def _dashboard_kpis(period: str | None) -> dict:
    backlog_30d = frappe.db.sql(
        f"""SELECT COUNT(*) FROM `tab{_DT_NR}`
            WHERE docstatus=0 AND workflow_state IN ('Submitted','Reviewing')
              AND DATEDIFF(CURDATE(), request_date) > 30"""
    )[0][0]

    by_state = dict(frappe.db.sql(
        f"""SELECT workflow_state, COUNT(*)
            FROM `tab{_DT_NR}` WHERE docstatus < 2
            GROUP BY workflow_state"""
    ))

    g01_pass_rate = _g01_pass_rate()

    approved_envelope = frappe.db.sql(
        f"""SELECT COALESCE(SUM(allocated_capex),0), COALESCE(SUM(budget_envelope),0)
            FROM `tab{_DT_PP}` WHERE docstatus=1"""
    )[0]
    envelope_util = (
        round(approved_envelope[0] / approved_envelope[1] * 100, 2)
        if approved_envelope[1] else 0
    )

    return {
        "backlog_over_30d":     backlog_30d,
        "by_state":             by_state,
        "g01_pass_rate":        g01_pass_rate,
        "envelope_utilization": envelope_util,
    }


def _g01_pass_rate() -> float:
    total = frappe.db.count(_DT_NR, {"docstatus": ["<", 2]})
    if not total:
        return 100.0
    submitted_or_after = frappe.db.count(_DT_NR, {
        "docstatus": ["<", 2],
        "workflow_state": ["not in", ["Draft"]],
    })
    return round(submitted_or_after / total * 100, 2)
