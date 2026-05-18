# 04 — Backend Design — IMM-16 Compliance Monitoring & CAPA

| Mục | Giá trị |
|---|---|
| Module | IMM-16 — Compliance Monitoring & CAPA |
| Phiên bản | 0.5.0 |
| Ngày cập nhật | 2026-05-18 |
| Owner | Tech Lead + BE Developer |
| Liên kết | [03 Diagrams](./03_Diagrams.md) · [05 API](./05_API_Specification.md) · [07 Testing](./07_Testing_QA.md) |

> ✅ Implemented — Wave 2 (feature/hieuc/wave-2). 11 DocType IMM-16 đã có JSON + controller trong `assetcore/assetcore/doctype/imm_compliance_*`, `imm_internal_audit`, `imm_management_review`, `imm_capa_*`, `imm_audit_*`. Service `assetcore/services/imm16.py` (2076 dòng) + `assetcore/api/imm16.py` (424 dòng / 42 whitelist functions) LIVE.

---

# Phần I — DocType Catalog

| DocType | Trạng thái | Naming | Submittable | Track Changes | Vai trò |
|---|---|---|---|---|---|
| `IMM CAPA Record` | **LIVE** | `CAPA-.YYYY.-.#####` | 1 | 1 | CAPA backbone (extended với CF IMM-16) |
| `IMM CAPA Action Step` | **LIVE** | child | 0 | 0 | Action plan step (Wave 2) |
| `Audit Finding` | **LIVE — REUSE** | child | 0 | 0 | Audit Finding child |
| `IMM Audit Trail` | **LIVE** | `IMM-AUD-.YYYY.-.#######` | 0 | 0 | Hash chain |
| `IMM RCA Record` | **LIVE — REUSE** | `IMM-RCA-.YYYY.-.#####` | 1 | 1 | RCA backbone |
| `IMM Compliance Rule` | **LIVE** | `field:rule_code` | 0 | 1 | Master rule declarative |
| `IMM Compliance Finding` | **LIVE** | `format:FND-.YYYY.-.#####` | 0 | 1 | Non-conformance record |
| `IMM Internal Audit` | **LIVE** | `format:AUD-INT-.YYYY.-.#####` | 0 | 1 | Internal audit cycle |
| `IMM Audit Checklist Item` | **LIVE** | child | 0 | 0 | Audit checklist row |
| `IMM Compliance Scorecard` | **LIVE** | `format:SCR-.YYYY.-.MM.-.#####` | 0 | 1 | Monthly scorecard |
| `IMM Management Review` | **LIVE** | `MR-.YYYY.-.#####` (Naming Series) | 0 | 0 | Quarterly MR — `is_submittable=0` (confirmed from JSON) |
| `IMM Scorecard Module Row` | **LIVE** (child Table field trong `IMM Compliance Scorecard`) | child | 0 | 0 | Score by module — `generate_scorecard()` aggregate runtime; child rows KHÔNG được populate tự động bởi service hiện tại (field tồn tại trong JSON nhưng không có data writes) |
| `IMM Scorecard Department Row` | **LIVE** (child Table field trong `IMM Compliance Scorecard`) | child | 0 | 0 | Score by dept — tương tự, field tồn tại nhưng service không ghi rows |
| `IMM MR Attendee` | **LIVE** (DocType folder `imm_mr_attendee/` tồn tại; Table field `attendees` trong MR) | child | 0 | 0 | MR attendee list — được ghi bởi `update_management_review()` |
| `IMM MR Output Action` | **LIVE** (DocType folder `imm_mr_output_action/` tồn tại; Table field `output_actions` trong MR) | child | 0 | 0 | MR output actions — được ghi bởi `update_management_review()` + `finalize_management_review()` |

---

# Phần II — DocType Schemas

> ✅ Implemented — Wave 2. Spec dưới đây đã được code hoá trong `assetcore/services/imm16.py`.

## II.1. IMM CAPA Record — REUSE + Custom Fields

**Existing schema (LIVE — KHÔNG sửa core JSON):**

`CAPA-.YYYY.-.#####`, `is_submittable=1`, `track_changes=1`.

Existing fields: `naming_series`, `asset` (Link AC Asset), `severity` (Minor/Major/Critical), `status` (Open/In Progress/Pending Verification/Closed/Overdue), `workflow_state`, `source_type`, `source_ref`, `linked_incident`, `description`, `root_cause`, `corrective_action`, `preventive_action`, `responsible`, `opened_date`, `due_date`, `closed_date`, `effectiveness_check` (Effective/Partially Effective/Not Effective), `notes`, `amended_from`.

