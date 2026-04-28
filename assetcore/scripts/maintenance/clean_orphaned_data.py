# Copyright (c) 2026, AssetCore Team
"""
clean_orphaned_data.py — Garbage Collector: dọn dẹp dữ liệu mồ côi (orphaned records).

"Mồ côi" = bản ghi có link đến AC Asset không còn tồn tại trong hệ thống.

Phạm vi quét:
  ┌──────────────────────────────────┬───────────────┬───────────┐
  │ DocType                          │ Field         │ Hành động │
  ├──────────────────────────────────┼───────────────┼───────────┤
  │ PM Work Order                    │ asset_ref     │ xóa       │
  │ PM Schedule                      │ asset_ref     │ xóa       │
  │ IMM Asset Calibration            │ asset         │ xóa       │
  │ IMM Calibration Schedule         │ asset         │ xóa       │
  │ Asset Transfer                   │ asset         │ xóa       │
  │ Asset Repair                     │ asset_ref     │ xóa       │
  │ Asset Commissioning              │ final_asset   │ nullify   │
  │ Asset Document                   │ asset_ref     │ xóa       │
  │ Incident Report                  │ asset         │ xóa       │
  │ IMM CAPA Record                  │ asset         │ nullify   │
  │ IMM RCA Record                   │ asset         │ nullify   │
  │ Asset Lifecycle Event            │ asset         │ xóa       │
  │ IMM Audit Trail                  │ asset         │ xóa       │
  └──────────────────────────────────┴───────────────┴───────────┘

"xóa"    → frappe.delete_doc (xóa hẳn bản ghi)
"nullify" → frappe.db.set_value field = None (giữ bản ghi, bỏ link)

Chạy:
  # Preview trước (không thay đổi gì):
  bench --site miyano execute assetcore.scripts.maintenance.clean_orphaned_data.dry_run

  # Chạy thật:
  bench --site miyano execute assetcore.scripts.maintenance.clean_orphaned_data.run

  # Chỉ quét một DocType:
  bench --site miyano execute assetcore.scripts.maintenance.clean_orphaned_data.scan_doctype \
        --kwargs '{"doctype": "PM Work Order"}'
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import frappe

# ─── Cấu hình DocTypes cần quét ──────────────────────────────────────────────

ActionType = Literal["delete", "nullify"]

@dataclass
class ScanTarget:
    doctype: str
    asset_field: str
    action: ActionType
    # DocType có docstatus (submitted docs) → cần cancel trước khi xóa
    has_submit: bool = False


_TARGETS: list[ScanTarget] = [
    ScanTarget("PM Work Order",           "asset_ref",   "delete",  has_submit=False),
    ScanTarget("PM Schedule",             "asset_ref",   "delete",  has_submit=False),
    ScanTarget("IMM Asset Calibration",   "asset",       "delete",  has_submit=True),
    ScanTarget("IMM Calibration Schedule","asset",       "delete",  has_submit=False),
    ScanTarget("Asset Transfer",          "asset",       "delete",  has_submit=True),
    ScanTarget("Asset Repair",            "asset_ref",   "delete",  has_submit=True),
    ScanTarget("Asset Commissioning",     "final_asset", "nullify", has_submit=True),
    # Asset Document có validator chặn xóa → chỉ nullify link
    ScanTarget("Asset Document",          "asset_ref",   "nullify", has_submit=False),
    ScanTarget("Incident Report",         "asset",       "delete",  has_submit=False),
    ScanTarget("IMM CAPA Record",         "asset",       "nullify", has_submit=False),
    ScanTarget("IMM RCA Record",          "asset",       "nullify", has_submit=False),
    # Lifecycle Event và Audit Trail: giữ bản ghi (traceability), chỉ tháo link asset đã xóa
    ScanTarget("Asset Lifecycle Event",   "asset",       "nullify", has_submit=False),
    ScanTarget("IMM Audit Trail",         "asset",       "nullify", has_submit=False),
]

# ─── Kết quả cho mỗi bản ghi ─────────────────────────────────────────────────

@dataclass
class RecordResult:
    doctype: str
    name: str
    orphaned_asset: str
    action: str        # "deleted" | "nullified" | "would_delete" | "would_nullify" | "error"
    error: str = ""


# ─── Core logic ──────────────────────────────────────────────────────────────

def _get_live_asset_names() -> set[str]:
    # pluck trả về list[str] — cast thành set để O(1) lookup
    return set(frappe.db.get_all("AC Asset", pluck="name"))


def _find_orphans(target: ScanTarget, live_assets: set[str]) -> list[dict]:
    """Trả về các bản ghi của target.doctype mà asset_field trỏ đến asset đã xóa."""
    # Chỉ lấy bản ghi có asset_field != None/""
    try:
        rows = frappe.db.get_all(
            target.doctype,
            fields=["name", target.asset_field, "docstatus"],
            filters=[[target.asset_field, "is", "set"]],
        )
    except Exception as exc:
        # DocType chưa migrate hoặc bảng chưa tồn tại
        print(f"  [WARN] Không thể query {target.doctype}: {exc}")
        return []

    orphans = []
    for row in rows:
        asset_val = row.get(target.asset_field)
        if asset_val and asset_val not in live_assets:
            orphans.append({
                "name": row["name"],
                "asset": asset_val,
                "docstatus": row.get("docstatus", 0),
            })
    return orphans


def _delete_record(doctype: str, name: str, has_submit: bool, docstatus: int) -> str:
    """Xóa bản ghi. Cancel trước nếu đã submit."""
    try:
        if has_submit and docstatus == 1:
            frappe.db.set_value(doctype, name, "docstatus", 2)
        frappe.delete_doc(doctype, name, ignore_missing=True, force=True)
        return "deleted"
    except Exception as exc:
        return f"error: {exc}"


def _nullify_record(doctype: str, name: str, asset_field: str) -> str:
    """Set asset_field = None để tháo link, giữ nguyên bản ghi."""
    try:
        frappe.db.set_value(doctype, name, asset_field, None)
        return "nullified"
    except Exception as exc:
        return f"error: {exc}"


def _process_target(target: ScanTarget, live_assets: set[str], dry_run: bool) -> list[RecordResult]:
    orphans = _find_orphans(target, live_assets)
    results: list[RecordResult] = []

    for o in orphans:
        rec_name = o["name"]
        asset_val = o["asset"]
        docstatus = o["docstatus"]

        if dry_run:
            dry_action = f"would_{target.action}"
            results.append(RecordResult(target.doctype, rec_name, asset_val, dry_action))
            continue

        if target.action == "delete":
            outcome = _delete_record(target.doctype, rec_name, target.has_submit, docstatus)
        else:  # nullify
            outcome = _nullify_record(target.doctype, rec_name, target.asset_field)

        err = outcome if outcome.startswith("error") else ""
        action_label = outcome if not err else "error"
        results.append(RecordResult(target.doctype, rec_name, asset_val, action_label, err))

    return results


# ─── Reporting ───────────────────────────────────────────────────────────────

def _print_report(all_results: list[RecordResult], mode: str) -> None:
    sep = "=" * 68
    print(f"\n{sep}")
    print(f"  clean_orphaned_data — {mode}")
    print(sep)

    by_dt: dict[str, list[RecordResult]] = {}
    for r in all_results:
        by_dt.setdefault(r.doctype, []).append(r)

    total_acted = 0
    total_errors = 0

    for dt, recs in by_dt.items():
        print(f"\n  ▸ {dt}  ({len(recs)} orphan)")
        for r in recs:
            tag = r.action.upper()
            line = f"    [{tag}] {r.name}  (asset: {r.orphaned_asset})"
            if r.error:
                line += f"\n         ERROR: {r.error}"
                total_errors += 1
            else:
                total_acted += 1
            print(line)

    print(f"\n{sep}")
    print(f"  Tổng: {len(all_results)} orphan tìm thấy")
    print(f"  Đã xử lý: {total_acted}  |  Lỗi: {total_errors}")
    if mode == "DRY RUN":
        print("  ℹ️  Dry run — chưa thay đổi gì. Chạy run() để áp dụng thật.")
    else:
        print("  ✓ Đã commit vào DB.")
    print(f"{sep}\n")


# ─── Public API ──────────────────────────────────────────────────────────────

def run(dry_run: bool = False) -> dict:
    """Điểm vào chính."""
    mode = "DRY RUN" if dry_run else "LIVE"

    print("\n[clean_orphaned_data] Đang tải danh sách AC Asset sống...")
    live_assets = _get_live_asset_names()
    print(f"[clean_orphaned_data] Tìm thấy {len(live_assets)} AC Asset hợp lệ.")

    all_results: list[RecordResult] = []
    for target in _TARGETS:
        print(f"[clean_orphaned_data] Quét {target.doctype}...", end=" ", flush=True)
        results = _process_target(target, live_assets, dry_run)
        print(f"{len(results)} orphan")
        all_results.extend(results)

    _print_report(all_results, mode)

    if not dry_run and all_results:
        frappe.db.commit()

    return {
        "mode": mode,
        "total_orphans": len(all_results),
        "results": [
            {
                "doctype": r.doctype,
                "name": r.name,
                "orphaned_asset": r.orphaned_asset,
                "action": r.action,
                "error": r.error,
            }
            for r in all_results
        ],
    }


def dry_run() -> dict:
    """Preview — không thay đổi DB."""
    return run(dry_run=True)


def scan_doctype(doctype: str) -> dict:
    """Quét một DocType cụ thể (dry run). Dùng để debug."""
    target = next((t for t in _TARGETS if t.doctype == doctype), None)
    if not target:
        valid = [t.doctype for t in _TARGETS]
        print(f"[clean_orphaned_data] DocType '{doctype}' không có trong danh sách quét.")
        print(f"  Các DocType hợp lệ: {valid}")
        return {"error": "DocType not in scan list", "valid": valid}

    live_assets = _get_live_asset_names()
    results = _process_target(target, live_assets, dry_run=True)

    sep = "─" * 50
    print(f"\n{sep}")
    print(f"scan_doctype: {doctype} ({len(results)} orphan)")
    print(sep)
    for r in results:
        print(f"  {r.name}  →  asset '{r.orphaned_asset}' đã bị xóa")
    if not results:
        print("  Không tìm thấy orphan nào.")
    print(f"{sep}\n")

    return {"doctype": doctype, "orphans": len(results), "records": [r.name for r in results]}
