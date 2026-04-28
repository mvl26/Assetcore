"""Helper: print required fields for key DocTypes."""
import frappe


def run():
    for dt in ["AC Location", "AC Department", "AC Asset Category", "AC Supplier",
               "IMM Device Model", "IMM SLA Policy", "Incident Report", "AC Asset"]:
        meta = frappe.get_meta(dt)
        reqd = [(f.fieldname, f.fieldtype, f.options or "") for f in meta.fields
                if f.reqd and f.fieldname != "naming_series"]
        print(f"\n=== {dt} ===")
        for fn, ft, opts in reqd:
            print(f"  {fn}: {ft} {opts[:60]}")
