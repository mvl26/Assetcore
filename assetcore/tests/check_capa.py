"""Debug helper to check CAPA/Incident state."""
import frappe


def run():
    print("\n=== All CAPAs ===")
    for c in frappe.get_all("IMM CAPA Record",
                             fields=["name", "source_type", "source_ref", "severity", "status", "docstatus"],
                             order_by="creation desc", limit=10):
        print(f"  {c}")

    print("\n=== Incidents ===")
    for i in frappe.get_all("Incident Report",
                             fields=["name", "severity", "docstatus", "status"],
                             order_by="creation desc", limit=10):
        print(f"  {i}")

    # Resubmit a draft Critical incident if any
    drafts = frappe.get_all("Incident Report",
                             filters={"severity": "Critical", "docstatus": 0},
                             pluck="name")
    print(f"\nCritical drafts to submit: {drafts}")
    for name in drafts:
        try:
            doc = frappe.get_doc("Incident Report", name)
            doc.submit()
            print(f"  submitted {name}")
        except Exception as e:
            print(f"  failed {name}: {e}")

    print("\n=== CAPAs after submit ===")
    for c in frappe.get_all("IMM CAPA Record",
                             filters={"source_type": "Incident Report"},
                             fields=["name", "source_ref", "severity", "status"],
                             order_by="creation desc", limit=10):
        print(f"  {c}")

    frappe.db.commit()
