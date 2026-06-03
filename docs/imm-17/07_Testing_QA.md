# 07 — Kiểm thử & An ninh (Testing & QA & Security)

| Mục | Giá trị |
|---|---|
| Module | IMM-17 — Phân tích dự đoán (Predictive Analytics) |
| Phạm vi | Per-module |
| Owner | QA Lead + Security Officer |
| Liên kết | 02 Analysis (US, BR, Activity, BPMN) · 03 Diagrams · 04 Backend · 05 API · 06 Frontend |

> **Mục đích**: Suy ra test case có hệ thống từ phân tích (file 02) bằng kỹ thuật black-box + white-box, không liệt kê tự phát. Bao gồm: phân tích đối tượng test → chọn kỹ thuật → viết test → traceability → UAT → security → code quality. Q3 là gate go-live.

> **Trạng thái IMM-17**: Module CHƯA scaffold BE (không có `services/imm17.py`, `api/imm17.py`, test). File này là **kế hoạch (planning skeleton)** — đầy đủ cấu trúc, nhưng các test case ID, coverage %, baseline KPI, fieldname DocType, shape endpoint **chưa chốt** và được đánh dấu `⬜ Planned` hoặc *(Cần thiết kế khi scaffold BE)* / *(Cần khảo sát baseline)*. Test case ID + coverage % chốt trong sprint Wave 3.

---

# Phần I — Test Analysis (Phân tích đối tượng test)

> Mục tiêu Phần I: trả lời 4 câu hỏi trước khi viết test case: (1) test cái gì (component inventory) (2) suy ra từ đâu (US/BR/Activity) (3) ưu tiên cái nào (risk) (4) loại trừ cái nào (out-of-scope).

## I.1. Component Inventory — Liệt kê phần mềm cần test

Liệt kê artefact test được của IMM-17. Tên DocType / service / endpoint lấy từ 04 §1/§3 và 05 §1 (đã pre-declare). Field detail + signature chi tiết sẽ scaffold trong sprint Wave 3 → đánh dấu rõ ở cột ghi chú.

→ Nguồn: 04 Backend §1 DocType, §3 Service, §5 Hook/Scheduler · 05 API §1 Catalog · 06 Frontend §Components.

| # | Component | Loại | File / Tên | Test layer áp dụng |
|---|---|---|---|---|
| 1 | `AC Predictive Insight` | DocType | `ac_predictive_insight.json` *(field detail: Cần thiết kế khi scaffold BE)* | Integration (lifecycle, on_insert audit) |
| 2 | `IMM Predictive Model` | DocType | `imm_predictive_model.json` | Integration (versioning, chỉ 1 Active) |
| 3 | `IMM Predictive Run Log` | DocType | `imm_predictive_run_log.json` | Integration (status, duration, asset_count) |
| 4 | `IMM Predictive Feature Snapshot` (Wave 3 cuối) | DocType | *(Cần thiết kế khi scaffold BE)* | Integration (replay/audit) |
| 5 | `IMM Predictive Model` workflow (Draft→Validated→Active→Retired) | Workflow | *(Chưa quyết định — 04 §2: có thể dùng workflow đơn giản)* | Integration (state transition) nếu áp dụng |
| 6 | `run_weekly_pipeline` | Service function | `services/imm17.py::run_weekly_pipeline` *(sẽ scaffold)* | Unit + Cron simulation |
| 7 | `run_for_asset` | Service function | `services/imm17.py::run_for_asset` | Unit + API integration |
| 8 | `extract_history` | Repository / DAO | `repositories/predictive_repo.py::get_*_history` | Integration (DB, read-only) |
| 9 | `build_features` | Service function | `services/imm17.py::build_features` | Unit (BVA/EP — feature vector) |
| 10 | `score` | Service function | `services/imm17.py::score` | Unit (EP — output ∈ [0,1], deterministic) |
| 11 | `persist_insight` | Service function | `services/imm17.py::persist_insight` | Integration (insert + audit, no double-insert) |
| 12 | `emit_replacement_signal` | Service function + Lifecycle event | `services/imm17.py::emit_replacement_signal` → `replacement_signal_emitted` | Integration (audit chain, threshold gate) |
| 13 | `acknowledge_insight` | Service function | `services/imm17.py::acknowledge_insight` | Unit + API (decision EP) |
| 14 | `register_model` / `activate_model` | Service function | `services/imm17.py::register_model`, `activate_model` | Unit (versioning) + API |
| 15 | `whatif_pm_cycle` | Service function | `services/imm17.py::whatif_pm_cycle` | Unit (read-only, KHÔNG ghi DB/audit) |
| 16 | `check_drift` / `retrain_trigger` | Scheduler job | `services/imm17.py::check_drift`, `retrain_trigger` *(Cần thiết kế khi scaffold BE)* | Unit + Cron simulation |
| 17 | API endpoints (10) | API endpoint | `api/imm17.py::*` (xem I.2 / 05 §1) | API integration |
| 18 | Predictive cockpit view + composable | FE view / composable | `frontend/src/views/PredictiveCockpit*.vue` *(Cần thiết kế khi scaffold BE)* | E2E (Playwright) |
| 19 | Pinia store insight | Pinia store | `frontend/src/stores/predictive*.ts` *(Cần thiết kế khi scaffold BE)* | Unit (vitest) |

## I.2. Trace nguồn test — User Stories, Activity Flows, Business Rules

3 bảng dẫn từ artefact phân tích (file 02) sang test layer. IMM-17 §02 chưa có bảng "User Story" / "Business Rule" hình thức riêng — dùng FR (02 §I.7), NFR (02 §I.8), UC (02 §III) và các ràng buộc thiết kế (02 §VI) làm nguồn tương đương; quy ước rằng US/BR/ACT chính thức sẽ chốt khi phân tích chi tiết Wave 3.

→ Nguồn: 02 §I.7 Functional Requirements · 02 §I.8 NFR · 02 §III Use Cases · 02 §II BPMN · 02 §VI Ràng buộc thiết kế.

