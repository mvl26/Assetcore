# Copyright (c) 2026, AssetCore Team
"""IMM Training Session controller."""
from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document


class IMMTrainingSession(Document):
    def validate(self) -> None:
        """Validate: instructor required (VR-04)."""
        if (
            not self.instructor
            and not self.instructor_external_name
            and not self.get("trainer_ref")
        ):
            frappe.throw(_("Phải có ít nhất giảng viên nội bộ, hồ sơ giảng viên hoặc giảng viên bên ngoài"))
        from assetcore.services.imm06 import validate_participant_scores

        validate_participant_scores(self)
