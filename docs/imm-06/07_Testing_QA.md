# 07 — Kiểm thử & An ninh (Testing & QA & Security)

| Mục | Giá trị |
|---|---|
| Module | IMM-06 — Đào tạo & Năng lực (Training & Competency) |
| Phạm vi | Per-module |
| Owner | QA Lead + Security Officer |
| Liên kết | 02 Analysis (US, BR, Activity, BPMN) · 03 Diagrams · 04 Backend · 05 API · 06 Frontend |

> **Mục đích**: Suy ra test case **có hệ thống** từ phân tích (file 02) bằng kỹ thuật black-box + white-box, không liệt kê tự phát. Bao gồm: phân tích đối tượng test → chọn kỹ thuật → viết test → traceability → UAT → security → code quality. Q3 là gate go-live.

---

# Phần I — Test Analysis (Phân tích đối tượng test)

> Mục tiêu Phần I: trả lời 4 câu hỏi trước khi viết test case: **(1) test cái gì** (component inventory) **(2) suy ra từ đâu** (US/BR/Activity) **(3) ưu tiên cái nào** (risk) **(4) loại trừ cái nào** (out-of-scope).

## I.1. Component Inventory — Liệt kê phần mềm cần test

Tổng hợp artefact test được của IMM-06 (đối chiếu 04 Backend, 05 API, 06 Frontend). Mỗi dòng → ≥ 1 test class ở Phần III.

| # | Component | Loại | File / Tên | Test layer áp dụng |
|---|---|---|---|---|
| 1 | IMM Training Program | DocType | `imm_training_program.json` | Integration (lifecycle) |
| 2 | IMM Training Session | DocType | `imm_training_session.json` | Integration (state machine service-layer) |
| 3 | IMM User Competency | DocType | `imm_user_competency.json` | Integration (workflow JSON) |
| 4 | IMM Training Participant | Child DocType | `imm_training_participant.json` | Unit (score compute) |
| 5 | IMM Trainer | DocType | `imm_trainer.json` | Integration (assign instructor) |
| 6 | IMM Competency Gap Report | DocType | `imm_competency_gap_report.json` | Integration (scheduler output) |
| 7 | IMM Competency Alert Log | DocType | `imm_competency_alert_log.json` | Unit (idempotent alert) |
| 8 | Competency Workflow | Workflow JSON | `workflow/imm_06_competency_workflow.json` (19 transitions) | Integration (state transition) |
| 9 | Session lifecycle | Service state machine | `services/imm06.py::confirm/start/complete/verify/close/cancel_session` | Integration (state transition) |
| 10 | Validators | Service function | `services/imm06.py::validate_*` (VR-01..VR-12) | Unit (BVA/EP/Decision Table) |
| 11 | Score compute | Service function | `services/imm06.py::compute_overall_results` | Unit |
| 12 | Auto-create competency | Service function | `services/imm06.py::create_competency_from_session` / `_create_competency_record` | Integration |
| 13 | Sign-off / Revoke / Archive | Service function | `services/imm06.py::signoff_competency`, `revoke_competency_with_capa`, `archive_old_competency` | Unit + Integration |
| 14 | Authorization gate | Service function | `services/imm06.py::validate_user_authorized_for_asset` | Unit + Integration (cache) |
| 15 | Operator coverage gate | Service function | `services/imm06.py::get_asset_operator_coverage` | Unit |
| 16 | Gap report | Service function | `services/imm06.py::generate_gap_report`, `generate_weekly_gap_report` | Integration |
| 17 | Recertification | Service function | `services/imm06.py::recertify_competency`, `check_recertification_due` | Integration |
| 18 | Scheduler — expiry | Cron function | `services/imm06.py::check_expiring_competencies`, `auto_expire_competencies` | Unit + Cron simulation |
| 19 | Program change recert | Hook function | `services/imm06.py::flag_recertification_if_critical_change` | Integration (on_update) |
| 20 | Dept change | Hook function | `services/imm06.py::handle_user_dept_change` | Integration |
| 21 | API endpoints (25) | API endpoint | `api/imm06.py::*` | API integration |
| 22 | Audit log | Service function | `services/imm06.py::_log_competency_audit` → `IMM Audit Trail` | Integration (audit chain) |
| 23 | FE — Training Dashboard / Program / Session / Competency views | FE view | `frontend/src/views/imm06/*.vue` *(Cần khảo sát đường dẫn chính xác)* | E2E (Playwright) |
| 24 | FE — store imm06 | Pinia store | `frontend/src/stores/imm06.ts` *(Cần khảo sát)* | Unit (vitest) |

Service functions xác thực bằng `grep -n "^def " assetcore/services/imm06.py`; endpoint bằng `grep -n "@frappe.whitelist" assetcore/api/imm06.py` (25 endpoint thực tế — xem III.6).

## I.2. Trace nguồn test — User Stories, Activity Flows, Business Rules

Dẫn từ artefact phân tích (02_Analysis_Design.md) sang test layer. Mỗi US/BR/Activity phải có ≥ 1 test ở Phần III và xuất hiện trong matrix Phần IV.

### I.2.a. Từ User Story
→ 02 §Functional Specs (US-06-01 → US-06-12)

| US ID | Tiêu đề ngắn | Acceptance Criteria # | Test layer dự kiến |
|---|---|---|---|
| US-06-01 | Tạo Training Program (curriculum) | AC1 (tạo hợp lệ), AC2 (VR-02 score) | Unit + API + UAT |
| US-06-02 | Schedule Training Session | AC1, AC2 (VR-10 ngày) | Integration + UAT |
| US-06-03 | Confirm & Run Session | AC1 (VR-05), AC2 | Workflow + UAT |
| US-06-04 | Chấm điểm & Complete Session | AC1 (VR-06), AC2 (auto-create) | Unit + Integration + UAT |
| US-06-05 | Supervisor Sign-off Competency | AC1 (VR-07), AC2 (dept) | Unit + API + UAT |
| US-06-06 | Cảnh báo hết hạn (Scheduler) | AC1 (milestone), AC2 (idempotent) | Unit (cron) + UAT |
| US-06-07 | Authorization Gate (IMM-08/09/12 hook) | AC1 (active), AC2 (expired) | Unit + API + UAT |
| US-06-08 | Operator Coverage Gate (IMM-04 Clinical Release) | AC1 (Class III ≥2) | Unit + API + UAT |
| US-06-09 | Recertification Flow | AC1 | Integration + UAT |
| US-06-10 | Revoke Competency | AC1 (VR-08 CAPA) | Unit + API + UAT |
| US-06-11 | Self-service portal | AC1 (own only) | API + E2E + UAT |
| US-06-12 | Gap Dashboard | AC1 (KPI), AC2 (drill-down) | API + E2E + UAT |

### I.2.b. Từ Business Rule
→ 02 §Business Rules (BR-06-01 → BR-06-12)

| BR ID | Phát biểu (rút gọn) | Component liên quan (I.1) | Kỹ thuật test phù hợp |
|---|---|---|---|
| BR-06-01 | Operator chỉ giao WO Class II/III nếu có Active competency cho device_model | #14 `validate_user_authorized_for_asset` | Decision Table |
| BR-06-02 | Session phải có instructor đủ qualification (VR-04) | #10 `validate_instructor_present` | EP |
| BR-06-03 | Re-certification bắt buộc trước expiry; Expired → block | #18 scheduler + #14 gate | State Transition |
| BR-06-04 | Program đổi field trọng yếu → trigger re-cert hàng loạt | #19 `flag_recertification_if_critical_change` | Decision Table |
| BR-06-05 | Participant cần theory+practical+sign-off trước Active (VR-06/07) | #11 #13 | Decision Table |
| BR-06-06 | Revoke cần lý do + CAPA nếu liên quan incident (VR-08) | #13 `revoke_competency_with_capa` | Decision Table |
| BR-06-07 | Class III cần ≥2 operator Active tại khoa | #15 `get_asset_operator_coverage` | BVA (boundary =1/=2) |
| BR-06-08 | Audit trail mọi thay đổi competency | #22 `_log_competency_audit` | Use Case |
| BR-06-09 | Không xóa cứng competency | `on_trash()` guard | EP |
| BR-06-10 | Đổi khoa → lưu `department_at_assessment`, gap tính lại | #20 `handle_user_dept_change` | Use Case |
| BR-06-11 | 1 user × device_model chỉ 1 Active (archive cũ) | #13 `archive_old_competency` | State Transition |
| BR-06-12 | Session Verified không thể Cancel | #9 `cancel_session` check | State Transition |

