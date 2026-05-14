# IMM-06 — Kiểm thử & An ninh (Testing, QA & Security)

| Mục | Giá trị |
|---|---|
| Module | **IMM-06 — Đào tạo & Quản lý Năng lực (Training & Competency)** |
| Phiên bản | 1.0.0 |
| Ngày cập nhật | 2026-05-08 |
| Owner | QA Lead + Tech Lead |
| Liên kết | [Module Overview](./IMM-06_Module_Overview.md) · [Functional Specs](./IMM-06_Functional_Specs.md) · [API Interface](./IMM-06_API_Interface.md) |

---

# Phần I — Test Plan

## I.1. Test Pyramid

```
                  ┌────────────┐
                  │  E2E / UAT │  ← Playwright; 1 Golden Scenario (session lifecycle)
                 ─┴────────────┴─
              ┌──────────────────────┐
              │   API Integration    │  ← pytest + Frappe whitelist (23 endpoints)
             ─┴──────────────────────┴─
          ┌────────────────────────────────┐
          │  Workflow + DocType lifecycle  │  ← pytest FrappeTestCase (Session + Competency)
         ─┴────────────────────────────────┴─
      ┌────────────────────────────────────────────┐
      │         Unit — Service Layer               │  ← TDD; bulk ở đây (services/imm06.py)
     ─┴────────────────────────────────────────────┴─
```

Mọi service function phải có test trước khi code (TDD — CLAUDE.md §17). Mỗi business rule (BR-06-01 → 12) có ≥ 1 happy + 1 negative test.

**Trạng thái thực tế (2026-05-14):**
- ✅ Test scaffold: **một file duy nhất** `assetcore/tests/test_imm06.py` (314 LOC). Các file con (`test_imm06_service.py`, `test_imm06_validators.py`, `test_imm06_doctype.py`, `test_imm06_workflow.py`, `test_imm06_audit.py`, `test_imm06_api.py`, e2e `test_imm06_golden.py`) **chưa được tách** — phần I.2–I.8 dưới đây là **kế hoạch chia file**.
- ✅ API count theo whitelist: **23 endpoints** (cũng cập nhật ở `05_API_Specification.md`).

## I.2. Unit Test — Service Layer

**File:** `assetcore/tests/test_imm06_service.py`

| Test class | Hàm cover | Cases dự kiến |
|---|---|---|
| `TestUserAuthorization` | `check_user_authorization()` | happy(Active), fail(Expired), fail(Revoked), fail(no competency), fail(Suspended) |
| `TestOperatorCoverage` | `get_asset_operator_coverage()` | Class III ≥ 2 → pass, Class III = 1 → fail, Class II = 1 → pass |
| `TestAutoCreateCompetency` | `auto_create_competency_from_session()` | 3 Pass → 3 COMP created, 0 Pass → empty list, Fail row → skip |
| `TestSignoff` | `signoff_competency()` | happy(own dept), fail(wrong dept), fail(already Active), expiry_date computed |
| `TestRevoke` | `revoke_competency()` | happy(no incident), happy(with CAPA), fail(VR-08 missing CAPA), fail(Revoked→Revoked) |
| `TestExpiry` | `check_competency_expiry()` | milestone 90/60/30 set Expiring, idempotent (Alert Log), no duplicate |
| `TestAutoExpire` | `auto_expire_competency()` | past due → Expired, future → skip, cache invalidated |
| `TestRecertDue` | `check_recertification_due()` | 60d → create placeholder session, idempotent (no duplicate), email sent |
| `TestGapReport` | `generate_competency_gap_report()` | weekly creates GAP record, coverage matrix correct |
| `TestProgramUpdate` | `trigger_recertification_on_program_change()` | critical field changed → recert flag, non-critical → skip |
| `TestDeletePrevention` | `on_trash()` | Active/Expired/Revoked → all throw ServiceError |
| `TestBR0611` | `archive_old_competency()` | 2nd Active for same user×model → old archived, new kept |

**Pattern seed:**
```python
class TestUserAuthorization(FrappeTestCase):
    def setUp(self):
        self.asset = make_asset("AC-ASSET-TEST-001", device_model="MDL-MON-PHILIPS-X3")
        self.user = "ktv.test@hospital.vn"
        self.comp = make_competency(user=self.user, device_model="MDL-MON-PHILIPS-X3",
                                    status="Active")

    def test_authorized_when_active(self):
        result = check_user_authorization(self.user, "MDL-MON-PHILIPS-X3")
        self.assertTrue(result["authorized"])

    def test_unauthorized_when_expired(self):
        frappe.db.set_value("IMM User Competency", self.comp.name, "status", "Expired")
        result = check_user_authorization(self.user, "MDL-MON-PHILIPS-X3")
        self.assertFalse(result["authorized"])
        self.assertEqual(result["code"], "NOT_AUTHORIZED")
```

## I.3. Unit Test — Validators & Repository

**File:** `assetcore/tests/test_imm06_validators.py`

| Validator | Happy | Fail |
|---|---|---|
| `_check_expiry_date(doc)` | expiry > achieved → pass | expiry ≤ achieved → VR-01 raise |
| `_check_passing_score(doc)` | 1 ≤ score ≤ 100 → pass | score=0 / score=150 → VR-02 raise |
| `_check_validity_months(doc)` | 1 ≤ months ≤ 60 → pass | months=0 / months=120 → VR-03 raise |
| `_check_instructor_qualification(doc)` | biomed instructor + program needs biomed → pass | operator as instructor → VR-04 raise |
| `_check_min_participants(doc)` | ≥ 1 participant → pass | 0 participants → VR-05 raise |
| `CompetencyRepo.list(filters)` | Paginated results, filter by status | Invalid filter → empty list |
| `CompetencyRepo.get(name)` | Full doc + days_until_expiry | Not found → NOT_FOUND raise |

