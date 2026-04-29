---
description: Build a requirements traceability matrix for an AssetCore module
argument-hint: <module>
---

Build a **Requirements Traceability Matrix (RTM)** for: `$ARGUMENTS`

**RTM Table:**

| REQ-ID | Requirement | Regulatory Basis | DocType | API Endpoint | UI Component | Test Case | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| IMM-XX-FR01 | ... | ISO §X.X / NĐ98 Điều X | ... | ... | ... | TC-XX-01 | Implemented / Pending / Gap |

**Traceability Directions:**

- Forward: Requirement → Implementation → Test (are all requirements covered?)
- Backward: Test → Implementation → Requirement (are all tests justified?)

**Coverage Summary:**

```text
Total Requirements: XX
Implemented: XX (XX%)
Pending: XX
Gap (no implementation): XX
Test Coverage: XX% of requirements have at least one test case
```

**Regulatory Coverage:**

List each ISO 13485 clause and NĐ98 article referenced, and which REQ-IDs satisfy it.

**Output file suggestion:** `docs/sprints/IMM-XX_RTM.md`
