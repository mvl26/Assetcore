---
name: assetcore-doctype-designer
description: Design or modify a Frappe DocType for AssetCore — choose fieldnames, types, links, child tables, naming series, permissions, and controller hooks. Use this whenever the user asks to "tạo DocType mới", "thêm field", "thiết kế bảng", "child table cho ...", "scaffold AC X", "extend ERPNext X without modifying core", or any data-modeling question. Strongly use this skill if the user mentions DocType, .json schema, Custom Field, Link field, Child Table, autoname, or naming_series — even if they don't say "DocType".
---

# AssetCore DocType Designer

Frappe DocTypes are the data model. AssetCore has ~80 DocTypes; consistency matters more than cleverness. Follow these conventions exactly.

## Naming conventions

| Prefix | Meaning | Example |
|---|---|---|
| `AC ` | AssetCore-owned core entity (replaces ERPNext one) | `AC Asset`, `AC Supplier`, `AC Location` |
| `IMM ` | IMM module-specific governance / reference data | `IMM SLA Policy`, `IMM Audit Trail`, `IMM CAPA Record` |
| (no prefix) | Operational records | `Asset Repair`, `Asset Commissioning`, `Incident Report` |

**Folder is snake_case of the name:** `AC Asset` → `assetcore/assetcore/doctype/ac_asset/`. Always lowercase + underscores. The 4 files inside:

```
ac_asset/
├── ac_asset.json   # schema
├── ac_asset.py     # controller (Document subclass)
├── ac_asset.js     # client script (form-side hooks; minimal)
└── __init__.py     # empty
```

## JSON schema template (minimum fields)

```json
{
  "name": "Asset Repair",
  "doctype": "DocType",
  "module": "AssetCore",
  "engine": "InnoDB",
  "is_submittable": 1,
  "track_changes": 1,
  "track_seen": 1,
  "autoname": "format:WO-RP-{YYYY}-{####}",
  "title_field": "name",
  "search_fields": "asset_ref,assigned_to,status",
  "sort_field": "modified",
  "sort_order": "DESC",
  "fields": [ /* see field templates below */ ],
  "permissions": [ /* see permissions section */ ]
}
```

**Always set:**
- `module: "AssetCore"` (required so Frappe loads it).
- `track_changes: 1` — audit trail at row level.
- `is_submittable: 1` for any record that has approval or final-state transitions.
- `autoname: "format:..."` — never rely on hash naming. Use a prefix that telegraphs the module: `WO-PM-`, `WO-RP-`, `CAL-`, `DOC-`, `IR-`.

## Field templates

### Link field
```json
{
  "fieldname": "asset_ref",
  "label": "Thiết bị",
  "fieldtype": "Link",
  "options": "AC Asset",
  "reqd": 1,
  "in_list_view": 1,
  "in_standard_filter": 1
}
```

### Select (status)
```json
{
  "fieldname": "status",
  "label": "Trạng thái",
  "fieldtype": "Select",
  "options": "Open\nAssigned\nIn Progress\nCompleted\nCancelled",
  "default": "Open",
  "reqd": 1,
  "read_only": 1,
  "in_list_view": 1
}
```
**Status is read-only at the form level** — only workflow + service can change it. Never let users edit it directly.

### Datetime (occurrence)
```json
{
  "fieldname": "open_datetime",
  "label": "Thời điểm mở",
  "fieldtype": "Datetime",
  "read_only": 1
}
```
Set in `before_insert`. Never let user edit timestamps; they're audit data.

### Currency
```json
{
  "fieldname": "total_parts_cost",
  "label": "Tổng chi phí vật tư",
  "fieldtype": "Currency",
  "read_only": 1,
  "default": "0"
}
```

### Child table
```json
{
  "fieldname": "spare_parts_used",
  "label": "Vật tư đã dùng",
  "fieldtype": "Table",
  "options": "AC Spare Part Usage Row"
}
```
Child DocType naming: `<Parent> Row` or `<Domain> Row`. Set `istable: 1` on the child JSON.

### Section break / column break
Group related fields under section breaks for usable forms:
```json
{ "fieldtype": "Section Break", "label": "Thông tin chính" },
{ "fieldtype": "Column Break" }
```

## Lifecycle / audit integration (mandatory for asset-touching DocTypes)

Any DocType that mutates an `AC Asset`'s status must:

