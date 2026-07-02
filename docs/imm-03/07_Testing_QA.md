# 07 — Kiểm thử & An ninh (Testing & QA & Security)

| Mục | Giá trị |
|---|---|
| Module | IMM-03 — Đánh giá Nhà cung cấp & Quyết định Mua sắm (Procurement) |
| Phạm vi | Per-module |
| Owner | QA Lead + Security Officer |
| Liên kết | 02 Analysis (US, BR, Activity, BPMN) · 03 Diagrams · 04 Backend · 05 API · 06 Frontend |

> **Mục đích**: Suy ra test case **có hệ thống** từ phân tích (file 02) bằng kỹ thuật black-box + white-box, không liệt kê tự phát. Bao gồm: phân tích đối tượng test → chọn kỹ thuật → viết test → traceability → UAT → security → code quality. Q3 là gate go-live.

> ✅ Module LIVE — Wave 2. Backend (`assetcore/services/imm03.py`, `assetcore/api/imm03.py`) và Frontend (Vue 3 + Pinia) đã triển khai. Unit test thuần Python (`test_imm03.py`) đã có; integration/workflow/API/UAT một phần còn ở trạng thái Planned.

---

# Phần I — Test Analysis (Phân tích đối tượng test)

> Mục tiêu Phần I: trả lời 4 câu hỏi trước khi viết test case: **(1) test cái gì** (component inventory) **(2) suy ra từ đâu** (US/BR/Activity) **(3) ưu tiên cái nào** (risk) **(4) loại trừ cái nào** (out-of-scope).

## I.1. Component Inventory — Liệt kê phần mềm cần test

Liệt kê artefact test được của IMM-03 (nguồn: 04 Backend §Service/§Hook · 05 API §Catalog · 06 Frontend §Views). Mỗi dòng → ≥ 1 test class ở Phần III.

| # | Component | Loại | File / Tên | Test layer áp dụng |
|---|---|---|---|---|
| 1 | IMM Vendor Evaluation | DocType (submittable, `VE-.YY.-.#####`) | `imm_vendor_evaluation.json` | Integration (lifecycle) |
| 2 | IMM Procurement Decision | DocType (submittable, `PD-.YY.-.#####`) | `imm_procurement_decision.json` | Integration (lifecycle) |
| 3 | IMM AVL Entry | DocType (submittable, `AVL-.YYYY.-.#####`) | `imm_avl_entry.json` | Integration (lifecycle) |
| 4 | IMM Vendor Scorecard | DocType | `imm_vendor_scorecard.json` | Integration (DB) |
| 5 | IMM Supplier Audit | DocType | `imm_supplier_audit.json` | Integration (lifecycle) |
| 6 | Vendor Evaluation workflow | Workflow (5 state, 6 transition) | `workflow/imm_03_vendor_eval_workflow.json` | Integration (state transition) |
| 7 | Procurement Decision workflow | Workflow (9 state, 8 transition) | `workflow/imm_03_decision_workflow.json` | Integration (state transition) |
| 8 | AVL workflow | Workflow (5 state, 7 transition) | `workflow/imm_03_avl_workflow.json` | Integration (state transition) |
| 9 | `_compute_eval_scores` | Service function (scoring) | `services/imm03.py::_compute_eval_scores` | Unit (EP + BVA) |
| 10 | `_parse_weighting` / `_parse_json_field` | Service helper | `services/imm03.py::_parse_weighting` / `_parse_json_field` | Unit (EP) |
| 11 | `_vr01_min_candidates` | Validator | `services/imm03.py::_vr01_min_candidates` | Unit (EP/Decision Table) |
| 12 | `_vr03_quotation_validity` | Validator | `services/imm03.py::_vr03_quotation_validity` | Unit (BVA date) |
| 13 | `_vr04_envelope_check` | Validator | `services/imm03.py::_vr04_envelope_check` (`ENVELOPE_HARD_LIMIT_PCT=105`) | Unit (BVA) |
| 14 | `_vr05_winner_avl_required` | Validator | `services/imm03.py::_vr05_winner_avl_required` | Unit (Decision Table) |
| 15 | `_vr07_unique_decision_per_spec` | Validator | `services/imm03.py::_vr07_unique_decision_per_spec` | Integration (DB lookup) |
| 16 | `_validate_gate_g04_method` | Gate logic | `services/imm03.py::_validate_gate_g04_method` (`_METHOD_RULES`) | Unit (Decision Table/MC-DC) |
| 17 | `_validate_gate_g05` | Gate logic | `services/imm03.py::_validate_gate_g05` | Unit (Decision Table) |
| 18 | `_mint_ac_purchase` | Service function | `services/imm03.py::_mint_ac_purchase` | Integration (cross-module) |
| 19 | `_update_plan_line_status` | Service function | `services/imm03.py::_update_plan_line_status` | Integration (IMM-01 link) |
| 20 | `_sync_supplier_avl_status` / `activate_avl` | Service function | `services/imm03.py::_sync_supplier_avl_status` | Integration |
| 21 | `validate_ac_purchase_imm_link` | Hook (AC Purchase `validate`) | `services/imm03.py::validate_ac_purchase_imm_link` | Integration (cross-module) |
| 22 | `validate_receipt_against_po` / `set_actual_delivery_on_received` | Service function | `services/imm03.py` | Unit + Integration |
| 23 | `check_avl_expiry` | Scheduler job (daily) | `services/imm03.py::check_avl_expiry` | Unit + Cron simulation |
| 24 | `check_audit_due` | Scheduler job | `services/imm03.py::check_audit_due` | Cron simulation |
| 25 | `check_decision_overdue` | Scheduler job | `services/imm03.py::check_decision_overdue` | Cron simulation |
| 26 | `update_vendor_scorecard` | Scheduler job (quarterly) | `services/imm03.py::update_vendor_scorecard` | Unit (idempotency) |
| 27 | 22 API endpoint | API | `api/imm03.py` (xem I.2 / III.6) | API integration |
| 28 | Vendor Profile / Eval / Decision / AVL views | FE view | `frontend/src/views/procurement/*View.vue` | E2E (Playwright) |
| 29 | Pinia store IMM-03 | FE store | `frontend/src/stores/imm03.ts` | Unit (vitest) |

## I.2. Trace nguồn test — User Stories, Activity Flows, Business Rules

Dẫn từ artefact phân tích (02) sang test layer. Mỗi US/BR/Activity phải có ≥ 1 test ở Phần III và xuất hiện ở matrix Phần IV.

### I.2.a. Từ User Story
*(→ 02 §IV.1 Functional Specifications)*

| US ID | Tiêu đề ngắn | Acceptance Criteria # | Test layer dự kiến |
|---|---|---|---|
| US-03-001 | Tạo Vendor Profile mở rộng từ AC Supplier | AC-1 tạo + cert Active, AC-2 cert Expiring ≤ 30 ngày | Integration + UAT |
| US-03-021 | Add candidate có check AVL | AC-1 in_avl=true no warning, AC-2 non-AVL warning + block submit | Unit + API + UAT |
| US-03-032 | VP Block1 Approve → Mint PO | AC-1 happy mint AC Purchase + Plan Line Awarded + event, AC-2 PO TBYT direct block (VR-03-08) | Integration + UAT |

### I.2.b. Từ Business Rule
*(→ 02 §IV.2 Business Rules)*

