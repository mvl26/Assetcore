# Copyright (c) 2026, AssetCore Team
"""Purge leaked test MASTER/governance records left after the asset purge
(cleanup 2026-06-03, round 2 of expanded DB-wide sweep).

Covers DocTypes the first ``purge_leaked_test_data`` did NOT touch:
  - IMM User Competency  (FK to a _Test Model / _TEST-PROG → dangling test leak)
  - IMM CAPA Record      (description='Test effectiveness', root_cause/action='test')
  - AC Spare Part Stock  (child of test spare part) → AC Spare Part ("(test-override)")
  - IMM Device Model     ("_Test Model IMM06", "_Test RCA Model")
  - AC Asset Category    ("_ProbeCat11")
  - AC Location          ("FK-Integ Loc DEL-BLOCK")

Deletes children before parents (FK-safe). The 3 genuine demo assets
(TS-2025-*), 3 genuine incidents (IR-2026-0131/0132/0168) and every master they
reference are NEVER matched (allowlisted by resolving the asset FK closure).

    bench --site miyano execute assetcore.scripts.maintenance.purge_test_masters.run --kwargs "{'dry_run': 1}"
    bench --site miyano execute assetcore.scripts.maintenance.purge_test_masters.run
"""
from __future__ import annotations

import frappe

REAL_ASSET_CODES = ("TS-2025-USG-001", "TS-2025-VEN-001", "TS-2025-CT-001")


def _allowlist() -> dict[str, set[str]]:
    """FK closure of the 3 real assets — these masters are real, never purge."""
    allow: dict[str, set[str]] = {"AC Asset": set(REAL_ASSET_CODES)}
    fk = {"device_model": "IMM Device Model", "supplier": "AC Supplier",
          "location": "AC Location", "department": "AC Department",
          "asset_category": "AC Asset Category"}
    cols = [c for c in fk if frappe.db.has_column("AC Asset", c)]
    for r in frappe.get_all("AC Asset", filters={"name": ["in", list(REAL_ASSET_CODES)]},
                            fields=["name"] + cols, ignore_permissions=True):
        for col in cols:
            if r.get(col):
                allow.setdefault(fk[col], set()).add(r[col])
    return allow


def _candidates(allow: dict[str, set[str]]) -> dict[str, list[str]]:
    """Resolve the exact rác record-names per DocType (markers + FK-to-test)."""
    c: dict[str, list[str]] = {}
    esc = r" ESCAPE '\\'"

    # 1) Competencies whose device_model OR training_program carries a test marker
    #    (or is a dangling FK to a deleted test program).
    c["IMM User Competency"] = frappe.db.sql_list(
        "SELECT uc.name FROM `tabIMM User Competency` uc "
        "LEFT JOIN `tabIMM Device Model` dm ON dm.name = uc.device_model "
        "WHERE dm.model_name LIKE %s" + esc + " "
        "   OR uc.training_program LIKE %s" + esc,
        ("\\_Test%", "\\_TEST%"),
    )

    # 2) CAPA with test description / placeholder root_cause+action.
    #    All observed leaks: desc in {'Test effectiveness','Test fields',
    #    'Eval round 2 ...'} OR (root_cause='test' AND corrective_action='test')
    #    OR placeholder narratives ('RC narrative'/'CA narrative'/'Eval *').
    c["IMM CAPA Record"] = frappe.db.sql_list(
        "SELECT name FROM `tabIMM CAPA Record` WHERE "
        "description IN (%s, %s) "
        "OR description LIKE %s" + esc + " "
        "OR (root_cause = %s AND corrective_action = %s) "
        "OR (root_cause = %s AND corrective_action = %s) "
        "OR root_cause LIKE %s" + esc,
        ("Test effectiveness", "Test fields", "Eval round%",
         "test", "test", "RC narrative", "CA narrative", "Eval %narrative"),
    )

    # 3) Spare parts with "(test-override)" / _Test in part_name.
    sp = frappe.db.sql_list(
        "SELECT name FROM `tabAC Spare Part` "
        "WHERE part_name LIKE %s OR part_name LIKE %s" + esc,
        ("%(test-override)%", "\\_Test%"),
    )
    c["AC Spare Part"] = sp

    # 4) Device Models with _Test marker (excluding allowlist).
    dm = frappe.db.sql_list(
        "SELECT name FROM `tabIMM Device Model` WHERE model_name LIKE %s" + esc,
        ("\\_Test%",),
    )
    c["IMM Device Model"] = [x for x in dm if x not in allow.get("IMM Device Model", set())]

    # 5) Asset Categories with _Probe / _Test / _DBG (excluding allowlist).
    cat = frappe.db.sql_list(
        "SELECT name FROM `tabAC Asset Category` "
        "WHERE category_name LIKE %s" + esc + " OR category_name LIKE %s" + esc
        + " OR category_name LIKE %s" + esc,
        ("\\_Probe%", "\\_Test%", "\\_DBG%"),
    )
    c["AC Asset Category"] = [x for x in cat if x not in allow.get("AC Asset Category", set())]

    # 6) Locations with FK-Integ / _Test marker (excluding allowlist).
    loc = frappe.db.sql_list(
        "SELECT name FROM `tabAC Location` "
        "WHERE location_name LIKE %s OR location_name LIKE %s" + esc,
        ("FK-Integ%", "\\_Test%"),
    )
    c["AC Location"] = [x for x in loc if x not in allow.get("AC Location", set())]
    return c


