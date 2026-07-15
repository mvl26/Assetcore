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
| US-16-06 | Compliance Scorecard sinh tự động | AC1 (formula BR-16-11: `compute_compliance_rate` SoT, pending KHÔNG vào mẫu số), AC2 (immutability), AC3 (scorecard + heatmap CÙNG dataset → CÙNG score), AC4 (BR-16-12: cả 2 lọc kỳ theo CÙNG field `evaluation_date` — parity thật trên dataset detected_date≠evaluation_date) | Unit + UAT |
| US-16-07 | Waive Finding (BR-16-06) | AC1..AC3 (reason/evidence/expiry), AC4 (role) | Unit + API + UAT |
| US-16-08 | Gate IMM-08/09 (BR-16-09) | AC1 (block), AC2 (unblock) | Unit + Integration + UAT |
| US-16-09 | Management Review quý | AC1 (finalize gate), AC2 (MR gate scorecard) | Unit + UAT |
| US-16-10 | Compliance Heatmap | AC1 (render), AC2 (drill-down) | E2E (UAT) |

### I.2.b. Từ Business Rule
| BR ID | Phát biểu (rút gọn) | Component liên quan (I.1) | Kỹ thuật test phù hợp |
|---|---|---|---|
| BR-16-01 | Finding severity ≥ High → mở CAPA trong 5 NLV | #11, #21 (`check_capa_due`) | EP + Use Case |
| BR-16-02 | CAPA quá hạn → escalate tiered ĐỘC LẬP (Critical ≥1d/≥3d, High ≥3d, Medium/Low none) — effective-risk SoT + idempotent | #11 (`_escalate_capa` / `_capa_escalation_severity`), #21 | BVA (biên 0/1/2/3 ngày × risk) + Decision Table |
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
| `TestCapaEscalation::*` (`test_imm16_capa_escalation.py`, TC-CAPA-ESC-01..08, 11 test) | #11 `_escalate_capa` / `_capa_escalation_severity` / `_severity_to_risk` / `_record_capa_escalation` / `check_capa_due` (BR-16-02, RC-CAPA-ESC) | BVA + Decision Table | 4 happy / 7 boundary-neg | ✅ Live (Vòng 13) |

### III.2c. CAPA Escalation BVA matrix (BR-16-02 — Vòng 13)

> Fixture isolated `_TestCapaEsc-*` (asset + CAPA self-contained, teardown purge). Mock `_safe_sendmail` (đếm call) + spy `frappe.db.get_value`. Backdate `due_date` để set `overdue_days` chính xác. RED-prove: khôi phục `if/elif` cũ ⇒ TC-ESC-01 FAIL (level=2 count 0).

| Test ID | Setup (effective-risk, overdue) | escalation_level trước | Kỳ vọng | Invariant |
|---|---|---|---|---|
| **TC-ESC-01** (BUG-1 chính) | `imm_risk_level=Critical`, =3d | 0 | `_send_capa_escalation(level=2)` count ≥1 (đồng thời level=1); `escalation_level→2` | INV-CAPA-ESC-1 |
| **TC-ESC-02** (BUG-2) | `severity=Critical`, `imm_risk_level=''`/`Medium`, =1d | 0 | escalate L1 (effective-risk='Critical' qua fallback severity) | INV-CAPA-ESC-2 |
| **TC-ESC-03** | Critical, =0d | 0 | KHÔNG escalate (no sendmail) | BVA biên 0 |
| **TC-ESC-04** | Critical, =1d | 0 | CHỈ Level-1 (`escalation_level→1`) | BVA |
| **TC-ESC-05** | Critical, =2d | 0 | VẪN chỉ Level-1 (chưa Level-2) | BVA biên 2 |
| **TC-ESC-06** | Critical, =3d | 1 (đã L1) | CHỈ gửi Level-2 mới (L1 không re-send) | INV-CAPA-ESC-3 |
| **TC-ESC-07** (BUG-3 idempotency) | Critical, =3d | 0 | chạy `check_capa_due` 2×: lần 2 `_safe_sendmail` call-count BẤT BIẾN; audit không trùng | INV-CAPA-ESC-3 |
| **TC-ESC-08** | `imm_risk_level=High`, =2d | 0 | KHÔNG escalate | BVA-HIGH biên 2 |
| **TC-ESC-09** | High, =3d | 0 | Level-2 (`escalation_level→2`) | BVA-HIGH |
| **TC-ESC-10** | Medium / Low, =5d | 0 | KHÔNG escalate bất kỳ ngày | BVA-LOWMED neg |
| **TC-ESC-11** (BUG-4 N+1) | Critical, =3d (qua `check_capa_due`) | 0 | spy `frappe.db.get_value` = 0 lần trong `_escalate_capa` (đọc từ row select) | INV-CAPA-ESC-4 |

**No-regression bắt buộc:** `test_imm16` + `test_imm16_compliance_gate_sot` + `test_capa_overdue_sot` + `test_capa_open_sot` GREEN; `_overdue_capa_filter` / `check_capa_overdue` SoT BẤT BIẾN (round này KHÔNG đụng); `api/imm16.py` delegate verbatim.

