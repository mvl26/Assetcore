---
description: Draft a formal requirement for an AssetCore feature
argument-hint: <feature>
---

Draft a formal **requirement specification** for: `$ARGUMENTS`

**Requirement Format:**

```text
REQ-ID: IMM-XX-FRxx / NFRxx
Title: <short title>
Type: Functional / Non-Functional / Regulatory
Priority: Critical / High / Medium / Low
Module: IMM-XX
Actor: <primary role>
```

**Sections:**

1. **Mô tả (Description)** — what the system must do, in plain language
2. **Điều kiện kích hoạt (Trigger)** — what event or condition starts this
3. **Luồng chính (Main Flow)** — numbered steps (actor → system response)
4. **Luồng thay thế (Alternative Flows)** — error cases, cancellations
5. **Điều kiện tiên quyết (Preconditions)** — what must be true before
6. **Điều kiện kết thúc (Postconditions)** — what is true after success
7. **Quy tắc nghiệp vụ (Business Rules)** — constraints, VR-XX references
8. **Dữ liệu (Data)** — input fields, output fields, linked DocTypes
9. **Audit Trail** — what record must be created as evidence
10. **KPI Impact** — which metrics does this feature affect

**Regulatory Basis:** Which ISO 13485 clause or NĐ98 article mandates this?
