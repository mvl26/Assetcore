"""
Purge all test/demo data.
Run: bench --site miyano execute assetcore.scripts.purge_test_data.run
"""
import frappe


def _sql_delete(table: str) -> None:
    try:
        count = frappe.db.sql(f"SELECT COUNT(*) FROM `{table}`")[0][0]
        if count:
            frappe.db.sql(f"DELETE FROM `{table}`")
            frappe.db.commit()
            print(f"  SQL {count} × {table}")
    except Exception as e:
        print(f"  SKIP {table}: {e}")


def _delete_doc(doctype: str, table: str | None = None) -> None:
    tbl = table or f"tab{doctype}"
    try:
        names = [r[0] for r in frappe.db.sql(f"SELECT name FROM `{tbl}`")]
    except Exception:
        return
    if not names:
        return
    deleted = 0
    for name in names:
        try:
            doc = frappe.get_doc(doctype, name)
            if doc.docstatus == 1:
                doc.flags.ignore_permissions = True
                doc.flags.ignore_links = True
                doc.cancel()
                frappe.db.commit()
            frappe.delete_doc(
                doctype, name, force=True,
                ignore_permissions=True, ignore_missing=True, delete_permanently=True,
            )
            frappe.db.commit()
            deleted += 1
        except Exception as e:
            # fallback: raw SQL
            try:
                frappe.db.sql(f"DELETE FROM `{tbl}` WHERE name=%s", name)
                frappe.db.commit()
                deleted += 1
            except Exception as e2:
                print(f"  WARN {doctype} {name}: {e2}")
    if deleted:
        print(f"  Deleted {deleted} × {doctype}")


