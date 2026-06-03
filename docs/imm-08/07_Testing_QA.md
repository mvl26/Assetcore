# 07 — Kiểm thử & An ninh (Testing & QA & Security)

| Mục | Giá trị |
|---|---|
| Module | IMM-08 — Bảo trì Định kỳ (Preventive Maintenance) |
| Phạm vi | Per-module |
| Owner | QA Lead + Security Officer |
| Liên kết | 02 Analysis (US, BR, Activity, BPMN) · 03 Diagrams · 04 Backend · 05 API · 06 Frontend |

> **Mục đích**: Suy ra test case **có hệ thống** từ phân tích (file 02) bằng kỹ thuật black-box + white-box, không liệt kê tự phát. Bao gồm: phân tích đối tượng test → chọn kỹ thuật → viết test → traceability → UAT → security → code quality. Phần VI là gate go-live.

---

# Phần I — Test Analysis (Phân tích đối tượng test)

> Mục tiêu Phần I: trả lời 4 câu hỏi trước khi viết test case: **(1) test cái gì** (component inventory) **(2) suy ra từ đâu** (US/BR/Activity) **(3) ưu tiên cái nào** (risk) **(4) loại trừ cái nào** (out-of-scope).

## I.1. Component Inventory — Liệt kê phần mềm cần test

Toàn bộ artefact test được của module IMM-08. Mỗi dòng → ≥ 1 test class ở Phần III (→ 04 Backend §DocType/§Service · 05 API §Catalog · 06 Frontend §Components).

| # | Component | Loại | File / Tên | Test layer áp dụng |
|---|---|---|---|---|
| 1 | PM Work Order | DocType | `pm_work_order/pm_work_order.json` | Integration (lifecycle) |
| 2 | PM Schedule | DocType | `pm_schedule/pm_schedule.json` | Integration (lifecycle) |
| 3 | PM Checklist Template | DocType | `pm_checklist_template/pm_checklist_template.json` | Integration (versioning) |
| 4 | PM Task Log | DocType | `pm_task_log/pm_task_log.json` (`in_create=1`) | Integration (immutability) |
| 5 | PM Checklist Item / Result | Child DocType | `pm_checklist_item` · `pm_checklist_result` | Integration (clone từ template) |
| 6 | Workflow PM Work Order | Workflow | `workflow/imm_08_pm_workflow.json` (7 states, 13 transitions) | Integration (state transition) |
| 7 | Completion gate | Validator (controller) | `doctype/pm_work_order/pm_work_order.py::validate` → `services/imm08.py::validate_work_order` | Unit (Decision Table) |
| 8 | `validate_work_order` | Service validator | `services/imm08.py::validate_work_order` (BR-08-08/09/10/06/02) | Unit (BVA/EP/Decision Table) |
| 9 | `handle_work_order_submit` | Service function | `services/imm08.py::handle_work_order_submit` | Unit + Integration |
| 10 | `_create_cm_wo_from_failure` | Service function | `services/imm08.py::_create_cm_wo_from_failure` (BR-08-09) | Unit (cross-module → IMM-09) |
| 11 | `generate_pm_work_orders_from_schedule` | Scheduler job | `services/imm08.py::generate_pm_work_orders_from_schedule` | Unit + Cron simulation |
| 12 | `backfill_pm_schedules_for_due_assets` | Scheduler job | `services/imm08.py::backfill_pm_schedules_for_due_assets` | Unit + Cron simulation |
| 13 | `count_overdue_pm` | Service function | `services/imm08.py::count_overdue_pm` | Unit |
| 13a | `is_pm_overdue` (overdue SoT, BR-08-11) | Pure predicate | `services/imm08.py::is_pm_overdue` | Unit (BVA boundary) |
| 13b | `due_soon_filter` (due-soon window SoT, BR-08-12) | Pure filter builder | `services/imm08.py::due_soon_filter` | Unit + convergence (KPI==drill) |
| 14 | `update_pm_schedule_after_completion` | Service function | `services/imm08.py::update_pm_schedule_after_completion` (BR-08-03) | Unit (BVA date) |
| 15 | `assign_technician` / `submit_result` / `report_major_failure` / `reschedule` | Service function | `services/imm08.py` | API integration |
| 16 | `create_schedule` / `update_schedule` / `set_schedule_status` / `delete_schedule` | Service (CRUD) | `services/imm08.py` | API integration |
| 17 | `create_template` / `approve_template` / `version_template` / `apply_template_to_category_assets` | Service (template) | `services/imm08.py` | API integration |
| 18 | `create_pm_schedule_from_commissioning` | Lifecycle hook | `services/imm08.py::create_pm_schedule_from_commissioning` (IMM-04 → IMM-08) | Integration (audit chain) |
| 19 | API endpoints (23) | API endpoint | `api/imm08.py::*` | API integration |
| 20 | IMM Audit Trail | Lifecycle event | `hooks → lifecycle.log_audit_event` | Integration (audit chain) |
| 21 | PMDashboardView / PMCalendarView | FE view | `frontend/src/views/...` *(Cần khảo sát đường dẫn)* | E2E (Playwright) |

## I.2. Trace nguồn test — User Stories, Activity Flows, Business Rules

3 bảng dẫn từ artefact phân tích (file 02) sang test layer (→ 02 §Functional Specs · 02 §Business Rules · 02 §Activity Diagram per UC).

### I.2.a. Từ User Story
| US ID | Tiêu đề ngắn | Acceptance Criteria # | Test layer dự kiến |
|---|---|---|---|
| US-08-01 | Scheduler tự động tạo PM WO | AC1 (happy due), AC2 (idempotent) | Unit + Cron + UAT |
| US-08-02 | Submit PM Result (happy) | AC1, AC2 | Unit + API + UAT |
| US-08-03 | Major Failure → Asset Out of Service | AC1 (happy), AC2 (email khẩn) | Unit + API + UAT |
| US-08-04 | Check Overdue + escalation email | AC1 | Cron + UAT |
| US-08-06 | Phân công KTV + reschedule | AC1 | API + UAT |

### I.2.b. Từ Business Rule
| BR ID | Phát biểu | Component liên quan (I.1) | Kỹ thuật test phù hợp |
|---|---|---|---|
| BR-08-01 | Phải có Checklist Template trước khi tạo PM WO | `generate_pm_work_orders_from_schedule` (skip + email) | Decision Table / EP |
| BR-08-02 | CM WO phải có `source_pm_wo` | `validate_work_order` | Decision Table |
| BR-08-03 | `next_pm_date = completion_date + interval` (KHÔNG dùng due_date) | `update_pm_schedule_after_completion` | BVA (date) |
| BR-08-04 | Asset Out of Service → block tạo PM WO | scheduler skip | EP (status partition) |
| BR-08-05 | `is_late = completion_date > due_date` | `handle_work_order_submit` | BVA (date boundary) |
| BR-08-06 | Class III/C/D bắt buộc ảnh trước/sau PM | `validate_work_order` | Decision Table / EP |
| BR-08-07 | Mỗi pm_type là 1 PM Schedule riêng (naming `PMS-{asset}-{pm_type}`) | `create_schedule` | EP |
| BR-08-08 | Checklist 100% có result trước Submit | `validate_work_order` | BVA (coverage 99% vs 100%) |
| BR-08-09 | Fail-Minor → CM Medium; Fail-Major → CM Critical + Out of Service | `_create_cm_wo_from_failure` | Decision Table |
| BR-08-10 | PM Task Log immutable (`in_create=1`, no write/delete perm) | PM Task Log DocPerm | EP + Error guessing |

