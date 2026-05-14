"""Check AC Asset records."""
import frappe


def run():
    frappe.set_user("Administrator")
    assets = frappe.db.sql("SELECT name, asset_name, status FROM `tabAC Asset`", as_dict=True)
    print("Total assets:", len(assets))
    for a in assets:
        print(f"  {a['name']}: {a['asset_name']} [{a['status']}]")
