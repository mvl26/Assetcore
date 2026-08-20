# 07 — Kiểm thử & An ninh (Testing & QA & Security)

> ⚠ **[ROADMAP — Wave 3 / Chưa scaffold]**
> Module IMM-10 chưa có code: không có `assetcore/services/imm10.py`, không có `assetcore/api/imm10.py`, chưa có `assetcore/tests/test_imm10*.py`.
> File này là **kế hoạch test (planning skeleton)**. Test ID chính thức (`TC-IMM10-…`), coverage % thực tế, naming series, ErrorCode và DocType fieldname sẽ được chốt khi sprint Wave 3 mở và phụ thuộc IMM-16 (Compliance Rule Engine) GA trước. Mọi ô đánh dấu *(Cần thiết kế khi scaffold BE)* / ⬜ Planned KHÔNG được tự ý fill nếu chưa có code/user story chốt.

| Mục | Giá trị |
|---|---|
| Module | IMM-10 — Hậu kiểm và tuân thủ (Post-market Surveillance) |
| Phạm vi | Per-module |
| Owner | QA Lead + Security Officer |
| Liên kết | 02 Analysis (US, BR, Activity, BPMN) · 03 Diagrams · 04 Backend · 05 API · 06 Frontend |

> **Mục đích**: Suy ra test case **có hệ thống** từ phân tích (file 02) bằng kỹ thuật black-box + white-box, không liệt kê tự phát. Bao gồm: phân tích đối tượng test → chọn kỹ thuật → viết test → traceability → UAT → security → code quality. Phần VII là gate go-live.

---

# Phần I — Test Analysis (Phân tích đối tượng test)

> Mục tiêu Phần I: trả lời 4 câu hỏi trước khi viết test case: **(1) test cái gì** (component inventory) **(2) suy ra từ đâu** (US/BR/Activity) **(3) ưu tiên cái nào** (risk) **(4) loại trừ cái nào** (out-of-scope).

## I.1. Component Inventory — Liệt kê phần mềm cần test

Inventory dưới đây liệt kê artefact **dự kiến** theo thiết kế 04/05/06. Tên DocType và endpoint là planned (đã có trong docs); fieldname, signature chi tiết, repo method còn ở dạng skeleton. Mỗi dòng → ≥ 1 test class ở Phần III khi scaffold.

→ Nguồn: 04 Backend §I (DocType), §II (Service), §III (Workflow), §IV (Hook) · 05 API §2 (Catalog) · 06 Frontend §I–II (Components/Views)

| # | Component | Loại | File / Tên (planned) | Test layer áp dụng |
|---|---|---|---|---|
| 1 | `IMM Compliance Case` | DocType (submittable) | `doctype/imm_compliance_case/` | Integration (lifecycle) |
| 2 | `IMM Affected Asset` (child) | DocType (child) | child of Compliance Case | Integration (lifecycle) |
| 3 | `IMM Disclosure Log` (child) | DocType (child) | child of Compliance Case | Integration (lifecycle) |
| 4 | `IMM Effectiveness Check` | DocType (child/standalone) | *(Cần thiết kế khi scaffold BE)* | Integration |
| 5 | `IMM Recall Action Template` | DocType | `doctype/imm_recall_action_template/` | Integration |
| 6 | `IMM-10 Compliance Workflow` | Workflow | `fixtures/imm10_compliance_workflow.json` | Integration (state transition) |
| 7 | `open_case` / `find_scope` / `lock_scope` | Service function | `services/imm10.py::open_case` … | Unit + API |
| 8 | `start_disclosure_timer` / `send_disclosure` | Service function | `services/imm10.py` | Unit + API |
| 9 | `bulk_create_recall_wo` | Service function (idempotent) | `services/imm10.py::bulk_create_recall_wo` | Unit + Integration |
| 10 | `close_case` / `schedule_effectiveness_check` | Service function | `services/imm10.py` | Unit + Integration |
| 11 | `validate_case` (validator BR/VR) | Validator | `services/imm10.py::validate_case` | Unit (BVA/EP/Decision Table) |
| 12 | `ComplianceCaseRepo` | Repository / DAO | `repositories/compliance_case_repo.py` | Integration (DB) |
| 13 | 13 endpoint catalog (open/find/lock/disclose/bulk/close/get/list/…) | API endpoint | `api/imm10.py` | API integration |
| 14 | `compliance.case.opened/.scope_locked/.disclosure_sent/.closed` | Lifecycle/Audit event | `hooks.py → utils/lifecycle` | Integration (audit chain) |
| 15 | `check_disclosure_breach` (hourly) | Scheduler job | `services/imm10.py::check_disclosure_breach` | Unit + Cron simulation |
| 16 | `run_effectiveness_check` / `detect_chronic_failure_signals` / `capa_tracker_alert` / `feed_management_review` | Scheduler jobs | `services/imm10.py` | Unit + Cron simulation |
| 17 | `subscribe_chronic_failure_signal` / `subscribe_calibration_fail_signal` | Hook subscriber | `hooks.py doc_events` | Integration (cross-module) |
| 18 | `compliance_case_query` | permission_query_conditions | `permissions.py::compliance_case_query` | Integration (RBAC isolation) |
| 19 | `ComplianceDashboard.vue` / `ComplianceCaseDetail.vue` / `ScopeFinder.vue` / `DisclosurePanel.vue` / `BulkRecallActions.vue` / `CAPATracker.vue` | FE view | `frontend/src/views/imm10/` | E2E (Playwright) |
| 20 | `useComplianceStore` | Pinia store | `frontend/src/stores/imm10.ts` | Unit (vitest) |

## I.2. Trace nguồn test — User Stories, Activity Flows, Business Rules

3 bảng dẫn từ artefact phân tích (02) sang test layer. Mỗi US/BR/Activity phải có ≥ 1 test ở Phần III và xuất hiện trong matrix Phần IV khi scaffold.

→ Nguồn: 02 §IV.1 (US) · 02 §IV.2 (BR) · 02 §IV.3 (VR) · 02 §II.2 (BPMN To-Be) · 02 §III (UC)

