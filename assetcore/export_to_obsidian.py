# Copyright (c) 2026, AssetCore Team
"""
export_to_obsidian.py — AssetCore → Obsidian Graph View Exporter

Xuất cấu trúc DocType + Business Rules + Workflow sang Markdown
để dùng với Obsidian Graph View.

Usage:
  bench --site [site] execute assetcore.export_to_obsidian.export_all

Output:  apps/assetcore/obsidian_vault/
"""

import frappe
import re
import os
from pathlib import Path
from datetime import datetime
from textwrap import dedent

# ── CONFIG ─────────────────────────────────────────────────────────────────────
VAULT       = Path(__file__).parent.parent / "obsidian_vault"   # apps/assetcore/obsidian_vault/
APP_ROOT    = Path(__file__).parent
GENERATED   = datetime.now().strftime("%Y-%m-%d %H:%M")

# DocTypes to export (primary + child)
PRIMARY_DOCTYPES = [
    "Asset",
    "Asset Commissioning",
    "Asset Repair",
    "Asset Document",
]
EXTRA_DOCTYPES = [
    "Asset QA Non Conformance",
    "Document Request",
    "Expiry Alert Log",
    "Required Document Type",
    "Commissioning Checklist",
    "Commissioning Document Record",
]

# Module mapping
MODULE_MAP = {
    "Asset Commissioning":         "IMM-04",
    "Asset Document":              "IMM-05",
    "Commissioning Checklist":     "IMM-04",
    "Commissioning Document Record": "IMM-04",
    "Asset QA Non Conformance":    "IMM-04",
    "Asset Repair":                "IMM-09",
    "Expiry Alert Log":            "IMM-05",
    "Document Request":            "IMM-05",
    "Required Document Type":      "IMM-05",
    "Asset":                       "ERPNext Core",
}

