# IMM-16 UAT Script

**Module:** IMM-16 — Compliance Monitoring & CAPA
**Version:** 0.1-draft (Wave 2)
**Ngày:** 2026-05-04
**Trạng thái:** PLANNED — chờ implement & UAT

---

## 1. Tổng quan

### 1.1 Mục tiêu UAT

Xác nhận module IMM-16 hoạt động đúng theo Functional Spec, bao gồm:

- Khai báo & versioning Compliance Rule (change control)
- Auto-detect Finding qua scheduler — idempotent
- Lifecycle Finding: Open → Under Review → Confirmed NC / False Positive / Waived
- Internal Audit cycle với checklist + auto-create Finding
- CAPA full lifecycle: Draft → Investigating → Action Plan → Implementation → Verification → Closed/Re-opened
- Effectiveness check (Effective / Not Effective re-open)
- Compliance Scorecard sinh tự động + publish + immutability
- Management Review quý + gate publish scorecard
- Cross-module gate (BR-16-09 block IMM-08/09 WO Submit)
- Heatmap drill-down
- Permission & audit trail

### 1.2 Preconditions

| # | Điều kiện | Cách chuẩn bị |
|---|---|---|
| PC-01 | Có ≥ 5 Asset đã mint từ IMM-04 | Chạy IMM-04 flow |
| PC-02 | Có user role Tổ HC-QLCL | `test_qlcl@assetcore.test` |
| PC-03 | Có user role Internal Auditor | `test_auditor@assetcore.test` |
| PC-04 | Có user role Workshop Head | `test_wshead@assetcore.test` |
| PC-05 | Có user role Biomed Engineer | `test_biomed@assetcore.test` |
| PC-06 | Có user role VP Block2 | `test_vp2@assetcore.test` |
| PC-07 | Có user role Trưởng phòng | `test_tp@assetcore.test` |
| PC-08 | Có user role CMMS Admin | `test_admin@assetcore.test` |
| PC-09 | 4 Workflow IMM-16 đã active | Verify Setup > Workflow |
| PC-10 | Baseline Compliance Rules đã seed (≥40 rule) | Chạy `bench migrate` + fixtures `imm16_compliance_rules_baseline.json` |
| PC-11 | Có dữ liệu test IMM-08 (PM Work Order) đủ để rule eval ra Finding | Tạo PM jobs với 2 dept compliance < 90% |
| PC-12 | Có dữ liệu test IMM-05 (doc expired/expiring) | Set 1 doc expiry_date = today+5d |
| PC-13 | File evidence test (PDF) | Chuẩn bị `evidence-test.pdf` |

### 1.3 Test Data

| Asset | Dept | Trạng thái compliance |
|---|---|---|
| AC-ASSET-TEST-IMM16-001 | ICU | PM compliance 78% (sẽ trigger High finding) |
| AC-ASSET-TEST-IMM16-002 | OR | OK |
| AC-ASSET-TEST-IMM16-003 | CT | Calibration overdue 30d (sẽ trigger Critical) |
| AC-ASSET-TEST-IMM16-004 | ER | OK |
| AC-ASSET-TEST-IMM16-005 | ICU | Doc expired 1d |

---

## 2. Kịch bản kiểm thử

### TC-01: Tạo Compliance Rule (Happy Path)

**Actor:** Tổ HC-QLCL (`test_qlcl`)
**Precondition:** PC-02

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|------|---|---|:---:|
| 1 | Login `test_qlcl` | Đăng nhập thành công | ☐ |
| 2 | Mở `/imm16/rules` | Thấy nút `+ Tạo Rule mới` | ☐ |
| 3 | Click `+ Tạo Rule mới` | Form trống hiện ra | ☐ |
| 4 | Điền `rule_code = "TEST-R-001"` | — | ☐ |
| 5 | Điền `rule_name = "Test rule PM 90"` | — | ☐ |
| 6 | Chọn `source_module = IMM-08` | — | ☐ |
| 7 | Chọn `category = PM`, `severity = High` | — | ☐ |
| 8 | Điền `threshold_definition` JSON `{"metric":"pm_compliance_pct","op":"<","value":90}` | — | ☐ |
| 9 | Chọn `evaluation_frequency = Monthly` | — | ☐ |
| 10 | Click Save | Rule saved, version="1.0", is_active=1 | ☐ |
| 11 | Verify naming `TEST-R-001` | Đúng (autoname theo rule_code) | ☐ |

