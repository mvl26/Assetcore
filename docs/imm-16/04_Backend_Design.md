# 04 — Backend Design — IMM-16 Compliance Monitoring & CAPA

| Mục | Giá trị |
|---|---|
| Module | IMM-16 — Compliance Monitoring & CAPA |
| Phiên bản | 0.3.0 |
| Ngày cập nhật | 2026-05-08 |
| Owner | Tech Lead + BE Developer |
| Liên kết | [03 Diagrams](./03_Diagrams.md) · [05 API](./05_API_Specification.md) · [07 Testing](./07_Testing_QA.md) |

> ⚠️ Pending implementation — Wave 3

---

# Phần I — DocType Catalog

| DocType | Trạng thái | Naming | Submittable | Track Changes | Vai trò |
|---|---|---|---|---|---|
| `IMM CAPA Record` | **LIVE — REUSE** | `CAPA-.YYYY.-.#####` | 1 | 1 | CAPA backbone |
| `Audit Finding` | **LIVE — REUSE** | child | 0 | 0 | Audit Finding child |
| `IMM Audit Trail` | **LIVE — REUSE** | `IMM-AUD-.YYYY.-.#######` | 0 | 0 | Hash chain |
| `IMM RCA Record` | **LIVE — REUSE** | `IMM-RCA-.YYYY.-.#####` | 1 | 1 | RCA backbone |
| `IMM Compliance Rule` | **PLANNED** | `field:rule_code` | 0 | 1 | Master rule declarative |
| `IMM Compliance Finding` | **PLANNED** | `format:FND-.YYYY.-.#####` | 0 | 1 | Non-conformance record |
| `IMM Internal Audit` | **PLANNED** | `format:AUD-INT-.YYYY.-.#####` | 0 | 1 | Internal audit cycle |
| `IMM Audit Checklist Item` | **PLANNED** | child | 0 | 0 | Audit checklist row |
| `IMM CAPA Action Step` | **PLANNED** | child | 0 | 0 | CAPA action step |
| `IMM Compliance Scorecard` | **PLANNED** | `format:SCR-.YYYY.-.MM.-.#####` | 0 | 1 | Monthly scorecard |
| `IMM Management Review` | **PLANNED** | `format:MR-.YYYY.-.#####` | 0 | 1 | Quarterly MR |
| `IMM Scorecard Module Row` | **PLANNED** | child | 0 | 0 | Score by module |
| `IMM Scorecard Department Row` | **PLANNED** | child | 0 | 0 | Score by dept |
| `IMM MR Attendee` | **PLANNED** | child | 0 | 0 | MR attendee |
| `IMM MR Output Action` | **PLANNED** | child | 0 | 0 | MR output action |

---

# Phần II — DocType Schemas

> ⚠️ Pending implementation — Wave 3

## II.1. IMM CAPA Record — REUSE + Custom Fields

**Existing schema (LIVE — KHÔNG sửa core JSON):**

`CAPA-.YYYY.-.#####`, `is_submittable=1`, `track_changes=1`.

Existing fields: `naming_series`, `asset` (Link AC Asset), `severity` (Minor/Major/Critical), `status` (Open/In Progress/Pending Verification/Closed/Overdue), `workflow_state`, `source_type`, `source_ref`, `linked_incident`, `description`, `root_cause`, `corrective_action`, `preventive_action`, `responsible`, `opened_date`, `due_date`, `closed_date`, `effectiveness_check` (Effective/Partially Effective/Not Effective), `notes`, `amended_from`.

**Custom Fields IMM-16 (PLANNED — fixture `imm16_custom_field_capa_record.json`):**

| # | fieldname | fieldtype | options / default | reqd |
|---|---|---|---|---|
| 1 | `imm_root_cause_method` | Select | `\n5-Why\nFishbone\nFMEA\nFTA\nOther` | — |
| 2 | `imm_correction_immediate` | Text | — | — |
| 3 | `imm_action_plan` | Table | `IMM CAPA Action Step` | — |
| 4 | `imm_effectiveness_check_date` | Date | — | — |
| 5 | `imm_effectiveness_evidence` | Attach | — | — |
| 6 | `imm_change_control_ref` | Data | — | — |
| 7 | `imm_risk_level` | Select | `Low\nMedium\nHigh\nCritical` | * |
| 8 | `imm_compliance_finding_ref` | Link | `IMM Compliance Finding` | — |
| 9 | `imm_audit_finding_ref` | Data | — | — |
| 10 | `imm_rca_ref` | Link | `IMM RCA Record` | — |
| 11 | `imm_reopen_count` | Int | default 0 | — |

