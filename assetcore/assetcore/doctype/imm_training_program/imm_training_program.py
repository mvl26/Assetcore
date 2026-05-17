# Copyright (c) 2026, AssetCore Team
"""IMM Training Program controller."""
from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document


class IMMTrainingProgram(Document):
    def validate(self) -> None:
        """Validate training program business rules (VR-02, VR-03)."""
        if not self.target_device_model and not self.target_device_category:
            frappe.throw(_("Phải chỉ định ít nhất Device Model hoặc Device Category"))
        score = float(self.passing_score_pct or 0)
        if not (0 <= score <= 100):
            frappe.throw(_("Điểm đạt phải từ 0 đến 100%"))
        if int(self.validity_period_months or 0) < 1:
            frappe.throw(_("Hiệu lực phải ít nhất 1 tháng"))
        from assetcore.services.imm06 import validate_score_bounds_config

        validate_score_bounds_config(self)
