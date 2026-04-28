---
description: Review risks for an AssetCore feature, sprint, or release
argument-hint: <feature, sprint or release>
---

Review risks for: `$ARGUMENTS`

**Risk Register:**

For each risk:

```text
RISK-XX | <Title>
Category: Technical / Regulatory / Integration / Data / People
Probability: Low / Medium / High
Impact: Low / Medium / High / Critical
Score: P × I
Status: Open / Mitigated / Accepted / Closed
Mitigation: <specific action>
Owner: <role>
Due: <date or sprint>
```

**Categories to Always Check:**

- **Technical:** ERPNext core conflicts, Frappe version compatibility, migration impact
- **Regulatory:** NĐ98/2021 compliance gaps, WHO HTM requirement coverage
- **Integration:** FHIR / HIS / LIS connection points, data format mismatches
- **Data:** Migration from legacy system, data quality, audit trail gaps
- **People:** Role availability, training needs, clinical dept buy-in

**Output:**

1. Risk register table sorted by Score (highest first)
2. Top 3 risks requiring immediate action
3. Go/No-Go recommendation for the sprint or release
