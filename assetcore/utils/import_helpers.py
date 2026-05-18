# Copyright (c) 2026, AssetCore Team
"""Import/Export helper utilities — parse uploaded Excel, build error reports, export data."""
from __future__ import annotations

import io
import re
from typing import Any

import frappe

_LABEL_SYSTEM_CODE = "Mã hệ thống"

# Mapping doctype → (fieldname, tiếng Việt label, export fields)
_REF_DATA_CONFIG: dict[str, dict] = {
    "AC Asset Category": {
        "name_field": "category_name",
        "export_fields": [
            "name", "category_name", "description", "gmdn_code", "gmdn_term",
            "default_pm_required", "default_pm_interval_days",
            "default_calibration_required", "default_calibration_interval_days",
            "default_depreciation_method", "total_depreciation_months",
            "depreciation_frequency", "default_residual_value_pct",
            "has_radiation", "is_active",
        ],
        "export_labels": {
            "name": _LABEL_SYSTEM_CODE,
            "category_name": "Tên danh mục",
            "description": "Mô tả",
            "gmdn_code": "Mã GMDN",
            "gmdn_term": "Tên GMDN",
            "default_pm_required": "Cần bảo trì ĐK",
            "default_pm_interval_days": "Chu kỳ PM (ngày)",
            "default_calibration_required": "Cần hiệu chuẩn",
            "default_calibration_interval_days": "Chu kỳ HC (ngày)",
            "default_depreciation_method": "PP khấu hao",
            "total_depreciation_months": "Thời gian KH (tháng)",
            "depreciation_frequency": "Tần suất KH",
            "default_residual_value_pct": "Giá trị thu hồi (%)",
            "has_radiation": "Có bức xạ",
            "is_active": "Đang hoạt động",
        },
    },
    "AC Department": {
        "name_field": "department_name",
        "export_fields": [
            "name", "department_name", "department_code", "parent_department",
            "is_group", "dept_head", "phone", "email", "is_active",
        ],
        "export_labels": {
            "name": _LABEL_SYSTEM_CODE,
            "department_name": "Tên khoa/phòng",
            "department_code": "Mã khoa",
            "parent_department": "Khoa cha",
            "is_group": "Là nhóm cha",
            "dept_head": "Trưởng khoa",
            "phone": "Điện thoại",
            "email": "Email",
            "is_active": "Đang hoạt động",
        },
    },
    "AC Location": {
        "name_field": "location_name",
        "export_fields": [
            "name", "location_name", "location_code", "parent_location",
            "is_group", "clinical_area_type", "infection_control_level",
            "power_backup_available", "emergency_contact", "dept_head",
            "technical_contact", "notes",
        ],
        "export_labels": {
            "name": _LABEL_SYSTEM_CODE,
            "location_name": "Tên vị trí",
            "location_code": "Mã vị trí",
            "parent_location": "Vị trí cha",
            "is_group": "Là nhóm cha",
            "clinical_area_type": "Khu vực lâm sàng",
            "infection_control_level": "Kiểm soát nhiễm khuẩn",
            "power_backup_available": "Có UPS/máy phát",
            "emergency_contact": "Liên hệ khẩn cấp",
            "dept_head": "Phụ trách",
            "technical_contact": "KTV phụ trách",
            "notes": "Ghi chú",
        },
    },
}

SUPPORTED_REF_DOCTYPES = list(_REF_DATA_CONFIG.keys())

# ─────────────────────────────────────────────────────────────────────────────
# PARSE UPLOADED FILE
# ─────────────────────────────────────────────────────────────────────────────

def parse_upload_file(file_url: str) -> tuple[list[str], list[dict]]:
    """
    Parse AssetCore import template (Excel/CSV).

    Template row layout:
        Row 1 — banner (skip)
        Row 2 — fieldnames  ← use as column headers
        Row 3 — VN labels   (skip)
        Row 4 — description (skip)
        Row 5 — example     (skip)
        Row 6+ — data

    Returns (fieldnames, rows) where rows is list[dict] keyed by fieldname.
    """
    file_doc = frappe.db.get_value("File", {"file_url": file_url}, "name")
    if not file_doc:
        raise ValueError(f"Không tìm thấy file: {file_url}")
    fdoc = frappe.get_doc("File", file_doc)
    file_path = fdoc.get_full_path()

    if file_url.lower().endswith((".xlsx", ".xls")):
        return _parse_excel(file_path)
    return _parse_csv(file_path)


