# IMM-16 — Technical Design

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-16 — Compliance Monitoring & CAPA |
| Phiên bản | 0.2.0 (Wave 2 — alignment with existing CAPA backbone) |
| Ngày cập nhật | 2026-05-04 |
| Trạng thái | PARTIAL — CAPA core LIVE, compliance/audit/scorecard PLANNED |
| Tác giả | AssetCore Team |

---

## 0. Trạng thái hiện tại (LIVE vs PLANNED)

| Artefact | Trạng thái | Đường dẫn |
|---|---|---|
| `IMM CAPA Record` (DocType, submittable) | **LIVE** | `assetcore/assetcore/doctype/imm_capa_record/imm_capa_record.json` |
| `Audit Finding` (child) | **LIVE** | `assetcore/assetcore/doctype/audit_finding/audit_finding.json` |
| `IMM Audit Trail` (hash chain) | **LIVE** | `assetcore/assetcore/doctype/imm_audit_trail/imm_audit_trail.json` |
| `IMM RCA Record` + `IMM RCA Five Why Step` | **LIVE** | `assetcore/assetcore/doctype/imm_rca_record/` |
| `IMM Supplier Audit` (vendor-side, IMM-03) | **LIVE** | `assetcore/assetcore/doctype/imm_supplier_audit/` |
| `services/imm00.py` (`create_capa`, `close_capa`, `check_capa_overdue`) | **LIVE** | `assetcore/services/imm00.py` |
| `services/imm12.py` (đã wire `_DT_CAPA = "IMM CAPA Record"`) | **LIVE** | `assetcore/services/imm12.py` |
| Custom Field 11x trên IMM CAPA Record | PLANNED | Patch + fixture |
| Custom Field 2x trên Audit Finding | PLANNED | Patch |
| `IMM Compliance Rule`, `IMM Compliance Finding`, `IMM Internal Audit`, `IMM CAPA Action Step`, `IMM Compliance Scorecard`, `IMM Management Review` | PLANNED | — |
| `assetcore/api/imm16.py`, `assetcore/services/imm16.py` | PLANNED | — |
| 5 scheduler entries trong `tasks.py` | PLANNED | — |
| 4 workflow JSON | PLANNED | — |

---

## 1. Overview

### 1.1 Layered architecture

```
Request (HTTP / Workflow Action / Scheduler / Hook IMM-08/09)
    │
    ▼
API Layer  (assetcore/api/imm16.py — ~30 endpoints)
    │   @frappe.whitelist()
    ▼
Service Layer (assetcore/services/imm16.py)
    │   - rule_evaluator.evaluate(rule, context)
    │   - finding_upsertor.upsert(rule, source_record, eval_date, current_value)
    │   - scorecard_aggregator.build(period_year, period_month)
    │   - escalation_matrix.escalate(capa_record)
    │   - compliance_gate.check(asset)
    │
    │   Reuse:
    │   - services.imm00.create_capa(asset, source_type, source_ref, severity, ...)
    │   - services.imm00.close_capa(capa_name, root_cause, corrective_action, ...)
    │   - services.imm00.log_audit_event(...) → IMM Audit Trail
    ▼
Controller (per-DocType) — IMM CAPA Record EXISTING + new compliance DocTypes
    │   validate(), before_save(), on_update()
    ▼
Frappe ORM → MariaDB
    │   - tabIMM CAPA Record (LIVE — extend via Custom Field)
    │   - tabAudit Finding (LIVE — extend via Custom Field)
    │   - tabIMM Compliance Rule/Finding/Internal Audit/Scorecard/MR (NEW)
    ▼
Side effects:
  - Frappe Version (auto, track_changes=1 — đã bật trên CAPA Record)
  - IMM Audit Trail (hash chain) qua imm00.log_audit_event
  - Email notifications
  - frappe.publish_realtime("imm16:finding_created") cho dashboard
```

> **Service-first pattern.** Controller chỉ điều phối + validate. Rule engine + escalation logic phức tạp, cần unit-test isolated.

### 1.2 Files

| File | Trạng thái | Vai trò |
|---|---|---|
| `assetcore/assetcore/doctype/imm_capa_record/imm_capa_record.json` | LIVE | CAPA backbone DocType |
| `assetcore/assetcore/doctype/audit_finding/audit_finding.json` | LIVE | Child Audit Finding |
| `assetcore/assetcore/doctype/imm_audit_trail/` | LIVE | Hash-chained audit trail |
| `assetcore/assetcore/doctype/imm_rca_record/` | LIVE | RCA infrastructure |
| `assetcore/assetcore/custom/imm_capa_record_imm16.json` | PLANNED | 11 Custom Field fixture |
| `assetcore/assetcore/custom/audit_finding_imm16.json` | PLANNED | 2 Custom Field fixture |
| `assetcore/assetcore/doctype/imm_compliance_rule/imm_compliance_rule.json` | PLANNED | Rule (master, versioned) |
| `assetcore/assetcore/doctype/imm_compliance_rule/imm_compliance_rule.py` | PLANNED | Controller — change-control snapshot |
| `assetcore/assetcore/doctype/imm_compliance_finding/imm_compliance_finding.json` | PLANNED | Finding |
| `assetcore/assetcore/doctype/imm_compliance_finding/imm_compliance_finding.py` | PLANNED | Controller — VR-03/04, link_to_capa |
| `assetcore/assetcore/doctype/imm_internal_audit/imm_internal_audit.json` | PLANNED | Audit (reuse Audit Finding child) |
| `assetcore/assetcore/doctype/imm_audit_checklist_item/imm_audit_checklist_item.json` | PLANNED | Child — checklist item |
| `assetcore/assetcore/doctype/imm_capa_action_step/imm_capa_action_step.json` | PLANNED | Child — gắn vào IMM CAPA Record qua Custom Field `imm_action_plan` |
| `assetcore/assetcore/doctype/imm_compliance_scorecard/imm_compliance_scorecard.json` | PLANNED | Scorecard (immutable) |
| `assetcore/assetcore/doctype/imm_management_review/imm_management_review.json` | PLANNED | MR |
| `assetcore/assetcore/workflow/imm_16_finding_workflow.json` | PLANNED | Finding |
| `assetcore/assetcore/workflow/imm_16_audit_workflow.json` | PLANNED | Audit |
| `assetcore/assetcore/workflow/imm_16_capa_workflow.json` | PLANNED | **Extend** workflow trên IMM CAPA Record (state mới: Investigating, Action Plan, Implementation, Verification, Re-opened) |
| `assetcore/assetcore/workflow/imm_16_mr_workflow.json` | PLANNED | MR |
| `assetcore/api/imm16.py` | PLANNED | ~30 REST endpoints |
| `assetcore/services/imm16.py` | PLANNED | Rule engine, scorecard, escalation, gate |
| `assetcore/tasks.py` | EXTEND | 5 scheduler entries IMM-16 |
| `assetcore/patches/v0_2/migrate_capa_record_workflow_state.py` | PLANNED | Map In Progress → Investigating cho dữ liệu cũ |

