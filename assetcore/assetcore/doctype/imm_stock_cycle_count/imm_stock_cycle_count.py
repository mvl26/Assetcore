# Copyright (c) 2026, AssetCore Team
"""IMM Stock Cycle Count controller."""
from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document


class IMMStockCycleCount(Document):
    def validate(self) -> None:
        """Validate: verified_by != counted_by (VR-15-11)."""
        if self.verified_by and self.verified_by == self.counted_by:
            frappe.throw(_("Người xác nhận phải khác người kiểm kê"))
