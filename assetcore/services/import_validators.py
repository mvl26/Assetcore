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


class ImportError(TypedDict):
    row: int
    field: str
    message: str
    severity: str  # "error" | "warning"


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
        # Also collect names from this batch (for parent_department validation)
        batch_names: set[str] = {
            str(r.get("department_name", "")).strip()
            for r in rows if r.get("department_name")
        }
        seen: set[str] = set()
        errors: list[ImportError] = []

        for i, row in enumerate(rows, start=1):
            errors.extend(self._validate_dept_row(row, i, existing, seen, batch_names))
        return errors

    def _validate_dept_row(
        self, row: dict, row_idx: int,
        existing: set[str], seen: set[str],
        batch_names: set[str],
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
        batch_names: set[str] = {
            str(r.get("location_name", "")).strip()
            for r in rows if r.get("location_name")
        }
        seen: set[str] = set()
        errors: list[ImportError] = []

        for i, row in enumerate(rows, start=1):
            errors.extend(self._validate_loc_row(row, i, existing, seen, batch_names))
        return errors

    def _validate_loc_row(
        self, row: dict, row_idx: int,
        existing: set[str], seen: set[str],
        batch_names: set[str],
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
# REGISTRY
# ─────────────────────────────────────────────────────────────────────────────

VALIDATOR_REGISTRY: dict[str, type[BaseImportValidator]] = {
    "AC Asset Category": CategoryImportValidator,
    "AC Department":     DepartmentImportValidator,
    "AC Location":       LocationImportValidator,
    # Thêm validators khác khi mở rộng scope import
}


def get_validator(doctype: str) -> BaseImportValidator:
    cls = VALIDATOR_REGISTRY.get(doctype, BaseImportValidator)
    return cls()
