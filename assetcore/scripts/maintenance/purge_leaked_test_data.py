# Copyright (c) 2026, AssetCore Team
"""Purge leaked test/debug fixtures from a polluted site (cleanup 2026-06-03).

Idempotent. Re-uses the proven ``purge_asset`` helper (cancels submitted
children + raw-SQL deletes append-only IMM Audit Trail / Asset Lifecycle Event /
Asset Document, which all throw in ``on_trash``).

Classifier (denylist): asset_name prefix ``_Test`` / ``Gate Test`` /
``Gate Cron`` / ``Gate5`` / ``_DBG`` or substring pytest / ``Test Asset IMM`` /
``SLA Test``. The 3 genuine demo assets (``TS-2025-USG/VEN/CT-001`` — real
Vietnamese device names) carry NO marker → NEVER matched.

    # preview only (no writes):
    bench --site miyano execute assetcore.scripts.maintenance.purge_leaked_test_data.run --kwargs "{'dry_run': 1}"
    # execute:
    bench --site miyano execute assetcore.scripts.maintenance.purge_leaked_test_data.run
"""
from __future__ import annotations

import frappe

from assetcore.tests._helpers._asset_cleanup import purge_asset

_ASSET_PREFIXES = ("_Test", "Gate Test", "Gate Cron", "Gate5", "_DBG")
_ASSET_SUBSTR = ("pytest", "Test Asset IMM", "Test Asset Xmod", "SLA Test")
_ESC = " ESCAPE '\\\\'"


def _is_rac_asset(an: str) -> bool:
    an = an or ""
    return an.startswith(_ASSET_PREFIXES) or any(s in an for s in _ASSET_SUBSTR)


def _rac_assets() -> list[str]:
    rows = frappe.db.sql("SELECT name, asset_name FROM `tabAC Asset`")
    return [name for name, an in rows if _is_rac_asset(an)]


def _rac_categories() -> list[tuple[str, str]]:
    # AC Asset Category autoname = CAT-#### → match by category_name field.
    return frappe.db.sql(
        "SELECT name, category_name FROM `tabAC Asset Category` "
        "WHERE category_name LIKE %s" + _ESC + " OR category_name LIKE %s" + _ESC,
        ("\\_Test%", "\\_DBG%"),
    )


def _rac_incidents() -> list[str]:
    return frappe.db.sql_list(
        "SELECT name FROM `tabIncident Report` "
        "WHERE description LIKE %s" + _ESC, ("\\_Test%",)
    )


def _rac_training() -> list[str]:
    return frappe.db.sql_list(
        "SELECT name FROM `tabIMM Training Program` "
        "WHERE name LIKE %s" + _ESC + " OR program_name LIKE %s" + _ESC,
        ("\\_TEST%", "\\_Test%"),
    )


def _counts() -> dict[str, int]:
    return {
        "AC Asset": frappe.db.count("AC Asset"),
        "AC Asset Category": frappe.db.count("AC Asset Category"),
        "Incident Report": frappe.db.count("Incident Report"),
        "IMM Training Program": frappe.db.count("IMM Training Program"),
        "IMM Audit Trail": frappe.db.count("IMM Audit Trail"),
        "Asset Lifecycle Event": frappe.db.count("Asset Lifecycle Event"),
        "Asset Document": frappe.db.count("Asset Document"),
    }


def _safe_delete(dt: str, name: str) -> None:
    doc = frappe.get_doc(dt, name)
    if doc.docstatus == 1:
        doc.cancel()
    frappe.delete_doc(dt, name, force=True, ignore_permissions=True,
                      delete_permanently=True)


def run(dry_run: int = 0) -> None:
    frappe.set_user("Administrator")
    assets = _rac_assets()
    cats = _rac_categories()
    incidents = _rac_incidents()
    training = _rac_training()

    print("=== BEFORE ===")
    before = _counts()
    for k, v in before.items():
        print(f"   {k:24} = {v}")
    print(f"\n[plan] purge: assets={len(assets)} categories={len(cats)} "
          f"incidents={len(incidents)} training={len(training)}")

    if dry_run:
        print("\n[DRY-RUN] nothing deleted. Sample assets:")
        for n in assets[:5]:
            print(f"   {n} | {frappe.db.get_value('AC Asset', n, 'asset_name')!r}")
        for name, label in cats:
            print(f"   CAT {name} | {label!r}")
        return

    # 1) Standalone test incidents NOT bound to a rác asset get cleared first
    #    (purge_asset handles incidents on rác assets; this catches strays).
    n_inc = 0
    for inc in incidents:
        try:
            _safe_delete("Incident Report", inc)
            n_inc += 1
        except Exception as e:  # noqa: BLE001
            print(f"  [incident-skip] {inc}: {e}")
    frappe.db.commit()

    # 2) Assets — purge_asset cancels children (incidents/CAPA/RCA/WO) + audit.
    n_asset = 0
    for i, name in enumerate(assets, 1):
        try:
            purge_asset(name)
            n_asset += 1
        except Exception as e:  # noqa: BLE001
            print(f"  [asset-skip] {name}: {e}")
        if i % 50 == 0:
            frappe.db.commit()
            print(f"  ...purged {i}/{len(assets)} assets")
    frappe.db.commit()

    # 3) Test categories (FK parents now free) — match by name (already resolved).
    n_cat = 0
    for name, _label in cats:
        try:
            _safe_delete("AC Asset Category", name)
            n_cat += 1
        except Exception as e:  # noqa: BLE001
            print(f"  [cat-skip] {name}: {e}")

    # 4) Test training programs.
    n_prog = 0
    for prog in training:
        try:
            _safe_delete("IMM Training Program", prog)
            n_prog += 1
        except Exception as e:  # noqa: BLE001
            print(f"  [prog-skip] {prog}: {e}")
    frappe.db.commit()

    print(f"\n[done] purged incidents={n_inc} assets={n_asset} "
          f"categories={n_cat} training={n_prog}")
    print("\n=== AFTER ===")
    after = _counts()
    for k, v in after.items():
        print(f"   {k:24} = {v}  (Δ {v - before[k]:+d})")
