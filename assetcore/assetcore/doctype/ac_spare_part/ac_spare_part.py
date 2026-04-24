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
        if not self.stock_uom:
            self.stock_uom = "Nos"
        self._validate_uom_conversions()

    def _validate_uom_conversions(self) -> None:
        """Bảng quy đổi không được trùng UOM và không được chứa stock_uom."""
        seen: set[str] = set()
        for row in (self.uom_conversions or []):
            if not row.uom:
                frappe.throw(_(f"Quy đổi UOM dòng {row.idx}: Đơn vị tính không được để trống"))
            if row.uom == self.stock_uom:
                frappe.throw(_(
                    f"Quy đổi UOM dòng {row.idx}: '{row.uom}' trùng với Stock UOM. "
                    "Stock UOM mặc định có hệ số = 1, không khai báo lại."
                ))
            if row.uom in seen:
                frappe.throw(_(f"Quy đổi UOM dòng {row.idx}: '{row.uom}' bị trùng"))
            if not row.conversion_factor or float(row.conversion_factor) <= 0:
                frappe.throw(_(f"Quy đổi UOM dòng {row.idx}: Hệ số quy đổi phải > 0"))
            seen.add(row.uom)

    def on_trash(self):
        # BR-00-13: block delete if any stock or movement references this part
        if frappe.db.exists("AC Spare Part Stock", {"spare_part": self.name}):
            frappe.throw(_("Không thể xoá phụ tùng đã có dữ liệu tồn kho. Vô hiệu hoá thay vì xoá."))
        if frappe.db.exists("AC Stock Movement Item", {"spare_part": self.name}):
            frappe.throw(_("Không thể xoá phụ tùng đã có trong phiếu kho."))