---

## 2. DocType Schema

### 2.1 IMM CAPA Record — REUSE + EXTEND (Custom Fields)

**Existing schema (LIVE — KHÔNG sửa core JSON):**

| Property | Value |
|---|---|
| name | IMM CAPA Record |
| autoname | `naming_series:` → `CAPA-.YYYY.-.#####` |
| is_submittable | 1 |
| track_changes | 1 |

Existing fields gồm: `naming_series`, `capa_number`, `asset` (Link AC Asset), `severity` (Minor/Major/Critical), `status` (Open/In Progress/Pending Verification/Closed/Overdue), `workflow_state`, `source_type`, `source_ref` (Dynamic Link), `linked_incident`, `description`, `root_cause`, `corrective_action`, `preventive_action`, `responsible`, `opened_date`, `due_date`, `closed_date`, `lookback_required`, `lookback_status`, `lookback_assets`, `verification_notes`, `effectiveness_check` (Effective/Partially Effective/Not Effective), `notes`, `amended_from`.

**Custom Fields IMM-16 (PLANNED — fixture):**

| # | fieldname | fieldtype | options / default | reqd | depends_on | Mục đích |
|---|---|---|---|:---:|---|---|
| 1 | `imm_root_cause_method` | Select | `\n5-Why\nFishbone\nFMEA\nFTA\nOther` | — | workflow_state IN (Action Plan, Implementation, Verification, Closed) | VR-05 |
| 2 | `imm_correction_immediate` | Text | — | — | — | Hành động khắc phục tức thời (correction) |
| 3 | `imm_action_plan` | Table | `IMM CAPA Action Step` | — | — | Kế hoạch theo bước |
| 4 | `imm_effectiveness_check_date` | Date | — | — | — | Ngày verify |
| 5 | `imm_effectiveness_evidence` | Attach | — | — | — | Bằng chứng |
| 6 | `imm_change_control_ref` | Data | — | — | — | Tham chiếu change control |
| 7 | `imm_risk_level` | Select | `Low\nMedium\nHigh\nCritical` | * (cho IMM-16 flow) | — | Risk-based — phục vụ BR-16-09 |
| 8 | `imm_compliance_finding_ref` | Link | `IMM Compliance Finding` | — | — | Link Finding → CAPA |
| 9 | `imm_audit_finding_ref` | Data | — | — | — | Reference Audit Finding row (parent_audit + idx) |
| 10 | `imm_rca_ref` | Link | `IMM RCA Record` | — | — | Link RCA — KHÔNG re-model 5-Why trong CAPA |
| 11 | `imm_reopen_count` | Int | default 0 | — | — | Đếm lần re-open |

**Extension Select option `source_type`:** thêm `Audit Finding`, `Compliance Finding`, `Management Review` qua Property Setter (giữ tương thích bản ghi cũ).

> Lưu ý: Field `severity` cũ (Minor/Major/Critical) là theo discrepancy/severity của CAPA — IMM-16 dùng `imm_risk_level` (Low/Medium/High/Critical) cho prioritization và gate logic. Cả hai cùng tồn tại; UI sẽ map auto khi tạo CAPA từ Compliance Finding.

### 2.2 Audit Finding (child) — REUSE + EXTEND

**Existing (LIVE):** `severity` (Minor/Major/Critical), `category` (Quality/Compliance/Delivery/Documentation/Other), `description`, `capa_action` (Long Text — loose), `capa_owner` (Link User), `capa_due` (Date), `capa_status` (Open/In Progress/Closed).

**Custom Fields IMM-16 (PLANNED):**

| # | fieldname | fieldtype | options | Mục đích |
|---|---|---|---|---|
| 1 | `imm_finding_link` | Link | `IMM Compliance Finding` | Cross-ref Audit Finding ↔ Compliance Finding (cho cả Internal Audit và Supplier Audit) |
| 2 | `imm_capa_link` | Link | `IMM CAPA Record` | Thay thế text loose `capa_action` bằng link cứng — phục vụ VR-08 (BR-16-04) |

> `Audit Finding` được dùng chung cho `IMM Internal Audit` (mới) và `IMM Supplier Audit` (LIVE, IMM-03). Cùng schema, cùng custom field — KHÔNG fork.

### 2.3 IMM Compliance Rule (PLANNED — `tabIMM Compliance Rule`)

**Config:**

| Property | Value |
|---|---|
| name | IMM Compliance Rule |
| autoname | `field:rule_code` |
| is_submittable | 0 |
| track_changes | 1 |
| title_field | `rule_name` |
| search_fields | `rule_code,rule_name,source_module,category` |

**Fields:**