1. Have a `Link` field to `AC Asset` (typically named `asset_ref`).
2. In the right hook (`on_submit` for finalization, `on_update_after_submit` for state inside `1`), either:
   - Call `transition_asset_status(asset_ref, target_status, root_record=self.name)` from `assetcore.services.imm00` (combined: flips asset status AND writes an `IMM Audit Trail` row).
   - Or call `log_audit_event(...)` from `assetcore.utils.lifecycle` directly when no asset-status change is needed (just a record of the event).

`IMM Audit Trail` is a SHA-256-chained log: each row hashes its content together with the previous row's hash. **Don't write to the table directly** — always go through `log_audit_event`, which reads the previous hash, computes the new one, and inserts atomically. Tampering with one row breaks the chain for every subsequent row, which is the whole point.

`Asset Lifecycle Event` is a simpler table used by the FE timeline component; it's optional and can be derived from audit trail. The compliance source of truth is `IMM Audit Trail`.

## Permissions block

Define DocPerm in the JSON for primary roles. Follow the pattern from existing DocTypes:

```json
"permissions": [
  {
    "role": "IMM System Admin",
    "read": 1, "write": 1, "create": 1, "delete": 1,
    "submit": 1, "cancel": 1, "amend": 1,
    "report": 1, "export": 1, "print": 1, "email": 1, "share": 1
  },
  {
    "role": "IMM Workshop Lead",
    "read": 1, "write": 1, "create": 1,
    "submit": 1,
    "report": 1, "export": 1, "print": 1
  },
  {
    "role": "IMM Biomed Technician",
    "read": 1, "write": 1, "create": 1,
    "report": 1, "print": 1
  }
]
```

For finer matrices (owner-scoped, level 1 fields, etc.) use the runtime setup at `assetcore/setup/setup_permissions.py` — keeps JSON clean and code-driven.

**Never** add `System Manager` to a non-admin DocType. IMM users should never need it.

## Controller (.py) skeleton

```python
import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class AssetRepair(Document):
    def before_insert(self) -> None:
        from assetcore.services.imm09 import (
            validate_repair_source, validate_asset_not_under_repair,
        )
        validate_repair_source(self)
        validate_asset_not_under_repair(self.asset_ref)
        self.open_datetime = now_datetime()

    def validate(self) -> None:
        from assetcore.services.imm09 import validate_spare_parts_stock_entries
        validate_spare_parts_stock_entries(self)

    def on_submit(self) -> None:
        from assetcore.services.imm09 import on_repair_complete
        on_repair_complete(self)
```

Hooks in order: `autoname → before_insert → validate → on_insert → on_update → before_submit → on_submit → on_cancel`. Lazy-import services to avoid circular deps.

## ERPNext extension rule

CLAUDE.md §19 says "không modify ERPNext core". To extend an ERPNext concept (Asset, Supplier, Item):

- **DON'T** edit ERPNext's JSON or add Custom Fields on `Asset`.
- **DO** create a parallel `AC <X>` DocType that owns AssetCore data first-class.
- If both must coexist temporarily, use a Link from `AC X` → ERPNext `X` (one-way, optional).

Reference: `patches/v3_0/001_migrate_from_v2.py` — dropped Custom Fields and sidecar DocTypes precisely to enforce this rule.

## Validation checklist before claiming the DocType is done

- [ ] `module: "AssetCore"` set
- [ ] `autoname` uses readable prefix
- [ ] `track_changes: 1`
- [ ] `is_submittable: 1` if has finalization step
- [ ] All status fields are `read_only: 1`
- [ ] All timestamps are `read_only: 1`
- [ ] Has Link to `AC Asset` (or parent) if asset-related
- [ ] Permissions cover SYS_ADMIN + at least 2 operational roles
- [ ] Controller hooks delegate to service layer, no inline logic
- [ ] If status changes asset state: `log_audit_event(...)` (or `transition_asset_status(...)`) called in the right hook
- [ ] Workflow JSON exists in `assetcore/workflow/` if state machine has >2 active states
- [ ] Smoke test added in `tests/` (use `assetcore-tester` skill)

## Where to look for live examples

- `assetcore/assetcore/doctype/asset_repair/asset_repair.json` — submittable + child tables + workflow-driven
- `assetcore/assetcore/doctype/ac_asset/ac_asset.json` — core entity with many fields
- `assetcore/assetcore/doctype/asset_lifecycle_event/asset_lifecycle_event.json` — append-only audit pattern
- `assetcore/assetcore/doctype/asset_repair/asset_repair.py` — controller with ERPNext compat shims