---

### TC-02: VR-01 — Threshold JSON invalid

**Actor:** Tổ HC-QLCL

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|------|---|---|:---:|
| 1 | Tạo rule với threshold = `{"foo":"bar"}` (thiếu metric/op/value) | Lỗi VR-01 "Threshold rule không hợp lệ. Cần `metric`, `op`, `value`." | ☐ |
| 2 | Sửa thành `{"metric":"x","op":"INVALID","value":1}` | Lỗi VR-01 op không hợp lệ | ☐ |
| 3 | Sửa thành hợp lệ | Save thành công | ☐ |

---

### TC-03: Auto-detect Finding qua Scheduler (Idempotent)

**Actor:** System (scheduler)
**Precondition:** TC-01 passed (rule active), PC-11 (PM compliance ICU = 78%)

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|------|---|---|:---:|
| 1 | Chạy `bench execute assetcore.tasks.run_compliance_evaluation_monthly` | — | ☐ |
| 2 | Mở `/imm16/findings` filter rule=TEST-R-001 | Có 1 finding mới | ☐ |
| 3 | Verify `severity=High`, `current_value=78`, `threshold_value=90` | Đúng | ☐ |
| 4 | Verify `status=Open`, `responsible_dept=ICU` | Đúng | ☐ |
| 5 | Chạy lại scheduler cùng ngày | KHÔNG tạo bản ghi mới (idempotent — UNIQUE INDEX) | ☐ |
| 6 | Verify count Finding cho rule này = 1 | Đúng | ☐ |

---

### TC-04: Confirm NC & Open CAPA

**Actor:** Tổ HC-QLCL → tạo CAPA

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|------|---|---|:---:|
| 1 | Mở finding TC-03 | Hiện nút [Confirm NC] [Mark FP] | ☐ |
| 2 | Click [Confirm NC] | status → Confirmed NC, reviewer set, review_date=now | ☐ |
| 3 | Click [Open CAPA] | Modal create CAPA hiện ra với source=Finding pre-fill | ☐ |
| 4 | Điền problem_statement, risk_level=High, action_owner=test_wshead | — | ☐ |
| 5 | Submit | CAPA tạo (status=Draft), finding.capa_ref set | ☐ |
| 6 | Verify naming `CAPA-2026-####` | Đúng | ☐ |

---

### TC-05: CAPA Lifecycle Happy Path

**Actor:** test_wshead (action owner) → test_qlcl (verify)

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|------|---|---|:---:|
| 1 | Advance Draft → Investigating | OK | ☐ |
| 2 | Advance to Action Plan THIẾU root_cause_method | VR-05 throw "Phải chọn phương pháp..." | ☐ |
| 3 | Chọn root_cause_method=5-Why, điền analysis | — | ☐ |
| 4 | Đặt due_date = ngày trong quá khứ | VR-12 throw "Hạn hoàn thành phải sau hôm nay" | ☐ |
| 5 | Đặt due_date = today+30 | OK | ☐ |
| 6 | Advance to Action Plan | status → Action Plan | ☐ |
| 7 | Thêm 3 action_steps với owner + planned_date | — | ☐ |
| 8 | Advance to Implementation | OK | ☐ |
| 9 | Mark all steps status=Done | — | ☐ |
| 10 | Advance to Verification | OK | ☐ |
| 11 | Cố Advance to Closed mà chưa effectiveness check | VR-06 throw | ☐ |
| 12 | Click [Effectiveness Check] modal, chọn "Effective", upload evidence | — | ☐ |
| 13 | Verify CAPA status → Closed | Đúng | ☐ |
| 14 | Verify Finding linked → status=Resolved | Đúng (auto cascade) | ☐ |

---

### TC-06: CAPA Re-open (Not Effective)

**Actor:** test_qlcl
**Precondition:** TC-05 mở variant — CAPA ở Verification

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|------|---|---|:---:|
| 1 | Click Effectiveness Check, chọn "Not Effective" + evidence | — | ☐ |
| 2 | Verify CAPA status → Re-opened → Investigating | Đúng | ☐ |
| 3 | Verify `reopen_count = 1` | Đúng | ☐ |
| 4 | Cố advance trực tiếp Verification → Closed | VR-07 throw "Không thể Close khi effectiveness chưa Effective" (BR-16-03) | ☐ |
| 5 | Thêm action_step mới, hoàn thành, làm lại verification | — | ☐ |
| 6 | Effectiveness="Effective" | CAPA → Closed | ☐ |

