"""IMM-01 (Wave 2) — install DocTypes + Workflows.

Bootstrap module IMM-01 — Đánh giá nhu cầu và dự toán.

DocType reload tự động khi `bench migrate` chạy `sync_doctypes` (Frappe đọc
JSON từ `<app>/<module>/doctype/<dt>/<dt>.json`). Patch này chỉ cần:
  1) Đảm bảo workflow JSON được nạp vào DB (Frappe không tự nạp file flat
     trong `<module>/workflow/`; phải upsert thủ công — đây là cách Wave 1
     làm qua bench export-fixtures, ta chuẩn hóa thành patch idempotent).
  2) Đảm bảo workflow active sau khi insert.

Idempotent — re-run an toàn.
"""
from __future__ import annotations

import json
import os

import frappe

# Path tới workflow JSON files. Frappe module folder = `assetcore/assetcore/`,
# nên path là `<app_path>/assetcore/workflow/` (3 mức `assetcore`).
def _wf_dir() -> str:
    return frappe.get_app_path("assetcore", "assetcore", "workflow")

_WORKFLOWS = (
    ("imm_01_needs_workflow.json", "IMM-01 Needs Workflow"),
    ("imm_01_plan_workflow.json",  "IMM-01 Plan Workflow"),
)


_DOCTYPES = (
    "needs_priority_scoring", "budget_estimate_line",
    "procurement_plan_line", "forecast_driver",
    "imm_needs_request", "imm_procurement_plan", "imm_demand_forecast",
)


def execute() -> None:
    for dt in _DOCTYPES:
        try:
            frappe.reload_doc("assetcore", "doctype", dt)
        except Exception:
            frappe.log_error(frappe.get_traceback(), f"IMM-01 reload_doc {dt} failed")

    wf_dir = _wf_dir()
    for filename, wf_name in _WORKFLOWS:
        path = os.path.join(wf_dir, filename)
        if not os.path.exists(path):
            frappe.log_error(f"Workflow file missing: {path}", "IMM-01 install")
            continue
        with open(path) as f:
            data = json.load(f)
        _upsert_workflow(data, wf_name)

    frappe.clear_cache()


def _upsert_workflow(data: dict, wf_name: str) -> None:
    """Upsert Workflow + Workflow State + Workflow Action Master + transitions."""
    # Đảm bảo Workflow State + Workflow Action Master tồn tại
    for st in data.get("states", []):
        _ensure_workflow_state(st["state"])
    for tr in data.get("transitions", []):
        _ensure_workflow_action_master(tr["action"])
        _ensure_workflow_state(tr["next_state"])

    if frappe.db.exists("Workflow", wf_name):
        wf = frappe.get_doc("Workflow", wf_name)
        # Reset states + transitions để re-import
        wf.set("states", [])
        wf.set("transitions", [])
    else:
        wf = frappe.new_doc("Workflow")
        wf.workflow_name = wf_name
        wf.name = wf_name

    wf.document_type = data["document_type"]
    wf.workflow_state_field = data.get("workflow_state_field", "workflow_state")
    wf.is_active = data.get("is_active", 1)
    wf.send_email_alert = data.get("send_email_alert", 0)

    for st in data.get("states", []):
        wf.append("states", {
            "state":      st["state"],
            "doc_status": st.get("doc_status", "0"),
            "allow_edit": st.get("allow_edit", "System Manager"),
            "update_field": st.get("update_field"),
            "update_value": st.get("update_value"),
        })
    for tr in data.get("transitions", []):
        wf.append("transitions", {
            "state":      tr["state"],
            "next_state": tr["next_state"],
            "action":     tr["action"],
            "allowed":    tr.get("allowed", "System Manager"),
            "condition":  tr.get("condition"),
        })

    wf.save(ignore_permissions=True)
    frappe.db.commit()


def _ensure_workflow_state(state: str) -> None:
    if not frappe.db.exists("Workflow State", state):
        doc = frappe.new_doc("Workflow State")
        doc.workflow_state_name = state
        doc.style = _style_for_state(state)
        doc.insert(ignore_permissions=True)


def _style_for_state(state: str) -> str:
    s = state.lower()
    if any(k in s for k in ("approved", "active", "released", "completed")):
        return "Success"
    if any(k in s for k in ("reject", "cancel", "withdraw", "fail")):
        return "Danger"
    if any(k in s for k in ("pending", "review", "submit", "hold")):
        return "Warning"
    return "Primary"


def _ensure_workflow_action_master(action: str) -> None:
    if not frappe.db.exists("Workflow Action Master", action):
        doc = frappe.new_doc("Workflow Action Master")
        doc.workflow_action_name = action
        doc.insert(ignore_permissions=True)
