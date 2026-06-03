# Copyright (c) 2026, AssetCore Team
"""IMM User Competency controller."""
from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import date_diff, nowdate


class IMMUserCompetency(Document):
    def validate(self) -> None:
        """Validate: expiry after achieved; compute days_until_expiry."""
        if self.achieved_date and self.expiry_date:
            if self.expiry_date < self.achieved_date:
                frappe.throw(_("Ngày hết hạn phải sau ngày đạt năng lực"))
        self._set_computed_fields()

    def before_save(self) -> None:
        """Compute expiry_date + recertification_due_date if Active and not yet set.

        Gọi SoT `compute_competency_dates` (services/imm06.py §V.1, BR-06-13) —
        INVARIANT recert = expiry − 60 ngày. KHÔNG inline formula (lazy-import tránh
        circular import controller ↔ service). Idempotent: chỉ set khi expiry còn trống."""
        if self.workflow_state == "Active" and self.achieved_date and not self.expiry_date:
            from assetcore.services.imm06 import compute_competency_dates
            dates = compute_competency_dates(self.achieved_date, int(self.validity_months or 24))
            self.expiry_date = dates["expiry_date"]
            self.recertification_due_date = dates["recertification_due_date"]

    def on_update(self) -> None:
        """Archive old competencies and invalidate cache on state change."""
        if self.has_value_changed("workflow_state"):
            if self.workflow_state == "Active":
                try:
                    from assetcore.services.imm06 import archive_old_competency
                    archive_old_competency(self.user, self.device_model, exclude=self.name)
                except Exception:
                    pass
            try:
                from assetcore.services.imm06 import _invalidate_auth_cache
                _invalidate_auth_cache(self.user, self.device_model)
            except Exception:
                pass

    def on_trash(self) -> None:
        frappe.throw(_("BR-06-09: Không được phép xóa Competency. Vui lòng dùng Suspend hoặc Revoke."))

    def _set_computed_fields(self) -> None:
        if self.expiry_date:
            delta = date_diff(self.expiry_date, nowdate())
            self.days_until_expiry = int(delta)
            self.is_expired = 1 if delta < 0 else 0
