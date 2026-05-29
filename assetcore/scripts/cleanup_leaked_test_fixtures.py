# Copyright (c) 2026, AssetCore Team
"""One-off cleanup of leaked test fixtures (2026-05-29 test session).

Prior test runs leaked autonamed records because `_ensure_doc` ignored autoname
(LL-TEST-9) and teardowns swallowed the AC Asset audit guard with `except: pass`.
This purges that residue. Idempotent — safe to re-run.

    bench --site miyano execute assetcore.scripts.cleanup_leaked_test_fixtures.run
"""
from __future__ import annotations

import frappe

from assetcore.tests._asset_cleanup import purge_asset

_ASSET_LIKE = ("%Test Asset IMM%", "\\_Test%")
_PART_LIKE = ("%Test%IMM-15%", "\\_Test%", "Low Stock Part")
_WH_LIKE = ("%Test%IMM-15%", "\\_Test%", "Low WH%")
_CAT_LIKE = ("\\_Test%",)


def _names(table: str, field: str, patterns: tuple[str, ...]) -> list[str]:
    out: list[str] = []
    for p in patterns:
        rows = frappe.db.sql(
            f"SELECT name FROM `tab{table}` WHERE `{field}` LIKE %s ESCAPE '\\\\'",
            (p,),
        )
        out.extend(r[0] for r in rows)
    return sorted(set(out))


def run(dry_run: int = 0) -> None:
    frappe.set_user("Administrator")
    assets = _names("AC Asset", "asset_name", _ASSET_LIKE)
    parts = _names("AC Spare Part", "part_name", _PART_LIKE)
    whs = _names("AC Warehouse", "warehouse_name", _WH_LIKE)
    cats = _names("AC Asset Category", "category_name", _CAT_LIKE)

    print(f"[cleanup] assets={len(assets)} parts={len(parts)} "
          f"warehouses={len(whs)} categories={len(cats)}")
    if dry_run:
        for label, items in (("ASSET", assets), ("PART", parts),
                             ("WAREHOUSE", whs), ("CATEGORY", cats)):
            for n in items:
                print(f"  [{label}] {n}")
        return

    # 1) Assets first — purge_asset cancels incidents/CAPA/RCA + audit trail.
    for name in assets:
        try:
            purge_asset(name)
        except Exception as e:  # noqa: BLE001
            print(f"  [asset-skip] {name}: {e}")

    # 2) Spare parts — drop dependent stock/movements first.
    for part in parts:
        try:
            for sm in frappe.get_all("AC Stock Movement Item",
                                     filters={"spare_part": part}, pluck="parent"):
                doc = frappe.get_doc("AC Stock Movement", sm)
                if doc.docstatus == 1:
                    doc.cancel()
                frappe.delete_doc("AC Stock Movement", sm, force=True,
                                  ignore_permissions=True)
            for st in frappe.get_all("AC Spare Part Stock",
                                     filters={"spare_part": part}, pluck="name"):
                frappe.delete_doc("AC Spare Part Stock", st, force=True,
                                  ignore_permissions=True)
            for al in frappe.get_all("IMM Spare Allocation Item",
                                     filters={"spare_part": part}, pluck="parent"):
                alloc = frappe.get_doc("IMM Spare Allocation", al)
                if alloc.docstatus == 1:
                    alloc.cancel()
                frappe.delete_doc("IMM Spare Allocation", al, force=True,
                                  ignore_permissions=True)
            frappe.delete_doc("AC Spare Part", part, force=True, ignore_permissions=True)
        except Exception as e:  # noqa: BLE001
            print(f"  [part-skip] {part}: {e}")

    # 3) Warehouses + categories last (FK parents now free).
    for wh in whs:
        try:
            frappe.delete_doc("AC Warehouse", wh, force=True, ignore_permissions=True)
        except Exception as e:  # noqa: BLE001
            print(f"  [wh-skip] {wh}: {e}")
    for cat in cats:
        try:
            frappe.delete_doc("AC Asset Category", cat, force=True, ignore_permissions=True)
        except Exception as e:  # noqa: BLE001
            print(f"  [cat-skip] {cat}: {e}")

    frappe.db.commit()
    print("[cleanup] done — re-run with dry_run=1 to verify residue count")
