# 07 — Kiểm thử & An ninh (Testing & QA & Security)

| Mục | Giá trị |
|---|---|
| Module | **IMM-02 — Thông số Kỹ thuật & Phân tích Thị trường (Tech Spec & Market Analysis)** |
| Phạm vi | Per-module |
| Owner | QA Lead + Security Officer |
| Liên kết | [02 Analysis](./02_Analysis_Design.md) (US, BR, VR, Gate) · [03 Diagrams](./03_Diagrams.md) · [04 Backend](./04_Backend_Design.md) · [05 API](./05_API_Specification.md) · [06 Frontend](./06_Frontend_Design.md) |

> **Mục đích**: Suy ra test case có hệ thống từ phân tích (file 02) bằng kỹ thuật black-box + white-box, không liệt kê tự phát. Bao gồm: phân tích đối tượng test → chọn kỹ thuật → viết test → traceability → UAT → security → code quality. Phần VI là gate go-live.

> **Trạng thái**: Wave 2 — Live. Unit test thực tế tại `assetcore/tests/test_imm02.py` (7 TestClass · 24 test method, đã chạy). Layer Integration/Workflow/API hiện ở trạng thái Planned.

---

# Phần I — Test Analysis (Phân tích đối tượng test)

> Mục tiêu Phần I: trả lời 4 câu hỏi trước khi viết test case: **(1) test cái gì** (component inventory) **(2) suy ra từ đâu** (US/BR/Activity) **(3) ưu tiên cái nào** (risk) **(4) loại trừ cái nào** (out-of-scope).

## I.1. Component Inventory — Liệt kê phần mềm cần test

Toàn bộ artefact test được của IMM-02. Mỗi dòng → ≥ 1 test class ở Phần III. (→ 04 Backend §DocType + §Service · 05 API §Catalog · 06 Frontend §Components.)

| # | Component | Loại | File / Tên | Test layer áp dụng |
|---|---|---|---|---|
| 1 | IMM Tech Spec | DocType | `imm_tech_spec.json` | Integration (lifecycle) |
| 2 | IMM Market Benchmark | DocType | `imm_market_benchmark.json` | Integration (lifecycle) |
| 3 | IMM Lock-in Risk Assessment | DocType | `imm_lock_in_risk_assessment.json` | Integration (lifecycle) |
| 4 | Tech Spec Requirement | Child table | `tech_spec_requirement.json` | Integration (rollup) |
| 5 | Infra Compatibility Item | Child table | `infra_compatibility_item.json` | Integration (rollup G03) |
| 6 | Benchmark Candidate | Child table | `benchmark_candidate.json` | Unit (scoring) |
| 7 | Lock-in Risk Item | Child table | `lock_in_risk_item.json` | Unit (weighting) |
| 8 | Spec workflow | Workflow | `workflow/imm_02_spec_workflow.json` (9 transitions) | Integration (state transition) |
| 9 | Validator `_vr01_unique_per_plan_line` | Validator | `services/imm02.py::_vr01_unique_per_plan_line` | Unit (EP) |
| 10 | Validator `_vr02_mandatory_min_count` | Validator | `services/imm02.py::_vr02_mandatory_min_count` | Unit (BVA) |
| 11 | Validator `_vr03_test_method_present` | Validator | `services/imm02.py::_vr03_test_method_present` | Unit (EP) |
| 12 | Validator `_vr05_infra_completeness` | Validator | `services/imm02.py::_vr05_infra_completeness` | Unit (BVA) |
| 13 | Gate `_validate_gate_g01` | Gate logic | `services/imm02.py::_validate_gate_g01` | Unit (BVA/Decision Table) — ✅ Live |
| 14 | Gate `_validate_gate_g02` | Gate logic | `services/imm02.py::_validate_gate_g02` | Unit (BVA) — ⬜ Planned |
| 15 | Gate `_validate_gate_g03` | Gate logic | `services/imm02.py::_validate_gate_g03` | Unit (BVA) — ⬜ Planned |
| 16 | Gate `_validate_gate_g04` | Gate logic | `services/imm02.py::_validate_gate_g04` | Unit (Decision Table) — ✅ Live |
| 17 | Rollup `_rollup_requirement_counts` | Service function | `services/imm02.py::_rollup_requirement_counts` | Unit — ✅ Live |
| 18 | Rollup `_rollup_infra_status` | Service function | `services/imm02.py::_rollup_infra_status` | Unit — ✅ Live |
| 19 | `_compute_candidate_score` | Service function | `services/imm02.py::_compute_candidate_score` | Unit (BVA) — ✅ Live |
| 20 | `_parse_weighting` | Service function | `services/imm02.py::_parse_weighting` | Unit (EP) — ✅ Live |
| 21 | `validate_lock_in_assessment` | Service function | `services/imm02.py::validate_lock_in_assessment` | Unit — ✅ Live |
| 22 | `validate_market_benchmark` | Service function | `services/imm02.py::validate_market_benchmark` | Unit — ⬜ Planned |
| 23 | `add_requirement_to_spec` | Service function | `services/imm02.py::add_requirement_to_spec` | Integration — ⬜ Planned |
| 24 | `bulk_import_requirements_from_csv` | Service function | `services/imm02.py::bulk_import_requirements_from_csv` | Integration — ⬜ Planned |
| 25 | `check_overdue_drafts` | Scheduler job | `services/imm02.py::check_overdue_drafts` | Unit + Cron simulation — ⬜ Planned |
| 26 | `benchmark_freshness_alert` | Scheduler job | `services/imm02.py::benchmark_freshness_alert` | Unit + Cron simulation — ⬜ Planned |
| 27 | Lifecycle hooks Tech Spec | Hook | `services/imm02.py::{before_insert,validate,before_submit,on_submit}_tech_spec` | Integration (audit chain) |
| 28 | API endpoints (17) | API | `api/imm02.py` (xem I.1 list dưới) | API integration |
| 29 | Tech Spec views | FE view | `frontend/src/views/tech-specs/{List,Detail,Create}View.vue` | E2E (Playwright) |
| 30 | Pinia store | Pinia store | `frontend/src/stores/imm02.ts` | Unit (vitest) — ⬜ Planned |
| 31 | API client | TS module | `frontend/src/api/imm02.ts` | Unit (vitest) — ⬜ Planned |

**API endpoints (`api/imm02.py`)** — 17 endpoint thực tế:

| Endpoint | Verb | Endpoint | Verb |
|---|---|---|---|
| `list_tech_specs` | GET | `transition_workflow` | POST |
| `get_tech_spec` | GET | `get_market_benchmark` | GET |
| `create_tech_spec` | POST | `get_lock_in_assessment` | GET |
| `draft_from_plan` | POST | `lock_spec` | POST |
| `update_tech_spec` | POST | `withdraw_spec` | POST |
| `add_requirement` | POST | `reissue_spec` | POST |
| `bulk_import_requirements` | POST | `submit_benchmark` | POST |
| `submit_lock_in_assessment` | POST | `dashboard_kpis` | GET |
| | | `get_tech_spec` (read) | GET |

## I.2. Trace nguồn test — User Stories, Activity Flows, Business Rules

3 bảng dẫn từ artefact phân tích (file 02 / 09 §Traceability) sang test layer. (→ 02 §Business Rules · 09 §III.2 Matrix.)

### I.2.a. Từ User Story

