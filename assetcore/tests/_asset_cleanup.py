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
    ("Asset Decommission", "asset"),
    ("AC Asset Downtime Log", "asset"),
]


def decommission_via_closure(
    asset_name: str,
    *,
    actor: str = "Administrator",
    disposal_method: str = "Huỷ",
    reason: str = "Thiết bị hết niên hạn sử dụng theo quy định BYT; đã lập biên bản thanh lý.",
    sanitized: bool = True,
) -> str:
    """Decommission an asset through the IMM-14 closure flow (gate-compliant).

    Sau khi IMM-14 wire GATE (BR-14-W2-01), KHÔNG asset nào vào Decommissioned mà
    không có 'Asset Decommission' docstatus=1. Test fixtures cần asset
    Decommissioned (để verify side-effect: PM suspend, depreciation cancel, audit)
    phải đi qua closure flow này thay vì gọi transition_asset_status trực tiếp.

    Idempotent: asset đã Decommissioned → no-op, trả "".
    Returns: tên Asset Decommission record (hoặc "" nếu đã terminal).
    """
    from assetcore.services import imm14
    from assetcore.services.shared import AssetStatus

    if frappe.db.get_value("AC Asset", asset_name, "lifecycle_status") == \
            AssetStatus.DECOMMISSIONED:
        return ""
    rec = imm14.create_decommission(
        asset=asset_name, disposal_method=disposal_method,
        decommission_reason=reason, patient_data_sanitized=sanitized,
        responsible=actor,
    )["name"]
    imm14.approve_decommission(rec)
    frappe.db.commit()
    return rec


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


def purge_assets_by_name_prefix(*prefixes: str) -> int:
    """Module-teardown safety net: purge every AC Asset whose asset_name starts
    with any of ``prefixes`` (all FK-safe via ``purge_asset``).

    Use in a ``tearDownModule`` so a leak survives no single class's teardown gap.
    Returns the number of assets purged.
    """
    if not prefixes:
        return 0
    conds = " OR ".join(["asset_name LIKE %s"] * len(prefixes))
    rows = frappe.db.sql_list(
        f"SELECT name FROM `tabAC Asset` WHERE {conds}",
        tuple(f"{p}%" for p in prefixes),
    )
    for name in rows:
        try:
            purge_asset(name)
        except Exception:  # noqa: BLE001
            pass
    frappe.db.commit()
    return len(rows)


def purge_category_by_name(*category_names: str) -> int:
    """Purge AC Asset Category rows by category_name field (autoname=CAT-#### →
    NEVER match by name, LL-TEST-9).

    First FK-purges any leaked test assets still referencing the category (so the
    category becomes deletable regardless of the asset's name prefix), then NULLs
    any non-asset references (e.g. IMM Device Model.asset_category) before delete.
    Skips a category only if a NON-test asset still references it. Returns count.
    """
    n = 0
    for cn in category_names:
        for cat in frappe.db.sql_list(
            "SELECT name FROM `tabAC Asset Category` WHERE category_name=%s", (cn,)
        ):
            # FK-purge any remaining test assets in this category.
            for an, aname in frappe.db.sql(
                "SELECT name, asset_name FROM `tabAC Asset` WHERE asset_category=%s",
                (cat,),
            ):
                if (aname or "").startswith(("_Test", "Gate", "Test ")):
                    try:
                        purge_asset(an)
                    except Exception:  # noqa: BLE001
                        pass
            if frappe.db.exists("AC Asset", {"asset_category": cat}):
                continue  # a genuine asset still uses it — leave it
            # Delete test PM Checklist Templates autonamed off this category
            # (PMCT-<cat>-<freq>) — they are test fixtures, not real config.
            for pmct in frappe.db.sql_list(
                "SELECT name FROM `tabPM Checklist Template` WHERE asset_category=%s", (cat,)
            ):
                try:
                    frappe.delete_doc("PM Checklist Template", pmct, force=True,
                                      ignore_permissions=True)
                except Exception:  # noqa: BLE001
                    frappe.db.set_value("PM Checklist Template", pmct,
                                        "asset_category", None, update_modified=False)
            # NULL any other non-asset FK refs so the delete won't 500.
            for dt in ("IMM Device Model", "Asset Commissioning"):
                if frappe.db.table_exists(dt) and frappe.db.has_column(dt, "asset_category"):
                    frappe.db.sql(
                        f"UPDATE `tab{dt}` SET asset_category=NULL WHERE asset_category=%s",
                        (cat,),
                    )
            try:
                frappe.delete_doc("AC Asset Category", cat, force=True,
                                  ignore_permissions=True)
                n += 1
            except Exception:  # noqa: BLE001
                pass
    frappe.db.commit()
    return n
