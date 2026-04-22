---
name: erpnext-doctype-designer
description: Design complete Frappe/ERPNext DocType specs for AssetCore domain entities — fields, naming, permissions, workflow, controller hooks
type: skill
---

# ERPNext DocType Designer — AssetCore

## What This Skill Does

Given a domain entity name, produce a **complete, implementation-ready DocType specification** for Frappe v15/ERPNext, aligned with AssetCore's HTM lifecycle architecture.

## Input

User provides one of:

- Entity name: `"Asset Commissioning"`
- Entity + module: `"Work Order for IMM-09 Repair"`
- Short description: `"Track PM schedules linked to assets"`

## Output Format

### 1. DocType Metadata

```text
DocType: <name>
Module: AssetCore
Is Submittable: yes/no
Track Changes: yes
Has Attachments: yes/no
Naming: <rule — e.g., "ACC-.YYYY.-.#####" or "field:asset_ref">
```

### 2. Field Definitions Table

| # | fieldname | fieldtype | label | reqd | in_list_view | options/link_to |
|---|-----------|-----------|-------|------|--------------|-----------------|

Include ALL fields: Section Breaks, Column Breaks, data fields, Link, Select, Date/Datetime, Table (child), Attach, Check.

### 3. Child Tables (if any)

Define each child DocType separately with its own field list.

### 4. Select Field Options

List all allowed values for every Select field.

### 5. Naming Rule

Explain the autoname pattern and why.

### 6. Permissions Table

| Role | Read | Write | Create | Delete | Submit | Cancel |
|------|------|-------|--------|--------|--------|--------|

Roles: CMMS Admin, Biomed Engineer, HTM Technician, Workshop Head, Tổ HC-QLCL, Clinical User.

### 7. Workflow States

```text
States: Draft → Pending_Review → Active | Rejected → Archived
Transitions:
  Submit:  [roles] Draft → Pending_Review
  Approve: [roles] Pending_Review → Active
  Reject:  [roles] Pending_Review → Rejected
  Archive: [roles] Active → Archived
```

### 8. Controller Hooks (Python)

```python
# assetcore/doctype/<snake_name>/<snake_name>.py
class <DocTypeName>(Document):
    def validate(self): ...      # constraints to check
    def before_insert(self): ... # defaults to set
    def on_submit(self): ...     # lifecycle event to fire
    def on_cancel(self): ...     # what to reverse
```

Describe each hook's **purpose** — do NOT write full logic here (belongs in service layer).

### 9. Linked DocTypes

List all Link fields with target DocType and cardinality.

### 10. Bench Commands

```bash
bench --site miyano migrate
bench --site miyano clear-cache
```

### 11. Audit Trail Notes

What fields change at each state transition? Any custom log entries beyond Frappe's Version DocType?

## Domain Rules (Always Apply)

- Never modify ERPNext core DocTypes — only extend or create new
- Every operational record must have: `asset_ref → Asset`, `actor` (owner/user), `timestamp`
- Work Orders are the action engine — no action outside a Work Order (IMM-07 to IMM-12)
- Naming prefix convention: `ACC-` commissioning, `WO-` work order, `MP-` maintenance plan, `IR-` incident
- `docstatus`: 0=Draft, 1=Submitted, 2=Cancelled — use Submittable for formal records
- SLA fields: `sla_deadline`, `sla_status` (On Time / Breached / At Risk)
- All records must be auditable: no action without a traceable record

## Step-by-Step Execution

1. Identify entity and IMM module (Planning/Deployment/Operation/End-of-Life)
2. Determine category: Master, Operational, or Governance
3. Draft fields: name, asset_ref, status, actor, timestamps first
4. Add domain-specific fields
5. Define child tables for line items
6. Map workflow to lifecycle states from CLAUDE.md
7. Assign permissions per role matrix
8. Define controller hook responsibilities (NOT implementation)
9. List audit trail requirements
10. Output all sections in order
