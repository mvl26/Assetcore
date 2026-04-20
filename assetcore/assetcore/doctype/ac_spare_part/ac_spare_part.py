# Copyright (c) 2026, AssetCore Team
import frappe
from frappe import _
from frappe.model.document import Document


class ACSparePart(Document):
    def validate(self):
        if self.min_stock_level and self.max_stock_level and self.max_stock_level < self.min_stock_level:
            frappe.throw(_("Tồn tối đa phải >= tồn tối thiểu"))
        if not self.part_code:
            self.part_code = self.name

    def on_trash(self):
        # BR-00-13: block delete if any stock or movement references this part
        if frappe.db.exists("AC Spare Part Stock", {"spare_part": self.name}):
            frappe.throw(_("Không thể xoá phụ tùng đã có dữ liệu tồn kho. Vô hiệu hoá thay vì xoá."))
        if frappe.db.exists("AC Stock Movement Item", {"spare_part": self.name}):
            frappe.throw(_("Không thể xoá phụ tùng đã có trong phiếu kho."))
