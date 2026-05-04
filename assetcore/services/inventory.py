# Copyright (c) 2026, AssetCore Team
# IMM-00 Inventory Sub-Domain — stock math & movement application
from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import now_datetime
from assetcore.services.purchase import _DT_PUR

_DT_STOCK   = "AC Spare Part Stock"
_DT_PART    = "AC Spare Part"
_DT_WH      = "AC Warehouse"


# ─── Stock querying ──────────────────────────────────────────────────────────

def get_stock_row(warehouse: str, spare_part: str) -> dict | None:
    key = f"{warehouse}::{spare_part}"
    return frappe.db.get_value(
        _DT_STOCK, key,
        ["name", "qty_on_hand", "reserved_qty", "available_qty"],
        as_dict=True,
    ) or None


def get_available_qty(warehouse: str, spare_part: str) -> float:
    row = get_stock_row(warehouse, spare_part)
    if not row:
        return 0.0
    return float(row.get("available_qty") or 0)


def get_total_stock(spare_part: str) -> float:
    """Tổng tồn của 1 phụ tùng qua tất cả kho."""
    return float(frappe.db.sql("""
        SELECT COALESCE(SUM(qty_on_hand), 0)
        FROM `tabAC Spare Part Stock`
        WHERE spare_part = %s
    """, spare_part)[0][0] or 0)


# ─── Upsert helper ───────────────────────────────────────────────────────────

def _upsert_stock(warehouse: str, spare_part: str, delta: float, *, touch_dt=None) -> None:
    key = f"{warehouse}::{spare_part}"
    touch_dt = touch_dt or now_datetime()

    if frappe.db.exists(_DT_STOCK, key):
        doc = frappe.get_doc(_DT_STOCK, key)
        doc.qty_on_hand = float(doc.qty_on_hand or 0) + float(delta)
        doc.last_movement_date = touch_dt
        doc.save(ignore_permissions=True)
    else:
        doc = frappe.get_doc({
            "doctype": _DT_STOCK,
            "warehouse": warehouse,
            "spare_part": spare_part,
            "qty_on_hand": float(delta),
            "reserved_qty": 0,
            "last_movement_date": touch_dt,
        })
        doc.insert(ignore_permissions=True)


# ─── Stock Movement hooks ────────────────────────────────────────────────────

_REF_DOCTYPE_MAP = {
    "Asset Repair": "Asset Repair",
    "PM Work Order": "PM Work Order",
    _DT_PUR: _DT_PUR,
}


def validate_stock_movement(doc) -> None:
    """Validate business rules before submit (BR-INV-07, BR-INV-08)."""
    ref_type = doc.get("reference_type") or ""
    ref_name = (doc.get("reference_name") or "").strip()

    # BR-INV-08: For linked doc types, verify the referenced document exists
    if ref_type in _REF_DOCTYPE_MAP and ref_name:
        dt = _REF_DOCTYPE_MAP[ref_type]
        if not frappe.db.exists(dt, ref_name):
            frappe.throw(_("Chứng từ {0} '{1}' không tồn tại").format(ref_type, ref_name))

    # BR-INV-07: Manual and Adjustment require notes
    if ref_type == "Manual" or doc.get("movement_type") == "Adjustment":
        if not (doc.get("notes") or "").strip():
            frappe.throw(_("Phiếu Manual / Điều chỉnh bắt buộc phải có Ghi chú (lý do)"))


def apply_stock_movement(doc) -> None:
    """Apply a submitted AC Stock Movement to AC Spare Part Stock.

    Dùng stock_qty (= qty * conversion_factor, đã quy về stock UOM) nếu có.
    Fallback về qty khi conversion_factor = 1 hoặc chưa điền.
    """
    validate_stock_movement(doc)
    t = doc.movement_type
    for row in doc.items:
        stock_qty = float(row.stock_qty or 0) or float(row.qty or 0)
        if t == "Receipt":
            _upsert_stock(doc.to_warehouse, row.spare_part, +stock_qty)
        elif t == "Issue":
            _upsert_stock(doc.from_warehouse, row.spare_part, -stock_qty)
        elif t == "Transfer":
            _upsert_stock(doc.from_warehouse, row.spare_part, -stock_qty)
            _upsert_stock(doc.to_warehouse,   row.spare_part, +stock_qty)
        elif t == "Adjustment":
            _upsert_stock(doc.from_warehouse, row.spare_part, stock_qty)


def reverse_stock_movement(doc) -> None:
    """Reverse a previously-applied movement (cancel)."""
    t = doc.movement_type
    for row in doc.items:
        stock_qty = float(row.stock_qty or 0) or float(row.qty or 0)
        if t == "Receipt":
            _upsert_stock(doc.to_warehouse, row.spare_part, -stock_qty)
        elif t == "Issue":
            _upsert_stock(doc.from_warehouse, row.spare_part, +stock_qty)
        elif t == "Transfer":
            _upsert_stock(doc.from_warehouse, row.spare_part, +stock_qty)
            _upsert_stock(doc.to_warehouse,   row.spare_part, -stock_qty)
        elif t == "Adjustment":
            _upsert_stock(doc.from_warehouse, row.spare_part, -stock_qty)