## I.4. Integration Test — DocType Lifecycle

**File:** `assetcore/tests/test_imm06_doctype.py`

| Test | Setup | Action | Assert |
|---|---|---|---|
| `test_session_before_insert_validates_instructor` | Program needs Biomed, instructor = Operator | `session.insert()` | `ValidationError` VR-04 |
| `test_session_complete_creates_competencies` | Session In Progress, 3 Pass + 2 Fail | `complete_session(name)` | 3 `IMM User Competency` Pending Assessment |
| `test_signoff_sets_expiry_date` | Competency Pending Assessment | `signoff_competency(name)` | `expiry_date = achieved_date + validity_months` |
| `test_competency_on_trash_blocked` | Competency Active | `frappe.delete_doc(...)` | `PermissionError` BR-06-09 |
| `test_program_critical_field_change_triggers_recert` | Program 5 Active users | Update `passing_score_pct` | recert_triggered = True, 5 affected |
| `test_audit_trail_on_revoke` | Competency Active | `revoke_competency(reason)` | `IMM Audit Trail` event type = "REVOKE" |
| `test_br0611_single_active_per_model` | User has 1 Active Competency | New session completed + signoff | Old archived, new Active |

## I.5. Integration Test — Workflow Transitions

**File:** `assetcore/tests/test_imm06_workflow.py`

**Workflow 1 — IMM Training Session** (7 states):

| Transition | From → To | Role required | Test |
|---|---|---|---|
| Xác nhận | Planned → Confirmed | Tổ HC-QLCL | pass + fail(wrong role) + VR-05 no participants |
| Bắt đầu | Confirmed → In Progress | Instructor / Tổ HC-QLCL | pass + fail(Operator as instructor) |
| Hoàn thành | In Progress → Completed | Instructor / Tổ HC-QLCL | pass + fail(missing scores VR-06) |
| Verify | Completed → Verified | Workshop Head | pass + fail(wrong role) |
| Đóng | Verified → Closed | Workshop Head / CMMS Admin | pass (terminal, read-only) |
| Hủy | Planned/Confirmed/In Progress → Cancelled | Tổ HC-QLCL / CMMS Admin | pass + fail(from Verified — BR-06-12) |

**Workflow 2 — IMM User Competency** (6 states):

| Transition | From → To | Trigger | Test |
|---|---|---|---|
| Sign-off | Pending Assessment → Active | Supervisor API | pass + fail(wrong dept supervisor) |
| Auto Expiring | Active → Expiring | Scheduler | milestone 90d pass |
| Auto Expired | Active/Expiring → Expired | Scheduler | past due → Expired |
| Tạm ngưng | Active → Suspended | Workshop Head API | pass + fail(CMMS Admin only for revoke) |
| Thu hồi | Any → Revoked | Tổ HC-QLCL API | pass + VR-08 incident without CAPA |

## I.6. Integration Test — Audit Chain Integrity

**File:** `assetcore/tests/test_imm06_audit.py`

```python
def test_audit_chain_intact_after_competency_lifecycle():
    # Create session → Complete → Signoff → Active → Revoke
    # After each step, assert verify_audit_chain(asset) == True

def test_audit_trail_on_revoke_has_metadata():
    # Revoke competency with reason + CAPA ref
    # Assert IMM Audit Trail record has event_type="REVOKE"
    # Assert metadata contains revoke_reason and revoke_capa_ref

def test_audit_chain_breaks_on_tamper():
    # Insert 1 IMM Audit Trail record
    # Directly modify hash_sha256 in DB
    # Assert verify_audit_chain() == False
```

## I.7. API Test

**File:** `assetcore/tests/test_imm06_api.py`

| Test | Endpoint | Verify |
|---|---|---|
| `test_list_programs_pagination` | `list_programs` | page=1, page_size=20, total ≥ 0 |
| `test_get_program_existing` | `get_program?name=TRN-MON-INIT-01` | `success=true`, fields đầy đủ |
| `test_get_program_not_found` | `get_program?name=FAKE` | `success=false`, `code=NOT_FOUND` |
| `test_create_program_happy` | `create_program` | `success=true`, name = program_code |
| `test_create_program_bad_score` | VR-02: passing_score=0 | `success=false`, `code=VALIDATION` |
| `test_complete_session_auto_competency` | `complete_session` | N Pass → N competency created |
| `test_complete_session_missing_scores` | VR-06: practical_score missing | `code=VALIDATION` |
| `test_signoff_wrong_dept` | `signoff_competency` dept mismatch | `code=FORBIDDEN` |
| `test_check_user_authorization_active` | `check_user_authorization` | `authorized=true` |
| `test_check_user_authorization_expired` | Expired competency | `authorized=false`, reason set |
| `test_revoke_with_incident_no_capa` | `revoke_competency` reason="incident", no CAPA | `code=VALIDATION` VR-08 |
| `test_operator_coverage_class3_insufficient` | `get_asset_operator_coverage` Class III, 1 operator | `gate_pass=false` |
| `test_operator_coverage_class3_sufficient` | Class III, 2 operators | `gate_pass=true` |
| `test_get_dashboard_stats` | `get_dashboard_stats` | KPI fields present |
| `test_list_competencies_as_operator` | `list_competencies` role=Operator | Only own records |
| `test_create_program_no_permission` | role=HTM Technician | HTTP 403 |
| `test_idempotent_complete_session` | complete_session twice | 2nd call → `code=BAD_STATE` |

