"""Create required UOM records for AssetCore."""
import frappe


def run():
    frappe.set_user("Administrator")
    uoms = [
        {"uom_name": "Cái", "must_be_whole_number": 1},
        {"uom_name": "Bộ", "must_be_whole_number": 1},
        {"uom_name": "Chiếc", "must_be_whole_number": 1},
        {"uom_name": "Hộp", "must_be_whole_number": 1},
    ]
    for data in uoms:
        if not frappe.db.exists("UOM", data["uom_name"]):
            doc = frappe.get_doc({"doctype": "UOM", **data})
            doc.insert(ignore_permissions=True)
            frappe.db.commit()
            print(f"  Created UOM: {data['uom_name']}")
        else:
            print(f"  Exists: {data['uom_name']}")
    print("Done.")
