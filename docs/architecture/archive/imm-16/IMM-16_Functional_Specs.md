# IMM-16 — Functional Specifications

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-16 — Compliance Monitoring & CAPA |
| Phiên bản | 0.2.0 (Wave 2 — alignment with existing CAPA backbone) |
| Ngày cập nhật | 2026-05-04 |
| Trạng thái | PARTIAL — CAPA core LIVE, compliance/audit/scorecard PLANNED |
| Tác giả | AssetCore Team |
| Chuẩn tham chiếu | ISO 13485:2016 §8.2.4, §8.5, §5.6; WHO HTM 5.4; NĐ 98/2021/NĐ-CP §35-§38 |

---

## 0. Phạm vi thay đổi vs hệ thống hiện tại

### 0.1 Đã có (REUSE)

| Artefact | Trạng thái | Vai trò |
|---|---|---|
| `IMM CAPA Record` (DocType, submittable, naming `CAPA-.YYYY.-.#####`) | LIVE | CAPA backbone — mọi tham chiếu "CAPA" trong tài liệu này map về DocType này. |
| `Audit Finding` (child DocType) | LIVE | Reuse cho `IMM Internal Audit` (cùng schema với `IMM Supplier Audit`). |
| `IMM Audit Trail` (hash chain) | LIVE | Persistence audit trail bất biến. |
| `IMM RCA Record` + 5-Why Step | LIVE | Reuse cho RCA — KHÔNG re-implement 5-Why trong CAPA. |
| `services/imm00.py` (`create_capa`, `close_capa`, `check_capa_overdue`) | LIVE | Service layer chia sẻ với IMM-12. |

### 0.2 Mở rộng (CUSTOM FIELDS)

- Trên `IMM CAPA Record`: 11 field IMM-16 (`imm_root_cause_method`, `imm_correction_immediate`, `imm_action_plan` table, `imm_effectiveness_check_date`, `imm_effectiveness_evidence`, `imm_change_control_ref`, `imm_risk_level`, `imm_compliance_finding_ref`, `imm_audit_finding_ref`, `imm_rca_ref`, `imm_reopen_count`) + extend Select option `source_type` (thêm `Audit Finding`, `Compliance Finding`, `Management Review`).
- Trên `Audit Finding`: 2 field (`imm_finding_link`, `imm_capa_link`).

### 0.3 Thêm mới (PLANNED)

`IMM Compliance Rule`, `IMM Compliance Finding`, `IMM Internal Audit`, `IMM CAPA Action Step` (child), `IMM Compliance Scorecard`, `IMM Management Review`, `api/imm16.py`, `services/imm16.py`, 5 scheduler entries, 4 workflows.

### 0.4 Phân biệt module

| IMM-16 | IMM-10 | IMM-03 | IMM-12 |
|---|---|---|---|
| Internal compliance + audit + CAPA | EXTERNAL recall / FSCA / vigilance | Supplier qualification + vendor audit (`IMM Supplier Audit` LIVE) | Corrective + RCA (đã share `IMM CAPA Record`) |

---

## 1. Scope

### 1.1 In Scope

| # | Chức năng | Mô tả |
|---|---|---|
| F-01 | Compliance Rule Engine | Khai báo rule declarative (source module, threshold, severity, frequency) — versioned |
| F-02 | Auto Compliance Evaluation | Scheduler đánh giá rule active → upsert Finding (idempotent) |
| F-03 | Manual Finding Entry | Tổ HC-QLCL/Internal Auditor tạo Finding thủ công |
| F-04 | Internal Audit Cycle | Plan → Execute (checklist + Audit Finding child) → Reporting → Close; auto sinh Compliance Finding từ checklist Major/Minor NC |
| F-05 | NC / CAPA Lifecycle (extend `IMM CAPA Record`) | Workflow extend: Open → Investigating → Action Plan → Implementation → Verification → Closed; Re-open nếu effectiveness fail. **Không thay field `status` cũ — thêm sub-state qua `workflow_state`** (xem §6 migration). |
| F-06 | Root Cause Analysis | Reuse `IMM RCA Record` + 5-Why Step có sẵn — link qua Custom Field `imm_rca_ref`. CAPA Record có thêm `imm_root_cause_method` để đánh dấu phương pháp. |
| F-07 | CAPA Effectiveness Check | Verification phase + check date + result (dùng field `effectiveness_check` đã có trên CAPA Record); Not Effective → Re-open (`imm_reopen_count++`) |
| F-08 | Compliance Scorecard | Snapshot tháng — score % toàn hệ + theo module + theo dept; immutable sau publish |
| F-09 | Management Review | Hồ sơ họp định kỳ (quý) per ISO 13485 §5.6, gồm input/output actions |
| F-10 | Compliance Heatmap | Module × Department matrix, drill-down về Finding |
| F-11 | Cross-module Gate | Hook trong `services/imm08.py` + `services/imm09.py.validate_*` → block Submit WO nếu asset có CAPA `imm_risk_level=Critical` AND `status` IN (Open, In Progress, Pending Verification) |
| F-12 | Waiver Process | VP Block2 phê duyệt miễn rule + expiry date + bằng chứng |
| F-13 | Audit Trail bắt buộc | Mọi finding/CAPA/audit/scorecard versioned qua `IMM Audit Trail` (hash chain); scorecard published immutable |
| F-14 | Escalation Matrix | CAPA quá hạn → email theo level (Owner → Workshop Head → VP Block2 → Trưởng phòng) |
| F-15 | Integration ingestion | Consume tín hiệu từ IMM-04/05/06/08/09/10/11/12/15 |

