"""Check state before IMM-03 creation."""
import frappe


def run():
    frappe.set_user("Administrator")
    specs = frappe.db.sql(
        "SELECT name, source_plan, source_needs_request, device_model_ref FROM `tabIMM Tech Spec`",
        as_dict=True,
    )
    print("Tech Specs:")
    for ts in specs:
        print(f"  {ts['name']} plan={ts['source_plan']} model={ts['device_model_ref']}")

    suppliers = frappe.db.sql("SELECT name, supplier_name FROM `tabAC Supplier`", as_dict=True)
    print("Suppliers:")
    for s in suppliers:
        print(f"  {s['name']}: {s['supplier_name']}")

    ves = frappe.db.sql(
        "SELECT name, spec_ref, workflow_state FROM `tabIMM Vendor Evaluation`",
        as_dict=True,
    )
    print(f"Vendor Evaluations ({len(ves)}):")
    for ve in ves:
        print(f"  {ve['name']} spec={ve['spec_ref']} state={ve['workflow_state']}")
