# Copyright (c) 2026, AssetCore Team
import frappe
from frappe import _
from frappe.model.document import Document

from assetcore.services import inventory as inv_svc


class ACStockMovement(Document):
    def validate(self):
        self._validate_warehouses()
        self._validate_items()
        self._compute_total()
        inv_svc.validate_stock_movement(self)

    def _validate_warehouses(self):
        t = self.movement_type
        if t == "Receipt" and not self.to_warehouse:
            frappe.throw(_("Phiếu nhập phải có kho nhập"))
        if t == "Issue" and not self.from_warehouse:
            frappe.throw(_("Phiếu xuất phải có kho xuất"))
        if t == "Transfer":
            if not self.from_warehouse or not self.to_warehouse:
                frappe.throw(_("Phiếu chuyển kho phải có cả kho xuất và kho nhập"))
            if self.from_warehouse == self.to_warehouse:
                frappe.throw(_("Kho nguồn và kho đích phải khác nhau"))
        if t == "Adjustment" and not self.from_warehouse:
            frappe.throw(_("Phiếu điều chỉnh phải chỉ định kho"))

    def _validate_items(self):
        if not self.items:
            frappe.throw(_("Phải có ít nhất 1 dòng phụ tùng"))
        for row in self.items:
            if self.movement_type != "Adjustment" and (row.qty is None or row.qty <= 0):
                frappe.throw(_("Số lượng phải > 0 (dòng {0})").format(row.idx))

    def _compute_total(self):
        self.total_value = sum((r.qty or 0) * (r.unit_cost or 0) for r in (self.items or []))

    def before_submit(self):
        if self.movement_type in ("Issue", "Transfer"):
            # BR-INV-02: a physical movement can only ship goods that physically EXIST.
            # Compare against qty_on_hand, NOT available_qty: the soft-reservation ledger
            # (reserved_qty) is an allocation-layer earmark (IMM-15 §III-bis). The
            # anti-oversell gate that subtracts OTHER allocations' holds is VR-15-03 in
            # services.imm15.issue_allocation; checking available_qty here would
            # double-count an allocation's own reservation and block its legitimate issue.
            for row in self.items:
                bin_row = inv_svc.get_stock_row(self.from_warehouse, row.spare_part)
                on_hand = float((bin_row or {}).get("qty_on_hand") or 0)
                if on_hand < (row.qty or 0):
                    frappe.throw(_(
                        "Tồn kho không đủ cho {0} tại {1}: có {2}, cần {3}"
                    ).format(row.part_name or row.spare_part, self.from_warehouse, on_hand, row.qty))
        self.status = "Submitted"

    def on_submit(self):
        inv_svc.apply_stock_movement(self)

    def on_cancel(self):
        inv_svc.reverse_stock_movement(self)
        self.status = "Cancelled"