## I.8. E2E Browser (Playwright)

**File:** `assetcore/tests/e2e/test_imm06_golden.py`

**Golden scenario:** Tổ HC-QLCL tạo Program → Schedule Session → Confirm → In Progress → Chấm điểm 3 Pass + 2 Fail → Complete → Department Manager sign-off → competency Active → Verify `check_user_authorization = true` → Scheduler Expiry Alert → Revoke với CAPA.

Chạy: `pytest assetcore/tests/e2e/ -m imm06 --headed` (staging only).

## I.9. Performance Test

| Metric | Target | Phương pháp |
|---|---|---|
| `list_competencies` p95 (5k records) | ≤ 1.5 s | k6 ramping 20 VU |
| `check_user_authorization` p95 (cached) | ≤ 200 ms | k6 — critical: WO assign hotpath |
| `complete_session` p95 (15 participants) | ≤ 2 s | k6 |
| `get_dashboard_stats` p95 | ≤ 1.2 s | k6 |
| Scheduler `check_competency_expiry` (1000 competencies) | ≤ 60 s | bench execute + timer |
| Scheduler `generate_competency_gap_report` | ≤ 120 s | bench execute + timer |
| Dashboard FE render (gap matrix 10×3) | ≤ 1 s DOMContentLoaded | Lighthouse / Playwright |

## I.10. Test Data

| Loại | Cách seed | File |
|---|---|---|
| IMM Device Model | `tests/fixtures/test_device_models.json` | 2 models (Class II + Class III) |
| IMM Training Program | `tests/fixtures/test_training_programs.json` | 3 programs (Initial, Refresher, Advanced) |
| IMM Training Session | `tests/fixtures/test_training_sessions.json` | 5 sessions với participants |
| IMM User Competency | `tests/fixtures/test_competencies.json` | 10 competencies (Active/Expiring/Expired/Revoked) |
| AC Asset (training context) | `tests/fixtures/test_assets.json` | 4 assets gắn với device models trên |
| UAT full seed | `scripts/uat/uat_imm06.py` | Users + programs + sessions đầy đủ |

Reset script: `bench --site assetcore.local execute assetcore.scripts.uat.uat_imm06.seed_data`

## I.11. Run Commands & Coverage Gate

```bash
# Unit + integration
bench --site assetcore.local run-tests --app assetcore --module assetcore.tests.test_imm06_service
bench --site assetcore.local run-tests --app assetcore --module assetcore.tests.test_imm06_doctype

# Full suite (CI)
bench --site assetcore.local run-tests --app assetcore --coverage

# UAT golden scenario
bench --site uat.assetcore.local execute assetcore.scripts.uat.uat_imm06.run
```

| Layer | Coverage target | Đo |
|---|---|---|
| Service (`services/imm06.py`) | ≥ 85% | `coverage report` |
| DocType lifecycle | ≥ 70% | `coverage report` |
| API (`api/imm06.py`) | ≥ 60% | `coverage report` |
| Frontend (vue-tsc) | Không crash build | CI `npm run build` |

CI fail nếu coverage < target hoặc bất kỳ test nào fail.

## I.12. Đo Chất Lượng Mã Nguồn

| Tool | Mục tiêu | Target | Cadence |
|---|---|---|---|
| **SonarQube** (BE Python) | Bug 0 Critical, code smell ≤ 5, duplication ≤ 3%, coverage ≥ 70%, security hotspot review 100% | Quality Gate pass | Mỗi PR (CI gate) |
| **Lighthouse** (FE — TrainingDashboard) | Performance ≥ 90, Accessibility ≥ 95, Best Practices ≥ 90 | ≥ target | Mỗi release + monthly |
| **ESLint + vue-tsc** | 0 error, 0 warning prod build | pass | Mỗi PR FE (CI gate) |
| **ruff / black** (BE) | 0 error, format chuẩn PEP8 | pass | Mỗi PR (CI gate) |
| **Bundle size** (FE chunk imm06) | main chunk ≤ 250 KB gzip | ≤ budget | Mỗi PR FE (CI report) |

---

# Phần II — UAT Script

## II.1. Phạm vi UAT

**In-scope:**
- Tạo Training Program + change control (BR-06-04)
- Session lifecycle: Planned → Confirmed → In Progress → Completed → Verified → Closed (BR-06-02, BR-06-05)
- Auto-create Competency từ session.complete + sign-off (BR-06-05)
- Scheduler expiry alert 90/60/30 + auto-expire (BR-06-03)
- Authorization gate IMM-08/09/12 (BR-06-01)
- Operator coverage gate IMM-04 Clinical_Release (BR-06-07)
- Revoke + CAPA linkage (BR-06-06)
- Recertification flow (BR-06-03)
- Self-service portal
- Dashboard KPI + Gap Report
- Permission matrix mỗi role
- Audit trail (BR-06-08, BR-06-09)

**Out-of-scope (UAT):** Load testing, penetration testing, LMS content delivery, e-signature số.