### I.2.a. Từ User Story
| US ID | Tiêu đề ngắn | Acceptance Criteria # | Test layer dự kiến |
|---|---|---|---|
| US-10-01 | Mở case từ email vendor, ghi vết + đếm 48h | AC: case_no sinh, timer kích hoạt | Unit + API + UAT |
| US-10-02 | Auto-find affected assets (không tra Excel) | AC: scope list trả đúng asset | Unit + Integration + UAT |
| US-10-03 | Template công văn disclosure tự fill | AC: disclosure log + sent_at | API + UAT |
| US-10-04 | Workshop nhận bulk WO Recall | AC: N WO tạo với ref case | Integration + UAT |
| US-10-05 | Dashboard 1 trang: recall/% hoàn thành/CAPA quá hạn | AC: KPI cards | API + E2E |
| US-10-06 | Nhắc effectiveness check 30/60/90 ngày | AC: scheduler tạo task | Unit + Cron + UAT |

### I.2.b. Từ Business Rule
| BR ID | Phát biểu (rút gọn) | Component liên quan (I.1) | Kỹ thuật test phù hợp |
|---|---|---|---|
| BR-10-01 | severity=Critical → disclosure_required + timer 48h | #8, #11 | Decision Table |
| BR-10-02 | Không submit nếu affected_assets rỗng mà scope_criteria non-empty | #11 | Decision Table / EP |
| BR-10-03 | Bulk WO chỉ tạo khi state=Action Pending + vendor confirm | #9 | Decision Table |
| BR-10-04 | Đóng case: 100% WO Closed HOẶC waived (cần BGĐ) | #10 | Decision Table |
| BR-10-05 | Disclosure breach → escalation + finding IMM-16 | #15 | State Transition / Use Case |
| BR-10-06 | CAPA preventive bắt buộc cho severity ≥ High | #10 | Decision Table |
| BR-10-07 | Effectiveness check 30/60/90; quá 14 ngày → flag | #16 | BVA (ngày) + Cron |
| BR-10-08 | Mọi action ghi `IMM Audit Trail` (hash chain SHA-256) | #14 | Use Case (audit chain) |

Validation Rules (02 §IV.3) bổ sung input cho BVA/EP:
| VR ID | Phát biểu | Kỹ thuật |
|---|---|---|
| VR-10-01 | `disclosure_due_at = recall_confirmed_at + 48h` (UTC) | BVA (biên thời gian, sai số < 1 phút) |
| VR-10-02 | `case_no` autoname `CC-{YYYY}-{####}` *(naming series chốt khi scaffold)* | EP |
| VR-10-03 | `severity` enum Low/Medium/High/Critical | EP (1 test/partition) |
| VR-10-04 | `case_type` enum Recall/FSCA/PMS Signal | EP |
| VR-10-05 | Source ≥ 1 ref (vendor_notice / regulator_doc / internal_signal) | Decision Table / Error guessing |

### I.2.c. Từ Activity Flow / BPMN
| Activity (02 §II.2) | Use Case | Branch chính | Branch ngoại lệ |
|---|---|---|---|
| [1] Open case | UC-10-01/02/03 | Happy: case Draft tạo | Source rỗng cả 3 ref (VR-10-05) |
| [2] Auto-find scope | UC-10-04 | Happy: list asset đúng | Asset đã decommission → `historical=true` |
| [3]+[4] Disclosure timer + gửi công văn | UC-10-05 | Happy: log + sent_at | Breach 48h → Escalated (BR-10-05) |
| [5]+[6] Stand-down + bulk WO | UC-10-06/07 | Happy: N WO tạo | Re-call idempotent → skipped |
| [7]+[8] Track completion + close | UC-10-08 | Happy: 100% → Closed | WO chưa đủ → block close (BR-10-04) |
| [9] CAPA preventive | UC-10-08 | Happy: CAPA linked | severity ≥ High thiếu CAPA → block (BR-10-06) |
| [10] Effectiveness check | UC-10-10 | Happy: pass 30/60/90 | Fail → re-open Action Pending |
| [11] Management Review feed | UC-10-11 | Happy: entry sang IMM-16 | — |

## I.3. Risk-based Priority

| Component (I.1) | Likelihood (1-5) | Impact (1-5) | Risk = L×I | Priority |
|---|---|---|---|---|
| #15 check_disclosure_breach (NĐ98 48h) | 4 | 5 | 20 | **Critical** |
| #11 validate_case (BR/VR gate) | 4 | 5 | 20 | **Critical** |
| #14 Audit chain integrity | 3 | 5 | 15 | **Critical** |
| #18 compliance_case_query (vendor isolation) | 3 | 5 | 15 | **Critical** |
| #9 bulk_create_recall_wo (idempotency) | 4 | 4 | 16 | **Critical** |
| #10 close_case (CAPA gate, approver) | 3 | 4 | 12 | High |
| #6 Workflow transitions | 3 | 4 | 12 | High |
| #7/#8 open_case/find_scope/disclosure | 3 | 4 | 12 | High |
| #16 effectiveness/chronic-failure scheduler | 3 | 3 | 9 | Medium |
| #17 signal subscribers (cross-module) | 2 | 4 | 8 | Medium |
| #13 read endpoints (get/list/dashboard) | 2 | 2 | 4 | Low |
| #19/#20 FE view + store | 2 | 2 | 4 | Low |

**Quy ước priority**:
- **Critical** (R ≥ 15): test trước, fail = block release
- **High** (10 ≤ R < 15): bắt buộc trước go-live
- **Medium** (5 ≤ R < 10): trong sprint khi có thời gian
- **Low** (R < 5): chỉ test khi báo cáo bug

## I.4. Scope

