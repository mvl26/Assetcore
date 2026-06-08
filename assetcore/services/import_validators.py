# Copyright (c) 2026, AssetCore Team
"""Import pre-validators — domain rules checked BEFORE inserting into DB.

Rules:
- Validator KHÔNG insert/update DB — chỉ đọc (frappe.db.exists / frappe.db.get_value)
- Validator KHÔNG raise Exception — trả list[dict], engine tổng hợp
- severity "error" = block import; "warning" = cho phép nhưng hiện cảnh báo
- row index là 1-based (khớp với dòng người dùng nhìn thấy trong file)
- Message tiếng Việt, có giá trị cụ thể
"""
from __future__ import annotations

from typing import TypedDict

import frappe

from assetcore.utils.import_helpers import is_valid_email, is_valid_gmdn_code

# SoT DUY NHẤT — KHÔNG khai báo / re.compile regex asset_code thứ 2.
# Pattern + hằng reserved-prefix dùng CHUNG với BE create path (parity defense
# lớp 2 ở ac_asset.autoname / _validate_unique_*). Import ở module-level để
# grep-guard (test_import_asset_identity) xác minh 1-nguồn.
from assetcore.assetcore.doctype.ac_asset.ac_asset import _ASSET_CODE_PATTERN
from assetcore.services.imm00 import (
    _RESERVED_NAME_PREFIX,
    _RESERVED_NAME_SI_PREFIX,
)


class ImportError(TypedDict):
    row: int
    field: str
    message: str
    severity: str  # "error" | "warning"


def _link_lookup_set(doctype: str, display_field: str) -> set[str]:
    """Return union(doc names + display_field values) for a Link target DocType.

    Rule LL-IMP-1: import templates ask users for display names (e.g.
    "Máy chẩn đoán hình ảnh" for asset_category), but Frappe Link fields
    store doc names (system codes like "AC-CAT-2026-0001"). The
    `_RESOLVABLE_LINKS_BY_DOCTYPE` resolver in api.import_data accepts EITHER
    form before insert — so validators MUST accept either too, otherwise
    they reject valid display-name input and crash the wizard.

    Use this helper anywhere you build a "valid Link values" set and compare
    user input against it. Never collect just `r.name` and reject the rest.
    """
    names = {r.name for r in frappe.get_all(doctype, fields=["name"])}
    if not display_field:
        return names
    displays = {
        str(r.get(display_field) or "")
        for r in frappe.get_all(doctype, fields=[display_field])
    }
    displays.discard("")
    return names | displays


# ─────────────────────────────────────────────────────────────────────────────
# BASE
# ─────────────────────────────────────────────────────────────────────────────

class BaseImportValidator:
    doctype: str = ""

    def validate_row(self, row: dict, row_idx: int) -> list[ImportError]:
        return []

    def validate_all(self, rows: list[dict]) -> list[ImportError]:
        errors: list[ImportError] = []
        for i, row in enumerate(rows, start=1):
            errors.extend(self.validate_row(row, i))
        return errors

    # ── shared helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _err(row: int, field: str, msg: str) -> ImportError:
        return ImportError(row=row, field=field, message=msg, severity="error")

    @staticmethod
    def _warn(row: int, field: str, msg: str) -> ImportError:
        return ImportError(row=row, field=field, message=msg, severity="warning")

    @staticmethod
    def _req(row: dict, row_idx: int, field: str, label: str) -> ImportError | None:
        if not row.get(field):
            return ImportError(
                row=row_idx, field=field,
                message=f"'{label}' là bắt buộc",
                severity="error",
            )
        return None


# ─────────────────────────────────────────────────────────────────────────────
# AC ASSET CATEGORY
# ─────────────────────────────────────────────────────────────────────────────

