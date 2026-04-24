# Copyright (c) 2026, AssetCore Team
# Scan orphan / broken data across IMM-00 inventory + asset domain.
#
# USAGE:
#   bench --site <site> execute assetcore.scripts.scan_orphans.run
#
# Non-destructive: prints a report only. Nothing is written.
from __future__ import annotations

import frappe


def run() -> None:
    sections = [
        ("1. Spare parts thiếu stock_uom",          _scan_parts_missing_stock_uom),
        ("2. Spare parts có stock_uom không tồn tại trong AC UOM", _scan_parts_bad_uom),
        ("3. AC Spare Part Stock tham chiếu spare_part đã xoá",    _scan_stock_orphan_part),
        ("4. AC Spare Part Stock tham chiếu warehouse đã xoá",     _scan_stock_orphan_wh),
        ("5. AC Stock Movement Item có spare_part đã xoá",         _scan_movitem_orphan_part),
        ("6. AC Stock Movement Item thiếu stock_qty hoặc conversion_factor", _scan_movitem_missing_uom_fields),
        ("7. AC Stock Movement reference_name trỏ về AC Purchase không tồn tại", _scan_mov_bad_ref),
        ("8. AC Purchase Item thiếu stock_qty hoặc conversion_factor",  _scan_purchitem_missing_uom_fields),
        ("9. AC Purchase Item có spare_part đã xoá",               _scan_purchitem_orphan_part),
        ("10. AC Asset có department không tồn tại trong AC Department", _scan_asset_bad_dept),
        ("11. AC Asset không có lifecycle event 'Received' (chưa nghiệm thu)", _scan_asset_not_received),
        ("12. Asset Commissioning trỏ về asset đã xoá",            _scan_commissioning_orphan_asset),
        ("13. AC Warehouse có manager (User) không tồn tại",       _scan_wh_bad_manager),
        ("14. UOM names bị trùng chỉ khác hoa/thường trong AC UOM", _scan_duplicate_uom_case),
    ]

    print("=" * 70)
    print("ASSETCORE ORPHAN DATA SCAN")
    print("=" * 70)

    total_issues = 0
    for title, fn in sections:
        rows = fn()
        count = len(rows)
        total_issues += count
        marker = "❌" if count else "✅"
        print(f"\n{marker} {title}: {count} row(s)")
        for r in rows[:20]:
            print(f"    · {r}")
        if count > 20:
            print(f"    ... (+{count - 20} more)")

    print("\n" + "=" * 70)
    print(f"TOTAL ISSUES: {total_issues}")
    print("=" * 70)


# ─── Scanners ────────────────────────────────────────────────────────────────

def _scan_parts_missing_stock_uom() -> list:
    return frappe.db.sql("""
        SELECT name, part_name FROM `tabAC Spare Part`
        WHERE (stock_uom IS NULL OR stock_uom = '') AND is_active = 1
    """, as_dict=True)


def _scan_parts_bad_uom() -> list:
    return frappe.db.sql("""
        SELECT p.name, p.part_name, p.stock_uom, p.purchase_uom
        FROM `tabAC Spare Part` p
        LEFT JOIN `tabAC UOM` u1 ON u1.name = p.stock_uom
        LEFT JOIN `tabAC UOM` u2 ON u2.name = p.purchase_uom
        WHERE (p.stock_uom IS NOT NULL AND p.stock_uom != '' AND u1.name IS NULL)
           OR (p.purchase_uom IS NOT NULL AND p.purchase_uom != '' AND u2.name IS NULL)
    """, as_dict=True)


def _scan_stock_orphan_part() -> list:
    return frappe.db.sql("""
        SELECT s.name, s.spare_part, s.warehouse, s.qty_on_hand
        FROM `tabAC Spare Part Stock` s
        LEFT JOIN `tabAC Spare Part` p ON p.name = s.spare_part
        WHERE p.name IS NULL
    """, as_dict=True)


def _scan_stock_orphan_wh() -> list:
    return frappe.db.sql("""
        SELECT s.name, s.spare_part, s.warehouse, s.qty_on_hand
        FROM `tabAC Spare Part Stock` s
        LEFT JOIN `tabAC Warehouse` w ON w.name = s.warehouse
        WHERE w.name IS NULL
    """, as_dict=True)


def _scan_movitem_orphan_part() -> list:
    return frappe.db.sql("""
        SELECT mi.name, mi.parent AS movement, mi.spare_part, mi.qty
        FROM `tabAC Stock Movement Item` mi
        LEFT JOIN `tabAC Spare Part` p ON p.name = mi.spare_part
        WHERE p.name IS NULL AND mi.spare_part IS NOT NULL AND mi.spare_part != ''
    """, as_dict=True)