# ── BUSINESS RULES (extracted from asset_commissioning.py + asset_document.py) ─
BUSINESS_RULES = {
    "VR-01": {
        "title":   "Serial Number Uniqueness",
        "module":  "IMM-04",
        "doctype": "Asset Commissioning",
        "trigger": "validate()",
        "desc":    "Vendor Serial Number phải duy nhất trên toàn hệ thống — kiểm tra trong cả `tabAsset` (custom_vendor_serial) và `tabAsset Commissioning` (docstatus != 2).",
        "block":   "Throw ValidationError khi trùng serial.",
        "code_ref": "asset_commissioning.py::validate_unique_serial()",
    },
    "VR-02": {
        "title":   "Required Documents Gate",
        "module":  "IMM-04",
        "doctype": "Asset Commissioning",
        "trigger": "validate() khi workflow_state ∈ {Pending_Handover, Installing, Identification, Initial_Inspection, Re_Inspection, Pending_Release, Clinical_Release}",
        "desc":    "Các hồ sơ bắt buộc CO và CQ phải có status = 'Received' trước khi bàn giao máy.",
        "block":   "Throw ValidationError nếu CQ hoặc CO != Received.",
        "code_ref": "asset_commissioning.py::validate_required_documents()",
    },
    "VR-03": {
        "title":   "Baseline Test Completion",
        "module":  "IMM-04",
        "doctype": "Asset Commissioning",
        "trigger": "validate() khi workflow_state ∈ {Initial_Inspection, Re_Inspection, Clinical_Release}",
        "desc":    "Toàn bộ tiêu chí an toàn điện (IEC 60601-1) phải có kết quả. Nếu kết quả Fail bắt buộc điền fail_note.",
        "block":   "VR-03a: Thiếu result. VR-03b: Có Fail nhưng cố Release.",
        "code_ref": "asset_commissioning.py::validate_checklist_completion()",
    },
    "VR-04": {
        "title":   "Non-Conformance Release Block",
        "module":  "IMM-04",
        "doctype": "Asset Commissioning",
        "trigger": "validate() khi workflow_state = Clinical_Release",
        "desc":    "Không thể phát hành nếu còn Phiếu NC (Asset QA Non Conformance) với resolution_status = Open.",
        "block":   "Throw kèm danh sách NC chưa đóng.",
        "code_ref": "asset_commissioning.py::block_release_if_nc_open()",
    },
    "VR-07": {
        "title":   "Radiation Device License Hold",
        "module":  "IMM-04",
        "doctype": "Asset Commissioning",
        "trigger": "validate() khi is_radiation_device = True AND workflow_state ∈ {Clinical_Release, Pending_Release}",
        "desc":    "Thiết bị bức xạ / tia X bắt buộc upload Giấy phép Cục An toàn Bức xạ Hạt nhân trước khi release.",
        "block":   "Throw VR-07 nếu qa_license_doc trống.",
        "code_ref": "asset_commissioning.py::validate_radiation_hold()",
    },
    "GW-2": {
        "title":   "IMM-05 Document Compliance Gateway",
        "module":  "IMM-04 → IMM-05",
        "doctype": "Asset Commissioning",
        "trigger": "validate() khi workflow_state ∈ {Clinical_Release, Pending_Release} AND final_asset IS SET",
        "desc":    "Thiết bị phải có Chứng nhận đăng ký lưu hành (Active) trong IMM-05 hoặc được đánh dấu Exempt (NĐ 98/2021) trước khi Submit.",
        "block":   "Throw kèm message 'GW-2 Compliance Block'.",
        "code_ref": "asset_commissioning.py::_gw2_check_document_compliance()",
    },
    "BR-07": {
        "title":   "Auto-Import Document Set",
        "module":  "IMM-04 → IMM-05",
        "doctype": "Asset Commissioning",
        "trigger": "on_submit() — sau khi mint_core_asset()",
        "desc":    "US-03: Tự động import toàn bộ commissioning_documents có status=Received sang IMM-05 (Asset Document) dưới dạng Draft.",
        "block":   "N/A — auto-create, log error nếu thất bại.",
        "code_ref": "asset_commissioning.py::create_initial_document_set()",
    },
    "IMM05-VR-01": {
        "title":   "Expiry After Issued Date",
        "module":  "IMM-05",
        "doctype": "Asset Document",
        "trigger": "validate()",
        "desc":    "expiry_date phải sau issued_date.",
        "block":   "Throw VR-01 nếu expiry_date <= issued_date.",
        "code_ref": "asset_document.py::vr_01_expiry_after_issued()",
    },
    "IMM05-VR-02": {
        "title":   "Unique Document Number",
        "module":  "IMM-05",
        "doctype": "Asset Document",
        "trigger": "validate()",
        "desc":    "doc_number phải duy nhất theo (asset_ref, doc_type_detail). Nếu là version mới thì tăng version field.",
        "block":   "Throw VR-02 nếu trùng.",
        "code_ref": "asset_document.py::vr_02_unique_doc_number()",
    },
    "IMM05-VR-07": {
        "title":   "Legal/Certification Requires Expiry Date",
        "module":  "IMM-05",
        "doctype": "Asset Document",
        "trigger": "validate() khi doc_category ∈ {Legal, Certification}",
        "desc":    "Tài liệu pháp lý bắt buộc có expiry_date (NĐ 98/2021 mandate).",
        "block":   "Throw VR-07.",
        "code_ref": "asset_document.py::vr_07_legal_requires_expiry()",
    },
    "IMM05-VR-08": {
        "title":   "File Format Validation",
        "module":  "IMM-05",
        "doctype": "Asset Document",
        "trigger": "validate() khi file_attachment IS SET",
        "desc":    "Chỉ chấp nhận định dạng PDF, JPG, JPEG, PNG, DOCX.",
        "block":   "Throw VR-08 nếu sai định dạng.",
        "code_ref": "asset_document.py::vr_08_file_format_check()",
    },
    "IMM05-VR-10": {
        "title":   "Exempt Fields Required",
        "module":  "IMM-05",
        "doctype": "Asset Document",
        "trigger": "validate() khi is_exempt = True",
        "desc":    "Khi đánh dấu miễn đăng ký NĐ98 phải có exempt_reason + exempt_proof.",
        "block":   "Throw VR-10.",
        "code_ref": "asset_document.py::vr_10_exempt_fields_required()",
    },
    "BR-SLA-PM": {
        "title":   "PM Next Due Date Calculation",
        "module":  "IMM-08",
        "doctype": "PM Work Order (pending)",
        "trigger": "on_submit() của PM Work Order",
        "desc":    "Next Due Date = Completion Date + Interval (ngày thực hoàn thành, KHÔNG phải ngày dự kiến). Đảm bảo lịch bám thực tế.",
        "block":   "N/A — tính toán trường next_due_date.",
        "code_ref": "services/imm08.py (planned)",
    },
    "BR-12-P1": {
        "title":   "P1 Incident SLA Escalation",
        "module":  "IMM-12",
        "doctype": "Corrective Work Order (pending)",
        "trigger": "tasks.py scheduler (hourly)",
        "desc":    "P1: Response SLA = 120 phút. Quá hạn → L1 escalate Workshop Head. Quá hạn + 30 phút → L2 escalate VP Block2.",
        "block":   "sendmail + publish_realtime theo level.",
        "code_ref": "tasks.py (planned)",
    },
}

