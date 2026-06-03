# Copyright (c) 2026, AssetCore Team
"""Import/Export API — Tier 1 thin wrapper.

Endpoints:
    preview_ref_data(doctype, file_url)          → parse + validate, no insert
    import_ref_data(doctype, file_url)           → validate + insert rows, return job summary
    export_ref_data(doctype)                     → download current data as xlsx
    download_template(doctype)                   → download blank Excel template
"""
from __future__ import annotations

import frappe

from assetcore.services.shared import ErrorCode, ServiceError
from assetcore.utils.response import _err, _ok


def _handle(fn, *args, **kwargs) -> dict:
    try:
        return _ok(fn(*args, **kwargs))
    except ServiceError as e:
        return _err(e.message, e.code)
    except (ValueError, FileNotFoundError) as e:
        return _err(str(e), ErrorCode.VALIDATION)
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Import API Error")
        return _err("Lỗi hệ thống — xem Error Log để biết chi tiết.", ErrorCode.INTERNAL)


# ─────────────────────────────────────────────────────────────────────────────
# SHARED CONSTANTS (used by both preview + import)
# ─────────────────────────────────────────────────────────────────────────────

# Bool fields shared across DocTypes. Add new flags here when introducing
# import templates that include them — _normalise_row() consults this set.
_BOOL_FIELDS: set[str] = {
    "is_active", "is_group", "is_transporter",
    "default_pm_required", "default_calibration_required",
    "has_radiation", "power_backup_available",
    "is_pm_required", "is_calibration_required",
    "is_radiation_device", "registration_required",
    "auto_renew",
}

# Link fields where the user fills the display name in the template but the
# Frappe field expects the doc name (system code). Resolver looks up
# display_name → name before insert.
#
# RULE (LL-BE-26): Tree DocType (is_tree=1) MUST list its nsm_parent_field here
# self-referencing — otherwise Frappe core nested_set.validate_parent_field
# crashes with "Could not find Parent <Doctype>: <display_name>".
_RESOLVABLE_LINKS_BY_DOCTYPE: dict[str, dict[str, tuple[str, str]]] = {
    "AC Asset": {
        "asset_category": ("AC Asset Category", "category_name"),
        "device_model":   ("IMM Device Model", "model_name"),
        "location":       ("AC Location", "location_name"),
        "department":     ("AC Department", "department_name"),
        "supplier":       ("AC Supplier", "supplier_name"),
    },
    "AC Location": {
        # Tree DocType — parent self-reference (LL-BE-26)
        "parent_location": ("AC Location", "location_name"),
    },
    "AC Department": {
        # Tree DocType — parent self-reference (LL-BE-26)
        "parent_department": ("AC Department", "department_name"),
    },
    "AC Warehouse": {
        "location":   ("AC Location", "location_name"),
        "department": ("AC Department", "department_name"),
    },
    "AC Spare Part": {
        "preferred_supplier": ("AC Supplier", "supplier_name"),
    },
    "Service Contract": {
        "supplier": ("AC Supplier", "supplier_name"),
    },
    "IMM Device Model": {
        "asset_category": ("AC Asset Category", "category_name"),
    },
    "User": {
        # ac_department user-fills name like "Khoa HSCC", resolve to AC-DEPT-####
        "ac_department": ("AC Department", "department_name"),
    },
}

