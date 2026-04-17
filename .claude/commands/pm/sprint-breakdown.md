---
description: Break down a sprint goal into tasks for AssetCore development
---

Break down this sprint goal into tasks: `$ARGUMENTS`

**Sprint Breakdown Format:**

```text
Sprint Goal: <one sentence>
Duration: 2 weeks
Module: IMM-XX
```

**Task List:**

For each task:

```text
TASK-XX | <Title>
Type: Backend / Frontend / Test / Docs / DevOps
Estimate: <story points>
Owner: <role — Dev / QA / BA>
Depends on: <TASK-XX if any>
Definition of Done:
  - [ ] Code written and reviewed
  - [ ] Unit test passing
  - [ ] UAT test case written
  - [ ] API contract updated (if new endpoint)
  - [ ] No regressions in existing UAT
```

**Sequence Diagram** (text):

```text
Day 1-3: Backend DocType + API
Day 3-5: Frontend data layer
Day 5-8: UI components
Day 8-10: Integration test + UAT
Day 10: Demo + docs
```

**Risk Flags:** List any tasks with High technical risk and mitigation approach.