### I.2.c. Từ Activity Flow / BPMN
| Activity ID | Use Case | Branch chính | Branch ngoại lệ |
|---|---|---|---|
| UC-09 | Auto-create PM WO | Tạo WO khi đến hạn | Skip + email Admin (BR-08-01) · Skip Out of Service (BR-08-04) |
| UC-03 | Submit PM Result | All Pass → Completed | Block checklist <100% (BR-08-08) · Block Class III no photo (BR-08-06) |
| UC-04 | Report Major Failure | Halted + CM Critical + Out of Service | Email khẩn (US-08-03 AC2) |
| UC-10 | Check Overdue | Đánh dấu Overdue + escalation email | < 7d / 8-30d / > 30d tier khác nhau (BR-08-05) |
| UC-02 | Phân công KTV / Reschedule | Open → In Progress | Reschedule reason < 5 ký tự → block (VR-08-09) |

## I.3. Risk-based Priority

| Component (I.1) | Likelihood (1-5) | Impact (1-5) | Risk = L×I | Priority |
|---|---|---|---|---|
| Workflow PM Work Order (13 transitions) | 4 | 5 | 20 | **Critical** |
| Completion gate `validate_work_order` (BR-08-08/06/09/10) | 4 | 5 | 20 | **Critical** |
| `_create_cm_wo_from_failure` (Major → Out of Service, cross-module) | 3 | 5 | 15 | **Critical** |
| PM Task Log immutability (audit trail) | 2 | 5 | 10 | High |
| `generate_pm_work_orders_from_schedule` (idempotent) | 4 | 4 | 16 | **Critical** |
| `update_pm_schedule_after_completion` (BR-08-03) | 3 | 4 | 12 | High |
| `create_pm_schedule_from_commissioning` (IMM-04 hook) | 3 | 3 | 9 | Medium |
| Template versioning / approve | 2 | 3 | 6 | Medium |
| `get_dashboard_stats` / `get_calendar` (read-only) | 2 | 2 | 4 | Low |

**Quy ước priority**:
- **Critical** (R ≥ 15): test trước, fail = block release
- **High** (10 ≤ R < 15): bắt buộc trước go-live
- **Medium** (5 ≤ R < 10): trong sprint khi có thời gian
- **Low** (R < 5): chỉ test khi báo cáo bug

## I.4. Scope

- **In-scope**: completion gate (BR-08-08/06/09/10), workflow 13 transitions, scheduler idempotency (BR-08-01/04/07), PM Schedule advance (BR-08-03), Major Failure cross-module → IMM-09, PM Task Log immutability.
- **Out-of-scope**: Performance test (giao Phần III.8); Calibration WO (IMM-11); mobile offline sync; holiday-list integration; cross-module IMM-15 reporting (chỉ smoke ở Phần III.6).
- **Assumptions**: master data (Asset Category, AC Asset, Vendor) đã seed; tester accounts (PM Manager, PM User, AssetCore Auditor) đã tạo; Chrome/Edge ≥ 120.

---

# Phần II — Test Design Techniques (Kỹ thuật thiết kế test case)

> Mỗi test phải truy được về 1 kỹ thuật ở dưới.

## II.1. Black-box techniques

| Kỹ thuật | Khi nào dùng | Áp dụng vào IMM-08 | Số test sinh ra (rule of thumb) |
|---|---|---|---|
| **Equivalence Partitioning (EP)** | Input có miền giá trị chia nhóm tương đương | `status` (7 giá trị), `wo_type` (Preventive/Corrective), `overall_result`, Asset risk class (I/II/III) | 1 test/partition |
| **Boundary Value Analysis (BVA)** | Numeric / date / length field có biên | `reason` reschedule (≥ 5 ký tự), `duration_minutes` (> 0), `next_pm_date = completion + interval`, `is_late` boundary (completion == due) | 2-3 test/biên |
| **Decision Table** | Multi-condition gate, business rule kết hợp | Completion gate `validate_work_order` (checklist × photo × sticker × duration), Fail-Minor/Major routing (BR-08-09) | 2^N rút gọn theo equivalence |
| **State Transition Testing** | Workflow finite state machine | `imm_08_pm_workflow.json` (7 states, 13 transitions) | Mỗi transition + invalid transition |
| **Use Case Testing** | End-to-end actor flow | UAT scenarios, API integration test | 1/main + 1/alt + 1/exception |
| **Pairwise / Combinatorial** | Nhiều field optional kết hợp | Filter `list_pm_work_orders` (status × asset_ref × page) | Min set cover all pairs |
| **Error Guessing** | Lỗi từ kinh nghiệm: null, empty, race | Tất cả endpoint nhận user input; PM Task Log tamper | Bổ sung — không thay thế |

## II.2. White-box techniques

| Kỹ thuật | Áp dụng vào | Tiêu chí đạt | Công cụ |
|---|---|---|---|
| **Statement coverage** | Service functions ở I.1 (`services/imm08.py`) | ≥ 85% line | `coverage report` |
| **Branch / Decision coverage** | Functions có if/else, try/except (`submit_result`, `handle_work_order_submit`, scheduler) | ≥ 80% branch | `coverage --branch` |
| **Condition / MC/DC** | Completion gate `validate_work_order` (multi-AND BR-08-08/09/10) | Mỗi sub-condition kiểm soát outcome độc lập | Manual test design + coverage |
| **Path coverage** | `_create_cm_wo_from_failure` (Minor/Major path) | Toàn bộ path khả dĩ | Manual |

## II.3. Mapping Component → Kỹ thuật

| Loại component | Kỹ thuật chính | Kỹ thuật phụ |
|---|---|---|
| Completion gate (`validate_work_order`) | Decision Table | MC/DC |
| Workflow transition | State Transition | Use Case |
| Scheduler (`generate_*`, `backfill_*`) | Use Case (setup → run → assert) | Error guessing (idempotent, partial fail) |
| Service function CRUD | EP + Branch coverage | BVA |
| API endpoint | Use Case + EP | Pairwise (filter input) |
| PM Task Log immutability | EP (perm partition) | Error guessing (direct db.set_value) |
| FE view (Playwright) | Use Case end-to-end | Error guessing (network 4xx/5xx, role gate) |

---

# Phần III — Test Plan (Kế hoạch thực thi)

## III.1. Test Pyramid

```
                  ┌────────────┐
                  │  E2E / UAT │   ~5%  (Playwright; 1 Golden Scenario PM full lifecycle)
                 ─┴────────────┴─
              ┌──────────────────────┐
              │   API Integration    │   ~15% (23 endpoints, Frappe whitelist)
             ─┴──────────────────────┴─
          ┌────────────────────────────────┐
          │  Workflow + DocType lifecycle  │   ~25% (PM WO 13 transitions)
         ─┴────────────────────────────────┴─
      ┌────────────────────────────────────────────┐
      │         Unit — Service Layer               │   ~55% (controller + scheduler + gate)
     ─┴────────────────────────────────────────────┴─
```

TDD bắt buộc (→ CLAUDE.md §17). Mỗi BR-08-01..10 có ≥ 1 happy + 1 negative test.

> **Trạng thái thực tế (2026-05-29):** test code hợp nhất trong **một file** `assetcore/tests/test_imm08.py` (444 dòng). Các class **đã viết (✅ Live)**: `TestPMChecklistTemplate`, `TestPMSchedule`, `TestPMWorkOrder`, `TestPMBackfillAndSupervisor`, `TestPMCompletionGate`. Các class còn lại = **⬜ Planned** (Wave 2). Split sang nhiều file là mục tiêu refactor.

## III.2. Unit test — Service Layer

**File:** `assetcore/tests/test_imm08.py`

