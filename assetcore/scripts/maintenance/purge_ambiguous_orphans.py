# Copyright (c) 2026, AssetCore Team
"""Purge the 53 user-approved dangling-FK orphans left after test/seed masters
were deleted (cleanup 2026-06-03, run 4 — final tail).

These are the ``_AMBIGUOUS`` group reported (but never purged) by
``purge_orphan_logs.py``. The user has explicitly approved deleting them. Each
row's FK target has been re-verified GONE and none touch the 3 real demo assets,
3 real incidents, or the real-asset FK-closure allowlist (see
``verify_ambiguous_orphans.run``).

FK-safe strategy (child rows removed BEFORE / instead of destroying live parents):

  G1  AC Purchase (supplier dangling, 17 docs)  -> delete whole top-level doc
      (parent itself is orphaned; ORM-delete cascades its child device rows,
       which covers 16 of the 24 dangling device_model child rows).
  G2  AC Purchase Device Item.device_model on LIVE-supplier purchases (8 rows)
      -> the parent purchase is NOT orphaned (supplier AC-SUP-2026-0049 alive,
         shared with non-orphan siblings) so we delete ONLY the orphan child
         row (raw-SQL on child table), keeping the parent intact.
  G3  AC Warehouse (location AND department both dangling, 3 docs, 0 stock,
      0 movement refs) -> delete whole top-level doc.
  G4  Procurement Plan Line.needs_request (6 rows, parent IMM Procurement Plan
      already GONE) -> true leaked child rows -> raw-SQL delete on child table.

Idempotent + dry-run capable. Prints before->after counts per group.

    bench --site miyano execute assetcore.scripts.maintenance.purge_ambiguous_orphans.run --kwargs "{'dry_run': 1}"
    bench --site miyano execute assetcore.scripts.maintenance.purge_ambiguous_orphans.run
"""
from __future__ import annotations

import frappe

_CHILD_DEV = "AC Purchase Device Item"
_PPL = "Procurement Plan Line"


def _dangling_top(dt: str, fld: str, target: str) -> list[str]:
    rows = frappe.db.sql(
        f"SELECT t.name FROM `tab{dt}` t "
        f"LEFT JOIN `tab{target}` p ON p.name = t.`{fld}` "
        f"WHERE t.`{fld}` IS NOT NULL AND t.`{fld}` != '' AND p.name IS NULL",
        pluck="name",
    )
    return list(rows)


def _dangling_child(dt: str, fld: str, target: str):
    """Return (child_name, parent_name, parent_exists) for orphan child rows."""
    return frappe.db.sql(
        f"SELECT t.name, t.parent, t.parenttype FROM `tab{dt}` t "
        f"LEFT JOIN `tab{target}` p ON p.name = t.`{fld}` "
        f"WHERE t.`{fld}` IS NOT NULL AND t.`{fld}` != '' AND p.name IS NULL",
        as_dict=True,
    )