class CategoryImportValidator(BaseImportValidator):
    doctype = "AC Asset Category"

    def validate_all(self, rows: list[dict]) -> list[ImportError]:
        # Cache existing names to avoid N queries
        existing: set[str] = {
            r.category_name
            for r in frappe.get_all("AC Asset Category", fields=["category_name"])
        }
        seen_in_batch: set[str] = set()
        errors: list[ImportError] = []

        for i, row in enumerate(rows, start=1):
            errors.extend(self._validate_category_row(row, i, existing, seen_in_batch))
        return errors

    def _validate_category_row(
        self, row: dict, row_idx: int,
        existing: set[str], seen: set[str],
    ) -> list[ImportError]:
        errors: list[ImportError] = []

        name = str(row.get("category_name", "")).strip()
        if not name:
            errors.append(self._err(row_idx, "category_name", "'Tên danh mục' là bắt buộc"))
            return errors

        if name in existing:
            errors.append(self._err(
                row_idx, "category_name",
                f"Danh mục '{name}' đã tồn tại trong hệ thống",
            ))
        elif name in seen:
            errors.append(self._err(
                row_idx, "category_name",
                f"Danh mục '{name}' bị trùng lặp trong file",
            ))
        seen.add(name)

        # gmdn_code format
        gmdn = str(row.get("gmdn_code", "")).strip()
        if gmdn and not is_valid_gmdn_code(gmdn):
            errors.append(self._err(
                row_idx, "gmdn_code",
                f"Mã GMDN '{gmdn}' không hợp lệ — phải là 5–6 chữ số",
            ))

        # PM cross-field
        if str(row.get("default_pm_required", "0")) in ("1", "True", "true"):
            if not row.get("default_pm_interval_days"):
                errors.append(self._err(
                    row_idx, "default_pm_interval_days",
                    "Bắt buộc khi 'Cần bảo trì định kỳ' = 1",
                ))

        # Calibration cross-field
        if str(row.get("default_calibration_required", "0")) in ("1", "True", "true"):
            if not row.get("default_calibration_interval_days"):
                errors.append(self._err(
                    row_idx, "default_calibration_interval_days",
                    "Bắt buộc khi 'Cần hiệu chuẩn' = 1",
                ))

        # depreciation_method valid values
        method = str(row.get("default_depreciation_method", "")).strip()
        valid_methods = {"", "Straight Line", "Double Declining", "Units of Production"}
        if method and method not in valid_methods:
            errors.append(self._err(
                row_idx, "default_depreciation_method",
                f"Phương pháp '{method}' không hợp lệ — chọn: Straight Line / Double Declining / Units of Production",
            ))

        return errors


# ─────────────────────────────────────────────────────────────────────────────
# AC DEPARTMENT
# ─────────────────────────────────────────────────────────────────────────────

class DepartmentImportValidator(BaseImportValidator):
    doctype = "AC Department"

    def validate_all(self, rows: list[dict]) -> list[ImportError]:
        existing: set[str] = {
            r.department_name
            for r in frappe.get_all("AC Department", fields=["department_name"])
        }
        first_seen_at: dict[str, int] = {}
        for i, r in enumerate(rows, start=1):
            name = str(r.get("department_name", "")).strip()
            if name and name not in first_seen_at:
                first_seen_at[name] = i

        batch_names: set[str] = set(first_seen_at.keys())
        seen: set[str] = set()
        errors: list[ImportError] = []

        for i, row in enumerate(rows, start=1):
            errors.extend(self._validate_dept_row(
                row, i, existing, seen, batch_names, first_seen_at,
            ))
        return errors

    def _validate_dept_row(
        self, row: dict, row_idx: int,
        existing: set[str], seen: set[str],
        batch_names: set[str],
        first_seen_at: dict[str, int],
    ) -> list[ImportError]:
        errors: list[ImportError] = []

        name = str(row.get("department_name", "")).strip()
        if not name:
            errors.append(self._err(row_idx, "department_name", "'Tên khoa/phòng' là bắt buộc"))
            return errors

        if name in existing:
            errors.append(self._err(
                row_idx, "department_name",
                f"Khoa/phòng '{name}' đã tồn tại trong hệ thống",
            ))
        elif name in seen:
            errors.append(self._err(
                row_idx, "department_name",
                f"Khoa/phòng '{name}' bị trùng lặp trong file",
            ))
        seen.add(name)

        # parent_department: phải tồn tại trong DB hoặc trong batch
        parent = str(row.get("parent_department", "")).strip()
        if parent:
            parent_in_db = frappe.db.exists("AC Department", {"department_name": parent})
            parent_in_batch = parent in batch_names and parent != name
            if not parent_in_db and not parent_in_batch:
                errors.append(self._warn(
                    row_idx, "parent_department",
                    f"Khoa cha '{parent}' chưa tồn tại — sẽ để trống",
                ))
            elif not parent_in_db:
                parent_row_idx = first_seen_at.get(parent, 0)
                if parent_row_idx > row_idx:
                    errors.append(self._warn(
                        row_idx, "parent_department",
                        f"Khoa cha '{parent}' được khai ở dòng {parent_row_idx} "
                        f"(sau dòng này) — sắp xếp lại để parent đứng trước con",
                    ))

        # email format
        email = str(row.get("email", "")).strip()
        if email and not is_valid_email(email):
            errors.append(self._err(
                row_idx, "email",
                f"Email '{email}' không đúng định dạng",
            ))

        return errors


