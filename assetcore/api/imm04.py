# Copyright (c) 2026, AssetCore Team
# REST API cho Module IMM-04 — Asset Commissioning.
# Tier 1 — parse HTTP input → gọi services.imm04 → _ok / _err envelope.

from __future__ import annotations

import json

import frappe

from assetcore.services import imm04 as svc
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
    except frappe.ValidationError as e:
        return _err(str(e), "VALIDATION_ERROR")
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), f"IMM-04 {fn.__name__}")
        return _err(str(e), "SYSTEM_ERROR")


# ─── Read Endpoints ───────────────────────────────────────────────────────────

@frappe.whitelist()
def get_form_context(name: str) -> dict:
    return _handle(svc.get_form_context, name)


@frappe.whitelist()
def list_commissioning(filters: str = "{}", page: int = 1, page_size: int = 20) -> dict:
    try:
        f = _parse_json(filters, field_name="filters")
    except ServiceError as e:
        return _err(e.message, e.code)
    return _handle(svc.list_commissioning, f, int(page), int(page_size))


@frappe.whitelist()
def get_barcode_lookup(barcode: str) -> dict:
    return _handle(svc.get_barcode_lookup, barcode)


@frappe.whitelist()
def get_dashboard_stats() -> dict:
    return _handle(svc.get_dashboard_stats)


@frappe.whitelist()
def generate_qr_label(name: str) -> dict:
    return _handle(svc.generate_qr_label, name)


@frappe.whitelist()
def get_po_details(po_name: str) -> dict:
    return _handle(svc.get_po_details, po_name)


@frappe.whitelist()
def search_link(doctype: str, query: str = "", page_length: int = 10) -> dict:
    return _handle(svc.search_link, doctype, query, int(page_length))


@frappe.whitelist()
def check_sn_unique(vendor_sn: str, exclude_name: str = "") -> dict:
    return _handle(svc.check_sn_unique, vendor_sn, exclude_name)


@frappe.whitelist()
def list_non_conformances(commissioning: str) -> dict:
    return _handle(svc.list_non_conformances, commissioning)


@frappe.whitelist()
def generate_handover_pdf(name: str) -> dict:
    return _handle(svc.generate_handover_pdf, name)


# ─── Write Endpoints ──────────────────────────────────────────────────────────

@frappe.whitelist(methods=["POST"])
def transition_state(name: str, action: str) -> dict:
    return _handle(svc.transition_state, name, action)


@frappe.whitelist(methods=["POST"])
def submit_commissioning(name: str) -> dict:
    return _handle(svc.submit_commissioning, name)


@frappe.whitelist(methods=["POST"])
def save_commissioning(name: str, fields: str | dict | None = None) -> dict:
    try:
        parsed = _parse_json(fields, field_name="fields")
    except ServiceError as e:
        return _err(e.message, e.code)
    return _handle(svc.save_commissioning, name, parsed)


@frappe.whitelist(methods=["POST"])
def create_commissioning(data: str | dict | None = None) -> dict:
    try:
        parsed = _parse_json(data, field_name="data")
    except ServiceError as e:
        return _err(e.message, e.code)
    return _handle(svc.create_commissioning, parsed)


@frappe.whitelist(methods=["POST"])
def report_nonconformance(commissioning_name: str, nc_data: str | dict | None = None) -> dict:
    try:
        parsed = _parse_json(nc_data, field_name="nc_data")
    except ServiceError as e:
        return _err(e.message, e.code)
    return _handle(svc.report_nonconformance, commissioning_name, parsed)


@frappe.whitelist(methods=["POST"])
def close_nonconformance(nc_name: str, root_cause: str = "", corrective_action: str = "") -> dict:
    return _handle(svc.close_nonconformance, nc_name, root_cause, corrective_action)


@frappe.whitelist(methods=["POST"])
def assign_identification(name: str, vendor_serial_no: str = "",
                          internal_tag_qr: str = "", custom_moh_code: str = "") -> dict:
    return _handle(svc.assign_identification, name, vendor_serial_no, internal_tag_qr, custom_moh_code)


@frappe.whitelist(methods=["POST"])
def submit_baseline_checklist(name: str, results: str | list | None = None) -> dict:
    try:
        parsed = _parse_json(results, field_name="results", default=[])
    except ServiceError as e:
        return _err(e.message, e.code)
    return _handle(svc.submit_baseline_checklist, name, parsed)


@frappe.whitelist(methods=["POST"])
def clear_clinical_hold(name: str, license_no: str = "") -> dict:
    return _handle(svc.clear_clinical_hold, name, license_no)


@frappe.whitelist(methods=["POST"])
def upload_document(commissioning: str, doc_index: int, doc_type: str = "",
                    file_url: str = "", expiry_date: str = "", doc_number: str = "") -> dict:
    return _handle(svc.upload_document, commissioning, doc_index, file_url, expiry_date, doc_number)


@frappe.whitelist(methods=["POST"])
def approve_clinical_release(commissioning: str, board_approver: str,
                              approval_remarks: str = "") -> dict:
    return _handle(svc.approve_clinical_release, commissioning, board_approver, approval_remarks)


@frappe.whitelist(methods=["POST"])
def report_doa(commissioning: str, description: str) -> dict:
    return _handle(svc.report_doa, commissioning, description)


@frappe.whitelist(methods=["POST"])
def delete_commissioning(name: str) -> dict:
    return _handle(svc.delete_commissioning, name)


@frappe.whitelist(methods=["POST"])
def cancel_commissioning(name: str) -> dict:
    return _handle(svc.cancel_commissioning, name)
