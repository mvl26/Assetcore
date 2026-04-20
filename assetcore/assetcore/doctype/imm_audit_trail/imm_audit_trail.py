# Copyright (c) 2026, AssetCore Team
import frappe
from frappe.model.document import Document
from frappe import _


class IMMAuditTrail(Document):
    def validate(self) -> None:
        if not self.is_new():
            frappe.throw(_("Audit Trail records are immutable. No update allowed."))

    def on_trash(self) -> None:
        frappe.throw(_("Audit Trail records cannot be deleted (ISO 13485:7.5.9)."))