# ─────────────────────────────────────────────────────────────────────────────
# AC LOCATION
# ─────────────────────────────────────────────────────────────────────────────

class LocationImportValidator(BaseImportValidator):
    doctype = "AC Location"

    _VALID_AREA_TYPES = {"", "ICU", "OR", "Lab", "Imaging", "General Ward", "Storage", "Office"}
    _VALID_INFECTION_LEVELS = {"", "Standard", "Enhanced", "Isolation"}

    def validate_all(self, rows: list[dict]) -> list[ImportError]:
        existing: set[str] = {
            r.location_name
            for r in frappe.get_all("AC Location", fields=["location_name"])
        }
        # Map display_name → first row index it appears in (for order warning)
        first_seen_at: dict[str, int] = {}
        for i, r in enumerate(rows, start=1):
            name = str(r.get("location_name", "")).strip()
            if name and name not in first_seen_at:
                first_seen_at[name] = i

        batch_names: set[str] = set(first_seen_at.keys())
        seen: set[str] = set()
        errors: list[ImportError] = []

        for i, row in enumerate(rows, start=1):
            errors.extend(self._validate_loc_row(
                row, i, existing, seen, batch_names, first_seen_at,
            ))
        return errors

    def _validate_loc_row(
        self, row: dict, row_idx: int,
        existing: set[str], seen: set[str],
        batch_names: set[str],
        first_seen_at: dict[str, int],
    ) -> list[ImportError]:
        errors: list[ImportError] = []

        name = str(row.get("location_name", "")).strip()
        if not name:
            errors.append(self._err(row_idx, "location_name", "'Tên vị trí' là bắt buộc"))
            return errors

        if name in existing:
            errors.append(self._err(
                row_idx, "location_name",
                f"Vị trí '{name}' đã tồn tại trong hệ thống",
            ))
        elif name in seen:
            errors.append(self._err(
                row_idx, "location_name",
                f"Vị trí '{name}' bị trùng lặp trong file",
            ))
        seen.add(name)

        # parent_location
        parent = str(row.get("parent_location", "")).strip()
        if parent:
            parent_in_db = frappe.db.exists("AC Location", {"location_name": parent})
            parent_in_batch = parent in batch_names and parent != name
            if not parent_in_db and not parent_in_batch:
                errors.append(self._warn(
                    row_idx, "parent_location",
                    f"Vị trí cha '{parent}' chưa tồn tại — sẽ để trống",
                ))
            elif not parent_in_db:
                # Parent in batch — verify order so cross-row resolve works at insert time
                parent_row_idx = first_seen_at.get(parent, 0)
                if parent_row_idx > row_idx:
                    errors.append(self._warn(
                        row_idx, "parent_location",
                        f"Vị trí cha '{parent}' được khai ở dòng {parent_row_idx} "
                        f"(sau dòng này) — sắp xếp lại để parent đứng trước con",
                    ))

        # clinical_area_type
        area = str(row.get("clinical_area_type", "")).strip()
        if area and area not in self._VALID_AREA_TYPES:
            errors.append(self._err(
                row_idx, "clinical_area_type",
                f"Khu vực lâm sàng '{area}' không hợp lệ — chọn: ICU / OR / Lab / Imaging / General Ward / Storage / Office",
            ))

        # infection_control_level
        icl = str(row.get("infection_control_level", "")).strip()
        if icl and icl not in self._VALID_INFECTION_LEVELS:
            errors.append(self._err(
                row_idx, "infection_control_level",
                f"Mức kiểm soát '{icl}' không hợp lệ — chọn: Standard / Enhanced / Isolation",
            ))

        return errors


