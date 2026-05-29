# 07 — Kiểm thử & An ninh (Testing & QA & Security)

| Mục | Giá trị |
|---|---|
| Module | IMM-15 — Spare Parts Inventory Tracking (Theo dõi tồn kho phụ tùng y tế) |
| Phạm vi | Per-module |
| Owner | QA Lead + Security Officer |
| Liên kết | 02 Analysis (US, BR, Activity, BPMN) · 03 Diagrams · 04 Backend · 05 API · 06 Frontend |

> **Mục đích**: Suy ra test case **có hệ thống** từ phân tích (file 02) bằng kỹ thuật black-box + white-box, không liệt kê tự phát. Bao gồm: phân tích đối tượng test → chọn kỹ thuật → viết test → traceability → UAT → security → code quality. Phần này là gate go-live.

> **Trạng thái hiện tại (2026-05-29)**: Module IMM-15 **đã triển khai** (Wave 2). Test thực tế: `assetcore/tests/test_imm15.py` — 9 lớp test, 15 test method **✅ Live**. Coverage formal report **chưa chạy** → các con số coverage dưới đây là *target*, không phải đo thực. Field-level permission (permlevel) **chưa cấu hình** trên DocType → đánh dấu gap ở VI.1.

---

# Phần I — Test Analysis (Phân tích đối tượng test)

> Mục tiêu Phần I: trả lời 4 câu hỏi trước khi viết test case: **(1) test cái gì** **(2) suy ra từ đâu** **(3) ưu tiên cái nào** **(4) loại trừ cái nào**.

## I.1. Component Inventory — Liệt kê phần mềm cần test

Liệt kê toàn bộ artefact test được của IMM-15 (nguồn: `04_Backend_Design.md` §DocType+§Service, `05_API_Specification.md` §Catalog, `06_Frontend_Design.md` §Views). Mỗi dòng → ≥ 1 test class ở Phần III.

| # | Component | Loại | File / Tên | Test layer áp dụng |
|---|---|---|---|---|
| 1 | IMM Spare Allocation | DocType | `imm_spare_allocation.json` | Integration (lifecycle) |
| 2 | IMM Spare Allocation Item | Child DocType | `imm_spare_allocation_item.json` | Integration (via parent) |
| 3 | IMM Stock Cycle Count | DocType | `imm_stock_cycle_count.json` | Integration (lifecycle) |
| 4 | IMM Stock Cycle Count Item | Child DocType | `imm_stock_cycle_count_item.json` | Integration (via parent) |
| 5 | IMM Spare Part Forecast | DocType | `imm_spare_part_forecast.json` | Integration (lifecycle) |
| 6 | IMM Spare Forecast Item | Child DocType | `imm_spare_forecast_item.json` | Integration (via parent) |
| 7 | IMM Critical Spare Watchlist | DocType | `imm_critical_spare_watchlist.json` | Integration (CRUD + breach) |
| 8 | Allocation workflow | Workflow | `workflow/imm_15_allocation_workflow.json` (12 transitions) | Integration (state transition) |
| 9 | Cycle Count workflow | Workflow | `workflow/imm_15_cycle_count_workflow.json` (4 transitions) | Integration (state transition) |
| 10 | `create_allocation` | Service function | `services/imm15.py::create_allocation` | Unit |
| 11 | `approve_allocation` | Service function | `services/imm15.py::approve_allocation` | Unit |
| 12 | `issue_allocation` | Service function | `services/imm15.py::issue_allocation` | Unit + Integration (stock movement) |
| 13 | `return_items` / `return_allocation` | Service function | `services/imm15.py::return_items` | Unit |
| 14 | `create_cycle_count` / `submit_cycle_count` / `post_cycle_count` | Service function | `services/imm15.py::*_cycle_count` | Unit + Integration |
| 15 | `generate_spare_forecast` / `approve_forecast` | Service function | `services/imm15.py::*_forecast` | Unit |
| 16 | `add_to_watchlist` / `get_critical_watchlist` | Service function | `services/imm15.py::add_to_watchlist` | Unit |
| 17 | `get_dashboard_stats` / `get_low_stock_alerts` / `get_stock_snapshot` | Service function (read) | `services/imm15.py::get_*` | Unit (schema) |
| 18 | `check_part_availability` | API read | `api/imm15.py::check_part_availability` | API integration + perf |
| 19 | Validator `_vr_05_urgency_valid` | Validator | `services/imm15.py::_vr_05_urgency_valid` | Unit (EP) |
| 20 | Validator `_vr_13_warehouse_active` | Validator | `services/imm15.py::_vr_13_warehouse_active` | Unit (EP) |
| 21 | `_create_stock_movement_for_issue/return/adjustment` | Service (DAO bridge) | `services/imm15.py::_create_stock_movement_*` | Integration (AC Stock Movement) |
| 22 | `_seed_capa_for_cycle_variance` / `_seed_breach_capa` | Service (cross-module IMM-16) | `services/imm15.py::_seed_*_capa` | Integration |
| 23 | `_write_allocation_audit` | Audit writer | `services/imm15.py::_write_allocation_audit` | Integration (audit chain) |
| 24 | `check_critical_spare_breach` | Scheduler job | `services/imm15.py::check_critical_spare_breach` (hooks daily) | Unit + Cron simulation |
| 25 | `check_low_stock_and_alert` | Scheduler job | `services/imm15.py::check_low_stock_and_alert` | Cron simulation |
| 26 | `check_expiring_batches` | Scheduler job | `services/imm15.py::check_expiring_batches` | Cron simulation |
| 27 | `compute_inventory_kpis` | Scheduler job | `services/imm15.py::compute_inventory_kpis` | Cron simulation |
| 28 | `generate_spare_demand_forecast` | Scheduler job | `services/imm15.py::generate_spare_demand_forecast` (monthly) | Cron simulation |
| 29 | `reclassify_abc` | Scheduler job | `services/imm15.py::reclassify_abc` (quarterly) | Cron simulation |
| 30 | `reserve_for_pm` / `reserve_for_repair` / `flag_obsolete_on_decommission` | Lifecycle hook | `hooks.py → services/imm15.py` | Integration (cross-module) |
| 31 | API endpoints (24 whitelisted) | API | `api/imm15.py` | API integration |
| 32 | FE views (Inventory) | FE view | `frontend/src/views/inventory/*.vue` (13 view) | E2E (Playwright) |
| 33 | Pinia store | Store | `frontend/src/stores/imm15.ts` | Unit (vitest) — *(Cần khảo sát)* |

## I.2. Trace nguồn test — User Stories, Activity Flows, Business Rules

3 bảng dẫn từ artefact phân tích (`02_Analysis_Design.md`) sang test layer. Mỗi US/BR/UC phải có ≥ 1 test ở Phần III và xuất hiện trong matrix Phần IV.