def _scan_movitem_missing_uom_fields() -> list:
    return frappe.db.sql("""
        SELECT mi.name, mi.parent AS movement, mi.spare_part, mi.qty,
               mi.conversion_factor, mi.stock_qty, mi.uom
        FROM `tabAC Stock Movement Item` mi
        JOIN `tabAC Stock Movement` m ON m.name = mi.parent
        WHERE m.docstatus = 1
          AND (mi.stock_qty IS NULL OR mi.stock_qty = 0
               OR mi.conversion_factor IS NULL OR mi.conversion_factor = 0)
    """, as_dict=True)


def _scan_mov_bad_ref() -> list:
    return frappe.db.sql("""
        SELECT m.name, m.reference_type, m.reference_name, m.status, m.docstatus
        FROM `tabAC Stock Movement` m
        LEFT JOIN `tabAC Purchase` p ON p.name = m.reference_name
        WHERE m.reference_type = 'AC Purchase'
          AND m.reference_name IS NOT NULL AND m.reference_name != ''
          AND p.name IS NULL
    """, as_dict=True)


def _scan_purchitem_missing_uom_fields() -> list:
    return frappe.db.sql("""
        SELECT pi.name, pi.parent AS purchase, pi.spare_part, pi.qty,
               pi.conversion_factor, pi.stock_qty, pi.uom
        FROM `tabAC Purchase Item` pi
        JOIN `tabAC Purchase` p ON p.name = pi.parent
        WHERE p.docstatus >= 1
          AND (pi.stock_qty IS NULL OR pi.stock_qty = 0
               OR pi.conversion_factor IS NULL OR pi.conversion_factor = 0)
    """, as_dict=True)


def _scan_purchitem_orphan_part() -> list:
    return frappe.db.sql("""
        SELECT pi.name, pi.parent AS purchase, pi.spare_part
        FROM `tabAC Purchase Item` pi
        LEFT JOIN `tabAC Spare Part` sp ON sp.name = pi.spare_part
        WHERE sp.name IS NULL AND pi.spare_part IS NOT NULL AND pi.spare_part != ''
    """, as_dict=True)


def _scan_asset_bad_dept() -> list:
    if not frappe.db.table_exists("tabAC Asset"):
        return []
    if not frappe.db.has_column("AC Asset", "department"):
        return []
    return frappe.db.sql("""
        SELECT a.name, a.asset_name, a.department
        FROM `tabAC Asset` a
        LEFT JOIN `tabAC Department` d ON d.name = a.department
        WHERE a.department IS NOT NULL AND a.department != '' AND d.name IS NULL
    """, as_dict=True)


def _scan_asset_not_received() -> list:
    if not frappe.db.table_exists("tabAsset Lifecycle Event"):
        return []
    return frappe.db.sql("""
        SELECT a.name, a.asset_name, a.status
        FROM `tabAC Asset` a
        WHERE a.status IN ('Active', 'InUse', 'In Use')
          AND NOT EXISTS (
            SELECT 1 FROM `tabAsset Lifecycle Event` e
            WHERE e.asset = a.name AND e.event_type IN ('Received', 'Commissioned', 'Installed')
          )
    """, as_dict=True)


def _scan_commissioning_orphan_asset() -> list:
    if not frappe.db.table_exists("tabAsset Commissioning"):
        return []
    return frappe.db.sql("""
        SELECT c.name, c.asset_ref, c.status
        FROM `tabAsset Commissioning` c
        LEFT JOIN `tabAC Asset` a ON a.name = c.asset_ref
        WHERE c.asset_ref IS NOT NULL AND c.asset_ref != '' AND a.name IS NULL
    """, as_dict=True)


def _scan_wh_bad_manager() -> list:
    return frappe.db.sql("""
        SELECT w.name, w.warehouse_name, w.manager
        FROM `tabAC Warehouse` w
        LEFT JOIN `tabUser` u ON u.name = w.manager
        WHERE w.manager IS NOT NULL AND w.manager != '' AND u.name IS NULL
    """, as_dict=True)


def _scan_duplicate_uom_case() -> list:
    return frappe.db.sql("""
        SELECT LOWER(uom_name) AS key_lower, GROUP_CONCAT(uom_name) AS names, COUNT(*) AS cnt
        FROM `tabAC UOM`
        GROUP BY LOWER(uom_name)
        HAVING cnt > 1
    """, as_dict=True)