### I.2.c. Từ Activity Flow / BPMN
→ 02 §Activity Diagram

| Activity ID | Use Case | Branch chính | Branch ngoại lệ |
|---|---|---|---|
| ACT-06-01 | UC tạo Program + curriculum | Tạo & active | VR-02/VR-03/VR-11 reject |
| ACT-06-02 | UC session lifecycle Planned→Closed | Happy 6 state | VR-05 no participant, VR-04 instructor, VR-06 missing score, BR-06-12 cancel-from-verified |
| ACT-06-03 | UC sign-off → Active | Pass → competency Active | wrong dept, đã Active, VR-07 missing |
| ACT-06-04 | UC scheduler expiry/auto-expire | Milestone 90/60/30 + auto expire | idempotent (no duplicate), cache invalidate |
| ACT-06-05 | UC revoke + CAPA | revoke pass | VR-08 incident no CAPA |
| ACT-06-06 | UC authorization/coverage gate | authorized=true | expired/no competency, Class III thiếu coverage |

## I.3. Risk-based Priority

| Component (I.1) | Likelihood | Impact | Risk = L×I | Priority |
|---|---|---|---|---|
| #14 Authorization gate (`validate_user_authorized_for_asset`) | 4 | 5 | 20 | **Critical** |
| #8 Competency Workflow (19 transitions) | 4 | 5 | 20 | **Critical** |
| #13 Sign-off/Revoke/Archive | 3 | 5 | 15 | **Critical** |
| #22 Audit log + chain | 2 | 5 | 10 | High |
| #15 Operator coverage gate (BR-06-07) | 3 | 4 | 12 | High |
| #9 Session lifecycle state machine | 4 | 3 | 12 | High |
| #10 Validators VR-01..VR-12 | 4 | 3 | 12 | High |
| #18 Scheduler expiry | 3 | 3 | 9 | Medium |
| #19 Program change recert | 2 | 4 | 8 | Medium |
| #16 Gap report | 2 | 3 | 6 | Medium |
| #21 API list/get endpoints (read) | 2 | 2 | 4 | Low |
| #23 FE views (read-only dashboard) | 2 | 2 | 4 | Low |

**Quy ước priority**:
- **Critical** (R ≥ 15): test trước, fail = block release
- **High** (10 ≤ R < 15): bắt buộc trước go-live
- **Medium** (5 ≤ R < 10): trong sprint khi có thời gian
- **Low** (R < 5): chỉ test khi báo cáo bug

## I.4. Scope

**In-scope:**
- Service layer `services/imm06.py` (validators VR-01..12, session lifecycle, sign-off/revoke, authorization & coverage gate, scheduler) — I.1 #9–#20
- Competency Workflow JSON 19 transitions — I.1 #8
- 25 API endpoint — I.1 #21
- Audit trail trên sign-off/revoke/suspend/auto-expire — I.1 #22
- Permission isolation self-service portal (operator chỉ thấy competency mình)

**Out-of-scope:**
- Performance/load test → giao Phần III.8 (chỉ định nghĩa target, chưa chạy)
- Penetration test → Phần VI.10 (trước go-live đầu tiên)
- LMS content delivery, e-signature số (ngoài phạm vi IMM-06)
- Cross-module IMM-04/08/09/11/12 chỉ test contract gate (smoke), full flow thuộc module đó

**Assumptions:**
- Master data đã seed: IMM Device Model (Class II + III), AC Department, CAPA stub
- 7 tester accounts đủ role (xem V.2)
- Scheduler enabled, MailHog cho outbound email
- Browser Chrome ≥ 120 / Edge ≥ 120

---

# Phần II — Test Design Techniques (Kỹ thuật thiết kế test case)

> Mục tiêu Phần II: chọn đúng kỹ thuật cho từng loại input/logic. Mỗi test phải truy được về 1 kỹ thuật ở dưới.

## II.1. Black-box techniques

| Kỹ thuật | Khi nào dùng | Áp dụng vào IMM-06 | Số test sinh ra (rule of thumb) |
|---|---|---|---|
| **Equivalence Partitioning (EP)** | Input có miền giá trị chia nhóm | `competency_level` (VR-12), `assessment_method` Select, `status` enum, `training_type` | 1 test/partition |
| **Boundary Value Analysis (BVA)** | Numeric/date/length có biên | `passing_score_pct` 0/1/100/101 (VR-02), `validity_period_months` 0/1/60 (VR-03), operator_count =1/=2 (BR-06-07), `attendance_pct` 0/100 (VR-09) | 2-3 test/biên |
| **Decision Table** | Multi-condition gate | Authorization gate (status × cache × model), VR-08 (reason keyword × CAPA presence), VR-06 (assessment_method × score presence) | 2^N rút gọn |
| **State Transition Testing** | Workflow finite state machine | Competency Workflow 19 transition; session lifecycle 7 state; BR-06-11 archive; BR-06-12 cancel guard | Mỗi transition + invalid transition |
| **Use Case Testing** | End-to-end actor flow | UAT scenarios (V.4), API integration | 1/main + 1/alt + 1/exception |
| **Pairwise / Combinatorial** | Nhiều field optional kết hợp | Form tạo Program (training_type × assessment_method × validity) | Min set cover all pairs |
| **Error Guessing** | null, empty, unicode, race | Mọi endpoint nhận user input; complete_session gọi 2 lần (idempotent) | Bổ sung |

## II.2. White-box techniques

| Kỹ thuật | Áp dụng vào | Tiêu chí đạt | Công cụ |
|---|---|---|---|
| **Statement coverage** | Service functions I.1 #9–#20 | ≥ 85% line | `coverage report` |
| **Branch / Decision coverage** | Functions có if/else/try/except | ≥ 80% branch | `coverage --branch` |
| **Condition / MC/DC** | Authorization gate, VR-08 keyword check, `compute_overall_results` (avg + attendance AND) | mỗi sub-condition kiểm soát outcome độc lập | Manual design + coverage |
| **Path coverage** | `compute_overall_results`, `archive_old_competency` | path khả dĩ (loop 0,1,N) | Manual |

Ưu tiên Branch coverage cho service layer; MC/DC chỉ áp dụng vào gate logic và `compute_overall_results`.

## II.3. Mapping Component → Kỹ thuật

| Loại component | Kỹ thuật chính | Kỹ thuật phụ |
|---|---|---|
| Field validator (`validate_*`) | BVA + EP | Error guessing |
| Gate logic (authorization / coverage / VR-08) | Decision Table | MC/DC |
| Competency Workflow transition | State Transition | Use Case |
| Session lifecycle service | State Transition | Use Case |
| Service function pure (`compute_overall_results`) | EP + Branch coverage | BVA + Path |
| API endpoint | Use Case + EP | Pairwise (form input) |
| Scheduler (`check_expiring_competencies`, `auto_expire_competencies`) | Use Case (setup → run → assert) | Error guessing (idempotent, partial fail) |
| FE view (Playwright) | Use Case end-to-end | Error guessing (network 4xx/5xx, role gate) |

---

# Phần III — Test Plan (Kế hoạch thực thi)

## III.1. Test Pyramid

