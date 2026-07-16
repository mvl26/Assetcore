# 07 — Kiểm thử & An ninh (Testing & QA & Security)

| Mục | Giá trị |
|---|---|
| Module | IMM-01 — Nhu cầu (Needs Assessment & Budget Estimation) |
| Phạm vi | Per-module |
| Owner | QA Lead + Security Officer |
| Liên kết | [02 Analysis](./02_Analysis_Design.md) · [03 Diagrams](./03_Diagrams.md) · [04 Backend](./04_Backend_Design.md) · [05 API](./05_API_Specification.md) · [06 Frontend](./06_Frontend_Design.md) |

> **Mục đích**: Suy ra test case có hệ thống từ phân tích (file 02) bằng kỹ thuật black-box + white-box, không liệt kê tự phát. Bao gồm: phân tích đối tượng test → chọn kỹ thuật → viết test → traceability → UAT → security → code quality. Phần VI là gate go-live.

> **Trạng thái Wave 2 — Live.** Test suite hiện tại: `assetcore/tests/test_imm01.py` (≈ 322 LOC, 9 test class, 38 test method) — cover scoring formula, priority classification, device target, VR-01-04 target_year, VR-01-05 score consistency, và Gates G01/G02/G03/G05. Các test class còn lại (lifecycle integration, workflow transition, API endpoint, `roll_into_plan`/`generate_demand_forecast`/`check_pending_request_overdue`) vẫn là **roadmap** chưa implement.

---

# Phần I — Test Analysis (Phân tích đối tượng test)

> Mục tiêu Phần I: trả lời 4 câu hỏi trước khi viết test case: (1) test cái gì (component inventory) (2) suy ra từ đâu (US/BR/Activity) (3) ưu tiên cái nào (risk) (4) loại trừ cái nào (out-of-scope).

## I.1. Component Inventory — Liệt kê phần mềm cần test

Liệt kê toàn bộ artefact test được của IMM-01. Mỗi dòng → ≥ 1 test class ở Phần III. Nguồn: `04 §DocType + §Service + §Hook`, `05 §Catalog`, `06 §Components`.

| # | Component | Loại | File / Tên | Test layer áp dụng |
|---|---|---|---|---|
| 1 | `IMM Needs Request` | DocType | `imm_needs_request.json` | Integration (lifecycle) |
| 2 | `IMM Procurement Plan` | DocType | `imm_procurement_plan.json` | Integration (lifecycle) |
| 3 | `Needs Priority Scoring` / `Budget Estimate Line` / `Procurement Plan Line` | Child table | `needs_priority_scoring.json` … | Integration (rollup) |
| 4 | `IMM Demand Forecast` | DocType | `imm_demand_forecast.json` | Integration (scheduler output) |
| 5 | IMM-01 Needs Workflow | Workflow | `workflow/imm_01_needs_workflow.json` (8 state, 24 transition) | Integration (state transition) |
| 6 | `_compute_priority_score`, `_classify_priority`, `_get_priority_weights` | Service function | `services/imm01.py` | Unit |
| 7 | `_validate_device_target`, `_vr01..`, `_vr02..`, `_vr04_target_year`, `_vr05_score_consistency` | Validator | `services/imm01.py` | Unit (BVA/EP) |
| 8 | `_validate_gate_g01..g05`, `_check_workflow_gates` | Gate validator | `services/imm01.py` | Unit (Decision Table) |
| 9 | `_rollup_budget`, `_rollup_plan_capex`, `_autofetch_replacement_metrics` | Service function | `services/imm01.py` | Unit + Integration |
| 10 | `roll_into_plan` | Service function | `services/imm01.py::roll_into_plan` | Integration (DB) |
| 11 | Hook chain `before_insert / validate / before_submit / on_submit / on_cancel` | Lifecycle hook | `services/imm01.py` (gọi từ controller) | Integration (audit chain) |
| 12 | `generate_demand_forecast`, `check_pending_request_overdue`, `budget_envelope_alert` | Scheduler job | `services/imm01.py` | Unit + Cron simulation |
| 13 | 22 endpoint whitelist (xem I.2 / III.6) | API endpoint | `api/imm01.py` | API integration |
| 14 | `write_audit_trail` → `IMM Audit Trail` | Lifecycle event | `services/imm01.py::write_audit_trail` | Integration (audit chain) |
| 15 | Imm01Dashboard + Needs Request list/detail/form | FE view / composable | `frontend/src/views/...` (xem 06) | E2E (Playwright) |
| 16 | Needs Request Pinia store | Pinia store | `frontend/src/stores/...` (xem 06) | Unit (vitest) — *(Cần khảo sát tên file)* |

## I.2. Trace nguồn test — User Stories, Activity Flows, Business Rules

3 bảng dẫn từ artefact phân tích (file 02) sang test layer. Mỗi US/BR/Activity phải có ≥ 1 test ở Phần III và xuất hiện trong matrix Phần IV. Nguồn: `02 §Functional Specs (US + AC)`, `02 §Business Rules`, `02 §Activity`.

### I.2.a. Từ User Story
| US ID | Tiêu đề ngắn | Acceptance Criteria # | Test layer dự kiến |
|---|---|---|---|
| US-01-001 | Tạo Needs Request hợp lệ (New) | AC1 (reqd fields), AC2 (justification) | Integration + API + UAT |
| US-01-002 | Replacement phải link Decommission Plan | AC1 (VR-01-02 soft warn) | Unit + API + UAT |
| US-01-010 | Chấm điểm 6 tiêu chí | AC1 (6/6), AC2 (weighted=4.35/P1) | Unit + API + UAT |
| US-01-020 | Lập dự toán CAPEX + OPEX 5 năm | AC1 (CAPEX>0), AC2 (OPEX year 1..5) | Unit + API + UAT |
| US-01-030 | Phê duyệt với funding_source | AC1 (G05 funding+approver) | Unit + API + UAT |
| US-01-040 | Xem Procurement Plan tổng hợp | AC1 (sort by score desc) | Integration + API + UAT |

### I.2.b. Từ Business Rule
| BR ID | Phát biểu | Component liên quan (I.1) | Kỹ thuật test phù hợp |
|---|---|---|---|
| BR-01-01 | NR phải có requesting_department + clinical_justification (reqd ở DocType; độ dài enforce ở G01) | DocType reqd + `_validate_gate_g01` | EP + BVA |
| BR-01-02 (G01) | utilization_pct_12m bắt buộc nếu request_type ∈ {Replacement, Upgrade} | `_validate_gate_g01` | Decision Table |
| BR-01-03 (VR-01-01) | 1 Asset chỉ 1 NR Replacement Active | `_vr01_unique_active_request_per_asset` | EP (cần DB) |
| BR-01-04 (G02) | Priority scoring đủ 6/6 + weighted_score đúng | `_compute_priority_score` + `_validate_gate_g02` | BVA + Decision Table |
| BR-01-05 (G03) | Budget Estimate CAPEX > 0 + OPEX đủ year_offset 1..5 | `_validate_gate_g03` | Decision Table + BVA |
| BR-01-06 (G04) | Tổng dự toán vs budget envelope (soft + rollup) | `_validate_gate_g04` (soft), `_rollup_plan_capex` | EP |
| BR-01-07 (G05) | board_approver + funding_source bắt buộc trước Submit | `_validate_gate_g05` | Decision Table |
| BR-01-08 (VR-01-02) | Replacement nên có IMM-13 Decom Plan (soft warn) | `_vr02_replacement_requires_decom_plan` | EP |
| BR-01-09 (VR-01-04) | target_year ≥ năm hiện tại | `_vr04_target_year` | BVA |
| BR-01-10 (VR-01-05) | abs(weighted_score − Σ weighted) < 0.01 | `_vr05_score_consistency` | BVA |