### 1.2 Out of Scope

| # | Chức năng | Module phụ trách |
|---|---|---|
| 1 | Quản lý hồ sơ tài liệu thiết bị | IMM-05 |
| 2 | Lịch PM, Calibration | IMM-08, IMM-11 |
| 3 | Vendor recall / FSCA / vigilance | IMM-10 (external) |
| 4 | Vendor-side audit | IMM-03 (`IMM Supplier Audit` đã LIVE) |
| 5 | RCA infrastructure (5-Why, Fishbone modeling) | IMM-12 (đã LIVE qua `IMM RCA Record`) |
| 6 | Predictive analytics | IMM-17 |
| 7 | Electronic signature pháp lý | v2.0 (FDA 21 CFR Part 11 — phase 2) |
| 8 | External regulator submission | Phase 2 |

---

## 2. Actors

| Actor | Vị trí thực tại BV | Quyền chính | Trách nhiệm |
|---|---|---|---|
| Tổ HC-QLCL / IMM QA Officer | Tổ HC-QLCL (primary owner) | Full Finding/Audit/CAPA Record/Scorecard/MR | Quản trị rule, confirm NC, lead audit, theo dõi CAPA, publish scorecard |
| Internal Auditor (sub-role) | Thành viên audit team | R/W Audit + Finding | Thực hiện audit, ghi checklist, raise NC |
| Workshop Head | Trưởng Phân xưởng | R/W Finding + CAPA | Action owner cấp xưởng, theo dõi escalation |
| Biomed Engineer / IMM Biomed Technician | Kỹ sư Biomedical | R/W Finding + CAPA action step | Thực hiện corrective action kỹ thuật |
| HTM Technician / IMM Technician | Kỹ thuật viên HTM | R/W CAPA Action Step | Thực hiện step được giao |
| VP Block2 | Phó Khối 2 (Operations) | R/W Waive Finding + Approve CAPA Close + Sign Scorecard | Phê duyệt cuối, chair Management Review |
| VP Block1 | Phó Khối 1 (Planning) | R Audit/CAPA/Scorecard | Tham dự Management Review |
| Trưởng phòng / IMM Department Head | Department Head | R/W (action owner cấp khoa) | Action owner khi CAPA gắn với khoa |
| CMMS Admin / IMM System Admin | IT/CMMS | Full | Quản trị, override |
| System (Scheduler) | — | system-only | Auto-eval rule, scorecard, escalation |

---

## 3. User Stories (Gherkin)

### US-16-01 — Khai báo Compliance Rule

```gherkin
As Tổ HC-QLCL,
I want khai báo 1 rule mới (source IMM-08, threshold PM compliance < 90%),
So that hệ thống tự động đánh giá định kỳ.

Scenario: Tạo rule hợp lệ
  Given tôi có role Tổ HC-QLCL
  When tôi POST /api/method/assetcore.api.imm16.create_rule với
    {rule_code: "R-IMM08-PM-COMP-90",
     source_module: "IMM-08",
     category: "PM",
     severity: "High",
     threshold_definition: {"metric":"pm_compliance_pct","op":"<","value":90},
     evaluation_frequency: "Monthly",
     owner_role: "Workshop Head",
     qms_doc_ref: "PR-IMMIS-08-01",
     regulatory_reference: "ISO 13485 §7.5.1"}
  Then response.success = true
  And rule.is_active = 1
  And rule.version = "1.0"
```

