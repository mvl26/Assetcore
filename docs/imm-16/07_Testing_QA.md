# 07 — Kiểm thử & An ninh (Testing & QA & Security)

| Mục | Giá trị |
|---|---|
| Module | IMM-16 — Giám sát Tuân thủ & CAPA |
| Phạm vi | Per-module |
| Owner | QA Lead + Security Officer |
| Liên kết | 02 Analysis (US, BR, Activity, BPMN) · 03 Diagrams · 04 Backend · 05 API · 06 Frontend |

> **Mục đích**: Suy ra test case **có hệ thống** từ phân tích (file 02) bằng kỹ thuật black-box + white-box, không liệt kê tự phát. Bao gồm: phân tích đối tượng test → chọn kỹ thuật → viết test → traceability → UAT → security → code quality. Phần này là gate go-live.

> **Trạng thái**: Module IMM-16 đã LIVE (Wave 2). Suite test hiện tại: `assetcore/tests/test_imm16.py` — 12 TestCase, 29 test method (xem III.2). Các dòng đánh dấu `⬜ Planned` là backlog mở rộng chưa viết.

---

# Phần I — Test Analysis (Phân tích đối tượng test)

> Mục tiêu Phần I: trả lời 4 câu hỏi trước khi viết test case: **(1) test cái gì** (component inventory) **(2) suy ra từ đâu** (US/BR/Activity) **(3) ưu tiên cái nào** (risk) **(4) loại trừ cái nào** (out-of-scope).

## I.1. Component Inventory — Liệt kê phần mềm cần test

Toàn bộ artefact test được của IMM-16. Mỗi dòng → ≥ 1 test class ở Phần III. → tham chiếu 04 §DocType + §Service + §Hook · 05 §Catalog · 06 §Components.

| # | Component | Loại | File / Tên | Test layer áp dụng |
|---|---|---|---|---|
| 1 | IMM Compliance Rule | DocType | `imm_compliance_rule.json` | Integration (lifecycle) |
| 2 | IMM Compliance Finding | DocType + Workflow | `imm_compliance_finding.json` · `workflow/imm_16_finding_workflow.json` | Integration (state transition) |
| 3 | IMM CAPA Record (extended) | DocType + Workflow | `imm_capa_record.json` · `workflow/imm_16_capa_workflow.json` (shared IMM-12) | Integration (state transition) |
| 4 | IMM CAPA Action Step | Child DocType | `imm_capa_action_step.json` (shared IMM-12) | Integration |
| 5 | IMM Internal Audit | DocType + Workflow | `imm_internal_audit.json` · `workflow/imm_16_internal_audit.json` | Integration (state transition) |
| 6 | IMM Audit Checklist Item | Child DocType | `imm_audit_checklist_item.json` | Integration |
| 7 | IMM Compliance Scorecard | DocType | `imm_compliance_scorecard.json` (+ child `imm_scorecard_module_row`, `imm_scorecard_department_row`) | Integration (immutability) |
| 8 | IMM Management Review | DocType | `imm_management_review.json` | Integration |
| 9 | Rule lifecycle services | Service function | `services/imm16.py::create_compliance_rule / update_rule / deactivate_rule / reactivate_rule` | Unit |
| 10 | Finding triage services | Service function | `services/imm16.py::confirm_finding / mark_false_positive / waive_finding / link_finding_to_capa` | Unit |
| 11 | CAPA lifecycle services | Service function | `services/imm16.py::advance_capa_state / perform_effectiveness_check / reopen_capa / update_capa_fields / create_capa_from_finding / create_capa_from_incident` | Unit |
| 12 | Audit cycle services | Service function | `services/imm16.py::create_internal_audit / start_audit / complete_audit_checklist / close_internal_audit / submit_audit_findings` | Unit + Integration |
| 13 | Scorecard services | Service function | `services/imm16.py::generate_scorecard / publish_scorecard / validate_scorecard_immutability` | Unit |
| 14 | Management Review services | Service function | `services/imm16.py::create_management_review / update_management_review / advance_mr_state / finalize_management_review` | Unit |
| 15 | Threshold comparator | Validator (pure) | `services/imm16.py::_compare_values`, `_map_severity` | Unit (BVA/EP/Decision Table) |
| 16 | Cross-module gate | Service function | `services/imm16.py::check_asset_compliance_status`, `gate_wo_submit` | Unit + Integration (BR-16-09) |
| 17 | Rule evaluation core | Service function | `services/imm16.py::_evaluate_single_rule`, `_evaluate_single_rule_for_asset` | Unit |
| 18 | Validator hooks | Validator | `services/imm16.py::compliance_rule_validate / compliance_rule_before_save / compliance_finding_validate / capa_record_validate / capa_record_before_submit / validate_internal_audit` | Unit |
| 19 | Realtime eval hooks | Lifecycle hook | `services/imm16.py::eval_imm04_realtime / eval_imm05_realtime / eval_imm08_09_realtime / eval_imm11_realtime` | Integration |
| 20 | Audit trail event | Lifecycle event | `services/imm16.py::_log_record_event → utils.lifecycle.log_audit_event` → `IMM Audit Trail` | Integration (audit chain) |
| 21 | Schedulers | Scheduler job | `services/imm16.py::evaluate_all_compliance_rules / check_capa_due / run_compliance_evaluation_hourly / run_compliance_evaluation_weekly / check_audit_milestones / check_management_review_due / update_compliance_scorecard` | Unit + Cron simulation |
| 22 | Dashboard / reporting | Service function | `services/imm16.py::get_dashboard_stats / get_compliance_heatmap / get_capa_aging / get_overdue_actions / get_record_history` | Unit |
| 23 | API endpoints | API endpoint | `api/imm16.py` (52 `@frappe.whitelist`) | API integration |
| 24 | FE views | FE view | `frontend/src/views/compliance/*.vue` (10 view) | E2E (Playwright) |
| 25 | FE store / API client | Pinia store + client | `frontend/src/stores/imm16.ts` · `frontend/src/api/imm16.ts` | Unit (vitest) |

## I.2. Trace nguồn test — User Stories, Activity Flows, Business Rules

3 bảng dẫn từ artefact phân tích (file 02) sang test layer. Mỗi US/BR phải có ≥ 1 test ở Phần III và xuất hiện trong matrix Phần IV. → tham chiếu 02 §Functional Specs (US + AC), 02 §Business Rules, 02 §Use Case Diagram.

### I.2.a. Từ User Story
| US ID | Tiêu đề ngắn | Acceptance Criteria # | Test layer dự kiến |
|---|---|---|---|
| US-16-01 | Khai báo Compliance Rule | AC1 (threshold JSON), AC2 (version) | Unit + API + UAT |
| US-16-02 | Auto-detect Finding qua scheduler | AC1 (idempotent), AC2 (severity mirror) | Unit + UAT |
| US-16-03 | Confirm NC & open CAPA Record | AC1 (confirm), AC2 (CAPA link) | Unit + API + UAT |
| US-16-04 | Effectiveness check & Re-open | AC1 (Effective→Closed), AC2 (Not Effective→Re-open) | Unit + UAT |
| US-16-05 | Internal Audit cycle | AC1 (auto-Finding), AC2 (close gate VR-08) | Integration + UAT |
| US-16-06 | Compliance Scorecard sinh tự động | AC1 (formula), AC2 (immutability) | Unit + UAT |
| US-16-07 | Waive Finding (BR-16-06) | AC1..AC3 (reason/evidence/expiry), AC4 (role) | Unit + API + UAT |
| US-16-08 | Gate IMM-08/09 (BR-16-09) | AC1 (block), AC2 (unblock) | Unit + Integration + UAT |
| US-16-09 | Management Review quý | AC1 (finalize gate), AC2 (MR gate scorecard) | Unit + UAT |
| US-16-10 | Compliance Heatmap | AC1 (render), AC2 (drill-down) | E2E (UAT) |

