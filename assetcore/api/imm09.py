# Copyright (c) 2026, AssetCore Team
# IMM-09 Corrective Maintenance — Tier 1 API Layer.

from __future__ import annotations

import datetime
import json

import frappe
from frappe.utils import getdate, nowdate

from assetcore.services import imm09 as svc
from assetcore.services.shared import ErrorCode, ServiceError
from assetcore.utils.helpers import _err, _ok


def _parse_json(raw: str | list | dict | None, *, field_name: str, default=None):
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
def list_repair_work_orders(filters: str = "{}", page: int = 1, page_size: int = 20):
    try:
        f = _parse_json(filters, field_name="filters")
    except ServiceError as e:
        return _err(e.message, e.code)
    return _handle(svc.list_work_orders, f, page=int(page), page_size=int(page_size))


@frappe.whitelist()
def get_repair_work_order(name: str):
    return _handle(svc.get_work_order, name)


@frappe.whitelist()
def create_repair_work_order(asset_ref: str, repair_type: str, priority: str,
                              failure_description: str, incident_report: str = "",
                              source_pm_wo: str = "") -> dict:
    return _handle(
        svc.create_work_order,
        asset_ref=asset_ref, repair_type=repair_type, priority=priority,
        failure_description=failure_description,
        incident_report=incident_report, source_pm_wo=source_pm_wo,
    )


@frappe.whitelist()
def assign_technician(name: str, technician: str, priority: str = ""):
    return _handle(svc.assign_technician, name, technician=technician, priority=priority)


@frappe.whitelist()
def submit_diagnosis(name: str, diagnosis_notes: str, needs_parts: int = 0):
    return _handle(svc.submit_diagnosis, name,
                   diagnosis_notes=diagnosis_notes,
                   needs_parts=int(needs_parts))


@frappe.whitelist(methods=["POST"])
def start_repair(name: str) -> dict:
    return _handle(svc.start_repair, name)


@frappe.whitelist()
def request_spare_parts(name: str, parts: str = "[]"):
    try:
        parts_list = _parse_json(parts, field_name="parts", default=[])
    except ServiceError as e:
        return _err(e.message, e.code)
    return _handle(svc.request_spare_parts, name, parts_list)


@frappe.whitelist()
def close_work_order(name: str, repair_summary: str, root_cause_category: str,
                     dept_head_name: str, checklist_results: str = "[]",
                     spare_parts: str = "[]", firmware_updated: int = 0,
                     firmware_change_request: str = "", cannot_repair: int = 0,
                     cannot_repair_reason: str = ""):
    try:
        checklist = _parse_json(checklist_results, field_name="checklist_results", default=[])
        parts = _parse_json(spare_parts, field_name="spare_parts", default=[])
    except ServiceError as e:
        return _err(e.message, e.code)
    return _handle(
        svc.close_work_order, name,
        repair_summary=repair_summary, root_cause_category=root_cause_category,
        dept_head_name=dept_head_name, checklist_results=checklist,
        spare_parts=parts, firmware_updated=int(firmware_updated),
        firmware_change_request=firmware_change_request,
        cannot_repair=int(cannot_repair), cannot_repair_reason=cannot_repair_reason,
    )


@frappe.whitelist()
def get_repair_kpis(year: int = None, month: int = None):
    today = getdate(nowdate())
    return _handle(svc.get_kpis,
                   int(year) if year else today.year,
                   int(month) if month else today.month)


@frappe.whitelist()
def get_asset_repair_history(asset_ref: str, limit: int = 10):
    return _handle(svc.get_asset_history, asset_ref, limit=int(limit))


@frappe.whitelist()
def search_spare_parts(query: str = "", limit: int = 10) -> dict:
    return _handle(svc.search_spare_parts, query, limit=int(limit))


@frappe.whitelist()
def get_mttr_report(year: int = None, month: int = None) -> dict:
    today = getdate(nowdate())
    return _handle(svc.get_mttr_report,
                   int(year) if year else today.year,
                   int(month) if month else today.month)
