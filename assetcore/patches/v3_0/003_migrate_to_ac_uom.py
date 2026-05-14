# Copyright (c) 2026, AssetCore Team
# Migration: seed AC UOM master + re-link all AssetCore doctypes that were
# previously linking to the ERPNext core "UOM" doctype.
#
# Execution order (idempotent):
#   1. Seed AC UOM records (Vietnamese medical UOMs)
#   2. Copy over any existing UOM names already used in AC Spare Part /
#      AC Stock Movement Item / AC Purchase Item so migration doesn't break
#      existing data.
from __future__ import annotations

import frappe

_DT_UOM = "AC UOM"
_SOURCE_TABLES = [
    ("AC Spare Part",          ["stock_uom", "purchase_uom"]),
    ("AC Spare Part Stock",    ["uom"]),
    ("AC Stock Movement Item", ["uom"]),
    ("AC Purchase Item",       ["uom"]),
    ("AC UOM Conversion",      ["uom"]),
    ("IMM Device Spare Part",  ["uom"]),
    ("Spare Parts Used",       ["uom"]),
    ("AC Asset",               ["uom"]),
]


def execute() -> None:
    _seed_ac_uoms()
    _ingest_existing_uom_values()


def _seed_ac_uoms() -> None:
    from assetcore.services.uom import seed_ac_uoms
    created = seed_ac_uoms()
    if created:
        print(f"[003_migrate_to_ac_uom] Seeded {len(created)} AC UOM: {created}")


def _collect_existing_uoms() -> set[str]:
    seen: set[str] = set()
    for dt, columns in _SOURCE_TABLES:
        if not frappe.db.table_exists(dt):
            continue
        for col in columns:
            if not frappe.db.has_column(dt, col):
                continue
            rows = frappe.db.sql(
                f"SELECT DISTINCT `{col}` FROM `tab{dt}` WHERE `{col}` IS NOT NULL AND `{col}` != ''"
            )
            seen.update(val.strip() for (val,) in rows if val)
    return seen


def _ingest_existing_uom_values() -> None:
    """Collect all distinct UOM names referenced by AssetCore tables and
    ensure each exists as an AC UOM record."""
    created = 0
    for uom_name in _collect_existing_uoms():
        if not frappe.db.exists(_DT_UOM, uom_name):
            frappe.get_doc({
                "doctype": _DT_UOM,
                "uom_name": uom_name,
                "symbol": uom_name,
                "is_active": 1,
            }).insert(ignore_permissions=True)
            created += 1
    if created:
        print(f"[003_migrate_to_ac_uom] Back-filled {created} AC UOM from existing data")
    frappe.db.commit()
