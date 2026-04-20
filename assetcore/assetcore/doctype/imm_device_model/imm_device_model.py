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

    def validate(self) -> None:
        """Enforce BR-00-01 class -> risk mapping."""
        self._auto_map_risk_classification()
        self._validate_unique_model_manufacturer()

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
