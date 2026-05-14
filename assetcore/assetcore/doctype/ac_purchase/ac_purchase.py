# Copyright (c) 2026, AssetCore Team
from __future__ import annotations
import frappe
from frappe import _
from frappe.model.document import Document


class ACPurchase(Document):
    def validate(self):
        if not self.items and not self.get("devices"):
            frappe.throw(_("Phải có ít nhất 1 thiết bị hoặc 1 phụ tùng"))
        for row in self.items or []:
            if not row.spare_part:
                frappe.throw(_("Dòng phụ tùng {0}: chưa chọn phụ tùng").format(row.idx))
            if not row.qty or float(row.qty) <= 0:
                frappe.throw(_("Dòng phụ tùng {0}: số lượng phải lớn hơn 0").format(row.idx))
        for row in self.get("devices") or []:
            if not row.device_model:
                frappe.throw(_("Dòng thiết bị {0}: chưa chọn Model").format(row.idx))
            # Enforce 1 row = 1 physical unit
            row.qty = 1

    def before_save(self):
        from assetcore.services import uom as uom_svc
        spare_total = 0.0
        for r in self.items or []:
            qty = float(r.qty or 0)
            uom = (r.uom or "").strip()
            if r.spare_part and uom:
                stock_uom = uom_svc.get_stock_uom(r.spare_part)
                cf = uom_svc.get_conversion_factor(r.spare_part, uom, stock_uom) if uom != stock_uom else 1.0
            else:
                cf = float(r.conversion_factor or 1) or 1.0
            r.conversion_factor = cf
            r.stock_qty = qty * cf
            r.total_cost = qty * float(r.unit_cost or 0)
            spare_total += float(r.total_cost or 0)

        device_total = sum(float(r.unit_cost or 0) for r in (self.get("devices") or []))
        self.total_value = spare_total + device_total

    def on_submit(self):
        self.status = "Submitted"
        self.db_set("status", "Submitted")

    def on_cancel(self):
        self.status = "Cancelled"
        self.db_set("status", "Cancelled")
        self._unlink_references()

    def _unlink_references(self) -> None:
        """Gỡ mọi Link 2 chiều liên quan tới purchase này để cho phép delete trên UI.

        Why: Asset Commissioning.po_reference (reqd=1) trỏ tới AC Purchase, đồng thời
        child AC Purchase Device Item.commissioning_ref trỏ ngược lại Asset Commissioning
        → Frappe block delete cả 2 phía. Khi Cancel, gỡ ràng buộc để admin có thể xóa.
        Dùng db.set_value để bypass `reqd` validate trên Asset Commissioning.
        """
        # Outbound: child rows của chính purchase này
        for row in self.get("devices") or []:
            if row.get("commissioning_ref"):
                row.db_set("commissioning_ref", None, update_modified=False)

        # Inbound: Asset Commissioning trỏ tới purchase này qua po_reference
        linked_comms = frappe.get_all(
            "Asset Commissioning",
            filters={"po_reference": self.name},
            pluck="name",
        )
        for name in linked_comms:
            frappe.db.set_value(
                "Asset Commissioning", name, "po_reference", None,
                update_modified=False,
            )

        if linked_comms:
            frappe.msgprint(
                _("Đã gỡ liên kết PO khỏi {0} phiếu Commissioning: {1}").format(
                    len(linked_comms), ", ".join(linked_comms)
                ),
                alert=True, indicator="orange",
            )
