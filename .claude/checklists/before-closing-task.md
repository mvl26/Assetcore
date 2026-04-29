# Before Closing a Task Checklist

Run before marking any development task as Done.

## 1. Code Quality

- [ ] No logic in controller — moved to service layer
- [ ] All functions have type hints
- [ ] No hardcoded strings (IDs, DocType names use constants)
- [ ] Files under 200 lines (split if needed)

## 2. Tests

- [ ] Unit test passes: `bench --site miyano run-tests`
- [ ] UAT test case exists and is PASS
- [ ] No regression in existing test cases from this module

## 3. API

- [ ] Endpoint returns `{success, data}` or `{success, error, code}`
- [ ] `@frappe.whitelist()` decorator present
- [ ] Errors use Vietnamese messages

## 4. Audit Trail

- [ ] State transition creates Lifecycle Event record
- [ ] Approval actions record `approved_by` + `approval_date`
- [ ] Rejection records reason

## 5. Documentation

- [ ] Relevant UAT script updated if flow changed
- [ ] CLAUDE.md updated if new pattern introduced
- [ ] API contract updated if new endpoint added

## 6. Migration

- [ ] `bench --site miyano migrate` run successfully
- [ ] No migration errors or warnings
