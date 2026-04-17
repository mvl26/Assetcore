---
description: Build an audit trail completeness check for an AssetCore DocType or module
---

Build an **audit trail completeness check** for: `$ARGUMENTS`

**Output:**

**1. Audit Trail Matrix**

For each action in the module's lifecycle:

| Action | Who | When | Record Created | Fields Captured | Gap Risk |
| --- | --- | --- | --- | --- | --- |
| Create | Actor | Timestamp | HS record + Version | all fields | None |
| Approve | Approver role | Timestamp | Lifecycle Event | from/to state, actor | None |
| ... | ... | ... | ... | ... | ... |

**2. Frappe Version DocType Coverage**

Which fields are tracked by `track_changes = 1`? Which need custom logging?

**3. Custom Lifecycle Event Entries**

For each state transition not covered by Frappe's Version:

```python
frappe.get_doc({
    "doctype": "Lifecycle Event",
    "asset": self.asset_ref,
    "event_type": "<type>",
    "from_state": prev_state,
    "to_state": self.workflow_state,
    "actor": frappe.session.user,
    "root_record": f"{self.doctype}/{self.name}",
}).insert(ignore_permissions=True)
```

**4. Audit Trail Test Cases**

For each critical action: verify record exists with correct fields after the action.

**5. Retention Policy**

| Record Type | Retention | Storage |
| --- | --- | --- |
| HS (operational records) | 10 years | MariaDB + attachment store |
| Version history | Permanent | Frappe Version DocType |
| Lifecycle Events | 10 years | MariaDB |
