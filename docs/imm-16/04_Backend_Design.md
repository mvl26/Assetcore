# 04 — Backend Design — IMM-16 Compliance Monitoring & CAPA

| Mục | Giá trị |
|---|---|
| Module | IMM-16 — Compliance Monitoring & CAPA |
| Phiên bản | 0.0.2 (đồng bộ `assetcore/__init__.py`) |
| Ngày cập nhật | 2026-05-27 |
| Owner | Tech Lead + BE Developer |
| Liên kết | [03 Diagrams](./03_Diagrams.md) · [05 API](./05_API_Specification.md) · [07 Testing](./07_Testing_QA.md) |

> ✅ Implemented — Wave 2 (feature/hieuc/wave-2). 11 DocType IMM-16 đã có JSON + controller trong `assetcore/assetcore/doctype/imm_compliance_*`, `imm_internal_audit`, `imm_management_review`, `imm_capa_*`, `imm_audit_*`. Service `assetcore/services/imm16.py` (2076 dòng) + `assetcore/api/imm16.py` (423 dòng / 52 whitelist functions) LIVE.

---

# Phần I — DocType Catalog

| DocType | Trạng thái | Naming | Submittable | Track Changes | Vai trò |
|---|---|---|---|---|---|
| `IMM CAPA Record` | **LIVE** (shared owner với IMM-12) | `CAPA-.YYYY.-.#####` | 1 | 1 | CAPA backbone — DocType **shared cross-module**: IMM-12 sở hữu CAPA từ Incident/RCA; IMM-16 extend lifecycle (6 sub-states) + Compliance Finding source. Cùng 1 DocType, hai entrypoint. |
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
| 6 | `escalation_level` | Int | default 0, read_only | — | **NEW Vòng 13 — cần `bench migrate`.** Mức leo thang cao nhất ĐÃ gửi cho CAPA này (0/1/2). Bút toán hệ thống của `_escalate_capa` → idempotency cron daily (INV-CAPA-ESC-3). Đặt sau section Verification, trước `notes`. `api/imm16.py` delegate verbatim → field tự lộ qua `get_capa`, KHÔNG cần sửa endpoint. |

> **NOT in JSON**: `imm_correction_immediate`, `imm_action_plan` (Table), `imm_effectiveness_check_date`, `imm_change_control_ref`, `imm_audit_finding_ref`, `imm_rca_ref` — các fields này trong spec BA nhưng chưa được code hoá vào JSON. `advance_capa_state()` tham chiếu `doc.imm_action_plan` tại bước Implementation/Verification nhưng nếu field không có trong schema thì `getattr(doc, "imm_action_plan", None)` trả `None` và validation bị bypass.

**`source_type` options (từ JSON thực tế):** `Incident Report`, `Non-Conformance`, `Complaint`, `PM Work Order`, `IMM Asset Calibration`, `Asset Repair`, `IMM Compliance Finding`, `Cycle Count Variance`, `Critical Stock Breach`.

**Permissions** (mapping vào 30-role catalog — `assetcore/fixtures/role.json`):

| Role hệ thống | R | W | C | Submit | Cancel |
|---|---|---|---|---|---|
| Compliance Manager | ✅ | ✅ | ✅ | ✅ | — |
| Compliance User | ✅ | ✅ | ✅ | — | — |
| Corrective Manager (IMM-09) | ✅ | ✅ | ✅ | — | — |
| Corrective User / PM User | ✅ | ✅ (action step) | — | — | — |
| AssetCore Auditor | ✅ | — | — | — | — |
| AssetCore Super Admin | ✅ | ✅ | ✅ | ✅ | ✅ |

## II.2. IMM Compliance Rule (LIVE)

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

| Role hệ thống | R | W | C |
|---|---|---|---|
| Compliance Manager | ✅ | ✅ | ✅ |
| AssetCore System User (all authenticated) | ✅ | — | — |
| AssetCore Super Admin | ✅ | ✅ | ✅ |

## II.3. IMM Compliance Finding (LIVE)

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

## II.4. IMM Internal Audit (LIVE)

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

### II.4b. IMM Audit Checklist Item (child — LIVE, `istable:1`)