```
                  ┌────────────┐
                  │  E2E / UAT │   ~5% — Playwright golden scenario (session→competency lifecycle)
                 ─┴────────────┴─
              ┌──────────────────────┐
              │   API Integration    │   ~15% — pytest + Frappe whitelist (25 endpoints)
             ─┴──────────────────────┴─
          ┌────────────────────────────────┐
          │  Workflow + DocType lifecycle  │   ~25% — Competency 19 transition + Session 7 state
         ─┴────────────────────────────────┴─
      ┌────────────────────────────────────────────┐
      │         Unit — Service Layer               │   ~55% — services/imm06.py (TDD)
     ─┴────────────────────────────────────────────┴─
```

Mọi service function phải có test trước khi code (TDD — → CLAUDE.md §17). Mỗi BR có ≥ 1 happy + 1 negative test.

**Trạng thái thực tế (2026-05-29):** Test scaffold hiện là **một file duy nhất** `assetcore/tests/test_imm06.py`. Các test class đã viết (✅ Live) liệt kê ở III.2; các file con tách theo layer (`test_imm06_service.py`, `_validators.py`, `_doctype.py`, `_workflow.py`, `_audit.py`, `_api.py`, e2e) **chưa tách** → đánh dấu ⬜ Planned.

## III.2. Unit test — Service Layer

**File hiện tại:** `assetcore/tests/test_imm06.py` (file đơn). Bảng dưới đánh dấu trạng thái thực: ✅ Live = class/method đã tồn tại; ⬜ Planned = chưa viết.

| Test class | Function cover | Kỹ thuật | Cases (happy/negative) | Trạng thái |
|---|---|---|---|---|
| `TestValidatePassingScoreRange` | `validate_passing_score_range` (VR-02) | BVA | 70/1/100 pass · 0/101 raise · None skip | ✅ Live |
| `TestScoreBoundsConfig` | `validate_score_bounds_config`, `get_program_score_bounds` | BVA + EP | valid bounds · max=min/max<min raise · defaults · tuple · invalid | ✅ Live |
| `TestValidateValidityRange` | `validate_validity_range` (VR-03) | BVA | 12/1 pass · 0/neg raise · None skip | ✅ Live |
| `TestComputeOverallResults` | `compute_overall_results` | MC/DC + Path | both above pass · avg below fail · attendance<80 fail · no program noop · multi participant | ✅ Live |
| `TestSignoffCompetency` | `signoff_competency` | EP | pending succeeds · already active raise · not found raise | ✅ Live |
| `TestArchiveOldCompetency` | `archive_old_competency` (BR-06-11) | State Transition | old active suspended · no old returns zero | ✅ Live |
| `TestIMMTrainer` | trainer create + assign session | Use Case | create & assign | ✅ Live |
| `TestParticipantScoreRange` | `validate_participant_scores` (VR-06/VR-09) | BVA | above max rejected · program max≤min rejected | ✅ Live |
| `TestEnrollParticipants` | `enroll_participants`, `remove_participant` | State Transition + EP | enroll adds rows · enroll on completed rejected · remove works | ✅ Live |
| `TestUserAuthorization` | `validate_user_authorized_for_asset` (BR-06-01) | Decision Table | active pass · expired/revoked/no-competency fail · cache | ⬜ Planned |
| `TestOperatorCoverage` | `get_asset_operator_coverage` (BR-06-07) | BVA | Class III =1 fail · =2 pass · Class II =1 pass | ⬜ Planned |
| `TestRevokeWithCapa` | `revoke_competency_with_capa` (VR-08) | Decision Table | no-incident pass · incident+CAPA pass · incident no-CAPA fail | ⬜ Planned |
| `TestScheduler` | `check_expiring_competencies`, `auto_expire_competencies` | Use Case (cron) | milestone 90/60/30 · idempotent · past-due expire · cache invalidate | ⬜ Planned |
| `TestRecertDue` | `check_recertification_due`, `recertify_competency` | Use Case | placeholder session · idempotent | ⬜ Planned |
| `TestGapReport` | `generate_gap_report`, `generate_weekly_gap_report` | Use Case | gap record + matrix | ⬜ Planned |
| `TestProgramRecert` | `flag_recertification_if_critical_change` (BR-06-04) | Decision Table | critical field → flag · non-critical → skip | ⬜ Planned |
| `TestDeletePrevention` | `on_trash()` (BR-06-09) | EP | Active/Expired/Revoked → throw | ⬜ Planned |

Mẹo: test thuần công thức (VR-02/03, compute_overall_results) dùng `SimpleNamespace` — không cần DB/fixture.

## III.3. Integration — DocType lifecycle

**File:** `assetcore/tests/test_imm06_doctype.py` ⬜ Planned (chưa tách).

| Test | Setup | Action | Assert | Kỹ thuật |
|---|---|---|---|---|
| `test_session_validates_instructor` | Program reqd Biomed, instructor = Operator | `session.insert()` | ValidationError VR-04 | EP |
| `test_complete_creates_competencies` | Session In Progress, 3 Pass + 2 Fail | `complete_session(name, results)` | 3 IMM User Competency Pending Assessment | Use Case |
| `test_signoff_sets_expiry` | Competency Pending Assessment | `signoff_competency(name)` | `expiry_date = achieved_date + validity_months` | EP |
| `test_competency_on_trash_blocked` | Competency Active | `frappe.delete_doc(...)` | PermissionError BR-06-09 | EP |
| `test_program_critical_change_recert` | Program 5 Active users | update `passing_score_pct` | recert flag, 5 affected | Decision Table |
| `test_audit_on_revoke` | Competency Active | `revoke_competency_with_capa(...)` | IMM Audit Trail action REVOKE | Use Case |
| `test_br0611_single_active` | User 1 Active | new session completed + signoff | old suspended, new Active | State Transition |

Fixture trong `setUpClass` phải có `tearDownClass` purge.

## III.4. Integration — Workflow transitions

**File:** `assetcore/tests/test_imm06_workflow.py` ⬜ Planned.

**Workflow JSON:** `assetcore/assetcore/workflow/imm_06_competency_workflow.json` — **19 transitions** (xác thực `python3 -c "import json;print(len(json.load(open('...'))['transitions']))"` → 19). 6 state: Pending Assessment, Active, Expiring, Expired, Suspended, Revoked.

| # | Action | From → To | Role required | Test pass | Test fail (wrong role / gate) |
|---|---|---|---|---|---|
| 1 | Sign-off | Pending Assessment → Active | Commissioning Manager | ☐ | ☐ |
| 2 | Sign-off | Pending Assessment → Active | PM Manager | ☐ | ☐ |
| 3 | Sign-off | Pending Assessment → Active | Training Manager | ☐ | ☐ |
| 4 | Đánh dấu sắp hết hạn | Active → Expiring | AssetCore Super Admin | ☐ | ☐ |
| 5 | Hết hạn | Active → Expired | AssetCore Super Admin | ☐ | ☐ |
| 6 | Hết hạn | Expiring → Expired | AssetCore Super Admin | ☐ | ☐ |
| 7 | Tạm ngưng | Active → Suspended | PM Manager | ☐ | ☐ |
| 8 | Tạm ngưng | Active → Suspended | Training Manager | ☐ | ☐ |
| 9 | Khôi phục | Suspended → Active | PM Manager | ☐ | ☐ |
| 10 | Khôi phục | Suspended → Active | Training Manager | ☐ | ☐ |
| 11 | Thu hồi | Active → Revoked | Training Manager | ☐ | ☐ |
| 12 | Thu hồi | Active → Revoked | AssetCore Super Admin | ☐ | ☐ |
| 13 | Thu hồi | Expiring → Revoked | Training Manager | ☐ | ☐ |
| 14 | Thu hồi | Expiring → Revoked | AssetCore Super Admin | ☐ | ☐ |
| 15 | Thu hồi | Expired → Revoked | Training Manager | ☐ | ☐ |
| 16 | Thu hồi | Expired → Revoked | AssetCore Super Admin | ☐ | ☐ |
| 17 | Thu hồi | Suspended → Revoked | Training Manager | ☐ | ☐ |
| 18 | Thu hồi | Suspended → Revoked | AssetCore Super Admin | ☐ | ☐ |
| 19 | Tái chứng nhận | Expired → Active | AssetCore Super Admin | ☐ | ☐ |