| Test class | Function cover | Kỹ thuật | Cases | Trạng thái |
|---|---|---|---|---|
| `TestPMChecklistTemplate` | `create_template`, naming series | EP | 3 (missing required, create ok, naming) | ✅ Live |
| `TestPMSchedule` | `create_schedule`, `set_schedule_status` | EP + BVA | 4 (missing, create, paused, invalid status) | ✅ Live |
| `TestPMWorkOrder` | WO create + schedule binding | EP + Error guessing | 5 (missing, not-found schedule, asset mismatch, create ok, paused schedule block) | ✅ Live |
| `TestPMBackfillAndSupervisor` | `backfill_pm_schedules_for_due_assets`, `list_work_orders`, `get_work_order` | EP + idempotent | 3 (create for due, skip active schedule, expose supervisor) | ✅ Live |
| `TestPMCompletionGate` | `validate_work_order` (BR-08-08/09/10) | Decision Table / MC/DC | 4 (checklist unrated, labor zero, sticker missing, all satisfied) | ✅ Live |
| `TestGeneratePMWorkOrders` | `generate_pm_work_orders_from_schedule` | Use Case + idempotent | happy(due), skip(Out of Service BR-08-04), skip(no template BR-08-01), idempotent | ⬜ Planned |
| `TestHandleFailures` | `_create_cm_wo_from_failure` | Decision Table | Fail-Minor → CM Medium + Active; Fail-Major → CM Critical + Out of Service (BR-08-09) | ⬜ Planned |
| `TestUpdatePMSchedule` | `update_pm_schedule_after_completion` | BVA (date) | next_due = completion + interval (BR-08-03), KHÔNG từ due_date | ⬜ Planned |
| `TestIsLate` | `handle_work_order_submit` | BVA boundary | completion ≤ due → is_late=False; completion > due → is_late=True (BR-08-05) | ⬜ Planned |
| `TestReschedule` | `reschedule` | BVA + EP | happy(reason ≥ 5), fail(reason < 5 VR-08-09), fail(wrong state BAD_STATE) | ⬜ Planned |

## III.3. Integration — DocType lifecycle

**File:** `assetcore/tests/test_imm08.py` (hợp nhất — xem ghi chú §III.1)

| Test | Setup | Action | Assert | Trạng thái |
|---|---|---|---|---|
| `test_create_pm_work_order_succeeds` | Asset Active + PM Schedule + template | WO create | WO Open, checklist clone | ✅ Live |
| `test_paused_schedule_blocks_wo_creation` | PM Schedule Paused | WO create | block | ✅ Live |
| `test_complete_succeeds_when_all_satisfied` | WO In Progress, checklist filled + sticker + labor | submit | Completed | ✅ Live |
| `test_on_submit_updates_pm_schedule` | WO Completed | `doc.submit()` | `next_due_date = completion + interval` (BR-08-03) | ⬜ Planned |
| `test_on_submit_creates_task_log` | WO valid all pass | `doc.submit()` | PM Task Log created | ⬜ Planned |
| `test_on_submit_fail_major_out_of_service` | WO Class III Fail-Major | `report_major_failure` | Asset Out of Service, CM WO Critical (BR-08-09) | ⬜ Planned |
| `test_audit_trail_immutable` | PM Task Log inserted | `frappe.db.set_value("PM Task Log", …)` | block (`in_create=1` + DocPerm no write) | ⬜ Planned |

## III.4. Integration — Workflow transitions

**File:** `assetcore/tests/test_imm08_workflow.py` *(⬜ Planned — hiện gộp trong `test_imm08.py`)*

Workflow `imm_08_pm_workflow.json`: **7 states, 13 transitions** (đếm: `python3 -c "import json; print(len(json.load(open('assetcore/assetcore/workflow/imm_08_pm_workflow.json'))['transitions']))"` → 13). **Bắt buộc** cover 100%.

States: Open, In Progress, Pending–Device Busy, Overdue, Halted–Major Failure, Completed (docstatus=1), Cancelled.

| # | Action | From → To | Role required | Test pass | Test fail (wrong role / gate) |
|---|---|---|---|---|---|
| 1 | Bắt đầu thực hiện | Open → In Progress | PM User | ⬜ | ⬜ |
| 2 | Đánh dấu trễ hạn | Open → Overdue | System Manager | ⬜ | ⬜ |
| 3 | Hủy phiếu | Open → Cancelled | System Manager | ⬜ | ⬜ |
| 4 | Hoàn thành PM | In Progress → Completed | PM User | ⬜ | ⬜ (gate BR-08-08/06) |
| 5 | Báo lỗi nghiêm trọng | In Progress → Halted–Major Failure | PM User | ⬜ | ⬜ |
| 6 | Thiết bị bận - hoãn | In Progress → Pending–Device Busy | PM User | ⬜ | ⬜ (reason < 5 VR-08-09) |
| 7 | Tiếp tục thực hiện | Pending–Device Busy → In Progress | PM User | ⬜ | ⬜ |
| 8 | Bắt đầu muộn | Overdue → In Progress | PM User | ⬜ | ⬜ |
| 9 | Tiếp tục sau xử lý | Halted–Major Failure → In Progress | System Manager | ⬜ | ⬜ |
| 10 | Hủy phiếu | In Progress → Cancelled | System Manager | ⬜ | ⬜ |
| 11 | Hủy phiếu | Pending–Device Busy → Cancelled | System Manager | ⬜ | ⬜ |
| 12 | Hủy phiếu | Overdue → Cancelled | System Manager | ⬜ | ⬜ |
| 13 | Hủy phiếu | Halted–Major Failure → Cancelled | System Manager | ⬜ | ⬜ |

**Kỹ thuật**: State Transition Testing — mỗi edge = 1 test pass + 1 test fail (wrong role / gate fail).

## III.5. Integration — Audit chain integrity

2 test chính:
- (a) Sau N mutation (create schedule → generate WO → assign → submit Completed), chain hash SHA-256 hợp lệ end-to-end: `verify_audit_chain(asset) == True`.
- (b) Khi 1 entry bị tamper (sửa `hash_sha256` / `change_summary`), verify endpoint trả `chain_broken=true`.

Bổ sung: PM Task Log immutable — `frappe.db.set_value("PM Task Log", name, ...)` sau create → raise (`in_create=1` + DocPerm no write). Trace → 04 Backend §Audit Trail · `IMM Audit Trail` DocType. Trạng thái: ⬜ Planned.

## III.6. API test

**File:** `assetcore/tests/test_imm08_api.py` *(⬜ Planned — một phần gộp trong `test_imm08.py`)*

| Test | Endpoint | Verify | Kỹ thuật |
|---|---|---|---|
| `test_list_pm_work_orders_pagination` | `api/imm08.list_pm_work_orders` | page=1, page_size=20, total ≥ 0 | Pairwise |
| `test_list_filter_status_open` | `list_pm_work_orders?filters={"status":"Open"}` | mọi row status == Open | EP |
| `test_get_existing_wo` | `get_pm_work_order` | `success=true`, checklist present | Use Case |
| `test_get_not_found` | `get_pm_work_order?name=FAKE` | `code=NOT_FOUND` | EP |
| `test_assign_technician_happy` | `assign_technician` | status==In Progress, assigned_to set | Use Case |
| `test_assign_technician_wrong_state` | `assign_technician` (Completed WO) | `code=BAD_STATE` | EP |
| `test_submit_pm_result_happy` | `submit_pm_result` (all Pass, Class II) | `success=true`, new_status=Completed | Use Case |
| `test_submit_pm_result_incomplete_checklist` | `submit_pm_result` (1 empty) | `code=VALIDATION` BR-08-08 | BVA |
| `test_submit_pm_result_class3_no_photo` | `submit_pm_result` (Class III no photo) | `code=VALIDATION` BR-08-06 | Decision Table |
| `test_report_major_failure` | `report_major_failure` | WO Halted, Asset Out of Service, CM WO created | Use Case |
| `test_reschedule_pm_short_reason` | `reschedule_pm` (reason="OK") | `code=VALIDATION` VR-08-09 | BVA |
| `test_get_dashboard_stats` | `get_pm_dashboard_stats?year=2026&month=4` | `compliance_rate_pct`, `overdue`, `trend` present | Use Case |
| `test_no_permission_low_role` | `assign_technician` (AssetCore System User) | `code=FORBIDDEN` (HTTP 403) | EP (permission partition) |
| `test_idempotent_submit` | `submit_pm_result` 2 lần | 2nd → `code=CONFLICT` "đã được Submit" | Error guessing |