### I.2.b. Từ Business Rule
| BR ID | Phát biểu (rút gọn) | Component liên quan (I.1) | Kỹ thuật test phù hợp |
|---|---|---|---|
| BR-16-01 | Finding severity ≥ High → mở CAPA trong 5 NLV | #11, #21 (`check_capa_due`) | EP + Use Case |
| BR-16-02 | CAPA Critical > 30 ngày → escalate | #11 (`_escalate_capa`), #21 | BVA (boundary 30 ngày) |
| BR-16-03 | CAPA Close chỉ khi effectiveness=Effective; Not Effective → Re-open + reopen_count++ | #11 (`perform_effectiveness_check`) | Decision Table |
| BR-16-04 | Audit Major NC → CAPA (VR-08 gate close) | #12 (`close_internal_audit`) | Decision Table |
| BR-16-05 | Rule đổi threshold/severity → change control versioned | #9 (`update_rule`), #18 (`compliance_rule_before_save`) | Decision Table |
| BR-16-06 | Waive chỉ Commissioning Manager + reason ≥ 50 + evidence + expiry > today | #10 (`waive_finding`) | Decision Table + BVA |
| BR-16-07 | Scorecard published immutable; sửa → restate | #13 (`validate_scorecard_immutability`) | Decision Table |
| BR-16-08 | Mỗi quý ≥ 1 MR Closed; missed → block publish scorecard | #13 (`publish_scorecard`), #14 | Decision Table |
| BR-16-09 | Asset có CAPA Critical OPEN → block IMM-08/09 WO Submit | #16 (`check_asset_compliance_status`, `gate_wo_submit`) | Decision Table |
| BR-16-10 | Mọi mutation ghi IMM Audit Trail (hash chain) + Frappe Version | #20 (`_log_record_event`) | Use Case + audit chain |

### I.2.c. Từ Activity Flow / BPMN
| Hoạt động | Use Case | Branch chính | Branch ngoại lệ |
|---|---|---|---|
| Rule eval → Finding | US-16-02 | Threshold vi phạm → tạo Finding | metric None → skip; chạy lại cùng ngày → không duplicate |
| Finding triage | US-16-03/07 | Confirm NC → CAPA | False Positive; Waive (role + VR-04) |
| CAPA lifecycle | US-16-04 | Open→…→Verification→Closed (Effective) | Not Effective → Re-opened → Investigating |
| Internal Audit | US-16-05 | Planned→In Progress→Reporting→Closed | Major NC chưa có CAPA → VR-08 block close |
| Scorecard publish | US-16-06/09 | Draft → Published (MR quý trước Closed) | Không có MR Closed → VR-10 block; published → immutable |
| WO submit gate | US-16-08 | Asset clean → submit OK | CAPA Critical open → block (BR-16-09) |

## I.3. Risk-based Priority

| Component (I.1) | Likelihood (1-5) | Impact (1-5) | Risk = L×I | Priority |
|---|---|---|---|---|
| #16 Cross-module gate (`gate_wo_submit`) | 4 | 5 | 20 | **Critical** |
| #13 Scorecard immutability + MR gate | 3 | 5 | 15 | **Critical** |
| #11 CAPA effectiveness / re-open (BR-16-03) | 4 | 4 | 16 | **Critical** |
| #15 Threshold comparator `_compare_values` | 4 | 4 | 16 | **Critical** |
| #10 Waive finding (BR-16-06 role + VR-04) | 3 | 4 | 12 | **High** |
| #20 Audit trail chain (BR-16-10) | 2 | 5 | 10 | **High** |
| #9 Rule change control (VR-11) | 3 | 3 | 9 | Medium |
| #12 Audit close gate (VR-08) | 3 | 3 | 9 | Medium |
| #21 Schedulers (idempotency) | 3 | 3 | 9 | Medium |
| #22 Dashboard / heatmap (read-only) | 2 | 2 | 4 | Low |

**Quy ước priority**:
- **Critical** (R ≥ 15): test trước, fail = block release
- **High** (10 ≤ R < 15): bắt buộc trước go-live
- **Medium** (5 ≤ R < 10): trong sprint khi có thời gian
- **Low** (R < 5): chỉ test khi báo cáo bug

## I.4. Scope

- **In-scope**: deterministic logic (threshold comparator, scorecard formula, gate), workflow transitions của 3 workflow (Finding 8, CAPA 7, Internal Audit 3), Finding/CAPA lifecycle, RBAC/DocPerm, audit trail chain, cross-module gate BR-16-09.
- **Out-of-scope**:
  - Performance test → giao Phần III.8 (chỉ định target, chưa benchmark).
  - Cross-module thực thi IMM-08/09 WO submit → chỉ smoke ở mức gate (IMM-08/09 có suite riêng).
  - Email/escalation template rendering (`_send_capa_escalation`) → smoke logic, không test nội dung email.
  - Chart/heatmap visual rendering → chỉ E2E drill-down, không pixel-diff.
  - SSO / LDAP / 2FA → roadmap, không trong scope module.
- **Assumptions**: master data (Department, Asset, Vendor) đã seed qua fixtures; test users theo 30-role catalog đã tạo; site test `bench run-tests`; browser Chromium (Playwright headless).

---

# Phần II — Test Design Techniques (Kỹ thuật thiết kế test case)

> Mục tiêu Phần II: chọn đúng kỹ thuật cho từng loại input/logic. Mỗi test phải truy được về 1 kỹ thuật ở dưới.

## II.1. Black-box techniques

| Kỹ thuật | Khi nào dùng | Áp dụng vào IMM-16 | Số test sinh ra (rule of thumb) |
|---|---|---|---|
| **Equivalence Partitioning (EP)** | Input có miền giá trị chia nhóm tương đương | `severity` enum (Low/Medium/High/Critical), `op` enum (`<`,`>`,`==`,`<=`,`>=`), `evaluation_frequency`, `effectiveness_check` enum | 1 test/partition |
| **Boundary Value Analysis (BVA)** | Numeric / date / length field có biên | `waiver_reason` length (≥ 50 chars), `due_date`/`expiry_date` (> today), CAPA escalation (30 ngày), threshold biên (78 < 90, 90 < 90, 90 ≤ 90) | 2-3 test/biên |
| **Decision Table** | Multi-condition gate, business rule kết hợp | BR-16-03 (effectiveness × close), BR-16-06 (role × reason × evidence × expiry), BR-16-08 (MR Closed × publish), BR-16-09 (risk_level × status) | 2^N rút gọn theo equivalence |
| **State Transition Testing** | Workflow finite state machine | Finding workflow (8 transition), CAPA workflow (7 transition), Internal Audit (3 transition) | Mỗi transition + invalid transition |
| **Use Case Testing** | End-to-end actor flow | UAT scenarios, API integration test | 1/main + 1/alt + 1/exception |
| **Pairwise / Combinatorial** | Nhiều field optional kết hợp | Form tạo Rule (`source_module` × `category` × `severity` × `frequency`) | Min set cover all pairs |
| **Error Guessing** | Lỗi từ kinh nghiệm: null, empty, unicode, race | Threshold metric None → skip; scheduler chạy 2 lần cùng ngày; CAPA missing | Bổ sung — không thay thế kỹ thuật khác |

