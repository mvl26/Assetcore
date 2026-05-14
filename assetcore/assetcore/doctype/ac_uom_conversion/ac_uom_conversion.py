# Copyright (c) 2026, AssetCore Team
import frappe
from frappe.model.document import Document


class ACUOMConversion(Document):
    def validate(self):
        if self.conversion_factor <= 0:
            frappe.throw(frappe._("Hệ số quy đổi phải lớn hơn 0"))
