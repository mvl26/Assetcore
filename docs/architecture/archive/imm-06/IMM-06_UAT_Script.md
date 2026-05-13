# IMM-06 UAT Script

**Module:** IMM-06 — User Training & Competency Management
**Version:** 0.1.0 (Wave 2 — DRAFT)
**Ngày:** 2026-05-04
**Trạng thái:** PLANNED — chờ implement và phê duyệt

---

## 1. Tổng quan

### 1.1 Mục tiêu UAT

Xác nhận module IMM-06 hoạt động đúng theo Functional Spec, bao gồm:

- Curriculum master (Training Program) CRUD + change control (BR-06-04)
- Session lifecycle: Planned → Confirmed → In Progress → Completed → Verified → Closed
- Auto-create Competency từ Session.complete + Pending Assessment workflow
- Supervisor sign-off → Active
- Scheduler expiry alert 90/60/30 + auto-expire
- Recertification flow
- Revoke + CAPA gate (VR-08)
- Cross-module gates: IMM-04 Clinical_Release coverage + IMM-08/09/12 authorization
- Self-service portal
- Dashboard KPIs + Gap Report
- Permission matrix
- Audit trail

### 1.2 Preconditions

| # | Điều kiện | Cách chuẩn bị |
|---|---|---|
| PC-01 | App `assetcore` đã cài + module IMM-06 đã migrate | `bench --site test install-app assetcore` + `bench migrate` |
| PC-02 | 5 test users với role chuẩn | Tạo: `test_optr@`, `test_biomed@`, `test_qlcl@`, `test_workshop@`, `test_deptmgr@`, `test_clinhead@`, `test_admin@` |
| PC-03 | 2 IMM Device Model đã có | `MDL-MON-PHILIPS-X3` (Class III), `MDL-INFUSION-BBRAUN` (Class II) |
| PC-04 | 3 AC Asset đã commission, đặt tại 2 khoa | `AC-ASSET-TEST-001` ICU, `AC-ASSET-TEST-002` ICU, `AC-ASSET-TEST-003` ER |
| PC-05 | AC Department ICU, ER tồn tại | Seed |
| PC-06 | Workflow IMM-06 Session + Competency đã active | Verify via Setup > Workflow |
| PC-07 | Scheduler enabled | `bench enable-scheduler` |
| PC-08 | Email outbound disable hoặc trỏ MailHog | Tránh spam — config `mail_server` |
| PC-09 | CAPA DocType (mock) tồn tại | Stub `CAPA-2026-0001` |

### 1.3 Test Data

| Object | Value |
|---|---|
| Program A | `TRN-MON-INIT-01` Initial · MDL-MON-PHILIPS-X3 · 24 tháng · Pass 70% · Both |
| Program B | `TRN-INF-INIT-01` Initial · MDL-INFUSION-BBRAUN · 24 tháng · Pass 70% · Both |
| Program C | `TRN-MON-REF-01` Refresher · MDL-MON-PHILIPS-X3 · 12 tháng · Pass 70% · Practical |

---

## 2. Kịch bản kiểm thử

### TC-06-001: Tạo Training Program (Happy Path)

**Actor:** Tổ HC-QLCL (`test_qlcl`)
**Precondition:** PC-01, PC-02, PC-03

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|:---:|
| 1 | Login `test_qlcl` | Đăng nhập thành công | ☐ |
| 2 | Mở `/imm06/programs/new` | Form trống hiện ra | ☐ |
| 3 | Điền program_code = `TRN-MON-INIT-01` | — | ☐ |
| 4 | Điền program_name = "Đào tạo Monitor Philips X3 cơ bản" | — | ☐ |
| 5 | Chọn target_device_model = MDL-MON-PHILIPS-X3 | — | ☐ |
| 6 | Chọn training_type = Initial, duration = 8h, validity = 24 tháng | — | ☐ |
| 7 | Chọn assessment_method = Both, passing_score = 70 | — | ☐ |
| 8 | Click [Lưu] | Program saved, is_active=1 | ☐ |
| 9 | Verify name = `TRN-MON-INIT-01` (autoname theo field) | Đúng | ☐ |
| 10 | Verify list_programs trả program mới | Có | ☐ |

---

### TC-06-002: Validation Rules — Program

