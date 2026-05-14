"""UAT script: tests full CRUD for Asset Transfer and Service Contract via whitelisted API."""
import frappe
from assetcore.api.imm00 import (
    create_service_contract, list_service_contracts, get_service_contract,
    update_service_contract, submit_service_contract, delete_service_contract,
    create_transfer, list_transfers, get_transfer, delete_transfer,
)


def _unwrap(r):
    """API returns _ok/_err which is dict with 'success' and 'data'/'error'."""
    if isinstance(r, dict):
        return r
    return {"raw": r}


def run():
    frappe.set_user("Administrator")
    results = []

    # ===== Setup: ensure sample data =====
    # Location
    locs = frappe.get_all("AC Location", limit=2, fields=["name"])
    if not locs:
        for i in range(2):
            frappe.get_doc({
                "doctype": "AC Location", "location_name": f"UAT Location {i+1}",
                "location_type": "Room", "is_active": 1,
            }).insert(ignore_permissions=True)
        locs = frappe.get_all("AC Location", limit=2, fields=["name"])
    print(f"[SETUP] Locations: {[l.name for l in locs]}")

    # Category
    cats = frappe.get_all("AC Asset Category", limit=1, fields=["name"])
    if not cats:
        frappe.get_doc({
            "doctype": "AC Asset Category", "category_name": "UAT Category",
        }).insert(ignore_permissions=True)
        cats = frappe.get_all("AC Asset Category", limit=1, fields=["name"])
    cat_name = cats[0].name
    print(f"[SETUP] Category: {cat_name}")

    # Asset
    assets = frappe.get_all("AC Asset", limit=1, fields=["name", "location", "department"])
    if not assets:
        a = frappe.get_doc({
            "doctype": "AC Asset",
            "asset_name": "UAT Test Device",
            "asset_code": "UAT-001",
            "asset_category": cat_name,
            "status": "Active",
            "lifecycle_status": "Active",
            "location": locs[0].name,
        }).insert(ignore_permissions=True)
        a.submit()
        assets = frappe.get_all("AC Asset", limit=1, fields=["name", "location", "department"])
    asset = assets[0]
    print(f"[SETUP] Using asset: {asset.name} at location={asset.location}")

    suppliers = frappe.get_all("AC Supplier", limit=1, fields=["name"])
    if not suppliers:
        print("[SKIP] No AC Supplier — creating sample")
        sup = frappe.get_doc({
            "doctype": "AC Supplier", "supplier_name": "UAT Supplier Co.",
            "supplier_type": "Manufacturer", "country": "VN",
        }).insert(ignore_permissions=True)
        supplier_name = sup.name
    else:
        supplier_name = suppliers[0].name
    print(f"[SETUP] Using supplier: {supplier_name}")

    # Pick a to_location different from current asset location
    to_loc = next((l.name for l in locs if l.name != asset.location), locs[0].name)
    print(f"[SETUP] Using to_location: {to_loc}")

    # ================================================================
    # Service Contract — CRUD
    # ================================================================
    print("\n=== Service Contract CRUD ===")

    # CREATE
    frappe.local.form_dict = frappe._dict({
        "contract_title": "UAT PM Contract 2026",
        "supplier": supplier_name,
        "contract_type": "Preventive Maintenance",
        "contract_start": "2026-04-18",
        "contract_end": "2027-04-18",
        "contract_value": 50000000,
        "sla_response_hours": 24,
    })
    r = _unwrap(create_service_contract())
    print(f"[CREATE SC] success={r.get('success')} data={r.get('data')}")
    sc_name = (r.get("data") or {}).get("name")
    assert sc_name, f"Create failed: {r}"
    results.append(("SC CREATE", True, sc_name))

    # LIST
    r = _unwrap(list_service_contracts(page=1, page_size=5))
    total = (r.get("data") or {}).get("pagination", {}).get("total", 0)
    print(f"[LIST SC] total={total}")
    results.append(("SC LIST", total >= 1, f"total={total}"))

    # GET
    r = _unwrap(get_service_contract(sc_name))
    title = (r.get("data") or {}).get("contract_title")
    print(f"[GET SC] title={title}")
    results.append(("SC GET", title == "UAT PM Contract 2026", title))

    # UPDATE (draft)
    frappe.local.form_dict = frappe._dict({"contract_value": 60000000})
    r = _unwrap(update_service_contract(sc_name))
    print(f"[UPDATE SC] success={r.get('success')}")
    r2 = _unwrap(get_service_contract(sc_name))
    new_val = (r2.get("data") or {}).get("contract_value")
    print(f"[UPDATE SC] new value={new_val}")
    results.append(("SC UPDATE", float(new_val) == 60000000.0, f"value={new_val}"))

    # SUBMIT
    r = _unwrap(submit_service_contract(sc_name))
    print(f"[SUBMIT SC] success={r.get('success')} data={r.get('data')}")
    results.append(("SC SUBMIT", r.get("success") is True, str(r.get('data'))))

    # UPDATE after submit — should fail
    frappe.local.form_dict = frappe._dict({"contract_value": 999})
    r = _unwrap(update_service_contract(sc_name))
    print(f"[UPDATE after SUBMIT] success={r.get('success')} (expected False)")
    results.append(("SC UPDATE-blocked", r.get("success") is False, r.get("error", "")))

    # DELETE (cancel + delete)
    r = _unwrap(delete_service_contract(sc_name))
    print(f"[DELETE SC] success={r.get('success')} data={r.get('data')}")
    results.append(("SC DELETE", r.get("success") is True, str(r.get('data'))))

    exists = frappe.db.exists("Service Contract", sc_name)
    results.append(("SC DELETE verified", not exists, f"exists={exists}"))

    # ================================================================
    # Asset Transfer — Create/List/Get/Delete
    # ================================================================
    print("\n=== Asset Transfer CRUD ===")

    # CREATE (auto-submits)
    frappe.local.form_dict = frappe._dict({
        "asset": asset.name,
        "transfer_date": "2026-04-18",
        "transfer_type": "Internal",
        "to_location": to_loc,
        "reason": "UAT test transfer",
    })
    r = _unwrap(create_transfer())
    print(f"[CREATE AT] success={r.get('success')} data={r.get('data')}")
    at_name = (r.get("data") or {}).get("name")
    assert at_name, f"Create failed: {r}"
    results.append(("AT CREATE", True, at_name))

    # Verify asset location updated (BR: on_submit must transfer)
    new_loc = frappe.db.get_value("AC Asset", asset.name, "location")
    print(f"[AT effect] asset.location={new_loc} (was {asset.location}, target {to_loc})")
    results.append(("AT applies location", new_loc == to_loc, f"location={new_loc}"))

    # Verify lifecycle event created
    le = frappe.db.exists("Asset Lifecycle Event", {
        "root_record": at_name, "event_type": "transferred",
    })
    print(f"[AT lifecycle event] {le}")
    results.append(("AT lifecycle event", bool(le), str(le)))

    # Verify audit trail entry
    au = frappe.db.exists("IMM Audit Trail", {
        "ref_name": at_name, "event_type": "Transfer",
    })
    print(f"[AT audit trail] {au}")
    results.append(("AT audit trail", bool(au), str(au)))

    # LIST
    r = _unwrap(list_transfers(asset=asset.name, page=1, page_size=5))
    total = (r.get("data") or {}).get("pagination", {}).get("total", 0)
    print(f"[LIST AT] total={total}")
    results.append(("AT LIST", total >= 1, f"total={total}"))

    # GET
    r = _unwrap(get_transfer(at_name))
    reason = (r.get("data") or {}).get("reason")
    print(f"[GET AT] reason={reason}")
    results.append(("AT GET", reason == "UAT test transfer", reason))

    # DELETE (auto-submitted → cancel semantics; audit preserved per BR-00-04)
    r = _unwrap(delete_transfer(at_name))
    print(f"[DELETE AT] success={r.get('success')} data={r.get('data')}")
    results.append(("AT CANCEL", r.get("success") is True, str(r.get('data'))))

    docstatus = frappe.db.get_value("Asset Transfer", at_name, "docstatus")
    print(f"[AT docstatus after delete] {docstatus} (expect 2=Cancelled)")
    results.append(("AT CANCEL verified", docstatus == 2, f"docstatus={docstatus}"))

    # ================================================================
    # Report
    # ================================================================
    print("\n" + "=" * 60)
    print("UAT SUMMARY")
    print("=" * 60)
    for label, ok, detail in results:
        mark = "[PASS]" if ok else "[FAIL]"
        print(f"{mark} {label:28s} — {detail}")
    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)}/{len(results)} passed")
    return len(failed) == 0