### I.2.c. Từ Activity Flow / BPMN
| Activity ID | Use Case | Branch chính | Branch ngoại lệ |
|---|---|---|---|
| ACT-01-01 | Tạo & Submit NR | Draft → Submitted | G01 fail (justification ngắn / thiếu utilization) |
| ACT-01-02 | Rà soát & Chấm điểm | Submitted → Reviewing → Prioritized | G02 fail (5/6 tiêu chí) |
| ACT-01-03 | Lập dự toán | Prioritized → Budgeted | G03 fail (thiếu OPEX year / CAPEX=0) |
| ACT-01-04 | Trình & Phê duyệt | Budgeted → Pending Approval → Approved | G05 fail (thiếu funding/approver), Reject (thiếu lý do) |
| ACT-01-05 | Gom vào Plan | Approved → roll_into_plan | reject non-Approved NR |

## I.3. Risk-based Priority

| Component (I.1) | Likelihood (1-5) | Impact (1-5) | Risk = L×I | Priority |
|---|---|---|---|---|
| Gate G05 (funding + approver trước Approve) | 3 | 5 | 15 | **Critical** |
| Workflow 24 transition (role gate Approve/Reject) | 3 | 5 | 15 | **Critical** |
| Audit chain (`write_audit_trail` → IMM Audit Trail) | 2 | 5 | 10 | High |
| `_compute_priority_score` (sai → sai ưu tiên ngân sách) | 3 | 4 | 12 | High |
| Gate G03 (CAPEX/OPEX budget) | 3 | 4 | 12 | High |
| Gate G01 (justification + utilization) | 4 | 3 | 12 | High |
| `roll_into_plan` (gom NR → Plan) | 2 | 4 | 8 | Medium |
| `_vr04_target_year` / `_vr05_score_consistency` | 3 | 2 | 6 | Medium |
| Scheduler `generate_demand_forecast` (DoS lock DB) | 2 | 3 | 6 | Medium |
| Imm01Dashboard (read-only KPI) | 2 | 2 | 4 | Low |

**Quy ước priority**: Critical (R ≥ 15) test trước, fail = block release · High (10 ≤ R < 15) bắt buộc trước go-live · Medium (5 ≤ R < 10) trong sprint · Low (R < 5) chỉ test khi báo cáo bug.

## I.4. Scope

- **In-scope**: service layer (scoring, gate validator, rollup), workflow 24 transition, lifecycle hook + audit chain, 22 API endpoint, UAT golden flow Draft → Approved → Plan.
- **Out-of-scope**:
  - Performance/load test → giao Phần III.8 (target-only, chưa chạy baseline).
  - Cross-module IMM-02 (Tech Spec) / IMM-13 (Decommission Plan) → chỉ smoke (VR-01-02 hiện soft warn, IMM-13 chưa LIVE).
  - Field-level diff UI rendering → Lighthouse + Playwright spot-check.
- **Assumptions**: master data đã seed (`AC Department`, `AC Asset Category`, `IMM Device Model`, scoring weights), test users đủ các role (xem V.2), Chrome/Edge ≥ 120.

---

# Phần II — Test Design Techniques (Kỹ thuật thiết kế test case)

> Mỗi test phải truy được về 1 kỹ thuật ở dưới.

## II.1. Black-box techniques

| Kỹ thuật | Khi nào dùng | Áp dụng vào IMM-01 (I.1) | Số test sinh ra |
|---|---|---|---|
| **Equivalence Partitioning (EP)** | Input có miền chia nhóm tương đương | `request_type` (New/Replacement/Upgrade/Add-on), `funding_source`, `workflow_state`, `priority_class` | 1 test/partition |
| **Boundary Value Analysis (BVA)** | Numeric/date/length có biên | `target_year` (≥ năm hiện tại), `clinical_justification` ≥ 200 ký tự, `total_capex` > 0, `weighted_score` tolerance 0.01, OPEX year_offset 1..5 | 2-3 test/biên |
| **Decision Table** | Multi-condition gate | G01 (justification × request_type × utilization), G02 (6 tiêu chí), G03 (CAPEX × OPEX), G05 (funding × approver) | 2^N rút gọn theo equivalence |
| **State Transition Testing** | Workflow finite state machine | `imm_01_needs_workflow.json` (Draft → Submitted → … → Approved/Rejected) | Mỗi transition + invalid transition |
| **Use Case Testing** | End-to-end actor flow | UAT scenario, API integration | 1/main + 1/alt + 1/exception |
| **Pairwise / Combinatorial** | Nhiều field optional kết hợp | Form tạo NR (request_type × device_category × device_model_ref × funding_source) | Min set cover all pairs |
| **Error Guessing** | null, empty, unicode, race | Mọi endpoint nhận user input | Bổ sung |

## II.2. White-box techniques

| Kỹ thuật | Áp dụng vào | Tiêu chí đạt | Công cụ |
|---|---|---|---|
| **Statement coverage** | Service functions (I.1) | ≥ 85% line | `coverage report` |
| **Branch / Decision coverage** | Function có if/else, try/except (gate, rollup) | ≥ 80% branch | `coverage --branch` |
| **Condition / MC/DC** | Gate phức hợp G01/G02/G03/G05 | Mỗi sub-condition kiểm soát outcome độc lập | Manual test design + coverage |
| **Path coverage** | `_compute_priority_score`, `_classify_priority` (≤ 20 LOC) | Toàn bộ path (loop 0,1,N) | Manual |

Ưu tiên Branch coverage cho service layer; MC/DC chỉ áp dụng vào gate logic.

## II.3. Mapping Component → Kỹ thuật

| Loại component | Kỹ thuật chính | Kỹ thuật phụ |
|---|---|---|
| Field validator (`_vr04`, `_vr05`) | BVA + EP | Error guessing |
| Gate logic (`_validate_gate_g0*`) | Decision Table | MC/DC |
| Workflow transition | State Transition | Use Case |
| Service function pure (`_compute_priority_score`) | EP + Branch coverage | BVA |
| API endpoint | Use Case + EP | Pairwise (form input) |
| Scheduler (`generate_demand_forecast`) | Use Case (state setup → run → assert) | Error guessing (lock, partial fail) |
| FE view (Playwright) | Use Case end-to-end | Error guessing (network 4xx/5xx, role gate) |

---

# Phần III — Test Plan (Kế hoạch thực thi)

## III.1. Test Pyramid

```
                  ┌────────────┐
                  │  E2E / UAT │   ~5%  ← Playwright; Golden Draft → Approved → Plan
                 ─┴────────────┴─
              ┌──────────────────────┐
              │   API Integration    │   ~15%  ← 22 endpoint @frappe.whitelist
             ─┴──────────────────────┴─
          ┌────────────────────────────────┐
          │  Workflow + DocType lifecycle  │   ~25%  ← FrappeTestCase, 24 transition
         ─┴────────────────────────────────┴─
      ┌────────────────────────────────────────────┐
      │         Unit — Service Layer               │   ~55%  ← TDD; 38 test hiện có
     ─┴────────────────────────────────────────────┴─
```

