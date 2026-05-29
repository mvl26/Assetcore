# Copyright (c) 2026, AssetCore Team
# REST API cho Module IMM-04 — Asset Commissioning.
# Tier 1 — parse HTTP input → gọi services.imm04 → _ok / _err envelope.

from __future__ import annotations

import frappe
from frappe import _

from assetcore.services import imm04 as svc
from assetcore.services.shared import ErrorCode, ServiceError
from assetcore.services.shared import rbac
from assetcore.utils.api_handler import handle as _handle
from assetcore.utils.api_handler import parse_json as _parse_json
from assetcore.utils.helpers import _err, _ok

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
def search_link(
    doctype: str,
    query: str = "",
    page_length: int = 10,
    filters: str = "",
) -> dict:
    """Whitelisted Link-search. `filters` is a JSON string of dynamic filters
    (only fields in config.dynamic_filter_fields are honored — others ignored).
    """
    import json
    extra: dict = {}
    if filters:
        try:
            parsed = json.loads(filters)
            if isinstance(parsed, dict):
                extra = parsed
        except (ValueError, TypeError):
            pass
    return _handle(svc.search_link, doctype, query, int(page_length), extra)


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
    # AUTH-02 — workflow transition needs write capability on commissioning.
    rbac.require("commissioning.write")
    return _handle(svc.transition_state, name, action)


@frappe.whitelist(methods=["POST"])
def submit_commissioning(name: str) -> dict:
    rbac.require("commissioning.submit")
    return _handle(svc.submit_commissioning, name)


@frappe.whitelist(methods=["POST"])
def save_commissioning(name: str, fields: str | dict | None = None) -> dict:
    rbac.require("commissioning.write")
    try:
        parsed = _parse_json(fields, field_name="fields")
    except ServiceError as e:
        return _err(e.message, e.code)
    return _handle(svc.save_commissioning, name, parsed)


@frappe.whitelist(methods=["POST"])
def create_commissioning(data: str | dict | None = None) -> dict:
    rbac.require("commissioning.create")
    try:
        parsed = _parse_json(data, field_name="data")
    except ServiceError as e:
        return _err(e.message, e.code)
    return _handle(svc.create_commissioning, parsed)


@frappe.whitelist(methods=["POST"])
def report_nonconformance(commissioning_name: str, nc_data: str | dict | None = None) -> dict:
    rbac.require("commissioning.write")
    try:
        parsed = _parse_json(nc_data, field_name="nc_data")
    except ServiceError as e:
        return _err(e.message, e.code)
    return _handle(svc.report_nonconformance, commissioning_name, parsed)


@frappe.whitelist(methods=["POST"])
def close_nonconformance(nc_name: str, root_cause: str = "", corrective_action: str = "") -> dict:
    rbac.require("commissioning.write")
    return _handle(svc.close_nonconformance, nc_name, root_cause, corrective_action)


@frappe.whitelist(methods=["POST"])
def assign_identification(name: str, vendor_serial_no: str = "",
                          internal_tag_qr: str = "", custom_moh_code: str = "") -> dict:
    rbac.require("commissioning.write")
    return _handle(svc.assign_identification, name, vendor_serial_no, internal_tag_qr, custom_moh_code)


@frappe.whitelist(methods=["POST"])
def generate_internal_qr(name: str) -> dict:
    """BUG-009: Manual QR generation endpoint. Idempotent — chỉ sinh nếu chưa có."""
    rbac.require("commissioning.write")
    return _handle(svc.generate_internal_qr, name)


@frappe.whitelist(methods=["POST"])
def submit_baseline_checklist(name: str, results: str | list | None = None) -> dict:
    rbac.require("commissioning.write")
    try:
        parsed = _parse_json(results, field_name="results", default=[])
    except ServiceError as e:
        return _err(e.message, e.code)
    return _handle(svc.submit_baseline_checklist, name, parsed)


@frappe.whitelist(methods=["POST"])
def clear_clinical_hold(name: str, license_no: str = "") -> dict:
    rbac.require("commissioning.write")
    return _handle(svc.clear_clinical_hold, name, license_no)


@frappe.whitelist(methods=["POST"])
def retry_mint_asset(name: str) -> dict:
    """Retry minting AC Asset for a Clinical Release commissioning where minting failed."""
    rbac.require("commissioning.submit")
    return _handle(_retry_mint_asset, name)


