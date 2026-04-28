---
description: Implement a validation rule in AssetCore backend and/or frontend
argument-hint: <rule description>
---

Implement the following **validation rule**: `$ARGUMENTS`

**Backend (Python — Frappe Controller)**

```python
def validate(self):
    self._validate_<rule_name>()

def _validate_<rule_name>(self):
    if <invalid_condition>:
        frappe.throw(_("Vietnamese error message"))
```

Rules:

- Use `frappe.throw()` — never `raise Exception`
- Add `# VR-XX` comment if linked to a spec requirement
- One method per rule, focused on a single invariant

**Frontend (TypeScript — Vue 3)**

```typescript
function validate<RuleName>(): string | null {
  // return null if valid, Vietnamese message if invalid
}
```

Wire to `@blur` on the field and call in `validateAll()` before POST.

**Test Case**

One positive test (valid data passes) and one negative test (invalid data caught with correct message).

**Where to Add**

- Backend: `assetcore/doctype/<name>/<name>.py` or `assetcore/api/<module>.py`
- Frontend: `frontend/src/views/<View>.vue` or `frontend/src/components/<Component>.vue`