**Actor:** Tổ HC-QLCL

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|:---:|
| **VR-02** | | | |
| 1 | Tạo program với passing_score = 0 | Lỗi: "VR-02: Điểm đạt phải trong khoảng 1-100." | ☐ |
| 2 | Tạo program với passing_score = 150 | Lỗi VR-02 | ☐ |
| **VR-03** | | | |
| 3 | Tạo program với validity_period_months = 0 | Lỗi: "VR-03: Hiệu lực phải trong khoảng 1-60 tháng." | ☐ |
| 4 | Tạo program với validity = 120 | Lỗi VR-03 | ☐ |
| **VR-11** | | | |
| 5 | Tạo program với target_device_model không tồn tại | Lỗi: "VR-11: Model thiết bị không hợp lệ..." | ☐ |
| 6 | Tạo program với device_model is_active=0 | Lỗi VR-11 | ☐ |

---

### TC-06-003: Schedule Training Session

**Actor:** Tổ HC-QLCL
**Precondition:** TC-06-001 passed

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|:---:|
| 1 | Mở `/imm06/sessions/new` | Form trống | ☐ |
| 2 | Chọn training_program = TRN-MON-INIT-01 | Auto-fetch validity, passing_score, etc | ☐ |
| 3 | Điền session_date = today + 14 days | — | ☐ |
| 4 | Chọn session_type = Onsite, location = "Phòng F3" | — | ☐ |
| 5 | Chọn instructor = test_biomed | — | ☐ |
| 6 | Add 5 participants (test_optr, test_optr2, ..., test_optr5) | Table có 5 rows | ☐ |
| 7 | Click [Lưu Draft] | Session saved, state = Planned | ☐ |
| 8 | Verify name match `^TRN-2026-\d{4}$` | Đúng | ☐ |
| 9 | Verify email reminder gửi cho 5 participants | Inbox MailHog có 5 emails | ☐ |

---

### TC-06-004: VR-04 Instructor Qualification

**Actor:** Tổ HC-QLCL

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|:---:|
| 1 | Tạo Program với `instructor_qualification_required = "Biomed Engineer"` | — | ☐ |
| 2 | Tạo Session với instructor = test_optr (chỉ có role HTM Technician) | Lỗi: "VR-04: Giảng viên không đủ điều kiện..." | ☐ |
| 3 | Đổi instructor = test_biomed | Pass | ☐ |
| 4 | Hoặc dùng instructor_external_name = "Dr. X" | Pass (external bypass role check) | ☐ |

---

### TC-06-005: VR-05 Min Participants Confirm

**Actor:** Tổ HC-QLCL

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|:---:|
| 1 | Tạo session với 0 participants | Save Draft OK | ☐ |
| 2 | Action [Xác nhận] | Lỗi: "VR-05: Phải có ít nhất 1 học viên..." | ☐ |
| 3 | Add 1 participant, action [Xác nhận] | Pass, state → Confirmed | ☐ |

---

### TC-06-006: Session Workflow Transitions

**Actor:** Tổ HC-QLCL → Biomed (instructor) → Workshop Head
**Precondition:** TC-06-003 passed

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|:---:|
| 1 | (test_qlcl) Action [Xác nhận] | state → Confirmed | ☐ |
| 2 | Verify email notification gửi participants | OK | ☐ |
| 3 | Login test_biomed (instructor) | — | ☐ |
| 4 | Action [Bắt đầu] | state → In Progress | ☐ |
| 5 | Verify nút [Vào Run Mode] hiện | OK | ☐ |
| 6 | (test_qlcl) Action [Verify] khi state = Completed | (test sau bước Complete) | ☐ |

---

### TC-06-007: Complete Session — Auto-create Competency

**Actor:** Biomed (instructor)
**Precondition:** TC-06-006, session state = In Progress, 5 participants

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|:---:|
| 1 | Mở Run Mode | Bảng 5 participants hiện | ☐ |
| 2 | Điền cho participant 1: att=100, theory=85, practical=80 | Auto-compute Result = Pass | ☐ |
| 3 | Điền p2: att=90, theory=75, practical=82 | Pass | ☐ |
| 4 | Điền p3: att=60, theory=80, practical=70 | Fail (att<80%) | ☐ |
| 5 | Điền p4: att=85, theory=68, practical=72 | Pass (avg 70) | ☐ |
| 6 | Điền p5: att=90, theory=50, practical=80 | Fail (avg 65) | ☐ |
| 7 | Click [Hoàn thành buổi học] | session state → Completed | ☐ |
| 8 | Verify response: pass=3, fail=2 | Đúng | ☐ |
| 9 | Verify 3 IMM User Competency tự sinh, status=Pending Assessment | Đúng | ☐ |
| 10 | Verify mỗi competency có training_session, training_program, achieved_date đúng | Đúng | ☐ |
| 11 | Verify email gửi supervisor (Department Manager) | OK | ☐ |

