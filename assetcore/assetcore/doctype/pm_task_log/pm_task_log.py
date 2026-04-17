# Copyright (c) 2026, AssetCore Team
import frappe
from frappe.model.document import Document


class PMTaskLog(Document):
    def before_insert(self) -> None:
        """Audit trail record — no business logic on create."""
        pass

    def validate(self) -> None:
        """Block modifications after creation to preserve immutable audit trail."""
        if not self.is_new():
            frappe.throw("PM Task Log kh\u00f4ng th\u1ec3 s\u1eeda sau khi \u0111\u00e3 t\u1ea1o (immutable audit trail).")