| US ID | Tiêu đề ngắn | Acceptance Criteria # | Test layer dự kiến |
|---|---|---|---|
| US-02-001 | Tạo Tech Spec từ Plan Line | AC1 (1 spec/plan_line) | Integration + API + UAT |
| US-02-010 | Soạn requirements mandatory + test_method | AC1, AC2 | Unit + UAT |
| US-02-011 | G01 block nếu thiếu test_method | AC1 | Unit (Live) + UAT |
| US-02-020 | Nhập ≥ 3 candidates benchmark | AC1 | Unit + API + UAT |
| US-02-030 | Đánh giá 6 mục infra | AC1 | Unit + UAT |
| US-02-040 | Tính lock-in score 5 chiều | AC1 | Unit (Live) + UAT |
| US-02-050 | Lock spec → trigger IMM-03 | AC1 | Integration + API + UAT |
| US-02-060 | Withdraw + Reissue versioning | AC1, AC2 | API + UAT |

### I.2.b. Từ Business Rule

| BR ID | Phát biểu | Component liên quan (I.1) | Kỹ thuật test phù hợp |
|---|---|---|---|
| BR-02-01 | 1 Procurement Plan Line ↔ 1 Tech Spec Active | `_vr01_unique_per_plan_line` (#9) | EP |
| BR-02-02 | ≥ 8 mandatory requirements trước Reviewing | G01 `_validate_gate_g01` (#13) | BVA |
| BR-02-03 | Mandatory requirement phải có test_method | `_vr03_test_method_present` (#11) | EP / Decision Table |
| BR-02-04 | ≥ 3 benchmark candidates | G02 `_validate_gate_g02` (#14) | BVA |
| BR-02-05 | 6/6 infra domains phải đánh giá | G03 `_validate_gate_g03` (#15) + `_vr05` (#12) | BVA |
| BR-02-06 | Lock-in score ≤ threshold hoặc có mitigation | G04 `_validate_gate_g04` (#16) | Decision Table |
| BR-02-07 | Locked spec không sửa; phải Withdraw + Reissue | `before_save` docstatus=1 check (#27) | State Transition |
| BR-02-08 | CTA gating server-driven (`can_lock/can_withdraw/can_reissue`) | `_get_tech_spec` derive cờ + `_SPEC_CTA_TRANSITIONS` | Decision Table (state × capability) |
| BR-02-09 | Lock/Withdraw cần `spec.submit`; Reissue cần `spec.create` → FORBIDDEN | `_require_spec_approver` trong `_lock_spec`/`_withdraw_spec`/`_reissue_spec` | EP (permission) + State Transition |

### I.2.c. Từ Activity Flow / BPMN

| Activity | Use Case | Branch chính | Branch ngoại lệ |
|---|---|---|---|
| Spec lifecycle | UC-Soạn & khóa Tech Spec | Draft → Reviewing → Benchmarked → Risk Assessed → Pending Approval → Locked | G01..G04 fail; Reviewing→Draft (yêu cầu chỉnh); Pending→Risk Assessed (chỉnh risk); Withdraw |
| Benchmark | UC-So sánh thị trường | Nhập ≥ 3 candidate → recommended_candidate set | < 3 candidate → G02 fail |
| Lock-in | UC-Đánh giá rủi ro lệ thuộc | 5 chiều → weighted score ≤ threshold | score > threshold không mitigation → G04 fail |

## I.3. Risk-based Priority

| Component (I.1) | Likelihood (1-5) | Impact (1-5) | Risk = L×I | Priority |
|---|---|---|---|---|
| Spec workflow transitions (#8) | 4 | 5 | 20 | **Critical** |
| Gate `_validate_gate_g04` lock-in (#16) | 4 | 5 | 20 | **Critical** |
| Gate `_validate_gate_g01` (#13) | 4 | 4 | 16 | **Critical** |
| Lifecycle hooks + audit chain (#27) | 3 | 5 | 15 | **Critical** |
| BR-02-07 immutable Locked (#27) | 3 | 5 | 15 | **Critical** |
| Gate `_validate_gate_g02/g03` (#14,#15) | 3 | 4 | 12 | High |
| `validate_lock_in_assessment` (#21) | 3 | 4 | 12 | High |
| `_vr01_unique_per_plan_line` (#9) | 3 | 3 | 9 | Medium |
| `bulk_import_requirements_from_csv` (#24) | 3 | 3 | 9 | Medium |
| `_compute_candidate_score` (#19) | 2 | 3 | 6 | Medium |
| Scheduler jobs (#25,#26) | 2 | 2 | 4 | Low |
| FE views (#29) | 2 | 2 | 4 | Low |
| `dashboard_kpis` read-only (#28) | 1 | 2 | 2 | Low |

**Quy ước priority**: Critical (R ≥ 15) test trước, fail = block release · High (10–14) bắt buộc trước go-live · Medium (5–9) trong sprint · Low (< 5) chỉ test khi báo bug.

## I.4. Scope

- **In-scope**: (1) toàn bộ gate logic G01–G04 + validator VR-02-01/03/05; (2) workflow 9 transition state machine; (3) audit chain integrity khi lock/withdraw/reissue; (4) API envelope + permission của 17 endpoint; (5) permlevel 1 isolation của `lock_in_score`/`mitigation_*`.
- **Out-of-scope**:
  - Performance/load test → giao Phần III.8 (chỉ định target, không chạy trong sprint này).
  - Cross-module IMM-03 (AVL/Vendor Eval) — chỉ smoke ở `test_lock_triggers_imm03`, full integration thuộc docs IMM-03.
  - Cross-module IMM-10 Risk Register — chỉ verify entry tạo, không test logic IMM-10.
  - Frontend visual regression — chỉ E2E happy + role-gate.
- **Assumptions**: master data (IMM Device Model, AC Asset Category, IMM Procurement Plan) đã seed; test users đủ 6 role đã tạo; site test sạch (`_Test*` prefix cho fixture mới).

---

# Phần II — Test Design Techniques (Kỹ thuật thiết kế test case)

> Mỗi test phải truy được về 1 kỹ thuật ở dưới.

## II.1. Black-box techniques

| Kỹ thuật | Khi nào dùng | Áp dụng vào IMM-02 | Số test (rule of thumb) |
|---|---|---|---|
| **Equivalence Partitioning (EP)** | Input có miền giá trị chia nhóm | `infra_status_overall` (All Compatible / Partial / Need Major Upgrade); `workflow_state`; `_parse_weighting` (none/dict/json/invalid) | 1 test/partition |
| **Boundary Value Analysis (BVA)** | Numeric / count field có biên | `total_mandatory` quanh 8 (G01); `candidate_count` quanh 3 (G02); infra 6/6 (G03); `lock_in_score` quanh threshold (G04) | 2–3 test/biên: min-1, min, min+1 |
| **Decision Table** | Multi-condition gate | G04 (score>threshold × có/không mitigation_plan × có/không evidence); BR-02-03 (mandatory × có/không test_method) | 2^N rút gọn theo equivalence |
| **State Transition Testing** | Workflow finite state machine | `imm_02_spec_workflow.json` 9 transition (Draft→…→Locked/Withdrawn + reverse edges) | mỗi transition + invalid transition |
| **Use Case Testing** | End-to-end actor flow | 12 UAT scenario, API integration | 1/main + 1/alt + 1/exception |
| **Pairwise** | Nhiều field optional kết hợp | Form tạo Tech Spec (device_category × source_plan × template_ref) | min set cover all pairs |
| **Error Guessing** | null/empty/unicode/race | Mọi endpoint nhận user input; bulk import 0-row, oversize | bổ sung — không thay thế |

## II.2. White-box techniques

| Kỹ thuật | Áp dụng vào | Tiêu chí đạt | Công cụ |
|---|---|---|---|
| **Statement coverage** | Service functions (#9–#26) | ≥ 85% line | `coverage report` |
| **Branch / Decision coverage** | Functions có if/else, try/except (G01–G04, `_rollup_infra_status`, `_validate_gate_g04`) | ≥ 80% branch | `coverage --branch` |
| **Condition / MC/DC** | G04 (3 sub-condition: score>threshold, mitigation_plan, mitigation_evidence) | mỗi sub-condition kiểm soát outcome độc lập | manual design + coverage |
| **Path coverage** | `_rollup_infra_status` (status precedence), `_compute_candidate_score` | toàn bộ path khả dĩ | manual |

## II.3. Mapping Component → Kỹ thuật

| Loại component | Kỹ thuật chính | Kỹ thuật phụ |
|---|---|---|
| Field validator (`_vr*`) | BVA + EP | Error guessing |
| Gate logic (`_validate_gate_*`) | Decision Table | MC/DC |
| Workflow transition | State Transition | Use Case |
| Service function pure (`_compute_*`, `_parse_*`, `_rollup_*`) | EP + Branch coverage | BVA |
| API endpoint | Use Case + EP | Pairwise (form input) |
| Scheduler (`check_overdue_drafts`, `benchmark_freshness_alert`) | Use Case (state setup → run → assert) | Error guessing (partial fail) |
| FE view (Playwright) | Use Case end-to-end | Error guessing (4xx/5xx, role gate) |

---

# Phần III — Test Plan (Kế hoạch thực thi)

## III.1. Test Pyramid

```
                  ┌────────────┐
                  │  E2E / UAT │   12 scenarios (~5%)
                 ─┴────────────┴─
              ┌──────────────────────┐
              │   API Integration    │   10 test (~15%) ⬜ Planned
             ─┴──────────────────────┴─
          ┌────────────────────────────────┐
          │  Workflow + DocType lifecycle  │   9 WF + 6 lifecycle (~25%) ⬜ Planned
         ─┴────────────────────────────────┴─
      ┌────────────────────────────────────────────┐
      │   Unit — Service Layer (24 test, ✅ Live)   │   (~55%)
     ─┴────────────────────────────────────────────┴─
```

(→ CLAUDE.md §17 TDD mandatory.)

## III.2. Unit test — Service Layer

File: `assetcore/tests/test_imm02.py` (1 file, 7 TestClass, 24 method — đã chạy). Mỗi class trace về ≥ 1 dòng I.1.

| Test class | Function cover | Kỹ thuật | Method (Live) |
|---|---|---|---|
| `TestRollupInfraStatus` ✅ | `_rollup_infra_status` (#18) | EP | empty_returns_blank · all_compatible · need_upgrade_gives_partial · need_major_upgrade_wins · no_statuses_returns_blank |
| `TestRollupRequirementCounts` ✅ | `_rollup_requirement_counts` (#17) | EP | counts_mandatory_optional · sets_seq_on_each_row |
| `TestGateG01` ✅ | `_validate_gate_g01` (#13) | BVA | below_minimum_raises · exactly_minimum_passes · missing_test_method_raises |
| `TestGateG04` ✅ | `_validate_gate_g04` (#16) | Decision Table | below_threshold_passes · above_threshold_no_plan_raises · above_threshold_with_plan_but_no_evidence_raises · above_threshold_with_plan_and_evidence_passes |
| `TestComputeCandidateScore` ✅ | `_compute_candidate_score` (#19) | BVA | returns_float_in_range · higher_spec_match_gives_higher_score · tier1_better_than_tier3 |
| `TestParseWeighting` ✅ | `_parse_weighting` (#20) | EP | none_returns_defaults · dict_passthrough · json_string_parsed · invalid_json_returns_defaults |
| `TestValidateLockInAssessment` ✅ | `validate_lock_in_assessment` (#21) | EP | computes_weighted_score · sets_default_threshold · unknown_dimension_ignored |

**Gap unit test (⬜ Planned — Wave 3):**

| Class | Function cover | Lý do |
|---|---|---|
| `TestGateG02` ⬜ | `_validate_gate_g02` (#14) | hiện chỉ có G01/G04; cần BVA quanh candidate_count=3 |
| `TestGateG03` ⬜ | `_validate_gate_g03` (#15) + `_vr05_infra_completeness` | BVA quanh 6/6 infra domain |
| `TestVR01UniquePerPlanLine` ⬜ | `_vr01_unique_per_plan_line` (#9) | cần fixture IMM Procurement Plan + plan_line |
| `TestVR03TestMethod` ⬜ | `_vr03_test_method_present` (#11) | Decision Table mandatory × test_method |
| `TestValidateMarketBenchmark` ⬜ | `validate_market_benchmark` (#22) | chưa có unit test |
| `TestSchedulers` ⬜ | `check_overdue_drafts` / `benchmark_freshness_alert` (#25,#26) | cron simulation |

**Run:**
```bash
bench --site <site> run-tests --app assetcore --module assetcore.tests.test_imm02
```

> Lưu ý naming thực tế: `draft_from_plan` nằm ở `api/imm02.py` (không phải `services`); lock-in tính qua `validate_lock_in_assessment(doc)` (không có hàm `compute_lock_in` riêng).

## III.3. Integration — DocType lifecycle (⬜ Planned)

File dự kiến: `tests/test_imm02_lifecycle.py`. Cover hook `before_insert / validate / before_submit / on_submit` của IMM Tech Spec.

| Test | Setup | Action | Assert | Kỹ thuật |
|---|---|---|---|---|
| `test_full_lifecycle_draft_to_locked` ⬜ | Tech Spec + 8 mandatory + 3 candidate + 6 infra + lock-in | apply 6 transition | state=Locked, docstatus=1 | Use Case |
| `test_lock_triggers_imm03` ⬜ | spec Pending Approval | `lock_spec()` | `publish_realtime "imm02_spec_locked"` được gọi | Use Case |
| `test_lock_triggers_risk_register` ⬜ | lock_in_score > threshold | lock | IMM-10 Risk Register entry tạo | Use Case |
| `test_reissue_chain` ⬜ | Lock → Withdraw → Reissue ×2 | reissue | version bump, parent_spec chain đúng | State Transition |
| `test_immutable_locked_spec` ⬜ | spec Locked | `doc.save()` | `frappe.throw` (BR-02-07) | EP |
| `test_rollup_counts_on_save` ⬜ | spec + N requirement | `doc.save()` | `total_mandatory`/`total_optional` đúng | EP |

> Fixture trong `setUpClass` phải có `tearDownClass` purge (assetcore-test LL-TEST-17).

## III.4. Integration — Workflow transitions (⬜ Planned)

File dự kiến: `tests/test_imm02_workflow.py`. Workflow `imm_02_spec_workflow.json` có **9 transition** (`python3 -c "import json;print(len(json.load(open('assetcore/assetcore/workflow/imm_02_spec_workflow.json'))['transitions']))"` → 9). Bắt buộc cover 100%.

| # | Transition (action) | From → To | Role required | Test pass | Test fail |
|---|---|---|---|---|---|
| 1 | Gửi rà soát | Draft → Reviewing | Spec User | ☐ | ☐ G01 fail (mandatory<8 / thiếu test_method) |
| 2 | Yêu cầu chỉnh spec | Reviewing → Draft | Spec User | ☐ | ☐ wrong role |
| 3 | Yêu cầu chỉnh spec | Reviewing → Draft | Needs Manager | ☐ | ☐ wrong role |
| 4 | Hoàn tất benchmark | Reviewing → Benchmarked | Needs Manager | ☐ | ☐ G02 fail (candidate<3) |
| 5 | Đánh giá rủi ro xong | Benchmarked → Risk Assessed | Spec Manager | ☐ | ☐ G03 fail (infra<6/6) |
| 6 | Trình duyệt spec | Risk Assessed → Pending Approval | Commissioning Manager | ☐ | ☐ wrong role |
| 7 | Phê duyệt spec | Pending Approval → Locked | Procurement Manager | ☐ | ☐ G04 fail (lock-in no mitigation) |
| 8 | Rút spec | Pending Approval → Withdrawn | Procurement Manager | ☐ | ☐ wrong role |
| 9 | Yêu cầu chỉnh risk | Pending Approval → Risk Assessed | Procurement Manager | ☐ | ☐ wrong role |

**Kỹ thuật**: State Transition Testing — mỗi edge = 1 test pass + 1 test fail (wrong role hoặc gate fail).

## III.5. Integration — Audit chain integrity (⬜ Planned)

- (a) Sau toàn bộ lifecycle (6 transition), `IMM Audit Trail` có entry tương ứng mỗi transition; chain hash SHA-256 hợp lệ end-to-end.
- (b) Khi tamper 1 entry (sửa `change_summary`), verify endpoint trả `chain_broken=true`.

(→ 04 Backend §Audit Trail · `IMM Audit Trail` DocType · III.4 transition set.)

## III.6. API test (⬜ Planned)

File dự kiến: `tests/test_imm02_api.py`. Cover happy + envelope `success=true`, INVALID_PARAMS, FORBIDDEN, pagination, idempotent retry.

| Test | Endpoint | Verify | Kỹ thuật |
|---|---|---|---|
| `test_list_tech_specs_ok` ⬜ | `api/imm02.list_tech_specs` | `success=true`, items[], pagination | Use Case |
| `test_draft_from_plan_ok` ⬜ | `api/imm02.draft_from_plan` | created: N specs | Use Case |
| `test_draft_from_plan_vr01` ⬜ | `api/imm02.draft_from_plan` (plan_line trùng) | skipped[] (BR-02-01) | EP |
| `test_add_requirement_ok` ⬜ | `api/imm02.add_requirement` | total_mandatory++ | Use Case |
| `test_bulk_import_ok` ⬜ | `api/imm02.bulk_import_requirements` | imported=N | Use Case |
| `test_submit_benchmark_ok` ⬜ | `api/imm02.submit_benchmark` (3 cand) | recommended_candidate set | Use Case |
| `test_submit_benchmark_fail_g02` ⬜ | `api/imm02.submit_benchmark` (2 cand) | `code=BUSINESS_RULE` | BVA |
| `test_submit_lock_in_ok` ⬜ | `api/imm02.submit_lock_in_assessment` | lock_in_score correct | Use Case |
| `test_lock_spec_ok` ⬜ | `api/imm02.lock_spec` | `success=true`, state=Locked | Use Case |
| `test_lock_spec_low_role_forbidden` ⬜ | `api/imm02.lock_spec` (low-role) | `code=FORBIDDEN`, spec vẫn Pending Approval (KHÔNG pass-through submit) | EP (permission) |
| `test_reissue_spec_ok` ⬜ | `api/imm02.reissue_spec` | new_spec, version bump | Use Case |

### III.6.1. CTA gating server-driven (BR-02-08/09 — vòng 6, `test_imm02`)

| Test | Đối tượng | Verify | Kỹ thuật |
|---|---|---|---|
| `test_get_tech_spec_flags_pending_approval` | `_get_tech_spec` @ Pending Approval, role có `spec.submit` | `allowed_transitions=["lock","withdraw"]`, `can_lock=1`, `can_withdraw=1`, `can_reissue=0` | Decision Table |
| `test_get_tech_spec_flags_locked` | `_get_tech_spec` @ Locked | `can_withdraw=1`, `can_lock=0`, `can_reissue=0` | State Transition |
| `test_get_tech_spec_flags_withdrawn` | `_get_tech_spec` @ Withdrawn, role có `spec.create` | `can_reissue=1`, còn lại 0 | State Transition |
| `test_get_tech_spec_flags_draft_all_false` | `_get_tech_spec` @ Draft/Reviewing/… | `allowed_transitions=[]`, 3 cờ = 0 | EP |
| `test_get_tech_spec_flags_no_role_all_false` | `_get_tech_spec` @ Pending Approval, user KHÔNG có `spec.submit` | `allowed_transitions=["lock","withdraw"]` (hint) nhưng `can_lock=can_withdraw=0` | EP (permission) |
| `test_lock_spec_low_role_forbidden` | `_lock_spec` (user thiếu `spec.submit`) @ Pending Approval | `FORBIDDEN`; state vẫn Pending Approval | EP (permission) |
| `test_withdraw_spec_low_role_forbidden` | `_withdraw_spec` (user thiếu `spec.submit`) | `FORBIDDEN`; state không đổi | EP (permission) |
| `test_invariant_flags_subset_of_guard` | ∀ state × ∀ role: nếu `can_X=1` thì gọi endpoint X KHÔNG trả FORBIDDEN/BAD_STATE | map ⊆ guard-permitted | Property/State Transition |
| `test_super_admin_can_lock_regression` | `AssetCore Super Admin` @ Pending Approval | `can_lock=1` **và** `lock_spec` OK (state→Locked) — chuỗi lesson "full quyền vẫn duyệt được" | Use Case (regression) |

> FE parity: `frontend/src/views/tech-specs/__tests__/TechSpecDetailView.ctaGating.test.ts` (vitest) — cờ→nút v-if; grep `workflow_state ===` trong 3 computed CTA = 0; cờ thiếu → không lỗi + không nút.

### III.6.2. SSoT 6 transition trung gian — `allowed_actions` + reconcile INVARIANT (CR-WF-02-SPEC vòng 24, `test_imm02`)

| Test | Đối tượng | Verify | Kỹ thuật |
|---|---|---|---|
| `test_spec_allowed_transitions_matches_workflow_fixture` | `_SPEC_VALID_TRANSITIONS` ⇄ `imm_02_spec_workflow.json` (parse JSON) | (a) ∀ `(state,action,next_state,roles)∈map`: `roles == ∪allowed` group workflow (EXACT); (b) `{action wf} − {action map} == _SPEC_EXCEPTION_ACTIONS` (`{'Phê duyệt spec','Rút spec'}`). **RED khi map rỗng/thiếu cạnh → GREEN sau 6 cạnh** | Invariant (STATIC) |
| `test_spec_allowed_actions_draft_spec_user` | `spec_allowed_actions('Draft', {'Spec User'})` | `== ['Gửi rà soát']` | Decision Table |
| `test_spec_allowed_actions_reviewing_needs_manager` | `spec_allowed_actions('Reviewing', {'Needs Manager'})` | `== ['Yêu cầu chỉnh spec','Hoàn tất benchmark']` | Decision Table |
| `test_spec_allowed_actions_reviewing_spec_user_no_benchmark` | `spec_allowed_actions('Reviewing', {'Spec User'})` | `== ['Yêu cầu chỉnh spec']` (KHÔNG có `Hoàn tất benchmark`) | EP (role filter) |
| `test_spec_allowed_actions_terminal_empty` | `spec_allowed_actions('Locked'/'Withdrawn'/None/'Foo', roles)` | `== []` | Boundary |
| `test_get_tech_spec_emits_allowed_actions` | `_get_tech_spec` @ Draft, session role có `Spec User` | payload có key `allowed_actions == ['Gửi rà soát']`; `allowed_transitions` (vòng 6) vẫn tồn tại riêng | Integration |
| `test_transition_workflow_advertised_action_reachable` | user có role, doc thoả gate cho cạnh | ∀ `action ∈ allowed_actions`: `transition_workflow(name, action)` KHÔNG FORBIDDEN + `workflow_state == next_state` (INVARIANT-2) | State Transition |
| `test_transition_workflow_missing_role_not_advertised` | user thiếu role cạnh (vd `Spec User` @ Reviewing với `Hoàn tất benchmark`) | action VẮNG khỏi `allowed_actions`; gọi thẳng `transition_workflow` → `FORBIDDEN` (in-handler cap-403, HTTP-200 + envelope, state không đổi) | EP (permission) |

> **Tách RBAC-gate ≠ business-gate:** `test_transition_workflow_advertised_action_reachable` phải dựng fixture thoả G01–G04 cho cạnh đang kiểm (vd Draft→Reviewing cần ≥8 mandatory + test_method), hoặc assert INVARIANT-2 ở mức role-permission. `allowed_actions` chỉ advertise cạnh role-reachable; `BUSINESS_RULE` khi bấm là UX đúng, KHÔNG vi phạm invariant.

> **KHÔNG đụng** `imm_02_spec_workflow.json` → `test_workflow_admin_override` GIỮ GREEN (verify trong DoD). FE parity: `TechSpecDetailView.ctaGating.test.ts` +case `allowed_actions` (render `cta-wf-<slug>`, click → `store.transitionWorkflow` + `fetchOne`, rỗng/thiếu → 0 nút wf, Pending Approval không nuốt `cta-lock`/`cta-withdraw`). DoD: `bench --site miyano run-tests --app assetcore --module assetcore.tests.test_imm02` → 'Ran N OK' THẬT (dòng cuối) + `vue-tsc` sạch + `vitest` xanh.

## III.7. E2E browser (Playwright)

Dùng cho flow UI khó cover bằng API: dropdown cascade `device_category`/`source_plan` ở `TechSpecCreateView.vue`; modal confirm Lock ở `TechSpecDetailView.vue`; workflow button visibility theo role; ẩn `lock_in_score` với HTM Engineer. (→ `assetcore-test` skill Phần 2 — Playwright MCP recipes R-1..R-9.)

## III.8. Performance test (target — không chạy sprint này)

| Metric | Target | Method |
|---|---|---|
| `list_tech_specs` 200 row p95 | ≤ 400ms | k6 GET |
| `create_tech_spec` p95 | ≤ 600ms | k6 POST batch |
| `bulk_import_requirements` 100 row | ≤ 10s | k6 POST |
| `check_overdue_drafts` 1000 record | ≤ 5min | `time bench execute …` |

## III.9. Test data & Fixtures

| Loại | Cách seed | File |
|---|---|---|
| Master data (Asset Category, Device Model, Procurement Plan) | `fixtures/*.json` qua `bench migrate` | `assetcore/fixtures/` |
| Workflow + states + actions | fixture | `assetcore/assetcore/workflow/imm_02_spec_workflow.json` |
| Test records | `test_records.json` per DocType | `imm_tech_spec/test_records.json` *(Cần khảo sát — chưa xác nhận tồn tại)* |
| UAT seed | Python script | `assetcore/scripts/uat/uat_imm02.py` *(Cần khảo sát)* |

> UAT data phải thực tế (tên bệnh viện VN, mã NCC chuẩn). Backend fixture mới dùng prefix `_Test` (assetcore-test R-0/R-1).

## III.10. Run commands & Coverage gate

```bash
# Module test (Live)
bench --site <site> run-tests --app assetcore --module assetcore.tests.test_imm02
# Coverage
coverage run -m unittest assetcore.tests.test_imm02 && coverage report
# Workflow smoke (khi test_imm02_workflow.py có)
bench --site <site> run-tests --module assetcore.tests.test_imm02_workflow
```

| Layer | Target coverage | Đo |
|---|---|---|
| Service (`services/imm02.py`) | ≥ 85% line + ≥ 80% branch | `coverage --branch` |
| DocType lifecycle | ≥ 70% | `coverage report` |
| API (`api/imm02.py`) | ≥ 60% | `coverage report` |
| Frontend (vue-tsc) | 0 error | `npm run build` |

> Coverage % thực tế: *(Cần khảo sát — chưa chạy `coverage report` trên runtime)*. Trên đây là target.

---

# Phần IV — Traceability Matrices

> Mọi test ở Phần III phải xuất hiện ở cả 3 bảng. (→ 09 §III.2 Matrix chính.)

## IV.1. US → Test mapping

| US ID | AC | Test ID (III.x) | Layer | Status |
|---|---|---|---|---|
| US-02-001 | AC1 | `test_draft_from_plan_ok` | API/Integration | ⬜ Planned |
| US-02-010 | AC1 | `TestVR03TestMethod` | Unit | ⬜ Planned |
| US-02-011 | AC1 | `TestGateG01::test_missing_test_method_raises` | Unit | ✅ Live |
| US-02-020 | AC1 | `test_submit_benchmark_fail_g02` / `TestGateG02` | Unit/API | ⬜ Planned |
| US-02-030 | AC1 | `TestGateG03` / `TestRollupInfraStatus` | Unit | partial ✅ (rollup Live) / G03 ⬜ |
| US-02-040 | AC1 | `TestValidateLockInAssessment::test_computes_weighted_score` | Unit | ✅ Live |
| US-02-050 | AC1 | `test_lock_triggers_imm03` | Integration | ⬜ Planned |
| US-02-060 | AC1,AC2 | `test_reissue_chain` / `test_reissue_spec_ok` | Integration/API | ⬜ Planned |

## IV.2. BR → Test mapping

| BR ID | Phát biểu (rút gọn) | Test ID | Kỹ thuật | Happy / Negative |
|---|---|---|---|---|
| BR-02-01 | 1 plan_line ↔ 1 Active spec | `TestVR01UniquePerPlanLine` ⬜ | EP | 1 / 1 |
| BR-02-02 | ≥ 8 mandatory | `TestGateG01::{exactly_minimum_passes,below_minimum_raises}` ✅ | BVA | 1 / 1 |
| BR-02-03 | mandatory có test_method | `TestGateG01::test_missing_test_method_raises` ✅ | Decision Table | 0 / 1 (Live) — happy ⬜ |
| BR-02-04 | ≥ 3 candidates | `TestGateG02` ⬜ | BVA | 1 / 1 |
| BR-02-05 | 6/6 infra domains | `TestGateG03` ⬜ + `TestRollupInfraStatus` ✅ | BVA | partial |
| BR-02-06 | lock-in ≤ threshold OR mitigation | `TestGateG04` (4 method) ✅ | Decision Table | 2 / 2 |
| BR-02-07 | Locked spec chỉ qua Withdraw+Reissue | `test_immutable_locked_spec` ⬜ | State Transition | 0 / 1 |

> BR Critical (I.3): BR-02-02 và BR-02-06 đã có Decision Table/BVA đầy đủ ✅. BR-02-07 (Critical) chưa có test ⬜.

## IV.3. Component → Test mapping

| Component (I.1) | Test ID | Test layer | Coverage % | Risk priority (I.3) |
|---|---|---|---|---|
| `_validate_gate_g01` (#13) | `TestGateG01` | Unit | *(Cần khảo sát)* | Critical |
| `_validate_gate_g04` (#16) | `TestGateG04` | Unit | *(Cần khảo sát)* | Critical |
| Spec workflow (#8) | `test_imm02_workflow.py` ⬜ | Integration | 0% (Planned) | Critical |
| Audit chain (#27) | III.5 ⬜ | Integration | 0% (Planned) | Critical |
| `_validate_gate_g02/g03` (#14,15) | `TestGateG02/G03` ⬜ | Unit | 0% (Planned) | High |
| `validate_lock_in_assessment` (#21) | `TestValidateLockInAssessment` | Unit | *(Cần khảo sát)* | High |
| `_compute_candidate_score` (#19) | `TestComputeCandidateScore` | Unit | *(Cần khảo sát)* | Medium |
| `_rollup_infra_status` (#18) | `TestRollupInfraStatus` | Unit | *(Cần khảo sát)* | High (G03 input) |
| API endpoints (#28) | `test_imm02_api.py` ⬜ | API | 0% (Planned) | High |
| Workflow role ⊆ Role Profile coverage (§IV.5) | `test_workflow_role_profile_coverage.py` ⬜ | Invariant (static, 22 wf) | 0% (Planned) | Critical |
| Dead-gate `Spec User` đóng (persona VT-TTBYT) | `test_imm02.py::TestSpecProfileDeadGate` ⬜ | Integration | 0% (Planned) | Critical |

## IV.4. CR-WF-RBAC-PROFILE-COVERAGE (vòng 34) — test spec

Ground truth: `02_Analysis_Design.md` §IV.5 + ADR-IMM02-03. TDD RED-trước → GREEN-sau.

| Test ID | Layer | Assert | RED-trước | GREEN-sau |
|---|---|---|---|---|
| `test_workflow_role_profile_coverage.py::test_every_non_admin_role_is_profile_backed` (**INV-COV**, own-file) | Invariant static (glob 22 source JSON + `ROLE_PROFILE_CATALOG`) | ∀ transition, mọi `allowed` non-admin role ∈ `(∪roles_for_profile) ∪ {Super Admin, System Manager} ∪ EXCEPTION_ROLES{Vendor Engineer}` | uncovered == `{Spec User}` → đỏ (msg liệt kê role + workflow) | thêm `Spec User` vào catalog → uncovered == `∅` |
| `test_workflow_role_profile_coverage.py::test_exception_role_never_sole_gates` (**INV-EXC-REACH**) | Invariant static | ∀ transition-group `allowed ∩ EXCEPTION_ROLES ≠ ∅` có ≥1 role ∈ `∪roles_for_profile` | (GREEN sẵn: 3 group IMM-04 co-list `PM User`) | giữ GREEN — chống ai đó thêm cạnh sole-gate `Vendor Engineer` |
| `TestSpecProfileDeadGate::test_vttbyt_profile_can_send_review` | Integration (ensure_user + profile "Trưởng phòng VT-TTBYT") | tạo Draft 8 spec-line (G01) → `transition_workflow('Gửi rà soát')` success + `workflow_state=='Reviewing'` | guard `spec_allowed_actions('Draft', roles)==[]` → `BAD_STATE` envelope (API) / `apply_workflow` `PermissionError` (raw) | success |
| `TestSpecProfileDeadGate::test_base_role_still_blocked` | Integration (user chỉ `AssetCore System User`) | `Gửi rà soát` bị chặn (BAD_STATE / PermissionError) | (đã chặn) | VẪN chặn — không mở-toang |

**Regression phải GREEN (không đỏ):** INV-A/INV-B/INV-C (`test_workflows.py`), `test_imm02.py` 593–604 (`spec_allowed_actions` với `{Spec User}`), `test_spec_valid_transitions_reconciles_workflow_json` (INVARIANT-1), `test_role_profiles.py` (`len(PROFILE_NAMES)==8`) — vì workflow JSON / `_SPEC_VALID_TRANSITIONS` / fixtures **không đổi**.

**DONE-gate:** `bench --site miyano run-tests` báo `Ran N OK` THẬT (không skip/false-green); sync live `assetcore.setup.setup_role_profiles.run` (idempotent, KHÔNG `bench migrate`).

---

# Phần V — UAT Script

## V.1. Phạm vi UAT

- **In-scope**: 12 scenario theo US (V.4) — lifecycle Draft→Locked, gates, withdraw/reissue, permlevel isolation.
- **Out-of-scope**: performance (III.8), security pentest (Phần VI.10).
- **Pre-condition**: site UAT deploy version v1.0.1; fixture (Procurement Plan + Device Model + template) loaded; 6 tester account active.

## V.2. Tester accounts

| Username (vai trò UAT) | Role | Vai trò UAT |
|---|---|---|
| `htm.engineer@uat` | Spec User | Soạn spec, thêm requirement |
| `khtc.officer@uat` | Needs Manager | Hoàn tất benchmark |
| `qa.risk@uat` | Spec Manager | Đánh giá rủi ro infra + lock-in |
| `commissioning@uat` | Commissioning Manager | Trình duyệt spec |
| `vp.block1@uat` | Procurement Manager | Phê duyệt / rút / reissue |
| `viewer.low@uat` | (read-only) | Cover FORBIDDEN case |

> Phải có account role thấp (`viewer.low`) để cover FORBIDDEN, không chỉ Admin.

## V.3. Test data đã seed

| DocType | Số lượng | Ghi chú |
|---|---|---|
| IMM Procurement Plan (Approved) | 1 | có ≥ 5 plan_line gắn Device Model + template |
| IMM Device Model | ≥ 5 | có spec template để seed requirement |
| IMM Tech Spec (sẵn các state) | ≥ 6 | mỗi state 1 spec để verify transition |
| Tester users | 6 | đủ 6 role (V.2) |

> Reset script: *(Cần khảo sát — `scripts/uat/uat_imm02.py` chưa xác nhận)*.

## V.4. UAT Scenarios — Suy ra từ US + Activity

12 scenario (migrate từ bản trước). ID `UAT-IMM-02-NN`.

| ID | Actor | Pre-condition | US/BR cover | Kỹ thuật | Kết quả mong đợi |
|---|---|---|---|---|---|
| UAT-IMM-02-01 | Spec User (HTM Eng) | PP Approved, plan_line có Device Model + template | US-02-001, BR-02-01 | Use Case happy | 5 spec tạo, requirements seeded từ template |
| UAT-IMM-02-02 | Spec User | Draft, 6 mandatory | US-02-010, BR-02-02 | Use Case happy | Thêm 2 mandatory + test_method → Gửi rà soát → G01 pass, state=Reviewing |
| UAT-IMM-02-03 | Spec User | Draft, 8 mandatory nhưng 1 thiếu test_method | BR-02-03 | Use Case alt | G01 fail: "Cần phương pháp kiểm tra cho yêu cầu bắt buộc: X" |
| UAT-IMM-02-04 | Needs Manager (KH-TC) | Spec ở Reviewing | US-02-020, BR-02-04 | Use Case happy | Nhập 3 candidate → Hoàn tất benchmark → G02 pass, recommended_candidate set |
| UAT-IMM-02-05 | Needs Manager | Spec ở Reviewing | BR-02-04 | Use Case alt | Nhập 2 candidate → G02 fail: "Cần ≥ 3 ứng viên so sánh" |
| UAT-IMM-02-06 | Spec Manager (QA Risk) | Spec ở Benchmarked | US-02-030, BR-02-05 | Use Case happy | 6 mục Infra + 5 chiều Lock-in → Đánh giá rủi ro xong → G03 pass, lock_in_score hiển thị |
| UAT-IMM-02-07 | Spec Manager | Spec ở Benchmarked, chỉ 5 mục Infra | BR-02-05 | Use Case alt | G03 fail: "Chưa đánh giá mục HVAC" |
| UAT-IMM-02-08 | Procurement Manager (VP Block1) | Pending Approval, lock_in_score=4.2, không mitigation | US-02-040, BR-02-06 | Use Case alt | G04 fail: "Lock-in score 4.2 vượt ngưỡng — cần mitigation_plan" |
| UAT-IMM-02-09 | Procurement Manager | Pending Approval, score=4.2 + mitigation_plan + evidence | US-02-050, BR-02-06 | Use Case happy | Phê duyệt → Locked, IMM-03 triggered |
| UAT-IMM-02-10 | Spec User | Spec ở Locked | BR-02-07 | EP permission | Cố sửa requirement → từ chối: "Spec đã Locked không thể sửa" |
| UAT-IMM-02-11 | Procurement Manager | Spec ở Pending Approval | US-02-060, BR-02-07 | State Transition | Rút spec + lý do → Withdrawn, lý do ghi nhận, audit entry |
| UAT-IMM-02-12 | Spec User | Spec ở Withdrawn | US-02-060 | State Transition | Reissue → spec mới, parent_spec=spec cũ, state=Draft |

## V.5. Tổng hợp kết quả & Bug found

- Bảng kết quả: `Scenario · Status (Pass/Fail/Block) · Tester · Ngày · Ghi chú` — điền khi chạy UAT.
- Bug list: `Issue ID · Severity (Blocker/Major/Minor/Trivial) · Mô tả · Fix status`.
- Acceptance: ≥ 95% PASS, Blocker = 0, Major ≤ 2 (có workaround).
- Sign-off: BA Lead + QA Lead + Module Owner (PTP Khối 1) + End-user (KH-TC).

---

# Phần VI — Security Review (gate)

## VI.1. RBAC

- **Role definitions**: `fixtures/role.json` + `role_profile.json`. Role IMM-02: Spec User, Needs Manager, Spec Manager, Commissioning Manager, Procurement Manager (+ System Manager/Admin).
- **DocPerm matrix** (xem dưới): IMM Tech Spec, IMM Market Benchmark, IMM Lock-in Risk Assessment.
- **Field-level permission**: section `section_lockin` + `lock_in_risk_ref`, `lock_in_score`, `mitigation_plan`, `mitigation_evidence` = **permlevel 1** (xác nhận trong `imm_tech_spec.json`).
- **User Permission**: filter row theo department/khối nếu áp dụng — *(Cần khảo sát match field cụ thể)*.

**Kỹ thuật**: Decision Table — mỗi (role × action × state) = 1 row, expected Allow/Deny.

### DocPerm — IMM Tech Spec

| Role | R | W | C | D | Submit | Amend | Permlevel 1 (lock_in_score, mitigation) |
|---|---|---|---|---|---|---|---|
| Spec User (HTM Engineer) | ✅ | ✅ (Draft/Reviewing) | ✅ | ❌ | ❌ | ❌ | ❌ |
| Needs Manager (KH-TC) | ✅ | ✅ (benchmark fields) | ❌ | ❌ | ❌ | ❌ | ❌ |
| Spec Manager (QA Risk) | ✅ | ✅ (infra/lock-in fields) | ❌ | ❌ | ❌ | ❌ | ✅ |
| Commissioning Manager | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| Procurement Manager (Board Approver) | ✅ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| System Admin | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

### DocPerm — IMM Market Benchmark

| Role | R | W | C | Submit |
|---|---|---|---|---|
| Spec User | ✅ | ✅ | ✅ | ❌ |
| Needs Manager | ✅ | ✅ | ✅ | ✅ |
| Spec Manager | ✅ | ❌ | ❌ | ❌ |
| Commissioning Manager | ✅ | ❌ | ❌ | ❌ |
| Procurement Manager | ✅ | ❌ | ❌ | ❌ |
| System Admin | ✅ | ✅ | ✅ | ✅ |

### DocPerm — IMM Lock-in Risk Assessment

| Role | R (permlevel 0) | R (permlevel 1: score) | W | C | Submit |
|---|---|---|---|---|---|
| Spec User | ✅ | ❌ | ❌ | ❌ | ❌ |
| Needs Manager | ✅ | ❌ | ❌ | ❌ | ❌ |
| Spec Manager (QA Risk) | ✅ | ✅ | ✅ | ✅ | ✅ |
| Commissioning Manager | ✅ | ❌ | ❌ | ❌ | ❌ |
| Procurement Manager | ✅ | ✅ | ❌ | ❌ | ❌ |
| System Admin | ✅ | ✅ | ✅ | ✅ | ✅ |

## VI.2. API security

- **Whitelist hygiene**: 17 endpoint đều `@frappe.whitelist()`; mutating endpoint dùng `methods=["POST"]` (xác nhận trong `api/imm02.py`). *(Cần khảo sát: docstring + `rbac.require()` từng endpoint.)*
- **CSRF**: Frappe default `X-Frappe-CSRF-Token` trên mọi POST.
- **Input validation**: Link field (`source_plan`, `device_model_ref`) validate trước khi dùng; JSON payload parse an toàn.
- **SQL injection**: parameterized query only; không f-string vào raw SQL.
- **Rate limit**: `draft_from_plan` ≤ 10 req/phút/user; `bulk_import_requirements` ≤ 5 req/phút/user; file upload max 5MB, chỉ `.xlsx/.xls/.csv`. *(Trạng thái thực thi: Cần khảo sát.)*

## VI.3. Audit trail integrity

Mọi mutation (lock/withdraw/reissue + transition) sinh `IMM Audit Trail` với actor + timestamp + hash SHA-256 chain. Verify endpoint phát hiện tamper. User KHÔNG có quyền edit/delete `IMM Audit Trail` (DocPerm + `on_trash` guard, ISO 13485 §7.5.9). (→ III.5 test cases.)

## VI.4. Authentication & session

Login Frappe default; session + SameSite cookie; lockout + password policy theo site config; API key cho integration; 2FA roadmap.

## VI.5. Data sensitivity

| Loại | Trường | Sensitivity | Bảo vệ |
|---|---|---|---|
| Lock-in risk | `lock_in_score`, `mitigation_plan`, `mitigation_evidence`, `lock_in_risk_ref` | Confidential | permlevel 1 (chỉ Spec Manager/Procurement Manager/Admin) |
| Benchmark giá | candidate price fields | Internal | DocPerm IMM Market Benchmark |
| Spec metadata | requirement, infra status | Internal | DocPerm read theo role |

Khẳng định: IMM-02 KHÔNG lưu patient/clinical data.

## VI.6. Vendor isolation

IMM-02 không cấp quyền cho role Vendor External: NCC KHÔNG truy cập Tech Spec / Benchmark / Lock-in (không có DocPerm vendor). Benchmark candidate là dữ liệu nội bộ thẩm định, không export ra ngoài. (→ III.6 low-role API call test.)

## VI.7. Secrets management

Cấm commit `.env`/credential; `site_config.json` không lên git; external token lưu `frappe.conf`; backup encrypt at-rest off-site.

## VI.8. Logging & monitoring

| Sự kiện | Log level | Where | Alert? |
|---|---|---|---|
| Lock/Withdraw/Reissue spec | INFO | IMM Audit Trail + app log | có (audit) |
| Gate fail (G01–G04) | WARNING | app log | không |
| Scheduler overdue/freshness | INFO | scheduler log | notification |

PII / token KHÔNG vào log.

## VI.9. Threat model (STRIDE-lite)

| # | Threat | Category | Vector | Likelihood | Impact | Mitigation |
|---|---|---|---|---|---|---|
| T01 | Session hijack tạo spec giả | Spoofing | session cookie | Medium | High | Frappe session + SameSite; API key cho integration |
| T02 | Sửa `lock_in_score` sau assess | Tampering | direct field write | Medium | High | permlevel 1 + auto-compute tại service layer |
| T03 | Submit spec không qua gate | Tampering | bypass workflow | Medium | High | service layer enforce G01–G04 trước transition; unit test gate (Live) |
| T04 | "Ai đã Lock spec?" không trace | Repudiation | thiếu audit | Low | High | IMM Audit Trail immutable: actor + timestamp + hash |
| T05 | HTM Engineer xem lock_in_score | Info disclosure | permlevel leak | Medium | Medium | permlevel 1 filter response theo role |
| T06 | Bulk import 10k rows timeout | Denial of service | oversized import | Low | Medium | max 200 row/import; file ≤ 5MB; rate limit |
| T07 | Spec User cố Lock spec | Elevation of privilege | low-role call mutating endpoint | Medium | High | workflow transition role check (Procurement Manager) + DocPerm |

## VI.10. Penetration test

Trước release đầu tiên: Burp/ZAP scan, sqlmap (an toàn), CSRF test, role escalation (Spec User → lock_spec). Report lưu `docs/security/`. *(Trạng thái: Cần khảo sát — chưa chạy.)*

## VI.11. Sign-off

| Role | Người | Ngày | Quyết định |
|---|---|---|---|
| Security Officer | *(Cần điền)* | | Pass / Pass with conditions / Fail |
| QA Lead | *(Cần điền)* | | |
| Module Owner (PTP Khối 1) | *(Cần điền)* | | |

---

# Phần VII — Code Quality

## VII.1. Tool matrix

| Tool | Mục tiêu | Target | Cadence |
|---|---|---|---|
| **SonarQube** (BE Python) | bug / smell / coverage | 0 critical bug, duplication < 5%, coverage ≥ 70%, cyclomatic ≤ 10/fn, security hotspot review 100% | mỗi PR (CI gate) |
| **Lighthouse** (FE — TechSpecDetail) | UX score | Performance ≥ 85, Accessibility ≥ 95, Best Practices ≥ 90 | mỗi release lớn + monthly |
| **ESLint + vue-tsc** (FE) | lint + types | 0 error (warning cho phép), `tsc --strict` 0 error | mỗi PR (CI gate) |
| **ruff + black** (BE Python) | lint + format | 0 error, black enforced | mỗi PR (CI gate) |
| **Bundle size** (chunk imm02) | budget | ≤ 120 KB gzipped | mỗi PR FE (CI report) |
| **k6** (perf) | latency | `list_tech_specs` p95 < 1.5s @ 50 concurrent; `bulk_import` < 10s @ 100 row | pre-release |

## VII.2. Cadence

- SonarQube: mỗi PR (fail nếu Quality Gate fail).
- Lighthouse: mỗi release lớn + monthly audit.
- ESLint / ruff: mỗi PR (CI gate).
- Bundle size: mỗi PR FE (CI report, fail nếu vượt budget).
- Screenshot SonarQube + Lighthouse gắn vào [09 §Release Notes](./09_Release.md) khi báo cáo final.

---

# Phụ lục A — Template per UAT scenario

```markdown
### UAT-IMM-02-<NN> — <Tên>

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
### TC-IMM-02-<LAYER>-<NN> — <Tên>

**Component (I.1)**: <…>
**Liên kết**: US-<NN> | BR-<NN> | ACT-<NN>
**Kỹ thuật (II.1/II.2)**: BVA boundary `total_mandatory=7` (G01)
**Priority (I.3)**: Critical / High / Medium / Low
**Test type**: Unit / Integration / API / E2E
**Pre-condition**: <fixture / state setup>

**Input**:
- <field>: <value>

**Steps**:
1. <…>
2. <…>

**Expected**:
- ServiceError(code=BUSINESS_RULE, message contains "G01")
- doc.workflow_state unchanged

**Post-condition**: <DB rollback / fixture cleanup>
```

# Phụ lục C — Workflow State Transition Test template

```markdown
### TC-IMM-02-WF-<NN> — <action>: <from> → <to>

**Workflow JSON**: `assetcore/assetcore/workflow/imm_02_spec_workflow.json`
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
- [x] Test class structure cho service public function (I.1) — 7 class Live + gap liệt kê
- [ ] ≥ 1 happy + 1 negative test mỗi function — gap: VR01/G02/G03/scheduler chưa có
- [ ] Workflow transitions cover 100% (9 transition) — chưa có `test_imm02_workflow.py`
- [ ] Audit chain test (intact + tampered) — Planned
- [ ] API test ≥ 60% coverage + permission matrix — chưa có `test_imm02_api.py`
- [x] Performance target xác định (III.8)
- [x] CI command chạy clean (`bench run-tests --module assetcore.tests.test_imm02`)
- [ ] SonarQube Quality Gate pass + Lighthouse ≥ target — chưa chạy/báo cáo

## IV. Traceability
- [x] IV.1 US → Test: mọi US có ≥ 1 Test ID
- [x] IV.2 BR → Test: mọi BR có dòng (BR-02-02/06 đủ happy+negative; BR-02-01/03/04/07 còn Planned)
- [ ] IV.3 Component → Test: Critical/High đạt coverage target — workflow + audit + G02/G03 chưa cover

## V. UAT
- [x] Mỗi US có ≥ 1 UAT scenario (12 scenario)
- [x] ≥ 1 negative + permission + audit verify scenario
- [ ] Test data seed script chạy được — `scripts/uat/uat_imm02.py` Cần khảo sát
- [ ] Tester accounts đã tạo ở UAT site — liệt kê nhưng chưa xác nhận tạo
- [x] Sign-off section sẵn sàng

## VI. Security
- [x] DocPerm matrix đầy đủ (3 DocType, Decision Table)
- [x] Mọi field nhạy cảm có permlevel ≠ 0 (lock_in_score + mitigation = permlevel 1, xác nhận trong JSON)
- [ ] SQL injection + CSRF test pass — chưa chạy
- [ ] Audit chain test pass (intact + tampered) — Planned
- [ ] Vendor isolation test pass (low-role API call) — Planned
- [x] Threat model đủ 6 STRIDE với mitigation (7 threat)
- [ ] Sign-off đầy đủ trước go-live — chờ điền người ký

## VII. Code Quality
- [ ] SonarQube Quality Gate pass — chưa chạy
- [ ] Lighthouse ≥ target — chưa chạy
- [ ] Bundle size ≤ budget — chưa đo
- [ ] Screenshot báo cáo gắn vào file 09 — chờ release
