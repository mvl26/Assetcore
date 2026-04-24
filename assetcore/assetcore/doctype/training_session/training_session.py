# Copyright (c) 2026, AssetCore Team
# Controller for Training Session (IMM-06 child DocType).

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document


class TrainingSession(Document):

    def validate(self) -> None:
        """Validate training session fields."""
        self._validate_training_date()
        self._compute_competency()

    def _validate_training_date(self) -> None:
        """Training date must not be in the future for completed sessions."""
        if self.status == "Completed" and self.training_date:
            from frappe.utils import getdate, today
            if getdate(self.training_date) > getdate(today()):
                frappe.throw(
                    _("Không thể đánh dấu Completed cho buổi đào tạo chưa diễn ra "
                      "(ngày đào tạo: {0}).").format(self.training_date)
                )

    def _compute_competency(self) -> None:
        """Auto-compute competency_confirmed from trainee scores."""
        if not self.trainees:
            self.competency_confirmed = 0
            return
        scored = [t for t in self.trainees if t.attendance == "Present"]
        if not scored:
            self.competency_confirmed = 0
            return
        all_passed = all(t.passed for t in scored)
        self.competency_confirmed = 1 if all_passed else 0
