# 07 — Kiểm thử & An ninh (Testing & QA & Security)

| Mục | Giá trị |
|---|---|
| Module | IMM-09 — Sửa chữa (Corrective Maintenance) |
| Phạm vi | Per-module |
| Owner | QA Lead + Security Officer |
| Liên kết | 02 Analysis (US, BR, Activity, BPMN) · 03 Diagrams · 04 Backend · 05 API · 06 Frontend |

> **Mục đích**: Suy ra test case **có hệ thống** từ phân tích (file 02) bằng kỹ thuật black-box + white-box, không liệt kê tự phát. Bao gồm: phân tích đối tượng test → chọn kỹ thuật → viết test → traceability → UAT → security → code quality. Phần VI (Security) là gate go-live.

---

# Phần I — Test Analysis (Phân tích đối tượng test)

> Mục tiêu Phần I: trả lời 4 câu hỏi trước khi viết test case: **(1) test cái gì** (component inventory) **(2) suy ra từ đâu** (US/BR/Activity) **(3) ưu tiên cái nào** (risk) **(4) loại trừ cái nào** (out-of-scope).

## I.1. Component Inventory — Liệt kê phần mềm cần test

Toàn bộ artefact test được của IMM-09 (nguồn: 04 Backend §DocType + §Service · 05 API §Catalog · 06 Frontend §Components).

| # | Component | Loại | File / Tên | Test layer áp dụng |
|---|---|---|---|---|
| 1 | `Asset Repair` | DocType (master) | `doctype/asset_repair/asset_repair.json` | Integration (lifecycle) |
| 2 | `Repair Checklist` | DocType (child) | `doctype/repair_checklist/repair_checklist.json` | Integration |
| 3 | `Spare Parts Used` | DocType (child) | `doctype/spare_parts_used/spare_parts_used.json` | Integration |
| 4 | `Firmware Change Request` | DocType (link target) | `doctype/firmware_change_request/` | Integration (gate BR-09-03) |
| 5 | `IMM-09 Repair Workflow` | Workflow | `workflow/imm_09_repair_workflow.json` (9 state, 15 transition) | Integration (state transition) |
| 6 | `get_sla_target` | Service (pure) | `services/imm09.py::get_sla_target` | Unit (Decision Table risk×priority) |
| 7 | `validate_repair_source` | Validator | `services/imm09.py::validate_repair_source` | Unit (EP, BR-09-01 relaxed) |
| 8 | `validate_asset_not_under_repair` | Validator | `services/imm09.py::validate_asset_not_under_repair` | Unit (EP, BR-09-05) |
| 9 | `check_repeat_failure` | Service | `services/imm09.py::check_repeat_failure` | Unit (BVA window 30d, BR-09-06) |
| 10 | `validate_spare_parts_stock_entries` | Validator | `services/imm09.py::validate_spare_parts_stock_entries` | Unit (EP, BR-09-02) |
| 11 | `validate_firmware_change_request` | Validator | `services/imm09.py::validate_firmware_change_request` | Unit (Decision Table, BR-09-03) |
| 12 | `validate_repair_checklist_complete` | Validator | `services/imm09.py::validate_repair_checklist_complete` | Unit (EP, BR-09-04) |
| 13 | `complete_repair` | Service | `services/imm09.py::complete_repair` | Unit + Integration (MTTR, SLA, ALE) |
| 14 | `set_asset_under_repair` | Service | `services/imm09.py::set_asset_under_repair` | Integration (Asset status) |
| 15 | `_mark_cannot_repair` | Service | `services/imm09.py::_mark_cannot_repair` | Integration (Asset OOS) |
| 16 | `create_work_order` | Service | `services/imm09.py::create_work_order` | Unit + API |
| 17 | `assign_technician` / `submit_diagnosis` / `start_repair` / `request_spare_parts` / `close_work_order` / `confirm_inspection` | Service (transition fns) | `services/imm09.py` | Unit + Integration (workflow) |
| 18 | `check_repair_sla_breach` | Scheduler job | `services/imm09.py::check_repair_sla_breach` | Unit + Cron simulation (BR-09-07) |
| 19 | `check_repair_overdue` | Scheduler job | `services/imm09.py::check_repair_overdue` | Cron simulation |
| 20 | `update_asset_mttr_avg` | Scheduler job | `services/imm09.py::update_asset_mttr_avg` | Cron simulation |
| 21 | `get_kpis` / `get_mttr_report` / `get_asset_history` | Service (read) | `services/imm09.py` | Unit + API |
| 22 | API catalog (14 endpoint) | API endpoint | `api/imm09.py` | API integration |
| 23 | Lifecycle event `_log_lifecycle_event` | Lifecycle event | `services/imm09.py::_log_lifecycle_event` → `IMM Audit Trail` | Integration (audit chain) |
| 24 | FE views CM (8 view) | FE view | `frontend/src/views/cm/*.vue` | E2E (Playwright) |
| 25 | Pinia store IMM-09 | Pinia store | `frontend/src/stores/imm09.ts` | Unit (vitest) — *(Cần khảo sát)* |

## I.2. Trace nguồn test — User Stories, Activity Flows, Business Rules

Dẫn từ artefact phân tích (02_Analysis_Design.md) sang test layer. Mỗi US/BR/Activity có ≥ 1 test ở Phần III và xuất hiện trong matrix Phần IV.

### I.2.a. Từ User Story
→ 02 §Functional Specs

| US ID | Tiêu đề ngắn | Acceptance Criteria # | Test layer dự kiến |
|---|---|---|---|
| US-09-01 | Tạo CM WO (có/không nguồn) | AC1, AC2 | Unit + API + UAT |
| US-09-02 | Phân công KTV | AC1 | API + UAT (workflow) |
| US-09-03 | Submit Diagnosis (ghi chẩn đoán) | AC1 | API + UAT |
| US-09-04 | Yêu cầu vật tư | AC1 | API + UAT |
| US-09-05 | Xác nhận vật tư (stock entry) | AC1 | Unit + UAT (BR-09-02) |
| US-09-07 | Checklist 100% Pass trước Complete | AC1, AC2 | Unit + UAT (BR-09-04) |
| US-09-08 | Đóng WO / nghiệm thu | AC1 | Integration + UAT |
| US-09-09 | Cannot Repair → EOL trigger | AC1 | Integration + UAT |
| US-09-10 | MTTR Dashboard / KPI | AC1 | API + UAT |
| US-09-11 | MTTR report drill-down | AC1 | API + UAT |

### I.2.b. Từ Business Rule
→ 02 §Business Rules