# ─────────────────────────────────────────────────────────────────────────────
# IMM DEVICE MODEL
# ─────────────────────────────────────────────────────────────────────────────

class DeviceModelImportValidator(BaseImportValidator):
    doctype = "IMM Device Model"

    _VALID_CLASSES = {"Class I", "Class II", "Class III"}
    _VALID_CAL_TYPES = {"", "Internal", "External", "Both"}
    _NUMERIC_FIELDS = [
        ("pm_interval_days", "Chu kỳ PM"),
        ("calibration_interval_days", "Chu kỳ HC"),
        ("expected_lifespan_years", "Tuổi thọ kỳ vọng"),
        ("weight_kg", "Trọng lượng"),
    ]

    def validate_all(self, rows: list[dict]) -> list[ImportError]:
        existing: set[str] = {
            r.model_name
            for r in frappe.get_all("IMM Device Model", fields=["model_name"])
        }
        # LL-IMP-1: accept either system code or display name (category_name)
        valid_categories = _link_lookup_set("AC Asset Category", "category_name")
        seen: set[str] = set()
        errors: list[ImportError] = []
        for i, row in enumerate(rows, start=1):
            errors.extend(self._validate_model_row(row, i, existing, valid_categories, seen))
        return errors

    def _validate_model_row(
        self, row: dict, row_idx: int,
        existing: set[str], valid_categories: set[str], seen: set[str],
    ) -> list[ImportError]:
        errors: list[ImportError] = []

        name = str(row.get("model_name", "")).strip()
        if not name:
            errors.append(self._err(row_idx, "model_name", "'Tên model' là bắt buộc"))
            return errors

        if name in existing:
            errors.append(self._err(row_idx, "model_name", f"Model '{name}' đã tồn tại trong hệ thống"))
        elif name in seen:
            errors.append(self._err(row_idx, "model_name", f"Model '{name}' bị trùng lặp trong file"))
        seen.add(name)

        if not row.get("manufacturer"):
            errors.append(self._err(row_idx, "manufacturer", "'Nhà sản xuất' là bắt buộc"))

        cat = str(row.get("asset_category", "")).strip()
        if not cat:
            errors.append(self._err(row_idx, "asset_category", "'Danh mục tài sản' là bắt buộc"))
        elif cat not in valid_categories:
            errors.append(self._err(
                row_idx, "asset_category",
                f"Danh mục '{cat}' không tồn tại — kiểm tra hoặc import danh mục trước",
            ))

        cls = str(row.get("medical_device_class", "")).strip()
        if not cls:
            errors.append(self._err(row_idx, "medical_device_class", "'Phân loại thiết bị' là bắt buộc"))
        elif cls not in self._VALID_CLASSES:
            errors.append(self._err(
                row_idx, "medical_device_class",
                f"Phân loại '{cls}' không hợp lệ — chọn: Class I / Class II / Class III",
            ))

        gmdn = str(row.get("gmdn_code", "")).strip()
        if gmdn and not is_valid_gmdn_code(gmdn):
            errors.append(self._err(row_idx, "gmdn_code", f"Mã GMDN '{gmdn}' không hợp lệ — phải là 5–6 chữ số"))

        if str(row.get("is_pm_required", "0")) in ("1", "True", "true"):
            if not row.get("pm_interval_days"):
                errors.append(self._err(row_idx, "pm_interval_days", "Bắt buộc khi 'Cần bảo trì định kỳ' = 1"))

        if str(row.get("is_calibration_required", "0")) in ("1", "True", "true"):
            if not row.get("calibration_interval_days"):
                errors.append(self._err(row_idx, "calibration_interval_days", "Bắt buộc khi 'Cần hiệu chuẩn' = 1"))

        cal_type = str(row.get("default_calibration_type", "")).strip()
        if cal_type and cal_type not in self._VALID_CAL_TYPES:
            errors.append(self._err(
                row_idx, "default_calibration_type",
                f"Loại hiệu chuẩn '{cal_type}' không hợp lệ — chọn: Internal / External / Both",
            ))

        for field, label in self._NUMERIC_FIELDS:
            val = row.get(field)
            if val not in ("", None):
                try:
                    if float(str(val)) <= 0:
                        errors.append(self._err(row_idx, field, f"'{label}' phải lớn hơn 0"))
                except ValueError:
                    errors.append(self._err(row_idx, field, f"'{label}' phải là số"))

        return errors