---

### TC-06-008: VR-06 Scores Required khi Complete

**Actor:** Biomed (instructor)
**Precondition:** Session In Progress, program.assessment_method = Both

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|:---:|
| 1 | Click [Hoàn thành] mà không nhập practical_score cho 1 participant | Lỗi: "VR-06: Vui lòng nhập điểm lý thuyết và thực hành." | ☐ |
| 2 | Điền đầy đủ, complete | Pass | ☐ |

---

### TC-06-009: Sign-off Competency

**Actor:** Department Manager (`test_deptmgr` ICU)
**Precondition:** TC-06-007 — 3 Pending Assessment competency

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|:---:|
| 1 | Login test_deptmgr | — | ☐ |
| 2 | Mở `/imm06/competencies` filter status=Pending Assessment | Thấy 3 records của khoa ICU | ☐ |
| 3 | Mở competency của test_optr1 | Hiện nút [Sign-off] | ☐ |
| 4 | Click [Sign-off] → modal | Modal hiện info đầy đủ | ☐ |
| 5 | Confirm | state → Active | ☐ |
| 6 | Verify supervisor_signoff = test_deptmgr | Đúng | ☐ |
| 7 | Verify expiry_date = achieved_date + 24 tháng | Đúng | ☐ |
| 8 | Verify recertification_due_date = expiry_date - 60d | Đúng | ☐ |
| 9 | Verify email gửi user "Đã được cấp năng lực..." | OK | ☐ |
| 10 | Verify scope: thử sign-off competency của user khoa ER | Lỗi FORBIDDEN | ☐ |

---

### TC-06-010: VR-07 Sign-off Required

**Actor:** Tổ HC-QLCL

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|:---:|
| 1 | Try chuyển competency Pending Assessment → Active mà không qua sign-off API | Lỗi: "VR-07: Cần chữ ký của cán bộ giám sát..." | ☐ |
| 2 | Qua signoff_competency API | Pass | ☐ |

---

### TC-06-011: Authorization Gate (IMM-08 hook)

**Actor:** System (IMM-08 controller mock)
**Precondition:** test_optr1 có Active competency cho MDL-MON-PHILIPS-X3

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|:---:|
| 1 | GET `check_user_authorization?user=test_optr1&device_model=MDL-MON-PHILIPS-X3` | authorized=true | ☐ |
| 2 | GET với user=test_optr2 (không có competency) | authorized=false, reason "chưa có Active competency" | ☐ |
| 3 | Manually set competency status=Expired, retry | authorized=false, reason "Năng lực đã hết hạn..." | ☐ |
| 4 | Verify cache: gọi 2 lần liên tiếp → second call < 50ms (từ cache) | OK | ☐ |
| 5 | Update competency status → Active again, retry | Cache invalidated, authorized=true | ☐ |

---

### TC-06-012: Operator Coverage Gate (IMM-04 hook)

**Actor:** System
**Precondition:** AC-ASSET-TEST-001 Class III, ICU; có 1 user Active competency tại ICU

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|:---:|
| 1 | GET `get_asset_operator_coverage?asset=AC-ASSET-TEST-001` | operator_count=1, required_min=2, gate_pass=false | ☐ |
| 2 | Sign-off thêm 1 user Active tại ICU cho cùng device_model | — | ☐ |
| 3 | Retry GET coverage | operator_count=2, gate_pass=true | ☐ |
| 4 | Test với asset Class II: required_min=1 | gate_pass=true với coverage=1 | ☐ |
| 5 | IMM-04 Clinical_Release submit khi coverage thiếu | Block với error "BR-06-07..." | ☐ |

---

### TC-06-013: Scheduler — Expiry Alert

**Actor:** System
**Precondition:** 1 Active competency với expiry_date được set bằng các mốc

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|:---:|
| 1 | Set expiry_date = today + 90 ngày | — | ☐ |
| 2 | `bench execute assetcore.tasks.check_competency_expiry` | — | ☐ |
| 3 | Verify status → Expiring | Đúng | ☐ |
| 4 | Verify IMM Competency Alert Log có record (milestone=90, alert_level=Info) | Đúng | ☐ |
| 5 | Run lần 2 cùng ngày | KHÔNG tạo duplicate (idempotent) | ☐ |
| 6 | Set expiry_date = today + 30 ngày, run | Alert milestone=30, alert_level=Critical | ☐ |
| 7 | Verify email user + supervisor + Workshop Head | OK | ☐ |