def _retry_mint_asset(name: str) -> dict:
    doc = frappe.get_doc("Asset Commissioning", name)
    if doc.workflow_state != "Clinical Release":
        raise ServiceError(ErrorCode.BAD_STATE, "Chỉ retry được khi ở Clinical Release")
    if doc.final_asset:
        return {"name": name, "final_asset": doc.final_asset, "already_minted": True}
    asset_name = svc.create_ac_asset(doc)
    frappe.db.set_value("Asset Commissioning", name, "final_asset", asset_name)
    return {"name": name, "final_asset": asset_name}


@frappe.whitelist(methods=["POST"])
def upload_document(commissioning: str, doc_index: int, doc_type: str = "",
                    file_url: str = "", expiry_date: str = "", doc_number: str = "") -> dict:
    rbac.require("commissioning.write")
    return _handle(svc.upload_document, commissioning, doc_index, file_url, expiry_date, doc_number)


@frappe.whitelist(methods=["POST"])
def approve_clinical_release(commissioning: str, board_approver: str,
                              approval_remarks: str = "") -> dict:
    # AUTH-02 + AUTH-05 — board approval is the final 4-eyes gate before
    # AC Asset is minted. Must be Commissioning Manager (cannot be done by
    # any role with FE button hidden).
    rbac.require("commissioning.submit")
    return _handle(svc.approve_clinical_release, commissioning, board_approver, approval_remarks)


@frappe.whitelist(methods=["POST"])
def report_doa(commissioning: str, description: str) -> dict:
    rbac.require("commissioning.write")
    return _handle(svc.report_doa, commissioning, description)


@frappe.whitelist(methods=["POST"])
def delete_commissioning(name: str) -> dict:
    rbac.require("commissioning.delete")
    return _handle(svc.delete_commissioning, name)


@frappe.whitelist(methods=["POST"])
def cancel_commissioning(name: str) -> dict:
    rbac.require("commissioning.cancel")
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
                               filters={"ref_commissioning": name, "resolution_status": ["!=", "Closed"]})
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
    # AUTH-02 — submitter must have write permission; 4-eyes enforced in service.
    rbac.require("commissioning.write")
    return _handle(svc.submit_for_approval, commissioning, approver, stage, remarks)


@frappe.whitelist(methods=["POST"])
def approve_pending(commissioning: str, decision: str, remarks: str = "") -> dict:
    # AUTH-02 + AUTH-05 — approval is submit-tier; 4-eyes (self-submit + dup
    # signer) enforced in service.
    rbac.require("commissioning.submit")
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


@frappe.whitelist()
def get_lifecycle_timeline(name: str) -> dict:
    """Return audit/lifecycle events for an Asset Commissioning record.

    RC-05 fix: source-of-truth is `IMM Audit Trail` filtered by
    (ref_doctype = "Asset Commissioning", ref_name = <commissioning>). The legacy
    child table `lifecycle_events` is also merged for backward compatibility, but
    is empty for records created after the DocType refactor (the Table field no
    longer exists in the DocType JSON).
    """
    doc = frappe.get_doc("Asset Commissioning", name)

    # Primary: IMM Audit Trail
    audit_rows = frappe.get_all(
        "IMM Audit Trail",
        filters={"ref_doctype": "Asset Commissioning", "ref_name": name},
        fields=["name", "event_type", "from_status", "to_status", "actor",
                "timestamp", "change_summary", "ip_address"],
        order_by="timestamp asc, creation asc",
        limit_page_length=500,
    )
    events = [
        {
            "idx": idx + 1,
            "event_type": r.get("event_type") or "",
            "from_status": r.get("from_status") or "",
            "to_status": r.get("to_status") or "",
            "actor": r.get("actor") or "",
            "event_timestamp": str(r.get("timestamp") or ""),
            "remarks": r.get("change_summary") or "",
            "ip_address": r.get("ip_address") or "",
        }
        for idx, r in enumerate(audit_rows)
    ]

    # Legacy fallback: any child rows that may still exist on older records
    for row in (doc.get("lifecycle_events") or []):
        events.append({
            "idx": row.idx,
            "event_type": row.get("event_type") or "",
            "from_status": row.get("from_status") or "",
            "to_status": row.get("to_status") or "",
            "actor": row.get("actor") or "",
            "event_timestamp": str(row.get("event_timestamp") or ""),
            "remarks": row.get("remarks") or "",
            "ip_address": row.get("ip_address") or "",
        })

    return _ok({"events": events})