**Gap (⬜ Planned)**: chưa có unit riêng cho `_compare_values` (threshold BVA/EP toàn matrix op), `create_capa_from_finding`, `mark_false_positive`, scheduler idempotency của `evaluate_all_compliance_rules`.

**Regression bắt buộc (BR-16-11 — score_pct mẫu số adjudicated):** dataset `1×Confirmed NC + 1×Open + 1×Resolved` qua `compute_compliance_rate()`:
- assert `total_adjudicated == 2`, `compliant == 1`, `non_compliant == 1`, `pending == 1`
- assert `score_pct == 50.0` (KHÔNG phải 66.67 của công thức cũ `(total-nc)/total`)
- assert `compute_compliance_rate([]) → score_pct == 100.0` (adjudicated=0 semantics)
- assert scorecard `generate_scorecard()` và `get_compliance_heatmap()` cùng dataset → cùng score (no divergence; grep xác nhận KHÔNG còn `(total - nc) / total` inline ở 2 nơi)
- VR-09 immutability KHÔNG hồi quy: publish → `score_pct`/`non_compliant_count` immutable vẫn pass.

**Regression bắt buộc (BR-16-12 — period-anchor PARITY THẬT):** test parity cũ `test_tdd5_scorecard_heatmap_parity` là FALSE-GREEN vì ép CẢ `evaluation_date` VÀ `detected_date` vào cùng kỳ → divergence không bao giờ lộ. Test parity THẬT phải pin 2 date KHÁC kỳ:
- dataset có ≥1 Confirmed-NC với `detected_date` ở kỳ T2 (`2027-02-25`) nhưng `evaluation_date` ở kỳ T3 (`2027-03-05`) — mô phỏng lag adjudication thực tế.
- assert `generate_scorecard("", "2027-02")` score == `get_compliance_heatmap(2027, 2)` cell.score cho cùng module → kỳ T2 finding này KHÔNG đếm ở CẢ 2 view (cả 2 = 100.0 nếu không có NC khác trong T2).
- assert `generate_scorecard("", "2027-03")` score == heatmap T3 cell.score cho cùng module → finding chỉ thuộc T3 ở CẢ 2 view, score giống nhau.
- **RED-experiment**: revert anchor heatmap về `detected_date` → test FAIL đúng symptom (T2 heatmap đếm finding NC trong khi scorecard T2 không, score lệch) → chứng minh test bắt được bug thật, không phải false-green.

> *Lưu ý*: dùng `SimpleNamespace` cho test thuần công thức (`_compare_values`, score_pct) — chạy ms-level, không cần fixture cleanup. Test period-anchor cần fixture committed (set cả 2 cột date qua `frappe.db.set_value`) + purge cả 2 kỳ T2+T3 ở `addCleanup`.

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

## III.4b. Server-driven CTA — `allowed_transitions` + `can_create_capa` (GATE-8 / LL-FE-51)

**BE — `TestFindingAllowedTransitions` (test_imm16), đối xứng `test_imm09.TestRepairAllowedTransitions`:**

| # | Kiểm | Kỳ vọng |
|---|---|---|
| AT-16-1 | `get_finding` trên finding **Open** | `allowed_transitions == ['Under Review','Confirmed NC','False Positive','Waived']` *(round 14 +Under Review)* |
| AT-16-1b | `get_finding` trên **Under Review** | `allowed_transitions == ['Confirmed NC','False Positive','Waived']` (KHÔNG có 'Under Review') |
| AT-16-2 | `get_finding` trên Confirmed NC (chưa có capa_ref) | `allowed_transitions == ['Waived']` · `can_create_capa == True` |
| AT-16-3 | `get_finding` trên Confirmed NC (đã có capa_ref) | `can_create_capa == False` |
| AT-16-4 | `get_finding` trên False Positive / Resolved / Waived / Closed | `allowed_transitions == []` · `can_create_capa == False` |
| AT-16-5 | Codomain toàn map ⊆ `FindingStatus` enum (chống typo/drift) | mọi target ∈ enum |
| AT-16-6 | Map keyed đủ 7 status; terminal → `[]` | invariant |
| AT-16-7 (guard) | `confirm_finding` / `mark_false_positive` từ status ∉ `REVIEWABLE` | raise `BAD_STATE` (HTTP-200 Error envelope) |
| AT-16-8 (guard) | `waive_finding` từ status ∉ `WAIVABLE` (vd Closed) | raise `BAD_STATE` |
| AT-16-9 (invariant) | ∀status: `allowed_transitions[status] ⊆ {đích guard cho phép}` | map ⊆ guard-permitted |
| **AT-16-10 (lockstep, RED→GREEN)** | tạo Finding Open (`status='Open'`, `workflow_state='Open'`) → `confirm_finding` → reload | `status=='Confirmed NC'` **AND** `workflow_state=='Confirmed NC'` |
| AT-16-11 (lockstep) | Finding Open → `mark_false_positive` → reload | `status==workflow_state=='False Positive'` |
| AT-16-12 (lockstep) | Finding Under Review → `waive_finding` (VR-04 hợp lệ) → reload | `status==workflow_state=='Waived'` |
| AT-16-13 (lockstep) | Finding Confirmed NC → `close_finding` → reload | `status==workflow_state=='Resolved'` |
| AT-16-14 (lockstep cascade) | CAPA (`source_type='Compliance Finding'`) → Closed → cascade | Finding `status==workflow_state=='Resolved'` |
| **AT-16-15 (start_review, RED→GREEN)** | Finding Open → `start_review` → reload | `status==workflow_state=='Under Review'` |
| AT-16-16 (start_review guard) | `start_review` từ status ≠ Open (vd Under Review/Confirmed NC) | raise `BAD_STATE` |
| **AT-16-17 (INVARIANT map⇄workflow, RED→GREEN)** | set-diff `codomain(_FINDING_VALID_TRANSITIONS)` ⇄ `next_state` graph `imm_16_finding_workflow.json` | `codomain − wf_next == ∅` · `wf_next − codomain == {Resolved, Closed}` = `EXCEPTION_EDGES` · `{Confirmed NC,False Positive,Waived,Resolved,Under Review} ⊆ wf_next` (§III.B.2 INV-16-A/B/C). RED trước round: `Under Review` ∉ EXCEPTION_EDGES ⇒ FAIL |