**Pre-conditions:**
- UAT site: `uat.assetcore.vn` đã deploy bản mới nhất
- Seed data chạy thành công: `uat_imm06.py seed_data`
- 7 tester accounts tạo (xem §II.2)
- Browser: Chrome ≥ 120 hoặc Edge ≥ 120
- Scheduler enabled + MailHog cho outbound email

## II.2. Tester Accounts

| Username | Email | Role | Vai trò UAT |
|---|---|---|---|
| `qlcl.lead` | qlcl.lead@hospital.vn | Tổ HC-QLCL (Training Officer) | Tạo Program, Schedule Session, Revoke, Change Control |
| `biomed.eng` | biomed.eng@hospital.vn | Biomed Engineer | Instructor, complete session, chấm điểm |
| `ktv.optr1` | ktv.optr1@hospital.vn | HTM Technician / Operator | Tham gia training, xem self-service portal |
| `ktv.optr2` | ktv.optr2@hospital.vn | HTM Technician / Operator | Test concurrent + permission isolation |
| `dept.mgr` | dept.mgr@hospital.vn | Department Manager | Sign-off competency khoa ICU |
| `workshop.head` | workshop.head@hospital.vn | Workshop Head | Verify session, xem gap report, escalation |
| `admin.cms` | admin.cms@hospital.vn | CMMS Admin | Override + full-access test |

Mật khẩu UAT: `Assetcore@2026` (reset sau UAT).

## II.3. Test Data Đã Seed

| DocType | Số lượng | Ghi chú |
|---|---|---|
| IMM Device Model | 2 | `MDL-MON-PHILIPS-X3` (Class III), `MDL-INFUSION-BBRAUN` (Class II) |
| IMM Training Program | 3 | Initial/Refresher/Advanced cho MDL-MON-PHILIPS-X3 |
| IMM Training Session | 2 | 1 Planned (tương lai), 1 Completed (lịch sử) |
| IMM User Competency | 5 | Active ×2, Expiring ×1, Expired ×1, Revoked ×1 |
| AC Asset | 3 | 2 ICU (Class III), 1 ER (Class II) |
| AC Department | 2 | ICU, ER |
| CAPA stub | 1 | `CAPA-2026-0001` (cho VR-08 test) |

## II.4. Test Scenarios

### UAT-IMM06-01 — Tạo Training Program (Happy Path)

**Liên kết:** US-06-01, BR-06-02
**Role tester:** Tổ HC-QLCL
**Mục tiêu:** Tạo Program hợp lệ, kiểm tra naming series và defaults.

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | Đăng nhập `qlcl.lead`, vào `/imm06/programs/new` | Form tạo Program hiển thị | ☐ |
| 2 | Điền program_code = `TRN-MON-INIT-UAT`, program_name, target_device_model = MDL-MON-PHILIPS-X3 | — | ☐ |
| 3 | Chọn training_type = Initial, duration = 8h, validity = 24 tháng | — | ☐ |
| 4 | Chọn assessment_method = Both, passing_score = 70, instructor_qualification = Biomed Engineer | — | ☐ |
| 5 | Bấm "Lưu" | Program saved, name = `TRN-MON-INIT-UAT`, is_active = 1 | ☐ |
| 6 | Kiểm tra `list_programs` | Program mới xuất hiện | ☐ |
| 7 | Thử tạo Program với passing_score = 0 | Lỗi VR-02 "Điểm đạt phải trong khoảng 1-100" | ☐ |

**Acceptance:** Tất cả 7 step Pass.

---

### UAT-IMM06-02 — Session Lifecycle: Planned → Closed (Happy Path)

**Liên kết:** US-06-02, US-06-03, BR-06-02
**Role tester:** Tổ HC-QLCL → Biomed Engineer → Workshop Head
**Mục tiêu:** Workflow session đầy đủ 6 trạng thái.

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | `qlcl.lead` tạo session với Program trên, instructor = `biomed.eng`, 3 participants | Session state = Planned, naming = `TRN-2026-XXXX` | ☐ |
| 2 | Thử Confirm khi 0 participants | Lỗi VR-05 | ☐ |
| 3 | `qlcl.lead` action "Xác nhận" | State → Confirmed, email gửi participants | ☐ |
| 4 | `biomed.eng` action "Bắt đầu" | State → In Progress | ☐ |
| 5 | `biomed.eng` điền điểm cho 3 participants | Pass/Fail tính tự động | ☐ |
| 6 | `biomed.eng` action "Hoàn thành" | State → Completed, N Competency Pending Assessment tạo | ☐ |
| 7 | `workshop.head` action "Verify" | State → Verified | ☐ |
| 8 | `workshop.head` action "Đóng" | State → Closed (read-only) | ☐ |

**Acceptance:** Tất cả 8 step Pass.

---

### UAT-IMM06-03 — Auto-create Competency + Sign-off

**Liên kết:** US-06-04, US-06-05, BR-06-05
**Role tester:** Biomed Engineer → Department Manager
**Mục tiêu:** 3 Pass → 3 Competency Pending Assessment; sign-off → Active, expiry đúng.

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | Session In Progress với 5 participants; điền 3 Pass + 2 Fail | Pass/Fail computed | ☐ |
| 2 | Action Hoàn thành | 3 IMM User Competency Pending Assessment tạo | ☐ |
| 3 | `dept.mgr` mở Competency của `ktv.optr1` | Nút "Sign-off" khả dụng | ☐ |
| 4 | Sign-off | State → Active; `supervisor_signoff`, `signoff_date` set | ☐ |
| 5 | Verify `expiry_date = achieved_date + 24 months` | Đúng theo VR-01 | ☐ |
| 6 | `dept.mgr` thử sign-off competency khoa ER | Lỗi FORBIDDEN (sai dept) | ☐ |
| 7 | Email gửi `ktv.optr1` | "Bạn đã được cấp năng lực..." | ☐ |