### I.2.a. Từ User Story / Functional Requirement
| FR/US ID | Tiêu đề ngắn | Acceptance Criteria # | Test layer dự kiến |
|---|---|---|---|
| FR-17-01 | Tổng hợp feature từ Lifecycle Event + WO history | *(AC chi tiết: Chờ phân tích Wave 3)* | Unit + Integration |
| FR-17-02 | Sinh `AC Predictive Insight` per asset/kỳ chạy | *(Chờ phân tích)* | Integration + UAT |
| FR-17-03 | Phát signal `replacement_signal_emitted` qua Lifecycle Event | *(Chờ phân tích)* | Integration (audit) + UAT |
| FR-17-04 | Cockpit top-N + filter khoa/loại | *(Chờ phân tích)* | E2E + UAT |
| FR-17-05 | Action: tạo PM Work Order theo insight | *(Chờ phân tích)* | Integration + UAT |
| FR-17-06 | Action: tạo Incident nếu severity High | *(Chờ phân tích)* | Integration + UAT |
| FR-17-07 | What-if PM cycle → failure probability | *(Chờ phân tích)* | Unit + UAT |
| FR-17-08 | Model versioning + dataset snapshot ref | *(Chờ phân tích)* | Unit + Integration |
| FR-17-09 | Audit trail mọi inference | *(Chờ phân tích)* | Integration (audit chain) |
| FR-17-10 | Vendor ML integration (INT-13) — Wave 3 cuối | *(Chờ phân tích)* | Integration (defer) |

