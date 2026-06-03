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
        self._compute_values()

    def _compute_values(self) -> None:
        """BR-15-16 (04 §III-bis.8): line_value = value_qty × unit_value;
        total_value = Σ line_value. value_qty lifecycle-aware = qty_issued nếu đã
        xuất, ngược lại effective_alloc_qty (qty_approved>0 → qty_approved, else
        qty_requested). MỘT writer duy nhất — service KHÔNG tự set total_value
        (tránh clobber). line_value KHÔNG còn dead column.
        """
        total = 0.0
        for item in self.items:
            unit_value = float(item.unit_value or 0)
            if not unit_value and item.spare_part:
                unit_value = float(
                    frappe.db.get_value("AC Spare Part", item.spare_part, "unit_cost") or 0
                )
                item.unit_value = unit_value
            value_qty = float(item.qty_issued or 0) or (
                float(item.qty_approved or 0) or float(item.qty_requested or 0)
            )
            item.line_value = value_qty * unit_value
            total += item.line_value
        self.total_value = total