### US-16-02 — Auto-detect Finding qua scheduler

```gherkin
As System,
When scheduler run_compliance_evaluation chạy theo frequency của rule,
I evaluate rule và upsert Finding nếu vi phạm threshold.

Scenario: PM compliance khoa ICU = 78% (< 90%)
  Given rule R-IMM08-PM-COMP-90 active, frequency=Monthly
  When scheduler evaluation kích hoạt vào ngày 1 tháng
  Then sinh IMM Compliance Finding với
    severity="High", current_value=78, threshold_value=90,
    source_record="department:ICU", status="Open"
  And idempotent: chạy lại cùng ngày không tạo bản ghi mới
```

### US-16-03 — Confirm NC & open CAPA Record

```gherkin
As Tổ HC-QLCL,
When Finding ở Under Review,
I confirm là NC và mở CAPA Record (reuse IMM CAPA Record).

Scenario: Open CAPA từ Finding
  Given finding ở "Under Review" với severity="High"
  When tôi POST confirm_finding(name) → status "Confirmed NC"
  And POST link_to_capa(finding) → tạo IMM CAPA Record mới (qua imm00.create_capa)
  Then capa.source_type="Compliance Finding"
  And capa.imm_compliance_finding_ref=finding.name
  And finding.capa_ref=capa.name (CAPA-YYYY-#####)
  And finding.status="Resolved" sau khi capa.status="Closed"
```

### US-16-04 — Effectiveness check & Re-open

```gherkin
As Tổ HC-QLCL,
When CAPA Record ở workflow_state "Verification",
I run effectiveness check sau N tuần monitoring.

Scenario: Effective → Close
  Given capa workflow_state="Verification", imm_effectiveness_check_date=today
  When POST perform_effectiveness_check(name, result="Effective", evidence)
  Then capa.status="Closed", workflow_state="Closed"
  And capa.effectiveness_check="Effective" (field hiện có)

Scenario: Not Effective → Re-open
  When POST perform_effectiveness_check(name, result="Not Effective", evidence)
  Then capa.status="In Progress", workflow_state="Investigating"
  And capa.imm_reopen_count += 1
  And finding linked vẫn status "Confirmed NC"
  And BR-16-03 throw nếu cố Close mà chưa Effective
```

### US-16-05 — Internal Audit cycle

```gherkin
As Lead Auditor,
I plan và execute internal audit cho scope đã định.

Scenario: Plan audit
  Given audit_code="A-2026-Q2-MAINT", scope_modules=[IMM-08, IMM-11]
  When tôi POST create_audit({...})
  Then audit.status="Planned"
  And lead_auditor được gán
  And scheduler check_audit_milestones cảnh báo 7 ngày trước planned_start

Scenario: Execute checklist + ghi Audit Finding
  Given audit ở "In Progress"
  When tôi complete_audit_checklist(name, items) với 1 item finding_status="Major NC"
  Then sinh IMM Compliance Finding tự động link checklist item
  And ghi 1 row vào audit.findings (Audit Finding child) với severity=Major,
    imm_finding_link=finding.name
  And finding.severity="High" mặc định cho Major NC

Scenario: Close audit
  Given audit ở "Reporting", tất cả Major NC trong Audit Finding child có imm_capa_link
  When tôi close_audit(name) (role: Tổ HC-QLCL hoặc VP Block2)
  Then audit.status="Closed"
  And BR-16-04 enforce: Audit Finding row severity=Major chưa link CAPA → throw
```

### US-16-06 — Compliance Scorecard sinh tự động

```gherkin
As System,
On 1st of month at 03:00,
I aggregate findings tháng trước và sinh Scorecard Draft.

Scenario: Sinh scorecard tháng
  Given findings tháng 4/2026 có 120 đánh giá, 18 NC, 5 đang waive
  When scheduler update_compliance_scorecard chạy
  Then sinh IMM Compliance Scorecard {period_year:2026, period_month:4}
  And score_pct = (120-18)/120 * 100 = 85%
  And score_by_module + score_by_department được fill
  And status="Draft", is_published=0

Scenario: Publish scorecard
  Given scorecard "Draft" đã review
  When VP Block2 POST publish_scorecard(name)
  Then is_published=1, approved_by_for_review=session.user
  And BR-16-07: sửa scorecard sau publish → throw
```