**Session lifecycle (service-layer state machine, KHÔNG dùng workflow JSON):** enforced trong `services/imm06.py` qua `SessionStatus` (Planned → Confirmed → In Progress → Completed → Verified → Closed; Cancelled). Mỗi transition có guard kiểm tra `workflow_state` hiện tại.

| Action (service fn) | From → To | Role required | Test pass | Test fail |
|---|---|---|---|---|
| `confirm_session` | Planned → Confirmed | Tổ HC-QLCL | ☐ | ☐ (VR-05 no participant / wrong state) |
| `start_session` | Confirmed → In Progress | Instructor / Tổ HC-QLCL | ☐ | ☐ (wrong state) |
| `complete_session` | In Progress → Completed | Instructor / Tổ HC-QLCL | ☐ | ☐ (VR-06 missing score / idempotent 2nd call) |
| `verify_session` | Completed → Verified | Workshop Head | ☐ | ☐ (wrong state) |
| `close_session` | Verified → Closed | Workshop Head / CMMS Admin | ☐ | ☐ |
| `cancel_session` | Planned/Confirmed/In Progress → Cancelled | Tổ HC-QLCL / CMMS Admin | ☐ | ☐ (BR-06-12 from Verified) |

**Kỹ thuật:** State Transition Testing — mỗi edge = 1 test pass + 1 test fail.

## III.5. Integration — Audit chain integrity

**File:** `assetcore/tests/test_imm06_audit.py` ⬜ Planned. 2 test chính:
- (a) Sau chuỗi mutation (complete → signoff → revoke), `verify_audit_chain(asset)` hash SHA-256 hợp lệ end-to-end.
- (b) Khi tamper 1 entry (sửa `hash_sha256` trong DB), verify endpoint trả `chain_broken=true`.

→ 04 Backend §Audit Trail · `IMM Audit Trail` DocType · `services/imm06.py::_log_competency_audit`.

## III.6. API test

**File:** `assetcore/tests/test_imm06_api.py` ⬜ Planned. **25 endpoint thực tế** (xác thực `grep -n "@frappe.whitelist" assetcore/api/imm06.py`):

| # | Endpoint | Verb | # | Endpoint | Verb |
|---|---|---|---|---|---|
| 1 | `list_programs` | GET | 14 | `cancel_session` | POST |
| 2 | `get_program` | GET | 15 | `verify_session` | POST |
| 3 | `create_program` | POST | 16 | `close_session` | POST |
| 4 | `update_program` | POST | 17 | `list_competencies` | GET |
| 5 | `list_sessions` | GET | 18 | `get_user_competencies` | GET |
| 6 | `get_session` | GET | 19 | `signoff_competency` | POST |
| 7 | `create_session` | POST | 20 | `revoke_competency` | POST |
| 8 | `confirm_session` | POST | 21 | `recertify_competency` | POST |
| 9 | `start_session` | POST | 22 | `get_dashboard_stats` | GET |
| 10 | `enroll_participants` | POST | 23 | `get_competency_gaps_by_dept` | GET |
| 11 | `remove_participant` | POST | 24 | `get_expiring_competencies` | GET |
| 12 | `complete_session` | POST | 25 | `check_user_authorization` | GET |
| 13 | `cancel_session`* | — | 26 | `get_asset_operator_coverage` | GET |

\* (25 endpoint whitelist; bảng liệt kê toàn bộ tên thực tế — `complete_session` ở dòng 12, các verb theo decorator `methods=["POST"]`).

| Test | Endpoint | Verify | Kỹ thuật |
|---|---|---|---|
| `test_list_programs_pagination` | `list_programs` | page/page_size, envelope `success=true` | EP |
| `test_get_program_not_found` | `get_program?name=FAKE` | `code=NOT_FOUND` | EP |
| `test_create_program_bad_score` | `create_program` score=0 | `code=VALIDATION` VR-02 | BVA |
| `test_complete_session_auto_competency` | `complete_session` | N Pass → N competency | Use Case |
| `test_complete_session_missing_scores` | `complete_session` no practical | `code=VALIDATION` VR-06 | Decision Table |
| `test_signoff_wrong_dept` | `signoff_competency` dept mismatch | `code=FORBIDDEN` | EP (permission) |
| `test_revoke_incident_no_capa` | `revoke_competency` incident, no CAPA | `code=VALIDATION` VR-08 | Decision Table |
| `test_check_user_authorization_active/expired` | `check_user_authorization` | `authorized=true/false` | Decision Table |
| `test_coverage_class3_insufficient/sufficient` | `get_asset_operator_coverage` | `gate_pass=false/true` | BVA |
| `test_list_competencies_as_operator` | `list_competencies` role=Operator | chỉ own records | EP |
| `test_create_program_no_permission` | `create_program` role=HTM Technician | HTTP 403 / FORBIDDEN | EP |
| `test_idempotent_complete_session` | `complete_session` ×2 | 2nd → `code=BAD_STATE` | Error guessing |

Cover: happy + envelope `success=true`, invalid params, no permission FORBIDDEN, pagination boundaries, idempotent retry.

## III.7. E2E browser (Playwright)

**File:** `assetcore/tests/e2e/test_imm06_golden.py` ⬜ Planned. Dùng cho flow UI khó cover bằng API: dropdown cascade Program→Session, modal confirm sign-off/revoke, workflow button visibility theo role, dashboard gap matrix drill-down.

**Golden scenario:** Tổ HC-QLCL tạo Program → Schedule Session → Confirm → Start → chấm 3 Pass + 2 Fail → Complete → Department Manager sign-off → competency Active → `check_user_authorization=true` → Scheduler expiry alert → Revoke với CAPA.

→ `assetcore-test` skill Phần 2 (Playwright MCP recipes + R-1..R-9 data rules).

## III.8. Performance test

| Metric | Target | Method |
|---|---|---|
| `list_competencies` p95 (5k records) | ≤ 1.5 s | k6 ramping 20 VU |
| `check_user_authorization` p95 (cached) | ≤ 200 ms | k6 — critical: WO assign hotpath |
| `complete_session` p95 (15 participants) | ≤ 2 s | k6 POST batch |
| `get_dashboard_stats` p95 | ≤ 1.2 s | k6 |
| Scheduler `check_expiring_competencies` (1000 competency) | ≤ 60 s | `time bench execute` |
| Scheduler `generate_weekly_gap_report` | ≤ 120 s | `time bench execute` |
| Dashboard FE render (gap matrix 10×3) | ≤ 1 s DOMContentLoaded | Lighthouse / Playwright |

## III.9. Test data & Fixtures

| Loại | Cách seed | File |
|---|---|---|
| Master data (Device Model, Department, CAPA stub) | `fixtures/*.json` (cài qua `bench migrate`) | `assetcore/fixtures/` |
| IMM Device Model | test fixture | 2 models (Class II + Class III) |
| IMM Training Program | test fixture | 3 programs (Initial/Refresher/Advanced) |
| IMM Training Session | test fixture | 5 sessions với participants |
| IMM User Competency | test fixture | 10 (Active/Expiring/Expired/Revoked) |
| AC Asset (training context) | test fixture | 4 assets gắn device model |
| UAT full seed | Python script | `assetcore/scripts/uat/uat_imm06.py` *(Cần khảo sát tồn tại file)* |

UAT data phải **thực tế** (tên bệnh viện VN, mã NCC chuẩn). Backend test fixture mới dùng prefix `_Test` (→ `assetcore-test` R-0/R-1).

## III.10. Run commands & Coverage gate

```bash
# Module test (file đơn hiện tại)
bench --site assetcore.local run-tests --app assetcore --module assetcore.tests.test_imm06
# Coverage
coverage run -m unittest assetcore.tests.test_imm06 && coverage report
# Full suite (CI)
bench --site assetcore.local run-tests --app assetcore --coverage
```

