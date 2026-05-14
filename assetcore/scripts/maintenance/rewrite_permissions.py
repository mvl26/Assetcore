#!/usr/bin/env python3
"""
Idempotent rewriter cho `permissions` block trong tất cả DocType JSON của AssetCore.

Áp dụng matrix role/permission đã được approve (xem CLAUDE conversation tháng 4/2026).
- Drop legacy role: HTM Technician, Biomed Engineer, Workshop Head, VP Block2,
  QA Risk Team, Tổ HC-QLCL, CMMS Admin, Workshop Manager, Clinical Head,
  Kho vật tư, IMM Manager.
- Áp 12 canonical IMM role theo category của DocType.
- Tôn trọng `is_submittable` và `istable` của DocType.
- Child tables (istable=1) không được set permissions trực tiếp — Frappe inherit từ parent.

Run: chạy local script (KHÔNG cần bench), nó chỉ rewrite JSON file.
  python3 assetcore/scripts/maintenance/rewrite_permissions.py
Sau đó: bench --site <site> migrate để Frappe sync permissions vào DB.
"""
from __future__ import annotations
import json
from pathlib import Path

# ── Permission letter codes ────────────────────────────────────────────────────
# R=read W=write C=create D=delete S=submit M=cancel A=amend
# Pr=print/email/share Ex=export/report
def _perm(code: str, is_submittable: bool = False) -> dict:
    flags = set(code)
    p = {
        "read":   1 if "R" in flags else 0,
        "write":  1 if "W" in flags else 0,
        "create": 1 if "C" in flags else 0,
        "delete": 1 if "D" in flags else 0,
        "report": 1 if "E" in flags else 0,
        "export": 1 if "E" in flags else 0,
        "print":  1 if "P" in flags else 0,
        "email":  1 if "P" in flags else 0,
        "share":  1 if "P" in flags else 0,
    }
    if is_submittable:
        p["submit"] = 1 if "S" in flags else 0
        p["cancel"] = 1 if "M" in flags else 0
        p["amend"]  = 1 if "A" in flags else 0
    return p

# ── Role permission matrix per category ───────────────────────────────────────
# Format: {role: "letter-code"}
# Letter code interpretation:
#   E = report+export, P = print+email+share, R/W/C/D/S/M/A as above

MATRIX = {
    "MASTER_REF": {
        "IMM System Admin":           "RWCDPE",
        "IMM Operations Manager":     "RWCPE",
        "IMM QA Officer":             "RPE",
        "IMM Auditor":                "RPE",
        "IMM Department Head":        "RPE",
        "IMM Deputy Department Head": "RPE",
        "IMM Workshop Lead":          "RPE",
        "IMM Biomed Technician":      "RPE",
        "IMM Technician":             "RPE",
        "IMM Storekeeper":            "RPE",
        "IMM Document Officer":       "RPE",
        "IMM Clinical User":          "R",
        "Vendor Engineer":            "R",
    },
    "ASSET_CORE": {
        "IMM System Admin":           "RWCDSMAPE",
        "IMM Operations Manager":     "RWCSMAPE",
        "IMM QA Officer":             "RPE",
        "IMM Auditor":                "RPE",
        "IMM Department Head":        "RWCSPE",
        "IMM Deputy Department Head": "RWSPE",
        "IMM Workshop Lead":          "RWSPE",
        "IMM Biomed Technician":      "RWPE",
        "IMM Technician":             "RPE",
        "IMM Storekeeper":            "RPE",
        "IMM Document Officer":       "RPE",
        "IMM Clinical User":          "R",
        "Vendor Engineer":            "R",
    },
    "STOCK": {
        "IMM System Admin":           "RWCDSMAPE",
        "IMM Operations Manager":     "RWCSMAPE",
        "IMM QA Officer":             "RPE",
        "IMM Auditor":                "RPE",
        "IMM Department Head":        "RPE",
        "IMM Deputy Department Head": "RPE",
        "IMM Workshop Lead":          "RWSPE",
        "IMM Biomed Technician":      "RPE",
        "IMM Technician":             "RPE",
        "IMM Storekeeper":            "RWCDSMAPE",
        "IMM Document Officer":       "RPE",
        "Vendor Engineer":            "R",
    },
    "WORK_ORDER": {
        "IMM System Admin":           "RWCDSMAPE",
        "IMM Operations Manager":     "RWCSMAPE",
        "IMM QA Officer":             "RPE",
        "IMM Auditor":                "RPE",
        "IMM Department Head":        "RWSPE",
        "IMM Deputy Department Head": "RWSPE",
        "IMM Workshop Lead":          "RWCSMAPE",
        "IMM Biomed Technician":      "RWCSPE",
        "IMM Technician":             "RWCSPE",
        "IMM Storekeeper":            "RPE",
        "IMM Document Officer":       "RPE",
        "Vendor Engineer":            "RWCSPE",  # Vendor thực hiện WO theo hợp đồng
    },
    "INCIDENT": {  # Incident Report — clinical may create
        "IMM System Admin":           "RWCDSMAPE",
        "IMM Operations Manager":     "RWCSMAPE",
        "IMM QA Officer":             "RWCSPE",
        "IMM Auditor":                "RPE",
        "IMM Department Head":        "RWSPE",
        "IMM Deputy Department Head": "RWSPE",
        "IMM Workshop Lead":          "RWCSPE",
        "IMM Biomed Technician":      "RWCSPE",
        "IMM Technician":             "RWCSPE",
        "IMM Storekeeper":            "R",
        "IMM Document Officer":       "RPE",
        "IMM Clinical User":          "RWCP",
        "Vendor Engineer":            "RP",   # vendor xem được sự cố liên quan
    },
    "QMS": {
        "IMM System Admin":           "RWCDSMAPE",
        "IMM Operations Manager":     "RWSPE",
        "IMM QA Officer":             "RWCDSMAPE",
        "IMM Auditor":                "RPE",
        "IMM Department Head":        "RPE",
        "IMM Deputy Department Head": "RPE",
        "IMM Workshop Lead":          "RPE",
        "IMM Biomed Technician":      "RPE",
        "IMM Technician":             "RPE",
        "IMM Storekeeper":            "R",
        "IMM Document Officer":       "RWCSPE",
        "IMM Clinical User":          "R",
        # Vendor Engineer KHÔNG được vào QMS (NCR/CAPA/RCA) — đó là nội bộ
    },
    "AUDIT": {  # IMM Audit Trail — read-only, ai có quyền xem audit thôi
        "IMM System Admin":           "RPE",
        "IMM QA Officer":             "RPE",
        "IMM Auditor":                "RPE",
    },
}

