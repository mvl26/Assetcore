---
description: Prioritize AssetCore backlog items for the next sprint
argument-hint: <backlog items>
---

Prioritize the following backlog items for AssetCore: `$ARGUMENTS`

**Scoring Framework (MoSCoW + WSJF):**

For each item, assess:

- **Value:** Clinical impact / compliance risk / user pain (1–5)
- **Urgency:** Regulatory deadline / sprint dependency (1–5)
- **Effort:** Story points estimate (1, 2, 3, 5, 8, 13)
- **Risk:** Technical uncertainty / integration complexity (Low/Medium/High)
- **WSJF Score:** (Value + Urgency) / Effort

**Output Table:**

| ID | Item | Value | Urgency | Effort | Risk | WSJF | Priority |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ... | ... | ... | ... | ... | ... | ... | Must/Should/Could/Won't |

**Wave 1 Scope Constraint:** Flag any item outside IMM-04, IMM-05, IMM-08, IMM-09, IMM-11, IMM-12.

**Dependencies:** List any items that block or are blocked by others.

**Recommendation:** Top 3 items for next sprint with justification.
