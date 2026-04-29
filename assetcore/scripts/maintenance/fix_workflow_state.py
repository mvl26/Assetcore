# Copyright (c) 2026, AssetCore Team
"""
fix_workflow_state.py — Vá lỗi Workflow State 'Commissioned not found' (HTTP 500).

Nguyên nhân:
  tabWorkflow State và tabWorkflow Action Master thiếu các bản ghi cần thiết
  cho workflow "AC Asset Lifecycle" → Frappe ném 500 khi validate transition.
  AC Asset dùng field lifecycle_status (không phải workflow_state).

Giải pháp:
  1. Tạo các Workflow State còn thiếu.
  2. Tạo các Workflow Action Master còn thiếu.
  3. Kiểm tra AC Asset có lifecycle_status không hợp lệ → migrate về "Active".

Chạy:
  bench --site miyano execute assetcore.scripts.maintenance.fix_workflow_state.dry_run
  bench --site miyano execute assetcore.scripts.maintenance.fix_workflow_state.run
"""
from __future__ import annotations

import frappe

# Khớp với ac_asset_lifecycle_workflow.json → states[]
_REQUIRED_STATES: list[dict] = [
    {"name": "Draft",             "style": "Warning"},
    {"name": "Commissioned",      "style": "Primary"},
    {"name": "Active",            "style": "Success"},
    {"name": "Under Maintenance", "style": "Warning"},
    {"name": "Under Repair",      "style": "Warning"},
    {"name": "Calibrating",       "style": "Warning"},
    {"name": "Out of Service",    "style": "Danger"},
    {"name": "Decommissioned",    "style": "Inverse"},
]

# Khớp với ac_asset_lifecycle_workflow.json → transitions[].action
_REQUIRED_ACTIONS: list[str] = [
    "Commission", "Activate",
    "Bắt đầu bảo trì", "Hoàn thành bảo trì",
    "Bắt đầu sửa chữa", "Bắt đầu hiệu chuẩn", "Đưa ra khỏi sử dụng",
    "Hoàn thành sửa chữa", "Không thể sửa chữa",
    "Hiệu chuẩn đạt", "Hiệu chuẩn không đạt",
    "Khôi phục hoạt động", "Sửa chữa lại", "Thanh lý",
]

_VALID_STATES = {s["name"] for s in _REQUIRED_STATES}
_LIFECYCLE_FIELD = "lifecycle_status"   # workflow_state_field trong workflow JSON
_FALLBACK_STATE = "Active"


# ─── Phase 1: Workflow States ────────────────────────────────────────────────

def _ensure_workflow_states(dry_run: bool) -> list[dict]:
    results = []
    for state_def in _REQUIRED_STATES:
        name = state_def["name"]
        if frappe.db.exists("Workflow State", name):
            results.append({"item": name, "action": "ok", "note": "already exists"})
            continue
        if dry_run:
            results.append({"item": name, "action": "would_create", "note": f"style={state_def['style']}"})
            continue
        doc = frappe.new_doc("Workflow State")
        doc.workflow_state_name = name
        doc.style = state_def["style"]
        doc.name = name
        doc.insert(ignore_permissions=True)
        results.append({"item": name, "action": "created", "note": f"style={state_def['style']}"})
    return results


# ─── Phase 2: Workflow Action Masters ────────────────────────────────────────

def _ensure_action_masters(dry_run: bool) -> list[dict]:
    results = []
    for action in _REQUIRED_ACTIONS:
        if frappe.db.exists("Workflow Action Master", action):
            results.append({"item": action, "action": "ok", "note": "already exists"})
            continue
        if dry_run:
            results.append({"item": action, "action": "would_create", "note": ""})
            continue
        doc = frappe.new_doc("Workflow Action Master")
        doc.workflow_action_name = action
        doc.name = action
        doc.insert(ignore_permissions=True)
        results.append({"item": action, "action": "created", "note": ""})
    return results


# ─── Phase 3: AC Asset lifecycle_status sanity check ─────────────────────────

def _check_asset_states(dry_run: bool) -> list[dict]:
    rows = frappe.db.get_all(
        "AC Asset",
        fields=["name", _LIFECYCLE_FIELD],
        filters=[[_LIFECYCLE_FIELD, "is", "set"]],
    )
    results = []
    for row in rows:
        current = row.get(_LIFECYCLE_FIELD) or ""
        if current in _VALID_STATES:
            continue
        if dry_run:
            results.append({
                "item": row["name"],
                "action": "would_migrate",
                "note": f"{current} → {_FALLBACK_STATE}",
            })
            continue
        frappe.db.set_value("AC Asset", row["name"], _LIFECYCLE_FIELD, _FALLBACK_STATE)
        results.append({
            "item": row["name"],
            "action": "migrated",
            "note": f"{current} → {_FALLBACK_STATE}",
        })
    return results


# ─── Output ──────────────────────────────────────────────────────────────────

def _print_section(title: str, rows: list[dict]) -> None:
    bar = "─" * 56
    print(f"\n  {bar}")
    print(f"  {title}  ({len(rows)})")
    print(f"  {bar}")
    for r in rows:
        tag = r["action"].upper()
        note = f"  · {r['note']}" if r.get("note") else ""
        print(f"  [{tag}] {r['item']}{note}")


def run(dry_run: bool = False) -> dict:
    mode = "DRY RUN" if dry_run else "LIVE"
    sep = "=" * 62
    print(f"\n{sep}")
    print(f"  fix_workflow_state — {mode}")
    print(sep)

    state_results  = _ensure_workflow_states(dry_run)
    action_results = _ensure_action_masters(dry_run)
    asset_results  = _check_asset_states(dry_run)

    _print_section("Workflow States", state_results)
    _print_section("Workflow Action Masters", action_results)
    _print_section("AC Asset lifecycle_status không hợp lệ", asset_results)

    if not dry_run:
        frappe.db.commit()
        print("\n  ✓ Đã commit vào DB.")
    else:
        print("\n  ℹ️  Dry run — chưa thay đổi gì.")

    created_s = sum(1 for r in state_results  if r["action"] == "created")
    created_a = sum(1 for r in action_results if r["action"] == "created")
    migrated  = sum(1 for r in asset_results  if r["action"] == "migrated")
    print(f"\n  Tóm tắt: {created_s} state tạo mới, {created_a} action tạo mới, {migrated} asset migrate.")
    print(f"{sep}\n")

    return {
        "mode": mode,
        "workflow_states": state_results,
        "action_masters": action_results,
        "migrated_assets": asset_results,
    }


def dry_run() -> dict:
    return run(dry_run=True)