**Extension Select option `source_type`** (qua Property Setter): thêm `Audit Finding`, `Compliance Finding`, `Management Review`.

**Permissions** (giữ nguyên 12 role đã định nghĩa trong JSON LIVE):

| Role | R | W | C | Submit | Cancel |
|---|---|---|---|---|---|
| Tổ HC-QLCL | ✅ | ✅ | ✅ | ✅ | — |
| Internal Auditor | ✅ | ✅ | ✅ | — | — |
| Workshop Head | ✅ | ✅ | ✅ | — | — |
| Biomed Engineer | ✅ | ✅ | — | — | — |
| HTM Technician | ✅ | ✅ (action step) | — | — | — |
| VP Block2 | ✅ | ✅ | — | ✅ | ✅ |
| CMMS Admin | ✅ | ✅ | ✅ | ✅ | ✅ |

## II.2. IMM Compliance Rule (PLANNED)

**Config:** `autoname: field:rule_code`, `is_submittable: 0`, `track_changes: 1`

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
| 13 | is_active | Check | default 1 | — | — |
| 14 | effective_date | Date | — | * | — |
| 15 | version | Data | default "1.0" | — | 1 |
| 16 | previous_version | Data | — | — | 1 |
| 17 | change_summary | Small Text | — | — | — |

**Permissions:**

| Role | R | W | C |
|---|---|---|---|
| Tổ HC-QLCL | ✅ | ✅ | ✅ |
| All authenticated | ✅ | — | — |
| CMMS Admin | ✅ | ✅ | ✅ |

## II.3. IMM Compliance Finding (PLANNED)

**Config:** `autoname: format:FND-.YYYY.-.#####`, `is_submittable: 0`, `track_changes: 1`

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

## II.4. IMM Internal Audit (PLANNED)

**Config:** `autoname: format:AUD-INT-.YYYY.-.#####`, `is_submittable: 0`, `track_changes: 1`

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
| 14 | **findings** | Table → **Audit Finding** (REUSE LIVE) | — |
| 15 | status | Select | Planned/In Progress/Reporting/Closed |
| 16 | findings_count | Int | read_only |
| 17 | total_score | Float | read_only |
| 18 | audit_report | Attach | — |
| 19 | management_review_ref | Link → IMM Management Review | — |
| 20 | workflow_state | Link → Workflow State | — |

## II.5. IMM Compliance Scorecard (PLANNED)

**Config:** `autoname: format:SCR-.YYYY.-.MM.-.#####`, `track_changes: 1`

| # | fieldname | fieldtype | options |
|---|---|---|---|
| 1 | period_year | Int | reqd |
| 2 | period_month | Int | reqd |
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

## II.6. IMM Management Review (PLANNED)

**Config:** `autoname: format:MR-.YYYY.-.#####`

| # | fieldname | fieldtype | options |
|---|---|---|---|
| 1 | review_date | Date | reqd |
| 2 | quarter | Data | auto Q{N}-{YYYY} |
| 3 | chair | Link → User | reqd |
| 4 | attendees | Table → IMM MR Attendee | — |
| 5 | scorecard_ref | Link → IMM Compliance Scorecard | — |
| 6 | inputs_summary | Long Text | — |
| 7 | audit_summary | Long Text | — |
| 8 | capa_summary | Long Text | — |
| 9 | capa_effectiveness | Long Text | — |
| 10 | training_compliance | Long Text | — |
| 11 | risk_review | Long Text | — |
| 12 | qms_changes_decided | Long Text | — |
| 13 | output_actions | Table → IMM MR Output Action | — |
| 14 | next_review_date | Date | — |
| 15 | minutes_doc | Attach | — |
| 16 | status | Select | Draft/Held/Minutes Approved/Closed |

---

# Phần III — Service Layer

> ⚠️ Pending implementation — Wave 3

File: `assetcore/services/imm16.py`

## III.1. Rule Evaluator

