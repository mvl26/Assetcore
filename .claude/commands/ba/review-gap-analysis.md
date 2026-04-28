---
description: Review gaps between AssetCore current state and a target requirement
argument-hint: <scope>
---

Perform a **gap analysis** for: `$ARGUMENTS`

**Gap Analysis Format:**

For each requirement area:

| Area | Requirement | Current State | Gap | Effort | Priority |
| --- | --- | --- | --- | --- | --- |
| ... | Must have X | System does Y / Not implemented | Delta | S/M/L | Critical/High/Medium |

**Categories to Review:**

- **Functional gaps** — features required but not built
- **Data model gaps** — fields or DocTypes missing
- **Workflow gaps** — states or transitions not implemented
- **API gaps** — endpoints needed but absent
- **UI gaps** — screens or actions missing
- **QMS gaps** — audit trail, document control, CAPA not wired
- **Integration gaps** — FHIR / HIS connections missing
- **Regulatory gaps** — NĐ98 / WHO HTM requirements not met

**Output:**

1. Gap register table sorted by Priority
2. Total effort estimate (S=0.5d, M=2d, L=5d)
3. Recommended remediation sequence
4. Items that block Wave 1 UAT sign-off
