"""Check DB state for reference data."""
import frappe


def run():
    frappe.set_user("Administrator")
    depts = frappe.db.sql(
        "SELECT name, department_name, department_code, is_active FROM `tabAC Department`",
        as_dict=True
    )
    print("=== DEPARTMENTS ===")
    for d in depts:
        print(f"  name={d['name']!r}, dept_name={d['department_name']!r}, code={d['department_code']!r}")

    locs = frappe.db.sql(
        "SELECT name, location_name, location_code FROM `tabAC Location`",
        as_dict=True
    )
    print("=== LOCATIONS ===")
    for l in locs:
        print(f"  name={l['name']!r}, loc_name={l['location_name']!r}")

    cats = frappe.db.sql(
        "SELECT name, category_name FROM `tabAC Asset Category`",
        as_dict=True
    )
    print("=== CATEGORIES ===")
    for c in cats:
        print(f"  name={c['name']!r}, cat_name={c['category_name']!r}")