def run(dry_run: int = 0) -> None:
    frappe.set_user("Administrator")
    dry = bool(int(dry_run))
    mode = "DRY-RUN (no writes)" if dry else "LIVE DELETE"
    print(f"=== purge_ambiguous_orphans :: {mode} ===\n")

    # ---- snapshot BEFORE ----
    purch_sup = _dangling_top("AC Purchase", "supplier", "AC Supplier")
    wh_loc = _dangling_top("AC Warehouse", "location", "AC Location")
    wh_dep = _dangling_top("AC Warehouse", "department", "AC Department")
    wh_all = sorted(set(wh_loc) | set(wh_dep))
    dev_rows = _dangling_child(_CHILD_DEV, "device_model", "IMM Device Model")
    ppl_rows = _dangling_child(_PPL, "needs_request", "IMM Needs Request")

    # device child rows whose parent is one of the supplier-dangling purchases
    # (covered by G1 parent-delete) vs. live-supplier purchases (delete child only)
    dev_covered = [r for r in dev_rows if r["parent"] in set(purch_sup)]
    dev_orphan_only = [r for r in dev_rows if r["parent"] not in set(purch_sup)]

    print("BEFORE:")
    print(f"  G1 AC Purchase (supplier dangling)          = {len(purch_sup)}")
    print(f"  G2 AC Purchase Device Item.device_model     = {len(dev_rows)} "
          f"({len(dev_covered)} via parent-delete + {len(dev_orphan_only)} child-only)")
    print(f"  G3 AC Warehouse (loc/dept dangling)         = {len(wh_all)} docs "
          f"({len(wh_loc)} loc + {len(wh_dep)} dept FK cells)")
    print(f"  G4 Procurement Plan Line.needs_request      = {len(ppl_rows)}")
    print(f"  -> dangling-FK rows total = "
          f"{len(purch_sup) + len(dev_rows) + len(wh_loc) + len(wh_dep) + len(ppl_rows)}"
          " (counting loc+dept as 2 cells/warehouse, per STATE)\n")

    if dry:
        print("[DRY-RUN] nothing deleted. Plan above is what LIVE would do.")
        return

    # ---- G1: delete whole supplier-dangling purchases (cascades 16 child rows) ----
    n1 = 0
    for name in purch_sup:
        if not frappe.db.exists("AC Purchase", name):
            continue
        if frappe.db.get_value("AC Purchase", name, "docstatus") == 1:
            frappe.get_doc("AC Purchase", name).cancel()
        frappe.delete_doc("AC Purchase", name, force=True,
                          ignore_permissions=True, delete_permanently=True)
        n1 += 1
    frappe.db.commit()
    print(f"  G1 deleted AC Purchase docs: {n1}")

    # ---- G2: delete ONLY orphan child rows on live-supplier purchases ----
    n2 = 0
    for r in dev_orphan_only:
        if frappe.db.exists(_CHILD_DEV, r["name"]):
            frappe.db.sql(f"DELETE FROM `tab{_CHILD_DEV}` WHERE name=%s", (r["name"],))
            n2 += 1
    frappe.db.commit()
    print(f"  G2 deleted live-supplier orphan child rows : {n2}")

    # ---- G3: delete whole orphaned warehouses (both FKs dangle, 0 refs) ----
    n3 = 0
    for name in wh_all:
        if not frappe.db.exists("AC Warehouse", name):
            continue
        if frappe.db.get_value("AC Warehouse", name, "docstatus") == 1:
            frappe.get_doc("AC Warehouse", name).cancel()
        frappe.delete_doc("AC Warehouse", name, force=True,
                          ignore_permissions=True, delete_permanently=True)
        n3 += 1
    frappe.db.commit()
    print(f"  G3 deleted AC Warehouse docs: {n3}")

    # ---- G4: delete leaked Procurement Plan Line child rows (parent gone) ----
    n4 = 0
    for r in ppl_rows:
        if frappe.db.exists(_PPL, r["name"]):
            frappe.db.sql(f"DELETE FROM `tab{_PPL}` WHERE name=%s", (r["name"],))
            n4 += 1
    frappe.db.commit()
    print(f"  G4 deleted leaked Procurement Plan Line rows: {n4}")

    # ---- snapshot AFTER ----
    after_purch = _dangling_top("AC Purchase", "supplier", "AC Supplier")
    after_wh_loc = _dangling_top("AC Warehouse", "location", "AC Location")
    after_wh_dep = _dangling_top("AC Warehouse", "department", "AC Department")
    after_dev = _dangling_child(_CHILD_DEV, "device_model", "IMM Device Model")
    after_ppl = _dangling_child(_PPL, "needs_request", "IMM Needs Request")
    print("\nAFTER (dangling-FK remaining):")
    print(f"  G1 AC Purchase.supplier                 = {len(after_purch)}")
    print(f"  G2 AC Purchase Device Item.device_model = {len(after_dev)}")
    print(f"  G3 AC Warehouse.location/department     = {len(after_wh_loc)}/{len(after_wh_dep)}")
    print(f"  G4 Procurement Plan Line.needs_request  = {len(after_ppl)}")
    print(f"\n[done] G1={n1} purchases, G2={n2} child rows, "
          f"G3={n3} warehouses, G4={n4} plan-line rows.")
