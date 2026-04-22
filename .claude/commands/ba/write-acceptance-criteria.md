---
description: Write acceptance criteria for an AssetCore user story or requirement
---

Write **acceptance criteria** for: `$ARGUMENTS`

**Format — Gherkin (Given/When/Then):**

```text
Scenario: <title>
  Given <precondition / system state>
  And <additional context>
  When <actor performs action>
  Then <expected outcome>
  And <additional assertions>
```

**Coverage Checklist:**

Write scenarios for ALL of the following:

- [ ] Happy path — valid data, authorized user, correct outcome
- [ ] Authorization failure — wrong role gets error
- [ ] Validation failure — missing/invalid field gets Vietnamese error message
- [ ] State guard — action rejected in wrong workflow state
- [ ] Audit trail — correct record created with all required fields
- [ ] Integration — linked DocType updated correctly
- [ ] Edge case — boundary condition, empty result, duplicate

**Non-Functional Acceptance Criteria:**

- Response time: API must return within 2 seconds under normal load
- Audit: Every state change must create a traceable record
- Access control: Role restrictions enforced without bypass

**Definition of Done (DoD):**

- [ ] All Gherkin scenarios pass in UAT
- [ ] No regression in existing test cases
- [ ] QMS document (BM/HS) created for this feature
