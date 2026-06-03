# Copyright (c) 2026, AssetCore Team
"""READ-ONLY scanner: list test-garbage candidates across ALL app DocTypes +
resolve the FK-closure allowlist of the 3 genuine demo assets.

NEVER writes. Use to produce the audit list BEFORE any purge.

    bench --site miyano execute assetcore.scripts.maintenance.scan_test_garbage.run
"""
from __future__ import annotations

import re

import frappe

# 3 genuine demo asset codes — the ONLY real AC Assets (real VI device names).
REAL_ASSET_CODES = ("TS-2025-USG-001", "TS-2025-VEN-001", "TS-2025-CT-001")
# 3 genuine demo incidents.
REAL_INCIDENTS = ("IR-2026-0131", "IR-2026-0132", "IR-2026-0168")

# Test-marker regex applied to NAME + key business label fields.
MARKERS = re.compile(
    r"(_Test|^Test |\bTest |_TEST|TEST-|TEST_|pytest|_pytest|UAT-|Gate Test|"
    r"Gate Cron|Gate5|Gate ?\d|_DBG|_tmp|probe|Sample|Demo Test|Xmod|_SCSupplier|"
    r"_TestSC|SLA Test|_Test RCA|FK-INTEG|MBT9|EPQ7\b|CXD ?\d)",
    re.IGNORECASE,
)
# IMM06 special tag from the user's example: "_Test Model IMM06".
IMM06_TAG = re.compile(r"IMM06\b", re.IGNORECASE)

# Per-doctype label fields to test for markers (besides `name`).
LABEL_FIELDS = {
    "AC Asset": ["asset_name", "serial_no"],
    "AC Asset Category": ["category_name"],
    "IMM Device Model": ["model_name", "model_code", "model_number"],
    "AC Supplier": ["supplier_name"],
    "AC Location": ["location_name"],
    "AC Department": ["department_name", "department_code"],
    "AC Warehouse": ["warehouse_name"],
    "AC Spare Part": ["part_name", "part_number"],
    "Service Contract": ["contract_name", "contract_number"],
    "Incident Report": ["description", "title"],
    "IMM Training Program": ["program_name", "program_code"],
    "IMM Training Session": ["location"],
    "IMM User Competency": [],
    "IMM Trainer": ["trainer_name"],
    "PM Work Order": ["title"],
    "Asset Repair": ["title", "problem_description"],
    "IMM Spare Allocation": ["purpose"],
    "AC Stock Movement": ["remarks"],
    "IMM CAPA Record": ["title", "description"],
    "IMM RCA Record": ["title"],
    "IMM Calibration Schedule": [],
    "IMM Asset Calibration": [],
    "IMM Needs Request": ["title", "description"],
    "IMM Procurement Plan": ["plan_name"],
    "AC Purchase": ["purchase_name"],
    "Asset Commissioning": ["asset_description"],
    "Asset Document": ["doc_number", "notes"],
    "AC Authorized Technician": ["technician_name"],
    "IMM Tech Spec": ["spec_name"],
    "IMM Internal Audit": ["audit_title"],
    "IMM Supplier Audit": [],
    "IMM Vendor Evaluation": [],
    "IMM Management Review": ["title"],
    "IMM Compliance Scorecard": [],
    "IMM Spare Batch": ["batch_number"],
}


def _real_asset_names() -> list[str]:
    rows = frappe.get_all(
        "AC Asset", filters={"asset_name": ["like", "%"]},
        fields=["name", "asset_name"], ignore_permissions=True,
    )
    real = [r["name"] for r in rows if r["name"] in REAL_ASSET_CODES]
    return real


def _allowlist_fk() -> dict[str, set[str]]:
    """Resolve the FK closure of the 3 real assets: their model/supplier/
    location/department/category — these masters are REAL, never purge them."""
    allow: dict[str, set[str]] = {}
    real = _real_asset_names()
    if not real:
        return allow
    fields = ["device_model", "supplier", "location", "department",
              "asset_category", "category"]
    cols = [f for f in fields if frappe.db.has_column("AC Asset", f)]
    rows = frappe.get_all("AC Asset", filters={"name": ["in", real]},
                          fields=["name"] + cols, ignore_permissions=True)
    fk_map = {
        "device_model": "IMM Device Model",
        "supplier": "AC Supplier",
        "location": "AC Location",
        "department": "AC Department",
        "asset_category": "AC Asset Category",
        "category": "AC Asset Category",
    }
    for r in rows:
        for col, dt in fk_map.items():
            v = r.get(col)
            if v:
                allow.setdefault(dt, set()).add(v)
    allow["AC Asset"] = set(real)
    allow["Incident Report"] = set(REAL_INCIDENTS)
    return allow


def _scan_doctype(dt: str, label_fields: list[str], allow: set[str]) -> list[tuple]:
    if not frappe.db.table_exists(dt):
        return []
    cols = ["name"] + [f for f in label_fields if frappe.db.has_column(dt, f)]
    rows = frappe.get_all(dt, fields=cols, ignore_permissions=True, limit=0)
    hits = []
    for r in rows:
        if r["name"] in allow:
            continue
        blob = " | ".join(str(r.get(c) or "") for c in cols)
        if MARKERS.search(blob) or IMM06_TAG.search(blob):
            hits.append((r["name"], blob[:90]))
    return hits


def run() -> None:
    frappe.set_user("Administrator")
    allow = _allowlist_fk()
    print("=== REAL-FK ALLOWLIST (never purge) ===")
    for dt, names in sorted(allow.items()):
        print(f"   {dt:24} -> {sorted(names)}")

    print("\n=== TEST-GARBAGE CANDIDATES PER DOCTYPE ===")
    total = 0
    for dt, lbls in LABEL_FIELDS.items():
        hits = _scan_doctype(dt, lbls, allow.get(dt, set()))
        cnt = frappe.db.count(dt) if frappe.db.table_exists(dt) else 0
        if hits:
            total += len(hits)
            print(f"\n[{dt}] total={cnt}  garbage={len(hits)}")
            for name, blob in hits[:12]:
                print(f"    RAC  {name:28} | {blob}")
            if len(hits) > 12:
                print(f"    ... +{len(hits) - 12} more")
        else:
            print(f"[{dt}] total={cnt}  garbage=0")
    print(f"\n=== TOTAL GARBAGE CANDIDATES = {total} ===")
