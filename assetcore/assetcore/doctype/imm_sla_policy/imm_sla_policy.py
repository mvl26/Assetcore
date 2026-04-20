# Copyright (c) 2026, AssetCore Team
import frappe
from frappe.model.document import Document
from frappe import _

_DOCTYPE = "IMM SLA Policy"


class IMMSLAPolicy(Document):
    def validate(self) -> None:
        self._validate_response_vs_resolution()
        self._validate_validity_dates()
        self._validate_unique_active_policy()

    def _validate_response_vs_resolution(self) -> None:
        """VR-00-19/20: response_time < resolution_time."""
        if self.response_time_minutes and self.resolution_time_hours:
            if self.response_time_minutes >= self.resolution_time_hours * 60:
                frappe.throw(_("Response time phải nhỏ hơn resolution time (BR-00-07)."))

    def _validate_validity_dates(self) -> None:
        if self.effective_date and self.expiry_date and self.expiry_date < self.effective_date:
            frappe.throw(_("expiry_date phải >= effective_date."))

    def _validate_unique_active_policy(self) -> None:
        """BR-00-05: chỉ một SLA Policy active cho mỗi (priority, risk_class)."""
        if not self.is_active or not self.priority:
            return
        filters = {
            "priority": self.priority,
            "is_active": 1,
            "name": ["!=", self.name or ""],
        }
        if self.risk_class:
            filters["risk_class"] = self.risk_class
        existing = frappe.db.exists(_DOCTYPE, filters)
        if existing:
            frappe.throw(
                _("Đã tồn tại SLA Policy active cho priority='{0}', risk_class='{1}' ({2}). "
                  "Tắt policy cũ trước khi tạo mới (BR-00-05).").format(
                    self.priority, self.risk_class or "—", existing
                )
            )