**Acceptance:** Tất cả 7 step Pass.

---

### UAT-IMM06-04 — Authorization Gate IMM-08 (BR-06-01)

**Liên kết:** US-06-07, BR-06-01
**Role tester:** System / QA Lead
**Mục tiêu:** check_user_authorization block/allow đúng theo trạng thái competency.

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | GET `check_user_authorization?user=ktv.optr1&device_model=MDL-MON-PHILIPS-X3` (Active) | `authorized=true` | ☐ |
| 2 | GET với user không có competency | `authorized=false`, reason = "chưa có Active competency" | ☐ |
| 3 | Set competency `ktv.optr1` → Expired, retry | `authorized=false`, reason = "Năng lực đã hết hạn" | ☐ |
| 4 | Gọi 2 lần liên tiếp khi Active | 2nd call ≤ 50ms (cache hit) | ☐ |
| 5 | IMM-08 assign KTV không có competency → thử assign WO | Block: "Kỹ thuật viên chưa có năng lực..." | ☐ |

**Acceptance:** Tất cả 5 step Pass.

---

### UAT-IMM06-05 — Operator Coverage Gate IMM-04 (BR-06-07)

**Liên kết:** US-06-08, BR-06-07
**Role tester:** System / QA Lead
**Mục tiêu:** Class III cần ≥ 2 operator; gate_pass=false khi chỉ có 1.

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | GET `get_asset_operator_coverage?asset=AC-ASSET-TEST-001` (Class III, 1 operator ICU) | `operator_count=1`, `required_min=2`, `gate_pass=false` | ☐ |
| 2 | Sign-off thêm 1 competency cho cùng device_model tại ICU | — | ☐ |
| 3 | Retry GET coverage | `operator_count=2`, `gate_pass=true` | ☐ |
| 4 | Test Class II asset: required_min=1 | `gate_pass=true` khi coverage=1 | ☐ |
| 5 | IMM-04 Clinical_Release submit khi Class III thiếu coverage | Block "BR-06-07: Cần ≥2 operator competent..." | ☐ |

**Acceptance:** Tất cả 5 step Pass.

---

### UAT-IMM06-06 — Scheduler Expiry Alert + Auto-expire (BR-06-03)

**Liên kết:** US-06-06, BR-06-03
**Role tester:** System
**Mục tiêu:** Scheduler đánh dấu Expiring đúng mốc, idempotent; auto-expire đúng hạn.

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | Set expiry_date = today + 90, `bench execute assetcore.tasks.check_competency_expiry` | status = Expiring, Alert Log (milestone=90) | ☐ |
| 2 | Chạy lần 2 cùng ngày | KHÔNG tạo duplicate Alert Log (idempotent) | ☐ |
| 3 | Set expiry_date = today + 30, chạy lại | Alert milestone=30 Critical, email user + supervisor + Workshop Head | ☐ |
| 4 | Set expiry_date = today - 1, `bench execute assetcore.tasks.auto_expire_competency` | status = Expired, email user + Workshop Head | ☐ |
| 5 | Verify `check_user_authorization` sau auto-expire | `authorized=false` (cache invalidated) | ☐ |
| 6 | Verify IMM Audit Trail "AUTO_EXPIRE" | OK | ☐ |

**Acceptance:** Tất cả 6 step Pass.

---

### UAT-IMM06-07 — Revoke Competency + CAPA (BR-06-06, VR-08)

**Liên kết:** US-06-10, BR-06-06
**Role tester:** Tổ HC-QLCL
**Mục tiêu:** Revoke đúng flow; VR-08 block khi thiếu CAPA nếu reason liên quan incident.

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | `qlcl.lead` mở Competency Active, bấm "Thu hồi" | Modal hiện | ☐ |
| 2 | Nhập reason = "Vi phạm quy trình vận hành" (không có từ khóa incident) | CAPA field optional | ☐ |
| 3 | Confirm | status = Revoked, `revoked_by`, `revoked_date` set | ☐ |
| 4 | Thử revoke với reason = "Liên quan sự cố vận hành" và không điền CAPA | Lỗi VR-08 "Thu hồi do sự cố phải có CAPA reference" | ☐ |
| 5 | Điền `revoke_capa_ref = CAPA-2026-0001`, revoke | Pass | ☐ |
| 6 | Verify cache invalidated: `check_user_authorization` → false | OK | ☐ |
| 7 | Verify IMM Audit Trail "REVOKE" với metadata | OK | ☐ |
| 8 | Verify email Workshop Head (flagged WO nếu có) | OK | ☐ |

**Acceptance:** Tất cả 8 step Pass.

---

### UAT-IMM06-08 — BR-06-04 Program Update Trigger Recert