**Custom Fields IMM-16 (LIVE — đã trong core `imm_capa_record.json` tại `section_imm16`):**

> Xác nhận từ `imm_capa_record.json` (2026-05-18): các fields dưới đây đã là core JSON fields, KHÔNG còn là custom fields fixture riêng. Fixture `imm16_custom_field_capa_record.json` có thể tồn tại như backup nhưng data thực tế từ core JSON.

| # | fieldname | fieldtype | options / default | reqd | Ghi chú |
|---|---|---|---|---|---|
| 1 | `imm_root_cause_method` | Select | `\n5-Why\nFishbone\nFault Tree\nPareto\nOther` | — | LIVE trong JSON |
| 2 | `imm_effectiveness_evidence` | Data | — | — | LIVE (Data, không phải Attach) |
| 3 | `imm_risk_level` | Select | `\nLow\nMedium\nHigh\nCritical` | — | LIVE trong JSON |
| 4 | `imm_compliance_finding_ref` | Link | `IMM Compliance Finding` | — | LIVE trong JSON |
| 5 | `imm_reopen_count` | Int | default 0, read_only | — | LIVE trong JSON |

> **NOT in JSON**: `imm_correction_immediate`, `imm_action_plan` (Table), `imm_effectiveness_check_date`, `imm_change_control_ref`, `imm_audit_finding_ref`, `imm_rca_ref` — các fields này trong spec BA nhưng chưa được code hoá vào JSON. `advance_capa_state()` tham chiếu `doc.imm_action_plan` tại bước Implementation/Verification nhưng nếu field không có trong schema thì `getattr(doc, "imm_action_plan", None)` trả `None` và validation bị bypass.

**`source_type` options (từ JSON thực tế):** `Incident Report`, `Non-Conformance`, `Complaint`, `PM Work Order`, `IMM Asset Calibration`, `Asset Repair`, `IMM Compliance Finding`, `Cycle Count Variance`, `Critical Stock Breach`.

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

> ✅ Implemented — Wave 2. File: `assetcore/services/imm16.py` (2076 dòng).
>
> **Lưu ý**: Spec pseudocode BA (III.1–III.6 cũ) là design target. Implementation thực tế dùng flat functions thay vì class. Xem §III.A–III.G dưới đây cho danh sách function thực tế.

## III.A. Compliance Rule

| Function | Signature | Ghi chú |
|---|---|---|
| `list_compliance_rules(filters, *, page, page_size)` | `→ dict` | list + normalize_filters |
| `create_compliance_rule(data)` | `→ dict` | VR-01 threshold JSON validate |
| `get_rule(name)` | `→ dict` | chi tiết rule |
| `update_rule(name, rule_data, change_summary)` | `→ dict` | VR-11 version bump |
| `deactivate_rule(name)` | `→ dict` | set is_active=0 |
| `reactivate_rule(name)` | `→ dict` | set is_active=1 (BUG-16-02 fix) |

## III.B. Compliance Finding

| Function | Signature | Ghi chú |
|---|---|---|
| `list_compliance_findings(filters, *, page, page_size)` | `→ dict` | enrich asset_name |
| `create_finding(rule_ref, asset_ref, work_order_ref, severity, description, evaluation_date, actual_value, threshold_value)` | `→ dict` | idempotent; auto-CAPA nếu Critical |
| `get_finding(name)` | `→ dict` | enrich asset_name, responsible_dept_name, rule_name |
| `confirm_finding(name, reviewer_note)` | `→ dict` | → Confirmed NC + audit trail |
| `mark_false_positive(name, reason)` | `→ dict` | reason required |
| `waive_finding(name, waiver_reason, waiver_evidence, waiver_expiry)` | `→ dict` | VR-04: reason ≥ 50 chars, evidence, expiry > today |
| `link_finding_to_capa(name, capa_ref)` | `→ dict` | set finding.capa_ref |
| `close_finding(finding_name, capa_ref, resolution_note)` | `→ dict` | → Resolved |

## III.C. Internal Audit

| Function | Signature | Ghi chú |
|---|---|---|
| `list_internal_audits(filters, *, page, page_size)` | `→ dict` | enrich lead_auditor_name |
| `create_internal_audit(data)` | `→ dict` | alias: `create_audit` |
| `get_audit(name)` | `→ dict` | enrich lead_auditor_name |
| `start_audit(name)` | `→ dict` | Planned → In Progress |
| `submit_audit_findings(audit_name, findings)` | `→ dict` | batch create findings + → Reporting |
| `complete_audit_checklist(audit_name, items)` | `→ dict` | auto-Finding cho Major/Minor NC |
| `close_audit(name, audit_report)` | `→ dict` | VR-08: block nếu Major NC chưa CAPA |
| `close_internal_audit(audit_name)` | `→ dict` | legacy alias |