**FE — `findingDetailCtaGating.test.ts` (vitest):**

| # | Kịch bản (mock `getFinding`) | Kỳ vọng render |
|---|---|---|
| FE-16-1 | `compliance.write` + `allowed_transitions=['Confirmed NC','False Positive','Waived']` | 3 nút Xác nhận/Đánh dấu-sai/Miễn áp dụng HIỆN |
| FE-16-2 | Confirmed NC, `allowed_transitions=['Waived']`, `can_create_capa=true` | Xác nhận/Đánh dấu-sai ẨN; Miễn áp dụng + Tạo CAPA + Liên kết CAPA HIỆN |
| FE-16-3 | `can_create_capa=false` (đã có capa_ref) | Tạo/Liên kết CAPA ẨN |
| FE-16-4 | terminal `allowed_transitions=[]` | 0 CTA đổi trạng thái |
| FE-16-5 | THIẾU `compliance.write` (bất kỳ status) | mọi CTA ẨN |
| FE-16-6 | field `allowed_transitions`/`can_create_capa` VẮNG (worker cũ) | CTA ẨN, KHÔNG crash (`?? []` / `?? false`) |
| FE-16-7 | grep-guard: `FindingDetailView.vue` KHÔNG còn `finding.status ===` / `.includes(finding.status)` | 0 match |
| FE-16-8 *(round 14)* | `compliance.write` + `allowed_transitions=['Under Review','Confirmed NC','False Positive','Waived']` | +nút "Bắt đầu xem xét" HIỆN; 3 CTA cũ KHÔNG regress |

