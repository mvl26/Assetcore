# 07 — Kiểm thử & An ninh (Testing & QA & Security)

| Mục | Giá trị |
|---|---|
| Module | IMM-14 — Giải nhiệm thiết bị |
| Phạm vi | Per-module |
| Owner | QA Lead + Security Officer |
| Liên kết | [02 Analysis](./02_Analysis_Design.md) (US, BR, Activity, BPMN) · [03 Diagrams](./03_Diagrams.md) · [04 Backend](./04_Backend_Design.md) · [05 API](./05_API_Specification.md) · [06 Frontend](./06_Frontend_Design.md) |

> **Mục đích**: Suy ra test case **có hệ thống** từ phân tích (file 02) bằng kỹ thuật black-box + white-box, không liệt kê tự phát. Bao gồm: phân tích đối tượng test → chọn kỹ thuật → viết test → traceability → UAT → security → code quality. Q3 là gate go-live.

> **Trạng thái**: IMM-14 **chưa scaffold BE** (chưa có `services/imm14.py`, `api/imm14.py`, `tests/test_imm14.py`, workflow JSON). File này là **kế hoạch kiểm thử (planning skeleton)**: cấu trúc đầy đủ, điền sự thật đã chốt từ docs 02/04/05; mọi field/endpoint shape/test ID/coverage thực tế đánh dấu `⬜ Planned` hoặc `*(Cần khảo sát)*`, chốt sau Sprint W3-1.

> **⚠️ Đính chính (2026-07-10):** banner trên đã **stale**. MVP vòng 2 + vòng 17 ĐÃ scaffold: `services/imm14.py`, `api/imm14.py`, `tests/test_imm14.py` (15 test class/method — gate, patient-data C/D, approve flow, idempotent/terminal, NEG-09, RBAC, list) đều tồn tại và xanh. Kế hoạch test cho **vòng 17** (detail-view + server-driven approve gate) ở **Phần VIII** cuối file. Phần I–VII giữ làm khung Đợt 3.

---

# Phần I — Test Analysis (Phân tích đối tượng test)

> Mục tiêu Phần I: trả lời 4 câu hỏi trước khi viết test case: **(1) test cái gì** (component inventory) **(2) suy ra từ đâu** (US/BR/Activity) **(3) ưu tiên cái nào** (risk) **(4) loại trừ cái nào** (out-of-scope).

## I.1. Component Inventory — Liệt kê phần mềm cần test

Component planned từ [04 §I-II](./04_Backend_Design.md) + [05 §1](./05_API_Specification.md) + [06](./06_Frontend_Design.md). Mỗi dòng → ≥ 1 test class ở Phần III. Fieldname/file path cụ thể chốt khi scaffold.

| # | Component | Loại | File / Tên (planned) | Test layer áp dụng |
|---|---|---|---|---|
| 1 | `IMM Asset Closure` | DocType (submittable) | `imm_asset_closure.json` | Integration (lifecycle) |
| 2 | `IMM Reconciliation Line` | Child DocType | `imm_reconciliation_line.json` | Integration (child write) |
| 3 | `IMM Sanitization Item` | Child DocType | `imm_sanitization_item.json` | Integration (DPO sign) |
| 4 | `IMM Closure Document` | Child DocType | `imm_closure_document.json` | Integration (attach) |
| 5 | Workflow `IMM Asset Closure` | Workflow | `workflow/imm_14_closure_workflow.json` | Integration (state transition) |
| 6 | `ClosureService.create_from_decision` | Service function | `services/imm14.py::create_from_decision` | Unit |
| 7 | `ClosureService.validate_finalize` | Validator | `services/imm14.py::validate_finalize` | Unit (Decision Table/EP) |
| 8 | `ClosureService.run_finalize_transaction` | Service (atomic) | `services/imm14.py::run_finalize_transaction` | Integration (DB transaction) |
| 9 | `ClosureService.run_rollback` | Service | `services/imm14.py::run_rollback` | Integration |
| 10 | `ReconciliationService` (load_open_wo / load_spare_stock / load_book_value / mark_line_done) | Service (sub) | `services/imm14.py::ReconciliationService.*` | Unit + Integration |
| 11 | `SanitizationService` (load_template / sign) | Service (sub) | `services/imm14.py::SanitizationService.*` | Unit |
| 12 | `ClosureRepo` (get_active / create / update_state) | Repository / DAO | `repositories/closure_repo.py` | Integration (DB) |
| 13 | API `create_closure` | API endpoint POST | `api/imm14.py::create_closure` | API integration |
| 14 | API `get_closure` / `list_closure` | API endpoint GET | `api/imm14.py::get_closure`, `list_closure` | API integration |
| 15 | API `update_reconciliation` | API endpoint POST | `api/imm14.py::update_reconciliation` | API integration |
| 16 | API `sign_sanitization` | API endpoint POST | `api/imm14.py::sign_sanitization` | API integration |
| 17 | API `attach_document` | API endpoint POST | `api/imm14.py::attach_document` | API integration |
| 18 | API `submit_for_approval` | API endpoint POST | `api/imm14.py::submit_for_approval` | API integration |
| 19 | API `finalize` | API endpoint POST | `api/imm14.py::finalize` | API integration |
| 20 | API `request_rollback` / `confirm_rollback` | API endpoint POST | `api/imm14.py::request_rollback`, `confirm_rollback` | API integration |
| 21 | Lifecycle event `decommissioned`, `closure_rolled_back` | Lifecycle event | `Asset Lifecycle Event` (extend) | Integration (audit chain) |
| 22 | `guard_decommissioned_asset` (BR-14-06) | Hook `AC Asset.before_save` | `services/imm14.py::guard_decommissioned_asset` | Unit + Integration |
| 23 | `cron_reconcile_spare_stock` | Scheduler (weekly) | `services/imm14.py::cron_reconcile_spare_stock` | Unit + Cron simulation |
| 24 | `cron_alert_pending_long` | Scheduler (weekly) | `services/imm14.py::cron_alert_pending_long` | Unit + Cron simulation |
| 25 | `cron_dashboard_refresh` | Scheduler (monthly) | `services/imm14.py::cron_dashboard_refresh` | Unit |
| 26 | FE list + form closure | FE view / composable | `frontend/src/views/imm14/*.vue` *(Cần thiết kế khi scaffold FE)* | E2E (Playwright) |
| 27 | Pinia store closure | Pinia store | `frontend/src/stores/imm14*.ts` *(Cần thiết kế khi scaffold FE)* | Unit (vitest) |

## I.2. Trace nguồn test — User Stories, Activity Flows, Business Rules

Dẫn từ [02 §IV Functional Specs](./02_Analysis_Design.md) + [02 §II BPMN To-Be](./02_Analysis_Design.md). Mỗi US/BR/Activity có ≥ 1 test ở Phần III và xuất hiện trong matrix Phần IV.

