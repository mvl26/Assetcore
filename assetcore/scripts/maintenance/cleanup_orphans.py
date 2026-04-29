# Copyright (c) 2026, AssetCore Team
# Cleanup garbage / orphan data. Each fix is a standalone function with a
# `dry_run` parameter (default True). Run `bench execute ...cleanup_orphans.run`
# with dry_run=False to actually write.
#
# USAGE:
#   bench --site <site> execute assetcore.scripts.maintenance.cleanup_orphans.run
#   bench --site <site> execute assetcore.scripts.maintenance.cleanup_orphans.run --kwargs "{'dry_run':0}"
from __future__ import annotations

import frappe


def run(dry_run: int = 1) -> None:
    dry = bool(int(dry_run))
    mode = "DRY-RUN" if dry else "EXECUTE"
    print(f"\n{'=' * 70}\nCLEANUP ORPHANS — {mode}\n{'=' * 70}")

    tasks = [
        ("Backfill stock_qty cho Stock Movement Item đã submit",  fix_movitem_missing_stock_qty),
        ("Backfill stock_qty cho Purchase Item đã submit",        fix_purchitem_missing_stock_qty),
        ("Xoá AC Spare Part Stock mồ côi (spare_part đã xoá)",    fix_delete_orphan_stock_part),
        ("Xoá AC Spare Part Stock mồ côi (warehouse đã xoá)",     fix_delete_orphan_stock_wh),
        ("Clear reference_name sai ở AC Stock Movement",          fix_clear_bad_mov_ref),
        ("Set stock_uom=Cái cho spare part thiếu",                fix_parts_missing_stock_uom),
        ("Clear manager không tồn tại trên AC Warehouse",         fix_clear_bad_wh_manager),
    ]

    for title, fn in tasks:
        print(f"\n→ {title}")
        n = fn(dry)
        marker = "✓ skipped" if n == 0 else ("⟳ would fix" if dry else "✔ fixed")
        print(f"  {marker}: {n} row(s)")

    if not dry:
        frappe.db.commit()
        print("\n✔ Changes committed")
    else:
        print("\n(dry-run — no writes)")


# ─── Fixes ────────────────────────────────────────────────────────────────────

def fix_movitem_missing_stock_qty(dry: bool) -> int:
    rows = frappe.db.sql("""
        SELECT mi.name, mi.spare_part, mi.qty, mi.uom
        FROM `tabAC Stock Movement Item` mi
        JOIN `tabAC Stock Movement` m ON m.name = mi.parent
        WHERE m.docstatus = 1
          AND (mi.stock_qty IS NULL OR mi.stock_qty = 0)
          AND mi.qty > 0
    """, as_dict=True)
    if not rows:
        return 0
    for r in rows:
        cf = _compute_cf(r["spare_part"], r["uom"])
        stock_qty = float(r["qty"]) * cf
        if not dry:
            frappe.db.set_value("AC Stock Movement Item", r["name"],
                                {"conversion_factor": cf, "stock_qty": stock_qty},
                                update_modified=False)
    return len(rows)


def fix_purchitem_missing_stock_qty(dry: bool) -> int:
    rows = frappe.db.sql("""
        SELECT pi.name, pi.spare_part, pi.qty, pi.uom
        FROM `tabAC Purchase Item` pi
        JOIN `tabAC Purchase` p ON p.name = pi.parent
        WHERE p.docstatus >= 1
          AND (pi.stock_qty IS NULL OR pi.stock_qty = 0)
          AND pi.qty > 0
    """, as_dict=True)
    if not rows:
        return 0
    for r in rows:
        cf = _compute_cf(r["spare_part"], r["uom"])
        stock_qty = float(r["qty"]) * cf
        if not dry:
            frappe.db.set_value("AC Purchase Item", r["name"],
                                {"conversion_factor": cf, "stock_qty": stock_qty},
                                update_modified=False)
    return len(rows)


def fix_delete_orphan_stock_part(dry: bool) -> int:
    rows = frappe.db.sql("""
        SELECT s.name
        FROM `tabAC Spare Part Stock` s
        LEFT JOIN `tabAC Spare Part` p ON p.name = s.spare_part
        WHERE p.name IS NULL
    """, as_dict=True)
    if not rows:
        return 0
    if not dry:
        for r in rows:
            frappe.db.sql("DELETE FROM `tabAC Spare Part Stock` WHERE name = %s", r["name"])
    return len(rows)


def fix_delete_orphan_stock_wh(dry: bool) -> int:
    rows = frappe.db.sql("""
        SELECT s.name
        FROM `tabAC Spare Part Stock` s
        LEFT JOIN `tabAC Warehouse` w ON w.name = s.warehouse
        WHERE w.name IS NULL
    """, as_dict=True)
    if not rows:
        return 0
    if not dry:
        for r in rows:
            frappe.db.sql("DELETE FROM `tabAC Spare Part Stock` WHERE name = %s", r["name"])
    return len(rows)


def fix_clear_bad_mov_ref(dry: bool) -> int:
    rows = frappe.db.sql("""
        SELECT m.name
        FROM `tabAC Stock Movement` m
        LEFT JOIN `tabAC Purchase` p ON p.name = m.reference_name
        WHERE m.reference_type = 'AC Purchase'
          AND m.reference_name IS NOT NULL AND m.reference_name != ''
          AND p.name IS NULL
    """, as_dict=True)
    if not rows:
        return 0
    if not dry:
        for r in rows:
            frappe.db.set_value("AC Stock Movement", r["name"],
                                {"reference_name": None, "reference_type": None},
                                update_modified=False)
    return len(rows)


def fix_parts_missing_stock_uom(dry: bool) -> int:
    rows = frappe.db.sql("""
        SELECT name FROM `tabAC Spare Part`
        WHERE (stock_uom IS NULL OR stock_uom = '')
    """, as_dict=True)
    if not rows:
        return 0
    if not dry:
        for r in rows:
            frappe.db.set_value("AC Spare Part", r["name"], "stock_uom", "Cái",
                                update_modified=False)
    return len(rows)


def fix_clear_bad_wh_manager(dry: bool) -> int:
    rows = frappe.db.sql("""
        SELECT w.name
        FROM `tabAC Warehouse` w
        LEFT JOIN `tabUser` u ON u.name = w.manager
        WHERE w.manager IS NOT NULL AND w.manager != '' AND u.name IS NULL
    """, as_dict=True)
    if not rows:
        return 0
    if not dry:
        for r in rows:
            frappe.db.set_value("AC Warehouse", r["name"], "manager", None,
                                update_modified=False)
    return len(rows)


# ─── Helpers ────────────────────────────────────────────────────────────────

def _compute_cf(spare_part: str, from_uom: str) -> float:
    """Tính conversion_factor = 1 [from_uom] → stock_uom. Trả 1.0 nếu không xác định được."""
    if not spare_part or not from_uom:
        return 1.0
    try:
        from assetcore.services import uom as uom_svc
        stock_uom = uom_svc.get_stock_uom(spare_part)
        if from_uom == stock_uom:
            return 1.0
        return uom_svc.get_conversion_factor(spare_part, from_uom, stock_uom)
    except Exception:
        return 1.0
