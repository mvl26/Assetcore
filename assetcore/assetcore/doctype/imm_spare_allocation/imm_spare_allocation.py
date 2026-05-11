# Copyright (c) 2026, AssetCore Team
"""IMM Spare Allocation controller."""
from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document


class IMMSpareAllocation(Document):
    def validate(self) -> None:
        """Validate allocation before save."""
        if not self.items:
            frappe.throw(_("Phiếu cấp phát phải có ít nhất 1 dòng phụ tùng"))
        if not self.warehouse_from:
            frappe.throw(_("Phải chọn kho xuất"))
        if self.urgency not in ("Routine", "Urgent", "Emergency"):
            frappe.throw(_("Mức độ khẩn cấp không hợp lệ"))
        # VR-15-13: warehouse active
        wh_active = frappe.db.get_value("AC Warehouse", self.warehouse_from, "is_active")
        if wh_active == 0:
            frappe.throw(_(f"Kho {self.warehouse_from} không còn hoạt động"))
        # Compute total_value
        self.total_value = sum(
            float(item.qty_requested or 0) * float(item.unit_value or 0)
            for item in self.items
        )