def _parse_excel(file_path: str) -> tuple[list[str], list[dict]]:
    try:
        from openpyxl import load_workbook
    except ImportError as e:
        raise RuntimeError("openpyxl chưa được cài đặt trong bench env") from e

    wb = load_workbook(file_path, data_only=True)
    ws = wb.active

    rows_raw = list(ws.iter_rows(values_only=True))
    if len(rows_raw) < 2:
        raise ValueError("File rỗng hoặc thiếu dòng header (fieldname).")

    # Row index 1 (0-based) = fieldnames
    fieldnames: list[str] = [str(c).strip() if c is not None else "" for c in rows_raw[1]]

    # Data starts at row index 5 (0-based), skip example row at index 4
    data_rows = rows_raw[5:]
    return fieldnames, _rows_to_dicts(fieldnames, data_rows)


def _parse_csv(file_path: str) -> tuple[list[str], list[dict]]:
    import csv
    with open(file_path, encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        all_rows = list(reader)

    if len(all_rows) < 2:
        raise ValueError("File CSV rỗng hoặc thiếu dòng header.")

    fieldnames = [c.strip() for c in all_rows[1]]
    data_rows_raw = [tuple(r) for r in all_rows[5:]]
    return fieldnames, _rows_to_dicts(fieldnames, data_rows_raw)


def _normalise_cell(val: Any) -> Any:
    if val is None or (isinstance(val, str) and not val.strip()):
        return ""
    return val.strip() if isinstance(val, str) else val


def _rows_to_dicts(fieldnames: list[str], raw_rows) -> list[dict]:
    result = []
    for raw in raw_rows:
        row: dict[str, Any] = {
            fn: _normalise_cell(raw[i] if i < len(raw) else None)
            for i, fn in enumerate(fieldnames)
            if fn
        }
        if any(v not in ("", None) for v in row.values()):
            result.append(row)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# BUILD ERROR REPORT
# ─────────────────────────────────────────────────────────────────────────────

def build_error_report(fieldnames: list[str], rows: list[dict], errors: list[dict]) -> bytes:
    """Return xlsx bytes with error rows highlighted, plus Status + Ghi chú columns."""
    try:
        from openpyxl import Workbook
        from openpyxl.styles import PatternFill, Font
    except ImportError as e:
        raise RuntimeError("openpyxl chưa được cài đặt") from e

    error_map: dict[int, list[str]] = {}
    for e in errors:
        error_map.setdefault(e["row"], []).append(f"[{e['field']}] {e['message']}")

    wb = Workbook()
    ws = wb.active
    ws.title = "Lỗi import"

    header = fieldnames + ["Trạng thái", "Ghi chú lỗi"]
    ws.append(header)
    for cell in ws[1]:
        cell.font = Font(bold=True)

    red_fill = PatternFill("solid", fgColor="FFCCCC")
    ok_fill = PatternFill("solid", fgColor="CCFFCC")

    for i, row in enumerate(rows, start=1):
        data = [row.get(fn, "") for fn in fieldnames]
        notes = error_map.get(i, [])
        status = "Lỗi" if notes else "OK"
        ws.append(data + [status, "; ".join(notes)])
        xl_row = ws[ws.max_row]
        fill = red_fill if notes else ok_fill
        for cell in xl_row:
            cell.fill = fill

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# EXPORT CURRENT DATA
# ─────────────────────────────────────────────────────────────────────────────

def export_ref_data(doctype: str) -> bytes:
    """Export all records of a ref-data DocType to xlsx bytes."""
    if doctype not in _REF_DATA_CONFIG:
        raise ValueError(f"DocType '{doctype}' không hỗ trợ export")

    try:
        from openpyxl import Workbook
        from openpyxl.styles import PatternFill, Font
    except ImportError as e:
        raise RuntimeError("openpyxl chưa được cài đặt") from e

    cfg = _REF_DATA_CONFIG[doctype]
    fields = cfg["export_fields"]
    labels = cfg["export_labels"]

    rows = frappe.get_all(doctype, fields=fields, order_by="creation asc")

    wb = Workbook()
    ws = wb.active
    ws.title = doctype

    # Header row: Vietnamese labels
    label_row = [labels.get(f, f) for f in fields]
    ws.append(label_row)
    header_fill = PatternFill("solid", fgColor="2E4053")
    header_font = Font(bold=True, color="FFFFFF")
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font

    # Fieldname row (for re-import)
    ws.append(fields)
    fn_fill = PatternFill("solid", fgColor="D6EAF8")
    for cell in ws[2]:
        cell.fill = fn_fill

    for i, row in enumerate(rows):
        data = [row.get(f) for f in fields]
        ws.append(data)
        # Stripe rows
        if i % 2 == 1:
            stripe = PatternFill("solid", fgColor="F8F9FA")
            for cell in ws[ws.max_row]:
                cell.fill = stripe

    # Auto-width
    for col in ws.columns:
        max_len = max((len(str(cell.value or "")) for cell in col), default=10)
        ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 40)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# TEMPLATE PATH
