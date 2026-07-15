# 07 — Kiểm thử & An ninh (Testing & QA & Security)

| Mục | Giá trị |
|---|---|
| Module | IMM-05 — Hồ sơ thiết bị (Asset Documents) |
| Phạm vi | Per-module |
| Owner | QA Lead + Security Officer |
| Liên kết | 02 Analysis (US, BR, Activity, BPMN) · 03 Diagrams · 04 Backend · 05 API · 06 Frontend |

> **Mục đích**: Suy ra test case có hệ thống từ phân tích (file 02) bằng kỹ thuật black-box + white-box, không liệt kê tự phát. Bao gồm: phân tích đối tượng test → chọn kỹ thuật → viết test → traceability → UAT → security → code quality. Phần VI (Security) là gate go-live.

---

# Phần I — Test Analysis (Phân tích đối tượng test)

> Mục tiêu Phần I: trả lời 4 câu hỏi trước khi viết test case: (1) test cái gì (component inventory) (2) suy ra từ đâu (US/BR/Activity) (3) ưu tiên cái nào (risk) (4) loại trừ cái nào (out-of-scope).

## I.1. Component Inventory — Liệt kê phần mềm cần test

Toàn bộ artefact test được của IMM-05 (đối chiếu 04 §DocType/Service/Hook, 05 §Catalog, 06 §Components). Mỗi dòng → ≥ 1 test class ở Phần III.

| # | Component | Loại | File / Tên | Test layer áp dụng |
|---|---|---|---|---|
| 1 | Asset Document | DocType | `asset_document/asset_document.json` | Integration (lifecycle) |
| 2 | Document Request | DocType | `document_request/document_request.json` | Integration (lifecycle) |
| 3 | Expiry Alert Log | DocType | `expiry_alert_log/expiry_alert_log.json` | Integration (idempotent) |
| 4 | Required Document Type | DocType | `required_document_type/required_document_type.json` | Integration (completeness) |
| 5 | IMM-05 Document Workflow | Workflow | `workflow/imm_05_document_workflow.json` (6 state, 9 transition) | Integration (state transition) |
| 6 | `check_document_expiry()` | Scheduler job | `services/imm05.py::check_document_expiry` | Unit + Cron simulation |
| 7 | `_resolve_alert_level()` | Validator (pure) | `services/imm05.py::_resolve_alert_level` | Unit (BVA/EP) |
| 8 | `_apply_visibility_filter()` | Validator (RBAC) | `services/imm05.py::_apply_visibility_filter` | Unit (EP) |
| 9 | `_can_see_internal()` | Helper RBAC | `services/imm05.py::_can_see_internal` | Unit (Decision Table) |
| 10 | `_require_approve_role()` / `_require_exempt_role()` | Guard | `services/imm05.py` | Unit (EP permission) |
| 11 | `create_document()` | Service function | `services/imm05.py::create_document` | Unit |
| 12 | `submit_for_review()` | Service function | `services/imm05.py::submit_for_review` | Unit |
| 13 | `update_document()` | Service function | `services/imm05.py::update_document` | Unit (state guard) |
| 14 | `approve_document()` | Service function | `services/imm05.py::approve_document` | Unit (archive old) |
| 15 | `reject_document()` | Service function | `services/imm05.py::reject_document` | Unit |
| 16 | `archive_document()` | Service function | `services/imm05.py::archive_document` | Unit |
| 17 | `list_documents()` | Service function | `services/imm05.py::list_documents` | Unit + API (pagination, visibility) |
| 18 | `get_document()` | Service function | `services/imm05.py::get_document` | Unit (NOT_FOUND) |
| 19 | `get_asset_documents()` | Service function | `services/imm05.py::get_asset_documents` | Integration (completeness) |
| 20 | `get_dashboard_stats()` | Service function | `services/imm05.py::get_dashboard_stats` | Unit |
| 21 | `get_expiring_documents()` | Service function | `services/imm05.py::get_expiring_documents` | Unit |
| 22 | `get_compliance_by_dept()` | Service function | `services/imm05.py::get_compliance_by_dept` | Unit |
| 23 | `get_document_history()` | Service function | `services/imm05.py::get_document_history` | Integration (audit chain) |
| 24 | `create_document_request()` / `get_document_requests()` | Service function | `services/imm05.py` | Unit + API |
| 25 | `mark_exempt()` | Service function | `services/imm05.py::mark_exempt` | Unit (role guard) |
| 26 | 16 API endpoints | API | `api/imm05.py::*` | API integration |
| 27 | Document views / store | FE | `frontend/src/api/imm05.ts` · `frontend/src/types/imm05.ts` | E2E (Playwright) |

## I.2. Trace nguồn test — User Stories, Activity Flows, Business Rules

3 bảng dẫn từ artefact phân tích (file 02) sang test layer. Mỗi US/BR/Activity có ≥ 1 test ở Phần III và xuất hiện trong matrix Phần IV.

### I.2.a. Từ User Story
→ 02 §III.5 UC↔US mapping, §US-05-01..09

| US ID | Tiêu đề ngắn | Acceptance Criteria # | Test layer dự kiến |
|---|---|---|---|
| US-05-01 | Upload tài liệu mới | AC1, AC2 | Unit + API + UAT |
| US-05-02 | Approve / Reject (auto-archive version cũ) | AC1, AC2 | Unit + API + UAT |
| US-05-03 | System auto-import từ IMM-04 | AC1 | Integration + UAT |
| US-05-04 | Cảnh báo hết hạn (scheduler) | AC1, AC2 | Unit + Cron + UAT |
| US-05-05 | Dashboard KPIs | AC1 | Unit + UAT |
| US-05-06 | Xem kho hồ sơ theo Asset | AC1 | Integration + UAT |
| US-05-07 | Version control | AC1 | Unit + UAT |
| US-05-08 | Document Request | AC1 | Unit + API |
| US-05-09 | Mark Exempt | AC1 | Unit + UAT |

### I.2.b. Từ Business Rule
→ 02 §Business Rules (BR-05-01..10)

