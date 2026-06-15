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
from assetcore.services.shared import rbac
from assetcore.services.shared.filters import count_with_or, pop_search
from assetcore.utils.helpers import _ok, _err

# Capability gate (LL-BE-24) — IMM Procurement Plan thuộc domain Needs.
_CAP_PLAN_CREATE = "needs.create"

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
    """Trả list Needs Request kèm display names (BE-DC-01-01).

    Data contract: mọi Link field phải kèm display name trong cùng response.
    - `requesting_department` (AC Department) → `department_name`
    - `device_model_ref` (IMM Device Model) → `device_model_name`
    - `replacement_for_asset` (AC Asset) → `target_asset_name`
    - `owner` (User) → `requester_name`
    """
    f = _parse_json(filters)
    # FE search: "mã phiếu hoặc tên model". `device_model_ref` chỉ chứa mã
    # link → muốn match `model_name` phải resolve qua link_search.
    f, or_filters = pop_search(
        f, ["name"],
        link_search={"device_model_ref": ("IMM Device Model", "model_name")},
    )
    fields = [
        "name", "request_type", "device_model_ref", "requesting_department",
        "replacement_for_asset", "owner",
        "quantity", "weighted_score", "priority_class", "workflow_state",
        "request_date", "total_capex", "tco_5y",
    ]
    page_size = max(1, min(int(page_size), 100))
    start = (max(1, int(page)) - 1) * page_size
    items = frappe.get_list(
        _DT_NR, filters=f or None, or_filters=or_filters, fields=fields,
        order_by=order_by, start=start, page_length=page_size,
    )
    _enrich_needs_display_names(items)
    total = count_with_or(_DT_NR, f or None, or_filters)
    return {"items": items, "total": total, "page": page, "page_size": page_size}


def _enrich_needs_display_names(items: list[dict]) -> None:
    """Mutates `items` in-place: thêm department_name, device_model_name,
    target_asset_name, requester_name. BE-DC-01-01.
    """
    if not items:
        return
    dept_ids   = {it.get("requesting_department")  for it in items if it.get("requesting_department")}
    model_ids  = {it.get("device_model_ref")       for it in items if it.get("device_model_ref")}
    asset_ids  = {it.get("replacement_for_asset")  for it in items if it.get("replacement_for_asset")}
    user_ids   = {it.get("owner")                  for it in items if it.get("owner")}

    dept_map  = _fetch_display_map("AC Department",     dept_ids,  "department_name")
    model_map = _fetch_display_map("IMM Device Model",  model_ids, "model_name")
    asset_map = _fetch_display_map("AC Asset",          asset_ids, "asset_name")
    user_map  = _fetch_display_map("User",              user_ids,  "full_name")

    for it in items:
        it["department_name"]    = dept_map.get(it.get("requesting_department"))
        it["device_model_name"]  = model_map.get(it.get("device_model_ref"))
        it["target_asset_name"]  = asset_map.get(it.get("replacement_for_asset"))
        it["requester_name"]     = user_map.get(it.get("owner"))


def _fetch_display_map(doctype: str, ids: set, display_field: str) -> dict:
    """Trả {id: display} cho 1 batch. Bỏ qua nếu doctype/field không tồn tại."""
    if not ids:
        return {}
    try:
        rows = frappe.get_all(
            doctype, filters={"name": ["in", list(ids)]},
            fields=["name", display_field], ignore_permissions=True,
        )
        return {r["name"]: r.get(display_field) for r in rows}
    except Exception:
        return {}


@frappe.whitelist()
def get_needs_request(name: str) -> dict:
    return _handle(_get_needs_request, name)


def _get_needs_request(name: str) -> dict:
    doc = frappe.get_doc(_DT_NR, name)
    data = doc.as_dict()
    # Enrich with human-readable department name for FE display
    if doc.requesting_department:
        data["requesting_department_name"] = frappe.db.get_value(
            "AC Department", doc.requesting_department, "department_name"
        ) or doc.requesting_department
    else:
        data["requesting_department_name"] = ""
    # Enrich asset category display name
    if doc.get("device_category"):
        data["device_category_name"] = frappe.db.get_value(
            "AC Asset Category", doc.get("device_category"), "category_name"
        ) or doc.get("device_category")
    # Enrich device model display name (BE-DC-01-01) — tránh leak mã IMM-MDL ở FE detail
    if doc.get("device_model_ref"):
        data["device_model_name"] = frappe.db.get_value(
            "IMM Device Model", doc.get("device_model_ref"), "model_name"
        ) or doc.get("device_model_ref")
    else:
        data["device_model_name"] = ""
    return data