# ─────────────────────────────────────────────────────────────────────────────
# SERVICE CONTRACT
# ─────────────────────────────────────────────────────────────────────────────

class ContractImportValidator(BaseImportValidator):
    doctype = "Service Contract"

    _VALID_TYPES = frozenset({
        "Preventive Maintenance", "Calibration", "Repair",
        "Full Service", "Warranty Extension",
    })

    def validate_all(self, rows: list[dict]) -> list[ImportError]:
        # contract_code đã unify với name (PK) — kiểm tra trùng cả 2 cột.
        existing: set[str] = {
            r.name for r in frappe.get_all("Service Contract", fields=["name"])
        }
        existing |= {
            r.contract_code
            for r in frappe.get_all("Service Contract", fields=["contract_code"])
            if r.contract_code
        }
        # LL-IMP-1: supplier accepts either system code or supplier_name
        valid_suppliers = _link_lookup_set("AC Supplier", "supplier_name")
        seen: set[str] = set()
        errors: list[ImportError] = []

        for i, row in enumerate(rows, start=1):
            errors.extend(self._validate_contract_row(row, i, existing, seen, valid_suppliers))
        return errors

    def _validate_contract_row(
        self, row: dict, row_idx: int,
        existing: set[str], seen: set[str],
        valid_suppliers: set[str],
    ) -> list[ImportError]:
        errors: list[ImportError] = []

        # Required fields — `contract_code` để trống được (autogen từ naming_series).
        for field, label in [
            ("contract_title", "Tên hợp đồng"),
            ("supplier", "Nhà cung cấp"),
            ("contract_type", "Loại hợp đồng"),
            ("contract_start", "Ngày bắt đầu"),
            ("contract_end", "Ngày kết thúc"),
        ]:
            e = self._req(row, row_idx, field, label)
            if e:
                errors.append(e)

        # Duplicate contract_code
        code = str(row.get("contract_code", "")).strip()
        if code:
            if code in existing:
                errors.append(self._err(row_idx, "contract_code",
                    f"Hợp đồng '{code}' đã tồn tại trong hệ thống"))
            elif code in seen:
                errors.append(self._err(row_idx, "contract_code",
                    f"Mã hợp đồng '{code}' bị trùng lặp trong file"))
            seen.add(code)

        # Supplier must exist (accepts either system code or supplier_name)
        supplier = str(row.get("supplier", "")).strip()
        if supplier and supplier not in valid_suppliers:
            errors.append(self._err(row_idx, "supplier",
                f"Nhà cung cấp '{supplier}' không tồn tại — tạo NCC trước khi import hợp đồng"))

        # contract_type valid values
        ctype = str(row.get("contract_type", "")).strip()
        if ctype and ctype not in self._VALID_TYPES:
            errors.append(self._err(row_idx, "contract_type",
                f"Loại '{ctype}' không hợp lệ — chọn: " + " / ".join(sorted(self._VALID_TYPES))))

        # contract_end must be >= contract_start
        start = str(row.get("contract_start", "")).strip()
        end = str(row.get("contract_end", "")).strip()
        if start and end:
            try:
                from datetime import date as _date
                if _date.fromisoformat(end) < _date.fromisoformat(start):
                    errors.append(self._err(row_idx, "contract_end",
                        f"Ngày kết thúc ({end}) phải >= ngày bắt đầu ({start})"))
            except ValueError:
                pass  # invalid date format caught by frappe insert

        return errors


# ─────────────────────────────────────────────────────────────────────────────
# USER
# ─────────────────────────────────────────────────────────────────────────────