# ── WORKFLOW STATES ────────────────────────────────────────────────────────────
IMM04_STATES = [
    ("Draft_Reception",          "HTM Technician",  "initial"),
    ("Pending_Doc_Verify",       "TBYT Officer",    "gate"),
    ("To_Be_Installed",          "Clinical Head",   "normal"),
    ("Installing",               "Vendor Tech",     "normal"),
    ("Identification",           "Biomed Engineer", "normal"),
    ("Initial_Inspection",       "Biomed Engineer", "gate"),
    ("Non_Conformance",          "Biomed/Vendor",   "bypass"),
    ("Clinical_Hold",            "QA Officer",      "gate"),
    ("Re_Inspection",            "Biomed Engineer", "normal"),
    ("Pending_Release",          "Workshop Head",   "gate"),
    ("Clinical_Release",         "VP Block2",       "gate"),
    ("Clinical_Release_Success", "Board/CEO",       "terminal"),
    ("Return_To_Vendor",         "Board",           "terminal"),
]


# ── HELPERS ────────────────────────────────────────────────────────────────────

def slug(name: str) -> str:
    """Convert 'Asset Commissioning' → 'Asset_Commissioning' for Mermaid IDs."""
    return name.replace(" ", "_").replace("-", "_").upper()


def mk(name: str) -> str:
    """Obsidian wikilink: [[Asset Commissioning]]."""
    return f"[[{name}]]"


def get_meta_fields(doctype: str) -> list[dict]:
    """Return list of {fieldname, fieldtype, label, options} for a DocType."""
    try:
        meta = frappe.get_meta(doctype)
        return [
            {
                "fieldname": f.fieldname,
                "fieldtype": f.fieldtype,
                "label":     f.label or f.fieldname,
                "options":   f.options or "",
                "reqd":      bool(f.reqd),
                "read_only": bool(f.read_only),
                "in_list_view": bool(f.in_list_view),
            }
            for f in meta.fields
            if f.fieldtype not in ("Section Break", "Column Break", "HTML",
                                   "Fold", "Heading", "Tab Break")
        ]
    except Exception as e:
        print(f"  ⚠️  get_meta({doctype}) failed: {e}")
        return []


def get_link_fields(fields: list[dict]) -> list[dict]:
    return [f for f in fields if f["fieldtype"] == "Link" and f["options"]]


def get_table_fields(fields: list[dict]) -> list[dict]:
    return [f for f in fields if f["fieldtype"] in ("Table", "Table MultiSelect")]


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"  ✅ {path.relative_to(VAULT.parent)}")


# ── MERMAID GENERATORS ─────────────────────────────────────────────────────────

