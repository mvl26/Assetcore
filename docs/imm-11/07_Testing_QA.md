# 07 — Kiểm thử & An ninh (Testing & QA & Security)

| Mục | Giá trị |
|---|---|
| Module | IMM-11 — Hiệu chuẩn (Calibration) |
| Phạm vi | Per-module |
| Owner | QA Lead + Security Officer |
| Liên kết | [02 Analysis](./02_Analysis_Design.md) · [03 Diagrams](./03_Diagrams.md) · [04 Backend](./04_Backend_Design.md) · [05 API](./05_API_Specification.md) · [06 Frontend](./06_Frontend_Design.md) |

> **Mục đích**: Suy ra test case **có hệ thống** từ phân tích (file 02) bằng kỹ thuật black-box + white-box, không liệt kê tự phát. Bao gồm: phân tích đối tượng test → chọn kỹ thuật → viết test → traceability → UAT → security → code quality. Phần này là gate go-live.

> **Trạng thái module**: ✅ Live — BE (`services/imm11.py`, `api/imm11.py`), 3 DocType, workflow JSON, FE (5 views + store + api client) đã deploy. Test suite `assetcore/tests/test_imm11.py` đã có 3 test class / 8 method live; phần lớn integration/API/E2E/UAT còn ⬜ Planned.

---

# Phần I — Test Analysis (Phân tích đối tượng test)

> Mục tiêu Phần I: trả lời 4 câu hỏi trước khi viết test case: **(1) test cái gì** (component inventory) **(2) suy ra từ đâu** (US/BR/Activity) **(3) ưu tiên cái nào** (risk) **(4) loại trừ cái nào** (out-of-scope).

## I.1. Component Inventory — Liệt kê phần mềm cần test

Toàn bộ artefact test được của IMM-11 (nguồn: 04 §DocType/§Service/§Hook · 05 §Catalog · 06 §Components). Mỗi dòng → ≥ 1 test class ở Phần III.

| # | Component | Loại | File / Tên | Test layer áp dụng |
|---|---|---|---|---|
| 1 | `IMM Asset Calibration` | DocType (Submittable) | `imm_asset_calibration.json` | Integration (lifecycle) |
| 2 | `IMM Calibration Schedule` | DocType | `imm_calibration_schedule.json` | Integration (CRUD) |
| 3 | `IMM Calibration Measurement` | Child DocType | `imm_calibration_measurement.json` | Unit (auto Pass/Fail) |
| 4 | `IMM-11 Calibration Workflow` | Workflow | `workflow/imm_11_calibration_workflow.json` | Integration (state transition) |
| 5 | `create_calibration` | Service function | `services/imm11.py::create_calibration` | Unit + API |
| 6 | `submit_calibration` | Service function | `services/imm11.py::submit_calibration` | Unit + Integration |
| 7 | `handle_calibration_pass` | Service function | `services/imm11.py::handle_calibration_pass` | Unit (BR-11-04) |
| 8 | `handle_calibration_fail` | Service function | `services/imm11.py::handle_calibration_fail` | Unit (BR-11-02) |
| 9 | `perform_lookback_assessment` | Service function | `services/imm11.py::perform_lookback_assessment` | Unit (BR-11-03) |
| 10 | `cancel_calibration` | Service function | `services/imm11.py::cancel_calibration` | Unit |
| 11 | `send_to_lab` / `receive_certificate` | Service function | `services/imm11.py::send_to_lab`, `receive_certificate` | Unit + API |
| 12 | `add_measurement` | Service function | `services/imm11.py::add_measurement` | Unit (BVA tolerance) |
| 13 | DocType controller validators | Validator | `imm_asset_calibration.py::validate / before_submit / on_cancel / on_trash` (VR-11-01..07) | Unit (BVA/EP/Decision Table) |
| 14 | `IMMAssetCalibration.before_submit` gate | Gate | `imm_asset_calibration.py::before_submit` (measurements ≥1 + có giá trị đo) | Unit (Decision Table) |
| 15 | `create_calibration_schedule_from_commissioning` | Lifecycle hook | `services/imm11.py` (gọi từ IMM-04 commissioning) | Integration (cross-module) |
| 16 | `create_post_repair_calibration` | Lifecycle hook | `services/imm11.py` (gọi từ IMM-09 repair) | Integration (cross-module) |
| 17 | `create_due_calibration_wos` | Scheduler job | `services/imm11.py::create_due_calibration_wos` | Unit + Cron simulation |
| 18 | `check_calibration_expiry` | Scheduler job | `services/imm11.py::check_calibration_expiry` | Unit + Cron simulation |
| 19 | API endpoints (18) | API endpoint | `api/imm11.py` (catalog §I.2.a layer) | API integration |
| 20 | Lifecycle event `calibration_*` | Lifecycle event | `services/imm11.py::_transition_asset` → `IMM Audit Trail` | Integration (audit chain) |
| 21 | `CalibrationListView/Dashboard/CreateView/DetailView/ScheduleListView` | FE view | `frontend/src/views/calibration/*.vue` | E2E (Playwright) |
| 22 | Pinia store `imm11` | Pinia store | `frontend/src/stores/imm11.ts` | Unit (vitest) — ⬜ Planned |

## I.2. Trace nguồn test — User Stories, Activity Flows, Business Rules

3 bảng dẫn từ artefact phân tích (file 02 §Functional Specs + §Business Rules + §State Machine) sang test layer.

### I.2.a. Từ User Story
| US ID | Tiêu đề ngắn | Acceptance Criteria # | Test layer dự kiến |
|---|---|---|---|
| US-11-01 | Xem danh sách thiết bị đến hạn calibration (30 ngày) | AC-01 (Due Soon), AC-02 (Overdue) | API (`get_due_calibrations`) + UAT |
| US-11-02 | Auto Pass/Fail khi nhập measurement | AC-01 (in-tolerance Pass), AC-02 (OOT Fail) | Unit (`add_measurement`) + UAT |

> *(02 §III chỉ định nghĩa đầy đủ US-11-01/02; US-11-03→NN chưa hoàn thiện trong 02 — đánh dấu `*(Cần khảo sát)*` khi viết test cho các US đó.)*

### I.2.b. Từ Business Rule
| BR ID | Phát biểu | Component liên quan (I.1) | Kỹ thuật test phù hợp |
|---|---|---|---|
| BR-11-01 | External: lab ISO 17025 + cert + accreditation number bắt buộc | #13 `validate()` (VR-11-01/02/03/04) | Decision Table |
| BR-11-02 | Fail → asset Out of Service + CAPA bắt buộc | #8 `handle_calibration_fail` | Decision Table / Use Case |
| BR-11-03 | Lookback bắt buộc cùng `device_model` | #9 `perform_lookback_assessment` | EP (active/decommissioned partition) |
| BR-11-04 | `next_cal = certificate_date + interval` (không phải due_date) | #7 `handle_calibration_pass` | BVA (date boundary) |
| BR-11-05 | Immutable sau Submit; Amend cần reason | #13 `on_cancel`/`on_trash` + amendment_reason | EP + Error guessing |
| BR-11-06 | Decommissioned → suspend Schedule | #15 transition cascade | EP |
| BR-11-07 | `validate_asset_for_operations()` gate (trừ `is_recalibration=1`) | #5 service entry | Decision Table |
| BR-11-08 | SoT predicate due/overdue — biên rõ + 1 nguồn date (Schedule.next_due_date) | `is_calibration_overdue` / `is_calibration_due_soon` / `_overdue_asset_ids` | BVA (date boundary) + EP |
| BR-11-08b | FAIL → hạ MỌI active `Schedule.next_due_date` về basis-date (due-now) → asset FAIL vào overdue/due-soon SoT, hết mask ON_SCHEDULE; null-safe | #8 `handle_calibration_fail` (write-path §04 §4.1.6) | Decision Table + BVA + Path |
| BR-11-09 | De-dup theo asset (>1 active schedule overdue → đếm 1) | `_overdue_asset_ids` DISTINCT | EP |

### I.2.c. Từ Activity Flow / State Machine
Nguồn: 02 §IV.3 State Machine (mermaid). ACT id chưa định danh trong 02 → dùng branch của state machine làm path test.

| Branch | Use Case | Branch chính | Branch ngoại lệ |
|---|---|---|---|
| External track | UC-05/06 Nhập + Submit | Scheduled → Sent to Lab → Certificate Received → Passed | cert null (VR-11-03), accreditation null (VR-11-04), cert_date tương lai (VR-11-07) |
| In-House track | UC-05/06 | Scheduled → In Progress → Passed | reference_standard_serial null (VR-11-06) |
| Fail + CAPA | UC Fail handling | … → Failed → (CAPA closed) → Conditionally Passed | submit không có measurement (CAL-004), asset không OOS |
| Cancel | UC-01 Lập lịch | Scheduled → Cancelled (docstatus=0) | cancel sau Submit (BR-11-05) → throw |

## I.3. Risk-based Priority

| Component (I.1) | Likelihood (1-5) | Impact (1-5) | Risk = L×I | Priority |
|---|---|---|---|---|
| #8 `handle_calibration_fail` (OOS + CAPA) | 3 | 5 | 15 | **Critical** |
| #13 validators VR-11-01/02 (lab ISO 17025) | 4 | 4 | 16 | **Critical** |
| #7 `handle_calibration_pass` (BR-11-04 date) | 3 | 5 | 15 | **Critical** |
| #4 Workflow transitions | 3 | 4 | 12 | High |
| #20 Lifecycle event / audit chain | 2 | 5 | 10 | High |
| #14 before_submit gate (measurements) | 3 | 4 | 12 | High |
| #9 `perform_lookback_assessment` | 2 | 4 | 8 | Medium |
| #17/#18 Scheduler jobs | 3 | 3 | 9 | Medium |
| #19 API list/get endpoints (read) | 2 | 2 | 4 | Low |
| #21 FE views | 2 | 2 | 4 | Low |

**Quy ước priority**: Critical (R ≥ 15) test trước, fail = block release · High (10–14) bắt buộc trước go-live · Medium (5–9) trong sprint · Low (<5) test khi báo bug.

## I.4. Scope

- **In-scope**: validators External/In-House (VR-11-01..07), gate before_submit (CAL-004), Pass/Fail handling (BR-11-02/04), lookback (BR-11-03), workflow 13 transitions, audit chain, 18 API endpoint, scheduler idempotent.
- **Out-of-scope**:
  - Performance test → giao Phần III.8 (chưa thực thi).
  - Cross-module với IMM-04 (commissioning) và IMM-09 (post-repair) chỉ smoke ở III.3.
  - OCR/parse PDF chứng chỉ — không trong phạm vi module.
  - FE store unit test (vitest) — ⬜ Planned, chưa cấu hình harness.
- **Assumptions**: master data (`AC Asset Category`, `AC Supplier` lab, `IMM Device Model`) đã seed; test users theo role IMM-11 đã tạo; Chrome ≥ 120 cho E2E.

---

# Phần II — Test Design Techniques (Kỹ thuật thiết kế test case)

## II.1. Black-box techniques

| Kỹ thuật | Khi nào dùng | Áp dụng vào IMM-11 | Số test sinh ra (rule of thumb) |
|---|---|---|---|
| **Equivalence Partitioning (EP)** | Input có miền giá trị chia nhóm | `calibration_type` (External/In-House), `status` enum (8 giá trị), lookback partition (Active vs Decommissioned) | 1 test/partition |
| **Boundary Value Analysis (BVA)** | Numeric / date có biên | measurement tolerance (`nominal ± tol`: in/at/out), `next_calibration_date = certificate_date + interval_days`, `get_due_calibrations(days=30)` biên 30 | 2-3 test/biên |
| **Decision Table** | Multi-condition gate | VR-11-01..04 (External: lab + cert + accreditation), before_submit (measurements ≥1 AND có giá trị đo), BR-11-07 gate (asset Active AND NOT is_recalibration) | 2^N rút gọn |
| **State Transition Testing** | Workflow state machine | 13 transition trong `imm_11_calibration_workflow.json` (Scheduled → … → Passed/Failed/Conditionally Passed/Cancelled) | mỗi transition + invalid transition |
| **Use Case Testing** | End-to-end actor flow | UAT scenarios (V.4), API integration test (III.6) | 1/main + 1/alt + 1/exception |
| **Error Guessing** | null/empty/future date/race | tất cả endpoint nhận input (cert_date tương lai, asset không tồn tại, double-submit scheduler) | bổ sung |

## II.2. White-box techniques

