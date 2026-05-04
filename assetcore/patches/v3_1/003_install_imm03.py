"""IMM-03 (Wave 2) — install DocTypes + Custom Fields + 3 Workflows.

Bao gồm:
  - 5 primary DocType + 6 child table (auto sync qua reload_doc)
  - Custom fields trên AC Supplier (AVL info)
  - Custom fields trên AC Purchase (link IMM-03)
  - 3 Workflow JSON: Vendor Eval / Decision / AVL

Idempotent.
"""
from __future__ import annotations

import json
import os

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


_DOCTYPES = (
    "vendor_eval_criterion", "vendor_eval_candidate", "vendor_quotation_line",
    "vendor_cert", "audit_finding", "scorecard_kpi_row",
    "imm_vendor_evaluation", "imm_procurement_decision",
    "imm_avl_entry", "imm_vendor_scorecard", "imm_supplier_audit",
)

_WORKFLOWS = (
    ("imm_03_vendor_eval_workflow.json", "IMM-03 Vendor Eval Workflow"),
    ("imm_03_decision_workflow.json",    "IMM-03 Decision Workflow"),
    ("imm_03_avl_workflow.json",         "IMM-03 AVL Workflow"),
)


_AC_SUPPLIER_CFIELDS = [
    {
        "fieldname": "section_imm_avl",
        "fieldtype": "Section Break",
        "label": "IMM AVL & Audit",
        "insert_after": "notes",  # default sections; if missing fallback ok
    },
    {"fieldname": "imm_avl_status", "fieldtype": "Select",
     "label": "AVL Status", "insert_after": "section_imm_avl",
     "options": "\nApproved\nConditional\nSuspended\nExpired\nNot Applicable",
     "read_only": 1, "in_standard_filter": 1},
    {"fieldname": "imm_avl_categories", "fieldtype": "Small Text",
     "label": "AVL Categories", "insert_after": "imm_avl_status", "read_only": 1},
    {"fieldname": "imm_overall_score", "fieldtype": "Float",
     "label": "Overall Score", "insert_after": "imm_avl_categories",
     "read_only": 1, "precision": "4"},
    {"fieldname": "imm_last_audit_date", "fieldtype": "Date",
     "label": "Last Audit Date", "insert_after": "imm_overall_score", "read_only": 1},
    {"fieldname": "imm_next_audit_date", "fieldtype": "Date",
     "label": "Next Audit Due", "insert_after": "imm_last_audit_date", "read_only": 1},
    {"fieldname": "imm_certifications", "fieldtype": "Table",
     "label": "Certifications", "options": "Vendor Cert",
     "insert_after": "imm_next_audit_date"},
]

_AC_PURCHASE_CFIELDS = [
    {"fieldname": "section_imm03", "fieldtype": "Section Break",
     "label": "IMM-03 Procurement", "insert_after": "notes"},
    {"fieldname": "imm_procurement_decision", "fieldtype": "Link",
     "label": "Procurement Decision", "options": "IMM Procurement Decision",
     "insert_after": "section_imm03", "read_only": 1, "in_standard_filter": 1},
    {"fieldname": "imm_tech_spec", "fieldtype": "Link",
     "label": "Tech Spec", "options": "IMM Tech Spec",
     "insert_after": "imm_procurement_decision", "read_only": 1},
    {"fieldname": "imm_funding_source", "fieldtype": "Select",
     "label": "Funding Source", "insert_after": "imm_tech_spec",
     "options": "\nNSNN\nTài trợ\nXã hội hóa\nBHYT\nKhác"},
]


def execute() -> None:
    # 1. Force-load DocType JSONs trước khi patch dùng (đảm bảo có trước custom_fields)
    for dt in _DOCTYPES:
        try:
            frappe.reload_doc("assetcore", "doctype", dt)
        except Exception:
            frappe.log_error(frappe.get_traceback(), f"IMM-03 reload_doc {dt} failed")

    # 2. Custom fields
    try:
        create_custom_fields(
            {"AC Supplier": _AC_SUPPLIER_CFIELDS},
            ignore_validate=True, update=True,
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMM-03 AC Supplier cfields failed")

    try:
        create_custom_fields(
            {"AC Purchase": _AC_PURCHASE_CFIELDS},
            ignore_validate=True, update=True,
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMM-03 AC Purchase cfields failed")

    # 3. Workflows
    wf_dir = frappe.get_app_path("assetcore", "assetcore", "workflow")
    for filename, wf_name in _WORKFLOWS:
        path = os.path.join(wf_dir, filename)
        if not os.path.exists(path):
            frappe.log_error(f"Workflow file missing: {path}", "IMM-03 install")
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
        wf.set("states", []); wf.set("transitions", [])
    else:
        wf = frappe.new_doc("Workflow")
        wf.workflow_name = wf_name; wf.name = wf_name

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
    if any(k in sl for k in ("approved", "awarded", "active", "completed", "evaluated", "issued", "signed")): return "Success"
    if any(k in sl for k in ("suspend", "cancel", "reject", "fail")): return "Danger"
    if any(k in sl for k in ("review", "pending", "negot", "recommend", "rfq", "warning", "received", "selected")): return "Warning"
    return "Primary"


def _ensure_workflow_action_master(action: str) -> None:
    if not frappe.db.exists("Workflow Action Master", action):
        d = frappe.new_doc("Workflow Action Master")
        d.workflow_action_name = action
        d.insert(ignore_permissions=True)