def build_er_diagram(doctype: str, fields: list[dict]) -> str:
    """Generate Mermaid erDiagram for a DocType and its relationships."""
    links  = get_link_fields(fields)
    tables = get_table_fields(fields)

    lines = ["```mermaid", "erDiagram"]

    # Primary entity with key fields
    key_fields = [
        f for f in fields
        if f["fieldtype"] in ("Data", "Select", "Date", "Datetime", "Check",
                               "Link", "Currency", "Int", "Float", "Percent")
        and f["fieldname"] not in ("idx", "owner", "docstatus")
        and not f["fieldname"].startswith("column_break")
    ][:12]  # limit to 12 fields for readability

    entity_id = slug(doctype)
    lines.append(f"    {entity_id} {{")
    lines.append(f'        string name PK "Document ID"')
    for f in key_fields:
        ft_map = {
            "Data": "string", "Small Text": "string", "Text": "string",
            "Select": "string", "Link": "string",
            "Date": "date", "Datetime": "datetime",
            "Check": "boolean", "Int": "int", "Float": "float",
            "Currency": "decimal", "Percent": "float",
        }
        ftype = ft_map.get(f["fieldtype"], "string")
        req_marker = " UK" if f["reqd"] else ""
        lines.append(f'        {ftype} {f["fieldname"]}{req_marker} "{f["label"]}"')
    lines.append("    }")

    # Link relationships (many-to-one)
    added_entities = {entity_id}
    for lf in links:
        target = lf["options"].strip()
        if not target:
            continue
        target_id = slug(target)
        if target_id not in added_entities:
            lines.append(f"    {target_id} {{")
            lines.append(f'        string name PK')
            lines.append("    }")
            added_entities.add(target_id)
        req = "||" if lf["reqd"] else "|o"
        lines.append(f'    {entity_id} }}o--{req} {target_id} : "{lf["fieldname"]}"')

    # Table relationships (one-to-many)
    for tf in tables:
        child = tf["options"].strip()
        if not child:
            continue
        child_id = slug(child)
        if child_id not in added_entities:
            lines.append(f"    {child_id} {{")
            lines.append(f'        string name PK')
            lines.append("    }")
            added_entities.add(child_id)
        lines.append(f'    {entity_id} ||--o{{ {child_id} : "{tf["fieldname"]}"')

    lines.append("```")
    return "\n".join(lines)


def build_flowchart_workflow(states: list[tuple]) -> str:
    """Generate Mermaid flowchart for IMM-04 workflow."""
    lines = ["```mermaid", "flowchart TD"]
    prev = None
    colors = {
        "initial": "fill:#4CAF50,color:#fff",
        "gate":    "fill:#FF9800,color:#fff",
        "normal":  "fill:#2196F3,color:#fff",
        "bypass":  "fill:#F44336,color:#fff",
        "terminal":"fill:#607D8B,color:#fff",
    }
    for state, actor, stype in states:
        node_id = state.replace("_", "").replace(" ", "")
        shape_open  = "([" if stype == "terminal" else ("{" if stype == "gate" else "[")
        shape_close = "])" if stype == "terminal" else ("}" if stype == "gate" else "]")
        label = f"{state}\\n👤 {actor}"
        lines.append(f'    {node_id}{shape_open}"{label}"{shape_close}')
        color = colors.get(stype, "fill:#2196F3,color:#fff")
        lines.append(f"    style {node_id} {color}")
        if prev:
            lines.append(f"    {prev} --> {node_id}")
        prev = node_id

    lines.append("```")
    return "\n".join(lines)


# ── DOCTYPE MARKDOWN ───────────────────────────────────────────────────────────