### US-16-07 — Waive Finding (BR-16-06)

```gherkin
As VP Block2,
When 1 Finding hợp lý không cần CAPA (false alarm có context),
I waive với reason + expiry.

Scenario: Waive thành công
  Given finding "Under Review", role=VP Block2
  When POST waive_finding(name, waiver_reason, evidence_attach, expiry_date)
  Then finding.status="Waived"
  And waiver_reason ≥ 50 ký tự
  And expiry_date > today

Scenario: Block waive nếu không phải VP Block2
  Given role=Workshop Head
  When POST waive_finding(...)
  Then response.code="FORBIDDEN" (BR-16-06)
```

### US-16-08 — Gate IMM-08/09 (BR-16-09)

```gherkin
As IMM-08/09 service validator,
Before submitting Work Order on asset,
I check IMM-16 compliance status.

Scenario: Asset có CAPA Critical OPEN
  Given asset AC-ASSET-2026-0001 có 1 CAPA Record
    với imm_risk_level="Critical", status="In Progress"
  When services/imm08.py.validate_pm_wo gọi check_asset_compliance_status(asset)
  Then response = {blocked: true, reason: "CAPA-2026-00007 OPEN (Critical)"}
  And IMM-08 throw: "Block: thiết bị có CAPA Critical chưa close (BR-16-09)"
```

### US-16-09 — Management Review quý

```gherkin
As VP Block2 (Chair),
Each quarter I hold Management Review per ISO 13485 §5.6.

Scenario: Tạo + finalize MR
  Given quý 2/2026 chưa có Management Review
  When tôi create_management_review(...) + sau cuộc họp finalize_management_review(name, minutes_doc)
  Then MR.status="Minutes Approved" → "Closed"
  And MR.scorecard_ref link Scorecard published
  And output_actions table có items với owner + due_date

Scenario: Block KPI publish nếu missed (BR-16-08)
  Given quý 2 đã hết, không có MR
  When publish_scorecard(scorecard_quarter_3_first_month)
  Then throw: "Block: quý trước thiếu Management Review (BR-16-08)"
```

### US-16-10 — Compliance Heatmap

```gherkin
As VP Block2 / Tổ HC-QLCL,
I want xem heatmap module × department,
So that nhìn ra điểm yếu nhanh.

Acceptance:
  GET get_compliance_heatmap → matrix
  rows = modules (IMM-04..15)
  cols = departments (ICU, OR, ER, ...)
  cell = score_pct
  click cell → drill-down list_findings filtered
```

---

## 4. Business Rules

| ID | Rule | Enforce | Chuẩn |
|---|---|---|---|
| BR-16-01 | Finding severity ≥ High → mở CAPA Record trong 5 NLV | `check_capa_due` + Finding `validate()` | ISO 13485 §8.5 |
| BR-16-02 | CAPA Critical >30 ngày chưa close → escalate VP Block2 + Trưởng phòng | `check_capa_due` scheduler | Internal |
| BR-16-03 | CAPA Close chỉ khi `effectiveness_check=Effective`; Not Effective → Re-open + `imm_reopen_count++` | CAPA Record `validate()` | ISO 13485 §8.5 |
| BR-16-04 | Audit Major NC → CAPA Record + change control link nếu thay đổi master/process | `close_audit` validator | ISO 13485 §8.2.4 |
| BR-16-05 | Compliance Rule thay đổi threshold/severity → change control versioned | Rule controller `before_save` | ISO 13485 §4.2 |
| BR-16-06 | Waiver chỉ VP Block2 + reason ≥ 50 chars + evidence + expiry | `waive_finding` API | Internal |
| BR-16-07 | Scorecard published immutable; sửa → tạo restate phiên bản mới | Scorecard `validate()` | ISO 13485 §4.2 |
| BR-16-08 | Mỗi quý ≥1 Management Review; missed → block scorecard publish quý tiếp | `publish_scorecard` validator | ISO 13485 §5.6 |
| BR-16-09 | Asset có CAPA Record `imm_risk_level=Critical` AND `status` IN (Open, In Progress, Pending Verification) → block IMM-08/09 WO Submit | Hook tại `services/imm08.py` + `services/imm09.py.validate_*` gọi `check_asset_compliance_status` | Internal gate |
| BR-16-10 | Mọi thay đổi Finding/CAPA/Audit/Scorecard ghi `IMM Audit Trail` (hash chain) + Frappe Version | `track_changes=1` + `imm00.log_audit_event` | NĐ 98 |