| BR ID | Phát biểu | Component liên quan (I.1) | Kỹ thuật test phù hợp |
|---|---|---|---|
| BR-09-01 | WO standalone hợp lệ; chỉ bắt buộc nguồn khi `source_type` = Incident/PM (relaxed Wave 2) | `validate_repair_source` (#7) | EP (3 partition source_type) |
| BR-09-02 | Spare parts row phải có `stock_entry_ref` hợp lệ | `validate_spare_parts_stock_entries` (#10) | EP + Error guessing |
| BR-09-03 | `firmware_updated=1` → FCR Approved linked | `validate_firmware_change_request` (#11) | Decision Table |
| BR-09-04 | Repair Checklist đầy đủ + 100% Pass trước Submit | `validate_repair_checklist_complete` (#12) | EP (Pass/Fail/N-A/empty) |
| BR-09-05 | Asset Under Repair khi open; Active khi Completed; OOS khi Cannot Repair; chặn WO trùng | `set_asset_under_repair` (#14), `validate_asset_not_under_repair` (#8), `complete_repair` (#13) | State Transition + EP |
| BR-09-06 | WO trong 30 ngày → `is_repeat_failure=1` | `check_repeat_failure` (#9) | BVA (biên cửa sổ 30 ngày) |
| BR-09-07 | `elapsed/MTTR >= SLA target → sla_breached=1` (biên: BẰNG target ⇒ breach). 1 SoT `is_sla_breached(elapsed, target)` dùng chung; cờ monotonic — completion không reset 1→0 | `is_sla_breached` (SoT), `complete_repair` (#13), `check_repair_sla_breach` (#18) | BVA (biên SLA: <, ==, >) + Decision Table |

### I.2.c. Từ Activity Flow / BPMN
→ 02 §Activity Diagram per UC

| Activity / UC | Use Case | Branch chính | Branch ngoại lệ |
|---|---|---|---|
| UC-01 | Tạo CM WO | Tạo WO standalone/từ IR/PM | Asset không tồn tại, asset đang Under Repair (BR-09-05) |
| UC-02 | Phân công KTV | Open → Assigned | Wrong role |
| UC-03 | Submit Diagnosis | Diagnosing | needs_parts=1 → Pending Parts |
| UC-04 | Request Spare Parts | Gắn stock_entry_ref | Thiếu stock_entry_ref (BR-09-02) |
| UC-06 | Close WO | Checklist 100% Pass → Pending Inspection → Completed | Checklist Fail (BR-09-04), thiếu FCR (BR-09-03) |
| UC-07 | Cannot Repair | Any → Cannot Repair → Asset OOS | Thiếu lý do |
| UC-09 | MTTR Dashboard | Hiển thị KPI | High MTTR alert |

## I.3. Risk-based Priority

| Component (I.1) | Likelihood (1-5) | Impact (1-5) | Risk = L×I | Priority |
|---|---|---|---|---|
| Workflow transitions (#5) | 4 | 5 | 20 | **Critical** |
| `complete_repair` MTTR/SLA/ALE (#13) | 4 | 5 | 20 | **Critical** |
| Audit chain `_log_lifecycle_event` (#23) | 3 | 5 | 15 | **Critical** |
| `validate_firmware_change_request` (#11) | 3 | 4 | 12 | **High** |
| `validate_repair_checklist_complete` (#12) | 3 | 4 | 12 | **High** |
| `validate_spare_parts_stock_entries` (#10) | 3 | 4 | 12 | **High** |
| `validate_asset_not_under_repair` (#8) | 3 | 4 | 12 | **High** |
| `get_sla_target` (#6) | 4 | 3 | 12 | **High** |
| `check_repair_sla_breach` scheduler (#18) | 3 | 3 | 9 | Medium |
| `check_repeat_failure` (#9) | 2 | 3 | 6 | Medium |
| `validate_repair_source` (#7) | 2 | 3 | 6 | Medium |
| API read endpoints / KPI (#21, #22) | 2 | 2 | 4 | Low |
| FE CM views (#24) | 2 | 2 | 4 | Low |

**Quy ước priority**:
- **Critical** (R ≥ 15): test trước, fail = block release
- **High** (10 ≤ R < 15): bắt buộc trước go-live
- **Medium** (5 ≤ R < 10): trong sprint khi có thời gian
- **Low** (R < 5): chỉ test khi báo cáo bug

## I.4. Scope

- **In-scope**:
  - Vòng đời `Asset Repair`: tạo WO (standalone/IR/PM) → assign → diagnose → parts → repair → inspection → complete/cannot-repair.
  - 7 Business Rule BR-09-01..07 (gate validators + scheduler SLA/repeat-failure).
  - 15 workflow transition + audit chain integrity + RBAC row-level (`assigned_to` scope).
  - 14 API endpoint (envelope + permission + pagination).
- **Out-of-scope**:
  - Performance/load test → giao Phần III.8 (chỉ định target, không chạy trong sprint hiện tại).
  - Penetration test → Phần VI.10 (trước go-live đầu tiên).
  - Cross-module với IMM-12 (CAPA từ repeat failure) → chỉ smoke link, không full integration test.
  - FCR approval flow nội bộ (thuộc module Firmware Change Request) → chỉ test gate consume FCR Approved.
- **Assumptions**: master data (AC Asset, AC Spare Part, Vendor, Department) đã seed qua fixtures; tester accounts đủ role đã tạo trên site UAT; browser Chrome/Edge ≥ 120.

---

# Phần II — Test Design Techniques (Kỹ thuật thiết kế test case)

> Mỗi test phải truy được về 1 kỹ thuật ở dưới — không "vẽ test cho có".

## II.1. Black-box techniques

| Kỹ thuật | Khi nào dùng | Áp dụng vào IMM-09 | Số test sinh ra (rule of thumb) |
|---|---|---|---|
| **Equivalence Partitioning (EP)** | Input có miền giá trị chia nhóm | `repair_type` {Corrective, Breakdown, Warranty Repair}, `priority` {Normal, Urgent, Emergency}, `risk_class` {I, II, III}, `source_type` {standalone, Incident, PM}, checklist `result` {Pass, Fail, N/A} | 1 test/partition |
| **Boundary Value Analysis (BVA)** | Numeric / date / window có biên | `check_repeat_failure` cửa sổ 30 ngày (29d/30d/31d), `sla_target_hours` vs `mttr_hours` biên SLA breach, `qty` spare part | 2-3 test/biên |
| **Decision Table** | Multi-condition gate | `get_sla_target` (risk_class × priority = 9 combo + fallback), `validate_firmware_change_request` (firmware_updated × FCR present × FCR status) | 2^N rút gọn theo equivalence |
| **State Transition Testing** | Workflow finite state machine | `IMM-09 Repair Workflow`: Open→Assigned→Diagnosing→(Pending Parts)→In Repair→Pending Inspection→Completed/Cannot Repair/Cancelled (15 transition) | Mỗi transition + invalid transition |
| **Use Case Testing** | End-to-end actor flow | UAT scenario V.4, API integration test III.6 | 1/main + 1/alt + 1/exception |
| **Pairwise / Combinatorial** | Nhiều field optional kết hợp | Form tạo WO (`repair_type` × `priority` × `source_type`) | Min set cover all pairs |
| **Error Guessing** | Null, empty, unicode, race, SE ref giả | Tất cả endpoint nhận user input; `stock_entry_ref` không tồn tại; asset_ref giả | Bổ sung — không thay thế |

## II.2. White-box techniques

| Kỹ thuật | Áp dụng vào | Tiêu chí đạt | Công cụ |
|---|---|---|---|
| **Statement coverage** | Service functions `services/imm09.py` (I.1 #6-#21) | ≥ 85% line | `coverage report` |
| **Branch / Decision coverage** | Functions có if/else, try/except (`complete_repair`, `validate_*`, scheduler) | ≥ 80% branch | `coverage --branch` |
| **Condition / MC/DC** | `get_sla_target` matrix, `validate_firmware_change_request` (multi-AND) | Mỗi sub-condition kiểm soát outcome độc lập | Manual test design + coverage |
| **Path coverage** | `validate_repair_source` (≤ 20 LOC, 3 nhánh source_type) | Toàn bộ path khả dĩ | Manual |

## II.3. Mapping Component → Kỹ thuật

| Loại component | Kỹ thuật chính | Kỹ thuật phụ |
|---|---|---|
| Field validator (`validate_*`) | BVA + EP | Error guessing |
| Gate logic (`validate_firmware_change_request`, checklist) | Decision Table | MC/DC |
| `get_sla_target` matrix | Decision Table | BVA (biên SLA) |
| Workflow transition | State Transition | Use Case |
| Service function pure (`get_sla_target`, `_month_range`) | EP + Branch coverage | BVA |
| API endpoint | Use Case + EP | Pairwise (form input) |
| Scheduler (`check_repair_sla_breach`, `update_asset_mttr_avg`) | Use Case (state setup → run → assert) | Error guessing (lock, partial fail) |
| FE view (Playwright) | Use Case end-to-end | Error guessing (network 4xx/5xx, role gate) |

---

# Phần III — Test Plan (Kế hoạch thực thi)

## III.1. Test Pyramid

```
                  ┌────────────┐
                  │  E2E / UAT │   ~5%  (Playwright golden scenario)
                 ─┴────────────┴─
              ┌──────────────────────┐
              │   API Integration    │   ~15% (14 endpoint)
             ─┴──────────────────────┴─
          ┌────────────────────────────────┐
          │  Workflow + DocType lifecycle  │   ~25% (15 transition)
         ─┴────────────────────────────────┴─
      ┌────────────────────────────────────────────┐
      │         Unit — Service Layer               │   ~55%
     ─┴────────────────────────────────────────────┴─
```

→ CLAUDE.md §17 (TDD mandatory): mọi service function có test trước khi code.

## III.2. Unit test — Service Layer

> **Trạng thái thực tế**: test code hợp nhất trong **một file duy nhất** `assetcore/tests/test_imm09.py`. Hai class đã live: `TestSlaMatrix` (4 test), `TestRepairWOCreation` (8 test). Các class còn lại là kế hoạch (⬜ Planned) — split sang file riêng là mục tiêu refactor tương lai.

**File**: `assetcore/tests/test_imm09.py`

| Test class | Function cover (I.1) | Kỹ thuật | Cases | Status |
|---|---|---|---|---|
| `TestSlaMatrix` | `get_sla_target` (#6) | Decision Table | 4 (`test_class_iii_emergency_is_4h`, `test_class_ii_urgent_is_48h`, `test_class_i_normal_is_480h`, `test_unknown_combo_falls_back_to_default`) | ✅ Live |
| `TestRepairWOCreation` | `create_work_order` (#16), `validate_repair_source` (#7), `validate_asset_not_under_repair` (#8) | EP + Error guessing | 8 (`test_standalone_create_succeeds`, `test_requested_by_is_session_user`, `test_failure_description_persisted`, `test_nonexistent_asset_raises_not_found`, `test_create_with_incident_report_succeeds`, `test_sla_is_set_on_wo`, `test_duplicate_open_wo_raises_conflict`) | ✅ Live |
| `TestRepeatFailure` | `check_repeat_failure` (#9) | BVA (29d/30d/31d) | 3 happy/flag | ⬜ Planned |
| `TestSpareParts` | `validate_spare_parts_stock_entries` (#10) | EP + Error guessing | 3 (happy / missing ref / nonexistent SE) | ⬜ Planned |
| `TestFirmwareCR` | `validate_firmware_change_request` (#11) | Decision Table | 4 (no firmware / FCR Approved / FCR Draft / no FCR) | ⬜ Planned |
| `TestChecklist` | `validate_repair_checklist_complete` (#12) | EP | 4 (all Pass / 1 Fail / N-A / empty) | ⬜ Planned |
| `TestSlaBreachPredicate` | `is_sla_breached` (SoT) | BVA biên (`<`, `==`, `>`) | 3 (mttr<target→False; mttr==target→True; mttr>target→True) + None-guard | ✅ Live |
| `TestComplete` | `complete_repair` (#13) | BVA SLA | 4 (mttr_hours calc; mttr<target→0; mttr==target→1; mttr>target→1; ALE + Asset→Active) | ✅ Live |
| `TestSlaMonotonic` | `complete_repair` ↔ `check_repair_sla_breach` | State Transition | 2 (scheduler set 1 lúc đang chạy → confirm_inspection giữ 1, KHÔNG lật 0 cho mttr==target; mttr<target chưa từng breach → 0) | ✅ Live |
| `TestCannotRepair` | `_mark_cannot_repair` (#15) | State Transition | 2 (Asset→Out of Service, ALE created) | ⬜ Planned |
| `TestScheduler` | `check_repair_sla_breach` (#18) | Use Case + Error guessing | 3 (breach flag khi elapsed==target; skip completed; idempotent — không re-publish khi đã 1) | ✅ Live |

> **Mẹo thực thi**: dùng `SimpleNamespace` cho test thuần công thức (`get_sla_target`) — chạy ms-level, không cần fixture cleanup.

## III.3. Integration — DocType lifecycle

**File**: `assetcore/tests/test_imm09.py` (hợp nhất — xem §III.2). Cover hook `validate / before_insert / on_submit / on_update_after_submit`.

| Test | Setup | Action | Assert | Kỹ thuật | Status |
|---|---|---|---|---|---|
| `test_on_insert_sets_asset_under_repair` | Asset Active | `doc.insert()` | `Asset.status == "Under Repair"` | State Transition | ⬜ Planned |
| `test_on_insert_creates_lifecycle_event` | Asset Active | `doc.insert()` | ALE `event_type == "repair_opened"` | EP | ⬜ Planned |
| `test_before_submit_validates_checklist` | WO In Repair, 1 Fail row | `close_work_order` | `frappe.ValidationError` (BR-09-04) | EP | ⬜ Planned |
| `test_on_complete_sets_asset_active` | WO Pending Inspection, all Pass | `confirm_inspection` | `Asset.status == "Active"`, `mttr_hours > 0` | State Transition | ⬜ Planned |
| `test_cannot_repair_sets_oos` | WO with reason | `_mark_cannot_repair` | `Asset.status == "Out of Service"` | State Transition | ⬜ Planned |

> Fixture trong `setUpClass` phải có `tearDownClass` purge — xem skill `assetcore-test` LL-TEST-17.

## III.4. Integration — Workflow transitions

**File**: `assetcore/tests/test_imm09.py`. Workflow `IMM-09 Repair Workflow` (`workflow/imm_09_repair_workflow.json`) — **9 state, 15 transition** (verified `len(...['transitions']) == 15`). Roles thực trong JSON: `System Manager`, `Repair User`. **Bắt buộc** cover 100% transition.

| # | Action | From → To | Role required | Test pass | Test fail (wrong role / gate) |
|---|---|---|---|---|---|
| 1 | Phân công KTV | Open → Assigned | System Manager | ⬜ | ⬜ |
| 2 | Hủy phiếu | Open → Cancelled | System Manager | ⬜ | ⬜ |
| 3 | Bắt đầu chẩn đoán | Assigned → Diagnosing | Repair User | ⬜ | ⬜ |
| 4 | Yêu cầu linh kiện | Diagnosing → Pending Parts | Repair User | ⬜ | ⬜ |
| 5 | Bắt đầu sửa chữa | Diagnosing → In Repair | Repair User | ⬜ | ⬜ |
| 6 | Linh kiện đã nhận - bắt đầu sửa | Pending Parts → In Repair | Repair User | ⬜ | ⬜ |
| 7 | Hoàn thành sửa chữa - chờ kiểm tra | In Repair → Pending Inspection | Repair User | ⬜ | ⬜ |
| 8 | Không thể sửa chữa | In Repair → Cannot Repair | System Manager | ⬜ | ⬜ (require reason) |
| 9 | Xác nhận hoàn thành | Pending Inspection → Completed | System Manager | ⬜ | ⬜ (checklist gate) |
| 10 | Kiểm tra thất bại - sửa lại | Pending Inspection → In Repair | Repair User | ⬜ | ⬜ |
| 11 | Hủy phiếu | Assigned → Cancelled | System Manager | ⬜ | ⬜ |
| 12 | Hủy phiếu | Diagnosing → Cancelled | System Manager | ⬜ | ⬜ |
| 13 | Hủy phiếu | Pending Parts → Cancelled | System Manager | ⬜ | ⬜ |
| 14 | Hủy phiếu | In Repair → Cancelled | System Manager | ⬜ | ⬜ |
| 15 | Hủy phiếu | Pending Inspection → Cancelled | System Manager | ⬜ | ⬜ |

**Kỹ thuật**: State Transition Testing — vẽ state graph; mỗi edge = 1 test pass + 1 test fail (wrong role hoặc gate fail).

## III.5. Integration — Audit chain integrity

Hai test chính (trace 04 Backend §Audit Trail · `IMM Audit Trail` DocType · `_log_lifecycle_event`):
- (a) Sau N mutation (open → assign → diagnose → parts → repair → complete), chain hash SHA-256 hợp lệ end-to-end: `verify_audit_chain(asset) == True`.
- (b) Khi sửa thẳng DB field hash của 1 entry → verify endpoint trả `chain_broken=true` / `verify_audit_chain() == False`.

Status: ⬜ Planned (chưa có test method trong `test_imm09.py` hiện tại).

## III.6. API test

**File**: `assetcore/tests/test_imm09.py`. Cover: happy path + envelope `success=true`; invalid params; FORBIDDEN; pagination; idempotent retry.

| Test | Endpoint (`api/imm09.py`) | Verify | Kỹ thuật | Status |
|---|---|---|---|---|
| `test_list_default_pagination` | `list_repair_work_orders` | page=1, page_size=20, total ≥ 0 | Use Case | ⬜ Planned |
| `test_list_filter_status_open` | `list_repair_work_orders?filters={"status":"Open"}` | Mọi row status == Open | EP | ⬜ Planned |
| `test_get_existing` | `get_repair_work_order` | `success=true`, fields đầy đủ | Use Case | ⬜ Planned |
| `test_get_not_found` | `get_repair_work_order?name=FAKE` | `success=false`, NOT_FOUND | Error guessing | ⬜ Planned |
| `test_create_happy` | `create_repair_work_order` (POST) | `success=true`, WO name trả về | Use Case | ✅ Live (qua `create_work_order` service) |
| `test_create_nonexistent_asset` | `create_repair_work_order` | NOT_FOUND | EP | ✅ Live (`test_nonexistent_asset_raises_not_found`) |
| `test_assign_technician` | `assign_technician` (POST) | status==Assigned, assigned_to set | Use Case | ⬜ Planned |
| `test_close_wo_incomplete_checklist` | `close_work_order` (POST) | ValidationError (BR-09-04) | EP | ⬜ Planned |
| `test_confirm_inspection` | `confirm_inspection` (POST) | status==Completed | Use Case | ⬜ Planned |
| `test_get_kpis` | `get_repair_kpis` | MTTR, SLA compliance fields | Use Case | ⬜ Planned |
| `test_create_low_role_forbidden` | `create_repair_work_order` (role Storekeeper) | FORBIDDEN / 403 | EP (permission partition) | ⬜ Planned |

> Endpoint khác cần cover: `submit_diagnosis`, `start_repair`, `request_spare_parts`, `get_asset_repair_history`, `search_spare_parts`, `get_mttr_report`.

## III.7. E2E browser (Playwright)

Dùng cho flow UI khó cover bằng API: dropdown cascade (Asset → auto-fill risk_class/serial), modal "Không sửa được" yêu cầu lý do, workflow button visibility theo role, banner Repeat Failure, badge SLA breach. Golden scenario: IR → Tạo CM WO → Assign → Diagnose → Parts → In Repair → Checklist → Complete → verify MTTR hiển thị.

→ skill `assetcore-test` Phần 2 (Playwright MCP recipes + R-1..R-9 data rules). Status: ⬜ Planned.

## III.8. Performance test

| Metric | Target | Method |
|---|---|---|
| `list_repair_work_orders` p95 (200 WO) | ≤ 800 ms | k6 ramping 20 VU |
| `create_repair_work_order` p95 | ≤ 1.5 s | k6 POST batch |
| `close_work_order` (full flow) p95 | ≤ 2 s | k6 |
| Scheduler `check_repair_sla_breach` (500 WO) | ≤ 30 s | `time bench execute assetcore.services.imm09.check_repair_sla_breach` |
| List view FE render (100 row) | ≤ 1 s DOMContentLoaded | Lighthouse / Playwright |

## III.9. Test data & Fixtures

| Loại | Cách seed | File |
|---|---|---|
| Master data (Department, AC Asset Category, Vendor, AC UOM) | `fixtures/*.json` (cài qua `bench migrate`) | `assetcore/fixtures/` |
| AC Asset (test) | `test_records.json` / helper `make_asset` | `doctype/asset_repair/` + test helpers |
| Incident Report / PM Work Order | helper trong test | `tests/test_imm09.py` |
| AC Spare Part + Stock Entry | helper / fixture | *(Cần khảo sát file cụ thể)* |
| UAT seed | Python script | `assetcore/scripts/uat/uat_imm09.py` |

> UAT data phải **thực tế** (tên bệnh viện VN, mã NCC chuẩn). Backend test fixture dùng prefix `_Test` — xem `assetcore-test` R-0/R-1.

## III.10. Run commands & Coverage gate

```bash
# Module test (tất cả trong một file)
bench --site assetcore.local run-tests --app assetcore --module assetcore.tests.test_imm09
# Coverage
coverage run -m unittest assetcore.tests.test_imm09 && coverage report
# Workflow smoke
bench --site assetcore.local run-tests --module assetcore.tests.test_workflows
```

| Layer | Target coverage | Đo |
|---|---|---|
| Service (`services/imm09.py`) | ≥ 85% line + ≥ 80% branch | `coverage --branch` |
| DocType lifecycle | ≥ 70% | `coverage report` |
| API (`api/imm09.py`) | ≥ 60% | `coverage report` |
| Frontend (vue-tsc) | 0 error | `npm run build` |

> Coverage % thực tế: *(Cần khảo sát — chạy `coverage report` trên `test_imm09.py`)*. Hiện chỉ 2 class live nên coverage service layer chưa đạt target.

---

# Phần IV — Traceability Matrices

> Mọi test ở Phần III phải xuất hiện ở **cả 3** bảng (audit ngược: thiếu cover US? BR? component nào?).

## IV.1. US → Test mapping

| US ID | AC | Test ID (III.x) | Layer | Status |
|---|---|---|---|---|
| US-09-01 | AC1 | `TestRepairWOCreation::test_standalone_create_succeeds`, `::test_create_with_incident_report_succeeds` | Unit | ✅ Live |
| US-09-01 | AC2 | `TestRepairWOCreation::test_failure_description_persisted`, `::test_requested_by_is_session_user` | Unit | ✅ Live |
| US-09-02 | AC1 | `test_assign_technician` | API | ⬜ Planned |
| US-09-03 | AC1 | `test_submit_diagnosis` | API | ⬜ Planned |
| US-09-04 | AC1 | `test_request_spare_parts` | API | ⬜ Planned |
| US-09-05 | AC1 | `TestSpareParts` (BR-09-02) | Unit | ⬜ Planned |
| US-09-07 | AC1 | `TestChecklist` (BR-09-04) | Unit | ⬜ Planned |
| US-09-08 | AC1 | `test_on_complete_sets_asset_active` | Integration | ⬜ Planned |
| US-09-09 | AC1 | `TestCannotRepair` | Integration | ⬜ Planned |
| US-09-10 | AC1 | `test_get_kpis` | API | ⬜ Planned |
| US-09-11 | AC1 | `test_get_mttr_report` | API | ⬜ Planned |

## IV.2. BR → Test mapping

| BR ID | Phát biểu (rút gọn) | Test ID | Kỹ thuật | Happy / Negative |
|---|---|---|---|---|
| BR-09-01 | WO standalone hợp lệ; nguồn chỉ bắt buộc theo source_type | `TestRepairWOCreation::test_standalone_create_succeeds` (+ Incident case) | EP | 2 / 0 (relaxed) — negative chỉ khi source_type set; ⬜ Planned |
| BR-09-02 | Spare part cần `stock_entry_ref` | `TestSpareParts` | EP + Error guessing | 1 / 2 ⬜ Planned |
| BR-09-03 | firmware_updated → FCR Approved | `TestFirmwareCR` | Decision Table | 2 / 2 ⬜ Planned |
| BR-09-04 | Checklist 100% Pass | `TestChecklist` | EP | 1 / 3 ⬜ Planned |
| BR-09-05 | Asset status transitions + chặn WO trùng | `TestRepairWOCreation::test_duplicate_open_wo_raises_conflict` (✅ Live) + `TestComplete`/`TestCannotRepair` (⬜ Planned) | State Transition | 1 / 1 (live) |
| BR-09-06 | Repeat failure 30 ngày | `TestRepeatFailure` | BVA | 1 / 2 ⬜ Planned |
| BR-09-07 | MTTR > SLA → breach | `TestSlaMatrix` (✅ Live, matrix) + `TestComplete`/`TestScheduler` (⬜ Planned) | BVA + Decision Table | 4 live (matrix) |

## IV.3. Component → Test mapping

| Component (I.1) | Test ID | Test layer | Coverage % | Risk priority (I.3) |
|---|---|---|---|---|
| `get_sla_target` (#6) | `TestSlaMatrix` | Unit | *(Cần khảo sát)* | High |
| `create_work_order` (#16) | `TestRepairWOCreation` | Unit/API | *(Cần khảo sát)* | High |
| `validate_repair_source` (#7) | `TestRepairWOCreation::test_standalone_create_succeeds` | Unit | *(Cần khảo sát)* | Medium |
| `validate_asset_not_under_repair` (#8) | `TestRepairWOCreation::test_duplicate_open_wo_raises_conflict` | Unit | *(Cần khảo sát)* | High |
| `validate_firmware_change_request` (#11) | `TestFirmwareCR` ⬜ | Unit | 0% (planned) | High |
| `validate_repair_checklist_complete` (#12) | `TestChecklist` ⬜ | Unit | 0% (planned) | High |
| `validate_spare_parts_stock_entries` (#10) | `TestSpareParts` ⬜ | Unit | 0% (planned) | High |
| `complete_repair` (#13) | `TestComplete` ⬜ | Unit/Integration | 0% (planned) | Critical |
| Workflow transitions (#5) | III.4 (15 transition) ⬜ | Integration | 0% (planned) | Critical |
| Audit chain (#23) | III.5 ⬜ | Integration | 0% (planned) | Critical |
| API endpoints (#22) | III.6 | API | *(Cần khảo sát)* | Low |

---

# Phần V — UAT Script

## V.1. Phạm vi UAT

- **In-scope**: tạo CM WO (standalone/IR/PM) + 7 BR + workflow + audit + dashboard MTTR + permission mỗi role (V.4).
- **Out-of-scope**: load testing (III.8), penetration testing (VI.10), external system integration.
- **Pre-condition**: site UAT `uat.assetcore.vn` deploy bản mới nhất; seed `uat_imm09.py seed_data` chạy thành công; 6 tester accounts active; Chrome/Edge ≥ 120.

## V.2. Tester accounts

| Username | Email | Role | Vai trò UAT |
|---|---|---|---|
| `manager.ws` | manager.ws@hospital.vn | System Manager (Workshop Lead) | Tạo/phân công/hủy WO, xác nhận hoàn thành |
| `ktv.anha` | ktv.anha@hospital.vn | Repair User (Biomed Technician) | Chẩn đoán, sửa chữa, checklist |
| `ktv.binh` | ktv.binh@hospital.vn | Repair User (Biomed Technician) | Test concurrent + permission scope |
| `kho.vt` | kho.vt@hospital.vn | IMM Storekeeper | Gắn Stock Entry vào spare parts |
| `truong.icu` | truong.icu@hospital.vn | IMM Department Head | Xác nhận nghiệm thu |
| `ptp.k2` | ptp.k2@hospital.vn | IMM Operations Manager | Xem MTTR Report, Dashboard |

Mật khẩu UAT: `Assetcore@2026` (reset sau UAT). Phải có account role thấp (`kho.vt`) để cover FORBIDDEN case.

## V.3. Test data đã seed

| DocType | Số lượng | Ghi chú |
|---|---|---|
| AC Asset | 5 | Mỗi risk class + trạng thái khác nhau |
| Incident Report | 3 | Gắn 3 asset cụ thể |
| PM Work Order | 2 | 1 Halted–Major Failure, 1 Completed |
| AC Spare Part / Item | 4 | Có stock ở `Workshop-Store` |
| Stock Entry | 3 | Sẵn dùng cho `stock_entry_ref` |
| Repair User accounts | 2 | `ktv.anha`, `ktv.binh` |

Reset: `bench --site uat.assetcore.vn execute assetcore.scripts.uat.uat_imm09.seed_data`.

## V.4. UAT Scenarios — Suy ra từ US + Activity

> Mỗi scenario theo template Phụ lục A. Quy tắc suy (Use Case Testing): mỗi US → ≥ 1 happy; mỗi Activity branch ngoại lệ → ≥ 1; mỗi role mutate → ≥ 1 permission verify; mỗi terminal transition → ≥ 1 audit verify; ≥ 1 negative per BR Critical.

| ID | Actor | Pre-condition | US/BR cover | Kỹ thuật | Kết quả mong đợi |
|---|---|---|---|---|---|
| UAT-IMM-09-01 | System Manager | Asset Active + IR `IR-2026-00123` | US-09-01, BR-09-01 | Use Case happy | WO tạo, Asset→Under Repair, ALE `repair_opened` |
| UAT-IMM-09-02 | System Manager | Asset Active, không IR/PM | US-09-01, BR-09-01 (relaxed) | Use Case alt | WO standalone tạo thành công, status Open |
| UAT-IMM-09-03 | System Manager → Repair User | WO từ UAT-01 | US-09-02, US-09-03 | State Transition | Assign → Diagnosing → Pending Parts |
| UAT-IMM-09-04 | IMM Storekeeper → Repair User | WO Pending Parts | US-09-04, BR-09-02 | Use Case + EP negative | Gắn `stock_entry_ref`; thiếu ref → VALIDATION |
| UAT-IMM-09-05 | Repair User → IMM Department Head | WO In Repair, checklist | US-09-07, BR-09-04, US-09-08 | EP negative + State Transition | Fail row block; all Pass → Pending Inspection → Completed; MTTR > 0; ALE `repair_completed` |
| UAT-IMM-09-06 | System Manager | WO Diagnosing | US-09-09, BR-09-05 | State Transition | Cannot Repair (require reason) → Asset Out of Service; ALE `cannot_repair` |
| UAT-IMM-09-07 | System Manager + Repair User | WO In Repair, firmware_updated=1 | BR-09-03 | Decision Table | Thiếu FCR / FCR Draft → block; FCR Approved → submit OK |
| UAT-IMM-09-08 | System Manager | 2 WO Completed trong 30 ngày cùng asset | US-09-07, BR-09-06 | BVA | WO thứ 3 → banner Repeat Failure, `is_repeat_failure=1`, link mở CAPA (IMM-12) |
| UAT-IMM-09-09 | IMM Operations Manager | WO Class III Emergency, open_datetime 5h trước | BR-09-07 | BVA + Use Case | Sau scheduler → `sla_breached=1`, dashboard KPI giảm |
| UAT-IMM-09-10 | Repair User (2 account) | WO-A→ktv.anha, WO-B→ktv.binh | VI.1 RBAC | EP permission | `ktv.anha` chỉ thấy WO-A; truy cập WO-B → 403 |
| UAT-IMM-09-11 | IMM Operations Manager | Có WO Completed | US-09-10, US-09-11 | Use Case | Dashboard KPI hiển thị; drill-down MTTR theo risk class |
| UAT-IMM-09-12 | IMM QA Officer | WO Completed (UAT-05) | III.5 Audit | Use Case audit | `verify_audit_chain(asset)==True`; sửa trực tiếp ALE bị block |

## V.5. Tổng hợp kết quả & Bug found

**Bảng kết quả**:

| Scenario | Status | Tester | Ngày | Ghi chú |
|---|---|---|---|---|
| UAT-IMM-09-01 | ☐ Pass / ☐ Fail / ☐ Block | | | |
| UAT-IMM-09-02 | ☐ Pass / ☐ Fail / ☐ Block | | | |
| UAT-IMM-09-03 | ☐ Pass / ☐ Fail / ☐ Block | | | |
| UAT-IMM-09-04 | ☐ Pass / ☐ Fail / ☐ Block | | | |
| UAT-IMM-09-05 | ☐ Pass / ☐ Fail / ☐ Block | | | |
| UAT-IMM-09-06 | ☐ Pass / ☐ Fail / ☐ Block | | | |
| UAT-IMM-09-07 | ☐ Pass / ☐ Fail / ☐ Block | | | |
| UAT-IMM-09-08 | ☐ Pass / ☐ Fail / ☐ Block | | | |
| UAT-IMM-09-09 | ☐ Pass / ☐ Fail / ☐ Block | | | |
| UAT-IMM-09-10 | ☐ Pass / ☐ Fail / ☐ Block | | | |
| UAT-IMM-09-11 | ☐ Pass / ☐ Fail / ☐ Block | | | |
| UAT-IMM-09-12 | ☐ Pass / ☐ Fail / ☐ Block | | | |

**Bug list**:

| Issue ID | Severity (Blocker/Major/Minor/Trivial) | Mô tả | Fix status |
|---|---|---|---|
| (điền khi phát sinh) | | | |

**Acceptance**: ≥ 95% PASS, Blocker = 0, Major ≤ 2 (có workaround documented).

**Sign-off**:

| Vai trò | Người | Ngày | Chữ ký |
|---|---|---|---|
| BA Lead | | | |
| QA Lead | | | |
| Module Owner (IMM-09) | | | |
| Đại diện end-user (Workshop Manager) | | | |

---

# Phần VI — Security Review (gate)

## VI.1. RBAC

**Role definitions** (file `fixtures/role.json` + `role_profile.json`). Roles thực dùng trong workflow JSON: `System Manager`, `Repair User`; role nghiệp vụ bổ sung: IMM Storekeeper, IMM Department Head, IMM Operations Manager, IMM QA Officer.

**DocPerm matrix — `Asset Repair`** (Decision Table: mỗi (role × action) = Allow/Deny):

| Role | Read | Write | Create | Submit | Cancel | Amend | Delete |
|---|---|---|---|---|---|---|---|
| System Manager (Workshop Lead) | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| Repair User (Biomed Technician) | ✅ (own) | ✅ (own) | ❌ | ✅ (own) | ❌ | ❌ | ❌ |
| IMM Storekeeper | ✅ | ✅ (spare parts only) | ❌ | ❌ | ❌ | ❌ | ❌ |
| IMM Department Head | ✅ | ✅ (confirm only) | ❌ | ❌ | ❌ | ❌ | ❌ |
| IMM Operations Manager | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| IMM QA Officer | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

> Cần đối chiếu DocPerm thực trong `asset_repair.json` để xác nhận đúng — bảng trên là policy thiết kế. *(Cần khảo sát: số DocPerm row thực)*.

**Field-level permission (permlevel ≠ 0)**:

| Field | permlevel | Mô tả |
|---|---|---|
| `sla_breached` | 1 — Workshop Lead+ | Không cho KTV xem SLA flag |
| `total_parts_cost` | 1 — Operations Manager+ | Chi phí ẩn với KTV/Kho |
| `root_cause_category` | 0 — authenticated | Nội dung kỹ thuật |

> Cần verify permlevel thực trong `asset_repair.json`. *(Cần khảo sát)*.

**User Permission (Row-level)** — `permission_query_conditions` trong `assetcore/permissions.py::asset_repair_query`: senior role (Workshop Lead/Admin) + Auditor thấy tất cả; Vendor/Technician chỉ thấy WO `assigned_to = session.user`:
```python
def asset_repair_query(user):
    roles = _user_roles(user)
    if _is_senior(roles) or _AUDITOR_ROLE in roles:
        return ""
    if _VENDOR_ROLE in roles or (roles & _TECHNICIAN_ROLES):
        return f"(`tabAsset Repair`.assigned_to = '{_esc(user)}')"
    return ""
```

## VI.2. API security

- **Whitelist hygiene**: 14 endpoint `@frappe.whitelist` trong `api/imm09.py`; endpoint mutating dùng `methods=["POST"]` (create/assign/diagnosis/start/parts/close/confirm). Cần xác nhận mỗi endpoint có docstring + `rbac.require()`. *(Cần khảo sát: rbac.require coverage)*.
- **CSRF**: Frappe default `X-Frappe-CSRF-Token`.
- **Input validation**: `name`/`asset_ref` validate qua repo/`frappe.get_value` trước khi dùng (`test_nonexistent_asset_raises_not_found` ✅ Live).
- **SQL injection**: `asset_repair_query` dùng `_esc(user)` escape; ORM parameterized. Không raw f-string SQL từ user input chưa escape.
- **Rate limit**: ⚠️ Roadmap — cấu hình Frappe rate limit cho `create_repair_work_order`, `close_work_order`.

## VI.3. Audit trail integrity

Mọi state change sinh `IMM Audit Trail` qua `_log_lifecycle_event`. Hash chain SHA-256: `hash = SHA256(prev_hash + canonical_json(event))`. Verify: `verify_audit_chain(asset) → bool`. User KHÔNG có quyền Delete/Amend `IMM Audit Trail` (không có DocPerm). Retention ≥ 5 năm (NĐ98/2021/NĐ-CP Điều 15 · ISO 13485:7.5.9). → test case III.5 (intact + tampered).

## VI.4. Authentication & session

| Hạng mục | Config |
|---|---|
| Login | Frappe default username + password |
| Session timeout | 8 giờ (`frappe.conf.session_expiry`) |
| Lockout | Frappe default: 3 fail → lock 15 phút |
| Password policy | ≥ 8 ký tự, 1 hoa, 1 số |
| API key | Per-user, rotate 90 ngày; không commit git |
| 2FA | Roadmap Phase 2 — TOTP via Frappe 2FA |

## VI.5. Data sensitivity

| Loại | Trường | Sensitivity | Bảo vệ |
|---|---|---|---|
| Thông tin kỹ thuật thiết bị | `asset_ref`, serial | Internal | Role permission |
| Chi phí sửa chữa | `total_parts_cost` | Confidential | permlevel 1 |
| Ghi chú chẩn đoán | `diagnosis_notes` | Internal | Role permission |
| Thông tin cá nhân user | `assigned_to`, `requested_by` | Internal | Role permission |
| Dữ liệu bệnh nhân | Không lưu | N/A | AssetCore KHÔNG lưu patient data |

## VI.6. Vendor isolation

Vendor External (qua `_VENDOR_ROLE`) chỉ thấy WO `assigned_to = session.user` (`permission_query_conditions`). KHÔNG thấy: `total_parts_cost`, `diagnosis_notes`, audit trail vendor khác, dashboard. KHÔNG export bulk. → test case III.6 (low-role API call) + UAT-IMM-09-10.

## VI.7. Secrets management

`site_config.json` không commit (`.gitignore`). External token (email/SMS) lưu `frappe.conf`, không hardcode. Backup encrypt at-rest off-site (xem 08 §Deployment). Secret scan CI: `detect-secrets` pre-commit hook.

## VI.8. Logging & monitoring

| Sự kiện | Log level | Where | Alert? |
|---|---|---|---|
| SLA breach phát hiện | WARNING | `frappe.log_error` + `IMM Audit Trail` | ✅ Email Workshop Manager |
| WO overdue > 7 ngày | WARNING | scheduler log | ✅ Email Workshop Manager |
| Audit chain tamper | ERROR | `frappe.log_error` | ✅ Email System Admin |
| API 4xx (create fail) | INFO | Frappe access log | ❌ |
| Login fail | INFO | Frappe login log | ✅ (sau 3 lần) |
| PII / token | ❌ | Policy: KHÔNG log patient data / token | — |

## VI.9. Threat model (STRIDE-lite)

| Threat | Vector | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| **S**poofing | Giả mạo session KTV | Low | High | Session cookie HttpOnly + SameSite; Frappe session verify |
| **T**ampering | Sửa `IMM Audit Trail` DB trực tiếp / `total_parts_cost` bypass permlevel | Low | Critical | DocPerm no-delete; verify chain endpoint; permlevel 1 |
| **R**epudiation | KTV phủ nhận đã Submit | Low | High | `IMM Audit Trail` + hash chain + actor field |
| **I**nfo disclosure | KTV xem WO của người khác | Low | Medium | `asset_repair_query` row filter + test UAT-IMM-09-10 |
| **D**enial of service | Scheduler overload 1000+ WO open | Medium | Medium | Batch/run + index `status + open_datetime`; rate limit |
| **E**levation of privilege | Storekeeper gọi `assign_technician` | Low | High | Workflow role check + `rbac.require` |

## VI.10. Penetration test

Trước release đầu tiên (go-live bệnh viện): Burp/OWASP ZAP scan trên `uat.assetcore.vn` (0 High/Critical); sqlmap mode-safe trên `create_repair_work_order`, `close_work_order`; CSRF test bằng curl không token; role escalation (`assign_technician` với Storekeeper → 403). Report lưu `docs/security/pentest_imm09_v1.md`.

## VI.11. Sign-off

| Vai trò | Người | Ngày | Quyết định |
|---|---|---|---|
| QA Lead | | | ☐ Pass / ☐ Pass with conditions / ☐ Fail |
| Security Officer / Tech Lead | | | ☐ Pass / ☐ Pass with conditions / ☐ Fail |
| Module Owner (IMM-09) | | | ☐ Pass / ☐ Pass with conditions / ☐ Fail |

**Điều kiện go-live**: tất cả Sign-off Pass hoặc Pass with conditions (workaround documented).

---

# Phần VII — Code Quality

## VII.1. Tool matrix

| Tool | Mục tiêu | Target | Cadence |
|---|---|---|---|
| **SonarQube** (BE Python) | Bug 0 Critical, code smell ≤ 5, duplication ≤ 3%, coverage ≥ 70%, security hotspot review 100% | Quality Gate pass | Mỗi PR (CI gate) |
| **Lighthouse** (FE — CMDashboardView) | Performance ≥ 90, Accessibility ≥ 95, Best Practices ≥ 90, SEO ≥ 80 | ≥ target | Mỗi release + monthly |
| **ESLint + vue-tsc** (FE) | 0 error, 0 warning prod build | pass | Mỗi PR FE (CI gate) |
| **ruff / black** (BE) | 0 error, format PEP8 | pass | Mỗi PR (CI gate) |
| **Bundle size** (FE chunk imm09) | main ≤ 250 KB gzip, async ≤ 80 KB gzip | ≤ budget | Mỗi PR FE (CI report) |

## VII.2. Cadence

- SonarQube: mỗi PR (CI gate, fail nếu Quality Gate fail).
- Lighthouse: mỗi release lớn + monthly audit.
- ESLint / ruff: mỗi PR (CI gate).
- Bundle size: mỗi PR FE (CI report, fail nếu vượt budget).

Gắn screenshot SonarQube + Lighthouse vào file 09 §Release Notes khi báo cáo final.

---

# Phụ lục A — Template per UAT scenario

```markdown
### UAT-IMM-09-<NN> — <Tên>

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
### TC-IMM-09-<LAYER>-<NN> — <Tên>

**Component (I.1)**: <…>
**Liên kết**: US-<NN> | BR-<NN> | ACT-<NN>
**Kỹ thuật (II.1/II.2)**: <vd BVA boundary repeat-failure window=30d>
**Priority (I.3)**: Critical / High / Medium / Low
**Test type**: Unit / Integration / API / E2E
**Pre-condition**: <fixture / state setup>

**Input**:
- <field>: <value>

**Steps**:
1. <…>
2. <…>

**Expected**:
- ServiceError(code=VALIDATION, message contains "BR-09-04")
- doc.workflow_state unchanged

**Post-condition**: <DB rollback / fixture cleanup>
```

# Phụ lục C — Workflow State Transition Test template

```markdown
### TC-IMM-09-WF-<NN> — <action>: <from> → <to>

**Workflow JSON**: `workflow/imm_09_repair_workflow.json`
**Role required**: <System Manager | Repair User>
**Pre-condition**: doc.workflow_state = <from>, gate đã pass
**Action**: apply_workflow(doc, "<action>")
**Expected (happy)**: doc.workflow_state = <to>, audit entry created
**Expected (negative role)**: PermissionError / FORBIDDEN
**Expected (gate fail)**: ServiceError(code=BUSINESS_RULE, message contains "<BR-09-xx>")
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
- [x] II.2 white-box criteria xác định (statement + branch bắt buộc)
- [x] II.3 mapping component → kỹ thuật điền đầy đủ

## III. Test Plan
- [x] Test class structure cho mọi service public function (I.1)
- [ ] ≥ 1 happy + 1 negative test mỗi function — chỉ 2 class live (`TestSlaMatrix`, `TestRepairWOCreation`); 7 class còn lại ⬜ Planned
- [ ] Workflow transitions cover 100% — 15 transition đã liệt kê nhưng test ⬜ Planned (chưa có method)
- [ ] Audit chain test (intact + tampered) — ⬜ Planned, chưa viết
- [ ] API test ≥ 60% coverage + permission matrix — endpoint liệt kê đủ, hầu hết ⬜ Planned
- [x] Performance target xác định
- [x] CI command chạy clean (`bench run-tests --module …`)
- [ ] **SonarQube Quality Gate pass** + **Lighthouse score ≥ target** — chưa chạy

## IV. Traceability
- [x] IV.1 US → Test: mọi US có ≥ 1 Test ID
- [x] IV.2 BR → Test: mọi BR có dòng map (BR Critical chưa đủ happy+negative live)
- [x] IV.3 Component → Test: bảng đầy đủ (coverage % nhiều ô *(Cần khảo sát)*)

## V. UAT
- [x] Mỗi US có ≥ 1 UAT scenario
- [x] ≥ 1 negative + permission + audit verify scenario
- [ ] Test data seed script chạy được — `uat_imm09.py` cần verify chạy thực
- [x] Tester accounts đã định nghĩa (đủ role, có role thấp cho FORBIDDEN)
- [x] Sign-off section sẵn sàng

## VI. Security
- [x] DocPerm matrix (Decision Table) — policy đầy đủ; số row thực *(Cần khảo sát)*
- [ ] Mọi field nhạy cảm có permlevel ≠ 0 — cần verify trong `asset_repair.json`
- [ ] SQL injection + CSRF test pass — chưa chạy (mitigation `_esc` đã có)
- [ ] Audit chain test pass (intact + tampered) — ⬜ Planned
- [ ] Vendor isolation test pass (low-role API call) — ⬜ Planned (UAT-IMM-09-10)
- [x] Threat model đủ 6 STRIDE với mitigation
- [x] Sign-off section sẵn sàng

## VII. Code Quality
- [ ] SonarQube Quality Gate pass — chưa chạy
- [ ] Lighthouse ≥ target — chưa chạy
- [ ] Bundle size ≤ budget — chưa đo
- [ ] Screenshot báo cáo gắn vào file 09 — chưa có
