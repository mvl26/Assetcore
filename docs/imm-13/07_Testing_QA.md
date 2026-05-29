# 07 — Kiểm thử & An ninh (Testing & QA & Security)

| Mục | Giá trị |
|---|---|
| Module | IMM-13 — Ngừng sử dụng và điều chuyển |
| Phạm vi | Per-module |
| Owner | QA Lead + Security Officer |
| Liên kết | 02 Analysis (US, BR, Activity, BPMN) · 03 Diagrams · 04 Backend · 05 API · 06 Frontend |

> **Mục đích**: Suy ra test case có hệ thống từ phân tích ([02](./02_Analysis_Design.md)) bằng kỹ thuật black-box + white-box. Bao gồm: phân tích đối tượng test → chọn kỹ thuật → viết test → traceability → UAT → security → code quality. Phần VI (Security) là gate go-live.

> **Trạng thái module**: BE **chưa scaffold** (không có `services/imm13.py`, `api/imm13.py`, `tests/test_imm13.py`). File này là **PLANNING SKELETON** — cấu trúc đầy đủ nhưng các ô phụ thuộc BE đánh dấu `⬜ Planned` hoặc *(Cần thiết kế khi scaffold BE — Sprint Wave 3)*. US/BR/UC/Activity/Endpoint/ErrorCode lấy từ [02](./02_Analysis_Design.md), [04](./04_Backend_Design.md), [05](./05_API_Specification.md) (đều là interface contract dự kiến). Coverage % chỉ ghi **target**, KHÔNG ghi số đo thực (chưa có code).

---

# Phần I — Test Analysis (Phân tích đối tượng test)

> Mục tiêu Phần I: trả lời 4 câu hỏi trước khi viết test case: (1) test cái gì (component inventory) (2) suy ra từ đâu (US/BR/Activity) (3) ưu tiên cái nào (risk) (4) loại trừ cái nào (out-of-scope).

## I.1. Component Inventory — Liệt kê phần mềm cần test