---

## 5. Permission Matrix

| Action | Tổ HC-QLCL | Int. Auditor | Workshop Head | Biomed | HTM Tech | VP Block2 | VP Block1 | Trưởng phòng | CMMS Admin |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Create Rule | OK | — | — | — | — | — | — | — | OK |
| Update Rule (versioned) | OK | — | — | — | — | — | — | — | OK |
| Create Finding (manual) | OK | OK | OK | OK | — | — | — | — | OK |
| Confirm NC | OK | OK | — | — | — | — | — | — | OK |
| Mark False Positive | OK | OK | — | — | — | — | — | — | OK |
| Waive Finding | — | — | — | — | — | OK | — | — | OK |
| Create Audit | OK | — | — | — | — | — | — | — | OK |
| Execute Audit Checklist | OK | OK | — | — | — | — | — | — | OK |
| Close Audit | OK | — | — | — | — | OK | — | — | OK |
| Create CAPA Record | OK | OK | OK | OK | — | — | — | OK | OK |
| Edit CAPA Action Step | OK | — | OK | OK | OK | — | — | OK | OK |
| Effectiveness Check | OK | — | — | — | — | — | — | — | OK |
| Re-open CAPA | OK | — | — | — | — | — | — | — | OK |
| Publish Scorecard | OK | — | — | — | — | OK | — | — | OK |
| Finalize MR | — | — | — | — | — | OK | — | — | OK |
| Read All | OK | OK | OK | OK | OK | OK | OK | OK | OK |

> Quyền trên `IMM CAPA Record` giữ nguyên 12 role đã định nghĩa trong JSON LIVE; bảng trên chỉ thêm action mới của IMM-16.

---

## 6. Validation Rules

| VR ID | Field / Trigger | Rule | Error Message |
|---|---|---|---|
| VR-01 | Rule.threshold_definition | JSON valid + `metric/op/value` mandatory | "VR-01: Threshold rule không hợp lệ. Cần `metric`, `op`, `value`." |
| VR-02 | Rule.evaluation_frequency | IN (Realtime, Hourly, Daily, Weekly, Monthly, Quarterly) | "VR-02: Frequency không hợp lệ." |
| VR-03 | Finding.severity | IN (Low, Medium, High, Critical) | "VR-03: Severity không hợp lệ." |
| VR-04 | Finding waive | `waiver_reason` ≥ 50 chars + `evidence` reqd + `expiry_date > today` | "VR-04: Waiver thiếu lý do/evidence/expiry hợp lệ." |
| VR-05 | CAPA.imm_root_cause_method | IN (5-Why, Fishbone, FMEA, FTA, Other) khi advance to "Action Plan" | "VR-05: Phải chọn phương pháp phân tích root cause." |
| VR-06 | CAPA.effectiveness_check | IN (Effective, Partially Effective, Not Effective) khi workflow_state Verification → Closed | "VR-06: Effectiveness check chưa hoàn tất." |
| VR-07 | CAPA Close | Phải có `effectiveness_check = Effective` (BR-16-03) | "VR-07: Không thể Close khi effectiveness chưa Effective." |
| VR-08 | Audit close | Tất cả Audit Finding row severity=Major phải có `imm_capa_link` set (BR-16-04) | "VR-08: Còn {n} Major NC chưa mở CAPA." |
| VR-09 | Scorecard publish | `is_published=1` ⇒ block edit (BR-16-07) | "VR-09: Scorecard đã publish, không thể sửa. Hãy tạo restate mới." |
| VR-10 | Mgmt Review missed gate | Quý trước thiếu MR ⇒ block publish scorecard quý sau (BR-16-08) | "VR-10: Quý {q} chưa có Management Review." |
| VR-11 | Rule version change | Threshold/severity thay đổi ⇒ `version++` + `change_summary` reqd | "VR-11: Thay đổi rule yêu cầu Tóm tắt thay đổi (change control)." |
| VR-12 | CAPA due_date | `due_date > today` khi advance vào "Action Plan" | "VR-12: Hạn hoàn thành phải sau hôm nay." |

---

## 7. Non-Functional Requirements