Cover: happy + envelope `success=true`; invalid params → `INVALID_PARAMS`; no permission → `FORBIDDEN`; pagination boundaries; idempotent retry.

## III.7. E2E browser (Playwright)

Dùng cho flow UI khó cover bằng API: checklist mobile (one-item-per-screen), modal confirm Major Failure, workflow button visibility theo role, calendar event color, dashboard KPI render. Trace → `assetcore-test` skill Phần 2 (Playwright MCP recipes + R-1..R-9 data rules). Trạng thái: ⬜ Planned (`tests/e2e/test_imm08_golden.py`).

**Golden scenario:** Commissioning submit → PM Schedule tạo → scheduler `generate_pm_work_orders_from_schedule` → WO Open → PM Manager phân công PM User → PM User điền checklist (all Pass, attach photo nếu Class III) → submit → Completed → verify PM Schedule.next_due_date = completion + interval → PM Task Log immutable → Dashboard KPI cập nhật.

## III.8. Performance test

| Metric | Target | Method |
|---|---|---|
| `list_pm_work_orders` p95 (50k WO, page=20) | ≤ 300 ms (NFR-08-02) | k6 ramping 20 VU |
| `submit_pm_result` p95 | ≤ 1.5 s | k6 |
| `get_pm_dashboard_stats` p95 | ≤ 800 ms (NFR-08-03) | k6 |
| `report_major_failure` p95 | ≤ 2 s | k6 |
| `generate_pm_work_orders_from_schedule` (500 schedules) | ≤ 60 s | `time bench execute …` |
| Calendar view FE render (30 days, 50 events) | ≤ 1 s DOMContentLoaded | Lighthouse / Playwright |

## III.9. Test data & Fixtures

| Loại | Cách seed | File |
|---|---|---|
| Master data (Asset Category, AC Asset, Vendor) | `fixtures/*.json` (cài qua `bench migrate`) | `assetcore/fixtures/` |
| AC Asset (test) | `tests/fixtures/test_assets_pm.json` (4 assets: Class I, II, III, Out of Service) | `assetcore/tests/fixtures/` |
| PM Schedule | `tests/fixtures/test_pm_schedules.json` (4, gắn assets trên) | idem |
| PM Checklist Template | `tests/fixtures/test_pm_templates.json` (Class II + Class III) | idem |
| PM Work Order | `tests/fixtures/test_pm_work_orders.json` (Open, In Progress, Overdue, Completed, Halted) | idem |
| UAT seed | Python script `scripts/uat/uat_imm08.py` | `assetcore/scripts/uat/` |

UAT data dùng tên/mã thực tế VN. Backend test fixture mới dùng prefix `_Test` (→ `assetcore-test` R-0/R-1).

## III.10. Run commands & Coverage gate

```bash
# Module test (tất cả trong một file)
bench --site assetcore.local run-tests --app assetcore --module assetcore.tests.test_imm08
# Coverage
coverage run -m unittest assetcore.tests.test_imm08 && coverage report
# Full suite (CI)
bench --site assetcore.local run-tests --app assetcore --coverage
```

| Layer | Target coverage | Đo |
|---|---|---|
| Service (`services/imm08.py`) | ≥ 85% line + ≥ 80% branch | `coverage --branch` |
| DocType lifecycle | ≥ 70% | `coverage report` |
| API (`api/imm08.py`) | ≥ 60% | `coverage report` |
| Frontend (vue-tsc) | 0 error | `npm run build` |

Coverage % thực tế: *(Cần khảo sát — chạy `coverage report`)*. CI fail nếu test fail hoặc coverage < target.

---

# Phần IV — Traceability Matrices

> Mọi test ở Phần III phải xuất hiện ở **cả 3** bảng.

## IV.1. US → Test mapping

| US ID | AC | Test ID (III.x) | Layer | Status |
|---|---|---|---|---|
| US-08-01 | AC1 (happy due) | `TestGeneratePMWorkOrders::test_creates_wo_when_due` | Unit/Cron | ⬜ Planned |
| US-08-01 | AC2 (idempotent) | `TestGeneratePMWorkOrders::test_idempotent_no_duplicate` · `TestPMBackfillAndSupervisor::test_backfill_skips_asset_with_active_schedule` | Unit | ✅ Live (backfill) / ⬜ Planned (generate) |
| US-08-02 | AC1, AC2 | `TestPMCompletionGate::test_complete_succeeds_when_all_satisfied` · `test_submit_pm_result_happy` | Unit + API | ✅ Live (gate) / ⬜ Planned (API) |
| US-08-03 | AC1 | `TestHandleFailures` · `test_report_major_failure` | Unit + API | ⬜ Planned |
| US-08-04 | AC1 | `count_overdue_pm` + escalation test | Cron | ⬜ Planned |
| US-08-06 | AC1 | `TestReschedule` · `test_assign_technician_happy` | Unit + API | ⬜ Planned |

## IV.2. BR → Test mapping

| BR ID | Phát biểu (rút gọn) | Test ID | Kỹ thuật | Happy / Negative |
|---|---|---|---|---|
| BR-08-01 | Có template trước khi tạo WO | `TestGeneratePMWorkOrders` (skip + email) | Decision Table | 1 / 1 — ⬜ Planned |
| BR-08-02 | CM WO có `source_pm_wo` | `validate_work_order` test | Decision Table | 1 / 1 — ⬜ Planned |
| BR-08-03 | next_pm_date = completion + interval | `TestUpdatePMSchedule` | BVA | 1 / 1 — ⬜ Planned |
| BR-08-04 | Out of Service → skip WO | `test_skip_when_out_of_service` | EP | 1 / 1 — ⬜ Planned |
| BR-08-05 | is_late = completion > due | `TestIsLate` | BVA | 1 / 2 — ⬜ Planned |
| BR-08-06 | Class III bắt buộc ảnh | `test_submit_pm_result_class3_no_photo` | Decision Table | 1 / 1 — ⬜ Planned |
| BR-08-07 | Mỗi pm_type 1 schedule | `TestPMSchedule::test_create_schedule_succeeds` | EP | 1 / 1 — ✅ Live (create) |
| BR-08-08 | Checklist 100% trước Submit | `TestPMCompletionGate::test_complete_blocked_when_checklist_unrated` | BVA | 1 / 1 — ✅ Live |
| BR-08-09 | Fail-Minor/Major routing | `TestHandleFailures` | Decision Table | 1 / 1 — ⬜ Planned |
| BR-08-10 | PM Task Log immutable | `test_audit_trail_immutable` | EP + Error guessing | 1 / 1 — ⬜ Planned |
| BR-08-11 | Overdue SoT predicate `is_pm_overdue` (`due_date<today` + status∈source) | `TestPMOverdueSoT` (BVA boundary today-1/today) + `test_d_be_18` (drill route) | BVA | 1 / 2 — ✅ Live (predicate) |
| BR-08-12 | **Due-soon window SoT `due_soon_filter`** — KPI count == drill rows, disjoint với overdue | `TestPMDueSoonConvergence` + `test_d_be_18b` (convergence, KHÔNG còn superset comment) | BVA + Decision Table | 1 / 3 — 🔴 Vòng 23 |