| BR ID | Phát biểu (rút gọn) | Component liên quan (I.1) | Kỹ thuật test phù hợp |
|---|---|---|---|
| BR-05-01 | 1 Active doc per (asset_ref + doc_type_detail) — archive cũ | `approve_document` (#14), `on_update` archive | Decision Table |
| BR-05-02 | Không xóa cứng — `on_trash()` throw | Asset Document DocType (#1) | Error guessing |
| BR-05-03 | Expiry alert 90/60/30/0 idempotent | `check_document_expiry` (#6), `_resolve_alert_level` (#7) | BVA |
| BR-05-04 | Auto-import từ IMM-04 khi Clinical Release | IMM-04 `on_submit` hook | Use Case |
| BR-05-05 | Bộ hồ sơ bắt buộc qua Required Document Type | `get_asset_documents` (#19) | EP |
| BR-05-06 | `is_model_level=1` áp dụng toàn bộ asset cùng model | UI filter + report | EP |
| BR-05-07 | GW-2: block IMM-04 Submit nếu thiếu CN ĐKLH + không exempt | IMM-04 `validate()` | Decision Table |
| BR-05-08 | Exempt → `document_status = "Compliant (Exempt)"` | `mark_exempt` (#25), `_compute_document_status` | Decision Table |
| BR-05-09 | `change_summary` bắt buộc khi version ≠ "1.0" | Asset Document `validate()` (VR-09) | BVA + EP |
| BR-05-10 | `Internal_Only` ẩn với non-internal roles | `_apply_visibility_filter` (#8) | Decision Table |

### I.2.c. Từ Activity Flow / BPMN
→ 02 §Use Case (UC-01..UC-10)

| Activity (UC) | Use Case | Branch chính | Branch ngoại lệ |
|---|---|---|---|
| UC-01 | Upload tài liệu | Happy: Draft → Pending Review | Thiếu file, expiry ≤ issued, doc_number trùng |
| UC-03 | Approve / Reject | Happy: Pending → Active | Reject không lý do, sai role, wrong state |
| UC-04 | Version control | Approve v2 → v1 Archived | change_summary trống khi v ≠ 1.0 |
| UC-05 | Mark Exempt | Exempt → Compliant (Exempt) | Sai role (không phải approve role) |
| UC-08 | Dashboard | KPI đếm đúng | Không có doc → đếm 0 |
| UC-09 | Cảnh báo hết hạn | Scheduler sinh alert đúng mốc | Chạy 2 lần cùng ngày (idempotent) |

> 1 BR thường sinh 1 nhóm test (1 happy + N negative). 1 Activity branch = 1 path test trong State Transition.

## I.3. Risk-based Priority

| Component (I.1) | Likelihood (1-5) | Impact (1-5) | Risk = L×I | Priority |
|---|---|---|---|---|
| IMM-05 Document Workflow (#5) | 4 | 5 | 20 | **Critical** |
| `approve_document` archive old (#14) | 4 | 5 | 20 | **Critical** |
| `on_trash()` block delete (#1, BR-05-02) | 2 | 5 | 10 | High |
| GW-2 gate cho IMM-04 (BR-05-07) | 3 | 5 | 15 | **Critical** |
| `check_document_expiry` idempotent (#6) | 4 | 4 | 16 | **Critical** |
| `_apply_visibility_filter` RBAC (#8) | 3 | 4 | 12 | High |
| `mark_exempt` role guard (#25) | 3 | 4 | 12 | High |
| `_resolve_alert_level` (#7) | 3 | 3 | 9 | Medium |
| `list_documents` pagination (#17) | 3 | 2 | 6 | Medium |
| `get_dashboard_stats` (#20) | 2 | 2 | 4 | Low |
| `get_compliance_by_dept` (#22) | 2 | 2 | 4 | Low |

**Quy ước priority**:
- **Critical** (R ≥ 15): test trước, fail = block release
- **High** (10 ≤ R < 15): bắt buộc trước go-live
- **Medium** (5 ≤ R < 10): trong sprint khi có thời gian
- **Low** (R < 5): chỉ test khi báo cáo bug

## I.4. Scope

**In-scope**:
- Lifecycle Asset Document: upload → gửi duyệt → approve/reject → active → archive/expire (#1, #5, #11–#16)
- Version control auto-archive (BR-05-01) và block delete (BR-05-02)
- Scheduler expiry alert idempotent (#6, BR-05-03)
- RBAC + visibility filter Internal_Only (#8, BR-05-10) và mark_exempt role guard (#25)
- 16 API endpoint (#26): envelope, pagination, permission

**Out-of-scope**:
- Performance test → giao Phần III.8 (target-only, chưa benchmark)
- Penetration test → Phần VI.10 (trước go-live)
- GW-2 gate logic chi tiết thuộc IMM-04 → ở đây chỉ smoke cross-module (BR-05-07)
- Auto-import từ IMM-04 → integration smoke; logic mint asset thuộc IMM-04

**Assumptions**: master data (AC Asset, Required Document Type, AC Department) đã seed; test users đã tạo đủ các role; Chrome ≥ 120 cho E2E; file fixtures (PDF nhỏ/lớn/sai định dạng) sẵn sàng.

---

# Phần II — Test Design Techniques (Kỹ thuật thiết kế test case)

> Mỗi test phải truy được về 1 kỹ thuật ở dưới.

## II.1. Black-box techniques

| Kỹ thuật | Khi nào dùng | Áp dụng vào IMM-05 | Số test sinh ra (rule of thumb) |
|---|---|---|---|
| **Equivalence Partitioning (EP)** | Input có miền giá trị chia nhóm | `doc_category` (Legal/Technical/Certification/Training/QA), `visibility` (Public/Internal_Only), workflow_state enum | 1 test/partition |
| **Boundary Value Analysis (BVA)** | Numeric / date có biên | `days_remaining` mốc 90/60/30/0 trong `_resolve_alert_level`; `expiry_date` vs `issued_date`; `version` "1.0" vs khác | 2-3 test/biên |
| **Decision Table** | Multi-condition gate | GW-2 (license Active AND NOT exempt), BR-05-01 (active duplicate), `_can_see_internal` (role ∈ internal set) | 2^N rút gọn theo equivalence |
| **State Transition Testing** | Workflow finite state machine | `'IMM-05 Document Workflow'` (fixtures/workflow.json): Draft → {Pending Review, Archived} · Pending Review → {Active, Rejected} · Rejected → Pending Review · Active → Archived. `Expired` = declared-dead terminal (0 transition dẫn vào; hết hạn = thuộc tính dẫn xuất, BR-05-16 / ADR-IMM-05-02). | Mỗi transition + invalid transition + INV-CTA-1 (map↔fixture) |
| **Use Case Testing** | End-to-end actor flow | UAT scenarios, API integration test | 1/main + 1/alt + 1/exception |
| **Pairwise / Combinatorial** | Nhiều field optional kết hợp | Form tạo Asset Document (doc_category × visibility × is_exempt) | Min set cover all pairs |
| **Error Guessing** | Lỗi từ kinh nghiệm: null, empty, sai định dạng file, delete | `on_trash`, file .exe, file > 25MB, name không tồn tại | Bổ sung — không thay thế |

## II.2. White-box techniques

| Kỹ thuật | Áp dụng vào | Tiêu chí đạt | Công cụ |
|---|---|---|---|
| **Statement coverage** | Service functions `services/imm05.py` (I.1 #6–#25) | ≥ 85% line | `coverage report` |
| **Branch / Decision coverage** | Functions có if/else, try/except (`update_document` state guard, `_resolve_alert_level`, `approve_document`) | ≥ 80% branch | `coverage --branch` |
| **Condition / MC/DC** | GW-2 gate (license Active AND NOT exempt), `_can_see_internal` multi-role OR | Mỗi sub-condition kiểm soát outcome độc lập | Manual test design + coverage |
| **Path coverage** | `_resolve_alert_level` (≤ 20 LOC, 5 nhánh mốc) | Toàn bộ path khả dĩ | Manual |

> Ưu tiên Branch coverage cho service layer; MC/DC chỉ áp dụng vào GW-2 gate và visibility logic.

## II.3. Mapping Component → Kỹ thuật

| Loại component | Kỹ thuật chính | Kỹ thuật phụ |
|---|---|---|
| Field validator (VR-01/VR-02/VR-09) | BVA + EP | Error guessing |
| Gate logic (GW-2, BR-05-01 duplicate) | Decision Table | MC/DC |
| Workflow transition | State Transition | Use Case |
| Service function pure (`_resolve_alert_level`) | EP + Branch coverage | BVA |
| API endpoint | Use Case + EP | Pairwise (form input) |
| Scheduler (`check_document_expiry`) | Use Case (setup → run → assert) | Error guessing (idempotent re-run) |
| FE view (Playwright) | Use Case end-to-end | Error guessing (network 4xx/5xx, role gate) |

---

# Phần III — Test Plan (Kế hoạch thực thi)

## III.1. Test Pyramid

```
                  ┌────────────┐
                  │  E2E / UAT │   ~5%   ← Playwright; Golden upload → approve → expire
                 ─┴────────────┴─
              ┌──────────────────────┐
              │   API Integration    │   ~15%  ← 16 whitelist endpoints
             ─┴──────────────────────┴─
          ┌────────────────────────────────┐
          │  Workflow + DocType lifecycle  │   ~25%  ← 9 transition, 6 state
         ─┴────────────────────────────────┴─
      ┌────────────────────────────────────────────┐
      │         Unit — Service Layer               │   ~55%  ← services/imm05.py
     ─┴────────────────────────────────────────────┴─
```

→ CLAUDE.md §17 (TDD mandatory).

**Trạng thái thực tế (2026-05-29):** business logic đã refactor ra `assetcore/services/imm05.py` (24 hàm — xem I.1). Test hiện tại nằm trong **một file duy nhất** `assetcore/tests/test_imm05.py`; các file con `test_imm05_workflow.py` / `_api.py` / `_audit.py` / `test_asset_document_doctype.py` mô tả dưới đây là **kế hoạch chia file** (⬜ Planned), hiện chưa tách.

## III.2. Unit test — Service Layer

**File:** `assetcore/tests/test_imm05.py` (đang có) — các test sau ✅ Live đã được viết thật trong file này.

| Test class | Function cover (I.1) | Kỹ thuật | Cases (happy/negative) | Status |
|---|---|---|---|---|
| `TestResolveAlertLevel` | `_resolve_alert_level` (#7) | BVA (mốc 0/30/90/91) | 8 / 0 | ✅ Live |
| `TestCreateDocument` | `create_document` (#11) | EP | 2 / 0 | ✅ Live |
| `TestUpdateDocument` | `update_document` (#13) | State guard / EP | 1 / 2 (active blocked, not found) | ✅ Live |
| `TestApproveDocument` | `approve_document` (#14) | Decision Table (archive old) | 1 / 1 + 1 archive assert | ✅ Live |
| `TestRejectDocument` | `reject_document` (#15) | EP | 1 / 2 (no reason, bad state) | ✅ Live |
| `TestListDocuments` | `list_documents` (#17) | EP (pagination) | 2 / 0 | ✅ Live |
| `TestKpiExpiredDocs` | `get_dashboard_stats` (#20) | EP | 2 / 0 (expiry-only filter) | ✅ Live |
| `TestExpiredSoT` (`test_imm05.py`) | `expired_filter()` SoT + count↔drill (BR-05-16 / **INV-EXP-1**) | **Counterexample** (Active doc `expiry_date=today-5,is_expired=1` → count≥1 ∧ drill `{expiry_status:'expired'}` chứa đúng doc) + **Invariant** (`expired_not_renewed == len(list_documents({expiry_status:'expired'}).items)`, chênh=0 đa-tập) + **EP/tightening** (Archived/Rejected quá hạn KHÔNG đếm; Active/Draft/Pending Review quá hạn ĐẾM) | 5 / 0 | ⬜ Planned (BE viết) |
| `TestDepreciationDefaults` | (chia sẻ helper depreciation) | EP | 3 / 0 | ✅ Live |
| `TestGenerateScheduleZeroPrice` | (chia sẻ helper depreciation) | BVA / Error guessing | 1 / 2 | ✅ Live |
| `TestFullyDepreciatedSoT` (`test_depreciation.py`) | `is_fully_depreciated` / `is_configured_for_depreciation` SoT (BR-05-15) | BVA (book==residual, +1, +2; residual=0→book≤1) + Decision Table (configured) | 4 / 5 (NOT configured, +2, book=2, book=None→gross) | ✅ Live |
| `TestFullyDepreciatedReadPath` (`test_imm05.py`) | `get_depreciation_stats` count ↔ `list_assets_depreciation(depreciation_filter)` drill (INV-DEP-5) | Invariant (count==drill) + EP (AND method/category) + Regression (other keys) | 6 / 0 | ✅ Live |
| `TestVisibilityFilter` | `_apply_visibility_filter` (#8) | Decision Table | — | ⬜ Planned |
| `TestSubmitForReview` | `submit_for_review` (#12) | EP + Error guessing (no file) | — | ⬜ Planned |
| `TestArchiveDocument` | `archive_document` (#16) | EP | — | ⬜ Planned |
| `TestMarkExempt` | `mark_exempt` (#25) | Decision Table + role guard | — | ⬜ Planned |
| `TestGetAssetDocuments` | `get_asset_documents` (#19) | EP (completeness) | — | ⬜ Planned |

> Test thuần công thức (`_resolve_alert_level`) dùng `unittest.TestCase` không cần DB — chạy ms-level, không cần fixture cleanup.

## III.3. Integration — DocType lifecycle

**File:** `assetcore/tests/test_asset_document_doctype.py` ⬜ Planned (chưa tách). Cover hook `validate / on_submit / on_update_after_submit / on_trash`.

| Test | Setup | Action | Assert | Kỹ thuật |
|---|---|---|---|---|
| `test_on_trash_always_blocked` | Asset Document bất kỳ | `frappe.delete_doc(...)` | `frappe.ValidationError` (BR-05-02) | Error guessing |
| `test_submit_without_file_blocked` | Draft, no attachment | gửi duyệt | `ValidationError` chứa "VR" file | EP |
| `test_approve_archives_old_active` | 1 Active same type | doc mới → Active | doc cũ `workflow_state == "Archived"`, `superseded_by` set | Decision Table |
| `test_change_summary_required_v2` | `version = "2.0"` | save không change_summary | `ValidationError` chứa "change_summary" (BR-05-09) | BVA |

> Fixture trong `setUpClass` phải có `tearDownClass` purge — xem `assetcore-test` LL-TEST-17.

## III.4. Integration — Workflow transitions

**File:** `assetcore/tests/test_imm05.py` (module `assetcore.tests.test_imm05`). Workflow `'IMM-05 Document Workflow'` (`fixtures/workflow.json`): **6 state** (Draft, Pending Review, Active, Rejected, Archived, **Expired** — declared-dead, giữ theo ADR-IMM-05-02). Cạnh unique SAU Self-Correction = 6: `Draft→Pending Review`, **`Draft→Archived` (Hủy bỏ — THÊM MỚI)**, `Pending Review→Active`, `Pending Review→Rejected`, `Rejected→Pending Review`, `Active→Archived`. `Archived`/`Expired` = 0 outbound.

> **BR-05-16 / ADR-IMM-05-02 — state `Expired` GIỮ (supersede COUPLED TEST CONTRACT cũ):** contract cũ yêu cầu gỡ state-def `Expired` + hạ `test_workflows.py` `min_states` 6→5. **Quyết định mới:** GIỮ `Expired` (declared-dead terminal) → `test_workflows.py` giữ `min_states 6` (KHÔNG đổi), fixture giữ 6 state. Ngữ nghĩa derived-expiry (fix bug count-vs-drill ở read-path `expired_filter` + FE marker) KHÔNG phụ thuộc state-def → vẫn xanh. Gỡ `Expired` là backlog dọn-dẹp độc lập, KHÔNG thuộc change CTA này.

**(a) State Transition Testing — mỗi edge = 1 pass + 1 fail (invalid transition / wrong role):**

| Transition (action) | From → To | Role required (allowed) | Test pass | Test fail |
|---|---|---|---|---|
| Gửi duyệt | Draft → Pending Review | PM User | ☐ | ☐ (no file) |
| Gửi duyệt | Draft → Pending Review | AssetCore Super Admin | ☐ | — |
| Hủy bỏ | Draft → Archived | Compliance Manager / Super Admin (`doc.approve`) | ☐ | ☐ (no doc.approve) |
| Phê duyệt | Pending Review → Active | Compliance Manager | ☐ | ☐ (wrong role) |
| Phê duyệt | Pending Review → Active | AssetCore Super Admin | ☐ | — |
| Từ chối | Pending Review → Rejected | Compliance Manager | ☐ | ☐ (no reason) |
| Từ chối | Pending Review → Rejected | AssetCore Super Admin | ☐ | — |
| Gửi lại | Rejected → Pending Review | PM User | ☐ | — |
| Gửi lại | Rejected → Pending Review | AssetCore Super Admin | ☐ | — |
| Lưu trữ | Active → Archived | Compliance Manager / Super Admin (`doc.approve`) | ☐ | ☐ (wrong role) |

**(b) INV-CTA-1 — invariant map ↔ fixture (BẮT BUỘC, chống drift):** đọc `fixtures/workflow.json` entry `'IMM-05 Document Workflow'`, dựng `codomain[state] = {t.next_state}`. Assert:
1. `set(_DOC_VALID_TRANSITIONS.keys()) == set(states[])` (6 key: Draft, Pending Review, Active, Rejected, Archived, Expired).
2. Với MỖI state: `set(_DOC_VALID_TRANSITIONS[state]) == codomain[state]` (thêm/sửa transition mà quên map → RED).
3. Mọi value-state ∈ `DocState` enum (0 extra).

Mirror `test_imm11.TestCalibrationAllowedTransitions`. **Chỉ xanh SAU khi thêm cạnh `Draft→Archived` vào fixture (04 §3.2).**

**(c) `get_document` enrich — contract 2 khóa:** với ≥3 state (Draft, Pending Review, Active), `get_document(name)` trả `allowed_transitions == _DOC_VALID_TRANSITIONS[state]` VÀ chứa khóa `can_approve` ∈ {0,1}; MỌI khóa cũ của AssetDocument vẫn còn (backward-compat).

**(d) `can_approve` theo quyền:** user có `doc.approve` (Compliance Manager) → `can_approve == 1`; user KHÔNG có (vd technician-only) → `can_approve == 0`. (FE gating false-permissive test ở vitest — 06 §7.5.)

**Run:** `bench --site miyano run-tests --module assetcore.tests.test_imm05` → `Ran N OK` (không FAIL/ERROR).

## III.5. Integration — Audit chain integrity

**File:** `assetcore/tests/test_imm05_audit.py` ⬜ Planned. 2 test chính:
- (a) Sau chuỗi mutation (create → submit → approve), `get_document_history(name)` (#23) trả ≥ 3 entry và chain hợp lệ.
- (b) `check_document_expiry` chạy 2 lần cùng ngày → Expiry Alert Log không sinh duplicate (idempotent theo `alert_date` + `asset_document`).

→ 04 Backend §Audit Trail · Frappe `Version` DocType + `Expiry Alert Log`.

> *(Cần khảo sát)*: hiện chưa xác minh có `IMM Audit Trail` chain SHA-256 cho Asset Document hay chỉ dùng Frappe `Version`. Test tamper-hash chỉ áp dụng nếu chain hash tồn tại.

## III.6. API test

**File:** `assetcore/tests/test_imm05_api.py` ⬜ Planned. 16 endpoint (verify từ `api/imm05.py`).

| Test | Endpoint | Verify | Kỹ thuật |
|---|---|---|---|
| `test_list_default_pagination` | `list_documents` | `success=true`, page=1, page_size=20 | Use Case |
| `test_list_internal_hidden` | `list_documents` (non-internal role) | No Internal_Only rows | EP (visibility) |
| `test_get_existing` | `get_document` | `success=true`, fields đầy đủ | Use Case |
| `test_get_not_found` | `get_document?name=FAKE` | `code=NOT_FOUND` | Error guessing |
| `test_create_happy` | `create_document` | `success=true`, name trả về | Use Case |
| `test_create_invalid` | `create_document` (no asset_ref) | `code=VALIDATION` | EP |
| `test_submit_for_review` | `submit_for_review` | state → Pending Review | Use Case |
| `test_approve_archives_old` | `approve_document` | old doc → Archived | Decision Table |
| `test_reject_no_reason` | `reject_document` (empty) | `code=VALIDATION` | EP |
| `test_archive_document` | `archive_document` | state → Archived | Use Case |
| `test_get_asset_documents` | `get_asset_documents` | completeness % đúng | Use Case |
| `test_get_dashboard_stats` | `get_dashboard_stats` | KPI fields trả về | Use Case |
| `test_get_expiring_documents` | `get_expiring_documents?days=30` | chỉ doc ≤ 30d | BVA |
| `test_get_compliance_by_dept` | `get_compliance_by_dept` | list theo dept | Use Case |
| `test_document_history` | `get_document_history` | ≥ 1 version entry | Use Case |
| `test_create_get_request` | `create_document_request` / `get_document_requests` | request tạo + truy vấn | Use Case |
| `test_mark_exempt` | `mark_exempt` | is_exempt=1 | Decision Table |
| `test_mark_exempt_wrong_role` | `mark_exempt` (low-role) | `code=FORBIDDEN` / PermissionError | EP (permission partition) |

Cover bắt buộc: envelope `success=true` · `INVALID_PARAMS` / `VALIDATION` · `FORBIDDEN` · pagination boundary · idempotent retry.

## III.7. E2E browser (Playwright)

Dùng cho flow UI khó cover bằng API: dropdown cascade (asset → model/dept auto-fill), modal confirm approve/reject, hiển thị nút workflow theo role, upload file attachment.

→ `assetcore-test` skill Phần 2 (Playwright MCP recipes + R-1..R-9 data rules). Golden scenario ở V.4 (UAT-IMM-05-01/03/05).

## III.8. Performance test

Target-only (chưa benchmark). Tool **k6** hoặc `pytest-benchmark`.

| Metric | Target | Method |
|---|---|---|
| `list_documents` p95 (500 docs) | ≤ 800ms | k6 GET ramping 20 VU |
| `get_asset_documents` p95 (50 docs/asset) | ≤ 500ms | k6 |
| `approve_document` (archive old) p95 | ≤ 1.5s | k6 POST |
| Scheduler `check_document_expiry` (1000 Active) | ≤ 60s | `time bench execute …` |

## III.9. Test data & Fixtures

| Loại | Cách seed | File |
|---|---|---|
| Master (AC Asset, AC Department, Required Document Type) | `fixtures/*.json` (qua `bench migrate`) | `assetcore/fixtures/` |
| Test records (Asset Document các state) | `test_records.json` per DocType | `asset_document/test_records.json` *(Cần khảo sát — có thể chưa tồn tại)* |
| Test PDF (nhỏ / > 25MB / sai định dạng) | file tĩnh | `tests/fixtures/imm05/` *(Cần khảo sát)* |
| UAT seed | Python script | `assetcore/scripts/uat/uat_imm05.py` *(Cần khảo sát — chưa verify tồn tại)* |

> UAT data phải thực tế (tên bệnh viện VN, mã NCC chuẩn). Backend test fixture mới dùng prefix `_Test` — xem `assetcore-test` R-0/R-1.

## III.10. Run commands & Coverage gate

```bash
# Module test (file hiện có)
bench --site assetcore.local run-tests --app assetcore --module assetcore.tests.test_imm05
# Coverage
coverage run -m unittest assetcore.tests.test_imm05 && coverage report
# Scheduler thủ công
bench --site assetcore.local execute assetcore.services.imm05.check_document_expiry
```

| Layer | Target coverage | Đo |
|---|---|---|
| Service (`services/imm05.py`) | ≥ 85% line + ≥ 80% branch | `coverage --branch` |
| DocType lifecycle | ≥ 70% | `coverage report` |
| API (`api/imm05.py`) | ≥ 60% | `coverage report` |
| Frontend (vue-tsc) | 0 error | `npm run build` |

> Coverage % thực tế: *(Cần khảo sát — chưa chạy `coverage report`)*. Chỉ ghi target.

---

# Phần IV — Traceability Matrices

> Mọi test ở Phần III phải xuất hiện ở cả 3 bảng.

## IV.1. US → Test mapping

| US ID | AC | Test ID (III.x) | Layer | Status |
|---|---|---|---|---|
| US-05-01 | AC1 | `TestCreateDocument::test_create_returns_name_and_state` | Unit | ✅ Live |
| US-05-01 | AC2 | `TestCreateDocument::test_default_version_is_1_0` | Unit | ✅ Live |
| US-05-02 | AC1 | `TestApproveDocument::test_approve_pending_review_succeeds` | Unit | ✅ Live |
| US-05-02 | AC2 | `TestRejectDocument::test_reject_without_reason_raises` | Unit | ✅ Live |
| US-05-03 | AC1 | `test_auto_import_from_imm04_on_submit` | Integration | ⬜ Planned |
| US-05-04 | AC1 | `TestResolveAlertLevel::*` (8 case) | Unit | ✅ Live |
| US-05-04 | AC2 | `test_expiry_alert_log_idempotent` | Integration | ⬜ Planned |
| US-05-05 | AC1 | `TestKpiExpiredDocs::test_expired_kpi_counts_draft_doc` | Unit | ✅ Live |
| US-05-06 | AC1 | `test_get_asset_documents_completeness` | Integration/API | ⬜ Planned |
| US-05-07 | AC1 | `TestApproveDocument::test_approve_archives_old_active` | Unit | ✅ Live |
| US-05-08 | AC1 | `test_create_get_request` | API | ⬜ Planned |
| US-05-09 | AC1 | `TestMarkExempt` | Unit | ⬜ Planned |

## IV.2. BR → Test mapping

| BR ID | Phát biểu (rút gọn) | Test ID | Kỹ thuật | Happy / Negative |
|---|---|---|---|---|
| BR-05-01 | 1 Active per (asset+type), archive cũ | `TestApproveDocument::test_approve_archives_old_active` | Decision Table | 1 / 0 (negative ⬜ Planned) |
| BR-05-02 | Không xóa cứng | `test_on_trash_always_blocked` ⬜ | Error guessing | 0 / 1 ⬜ Planned |
| BR-05-03 | Expiry alert 90/60/30/0 idempotent | `TestResolveAlertLevel::*` ✅ + `test_expiry_alert_log_idempotent` ⬜ | BVA | 8 / 0 (idempotent ⬜) |
| BR-05-04 | Auto-import từ IMM-04 | `test_auto_import_from_imm04_on_submit` ⬜ | Use Case | ⬜ Planned |
| BR-05-05 | Completeness qua Required Document Type | `test_get_asset_documents_completeness` ⬜ | EP | ⬜ Planned |
| BR-05-06 | `is_model_level` áp dụng theo model | *(Cần khảo sát)* | EP | ⬜ Planned |
| BR-05-07 | GW-2 block IMM-04 | `test_gw2_gate_blocks_commissioning` ⬜ (IMM-04) | Decision Table | ⬜ Planned |
| BR-05-08 | Exempt → Compliant (Exempt) | `TestMarkExempt` ⬜ | Decision Table | ⬜ Planned |
| BR-05-09 | change_summary bắt buộc v ≠ 1.0 | `test_change_summary_required_v2` ⬜ | BVA | ⬜ Planned |
| BR-05-10 | Internal_Only ẩn với non-internal | `TestVisibilityFilter` ⬜ | Decision Table | ⬜ Planned |
| BR-05-16 | "Đã hết hạn" 1 SoT `expired_filter()`, count==drill, loại Archived/Rejected, không dead-state | `TestExpiredSoT` ⬜ (counterexample + INV-EXP-1 + tightening) + FE `documentFilters.test.ts` (`{expiry_status:'expired'}` + grep-guard no-`Expired`) | Invariant + Counterexample + EP | 5 / 0 ⬜ Planned (BE/FE viết) |

**Gap thật:** chỉ BR-05-01/03 và phần happy-path đang có test ✅ Live trong `test_imm05.py`; các negative test và BR còn lại là ⬜ Planned (chưa viết). BR-05-16 là deliverable Vòng 19 (BE viết `TestExpiredSoT` + sửa FE `documentFilters.test.ts` 2 assert đang lock dead-state — line 46 + 81).

## IV.3. Component → Test mapping

| Component (I.1) | Test ID | Test layer | Coverage % | Risk priority (I.3) |
|---|---|---|---|---|
| `_resolve_alert_level` (#7) | `TestResolveAlertLevel` | Unit | *(Cần khảo sát)* | Medium |
| `create_document` (#11) | `TestCreateDocument` | Unit | *(Cần khảo sát)* | Medium |
| `update_document` (#13) | `TestUpdateDocument` | Unit | *(Cần khảo sát)* | Medium |
| `approve_document` (#14) | `TestApproveDocument` | Unit | *(Cần khảo sát)* | Critical |
| `reject_document` (#15) | `TestRejectDocument` | Unit | *(Cần khảo sát)* | High |
| `list_documents` (#17) | `TestListDocuments` | Unit | *(Cần khảo sát)* | Medium |
| `get_dashboard_stats` (#20) | `TestKpiExpiredDocs` | Unit | *(Cần khảo sát)* | Low |
| Workflow (#5) | `test_imm05_workflow.py` ⬜ | Integration | 0% (chưa viết) | Critical |
| `check_document_expiry` (#6) | `test_expiry_alert_log_idempotent` ⬜ | Integration | 0% (idempotent chưa viết) | Critical |
| `_apply_visibility_filter` (#8) | `TestVisibilityFilter` ⬜ | Unit | 0% | High |
| `mark_exempt` (#25) | `TestMarkExempt` ⬜ | Unit | 0% | High |
| 16 API endpoint (#26) | `test_imm05_api.py` ⬜ | API | 0% | High |

---

# Phần V — UAT Script

## V.1. Phạm vi UAT

**In-scope**:
- Upload → gửi duyệt → approve/reject (US-05-01/02, BR-05-01)
- Version control auto-archive (US-05-07, BR-05-01)
- Block xóa document (BR-05-02)
- Expiry alert scheduler idempotent (US-05-04, BR-05-03)
- Auto-import từ IMM-04 (US-05-03, BR-05-04)
- Completeness (BR-05-05), GW-2 gate (BR-05-07), Exempt (BR-05-08)
- Visibility filter Internal_Only (BR-05-10), Dashboard KPIs (US-05-05), phân quyền mỗi role

**Out-of-scope**: load testing (III.8), penetration testing (Phần VI).

**Pre-condition**: UAT site deploy bản mới nhất; seed data chạy; tester accounts active đủ các role; ≥ 3 Asset đã mint từ IMM-04; Chrome ≥ 120.

## V.2. Tester accounts

> Phải có account role thấp (read-only) để cover FORBIDDEN case, không chỉ Admin.

| Username | Role | Vai trò UAT |
|---|---|---|
| `test_super` | AssetCore Super Admin | Approve/Reject, archive, mark exempt, full flow |
| `test_docmgr` | Document Manager | Approve/Reject, submit, cancel |
| `test_docuser` | Document User | Upload, gửi duyệt (không approve) |
| `test_pm` | PM User | Gửi duyệt / gửi lại (workflow) |
| `test_compliance` | Compliance Manager | Phê duyệt / từ chối (workflow) |
| `test_auditor` | AssetCore Auditor | Read-only — cover FORBIDDEN trên create/approve |

> Các role workflow (PM User, Compliance Manager) lấy từ `imm_05_document_workflow.json`; các role DocPerm (Document Manager/User, Auditor) lấy từ `asset_document.json`. Mật khẩu UAT reset sau phiên.

## V.3. Test data đã seed

| DocType | Số lượng | Ghi chú |
|---|---|---|
| AC Asset | 5 | CT, X-Ray, Pump, Ventilator, LINAC (2 thiết bị bức xạ) |
| Required Document Type | 5 | CO, CQ, Manual, License, Radiation License |
| Asset Document | 8 | Draft / Pending Review / Active / Rejected / Archived (5 state) + ≥1 Active đã quá hạn (`expiry_date<today, is_expired=1`) để cover BR-05-16 counterexample |
| Test PDF | 3 | nhỏ (<1MB), lớn (>25MB), sai định dạng (.exe) |

Reset script: `bench --site uat.assetcore.local execute assetcore.scripts.uat.uat_imm05.seed_data` *(Cần khảo sát — verify script tồn tại)*.

## V.4. UAT Scenarios — Suy ra từ US + Activity

Mỗi scenario theo template Phụ lục A. ID `UAT-IMM-05-NN`.

| ID | Actor | Pre-condition | US/BR cover | Kỹ thuật | Kết quả mong đợi |
|---|---|---|---|---|---|
| UAT-IMM-05-01 | Document User → Compliance Manager | Asset đã mint | US-05-01, BR-05-01 | Use Case happy | Doc → Active |
| UAT-IMM-05-02 | Compliance Manager → Document User | Doc Pending Review | US-05-02, BR-05-01 | Use Case alt | Reject (có lý do) → gửi lại → Active |
| UAT-IMM-05-03 | Document User + Compliance Manager | 1 Active v1.0 | US-05-07, BR-05-01 | State Transition | Approve v2.0 → v1.0 Archived, `superseded_by` set |
| UAT-IMM-05-04 | AssetCore Super Admin | 1 Archived doc | BR-05-02 | Error guessing | Xóa bị block (`on_trash` raise) |
| UAT-IMM-05-05 | System (scheduler) | Active doc expiry +90/+30/0 | US-05-04, BR-05-03 | Use Case + BVA | Alert đúng mốc, idempotent; khi quá hạn → `is_expired=1` (state GIỮ Active, KHÔNG đổi sang "Expired" — BR-05-16) |
| UAT-IMM-05-05b | Workshop Head | Active doc `expiry_date=today-5`, `is_expired=1` | BR-05-16, INV-EXP-1 | Counterexample + drill | Tile "Đã hết hạn" đếm ≥1; click tile → list chứa đúng doc; số tile == số dòng list |
| UAT-IMM-05-06 | System (IMM-04 submit) | Commissioning Clinical Release | US-05-03, BR-05-04 | Use Case | ≥ 3 Asset Document, `source_module="IMM-04"` |
| UAT-IMM-05-07 | Document User | — | VR-01/VR-02/VR-09 | EP + BVA | Validation rule raise đúng thông báo |
| UAT-IMM-05-08 | Auditor / Document User | doc Internal_Only | BR-05-10, Phần VI | EP permission | Auditor không create; Internal_Only ẩn với non-internal |
| UAT-IMM-05-09 | Document Manager | có doc các state | US-05-05 | Use Case | Dashboard KPI đúng, drill-down List |
| UAT-IMM-05-10 | Compliance Manager / Super Admin | Asset thiếu License doc | BR-05-07 | Decision Table | GW-2 block IMM-04 Release; exempt bypass |

**Chi tiết scenario chính:**

### UAT-IMM-05-01 — Upload tài liệu mới và gửi duyệt (Happy Path)
**Liên kết**: US-05-01, BR-05-01
**Role tester**: Document User → Compliance Manager
**Mục tiêu**: Upload doc, gửi duyệt, approve → Active.
**Pre-condition**: Asset đã mint từ IMM-04.

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | `test_docuser` vào `/app/asset-document/new` | Form trống, state = Draft | ☐ |
| 2 | Chọn Asset; doc_category = Legal; doc_type_detail = Giấy phép nhập khẩu | `model_ref`, `clinical_dept` tự fill | ☐ |
| 3 | Điền doc_number, issuing_authority, issued_date, expiry_date | `days_until_expiry` tự tính | ☐ |
| 4 | Upload PDF hợp lệ + Save | Saved, naming series đúng | ☐ |
| 5 | Gửi duyệt | state = Pending Review | ☐ |
| 6 | `test_compliance` mở doc, Phê duyệt | state = Active; `approved_by` set | ☐ |

**Post-condition**: 1 Active doc cho (asset + type).
**Acceptance**: Tất cả step Pass + version/audit entry tương ứng.

### UAT-IMM-05-05 — Expiry Alert Scheduler (BR-05-03)
**Liên kết**: US-05-04, BR-05-03
**Role tester**: System
**Mục tiêu**: Scheduler sinh alert đúng mốc 90/30/0, idempotent.

| Step | Hành động | Kết quả mong đợi | Pass/Fail |
|---|---|---|---|
| 1 | Seed Active doc expiry = today + 90 | — | ☐ |
| 2 | Chạy `check_document_expiry` | Alert level = Info (90), `days_remaining = 90` | ☐ |
| 3 | Chạy lại cùng ngày | Không tạo duplicate (idempotent) | ☐ |
| 4 | Đổi expiry = today + 30, chạy lại | Alert level = Critical | ☐ |
| 5 | Đổi expiry = today-1, chạy lại | `is_expired=1` (state GIỮ Active); alert Danger; doc xuất hiện trong KPI/drill "Đã hết hạn" (BR-05-16) | ☐ |

**Acceptance**: 5 step Pass.

## V.5. Tổng hợp kết quả & Bug found

| Scenario | Status | Tester | Ngày | Ghi chú |
|---|---|---|---|---|
| UAT-IMM-05-01 | ☐ Pass / ☐ Fail | | | |
| UAT-IMM-05-02 | ☐ Pass / ☐ Fail | | | |
| UAT-IMM-05-03 | ☐ Pass / ☐ Fail | | | |
| UAT-IMM-05-04 | ☐ Pass / ☐ Fail | | | |
| UAT-IMM-05-05 | ☐ Pass / ☐ Fail | | | |
| UAT-IMM-05-06 | ☐ Pass / ☐ Fail | | | |
| UAT-IMM-05-07 | ☐ Pass / ☐ Fail | | | |
| UAT-IMM-05-08 | ☐ Pass / ☐ Fail | | | |
| UAT-IMM-05-09 | ☐ Pass / ☐ Fail | | | |
| UAT-IMM-05-10 | ☐ Pass / ☐ Fail | | | |

**Bug log:**

| Issue ID | Severity | Mô tả | Fix status |
|---|---|---|---|
| IMM05-BUG-001 | Minor | Email notification dùng inline string, chưa dùng Email Template DocType | Known — deferred |
| IMM05-BUG-002 | Minor | Test suite chưa tách file (workflow/api/audit gộp trong `test_imm05.py`) | Tech-debt |

**Acceptance**: ≥ 95% PASS, Blocker = 0, Major ≤ 2 (có workaround documented).

**Sign-off UAT:**

| Vai trò | Người | Ngày | Chữ ký |
|---|---|---|---|
| BA Lead | | | |
| QA Lead | | | |
| Module Owner (IMM-05) | | | |
| Đại diện end-user (Tổ HC-QLCL) | | | |

---

# Phần VI — Security Review (gate)

## VI.1. RBAC

**Role definitions** (`fixtures/role.json` + `role_profile.json`). Role thực tế liên quan IMM-05 (verify từ `asset_document.json` + workflow JSON): AssetCore Super Admin, Document Manager, Document User, AssetCore Auditor, AssetCore System User, PM User, Compliance Manager.

**DocPerm matrix — `Asset Document`** (verify từ `asset_document.json`):

| Role | Read | Write | Create | Submit | Cancel | Amend | Delete |
|---|---|---|---|---|---|---|---|
| AssetCore Super Admin | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ |
| Document Manager | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ |
| Document User | ✅ | ✅ | ✅ | ❌ | ❌ | — | ❌ |
| AssetCore Auditor | ✅ | ❌ | ❌ | ❌ | ❌ | — | ❌ |
| AssetCore System User | ✅ | ❌ | ❌ | ❌ | ❌ | — | ❌ |

> **Lưu ý quan trọng (gap thật):** DocPerm hiện cho phép `delete=1` với Super Admin + Document Manager. BR-05-02 (không xóa cứng) **phải** được enforce ở tầng controller `on_trash()` raise — nếu `on_trash` chưa block thì đây là lỗ hổng compliance NĐ98. *(Cần khảo sát: xác minh `asset_document.py::on_trash` có raise không.)*

**Field-level permission (permlevel)**: DocType `Asset Document` hiện **không** có field nào đặt `permlevel ≠ 0` (verify từ JSON — tất cả field permlevel=0). Các field nhạy cảm (`approved_by`, `rejection_reason`, `is_exempt`, `exempt_reason`, `visibility`) hiện chỉ bảo vệ qua DocPerm + workflow role, **chưa** có field-level lock. → Khuyến nghị bổ sung permlevel cho `approved_by`/`is_exempt`/`visibility` (gap, xem DoD).

**User Permission (row-level)**: visibility filter `Internal_Only` áp dụng qua `_apply_visibility_filter()` + `_can_see_internal()` trong `services/imm05.py` (BR-05-10) — non-internal role không thấy doc `Internal_Only`.

**Kỹ thuật**: Decision Table — mỗi (role × action × state) là 1 row, expected Allow/Deny.

## VI.2. API security

| Mục | Trạng thái | Ghi chú |
|---|---|---|
| Whitelist hygiene | *(Cần khảo sát)* | 16 endpoint trong `api/imm05.py`; verify mỗi endpoint có docstring + role check (`_require_approve_role` / `_require_exempt_role` cho mutating) |
| CSRF | ✅ | Frappe default `X-Frappe-CSRF-Token` |
| Input validation | *(Cần khảo sát)* | `name` Link field validate; attachment extension/size check trong service |
| SQL injection | ✅ | Frappe ORM parameterized; không f-string vào raw SQL |
| Rate limit | ⚠️ Roadmap | Cần config cho `approve_document`, `create_document` |

## VI.3. Audit trail integrity

- Mọi state change ghi qua Frappe `Version` DocType (auto); `get_document_history()` truy vấn được.
- `Expiry Alert Log` immutable — không Delete permission cho bất kỳ role nào *(Cần khảo sát: verify permissions JSON đã loại Delete)*.
- `check_document_expiry` idempotent theo `alert_date` + `asset_document`.
- BR-05-02: `on_trash` raise để chặn xóa cứng (ISO 13485:7.5.9) — **cần verify** vì DocPerm vẫn cho delete=1.
- Retention ≥ 5 năm theo NĐ98/2021 Điều 15.

→ III.5 test cases.

## VI.4. Authentication & session

| Hạng mục | Config |
|---|---|
| Login | Frappe default (username + password) |
| Session timeout | 8 giờ |
| Lockout | 3 fail → lock 15 phút |
| Password policy | ≥ 8 ký tự, 1 chữ hoa, 1 số |
| API key | Per-user, rotate 90 ngày |
| 2FA | Roadmap Phase 2 |

## VI.5. Data sensitivity

| Loại | Trường | Sensitivity | Bảo vệ |
|---|---|---|---|
| Giấy phép BYT (Legal) | `file_attachment` (doc_category=Legal) | Confidential | DocPerm + visibility filter |
| Lý do từ chối | `rejection_reason` | Internal | DocPerm (permlevel chưa đặt — gap) |
| Quyết định exempt | `is_exempt`, `exempt_reason` | Confidential | `_require_exempt_role()` guard |
| Người phê duyệt | `approved_by` | Internal | DocPerm |
| Dữ liệu bệnh nhân | Không lưu | N/A | AssetCore KHÔNG lưu patient data |

## VI.6. Vendor isolation

`AssetCore System User` (ngoài) chỉ có Read trên `Asset Document` theo DocPerm; không Write/Create/Submit. Không có quyền xem chi phí, rejection_reason, exempt fields ở mức nghiệp vụ; doc `Internal_Only` ẩn qua `_apply_visibility_filter()`. Không export.

→ test case III.6 (low-role API call: `mark_exempt` / `approve_document` → FORBIDDEN).

## VI.7. Secrets management

- `site_config.json` không commit git.
- External token lưu `frappe.conf`, không hardcode.
- File attachment lưu Frappe private files path (không public URL mặc định).
- Backup encrypt at-rest, off-site (xem `08_Deployment.md`).

## VI.8. Logging & monitoring

| Sự kiện | Log level | Where | Alert? |
|---|---|---|---|
| Document quá hạn (`is_expired=1`, scheduler) | WARNING | Scheduler log + Expiry Alert Log | ✅ Email Document Manager |
| Document Request overdue | WARNING | Scheduler log | ✅ Email Document Manager |
| `on_trash` attempt | ERROR | `frappe.log_error` | ❌ |
| Approve/Reject action | INFO | Frappe access log + Version | ❌ |
| Login fail | INFO | Frappe login log | ✅ (sau 3 lần) |
| File upload fail (size/format) | INFO | Frappe error log | ❌ |

PII / token KHÔNG vào log.

## VI.9. Threat model (STRIDE-lite)

| Threat | Vector | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| **S**poofing | Giả mạo session Compliance Manager | Low | High | Session HttpOnly + SameSite |
| **T**ampering — Delete doc | Xóa record qua admin/API | Medium | Critical | `on_trash` raise (cần verify) + giảm DocPerm delete |
| **T**ampering — Backdate expiry | Edit `expiry_date` sau approve | Low | High | permlevel/field lock sau Active (gap — chưa có permlevel) |
| **R**epudiation | Phủ nhận đã Approve | Low | High | `approved_by` + `approval_date` + Frappe Version |
| **I**nfo disclosure | Non-internal role thấy Internal_Only | Low | Medium | `_apply_visibility_filter()` + UAT-08 |
| **D**enial of service | Expiry check 10,000+ Active docs | Low | Medium | Batch/run; index `expiry_date + workflow_state` |
| **E**levation of privilege | Document User self-approve | Low | High | Workflow role: Phê duyệt chỉ Compliance Manager / Super Admin |

## VI.10. Penetration test

Trước release đầu tiên: Burp/ZAP scan trên UAT (0 High/Critical), sqlmap an toàn, CSRF test (curl không token), role escalation (`approve_document` / `mark_exempt` với role thấp → FORBIDDEN), thử `frappe.delete_doc("Asset Document", ...)` → kỳ vọng raise. Report lưu `docs/security/pentest_imm05_v1.md`.

## VI.11. Sign-off

| Role | Người | Ngày | Quyết định |
|---|---|---|---|
| QA Lead | | | ☐ Pass / ☐ Pass with conditions / ☐ Fail |
| Security Officer | | | ☐ Pass / ☐ Pass with conditions / ☐ Fail |
| Module Owner | | | ☐ Pass / ☐ Pass with conditions / ☐ Fail |

**Điều kiện go-live**: tất cả Sign-off Pass / Pass with conditions (workaround documented).

---

# Phần VII — Code Quality

## VII.1. Tool matrix

| Tool | Mục tiêu | Target | Cadence |
|---|---|---|---|
| **SonarQube** (BE Python) | Bug 0 Critical, code smell ≤ 5, duplication ≤ 3%, coverage ≥ 70%, security hotspot review 100% | Quality Gate pass | Mỗi PR (CI gate) |
| **Lighthouse** (FE Document views) | Performance ≥ 90, Accessibility ≥ 95, Best Practices ≥ 90, SEO ≥ 80 | ≥ target | Mỗi release + monthly |
| **ESLint + vue-tsc** | 0 error, 0 warning prod build | pass | Mỗi PR FE (CI gate) |
| **ruff / black** (BE) | 0 error, format PEP8 | pass | Mỗi PR (CI gate) |
| **Bundle size** (FE chunk imm05) | main ≤ 250KB gzip, async ≤ 80KB gzip | ≤ budget | Mỗi PR FE (CI report) |

## VII.2. Cadence

- SonarQube: mỗi PR (CI gate, fail nếu Quality Gate fail)
- Lighthouse: mỗi release lớn + monthly audit
- ESLint / ruff: mỗi PR (CI gate)
- Bundle size: mỗi PR FE (CI report, fail nếu vượt budget)

Screenshot SonarQube + Lighthouse gắn vào `09_Release.md §Release Notes` khi báo cáo final.

---

# Phụ lục A — Template per UAT scenario

```markdown
### UAT-IMM05-<NN> — <Tên>

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
### TC-IMM05-<LAYER>-<NN> — <Tên>

**Component (I.1)**: <…>
**Liên kết**: US-<NN> | BR-<NN> | ACT-<NN>
**Kỹ thuật (II.1/II.2)**: BVA boundary `expiry_date = issued_date`
**Priority (I.3)**: Critical / High / Medium / Low
**Test type**: Unit / Integration / API / E2E
**Pre-condition**: <fixture / state setup>

**Input**:
- <field>: <value>

**Steps**:
1. <…>
2. <…>

**Expected**:
- ServiceError(code=VALIDATION, message contains "VR-09")
- doc.workflow_state unchanged

**Post-condition**: <DB rollback / fixture cleanup>
```

# Phụ lục C — Workflow State Transition Test template

```markdown
### TC-IMM05-WF-<NN> — <action>: <from> → <to>

**Workflow JSON**: `assetcore/assetcore/workflow/imm_05_document_workflow.json`
**Role required**: <…>
**Pre-condition**: doc.workflow_state = <from>
**Action**: apply_workflow(doc, "<action>")
**Expected (happy)**: doc.workflow_state = <to>, docstatus = <…>, version entry created
**Expected (negative role)**: PermissionError / FORBIDDEN
**Expected (gate fail)**: ValidationError (vd thiếu rejection_reason / thiếu file)
```

---

# DoD — File 07 hoàn chỉnh

## I. Test Analysis
- [x] I.1 Component Inventory liệt kê đủ artefact (đối chiếu 04/05/06 — 27 dòng)
- [x] I.2 mỗi US / BR / Activity có ≥ 1 dòng map
- [x] I.3 Risk priority gán cho mọi component (không trống)
- [x] I.4 Scope ghi rõ out-of-scope kèm lý do

## II. Test Design Techniques
- [x] II.1 chọn ≥ 4 black-box techniques (EP + BVA + Decision Table + State Transition)
- [x] II.2 white-box criteria xác định (statement + branch)
- [x] II.3 mapping component → kỹ thuật điền đầy đủ

## III. Test Plan
- [ ] Test class cho mọi service public function — chỉ ~9/24 hàm có test ✅ Live; còn lại ⬜ Planned
- [ ] ≥ 1 happy + 1 negative mỗi function — nhiều hàm chỉ có happy hoặc chưa test
- [ ] Workflow transitions cover 100% (9 transition) — chưa viết `test_imm05_workflow.py`
- [ ] Audit chain test (idempotent + version) — chưa viết
- [ ] API test ≥ 60% + permission matrix — chưa viết `test_imm05_api.py`
- [x] Performance target xác định (target-only)
- [x] CI command chạy clean (`run-tests --module assetcore.tests.test_imm05`)
- [ ] SonarQube Quality Gate pass + Lighthouse ≥ target — chưa chạy

## IV. Traceability
- [x] IV.1 US → Test: mọi US có ≥ 1 Test ID (live hoặc planned)
- [ ] IV.2 BR → Test: mọi BR có happy + negative — phần lớn negative ⬜ Planned
- [ ] IV.3 Component → Test: Critical/High đạt coverage target — coverage % chưa đo

## V. UAT
- [x] Mỗi US có ≥ 1 UAT scenario
- [x] ≥ 1 negative + permission + audit verify scenario
- [ ] Test data seed script chạy được — `uat_imm05.py` chưa verify tồn tại
- [x] Tester accounts đủ các role thật (gồm role thấp Auditor)
- [x] Sign-off section sẵn sàng

## VI. Security
- [x] DocPerm matrix đầy đủ (5 role thật, Decision Table)
- [ ] Mọi field nhạy cảm có permlevel ≠ 0 — gap thật: DocType chưa đặt permlevel nào
- [ ] SQL injection + CSRF test pass — CSRF mặc định OK; injection chưa test riêng
- [ ] Audit chain test pass — chưa viết
- [ ] Vendor isolation test pass (low-role API) — chưa viết
- [x] Threat model đủ 6 STRIDE với mitigation
- [x] Sign-off section sẵn sàng

## VII. Code Quality
- [ ] SonarQube Quality Gate pass — chưa chạy
- [ ] Lighthouse ≥ target — chưa chạy
- [ ] Bundle size ≤ budget — chưa đo
- [ ] Screenshot báo cáo gắn vào file 09 — chưa có