| # | fieldname | fieldtype | options | reqd | read_only |
|---|---|---|---|:---:|:---:|
| 1 | rule_code | Data (unique) | — | * | — |
| 2 | rule_name | Data | — | * | — |
| 3 | source_module | Select | IMM-04..IMM-15 | * | — |
| 4 | category | Select | Document/PM/Calibration/Training/Stock/SLA/Safety | * | — |
| 5 | severity | Select | Low/Medium/High/Critical | * | — |
| 6 | threshold_definition | JSON | — | * | — |
| 7 | evaluation_frequency | Select | Realtime/Hourly/Daily/Weekly/Monthly/Quarterly | * | — |
| 8 | data_source_doctype | Link → DocType | — | — | — |
| 9 | data_source_field | Data | — | — | — |
| 10 | owner_role | Link → Role | — | * | — |
| 11 | qms_doc_ref | Data | — | — | — |
| 12 | regulatory_reference | Data | — | — | — |
| 13 | is_active | Check | — | — | — |
| 14 | effective_date | Date | — | * | — |
| 15 | version | Data | default "1.0" | — | 1 |
| 16 | previous_version | Data | — | — | 1 |
| 17 | change_summary | Small Text | — | — | — |

### 2.4 IMM Compliance Finding (PLANNED — `tabIMM Compliance Finding`)

**Config:**

| Property | Value |
|---|---|
| autoname | `format:FND-.YYYY.-.#####` |
| is_submittable | 0 |
| track_changes | 1 |
| title_field | `rule` |
| search_fields | `rule,asset,source_record,severity,status` |

**Fields:**

| # | fieldname | fieldtype | options | reqd | read_only | search_index |
|---|---|---|---|:---:|:---:|:---:|
| 1 | rule | Link → IMM Compliance Rule | — | * | — | 1 |
| 2 | detected_date | Datetime | — | * | 1 | 1 |
| 3 | source_record_doctype | Link → DocType | — | — | — | 1 |
| 4 | source_record | Dynamic Link | — | — | — | 1 |
| 5 | asset | Link → AC Asset | — | — | — | 1 |
| 6 | responsible_dept | Link → AC Department | — | — | — | 1 |
| 7 | severity | Select | Low/Medium/High/Critical | * | — | 1 |
| 8 | current_value | Data | — | — | — | — |
| 9 | threshold_value | Data | — | — | — | — |
| 10 | status | Select | Open/Under Review/Confirmed NC/False Positive/Resolved/Waived/Closed | * | — | 1 |
| 11 | reviewer | Link → User | — | — | — | — |
| 12 | review_date | Datetime | — | — | 1 | — |
| 13 | capa_ref | Link → IMM CAPA Record | — | — | — | — |
| 14 | waiver_reason | Long Text | — | — | — | — |
| 15 | waiver_evidence | Attach | — | — | — | — |
| 16 | waiver_expiry | Date | — | — | — | — |
| 17 | evaluation_date | Date | — | * | 1 | 1 |
| 18 | evidence | Attach | — | — | — | — |
| 19 | notes | Text Editor | — | — | — | — |
| 20 | workflow_state | Link → Workflow State | — | — | 1 | 1 |

**Index khuyến nghị:**

```sql
CREATE UNIQUE INDEX idx_finding_idem
  ON `tabIMM Compliance Finding` (rule, source_record, evaluation_date);
```

### 2.5 IMM Internal Audit (PLANNED — `tabIMM Internal Audit`)

**Config:** `autoname format:AUD-INT-.YYYY.-.#####`, `is_submittable=0`, `track_changes=1`.

**Fields:**

| # | fieldname | fieldtype | options |
|---|---|---|---|
| 1 | audit_code | Data (unique) | reqd |
| 2 | audit_type | Select | Internal/Self-assessment |
| 3 | scope_modules | Table | IMM Audit Scope Module |
| 4 | scope_departments | Table | IMM Audit Scope Department |
| 5 | planned_start | Date | reqd |
| 6 | planned_end | Date | reqd |
| 7 | actual_start | Date | — |
| 8 | actual_end | Date | — |
| 9 | lead_auditor | Link → User | reqd |
| 10 | auditor_team | Table | IMM Auditor Team Member |
| 11 | audit_plan_doc | Attach | — |
| 12 | checklist_template | Link → IMM Audit Checklist Template | — |
| 13 | checklist_items | Table → IMM Audit Checklist Item | — |
| 14 | **findings** | Table → **Audit Finding** (REUSE child LIVE) | — |
| 15 | status | Select | Planned/In Progress/Reporting/Closed |
| 16 | findings_count | Int | — |
| 17 | total_score | Float | — |
| 18 | audit_report | Attach | — |
| 19 | management_review_ref | Link → IMM Management Review | — |
| 20 | workflow_state | Link → Workflow State | — |

> `findings` table reuse `Audit Finding` (cùng child với `IMM Supplier Audit`). Phân biệt qua parent doctype.

### 2.6 IMM Audit Checklist Item (PLANNED, child)

| # | fieldname | fieldtype | options |
|---|---|---|---|
| 1 | clause_ref | Data | — |
| 2 | requirement | Small Text | — |
| 3 | evidence_required | Small Text | — |
| 4 | evidence_provided | Small Text | — |
| 5 | finding_status | Select | Compliant/Minor NC/Major NC/Observation/Not Applicable |
| 6 | notes | Small Text | — |
| 7 | linked_finding | Link → IMM Compliance Finding | — |

### 2.7 IMM CAPA Action Step (PLANNED, child — gắn vào CAPA Record qua Custom Field `imm_action_plan`)

| # | fieldname | fieldtype | options |
|---|---|---|---|
| 1 | step_no | Int | — |
| 2 | action_description | Small Text | — |
| 3 | owner | Link → User | — |
| 4 | planned_date | Date | — |
| 5 | completed_date | Date | — |
| 6 | evidence | Attach | — |
| 7 | status | Select | Pending/In Progress/Done/Blocked |

### 2.8 IMM Compliance Scorecard (PLANNED — `tabIMM Compliance Scorecard`)

**Config:** `autoname format:SCR-.YYYY.-.MM.-.#####`, `track_changes=1`.