@frappe.whitelist()
def get_allowed_transitions(name: str) -> dict:
    """Trả về các workflow action mà user hiện tại được phép thực hiện trên phiếu.

    FE dùng để render đúng các nút bấm theo role — tránh "Not a valid Workflow Action".
    """
    return _handle(_get_allowed_transitions, name)


def _get_allowed_transitions(name: str) -> dict:
    from frappe.model.workflow import get_transitions
    doc = frappe.get_doc(_DT_NR, name)
    transitions = get_transitions(doc) or []
    # `get_transitions` trả 1 row / (action × role match) — dedupe theo action.
    seen = set()
    unique = []
    for t in transitions:
        key = (t.get("action"), t.get("next_state"))
        if key in seen:
            continue
        seen.add(key)
        unique.append({"action": key[0], "next_state": key[1]})
    return {"workflow_state": doc.workflow_state, "transitions": unique}


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
                            funding_source: str = "",
                            funding_evidence: str = "") -> dict:
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
    f, or_filters = pop_search(f, ["name", "plan_period"])
    fields = ["name", "plan_period", "plan_year", "budget_envelope",
              "allocated_capex", "utilization_pct", "workflow_state"]
    page_size = max(1, min(int(page_size), 100))
    start = (max(1, int(page)) - 1) * page_size
    items = frappe.get_list(
        _DT_PP, filters=f or None, or_filters=or_filters, fields=fields,
        order_by="plan_year desc, plan_period asc", start=start, page_length=page_size,
    )
    return {"items": items, "total": count_with_or(_DT_PP, f or None, or_filters),
            "page": page, "page_size": page_size}


@frappe.whitelist()
def get_procurement_plan(name: str) -> dict:
    """Chi tiết 1 Procurement Plan (kèm plan_items)."""
    return _handle(_get_procurement_plan, name)


def _get_procurement_plan(name: str) -> dict:
    doc = frappe.get_doc(_DT_PP, name)
    payload = doc.as_dict()
    # BUG-004: plan_items chỉ chứa link tới NR — FE cần department_name + tco_5y
    # để hiển thị bảng "Danh sách Needs Request đã gom". Bulk-fetch để tránh N+1.
    items = payload.get("plan_items") or []
    nr_names = [it.get("needs_request") for it in items if it.get("needs_request")]
    if nr_names:
        nr_rows = frappe.get_all(
            _DT_NR,
            filters={"name": ["in", nr_names]},
            fields=["name", "requesting_department", "tco_5y", "weighted_score"],
        )
        nr_map = {r["name"]: r for r in nr_rows}
        dept_names = {r["requesting_department"] for r in nr_rows if r.get("requesting_department")}
        dept_map: dict[str, str] = {}
        if dept_names:
            dept_rows = frappe.get_all(
                "AC Department",
                filters={"name": ["in", list(dept_names)]},
                fields=["name", "department_name"],
            )
            dept_map = {r["name"]: r.get("department_name") or r["name"] for r in dept_rows}
        for it in items:
            nr = nr_map.get(it.get("needs_request"))
            if not nr:
                continue
            it["requesting_department"] = nr.get("requesting_department")
            it["department_name"] = dept_map.get(nr.get("requesting_department") or "", "")
            it["tco_5y"] = nr.get("tco_5y") or 0
            # Backfill weighted_score nếu line chưa snapshot (line lưu lúc roll-in)
            if not it.get("weighted_score") and nr.get("weighted_score"):
                it["weighted_score"] = nr["weighted_score"]
    return payload


@frappe.whitelist(methods=["POST"])
def create_procurement_plan(plan_year: int, plan_period: str, budget_envelope: float = 0) -> dict:
    rbac.require(_CAP_PLAN_CREATE)  # LL-BE-24: chốt chặn BE, không tin FE hide
    return _handle(_create_procurement_plan, int(plan_year), plan_period, float(budget_envelope))


def _create_procurement_plan(plan_year: int, plan_period: str, budget_envelope: float) -> dict:
    if not plan_period:
        raise ServiceError(ErrorCode.INVALID_PARAMS, _("plan_period không được rỗng"))
    doc = frappe.new_doc(_DT_PP)
    doc.plan_year = plan_year
    doc.plan_period = plan_period
    doc.budget_envelope = budget_envelope
    doc.insert(ignore_permissions=True)
    return {"name": doc.name}