def render_doctype(doctype: str, fields: list[dict]) -> str:
    links  = get_link_fields(fields)
    tables = get_table_fields(fields)
    module = MODULE_MAP.get(doctype, "AssetCore")
    brs    = [k for k, v in BUSINESS_RULES.items() if v["doctype"] == doctype]

    # Tags
    tags = ["DocType", "AssetCore", module.replace("-", "").replace(" ", "")]
    if doctype in ("Asset Commissioning", "Asset Document"):
        tags.append("Wave1")

    # Related doctypes via links + tables
    related = sorted({
        lf["options"].strip() for lf in links if lf["options"].strip()
    } | {
        tf["options"].strip() for tf in tables if tf["options"].strip()
    })

    # ── Frontmatter ──────────────────────────────────────────────────────────
    lines = [
        "---",
        f"title: \"{doctype}\"",
        f"module: \"{module}\"",
        f'tags: [{", ".join(tags)}]',
        f'generated: "{GENERATED}"',
        f'aliases: ["{slug(doctype).lower()}"]',
        "---",
        "",
        f"# {doctype}",
        "",
        f"> **Module:** `{module}` | **App:** `assetcore` | **Generated:** {GENERATED}",
        "",
    ]

    # ── ER Diagram ───────────────────────────────────────────────────────────
    lines += [
        "## Entity Relationship",
        "",
        build_er_diagram(doctype, fields),
        "",
    ]

    # ── IMM-04 Workflow ──────────────────────────────────────────────────────
    if doctype == "Asset Commissioning":
        lines += [
            "## Workflow — IMM-04 State Machine",
            "",
            build_flowchart_workflow(IMM04_STATES),
            "",
        ]

    # ── Overview ─────────────────────────────────────────────────────────────
    lines += ["## Overview", ""]
    desc_map = {
        "Asset":              "ERPNext core Fixed Asset record. Represents a physical device registered in the system. Extended by AssetCore with custom fields (vendor_serial, comm_ref, doc_completeness).",
        "Asset Commissioning":"**IMM-04** — Phiếu Lắp đặt & Nghiệm thu. Manages the full installation lifecycle from goods receipt (Draft) through QA inspection to Clinical Release. Creates the ERPNext Asset on successful submission.",
        "Asset Repair":       "ERPNext core Asset Repair record. Tracks corrective maintenance events, repair costs, and spare parts consumed. Maps to **IMM-09** in AssetCore workflow.",
        "Asset Document":     "**IMM-05** — Kho Hồ sơ Thiết bị. Stores all legal, technical, and certification documents. Enforces NĐ 98/2021 compliance with automatic expiry alerting at 90/60/30/0 day thresholds.",
        "Asset QA Non Conformance": "DOA/Damage incident report linked to Asset Commissioning. Blocks Clinical Release until resolved (VR-04).",
        "Document Request":   "Auto-escalating request for missing required documents. Created manually or by GW-2 compliance check. Escalates to 'Overdue' via daily scheduler.",
        "Expiry Alert Log":   "Immutable log of document expiry notifications. Created by daily scheduler at 90/60/30/0 day thresholds. Read-only after creation.",
        "Required Document Type": "Master configuration for mandatory document types per device category. Drives doc_completeness_pct calculation.",
        "Commissioning Checklist":        "Child table of Asset Commissioning. Stores IEC 60601-1 electrical safety test results.",
        "Commissioning Document Record":  "Child table of Asset Commissioning. Tracks receipt status of each required document (CO, CQ, Packing List, etc.).",
    }
    lines.append(desc_map.get(doctype, f"DocType `{doctype}` in module `{module}`."))
    lines += [""]

    # ── Fields Table ─────────────────────────────────────────────────────────
    visible_fields = [
        f for f in fields
        if f["fieldtype"] not in ("Button", "HTML", "Read Only")
        and not f["fieldname"].startswith(("section_", "column_", "sb_", "cb_"))
    ]

    lines += [
        "## Fields",
        "",
        "| Fieldname | Type | Label | Required | Options/Link |",
        "|-----------|------|-------|----------|-------------|",
    ]
    for f in visible_fields:
        req    = "✅" if f["reqd"] else ""
        opts   = mk(f["options"]) if f["fieldtype"] == "Link" and f["options"] else (f["options"] or "")
        if f["fieldtype"] in ("Table", "Table MultiSelect") and f["options"]:
            opts = mk(f["options"])
        lines.append(
            f'| `{f["fieldname"]}` | `{f["fieldtype"]}` | {f["label"]} | {req} | {opts} |'
        )
    lines += [""]

    # ── Link Fields (Obsidian wikilinks) ─────────────────────────────────────
    if links:
        lines += ["## Outgoing Links (Link Fields)", ""]
        for lf in links:
            target = lf["options"].strip()
            if target:
                req_label = " *(required)*" if lf["reqd"] else ""
                lines.append(f"- `{lf['fieldname']}` → {mk(target)}{req_label}")
        lines += [""]

    # ── Child Tables ─────────────────────────────────────────────────────────
    if tables:
        lines += ["## Child Tables", ""]
        for tf in tables:
            child = tf["options"].strip()
            if child:
                lines.append(f"- `{tf['fieldname']}` → {mk(child)}")
        lines += [""]

    # ── Business Rules ───────────────────────────────────────────────────────
    if brs:
        lines += ["## Business Rules", ""]
        for br_id in brs:
            br = BUSINESS_RULES[br_id]
            lines.append(f"- {mk(f'BR_{br_id}')} — **{br['title']}**")
            lines.append(f"  - Trigger: `{br['trigger']}`")
            lines.append(f"  - Block: {br['block']}")
        lines += [""]

    # ── Related DocTypes ─────────────────────────────────────────────────────
    if related:
        lines += ["## Related DocTypes", ""]
        for r in related:
            if r:
                lines.append(f"- {mk(r)}")
        lines += [""]

    return "\n".join(lines)


