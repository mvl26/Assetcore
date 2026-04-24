# Copyright (c) 2026, AssetCore Team
# IMM-00 Purchase service — business logic for AC Purchase lifecycle
from __future__ import annotations

import frappe
from frappe import _

_DT_PUR = "AC Purchase"
_DT_MOV = "AC Stock Movement"


def create_receipt_movement(purchase_name: str, to_warehouse: str,
                            requested_by: str = "", auto_submit: bool = False) -> object:
    """Create an AC Stock Movement (Receipt) from an approved AC Purchase.

    Copies all items from the purchase into the movement so the storekeeper
    only needs to confirm the receiving warehouse.
    """
    purchase = frappe.get_doc(_DT_PUR, purchase_name)

    if purchase.docstatus != 1:
        frappe.throw(_("Chỉ tạo phiếu nhập kho từ đơn hàng đã duyệt"))
    if purchase.status == "Cancelled":
        frappe.throw(_("Đơn hàng đã bị huỷ"))
    if not to_warehouse:
        frappe.throw(_("Phải chọn kho nhập hàng"))
    if not frappe.db.exists("AC Warehouse", to_warehouse):
        frappe.throw(_("Kho nhập không tồn tại"))

    spare_rows = [r for r in (purchase.items or []) if r.spare_part]
    if not spare_rows:
        frappe.throw(_(
            "Đơn hàng này không có phụ tùng. Thiết bị y tế phải qua phiếu tiếp nhận (commissioning)."
        ))

    movement = frappe.get_doc({
        "doctype": _DT_MOV,
        "movement_type": "Receipt",
        "movement_date": frappe.utils.now_datetime(),
        "to_warehouse": to_warehouse,
        "supplier": purchase.supplier,
        "reference_type": _DT_PUR,
        "reference_name": purchase.name,
        "requested_by": requested_by or frappe.session.user,
        "items": [
            {
                "spare_part": r.spare_part,
                "qty": float(r.qty or 0),
                "uom": r.uom or None,
                "conversion_factor": float(r.conversion_factor or 1),
                "stock_qty": float(r.stock_qty or 0) or float(r.qty or 0),
                "unit_cost": float(r.unit_cost or 0),
            }
            for r in spare_rows
        ],
    })
    movement.insert(ignore_permissions=True)

    if auto_submit:
        movement.submit()

    return movement


def auto_mark_purchase_received(movement_doc) -> None:
    """Hook called after a Receipt Stock Movement is submitted."""
    if movement_doc.movement_type != "Receipt" or movement_doc.reference_type != _DT_PUR:
        return
    ref = movement_doc.reference_name
    if not ref:
        return
    vals = frappe.db.get_value(_DT_PUR, ref, ["docstatus", "status"], as_dict=True)
    if vals and vals.docstatus == 1 and vals.status == "Submitted":
        frappe.db.set_value(_DT_PUR, ref, "status", "Received")


def auto_unmark_purchase_received(movement_doc) -> None:
    """Hook called when a Receipt Stock Movement is cancelled."""
    if movement_doc.movement_type != "Receipt" or movement_doc.reference_type != _DT_PUR:
        return
    ref = movement_doc.reference_name
    if not ref:
        return
    vals = frappe.db.get_value(_DT_PUR, ref, ["docstatus", "status"], as_dict=True)
    if vals and vals.docstatus == 1 and vals.status == "Received":
        frappe.db.set_value(_DT_PUR, ref, "status", "Submitted")


def get_purchase_movements(purchase_name: str) -> list[dict]:
    """Return all stock movements linked to a given AC Purchase."""
    rows = frappe.db.get_all(
        _DT_MOV,
        filters={"reference_type": _DT_PUR, "reference_name": purchase_name},
        fields=["name", "movement_type", "movement_date", "to_warehouse",
                "from_warehouse", "status", "total_value", "docstatus"],
        order_by="movement_date DESC",
    )
    # enrich warehouse codes
    wh_ids = {r.to_warehouse for r in rows if r.to_warehouse} | \
             {r.from_warehouse for r in rows if r.from_warehouse}
    wh_map = {}
    if wh_ids:
        for w in frappe.get_all("AC Warehouse",
                                filters={"name": ["in", list(wh_ids)]},
                                fields=["name", "warehouse_code", "warehouse_name"]):
            wh_map[w.name] = w
    for r in rows:
        if r.to_warehouse and r.to_warehouse in wh_map:
            r["to_warehouse_code"] = wh_map[r.to_warehouse].warehouse_code
        if r.from_warehouse and r.from_warehouse in wh_map:
            r["from_warehouse_code"] = wh_map[r.from_warehouse].warehouse_code
    return rows