```python
class RuleEvaluator:
    def evaluate(self, rule: dict, context: dict) -> EvalResult:
        """
        Returns: EvalResult(violated: bool, current_value, threshold_value, source_record)
        Raises: ServiceError(ErrorCode.VALIDATION, "VR-01: ...") nếu threshold JSON invalid
        """
        metric = rule["threshold_definition"]["metric"]
        op = rule["threshold_definition"]["op"]
        threshold = rule["threshold_definition"]["value"]
        current = self._fetch_metric(rule, context)
        violated = self._compare(current, op, threshold)
        return EvalResult(violated, current, threshold, context["source_record"])

    METRIC_MAP = {
        "IMM-04": ["commissioning_doc_completeness"],
        "IMM-05": ["doc_expired_count", "doc_expiring_30d"],
        "IMM-06": ["training_overdue_count"],
        "IMM-08": ["pm_compliance_pct"],
        "IMM-09": ["repair_sla_breach_count"],
        "IMM-11": ["calibration_overdue_count", "oot_count"],
        "IMM-12": ["corrective_sla_breach_count"],
        "IMM-15": ["critical_spare_breach_count"],
    }
```

## III.2. Finding Upsertor (idempotent)

```python
def upsert_finding(
    rule: str,
    source_record: str,
    eval_date: str,
    current_value: Any,
) -> str:
    """
    Idempotent: UNIQUE INDEX (rule, source_record, evaluation_date) bảo đảm
    chạy nhiều lần cùng ngày không tạo bản ghi mới.
    Raises: ServiceError(ErrorCode.CREATE_ERROR, "Không thể tạo Finding") nếu insert fail
    """
    existing = frappe.db.exists("IMM Compliance Finding", {
        "rule": rule,
        "source_record": source_record,
        "evaluation_date": eval_date,
    })
    if existing:
        return existing  # idempotent

    doc = frappe.new_doc("IMM Compliance Finding")
    doc.update({...})
    doc.insert(ignore_permissions=True)
    frappe.publish_realtime("imm16:finding_created", doc.as_dict())
    imm00.log_audit_event(doc.doctype, doc.name, "created", frappe.session.user)
    return doc.name
```

## III.3. Link Finding → CAPA Record

```python
def link_finding_to_capa(finding_name: str, capa_data: dict) -> str:
    """
    Reuse imm00.create_capa để tạo IMM CAPA Record.
    Set Custom Fields IMM-16 trên CAPA Record.
    Raises: ServiceError(ErrorCode.NOT_FOUND, "Finding không tồn tại")
    """
    from assetcore.services import imm00 as svc00
    finding = frappe.get_doc("IMM Compliance Finding", finding_name)
    capa_name = svc00.create_capa(
        asset=finding.asset,
        source_type="Compliance Finding",
        source_ref=finding.name,
        severity=_map_severity_to_capa(finding.severity),
        description=f"Compliance Finding {finding.name}",
    )
    frappe.db.set_value("IMM CAPA Record", capa_name, {
        "imm_compliance_finding_ref": finding.name,
        "imm_risk_level": finding.severity,
        "workflow_state": "Open",
    })
    frappe.db.set_value("IMM Compliance Finding", finding_name, "capa_ref", capa_name)
    return capa_name
```

## III.4. Scorecard Aggregator

```python
def build_scorecard(period_year: int, period_month: int, scope: str = "Hospital") -> str:
    """
    Aggregate findings tháng → sinh IMM Compliance Scorecard Draft.
    Formula: score_pct = (total - non_compliant) / total × 100
    Raises: ServiceError(ErrorCode.CREATE_ERROR, "Không thể tạo Scorecard")
    """
    findings = frappe.get_all("IMM Compliance Finding", filters={
        "evaluation_date": ["between", (start_of_month, end_of_month)],
        "status": ["!=", "False Positive"],
    }, fields=["rule", "responsible_dept", "status", "severity"])

    total = len(findings)
    nc = sum(1 for f in findings if f.status in ("Confirmed NC", "Resolved", "Closed"))
    score = round((total - nc) / total * 100, 2) if total else 100.0

    sc = frappe.new_doc("IMM Compliance Scorecard")
    sc.update({
        "period_year": period_year,
        "period_month": period_month,
        "scope": scope,
        "total_rules_evaluated": total,
        "non_compliant_count": nc,
        "compliant_count": total - nc,
        "score_pct": score,
        "score_by_module": _aggregate_by_module(findings),
        "score_by_department": _aggregate_by_dept(findings),
        "trend_vs_prev_month": _compute_trend(period_year, period_month, score),
        "generated_at": now(),
        "is_published": 0,
    })
    sc.insert(ignore_permissions=True)
    return sc.name
```

