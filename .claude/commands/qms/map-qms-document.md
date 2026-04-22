---
description: Map an AssetCore feature or module to its QMS document requirements
---

Map the following to QMS document requirements: `$ARGUMENTS`

Use the `/qms-mapper` skill logic. Output all sections:

1. **Module Summary** — actor, trigger, output record
2. **QMS Document Hierarchy** — QC → PR → WI → BM → HS → KPI table
3. **Regulatory Clause Mapping** — ISO 13485, WHO HTM, NĐ98 table
4. **CAPA Triggers** — conditions, severity, owner, SLA
5. **Audit Trail Requirements** — event, actor, timestamp, from/to state, evidence
6. **Change Control Requirements** — checklist of what requires CCR before change
7. **KPI Definitions** — formula, target, alert threshold
8. **Implementation Checklist** — all QMS requirements mapped to system features

Reference docs in `assetcore/docs/` if available for the specified module.
