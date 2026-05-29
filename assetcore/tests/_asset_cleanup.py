# Copyright (c) 2026, AssetCore Team
"""Shared test fixture cleanup helpers (LL-TEST-17).

``AC Asset.on_trash`` (WR-03) blocks hard-delete while audit / lifecycle /
operational records exist, and ``force=True`` does NOT bypass a custom
``on_trash``. ``IMM Audit Trail`` and ``Asset Lifecycle Event`` additionally
throw in their own ``on_trash`` (ISO 13485:7.5.9 / append-only), so they must
be purged via raw SQL. Operational dependents have no guard → ORM delete.

Import from any ``test_immXX`` module instead of re-implementing teardown:

    from assetcore.tests._asset_cleanup import purge_asset
"""
from __future__ import annotations

import frappe

# (doctype, asset-link fieldname) — operational dependents with no on_trash guard.
# Field names verified against DocType JSON; non-existent doctypes/columns are
# skipped at runtime so this list is safe across module subsets.
_ASSET_DEPENDENTS: list[tuple[str, str]] = [
    ("PM Work Order", "asset_ref"),
    ("Asset Repair", "asset_ref"),
    ("PM Schedule", "asset_ref"),
    ("IMM Calibration Schedule", "asset"),
    ("IMM Asset Calibration", "asset"),
    ("IMM CAPA Record", "asset"),
    ("IMM RCA Record", "asset"),
    ("IMM Compliance Finding", "asset"),
    ("Incident Report", "asset"),
    ("Asset Transfer", "asset"),
    ("AC Asset Downtime Log", "asset"),
]


def purge_asset(asset_name: str) -> None:
    """Force-delete an AC Asset and all its dependents for fixture cleanup."""
    if not frappe.db.exists("AC Asset", asset_name):
        return
    # 1) Append-only records — raw SQL (ORM delete always throws, even force=True)
    frappe.db.sql(
        "DELETE FROM `tabIMM Audit Trail` "
        "WHERE asset=%s OR (ref_doctype='AC Asset' AND ref_name=%s)",
        (asset_name, asset_name),
    )
    frappe.db.sql("DELETE FROM `tabAsset Lifecycle Event` WHERE asset=%s", (asset_name,))
    # Asset Document.on_trash unconditionally throws (append-only) → raw SQL too.
    frappe.db.sql("DELETE FROM `tabAsset Document` WHERE asset_ref=%s", (asset_name,))
    # 2) Operational dependents — ORM (cancel submitted docs first)
    for dt, fld in _ASSET_DEPENDENTS:
        if not frappe.db.table_exists(dt) or not frappe.db.has_column(dt, fld):
            continue
        for child in frappe.get_all(dt, filters={fld: asset_name}, pluck="name"):
            doc = frappe.get_doc(dt, child)
            if doc.docstatus == 1:
                doc.cancel()
            frappe.delete_doc(dt, child, force=True, ignore_permissions=True,
                              delete_permanently=True)
    frappe.db.commit()
    # 3) Asset now deletes cleanly
    frappe.delete_doc("AC Asset", asset_name, force=True, ignore_permissions=True)