| Layer | Target coverage | Đo |
|---|---|---|
| Service (`services/imm06.py`) | ≥ 85% line + ≥ 80% branch | `coverage --branch` |
| DocType lifecycle | ≥ 70% | `coverage report` |
| API (`api/imm06.py`) | ≥ 60% | `coverage report` |
| Frontend (vue-tsc) | 0 error | `npm run build` |

Coverage % thực tế: *(Cần khảo sát — chưa chạy đo)*. CI fail nếu coverage < target hoặc test fail.

---

# Phần IV — Traceability Matrices

> Mọi test ở Phần III phải xuất hiện ở **cả 3** bảng để audit ngược.

## IV.1. US → Test mapping

| US ID | AC | Test ID (III.x) | Layer | Status |
|---|---|---|---|---|
| US-06-01 | AC2 score | `TestValidatePassingScoreRange` (III.2) | Unit | ✅ Live |
| US-06-02 | AC1 schedule | `test_session_validates_instructor` (III.3) | Integration | ⬜ Planned |
| US-06-03 | AC1 confirm | `confirm_session` transition (III.4) | Workflow | ⬜ Planned |
| US-06-04 | AC1 score / AC2 complete | `TestComputeOverallResults` (III.2) · `test_complete_creates_competencies` (III.3) | Unit + Integration | ✅ Live / ⬜ Planned |
| US-06-05 | AC1 sign-off | `TestSignoffCompetency` (III.2) | Unit | ✅ Live |
| US-06-06 | AC milestone | `TestScheduler` (III.2) | Unit (cron) | ⬜ Planned |
| US-06-07 | AC active/expired | `TestUserAuthorization` (III.2) · `test_check_user_authorization_*` (III.6) | Unit + API | ⬜ Planned |
| US-06-08 | AC Class III | `TestOperatorCoverage` (III.2) · `test_coverage_class3_*` (III.6) | Unit + API | ⬜ Planned |
| US-06-09 | AC recert | `TestRecertDue` (III.2) | Integration | ⬜ Planned |
| US-06-10 | AC VR-08 | `TestRevokeWithCapa` (III.2) · `test_revoke_incident_no_capa` (III.6) | Unit + API | ⬜ Planned |
| US-06-11 | AC own only | `test_list_competencies_as_operator` (III.6) | API + E2E | ⬜ Planned |
| US-06-12 | AC KPI | `test_get_dashboard_stats` (III.6) | API + E2E | ⬜ Planned |

**DoD**: mọi US có ≥ 1 dòng (đạt). Cột Status không trống (đạt).

## IV.2. BR → Test mapping

| BR ID | Phát biểu (rút gọn) | Test ID | Kỹ thuật | Happy / Negative |
|---|---|---|---|---|
| BR-06-01 | Authorization gate | `TestUserAuthorization` | Decision Table | 1 / 3 ⬜ |
| BR-06-02 | Instructor qualification (VR-04) | `test_session_validates_instructor` | EP | 1 / 1 ⬜ |
| BR-06-03 | Re-cert / Expired block | `TestScheduler` + `TestUserAuthorization` | State Transition | 1 / 1 ⬜ |
| BR-06-04 | Program change recert | `TestProgramRecert` | Decision Table | 1 / 1 ⬜ |
| BR-06-05 | Score+signoff trước Active (VR-06/07) | `TestComputeOverallResults` ✅ · `test_signoff_sets_expiry` | Decision Table | ✅ 5 / 0 · ⬜ |
| BR-06-06 | Revoke + CAPA (VR-08) | `TestRevokeWithCapa` | Decision Table | 2 / 1 ⬜ |
| BR-06-07 | Class III ≥2 operator | `TestOperatorCoverage` | BVA | 2 / 1 ⬜ |
| BR-06-08 | Audit trail | `test_audit_on_revoke` | Use Case | 1 / 0 ⬜ |
| BR-06-09 | No hard delete | `TestDeletePrevention` | EP | 0 / 3 ⬜ |
| BR-06-10 | Dept change | `handle_user_dept_change` test | Use Case | 1 / 0 ⬜ |
| BR-06-11 | 1 Active per model | `TestArchiveOldCompetency` ✅ | State Transition | ✅ 1 / 1 |
| BR-06-12 | Session Verified no cancel | `cancel_session` guard (III.4) | State Transition | 1 / 1 ⬜ |

**DoD**: mọi BR có ≥ 1 happy + ≥ 1 negative. BR Critical (BR-06-01) cần Decision Table đầy đủ — hiện ⬜ Planned.

## IV.3. Component → Test mapping

| Component (I.1) | Test ID | Test layer | Coverage % | Risk priority (I.3) |
|---|---|---|---|---|
| `validate_passing_score_range` | `TestValidatePassingScoreRange` | Unit | *(Cần khảo sát)* | High |
| `validate_validity_range` | `TestValidateValidityRange` | Unit | *(Cần khảo sát)* | High |
| `compute_overall_results` | `TestComputeOverallResults` | Unit | *(Cần khảo sát)* | High |
| `signoff_competency` | `TestSignoffCompetency` | Unit | *(Cần khảo sát)* | Critical |
| `archive_old_competency` | `TestArchiveOldCompetency` | Unit | *(Cần khảo sát)* | Critical |
| `validate_participant_scores` | `TestParticipantScoreRange` | Unit | *(Cần khảo sát)* | High |
| `enroll_participants`/`remove_participant` | `TestEnrollParticipants` | Integration | *(Cần khảo sát)* | High |
| `validate_user_authorized_for_asset` | `TestUserAuthorization` ⬜ | Unit + API | 0% (Planned) | Critical |
| `get_asset_operator_coverage` | `TestOperatorCoverage` ⬜ | Unit + API | 0% (Planned) | High |
| Competency Workflow (19 transition) | `test_imm06_workflow.py` ⬜ | Integration | 0% (Planned) | Critical |
| `revoke_competency_with_capa` | `TestRevokeWithCapa` ⬜ | Unit | 0% (Planned) | Critical |
| Audit chain | `test_imm06_audit.py` ⬜ | Integration | 0% (Planned) | High |