- **In-scope**: (1) service layer 9 function (I.1 #7–#11); (2) workflow `IMM-10 Compliance Workflow` toàn bộ transition; (3) disclosure timer 48h + breach escalation; (4) bulk recall WO idempotency; (5) audit chain + vendor/role isolation.
- **Out-of-scope**:
  - Compliance Rule Engine, Internal Audit, Management Review *engine* — thuộc IMM-16 (IMM-10 chỉ test phần đăng ký rule + feed entry, smoke).
  - Calibration/Repair xử lý kỹ thuật — thuộc IMM-11/IMM-09 (IMM-10 chỉ test subscribe tín hiệu).
  - Hồ sơ pháp lý cấp phép — thuộc IMM-05.
  - Performance test giao Phần III.8; security giao Phần VI.
- **Assumptions**: IMM-16 đã GA; master data (AC Asset, IMM Device Model, AC Supplier) đã seed; test users đủ role (không chỉ Admin); IMM-04/08/09 stable cho cross-module write.

---

# Phần II — Test Design Techniques (Kỹ thuật thiết kế test case)

> Mỗi test phải truy được về 1 kỹ thuật ở dưới.

## II.1. Black-box techniques

| Kỹ thuật | Khi nào dùng | Áp dụng vào IMM-10 (I.1) | Số test sinh ra (rule of thumb) |
|---|---|---|---|
| **Equivalence Partitioning (EP)** | Input có miền giá trị chia nhóm | `severity` (VR-10-03), `case_type` (VR-10-04) enum; role permission partition (#18) | 1 test/partition |
| **Boundary Value Analysis (BVA)** | Numeric / date có biên | `disclosure_due_at` = +48h (VR-10-01); effectiveness check ngày 30/60/90, quá hạn 14 ngày (BR-10-07) | 2-3 test/biên |
| **Decision Table** | Multi-condition gate | BR-10-01/02/03/04/06, VR-10-05 (source ≥ 1 ref) | 2^N rút gọn theo equivalence |
| **State Transition Testing** | Workflow finite state machine | `IMM-10 Compliance Workflow` (Draft → … → Closed → Effectiveness Check) — xem 03 Hình 7 | Mỗi transition + invalid transition |
| **Use Case Testing** | End-to-end actor flow | UAT scenarios (Phần V), API integration | 1/main + 1/alt + 1/exception |
| **Pairwise / Combinatorial** | Nhiều field optional kết hợp | Form open_case (case_type × severity × source_ref × scope_criteria) | Min set cover all pairs |
| **Error Guessing** | null, empty, unicode, race | Mọi endpoint nhận user input; re-call bulk WO; double disclosure | Bổ sung |

## II.2. White-box techniques

| Kỹ thuật | Áp dụng vào | Tiêu chí đạt | Công cụ |
|---|---|---|---|
| **Statement coverage** | Service functions (I.1 #7–#11, #15–#16) | ≥ 85% line | `coverage report` |
| **Branch / Decision coverage** | Functions có if/else, try/except (validate_case, close_case, bulk_create) | ≥ 80% branch | `coverage --branch` |
| **Condition / MC/DC** | BR gate (BR-10-01/04/06) multi-AND | Mỗi sub-condition kiểm soát outcome độc lập | Manual + coverage |
| **Path coverage** | find_scope reconcile logic (≤ 20 LOC) | Toàn bộ path (loop = 0,1,N asset) | Manual |

Ưu tiên Branch coverage cho service layer; MC/DC chỉ áp dụng vào BR gate logic.

## II.3. Mapping Component → Kỹ thuật

| Loại component | Kỹ thuật chính | Kỹ thuật phụ |
|---|---|---|
| Field validator (VR-10-*) | BVA + EP | Error guessing |
| Gate logic (BR-10-*) | Decision Table | MC/DC |
| Workflow transition | State Transition | Use Case |
| Service function pure (find_scope) | EP + Branch coverage | BVA |
| API endpoint (13 endpoint) | Use Case + EP | Pairwise (form input) |
| Scheduler (check_disclosure_breach, effectiveness) | Use Case (setup → run → assert) | Error guessing (lock, partial fail) |
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

→ CLAUDE.md §17 (TDD mandatory). Tỷ lệ thực tế ghi lại khi scaffold Wave 3.

## III.2. Unit test — Service Layer

File `tests/test_imm10.py` (⬜ Planned — sẽ tạo khi scaffold). Test class trace về service function ở I.1 #7–#11, #15–#16. Test ID chính thức `TC-IMM10-UNIT-NN` chốt khi code có; bảng dưới là kế hoạch unit dẫn từ 02 + 04 + 05.

| Test class (planned) | Function cover | Kỹ thuật | Cases (happy/negative) |
|---|---|---|---|
| `TestOpenCase` | `open_case` | Decision Table (VR-10-05) + EP | 1 / 2 (source rỗng → INVALID_SOURCE; scope criteria sai → INVALID_SCOPE_CRITERIA) |
| `TestFindScope` | `find_scope` | EP + Path (loop 0/1/N) | 2 / 1 (asset decommission → historical=true; scope locked → SCOPE_LOCKED) |
| `TestLockScope` | `lock_scope` | State Transition | 1 / 1 (re-run sau lock → SCOPE_LOCKED) |
| `TestDisclosureTimer` | `start_disclosure_timer` | BVA (VR-10-01, +48h, sai số < 1 phút) | 1 / 1 |
| `TestSendDisclosure` | `send_disclosure` | Use Case + Error guessing | 1 / 2 (lần 2 → ALREADY_DISCLOSED; non-regulatory → NOT_REGULATORY_GRADE) |
| `TestBulkCreateRecallWO` | `bulk_create_recall_wo` | Decision Table (BR-10-03) + idempotency | 1 / 2 (scope chưa lock → SCOPE_NOT_LOCKED; re-call → skipped) |
| `TestCloseCase` | `close_case` | Decision Table (BR-10-04/06) + MC/DC | 1 / 3 (WO chưa đủ → INCOMPLETE_ACTIONS; CAPA chưa mở → CAPA_NOT_OPEN; thiếu approver → NEED_APPROVER) |
| `TestEffectivenessCheck` | `schedule_effectiveness_check` / `run_effectiveness_check` | BVA (BR-10-07) + Cron | 2 / 1 |
| `TestCheckDisclosureBreach` | `check_disclosure_breach` | Use Case + Cron simulation | 1 / 1 (breach → escalate + finding IMM-16) |

Dùng `SimpleNamespace` cho test thuần công thức (vd timer +48h) — chạy ms-level, không cần fixture cleanup.

## III.3. Integration — DocType lifecycle

File `tests/test_imm_compliance_case_doctype.py` (⬜ Planned). Cover hook `validate / on_submit / on_update_after_submit / on_cancel` (04 §IV.1). Fieldname cụ thể *(Cần thiết kế khi scaffold BE)*.

| Test (planned) | Setup | Action | Assert | Kỹ thuật |
|---|---|---|---|---|
| `test_validate_source_required` | case không ref | `doc.insert()` | raise (VR-10-05) | Decision Table |
| `test_critical_sets_disclosure` | severity=Critical | `doc.save()` | `disclosure_required=true`, timer set | EP |
| `test_affected_assets_immutable_after_lock` | scope locked | sửa child | reject | State Transition |
| `test_on_submit_publishes_lifecycle` | case Verifying→Closed | `doc.submit()` | `Asset Lifecycle Event` `recall_completed` | Use Case |

Fixture trong `setUpClass` phải có `tearDownClass` purge.

## III.4. Integration — Workflow transitions

File `tests/test_imm10_workflow.py` (⬜ Planned). **Bắt buộc** cover mọi transition trong workflow JSON khi scaffold (đếm bằng `python3 -c "import json; print(len(json.load(open('fixtures/imm10_compliance_workflow.json'))['transitions']))"`). Bảng dưới dẫn từ 04 §III.1 + 03 Hình 7 — **8 transition dự kiến**.

| # | Transition (action VN) | From → To | Role required | Test pass | Test fail (wrong role / gate) |
|---|---|---|---|---|---|
| 1 | Xác nhận tín hiệu | Draft → Scope Identification | IMM QA Officer | ⬜ | ⬜ |
| 2 | Khóa scope (regulatory) | Scope Identification → Disclosure Pending | IMM QA Officer | ⬜ | ⬜ |
| 3 | Khóa scope (nội bộ) | Scope Identification → Action Pending | IMM QA Officer | ⬜ | ⬜ |
| 4 | Đã gửi công văn | Disclosure Pending → Action Pending | IMM Document Officer | ⬜ | ⬜ |
| 5 | Quá 48h (System) | Disclosure Pending → Escalated | (System scheduler) | ⬜ | ⬜ |
| 6 | Hoàn tất 100% asset | Action Pending → Verifying | IMM Workshop Lead | ⬜ | ⬜ |
| 7 | Phê duyệt đóng | Verifying → Closed | IMM Operations Manager | ⬜ | ⬜ |
| 8 | (System scheduler) | Closed → Effectiveness Check | (System) | ⬜ | ⬜ |

> Lưu ý: 03 Hình 7 còn vẽ thêm cạnh `Escalated → Action Pending`, `Verifying → Action Pending` (re-open), `Effectiveness Check → Action Pending` (fail). Khi scaffold, đếm lại transition từ JSON thật và bổ sung dòng tương ứng — mỗi cạnh = 1 test pass + 1 test fail.

**Kỹ thuật**: State Transition Testing — vẽ state graph; mỗi edge = 1 test pass + 1 test fail.

## III.5. Integration — Audit chain integrity

File `tests/test_imm10_audit.py` (⬜ Planned). 2 test chính (dẫn từ BR-10-08, 04 §II.2):
- (a) Sau N mutation trên 1 case (open → scope_locked → disclosure_sent → closed), chain hash SHA-256 hợp lệ end-to-end.
- (b) Khi 1 entry bị tamper (sửa `change_summary`), verify endpoint trả `chain_broken=true`.

→ 04 Backend §II.2 (log_audit_event API) · `IMM Audit Trail` DocType (Wave 1).

## III.6. API test

File `tests/test_imm10_api.py` (⬜ Planned). Endpoint catalog dẫn từ 05 §2 (13 endpoint). Cover: happy + envelope `success=true`; invalid params; no permission → FORBIDDEN; pagination; idempotent retry.

| Test (planned) | Endpoint (05 §2) | Verify | Kỹ thuật |
|---|---|---|---|
| `test_open_case_ok` | POST `api/imm10.open_case` | `success=true`, `case_no`, `workflow_state` | Use Case |
| `test_open_case_no_source` | POST `api/imm10.open_case` | `code=IMM10_INVALID_SOURCE` | Decision Table |
| `test_find_scope_locked` | POST `api/imm10.find_scope` | `code=IMM10_SCOPE_LOCKED` | EP |
| `test_send_disclosure_twice` | POST `api/imm10.send_disclosure` | `code=IMM10_ALREADY_DISCLOSED` | Error guessing |
| `test_bulk_wo_idempotent` | POST `api/imm10.bulk_create_recall_wo` (×2) | lần 2 `created=[]`, `skipped` đầy | idempotency |
| `test_close_capa_not_open` | POST `api/imm10.close_case` | `code=IMM10_CAPA_NOT_OPEN` (BR-10-06) | Decision Table |
| `test_list_cases_vendor_scope` | GET `api/imm10.list_cases` (Vendor role) | chỉ case của vendor đó | EP (permission partition) |
| `test_open_case_low_role` | POST `api/imm10.open_case` (no QA Officer) | `code=IMM10_PERMISSION_DENIED` / FORBIDDEN | EP (permission) |
| `test_list_cases_pagination` | GET `api/imm10.list_cases` | `items/total/limit/offset` (05 §5) | BVA |

> ErrorCode `IMM10_*` ở 05 §4 là **danh sách tham khảo** — code chính thức append vào `services/shared/constants.py::ErrorCode` khi scaffold; KHÔNG hard-code chuỗi.

## III.7. E2E browser (Playwright)

Dùng cho flow UI khó cover bằng API (06 §VI): cascade `vendor → model → lot/serial` trong form open_case; DisclosureTimer countdown + color shift; CAPATracker filter; workflow button visibility theo role; AffectedAssets bulk select.

→ `assetcore-test` skill Phần 2 (Playwright MCP recipes + R-1..R-9 data rules). FE chưa scaffold → E2E ⬜ Planned.

## III.8. Performance test

Migrate từ §VII (file cũ) — target dẫn từ 02 §V NFR.

| Metric | Target | Method |
|---|---|---|
| `find_scope` trên 100k asset | < 5s | k6 / `time bench execute` |
| `bulk_create_recall_wo` cho 100 asset | < 30s (async job OK) | k6 POST batch |
| Dashboard load với 50 case open | < 2s | k6 GET `dashboard_summary` |
| `list_cases` với 1000 case (pagination 50) | < 1s | k6 GET `list_cases` |

## III.9. Test data & Fixtures

| Loại | Cách seed | File |
|---|---|---|
| Master data (AC Asset, IMM Device Model, AC Supplier) | `fixtures/*.json` (qua `bench migrate`) | `assetcore/fixtures/` |
| Workflow + SLA + Action Template | `fixtures/imm10_*.json` (04 §IV.4) | `assetcore/fixtures/imm10_compliance_workflow.json`, `imm10_recall_action_template.json`, `imm10_sla_policy.json` *(⬜ Planned)* |
| Test records | `test_records.json` per DocType | `imm_compliance_case/test_records.json` *(⬜ Planned)* |
| UAT seed | Python script | `assetcore/scripts/uat/uat_imm10.py` *(⬜ Planned — Sprint Wave 3)* |

UAT data phải **thực tế** (tên BV VN, mã NCC chuẩn). Backend test fixture mới dùng prefix `_Test` — xem `assetcore-test` R-0/R-1.

## III.10. Run commands & Coverage gate

```bash
# Module test (sau khi scaffold)
bench --site assetcore.local run-tests --app assetcore --module assetcore.tests.imm10.test_imm10
# Coverage
coverage run -m unittest assetcore.tests.imm10.test_imm10 && coverage report
# Workflow smoke
bench --site assetcore.local run-tests --module assetcore.tests.test_imm10_workflow
# UAT golden
bench --site assetcore.local execute assetcore.scripts.uat.uat_imm10.run
# Frontend
cd frontend && npm run test:unit -- imm10 && npm run test:e2e -- imm10
```

| Layer | Target coverage | Đo |
|---|---|---|
| Service (`services/imm10.py`) | ≥ 85% line + ≥ 80% branch (CONVENTIONS §6 tối thiểu ≥ 70%) | `coverage --branch` |
| DocType lifecycle | ≥ 70% | `coverage report` |
| API (`api/imm10.py`) | ≥ 60% | `coverage report` |
| Frontend (vue-tsc) | 0 error | `npm run build` |

> Coverage % **thực tế** chưa đo được (BE chưa scaffold) — cột target only; số thực ghi vào file này Sprint Wave 3.

---

# Phần IV — Traceability Matrices

> 3 ma trận theo 3 hướng. Vì module chưa scaffold, cột Status/Coverage để ⬜ Planned; mọi US/BR/component vẫn có dòng để audit ngược khi code có.

## IV.1. US → Test mapping

| US ID | AC | Test ID (III.x) | Layer | Status |
|---|---|---|---|---|
| US-10-01 | case_no + timer | `TestOpenCase` + `test_open_case_ok` | Unit + API | ⬜ Planned |
| US-10-02 | scope list đúng | `TestFindScope` | Unit + Integration | ⬜ Planned |
| US-10-03 | disclosure log | `TestSendDisclosure` + UAT-IMM-10-02 | API + UAT | ⬜ Planned |
| US-10-04 | N WO ref case | `TestBulkCreateRecallWO` + UAT-IMM-10-01 | Integration + UAT | ⬜ Planned |
| US-10-05 | KPI cards | `test_dashboard_summary` (E2E) | API + E2E | ⬜ Planned |
| US-10-06 | scheduler task | `TestEffectivenessCheck` | Unit + Cron | ⬜ Planned |

## IV.2. BR → Test mapping

| BR ID | Phát biểu (rút gọn) | Test ID | Kỹ thuật | Happy / Negative |
|---|---|---|---|---|
| BR-10-01 | Critical → timer 48h | `TestDisclosureTimer` | Decision Table | 1 / 1 ⬜ |
| BR-10-02 | scope rỗng → block submit | `test_validate_source_required` | Decision Table | 1 / 1 ⬜ |
| BR-10-03 | Bulk WO chỉ khi Action Pending | `TestBulkCreateRecallWO` | Decision Table | 1 / 1 ⬜ |
| BR-10-04 | close cần 100% WO / waive | `TestCloseCase` | Decision Table | 1 / 2 ⬜ |
| BR-10-05 | breach → escalate + finding | `TestCheckDisclosureBreach` | State Transition | 1 / 1 ⬜ |
| BR-10-06 | CAPA bắt buộc severity ≥ High | `TestCloseCase` | Decision Table / MC/DC | 1 / 1 ⬜ |
| BR-10-07 | effectiveness 30/60/90, quá 14 ngày flag | `TestEffectivenessCheck` | BVA | 2 / 1 ⬜ |
| BR-10-08 | mọi action ghi audit hash chain | `tests/test_imm10_audit.py` | Use Case | 1 / 1 ⬜ |

## IV.3. Component → Test mapping

| Component (I.1) | Test ID | Test layer | Coverage % | Risk priority (I.3) |
|---|---|---|---|---|
| `services/imm10::validate_case` | `test_validate_*` | Unit | ⬜ (target ≥ 85%) | Critical |
| `services/imm10::check_disclosure_breach` | `TestCheckDisclosureBreach` | Unit + Cron | ⬜ (target ≥ 85%) | Critical |
| `services/imm10::bulk_create_recall_wo` | `TestBulkCreateRecallWO` | Unit + Integration | ⬜ | Critical |
| `IMM Audit Trail` chain | `tests/test_imm10_audit.py` | Integration | ⬜ | Critical |
| `permissions.compliance_case_query` | `test_list_cases_vendor_scope` | Integration | ⬜ | Critical |
| `services/imm10::close_case` | `TestCloseCase` | Unit | ⬜ (target ≥ 85%) | High |
| `IMM-10 Compliance Workflow` | `test_imm10_workflow` (8 transition) | Integration | ⬜ | High |
| `api/imm10` (13 endpoint) | `test_imm10_api` | API | ⬜ (target ≥ 60%) | High |
| FE views (imm10) | Playwright suite | E2E | ⬜ | Low |

---

# Phần V — UAT Script

## V.1. Phạm vi UAT

- **In-scope**: scenario theo US (V.4) — recall vendor end-to-end, FSCA software, disclosure breach, PMS internal signal.
- **Out-of-scope**: performance (III.8), security (Phần VI).
- **Pre-condition**: site UAT deploy version Wave 3 *(version chốt khi release)*; IMM-16 GA; fixture loaded; tester accounts active đủ role.

## V.2. Tester accounts

| Username (planned) | Role | Vai trò UAT |
|---|---|---|
| `qa.officer@uat` | IMM QA Officer | Mở case, find scope, bulk WO, close |
| `doc.officer@uat` | IMM Document Officer | Gửi công văn disclosure |
| `workshop.lead@uat` | IMM Workshop Lead | Thực thi recall action, xác nhận hoàn tất |
| `ops.manager@uat` | IMM Operations Manager (BGĐ) | Phê duyệt đóng case |
| `vendor.v1@uat` | Vendor Engineer | Verify isolation (chỉ thấy case vendor mình) |
| `clinic.head@uat` | Trưởng khoa | Verify chỉ thấy case ≥ High từ Action Pending |

Phải có account role thấp (vendor, trưởng khoa) để cover FORBIDDEN / isolation case — không chỉ Admin.

## V.3. Test data đã seed

| DocType | Số lượng (planned) | Ghi chú |
|---|---|---|
| AC Asset | ≥ 30 (1 model có ≥ 23 đơn vị, vài đã decommission) | cover happy scope + historical flag |
| IMM Device Model | ≥ 3 | scope by model |
| AC Supplier (Vendor) | ≥ 2 (V1, V2) | isolation test |
| IMM Compliance Case seed | ≥ 5 (mỗi state 1) | cover dashboard + list + permission |

Reset script `scripts/uat/uat_imm10.py` *(⬜ Planned — Sprint Wave 3)*.

## V.4. UAT Scenarios — Suy ra từ US + Activity

**Quy tắc suy scenarios** (Use Case Testing): mỗi US → ≥ 1 happy; mỗi Activity branch ngoại lệ (I.2.c) → ≥ 1; mỗi role mutate → ≥ 1 permission verify; mỗi workflow terminal transition → ≥ 1 audit + cross-module hook; ≥ 1 negative per BR Critical.

Các scenario golden dưới đây migrate từ file 07 cũ và gán liên kết US/BR/UC thật.

| ID | Actor | Pre-condition | US/BR cover | Kỹ thuật | Kết quả mong đợi |
|---|---|---|---|---|---|
| UAT-IMM-10-01 | QA Officer + Workshop + BGĐ | vendor notice, IMM-16 GA | US-10-01/02/04, BR-10-01/04/08, UC-10-01/04/06/08 | Use Case happy | Recall end-to-end: 23 asset scope → lock → disclosure 36h → 23 WO Replace → 23/23 close → effectiveness 30/60/90 → entry IMM-16 |
| UAT-IMM-10-02 | QA Officer + Doc Officer | vendor firmware warning | US-10-03, UC-10-02/06, BR-10-06 | Use Case alt | FSCA action=Update Software → bulk WO Repair "firmware 2.1.4" → close → CAPA preventive |
| UAT-IMM-10-03 | QA Officer + System + BGĐ | case Critical lúc T0, disclosure chưa gửi | BR-10-05, UC-10-05 | State Transition (breach) | T0+48h scheduler → Escalated → notify BGĐ + finding IMM-16 → công văn T0+50h → về Action Pending, finding cập nhật response_time |
| UAT-IMM-10-04 | System (S2) + QA Officer | IMM-12 phát hiện 4 incident cùng model/60 ngày | UC-10-03, BR cross-module signal | Use Case (auto-trigger) | Hook `subscribe_chronic_failure_signal` mở case PMS Signal tự động; Officer escalate Recall hoặc đóng |
| UAT-IMM-10-05 | Vendor V1 / Trưởng khoa | seed case của V1 và V2 | NFR §V security | EP permission | V1 chỉ thấy case V1; trưởng khoa chỉ thấy case ≥ High từ Action Pending — verify isolation |

Mỗi scenario chi tiết bước theo template Phụ lục A khi viết script UAT thật.

## V.5. Tổng hợp kết quả & Bug found

- Bảng `Scenario · Status (Pass/Fail/Block) · Tester · Ngày · Ghi chú` — điền khi chạy UAT Sprint Wave 3.
- Bug list: `Issue ID · Severity (Blocker/Major/Minor/Trivial) · Mô tả · Fix status`.
- Acceptance: ≥ 95% PASS, Blocker = 0, Major ≤ 2 (có workaround).
- Sign-off: BA Lead + QA Lead + Module Owner (Tổ HC-QLCL & Risk) + End-user (Pháp chế / Workshop).

---

# Phần VI — Security Review (gate)

## VI.1. RBAC

- **Role definitions** (`fixtures/role.json` + `role_profile.json`): IMM QA Officer, IMM Operations Manager, IMM Document Officer, IMM Workshop Lead, IMM Biomed Technician, Vendor Engineer + clinical (Trưởng khoa).
- **DocPerm matrix** `IMM Compliance Case` (dẫn từ 04 §III.1 role transition + §IV.3) — Decision Table (role × action × state). Fieldname/permlevel cụ thể *(Cần thiết kế khi scaffold BE)*:

| Role | Read | Write | Create | Submit | Cancel | Amend | User Permission / Match |
|---|---|---|---|---|---|---|---|
| IMM QA Officer | ✅ | ✅ | ✅ | ✅ | ⬜ | ⬜ | full |
| IMM Operations Manager (BGĐ) | ✅ | ✅ (approve close) | ⬜ | ✅ | ⬜ | ⬜ | full |
| IMM Document Officer (Pháp chế) | ✅ | ✅ (disclosure) | ⬜ | ⬜ | ⬜ | ⬜ | state ≥ Disclosure Pending |
| IMM Workshop Lead | ✅ (scope phụ trách) | ✅ (action_status) | ⬜ | ⬜ | ⬜ | ⬜ | match: asset thuộc scope |
| Vendor Engineer | ✅ (chỉ vendor mình) | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | match: `vendor` |
| Trưởng khoa (clinical) | ✅ (severity ≥ High, state ≥ Action Pending) | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | match: department |

- **Field-level permission** (permlevel ≠ 0): trường nhạy cảm chi phí recall, internal note, approver — *(Cần thiết kế khi scaffold BE — fieldname chưa lock)*.
- **User Permission**: filter row qua `compliance_case_query` (04 §IV.3) theo vendor / department / scope phụ trách.

**Kỹ thuật**: Decision Table — mỗi (role × action × state) là 1 row, expected Allow/Deny.

## VI.2. API security

- **Whitelist hygiene**: mọi `@frappe.whitelist` trong `api/imm10.py` có docstring + `rbac.require()` + validate input (kiểm khi scaffold).
- **CSRF**: Frappe default `X-Frappe-CSRF-Token` (verify ở `test_csrf` — file cũ S-05).
- **Input validation**: Link field (vendor, model, asset) validate qua `frappe.get_value` trước khi dùng; `scope_criteria.lot_range` reject SQL injection (file cũ S-04).
- **SQL injection**: parameterized only trong `find_scope` query `AC Asset` (03 Hình 4); không f-string vào raw SQL.
- **Rate limit**: cho endpoint mutating (open_case, bulk_create_recall_wo, send_disclosure).

## VI.3. Audit trail integrity

Mọi mutation sinh `IMM Audit Trail` (BR-10-08, hash SHA-256 chain). Verify endpoint + test tamper. User KHÔNG có quyền edit/delete `IMM Audit Trail` (file cũ S-06; DocPerm + `on_trash` guard ISO 13485 §7.5.9).

→ III.5 test cases (audit chain intact + tampered).

## VI.4. Authentication & session

Login Frappe default. Session timeout + lockout + password policy theo site config. API key rotation cho integration. 2FA roadmap *(chốt khi go-live)*.

## VI.5. Data sensitivity

| Loại | Trường (planned) | Sensitivity | Bảo vệ |
|---|---|---|---|
| Recall scope | affected asset list | Internal | RBAC + query condition |
| Disclosure công văn | doc_no, regulator, pdf | Confidential | role IMM Document Officer + BGĐ |
| Chi phí recall / internal note | *(Cần thiết kế khi scaffold BE)* | Confidential | permlevel ≠ 0 |
| Vendor lot list | scope_criteria | Internal | vendor isolation |

Khẳng định: IMM-10 KHÔNG lưu patient data.

## VI.6. Vendor isolation

Vendor Engineer chỉ thấy case có `vendor` = vendor của chính user (qua `permission_query_conditions` `compliance_case_query`, 04 §IV.3). KHÔNG thấy: case vendor khác, chi phí, internal note, audit trail case khác, dashboard. KHÔNG export.

→ test case III.6 `test_list_cases_vendor_scope` + file cũ S-01 (Vendor V1 đọc case V2 → 403).

## VI.7. Secrets management

Cấm commit `.env` / credential. `site_config.json` không lên git. External token (regulator portal nếu có) lưu `frappe.conf`. Backup encrypt at-rest off-site. Case + audit giữ ≥ 5 năm (02 §V NĐ98).

## VI.8. Logging & monitoring

| Sự kiện | Log level | Where | Alert? |
|---|---|---|---|
| open_case / close_case | INFO | frappe logger | — |
| disclosure breach escalation | WARNING | logger + IMM-16 finding | Yes (BGĐ) |
| permission denied (vendor isolation) | WARNING | logger | review |
| audit chain broken | ERROR | logger | Yes |

PII / token KHÔNG vào log.

## VI.9. Threat model (STRIDE-lite)

| Threat | Vector | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| **S**poofing | Giả mạo Document Officer gửi disclosure | Low | High | Frappe auth + role gate + audit actor |
| **T**ampering | Sửa `affected_assets` sau lock / sửa audit entry | Med | High | scope immutable sau lock; audit hash chain SHA-256 (BR-10-08) |
| **R**epudiation | Phủ nhận đã gửi/đã đóng case | Med | High | `IMM Audit Trail` actor + timestamp; disclosure_log |
| **I**nfo disclosure | Vendor thấy case vendor khác / chi phí | Med | High | `compliance_case_query` + permlevel sensitive field |
| **D**enial of service | find_scope 100k asset / bulk WO N+1 | Med | Med | query parameterized + index; async bulk job; pagination |
| **E**levation of privilege | Role thấp gọi open_case/close_case | Med | High | `rbac.require()` per endpoint; FORBIDDEN test III.6 |

## VI.10. Penetration test

Trước release đầu tiên (Sprint Wave 3 GA): Burp/ZAP scan, sqlmap (an toàn) vào `find_scope` lot_range, CSRF test, role escalation. Report lưu `docs/security/`. ⬜ Chưa thực hiện (chưa có endpoint live).

## VI.11. Sign-off

| Role | Người | Ngày | Quyết định |
|---|---|---|---|
| Security Officer | *(chốt Wave 3)* | — | ⬜ Pass / Pass with conditions / Fail |
| QA Lead | *(chốt Wave 3)* | — | ⬜ |
| Module Owner (Tổ HC-QLCL & Risk) | *(chốt Wave 3)* | — | ⬜ |

---

# Phần VII — Code Quality

## VII.1. Tool matrix

| Tool | Mục tiêu | Target | Cadence |
|---|---|---|---|
| **SonarQube** (BE Python) | bug / smell / coverage | 0 critical bug, smell ≤ ngưỡng dự án, duplication ≤ 3%, coverage ≥ 70%, security hotspot review 100% | mỗi PR |
| **Lighthouse** (FE) | UX metric | Performance ≥ 90, Accessibility ≥ 95, Best Practices ≥ 90, SEO ≥ 80 | mỗi release lớn + monthly |
| **ESLint + vue-tsc** (FE) | type/lint | 0 error, 0 warning trên prod build | mỗi PR |
| **ruff / black** (BE) | lint + format | 0 error, format consistent | mỗi PR |
| **mypy** (BE) | type hint (CLAUDE.md §15) | 0 error `services/imm10.py` | mỗi PR |
| **Bundle size** (FE chunk imm10) | budget | main ≤ 250KB gzip, async ≤ 80KB gzip | mỗi PR FE |

## VII.2. Cadence

- SonarQube: mỗi PR (CI gate, fail nếu Quality Gate fail).
- Lighthouse: mỗi release lớn + monthly audit.
- ESLint / ruff / mypy: mỗi PR (CI gate).
- Bundle size: mỗi PR FE (CI report, fail nếu vượt budget).

Gắn screenshot SonarQube + Lighthouse vào file `09_Release.md` §Release Notes khi báo cáo final.

---

# Phụ lục A — Template per UAT scenario

```markdown
### UAT-IMM-10-<NN> — <Tên>

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
### TC-IMM-10-<LAYER>-<NN> — <Tên>

**Component (I.1)**: <…>
**Liên kết**: US-<NN> | BR-<NN> | ACT-<NN>
**Kỹ thuật (II.1/II.2)**: BVA boundary `disclosure_due_at = recall_confirmed_at + 48h`
**Priority (I.3)**: Critical / High / Medium / Low
**Test type**: Unit / Integration / API / E2E
**Pre-condition**: <fixture / state setup>

**Input**:
- <field>: <value>

**Steps**:
1. <…>
2. <…>

**Expected**:
- ServiceError(code=IMM10_<…>, message contains "<BR/VR>")
- doc.workflow_state unchanged

**Post-condition**: <DB rollback / fixture cleanup>
```

# Phụ lục C — Workflow State Transition Test template

```markdown
### TC-IMM-10-WF-<NN> — <action>: <from> → <to>

**Workflow JSON**: `fixtures/imm10_compliance_workflow.json`
**Role required**: <…>
**Pre-condition**: doc.workflow_state = <from>, gate đã pass
**Action**: apply_workflow(doc, "<action>")
**Expected (happy)**: doc.workflow_state = <to>, docstatus = <…>, audit entry created
**Expected (negative role)**: PermissionError / FORBIDDEN
**Expected (gate fail)**: ServiceError(code=IMM10_<…>, message contains "<BR-10-…>")
```

---

# DoD — File 07 hoàn chỉnh

## I. Test Analysis
- [x] I.1 Component Inventory liệt kê đủ artefact planned (so với 04/05/06)
- [x] I.2 mỗi US / BR / Activity có ≥ 1 dòng map
- [x] I.3 Risk priority gán cho mọi component (không trống)
- [x] I.4 Scope ghi rõ out-of-scope kèm lý do

## II. Test Design Techniques
- [x] II.1 chọn ≥ 4 black-box techniques (EP + BVA + Decision Table + State Transition)
- [x] II.2 white-box criteria xác định (statement + branch)
- [x] II.3 mapping component → kỹ thuật điền đầy đủ

## III. Test Plan
- [x] Test class structure planned cho mọi service public function (I.1)
- [x] ≥ 1 happy + 1 negative test mỗi function (kế hoạch)
- [ ] Workflow transitions cover 100% — chưa thực thi (JSON chưa scaffold; 8 transition dự kiến, đếm lại khi có file)
- [ ] Audit chain test (intact + tampered) — chưa viết (BE chưa scaffold)
- [ ] API test ≥ 60% coverage + permission matrix — chưa thực thi (endpoint chưa live)
- [x] Performance target xác định (III.8)
- [ ] CI command chạy clean — chưa chạy được (chưa có `test_imm10.py`)
- [ ] SonarQube Quality Gate pass + Lighthouse ≥ target — chưa có code/build

## IV. Traceability
- [x] IV.1 US → Test: mọi US có ≥ 1 Test ID (Status ⬜ Planned)
- [x] IV.2 BR → Test: mọi BR có happy + negative (kế hoạch)
- [ ] IV.3 Component → Test: Critical/High đạt coverage target — chưa đo được (BE chưa scaffold)

## V. UAT
- [x] Mỗi US có ≥ 1 UAT scenario
- [x] ≥ 1 negative + permission + audit verify scenario (UAT-IMM-10-05 + -03)
- [ ] Test data seed script chạy được — `uat_imm10.py` ⬜ Planned
- [ ] Tester accounts đã tạo ở UAT site — chưa tạo (site UAT Wave 3 chưa dựng)
- [x] Sign-off section sẵn sàng

## VI. Security
- [x] DocPerm matrix đầy đủ (Decision Table) — khung role × action × state hoàn chỉnh; permlevel field chốt khi scaffold
- [ ] Mọi field nhạy cảm có permlevel ≠ 0 — fieldname chưa lock (BE chưa scaffold)
- [ ] SQL injection + CSRF test pass — chưa thực thi (endpoint chưa live)
- [ ] Audit chain test pass (intact + tampered) — chưa viết
- [ ] Vendor isolation test pass (low-role API call) — chưa thực thi
- [x] Threat model đủ 6 STRIDE với mitigation
- [ ] Sign-off đầy đủ trước go-live — chờ Wave 3

## VII. Code Quality
- [x] Tool matrix + cadence xác định
- [ ] SonarQube Quality Gate pass — chưa có code
- [ ] Lighthouse ≥ target — chưa có FE build
- [ ] Bundle size ≤ budget — chưa có chunk imm10
- [ ] Screenshot báo cáo gắn vào file 09 — chờ Wave 3

---

*Cập nhật: 2026-05-29. Planning skeleton theo template 07 — test ID chính thức (`TC-IMM-10-…`), coverage % thực tế, naming series, ErrorCode, DocType fieldname chốt khi scaffold Sprint Wave 3 (sau khi IMM-16 GA). Coverage target tuân thủ CONVENTIONS §6.*
