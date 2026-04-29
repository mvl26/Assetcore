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
        """Enforce BR-00-01 class -> risk mapping."""
        self._auto_map_risk_classification()
        self._validate_unique_model_manufacturer()

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
            ],
            as_dict=True,
        )
        if not cat:
            return
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