| # | fieldname | fieldtype | options |
|---|---|---|---|
| 1 | period_year | Int | — |
| 2 | period_month | Int | — |
| 3 | scope | Select | Hospital/Block/Department |
| 4 | scope_value | Data | — |
| 5 | total_rules_evaluated | Int | — |
| 6 | compliant_count | Int | — |
| 7 | non_compliant_count | Int | — |
| 8 | score_pct | Float | — |
| 9 | score_by_module | Table → IMM Scorecard Module Row | — |
| 10 | score_by_department | Table → IMM Scorecard Department Row | — |
| 11 | trend_vs_prev_month | Float | — |
| 12 | capa_open_count | Int | — |
| 13 | capa_overdue_count | Int | — |
| 14 | generated_at | Datetime | read_only |
| 15 | approved_by_for_review | Link → User | read_only |
| 16 | is_published | Check | default 0 |
| 17 | published_at | Datetime | read_only |
| 18 | restate_of | Link → IMM Compliance Scorecard | — |

### 2.9 IMM Management Review (PLANNED)

**Config:** `autoname format:MR-.YYYY.-.#####`

| # | fieldname | fieldtype | options |
|---|---|---|---|
| 1 | review_date | Date | reqd |
| 2 | quarter | Data | (auto Q{N}-{YYYY}) |
| 3 | chair | Link → User | reqd |
| 4 | attendees | Table → IMM MR Attendee | — |
| 5 | inputs_summary | Long Text | — |
| 6 | scorecard_ref | Link → IMM Compliance Scorecard | — |
| 7 | audit_summary | Long Text | — |
| 8 | capa_summary | Long Text | — |
| 9 | capa_effectiveness | Long Text | — |
| 10 | customer_complaint_summary | Long Text | — |
| 11 | training_compliance | Long Text | — |
| 12 | risk_review | Long Text | — |
| 13 | qms_changes_decided | Long Text | — |
| 14 | output_actions | Table → IMM MR Output Action | — |
| 15 | next_review_date | Date | — |
| 16 | minutes_doc | Attach | — |
| 17 | status | Select | Draft/Held/Minutes Approved/Closed |

---

## 3. Validation Rules

Implement trong:
- `IMMComplianceRule.before_save()`
- `IMMComplianceFinding.validate()`
- `IMMCAPARecord.validate()` (qua Custom Field hooks — KHÔNG sửa core controller; dùng `doc_events` `validate` trong `hooks.py`)
- `IMMComplianceScorecard.validate()`
- `IMMInternalAudit.validate()`

| VR | Method | Trigger | Logic |
|---|---|---|---|
| VR-01 | `vr_01_threshold_json_schema` | Rule `validate` | JSON schema check (`metric/op/value`) |
| VR-02 | `vr_02_evaluation_frequency` | Rule `validate` | IN allowed list |
| VR-03 | `vr_03_severity_enum` | Finding `validate` | IN (Low, Medium, High, Critical) |
| VR-04 | `vr_04_waiver_complete` | Finding `before_save` if status="Waived" | reason ≥ 50, evidence reqd, expiry > today |
| VR-05 | `vr_05_root_cause_method` | CAPA Record `validate` (hook IMM-16) khi `workflow_state` IN (Action Plan, Implementation, Verification, Closed) | `imm_root_cause_method` reqd IN (5-Why, Fishbone, FMEA, FTA, Other) |
| VR-06 | `vr_06_effectiveness_set` | CAPA Record advance to "Closed" | `effectiveness_check` reqd (field LIVE) |
| VR-07 | `vr_07_close_only_if_effective` | CAPA Record advance to "Closed" | `effectiveness_check == "Effective"` (BR-16-03) |
| VR-08 | `vr_08_audit_close_capa_link` | Internal Audit `close` | Mọi Audit Finding row severity=Major phải có `imm_capa_link` |
| VR-09 | `vr_09_scorecard_immutable` | Scorecard `validate` | `is_published=1` ⇒ throw on edit |
| VR-10 | `vr_10_quarterly_mr_gate` | Scorecard `publish` | Quý trước phải có MR Closed |
| VR-11 | `vr_11_rule_change_summary` | Rule `before_save` | Threshold/severity change ⇒ `change_summary` reqd, version bump |
| VR-12 | `vr_12_capa_due_future` | CAPA Record advance to "Action Plan" (workflow_state) | `due_date > today` |

---

## 4. Service Layer — `services/imm16.py`

### 4.1 Rule Evaluator

```python
class RuleEvaluator:
    def evaluate(self, rule: dict, context: dict) -> EvalResult:
        """
        Returns: EvalResult(violated: bool, current_value, threshold_value, source_record)
        """
        metric = rule["threshold_definition"]["metric"]
        op = rule["threshold_definition"]["op"]    # <, <=, >, >=, ==, !=
        threshold = rule["threshold_definition"]["value"]
        current = self._fetch_metric(rule, context)
        violated = self._compare(current, op, threshold)
        return EvalResult(violated, current, threshold, context["source_record"])
```

Built-in metrics (per `source_module`):

| source_module | metric | data source |
|---|---|---|
| IMM-04 | `commissioning_doc_completeness` | Asset Commissioning + Asset Document |
| IMM-05 | `doc_expired_count`, `doc_expiring_30d` | tabAsset Document |
| IMM-06 | `training_overdue_count` | tabTraining Record |
| IMM-08 | `pm_compliance_pct` | Work Order (PM) |
| IMM-09 | `repair_sla_breach_count` | Work Order (CM) |
| IMM-11 | `calibration_overdue_count`, `oot_count` | Calibration Record |
| IMM-12 | `corrective_sla_breach_count` | Corrective Action |
| IMM-15 | `critical_spare_breach_count` | Spare Stock |

### 4.2 Finding Upsertor (idempotent)

```python
def upsert_finding(rule, source_record, eval_date, current_value):
    existing = frappe.db.exists("IMM Compliance Finding", {
        "rule": rule.name, "source_record": source_record, "evaluation_date": eval_date
    })
    if existing:
        return existing  # idempotent
    doc = frappe.new_doc("IMM Compliance Finding")
    doc.update(...)
    doc.insert()
    frappe.publish_realtime("imm16:finding_created", doc.as_dict())
    return doc.name
```

### 4.3 Link Finding → CAPA Record (reuse imm00.create_capa)

