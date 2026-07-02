# Copyright (c) 2026, AssetCore Team
# IMM-15 Spare Parts Inventory Tracking — API Layer (Tier 1).
#
# All endpoints follow the envelope {success, data} | {success:false, error, code}.
# Reference: docs/imm-15/05_API_Specification.md §3
from __future__ import annotations

import json

import frappe

from assetcore.services import imm15 as svc
from assetcore.services.shared import ErrorCode, ServiceError
from assetcore.utils.helpers import _err, _ok


def _parse_json(raw, *, field_name: str, default=None):
    if raw is None or raw == "":
        return default if default is not None else {}
    if not isinstance(raw, str):
        return raw
    try:
        return json.loads(raw)
    except (ValueError, TypeError) as e:
        raise ServiceError(ErrorCode.INVALID_PARAMS,
                           f"{field_name} không phải JSON hợp lệ") from e


def _handle(fn, *args, **kwargs) -> dict:
    try:
        return _ok(fn(*args, **kwargs))
    except ServiceError as e:
        return _err(e.message, e.code)
    except Exception as e:  # noqa: BLE001
        frappe.log_error(frappe.get_traceback(), f"IMM-15 API error in {fn.__name__}")
        return _err(str(e) or "Lỗi máy chủ", ErrorCode.INTERNAL)


# ─── Allocations ─────────────────────────────────────────────────────────────

@frappe.whitelist()
def list_allocations(filters: str = "{}", page: int = 1,
                     page_size: int = 20,
                     workflow_state: str = "",
                     asset: str = "",
                     work_order_ref: str = "",
                     urgency: str = "") -> dict:
    """§3.1 GET list_allocations"""
    try:
        f = _parse_json(filters, field_name="filters", default={})
    except ServiceError as e:
        return _err(e.message, e.code)
    # Merge explicit query params
    if workflow_state:
        f["allocation_status"] = workflow_state
    if asset:
        f["asset"] = asset
    if work_order_ref:
        f["work_order_ref"] = work_order_ref
    if urgency:
        f["urgency"] = urgency
    return _handle(svc.list_allocations, f, page=int(page), page_size=int(page_size))


@frappe.whitelist()
def get_allocation(name: str) -> dict:
    return _handle(svc.get_allocation, name)


@frappe.whitelist(methods=["POST"])
def create_allocation(work_order_ref: str = "", items: str = "[]",
                      asset: str = "", warehouse: str = "",
                      warehouse_from: str = "",
                      urgency: str = "Routine",
                      work_order_doctype: str = "",
                      required_date: str = "") -> dict:
    """§3.2 POST create_allocation"""
    try:
        items_list = _parse_json(items, field_name="items", default=[])
    except ServiceError as e:
        return _err(e.message, e.code)
    wh = warehouse or warehouse_from
    return _handle(svc.create_allocation, work_order_ref, items_list,
                   asset=asset, warehouse=wh, urgency=urgency)


@frappe.whitelist(methods=["POST"])
def approve_allocation(allocation: str = "", name: str = "") -> dict:
    """§3.3 POST approve_allocation"""
    return _handle(svc.approve_allocation, allocation or name)


@frappe.whitelist(methods=["POST"])
def issue_allocation(allocation: str = "", name: str = "",
                     allocation_name: str = "",
                     items: str = "[]") -> dict:
    """§3.4 POST issue_allocation"""
    # `items` param accepted for future per-line qty_issued override; ignored otherwise
    return _handle(svc.issue_allocation, allocation or name or allocation_name)


@frappe.whitelist(methods=["POST"])
def return_items(allocation: str = "", name: str = "",
                 items: str = "[]") -> dict:
    """§3.5 POST return_items (renamed from return_allocation)."""
    try:
        items_list = _parse_json(items, field_name="items", default=[])
    except ServiceError as e:
        return _err(e.message, e.code)
    return _handle(svc.return_items, allocation or name, items_list)


@frappe.whitelist(methods=["POST"])
def return_allocation(allocation_name: str = "",
                      return_items: str = "[]") -> dict:
    """Deprecated alias of return_items — kept for backward compat."""
    try:
        items_list = _parse_json(return_items, field_name="return_items", default=[])
    except ServiceError as e:
        return _err(e.message, e.code)
    return _handle(svc.return_items, allocation_name, items_list)


@frappe.whitelist(methods=["POST"])
def cancel_allocation(allocation: str = "", name: str = "") -> dict:
    """§III-bis.3 POST cancel_allocation — hủy phiếu (release reserved)."""
    return _handle(svc.cancel_allocation, allocation or name)


# ─── Cycle Counts ─────────────────────────────────────────────────────────────

@frappe.whitelist()
def list_cycle_counts(filters: str = "{}", page: int = 1,
                      page_size: int = 20, status: str = "",
                      warehouse: str = "") -> dict:
    try:
        f = _parse_json(filters, field_name="filters", default={})
    except ServiceError as e:
        return _err(e.message, e.code)
    if status:
        f["status"] = status
    if warehouse:
        f["warehouse"] = warehouse
    return _handle(svc.list_cycle_counts, f, page=int(page), page_size=int(page_size))


@frappe.whitelist()
def get_cycle_count(name: str = "") -> dict:
    """§3.6 GET get_cycle_count — header + item lines + allowed_transitions.

    Not-found → 404 envelope (KHÔNG 500) via _handle → ServiceError(NOT_FOUND).
    """
    return _handle(svc.get_cycle_count, name)