**Liên kết:** BR-06-04, US-06-01
**Role tester:** Tổ HC-QLCL
**Mục tiêu:** Thay đổi field trọng yếu của Program → trigger recert toàn bộ user.

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | Seed: Program TRN-MON-INIT-UAT có 3 user Active competency | — | ☐ |
| 2 | `qlcl.lead` mở Program, sửa `passing_score_pct` từ 70 → 75 | Banner cảnh báo "3 user sẽ cần re-cert" | ☐ |
| 3 | Lưu | response.recert_triggered=true, affected_count=3 | ☐ |
| 4 | Verify Document Request / task tạo cho Tổ HC-QLCL | OK | ☐ |
| 5 | Sửa chỉ `description` (non-critical) | Không trigger recert | ☐ |

**Acceptance:** Tất cả 5 step Pass.

---

### UAT-IMM06-09 — Self-service Portal (Permission Isolation)

**Liên kết:** US-06-11, SEC-IMM06-01
**Role tester:** HTM Technician (2 accounts)
**Mục tiêu:** Operator chỉ thấy competency của chính mình.

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | `ktv.optr1` đăng nhập, mở `/me/competencies` | List competency của chính mình | ☐ |
| 2 | Verify không thấy competency của `ktv.optr2` | Đúng | ☐ |
| 3 | `ktv.optr1` GET `get_user_competencies?user=ktv.optr2` | Lỗi FORBIDDEN | ☐ |
| 4 | `ktv.optr1` không thấy nút Sign-off / Revoke / Dashboard tab | Đúng (role-based UI) | ☐ |
| 5 | `ktv.optr1` click "Xem chứng nhận PDF" | Mở/download PDF (certificate_file) | ☐ |

**Acceptance:** Tất cả 5 step Pass.

---

### UAT-IMM06-10 — Delete Prevention (BR-06-09)

**Liên kết:** BR-06-09
**Role tester:** CMMS Admin
**Mục tiêu:** Không thể xóa cứng bất kỳ competency nào, kể cả Admin.

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | `admin.cms` thử delete competency Active | Lỗi BR-06-09 "Không được phép xóa Competency..." | ☐ |
| 2 | Thử delete competency Expired | Lỗi BR-06-09 | ☐ |
| 3 | API `frappe.delete_doc("IMM User Competency", name)` từ console | on_trash() throw | ☐ |
| 4 | Verify record vẫn tồn tại sau mọi attempt | OK | ☐ |

**Acceptance:** Tất cả 4 step Pass.

---

### UAT-IMM06-11 — Dashboard KPI + Gap Report

**Liên kết:** US-06-12
**Role tester:** Workshop Head
**Mục tiêu:** Dashboard hiển thị đúng KPI, Gap Matrix drill-down.

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | `workshop.head` mở `/imm06/dashboard` | 7 KPI cards load đúng số liệu | ☐ |
| 2 | Verify Gap Matrix khoa × device class hiển thị | Đúng format (rows=dept, cols=Class II/III) | ☐ |
| 3 | Click cell ICU × Class III có gap | List assets vi phạm BR-06-07 | ☐ |
| 4 | Filter "Expiring 90d" | Navigate list đúng | ☐ |
| 5 | Chạy `generate_competency_gap_report` | GAP Record mới tạo, email Workshop Head + VP Block2 | ☐ |

**Acceptance:** Tất cả 5 step Pass.

---

### UAT-IMM06-12 — Audit Trail Integrity

**Liên kết:** BR-06-08, SEC-IMM06-02
**Role tester:** CMMS Admin / QA Lead
**Mục tiêu:** Mọi action có audit trail; chain không thể tamper.

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | Kiểm tra IMM Audit Trail sau signoff | event_type = "SIGNOFF" tồn tại | ☐ |
| 2 | Kiểm tra sau revoke | event_type = "REVOKE" tồn tại, metadata đầy đủ | ☐ |
| 3 | Gọi `verify_audit_chain(asset)` từ console | True | ☐ |
| 4 | Thử sửa 1 IMM Audit Trail record trực tiếp | System block hoặc permission denied | ☐ |

**Acceptance:** Tất cả 4 step Pass.

---

## II.5. Tổng Hợp Kết Quả & Bug Found

### Bảng kết quả

| Scenario | Status | Tester | Ngày | Ghi chú |
|---|---|---|---|---|
| UAT-IMM06-01 | ☐ Pass / ☐ Fail | | | |
| UAT-IMM06-02 | ☐ Pass / ☐ Fail | | | |
| UAT-IMM06-03 | ☐ Pass / ☐ Fail | | | |
| UAT-IMM06-04 | ☐ Pass / ☐ Fail | | | |
| UAT-IMM06-05 | ☐ Pass / ☐ Fail | | | |
| UAT-IMM06-06 | ☐ Pass / ☐ Fail | | | |
| UAT-IMM06-07 | ☐ Pass / ☐ Fail | | | |
| UAT-IMM06-08 | ☐ Pass / ☐ Fail | | | |
| UAT-IMM06-09 | ☐ Pass / ☐ Fail | | | |
| UAT-IMM06-10 | ☐ Pass / ☐ Fail | | | |
| UAT-IMM06-11 | ☐ Pass / ☐ Fail | | | |
| UAT-IMM06-12 | ☐ Pass / ☐ Fail | | | |

### Sign-off UAT

| Vai trò | Người | Ngày | Chữ ký |
|---|---|---|---|
| BA Lead | | | |
| QA Lead | | | |
| Module Owner (Tổ HC-QLCL Lead) | | | |
| Đại diện end-user (Workshop Head) | | | |