| ID | Category | Yêu cầu | Target |
|---|---|---|---|
| NFR-16-01 | Performance — list | `list_findings` 50k records | P95 < 2s |
| NFR-16-02 | Rule evaluation throughput | 200 rules/run | < 5 phút |
| NFR-16-03 | Scheduler reliability | Idempotent finding upsert | UNIQUE (rule + source_record + evaluation_date) |
| NFR-16-04 | Audit trail | Mọi thao tác track qua Frappe Version + `IMM Audit Trail` | `track_changes=1` + hash chain |
| NFR-16-05 | Availability giờ hành chính | 99.5% | — |
| NFR-16-06 | Concurrent users | Đồng thời không degradation | 50 users |
| NFR-16-07 | Data retention | Sau closed | ≥ 10 năm (NĐ98) |
| NFR-16-08 | i18n | Error messages | `frappe._()` tiếng Việt |
| NFR-16-09 | API contract | Response chuẩn | `_ok()` / `_err()` |
| NFR-16-10 | Scorecard immutability | Sau publish | DB-level guard + controller `validate()` |
| NFR-16-11 | Notification | Email escalation | < 5 phút từ scheduler trigger |
| NFR-16-12 | Heatmap rendering | Module × Dept (10×15 cell) | < 1s |
| NFR-16-13 | Backwards compatibility | CAPA Record dữ liệu cũ (IMM-12) | Migration patch không phá; `workflow_state` default mapping (xem Module_Overview §5.1) |

---

## 8. Acceptance Criteria

| ID | Scenario | Pass criterion |
|---|---|---|
| AC-01 | Tạo rule hợp lệ | rule.is_active=1, version="1.0" |
| AC-02 | Auto evaluation idempotent | Chạy 2 lần cùng ngày → 1 finding |
| AC-03 | Confirm NC + open CAPA Record | finding.capa_ref set tới CAPA-YYYY-####, finding.status="Resolved" sau capa close |
| AC-04 | Effectiveness Not Effective → Re-open | capa.status="In Progress", workflow_state="Investigating", `imm_reopen_count++` |
| AC-05 | Audit close block khi NC chưa CAPA | VR-08 throw |
| AC-06 | Scorecard publish | is_published=1; sửa → VR-09 throw |
| AC-07 | Waive bởi non-VP-Block2 | response.code="FORBIDDEN" |
| AC-08 | Gate IMM-08/09 | check_asset_compliance_status trả `blocked=true` khi CAPA Crit OPEN |
| AC-09 | Quarterly MR enforce | Missed quý → VR-10 block publish |
| AC-10 | Compliance Heatmap drill-down | Click cell → list_findings filtered đúng (module, dept) |
| AC-11 | Rule version change requires change_summary | VR-11 throw nếu thiếu |
| AC-12 | Audit trail | Frappe Version + IMM Audit Trail entry cho tạo/sửa Finding/CAPA |
| AC-13 | Migration CAPA Record cũ | Bản ghi `In Progress` cũ map workflow_state="Investigating" mặc định, không vỡ data |

---

## 9. Glossary

| Thuật ngữ | Nghĩa |
|---|---|
| Compliance Rule | Quy tắc khai báo (declarative) đánh giá tuân thủ |
| Finding | Bản ghi non-compliance phát hiện auto/manual |
| NC (Non-Conformance) | Finding đã được confirm là vi phạm |
| CAPA Record | `IMM CAPA Record` — submittable DocType LIVE, naming `CAPA-.YYYY.-.#####` |
| Audit Finding | Child DocType LIVE — row trong `IMM Internal Audit` (và `IMM Supplier Audit`) |
| Effectiveness Check | Bước verify CAPA đã loại bỏ root cause (field `effectiveness_check` trên CAPA Record) |
| Internal Audit | Audit nội bộ — DocType `IMM Internal Audit` (mới) |
| Supplier Audit | Audit nhà cung cấp — `IMM Supplier Audit` (LIVE, IMM-03) |
| RCA Record | `IMM RCA Record` (LIVE) — reuse cho CAPA root cause analysis |
| Scorecard | Snapshot tháng — score % compliance toàn hệ + module + dept |
| Management Review | Họp định kỳ (quý) per ISO 13485 §5.6 |
| Waiver | Miễn áp dụng rule với approval VP Block2 + bằng chứng + expiry |
| Heatmap | Matrix module × department thể hiện compliance score |
| Re-open | Mở lại CAPA khi effectiveness check kết luận Not Effective |
| Restate | Phiên bản scorecard mới phát sinh khi cần sửa scorecard đã publish |