Mọi service function phải có test trước khi code (TDD — `CLAUDE.md §17`). Mỗi BR (BR-01-01 → BR-01-10) và Gate (G01 → G05) phải có ≥ 1 happy + 1 negative test.

## III.2. Unit test — Service Layer

File hiện có: `assetcore/tests/test_imm01.py` (≈ 322 LOC). Mỗi test class trace về ≥ 1 dòng I.1.

| Test class | Status | Function cover | Kỹ thuật | Cases (happy/negative) |
|---|---|---|---|---|
| `TestPriorityClassification` | ✅ Live | `_classify_priority()` | EP + BVA | P1/P2/P3/P4 + zero/negative (5 test) |
| `TestComputePriorityScore` | ✅ Live | `_compute_priority_score()` | BVA + EP | all-max→5.0/P1; all-zero→0.0; US-01-010→4.35/P1; row weight; unknown criterion; empty; weights sum=1.0 (7 test) |
| `TestValidateDeviceTarget` | ✅ Live | `_validate_device_target()` | EP | category-only OK; nothing→ServiceError "Nhóm thiết bị" (2 test) |
| `TestTargetYear` | ✅ Live | `_vr04_target_year()` | BVA | current/future OK; past + None → VALIDATION (4 test) |
| `TestScoreConsistency` | ✅ Live | `_vr05_score_consistency()` | BVA | within-tolerance OK; > 0.01 → VALIDATION; None=0 (4 test) |
| `TestGateG01` | ✅ Live | `_validate_gate_g01()` | Decision Table | New+long OK; short→VR-01-03; Replacement w/o util→BR; util=0 OK; Upgrade w/ util OK (5 test) |
| `TestGateG02` | ✅ Live | `_validate_gate_g02()` | Decision Table | 6/6 pass; 5/6→BUSINESS_RULE; empty→reject (3 test) |
| `TestGateG03` | ✅ Live | `_validate_gate_g03()` | Decision Table + BVA | full OPEX OK; zero CAPEX; thiếu year 4; no OPEX → reject (4 test) |
| `TestGateG05` | ✅ Live | `_validate_gate_g05()` | Decision Table | both set OK; missing funding/approver/both → BUSINESS_RULE (4 test) |
| `TestUniqueActiveRequest` | ⬜ Planned | `_vr01_unique_active_request_per_asset()` | EP | happy/fail duplicate (cần DB) |
| `TestReplacementDecomPlan` | ⬜ Planned | `_vr02_replacement_requires_decom_plan()` | EP | soft warn — test `msgprint` emit |
| `TestGateG04` | ⬜ Planned | `_validate_gate_g04()` | EP | hiện soft — wire khi cross-doc envelope rollup |
| `TestRollIntoPlan` | ⬜ Planned | `roll_into_plan()` | Use Case | tạo plan, append, reject non-Approved (cần DB) |
| `TestDemandForecast` | ⬜ Planned | `generate_demand_forecast()` | Use Case | skeleton record per category (cần DB) |
| `TestNeedsOverdueEscalation` | ⬜ Planned (E7 — BR-01-11) | `check_pending_request_overdue()` → `notify_needs_overdue()` | Use Case | Cần DB. Assert: (a) `get_users_with_role("Needs Manager") ≥ 1` (anti dead-gate); (b) ≥1 NR quá hạn → ≥1 Notification Log cho recipient; (c) 0 NR quá hạn → 0 Notification Log; (d) chạy scheduler 2 lần/ngày → KHÔNG double (dedup); (e) 0 recipient → KHÔNG raise. KHÔNG hồi quy `test_notifications`. |

Test sử dụng `SimpleNamespace` (không DB) — chạy ms-level, an toàn offline. Trích pattern thực tế:

```python
# assetcore/tests/test_imm01.py — actual file
class TestComputePriorityScore(unittest.TestCase):
    def test_brd_example_from_us_01_010(self):
        # clinical=5 risk=5 util=4 replace=5 compliance=3 budget=3 → 4.35
        doc = _make_doc([...])
        _compute_priority_score(doc)
        self.assertAlmostEqual(doc.weighted_score, 4.35, places=4)
        self.assertEqual(doc.priority_class, "P1")
```

## III.3. Integration — DocType lifecycle (planned)

File (roadmap): `assetcore/tests/test_imm_needs_request_doctype.py` — chưa tạo. Cover hook chain `before_insert_needs_request / validate_needs_request / before_submit_needs_request / on_submit_needs_request / on_cancel_needs_request`.

| Test | Setup | Action | Assert | Kỹ thuật |
|---|---|---|---|---|
| `test_before_insert_defaults` ⬜ | Draft NR | `doc.insert()` | request_date set; clinical_head sync từ department | EP |
| `test_validate_device_target_fail` ⬜ | NR no category/model | `doc.insert()` | ServiceError "Nhóm thiết bị" | EP |
| `test_before_submit_g05_fail` ⬜ | NR Pending, thiếu funding | `doc.submit()` | BUSINESS_RULE | Decision Table |
| `test_on_submit_creates_audit_trail` ⬜ | NR approved | `doc.submit()` | `IMM Audit Trail` record exists | Use Case |
| `test_rollup_budget` ⬜ | NR + CAPEX/OPEX lines | `validate` | total_capex / total_opex_5y / tco_5y đúng | BVA |

Fixture trong `setUpClass` phải có `tearDownClass` purge.

## III.4. Integration — Workflow transitions (planned)

File (roadmap): `assetcore/tests/test_imm01_workflow.py` — chưa tạo. Workflow `imm_01_needs_workflow.json` có **8 state** và **24 transition** (đếm bằng `python3 -c "import json; print(len(json.load(open('assetcore/assetcore/workflow/imm_01_needs_workflow.json'))['transitions']))"` → 24). 24 transition = 8 action logic × các role được phép (mỗi action có thêm dòng cho `AssetCore Super Admin`). Bắt buộc cover 100%.

| Action | From → To | Role required | Test pass | Test fail (wrong role / gate fail) |
|---|---|---|---|---|
| Gửi đề xuất | Draft → Submitted | Corrective User · Needs Manager · Super Admin | ☐ | ☐ (G01 fail) |
| Tiếp nhận rà soát | Submitted → Reviewing | Spec Manager · Needs Manager · Super Admin | ☐ | ☐ (wrong role) |
| Yêu cầu bổ sung | Submitted → Draft | Spec Manager · Needs Manager · Super Admin | ☐ | ☐ |
| Hoàn tất chấm điểm | Reviewing → Prioritized | Needs Manager · Spec Manager · Super Admin | ☐ | ☐ (G02: 5/6 rows) |
| Bác đề xuất sớm | Reviewing → Rejected | Needs Manager · Super Admin | ☐ | ☐ (wrong role) |
| Hoàn tất dự toán | Prioritized → Budgeted | Needs Manager · Super Admin | ☐ | ☐ (G03: no OPEX) |
| Trình BGĐ | Budgeted → Pending Approval | Needs Manager · Super Admin | ☐ | ☐ |
| Phê duyệt | Pending Approval → Approved | Procurement Manager · Super Admin | ☐ | ☐ (G05: no funding_source / wrong role) |
| Bác đề xuất | Pending Approval → Rejected | Procurement Manager · Super Admin | ☐ | ☐ (no rejection_reason) |
| Yêu cầu chỉnh dự toán | Pending Approval → Budgeted | Procurement Manager · Super Admin | ☐ | ☐ |

