# Copyright (c) 2026, AssetCore Team
import frappe
from frappe.model.document import Document
from frappe.utils import today


class IMMSpareBatch(Document):
    def validate(self) -> None:
        """Check expiry and set is_expired flag."""
        if self.expiry_date and self.expiry_date < today():
            self.is_expired = 1
        else:
            self.is_expired = 0