## III.D. CAPA

`_CAPA_TRANSITIONS` (code thực tế):
```
Open → Investigating
Investigating → Action Plan
Action Plan → Implementation
Implementation → Verification
Verification → {Closed, Re-opened}
Re-opened → Investigating
```

| Function | Signature | Ghi chú |
|---|---|---|
| `create_capa_from_finding(finding_name, imm_risk_level, imm_root_cause_method, responsible, due_date)` | `→ dict` | gọi `imm00.create_capa` + set IMM-16 custom fields |
| `get_capa(name)` | `→ dict` | enrich asset_name, responsible_name, finding_ref (BUG-16-08) |
| `update_capa_fields(name, data)` | `→ dict` | editable fields khi chưa Closed |
| `advance_capa_state(name, target_state, payload)` | `→ dict` | VR-05/06/07/12 enforcement |
| `perform_effectiveness_check(name, result, effectiveness_evidence)` | `→ dict` | Effective→Closed; Not Effective→Re-opened + reopen_count++ |
| `reopen_capa(name, reason)` | `→ dict` | force → Re-opened |

## III.E. Compliance Scorecard

`generate_scorecard()` **không ghi child rows** `score_by_module`/`score_by_department` vào DB — các field này là Table nhưng service chỉ tính runtime và không append rows. `score_pct` được tính từ `Confirmed NC` counts (không phải Resolved/Closed).

| Function | Signature | Ghi chú |
|---|---|---|
| `generate_scorecard(module_ref, period)` | `→ dict` | tạo Scorecard record; runtime aggregate |
| `list_scorecards(filters, *, page, page_size)` | `→ dict` | |
| `get_current_scorecard(scope)` | `→ dict` | delegate → get_scorecard_by_period(today) |
| `get_scorecard_by_period(year, month, scope)` | `→ dict` | |
| `publish_scorecard(name)` | `→ dict` | VR-09 immutable; VR-10 gate quý trước MR |
| `validate_scorecard_immutability(doc)` | controller hook | score_pct + non_compliant_count immutable sau publish |

## III.F. Management Review

`_MR_TRANSITIONS`:
```
Draft → Held
Held → Minutes Approved
Minutes Approved → Closed  (nhưng close phải đi qua finalize_management_review)
```

| Function | Signature | Ghi chú |
|---|---|---|
| `list_management_reviews(filters, *, page, page_size)` | `→ dict` | enrich chair_name, scorecard_score_pct |
| `get_management_review(name)` | `→ dict` | enrich chair_name + scorecard (BUG-16-10) |
| `create_management_review(data)` | `→ dict` | unique per quarter |
| `update_management_review(name, data)` | `→ dict` | scalar fields + attendees + output_actions child |
| `advance_mr_state(name, target_state)` | `→ dict` | Draft→Held→Minutes Approved; không cho→Closed (dùng finalize) |
| `finalize_management_review(name, minutes_doc, output_actions)` | `→ dict` | Closed + attach minutes + VR: ≥1 output action |

## III.G. Dashboard / Reports / Cross-module

| Function | Signature | Ghi chú |
|---|---|---|
| `get_dashboard_stats()` | `→ dict` | KPIs + trend_12m + recent_findings |
| `get_compliance_heatmap(period_year, period_month)` | `→ dict` | Module×Dept matrix (BUG-16-11: source_module từ Rule, BUG-16-04: dept label) |
| `get_capa_aging()` | `→ dict` | buckets: 0-7d/8-30d/31-60d/60+ |
| `get_overdue_actions()` | `→ dict` | overdue findings (>30d) + overdue CAPAs |
| `check_asset_compliance_status(asset)` | `→ dict` | BR-16-09 gate; blocked=True nếu Critical CAPA open |
| `get_record_history(ref_doctype, ref_name, limit)` | `→ dict` | audit trail cho Finding/CAPA/MR/Rule |

## III.H. Doc-event Real-time Evaluators

| Function | Trigger DocType |
|---|---|
| `eval_imm04_realtime(doc, method)` | `Asset Commissioning.on_submit` |
| `eval_imm05_realtime(doc, method)` | `AC Asset Document.on_update` (khi workflow_state=Expired) |
| `eval_imm08_09_realtime(doc, method)` | `IMM PM Work Order.on_submit`, `IMM CM Work Order.on_submit` |
| `eval_imm11_realtime(doc, method)` | `IMM Calibration Record.on_submit` |
| `gate_wo_submit(doc, method)` | `IMM PM Work Order.validate`, `IMM CM Work Order.validate` |

