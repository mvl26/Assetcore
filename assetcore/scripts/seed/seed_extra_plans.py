"""Seed 2 extra Procurement Plans so list has 3 records (per assetcore-test R-2)."""
import frappe


def run():
    plans = [
        {
            "plan_year": 2026,
            "plan_period": "Q3",
            "budget_envelope": 8500000000,
            "workflow_state": "Draft",
        },
        {
            "plan_year": 2027,
            "plan_period": "Annual",
            "budget_envelope": 35000000000,
            "workflow_state": "Draft",
        },
    ]
    for p in plans:
        existing = frappe.db.exists("IMM Procurement Plan", {
            "plan_year": p["plan_year"], "plan_period": p["plan_period"]
        })
        if existing:
            print(f"exists: year={p['plan_year']} period={p['plan_period']} -> {existing}")
            continue
        doc = frappe.get_doc({"doctype": "IMM Procurement Plan", **p})
        doc.insert(ignore_permissions=True)
        print(f"created: {doc.name} ({p['plan_period']}/{p['plan_year']})")
    frappe.db.commit()
    print("DONE")