**DoD**: component Critical/High đạt coverage target III.10 — hiện một số Critical (#8, #14) còn ⬜ Planned, là gap.

---

# Phần V — UAT Script

## V.1. Phạm vi UAT

**In-scope:** Tạo Program + change control (BR-06-04); session lifecycle Planned→Closed (BR-06-02/05/12); auto-create competency + sign-off (BR-06-05); scheduler expiry 90/60/30 + auto-expire (BR-06-03); authorization gate IMM-08/09/12 (BR-06-01); operator coverage gate IMM-04 (BR-06-07); revoke + CAPA (BR-06-06); recertification (BR-06-03); self-service portal; dashboard KPI + Gap Report; permission matrix mỗi role; audit trail (BR-06-08/09).

**Out-of-scope:** Load testing (III.8), penetration testing (VI.10), LMS content delivery, e-signature số.

**Pre-condition:** UAT site `uat.assetcore.vn` deploy bản mới nhất; seed data `uat_imm06.py seed_data`; 7 tester accounts (V.2); Chrome ≥ 120 / Edge ≥ 120; scheduler enabled + MailHog.

## V.2. Tester accounts

| Username | Email | Role | Vai trò UAT |
|---|---|---|---|
| `qlcl.lead` | qlcl.lead@hospital.vn | Tổ HC-QLCL (Training Officer) | Tạo Program, Schedule, Revoke, Change Control |
| `biomed.eng` | biomed.eng@hospital.vn | Biomed Engineer | Instructor, complete session, chấm điểm |
| `ktv.optr1` | ktv.optr1@hospital.vn | HTM Technician / Operator | Tham gia training, self-service portal |
| `ktv.optr2` | ktv.optr2@hospital.vn | HTM Technician / Operator | Concurrent + permission isolation |
| `dept.mgr` | dept.mgr@hospital.vn | Department Manager | Sign-off competency khoa ICU |
| `workshop.head` | workshop.head@hospital.vn | Workshop Head | Verify session, gap report, escalation |
| `admin.cms` | admin.cms@hospital.vn | CMMS Admin | Override + full-access |

Mật khẩu UAT: `Assetcore@2026` (reset sau UAT). Đã có account role thấp (Operator) để cover FORBIDDEN case.

## V.3. Test data đã seed

| DocType | Số lượng | Ghi chú |
|---|---|---|
| IMM Device Model | 2 | `MDL-MON-PHILIPS-X3` (Class III), `MDL-INFUSION-BBRAUN` (Class II) |
| IMM Training Program | 3 | Initial/Refresher/Advanced cho MDL-MON-PHILIPS-X3 |
| IMM Training Session | 2 | 1 Planned (tương lai), 1 Completed (lịch sử) |
| IMM User Competency | 5 | Active ×2, Expiring ×1, Expired ×1, Revoked ×1 |
| AC Asset | 3 | 2 ICU (Class III), 1 ER (Class II) |
| AC Department | 2 | ICU, ER |
| CAPA stub | 1 | `CAPA-2026-0001` (cho VR-08 test) |

Reset script: `bench --site uat.assetcore.local execute assetcore.scripts.uat.uat_imm06.seed_data`.

## V.4. UAT Scenarios — Suy ra từ US + Activity

Mỗi scenario theo template §Phụ lục A. ID `UAT-IMM-06-NN`.

**Bảng tổng:**

| ID | Actor | Pre-condition | US/BR cover | Kỹ thuật | Kết quả mong đợi |
|---|---|---|---|---|---|
| UAT-IMM-06-01 | Tổ HC-QLCL | seed Program | US-06-01, BR-06-02, VR-02 | Use Case happy + neg | Program saved + VR-02 reject score=0 |
| UAT-IMM-06-02 | QLCL→Biomed→Workshop Head | seed session | US-06-02/03, BR-06-02/05/12 | State Transition | Session Planned→Closed đủ 6 state |
| UAT-IMM-06-03 | Biomed→Dept Manager | session In Progress | US-06-04/05, BR-06-05 | Use Case + permission | 3 competency Active, expiry đúng, wrong-dept FORBIDDEN |
| UAT-IMM-06-04 | System/QA | competency Active | US-06-07, BR-06-01 | Decision Table | authorize allow/block đúng trạng thái + cache |
| UAT-IMM-06-05 | System/QA | Class III asset | US-06-08, BR-06-07 | BVA | gate_pass=false khi 1 op, true khi 2 op |
| UAT-IMM-06-06 | System | competency near expiry | US-06-06, BR-06-03 | Use Case (cron) | Expiring đúng mốc, idempotent, auto-expire |
| UAT-IMM-06-07 | Tổ HC-QLCL | competency Active | US-06-10, BR-06-06, VR-08 | Decision Table | revoke ok; VR-08 block thiếu CAPA |
| UAT-IMM-06-08 | Tổ HC-QLCL | Program 3 Active users | BR-06-04, US-06-01 | Decision Table | critical field → recert flag 3 users |
| UAT-IMM-06-09 | HTM Technician ×2 | seed competency | US-06-11 | EP permission | Operator chỉ thấy competency mình; cross-user FORBIDDEN |
| UAT-IMM-06-10 | CMMS Admin | competency các state | BR-06-09 | EP | mọi delete bị block kể cả Admin |
| UAT-IMM-06-11 | Workshop Head | seed gap data | US-06-12 | Use Case | dashboard KPI + gap matrix drill-down |
| UAT-IMM-06-12 | CMMS Admin/QA | sau mutation | BR-06-08 | Use Case | audit trail entry + chain không tamper được |

Chi tiết từng scenario (steps) giữ ở phiên bản chi tiết bên dưới phần này khi cần — mỗi US có ≥1 happy; mỗi activity branch ngoại lệ ≥1; mỗi role mutate ≥1 permission verify; terminal transition ≥1 audit verify; ≥1 negative per BR Critical.

### UAT-IMM-06-01 — Tạo Training Program (Happy Path)

**Liên kết**: US-06-01, BR-06-02, VR-02
**Role tester**: Tổ HC-QLCL
**Kỹ thuật áp dụng**: Use Case happy + EP negative
**Mục tiêu**: Tạo Program hợp lệ, kiểm naming series + defaults; VR-02 reject.
**Pre-condition**: Device Model MDL-MON-PHILIPS-X3 active.

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | `qlcl.lead` mở form tạo Program | Form hiển thị | ☐ |
| 2 | Điền program_code, target_device_model, training_type=Initial, validity=24 | — | ☐ |
| 3 | assessment_method=Both, passing_score=70, instructor_qualification=Biomed | — | ☐ |
| 4 | Lưu | Program saved, is_active=1 | ☐ |
| 5 | Tạo Program với passing_score=0 | Lỗi VR-02 "Điểm đạt phải trong khoảng 1-100" | ☐ |

**Post-condition**: 1 Program mới active.
**Acceptance**: Tất cả step Pass + audit trail có entry tương ứng.

### UAT-IMM-06-07 — Revoke Competency + CAPA (VR-08)

**Liên kết**: US-06-10, BR-06-06, VR-08
**Role tester**: Tổ HC-QLCL
**Kỹ thuật áp dụng**: Decision Table (reason keyword × CAPA presence)
**Mục tiêu**: Revoke đúng flow; VR-08 block khi reason chứa keyword sự cố mà thiếu CAPA.
**Pre-condition**: 1 competency Active của `ktv.optr1`; CAPA-2026-0001 tồn tại.

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | Revoke reason="Vi phạm quy trình" (no keyword), no CAPA | Pass → Revoked | ☐ |
| 2 | Revoke reason="Liên quan sự cố vận hành", no CAPA | Lỗi VR-08 | ☐ |
| 3 | Điền capa_ref=CAPA-2026-0001, revoke | Pass | ☐ |
| 4 | `check_user_authorization` sau revoke | `authorized=false` (cache invalidated) | ☐ |
| 5 | IMM Audit Trail action REVOKE + metadata | Entry tồn tại | ☐ |

**Post-condition**: competency Revoked, audit entry.
**Acceptance**: Tất cả step Pass + audit trail có entry.

## V.5. Tổng hợp kết quả & Bug found

| Scenario | Status | Tester | Ngày | Ghi chú |
|---|---|---|---|---|
| UAT-IMM-06-01 | ☐ Pass / ☐ Fail / ☐ Block | | | |
| UAT-IMM-06-02 | ☐ Pass / ☐ Fail / ☐ Block | | | |
| UAT-IMM-06-03 | ☐ Pass / ☐ Fail / ☐ Block | | | |
| UAT-IMM-06-04 | ☐ Pass / ☐ Fail / ☐ Block | | | |
| UAT-IMM-06-05 | ☐ Pass / ☐ Fail / ☐ Block | | | |
| UAT-IMM-06-06 | ☐ Pass / ☐ Fail / ☐ Block | | | |
| UAT-IMM-06-07 | ☐ Pass / ☐ Fail / ☐ Block | | | |
| UAT-IMM-06-08 | ☐ Pass / ☐ Fail / ☐ Block | | | |
| UAT-IMM-06-09 | ☐ Pass / ☐ Fail / ☐ Block | | | |
| UAT-IMM-06-10 | ☐ Pass / ☐ Fail / ☐ Block | | | |
| UAT-IMM-06-11 | ☐ Pass / ☐ Fail / ☐ Block | | | |
| UAT-IMM-06-12 | ☐ Pass / ☐ Fail / ☐ Block | | | |

**Bug list:**

| Issue ID | Severity | Mô tả | Fix status |
|---|---|---|---|
| (điền khi phát sinh) | Blocker/Major/Minor/Trivial | | |

**Acceptance:** ≥ 95% PASS, Blocker = 0, Major ≤ 2 (có workaround documented).

**Sign-off:**

| Vai trò | Người | Ngày | Chữ ký |
|---|---|---|---|
| BA Lead | | | |
| QA Lead | | | |
| Module Owner (Tổ HC-QLCL Lead) | | | |
| Đại diện end-user (Workshop Head) | | | |

---

# Phần VI — Security Review (gate)

## VI.1. RBAC

**Role definitions** — `fixtures/role.json` + `role_profile.json`. Role liên quan IMM-06:

| Role | Quyền trên Training / Competency |
|---|---|
| Tổ HC-QLCL (Training Officer) / Training Manager | Full — Create, Read, Write, Cancel, Revoke |
| Workshop Head | Read, Write (Verify Session, Sign-off, Suspend) |
| Biomed Engineer | Read/Write Session (instructor), Read Competency |
| Department Manager / Commissioning Manager / PM Manager | Read, Write (Sign-off) |
| HTM Technician / Operator | Read (own competency only) |
| CMMS Admin / AssetCore Super Admin | Full (incl. workflow auto-transition) |

**DocPerm matrix — `IMM User Competency`** (Decision Table: role × action → Allow/Deny):

| Role | Read | Write | Create | Submit | Cancel | Delete |
|---|---|---|---|---|---|---|
| Tổ HC-QLCL / Training Manager | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| Workshop Head | ✅ | ✅ (Suspend) | ❌ | ❌ | ❌ | ❌ |
| Department Manager | ✅ (own dept) | ✅ (sign-off own) | ❌ | ❌ | ❌ | ❌ |
| Biomed Engineer | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| HTM Technician / Operator | ✅ (own) | ❌ | ❌ | ❌ | ❌ | ❌ |
| CMMS Admin | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |

**DocPerm matrix — `IMM Training Session`:**

| Role | Read | Write | Create | Submit | Cancel |
|---|---|---|---|---|---|
| Tổ HC-QLCL | ✅ | ✅ | ✅ | ✅ | ✅ |
| Biomed Engineer | ✅ | ✅ (if instructor) | ✅ | ✅ | ❌ |
| Workshop Head | ✅ | ✅ (Verify) | ❌ | ❌ | ❌ |
| HTM Technician | ✅ (own session) | ✅ (own session) | ✅ | ❌ | ❌ |
| Operator | ✅ (own) | ❌ | ❌ | ❌ | ❌ |

**Field-level permission (permlevel ≠ 0 cho field nhạy cảm):**

| Field | permlevel | Mô tả |
|---|---|---|
| `revoke_reason` | 1 — Tổ HC-QLCL+ | Lý do thu hồi nhạy cảm |
| `revoke_capa_ref` | 1 — Tổ HC-QLCL+ | CAPA reference |
| `supervisor_signoff` | 1 — Workshop Head+ | Ký tên cấp trên |
| `last_assessment_score` | 0 — all authenticated | Điểm đánh giá |

**User Permission (row-level):** Operator/HTM Technician chỉ thấy competency `user = session_user`; Department Manager chỉ own dept. *(Cần khảo sát: `permission_query_conditions` cho `IMM User Competency` CHƯA tồn tại trong `assetcore/permissions.py` tại thời điểm rà soát — cần implement hàm `user_competency_query` + đăng ký trong `hooks.py::permission_query_conditions`. Đây là GAP an ninh cần đóng trước go-live.)*

## VI.2. API security

| Mục | Trạng thái | Ghi chú |
|---|---|---|
| Whitelist hygiene | ✅ | 25 `@frappe.whitelist()` có docstring + role check; mutating dùng `methods=["POST"]` |
| CSRF | ✅ | Frappe default X-Frappe-CSRF-Token |
| Input validation | ✅ | `name`/Link field validate qua `frappe.get_value` trước khi dùng |
| SQL injection | ✅ | Frappe ORM parameterized; không raw f-string SQL trong imm06.py |
| Rate limit `check_user_authorization` | ⚠️ Roadmap | Cached nhưng chưa rate-limit external caller |
| Rate limit `create_program` / `complete_session` | ⚠️ Roadmap | Cần cấu hình cho batch |

## VI.3. Audit trail integrity

- Mọi mutation (sign-off/revoke/suspend/auto-expire) sinh `IMM Audit Trail` qua `_log_competency_audit()`.
- Hash chain SHA-256: `hash = SHA256(prev_hash + canonical_json(event))`.
- Verify endpoint: `verify_audit_chain(asset)` → bool. Test tamper: III.5 (b).
- User KHÔNG có quyền edit/delete `IMM Audit Trail` (không trong DocPerm bất kỳ role — ISO 13485:7.5.9).
- Retention ≥ 10 năm sau user nghỉ việc (NĐ98 §35).

→ III.5 test cases.

## VI.4. Authentication & session

| Hạng mục | Config |
|---|---|
| Login | Frappe default — username + password |
| Session timeout | 8 giờ (`frappe.conf.session_expiry`) |
| Lockout | 3 lần fail → lock 15 phút |
| Password policy | ≥ 8 ký tự, 1 chữ hoa, 1 số |
| API key | Per-user, rotate 90 ngày; không commit git |
| 2FA | Roadmap Phase 2 — TOTP via Frappe 2FA |

## VI.5. Data sensitivity

| Loại | Trường | Sensitivity | Bảo vệ |
|---|---|---|---|
| Điểm đánh giá | `theory_score`, `practical_score`, `last_assessment_score` | Internal | Role permission |
| Lý do thu hồi | `revoke_reason` | Confidential | permlevel 1 |
| Chứng nhận PDF | `certificate_file` | Internal | Role permission (R own only) |
| Thông tin user | `user`, `supervisor_signoff` | Internal | Row-level permission |
| Dữ liệu bệnh nhân | Không lưu | N/A | IMM-06 KHÔNG lưu patient data |

## VI.6. Vendor isolation

Vendor External (`Vendor Engineer`) KHÔNG có quyền trên bất kỳ Training/Competency DocType nào. Training IMM-06 dành cho **nhân sự nội bộ** — vendor training quản lý qua `AC Authorized Technician` (IMM-03), tách biệt hoàn toàn. Vendor KHÔNG thấy chi phí, internal note, audit trail, dashboard; KHÔNG export.

→ test case ở III.6 (low-role API call test).

## VI.7. Secrets management

- `site_config.json` không commit git (`.gitignore`).
- Email notification token lưu `frappe.conf`, không hardcode.
- Backup encrypt at-rest; off-site S3 theo `08_Deployment §I.2b`.
- Secret scan CI: `detect-secrets` pre-commit hook.

## VI.8. Logging & monitoring

| Sự kiện | Log level | Where | Alert? |
|---|---|---|---|
| Competency auto-expired (batch) | WARNING | `frappe.log_error` + Audit Trail | ✅ Email Workshop Head |
| Competency revoked | WARNING | `IMM Audit Trail` + frappe log | ✅ Email Workshop Head |
| Authorization gate denied (WO assign) | INFO | Frappe access log | ❌ |
| Audit chain tamper detected | ERROR | `frappe.log_error` | ✅ Email CMMS Admin |
| Gap report violation (Class III) | WARNING | Gap Report record + email | ✅ Email Workshop Head + VP Block2 |
| Login fail | INFO | Frappe login log | ✅ (sau 3 lần) |
| PII / token trong log | ❌ | Policy: KHÔNG log patient data / token | — |

## VI.9. Threat model (STRIDE-lite)

| Threat | Vector | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| **S**poofing — session KTV | Giả mạo session user | Low | High | Session cookie HttpOnly + SameSite; Frappe session verify |
| **T**ampering — Audit Trail | Sửa IMM Audit Trail trực tiếp | Low | Critical | DocPerm no-delete; verify chain endpoint; test tamper III.5 |
| **R**epudiation — Sign-off | Supervisor phủ nhận đã duyệt | Low | High | IMM Audit Trail + chain hash + `supervisor_signoff` field |
| **I**nfo Disclosure — Điểm thi | Operator xem điểm/competency người khác | Medium | Medium | Row-level permission (CẦN implement query — VI.1) + test UAT-IMM-06-09 |
| **D**enial of Service — Scheduler | Gap report quá nhiều competency (50k) | Low | Medium | Batch 200/run; index `(status, expiry_date)` |
| **E**levation of privilege — Revoke bypass | Low-role gọi `revoke_competency` bypass VR-08 | Low | High | VR-08 enforce tại service layer + whitelist role check |

## VI.10. Penetration test

Trước release đầu tiên (go-live bệnh viện): Burp/OWASP ZAP scan trên `uat.assetcore.vn` (0 High/Critical open); sqlmap (mode safe) trên `create_program`, `revoke_competency`; CSRF test bằng curl không token; role escalation (`revoke_competency` role HTM Technician → 403); authorization gate bypass test. Report lưu `docs/security/pentest_imm06_v1.md`.

## VI.11. Sign-off

| Role | Người | Ngày | Quyết định |
|---|---|---|---|
| QA Lead | | | ☐ Pass / ☐ Pass with conditions / ☐ Fail |
| Tech Lead / Security Officer | | | ☐ Pass / ☐ Pass with conditions / ☐ Fail |
| Module Owner (Tổ HC-QLCL Lead) | | | ☐ Pass / ☐ Pass with conditions / ☐ Fail |

**Điều kiện go-live:** Tất cả Sign-off Pass hoặc Pass with conditions (workaround documented). Lưu ý GAP row-level permission VI.1 phải đóng trước.

---

# Phần VII — Code Quality

## VII.1. Tool matrix

| Tool | Mục tiêu | Target | Cadence |
|---|---|---|---|
| **SonarQube** (BE Python) | Bug 0 Critical, code smell ≤ 5, duplication ≤ 3%, coverage ≥ 70%, security hotspot review 100% | Quality Gate pass | Mỗi PR (CI gate) |
| **Lighthouse** (FE — Training Dashboard) | Performance ≥ 90, Accessibility ≥ 95, Best Practices ≥ 90, SEO ≥ 80 | ≥ target | Mỗi release + monthly |
| **ESLint + vue-tsc** (FE) | 0 error, 0 warning prod build | pass | Mỗi PR FE (CI gate) |
| **ruff / black** (BE) | 0 error, format PEP8 | pass | Mỗi PR (CI gate) |
| **Bundle size** (FE chunk imm06) | main ≤ 250 KB gzip, async ≤ 80 KB gzip | ≤ budget | Mỗi PR FE (CI report) |

## VII.2. Cadence

- SonarQube: mỗi PR (CI gate, fail nếu Quality Gate fail)
- Lighthouse: mỗi release lớn + monthly audit
- ESLint / ruff: mỗi PR (CI gate)
- Bundle size: mỗi PR FE (CI report, fail nếu vượt budget)

Gắn screenshot SonarQube + Lighthouse vào file 09 §Release Notes khi báo cáo final.

---

# Phụ lục A — Template per UAT scenario

```markdown
### UAT-IMM-06-<NN> — <Tên>

**Liên kết**: US-<NN>, AC<N>, BR-<NN>, ACT-<NN>
**Role tester**: <…>
**Kỹ thuật áp dụng**: Use Case happy / Use Case alt / EP permission / State Transition
**Mục tiêu**: <1 câu>
**Pre-condition**: <data state cần có>

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | <…> | <…> | ☐ |
| 2 | <…> | <…> | ☐ |

**Post-condition**: <data state sau khi pass>
**Acceptance**: Tất cả step Pass + audit trail có entry tương ứng.
```

# Phụ lục B — Template per Test Case (unit/integration/API)

```markdown
### TC-IMM-06-<LAYER>-<NN> — <Tên>

**Component (I.1)**: <…>
**Liên kết**: US-<NN> | BR-<NN> | ACT-<NN>
**Kỹ thuật (II.1/II.2)**: BVA boundary `passing_score_pct=0`
**Priority (I.3)**: Critical / High / Medium / Low
**Test type**: Unit / Integration / API / E2E
**Pre-condition**: <fixture / state setup>

**Input**:
- <field>: <value>

**Steps**:
1. <…>
2. <…>

**Expected**:
- ServiceError(code=VALIDATION, message contains "VR-02")
- doc.workflow_state unchanged

**Post-condition**: <DB rollback / fixture cleanup>
```

# Phụ lục C — Workflow State Transition Test template

```markdown
### TC-IMM-06-WF-<NN> — <action>: <from> → <to>

**Workflow JSON**: `assetcore/assetcore/workflow/imm_06_competency_workflow.json`
**Role required**: <…>
**Pre-condition**: doc.workflow_state = <from>, gate <Gx> đã pass
**Action**: apply_workflow(doc, "<action>")
**Expected (happy)**: doc.workflow_state = <to>, docstatus = <…>, audit entry created
**Expected (negative role)**: PermissionError / FORBIDDEN
**Expected (gate fail)**: ServiceError(code=BUSINESS_RULE, message contains "<Gx>")
```

---

# DoD — File 07 hoàn chỉnh

## I. Test Analysis
- [x] I.1 Component Inventory liệt kê đủ artefact (so với 04/05/06)
- [x] I.2 mỗi US / BR / Activity có ≥ 1 dòng map
- [x] I.3 Risk priority gán cho mọi component (không trống)
- [x] I.4 Scope ghi rõ out-of-scope kèm lý do

## II. Test Design Techniques
- [x] II.1 chọn ≥ 4 black-box techniques (EP + BVA + Decision Table + State Transition)
- [x] II.2 white-box criteria xác định (statement + branch)
- [x] II.3 mapping component → kỹ thuật điền đầy đủ

## III. Test Plan
- [x] Test class structure cho mọi service public function (I.1)
- [x] ≥ 1 happy + 1 negative test mỗi function (định nghĩa); một phần ⬜ Planned chưa viết code
- [x] Workflow transitions cover 100% (đếm = JSON: 19 competency + 6 session lifecycle)
- [ ] Audit chain test (intact + tampered) — ⬜ Planned, chưa viết `test_imm06_audit.py`
- [ ] API test ≥ 60% coverage + permission matrix — ⬜ Planned, chưa viết `test_imm06_api.py`
- [x] Performance target xác định
- [x] CI command chạy clean (`bench run-tests --module assetcore.tests.test_imm06`)
- [ ] SonarQube Quality Gate pass + Lighthouse ≥ target — chưa chạy đo

## IV. Traceability
- [x] IV.1 US → Test: mọi US có ≥ 1 Test ID
- [x] IV.2 BR → Test: mọi BR có happy + negative (một phần ⬜ Planned)
- [ ] IV.3 Component → Test: Critical/High đạt coverage target III.10 — một số Critical (#8 workflow, #14 authorization) còn ⬜ Planned

## V. UAT
- [x] Mỗi US có ≥ 1 UAT scenario
- [x] ≥ 1 negative + permission + audit verify scenario
- [x] Test data seed script đề cập (`uat_imm06.py`) — *(tồn tại file cần khảo sát)*
- [x] Tester accounts đã định nghĩa (đủ role, không chỉ Admin)
- [x] Sign-off section sẵn sàng

## VI. Security
- [x] DocPerm matrix đầy đủ (Decision Table) cho Session + Competency
- [x] Mọi field nhạy cảm có permlevel ≠ 0
- [ ] SQL injection + CSRF test pass — ⬜ Planned (pentest VI.10)
- [ ] Audit chain test pass (intact + tampered) — ⬜ Planned (III.5)
- [ ] Vendor isolation test pass (low-role API call) — ⬜ Planned
- [x] Threat model đủ 6 STRIDE với mitigation
- [ ] Row-level `permission_query_conditions` cho IMM User Competency — GAP, chưa có trong `permissions.py`
- [ ] Sign-off đầy đủ trước go-live

## VII. Code Quality
- [ ] SonarQube Quality Gate pass — chưa chạy
- [ ] Lighthouse ≥ target — chưa chạy
- [ ] Bundle size ≤ budget — chưa đo
- [ ] Screenshot báo cáo gắn vào file 09 — pending release