State Transition Testing — mỗi edge = 1 test pass + 1 test fail. (Lưu ý: tên role trong workflow JSON dùng role chuẩn AssetCore — `Needs Manager`, `Spec Manager`, `Procurement Manager`, `Corrective User`, `AssetCore Super Admin` — không phải nhãn nghiệp vụ `IMM Clinical User`/`IMM Board Approver` ở doc cũ.)

> ⚠️ **Stale-count flag (light-touch — không rewrite):** dòng "8 state / 24 transition" ở trên là số ĐẾM CŨ. Fixture **hiện tại** (verified 2026-07-14): `imm_01_needs_workflow.json` = **34 transition-row → 10 cạnh distinct** (`{(state,action,next_state)}`, khớp 10 dòng bảng); `imm_01_plan_workflow.json` = **10 transition-row → 3 cạnh distinct**. Guard III.4a dưới dùng con số MỚI (grounded).

## III.4a. Guard — Workflow-Surface Integrity (CR-WF-01-SURFACE · silent-CTA-loss)

File: `tests/test_imm01.py` → class **`TestImm01WorkflowSurfaceIntegrity`** (⬜ Planned, **test-only** — 0 chạm runtime `.py`, 0 gunicorn `--preload` reload / 0 `bench migrate`). Khoá **INV-01-SURFACE-A/B/C** (spec: `04 §5.4` + ADR-IMM-01-03). Đóng lỗ mà guard toàn cục `test_workflow_admin_override` **KHÔNG** bắt: nó `glob` JSON theo `name`, không biết 2 surface IMM-01 (`_nr_allowed_transition_actions` `api/imm01.py:187` · `_plan_allowed_transition_actions` `api/imm01.py:476`) resolve workflow theo **`document_type`+`is_active`** (Frappe `get_workflow_name`), KHÔNG qua tên literal (KHÁC IMM-04).

| Test ID | Invariant | Assert (grounded) | RED vector |
|---|---|---|---|
| **TC-01-WF-SURFACE-01** | INV-01-SURFACE-A (NR) | Oracle parse `fixtures/workflow.json` + `imm_01_needs_workflow.json`: `document_type=='IMM Needs Request'` có **đúng 1** entry `is_active==1`, `name=='IMM-01 Needs Workflow'`; live `get_workflow_name('IMM Needs Request')=='IMM-01 Needs Workflow'`; `inspect` `api/imm01._DT_NR=='IMM Needs Request'`. | rename · xoá · deactivate · duplicate active workflow Needs · drift `_DT_NR` |
| **TC-01-WF-SURFACE-02** | INV-01-SURFACE-A (Plan) | Đối xứng: `document_type=='IMM Procurement Plan'` → **đúng 1** active `name=='IMM-01 Plan Workflow'`; live `get_workflow_name(...)` == kỳ vọng; `_DT_PP=='IMM Procurement Plan'`. | rename · xoá · deactivate · duplicate active workflow Plan · drift `_DT_PP` |
| **TC-01-WF-SURFACE-03** | INV-01-SURFACE-B (NR live-wiring) | NR seed `workflow_state='Draft'` + `set_user(<Needs Manager | System Manager | Super Admin>)` (∈ allowed cạnh Draft-out `Gửi đề xuất`; **KHÔNG** Procurement Manager) → `_nr_allowed_transition_actions(doc)` **NON-EMPTY**, `== dedupe(action for get_transitions(doc))`, chứa `Gửi đề xuất`. | workflow vỡ → `except→[]` permanent (RED) · emit stale ≠ get_transitions |
| **TC-01-WF-SURFACE-04** | INV-01-SURFACE-B (Plan live-wiring) | Plan seed `Draft` + `set_user(<Procurement Manager | Commissioning Manager | System Manager | Super Admin>)` → `_plan_allowed_transition_actions(doc)` NON-EMPTY, chứa `Phê duyệt kế hoạch`, `== dedupe(get_transitions)`. | như trên (Plan surface) |
| **TC-01-WF-SURFACE-05** | INV-01-SURFACE-C (degrade NR) | Cùng NR Draft, `set_user(<chỉ base role AssetCore System User>)` → `_nr_allowed_transition_actions` trả `[]` **GRACEFUL** (không raise); payload `_get_needs_request(name)` còn nguyên các field khác (không vỡ). | phân-định empty-thiếu-quyền ≠ empty-vỡ |
| **TC-01-WF-SURFACE-06** | INV-01-SURFACE-C (degrade Plan) | Đối xứng Plan: base-role user → `_plan_allowed_transition_actions=[]` graceful; payload `_get_procurement_plan` intact. | như trên |

**RED-before demo (chứng minh guard cắn — chạy THẬT, không false-green):**
1. Baseline `bench --site miyano run-tests --module assetcore.tests.test_imm01` → đọc dòng cuối `Ran N OK`.
2. **RED vector A (rename):** tạm đổi `name` `IMM-01 Needs Workflow` → `IMM-01 Needs Workflow-X` trong **bản-sao** workflow live (hoặc temp Workflow doctype `is_active`) → **TC-01-WF-SURFACE-01** FAIL (resolve ≠ kỳ vọng) → revert.
3. **RED vector B (monkeypatch):** `unittest.mock.patch('frappe.model.workflow.get_transitions', side_effect=Exception)` trong 1 TC riêng → **TC-01-WF-SURFACE-03/04** FAIL (`emit == []` permanent) → chứng minh surface `except→[]` là silent-loss thật; SURFACE-C (TC-05/06) VẪN `[]` graceful → **phân-định** đúng.
4. Restore → **GREEN**. `test_workflow_admin_override` 5-class **VẪN GREEN** và **KHÔNG** bị re-assert (every-edge-super-admin đã cover global — cross-ref, không chép).

## III.5. Integration — Audit chain integrity (planned)

2 test chính (file roadmap `test_imm01_audit.py`):
- (a) Sau N mutation NR (insert → score → submit), chain hash SHA-256 hợp lệ end-to-end qua `write_audit_trail`.
- (b) Khi 1 entry bị tamper (sửa `change_summary`), verify endpoint trả `chain_broken=true`.

Nguồn: `04 §Audit Trail` · `IMM Audit Trail` là shared DocType của IMM-00 (bảo vệ tập trung).

## III.6. API test (planned)

File (roadmap): `assetcore/tests/test_imm01_api.py` — chưa tạo. 22 endpoint thực tế (`grep "@frappe.whitelist" assetcore/api/imm01.py`):

GET: `list_needs_requests`, `get_needs_request`, `get_allowed_transitions`, `list_procurement_plans`, `get_procurement_plan`, `get_demand_forecast`, `dashboard_kpis`.
POST: `create_needs_request`, `update_needs_request`, `transition_workflow`, `submit_needs_request`, `score_needs_request`, `submit_budget_estimate`, `approve_needs_request`, `reject_needs_request`, `create_procurement_plan`, `set_budget_envelope`, `approve_plan`, `activate_plan`, `close_plan`, `remove_from_plan`, `roll_into_plan`.

Cover: happy + envelope `success=true`; invalid params → `code=INVALID_PARAMS`/`VALIDATION`; no permission → `code=FORBIDDEN`; pagination boundaries; idempotent retry.