# ── DocType → category mapping ────────────────────────────────────────────────
CATEGORY = {
    # MASTER_REF
    "ac_asset_category":    "MASTER_REF",
    "ac_department":        "MASTER_REF",
    "ac_location":          "MASTER_REF",
    "ac_supplier":          "MASTER_REF",
    "ac_uom":               "MASTER_REF",
    "ac_warehouse":         "MASTER_REF",
    "imm_device_model":     "MASTER_REF",
    "required_document_type": "MASTER_REF",
    # ASSET_CORE
    "ac_asset":                       "ASSET_CORE",
    "asset_lifecycle_event":          "ASSET_CORE",
    "asset_transfer":                 "ASSET_CORE",
    "service_contract":               "ASSET_CORE",
    "ac_asset_depreciation_schedule": "ASSET_CORE",
    # STOCK
    "ac_spare_part":       "STOCK",
    "ac_spare_part_stock": "STOCK",
    "ac_stock_movement":   "STOCK",
    "ac_purchase":         "STOCK",
    # WORK_ORDER
    "pm_work_order":            "WORK_ORDER",
    "pm_schedule":              "WORK_ORDER",
    "pm_task_log":              "WORK_ORDER",
    "asset_repair":             "WORK_ORDER",
    "imm_asset_calibration":    "WORK_ORDER",
    "imm_calibration_schedule": "WORK_ORDER",
    "firmware_change_request":  "WORK_ORDER",
    "ac_asset_downtime_log":    "WORK_ORDER",
    "pm_checklist_template":    "WORK_ORDER",
    # INCIDENT
    "incident_report": "INCIDENT",
    # QMS
    "imm_capa_record":          "QMS",
    "imm_rca_record":           "QMS",
    "asset_qa_non_conformance": "QMS",
    "asset_commissioning":      "QMS",
    "document_request":         "QMS",
    "asset_document":           "QMS",
    "imm_sla_policy":           "QMS",
    "expiry_alert_log":         "QMS",
    # AUDIT
    "imm_audit_trail": "AUDIT",
}

ROOT = Path(__file__).resolve().parents[2] / "assetcore" / "doctype"


def build_permissions(category: str, is_submittable: bool) -> list[dict]:
    role_map = MATRIX[category]
    return [
        {"role": role, **_perm(code, is_submittable)}
        for role, code in role_map.items()
    ]


def main() -> int:
    if not ROOT.exists():
        print(f"❌ DocType root not found: {ROOT}")
        return 1

    changed, skipped, child_skipped = [], [], []
    for jf in sorted(ROOT.glob("*/*.json")):
        # Chỉ xử lý file <doctype>/<doctype>.json (DocType definition)
        if jf.stem != jf.parent.name:
            continue
        with jf.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        if data.get("doctype") != "DocType":
            continue

        dt_dir = jf.parent.name

        # Child tables: bỏ permissions, Frappe inherit từ parent
        if data.get("istable"):
            if data.get("permissions"):
                data["permissions"] = []
                with jf.open("w", encoding="utf-8") as fh:
                    json.dump(data, fh, indent=1, ensure_ascii=False)
                    fh.write("\n")
                child_skipped.append(f"{dt_dir} (istable, cleared permissions)")
            else:
                child_skipped.append(f"{dt_dir} (istable, no perms)")
            continue

        cat = CATEGORY.get(dt_dir)
        if not cat:
            skipped.append(f"{dt_dir} (no category mapping)")
            continue

        is_sub = bool(data.get("is_submittable"))
        new_perms = build_permissions(cat, is_sub)

        # Sort tabs: keep DocType-defined ordering stable by role name
        old = data.get("permissions") or []
        if old == new_perms:
            skipped.append(f"{dt_dir} (already up to date)")
            continue

        data["permissions"] = new_perms
        with jf.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=1, ensure_ascii=False)
            fh.write("\n")
        changed.append(f"{dt_dir} [{cat}]" + (" submittable" if is_sub else ""))

    print(f"✅ Updated {len(changed)} DocType(s):")
    for c in changed:
        print(f"  • {c}")
    if child_skipped:
        print(f"\n⏭  Child tables ({len(child_skipped)}):")
        for c in child_skipped:
            print(f"  • {c}")
    if skipped:
        print(f"\n⚠️  Skipped ({len(skipped)}):")
        for s in skipped:
            print(f"  • {s}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