### I.2.a. Từ User Story
*(Nguồn: 02 §IV.1. AC chi tiết hiện chỉ có cho US-14-05; AC các US còn lại chốt khi BE scaffold → đánh dấu `⬜ Planned`.)*

| US ID | Tiêu đề ngắn | Acceptance Criteria # | Test layer dự kiến |
|---|---|---|---|
| US-14-01 | Tạo closure từ Decommission Decision IMM-13 | ⬜ Planned | Unit + API + UAT |
| US-14-02 | DPO xác nhận sanitization trước duyệt | ⬜ Planned | Unit + API + UAT |
| US-14-03 | Storekeeper xem & xử lý phụ tùng tồn | ⬜ Planned | Unit + API + UAT |
| US-14-04 | Accountant ghi giá trị thanh lý / điều chuyển | ⬜ Planned | Unit + API + UAT |
| US-14-05 | Department Head duyệt closure cuối | AC1, AC2, AC3, AC4, AC5, AC6 (02 §IV.2) | Unit + API + UAT |
| US-14-06 | QLCL xuất closure record cho audit | ⬜ Planned | API + UAT |
| US-14-07 | Dashboard end-of-life (lý do, chi phí) | ⬜ Planned | API + E2E |

### I.2.b. Từ Business Rule
*(Nguồn: 02 §IV.3 + 04 §VI Validation map.)*