# ── BUSINESS RULE NOTES ────────────────────────────────────────────────────────

def render_business_rule(br_id: str, br: dict) -> str:
    lines = [
        "---",
        f'title: "BR_{br_id} — {br["title"]}"',
        f'tags: [BusinessRule, {br["module"].replace("-","").replace(" ","").replace("→","")}, AssetCore]',
        f'generated: "{GENERATED}"',
        "---",
        "",
        f"# BR `{br_id}` — {br['title']}",
        "",
        f"> #BusinessRule | Module: `{br['module']}` | DocType: {mk(br['doctype'])}",
        "",
        "## Definition",
        "",
        br["desc"],
        "",
        "## Trigger",
        "",
        f"```\n{br['trigger']}\n```",
        "",
        "## Blocking Behaviour",
        "",
        br["block"],
        "",
        "## Code Reference",
        "",
        f"`{br['code_ref']}`",
        "",
        "## Linked DocType",
        "",
        f"{mk(br['doctype'])}",
        "",
    ]
    return "\n".join(lines)


# ── MODULE NOTES ───────────────────────────────────────────────────────────────

MODULE_NOTES = {
    "IMM-04": {
        "title": "IMM-04 — Asset Installation & Commissioning",
        "actor": "HTM Technician / Biomed Engineer / VP Block2",
        "input": "Purchase Order + Vendor Serial Number",
        "output": "ERPNext Asset + Initial Document Set (IMM-05) + Commissioning Record (immutable)",
        "workflow": "Draft → Pending_Doc_Verify → Installing → Identification → Initial_Inspection → Clinical_Release → Clinical_Release_Success",
        "sla": "expected_installation_date — Daily SLA check in tasks.py",
        "primary_dt": "Asset Commissioning",
        "brs": ["VR-01", "VR-02", "VR-03", "VR-04", "VR-07", "GW-2", "BR-07"],
        "kpi": "TTI (Time to Install), Doc Completeness %, DOA Rate",
    },
    "IMM-05": {
        "title": "IMM-05 — Asset Document Management (NĐ 98/2021)",
        "actor": "TBYT Officer / Tổ HC-QLCL / Workshop Head",
        "input": "Document files (PDF/JPG/PNG) + Metadata",
        "output": "Compliant document repository with expiry alerting",
        "workflow": "Draft → Pending_Review → Active → Expiring_Soon → Expired → Archived",
        "sla": "check_document_expiry() daily at 00:30 — alerts at 90/60/30/0 days",
        "primary_dt": "Asset Document",
        "brs": ["IMM05-VR-01", "IMM05-VR-02", "IMM05-VR-07", "IMM05-VR-08", "IMM05-VR-10"],
        "kpi": "Doc Completeness % per Asset, Expiry count, Non-Compliant devices",
    },
    "IMM-08": {
        "title": "IMM-08 — Preventive Maintenance (PM)",
        "actor": "HTM Technician / Biomed Engineer",
        "input": "PM Schedule + Asset ID",
        "output": "PM Work Order (immutable after submit) + Next Due Date update",
        "workflow": "Scheduled → In Progress → Completed / Deferred",
        "sla": "next_due_date = completion_date + interval_days (BR-08)",
        "primary_dt": "PM Work Order (pending implementation)",
        "brs": ["BR-SLA-PM"],
        "kpi": "PM Compliance Rate, MTBF, On-time PM %",
    },
    "IMM-09": {
        "title": "IMM-09 — Corrective Maintenance (CM / Repair)",
        "actor": "HTM Technician / Workshop Head",
        "input": "Failure report or PM-triggered NC",
        "output": "CM Work Order → Repair Record (maps to Asset Repair) + source_pm_wo traceability",
        "workflow": "Open → In Progress → Pending Parts → Completed",
        "sla": "Response based on priority; auto-creates Material Request if stock = 0",
        "primary_dt": "Asset Repair (ERPNext) / CM Work Order (pending)",
        "brs": [],
        "kpi": "MTTR, Repair Cost, First-Time Fix Rate",
    },
    "IMM-11": {
        "title": "IMM-11 — Calibration",
        "actor": "Biomed Engineer / External Calibration Body",
        "input": "Device under test + Calibration certificate",
        "output": "Calibration record (immutable) + Certificate in IMM-05 + Return to Service gate",
        "workflow": "Scheduled → In Progress → Passed / Failed",
        "sla": "certificate expiry tracked in IMM-05",
        "primary_dt": "Calibration Record (pending implementation)",
        "brs": [],
        "kpi": "Calibration compliance %, Out-of-tolerance rate",
    },
    "IMM-12": {
        "title": "IMM-12 — Corrective Action / Incident Management",
        "actor": "Clinical Staff (reporter) / Workshop Head (owner)",
        "input": "Incident report with priority (P1-P3)",
        "output": "CAPA record + SLA breach notifications",
        "workflow": "Open → Acknowledged → Investigation → Resolved → Closed",
        "sla": "P1=120min response, P2=240min, P3=480min. Escalation L1→L2 at +30min",
        "primary_dt": "Corrective Work Order (pending implementation)",
        "brs": ["BR-12-P1"],
        "kpi": "SLA breach rate, CAPA closure rate, Repeat incident rate",
    },
}