---

### TC-07: Waive Finding (BR-16-06)

**Actor:** test_vp2 (VP Block2) — chỉ VP được waive

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|------|---|---|:---:|
| 1 | (test_qlcl) Mở finding "Under Review" → button [Waive] | Button KHÔNG hiện (role không phải VP) | ☐ |
| 2 | (test_vp2) Mở finding tương tự | Button [Waive] hiện | ☐ |
| 3 | Click [Waive], điền reason 20 chars | VR-04 throw "≥ 50 ký tự" | ☐ |
| 4 | Reason đủ 60 chars, KHÔNG upload evidence | VR-04 throw evidence reqd | ☐ |
| 5 | Đầy đủ + expiry < today | VR-04 throw expiry phải > today | ☐ |
| 6 | Đầy đủ hợp lệ | finding.status → Waived | ☐ |
| 7 | (test_wshead) Cố waive finding khác | response.code = FORBIDDEN | ☐ |

---

### TC-08: Internal Audit Cycle

**Actor:** test_qlcl (lead) → test_auditor → test_vp2 (close)

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|------|---|---|:---:|
| 1 | Tạo audit `audit_code="A-TEST-Q2"`, scope=[IMM-08, IMM-11], depts=[ICU, CT] | status=Planned | ☐ |
| 2 | Verify scheduler check_audit_milestones cảnh báo 7d trước planned_start | Email gửi tới lead_auditor | ☐ |
| 3 | Click [Start Audit] | status → In Progress, actual_start=today | ☐ |
| 4 | (test_auditor) Hoàn thành 5 checklist items: 1 Major NC, 1 Minor NC, 3 Compliant | — | ☐ |
| 5 | Verify: 2 IMM Compliance Finding tự sinh (Major→High, Minor→Medium) | Đúng | ☐ |
| 6 | Verify mỗi item NC có `linked_finding` set | Đúng | ☐ |
| 7 | Cố [Close Audit] mà Major NC chưa link CAPA | VR-08 throw "Còn 1 Major NC chưa mở CAPA" (BR-16-04) | ☐ |
| 8 | Mở CAPA cho Major NC finding | finding.capa_ref set | ☐ |
| 9 | (test_vp2) [Close Audit] với audit_report PDF | status → Closed, actual_end=today | ☐ |

---

### TC-09: Compliance Scorecard sinh + Publish

**Actor:** System → test_vp2

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|------|---|---|:---:|
| 1 | Chạy `bench execute assetcore.tasks.update_compliance_scorecard` (1st of month) | — | ☐ |
| 2 | Mở `/imm16/scorecards` | Có scorecard mới Draft | ☐ |
| 3 | Verify naming `SCR-{YYYY}-{MM}-####` | Đúng | ☐ |
| 4 | Verify `score_pct = (compliant - non_compliant)/total × 100` | Đúng | ☐ |
| 5 | Verify `score_by_module` + `score_by_department` filled | Đúng | ☐ |
| 6 | Verify `trend_vs_prev_month` tính đúng | Đúng | ☐ |
| 7 | (test_qlcl) Cố [Publish] mà role chỉ Tổ QLCL | OK (role có quyền) — verify hành vi | ☐ |
| 8 | Verify quý trước có MR Closed (BR-16-08) → publish OK | is_published=1, published_at set | ☐ |
| 9 | Sau publish, cố sửa score_pct | VR-09 throw "Scorecard đã publish, không thể sửa" | ☐ |
| 10 | Verify [Tạo Restate] button hiện | — | ☐ |

---

### TC-10: Quarterly MR Gate (BR-16-08)

**Actor:** test_vp2
**Precondition:** Xóa/cancel MR quý trước trong test env

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|------|---|---|:---:|
| 1 | Verify quý trước KHÔNG có MR Closed | — | ☐ |
| 2 | Cố [Publish] scorecard tháng đầu quý mới | VR-10 throw "Quý {q} chưa có Management Review" — code MR_MISSING_QUARTERLY | ☐ |
| 3 | Tạo MR quý trước, finalize | status → Closed | ☐ |
| 4 | Quay lại publish scorecard | OK | ☐ |

---

### TC-11: Cross-module Gate (BR-16-09)

