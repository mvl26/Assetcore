# 07 — Kiểm thử & An ninh (Testing & QA & Security)

| Mục | Giá trị |
|---|---|
| Module | IMM-07 — Theo dõi hiệu suất |
| Phạm vi | Per-module |
| Owner | QA Lead + Security Officer |
| Liên kết | 02 Analysis (US, BR, Activity, BPMN) · 03 Diagrams · 04 Backend · 05 API · 06 Frontend |

> **Mục đích**: Suy ra test case có hệ thống từ phân tích (file 02) bằng kỹ thuật black-box + white-box, không liệt kê tự phát. Bao gồm: phân tích đối tượng test → chọn kỹ thuật → viết test → traceability → UAT → security → code quality. Phần VI (Security Review) là gate go-live.

> **Trạng thái module**: IMM-07 CHƯA scaffold BE/FE (Đợt 3). Tài liệu này là **PLANNING SKELETON** — giữ đủ cấu trúc, điền dữ liệu thật đã có ở 02/04/05/06, các ô chưa thiết kế được đánh dấu `⬜ Planned` hoặc `*(Cần thiết kế khi scaffold BE)*`. KHÔNG fabricate fieldname / endpoint shape / ErrorCode constant / baseline KPI / test-case ID chưa tồn tại trong source.

---

# Phần I — Test Analysis (Phân tích đối tượng test)

> Mục tiêu Phần I: trả lời 4 câu hỏi trước khi viết test case: **(1) test cái gì** (component inventory) **(2) suy ra từ đâu** (US/BR/Activity) **(3) ưu tiên cái nào** (risk) **(4) loại trừ cái nào** (out-of-scope).

## I.1. Component Inventory — Liệt kê phần mềm cần test

Inventory dưới đây lấy từ **kế hoạch** 04/05/06 (BE/FE chưa scaffold). Mỗi dòng → ≥ 1 test class ở Phần III sau khi scaffold. Fieldname, endpoint shape, tên hàm cụ thể chưa chốt → đánh dấu planning.

→ Nguồn: 04 Backend §2 DocType + §4 Service + §4b Repository + §7 Scheduler · 05 API §0 Catalog · 06 Frontend §3-§5

| # | Component | Loại | File / Tên (kế hoạch) | Test layer áp dụng |
|---|---|---|---|---|
| 1 | `AC KPI Catalog` | DocType (master) | `ac_kpi_catalog/ac_kpi_catalog.json` ⬜ Planned | Integration (lifecycle) |
| 2 | `AC KPI Snapshot` | DocType | `ac_kpi_snapshot/ac_kpi_snapshot.json` ⬜ Planned | Integration (lifecycle) |
| 3 | `AC KPI Value` | DocType (child) | `ac_kpi_value/ac_kpi_value.json` ⬜ Planned | Integration (cùng transaction với Snapshot) |
| 4 | `AC Performance Rule` | DocType | `ac_performance_rule/ac_performance_rule.json` ⬜ Planned | Integration + Unit (rule eval) |
| 5 | `AC Replacement Signal` | DocType | `ac_replacement_signal/ac_replacement_signal.json` ⬜ Planned | Integration (lifecycle) |
| 6 | Workflow Snapshot | Workflow | `Draft → Computed → Verified → Closed (+ Reopened)` ⬜ Planned JSON | Integration (state transition) |
| 7 | Workflow Signal | Workflow | `Open → Reviewing → Resolved \| Dismissed` ⬜ Planned JSON | Integration (state transition) |
| 8 | `build_snapshot(period, scope)` | Service function | `services/imm07.py::build_snapshot` ⬜ Planned | Unit + Cron simulation |
| 9 | `verify_snapshot(snapshot, verifier)` | Service function | `services/imm07.py::verify_snapshot` ⬜ Planned | Unit (Decision Table 4-mắt) |
| 10 | `evaluate_rules(snapshot)` | Service function | `services/imm07.py::evaluate_rules` ⬜ Planned | Unit (BVA threshold + dedupe) |
| 11 | `close_signal(signal, resolution)` | Service function | `services/imm07.py::close_signal` ⬜ Planned | Unit (EP resolution) |
| 12 | KPI formula / threshold validator | Validator | `services/imm07.py::_vr*` *(Cần thiết kế khi scaffold BE)* | Unit (BVA/EP/Decision Table) |
| 13 | `load_events(period, scope)` | Repository / DAO | `repositories/imm07_repo.py::load_events` ⬜ Planned | Integration (DB) |
| 14 | `save_snapshot(snapshot)` | Repository / DAO | `repositories/imm07_repo.py::save_snapshot` ⬜ Planned | Integration (atomic insert child) |
| 15 | `find_open_signals(asset)` | Repository / DAO | `repositories/imm07_repo.py::find_open_signals` ⬜ Planned | Integration (dedupe) |
| 16 | 12 API endpoint | API endpoint | `api/imm07.py::*` (xem I.2 không áp dụng — xem III.6) ⬜ Planned | API integration |
| 17 | Lifecycle event hook | Lifecycle event | `hooks.py → AC Lifecycle Event` (`kpi_snapshot_verified`, `replacement_signal_raised`) ⬜ Planned | Integration (audit chain) |
| 18 | Scheduler build snapshot | Scheduler job | `services/imm07.py` daily/weekly/monthly cron *(Cần thiết kế khi scaffold BE)* | Unit + Cron simulation |
| 19 | Cockpit + 6 view FE | FE view / composable | `frontend/src/views/imm07/*.vue` ⬜ Planned | E2E (Playwright) |
| 20 | Pinia store | Pinia store | `frontend/src/stores/imm07.ts` ⬜ Planned | Unit (vitest) |

Endpoint thực tế (verb + path) đã chốt ở 05 §0 — xem bảng III.6.

## I.2. Trace nguồn test — User Stories, Activity Flows, Business Rules

3 bảng dẫn từ artefact phân tích (file 02) sang test layer. User Story và Activity Flow của IMM-07 **chưa được phân tích** (02 §IV.1 và §II.10 còn stub) → để `*(Chờ phân tích)*`. Business Rule đã có (02 §IV.2) → map đầy đủ.

