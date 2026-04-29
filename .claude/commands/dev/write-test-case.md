---
description: Write UAT test cases for an AssetCore IMM module or feature
argument-hint: <feature or module>
---

Write complete **UAT test cases** for: `$ARGUMENTS`

Output format for each test case:

```text
TC-XX | <Title>
Actor: <role>
Precondition: <what must exist>
Steps:
  1. <action>
  2. <action>
Expected Result: <what the system does>
Validation: <field/state/record to verify>
Pass Criteria: <specific measurable condition>
Priority: Critical / High / Medium / Low
```

**Coverage Requirements:**

- Happy path (correct data, authorized user) — Critical
- Authorization (wrong role attempt) — each restricted action
- Validation rules (missing required fields, invalid formats)
- State transitions (each workflow transition)
- Edge cases (duplicate records, boundary dates, empty results)
- Audit trail (records created with correct fields)
- SLA behavior (if applicable)
- Integration (linked DocTypes updated correctly)

**Output Structure:**

1. Test summary table (TC-ID, Title, Priority, Status=PENDING)
2. Full test case details
3. Test data setup instructions
4. Pass/Fail tally template

**Naming:** `TC-<MODULE>-<sequence>` — e.g., `TC-IMM05-01`
