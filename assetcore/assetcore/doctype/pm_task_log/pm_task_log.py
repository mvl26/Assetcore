# Copyright (c) 2026, AssetCore Team
import frappe
from frappe.model.document import Document


class PMTaskLog(Document):
    def validate(self) -> None:
        # Immutable audit trail — db_set must never be called on this DocType either
        if not self.is_new():
            frappe.throw("PM Task Log không thể sửa sau khi đã tạo (immutable audit trail).")