def render_module_note(module_id: str, info: dict) -> str:
    brs = info.get("brs", [])
    lines = [
        "---",
        f'title: "{info["title"]}"',
        f'tags: [Module, AssetCore, Wave1, {module_id.replace("-","")}]',
        f'generated: "{GENERATED}"',
        "---",
        "",
        f"# {info['title']}",
        "",
        "```mermaid",
        "flowchart LR",
        f'    IN["📥 Input\\n{info["input"]}"] --> PROC["{module_id} Process"]',
        f'    PROC --> OUT["📤 Output\\n{info["output"]}"]',
        f'    PROC --> SLA["⏱ SLA\\n{info["sla"][:60]}..."]' if len(info["sla"]) > 60 else f'    PROC --> SLA["⏱ SLA\\n{info["sla"]}"]',
        "```",
        "",
        "## Summary",
        "",
        f"| Field | Value |",
        f"|-------|-------|",
        f"| **Module** | `{module_id}` |",
        f"| **Actor** | {info['actor']} |",
        f"| **Primary DocType** | {mk(info['primary_dt'])} |",
        f"| **SLA** | {info['sla']} |",
        f"| **KPI** | {info['kpi']} |",
        "",
        "## Input / Output",
        "",
        f"- **Input:** {info['input']}",
        f"- **Output:** {info['output']}",
        "",
        "## Workflow States",
        "",
        f"`{info['workflow']}`",
        "",
    ]

    if brs:
        lines += ["## Business Rules", ""]
        for br_id in brs:
            br = BUSINESS_RULES.get(br_id)
            if br:
                lines.append(f"- {mk(f'BR_{br_id}')} — {br['title']}")
        lines += [""]

    return "\n".join(lines)


# ── INDEX ──────────────────────────────────────────────────────────────────────