# Link fields that are tolerated as missing — if value doesn't resolve, drop
# the field rather than fail the row. Only fields the user can legitimately
# leave unmapped at import time should go here.
_OPTIONAL_LINKS_BY_DOCTYPE: dict[str, dict[str, str]] = {
    "AC Asset": {
        "device_model": "IMM Device Model",
        "location": "AC Location",
        "department": "AC Department",
        "supplier": "AC Supplier",
        "custodian": "User",
        "responsible_technician": "User",
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# FOLDER INIT
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def init_import_folders(doctype: str) -> dict:
    """
    Create Frappe folder hierarchy and commit. FE calls this before upload_file
    so the target folder exists when Frappe validates the Link field.
    Returns: {folder: "Home/AssetCore Imports/<doctype>"} or Home/Attachments fallback.
    """
    from assetcore.utils.import_helpers import ensure_import_folder
    try:
        safe = doctype.replace(" ", "_")
        folder = ensure_import_folder(safe)
        ensure_import_folder("Error Reports")
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Init Import Folders")
        folder = "Home/Attachments"
    return _ok({"folder": folder})


# ─────────────────────────────────────────────────────────────────────────────
# PREVIEW
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist(methods=["POST"])
def preview_ref_data(doctype: str, file_url: str) -> dict:
    """
    Parse file + chạy pre-validators. KHÔNG insert.
    Returns: {total_rows, valid_rows, preview (10 dòng), errors, warnings}
    """
    return _handle(_do_preview, doctype, file_url)


def _do_preview(doctype: str, file_url: str) -> dict:
    from assetcore.services.import_validators import get_validator
    from assetcore.utils.import_helpers import (
        SUPPORTED_REF_DOCTYPES,
        parse_upload_file,
    )

    if doctype not in SUPPORTED_REF_DOCTYPES:
        raise ServiceError(
            ErrorCode.VALIDATION,
            f"DocType '{doctype}' chưa hỗ trợ import — hỗ trợ: {', '.join(SUPPORTED_REF_DOCTYPES)}",
        )

    fieldnames, rows = parse_upload_file(file_url, doctype)

    if not rows:
        raise ServiceError(ErrorCode.VALIDATION, "File không có dòng dữ liệu (từ hàng 6 trở xuống).")

    validator = get_validator(doctype)
    all_issues = validator.validate_all(rows)

    errors   = [e for e in all_issues if e["severity"] == "error"]
    warnings = [e for e in all_issues if e["severity"] == "warning"]
    invalid_rows = {e["row"] for e in errors}

    # Tree DocType: predict cascade so FE can show "5 lỗi + 2 phụ thuộc"
    # before user picks skip mode.
    _, cascade = _cascade_skip_for_tree(doctype, rows, set(invalid_rows))
    cascade_count = len(cascade)

    return {
        "doctype": doctype,
        "total_rows": len(rows),
        "valid_rows": len(rows) - len(invalid_rows) - cascade_count,
        "preview": rows[:10],
        "fieldnames": fieldnames,
        "errors": errors,
        "warnings": warnings,
        "cascade_count": cascade_count,
    }


# ─────────────────────────────────────────────────────────────────────────────
# CASCADE HELPER (Tree DocType skip propagation)
# ─────────────────────────────────────────────────────────────────────────────

def _cascade_skip_for_tree(
    doctype: str,
    rows: list[dict],
    invalid_idx: set[int],
) -> tuple[set[int], list[dict]]:
    """If DocType is Tree and a parent row is skipped, propagate skip to all
    descendants in the same batch. Avoids orphan tree nodes and "Could not
    find Parent" crashes downstream. Returns (final_invalid_idx, extra_skip).
    """
    if not invalid_idx:
        return invalid_idx, []

    try:
        meta = frappe.get_meta(doctype)
    except Exception:
        return invalid_idx, []
    if not getattr(meta, "is_tree", 0):
        return invalid_idx, []

    parent_field = getattr(meta, "nsm_parent_field", None)
    cfg = _RESOLVABLE_LINKS_BY_DOCTYPE.get(doctype, {}).get(parent_field or "")
    if not parent_field or not cfg:
        return invalid_idx, []
    _, display_field = cfg

    skipped_names: set[str] = {
        str(rows[i - 1].get(display_field, "")).strip()
        for i in invalid_idx
        if 1 <= i <= len(rows) and str(rows[i - 1].get(display_field, "")).strip()
    }

    extra_skip: list[dict] = []
    changed = True
    while changed:
        changed = False
        for i, row in enumerate(rows, start=1):
            if i in invalid_idx:
                continue
            parent_val = str(row.get(parent_field, "")).strip()
            if parent_val and parent_val in skipped_names:
                invalid_idx.add(i)
                extra_skip.append({
                    "row": i,
                    "reason": "cascade_parent_skipped",
                    "field": parent_field,
                    "message": f"Cha '{parent_val}' đã bị bỏ qua → bỏ qua dòng này",
                })
                own_name = str(row.get(display_field, "")).strip()
                if own_name:
                    skipped_names.add(own_name)
                changed = True

    return invalid_idx, extra_skip


# ─────────────────────────────────────────────────────────────────────────────
# IMPORT
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist(methods=["POST"])
def import_ref_data(doctype: str, file_url: str, skip_invalid: bool = False) -> dict:
    """
    Validate + insert rows trực tiếp (không qua Frappe Data Import engine).
    Reference data không có side-effects → direct insert an toàn.

    skip_invalid=False (mặc định): có lỗi pre-validate → ServiceError, abort.
    skip_invalid=True: bỏ qua dòng lỗi (+ cascade child cho Tree DocType),
        vẫn insert phần hợp lệ. KHÔNG hỗ trợ cho `User` doctype.

    Returns: {total, success, failed, skipped, errors, skipped_rows}
    """
    return _handle(_do_import, doctype, file_url, skip_invalid)


def _do_import(doctype: str, file_url: str, skip_invalid: bool = False) -> dict:
    from assetcore.services.import_validators import get_validator
    from assetcore.utils.import_helpers import (
        SUPPORTED_REF_DOCTYPES,
        parse_upload_file,
    )

    if doctype not in SUPPORTED_REF_DOCTYPES:
        raise ServiceError(
            ErrorCode.VALIDATION,
            f"DocType '{doctype}' chưa hỗ trợ import",
        )

    _, rows = parse_upload_file(file_url, doctype)
    if not rows:
        raise ServiceError(ErrorCode.VALIDATION, "File không có dòng dữ liệu.")

    # ── Pre-validate ───────────────────────────────────────────────────────
    validator = get_validator(doctype)
    issues = validator.validate_all(rows)
    blocking = [e for e in issues if e["severity"] == "error"]

    invalid_idx: set[int] = set()
    skipped_rows: list[dict] = []

    if blocking:
        if not skip_invalid:
            raise ServiceError(
                ErrorCode.VALIDATION,
                f"File có {len(blocking)} lỗi bắt buộc phải sửa trước khi import. "
                "Dùng Preview để xem chi tiết hoặc bật 'Bỏ qua dòng lỗi'.",
            )
        # User import chưa hỗ trợ skip (upsert logic riêng — xem _do_import_users)
        if doctype == "User":
            raise ServiceError(
                ErrorCode.VALIDATION,
                "Chế độ 'Bỏ qua dòng lỗi' chưa hỗ trợ cho import Người dùng. "
                "Vui lòng sửa file và import lại.",
            )

        for e in blocking:
            invalid_idx.add(e["row"])
            skipped_rows.append({
                "row": e["row"],
                "reason": "pre_validate",
                "field": e["field"],
                "message": e["message"],
            })

        # Tree DocType: skip child cũng nếu parent bị skip (avoid orphans)
        invalid_idx, cascade = _cascade_skip_for_tree(doctype, rows, invalid_idx)
        skipped_rows.extend(cascade)

        if len(invalid_idx) >= len(rows):
            raise ServiceError(
                ErrorCode.VALIDATION,
                "Không có dòng hợp lệ nào để import — toàn bộ file lỗi.",
            )

    # ── Insert ─────────────────────────────────────────────────────────────
    if doctype == "User":
        return _do_import_users(rows)

    resolvable_links = _RESOLVABLE_LINKS_BY_DOCTYPE.get(doctype, {})
    optional_links = _OPTIONAL_LINKS_BY_DOCTYPE.get(doctype, {})

    results: dict = {
        "total": len(rows),
        "success": 0,
        "failed": 0,
        "skipped": len(invalid_idx),
        "errors": [],
        "skipped_rows": skipped_rows,
    }

    for i, row in enumerate(rows, start=1):
        if i in invalid_idx:
            continue
        try:
            clean = _normalise_row(row, _BOOL_FIELDS)
            _resolve_links(clean, resolvable_links)
            _drop_unresolved_optional_links(clean, optional_links)

            # AC Asset: workflow only allows new docs at "Draft". Capture the
            # desired status so we can transition AFTER insert (mirrors the
            # logic in api.imm00.create_asset for non-procurement assets).
            desired_status = ""
            if doctype == "AC Asset":
                desired_status = (clean.get("lifecycle_status") or "").strip()
                clean["lifecycle_status"] = "Draft"

            doc = frappe.new_doc(doctype)
            doc.update(clean)
            doc.insert(ignore_permissions=True)

            if doctype == "AC Asset" and desired_status and desired_status != "Draft":
                _transition_asset_lifecycle(doc.name, desired_status)
            results["success"] += 1
        except Exception as e:
            frappe.log_error(f"Import row {i} failed: {e}", "Import Ref Data")
            results["failed"] += 1
            results["errors"].append({
                "row": i,
                "field": "",
                "message": _friendly_frappe_error(str(e)),
                "severity": "error",
            })

    frappe.db.commit()
    return results


def _resolve_links(clean: dict, resolvable: dict[str, tuple[str, str]]) -> None:
    """Resolve display name → doc name for Link fields. Mutates `clean` in-place.

    Tree DocType cross-row resolve in same batch works because frappe.db
    queries see the write-through transaction state after each doc.insert().
    """
    for fld, (link_dt, display_field) in resolvable.items():
        val = clean.get(fld)
        if not val or frappe.db.exists(link_dt, val):
            continue   # empty, or already a valid doc name (system code)
        resolved = frappe.db.get_value(link_dt, {display_field: val}, "name")
        if resolved:
            clean[fld] = resolved
        # else: leave value; Frappe core will surface "Could not find <Link>"


def _drop_unresolved_optional_links(clean: dict, optional: dict[str, str]) -> None:
    """Drop Link values that don't resolve, so insert won't fail on optional FKs."""
    for fld, link_dt in optional.items():
        val = clean.get(fld)
        if val and not frappe.db.exists(link_dt, val):
            clean.pop(fld, None)


def _transition_asset_lifecycle(asset_name: str, desired_status: str) -> None:
    """Walk the AC Asset workflow from Draft to desired_status.

    Workflow path: Draft → Commissioned → Active. Other terminal/branch states
    (Out of Service, Decommissioned, ...) are not reachable in bulk import and
    silently ignored so a bad CSV row doesn't trap the asset mid-flight.
    """
    from assetcore.services.imm00 import transition_asset_status

    chain: list[str] = []
    if desired_status == "Commissioned":
        chain = ["Commissioned"]
    elif desired_status == "Active":
        chain = ["Commissioned", "Active"]
    else:
        return
    for step in chain:
        transition_asset_status(asset_name, to_status=step, reason="Bulk import")


def _normalise_row(row: dict, bool_fields: set[str]) -> dict:
    """Convert string values to proper Python types for frappe.new_doc."""
    out: dict = {}
    for k, v in row.items():
        if v == "" or v is None:
            continue
        if k in bool_fields:
            out[k] = 1 if str(v) in ("1", "True", "true", "yes") else 0
        else:
            out[k] = v
    return out


def _friendly_frappe_error(msg: str) -> str:
    """Extract meaningful part from Frappe exception strings."""
    if "Duplicate entry" in msg:
        return "Bản ghi đã tồn tại (trùng tên hoặc mã)."
    if "cannot be null" in msg.lower() or "mandatory" in msg.lower():
        return "Thiếu trường bắt buộc."
    return msg[:200]


def _do_import_users(rows: list[dict]) -> dict:
    """Upsert Frappe Users — insert new, update existing; assign roles additively.

    Resolves `ac_department` display name → AC-DEPT-#### code (LL-BE-26).
    """
    results: dict = {
        "total": len(rows), "success": 0, "failed": 0,
        "skipped": 0, "errors": [], "skipped_rows": [],
    }
    _USER_FIELDS = ("first_name", "last_name", "mobile_no", "ac_department", "imm_approval_status")
    user_resolvable = _RESOLVABLE_LINKS_BY_DOCTYPE.get("User", {})

    for i, row in enumerate(rows, start=1):
        try:
            email = str(row.get("email", "")).strip()
            if not email:
                raise ValueError("Email là bắt buộc")

            is_new = not frappe.db.exists("User", email)
            user = frappe.new_doc("User") if is_new else frappe.get_doc("User", email)

            if is_new:
                user.email = email
                user.send_welcome_email = 0

            # Resolve display-name → system code for Link fields (ac_department etc.)
            staged = {f: str(row.get(f, "")).strip() for f in _USER_FIELDS if row.get(f)}
            _resolve_links(staged, user_resolvable)
            for field, val in staged.items():
                setattr(user, field, val)

            if is_new:
                user.insert(ignore_permissions=True)
            else:
                user.save(ignore_permissions=True)

            # Add roles listed in file (additive — never removes existing roles)
            roles_raw = str(row.get("roles", "")).strip()
            if roles_raw:
                user_doc = frappe.get_doc("User", email)
                existing = {hr.role for hr in user_doc.get("roles", [])}
                new_roles = [
                    r.strip() for r in roles_raw.split(",")
                    if r.strip() and r.strip() not in existing and frappe.db.exists("Role", r.strip())
                ]
                if new_roles:
                    user_doc.add_roles(*new_roles)

            results["success"] += 1
        except Exception as e:
            frappe.log_error(f"Import User row {i} failed: {e}", "Import User Data")
            results["failed"] += 1
            results["errors"].append({
                "row": i, "field": "",
                "message": _friendly_frappe_error(str(e)),
                "severity": "error",
            })

    frappe.db.commit()
    return results


# ─────────────────────────────────────────────────────────────────────────────
# EXPORT
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def export_ref_data(doctype: str):
    """Download current data as Excel. Returns file as response attachment."""
    from assetcore.utils.import_helpers import (
        SUPPORTED_REF_DOCTYPES,
        export_ref_data as _export,
    )

    if doctype not in SUPPORTED_REF_DOCTYPES:
        frappe.throw(f"DocType '{doctype}' không hỗ trợ export")

    try:
        xlsx_bytes = _export(doctype)
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Export Ref Data Error")
        frappe.throw(f"Lỗi khi tạo file export: {e}")

    safe_name = doctype.replace(" ", "_").lower()
    filename = f"export_{safe_name}.xlsx"

    frappe.local.response.filename = filename
    frappe.local.response.filecontent = xlsx_bytes
    frappe.local.response.type = "download"


# ─────────────────────────────────────────────────────────────────────────────
# DOWNLOAD TEMPLATE
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def download_template(doctype: str):
    """Serve blank Excel import template for the given DocType."""
    from assetcore.utils.import_helpers import get_template_path

    try:
        path = get_template_path(doctype)
    except (ValueError, FileNotFoundError) as e:
        frappe.throw(str(e))

    with open(path, "rb") as f:
        content = f.read()

    import os
    filename = os.path.basename(path)
    frappe.local.response.filename = filename
    frappe.local.response.filecontent = content
    frappe.local.response.type = "download"


# ─────────────────────────────────────────────────────────────────────────────
# BUILD ERROR REPORT (for FE download)
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist(methods=["POST"])
def build_error_report(doctype: str, file_url: str) -> dict:
    """
    Parse file, run validators, return error report as uploaded File URL.
    FE calls this to get a downloadable xlsx with highlighted error rows.
    """
    return _handle(_do_build_error_report, doctype, file_url)


def _do_build_error_report(doctype: str, file_url: str) -> dict:
    from frappe.utils.file_manager import save_file

    from assetcore.services.import_validators import get_validator
    from assetcore.utils.import_helpers import (
        build_error_report,
        ensure_import_folder,
        parse_upload_file,
    )

    fieldnames, rows = parse_upload_file(file_url, doctype)
    validator = get_validator(doctype)
    errors = validator.validate_all(rows)

    xlsx_bytes = build_error_report(fieldnames, rows, errors)

    folder = ensure_import_folder("Error Reports")
    fname = f"error_report_{doctype.replace(' ', '_').lower()}.xlsx"
    file_doc = save_file(fname, xlsx_bytes, dt="", dn="", folder=folder, is_private=1)

    return {"file_url": file_doc.file_url, "error_count": len(errors)}