@frappe.whitelist(methods=["POST"])
def create_cycle_count(warehouse: str, spare_parts: str = "[]",
                       items: str = "[]",
                       count_type: str = "Cycle",
                       count_date: str = "") -> dict:
    """§3.6 POST create_cycle_count"""
    raw = spare_parts if spare_parts and spare_parts != "[]" else items
    try:
        parsed = _parse_json(raw, field_name="spare_parts", default=[])
    except ServiceError as e:
        return _err(e.message, e.code)
    # Accept array of part names or array of dicts
    if parsed and isinstance(parsed[0], str):
        parsed = [{"spare_part": sp} for sp in parsed]
    return _handle(svc.create_cycle_count, warehouse, parsed,
                   count_type=count_type, count_date=count_date)


@frappe.whitelist(methods=["POST"])
def submit_cycle_count(count_name: str = "", name: str = "",
                       counted_items: str = "[]") -> dict:
    """Internal: review step (Planned/Counting → Reviewed)."""
    try:
        items_list = _parse_json(counted_items, field_name="counted_items", default=[])
    except ServiceError as e:
        return _err(e.message, e.code)
    return _handle(svc.submit_cycle_count, count_name or name, items_list)


@frappe.whitelist(methods=["POST"])
def post_cycle_count(cycle_count: str = "", name: str = "",
                     verified_by: str = "", notes: str = "") -> dict:
    """§3.7 POST post_cycle_count (rename from submit_cycle_count)."""
    return _handle(svc.post_cycle_count, cycle_count or name,
                   verified_by=verified_by, notes=notes)


# ─── Forecast ─────────────────────────────────────────────────────────────────

@frappe.whitelist()
def list_spare_forecasts(filters: str = "{}", page: int = 1,
                         page_size: int = 20) -> dict:
    try:
        f = _parse_json(filters, field_name="filters", default={})
    except ServiceError as e:
        return _err(e.message, e.code)
    return _handle(svc.list_spare_forecasts, f, page=int(page), page_size=int(page_size))


@frappe.whitelist(methods=["POST"])
def generate_spare_forecast(horizon_months: int = 3,
                            method: str = "Moving_Avg",
                            forecast_period: str = "") -> dict:
    """§3.8 POST generate_spare_forecast"""
    return _handle(svc.generate_spare_forecast,
                   horizon_months=int(horizon_months or 3),
                   method=method, forecast_period=forecast_period)


@frappe.whitelist(methods=["POST"])
def approve_forecast(forecast: str = "", name: str = "") -> dict:
    """§3.9 POST approve_forecast"""
    return _handle(svc.approve_forecast, forecast or name)


# ─── Watchlist ────────────────────────────────────────────────────────────────

@frappe.whitelist()
def list_watchlist(filters: str = "{}", page: int = 1,
                   page_size: int = 50, active_only: int = 1) -> dict:
    try:
        f = _parse_json(filters, field_name="filters", default={})
    except ServiceError as e:
        return _err(e.message, e.code)
    if int(active_only):
        f.setdefault("active", 1)
    return _handle(svc.list_watchlist, f, page=int(page), page_size=int(page_size))


@frappe.whitelist(methods=["POST"])
def add_to_watchlist(watchlist_name: str, critical_asset: str,
                     spare_part: str, min_required_on_hand: float,
                     warehouse: str) -> dict:
    """§3.10 POST add_to_watchlist"""
    return _handle(svc.add_to_watchlist, watchlist_name=watchlist_name,
                   critical_asset=critical_asset, spare_part=spare_part,
                   min_required_on_hand=float(min_required_on_hand or 0),
                   warehouse=warehouse)


# ─── Availability / Stock / Dashboard ────────────────────────────────────────

@frappe.whitelist()
def check_part_availability(spare_part: str = "", warehouse: str = "",
                            qty_needed: float = 1.0,
                            items: str = "",
                            include_alternatives: int = 0) -> dict:
    """§3.11 GET check_part_availability — supports single & bulk."""
    from assetcore.services.inventory import get_available_qty
    try:
        if items:
            items_list = _parse_json(items, field_name="items", default=[])
            results = []
            all_ok = True
            for it in items_list:
                sp = it.get("spare_part")
                qty = float(it.get("qty", 0))
                avail = get_available_qty(warehouse, sp)
                sufficient = avail >= qty
                if not sufficient:
                    all_ok = False
                part_class = frappe.db.get_value("AC Spare Part", sp, "imm_part_class")
                results.append({
                    "spare_part": sp,
                    "part_name": frappe.db.get_value("AC Spare Part", sp, "part_name") or sp,
                    "qty_on_hand": avail,
                    "reserved_qty": 0,
                    "available_qty": avail,
                    "qty_needed": qty,
                    "sufficient": sufficient,
                    "imm_part_class": part_class,
                    "imm_alternative_parts": [],
                })
            return _ok({"warehouse": warehouse, "results": results,
                        "all_sufficient": all_ok})
        # single-part fallback
        avail = get_available_qty(warehouse, spare_part)
        return _ok({"spare_part": spare_part, "warehouse": warehouse,
                    "available_qty": avail, "qty_needed": float(qty_needed),
                    "sufficient": avail >= float(qty_needed)})
    except ServiceError as e:
        return _err(e.message, e.code)


@frappe.whitelist()
def get_stock_snapshot(warehouse: str) -> dict:
    return _handle(svc.get_stock_snapshot, warehouse)


@frappe.whitelist()
def get_critical_watchlist() -> dict:
    """Legacy: list breaching watchlist entries (different from list_watchlist)."""
    return _handle(svc.get_critical_watchlist)


@frappe.whitelist()
def get_dashboard_stats(period: str = "") -> dict:
    """§3.12 GET get_dashboard_stats"""
    return _handle(svc.get_dashboard_stats, period=period)


@frappe.whitelist()
def get_low_stock_alerts(warehouse: str = "") -> dict:
    """§3.13 GET get_low_stock_alerts"""
    return _handle(svc.get_low_stock_alerts, warehouse=warehouse)