| Test | Endpoint | Verify | Kỹ thuật |
|---|---|---|---|
| `test_list_default_pagination` ⬜ | `list_needs_requests` | `success=true`, `page=1`, `total ≥ 0` | Use Case |
| `test_list_filter_state` ⬜ | `list_needs_requests?filters={"workflow_state":"Submitted"}` | mọi item state=Submitted | EP |
| `test_get_not_found` ⬜ | `get_needs_request?name=FAKE` | `success=false`, `code=NOT_FOUND` | EP |
| `test_create_happy` ⬜ | `create_needs_request` | `success=true`, name `NR-…` | Use Case |
| `test_create_no_permission` ⬜ | `create_needs_request` (role Auditor) | `code=FORBIDDEN` | EP (permission partition) |
| `test_score_compute` ⬜ | `score_needs_request` 6 rows | `weighted_score=4.35`, `priority_class=P1` | Use Case |
| `test_approve_g05_fail` ⬜ | `approve_needs_request` missing funding | `code=BUSINESS_RULE` | Decision Table |
| `test_get_needs_request_allowed_transitions` ⬜ | `get_needs_request` (NR Pending Approval, user Procurement Manager) | payload có `allowed_transitions` ⊇ `["Phê duyệt","Bác đề xuất"]` | ADR-IMM-01-02 |
| `test_approve_wrong_role_clean_forbidden` ⬜ | `_approve_needs_request` (NR Pending Approval, user role KHÔNG duyệt vd Needs Manager) | `ServiceError.code=FORBIDDEN`; message KHÔNG chứa `<strong>`/"transition not allowed"; `workflow_state` giữ `Pending Approval` | ADR-IMM-01-02 (đối xứng `test_approve_nonempty_plan_wrong_role_clean_forbidden`) |
| `test_reject_wrong_role_clean_forbidden` ⬜ | `_reject_needs_request` (user role KHÔNG duyệt) | `code=FORBIDDEN` sạch; state không đổi | ADR-IMM-01-02 |
| `test_approve_procurement_manager_ok` ⬜ | `_approve_needs_request` (user Procurement Manager thuần) | `workflow_state=Approved`, docstatus=1; `write_audit_trail` được gọi (regression xanh) | ADR-IMM-01-02 |
| `test_dashboard_kpis_format` ⬜ | `dashboard_kpis?period=2026-Q2` | 6 KPI key present *(cần khảo sát key chính xác)* | Use Case |

> **FE vitest** `needsRequestDetailCtaGating.test.ts` (đối xứng `procurementPlanCtaGating.test.ts`): mount `NeedsRequestDetailView` với `currentDoc.allowed_transitions` = `["Phê duyệt","Bác đề xuất"]` → 2 nút render; = `[]` → 2 nút ẩn; field vắng → 0 nút, không crash. Grep guard: `NeedsRequestDetailView.vue` KHÔNG còn `isBoardApprover` HAY literal `'Pending Approval'` cho 2 CTA. `vue-tsc` sạch (type `NeedsRequestDoc.allowed_transitions?: string[]`).

## III.7. E2E browser (Playwright)

Dùng cho flow UI khó cover bằng API: dropdown cascade device_category → device_model_ref, modal confirm Approve/Reject, workflow button visibility theo role (Needs User không thấy nút Submit/Approve). Tham chiếu `assetcore-test` skill (Playwright MCP recipes + data rules).

## III.8. Performance test (target-only — chưa chạy baseline)

| Metric | Target | Method |
|---|---|---|
| List 200 NR p95 | ≤ 400ms | k6 GET `list_needs_requests` |
| `create_needs_request` p95 | ≤ 600ms | k6 POST batch |
| `generate_demand_forecast` | ≤ 5min/1000 record | `time bench execute assetcore.services.imm01.generate_demand_forecast` |

## III.9. Test data & Fixtures

| Loại | Cách seed | File |
|---|---|---|
| Master data (AC Department, AC Asset Category, IMM Device Model) | `fixtures/*.json` (cài qua `bench migrate`) | `assetcore/fixtures/` |
| Test records | `SimpleNamespace` in-test (unit) / `test_records.json` (integration roadmap) | `imm_needs_request/test_records.json` *(Cần tạo)* |
| UAT seed | Python script | `assetcore/scripts/uat/uat_imm01.py` *(Cần tạo)* |

UAT data phải thực tế (tên bệnh viện VN, mã NCC chuẩn). Backend test fixture mới dùng prefix `_Test`.

## III.10. Run commands & Coverage gate

```bash
# Module test
bench --site miyano run-tests --app assetcore --module assetcore.tests.test_imm01
# Coverage
coverage run -m unittest assetcore.tests.test_imm01 && coverage report
# Workflow smoke
bench --site miyano run-tests --module assetcore.tests.test_imm00_smoke
```

| Layer | Target coverage | Đo |
|---|---|---|
| Service (`services/imm01.py`) | ≥ 85% line + ≥ 80% branch | `coverage --branch` |
| DocType lifecycle | ≥ 70% | `coverage report` |
| API (`api/imm01.py`) | ≥ 60% | `coverage report` |
| Frontend (vue-tsc) | 0 error | `npm run build` |

*(Coverage % thực đo: Cần khảo sát — chưa chạy `coverage report` cho module này; bảng trên là target.)*

---

# Phần IV — Traceability Matrices

> Mọi test ở Phần III phải xuất hiện ở cả 3 bảng (audit ngược: thiếu cover US? BR? component?).

## IV.1. US → Test mapping

| US ID | AC | Test ID (III.x) | Layer | Status |
|---|---|---|---|---|
| US-01-001 | AC1/AC2 | `TestValidateDeviceTarget`; `test_create_happy` | Unit + API | ✅ Live (unit) / ⬜ Planned (API) |
| US-01-002 | AC1 | `TestReplacementDecomPlan` | Unit | ⬜ Planned |
| US-01-010 | AC1/AC2 | `TestComputePriorityScore::test_brd_example_from_us_01_010`; `TestGateG02` | Unit | ✅ Live |
| US-01-020 | AC1/AC2 | `TestGateG03` | Unit | ✅ Live |
| US-01-030 | AC1 | `TestGateG05`; `test_approve_g05_fail` | Unit + API | ✅ Live (unit) / ⬜ Planned (API) |
| US-01-040 | AC1 | `TestRollIntoPlan` | Integration | ⬜ Planned |

## IV.2. BR → Test mapping

| BR ID | Phát biểu (rút gọn) | Test ID | Kỹ thuật | Happy / Negative |
|---|---|---|---|---|
| BR-01-01 | reqd + justification ≥ 200 | `TestGateG01` | Decision Table | 1 / 1 |
| BR-01-02 (G01) | utilization bắt buộc Replacement/Upgrade | `TestGateG01` | Decision Table | 2 / 1 |
| BR-01-03 (VR-01-01) | 1 Asset 1 NR Replacement Active | `TestUniqueActiveRequest` ⬜ | EP | 0 / 0 (planned) |
| BR-01-04 (G02) | 6/6 + weighted đúng | `TestComputePriorityScore` + `TestGateG02` | BVA + Decision Table | 4 / 3 |
| BR-01-05 (G03) | CAPEX > 0 + OPEX 1..5 | `TestGateG03` | Decision Table + BVA | 1 / 3 |
| BR-01-06 (G04) | dự toán vs envelope | `TestGateG04` ⬜ | EP | 0 / 0 (planned, soft) |
| BR-01-07 (G05) | funding + approver | `TestGateG05` | Decision Table | 1 / 3 |
| BR-01-08 (VR-01-02) | Replacement nên có Decom Plan | `TestReplacementDecomPlan` ⬜ | EP | 0 / 0 (planned) |
| BR-01-09 (VR-01-04) | target_year ≥ năm hiện tại | `TestTargetYear` | BVA | 2 / 2 |
| BR-01-10 (VR-01-05) | abs(score − Σ weighted) < 0.01 | `TestScoreConsistency` | BVA | 2 / 1 |

