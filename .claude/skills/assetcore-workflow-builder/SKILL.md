---
name: assetcore-workflow-builder
description: Design or modify a Frappe Workflow JSON for AssetCore — choose states, transitions, allowed roles, and docstatus mapping for an IMM module. Use whenever the user asks to "tạo workflow", "thêm state", "transition cho IMM-XX", "approval flow", "state machine", "thay đổi luồng duyệt", "allow_edit role", or any state-machine modeling for a DocType. Strongly use this skill if the user mentions docstatus 0/1/2, workflow_state, or state types like Warning/Success/Danger.
---

# AssetCore Workflow Builder

A Frappe Workflow is a JSON file at `assetcore/assetcore/workflow/<name>.json` that defines a state machine for a DocType. AssetCore ships workflow JSON files in `assetcore/assetcore/workflow/`. All workflows must be registered in fixtures AND smoke-tested in `tests/test_workflows.py:EXPECTED_WORKFLOWS`. A workflow JSON that exists in the repo but is missing from fixtures will NOT be imported on fresh sites — this is the most common deployment gap. When you add or modify a workflow, always update all three: the JSON, `hooks.py` fixtures, and `EXPECTED_WORKFLOWS`.

## Anatomy of a workflow

```json
{
  "doctype": "Workflow",
  "name": "IMM-09 Repair Workflow",
  "workflow_name": "IMM-09 Repair Workflow",
  "document_type": "Asset Repair",
  "workflow_state_field": "workflow_state",
  "is_active": 1,
  "send_email_alert": 0,
  "states": [...],
  "transitions": [...]
}
```

**Required:**
- `name === workflow_name` — Frappe quirk; both must match.
- `document_type` — the DocType this state machine governs. Must exist.
- `workflow_state_field` — the DocType must have a Data field with this name (default: `workflow_state`). Add it as `read_only: 1`.
- `is_active: 1` so Frappe enforces it.

## States

```json
{
  "state": "Open",
  "doc_status": "0",
  "allow_edit": "IMM Workshop Lead",
  "type": "Warning"
}
```

| Field | Meaning |
|---|---|
| `state` | Display name; matches the value stored in `workflow_state` |
| `doc_status` | Frappe lifecycle stage: `"0"` Draft, `"1"` Submitted, `"2"` Cancelled |
| `allow_edit` | Role allowed to edit fields while doc is in this state |
| `type` | UI badge color: `Success`, `Warning`, `Danger`, `Primary`, `Inverse` |

**Type convention:**
- `Success` → progress states (Diagnosing, In Repair, Completed)
- `Warning` → waiting states (Open, Pending Parts, Pending Inspection)
- `Danger` → terminal-bad (Cancelled, Cannot Repair, Rejected, Out of Service)

## Transitions

```json
{
  "state": "Open",
  "action": "Phân công KTV",
  "next_state": "Assigned",
  "allowed": "IMM Workshop Lead",
  "condition": "doc.assigned_to"
}
```

| Field | Meaning |
|---|---|
| `state` | Current state (must exist in `states`) |
| `action` | Vietnamese button label shown in desk + read by FE |
| `next_state` | Target state (must exist in `states`) |
| `allowed` | Role permitted to perform this transition |
| `condition` | Optional Python expression evaluated against `doc` |

## docstatus rule (CRITICAL — Frappe enforces)

Valid transitions between docstatus values:
- `0 → 0` (Draft to Draft)
- `0 → 1` (Draft to Submitted)
- `1 → 1` (Submitted to Submitted — only if doc is still amendable)
- `1 → 2` (Submitted to Cancelled)

**Invalid (Frappe will reject the workflow):**
- `0 → 2` (cannot cancel a draft via workflow — delete instead)
- `1 → 0` (cannot un-submit)
- `2 → anything` (cancelled is terminal)

A test in `tests/test_workflows.py` enforces this. Run it before claiming done.

## Naming convention

| Pattern | Example |
|---|---|
| Workflow file | `imm_09_repair_workflow.json` |
| Workflow name | `IMM-09 Repair Workflow` |
| State field on DocType | `workflow_state` (Data, read_only) |

## Adding the workflow_state field to the DocType

The DocType must have a field named whatever `workflow_state_field` says. Add this to its `.json`:

```json
{
  "fieldname": "workflow_state",
  "label": "Trạng thái workflow",
  "fieldtype": "Link",
  "options": "Workflow State",
  "read_only": 1,
  "hidden": 1,
  "no_copy": 1
}
```

`hidden: 1` because users see the human `status` field — `workflow_state` is plumbing.

## Registering the workflow as a fixture

In `assetcore/hooks.py`, add the workflow name to the fixtures list:

