# Copyright (c) 2026, AssetCore Team
# IMM-15 Spare Parts Inventory Tracking — API Layer.
from __future__ import annotations

import json

import frappe

from assetcore.services import imm15 as svc
from assetcore.services.shared import ErrorCode, ServiceError
from assetcore.utils.helpers import _err, _ok


def _parse_json(raw, *, field_name: str, default=None):
    if not raw:
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


@frappe.whitelist()
def list_allocations(filters: str = "{}", page: int = 1,
                     page_size: int = 20) -> dict:
    try:
        f = _parse_json(filters, field_name="filters")
    except ServiceError as e:
        return _err(e.message, e.code)
    return _handle(svc.list_allocations, f, page=int(page),
                   page_size=int(page_size))


@frappe.whitelist(methods=["POST"])
def create_allocation(work_order_ref: str = "", items: str = "[]",
                      asset: str = "", warehouse: str = "",
                      urgency: str = "Routine") -> dict:
    try:
        items_list = _parse_json(items, field_name="items", default=[])
    except ServiceError as e:
        return _err(e.message, e.code)
    return _handle(svc.create_allocation, work_order_ref, items_list,
                   asset=asset, warehouse=warehouse, urgency=urgency)


@frappe.whitelist(methods=["POST"])
def issue_allocation(allocation_name: str) -> dict:
    return _handle(svc.issue_allocation, allocation_name)


@frappe.whitelist(methods=["POST"])
def return_allocation(allocation_name: str,
                      return_items: str = "[]") -> dict:
    try:
        items_list = _parse_json(return_items, field_name="return_items", default=[])
    except ServiceError as e:
        return _err(e.message, e.code)
    return _handle(svc.return_allocation, allocation_name, items_list)


@frappe.whitelist(methods=["POST"])
def create_cycle_count(warehouse: str, items: str = "[]") -> dict:
    try:
        items_list = _parse_json(items, field_name="items", default=[])
    except ServiceError as e:
        return _err(e.message, e.code)
    return _handle(svc.create_cycle_count, warehouse, items_list)


@frappe.whitelist(methods=["POST"])
def submit_cycle_count(count_name: str,
                       counted_items: str = "[]") -> dict:
    try:
        items_list = _parse_json(counted_items, field_name="counted_items", default=[])
    except ServiceError as e:
        return _err(e.message, e.code)
    return _handle(svc.submit_cycle_count, count_name, items_list)


@frappe.whitelist()
def get_stock_snapshot(warehouse: str) -> dict:
    return _handle(svc.get_stock_snapshot, warehouse)


@frappe.whitelist()
def get_critical_watchlist() -> dict:
    return _handle(svc.get_critical_watchlist)


@frappe.whitelist()
def check_part_availability(spare_part: str, warehouse: str,
                             qty_needed: float = 1.0) -> dict:
    from assetcore.services.inventory import get_available_qty
    try:
        avail = get_available_qty(warehouse, spare_part)
        return _ok({"spare_part": spare_part, "warehouse": warehouse,
                    "available_qty": avail, "qty_needed": float(qty_needed),
                    "sufficient": avail >= float(qty_needed)})
    except ServiceError as e:
        return _err(e.message, e.code)