@frappe.whitelist(methods=["POST"])
def set_budget_envelope(name: str, budget_envelope: float) -> dict:
    return _handle(_set_budget_envelope, name, float(budget_envelope))


def _set_budget_envelope(name: str, budget_envelope: float) -> dict:
    doc = frappe.get_doc(_DT_PP, name)
    if doc.workflow_state != "Draft":
        raise ServiceError(
            ErrorCode.BAD_STATE,
            _("Chỉ kế hoạch Draft mới cập nhật budget_envelope được (hiện: {0})")
            .format(doc.workflow_state),
        )
    doc.budget_envelope = budget_envelope
    doc.save(ignore_permissions=True)
    return doc.as_dict()


@frappe.whitelist(methods=["POST"])
def approve_plan(name: str) -> dict:
    return _handle(_approve_plan, name)


def _approve_plan(name: str) -> dict:
    doc = frappe.get_doc(_DT_PP, name)
    if doc.workflow_state != "Draft":
        raise ServiceError(
            ErrorCode.BAD_STATE,
            _("Chỉ kế hoạch Draft mới Phê duyệt được (hiện: {0})")
            .format(doc.workflow_state),
        )
    doc.workflow_state = "Approved"
    doc.approved_by = frappe.session.user
    doc.approved_date = frappe.utils.today()
    doc.save(ignore_permissions=True)
    return doc.as_dict()


@frappe.whitelist(methods=["POST"])
def activate_plan(name: str) -> dict:
    return _handle(_activate_plan, name)


def _activate_plan(name: str) -> dict:
    doc = frappe.get_doc(_DT_PP, name)
    if doc.workflow_state != "Approved":
        raise ServiceError(
            ErrorCode.BAD_STATE,
            _("Chỉ kế hoạch Approved mới Kích hoạt được (hiện: {0})")
            .format(doc.workflow_state),
        )
    doc.workflow_state = "Active"
    doc.save(ignore_permissions=True)
    return doc.as_dict()


@frappe.whitelist(methods=["POST"])
def close_plan(name: str) -> dict:
    return _handle(_close_plan, name)


def _close_plan(name: str) -> dict:
    doc = frappe.get_doc(_DT_PP, name)
    if doc.workflow_state != "Active":
        raise ServiceError(
            ErrorCode.BAD_STATE,
            _("Chỉ kế hoạch Active mới Đóng được (hiện: {0})")
            .format(doc.workflow_state),
        )
    doc.workflow_state = "Closed"
    doc.save(ignore_permissions=True)
    return doc.as_dict()


@frappe.whitelist(methods=["POST"])
def remove_from_plan(plan_name: str, needs_request: str) -> dict:
    return _handle(_remove_from_plan, plan_name, needs_request)


def _remove_from_plan(plan_name: str, needs_request: str) -> dict:
    doc = frappe.get_doc(_DT_PP, plan_name)
    row = next((r for r in doc.plan_items if r.needs_request == needs_request), None)
    if not row:
        raise ServiceError(
            ErrorCode.NOT_FOUND,
            _("Needs Request {0} không có trong kế hoạch {1}").format(needs_request, plan_name),
        )
    doc.remove(row)
    doc.save(ignore_permissions=True)
    return {"name": doc.name, "removed": needs_request}


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
def get_demand_forecast(forecast_year: int, device_category: str = "") -> dict:
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
def dashboard_kpis(period: str = "") -> dict:
    """KPI tổng hợp IMM-01 (6 chỉ số mục 10 Module Overview).

    period: 'YYYY-Qx' (placeholder; v0.1 trả tổng hợp toàn bộ active).
    `period=""` ≡ None-cũ (kỳ mặc định — placeholder không lọc theo period).
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


_PASSED_REVIEW_STATES = ["Reviewing", "Prioritized", "Budgeted", "Pending Approval", "Approved"]

def _g01_pass_rate() -> float:
    # Denominator: all submitted records (Draft excluded — hasn't entered review yet)
    total_submitted = frappe.db.count(_DT_NR, {
        "docstatus": ["<", 2],
        "workflow_state": ["not in", ["Draft"]],
    })
    if not total_submitted:
        return 0.0
    # Numerator: records that passed initial review (Rejected = fail, Submitted = pending)
    passed = frappe.db.count(_DT_NR, {
        "docstatus": ["<", 2],
        "workflow_state": ["in", _PASSED_REVIEW_STATES],
    })
    return round(passed / total_submitted * 100, 2)
