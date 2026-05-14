"""Create and approve AVL entries for all winner suppliers."""
import frappe
from assetcore.api.imm03 import _create_avl_entry, _approve_avl

SUP_DRAGER   = "AC-SUP-2026-0017"
SUP_BINHMINH = "AC-SUP-2026-0018"
SUP_MEDITR   = "AC-SUP-2026-0021"

DT_AVL = "IMM AVL Entry"


def run():
    frappe.set_user("Administrator")

    # Get device categories from tech specs
    specs = frappe.db.sql(
        "SELECT name, device_category FROM `tabIMM Tech Spec`",
        as_dict=True,
    )
    print("Tech Spec device categories:")
    for ts in specs:
        print(f"  {ts['name']} → device_category={ts['device_category']!r}")

    # Get all categories to map by spec
    cats = frappe.db.sql("SELECT name FROM `tabAC Asset Category`", as_list=True)
    cat_names = [c[0] for c in cats]
    print(f"Available categories: {cat_names}")

    # Build AVL entries: (supplier, category) pairs for winners
    # TS-26-00007 winner=BINHMINH, TS-26-00008 winner=BINHMINH, TS-26-00009 winner=MEDITR
    # We need all 3 categories covered for all 3 suppliers (safe to have extras)
    avl_needed = []
    for ts in specs:
        cat = ts["device_category"]
        if not cat:
            print(f"  WARNING: {ts['name']} has no device_category — skipping")
            continue
        # Add winner supplier for each spec
        winner = SUP_MEDITR if ts["name"] == "TS-26-00009" else SUP_BINHMINH
        avl_needed.append({"supplier": winner, "category": cat, "spec": ts["name"]})

    # Also add Drager for life support (bonus)
    avl_needed.append({"supplier": SUP_DRAGER, "category": "Thiet-bi-Ho-tro-Su-song", "spec": "bonus"})

    for entry in avl_needed:
        sup, cat = entry["supplier"], entry["category"]
        existing = frappe.db.get_value(
            DT_AVL,
            {"supplier": sup, "device_category": cat, "docstatus": ["!=", 2]},
            "name",
        )
        if existing:
            existing_state = frappe.db.get_value(DT_AVL, existing, "workflow_state")
            print(f"  EXISTS: {existing} ({sup}/{cat}) state={existing_state}")
            if existing_state != "Approved":
                _approve_avl(existing, "Administrator", "")
                frappe.db.commit()
                print(f"  → Approved")
            continue

        result = _create_avl_entry(sup, cat, 3, "2025-01-01")
        frappe.db.commit()
        avl_name = result["name"]
        print(f"  Created: {avl_name} ({sup}/{cat})")

        _approve_avl(avl_name, "Administrator", "")
        frappe.db.commit()
        print(f"  → Approved")

    # Verify
    avls = frappe.db.sql(
        f"SELECT name, supplier, device_category, workflow_state, docstatus "
        f"FROM `tab{DT_AVL}`",
        as_dict=True,
    )
    print(f"\nAVL entries ({len(avls)}):")
    for avl in avls:
        print(f"  {avl['name']} sup={avl['supplier']} cat={avl['device_category']} "
              f"state={avl['workflow_state']} docstatus={avl['docstatus']}")
    print("Done.")
