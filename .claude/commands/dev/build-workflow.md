---
description: Build a Frappe Workflow JSON definition for an AssetCore DocType
argument-hint: <DocType name>
---

Design and output a complete **Frappe Workflow** for the DocType: `$ARGUMENTS`

**1. Workflow States**

List every state with:

- State name (matches Select field values)
- Style: Success / Warning / Danger / Primary / Default
- `doc_status`: 0=Draft, 1=Submitted, 2=Cancelled
- `update_field` and `update_value` if workflow sets a field on entry

**2. Workflow Transitions**

For each transition:

```text
Action: <button label>
From State: <state>
To State: <state>
Allowed Roles: <roles>
Condition (optional): <Python expression>
```

**3. Role Matrix Summary**

Table showing which roles trigger which transitions.

**4. Frappe JSON Output**

Complete workflow JSON importable via Frappe Workflow DocType or saved as `assetcore/fixtures/<name>_workflow.json`.

**5. Implementation Notes**

- Which field stores the workflow state?
- Does the DocType need `Is Submittable = Yes`?
- What controller hooks are needed (`on_submit`, `before_submit`)?
- Any `doc_status` change affecting child records?

**Constraints:**

- No backwards transitions without justification
- Every terminal state must be reachable from at least one path
- Roles: CMMS Admin, Biomed Engineer, HTM Technician, Workshop Head, Tổ HC-QLCL, Clinical User