**Actor:** test_biomed (gọi từ IMM-08)
**Precondition:** AC-ASSET-TEST-IMM16-003 có CAPA Critical status=Implementation

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|------|---|---|:---:|
| 1 | Gọi API `assetcore.api.imm16.check_asset_compliance_status?asset=AC-ASSET-TEST-IMM16-003` | Response `{blocked: true, reasons:[CAPA_CRITICAL_OPEN]}` | ☐ |
| 2 | Cố Submit IMM-08 PM Work Order trên asset này | Frappe throw "Block: thiết bị có CAPA Critical chưa close (BR-16-09)" | ☐ |
| 3 | Close CAPA (effectiveness Effective) | CAPA → Closed | ☐ |
| 4 | Gọi lại check_asset_compliance_status | Response `{blocked: false}` | ☐ |
| 5 | Submit IMM-08 PM | OK | ☐ |

---

### TC-12: Compliance Heatmap

**Actor:** test_qlcl

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|------|---|---|:---:|
| 1 | Mở `/imm16/heatmap` | Heatmap render module × dept | ☐ |
| 2 | Verify cell màu theo score (≥90 xanh, 80-89 vàng, 70-79 cam, <70 đỏ) | Đúng | ☐ |
| 3 | Hover cell IMM-08 × ICU | Tooltip {module, dept, score, findings_count} | ☐ |
| 4 | Click cell → drill-down | Navigate `/imm16/findings?filters={...}` filtered đúng | ☐ |
| 5 | Verify cell có Critical hiện ★ | Đúng | ☐ |

---

### TC-13: Rule Change Control (BR-16-05, VR-11)

**Actor:** test_qlcl

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|------|---|---|:---:|
| 1 | Mở rule TEST-R-001 | version=1.0 | ☐ |
| 2 | Sửa `severity` từ High → Critical, KHÔNG điền change_summary | VR-11 throw "Thay đổi rule yêu cầu Tóm tắt thay đổi" | ☐ |
| 3 | Điền change_summary "Tăng severity do tăng yêu cầu compliance" | — | ☐ |
| 4 | Save | version → 1.1, previous_version="1.0" | ☐ |
| 5 | Verify Frappe Version có entry | Đúng | ☐ |

---

### TC-14: CAPA Escalation Matrix (BR-16-02)

**Actor:** System

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|------|---|---|:---:|
| 1 | Tạo CAPA Critical, due_date = today - 8 (đã quá hạn 8 ngày) | — | ☐ |
| 2 | Chạy `bench execute assetcore.tasks.check_capa_due` | — | ☐ |
| 3 | Verify email gửi tới: action_owner + Workshop Head + VP Block2 + Trưởng phòng | Đúng (level L3) | ☐ |
| 4 | Chạy lại cùng ngày | KHÔNG gửi email trùng (idempotent escalation log) | ☐ |
| 5 | Sang ngày sau, chạy lại | Email tiếp tục theo cadence | ☐ |

---

### TC-15: Permission Matrix

**Mục đích:** Xác nhận RBAC IMM-16

| Action | qlcl | auditor | wshead | biomed | vp2 | tp | admin |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Create Rule | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ |
| Confirm NC | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✓ |
| Waive Finding | ✗ | ✗ | ✗ | ✗ | ✓ | ✗ | ✓ |
| Create Audit | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ |
| Close Audit | ✓ | ✗ | ✗ | ✗ | ✓ | ✗ | ✓ |
| Create CAPA | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ |
| Effectiveness Check | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ |
| Re-open CAPA | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ |
| Publish Scorecard | ✓ | ✗ | ✗ | ✗ | ✓ | ✗ | ✓ |
| Finalize MR | ✗ | ✗ | ✗ | ✗ | ✓ | ✗ | ✓ |

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|------|---|---|:---:|
| 1 | (auditor) Try Create Rule | response.code=FORBIDDEN | ☐ |
| 2 | (wshead) Try Waive Finding | response.code=FORBIDDEN | ☐ |
| 3 | (vp2) Waive OK | OK | ☐ |
| 4 | (biomed) Try Effectiveness Check | response.code=FORBIDDEN | ☐ |
| 5 | (qlcl) Effectiveness Check OK | OK | ☐ |
| 6 | (tp) Create CAPA OK | OK (action owner cấp khoa) | ☐ |
| 7 | (qlcl) Try Finalize MR | response.code=FORBIDDEN (chỉ VP2) | ☐ |

---

### TC-16: Audit Trail (BR-16-10)