→ Nguồn: 02 §III.3 Use Case · 02 §IV.1 Functional Specs (US + AC, *chờ phân tích*) · 02 §IV.2 Business Rules · 02 §II.10 Activity Diagram (*chờ phân tích*)

### I.2.a. Từ User Story
| US ID | Tiêu đề ngắn | Acceptance Criteria # | Test layer dự kiến |
|---|---|---|---|
| *(Chờ phân tích — 02 §IV.1 stub, BA bổ sung Đợt 3 sprint discovery)* | — | — | — |

UC list đã có (02 §III.3, UC-07-01..07) nhưng chưa tách thành US/AC. Khi 02 §IV.1 hoàn tất, mỗi US phải có ≥ 1 dòng ở đây và xuất hiện ở matrix IV.1.

### I.2.b. Từ Business Rule
| BR ID | Phát biểu | Component liên quan (I.1) | Kỹ thuật test phù hợp |
|---|---|---|---|
| BR-07-01 | Mỗi KPI snapshot phải tham chiếu tập event nguồn xác định (event_ids đóng băng) | `build_snapshot` (#8), `save_snapshot` (#14) | Use Case + EP |
| BR-07-02 | Snapshot `Verified` không được sửa; muốn sửa phải tạo phiên bản mới | Workflow Snapshot (#6), `verify_snapshot` (#9) | State Transition + Error guessing |
| BR-07-03 | Replacement signal chỉ phát khi đủ ≥ 3 chu kỳ liên tiếp vượt ngưỡng | `evaluate_rules` (#10), `AC Performance Rule` (#4) | BVA (biên 2/3/4 chu kỳ) + Decision Table |
| BR-07-04 | Verify cần 4-mắt — người tổng hợp ≠ người duyệt | `verify_snapshot` (#9) | Decision Table (creator vs verifier) |
| BR-07-05 | Mọi thay đổi KPI definition phải qua change control (QMS) | `AC KPI Catalog` (#1) | Use Case + EP (permission) |

### I.2.c. Từ Activity Flow / BPMN
| Activity ID | Use Case | Branch chính | Branch ngoại lệ |
|---|---|---|---|
| *(Chờ phân tích — 02 §II.10 BPMN swimlane chưa vẽ)* | UC-07-01..07 | Happy path | Snapshot `Incomplete` (thiếu nguồn); event đến trễ (`late_arrival`); signal trùng (dedupe) — từ 02 §II.8 + §IV.5 |

Edge case đã liệt kê ở 02 §IV.5 (asset retire giữa kỳ → prorata; event trễ → flag `late_arrival`; thiếu scheduled time → `Incomplete`) sẽ thành path test khi Activity diagram hoàn tất.

## I.3. Risk-based Priority

Đánh giá rủi ro sơ bộ theo kế hoạch (chưa có code đo). Test case priority sẽ khớp risk khi scaffold.

| Component (I.1) | Likelihood (1-5) | Impact (1-5) | Risk = L×I | Priority |
|---|---|---|---|---|
| `verify_snapshot` 4-mắt (#9) — gate đóng kỳ | 3 | 5 | 15 | **Critical** |
| Workflow Snapshot immutable sau Verified (#6) | 3 | 5 | 15 | **Critical** |
| Lifecycle event / audit chain (#17) | 3 | 5 | 15 | **Critical** |
| `build_snapshot` đóng băng event_ids (#8) | 4 | 4 | 16 | **Critical** |
| `evaluate_rules` threshold + dedupe (#10) | 3 | 4 | 12 | High |
| RBAC cross-khoa (KPI khoa A ẩn với khoa B) | 3 | 4 | 12 | High |
| `close_signal` resolution → IMM-13 feed (#11) | 2 | 4 | 8 | Medium |
| `load_events` filter period/scope (#13) | 3 | 3 | 9 | Medium |
| Cockpit read-only view (#19) | 2 | 2 | 4 | Low |

**Quy ước priority**:
- **Critical** (R ≥ 15): test trước, fail = block release
- **High** (10 ≤ R < 15): bắt buộc trước go-live
- **Medium** (5 ≤ R < 10): trong sprint khi có thời gian
- **Low** (R < 5): chỉ test khi báo cáo bug

## I.4. Scope

- **In-scope**: (1) Service layer `build_snapshot` / `verify_snapshot` / `evaluate_rules` / `close_signal` (I.1 #8-11); (2) 2 workflow state machine (#6, #7) cover 100% transition; (3) audit chain integrity (#17); (4) 12 API endpoint envelope + permission (III.6); (5) RBAC cross-khoa (VI.1).
- **Out-of-scope**:
  - Predictive ML model → IMM-17 (02 §I.4 out-of-scope).
  - Recall / FSCA → IMM-10.
  - Quyết định decommissioning cuối → IMM-13/14 (IMM-07 chỉ phát signal); test chỉ verify feed sang IMM-13.
  - Performance test → giao Phần III.8.
  - Security pen-test → giao Phần VI.10.
  - Tích hợp HIS lấy actual usage realtime → open (02 §IV.6), chưa test Đợt 3.
- **Assumptions**: master data (Department, Asset, KPI Catalog) đã seed; `AC Lifecycle Event` từ IMM-04/08/09/11/12 đã có dữ liệu mẫu; test users đủ role (BGĐ/QLCL/Workshop/CNTT); browser Chromium cho Playwright; site Đợt 3 đã `bench migrate` xong scaffold.

---

# Phần II — Test Design Techniques (Kỹ thuật thiết kế test case)

> Mục tiêu Phần II: chọn đúng kỹ thuật cho từng loại input/logic. Mỗi test phải truy được về 1 kỹ thuật ở dưới.

## II.1. Black-box techniques

| Kỹ thuật | Khi nào dùng | Áp dụng vào IMM-07 | Số test sinh ra (rule of thumb) |
|---|---|---|---|
| **Equivalence Partitioning (EP)** | Input có miền giá trị chia nhóm tương đương | `period` (ngày/tuần/tháng/quý), `scope` (asset/model/khoa), resolution (replace/repair/monitor), snapshot status enum | 1 test/partition |
| **Boundary Value Analysis (BVA)** | Numeric / date / length field có biên | Số chu kỳ liên tiếp vượt ngưỡng (BR-07-03: 2/3/4), `period_start < period_end`, lý do dismiss/resolve ≥ 20 ký tự (06 §7e), KPI threshold | 2-3 test/biên: min-1, min, min+1 |
| **Decision Table** | Multi-condition gate, business rule kết hợp | Verify 4-mắt (BR-07-04: creator × verifier × role), rule eval (KPI vượt ngưỡng × đủ N chu kỳ × chưa dedupe) | 2^N rút gọn theo equivalence |
| **State Transition Testing** | Workflow finite state machine | Snapshot `Draft→Computed→Verified→Closed (+Reopened)`; Signal `Open→Reviewing→Resolved\|Dismissed` | Mỗi transition + invalid transition |
| **Use Case Testing** | End-to-end actor flow | UAT scenarios (V.4), API integration test | 1/main flow + 1/alt flow + 1/exception |
| **Pairwise / Combinatorial** | Nhiều field optional kết hợp | Filter cockpit (chu kỳ × khoa × model) | Min set cover all pairs |
| **Error Guessing** | Lỗi từ kinh nghiệm: null, empty, unicode, race | Tất cả endpoint nhận user input; event đến trễ sau khi đóng kỳ; signal trùng | Bổ sung — không thay thế kỹ thuật khác |

## II.2. White-box techniques

| Kỹ thuật | Áp dụng vào | Tiêu chí đạt | Công cụ |
|---|---|---|---|
| **Statement coverage** | Service functions `build_snapshot` / `verify_snapshot` / `evaluate_rules` / `close_signal` | ≥ 70% line (CONVENTIONS §6, mục tiêu IMM-07) | `coverage report` |
| **Branch / Decision coverage** | Hàm có if/else, try/except (verify gate, rule loop) | ≥ 70% branch (mục tiêu — chốt khi scaffold) | `coverage --branch` |
| **Condition / MC/DC** | Verify 4-mắt + rule multi-AND (vượt ngưỡng AND đủ N chu kỳ AND chưa dedupe) | Mỗi sub-condition kiểm soát outcome độc lập | Manual test design + coverage |
| **Path coverage** | `evaluate_rules` loop chu kỳ (loop = 0,1,N) | Toàn bộ path khả dĩ | Manual |

Ưu tiên Branch coverage cho service layer; MC/DC chỉ áp dụng vào verify gate + rule eval.

## II.3. Mapping Component → Kỹ thuật

| Loại component | Kỹ thuật chính | Kỹ thuật phụ |
|---|---|---|
| Field validator (`_vr*`) | BVA + EP | Error guessing |
| Verify gate / rule eval | Decision Table | MC/DC |
| Workflow transition (Snapshot, Signal) | State Transition | Use Case |
| Service function (`build_snapshot`, `close_signal`) | EP + Branch coverage | BVA |
| API endpoint | Use Case + EP | Pairwise (filter input) |
| Scheduler (daily/weekly/monthly build) | Use Case (state setup → run → assert) | Error guessing (lock, partial fail) |
| FE view (Playwright) | Use Case end-to-end | Error guessing (network 4xx/5xx, role gate) |

---

# Phần III — Test Plan (Kế hoạch thực thi)

## III.1. Test Pyramid

Tỷ lệ kế hoạch (di trú từ skeleton cũ §I.1, điều chỉnh theo template 4 tầng):

```
                  ┌────────────┐
                  │  E2E / UAT │   ~10%
                 ─┴────────────┴─
              ┌──────────────────────┐
              │   API Integration    │   ~15%
             ─┴──────────────────────┴─
          ┌────────────────────────────────┐
          │  Workflow + DocType lifecycle  │   ~25%
         ─┴────────────────────────────────┴─
      ┌────────────────────────────────────────────┐
      │         Unit — Service Layer               │   ~50%
     ─┴────────────────────────────────────────────┴─
```

→ CLAUDE.md §17 (TDD mandatory). Coverage target service > 50 LOC: ≥ 70% (CONVENTIONS §6).

## III.2. Unit test — Service Layer

File dự kiến: `assetcore/tests/test_imm07.py` (chưa tồn tại — tạo khi scaffold). Mỗi test class trace về ≥ 1 dòng I.1. Test-case ID cụ thể chưa sinh (không fabricate).

| Test class | Function cover | Kỹ thuật | Cases (happy/negative) |
|---|---|---|---|
| `TestBuildSnapshot` ⬜ Planned | `services/imm07.py::build_snapshot` (#8) | EP + Error guessing | happy / thiếu event nguồn / chu kỳ chồng lấp |
| `TestVerifySnapshot` ⬜ Planned | `services/imm07.py::verify_snapshot` (#9) | Decision Table (BR-07-04) | pass 4-mắt / fail same-user |
| `TestEvaluateRules` ⬜ Planned | `services/imm07.py::evaluate_rules` (#10) | BVA (BR-07-03) + Decision Table | đủ N chu kỳ / chưa đủ / dedupe signal |
| `TestCloseSignal` ⬜ Planned | `services/imm07.py::close_signal` (#11) | EP | resolution hợp lệ / thiếu lý do |
| `TestKpiValidators` ⬜ Planned | `services/imm07.py::_vr*` (#12) | BVA + EP | formula valid / threshold dương / `period_start < period_end` |

Dùng `SimpleNamespace` cho test thuần công thức KPI (không DB) — chạy ms-level.

## III.3. Integration — DocType lifecycle

File dự kiến: `assetcore/tests/test_<doctype>_doctype.py`. Cover hook `validate / before_save / on_submit / on_update_after_submit / on_cancel`. Field detail chưa thiết kế → assert chưa cụ thể hóa được.

| Test | Setup | Action | Assert | Kỹ thuật |
|---|---|---|---|---|
| Snapshot + child KPI Value atomic ⬜ Planned | seed Asset + Lifecycle Event 1 chu kỳ | `doc.insert()` | child `AC KPI Value` lưu cùng transaction | EP |
| Signal link đúng asset + rule ⬜ Planned | seed rule MTBF-DROP + asset suy giảm | tạo signal từ `evaluate_rules` | signal.asset + signal.rule khớp | EP |
| Audit event sinh mỗi state change ⬜ Planned | seed snapshot Computed | verify → close | `AC Lifecycle Event` sinh đúng event_type | Use Case |

Fixture trong `setUpClass` phải có `tearDownClass` purge — xem skill `assetcore-test`.

## III.4. Integration — Workflow transitions

File dự kiến: `assetcore/tests/test_imm07_workflow.py`. Bắt buộc cover mọi transition trong workflow JSON khi scaffold (đếm bằng `python3 -c "import json; print(len(json.load(open('<wf>.json'))['transitions']))"`). Role required chưa chốt với DocPerm → `*(Cần thiết kế khi scaffold BE)*`.

**Workflow Snapshot** (`Draft → Computed → Verified → Closed` + `Reopened`):

| Transition | From → To | Role required | Test pass | Test fail (wrong role / gate fail) |
|---|---|---|---|---|
| Compute | Draft → Computed | System (scheduler) ⬜ | ☐ | ☐ |
| Verify | Computed → Verified | QLCL (4-mắt, BR-07-04) ⬜ | ☐ | ☐ (creator==verifier → reject) |
| Close | Verified → Closed | QLCL ⬜ | ☐ | ☐ |
| Reopen | Verified → Reopened | QLCL only ⬜ | ☐ | ☐ (role khác → FORBIDDEN) |

**Workflow Signal** (`Open → Reviewing → Resolved | Dismissed`):

| Transition | From → To | Role required | Test pass | Test fail |
|---|---|---|---|---|
| Review | Open → Reviewing | QLCL ⬜ | ☐ | ☐ |
| Resolve | Reviewing → Resolved | QLCL ⬜ | ☐ | ☐ (thiếu resolution) |
| Dismiss | Reviewing → Dismissed | QLCL ⬜ | ☐ | ☐ (thiếu lý do ≥ 20 ký tự) |

Kỹ thuật: State Transition Testing — vẽ state graph khi workflow JSON chốt; mỗi edge = 1 test pass + 1 test fail. Tổng transition kế hoạch: **7** (4 Snapshot + 3 Signal) — số thực chốt khi scaffold.

## III.5. Integration — Audit chain integrity

2 test chính (di trú từ skeleton cũ §I.6):
- (a) Sau N mutation (verify/close snapshot, resolve/dismiss signal), chuỗi `AC Lifecycle Event` không đứt gãy; nếu BE dùng hash chain SHA-256 thì verify hợp lệ end-to-end.
- (b) Khi 1 entry bị tamper, verify endpoint trả `chain_broken=true`. *(Cơ chế hash chain cụ thể cần thiết kế khi scaffold BE — 04 §6 mới nêu immutable `verified_by`/`verified_at`, chưa nêu hash.)*

→ 04 Backend §6 Audit Trail · `AC Lifecycle Event` DocType. III.5 này là nguồn cho VI.3.

## III.6. API test

File dự kiến: `assetcore/tests/test_imm07_api.py`. 12 endpoint đã chốt verb + path ở 05 §0. Request/response body chưa chốt → assert field cụ thể là planning.

Cover (di trú smoke test cũ §I.7): Happy path + envelope `success=true` · Auth required (401 khi thiếu) · No permission → `code=PERMISSION_DENIED` (403) · Pagination (endpoint #5, #9) · Idempotent retry (lock theo `(scope, period)` — 05 §6).

| # | Test | Endpoint (05 §0) | Verify | Kỹ thuật |
|---|---|---|---|---|
| 1 | build snapshot happy ⬜ | POST `api/imm07.build_snapshot` | `success=true`, snapshot Computed | Use Case |
| 2 | verify 4-mắt fail same-user ⬜ | POST `api/imm07.verify_snapshot` | `code=VALIDATION_ERROR` (BR-07-04) | Decision Table |
| 3 | reopen by non-QLCL ⬜ | POST `api/imm07.reopen_snapshot` | `code=PERMISSION_DENIED` | EP (permission partition) |
| 4 | get snapshot + values ⬜ | GET `api/imm07.get_snapshot` | envelope + KPI values + event_ids | Use Case |
| 5 | list snapshots pagination ⬜ | GET `api/imm07.list_snapshots` | page/page_size boundary | BVA |
| 6 | KPI timeseries ⬜ | GET `api/imm07.get_kpi_timeseries` | series đúng KPI/scope | EP |
| 7 | cockpit aggregate ⬜ | GET `api/imm07.get_cockpit` | hero metrics + heatmap | Use Case |
| 8 | evaluate rules manual ⬜ | POST `api/imm07.evaluate_rules` | signal phát khi vượt ngưỡng | Decision Table |
| 9 | list signals filter ⬜ | GET `api/imm07.list_signals` | filter status/khoa | EP |
| 10 | resolve signal ⬜ | POST `api/imm07.resolve_signal` | `success=true`, feed IMM-13 | Use Case |
| 11 | dismiss signal thiếu lý do ⬜ | POST `api/imm07.dismiss_signal` | `code=VALIDATION_ERROR` (< 20 ký tự) | BVA |
| 12 | export report PDF ký số ⬜ | POST `api/imm07.export_report` | PDF có chữ ký số | Use Case |
| 13 | cross-khoa isolation ⬜ | GET `api/imm07.get_cockpit` (Workshop khoa A) | KHÔNG thấy KPI khoa B | EP (permission) |

ErrorCode chính xác chốt khi scaffold (05 §1.3 mới reference `services/shared/constants.py` ErrorCode enum, chưa định nghĩa code riêng IMM-07).

## III.7. E2E browser (Playwright)

Dùng cho flow UI khó cover bằng API: filter cascade Khoa→Phòng→Vị trí→Asset (06 §7d), drill-down 1-click snapshot → event nguồn (modal `EventDrillDownDialog.vue`), workflow button visibility theo role (Verify/Reopen chỉ QLCL).

→ skill `assetcore-test` Phần 2 (Playwright MCP recipes + R-1..R-9 data rules). Test E2E viết khi FE scaffold (06 chưa build).

## III.8. Performance test

| Metric | Target | Method |
|---|---|---|
| Build snapshot 5.000 asset / chu kỳ tháng | ≤ 5 phút (NFR §V.1) | `time bench execute assetcore.services.imm07.build_snapshot` |
| Cockpit query KPI 12 tháng p95 | ≤ 2 giây (NFR §V.1) | k6 GET `api/imm07.get_cockpit` |
| List snapshot 200 row p95 | ≤ 400ms (target chung) | k6 GET `api/imm07.list_snapshots` |

## III.9. Test data & Fixtures

| Loại | Cách seed | File |
|---|---|---|
| Master data (Department, Asset, KPI Catalog) | `fixtures/*.json` (cài qua `bench migrate`) | `assetcore/fixtures/` |
| Test records | `test_records.json` per DocType (khi scaffold) | `<doctype>/test_records.json` ⬜ Planned |
| Fixture module | 50 asset / 3 khoa · 6 chu kỳ tháng lifecycle event · KPI catalog 8 KPI · rule mẫu (MTBF-DROP, DOWNTIME-SPIKE) | `assetcore/tests/fixtures/imm07/` ⬜ Planned (Đợt 3 sprint 1) |
| UAT seed | Python script | `assetcore/scripts/uat/uat_imm07.py` ⬜ Planned |

UAT data phải thực tế (tên bệnh viện VN, mã NCC chuẩn). Backend test fixture mới dùng prefix `_Test` — xem skill `assetcore-test` R-0/R-1.

## III.10. Run commands & Coverage gate

```bash
# Module test (sau khi scaffold)
bench --site <site> run-tests --app assetcore --module assetcore.tests.test_imm07
# Coverage
coverage run -m unittest assetcore.tests.test_imm07 && coverage report
# Workflow smoke
bench --site <site> run-tests --module assetcore.tests.test_imm07_workflow
# API smoke
bench --site <site> run-tests --module assetcore.tests.test_imm07_api
```

| Layer | Target coverage | Đo |
|---|---|---|
| Service (`services/imm07.py`) | ≥ 70% line (CONVENTIONS §6) | `coverage --branch` |
| DocType lifecycle | ≥ 70% (target) | `coverage report` |
| API (`api/imm07.py`) | ≥ 60% (target) | `coverage report` |
| Frontend (vue-tsc) | 0 error | `npm run build` |

Coverage % thực tế chỉ điền sau khi có code chạy (không fabricate). CI fail nếu coverage service giảm dưới target.

---

# Phần IV — Traceability Matrices

> 3 ma trận theo 3 hướng. Mọi test ở Phần III phải xuất hiện ở cả 3 bảng (audit ngược: thiếu cover US? BR? component nào?). Vì module chưa scaffold, cột Status = `⬜ Planned`, Coverage % để trống cho tới khi có code.

## IV.1. US → Test mapping

| US ID | AC | Test ID (III.x) | Layer | Status |
|---|---|---|---|---|
| *(Chờ phân tích — 02 §IV.1 stub)* | — | — | — | ⬜ Planned |

DoD: mọi US trong 02 §Functional Specs có ≥ 1 dòng — hiện 02 §IV.1 chưa có US nào (BA bổ sung Đợt 3 sprint discovery), nên bảng này trống hợp lệ ở trạng thái skeleton.

## IV.2. BR → Test mapping

| BR ID | Phát biểu (rút gọn) | Test ID | Kỹ thuật | Happy / Negative |
|---|---|---|---|---|
| BR-07-01 | event_ids đóng băng theo snapshot | `TestBuildSnapshot` ⬜ | EP | 1 / 1 (thiếu event) |
| BR-07-02 | Snapshot Verified bất biến | `TestVerifySnapshot` + workflow ⬜ | State Transition | 1 / 1 (sửa sau verify → reject) |
| BR-07-03 | Signal chỉ phát khi ≥ 3 chu kỳ liên tiếp | `TestEvaluateRules` ⬜ | BVA + Decision Table | 1 / 2 (2 chu kỳ → không phát; dedupe) |
| BR-07-04 | Verify 4-mắt (creator ≠ verifier) | `TestVerifySnapshot` ⬜ | Decision Table | 1 / 1 (same-user → fail) |
| BR-07-05 | KPI definition đổi qua change control | `AC KPI Catalog` perm test ⬜ | EP (permission) | 1 / 1 (role thấp → FORBIDDEN) |

DoD: mọi BR có ≥ 1 happy + ≥ 1 negative test. BR-07-03 (Critical) có Decision Table đầy đủ. Test ID cụ thể sinh khi scaffold.

## IV.3. Component → Test mapping

| Component (I.1) | Test ID | Test layer | Coverage % | Risk priority (I.3) |
|---|---|---|---|---|
| `services/imm07::build_snapshot` (#8) | `TestBuildSnapshot` ⬜ | Unit | *(Cần khảo sát — chưa có code)* | Critical |
| `services/imm07::verify_snapshot` (#9) | `TestVerifySnapshot` ⬜ | Unit | *(Cần khảo sát)* | Critical |
| `services/imm07::evaluate_rules` (#10) | `TestEvaluateRules` ⬜ | Unit | *(Cần khảo sát)* | High |
| `services/imm07::close_signal` (#11) | `TestCloseSignal` ⬜ | Unit | *(Cần khảo sát)* | Medium |
| Workflow Snapshot (#6) | `test_imm07_workflow` ⬜ | Integration | *(Cần khảo sát)* | Critical |
| Audit chain (#17) | `test_imm07` audit ⬜ | Integration | *(Cần khảo sát)* | Critical |
| `api/imm07::*` (#16) | `test_imm07_api` ⬜ | API | *(Cần khảo sát)* | High |

DoD: mọi component Critical/High phải đạt coverage target III.10 khi có code. Coverage % chỉ điền khi `coverage report` chạy thực.

---

# Phần V — UAT Script

## V.1. Phạm vi UAT

- **In-scope**: end-to-end từ lifecycle event đầu vào → snapshot → verify → cockpit → replacement signal → báo cáo ký số (scenario theo V.4).
- **Out-of-scope**: performance (đã làm III.8), security pen-test (Phần VI), predictive ML (IMM-17).
- **Pre-condition**: site UAT deploy version Đợt 3 (chưa có — `*(Cần khảo sát khi release)*`), fixture loaded (III.9), tester accounts active (V.2).

## V.2. Tester accounts

| Username | Role | Vai trò UAT |
|---|---|---|
| `qlcl@hospital.test` | QLCL | Verifier snapshot, xử lý signal, admin catalog/rule |
| `workshop@hospital.test` | Workshop | Submitter event, đối soát downtime (chỉ khoa của mình) |
| `bgd@hospital.test` | BGĐ | Viewer cockpit (read-only), duyệt replacement signal |
| `cntt@hospital.test` | CNTT/Admin | Bảo trì pipeline, build snapshot manual |

Phải có account role thấp (Workshop) để cover FORBIDDEN / cross-khoa case (không chỉ Admin).

## V.3. Test data đã seed

| DocType | Số lượng | Ghi chú |
|---|---|---|
| Asset | 50 | phân 3 khoa (cover cross-khoa RBAC) |
| AC Lifecycle Event | 6 chu kỳ tháng | event PM/CM/Calibration giả lập |
| AC KPI Catalog | 8 KPI | mặc định (availability, utilization, downtime, MTBF, MTTR, PM compliance, data completeness, replacement lead time) |
| AC Performance Rule | 2 | MTBF-DROP, DOWNTIME-SPIKE |

Reset script đi kèm: `assetcore/scripts/uat/uat_imm07.py` ⬜ Planned (Đợt 3 sprint 1). Chi tiết §III.9.

## V.4. UAT Scenarios — Suy ra từ US + Activity

Mỗi scenario theo template §Phụ lục A. ID `UAT-IMM-07-NN`. US/Activity chưa phân tích → scenario suy từ UC (02 §III.3) + BR (02 §IV.2); cột "US/BR cover" link tới BR thật, US để `*(chờ phân tích)*`.

**Quy tắc suy scenarios** (Use Case Testing): mỗi UC → ≥ 1 happy; mỗi exception (02 §II.8/§IV.5) → ≥ 1 scenario; mỗi role mutate → ≥ 1 permission verify; mỗi terminal transition → ≥ 1 audit verify; ≥ 1 negative per BR Critical.

| ID | Actor | Pre-condition | US/BR cover | Kỹ thuật | Kết quả mong đợi |
|---|---|---|---|---|---|
| UAT-IMM-07-01 | Workshop | event PM/CM trong tháng đã nhập | UC-07-01, BR-07-01 | Use Case happy | scheduler chạy → snapshot Computed, event_ids đóng băng |
| UAT-IMM-07-02 | QLCL | snapshot Computed (creator ≠ QLCL) | UC-07-02, BR-07-02/04 | State Transition | snapshot Verified, KHÔNG cho sửa sau verify |
| UAT-IMM-07-03 | QLCL | snapshot Computed do chính mình tạo | BR-07-04 negative | Decision Table | verify bị từ chối (4-mắt) |
| UAT-IMM-07-04 | BGĐ | snapshot Verified | UC-07-03/07 | Use Case happy | cockpit thấy KPI cập nhật + drill-down event nguồn |
| UAT-IMM-07-05 | System/QLCL | asset MTBF giảm 3 chu kỳ liên tiếp | UC-07-04, BR-07-03 | BVA | signal phát; 2 chu kỳ → KHÔNG phát |
| UAT-IMM-07-06 | QLCL | signal Open | UC-07-05 | Use Case happy | Resolve = Replace → feed IMM-13; audit entry |
| UAT-IMM-07-07 | QLCL | signal Open | UC-07-05 negative | BVA | Dismiss thiếu lý do < 20 ký tự → chặn |
| UAT-IMM-07-08 | QLCL | snapshot Verified | UC-07-06 | Use Case happy | export báo cáo tháng PDF có chữ ký số hợp lệ |
| UAT-IMM-07-09 | Workshop (khoa A) | KPI khoa A + B đã seed | NFR §V.2 RBAC | EP permission | KHÔNG thấy KPI khoa B |

## V.5. Tổng hợp kết quả & Bug found

- Bảng kết quả: `Scenario · Status (Pass/Fail/Block) · Tester · Ngày · Ghi chú` — *(Cập nhật mỗi vòng UAT Đợt 3 sprint 4)*.
- Bug list: `Issue ID · Severity (Blocker/Major/Minor/Trivial) · Mô tả · Fix status` — *(Cập nhật mỗi vòng UAT)*.
- Acceptance: ≥ 95% PASS, Blocker = 0, Major ≤ 2 (có workaround).
- Sign-off: BA Lead + QA Lead + Module Owner (PTP Khối 2 + Tổ HC-QLCL) + End-user (BGĐ/QLCL).

---

# Phần VI — Security Review (gate)

## VI.1. RBAC

- **Role definitions**: `fixtures/role.json` + `role_profile.json` — role IMM-07: BGĐ, QLCL, Workshop, CNTT/Admin (02 §I.3).
- **DocPerm matrix per DocType**: chưa chốt vì DocType chưa scaffold; ma trận hành vi (di trú từ skeleton cũ §III.1) làm cơ sở Decision Table:

| Role | Read | Build snapshot | Verify | Resolve signal | Admin catalog/rule |
|---|---|---|---|---|---|
| BGĐ | ✓ | ✗ | ✗ | ✗ (chỉ duyệt) | ✗ |
| QLCL | ✓ | ✓ (manual) | ✓ | ✓ | ✓ |
| Workshop | ✓ (khoa của mình) | ✗ | ✗ | ✗ | ✗ |
| CNTT/Admin | ✓ | ✓ | ✗ | ✗ | ✓ |

DocPerm (Read/Write/Create/Submit/Cancel/Amend/User Permission/Match field) per DocType — *(Cần thiết kế khi scaffold BE, refer skill assetcore-audit security)*.
- **Field-level permission**: field nhạy cảm (chi phí internal nếu có trong KPI value, `verified_by`) cần permlevel ≠ 0 — *(Cần thiết kế khi scaffold BE)*.
- **User Permission**: filter row theo khoa (Workshop chỉ thấy KPI khoa mình) qua `permission_query_conditions` / User Permission trên Department.

Kỹ thuật: Decision Table — mỗi (role × action × state) là 1 row, expected = Allow/Deny.

## VI.2. API security

- **Whitelist hygiene**: mọi `@frappe.whitelist` của `api/imm07.py` có docstring + check permission + validate input (05 §3 CONVENTIONS).
- **CSRF**: Frappe default `X-Frappe-CSRF-Token`.
- **Input validation**: Link field (asset, scope, rule) validate qua `frappe.get_value` trước khi dùng.
- **SQL injection**: parameterized only trong `imm07_repo.py`; không f-string vào raw SQL khi query `AC Lifecycle Event`.
- **Rate limit**: `build_snapshot`, `evaluate_rules`, `export_report` lock 1 request đồng thời cho cùng `(scope, period)` qua `frappe.cache().lock` (05 §6).

## VI.3. Audit trail integrity

Mọi chuyển trạng thái Snapshot/Signal sinh `AC Lifecycle Event` (event_type: `kpi_snapshot_verified`, `replacement_signal_raised`, …). `verified_by` + `verified_at` immutable sau khi set (04 §6, BR-07-02). User KHÔNG có quyền edit/delete `AC Lifecycle Event` (DocPerm + `on_trash` guard, ISO 13485:7.5.9). Cơ chế hash chain SHA-256 (nếu áp dụng) — *(Cần thiết kế khi scaffold BE)*.

→ III.5 test cases (intact + tampered).

## VI.4. Authentication & session

Login Frappe v15 default. Session timeout + lockout + password policy theo cấu hình site. API key rotation theo chính sách CNTT. 2FA: roadmap (chưa Đợt 3).

## VI.5. Data sensitivity

| Loại | Trường | Sensitivity | Bảo vệ |
|---|---|---|---|
| KPI vận hành | availability, utilization, downtime, MTBF, MTTR | Internal | RBAC + cross-khoa filter |
| Audit | `verified_by`, `verified_at` | Internal | immutable, permlevel review |
| Báo cáo ký số | PDF export | Confidential | chữ ký số + RBAC export |

Khẳng định: IMM-07 KHÔNG lưu patient data (module thuần vận hành thiết bị — 02 §I.6).

## VI.6. Vendor isolation

IMM-07 không có actor Vendor External trong scope (02 §I.3 actor toàn nội viện). Nếu Đợt sau mở vendor xem KPI thiết bị họ bảo trì: chỉ thấy asset assigned qua `permission_query_conditions`, KHÔNG thấy chi phí / audit khoa khác / cockpit toàn viện, KHÔNG export. → test ở III.6 #13 (cross-khoa isolation làm mẫu pattern).

## VI.7. Secrets management

Cấm commit `.env` / credential. `site_config.json` không lên git. Token ký số báo cáo lưu `frappe.conf`. Backup encrypt at-rest off-site.

## VI.8. Logging & monitoring

| Sự kiện | Log level | Where | Alert? |
|---|---|---|---|
| Scheduler build snapshot fail (sau 3 retry) | ERROR | Frappe error log | Có → CNTT (NFR §V.3) |
| Verify 4-mắt vi phạm | WARNING | error log | Không |
| Signal phát | INFO | `AC Lifecycle Event` | Không |
| Export báo cáo ký số | INFO | audit | Không |

PII / token KHÔNG vào log (module không có PII).

## VI.9. Threat model (STRIDE-lite)

| Threat | Vector | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| **S**poofing | Giả role QLCL để verify | Thấp | Cao | Frappe auth + DocPerm + RBAC matrix VI.1 |
| **T**ampering | Sửa snapshot Verified / audit event | TB | Cao | immutable sau verify (BR-07-02), audit chain VI.3, on_trash guard |
| **R**epudiation | QLCL phủ nhận đã verify | Thấp | TB | `verified_by` + `verified_at` immutable, lifecycle event |
| **I**nfo disclosure | Workshop khoa A xem KPI khoa B | TB | TB | User Permission theo Department, cross-khoa test III.6 #13 |
| **D**enial of service | build_snapshot lock / N+1 trên 5.000 asset | TB | TB | rate limit `(scope, period)` lock (05 §6), query partition theo `period_end` |
| **E**levation of privilege | Workshop gọi `verify_snapshot` / `build_snapshot` | TB | Cao | check permission trong API + service; test III.6 #3 |

## VI.10. Penetration test

Trước release đầu tiên (Đợt 3 sprint 4): Burp/ZAP scan, sqlmap (an toàn) trên endpoint list/query, CSRF test, role escalation (Workshop → QLCL action). Report lưu `docs/security/imm07_pentest.md` ⬜ Planned.

## VI.11. Sign-off

| Role | Người | Ngày | Chữ ký |
|---|---|---|---|
| Security Officer | *(Cần khảo sát khi release)* | | |
| QA Lead | *(Cần khảo sát khi release)* | | |
| Module Owner (PTP Khối 2) | *(Cần khảo sát khi release)* | | |

Decision: Pass / Pass with conditions / Fail (block) — quyết khi UAT + pen-test xong.

---

# Phần VII — Code Quality

## VII.1. Tool matrix

| Tool | Mục tiêu | Target | Cadence |
|---|---|---|---|
| **SonarQube** (BE Python) | bug, code smell, duplication, coverage, security hotspot | 0 critical bug · code smell ≤ ngưỡng project · duplication ≤ 3% · coverage ≥ 70% · hotspot review 100% | Mỗi PR (CI gate) |
| **ruff / black** (BE Python) | lint + format | 0 error, format consistent | Mỗi PR (CI gate) |
| **mypy** (service layer) | type check | strict, 0 error (di trú skeleton cũ §I.12) | Mỗi PR |
| **ESLint + vue-tsc** (FE) | lint + type | 0 error, 0 warning trên prod build | Mỗi PR |
| **Lighthouse** (FE cockpit) | Perf/A11y/BP/SEO | Performance ≥ 90 · Accessibility ≥ 95 · Best Practices ≥ 90 · SEO ≥ 80 | Mỗi release lớn + monthly |
| **Bundle size** (chunk imm07) | budget | main ≤ 250KB gzip · async ≤ 80KB gzip | Mỗi PR FE (CI report) |

Số liệu thực tế (coverage %, score) chỉ điền khi có code chạy — không fabricate.

## VII.2. Cadence

- SonarQube: mỗi PR (CI gate, fail nếu Quality Gate fail).
- Lighthouse: mỗi release lớn + monthly audit.
- ESLint / ruff / mypy: mỗi PR (CI gate).
- Bundle size: mỗi PR FE (CI report, fail nếu vượt budget).

Gắn screenshot SonarQube + Lighthouse vào file 09 §Release Notes khi báo cáo final.

---

# Phụ lục A — Template per UAT scenario

```markdown
### UAT-IMM-07-<NN> — <Tên>

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
### TC-IMM-07-<LAYER>-<NN> — <Tên>

**Component (I.1)**: <…>
**Liên kết**: US-<NN> | BR-<NN> | ACT-<NN>
**Kỹ thuật (II.1/II.2)**: BVA boundary <field>=<value>
**Priority (I.3)**: Critical / High / Medium / Low
**Test type**: Unit / Integration / API / E2E
**Pre-condition**: <fixture / state setup>

**Input**:
- <field>: <value>

**Steps**:
1. <…>
2. <…>

**Expected**:
- ServiceError(code=<…>, message contains "<…>")
- doc.workflow_state unchanged

**Post-condition**: <DB rollback / fixture cleanup>
```

# Phụ lục C — Workflow State Transition Test template

```markdown
### TC-IMM-07-WF-<NN> — <action>: <from> → <to>

**Workflow JSON**: `<path>.json`
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
- [x] I.1 Component Inventory liệt kê đủ artefact (đối chiếu kế hoạch 04/05/06; đánh dấu ⬜ Planned vì chưa scaffold)
- [ ] I.2 mỗi US / BR / Activity có ≥ 1 dòng map — BR đầy đủ, nhưng US (02 §IV.1) + Activity (02 §II.10) còn stub → chờ phân tích Đợt 3
- [x] I.3 Risk priority gán cho mọi component (không trống)
- [x] I.4 Scope ghi rõ out-of-scope kèm lý do

## II. Test Design Techniques
- [x] II.1 chọn ≥ 4 black-box techniques (EP + BVA + Decision Table + State Transition + Use Case + Pairwise + Error guessing)
- [x] II.2 white-box criteria xác định (statement + branch)
- [x] II.3 mapping component → kỹ thuật điền đầy đủ

## III. Test Plan
- [ ] Test class structure cho mọi service public function — đã liệt kê plan, nhưng `services/imm07.py` chưa tồn tại → chờ scaffold Đợt 3
- [ ] ≥ 1 happy + 1 negative test mỗi function — đã thiết kế bảng, chưa viết code
- [ ] Workflow transitions cover 100% — liệt kê 7 transition kế hoạch, workflow JSON chưa tồn tại để đếm
- [ ] Audit chain test (intact + tampered) — đã thiết kế, cơ chế hash chưa chốt BE
- [ ] API test ≥ 60% coverage + permission matrix — endpoint catalog có, code chưa có
- [x] Performance target xác định (NFR §V.1)
- [ ] CI command chạy clean — module chưa tồn tại để chạy
- [ ] **SonarQube Quality Gate pass** + **Lighthouse score ≥ target** — chưa có code/build

## IV. Traceability
- [ ] IV.1 US → Test: mọi US có ≥ 1 Test ID — US chưa phân tích (02 §IV.1 stub)
- [x] IV.2 BR → Test: mọi BR (BR-07-01..05) có happy + negative đã map
- [ ] IV.3 Component → Test: Critical/High đạt coverage target — chưa có code để đo coverage

## V. UAT
- [ ] Mỗi US có ≥ 1 UAT scenario — suy từ UC/BR (9 scenario), nhưng US chưa phân tích để map 1-1
- [x] ≥ 1 negative + permission + audit verify scenario (UAT-07-03/07/09 + audit ở 06)
- [ ] Test data seed script chạy được — `uat_imm07.py` chưa tạo
- [ ] Tester accounts đã tạo ở UAT site — site Đợt 3 chưa deploy
- [x] Sign-off section sẵn sàng

## VI. Security
- [ ] DocPerm matrix đầy đủ (Decision Table) — ma trận hành vi có, DocPerm per-DocType chờ scaffold
- [ ] Mọi field nhạy cảm có permlevel ≠ 0 — field chưa thiết kế
- [ ] SQL injection + CSRF test pass — chưa có endpoint để test
- [ ] Audit chain test pass (intact + tampered) — chưa có code
- [ ] Vendor isolation test pass — cross-khoa pattern thiết kế, chưa chạy
- [x] Threat model đủ 6 STRIDE với mitigation (VI.9)
- [ ] Sign-off đầy đủ trước go-live — chờ UAT + pen-test

## VII. Code Quality
- [x] Tool matrix + cadence xác định (VII.1/VII.2)
- [ ] SonarQube Quality Gate pass — chưa có code
- [ ] Lighthouse ≥ target — chưa có FE build
- [ ] Bundle size ≤ budget — chưa có chunk
- [ ] Screenshot báo cáo gắn vào file 09 — chờ release
