"""IMM-02 (Wave 2) — install DocTypes + Workflow.

DocType reload tự động khi `bench migrate` chạy `sync_doctypes`.
Patch này: upsert IMM-02 Spec Workflow vào DB (idempotent).
"""
from __future__ import annotations

import json
import os

import frappe


_WORKFLOWS = (
    ("imm_02_spec_workflow.json", "IMM-02 Spec Workflow"),
)


_DOCTYPES = (
    "tech_spec_requirement", "tech_spec_document", "benchmark_candidate",
    "infra_compatibility_item", "lock_in_risk_item",
    "imm_tech_spec", "imm_market_benchmark", "imm_lock_in_risk_assessment",
)


def execute() -> None:
    # 1. Force-load DocType JSONs trước khi patch dùng (chạy trước sync_doctypes step)
    for dt in _DOCTYPES:
        try:
            frappe.reload_doc("assetcore", "doctype", dt)
        except Exception:
            frappe.log_error(frappe.get_traceback(), f"IMM-02 reload_doc {dt} failed")

    wf_dir = frappe.get_app_path("assetcore", "assetcore", "workflow")
    for filename, wf_name in _WORKFLOWS:
        path = os.path.join(wf_dir, filename)
        if not os.path.exists(path):
            frappe.log_error(f"Workflow file missing: {path}", "IMM-02 install")
            continue
        with open(path) as f:
            data = json.load(f)
        _upsert_workflow(data, wf_name)
    frappe.clear_cache()


def _upsert_workflow(data: dict, wf_name: str) -> None:
    for st in data.get("states", []):
        _ensure_workflow_state(st["state"])
    for tr in data.get("transitions", []):
        _ensure_workflow_action_master(tr["action"])
        _ensure_workflow_state(tr["next_state"])

    if frappe.db.exists("Workflow", wf_name):
        wf = frappe.get_doc("Workflow", wf_name)
        wf.set("states", [])
        wf.set("transitions", [])
    else:
        wf = frappe.new_doc("Workflow")
        wf.workflow_name = wf_name
        wf.name = wf_name

    wf.document_type        = data["document_type"]
    wf.workflow_state_field = data.get("workflow_state_field", "workflow_state")
    wf.is_active            = data.get("is_active", 1)
    wf.send_email_alert     = data.get("send_email_alert", 0)

    for st in data.get("states", []):
        wf.append("states", {
            "state": st["state"], "doc_status": st.get("doc_status", "0"),
            "allow_edit": st.get("allow_edit", "System Manager"),
        })
    for tr in data.get("transitions", []):
        wf.append("transitions", {
            "state": tr["state"], "next_state": tr["next_state"],
            "action": tr["action"], "allowed": tr.get("allowed", "System Manager"),
        })
    wf.save(ignore_permissions=True)
    frappe.db.commit()


def _ensure_workflow_state(state: str) -> None:
    if not frappe.db.exists("Workflow State", state):
        d = frappe.new_doc("Workflow State")
        d.workflow_state_name = state
        d.style = _style_for(state)
        d.insert(ignore_permissions=True)


def _style_for(s: str) -> str:
    sl = s.lower()
    if any(k in sl for k in ("locked", "active", "approved", "completed")): return "Success"
    if any(k in sl for k in ("withdraw", "reject", "cancel", "fail")): return "Danger"
    if any(k in sl for k in ("review", "pending", "submit")): return "Warning"
    return "Primary"


def _ensure_workflow_action_master(action: str) -> None:
    if not frappe.db.exists("Workflow Action Master", action):
        d = frappe.new_doc("Workflow Action Master")
        d.workflow_action_name = action
        d.insert(ignore_permissions=True)
