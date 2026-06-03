# Copyright (c) 2026, AssetCore Team
"""Clean orphan dependents left after the leaked-asset purge (2026-06-03).

After purging 616 rác AC Assets, two dependent DocTypes were left dangling
(``purge_asset`` skipped them under a permission filter): draft
``IMM Calibration Schedule`` + ``IMM CAPA Record`` pointing to deleted rác
assets. All are docstatus=0 and reference now-gone _Test/Gate assets → rác.

One REAL ``Incident Report`` (IR-2026-0131, genuine VI description) also lost
its asset; we do NOT delete the incident — we NULL its dangling FK and report it.

Idempotent.

    bench --site miyano execute assetcore.scripts.maintenance.purge_orphan_dependents.run --kwargs "{'dry_run': 1}"
    bench --site miyano execute assetcore.scripts.maintenance.purge_orphan_dependents.run
"""
from __future__ import annotations

import frappe

_ORPHAN_DEPENDENTS = [
    ("IMM Calibration Schedule", "asset"),
    ("IMM CAPA Record", "asset"),
    ("IMM RCA Record", "asset"),
    ("PM Work Order", "asset_ref"),
    ("Asset Repair", "asset_ref"),
]


def _orphan_names(table: str, fld: str) -> list[tuple[str, int]]:
    if not frappe.db.table_exists(table) or not frappe.db.has_column(table, fld):
        return []
    return frappe.db.sql(
        f"SELECT t.name, t.docstatus FROM `tab{table}` t "
        f"LEFT JOIN `tabAC Asset` a ON a.name = t.`{fld}` "
        f"WHERE t.`{fld}` IS NOT NULL AND t.`{fld}` != '' AND a.name IS NULL"
    )


def run(dry_run: int = 0) -> None:
    frappe.set_user("Administrator")

    plan: dict[str, list[tuple[str, int]]] = {}
    for table, fld in _ORPHAN_DEPENDENTS:
        rows = _orphan_names(table, fld)
        if rows:
            plan[table] = rows

    # Real incident orphans: keep doc, null FK.
    inc_orphans = frappe.db.sql(
        "SELECT t.name FROM `tabIncident Report` t "
        "LEFT JOIN `tabAC Asset` a ON a.name = t.asset "
        "WHERE t.asset IS NOT NULL AND t.asset != '' AND a.name IS NULL"
    )

    print("=== PLAN ===")
    for table, rows in plan.items():
        sub = sum(1 for _, ds in rows if ds == 1)
        print(f"   delete {table}: {len(rows)} orphan (submitted={sub})")
    print(f"   NULL Incident Report.asset on {len(inc_orphans)} real incident(s): "
          f"{[r[0] for r in inc_orphans]}")

    if dry_run:
        print("\n[DRY-RUN] nothing changed.")
        return

    for table, rows in plan.items():
        n = 0
        for name, ds in rows:
            try:
                doc = frappe.get_doc(table, name)
                if doc.docstatus == 1:
                    doc.cancel()
                frappe.delete_doc(table, name, force=True, ignore_permissions=True,
                                  delete_permanently=True)
                n += 1
            except Exception as e:  # noqa: BLE001
                print(f"  [{table}-skip] {name}: {e}")
        frappe.db.commit()
        print(f"   deleted {table}: {n}")

    # NULL the dangling FK on real incidents (raw SQL — avoid revalidation).
    for (name,) in inc_orphans:
        frappe.db.set_value("Incident Report", name, "asset", None,
                            update_modified=False)
    frappe.db.commit()
    print(f"   nulled asset FK on {len(inc_orphans)} real incident(s)")
    print("[done]")
