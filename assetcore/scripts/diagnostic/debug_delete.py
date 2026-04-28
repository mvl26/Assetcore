import frappe
import traceback


def run():
    frappe.set_user("Administrator")
    # Pick the most recent AT
    ats = frappe.get_all("Asset Transfer", order_by="creation desc", limit=1, pluck="name")
    if not ats:
        print("No AT to test")
        return
    name = ats[0]
    print(f"Testing delete on: {name}")
    try:
        doc = frappe.get_doc("Asset Transfer", name)
        print(f"  docstatus={doc.docstatus}")
        if doc.docstatus == 1:
            doc.cancel()
            print(f"  cancelled, new docstatus={doc.docstatus}")
        frappe.delete_doc("Asset Transfer", name, ignore_permissions=False)
        print(f"  deleted OK")
        frappe.db.commit()
    except Exception as e:
        print(f"  FAILED: {type(e).__name__}: {e}")
        traceback.print_exc()