| BR ID | Phát biểu (rút gọn) | Component liên quan (I.1) | Kỹ thuật test phù hợp |
|---|---|---|---|
| BR-14-01 | 7 mục bắt buộc trước Approve | `validate_finalize` (#7) | Decision Table |
| BR-14-02 | Separation of duties: `created_by` ≠ `approved_by` | `validate_finalize` (#7) | Decision Table / EP |
| BR-14-03 | Single closure active per asset | `ClosureRepo.get_active` / `before_insert` (#12) | EP |
| BR-14-04 | Rollback chỉ trong `rollback_window_days` (default 30) | `validate_rollback` (#9) | BVA (biên ngày) |
| BR-14-05 | Sanitization gate: `has_patient_data=true` → DPO sign | `SanitizationService` (#11) / `validate_finalize` | Decision Table |
| BR-14-06 | Asset `decommissioned` không cho sửa từ module khác | `guard_decommissioned_asset` (#22) | EP / State Transition |
| BR-14-07 | IMM-05 docs `active` → set `archived` cùng transaction | `run_finalize_transaction` (#8) | Use Case + Error guessing |
| BR-14-08 | IMM-15 stock > 0 → mọi line phải có quyết định, không còn `pending` | `validate_finalize` (#7) | Decision Table / EP |

### I.2.c. Từ Activity Flow / BPMN
*(Nguồn: 02 §II.4 To-Be BPMN + 02 §III Use Case. Activity ID chưa được đánh số hình thức trong 02 → map theo UC.)*

| Activity / UC | Use Case | Branch chính | Branch ngoại lệ |
|---|---|---|---|
| UC-14-01 | Tạo closure từ decision | Tạo draft thành công | Đã có closure active (`IMM14_DUPLICATE_CLOSURE`); decision chưa approved (`IMM13_DECISION_NOT_APPROVED`) |
| UC-14-02 | Đóng WO còn mở | WO đóng/transfer hết | Còn WO Open (`IMM14_OPEN_WO`) |
| UC-14-03 | Sanitization PII/PHI | DPO ký đủ item | Item chưa check đủ (`IMM14_SANITIZATION_INCOMPLETE`); chưa ký (`IMM14_SANITIZATION_REQUIRED`) |
| UC-14-04 | Đối soát phụ tùng kho | Mọi line spare_stock done | Còn line `pending` (`IMM14_PENDING_RECONCILE`) |
| UC-14-05 | Đối soát giá trị tài sản | Ghi book_value done | Role sai scope (`IMM14_PERMISSION_DENIED`) |
| UC-14-06 | Archive hồ sơ pháp lý | IMM-05 docs → archived | Archive fail → rollback transaction (`IMM14_DOCS_ARCHIVE_FAIL`) |
| UC-14-07 | Phê duyệt closure cuối | Approve → decommissioned | Thiếu mục (`IMM14_INCOMPLETE`); SoD (`IMM14_SOD_VIOLATION`) |
| UC-14-08 | Rollback closure | Trong window → reopened | Quá window (`IMM14_ROLLBACK_EXPIRED`); confirm khi chưa request (`IMM14_ROLLBACK_NOT_REQUESTED`) |
| UC-14-10 | Migration legacy closure | Import tạo closure `legacy_imported` | *(Cần khảo sát — script chưa thiết kế)* |

## I.3. Risk-based Priority

Đánh giá rủi ro cho component ở I.1. Likelihood/Impact tham chiếu [02 §I.7 Risk](./02_Analysis_Design.md).

| Component (I.1) | Likelihood (1-5) | Impact (1-5) | Risk = L×I | Priority |
|---|---|---|---|---|
| `run_finalize_transaction` (#8) — atomic finalize | 4 | 5 | 20 | **Critical** |
| `validate_finalize` BR-14-01..08 (#7) | 4 | 5 | 20 | **Critical** |
| Sanitization gate BR-14-05 (#11) — rò rỉ PII/PHI | 3 | 5 | 15 | **Critical** |
| Workflow transition (#5) — approve / rollback | 3 | 5 | 15 | **Critical** |
| BR-14-02 SoD (#7) | 2 | 5 | 10 | High |
| `run_rollback` (#9) — đảo asset_status | 2 | 5 | 10 | High |
| `guard_decommissioned_asset` BR-14-06 (#22) | 2 | 4 | 8 | Medium |
| `cron_reconcile_spare_stock` (#23) — đối soát kho | 3 | 3 | 9 | Medium |
| API permission scope (#15-#16) | 3 | 3 | 9 | Medium |
| `list_closure` / dashboard (#14, #25) read-only | 2 | 2 | 4 | Low |

**Quy ước priority**:
- **Critical** (R ≥ 15): test trước, fail = block release
- **High** (10 ≤ R < 15): bắt buộc trước go-live
- **Medium** (5 ≤ R < 10): trong sprint khi có thời gian
- **Low** (R < 5): chỉ test khi báo cáo bug

## I.4. Scope

**In-scope**:
- Service layer 3-tier (`ClosureService` + `ReconciliationService` + `SanitizationService` + `ClosureRepo`) — unit + integration.
- Workflow `IMM Asset Closure` 7 state — mọi transition (Phần III.4).
- Atomic finalize transaction (cập nhật asset + archive IMM-05 + lifecycle event + audit) — Phần III.3/III.5.
- 10 API endpoint (05 §1) — envelope + error code + permission scope.
- 8 Business Rule (BR-14-01..08) — Decision Table/BVA.

**Out-of-scope**:
- Performance test chi tiết → giao Phần III.8 (chỉ định target, đo khi BE scaffold).
- Cross-module với IMM-13 (input decision), IMM-15 (đối soát kho), IMM-16 (audit pack): chỉ **smoke** ở mức hook emit/subscribe; logic nội bộ các module đó test ở module gốc.
- Quy trình thầu thanh lý / đấu giá (out-of-scope nghiệp vụ — 02 §I.4).
- Xử lý vật lý chất thải nguy hại (ngoài IMMIS).

**Assumptions**:
- IMM-13 đã chuyển asset về `pending_decommission` trước khi test IMM-14.
- Master data (Department, Asset Category, Vendor) đã seed qua fixtures.
- Test users đủ 7 role (I.1 / V.2) đã tạo ở site test.
- Field/endpoint shape đã chốt sau Sprint W3-1 (điều kiện tiên quyết để viết test case thực).

---

# Phần II — Test Design Techniques (Kỹ thuật thiết kế test case)

> Mỗi test phải truy được về 1 kỹ thuật ở dưới.

## II.1. Black-box techniques

| Kỹ thuật | Khi nào dùng | Áp dụng vào IMM-14 (I.1) | Số test sinh ra (rule of thumb) |
|---|---|---|---|
| **Equivalence Partitioning (EP)** | Input có miền giá trị chia nhóm tương đương | `scope` ∈ {spare_stock, book_value, work_order, document}; `disposal_method` ∈ {disposal, donation, sale, trade-in, internal_reassignment}; `confirm_rollback.decision` ∈ {approve, reject}; role partition theo permission | 1 test/partition |
| **Boundary Value Analysis (BVA)** | Numeric / date có biên | `rollback_window_days` (closed_on + 29 / 30 / 31 ngày — BR-14-04); `qty_or_amount` reconciliation line | 2-3 test/biên: window-1, window, window+1 |
| **Decision Table** | Multi-condition gate | BR-14-01 (7 mục AND), BR-14-05 (has_patient_data × signed), BR-14-08 (stock>0 × line status) | 2^N rút gọn theo equivalence |
| **State Transition Testing** | Workflow finite state machine | Workflow `IMM Asset Closure` (Draft → Reconciling → Pending Approval → Closed → Rollback Requested → Reopened / Cancelled) | Mỗi transition + invalid transition |
| **Use Case Testing** | End-to-end actor flow | UAT scenarios (V.4), API integration test | 1/main flow + 1/alt flow + 1/exception |
| **Pairwise / Combinatorial** | Nhiều field optional kết hợp | `list_closure` filter (status × asset_no × year × disposal_method) | Min set cover all pairs |
| **Error Guessing** | Lỗi từ kinh nghiệm: null, empty, unicode, race | Mọi endpoint nhận user input; concurrent finalize 2 lần (race) | Bổ sung — không thay thế kỹ thuật khác |

## II.2. White-box techniques

| Kỹ thuật | Áp dụng vào | Tiêu chí đạt | Công cụ |
|---|---|---|---|
| **Statement coverage** | Service functions I.1 (#6-#11, #22-#25) | ≥ 85% line | `coverage report` |
| **Branch / Decision coverage** | `validate_finalize`, `run_finalize_transaction` (try/except), `run_rollback` | ≥ 80% branch | `coverage --branch` |
| **Condition / MC/DC** | BR-14-01 (7 điều kiện AND), BR-14-05, BR-14-08 | Mỗi sub-condition kiểm soát outcome độc lập | Manual test design + coverage |
| **Path coverage** | `mark_line_done`, `guard_decommissioned_asset` (≤ 20 LOC) | Toàn bộ path khả dĩ | Manual |

## II.3. Mapping Component → Kỹ thuật

| Loại component | Kỹ thuật chính | Kỹ thuật phụ |
|---|---|---|
| Field validator (`SanitizationService.sign`, line status) | BVA + EP | Error guessing |
| Gate logic (`validate_finalize` BR-14-01/05/08) | Decision Table | MC/DC |
| Workflow transition | State Transition | Use Case |
| Service function pure (`load_template`, `load_book_value`) | EP + Branch coverage | BVA |
| API endpoint | Use Case + EP | Pairwise (`list_closure` filter) |
| Scheduler / cron (`cron_reconcile_spare_stock`) | Use Case (state setup → run → assert) | Error guessing (lock, partial fail) |
| FE view (Playwright) | Use Case end-to-end | Error guessing (network 4xx/5xx, role gate) |

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

Theo CLAUDE.md §17 (TDD mandatory): viết test trước khi implement. Service service `imm14.py` dự kiến 600–900 LOC → bắt buộc unit test mọi method public.

## III.2. Unit test — Service Layer

File (planned) `tests/test_imm14.py`. Mỗi test class trace về ≥ 1 dòng I.1. Test ID + số case chính xác chốt khi scaffold (`⬜ Planned`).

| Test class (planned) | Function cover (I.1) | Kỹ thuật | Cases (happy/negative, dự kiến) |
|---|---|---|---|
| `TestClosureCreate` | `create_from_decision` (#6) | EP + Error guessing | 1 / 2 (duplicate, decision chưa approved) |
| `TestValidateFinalize` | `validate_finalize` (#7) — BR-14-01/02/05/08 | Decision Table + MC/DC | 1 / ≥7 (mỗi BR fail) |
| `TestReconciliation` | `ReconciliationService.*` (#10) | EP + BVA | 3 / 2 |
| `TestSanitization` | `SanitizationService.*` (#11) — BR-14-05 | Decision Table | 2 / 2 |
| `TestRollbackWindow` | `run_rollback` / `validate_rollback` (#9) — BR-14-04 | BVA (window±1) | 1 / 2 |
| `TestAssetGuard` | `guard_decommissioned_asset` (#22) — BR-14-06 | EP | 1 / 1 |

## III.3. Integration — DocType lifecycle

File (planned) `tests/test_imm_asset_closure_doctype.py`. Cover hook `validate / before_insert / on_submit (finalize) / on_cancel`.

| Test | Setup | Action | Assert | Kỹ thuật |
|---|---|---|---|---|
| Tạo closure single | Asset `pending_decommission` + decision approved | `doc.insert()` | closure state = Draft, copy decision snapshot | EP |
| Duplicate closure | Đã có closure active cho asset | `doc.insert()` | raise `IMM14_DUPLICATE_CLOSURE` (BR-14-03) | EP |
| Finalize on_submit | 7 mục đầy đủ | `doc.submit()` | asset_status = decommissioned, lifecycle event tạo, docs archived | Use Case |
| Finalize archive fail | Mock IMM-05 archive fail | `doc.submit()` | rollback toàn bộ, asset_status không đổi (`IMM14_DOCS_ARCHIVE_FAIL`) | Error guessing |

Fixture trong `setUpClass` phải có `tearDownClass` purge (refer `assetcore-test` LL-TEST-17). Seed script: III.9.

## III.4. Integration — Workflow transitions

File (planned) `tests/test_imm14_workflow.py`. **Bắt buộc** cover mọi transition trong workflow JSON; đếm bằng `python3 -c "import json; print(len(json.load(open('assetcore/assetcore/workflow/imm_14_closure_workflow.json'))['transitions']))"` sau khi scaffold. Bảng dưới theo state machine [04 §III](./04_Backend_Design.md) (9 transition dự kiến).

| # | Transition | From → To | Role required | Test pass | Test fail (wrong role / gate fail) |
|---|---|---|---|---|---|
| 1 | (auto khi tạo lines) | Draft → Reconciling | HTM Engineer / PTP Khối 2 | ☐ | ☐ |
| 2 | Submit for Approval | Reconciling → Pending Approval | HTM Engineer | ☐ (7 mục đủ) | ☐ (thiếu mục → `IMM14_INCOMPLETE`) |
| 3 | Approve | Pending Approval → Closed | IMM-14 Approver (Dept Head) | ☐ | ☐ (HTM Engineer → reject role) |
| 4 | Send back | Pending Approval → Reconciling | IMM-14 Approver | ☐ | ☐ |
| 5 | Request Rollback | Closed → Rollback Requested | Department Head | ☐ (trong window) | ☐ (quá window → `IMM14_ROLLBACK_EXPIRED`) |
| 6 | Confirm Rollback | Rollback Requested → Reopened | IMM-14 Accountant | ☐ | ☐ (role khác → reject) |
| 7 | Reject Rollback | Rollback Requested → Closed | IMM-14 Accountant | ☐ | ☐ |
| 8 | Continue | Reopened → Reconciling | HTM Engineer | ☐ | ☐ |
| 9 | Cancel | (any 0-state) → Cancelled | Department Head | ☐ | ☐ |

**Kỹ thuật**: State Transition Testing — mỗi edge = 1 test pass + 1 test fail (wrong role hoặc gate fail).

## III.5. Integration — Audit chain integrity

2 test chính:
- (a) Sau N mutation (create → reconcile → sanitize → finalize → rollback), chain hash SHA-256 hợp lệ end-to-end.
- (b) Khi 1 entry bị tamper (sửa `change_summary`), verify endpoint trả `chain_broken=true`.

Trace: [04 §IV Hooks + §VIII](./04_Backend_Design.md) (mọi state transition + giá trị tiền log vào `IMM Audit Trail` — 02 §V NFR Audit). Verify endpoint cụ thể `*(Cần khảo sát khi scaffold)*`.

## III.6. API test

File (planned) `tests/test_imm14_api.py`. Cover happy + invalid params + no permission + pagination + idempotent retry. Endpoint từ [05 §1](./05_API_Specification.md).

| Test | Endpoint (05 §1) | Verify | Kỹ thuật |
|---|---|---|---|
| Create closure happy | `api/imm14.create_closure` | `success=true`, `data.closure_no`, state Draft | Use Case |
| Create closure duplicate | `api/imm14.create_closure` | `code=IMM14_DUPLICATE_CLOSURE` | EP |
| Update reconciliation wrong scope | `api/imm14.update_reconciliation` (Accountant ghi spare_stock) | `code=IMM14_PERMISSION_DENIED` | EP (permission partition) |
| Sign sanitization incomplete | `api/imm14.sign_sanitization` | `code=IMM14_SANITIZATION_INCOMPLETE` | BVA |
| Submit thiếu mục | `api/imm14.submit_for_approval` | `code=IMM14_INCOMPLETE` / `IMM14_PENDING_RECONCILE` / `IMM14_OPEN_WO` | Decision Table |
| Finalize SoD | `api/imm14.finalize` (creator = approver) | `code=IMM14_SOD_VIOLATION` | EP |
| Finalize happy | `api/imm14.finalize` | `success=true`, asset_status decommissioned | Use Case |
| Request rollback expired | `api/imm14.request_rollback` | `code=IMM14_ROLLBACK_EXPIRED` | BVA |
| Confirm rollback not requested | `api/imm14.confirm_rollback` | `code=IMM14_ROLLBACK_NOT_REQUESTED` | EP |
| Finalize low-role | `api/imm14.finalize` (HTM Engineer) | `code=IMM14_PERMISSION_DENIED` / FORBIDDEN | EP (permission partition) |
| List pagination | `api/imm14.list_closure` | `page`/`page_size` boundary, cache 60s | Pairwise |

## III.7. E2E browser (Playwright)

Dùng cho flow UI khó cover bằng API: cascade chọn Decommission Decision → asset; modal confirm finalize (gõ `closure_no` xác nhận); workflow button visibility theo role (HTM Engineer KHÔNG thấy nút Approve); tab Sanitization khoá role DPO. Critical flow E2E: create → reconcile → sanitize → finalize → rollback.

Trace: `assetcore-test` skill Phần 2 (Playwright MCP recipes + R-1..R-9 data rules). Selector/route cụ thể chốt khi FE scaffold (`⬜ Planned`).

## III.8. Performance test

Target từ [02 §V NFR](./02_Analysis_Design.md). Tool **k6** / `pytest-benchmark`. Đo thực khi BE scaffold.

| Metric | Target | Method |
|---|---|---|
| `create_closure` P95 | ≤ 500ms | k6 POST, 50 concurrent |
| `finalize` P95 | ≤ 2000ms | k6 POST, 10 concurrent (transaction lock) |
| `list_closure` (10000 record) P95 | ≤ 800ms | k6 GET |
| Dashboard end-of-life load (5 năm) | ≤ 3s | Browser timing |

Nếu vượt → optimize query (index `asset`, `workflow_state`, `decommissioned_on`).

## III.9. Test data & Fixtures

| Loại | Cách seed | File (planned) |
|---|---|---|
| Master data (Department, Asset Category, Vendor) | `fixtures/*.json` (cài qua `bench migrate`) | `assetcore/fixtures/` |
| Test records (closure/asset states) | `test_records.json` per DocType | `imm_asset_closure/test_records.json` |
| UAT seed (20 asset đa dạng A/B/C/D, có/không PHI, có/không phụ tùng; 10 decision IMM-13 approved; 5–7 user role) | Python script | `assetcore/scripts/uat/uat_imm14.py` *(Sprint W3-1)* |

UAT data phải **thực tế** (tên bệnh viện VN, mã NCC chuẩn). Backend test fixture dùng prefix `_Test` (refer `assetcore-test` R-0/R-1).

## III.10. Run commands & Coverage gate

```bash
# Module test (sau scaffold)
bench --site <site> run-tests --app assetcore --module assetcore.tests.test_imm14
# Coverage
coverage run -m unittest assetcore.tests.test_imm14 && coverage report
# Workflow smoke
bench --site <site> run-tests --module assetcore.tests.test_workflows
```

| Layer | Target coverage | Đo |
|---|---|---|
| Service (`services/imm14.py`) | ≥ 85% line + ≥ 80% branch | `coverage --branch` |
| DocType lifecycle | ≥ 70% | `coverage report` |
| API (`api/imm14.py`) | ≥ 60% | `coverage report` |
| Frontend (vue-tsc) | 0 error | `npm run build` |

Coverage % thực tế `*(Cần khảo sát — đo sau scaffold)*`.

---

# Phần IV — Traceability Matrices

> 3 ma trận theo 3 hướng. Test ID đánh dấu `⬜ Planned` (chưa scaffold).

## IV.1. US → Test mapping

| US ID | AC | Test ID (III.x) | Layer | Status |
|---|---|---|---|---|
| US-14-01 | ⬜ Planned | `TestClosureCreate` + `create_closure` API | Unit + API | ⬜ Planned |
| US-14-02 | ⬜ Planned | `TestSanitization` + `sign_sanitization` API | Unit + API | ⬜ Planned |
| US-14-03 | ⬜ Planned | `TestReconciliation` (spare_stock) + `update_reconciliation` | Unit + API | ⬜ Planned |
| US-14-04 | ⬜ Planned | `TestReconciliation` (book_value) + `update_reconciliation` | Unit + API | ⬜ Planned |
| US-14-05 | AC1-AC6 | `TestValidateFinalize` + `finalize` API + UAT-IMM-14-01 | Unit + API + UAT | ⬜ Planned |
| US-14-06 | ⬜ Planned | `list_closure` / export PDF | API + UAT | ⬜ Planned |
| US-14-07 | ⬜ Planned | Dashboard E2E | API + E2E | ⬜ Planned |

## IV.2. BR → Test mapping

| BR ID | Phát biểu (rút gọn) | Test ID | Kỹ thuật | Happy / Negative |
|---|---|---|---|---|
| BR-14-01 | 7 mục bắt buộc | `TestValidateFinalize` | Decision Table | 1 / 7 |
| BR-14-02 | SoD created ≠ approved | `TestValidateFinalize::sod` | EP | 1 / 1 |
| BR-14-03 | Single closure active | DocType integration (III.3) | EP | 1 / 1 |
| BR-14-04 | Rollback window | `TestRollbackWindow` | BVA | 1 / 2 |
| BR-14-05 | Sanitization gate | `TestSanitization` | Decision Table | 1 / 2 |
| BR-14-06 | Asset lock | `TestAssetGuard` | EP | 1 / 1 |
| BR-14-07 | Archive hồ sơ cùng transaction | `run_finalize_transaction` integration (III.3) | Use Case + Error guessing | 1 / 1 |
| BR-14-08 | Phụ tùng pending | `TestValidateFinalize::pending_stock` | Decision Table | 1 / 1 |

## IV.3. Component → Test mapping

| Component (I.1) | Test ID | Test layer | Coverage % | Risk priority (I.3) |
|---|---|---|---|---|
| `run_finalize_transaction` (#8) | III.3 finalize tests | Integration | *(Cần khảo sát)* | Critical |
| `validate_finalize` (#7) | `TestValidateFinalize` | Unit | *(Cần khảo sát)* | Critical |
| `SanitizationService` (#11) | `TestSanitization` | Unit | *(Cần khảo sát)* | Critical |
| Workflow (#5) | `test_imm14_workflow.py` | Integration | *(Cần khảo sát)* | Critical |
| `run_rollback` (#9) | `TestRollbackWindow` | Integration | *(Cần khảo sát)* | High |
| API finalize (#19) | III.6 finalize tests | API | *(Cần khảo sát)* | Critical |
| `cron_reconcile_spare_stock` (#23) | cron simulation | Unit | *(Cần khảo sát)* | Medium |
| `list_closure` (#14) | III.6 pagination | API | *(Cần khảo sát)* | Low |

---

# Phần V — UAT Script

## V.1. Phạm vi UAT

- **In-scope**: scenario theo US-14-01..07 (V.4) — đủ happy + negative + permission + rollback + legacy migration.
- **Out-of-scope**: performance (III.8), security pentest (Phần VI.10).
- **Pre-condition**: site UAT deploy version `*(chốt sau Sprint W3-4)*`, fixture loaded (III.9), tester accounts active đủ 7 role.

## V.2. Tester accounts

| Username (planned) | Role | Vai trò UAT |
|---|---|---|
| `uat_htm@<site>` | HTM Engineer | Tạo & driver closure |
| `uat_dpo@<site>` | DPO | Ký sanitization |
| `uat_store@<site>` | Storekeeper | Đối soát phụ tùng (scope spare_stock) |
| `uat_acct@<site>` | Accountant | Đối soát giá trị + confirm rollback |
| `uat_qlcl@<site>` | QLCL Officer | Archive hồ sơ + attach biên bản |
| `uat_head@<site>` | Department Head / IMM-14 Approver | Phê duyệt cuối + request rollback |
| `uat_auditor@<site>` | Auditor (read-only) | Đọc closure record, cover FORBIDDEN case |

Bắt buộc có account role thấp (Auditor / Storekeeper) để cover FORBIDDEN — không chỉ Admin.

## V.3. Test data đã seed

| DocType | Số lượng | Ghi chú |
|---|---|---|
| `AC Asset` (`pending_decommission`) | 20 | Đa dạng classification A/B/C/D, có/không `has_patient_data`, có/không phụ tùng tồn |
| `IMM Decommission Decision` (IMM-13, approved) | 10 | Input cho create_closure |
| `IMM Spare Part Stock` (IMM-15) | ≥5 asset có tồn | Cover BR-14-08 |
| `IMM Document` (IMM-05, active) | ≥5 asset có docs | Cover BR-14-07 archive |
| User các role | 7 | Theo V.2 |

Reset script đi kèm: `assetcore/scripts/uat/uat_imm14.py` *(Sprint W3-1)*.

## V.4. UAT Scenarios — Suy ra từ US + Activity

Mỗi scenario theo template §Phụ lục A. ID `UAT-IMM-14-NN`. Step chi tiết chốt khi FE scaffold; bảng tổng dưới cố định actor + US/BR cover + kỹ thuật.

| ID | Actor | Pre-condition | US/BR cover | Kỹ thuật | Kết quả mong đợi |
|---|---|---|---|---|---|
| UAT-IMM-14-01 | HTM Engineer → Dept Head | Asset (không PHI) + decision approved, không WO mở | US-14-01/05, BR-14-01 | Use Case happy | Closure Closed, asset decommissioned, IMM-05 archived, dashboard +1 |
| UAT-IMM-14-02 | DPO + HTM Engineer | Asset `has_patient_data=true` | US-14-02, BR-14-05 | Use Case alt + Decision Table | Submit khi chưa ký → `IMM14_SANITIZATION_REQUIRED`; sau ký DPO → OK, report có chữ ký + timestamp |
| UAT-IMM-14-03 | Dept Head + Accountant | Closure đã Closed 5 ngày | US-14-05, BR-14-04 | State Transition | Rollback in-window → asset về `pending_decommission`, IMM-05 unarchive, event `closure_rolled_back` |
| UAT-IMM-14-04 | Storekeeper | Asset còn phụ tùng IMM-15 `pending` | US-14-03, BR-14-08 | Use Case alt | Submit bị block `IMM14_PENDING_RECONCILE` cho tới khi mọi line done |
| UAT-IMM-14-05 | HTM Engineer (creator) | Closure Pending Approval | US-14-05 AC6, BR-14-02 | EP permission negative | Creator bấm Approve → block `IMM14_SOD_VIOLATION` |
| UAT-IMM-14-06 | Auditor | Closure đã Closed | US-14-06 | EP permission | Auditor đọc + xuất PDF; mọi nút mutate ẩn/disabled |
| UAT-IMM-14-07 | Admin (System) | 5 asset thanh lý trước go-live | US (migration), UC-14-10 | Use Case | Script tạo 5 closure `legacy_imported=true`, asset decommissioned, xuất được closure report |

**Quy tắc suy scenario** (Use Case Testing): mỗi US ≥ 1 happy; mỗi Activity exception (I.2.c) ≥ 1; mỗi role mutate ≥ 1 permission verify; mỗi terminal transition ≥ 1 verify audit + cross-module hook; mỗi BR Critical ≥ 1 negative.

## V.5. Tổng hợp kết quả & Bug found

- Bảng kết quả: `Scenario · Status (Pass/Fail/Block) · Tester · Ngày · Ghi chú` — điền khi chạy UAT (Sprint W3-4).
- Bug list: `Issue ID · Severity (Blocker/Major/Minor/Trivial) · Mô tả · Fix status`.
- Acceptance: ≥ 95% PASS, Blocker = 0, Major ≤ 2 (có workaround).
- Sign-off: BA Lead + QA Lead + Module Owner (PTP Khối 2) + End-user (Trưởng phòng VT-TBYT).

---

# Phần VI — Security Review (gate)

## VI.1. RBAC

- **Role definitions** (planned `fixtures/role.json` + `role_profile.json`): HTM Engineer, Storekeeper, Accountant (IMM-14 Accountant), DPO, QLCL Officer, Department Head (IMM-14 Approver), Auditor.
- **DocPerm matrix** `IMM Asset Closure` (từ [04 §V](./04_Backend_Design.md)):

| Role | Read | Write | Submit | Approve | Cancel | Ghi chú scope |
|---|---|---|---|---|---|---|
| HTM Engineer | ✅ | ✅ (Draft, Reconciling) | ❌ | ❌ | ❌ | driver closure |
| Storekeeper | ✅ | ✅ | ❌ | ❌ | ❌ | chỉ Reconciliation Line `scope=spare_stock` |
| Accountant | ✅ | ✅ | ❌ | ❌ | ❌ | chỉ `scope=book_value` + confirm rollback |
| DPO | ✅ | ✅ | ❌ | ❌ | ❌ | chỉ Sanitization Item |
| QLCL Officer | ✅ | ✅ | ❌ | ❌ | ❌ | chỉ Closure Document |
| Department Head (Approver) | ✅ | ❌ | ✅ | ✅ | ✅ | finalize + cancel |
| Auditor | ✅ | ❌ | ❌ | ❌ | ❌ | read-only |

- **Field-level permission**: field nhạy cảm `final_value` / `book_value` / `purchase_value` (giá trị tiền) → permlevel ≠ 0, chỉ Accountant + Approver write. `signed_by` (DPO) read-only sau ký. *(permlevel cụ thể chốt sprint W3-1.)*
- **User Permission**: filter row theo `company` / `department` của asset *(Cần khảo sát — xác nhận khi scaffold).*

**Kỹ thuật**: Decision Table — mỗi (role × action × state) là 1 row, expected = Allow/Deny. QA tạo 1 user/role thử full matrix; mọi cell sai = security bug P0.

## VI.2. API security

- **Whitelist hygiene**: mọi `@frappe.whitelist()` trong `api/imm14.py` có docstring + `allow_guest=False` + `frappe.has_permission(...)` / `rbac.require()` + validate input. Không lộ method nội bộ ra whitelist.
- **CSRF**: endpoint POST yêu cầu `X-Frappe-CSRF-Token` (Frappe default).
- **Input validation**: `decision_no`, `closure_no`, `ref_name` validate qua `frappe.get_value` / `frappe.db.exists` trước khi dùng; `scope`/`disposal_method` validate enum.
- **SQL injection**: parameterized query only trong `closure_repo.py`; cấm f-string vào raw SQL.
- **Rate limit**: endpoint mutating `finalize`, `confirm_rollback` áp RBAC chặt + full audit; `list_closure` cache 60s ([05 §5](./05_API_Specification.md)).

## VI.3. Audit trail integrity

Mọi state transition + finalize + rollback + giá trị tiền ghi `IMM Audit Trail` (user, timestamp, before, after, reason) — 02 §V NFR Audit. Hash SHA-256 chain + verify endpoint + test tamper (III.5). User KHÔNG có quyền edit/delete `IMM Audit Trail` (DocPerm + `on_trash` guard — ISO 13485:7.5.9). Sanity: 10 action → 10 audit record.

## VI.4. Authentication & session

Login Frappe default (session cookie). Session timeout + lockout + password policy theo `assetcore-security` skill chung. API key rotation theo policy site. 2FA: roadmap (ngoài Đợt 3 core).

## VI.5. Data sensitivity

KHÔNG lưu patient data trong closure. Khi closure approved, KHÔNG persist nội dung sanitization item dạng text PII — chỉ lưu boolean `checked` + `signed_by` + `signed_at`. Hồ sơ archive IMM-05 có thể chứa PII → read = Auditor + DPO.

| Loại | Trường (planned) | Sensitivity | Bảo vệ |
|---|---|---|---|
| Giá trị tài sản | `final_value`, `book_value`, `purchase_value` | Confidential | permlevel ≠ 0, Accountant/Approver only |
| Chữ ký DPO | `signed_by`, `signed_at` | Internal | read-only sau ký, audit log |
| Checklist sanitization | `IMM Sanitization Item.checked` | Internal | boolean only, không lưu text PII |
| Closure metadata | `asset_no`, `disposal_method`, `reason` | Internal | RBAC IMM-14 roles |

## VI.6. Vendor isolation

IMM-14 không có actor Vendor External trong [02 §I.3 / III.1](./02_Analysis_Design.md) (toàn bộ actor là nội viện). Nếu sau này gắn vendor thanh lý → vendor chỉ thấy phần được assign qua `permission_query_conditions`, KHÔNG thấy giá trị tài sản / audit trail / hồ sơ asset khác, KHÔNG export. Hiện tại: `*(Cần khảo sát khi mở rộng — chưa trong scope Đợt 3).*`

## VI.7. Secrets management

Cấm commit `.env` / credential. `site_config.json` không lên git. Token integration ERP tài chính (nếu có, giai đoạn sau) lưu `frappe.conf`. Backup encrypt at-rest, lưu off-site.

## VI.8. Logging & monitoring

| Sự kiện | Log level | Where | Alert? |
|---|---|---|---|
| Finalize / rollback | INFO | `IMM Audit Trail` + app log | Có (closure quá 5 ngày → `cron_alert_pending_long`) |
| Archive IMM-05 fail | ERROR | app log + audit | Có |
| Permission denied (FORBIDDEN) | WARNING | app log | Theo dõi pattern |
| SoD violation | WARNING | audit | Có |

PII / token KHÔNG vào log.

## VI.9. Threat model (STRIDE-lite)

| Threat | Vector | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| **S**poofing | Giả mạo Approver duyệt closure | Thấp | Cao | Frappe session auth + RBAC role `IMM-14 Approver` |
| **T**ampering | Sửa `final_value` / audit trail sau finalize | Trung bình | Cao | permlevel field + asset lock BR-14-06 + audit hash chain (III.5) |
| **R**epudiation | Phủ nhận đã duyệt / ký sanitization | Thấp | Cao | `signed_by`+`signed_at`, audit log mọi transition |
| **I**nfo disclosure | Storekeeper/Auditor xem giá trị tài sản confidential | Trung bình | Trung bình | permlevel ≠ 0 field tiền, DocPerm scope |
| **D**enial of service | Concurrent finalize / lock DB transaction dài | Thấp | Trung bình | Atomic transaction + rate limit + index query |
| **E**levation of privilege | HTM Engineer gọi `finalize` / `confirm_rollback` | Trung bình | Cao | `frappe.has_permission` + RBAC test (III.6 low-role) |

## VI.10. Penetration test

Trước release đầu tiên: Burp/ZAP scan, sqlmap (an toàn), CSRF test, role escalation (HTM Engineer → finalize). Report lưu `docs/security/`. *(Thực hiện sau scaffold, trước go-live W3-4.)*

## VI.11. Sign-off

| Role | Người | Ngày | Chữ ký |
|---|---|---|---|
| Security Officer | *(chốt go-live)* | | |
| QA Lead | | | |
| Module Owner (PTP Khối 2) | | | |

Decision: ☐ Pass / ☐ Pass with conditions / ☐ Fail (block). *(Điền khi go-live W3-4.)*

---

# Phần VII — Code Quality

## VII.1. Tool matrix

| Tool | Mục tiêu | Target | Cadence |
|---|---|---|---|
| **SonarQube** (BE Python) | Bug / smell / duplication / coverage / hotspot | 0 critical bug, code smell ≤ 20, duplication ≤ 3%, coverage ≥ 70%, security hotspot review 100% | Mỗi PR (CI gate) |
| **ruff / black** (BE Python) | Lint + format | 0 error, format consistent | Mỗi PR (CI gate) |
| **Type hint + docstring** | CLAUDE.md §15 | 100% function có type hint + docstring public | Mỗi PR (review) |
| **Cyclomatic complexity** | Service function | ≤ 10 per function | SonarQube |
| **ESLint + vue-tsc** (FE) | Lint + type | 0 error, 0 warning prod build | Mỗi PR FE |
| **Lighthouse** (FE) | Perf / a11y / best practices / SEO | Perf ≥ 90, A11y ≥ 95, Best Practices ≥ 90, SEO ≥ 80 | Mỗi release + monthly |
| **Bundle size** (chunk imm14) | Budget gzip | main ≤ 250KB, async ≤ 80KB | Mỗi PR FE (CI report) |

## VII.2. Cadence

- SonarQube: mỗi PR (CI gate, fail nếu Quality Gate fail).
- Lighthouse: mỗi release lớn + monthly audit.
- ESLint / ruff: mỗi PR (CI gate; PR fail nếu coverage giảm hoặc lint dirty — refer `assetcore-deploy`).
- Bundle size: mỗi PR FE (CI report, fail nếu vượt budget).

Screenshot SonarQube + Lighthouse gắn vào [09 §Release Notes](./09_Release.md) khi báo cáo final.

---

# Phụ lục A — Template per UAT scenario

```markdown
### UAT-IMM-14-<NN> — <Tên>

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
### TC-IMM-14-<LAYER>-<NN> — <Tên>

**Component (I.1)**: <…>
**Liên kết**: US-<NN> | BR-<NN> | ACT-<NN>
**Kỹ thuật (II.1/II.2)**: BVA boundary `rollback_window_days = 30`
**Priority (I.3)**: Critical / High / Medium / Low
**Test type**: Unit / Integration / API / E2E
**Pre-condition**: <fixture / state setup>

**Input**:
- <field>: <value>

**Steps**:
1. <…>
2. <…>

**Expected**:
- ServiceError(code=IMM14_INCOMPLETE, message contains "BR-14-01")
- doc.workflow_state unchanged

**Post-condition**: <DB rollback / fixture cleanup>
```

# Phụ lục C — Workflow State Transition Test template

```markdown
### TC-IMM-14-WF-<NN> — <action>: <from> → <to>

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
- [x] I.1 Component Inventory liệt kê đủ artefact (27 dòng, so với 04/05/06)
- [x] I.2 mỗi US / BR / Activity có ≥ 1 dòng map (AC chi tiết chỉ US-14-05 — phần còn lại ⬜ Planned vì 02 chưa đánh AC)
- [x] I.3 Risk priority gán cho mọi nhóm component (không trống)
- [x] I.4 Scope ghi rõ out-of-scope kèm lý do

## II. Test Design Techniques
- [x] II.1 chọn ≥ 4 black-box techniques (EP + BVA + Decision Table + State Transition + Use Case + Pairwise + Error Guessing)
- [x] II.2 white-box criteria xác định (statement + branch + MC/DC + path)
- [x] II.3 mapping component → kỹ thuật điền đầy đủ

## III. Test Plan
- [x] Test class structure cho mọi service public function (I.1) — bảng III.2 (test ID ⬜ Planned vì chưa scaffold)
- [x] ≥ 1 happy + 1 negative test mỗi function (kế hoạch)
- [x] Workflow transitions liệt kê 100% (9 transition theo 04 §III; đếm lại bằng JSON sau scaffold)
- [x] Audit chain test (intact + tampered) — III.5
- [x] API test plan ≥ 60% target + permission matrix — III.6
- [x] Performance target xác định — III.8
- [ ] CI command chạy clean — **BE chưa scaffold, không chạy được `bench run-tests`**
- [ ] SonarQube Quality Gate pass + Lighthouse ≥ target — **chưa có code/FE để đo**

## IV. Traceability
- [x] IV.1 US → Test: mọi US (7) có ≥ 1 Test ID (status ⬜ Planned)
- [x] IV.2 BR → Test: mọi BR (8) có happy + negative
- [ ] IV.3 Component → Test: coverage % — **`*(Cần khảo sát)*`, đo sau scaffold**

## V. UAT
- [x] Mỗi US có ≥ 1 UAT scenario (7 scenario UAT-IMM-14-01..07)
- [x] ≥ 1 negative + permission + audit verify scenario (UAT-02/04/05/06)
- [ ] Test data seed script chạy được — **script `uat_imm14.py` planned Sprint W3-1, chưa tồn tại**
- [ ] Tester accounts đã tạo ở UAT site — **site UAT chưa deploy (W3-4)**
- [x] Sign-off section sẵn sàng

## VI. Security
- [x] DocPerm matrix đầy đủ (Decision Table) — VI.1, từ 04 §V
- [x] Field nhạy cảm (giá trị tiền) gán permlevel ≠ 0 (kế hoạch; permlevel cụ thể chốt W3-1)
- [ ] SQL injection + CSRF test pass — **chưa có code để test**
- [ ] Audit chain test pass (intact + tampered) — **chưa scaffold**
- [x] Vendor isolation: xác nhận IMM-14 không có actor vendor (VI.6); plan nếu mở rộng
- [x] Threat model đủ 6 STRIDE với mitigation — VI.9
- [ ] Sign-off đầy đủ trước go-live — **điền W3-4**

## VII. Code Quality
- [ ] SonarQube Quality Gate pass — **chưa có code**
- [ ] Lighthouse ≥ target — **chưa có FE**
- [ ] Bundle size ≤ budget — **chưa có FE chunk**
- [ ] Screenshot báo cáo gắn vào file 09 — **sau scaffold**

---

---

# Phần VIII — Test plan vòng 17 (Chi tiết + server-driven approve gate) — CHỐT

> Ref acceptance `02 §VIII.3` · SoT `04 §X` · API `05 §8` · FE `06 §13`. TDD gate: `bench --site miyano run-tests` (test_imm14) → "Ran N OK"; FE `DecommissionDetailView.ctaGate.test.ts` pass + `npm run typecheck` (prod) 0 error.

## VIII.1. BE — `tests/test_imm14.py` (EXTEND, không tạo file mới)

Thêm class `TestGetDecommissionApproveGate(_BaseIMM14)` — trace BR-14-W2-13..16:

| Test | Kịch bản | Assert |
|---|---|---|
| `test_get_emits_can_approve_for_approver_draft` | approver (submit=1) đọc draft hợp lệ (không C/D, hoặc C/D đã sanitized) | `can_approve == 1` **and** `approve_blocked_reason == ""` |
| `test_get_can_approve_zero_for_reader_without_submit` | Commissioning User (create=1/submit=0) đọc CÙNG draft | `can_approve == 0` **and** reason == "Bạn không đủ quyền duyệt giải nhiệm." |
| `test_get_can_approve_zero_when_already_approved` | record docstatus=1 | `can_approve == 0` **and** reason == "Hồ sơ giải nhiệm đã được duyệt." |
| `test_get_can_approve_zero_when_patient_data_missing` | approver đọc draft C/D (High/Critical) chưa `patient_data_sanitized` | `can_approve == 0` **and** reason chứa "dữ liệu bệnh nhân" (WHO §3.6) |
| `test_get_can_approve_zero_when_asset_already_decommissioned` | asset đã Decommissioned bởi record khác | `can_approve == 0` **and** reason chứa "đã được giải nhiệm" |
| `test_invariant_reason_iff_blocked` | mọi case trên | `(approve_blocked_reason != "") == (can_approve == 0)` |
| `test_get_no_email_leak` | responsible = email | output có `responsible_name`; `responsible` giữ khoá kỹ thuật; `asset_name` set (không rò id thô ở field hiển thị) |
| `test_get_can_approve_matches_approve_enforcement` | **SoT parity:** với record mà `can_approve==0` vì field-rule → gọi `approve_decommission` PHẢI raise/blocked cùng lý do (không drift) | approve chặn tương ứng |

- Dùng helper `_BaseIMM14` (set user theo role) đã có; capability check qua `rbac.can` → set session user role tương ứng (Super Admin / Commissioning Manager / Commissioning User).
- Read-only: assert `get_decommission` KHÔNG sinh Lifecycle Event / Audit Trail mới (BR-14-W2-12 giữ).

## VIII.2. FE — `views/eol/DecommissionDetailView.ctaGate.test.ts` (NEW)

Mirror `DocumentDetailView.ctaGating.test.ts`. Matrix (mock `getDecommission`):

| Case | Mock | Assert |
|---|---|---|
| (a) approver draft | `can_approve:1, reason:""` | `[data-testid=cta-approve]` render; click → `approveDecommission(name)` gọi 1 lần |
| (b) reader no-submit | `can_approve:0, reason:"Bạn không đủ quyền duyệt giải nhiệm."` | KHÔNG `cta-approve`; `[data-testid=approve-blocked-hint]` chứa chuỗi VI đó |
| (c) already approved | `can_approve:0, reason:"Hồ sơ giải nhiệm đã được duyệt.", workflow_state:"Approved"` | KHÔNG nút; badge "Đã duyệt" |
| (d) anti-dead-control | `docstatus:0, workflow_state:"Draft", can_approve:0` | **KHÔNG** nút (chứng minh gate theo `can_approve`, KHÔNG docstatus/state===) |
| (e) anti-PII | `responsible:"x@y.vn", asset:"AST-1", asset_name:"Máy X", responsible_name:"Nguyễn A"` | DOM KHÔNG chứa "x@y.vn" / "AST-1" ở field hiển thị; KHÔNG raw 'Draft'/'Approved' EN |
| (f) degrade | `can_approve: undefined` | KHÔNG nút (an toàn) |

## VIII.3. FE — cập nhật `DecommissionListView.render.test.ts` (EDIT)

- Đổi assertion row-click: `router.push` gọi với `'/decommissions/<name>'` (thay `'/assets/<asset>'`) — theo ADR-IMM14-DETAIL-03.

## VIII.4. Run commands

```bash
bench --site miyano run-tests --app assetcore --module assetcore.tests.test_imm14   # BE → "Ran N OK"
cd frontend && npx vitest run src/views/eol/tests/DecommissionDetailView.ctaGate.test.ts       # FE gate
cd frontend && npm run typecheck                                                     # prod tsc 0 error
```

*Hết Phần VIII (vòng 17).*

---

*Hết file 07 — IMM-14 planning skeleton (Phần I–VII) + test plan vòng 17 (Phần VIII CHỐT). Test case ID, coverage %, sign-off điền khi BE scaffold (Sprint W3-1) và UAT (W3-4).*
