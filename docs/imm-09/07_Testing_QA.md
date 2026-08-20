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
| BR-09-09 | Restore asset CÓ ĐIỀU KIỆN theo state machine: Asset→Active CHỈ khi prev=`Under Repair`; prev=`Out of Service`/khác → giữ hold (no override NĐ98); prev=`Decommissioned` → bỏ restore, no raise. MỌI nhánh ghi 1 ALE. **INV-09-RESTORE-1**: lifecycle_status mới ∈ {Active (chỉ khi prev=Under Repair), prev giữ nguyên}; nhánh restore không raise | `complete_repair` (#13) khối transition guarded — `TestRestoreGuard` | Decision Table (3 nhánh prev) + State Transition |
| BR-09-10 | **SLA/MTTR clock-stop khi Pending Parts.** SoT `repair_elapsed_hours = (until−open) − parts_hold_hours_effective` (trừ thời gian chờ phụ tùng). 3 consumer (`complete_repair`/`check_repair_sla_breach`/`_row_is_live_overdue`) cùng SoT. `is_sla_breached`/SLA matrix/biên `>=` BẤT BIẾN. **INV-CM-HOLD-1..6** (SoT duy nhất; stamp/accumulate đối xứng; monotonic ≥0; no-regression khi hold=0; chốt hold cuối trước elapsed; card==scheduler==stamp) | `repair_elapsed_hours`/`enter_parts_hold`/`exit_parts_hold` (SoT mới) + 2 field; `complete_repair` (#13), `check_repair_sla_breach` (#18), `_row_is_live_overdue` — `TestSlaClockStop` | BVA (biên hold: 0, Δ==0, multi-cycle) + State Transition + invariant |
| BR-09-15 | **Đính ảnh mục checklist sửa chữa — permission + validation + reject-order** (mobile CR-15/G6) — mọi nhánh reject TRƯỚC File.insert; 2 loại 403 (dispatcher-403 guest + in-handler cap-403); discriminator = Frappe child `idx`; `db.set_value` KHÔNG `doc.save()` | `attach_repair_checklist_photo`/`_find_repair_checklist_row`/`_assert_can_attach_repair_photo` — `TestAttachRepairChecklistPhoto` (`test_imm09.py`) — TC-CM-PHOTO-01..08 | Decision Table + EP + BVA (size/max-count) |
| BR-09-16 | **Bằng chứng NĐ98 (Class C/D) — lifecycle event hard-req + read-back parity + count==rows** — đúng 1 ALE `repair_checklist_photo_attached` (canonical create_lifecycle_event TRỰC TIẾP, KHÔNG wrapper swallow); event throw→File+set_value rollback (không orphan/không silent); `get_repair_work_order.repair_checklist[idx].photo == file_url`; SoT `row.photo` chung cho max-count + hiển thị | `attach_repair_checklist_photo`; `asset_lifecycle_event.json` (+enum) — `TestAttachRepairChecklistPhoto` — TC-CM-PHOTO-EVIDENCE-01..03 | Invariant (rollback-on-throw, count==rows) |

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

> **Trạng thái thực tế**: test code hợp nhất trong **một file duy nhất** `assetcore/tests/imm09/test_imm09.py`. Hai class đã live: `TestSlaMatrix` (4 test), `TestRepairWOCreation` (8 test). Các class còn lại là kế hoạch (⬜ Planned) — split sang file riêng là mục tiêu refactor tương lai.

**File**: `assetcore/tests/imm09/test_imm09.py`

| Test class | Function cover (I.1) | Kỹ thuật | Cases | Status |
|---|---|---|---|---|
| `TestSlaMatrix` | `get_sla_target` (#6) | Decision Table | 4 (`test_class_iii_emergency_is_4h`, `test_class_ii_urgent_is_48h`, `test_class_i_normal_is_480h`, `test_unknown_combo_falls_back_to_default`) | ✅ Live |
| `TestRepairWOCreation` | `create_work_order` (#16), `validate_repair_source` (#7), `validate_asset_not_under_repair` (#8) | EP + Error guessing | 8 (`test_standalone_create_succeeds`, `test_requested_by_is_session_user`, `test_failure_description_persisted`, `test_nonexistent_asset_raises_not_found`, `test_create_with_incident_report_succeeds`, `test_sla_is_set_on_wo`, `test_duplicate_open_wo_raises_conflict`) | ✅ Live |
| `TestRepeatFailure` | `check_repeat_failure` (#9) | BVA (29d/30d/31d) | 3 happy/flag | ⬜ Planned |
| `TestSpareParts` | `validate_spare_parts_stock_entries` (#10) | EP + Error guessing | 3 (happy / missing ref / nonexistent SE) | ⬜ Planned |
| `TestFirmwareCR` | `validate_firmware_change_request` (#11) | Decision Table | 4 (no firmware / FCR Approved / FCR Draft / no FCR) | ⬜ Planned |
| `TestFirmwareTransition` | `_FCR_VALID_TRANSITIONS` / `approve_firmware_cr` / `deploy_firmware_cr` / `rollback_firmware_cr` / `firmware_allowed_transitions` / `update_firmware_cr` strip (BR-09-18/19/20) | State Transition + Decision Table + Invariant (rollback-on-throw · count-gate CRUD) | **≥ 14** — TC-FCR-01..09 (capability + valid-transition + audit + event-throw-rollback) + TC-FCR-CRUD-GUARD-01 + TC-FCR-CTA-01..04 (allowed_transitions lọc theo cap + can_approve) | ⬜ Planned (Vòng 10, RED-first) |
| `TestChecklist` | `validate_repair_checklist_complete` (#12) | EP | 4 (all Pass / 1 Fail / N-A / empty) | ⬜ Planned |
| `TestSeedChecklist` | `create_work_order` seed (#16) / `_standard_repair_checklist_rows` / `_apply_checklist` idx-update / `backfill_repair_checklists` (CR-50) | EP + Invariant (len-preserve, category-preserve, idempotent) | **7** — xem TC-CM-SEED-01..07 dưới (AC1/AC2/AC3/AC4/AC5) | ⬜ Planned (Vòng 4, RED-first) |
| `TestSlaBreachPredicate` | `is_sla_breached` (SoT) | BVA biên (`<`, `==`, `>`) | 3 (mttr<target→False; mttr==target→True; mttr>target→True) + None-guard | ✅ Live |
| `TestComplete` | `complete_repair` (#13) | BVA SLA | 4 (mttr_hours calc; mttr<target→0; mttr==target→1; mttr>target→1; ALE + Asset→Active khi prev=Under Repair) | ✅ Live |
| `TestRestoreGuard` | `complete_repair` khối transition (BR-09-09) | State Transition + Decision Table | 3 (A prev=Under Repair → Active + ALE from=Under Repair to=Active; B prev=Out of Service → GIỮ OoS, KHÔNG ép Active + ALE from=to=OoS note hold; C prev=Decommissioned → submit KHÔNG raise, giữ Decommissioned + ALE from=to note đã thanh lý) — **INV-09-RESTORE-1** | ⬜ Planned (Scenario 9.10, 9.11) |
| `TestSlaMonotonic` | `complete_repair` ↔ `check_repair_sla_breach` | State Transition | 2 (scheduler set 1 lúc đang chạy → confirm_inspection giữ 1, KHÔNG lật 0 cho mttr==target; mttr<target chưa từng breach → 0) | ✅ Live |
| `TestCannotRepair` | `_mark_cannot_repair` (#15) | State Transition | 2 (Asset→Out of Service, ALE created) | ⬜ Planned |
| `TestScheduler` | `check_repair_sla_breach` (#18) | Use Case + Error guessing | 3 (breach flag khi elapsed==target; skip completed; idempotent — không re-publish khi đã 1) | ✅ Live |
| `TestCmSlaBreachLiveSoT` | `cm_sla_breach_count` / `_row_is_live_overdue` / `_enrich_sla_breach` (BR-09-07 LIVE) | State + Decision Table + invariant | 5 (INV-CM-SLA-1 open live-overdue cờ=0 → count +1 ngay; INV-CM-SLA-2 idempotent trước==sau scheduler stamp; INV-CM-SLA-3 completed cờ=1 vẫn đếm + completed in-hạn cờ=0 không đếm; INV-CM-SLA-4 Cannot Repair/Cancelled overdue cờ=0 no-phantom; INV-CM-SLA-5 list enrich is_sla_breached live == count card) + grep-guard (no `_count({sla_breached:1})` cho KPI) | ⬜ Planned (Scenario 9.9) |
| `TestSlaClockStop` | `repair_elapsed_hours` (SoT) / `enter_parts_hold` / `exit_parts_hold` / 3 consumer (BR-09-10) | BVA biên hold + State Transition + invariant | **6** — xem TC-09-HOLD-01..06 dưới (INV-CM-HOLD-1..6) + grep-guard (0 idiom `(now/completion−open)` thô quyết breach/MTTR) | ⬜ Planned (Scenario 9.12) |
| `TestAttachRepairChecklistPhoto` | `attach_repair_checklist_photo` / `_find_repair_checklist_row` / `_repair_checklist_item_photos` / `_assert_can_attach_repair_photo` (BR-09-15/16) | Decision Table + EP + BVA (size/max-count boundary) + Invariant (rollback-on-throw, count==rows) | **≥ 11** — TC-CM-PHOTO-01..08 (permission + validation + reject-order + 2 loại 403) + TC-CM-PHOTO-EVIDENCE-01..03 (lifecycle hard-req + read-back parity + count==rows) | ⬜ Planned (Vòng 3, RED-first) |

**TestSeedChecklist — chi tiết test case (CR-50, ADR-IMM09-SEED-CHECKLIST — gỡ deadlock `confirm_inspection` 422):**

| TC | Setup | Action | Expect | AC |
|----|-------|--------|--------|----|
| **TC-CM-SEED-01** *(seed không rỗng)* | Asset hợp lệ (repairable) | `create_work_order(...)` | `len(repair_checklist) == 6`; mỗi dòng `test_description` non-empty ∧ `test_category ∈ {Electrical,Mechanical,Software,Safety,Performance}`; `result == ""` (trống) | AC1 |
| **TC-CM-SEED-02** *(happy submit sau điền Pass)* | WO CM mới (seeded) đưa về In Repair | `close_work_order(checklist_results=[{idx:i, result:"Pass"} for i in 1..6], dept_head_name=...)` → `confirm_inspection` | submit THÀNH CÔNG; `status == "Completed"`; **KHÔNG** 422; asset rời `Under Repair` (→ Active nếu prev=Under Repair); `mttr_hours` chốt (non-null) | AC2 |
| **TC-CM-SEED-03** *(regression: trống → chặn)* | WO seeded, KTV chỉ điền 5/6 dòng Pass (1 dòng result trống) | `close_work_order(...)` → `confirm_inspection` | 422 `IMM09_CHECKLIST_INCOMPLETE` (idx dòng trống); `status` GIỮ `Pending Inspection` (không submit) | AC3 |
| **TC-CM-SEED-04** *(regression: Fail → chặn)* | WO seeded, 5 Pass + 1 `result="Fail"` | `close_work_order(...)` → `confirm_inspection` | 422 `IMM09_CHECKLIST_FAILED` (idx dòng Fail); không submit | AC3 |
| **TC-CM-SEED-05** *(idx-update, no append trùng)* | WO seeded (`len==6`) | `close_work_order(checklist_results=[{idx:1, result:"Pass", measured_value:"24V"}])` | `len(repair_checklist)` **GIỮ == 6** (KHÔNG append dòng thứ 7); `row[idx=1].result=="Pass"`, `.measured_value=="24V"`; **`test_category`/`test_description` dòng idx=1 BẢO TOÀN** (giá trị seed) | AC4 |
| **TC-CM-SEED-06** *(backfill phiếu kẹt)* | Phiếu CM legacy `repair_checklist==[]`, `status` chưa đóng (vd `Pending Inspection`), `docstatus==0` | `backfill_repair_checklists(dry_run=0)` | trả `{scanned, backfilled>=1, ...}`; phiếu đó `len(repair_checklist)==6` (danh mục chuẩn); sau backfill `confirm_inspection` (điền Pass) submit được | AC5 |
| **TC-CM-SEED-07** *(backfill idempotent + skip đã-đóng)* | (a) chạy backfill lần 2; (b) phiếu `Completed`/`Cancelled` hoặc đã có ≥1 dòng | `backfill_repair_checklists(dry_run=0)` ×2 | lần 2 `backfilled==0` (idempotent); phiếu Completed/Cancelled/có-dòng **KHÔNG** bị đụng (`len` giữ nguyên, không thêm) | AC5 |

> **Mẹo thực thi (TestSeedChecklist):** dùng fixture Asset repairable (`lifecycle_status` cho phép → Under Repair). RED-first: viết TC-CM-SEED-01 (len==6) TRƯỚC khi thêm seed vào `create_work_order` ⇒ đỏ (len==0); implement seed ⇒ xanh. TC-CM-SEED-05 chứng minh `_apply_checklist` đi nhánh idx-update (không append) — assert `len` bất biến + category-preserve. Backfill test tạo phiếu 0-dòng qua `frappe.db.set_value`/`doc` trực tiếp (bypass seed) để mô phỏng legacy. Teardown `_asset_cleanup` + purge WO test (prefix `_Test CM-SEED%`). Module-isolated: `bench --site miyano run-tests --module assetcore.tests.imm09.test_imm09`.

**TestAttachRepairChecklistPhoto — chi tiết test case (BR-09-15/16, mobile CR-15/G6):**

| TC | Setup | Action | Expect | Kỹ thuật |
|----|-------|--------|--------|----------|
| **TC-CM-PHOTO-01** *(happy)* | WO mở, KTV = `assigned_to`; `repair_checklist` có ≥1 hàng (idx=1) chưa có `photo`; jpg hợp lệ | `attach_repair_checklist_photo(WO, 1, jpg)` as assignee | `success=true`, `data={file_url, file_name, checklist_item_idx:1}`; reload DB: `Repair Checklist` (idx=1) `.photo == file_url`; **đúng 1** File private (`attached_to='Asset Repair'`); `workflow_state`/`status` KHÔNG đổi | Happy path |
| **TC-CM-PHOTO-02** *(NOT_FOUND)* | WO không tồn tại | `attach_repair_checklist_photo("NOPE", 1, jpg)` | `code=NOT_FOUND`; **0 File** tạo | EP |
| **TC-CM-PHOTO-03** *(in-handler cap-403)* | WO của KTV khác; user hiện tại KHÔNG assignee ∧ KHÔNG `repair.write` (vd Auditor) | attach as user đó | `code=FORBIDDEN` (Decision-B HTTP-200 body); **0 File**; KHÔNG leak raw cap | Decision Table |
| **TC-CM-PHOTO-04** *(idx không khớp)* | WO có 2 hàng checklist (idx 1,2) | `attach_repair_checklist_photo(WO, 99, jpg)` | `code=VALIDATION`, `fields.file`="Không tìm thấy mục checklist…"; **0 File** | EP (idx ngoài miền) |
| **TC-CM-PHOTO-05** *(thiếu file)* | WO hợp lệ, assignee | attach với `filedata=None` | `code=VALIDATION`, `fields.file`="Thiếu tệp ảnh"; **0 File** | EP |
| **TC-CM-PHOTO-06** *(content-type sai)* | WO hợp lệ, assignee, `content_type="application/pdf"` | attach | `code=VALIDATION`, `fields.file`="Tệp phải là ảnh JPG hoặc PNG"; **0 File** | EP |
| **TC-CM-PHOTO-07** *(size > cap)* | `filedata` > 10 MB, content-type jpg | attach | `code=VALIDATION`, `fields.file`="…tối đa 10 MB"; **0 File** | BVA (biên cap) |
| **TC-CM-PHOTO-08** *(max-count/mục)* | hàng idx=1 đã có `photo` (đính lần 1) | đính lần 2 vào idx=1 | `code=VALIDATION`, `fields.file`="Mỗi mục checklist chỉ đính 1 ảnh"; **KHÔNG** ghi đè; vẫn đúng 1 File cũ | BVA (max=1) |
| **TC-CM-PHOTO-EVIDENCE-01** *(lifecycle hard-req)* | WO hợp lệ, assignee | attach thành công | **đúng 1** `Asset Lifecycle Event` `event_type='repair_checklist_photo_attached'` (`asset=wo.asset_ref`, `root_doctype='Asset Repair'`, `root_record=WO`); seed enum qua `create_lifecycle_event` | Invariant |
| **TC-CM-PHOTO-EVIDENCE-02** *(rollback-on-throw, KHÔNG orphan)* | monkeypatch `create_lifecycle_event` raise | attach | raise propagate (KHÔNG swallow); sau rollback: **0 File** mới, `row.photo` GIỮ nguyên (chưa commit) ⇒ không orphan, không silent | Invariant (RED-prove: nếu dùng wrapper swallow → File orphan + row.photo set nhưng KHÔNG event → FAIL) |
| **TC-CM-PHOTO-EVIDENCE-03** *(read-back parity + count==rows)* | attach idx=1 thành công | `get_repair_work_order(WO)` | `repair_checklist[idx=1].photo == file_url` vừa trả (get_work_order KHÔNG đổi); `len(_repair_checklist_item_photos(row))==1` == số ảnh hiển thị (count==rows) | Invariant |

> **Mẹo thực thi (TestAttachRepairChecklistPhoto):** cần fixture Asset Repair thật + ≥1 hàng `repair_checklist` (append qua `doc.append("repair_checklist", {...})`); teardown `_purge` (prefix `_Test CM-PHOTO%`) + xóa File orphan test. File nhỏ: `filedata=b"\xff\xd8\xff..."` (JPEG magic) đủ cho content-type test; size-cap test = `b"x" * (10*1024*1024 + 1)` với content_type jpg. Permission test: tạo user Auditor (KHÔNG repair.write) + user assignee riêng, `frappe.set_user(...)`. **RED-first:** viết 11 test TRƯỚC khi có handler ⇒ đỏ; implement service+api ⇒ xanh. Đối xứng `TestAttachPmChecklistPhoto` (imm08 `test_imm08.py`) / `TestAttachIncidentPhoto` (imm12 `test_imm12.py`). Enum `repair_checklist_photo_attached` seed qua `create_lifecycle_event` (KHÔNG phụ thuộc `reload-doctype` live).

**TestFirmwareTransition — FCR state machine SERVER-controlled (BR-09-18/19/20, Vòng 10):**

| TC | Setup | Action | Expect | Kỹ thuật |
|----|-------|--------|--------|-----|
| **TC-FCR-01** *(happy approve)* | FCR `Pending Approval`; user = Repair Manager (submit=1) | `approve_firmware_cr(name)` | `success=true`, `data.status=='Approved'`; `approved_by==user`, `approved_datetime` set; **đúng 1** ALE `firmware_cr_approved` (from='Pending Approval' to='Approved', root_doctype='Firmware Change Request', root_record=FCR) | Happy + State |
| **TC-FCR-02** *(Super Admin duyệt được)* | FCR `Pending Approval`; user = AssetCore Super Admin | `approve_firmware_cr` | `success=true`, status=Approved (đối xứng root-cause 'đủ quyền vẫn không duyệt được') | State |
| **TC-FCR-03** *(Repair User thiếu quyền — KHÔNG 500/silent)* | FCR `Pending Approval`; user = Repair User (submit=0 trên FCR) | `approve_firmware_cr` | **HTTP-200** `success=false`, `code=FORBIDDEN`, message VN "Bạn không có quyền phê duyệt…"; status GIỮ 'Pending Approval'; **0 ALE** | Decision Table (E-09-10) |
| **TC-FCR-04** *(deploy happy)* | FCR `Approved`; user = Repair User (repair.write) | `deploy_firmware_cr` | status='Applied', `applied_datetime` set; 1 ALE `firmware_deployed` | State |
| **TC-FCR-05** *(rollback happy)* | FCR `Applied`; user = Repair Manager; `rollback_reason='Lỗi treo màn hình'` | `rollback_firmware_cr(name, reason)` | status='Rolled Back'; 1 ALE `firmware_rolled_back`; `rollback_reason` lưu | State |
| **TC-FCR-06** *(rollback thiếu reason)* | FCR `Applied`; reason='' | `rollback_firmware_cr(name, '')` | `code=VALIDATION` "Lý do hoàn tác là bắt buộc"; status GIỮ 'Applied'; 0 ALE | EP (E-09-12) |
| **TC-FCR-07** *(nhảy-cóc)* | FCR `Draft` | `deploy_firmware_cr` (Draft→Applied, ngoài map) | `code=BAD_STATE` "Không thể chuyển… từ 'Draft' sang 'Applied'"; status GIỮ 'Draft'; 0 ALE | EP (E-09-11) |
| **TC-FCR-08** *(lùi trạng thái)* | FCR `Approved` | thử transition về 'Draft' (ngoài map) | `code=BAD_STATE`; status GIỮ 'Approved' | EP (E-09-11) |
| **TC-FCR-09** *(event throw → rollback, KHÔNG đổi status câm)* | FCR `Pending Approval`; monkeypatch `create_lifecycle_event` raise | `approve_firmware_cr` | raise propagate/rollback; sau rollback status GIỮ 'Pending Approval' (KHÔNG commit 'Approved' mà mất event) | Invariant (E-09-14) |
| **TC-FCR-CRUD-GUARD-01** *(chặn CRUD chung)* | FCR `Pending Approval` | `update_firmware_cr(name, status='Approved', change_notes='x')` | status GIỮ 'Pending Approval' (STRIP); `change_notes=='x'` (field tự do vẫn sửa); **0 ALE** approve | Invariant (E-09-13, BR-09-19b) |
| **TC-FCR-CTA-01** *(allowed_transitions lọc — Repair User)* | FCR `Pending Approval`; user = Repair User | `get_firmware_cr(name)` | `allowed_transitions==[]`, `can_approve==0` | Invariant (BR-09-20) |
| **TC-FCR-CTA-02** *(allowed_transitions — Manager)* | FCR `Pending Approval`; user = Repair Manager | `get_firmware_cr(name)` | `allowed_transitions==['Approved']`, `can_approve==1` | Invariant |
| **TC-FCR-CTA-03** *(terminal)* | FCR `Rolled Back` | `get_firmware_cr` | `allowed_transitions==[]` (mọi user) | Invariant |
| **TC-FCR-CTA-04** *(deploy edge — repair.write, không cần approve)* | FCR `Approved`; user = Repair User (repair.write) | `get_firmware_cr` | `allowed_transitions==['Applied']` (cạnh non-approval lọc theo repair.write, KHÔNG cần firmware.approve) | Invariant |

> **Mẹo thực thi (TestFirmwareTransition):** fixture FCR thật (`frappe.get_doc({"doctype":"Firmware Change Request", ...}).insert()`) + `asset_ref` là AC Asset test; teardown `_purge` (prefix asset `_Test FCR%`) + xóa ALE test. Đặt status ban đầu qua `frappe.db.set_value` (né `validate()` khi seed). User theo capability: Repair Manager / Repair User / AssetCore Super Admin — assign role rồi `frappe.set_user`. **KHÔNG hardcode role-name trong assert** — assert theo hành vi (status/ALE/envelope). **RED-first:** 3 loại 403 phân biệt — dispatcher-403 (guest, test riêng POST no-token) vs in-handler FORBIDDEN HTTP-200 (Repair User TC-FCR-03). Enum `firmware_cr_approved`/`firmware_deployed`/`firmware_rolled_back` seed qua `create_lifecycle_event` (KHÔNG phụ thuộc `reload-doctype` live).

**TestSlaClockStop — chi tiết test case (BR-09-10):**

| TC | Setup | Action | Expect | INV |
|----|-------|--------|--------|-----|
| **TC-09-HOLD-01** *(RED-prove)* | WO mở tổng 80h, trong đó 40h ở Pending Parts (`parts_hold_hours=40`); target=72h (Class II Normal) | `complete_repair` (until=open+80h) | `mttr_hours==40.0` ∧ `sla_breached==0` (clock-stop: 80−40=40 < 72). **RED:** dùng `(completion−open)` thô ⇒ mttr=80, breach=1 (SAI) | INV-CM-HOLD-1 |
| **TC-09-HOLD-02** *(no-regression)* | WO không bao giờ qua Pending Parts (`parts_hold_hours=0`, `parts_hold_started=null`), mở 80h | `repair_elapsed_hours(doc, open+80h)` | `== 80.0` (wall-clock cũ nguyên vẹn — đối chứng) | INV-CM-HOLD-4 |
| **TC-09-HOLD-03** *(SoT đồng nhất)* | 1 WO Pending Parts đang hold 40h, target=72, open 80h trước | gọi `_row_is_live_overdue(row, now)` ∧ `check_repair_sla_breach` ∧ `complete_repair` trên cùng dữ liệu | cả 3 phái sinh elapsed=40 ⇒ KHÔNG breach; card==scheduler==stamp (no divergence) | INV-CM-HOLD-6 |
| **TC-09-HOLD-04** *(multi-cycle + biên Δ=0)* | enter→exit (10h) → enter→exit (15h) → enter→exit (Δ=0 cùng thời điểm) | đọc `parts_hold_hours` | `== 25.0` (10+15+0); KHÔNG âm; mỗi khoảng ≥0 | INV-CM-HOLD-3 |
| **TC-09-HOLD-05** *(đóng khi đang hold)* | WO đang Pending Parts (`parts_hold_started` non-null, đã hold 20h), đóng tại completion=open+50h | `complete_repair` | `exit_parts_hold(until=completion)` chốt 20h cuối TRƯỚC → `parts_hold_hours==20`, `parts_hold_started==null`; `mttr_hours==30` (50−20); không bỏ sót khoảng cuối | INV-CM-HOLD-5/2 |
| **TC-09-HOLD-06** *(stamp/reset đối xứng + ALE)* | submit_diagnosis(needs_parts=1) → start_repair | sau mỗi bước assert field + ALE | sau enter: `parts_hold_started` non-null ∧ ALE `parts_hold_started`; sau exit: `parts_hold_started==null` ∧ `parts_hold_hours>0` ∧ ALE `parts_hold_resumed`; `is_sla_breached`/`get_sla_target` BẤT BIẾN (cùng input → cùng output trước/sau patch) | INV-CM-HOLD-2 + bất biến SoT |

> **Mẹo thực thi**: dùng `SimpleNamespace` cho test thuần công thức (`get_sla_target`, `repair_elapsed_hours` — pure, no DB) — chạy ms-level, không cần fixture cleanup. `TestCmSlaBreachLiveSoT` + `TestSlaClockStop` (TC-03/05/06) cần fixture Asset Repair thật (open_datetime/parts_hold backdated) + teardown `_purge` (prefix `_Test CM-SLA%` / `_Test CM-HOLD%`). **RED-prove (BR-09-07 LIVE):** revert `cm_sla_breached` về `_count({sla_breached:1})` + bỏ `_enrich_sla_breach` ⇒ INV-CM-SLA-1/5 FAIL (`0!=1` card, `None!=true` badge); restore ⇒ GREEN. **RED-prove (BR-09-10):** TC-09-HOLD-01 — thay `repair_elapsed_hours` bằng `(completion−open)` thô ⇒ `mttr==80 != 40`, `sla_breached==1 != 0` FAIL; restore SoT ⇒ GREEN.

**TestSearchSparePartsIdentity — khoá nhận dạng gợi ý phụ tùng (CR-73a, BR-09-21/22) 🔴 RED-first, chốt 2026-07-25:**

**Fixture bắt buộc (chính xác — nếu sai, TC-CM-SPARE-01 xanh giả):** 2 bản ghi `IMM Device Model` KHÁC NHAU (vd `_Test Model VENT-A`, `_Test Model VENT-B`), MỖI model có 1 dòng `spare_parts_list` với **`part_name` GIỐNG HỆT** (`'Van PEEP'`) **và `manufacturer_part_no` GIỐNG HỆT** **và `estimated_cost` GIỐNG HỆT**. Ba trường phải trùng cả ba thì `SELECT DISTINCT` hiện tại mới gộp còn 1 dòng — nếu để `manufacturer_part_no` khác nhau, code cũ đã trả 2 dòng và test **không đỏ** (vacuous). Thêm: 1 `AC Spare Part` `is_active=1` khớp `manufacturer_part_no` đó + 1 `AC Spare Part Stock` trỏ nó với `warehouse` là `AC Warehouse` `is_active=1`.

| TC | Setup | Action | Expect | AC |
|----|-------|--------|--------|----|
| **TC-CM-SPARE-01** *(khử nhập nhằng — RED trên code hiện tại)* | 2 model như fixture trên | `search_spare_parts('Van PEEP')` | **ĐÚNG 2 dòng**; `device_model` của 2 dòng **KHÁC NHAU**; `device_model_name` mỗi dòng == `model_name` của model tương ứng | A2 |
| **TC-CM-SPARE-02** *(13 khoá, đủ mặt, đúng kiểu)* | như trên | `search_spare_parts('Van PEEP')` | mỗi row có **đúng 13 khoá** (`set(row) == <13 khoá>`); `device_model`/`device_model_name`/`spare_part` đều `isinstance(str)`; **KHÔNG `None`**, **KHÔNG thiếu khoá** | A1 |
| **TC-CM-SPARE-03** *(10 khoá cũ bất biến)* | 1 phụ tùng đơn giản, 1 model | so sánh 10 khoá cũ với giá trị kỳ vọng cũ (`item_code`, `item_name`, `manufacturer_part_no`, `qty==1`, `uom=='Cái'`, `unit_cost`, `total_cost`, `stock_entry_ref==''`, `notes==''`, `idx==0`) | trùng khớp **từng khoá** (thuần ADDITIVE, 0 regression consumer cũ) | A1 |
| **TC-CM-SPARE-04** *(resolve ưu tiên MPN)* | `AC Spare Part` X khớp `manufacturer_part_no`; `AC Spare Part` Y khớp `part_name` (khác X) | `search_spare_parts(...)` | `spare_part == X.name` (MPN thắng `part_name`) | A4 |
| **TC-CM-SPARE-05** *(fallback + `is_active` + tie-break)* | 0 bản ghi khớp MPN; 2 bản ghi khớp `part_name` `is_active=1` + 1 bản ghi khớp nhưng `is_active=0` | `search_spare_parts(...)` | `spare_part` == `name` **nhỏ nhất theo `order_by name asc`** trong 2 bản ghi active; bản ghi `is_active=0` **KHÔNG BAO GIỜ** được chọn | A4 |
| **TC-CM-SPARE-06** *(0 khớp ⇒ chuỗi rỗng)* | phụ tùng không có `AC Spare Part` nào khớp | `search_spare_parts(...)` | `spare_part == ''` (**KHÔNG `None`**, khoá vẫn có mặt) | A1/A4 |
| **TC-CM-SPARE-07** *(không N+1)* | ≥ 5 dòng thuộc ≥ 2 model, có cả nhánh MPN lẫn fallback | monkeypatch counter lên `frappe.get_all`/`frappe.db.get_value`/`frappe.db.sql` | tổng truy vấn **phụ** (ngoài 1 SQL chính) **≤ 3**; số dòng tăng ⇒ số truy vấn **KHÔNG tăng** | A5 |
| **TC-CM-SPARE-08a** *(gate — thiếu quyền)* | user CHỈ role `Repair User` (**KHÔNG** `AssetCore System User`) ⇒ 0 DocPerm read `IMM Device Model` | `search_spare_parts('Van')` | raise `ServiceError` `code=FORBIDDEN`, `http_status=403`; **KHÔNG** HTTP-500; **KHÔNG** rò dòng nào (không trả `[]` câm — assert bằng exception, không bằng list rỗng) | A6 |
| **TC-CM-SPARE-08b** *(gate — persona thật KHÔNG bị khoá)* | user = `AssetCore System User` + `Repair User` (persona "Kỹ thuật viên") | `search_spare_parts('Van PEEP')` | kết quả **non-empty**; `spare_part` **non-empty** trên fixture có `AC Spare Part` | A6 |
| **TC-CM-SPARE-ALLOC-01** *(A3-a — hết "allocation câm", quyền đầy đủ)* | fixture đủ `AC Spare Part` + `AC Spare Part Stock`; chạy bằng `Administrator` | lấy `spare_part` từ gợi ý → `request_spare_parts(wo, [{spare_part, qty:1}])` | `allocation` **NON-NULL**; bản ghi `IMM Spare Allocation` tồn tại, `allocation_status == 'Requested'` | A3 |
| **TC-CM-SPARE-ALLOC-02** *(A3-b — persona THẬT, chống xanh giả)* | như trên; chạy bằng persona KTV (`AssetCore System User` + `Repair User`) | như trên | `allocation` **NON-NULL**. **Nếu đỏ vì `inventory.write`** ⇒ thực thi ADR-IMM09-SPARE-03 (kèm `test_imm15` vào DoD) **HOẶC** báo ngược [PM]. **CẤM** đổi test sang `Administrator` để né | A3-bis |
| **TC-CM-SPARE-ALLOC-03** *(null hợp lệ)* | phụ tùng có `AC Spare Part` nhưng **không** có `AC Spare Part Stock` | `request_spare_parts(...)` | `success == true`, `allocation is None`, `updated` đúng; **0** `IMM Spare Allocation` mới | BR-09-22 |

**Thực thi 2026-07-25 (BE Bước-4) — TC ↔ test method THẬT:** `assetcore/tests/imm09/test_imm09.py::TestSearchSparePartsIdentity` (TC-01 `test_search_spare_parts_distinguishes_by_device_model` · TC-02 `..._row_has_exact_13_string_keys` · TC-03 `..._legacy_10_keys_unchanged` + `..._short_query_returns_empty` · fallback-nhãn `..._device_model_name_fallback_to_id` · TC-04 `..._resolves_spare_part_by_manufacturer_part_no` · TC-05 `..._resolves_spare_part_fallback_by_part_name` · TC-06 `..._unmatched_resolves_to_empty_string` · TC-07 `..._no_n_plus_one`) · `::TestRequestSparePartsAllocation` (ALLOC-01 `test_request_spare_parts_creates_allocation_with_resolved_key` · **ALLOC-02** `..._creates_allocation_as_technician_persona` · ALLOC-03 `..._allocation_null_when_no_stock`) · `assetcore/tests/integration/test_rowscope_docperm_gate.py::TestSearchSparePartsRoleGate` (08a `test_search_spare_parts_requires_read_on_device_model` · 08b `..._technician_persona_still_gets_results`) · `assetcore/tests/guards/test_mobile_oas.py::TestMobileSearchSparePartItemIdentity` (6 TC `cr73a_a..f`, gồm **parity AST BE↔OAS** và **chống cite-rot**). ⚠️ **ALLOC-02 ĐỎ trước khi thực thi ADR-IMM09-SPARE-03** (dù E2 đã sửa) ⇒ K4 đã được thực thi trong vòng, `test_imm15` vào DoD.

**Bẫy hạ-tầng test đã gặp (ghi lại để vòng sau không mất giờ):** (1) token fixture PHẢI **rời nhau** — đặt tên phụ tùng chứa token của TC khác (`NPLUS1<TOKEN>`) làm fixture TC này lọt vào `LIKE %TOKEN%` của TC kia ⇒ TC-01 "đúng 2 dòng" vỡ **theo thứ tự chạy**; (2) teardown phải xoá `AC Spare Part Stock` **TRƯỚC** `AC Spare Part` (Link) — sai thứ tự thì `LinkExistsError` bị nuốt ⇒ bản ghi rò sang lần chạy sau và **thắng** quy tắc `order_by name asc`; (3) fixture `IMM Device Model` phải idempotent (unique-guard model_name+manufacturer) vì `setUpClass` đổ giữa chừng sẽ không chạy `tearDownClass`; (4) 1 thiết bị chỉ được có 1 phiếu sửa chữa đang mở ⇒ ca persona cần **asset riêng**.

**Mutation-check bắt buộc (chống vacuous-green, A9):** hoàn nguyên **đúng 1 dòng** enrich (bỏ khoá `spare_part` khỏi row-dict, **hoặc** trả lại `SELECT DISTINCT`) ⇒ TC-CM-SPARE-01/02 (hoặc 04–06) phải **ĐỎ**; khôi phục ⇒ XANH. Ghi kết quả mutation vào báo cáo vòng.

**Mẹo thực thi:** teardown purge theo prefix `_Test Model VENT-%` (models) + `_Test SP-%` (`AC Spare Part`/`AC Spare Part Stock`) + WO test; dùng `frappe.set_user` cho 2 ca gate rồi `frappe.set_user("Administrator")` trong `finally`. User test tạo bằng helper sẵn có (`_ensure_user` kiểu `test_rowscope_docperm_gate.py:63-85`) — **KHÔNG** gán role bằng cách sửa Role Profile (sẽ ảnh hưởng user thật).

**Suite phải XANH trong vòng (A9):** `bench --site miyano run-tests --module assetcore.tests.imm09.test_imm09` · `…test_mobile_oas` · `…test_mobile_docset` · `…test_rowscope_docperm_gate` · `npm run test -- CMCreateView` · `npx vue-tsc --noEmit`. Nếu thực thi ADR-IMM09-SPARE-03 ⇒ **thêm** `…test_imm15`. Nếu thực thi K3 (`"search_"` vào `_ENTRYPOINT_PREFIXES`) ⇒ **thêm** `…test_rowscope_scope_guard`.

## III.3. Integration — DocType lifecycle

**File**: `assetcore/tests/imm09/test_imm09.py` (hợp nhất — xem §III.2). Cover hook `validate / before_insert / on_submit / on_update_after_submit`.

| Test | Setup | Action | Assert | Kỹ thuật | Status |
|---|---|---|---|---|---|
| `test_on_insert_sets_asset_under_repair` | Asset Active | `doc.insert()` | `Asset.status == "Under Repair"` | State Transition | ⬜ Planned |
| `test_on_insert_creates_lifecycle_event` | Asset Active | `doc.insert()` | ALE `event_type == "repair_opened"` | EP | ⬜ Planned |
| `test_before_submit_validates_checklist` | WO In Repair, 1 Fail row | `close_work_order` | `frappe.ValidationError` (BR-09-04) | EP | ⬜ Planned |
| `test_on_complete_sets_asset_active` | WO Pending Inspection, asset Under Repair, all Pass | `confirm_inspection` | `Asset.status == "Active"`, `mttr_hours > 0`, WO=Completed | State Transition | ⬜ Planned |
| `test_cannot_repair_sets_oos` | WO with reason | `_mark_cannot_repair` | `Asset.status == "Out of Service"` | State Transition | ⬜ Planned |
| `test_complete_repair_keeps_oos_hold` (Scenario 9.10) | WO Pending Inspection; asset đã `Out of Service` do hold khác (calib-fail/CAPA) | `confirm_inspection` | `Asset.status == "Out of Service"` (KHÔNG ép Active); WO=Completed; mttr/sla set; ALE `repair_completed` from=to=OoS + note hold | State Transition (BR-09-09 nhánh B) | ⬜ Planned |
| `test_complete_repair_decommissioned_no_raise` (Scenario 9.11) | WO Pending Inspection; asset đã `Decommissioned` (terminal) | `confirm_inspection` | KHÔNG raise `InvalidAssetTransition`; WO=Completed (docstatus=1, đóng được); asset giữ `Decommissioned`; ALE `repair_completed` from=to + note đã thanh lý | State Transition (BR-09-09 nhánh C) | ⬜ Planned |
| `test_close_while_pending_parts_clamps_hold` (Scenario 9.12) | WO đang Pending Parts, đã hold 40h, đóng tại completion=open+80h (cannot_repair=0 → qua Pending Inspection→Completed) | `confirm_inspection` (→ `complete_repair`) | `parts_hold_hours` gồm cả khoảng hold cuối tới completion; `mttr_hours==40` (80−40); `sla_breached==0` (target 72); `parts_hold_started==null`; ALE `parts_hold_resumed` + `repair_completed` | State Transition (BR-09-10, INV-CM-HOLD-5) | ⬜ Planned |

**TestSelfInspectionSoD — chặn tự-nghiệm-thu (CR-41, BR-09-SOD, ADR-IMM09-SOD-INSPECT):** người `confirm_inspection` phải khác người `close_work_order`. Fixture cần **2 user** cùng site: `user_A` (có `repair.create` + `repair.submit`), `user_B` (≠A, có `repair.submit`). Mỗi TC: `frappe.set_user(user_A)` → dựng WO In Repair → `close_work_order(... , checklist all Pass)` (A = closer, ghi ALE `repair_pending_inspection` actor=A). `tearDownClass` purge WO + user tạm.

| Test (TC) | Setup | Action | Assert | AC |
|---|---|---|---|---|
| `test_self_inspection_blocked` (TC-CM-SOD-01) | A đóng WO → status `Pending Inspection`, docstatus=0 | `set_user(A)` → `confirm_inspection(name)` | Error envelope HTTP-200 `{success:false, code:'FORBIDDEN', http_status:403, message:'Người nghiệm thu phải khác người đóng phiếu.'}`; WO **GIỮ** `status=='Pending Inspection'`, `docstatus==0`; asset **KHÔNG** reactivate (giữ Under Repair) | AC1 |
| `test_other_user_confirms_ok` (TC-CM-SOD-02) | A đóng WO (Pending Inspection) | `set_user(B)` (B≠A, `repair.submit`) → `confirm_inspection(name)` | `success==true`; `status=='Completed'`; `docstatus==1`; response 4-key `{name,status,mttr_hours,sla_breached}` bất biến (CR-13a); asset Under Repair→Active (BR-09-09 nhánh A) | AC2 |
| `test_closer_read_from_lifecycle_event` (TC-CM-SOD-03) | A đóng WO | assert trực tiếp: ALE mới nhất (`event_type='repair_pending_inspection'`, `root_doctype='Asset Repair'`, `root_record=name`).`actor == A` | 0 field DocType mới trên Asset Repair (introspect meta — KHÔNG có `closed_by`); test chạy KHÔNG cần `bench migrate` | AC3 |
| `test_order_bad_state_before_sod` (TC-CM-SOD-04) | WO ở `In Repair` (KHÔNG Pending Inspection); A là closer-tương-lai | `set_user(A)` → `confirm_inspection(name)` | Error `IMM09_BAD_STATE` (NOT `FORBIDDEN`/SoD) — chứng minh thứ tự `NOT_FOUND→BAD_STATE→self-check` giữ nguyên (INV-CM-SOD-1); + case NOT_FOUND (name rác) → `IMM09_NOT_FOUND` | AC4 |
| `test_unknown_closer_fail_open` (TC-CM-SOD-05) | WO ở `Pending Inspection` nhưng **XOÁ/thiếu** ALE `repair_pending_inspection` (mô phỏng legacy/event swallow) | `set_user(A)` → `confirm_inspection(name)` | KHÔNG raise/crash; submit THÀNH CÔNG (`status=='Completed'`, docstatus=1) — fail-open (INV-CM-SOD-2); (optional) capture `frappe.logger().debug` closer-unknown | AC5 |

> **RED-prove (BR-09-SOD):** bỏ SoD-check trong `confirm_inspection` ⇒ TC-CM-SOD-01 FAIL (A tự nghiệm thu submit được, KHÔNG Error). Đặt SoD-check TRƯỚC BAD_STATE ⇒ TC-CM-SOD-04 FAIL (WO In Repair trả FORBIDDEN thay vì BAD_STATE). Fail-closed thay fail-open ⇒ TC-CM-SOD-05 FAIL (legacy deadlock). GREEN khi đúng cả 3.
>
> **DoD (AC7):** `bench --site miyano run-tests --module assetcore.tests.imm09.test_imm09` XANH THẬT (Ran N OK). **KHÔNG curl** — gunicorn `--preload` stale tới khi USER reload (chạm `services/imm09.py` + `utils/messages.py`). Đây là **application-code** ⇒ bàn giao [BE] implement + verify.

> Fixture trong `setUpClass` phải có `tearDownClass` purge — xem skill `assetcore-test` LL-TEST-17.
>
> **RED-prove (BR-09-10 / INV-CM-HOLD-5):** bỏ `exit_parts_hold(until=completion)` trong `complete_repair` (không chốt khoảng hold cuối) ⇒ Scenario 9.12 FAIL (`parts_hold_hours` thiếu khoảng cuối → mttr/breach sai). Restore ⇒ GREEN.
>
> **RED-prove (BR-09-09 / INV-09-RESTORE-1):** revert gate (đưa `complete_repair` về `transition_asset_status(to_status=ACTIVE)` không-điều-kiện) ⇒ Scenario 9.10 FAIL (`Out of Service` bị lật → `Active`) VÀ Scenario 9.11 FAIL (`InvalidAssetTransition` raise → `on_submit` vỡ, WO un-closeable). Restore gate ⇒ cả hai GREEN. Grep-guard: `transition_asset_status(..., to_status=AssetStatus.ACTIVE)` trong `complete_repair` chỉ tồn tại bên trong nhánh `if prev_status == AssetStatus.UNDER_REPAIR`.

## III.4. Integration — Workflow transitions

**File**: `assetcore/tests/imm09/test_imm09.py`. Workflow `IMM-09 Repair Workflow` (`workflow/imm_09_repair_workflow.json`) — **9 state, 15 transition** (verified `len(...['transitions']) == 15`). Roles thực trong JSON: `System Manager`, `Repair User`. **Bắt buộc** cover 100% transition.

| # | Action | From → To | Role required | Test pass | Test fail (wrong role / gate) |
|---|---|---|---|---|---|
| 1 | Phân công KTV | Open → Assigned | System Manager | ⬜ | ⬜ |
| 2 | Hủy phiếu | Open → Cancelled | System Manager | ⬜ | ⬜ |
| 3 | Bắt đầu chẩn đoán | Assigned → Diagnosing | Repair User | ⬜ | ⬜ |
| 4 | Yêu cầu linh kiện | Diagnosing → Pending Parts | Repair User | ⬜ *(BR-09-10: stamp `parts_hold_started`)* | ⬜ |
| 5 | Bắt đầu sửa chữa | Diagnosing → In Repair | Repair User | ⬜ | ⬜ |
| 6 | Linh kiện đã nhận - bắt đầu sửa | Pending Parts → In Repair | Repair User | ⬜ *(BR-09-10: chốt hold → `parts_hold_hours`, reset `parts_hold_started`)* | ⬜ |
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

**File**: `assetcore/tests/imm09/test_imm09.py`. Cover: happy path + envelope `success=true`; invalid params; FORBIDDEN; pagination; idempotent retry.

| Test | Endpoint (`api/imm09.py`) | Verify | Kỹ thuật | Status |
|---|---|---|---|---|
| `test_list_default_pagination` | `list_repair_work_orders` | page=1, page_size=20, total ≥ 0 | Use Case | ⬜ Planned |
| `test_list_filter_status_open` | `list_repair_work_orders?filters={"status":"Open"}` | Mọi row status == Open | EP | ⬜ Planned |
| **TC-CM-SEARCH-01** `test_search_matches_name_asset_code_name` | `list_repair_work_orders?search=X` | mọi row có `name` HOẶC `asset_code` HOẶC `asset_name` chứa "X" (case-insensitive); phiếu KHÔNG khớp bị loại | EP | ⬜ Planned |
| **TC-CM-SEARCH-02** `test_search_count_equals_rows_paginated` | `?search=X&page_size=2` (dataset > 2 khớp) | `pagination.total` == tổng phiếu khớp toàn tập; gộp mọi trang == total; count==rows | Invariant + BVA | ⬜ Planned |
| **TC-CM-SEARCH-03** `test_search_empty_byte_identical_baseline` | `search=""` vs absent vs baseline | data + pagination BYTE-IDENTICAL list không-search (regression=0) | Invariant | ⬜ Planned |
| **TC-CM-SEARCH-04** `test_search_wildcard_escaped_literal` | `search='%'` / `'_'` / `'%%%%%'` | KHÔNG match toàn bảng (literal `%`/`_`); no-throw, no-DoS | Security (escape) | ⬜ Planned |
| **TC-CM-SEARCH-05** `test_search_and_vendor_mine_no_leak` | Vendor + `mine=1` KTV, `search` khớp phiếu ngoài scope | phiếu ngoài scope KHÔNG trả dù khớp (AND vendor/`assigned_to`); count==rows | Security (scope) | ⬜ Planned |
| **TC-CM-SEARCH-06** `test_search_and_status_filter` | `?search=X&filters={"status":"Open"}` | chỉ phiếu Open ∧ khớp search (AND-combine) | EP | ⬜ Planned |
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

### III.6-bis. Contract guard — OpenAPI mobile (CR-65, `repair_checklist[]` typed)

**File**: `assetcore/tests/guards/test_mobile_oas.py::TestMobileRepairChecklistItemTyped` — guard **tầng hợp đồng** (thuần-shape: đọc yaml + DocType json, **không** đụng DB/`.py` production). Xem spec: [`05_API_Specification.md` §3.2 + ADR-IMM09-CHECKLIST-WIRE-01](./05_API_Specification.md).

| TC | Verify | Kỹ thuật | Status |
|---|---|---|---|
| `cr65_a_detail_repair_checklist_array_ref` | `RepairWorkOrderDetail.repair_checklist` = `array` + `items.$ref` → `RepairChecklistItem` (không dangling) | Contract shape | ✅ Live |
| `cr65_b_item_open_object_mirror_pm_precedent` | `RepairChecklistItem` `object` + `additionalProperties:true`; precedent `PmChecklistResultItem` cũng mở; không khai `required` | Mirror-precedent | ✅ Live |
| `cr65_c_seven_domain_fields_grounded_no_invention` | Khai ĐỦ 7 field domain đọc TRỰC TIẾP `repair_checklist.json` + `idx`/`name`; **0 field bịa** | Grounding chống-bịa | ✅ Live |
| `cr65_d_idx_integer_join_parity_with_attach_photo` | `idx:integer` **cùng kiểu** `checklist_item_idx` ở CẢ request lẫn response `attachRepairChecklistPhoto` (3-way); `idx` không nullable | Invariant (khoá join) | ✅ Live |
| `cr65_e_result_no_hard_enum_seed_empty_allowed` | `result` không `enum` cứng (nếu có phải chứa `""`); grounding: options doctype `[Pass,Fail,N/A]` không mở đầu dòng trống ⇒ seed `""` sẽ bị enum cấm | EP + RED-prove | ✅ Live |
| `cr65_f_photo_single_attach_string_not_array` | `photo` = `string` nullable (KHÔNG array); grounding fieldtype `Attach` @doctype; BR-09-16 `MAX_REPAIR_CHECKLIST_PHOTOS=1` | Contract shape | ✅ Live |
| `cr65_g_zero_footprint_detail_open_envelope_closed` | Payload GIỮ `additionalProperties:true` + `required:[name]`; envelope GIỮ CLOSED `{success,data}` + 0 discriminator; `RepairChecklistItem` được `$ref` ≥1 (0 orphan) | Zero-footprint | ✅ Live |

> **RED-before (đo được):** xoá property `repair_checklist` hoặc schema `RepairChecklistItem` khỏi yaml ⇒ `cr65_a`/`cr65_b` FAIL. Khai `result.enum: [Pass, Fail, N/A]` ⇒ `cr65_e` FAIL (đúng lớp lỗi sẽ reject 100% phiếu CM mới seed `result=""`).
>
> **DoD:** `bench --site miyano run-tests --module assetcore.tests.guards.test_mobile_oas` → **Ran 905 tests … OK** và `--module assetcore.tests.guards.test_mobile_docset` → **Ran 9 tests … OK** (2026-07-25). Đổi số test PHẢI sync 4 counter: `_EXPECTED_TEST_COUNT` (+2 assert literal trong `test_mob_oas_cancelcal_j…`/`test_mob_oas_receivecert_j…`) @`test_mobile_oas.py`, và `_GUARD_SUITE_EXPECTED["test_mobile_oas.py"]` / `_GUARD_SUITE_SUM` / `_MOBILE_OAS_TOTAL` + Δ transition-baseline @`test_mobile_docset.py`.

### III.6-ter. Contract guard — OpenAPI mobile (CR-73a, `SearchSparePartItem` 10→13 prop) 🔴 Planned (Bước-4)

**File**: `assetcore/tests/guards/test_mobile_oas.py::TestMobileSearchSparePartItemIdentity` — guard **thuần-shape** (đọc yaml, KHÔNG đụng DB/`.py`). Spec: [`05_API_Specification.md §3.13-bis(8)`](./05_API_Specification.md).

| TC (gợi ý) | Verify |
|---|---|
| `cr73a_a_three_new_properties_present` | `SearchSparePartItem.properties` chứa `device_model`, `device_model_name`, `spare_part`, cả 3 `type: string` |
| `cr73a_b_required_covers_all_thirteen` | `required` == đúng 13 khoá (thiếu 1 ⇒ client codegen rớt field vì `additionalProperties:false`) |
| `cr73a_c_no_nullable_no_extra_type` | 3 property mới **KHÔNG** `nullable: true`, KHÔNG `oneOf`/`type: [string, "null"]` (hợp đồng "vắng = `\"\"`") |
| `cr73a_d_schema_stays_closed` | `additionalProperties: false` GIỮ NGUYÊN; `SearchSparePartsEnvelope` GIỮ `required[success,data]` + `data` = array `$ref` |
| `cr73a_e_zero_new_path_or_operation` | Tổng path/opId GIỮ **105**; `components.schemas` **+0** schema mới |
| `cr73a_f_cite_refreshed_not_rotted` | Mô tả schema/property KHÔNG còn chuỗi cite cũ đã rot (`imm09.py:1237-1246` / `:1223-1248`) |

> **RED-before (đo được):** bỏ 1 trong 3 property khỏi yaml ⇒ `cr73a_a` FAIL; khai property nhưng quên thêm vào `required` ⇒ `cr73a_b` FAIL.
>
> **Counters — cộng theo DELTA, đọc tại chỗ:** thêm **N** TC ⇒ `_EXPECTED_TEST_COUNT` @`test_mobile_oas.py` **+N**, và `_GUARD_SUITE_EXPECTED["test_mobile_oas.py"]` / `_GUARD_SUITE_SUM` / `_MOBILE_OAS_TOTAL` @`test_mobile_docset.py` **+N**. Giá trị lúc chốt spec: `911` / `1054` / `1080` — **nếu file đã khác thì tin file** (CR khác có thể landed xen giữa; chấm theo delta, KHÔNG theo số tuyệt đối).

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
bench --site assetcore.local run-tests --app assetcore --module assetcore.tests.imm09.test_imm09
# Coverage
coverage run -m unittest assetcore.tests.imm09.test_imm09 && coverage report
# Workflow smoke
bench --site assetcore.local run-tests --module assetcore.tests.guards.test_workflows
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
| BR-09-21 | Gợi ý phụ tùng mang khoá nhận dạng (13 khoá; khử nhập nhằng; resolve deterministic; ≤3 query phụ; role-gate) | `TestSearchSparePartsIdentity` — TC-CM-SPARE-01..08b | EP + Decision Table + Invariant (đếm query) + Pairwise persona | 6 / 3 🔴 RED-first (CR-73a) |
| BR-09-22 | Gate-2 → IMM-15: `allocation:null` không che lỗi | `TestSearchSparePartsIdentity` — TC-CM-SPARE-ALLOC-01..03 | State + Invariant (persona pair) | 2 / 1 🔴 RED-first (CR-73a) |
| BR-09-23 | **Cổng ảnh bằng chứng NĐ98 (Class C/D) khi đóng/nghiệm thu phiếu CM** — 1 predicate SSoT cho enforcement + advertise + read; in-envelope HTTP-200; không ghi nửa chừng; miễn trừ `cannot_repair=1`; `""` không phải nguy cơ cao | `TestCmEvidencePhotoGate` — TC-CM-EVID-01..12 (`test_imm09.py`) + `TestMobileRepairEvidencePhotoContract` cr84_a..i (`test_mobile_oas.py`, ✅ XANH Bước-2) | Decision Table + EP (enum risk) + Invariant (parity predicate) + State (không ghi nửa chừng) | 12 / 3 🔴 RED-first (AC-CR-84) |

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
| UAT-IMM-09-13 | Repair User → IMM Department Head | WO Class II Normal (target 72h), mở 80h trong đó 40h chờ phụ tùng hết kho | BR-09-10 | BVA + State Transition | Khi ở Pending Parts: detail hiện badge "Chờ phụ tùng — SLA tạm dừng" (amber), progress bar xám, KHÔNG báo vi phạm. Sau Complete: MTTR=40h, **KHÔNG** `sla_breached`. Đối chứng WO không qua Pending Parts (mở 80h) → MTTR=80h, breach=1 |

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

## VIII. CR-74 — Read-gate CHI TIẾT (getRepairWorkOrder) · bộ TC bắt buộc (2026-07-25)

> Spec: [`05_API_Specification.md` §12](./05_API_Specification.md) · SSoT: [ADR-IMM00-LIST-SCOPE §9](../imm-00/ADR-IMM00-LIST-SCOPE.md).
> **Suite:** `bench --site miyano run-tests --app assetcore --module assetcore.tests.imm09.test_imm09` (+ `test_rowscope_docperm_gate` · `test_rowscope_invariant` · `test_rowscope_scope_guard`). **DoD = suite XANH, KHÔNG curl** (`.py` prod dirty dưới gunicorn `--preload` ⇒ BLOCKED-RELOAD).

### VIII.1 Fixture tối thiểu (dựng 1 lần, dùng chung 6 TC)

| Ký hiệu | Là gì | Ràng buộc |
|---|---|---|
| `USER_NOPERM` | user **đăng nhập được** nhưng **0 DocPerm read** trên `Asset Repair` | vd persona `PM User` / `Calibration User` (0 DocPerm read trên `Asset Repair` — bảng ADR §8.5). **KHÔNG** dùng Guest (Guest → dispatcher-403/401, sai loại lỗi) |
| `USER_OWNER` | persona `Repair User` — `assigned_to` == chính mình | phải có DocPerm read |
| `USER_OTHER` | persona `Repair User` khác — **không** được giao phiếu đang test | phải có DocPerm read (để phân biệt trục ROW với trục ROLE) |
| `USER_SENIOR` | `Repair Manager` hoặc `AssetCore Auditor` | chứng minh 0 regress |
| `REC_OWNED` | 1 bản ghi `Asset Repair` có `assigned_to` = `USER_OWNER` | |
| `REC_FOREIGN` | 1 bản ghi `Asset Repair` có `assigned_to` = `USER_OWNER`, dùng khi đăng nhập `USER_OTHER` | |
| `NAME_GHOST` | chuỗi PK **không tồn tại** (vd `"AC-REPAIR-9999-99999"`) | dùng cho cặp TC existence-oracle |

> 🔴 **BẮT BUỘC `frappe.set_user(...)` cho MỌI TC** + `frappe.set_user("Administrator")` trong `tearDown`. `frappe/permissions.py:107-109` trả `True` ngay cho Administrator ⇒ chạy bằng Administrator = **xanh giả** (đúng bài học INV-ROWSCOPE-4/6).

### VIII.2 Bộ TC

| TC | User | Input | Kỳ vọng (assert) | INV |
|---|---|---|---|---|
| `TC-CM-DETAILGATE-01` | `USER_NOPERM` | `REC_OWNED` | `env["success"] is False` · `env["code"] == "FORBIDDEN"` · `env["http_status"] == 403` · **KHÔNG raise** · `set(env) & {"asset_ref", "repair_summary", "mttr_hours", "root_cause_category", "asset_info"} == set()` | INV-DETAIL-1 |
| `TC-CM-DETAILGATE-02` | `USER_OTHER` | `REC_FOREIGN` | `code == "FORBIDDEN"` · `http_status == 403` | INV-DETAIL-2 |
| `TC-CM-DETAILGATE-03` | `USER_SENIOR` | `REC_OWNED` | `env["success"] is True` · payload **byte-identical** snapshot baseline (so khoá + giá trị) | INV-DETAIL-4 |
| `TC-CM-DETAILGATE-04` | `USER_NOPERM` | `NAME_GHOST` | envelope **giống hệt** `TC-CM-DETAILGATE-01` (cùng `code` + `http_status`) ⇒ 0 existence-oracle | INV-DETAIL-5 |
| `TC-CM-DETAILGATE-05` | `USER_OWNER` | `NAME_GHOST` | `code == "NOT_FOUND"` · `http_status == 404` — **GIỮ NGUYÊN** | INV-DETAIL-6 |
| `TC-CM-DETAILGATE-06` | `Vendor Engineer` ngoài scope | `REC_OWNED` | `code == "FORBIDDEN"` · **KHÔNG** 500 · **KHÔNG** traceback ⇒ chứng minh lớp `assert_vendor_can_access` vẫn sống | INV-DETAIL-7 |

### VIII.3 Chống vacuous (BẮT BUỘC ghi bằng chứng vào báo cáo vòng)

1. **Mutation gate:** gỡ `assert_doctype_read_permission` khỏi `services/imm09.py::get_work_order` ⇒ `TC-CM-DETAILGATE-01` và `TC-CM-DETAILGATE-04` PHẢI **ĐỎ**. Hoàn nguyên ⇒ xanh.
2. **Mutation guard tĩnh:** cùng thao tác trên ⇒ `test_rowscope_scope_guard::TestRowScopeStaticGuard` **G5** PHẢI **ĐỎ**.
3. **Anti-false-green:** TC-01 phải assert **cả 3** (`success`/`code`/`http_status`) — chỉ assert `success is False` sẽ **không** phân biệt 403 với 404/422.
4. **Anti-leak:** TC-01/02 assert **tập khoá** của envelope, KHÔNG chỉ `"asset_ref" not in env` (khoá lồng trong `data` vẫn rò nếu quên).

### VIII.4 `TC-CM-DETAILGATE-07` — BẢNG CHÂN TRỊ 2×2 (đóng P0 read-vs-write, INV-DETAIL-3)

TC **quan trọng nhất** của CR-74. Với **CÙNG** doctype `Asset Repair`, chạy đủ **4 tổ hợp** và assert **3 đường kết luận GIỐNG NHAU**:

| # | Persona | Phiếu | `list_work_orders` | `get_repair_work_order` | `attach_repair_checklist_photo` |
|---|---|---|---|---|---|
| 1 | `USER_OWNER` | `REC_OWNED` | **CÓ** trong rows | **200 success** | **thành công** |
| 2 | `USER_OWNER` | `REC_OTHER` (của `USER_OTHER`) | **KHÔNG** trong rows | **403** | **403** |
| 3 | `USER_OTHER` | `REC_OTHER` | **CÓ** trong rows | **200 success** | **thành công** |
| 4 | `USER_OTHER` | `REC_OWNED` | **KHÔNG** trong rows | **403** | **403** |

Assert dạng **bảng** (KHÔNG 3 TC rời): với mỗi ô, quy về boolean `allowed` rồi
`self.assertEqual(allowed_list, allowed_detail)` **và** `self.assertEqual(allowed_list, allowed_attach)`
kèm message nêu rõ tổ hợp lệch. **0/4 tổ hợp được phép lệch** ⇒ hết trạng thái "đọc được nhưng không đính được ảnh".

> Ràng buộc fixture: 2 phiếu ở trạng thái **cho phép đính ảnh** (nếu trạng thái chặn thì `attach` trả `VALIDATION`/`BAD_STATE`, **không phải** 403 ⇒ bảng mất ý nghĩa). Kiểm tra `_REPAIR_VALID_TRANSITIONS` + gate `_assert_can_attach_repair_photo` (`services/imm09.py:1419-1429`) trước khi chốt fixture.


---

## IX. AC-CR-78 — `spare_parts_used[]` typed + trạng thái phiếu xuất kho · bộ TC bắt buộc (2026-07-27)

> **SSoT hợp đồng:** [`05_API_Specification.md §13`](05_API_Specification.md) ·
> code-shape [`04_Backend_Design.md §3.8`](04_Backend_Design.md) · FE [`06 §SparePartsStockEntry`](06_Frontend_Design.md).
> **Mục tiêu đo được của vòng:** **INV-PARTS-1** — badge hiển thị ⟺ validator BR-09-02.

### IX.1 Fixture tối thiểu (dựng 1 lần, dùng chung)

| Ký hiệu | Là gì | Ràng buộc |
|---|---|---|
| `SM_REAL` | 1 bản ghi **`AC Stock Movement`** THẬT | `frappe.db.exists("AC Stock Movement", SM_REAL)` là `True`. **KHÔNG** dùng ERPNext `Stock Entry` (sai DocType) |
| `SM_GHOST` | chuỗi PK **không tồn tại** (vd `"SM-9999-99999"`) | dùng cho nhánh `NOT_FOUND` |
| `WO_MIX` | `Asset Repair` **docstatus=0** với **3 dòng** `spare_parts_used`: idx1 `stock_entry_ref=SM_REAL` · idx2 `stock_entry_ref=""` · idx3 `stock_entry_ref=SM_GHOST` | 9 khoá domain điền đủ (`item_code`/`item_name`/`qty`/`uom`/`unit_cost` là `reqd:1`) |
| `WO_EMPTY` | `Asset Repair` **0 dòng** phụ tùng | cho INV-PARTS-3 + nhánh 0-query |
| `WO_ALL_OK` | `Asset Repair` mọi dòng ref = `SM_REAL` | cho chiều ⟸ của INV-PARTS-1 |
| `USER_OWNER` / `USER_NOPERM` | tái dùng §VIII.1 | cho TC-08 (403 + enrich không chạy) |

> 🔴 `tearDownClass` **phải** dọn `AC Stock Movement` + `Asset Repair` đã tạo. **Mọi `bench run-tests` đặt
> `timeout` tool ≥ 600000ms** — kill giữa chừng ⇒ teardown không chạy ⇒ nhiễm DB ⇒ **suite đỏ giả**.

### IX.2 Bộ TC BE — `test_imm09.py::TestSparePartsStockEntryStatus` (**9 TC**, 221 → **≥230**)

| TC | Input | Kỳ vọng (assert) | INV |
|---|---|---|---|
| `TC-CM-PARTS-01` | `get_work_order(WO_EMPTY)` | `"spare_parts_used" in data` · `data["spare_parts_used"] == []` (**KHÔNG** `None`, **KHÔNG** thiếu khoá) · `data["parts_pending_stock_entry"] == 0` | INV-PARTS-3 |
| `TC-CM-PARTS-02` | `get_work_order(WO_MIX)` | 3 dòng có `stock_entry_status` lần lượt `OK`/`MISSING`/`NOT_FOUND` · `stock_entry_ok` `1`/`0`/`0` · **mỗi giá trị `isinstance(v, int) and not isinstance(v, bool)`** (quirk CR-01) · `parts_pending_stock_entry == 2` | INV-PARTS-2 |
| `TC-CM-PARTS-03` | `WO_MIX` | `[r["idx"] for r in rows] == sorted(...)` **tăng dần** | A1 |
| `TC-CM-PARTS-04` | `WO_MIX` | mỗi dòng chứa **đủ 9 khoá domain** (`item_code`, `item_name`, `manufacturer_part_no`, `qty`, `uom`, `unit_cost`, `total_cost`, `stock_entry_ref`, `notes`) và **giá trị KHỚP** row đọc thẳng DB | A1 |
| `TC-CM-PARTS-05` | `WO_ALL_OK` | `parts_pending_stock_entry == 0` **và** `validate_spare_parts_stock_entries(doc)` **KHÔNG raise** | **INV-PARTS-1 (⟸)** |
| `TC-CM-PARTS-06` | `WO_MIX` + biến thể chỉ-`MISSING` + biến thể chỉ-`NOT_FOUND` | `parts_pending_stock_entry > 0` **và** `validate_spare_parts_stock_entries(doc)` **raise** — kiểm **cả 2 nhánh** (`MSG.IMM09_SPARE_NO_STOCK_ENTRY` · `MSG.IMM09_STOCK_ENTRY_NOT_FOUND`), mã lỗi + thứ tự raise **GIỮ NGUYÊN** | **INV-PARTS-1 (⟹)** |
| `TC-CM-PARTS-07` | đếm query | wrap `frappe.get_all` (mirror `test_imm00_approvals_inbox.py:488-500` wrap `frappe.db.sql`), đếm call có `doctype == "AC Stock Movement"`: `WO_EMPTY` ⇒ **0** · `WO_MIX` ⇒ **1** · phiếu 10 dòng ⇒ **1** (KHÔNG tăng theo N) | INV-PARTS-4 |
| `TC-CM-PARTS-08` | no-regress + gate | (a) `set(baseline_keys) ⊆ set(data)` (chỉ ADDITIVE) · (b) `allowed_transitions` / `risk_classification` / `is_sla_breached` / `asset_info` **giữ nguyên giá trị** · (c) `USER_NOPERM` ⇒ `code=="FORBIDDEN"` · `http_status==403` trên **HTTP-200** **và** `"spare_parts_used" not in env` · `"parts_pending_stock_entry" not in env` | INV-PARTS-5 / A5 |
| `TC-CM-PARTS-09` | phiếu **25 dòng**, **tất cả** ref = 25 `AC Stock Movement` THẬT khác nhau | **cả 25** dòng `stock_entry_status == "OK"` · `parts_pending_stock_entry == 0` — chống bẫy `limit_page_length` mặc định 20 của `get_list` (dòng 21+ sẽ bị gán nhầm `NOT_FOUND` = **badge đỏ giả**) | INV-PARTS-6 |

> ⚠️ `TC-CM-PARTS-08(c)` **BẮT BUỘC `frappe.set_user(USER_NOPERM)`** — Administrator được
> `frappe/permissions.py:107-109` trả `True` ngay ⇒ chạy bằng Administrator là **xanh giả**.

### IX.3 Guard hợp đồng OAS — `test_mobile_oas.py::TestMobileRepairSparePartsContract` **8 TC** `cr78_a..h`

Chi tiết từng TC: [`05_API_Specification.md §13.7`](05_API_Specification.md). Điểm dễ sai:

- `cr78_b` đọc **`field_order` THẬT** của `spare_parts_used.json` — không hardcode 9 tên trong test.
- `cr78_g` **import THẬT** `assetcore.services.imm09._STOCK_ENTRY_STATUS` (mirror `cr77_i`; tên ĐÃ LAND — xem `04 §3.8.2`),
  không so với literal chép tay.
- `cr78_h` quét **`components.schemas`** — `cr74_g` chỉ quét `description` của **operation** nên
  **không** chạm tới schema mới (đúng bẫy AC-CR-77 đã gặp).

### IX.4 Test FE (CÙNG VÒNG — A8)

`frontend/src/views/cm/CMWorkOrderDetailView.sparePartsStockEntry.test.ts` — **7 TC render**
`FE-CM-PARTS-01..07`, chi tiết ở [`06_Frontend_Design.md §SparePartsStockEntry`](06_Frontend_Design.md).
Bắt buộc **mount thật + assert text đã render** (không assert store/type) — chống "state chết" như CR-69.

### IX.5 Chống vacuous (BẮT BUỘC ghi bằng chứng vào báo cáo vòng)

1. **Mutation parity:** đổi trong `_spare_row_stock_status` (tên ĐÃ LAND — `04 §3.8.2`) nhánh
   `NOT_FOUND` → `"OK"` ⇒ `TC-CM-PARTS-03`, `TC-CM-PARTS-04` PHẢI **ĐỎ**. Hoàn nguyên ⇒ xanh.
2. **Mutation SSoT:** thay lời gọi helper trong `validate_spare_parts_stock_entries` bằng phép so sánh
   viết tay ⇒ TC vẫn xanh (predicate trùng), nhưng **guard tĩnh** phải bắt: guard đếm số lần xuất hiện
   literal `"AC Stock Movement"` trong `services/imm09.py` — **chỉ được 1** (hằng `_DT_STOCK_MOVEMENT`).
   >1 ⇒ ĐỎ. **ĐÃ LAND** = `TC-CM-PARTS-09` (`test_imm09.py`).
3. **Mutation cite:** rot 1 cite `services/imm09.py:<dòng> <symbol>` trong `description` ⇒ `cr78_h` ĐỎ.
4. **Mutation counter:** thêm 1 TC mà không sync 7 counter ⇒ `test_mobile_docset` ĐỎ (đúng thiết kế).
5. **Mutation FE:** hoàn nguyên cột về `v-if="p.stock_entry_ref"` ⇒ `FE-CM-PARTS-03` ĐỎ.

### IX.6 DoD vòng

| Suite | Trước | Sau |
|---|---|---|
| `bench --site miyano run-tests --module assetcore.tests.imm09.test_imm09` | 221 OK | **229 OK** (+8 TC `TestRepairSparePartsStockEntryStatus` TC-CM-PARTS-01..08) |
| `… --module assetcore.tests.guards.test_mobile_oas` | 951 OK | **959 OK** |
| `… --module assetcore.tests.guards.test_mobile_docset` | 9 OK | **9 OK** (không đổi số TC) |
| `… --module assetcore.tests.integration.test_rowscope_docperm_gate` / `test_rowscope_invariant` | xanh | **xanh** (0 regress CR-74) |
| FE `vue-tsc --noEmit` · `vitest run` | xanh | **xanh** |

> 🔴 **Mọi `run-tests` đặt `timeout` tool ≥ 600000ms.** Kill giữa chừng = nhiễm DB, **không phải** bug sản phẩm.
> 🔴 **KHÔNG curl** để chấm DoD — gunicorn `--preload` chưa reload ⇒ stale worker / phantom 417 (LL-DEPLOY-07).

---

## X. AC-CR-79 — Whitelist khoá `filters` (`list_repair_work_orders`) · bộ TC bắt buộc (2026-07-27) 🔴 SPEC

> Khuôn canonical + guard OAS `cr79_a..h` + mutation + DoD: [`../imm-08/07 §X`](../imm-08/07_Testing_QA.md).
> **KHÔNG lặp lại** — dưới đây chỉ là bộ TC BE riêng của IMM-09.

### X.1 Fixture

1 `AC Asset` + 1 `Asset Repair` `status="Open"`, `priority="Normal"`, `assigned_to` = KTV test.
Persona **KTV nội bộ** (có DocPerm read `Asset Repair`) — **KHÔNG `Administrator`**. Teardown
`tests/_asset_cleanup.py` (đã từng rò 101 `Asset Repair` làm suite ĐỎ giả).

### X.2 Bộ TC BE — `test_imm09.py::TestCmFilterKeyWhitelist`

| TC | Kịch bản | Assert |
|---|---|---|
| **TC-CMFK-01** | `list_repair_work_orders(filters='{"khong_ton_tai_abc":"x"}')` qua API tier | `success is False` · `error.code == "INVALID_PARAMS"` · `http_status == 400` · `message_code == "VAL-INVALID-FILTER-KEY"` · **KHÔNG raise** |
| **TC-CMFK-02** | như trên | message nêu `khong_ton_tai_abc` + ≥3 khoá hợp lệ |
| **TC-CMFK-03** | như trên — **assert phủ định** | không chứa `Unknown column` / `tabAsset Repair` / `tabPM Work Order` / `OperationalError` / `SELECT` |
| **TC-CMFK-04** | **AC2(a)**: lặp TỪNG khoá của `services.imm09._ALLOWED_FILTER_KEYS` (**import THẲNG**) | mỗi khoá ⇒ `success is True`; `set(_PROBE_VALUES) == _ALLOWED_FILTER_KEYS`; `assertGreaterEqual(len(...), 18)` chống vacuous |
| **TC-CMFK-05** | **AC4**: `_VENDOR_SCOPE_FIELD_MAP["Asset Repair"]` (đọc từ `services.shared.scope`) ∈ whitelist | xanh, **không** hardcode `"asset_ref"` |
| **TC-CMFK-06** | `filters='{}'` / absent | `success is True`, rows == baseline |
| **TC-CMFK-07** | JSON hỏng | `VAL-INVALID-PARAMS` (đường cũ), không bị nuốt |
| **TC-CMFK-08** | **AC3 — 0 regression** 7 khoá: `status`, `asset_ref`, `assigned_to`(`mine=1`), `priority`, `open`, `sla_breached_live`, `search` | rows + `pagination` **y hệt** snapshot trước-thay-đổi |
| **TC-CMFK-09** | **AC5 — ngữ nghĩa khoá ảo không đổi**: `{"open":"1","status":"Completed"}` | `status` đơn lẻ **THẮNG** `open` (`_apply_open_drill:1081`) — kết quả y hệt baseline |
| **TC-CMFK-10** | **INV-ROWSCOPE** persona KTV + filter hợp lệ | `pagination.total == len(data["data"])` |
| **TC-CMFK-11** | 6 khoá web-FE thật (`CMWorkOrderListView.buildFilters` `:104-115`) gửi **cùng lúc** | `success is True` — chốt "FE hiện tại KHÔNG bịa khoá nào" |
| **TC-CMFK-12** | `{"parts_hold_started": "2026-01-01"}` (cột THẬT nhưng **CỐ Ý** ngoài whitelist) | `success is False` + `VAL-INVALID-FILTER-KEY` — chốt quyết định "cột nội bộ không quảng cáo" |
| **TC-CMFK-13** *(QA bổ sung)* | `filters` KHÔNG phải object: `'[["asset_ref","=","X"]]'`, `'123'`, `'"abc"'` | envelope `success is False` + `http_status 400` + `code INVALID_PARAMS`, **KHÔNG raise** — mirror `TC-PMFK-14` (SSoT `shared/filters.py::assert_allowed_filter_keys` SHAPE-GATE) |

### X.3 Chống vacuous

1. **RED-before**: `TC-CMFK-01` hiện **raise `OperationalError (1054, 'tabAsset Repair.khong_ton_tai_abc')`**.
2. `TC-CMFK-08`/`TC-CMFK-09` phải so **snapshot THẬT** trong cùng lần chạy, không so "có > 0 dòng".
3. `TC-CMFK-11` phải đọc bộ khoá **từ hằng số/hiện vật**, không chép 6 chuỗi rời — nếu FE thêm điều khiển mới
   mà quên whitelist, TC này phải **ĐỎ**.

### X.4 DoD vòng — xem bảng đầy đủ ở [`../imm-08/07 §X.5`](../imm-08/07_Testing_QA.md)

`test_imm09` baseline **230 `def test`** → **≥242**. Đọc lại số trên đĩa trước khi sửa; **chấm theo DELTA**.

---

## XI. AC-CR-82 — `available_actions[]` 6 CTA server-driven · bộ TC bắt buộc (2026-07-27)

Hợp đồng: [`05_API_Specification.md §15`](./05_API_Specification.md) · builder: [`04_Backend_Design.md §3.1-ter`](./04_Backend_Design.md) · FE: [`06_Frontend_Design.md`](./06_Frontend_Design.md) «CMWorkOrderDetail — 6 CTA server-driven».

### XI.1 Fixture tối thiểu

1 `AC Asset` + **1 phiếu `Asset Repair` cho MỖI status** trong 9 state (`Open` … `Cancelled`). 2 status `Completed`/`Cannot Repair` có `docstatus=1` ⇒ **dựng bằng `db_set`/`frappe.db.set_value` trên bản ghi đã submit**, KHÔNG `doc.save()` (không tái-validate). Dọn sạch ở `tearDownClass` (`tests/_asset_cleanup.py`).

3 persona kiểm quyền: **đủ cap** (`Repair Manager`) · **chỉ `repair.write`, không `repair.create`** (dựng bằng cách gỡ `create` khỏi DocPerm **trong test**, khôi phục ở teardown) · **không cap nào** (`AssetCore Auditor`).

### XI.2 Bộ TC BE — `test_imm09.py::TestCmAvailableActionsParity` (baseline **243 `def test`** đếm tĩnh 2026-07-27 — **ĐỌC LẠI trước khi sửa**, chấm theo **DELTA +12**, KHÔNG số tuyệt đối)

| TC | Kỳ vọng | Bất biến |
|---|---|---|
| `TC-CM-CTA-01` | `get_work_order` trả khoá `available_actions` với **ĐÚNG 6** phần tử, **đúng thứ tự** `_REPAIR_ACTION_SPECS`, mỗi phần tử **đúng 5 khoá**, `route == ""` — cho **cả 9** status | INV-CMCTA-3 |
| `TC-CM-CTA-02` | **PARAMETRIC 54 ô** (9 status × 6 action) — `enabled == 1` ⟹ gọi service tương ứng **KHÔNG** ném `IMM09_BAD_STATE` | **INV-CMCTA-1a** (soundness, 54/54) |
| `TC-CM-CTA-03` | **PARAMETRIC 45 ô** (trừ 9 ô `request_spare_parts`) — `enabled == 0` ∧ đủ cap ∧ không SoD ⟹ service **CÓ** ném `IMM09_BAD_STATE` | **INV-CMCTA-1b** + allowlist `_ADVERTISE_NARROWER_THAN_ENFORCE` **chỉ-giảm** (assert `== {"request_spare_parts"}` — thêm phần tử ⇒ ĐỎ) |
| `TC-CM-CTA-04` | `enabled is False ⟹ reason != ""` ∧ `enabled is True ⟹ reason == ""` trên **cả 54 ô**; `reason ∈ {3 hằng}` | **INV-CMCTA-9 (D9)** + INV-CMCTA-2 |
| `TC-CM-CTA-05` | status **rỗng** `""` và mã lạ `"Đang bay"` ⇒ 6 phần tử, cả 6 `enabled=false`, cả 6 reason = **bậc transition** | D9 biên |
| `TC-CM-CTA-06` | Persona **chỉ `repair.write`** (không `create`) ⇒ 4 action đầu `enabled=false` + reason **capability** (nếu chỉ lấy cap lớp API thì test này XANH GIẢ ⇒ phải assert reason == `_REPAIR_ACTION_REASON_CAPABILITY`) | **INV-CMCTA-5** / ADR-IMM09-CTA-03 |
| `TC-CM-CTA-07` | AST-parse `api/imm09.py` + `services/imm09.py`: tập cap advertise của mỗi action == **hợp** mọi `rbac.require(...)` trên đường gọi | INV-CMCTA-5 (anti-drift) |
| `TC-CM-CTA-08` | Mỗi `spec["endpoint"]` resolve ĐỘNG trong `assetcore.api.imm09` **và** `f"assetcore.api.imm09.{endpoint}" in frappe.whitelisted` (hoặc tương đương v15) | INV-CMCTA-4 |
| `TC-CM-CTA-09` | **SoD**: phiếu `Pending Inspection`, closer == `session.user` ⇒ `confirm_inspection.enabled=0` + reason SoD; closer khác ⇒ `1`; **không** có event `repair_pending_inspection` ⇒ `1` (**FAIL-OPEN**) | A5 / §15.5 |
| `TC-CM-CTA-10` | **READ-ONLY**: đếm `Asset Lifecycle Event` + `modified` của doc **trước/sau** `get_work_order` ⇒ **bằng nhau**; `_resolve_wo_closer` **không** được gọi khi status ≠ `Pending Inspection` (patch/spy) | **INV-CMCTA-10** |
| `TC-CM-CTA-11` | Key-set payload **⊇** key-set trước CR (đặc biệt `allowed_transitions`, `spare_parts_used`, `parts_pending_stock_entry`, `repair_checklist`, `is_sla_breached`) | **INV-CMCTA-11** (thuần additive) |
| `TC-CM-CTA-12` | 6 guard service dùng **đúng hằng** `*_FROM` (grep/AST: 0 tuple literal status trong 6 thân hàm) | SSoT §15.2 |

### XI.3 Guard hợp đồng OAS — `test_mobile_oas.py::TestMobileRepairAvailableActionsParity` **8 TC** `cr82_a..h` ✅ ĐÃ LAND (Bước-2, XANH)

Bảng TC: [`05 §15.7`](./05_API_Specification.md). BE Bước-4 bồi thêm **`cr82_i`** (parity `_REPAIR_ACTION_SPECS` import THẬT ↔ 6 key OAS, mirror `cr77_i`) ⇒ `_EXPECTED_TEST_COUNT` **991 → 992** + sync 3 counter docset (`05 §15.8`).

### XI.4 Test FE (CÙNG VÒNG — A9)

`frontend/src/views/cm/tests/CMWorkOrderDetailView.availableActions.test.ts` — **7 TC** `FE-CMCTA-1..7`, bảng ở [`06_Frontend_Design.md`](./06_Frontend_Design.md). TC **`FE-CMCTA-2`** là invariant A9: *không nút CTA nào enabled mà `key` ∉ tập `available_actions` enabled*.

### XI.5 Chống vacuous (BẮT BUỘC ghi bằng chứng vào báo cáo vòng)

1. **Mutation transition:** thêm `RepairStatus.OPEN` vào `_DIAGNOSIS_FROM` ⇒ `TC-CM-CTA-02` **ĐỎ** (advertise rộng hơn enforce). Hoàn nguyên ⇒ xanh.
2. **Mutation cap:** đổi `caps` của `assign_technician` thành `(_CAP_REPAIR_WRITE,)` ⇒ `TC-CM-CTA-06`/`TC-CM-CTA-07` **ĐỎ**.
3. **Mutation reason:** trả `reason=""` khi `enabled=false` ⇒ `TC-CM-CTA-04` **ĐỎ** (D9).
4. **Mutation SoD:** đổi fail-open thành fail-closed (`closer is None ⇒ enabled=0`) ⇒ `TC-CM-CTA-09` **ĐỎ** — chứng minh test khoá **đúng** hành vi enforcement hiện hành, không phải mong muốn.
5. **Mutation read-only:** thêm `frappe.db.set_value` bất kỳ vào builder ⇒ `TC-CM-CTA-10` **ĐỎ**.
6. **Mutation cite:** rot 1 cite `services|api/imm09.py:<dòng> <symbol>` trong `description` ⇒ `cr82_h` **ĐỎ** *(đã verify khuôn này ở `cr78_h`/`cr81_c`)*.
7. **Mutation counter:** thêm TC mà không sync 4 counter ⇒ `test_mobile_docset` **ĐỎ**.
8. **Mutation FE:** hoàn nguyên 1 nút về `v-if="canAssign"` (bỏ trục server) ⇒ `FE-CMCTA-2` **ĐỎ**.

### XI.6 DoD vòng

| Suite | Trước | Sau |
|---|---|---|
| `bench --site miyano run-tests --module assetcore.tests.imm09.test_imm09` | baseline hiện hành (đếm tĩnh **243** `def test` @2026-07-27) | **baseline + 12 OK** — chấm **DELTA**, đọc lại số thật trước khi sửa (đa-phiên ⇒ số tuyệt đối luôn có thể stale) |
| `… --module assetcore.tests.guards.test_mobile_oas` | 983 OK | **991 OK** *(Bước-2 — ĐÃ ĐẠT)* → **992 OK** sau `cr82_i` |
| `… --module assetcore.tests.guards.test_mobile_docset` | 9 OK | **9 OK** *(Bước-2 — ĐÃ ĐẠT)* |
| FE `vue-tsc --noEmit` · `vitest run` | xanh | **xanh** (+7 TC `cmDetailCtaGating`) |

> 🔴 **Mọi `run-tests` đặt `timeout` tool ≥ 600000ms.** Kill giữa chừng = nhiễm DB, **không phải** bug sản phẩm.
> 🔴 **KHÔNG curl** để chấm DoD (LL-DEPLOY-07/08) · **KHÔNG `bench migrate`** (CR này 0 DocType/field mới).

---

## XII. AC-CR-84 — Cổng **ảnh bằng chứng NĐ98** (BR-09-23) · bộ TC bắt buộc (2026-07-27) 🔴 RED-first

> Hợp đồng: [`05 §16`](./05_API_Specification.md) · recipe BE: [`04 §3.10`](./04_Backend_Design.md) · FE: [`06 §CMEvidencePhoto`](./06_Frontend_Design.md).
> **Nguyên tắc chấm:** mọi con số suite ghi theo **DELTA** — baseline tuyệt đối luôn có thể stale do đa-phiên; **ĐỌC LẠI** trước khi sửa.

### XII.1 Fixture tối thiểu (dựng 1 lần, dùng chung)

| Ký hiệu | Nội dung |
|---|---|
| `A_CRIT` | `AC Asset` với `risk_classification = "Critical"` |
| `A_HIGH` | `AC Asset` với `risk_classification = "High"` |
| `A_LOW` / `A_MED` / `A_BLANK` | `risk_classification` = `"Low"` / `"Medium"` / `""` (**chưa phân loại**) |
| `WO(asset)` | `Asset Repair` tạo qua `create_work_order` ⇒ **seed 6 dòng** `repair_checklist` (CR-50), đưa về `In Repair` bằng đường hợp lệ |
| `photo(wo, idx)` | Đính ảnh 1 mục qua `attach_repair_checklist_photo` (**đường THẬT**, không `db.set_value` tay — để test đi qua đúng cửa mà người dùng đi) |

🔴 **Chống vacuous:** mỗi TC chặn PHẢI kèm **đối chứng dương** (cùng fixture, đính đủ ảnh ⇒ thao tác THÀNH CÔNG). Test chỉ khẳng định "bị chặn" là test không phân biệt được *cổng hoạt động* với *mọi thứ đều hỏng*.

### XII.2 Bộ TC BE — `test_imm09.py::TestCmEvidencePhotoGate` (**≥12 TC**, chấm DELTA **+12**)

| TC | Điều kiện | Kỳ vọng |
|---|---|---|
| `TC-CM-EVID-01` | `A_CRIT`, 6 dòng, ảnh ở idx 1,3,4,6 → `close_work_order(cannot_repair=0)` | `success=false`, `message_code == "IMM09-EVIDENCE-PHOTO-REQUIRED"`, `http_status == 422`, `context.missing_count == 2`, `context.missing_idxs == [2, 5]`, `fields` có khoá **`repair_checklist`** (**A1**) |
| `TC-CM-EVID-02` | Sau TC-01: **đọc lại doc TỪ DB** (`frappe.get_doc`, KHÔNG dùng biến in-memory) | `status == "In Repair"`; `repair_summary`/`root_cause_category`/`dept_head_name` **y nguyên** giá trị trước lời gọi; `docstatus == 0` (**A2 · INV-CMEVID-5**) |
| `TC-CM-EVID-03` | Cùng fixture TC-01 → `get_work_order(WO).available_actions` | phần tử `close_work_order`: `enabled is False`, `reason == _REPAIR_ACTION_REASON_EVIDENCE_PHOTO` (**so với HẰNG import từ service**, không so chuỗi chép tay) (**A3**) |
| `TC-CM-EVID-04` | Đính nốt ảnh idx 2,5 → `get_work_order` rồi `close_work_order` | `available_actions[close_work_order].enabled is True` **và** đóng phiếu **THÀNH CÔNG** → `Pending Inspection` (**A3 đối chứng dương**) |
| `TC-CM-EVID-05` | **Parity** `A_CRIT` thiếu ảnh: so `get_work_order().evidence_photo_missing_idxs` với `context.missing_idxs` của `close_work_order` | **BẰNG NHAU** (**INV-CMEVID-1**). Lặp cho 3 cấu hình ảnh khác nhau (0 ảnh · 1 ảnh · 5 ảnh) |
| `TC-CM-EVID-06` | `A_LOW`, `A_MED`, `A_BLANK` — mỗi thứ 1 phiếu, **0 ảnh** | `close_work_order` **THÀNH CÔNG** → `Pending Inspection`; `evidence_photo_required == 0`; `missing_idxs == []`; `total_required == 0` (**A4 · INV-CMEVID-2/7**) |
| `TC-CM-EVID-07` | `A_CRIT`, 0 ảnh → `close_work_order(cannot_repair=1, cannot_repair_reason=…)` | **KHÔNG bị chặn**: `status == "Cannot Repair"`, asset → `Out of Service` (**A5**) |
| `TC-CM-EVID-08` | `A_CRIT` thiếu ảnh, ép `status='Pending Inspection'` bằng `frappe.db.set_value` (bỏ qua `close_work_order`) → `confirm_inspection` | Raise **`ServiceError`** với `message_code == "IMM09-EVIDENCE-PHOTO-REQUIRED"`; **KHÔNG** `frappe.ValidationError`; `docstatus` vẫn `0` (**A6 · INV-CMEVID-6**) |
| `TC-CM-EVID-09` | Như TC-08 nhưng **đính đủ ảnh** trước | `confirm_inspection` **THÀNH CÔNG** → `Completed` (đối chứng dương của A6) |
| `TC-CM-EVID-10` | `get_work_order` trên `A_CRIT` (6 dòng, 2 thiếu) | 3 khoá có mặt, đúng kiểu: `evidence_photo_required == 1` (**int**, `assertIsInstance(v, int)` + `assertNotIsInstance(v, bool)`), `missing_idxs == [2,5]` (**list[int]**, tăng dần), `total_required == 6` (**A7 · INV-CMEVID-3**) |
| `TC-CM-EVID-11` | Phiếu **legacy 0 dòng** checklist, `A_CRIT`, đóng kèm `checklist_results` (3 mục) | `close_work_order` **THÀNH CÔNG** (dòng vừa append **chưa lưu** ⇒ không tính — **ADR-IMM09-EVIDENCE-02**); 3 dòng SAU ĐÓ đã lưu. ⚠️ **CẢI CHÍNH BE Bước-4 (đo được, không suy luận):** ở bước nghiệm thu kế tiếp phiếu bị chặn bởi **CỔNG ẢNH** (`IMM09-EVIDENCE-PHOTO-REQUIRED`) chứ **KHÔNG** phải BR-09-04 như bảng này dự đoán ban đầu — hệ quả TẤT YẾU của thứ tự guard **INV-CMEVID-6** (evidence chạy TRƯỚC `doc.submit()`, còn BR-09-04 nằm ở `before_submit`). Vẫn **không deadlock**: 3 dòng đã có định danh ⇒ đính ảnh rồi nghiệm thu. Test BE khẳng định phần ĐO ĐƯỢC (close thành công + 3 dòng đã lưu); [BA] cần ratify câu chữ kỳ vọng ở bước 2 |
| `TC-CM-EVID-12` | i18n sweep: gom `message` + `action_hint` + `fields.repair_checklist` + `_REPAIR_ACTION_REASON_EVIDENCE_PHOTO` | **0** lần xuất hiện `High`/`Critical`/`In Repair`/`Pending Inspection`/tên vai trò EN; **0** ký tự ASCII-only-token nào ngoài `#<số>` (**A10 · INV-CMEVID-8**) |

**[AC-CR-85] Bổ sung 5 TC sau khi QA phát hiện dư âm (vòng 3) — `test_imm09.py`, ĐÃ XANH 2026-07-27:**

| TC | Tình huống | Kỳ vọng |
|---|---|---|
| `TC-CM-EVID-15` | Đóng phiếu khi thiết bị còn `Low` (0 ảnh, hợp lệ) → **rà soát NĐ98 tái phân loại** asset lên `Critical` → đọc `get_work_order` + gọi `confirm_inspection` | `evidence_photo_missing_idxs == [1..6]`; `confirm_inspection` ném `IMM09-EVIDENCE-PHOTO-REQUIRED` với **CÙNG** `missing_idxs`; `available_actions[confirm_inspection].enabled == false` ∧ `reason == _REPAIR_ACTION_REASON_EVIDENCE_PHOTO_INSPECT`; `docstatus` GIỮ 0 (**INV-CMEVID-4b · D9**) |
| `TC-CM-EVID-16` | Cùng fixture, đính đủ 6 ảnh **ở trạng thái 'Pending Inspection'** | Đính ảnh ĐƯỢC PHÉP (đường khắc phục còn mở — P5 không chặn state này); CTA bật lại + `reason == ""`; `confirm_inspection` → `Completed`, `docstatus=1` (đối chứng dương, chống vacuous) |
| `TC-CM-EVID-17` | Đính ảnh vào phiếu **đã nghiệm thu** (`docstatus=1`) **và** phiếu **'Cannot Repair'** (`docstatus=0` — nhánh chỉ bắt được nếu guard đọc CẢ `status`) | Cả 2 nhánh: `ServiceError` VALIDATION 422 + `fields.file`; `row.photo` **0 byte** đổi (**INV-CMEVID-9**) |
| `TC-CM-EVID-18` | Re-drain write-outbox: đính ảnh có `client_request_id` khi phiếu đang mở → đóng + nghiệm thu → **gọi lại CÙNG khoá** | Trả envelope **VERBATIM** như lần đầu (0 false-error → `markFailed`), `File` **không** nhân đôi ⇒ guard P5 KHÔNG phá BR-09-16-IDEMP |
| `TC-CR82-B3` | Meta-guard AST: quét mọi hằng `_REPAIR_ACTION_REASON_*` mà `_build_repair_available_actions` dùng | Mỗi hằng phải ánh xạ tới mã lỗi ∈ `_CR82_ADVERTISED_GATE_CODES` ⇒ thêm bậc business mới mà quên bồi oracle = **ĐỎ NGAY** (bài học: oracle 54 ô chỉ đếm `IMM09_BAD_STATE` nên **mù** với H1) |

> **Mutation-verify AC-CR-85 (đã chạy 2026-07-27):** (a) thay nhánh `elif _repair_evidence_missing_idxs(...)` trong builder bằng `elif False` ⇒ `TC-CM-EVID-15` **ĐỎ** với đúng thông điệp "NÚT CHẾT … advertise BẬT nhưng service ném IMM09_EVIDENCE_PHOTO_REQUIRED"; (b) gỡ `_REPAIR_ACTION_REASON_EVIDENCE_PHOTO_INSPECT` khỏi bảng ánh xạ của meta-guard ⇒ `TC-CR82-B3` **ĐỎ**; hoàn nguyên ⇒ XANH. ⚠️ Ghi nhận thành thật: parity 54 ô **KHÔNG** ĐỎ dưới đột biến (a) vì fixture của nó dùng asset **chưa phân loại** ⇒ cổng ảnh không kích hoạt; đó chính là lý do phải có `TC-CM-EVID-15` (fixture nghiệp vụ) **cộng** meta-guard `TC-CR82-B3` (cấu trúc), chứ không dựa vào ma trận 54 ô.

**Mutation-verify (BẮT BUỘC ghi bằng chứng vào báo cáo vòng — chống test vacuous):**

> ✅ **ĐÃ CHẠY Bước-4 (2026-07-27), 7/7 đột biến ĐỎ đúng thiết kế** — mỗi lần đột biến 1 chỗ trên bản sao, chạy TC đích, rồi khôi phục nguyên trạng (md5 xác nhận): M1→`TC-CM-EVID-05` ĐỎ · M2→`TC-06` ĐỎ · M3 (dời guard xuống SAU `RepairRepo.save`)→`TC-02` ĐỎ · M4 (gỡ pre-check nghiệm thu)→`TC-08` ĐỎ · M5 (builder suy từ `risk_class` = CHÍNH bug CR-51)→`TC-03` ĐỎ · M6 (emit `bool`)→`TC-10` ĐỎ · M7 (chặn cả nhánh `cannot_repair=1`)→`TC-07` ĐỎ. Ngoài ra `TC-CR84-13` (mutation-probe THƯỜNG TRỰC trong suite) ép predicate trả `[]` ⇒ phiếu đóng được, khôi phục ⇒ chặn lại — giữ tính không-vacuous ở MỌI vòng sau, không chỉ vòng này.

| # | Đột biến tạm | TC phải ĐỎ |
|---|---|---|
| M1 | Đổi `_EVIDENCE_HIGH_RISK` thành `{"Critical"}` | `TC-CM-EVID-01` (fixture `A_HIGH`) |
| M2 | Coi `""` là nguy cơ cao (`strip() not in {"Low","Medium"}`) | `TC-CM-EVID-06` |
| M3 | Dời guard **xuống sau** `RepairRepo.save(doc)` | `TC-CM-EVID-02` |
| M4 | Bỏ pre-check ở `confirm_inspection` | `TC-CM-EVID-08` |
| M5 | Builder tự tính lại (predicate thứ hai) rồi lệch 1 dòng | `TC-CM-EVID-03`/`05` |
| M6 | Emit `evidence_photo_required` kiểu `bool` | `TC-CM-EVID-10` |
| M7 | Chặn cả nhánh `cannot_repair=1` | `TC-CM-EVID-07` |

### XII.3 Guard hợp đồng OAS — `test_mobile_oas.py::TestMobileRepairEvidencePhotoContract` **9 TC** `cr84_a..i` ✅ ĐÃ LAND (Bước-2, XANH)

`cr84_a` kiểu (int enum[0,1] · array<integer≥1> · integer≥0) · `cr84_b` additive/optional + `required` GIỮ `['name']` + 2 câu chống-suy-sai · `cr84_c` 0 delta cấu trúc (109/287/38) + AP:true · `cr84_d` **INV-CMEVID-1** tuyên bố trong hợp đồng · `cr84_e` nguồn `risk_classification` (phủ định `risk_class`, `""` ⇒ 0) · `cr84_f` 2 op ghi khai mã lỗi + HTTP-200 + `KHÔNG 417` + miễn trừ + lý do pre-check · `cr84_g` advertise↔enforce trong `available_actions` · `cr84_h` cite-drift (schema + 2 op, 6 symbol bắt buộc) · `cr84_i` **PENDING-BE**.

> ⚠️ **`cr84_i` PHẢI được LẬT ở Bước-4.** Nó đang khẳng định `services.imm09._repair_evidence_missing_idxs` **chưa** tồn tại và `IMM09-EVIDENCE-PHOTO-REQUIRED` **chưa** vào `MESSAGES`. BE land ⇒ **ĐỎ ĐÚNG THIẾT KẾ** ⇒ đổi thành `cr84_j` parity đầy đủ: (1) predicate tồn tại & callable; (2) `MESSAGES[mã]["http_status"] == 422` ∧ `template` khác rỗng ∧ **không** chứa `High`/`Critical`; (3) `_REPAIR_ACTION_REASON_EVIDENCE_PHOTO` khác rỗng. **Lật ≠ thêm TC** ⇒ counter `test_mobile_oas` **KHÔNG đổi** (1008). Đồng thời **REFRESH CITE** `services/imm09.py` trong OAS (dòng dịch sau khi land) — `cr84_h` sẽ ĐỎ nếu quên.

### XII.4 Test FE (CÙNG VÒNG — A8) — `FE-CM-EVID-01..07`

Chi tiết ở [`06 §CMEvidencePhoto`](./06_Frontend_Design.md). Bắt buộc **RENDER thật** (không chỉ type-check), có TC "3 khoá vắng ⇒ không khẳng định gì" và TC "tooltip == `reason` nguyên văn".

### XII.5 DoD vòng

| Suite | Trước | Sau |
|---|---|---|
| `bench --site miyano run-tests --module assetcore.tests.imm09.test_imm09` | **259 OK** (đếm THẬT ngay trước Bước-4) | **273 OK** ✅ ĐÃ ĐẠT 2026-07-27 (DELTA **+14** = 12 TC `§XII.2` + `TC-CR84-13` mutation-probe thường trực + `TC-CR84-14` biên predicate thuần) → **278 OK** sau **AC-CR-85** (DELTA **+5** = `TC-CM-EVID-15..18` + meta-guard `TC-CR82-B3`) |
| `… --module assetcore.tests.guards.test_mobile_oas` | 999 OK | **1008 OK** *(Bước-2 — ĐÃ ĐẠT)*; Bước-4 lật `cr84_i` ⇒ **GIỮ 1008** |
| `… --module assetcore.tests.guards.test_mobile_docset` | 9 OK | **9 OK** *(Bước-2 — ĐÃ ĐẠT)* |
| `python scripts/gen_fe_messages.py --check` | xanh | **xanh** (bắt buộc — thiếu ⇒ FE render `SYS-500`) |
| FE `vue-tsc --noEmit` · `npm run test` | xanh | **xanh** (+7 TC `FE-CM-EVID-*`) |

> 🔴 **Mọi `run-tests` đặt `timeout` tool ≥ 600000ms.** Kill giữa chừng = nhiễm DB, **không phải** bug sản phẩm.
> 🔴 **KHÔNG curl** để chấm DoD (LL-DEPLOY-07/08) · **KHÔNG `bench migrate`** (0 DocType/field mới) · **KHÔNG `npm run build`** (= deploy live).