## IV.3. Component → Test mapping

| Component (I.1) | Test ID | Test layer | Coverage % | Risk priority (I.3) |
|---|---|---|---|---|
| `imm01::_compute_priority_score` | `TestComputePriorityScore` | Unit | *(Cần khảo sát)* | High |
| `imm01::_classify_priority` | `TestPriorityClassification` | Unit | *(Cần khảo sát)* | High |
| `imm01::_validate_gate_g01` | `TestGateG01` | Unit | *(Cần khảo sát)* | High |
| `imm01::_validate_gate_g02` | `TestGateG02` | Unit | *(Cần khảo sát)* | High |
| `imm01::_validate_gate_g03` | `TestGateG03` | Unit | *(Cần khảo sát)* | High |
| `imm01::_validate_gate_g05` | `TestGateG05` | Unit | *(Cần khảo sát)* | **Critical** |
| `imm01::_vr04_target_year` | `TestTargetYear` | Unit | *(Cần khảo sát)* | Medium |
| `imm01::_vr05_score_consistency` | `TestScoreConsistency` | Unit | *(Cần khảo sát)* | Medium |
| `imm01::_validate_device_target` | `TestValidateDeviceTarget` | Unit | *(Cần khảo sát)* | Medium |
| Workflow 24 transition | `test_imm01_workflow.py` ⬜ | Integration | 0% | **Critical** |
| `api/imm01.py` (22 endpoint) | `test_imm01_api.py` ⬜ | API | 0% | High |
| `imm01::roll_into_plan` | `TestRollIntoPlan` ⬜ | Integration | 0% | Medium |
| Audit chain | `test_imm01_audit.py` ⬜ | Integration | 0% | High |

---

# Phần V — UAT Script

## V.1. Phạm vi UAT

- **In-scope**: scenario theo US (V.4) — golden flow Draft → Submitted → Reviewing → Prioritized → Budgeted → Pending Approval → Approved → roll_into_plan.
- **Out-of-scope**: performance (III.8), security (Phần VI).
- **Pre-condition**: site UAT deploy build Wave 2; fixture loaded (`AC Department`, `AC Asset Category`, `IMM Device Model`, scoring weights); tester accounts active; Chrome/Edge ≥ 120.

## V.2. Tester accounts

| Username | Role | Vai trò UAT |
|---|---|---|
| `clinical@hospital.vn` | Needs User | Tạo NR, chuyển trạng thái Gửi đề xuất |
| `htm.reviewer@hospital.vn` | Spec Manager | Tiếp nhận rà soát, hỗ trợ chấm điểm |
| `khtc@hospital.vn` | Needs Manager | Chấm điểm, lập dự toán, tạo Plan, Trình BGĐ |
| `vp.block1@hospital.vn` | Procurement Manager | Phê duyệt / Bác đề xuất |
| `auditor@hospital.vn` | AssetCore Auditor | Verify read-only / FORBIDDEN case |
| `cmms.admin@hospital.vn` | AssetCore Super Admin | Override |

Phải có account role thấp (`Needs User`, `AssetCore Auditor`) để cover FORBIDDEN case — không chỉ Admin.

## V.3. Test data đã seed

| DocType | Số lượng | Ghi chú |
|---|---|---|
| AC Department | ≥ 3 | đủ test scope filter |
| AC Asset Category | ≥ 5 | cover device_category dropdown |
| IMM Device Model | ≥ 5 | cover device_model_ref cascade |
| IMM Needs Request | ≥ 6 (mỗi state ≥ 1) | cover happy + edge + permission |
| IMM Procurement Plan | 1 (`PP-26-001`) | cover roll_into_plan |

Reset script đi kèm: `assetcore/scripts/uat/uat_imm01.py` *(Cần tạo)*.

## V.4. UAT Scenarios — Suy ra từ US + Activity

Mỗi scenario theo template Phụ lục A. ID `UAT-IMM-01-NN`.

| ID | Actor | Pre-condition | US/BR cover | Kỹ thuật | Kết quả mong đợi |
|---|---|---|---|---|---|
| UAT-IMM-01-01 | Needs User | IMM Device Model tồn tại | US-01-001, BR-01-01 | Use Case happy | NR type=New, justification ≥ 200, Gửi đề xuất → Submitted; audit "Submitted" ghi |
| UAT-IMM-01-02 | Needs User | Asset không có Decom Plan | US-01-002, BR-01-08 | Use Case alt | NR Replacement → soft warn (msgprint) VR-01-02, vẫn tạo được (chưa block) |
| UAT-IMM-01-03 | Needs User | — | BR-01-02 (G01) | EP negative | NR Replacement thiếu utilization_pct_12m → Gửi đề xuất fail "utilization_pct_12m" |
| UAT-IMM-01-04 | Needs Manager | NR ở Reviewing | US-01-010, BR-01-04 | Use Case happy | Chấm 6 tiêu chí → weighted_score=4.35, P1; Hoàn tất chấm điểm → Prioritized |
| UAT-IMM-01-05 | Needs Manager | NR ở Reviewing | BR-01-04 (G02) | State Transition negative | Chấm 5/6 → "Hoàn tất chấm điểm" fail G02 |
| UAT-IMM-01-06 | Needs Manager | NR ở Prioritized | US-01-020, BR-01-05 | Use Case happy | Nhập CAPEX + OPEX year 1..5, funding_source=NSNN → total_capex/tco_5y đúng; Budgeted |
| UAT-IMM-01-07 | Needs Manager | NR ở Prioritized | BR-01-05 (G03) | State Transition negative | Bỏ OPEX year 4 → "Hoàn tất dự toán" fail "OPEX 5 năm" |
| UAT-IMM-01-08 | Needs Manager | NR ở Budgeted | US-01-030 | Use Case happy | Trình BGĐ → Pending Approval |
| UAT-IMM-01-09 | Procurement Manager | NR ở Pending Approval, funding set | US-01-030, BR-01-07 | Use Case happy | board_approver=self, Phê duyệt → docstatus=1, Approved; audit "Approved" ghi |
| UAT-IMM-01-10 | Procurement Manager | NR ở Pending Approval | — | Use Case alt | Bác đề xuất không nhập rejection_reason → VALIDATION, state không đổi |
| UAT-IMM-01-11 | Needs Manager | 3 NR Approved | US-01-040, BR-01-06 | Use Case happy | roll_into_plan → Plan `PP-26-001`, plan_items sort by weighted_score desc; NR.procurement_plan link set |
| UAT-IMM-01-12 | AssetCore Auditor | NR bất kỳ | — | EP permission verify | Auditor chỉ Read; không thấy nút Submit/Approve; gọi `create_needs_request` → FORBIDDEN |

**Quy tắc suy scenarios**: mỗi US → ≥ 1 happy; mỗi Activity branch ngoại lệ (I.2.c) → ≥ 1; mỗi role mutate → ≥ 1 permission verify; mỗi terminal transition → ≥ 1 audit verify; ≥ 1 negative per BR Critical.

