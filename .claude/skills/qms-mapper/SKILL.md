---
name: qms-mapper
description: Map AssetCore IMM module features to QMS requirements — ISO 13485, WHO HTM, NĐ98, controlled documents, CAPA triggers, audit trail
type: skill
---

# QMS Mapper — AssetCore

## What This Skill Does

Given an IMM module or feature, produce a **complete QMS compliance mapping** covering controlled documents, regulatory clauses, CAPA triggers, and audit trail requirements.

## Input

User provides one of:
- Module name: `IMM-05` or `IMM-08 PM`
- Feature description: `"approve asset document workflow"`
- Entity: `"Work Order for Calibration"`

## Output Format

### 1. Module Summary
```
Module: IMM-XX — <Name>
Actor: <roles>
Trigger: <what starts this process>
Output Record: <DocType created>
```

### 2. QMS Document Hierarchy
For each applicable level:

| Level | Code | Document | Owner | Revision |
|-------|------|----------|-------|---------|
| QC | QC-XX | Quality Manual clause | CMMS Admin | — |
| PR | PR-XX | Procedure (SOP) | Workshop Head | Controlled |
| WI | WI-XX | Work Instruction | Biomed Engineer | Controlled |
| BM | BM-XX | Biểu mẫu (Form) | HTM Technician | Controlled |
| HS | HS-XX | Hồ sơ (Record) | System | Auto-generated |
| KPI | KPI-XX | Metric | CMMS Admin | Dashboard |

### 3. Regulatory Clause Mapping
| Clause | Standard | Requirement | Implementation in AssetCore |
|--------|----------|-------------|----------------------------|
| X.X.X | ISO 13485:2016 | ... | ... |
| X.X | WHO HTM | ... | ... |
| Điều X | NĐ98/2021 | ... | ... |

### 4. CAPA Triggers
List conditions that must automatically open a CAPA record:
```
TRIGGER: <condition>
CAPA Type: Corrective / Preventive
Severity: Minor / Major / Critical
Owner: <role>
Response SLA: <timeframe>
```

### 5. Audit Trail Requirements
What must be recorded for traceability:
```
Event: <what happened>
Actor: <who did it>
Timestamp: <when>
From State: <previous>
To State: <new>
Root Record: <DocType.name>
Evidence: <attachments required>
```

### 6. Change Control Requirements
Does this feature require:
- [ ] Document Control (version bump on change)
- [ ] Change Control Record before modification
- [ ] Validation/re-validation after change
- [ ] Notification to regulatory body

### 7. KPI Definitions
| KPI | Formula | Target | Alert Threshold | Dashboard |
|-----|---------|--------|-----------------|-----------|

### 8. Implementation Checklist
- [ ] Workflow states match QMS procedure steps
- [ ] Every state transition creates an audit log entry
- [ ] Approval requires documented role authorization
- [ ] Rejection requires documented reason
- [ ] All attachments version-controlled
- [ ] Expiry dates tracked with advance alerts
- [ ] CAPA linkage available for non-conformances

## QMS Framework Reference

### Document Hierarchy
```
QC (Quality Manual) → PR (Procedure/SOP) → WI (Work Instruction) → BM (Form) → HS (Record)
```

### Key ISO 13485 Clauses for AssetCore
- 4.2.4 — Control of records
- 6.3 — Infrastructure (equipment maintenance)
- 7.5.1 — Control of production/service
- 7.6 — Control of monitoring & measuring equipment (Calibration)
- 8.3 — Control of nonconforming product
- 8.5.2 — Corrective action
- 8.5.3 — Preventive action

### Vietnamese Regulations
- NĐ98/2021 — Quản lý trang thiết bị y tế
- TT46/2017 — Kiểm định, hiệu chuẩn
- TT32/2023 — Phân loại trang thiết bị y tế

## Step-by-Step Execution

1. Identify the module and its actor/role
2. Map to the document hierarchy (QC → PR → WI → BM → HS → KPI)
3. Find applicable ISO 13485 clauses
4. Find applicable Vietnamese regulation articles
5. List CAPA trigger conditions
6. Define audit trail requirements
7. Specify KPIs with formulas and targets
8. Output the implementation checklist