**Quy ước go-live:** Blocker = 0, Major ≤ 2 (có workaround đã documented).

### Bug Log

| Issue ID | Severity | Mô tả | Fix status |
|---|---|---|---|
| (điền khi phát sinh) | | | |

---

# Phần III — Security Review

## III.1. RBAC

### Role definitions

Xem `assetcore/fixtures/role.json` + `role_profile.json`. Các role liên quan IMM-06:

| Role | Quyền trên Training / Competency |
|---|---|
| Tổ HC-QLCL (Training Officer) | Full — Create, Read, Write, Cancel, Revoke |
| Workshop Head | Read, Write (Verify Session, Sign-off, Suspend) |
| Biomed Engineer | Read/Write Session (instructor), Read Competency |
| Department Manager | Read, Write (Sign-off own dept only) |
| Clinical Head | Read (own dept only) |
| HTM Technician / Operator | Read (own competency only) |
| CMMS Admin | Full |

### DocPerm Matrix — `IMM User Competency`

| Role | Read | Write | Create | Submit | Cancel | Delete |
|---|---|---|---|---|---|---|
| Tổ HC-QLCL | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| Workshop Head | ✅ | ✅ (Suspend) | ❌ | ❌ | ❌ | ❌ |
| Department Manager | ✅ (own dept) | ✅ (sign-off own) | ❌ | ❌ | ❌ | ❌ |
| Biomed Engineer | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| HTM Technician / Operator | ✅ (own) | ❌ | ❌ | ❌ | ❌ | ❌ |
| CMMS Admin | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |

### DocPerm Matrix — `IMM Training Session`

| Role | Read | Write | Create | Submit | Cancel |
|---|---|---|---|---|---|
| Tổ HC-QLCL | ✅ | ✅ | ✅ | ✅ | ✅ |
| Biomed Engineer | ✅ | ✅ (if instructor) | ✅ | ✅ | ❌ |
| Workshop Head | ✅ | ✅ (Verify) | ❌ | ❌ | ❌ |
| HTM Technician | ✅ (own session) | ✅ (own session) | ✅ | ❌ | ❌ |
| Operator | ✅ (own) | ❌ | ❌ | ❌ | ❌ |

### Field-level permission (permlevel)

| Field | permlevel | Mô tả |
|---|---|---|
| `revoke_reason` | 1 — Tổ HC-QLCL+ | Lý do thu hồi nhạy cảm |
| `revoke_capa_ref` | 1 — Tổ HC-QLCL+ | CAPA reference |
| `last_assessment_score` | 0 — all authenticated | Điểm đánh giá |
| `supervisor_signoff` | 1 — Workshop Head+ | Ký tên cấp trên |

### User Permission (Row-level)

`permission_query_conditions` trong `assetcore/permissions.py`:
```python
def user_competency_query(user):
    if any([frappe.has_role(r, user) for r in
            ["Tổ HC-QLCL", "Workshop Head", "CMMS Admin", "Biomed Engineer"]]):
        return ""
    # Department Manager: own dept only
    if frappe.has_role("Department Manager", user):
        dept = frappe.db.get_value("User", user, "department")
        return f"(`tabIMM User Competency`.department_at_assessment = '{dept}')"
    # Operator / HTM Technician: own only
    return f"(`tabIMM User Competency`.user = '{user}')"
```

## III.2. API Security

| Mục | Trạng thái | Ghi chú |
|---|---|---|
| Whitelist hygiene | ✅ | Mọi `@frappe.whitelist()` có docstring + required role check |
| CSRF | ✅ | Frappe default X-Frappe-CSRF-Token |
| Input validation | ✅ | `name` field validate qua `frappe.get_value` trước khi dùng |
| SQL injection | ✅ | Frappe ORM parameterized; không raw SQL trong imm06.py |
| Rate limit `check_user_authorization` | ⚠️ Roadmap | Cached nhưng chưa rate-limit external caller |
| Rate limit `create_program` | ⚠️ Roadmap | Cần cấu hình cho batch creation |

## III.3. Audit Trail Integrity

- Mọi state change (sign-off / revoke / suspend / auto-expire) sinh `IMM Audit Trail` qua `lifecycle.log_audit_event()`.
- Hash chain SHA-256: `hash = SHA256(prev_hash + canonical_json(event))`.
- API verify: `assetcore.utils.lifecycle.verify_audit_chain(asset)` → `bool`.
- Test tamper: `test_audit_chain_breaks_on_tamper()` (§I.6).
- User KHÔNG có quyền Delete/Amend `IMM Audit Trail` (không trong DocPerm bất kỳ role nào).
- Retention: ≥ 10 năm sau user nghỉ việc (NFR-06-06 + NĐ98 §35).

## III.4. Authentication & Session

| Hạng mục | Config |
|---|---|
| Login | Frappe default — username + password |
| Session timeout | 8 giờ (config `frappe.conf.session_expiry`) |
| Lockout policy | 3 lần fail → lock 15 phút |
| Password policy | Minimum 8 ký tự, 1 chữ hoa, 1 số |
| API key | Per-user, rotate mỗi 90 ngày; không commit vào git |
| 2FA | Roadmap Phase 2 — TOTP via Frappe 2FA |

## III.5. Data Sensitivity

