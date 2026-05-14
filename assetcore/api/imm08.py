# Copyright (c) 2026, AssetCore Team
# REST API cho Module IMM-08 — Preventive Maintenance.
# Tier 1 — parse HTTP input → gọi services.imm08 → _ok / _err envelope.

from __future__ import annotations

import json

import frappe
from frappe.utils import getdate, nowdate

from assetcore.services import imm08 as svc
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


def _form_dict(*strip: str) -> dict:
    """Lấy frappe.local.form_dict loại bỏ các key control."""
    data = dict(frappe.local.form_dict)
    for k in ("cmd", "doctype", *strip):
        data.pop(k, None)
    return data


# ─── PM Work Orders ───────────────────────────────────────────────────────────

@frappe.whitelist()
def list_pm_work_orders(filters: str = "{}", page: int = 1, page_size: int = 20) -> dict:
    try:
        f = _parse_json(filters, field_name="filters")
    except ServiceError as e:
        return _err(e.message, e.code)
    return _handle(svc.list_work_orders, f, page=int(page), page_size=int(page_size))


@frappe.whitelist()
def get_pm_work_order(name: str) -> dict:
    return _handle(svc.get_work_order, name)


@frappe.whitelist()
def assign_technician(name: str, technician: str, scheduled_date: str = None) -> dict:
    return _handle(svc.assign_technician, name,
                   technician=technician, scheduled_date=scheduled_date)


@frappe.whitelist()
def submit_pm_result(name: str, checklist_results: str = "[]",
                      overall_result: str = "Pass", technician_notes: str = "",
                      pm_sticker_attached: int = 0, duration_minutes: int = 0) -> dict:
    try:
        results = _parse_json(checklist_results, field_name="checklist_results", default=[])
    except ServiceError as e:
        return _err(e.message, e.code)
    return _handle(
        svc.submit_result, name,
        checklist_results=results, overall_result=overall_result,
        technician_notes=technician_notes,
        pm_sticker_attached=int(pm_sticker_attached),
        duration_minutes=int(duration_minutes),
    )


@frappe.whitelist()
def report_major_failure(pm_wo_name: str, failure_description: str,
                          failed_item_indexes: str = "[]") -> dict:
    try:
        failed = _parse_json(failed_item_indexes, field_name="failed_item_indexes", default=[])
    except ServiceError as e:
        return _err(e.message, e.code)
    return _handle(svc.report_major_failure, pm_wo_name,
                   failure_description=failure_description, failed_item_indexes=failed)


@frappe.whitelist(methods=["POST"])
def reschedule_pm(name: str, new_date: str, reason: str) -> dict:
    return _handle(svc.reschedule, name, new_date=new_date, reason=reason)


@frappe.whitelist(methods=["POST"])
def create_pm_work_order() -> dict:
    return _handle(svc.create_adhoc_work_order, _form_dict())


# ─── PM Calendar & Dashboard ─────────────────────────────────────────────────

@frappe.whitelist()
def get_pm_calendar(year: int, month: int, asset_ref: str = None,
                     technician: str = None) -> dict:
    return _handle(svc.get_calendar,
                   year=int(year), month=int(month),
                   asset_ref=asset_ref, technician=technician)


@frappe.whitelist()
def get_pm_dashboard_stats(year: int = None, month: int = None) -> dict:
    today = getdate(nowdate())
    return _handle(svc.get_dashboard_stats,
                   year=int(year) if year else today.year,
                   month=int(month) if month else today.month)


@frappe.whitelist()
def get_asset_pm_history(asset_ref: str, limit: int = 10) -> dict:
    return _handle(svc.get_asset_history, asset_ref, limit=int(limit))


# ─── PM Schedules ─────────────────────────────────────────────────────────────

@frappe.whitelist()
def list_pm_schedules(asset_ref: str = None, status: str = None,
                       page: int = 1, page_size: int = 20) -> dict:
    return _handle(svc.list_schedules,
                   asset_ref=asset_ref, status=status,
                   page=int(page), page_size=int(page_size))


@frappe.whitelist()
def get_pm_schedule(name: str) -> dict:
    return _handle(svc.get_schedule, name)


@frappe.whitelist(methods=["POST"])
def create_pm_schedule() -> dict:
    return _handle(svc.create_schedule, _form_dict())


@frappe.whitelist(methods=["POST"])
def update_pm_schedule(name: str) -> dict:
    return _handle(svc.update_schedule, name, _form_dict("name"))


@frappe.whitelist(methods=["POST"])
def set_pm_schedule_status(name: str, status: str) -> dict:
    return _handle(svc.set_schedule_status, name, status)


@frappe.whitelist(methods=["POST"])
def delete_pm_schedule(name: str) -> dict:
    return _handle(svc.delete_schedule, name)


# ─── PM Checklist Templates ──────────────────────────────────────────────────

@frappe.whitelist()
def list_pm_templates(asset_category: str = None, pm_type: str = None,
                       page: int = 1, page_size: int = 20) -> dict:
    return _handle(svc.list_templates,
                   asset_category=asset_category, pm_type=pm_type,
                   page=int(page), page_size=int(page_size))


@frappe.whitelist()
def get_pm_template(name: str) -> dict:
    return _handle(svc.get_template, name)


@frappe.whitelist(methods=["POST"])
def create_pm_template() -> dict:
    data = _form_dict()
    items_raw = data.get("checklist_items")
    if items_raw is not None:
        try:
            data["checklist_items"] = _parse_json(items_raw, field_name="checklist_items", default=[])
        except ServiceError as e:
            return _err(e.message, e.code)
    return _handle(svc.create_template, data)


@frappe.whitelist(methods=["POST"])
def update_pm_template(name: str) -> dict:
    data = _form_dict("name")
    if "checklist_items" in data:
        try:
            data["checklist_items"] = _parse_json(data["checklist_items"],
                                                   field_name="checklist_items", default=[])
        except ServiceError as e:
            return _err(e.message, e.code)
    return _handle(svc.update_template, name, data)


@frappe.whitelist(methods=["POST"])
def approve_pm_template(name: str) -> dict:
    return _handle(svc.approve_template, name)


@frappe.whitelist(methods=["POST"])
def version_pm_template(source_name: str, new_version: str) -> dict:
    return _handle(svc.version_template, source_name, new_version)


@frappe.whitelist(methods=["POST"])
def delete_pm_template(name: str) -> dict:
    return _handle(svc.delete_template, name)