| BR ID | Phát biểu | Component liên quan (I.1) | Kỹ thuật test phù hợp |
|---|---|---|---|
| BR-03-01 / VR-03-07 | 1 Tech Spec ↔ 1 Decision Awarded | `_vr07_unique_decision_per_spec` (#15) | EP (DB state) |
| BR-03-02 / VR-03-01 | Min candidates phù hợp phương án (V1: warning) | `_vr01_min_candidates` (#11) | EP / Decision Table |
| BR-03-03 / VR-03-02 | Vendor non-AVL cần sign-off | `_check_avl_warnings` + `add_candidate` (#27) | EP |
| BR-03-04 / VR-03-03 | Quotation hết hạn không dùng | `_vr03_quotation_validity` (#12) | BVA (date boundary) |
| BR-03-05 / VR-03-04 | Awarded > 105% envelope cần justification | `_vr04_envelope_check` (#13) | BVA (104/105/106%) |
| BR-03-06 / G04 | Phương án mua sắm hợp pháp theo giá trị + loại | `_validate_gate_g04_method` (#16) | Decision Table |
| BR-03-07 / VR-03-05 | Winner phải có AVL Approved/Conditional | `_vr05_winner_avl_required` (#14) | Decision Table |
| BR-03-08 / VR-03-08 | PO TBYT cần link Decision (V1: soft warning) | `validate_ac_purchase_imm_link` (#21) | EP |

### I.2.c. Từ Activity Flow / BPMN
*(→ 02 §III Use Case Spec + §II.3 To-Be)*

| Activity ID | Use Case | Branch chính | Branch ngoại lệ |
|---|---|---|---|
| UC-IMM03-01 | Vendor Evaluation từ Spec Locked | Draft → Open RFQ → Quotation Received → Evaluated | E-03-04 quotation hết hạn; Cancelled từ Open RFQ / Quotation Received |
| UC-IMM03-02 | Procurement Decision → Award | Draft → Method Selected → Negotiation → Award Recommended → Pending Approval → Awarded → Contract Signed → PO Issued | E-03-01 dup decision; E-03-02 >105% envelope; E-03-06 G05 fail; E-03-08 mint fail rollback; Cancelled từ Pending Approval |

## I.3. Risk-based Priority

| Component (I.1) | Likelihood (1-5) | Impact (1-5) | Risk = L×I | Priority |
|---|---|---|---|---|
| `award_decision` + `_mint_ac_purchase` (#18) | 3 | 5 | 15 | **Critical** |
| `_validate_gate_g04_method` (#16) — hợp pháp Luật Đấu thầu | 3 | 5 | 15 | **Critical** |
| `_validate_gate_g05` (#17) | 3 | 5 | 15 | **Critical** |
| `_vr04_envelope_check` (#13) — money flow | 4 | 4 | 16 | **Critical** |
| `_vr05_winner_avl_required` (#14) | 3 | 4 | 12 | High |
| `_vr07_unique_decision_per_spec` (#15) | 2 | 5 | 10 | High |
| Decision workflow transitions (#7) | 3 | 4 | 12 | High |
| IMM Audit Trail integrity (Phần VI.3) | 2 | 5 | 10 | High |
| `_compute_eval_scores` (#9) | 3 | 3 | 9 | Medium |
| `check_avl_expiry` scheduler (#23) | 2 | 3 | 6 | Medium |
| `update_vendor_scorecard` idempotency (#26) | 2 | 3 | 6 | Medium |
| `_parse_weighting` / `_parse_json_field` (#10) | 2 | 2 | 4 | Low |
| FE views (#28) | 2 | 2 | 4 | Low |

**Quy ước priority**: Critical (R ≥ 15) test trước, fail = block release · High (10 ≤ R < 15) bắt buộc trước go-live · Medium (5 ≤ R < 10) trong sprint · Low (R < 5) chỉ test khi báo bug.

## I.4. Scope

**In-scope:**
- Service layer: 7 VR/Gate validator + scoring + 4 scheduler job (#9–#26).
- 3 workflow state machine (Eval 6 transition, Decision 8 transition, AVL 7 transition — tổng **21 transition**).
- Cross-module integration: mint AC Purchase, update Procurement Plan Line, sync AC Supplier AVL status.
- 22 REST endpoint + RBAC permission boundary.

**Out-of-scope:**
- Performance/load test → giao Phần III.8 (chưa chạy).
- E-bidding API và full-text contract management (ngoài scope module, xem 02 §I.4).
- Cross-module sâu với IMM-04/09/15/10 cho Vendor Scorecard — V1 chỉ skeleton (`source_module="TBD"`); smoke only.

**Assumptions:**
- Master data AC Supplier, IMM Tech Spec (Locked), Procurement Plan Line đã seed.
- Test users đủ các role thật của module (xem VI.1) đã tạo trên site UAT.
- Patch `v3_1.003_install_imm03` đã thêm custom fields lên AC Supplier / AC Purchase.

---

# Phần II — Test Design Techniques (Kỹ thuật thiết kế test case)

> Mỗi test phải truy được về 1 kỹ thuật ở dưới.

## II.1. Black-box techniques

| Kỹ thuật | Khi nào dùng | Áp dụng vào AssetCore IMM-03 | Số test sinh ra |
|---|---|---|---|
| **Equivalence Partitioning (EP)** | Input có miền giá trị chia nhóm | `procurement_method` Select (5 options), `funding_source` (5 options), `in_avl` flag, AVL status partition | 1 test/partition |
| **Boundary Value Analysis (BVA)** | Numeric / date có biên | `awarded_price` quanh 105% envelope (`ENVELOPE_HARD_LIMIT_PCT`); ngưỡng `_METHOD_RULES` (50M/100M/1B); `quotation_validity` quanh today | 2-3 test/biên |
| **Decision Table** | Multi-condition gate | G04 (method × giá trị × legal_basis), G05 (funding × board_approver × contract_doc), VR-03-05 (AVL Approved/Conditional × category) | 2^N rút gọn |
| **State Transition Testing** | Workflow finite state machine | 3 workflow JSON — mỗi transition + invalid transition (vd Evaluated → Open RFQ, Awarded → Cancelled) | Mỗi transition + invalid |
| **Use Case Testing** | End-to-end actor flow | UAT scenarios, full flow Eval → Decision → PO | 1 main + alt + exception |
| **Pairwise** | Nhiều field optional kết hợp | Decision form (procurement_method × funding_source × có/không contract_doc) | Min set cover all pairs |
| **Error Guessing** | null, empty, unicode, race | Mọi endpoint nhận JSON payload (`weighting_scheme`, `quotations`, `scores_by_supplier`) | Bổ sung |

## II.2. White-box techniques

| Kỹ thuật | Áp dụng vào | Tiêu chí đạt | Công cụ |
|---|---|---|---|
| **Statement coverage** | Service functions (#9–#26) | ≥ 85% line (target) | `coverage report` |
| **Branch / Decision coverage** | `_validate_gate_g04_method`, `_vr04_envelope_check`, `_vr05_winner_avl_required` (có if/else) | ≥ 80% branch (target) | `coverage --branch` |
| **Condition / MC/DC** | G04 (method + giá trị + legal_basis), G05 (3 điều kiện AND) | Mỗi sub-condition kiểm soát outcome độc lập | Manual test design |
| **Path coverage** | `_compute_eval_scores` (≤ 20 LOC) | Path: empty candidates / unknown criterion / happy | Manual |

## II.3. Mapping Component → Kỹ thuật

| Loại component | Kỹ thuật chính | Kỹ thuật phụ |
|---|---|---|
| Field validator (`_vr*`) | BVA + EP | Error guessing |
| Gate logic (`_validate_gate_*`) | Decision Table | MC/DC |
| Workflow transition | State Transition | Use Case |
| Service function pure (`_compute_eval_scores`, `_parse_*`) | EP + Branch coverage | BVA |
| API endpoint | Use Case + EP | Pairwise (form input) |
| Scheduler (`check_avl_expiry`, `update_vendor_scorecard`) | Use Case (state setup → run → assert) | Error guessing (idempotency, partial fail) |
| FE view (Playwright) | Use Case end-to-end | Error guessing (network 4xx/5xx, role gate) |

---

# Phần III — Test Plan (Kế hoạch thực thi)

## III.1. Test Pyramid

```
                  ┌────────────┐
                  │  E2E / UAT │   ~5%   (12 UAT scenarios — V.4)
                 ─┴────────────┴─
              ┌──────────────────────┐
              │   API Integration    │   ~15%  (22 endpoint — III.6, Planned)
             ─┴──────────────────────┴─
          ┌────────────────────────────────┐
          │  Workflow + DocType lifecycle  │   ~25%  (21 transition — III.4, Planned)
         ─┴────────────────────────────────┴─
      ┌────────────────────────────────────────────┐
      │         Unit — Service Layer               │   ~55%  (test_imm03.py — 9 class Live)
     ─┴────────────────────────────────────────────┴─
```

*(→ CLAUDE.md §17 TDD mandatory)*

## III.2. Unit test — Service Layer

**File ground truth:** `assetcore/tests/test_imm03.py` — pure-Python `unittest`, KHÔNG mở DB (dùng `SimpleNamespace`). Các class dưới đây là **Live** (đã viết & chạy).

| Test class | Function cover | Kỹ thuật | Cases | Trạng thái |
|---|---|---|---|---|
| `TestParseWeighting` | `_parse_weighting` (#10) | EP (none/dict/valid JSON/invalid JSON) | 4 | ✅ Live |
| `TestParseJsonField` | `_parse_json_field` (#10) | EP | 4 | ✅ Live |
| `TestComputeEvalScores` | `_compute_eval_scores` (#9) | EP + Path + Decision Table (tie) | 3 cũ (higher wins / unknown criterion ignored / empty → no recommended) **+ 3 mới** (TC-32 tie-2 → recommended None + has_top_tie=1 / TC-33 tie-order-invariant / TC-34 zero → no tie) — xem §III.2.y | ✅ Live + ⬜ Planned (vòng 26 — TDD RED trước) |
| `TestGateG04Method` | `_validate_gate_g04_method` (#16) | Decision Table | 6 (draft skip / chỉ định vượt 50M raise / chỉ định trong hạn no legal_basis raise / chào hàng trong hạn + legal_basis pass / unknown method skip / no method skip) | ✅ Live |
| `TestMethodRules` | `_METHOD_RULES` constant (#16) | EP | 3 (chỉ định = 50M / chào hàng = 1B / đấu thầu rộng rãi no cap) | ✅ Live |
| `TestActualDeliveryDefault` | `set_actual_delivery_on_received` (#22) | EP | 3 (received empty → today / received có value giữ nguyên / non-received skip) | ✅ Live |
| `TestReceiptAgainstPO` | `validate_receipt_against_po` (#22) | EP + Error guessing | 3 (match pass / mismatch raise / unknown PO raise) | ✅ Live |
| `TestReceiptAgainstPO` (DB) | PO code set after insert; traceability PO → Decision → Plan | Integration | 2 | ✅ Live |
| `TestImm03ValidationRules` | `_vr03_quotation_validity`, `_vr04_envelope_check`, `_vr05_winner_avl_required` (#12–#14) | BVA + Decision Table | *(Cần khảo sát)* | ⬜ Planned |
| `TestAvlLiveSoT` | `_avl_is_live` / `_is_supplier_in_avl` / `_vr05_winner_avl_required` / `_sync_supplier_avl_status` / dashboard `avl_active` — predicate SoT "AVL còn hiệu lực" (INV-AVL-LIVE, 02 §IV.6) | BVA (date boundary) + Decision Table + Parity | 6+ (INV-1..6) | ⬜ Planned (vòng 22 — TDD RED trước) |
| `TestImm03ScorecardScheduler` | `update_vendor_scorecard` idempotency (#26) | Use Case | 1 | ⬜ Planned |
| `TestDecisionDrillParity` (DB) | `_dashboard_kpis().decision_states` vs `_list_decisions({'workflow_state': S})['total']` — INVARIANT card==drill (INV-DEC-DRILL, 02 §IV.8) | Parity + BVA (docstatus=2, value=0) | 8 (INV-DEC-DRILL-1..5 BE; 6..8 FE-vitest) — xem §III.2.z | ⬜ Planned (TDD RED trước) |

### III.2.x — TestAvlLiveSoT — Decision Table & BVA (spec vòng 22)

Predicate SoT: `LIVE ⇔ docstatus=1 ∧ workflow_state ∈ {Approved,Conditional} ∧ (valid_to IS NULL ∨ valid_to ≥ CURDATE())`. **Viết test TRƯỚC, RED-prove trên code cũ** (cũ thiếu `valid_to` ở `_is_supplier_in_avl`/`_vr05`/dashboard → ca hết-hạn PASS sai).

| TC | Invariant | Setup | Action | Assert |
|---|---|---|---|---|
| TC-AVL-LIVE-01 | INV-AVL-LIVE-1 | AVL `Approved`, `valid_to = hôm nay − 1d` (chưa flip Expired); Decision winner = supplier đó | `before_submit_decision` / submit | RAISE `ServiceError(BUSINESS_RULE)` VR-03-05. **Code cũ: RED (không raise).** |
| TC-AVL-LIVE-02a | INV-AVL-LIVE-2 | AVL `Approved`, `valid_to = hôm nay − 1d` | `_is_supplier_in_avl(sup, cat)` | trả `0`. **Code cũ: RED (trả 1).** |
| TC-AVL-LIVE-02b | INV-AVL-LIVE-2 | AVL `Approved`, `valid_to = hôm nay + 30d` | `_is_supplier_in_avl` | trả `1` |
| TC-AVL-LIVE-02c | INV-AVL-LIVE-2 | AVL `Approved`, `valid_to = NULL` (vô thời hạn) | `_is_supplier_in_avl` | trả `1` |
| TC-AVL-LIVE-03 | INV-AVL-LIVE-3 | Bộ AVL hỗn hợp (live / hết hạn / NULL / Suspended) | so tập supplier eligible (`_avl_is_live`) vs tập 'active' của `_sync_supplier_avl_status` | hai tập **bằng nhau** (parity) |
| TC-AVL-LIVE-04 | INV-AVL-LIVE-4 | AVL `Approved`, `valid_to == hôm nay` | `_is_supplier_in_avl` + `_vr05` | ELIGIBLE (`>=` inclusive) — submit PASS; đồng thời `check_avl_expiry` (dùng `<`) KHÔNG flip Expired hôm nay |
| TC-AVL-LIVE-05 | INV-AVL-LIVE-5 | AVL `Approved`, `valid_to` tương lai | submit Decision happy-path | eligible=1, submit PASS như cũ (no-regression) |
| TC-AVL-LIVE-06 | INV-AVL-LIVE-6 | (AST/query-guard) | đếm truy vấn của `_avl_is_live` | đúng 1 `db.exists`/`get_value`/`sql`; KHÔNG loop Python; KHÔNG có patch thêm field `valid_to` (đã tồn tại) |

> RED-prove bắt buộc: revert thân `_is_supplier_in_avl`/`_vr05` về "chỉ workflow_state" → TC-AVL-LIVE-01/02a/03 FAIL; restore `_avl_is_live` → GREEN. `test_imm03` (28→≥34) + `test_workflows` + `test_dashboard` GREEN, no leak.

### III.2.y — TestComputeEvalScores (tie-break) — Decision Table & invariance (spec vòng 26)

Cổng tie-break INV-VE-TIE (02 §IV.7). **Viết test TRƯỚC, RED-prove trên code cũ** (cũ luôn gán `recommended_candidate = cands_sorted[0].supplier` khi điểm > 0 ⇒ auto-award first-row khi hòa). Dùng harness `SimpleNamespace` hiện có (`_make_eval_doc`/`_make_candidate`/`_make_criterion`) — KHÔNG cần DB; ca audit-on-submit (TC-35) cần DB nên xếp Integration §III.3.

| TC | Invariant | Setup (criteria 1 nhóm Technical 100% weight) | Action | Assert |
|---|---|---|---|---|
| TC-32 | INV-VE-TIE-2/3/5 | 2 candidate SUP-A, SUP-B cùng `scores={"Tech":0.8}` → cùng `weighted_score` (|Δ|≤1e-9) | `_compute_eval_scores(doc)` | `recommended_candidate is None`; `has_top_tie == 1`; `tied_candidates == "SUP-A,SUP-B"` (sorted); KHÔNG raise. **Code cũ: RED (recommended=SUP-A).** |
| TC-33 | INV-VE-TIE-5 | Như TC-32 nhưng đảo thứ tự row đầu vào (SUP-B trước SUP-A) | `_compute_eval_scores(doc)` | Kết quả y hệt TC-32 (`recommended None`, `tied_candidates == "SUP-A,SUP-B"`) — bất biến theo thứ tự nhập. **Code cũ: RED (recommended=SUP-B).** |
| TC-34 | INV-VE-TIE-4 | 2 candidate, mọi `scores={"Tech":0}` ⇒ `weighted_score ≤ 0` | `_compute_eval_scores(doc)` | `recommended_candidate is None`; `has_top_tie == 0`; `tied_candidates in (None, "")`. Giữ hành vi cũ. |
| (giữ) `test_higher_score_candidate_wins` | INV-VE-TIE-1/6 | SUP-A 0.9 vs SUP-B 0.5 | `_compute_eval_scores(doc)` | `recommended_candidate == "SUP-A"`; `has_top_tie == 0`. KHÔNG hồi quy. |
| (giữ) `test_empty_candidates_no_recommended` | INV-VE-TIE-4 | candidates=[] | `_compute_eval_scores(doc)` | `recommended_candidate is None`; `has_top_tie == 0`. KHÔNG hồi quy. |
| TC-35 (DB, §III.3) | INV-VE-TIE-3 | VE thật có `has_top_tie=1` | `doc.submit()` → `on_submit_evaluation` | đúng **1** IMM Audit Trail row `change_summary LIKE 'eval_tie_unresolved%'` (idempotent khi save/submit lặp) + logger `imm03` có dòng `eval_tie_unresolved`. |

> **Harness note:** `_make_eval_doc` (line 91-93) phải thêm `name="VE-TEST"` + khởi tạo `has_top_tie=0`, `tied_candidates=""` vào `SimpleNamespace` để assert field mới (hiện chỉ có `recommended_candidate=None`). `_make_candidate` đã có `weighted_score`.
>
> **RED-prove bắt buộc:** chạy TC-32/33 trên code cũ → FAIL (recommended = first/second row). Áp patch `_compute_eval_scores` (tie-detect) → GREEN. `bench --site miyano run-tests --module assetcore.tests.test_imm03` PASS toàn bộ (3 tie mới + 3 cũ `TestComputeEvalScores` + phần còn lại), no leak.

### III.2.z — TestDecisionDrillParity — INVARIANT card==drill (spec INV-DEC-DRILL, 02 §IV.8)

Bảo toàn INVARIANT **count tile == total list** cho 3 state decision. **Viết test TRƯỚC, RED-prove trên code cũ** (cũ: `_list_decisions` không loại `docstatus=2` → list đếm dư bản huỷ so với tile). Cần DB (seed `IMM Procurement Decision` thật) → xếp tại file `tests/test_imm03.py` lớp DB hoặc `test_imm03_decision_drill.py`. Predicate SoT: `docstatus<2 AND workflow_state = S`. Teardown phải purge mọi PD seed (theo `tests/_asset_cleanup.py` pattern, tránh leak DB chung).

| TC | Invariant | Setup | Action | Assert |
|---|---|---|---|---|
| TC-DEC-DRILL-01 | INV-DEC-DRILL-1 | Seed ≥1 PD ở mỗi state {Awarded, Pending Approval, PO Issued} (docstatus 0/1) | `_dashboard_kpis()` + `_list_decisions({'workflow_state': S}, 1, 100)` cho từng S | `decision_states.get(S,0) == list['total']` cho cả 3 S |
| TC-DEC-DRILL-02 | INV-DEC-DRILL-2 | Như 01 + thêm 1 PD `docstatus=2` mang `workflow_state='Awarded'` | so tile Awarded & total list Awarded trước/sau khi thêm bản huỷ | cả tile lẫn total **KHÔNG đổi** (loại cancelled). **Code cũ: RED — total list +1.** |
| TC-DEC-DRILL-03 | INV-DEC-DRILL-3 | Bộ PD hỗn hợp docstatus 0/1/2 | đếm trực tiếp predicate | cả `_dashboard_kpis` lẫn `_list_decisions` chỉ đếm `docstatus ∈ {0,1}`; không nhánh nào đếm `docstatus=2` |
| TC-DEC-DRILL-04 | INV-DEC-DRILL-4 | KHÔNG seed PD nào ở state `PO Issued` | tile `PO Issued` + `_list_decisions({'workflow_state':'PO Issued'})` | tile=0 và `total==0`; `items==[]`; KHÔNG raise |
| TC-DEC-DRILL-05 | INV-DEC-DRILL-5 | Seed PD + 1 PD `docstatus=2` | `_list_decisions({'docstatus': 2})` (override tường minh) | trả đúng các bản huỷ (override mặc định `docstatus<2`); field/search/enrich/pagination không đổi so với baseline |
| TC-DEC-DRILL-06 (vitest) | INV-DEC-DRILL-6 | mount `DecisionListView` (mock store real-refs) | click tile `Đã trao thầu`/`Chờ phê duyệt`/`Đã phát hành đơn hàng` | gọi `quickFilter('workflow_state', S)` với S = `Awarded`/`Pending Approval`/`PO Issued` (canonical) |
| TC-DEC-DRILL-07 (vitest) | INV-DEC-DRILL-7 | tile active (filter trùng) | click tile active lần 2 / click "Xóa tất cả" | `filters.workflow_state` về `''`; `aria-pressed`/active class off; list về full; không kẹt |
| TC-DEC-DRILL-08 (vitest/tsc) | INV-DEC-DRILL-8 | render badge các state | grep EN-leak + vue-tsc | `StatusBadge`/`stateLabel` phủ đủ `DECISION_STATES`; 0 nhãn EN; vue-tsc 0 lỗi |

> **RED-prove bắt buộc:** TC-DEC-DRILL-02 chạy trên code cũ → FAIL (total list Awarded = tile + #cancelled). Áp patch `_list_decisions` (bơm `docstatus<2` mặc định) → GREEN. `bench --site miyano run-tests --module assetcore.tests.test_imm03` GREEN + `vitest` FE GREEN, no leak. KHÔNG sửa hành vi BE list/kpis ngoài việc đồng nhất predicate.

## III.3. Integration — DocType lifecycle

⬜ Planned. File dự kiến `tests/test_imm_procurement_decision_doctype.py` — cover hook `validate / before_submit_decision / on_submit_decision / on_cancel_decision`.

| Test | Setup | Action | Assert | Kỹ thuật |
|---|---|---|---|---|
| Decision on_submit mint PO | Eval Evaluated + Plan Line | `doc.submit()` (state Awarded) | AC Purchase tạo, Plan Line `status=Awarded` | EP |
| Eval on_submit tie audit (TC-35) | VE có 2 candidate hòa đỉnh (`has_top_tie=1`) | `doc.submit()` → `on_submit_evaluation` | đúng 1 IMM Audit Trail `change_summary LIKE 'eval_tie_unresolved%'`, `event_type='System'`, `ref_name=doc.name`; submit lặp/amend KHÔNG nhân đôi (idempotent) | EP + idempotency |
| Decision on_cancel | Decision Awarded | `doc.cancel()` | rollback Plan Line | EP |
| AVL activate sync supplier | AVL Approved | `activate_avl` | `AC Supplier.imm_avl_status` update | EP |

## III.4. Integration — Workflow transitions

⬜ Planned. **Bắt buộc** cover 100% transition. Đếm (ground truth):
- Vendor Eval: `imm_03_vendor_eval_workflow.json` → **6 transition**
- Procurement Decision: `imm_03_decision_workflow.json` → **8 transition**
- AVL: `imm_03_avl_workflow.json` → **7 transition**
- **Tổng = 21 transition**

### Vendor Evaluation (6)
| Transition (action) | From → To | Role required | Test pass | Test fail |
|---|---|---|---|---|
| Mở RFQ | Draft → Open RFQ | Procurement Manager | ⬜ | ⬜ |
| Nhận báo giá xong | Open RFQ → Quotation Received | Procurement Manager | ⬜ | ⬜ |
| Hoàn tất chấm điểm | Quotation Received → Evaluated | Procurement Manager | ⬜ | ⬜ |
| Hoàn tất chấm điểm | Quotation Received → Evaluated | Commissioning Manager | ⬜ | ⬜ |
| Huỷ Eval | Open RFQ → Cancelled | Commissioning Manager | ⬜ | ⬜ |
| Huỷ Eval | Quotation Received → Cancelled | Commissioning Manager | ⬜ | ⬜ |

### Procurement Decision (8)
| Transition (action) | From → To | Role required | Test pass | Test fail |
|---|---|---|---|---|
| Chọn phương án | Draft → Method Selected | Procurement Manager | ⬜ | ⬜ (G04 fail) |
| Bắt đầu thương thảo | Method Selected → Negotiation | Procurement Manager | ⬜ | ⬜ |
| Đề xuất trúng thầu | Negotiation → Award Recommended | Procurement Manager | ⬜ | ⬜ |
| Trình BGĐ | Award Recommended → Pending Approval | Commissioning Manager | ⬜ | ⬜ |
| Phê duyệt trúng thầu | Pending Approval → Awarded | Procurement Manager | ⬜ | ⬜ (G05 fail) |
| Huỷ Decision | Pending Approval → Cancelled | Procurement Manager | ⬜ | ⬜ |
| Ký HĐ | Awarded → Contract Signed | Needs Manager | ⬜ | ⬜ |
| Phát hành PO | Contract Signed → PO Issued | Procurement Manager | ⬜ | ⬜ |

### AVL Entry (7)
| Transition (action) | From → To | Role required | Test pass | Test fail |
|---|---|---|---|---|
| Phê duyệt AVL | Draft → Approved | Procurement Manager | ⬜ | ⬜ |
| Cấp Conditional | Draft → Conditional | Spec Manager | ⬜ | ⬜ |
| Hạ xuống Conditional | Approved → Conditional | Spec Manager | ⬜ | ⬜ |
| Đình chỉ | Approved → Suspended | Spec Manager | ⬜ | ⬜ |
| Phục hồi Approved | Conditional → Approved | Procurement Manager | ⬜ | ⬜ |
| Đình chỉ | Conditional → Suspended | Spec Manager | ⬜ | ⬜ |
| Phục hồi Approved | Suspended → Approved | Procurement Manager | ⬜ | ⬜ |

> Lưu ý invalid-transition cần test: Evaluated → Open RFQ (terminal), Awarded → Cancelled (terminal positive), Expired là terminal (set bởi scheduler `check_avl_expiry`, không có transition action).

**Kỹ thuật**: State Transition Testing — mỗi edge = 1 test pass + 1 test fail (wrong role / gate fail).

## III.5. Integration — Audit chain integrity

⬜ Planned. 2 test chính:
- (a) Sau N mutation (Award → Contract Signed → PO Issued), `IMM Audit Trail` chain hợp lệ end-to-end, actor = `frappe.session.user`.
- (b) Khi 1 entry bị tamper, verify endpoint trả `chain_broken=true`.

*(→ 04 Backend §Audit Trail · `IMM Audit Trail` DocType. VR-03-06: V1 KHÔNG hard-enforce trong service IMM-03 — dựa vào permlevel của `IMM Audit Trail` chung hệ thống.)*

## III.6. API test

⬜ Planned. File dự kiến `tests/test_imm03_api.py`. **22 endpoint** (ground truth `api/imm03.py`); envelope chung `{success, data}` / `{success:false, code}` qua `_handle`/`_err` (`frappe.PermissionError → FORBIDDEN`).

| # | Endpoint (verb) | Verify | Kỹ thuật |
|---|---|---|---|
| 1 | `list_vendor_profiles` (GET) | `success=true`, pagination | Use Case + BVA (page) |
| 2 | `get_vendor_profile` (GET) | certs + AVL + scorecard history | Use Case |
| 3 | `create_vendor_profile` (POST) | upsert AC Supplier extension | Use Case |
| 4 | `add_vendor_cert` (POST) | cert status Active/Expiring | EP |
| 5 | `list_evaluations` (GET) | pagination | Use Case |
| 6 | `create_evaluation` (POST) | VE Draft + weighting JSON | Use Case |
| 7 | `add_candidate` (POST) | `in_avl` flag + warning non-AVL | EP |
| 8 | `submit_quotations` (POST) | VR-03-03 khi state ≥ Quotation Received | BVA |
| 9 | `score_evaluation` (POST) | weighted compute; wrong scorer_role → FORBIDDEN | EP (permission) |
| 10 | `list_avl` (GET) | filter | Use Case |
| 11 | `create_avl_entry` (POST) | status Draft | Use Case |
| 12 | `approve_avl` (POST) | role Procurement Manager | EP (permission) |
| 13 | `suspend_avl` (POST) | reason bắt buộc | EP |
| 14 | `get_evaluation` (GET) | detail | Use Case |
| 15 | `get_decision` (GET) | detail | Use Case |
| 16 | `get_avl` (GET) | detail | Use Case |
| 17 | `list_decisions` (GET) | pagination | Use Case |
| 18 | `transition_eval_workflow` (POST) | state change + role gate | State Transition |
| 19 | `transition_decision_workflow` (POST) | state change + gate | State Transition |
| 20 | `create_decision` (POST) | từ evaluation_ref + method | Use Case |
| 21 | `award_decision` (POST) | mint PO; non-Manager → FORBIDDEN | Use Case + EP |
| 22 | `record_contract` (POST) | contract_no + signed_date | Use Case |
| 23 | `get_vendor_scorecard` (GET) | KPI rows | Use Case |
| 24 | `dashboard_kpis` (GET) | 7 KPI keys (→ 02 §I.5) | Use Case |

> Note: API layer hiện không gọi `rbac.require()` tường minh — quyền dựa vào DocPerm + `frappe.PermissionError`. Test FORBIDDEN phải chạy bằng user role thấp thật (xem VI.2 gap).

## III.7. E2E browser (Playwright)

⬜ Planned. Dùng cho flow UI khó cover bằng API: dropdown AVL cascade khi add candidate, modal confirm Award, workflow button visibility theo role, mask field permlevel-1 (`awarded_price`).

*(→ `assetcore-test` skill Phần 2 — Playwright MCP recipes + R-1..R-9 data rules)*

## III.8. Performance test

⬜ Planned (chưa chạy). Tool **k6** / `pytest-benchmark`. Target lấy từ 02 §V.1.

| Metric | Target | Method |
|---|---|---|
| `list_vendor_profiles` (5000 vendor) P95 | < 2s | k6 GET |
| Mint AC Purchase khi Award | < 3s | `time bench execute` |
| `dashboard_kpis` 7 chỉ số | < 2s | k6 GET |
| `score_evaluation` compute | < 1s | `pytest-benchmark` |

## III.9. Test data & Fixtures

| Loại | Cách seed | File |
|---|---|---|
| Master (AC Supplier, custom fields) | Patch `v3_1.003_install_imm03` + `fixtures/*.json` | `assetcore/fixtures/` |
| Workflow + Role | `fixtures` (cài qua `bench migrate`) | `assetcore/assetcore/workflow/imm_03_*.json` |
| Test records | `SimpleNamespace` inline (unit) / `test_records.json` (Planned integration) | `test_imm03.py` |
| UAT seed | Python script (Planned) | `assetcore/scripts/uat/uat_imm03.py` *(Cần khảo sát — chưa tồn tại)* |

> UAT data thực tế: vendor VINAMED / HAMILTON-VN / MINDRAY-VN / DRAGER-VN; spec TS-26-00045; plan PP-26-001 allocated_budget = 2.5 tỷ. Backend fixture mới dùng prefix `_Test` (xem `assetcore-test` R-0/R-1; `test_imm03.py` đã dùng `_Test-PD-001`).

## III.10. Run commands & Coverage gate

```bash
# Module test
bench --site [site] run-tests --app assetcore --module assetcore.tests.test_imm03
# Coverage
coverage run -m unittest assetcore.tests.test_imm03 && coverage report
# Run riêng 1 class
bench --site [site] run-tests --module assetcore.tests.test_imm03.TestGateG04Method
```

| Layer | Target coverage | Đo |
|---|---|---|
| Service (`services/imm03.py`) | ≥ 85% line + ≥ 80% branch (target) | `coverage --branch` |
| DocType lifecycle | ≥ 70% (target) | `coverage report` |
| API (`api/imm03.py`) | ≥ 60% (target) | `coverage report` |
| Frontend (vue-tsc) | 0 error | `npm run build` |

> Coverage % thực tế: *(Cần khảo sát — chưa có report sinh ra)*. Chỉ ghi target.

---

# Phần IV — Traceability Matrices

> Mọi test ở Phần III phải xuất hiện ở cả 3 bảng.

## IV.1. US → Test mapping

| US ID | AC | Test ID (III.x) | Layer | Status |
|---|---|---|---|---|
| US-03-001 | AC-1/AC-2 cert status | `add_vendor_cert` API test (III.6 #4) | API/Integration | ⬜ Planned |
| US-03-021 | AC-1 in_avl | `add_candidate` API test (III.6 #7) | API | ⬜ Planned |
| US-03-021 | AC-2 non-AVL block submit | `TestImm03ValidationRules::vr02` (III.2) | Unit | ⬜ Planned |
| US-03-032 | AC-1 mint PO | Decision on_submit (III.3) | Integration | ⬜ Planned |
| US-03-032 | AC-2 PO TBYT direct block | `validate_ac_purchase_imm_link` test (III.6) | Integration | ⬜ Planned |

## IV.2. BR → Test mapping

| BR ID | Phát biểu (rút gọn) | Test ID | Kỹ thuật | Happy / Negative |
|---|---|---|---|---|
| BR-03-01 / VR-03-07 | 1 spec ↔ 1 Decision Awarded | `TestImm03ValidationRules::vr07` | EP | ⬜ / ⬜ Planned |
| BR-03-02 / VR-03-01 | Min candidates | `TestImm03ValidationRules::vr01` | EP | ⬜ / ⬜ Planned |
| BR-03-03 / VR-03-02 | Non-AVL sign-off | `add_candidate` API test | EP | ⬜ / ⬜ Planned |
| BR-03-04 / VR-03-03 | Quotation hết hạn | `TestImm03ValidationRules::vr03` | BVA | ⬜ / ⬜ Planned |
| BR-03-05 / VR-03-04 | >105% envelope | `TestImm03ValidationRules::vr04` | BVA | ⬜ / ⬜ Planned |
| BR-03-06 / G04 | Method hợp pháp | `TestGateG04Method` (6 case) | Decision Table | 2 ✅ / 4 ✅ Live |
| BR-03-07 / VR-03-05 | Winner có AVL | `TestImm03ValidationRules::vr05` | Decision Table | ⬜ / ⬜ Planned |
| BR-03-08 / VR-03-08 | PO TBYT link Decision | `validate_ac_purchase_imm_link` test | EP | ⬜ / ⬜ Planned |

> Note: BR-03-06/G04 là BR Critical (I.3) đã có Decision Table đầy đủ ở `TestGateG04Method` (Live). Các BR Critical khác (VR-03-04, VR-03-05) còn Planned.

## IV.3. Component → Test mapping

| Component (I.1) | Test ID | Test layer | Coverage % | Risk priority (I.3) |
|---|---|---|---|---|
| `_validate_gate_g04_method` (#16) | `TestGateG04Method` + `TestMethodRules` | Unit | *(Cần khảo sát)* | Critical ✅ Live |
| `_compute_eval_scores` (#9) | `TestComputeEvalScores` | Unit | *(Cần khảo sát)* | Medium ✅ Live |
| `_parse_weighting`/`_parse_json_field` (#10) | `TestParseWeighting`/`TestParseJsonField` | Unit | *(Cần khảo sát)* | Low ✅ Live |
| `set_actual_delivery_on_received` (#22) | `TestActualDeliveryDefault` | Unit | *(Cần khảo sát)* | Low ✅ Live |
| `validate_receipt_against_po` (#22) | `TestReceiptAgainstPO` | Unit + Integration | *(Cần khảo sát)* | Medium ✅ Live |
| `_vr04_envelope_check` (#13) | Planned | Unit | — | Critical ⬜ Planned |
| `_vr05_winner_avl_required` (#14) | Planned | Unit | — | High ⬜ Planned |
| `_validate_gate_g05` (#17) | Planned | Unit | — | Critical ⬜ Planned |
| `award_decision`/`_mint_ac_purchase` (#18) | Planned | Integration | — | Critical ⬜ Planned |
| Decision workflow (#7) | Planned | Integration | — | High ⬜ Planned |

> ⚠️ Gap nghiêm trọng: các component **Critical** `_vr04_envelope_check`, `_validate_gate_g05`, `award_decision`/`_mint_ac_purchase` chưa có test Live → chưa đạt coverage target III.10.

---

# Phần V — UAT Script

## V.1. Phạm vi UAT

- **In-scope**: scenario theo US (V.4) — Vendor Profile extension, AVL lifecycle + auto-expiry, Vendor Evaluation scoring đa tiêu chí, Procurement Decision 9 state, Award → mint AC Purchase, Vendor Scorecard quarterly, Supplier Audit + CAPA.
- **Out-of-scope**: performance (III.8), security (Phần VI).
- **Pre-condition**: site UAT deploy version Wave 2; fixture (workflow + role + custom fields) loaded; tester accounts active.

## V.2. Tester accounts

> ⚠️ Role ground truth của module (DocPerm + workflow JSON): **AssetCore Super Admin, Procurement Manager, Procurement User, AssetCore Auditor, AssetCore System User** + role workflow **Spec Manager, Commissioning Manager, Needs Manager**. Bảng dưới ánh xạ persona nghiệp vụ (02 §I.3) → role thật; account UAT cần tạo theo role thật, không theo tên persona.

| Username | Role thật | Persona nghiệp vụ (02) | Vai trò UAT |
|---|---|---|---|
| `procurement.mgr@test.vn` | Procurement Manager | ĐT-HĐ-NCC / VP Block1 | Tạo/approve AVL, evaluation, decision, award |
| `procurement.user@test.vn` | Procurement User | ĐT-HĐ-NCC Officer | Tạo vendor/eval/decision (không submit) |
| `spec.mgr@test.vn` | Spec Manager | QA Risk / Spec | Cấp/đình chỉ AVL Conditional/Suspended |
| `commissioning.mgr@test.vn` | Commissioning Manager | PTP Khối 1 | Trình BGĐ; huỷ eval |
| `needs.mgr@test.vn` | Needs Manager | TCKT | Ký Contract Signed |
| `auditor@test.vn` | AssetCore Auditor | Kiểm toán nội bộ | Read-only verify (cover FORBIDDEN) |
| `sysuser@test.vn` | AssetCore System User | Người dùng thường | Read-only (cover Info Disclosure) |
| `admin@test.vn` | AssetCore Super Admin | CMMS Admin | Override |

## V.3. Test data đã seed

| DocType | Số lượng | Ghi chú |
|---|---|---|
| AC Supplier | 4 | VINAMED, HAMILTON-VN, MINDRAY-VN, DRAGER-VN (đã tạo trong ERPNext) |
| IMM AVL Entry | ≥ 3 | ≥ 2 Approved + 1 Conditional cho category Imaging |
| IMM Tech Spec | 1 | TS-26-00045 (Locked, plan_line=line001) |
| IMM Procurement Plan | 1 | PP-26-001, allocated_budget = 2.5 tỷ |
| IMM Vendor Evaluation | 1 | VE-26-00120 seed |

## V.4. UAT Scenarios — Suy ra từ US + Activity

ID `UAT-IMM03-NN` (template §Phụ lục A). Migrate từ bảng UAT Wave 2 hiện có.

| ID | Actor (role thật) | Pre-condition | US/BR cover | Kỹ thuật | Kết quả mong đợi |
|---|---|---|---|---|---|
| UAT-IMM03-01 | Procurement Manager | Supplier VINAMED tồn tại | US-03-001 AC-1 | Use Case happy | Profile saved, cert ISO 9001 Active |
| UAT-IMM03-02 | Procurement Manager | AVL Draft VINAMED/Imaging | US-03-001 | State Transition | Status Approved, valid_to auto |
| UAT-IMM03-03 | Scheduler | AVL valid_to < today | BR-03 expiry | Use Case alt | status=Expired, email cảnh báo |
| UAT-IMM03-04 | Procurement User | Spec TS-26-00045 Locked | UC-IMM03-01 | Use Case happy | VE-26-00120 Draft tạo |
| UAT-IMM03-05 | Procurement User | VE Draft | US-03-021 AC-1/AC-2 | EP | in_avl flags đúng, warning non-AVL |
| UAT-IMM03-06 | Procurement Manager | VE Open RFQ | UC-IMM03-01 b4 | State Transition | state Quotation Received |
| UAT-IMM03-07 | Mixed (Manager + Spec Mgr) | VE Quotation Received | UC-IMM03-01 b5 | Use Case | weighted_score compute, recommended set |
| UAT-IMM03-08 | Procurement Manager | VE Evaluated | BR-03-06 G04 | Decision Table | state Method Selected (Đấu thầu rộng rãi OK) |
| UAT-IMM03-09 | Procurement Manager | Decision Pending Approval, G05 pass | US-03-032 AC-1 | Use Case happy | docstatus=1, AC Purchase mint, Plan Line Awarded, event publish |
| UAT-IMM03-10 | Procurement User | item TBYT, no decision link | US-03-032 AC-2 / VR-03-08 | EP negative | VR-03-08 warning/block |
| UAT-IMM03-11 | Scheduler | KPI source data | BR-03 scorecard | Use Case | VS-2026-Q2-VINAMED idempotent |
| UAT-IMM03-12 | Spec Manager | Supplier Audit Critical finding | E-03-07 | State Transition | AVL Suspended, email approver |

**Quy tắc suy scenarios**: mỗi US ≥ 1 happy (01,04,09); mỗi Activity branch ngoại lệ ≥ 1 (03,10,12); mỗi role mutate ≥ 1 permission verify (cần thêm scenario FORBIDDEN cho Auditor/System User — xem gap VI.2); mỗi workflow terminal transition ≥ 1 audit verify (09); BR Critical negative (08,10).

## V.5. Tổng hợp kết quả & Bug found

| Scenario | Status | Tester | Ngày | Ghi chú |
|---|---|---|---|---|
| UAT-IMM03-01..12 | ☐ Pending | | | Chưa chạy UAT site |

**Bug list**: *(Cần khảo sát — chưa có phiên UAT chính thức)*

**Acceptance**: ≥ 95% PASS, Blocker = 0, Major ≤ 2 (có workaround); PO mint 100% thành công với decision hợp lệ.

**Sign-off**:

| Vai trò | Người | Ngày | Chữ ký |
|---|---|---|---|
| BA Lead | | | |
| QA Lead | | | |
| Module Owner (PTP Khối 1) | | | |

---

# Phần VI — Security Review (gate)

## VI.1. RBAC

**Role definitions** (ground truth DocPerm + workflow JSON, KHÔNG phải tên "IMM xxx"):
`AssetCore Super Admin`, `Procurement Manager`, `Procurement User`, `AssetCore Auditor`, `AssetCore System User` (DocPerm) + `Spec Manager`, `Commissioning Manager`, `Needs Manager` (workflow transition).

**DocPerm matrix** (ground truth — 3 DocType chính có cùng 5 role rows, permlevel 0):

| DocType | Role | Read | Write | Create | Submit | Cancel | Delete |
|---|---|---|---|---|---|---|---|
| IMM Vendor Evaluation / Decision / AVL Entry | AssetCore Super Admin | Y | Y | Y | Y | Y | Y |
| (cùng 3 DocType) | Procurement Manager | Y | Y | Y | Y | Y | Y |
| (cùng 3 DocType) | Procurement User | Y | Y | Y | N | N | N |
| (cùng 3 DocType) | AssetCore Auditor | Y | N | N | N | N | N |
| (cùng 3 DocType) | AssetCore System User | Y | N | N | N | N | N |

**Field-level permission** (`IMM Procurement Decision` — permlevel 1 trong field JSON): `winner_supplier`, `awarded_price`, `envelope_check_pct`, `funding_source`, `funding_evidence`, `board_approver`, `contract_doc` (+ section `section_winner`, `section_funding`).

> ⚠️ **Gap thật**: field có `permlevel=1` nhưng DocPerm JSON của `IMM Procurement Decision` **chỉ có permlevel-0 rows** — KHÔNG có DocPerm row permlevel 1 cấp Read cho role nào. Hệ quả: field nhạy cảm hiện ẩn với mọi role (kể cả Manager) trừ khi có default. Cần bổ sung DocPerm permlevel-1 Read cho Procurement Manager / Super Admin trước go-live.

**User Permission**: *(Cần khảo sát — chưa thấy `permission_query_conditions` cho IMM-03 trong hooks.py)*.

**Kỹ thuật**: Decision Table — mỗi (role × action × state) = 1 row, expected Allow/Deny.

## VI.2. API security

- **Whitelist hygiene**: 22 endpoint đều có `@frappe.whitelist()`; POST endpoint khai `methods=["POST"]`; có docstring `Docs §x.y`. Mutating dùng `_handle` envelope.
- **CSRF**: Frappe default `X-Frappe-CSRF-Token` (POST endpoint).
- **Input validation**: payload JSON parse qua `_parse_json_field`/`_parse_weighting`; Link field (spec_ref, supplier) resolve qua `frappe.get_doc`.
- **SQL injection**: dùng `frappe.db.count` / ORM; *(Cần khảo sát raw SQL nếu có)*.
- **Permission boundary**: API KHÔNG gọi `rbac.require()` tường minh — chỉ map `frappe.PermissionError → FORBIDDEN` (`api/imm03.py:40-41`). ⚠️ Gap: `score_evaluation(scorer_role=...)` nhận role từ payload FE — phải validate khớp role của `frappe.session.user` ở service layer (xem VI.9 Spoofing). Cần test FORBIDDEN bằng user role thấp thật.
- **Rate limit**: *(Cần khảo sát — chưa cấu hình cho create/award)*.

## VI.3. Audit trail integrity

- Mọi state transition kỳ vọng sinh `IMM Audit Trail` (actor = `frappe.session.user`); `award_decision` ghi event Awarded + PO Created.
- VR-03-06 (02 §IV.3): **V1 KHÔNG hard-enforce trong service IMM-03** — bất biến dựa vào permlevel/`on_trash` guard của `IMM Audit Trail` DocType chung hệ thống (ISO 13485:7.5.9).
- Test tamper (intact + tampered) → III.5 (⬜ Planned).

## VI.4. Authentication & session

Login Frappe default + API token; session timeout, lockout, password policy theo cấu hình site. API key rotation theo `frappe.conf`. 2FA: roadmap.

## VI.5. Data sensitivity

| Loại | Trường | Sensitivity | Bảo vệ |
|---|---|---|---|
| Tài chính | `awarded_price`, `envelope_check_pct`, `funding_source`, `funding_evidence` | Confidential | permlevel 1 (⚠️ cần DocPerm row — VI.1) |
| Pháp lý | `contract_doc` | Confidential | permlevel 1 + private file |
| Phê duyệt | `board_approver`, `winner_supplier` | Internal | permlevel 1 |
| Chấm điểm | `scores`, `weighted_score` | Internal | permlevel 0 |

KHÔNG lưu patient/clinical data.

## VI.6. Vendor isolation

IMM-03 chưa expose vendor-external portal trong Wave 2 (vendor là master AC Supplier, không có login external). Nếu mở: vendor chỉ thấy WO/decision assigned qua `permission_query_conditions`; KHÔNG thấy chi phí, internal note, audit trail vendor khác. *(Cần khảo sát — V1 không có permission_query_conditions cho IMM-03)*.

## VI.7. Secrets management

Cấm commit `.env`/credential; `site_config.json` không lên git; external token lưu `frappe.conf`; backup encrypt at-rest off-site.

## VI.8. Logging & monitoring

| Sự kiện | Log level | Where | Alert? |
|---|---|---|---|
| Award decision | INFO | frappe log + IMM Audit Trail | — |
| Mint AC Purchase fail (E-03-08) | ERROR | frappe error log | Alert System Admin |
| Scheduler run (`check_avl_expiry`, `update_vendor_scorecard`) | INFO | scheduler log | Alert on missed run |

PII/token KHÔNG vào log; `awarded_price`/`funding_source` không log rõ ràng (02 §V.2).

## VI.9. Threat model (STRIDE-lite)

| Threat | Vector | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| **Spoofing** | FE gửi `scorer_role` giả để chấm nhóm không có quyền (`score_evaluation`) | Medium | High | BE phải validate role của `frappe.session.user` — không tin FE payload (⚠️ cần kiểm chứng đã enforce) |
| **Tampering** | Sửa `awarded_price` sau submit Decision | Medium | High | `docstatus=1` read-only; permlevel 1 (cần DocPerm row VI.1) |
| **Repudiation** | Phủ nhận đã Award | Low | High | IMM Audit Trail bất biến: actor + timestamp + from→to state |
| **Information Disclosure** | User thường xem giá trúng thầu | Medium | High | permlevel 1 + FE mask `***` |
| **Denial of Service** | Scorecard quarterly query nặng toàn bộ vendor | Low | Medium | Scheduler background job, không blocking; rate limit (cần cấu hình) |
| **Elevation of Privilege** | Non-Manager gọi `award_decision`/`submit` Decision | Medium | High | DocPerm submit chỉ Procurement Manager/Super Admin; `PermissionError → FORBIDDEN` |

## VI.10. Penetration test

⬜ Planned (trước release đầu tiên): Burp/ZAP scan, sqlmap (an toàn), CSRF test, role escalation. Report lưu `docs/security/`.

## VI.11. Sign-off

| Role | Người | Ngày | Chữ ký |
|---|---|---|---|
| Security Officer | | | |
| QA Lead | | | |
| Module Owner | | | |

Decision: ☐ Pass / ☐ Pass with conditions / ☐ Fail (block). *(Hiện: có gap permlevel DocPerm + scorer_role validation cần đóng trước go-live.)*

---

# Phần VII — Code Quality

## VII.1. Tool matrix

| Tool | Mục tiêu | Target | Cadence |
|---|---|---|---|
| **SonarQube** (BE Python) | bug / smell / duplication / coverage | 0 critical bug, smell ≤ N, duplication ≤ 3%, coverage ≥ 70%, security hotspot review 100% | mỗi PR (CI gate) |
| **ruff / black** (BE) | lint + format | 0 error, format consistent | mỗi PR |
| **ESLint + vue-tsc** (FE) | type + lint | 0 error, 0 warning prod build | mỗi PR |
| **Lighthouse** (FE views procurement) | Perf/A11y/BP/SEO | Perf ≥ 90, A11y ≥ 95, BP ≥ 90, SEO ≥ 80 | release lớn + monthly |
| **Bundle size** (chunk imm03) | budget | main ≤ 250KB gzip, async ≤ 80KB gzip | mỗi PR FE |

> Đối chiếu giới hạn dự án: function ≤ 50 LOC, file ≤ 200 LOC, cyclomatic ≤ 10, type hints 100% + docstring 100% public (CLAUDE.md §15). Số thực tế SonarQube/Lighthouse: *(Cần khảo sát — chưa có report)*.

## VII.2. Cadence

- SonarQube: mỗi PR (CI gate, fail nếu Quality Gate fail).
- Lighthouse: mỗi release lớn + monthly audit.
- ESLint / ruff: mỗi PR (CI gate).
- Bundle size: mỗi PR FE (CI report, fail nếu vượt budget).
- Screenshot SonarQube + Lighthouse gắn vào `09_Release.md` §Release Notes khi báo cáo final.

---

# Phụ lục A — Template per UAT scenario

```markdown
### UAT-IMM-03-<NN> — <Tên>

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
### TC-IMM-03-<LAYER>-<NN> — <Tên>

**Component (I.1)**: <…>
**Liên kết**: US-<NN> | BR-<NN> | ACT-<NN>
**Kỹ thuật (II.1/II.2)**: BVA boundary `awarded_price = 105% envelope`
**Priority (I.3)**: Critical / High / Medium / Low
**Test type**: Unit / Integration / API / E2E
**Pre-condition**: <fixture / state setup>

**Input**:
- <field>: <value>

**Steps**:
1. <…>
2. <…>

**Expected**:
- ServiceError(code=CONFLICT, message contains "VR-03-04")
- doc.workflow_state unchanged

**Post-condition**: <DB rollback / fixture cleanup>
```

# Phụ lục C — Workflow State Transition Test template

```markdown
### TC-IMM-03-WF-<NN> — <action>: <from> → <to>

**Workflow JSON**: `workflow/imm_03_<…>_workflow.json`
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
- [x] I.1 Component Inventory liệt kê đủ artefact (29 dòng, đối chiếu 04/05/06)
- [x] I.2 mỗi US / BR / Activity có ≥ 1 dòng map
- [x] I.3 Risk priority gán cho mọi component (không trống)
- [x] I.4 Scope ghi rõ out-of-scope kèm lý do

## II. Test Design Techniques
- [x] II.1 chọn ≥ 4 black-box techniques (EP + BVA + Decision Table + State Transition + Use Case + Pairwise + Error Guessing)
- [x] II.2 white-box criteria xác định (statement + branch)
- [x] II.3 mapping component → kỹ thuật đầy đủ

## III. Test Plan
- [ ] Test class cho mọi service public function — chỉ 9 class Live; VR-03-04/05, G05, award/mint, scheduler scorecard còn Planned
- [ ] ≥ 1 happy + 1 negative mỗi function — gate G04 đủ; phần lớn VR/integration Planned
- [ ] Workflow transitions cover 100% (21 transition) — liệt kê đủ nhưng test ⬜ Planned
- [ ] Audit chain test (intact + tampered) — Planned (VR-03-06 không hard-enforce ở IMM-03)
- [ ] API test ≥ 60% + permission matrix — Planned
- [ ] Performance target xác định (có target, chưa chạy)
- [x] CI command chạy (`bench run-tests --module assetcore.tests.test_imm03`)
- [ ] SonarQube Quality Gate + Lighthouse — chưa có report

## IV. Traceability
- [x] IV.1 US → Test: mọi US có ≥ 1 Test ID
- [ ] IV.2 BR → Test: mọi BR có happy + negative — chỉ BR-03-06/G04 đủ Live; còn lại Planned
- [ ] IV.3 Component → Test: Critical/High đạt coverage target — `_vr04`, G05, award/mint chưa Live

## V. UAT
- [x] Mỗi US có ≥ 1 UAT scenario
- [ ] ≥ 1 negative + permission + audit verify — thiếu scenario FORBIDDEN cho Auditor/System User
- [ ] Test data seed script chạy được — `uat_imm03.py` chưa tồn tại
- [ ] Tester accounts đã tạo ở UAT site (đủ role thật) — chưa tạo
- [x] Sign-off section sẵn sàng

## VI. Security
- [x] DocPerm matrix đầy đủ — ✅ 2026-07-02 thêm DocPerm permlevel-1 (Super Admin R+W, Procurement Manager R+W, Auditor R). Trước đó thiếu row → `doc.save()` strip câm `awarded_price/funding_source/board_approver`. Xem LL-BE-67.
- [x] Mọi field nhạy cảm có permlevel ≠ 0 — ✅ permlevel-1 field giờ có DocPerm Read+Write row hợp lệ
- [ ] SQL injection + CSRF test pass — Planned
- [ ] Audit chain test pass — Planned
- [ ] Vendor isolation test — chưa có permission_query_conditions
- [x] Threat model đủ 6 STRIDE với mitigation
- [ ] Sign-off đầy đủ trước go-live — còn gap permlevel + scorer_role

## VII. Code Quality
- [ ] SonarQube Quality Gate — chưa chạy
- [ ] Lighthouse ≥ target — chưa chạy
- [ ] Bundle size ≤ budget — chưa đo
- [ ] Screenshot báo cáo gắn vào 09 — chưa có