```python
def link_finding_to_capa(finding_name: str, capa_data: dict) -> str:
    """Reuse imm00.create_capa to instantiate IMM CAPA Record."""
    from assetcore.services import imm00 as svc00
    finding = frappe.get_doc("IMM Compliance Finding", finding_name)
    capa_name = svc00.create_capa(
        asset=finding.asset,
        source_type="Compliance Finding",
        source_ref=finding.name,
        severity=_map_severity_to_capa(finding.severity),
        description=f"Compliance Finding {finding.name}: {finding.notes or ''}",
    )
    # Set IMM-16 Custom Fields on the CAPA Record
    frappe.db.set_value("IMM CAPA Record", capa_name, {
        "imm_compliance_finding_ref": finding.name,
        "imm_risk_level": finding.severity,
        "workflow_state": "Open",
    })
    frappe.db.set_value("IMM Compliance Finding", finding_name, "capa_ref", capa_name)
    return capa_name
```

### 4.4 Scorecard Aggregator

```python
def build_scorecard(period_year, period_month, scope="Hospital"):
    findings = frappe.get_all("IMM Compliance Finding", filters={
        "evaluation_date": ["between", (start_of_month, end_of_month)],
        "status": ["!=", "False Positive"]
    }, fields=["rule", "responsible_dept", "status", "severity"])
    total = len(findings)
    nc = sum(1 for f in findings if f.status in ("Confirmed NC", "Resolved", "Closed"))
    score = round((total - nc) / total * 100, 2) if total else 100
    sc = frappe.new_doc("IMM Compliance Scorecard")
    sc.update({...})
    sc.insert()
    return sc.name
```

### 4.5 Escalation Matrix (CAPA Record)

```python
ESCALATION = {
    "High":     {"L1": 3, "L2": 7,  "L3": 14},   # days overdue
    "Critical": {"L1": 1, "L2": 3,  "L3": 7},
}
RECIPIENTS = {
    "L1": ["responsible"],
    "L2": ["workshop_head", "responsible"],
    "L3": ["vp_block2", "truong_phong", "workshop_head"],
}
```

> Reuse: `imm00.check_capa_overdue` (LIVE) đã quét CAPA Record quá hạn. IMM-16 thêm escalation matrix trên cùng dataset.

### 4.6 Compliance Gate (BR-16-09)

```python
@frappe.whitelist()
def check_asset_compliance_status(asset: str) -> dict:
    """Called by services/imm08.py + services/imm09.py validate_* before WO Submit.
    Reads existing IMM CAPA Record + IMM-16 Custom Field imm_risk_level."""
    crit_open = frappe.get_all("IMM CAPA Record", filters={
        "asset": asset,
        "imm_risk_level": "Critical",
        "status": ["in", ["Open", "In Progress", "Pending Verification"]]
    }, pluck="name")
    if crit_open:
        return _ok({"blocked": True,
                    "reason": f"CAPA Critical OPEN: {','.join(crit_open)}"})
    return _ok({"blocked": False})
```

**Hook integration:**

- `services/imm08.py.validate_pm_work_order(doc)`: gọi `imm16.check_asset_compliance_status(doc.asset)` → throw nếu blocked.
- `services/imm09.py.validate_repair_work_order(doc)`: tương tự.

---

## 5. Hooks (Controller lifecycle)

### 5.1 IMM Compliance Rule (mới)

```python
class IMMComplianceRule(Document):
    def validate(self):
        self.vr_01_threshold_json_schema()
        self.vr_02_evaluation_frequency()

    def before_save(self):
        if self.has_value_changed("threshold_definition") or self.has_value_changed("severity"):
            self.vr_11_rule_change_summary()
            self.previous_version = self.version
            self.version = self._bump_version(self.version)
```

### 5.2 IMM CAPA Record — KHÔNG sửa core controller

Thay vào đó, thêm `doc_events` trong `hooks.py`:

```python
doc_events = {
    "IMM CAPA Record": {
        "validate": "assetcore.services.imm16.capa_record_validate",
        "on_update": "assetcore.services.imm16.capa_record_on_update",
    },
}
```

```python
# services/imm16.py
def capa_record_validate(doc, method=None):
    ws = doc.workflow_state
    if ws in ("Action Plan", "Implementation", "Verification", "Closed"):
        if not doc.get("imm_root_cause_method"):
            frappe.throw(_("VR-05: Phải chọn phương pháp phân tích root cause."))
    if ws == "Action Plan":
        if not doc.due_date or getdate(doc.due_date) <= getdate(today()):
            frappe.throw(_("VR-12: Hạn hoàn thành phải sau hôm nay."))
    if doc.status == "Closed":
        if not doc.effectiveness_check:
            frappe.throw(_("VR-06: Effectiveness check chưa hoàn tất."))
        if doc.effectiveness_check != "Effective":
            frappe.throw(_("VR-07: Không thể Close khi effectiveness chưa Effective."))

def capa_record_on_update(doc, method=None):
    # Cascade Finding → Resolved khi CAPA Closed
    if doc.status == "Closed" and doc.source_type == "Compliance Finding":
        frappe.db.set_value("IMM Compliance Finding", doc.source_ref,
                            "status", "Resolved")
    # Re-open detection
    if doc.has_value_changed("status") and doc.status == "In Progress" \
       and (doc.get_db_value("status") == "Closed"):
        new_count = (doc.get("imm_reopen_count") or 0) + 1
        doc.db_set("imm_reopen_count", new_count)
        doc.db_set("workflow_state", "Investigating")
```

### 5.3 IMM Compliance Scorecard

```python
class IMMComplianceScorecard(Document):
    def validate(self):
        if self.is_published and self.has_changed_after_publish():
            frappe.throw(_("VR-09: Scorecard đã publish, không thể sửa. Hãy tạo restate mới."))
```

---

## 6. API Layer

Xem `IMM-16_API_Interface.md`. Module: `assetcore/api/imm16.py`.

Constants:

