"""Fix asset gmdn_status to valid options + lifecycle to Active."""
import frappe


def run():
    for a in frappe.get_all("AC Asset", fields=["name"]):
        frappe.db.set_value("AC Asset", a.name, "gmdn_status", "In Use")
        frappe.db.set_value("AC Asset", a.name, "lifecycle_status", "Commissioned")
    frappe.db.commit()
    print("Updated all assets to gmdn_status=In Use, lifecycle_status=Commissioned")
