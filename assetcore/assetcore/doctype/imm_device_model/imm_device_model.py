# Copyright (c) 2026, AssetCore Team
import frappe
from frappe import _
from frappe.model.document import Document


# BR-00-01: Class -> Risk mapping per NĐ 98/2021
_CLASS_RISK_MAP = {
    ("Class I", False): "Low",
    ("Class I", True): "Low",
    ("Class II", False): "Medium",
    ("Class II", True): "Medium",
    ("Class III", False): "High",
    ("Class III", True): "Critical",
}


class IMMDeviceModel(Document):
    """IMM Device Model - Master template for a model line of medical devices."""

    def before_insert(self) -> None:
        """Inherit PM / Calibration defaults from Asset Category on creation."""
        self._inherit_pm_calibration_defaults()

    def validate(self) -> None:
        """Enforce BR-00-01 class -> risk mapping + GMDN P3 inherited flag."""
        self._auto_map_risk_classification()
        self._validate_unique_model_manufacturer()
        self._set_gmdn_inherited_flag()

    def _set_gmdn_inherited_flag(self) -> None:
        """C2 (P3 Hybrid): xác định gmdn_inherited.

        - gmdn_code rỗng (kế thừa lười / chưa có) → inherited = 1.
        - gmdn_code == Category.gmdn_code → kế thừa → inherited = 1.
        - gmdn_code khác Category.gmdn_code → override cố ý → inherited = 0.

        Ref: docs/res/plans/2026-05-19-gmdn-code-sync-strategy.md §5.1 P3.
        """
        cat_code = None
        if self.asset_category:
            cat_code = frappe.db.get_value(
                "AC Asset Category", self.asset_category, "gmdn_code"
            )
        # gmdn_code may arrive as int from bulk import (openpyxl yields a
        # numeric cell as int) — coerce before string ops.
        my_code = str(self.gmdn_code or "").strip()
        if not my_code or my_code == str(cat_code or "").strip():
            self.gmdn_inherited = 1
        else:
            self.gmdn_inherited = 0

    def _inherit_pm_calibration_defaults(self) -> None:
        """Copy PM / Calibration defaults from Asset Category if user hasn't set them.

        Only fills fields that are empty (None / 0 / '') so explicit user input
        is never overridden.
        """
        if not self.asset_category:
            return
        cat = frappe.db.get_value(
            "AC Asset Category",
            self.asset_category,
            [
                "default_pm_required",
                "default_pm_interval_days",
                "default_calibration_required",
                "default_calibration_interval_days",
                "gmdn_code",
                "gmdn_term",
            ],
            as_dict=True,
        )
        if not cat:
            return
        # GMDN: inherit từ category nếu model chưa có
        if not self.gmdn_code and cat.get("gmdn_code"):
            self.gmdn_code = cat["gmdn_code"]
        if not self.gmdn_term and cat.get("gmdn_term"):
            self.gmdn_term = cat["gmdn_term"]
        if not self.is_pm_required and cat.get("default_pm_required"):
            self.is_pm_required = 1
            if not self.pm_interval_days and cat.get("default_pm_interval_days"):
                self.pm_interval_days = cat["default_pm_interval_days"]
        if not self.is_calibration_required and cat.get("default_calibration_required"):
            self.is_calibration_required = 1
            if not self.calibration_interval_days and cat.get("default_calibration_interval_days"):
                self.calibration_interval_days = cat["default_calibration_interval_days"]

    def _auto_map_risk_classification(self) -> None:
        """BR-00-01: risk_classification auto-derived from medical_device_class + is_radiation_device."""
        if not self.medical_device_class:
            return
        key = (self.medical_device_class, bool(self.is_radiation_device))
        mapped = _CLASS_RISK_MAP.get(key)
        if mapped:
            self.risk_classification = mapped

    def _validate_unique_model_manufacturer(self) -> None:
        """Composite (model_name, manufacturer) must be UNIQUE."""
        if not (self.model_name and self.manufacturer):
            return
        existing = frappe.db.exists(
            "IMM Device Model",
            {
                "model_name": self.model_name,
                "manufacturer": self.manufacturer,
                "name": ["!=", self.name or ""],
            },
        )
        if existing:
            frappe.throw(
                _("Model {0} của nhà sản xuất {1} đã tồn tại ({2})").format(
                    self.model_name, self.manufacturer, existing
                )
            )

    def on_trash(self) -> None:
        """NEG-12 (FK delete-integrity): chặn xóa Model đang được Asset tham chiếu.

        Dùng `on_trash` (chạy TRƯỚC `check_if_doc_is_linked` của Frappe — xem
        `frappe/model/delete_doc.py`) để raise message tiếng Việt thân thiện
        kèm danh sách tài sản phụ thuộc, thay vì message English generic.

        Bypass dùng cho test fixture cleanup / migration: `flags.ignore_link_validation`
        hoặc `flags.in_install` (theo convention Frappe).
        """
        if getattr(self.flags, "ignore_link_validation", False) or frappe.flags.in_install:
            return
        dependents = frappe.get_all(
            "AC Asset",
            filters={"device_model": self.name},
            fields=["name", "asset_name"],
            order_by="creation desc",
            limit=6,
        )
        if not dependents:
            return
        total = frappe.db.count("AC Asset", {"device_model": self.name})
        names = [(d.asset_name or d.name) for d in dependents[:5]]
        suffix = ""
        if total > 5:
            suffix = _(" và {0} tài sản khác").format(total - 5)
        frappe.throw(
            _(
                "Không thể xóa Model thiết bị {0}: đang được {1} tài sản tham chiếu ({2}{3}). "
                "Vui lòng gỡ liên kết hoặc thanh lý các tài sản trước."
            ).format(self.name, total, ", ".join(names), suffix),
            exc=frappe.LinkExistsError,
        )