## III.5. Escalation Matrix

```python
ESCALATION = {
    "High":     {"L1": 3,  "L2": 7,  "L3": 14},  # overdue days → level
    "Critical": {"L1": 1,  "L2": 3,  "L3": 7},
}
RECIPIENTS = {
    "L1": ["responsible"],
    "L2": ["workshop_head", "responsible"],
    "L3": ["vp_block2", "truong_phong", "workshop_head"],
}

def escalate(capa_record: dict) -> None:
    """
    Gửi email escalation theo level dựa trên imm_risk_level + overdue_days.
    Idempotent: ghi log IMM Audit Trail để tránh gửi trùng cùng ngày.
    Raises: ServiceError(ErrorCode.VALIDATION, "CAPA không có risk_level")
    """
    overdue_days = (getdate(today()) - getdate(capa_record.due_date)).days
    level = _compute_level(capa_record.get("imm_risk_level"), overdue_days)
    if not _already_escalated_today(capa_record.name, level):
        _send_email(RECIPIENTS[level], capa_record)
        imm00.log_audit_event("IMM CAPA Record", capa_record.name,
                              f"escalated_L{level}", "system")
```

## III.6. Compliance Gate (BR-16-09)

```python
def check_asset_compliance_status(asset: str) -> dict:
    """
    Gọi bởi services/imm08.py + services/imm09.py validate_* trước WO Submit.
    Cũng gọi bởi IMM-13/14 trước decommission.
    Returns: {blocked: bool, reasons: list, active_capas_count: int}
    Raises: ServiceError(ErrorCode.NOT_FOUND, "Asset không tồn tại")
    """
    crit_open = frappe.get_all("IMM CAPA Record", filters={
        "asset": asset,
        "imm_risk_level": "Critical",
        "status": ["in", ["Open", "In Progress", "Pending Verification"]],
    }, pluck="name")
    if crit_open:
        return {
            "blocked": True,
            "reasons": [{"type": "CAPA_CRITICAL_OPEN", "ref": n} for n in crit_open],
            "active_capas_count": len(crit_open),
        }
    return {"blocked": False, "active_capas_count": 0}
```

---

# Phần IV — Controller Hooks

> ⚠️ Pending implementation — Wave 3

## IV.1. IMM Compliance Rule (mới)

```python
class IMMComplianceRule(Document):
    def validate(self):
        self.vr_01_threshold_json_schema()
        self.vr_02_evaluation_frequency()

    def before_save(self):
        if self.has_value_changed("threshold_definition") or \
           self.has_value_changed("severity"):
            self.vr_11_rule_change_summary()
            self.previous_version = self.version
            self.version = self._bump_version(self.version)

    def _bump_version(self, v: str) -> str:
        major, minor = v.split(".")
        return f"{major}.{int(minor) + 1}"
```

## IV.2. IMM CAPA Record — doc_events (KHÔNG sửa core controller)

Đăng ký trong `hooks.py`:

```python
doc_events = {
    "IMM CAPA Record": {
        "validate": "assetcore.services.imm16.capa_record_validate",
        "on_update": "assetcore.services.imm16.capa_record_on_update",
    },
    "Asset Commissioning": {
        "on_submit": "assetcore.services.imm16.eval_imm04_realtime",
    },
    "Asset Document": {
        "on_update": "assetcore.services.imm16.eval_imm05_realtime",
    },
    "Work Order": {
        "on_submit": "assetcore.services.imm16.eval_imm08_09_realtime",
        "validate":  "assetcore.services.imm16.gate_wo_submit",  # BR-16-09
    },
    "Calibration Record": {
        "on_submit": "assetcore.services.imm16.eval_imm11_realtime",
    },
}
```