```python
fixtures = [
    # ...
    {"dt": "Workflow", "filters": [["name", "in", [
        "IMM-09 Repair Workflow",
        "<your new workflow name>",
    ]]]},
    {"dt": "Workflow State", "filters": [["name", "in", [
        # all unique state names across all workflows
    ]]]},
    {"dt": "Workflow Action Master", "filters": [["name", "in", [
        # all unique action labels (Vietnamese button labels)
    ]]]},
]
```

**All three lists must be updated together.** Missing any one of them breaks fresh-site provisioning silently:
- Missing from `Workflow` → workflow doesn't import
- Missing from `Workflow State` → state resets to blank after import
- Missing from `Workflow Action Master` → transition button label disappears

Add **every new** state/action to all three lists in the same commit.

Then add a smoke test entry in `tests/test_workflows.py` `EXPECTED_WORKFLOWS`:
```python
"IMM-XX Workflow": {"doctype": "<DocType>", "min_states": N, "min_transitions": M},
```

## Sync with service-layer status enum

The `state` strings in the workflow are the same strings as the `XStatus` class in `services/immXX.py`. **They must stay identical.**

```python
class RepairStatus:
    OPEN = "Open"
    ASSIGNED = "Assigned"
    DIAGNOSING = "Diagnosing"
    # ... matches imm_09_repair_workflow.json states exactly
```

When you add a state to the workflow, also add it to the service constant class, also extend the FE type union in `src/api/<module>.ts`. Three places, in sync — that's the cost.

## Common pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| Workflow doesn't appear on form | Forgot `is_active: 1` or DocType lacks `workflow_state` field | Add both |
| `docstatus_validation` test fails | Made `0 → 2` or `1 → 0` transition | Reroute via valid path; cancel uses `0 → 1 → 2` |
| Transition button doesn't show for user | Role mismatch in `allowed` | Check user has the role; remember role == role profile is not the same |
| State label changes to wrong value after save | Missing entry in `Workflow State` fixture | Add the state name to fixture filter; reload |
| Migration fails on fresh site | New action label missing from `Workflow Action Master` fixture | Add the Vietnamese action string |
| Workflow JSON exists in repo but missing from prod | Workflow exists at `assetcore/workflow/*.json` but is not listed in `hooks.py` fixtures | Add to ALL THREE fixture filters (Workflow, State, Action) |
| Gate / SLA service function never fires | Function exists in `immXX.py` but not wired into `doc_events` in `hooks.py` | Add the `doc_events` entry; `bench migrate` to reload |
| `EXPECTED_WORKFLOWS` count mismatch | New workflow added but test file not updated | Add entry with `min_states` and `min_transitions` matching the JSON |

## Build sequence

1. Sketch the states + happy path on paper.
2. Decide the docstatus mapping (Draft `0` for active states, Submitted `1` for finalization, Cancelled `2` only via `1 → 2`).
3. Write the JSON. Mirror an existing one (`imm_09_repair_workflow.json` is a good template — covers branching + cancel + terminal-bad).
4. Add `workflow_state` field to the DocType JSON if missing.
5. Add the new state/action names to `hooks.py` fixtures.
6. Add the workflow to `EXPECTED_WORKFLOWS` in `tests/test_workflows.py` with state/transition counts.
7. Run `bench --site <site> migrate` (so workflow imports), then `bench --site <site> run-tests --module assetcore.tests.test_workflows`.
8. Verify in desk: open a record, see the badge + transition buttons.

## Where to look for live examples

- `assetcore/assetcore/workflow/imm_09_repair_workflow.json` — branching with mid-flow cancel
- `assetcore/assetcore/workflow/imm_04_workflow.json` — long happy path (11 states, 20 transitions)
- `assetcore/assetcore/workflow/ac_asset_lifecycle_workflow.json` — entity-level lifecycle (vs. work order)
- `assetcore/tests/test_workflows.py` — the validator that all workflows must pass

---

## Cross-skill conventions

Read [`/.claude/skills/CONVENTIONS.md`](../CONVENTIONS.md) for project-wide rules. Especially relevant to this skill:

- §1. Naming Conventions — workflow state names use Title Case with spaces, NOT underscores
- §10. Forbidden actions — never bypass state machine via `frappe.db.set_value`

### Module-specific gotchas
- IMM-04 has tech debt: `Clinical Release` (code) vs `Clinical_Release` (DB) — when fixing, audit all string comparisons
- Existing live workflows: imm-04, imm-05, imm-08, imm-09, imm-11, imm-12 (Wave 1) + imm-01, imm-02, imm-03 (Wave 2) + imm-06, imm-15, imm-16 (Wave 2/3 scaffolded)
- Workflow JSON `document_type` must EXACTLY match DocType name (case-sensitive)
- `doc_status: "1"` for terminal-success states; `"2"` for cancelled-after-submit; `"0"` otherwise