---

### TC-06-014: Scheduler — Auto Expire

**Actor:** System
**Precondition:** 1 Active competency expiry_date < today

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|:---:|
| 1 | `bench execute assetcore.tasks.auto_expire_competency` | — | ☐ |
| 2 | Verify status → Expired | Đúng | ☐ |
| 3 | Verify authorization cache invalidated | check_user_authorization trả false | ☐ |
| 4 | Verify email user + Workshop Head | OK | ☐ |
| 5 | Verify IMM Audit Trail log "AUTO_EXPIRE" | OK | ☐ |

---

### TC-06-015: Scheduler — Recertification Due

**Actor:** System
**Precondition:** 1 Active competency với recertification_due_date = today

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|:---:|
| 1 | `bench execute assetcore.tasks.check_recertification_due` | — | ☐ |
| 2 | Verify Refresher Session Planned tự tạo cho program/user | Có | ☐ |
| 3 | Verify user đã được add vào participants | Có | ☐ |
| 4 | Verify email digest gửi Tổ HC-QLCL | OK | ☐ |
| 5 | Run lần 2 — không tạo duplicate session | OK (idempotent) | ☐ |

---

### TC-06-016: Scheduler — Gap Report Weekly

**Actor:** System

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|:---:|
| 1 | `bench execute assetcore.tasks.generate_competency_gap_report` | — | ☐ |
| 2 | Verify IMM Competency Gap Report tạo mới | Đúng | ☐ |
| 3 | Verify gap_details JSON có data | Đúng | ☐ |
| 4 | Mở dashboard `get_competency_gaps_by_dept` | Số liệu match report | ☐ |
| 5 | Verify email Workshop Head + VP Block2 | OK | ☐ |

---

### TC-06-017: Revoke Competency (Happy Path)

**Actor:** Tổ HC-QLCL
**Precondition:** test_optr1 có Active competency + có Open WO assigned

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|:---:|
| 1 | Mở competency detail | Hiện nút [Thu hồi] | ☐ |
| 2 | Click [Thu hồi] → modal | Modal hiện | ☐ |
| 3 | Điền reason = "Vi phạm quy trình vận hành thiết bị" (không chứa "incident") | CAPA field optional | ☐ |
| 4 | Confirm | status → Revoked | ☐ |
| 5 | Verify revoked_by, revoked_date set | Đúng | ☐ |
| 6 | Verify IMM Audit Trail log "REVOKE" | OK | ☐ |
| 7 | Verify cache invalidated | check_user_authorization → false | ☐ |
| 8 | Verify response.flagged_work_orders | Có WO đang assign | ☐ |
| 9 | Verify email Workshop Head | OK | ☐ |

---

### TC-06-018: VR-08 Revoke + CAPA

**Actor:** Tổ HC-QLCL

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|:---:|
| 1 | Revoke với reason chứa "sự cố vận hành" | UI: nút disabled cho đến khi điền CAPA | ☐ |
| 2 | API call without revoke_capa_ref | Lỗi: "VR-08: Thu hồi do sự cố vận hành phải có CAPA reference." | ☐ |
| 3 | Điền revoke_capa_ref = CAPA-2026-0001 | Pass | ☐ |
| 4 | Test keyword khác: "incident", "tai nạn", "sai phạm" | Đều trigger VR-08 | ☐ |

---

### TC-06-019: BR-06-04 Program Update Trigger Recert

**Actor:** Tổ HC-QLCL
**Precondition:** Program TRN-MON-INIT-01 có 5 user Active competency

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|:---:|
| 1 | Mở Program detail, sửa `passing_score_pct` từ 70 → 75 | Banner cảnh báo "5 user sẽ cần re-cert" | ☐ |
| 2 | Click [Lưu và Trigger Recert] | Save thành công | ☐ |
| 3 | Verify response.recert_triggered = true, affected_competencies_count = 5 | Đúng | ☐ |
| 4 | Verify task/Document Request tạo cho Tổ HC-QLCL | OK | ☐ |
| 5 | Sửa chỉ description (non-critical) | Không trigger recert | ☐ |

---

### TC-06-020: Self-service Portal

