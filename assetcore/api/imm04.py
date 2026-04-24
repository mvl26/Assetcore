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


@frappe.whitelist()
def get_users_by_role(role: str, search: str = "", limit: int = 20) -> dict:
    """Return users with a given Frappe role, optionally filtered by name/email search."""
    like = f"%{(search or '').strip()}%"
    rows = frappe.db.sql("""
        SELECT DISTINCT u.name, u.full_name, u.email, u.user_image
        FROM `tabHas Role` hr
        JOIN `tabUser` u ON u.name = hr.parent
        WHERE hr.role = %(role)s
          AND hr.parenttype = 'User'
          AND u.enabled = 1
          AND u.user_type = 'System User'
          AND (%(search)s = '%%' OR u.full_name LIKE %(search)s OR u.email LIKE %(search)s)
        ORDER BY u.full_name ASC
        LIMIT %(limit)s
    """, {"role": role, "search": like, "limit": int(limit)}, as_dict=True)
    return _ok(rows)


@frappe.whitelist()
def get_gate_status(name: str) -> dict:
    """Return G01–G06 gate pass/fail status for a commissioning record."""
    try:
        doc = frappe.get_doc("Asset Commissioning", name)
    except frappe.DoesNotExistError:
        return _err(_("Không tìm thấy phiếu"), 404)

    # G01: all mandatory docs Received or Waived
    comm_docs = doc.get("commissioning_documents") or []
    mandatory = [d for d in comm_docs if d.get("is_mandatory")]
    g01 = all(d.get("status") in ("Received", "Waived") for d in mandatory) if mandatory else False

    # G02: facility checklist pass
    g02 = bool(doc.get("facility_checklist_pass"))

    # G03: all baseline tests Pass or N/A, at least 1 exists
    tests = doc.get("baseline_tests") or []
    g03 = bool(tests) and all(t.get("test_result") in ("Pass", "N/A") for t in tests)

    # G04: not radiation OR (radiation AND qa_license_doc uploaded)
    g04 = not bool(doc.get("is_radiation_device")) or bool(doc.get("qa_license_doc"))

    # G05: no open Non Conformance records
    open_nc = frappe.db.count("Asset QA Non Conformance",
                               filters={"parent": name, "status": ["!=", "Closed"]})
    g05 = open_nc == 0

    # G06: board_approver set
    g06 = bool(doc.get("board_approver"))

    return _ok({
        "g01_docs": g01,
        "g02_facility": g02,
        "g03_baseline": g03,
        "g04_radiation": g04,
        "g05_nc": g05,
        "g06_approver": g06,
    })


# ─── Submit-for-approval endpoints ────────────────────────────────────────────

@frappe.whitelist(methods=["POST"])
def submit_for_approval(commissioning: str, approver: str, stage: str = "",
                         remarks: str = "") -> dict:
    return _handle(svc.submit_for_approval, commissioning, approver, stage, remarks)


@frappe.whitelist(methods=["POST"])
def approve_pending(commissioning: str, decision: str, remarks: str = "") -> dict:
    return _handle(svc.approve_pending, commissioning, decision, remarks)


@frappe.whitelist()
def list_my_pending_approvals() -> dict:
    return _handle(svc.list_my_pending_approvals)


# ─── Purchase → Commissioning linkage (Wave 1) ────────────────────────────────

@frappe.whitelist(methods=["POST"])
def create_from_purchase(purchase_name: str, device_idx: int) -> dict:
    return _handle(svc.create_commissioning_from_purchase, purchase_name, int(device_idx))


@frappe.whitelist()
def get_commissioning_origin(asset_name: str) -> dict:
    return _handle(svc.get_commissioning_origin, asset_name)
