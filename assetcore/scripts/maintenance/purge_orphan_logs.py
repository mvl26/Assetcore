# Copyright (c) 2026, AssetCore Team
"""Purge orphan operational logs/schedules left dangling after test assets were
deleted (cleanup 2026-06-03, expanded DB-wide sweep round 2).

These are leaf operational records whose ``asset`` / ``asset_ref`` /
``pm_work_order`` / ``training_program`` / ``checklist_template`` FK now points to
a DELETED record (all of which were test garbage). They are themselves test
cascade-orphans → safe to hard-delete.

CONSERVATIVE: only purges the unambiguous test-log doctypes below. It does NOT
touch AC Purchase / AC Warehouse / Procurement Plan Line orphans (those may be
seed-ish data) — those are reported for user confirmation instead.

    bench --site miyano execute assetcore.scripts.maintenance.purge_orphan_logs.run --kwargs "{'dry_run': 1}"
    bench --site miyano execute assetcore.scripts.maintenance.purge_orphan_logs.run
"""
from __future__ import annotations

import frappe

# (doctype, fk-field, parent-doctype) — orphan ⟺ fk points to a now-gone parent.
_ORPHAN_LOGS: list[tuple[str, str, str]] = [
    ("AC Asset Downtime Log", "asset", "AC Asset"),
    ("PM Task Log", "asset_ref", "AC Asset"),
    ("PM Task Log", "pm_work_order", "PM Work Order"),
    ("IMM Calibration Schedule", "asset", "AC Asset"),
    ("PM Schedule", "asset_ref", "AC Asset"),
    ("PM Schedule", "checklist_template", "PM Checklist Template"),
    ("PM Work Order", "pm_schedule", "PM Schedule"),
    ("IMM Training Session", "training_program", "IMM Training Program"),
    ("PM Checklist Template", "asset_category", "AC Asset Category"),
]

# Reported but NOT auto-purged — need user confirmation (may be seed data).
_AMBIGUOUS: list[tuple[str, str, str]] = [
    ("AC Purchase", "supplier", "AC Supplier"),
    ("AC Purchase Device Item", "device_model", "IMM Device Model"),
    ("AC Warehouse", "location", "AC Location"),
    ("AC Warehouse", "department", "AC Department"),
    ("Procurement Plan Line", "needs_request", "IMM Needs Request"),
]


def _orphans(dt: str, fld: str, parent: str) -> list[tuple[str, int]]:
    if not (frappe.db.table_exists(dt) and frappe.db.has_column(dt, fld)
            and frappe.db.table_exists(parent)):
        return []
    return frappe.db.sql(
        f"SELECT t.name, t.docstatus FROM `tab{dt}` t "
        f"LEFT JOIN `tab{parent}` p ON p.name = t.`{fld}` "
        f"WHERE t.`{fld}` IS NOT NULL AND t.`{fld}` != '' AND p.name IS NULL"
    )


def run(dry_run: int = 0) -> None:
    frappe.set_user("Administrator")

    print("=== ORPHAN LOGS to purge (FK → deleted test record) ===")
    plan: list[tuple[str, str, list[tuple[str, int]]]] = []
    for dt, fld, parent in _ORPHAN_LOGS:
        rows = _orphans(dt, fld, parent)
        if rows:
            plan.append((dt, fld, rows))
            print(f"   {dt}.{fld}: {len(rows)} orphan")

    print("\n=== AMBIGUOUS orphans (NOT purged — need user confirmation) ===")
    for dt, fld, parent in _AMBIGUOUS:
        rows = _orphans(dt, fld, parent)
        if rows:
            print(f"   {dt}.{fld} -> {parent}: {len(rows)} dangling")

    if dry_run:
        print("\n[DRY-RUN] nothing deleted.")
        return

    total = 0
    # Child tables (AC Purchase Device Item etc.) aren't in the purge list; the
    # log doctypes here are all top-level. Cancel submitted before delete.
    for dt, _fld, rows in plan:
        n = 0
        for name, ds in rows:
            if not frappe.db.exists(dt, name):
                continue
            try:
                if ds == 1:
                    doc = frappe.get_doc(dt, name)
                    doc.cancel()
                frappe.delete_doc(dt, name, force=True, ignore_permissions=True,
                                  delete_permanently=True)
                n += 1
            except Exception as e:  # noqa: BLE001
                print(f"  [{dt}-skip] {name}: {e}")
        frappe.db.commit()
        total += n
        print(f"   deleted {dt}: {n}")
    print(f"\n[done] purged {total} orphan log records.")