```python
_DOCTYPE_RULE = "IMM Compliance Rule"
_DOCTYPE_FINDING = "IMM Compliance Finding"
_DOCTYPE_AUDIT = "IMM Internal Audit"
_DOCTYPE_CAPA = "IMM CAPA Record"          # REUSE LIVE
_DOCTYPE_AUDIT_FINDING = "Audit Finding"   # REUSE LIVE
_DOCTYPE_SCORECARD = "IMM Compliance Scorecard"
_DOCTYPE_MR = "IMM Management Review"
_DOCTYPE_RCA = "IMM RCA Record"            # REUSE LIVE

_WAIVE_ROLES = {"VP Block2", "CMMS Admin"}
_PUBLISH_SCORECARD_ROLES = {"Tổ HC-QLCL", "VP Block2", "CMMS Admin"}
_FINALIZE_MR_ROLES = {"VP Block2", "CMMS Admin"}
_CLOSE_AUDIT_ROLES = {"Tổ HC-QLCL", "VP Block2", "CMMS Admin"}
_AUDIT_LEAD_ROLES = {"Tổ HC-QLCL", "Internal Auditor", "CMMS Admin"}
```

---

## 7. Schedulers

File: `assetcore/tasks.py` (extend, KHÔNG tạo file mới).

### 7.1 `run_compliance_evaluation()` — Hourly + Daily 00:15

```
For each rule WHERE is_active=1 AND evaluation_frequency matches current cadence:
    For each context (per dept / per asset / per source_record):
        result = RuleEvaluator.evaluate(rule, context)
        If result.violated:
            upsert_finding(rule, ctx.source_record, today, result.current_value)
            If severity ≥ "High":
                notify owner_role (BR-16-01 reminder)
```

Cadence map: Realtime hooks; Hourly (stock breach IMM-15); Daily 00:15 (doc expiry, training overdue, calibration overdue); Weekly Mon (SLA review IMM-09/12); Monthly 1st (PM compliance, repeat failure trend).

### 7.2 `update_compliance_scorecard()` — Monthly 1st 03:00

Aggregate previous month → sinh Scorecard Draft per scope. Notify reviewer cho sign-off.

### 7.3 `check_capa_due_imm16()` — Daily 02:00

Reuse query trên `IMM CAPA Record` (đã có `imm00.check_capa_overdue`). IMM-16 thêm tier escalation:

```
For capa WHERE status NOT IN (Closed) AND due_date < today:
    overdue_days = today - due_date
    level = escalation_level(capa.imm_risk_level, overdue_days)
    if not capa.escalation_log_today(level):
        send_email(RECIPIENTS[level], capa)
        log_escalation(capa, level)  # ghi IMM Audit Trail
```

### 7.4 `check_audit_milestones()` — Daily 02:30

```
For audit WHERE status="Planned" AND planned_start - today <= 7:
    notify lead_auditor + Tổ HC-QLCL
For audit WHERE status="In Progress" AND today > planned_end:
    notify Tổ HC-QLCL "audit overrun"
```

### 7.5 `check_management_review_due()` — Weekly Monday 08:00

```
current_quarter = ...
if not exists(MR WHERE quarter=current_quarter AND status="Closed"):
    days_left = end_of_quarter - today
    if days_left <= 30: notify VP Block2 + Tổ HC-QLCL
```

---

## 8. Workflow JSON

### 8.1 Finding Workflow (`imm_16_finding_workflow.json`) — NEW

| state | doc_status | type |
|---|---|---|
| Open | 0 | Warning |
| Under Review | 0 | Warning |
| Confirmed NC | 0 | Danger |
| False Positive | 0 | Default |
| Waived | 1 | Default |
| Resolved | 1 | Success |
| Closed | 2 | Success |

Transitions: Open→Under Review (Tổ HC-QLCL/Auditor); Under Review→Confirmed NC | False Positive (Tổ HC-QLCL); Under Review→Waived (VP Block2 only); Confirmed NC→Resolved (auto khi CAPA Record.status=Closed); Resolved→Closed (Tổ HC-QLCL).

### 8.2 Internal Audit Workflow — NEW

| state | doc_status | type |
|---|---|---|
| Planned | 0 | Default |
| In Progress | 0 | Warning |
| Reporting | 0 | Warning |
| Closed | 1 | Success |

### 8.3 CAPA Workflow — **EXTEND** existing `IMM CAPA Record`

Existing `status` field hiện cho phép: `Open / In Progress / Pending Verification / Closed / Overdue`. Workflow mở rộng dùng `workflow_state` (Link → Workflow State) để bổ sung sub-state mà KHÔNG đổi `status` core.

| workflow_state | mapped status | doc_status | type | Ghi chú |
|---|---|---|---|---|
| Open | Open | 0 | Default | Khởi tạo |
| Investigating | In Progress | 0 | Warning | Đang RCA (link `imm_rca_ref`) |
| Action Plan | In Progress | 0 | Warning | RCA xong, lập kế hoạch (`imm_action_plan`) |
| Implementation | In Progress | 0 | Warning | Đang thực thi action steps |
| Verification | Pending Verification | 0 | Warning | Đợi `effectiveness_check` |
| Closed | Closed | 1 | Success | `effectiveness_check=Effective` |
| Re-opened | In Progress | 0 | Danger | `imm_reopen_count++` |

**Migration mapping (patch `migrate_capa_record_workflow_state.py`):**

| Bản ghi cũ `status` | Mặc định `workflow_state` |
|---|---|
| Open | Open |
| In Progress (chưa có RCA) | Investigating |
| In Progress (có `root_cause` non-empty) | Action Plan |
| Pending Verification | Verification |
| Closed | Closed |
| Overdue | giữ status; workflow_state = Investigating + flag overdue |

> Migration KHÔNG xoá / sửa field cũ. Idempotent: chạy lại không đổi giá trị đã set.

### 8.4 Management Review Workflow — NEW

| state | doc_status | type |
|---|---|---|
| Draft | 0 | Default |
| Held | 0 | Warning |
| Minutes Approved | 1 | Success |
| Closed | 1 | Success |

---

## 9. Fixtures & hooks.py

### 9.1 Required fixtures

