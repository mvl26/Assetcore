# Copyright (c) 2026, AssetCore Team
import frappe
from frappe.model.document import Document
from frappe import _


class FirmwareChangeRequest(Document):
    def validate(self) -> None:
        """Enforce business rules on FCR."""
        if self.version_before and self.version_after and self.version_before == self.version_after:
            frappe.throw(_("CM-014: version_after phải khác version_before — không có thay đổi firmware thực sự"))
        if self.status in ("Rollback Required", "Rolled Back") and not self.rollback_reason:
            frappe.throw(_("Lý do rollback là bắt buộc khi trạng thái là Rollback Required"))

    def on_submit(self) -> None:
        """Only allow submission when FCR is approved."""
        if self.status != "Approved":
            frappe.throw(_("Ch\u1ec9 c\u00f3 th\u1ec3 submit FCR khi \u0111\u00e3 \u0111\u01b0\u1ee3c ph\u00ea duy\u1ec7t (Approved)"))
