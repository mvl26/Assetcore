# Copyright (c) 2026, AssetCore Team
import frappe
from frappe.model.document import Document
from frappe.utils import getdate, today


class IMMSpareBatch(Document):
    def validate(self) -> None:
        """Check expiry and set is_expired flag."""
        # Normalize both sides to ``datetime.date`` — direct Python callers may
        # pass a ``date`` object while form submissions yield ``str``.
        if self.expiry_date and getdate(self.expiry_date) < getdate(today()):
            self.is_expired = 1
        else:
            self.is_expired = 0