**Actor:** Operator (`test_optr1`)

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|:---:|
| 1 | Login test_optr1 | — | ☐ |
| 2 | Mở `/me/competencies` | Hiện list competency của chính mình | ☐ |
| 3 | Verify chỉ thấy own (không thấy competency của test_optr2) | OK | ☐ |
| 4 | Click "Xem chứng nhận PDF" | Mở/download PDF | ☐ |
| 5 | Try GET `get_user_competencies?user=test_optr2` | Lỗi FORBIDDEN | ☐ |
| 6 | Operator KHÔNG thấy nút [Sign-off] / [Revoke] / Tab Dashboard | OK | ☐ |
| 7 | Mobile responsive (< 768px): card layout | OK | ☐ |

---

### TC-06-021: Dashboard KPIs

**Actor:** Workshop Head

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|:---:|
| 1 | Mở `/imm06/dashboard` | Dashboard load | ☐ |
| 2 | Verify 7 KPI cards hiển thị đúng số liệu | Match query SQL | ☐ |
| 3 | Click card "Expiring 90d" | Navigate filter list | ☐ |
| 4 | Verify Gap Matrix khoa × class | Render đúng | ☐ |
| 5 | Click cell ICU × Class III gap | Mở list assets vi phạm | ☐ |
| 6 | Verify realtime: trigger session.complete khác → KPI cập nhật mà không reload | OK | ☐ |

---

### TC-06-022: Permission Matrix

**Mục đích:** RBAC theo bảng matrix Functional Spec §5

| Role | Action | Expected | Pass/Fail |
|---|---|:---:|:---:|
| Operator | Create Program | ❌ FORBIDDEN | ☐ |
| Operator | Read own competency | ✅ | ☐ |
| Operator | Read other user competency | ❌ | ☐ |
| HTM Technician | Create Session | ✅ | ☐ |
| HTM Technician | Confirm Session | ❌ | ☐ |
| Biomed | Complete Session (instructor) | ✅ | ☐ |
| Biomed | Sign-off Competency | ❌ | ☐ |
| Tổ HC-QLCL | Create Program | ✅ | ☐ |
| Tổ HC-QLCL | Revoke Competency | ✅ | ☐ |
| Workshop Head | Verify Session | ✅ | ☐ |
| Workshop Head | Sign-off Competency | ✅ | ☐ |
| Workshop Head | Revoke Competency | ❌ (chỉ Tổ HC-QLCL/Admin) | ☐ |
| Department Manager | Sign-off Competency (own dept) | ✅ | ☐ |
| Department Manager | Sign-off Competency (other dept) | ❌ | ☐ |
| Clinical Head | Read dept competency | ✅ | ☐ |
| Clinical Head | Sign-off Competency (own dept) | ✅ | ☐ |
| CMMS Admin | Tất cả actions | ✅ | ☐ |

---

### TC-06-023: Delete Prevention (BR-06-09)

**Actor:** CMMS Admin

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|:---:|
| 1 | Try delete IMM User Competency Active | Lỗi: "BR-06-09: Không được phép xóa Competency..." | ☐ |
| 2 | Try delete competency Expired/Revoked | Lỗi BR-06-09 | ☐ |
| 3 | API `frappe.delete_doc("IMM User Competency", name)` | Lỗi on_trash block | ☐ |
| 4 | Verify record vẫn tồn tại sau attempt | OK | ☐ |

---

### TC-06-024: Audit Trail

**Mục đích:** Mọi action có log

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|:---:|
| 1 | Tạo Program → save | Frappe Version ghi "Created" | ☐ |
| 2 | Sign-off competency | Version + IMM Audit Trail "SIGNOFF" | ☐ |
| 3 | Revoke competency | IMM Audit Trail "REVOKE" với metadata reason+CAPA | ☐ |
| 4 | Auto-expire (scheduler) | Audit Trail "AUTO_EXPIRE" | ☐ |
| 5 | Suspend → Resume | Audit Trail 2 actions | ☐ |
| 6 | Mở tab Activity / History trên form | Timeline đầy đủ events | ☐ |

---

### TC-06-025: API Endpoints (Regression)

