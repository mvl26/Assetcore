"""Quick audit of record counts for IMM-00/01/02/03."""
import frappe


def run():
    targets = [
        # IMM-00 foundation masters
        "AC Department", "AC Supplier", "AC Location", "AC UOM",
        "AC Asset Category", "AC Warehouse", "AC Spare Part",
        "IMM Device Model", "IMM Tech Spec", "IMM AVL Entry",
        "IMM SLA Policy",
        # Asset
        "AC Asset", "Asset Document",
        # IMM-01
        "IMM Needs Request", "IMM Procurement Plan",
        "Procurement Plan Line", "Needs Priority Scoring",
        # IMM-02
        "IMM Procurement Decision", "IMM Vendor Evaluation",
        "Vendor Eval Candidate", "Vendor Quotation Line", "AC Purchase",
        # IMM-03
        "Asset Commissioning", "Commissioning Checklist",
        "Asset QA Non Conformance",
        # Audit
        "Asset Lifecycle Event", "IMM Audit Trail",
    ]
    for dt in targets:
        try:
            if not frappe.db.exists("DocType", dt):
                print(f"{dt}: <MISSING>")
                continue
            c = frappe.db.count(dt)
            print(f"{dt}: {c}")
        except Exception as e:
            print(f"{dt}: ERR {e}")
