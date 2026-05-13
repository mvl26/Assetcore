import frappe, json

frappe.set_user("Administrator")

from assetcore.api import imm15, imm16

ok, err = [], []

def run(label, fn, *args):
    try:
        r = fn(*args)
        cnt = len(r["items"]) if isinstance(r, dict) and "items" in r else "ok"
        ok.append(f"OK  {label}: {cnt} items")
    except Exception as e:
        err.append(f"ERR {label}: {e}")

run("imm15.list_spare_parts",      imm15.list_spare_parts,      "{}", 1, 5)
run("imm15.list_allocations",      imm15.list_allocations,      "{}", 1, 5)
run("imm15.list_cycle_counts",     imm15.list_cycle_counts,     "{}", 1, 5)
run("imm15.dashboard_kpis",        imm15.dashboard_kpis)
run("imm15.get_watchlist",         imm15.get_watchlist,         "{}")
run("imm16.list_findings",         imm16.list_findings,         "{}", 1, 5)
run("imm16.list_capa_records",     imm16.list_capa_records,     "{}", 1, 5)
run("imm16.list_internal_audits",  imm16.list_internal_audits,  "{}", 1, 5)
run("imm16.dashboard_kpis",        imm16.dashboard_kpis)

print(json.dumps({"ok": ok, "err": err}))