def run():
    frappe.set_user("Administrator")
    print("=== Purging AssetCore test data ===\n")

    # 1. Trails — SQL bypass
    print("-- Trails --")
    _sql_delete("tabIMM Audit Trail")
    _sql_delete("tabAsset Lifecycle Event")
    _sql_delete("tabAC Asset Downtime Log")

    # 2. IMM-12
    print("-- IMM-12 --")
    _sql_delete("tabIMM CAPA Action Step")
    _delete_doc("IMM CAPA Record")
    _sql_delete("tabIMM RCA Five Why Step")
    _sql_delete("tabIMM RCA Related Incident")
    _delete_doc("IMM RCA Record")
    _delete_doc("Incident Report")

    # 3. IMM-11 — SQL cho submitted
    print("-- IMM-11 --")
    _sql_delete("tabIMM Calibration Measurement")
    _sql_delete("tabIMM Calibration Schedule")
    _sql_delete("tabIMM Asset Calibration")

    # 4. IMM-09 Repair
    print("-- IMM-09 --")
    _sql_delete("tabRepair Checklist")
    _sql_delete("tabSpare Parts Used")
    _sql_delete("tabAsset QA Non Conformance")
    _sql_delete("tabAsset Repair")

    # 5. IMM-08 PM — correct table names
    print("-- IMM-08 --")
    _sql_delete("tabPM Task Log")
    _sql_delete("tabPM Checklist Result")
    _sql_delete("tabPM Work Order")
    _sql_delete("tabPM Schedule")

    # 6. IMM-15/16 Inventory
    print("-- IMM-15/16 --")
    _sql_delete("tabAC Stock Movement Item")
    _sql_delete("tabAC Stock Movement")
    _sql_delete("tabIMM Spare Allocation Item")
    _sql_delete("tabIMM Spare Allocation")
    _sql_delete("tabIMM Device Spare Part")
    _sql_delete("tabIMM Spare Alternative")
    _sql_delete("tabIMM Spare Forecast Item")
    _sql_delete("tabIMM Spare Part Forecast")
    _sql_delete("tabIMM Critical Spare Watchlist")
    _sql_delete("tabIMM Spare Batch")
    _sql_delete("tabAC Spare Part Stock")
    _sql_delete("tabAC Spare Part")

    # 7. IMM-06 Training
    print("-- IMM-06 --")
    _sql_delete("tabIMM Training Participant")
    _sql_delete("tabIMM Training Session")
    _sql_delete("tabIMM Training Program")

    # 8. IMM-04/05 Commissioning & Purchase
    print("-- IMM-04/05 --")
    _sql_delete("tabCommissioning Checklist")
    _sql_delete("tabCommissioning Document Record")
    _sql_delete("tabAsset Document")
    _sql_delete("tabAsset Commissioning")
    _sql_delete("tabAC Purchase Device Item")
    _sql_delete("tabAC Purchase Item")
    _sql_delete("tabAC Purchase")

    # 9. Asset Transfer
    print("-- Asset Transfer --")
    _sql_delete("tabAsset Transfer")

    # 10. IMM-02/03 Vendor chain
    print("-- IMM-02/03 --")
    _sql_delete("tabIMM Vendor Scorecard")
    _sql_delete("tabVendor Eval Candidate")
    _sql_delete("tabVendor Eval Criterion")
    _sql_delete("tabVendor Quotation Line")
    _sql_delete("tabIMM Vendor Evaluation")
    _sql_delete("tabIMM Procurement Decision")
    _sql_delete("tabIMM Supplier Audit")
    _sql_delete("tabVendor Cert")
    _sql_delete("tabIMM AVL Entry")
    _sql_delete("tabVendor AVL")
    _sql_delete("tabIMM Vendor Profile")

    # 11. IMM-01 Planning
    print("-- IMM-01 --")
    _sql_delete("tabIMM Lock-in Risk Assessment")
    _sql_delete("tabIMM Market Benchmark")
    _sql_delete("tabIMM Tech Spec")
    _sql_delete("tabIMM Procurement Plan")
    _sql_delete("tabIMM Needs Request")

    # 12. QMS / Compliance / Internal Audit
    print("-- QMS --")
    _sql_delete("tabIMM Audit Checklist Item")
    _sql_delete("tabIMM Internal Audit")
    _sql_delete("tabAudit Finding")
    _sql_delete("tabIMM Compliance Finding")
    _sql_delete("tabIMM Compliance Scorecard")
    _sql_delete("tabIMM Scorecard Department Row")
    _sql_delete("tabIMM Scorecard Module Row")
    _sql_delete("tabIMM Gap Detail Row")
    _sql_delete("tabIMM Compliance Rule")
    _sql_delete("tabIMM MR Attendee")
    _sql_delete("tabIMM MR Output Action")
    _sql_delete("tabIMM Management Review")

    # 13. Competency
    print("-- Competency --")
    _sql_delete("tabIMM Competency Alert Log")
    _sql_delete("tabIMM Competency Gap Report")
    _sql_delete("tabIMM User Competency")

    # 14. Service Contracts
    print("-- Service Contracts --")
    _sql_delete("tabService Contract Asset")
    _sql_delete("tabService Contract")

    # 15. Cycle Count
    print("-- Cycle Count --")
    _sql_delete("tabIMM Cycle Count Item")
    _sql_delete("tabIMM Stock Cycle Count")

    # 16. Depreciation
    print("-- Depreciation --")
    _sql_delete("tabAC Asset Depreciation Schedule")

    # 17. Core asset
    print("-- AC Asset --")
    _sql_delete("tabAC Asset")

    # 18. Reference / master data
    print("-- Reference data --")
    _sql_delete("tabIMM Device Model")
    _sql_delete("tabAC Supplier")
    _sql_delete("tabAC Asset Category")
    _sql_delete("tabAC Location")
    _sql_delete("tabAC Department")

    frappe.db.commit()
    print("\n=== Remaining counts ===")
    for tbl in [
        "tabAC Asset", "tabAC Supplier", "tabAC Location", "tabAC Department",
        "tabAC Asset Category", "tabIMM Device Model", "tabIMM Needs Request",
        "tabIMM Procurement Plan", "tabAsset Repair", "tabIMM Asset Calibration",
        "tabIncident Report", "tabIMM CAPA Record", "tabAC Spare Part",
        "tabIMM Audit Trail", "tabAsset Lifecycle Event",
        "tabPM Work Order", "tabPM Schedule",
    ]:
        try:
            c = frappe.db.sql(f"SELECT COUNT(*) FROM `{tbl}`")[0][0]
            print(f"  {tbl}: {c}")
        except Exception:
            pass
    print("\n=== Purge complete ===")