Bổ sung gate đã Live: `test_complete_blocked_when_labor_zero` (BR-08-09 duration > 0), `test_complete_blocked_when_sticker_missing` (BR-08-10 sticker).

### IV.2.a Test mới vòng 23 — Due-soon convergence (BR-08-12)

> **Lưu ý AC reference.** Đề mục vòng 23 trỏ `test_dashboard.py::test_d_be_20 (dòng 551)` là chỗ "hợp-thức-hoá divergence" cho IMM-08 — **đính chính:** `test_d_be_20` (line 542-552) thực ra là phiên bản **IMM-11 calibration** (`list_schedules`, `next_due_date`, assert `>= kpi_due` superset). Phiên bản PM hiện tại là `test_d_be_18` (line 501-510), **chỉ assert drill *route* `?due_before=today+7`**, KHÔNG assert convergence → đây mới là chỗ ngầm hợp-thức-hoá. Test cần viết/sửa cho PM:

| Test ID | File | Assert | Trạng thái |
|---|---|---|---|
| `test_d_be_18b_pm_due_7d_kpi_equals_drill` | `test_dashboard.py` | `kpi.pm_due_7d == list_pm_work_orders({"due_before": today+7}).pagination.total` (card == drill byte-for-byte). Dataset gồm: 1 WO due hôm nay, 1 WO due today+7, 1 WO due today+8 (loại), 1 WO **quá hạn** today-1 (KHÔNG vào due-soon), 1 WO Completed due today (loại). | 🔴 Viết mới |
| `test_pm_due_soon_overdue_disjoint` | `test_imm08.py` | `_normalize_filters({"due_before": X})` sinh `due_date BETWEEN [today, X]` (KHÔNG `<=`); WO today-1 KHÔNG xuất hiện trong drill due-soon mà thuộc `count_overdue_pm`. Hai tập ∩ = ∅. | 🔴 Viết mới |
| `test_pm_due_soon_boundary` | `test_imm08.py` | BVA: due==today **IN**, due==today+7 **IN**, due==today+8 **OUT**, due==today-1 **OUT (overdue)**, Completed/Cancelled **OUT** bất kể due_date. | 🔴 Viết mới |

> Sửa `test_d_be_18` (hoặc giữ + thêm `test_d_be_18b`): KHÔNG còn comment/assert hợp-thức-hoá superset cho PM due-soon. Grep guard QA: `grep -n "due_date.*<=.*due_before\|between.*today_str.*next7" assetcore/services/imm08.py assetcore/api/dashboard.py` == 0 inline (chỉ qua `due_soon_filter`).

## IV.3. Component → Test mapping

| Component (I.1) | Test ID | Test layer | Coverage % | Risk priority (I.3) |
|---|---|---|---|---|
| `validate_work_order` (gate) | `TestPMCompletionGate` (4 cases) | Unit | *(Cần khảo sát)* | Critical |
| `create_schedule` | `TestPMSchedule` (4 cases) | Unit/Integration | *(Cần khảo sát)* | Medium |
| WO lifecycle | `TestPMWorkOrder` (5 cases) | Integration | *(Cần khảo sát)* | Critical |
| `backfill_pm_schedules_for_due_assets` | `TestPMBackfillAndSupervisor` (3 cases) | Unit/Cron | *(Cần khảo sát)* | Critical |
| `generate_pm_work_orders_from_schedule` | `TestGeneratePMWorkOrders` | Unit/Cron | ⬜ Planned | Critical |
| `_create_cm_wo_from_failure` | `TestHandleFailures` | Unit | ⬜ Planned | Critical |
| Workflow 13 transitions | `test_imm08_workflow.py` | Integration | ⬜ Planned | Critical |
| API endpoints (23) | `test_imm08_api.py` | API | ⬜ Planned | High |
| PM Task Log immutability | `test_audit_trail_immutable` | Integration | ⬜ Planned | High |

---

# Phần V — UAT Script

## V.1. Phạm vi UAT

- **In-scope**: auto-create PM WO + idempotency (BR-08-01/04); happy submit + lifecycle update (BR-08-03/05/08); Overdue + escalation email (BR-08-05); Fail-Minor → CM Medium (BR-08-09); Fail-Major → CM Critical + Out of Service (BR-08-04/09); Class III ảnh bắt buộc (BR-08-06); reschedule (VR-08-09); PM Task Log immutable (BR-08-10); hook IMM-04 → IMM-08; Calendar + Dashboard; mobile checklist UX.
- **Out-of-scope**: load testing (Phần III.8), security (Phần VI), mobile offline sync, calibration WO (IMM-11), holiday list integration.
- **Pre-condition**: UAT site `uat.assetcore.vn` deploy bản mới nhất; seed `bench --site uat.assetcore.local execute assetcore.scripts.uat.uat_imm08.setup_seed`; tester accounts active (V.2); Chrome/Edge ≥ 120.

## V.2. Tester accounts

| Username | Role (thực tế trong fixtures) | Vai trò UAT |
|---|---|---|
| `pmmgr.test@hospital.vn` | PM Manager | Phân công, reschedule, hủy, Calendar, Dashboard |
| `pmuser.test@hospital.vn` | PM User | Điền checklist, upload ảnh, submit, báo Major |
| `auditor.test@hospital.vn` | AssetCore Auditor | Xem Dashboard KPI (read-only), verify audit trail |
| `sysuser.test@hospital.vn` | AssetCore System User | Cover FORBIDDEN case (read-only, không mutate) |

Mật khẩu UAT: `Assetcore@2026` (reset sau UAT). Phải có account role thấp (`AssetCore System User`) để cover FORBIDDEN.

## V.3. Test data đã seed

| DocType | Số lượng | Ghi chú |
|---|---|---|
| AC Asset | 4 | SEED-PM-01 (Class II Quarterly), SEED-PM-02 (Class II Annual, overdue), SEED-PM-03 (Class III Quarterly), SEED-PM-04 (Class II, Out of Service) |
| PM Schedule | 4 | gắn với 4 assets trên |
| PM Checklist Template | 1 | ≥ 5 items (≥ 1 critical), Class II + Class III variant |
| Users | 4 | 4 tester accounts (V.2) |

Reset script: `bench --site uat.assetcore.local execute assetcore.scripts.uat.uat_imm08.setup_seed`.

## V.4. UAT Scenarios — Suy ra từ US + Activity

Mỗi scenario theo template §Phụ lục A. ID `UAT-IMM-08-NN`.

### UAT-IMM-08-01 — Tự động tạo PM Work Order + Idempotency

**Liên kết**: US-08-01, BR-08-01, BR-08-04
**Role tester**: Scheduler (chạy thủ công)
**Kỹ thuật**: Use Case happy + idempotent
**Mục tiêu**: Scheduler tạo PM WO đúng khi đến hạn; không tạo bản sao.

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | `bench execute assetcore.services.imm08.generate_pm_work_orders_from_schedule` | Không lỗi, log `N WOs created` | ☐ |
| 2 | Truy cập `/pm/work-orders?asset_ref=SEED-PM-01` | 1 PM WO status=Open, due hôm nay | ☐ |
| 3 | Email PM Manager | Email `[AssetCore] N PM Work Order mới hôm nay` | ☐ |
| 4 | Mở `/pm/calendar` | SEED-PM-01 đúng ngày, màu Open | ☐ |
| 5 | Chạy lại scheduler | KHÔNG tạo WO thứ 2 (idempotent AC-2) | ☐ |
| 6 | SEED-PM-04 `status=Out of Service`, chạy scheduler | KHÔNG tạo WO (BR-08-04) | ☐ |