Liệt kê artefact test được của IMM-13. Nguồn: [04 §I DocType](./04_Backend_Design.md#i-doctype-skeleton), [04 §II Service](./04_Backend_Design.md#ii-service-layer-3-tier), [04 §III Workflow](./04_Backend_Design.md#iii-workflow), [04 §IV Hooks](./04_Backend_Design.md#iv-hooks), [05 §1 Endpoint catalog](./05_API_Specification.md#1--endpoint-catalog). Mọi tên dưới đây là **dự kiến** (BE chưa scaffold).

| # | Component | Loại | File / Tên (dự kiến) | Test layer áp dụng |
|---|---|---|---|---|
| 1 | `IMM Asset Reassignment` | DocType (master submittable) | `imm_asset_reassignment.json` | Integration (lifecycle) — ⬜ Planned |
| 2 | `IMM Replacement Review` | DocType (master submittable) | `imm_replacement_review.json` | Integration (lifecycle) — ⬜ Planned |
| 3 | `IMM Residual Risk` | DocType (master submittable) | `imm_residual_risk.json` | Integration (lifecycle) — ⬜ Planned |
| 4 | `IMM Residual Risk Item` | DocType (child) | `imm_residual_risk_item.json` | Integration (parent validate) — ⬜ Planned |
| 5 | `IMM-13 Settings` | DocType (single config) | `imm_13_settings.json` | Integration (config read) — ⬜ Planned |
| 6 | `IMM Asset Reassignment Workflow` | Workflow | `workflow/imm_13_reassignment.json` | Integration (state transition) — ⬜ Planned |
| 7 | `IMM Replacement Review Workflow` | Workflow | `workflow/imm_13_replacement_review.json` | Integration (state transition) — ⬜ Planned |
| 8 | `IMM Residual Risk Workflow` | Workflow | `workflow/imm_13_residual_risk.json` | Integration (state transition) — ⬜ Planned |
| 9 | `stand_down` | Service function | `services/imm13.py::stand_down` | Unit |
| 10 | `request_reassignment` | Service function | `services/imm13.py::request_reassignment` | Unit |
| 11 | `confirm_reassignment` | Service function | `services/imm13.py::confirm_reassignment` | Unit |
| 12 | `commit_reassignment` | Service function | `services/imm13.py::commit_reassignment` | Unit + Integration (atomic) |
| 13 | `create_replacement_review` | Service function | `services/imm13.py::create_replacement_review` | Unit |
| 14 | `submit_residual_risk` | Service function | `services/imm13.py::submit_residual_risk` | Unit (BVA: ≥ 3 item) |
| 15 | `approve_retire` | Service function | `services/imm13.py::approve_retire` | Unit + Integration (hand-off) |
| 16 | Gate `approve_retire` (Review + Risk required) | Validator / gate | `services/imm13.py` (BR-03) | Unit (Decision Table) |
| 17 | `asset_reassignment_repo` | Repository / DAO | `repositories/asset_reassignment_repo.py` | Integration (DB) — ⬜ Planned |
| 18 | `replacement_review_repo` | Repository / DAO | `repositories/replacement_review_repo.py` | Integration (DB) — ⬜ Planned |
| 19 | `residual_risk_repo` | Repository / DAO | `repositories/residual_risk_repo.py` | Integration (DB + hash chain) — ⬜ Planned |
| 20 | 14 API endpoint | API endpoint | `api/imm13.py` (xem [05 §1](./05_API_Specification.md#1--endpoint-catalog)) | API integration |
| 21 | Lifecycle event `stand_down` / `reassigned` / `retire_proposed` | Lifecycle event | `events/imm13.py` (audit chain) | Integration (audit chain) |
| 22 | `escalate_stale_oos` | Scheduler job (daily) | `services/imm13.py::escalate_stale_oos` | Unit + Cron simulation |
| 23 | `verify_location_consistency` | Scheduler job (daily) | `services/imm13.py::verify_location_consistency` | Unit + Cron simulation |
| 24 | `retry_handoff_imm14` | Scheduler job (hourly) | `services/imm13.py::retry_handoff_imm14` | Unit (retry / partial fail) |
| 25 | Listener `handle_repair_cannot_repair` | Hook (IMM-09 IN) | `events/imm13.py` | Integration (cross-module seed) |
| 26 | Listener `handle_calibration_failed` | Hook (IMM-11 IN) | `events/imm13.py` | Integration (cross-module seed) |
| 27 | FE list/detail reassignment + residual risk form | FE view / composable | `frontend/src/views/imm13/*.vue` | E2E (Playwright) — *(Cần thiết kế khi scaffold FE)* |
| 28 | Pinia store IMM-13 | Pinia store | `frontend/src/stores/imm13.ts` | Unit (vitest) — *(Cần thiết kế khi scaffold FE)* |

> Khi BE scaffold xong, chạy `grep -rn "^def\|^class" assetcore/services/imm13.py` và `grep -rn "@frappe.whitelist" assetcore/api/imm13.py` để đối chiếu inventory thực với bảng trên.

## I.2. Trace nguồn test — User Stories, Activity Flows, Business Rules

Dẫn từ artefact phân tích ([02](./02_Analysis_Design.md)) sang test layer. Mọi US/BR/Activity phải có ≥ 1 test ở Phần III và xuất hiện trong matrix Phần IV.

### I.2.a. Từ User Story → [02 §IV.1](./02_Analysis_Design.md#iv1-user-stories--acceptance-criteria)
| US ID | Tiêu đề ngắn | Acceptance Criteria # | Test layer dự kiến |
|---|---|---|---|
| IMM13-US-01 | Stand-down chủ động | AC1 (Pending Dept Confirm), AC2 (Asset → OOS + LE) | Unit + API + UAT |
| IMM13-US-02 | Stand-down tự động từ IMM-09 | AC (trigger event → form pre-filled) | Integration (cross-module) + Unit |
| IMM13-US-03 | Reassign nội viện | AC (cascade + atomic location + LE) | Unit + Integration + API + UAT |
| IMM13-US-04 | Xem bảng cost vs risk (replacement review) | AC (risk score = cost_repair/replacement_cost × risk_factor) | Unit + API |
| IMM13-US-05 | Ký residual risk theo WHO §3.2 | AC (≥ 3 item có mitigation + e-sign hash) | Unit (BVA/EP) + API + Security |
| IMM13-US-06 | Duyệt retire proposal một chỗ | AC (UI tổng hợp Review + Risk; e-sign) | Integration + API + UAT |
| IMM13-US-07 | Emit `retire_proposed` tin cậy | AC (retry 3×/6h, notify admin) | Unit (retry) + Integration |
| IMM13-US-08 | Notify Asset OOS > 30 ngày | AC (cron daily, notify list) | Unit (cron) + Integration |
| IMM13-US-09 | Xem chuỗi e-sign 1 retire proposal | AC (endpoint trả full hash chain + verify) | API + Security (audit chain) |

### I.2.b. Từ Business Rule → [02 §IV.2](./02_Analysis_Design.md#iv2-business-rules)
| BR ID | Phát biểu | Component liên quan (I.1) | Kỹ thuật test phù hợp |
|---|---|---|---|
| IMM13-BR-01 | Stand-down phải có 2-role e-sign (Trưởng khoa + PTP Khối 2) | `stand_down` (#9) + workflow (#6) | Decision Table (role × state) |
| IMM13-BR-02 | Reassign phải atomic update `Asset.location` + Lifecycle Event | `commit_reassignment` (#12) | Use Case + Error guessing (partial fail) |
| IMM13-BR-03 | Retire proposal block nếu thiếu Replacement Review hoặc Residual Risk | gate `approve_retire` (#16) | Decision Table / MC/DC |
| IMM13-BR-04 | Asset có clinical booking → block stand-down trừ khi override | `stand_down` (#9) | Decision Table (booking × override) |
| IMM13-BR-05 | Reassign khoa khác chuyên ngành (Class B/C/D) → auto-trigger IMM-04 lite | `request_reassignment` (#10) + listener IMM-04 (OUT) | EP (classification A/B/C/D) |
| IMM13-BR-06 | Lifecycle Event là channel duy nhất ghi state Asset (cấm direct ORM) | tất cả service mutate Asset | White-box (import/call inspection) + Error guessing |

### I.2.c. Từ Activity Flow / BPMN → [02 §II.10](./02_Analysis_Design.md#ii10-activity-diagram-per-uc-chính)
| Activity ID | Use Case | Branch chính | Branch ngoại lệ |
|---|---|---|---|
| ACT-UC-IMM13-01 | UC-IMM13-01 Stand-down | Lý do hợp lệ → Trưởng khoa xác nhận → PTP duyệt → Asset OOS | `ERR_REASON_REQUIRED`; Trưởng khoa từ chối → hủy; clinical booking → block/override |
| ACT-UC-IMM13-02 | UC-IMM13-02 Reassign | Cascade hợp lệ → competency OK → update location | `ERR_COMPETENCY_GAP`; cần re-commissioning → IMM-04 lite |
| ACT-UC-IMM13-04 | UC-IMM13-05 Đề xuất retire | Residual risk signed → PTP duyệt → emit `retire_proposed` | Chờ Tổ QLCL ký; PTP reject → trả về KTV |

## I.3. Risk-based Priority

Đánh giá rủi ro cho component ở I.1. Likelihood/Impact ước lượng từ [02 §I.7 Risk](./02_Analysis_Design.md#i7-risk--open-questions) và §II.7 RACI (separation of duties).

| Component (I.1) | Likelihood (1-5) | Impact (1-5) | Risk = L×I | Priority |
|---|---|---|---|---|
| Gate `approve_retire` — thiếu Review/Risk (#16, BR-03) | 3 | 5 | 15 | **Critical** |
| `commit_reassignment` atomic location + LE (#12, BR-02) | 3 | 5 | 15 | **Critical** |
| `stand_down` 2-role e-sign + clinical booking (#9, BR-01/04) | 3 | 5 | 15 | **Critical** |
| `submit_residual_risk` ≥ 3 item + e-sign (#14, BR đối WHO §3.2) | 3 | 4 | 12 | High |
| Lifecycle/audit chain integrity (#19, #21, BR-06) | 2 | 5 | 10 | High |
| Hand-off IMM-14 + `retry_handoff_imm14` (#15, #24) | 3 | 3 | 9 | Medium |
| Listener IMM-09/IMM-11 auto-seed (#25, #26) | 3 | 3 | 9 | Medium |
| `escalate_stale_oos` cron (#22) | 2 | 2 | 4 | Low |
| `verify_location_consistency` cron (#23) | 2 | 3 | 6 | Medium |
| Dashboard metrics endpoint (#20 — `dashboard_metrics`) | 2 | 2 | 4 | Low |

**Quy ước priority**: Critical (R ≥ 15) test trước, fail = block release · High (10 ≤ R < 15) bắt buộc trước go-live · Medium (5 ≤ R < 10) trong sprint khi có thời gian · Low (R < 5) chỉ test khi báo cáo bug.

## I.4. Scope

**In-scope:**
- Service layer 9 function ([04 §II.1](./04_Backend_Design.md#ii1-service-functions-signature-dự-kiến)) — unit + integration.
- 3 workflow state machine ([04 §III](./04_Backend_Design.md#iii-workflow)) — state transition test 100% transition.
- 14 API endpoint ([05 §1](./05_API_Specification.md#1--endpoint-catalog)) — happy + permission + envelope.
- Audit hash chain SHA-256 + e-sign (intact + tampered).
- Cross-module trigger IN (IMM-09 `cannot_repair`, IMM-11 `cal_failed`) và OUT (IMM-14 `retire_proposed`, IMM-04 re-commissioning lite).

**Out-of-scope:**
- Performance load test chi tiết → giao Phần III.8 (target-only, chưa có endpoint thực).
- Cross-module IMM-14 closure/đối soát kế toán → chỉ smoke event hand-off; logic closure test ở IMM-14.
- Mua sắm thay thế (IMM-01/02/03) → out.
- Sanitize patient data vật lý (WHO §3.6) → IMM-14.
- FE E2E chi tiết → chờ scaffold FE (Sprint Wave 3 — Sprint 4).

**Assumptions:**
- `AC Asset Lifecycle` (8 states) đã có từ Wave 1; IMM-13 chỉ invoke transition `Đưa ra khỏi sử dụng`, không tạo state mới.
- Master data (`Location` cây Khoa→Phòng→Vị trí, `AC Asset`, role fixtures) đã seed ở test site.
- Test users cho 6 role ([04 §I Permissions](./04_Backend_Design.md#i-doctype-skeleton)) đã tạo.
- Browser: Chrome/Edge ≥ 120, Firefox ≥ 122 (theo [02 §V.5](./02_Analysis_Design.md#phần-v--yêu-cầu-phi-chức-năng-nfr)).

---

# Phần II — Test Design Techniques (Kỹ thuật thiết kế test case)

> Mỗi test phải truy được về 1 kỹ thuật ở dưới.

## II.1. Black-box techniques

| Kỹ thuật | Khi nào dùng | Áp dụng vào IMM-13 | Số test sinh ra (rule of thumb) |
|---|---|---|---|
| **Equivalence Partitioning (EP)** | Input có miền giá trị chia nhóm tương đương | `asset.classification` (A/B/C/D → BR-05), `confirm_reassignment.role` ∈ {source, target}, workflow_state enum | 1 test/partition |
| **Boundary Value Analysis (BVA)** | Numeric / count / date có biên | `submit_residual_risk` số item (2 / 3 / 4 — biên BR ≥ 3), OOS days biên 30 (cron escalate), timeout dept confirm biên 14 ngày | 2-3 test/biên: min-1, min, min+1 |
| **Decision Table** | Multi-condition gate, BR kết hợp | Gate `approve_retire` (Review × Risk — BR-03), `stand_down` (clinical_booking × override — BR-04), permission matrix (role × action × state) | 2^N rút gọn theo equivalence |
| **State Transition Testing** | Workflow finite state machine | 3 workflow ([04 §III](./04_Backend_Design.md#iii-workflow)): Reassignment, Replacement Review, Residual Risk | Mỗi transition + invalid transition |
| **Use Case Testing** | End-to-end actor flow | UAT scenarios (Phần V), API integration test, atomic `commit_reassignment` | 1/main flow + 1/alt flow + 1/exception |
| **Pairwise / Combinatorial** | Nhiều field optional kết hợp | Form reassign (target_facility × department × room × location cascade 4 cấp) | Min set cover all pairs |
| **Error Guessing** | null, empty, unicode, race, partial fail | Concurrent reassign (`IMM13_CONCURRENT_UPDATE`), evidence file rỗng, hand-off IMM-14 partial fail | Bổ sung — không thay thế |

## II.2. White-box techniques

| Kỹ thuật | Áp dụng vào | Tiêu chí đạt | Công cụ |
|---|---|---|---|
| **Statement coverage** | 9 service function ([04 §II.1](./04_Backend_Design.md#ii1-service-functions-signature-dự-kiến)) | ≥ 85% line (target, đo sau scaffold) | `coverage report` |
| **Branch / Decision coverage** | Function có if/else/try (commit atomic, hand-off retry, gate) | ≥ 80% branch (target) | `coverage --branch` |
| **Condition / MC/DC** | Gate `approve_retire` (Review AND Risk — BR-03), `stand_down` (booking × override — BR-04) | Mỗi sub-condition kiểm soát outcome độc lập | Manual test design + coverage |
| **Path coverage** | `commit_reassignment` (atomic path + rollback path) | Toàn bộ path khả dĩ (happy / partial fail / lock) | Manual |

> Ưu tiên Branch coverage cho service layer; MC/DC chỉ áp vào gate logic BR-03/BR-04.

## II.3. Mapping Component → Kỹ thuật

| Loại component | Kỹ thuật chính | Kỹ thuật phụ |
|---|---|---|
| Service function (stand_down, reassign…) | EP + Branch coverage | BVA |
| Gate `approve_retire` (BR-03) | Decision Table | MC/DC |
| `submit_residual_risk` (count ≥ 3) | BVA | EP + Error guessing |
| Workflow transition (3 WF) | State Transition | Use Case |
| `commit_reassignment` (atomic) | Use Case + Path coverage | Error guessing (partial fail) |
| API endpoint (14) | Use Case + EP (permission) | Pairwise (cascade form) |
| Scheduler (escalate / verify / retry) | Use Case (state setup → run → assert) | Error guessing (lock, retry exhausted) |
| Cross-module listener (IMM-09/11) | Use Case (event → seed) | Error guessing (idempotent re-emit) |
| FE view (Playwright) | Use Case end-to-end | Error guessing (network 4xx/5xx, role gate) |

---

# Phần III — Test Plan (Kế hoạch thực thi)

## III.1. Test Pyramid

Theo [02 §I.5/§V.6](./02_Analysis_Design.md#i5-kpi-mục-tiêu): unit chiếm phần lớn, E2E ít. Tỷ lệ dự kiến:

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

Trace: CLAUDE.md §17 (TDD mandatory) — test viết trước implement khi scaffold Sprint Wave 3.

## III.2. Unit test — Service Layer

File dự kiến `tests/test_imm13.py` (**chưa tồn tại**). Bảng dưới là kế hoạch test class theo 9 service function ([04 §II.1](./04_Backend_Design.md#ii1-service-functions-signature-dự-kiến)) + 6 BR ([02 §IV.2](./02_Analysis_Design.md#iv2-business-rules)). Số case là **dự kiến**, ID chính thức chốt khi scaffold.

| Test class (dự kiến) | Function cover | Kỹ thuật | Cases (happy/negative) | BR/US trace |
|---|---|---|---|---|
| `TestStandDown` | `stand_down` (#9) | Decision Table + EP | 1 / 4 (reason rỗng, Under PM, Under Repair, clinical booking) | BR-01, BR-04, US-01 |
| `TestStandDownAutoSeed` | listener `handle_repair_cannot_repair` (#25) | Use Case | 1 / 1 | US-02 |
| `TestRequestReassignment` | `request_reassignment` (#10) | EP + Pairwise | 1 / 3 (invalid location, competency gap, concurrent) | BR-05, US-03 |
| `TestConfirmReassignment` | `confirm_reassignment` (#11) | EP (role source/target) | 2 / 1 | US-03 |
| `TestCommitReassignment` | `commit_reassignment` (#12) | Path + Use Case | 1 / 2 (partial fail rollback, direct-ORM forbidden) | BR-02, BR-06 |
| `TestCreateReplacementReview` | `create_replacement_review` (#13) | Use Case | 1 / 1 | US-04 |
| `TestSubmitResidualRisk` | `submit_residual_risk` (#14) | BVA (2/3/4 item) + EP | 1 / 2 (< 3 item, mitigation rỗng) | US-05 |
| `TestApproveRetire` | `approve_retire` (#15) + gate (#16) | Decision Table / MC/DC | 1 / 3 (thiếu Review, thiếu Risk, hand-off fail) | BR-03, US-06, US-07 |
| `TestEscalateStaleOOS` | `escalate_stale_oos` (#22) | BVA (biên 30 ngày) + Use Case | 1 / 1 | US-08 |
| `TestVerifyLocationConsistency` | `verify_location_consistency` (#23) | Use Case | 1 / 1 | – |
| `TestRetryHandoffIMM14` | `retry_handoff_imm14` (#24) | Error guessing (retry exhausted) | 1 / 1 | US-07 |

> **Tổng test class dự kiến: 11**, tất cả `⬜ Planned` (chưa viết — BE chưa scaffold). Dùng `SimpleNamespace` cho test thuần công thức (risk score US-04), chạy ms-level không cần fixture.

## III.3. Integration — DocType lifecycle

File dự kiến `tests/test_imm13_doctype.py`. Cover hook `validate / on_submit / on_cancel` của 3 DocType master ([04 §II.3](./04_Backend_Design.md#ii3-controller-hooks-doctype-class)). **Field detail chưa chốt** → bảng skeleton.

| Test | Setup | Action | Assert | Kỹ thuật |
|---|---|---|---|---|
| Reassignment validate | seed `AC Asset` Active + `Location` tree | `doc.insert()` | `from_location` auto-fill từ Asset.location | EP — ⬜ Planned |
| Replacement Review submit | seed Asset OOS | `doc.submit()` | child `IMM Cost Item` required | EP — ⬜ Planned |
| Residual Risk parent validate | seed Review submitted | `doc.insert()` với 2 item | raise `IMM13_RISK_ITEMS_INSUFFICIENT` | BVA — ⬜ Planned |

> Fixture trong `setUpClass` phải có `tearDownClass` purge (assetcore-test LL-TEST-17). *(Field-level assert chốt khi scaffold BE.)*

## III.4. Integration — Workflow transitions

File dự kiến `tests/test_imm13_workflow.py`. **Bắt buộc** cover mọi transition của 3 workflow JSON. Workflow JSON **chưa tồn tại** → đếm từ design ([04 §III](./04_Backend_Design.md#iii-workflow)); đếm lại thực tế khi scaffold bằng `python3 -c "import json; print(len(json.load(open('<wf>.json'))['transitions']))"`.

**WF-1 `IMM Asset Reassignment Workflow`** ([04 §III.1](./04_Backend_Design.md#iii1-imm-asset-reassignment-workflow)):

| Transition | From → To | Role required | Test pass | Test fail (wrong role / gate fail) |
|---|---|---|---|---|
| Gửi xác nhận | Draft → Pending Dept Confirm Source | IMM HTM Engineer | ⬜ | ⬜ |
| Trưởng khoa nguồn xác nhận | Pending Dept Confirm Source → Pending Dept Confirm Target | IMM Department Head | ⬜ | ⬜ |
| Trưởng khoa đích chấp nhận | Pending Dept Confirm Target → Pending Approval | IMM Department Head | ⬜ | ⬜ |
| Duyệt (side effect: `commit_reassignment`) | Pending Approval → Approved | IMM Operations Manager | ⬜ | ⬜ |
| Từ chối | Pending Approval → Rejected | IMM Operations Manager / Department Head | ⬜ | ⬜ |
| Hủy | (any) → Cancelled | IMM HTM Engineer / system | ⬜ | ⬜ |

**WF-2 `IMM Replacement Review Workflow`** ([04 §III.2](./04_Backend_Design.md#iii2-imm-replacement-review-workflow)):

| Transition | From → To | Role required | Test pass | Test fail |
|---|---|---|---|---|
| Gửi TCKT | Draft → Pending Finance | IMM HTM Engineer | ⬜ | ⬜ |
| TCKT điền cost | Pending Finance → Pending Risk Assessment | IMM Finance Officer | ⬜ | ⬜ |
| QLCL ký risk | Pending Risk Assessment → Pending Approval | IMM QA Officer | ⬜ | ⬜ |
| Duyệt (side effect: emit `retire_proposed`) | Pending Approval → Approved | IMM Operations Manager | ⬜ | ⬜ |
| Từ chối | Pending Approval → Rejected | IMM Operations Manager | ⬜ | ⬜ |

**WF-3 `IMM Residual Risk Workflow`** ([04 §III.3](./04_Backend_Design.md#iii3-imm-residual-risk-workflow)):

| Transition | From → To | Role required | Test pass | Test fail |
|---|---|---|---|---|
| Ký (side effect: `signature_hash` + `log_audit_event`) | Draft → Signed | IMM QA Officer | ⬜ | ⬜ |

> **Tổng transition document: 12** (WF-1: 6, WF-2: 5, WF-3: 1) — tất cả `⬜ Planned`. Kỹ thuật: State Transition Testing — mỗi edge = 1 test pass + 1 test fail.

## III.5. Integration — Audit chain integrity

File dự kiến `tests/test_imm13_audit.py`. 2 test chính (theo [02 §V.2](./02_Analysis_Design.md#phần-v--yêu-cầu-phi-chức-năng-nfr) + [05 §4](./05_API_Specification.md#4--authentication--authorization)):
- (a) Sau chuỗi e-sign 3 cấp (Trưởng khoa nguồn → đích → PTP), chain hash SHA-256 hợp lệ end-to-end qua endpoint `get_audit_chain`.
- (b) Khi 1 entry bị tamper (sửa 1 byte), `residual_risk_repo.verify_signature_chain` (#19) trả `False` / endpoint trả `chain_broken=true`.

Trace: dùng `log_audit_event` ([04 §III.3](./04_Backend_Design.md#iii3-imm-residual-risk-workflow)), Lifecycle Event (#21). ⬜ Planned (BE chưa scaffold).

## III.6. API test

File dự kiến `tests/test_imm13_api.py`. Cover 14 endpoint ([05 §1](./05_API_Specification.md#1--endpoint-catalog)). Mỗi mutating endpoint cần: happy (envelope `success=true`) + invalid params + no-permission (`success=false`, code `IMM13_*`/`FORBIDDEN`) + pagination (list) + idempotent retry.

| Test | Endpoint | Verify | Kỹ thuật |
|---|---|---|---|
| Create stand-down happy | `api/imm13.create_stand_down_request` | `success=true`, state `Pending Dept Confirm Source` | Use Case |
| Create stand-down no reason | `api/imm13.create_stand_down_request` | `code=IMM13_REASON_REQUIRED` | EP |
| Create reassignment cascade | `api/imm13.create_reassignment` | `needs_recommissioning` bool đúng theo class | Pairwise + EP |
| Confirm by wrong role | `api/imm13.confirm_reassignment` (low-role) | `code=FORBIDDEN` | EP (permission partition) |
| Approve reassignment commit | `api/imm13.approve_reassignment` | `asset_location_updated=true`, có `lifecycle_event` | Use Case |
| Submit residual risk < 3 item | `api/imm13.submit_residual_risk` | `code=IMM13_RISK_ITEMS_INSUFFICIENT` | BVA |
| Approve retire missing review | `api/imm13.approve_retire_proposal` | gate block (BR-03) | Decision Table |
| Get audit chain (auditor) | `api/imm13.get_audit_chain` | full hash chain + verify flag | Use Case |
| List reassignments pagination | `api/imm13.list_reassignments` | boundary `limit`/`start` | BVA |

> Tất cả `⬜ Planned`. Permission partition trace [05 §1 Auth column](./05_API_Specification.md#1--endpoint-catalog) + [04 §I Permissions](./04_Backend_Design.md#i-doctype-skeleton).

## III.7. E2E browser (Playwright)

Dùng khi flow UI khó cover bằng API: cascade Khoa→Phòng→Vị trí (4 cấp reset/reload), modal confirm e-sign, workflow button visibility theo role, form residual risk ≥ 3 item. Trace: `assetcore-test` skill Phần 2 (Playwright MCP recipes + R-1..R-9 data rules). *(Chờ scaffold FE — Sprint Wave 3 Sprint 4.)*

## III.8. Performance test

Target từ [02 §V.1](./02_Analysis_Design.md#phần-v--yêu-cầu-phi-chức-năng-nfr) (target-only, chưa có endpoint thực để đo):

| Metric | Target | Method |
|---|---|---|
| `create_stand_down_request` / `create_reassignment` p95 | < 800ms | k6 POST batch |
| List 1k reassignment | < 1.2s | DB seed 1k, k6 GET `list_reassignments` |
| Cron `escalate_stale_oos` daily | < 60s | `time bench execute …` |
| Query Asset OOS > 30 ngày | < 200ms | `time` query |
| Form stand-down load 5k asset | < 1s ([02 UC-01 special req](./02_Analysis_Design.md#uc-01-stand-down-asset)) | Lighthouse / manual |

## III.9. Test data & Fixtures

Migrate từ kế hoạch fixtures hiện có (thư mục dự kiến `tests/fixtures/imm13/`):

| Loại | Cách seed | File (dự kiến) |
|---|---|---|
| Master data (Location tree, Asset Category, role) | `fixtures/*.json` (cài qua `bench migrate`) | `assetcore/fixtures/` |
| Asset Active Class A | `test_records.json` | `tests/fixtures/imm13/asset_active_class_a.json` |
| Asset Active Class C (NĐ98 case) | `test_records.json` | `tests/fixtures/imm13/asset_active_class_c.json` |
| Asset Under Repair (negative EC-02) | `test_records.json` | `tests/fixtures/imm13/asset_under_repair.json` |
| Location tree (Cơ sở→Khoa→Phòng→Vị trí) | `test_records.json` | `tests/fixtures/imm13/location_tree.json` |
| Repair `cannot_repair` (trigger US-02) | `test_records.json` | `tests/fixtures/imm13/repair_cannot_repair.json` |
| Calibration `cal_failed` (trigger) | `test_records.json` | `tests/fixtures/imm13/calibration_failed.json` |
| UAT seed | Python script | `assetcore/scripts/uat/uat_imm13.py` — *(Cần thiết kế khi scaffold)* |

> UAT data phải thực tế (tên bệnh viện VN, mã NCC chuẩn). Backend test fixture mới dùng prefix `_Test` (assetcore-test R-0/R-1).

## III.10. Run commands & Coverage gate

```bash
# Module test (sau khi scaffold)
bench --site <site> run-tests --app assetcore --module assetcore.tests.test_imm13
# Coverage
coverage run -m unittest assetcore.tests.test_imm13 && coverage report
# Workflow smoke
bench --site <site> run-tests --module assetcore.tests.test_workflows
```

Coverage là **target** (chưa có số đo — BE chưa scaffold). Theo `CONVENTIONS §6` + [02 §V.6](./02_Analysis_Design.md#phần-v--yêu-cầu-phi-chức-năng-nfr):

| Layer | Target coverage | Đo |
|---|---|---|
| Service (`services/imm13.py`) | ≥ 85% line + ≥ 80% branch | `coverage --branch` |
| DocType lifecycle | ≥ 70% | `coverage report` |
| API (`api/imm13.py`) | ≥ 60% | `coverage report` |
| Repository (`repositories/*_repo.py`) | ≥ 80% | `coverage report` |
| Frontend (vue-tsc) | 0 error | `npm run build` |

---

# Phần IV — Traceability Matrices

> Mọi test ở Phần III phải xuất hiện ở cả 3 bảng. Status `⬜ Planned` cho mọi test (chưa viết).

## IV.1. US → Test mapping

| US ID | AC | Test ID (III.x) | Layer | Status |
|---|---|---|---|---|
| IMM13-US-01 | AC1, AC2 | `TestStandDown` (III.2) + API create stand-down (III.6) | Unit + API | ⬜ Planned |
| IMM13-US-02 | trigger event | `TestStandDownAutoSeed` (III.2) | Integration | ⬜ Planned |
| IMM13-US-03 | cascade + atomic | `TestRequestReassignment` + `TestCommitReassignment` (III.2) | Unit + Integration | ⬜ Planned |
| IMM13-US-04 | risk score formula | `TestCreateReplacementReview` (III.2) | Unit | ⬜ Planned |
| IMM13-US-05 | ≥ 3 item + e-sign | `TestSubmitResidualRisk` (III.2) | Unit + Security | ⬜ Planned |
| IMM13-US-06 | UI tổng hợp + e-sign | `TestApproveRetire` (III.2) + UAT-IMM13-03 | Integration + UAT | ⬜ Planned |
| IMM13-US-07 | retry 3×/6h | `TestRetryHandoffIMM14` (III.2) | Unit | ⬜ Planned |
| IMM13-US-08 | cron daily notify | `TestEscalateStaleOOS` (III.2) | Unit | ⬜ Planned |
| IMM13-US-09 | full hash chain | API `get_audit_chain` (III.6) + III.5 audit | API + Security | ⬜ Planned |

## IV.2. BR → Test mapping

| BR ID | Phát biểu (rút gọn) | Test ID | Kỹ thuật | Happy / Negative |
|---|---|---|---|---|
| IMM13-BR-01 | Stand-down 2-role e-sign | `TestStandDown` | Decision Table | 1 / ≥ 2 |
| IMM13-BR-02 | Reassign atomic location + LE | `TestCommitReassignment` | Use Case + Path | 1 / 1 (partial fail) |
| IMM13-BR-03 | Retire block nếu thiếu Review/Risk | `TestApproveRetire` (gate #16) | Decision Table / MC/DC | 1 / 2 |
| IMM13-BR-04 | Clinical booking → block trừ override | `TestStandDown` | Decision Table | 1 / 1 |
| IMM13-BR-05 | Reassign Class B/C/D → IMM-04 lite | `TestRequestReassignment` | EP (classification) | 1 / 1 |
| IMM13-BR-06 | Lifecycle Event = channel duy nhất | `TestCommitReassignment` (direct-ORM forbidden) | White-box | 1 / 1 |

> Mọi BR có ≥ 1 happy + ≥ 1 negative test. BR Critical (BR-01/02/03 ở I.3) phải có Decision Table / Path đầy đủ. Tất cả `⬜ Planned`.

## IV.3. Component → Test mapping

| Component (I.1) | Test ID | Test layer | Coverage % | Risk priority (I.3) |
|---|---|---|---|---|
| `services/imm13::stand_down` (#9) | `TestStandDown` | Unit | target ≥ 85% (chưa đo) | Critical |
| `services/imm13::commit_reassignment` (#12) | `TestCommitReassignment` | Unit + Integration | target ≥ 85% | Critical |
| gate `approve_retire` (#16) | `TestApproveRetire` | Unit (MC/DC) | target ≥ 85% | Critical |
| `services/imm13::submit_residual_risk` (#14) | `TestSubmitResidualRisk` | Unit | target ≥ 85% | High |
| `residual_risk_repo` hash chain (#19) | III.5 audit test | Integration | target ≥ 80% | High |
| 14 API endpoint (#20) | `tests/test_imm13_api.py` | API | target ≥ 60% | High/Medium |
| cron `escalate_stale_oos` (#22) | `TestEscalateStaleOOS` | Unit | target ≥ 85% | Low |
| dashboard metrics (#20) | API smoke | API | best-effort | Low |

> Mọi component Critical/High phải đạt coverage target III.10. Coverage % là **target** — số đo thực điền sau khi scaffold + chạy `coverage`.

---

# Phần V — UAT Script

## V.1. Phạm vi UAT

- **In-scope**: 3 scenario chính theo US-01 (stand-down), US-03 (reassign), US-06 (retire proposal hand-off) — xem V.4.
- **Out-of-scope**: performance (III.8), security pen-test (Phần VI.10).
- **Pre-condition**: site UAT deploy version AssetCore v3.x (Đợt 3, [05 §5](./05_API_Specification.md#5--versioning--backward-compat)), fixtures loaded (III.9), tester accounts active. *(Site UAT chưa dựng — BE chưa scaffold.)*

## V.2. Tester accounts

6 role theo [04 §I Permissions](./04_Backend_Design.md#i-doctype-skeleton). Phải có account role thấp để cover FORBIDDEN (không chỉ Admin).

| Username (dự kiến) | Role | Vai trò UAT |
|---|---|---|
| `ktv.uat@…` | IMM HTM Engineer | Khởi tạo stand-down / reassign / replacement review |
| `truongkhoa.a.uat@…` | IMM Department Head | Xác nhận khoa nguồn |
| `truongkhoa.b.uat@…` | IMM Department Head | Chấp nhận khoa đích |
| `ptp.uat@…` | IMM Operations Manager | Duyệt cuối + retire |
| `qlcl.uat@…` | IMM QA Officer | Ký residual risk |
| `tckt.uat@…` | IMM Finance Officer | Điền cost replacement review |
| `auditor.uat@…` | IMM Auditor | Đọc audit chain |

## V.3. Test data đã seed

| DocType | Số lượng | Ghi chú |
|---|---|---|
| `AC Asset` Active Class A | ≥ 2 | happy stand-down + reassign |
| `AC Asset` Active Class C | ≥ 1 | NĐ98 case → trigger IMM-04 lite (BR-05) |
| `AC Asset` Under Repair | ≥ 1 | negative EC-02 (`IMM13_ASSET_BUSY_REPAIR`) |
| `Location` tree | ≥ 2 khoa, mỗi khoa ≥ 1 phòng + vị trí | cascade reassign |
| `Asset Repair` outcome=cannot_repair | ≥ 1 | trigger auto-seed US-02 |

Reset script đi kèm: `scripts/uat/uat_imm13.py` — *(Cần thiết kế khi scaffold)*.

## V.4. UAT Scenarios — Suy ra từ US + Activity

ID `UAT-IMM13-NN`. Suy theo Use Case Testing: mỗi US chính → ≥ 1 happy; mỗi Activity branch ngoại lệ → ≥ 1; mỗi role mutate → ≥ 1 permission verify; mỗi terminal transition → ≥ 1 audit verify.

| ID | Actor | Pre-condition | US/BR cover | Kỹ thuật | Kết quả mong đợi |
|---|---|---|---|---|---|
| UAT-IMM13-01 | KTV → Trưởng khoa → PTP | Asset Active có lịch sử PM | US-01, BR-01 | Use Case happy + State Transition | Asset → Out of Service, Lifecycle Event `stand_down`, audit chain đủ 3 chữ ký |
| UAT-IMM13-02 | KTV → Trưởng khoa A/B → PTP | Asset Active + Location tree (khoa A→B) | US-03, BR-02, BR-05 | Use Case happy + Pairwise cascade | `AC Asset.location` đổi sang phòng đích; Class C → IMM-04 lite tự sinh |
| UAT-IMM13-03 | KTV → TCKT → QLCL → PTP | Asset OOS > 7 ngày | US-04, US-05, US-06, BR-03 | Use Case happy + State Transition | IMM-14 listener nhận event `retire_proposed`; hồ sơ truy được từ IMM-14 |
| UAT-IMM13-04 | KTV role thấp gọi approve | Reassignment Pending Approval | BR-01 (separation of duties) | EP permission negative | HTTP 403 / `PermissionError` (KTV không được approve) |
| UAT-IMM13-05 | KTV | Asset có clinical booking | BR-04, EC-06 | Decision Table negative | block `IMM13_ASSET_HAS_CLINICAL_BOOKING`; chỉ qua nếu Trưởng khoa override + e-sign |
| UAT-IMM13-06 | Auditor | 1 retire proposal approved | US-09 | Audit chain verify | endpoint `get_audit_chain` trả full hash chain + verify=true; tamper 1 byte → broken |

## V.5. Tổng hợp kết quả & Bug found

| Scenario | Status (Pass/Fail/Block) | Tester | Ngày | Ghi chú |
|---|---|---|---|---|
| UAT-IMM13-01 | ⬜ Chưa chạy (BE chưa scaffold) | – | – | – |
| UAT-IMM13-02 | ⬜ Chưa chạy | – | – | – |
| UAT-IMM13-03 | ⬜ Chưa chạy | – | – | – |
| UAT-IMM13-04 | ⬜ Chưa chạy | – | – | – |
| UAT-IMM13-05 | ⬜ Chưa chạy | – | – | – |
| UAT-IMM13-06 | ⬜ Chưa chạy | – | – | – |

**Bug list**: *(điền khi chạy UAT)* — `Issue ID · Severity (Blocker/Major/Minor/Trivial) · Mô tả · Fix status`.

**Acceptance criteria**: ≥ 95% PASS, Blocker = 0, Major ≤ 2 (có workaround).

**Sign-off**: BA Lead (Tổ HC-QLCL & Risk) + QA Lead + Module Owner (PTP Khối 2) + End-user (Trưởng khoa đại diện). ⬜ Chờ UAT.

---

# Phần VI — Security Review (gate)

## VI.1. RBAC

**Role definitions** (`fixtures/role.json` + `role_profile.json`): 6 role IMM-13 ([04 §I Permissions](./04_Backend_Design.md#i-doctype-skeleton)) — `IMM HTM Engineer`, `IMM Department Head`, `IMM Operations Manager`, `IMM QA Officer`, `IMM Finance Officer`, `IMM Auditor`. *(Fixture chưa sinh — Sprint Wave 3.)*

**DocPerm matrix** (Decision Table — migrate từ permission matrix file cũ; mỗi cell ❌ phải có negative test HTTP 403 / `PermissionError`):

| Action | KTV (Engineer) | Dept Head | PTP (Ops Mgr) | QA Officer | Finance | Auditor |
|---|---|---|---|---|---|---|
| Tạo Reassignment / Stand-down | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Confirm (source/target) | ❌ | ✅ (chỉ khoa của họ — User Permission) | ❌ | ❌ | ❌ | ❌ |
| Approve reassignment / retire | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| Fill cost replacement review | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ |
| Submit residual risk (e-sign) | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| Read audit chain | ❌ | ❌ | ✅ (own facility) | ✅ | ❌ | ✅ (all) |
| Override clinical booking | ❌ | ✅ + e-sign | ❌ | ❌ | ❌ | ❌ |

**Field-level permission**: field nhạy cảm (`residual_value`, `replacement_cost`, `signature_hash`, cost internal) đặt `permlevel ≠ 0` — chỉ Finance/QA/Ops đọc-ghi. *(permlevel cụ thể chốt khi scaffold DocType.)*

**User Permission**: filter row theo facility/department — Dept Head chỉ thấy reassignment thuộc khoa họ (qua `permission_query_conditions`).

**Kỹ thuật**: Decision Table — mỗi (role × action × state) = 1 row, expected Allow/Deny.

## VI.2. API security

- **Whitelist hygiene**: mọi `@frappe.whitelist` ([05 §1](./05_API_Specification.md#1--endpoint-catalog), 14 endpoint) phải có docstring + role check trong service + validate input. *(Audit khi scaffold api/imm13.py.)*
- **CSRF**: Frappe default `X-Frappe-CSRF-Token` ([05 §4](./05_API_Specification.md#4--authentication--authorization)); mutation thiếu token → reject.
- **Input validation**: Link field (`asset`, `target_location`) validate qua `frappe.get_value` trước khi dùng → trả `IMM13_INVALID_TARGET_LOCATION` nếu sai.
- **SQL injection**: parameterized only; không f-string vào raw SQL (CONVENTIONS).
- **Rate limit**: cho endpoint mutating (create, approve, e-sign endpoint 4/8/9).

## VI.3. Audit trail integrity

Mọi mutation sinh Lifecycle Event + gọi `log_audit_event` ([04 §III.3](./04_Backend_Design.md#iii3-imm-residual-risk-workflow)), hash SHA-256 chain. Verify endpoint `get_audit_chain` ([05 endpoint 13](./05_API_Specification.md#1--endpoint-catalog)). Test tamper. User KHÔNG có quyền edit/delete audit entry (DocPerm + `on_trash` guard, ISO 13485:7.5.9 + NĐ98 lưu ≥ 5 năm). Trace: III.5 test cases.

## VI.4. Authentication & session

Login Frappe default + session cookie. E-sign endpoint (4, 8, 9) bắt buộc re-auth password trong cùng request → sai trả `IMM13_ESIGN_INVALID` ([05 §4](./05_API_Specification.md#4--authentication--authorization)). Session timeout / lockout / password policy theo cấu hình site chung. 2FA: roadmap.

## VI.5. Data sensitivity

KHẲNG ĐỊNH: IMM-13 KHÔNG lưu patient data trong DocType ([02 §V.2](./02_Analysis_Design.md#phần-v--yêu-cầu-phi-chức-năng-nfr)); nếu Asset chứa thì gọi sanitize service IMM-14 trước reassign (WHO §3.6).

| Loại | Trường (dự kiến) | Sensitivity | Bảo vệ |
|---|---|---|---|
| Chi phí nội bộ | `residual_value`, `replacement_cost` | Confidential | permlevel ≠ 0, chỉ Finance/Ops |
| Chữ ký số | `signature_hash`, `signed_by/at` | Restricted | read-only, hash chain, no delete |
| Lý do stand-down + bằng chứng | `reason`, `evidence_files` | Internal | role-gated, audit |
| Risk assessment | `IMM Residual Risk Item` | Internal | QA/Ops read |

## VI.6. Vendor isolation

IMM-13 không có actor Vendor External trong [02 §I.3](./02_Analysis_Design.md#i3-stakeholders--actors) (toàn bộ actor nội viện). Tuy nhiên áp dụng nguyên tắc chung: account ngoài (nếu có) KHÔNG thấy chi phí, internal note, audit trail, dashboard, và KHÔNG export. Dept Head bị giới hạn theo facility (VI.1 User Permission). Trace: test permission negative III.6 + UAT-IMM13-04.

## VI.7. Secrets management

Cấm commit `.env` / credential. `site_config.json` không lên git. External token (nếu tích hợp HIS scheduling cho clinical booking check — EC-06) lưu `frappe.conf`. Backup encrypt at-rest off-site.

## VI.8. Logging & monitoring

| Sự kiện | Log level | Where | Alert? |
|---|---|---|---|
| Stand-down approved | INFO | Lifecycle Event + audit | – |
| Hand-off IMM-14 fail 3 lần (`IMM13_HANDOFF_IMM14_FAIL`) | ERROR | scheduler log | Notify admin (EC-07) |
| E-sign re-auth fail (`IMM13_ESIGN_INVALID`) | WARNING | audit | Cảnh báo nếu lặp |
| Cron escalate OOS > 30 ngày | INFO | scheduler log | Notify PTP |

PII / token / password KHÔNG vào log.

## VI.9. Threat model (STRIDE-lite)

| Threat | Vector | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| **S**poofing | Giả mạo Trưởng khoa duyệt stand-down | Thấp | Cao | E-sign re-auth password (VI.4) + session + role check |
| **T**ampering | Sửa `signature_hash` / audit entry | Thấp | Cao | Hash chain SHA-256, DocPerm no-edit/delete (VI.3), verify endpoint |
| **R**epudiation | Phủ nhận đã ký residual risk | Thấp | Cao | E-sign hash + `signed_by/at`, audit chain bất biến (NĐ98 ≥ 5 năm) |
| **I**nfo disclosure | Dept Head khoa A xem hồ sơ khoa B | Trung bình | Trung bình | User Permission per facility (VI.1), field permlevel cost |
| **D**enial of service | Concurrent reassign lock / N+1 list 1k | Trung bình | Trung bình | Optimistic lock `IMM13_CONCURRENT_UPDATE`, pagination, index location |
| **E**levation of privilege | KTV gọi `approve_reassignment` | Trung bình | Cao | Role check 3 lớp (whitelist → service → DocPerm), negative test UAT-IMM13-04 |

## VI.10. Penetration test

Trước release đầu tiên (AssetCore v3.x): Burp/ZAP scan, sqlmap (an toàn), CSRF test, role escalation (KTV → approve). Report lưu `docs/security/imm13_pentest.md`. ⬜ Chưa thực hiện (chờ scaffold + deploy UAT).

## VI.11. Sign-off

| Role | Người | Ngày | Chữ ký |
|---|---|---|---|
| Security Officer | – | – | ⬜ |
| QA Lead | – | – | ⬜ |
| Module Owner (PTP Khối 2) | – | – | ⬜ |

**Decision**: ⬜ Pass / ⬜ Pass with conditions / ⬜ Fail (block) — chờ scaffold + security test.

---

# Phần VII — Code Quality

## VII.1. Tool matrix

| Tool | Mục tiêu | Target | Cadence |
|---|---|---|---|
| **SonarQube** (BE Python) | bug 0 critical, code smell ≤ ngưỡng dự án, duplication ≤ 3%, coverage ≥ 70%, security hotspot review 100% | Quality Gate pass | mỗi PR (CI gate) |
| **ruff / black** (BE Python `services/imm13.py`, `api/imm13.py`, `repositories/*`) | 0 error, format consistent | 0 error | mỗi PR |
| **mypy** | type hints cho service layer (CLAUDE §15, CONVENTIONS §6) | 0 error `services/imm13.py` | mỗi PR |
| **Lighthouse** (FE) | Performance / A11y / Best Practices / SEO | ≥ 90 / ≥ 95 / ≥ 90 / ≥ 80 | mỗi release lớn + monthly |
| **ESLint + vue-tsc** (FE) | 0 error, 0 warning prod build | 0 / 0 | mỗi PR FE |
| **Bundle size** (FE chunk imm13) | main / async chunk | ≤ 250KB / ≤ 80KB gzip | mỗi PR FE (CI report) |

*(Tất cả chưa chạy — BE/FE chưa scaffold. Đây là gate dự kiến cho Sprint Wave 3.)*

## VII.2. Cadence

- SonarQube: mỗi PR (CI gate, fail nếu Quality Gate fail).
- Lighthouse: mỗi release lớn + monthly audit.
- ESLint / ruff / mypy: mỗi PR (CI gate).
- Bundle size: mỗi PR FE (CI report, fail nếu vượt budget).
- Khi báo cáo final: gắn screenshot SonarQube + Lighthouse vào [09 §Release Notes](./09_Release.md).

---

# Phụ lục A — Template per UAT scenario

```markdown
### UAT-IMM-13-<NN> — <Tên>

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
### TC-IMM-13-<LAYER>-<NN> — <Tên>

**Component (I.1)**: <…>
**Liên kết**: US-<NN> | BR-<NN> | ACT-<NN>
**Kỹ thuật (II.1/II.2)**: <vd BVA boundary `residual_risk items = 2`>
**Priority (I.3)**: Critical / High / Medium / Low
**Test type**: Unit / Integration / API / E2E
**Pre-condition**: <fixture / state setup>

**Input**:
- <field>: <value>

**Steps**:
1. <…>
2. <…>

**Expected**:
- ServiceError(code=IMM13_RISK_ITEMS_INSUFFICIENT)
- doc.workflow_state unchanged

**Post-condition**: <DB rollback / fixture cleanup>
```

# Phụ lục C — Workflow State Transition Test template

```markdown
### TC-IMM-13-WF-<NN> — <action>: <from> → <to>

**Workflow JSON**: `<path>.json`
**Role required**: <…>
**Pre-condition**: doc.workflow_state = <from>, gate <Gx> đã pass
**Action**: apply_workflow(doc, "<action>")
**Expected (happy)**: doc.workflow_state = <to>, docstatus = <…>, audit entry created
**Expected (negative role)**: PermissionError / FORBIDDEN
**Expected (gate fail)**: ServiceError(code=IMM13_<…>)
```

---

# DoD — File 07 hoàn chỉnh

## I. Test Analysis
- [x] I.1 Component Inventory liệt kê đủ artefact (28 dòng, đối chiếu 04/05/06)
- [x] I.2 mỗi US / BR / Activity có ≥ 1 dòng map (9 US, 6 BR, 3 Activity)
- [x] I.3 Risk priority gán cho mọi component (không trống)
- [x] I.4 Scope ghi rõ out-of-scope kèm lý do

## II. Test Design Techniques
- [x] II.1 chọn ≥ 4 black-box techniques (EP + BVA + Decision Table + State Transition + Use Case + Pairwise + Error Guessing)
- [x] II.2 white-box criteria xác định (statement + branch + MC/DC + path)
- [x] II.3 mapping component → kỹ thuật điền đầy đủ

## III. Test Plan
- [x] Test class structure cho mọi service public function (11 class dự kiến cho 9 fn + listener + cron)
- [x] ≥ 1 happy + 1 negative test mỗi function (kế hoạch)
- [x] Workflow transitions cover 100% (12 transition document, đếm lại khi có JSON)
- [x] Audit chain test (intact + tampered) — III.5
- [x] API test ≥ 60% coverage target + permission matrix
- [x] Performance target xác định (III.8)
- [ ] CI command chạy clean — **chưa**: BE chưa scaffold, `tests/test_imm13.py` chưa tồn tại
- [ ] SonarQube Quality Gate pass + Lighthouse ≥ target — **chưa**: chưa có code để quét

## IV. Traceability
- [x] IV.1 US → Test: mọi US (9) có ≥ 1 Test ID
- [x] IV.2 BR → Test: mọi BR (6) có happy + negative
- [x] IV.3 Component → Test: Critical/High có target coverage (số đo thực điền sau scaffold)

## V. UAT
- [x] Mỗi US chính có ≥ 1 UAT scenario (6 scenario)
- [x] ≥ 1 negative + permission + audit verify scenario (UAT-04 permission, UAT-05 negative, UAT-06 audit)
- [ ] Test data seed script chạy được — **chưa**: `scripts/uat/uat_imm13.py` chưa thiết kế
- [ ] Tester accounts đã tạo ở UAT site — **chưa**: site UAT chưa dựng, BE chưa scaffold
- [x] Sign-off section sẵn sàng

## VI. Security
- [x] DocPerm matrix đầy đủ (Decision Table, 7 action × 6 role)
- [x] Field nhạy cảm có permlevel ≠ 0 (kế hoạch VI.1/VI.5; permlevel cụ thể chốt khi scaffold)
- [ ] SQL injection + CSRF test pass — **chưa**: chưa có endpoint thực để test
- [ ] Audit chain test pass (intact + tampered) — **chưa**: chưa có BE
- [ ] Vendor isolation / permission negative test pass — **chưa**: chưa có BE
- [x] Threat model đủ 6 STRIDE với mitigation
- [ ] Sign-off đầy đủ trước go-live — **chưa**: chờ scaffold + security test

## VII. Code Quality
- [ ] SonarQube Quality Gate pass — **chưa**: chưa có code
- [ ] Lighthouse ≥ target — **chưa**: chưa có FE
- [ ] Bundle size ≤ budget — **chưa**: chưa có FE chunk
- [ ] Screenshot báo cáo gắn vào file 09 — **chưa**: chờ chạy thực

---

*File 07 này là PLANNING SKELETON — cấu trúc đầy đủ theo template, dữ liệu suy từ 02/04/05 (interface contract dự kiến). Khi BE scaffold xong (Sprint Wave 3), điền số đo coverage thực, ID test chính thức, kết quả UAT/security, và đánh dấu các DoD còn `[ ]`.*
