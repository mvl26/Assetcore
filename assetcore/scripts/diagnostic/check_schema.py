def run():
    import frappe
    import traceback
    frappe.set_user("Administrator")
    # Ensure asset with custom_risk_class exists
    if not frappe.db.exists("Asset", "ACC-ASS-UAT-CM-DBG"):
        doc = frappe.get_doc({
            "doctype": "Asset",
            "asset_name": "Debug Asset",
            "item_code": "VENT-PHL-V60",
            "company": frappe.defaults.get_global_default("company") or "Test Co",
            "purchase_date": frappe.utils.add_days(frappe.utils.nowdate(), -365),
            "gross_purchase_amount": 100_000_000,
            "asset_category": "Medical Equipment",
            "status": "Active",
            "location": "ICU",
        })
        doc.flags.ignore_links = True
        doc.flags.ignore_mandatory = True
        doc.insert(ignore_permissions=True)
        frappe.db.set_value("Asset", doc.name, "name", "ACC-ASS-UAT-CM-DBG")
        frappe.db.commit()

    try:
        doc = frappe.get_doc({
            "doctype": "Asset Repair",
            "asset_ref": "ACC-ASS-UAT-CM-DBG",
            "repair_type": "Corrective",
            "priority": "Urgent",
            "failure_description": "Debug test",
            "incident_report": "IR-DBG-001",
            "status": "Open",
            "risk_class": "Class III",
            "open_datetime": frappe.utils.now_datetime(),
        })
        doc.flags.ignore_links = True
        doc.flags.ignore_mandatory = True
        print("Before insert...")
        doc.insert(ignore_permissions=True)
        print("Insert OK:", doc.name)
        frappe.db.delete("Asset Repair", {"name": doc.name})
        frappe.db.commit()
    except Exception as e:
        print("Error:", e)
        traceback.print_exc()
