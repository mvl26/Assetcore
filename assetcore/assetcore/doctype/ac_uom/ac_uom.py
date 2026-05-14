# Copyright (c) 2026, AssetCore Team
from __future__ import annotations
import frappe
from frappe import _
from frappe.model.document import Document


class ACUOM(Document):
    def validate(self):
        self.uom_name = (self.uom_name or "").strip()
        if not self.uom_name:
            frappe.throw(_("Tên đơn vị tính không được để trống"))

    def on_trash(self):
        for dt in ("AC Spare Part", "AC Spare Part Stock", "AC Stock Movement Item",
                   "AC Purchase Item", "AC UOM Conversion"):
            if frappe.db.exists(dt, {"uom": self.name}):
                frappe.throw(
                    _("Không thể xoá đơn vị '{0}' vì đang được sử dụng trong {1}").format(
                        self.name, dt
                    )
                )
