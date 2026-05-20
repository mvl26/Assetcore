"""Inspect master data display values."""
import frappe


def run():
    print("=== AC Department ===")
    for d in frappe.get_all("AC Department", fields=["name", "department_name", "department_code"]):
        print(d)
    print("\n=== AC Location ===")
    for d in frappe.get_all("AC Location", fields=["name", "location_name"]):
        print(d)
    print("\n=== AC Asset Category ===")
    for d in frappe.get_all("AC Asset Category", fields=["name", "category_name"]):
        print(d)
    print("\n=== AC Supplier ===")
    for d in frappe.get_all("AC Supplier", fields=["name", "supplier_name"]):
        print(d)
    print("\n=== AC Asset (sample) ===")
    for d in frappe.get_all("AC Asset",
                            fields=["name", "asset_name", "department", "location", "asset_category", "supplier", "depreciation_method"],
                            limit=3):
        print(d)
    print("\n=== IMM Device Model ===")
    for d in frappe.get_all("IMM Device Model", fields=["name", "model_name", "manufacturer"]):
        print(d)
    print("\n=== IMM Tech Spec ===")
    for d in frappe.get_all("IMM Tech Spec", fields=["name", "spec_title", "workflow_state", "device_category"]):
        print(d)
    print("\n=== IMM Needs Request ===")
    for d in frappe.get_all("IMM Needs Request",
                            fields=["name", "title", "workflow_state", "department", "estimated_capex"]):
        print(d)
    print("\n=== IMM Procurement Plan ===")
    for d in frappe.get_all("IMM Procurement Plan",
                            fields=["name", "plan_title", "fiscal_year", "workflow_state"]):
        print(d)
    print("\n=== IMM Vendor Evaluation ===")
    for d in frappe.get_all("IMM Vendor Evaluation",
                            fields=["name", "evaluation_title", "workflow_state", "device_category"]):
        print(d)
    print("\n=== IMM Procurement Decision ===")
    for d in frappe.get_all("IMM Procurement Decision",
                            fields=["name", "decision_title", "workflow_state"]):
        print(d)
