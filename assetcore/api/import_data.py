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

    return {
        "doctype": doctype,
        "total_rows": len(rows),
        "valid_rows": len(rows) - len({e["row"] for e in errors}),
        "preview": rows[:10],
        "fieldnames": fieldnames,
        "errors": errors,
        "warnings": warnings,
    }


# ─────────────────────────────────────────────────────────────────────────────
# IMPORT
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist(methods=["POST"])
def import_ref_data(doctype: str, file_url: str) -> dict:
    """
    Validate + insert rows trực tiếp (không qua Frappe Data Import engine).
    Reference data không có side-effects → direct insert an toàn.
    Returns: {total, success, failed, errors}
    """
    return _handle(_do_import, doctype, file_url)


def _do_import(doctype: str, file_url: str) -> dict:
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

    # Pre-validate — block nếu có lỗi critical
    validator = get_validator(doctype)
    issues = validator.validate_all(rows)
    blocking = [e for e in issues if e["severity"] == "error"]
    if blocking:
        raise ServiceError(
            ErrorCode.VALIDATION,
            f"File có {len(blocking)} lỗi bắt buộc phải sửa trước khi import. Dùng Preview để xem chi tiết.",
        )

    if doctype == "User":
        return _do_import_users(rows)

    results: dict = {"total": len(rows), "success": 0, "failed": 0, "errors": []}
    _BOOL_FIELDS = {
        "is_active", "is_group", "is_transporter",
        "default_pm_required", "default_calibration_required",
        "has_radiation", "power_backup_available",
        # IMM Device Model
        "is_pm_required", "is_calibration_required",
        "is_radiation_device", "registration_required",
        # Service Contract
        "auto_renew",
    }

    for i, row in enumerate(rows, start=1):
        try:
            doc = frappe.new_doc(doctype)
            # Normalise types before assigning
            clean = _normalise_row(row, _BOOL_FIELDS)
            doc.update(clean)
            doc.insert(ignore_permissions=True)
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
    """Upsert Frappe Users — insert new, update existing; assign roles additively."""
    results: dict = {"total": len(rows), "success": 0, "failed": 0, "errors": []}
    _USER_FIELDS = ("first_name", "last_name", "mobile_no", "ac_department", "imm_approval_status")

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

            for field in _USER_FIELDS:
                val = str(row.get(field, "")).strip()
                if val:
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