class UserImportValidator(BaseImportValidator):
    doctype = "User"
    _VALID_STATUSES = frozenset({"Pending", "Approved", "Rejected"})

    def validate_all(self, rows: list[dict]) -> list[ImportError]:
        existing_emails: set[str] = {
            r.name for r in frappe.get_all("User", fields=["name"])
        }
        existing_roles: set[str] = {
            r.name for r in frappe.get_all("Role", fields=["name"])
        }
        # LL-IMP-1: ac_department accepts either system code or department_name
        valid_depts = _link_lookup_set("AC Department", "department_name")
        seen: set[str] = set()
        errors: list[ImportError] = []
        for i, row in enumerate(rows, start=1):
            errors.extend(self._validate_user_row(
                row, i, existing_emails, seen, existing_roles, valid_depts,
            ))
        return errors

    def _validate_user_row(
        self, row: dict, row_idx: int,
        existing_emails: set[str], seen: set[str],
        existing_roles: set[str],
        valid_depts: set[str],
    ) -> list[ImportError]:
        errors: list[ImportError] = []

        email = str(row.get("email", "")).strip()
        if not email:
            errors.append(self._err(row_idx, "email", "'Email' là bắt buộc"))
            return errors

        if not is_valid_email(email):
            errors.append(self._err(row_idx, "email", f"Email '{email}' không đúng định dạng"))
            return errors

        if email in seen:
            errors.append(self._err(row_idx, "email", f"Email '{email}' bị trùng lặp trong file"))
        elif email in existing_emails:
            errors.append(self._warn(row_idx, "email", f"Người dùng '{email}' đã tồn tại — sẽ cập nhật thông tin"))
        seen.add(email)

        first_name = str(row.get("first_name", "")).strip()
        if not first_name:
            errors.append(self._err(row_idx, "first_name", "'Tên' là bắt buộc"))

        dept = str(row.get("ac_department", "")).strip()
        if dept and dept not in valid_depts:
            errors.append(self._warn(
                row_idx, "ac_department",
                f"Khoa/phòng '{dept}' không tìm thấy trong hệ thống — sẽ để trống",
            ))

        status = str(row.get("imm_approval_status", "")).strip()
        if status and status not in self._VALID_STATUSES:
            errors.append(self._err(
                row_idx, "imm_approval_status",
                f"Trạng thái duyệt '{status}' không hợp lệ — chọn: Pending / Approved / Rejected",
            ))

        roles_raw = str(row.get("roles", "")).strip()
        if roles_raw:
            for role in (r.strip() for r in roles_raw.split(",") if r.strip()):
                if role not in existing_roles:
                    errors.append(self._warn(
                        row_idx, "roles",
                        f"Vai trò '{role}' không tồn tại trong hệ thống — sẽ bỏ qua",
                    ))

        return errors


# ─────────────────────────────────────────────────────────────────────────────
# AC ASSET
# ─────────────────────────────────────────────────────────────────────────────

