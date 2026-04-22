# Copyright (c) 2026, AssetCore Team
import frappe
from frappe.model.document import Document
from frappe import _


class AssetLifecycleEvent(Document):
    def validate(self) -> None:
        if not self.is_new():
            frappe.throw(_("Asset Lifecycle Event is immutable (append-only)."))

    def on_trash(self) -> None:
        frappe.throw(_("Asset Lifecycle Event cannot be deleted."))