| File | Nội dung |
|---|---|
| `fixtures/imm16_custom_field_capa_record.json` | 11 Custom Field trên IMM CAPA Record + Property Setter extend `source_type` Select |
| `fixtures/imm16_custom_field_audit_finding.json` | 2 Custom Field trên Audit Finding |
| `fixtures/imm16_compliance_rules_baseline.json` | ≥40 rule baseline |
| `fixtures/imm16_audit_checklist_template.json` | Template checklist ISO 13485 §8.2.4 |
| `workflow/imm_16_finding_workflow.json` | Finding workflow |
| `workflow/imm_16_audit_workflow.json` | Audit workflow |
| `workflow/imm_16_capa_workflow.json` | CAPA workflow EXTEND (xem §8.3) |
| `workflow/imm_16_mr_workflow.json` | MR workflow |
| `fixtures/imm16_role_internal_auditor.json` | Sub-role definition |

### 9.2 hooks.py registration

```python
scheduler_events = {
    "hourly": [
        "assetcore.tasks.run_compliance_evaluation_hourly",
    ],
    "daily": [
        "assetcore.tasks.run_compliance_evaluation_daily",
        "assetcore.tasks.check_capa_due_imm16",
        "assetcore.tasks.check_audit_milestones",
    ],
    "weekly_long": [
        "assetcore.tasks.check_management_review_due",
    ],
    "monthly_long": [
        "assetcore.tasks.update_compliance_scorecard",
    ],
}

doc_events = {
    "IMM CAPA Record": {
        "validate": "assetcore.services.imm16.capa_record_validate",
        "on_update": "assetcore.services.imm16.capa_record_on_update",
    },
    "Asset Commissioning": {
        "on_submit": "assetcore.services.imm16.eval_imm04_realtime"
    },
    "Asset Document": {
        "on_update": "assetcore.services.imm16.eval_imm05_realtime"
    },
    "Work Order": {
        "on_submit": "assetcore.services.imm16.eval_imm08_09_realtime",
        "validate": "assetcore.services.imm16.gate_wo_submit",  # BR-16-09
    },
    "Calibration Record": {
        "on_submit": "assetcore.services.imm16.eval_imm11_realtime"
    },
}
```

> `gate_wo_submit` chỉ kích hoạt khi `doc.work_order_type` IN (PM, CM) — chuyển vào `services/imm08.py` + `services/imm09.py.validate_*` nếu module đã có riêng controllers.

---

## 10. Database Indexes

| Bảng | Cột | Lý do |
|---|---|---|
| `tabIMM Compliance Finding` | `(rule, source_record, evaluation_date)` UNIQUE | Idempotent upsert (NFR-16-03) |
| `tabIMM Compliance Finding` | `status` | Filter dashboard |
| `tabIMM Compliance Finding` | `severity` | Filter |
| `tabIMM Compliance Finding` | `responsible_dept` | Heatmap aggregation |
| `tabIMM Compliance Finding` | `asset` | Asset-centric query |
| `tabIMM CAPA Record` | `(asset, imm_risk_level, status)` | check_asset_compliance_status (BR-16-09) — composite trên Custom Field |
| `tabIMM CAPA Record` | `(status, due_date)` | check_capa_due_imm16 |
| `tabIMM Internal Audit` | `(status, planned_start)` | check_audit_milestones |
| `tabIMM Compliance Scorecard` | `(period_year, period_month, scope, scope_value)` | Get current/by period |
| `tabIMM Management Review` | `quarter` | Quarterly check |

**Composite index manual SQL:**

```sql
CREATE UNIQUE INDEX idx_finding_idem
  ON `tabIMM Compliance Finding` (rule, source_record, evaluation_date);

CREATE INDEX idx_capa_gate
  ON `tabIMM CAPA Record` (asset, imm_risk_level, status);

CREATE INDEX idx_capa_due
  ON `tabIMM CAPA Record` (status, due_date);

CREATE INDEX idx_finding_dept_status
  ON `tabIMM Compliance Finding` (responsible_dept, status, severity);
```

---

## 11. Migration Notes

| Version | Migration |
|---|---|
| Wave 1 → Wave 2 (init IMM-16) | (1) Tạo Custom Field cho IMM CAPA Record + Audit Finding qua fixture. (2) Tạo 6 DocType mới + child tables. (3) Tạo 4 workflow (CAPA workflow EXTEND — xem §8.3). (4) Thêm 5 scheduler entries trong hooks.py. (5) Seed baseline rules (≥40). (6) Patch migrate `workflow_state` cho CAPA Record cũ. (7) Roll out theo thứ tự: Custom Fields → Rule master → Finding (manual mode) → Audit → Scorecard → MR. (8) Bật scheduler `run_compliance_evaluation` sau khi seed rules đã review. |

**Backfill scripts:**

```python
# Patch — migrate workflow_state cho CAPA Record cũ
def execute():
    rows = frappe.get_all("IMM CAPA Record",
        fields=["name", "status", "root_cause", "workflow_state"],
        filters={"workflow_state": ["in", ["", None]]})
    for r in rows:
        ws = _map_status_to_ws(r.status, bool(r.root_cause))
        frappe.db.set_value("IMM CAPA Record", r.name, "workflow_state", ws,
                            update_modified=False)

# Sau khi seed rules, chạy 1 lần evaluation đầu tiên
frappe.enqueue("assetcore.tasks.run_compliance_evaluation_daily", queue="long", timeout=3600)

# Backfill scorecard 6 tháng gần nhất
for y, m in last_6_months():
    frappe.enqueue("assetcore.services.imm16.build_scorecard",
                    period_year=y, period_month=m, scope="Hospital")
```

---

## 12. ERD