**Post-condition**: 1 WO cho SEED-PM-01; audit trail có entry tương ứng. **Acceptance**: 6/6 step Pass.

### UAT-IMM-08-02 — Happy path: Phân công + Submit đúng hạn

**Liên kết**: US-08-02, BR-08-03, BR-08-05, BR-08-08, BR-08-10
**Role tester**: PM Manager → PM User
**Kỹ thuật**: Use Case happy + State Transition

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | `pmmgr` mở SEED-PM-01, "Phân công" → `pmuser` | status=In Progress, assigned_to set | ☐ |
| 2 | `pmuser` mở WO | checklist clone từ template hiển thị | ☐ |
| 3 | Submit khi 1 item chưa điền result | block BR-08-08 "Tất cả mục checklist phải có kết quả…" | ☐ |
| 4 | Điền tất cả = Pass, tick sticker, duration=45 | nút Hoàn thành enable | ☐ |
| 5 | Click "Hoàn thành PM" | status=Completed, `is_late=false` | ☐ |
| 6 | Kiểm tra PM Schedule | `next_due_date = completion + interval` (BR-08-03) | ☐ |
| 7 | Kiểm tra PM Task Log | 1 entry, immutable | ☐ |
| 8 | Thử update PM Task Log qua UI | block (BR-08-10) | ☐ |

**Post-condition**: PM Schedule advance, Task Log tạo. **Acceptance**: 8/8 step Pass.

### UAT-IMM-08-03 — Overdue + Escalation email

**Liên kết**: US-08-04, BR-08-05
**Role tester**: Scheduler → PM Manager
**Kỹ thuật**: Use Case alt + State Transition

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | SEED-PM-02 due = today-10, status=Open | setup đúng | ☐ |
| 2 | Chạy job đánh dấu Overdue | log `N WOs marked Overdue` | ☐ |
| 3 | Kiểm tra WO | status = Overdue | ☐ |
| 4 | Dashboard `/pm/dashboard` | WO trong bảng "Quá hạn", màu đỏ | ☐ |
| 5 | Email PM Manager (8 ≤ 10 ≤ 30 ngày tier) | escalation email | ☐ |
| 6 | `pmuser` submit Pass | `is_late=true`, `days_late=10` | ☐ |

**Acceptance**: 6/6 step Pass.

### UAT-IMM-08-04 — Fail-Minor → CM WO tự sinh

**Liên kết**: US-08-02 (variant), BR-08-09, BR-08-02
**Role tester**: PM User
**Kỹ thuật**: Decision Table

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | `pmuser` điền 9/10 = Pass | — | ☐ |
| 2 | Item #4 (không Critical) = Fail-Minor + notes | notes bắt buộc khi Fail | ☐ |
| 3 | Item #10 = Pass, submit | Completed, overall_result="Pass with Minor Issues" | ☐ |
| 4 | Kiểm tra CM WO mới | `wo_type=Corrective`, `source_pm_wo` trỏ về WO, priority=Medium | ☐ |
| 5 | Asset.status | vẫn Active (BR-08-09 Minor) | ☐ |

**Acceptance**: 5/5 step Pass.

### UAT-IMM-08-05 — Major Failure → Asset Out of Service

**Liên kết**: US-08-03, BR-08-04, BR-08-06, BR-08-09
**Role tester**: PM User → PM Manager
**Kỹ thuật**: Use Case exception + State Transition

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | `pmuser` mở SEED-PM-03 (Class III) | banner "Class III ⚠ Cần ảnh" | ☐ |
| 2 | Submit không upload ảnh | block BR-08-06 "Class III bắt buộc ảnh" | ☐ |
| 3 | 1 item Critical = Fail-Major | nút "Báo lỗi nghiêm trọng" highlight | ☐ |
| 4 | Click + description ≥ 10 ký tự + confirm | WO status = Halted–Major Failure | ☐ |
| 5 | Asset status | Out of Service (BR-08-04) | ☐ |
| 6 | CM WO mới | priority=Critical, `source_pm_wo` đúng, notes `[MAJOR FAILURE]` | ☐ |
| 7 | Email khẩn PM Manager | HTML email trong 5 phút (US-08-03 AC2) | ☐ |
| 8 | Chạy lại scheduler | KHÔNG tạo PM WO mới cho SEED-PM-03 (BR-08-04) | ☐ |

**Acceptance**: 8/8 step Pass.

### UAT-IMM-08-06 — Reschedule PM (VR-08-09)

**Liên kết**: US-08-06, VR-08-09
**Role tester**: PM Manager
**Kỹ thuật**: BVA (reason length boundary)

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | `pmmgr` mở WO In Progress, "Thiết bị bận - hoãn" | dialog hiện | ☐ |
| 2 | reason = "Bận" (4 ký tự) | block VR-08-09 "Lý do hoãn tối thiểu 5 ký tự" | ☐ |
| 3 | reason ≥ 5 ký tự + new_date | WO status = Pending–Device Busy | ☐ |
| 4 | Mở `/pm/calendar` | WO ngày mới, màu Pending | ☐ |

**Acceptance**: 4/4 step Pass.

### UAT-IMM-08-07 — Hook IMM-04 → IMM-08 auto-tạo PM Schedule

**Liên kết**: US-08-07, BR-08-07
**Role tester**: PM User (commissioning)
**Kỹ thuật**: Use Case + cross-module

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | Submit Asset Commissioning (asset_category có template) | submit thành công | ☐ |
| 2 | Kiểm tra PM Schedule | 1 record mới, naming `PMS-{asset}-{pm_type}` | ☐ |
| 3 | `next_due_date` | = commissioning_date + interval | ☐ |
| 4 | Chạy scheduler ngay | KHÔNG tạo WO (next_due > today + alert_days_before) | ☐ |

**Acceptance**: 4/4 step Pass.

### UAT-IMM-08-08 — Permission verify (FORBIDDEN)

**Liên kết**: 02 §Business Rules, VI.1 DocPerm
**Role tester**: tất cả roles
**Kỹ thuật**: EP (permission partition)

| Role | Action | Expected | Pass/Fail |
|---|---|---|---|
| PM User | Điền checklist + submit | ✅ Allow | ☐ |
| PM User | Hủy phiếu (Cancel) | ❌ FORBIDDEN | ☐ |
| PM User | Delete PM WO | ❌ FORBIDDEN | ☐ |
| PM Manager | Phân công + reschedule + cancel | ✅ Allow | ☐ |
| AssetCore Auditor | Xem Dashboard | ✅ Allow | ☐ |
| AssetCore Auditor | Submit PM result | ❌ FORBIDDEN | ☐ |
| AssetCore System User | assign_technician | ❌ FORBIDDEN (403) | ☐ |
| AssetCore Super Admin | Delete PM WO | ✅ Allow | ☐ |

**Acceptance**: 8/8 row Pass.

## V.5. Tổng hợp kết quả & Bug found