**DoD round (CR-WF-16-FIND):** `bench --site miyano run-tests --module assetcore.tests.test_imm16` **VÀ** `...test_workflows` → `Ran N OK` THẬT (đọc dòng cuối, KHÔNG false-green); AT-16-10..17 RED-before/GREEN-after; `findingDetailCtaGating.test.ts` xanh (FE KHÔNG regress); `vue-tsc` sạch. **Non-regress:** `test_workflow_admin_override` (root cause #1, Super Admin+System Manager mọi edge) GREEN 22/22 KHÔNG đổi — KHÔNG sửa `imm_16_finding_workflow.json`/fixtures ⇒ 0 reload/migrate. Nếu BE chọn đổi workflow JSON = HARD-STOP USER.

## III.4c. Server-driven CTA — Internal Audit lifecycle (ADR-IMM-16-02, GATE-8 / LL-FE-51)

**BE — `TestAuditAllowedTransitions` (test_imm16), đối xứng `TestFindingAllowedTransitions`:**

| # | Kiểm | Kỳ vọng |
|---|---|---|
| AA-16-1 | `get_audit` trên Planned | `allowed_transitions == ['start']` |
| AA-16-2 | `get_audit` trên In Progress | `allowed_transitions == ['complete_checklist']` |
| AA-16-3 | `get_audit` trên Reporting | `allowed_transitions == ['close']` |
| AA-16-4 | `get_audit` trên Closed | `allowed_transitions == []` |
| AA-16-5 | `get_audit` status rỗng/lạ | `allowed_transitions == []` — KHÔNG `KeyError` (safe-default `.get`) |
| AA-16-6 | `get_audit` với cap `compliance.write`/`compliance.submit` | `can_operate`/`can_close` khớp `rbac.can(...)` |
| AA-16-7 | `complete_audit_checklist` từ **In Progress** | `status == Reporting` sau gọi (state Reporting sống lại) |
| AA-16-8 (guard) | `complete_audit_checklist` từ **Planned** (chưa start) | raise `BAD_STATE` (bỏ nhánh Planned) |
| AA-16-9 (guard) | `close_audit` từ **Planned / In Progress** | raise `BAD_STATE` "Audit phải ở trạng thái Reporting…" (VR-13, chặn jump-skip) |
| AA-16-10 | `close_audit` từ Reporting, còn Major NC chưa CAPA | raise `FIN-008` (VR-08) |
| AA-16-11 | `close_audit` từ Reporting, sạch Major NC | `status == Closed` |
| AA-16-12 (audit-trail) | Mỗi `start_audit`/`complete_audit_checklist`/`close_audit` | đếm `IMM Audit Trail` (`ref_name`, `event_type` tương ứng) **tăng ĐÚNG 1** |
| **AA-16-13 (guard-detect, R22 — CR-WF-16-AUDIT)** | legacy `submit_audit_findings` từ **Planned** | raise `BAD_STATE` (siết linear — bỏ nhánh Planned; In Progress vẫn → Reporting). RED-before: guard cũ `not in (IN_PROGRESS, PLANNED)` cho skip-start |
| **AA-16-14 (guard-detect)** | legacy `close_internal_audit` từ **Planned / In Progress** | raise `BAD_STATE` (siết linear — chỉ từ Reporting, VR-13 parity; Reporting → Closed OK). RED-before: guard cũ `== CLOSED` cho close-từ-non-Closed |
| **AA-16-15 (round-trip, CR-27b — RED→GREEN)** | `complete_audit_checklist(items=[{idx, finding_status}])` cho 3 mục (`Compliant`/`Major NC`/`N/A`) rồi **re-fetch `get_audit`** | mỗi `checklist_items[i].result` = `{Conforming, Non-Conforming, Not Applicable}` tương ứng, **KHÔNG rỗng**. **RED-before THẬT:** trước fix (assign `child.finding_status` no-op) → `result` rỗng ⇒ FAIL; sau map → GREEN |
| **AA-16-16 (unknown finding_status)** | item đã có `result="Conforming"`, gọi với `finding_status="???"` (lạ/thiếu) | `result` GIỮ `"Conforming"` — KHÔNG overwrite bằng giá trị lạ (`.get()`→None→skip) |
| **AA-16-17 (0-regression)** | `complete_audit_checklist` với 1 `Major NC` | `findings_created==1` (KHÔNG đổi) · `status==Reporting` · `notes` persist · `IMM Audit Trail` tăng ĐÚNG 1 (`audit_checklist_completed`) |

**BE — `TestChecklistVerdictMapInvariant` (test_imm16, CR-27b) — parse trực tiếp `imm_audit_checklist_item.json`, KHÔNG DB fixture (pure structural, drift-proof):**

| # | Kiểm | Kỳ vọng |
|---|---|---|
| INV-CHK-1 (why-no-op) | field_order/fields của `imm_audit_checklist_item.json` | **KHÔNG chứa** `finding_status` **và** `clause_ref` — chứng minh 2 assign cũ `hasattr(child,…)` là no-op câm (⇒ vì sao cần map sang `result`) |
| INV-CHK-2 (map⊆options) | `set(_FINDING_STATUS_TO_RESULT.values())` ⊆ options Select `result` (parse từ field `result.options` split `\n`, bỏ rỗng) | `⊆ {Conforming, Non-Conforming, Not Applicable}` — drift-proof: đổi Select HOẶC map lệch ⇒ FAIL |
| INV-CHK-3 (domain-DTO) | `set(_FINDING_STATUS_TO_RESULT.keys())` | `== {Compliant, Minor NC, Major NC, N/A}` = DTO enum FE (`frontend/src/api/imm16.ts:378`) — chống rơi enum khi FE thêm option |

**BE — `TestAuditWorkflowInvariant` (test_imm16, round 22 — CR-WF-16-AUDIT), reconcile-guard `_AUDIT_VALID_TRANSITIONS` ⇄ `imm_16_internal_audit.json` QUA resolver `_AUDIT_ACTION_TO_NEXT_STATE` — ĐÓNG NỐT quartet (Finding R14 / CAPA R19 / MR R20 + Internal Audit R22). KHÁC 3 workflow kia: map codomain = ACTION-KEY ⇒ resolver bắc cầu action→state. Pure map+resolver+JSON parse, KHÔNG DB fixture (§III.C.2 / ADR-IMM-16-09):**

| # | Kiểm | Kỳ vọng |
|---|---|---|
| INV-AUD-1 (keys==states) | `set(_AUDIT_VALID_TRANSITIONS.keys())` ⇄ `states[]` workflow JSON | `== {Planned, In Progress, Reporting, Closed}` (4-state) |
| INV-AUD-2 (resolver==3-handler) | `set(_AUDIT_ACTION_TO_NEXT_STATE.keys())` | `== {start, complete_checklist, close}` = 3 canonical handler whitelisted |
| INV-AUD-3 (no-orphan-action) | `codomain(_AUDIT_VALID_TRANSITIONS) − keys(resolver)` | `== ∅` (mọi action advertise dịch được → state) |
| INV-AUD-4 (values⊆enum) | `values(_AUDIT_ACTION_TO_NEXT_STATE) ⊆ AuditStatus enum` | True; + oracle độc-lập `{PLANNED,IN_PROGRESS,REPORTING,CLOSED} == 4-state literal` |
| **INV-AUD-5 (per-state, RED→GREEN)** | ∀ state: `{resolver[a] for a in map[state]}` ⇄ `{next_state cạnh workflow từ state}` (deduped 9-entry→3-cạnh) | Aligned: `Planned→{In Progress}`, `In Progress→{Reporting}`, `Reporting→{Closed}`, `Closed→∅`. **RED-before THẬT:** đổi 1 entry resolver (`start→Reporting`) HOẶC thêm `'close'` vào `map[In Progress]` ⇒ FAIL `'DRIFT <state>: map ≠ workflow'`; revert → GREEN |

**DoD round 22 (CR-WF-16-AUDIT reconcile-guard):** `bench --site miyano run-tests --module assetcore.tests.test_imm16` → `Ran N OK` THẬT (đọc DÒNG CUỐI, KHÔNG FAIL/ERROR/skip che — verified `Ran 101 OK`); INV-AUD-1..5 GREEN với **RED-before chứng minh THẬT** (resolver `start→Reporting` → INV-AUD-5 FAIL `'DRIFT Planned: map ≠ workflow (map→[Reporting] vs workflow→[In Progress])'` → revert GREEN); AA-16-13/14 guard-detect GREEN. **Non-regress (KHÔNG đụng):** `TestAuditServerDrivenLifecycle` (AA-16-1..12) + `TestFinding/Capa/MrWorkflowInvariant` + `test_workflow_admin_override` (`TestWorkflowAdminOverride` + `TestSourceWorkflowFiles`, `Ran 10 OK` — 22-workflow admin coverage) vẫn xanh; `internalAuditCtaGate.test.ts` **10 passed** (FE 0-change round này). **0 workflow-JSON / fixtures change ⇒ 0 reload/migrate** (map ⇄ workflow đã in-sync qua resolver). ⚠️ 2 guard legacy siết = service runtime → **cần worker reload để LIVE** (HARD-STOP USER deploy); test-runner re-import fresh nên verify GREEN không cần reload. Nếu buộc đổi workflow JSON = HARD-STOP USER.

**FE — `internalAuditCtaGate.test.ts` (vitest):**

| # | Kịch bản (mock `getAudit`) | Kỳ vọng render |
|---|---|---|
| FA-16-1 | Planned + `can_operate=true`, `allowed_transitions=['start']` | nút **Bắt đầu** HIỆN; editor bảng kiểm + Đóng ẨN |
| FA-16-2 | In Progress + `can_operate=true`, `allowed_transitions=['complete_checklist']` | **editor bảng kiểm** HIỆN; Bắt đầu + Đóng ẨN |
| FA-16-3 | Reporting + `can_close=true`, `allowed_transitions=['close']` | nút **Đóng** HIỆN; Bắt đầu + editor ẨN |
| FA-16-4 | Reporting + `can_close=false` (chỉ `can_operate`) | nút Đóng ẨN (gate `can_close`) |
| FA-16-5 | Closed / `allowed_transitions=[]` | 0 CTA |
| FA-16-6 | 3 field VẮNG (worker cũ) | 0 CTA, KHÔNG crash (`?? []` / `?? false`) |
| FA-16-7 (anti-dead-control) | click Bắt đầu/Hoàn tất/Đóng | gọi `startAudit`/`completeAuditChecklist`/`closeAudit` đúng tên |
| FA-16-8 (grep-guard) | `InternalAuditDetailView.vue` KHÔNG còn `audit.status ===` / `.includes(audit.status)` | 0 match |

**DoD round:** `bench --site miyano run-tests` module test_imm16 → `Ran N OK`; `internalAuditCtaGate.test.ts` xanh; `vue-tsc` prod 0 error.

## III.4d. Server-driven CTA — CAPA lifecycle (ADR-IMM-16-03, GATE-8 / LL-FE-51)

**BE — `TestCapaAllowedTransitions` (test_imm16), đối xứng `TestFindingAllowedTransitions`/`TestAuditAllowedTransitions`:**

| # | Kiểm | Kỳ vọng |
|---|---|---|
| AC-16-1 | `get_capa` (caller có `compliance.write`) trên Open | `allowed_transitions == ['Investigating']` · `can_advance == True` |
| AC-16-2 | `get_capa` trên Investigating / Action Plan / Implementation | `== ['Action Plan']` / `['Implementation']` / `['Verification']` |
| AC-16-3 | `get_capa` trên Verification | `allowed_transitions == ['Closed', 'Re-opened']` (sorted) |
| AC-16-4 | `get_capa` trên Re-opened | `allowed_transitions == ['Investigating']` |
| AC-16-5 | `get_capa` trên Closed | `allowed_transitions == []` (terminal, safe-default `.get`) |
| AC-16-6 (quyền) | `get_capa` caller **KHÔNG** có `compliance.write` (∀ state) | `allowed_transitions == []` · `can_advance == False` |
| AC-16-7 (full-quyền) | `get_capa` user full AssetCore (`AssetCore Super Admin`, có `compliance.write`) ở state hợp lệ | `allowed_transitions` KHÔNG rỗng · `can_advance == True`; `advance_capa_state` sau đó KHÔNG raise `FORBIDDEN` |
| AC-16-8 (invariant emit=domain) | ∀ state S (có quyền): `set(get_capa(S).allowed_transitions) == _CAPA_TRANSITIONS.get(S, set())` | emit = guard-domain, KHÔNG lệch (1 SoT) |
| AC-16-9 (invariant hint⊆guard) | ∀ T ∈ `get_capa(S).allowed_transitions`: `advance_capa_state(S, T)` | KHÔNG raise `INVALID_STATE "Không thể chuyển từ S sang T"` (validation downstream VR-05/12 được phép) |
| AC-16-10 (guard giữ nguyên) | `advance_capa_state` với `target` KHÔNG ∈ `_CAPA_TRANSITIONS[current]` | raise `INVALID_STATE` (defense-in-depth, hint không thay guard) |

**BE — `TestCapaWorkflowInvariant` (test_imm16, round 19 — CR-WF-16-CAPA), reconcile-guard `_CAPA_TRANSITIONS` ⇄ `imm_16_capa_workflow.json`, đối xứng `TestFindingWorkflowInvariant`/`TestIncidentAllowedTransitions` — pure map+JSON parse, KHÔNG DB fixture (§III.D.2 / ADR-IMM-16-07):**

| # | Kiểm | Kỳ vọng |
|---|---|---|
| AT-16-CAPA-INV-1 (MAP⊆WF, edge) | `map_edges − wf_edges` (cạnh `(state,next)` map KHÔNG có trong workflow JSON deduped) | `== _CAPA_EXCEPTION_EDGES` (== ∅) — 0 CTA dead/bypass |
| **AT-16-CAPA-INV-2 (WF⊆MAP, edge, RED→GREEN)** | `wf_edges − map_edges` (cạnh workflow KHÔNG surface trong map) | `== _CAPA_EXCEPTION_EDGES` (== ∅) — 0 CTA câm. **RED-before:** strip `Re-opened` khỏi `_CAPA_TRANSITIONS["Verification"]` → `{("Verification","Re-opened")}` ≠ ∅ ⇒ FAIL message `'workflow có cạnh Verification→Re-opened KHÔNG surface (CTA câm)'`; restore → GREEN ⇒ set-diff 2 chiều == ∅ |
| AT-16-CAPA-INV-3 (codomain⊆7-state) | `(keys ∪ values)(_CAPA_TRANSITIONS) − {7 state hợp lệ}` | `== ∅` (chống typo/orphan; 7 = `states[]` workflow JSON) |
| AT-16-CAPA-INV-4 (terminal) | `"Closed" not in _CAPA_TRANSITIONS` ∧ `_CAPA_TRANSITIONS.get("Closed", set()) == set()` | True — get_capa(Closed) → `[]` (live-proof AC-16-5); loader DEDUPE cạnh lặp-theo-vai (21 entry → 7 cạnh) |

> **`_CAPA_EXCEPTION_EDGES = frozenset()`** đặt **test-level** (KHÔNG trong `services/imm16.py` — round TEST-ONLY, 0 service change). `_load_capa_workflow_edges()` parse `imm_16_capa_workflow.json` THẬT (`frappe.get_app_path`) + `set()` dedupe cạnh lặp theo vai. `map_edges` đọc `svc._CAPA_TRANSITIONS` VERBATIM (KHÔNG map thứ hai).

**FE — `capaCtaGate.test.ts` (vitest):**

| # | Kịch bản (mock `getCapaDetail`) | Kỳ vọng render |
|---|---|---|
| FC-16-1 | Open + `can_advance=true`, `allowed_transitions=['Investigating']` | nút **Bắt đầu điều tra** HIỆN; các CTA khác ẨN |
| FC-16-2 | Implementation + `allowed_transitions=['Verification']` | **Chuyển sang xác minh** HIỆN; khác ẨN |
| FC-16-3 | Verification + `allowed_transitions=['Closed','Re-opened']` | **Đóng CAPA** + **Mở lại** HIỆN (gate `.includes('Closed')`/`.includes('Re-opened')`) |
| FC-16-4 | Verification + `allowed_transitions=['Re-opened']` (không có 'Closed') | Mở lại HIỆN; Đóng CAPA ẨN (anti-`isVerification`-hardcode) |
| FC-16-5 | Closed / `allowed_transitions=[]` | 0 CTA; badge "đã đóng" |
| FC-16-6 | `can_advance=false`, `allowed_transitions=[]` (state chưa Closed) | 0 CTA; hint "không đủ quyền" |
| FC-16-7 | 2 field VẮNG (worker cũ) | 0 CTA, KHÔNG crash (`?? []` / `?? false`) |
| FC-16-8 (anti-dead-control) | click Bắt đầu điều tra / Chuyển sang xác minh | gọi `advanceCapaState(name,'Investigating')` / `('...','Verification')` đúng tên |
| FC-16-9 (anti-dead-control) | click Đóng CAPA / Mở lại | gọi `performEffectivenessCheck` (result Effective / Not Effective) |
| FC-16-10 (grep-guard) | `CAPADetailView.vue` KHÔNG còn `const TRANSITIONS` / `interface Transition` / `isVerification` / `workflow_state ===` | 0 match |

**DoD round:** `bench --site miyano run-tests` module test_imm16 → `Ran N OK`; `capaCtaGate.test.ts` xanh; `vue-tsc` prod 0 error; label CTA đầy đủ tiếng Việt (LL-FE-53); KHÔNG leak `workflow_state` raw/EN.

**DoD round 19 (CR-WF-16-CAPA reconcile-guard):** `bench --site miyano run-tests --module assetcore.tests.test_imm16` → `Ran N OK` THẬT (N tăng đúng +4 = `TestCapaWorkflowInvariant`; đọc DÒNG CUỐI, KHÔNG FAIL/ERROR/skip che); AT-16-CAPA-INV-1..4 GREEN với **RED-before chứng minh THẬT** (strip `Verification→Re-opened` → INV-2 FAIL → restore GREEN). **Non-regress (KHÔNG đụng):** `test_get_capa_allowed_transitions_by_state`@543 + `test_allowed_transitions_parity_with_advance_guard`@591 + `test_workflow_admin_override` (`TestWorkflowAdminOverride` + `TestSourceWorkflowFiles`) vẫn xanh. **0 service .py change, 0 workflow-JSON change, 0 reload, 0 migrate** (map đã in-sync 7-cạnh-khớp-1-1). Nếu BE thấy drift THẬT ⇒ fix map/JSON = HARD-STOP USER (không tự sửa workflow JSON).

## III.4e. Server-driven CTA — Management Review lifecycle (ADR-IMM-16-04, GATE-8 / LL-FE-51)

> Workflow IMM-16 **thứ 4/4 — cái DUY NHẤT chưa server-driven** trước vòng này. Đóng nốt parity với Finding/Audit/CAPA.

**BE — `TestMRAllowedTransitions` (test_imm16), đối xứng `TestCapaAllowedTransitions`:**

| ID | Given | Assert |
|---|---|---|
| AM-16-1 | `get_management_review` trên Draft | `allowed_transitions == ['Held']` |
| AM-16-2 | `get_management_review` trên Held | `allowed_transitions == ['Minutes Approved']` |
| AM-16-3 | `get_management_review` trên Minutes Approved | `allowed_transitions == ['Closed']` |
| AM-16-4 | `get_management_review` trên Closed | `allowed_transitions == []` (terminal, safe-default `.get`) |
| AM-16-5 | `get_management_review` status rỗng/lạ | `allowed_transitions == []` — KHÔNG `KeyError` |
| AM-16-6 (quyền) | user có `compliance.submit` | `can_advance == True` ∧ `can_close == True` |
| AM-16-7 (không quyền) | user thiếu `compliance.submit` | `can_advance == False` ∧ `can_close == False` (allowed_transitions vẫn phát theo status — gate cuối ở FE bằng cờ) |
| AM-16-8 (invariant emit=domain) | ∀ status S | `set(get_management_review(S).allowed_transitions) == set(_MR_TRANSITIONS.get(S, set()))` — emit = guard-domain, 1 SoT |
| AM-16-9 (invariant hint⊆guard) | ∀ T ∈ `allowed_transitions` | T≠'Closed' → `advance_mr_state(S,T)` KHÔNG raise `INVALID_STATE`; T=='Closed' → `finalize_management_review` KHÔNG raise `INVALID_STATE`; target ngoài `_MR_TRANSITIONS[S]` → `advance_mr_state` raise `INVALID_STATE` |
| AM-16-10 (QTV full-quyền, root-cause) | user CHỈ role `AssetCore Super Admin` | `can_advance==can_close==True`; `advance_mr_state` Draft→Held→Minutes Approved + `finalize_management_review` Closed đều KHÔNG raise `FORBIDDEN` (chứng minh "QTV duyệt/đóng được") |

**FE — `managementReviewCtaGate.test.ts` (vitest):**

| ID | Given | Assert |
|---|---|---|
| FM-16-1 | Draft + `can_advance=true`, `allowed_transitions=['Held']` | nút **Đánh dấu Đã họp** HIỆN; Phê duyệt + Đóng ẨN |
| FM-16-2 | Held + `can_advance=true`, `allowed_transitions=['Minutes Approved']` | nút **Phê duyệt Biên bản** HIỆN; khác ẨN |
| FM-16-3 | Minutes Approved + `can_close=true`, `allowed_transitions=['Closed']` | nút **Đóng và xuất biên bản** HIỆN; chuyển-cạnh ẨN |
| FM-16-4 | Closed / `allowed_transitions=[]` | 0 CTA; badge "Đã đóng" |
| FM-16-5 (dead-control) | bất kỳ status + `can_advance=false, can_close=false` | 0 CTA (KHÔNG hiện nút rồi 403); hint "không đủ quyền" |
| FM-16-6 (degrade) | 3 field VẮNG (worker cũ / BE lỗi) | 0 CTA, KHÔNG crash (`?? []` / `?? false`) |
| FM-16-7 (anti-dead-control) | click Đánh dấu Đã họp / Phê duyệt Biên bản | gọi `advanceMrState(name,'Held')` / `('...','Minutes Approved')` đúng tên |
| FM-16-8 (anti-dead-control) | click Đóng và xuất biên bản (modal minutes_doc + ≥1 action) | gọi `finalizeManagementReview(name, minutes_doc, actions)` |
| FM-16-9 (grep-guard) | `ManagementReviewDetailView.vue` KHÔNG còn `const NEXT_LABEL` / `nextStep` / `status === 'Minutes Approved'` | 0 match |

**DoD round:** `bench --site miyano run-tests` module test_imm16 → `Ran N OK`; `managementReviewCtaGate.test.ts` + suite hiện có xanh; `vue-tsc` prod 0 error; nhãn CTA khớp EXACT workflow JSON; KHÔNG leak `status` raw/EN.

### III.4e.INV. Reconcile-guard MR — `_MR_TRANSITIONS` ⇄ `imm_16_mr_workflow.json` (round 20 — CR-WF-16-MR)

> **Đóng nốt quartet reconcile IMM-16** (Finding R14 / CAPA R19 / MR R20). Guard bất-biến 2 chiều edge-by-edge, mirror `TestCapaWorkflowInvariant` (R19) / `TestFindingWorkflowInvariant` (R14) / `TestIncidentAllowedTransitions` (IMM-12 R12) — pure map+JSON parse, KHÔNG DB fixture (§III.F.2 / ADR-IMM-16-08).

**BE — `TestMRWorkflowInvariant` (test_imm16), đối xứng `TestCapaWorkflowInvariant`:**

| # | Kiểm | Kỳ vọng |
|---|---|---|
| AT-16-MR-INV-1 (MAP⊆WF, edge) | `map_edges − wf_edges` (cạnh `(state,next)` map KHÔNG có trong workflow JSON deduped) | `== _MR_EXCEPTION_EDGES` (== ∅) — 0 CTA dead/bypass |
| **AT-16-MR-INV-2 (WF⊆MAP, edge, RED→GREEN)** | `wf_edges − map_edges` (cạnh workflow KHÔNG surface trong map) | `== _MR_EXCEPTION_EDGES` (== ∅) — 0 CTA câm. **RED-before:** strip `Held→{Minutes Approved}` khỏi `_MR_TRANSITIONS` → `{("Held","Minutes Approved")}` ≠ ∅ ⇒ FAIL message `'workflow có cạnh Held→Minutes Approved KHÔNG surface (CTA câm — nút duyệt MR mất)'`; restore → GREEN ⇒ set-diff 2 chiều == ∅ |
| AT-16-MR-INV-3 (codomain⊆4-state) | `(keys ∪ values)(_MR_TRANSITIONS) − {Draft, Held, Minutes Approved, Closed}` | `== ∅` (chống typo/orphan; 4 = `states[]` workflow JSON). keys={Draft,Held,Minutes Approved} ∪ values={Held,Minutes Approved,Closed} = đúng 4 |
| AT-16-MR-INV-4 (terminal) | `"Closed" not in _MR_TRANSITIONS` ∧ `_MR_TRANSITIONS.get("Closed", set()) == set()` | True — get_management_review(Closed) → `[]` (live-proof AM-16-4/AM-16-5 @test:1044); loader DEDUPE cạnh lặp-theo-vai (8 entry → 3 cạnh) |

> **`_MR_EXCEPTION_EDGES = frozenset()`** đặt **test-level** (KHÔNG trong `services/imm16.py` — round TEST-ONLY, 0 service change; đối xứng `_CAPA_EXCEPTION_EDGES`). `_load_mr_workflow_edges()` parse `imm_16_mr_workflow.json` THẬT (`frappe.get_app_path`) + `set()` dedupe cạnh lặp theo vai (Compliance Manager / AssetCore Super Admin / System Manager → 8 entry → 3 cạnh). `map_edges` đọc `svc._MR_TRANSITIONS` VERBATIM (KHÔNG map thứ hai). MR đối xứng HOÀN TOÀN workflow (3 cạnh 1-1) ⇒ EXCEPTION_EDGES=∅ cả 2 chiều — giống CAPA, KHÁC Finding `{Resolved,Closed}`.

**DoD round 20 (CR-WF-16-MR reconcile-guard):** `bench --site miyano run-tests --module assetcore.tests.test_imm16` → `Ran N OK` THẬT (N tăng đúng **+4** = `TestMRWorkflowInvariant`; đọc DÒNG CUỐI, KHÔNG FAIL/ERROR/skip che); AT-16-MR-INV-1..4 GREEN với **RED-before chứng minh THẬT** (strip `Held→Minutes Approved` → INV-2 FAIL với message nêu rõ cạnh → restore GREEN). **Non-regress (KHÔNG đụng):** `TestMRLifecycle` (`test_get_mr_emits_allowed_transitions_per_status` + `test_mr_allowed_transitions_subset_of_guard` + `test_super_admin_can_advance_and_close_mr`) + `TestCapaWorkflowInvariant` + `TestFindingWorkflowInvariant` + `test_workflow_admin_override` (`TestWorkflowAdminOverride` + `TestSourceWorkflowFiles`) vẫn xanh. **0 service .py change, 0 workflow-JSON change, 0 reload, 0 migrate** (map đã in-sync 3-cạnh-khớp-1-1; admin-override Super Admin + System Manager đã có sẵn cả 3 cạnh). Nếu BE thấy drift THẬT ⇒ fix map/JSON = HARD-STOP USER (không tự sửa workflow JSON).

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
| BR-16-02 | CAPA quá hạn → escalate tiered ĐỘC LẬP theo effective-risk (Vòng 13, RC-CAPA-ESC) | `TestCapaEscalationTiered::*` (`test_imm16.py`) — TC-ESC-01..10 BVA | BVA + Decision Table | ✅ Planned → đạt khi round = ✅ |
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