```
┌────────────────────────┐    ┌─────────────────────────┐
│ IMM Compliance Rule    │ 1──*│ IMM Compliance Finding  │
│  (rule_code PK)        │    │  (FND-...)       │
│  versioned             │    │  status, severity,      │
└────────────────────────┘    │  capa_ref ────────┐     │
                              └──────┬────────────┼─────┘
                                     │ * (source_record)│
                                     │ Dynamic Link     │
                                     ▼                  ▼
                          ┌────────────────────┐  ┌────────────────────┐
                          │  any DocType       │  │ IMM CAPA Record    │
                          │  (Asset, WO, ...)  │  │ (CAPA-YYYY-#####)  │
                          └────────────────────┘  │  LIVE — REUSE      │
                                                  │  +Custom Fields    │
┌────────────────────────┐                        │  imm_action_plan ──┼──┐
│ IMM Internal Audit     │                        │  imm_rca_ref ──────┼──┼─▶ IMM RCA Record (LIVE)
│  (AUD-INT-...)      │ 1                      │  imm_compliance_   │  │
│  scope, checklist,     │                        │   finding_ref ─────┼──┘ (back-ref)
│  findings (Audit       │                        └────────────────────┘
│   Finding child REUSE) │
└────────┬───────────────┘
         │ * (Audit Finding REUSE)
         ▼
┌────────────────────────┐
│ Audit Finding (child)  │ ─ imm_capa_link (Custom Field) ─▶ IMM CAPA Record
│  severity, category    │
│  imm_finding_link ─────┼──▶ IMM Compliance Finding
└────────────────────────┘

┌────────────────────────┐
│ IMM CAPA Action Step   │ ◀── imm_action_plan (Custom Field table)
│ (child mới)            │
└────────────────────────┘

┌────────────────────────┐  consume by   ┌────────────────────────┐
│ IMM Management Review  │ ──────────────│ IMM Compliance         │
│  (MR-...)       │  scorecard_ref│ Scorecard              │
│  quarterly, ISO 13485  │               │ (SCR-YYYY-MM-...)│
│  §5.6                  │               │ immutable after publish │
└────────────────────────┘               └────────────────────────┘

┌────────────────────────┐
│ IMM Audit Trail (LIVE) │ ◀── log_audit_event() từ mọi state-change
│  hash_sha256, prev_hash│
│  IMM-AUD-YYYY-#######  │
└────────────────────────┘
```

---

## 13. State Diagrams

### 13.1 CAPA Workflow (EXTEND existing CAPA Record)

```
                ┌───────┐
                │  Open │ ◀── create_capa (imm00.create_capa)
                └───┬───┘
                    │ submit
                    ▼
          ┌───────────────────┐
          │   Investigating   │ ◀───────────────┐ (Re-open if Not Effective)
          │   (status=        │                 │
          │    In Progress)   │                 │
          └────┬──────────────┘                 │
               │ root_cause done (VR-05)        │
               │ link imm_rca_ref               │
               ▼                                │
          ┌───────────────┐                     │
          │  Action Plan  │  (VR-12 due_date)   │
          │  (status=     │                     │
          │   In Progress)│                     │
          └────┬──────────┘                     │
               │ approved                       │
               ▼                                │
          ┌────────────────┐                    │
          │ Implementation │                    │
          │ (status=       │                    │
          │  In Progress)  │                    │
          └────┬───────────┘                    │
               │ all action_steps done          │
               ▼                                │
          ┌──────────────┐                      │
          │ Verification │                      │
          │ (status=     │                      │
          │  Pending Ver)│                      │
          └────┬─────────┘                      │
               │                                │
       ┌───────┴─────────┐                      │
       │                 │                      │
  effectiveness     effectiveness               │
   = Effective       = Not Effective ───────────┘
       │                 │
       ▼                 ▼
   ┌────────┐       ┌───────────┐
   │ Closed │       │ Re-opened │
   │ (1)    │       │ (status=  │
   └────────┘       │  In Prog) │
   (BR-16-03)       └───────────┘
                    imm_reopen_count++
```

### 13.2 Finding Workflow

```
   ┌──────┐  triage  ┌──────────────┐
   │ Open │ ──────▶  │ Under Review │
   └──────┘          └──┬───────────┘
                        │
       ┌────────────────┼─────────────────┐
       │                │                 │
       ▼                ▼                 ▼
 ┌─────────────┐  ┌──────────────┐  ┌────────┐
 │Confirmed NC │  │False Positive│  │ Waived │ (VP Block2 only)
 └──────┬──────┘  └──────────────┘  └────────┘
        │ link CAPA Record
        ▼
   ┌──────────┐  capa.Closed   ┌────────┐
   │ Resolved │ ─────────────▶│ Closed │
   └──────────┘                └────────┘
```

---

## 14. Testing Strategy

| Test type | Target | Coverage |
|---|---|---|
| Unit (service) | RuleEvaluator, ScorecardAggregator, EscalationMatrix | 90% |
| Unit (controller) | 12 VR + state transition validators | 90% |
| Unit (CAPA hook) | `capa_record_validate`, `capa_record_on_update` | 100% (existing CAPA Record dữ liệu cũ phải pass) |
| API | ~30 endpoints (success + error paths) | 100% endpoints |
| Workflow | 4 workflows × transitions với từng role | 100% |
| Scheduler | 5 jobs idempotent | Manual run + assertion |
| Integration | IMM-04→16, IMM-05→16, IMM-08→16, IMM-08←16 (BR-16-09), IMM-12 ↔ CAPA Record | E2E UAT |
| Migration patch | workflow_state mapping cho CAPA Record cũ | Idempotent + assertion |
| Performance | Rule eval 200 rules × 50 dept | < 5 phút |
| Compliance | Audit trail Frappe Version + IMM Audit Trail cho mọi DocType | 100% |

Test files (TBD):
- `assetcore/assetcore/doctype/imm_compliance_rule/test_imm_compliance_rule.py`
- `assetcore/assetcore/doctype/imm_compliance_finding/test_imm_compliance_finding.py`
- `assetcore/services/test_imm16_rule_evaluator.py`
- `assetcore/services/test_imm16_scorecard_aggregator.py`
- `assetcore/services/test_imm16_compliance_gate.py`
- `assetcore/services/test_imm16_capa_record_hook.py`
- `assetcore/patches/v0_2/test_migrate_capa_record_workflow_state.py`