def render_index(all_doctypes: list[str]) -> str:
    modules = list(MODULE_NOTES.keys())
    brs     = list(BUSINESS_RULES.keys())

    lines = [
        "---",
        'title: "AssetCore — Obsidian MOC"',
        'tags: [Index, AssetCore, MOC]',
        f'generated: "{GENERATED}"',
        "---",
        "",
        "# AssetCore — Map of Content",
        "",
        f"> Wave 1 Scope: IMM-04, IMM-05, IMM-08, IMM-09, IMM-11, IMM-12  ",
        f"> Generated: `{GENERATED}`",
        "",
        "```mermaid",
        "flowchart TD",
        '    subgraph PROC["Processing"]',
        '        IMM04["[[IMM-04]]\\nInstallation"] --> IMM05["[[IMM-05]]\\nDocuments"]',
        '        IMM04 --> IMM09["[[IMM-09]]\\nRepair/CM"]',
        '        IMM08["[[IMM-08]]\\nPM"] -->|failure| IMM09',
        '        IMM09 -->|measuring device| IMM11["[[IMM-11]]\\nCalibration"]',
        '        IMM11 -->|fail| IMM12["[[IMM-12]]\\nCorrective Action"]',
        "    end",
        '    ASSET["[[Asset]]\\n(ERPNext Core)"] --- IMM04',
        '    ASSET --- IMM08',
        '    ASSET --- IMM09',
        "```",
        "",
        "## Modules",
        "",
    ]
    for m in modules:
        info = MODULE_NOTES[m]
        lines.append(f"- {mk(m)} — {info['title']}")
    lines += [""]

    lines += ["## DocTypes", ""]
    for dt in all_doctypes:
        lines.append(f"- {mk(dt)}")
    lines += [""]

    lines += ["## Business Rules", ""]
    for br_id, br in BUSINESS_RULES.items():
        lines.append(f"- {mk(f'BR_{br_id}')} — `{br['module']}` — {br['title']}")
    lines += [""]

    lines += [
        "## Quick Navigation",
        "",
        "| Category | Links |",
        "|----------|-------|",
        f"| Core DocTypes | {' · '.join(mk(d) for d in PRIMARY_DOCTYPES)} |",
        f"| Child Tables | {mk('Commissioning Checklist')} · {mk('Commissioning Document Record')} |",
        f"| QA | {mk('Asset QA Non Conformance')} · {mk('Expiry Alert Log')} |",
        f"| Modules | {' · '.join(mk(m) for m in modules)} |",
        "",
    ]

    return "\n".join(lines)


# ── MAIN EXPORT ────────────────────────────────────────────────────────────────

def export_all():
    """
    bench --site [site] execute assetcore.export_to_obsidian.export_all
    """
    frappe.set_user("Administrator")
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print(f"\n{'='*65}")
    print("AssetCore → Obsidian Vault Exporter")
    print(f"{'='*65}")
    print(f"Vault: {VAULT}")
    print(f"Time:  {ts}\n")

    all_doctypes = PRIMARY_DOCTYPES + EXTRA_DOCTYPES
    exported_dts = []

    # ── 1. DocType notes ────────────────────────────────────────────────────
    print("[1/4] Exporting DocType notes...")
    for dt in all_doctypes:
        if not frappe.db.exists("DocType", dt):
            print(f"  ⚠️  DocType '{dt}' not found — skipping")
            continue
        fields   = get_meta_fields(dt)
        content  = render_doctype(dt, fields)
        out_path = VAULT / "doctypes" / f"{dt}.md"
        write_file(out_path, content)
        exported_dts.append(dt)

    # ── 2. Business Rule notes ──────────────────────────────────────────────
    print("\n[2/4] Exporting Business Rule notes...")
    for br_id, br in BUSINESS_RULES.items():
        content  = render_business_rule(br_id, br)
        out_path = VAULT / "business_rules" / f"BR_{br_id}.md"
        write_file(out_path, content)

    # ── 3. Module notes ─────────────────────────────────────────────────────
    print("\n[3/4] Exporting Module notes...")
    for module_id, info in MODULE_NOTES.items():
        content  = render_module_note(module_id, info)
        out_path = VAULT / "modules" / f"{module_id}.md"
        write_file(out_path, content)

    # ── 4. Index ────────────────────────────────────────────────────────────
    print("\n[4/4] Generating index...")
    index_content = render_index(exported_dts)
    write_file(VAULT / "00_INDEX.md", index_content)

    # ── Summary ─────────────────────────────────────────────────────────────
    total = len(exported_dts) + len(BUSINESS_RULES) + len(MODULE_NOTES) + 1
    print(f"\n{'='*65}")
    print(f"✅ Export complete — {total} files written")
    print(f"   DocTypes:       {len(exported_dts)}")
    print(f"   Business Rules: {len(BUSINESS_RULES)}")
    print(f"   Modules:        {len(MODULE_NOTES)}")
    print(f"   Index:          1")
    print(f"\nVault location: {VAULT}")
    print(f"Open in Obsidian: File → Open vault → {VAULT}")
    print(f"{'='*65}\n")

    return {
        "vault": str(VAULT),
        "files": total,
        "doctypes": exported_dts,
    }