**Mục đích:** Xác nhận audit trail bắt buộc

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|------|---|---|:---:|
| 1 | Tạo Finding manual | Frappe Version ghi "Created" | ☐ |
| 2 | Confirm NC | Version: status Open→Confirmed NC + reviewer set | ☐ |
| 3 | Tạo CAPA, advance state qua từng giai đoạn | Mỗi advance ghi version mới | ☐ |
| 4 | Effectiveness check | Version ghi effectiveness_result + actor | ☐ |
| 5 | Close CAPA | Version ghi status Verification→Closed | ☐ |
| 6 | Mở Activity tab | Timeline đầy đủ | ☐ |
| 7 | Mọi entry có actor + timestamp | Đúng | ☐ |

---

### TC-17: Scorecard Restate

**Actor:** test_qlcl

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|------|---|---|:---:|
| 1 | Mở scorecard đã publish | Read-only mode | ☐ |
| 2 | Click [Tạo Restate] | Scorecard mới tạo với `restate_of` link | ☐ |
| 3 | Verify Scorecard mới `is_published=0`, có thể edit | Đúng | ☐ |
| 4 | Sửa, sign-off, publish | OK; bản cũ vẫn tồn tại immutable | ☐ |

---

### TC-18: API Endpoints

**Mục đích:** Test các endpoint chính

| # | Endpoint | Method | Test | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|---|:---:|
| 1 | `list_rules` | GET | No filter | Paginated list | ☐ |
| 2 | `create_rule` | POST | Valid | Trả `{name,version:"1.0"}` | ☐ |
| 3 | `update_rule` | POST | Threshold change w/o change_summary | RULE_CHANGE_CONTROL | ☐ |
| 4 | `list_findings` | GET | filter status=Open | Đúng | ☐ |
| 5 | `confirm_finding` | POST | state=Open | INVALID_STATE (chỉ Under Review) | ☐ |
| 6 | `waive_finding` | POST | role=wshead | FORBIDDEN | ☐ |
| 7 | `link_to_capa` | POST | Valid | Trả `{finding_name,capa_name}` | ☐ |
| 8 | `create_audit` | POST | Valid | status=Planned | ☐ |
| 9 | `close_audit` | POST | Major NC chưa CAPA | CAPA_LINK_REQUIRED | ☐ |
| 10 | `advance_capa_state` | POST | Closed mà eff=Not Effective | EFFECTIVENESS_REQUIRED / VR-07 | ☐ |
| 11 | `publish_scorecard` | POST | Quý thiếu MR | MR_MISSING_QUARTERLY | ☐ |
| 12 | `check_asset_compliance_status` | GET | Asset có CAPA Crit Open | `{blocked:true}` | ☐ |
| 13 | `get_compliance_heatmap` | GET | period 2026-04 | Matrix module×dept | ☐ |
| 14 | `get_capa_aging` | GET | — | Bucket counts | ☐ |
| 15 | `get_dashboard_stats` | GET | — | KPIs đầy đủ | ☐ |

---

## 3. Test Sign-off

| Nhóm | Tổng TC | Pass | Fail | Block | Tester | Ngày |
|---|:---:|:---:|:---:|:---:|---|---|
| Rule Management | TC-01, TC-02, TC-13 | — | — | — | | |
| Finding Lifecycle | TC-03, TC-04, TC-07 | — | — | — | | |
| CAPA Lifecycle | TC-05, TC-06, TC-14 | — | — | — | | |
| Audit | TC-08 | — | — | — | | |
| Scorecard & MR | TC-09, TC-10, TC-17 | — | — | — | | |
| Cross-module Gate | TC-11 | — | — | — | | |
| Heatmap | TC-12 | — | — | — | | |
| Permission | TC-15 | — | — | — | | |
| Audit Trail | TC-16 | — | — | — | | |
| API | TC-18 | — | — | — | | |
| **TỔNG** | **18** | — | — | — | | |

### Sign-off Criteria

- **Pass:** 100% TC Pass (0 Fail, 0 Block)
- **Conditional Pass:** ≥ 90% Pass, Fail items đều P2 (cosmetic), có remediation plan
- **Fail:** Bất kỳ P0/P1 Fail (gate logic, audit trail, scorecard immutability) → block release

### Approvers

| Role | Tên | Chữ ký | Ngày |
|---|---|---|---|
| BA Lead | | | |
| Dev Lead | | | |
| QA Lead | | | |
| Tổ HC-QLCL Lead | | | |
| VP Block2 | | | |