## V.5. Tổng hợp kết quả & Bug found

| Scenario | Status (Pass/Fail/Block) | Tester | Ngày | Ghi chú |
|---|---|---|---|---|
| UAT-IMM-01-01 … 12 | *(Chờ thực thi UAT)* | | | |

Bug list: `Issue ID · Severity (Blocker/Major/Minor/Trivial) · Mô tả · Fix status` — *(Cập nhật sau buổi UAT.)*

- **Acceptance**: ≥ 95% PASS, Blocker = 0, Major ≤ 2 (có workaround).
- **Sign-off**: BA Lead + QA Lead + Module Owner (PTP Khối 1) + End-user.

---

# Phần VI — Security Review (gate)

## VI.1. RBAC

**Role definitions** (`fixtures/role.json` + `role_profile.json`): `AssetCore Super Admin`, `Needs Manager`, `Needs User`, `Spec Manager`, `Procurement Manager`, `Corrective User`, `AssetCore Auditor`, `AssetCore System User`.

**DocPerm matrix — `IMM Needs Request`** (đọc từ `imm_needs_request.json`):

| Role | Read | Write | Create | Submit | Cancel | Amend | Delete | permlevel |
|---|---|---|---|---|---|---|---|---|
| AssetCore Super Admin | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 0 |
| Needs Manager | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 0 |
| Needs User | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | 0 |
| AssetCore Auditor | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 0 |
| AssetCore System User | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 0 |
| AssetCore Super Admin | ✅ | ✅ | — | — | — | — | — | **1** |
| Needs Manager | ✅ | ✅ | — | — | — | — | — | **1** |
| AssetCore Auditor | ✅ | ❌ | — | — | — | — | — | **1** |

> permlevel-1 = các field tài chính/phê duyệt (`section_funding`). Không có DocPerm permlevel-1 nào → Frappe strip field khi `save()` với mọi user (trừ Administrator).

**DocPerm matrix — `IMM Procurement Plan`** (đọc từ `imm_procurement_plan.json`):

| Role | Read | Write | Create | Submit | Cancel |
|---|---|---|---|---|---|
| AssetCore Super Admin | ✅ | ✅ | ✅ | ✅ | ✅ |
| Needs Manager | ✅ | ✅ | ✅ | ✅ | ✅ |
| Needs User | ✅ | ✅ | ✅ | ❌ | ❌ |
| AssetCore Auditor | ✅ | ❌ | ❌ | ❌ | ❌ |
| AssetCore System User | ✅ | ❌ | ❌ | ❌ | ❌ |

**Field-level permission** (`permlevel = 1` trên `IMM Needs Request` — section `section_funding`): `funding_source`, `funding_evidence`, `board_approver`, `approval_date`, `rejection_reason`. ✅ **Implemented** — DocPerm permlevel-1 đã có trong JSON: `AssetCore Super Admin` (read+write), `Needs Manager` (read+write), `AssetCore Auditor` (read-only). Các role thấp (`Needs User`) KHÔNG có permlevel-1 → không thấy/sửa field tài chính (đúng yêu cầu Confidential). ⚠️ Trước khi có DocPerm này, `doc.save()` **âm thầm strip** field permlevel-1 với mọi user (trừ Administrator) → `funding_source` không lưu được → G05 chặn Submit (bug đã sửa).

**User Permission / row-level**: ⚠️ **Gap thực tế** — `IMM Needs Request` KHÔNG có trong `permission_query_conditions` (`hooks.py` chỉ wire AC Asset, Incident Report, Asset Repair, PM Work Order, Asset Commissioning). Hiện DocPerm cấp module-wide; chưa filter NR theo `requesting_department`. Roadmap snippet:

```python
# assetcore/permissions.py  ⬜ Planned — chưa wire vào hooks.permission_query_conditions
def needs_request_query(user):
    """Needs User chỉ thấy NR của khoa mình."""
    if frappe.has_role("Needs Manager", user) or frappe.has_role("AssetCore Super Admin", user):
        return ""  # See all
    dept = frappe.db.get_value("Employee", {"user_id": user}, "department")
    return f"(`tabIMM Needs Request`.requesting_department = %(dept)s)"  # parameterized
```

**Kỹ thuật**: Decision Table — mỗi (role × action × state) = 1 row, expected Allow/Deny.

## VI.2. API security

| Mục | Trạng thái | Ghi chú |
|---|---|---|
| Whitelist hygiene | ✅ | 22 `@frappe.whitelist`; mutating dùng `methods=["POST"]`; có docstring |
| CSRF | ✅ | Frappe default `X-Frappe-CSRF-Token` |
| Input validation | ✅ | `name`/Link validate qua `frappe.get_value`; payload parse JSON trong `_handle` |
| SQL injection | ✅ | Frappe ORM parameterized; không f-string vào raw SQL (kể cả query roadmap dùng `%(dept)s`) |
| Rate limit | ⚠️ Roadmap | Cần cấu hình cho `create_needs_request`, `approve_needs_request`, `roll_into_plan` |

## VI.3. Audit trail integrity

Mọi mutation NR sinh `IMM Audit Trail` qua `write_audit_trail` (hash SHA-256 chain). User KHÔNG có quyền edit/delete `IMM Audit Trail` (shared DocType IMM-00, bảo vệ tập trung — ISO 13485:7.5.9). Verify + tamper test ở III.5.

## VI.4. Authentication & session

Login Frappe default. Session timeout + lockout + password policy theo cấu hình site. API key rotation thủ công. 2FA = roadmap. *(Tham số cụ thể: Cần khảo sát `site_config.json`.)*

## VI.5. Data sensitivity

| Loại | Trường | Sensitivity | Bảo vệ |
|---|---|---|---|
| Tài chính | `funding_source`, `funding_evidence`, `total_capex`, `tco_5y` | Confidential | permlevel 1 section + role |
| Phê duyệt | `board_approver`, `approval_date` | Confidential | permlevel 1 |
| Nghiệp vụ | `clinical_justification`, `priority_class` | Internal | DocPerm |

Khẳng định: IMM-01 KHÔNG lưu patient data.

## VI.6. Vendor isolation

IMM-01 là module nội bộ (Needs → Budget → Approval) — KHÔNG có actor Vendor External. Role `Corrective User` (chỉ dùng cho transition "Gửi đề xuất") không thấy chi phí/internal note. Không có export cho role thấp. (Vendor isolation chính áp dụng ở IMM-09/12.)

## VI.7. Secrets management

Cấm commit `.env`/credential. `site_config.json` không lên git. External token lưu `frappe.conf`. Backup encrypt at-rest off-site. IMM-01 không có external integration secret riêng.

## VI.8. Logging & monitoring

| Sự kiện | Log level | Where | Alert? |
|---|---|---|---|
| Workflow transition | INFO | IMM Audit Trail | — |
| Gate fail (G01..G05) | WARN | Frappe error log | — |
| `check_pending_request_overdue` 30d+ | INFO | scheduler log | ✅ escalation digest (in-app + email) tới `Needs Manager` (E7); 0 recipient → WARN, không raise |
| `budget_envelope_alert` vượt envelope | WARN | scheduler log | ✅ alert |

PII / token KHÔNG vào log.

## VI.9. Threat model (STRIDE-lite)