```python
# services/imm16.py

def capa_record_validate(doc, method=None):
    """VR-05, VR-06, VR-07, VR-12 enforce."""
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
    """Cascade Finding → Resolved khi CAPA Closed; re-open detection."""
    if doc.status == "Closed" and doc.source_type == "Compliance Finding":
        frappe.db.set_value(
            "IMM Compliance Finding", doc.source_ref, "status", "Resolved"
        )
    if doc.has_value_changed("status") and doc.status == "In Progress" \
       and (doc.get_db_value("status") == "Closed"):
        new_count = (doc.get("imm_reopen_count") or 0) + 1
        doc.db_set("imm_reopen_count", new_count)
        doc.db_set("workflow_state", "Investigating")
```

## IV.3. IMM Compliance Scorecard

```python
class IMMComplianceScorecard(Document):
    def validate(self):
        """VR-09: immutable sau publish."""
        if self.is_published and self._has_changed_after_publish():
            frappe.throw(_(
                "VR-09: Scorecard đã publish, không thể sửa. Hãy tạo restate mới."
            ))

    def _has_changed_after_publish(self) -> bool:
        if self.get_db_value("is_published"):
            # kiểm tra field nào thay đổi ngoài approved_by/published_at
            return bool(self.get_all_children_changes() or self.has_value_changed("score_pct"))
        return False
```

---

# Phần V — Workflow

> ⚠️ Pending implementation — Wave 3

## V.1. Finding Workflow (`imm_16_finding_workflow.json`)

| State | doc_status | Type | Transitions |
|---|---|---|---|
| Open | 0 | Warning | → Under Review (Tổ HC-QLCL / Internal Auditor) |
| Under Review | 0 | Warning | → Confirmed NC / False Positive (QLCL) ; → Waived (VP Block2 only) |
| Confirmed NC | 0 | Danger | → Resolved (auto khi CAPA Closed) |
| False Positive | 0 | Default | terminal |
| Waived | 1 | Default | terminal (auto re-open sau expiry) |
| Resolved | 1 | Success | → Closed (Tổ HC-QLCL) |
| Closed | 2 | Success | terminal |

**Workflow actions (Vietnamese):** "Chuyển sang Xem xét", "Xác nhận NC", "Đánh dấu Sai", "Miễn áp dụng", "Đánh dấu Đã giải quyết", "Đóng"

## V.2. Internal Audit Workflow (`imm_16_audit_workflow.json`)

| State | doc_status | Type | Allowed roles |
|---|---|---|---|
| Planned | 0 | Default | Tổ HC-QLCL, CMMS Admin |
| In Progress | 0 | Warning | Tổ HC-QLCL, Internal Auditor, CMMS Admin |
| Reporting | 0 | Warning | Tổ HC-QLCL, CMMS Admin |
| Closed | 1 | Success | Tổ HC-QLCL, VP Block2, CMMS Admin |

**Workflow actions:** "Bắt đầu Audit", "Chuyển sang Báo cáo", "Đóng Audit"

## V.3. CAPA Workflow — EXTEND (`imm_16_capa_workflow.json`)

| workflow_state | mapped status | doc_status | Type |
|---|---|---|---|
| Open | Open | 0 | Default |
| Investigating | In Progress | 0 | Warning |
| Action Plan | In Progress | 0 | Warning |
| Implementation | In Progress | 0 | Warning |
| Verification | Pending Verification | 0 | Warning |
| Closed | Closed | 1 | Success |
| Re-opened | In Progress | 0 | Danger |

**Workflow actions:** "Gửi điều tra", "Lên kế hoạch hành động", "Bắt đầu thực thi", "Chuyển sang Xác minh", "Đóng CAPA", "Mở lại"

## V.4. Management Review Workflow (`imm_16_mr_workflow.json`)

| State | doc_status | Type |
|---|---|---|
| Draft | 0 | Default |
| Held | 0 | Warning |
| Minutes Approved | 1 | Success |
| Closed | 1 | Success |

**Workflow actions:** "Đánh dấu Đã họp", "Phê duyệt Biên bản", "Đóng"

---

# Phần VI — Schedulers

> ⚠️ Pending implementation — Wave 3

File: `assetcore/tasks.py` (EXTEND — không tạo file mới)

## VI.1. `run_compliance_evaluation_hourly()` + `run_compliance_evaluation_daily()`

