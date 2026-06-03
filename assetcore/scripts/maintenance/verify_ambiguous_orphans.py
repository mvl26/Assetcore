# Copyright (c) 2026, AssetCore Team
"""READ-ONLY re-verification of the 53 ambiguous dangling-FK orphans flagged by
``purge_orphan_logs.py`` (cleanup 2026-06-03). NEVER writes.

For each of the 4 groups it confirms:
  1. the FK target is genuinely GONE (dangling) — not a live link;
  2. the holding record / its parent doc is NOT one of the 3 real demo assets,
     3 real incidents, or any seed-demo master in the real FK allowlist.

Child-table rows (AC Purchase Device Item, Procurement Plan Line) are reported
WITH their parent doc + whether that parent is itself test garbage, so we can
decide: delete whole parent vs. drop just the orphan child row.

    bench --site miyano execute assetcore.scripts.maintenance.verify_ambiguous_orphans.run
"""
from __future__ import annotations

import frappe

from assetcore.scripts.maintenance.scan_test_garbage import (
    MARKERS,
    REAL_ASSET_CODES,
    REAL_INCIDENTS,
    _allowlist_fk,
)

# (top-dt, fk-field, target-dt)
_TOP_GROUPS = [
    ("AC Purchase", "supplier", "AC Supplier"),
    ("AC Warehouse", "location", "AC Location"),
    ("AC Warehouse", "department", "AC Department"),
]
# (child-dt, fk-field, target-dt, parent-dt)
_CHILD_GROUPS = [
    ("AC Purchase Device Item", "device_model", "IMM Device Model", "AC Purchase"),
    ("Procurement Plan Line", "needs_request", "IMM Needs Request", "IMM Procurement Plan"),
]


def _dangling(dt: str, fld: str, parent: str):
    """Rows where t.fld is set but the target record does not exist."""
    has_parent = frappe.db.has_column(dt, "parent")
    pcols = "t.parent, t.parenttype" if has_parent else "NULL AS parent, NULL AS parenttype"
    return frappe.db.sql(
        f"SELECT t.name, t.`{fld}` AS fk, t.docstatus, {pcols} "
        f"FROM `tab{dt}` t LEFT JOIN `tab{parent}` p ON p.name = t.`{fld}` "
        f"WHERE t.`{fld}` IS NOT NULL AND t.`{fld}` != '' AND p.name IS NULL",
        as_dict=True,
    )


def _is_garbage_name(dt: str, name: str) -> bool:
    if name in REAL_ASSET_CODES or name in REAL_INCIDENTS:
        return False
    blob = name
    for f in ("purchase_name", "supplier_name", "warehouse_name", "plan_name",
              "title", "description", "remarks"):
        if frappe.db.has_column(dt, f):
            v = frappe.db.get_value(dt, name, f)
            if v:
                blob += " | " + str(v)
    return bool(MARKERS.search(blob))


def run() -> None:
    frappe.set_user("Administrator")
    allow = _allowlist_fk()
    print("=== REAL allowlist (NEVER delete) ===")
    print(f"   AC Asset = {sorted(allow.get('AC Asset', set()))}")
    print(f"   Incident Report = {sorted(allow.get('Incident Report', set()))}")
    for dt in ("AC Supplier", "IMM Device Model", "AC Location", "AC Department"):
        if allow.get(dt):
            print(f"   {dt} (FK-closure of real assets) = {sorted(allow[dt])}")

    grand = 0

    print("\n=== TOP-LEVEL dangling-FK orphans ===")
    purch_supplier_dangling: set[str] = set()
    for dt, fld, target in _TOP_GROUPS:
        rows = _dangling(dt, fld, target)
        grand += len(rows)
        print(f"\n[{dt}.{fld} -> {target}]  count={len(rows)}  (total {dt}={frappe.db.count(dt)})")
        for r in rows:
            in_allow = r["name"] in allow.get(dt, set())
            real = r["name"] in REAL_ASSET_CODES or r["name"] in REAL_INCIDENTS
            garb = _is_garbage_name(dt, r["name"])
            flag = "REAL/ALLOW!!" if (in_allow or real) else ("garbage" if garb else "neutral-orphan")
            print(f"    {r['name']:22} fk={r['fk']:22} ds={r['docstatus']}  [{flag}]")
            if dt == "AC Purchase":
                purch_supplier_dangling.add(r["name"])

    print("\n=== CHILD-TABLE dangling-FK orphans (parent doc still alive?) ===")
    for dt, fld, target, pdt in _CHILD_GROUPS:
        rows = _dangling(dt, fld, target)
        grand += len(rows)
        print(f"\n[{dt}.{fld} -> {target}]  count={len(rows)}  parent={pdt}")
        parents: dict[str, list] = {}
        for r in rows:
            parents.setdefault(r["parent"], []).append(r["name"])
        for pname, child_names in sorted(parents.items()):
            p_exists = frappe.db.exists(pdt, pname)
            if not p_exists:
                flag = "PARENT-GONE(true-orphan-row -> raw-SQL delete child rows)"
            else:
                p_garb = _is_garbage_name(pdt, pname)
                # supplier link on this AC Purchase parent: live or dangling?
                sup = frappe.db.get_value(pdt, pname, "supplier") if frappe.db.has_column(pdt, "supplier") else None
                sup_live = bool(sup and frappe.db.exists("AC Supplier", sup))
                also_sup_dangling = pname in purch_supplier_dangling
                tag = "supplier-DANGLING(covered by parent-delete)" if also_sup_dangling else (
                    f"supplier-LIVE({sup})" if sup_live else f"supplier={sup}")
                flag = ("garbage-parent " if p_garb else "NEUTRAL-parent ") + tag
            print(f"    parent {pname:22} child-rows={len(child_names)}  [{flag}]")

    print(f"\n=== GRAND TOTAL dangling-FK rows across 4 groups = {grand} ===")

    # Cross-check: which AC Purchase parents holding orphan device rows are NOT
    # already covered by the supplier-dangling parent-delete set.
    dev_rows = _dangling("AC Purchase Device Item", "device_model", "IMM Device Model")
    dev_parents = {r["parent"] for r in dev_rows}
    not_covered = sorted(dev_parents - purch_supplier_dangling)
    print("\n=== AC Purchase parents w/ orphan device rows but LIVE supplier "
          "(NOT covered by supplier-delete) ===")
    for pname in not_covered:
        sup = frappe.db.get_value("AC Purchase", pname, "supplier")
        sup_live = bool(sup and frappe.db.exists("AC Supplier", sup))
        ndev = frappe.db.count("AC Purchase Device Item", {"parent": pname})
        ndev_orphan = sum(1 for r in dev_rows if r["parent"] == pname)
        print(f"    {pname:22} supplier={sup}(live={sup_live}) "
              f"device_rows={ndev} orphan_device_rows={ndev_orphan}")