def _delete(dt: str, name: str) -> None:
    doc = frappe.get_doc(dt, name)
    if doc.docstatus == 1:
        doc.cancel()
    frappe.delete_doc(dt, name, force=True, ignore_permissions=True,
                      delete_permanently=True)


def run(dry_run: int = 0) -> None:
    frappe.set_user("Administrator")
    allow = _allowlist()
    cand = _candidates(allow)

    print("=== ALLOWLIST (real-asset FK closure, never purge) ===")
    for dt, s in sorted(allow.items()):
        print(f"   {dt:20} -> {sorted(s)}")
    print("\n=== CANDIDATES (rác to delete) ===")
    for dt, names in cand.items():
        print(f"   {dt:22} = {len(names)}  e.g. {names[:3]}")

    if dry_run:
        print("\n[DRY-RUN] nothing deleted.")
        return

    # FK-safe order: competency → CAPA → spare-stock(child)+spare-part →
    # device-model → category → location.
    order = ["IMM User Competency", "IMM CAPA Record"]
    counts: dict[str, int] = {}
    for dt in order:
        n = 0
        for name in cand.get(dt, []):
            try:
                _delete(dt, name)
                n += 1
            except Exception as e:  # noqa: BLE001
                print(f"  [{dt}-skip] {name}: {e}")
        frappe.db.commit()
        counts[dt] = n

    # Spare parts: delete child stock rows first, then the part.
    n_stock = n_sp = 0
    for sp in cand.get("AC Spare Part", []):
        for st in frappe.get_all("AC Spare Part Stock",
                                 filters={"spare_part": sp}, pluck="name"):
            try:
                _delete("AC Spare Part Stock", st)
                n_stock += 1
            except Exception as e:  # noqa: BLE001
                print(f"  [stock-skip] {st}: {e}")
        try:
            _delete("AC Spare Part", sp)
            n_sp += 1
        except Exception as e:  # noqa: BLE001
            print(f"  [spare-skip] {sp}: {e}")
    frappe.db.commit()
    counts["AC Spare Part Stock"] = n_stock
    counts["AC Spare Part"] = n_sp

    for dt in ("IMM Device Model", "AC Asset Category", "AC Location"):
        n = 0
        for name in cand.get(dt, []):
            try:
                _delete(dt, name)
                n += 1
            except Exception as e:  # noqa: BLE001
                print(f"  [{dt}-skip] {name}: {e}")
        frappe.db.commit()
        counts[dt] = n

    print("\n=== DELETED ===")
    for dt, n in counts.items():
        print(f"   {dt:24} -{n}")