| Scenario | Status | Tester | Ngày | Ghi chú |
|---|---|---|---|---|
| UAT-IMM-08-01 | ☐ Pass / ☐ Fail / ☐ Block | | | |
| UAT-IMM-08-02 | ☐ Pass / ☐ Fail / ☐ Block | | | |
| UAT-IMM-08-03 | ☐ Pass / ☐ Fail / ☐ Block | | | |
| UAT-IMM-08-04 | ☐ Pass / ☐ Fail / ☐ Block | | | |
| UAT-IMM-08-05 | ☐ Pass / ☐ Fail / ☐ Block | | | |
| UAT-IMM-08-06 | ☐ Pass / ☐ Fail / ☐ Block | | | |
| UAT-IMM-08-07 | ☐ Pass / ☐ Fail / ☐ Block | | | |
| UAT-IMM-08-08 | ☐ Pass / ☐ Fail / ☐ Block | | | |

**Bug list**:

| Issue ID | Severity (Blocker/Major/Minor/Trivial) | Mô tả | Fix status |
|---|---|---|---|
| (điền khi phát sinh) | | | |

**Acceptance**: ≥ 95% PASS; UAT-IMM-08-01/02/03/05 **bắt buộc** Pass; Blocker = 0, Major ≤ 2 (có workaround documented).

**Sign-off**:

| Vai trò | Người | Ngày | Chữ ký |
|---|---|---|---|
| BA Lead | | | |
| QA Lead | | | |
| Module Owner (PTP Khối 2 / Workshop) | | | |
| Đại diện end-user (PM Manager) | | | |

---

# Phần VI — Security Review (gate)

## VI.1. RBAC

**Role definitions** (`fixtures/role.json` + `role_profile.json`). Role liên quan IMM-08: AssetCore Super Admin, PM Manager, PM User, AssetCore Auditor, AssetCore System User.

**DocPerm matrix — `PM Work Order`** (ground truth `pm_work_order.json`):

| Role | Read | Write | Create | Submit | Cancel | Delete |
|---|---|---|---|---|---|---|
| AssetCore Super Admin | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| PM Manager | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| PM User | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| AssetCore Auditor | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| AssetCore System User | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |

**DocPerm matrix — `PM Task Log`** (`in_create=1` — immutable sau khi tạo):

| Role | Read | Create | Write | Delete |
|---|---|---|---|---|
| AssetCore Super Admin | ✅ | ✅ | ✅ | ✅ |
| PM Manager | ✅ | ✅ | ✅ | ✅ |
| PM User | ✅ | ✅ | ✅ | ❌ |
| AssetCore Auditor | ✅ | ❌ | ❌ | ❌ |
| AssetCore System User | ✅ | ❌ | ❌ | ❌ |

> **Anti-FP / cảnh báo bảo mật**: `PM Task Log` hiện cho PM Manager + Super Admin **Write=1** và PM User Write=1, trái với mục tiêu immutable của BR-08-10 (immutability chỉ dựa vào `in_create=1`). **Cần khảo sát / siết DocPerm Write=0** cho mọi role để đảm bảo ISO 13485:7.5.9. → để ngỏ ở DoD.

**Field-level permission (permlevel)**: hiện tại `is_late` / `days_late` là KPI nhạy cảm nhưng `days_late` *(Cần khảo sát — field không thấy trong pm_work_order.json; chỉ có `duration_minutes` Int)*. Đề xuất permlevel 1 cho field lateness KPI.

**User Permission (row-level)**: PM User chỉ thấy/sửa WO `assigned_to = session.user`; PM Manager / Auditor read-all. Thực thi qua `permission_query_conditions`. Decision Table: mỗi (role × action × state) là 1 row → Allow/Deny (xem VI.1 matrix).

## VI.2. API security

| Mục | Trạng thái | Ghi chú |
|---|---|---|
| Whitelist hygiene | ✅ | 23 `@frappe.whitelist`; mutating endpoint dùng `methods=["POST"]` (reschedule_pm, create/update/delete schedule & template) |
| CSRF | ✅ | Frappe default `X-Frappe-CSRF-Token` |
| Input validation | ✅ | `name` validate qua `frappe.get_value` / service raise `NOT_FOUND`; JSON parse → `INVALID_PARAMS` |
| SQL injection | ✅ | Frappe ORM parameterized; không raw f-string SQL trong `imm08.py` |
| Rate limit | ⚠️ Roadmap | Cần cấu hình cho `report_major_failure` + `submit_pm_result` |

## VI.3. Audit trail integrity

Mỗi PM WO Completed sinh `PM Task Log` (`in_create=1`). Mọi state change (Completed, Halted–Major Failure, Overdue, Cancelled) sinh `IMM Audit Trail` qua `lifecycle.log_audit_event()`. Hash chain SHA-256: `hash = SHA256(prev_hash + canonical_json(event))`. Verify: `verify_audit_chain(asset) → bool`. Test tamper → III.5. Retention ≥ 5 năm (NĐ98/2021/NĐ-CP Điều 15). → Trace III.5.

## VI.4. Authentication & session

| Hạng mục | Config |
|---|---|
| Login | Frappe default — username + password |
| Session timeout | 8 giờ |
| Lockout | 3 lần fail → lock 15 phút |
| Password policy | ≥ 8 ký tự, 1 hoa, 1 số |
| API key | per-user, rotate 90 ngày |
| 2FA | Roadmap Phase 2 |

## VI.5. Data sensitivity

| Loại | Trường | Sensitivity | Bảo vệ |
|---|---|---|---|
| Kết quả checklist | `pm_checklist_result.result` | Internal | Role permission |
| KPI lateness | `is_late` (+ days_late nếu có) | Confidential | đề xuất permlevel 1 |
| Ghi chú kỹ thuật | `technician_notes` | Internal | Role permission |
| Ảnh thiết bị | Photo attachments | Internal | Role permission |
| Dữ liệu bệnh nhân | KHÔNG lưu | N/A | IMM-08 KHÔNG lưu patient data |

## VI.6. Vendor isolation

Vendor External KHÔNG có quyền trên `PM Work Order` trong DocPerm mặc định (không nằm trong 5 role được cấp quyền). Vendor technician hoạt động qua `AC Authorized Technician` (IMM-03), tách biệt PM internal flow. Nếu mở rộng: chỉ thấy WO `vendor_assigned = session.user`; KHÔNG thấy chi phí / lateness KPI / audit trail vendor khác; KHÔNG export bulk. → Test ở III.6 (low-role API call).

## VI.7. Secrets management

`site_config.json` không commit git. Email alert token lưu `frappe.conf`, không hardcode. Backup encrypt at-rest off-site (S3) theo `08_Deployment.md`. Secret scan CI: `detect-secrets` pre-commit hook.

## VI.8. Logging & monitoring

| Sự kiện | Log level | Where | Alert? |
|---|---|---|---|
| Major Failure phát hiện | CRITICAL | `frappe.log_error` + Audit Trail + email | ✅ PM Manager |
| PM WO Overdue > 30 ngày | ERROR | scheduler log | ✅ BGĐ |
| Scheduler `generate_pm_work_orders_from_schedule` không chạy | WARNING | Frappe scheduler log | ✅ Admin |
| PM Task Log tamper attempt | ERROR | `frappe.log_error` | ✅ Admin |
| Audit chain verify fail | ERROR | `frappe.log_error` | ✅ Admin |
| API 4xx (submit fail) | INFO | Frappe access log | ❌ |

PII / token KHÔNG vào log.

## VI.9. Threat model (STRIDE-lite)

