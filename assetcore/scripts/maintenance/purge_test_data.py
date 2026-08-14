"""
Purge all AssetCore business data.

Auto-discovers every DocType belonging to the `assetcore` app via Module Def,
so adding a new DocType requires NO change to this script.

Run:
    bench --site <site> execute assetcore.scripts.maintenance.purge_test_data.run

Keep (NOT touched): User, Role, Workflow, Custom Field, Server Script,
Translation, Email Account, System Settings, and anything outside
the `assetcore` app's modules.
"""
from __future__ import annotations

import frappe


EXTRA_EXCLUDE: set[str] = {
    # DocTypes belonging to AssetCore that must survive a purge
    # (config / catalog / shared reference). Edit this set if needed.
}


def _assetcore_modules() -> list[str]:
    return frappe.get_all("Module Def", filters={"app_name": "assetcore"}, pluck="name")


def _discover_doctypes() -> tuple[list[dict], list[dict]]:
    """Return (child_tables, parents) — both sorted alphabetically.

    Child tables go first so they're cleared before their parents, avoiding
    orphan rows if a parent delete fails partway.
    """
    modules = _assetcore_modules()
    if not modules:
        return [], []

    rows = frappe.get_all(
        "DocType",
        filters={
            "module": ["in", modules],
            "issingle": 0,
            "name": ["not in", list(EXTRA_EXCLUDE)] if EXTRA_EXCLUDE else ["!=", ""],
        },
        fields=["name", "istable", "is_submittable"],
        order_by="name asc",
    )
    children = [r for r in rows if r.istable]
    parents = [r for r in rows if not r.istable]
    return children, parents


def _truncate(table: str) -> int:
    try:
        count = frappe.db.sql(f"SELECT COUNT(*) FROM `{table}`")[0][0]
    except Exception:
        return 0
    if not count:
        return 0
    frappe.db.sql(f"DELETE FROM `{table}`")
    frappe.db.commit()
    return count


def _delete_parent(doctype: str) -> int:
    table = f"tab{doctype}"
    try:
        names = [r[0] for r in frappe.db.sql(f"SELECT name FROM `{table}`")]
    except Exception:
        return 0
    if not names:
        return 0

    deleted = 0
    for name in names:
        try:
            doc = frappe.get_doc(doctype, name)
            if doc.docstatus == 1:
                doc.flags.ignore_permissions = True
                doc.flags.ignore_links = True
                doc.cancel()
                frappe.db.commit()
            frappe.delete_doc(
                doctype, name,
                force=True,
                ignore_permissions=True,
                ignore_missing=True,
                ignore_on_trash=True,
                delete_permanently=True,
            )
            frappe.db.commit()
            deleted += 1
        except Exception:
            # last resort: raw SQL (skips on_trash + audit log)
            try:
                frappe.db.sql(f"DELETE FROM `{table}` WHERE name=%s", name)
                frappe.db.commit()
                deleted += 1
            except Exception as e:
                print(f"  WARN {doctype} {name}: {e}")
    return deleted


def run(dry_run: bool = False) -> None:
    frappe.set_user("Administrator")
    children, parents = _discover_doctypes()

    print("=== AssetCore purge ===")
    print(f"App modules : {len(_assetcore_modules())}")
    print(f"Child tables: {len(children)}")
    print(f"Parent doctypes: {len(parents)}")
    if EXTRA_EXCLUDE:
        print(f"Excluded   : {sorted(EXTRA_EXCLUDE)}")
    print()

    if dry_run:
        print("-- DRY RUN — would delete from:")
        for r in parents:
            tag = "[submit]" if r.is_submittable else "        "
            print(f"  {tag} {r.name}")
        for r in children:
            print(f"  [child]  {r.name}")
        return

    print("-- Phase 1: truncate child tables --")
    for r in children:
        n = _truncate(f"tab{r.name}")
        if n:
            print(f"  {n:>6} × {r.name}")

    print("\n-- Phase 2: delete parent doctypes --")
    for r in parents:
        n = _delete_parent(r.name)
        if n:
            tag = "[S]" if r.is_submittable else "   "
            print(f"  {n:>6} × {tag} {r.name}")

    frappe.db.commit()

    print("\n-- Remaining row counts --")
    total = 0
    for r in parents:
        try:
            c = frappe.db.sql(f"SELECT COUNT(*) FROM `tab{r.name}`")[0][0]
            if c:
                print(f"  {c:>6} × {r.name}")
                total += c
        except Exception:
            pass
    print(f"\nTotal remaining rows in AssetCore parents: {total}")
    print("=== Purge complete ===")


def dry_run() -> None:
    """Preview without deleting: bench --site X execute assetcore.scripts.maintenance.purge_test_data.dry_run"""
    run(dry_run=True)
