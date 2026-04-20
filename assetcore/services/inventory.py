# Copyright (c) 2026, AssetCore Team
# IMM-00 Inventory Sub-Domain — stock math & movement application
from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import now_datetime

_DT_STOCK = "AC Spare Part Stock"
_DT_PART  = "AC Spare Part"
_DT_WH    = "AC Warehouse"


# ─── Stock querying ──────────────────────────────────────────────────────────

def get_stock_row(warehouse: str, spare_part: str) -> dict | None:
    key = f"{warehouse}::{spare_part}"
    if frappe.db.exists(_DT_STOCK, key):
        return frappe.db.get_value(_DT_STOCK, key,
                                   ["name", "qty_on_hand", "reserved_qty", "available_qty"],
                                   as_dict=True)
    return None


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

def apply_stock_movement(doc) -> None:
    """Apply a submitted AC Stock Movement to AC Spare Part Stock."""
    t = doc.movement_type
    for row in doc.items:
        qty = float(row.qty or 0)
        if t == "Receipt":
            _upsert_stock(doc.to_warehouse, row.spare_part, +qty)
        elif t == "Issue":
            _upsert_stock(doc.from_warehouse, row.spare_part, -qty)
        elif t == "Transfer":
            _upsert_stock(doc.from_warehouse, row.spare_part, -qty)
            _upsert_stock(doc.to_warehouse,   row.spare_part, +qty)
        elif t == "Adjustment":
            # qty may be positive or negative in adjustment
            _upsert_stock(doc.from_warehouse, row.spare_part, qty)


def reverse_stock_movement(doc) -> None:
    """Reverse a previously-applied movement (used on cancel)."""
    t = doc.movement_type
    for row in doc.items:
        qty = float(row.qty or 0)
        if t == "Receipt":
            _upsert_stock(doc.to_warehouse, row.spare_part, -qty)
        elif t == "Issue":
            _upsert_stock(doc.from_warehouse, row.spare_part, +qty)
        elif t == "Transfer":
            _upsert_stock(doc.from_warehouse, row.spare_part, +qty)
            _upsert_stock(doc.to_warehouse,   row.spare_part, -qty)
        elif t == "Adjustment":
            _upsert_stock(doc.from_warehouse, row.spare_part, -qty)


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

def search_parts(query: str, *, limit: int = 10) -> list[dict]:
    if not query or len(query) < 2:
        return []
    rows = frappe.db.sql("""
        SELECT name AS spare_part, part_code, part_name, manufacturer_part_no,
               unit_cost, uom
        FROM `tabAC Spare Part`
        WHERE is_active = 1 AND (
            part_name LIKE %(q)s
            OR part_code LIKE %(q)s
            OR manufacturer_part_no LIKE %(q)s
        )
        ORDER BY part_name ASC
        LIMIT %(lim)s
    """, {"q": f"%{query}%", "lim": int(limit)}, as_dict=True)
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