```python
def run_compliance_evaluation_daily():
    """
    Đánh giá toàn bộ active rules theo evaluation_frequency.
    Chạy: Daily 00:15 UTC+7
    Pattern: for each rule → for each context → RuleEvaluator.evaluate() → upsert_finding()
    """
    rules = frappe.get_all("IMM Compliance Rule",
        filters={"is_active": 1, "evaluation_frequency": ["in", ["Daily", "Weekly", "Monthly"]]},
        fields=["*"])
    for rule in rules:
        if _is_due(rule):
            _run_rule(rule)
```

| Job | Lịch | Cadence |
|---|---|---|
| `run_compliance_evaluation_hourly` | Hourly | Stock breach IMM-15 |
| `run_compliance_evaluation_daily` | Daily 00:15 | Doc expiry, training, calibration |
| `run_compliance_evaluation_weekly` | Weekly Mon | SLA review IMM-09/12 |
| `update_compliance_scorecard` | Monthly 1st 03:00 | Tổng hợp Scorecard tháng trước |
| `check_capa_due_imm16` | Daily 02:00 | CAPA overdue + escalation |
| `check_audit_milestones` | Daily 02:30 | Cảnh báo Lead Auditor 7d trước |
| `check_management_review_due` | Weekly Monday 08:00 | Cảnh báo quý thiếu MR |

## VI.2. `check_capa_due_imm16()` — Daily 02:00

```python
def check_capa_due_imm16():
    """
    Reuse imm00.check_capa_overdue; IMM-16 thêm tiered escalation matrix.
    """
    from assetcore.services.imm16 import EscalationMatrix
    esc = EscalationMatrix()
    overdue_capas = frappe.get_all("IMM CAPA Record",
        filters={"status": ["not in", ["Closed", "Cancelled"]], "due_date": ["<", today()]},
        fields=["*"])
    for capa in overdue_capas:
        esc.escalate(capa)
```

---

# Phần VII — Database Indexes

> ⚠️ Pending implementation — Wave 3

```sql
-- Idempotent upsert (NFR-16-03)
CREATE UNIQUE INDEX idx_finding_idem
  ON `tabIMM Compliance Finding` (rule, source_record, evaluation_date);

-- Dashboard filter
CREATE INDEX idx_finding_status_sev
  ON `tabIMM Compliance Finding` (status, severity);

-- Heatmap aggregation
CREATE INDEX idx_finding_dept_status
  ON `tabIMM Compliance Finding` (responsible_dept, status, severity);

-- Asset-centric query
CREATE INDEX idx_finding_asset
  ON `tabIMM Compliance Finding` (asset);

-- BR-16-09 gate query (composite on Custom Field)
CREATE INDEX idx_capa_gate
  ON `tabIMM CAPA Record` (asset, imm_risk_level, status);

-- CAPA due check
CREATE INDEX idx_capa_due
  ON `tabIMM CAPA Record` (status, due_date);

-- Audit milestone check
CREATE INDEX idx_audit_status_start
  ON `tabIMM Internal Audit` (status, planned_start);

-- Scorecard lookup by period
CREATE INDEX idx_scorecard_period
  ON `tabIMM Compliance Scorecard` (period_year, period_month, scope, scope_value);

-- MR quarterly check
CREATE INDEX idx_mr_quarter
  ON `tabIMM Management Review` (quarter, status);
```

| Bảng | Index | Lý do |
|---|---|---|
| `tabIMM Compliance Finding` | `(rule, source_record, evaluation_date)` UNIQUE | Idempotent upsert |
| `tabIMM Compliance Finding` | `(status, severity)` | Dashboard filter |
| `tabIMM Compliance Finding` | `(responsible_dept, status, severity)` | Heatmap aggregation |
| `tabIMM Compliance Finding` | `asset` | Asset-centric query |
| `tabIMM CAPA Record` | `(asset, imm_risk_level, status)` | BR-16-09 gate |
| `tabIMM CAPA Record` | `(status, due_date)` | CAPA due scheduler |
| `tabIMM Internal Audit` | `(status, planned_start)` | Audit milestone check |
| `tabIMM Compliance Scorecard` | `(period_year, period_month, scope, scope_value)` | Scorecard lookup |
| `tabIMM Management Review` | `(quarter, status)` | MR quarterly gate |