# ─── Overview / KPIs ─────────────────────────────────────────────────────────

def get_stock_overview() -> dict:
    total_parts     = frappe.db.count(_DT_PART, {"is_active": 1})
    total_warehouses = frappe.db.count(_DT_WH, {"is_active": 1})

    total_value = frappe.db.sql("""
        SELECT COALESCE(SUM(s.qty_on_hand * p.unit_cost), 0)
        FROM `tabAC Spare Part Stock` s
        JOIN `tabAC Spare Part` p ON p.name = s.spare_part
    """)[0][0] or 0

    low_stock = frappe.db.sql("""
        SELECT p.name AS spare_part, p.part_name, p.min_stock_level,
               COALESCE(SUM(s.qty_on_hand), 0) AS total_qty
        FROM `tabAC Spare Part` p
        LEFT JOIN `tabAC Spare Part Stock` s ON s.spare_part = p.name
        WHERE p.is_active = 1 AND p.min_stock_level > 0
        GROUP BY p.name, p.part_name, p.min_stock_level
        HAVING total_qty < p.min_stock_level
        ORDER BY (p.min_stock_level - COALESCE(SUM(s.qty_on_hand), 0)) DESC
        LIMIT 10
    """, as_dict=True)

    movement_30d = frappe.db.sql("""
        SELECT movement_type, COUNT(*) AS cnt
        FROM `tabAC Stock Movement`
        WHERE docstatus = 1 AND movement_date >= DATE_SUB(NOW(), INTERVAL 30 DAY)
        GROUP BY movement_type
    """, as_dict=True)

    return {
        "total_parts":      total_parts,
        "total_warehouses": total_warehouses,
        "total_value":      float(total_value),
        "low_stock_count":  len(low_stock),
        "low_stock_items":  low_stock,
        "movement_30d":     {m["movement_type"]: m["cnt"] for m in movement_30d},
    }


# ─── Search (replacement for imm09.search_spare_parts) ───────────────────────

def search_parts(
    query: str, *, limit: int = 10,
    warehouse: str | None = None, show_stock_only: bool = False,
) -> list[dict]:
    if not query or len(query) < 2:
        return []

    q_param = f"%{query}%"
    name_filter = "(p.part_name LIKE %(q)s OR p.part_code LIKE %(q)s OR p.manufacturer_part_no LIKE %(q)s)"

    if warehouse:
        # Show stock levels for the given warehouse; optionally restrict to parts with stock
        stock_cond = "AND COALESCE(s.available_qty, 0) > 0" if show_stock_only else ""
        rows = frappe.db.sql(f"""
            SELECT p.name, p.name AS spare_part, p.part_code, p.part_name, p.manufacturer_part_no,
                   p.unit_cost, p.stock_uom, p.purchase_uom,
                   COALESCE(s.qty_on_hand, 0)  AS qty_on_hand,
                   COALESCE(s.available_qty, 0) AS available_qty
            FROM `tabAC Spare Part` p
            LEFT JOIN `tabAC Spare Part Stock` s
                   ON s.spare_part = p.name AND s.warehouse = %(wh)s
            WHERE p.is_active = 1 AND {name_filter} {stock_cond}
            ORDER BY p.part_name ASC
            LIMIT %(lim)s
        """, {"q": q_param, "lim": int(limit), "wh": warehouse}, as_dict=True)
    else:
        rows = frappe.db.sql(f"""
            SELECT name, name AS spare_part, part_code, part_name, manufacturer_part_no,
                   unit_cost, stock_uom, purchase_uom,
                   NULL AS qty_on_hand, NULL AS available_qty
            FROM `tabAC Spare Part`
            WHERE is_active = 1 AND {name_filter}
            ORDER BY part_name ASC
            LIMIT %(lim)s
        """, {"q": q_param, "lim": int(limit)}, as_dict=True)

    return rows


# ─── Scheduler: low-stock alert ──────────────────────────────────────────────

def check_low_stock() -> None:
    """Daily scheduler: email IMM Storekeeper about parts below min_stock_level."""
    from assetcore.utils.email import get_role_emails, safe_sendmail
    low = frappe.db.sql("""
        SELECT p.name, p.part_code, p.part_name, p.min_stock_level,
               COALESCE(SUM(s.qty_on_hand), 0) AS total_qty
        FROM `tabAC Spare Part` p
        LEFT JOIN `tabAC Spare Part Stock` s ON s.spare_part = p.name
        WHERE p.is_active = 1 AND p.min_stock_level > 0
        GROUP BY p.name
        HAVING total_qty < p.min_stock_level
    """, as_dict=True)

    if not low:
        return

    emails = get_role_emails(["IMM Storekeeper"])
    if not emails:
        return

    lines = [f"- {r.part_code or r.name} · {r.part_name}: tồn {r.total_qty} / min {r.min_stock_level}" for r in low]
    safe_sendmail(
        recipients=emails,
        subject=_("⚠️ Cảnh báo tồn kho thấp — {0} phụ tùng").format(len(low)),
        message=_("Các phụ tùng sau đang dưới mức tồn tối thiểu:\n\n") + "\n".join(lines),
    )
