"""Create required AC UOM records."""
import frappe


def run():
    frappe.set_user("Administrator")
    uoms = ["Cái", "Bộ", "Chiếc", "Hộp", "Cuộn", "Chai", "Lọ"]
    for name in uoms:
        if not frappe.db.exists("AC UOM", name):
            doc = frappe.get_doc({"doctype": "AC UOM", "uom_name": name})
            doc.insert(ignore_permissions=True)
            frappe.db.commit()
            print(f"  Created: {name}")
        else:
            print(f"  Exists: {name}")
    print("Done.")