| Threat | Vector | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| **S**poofing | Giả mạo Needs User submit NR khoa khác | Medium | High | ⚠️ Row-level filter `requesting_department` CHƯA wire (VI.1 gap) — hiện chỉ DocPerm module-wide |
| **T**ampering — Audit | Sửa `IMM Audit Trail` thay đổi lịch sử phê duyệt | Low | Critical | DocPerm no-write/no-delete + hash chain (IMM-00) |
| **T**ampering — Score | Sửa `weighted_score` bỏ qua compute | Medium | High | `_vr05_score_consistency` server-side recompute; tolerance 0.01 |
| **R**epudiation | Procurement Manager phủ nhận đã Approve | Low | High | IMM Audit Trail ghi actor + timestamp; immutable |
| **I**nfo Disclosure | Role thấp xem funding/approver | Medium | Medium | permlevel 1 section_funding |
| **D**enial of Service | `generate_demand_forecast` lock DB | Low | Medium | Batch + chạy ngoài giờ cao điểm (scheduler) |
| **E**levation of Privilege | Needs User tự Approve (bypass Procurement Manager) | Low | Critical | Workflow role check: chỉ Procurement Manager + Super Admin; DocPerm Needs User submit=0 |

## VI.10. Penetration test

Trước release đầu tiên: Burp/ZAP scan, sqlmap (an toàn), CSRF test, role escalation (Needs User gọi `approve_needs_request`). Report lưu `docs/security/`. *(Chưa thực thi.)*

## VI.11. Sign-off

| Role | Người | Ngày | Chữ ký |
|---|---|---|---|
| Security Officer | | | |
| QA Lead | | | |
| Module Owner (PTP Khối 1) | | | |

Decision: ☐ Pass · ☐ Pass with conditions (đóng gap row-level filter VI.1) · ☐ Fail (block).

---

# Phần VII — Code Quality

## VII.1. Tool matrix

| Tool | Mục tiêu | Target | Cadence |
|---|---|---|---|
| **SonarQube** (BE Python) | Bug 0 Critical, smell ≤ 5, duplication ≤ 3%, coverage ≥ 70%, security hotspot review 100% | Quality Gate pass | Mỗi PR |
| **Lighthouse** (FE — Imm01Dashboard) | Performance ≥ 90, Accessibility ≥ 95, Best Practices ≥ 90, SEO ≥ 80 | ≥ target | Mỗi release |
| **ESLint + vue-tsc** (FE) | 0 error, 0 warning prod build | pass | Mỗi PR FE |
| **ruff / black** (BE) | 0 error, format chuẩn PEP8 | pass | Mỗi PR |
| **Bundle size** (FE chunk imm01) | main ≤ 250 KB gzip, async ≤ 80 KB gzip | ≤ budget | Mỗi PR FE |

## VII.2. Cadence

- SonarQube: mỗi PR (CI gate, fail nếu Quality Gate fail).
- Lighthouse: mỗi release lớn + monthly audit.
- ESLint / ruff: mỗi PR (CI gate).
- Bundle size: mỗi PR FE (CI report, fail nếu vượt budget).

Gắn screenshot SonarQube + Lighthouse vào `09 §Release Notes` khi báo cáo final.

---

# Phụ lục A — Template per UAT scenario

```markdown
### UAT-IMM-01-<NN> — <Tên>

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
### TC-IMM-01-<LAYER>-<NN> — <Tên>

**Component (I.1)**: <…>
**Liên kết**: US-<NN> | BR-<NN> | ACT-<NN>
**Kỹ thuật (II.1/II.2)**: BVA boundary `target_year=current_year-1`
**Priority (I.3)**: Critical / High / Medium / Low
**Test type**: Unit / Integration / API / E2E
**Pre-condition**: <fixture / state setup>

**Input**:
- <field>: <value>

**Steps**:
1. <…>
2. <…>

**Expected**:
- ServiceError(code=VALIDATION, message contains "VR-01-04")
- doc.workflow_state unchanged

**Post-condition**: <DB rollback / fixture cleanup>
```

# Phụ lục C — Workflow State Transition Test template

```markdown
### TC-IMM-01-WF-<NN> — <action>: <from> → <to>

**Workflow JSON**: `assetcore/assetcore/workflow/imm_01_needs_workflow.json`
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
- [x] I.1 Component Inventory liệt kê đủ artefact (so với 04/05/06)
- [x] I.2 mỗi US / BR / Activity có ≥ 1 dòng map
- [x] I.3 Risk priority gán cho mọi component (không trống)
- [x] I.4 Scope ghi rõ out-of-scope kèm lý do

## II. Test Design Techniques
- [x] II.1 chọn ≥ 4 black-box techniques (EP + BVA + Decision Table + State Transition)
- [x] II.2 white-box criteria xác định (statement + branch)
- [x] II.3 mapping component → kỹ thuật điền đầy đủ

## III. Test Plan
- [x] Test class structure cho service public function (9 class Live)
- [ ] ≥ 1 happy + 1 negative test mỗi function — *VR-01-01, VR-01-02, G04, roll_into_plan, scheduler còn ⬜ Planned (cần DB fixture)*
- [ ] Workflow transitions cover 100% (24 transition) — *file `test_imm01_workflow.py` chưa tạo*
- [ ] Audit chain test (intact + tampered) — *chưa tạo*
- [ ] API test ≥ 60% coverage + permission matrix — *file `test_imm01_api.py` chưa tạo*
- [x] Performance target xác định (target-only, chưa baseline)
- [x] CI command chạy clean (`bench run-tests --module assetcore.tests.test_imm01`)
- [ ] **SonarQube Quality Gate pass** + **Lighthouse score ≥ target** — *chưa chạy/đính kèm báo cáo*

## IV. Traceability
- [x] IV.1 US → Test: mọi US có ≥ 1 Test ID
- [x] IV.2 BR → Test: mọi BR có dòng (Live cho BR-01-01/02/04/05/07/09/10; Planned cho 03/06/08)
- [ ] IV.3 Component → Test: Critical/High đạt coverage target III.10 — *coverage % chưa đo; workflow/API component = 0%*

## V. UAT
- [x] Mỗi US có ≥ 1 UAT scenario
- [x] ≥ 1 negative + permission + audit verify scenario
- [ ] Test data seed script chạy được — *`uat_imm01.py` chưa tạo*
- [x] Tester accounts đã liệt kê (đủ role, có role thấp Needs User + Auditor)
- [x] Sign-off section sẵn sàng

## VI. Security
- [x] DocPerm matrix đầy đủ (Decision Table, đọc từ JSON thực tế)
- [x] Field nhạy cảm có permlevel 1 (section_funding: funding/approver/rejection)
- [ ] SQL injection + CSRF test pass — *CSRF Frappe default OK; injection test chưa chạy*
- [ ] Audit chain test pass (intact + tampered) — *chưa tạo (III.5)*
- [ ] Vendor isolation test pass — *N/A IMM-01 (no Vendor External); nhưng row-level dept filter CHƯA wire (VI.1/VI.9 gap)*
- [x] Threat model đủ 6 STRIDE với mitigation
- [ ] Sign-off đầy đủ trước go-live — *chờ ký*

## VII. Code Quality
- [ ] SonarQube Quality Gate pass — *chưa chạy*
- [ ] Lighthouse ≥ target — *chưa chạy*
- [ ] Bundle size ≤ budget — *chưa đo*
- [ ] Screenshot báo cáo gắn vào file 09 — *chưa có*