| Kỹ thuật | Áp dụng vào | Tiêu chí đạt | Công cụ |
|---|---|---|---|
| **Statement coverage** | Service functions I.1 (#5–#18) | ≥ 85% line | `coverage report` |
| **Branch / Decision coverage** | Functions có if/else, try/except (`handle_calibration_pass/fail`, `_normalize_list_filters`) | ≥ 80% branch | `coverage --branch` |
| **Condition / MC/DC** | Gate VR-11-01..04, before_submit multi-AND | mỗi sub-condition kiểm soát outcome độc lập | Manual test design + coverage |
| **Path coverage** | `perform_lookback_assessment` (loop 0/1/N asset) | toàn bộ path (loop = 0,1,N) | Manual |

## II.3. Mapping Component → Kỹ thuật

| Loại component | Kỹ thuật chính | Kỹ thuật phụ |
|---|---|---|
| Field validator (VR-11-*) | BVA + EP | Error guessing |
| Gate logic (before_submit, BR-11-07) | Decision Table | MC/DC |
| Workflow transition | State Transition | Use Case |
| Service function pure (`perform_lookback_assessment`) | EP + Branch coverage | BVA |
| API endpoint | Use Case + EP | Pairwise (form input) |
| Scheduler (`create_due_calibration_wos`, `check_calibration_expiry`) | Use Case (setup → run → assert) | Error guessing (idempotent, partial fail) |
| FE view (Playwright) | Use Case end-to-end | Error guessing (network 4xx/5xx, role gate) |

---

# Phần III — Test Plan (Kế hoạch thực thi)

## III.1. Test Pyramid

```
                  ┌────────────┐
                  │  E2E / UAT │   ~5%  ← Playwright (⬜ Planned)
                 ─┴────────────┴─
              ┌──────────────────────┐
              │   API Integration    │   ~15% ← pytest + whitelist (⬜ Planned)
             ─┴──────────────────────┴─
          ┌────────────────────────────────┐
          │  Workflow + DocType lifecycle  │   ~25% ← FrappeTestCase
         ─┴────────────────────────────────┴─
      ┌────────────────────────────────────────────┐
      │         Unit — Service Layer               │   ~55% ← test_imm11.py (✅ Live)
     ─┴────────────────────────────────────────────┴─
```

Trace: CLAUDE.md §17 (TDD mandatory).

## III.2. Unit test — Service Layer

File `assetcore/tests/test_imm11.py` (✅ Live — `unittest.TestCase`, helper `_make_asset` prefix `_Test`).

| Test class | Function cover | Kỹ thuật | Cases (happy/negative) | Trạng thái |
|---|---|---|---|---|
| `TestCalibrationCreation` | `create_calibration` | EP + Error guessing | 3 / 1 (`test_nonexistent_asset_raises_not_found`, `test_create_calibration_succeeds`, `test_initial_status_is_scheduled`, `test_naming_series`) | ✅ Live |
| `TestCalibrationCancellation` | `cancel_calibration` | State Transition | 1 / 0 (`test_cancel_scheduled_calibration`) | ✅ Live |
| `TestCalibrationSubmitGate` | `submit_calibration` + before_submit | Decision Table | 1 / 1 (`test_submit_blocked_without_measurements`, `test_submit_succeeds_with_measurement_and_result`) | ✅ Live |
| `TestCalibrationPass` | `handle_calibration_pass` (BR-11-04 next_cal date) | BVA | 1 / 0 | ⬜ Planned |
| `TestCalibrationFail` | `handle_calibration_fail` (OOS + CAPA) | Decision Table | 2 / 0 | ⬜ Planned |
| `TestCalibrationFailDueNow` | `handle_calibration_fail` → Schedule due-now (BR-11-08b) | Decision Table + BVA + Path | 7 method (TC-CAL-FAIL-DUE-01..07; RED-prove 01/02/04) + FE `calFailDueNow.test.ts` 10 | ✅ Live |
| `TestLookback` | `perform_lookback_assessment` | EP (Active/Decommissioned) + Path | 1 / 2 | ⬜ Planned |
| `TestAddMeasurement` | `add_measurement` auto Pass/Fail | BVA tolerance | 2 / 1 | ⬜ Planned |
| `TestUpdateCalibrationMeasurements` | `update_calibration` `measurements` child-diff replace-set (BR-11-16, data-loss fix) | Decision Table + BVA + Error guessing | 5 / 4 (TC-11-MEASDIFF-01..10; RED-first 01) | ⬜ Planned |
| `TestSubmitCalibrationIdempotency` | `submit_calibration` idempotency dedup — replay THẮNG state-guard (BR-11-17 / CR-24-CAL-SUBMIT op#6) | Decision Table + Error guessing | 6 / 6 (TC-11-IDEMP-SUBMIT-01..06; RED-first 01/02/03) | ⬜ Planned |
| `TestSchedulerDueWOs` | `create_due_calibration_wos` idempotent | Use Case | 1 / 1 (duplicate guard) | ⬜ Planned |
| `TestExpiryCheck` | `check_calibration_expiry` | EP (On Schedule/Due Soon/Overdue) | 3 / 0 | ⬜ Planned |
| `TestSendReceiveLab` | `send_to_lab` / `receive_certificate` | State Transition | 2 / 1 | ⬜ Planned |
| `TestSendToLabCertGuard` | `send_to_lab` chặn gửi-lại phiếu ĐÃ có chứng chỉ — bảo toàn vết `sent_date` NĐ98 (BR-11-18 / CR-59) | State Transition + Error guessing | 2 / 1 (TC-11-SENDLAB-CERTGUARD-01/02; RED-first 01) | ⬜ Planned |

## III.3. Integration — DocType lifecycle

File `assetcore/tests/test_imm_asset_calibration_doctype.py` (⬜ Planned). Cover hook `validate / before_submit / on_submit / on_cancel / on_trash`.

| Test | Setup | Action | Assert | Kỹ thuật |
|---|---|---|---|---|
| `test_before_submit_blocks_no_cert` | External CAL, không cert file | `doc.submit()` | throw VR-11-03 | Decision Table |
| `test_external_blocks_no_accreditation` | External, lab không có accreditation number | `doc.submit()` | throw VR-11-04 | Decision Table |
| `test_external_blocks_lab_not_iso17025` | lab `vendor_type ≠ Calibration Lab` | `doc.submit()` | throw VR-11-02 | EP |
| `test_cert_date_future_blocked` | certificate_date = today+1 | `doc.submit()` | throw VR-11-07 | BVA |
| `test_inhouse_no_cert_required` | In-House, all Pass, no cert | `doc.submit()` | Submit OK | EP |
| `test_inhouse_blocks_no_reference_standard` | In-House, reference_standard_serial null | `doc.submit()` | throw VR-11-06 | EP |
| `test_submit_blocks_no_measurements` | không có measurement row | `doc.submit()` | throw CAL-004 | Decision Table |
| `test_on_submit_pass_updates_asset` | all Pass | `doc.submit()` | `AC Asset.next_calibration_date` đúng (BR-11-04) | BVA |
| `test_on_submit_fail_triggers_capa` | 1 measurement OOT | `doc.submit()` | CAPA created, asset Out of Service | Decision Table |
| `test_on_cancel_blocked_after_submit` | docstatus=1 | `doc.cancel()` | throw BR-11-05 | Error guessing |
| `test_on_trash_blocked_after_submit` | docstatus=1 | `doc.delete()` | throw BR-11-05 | Error guessing |
| `test_schedule_auto_created_on_commissioning` | IMM-04 commissioning submit | `commissioning.submit()` | `IMM Calibration Schedule` created (cross-module) | Use Case |

Fixture trong `setUpClass` phải có `tearDownClass` purge (xem `_purge_asset_with_deps` trong `test_imm11.py`).

## III.4. Integration — Workflow transitions

File `assetcore/tests/test_imm11_workflow.py` (⬜ Planned). Workflow `imm_11_calibration_workflow.json` có **13 transition** (đếm xác minh bằng `python3 -c "import json;print(len(json.load(open('assetcore/assetcore/workflow/imm_11_calibration_workflow.json'))['transitions']))"`). Bắt buộc cover 100%.

| # | Action | From → To | Role required | Test pass | Test fail (wrong role / gate) |
|---|---|---|---|---|---|
| 1 | Bắt đầu hiệu chuẩn | Scheduled → In Progress | Calibration User | ☐ | ☐ |
| 2 | Gửi phòng hiệu chuẩn | Scheduled → Sent to Lab | Calibration User | ☐ | ☐ |
| 3 | Hủy lịch | Scheduled → Cancelled | System Manager | ☐ | ☐ |
| 4 | Đạt hiệu chuẩn | In Progress → Passed | Calibration User | ☐ | ☐ |
| 5 | Không đạt hiệu chuẩn | In Progress → Failed | Calibration User | ☐ | ☐ |
| 6 | Đạt có điều kiện | In Progress → Conditionally Passed | Calibration User | ☐ | ☐ |
| 7 | Hủy hiệu chuẩn | In Progress → Cancelled | System Manager | ☐ | ☐ |
| 8 | Nhận chứng chỉ | Sent to Lab → Certificate Received | Calibration User | ☐ | ☐ |
| 9 | Phê duyệt đạt | Certificate Received → Passed | System Manager | ☐ | ☐ |
| 10 | Phê duyệt không đạt | Certificate Received → Failed | System Manager | ☐ | ☐ |
| 11 | Phê duyệt có điều kiện | Certificate Received → Conditionally Passed | System Manager | ☐ | ☐ |
| 12 | CAPA hoàn tất → có điều kiện | Failed → Conditionally Passed | Compliance Manager | ☐ | ☐ |
| 13 | CAPA hoàn tất → có điều kiện | Failed → Conditionally Passed | System Manager | ☐ | ☐ |

Kỹ thuật: State Transition Testing — mỗi edge = 1 test pass + 1 test fail (wrong role hoặc invalid from-state).

### III.4b. Dual-track lockstep `workflow_state ⇄ status` + INVARIANT (round 18 — CR-WF-11-CAL)

**Class mới `TestCalibrationWorkflowLockstep` (`tests/test_imm11.py`).** Đóng desync `workflow_state` đọng state khởi tạo. Groundtruth `04_Backend_Design.md §3.2` + `ADR-IMM11-06`. **BE-only** — 0 FE, 0 migrate, 0 đổi workflow JSON.

**RED-before (BẮT BUỘC chứng minh desync TRƯỚC khi fix):** tạo phiếu External `Scheduled` → `send_to_lab` → đọc lại DB `db.get_value('IMM Asset Calibration', name, 'workflow_state')` == `'Scheduled'` ≠ `status` == `'Sent to Lab'` ⇒ TC-11-LOCKSTEP-SENDLAB FAIL (chứng minh workflow_state đọng). Sau khi thêm lockstep (§3.2) → GREEN (`workflow_state == status`).

| # | TC id | Drive (service transition) | Assert sau khi đọc lại DB | AC |
|---|---|---|---|---|
| 1 | TC-11-LOCKSTEP-CREATE | `create_calibration(...)` | `workflow_state == status == 'Scheduled'` | AC-11-LS-1 |
| 2 | TC-11-LOCKSTEP-UPDATE | `update_calibration(name, {status: 'In Progress'})` | `workflow_state == status == 'In Progress'` | AC-11-LS-2 |
| 3 | TC-11-LOCKSTEP-SENDLAB | `send_to_lab(name)` (External) | `workflow_state == status == 'Sent to Lab'` — **RED-prove** trước fix | AC-11-LS-3 |
| 4 | TC-11-LOCKSTEP-RECVCERT | `receive_certificate(name, ...)` | `workflow_state == status == 'In Progress'` (⚠️ KHÔNG `Certificate Received` — §3.2) | AC-11-LS-4 |
| 5 | TC-11-LOCKSTEP-CANCEL | `cancel_calibration(name, reason)` | `workflow_state == status == 'Cancelled'` | AC-11-LS-5 |
| 6 | TC-11-LOCKSTEP-SUBMIT | `submit_calibration(name)` (đủ measurement) | `workflow_state == status` (giữ `'In Progress'` — submit KHÔNG advance, OoS backlog) | AC-11-LS-6 |
| 7 | TC-11-LOCKSTEP-GETTRANS | sau `send_to_lab` (đã fix) | `frappe.model.workflow.get_transitions(doc)` = cạnh của `'Sent to Lab'` (→ Certificate Received), KHÔNG của `'Scheduled'` | AC-11-LS-7 |
| 8 | TC-11-LOCKSTEP-NOTHROW | multi-hop `send_to_lab` → `receive_certificate` (`Sent to Lab → In Progress`, 0 workflow-edge) | KHÔNG raise `WorkflowPermissionError` (db.set_value bypass validate_workflow) | AC-11-LS-8 |

**INVARIANT guard `test_imm11` (RED-before / GREEN-after) — name-parity status ⇄ workflow states:**

| INV | Assert | Nguồn |
|---|---|---|
| INV-11-A | `set(status Select options `IMM Asset Calibration`) == set(states[] `imm_11_calibration_workflow.json`) == 8` (1-1 name-parity) ⇒ lockstep LUÔN ghi tên Workflow State hợp lệ | DocType JSON + workflow JSON |
| INV-11-B | `S_svc = {Scheduled, In Progress, Sent to Lab, Cancelled} ⊆ states[]` (service-reachable ⊆ workflow states; `Certificate Received` + 3 terminal ∈ states nhưng ∉ S_svc — grounded 6 write-path) | imm11.py write-path |
| INV-11-C | với mọi status ∈ S_svc: drive service transition → `db.get_value(workflow_state) == status` | TC-11-LOCKSTEP-* |

- **DoD:** `bench --site miyano run-tests` (module `test_imm11`) = **'Ran N OK' THẬT** (N tăng đúng số TC mới) · `TestCalibrationAllowedTransitions@2357` (SSoT map↔workflow) + `test_workflow_admin_override` + `test_workflows` (IMM-11 min_states 8 / min_transitions 11) đều **GREEN (0 regression)** · **0 `bench migrate`** (db.set_value sync live) · **0 đổi FE** (`CalibrationDetailView` + `calibrationButtonGating` dùng `allowed_transitions` status-keyed; FE calibration KHÔNG đọc `workflow_state` — verified grep=none).

## III.5. Integration — Audit chain integrity

File `assetcore/tests/test_imm11_audit.py` (⬜ Planned). 2 test chính:
- (a) Sau lifecycle Scheduled → … → Passed (N mutation qua `_transition_asset`), chain hash SHA-256 hợp lệ end-to-end → `verify_audit_chain(asset) == True`.
- (b) Tamper 1 entry `IMM Audit Trail` (sửa hash/change_summary) → verify trả `chain_broken=true`.
- (c) User KHÔNG có quyền delete `IMM Asset Calibration` đã submit (BR-11-05) → throw.

Trace: 04 §Audit Trail · `IMM Audit Trail` DocType · VI.3.

## III.6. API test

File `assetcore/tests/test_imm11_api.py` (⬜ Planned). 18 endpoint trong `api/imm11.py`.

| Test | Endpoint | Verify | Kỹ thuật |
|---|---|---|---|
| `test_list_default_pagination` | `list_calibrations` | `success=true`, page=1, page_size=20 | Use Case |
| `test_list_filter_status` | `list_calibrations` (filters status) | mọi row status đúng | EP |
| `test_get_existing` | `get_calibration` | `success=true`, fields đầy đủ | Use Case |
| `test_get_not_found` | `get_calibration` (FAKE) | `code=NOT_FOUND` | Error guessing |
| `test_create_external` | `create_calibration` (External) | `success=true`, CAL name trả về | Use Case |
| `test_create_low_role_forbidden` | `create_calibration` (role AssetCore System User) | `code=FORBIDDEN` / 403 | EP (permission partition) |
| `test_submit_pass_updates_asset` | `submit_calibration` all Pass | asset next_calibration_date updated | Use Case |
| `test_submit_fail_creates_capa` | `submit_calibration` 1 OOT | CAPA created, asset OOS | Decision Table |
| `test_send_to_lab_post_only` | `send_to_lab` (GET) | method not allowed (POST-only) | Error guessing |
| `test_receive_certificate` | `receive_certificate` (POST) | status → Certificate Received | State Transition |
| `test_cancel_calibration` | `cancel_calibration` (POST) | status → Cancelled (docstatus=0) | State Transition |
| `test_add_measurement_oot` | `add_measurement` measured OOT | row `pass_fail=Fail` | BVA |
| `test_get_due_calibrations` | `get_due_calibrations?days=30` | list trong 30 ngày | BVA |
| `test_get_kpis` | `get_calibration_kpis` | fields compliance/oot/capa rate | Use Case |
| `test_get_dashboard` | `get_calibration_dashboard` | KPI card data | Use Case |

Cover: envelope `success=true` · invalid params `INVALID_PARAMS` · no permission `FORBIDDEN` · pagination boundary · idempotent retry.

## III.7. E2E browser (Playwright)

⬜ Planned. Dùng cho flow UI khó cover bằng API: dropdown lab cascade theo calibration_type, modal confirm Fail (OOS + CAPA warning), workflow button visibility theo role (Calibration User không thấy nút Phê duyệt — chỉ System Manager).

**Golden scenario — External Track Pass**: tạo từ Commissioning → Dashboard due soon → tạo CAL → Gửi Lab → Nhận certificate → nhập measurements all Pass → Submit → asset dates cập nhật + ALE created.

**Golden scenario — Fail + CAPA**: submit 1 OOT → dialog cảnh báo → confirm → asset OOS + CAPA + lookback populated → close CAPA → recalibration Pass → asset Active + event `calibration_conditionally_passed`.

Trace: `assetcore-test` skill Phần 2 (Playwright MCP recipes + R-1..R-9).

## III.8. Performance test

⬜ Planned (chưa thực thi). Target only — chưa có baseline đo được.

| Metric | Target | Method |
|---|---|---|
| `list_calibrations` p95 (200 CAL) | ≤ 800ms | k6 ramping 20 VU |
| `submit_calibration` (10 measurement) p95 | ≤ 1.5s | k6 POST |
| `get_calibration_kpis` p95 | ≤ 2s | k6 |
| Scheduler `create_due_calibration_wos` (500 schedule) | ≤ 30s | `time bench execute …` |
| Scheduler `check_calibration_expiry` (500 asset) | ≤ 30s | `time bench execute …` |

## III.9. Test data & Fixtures

| Loại | Cách seed | File |
|---|---|---|
| Master data (Asset Category, Vendor, Device Model) | `fixtures/*.json` (qua `bench migrate`) | `assetcore/fixtures/` |
| Backend test fixtures | helper `_make_asset` / `_ensure_cat` (prefix `_Test`) | `assetcore/tests/test_imm11.py` |
| AC Supplier (Calibration Lab) | ⬜ Planned `tests/fixtures/test_cal_labs.json` | 2 lab (VLAS-T-028, VLAS-T-001) |
| UAT seed | ⬜ Planned Python script | `assetcore/scripts/uat/uat_imm11.py` |

UAT data phải thực tế (tên bệnh viện VN, mã NCC chuẩn). Test fixture mới dùng prefix `_Test` (xem `assetcore-test` R-0/R-1).

## III.10. Run commands & Coverage gate

```bash
# Module test (✅ chạy được)
bench --site miyano run-tests --app assetcore --module assetcore.tests.test_imm11
# Coverage
coverage run -m unittest assetcore.tests.test_imm11 && coverage report
# Workflow smoke
bench --site miyano run-tests --module assetcore.tests.test_workflows
```

| Layer | Target coverage | Đo | Trạng thái |
|---|---|---|---|
| Service (`services/imm11.py`) | ≥ 85% line + ≥ 80% branch | `coverage --branch` | *(Cần khảo sát — chỉ 3 fn có test live)* |
| DocType lifecycle | ≥ 70% | `coverage report` | ⬜ Planned |
| API (`api/imm11.py`) | ≥ 60% | `coverage report` | ⬜ Planned |
| Frontend (vue-tsc) | 0 error | `npm run build` | *(Cần khảo sát)* |

---

# Phần IV — Traceability Matrices

> Mọi test ở Phần III phải xuất hiện ở cả 3 bảng.

## IV.1. US → Test mapping

| US ID | AC | Test ID (III.x) | Layer | Status |
|---|---|---|---|---|
| US-11-01 | AC-01 Due Soon (SoT Schedule.next_due) | `test_get_due_calibrations`, `TestCalibrationSoTPredicate` | API + Unit | ⬜ Planned |
| US-11-01 | AC-02 Overdue (SoT Schedule.next_due) | `TestCalibrationSoTPredicate::test_overdue` | Unit | ⬜ Planned |
| US-11-01 | AC-11-11 Mint-gap (next_calibration_date NULL vẫn đếm) | `TestCalibrationCountDrillParity::test_mint_only_schedule` | Unit | ⬜ Planned |
| US-11-02 | AC-01 in-tolerance Pass | `TestAddMeasurement::test_in_tolerance_pass` | Unit | ⬜ Planned |
| US-11-02 | AC-02 OOT Fail | `TestAddMeasurement::test_oot_fail` | Unit | ⬜ Planned |
| US-11-03 | AC-11-34 persist (data-loss fix, RED-first) | `TestUpdateCalibrationMeasurements::TC-11-MEASDIFF-01` | Unit + API | ⬜ Planned |
| US-11-03 | AC-11-35 SSoT server-compute (không tin client) | `TestUpdateCalibrationMeasurements::TC-11-MEASDIFF-02/03a` | Unit | ⬜ Planned |
| US-11-03 | AC-11-36 replace-set count==payload | `TestUpdateCalibrationMeasurements::TC-11-MEASDIFF-04/05` | Unit | ⬜ Planned |
| US-11-03 | AC-11-37/38 guard submit/status (409) | `TestUpdateCalibrationMeasurements::TC-11-MEASDIFF-06/07` | Unit | ⬜ Planned |
| US-11-03 | AC-11-39 backward-compat / NO_FIELDS | `TestUpdateCalibrationMeasurements::TC-11-MEASDIFF-08a/b/c` | Unit | ⬜ Planned |
| US-11-03 | AC-11-40 idempotent replace-set | `TestUpdateCalibrationMeasurements::TC-11-MEASDIFF-09` | Unit | ⬜ Planned |
| US-11-03 | FE persist + re-fetch server pass_fail | `CalibrationDetailView` vitest (real store) | FE Unit | ⬜ Planned |
| US-11-03 | AC-11-47 CERTGUARD chặn gửi-lại phiếu ĐÃ có chứng chỉ + vết nguyên trạng (409) | `TestSendToLabCertGuard::TC-11-SENDLAB-CERTGUARD-01` (RED-first) | Unit + API | ⬜ Planned |
| US-11-03 | AC-11-48 regression — `Scheduled` (`certificate_file` rỗng) VẪN gửi-lab OK | `TestSendToLabCertGuard::TC-11-SENDLAB-CERTGUARD-02` | Unit | ⬜ Planned |

## IV.2. BR → Test mapping

| BR ID | Phát biểu (rút gọn) | Test ID | Kỹ thuật | Happy / Negative |
|---|---|---|---|---|
| BR-11-01 | External: lab ISO 17025 + cert + accreditation | `test_external_blocks_*` (III.3) | Decision Table | 1 / 3 |
| BR-11-02 | Fail → OOS + CAPA | `TestCalibrationFail`, `test_on_submit_fail_triggers_capa` | Decision Table | 1 / 1 |
| BR-11-03 | Lookback cùng device_model | `TestLookback` | EP + Path | 1 / 2 |
| BR-11-04 | next_cal (Schedule + phiếu) = certificate_date + interval (Asset-cache next_calibration_date nay = MIN rollup, xem BR-11-13) | `TestCalibrationPass`, `test_on_submit_pass_updates_asset` | BVA | 1 / 1 |
| BR-11-05 | Immutable sau Submit; Amend cần reason | `test_on_cancel_blocked_after_submit`, `test_on_trash_blocked_after_submit` | Error guessing | 1 / 2 |
| BR-11-06 | Decommissioned → suspend Schedule | *(Cần khảo sát — test chưa định danh)* | EP | ⬜ |
| BR-11-07 | gate `validate_asset_for_operations` (trừ recalibration) | `TestAssetGate` | Decision Table | 1 / 1 |
| BR-11-08 | SoT predicate biên + count==drill + mint-gap | `TestCalibrationSoTPredicate`, `TestCalibrationCountDrillParity` (test_imm11) + `test_dashboard` parity | BVA + EP | nhiều |
| BR-11-08b | FAIL → Schedule due-now (asset FAIL vào overdue/due-soon, hết mask ON_SCHEDULE) | `TestCalibrationFailDueNow` (TC-CAL-FAIL-DUE-01..07; RED-prove 01/02/04) ✅ Live + FE `calFailDueNow.test.ts` ✅ | Decision Table + BVA + Path | 7 / 2 |
| BR-11-09 | De-dup theo asset | `TestCalibrationSoTDedup` | EP | 1 / 1 |
| BR-11-10 | Stale-clear (hết active schedule → Not Required) | `TestCheckCalibrationExpiryRollup` (TC-11-ROLLUP-STALE) | Decision Table | 1 / 1 |
| BR-11-11 | FAILED-preserve terminal (OoS) | `TestCheckCalibrationExpiryRollup` (TC-11-ROLLUP-FAILED*) | Decision Table | 1 / 2 |
| BR-11-12 | Recalibration OoS-restore governance guard (chủ-hold == calibration ∧ 0 hold khác) | `TestCalibrationRestoreGuard` (TC-11-RESTORE-*) | Decision Table + Path | 2 / 3 |
| BR-11-13 | PASS → Asset-cache rollup đa-lịch (worst-of-all + MIN next_due; ROLLUP-CONSISTENCY với scheduler; happy 1-lịch bất biến) | `TestCalibrationPassRollup` (TC-11-PASS-ROLLUP-01..07 + N1; RED-prove 01/03) + FE verify §06 §7c-quater | Decision Table + BVA + Path | 5 / 3 |
| BR-11-16 | `update_calibration` `measurements` child-diff replace-set (data-loss fix + SSoT server-compute + guard docstatus/status + backward-compat) | `TestUpdateCalibrationMeasurements` (TC-11-MEASDIFF-01..10; RED-first 01) + FE `CalibrationDetailView` vitest (§06 §3.3-bis) | Decision Table + BVA + Error guessing | 5 / 4 |
| BR-11-18 | `send_to_lab` chặn gửi-lại phiếu ĐÃ có chứng chỉ — bảo toàn vết `sent_date` NĐ98 (guard `certificate_file`-presence, 409, raise-before-mutate; KHÔNG chặn `Scheduled`) | `TestSendToLabCertGuard` (TC-11-SENDLAB-CERTGUARD-01/02; RED-first 01) | State Transition + Error guessing | 2 / 1 |

### BR-11-12 — test cases bắt buộc (recalibration OoS-restore governance guard)

| TC ID | Given | When | Then | AC |
|---|---|---|---|---|
| TC-11-RESTORE-CALIBRATING | asset đang `Calibrating` | cal Pass submit | restore `Calibrating → Active`; ALE `calibration_passed` from=Calibrating to=Active (nhánh A KHÔNG đổi) | AC-11-14 |
| TC-11-RESTORE-SELF-OOS | asset `Out of Service` do cal-fail trước (ALE mới nhất vào OoS `root_doctype='IMM Asset Calibration'`) + KHÔNG hold khác | recal Pass | restore `OoS → Active`; ALE `calibration_passed` to=Active | AC-11-15 |
| TC-11-RESTORE-INCIDENT-HOLD | asset `Out of Service` do Incident (IMM-12, ALE root='Incident Report') | recal Pass | GIỮ `Out of Service`; 1 ALE `calibration_passed` from=OoS to=OoS + note `giữ Ngừng hoạt động do hạng mục khác (Sự cố...)` | AC-11-16 |
| TC-11-RESTORE-REPAIR-HOLD | asset `Out of Service` do Repair (IMM-09, ALE root='Asset Repair') | recal Pass | GIỮ OoS; ALE hold-note nguồn Sửa chữa | AC-11-16 |
| TC-11-RESTORE-PM-HOLD | asset `Out of Service` do PM-finding (IMM-08, ALE root='PM Work Order') | recal Pass | GIỮ OoS; ALE hold-note nguồn Bảo trì | AC-11-16 |
| TC-11-RESTORE-CONCURRENT | asset OoS do cal-fail NHƯNG còn ≥1 Incident mở / Repair WO mở / PM WO OoS-finding mở | recal Pass | GIỮ OoS (không restore); hold-note nêu hold còn lại | AC-11-17 |
| TC-11-RESTORE-NORAISE-DECOM | asset OoS rồi bị `Decommissioned` giữa chừng | recal Pass submit | on_submit KHÔNG raise `InvalidAssetTransition`, phiếu đóng được; KHÔNG ép Active; ALE audit ghi | AC-11-18 |
| TC-11-RESTORE-IDEMPOTENT | TC-11-RESTORE-SELF-OOS chạy lại cùng cal Pass | re-run | KHÔNG tạo ALE `activated` trùng (transition no-op prev==to) | AC-11-18 |
| TC-11-RESTORE-GREPGUARD | static/grep `handle_calibration_pass` | inspect | 0 nhánh `_transition_asset(..., ACTIVE)` từ prev=OoS NGOÀI block `if _can_restore_from_oos(...)` | AC-11-18 |

> Class mới `TestCalibrationRestoreGuard` (`tests/test_imm11.py`). Bắt buộc no-regression: `test_imm11`, `test_workflows`, `test_dashboard`, `test_imm09`, `test_imm12` GREEN. Predicate `_can_restore_from_oos` lazy-import `open_incident_filter`/`open_repair_filter` → KHÔNG tạo circular import (verify `bench start` không `ImportError`). KPI/dashboard shape KHÔNG đổi → FE `vue-tsc` 0.

### BR-11-08b — test cases bắt buộc (FAIL → Schedule due-now)

> **Class mới `TestCalibrationFailDueNow` (`tests/test_imm11.py`).** RED-prove TRƯỚC khi sửa: với code hiện tại (`handle_calibration_fail` KHÔNG chạm `Schedule.next_due_date`), asset FAIL có schedule active giữ `next_due` tương lai → asset KHÔNG nằm trong `_overdue_asset_ids()` cũng KHÔNG `_due_soon_asset_ids()` → TC-11-FAIL-DUENOW-01 FAIL (chứng minh mask). Sau khi thêm write-path (§04 §4.1.6) → GREEN.

| TC ID | Given | When | Then | Trace |
|---|---|---|---|---|
| TC-11-FAIL-DUENOW-01 | asset Active có active schedule (`is_active=1`) `next_due = today+200` (ON_SCHEDULE, asset KHÔNG trong overdue/due-soon set) — **RED-prove bug** | submit IMM Asset Calibration `overall_result=Fail` (basis=actual_date=today) | schedule `next_due == today` (`<= today`) → asset ∈ `_due_soon_asset_ids()` (due-now); KHÔNG còn ON_SCHEDULE; asset rời tập on-schedule | AC-11-19, BR-11-08b |
| TC-11-FAIL-DUENOW-01b | như trên nhưng `certificate_date = today-5` (basis quá khứ) | submit Fail | schedule `next_due == today-5 < today` → asset ∈ `_overdue_asset_ids()` | AC-11-19 |
| TC-11-FAIL-DUENOW-02 | asset có **2** active schedule (External+In-House) cùng `next_due` tương lai | submit Fail | **CẢ 2** schedule `next_due == basis` (theo asset, không chỉ `cal_doc.calibration_schedule`); asset đếm 1 lần (de-dup BR-11-09) trong overdue-or-due | AC-11-19, BR-11-09 |
| TC-11-FAIL-DUENOW-03 (KPI parity) | dataset có asset FAIL due-now | `get_calibration_kpis()` / `get_dashboard()` | `overdue_assets + due_soon_assets` GỒM asset FAIL; con số == số dòng drill `?overdue=1` ∪ `?due_soon=1` (count==drill, KHÔNG undercount) | AC-11-19, BR-11-08 |
| TC-11-FAIL-DUENOW-04 (null-safe) | asset FAIL **KHÔNG** có schedule active (is_active=1) | submit Fail | `handle_calibration_fail` no-op trên schedule, KHÔNG raise, phiếu đóng được; CAPA + Incident + lookback vẫn tạo (đường FAIL bất biến) | AC-11-20 |
| TC-11-FAIL-DUENOW-05 (idempotent) | asset đã due-now sau FAIL | resubmit/amend cùng basis (hoặc chạy lại) | `next_due` bất biến == basis; KHÔNG dời kép | AC-11-20 |
| TC-11-FAIL-DUENOW-06 (state bất biến) | asset FAIL | sau write-path | `lifecycle_status == Out of Service` (do transition), `calibration_status == Calibration Failed` (BR-11-11), `is_active` schedule GIỮ 1 (vẫn được KPI đếm); KHÔNG ép state vòng đời khác | AC-11-20 |
| TC-11-FAIL-DUENOW-07 (khép kín) | asset due-now sau FAIL | recalibration **Pass** (`handle_calibration_pass`, basis+interval) | `next_due` advance về tương lai → asset RỜI overdue/due-soon → ON_SCHEDULE; vòng đời fail→due-now→pass→on-schedule khép kín | AC-11-20, BR-11-04 |
| TC-11-FAIL-DUENOW-08 (PASS regression) | asset Active có schedule | submit **Pass** | `next_due == basis + interval` (tương lai) BẤT BIẾN — fix KHÔNG đổi nhánh PASS | BR-11-04 |
| TC-11-FAIL-DUENOW-N1 (no N+1) | asset 2 schedule active | submit Fail | write-path dùng 1 `CalibrationScheduleRepo.list({asset, is_active=1})` (1 query) + loop set_values — KHÔNG query-per-schedule trên list | INV-FAIL-DUENOW-2 |

> Fixture: asset prefix `_Test` + `_purge_asset_with_deps` teardown (purge schedule + CAPA + Incident + ALE leak). Bắt buộc no-regression: `test_imm11`, `test_workflows`, `test_dashboard` GREEN. SoT helper `_overdue_asset_ids`/`_due_soon_asset_ids` KHÔNG đổi (fix chỉ chạm write-path FAIL) → SoT parity + dashboard không regress.

### BR-11-08 / BR-11-09 — test cases bắt buộc (SoT calibration due/overdue)

| TC ID | Given | When | Then |
|---|---|---|---|
| TC-11-SOT-BVA-OVERDUE | active Schedule `next_due = today-1` | `is_calibration_overdue` / `_overdue_asset_ids` | True / asset có trong tập overdue |
| TC-11-SOT-BVA-TODAY | active Schedule `next_due = today` | predicate | overdue=False, **due_soon=True** (biên `today` thuộc due_soon) |
| TC-11-SOT-BVA-W30 | active Schedule `next_due = today+30` | predicate | due_soon=True (biên trên inclusive) |
| TC-11-SOT-BVA-W31 | active Schedule `next_due = today+31` | predicate | due_soon=False, on_schedule |
| TC-11-SOT-MINT | asset `is_calibration_required` minted (AC Asset.next_calibration_date NULL) nhưng `Schedule.next_due < today` | `get_calibration_kpis` + dashboard `calib_overdue` | **CẢ 2** đếm asset này (count == drill, mint-gap đóng) |
| TC-11-SOT-DEDUP | 1 asset có 2 active schedule cùng overdue | `_overdue_asset_ids` + KPI + drill | đếm **1** theo asset (không double-count theo row) |
| TC-11-SOT-DECOM | asset Decommissioned có active schedule overdue | KPI + dashboard | KHÔNG đếm (loại theo `lifecycle_status NOT IN Decommissioned`) |
| TC-11-SOT-INACTIVE | schedule `is_active=0`, `next_due < today` | KPI + dashboard | KHÔNG đếm (chỉ active) |
| TC-11-SOT-PARITY | dataset hỗn hợp | so `get_calibration_kpis().overdue_assets` vs `dashboard.get_overview().calibration.overdue` | bằng nhau (cùng SoT) |
| TC-11-SOT-IDEMPOTENT | chạy `check_calibration_expiry` 2 lần | so kết quả + notify | status không đổi lần 2; notify chỉ phát khi status THỰC SỰ đổi |
| TC-11-ROLLUP-STALE | asset cache=`Overdue`, lịch DUY NHẤT `is_active=0` (rollup map không còn asset) | `check_calibration_expiry()` | `calibration_status ∈ {Not Required, ''}` — KHÔNG giữ `Overdue` (BR-11-10, AC-11-12) |
| TC-11-ROLLUP-FAILED | sau `handle_calibration_fail` (cache=`Calibration Failed`, lifecycle=`Out of Service`, còn active schedule overdue) | `check_calibration_expiry()` | cache GIỮ `Calibration Failed` — KHÔNG ghi đè Overdue/Due Soon/On Schedule (BR-11-11, AC-11-13) |
| TC-11-ROLLUP-FAILED-IDEMP | TC-11-ROLLUP-FAILED chạy 2 lần | `check_calibration_expiry()` ×2 | lần 2 `new==old` → no-op, `notify_calibration_due` KHÔNG gọi lại (anti-spam preserve) |
| TC-11-ROLLUP-RECOVER | asset từng FAILED, recal Pass đưa về Active (`handle_calibration_pass`), còn active schedule trong window | `check_calibration_expiry()` | cache tiếp quản bằng SoT rollup (On Schedule/Due Soon/Overdue) — KHÔNG kẹt FAILED |

> 4 case rollup mới mở rộng class `TestCheckCalibrationExpiryRollup` (`tests/test_imm11.py`) — phải GIỮ 2 case idempotent/anti-spam cũ xanh. SoT count helper (`_overdue_asset_ids`/`_due_soon_asset_ids`/`_calibration_status_asset_ids`) KHÔNG đổi → `test_dashboard` + SoT parity không regress.

### BR-11-13 — test cases bắt buộc (PASS → Asset-cache rollup đa-lịch)

> **Class mới `TestCalibrationPassRollup` (`tests/test_imm11.py`).** RED-prove TRƯỚC khi sửa: với code hiện tại (`handle_calibration_pass` hardcode `calibration_status=ON_SCHEDULE` + `next_calibration_date=basis+interval` của 1 lịch), asset 2-lịch (A overdue + B Pass) sau Pass(B) → cache `On Schedule` + next tương lai → TC-11-PASS-ROLLUP-01/03 FAIL (chứng minh divergence + rớt due-list). Sau khi thay block bằng `_apply_asset_calibration_rollup` (§04 §4.1.7) → GREEN.

| TC ID | Given | When | Then | Map |
|---|---|---|---|---|
| TC-11-PASS-ROLLUP-01 | asset X có 2 active schedule: A `next_due=today-10` (OVERDUE) + B `next_due=today+5` | `handle_calibration_pass(cal B)` (basis=today) — **RED-prove bug** | `AC Asset.calibration_status == 'Overdue'` (KHÔNG `On Schedule`); == `_calibration_status_asset_ids()[X]` | AC-11-21, BR-11-13 |
| TC-11-PASS-ROLLUP-02 | như trên | sau Pass(B) | schedule B `next_due_date == today + interval` (BR-11-04 advance bất biến); schedule A `next_due_date` KHÔNG đổi (`today-10`) | AC-11-21, BR-11-04 |
| TC-11-PASS-ROLLUP-03 | như trên | sau Pass(B) + `get_due_calibrations(days=30)` | asset X ∈ `.items` (KHÔNG rớt); `AC Asset.next_calibration_date == today-10` (= MIN trên A,B = schedule A) | AC-11-21, INV-PASS-ROLLUP-2/4 |
| TC-11-PASS-ROLLUP-04 (consistency) | asset X multi-schedule sau Pass(B) | `check_calibration_expiry()` chạy NGAY sau | `AC Asset.calibration_status` KHÔNG đổi (PASS-rollup == scheduler-rollup); `_reconcile` thấy new==old → no-write, `notify_calibration_due` KHÔNG gọi (no flip-flop, no spam) | AC-11-22, INV-PASS-ROLLUP-3 |
| TC-11-PASS-ROLLUP-05 (due-soon rollup) | asset có A `next_due=today+10` (DUE_SOON) + B Pass | Pass(B) | `calibration_status == 'Due Soon'`; `next_calibration_date == MIN` (= A nếu A < B-advanced) | AC-11-21, BR-11-13 |
| TC-11-PASS-ROLLUP-06 (HAPPY 1-lịch bất biến) | asset chỉ 1 active schedule | Pass | `calibration_status == 'On Schedule'`; `next_calibration_date == add_days(basis, interval)`; hành vi == bản cũ 100% | AC-11-23, INV-PASS-ROLLUP-4 |
| TC-11-PASS-ROLLUP-07 (BR-11-12 bất biến) | asset multi-schedule trong các nhánh restore (Calibrating / OoS self-hold / OoS other-hold) | Pass | restore-guard 3-nhánh + ALE `calibration_passed` (đúng 1 record) + `CalibrationRepo.next_calibration_date` KHÔNG đổi bởi rollup (chỉ 3 field ASSET-cache đổi nguồn) | AC-11-23, INV-PASS-ROLLUP-5 |
| TC-11-PASS-ROLLUP-N1 (no N+1) | asset 3 active schedule | Pass | rollup ghi cache = số query bounded (≤4), KHÔNG loop per-schedule SQL (đếm query hoặc assert dùng `_calibration_status_asset_ids` set-query + 1 MIN aggregate) | AC-11-21, INV-PASS-ROLLUP-6 |

> Fixture: asset prefix `_Test` + `_purge_asset_with_deps` teardown (purge schedule + ALE leak). No-regression bắt buộc: `test_imm11` + `test_workflows` + `test_dashboard` GREEN; FE vue-tsc prod 0 + vitest full GREEN. SoT helper (`_overdue_asset_ids`/`_due_soon_asset_ids`/`_calibration_status_asset_ids`) + `CalibrationScheduleRepo` advance (BR-11-04) + restore-guard (BR-11-12) KHÔNG đổi → parity không regress.

### BR-11-14 — test cases bắt buộc (read-side derived flags `is_overdue`/`is_due_soon`)

> **Class mới `TestCalibrationReadFlags` (`tests/test_imm11.py`).** Cố định ref-date (dùng `add_days(nowdate(), …)` cho `next_calibration_date` của record) để loại race qua-nửa-đêm. Fixture: 1 asset `_Test` + phiếu hiệu chuẩn với `next_calibration_date` set theo case; `_purge_asset_with_deps` teardown. RED-before: chưa emit cờ → `KeyError`/`assert 0==1` FAIL; GREEN-after: sau khi list_calibrations/get_calibration bọc `int(predicate(...))` (§04 §4.1.8) → PASS.

| TC ID | Given (`next_calibration_date` của record) | When | Then | Map |
|---|---|---|---|---|
| TC-11-CALFLAG-OVERDUE | `today - 1` | `get_calibration(cal)` | `is_overdue == 1` ∧ `is_due_soon == 0` (int) | AC-11-24a, BR-11-14 |
| TC-11-CALFLAG-DUESOON-LO | `today` (biên dưới inclusive) | `get_calibration(cal)` | `is_due_soon == 1` ∧ `is_overdue == 0` | AC-11-24b |
| TC-11-CALFLAG-DUESOON-HI | `today + CAL_DUE_SOON_WINDOW_DAYS` (biên trên inclusive) | `get_calibration(cal)` | `is_due_soon == 1` ∧ `is_overdue == 0` | AC-11-24b |
| TC-11-CALFLAG-BEYOND | `today + CAL_DUE_SOON_WINDOW_DAYS + 1` | `get_calibration(cal)` | cả hai cờ `== 0` | AC-11-24c |
| TC-11-CALFLAG-NONE | `None` (phiếu Scheduled/In Progress chưa có hạn) | `get_calibration(cal)` | cả hai cờ `== 0` (None-guard) | AC-11-24c, BR-11-14 |
| TC-11-CALFLAG-INT | bất kỳ | `get_calibration(cal)` | `type(is_overdue) is int` ∧ `type(is_due_soon) is int` (KHÔNG bool) | INV-CALFLAG-2 |
| TC-11-CALFLAG-LIST-EACH | list ≥2 record ngày khác nhau | `list_calibrations()` | MỖI row có key `is_overdue`/`is_due_soon` (int 0/1) đúng theo `next_calibration_date` của row | AC-11-25, BR-11-14 |
| TC-11-CALFLAG-PARITY | record X trong 1 dataset | so `list_calibrations()` row-X vs `get_calibration(X)` tại CÙNG ref-date | `row-X.{is_overdue,is_due_soon} == get_calibration(X).{is_overdue,is_due_soon}` | AC-11-25, INV-CALFLAG-1 |
| TC-11-CALFLAG-SHARED | grep-guard / call-graph | `list_calibrations`/`get_calibration` gọi | dùng CHUNG `is_calibration_overdue`/`is_calibration_due_soon` (KHÔNG so-ngày inline mới); 0 query DB thêm (mock/assert repo-call-count không tăng) | AC-11-26, INV-CALFLAG-3 |

> No-regression bắt buộc: `test_imm11` (kể cả `TestCalibrationAllowedTransitions`, list-mine `TestCalibrationListMineScope`) GREEN; `test_mobile_oas` (contract-shape 2 property × 2 schema `integer enum[0,1]`) + `test_mobile_docset` (reconcile `_GUARD_SUITE_SUM`/`_MOBILE_OAS_TOTAL`) GREEN. SoT helper + predicate thuần KHÔNG đổi (chỉ THÊM call-site) → KPI/dashboard/drill parity (BR-11-08/09) không regress. Consumer-audit: `grep` FE/mobile không có nơi so `next_calibration_date` với client-clock (server-flag SSoT).

### BR-11-16 — test cases bắt buộc (`update_calibration` `measurements` child-diff · data-loss fix)

> **Class mới `TestUpdateCalibrationMeasurements` (`tests/test_imm11.py`).** **RED-first (chứng minh data-loss):** với code hiện tại (`_UPDATE_ALLOWED` KHÔNG có `measurements` → strip), `update_calibration(name, {measurements:[N]})` trên draft → `get_calibration(name).measurements` = **0 dòng** → TC-11-MEASDIFF-01 FAIL (data bốc hơi). Sau khi thêm nhánh child-diff replace-set (§04 §4.1.10) → GREEN. Fixture: asset prefix `_Test` + phiếu draft `status ∈ ACTIVE_STATUSES`; `_purge_asset_with_deps` teardown.

| TC ID | Given | When | Then | Map |
|---|---|---|---|---|
| TC-11-MEASDIFF-01 (RED-first / persist) | phiếu draft (`docstatus=0`, `status='In Progress'`), 0 dòng đo | `update_calibration(name, {measurements:[2 dòng valid]})` → `get_calibration(name)` | `.measurements` = **2 dòng** với `measured_value`/`nominal_value`/`tolerance_*` đúng payload | AC-11-34, BR-11-16 |
| TC-11-MEASDIFF-02 (SSoT compute — không tin client) | 1 dòng `nominal=7.5, tol±3%, measured=8.0`, client CỐ gửi `pass_fail='Pass'`/`out_of_tolerance=0` | lưu → reload | dòng có `pass_fail=='Fail'` ∧ `out_of_tolerance==1` (server strip + recompute) | AC-11-35, BR-11-16 |
| TC-11-MEASDIFF-03a (in-tolerance Pass) | 1 dòng `nominal=7.5, tol±3%, measured=7.6` | lưu → reload | `pass_fail=='Pass'` ∧ `out_of_tolerance==0` | AC-11-35 |
| TC-11-MEASDIFF-04 (replace-set — remove) | phiếu có 3 dòng | lưu `measurements`=2 dòng (bỏ 1) → reload | count == **2** (dòng bị bỏ → removed) | AC-11-36, BR-11-16 |
| TC-11-MEASDIFF-05 (replace-set — add) | phiếu có 2 dòng | lưu `measurements`=4 dòng → reload | count == **4** | AC-11-36 |
| TC-11-MEASDIFF-06 (guard submit) | phiếu `docstatus=1`, có sẵn M dòng | `update_calibration(name, {measurements:[khác]})` | `ServiceError` code `CONFLICT` msg `IMM11_ALREADY_SUBMITTED` (http_status 409); reload `.measurements` == M dòng cũ (KHÔNG mutate) | AC-11-37, BR-11-16 |
| TC-11-MEASDIFF-07 (guard status) | phiếu `docstatus=0`, `status='Cancelled'` | `update_calibration(name, {measurements:[...]})` | `ServiceError` code `CONFLICT` msg `IMM11_MEASUREMENTS_NOT_EDITABLE` (409); child table KHÔNG đổi | AC-11-38, BR-11-16 |
| TC-11-MEASDIFF-08a (backward-compat scalar) | phiếu draft | `update_calibration(name, {technician_notes:'x'})` (KHÔNG `measurements`) | hành vi cũ: `technician_notes` set, return `{name,status}`; `measurements` KHÔNG đụng; 0 regression | AC-11-39, BR-11-16 |
| TC-11-MEASDIFF-08b (measurements-only ≠ NO_FIELDS) | phiếu draft | `update_calibration(name, {measurements:[1 dòng]})` (0 scalar) | KHÔNG raise `IMM11_NO_FIELDS`; dòng persist (count==1) | AC-11-39, BR-11-16 |
| TC-11-MEASDIFF-08c (empty patch = NO_FIELDS) | phiếu draft | `update_calibration(name, {})` (0 scalar ∧ 0 key `measurements`) | raise `IMM11_NO_FIELDS` (hành vi cũ giữ) | AC-11-39 |
| TC-11-MEASDIFF-09 (idempotent replace-set) | phiếu draft | lưu CÙNG mảng [N] hai lần liên tiếp → reload | count == **N** (KHÔNG nhân đôi; KHÔNG cần `client_request_id`) | AC-11-40, BR-11-16 |
| TC-11-MEASDIFF-10 (unmeasured row draft-valid) | phiếu draft | lưu 1 dòng `measured_value=None` (chưa đo) → reload | dòng persist; `pass_fail` None (skip compute); submit sau vẫn chặn bởi BR-11-08 IMM11_MEASUREMENT_VALUE_REQUIRED | AC-11-34, BR-11-16 |

> **DoD BR-11-16:** `bench --site miyano run-tests` module-isolated `assetcore.tests.test_imm11` XANH THẬT (`Ran N OK`, N tăng đúng số TC mới); RED-first TC-11-MEASDIFF-01 chuyển GREEN. No-regression: `TestUpdateCalibration`(scalar cũ) + `TestAddMeasurement`(per-row) + `TestCalibrationSubmitGate` GREEN. **0 OAS coupling** (`update_calibration` không mobile-mirror + `**kwargs`) → `test_mobile_oas`/`test_mobile_docset` KHÔNG cần đổi. FE vitest `CalibrationDetailView` (real store + re-fetch) GREEN. Sửa `services/imm11.py` (+ `utils/messages.py` MSG mới) dưới `--preload` → USER reload cho HTTP-live (HARD-STOP); DoD authoritative = `bench run-tests` (KHÔNG curl).

### TC-11-IDEMP-SUBMIT — `submit_calibration` idempotency dedup (BR-11-17 / CR-24-CAL-SUBMIT op#6)

| Test ID | Given | When | Then | AC |
|---|---|---|---|---|
| TC-11-IDEMP-SUBMIT-01 (RED-first — replay wins) | phiếu đủ measurement, `submit_calibration(name, client_request_id='K1')` gọi lần 1 (success, `docstatus→1`) | gọi LẦN 2 CÙNG `K1` | trả `{name,status,overall_result,next_calibration_date}` **byte-đối-byte** == lần 1; KHÔNG raise `IMM11_ALREADY_SUBMITTED`; `docstatus` giữ 1; `CalibrationRepo.submit`/`_lockstep` KHÔNG chạy lần 2 (mock/spy assert 1 lần) | AC-11-41 |
| TC-11-IDEMP-SUBMIT-02 (RED-first — no-op) | `submit_calibration(name)` KHÔNG khoá (header vắng + body rỗng), gọi lần 1 success | gọi LẦN 2 KHÔNG khoá | `ServiceError` code CONFLICT msg `IMM11_ALREADY_SUBMITTED` (backward-compat y hệt hôm nay) | AC-11-42 |
| TC-11-IDEMP-SUBMIT-03 (RED-first — distinct key) | lần 1 `client_request_id='K1'` success | gọi LẦN 2 `client_request_id='K2'` (≠K1) | `IMM11_ALREADY_SUBMITTED` (cache MISS cho K2 → state-guard giữ; KHÔNG nuốt câm) | AC-11-43 |
| TC-11-IDEMP-SUBMIT-04 (source-precedence) | body `client_request_id='Kb'` + header `X-Idempotency-Key='Kh'` (Kb≠Kh) | 2 call cùng cặp | dedup theo **Kb** (body thắng); riêng header-only (body rỗng) → dedup theo Kh (`resolve_idempotency_key` SHARED) | AC-11-44 |
| TC-11-IDEMP-SUBMIT-05 (not-found intact) | phiếu `∄` | `submit_calibration(name=∄, client_request_id='K')` | `IMM11_CAL_NOT_FOUND` (pre-check MISS → get → not-found) | AC-11-45 |
| TC-11-IDEMP-SUBMIT-06 (race winner-reread) | `docstatus==1` + winner concurrent CÙNG khoá đã cache GIỮA pre-check và guard (giả lập cache HIT tại guard-recheck) | call CÙNG khoá | trả cached (KHÔNG raise); khoá không khớp → `IMM11_ALREADY_SUBMITTED` | AC-11-46/AC-11-41 |

> **DoD BR-11-17:** `bench --site miyano run-tests` module-isolated `assetcore.tests.test_imm11` XANH THẬT (`Ran N OK`); RED-first TC-11-IDEMP-SUBMIT-01/02/03 chuyển GREEN. No-regression: `TestCalibrationSubmitGate` (submit gate) + `TestAddMeasurement` (§4.1.9 dedup) GREEN. **COUPLED OAS slice (KHÁC BR-11-16):** `submit_calibration` CÓ mobile-mirror + live-sig guard EXACT ⇒ `test_mobile_oas` PHẢI đổi (`_SUBMIT_CAL_REQUEST_PROPS {name}→{name,client_request_id}` + prop-optional TC + `_EXPECTED_TEST_COUNT`) + `test_mobile_docset` (`_GUARD_SUITE_SUM`/`_MOBILE_OAS_TOTAL`/`_GUARD_SUITE_EXPECTED`) + OAS `SubmitCalibrationRequest` +prop — land **cùng lượt** với `.py` (Self-Correction: acceptance "test_mobile_oas unchanged" SAI — xem `05 §0.1.4-IDEMP-SUBMIT`). `oas_baseline.BASELINE_TOTAL` GIỮ (0 whitelist mới) → `test_oas_baseline` XANH KHÔNG đổi. Sửa `api/imm11.py`+`services/imm11.py` dưới `--preload` → USER reload cho HTTP-live (HARD-STOP); DoD authoritative = `bench run-tests` (KHÔNG curl — gunicorn `--preload` stale, LL-DEPLOY-07).

DoD: mọi BR có ≥ 1 happy + ≥ 1 negative. `TestCalibrationSubmitGate` (✅ Live) đã cover gate before_submit (CAL-004).

### TC-11-SENDLAB-CERTGUARD — `send_to_lab` chặn gửi-lại phiếu ĐÃ có chứng chỉ (BR-11-18 / CR-59)

> **Class mới `TestSendToLabCertGuard` (`tests/test_imm11.py`).** **RED-first (chứng minh corruption):** với code hiện tại (`send_to_lab` KHÔNG kiểm `certificate_file`), tạo phiếu External → `send_to_lab` (`sent_date=D0`) → `receive_certificate` (`certificate_file` set, `status='In Progress'`) → `send_to_lab` LẦN 2 → `sent_date` bị **ghi đè** ≠ D0 ⇒ TC-11-SENDLAB-CERTGUARD-01 FAIL (vết NĐ98 corrupt). Sau khi thêm guard `if doc.certificate_file` (§04 §ADR-IMM11-CERTGUARD) → GREEN (409 + vết nguyên trạng). Fixture: asset prefix `_Test` + phiếu External; `_purge_asset_with_deps` teardown.

| TC | Given | When | Then | AC |
|---|---|---|---|---|
| TC-11-SENDLAB-CERTGUARD-01 (RED-first — chặn + vết nguyên trạng) | phiếu **External** đã `send_to_lab` (`sent_date=D0`) + `receive_certificate` (`certificate_file` set, `certificate_date=Dc`, `status='In Progress'`) | `send_to_lab(name)` LẦN 2 | `ServiceError`/Error-envelope code `IMM11_SEND_LAB_ALREADY_CERTIFIED` (`http_status=409`, `body.message_code='IMM11-SEND-LAB-ALREADY-CERTIFIED'`); reload DB `sent_date==D0` ∧ `certificate_file` unchanged ∧ `status=='In Progress'` (0 mutate) | AC-11-47, BR-11-18 |
| TC-11-SENDLAB-CERTGUARD-02 (regression — luồng hợp lệ) | phiếu **External** `status='Scheduled'` (`certificate_file` **rỗng**) | `send_to_lab(name)` | thành công → reload `status=='Sent to Lab'` ∧ `sent_date` set (guard KHÔNG chặn phiếu chưa-có-chứng-chỉ) | AC-11-48, BR-11-18 |

> **DoD BR-11-18:** `bench --site miyano run-tests --module assetcore.tests.test_imm11` module-isolated XANH (`Ran N OK`) gồm ≥2 test mới; RED-first TC-11-SENDLAB-CERTGUARD-01 chuyển GREEN sau guard. No-regression: `TestSendReceiveLab` GREEN. **KHÔNG `bench migrate`** (field `certificate_file`/`sent_date`/`status` đã tồn tại). **Coupled FE-regen:** MSG code mới ⇒ `python scripts/gen_fe_messages.py` → `messages.ts` (chống SYS-500). **OAS mirror:** đã curate (op `sendToLab`, mã mới trong 200-oneOf Error branch) — `test_mobile_oas` 893 OK / `test_mobile_docset` 9 OK (BA verified, 0 baseline bump). Sửa `services/imm11.py`+`utils/messages.py` dưới `--preload` → USER reload; DoD authoritative = `run-tests` (KHÔNG curl — LL-DEPLOY-07).

## IV.3. Component → Test mapping

| Component (I.1) | Test ID | Test layer | Coverage % | Risk priority (I.3) |
|---|---|---|---|---|
| `create_calibration` | `TestCalibrationCreation` (✅ Live) | Unit | *(Cần khảo sát)* | Medium |
| `cancel_calibration` | `TestCalibrationCancellation` (✅ Live) | Unit | *(Cần khảo sát)* | Low |
| `submit_calibration` + gate | `TestCalibrationSubmitGate` (✅ Live) | Unit | *(Cần khảo sát)* | High |
| `handle_calibration_fail` | `TestCalibrationFail` (⬜) | Unit | ⬜ | **Critical** |
| `handle_calibration_pass` | `TestCalibrationPass` (⬜) | Unit | ⬜ | **Critical** |
| validators VR-11-01/02 | `test_external_blocks_*` (⬜) | Integration | ⬜ | **Critical** |
| Workflow 13 transition | `test_imm11_workflow.py` (⬜) | Integration | ⬜ | High |
| API endpoints | `test_imm11_api.py` (⬜) | API | ⬜ | Low–High |

---

# Phần V — UAT Script

## V.1. Phạm vi UAT

- **In-scope**: Schedule auto từ Commissioning (IMM-04); External validate lab ISO 17025/cert/accreditation (BR-11-01); Submit Pass cập nhật asset dates (BR-11-04); Submit Fail → OOS + CAPA + Lookback (BR-11-02/03); In-House không cần cert; Immutability (BR-11-05); CAPA lifecycle → Recalibration → Asset Active; Compliance Dashboard + KPI; Scheduler.
- **Out-of-scope**: Performance (III.8), Security (Phần VI), OCR PDF, API integration lab bên ngoài.
- **Pre-condition**: site UAT deploy version hiện hành, seed `uat_imm11.py` (⬜ Planned), tester accounts (V.2) active, Chrome/Edge ≥ 120.

## V.2. Tester accounts

| Username | Email | Role | Vai trò UAT |
|---|---|---|---|
| `manager.cal` | manager.cal@hospital.vn | Calibration Manager | Tạo lịch, chọn lab, phê duyệt |
| `ktv.cal` | ktv.cal@hospital.vn | Calibration User | Gửi lab, nhập kết quả, upload cert |
| `qa.cal` | qa.cal@hospital.vn | Compliance Manager | Review CAPA, Lookback, close CAPA |
| `viewer.cal` | viewer.cal@hospital.vn | AssetCore System User | Verify role thấp (FORBIDDEN case) |

Mật khẩu UAT: `Assetcore@2026` (reset sau UAT). Phải có account role thấp để cover FORBIDDEN (không chỉ Admin).

## V.3. Test data đã seed

| DocType | Số lượng | Ghi chú |
|---|---|---|
| AC Asset | 7 | mix status, model, overdue/due soon |
| AC Supplier (Calibration Lab) | 2 | vendor_type = Calibration Lab; 1 có ISO 17025, 1 không (cho negative) |
| IMM Device Model | 4 | với `calibration_interval_days` |
| IMM Calibration Schedule | 7 | 1/asset, interval từ Device Model |
| Sample Certificate PDF | 1 | cho External upload |

Reset script (⬜ Planned): `bench --site uat.assetcore.vn execute assetcore.scripts.uat.uat_imm11.seed_data`.

## V.4. UAT Scenarios — Suy ra từ US + State Machine

Mỗi scenario theo template Phụ lục A. ID `UAT-IMM-11-NN`.

| ID | Actor | Pre-condition | US/BR cover | Kỹ thuật | Kết quả mong đợi |
|---|---|---|---|---|---|
| UAT-IMM-11-01 | Calibration Manager | Dashboard có asset overdue + due soon | US-11-01 | Use Case happy | Dashboard hiển thị Due Soon + Overdue badge |
| UAT-IMM-11-02 | Calibration User | lab VLAS-T-028 (ISO 17025) | US-11-02, BR-11-01 | Use Case happy | tạo CAL External, gửi Lab OK, ALE `calibration_sent_to_lab` |
| UAT-IMM-11-03 | Calibration User | cert_date=2026-04-24, all Pass | BR-11-04 | BVA boundary | next_calibration_date = 2027-04-24 (cert_date + interval, không phải due_date) |
| UAT-IMM-11-04 | Calibration User → Compliance Manager | 1 measurement OOT | BR-11-02, BR-11-03 | Use Case alt | asset Out of Service + CAPA + lookback assets populated |
| UAT-IMM-11-05 | Compliance Manager → Calibration User | CAPA closed + recal | BR-11-02 | State Transition | asset Active + event `calibration_conditionally_passed` |
| UAT-IMM-11-06 | Calibration User | In-House, reference_standard_serial | US-11-02 | EP | Submit OK không cần cert; null reference_standard → block VR-11-06 |
| UAT-IMM-11-07 | Calibration Manager | submitted CAL | BR-11-05 | Error guessing | Delete/Cancel block; Amend cần reason |
| UAT-IMM-11-08 | System + Calibration Manager | schedule due ≤ 30d | scheduler | Use Case | `create_due_calibration_wos` tạo WO; chạy lại không duplicate |
| UAT-IMM-11-09 | Compliance Manager | data tháng | US-11-01 | Use Case | Compliance/OOT/CAPA closure rate tính đúng |
| UAT-IMM-11-10 | viewer.cal (System User) | bất kỳ | permission | EP permission | gọi `create_calibration` → FORBIDDEN/403 |
| UAT-IMM-11-11 | Compliance Manager | CAL Passed | audit | State Transition | `verify_audit_chain` = True; sửa IMM Audit Trail → block |

Tất cả scenario ⬜ Pending execution (UAT site chưa seed). Mỗi US có ≥ 1 scenario; có negative (06,07), permission (10), audit (11).

## V.5. Tổng hợp kết quả & Bug found

| Scenario | Status | Tester | Ngày | Ghi chú |
|---|---|---|---|---|
| UAT-IMM-11-01 … 11 | ⬜ Pending | | | seed + execution chưa thực hiện |

**Bug log**: `Issue ID · Severity (Blocker/Major/Minor/Trivial) · Mô tả · Fix status` — điền khi phát sinh.

**Acceptance**: ≥ 95% PASS, Blocker = 0, Major ≤ 2 (có workaround documented).

**Sign-off**:

| Vai trò | Người | Ngày | Chữ ký |
|---|---|---|---|
| BA Lead | | | |
| QA Lead | | | |
| Module Owner (IMM-11) | | | |
| End-user (Workshop Manager) | | | |

---

# Phần VI — Security Review (gate)

## VI.1. RBAC

**Role definitions** (`fixtures/role.json` + `role_profile.json`). Role liên quan IMM-11: AssetCore Super Admin, Calibration Manager, Calibration User, Compliance Manager, AssetCore Auditor, AssetCore System User.

**DocPerm matrix — `IMM Asset Calibration`** (nguồn thực: `imm_asset_calibration.json`):

| Role | Read | Write | Create | Submit | Cancel | Amend | Delete |
|---|---|---|---|---|---|---|---|
| AssetCore Super Admin | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Calibration Manager | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Calibration User | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| AssetCore Auditor | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| AssetCore System User | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

> Lưu ý: Calibration User KHÔNG có Submit/Cancel ở DocPerm (chỉ tạo + ghi draft); transition vào Passed/Failed do System Manager / on_submit. Workflow JSON cho Calibration User action "Đạt/Không đạt" ở state In Progress — cần khảo sát mâu thuẫn DocPerm submit=0 vs workflow transition (xem VI.9 EoP).

**DocPerm matrix — `IMM Calibration Schedule`** (nguồn: `imm_calibration_schedule.json`):

| Role | Read | Write | Create | Delete |
|---|---|---|---|---|
| AssetCore Super Admin | ✅ | ✅ | ✅ | ✅ |
| Calibration Manager | ✅ | ✅ | ✅ | ✅ |
| Calibration User | ✅ | ✅ | ✅ | ❌ |
| AssetCore Auditor | ✅ | ❌ | ❌ | ❌ |
| AssetCore System User | ✅ | ❌ | ❌ | ❌ |

**Field-level permission (permlevel)**: hiện mọi field ở permlevel 0 (kiểm tra `imm_asset_calibration.json` — không field nào đặt permlevel ≠ 0). Đề xuất nâng permlevel cho `amendment_reason` (lý do amend nhạy cảm) — *(Cần khảo sát: chưa implement permlevel)*.

**User Permission (row-level)**: hiện chưa có `permission_query_conditions` cho IMM-11 — *(Cần khảo sát)*. Calibration User thấy mọi record (DocPerm read=1, không filter).

Kỹ thuật: Decision Table — mỗi (role × action × state) là 1 row, expected Allow/Deny.

## VI.2. API security

| Mục | Trạng thái | Ghi chú |
|---|---|---|
| Whitelist hygiene | *(Cần khảo sát)* | 18 `@frappe.whitelist`; mutating (`send_to_lab`, `receive_certificate`, `cancel_calibration`) dùng `methods=["POST"]` |
| CSRF | ✅ Frappe default | `X-Frappe-CSRF-Token` |
| Input validation | *(Cần khảo sát)* | Link `asset`/`name` validate qua service trước khi dùng |
| SQL injection | *(Cần khảo sát — cần grep raw SQL)* | dùng Frappe ORM parameterized; không f-string vào raw SQL |
| Rate limit | ⬜ Roadmap | cho `submit_calibration`, `create_calibration` |

## VI.3. Audit trail integrity

- Mọi state change sinh `IMM Audit Trail` qua `_transition_asset` → lifecycle log.
- Hash chain SHA-256: `hash = SHA256(prev_hash + canonical_json(event))`.
- Verify endpoint: `verify_audit_chain(asset)` → `bool`.
- Test tamper: III.5 (b) — ⬜ Planned.
- User KHÔNG có quyền edit/delete `IMM Audit Trail` (DocPerm + on_trash guard, ISO 13485:7.5.9). `IMM Asset Calibration` submit cũng block delete (BR-11-05, controller `on_trash`).

## VI.4. Authentication & session

| Hạng mục | Config |
|---|---|
| Login | Frappe default (username + password) |
| Session timeout | 8h (`frappe.conf.session_expiry`) |
| Lockout | Frappe default: 3 fail → lock 15 phút |
| Password policy | min 8 ký tự, 1 hoa, 1 số |
| API key | per-user, rotate 90 ngày, không commit git |
| 2FA | Roadmap Phase 2 |

## VI.5. Data sensitivity

| Loại | Trường | Sensitivity | Bảo vệ |
|---|---|---|---|
| Calibration certificate | `certificate_file` | Internal | Role permission |
| Lab accreditation | `lab_accreditation_number`, `lab_supplier` | Internal | Role permission |
| Measurement data | `measurements` child table | Internal | Role permission |
| Amendment reason | `amendment_reason` | Confidential | đề xuất permlevel 1 *(chưa implement)* |
| Dữ liệu bệnh nhân | Không lưu | N/A | AssetCore KHÔNG lưu patient data |

## VI.6. Vendor isolation

Lab hiệu chuẩn (`AC Supplier`, vendor_type = Calibration Lab) hiện KHÔNG có role user trên `IMM Asset Calibration` (chỉ là Link target). Nếu mở rộng vendor portal:
- chỉ thấy CAL của lab mình (qua `permission_query_conditions` — *(Cần khảo sát, chưa có)*).
- KHÔNG thấy: chi phí, measurement asset khác, CAPA content, audit trail. KHÔNG export bulk.

Trace: test ở III.6 (`test_create_low_role_forbidden`).

## VI.7. Secrets management

- Cấm commit `.env` / credential. `site_config.json` không lên git.
- External token lưu `frappe.conf`. Backup encrypt at-rest off-site.
- Secret scan CI: `detect-secrets` pre-commit.

## VI.8. Logging & monitoring

| Sự kiện | Log level | Where | Alert? |
|---|---|---|---|
| Calibration Fail (asset OOS) | WARNING | `IMM Audit Trail` + email | ✅ Compliance Manager |
| CAL overdue > 0 ngày | WARNING | Scheduler log (`check_calibration_expiry`) | ✅ Calibration Manager |
| Audit chain tamper | ERROR | `frappe.log_error` | ✅ System Admin |
| Submit fail (validation) | INFO | Frappe access log | ❌ |

PII / token KHÔNG vào log.

## VI.9. Threat model (STRIDE-lite)

| Threat | Vector | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| **S**poofing | Giả mạo KTV upload cert giả | Low | High | cert file + accreditation number verify (VR-11-04); audit trail actor |
| **T**ampering | Sửa `certificate_file`/measurement sau submit | Low | Critical | Submittable immutable; on_cancel/on_trash block (BR-11-05) |
| **R**epudiation | KTV phủ nhận đã submit Fail | Low | High | `IMM Audit Trail` + hash chain + actor |
| **I**nfo disclosure | Role thấp xem CAL người khác | Medium | Medium | DocPerm read; ⚠ chưa có row-level filter — *(Cần khảo sát)* |
| **D**enial of service | Lookback với 10k+ asset cùng model | Low | Medium | paginate lookback; index `device_model + lifecycle_status` |
| **E**levation of privilege | Calibration User submit/approve | Low | High | DocPerm submit=0 cho Calibration User; transition Phê duyệt giới hạn System Manager — ⚠ kiểm tra mâu thuẫn workflow (VI.1) |

## VI.10. Penetration test

⬜ Planned — trước release đầu tiên: Burp/ZAP scan, sqlmap (an toàn), CSRF test (curl không token), role escalation (gọi `create_calibration`/`submit_calibration` role AssetCore System User → 403). Report lưu `docs/security/pentest_imm11_v1.md`.

## VI.11. Sign-off

| Vai trò | Người | Ngày | Quyết định |
|---|---|---|---|
| QA Lead | | | ☐ Pass / ☐ Pass with conditions / ☐ Fail |
| Security Officer | | | ☐ Pass / ☐ Pass with conditions / ☐ Fail |
| Module Owner | | | ☐ Pass / ☐ Pass with conditions / ☐ Fail |

---

# Phần VII — Code Quality

## VII.1. Tool matrix

| Tool | Mục tiêu | Target | Cadence |
|---|---|---|---|
| **SonarQube** (BE Python) | bug 0 Critical, code smell ≤ 5, duplication ≤ 3%, coverage ≥ 70%, security hotspot review 100% | Quality Gate pass | Mỗi PR (CI gate) |
| **Lighthouse** (FE — CalibrationDashboard) | Performance ≥ 90, Accessibility ≥ 95, Best Practices ≥ 90, SEO ≥ 80 | ≥ target | Mỗi release + monthly |
| **ESLint + vue-tsc** (FE) | 0 error, 0 warning trên prod build | pass | Mỗi PR FE (CI gate) |
| **ruff / black** (BE) | 0 error, format chuẩn PEP8 | pass | Mỗi PR (CI gate) |
| **Bundle size** (FE chunk imm11) | main ≤ 250KB gzip, async ≤ 80KB gzip | ≤ budget | Mỗi PR FE (CI report) |

## VII.2. Cadence

- SonarQube: mỗi PR (CI gate, fail nếu Quality Gate fail).
- Lighthouse: mỗi release lớn + monthly audit.
- ESLint / ruff: mỗi PR (CI gate).
- Bundle size: mỗi PR FE (CI report, fail nếu vượt budget).

Gắn screenshot SonarQube + Lighthouse vào file 09 §Release Notes khi báo cáo final.

---

# Phụ lục A — Template per UAT scenario

```markdown
### UAT-IMM-11-<NN> — <Tên>

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
### TC-IMM-11-<LAYER>-<NN> — <Tên>

**Component (I.1)**: <…>
**Liên kết**: US-<NN> | BR-<NN> | ACT-<NN>
**Kỹ thuật (II.1/II.2)**: BVA boundary `certificate_date + interval_days`
**Priority (I.3)**: Critical / High / Medium / Low
**Test type**: Unit / Integration / API / E2E
**Pre-condition**: <fixture / state setup>

**Input**:
- <field>: <value>

**Steps**:
1. <…>
2. <…>

**Expected**:
- ServiceError(code=VALIDATION, message contains "VR-11-04")
- doc.workflow_state unchanged

**Post-condition**: <DB rollback / fixture cleanup>
```

# Phụ lục C — Workflow State Transition Test template

```markdown
### TC-IMM-11-WF-<NN> — <action>: <from> → <to>

**Workflow JSON**: `assetcore/assetcore/workflow/imm_11_calibration_workflow.json`
**Role required**: <…>
**Pre-condition**: doc.workflow_state = <from>, gate đã pass
**Action**: apply_workflow(doc, "<action>")
**Expected (happy)**: doc.workflow_state = <to>, docstatus = <…>, audit entry created
**Expected (negative role)**: PermissionError / FORBIDDEN
**Expected (gate fail)**: ServiceError(code=BUSINESS_RULE, message contains "<rule>")
```

---

# DoD — File 07 hoàn chỉnh

## I. Test Analysis
- [x] I.1 Component Inventory liệt kê đủ artefact (22 component vs 04/05/06)
- [x] I.2 mỗi US / BR / Activity có ≥ 1 dòng map (US-11-03+ đánh dấu Cần khảo sát theo 02)
- [x] I.3 Risk priority gán cho mọi component
- [x] I.4 Scope ghi rõ out-of-scope kèm lý do

## II. Test Design Techniques
- [x] II.1 ≥ 4 black-box techniques (EP + BVA + Decision Table + State Transition + Use Case + Error Guessing)
- [x] II.2 white-box criteria (statement + branch + MC/DC + path)
- [x] II.3 mapping component → kỹ thuật đầy đủ

## III. Test Plan
- [x] Test class structure cho mọi service public function (I.1)
- [ ] ≥ 1 happy + 1 negative test mỗi function — chỉ 3 fn có test live; còn lại ⬜ Planned
- [ ] Workflow transitions cover 100% (13 transition liệt kê đủ; test ⬜ Planned)
- [ ] Audit chain test (intact + tampered) — ⬜ Planned
- [ ] API test ≥ 60% coverage + permission matrix — ⬜ Planned
- [x] Performance target xác định (target only, chưa baseline)
- [x] CI command chạy clean (`bench run-tests --module assetcore.tests.test_imm11`)
- [ ] SonarQube Quality Gate pass + Lighthouse ≥ target — chưa chạy

## IV. Traceability
- [x] IV.1 US → Test: mọi US (01/02) có ≥ 1 Test ID
- [x] IV.2 BR → Test: BR-11-01..05,07 có happy + negative (BR-11-06 Cần khảo sát)
- [ ] IV.3 Component → Test: Critical đạt coverage target — coverage chưa đo (Cần khảo sát)

## V. UAT
- [x] Mỗi US có ≥ 1 UAT scenario (11 scenario)
- [x] ≥ 1 negative + permission + audit verify scenario (06/07/10/11)
- [ ] Test data seed script chạy được (`uat_imm11.py` ⬜ Planned)
- [ ] Tester accounts đã tạo ở UAT site — chưa tạo
- [x] Sign-off section sẵn sàng

## VI. Security
- [x] DocPerm matrix đầy đủ (Decision Table) — từ JSON thực
- [ ] Mọi field nhạy cảm có permlevel ≠ 0 — hiện tất cả permlevel 0 (đề xuất nâng amendment_reason)
- [ ] SQL injection + CSRF test pass — CSRF default OK; SQLi Cần khảo sát
- [ ] Audit chain test pass (intact + tampered) — ⬜ Planned
- [ ] Vendor isolation test pass — chưa có row-level filter (Cần khảo sát)
- [x] Threat model đủ 6 STRIDE với mitigation
- [ ] Sign-off đầy đủ trước go-live

## VII. Code Quality
- [ ] SonarQube Quality Gate pass — chưa chạy
- [ ] Lighthouse ≥ target — chưa chạy
- [ ] Bundle size ≤ budget — chưa đo
- [ ] Screenshot báo cáo gắn vào file 09 — chưa có

## VIII. CR-74 — Read-gate CHI TIẾT (getCalibration) · bộ TC bắt buộc (2026-07-25)

> Spec: [`05_API_Specification.md` §12](./05_API_Specification.md) · SSoT: [ADR-IMM00-LIST-SCOPE §9](../imm-00/ADR-IMM00-LIST-SCOPE.md).
> **Suite:** `bench --site miyano run-tests --app assetcore --module assetcore.tests.test_imm11` (+ `test_rowscope_docperm_gate` · `test_rowscope_invariant` · `test_rowscope_scope_guard`). **DoD = suite XANH, KHÔNG curl** (`.py` prod dirty dưới gunicorn `--preload` ⇒ BLOCKED-RELOAD).

### VIII.1 Fixture tối thiểu (dựng 1 lần, dùng chung 6 TC)

| Ký hiệu | Là gì | Ràng buộc |
|---|---|---|
| `USER_NOPERM` | user **đăng nhập được** nhưng **0 DocPerm read** trên `Calibration Record` | vd persona `PM User` / `Repair User` (0 DocPerm read trên `Calibration Record`). **KHÔNG** dùng Guest (Guest → dispatcher-403/401, sai loại lỗi) |
| `USER_OWNER` | persona `Calibration User` — `technician` == chính mình | phải có DocPerm read |
| `USER_OTHER` | persona `Calibration User` khác — **không** được giao phiếu đang test | phải có DocPerm read (để phân biệt trục ROW với trục ROLE) |
| `USER_SENIOR` | `Calibration Manager` hoặc `AssetCore Auditor` | chứng minh 0 regress |
| `REC_OWNED` | 1 bản ghi `Calibration Record` có `technician` = `USER_OWNER` | |
| `REC_FOREIGN` | 1 bản ghi `Calibration Record` có `technician` = `USER_OWNER`, dùng khi đăng nhập `USER_OTHER` | |
| `NAME_GHOST` | chuỗi PK **không tồn tại** (vd `"CAL-9999-99999"`) | dùng cho cặp TC existence-oracle |

> 🔴 **BẮT BUỘC `frappe.set_user(...)` cho MỌI TC** + `frappe.set_user("Administrator")` trong `tearDown`. `frappe/permissions.py:107-109` trả `True` ngay cho Administrator ⇒ chạy bằng Administrator = **xanh giả** (đúng bài học INV-ROWSCOPE-4/6).

### VIII.2 Bộ TC

| TC | User | Input | Kỳ vọng (assert) | INV |
|---|---|---|---|---|
| `TC-CAL-DETAILGATE-01` | `USER_NOPERM` | `REC_OWNED` | `env["success"] is False` · `env["code"] == "FORBIDDEN"` · `env["http_status"] == 403` · **KHÔNG raise** · `set(env) & {"asset", "measurements", "overall_result", "certificate_no"} == set()` | INV-DETAIL-1 |
| `TC-CAL-DETAILGATE-02` | `USER_OTHER` | `REC_FOREIGN` | **`success is True` (200)** — D10: `Calibration Record` CHƯA có hook row-scope ⇒ TC này **ghim hành vi hiện tại** (0 regress). ⚠️ KHÔNG viết kỳ vọng 403 ở đây; muốn siết phải ratify hook riêng (ADR §9.6 Ask-first) | INV-DETAIL-2 |
| `TC-CAL-DETAILGATE-03` | `USER_SENIOR` | `REC_OWNED` | `env["success"] is True` · payload **byte-identical** snapshot baseline (so khoá + giá trị) | INV-DETAIL-4 |
| `TC-CAL-DETAILGATE-04` | `USER_NOPERM` | `NAME_GHOST` | envelope **giống hệt** `TC-CAL-DETAILGATE-01` (cùng `code` + `http_status`) ⇒ 0 existence-oracle | INV-DETAIL-5 |
| `TC-CAL-DETAILGATE-05` | `USER_OWNER` | `NAME_GHOST` | `code == "NOT_FOUND"` · `http_status == 404` — **GIỮ NGUYÊN** | INV-DETAIL-6 |
| `TC-CAL-DETAILGATE-06` | `Vendor Engineer` ngoài scope | `REC_OWNED` | `code == "FORBIDDEN"` · **KHÔNG** 500 · **KHÔNG** traceback ⇒ chứng minh lớp `assert_vendor_can_access` vẫn sống | INV-DETAIL-7 |

### VIII.3 Chống vacuous (BẮT BUỘC ghi bằng chứng vào báo cáo vòng)

1. **Mutation gate:** gỡ `assert_doctype_read_permission` khỏi `services/imm11.py::get_calibration` ⇒ `TC-CAL-DETAILGATE-01` và `TC-CAL-DETAILGATE-04` PHẢI **ĐỎ**. Hoàn nguyên ⇒ xanh.
2. **Mutation guard tĩnh:** cùng thao tác trên ⇒ `test_rowscope_scope_guard::TestRowScopeStaticGuard` **G5** PHẢI **ĐỎ**.
3. **Anti-false-green:** TC-01 phải assert **cả 3** (`success`/`code`/`http_status`) — chỉ assert `success is False` sẽ **không** phân biệt 403 với 404/422.
4. **Anti-leak:** TC-01/02 assert **tập khoá** của envelope, KHÔNG chỉ `"asset_ref" not in env` (khoá lồng trong `data` vẫn rò nếu quên).


---

## IX. AC-CR-86 — Dời lịch hiệu chuẩn (`reschedule_calibration`) · bộ TC bắt buộc (2026-07-27)

> Spec: `02 §BR-11-19` + `§BR-11-20` + US-11-04 (AC-11-49…60). Write-path: `04 §4.1.12` + `§4.1.13`. API: `05 §0.1.11` + `§2 #13`.
> **DoD chấm bằng `bench --site miyano run-tests --module assetcore.tests.test_imm11` (module-isolated, `timeout` tool ≥ 600000ms) — KHÔNG curl** (LL-DEPLOY-07/08: dưới gunicorn `--preload`, `.py` mới cần USER reload; 417/traceback từ curl = worker cũ, KHÔNG phải bug).

### IX.1 Fixture tối thiểu (dựng 1 lần, dùng chung)

| Fixture | Nội dung |
|---|---|
| `ASSET_RS` | 1 `AC Asset` Active + `AC Asset.next_calibration_date = D1` (ghi nhận để assert AC-11-57) |
| `SCHED_RS` | 1 `IMM Calibration Schedule` `is_active=1`, `next_due_date = D2` |
| `CAL_SCHEDULED` | `IMM Asset Calibration` `status='Scheduled'`, `docstatus=0`, `scheduled_date=X` |
| `CAL_INPROGRESS` | như trên, `status='In Progress'` |
| `CAL_SENTLAB` / `CAL_PASSED` / `CAL_CANCELLED` | 3 phiếu ở trạng thái NGOÀI `RESCHEDULE_CAL_STATES` |
| `CAL_SUBMITTED` | phiếu `docstatus=1` |
| `USER_CAL` | user có `calibration.write` · `USER_BASE` = user chỉ có base role `AssetCore System User` |

> 🔴 `frappe.set_user(...)` cho MỌI TC + `frappe.set_user("Administrator")` trong `tearDown`. Teardown purge đủ phiếu/asset/schedule đã tạo (LL-TEST: fixture mồ côi ⇒ suite ĐỎ GIẢ ở vòng sau).

### IX.2 Bộ TC backend (`tests/test_imm11.py` — class `TestCalibrationReschedule`)

| TC | Input | Kỳ vọng (assert) | AC / INV |
|---|---|---|---|
| `TC-CAL-RS-01` | `CAL_SCHEDULED`, `new_date=X+7`, `reason` hợp lệ | đọc lại DB: `scheduled_date == X+7` ∧ `status == 'Scheduled'` ∧ `docstatus == 0`; `data == {name, old_date: X, new_date: X+7, status: 'Scheduled'}` (so **4 khoá**, không chỉ 1) | AC-11-49 · INV-CALRS-1 |
| `TC-CAL-RS-02` | `CAL_INPROGRESS` dời hợp lệ | `scheduled_date` đổi ∧ `status == 'In Progress'` | AC-11-50 · INV-CALRS-1 |
| `TC-CAL-RS-03` | dời **2 lần** trên cùng phiếu | `IMM Audit Trail` (`ref_doctype='IMM Asset Calibration'`, `ref_name`, `event_type='Calibration'`) tăng **ĐÚNG 2**; mỗi `change_summary` chứa ngày cũ **và** ngày mới **và** lý do; `amendment_reason` có **2 dòng** `[Dời lịch …]`; số phiếu `status='Cancelled'` sinh thêm == **0** | AC-11-51 · INV-CALRS-2 |
| `TC-CAL-RS-04` | `CAL_SENTLAB` / `CAL_PASSED` / `CAL_CANCELLED` (3 sub-case) | `code == 'BAD_STATE'` ∧ `http_status == 409` ∧ **đọc lại DB `scheduled_date` == giá trị cũ** | AC-11-52 · INV-CALRS-4 |
| `TC-CAL-RS-05` | `CAL_SUBMITTED` (`docstatus=1`) | như TC-04 (cùng mã) | AC-11-52 |
| `TC-CAL-RS-06` | `reason=''` và `reason='  ab '` | `http_status == 422` ∧ `'reason' in fields` ∧ `'new_date' not in fields`; `scheduled_date` KHÔNG đổi | AC-11-53 |
| `TC-CAL-RS-07` | `new_date=''` và `new_date='32/13/2026'` | `422` ∧ `'new_date' in fields`; `scheduled_date` KHÔNG đổi | AC-11-54 |
| `TC-CAL-RS-08` | `new_date = today - 1` | `422` ∧ `'new_date' in fields`; **và** `new_date == today` ⇒ **THÀNH CÔNG** (biên inclusive) | AC-11-55 |
| `TC-CAL-RS-09` | `USER_BASE` gọi **thẳng service** | `ServiceError` `code=='FORBIDDEN'` ∧ `http_status==403`; `scheduled_date` KHÔNG đổi. `USER_CAL`/Super Admin ⇒ pass | AC-11-56 |
| `TC-CAL-RS-10` | sau khi dời lịch thành công | `AC Asset.next_calibration_date == D1` ∧ `IMM Calibration Schedule.next_due_date == D2` (đọc lại DB); `get_due_calibrations` vẫn liệt kê asset y như trước | AC-11-57 · INV-CALRS-6 |
| `TC-CAL-RS-11` | `update_calibration(name, {'scheduled_date': X+7})` **và** `{'technician_notes':'x','scheduled_date':X+7}` | `422` ∧ `'scheduled_date' in fields`; `scheduled_date` **và** `technician_notes` đều KHÔNG đổi (0 ghi từng phần) | AC-11-58 |
| `TC-CAL-RS-12` | `update_calibration` với patch chỉ gồm khoá ∈ `_UPDATE_ALLOWED` (`technician_notes`, `status`, `certificate_number`) **và** 1 khoá lạ khác (vd `foo`) | success; ghi đủ khoá hợp lệ; khoá lạ bị bỏ qua **im lặng** như cũ; return-shape 4 khoá `{name,status,measurement_count,overall_result}` KHÔNG đổi | AC-11-59 |
| `TC-CAL-RS-13` | `get_calibration` trên **mỗi** phiếu fixture × (USER_CAL, USER_BASE) | `can_reschedule` TRUE ⟺ `reschedule_calibration` KHÔNG trả `BAD_STATE`/`FORBIDDEN` (parity **2 chiều**, lặp qua ma trận) | AC-11-60 · INV-CALRS-5 |
| `TC-CAL-RS-14` | phiếu ∄ | `code=='NOT_FOUND'` ∧ `http_status==404` (KHÔNG bị BAD_STATE che) | INV-CALRS-3 |
| `TC-CAL-RS-15` | payload sai **ĐÔI** (`CAL_PASSED` + `reason=''`) | nhận **`BAD_STATE`** (trạng thái xét TRƯỚC ô nhập) — khoá thứ tự hợp đồng | INV-CALRS-3 |

### IX.3 Chống vacuous (BẮT BUỘC ghi bằng chứng vào báo cáo vòng)

1. **Mutation — guard trạng thái:** đổi `RESCHEDULE_CAL_STATES` thành `{Scheduled, In Progress, Passed}` ⇒ `TC-CAL-RS-04` **PHẢI ĐỎ**. Nếu vẫn xanh ⇒ TC đang assert exception chung chung, không assert giá trị.
2. **Mutation — audit:** comment dòng `log_audit_event` ⇒ `TC-CAL-RS-03` **PHẢI ĐỎ**.
3. **Mutation — append:** đổi `amendment_reason` từ append sang ghi đè ⇒ `TC-CAL-RS-03` **PHẢI ĐỎ** (đếm 2 dòng).
4. **Mutation — flip trạng thái:** thêm `"status": CalibrationResult.SCHEDULED` vào `update_fields` ⇒ `TC-CAL-RS-02` **PHẢI ĐỎ**.
5. **Mutation — cap:** đổi `_require_cal_reschedule_cap` thành `pass` ⇒ `TC-CAL-RS-09` **PHẢI ĐỎ**.
6. **Mutation — nuốt im lặng:** gỡ guard `scheduled_date` khỏi `update_calibration` ⇒ `TC-CAL-RS-11` **PHẢI ĐỎ**.
7. **Anti-false-green:** mọi TC từ chối phải assert **cả 3** (`success is False` + `code` + `http_status`) **và** đọc lại `scheduled_date` từ DB — chỉ `assertRaises` là **KHÔNG đủ** (không chứng minh 0-mutate).
8. **Đếm audit theo DELTA**, không theo tổng tuyệt đối (site có dữ liệu sẵn — blocker STATE #13).

### IX.4 Guard hợp đồng (doc-layer — ĐÃ ĐÓNG ở Bước-2)

- `assetcore/tests/test_mobile_oas.py::TestMobileRescheduleCalibrationContract` — 9 TC `cr86_a..i` (path/opId/POST-only · body CLOSED 3 khoá + `minLength:5` + `format:date` · 200-oneOf 2 nhánh + `data` 4 khoá · slot `{200,401,403}` + đủ 6 `message_code` + 2 khoá `fields` · cite-drift AST · `can_reschedule` trên `CalibrationDetail` · KHÔNG reuse `ReschedulePm*` · PENDING-BE parity · meta self-count).
- `assetcore/tests/test_mobile_docset.py` — 3 counter đồng bộ theo **DELTA +9**.
- ✅ **Bước-4 BE ĐÃ LÀM ĐỦ 3 việc trên guard (2026-07-28)** — handler LIVE `api/imm11.py:131` (POST-only) → `services/imm11.py:1217`:
  1. **LẬT** `cr86_h` → `test_mob_oas_cr86_h_message_code_registry_parity`: parity **3 tầng** hợp đồng ⇄ registry ⇄ @source — 6/6 mã ∈ `MESSAGES` LIVE, `http_status` khớp (`IMM11-CAL-NOT-FOUND` 404 · `IMM11-RESCHEDULE-BAD-STATE` 409 · 4 mã field-level 422), **và** 5 mã mới phải có call-site `MSG.<CODE>` THẬT trong `services/imm11.py` (mã có registry mà 0 nơi ném = hợp đồng khai một lỗi không bao giờ tới).
  2. **REFRESH** cite trong `description` (comment YAML KHÔNG được — guard chỉ soi spec đã parse): `_UPDATE_ALLOWED` `1155→1298` (3 chỗ), `get_calibration` `1079-1111→1082-1120`, và bồi cite numeric `@api/imm11.py:131-154` / `@services/imm11.py:1217-1295 reschedule_calibration` + `1171-1174 RESCHEDULE_CAL_STATES` + `1204-1214 _can_reschedule_cal` + `1190-1201 _require_cal_reschedule_cap`.
  3. **CHUYỂN** path `_PENDING_BE_PATHS` (nay **∅**, giữ cơ chế cho CR doc-first sau) → `_MVP_BUSINESS_PATHS` + `_MVP_ACTION_ENVELOPE` (c5 **98→99** ×8 chỗ, `_PARITY_BUSINESS_PATHS` **98→99** ×5 chỗ) và bật `_assert_post_only_at_source` trong `cr86_a`. Kết quả: `test_mobile_oas` **1024/1024 XANH** (counter GIỮ 1024 — lật ≠ thêm TC), `test_mobile_docset` 9/9 XANH.