---

# Phần IV — Controller Hooks

> ✅ Implemented — Wave 2. Spec dưới đây đã được code hoá trong `assetcore/services/imm16.py`.

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

Hook thực tế tại `assetcore/hooks.py` (verified 2026-05-14):

```python
doc_events = {
    "IMM CAPA Record": {
        "validate":      "assetcore.services.imm16.capa_record_validate",
        "before_submit": "assetcore.services.imm16.capa_record_before_submit",
        "on_update":     "assetcore.services.imm16.capa_record_on_update",
    },
    "Asset Commissioning": {
        "on_submit": "assetcore.services.imm16.eval_imm04_realtime",
    },
    "AC Asset Document": {
        "on_update": "assetcore.services.imm16.eval_imm05_realtime",
    },
    "IMM PM Work Order": {
        "validate":  "assetcore.services.imm16.gate_wo_submit",       # BR-16-09
        "on_submit": "assetcore.services.imm16.eval_imm08_09_realtime",
        # plus reservation hook from IMM-15
    },
    "IMM CM Work Order": {
        "validate":  "assetcore.services.imm16.gate_wo_submit",
        "on_submit": "assetcore.services.imm16.eval_imm08_09_realtime",
    },
    "IMM Calibration Record": {
        "on_submit": "assetcore.services.imm16.eval_imm11_realtime",
    },
}

# Scheduler — flat namespace
scheduler_events = {
    "hourly":  ["assetcore.services.imm16.run_compliance_evaluation_hourly"],
    "daily":   [
        "assetcore.services.imm16.evaluate_all_compliance_rules",
        "assetcore.services.imm16.check_capa_due",
        "assetcore.services.imm16.check_audit_milestones",
    ],
    "weekly":  [
        "assetcore.services.imm16.run_compliance_evaluation_weekly",
        "assetcore.services.imm16.check_management_review_due",
    ],
    "monthly": ["assetcore.services.imm16.update_compliance_scorecard"],
}
```

> Khác biệt vs spec draft 0.3.0: DocType ràng buộc gate đổi từ generic `Work Order` → cụ thể `IMM PM Work Order` + `IMM CM Work Order` (AssetCore không dùng ERPNext core `Work Order`). Asset document hook bám DocType `AC Asset Document`. CAPA có thêm `before_submit` hook.

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

> ✅ Implemented — Wave 2. Spec dưới đây đã được code hoá trong `assetcore/services/imm16.py`.

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

> ✅ Implemented — Wave 2. Spec dưới đây đã được code hoá trong `assetcore/services/imm16.py`.

File: `assetcore/services/imm16.py` (không phải `tasks.py` — tất cả scheduler functions trong service file)

## VI.1. Scheduler jobs thực tế (verified từ hooks.py 2026-05-18)

| Job | hooks.py entry | Cadence | Rules filter |
|---|---|---|---|
| `run_compliance_evaluation_hourly` | `hourly` | Hourly | evaluation_frequency IN (Hourly, Realtime) |
| `evaluate_all_compliance_rules` | `daily` | Daily | evaluation_frequency IN (Daily, Realtime, Hourly) |
| `check_capa_due` | `daily` | Daily | overdue CAPA escalation (tiered: Critical ≥1d, High ≥3d) |
| `check_audit_milestones` | `daily` | Daily | Planned audit bắt đầu trong 7 ngày → email Lead Auditor |
| `run_compliance_evaluation_weekly` | `weekly` | Weekly Monday | evaluation_frequency = Weekly |
| `check_management_review_due` | `weekly` | Weekly Monday | Quý hiện tại chưa có MR Closed → alert |
| `update_compliance_scorecard` | `monthly` | Monthly 1st | Tổng hợp Scorecard tháng trước; skip nếu đã tồn tại |

> **Khác biệt vs spec cũ**: `run_compliance_evaluation_daily` KHÔNG tồn tại — thay bằng `evaluate_all_compliance_rules` (daily). `check_capa_due_imm16` → đổi tên thành `check_capa_due`. Không có `EscalationMatrix` class — escalation logic inline trong `_escalate_capa()` / `_send_capa_escalation()`.

## VI.2. Escalation thực tế

Trong `_escalate_capa(capa)`:
- `imm_risk_level = Critical` + overdue ≥ 1 ngày → Level 1 (email `responsible`)
- `imm_risk_level IN (High, Critical)` + overdue ≥ 3 ngày → Level 2 (email `responsible` + tất cả `IMM Workshop Lead`)

---

# Phần VII — Database Indexes

> ✅ Implemented — Wave 2. Spec dưới đây đã được code hoá trong `assetcore/services/imm16.py`.

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