## II.2. White-box techniques

| Kỹ thuật | Áp dụng vào | Tiêu chí đạt | Công cụ |
|---|---|---|---|
| **Statement coverage** | Service functions ở I.1 (#9–#22) | ≥ 85% line (target) | `coverage report` |
| **Branch / Decision coverage** | Function có if/else, try/except (`_compare_values`, `advance_capa_state`, `publish_scorecard`, validators) | ≥ 80% branch (target) | `coverage --branch` |
| **Condition / MC/DC** | Gate logic BR-16-09 (`check_asset_compliance_status`: risk_level AND status), VR-04 multi-AND | Mỗi sub-condition kiểm soát outcome độc lập | Manual test design + coverage |
| **Path coverage** | `_compare_values` (≤ 20 LOC, 5 nhánh op) | Toàn bộ path khả dĩ | Manual |

## II.3. Mapping Component → Kỹ thuật

| Loại component | Kỹ thuật chính | Kỹ thuật phụ |
|---|---|---|
| Field validator (`compliance_*_validate`) | BVA + EP | Error guessing |
| Gate logic (`check_asset_compliance_status`, `gate_wo_submit`) | Decision Table | MC/DC |
| Workflow transition (Finding/CAPA/Audit) | State Transition | Use Case |
| Service function pure (`_compare_values`, scorecard formula) | EP + Branch coverage | BVA |
| API endpoint (`api/imm16.py`) | Use Case + EP | Pairwise (form input) |
| Scheduler / cron (`evaluate_all_compliance_rules`, `check_capa_due`) | Use Case (state setup → run → assert) | Error guessing (idempotency, partial fail) |
| FE view (Playwright) | Use Case end-to-end | Error guessing (network 4xx/5xx, role gate) |

---

# Phần III — Test Plan (Kế hoạch thực thi)

## III.1. Test Pyramid

```
                  ┌────────────┐
                  │  E2E / UAT │   ~5%   (12 UAT scenario — V.4)
                 ─┴────────────┴─
              ┌──────────────────────┐
              │   API Integration    │   ~15%  (⬜ Planned)
             ─┴──────────────────────┴─
          ┌────────────────────────────────┐
          │  Workflow + DocType lifecycle  │   ~25%  (workflow transition)
         ─┴────────────────────────────────┴─
      ┌────────────────────────────────────────────┐
      │         Unit — Service Layer               │   ~55%  (test_imm16.py LIVE)
     ─┴────────────────────────────────────────────┴─
```

→ tham chiếu CLAUDE.md §17 (TDD mandatory).

## III.2. Unit test — Service Layer

File: `assetcore/tests/test_imm16.py` — **12 TestCase, 29 test method** (LIVE). Mỗi test class trace về ≥ 1 dòng I.1.

| Test class | Function cover (I.1) | Kỹ thuật | Cases | Trạng thái |
|---|---|---|---|---|
| `TestRuleLifecycle::test_update_rule_without_change_summary_fails` | #9 `update_rule` (VR-11) | Decision Table | 1 negative | ✅ Live |
| `TestRuleLifecycle::test_update_rule_with_change_summary_bumps_version` | #9 `update_rule` version bump | EP | 1 happy | ✅ Live |
| `TestRuleLifecycle::test_deactivate_rule` | #9 `deactivate_rule` | Use Case | 1 happy | ✅ Live |
| `TestFindingWaiver::test_waive_with_short_reason_fails` | #10 `waive_finding` (VR-04 reason) | BVA | 1 negative | ✅ Live |
| `TestFindingWaiver::test_waive_missing_evidence_fails` | #10 `waive_finding` (VR-04 evidence) | EP | 1 negative | ✅ Live |
| `TestFindingWaiver::test_waive_expired_expiry_fails` | #10 `waive_finding` (VR-04 expiry) | BVA | 1 negative | ✅ Live |
| `TestAuditClose::test_close_audit_missing_planned_audit` | #12 `close_internal_audit` | Error guessing | 1 negative (NOT_FOUND) | ✅ Live |
| `TestCapaWorkflow::test_advance_to_action_plan_requires_root_cause_method` | #11 `advance_capa_state` (VR-05) | Decision Table | 1 negative | ✅ Live |
| `TestCapaWorkflow::test_advance_to_action_plan_requires_future_due_date` | #11 `advance_capa_state` (VR-12) | BVA | 1 negative | ✅ Live |
| `TestEffectivenessCheck::test_not_effective_reopens_capa` | #11 `perform_effectiveness_check` (BR-16-03) | Decision Table | 1 happy (re-open) | ✅ Live |
| `TestScorecardPublish::test_publish_scorecard_without_prev_mr_fails` | #13 `publish_scorecard` (VR-10) | Decision Table | 1 negative | ✅ Live |
| `TestCrossModuleGate::test_check_asset_compliance_returns_unblocked_for_empty` | #16 `check_asset_compliance_status` (BR-16-09) | EP | 1 happy | ✅ Live |
| `TestCrossModuleGate::test_check_asset_compliance_returns_unblocked_for_clean_asset` | #16 `check_asset_compliance_status` | EP | 1 happy | ✅ Live |
| `TestDashboard::test_dashboard_stats_shape` | #22 `get_dashboard_stats` | Use Case | 1 schema | ✅ Live |
| `TestRecordHistory::test_history_validation` | #22 `get_record_history` | EP | 1 negative | ✅ Live |
| `TestRecordHistory::test_history_shape` | #22 `get_record_history` | Use Case | 1 schema | ✅ Live |
| `TestRecordHistory::test_confirm_finding_writes_audit_trail` | #10 `confirm_finding` + #20 audit trail (BR-16-10) | Use Case | 1 audit chain | ✅ Live |
| `TestRuleReactivate::test_deactivate_then_reactivate` | #9 `deactivate_rule` + `reactivate_rule` | State Transition | 1 round-trip | ✅ Live |
| `TestCapaFieldsAndGet::test_advance_to_action_plan_requires_root_cause_method` | #11 `advance_capa_state` (VR-05) | Decision Table | 1 negative | ✅ Live |
| `TestCapaFieldsAndGet::test_update_capa_fields_persists` | #11 `update_capa_fields` | EP | 1 happy | ✅ Live |
| `TestCapaFieldsAndGet::test_get_capa_not_found` | #11 `get_capa` | Error guessing | 1 negative (NOT_FOUND) | ✅ Live |
| `TestMRLifecycle::test_advance_draft_to_held` | #14 `advance_mr_state` | State Transition | 1 happy | ✅ Live |
| `TestMRLifecycle::test_advance_invalid_transition_rejected` | #14 `advance_mr_state` | State Transition | 1 negative (INVALID_STATE) | ✅ Live |
| `TestMRLifecycle::test_update_management_review_content` | #14 `update_management_review` | EP | 1 happy | ✅ Live |
| `TestMRLifecycle::test_finalize_requires_output_action` | #14 `finalize_management_review` | Decision Table | 1 negative | ✅ Live |
| `TestCAPAFromIncidentChain::test_create_capa_from_incident_basic_link` | #11 `create_capa_from_incident` | Use Case | 1 happy | ✅ Live |
| `TestCAPAFromIncidentChain::test_create_capa_from_incident_idempotent` | #11 `create_capa_from_incident` | Error guessing (idempotent) | 1 happy | ✅ Live |
| `TestCAPAFromIncidentChain::test_create_capa_links_back_to_rca` | #11 `create_capa_from_incident` + RCA link | Use Case | 1 happy | ✅ Live |
| `TestCAPAFromIncidentChain::test_create_capa_from_invalid_incident_raises` | #11 `create_capa_from_incident` | Error guessing | 1 negative | ✅ Live |

**Gap (⬜ Planned)**: chưa có unit riêng cho `_compare_values` (threshold BVA/EP toàn matrix op), `generate_scorecard` formula (score_pct round 2dp), `create_capa_from_finding`, `mark_false_positive`, scheduler idempotency của `evaluate_all_compliance_rules`.

> *Lưu ý*: dùng `SimpleNamespace` cho test thuần công thức (`_compare_values`, score_pct) — chạy ms-level, không cần fixture cleanup.

## III.3. Integration — DocType lifecycle

File (⬜ Planned): `tests/test_imm16_doctype.py`. Cover hook `validate / before_save / before_submit / on_update`.

| Test | Setup | Action | Assert | Kỹ thuật |
|---|---|---|---|---|
| Rule before_save versioned | Rule `version=1.0` đã lưu | đổi threshold → `doc.save()` | `change_summary` reqd (VR-11), version bump | Decision Table |
| Finding validate severity | seed Finding | `doc.insert()` | severity ∈ enum (VR-03) | EP |
| CAPA before_submit | CAPA Verification | `doc.submit()` | effectiveness=Effective else block (VR-06/07) | Decision Table |
| Scorecard immutability | Scorecard `is_published=1` | `doc.save()` | raise VR-09 | EP |

> *Lưu ý*: fixture trong `setUpClass` phải có `tearDownClass` purge.

## III.4. Integration — Workflow transitions

File (⬜ Planned): `tests/test_imm16_workflow.py`. **Bắt buộc** cover mọi transition trong 3 workflow JSON.

**Finding** — `workflow/imm_16_finding_workflow.json` — **8 transition**:

| Transition | From → To | Role required | Test pass | Test fail (wrong role) |
|---|---|---|---|---|
| Bắt đầu xem xét | Open → Under Review | Compliance Manager | ⬜ | ⬜ |
| Xác nhận vi phạm | Under Review → Confirmed NC | Compliance Manager | ⬜ | ⬜ |
| Xác nhận không vi phạm | Under Review → False Positive | Compliance Manager | ⬜ | ⬜ |
| Miễn trừ | Under Review → Waived | Commissioning Manager | ⬜ | ⬜ (Compliance Manager phải fail) |
| Đánh dấu đã giải quyết | Confirmed NC → Resolved | Compliance Manager | ⬜ | ⬜ |
| Đóng finding | False Positive → Closed | Compliance Manager | ⬜ | ⬜ |
| Đóng finding | Waived → Closed | Compliance Manager | ⬜ | ⬜ |
| Đóng finding | Resolved → Closed | Compliance Manager | ⬜ | ⬜ |

**CAPA** — `workflow/imm_16_capa_workflow.json` — **7 transition**:

| Transition | From → To | Role required | Test pass | Test fail (gate/role) |
|---|---|---|---|---|
| Bắt đầu điều tra | Open → Investigating | Compliance Manager | ⬜ | ⬜ |
| Lập kế hoạch hành động | Investigating → Action Plan | Compliance Manager | ⬜ | ⬜ (VR-05 root_cause / VR-12 due_date) |
| Bắt đầu thực thi | Action Plan → Implementation | PM Manager | ⬜ | ⬜ |
| Chuyển sang xác minh | Implementation → Verification | Compliance Manager | ⬜ | ⬜ |
| Đóng CAPA | Verification → Closed | Compliance Manager | ⬜ | ⬜ (VR-06/07 effectiveness) |
| Mở lại do chưa hiệu quả | Verification → Re-opened | Compliance Manager | ⬜ | ⬜ |
| Bắt đầu điều tra lại | Re-opened → Investigating | Compliance Manager | ⬜ | ⬜ |

**Internal Audit** — `workflow/imm_16_internal_audit.json` — **3 transition**:

| Transition | From → To | Role required | Test pass | Test fail (gate) |
|---|---|---|---|---|
| Bắt đầu Audit | Planned → In Progress | Compliance Manager | ⬜ | ⬜ |
| Chuyển sang Báo cáo | In Progress → Reporting | Compliance Manager | ⬜ | ⬜ |
| Đóng Audit | Reporting → Closed | Compliance Manager | ⬜ | ⬜ (VR-08 Major NC chưa có CAPA) |

**Kỹ thuật**: State Transition Testing — mỗi edge = 1 test pass + 1 test fail. Tổng = 18 transition (8 + 7 + 3).

## III.5. Integration — Audit chain integrity

2 test chính (⬜ Planned):
- (a) Sau N mutation Finding/CAPA, chain hash SHA-256 trong `IMM Audit Trail` hợp lệ end-to-end. Note: `TestRecordHistory::test_confirm_finding_writes_audit_trail` (✅ Live) đã verify entry được ghi sau `confirm_finding`.
- (b) Khi 1 entry bị tamper → verify endpoint trả `chain_broken=true`.

→ tham chiếu 04 §Audit Trail · `IMM Audit Trail` DocType · `services/imm16.py::_log_record_event`.

## III.6. API test

File (⬜ Planned): `tests/test_imm16_api.py`. Cover happy + `INVALID_PARAMS` + `FORBIDDEN` + pagination + idempotent retry. `api/imm16.py` có 52 endpoint whitelist.

| Test | Endpoint | Verify | Kỹ thuật |
|---|---|---|---|
| List rules envelope | `api/imm16.list_compliance_rules` | `success=true`, `data.items`, `total` | Use Case |
| Create rule invalid threshold | `api/imm16.create_compliance_rule` | `code=VALIDATION` (VR-01) | EP |
| Waive finding low-role | `api/imm16.waive_finding` (non Commissioning Mgr) | `code=FORBIDDEN` (BR-16-06) | EP (permission partition) |
| Check asset compliance | `api/imm16.check_asset_compliance_status` | `blocked` bool, `reasons` list | Use Case |
| Publish scorecard no MR | `api/imm16.publish_scorecard` | `code=VALIDATION` (VR-10) | Decision Table |
| Pagination boundary | `api/imm16.list_compliance_findings` | `page=1,page_size=20` biên | BVA |

## III.7. E2E browser (Playwright)

Dùng cho flow UI khó cover bằng API: workflow button visibility theo role (Waive chỉ hiện với Commissioning Manager), heatmap drill-down (US-16-10), modal Open CAPA from Finding, cascade dropdown trong form Rule. → tham chiếu `assetcore-test` skill Phần 2 (Playwright MCP recipes + R-1..R-9 data rules).

## III.8. Performance test

| Metric | Target | Method |
|---|---|---|
| `check_asset_compliance_status` (gate check) | ≤ 200ms p99 | Single SQL query; `EXPLAIN ANALYZE` |
| `get_compliance_heatmap` (6 tháng × module × dept) | ≤ 2s p95 | DB index + cache; k6 GET |
| `evaluate_all_compliance_rules` scheduler | ≤ 120s / (rules × assets) | `time bench execute …` (staging) |
| `update_compliance_scorecard` (monthly) | ≤ 30s | batch aggregation |
| Scorecard/Finding list 200 row p95 | ≤ 400ms | k6 GET `list_*` endpoint |

*(Target chỉ định — chưa benchmark thực; Cần khảo sát baseline khi vào sprint perf.)*

## III.9. Test data & Fixtures

| Loại | Cách seed | File |
|---|---|---|
| Master data (Department, Asset Category, Vendor) | `fixtures/*.json` (cài qua `bench migrate`) | `assetcore/fixtures/` |
| Role (30-role catalog) | `fixtures/role.json` | `assetcore/fixtures/role.json` |
| Backend test records | tạo trong `setUpClass` (`TestImm16Base`) với prefix `_Test` | `assetcore/tests/test_imm16.py` |
| UAT seed | Python script | `assetcore/scripts/uat/uat_imm16.py` *(Cần khảo sát — chưa xác nhận tồn tại)* |

> *Lưu ý*: UAT data phải thực tế (tên bệnh viện VN, dept ICU/CT). Backend test fixture dùng prefix `_Test`.

## III.10. Run commands & Coverage gate

```bash
# Module test (LIVE)
bench --site [site] run-tests --app assetcore --module assetcore.tests.test_imm16
# Coverage
coverage run -m unittest assetcore.tests.test_imm16 && coverage report
# Workflow smoke
bench --site [site] run-tests --module assetcore.tests.test_workflows
```

| Layer | Target coverage | Đo |
|---|---|---|
| Service (`services/imm16.py`) | ≥ 85% line + ≥ 80% branch | `coverage --branch` |
| DocType lifecycle | ≥ 70% | `coverage report` |
| API (`api/imm16.py`) | ≥ 60% | `coverage report` |
| Frontend (vue-tsc) | 0 error | `npm run build` |

> Coverage % thực tế: *(Cần khảo sát — chưa chạy coverage report)*. Bảng trên là target.

---

# Phần IV — Traceability Matrices

> 3 ma trận theo 3 hướng. Mọi test ở Phần III phải xuất hiện ở cả 3 bảng.

## IV.1. US → Test mapping

| US ID | AC | Test ID (III.x) | Layer | Status |
|---|---|---|---|---|
| US-16-01 | AC2 (version) | `TestRuleLifecycle::test_update_rule_with_change_summary_bumps_version` | Unit | ✅ Live |
| US-16-01 | AC1 (threshold JSON) | `test_imm16_doctype.py::Rule validate VR-01` | Integration | ⬜ Planned |
| US-16-02 | AC1 (idempotent) | scheduler idempotency test | Unit | ⬜ Planned |
| US-16-03 | AC1 (confirm) | `TestRecordHistory::test_confirm_finding_writes_audit_trail` | Unit | ✅ Live |
| US-16-03 | AC2 (CAPA link) | `TestCAPAFromIncidentChain::test_create_capa_links_back_to_rca` | Unit | ✅ Live |
| US-16-04 | AC2 (Not Effective→Re-open) | `TestEffectivenessCheck::test_not_effective_reopens_capa` | Unit | ✅ Live |
| US-16-04 | AC1 (VR-05/VR-12 gate) | `TestCapaWorkflow::test_advance_to_action_plan_requires_root_cause_method` / `..._future_due_date` | Unit | ✅ Live |
| US-16-05 | AC2 (close gate) | `TestAuditClose::test_close_audit_missing_planned_audit` | Unit | ✅ Live |
| US-16-05 | AC1 (auto-Finding) | `test_imm16_workflow.py::Internal Audit` | Integration | ⬜ Planned |
| US-16-06 | AC2 (immutability) | `TestScorecardPublish::test_publish_scorecard_without_prev_mr_fails` | Unit | ✅ Live |
| US-16-06 | AC1 (formula) | `generate_scorecard` formula test | Unit | ⬜ Planned |
| US-16-07 | AC1..AC3 (VR-04) | `TestFindingWaiver::test_waive_*` (3 method) | Unit | ✅ Live |
| US-16-07 | AC4 (role) | `test_imm16_api.py::waive low-role FORBIDDEN` | API | ⬜ Planned |
| US-16-08 | AC1/AC2 (block/unblock) | `TestCrossModuleGate::test_check_asset_compliance_*` (2 method) | Unit | ✅ Live |
| US-16-09 | AC1 (finalize gate) | `TestMRLifecycle::test_finalize_requires_output_action` | Unit | ✅ Live |
| US-16-09 | AC2 (MR gate scorecard) | `TestScorecardPublish::test_publish_scorecard_without_prev_mr_fails` | Unit | ✅ Live |
| US-16-10 | AC1/AC2 (render/drill-down) | `UAT-IMM16-12` Heatmap | E2E | ⬜ Planned |

**DoD**: mọi US có ≥ 1 dòng. Cột Status không trống. ✅

## IV.2. BR → Test mapping

| BR ID | Phát biểu (rút gọn) | Test ID | Kỹ thuật | Happy / Negative |
|---|---|---|---|---|
| BR-16-01 | Finding High → CAPA 5 NLV | `check_capa_due` scheduler test | Use Case | ⬜ / ⬜ |
| BR-16-02 | CAPA Critical > 30 ngày escalate | `_escalate_capa` BVA test | BVA | ⬜ / ⬜ |
| BR-16-03 | Not Effective → Re-open | `TestEffectivenessCheck::test_not_effective_reopens_capa` | Decision Table | 1 ✅ / ⬜ (Effective→Closed) |
| BR-16-04 | Audit Major NC → CAPA (VR-08) | `TestAuditClose::test_close_audit_missing_planned_audit` | Decision Table | ⬜ / 1 ✅ |
| BR-16-05 | Rule change control versioned | `TestRuleLifecycle::test_update_rule_with/without_change_summary` | Decision Table | 1 ✅ / 1 ✅ |
| BR-16-06 | Waive role + VR-04 | `TestFindingWaiver::test_waive_*` (3) | Decision Table + BVA | ⬜ / 3 ✅ |
| BR-16-07 | Scorecard immutable | `validate_scorecard_immutability` test | Decision Table | ⬜ / ⬜ |
| BR-16-08 | MR quý → publish gate | `TestScorecardPublish::test_publish_scorecard_without_prev_mr_fails` | Decision Table | ⬜ / 1 ✅ |
| BR-16-09 | CAPA Critical → block WO | `TestCrossModuleGate::test_check_asset_compliance_*` (2) | Decision Table | 2 ✅ / ⬜ (blocked case) |
| BR-16-10 | Mọi mutation → audit trail | `TestRecordHistory::test_confirm_finding_writes_audit_trail` | Use Case | 1 ✅ / ⬜ (tamper) |

**DoD**: mọi BR có ≥ 1 test. Gap negative-side (BR-16-09 blocked, BR-16-03 Effective→Closed happy, BR-16-07 immutable) đánh dấu ⬜ Planned — cần bổ sung trước khi đạt "happy + negative đầy đủ".

## IV.3. Component → Test mapping

| Component (I.1) | Test ID | Test layer | Coverage % | Risk priority (I.3) |
|---|---|---|---|---|
| #16 `check_asset_compliance_status` | `TestCrossModuleGate::*` | Unit | *(Cần khảo sát)* | Critical |
| #16 `gate_wo_submit` | `test_imm16_workflow.py` | Integration | *(Cần khảo sát)* | Critical |
| #13 `publish_scorecard` | `TestScorecardPublish::*` | Unit | *(Cần khảo sát)* | Critical |
| #11 `perform_effectiveness_check` | `TestEffectivenessCheck::*` | Unit | *(Cần khảo sát)* | Critical |
| #11 `advance_capa_state` | `TestCapaWorkflow::*`, `TestCapaFieldsAndGet::*` | Unit | *(Cần khảo sát)* | Critical |
| #15 `_compare_values` | ⬜ Planned (BVA matrix) | Unit | *(Cần khảo sát)* | Critical |
| #10 `waive_finding` | `TestFindingWaiver::*` | Unit | *(Cần khảo sát)* | High |
| #20 audit trail (`_log_record_event`) | `TestRecordHistory::test_confirm_finding_writes_audit_trail` | Unit | *(Cần khảo sát)* | High |
| #9 `update_rule` / `deactivate_rule` / `reactivate_rule` | `TestRuleLifecycle::*`, `TestRuleReactivate::*` | Unit | *(Cần khảo sát)* | Medium |
| #12 `close_internal_audit` | `TestAuditClose::*` | Unit | *(Cần khảo sát)* | Medium |
| #14 MR services | `TestMRLifecycle::*` | Unit | *(Cần khảo sát)* | Medium |
| #22 `get_dashboard_stats`, `get_record_history` | `TestDashboard::*`, `TestRecordHistory::*` | Unit | *(Cần khảo sát)* | Low |

**DoD**: mọi component Critical/High đã có ≥ 1 test trỏ tới (trừ `_compare_values` ⬜ Planned). Coverage % chưa đo (`coverage report` chưa chạy).

---

# Phần V — UAT Script

## V.1. Phạm vi UAT

- **In-scope**: 12 scenario theo US (V.4) — nguồn TC-01..TC-12 của source `IMM-16_UAT_Script.md` (archived).
- **Out-of-scope**: performance (III.8), security (Phần VI), email rendering, chart pixel-diff.
- **Pre-condition**: site UAT deploy version `0.0.2`, fixtures loaded (Department ICU/CT, Asset test), tester accounts theo 30-role catalog active.

## V.2. Tester accounts

| Username | Role (30-role catalog) | Persona / Vai trò UAT |
|---|---|---|
| `test_qlcl` | Compliance Manager | Tổ HC-QLCL — tạo Rule, triage Finding, oversight CAPA, close Audit |
| `test_vp2` | Commissioning Manager | VP Block2 — Waive Finding, Publish Scorecard, Finalize MR |
| `test_wshead` | PM Manager | Workshop Head — CAPA Implementation owner |
| `test_biomed` | Corrective User / PM User | Biomed — chịu gate BR-16-09, không được waive |
| `test_auditor` | Compliance User | Internal Auditor — checklist audit |

> Lưu ý: workflow JSON gắn role theo 30-role catalog (Compliance Manager / Commissioning Manager / PM Manager). Persona cũ (Tổ HC-QLCL, VP Block2, Workshop Head) đã ánh xạ post-patch `v3_2.001_module_role_redesign`. Phải có account role thấp (`test_biomed`) để cover FORBIDDEN.

## V.3. Test data đã seed

| DocType | Số lượng | Ghi chú |
|---|---|---|
| IMM Compliance Rule | ≥ 1 | `TEST-R-001` PM compliance `<90` |
| Asset | ≥ 2 | 1 clean, 1 có CAPA Critical (cho BR-16-09) |
| IMM Management Review | 1 | quý trước, status Closed (cho VR-10 gate) |
| Department | 2 | ICU, CT |

Reset script đi kèm: *(Cần khảo sát — chưa xác nhận `scripts/uat/uat_imm16.py`)*.

## V.4. UAT Scenarios — Suy ra từ US + Activity

12 scenario (theo template Phụ lục A), ID `UAT-IMM16-NN`. Nguồn: TC-01..TC-12.

| ID | Actor | Pre-condition | US/BR cover | Kỹ thuật | Kết quả mong đợi |
|---|---|---|---|---|---|
| UAT-IMM16-01 | Compliance Manager | role tồn tại | US-16-01, BR-16-05 | Use Case happy | Rule saved, version=1.0, is_active=1 |
| UAT-IMM16-02 | Compliance Manager | — | US-16-01, VR-01 | Use Case alt | VR-01 block save threshold sai format/op |
| UAT-IMM16-03 | System (scheduler) | UAT-01 passed, PM ICU=78% | US-16-02, BR-16-01 | Use Case + Error guessing | 1 Finding; chạy lại cùng ngày → vẫn 1 (idempotent) |
| UAT-IMM16-04 | Compliance Manager | UAT-03 passed | US-16-03, BR-16-04 | Use Case happy | CAPA tạo từ Finding, liên kết 2 chiều |
| UAT-IMM16-05 | PM Manager → Compliance Manager | UAT-04 passed | US-16-04, VR-05/06/12 | State Transition | Full lifecycle Open→Closed; Finding auto-resolve |
| UAT-IMM16-06 | Compliance Manager | CAPA Verification | US-16-04, BR-16-03, VR-07 | Decision Table | Not Effective → Re-opened; reopen_count++ |
| UAT-IMM16-07 | Commissioning Manager | Finding Under Review | US-16-07, BR-16-06, VR-04 | Decision Table + EP permission | Waive chỉ Commissioning Mgr; 3 VR-04 enforced; low-role → FORBIDDEN |
| UAT-IMM16-08 | Compliance Manager → Compliance User | — | US-16-05, BR-16-04, VR-08 | State Transition | Auto-Finding; VR-08 gate; audit Closed với evidence |
| UAT-IMM16-09 | System → Commissioning Manager | — | US-16-06, BR-16-07, VR-09 | Decision Table | Formula đúng; immutable sau publish; restate flow |
| UAT-IMM16-10 | Commissioning Manager | MR quý trước bị xóa | US-16-09, BR-16-08, VR-10 | Decision Table | Block publish, code VALIDATION; tạo MR Closed → publish OK |
| UAT-IMM16-11 | Corrective/PM User | asset có CAPA Critical Implementation | US-16-08, BR-16-09 | Decision Table | Gate block/unblock deterministic theo CAPA state |
| UAT-IMM16-12 | Compliance Manager | scorecard data | US-16-10 | Use Case E2E | Heatmap render đúng màu, drill-down navigate đúng |

**Chi tiết step-by-step** giữ nguyên trong source archived `IMM-16_UAT_Script.md` (TC-01..TC-12); mỗi scenario tuân theo Phụ lục A.

## V.5. Tổng hợp kết quả & Bug found

- Bảng `Scenario · Status (Pass/Fail/Block) · Tester · Ngày · Ghi chú` — điền khi chạy UAT thực. *(Chưa chạy UAT — Cần khảo sát.)*
- Bug list: `Issue ID · Severity (Blocker/Major/Minor/Trivial) · Mô tả · Fix status`.
- Acceptance: ≥ 95% PASS, Blocker = 0, Major ≤ 2 (có workaround).
- Sign-off: BA Lead + QA Lead + Module Owner (Tổ HC-QLCL & Risk) + End-user.

---

# Phần VI — Security Review (gate)

## VI.1. RBAC

- **Role definitions**: `assetcore/fixtures/role.json` (30-role catalog) + `role_profile.json`. IMM-16 dùng: Compliance Manager, Compliance User, Commissioning Manager (waive), PM Manager (CAPA implementation), AssetCore Auditor, AssetCore Super Admin.
- **DocPerm matrix** per DocType: xem các bảng dưới (Read/Write/Create/Delete/Submit/Cancel). Kỹ thuật Decision Table — mỗi (role × action × state) = 1 row Allow/Deny.

### IMM Compliance Rule
| Role | Read | Write | Create | Delete | Submit | Cancel |
|---|:--:|:--:|:--:|:--:|:--:|:--:|
| Compliance Manager | ✓ | ✓ | ✓ | ✗ | — | — |
| Compliance User | ✓ | ✗ | ✗ | ✗ | — | — |
| Commissioning Manager | ✓ | ✗ | ✗ | ✗ | — | — |
| PM Manager | ✓ | ✗ | ✗ | ✗ | — | — |
| AssetCore Auditor | ✓ | ✗ | ✗ | ✗ | — | — |
| AssetCore Super Admin | ✓ | ✓ | ✓ | ✓ | — | — |

### IMM Compliance Finding
| Role | Read | Write | Create | Delete | Submit | Cancel |
|---|:--:|:--:|:--:|:--:|:--:|:--:|
| Compliance Manager | ✓ | ✓* | ✓ | ✗ | ✓ | ✗ |
| Compliance User | ✓ | ✓* | ✓ | ✗ | ✗ | ✗ |
| Commissioning Manager | ✓ | ✓** | ✗ | ✗ | ✗ | ✗ |
| PM Manager / Corrective User | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| AssetCore Super Admin | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

_* Write chỉ khi status = Open / Under Review (pre-confirm)._
_** Commissioning Manager chỉ waive qua API (`waive_finding`), không phải form edit._

### IMM CAPA Record (shared IMM-12)
| Role | Read | Write | Create | Delete | Submit | Cancel |
|---|:--:|:--:|:--:|:--:|:--:|:--:|
| Compliance Manager | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ |
| Compliance User | ✓ | ✓* | ✓ | ✗ | ✗ | ✗ |
| PM Manager | ✓ | ✓* | ✓ | ✗ | ✗ | ✗ |
| Commissioning Manager | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| AssetCore Super Admin | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

_* Write giới hạn record sở hữu / action_step của dept._

### IMM Internal Audit
| Role | Read | Write | Create | Delete | Submit | Cancel |
|---|:--:|:--:|:--:|:--:|:--:|:--:|
| Compliance Manager | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ |
| Compliance User | ✓ | ✓* | ✗ | ✗ | ✗ | ✗ |
| Commissioning Manager | ✓ | ✓** | ✗ | ✗ | ✓** | ✗ |
| AssetCore Super Admin | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

_* Checklist item khi In Progress._  _** Close audit only._

### IMM Compliance Scorecard
| Role | Read | Write | Create | Delete | Submit | Cancel |
|---|:--:|:--:|:--:|:--:|:--:|:--:|
| Compliance Manager | ✓ | ✓* | ✗ | ✗ | ✓* | ✗ |
| Commissioning Manager | ✓ | ✗ | ✗ | ✗ | ✓* | ✗ |
| Compliance User | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| System | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |
| AssetCore Super Admin | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

_* Chỉ khi is_published=0 (VR-09 immutability)._

### IMM Management Review
| Role | Read | Write | Create | Delete | Submit | Cancel |
|---|:--:|:--:|:--:|:--:|:--:|:--:|
| Compliance Manager | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |
| Commissioning Manager | ✓ | ✓ | ✗ | ✗ | ✓ | ✗ |
| Compliance User | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| AssetCore Super Admin | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

> DocPerm trên là từ thiết kế (07 cũ + workflow role); cần đối chiếu lại với `.json` DocPerm thực tế khi audit security — *(Cần khảo sát: xác nhận permlevel field nhạy cảm trong từng .json)*.

- **Field-level permission** (permlevel ≠ 0): cần áp cho field nhạy cảm như `waiver_reason`/`waiver_evidence`, `score_pct` sau publish, `effectiveness_check`. *(Cần khảo sát — chưa xác nhận permlevel trong .json.)*
- **User Permission**: filter row theo department cho Finding/CAPA. *(Cần khảo sát.)*

## VI.2. API security

- **Whitelist hygiene**: `api/imm16.py` có 52 `@frappe.whitelist`; service layer dùng `_require_qa_or_admin()` (16 call site trong `services/imm16.py`) cho action nhạy cảm. Cần xác nhận mọi endpoint mutating có role check.
- **CSRF**: Frappe default `X-Frappe-CSRF-Token` cho POST endpoint (`methods=["POST"]`).
- **Input validation**: Link field validate qua `frappe.get_value` / `frappe.db.exists` trước khi dùng; JSON args parse an toàn.
- **SQL injection**: parameterized only; gate query (`check_asset_compliance_status`) phải dùng param, không f-string. *(Cần khảo sát: audit raw SQL trong service.)*
- **Rate limit**: cho endpoint mutating (create, publish, finalize_mr) — *(Cần khảo sát.)*

## VI.3. Audit trail integrity

Mọi mutation Finding/CAPA/Audit/Rule/Scorecard sinh `IMM Audit Trail` qua `_log_record_event → utils.lifecycle.log_audit_event` (BR-16-10) + `track_changes=1` (Frappe Version). Hash SHA-256 chain. User KHÔNG có quyền edit/delete `IMM Audit Trail` (DocPerm read-only + ISO 13485:7.5.9). → tham chiếu III.5 test cases (`test_confirm_finding_writes_audit_trail` ✅ Live; tamper test ⬜ Planned).

## VI.4. Authentication & session

Login Frappe default. Session timeout + lockout + password policy theo cấu hình site. API key rotation. 2FA: roadmap (out-of-scope module).

## VI.5. Data sensitivity

| Loại | Trường | Sensitivity | Bảo vệ |
|---|---|---|---|
| Lý do/evidence miễn trừ | `waiver_reason`, `waiver_evidence` | Confidential | File `is_private=1`, DocPerm write hạn chế |
| Kết quả tuân thủ | `score_pct`, `effectiveness_check` | Internal | Immutable sau publish (VR-09) |
| Audit trail | `IMM Audit Trail` | Restricted | Read-only, hash chain |

KHẲNG ĐỊNH: module IMM-16 KHÔNG lưu patient/clinical data.

## VI.6. Vendor isolation

IMM-16 là module nội bộ QMS — không có actor Vendor External truy cập trực tiếp. Persona ngoài (PM/Corrective User) chỉ Read và chịu gate BR-16-09; KHÔNG thấy chi phí, không edit Finding/Scorecard, không export audit trail. → tham chiếu III.6 (low-role API call test ⬜ Planned).

## VI.7. Secrets management

Cấm commit `.env` / credential. `site_config.json` không lên git. External token lưu `frappe.conf`. Backup encrypt at-rest off-site.

## VI.8. Logging & monitoring

| Sự kiện | Log level | Where | Alert? |
|---|---|---|---|
| Waive / publish / finalize_mr | INFO + audit trail | `IMM Audit Trail` | No |
| CAPA Critical > 30 ngày escalate | WARNING | scheduler log + email VP Block2 | Yes |
| Scheduler eval fail | ERROR | `frappe error log` | Yes |
| Gate block WO (BR-16-09) | INFO | audit trail | No |

PII / token KHÔNG vào log.

## VI.9. Threat model (STRIDE-lite)

| Threat | Vector | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| **Spoofing** | Giả role Commissioning Manager để waive Finding | Thấp | Cao | Frappe session auth + role check `waive_finding` (workflow role + `_require_qa_or_admin`) |
| **Tampering** | Sửa `score_pct` trên Published Scorecard | TB | Cao | VR-09 `validate_scorecard_immutability` + write=0 sau publish |
| **Tampering** | Bypass gate BR-16-09 gọi WO submit trực tiếp | TB | Cao | `gate_wo_submit` hook trong `doc_events` IMM-08/09 — không bypass được |
| **Repudiation** | Phủ nhận đã waive Finding | Thấp | TB | `IMM Audit Trail` hash chain + Frappe Version (immutable) |
| **Info disclosure** | Xem CAPA Critical list qua API không auth | TB | TB | `@frappe.whitelist()` yêu cầu logged-in session; dept filter |
| **Denial of service** | Flood scheduler `evaluate_all_compliance_rules` | Thấp | TB | Job dedup (idempotent upsert) + scheduler interval cố định |
| **Elevation of privilege** | Compliance User cố finalize MR (chỉ Commissioning Mgr) | TB | Cao | Role check tại API + workflow transition role |

## VI.10. Penetration test

Trước release đầu tiên: Burp/ZAP scan, sqlmap (an toàn) trên gate query, CSRF test POST endpoint, role escalation (waive/publish/finalize). Report lưu `docs/security/`. *(Chưa thực hiện — Cần khảo sát.)*

## VI.11. Sign-off

| Role | Người | Ngày | Chữ ký |
|---|---|---|---|
| QA Lead | *(chưa ký)* | | |
| Security Officer | *(chưa ký)* | | |
| Module Owner (Tổ HC-QLCL & Risk) | *(chưa ký)* | | |

Decision: ☐ Pass · ☐ Pass with conditions · ☐ Fail (block).

---

# Phần VII — Code Quality

## VII.1. Tool matrix

| Tool | Mục tiêu | Target | Cadence |
|---|---|---|---|
| **SonarQube** (BE Python) | bug / code smell / duplication / coverage | 0 critical bug, code smell ≤ N, duplication ≤ 3%, coverage ≥ 70%, security hotspot review 100% | mỗi PR (CI gate) |
| **ruff** (BE Python) | lint + format | 0 error; select `E,W,F,I,B,C4,UP`, ignore `E501` | mỗi PR |
| **mypy** (BE) | type check | strict cho `assetcore.services.imm16*`, `assetcore.api.imm16` | mỗi PR |
| **ESLint + vue-tsc** (FE) | type + lint | 0 error, 0 warning prod build; `no-explicit-any: error` | mỗi PR |
| **Lighthouse** (FE) | web vitals | Performance ≥ 90, Accessibility ≥ 95, Best Practices ≥ 90, SEO ≥ 80 | mỗi release lớn + monthly |
| **Bundle size** (FE chunk compliance) | budget | main ≤ 250KB gzip, async ≤ 80KB gzip | mỗi PR FE |

## VII.2. Cadence

- SonarQube: mỗi PR (CI gate, fail nếu Quality Gate fail).
- Lighthouse: mỗi release lớn + monthly audit.
- ESLint / ruff / mypy: mỗi PR (CI gate, fail fast).
- Bundle size: mỗi PR FE (CI report, fail nếu vượt budget).

**Code review checklist (IMM-16 specific)** — trước mỗi PR merge:
- Service layer không gọi Frappe DB trực tiếp trong controller.
- Mọi API endpoint có `@frappe.whitelist()` + role check.
- Mọi action mutation ghi `IMM Audit Trail`.
- `_compare_values()` không side effect.
- `generate_scorecard` idempotent với cùng period.
- `check_asset_compliance_status` return `{blocked, reasons}`, không raise.
- CAPA hook không break suite IMM-12 (DocType shared).
- TypeScript strict — không `any`.

> Gắn screenshot SonarQube + Lighthouse vào file 09 §Release Notes khi báo cáo final.

---

# Phụ lục A — Template per UAT scenario

```markdown
### UAT-IMM16-<NN> — <Tên>

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
### TC-IMM16-<LAYER>-<NN> — <Tên>

**Component (I.1)**: <…>
**Liên kết**: US-<NN> | BR-<NN> | ACT-<NN>
**Kỹ thuật (II.1/II.2)**: BVA boundary `waiver_reason length = 49`
**Priority (I.3)**: Critical / High / Medium / Low
**Test type**: Unit / Integration / API / E2E
**Pre-condition**: <fixture / state setup>

**Input**:
- <field>: <value>

**Steps**:
1. <…>
2. <…>

**Expected**:
- ServiceError(code=VALIDATION, message contains "VR-04")
- doc.workflow_state unchanged

**Post-condition**: <DB rollback / fixture cleanup>
```

# Phụ lục C — Workflow State Transition Test template

```markdown
### TC-IMM16-WF-<NN> — <action>: <from> → <to>

**Workflow JSON**: `workflow/imm_16_<…>_workflow.json`
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
- [x] Test class structure cho service public function (I.1) — 12 class LIVE
- [ ] ≥ 1 happy + 1 negative test mỗi function — còn gap (`_compare_values`, `generate_scorecard` formula, `mark_false_positive`, scheduler idempotency chưa có unit)
- [ ] Workflow transitions cover 100% (18 transition) — hiện ⬜ Planned, chưa viết `test_imm16_workflow.py`
- [ ] Audit chain test (intact + tampered) — chỉ intact một phần (`test_confirm_finding_writes_audit_trail`); tamper test ⬜ Planned
- [ ] API test ≥ 60% coverage + permission matrix — `test_imm16_api.py` ⬜ Planned
- [x] Performance target xác định (III.8 — target, chưa benchmark)
- [x] CI command chạy clean (`bench run-tests --module assetcore.tests.test_imm16`)
- [ ] **SonarQube Quality Gate pass** + **Lighthouse score ≥ target** — chưa chạy/đo

## IV. Traceability
- [x] IV.1 US → Test: mọi US có ≥ 1 Test ID
- [ ] IV.2 BR → Test: mọi BR có happy + negative — một số BR thiếu nửa còn lại (đánh dấu ⬜)
- [ ] IV.3 Component → Test: Critical/High đạt coverage target — coverage % chưa đo; `_compare_values` chưa có test

## V. UAT
- [x] Mỗi US có ≥ 1 UAT scenario (12 scenario)
- [x] ≥ 1 negative + permission + audit verify scenario (UAT-07/10/11)
- [ ] Test data seed script chạy được — `scripts/uat/uat_imm16.py` chưa xác nhận
- [x] Tester accounts đã định nghĩa (đủ role, có role thấp `test_biomed`)
- [x] Sign-off section sẵn sàng

## VI. Security
- [x] DocPerm matrix đầy đủ (6 DocType, Decision Table)
- [ ] Mọi field nhạy cảm có permlevel ≠ 0 — chưa xác nhận trong .json
- [ ] SQL injection + CSRF test pass — chưa thực hiện (penetration ⬜)
- [ ] Audit chain test pass (intact + tampered) — tamper ⬜ Planned
- [ ] Vendor isolation test pass (low-role API call) — ⬜ Planned
- [x] Threat model đủ 7 mục STRIDE với mitigation
- [ ] Sign-off đầy đủ trước go-live — chưa ký

## VII. Code Quality
- [ ] SonarQube Quality Gate pass — chưa chạy
- [ ] Lighthouse ≥ target — chưa đo
- [ ] Bundle size ≤ budget — chưa đo
- [ ] Screenshot báo cáo gắn vào file 09 — chưa có