### I.2.b. Từ Business Rule (suy từ Ràng buộc 02 §VI + Compliance §I.6)
| BR ID | Phát biểu | Component liên quan (I.1) | Kỹ thuật test phù hợp |
|---|---|---|---|
| BR-17-01 *(dự kiến)* | `score` output phải ∈ [0,1] và deterministic với cùng input + model_version | `score` (#10) | BVA + EP |
| BR-17-02 *(dự kiến)* | Insight không double-insert cho cùng asset/kỳ chạy (idempotent theo run_id) | `persist_insight` (#11) | Decision Table |
| BR-17-03 *(dự kiến)* | `emit_replacement_signal` chỉ emit khi `replacement_score ≥ threshold` | `emit_replacement_signal` (#12) | BVA (biên threshold) + Decision Table |
| BR-17-04 *(dự kiến)* | Không cho acknowledge 2 lần cùng insight | `acknowledge_insight` (#13) | Decision Table (state ACK) |
| BR-17-05 *(dự kiến)* | `whatif_pm_cycle` KHÔNG ghi DB, KHÔNG ghi audit (read-only) | `whatif_pm_cycle` (#15) | Use Case (assert no-write) |
| BR-17-06 *(dự kiến)* | Chỉ 1 `IMM Predictive Model` ở trạng thái Active tại 1 thời điểm | `activate_model` (#14) | Decision Table |
| BR-17-07 *(dự kiến)* | Asset thiếu history (< ngưỡng) → skip, raise `IMM17_INSUFFICIENT_HISTORY`, không tạo insight giả | `run_for_asset` (#7) | EP + BVA (biên history) |
| BR-17-08 *(dự kiến)* | Inference + signal + ack + model activate phải sinh `IMM Audit Trail` (R-04) | audit chain (#12) | Use Case + tamper test |

> Phát biểu BR trên suy từ 02 §VI Ràng buộc + §I.6 Compliance + 02 mục Unit test cũ; ID chính thức chốt khi phân tích Wave 3.

### I.2.c. Từ Activity Flow / BPMN
| Activity ID | Use Case | Branch chính | Branch ngoại lệ |
|---|---|---|---|
| ACT-17-PIPE *(dự kiến)* | UC-17-01 Cron predictive run | Extract → Feature → Inference → Persist → (signal nếu vượt threshold) | Asset thiếu history (skip), data quality gate fail, scheduler retry |
| ACT-17-COCKPIT *(dự kiến)* | UC-17-02 Xem cockpit | Filter → drill-down → contributing factors | Không có insight 7 ngày gần nhất |
| ACT-17-ACK *(dự kiến)* | UC-17-03 Acknowledge signal | Mở Replacement Review (→IMM-13) / open_pm (→IMM-08) | Bỏ qua + ghi lý do; ack trùng (đã ACK) |
| ACT-17-MODEL *(dự kiến)* | UC-17-04 Deploy model mới | Register → activate → run kế tiếp dùng version mới | Model chưa pass validation; version không tồn tại |
| ACT-17-WHATIF *(dự kiến)* | UC-17-05 What-if PM cycle | Set giả định cycle → ước lượng → export | Model chưa ổn định (defer) |

## I.3. Risk-based Priority

Đánh giá rủi ro cho component ở I.1. Test case priority khớp risk: Critical/High = bắt buộc cover trong sprint Wave 3; Medium/Low = best-effort.

| Component (I.1) | Likelihood (1-5) | Impact (1-5) | Risk = L×I | Priority |
|---|---|---|---|---|
| `emit_replacement_signal` + audit chain (#12) | 4 | 5 | 20 | **Critical** |
| `persist_insight` idempotency + audit (#11) | 4 | 4 | 16 | **Critical** |
| `acknowledge_insight` (state + cross-module action) (#13) | 3 | 5 | 15 | **Critical** |
| `score` correctness ∈ [0,1] deterministic (#10) | 3 | 4 | 12 | High |
| `activate_model` (chỉ 1 Active) (#14) | 3 | 4 | 12 | High |
| Permission isolation Vendor / endpoint RBAC (#17) | 3 | 4 | 12 | High |
| `run_weekly_pipeline` cron (retry, data gate) (#6) | 3 | 3 | 9 | Medium |
| `build_features` (NaN-robust) (#9) | 3 | 3 | 9 | Medium |
| `whatif_pm_cycle` read-only (#15) | 2 | 3 | 6 | Medium |
| Cockpit FE view (#18) read-only | 2 | 2 | 4 | Low |
| `run_logs` / `list_models` read-only (#17) | 1 | 2 | 2 | Low |

**Quy ước priority**:
- **Critical** (R ≥ 15): test trước, fail = block release
- **High** (10 ≤ R < 15): bắt buộc trước go-live
- **Medium** (5 ≤ R < 10): trong sprint khi có thời gian
- **Low** (R < 5): chỉ test khi báo cáo bug

## I.4. Scope

**In-scope** (theo Component Inventory I.1):
- Service layer pipeline: extract → feature → score → persist → emit signal (#6–#12).
- Insight lifecycle phi-workflow: NEW → ACKED → ACTIONED/STALE qua field + audit (#1, #13).
- Audit chain integrity cho mọi inference/signal/ack/model-activate (R-04, NFR-17-03).
- Model governance: register/activate/version, chỉ 1 Active (#2, #14).
- API RBAC + permission isolation (Vendor Engineer KHÔNG có quyền) (#17).

**Out-of-scope** (kèm lý do):
- Performance/scale test (5,000 asset ≤ 30 phút) — giao Phần III.8, cần dataset thật.
- Model quality offline (precision/recall/AUC, fairness slice, drift) — chạy ở notebook offline ngoài CI; báo cáo đính kèm `IMM Predictive Model` record (xem mục Model quality III.9).
- IoT telemetry real-time (INT-13) — defer Wave 3 cuối / Wave 4 (02 §I.4 out-of-scope).
- Vendor ML federated learning — Wave 4.
- Cross-module sâu với IMM-13/IMM-15 — chỉ smoke ở Wave 3 đầu (02 §IV).

**Assumptions**:
- IMM-07 KPI snapshot DocType đã ship + ≥6 tháng dữ liệu (04 §8).
- IMM-08/09/11/12 đã ship Wave 1 (đã có).
- Lifecycle Event Engine + `IMM Audit Trail` ổn định, verify pass ≥100 asset mẫu.
- Test users đủ role (không chỉ Admin), browser Chromium hiện hành cho Playwright.

---

# Phần II — Test Design Techniques (Kỹ thuật thiết kế test case)

> Mục tiêu Phần II: chọn đúng kỹ thuật cho từng loại input/logic. Mỗi test phải truy được về 1 kỹ thuật ở dưới.

## II.1. Black-box techniques

Mỗi dòng ghi rõ áp dụng vào component nào ở I.1.

| Kỹ thuật | Khi nào dùng | Áp dụng vào IMM-17 | Số test sinh ra (rule of thumb) |
|---|---|---|---|
| **Equivalence Partitioning (EP)** | Input có miền giá trị chia nhóm tương đương | `acknowledge_insight.decision` (open_replacement / open_pm / dismiss / invalid), severity enum, role partition (#13, #17) | 1 test/partition |
| **Boundary Value Analysis (BVA)** | Numeric / date field có biên | `replacement_score` quanh threshold (#12), history length quanh ngưỡng "đủ dữ liệu" (#7), `score` ∈ [0,1] biên 0/1 (#10), `proposed_cycle_months` (#15) | 2-3 test/biên: min-1, min, min+1 |
| **Decision Table** | Multi-condition rule | BR-17-02 idempotency, BR-17-03 emit-signal gate, BR-17-06 chỉ-1-Active, BR-17-04 ack-trùng | 2^N rút gọn theo equivalence |
| **State Transition Testing** | Insight lifecycle NEW→ACKED→ACTIONED/STALE; `IMM Predictive Model` Draft→Validated→Active→Retired (nếu workflow) | #1, #2, #5 | Mỗi transition + invalid transition |
| **Use Case Testing** | End-to-end actor flow | UAT scenarios (Phần V), API integration, what-if no-write assert | 1/main + 1/alt + 1/exception |
| **Pairwise / Combinatorial** | Nhiều filter optional kết hợp | `list_insights` / `cockpit_summary` filter (asset × severity × date range × khoa) | Min set cover all pairs |
| **Error Guessing** | Lỗi từ kinh nghiệm: null, empty, unicode, race | Mọi endpoint nhận user input; cron partial-fail / lock | Bổ sung — không thay thế kỹ thuật khác |

## II.2. White-box techniques

| Kỹ thuật | Áp dụng vào | Tiêu chí đạt | Công cụ |
|---|---|---|---|
| **Statement coverage** | Service functions ở I.1 (#6–#16) | ≥ 85% line | `coverage report` |
| **Branch / Decision coverage** | Functions có if/else, try/except (pipeline, gate threshold, idempotency) | ≥ 80% branch | `coverage --branch` |
| **Condition / MC/DC** | Gate logic `emit_replacement_signal` (threshold AND severity), `activate_model` (single-Active) | Mỗi sub-condition kiểm soát outcome độc lập | Manual test design + coverage |
| **Path coverage** | `score` / `build_features` core ≤ 20 LOC | Toàn bộ path (loop = 0,1,N — asset có 0 / 1 / N event) | Manual |

> Ưu tiên Branch coverage cho service layer; MC/DC chỉ áp dụng vào gate logic emit-signal + model activation.

## II.3. Mapping Component → Kỹ thuật

| Loại component | Kỹ thuật chính | Kỹ thuật phụ |
|---|---|---|
| Score / feature builder (`score`, `build_features`) | BVA + EP | Path coverage |
| Gate logic (`emit_replacement_signal`, `activate_model`) | Decision Table | MC/DC |
| Insight lifecycle / Model workflow | State Transition | Use Case |
| Service function pure (`whatif_pm_cycle`) | EP + Branch coverage | BVA |
| API endpoint (`api/imm17.*`) | Use Case + EP (permission) | Pairwise (filter input) |
| Scheduler / cron (`run_weekly_pipeline`, `check_drift`) | Use Case (state setup → run → assert) | Error guessing (lock, partial fail, retry) |
| FE cockpit (Playwright) | Use Case end-to-end | Error guessing (network 4xx/5xx, role gate) |

---

# Phần III — Test Plan (Kế hoạch thực thi)

## III.1. Test Pyramid

Phần lớn test ở Service unit; ít test ở E2E. Tỷ lệ dự kiến cho IMM-17 (sẽ khớp số liệu thực khi scaffold Wave 3):

```
                  ┌────────────┐
                  │  E2E / UAT │   ~5%
                 ─┴────────────┴─
              ┌──────────────────────┐
              │   API Integration    │   ~15%
             ─┴──────────────────────┴─
          ┌────────────────────────────────┐
          │  DocType lifecycle + audit     │   ~25%
         ─┴────────────────────────────────┴─
      ┌────────────────────────────────────────────┐
      │     Unit — Service (pipeline + scoring)    │   ~55%
     ─┴────────────────────────────────────────────┴─
```

> IMM-17 không có Frappe Workflow cho insight (04 §2) → tầng "Workflow transition" được thay bằng DocType lifecycle + audit; nếu `IMM Predictive Model` dùng workflow thì bổ sung ở III.4. → CLAUDE.md §17 (TDD mandatory).

## III.2. Unit test — Service Layer

File `tests/test_imm17.py` *(sẽ tạo Wave 3)*. Mỗi test class trace về ≥ 1 dòng I.1. Cases hiện là dự kiến — số chốt khi scaffold.

| Test class | Function cover (I.1) | Kỹ thuật | Cases (happy/negative) — dự kiến |
|---|---|---|---|
| `TestExtractHistory` | `extract_history` (#8) | EP | trả đúng range / không leak record asset khác — ⬜ Planned |
| `TestBuildFeatures` | `build_features` (#9) | BVA + EP | feature vector đủ chiều, không NaN, robust asset thiếu data — ⬜ Planned |
| `TestScore` | `score` (#10) | BVA + EP | output ∈ [0,1], deterministic cùng input+version — ⬜ Planned |
| `TestPersistInsight` | `persist_insight` (#11) | Decision Table | tạo đúng record + audit, không double-insert — ⬜ Planned |
| `TestEmitReplacementSignal` | `emit_replacement_signal` (#12) | BVA + Decision Table | chỉ emit khi vượt threshold, idempotent theo run_id — ⬜ Planned |
| `TestAcknowledgeInsight` | `acknowledge_insight` (#13) | Decision Table + EP | state→ACKED, audit actor+reason, không ack 2 lần — ⬜ Planned |
| `TestModelGovernance` | `register_model`/`activate_model` (#14) | Decision Table | versioning đúng, chỉ 1 Active — ⬜ Planned |
| `TestWhatIfPmCycle` | `whatif_pm_cycle` (#15) | Use Case | KHÔNG ghi DB, KHÔNG ghi audit — ⬜ Planned |

> Dùng `SimpleNamespace` cho test thuần công thức (`score`, `build_features`) — chạy ms-level, không cần fixture cleanup. Coverage % gán khi sprint Wave 3 (CONVENTIONS.md §6: tối thiểu 70%).

## III.3. Integration — DocType lifecycle

File `tests/test_ac_predictive_insight_doctype.py` *(sẽ tạo Wave 3)*. Cover hook `validate / before_save / on_insert (→ log_audit_event, 04 §5.2)`.

| Test | Setup | Action | Assert | Kỹ thuật |
|---|---|---|---|---|
| `test_insight_on_insert_audit` | 1 asset + feature snapshot | `doc.insert()` | `IMM Audit Trail` entry tạo, hash nối chain | EP |
| `test_insight_no_double_insert` | insight đã có cho asset/kỳ | insert lần 2 cùng run_id | skip / raise, không double | Decision Table |
| `test_model_single_active` | 2 model version | activate version B | chỉ B Active, A → non-Active | Decision Table |

> Insight không submittable (04 §1) nên không có `on_submit/on_cancel`. Fixture trong `setUpClass` phải có `tearDownClass` purge — xem `assetcore-test` LL-TEST-17.

## III.4. Integration — Workflow transitions

IMM-17 **không** dùng Frappe Workflow cho `AC Predictive Insight` (04 §2): insight là output append-only, lifecycle qua field `acknowledged` + audit, không qua state machine Frappe. → 0 workflow transition bắt buộc cho insight.

`IMM Predictive Model` **có thể** dùng workflow đơn giản Draft → Validated → Active → Retired (04 §2 — quyết định trong sprint Wave 3). Nếu chốt dùng, bảng dưới được điền và đếm transition bằng `python3 -c "import json; print(len(json.load(open('<path>.json'))['transitions']))"`:

| Transition | From → To | Role required | Test pass | Test fail (wrong role / gate fail) |
|---|---|---|---|---|
| validate | Draft → Validated | Data Scientist | ⬜ Planned | ⬜ Planned |
| activate | Validated → Active | IMM System Admin | ⬜ Planned | ⬜ Planned |
| retire | Active → Retired | IMM System Admin | ⬜ Planned | ⬜ Planned |

> *(Cần thiết kế khi scaffold BE — workflow `IMM Predictive Model` chưa quyết định.)* Kỹ thuật: State Transition Testing — mỗi edge = 1 test pass + 1 test fail.

## III.5. Integration — Audit chain integrity

File `tests/test_imm17_audit.py` *(sẽ tạo Wave 3)*. 2 test chính (NFR-17-03, R-04):
- (a) Sau N inference + M ack, `verify_audit_chain(asset)` trả `True` end-to-end (SHA-256).
- (b) Khi 1 entry bị tamper (sửa `change_summary`), verify trả `chain_broken=true`.

Các sự kiện bắt buộc sinh audit (04 §7): inference completed / insight acknowledged / model activated|retired / threshold thay đổi.

→ Nguồn: 04 Backend §7 Audit Trail · `IMM Audit Trail` DocType · 02 §I.6 Compliance.

## III.6. API test

File `tests/test_imm17_api.py` *(sẽ tạo Wave 3)*. Endpoint từ 05 §1. Cover happy + envelope `ok=true`, invalid params, FORBIDDEN, pagination, idempotent retry.

| Test | Endpoint (05 §1) | Verify | Kỹ thuật |
|---|---|---|---|
| `test_run_for_asset_ok` | `api/imm17.run_for_asset` | `ok=true`, insight tạo | Use Case |
| `test_list_insights_filter` | `api/imm17.list_insights` | filter asset/severity/date, pagination 50/page | Pairwise + EP |
| `test_get_insight_factors` | `api/imm17.get_insight` | trả `contributing_factors` (NFR-17-04) | Use Case |
| `test_acknowledge_invalid_decision` | `api/imm17.acknowledge_insight` | `code=IMM17_INVALID_ACK_DECISION` | EP |
| `test_acknowledge_already_ack` | `api/imm17.acknowledge_insight` | `code=IMM17_INSIGHT_ALREADY_ACK` | Decision Table |
| `test_whatif_readonly` | `api/imm17.whatif_pm_cycle` | trả ước lượng, KHÔNG tạo record/audit | Use Case |
| `test_register_model_lowrole` | `api/imm17.register_model` (non Data Scientist) | `code=FORBIDDEN` | EP (permission partition) |
| `test_activate_model_not_found` | `api/imm17.activate_model` | `code=IMM17_MODEL_NOT_FOUND` | EP |
| `test_insufficient_history` | `api/imm17.run_for_asset` (asset mới) | `code=IMM17_INSUFFICIENT_HISTORY` | BVA |
| `test_vendor_isolation` | `api/imm17.list_insights` (Vendor Engineer) | `code=FORBIDDEN` / empty | EP (permission) |

> ErrorCode lấy từ 05 §3 (dự kiến) — chốt khi BE scaffold, KHÔNG bịa code mới.

## III.7. E2E browser (Playwright)

Dùng cho flow UI khó cover bằng API: cockpit top-N render + drill-down contributing factors, filter cascade theo khoa/loại, nút action (Mở Replacement Review / open PM) hiển thị theo role, ẩn menu IMM-17 với Vendor Engineer.

→ Nguồn: `assetcore-test` skill Phần 2 (Playwright MCP recipes + R-1..R-9 data rules).

## III.8. Performance test

| Metric | Target | Method |
|---|---|---|
| Pipeline weekly 5,000 asset × 24 tháng | ≤ 30 phút (NFR-17-01) *(Cần khảo sát baseline)* | `time bench execute assetcore.services.imm17.run_weekly_pipeline` |
| `list_insights` p95 (≤ 200 row) | ≤ 400ms *(target — chưa benchmark)* | k6 GET `list_insights` |
| `cockpit_summary` p95 | ≤ 600ms *(target)* | k6 GET (cache 5 phút server-side, 05 §5) |

> Profiling: `cProfile` + Frappe SQL profiler. Nếu vượt → parallel asset processing, feature caching, batch DB read. Benchmark trên dataset thật 5,000 asset.

## III.9. Test data & Fixtures

| Loại | Cách seed | File |
|---|---|---|
| Master data (Department, Asset Category, Vendor) | `fixtures/*.json` (cài qua `bench migrate`) | `assetcore/fixtures/` |
| Asset + ≥12 tháng lifecycle/WO/calibration history | `test_records.json` per DocType + script seed | `<doctype>/test_records.json` *(Cần thiết kế khi scaffold BE)* |
| Model offline quality dataset (precision/recall/AUC, slice khoa/vendor, drift KS-test) | notebook offline + validation report đính kèm `IMM Predictive Model` | offline (ngoài CI) |
| UAT seed | Python script | `assetcore/scripts/uat/uat_imm17.py` *(sẽ tạo Wave 3)* |

> Model phải pass tất cả check offline (Precision ≥ KPI-17-01 target, Recall ≥ KPI-17-02 target, AUC-ROC *(Cần khảo sát baseline)*, slice spread ≤ 15% — không bias, drift KS-test p > 0.05) trước khi `activate_model`. UAT data phải thực tế (tên BV VN, mã NCC chuẩn). Backend test fixture mới dùng prefix `_Test` — xem `assetcore-test` R-0/R-1.

## III.10. Run commands & Coverage gate

```bash
# Module test (sau khi scaffold Wave 3)
bench --site <site> run-tests --app assetcore --module assetcore.tests.test_imm17
# Coverage
coverage run -m unittest assetcore.tests.test_imm17 && coverage report
# Audit chain smoke
bench --site <site> run-tests --module assetcore.tests.test_imm17_audit
```

| Layer | Target coverage | Đo |
|---|---|---|
| Service (`services/imm17.py`) | ≥ 85% line + ≥ 80% branch *(đạt khi scaffold)* | `coverage --branch` |
| DocType lifecycle | ≥ 70% *(target)* | `coverage report` |
| API (`api/imm17.py`) | ≥ 60% *(target)* | `coverage report` |
| Frontend (vue-tsc) | 0 error | `npm run build` |

---

# Phần IV — Traceability Matrices

> 3 ma trận theo 3 hướng. Mọi test ở Phần III phải xuất hiện ở cả 3 bảng. IMM-17 chưa scaffold → cột Test ID = `⬜ Planned`, sẽ điền ID thật khi viết test Wave 3.

## IV.1. US/FR → Test mapping

| FR/US ID | AC | Test ID (III.x) | Layer | Status |
|---|---|---|---|---|
| FR-17-01 | *(Chờ phân tích)* | `TestExtractHistory` / `TestBuildFeatures` | Unit+Integration | ⬜ Planned |
| FR-17-02 | *(Chờ phân tích)* | `TestPersistInsight` | Integration | ⬜ Planned |
| FR-17-03 | *(Chờ phân tích)* | `TestEmitReplacementSignal` + audit | Integration | ⬜ Planned |
| FR-17-04 | *(Chờ phân tích)* | E2E cockpit (III.7) | E2E | ⬜ Planned |
| FR-17-05 | *(Chờ phân tích)* | UAT-IMM-17-03 + Integration | Integration+UAT | ⬜ Planned |
| FR-17-06 | *(Chờ phân tích)* | Integration severity High | Integration | ⬜ Planned |
| FR-17-07 | *(Chờ phân tích)* | `TestWhatIfPmCycle` | Unit | ⬜ Planned |
| FR-17-08 | *(Chờ phân tích)* | `TestModelGovernance` | Unit+Integration | ⬜ Planned |
| FR-17-09 | *(Chờ phân tích)* | `test_imm17_audit` (III.5) | Integration | ⬜ Planned |
| FR-17-10 | *(Chờ phân tích)* | defer Wave 3 cuối | Integration | ⬜ Planned (defer) |

## IV.2. BR → Test mapping

| BR ID | Phát biểu (rút gọn) | Test ID | Kỹ thuật | Happy / Negative |
|---|---|---|---|---|
| BR-17-01 | `score` ∈ [0,1], deterministic | `TestScore` | BVA+EP | ⬜ Planned |
| BR-17-02 | Insight idempotent (no double-insert) | `TestPersistInsight` | Decision Table | ⬜ Planned |
| BR-17-03 | Emit signal chỉ khi ≥ threshold | `TestEmitReplacementSignal` | BVA+Decision Table | ⬜ Planned |
| BR-17-04 | Không ack 2 lần | `TestAcknowledgeInsight` | Decision Table | ⬜ Planned |
| BR-17-05 | What-if read-only | `TestWhatIfPmCycle` | Use Case | ⬜ Planned |
| BR-17-06 | Chỉ 1 model Active | `TestModelGovernance` | Decision Table | ⬜ Planned |
| BR-17-07 | Asset thiếu history → skip + error | `test_insufficient_history` | EP+BVA | ⬜ Planned |
| BR-17-08 | Mọi inference/ack/activate sinh audit | `test_imm17_audit` | Use Case + tamper | ⬜ Planned |

## IV.3. Component → Test mapping

| Component (I.1) | Test ID | Test layer | Coverage % | Risk priority (I.3) |
|---|---|---|---|---|
| `services/imm17::emit_replacement_signal` (#12) | `TestEmitReplacementSignal` | Unit+Integration | ⬜ (target ≥ 85%) | Critical |
| `services/imm17::persist_insight` (#11) | `TestPersistInsight` | Integration | ⬜ (target ≥ 85%) | Critical |
| `services/imm17::acknowledge_insight` (#13) | `TestAcknowledgeInsight` | Unit+API | ⬜ (target ≥ 85%) | Critical |
| `services/imm17::score` (#10) | `TestScore` | Unit | ⬜ (target ≥ 85%) | High |
| `services/imm17::activate_model` (#14) | `TestModelGovernance` | Unit | ⬜ (target ≥ 85%) | High |
| `api/imm17::*` RBAC (#17) | `test_vendor_isolation`, `test_*_lowrole` | API | ⬜ (target ≥ 60%) | High |
| `services/imm17::whatif_pm_cycle` (#15) | `TestWhatIfPmCycle` | Unit | ⬜ (target ≥ 85%) | Medium |

---

# Phần V — UAT Script

## V.1. Phạm vi UAT

- **In-scope**: scenario theo FR/UC (V.4) — cron run, cockpit, acknowledge, what-if, model deploy, audit verify, permission.
- **Out-of-scope**: performance (III.8), security pentest (Phần VI), model quality offline (III.9 notebook).
- **Pre-condition**: site UAT deploy version IMM-17 Wave 3 *(version chốt khi release)*, fixture loaded (asset + ≥12 tháng history), ≥1 model `Validated`+`Active`, tester accounts active.

## V.2. Tester accounts

| Username | Role | Vai trò UAT |
|---|---|---|
| `uat.opsmgr@<bv>` | IMM Operations Manager | Xem cockpit, acknowledge signal |
| `uat.htmeng@<bv>` | IMM HTM Engineer | Acknowledge, what-if PM cycle |
| `uat.datasci@<bv>` | Data Scientist (custom — Wave 3) | Register/activate model |
| `uat.auditor@<bv>` | IMM Auditor | Xem run logs + verify audit chain |
| `uat.sysadmin@<bv>` | IMM System Admin | Activate model, run on-demand |
| `uat.vendor@<bv>` | Vendor Engineer | Verify KHÔNG thấy menu/data IMM-17 (FORBIDDEN) |

> Phải có account role thấp (Vendor Engineer) để cover FORBIDDEN. Tài khoản tạo khi setup UAT site Wave 3.

## V.3. Test data đã seed

| DocType | Số lượng | Ghi chú |
|---|---|---|
| `AC Asset` (active, ≥12 tháng history) | ≥ 10 *(chốt khi seed)* | đủ happy + edge; ≥1 asset critical có MTBF giảm |
| `Asset Lifecycle Event` / WO / Calibration history | per asset 12 tháng | đa dạng để feature có tín hiệu |
| `AC Asset` mới commissioning < 30 ngày | ≥ 1 | edge INSUFFICIENT_HISTORY |
| `IMM Predictive Model` | ≥ 1 Validated + Active | UC-17-04 deploy version mới |

> Reset script đi kèm: `scripts/uat/uat_imm17.py` *(sẽ tạo Wave 3)*.

## V.4. UAT Scenarios — Suy ra từ FR + Activity

Mỗi scenario theo template §Phụ lục A. ID `UAT-IMM-17-NN`. (Suy từ 02 §III Use Cases + §I.7 FR; chi tiết step điền khi BE scaffold.)

| ID | Actor | Pre-condition | FR/BR cover | Kỹ thuật | Kết quả mong đợi |
|---|---|---|---|---|---|
| UAT-IMM-17-01 | System scheduler | ≥1 asset active có đủ history | FR-17-01/02, BR-17-08 | Use Case happy | Cron weekly run thành công, sinh ≥1 insight cho asset critical + audit record |
| UAT-IMM-17-02 | IMM Operations Manager | Có insight trong 7 ngày | FR-17-04 | Use Case happy | Cockpit top-N hiển thị → drill-down → thấy contributing factors |
| UAT-IMM-17-03 | IMM Operations Manager | Có signal chưa xử lý | FR-17-03/05, BR-17-04/08 | Use Case alt | Ack decision=open_replacement → IMM-13 record tạo (link đúng asset), audit ghi actor |
| UAT-IMM-17-04 | IMM HTM Engineer | Model ổn định | FR-17-07, BR-17-05 | Use Case alt | What-if PM cycle → biểu đồ render, KHÔNG tạo record |
| UAT-IMM-17-05 | IMM System Admin + Data Scientist | Model pass validation offline | FR-17-08, BR-17-06 | State Transition | Register + activate model mới → run kế tiếp dùng version mới, chỉ 1 Active |
| UAT-IMM-17-06 | IMM Auditor | Có ≥5 inference + 3 ack | FR-17-09, BR-17-08 | Use Case | Thấy run logs + `verify_audit_chain` pass |
| UAT-IMM-17-07 | Vendor Engineer | Login vendor | RBAC (02 §VI, 04 §6) | EP permission | KHÔNG thấy menu IMM-17; gọi `list_insights` → FORBIDDEN/empty |

## V.5. Tổng hợp kết quả & Bug found

- Bảng kết quả: `Scenario · Status (Pass/Fail/Block) · Tester · Ngày · Ghi chú` — điền khi chạy UAT Wave 3.
- Bug list: `Issue ID · Severity (Blocker/Major/Minor/Trivial) · Mô tả · Fix status`.
- Acceptance: ≥ 95% PASS, Blocker = 0, Major ≤ 2 (có workaround).
- Sign-off: BA Lead + QA Lead + Module Owner (PTP Khối 2) + (tùy) End-user (Trưởng VTTBYT).

---

# Phần VI — Security Review (gate)

## VI.1. RBAC

- **Role definitions**: `fixtures/role.json` + `role_profile.json` — IMM System Admin, IMM Operations Manager, IMM HTM Engineer, IMM QA Officer, IMM Auditor, Data Scientist (custom — Wave 3), Vendor Engineer.
- **DocPerm matrix** (từ 04 §6):

| Role | `AC Predictive Insight` | `IMM Predictive Model` | Expected |
|---|---|---|---|
| IMM System Admin | Read/Write/Delete | Full | Allow |
| IMM Operations Manager | Read + Acknowledge | Read | Allow đọc + ack; Deny write model |
| IMM HTM Engineer | Read + Acknowledge + WhatIf | Read | Allow ack/whatif; Deny write model |
| IMM QA Officer | Read | Read | Read-only |
| IMM Auditor | Read | Read | Read-only |
| Data Scientist (Wave 3) | Read all | Full (train/deploy) | Allow register/activate |
| Vendor Engineer | Không có quyền | Không có quyền | **Deny toàn bộ** |

- **Field-level permission**: field nhạy cảm (vd `model_artifact_ref`, internal cost trong contributing factors nếu có) đặt `permlevel ≠ 0` *(field chốt khi scaffold BE)*.
- **User Permission**: nếu cần scope theo khoa, bổ sung handler `assetcore.permissions.predictive_insight_query` (04 §6, R-08) *(Quyết định khi BE scaffold)*.

> Kỹ thuật: Decision Table — mỗi (role × action × state) là 1 row, expected Allow/Deny như bảng trên.

## VI.2. API security

- **Whitelist hygiene**: mọi `@frappe.whitelist` trong `api/imm17.py` phải có docstring + `rbac.require()` + validate input (05 §6).
- **CSRF**: Frappe default `X-Frappe-CSRF-Token` cho mọi POST (run_for_asset, acknowledge, register/activate_model).
- **Input validation**: Link field (asset, model_version) validate qua `frappe.get_value` trước khi dùng; `acknowledge.decision` chỉ nhận tập {open_replacement, open_pm, dismiss} (IMM17_INVALID_ACK_DECISION).
- **SQL injection**: repository query parameterized only; KHÔNG f-string vào raw SQL (read-only repo 04 §4).
- **Rate limit**: `run_for_asset` 1 request/asset/phút (05 §5); endpoint mutating (acknowledge, register/activate_model) áp rate-limit.

## VI.3. Audit trail integrity

Mọi inference / ack / model activate-retire / threshold change sinh `IMM Audit Trail` (04 §7, R-04). Hash SHA-256 chain; verify qua `verify_audit_chain(asset)`. Test tamper ở III.5(b). User KHÔNG có quyền edit/delete `IMM Audit Trail` (DocPerm + `on_trash` guard, ISO 13485:7.5.9).

→ Nguồn: III.5 test cases · 04 §7.

## VI.4. Authentication & session

Login Frappe default (require login mọi endpoint, không anonymous — 05 §6). Session timeout + lockout + password policy theo cấu hình site. Vendor ML service (Wave 3 cuối) dùng API key dedicated trong `frappe.conf`, rotation định kỳ. 2FA: roadmap.

## VI.5. Data sensitivity

| Loại | Trường | Sensitivity | Bảo vệ |
|---|---|---|---|
| Failure/replacement score | `failure_score`, `replacement_score` | Internal | RBAC; không export cho Vendor |
| Contributing factors | `contributing_factors` | Internal | RBAC |
| Model artifact ref | `model_artifact_ref` | Confidential | permlevel ≠ 0 *(chốt khi scaffold)* |
| Dataset snapshot | feature snapshot | Internal/Confidential | RBAC + anonymise trước khi gửi vendor (NFR-17-05) |

> Khẳng định: IMM-17 KHÔNG lưu patient data. Dataset gửi vendor ML đã anonymise (không serial/PHI/PII — NFR-17-05, 02 §I.6).

## VI.6. Vendor isolation

Vendor Engineer KHÔNG có quyền trên `AC Predictive Insight` và `IMM Predictive Model` (04 §6). KHÔNG thấy: score, contributing factors, audit trail, cockpit; KHÔNG export. Vendor ML service (nếu dùng) chỉ nhận dataset đã anonymise qua INT-13.

→ Nguồn: III.6 test `test_vendor_isolation` (low-role API call).

## VI.7. Secrets management

Cấm commit `.env` / credential. `site_config.json` không lên git. Vendor ML API key lưu `frappe.conf` (R-09, 05 §6), KHÔNG hardcode, KHÔNG ghi log. Backup encrypt at-rest off-site.

## VI.8. Logging & monitoring

| Sự kiện | Log level | Where | Alert? |
|---|---|---|---|
| Pipeline run start/end + asset_count | INFO | `IMM Predictive Run Log` + bench log | — |
| Pipeline fail (sau 3 retry) | ERROR | bench log + scheduler | Có (NFR-17-02) |
| Model drift vượt KRI-17-01 | WARNING | bench log | Có |
| Replacement signal emitted | INFO | `IMM Audit Trail` + notify | notify Trưởng VTTBYT |

> PII / API token KHÔNG vào log (NFR-17-05).

## VI.9. Threat model (STRIDE-lite)

| Threat (STRIDE) | Vector | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| **S**poofing | Giả mạo identity gọi `acknowledge_insight` | Thấp | Cao | Frappe session auth + role match (05 §6) |
| **T**ampering | Sửa `AC Predictive Insight` / audit entry | Trung bình | Cao | Audit hash chain + `on_trash` guard + DocPerm deny edit audit (VI.3) |
| **R**epudiation | Phủ nhận đã ack signal | Trung bình | Trung bình | Audit ghi actor + reason + timestamp mọi ack (BR-17-08) |
| **I**nfo disclosure | Vendor/role thấp đọc score/factors cross-tenant | Trung bình | Cao | RBAC + vendor isolation + permission query (VI.1/VI.6) |
| **D**enial of service | Spam `run_for_asset` / cron lock DB | Thấp | Trung bình | Rate-limit 1/asset/phút + scheduler retry guard (05 §5, NFR-17-02) |
| **E**levation of privilege | Low-role gọi `register_model`/`activate_model` | Trung bình | Cao | `rbac.require()` Data Scientist/System Admin (VI.1, test III.6 `*_lowrole`) |

## VI.10. Penetration test

Trước release đầu tiên Wave 3: Burp/ZAP scan, sqlmap (an toàn) trên endpoint nhận input, CSRF test POST endpoint, role escalation (low-role gọi register/activate). Report lưu `docs/security/`. ⬜ Planned (chạy khi BE scaffold).

## VI.11. Sign-off

| Role | Người | Ngày | Chữ ký |
|---|---|---|---|
| Security Officer | *(điền khi review)* | | |
| QA Lead | *(điền khi review)* | | |
| Module Owner (PTP Khối 2) | *(điền khi review)* | | |

> Decision: Pass / Pass with conditions / Fail (block). ⬜ Chờ BE scaffold + review thực tế.

---

# Phần VII — Code Quality

## VII.1. Tool matrix

| Tool | Mục tiêu | Target | Cadence |
|---|---|---|---|
| **SonarQube** (BE Python) | Chất lượng `services/imm17.py`, `api/imm17.py`, repo | Bug 0 critical, code smell ≤ ngưỡng dự án, duplication ≤ 3%, coverage ≥ 70%, security hotspot review 100% | Mỗi PR (CI gate) |
| **Lighthouse** (FE cockpit) | Hiệu năng + accessibility cockpit | Performance ≥ 90, Accessibility ≥ 95, Best Practices ≥ 90, SEO ≥ 80 | Mỗi release lớn + monthly |
| **ESLint + vue-tsc** (FE) | Lint + type | 0 error, 0 warning trên prod build | Mỗi PR (CI gate) |
| **ruff / black** (BE) | Lint + format | 0 error, format consistent | Mỗi PR (CI gate) |
| **Bundle size** (FE chunk imm17) | Budget bundle | main ≤ 250KB gzip, async ≤ 80KB gzip | Mỗi PR FE (CI report) |

## VII.2. Cadence

- SonarQube: mỗi PR (CI gate, fail nếu Quality Gate fail).
- Lighthouse: mỗi release lớn + monthly audit.
- ESLint / ruff: mỗi PR (CI gate).
- Bundle size: mỗi PR FE (CI report, fail nếu vượt budget).

> Gắn screenshot SonarQube + Lighthouse vào file 09 §Release Notes khi báo cáo final Wave 3.

---

# Phụ lục A — Template per UAT scenario

```markdown
### UAT-IMM-17-<NN> — <Tên>

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
### TC-IMM-17-<LAYER>-<NN> — <Tên>

**Component (I.1)**: <…>
**Liên kết**: US-<NN> | BR-<NN> | ACT-<NN>
**Kỹ thuật (II.1/II.2)**: BVA boundary `replacement_score = threshold`
**Priority (I.3)**: Critical / High / Medium / Low
**Test type**: Unit / Integration / API / E2E
**Pre-condition**: <fixture / state setup>

**Input**:
- <field>: <value>

**Steps**:
1. <…>
2. <…>

**Expected**:
- ServiceError(code=IMM17_INSUFFICIENT_HISTORY, message contains "...")
- insight không được tạo

**Post-condition**: <DB rollback / fixture cleanup>
```

# Phụ lục C — Workflow State Transition Test template

```markdown
### TC-IMM-17-WF-<NN> — <action>: <from> → <to>

**Workflow JSON**: `<path>.json`
**Role required**: <…>
**Pre-condition**: doc.workflow_state = <from>, gate <Gx> đã pass
**Action**: apply_workflow(doc, "<action>")
**Expected (happy)**: doc.workflow_state = <to>, docstatus = <…>, audit entry created
**Expected (negative role)**: PermissionError / FORBIDDEN
**Expected (gate fail)**: ServiceError(code=BUSINESS_RULE, message contains "<Gx>")
```

> Lưu ý: `AC Predictive Insight` KHÔNG dùng Frappe Workflow (04 §2). Template này chỉ áp dụng nếu `IMM Predictive Model` chốt dùng workflow Draft→Validated→Active→Retired.

---

# DoD — File 07 hoàn chỉnh

## I. Test Analysis
- [x] I.1 Component Inventory liệt kê đủ artefact (so với 04/05/06; field/signature chi tiết defer Wave 3)
- [x] I.2 mỗi FR / BR-dự-kiến / Activity có ≥ 1 dòng map
- [x] I.3 Risk priority gán cho mọi component (không trống)
- [x] I.4 Scope ghi rõ out-of-scope kèm lý do

## II. Test Design Techniques
- [x] II.1 chọn ≥ 4 black-box techniques (EP + BVA + Decision Table + State Transition đủ)
- [x] II.2 white-box criteria xác định (statement + branch bắt buộc)
- [x] II.3 mapping component → kỹ thuật điền đầy đủ

## III. Test Plan
- [ ] Test class structure cho mọi service public function — *cấu trúc đã liệt kê (III.2) nhưng test chưa viết (BE chưa scaffold)*
- [ ] ≥ 1 happy + 1 negative test mỗi function — *⬜ Planned Wave 3*
- [ ] Workflow transitions cover 100% — *insight không có workflow (0 transition); model workflow chưa quyết định (III.4)*
- [ ] Audit chain test (intact + tampered) — *thiết kế ở III.5, chưa viết*
- [ ] API test ≥ 60% coverage + permission matrix — *bảng case III.6 sẵn, code chưa có*
- [x] Performance target xác định (III.8)
- [ ] CI command chạy clean — *không chạy được vì module chưa scaffold*
- [ ] SonarQube Quality Gate pass + Lighthouse score ≥ target — *chưa có code/FE*

## IV. Traceability
- [x] IV.1 US/FR → Test: mọi FR có ≥ 1 Test ID (Planned)
- [x] IV.2 BR → Test: mọi BR-dự-kiến có mapping
- [ ] IV.3 Component → Test: Critical/High đạt coverage target — *coverage chưa đo (BE chưa scaffold)*

## V. UAT
- [x] Mỗi FR/UC có ≥ 1 UAT scenario (V.4)
- [x] ≥ 1 negative + permission + audit verify scenario (UAT-17-03/06/07)
- [ ] Test data seed script chạy được — *`uat_imm17.py` sẽ tạo Wave 3*
- [ ] Tester accounts đã tạo ở UAT site — *tạo khi setup UAT site Wave 3*
- [x] Sign-off section sẵn sàng (V.5)

## VI. Security
- [x] DocPerm matrix đầy đủ (Decision Table, VI.1 — từ 04 §6)
- [ ] Mọi field nhạy cảm có permlevel ≠ 0 — *field chốt khi scaffold BE (VI.1/VI.5)*
- [ ] SQL injection + CSRF test pass — *kế hoạch VI.2/VI.10, chưa chạy*
- [ ] Audit chain test pass (intact + tampered) — *thiết kế III.5, chưa chạy*
- [ ] Vendor isolation test pass — *case III.6 sẵn, chưa chạy*
- [x] Threat model đủ 6 STRIDE với mitigation (VI.9)
- [ ] Sign-off đầy đủ trước go-live — *chờ review Wave 3 (VI.11)*

## VII. Code Quality
- [ ] SonarQube Quality Gate pass — *chưa có code*
- [ ] Lighthouse ≥ target — *chưa có FE*
- [ ] Bundle size ≤ budget — *chưa có FE chunk*
- [ ] Screenshot báo cáo gắn vào file 09 — *khi release Wave 3*