| # | Endpoint | Method | Test | Expected | Pass/Fail |
|---|---|---|---|---|:---:|
| 1 | list_programs | GET | No filters | Paginated | ☐ |
| 2 | get_program | GET | name=TRN-MON-INIT-01 | Full object | ☐ |
| 3 | get_program | GET | name=INVALID | NOT_FOUND | ☐ |
| 4 | create_program | POST | Valid data | name returned | ☐ |
| 5 | update_program | POST | Critical field changed | recert_triggered=true | ☐ |
| 6 | list_sessions | GET | filter date range | Filtered list | ☐ |
| 7 | confirm_session | POST | 0 participants | VR-05 error | ☐ |
| 8 | complete_session | POST | Missing scores | VR-06 error | ☐ |
| 9 | complete_session | POST | Valid | competencies_created list | ☐ |
| 10 | cancel_session | POST | state=Verified | INVALID_STATE error | ☐ |
| 11 | list_competencies | GET | as Operator | Only own | ☐ |
| 12 | get_user_competencies | GET | self | Own list | ☐ |
| 13 | get_asset_operator_coverage | GET | Class III asset | gate_pass logic | ☐ |
| 14 | get_competency_gaps_by_dept | GET | — | Matrix data | ☐ |
| 15 | get_expiring_competencies | GET | days=90 | Filtered | ☐ |
| 16 | revoke_competency | POST | No reason | VALIDATION_ERROR | ☐ |
| 17 | revoke_competency | POST | reason "incident" no CAPA | VR-08 error | ☐ |
| 18 | recertify_competency | POST | Valid | new_session created | ☐ |
| 19 | signoff_competency | POST | Wrong dept supervisor | FORBIDDEN | ☐ |
| 20 | check_user_authorization | GET | Active user | authorized=true | ☐ |
| 21 | check_user_authorization | GET | Expired user | authorized=false | ☐ |
| 22 | get_dashboard_stats | GET | — | KPIs object | ☐ |

---

## 3. Regression Matrix

| Functional Area | Test Cases | Critical for release |
|---|---|:---:|
| Program CRUD | TC-06-001, TC-06-002 | ✅ |
| Session lifecycle | TC-06-003, TC-06-006 | ✅ |
| Validation Rules | TC-06-002, TC-06-004, TC-06-005, TC-06-008, TC-06-010, TC-06-018 | ✅ |
| Auto-create Competency | TC-06-007 | ✅ |
| Sign-off | TC-06-009 | ✅ |
| Authorization Gate | TC-06-011 | ✅ (cross-module critical) |
| Coverage Gate (IMM-04) | TC-06-012 | ✅ |
| Schedulers | TC-06-013, TC-06-014, TC-06-015, TC-06-016 | ✅ |
| Revoke + CAPA | TC-06-017, TC-06-018 | ✅ |
| Change Control (BR-06-04) | TC-06-019 | ✅ |
| Self-service | TC-06-020 | ⚠ (P2 — không block release) |
| Dashboard | TC-06-021 | ⚠ |
| Permission | TC-06-022 | ✅ |
| Delete Prevention | TC-06-023 | ✅ |
| Audit Trail | TC-06-024 | ✅ |
| API Regression | TC-06-025 | ✅ |

---

## 4. Test Sign-off

| Nhóm | TC | Pass | Fail | Block | Tester | Ngày |
|---|---|:---:|:---:|:---:|---|---|
| Program CRUD | TC-06-001, 002 | — | — | — | | |
| Session Lifecycle | TC-06-003, 005, 006 | — | — | — | | |
| Validation | TC-06-004, 008, 010, 018 | — | — | — | | |
| Auto-create + Sign-off | TC-06-007, 009 | — | — | — | | |
| Authorization Gate | TC-06-011, 012 | — | — | — | | |
| Schedulers | TC-06-013, 014, 015, 016 | — | — | — | | |
| Revoke + Change Control | TC-06-017, 018, 019 | — | — | — | | |
| Self-service & Dashboard | TC-06-020, 021 | — | — | — | | |
| Permission | TC-06-022 | — | — | — | | |
| Delete + Audit | TC-06-023, 024 | — | — | — | | |
| API | TC-06-025 | — | — | — | | |
| **TỔNG** | **25** | — | — | — | | |

### Sign-off Criteria

- **Pass:** 100% TC critical Pass (0 Fail, 0 Block)
- **Conditional Pass:** ≥ 90% Pass; Fail items đều P2 (Self-service, Dashboard cosmetic), có remediation plan
- **Fail:** Bất kỳ P0/P1 (Authorization Gate, Coverage Gate, Schedulers, Revoke flow) Fail → block release

### Approvers

| Role | Tên | Chữ ký | Ngày |
|---|---|---|---|
| BA Lead | | | |
| Dev Lead | | | |
| QA Lead | | | |
| Tổ HC-QLCL Lead (Module Owner) | | | |
| Workshop Head | | | |