| Loại | Trường | Sensitivity | Bảo vệ |
|---|---|---|---|
| Điểm đánh giá | `theory_score`, `practical_score`, `last_assessment_score` | Internal | Role permission |
| Lý do thu hồi | `revoke_reason` | Confidential | permlevel 1 |
| Chứng nhận PDF | `certificate_file` | Internal | Role permission (R own only) |
| Thông tin cá nhân user | `user`, `supervisor_signoff` | Internal | Row-level permission |
| Dữ liệu bệnh nhân | Không lưu | N/A | IMM-06 KHÔNG lưu patient data |

## III.6. Vendor Isolation

`Vendor Engineer` (external) không có quyền trên bất kỳ Training / Competency DocType nào. Training trong IMM-06 dành cho **nhân sự nội bộ** — vendor training quản lý qua `AC Authorized Technician` (IMM-03), tách biệt hoàn toàn.

## III.7. Secrets Management

- `site_config.json` không commit vào git (`.gitignore` đã cấu hình).
- Email notification token lưu `frappe.conf`, không hardcode.
- Backup encrypt at-rest; off-site S3 theo `08_Deployment.md §I.2b`.
- Secret scan CI: `detect-secrets` trong pre-commit hook.

## III.8. Logging & Monitoring

| Sự kiện | Log level | Where | Alert? |
|---|---|---|---|
| Competency auto-expired (batch) | WARNING | `frappe.log_error` + Audit Trail | ✅ Email Workshop Head |
| Competency revoked | WARNING | `IMM Audit Trail` + frappe log | ✅ Email Workshop Head |
| Authorization gate denied (WO assign) | INFO | Frappe access log | ❌ |
| Audit chain tamper detected | ERROR | `frappe.log_error` | ✅ Email CMMS Admin |
| Gap report violation (Class III) | WARNING | Gap Report record + email | ✅ Email Workshop Head + VP Block2 |
| Login fail | INFO | Frappe login log | ✅ (sau 3 lần) |
| PII trong log | ❌ | Policy: KHÔNG log patient data | — |

## III.9. Threat Model (STRIDE-lite)

| Threat | Vector | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| Spoofing — session KTV | Giả mạo session user | Low | High | Session cookie HttpOnly + SameSite; Frappe session verify |
| Tampering — Audit Trail | Sửa IMM Audit Trail trực tiếp | Low | Critical | DocPerm no-delete; verify chain endpoint; test tamper |
| Tampering — Competency | Tự edit status = Active bypass sign-off | Low | High | Workflow constraint + service layer validate |
| Repudiation — Sign-off | Supervisor phủ nhận đã duyệt | Low | High | `IMM Audit Trail` + audit chain hash + supervisor_signoff field |
| Info Disclosure — Điểm thi | Operator xem điểm người khác | Medium | Medium | Row-level permission `user_competency_query()` + test UAT-09 |
| DoS — Scheduler | Gap report quá nhiều competency (50k) | Low | Medium | Batch 200/run; index `(status, expiry_date)` |
| Elevation — Revoke không CAPA | KTV tự revoke bypass VR-08 | Low | High | VR-08 enforce tại service layer + whitelist role check |

## III.10. Penetration Test

Trước release đầu tiên (go-live bệnh viện):
- Burp Suite / OWASP ZAP scan trên `uat.assetcore.vn` — 0 High/Critical open.
- sqlmap (mode safe) trên `create_program`, `revoke_competency`.
- CSRF token verify bằng curl không có token.
- Role escalation: thử gọi `revoke_competency` với role HTM Technician → 403.
- Authorization gate bypass: thử `check_user_authorization` với manipulated response.
- Report lưu: `docs/security/pentest_imm06_v1.md`.

## III.11. Sign-off Security

| Vai trò | Người | Ngày | Quyết định |
|---|---|---|---|
| QA Lead | | | ☐ Pass / ☐ Pass with conditions / ☐ Fail |
| Tech Lead | | | ☐ Pass / ☐ Pass with conditions / ☐ Fail |
| Module Owner (Tổ HC-QLCL Lead) | | | ☐ Pass / ☐ Pass with conditions / ☐ Fail |

**Điều kiện go-live:** Tất cả Sign-off là Pass hoặc Pass with conditions (với workaround documented).

---

## DoD — Hoàn chỉnh

### I. Test Plan
- [x] Test class structure cho 12 service functions (BR-06-01 → 12)
- [x] ≥ 1 happy + 1 negative test mỗi function
- [x] 2 workflow (Session + Competency) — mọi transition có test
- [x] Audit chain test (intact + tampered)
- [x] API test ≥ 60% coverage target (23 endpoints)
- [x] Performance target xác định (k6) — đặc biệt `check_user_authorization` ≤ 200ms
- [x] CI command xác định
- [x] SonarQube + Lighthouse target xác định

### II. UAT
- [x] 12 UAT scenario, cover mọi 12 BR + permission + audit + dashboard
- [x] Mọi User Story (US-06-01 → 06-12) có ≥ 1 UAT scenario
- [x] Test data seed script: `uat_imm06.py`
- [x] 7 Tester accounts + password documented
- [x] Sign-off section sẵn sàng

### III. Security
- [x] DocPerm matrix đầy đủ cho Training Session + User Competency
- [x] Row-level permission `user_competency_query()` documented
- [x] Threat model ≥ 7 threat với mitigation
- [ ] Pentest report lưu `docs/security/` (trước go-live)
- [ ] Rate limit `check_user_authorization` external (roadmap)
- [x] Vendor isolation policy documented
- [x] Sign-off section sẵn sàng