### I.2.a. Từ User Story (→ 02 §IV.1)
| US ID | Tiêu đề ngắn | Test layer dự kiến |
|---|---|---|
| US-15-01 | Allocation theo Work Order (create→approve→issue) | Unit + Integration + UAT |
| US-15-02 | Emergency override khi Critical Spare hết (dual-approval) | Unit + UAT |
| US-15-03 | Cycle Count → CAPA khi variance | Integration + UAT |
| US-15-04 | Critical Spare Watchlist breach (scheduler) | Cron sim + UAT |
| US-15-05 | Demand Forecast part-level (generate→approve) | Unit + UAT |

### I.2.b. Từ Business Rule (→ 02 §IV.2 + §IV.3)
| BR/VR ID | Phát biểu (rút gọn) | Component liên quan (I.1) | Kỹ thuật test phù hợp |
|---|---|---|---|
| BR-15-01 / VR-15-01 | Non-emergency phải link Work Order | `create_allocation` (#10) | Decision Table |
| BR-15-02 / VR-15-02 | `imm_traceability_required=1` → batch/serial bắt buộc khi issue | `issue_allocation` (#12) | Decision Table |
| BR-15-03 / VR-15-03 | `qty_issued ≤ available_qty`, Emergency+Critical bypass | `issue_allocation` (#12) | BVA + Decision Table |
| BR-15-04 | Critical Watchlist breach → CAPA + email | `check_critical_spare_breach` (#24) | Use Case (cron) |
| BR-15-05 / VR-15-04 | Variance > 5% hoặc > 5M → root_cause bắt buộc | `post_cycle_count` (#14) | BVA + Decision Table |
| BR-15-06 | ABC reclassification mỗi quý | `reclassify_abc` (#29) | Use Case (cron) |
| BR-15-07 | Forecast Approved mới được dùng gợi ý reorder | `approve_forecast` (#15) | Decision Table |
| BR-15-08 | Returned items → QC; Damaged → kho QC Hold | `return_items` (#13) | Decision Table |
| BR-15-09 | Asset decommissioned → flag obsolete | `flag_obsolete_on_decommission` (#30) | Use Case |
| BR-15-10 | Mọi mutation ghi IMM Audit Trail | `_write_allocation_audit` (#23) | Use Case + audit chain |
| VR-15-05 | `urgency IN {Routine/Urgent/Emergency}` | `_vr_05_urgency_valid` (#19) | EP |
| VR-15-07 | `reorder_point ≥ safety_stock` | `generate_spare_forecast` (#15) | BVA |
| VR-15-08 | `qty_returned ≤ qty_issued` | `return_items` (#13) | BVA |
| VR-15-09 | Watchlist spare phải Critical, min > 0 | `add_to_watchlist` (#16) | Decision Table |
| VR-15-10 | Emergency: 2 approver khác nhau | `issue_allocation` (#12) | Decision Table |
| VR-15-11 | Cycle count: `verified_by ≠ counted_by` | `post_cycle_count` (#14) | Decision Table |
| VR-15-12 | Forecast method whitelist | `generate_spare_forecast` (#15) | EP |
| VR-15-13 | `AC Warehouse.is_active=1` | `_vr_13_warehouse_active` (#20) | EP |

### I.2.c. Từ Use Case / Activity Flow (→ 02 §III.4)
| UC ID | Use Case | Branch chính | Branch ngoại lệ |
|---|---|---|---|
| UC-01 | Cấp phát theo WO | create→approve→pick→issue (Issued) | Thiếu WO (VR-15-01), tồn không đủ (VR-15-03) |
| UC-02 | Cycle Count | Planned→Counting→Reviewed→Posted | Variance > ngưỡng → root_cause + CAPA |
| UC-03 | Watchlist breach | Scheduler phát hiện < min → email + CAPA | Đã có open CAPA → không nhân đôi |
| UC-04 | Emergency Override | Dual-approval → Issued (audit_flags) | Cùng 1 approver (VR-15-10) |
| UC-05 | Return | Good → kho gốc; Damaged → QC Hold | `qty_returned > qty_issued` (VR-15-08) |
| UC-06 | Demand Forecast | generate Draft → approve → reorder | Draft chưa approve → không gợi ý (BR-15-07) |
| UC-07 | ABC/XYZ quarterly | reclassify cập nhật class | Idempotent — chạy lại không nhân đôi audit |
| UC-08 | Watchlist CRUD | add Critical part | add Major part bị chặn (VR-15-09) |

## I.3. Risk-based Priority

| Component (I.1) | Likelihood | Impact | Risk = L×I | Priority |
|---|---|---|---|---|
| `issue_allocation` + stock movement (#12, #21) | 4 | 5 | 20 | **Critical** |
| Emergency override dual-approval (VR-15-10) | 3 | 5 | 15 | **Critical** |
| Allocation workflow transitions (#8) | 4 | 4 | 16 | **Critical** |
| `_write_allocation_audit` / audit chain (#23) | 3 | 5 | 15 | **Critical** |
| Cycle Count variance → CAPA (#14, #22) | 3 | 4 | 12 | High |
| `check_critical_spare_breach` scheduler (#24) | 3 | 4 | 12 | High |
| `create_allocation` (VR-15-01) (#10) | 4 | 3 | 12 | High |
| `generate_spare_forecast` / `approve_forecast` (#15) | 2 | 3 | 6 | Medium |
| `add_to_watchlist` (VR-15-09) (#16) | 2 | 3 | 6 | Medium |
| Dashboard read endpoints (#17) | 2 | 2 | 4 | Low |

**Quy ước priority**: Critical (R ≥ 15) test trước, fail = block release · High (10–14) bắt buộc trước go-live · Medium (5–9) trong sprint · Low (< 5) chỉ khi báo bug.

## I.4. Scope

- **In-scope**: service layer IMM-15 (allocation/cycle count/forecast/watchlist), 2 workflow state machine, scheduler jobs, API envelope `{success, data}`, audit trail, RBAC theo role.
- **Out-of-scope**:
  - Performance load test sâu → chỉ định target ở III.8 (chưa chạy k6).
  - AC Inventory Backbone (Wave 1: AC Spare Part, AC Stock Movement) — đã LIVE, IMM-15 chỉ smoke qua `stock_movement_ref`.
  - Cross-module IMM-08/IMM-12 (reserve hook) — chỉ smoke ở integration, full flow test ở module gốc.
  - FE unit test (vitest) cho `stores/imm15.ts` — *(Cần khảo sát)*, hiện chỉ E2E.
- **Assumptions**: master data (AC UOM, AC Warehouse, AC Spare Part) đã seed; test tự tạo fixture riêng và cleanup ở `tearDownClass`; site test đã `bench migrate` (workflow + DocType active).

---

# Phần II — Test Design Techniques (Kỹ thuật thiết kế test case)

> Mỗi test phải truy được về 1 kỹ thuật ở dưới.

## II.1. Black-box techniques

| Kỹ thuật | Khi nào dùng | Áp dụng vào IMM-15 | Số test (rule of thumb) |
|---|---|---|---|
| **Equivalence Partitioning (EP)** | Input chia nhóm tương đương | `urgency` enum (VR-15-05), forecast `method` (VR-15-12), warehouse active/inactive (VR-15-13) | 1 test/partition |
| **Boundary Value Analysis (BVA)** | Numeric/length có biên | `qty_issued` vs `available_qty` (VR-15-03), `qty_returned ≤ qty_issued` (VR-15-08), variance 5% / 5M (VR-15-04), `reorder_point ≥ safety_stock` (VR-15-07) | 2-3 test/biên |
| **Decision Table** | Multi-condition rule | VR-15-01 (urgency×work_order), VR-15-10 (2 approver khác nhau×role), VR-15-09 (part class×min) | 2^N rút gọn |
| **State Transition Testing** | Workflow FSM | Allocation (12 transition), Cycle Count (4 transition) | Mỗi transition + invalid |
| **Use Case Testing** | E2E actor flow | UAT scenarios, scheduler jobs (setup→run→assert) | 1/main + 1/alt + 1/exception |
| **Error Guessing** | null/empty/race | Mọi endpoint nhận user input, idempotency breach/CAPA | Bổ sung |

## II.2. White-box techniques

| Kỹ thuật | Áp dụng vào | Tiêu chí đạt | Công cụ |
|---|---|---|---|
| **Statement coverage** | Service functions (#10–#16) | ≥ 85% line *(target — chưa đo)* | `bench run-tests --coverage` |
| **Branch / Decision coverage** | Functions có if/else/try (issue, post_cycle_count) | ≥ 80% branch *(target)* | `coverage --branch` |
| **Condition / MC/DC** | VR-15-10 (multi-AND), VR-15-03 (Emergency bypass) | Mỗi sub-condition kiểm soát outcome độc lập | Manual test design |
| **Path coverage** | `_compute_variance` / pure helper ≤ 20 LOC | Path khả dĩ (loop 0,1,N) | Manual |

## II.3. Mapping Component → Kỹ thuật

| Loại component | Kỹ thuật chính | Kỹ thuật phụ |
|---|---|---|
| Field validator (`_vr_05`, `_vr_13`) | EP | Error guessing |
| Business-rule check (VR-15-01/03/10) | Decision Table | MC/DC |
| Workflow transition | State Transition | Use Case |
| Service function pure | EP + Branch coverage | BVA |
| API endpoint | Use Case + EP | Pairwise |
| Scheduler / cron | Use Case (state→run→assert) | Error guessing (idempotency) |
| FE view (Playwright) | Use Case E2E | Error guessing (role gate, 4xx/5xx) |

---

# Phần III — Test Plan (Kế hoạch thực thi)

## III.1. Test Pyramid

```
                  ┌────────────┐
                  │  E2E / UAT │   ~5%
                 ─┴────────────┴─
              ┌──────────────────────┐
              │   API Integration    │   ~15%
             ─┴──────────────────────┴─
          ┌────────────────────────────────┐
          │  Workflow + DocType lifecycle  │   ~25%
         ─┴────────────────────────────────┴─
      ┌────────────────────────────────────────────┐
      │         Unit — Service Layer               │   ~55%
     ─┴────────────────────────────────────────────┴─
```

CLAUDE.md §17: TDD bắt buộc. Hiện tại trọng tâm test thực ở tầng Service unit (`test_imm15.py`).

## III.2. Unit test — Service Layer

File: `assetcore/tests/test_imm15.py`. Lớp test + method **đã tồn tại** (✅ Live) hoặc **chưa viết** (⬜ Planned).

| Test class | Test method | Function cover | Kỹ thuật | Status |
|---|---|---|---|---|
| `TestAllocationLifecycle` | `test_create_requires_work_order_for_non_emergency` | `create_allocation` (VR-15-01) | Decision Table | ✅ Live |
| `TestAllocationLifecycle` | `test_create_emergency_without_wo_succeeds` | `create_allocation` Emergency bypass | Decision Table | ✅ Live |
| `TestAllocationLifecycle` | `test_approve_requires_correct_role` | `approve_allocation` Requested→Approved | State Transition | ✅ Live |
| `TestAllocationLifecycle` | `test_approve_bad_state` | `approve_allocation` re-approve → `BAD_STATE` | State Transition | ✅ Live |
| `TestUrgencyValidation` | `test_invalid_urgency_rejected` | `_vr_05_urgency_valid` (VR-15-05) | EP | ✅ Live |
| `TestWarehouseValidation` | `test_inactive_warehouse_rejected` | `_vr_13_warehouse_active` (VR-15-13) | EP | ✅ Live |
| `TestReturnValidation` | `test_return_qty_exceeds_issued` | `return_items` (VR-15-08) | BVA | ✅ Live |
| `TestForecastGeneration` | `test_generate_forecast` | `generate_spare_forecast` Moving_Avg | Use Case | ✅ Live |
| `TestWatchlist` | `test_add_critical_part_ok` | `add_to_watchlist` happy path | Decision Table | ✅ Live |
| `TestWatchlist` | `test_add_non_critical_rejected` | `add_to_watchlist` (VR-15-09) | Decision Table | ✅ Live |
| `TestDashboardStats` | `test_dashboard_keys` | `get_dashboard_stats` schema | Use Case | ✅ Live |
| `TestDashboardLowStockPerBin` | `test_overview_low_stock_is_per_bin` | low-stock per-bin (regression BUG-15-03) | EP | ✅ Live |
| `TestDashboardLowStockPerBin` | `test_overview_count_matches_stock_page` | dashboard count = stock page | Use Case | ✅ Live |
| — | issue → stock movement + Bin decrement | `issue_allocation` + `_create_stock_movement_for_issue` | Integration | ⬜ Planned |
| — | Emergency dual-approval (VR-15-10) | `issue_allocation` override | Decision Table | ⬜ Planned |
| — | Cycle count variance → root_cause/CAPA (VR-15-04) | `post_cycle_count` + `_seed_capa_for_cycle_variance` | BVA + Decision Table | ⬜ Planned |
| — | `verified_by ≠ counted_by` (VR-15-11) | `post_cycle_count` | Decision Table | ⬜ Planned |
| — | `reorder_point ≥ safety_stock` (VR-15-07) | `generate_spare_forecast` | BVA | ⬜ Planned |
| — | Forecast method whitelist (VR-15-12) | `generate_spare_forecast` | EP | ⬜ Planned |

> Lưu ý: test thực dùng base `TestImm15Base(unittest.TestCase)` tự seed fixture (`AC-WH-TEST15`, `AC-SP-TEST15`) và cleanup ở `tearDownClass` — không dùng `FrappeTestCase` rollback do service tự commit.

## III.3. Integration — DocType lifecycle

File mục tiêu: `tests/test_imm_spare_allocation_doctype.py` ⬜ Planned. Cover hook `validate / before_submit / on_submit`.

| Test | Setup | Action | Assert | Status |
|---|---|---|---|---|
| Allocation insert | seed part + warehouse | `create_allocation()` | `workflow_state == "Requested"`, audit entry | ✅ Live (qua `TestAllocationLifecycle`) |
| Issue → stock movement | Picked allocation, đủ tồn | `issue_allocation()` | `AC Stock Movement` submitted, `stock_movement_ref` set, Bin giảm | ⬜ Planned |
| Cycle count post → adjustment | Counting, variance ≠ 0 | `post_cycle_count()` | `AC Stock Movement (Adjustment)`, Bin = counted_qty | ⬜ Planned |

> RULE-F01..F04 (xem README): IMM DocType chỉ LINK qua `stock_movement_ref`, không ghi thẳng stock → integration test phải verify `AC Stock Movement` submitted, không verify ghi trực tiếp Bin.

## III.4. Integration — Workflow transitions

**Allocation workflow** — `workflow/imm_15_allocation_workflow.json` (12 transitions, đếm: `python3 -c "import json;print(len(json.load(open('assetcore/assetcore/workflow/imm_15_allocation_workflow.json'))['transitions']))"`).

| # | Action | From → To | Role required | Test pass | Test fail |
|---|---|---|---|---|---|
| 1 | Phê duyệt | Requested → Approved | Inventory Manager | ✅ (`test_approve_requires_correct_role`) | ⬜ |
| 2 | Issue (Emergency) | Requested → Issued | Inventory Manager | ⬜ Planned | ⬜ |
| 3 | Hủy | Requested → Cancelled | Inventory Manager | ⬜ Planned | ⬜ |
| 4 | Hủy | Requested → Cancelled | AssetCore Super Admin | ⬜ Planned | ⬜ |
| 5 | Pick | Approved → Picked | Inventory Manager | ⬜ Planned | ⬜ |
| 6 | Hủy | Approved → Cancelled | Inventory Manager | ⬜ Planned | ⬜ |
| 7 | Hủy | Approved → Cancelled | AssetCore Super Admin | ⬜ Planned | ⬜ |
| 8 | Issue | Picked → Issued | Inventory Manager | ✅ (`TestReturnValidation` setup) | ⬜ |
| 9 | Hủy | Picked → Cancelled | Inventory Manager | ⬜ Planned | ⬜ |
| 10 | Hủy | Picked → Cancelled | AssetCore Super Admin | ⬜ Planned | ⬜ |
| 11 | Trả phụ tùng | Issued → Returned | Inventory Manager | ⬜ Planned (return path partial) | ⬜ |
| 12 | Đóng phiếu | Returned → Issued | Inventory Manager | ⬜ Planned | ⬜ |

**Cycle Count workflow** — `workflow/imm_15_cycle_count_workflow.json` (4 transitions).

| # | Action | From → To | Role required | Test pass | Test fail |
|---|---|---|---|---|---|
| 1 | Bắt đầu đếm | Planned → Counting | Inventory Manager | ⬜ Planned | ⬜ |
| 2 | Hoàn tất đếm | Counting → Reviewed | Inventory Manager | ⬜ Planned | ⬜ |
| 3 | Sửa đếm lại | Reviewed → Counting | Inventory Manager | ⬜ Planned | ⬜ |
| 4 | Post | Reviewed → Posted | Inventory Manager | ⬜ Planned | ⬜ |

State Transition Testing: mỗi edge = 1 test pass (đúng role + đúng state) + 1 test fail (sai role / sai state → `BAD_STATE` đã verify ở `test_approve_bad_state`).

## III.5. Integration — Audit chain integrity

`_write_allocation_audit` ghi `IMM Audit Trail` cho mọi mutation (BR-15-10). 2 test chính:
- (a) Sau N mutation (create→approve→issue→return), chain entry tồn tại đầy đủ với đúng `action`/`actor`/`payload`. ⬜ Planned.
- (b) Tamper 1 entry → verify endpoint trả chain broken. ⬜ Planned — *(Cần khảo sát: cơ chế hash chain của `IMM Audit Trail` chưa xác nhận trong source IMM-15)*.

→ Xem 04 Backend §Audit Trail · DocType `IMM Audit Trail`.

## III.6. API test

File mục tiêu: `tests/test_imm15_api.py` ⬜ Planned. Endpoint thực (`api/imm15.py`, 24 whitelisted). Cover: envelope `success=true`, invalid params, FORBIDDEN, pagination, idempotent retry.

| Test | Endpoint | Verify | Status |
|---|---|---|---|
| list envelope | `GET api/imm15.list_allocations` | `{success:true, data:{items, total}}` | ⬜ Planned |
| create missing WO | `POST api/imm15.create_allocation` (Routine, no WO) | `success=false`, `code=BUSINESS_RULE` | ⬜ Planned |
| approve forbidden | `POST api/imm15.approve_allocation` (Inventory User) | `code=FORBIDDEN` | ⬜ Planned |
| watchlist non-critical | `POST api/imm15.add_to_watchlist` (Major part) | `code=VALIDATION` (VR-15-09) | ⬜ Planned |
| availability perf | `GET api/imm15.check_part_availability` | latency P95 (NFR perf) | ⬜ Planned |
| dashboard schema | `GET api/imm15.get_dashboard_stats` | data chứa KPI keys | ✅ Live (qua service `TestDashboardStats`) |

> RBAC server-side: `create/approve/issue` qua `_require_any_role` với capability `inventory.write` (`_CAP_OPERATE`) hoặc `inventory.submit` (`_CAP_APPROVE`) — xem `services/imm15.py:94-95`.

## III.7. E2E browser (Playwright)

Dùng cho flow UI khó cover bằng API: dropdown cascade chọn warehouse/part, modal confirm issue, nút workflow theo role, dashboard realtime KPI. FE views: `frontend/src/views/inventory/` (InventoryDashboardView, StockLevelView, SparePartListView/DetailView, SpareForecastView, WatchlistView, StockMovement* ...). → Xem `assetcore-test` skill Phần 2 (Playwright MCP recipes + R-1..R-9 data rules). Hiện trạng: ⬜ Planned.

## III.8. Performance test

| Metric | Target | Method |
|---|---|---|
| `check_part_availability` p95 | ≤ 300ms | k6 GET `api/imm15.check_part_availability` |
| `list_allocations` 200 row p95 | ≤ 400ms | k6 GET |
| `create_allocation` p95 | ≤ 600ms | k6 POST batch |
| `compute_inventory_kpis` scheduler | ≤ 5min/1000 part | `time bench execute assetcore.services.imm15.compute_inventory_kpis` |

> Target — chưa chạy k6. Số liệu baseline không có; không bịa.

## III.9. Test data & Fixtures

| Loại | Cách seed | File |
|---|---|---|
| Master data (AC UOM, AC Warehouse, AC Spare Part) | fixtures cài qua `bench migrate` | `assetcore/fixtures/` |
| Workflow + Role | `workflow.json`, `role*.json` | `assetcore/fixtures/` |
| Backend test fixture | tự tạo trong `setUpClass` (`AC-WH-TEST15`, `AC-SP-TEST15`, qty 20) | `tests/test_imm15.py` |
| UAT seed | Python script | `assetcore/scripts/uat/uat_imm15.py` — *(Cần khảo sát: chưa xác nhận tồn tại)* |

> Backend test fixture dùng prefix `AC-*-TEST15` và cleanup ở `tearDownClass` (best-effort delete records creation > 2026-05-10) — xem `assetcore-test` R-0/R-1.

## III.10. Run commands & Coverage gate

```bash
# Module test
bench --site [site] run-tests --app assetcore --module assetcore.tests.test_imm15
# Coverage
bench --site [site] run-tests --app assetcore --coverage --module assetcore.tests.test_imm15
# Scheduler jobs (manual trigger)
bench --site [site] execute assetcore.services.imm15.check_critical_spare_breach
bench --site [site] execute assetcore.services.imm15.check_low_stock_and_alert
bench --site [site] execute assetcore.services.imm15.compute_inventory_kpis
bench --site [site] execute assetcore.services.imm15.reclassify_abc
```

| Layer | Target coverage | Đo |
|---|---|---|
| Service (`services/imm15.py`) | ≥ 85% line + ≥ 80% branch *(chưa đo)* | `coverage --branch` |
| DocType lifecycle | ≥ 70% *(chưa đo)* | `coverage report` |
| API (`api/imm15.py`) | ≥ 60% *(chưa đo)* | `coverage report` |
| Frontend (vue-tsc) | 0 error | `npm run build` |

---

# Phần IV — Traceability Matrices

> Mọi test ở Phần III phải xuất hiện ở cả 3 bảng.

## IV.1. US → Test mapping

| US ID | Test ID (III.x) | Layer | Status |
|---|---|---|---|
| US-15-01 | `TestAllocationLifecycle::test_create_requires_work_order_for_non_emergency` + `test_approve_requires_correct_role` | Unit | ✅ Live |
| US-15-01 | issue → stock movement | Integration | ⬜ Planned |
| US-15-02 | `TestAllocationLifecycle::test_create_emergency_without_wo_succeeds` | Unit | ✅ Live (create); override dual-approval ⬜ Planned |
| US-15-03 | cycle count variance → CAPA | Integration | ⬜ Planned |
| US-15-04 | `check_critical_spare_breach` cron | Cron sim | ⬜ Planned |
| US-15-05 | `TestForecastGeneration::test_generate_forecast` | Unit | ✅ Live (generate); `approve_forecast` ⬜ Planned |

## IV.2. BR → Test mapping

| BR/VR ID | Phát biểu (rút gọn) | Test ID | Happy / Negative |
|---|---|---|---|
| VR-15-01 / BR-15-01 | Non-emergency phải link WO | `test_create_requires_work_order_for_non_emergency` (neg) + `test_create_emergency_without_wo_succeeds` (happy) | 1 / 1 ✅ |
| VR-15-05 | urgency enum | `test_invalid_urgency_rejected` | 0 / 1 ✅ (happy ngầm qua các test khác) |
| VR-15-08 | qty_returned ≤ qty_issued | `test_return_qty_exceeds_issued` | 0 / 1 ✅ |
| VR-15-09 | Watchlist Critical-only | `test_add_critical_part_ok` (happy) + `test_add_non_critical_rejected` (neg) | 1 / 1 ✅ |
| VR-15-13 | warehouse active | `test_inactive_warehouse_rejected` | 0 / 1 ✅ |
| BR-15-07 | Forecast generate Draft | `test_generate_forecast` | 1 / 0 ✅ |
| VR-15-02 | traceability batch/serial | — | ⬜ Planned (0 / 0) |
| VR-15-03 | tồn không đủ → block; Emergency bypass | — | ⬜ Planned |
| VR-15-04 / BR-15-05 | variance > ngưỡng → root_cause | — | ⬜ Planned |
| VR-15-07 | reorder ≥ safety | — | ⬜ Planned |
| VR-15-10 | dual-approver khác nhau | — | ⬜ Planned |
| VR-15-11 | verified_by ≠ counted_by | — | ⬜ Planned |
| VR-15-12 | forecast method whitelist | — | ⬜ Planned |
| BR-15-10 | audit trail mọi mutation | — | ⬜ Planned (III.5) |

## IV.3. Component → Test mapping

| Component (I.1) | Test ID | Test layer | Coverage % | Risk priority |
|---|---|---|---|---|
| `create_allocation` (#10) | `TestAllocationLifecycle` (3 test) | Unit | *(chưa đo)* | High |
| `approve_allocation` (#11) | `test_approve_requires_correct_role` / `test_approve_bad_state` | Unit | *(chưa đo)* | Critical |
| `issue_allocation` (#12) | `TestReturnValidation` (setup) | Unit (partial) | *(chưa đo)* | Critical |
| `return_items` (#13) | `test_return_qty_exceeds_issued` | Unit | *(chưa đo)* | Medium |
| `generate_spare_forecast` (#15) | `test_generate_forecast` | Unit | *(chưa đo)* | Medium |
| `add_to_watchlist` (#16) | `TestWatchlist` (2 test) | Unit | *(chưa đo)* | Medium |
| `_vr_05_urgency_valid` (#19) | `test_invalid_urgency_rejected` | Unit | *(chưa đo)* | High |
| `_vr_13_warehouse_active` (#20) | `test_inactive_warehouse_rejected` | Unit | *(chưa đo)* | High |
| `get_dashboard_stats` (#17) | `test_dashboard_keys` + `TestDashboardLowStockPerBin` | Unit | *(chưa đo)* | Low |
| `post_cycle_count` (#14) | — | — | 0% | High ⬜ Planned |
| Workflow transitions (#8, #9) | — (chỉ #1, #8 chạm gián tiếp) | Integration | *(chưa đo)* | Critical ⬜ Planned |
| Scheduler jobs (#24–#29) | — | — | 0% | High ⬜ Planned |

---

# Phần V — UAT Script

## V.1. Phạm vi UAT

- **In-scope**: scenario theo US-15-01..05 + UC-01..08 (V.4), permission matrix, audit verify, scheduler jobs.
- **Out-of-scope**: performance (III.8), security pen-test (Phần VI.10).
- **Pre-condition**: site UAT deploy version `1.0.0-rc.2`, fixture loaded (`bench migrate`), 2 workflow active, tester accounts active, AC Inventory Backbone (Wave 1) LIVE.

## V.2. Tester accounts

| Username | Role | Vai trò UAT |
|---|---|---|
| `uat_inv_user@...` | Inventory User | Tạo allocation, pick, đếm kho |
| `uat_inv_mgr@...` | Inventory Manager | Approve, issue, post cycle count, approve forecast |
| `uat_super@...` | AssetCore Super Admin | Cancel, override, quản trị |
| `uat_auditor@...` | AssetCore Auditor | Read-only — verify FORBIDDEN khi mutate |
| `uat_sysuser@...` | AssetCore System User | Read-only base — verify FORBIDDEN |

> Bắt buộc có account role thấp (Auditor / System User) để cover FORBIDDEN, không chỉ Super Admin.

## V.3. Test data đã seed

| Item | Class | ABC | Min | Tồn đầu | Traceability |
|---|---|---|---|---|---|
| SP-CT-TUBE-01 | Critical | A | 1 | 1 | ☑ |
| SP-MRI-COIL | Critical | A | 1 | 1 | ☑ |
| SP-MON-BAT | Major | B | 6 | 12 | ☐ |
| SP-FILT-01 | Consumable | C | 4 | 10 | ☐ |
| SP-DEF-PAD | Consumable | B | 4 | 2 (low) | ☐ |
| SP-PUMP-SEAL | Major | B | 2 | 0 (out) | ☐ |

Bổ sung: ≥ 2 AC Warehouse (Kho trung tâm, Kho QC Hold), 1 PM WO Approved (IMM-08), 1 CM WO Emergency (IMM-12), Critical Watchlist seed cho CT/MRI. Reset script đi kèm: `assetcore/scripts/uat/` *(Cần khảo sát)*.

## V.4. UAT Scenarios — Suy ra từ US + Use Case

ID `UAT-IMM-15-NN`. Mỗi scenario theo template Phụ lục A.

| ID | Actor | Pre-condition | US/BR cover | Kỹ thuật | Kết quả mong đợi |
|---|---|---|---|---|---|
| UAT-IMM-15-01 | Inventory User | PM WO Approved (IMM-08) | US-15-01 | Use Case happy | SAL tạo, state=Requested, audit trail có ISSUED entry |
| UAT-IMM-15-02 | Inventory Mgr + User | UAT-01 pass | US-15-01 | State Transition | Approve→Pick→Issue; AC Stock Movement tạo, Bin giảm |
| UAT-IMM-15-03 | Inventory User | SP-CT-TUBE-01 (traceability) | VR-15-02 | Decision Table | Thiếu batch → lỗi; có batch → pass |
| UAT-IMM-15-04 | Inventory Mgr + Super Admin | Stock = 0, urgency=Emergency | US-15-02, VR-15-10 | Decision Table | EMERGENCY_OVERRIDE flag, dual-approver khác nhau, email cảnh báo |
| UAT-IMM-15-05 | Inventory User | Issued allocation | UC-05, BR-15-08 | Decision Table | Damaged → QC Hold; Good → kho gốc |
| UAT-IMM-15-06 | Inventory User + Mgr | Variance SP-FILT-01 > 5% | US-15-03, VR-15-04, VR-15-11 | BVA + Decision Table | root_cause bắt buộc, SR tạo, CAPA seed, Bin = counted_qty |
| UAT-IMM-15-07 | Scheduler | Bin CT-TUBE-01 < min | US-15-04, BR-15-04 | Use Case (cron) | Breach alert, CAPA seed, email 3 recipient, idempotent same-day |
| UAT-IMM-15-08 | Inventory Manager | ≥ 6 tháng data | US-15-05, BR-15-07 | Use Case | Forecast Approved → reorder recommendation (Draft không gợi ý) |
| UAT-IMM-15-09 | Inventory User + Mgr | N/A | VR-15-01/05/08/09/13 | EP/BVA | Mỗi VR trả lỗi tiếng Việt đúng |
| UAT-IMM-15-10 | All test users | N/A | RBAC | EP (permission) | FORBIDDEN khi sai role (Auditor/System User mutate) |
| UAT-IMM-15-11 | Scheduler | Manual trigger | scheduler jobs | Use Case | low_stock/breach/KPI/reclassify idempotent + email |
| UAT-IMM-15-12 | Inventory User | PM WO submit (IMM-08) | UC-01 hook | Use Case | `reserve_for_pm` chạy, reserved tăng |
| UAT-IMM-15-13 | All | Post flow | BR-15-10 | Use Case | Mỗi action có IMM Audit Trail entry |
| UAT-IMM-15-14 | Inventory Mgr | Breach event | Dashboard | Use Case | KPI tile reload sau realtime event |

## V.5. Tổng hợp kết quả & Bug found

- **Bảng kết quả**: `Scenario · Status (Pass/Fail/Block) · Tester · Ngày · Ghi chú` — điền khi chạy UAT.
- **Bug list**: `Issue ID · Severity (Blocker/Major/Minor/Trivial) · Mô tả · Fix status`.
- **Acceptance**: ≥ 95% PASS, Blocker = 0, Major ≤ 2 (có workaround). P0 tuyệt đối: UAT-IMM-15-01/04/06/07/13.
- **Sign-off**:

| Role | Tên | Chữ ký | Ngày |
|---|---|---|---|
| BA Lead | | | |
| Dev Lead | | | |
| QA Lead | | | |
| Module Owner (Kho trung tâm) | | | |
| Compliance Manager | | | |

---

# Phần VI — Security Review (gate)

## VI.1. RBAC

- **Role definitions** (`fixtures/role.json` + `role_profile.json`): Inventory Manager, Inventory User, AssetCore Super Admin, AssetCore Auditor, AssetCore System User.
- **DocPerm matrix** (đọc thực từ DocType JSON):

| DocType | Role | Read | Write | Create | Submit | Cancel | Delete |
|---|---|---|---|---|---|---|---|
| IMM Spare Allocation | AssetCore Super Admin | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| IMM Spare Allocation | Inventory Manager | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| IMM Spare Allocation | Inventory User | ✓ | ✓ | ✓ | — | — | — |
| IMM Spare Allocation | AssetCore Auditor | ✓ | — | — | — | — | — |
| IMM Spare Allocation | AssetCore System User | ✓ | — | — | — | — | — |
| IMM Stock Cycle Count | (cùng matrix 5 role như trên) | … | … | … | … | … | … |
| IMM Spare Part Forecast | (cùng matrix 5 role như trên) | … | … | … | … | … | … |
| IMM Critical Spare Watchlist | (cùng matrix 5 role như trên) | … | … | … | … | … | … |

> 4 DocType chính dùng **cùng** ma trận: Super Admin + Inventory Manager full (RWCSXD); Inventory User RWC (không submit/cancel/delete); Auditor + System User chỉ Read. Child table thừa kế quyền parent.

- **Field-level permission**: ⚠️ **Gap** — hiện KHÔNG có field nào đặt `permlevel ≠ 0` trên 4 DocType (xác nhận: không field nào có permlevel trong JSON). Các field nhạy cảm (`total_value`, `override_reason`, `variance_value`) nên đặt permlevel 1 → **TODO trước go-live**.
- **User Permission**: chưa cấu hình filter theo warehouse/department cho IMM-15 — *(Cần khảo sát)*.

Kỹ thuật: Decision Table — mỗi (role × action × state) là 1 row, expected = Allow/Deny.

## VI.2. API security

- **Whitelist hygiene**: 24 endpoint `@frappe.whitelist` ở `api/imm15.py`; mutating endpoint dùng `methods=["POST"]`; service layer gọi `_require_any_role(_CAP_*)` (`inventory.write`/`inventory.submit`).
- **CSRF**: Frappe default `X-Frappe-CSRF-Token` cho POST.
- **Input validation**: Link field (warehouse, spare_part) validate qua `_safe_get_value` / `_vr_13_warehouse_active` trước khi dùng.
- **SQL injection**: dùng `frappe.get_all` / `frappe.db.get_value` parameterized; không f-string vào raw SQL (cần re-verify khi audit).
- **Rate limit**: ⬜ chưa cấu hình cho `create_allocation`/`approve_allocation` — *(Cần khảo sát)*.

## VI.3. Audit trail integrity

Mọi mutation gọi `_write_allocation_audit` → sinh `IMM Audit Trail` (BR-15-10). User KHÔNG có quyền create/edit/delete `IMM Audit Trail` (System only — ISO 13485:7.5.9). Hash chain SHA-256 + tamper verify: *(Cần khảo sát — cơ chế hash chain chưa xác nhận trong source IMM-15)*. → Test ở III.5.

## VI.4. Authentication & session

Login Frappe default; session timeout + lockout + password policy theo cấu hình site; API key rotation; 2FA roadmap. Không có cấu hình riêng IMM-15.

## VI.5. Data sensitivity

| Loại | Trường | Sensitivity | Bảo vệ |
|---|---|---|---|
| Giá trị cấp phát | `total_value` (nếu có) | Internal | **TODO** permlevel 1 (hiện chưa đặt) |
| Lý do override khẩn | `override_reason` / `audit_flags=EMERGENCY_OVERRIDE` | Confidential | Audit trail immutable; **TODO** permlevel |
| Chênh lệch kiểm kê | `variance_value` | Internal | **TODO** permlevel 1 |
| Batch / Serial | traceability fields | Critical (regulatory NĐ98) | Required khi `imm_traceability_required=1` (VR-15-02) |

Khẳng định: IMM-15 **KHÔNG** lưu patient data.

## VI.6. Vendor isolation

IMM-15 không có role Vendor External trong DocPerm (5 role nội bộ). Không có vendor truy cập trực tiếp → không áp dụng `permission_query_conditions` cho vendor ở module này. Nếu mở rộng vendor xem WO-assigned spare → bổ sung sau.

## VI.7. Secrets management

Cấm commit `.env`/credential; `site_config.json` không lên git; external token lưu `frappe.conf`; backup encrypt at-rest off-site. IMM-15 không có secret riêng.

## VI.8. Logging & monitoring

| Sự kiện | Log level | Where | Alert? |
|---|---|---|---|
| Emergency override | INFO + email | IMM Audit Trail + `frappe.sendmail` | ✓ (Inventory Manager + Super Admin) |
| Critical breach | WARN + email | scheduler log + audit | ✓ |
| Service exception | ERROR | Frappe error log | theo dõi |

PII / token KHÔNG vào log.

## VI.9. Threat model (STRIDE)

| Threat | Vector | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| **Spoofing** | Giả mạo approver 2 trong emergency override | Med | High | `session.user` validate server-side; VR-15-10 enforce 2 approver khác nhau |
| **Tampering** | Sửa `qty_issued` sau Issued | Low | High | AC Stock Movement docstatus=1; `stock_movement_ref` read-only sau issue |
| **Repudiation** | Phủ nhận ai override | Med | High | IMM Audit Trail ghi actor + timestamp; immutable (no delete perm) |
| **Info disclosure** | Inventory User xem giá trị nhạy cảm | Med | Med | ⚠️ Gap — permlevel chưa đặt; TODO trước go-live |
| **Denial of service** | Flood `check_part_availability` 1000 item | Low | Med | ⬜ Rate limit chưa cấu hình (TODO) |
| **Elevation of privilege** | Inventory User tự approve | Med | High | `_require_any_role(_CAP_APPROVE)` không cấp cho Inventory User; verify ở III.6 |

## VI.10. Penetration test

Trước release đầu tiên: Burp/ZAP scan, sqlmap (an toàn), CSRF test, role escalation (Inventory User → approve). Report lưu `docs/security/`. Hiện trạng: ⬜ chưa chạy.

## VI.11. Sign-off

| Role | Người | Ngày | Chữ ký |
|---|---|---|---|
| Security Officer | | | |
| QA Lead | | | |
| Module Owner | | | |

Decision: ☐ Pass · ☐ Pass with conditions (permlevel + rate limit) · ☐ Fail (block).

---

# Phần VII — Code Quality

## VII.1. Tool matrix

| Tool | Mục tiêu | Target | Cadence |
|---|---|---|---|
| **SonarQube** (BE Python) | bug 0 critical, code smell ≤ thấp, duplication ≤ 3%, coverage ≥ 70%, security hotspot review 100% | Quality Gate pass | mỗi PR |
| **ruff / black** (`services/imm15.py`, `api/imm15.py`) | 0 error, format consistent | 0 error | mỗi PR |
| **radon** (cyclomatic) | ≤ 10 per function | đạt | mỗi PR |
| **mypy** (type hints) | 100% public function | đạt | mỗi PR |
| **ESLint + vue-tsc** (FE inventory views) | 0 error, 0 warning prod build | 0 error | mỗi PR FE |
| **Lighthouse** (FE) | Performance ≥ 90, Accessibility ≥ 95, Best Practices ≥ 90 | đạt | mỗi release lớn |
| **Bundle size** (FE chunk inventory) | main ≤ 250KB gzip, async ≤ 80KB gzip | đạt | mỗi PR FE |

Lệnh lint BE:

```bash
ruff check assetcore/services/imm15.py assetcore/api/imm15.py
mypy assetcore/services/imm15.py assetcore/api/imm15.py
radon cc assetcore/services/imm15.py -s -n B
```

## VII.2. Cadence

- SonarQube: mỗi PR (CI gate, fail nếu Quality Gate fail).
- Lighthouse: mỗi release lớn + monthly audit.
- ESLint / ruff / mypy: mỗi PR (CI gate).
- Bundle size: mỗi PR FE (CI report, fail nếu vượt budget).

> Gắn screenshot SonarQube + Lighthouse vào `09_Release.md` §Release Notes khi báo cáo final.

---

# Phụ lục A — Template per UAT scenario

```markdown
### UAT-IMM-15-<NN> — <Tên>

**Liên kết**: US-15-<NN>, AC<N>, BR-15-<NN>, UC-<NN>
**Role tester**: <…>
**Kỹ thuật áp dụng**: Use Case happy / Use Case alt / EP permission / State Transition
**Mục tiêu**: <1 câu>
**Pre-condition**: <data state cần có>

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | <…> | <…> | ☐ |
| 2 | <…> | <…> | ☐ |

**Post-condition**: <data state sau khi pass>
**Acceptance**: Tất cả step Pass + IMM Audit Trail có entry tương ứng.
```

# Phụ lục B — Template per Test Case (unit/integration/API)

```markdown
### TC-IMM-15-<LAYER>-<NN> — <Tên>

**Component (I.1)**: <…>
**Liên kết**: US-15-<NN> | BR-15-<NN> | VR-15-<NN>
**Kỹ thuật (II.1/II.2)**: BVA boundary `qty_issued = available_qty + 1`
**Priority (I.3)**: Critical / High / Medium / Low
**Test type**: Unit / Integration / API / E2E
**Pre-condition**: <fixture / state setup>

**Input**:
- <field>: <value>

**Steps**:
1. <…>
2. <…>

**Expected**:
- ServiceError(code=BUSINESS_RULE, message contains "VR-15-03")
- doc.workflow_state unchanged

**Post-condition**: <DB cleanup / fixture cleanup>
```

# Phụ lục C — Workflow State Transition Test template

```markdown
### TC-IMM-15-WF-<NN> — <action>: <from> → <to>

**Workflow JSON**: `assetcore/assetcore/workflow/imm_15_allocation_workflow.json`
**Role required**: <…> (vd Inventory Manager)
**Pre-condition**: doc.workflow_state = <from>
**Action**: apply_workflow(doc, "<action>")
**Expected (happy)**: doc.workflow_state = <to>, audit entry created
**Expected (negative role)**: PermissionError / FORBIDDEN
**Expected (bad state)**: ServiceError(code=BAD_STATE)
```

---

# DoD — File 07 hoàn chỉnh

## I. Test Analysis
- [x] I.1 Component Inventory liệt kê đủ artefact (so với 04/05/06)
- [x] I.2 mỗi US / BR / Use Case có ≥ 1 dòng map
- [x] I.3 Risk priority gán cho mọi component (không trống)
- [x] I.4 Scope ghi rõ out-of-scope kèm lý do

## II. Test Design Techniques
- [x] II.1 chọn ≥ 4 black-box techniques (EP + BVA + Decision Table + State Transition)
- [x] II.2 white-box criteria xác định (statement + branch)
- [x] II.3 mapping component → kỹ thuật điền đầy đủ

## III. Test Plan
- [x] Test class structure cho service public function (I.1) — 9 lớp Live + Planned
- [ ] ≥ 1 happy + 1 negative test mỗi function — *thiếu: post_cycle_count, issue (full), forecast approve, dual-approval VR-15-10*
- [ ] Workflow transitions cover 100% — *chỉ 2/12 alloc + 0/4 cycle count có test chạm; phần lớn ⬜ Planned*
- [ ] Audit chain test (intact + tampered) — *⬜ Planned; cơ chế hash chain cần khảo sát*
- [ ] API test ≥ 60% coverage + permission matrix — *⬜ Planned (chưa có test_imm15_api.py)*
- [x] Performance target xác định (chưa chạy k6)
- [x] CI command chạy clean (`bench run-tests --module …`)
- [ ] **SonarQube Quality Gate pass** + **Lighthouse score** — *chưa chạy*

## IV. Traceability
- [x] IV.1 US → Test: mọi US có ≥ 1 Test ID (US-15-01..05 đều có Live ít nhất 1)
- [ ] IV.2 BR → Test: mọi BR có happy + negative — *6/14 VR đủ; 8 còn lại ⬜ Planned*
- [ ] IV.3 Component → Test: Critical/High đạt coverage target — *coverage chưa đo; workflow + scheduler Critical chưa cover*

## V. UAT
- [x] Mỗi US có ≥ 1 UAT scenario (14 scenario)
- [x] ≥ 1 negative + permission + audit verify scenario (09/10/13)
- [ ] Test data seed script chạy được — *script `scripts/uat/` cần khảo sát*
- [ ] Tester accounts đã tạo ở UAT site — *liệt kê 5 role, chưa xác nhận tạo trên site*
- [x] Sign-off section sẵn sàng

## VI. Security
- [x] DocPerm matrix đầy đủ (đọc thực từ JSON, 5 role)
- [ ] Mọi field nhạy cảm có permlevel ≠ 0 — **GAP: chưa field nào có permlevel; TODO trước go-live**
- [ ] SQL injection + CSRF test pass — *CSRF default Frappe; SQLi cần re-verify khi audit*
- [ ] Audit chain test pass (intact + tampered) — *⬜ Planned*
- [x] Vendor isolation — *N/A: IMM-15 không có role vendor*
- [x] Threat model đủ 6 STRIDE với mitigation
- [ ] Sign-off đầy đủ trước go-live — *bảng sẵn sàng, chưa ký*

## VII. Code Quality
- [ ] SonarQube Quality Gate pass — *chưa chạy*
- [ ] Lighthouse ≥ target — *chưa chạy*
- [ ] Bundle size ≤ budget — *chưa đo*
- [ ] Screenshot báo cáo gắn vào file 09 — *chưa có*

---

*IMM-15 Module — Wave 2 IMPLEMENTED. Testing & QA. Cập nhật 2026-05-29.*