| Threat | Vector | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| **Spoofing** — PM User | Giả mạo session PM User | Low | High | Session HttpOnly + SameSite; row-level permission |
| **Tampering** — PM Task Log | Sửa DB trực tiếp | Low | Critical | `in_create=1`; test immutability; **cần siết Write=0 DocPerm** |
| **Tampering** — next_pm_date | Sửa tắt để skip PM | Low | High | `update_pm_schedule_after_completion` enforce BR-08-03; audit trail |
| **Repudiation** — Completion | PM User phủ nhận đã submit | Low | High | PM Task Log + IMM Audit Trail hash chain + actor field |
| **Info Disclosure** — KPI | low-role xem lateness KPI | Low | Medium | đề xuất permlevel 1; Auditor/System User read-only |
| **Denial of Service** — Scheduler | overload 10k+ WO/ngày | Medium | Medium | batch theo run; index `status + next_due_date`; skip Out of Service |
| **Elevation of Privilege** — Cancel/assign | low-role gọi `assign_technician`/cancel | Low | High | DocPerm (PM User Cancel=0); FORBIDDEN; row-level permission |

## VI.10. Penetration test

Trước release đầu tiên (go-live bệnh viện): Burp/OWASP ZAP scan `uat.assetcore.vn` (0 High/Critical open); sqlmap mode safe trên `submit_pm_result` + `report_major_failure`; CSRF test (curl không token); role escalation (`assign_technician` với AssetCore System User → 403). Report lưu `docs/security/pentest_imm08_v1.md`.

## VI.11. Sign-off

| Vai trò | Người | Ngày | Quyết định |
|---|---|---|---|
| QA Lead | | | ☐ Pass / ☐ Pass with conditions / ☐ Fail |
| Security Officer | | | ☐ Pass / ☐ Pass with conditions / ☐ Fail |
| Tech Lead | | | ☐ Pass / ☐ Pass with conditions / ☐ Fail |
| Module Owner (Workshop) | | | ☐ Pass / ☐ Pass with conditions / ☐ Fail |

**Điều kiện go-live**: tất cả Sign-off Pass hoặc Pass with conditions (workaround documented).

---

# Phần VII — Code Quality

## VII.1. Tool matrix

| Tool | Mục tiêu | Target | Cadence |
|---|---|---|---|
| **SonarQube** (BE Python) | Bug 0 Critical, code smell ≤ 5, duplication ≤ 3%, coverage ≥ 70%, security hotspot review 100% | Quality Gate pass | Mỗi PR (CI gate) |
| **Lighthouse** (FE — PMDashboardView) | Performance ≥ 90, Accessibility ≥ 95, Best Practices ≥ 90, SEO ≥ 80 | ≥ target | Mỗi release + monthly |
| **ESLint + vue-tsc** (FE) | 0 error, 0 warning prod build | pass | Mỗi PR FE (CI gate) |
| **ruff / black** (BE Python) | 0 error, format PEP8 | pass | Mỗi PR (CI gate) |
| **Bundle size** (FE chunk imm08) | main ≤ 250 KB gzip, async ≤ 80 KB gzip | ≤ budget | Mỗi PR FE (CI report) |

## VII.2. Cadence

- SonarQube: mỗi PR (CI gate, fail nếu Quality Gate fail).
- Lighthouse: mỗi release lớn + monthly audit.
- ESLint / ruff: mỗi PR (CI gate).
- Bundle size: mỗi PR FE (CI report, fail nếu vượt budget).

Screenshot SonarQube + Lighthouse gắn vào `09_Release.md` §Release Notes khi báo cáo final.

---

# Phụ lục A — Template per UAT scenario

```markdown
### UAT-IMM-08-<NN> — <Tên>

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
### TC-IMM-08-<LAYER>-<NN> — <Tên>

**Component (I.1)**: <…>
**Liên kết**: US-<NN> | BR-<NN> | ACT-<NN>
**Kỹ thuật (II.1/II.2)**: BVA boundary `reason length = 4`
**Priority (I.3)**: Critical / High / Medium / Low
**Test type**: Unit / Integration / API / E2E
**Pre-condition**: <fixture / state setup>

**Input**:
- <field>: <value>

**Steps**:
1. <…>
2. <…>

**Expected**:
- ServiceError(code=VALIDATION, message contains "BR-08-08")
- doc.workflow_state unchanged

**Post-condition**: <DB rollback / fixture cleanup>
```

# Phụ lục C — Workflow State Transition Test template

```markdown
### TC-IMM-08-WF-<NN> — <action>: <from> → <to>

**Workflow JSON**: `assetcore/assetcore/workflow/imm_08_pm_workflow.json`
**Role required**: <…>
**Pre-condition**: doc.workflow_state = <from>, gate <Gx> đã pass
**Action**: apply_workflow(doc, "<action>")
**Expected (happy)**: doc.workflow_state = <to>, docstatus = <…>, audit entry created
**Expected (negative role)**: PermissionError / FORBIDDEN
**Expected (gate fail)**: ServiceError(code=VALIDATION, message contains "<BR-08-xx>")
```

---

# DoD — File 07 hoàn chỉnh

## I. Test Analysis
- [x] I.1 Component Inventory liệt kê đủ artefact (21 component, so 04/05/06)
- [x] I.2 mỗi US / BR / Activity có ≥ 1 dòng map
- [x] I.3 Risk priority gán cho mọi component (không trống)
- [x] I.4 Scope ghi rõ out-of-scope kèm lý do

## II. Test Design Techniques
- [x] II.1 chọn ≥ 4 black-box techniques (EP + BVA + Decision Table + State Transition)
- [x] II.2 white-box criteria (statement + branch + MC/DC gate)
- [x] II.3 mapping component → kỹ thuật đầy đủ

## III. Test Plan
- [x] Test class structure cho service public function (I.1)
- [x] ≥ 1 happy + 1 negative test mỗi function (đã có 5 class Live; còn 5 class Planned)
- [x] Workflow transitions liệt kê 100% (13 transition = JSON)
- [ ] Workflow transition test viết đủ (hiện ⬜ Planned — chưa có `test_imm08_workflow.py`)
- [ ] Audit chain test (intact + tampered) — ⬜ Planned, chưa implement
- [ ] API test ≥ 60% coverage + permission matrix — ⬜ Planned (`test_imm08_api.py` chưa có)
- [x] Performance target xác định
- [x] CI command xác định (`bench run-tests --module …`)
- [ ] **SonarQube Quality Gate pass** + **Lighthouse ≥ target** — chưa chạy/đo, target xác định

## IV. Traceability
- [x] IV.1 US → Test: mọi US có ≥ 1 Test ID
- [x] IV.2 BR → Test: mọi BR có happy + negative (nhiều ⬜ Planned)
- [ ] IV.3 Component → Test: Critical/High đạt coverage target III.10 — coverage % *(Cần khảo sát)*, chưa đo

## V. UAT
- [x] Mỗi US có ≥ 1 UAT scenario
- [x] ≥ 1 negative + permission + audit verify scenario
- [ ] Test data seed script chạy được — `uat_imm08.py` *(Cần khảo sát tồn tại)*
- [x] Tester accounts đủ role (gồm AssetCore System User cho FORBIDDEN)
- [x] Sign-off section sẵn sàng

## VI. Security
- [x] DocPerm matrix đầy đủ (Decision Table) — ground truth từ JSON
- [ ] Mọi field nhạy cảm có permlevel ≠ 0 — lateness KPI chưa set permlevel; cần siết
- [ ] SQL injection + CSRF test pass — chưa chạy pentest (target xác định)
- [ ] Audit chain test pass (intact + tampered) — ⬜ Planned
- [ ] Vendor isolation test pass (low-role API call) — ⬜ Planned
- [x] Threat model đủ 6 STRIDE với mitigation
- [x] Sign-off section sẵn sàng

## VII. Code Quality
- [ ] SonarQube Quality Gate pass — chưa chạy
- [ ] Lighthouse ≥ target — chưa chạy
- [ ] Bundle size ≤ budget — chưa đo
- [x] Screenshot báo cáo gắn vào file 09 — quy trình documented
