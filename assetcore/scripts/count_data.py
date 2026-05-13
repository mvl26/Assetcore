import frappe

def run():
    doctypes = [
        "AC Asset", "AC Supplier", "AC Location", "AC Department", "AC Asset Category",
        "IMM Device Model",
        "IMM Needs Request", "IMM Procurement Plan", "IMM Tech Spec",
        "IMM Vendor Evaluation", "IMM Procurement Decision", "Vendor AVL",
        "IMM Vendor Profile",
        "Asset Commissioning", "AC Purchase",
        "IMM Program",
        "AC PM Schedule", "AC PM Work Order", "Asset Repair",
        "IMM Asset Calibration",
        "Incident Report", "IMM RCA", "IMM CAPA Record",
        "AC Spare Part", "AC Stock Movement", "AC Warehouse",
        "IMM Audit Trail", "Asset Lifecycle Event",
    ]
    for dt in doctypes:
        try:
            count = frappe.db.count(dt)
            if count > 0:
                print(f"{dt}: {count}")
        except Exception as e:
            pass