Child của `checklist_items` (§II.4 #13). Schema thật (`imm_audit_checklist_item.json`) — dùng để ground CR-27b:

| # | fieldname | fieldtype | options / ghi chú |
|---|---|---|---|
| 1 | item_description | Data (reqd) | mô tả mục kiểm |
| 2 | category | Select | `Document / Process / System` |
| 3 | criteria | Text | tiêu chí |
| 4 | **result** | **Select** | **`Conforming / Non-Conforming / Not Applicable`** — **field persist verdict, round-trip qua `get_audit`** (SSoT verdict) |
| 5 | evidence | Attach | bằng chứng |
| 6 | notes | Small Text | ghi chú (persist verbatim) |
| 7 | finding_ref | Link → **Audit Finding** | ⚠️ KHÔNG dùng cho backlink `IMM Compliance Finding` (kiểu Link khác doctype) — xem §III.C.1c |

> **KHÔNG có field** `finding_status`, `clause_ref`, `linked_finding` — 3 assign `hasattr(child, …)` tương ứng ở service là **no-op câm**. CR-27b LOẠI 2 assign đầu (`finding_status`/`clause_ref`) + map `finding_status → result`. **CR-27d LOẠI nốt assign thứ 3** (`if hasattr(child, "linked_finding")`): child KHÔNG có `linked_finding`, và `finding_ref` trỏ doctype `Audit Finding` ≠ `IMM Compliance Finding` (Link-validation reject nếu nhét tên Finding vào) → backlink row→finding **BỎ**; liên kết finding→audit đi qua `source_record_doctype='IMM Internal Audit'` + `source_record=<audit>` (SSoT forward-link, đủ cho truy vấn theo audit). Backlink cấp-dòng = `[ROADMAP]` (cần field Link mới `linked_compliance_finding` nếu về sau bắt buộc). Payload DTO `finding_status` (enum `Compliant/Minor NC/Major NC/N/A`) chỉ tồn tại ở lớp API/FE (`frontend/src/api/imm16.ts:378`) — service map sang `result` (bảng ở 05 §3.3.5), KHÔNG persist tên DTO.

## II.5. IMM Compliance Scorecard (LIVE)

**Config:** `autoname: format:SCR-.YYYY.-.MM.-.#####`, `track_changes: 1`

| # | fieldname | fieldtype | options |
|---|---|---|---|
| 1 | period_year | Int | reqd |
| 2 | period_month | Int | reqd |
| 3 | scope | Select | Hospital/Block/Department |
| 4 | scope_value | Data | — |
| 5 | total_rules_evaluated | Int | tổng finding sau filter False Positive (gồm cả pending) — KHÔNG phải mẫu số rate |
| 6 | compliant_count | Int | adjudicated-compliant = Resolved + Waived + Closed (BR-16-11) — KHÔNG còn = total − nc |
| 7 | non_compliant_count | Int | Confirmed NC (immutable sau publish — VR-09) |
| 8 | score_pct | Float | `compliant/(compliant+non_compliant)*100`; adjudicated=0 → 100.0 (immutable sau publish — VR-09) |
| 8a | pending_count | Int *(Cần khảo sát: thêm field DocType hay chỉ runtime)* | Open + Under Review — báo riêng, KHÔNG vào mẫu số. **BA decision (2026-06-02): trả runtime-only trong return dict; chưa thêm field DocType để tránh migration/fixture change. BE thêm column DocType khi cần persist cho restate audit.** |
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

## II.6. IMM Management Review (LIVE)

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
| `get_finding(name)` | `→ dict` | enrich asset_name, responsible_dept_name, rule_name, **`allowed_transitions[]`** + **`can_create_capa`** (server-driven CTA — §III.B.1) |
| `start_review(name, reviewer_note="")` | `→ dict` | **(round 14 — CR-WF-16-FIND)** Open → Under Review; guard `status != Open → BAD_STATE`; lockstep `workflow_state='Under Review'` (§III.B.2); audit trail. Surface cạnh workflow `Open→Under Review` vốn 0 service-driver (phantom) — xem ADR-IMM-16-06 |
| `confirm_finding(name, reviewer_note)` | `→ dict` | → Confirmed NC + audit trail; **lockstep `workflow_state='Confirmed NC'` (§III.B.2)** |
| `mark_false_positive(name, reason)` | `→ dict` | reason required; **lockstep `workflow_state='False Positive'` (§III.B.2)** |
| `waive_finding(name, waiver_reason, waiver_evidence, waiver_expiry)` | `→ dict` | VR-04: reason ≥ 50 chars, evidence, expiry > today; **lockstep `workflow_state='Waived'` (§III.B.2)** |
| `link_finding_to_capa(name, capa_ref)` | `→ dict` | set finding.capa_ref (không đổi status ⇒ không đụng workflow_state) |
| `close_finding(finding_name, capa_ref, resolution_note)` | `→ dict` | → Resolved (Confirmed NC → Resolved, cần `capa_ref`; KHÔNG có CTA trên FindingDetail — dùng cascade khi CAPA Closed); **lockstep `workflow_state='Resolved'` (§III.B.2)** |

### III.B.1. Server-driven CTA — `_FINDING_VALID_TRANSITIONS` + `can_create_capa` (GATE-8 / LL-FE-51)

> **Bối cảnh:** FindingDetailView.vue trước đây gate 5 CTA bằng so sánh `finding.status ===` client-side (dead-gate) → desync khỏi SoT `FindingStatus`. Chuyển sang **hint hiển thị do server phát**, đối xứng `_REPAIR_VALID_TRANSITIONS` (imm09.py:90) / IncidentDetail (imm12) / PmWorkOrderDetail (imm08). Xem **ADR-IMM-16-01** (`02_Analysis_Design.md`). Quyết định map do [BA] chốt — grounded state-machine `imm_16_finding_workflow.json` + service guard thực tế, KHÔNG theo phác thảo lỏng của đề mục.

**Map TẬP TRUNG (keyed bằng `FindingStatus.*` constant, KHÔNG literal) — codomain ⊆ `FindingStatus` enum:**

```python
# services/imm16.py — cạnh class FindingStatus
_FINDING_VALID_TRANSITIONS: dict[str, list[str]] = {
    # round 14 (CR-WF-16-FIND): +UNDER_REVIEW vào Open → surface CTA start_review
    # (Open→Under Review) — cạnh workflow vốn 0 service-driver (phantom). ADR-IMM-16-06.
    FindingStatus.OPEN:           [FindingStatus.UNDER_REVIEW, FindingStatus.CONFIRMED_NC, FindingStatus.FALSE_POSITIVE, FindingStatus.WAIVED],
    FindingStatus.UNDER_REVIEW:   [FindingStatus.CONFIRMED_NC, FindingStatus.FALSE_POSITIVE, FindingStatus.WAIVED],
    FindingStatus.CONFIRMED_NC:   [FindingStatus.WAIVED],
    FindingStatus.FALSE_POSITIVE: [],
    FindingStatus.RESOLVED:       [],
    FindingStatus.WAIVED:         [],
    FindingStatus.CLOSED:         [],
}
```

| `status` | `allowed_transitions` | CTA tương ứng trên FindingDetail |
|---|---|---|
| Open | `[Under Review, Confirmed NC, False Positive, Waived]` | **Bắt đầu xem xét** (round 14) · Xác nhận NC · Đánh dấu sai · Miễn áp dụng |
| Under Review | `[Confirmed NC, False Positive, Waived]` | Xác nhận NC · Đánh dấu sai · Miễn áp dụng (KHÔNG có "Bắt đầu xem xét" — đã trong review) |
| Confirmed NC | `[Waived]` | Miễn áp dụng (Xác nhận/Đánh dấu-sai ẩn — đã phân định NC); CAPA gate bằng `can_create_capa` |
| False Positive / Resolved / Waived / Closed | `[]` | terminal — 0 CTA đổi trạng thái |

**Vì sao KHÁC phác thảo đề mục** (Self-Correction, chi tiết ADR-IMM-16-01):
- Đề mục ghi `Confirmed NC → 'Waived','Closed'`. **Đúng SoT = `Confirmed NC → ['Waived']`.** State `Closed` KHÔNG có service-action nào phát ra từ Confirmed NC: `close_finding` đặt `status='Resolved'` (không phải Closed), còn `Resolved → Closed` là transition workflow-engine (dual-track, không endpoint status-CTA). Advertise `'Closed'` = hint dối → FE hiện nút gọi endpoint không tồn tại.
- `Resolved` KHÔNG có trong codomain Confirmed NC vì nó tới qua **auto-cascade** (`capa_record_on_update`: CAPA Closed → Finding Resolved, imm16.py:716) — KHÔNG phải CTA của cán bộ trên màn này. Lối đi CAPA biểu diễn bằng cờ riêng `can_create_capa` (dưới), KHÔNG nhồi vào `allowed_transitions`.
- **(round 14 — CR-WF-16-FIND) `Under Review` ĐƯỢC THÊM vào codomain Open** để surface cạnh workflow `Open→Under Review` ("Bắt đầu xem xét") vốn 0 service-driver (phantom). CTA `start_review` (§III.B.2) đóng phantom bằng cách cho Under Review 1 driver THẬT — đối xứng vòng 12 IMM-12 `reopen_incident` (surface cạnh orphan thành CTA). Under Review KHÔNG bị gỡ khỏi workflow (Branch A bị LOẠI: gỡ = HARD-STOP migrate + phá KPI `pending` sống @test:957 + phá nút desk). Chi tiết ADR-IMM-16-06.

**`get_finding(name)` enrich THÊM 2 field (derive SERVER-SIDE):**

```python
data["allowed_transitions"] = _FINDING_VALID_TRANSITIONS.get(data.get("status"), [])
data["can_create_capa"] = bool(
    data.get("status") == FindingStatus.CONFIRMED_NC and not data.get("capa_ref")
)
```

- `can_create_capa` = cờ eligibility DUY NHẤT cho CẢ HAI CTA **Tạo CAPA** và **Liên kết CAPA** (cùng điều kiện: Confirmed NC ∧ chưa có `capa_ref`). FE KHÔNG hardcode `'Confirmed NC'`.
- Fallback: worker cũ/field thiếu → FE đọc `allowed_transitions ?? []` và `can_create_capa ?? false` → CTA ẩn, KHÔNG vỡ.

**Defense-in-depth — guard BE (hint ≠ guard; `_require_qa_or_admin` = `compliance.write` vẫn chặn cứng):**

| Action | Set hợp lệ | Guard hiện tại | Yêu cầu sau round |
|---|---|---|---|
| `start_review` *(round 14)* | `START_REVIEWABLE = (Open,)` | *(fn mới)* | **THÊM** `status != Open → BAD_STATE` (chỉ bắt đầu review từ Open; Under Review đã review). Thêm set `FindingStatus.START_REVIEWABLE = (OPEN,)` |
| `confirm_finding` | `REVIEWABLE = (Open, Under Review)` | `status not in ACTIVE` (gồm Confirmed NC — over-permissive, cho self-confirm) | **SIẾT** về `REVIEWABLE` → raise `BAD_STATE` khi confirm 1 Confirmed NC (đóng desync ở tầng guard, khớp map) |
| `mark_false_positive` | `REVIEWABLE = (Open, Under Review)` | **KHÔNG có guard status** (gap) | **THÊM** `status not in REVIEWABLE → BAD_STATE` |
| `waive_finding` | `WAIVABLE = (Open, Under Review, Confirmed NC)` | **KHÔNG có guard status** (gap) | **THÊM** `status not in WAIVABLE → BAD_STATE` (giữ nguyên VR-04 + cap `compliance.approve`) |
| `close_finding` (→Resolved) | `(Confirmed NC)` khuyến nghị | `status not in ACTIVE` | GIỮ NGUYÊN (ngoài scope round — không có CTA trên FindingDetail) |
| `create_capa_from_finding` · `link_finding_to_capa` | `Confirmed NC ∧ ¬capa_ref` | KHÔNG có guard | *(Khuyến nghị SHOULD)* thêm `status != Confirmed NC or capa_ref → BAD_STATE` để cờ `can_create_capa` truthful |

> Bổ sung 3 set vào `class FindingStatus`: `START_REVIEWABLE = (OPEN,)` *(round 14)*, `REVIEWABLE = (OPEN, UNDER_REVIEW)` và `WAIVABLE = (OPEN, UNDER_REVIEW, CONFIRMED_NC)`. **Invariant an toàn:** với mọi `status`, `allowed_transitions[status] ⊆ {đích mà guard action cho phép}` — map KHÔNG BAO GIỜ advertise transition guard sẽ từ chối (map ⊆ guard-permitted). Đích `Under Review` ∈ map[Open] khớp guard `start_review` (Open → BAD_STATE nếu khác). Test-anchor: `TestFindingAllowedTransitions` (map↔state-machine edge-by-edge + codomain ⊆ enum + terminal → `[]`) — đối xứng `test_imm09.TestRepairAllowedTransitions`.
>
> ⚠️ Siết `confirm_finding` (ACTIVE→REVIEWABLE) đổi hành vi: confirm 1 Confirmed NC nay raise `BAD_STATE`. BE phải rà caller nội bộ (không có caller nào confirm lại Confirmed NC) + cập nhật test cũ (nếu có) assert hành vi lỏng.

### III.B.2. Dual-track lockstep `workflow_state ⇄ status` + INVARIANT (round 14 — CR-WF-16-FIND)

> **Bối cảnh (Self-Correction thiết kế gốc):** Workflow `imm_16_finding_workflow.json` **is_active=1**, bound qua `workflow_state_field="workflow_state"`. Các service-action Finding (`confirm_finding`@imm16:1353, `mark_false_positive`@1381, `waive_finding`@1410, `close_finding`@246 + cascade `capa_record_on_update`@716) đặt `doc.status` NHƯNG KHÔNG chạm `doc.workflow_state` → workflow_state **đọng `'Open'` vĩnh viễn** trong khi status marches qua vòng đời. Đây KHÔNG phải dual-track có chủ đích — là **DESYNC bug** (ADR-IMM-16-01 §V.1 note cũ mô tả sai là "track song song decorative"; SUPERSEDE bởi ADR-IMM-16-05).

**Cơ chế fix (lockstep) — SAU mỗi transition, sync `workflow_state = status`:**

```python
# services/imm16.py — SAU ComplianceFindingRepo.save(doc) trong mỗi transition fn.
# Mirror IMM-12 (imm12.py:797/938/1568 — dual-track lockstep đã proven) + CAPA/MR
# "đặt CẢ HAI" (ADR-IMM-16-03/04). frappe.db.set_value BYPASS validate_workflow.
frappe.db.set_value(ComplianceFindingRepo.DOCTYPE, name,
                    {"workflow_state": <new_status>}, update_modified=False)
# Cascade CAPA→Resolved (imm16:716): gộp 2 field 1 call —
#   frappe.db.set_value("IMM Compliance Finding", source_ref,
#       {"status": RESOLVED, "workflow_state": RESOLVED}, update_modified=False)
```

- **Vì sao `frappe.db.set_value` (KHÔNG `doc.save()` set cả 2):** Frappe v15 `model/workflow.py::validate_workflow` **raise `WorkflowPermissionError`** khi `doc.save()` đổi `workflow_state` sang state KHÔNG kề (không có transition edge từ state cũ). `confirm_finding` nhảy `Open→Confirmed NC` (bỏ qua `Under Review`) — workflow KHÔNG có cạnh `Open→Confirmed NC` ⇒ `doc.save()` sẽ throw. `db.set_value` ghi SQL trực tiếp, KHÔNG chạy validate cycle ⇒ an toàn cho multi-hop. (Lý do code cũ KHÔNG throw: workflow_state đọng Open→Open ⇒ `validate_workflow` return sớm `current==next`.)
- **Mirror trivial `workflow_state = status`:** 7 giá trị `FindingStatus` == 7 tên state workflow EXACT (Open / Under Review / Confirmed NC / False Positive / Resolved / Waived / Closed) ⇒ 1-1.
- **Boundaries — Always:** mọi transition-fn Finding (5: start_review/confirm/mark_false/waive/close) + cascade CAPA đặt CẢ 2 track lockstep. **Never:** đổi `workflow_state` Finding qua `doc.save()` (trip validate_workflow); sửa `imm_16_finding_workflow.json`/fixtures (HARD-STOP reload/migrate — root cause #1 admin-override GREEN 22/22 KHÔNG được phá); nhồi transition-edge mới vào workflow JSON.
- **Scope hẹp — CHỈ field `workflow_state`:** lockstep đồng bộ đúng field `workflow_state` ⇄ `status`. KHÔNG đụng `docstatus` (Frappe ledger submit/cancel) — service Finding vốn KHÔNG submit doc (docstatus giữ 0); mismatch `doc_status` cột workflow-JSON (vd Waived doc_status=1) vs docstatus thực = tình trạng CŨ, NGOÀI scope CR-WF-16-FIND. BE KHÔNG submit doc để "khớp" doc_status.

**INVARIANT guard (RED-before / GREEN-after) — codomain map ⇄ next_state graph workflow:**

```python
# Test đọc _FINDING_VALID_TRANSITIONS + parse imm_16_finding_workflow.json.
codomain      = {t for tgts in _FINDING_VALID_TRANSITIONS.values() for t in tgts}
wf_next_state = {tr["next_state"] for tr in workflow_json["transitions"]}
EXCEPTION_EDGES = {FindingStatus.RESOLVED, FindingStatus.CLOSED}  # 2 cạnh có tài liệu
# INV-16-A: 0 CTA advertise đích KHÔNG reachable trong workflow.
assert codomain - wf_next_state == set()
# INV-16-B: state workflow KHÔNG do map-CTA sinh ⊆ EXCEPTION_EDGES có tài liệu.
assert wf_next_state - codomain <= EXCEPTION_EDGES
# INV-16-C: mọi status service SINH ĐƯỢC reachable trong workflow.
assert {CONFIRMED_NC, FALSE_POSITIVE, WAIVED, RESOLVED, UNDER_REVIEW} <= wf_next_state
```

- **EXCEPTION_EDGES = {Resolved, Closed}** (đúng 2 cạnh acceptance nêu): `Confirmed NC→Resolved` = CAPA-auto (`capa_record_on_update`@720 + close_finding, KHÔNG service-CTA cán bộ); `*→Closed` = workflow-engine terminal (KHÔNG service-driver; FE SPA 0 nút Close). Cả 2 KHÔNG trong codomain map ⇒ hợp lệ ở INV-16-B.
- **RED-before:** trước round 14, `Under Review ∈ (wf_next_state − codomain)` NHƯNG ∉ EXCEPTION_EDGES ⇒ INV-16-B FAIL (phantom chưa phân định). **GREEN-after:** thêm `Under Review` vào codomain (map[Open]) ⇒ `wf_next_state − codomain == {Resolved, Closed} = EXCEPTION_EDGES` ⇒ PASS.

## III.C. Internal Audit

| Function | Signature | Ghi chú |
|---|---|---|
| `list_internal_audits(filters, *, page, page_size)` | `→ dict` | enrich lead_auditor_name |
| `create_internal_audit(data)` | `→ dict` | alias: `create_audit` |
| `get_audit(name)` | `→ dict` | enrich lead_auditor_name **+ `allowed_transitions[]` + `can_operate` + `can_close`** (server-driven CTA — §III.C.1) |
| `start_audit(name)` | `→ dict` | Planned → In Progress; **+1 audit-event `audit_started`** |
| `submit_audit_findings(audit_name, findings)` | `→ dict` | **[legacy, KHÔNG wired — DEPRECATED, dùng `complete_audit_checklist`]** batch create findings + → Reporting (event `audit_findings_submitted`). **CR-WF-16-AUDIT: guard SIẾT về linear — chỉ từ `In Progress`** (bỏ nhánh Planned: Planned→Reporting là skip-start guard-permissive) |
| `complete_audit_checklist(audit_name, items)` | `→ dict` | guard **chỉ `In Progress`** (bỏ nhánh Planned); **CR-27b: map `finding_status → child.result` (bảng SSoT §III.C.1b) để verdict round-trip — LOẠI 2 no-op `hasattr(child,"finding_status")`/`"clause_ref"`**; **CR-27d: auto-sinh `IMM Compliance Finding` THẬT cho mỗi Major/Minor NC — `findings_created` = số doc persist THỰC (§III.C.1c); rule resolve qua get-or-create canonical `AUDIT-INTERNAL-NC` (fail-loud, KHÔNG nuốt lỗi)**; **set `status=Reporting`** (khôi phục state chết); **+1 audit-event `audit_checklist_completed`** |
| `close_audit(name, audit_report)` | `→ dict` | guard **`status==Reporting`** (VR-13, chặn jump-skip) → VR-08 (FIN-008) → Closed; **+1 audit-event `audit_closed`** |
| `close_internal_audit(audit_name)` | `→ dict` | **[legacy alias, KHÔNG wired — DEPRECATED, dùng `close_audit`]** event `internal_audit_closed`. **CR-WF-16-AUDIT: guard SIẾT về linear — chỉ đóng từ `Reporting`** (VR-13 parity `close_audit`; chặn close-từ-Planned/In Progress). *Lưu ý: legacy KHÔNG có VR-08 Major-NC gate — dùng `close_audit` để có gate đầy đủ.* |

### III.C.1. Server-driven CTA — `_AUDIT_VALID_TRANSITIONS` + capability flags (ADR-IMM-16-02)

SSoT map keyed bằng `AuditStatus.*` (action-key, KHÔNG phải tên status-đích như Finding):

```python
_AUDIT_VALID_TRANSITIONS = {
    AuditStatus.PLANNED:     ["start"],
    AuditStatus.IN_PROGRESS: ["complete_checklist"],
    AuditStatus.REPORTING:   ["close"],
    AuditStatus.CLOSED:      [],
}
# get_audit enrich (safe-default .get → KHÔNG KeyError với status rỗng/lạ):
data["allowed_transitions"] = _AUDIT_VALID_TRANSITIONS.get(data.get("status"), [])
data["can_operate"] = rbac.can(_CAP_COMPLIANCE_WRITE)    # "compliance.write"
data["can_close"]   = rbac.can(_CAP_COMPLIANCE_APPROVE)  # "compliance.submit"
```

### III.C.1b. Mapping SSoT `finding_status → result` (CR-27b — silent-verdict-loss)

DUY NHẤT 1 dict module-level ở `services/imm16.py`; mọi value ∈ options Select `result` của `imm_audit_checklist_item.json` (`{Conforming, Non-Conforming, Not Applicable}`):

```python
# services/imm16.py — SSoT: DTO finding_status (API/FE enum) → child.result (persisted Select)
_FINDING_STATUS_TO_RESULT = {
    "Compliant": "Conforming",
    "Minor NC":  "Non-Conforming",
    "Major NC":  "Non-Conforming",
    "N/A":       "Not Applicable",
}
# trong loop complete_audit_checklist:
#   result = _FINDING_STATUS_TO_RESULT.get(finding_status)
#   if result:            # unknown/thiếu → giữ nguyên child.result cũ (KHÔNG set giá trị lạ)
#       child.result = result
#   child.notes = payload.get("notes", "")   # field THẬT — persist
#   # ❌ BỎ: child.finding_status / child.clause_ref (no-op câm, field không tồn tại)
```

- **Vì sao map thay vì thêm field:** verdict đã có nơi persist chuẩn (`result`, round-trip qua `get_audit`); thêm field `finding_status` vào child = migration + trùng dữ liệu 2 nguồn (drift). DTO enum finding_status thuộc lớp API/FE, map 1-chiều tại service. Xem ADR-IMM-16-10.
- **unknown finding_status** (payload sai / rỗng) → `.get()` trả `None` → KHÔNG overwrite `result` → an toàn (không ghi rác vào Select).

### III.C.1c. Auto-sinh `IMM Compliance Finding` THẬT cho Major/Minor NC (CR-27d — hết no-op câm)

> **Bối cảnh (Self-Correction — nhánh cũ là no-op câm).** Nhánh `if finding_status in ("Major NC","Minor NC")` (services/imm16.py:1720–1743) trước đây **KHÔNG bao giờ tạo được Finding**: (1) `rule` resolve từ `getattr(child, "rule_ref", "")` — child KHÔNG có field `rule_ref` → luôn `""` → `IMM Compliance Finding.rule` **reqd=1** (Link) → `insert()` raise `MandatoryError`; (2) `except Exception: frappe.log_error(...)` **nuốt** MandatoryError → `findings_created` đọng 0 nhưng hàm vẫn return "thành công" (status Reporting, items_count>0) — **success-giả**; (3) `if hasattr(child, "linked_finding")` — field ảo → backlink no-op. Kết quả: Major/Minor NC KHÔNG để lại record Finding nào; báo cáo/compliance-rate/VR-08 (close-gate) rỗng dữ liệu. CR-27d bật THẬT nhánh này.

**Nguồn `rule` (mandatory) — get-or-create canonical fallback, IDEMPOTENT.** Checklist item KHÔNG mang rule; auto-Finding cần `rule` (reqd Link → `IMM Compliance Rule`). Giải: get-or-create **1** rule canonical cố định `rule_code = "AUDIT-INTERNAL-NC"`. Vì `IMM Compliance Rule.autoname = field:rule_code` (unique) ⇒ `name == rule_code` ⇒ get-or-create khóa trên `rule_code` **tự nhiên idempotent**: chạy `complete_audit_checklist` 2 lần ⇒ ĐÚNG 1 doc rule fallback (KHÔNG nhân bản).

```python
# services/imm16.py — resolver rule canonical cho auto-Finding audit-NC (CR-27d)
_AUDIT_NC_RULE_CODE = "AUDIT-INTERNAL-NC"

def _resolve_audit_nc_rule() -> str:
    """Get-or-create canonical Compliance Rule cho NC phát hiện qua audit nội bộ.
    Idempotent (name==rule_code, unique) — trả về ``rule_code`` (= name Link)."""
    if ComplianceRuleRepo.exists(_AUDIT_NC_RULE_CODE):
        return _AUDIT_NC_RULE_CODE
    ComplianceRuleRepo.create({
        "rule_code":            _AUDIT_NC_RULE_CODE,
        "rule_name":            "Điểm không phù hợp (NC) — Kiểm toán nội bộ",
        "source_module":        "IMM-16",          # ⚠️ cần thêm option (xem note enum)
        "category":             "Document",         # reuse enum sẵn có (catch-all)
        "severity":             "Medium",           # severity-mẫu cấp rule (finding severity set riêng/dòng)
        "evaluation_frequency": "Realtime",         # event-driven khi complete audit
        "regulatory_reference": "ISO 13485 §8.2.4",
        "is_active":            1,
    })
    return _AUDIT_NC_RULE_CODE
```

> ⚠️ **Enum Self-Correction (handoff [BE]):** `IMM Compliance Rule.source_module` Select hiện `\nIMM-04…\nIMM-15` — **THIẾU IMM-16** (và IMM-00..03, 17). Để canonical rule có `source_module="IMM-16"` (đúng model — IMM-16 là module-nguồn hợp lệ của compliance rule), [BE] **thêm `IMM-16` vào options** của field `source_module` (`imm_compliance_rule.json`) → backward-compatible (0 row cũ vỡ; 0 test pin option-list — đã grep) → cần `bench migrate` (được phép). *Alternative (ADR-IMM-16-11) nếu tránh migrate: dùng value enum sẵn có — LOẠI vì làm bẩn report module đó.* **Đây là schema/data-model → [BE] sửa JSON, KHÔNG phải BA.**

**Vòng lặp auto-Finding (mỗi Major/Minor NC = 1 Finding, KHÔNG dedup):**

```python
# services/imm16.py — trong loop complete_audit_checklist, sau khi map result:
if finding_status in ("Major NC", "Minor NC"):
    severity = "High" if finding_status == "Major NC" else "Medium"
    rule = _resolve_audit_nc_rule()               # fail-loud nếu rule create hỏng
    finding = ComplianceFindingRepo.create({
        "rule":                  rule,             # reqd — hết MandatoryError câm
        "source_record_doctype": InternalAuditRepo.DOCTYPE,   # "IMM Internal Audit"
        "source_record":         doc.name,         # Dynamic Link → audit
        "severity":              severity,         # High (Major) / Medium (Minor)
        "status":                FindingStatus.OPEN,  # reqd, "Open"
        "detected_date":         now_datetime(),   # reqd, Datetime
        "evaluation_date":       nowdate(),        # reqd, Date
        "notes":                 payload.get("notes", ""),
        "current_value":         clause_ref or "", # (tùy chọn) lưu điều-khoản để truy vết
    })
    findings_created += 1                          # CHỈ tăng SAU khi create trả doc THẬT
    # ❌ BỎ: if hasattr(child, "linked_finding"): ...  (field ảo — no-op câm)
    # ❌ BỎ: except Exception: log_error(...)          (nuốt lỗi → success-giả)
```

**Boundaries (Always / Never) — CR-27d:**
- **Always:** `findings_created` = số `IMM Compliance Finding` doc **persist THỰC** (chỉ `+= 1` sau khi `create()` trả doc có `.name`). Mỗi Finding có `rule` KHÔNG rỗng (đã resolve) + `detected_date` (Datetime) + `evaluation_date` (Date) hợp lệ.
- **Always:** 1 Finding **cho mỗi** dòng Major/Minor NC (2 NC ⇒ 2 Finding).
- **Never (dedup-trap):** **KHÔNG** gọi `ComplianceFindingRepo.find_existing(rule, source_record, evaluation_date)` cho audit-NC. Nhiều dòng NC cùng audit chia sẻ `(rule=AUDIT-INTERNAL-NC, source_record=audit, evaluation_date=today)` ⇒ `find_existing` sẽ gộp nhiều NC → 1 Finding → `findings_created` sai (2 NC ra 1). `create_finding` (§III.B) CÓ dedup vì mỗi (rule, WO/asset) là 1 vi phạm riêng; audit-NC thì mỗi DÒNG là 1 vi phạm riêng ⇒ KHÔNG dedup.
- **Never (swallow-trap):** **KHÔNG** bọc `try/except Exception` nuốt lỗi quanh `create`. Lỗi THẬT (rule create hỏng / DB) → **raise** (in-handler → HTTP-200 Error envelope, DONE-gate) → abort TRƯỚC `frappe.db.commit()` (all-or-nothing, KHÔNG partial/success-giả). Audit-trail logging vẫn giữ try/except RIÊNG (lỗi trail KHÔNG chặn nghiệp vụ — pattern hiện hữu).
- **Never:** dòng `Compliant` / `N/A` / finding_status lạ → KHÔNG sinh Finding (chỉ Major/Minor NC).

**Field mapping Finding (per NC row) — mọi reqd đã phủ:**

| Finding field | Value | reqd |
|---|---|---|
| `rule` | canonical `AUDIT-INTERNAL-NC` (resolve) | reqd=1 ✓ |
| `source_record_doctype` | `"IMM Internal Audit"` | — |
| `source_record` | `<audit_name>` (Dynamic Link) | — |
| `severity` | Major NC→`High`, Minor NC→`Medium` | reqd=1 ✓ |
| `status` | `FindingStatus.OPEN` (`"Open"`) | reqd=1 ✓ (có default `Open` nhưng set tường minh) |
| `detected_date` | `now_datetime()` (Datetime) | reqd=1 ✓ |
| `evaluation_date` | `nowdate()` (Date) | reqd=1 ✓ |
| `notes` | payload NC `notes` | — |
| `current_value` | `clause_ref` (tùy chọn, truy vết điều-khoản) | — |

> **Truy vấn kiểm chứng persist (acceptance):** sau `complete_audit_checklist`, query
> `frappe.get_all("IMM Compliance Finding", filters={"source_record_doctype":"IMM Internal Audit", "source_record":<audit>}, fields=["severity","rule","detected_date","evaluation_date"])`
> ⇒ ĐÚNG N row (N = số NC) với `severity` = High (Major) / Medium (Minor), `rule` KHÔNG rỗng. Chứng minh persist THẬT — KHÔNG phải `len(payload)`.

- **Guard (defense-in-depth, HTTP-200 Error envelope `BAD_STATE` khi sai state)** — `allowed_transitions` chỉ là hint hiển thị, KHÔNG thay guard:
  - `start_audit`: chỉ từ `Planned` (giữ nguyên).
  - `complete_audit_checklist`: chỉ từ `In Progress` (siết — bỏ `Planned`); cuối thân set `status = Reporting`.
  - `close_audit`: chỉ từ `Reporting` (VR-13) → rồi VR-08 (`FIN-008`) → `Closed`.
- **Audit-trail** — mỗi service-action gọi `from assetcore.utils.lifecycle import log_audit_event` rồi ghi ĐÚNG 1 record trong `try/except` (lỗi audit-trail KHÔNG chặn nghiệp vụ — `frappe.log_error`):

  | Service-action | `event_type` | `from_status → to_status` |
  |---|---|---|
  | `start_audit` | `audit_started` | Planned → In Progress |
  | `complete_audit_checklist` | `audit_checklist_completed` | In Progress → Reporting |
  | `close_audit` | `audit_closed` | Reporting → Closed |

  Mọi record: `asset=''`, `ref_doctype='IMM Internal Audit'`, `ref_name=<audit>`, `actor=frappe.session.user`.
- **Invariant test-anchor** (`test_imm16`): `_AUDIT_VALID_TRANSITIONS.get(<mỗi AuditStatus>, [])` khớp bảng §IV.5; status rỗng/lạ → `[]` KHÔNG raise; đếm IMM Audit Trail tăng đúng 1 mỗi thao tác.
- **Fallback forward-compat:** worker cũ chưa enrich → 3 field vắng → FE đọc `?? []` / `?? false` → CTA ẩn, KHÔNG vỡ.

> **Dual-track status/workflow_state (ADR-IMM-16-02).** Canonical service-action đặt `status` trực tiếp; CTA InternalAuditDetail phát từ `status` qua `_AUDIT_VALID_TRANSITIONS`. `workflow_state` (workflow-engine `IMM-16 Internal Audit Workflow`, transition "Bắt đầu Audit / Chuyển sang Báo cáo / Đóng Audit") là track song song — KHÔNG phải nguồn CTA. Legacy `submit_audit_findings`/`close_internal_audit` **giữ trong whitelist (backward-compat, KHÔNG xóa) nhưng guard SIẾT về linear-machine** (CR-WF-16-AUDIT / §III.C.2 / ADR-IMM-16-09) — KHÔNG còn cho skip-start / close-từ-Planned. FE vẫn chỉ dùng canonical trio.

### III.C.2. Reconcile-guard `_AUDIT_VALID_TRANSITIONS` ⇄ `imm_16_internal_audit.json` qua resolver (round 22 — CR-WF-16-AUDIT)

> **ĐÓNG NỐT quartet reconcile IMM-16** (Finding R14 / CAPA R19 / MR R20 / **Internal Audit R22**). Khoá 0 hidden-CTA-câm + phát hiện guard-permissive trên state-machine Audit 4-state tuyến tính `Planned → In Progress → Reporting → Closed`. §III.C.2 / ADR-IMM-16-09. Đây chính là "backlog riêng" mà round MR (ADR-IMM-16-08, footnote ¹) đã defer — nay đóng.

**Khác-biệt cốt-lõi vs 3 workflow kia:** `_AUDIT_VALID_TRANSITIONS` codomain = **ACTION-KEY** (`start`/`complete_checklist`/`close`), KHÔNG phải status-đích như Finding/CAPA/MR (codomain = state). ⇒ đối soát 2-chiều với `next_state` graph workflow đòi 1 **resolver** dịch action-key → AuditStatus:

```python
# services/imm16.py — cạnh _AUDIT_VALID_TRANSITIONS. SSoT DUY NHẤT (ADR-IMM-16-09):
# 3 canonical handler whitelisted đặt CÙNG status-đích này (start_audit→In Progress,
# complete_audit_checklist→Reporting, close_audit→Closed — pinned bởi INVARIANT +
# lifecycle test AA-16-7..11).
_AUDIT_ACTION_TO_NEXT_STATE = {
    "start":              AuditStatus.IN_PROGRESS,
    "complete_checklist": AuditStatus.REPORTING,
    "close":              AuditStatus.CLOSED,
}
```

**INVARIANT guard (`TestAuditWorkflowInvariant`, test_imm16 — parse trực tiếp `imm_16_internal_audit.json`):**

| # | Kiểm | Kỳ vọng |
|---|---|---|
| INV-AUD-1 | `set(_AUDIT_VALID_TRANSITIONS.keys()) == states[]` workflow | == `{Planned, In Progress, Reporting, Closed}` (4-state; map keyed bằng status) |
| INV-AUD-2 | `set(resolver.keys())` | == `{start, complete_checklist, close}` = 3 handler whitelisted |
| INV-AUD-3 | `codomain(_AUDIT_VALID_TRANSITIONS) − keys(resolver)` | == ∅ (no orphan action — mọi action advertise dịch được → state) |
| INV-AUD-4 | `values(resolver) ⊆ AuditStatus enum` | == True (chống typo status-đích) |
| **INV-AUD-5 (RED→GREEN)** | ∀ state: `{resolver[a] for a in map[state]} == {next_state cạnh workflow từ state}` | Aligned: `Planned→{In Progress}`, `In Progress→{Reporting}`, `Reporting→{Closed}`, `Closed→∅`. **RED-before (perturbation THẬT):** đổi 1 entry resolver (vd `start→Reporting`) HOẶC thêm `'close'` vào `map[In Progress]` ⇒ FAIL message `'DRIFT <state>: map ≠ workflow'`; revert → GREEN |

- **Guard source-state canonical (KHÔNG regress):** 3 handler whitelisted chỉ nhận đúng source theo workflow — `start_audit ← Planned`, `complete_audit_checklist ← In Progress` (bỏ Planned), `close_audit ← Reporting` (VR-13). FE KHÔNG hiện nút mà BE sẽ raise `BAD_STATE`.
- **Legacy siết (guard-detect AA-16-13/14):** `submit_audit_findings` (was `∈ {In Progress, Planned}` → now `= In Progress`) + `close_internal_audit` (was `≠ Closed` → now `= Reporting`) — đóng lỗ guard-permissive (skip-start / close-từ-Planned né VR-13/VR-08). Whitelist GIỮ (0 API-count drift); chỉ guard state siết. Xem ADR-IMM-16-09.
- **0 workflow-JSON / fixtures change ⇒ admin-override GREEN + 0 reload/migrate.** Map ⇄ workflow đã in-sync (resolver bắc cầu khớp 1-1). Nếu BE thấy drift THẬT ⇒ fix map/resolver = KHÔNG tự sửa workflow JSON (HARD-STOP USER nếu buộc đổi JSON).

### ADR-IMM-16-10: DTO `finding_status` → persisted `result` mapping (KHÔNG thêm field child)

- **Status**: Accepted
- **Date**: 2026-07-14
- **Context**: `complete_audit_checklist` nhận payload item `{idx, finding_status, notes, clause_ref}` (DTO enum FE `Compliant/Minor NC/Major NC/N/A` — `frontend/src/api/imm16.ts:378`). Service cũ gán `child.finding_status`/`child.clause_ref` sau `hasattr(child, …)` — nhưng child `IMM Audit Checklist Item` KHÔNG có 2 field đó (chỉ `result` Select `{Conforming, Non-Conforming, Not Applicable}`). `hasattr` trả `False` (field không khai báo trong docfields ⇒ KHÔNG là instance attribute; Frappe `BaseDocument` KHÔNG override `__getattr__` nên lookup mặc định raise `AttributeError` — kiểm chứng live: `hasattr(new_doc, "finding_status")==False`, `"clause_ref"==False`, `"notes"==True`) ⇒ assign **no-op câm** ⇒ verdict KHÔNG persist ⇒ re-fetch `get_audit` trả `result` LUÔN rỗng (silent-verdict-loss, CR-27b).
- **Decision**: giữ nguyên schema child; thêm **1 dict SSoT `_FINDING_STATUS_TO_RESULT`** (§III.C.1b) map DTO enum → `result`, gán `child.result` (field round-trip THẬT). LOẠI 2 assign no-op `finding_status`/`clause_ref`. unknown/thiếu → giữ `result` cũ.
- **Alternatives**:
  1. *Thêm field `finding_status` (Select) + `clause_ref` (Data) vào child* — LOẠI: migration + 2 nguồn verdict (`finding_status` vs `result`) → drift; `result` đã là SSoT có round-trip + đã có FE/report tiêu thụ.
  2. *Đổi FE gửi thẳng `result` value (Conforming/…)* — LOẠI: DTO enum finding_status mang thêm severity (Major/Minor) để auto-Finding; ép FE về `result` mất phân biệt Major↔Minor (đều `Non-Conforming`).
- **Consequences**: 0 migration (field `result` đã tồn tại) → 0 `bench migrate`; verdict round-trip đúng; DTO enum vẫn giàu (Major/Minor) cho nhánh auto-Finding. Đánh đổi: map là 1-chiều — nếu cần lưu `clause_ref` thì phải thêm field (CR riêng, hiện discard). Backlink `linked_finding`/`finding_ref` vẫn no-op (nay LOẠI hẳn ở CR-27d — xem ADR-IMM-16-11 + §III.C.1c).

### ADR-IMM-16-11: Auto-Finding audit-NC — canonical rule get-or-create + fail-loud (CR-27d)

- **Status**: Accepted
- **Date**: 2026-07-19
- **Context**: Nhánh auto-sinh `IMM Compliance Finding` cho Major/Minor NC trong `complete_audit_checklist` là **no-op câm**: `rule` reqd=1 nhưng resolve từ field-ảo `child.rule_ref` → `""` → `insert()` raise `MandatoryError` → bị `except Exception` **nuốt** → `findings_created` đọng 0 nhưng return "thành công" (success-giả). Checklist item KHÔNG mang rule; auto-Finding vẫn cần 1 rule hợp lệ (reqd Link).
- **Decision**: **get-or-create 1 canonical `IMM Compliance Rule` `rule_code="AUDIT-INTERNAL-NC"`** làm nguồn `rule` cho mọi audit-NC Finding (`_resolve_audit_nc_rule()`, §III.C.1c). Idempotent nhờ `autoname=field:rule_code` (unique) ⇒ `name==rule_code`. **Bỏ blanket `except`** — lỗi create → raise (in-handler HTTP-200 Error envelope) abort trước commit. `findings_created` = số doc persist THỰC. 1 Finding/dòng NC, **KHÔNG dedup** (khác `create_finding`). Thêm `IMM-16` vào Select `source_module` (`imm_compliance_rule.json`) để canonical rule đúng module-nguồn.
- **Alternatives**:
  1. *Thêm field `rule` (Link) vào child + FE cho auditor chọn rule mỗi dòng* — LOẠI: UX nặng, auditor hiện trường không map từng NC về rule; checklist editor không thu rule; migration child.
  2. *`ignore_mandatory=True` khi insert Finding (bỏ qua reqd `rule`)* — LOẠI: Finding không rule = rác data, vỡ VR-08 close-gate + report compliance-rate + Link-integrity; chỉ giấu bug.
  3. *source_module dùng value enum sẵn có (né `bench migrate`)* — LOẠI: canonical rule là record hiển thị bền vững; gán sai module làm bẩn rule-list/report module đó. Thêm `IMM-16` (backward-compatible, 0 test pin) là đúng model. (Nếu branch buộc né migrate → interim reuse enum = tech-debt, target vẫn IMM-16.)
  4. *Giữ dedup `find_existing(rule, source_record, evaluation_date)`* — LOẠI: gộp nhiều NC cùng audit/ngày → 1 Finding → count sai (acceptance: 2 NC ⇒ 2 Finding).
- **Consequences**: auto-Finding hoạt động THẬT (Major→High, Minor→Medium); `findings_created` khớp số persist; VR-08 close-gate + compliance-rate có dữ liệu. **Cần `bench migrate`** (thêm option `IMM-16`, handoff [BE]). Canonical rule tự-seed lần đầu (không cần fixture). Đánh đổi: mọi audit-NC dùng chung 1 rule generic (không phân loại theo điều-khoản ISO); phân loại chi tiết = `[ROADMAP]` (map clause_ref→rule cụ thể). Backlink row→finding bỏ hẳn (forward-link finding→audit là SSoT).

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
| `get_capa(name)` | `→ dict` | enrich asset_name, responsible_name, finding_ref (BUG-16-08) **+ `allowed_transitions[]` + `can_advance`** (server-driven CTA — §III.D.1) |
| `update_capa_fields(name, data)` | `→ dict` | editable fields khi chưa Closed |
| `advance_capa_state(name, target_state, payload)` | `→ dict` | VR-05/06/07/12 enforcement |
| `perform_effectiveness_check(name, result, effectiveness_evidence)` | `→ dict` | Effective→Closed; Not Effective→Re-opened + reopen_count++ |
| `reopen_capa(name, reason)` | `→ dict` | force → Re-opened |

### III.D.1. Server-driven CTA — `_CAPA_TRANSITIONS` + `can_advance` (ADR-IMM-16-03 / GATE-8 / LL-FE-51)

> **Bối cảnh:** `CAPADetailView.vue` (lines 34-41) trước đây gate 6 CTA vòng đời (Bắt đầu điều tra / Lập kế hoạch hành động / Bắt đầu thực thi / Chuyển sang xác minh / Đóng / Mở lại) bằng client-map hardcode `TRANSITIONS: Record<string, Transition[]>` + `isVerification = wfState === 'Verification'` → dead-gate/desync khỏi SoT `_CAPA_TRANSITIONS`: QMS/QTV thấy/bấm action lệch quyền, và khi workflow đổi cạnh thì client-map câm lặng lệch. Chuyển sang **hint hiển thị do server phát**, đối xứng Finding (§III.B.1) / Audit (§III.C.1) / Repair (imm09) / PM (imm08) / Incident (imm12). Xem **ADR-IMM-16-03** (`02_Analysis_Design.md`).

SSoT map = **CÙNG** `_CAPA_TRANSITIONS` (dict giá trị `set`) mà `advance_capa_state` đọc để enforce — get_capa CHỈ ĐỌC lại, KHÔNG tạo nguồn thứ hai. Codomain = **tên workflow_state-đích** (KHÁC action-key của Audit), khớp tham số `target_state` của `advance_capa_state`:

```python
_CAPA_TRANSITIONS = {                       # GIỮ NGUYÊN — advance_capa_state enforce map này
    "Open":           {"Investigating"},
    "Investigating":  {"Action Plan"},
    "Action Plan":    {"Implementation"},
    "Implementation": {"Verification"},
    "Verification":   {"Closed", "Re-opened"},
    "Re-opened":      {"Investigating"},
}
# get_capa enrich (đặt cuối thân, trước return):
current = data.get("workflow_state") or "Open"     # khớp advance_capa_state: doc.workflow_state or "Open"
_can_advance = rbac.can(_CAP_COMPLIANCE_WRITE)      # "compliance.write" — CÙNG cap _require_qa_or_admin gate
data["can_advance"] = _can_advance
data["allowed_transitions"] = (
    sorted(_CAPA_TRANSITIONS.get(current, set())) if _can_advance else []
)
```

- **`allowed_transitions: string[]`** = `sorted(_CAPA_TRANSITIONS[current])` khi caller có `compliance.write`; **`[]` khi KHÔNG có** (gate quyền dồn vào chính hint — FE 1 nguồn). `sorted()` cho thứ tự **xác định** (set không thứ tự) → contract ổn định + test so-khớp được. Codomain ⊆ `CapaWorkflowState`. Terminal `Closed` (không key trong map) → `[]` (safe-default `.get`, KHÔNG KeyError).
- **`can_advance: bool`** = `rbac.can('compliance.write')` — derive SERVER-SIDE; cờ tường minh cho FE (mirror `can_operate` của Audit). `True` cả ở state terminal (phản ánh QUYỀN, không phải còn-thao-tác-hay-không); FE dùng `can_advance && allowed_transitions.includes('<đích>')`.
- **Guard (defense-in-depth) GIỮ NGUYÊN** — `advance_capa_state` vẫn `_require_qa_or_admin()` (FORBIDDEN nếu thiếu `compliance.write`) + `target not in _CAPA_TRANSITIONS[current] → INVALID_STATE` (chặn jump-skip). `allowed_transitions` CHỈ là hint hiển thị, KHÔNG thay guard: dù client bỏ qua hint, BE vẫn chặn cứng.
- **Verification → {Closed, Re-opened} đi qua `perform_effectiveness_check`**, KHÔNG qua `advance_capa_state` trên màn FE (Effective→Closed / Not-Partially Effective→Re-opened + `imm_reopen_count++`). `allowed_transitions` tại Verification = `['Closed', 'Re-opened']` vẫn dẫn xuất từ CÙNG `_CAPA_TRANSITIONS['Verification']` (SoT thống nhất) — FE gate 2 nút hiệu quả bằng `allowed_transitions.includes('Closed')` / `.includes('Re-opened')` (thay `isVerification` hardcode), rồi gọi `perform_effectiveness_check`. `advance_capa_state(Verification→Closed/Re-opened)` cũng hợp lệ theo map (bất biến parity không vỡ), chỉ là FE chọn đường effectiveness để thu `result`.
- **Invariant test-anchor** (`test_imm16`): (a) ∀ state S có `compliance.write`: `set(get_capa(S).allowed_transitions) == _CAPA_TRANSITIONS.get(S, set())` — emit = guard-domain, KHÔNG lệch; (b) ∀ T ∈ `get_capa(S).allowed_transitions`: `advance_capa_state(S, T)` KHÔNG raise `INVALID_STATE` (có thể raise validation downstream VR-05/12… nhưng KHÔNG BAO GIỜ "Không thể chuyển từ S sang T") — hint ⊆ guard-permitted; (c) caller thiếu `compliance.write` → `allowed_transitions == []` ∧ `can_advance == False` ở MỌI state; (d) user full-quyền AssetCore (có `compliance.write`, gồm `AssetCore Super Admin`) → `allowed_transitions` KHÔNG rỗng + `can_advance == True` ở state hợp lệ, và `advance_capa_state` thực thi thành công (KHÔNG FORBIDDEN).
- **Fallback forward-compat:** worker cũ chưa enrich → 2 field vắng → FE đọc `?? []` / `?? false` → 0 CTA (ẩn, không disable), KHÔNG vỡ.

> **Dual-track status/workflow_state (ADR-IMM-16-03).** CTA `CAPADetailView` phát từ `workflow_state` qua `_CAPA_TRANSITIONS`; `status` (SoT lifecycle — cron `check_capa_overdue` flip `Overdue` mà KHÔNG đổi `workflow_state`) là track song song hiển thị header, KHÔNG phải nguồn CTA. `advance_capa_state` đặt CẢ HAI (`workflow_state` = stage, `status` = In Progress/Closed).

### III.D.2. INVARIANT reconcile-guard `_CAPA_TRANSITIONS` ⇄ `imm_16_capa_workflow.json` (round 19 — CR-WF-16-CAPA)

> **Bối cảnh:** `_CAPA_TRANSITIONS` (SSoT sinh `allowed_transitions` → 6 CTA vòng đời CAPADetailView, §III.D.1) và workflow-engine `imm_16_capa_workflow.json` (is_active=1, bound `workflow_state_field="workflow_state"`) là **hai artefact tách rời** mô tả CÙNG một state-machine. Nếu chúng lệch cạnh — ai đó sửa 1 bên quên bên kia — thì: (a) map có cạnh workflow KHÔNG có ⇒ CTA **dead/bypass** (nút hiện nhưng engine từ chối); (b) workflow có cạnh map KHÔNG surface ⇒ **CTA câm** (nút duyệt biến mất, người dùng kẹt state). Guard này khoá parity **2 chiều, EDGE-by-EDGE** để mọi drift map↔workflow FAIL ngay ở test — mirror `TestFindingWorkflowInvariant` (§III.B.2, round 14) và `TestIncidentAllowedTransitions` (IMM-12, round 12).

**Khác Finding §III.B.2 — đối soát chặt hơn.** Finding INV-16-A/B/C so **codomain** (chỉ tập `next_state`, bỏ qua `state` nguồn). CAPA đối soát **cặp `(state → next_state)` EDGE-by-EDGE** cả 2 chiều — bắt được cả drift "đúng đích, sai nguồn" (vd cạnh `Open→Verification` giả). Vì `_CAPA_TRANSITIONS` **đối xứng HOÀN TOÀN** workflow (7 cạnh khớp 1-1) ⇒ **`EXCEPTION_EDGES = ∅` cả 2 chiều** (KHÁC Finding `{Resolved, Closed}` do Finding có cạnh CAPA-auto + workflow-terminal 0 service-driver).

```python
# ── TEST-ONLY (test_imm16.py) — KHÔNG đụng services/imm16.py, KHÔNG đụng workflow JSON ──
# SSoT map (state → set[next_state]) VERBATIM từ services/imm16.py:1958 (get_capa
# + advance_capa_state cùng đọc). Loader parse workflow JSON, DEDUPE cạnh lặp-theo-vai
# (Compliance Manager / System Manager / AssetCore Super Admin → nhiều entry cùng cạnh).
map_edges = {(s, t) for s, tgts in _CAPA_TRANSITIONS.items() for t in tgts}   # 7 cạnh
wf_edges  = {(tr["state"], tr["next_state"]) for tr in wf_json["transitions"]}  # 21 entry → 7 cạnh deduped
_CAPA_EXCEPTION_EDGES: frozenset[tuple[str, str]] = frozenset()   # ∅ — đối xứng hoàn toàn

# INV-16-CAPA-1 (MAP ⊆ WF): mọi cạnh map là cạnh THẬT của workflow (0 CTA dead/bypass).
assert map_edges - wf_edges == set(_CAPA_EXCEPTION_EDGES)   # == ∅
# INV-16-CAPA-2 (WF ⊆ MAP): mọi cạnh workflow được map surface (0 CTA câm).
assert wf_edges - map_edges == set(_CAPA_EXCEPTION_EDGES)   # == ∅   ⇒ set-diff 2 chiều == ∅
```

- **7 cạnh khớp 1-1** (`map_edges == wf_edges`): `Open→Investigating` · `Investigating→Action Plan` · `Action Plan→Implementation` · `Implementation→Verification` · `Verification→Closed` · `Verification→Re-opened` · `Re-opened→Investigating`. Set-diff **cả 2 chiều == ∅**.
- **Codomain `(keys ∪ values) ⊆ 7 state CAPA hợp lệ`** `{Open, Investigating, Action Plan, Implementation, Verification, Re-opened, Closed}` (== `states[]` của workflow JSON) — chống typo/orphan (vd `"Actn Plan"` lọt vào map). Không state lạ ngoài 7.
- **Terminal `Closed` ∉ `keys(_CAPA_TRANSITIONS)`** (6 key: Open/Investigating/Action Plan/Implementation/Verification/Re-opened) ⇒ `get_capa` của CAPA đã Closed trả `allowed_transitions == []` (safe-default `.get("Closed", set())` → `[]`, KHÔNG KeyError). Live-proof: AC-16-5 (`test_get_capa_allowed_transitions_by_state`).
- **RED-before (chứng minh THẬT, không GREEN-suông):** strip 1 cạnh map — vd bỏ `Re-opened` khỏi `_CAPA_TRANSITIONS["Verification"]` (`{"Closed"}` thay `{"Closed", "Re-opened"}`) → `wf_edges − map_edges == {("Verification", "Re-opened")}` ≠ ∅ ⇒ **INV-16-CAPA-2 FAIL** với message `'workflow có cạnh Verification→Re-opened KHÔNG surface (CTA câm)'`. Restore → GREEN. (Đối xứng: strip nguồn sai vào map → INV-16-CAPA-1 FAIL.)
- **`EXCEPTION_EDGES = ∅`** = hằng test-level `frozenset()` (KHÔNG đưa vào `services/imm16.py` — round TEST-ONLY, 0 service change). Nếu tương lai workflow thêm cạnh **cố ý** map KHÔNG surface (vd auto-advance), phải bồi cạnh đó vào `_CAPA_EXCEPTION_EDGES` + ADR giải thích — KHÔNG để test tự-GREEN bằng cách nới assert.

**Boundaries (Always / Never) — reconcile-guard CR-WF-16-CAPA:**
- **Always**: đối soát `_CAPA_TRANSITIONS` ⇄ workflow JSON **2 chiều edge-by-edge**; loader parse JSON THẬT (`frappe.get_app_path`) + DEDUPE cạnh lặp-theo-vai; set-diff cả 2 chiều so với `_CAPA_EXCEPTION_EDGES` (không so với `∅` cứng → dễ mở rộng có kiểm soát); codomain ⊆ 7 state hợp lệ; message FAIL nêu RÕ cạnh nào drift + hệ quả (dead/câm).
- **Never**: KHÔNG sửa `services/imm16.py` (map đã in-sync — round TEST-ONLY); KHÔNG sửa `imm_16_capa_workflow.json`/fixtures (⇒ 0 reload/migrate + admin-override giữ GREEN); KHÔNG chỉ so codomain `next_state` (bỏ sót drift "sai nguồn" — phải EDGE); KHÔNG nới assert để test GREEN khi drift THẬT (drift = fix map/JSON hoặc bồi EXCEPTION_EDGE + ADR); KHÔNG so cứng `== set()` (dùng `_CAPA_EXCEPTION_EDGES` để 1 chỗ khai báo miễn trừ).

## III.E. Compliance Scorecard

`generate_scorecard()` **không ghi child rows** `score_by_module`/`score_by_department` vào DB — các field này là Table nhưng service chỉ tính runtime và không append rows.

### SoT compliance-rate (BR-16-11)

`compute_compliance_rate()` là **Single Source of Truth** cho compliance-rate, dùng chung bởi `generate_scorecard()` (scorecard immutable) VÀ `get_compliance_heatmap()` (matrix Module×Dept) — KHÔNG nhân bản công thức `(total - nc) / total` inline ở 2 nơi. CÙNG dataset → CÙNG 1 score (không divergence).

#### Period-anchor canonical (BR-16-12) — điều kiện tiên quyết của "CÙNG dataset"

"CÙNG dataset" CHỈ đúng nếu cả 2 hàm chọn CÙNG TẬP finding cho cùng module/kỳ. SoT công thức không đủ — phải thống nhất cả **field neo kỳ**. Canonical = **`evaluation_date`** (Date), KHÔNG dùng `detected_date` (Datetime):

| Field | Kiểu | Ngữ nghĩa | Dùng neo kỳ? |
|---|---|---|---|
| `evaluation_date` | Date (reqd) | Ngày assessment — khớp chu kỳ review tháng của Scorecard; thành phần khóa idempotency `(rule, source_record, evaluation_date)` = "finding thuộc kỳ nào" | ✅ CANONICAL |
| `detected_date` | Datetime (reqd) | Event-timestamp lúc phát hiện; có thể lệch kỳ do lag adjudication (phát hiện T2, đánh giá T3) | ❌ KHÔNG — gây divergence |

**SoT period-filter — chống tái phát drift.** Field neo kỳ VÀ logic tính biên kỳ đều phải dùng chung, KHÔNG duplicate inline (gốc bug: bounds copy ở 2 nơi → 1 nơi đổi field, nơi kia quên). Hai artefact module-level trong `services/imm16.py`:

- Hằng **`PERIOD_ANCHOR_FIELD = "evaluation_date"`** — field neo kỳ canonical (BR-16-12). Cả `generate_scorecard()` và `get_compliance_heatmap()` tham chiếu hằng này (KHÔNG literal `"evaluation_date"` rải rác).
- Helper **`_period_bounds(year, month) -> (start, end_inclusive)`** — SoT cho biên kỳ. Semantics half-open `[start, next_month_start)`: ngày đầu kỳ THUỘC, ngày đầu kỳ KẾ KHÔNG thuộc. Vì Frappe `between` inclusive CẢ 2 đầu → `end_inclusive` = **ngày cuối tháng** (`next_month_start − 1 ngày`), tránh off-by-one cho finding rơi đúng ngày 01 kỳ kế (BR-16-12 / TDD-4 boundary).

CẢ HAI hàm dùng chung hằng + helper:

```python
PERIOD_ANCHOR_FIELD = "evaluation_date"   # BR-16-12 canonical

def _period_bounds(year, month):          # SoT biên kỳ — half-open [start, next)
    start = f"{year}-{month:02d}-01"
    next_start = f"{year + 1}-01-01" if month == 12 else f"{year}-{month + 1:02d}-01"
    return start, add_days(next_start, -1)  # end_inclusive = ngày cuối tháng

# generate_scorecard() VÀ get_compliance_heatmap():
start, end = _period_bounds(year, month)
filters = {
    PERIOD_ANCHOR_FIELD: ("between", [start, end]),  # BR-16-12 canonical, KHÔNG detected_date
    "status": ("!=", FindingStatus.FALSE_POSITIVE),
}
```

> Divergence chứng minh: 1 Confirmed-NC có `detected_date='2027-02-25'` (kỳ T2) nhưng `evaluation_date='2027-03-05'` (kỳ T3). TRƯỚC fix: heatmap T2 đếm finding này (score giảm), scorecard T2 KHÔNG đếm (score cao hơn). SAU fix: finding chỉ thuộc T3 ở CẢ 2 view; T2 score==100 cả 2; T3 giống nhau cả 2.

```python
def compute_compliance_rate(findings: list) -> dict:
    """SoT BR-16-11. ``findings`` đã loại False Positive từ filter.
    Trả: {total_adjudicated, compliant, non_compliant, pending, score_pct}.

    - non_compliant = chỉ Confirmed NC
    - compliant     = ĐÃ phân định-tuân-thủ: Resolved | Waived | Closed
    - pending       = Open | Under Review (chưa phân định) → KHÔNG vào mẫu số
    - mẫu số (total_adjudicated) = compliant + non_compliant
    - score_pct = round(compliant / total_adjudicated * 100, 2)
    - total_adjudicated == 0 → score_pct = 100.0 (semantics 'không có NC xác nhận')
    """
```

| Trạng thái finding | Phân loại trong rate | Vào mẫu số? |
|---|---|---|
| Confirmed NC | `non_compliant` | ✅ |
| Resolved / Waived / Closed | `compliant` (adjudicated) | ✅ |
| Open / Under Review | `pending` | ❌ (báo riêng) |
| False Positive | (loại từ filter `status != False Positive`) | ❌ |

**Regression chứng minh bằng số** — dataset `1×Confirmed NC + 1×Open + 1×Resolved`:

| | total | nc | compliant | pending | adjudicated | score_pct |
|---|---|---|---|---|---|---|
| TRƯỚC fix `(total−nc)/total` | 3 | 1 | 2 (gồm Open ❌) | — | 3 | **66.67%** (Open bị tính tuân thủ) |
| SAU fix SoT | 3 | 1 | 1 (Resolved) | 1 (Open) | 2 | **50.0%** |

Assert: `score_pct == 50.0` và `!= 66.67`.

| Function | Signature | Ghi chú |
|---|---|---|
| `compute_compliance_rate(findings)` | `→ dict{total_adjudicated, compliant, non_compliant, pending, score_pct}` | **SoT BR-16-11** — gọi bởi `generate_scorecard` + `get_compliance_heatmap` |
| `generate_scorecard(module_ref, period)` | `→ dict` | tạo Scorecard record; gọi SoT; ghi `compliant_count`/`non_compliant_count`/`score_pct`; trả thêm `pending_count` runtime. `capa_open_count` ← **SoT `imm00._open_capa_filter()`** (status NOT IN Closed — KHÔNG inline `IN [Open, In Progress, Pending Verification]`) → khớp KPI dashboard `capa_open`/drill byte-for-byte. `capa_overdue_count` ← **SoT `imm00._overdue_capa_filter()`** → khớp KPI/drill |
| `list_scorecards(filters, *, page, page_size)` | `→ dict` | |
| `get_current_scorecard(scope)` | `→ dict` | delegate → get_scorecard_by_period(today) |
| `get_scorecard_by_period(year, month, scope)` | `→ dict` | |
| `publish_scorecard(name)` | `→ dict` | VR-09 immutable; VR-10 gate quý trước MR |
| `validate_scorecard_immutability(doc)` | controller hook | score_pct + non_compliant_count immutable sau publish (KHÔNG hồi quy) |

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
| `get_management_review(name)` | `→ dict` | enrich chair_name + scorecard (BUG-16-10) **+ `allowed_transitions[]` + `can_advance` + `can_close`** (server-driven CTA — §III.F.1) |
| `create_management_review(data)` | `→ dict` | unique per quarter |
| `update_management_review(name, data)` | `→ dict` | scalar fields + attendees + output_actions child |
| `advance_mr_state(name, target_state)` | `→ dict` | Draft→Held→Minutes Approved; không cho→Closed (dùng finalize) |
| `finalize_management_review(name, minutes_doc, output_actions)` | `→ dict` | Closed + attach minutes + VR: ≥1 output action |

### III.F.1. Server-driven CTA — `_MR_TRANSITIONS` + `can_advance` + `can_close` (ADR-IMM-16-04 / GATE-8 / LL-FE-51)

Workflow IMM-16 **thứ 4/4 — cái DUY NHẤT chưa server-driven** trước vòng này (Finding/Audit/CAPA đã chuyển ADR-16-01/02/03). SSoT map keyed bằng tên status (codomain = tên **status-đích**, KHÔNG action-key như Audit — khớp 1-1 tham số `target_state`):

```python
_MR_TRANSITIONS = {
    "Draft":            {"Held"},
    "Held":             {"Minutes Approved"},
    "Minutes Approved": {"Closed"},   # 'Closed' đi qua finalize_management_review
}
# get_management_review enrich (safe-default .get → KHÔNG KeyError với status rỗng/lạ):
data["allowed_transitions"] = sorted(_MR_TRANSITIONS.get(doc.status, []))
data["can_advance"] = rbac.can(_CAP_COMPLIANCE_APPROVE)  # "compliance.submit"
data["can_close"]   = rbac.can(_CAP_COMPLIANCE_APPROVE)  # "compliance.submit"
```

- **`allowed_transitions: string[]`** = `sorted(_MR_TRANSITIONS.get(doc.status, []))` — phát **vô điều kiện** (KHÔNG gate bằng cờ, mirror Finding/Audit — KHÁC CAPA gate `[]` khi thiếu quyền). `sorted()` cho thứ tự **xác định** (set không thứ tự) → contract ổn định + test so-khớp. `Draft→['Held']`, `Held→['Minutes Approved']`, `Minutes Approved→['Closed']`, `Closed`/rỗng/lạ → `[]`.
- **`can_advance: bool`** = `rbac.can('compliance.submit')` — cờ tường minh gate 2 nút chuyển-cạnh (Đánh dấu Đã họp / Phê duyệt Biên bản). Derive SERVER-SIDE.
- **`can_close: bool`** = `rbac.can('compliance.submit')` — cùng capability nhưng cờ **tách riêng** (đối xứng Audit `can_operate`/`can_close`) gate nút Đóng và xuất biên bản. FE dùng `allowed_transitions.includes('Closed') && can_close===true`.
- **Guard (defense-in-depth, HTTP-200 Error envelope khi sai) — `allowed_transitions` chỉ là hint hiển thị, KHÔNG thay guard:**
  - `advance_mr_state(name, target)`: `rbac.can('compliance.submit')` (FORBIDDEN nếu thiếu) + `target not in _MR_TRANSITIONS[current] → INVALID_STATE` (chặn jump-skip) + `target=='Closed' → VALIDATION` "Dùng finalize_management_review để đóng MR".
  - `finalize_management_review(name, minutes_doc, actions)`: `rbac.can('compliance.submit')` + `status!='Closed'` (BAD_STATE nếu đã Closed) + `minutes_doc` bắt buộc (VALIDATION) + ≥1 output action (VALIDATION, skill R-2).
- **INVARIANT (hint ⊆ guard):** MỌI target ∈ `allowed_transitions` do get_management_review phát PHẢI được guard chấp nhận ở status đó — `'Held'`/`'Minutes Approved'` qua `advance_mr_state`, `'Closed'` qua `finalize_management_review`. Target NGOÀI `_MR_TRANSITIONS[status]` → `advance_mr_state` reject `INVALID_STATE`. KHÔNG desync giữa hint hiển thị và guard cứng.
- **Dual-track status/workflow_state (ADR-IMM-16-04).** Canonical service-action đặt `status` + `workflow_state` cùng lúc (advance_mr_state: cả hai = target; finalize: cả hai = "Closed"). CTA màn ManagementReviewDetail phát từ `status` qua `_MR_TRANSITIONS`. Frappe workflow-engine `IMM-16 Management Review Workflow` (transition 'Đánh dấu Đã họp' / 'Phê duyệt Biên bản' / 'Đóng') là track song song validate khi `doc.save()` đổi `workflow_state` — allowed roles phải gồm `AssetCore Super Admin` (fixtures/workflow.json đã có; backfill bởi `backfill_workflow_admin` nếu site chưa sync).
- **RBAC (verify, KHÔNG cần patch code):** `_CAP_COMPLIANCE_APPROVE = "compliance.submit"` bind `('IMM CAPA Record','submit')`; `AssetCore Super Admin` đã có `submit=1` DocPerm → `rbac.can('compliance.submit')=True`. QTV duyệt/đóng được. Nếu LIVE test cho thấy grant thiếu → sửa DocPerm JSON / workflow.json (SoT), KHÔNG hardcode role-name.
- **Invariant test-anchor** (`test_imm16`, đối xứng `TestCapaAllowedTransitions`): (a) ∀ status S: `set(get_management_review(S).allowed_transitions) == set(_MR_TRANSITIONS.get(S, set()))` — emit = guard-domain; (b) ∀ T ∈ `allowed_transitions`: nếu T≠'Closed' thì `advance_mr_state(S,T)` KHÔNG raise `INVALID_STATE`, nếu T=='Closed' thì `finalize_management_review` KHÔNG raise `INVALID_STATE`; (c) status rỗng/lạ/Closed → `allowed_transitions == []` (safe-default `.get`, KHÔNG KeyError); (d) user CHỈ role `AssetCore Super Admin` → `can_advance == can_close == True`, và advance_mr_state Draft→Held→Minutes Approved + finalize_management_review Closed đều KHÔNG raise `FORBIDDEN`.
- **Fallback forward-compat:** worker cũ chưa enrich → 3 field vắng → FE đọc `?? []` / `?? false` → CTA ẩn, KHÔNG vỡ.

### III.F.2. INVARIANT reconcile-guard `_MR_TRANSITIONS` ⇄ `imm_16_mr_workflow.json` (round 20 — CR-WF-16-MR)

> **Bối cảnh:** `_MR_TRANSITIONS` (SSoT sinh `allowed_transitions` → 3 CTA vòng đời ManagementReviewDetail, §III.F.1) và workflow-engine `imm_16_mr_workflow.json` (is_active=1, bound `workflow_state_field="workflow_state"`) là **hai artefact tách rời** mô tả CÙNG state-machine MR 4-state (Draft → Held → Minutes Approved → Closed, tuyến tính KHÔNG nhánh/vòng). §III.F.1 (ADR-IMM-16-04) đã khoá parity **map ⇄ advance/finalize-guard** (emit = guard-domain, §III.F.1 (a)-(d)) NHƯNG **CHƯA** khoá parity **map ⇄ workflow-JSON**. Nếu ai sửa 1 bên quên bên kia: (a) map có cạnh workflow KHÔNG có ⇒ CTA **dead/bypass** (nút hiện, engine `doc.save()` từ chối `workflow_state`); (b) workflow có cạnh map KHÔNG surface ⇒ **CTA câm** (nút 'Đánh dấu Đã họp'/'Phê duyệt Biên bản'/'Đóng' biến mất, MR kẹt state — không họp/duyệt/đóng được). Guard này khoá parity **2 chiều, EDGE-by-EDGE** để mọi drift map↔workflow FAIL ngay ở test. **Đóng nốt quartet reconcile IMM-16** — cùng bộ với Finding (§III.B.2, round 14) và CAPA (§III.D.2, round 19); mirror `TestCapaWorkflowInvariant`/`TestFindingWorkflowInvariant`/`TestIncidentAllowedTransitions` (IMM-12, round 12).

**Đối soát EDGE-by-EDGE 2 chiều — đối xứng HOÀN TOÀN (giống CAPA, KHÁC Finding).** MR đối soát **cặp `(state → next_state)`** cả 2 chiều (bắt cả drift "đúng đích, sai nguồn"), KHÔNG chỉ codomain `next_state` như Finding INV-16-A/B. Vì `_MR_TRANSITIONS` **khớp 1-1 HOÀN TOÀN** workflow (3 cạnh mỗi bên) ⇒ **`_MR_EXCEPTION_EDGES = ∅` cả 2 chiều** (KHÁC Finding `{Resolved, Closed}` do Finding có cạnh CAPA-auto-cascade + workflow-terminal 0 service-driver; giống CAPA `∅` do đối xứng hoàn toàn).

```python
# ── TEST-ONLY (test_imm16.py) — KHÔNG đụng services/imm16.py, KHÔNG đụng workflow JSON ──
# SSoT map (state → set[next_state]) đọc VERBATIM từ svc._MR_TRANSITIONS (imm16.py:2391 —
# get_management_review §III.F.1 + advance_mr_state cùng đọc). Loader parse workflow JSON,
# DEDUPE cạnh lặp-theo-vai (Compliance Manager / System Manager / AssetCore Super Admin →
# 8 transition entry → 3 cạnh duy nhất).
_MR_VALID_STATES = {"Draft", "Held", "Minutes Approved", "Closed"}  # == states[] của JSON
_MR_EXCEPTION_EDGES: frozenset[tuple[str, str]] = frozenset()   # ∅ — đối xứng hoàn toàn

# map_edges = {(s, t) for s, tgts in svc._MR_TRANSITIONS.items() for t in tgts}
#           = {(Draft,Held), (Held,Minutes Approved), (Minutes Approved,Closed)}
# wf_edges  = _load_mr_workflow_edges() (deduped) = CÙNG 3 cạnh

# INV-16-MR-1 (MAP ⊆ WF): mọi cạnh map là cạnh THẬT của workflow (0 CTA dead/bypass).
assert map_edges - wf_edges == set(_MR_EXCEPTION_EDGES)   # == ∅
# INV-16-MR-2 (WF ⊆ MAP): mọi cạnh workflow được map surface (0 CTA câm).
assert wf_edges - map_edges == set(_MR_EXCEPTION_EDGES)   # == ∅   ⇒ set-diff 2 chiều == ∅
```

- **Codomain (keys ∪ values) ⊆ 4 state hợp lệ** `{Draft, Held, Minutes Approved, Closed}` — chống typo/orphan (INV-16-MR-3). keys = `{Draft, Held, Minutes Approved}`; values = `{Held, Minutes Approved, Closed}`; union = đúng 4 state, KHÔNG dư.
- **Terminal `Closed` ∉ `keys(_MR_TRANSITIONS)`** (3 key: Draft/Held/Minutes Approved) ⇒ `get_management_review` của MR đã Closed trả `allowed_transitions == []` (safe-default `_MR_TRANSITIONS.get(data.get("status") or "Draft", set())` @imm16:2245-2246 → `[]`, KHÔNG KeyError). Live-proof: AM-16-4 / AM-16-5 (`test_get_mr_emits_allowed_transitions_per_status`@1044). **Đối xứng bất-cân-xứng có chủ đích:** `Closed` KHÔNG là key (đúng — không đi tiếp), nhưng LÀ value của `Minutes Approved` (đến qua `finalize_management_review`, KHÔNG qua `advance_mr_state` — advance reject `'Closed'` VALIDATION).
- **RED-before (chứng minh THẬT, không GREEN-suông):** strip 1 cạnh khỏi map — vd bỏ `Held → {Minutes Approved}` khỏi `_MR_TRANSITIONS` (hoặc đổi `{"Minutes Approved"}` → `set()`) → `wf_edges − map_edges == {("Held", "Minutes Approved")}` ≠ ∅ ⇒ **INV-16-MR-2 FAIL** với message `'workflow có cạnh Held→Minutes Approved KHÔNG surface (CTA câm — nút duyệt MR mất)'`. Restore → GREEN. (Đối xứng: chèn cạnh-nguồn giả vào map → INV-16-MR-1 FAIL.)
- **`_MR_EXCEPTION_EDGES = ∅`** = hằng test-level `frozenset()` (KHÔNG đưa vào `services/imm16.py` — round TEST-ONLY, 0 service change; đối xứng `_CAPA_EXCEPTION_EDGES`). Nếu tương lai workflow thêm cạnh **cố ý** map KHÔNG surface (vd auto-advance), phải bồi cạnh đó vào `_MR_EXCEPTION_EDGES` + ADR giải thích — KHÔNG nới assert để test tự-GREEN.

**Boundaries (Always / Never) — reconcile-guard CR-WF-16-MR:**
- **Always**: đối soát `_MR_TRANSITIONS` ⇄ `imm_16_mr_workflow.json` **2 chiều edge-by-edge**; loader `_load_mr_workflow_edges()` parse JSON THẬT (`frappe.get_app_path("assetcore","assetcore","workflow","imm_16_mr_workflow.json")`) + DEDUPE cạnh lặp-theo-vai (8 entry → 3 cạnh); `map_edges` đọc `svc._MR_TRANSITIONS` VERBATIM (KHÔNG map thứ hai); set-diff cả 2 chiều so với `_MR_EXCEPTION_EDGES` (không so `∅` cứng → dễ mở rộng có kiểm soát); codomain ⊆ 4 state hợp lệ; message FAIL nêu RÕ cạnh nào drift + hệ quả (dead/câm).
- **Never**: KHÔNG sửa `services/imm16.py` (`_MR_TRANSITIONS`/`get_management_review`/`advance_mr_state`/`finalize_management_review` giữ nguyên — map ĐÃ in-sync 3-cạnh-khớp-1-1 lúc grounding); KHÔNG sửa `imm_16_mr_workflow.json`/fixtures (admin-override `AssetCore Super Admin` + `System Manager` ĐÃ có sẵn trên cả 3 cạnh ⇒ 0 reload/migrate + gate admin GREEN); KHÔNG chỉ so codomain `next_state` (bỏ sót drift "sai nguồn" — phải EDGE); KHÔNG nới assert để test GREEN khi drift THẬT (drift = fix map/JSON hoặc bồi EXCEPTION_EDGE + ADR = HARD-STOP USER); KHÔNG so cứng `== set()` (dùng `_MR_EXCEPTION_EDGES` — 1 chỗ khai báo miễn trừ).

## III.G. Dashboard / Reports / Cross-module

| Function | Signature | Ghi chú |
|---|---|---|
| `get_dashboard_stats()` | `→ dict` | KPIs + trend_12m + recent_findings. `capa_open` ← **SoT `imm00._open_capa_filter()`** (status NOT IN Closed — KHÔNG inline `IN [Open, In Progress]` bỏ sót Overdue/Pending Verification) → khớp KPI dashboard `capa_open` byte-for-byte. `capa_overdue` ← **SoT `imm00._overdue_capa_filter()`** → khớp KPI dashboard + drill byte-for-byte |
| `_period_bounds(year, month)` | `→ (start, end_inclusive)` | **SoT biên kỳ** (BR-16-12) — half-open `[start, next)`; `end_inclusive` = ngày cuối tháng (Frappe `between` inclusive → tránh off-by-one). Dùng chung bởi `generate_scorecard` + `get_compliance_heatmap` |
| `get_compliance_heatmap(period_year, period_month)` | `→ dict` | Module×Dept matrix; lọc kỳ theo hằng `PERIOD_ANCHOR_FIELD` (=`evaluation_date`) + helper `_period_bounds()` — BR-16-12 canonical, KHÔNG `detected_date` (CÙNG hằng/helper với `generate_scorecard` → KHÔNG drift); `cell.score` ← `compute_compliance_rate()` SoT (BR-16-11, KHÔNG còn `(total-nc)/total` inline). BUG-16-11: source_module từ Rule, BUG-16-04: dept label |
| `get_capa_aging()` | `→ dict` | buckets: 0-7d/8-30d/31-60d/60+. Tập CAPA mở ← **SoT `imm00._open_capa_filter()`** (status NOT IN Closed — KHÔNG inline `IN [Open, In Progress]`). INVARIANT: `total_open == sum(buckets)` — record `opened_date` NULL bị loại khỏi CẢ HAI cách đếm (no null-skip divergence) |
| `get_overdue_actions()` | `→ dict` | overdue findings (>30d) + overdue CAPAs. `overdue_capas` ← **SoT `imm00._overdue_capa_filter()`** → len == KPI `capa_overdue` == `list_overdue_capas` drill (cùng dataset) |
| `check_asset_compliance_status(asset)` | `→ dict` | BR-16-09 gate. Critical CAPA mở ← **SoT `imm00._open_capa_filter()`** (status NOT IN Closed — KHÔNG inline `IN [Open, In Progress, Pending Verification]` bỏ sót `Overdue`) AND `imm_risk_level='Critical'`. `blocked=bool(crit_capas)`. **INVARIANT dưới cron**: byte-for-byte cùng tập trước/sau `check_capa_overdue` flip Open→Overdue → count không tụt, gate giữ block. `reasons[].status` = status thật (gồm `'Overdue'`), không nuốt. Consumer chung: `gate_wo_submit` (IMM-08/09) + `services/imm04.py` commissioning gate — cùng hành vi invariant |
| `get_record_history(ref_doctype, ref_name, limit)` | `→ dict` | audit trail cho Finding/CAPA/MR/Rule |

## III.H. Doc-event Real-time Evaluators

| Function | Trigger DocType |
|---|---|
| `eval_imm04_realtime(doc, method)` | `Asset Commissioning.on_submit` |
| `eval_imm05_realtime(doc, method)` | `AC Asset Document.on_update` (khi workflow_state=Expired) |
| `eval_imm08_09_realtime(doc, method)` | `IMM PM Work Order.on_submit`, `IMM CM Work Order.on_submit` |
| `eval_imm11_realtime(doc, method)` | `IMM Calibration Record.on_submit` |
| `gate_wo_submit(doc, method)` | `PM Work Order.validate`, `Asset Repair.validate` — đọc `asset_ref`; `check_asset_compliance_status().blocked` → `frappe.throw` (FE hiển thị verbatim). Chặn cả khi Critical CAPA status=`'Overdue'` (invariant). Commissioning IMM-04 (`services/imm04.py`) gọi cùng gate qua ServiceError `COMPLIANCE_BLOCKED` |

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

> **Self-Correction round 12 (RC-CAPA-EFF) — cổng hiệu quả CAPA về 1 SoT (đồng bộ với IMM-00 04 §II.5.a).** Code thực thi `services/imm16.py:616` đã **drift** khỏi spec này: thêm điều kiện kép `status=='Closed' AND workflow_state=='Closed'` + inline 2 literal VR-06/VR-07 → mọi save-to-Closed không set `workflow_state='Closed'` lọt cổng, và độ chặt lặp ở 2 nơi (đây + `services/imm00.py::close_capa` vốn KHÔNG gate). Hợp nhất: `capa_record_validate` fire cổng khi **`status=='Closed'` BẤT KỂ `workflow_state`**, và gọi predicate SoT DUY NHẤT `assert_capa_effectiveness_gate(doc)` (định nghĩa ở `services/imm00.py`) thay vì inline literal. `advance_capa_state` (VR-06/VR-07 đã đúng, raise `ServiceError('FIN-007', ...)`) KHÔNG đổi hành vi. Chi tiết predicate + 2 đường gọi (close_capa legacy + đường này): `docs/imm-00/04_Backend_Design.md §II.5.a`.

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
    if doc.status == "Closed":            # round 12: BẤT KỂ workflow_state (bỏ điều kiện kép cũ)
        from assetcore.services.imm00 import assert_capa_effectiveness_gate
        from assetcore.services.shared import ServiceError
        try:
            assert_capa_effectiveness_gate(doc)   # SoT đơn VR-06/VR-07 (INVARIANT-1)
        except ServiceError as e:
            frappe.throw(e.message)               # controller semantics (ValidationError)

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
| Open | 0 | Warning | → Under Review (Compliance Manager / Compliance User) |
| Under Review | 0 | Warning | → Confirmed NC / False Positive (Compliance Manager) ; → Waived (Compliance Manager only) |
| Confirmed NC | 0 | Danger | → Resolved (auto khi CAPA Closed) |
| False Positive | 0 | Default | terminal |
| Waived | 1 | Default | terminal (auto re-open sau expiry) |
| Resolved | 1 | Success | → Closed (Compliance Manager) |
| Closed | 2 | Success | terminal |

**Workflow actions (Vietnamese):** "Bắt đầu xem xét", "Xác nhận vi phạm", "Xác nhận không vi phạm", "Miễn trừ", "Đánh dấu đã giải quyết", "Đóng finding"

> **Dual-track status/workflow_state — LOCKSTEP (ADR-IMM-16-05, SUPERSEDES ADR-IMM-16-01 §V.1 note cũ).** Bảng trên là track `workflow_state` (workflow-engine is_active=1, gồm cạnh `Resolved→Closed`). Track `status` (field service enforce) do service-action đặt trực tiếp. **Round 14 (CR-WF-16-FIND) đóng DESYNC:** mỗi transition-fn (start_review/confirm/mark_false/waive/close + cascade CAPA) đặt CẢ HAI track lockstep (`workflow_state = status` qua `frappe.db.set_value`, §III.B.2) — mirror CAPA (ADR-IMM-16-03 "đặt CẢ HAI") / MR (ADR-IMM-16-04) / IMM-12 (imm12:797). **Note cũ ("workflow_state là track song song service KHÔNG chạm") ĐÃ SAI** → tạo desync workflow_state đọng `'Open'` trên workflow ĐANG ACTIVE. CTA trên FindingDetail vẫn chỉ phát từ `_FINDING_VALID_TRANSITIONS` (§III.B.1) — status-CTA `Under Review / Confirmed NC / False Positive / Waived` (+ route CAPA qua `can_create_capa`). **EXCEPTION_EDGES = {Resolved (CAPA-auto), Closed (workflow-engine terminal)}** — 2 state reachable qua workflow nhưng KHÔNG do service-CTA cán bộ sinh (INV-16-B, §III.B.2). `Closed` chỉ tới bằng workflow-engine desk button — FE SPA 0 nút Close.

## V.2. Internal Audit Workflow (`imm_16_audit_workflow.json`)

| State | doc_status | Type | Allowed roles |
|---|---|---|---|
| Planned | 0 | Default | Compliance Manager, AssetCore Super Admin |
| In Progress | 0 | Warning | Compliance Manager, Compliance User, AssetCore Super Admin |
| Reporting | 0 | Warning | Compliance Manager, AssetCore Super Admin |
| Closed | 1 | Success | Compliance Manager, AssetCore Super Admin |

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
| `check_capa_due` | `daily` | Daily | overdue CAPA escalation (tiered: Critical ≥1d, High ≥3d). Tập overdue ← **SoT `imm00._overdue_capa_filter()`** (cùng INVARIANT với KPI + cron flip) |
| `check_audit_milestones` | `daily` | Daily | Planned audit bắt đầu trong 7 ngày → email Lead Auditor |
| `run_compliance_evaluation_weekly` | `weekly` | Weekly Monday | evaluation_frequency = Weekly |
| `check_management_review_due` | `weekly` | Weekly Monday | Quý hiện tại chưa có MR Closed → alert |
| `update_compliance_scorecard` | `monthly` | Monthly 1st | Tổng hợp Scorecard tháng trước; skip nếu đã tồn tại |

> **Khác biệt vs spec cũ**: `run_compliance_evaluation_daily` KHÔNG tồn tại — thay bằng `evaluate_all_compliance_rules` (daily). `check_capa_due_imm16` → đổi tên thành `check_capa_due`. Không có `EscalationMatrix` class — escalation logic inline trong `_escalate_capa()` / `_send_capa_escalation()`.

## VI.2. Escalation thực tế (Vòng 13 — Self-Correction RC-CAPA-ESC)

> ⚠️ **Self-Correction (BA Vòng 13).** Spec cũ ở mục này codify đúng 2 lỗi thiết kế gốc đang nằm trong code (`if/elif` + đọc `imm_risk_level` thô + recipient "IMM Workshop Lead" đã chết). Mục này ghi đè bằng thiết kế tiered độc lập + SoT severity + idempotency/audit. 4 invariant ràng buộc: **INV-CAPA-ESC-1..4** (bảng dưới). Recipient Level-2 = SoT `notify_roles.CAPA_ESCALATION_MANAGER` (= `Compliance Manager`) — KHÔNG còn "IMM Workshop Lead".

### VI.2.0. Bốn lỗi thiết kế gốc (root cause)

| Bug | Triệu chứng | Nguyên nhân |
|---|---|---|
| **RC-ESC-1 TIER** | CAPA `imm_risk_level=Critical` quá hạn ≥3 ngày KHÔNG BAO GIỜ lên manager | `if severity=='Critical' and >=1` luôn khớp branch-1 → `elif` Level-2 **chết** (Python if/elif: nhánh đầu khớp → bỏ qua nhánh sau). Critical chỉ bao giờ chạm Level-1. |
| **RC-ESC-2 FIELD-SoT** | CAPA `severity=Critical` nhưng KHÔNG escalate | `_escalate_capa` đọc `imm_risk_level` (default rỗng/`Medium`) trong khi severity THẬT ở field `severity`. `create_capa` (imm00) CHỈ set `severity`; `create_capa_from_incident` (imm16) KHÔNG set `imm_risk_level`; `create_capa_from_finding` set `imm_risk_level="Medium"` mặc định kể cả CAPA Critical. → key escalation đọc nhầm trường rỗng → `or "Medium"` → không escalate. |
| **RC-ESC-3 IDEMPOTENCY** | Cron daily **re-send** email tier cũ mỗi ngày khi CAPA còn quá hạn | Không lưu mức đã escalate → mỗi lần `check_capa_due` chạy lại gửi y nguyên. Vi phạm CLAUDE.md §5 "mọi action có record" (không audit từng lần). |
| **RC-ESC-4 N+1/DEAD-SELECT** | 1 query thừa/CAPA + field `severity` select ra nhưng không dùng | `check_capa_due` select `severity` (dòng 538) nhưng `_escalate_capa` lại `db.get_value(imm_risk_level)` riêng (dòng 792). Hai field rời nhau, không truyền nhau. |

### VI.2.1. SoT severity escalation — `_capa_escalation_severity(row)` (FIX RC-ESC-2)

> **BA chốt SoT (quyết định cuối):** "mức rủi ro escalation" = **effective risk level** trong từ vựng tier `{Low, Medium, High, Critical}`. Lý do dùng từ vựng `imm_risk_level` (không phải `severity` Minor/Major/Critical): biên BVA (High=3d→Level-2) nói "High" — chỉ tồn tại trong `imm_risk_level`, KHÔNG có trong `severity`. → cần normalize cả 2 trường về 1 thang.

Predicate thuần (không I/O), nhận **row đã select trong `check_capa_due`** (KHÔNG query lại — đồng thời fix RC-ESC-4):

```python
# services/imm16.py — module-level helper (mới)
_ESC_RISK_VOCAB = ("Low", "Medium", "High", "Critical")  # thang tier escalation

def _severity_to_risk(severity: str | None) -> str:
    """Normalize field `severity` (Minor/Major/Critical) → thang risk tier.
    Minor→Low, Major→High, Critical→Critical. Rỗng/lạ → '' (no signal)."""
    return {"Minor": "Low", "Major": "High", "Critical": "Critical"}.get(
        (severity or "").strip(), "")

def _capa_escalation_severity(row: dict) -> str:
    """SoT effective-risk cho escalation (FIX RC-ESC-2).
    Ưu tiên imm_risk_level KHI nó là tín hiệu thật (High/Critical);
    ngược lại (rỗng / default-noise 'Medium' / 'Low') fall back severity-normalized.
    Trả 1 giá trị trong _ESC_RISK_VOCAB hoặc '' (không escalate)."""
    risk = (row.get("imm_risk_level") or "").strip()
    if risk in ("High", "Critical"):
        return risk                       # imm_risk_level đã là tín hiệu rõ → tin
    sev_risk = _severity_to_risk(row.get("severity"))
    if sev_risk in ("High", "Critical"):
        return sev_risk                   # severity THẬT vượt imm_risk_level default → dùng
    # cả 2 đều ≤ Medium → trả mức cao hơn để minh bạch, nhưng vẫn KHÔNG escalate
    return risk or sev_risk or "Medium"
```

**INV-CAPA-ESC-2 (FIELD-SoT):** với CAPA `severity='Critical'`, `_capa_escalation_severity` trả `'Critical'` **bất kể** `imm_risk_level` rỗng/`Medium`. → Critical-CAPA từ incident/finding escalate đúng mà không cần nâng `imm_risk_level` thủ công.

### VI.2.2. Tier độc lập (FIX RC-ESC-1) — `_escalate_capa(capa)`

`check_capa_due` truyền NGUYÊN row (đã có `severity` + thêm `imm_risk_level`, `escalation_level` vào field select — fix RC-ESC-4) vào `_escalate_capa`. Logic tier **độc lập** (KHÔNG if/elif loại trừ):

```python
def _escalate_capa(capa: dict) -> None:
    overdue_days = (getdate(nowdate()) - getdate(capa["due_date"])).days
    if overdue_days < 1:
        return                                   # BVA: 0d → no escalate
    risk = _capa_escalation_severity(capa)        # SoT (VI.2.1)
    already = int(capa.get("escalation_level") or 0)  # tier đã gửi (FIX RC-ESC-3)

    # Tính tier ĐÁNG LẼ phải đạt theo (risk × overdue) — ĐỘC LẬP, không elif
    target = 0
    if risk == "Critical":
        if overdue_days >= 1:
            target = max(target, 1)              # Critical ≥1d → Level-1
        if overdue_days >= 3:
            target = max(target, 2)              # Critical ≥3d → Level-2 (KÈM Level-1)
    elif risk == "High":
        if overdue_days >= 3:
            target = max(target, 2)              # High ≥3d → Level-2 (BVA: High <3d no escalate)
    # Medium/Low → target = 0 (KHÔNG escalate bất kỳ ngày — INV-CAPA-ESC liệt kê BVA)

    # CHỈ gửi các tier MỚI (level > already) → idempotency (FIX RC-ESC-3)
    for level in range(already + 1, target + 1):
        _send_capa_escalation(capa, level=level)
        _record_capa_escalation(capa, level=level)   # 1 audit record/tier (CLAUDE.md §5)
    if target > already:
        frappe.db.set_value("IMM CAPA Record", capa["name"],
                            "escalation_level", target, update_modified=False)
```

> ⚠️ **Critical ≥3d lần ĐẦU** (`already=0`, `target=2`): vòng `range(1, 3)` → gửi CẢ Level-1 VÀ Level-2 trong 1 lần chạy (cả 2 đều "mới"). Đúng AC BUG-1 (count level=2 ≥ 1) + biên BVA (=3d đồng thời Level-1 nếu chưa từng).

### VI.2.3. Idempotency + Audit (FIX RC-ESC-3) — field `escalation_level` + `_record_capa_escalation`

**Schema-delta (cần `bench migrate`):** thêm field vào `IMM CAPA Record`:

| fieldname | fieldtype | label | default | thuộc tính |
|---|---|---|---|---|
| `escalation_level` | Int | Mức leo thang | `0` | `read_only=1`, `in_list_view=0`, đặt sau section Verification / trước `notes`. Bút toán hệ thống — không cho user sửa tay. |

`_record_capa_escalation(capa, level)` — best-effort, KHÔNG vỡ luồng nếu audit fail:

```python
def _record_capa_escalation(capa: dict, level: int) -> None:
    """Ghi 1 IMM Audit Trail/tier escalation (CLAUDE.md §5 'mọi action có record')."""
    try:
        from assetcore.utils.lifecycle import log_audit_event
        log_audit_event(
            asset=capa.get("asset") or "",
            event_type="CAPA",                  # option hợp lệ sẵn trên IMM Audit Trail
            actor="Administrator",
            ref_doctype="IMM CAPA Record", ref_name=capa["name"],
            change_summary=_("CAPA {0} leo thang Level-{1} (quá hạn)").format(capa["name"], level),
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(),
                         f"IMM-16 CAPA escalation audit failed: {capa.get('name')}")
```

**INV-CAPA-ESC-3 (IDEMPOTENCY):** chạy `check_capa_due` 2 lần liên tiếp **cùng ngày** → lần 2 `already == target` → vòng `range` rỗng → KHÔNG `_send_capa_escalation` thêm (mock `_safe_sendmail` call-count bất biến) + KHÔNG ghi audit trùng.

> **`IMM16_ESCALATION_RETRY_HOURS`** (env, default 24 — đã có trong 08 §Config): cadence retry. Với cron daily mặc định, `escalation_level` đã chặn re-send trong-ngày; biến này dành cho cấu hình gửi-lại tier ĐÃ gửi sau N giờ nếu CAPA vẫn treo (roadmap — KHÔNG yêu cầu round này hiện thực reset-by-time; round này chỉ honor bằng cách KHÔNG re-send < retry window). Round 13 chốt: idempotency theo `escalation_level` là cơ chế chính; retry-by-time là tinh chỉnh cadence tương lai `[ROADMAP]`.

### VI.2.4. Bảng tier + recipient (cập nhật — recipient Level-2 đổi SoT)

| Effective risk | Overdue | Tier kích hoạt | Recipient |
|---|---|---|---|
| Critical | ≥ 1d, < 3d | Level-1 | `responsible` |
| Critical | ≥ 3d (lần đầu) | Level-1 **+** Level-2 | `responsible` + `notify_roles.CAPA_ESCALATION_MANAGER` (= `Compliance Manager`) |
| High | ≥ 3d | Level-2 | `responsible` + `CAPA_ESCALATION_MANAGER` |
| High | < 3d | — (no escalate) | — |
| Medium / Low | bất kỳ ngày | — (no escalate) | — |

> Recipient Level-2 lấy qua `_get_role_emails(notify_roles.CAPA_ESCALATION_MANAGER)` (SoT R21 — KHÔNG raw SQL `tabHas Role`, KHÔNG literal "IMM Workshop Lead" như spec cũ).

### VI.2.5. Invariants (test-anchor)

| Invariant | Phát biểu | Test BVA |
|---|---|---|
| **INV-CAPA-ESC-1 (TIER)** | Critical ≥3d (`already=0`) → `_send_capa_escalation(level=2)` được gọi ≥1 (đồng thời level=1) | =0d no-call · =1d L1 only · =2d L1 only (chưa L2) · =3d L1+L2 |
| **INV-CAPA-ESC-2 (FIELD-SoT)** | `severity='Critical'` ∧ `imm_risk_level` rỗng/`Medium` → vẫn escalate (effective risk='Critical') | severity-driven escalate |
| **INV-CAPA-ESC-3 (IDEMPOTENCY+AUDIT)** | 2× `check_capa_due` cùng ngày → `_safe_sendmail` call-count bất biến lần 2; mỗi tier mới = đúng 1 audit record | 2-run mock spy |
| **INV-CAPA-ESC-4 (NO N+1)** | `_escalate_capa` đọc `severity`/`imm_risk_level`/`escalation_level` TỪ row select sẵn — 0 `db.get_value` phụ/CAPA | spy db.get_value=0 |
| **BVA-HIGH** | High =2d → no escalate; =3d → Level-2 | High boundary |
| **BVA-LOWMED** | Medium/Low mọi ngày → KHÔNG escalate | negative |

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