# ─────────────────────────────────────────────────────────────────────────────

_TMPL_IMM00 = "02_imm00_ncc_model_hopdong_sla.xlsx"

_TEMPLATE_MAP: dict[str, str] = {
    "AC Asset Category": "01a_danh_muc_tai_san.xlsx",
    "AC Department":     "01b_khoa_phong.xlsx",
    "AC Location":       "01c_vi_tri.xlsx",
    "AC Supplier":       _TMPL_IMM00,
    "IMM Device Model":  _TMPL_IMM00,
    "Service Contract":  _TMPL_IMM00,
    "IMM SLA Policy":    _TMPL_IMM00,
    "AC Asset":          "03_danh_sach_tai_san.xlsx",
    "AC Spare Part":     "04_danh_sach_phu_tung.xlsx",
    "AC Warehouse":      "05_kho_hang.xlsx",
    "User":              "06_danh_sach_nguoi_dung.xlsx",
}

# Templates nằm ở assetcore/public/import_templates/
# frappe.get_app_path("assetcore") trả về <bench>/apps/assetcore/assetcore
_TEMPLATE_BASE = None


def _get_template_base() -> str:
    global _TEMPLATE_BASE
    if _TEMPLATE_BASE is None:
        import os
        _TEMPLATE_BASE = os.path.join(frappe.get_app_path("assetcore"), "public", "import_templates")
    return _TEMPLATE_BASE


def get_template_path(doctype: str) -> str:
    import os
    filename = _TEMPLATE_MAP.get(doctype)
    if not filename:
        raise ValueError(f"Không có template cho DocType '{doctype}'")
    path = os.path.join(_get_template_base(), filename)
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Template file không tồn tại: {path}. "
            "Chạy docs/imports/generate_templates.py để sinh lại."
        )
    return path


# ─────────────────────────────────────────────────────────────────────────────
# FRAPPE FOLDER MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────

_IMPORT_FOLDER_ROOT = "Home/AssetCore Imports"


def ensure_import_folder(sub: str = "") -> str:
    """
    Create Frappe folder hierarchy and commit so subsequent upload_file can find it.
    Returns the folder path (e.g. "Home/AssetCore Imports/AC_Department").
    """
    from frappe.core.api.file import create_new_folder

    _create_if_missing(create_new_folder, _IMPORT_FOLDER_ROOT, "Home")
    if not sub:
        frappe.db.commit()
        return _IMPORT_FOLDER_ROOT

    path = f"{_IMPORT_FOLDER_ROOT}/{sub}"
    _create_if_missing(create_new_folder, path, _IMPORT_FOLDER_ROOT)
    frappe.db.commit()
    return path


def _create_if_missing(create_fn, path: str, parent: str) -> None:
    if frappe.db.exists("File", path):
        return
    try:
        create_fn(path.rsplit("/", 1)[-1], parent)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Import Folder Creation")


# ─────────────────────────────────────────────────────────────────────────────
# VALIDATION HELPER
# ─────────────────────────────────────────────────────────────────────────────

def is_valid_email(value: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", value))


def is_valid_gmdn_code(value: str) -> bool:
    """GMDN code: 5 hoặc 6 chữ số."""
    return bool(re.match(r"^\d{5,6}$", value.strip()))
