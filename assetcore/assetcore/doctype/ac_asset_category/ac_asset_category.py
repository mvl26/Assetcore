# Copyright (c) 2026, AssetCore Team
import frappe
from frappe import _
from frappe.model.document import Document


class ACAssetCategory(Document):
    def validate(self) -> None:
        self._validate_pm_interval()
        self._validate_calibration_interval()

    def _validate_pm_interval(self) -> None:
        """VR-00-16: default_pm_interval_days > 0 khi default_pm_required=1."""
        if not self.default_pm_required:
            return
        if not self.default_pm_interval_days or int(self.default_pm_interval_days) <= 0:
            frappe.throw(_("default_pm_interval_days phải > 0 khi default_pm_required=1 (VR-00-16)."))

    def _validate_calibration_interval(self) -> None:
        if not self.default_calibration_required:
            return
        if not self.default_calibration_interval_days or int(self.default_calibration_interval_days) <= 0:
            frappe.throw(_("default_calibration_interval_days phải > 0 khi default_calibration_required=1."))
