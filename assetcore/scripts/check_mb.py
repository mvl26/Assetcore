"""Check Market Benchmark and Tech Spec records."""
import frappe


def run():
    frappe.set_user("Administrator")
    mbs = frappe.db.sql("SELECT name, spec_ref, workflow_state FROM `tabIMM Market Benchmark`", as_dict=True)
    print(f"Market Benchmarks ({len(mbs)}):")
    for mb in mbs:
        print(f"  {mb['name']} → spec_ref={mb['spec_ref']} state={mb['workflow_state']}")

    specs = frappe.db.sql("SELECT name, workflow_state, benchmark_ref FROM `tabIMM Tech Spec`", as_dict=True)
    print(f"\nTech Specs ({len(specs)}):")
    for ts in specs:
        print(f"  {ts['name']} → state={ts['workflow_state']} benchmark_ref={ts['benchmark_ref']}")