class AssetImportValidator(BaseImportValidator):
    doctype = "AC Asset"

    _VALID_LIFECYCLE = frozenset({
        "", "Draft", "Commissioned", "Active",
        "Under Maintenance", "Under Repair", "Calibrating",
        "Out of Service", "Decommissioned",
    })
    _VALID_DEPRECIATION_METHODS = frozenset({
        "", "Straight Line", "Double Declining", "Units of Production",
    })

    def validate_all(self, rows: list[dict]) -> list[ImportError]:
        # LL-IMP-1: Link fields accept either system code OR display name
        categories = _link_lookup_set("AC Asset Category", "category_name")
        models     = _link_lookup_set("IMM Device Model", "model_name")
        locations  = _link_lookup_set("AC Location", "location_name")
        departments = _link_lookup_set("AC Department", "department_name")
        suppliers  = _link_lookup_set("AC Supplier", "supplier_name")
        users      = _link_lookup_set("User", "")  # User PK = email = display

        # asset_code đã được unify với name (PK) — kiểm tra trùng cả 2 cột để
        # bắt sớm trường hợp user nhập code trùng với name của asset cũ.
        existing_codes = {
            r.name for r in frappe.get_all("AC Asset", fields=["name"])
        }
        existing_codes |= {
            r.asset_code for r in frappe.get_all(
                "AC Asset", filters={"asset_code": ["!=", ""]}, fields=["asset_code"],
            ) if r.asset_code
        }
        seen_codes: set[str] = set()

        # manufacturer_sn (Số serial NSX) app-unique (ADR D3 — KHÔNG nâng DB-unique).
        # Pre-validate parity với BE _validate_unique_manufacturer_sn: chặn dup DB +
        # dup-trong-file ngay ở bước validate, tránh frappe.throw nổ mid-insert.
        existing_sns: set[str] = {
            r.manufacturer_sn for r in frappe.get_all(
                "AC Asset", filters={"manufacturer_sn": ["!=", ""]},
                fields=["manufacturer_sn"],
            ) if r.manufacturer_sn
        }
        seen_sns: set[str] = set()

        errors: list[ImportError] = []
        for i, row in enumerate(rows, start=1):
            errors.extend(self._validate_asset_row(
                row, i,
                categories, models, locations, departments, suppliers, users,
                existing_codes, seen_codes, existing_sns, seen_sns,
            ))
        return errors

    def _validate_asset_row(
        self, row: dict, row_idx: int,
        categories: set, models: set, locations: set, departments: set,
        suppliers: set, users: set,
        existing_codes: set, seen_codes: set,
        existing_sns: set, seen_sns: set,
    ) -> list[ImportError]:
        errors: list[ImportError] = []

        for field, label in [("asset_name", "Tên tài sản"), ("asset_category", "Danh mục tài sản")]:
            e = self._req(row, row_idx, field, label)
            if e:
                errors.append(e)

        # asset_code: pattern + reserved-prefix + duplicate (DB & trong-file).
        # .strip() TRƯỚC mọi check (parity create path — autoname strip giá trị user).
        code = str(row.get("asset_code", "")).strip()
        if code:
            # (1) PATTERN — SoT _ASSET_CODE_PATTERN (ac_asset). Sai pattern thì
            # asset_code không thể là PK → chặn ở đây, KHÔNG để autoname throw.
            if not _ASSET_CODE_PATTERN.match(code):
                errors.append(self._err(
                    row_idx, "asset_code",
                    "Mã tài sản chỉ được chứa chữ cái, số và các ký tự . _ - /",
                ))
            # (2) RESERVED-PREFIX — '_' (test fixtures) / 'SI-' (security-audit).
            # Dùng hằng SoT services.imm00 (KHÔNG hardcode literal lần 2). '_' / 'SI-'
            # phải ở ĐẦU chuỗi ('_' giữa tên & 'TS-' KHÔNG bị chặn).
            elif (
                code.startswith(_RESERVED_NAME_PREFIX)
                or code.upper().startswith(_RESERVED_NAME_SI_PREFIX)
            ):
                errors.append(self._err(
                    row_idx, "asset_code",
                    "Mã tài sản không được bắt đầu bằng tiền tố dành riêng "
                    f"({_RESERVED_NAME_PREFIX}, {_RESERVED_NAME_SI_PREFIX})",
                ))
            # (3) DUPLICATE (in DB and within batch)
            elif code in existing_codes:
                errors.append(self._err(
                    row_idx, "asset_code",
                    f"Mã tài sản '{code}' đã tồn tại trong hệ thống",
                ))
            elif code in seen_codes:
                errors.append(self._err(
                    row_idx, "asset_code",
                    f"Mã tài sản '{code}' bị trùng lặp trong file",
                ))
            seen_codes.add(code)

        # manufacturer_sn (Số serial NSX) — optional, mutable. Trống thì bỏ qua.
        # Parity BE _validate_unique_manufacturer_sn: dup DB / dup-trong-file.
        sn = str(row.get("manufacturer_sn", "")).strip()
        if sn:
            if sn in existing_sns:
                errors.append(self._err(
                    row_idx, "manufacturer_sn",
                    f"Số serial NSX '{sn}' đã tồn tại trong hệ thống",
                ))
            elif sn in seen_sns:
                errors.append(self._err(
                    row_idx, "manufacturer_sn",
                    f"Số serial NSX '{sn}' bị trùng lặp trong file",
                ))
            seen_sns.add(sn)

        # Link validations
        cat = str(row.get("asset_category", "")).strip()
        if cat and cat not in categories:
            errors.append(self._err(
                row_idx, "asset_category",
                f"Danh mục '{cat}' không tồn tại — kiểm tra hoặc import danh mục trước",
            ))

        model = str(row.get("device_model", "")).strip()
        if model and model not in models:
            errors.append(self._warn(
                row_idx, "device_model",
                f"Model '{model}' không tồn tại — sẽ để trống",
            ))

        loc = str(row.get("location", "")).strip()
        if loc and loc not in locations:
            errors.append(self._warn(
                row_idx, "location",
                f"Vị trí '{loc}' không tồn tại — sẽ để trống",
            ))

        dept = str(row.get("department", "")).strip()
        if dept and dept not in departments:
            errors.append(self._warn(
                row_idx, "department",
                f"Khoa/phòng '{dept}' không tồn tại — sẽ để trống",
            ))

        sup = str(row.get("supplier", "")).strip()
        if sup and sup not in suppliers:
            errors.append(self._warn(
                row_idx, "supplier",
                f"Nhà cung cấp '{sup}' không tồn tại — sẽ để trống",
            ))

        for ufield, ulabel in [
            ("custodian", "Người phụ trách"),
            ("responsible_technician", "KTV phụ trách"),
        ]:
            uv = str(row.get(ufield, "")).strip()
            if uv:
                if not is_valid_email(uv):
                    errors.append(self._err(
                        row_idx, ufield,
                        f"{ulabel} '{uv}' không đúng định dạng email",
                    ))
                elif uv not in users:
                    errors.append(self._warn(
                        row_idx, ufield,
                        f"{ulabel} '{uv}' chưa có tài khoản — sẽ để trống",
                    ))

        # lifecycle_status valid values
        ls = str(row.get("lifecycle_status", "")).strip()
        if ls and ls not in self._VALID_LIFECYCLE:
            errors.append(self._err(
                row_idx, "lifecycle_status",
                f"Trạng thái vòng đời '{ls}' không hợp lệ — chọn: "
                + " / ".join(s for s in self._VALID_LIFECYCLE if s),
            ))

        # depreciation_method valid values
        dm = str(row.get("depreciation_method", "")).strip()
        if dm and dm not in self._VALID_DEPRECIATION_METHODS:
            errors.append(self._err(
                row_idx, "depreciation_method",
                f"Phương pháp khấu hao '{dm}' không hợp lệ — chọn: Straight Line / Double Declining / Units of Production",
            ))

        # purchase_date <= warranty_expiry_date
        from datetime import date as _date
        pd_s = str(row.get("purchase_date", "")).strip()
        we_s = str(row.get("warranty_expiry_date", "")).strip()
        if pd_s and we_s:
            try:
                if _date.fromisoformat(we_s) < _date.fromisoformat(pd_s):
                    errors.append(self._err(
                        row_idx, "warranty_expiry_date",
                        f"Hết hạn bảo hành ({we_s}) phải >= ngày mua ({pd_s})",
                    ))
            except ValueError:
                pass

        # insurance_end_date >= insurance_start_date
        is_s = str(row.get("insurance_start_date", "")).strip()
        ie_s = str(row.get("insurance_end_date", "")).strip()
        if is_s and ie_s:
            try:
                if _date.fromisoformat(ie_s) < _date.fromisoformat(is_s):
                    errors.append(self._err(
                        row_idx, "insurance_end_date",
                        f"Hết hạn BH ({ie_s}) phải >= ngày bắt đầu BH ({is_s})",
                    ))
            except ValueError:
                pass

        # Numeric fields must be parseable
        for field, label in [
            ("gross_purchase_amount", "Giá mua"),
            ("residual_value", "Giá trị thu hồi"),
            ("insured_value", "Giá trị bảo hiểm"),
            ("useful_life_years", "Tuổi thọ hữu ích"),
        ]:
            val = row.get(field)
            if val not in ("", None):
                try:
                    if float(str(val)) < 0:
                        errors.append(self._err(row_idx, field, f"'{label}' không thể âm"))
                except ValueError:
                    errors.append(self._err(row_idx, field, f"'{label}' phải là số"))

        return errors


# ─────────────────────────────────────────────────────────────────────────────
# REGISTRY
# ─────────────────────────────────────────────────────────────────────────────

VALIDATOR_REGISTRY: dict[str, type[BaseImportValidator]] = {
    "AC Asset Category": CategoryImportValidator,
    "AC Department":     DepartmentImportValidator,
    "AC Location":       LocationImportValidator,
    "IMM Device Model":  DeviceModelImportValidator,
    "Service Contract":  ContractImportValidator,
    "User":              UserImportValidator,
    "AC Asset":          AssetImportValidator,
}


def get_validator(doctype: str) -> BaseImportValidator:
    cls = VALIDATOR_REGISTRY.get(doctype, BaseImportValidator)
    return cls()
