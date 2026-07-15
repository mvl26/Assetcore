# 07 — Kiểm thử & An ninh (Testing & QA & Security)

| Mục | Giá trị |
|---|---|
| Module | IMM-12 — Sự cố (Incident / RCA / CAPA) |
| Phạm vi | Per-module |
| Owner | QA Lead + Security Officer |
| Liên kết | 02 Analysis (US, BR, Activity, BPMN) · 03 Diagrams · 04 Backend · 05 API · 06 Frontend |

> **Mục đích**: Suy ra test case **có hệ thống** từ phân tích (file 02) bằng kỹ thuật black-box + white-box, không liệt kê tự phát. Bao gồm: phân tích đối tượng test → chọn kỹ thuật → viết test → traceability → UAT → security → code quality. Phần này là gate go-live.

> **Trạng thái module**: BE/FE LIVE. `services/imm12.py` (12 public functions), `api/imm12.py` (14 endpoint), DocType `Incident Report` + `IMM RCA Record` + `IMM CAPA Record` + child `IMM RCA Five Why Step` / `IMM RCA Related Incident` / `IMM CAPA Action Step` đã có. Test cốt lõi tại `assetcore/tests/test_imm12.py` (4 test class ✅ Live). UAT/E2E/Pentest còn pending.

---

# Phần I — Test Analysis (Phân tích đối tượng test)

> Mục tiêu Phần I: trả lời 4 câu hỏi trước khi viết test case: **(1) test cái gì** (component inventory) **(2) suy ra từ đâu** (US/BR/Activity) **(3) ưu tiên cái nào** (risk) **(4) loại trừ cái nào** (out-of-scope).

## I.1. Component Inventory — Liệt kê phần mềm cần test

Toàn bộ artefact test được của IMM-12. Mỗi dòng → ≥ 1 test class ở Phần III.

| # | Component | Loại | File / Tên | Test layer áp dụng |
|---|---|---|---|---|
| 1 | `Incident Report` | DocType (submittable) | `incident_report/incident_report.json` | Integration (lifecycle) |
| 2 | `IMM RCA Record` | DocType (submittable) | `imm_rca_record/imm_rca_record.json` | Integration (lifecycle) |
| 3 | `IMM CAPA Record` | DocType (submittable, IMM-00) | `imm_capa_record/imm_capa_record.json` | Integration (lifecycle) |
| 4 | Incident workflow | Workflow | `workflow/imm_12_incident_workflow.json` (10 transition) | Integration (state transition) |
| 5 | RCA workflow | Workflow | `workflow/imm_12_rca_workflow.json` (4 transition) | Integration (state transition) |
| 6 | `report_incident()` | Service function | `services/imm12.py::report_incident` | Unit + API |
| 7 | `acknowledge_incident()` | Service function | `services/imm12.py::acknowledge_incident` | Unit + API |
| 8 | `resolve_incident()` | Service function | `services/imm12.py::resolve_incident` | Unit + API |
| 9 | `close_incident()` | Service function | `services/imm12.py::close_incident` | Unit + API |
| 10 | `cancel_incident()` | Service function | `services/imm12.py::cancel_incident` | Unit + API |
| 11 | `create_rca()` | Service function | `services/imm12.py::create_rca` | Unit + API |
| 12 | `submit_rca()` | Service function | `services/imm12.py::submit_rca` | Unit + API |
| 13 | `on_rca_completed()` / `_advance_incident_after_rca()` | Service (RCA→CAPA chain) | `services/imm12.py::on_rca_completed` | Integration (audit chain) |
| 14 | `detect_chronic_failures()` / `_process_chronic_group()` | Scheduler job | `services/imm12.py::detect_chronic_failures` | Unit + Cron simulation |
| 15 | `validate_incident_close_gate()` | Validator (hook `validate`) | `services/imm12.py::validate_incident_close_gate` | Unit (Decision Table) |
| 16 | `_map_severity()` / `_needs_rca()` | Pure helper | `services/imm12.py` | Unit (EP) |
| 17 | `list_incidents` / `get_incident` / `get_incident_stats` / `get_dashboard` | Read service | `services/imm12.py` | API integration |
| 18 | Lifecycle event qua `_log()` → `log_audit_event()` | Lifecycle event | `services/imm12.py::_log` | Integration (audit chain) |
| 19 | Incident FE views | FE view | `frontend/src/views/incident/IncidentList/Create/Detail/RCADetail/CAPAList/CAPADetail/IMM12Dashboard.vue` | E2E (Playwright) |
| 20 | Pinia store IMM-12 | Pinia store | `frontend/src/stores/imm12.ts` | Unit (vitest) |
| 21 | API client | FE API | `frontend/src/api/imm12.ts` | E2E |

> Severity canonical (DocType `Incident Report.severity`) = **Low / Medium / High / Critical**. Khi docs gọi "Major" hãy hiểu là "High" theo schema thực — service map qua `_map_severity()`.

## I.2. Trace nguồn test — User Stories, Activity Flows, Business Rules

Dẫn từ artefact phân tích (file 02) sang test layer. Mọi US/BR/Activity phải có ≥ 1 test ở Phần III và xuất hiện trong matrix Phần IV.

### I.2.a. Từ User Story (→ 02 §IV.1)
| US ID | Tiêu đề ngắn | Acceptance Criteria # | Test layer dự kiến |
|---|---|---|---|
| US-12-01 | Reporting User báo cáo sự cố Critical | AC-01 (Critical→OOS), AC-02 (thiếu clinical_impact→block) | Unit + API + UAT |
| US-12-02 | Phát hiện sự cố mãn tính (chronic) | AC-01 (≥3/90d→auto RCA), AC-02 (idempotent) | Unit + Cron + UAT |

### I.2.b. Từ Business Rule (→ 02 §IV.2)
| BR ID | Phát biểu | Component liên quan (I.1) | Kỹ thuật test phù hợp |
|---|---|---|---|
| BR-12-01 | Critical → bắt buộc `clinical_impact` | `report_incident()` | EP + Error guessing |
| BR-12-02 | High/Critical → RCA `Completed` trước Close | `close_incident()` / `validate_incident_close_gate()` | Decision Table |
| BR-12-03 | ≥3 incident cùng `fault_code`/asset/90d → auto RCA + flag | `detect_chronic_failures()` | BVA (ngưỡng 3) + Use Case |
| BR-12-04 | Critical → auto OOS (report); High → auto OOS (acknowledge) | `report_incident()` / `acknowledge_incident()` | Decision Table |
| BR-12-05 | Mọi transition → `log_audit_event()` (SHA-256 chain) | `_log()` | Use Case (audit chain) |
| BR-12-06 | Submit RCA → auto `create_capa()` + ghi `linked_capa` | `submit_rca()` | Use Case |
| BR-12-07 | RCA `root_cause` + `rca_method` ∈ {5-Why, Fishbone, Both} bắt buộc | `submit_rca()` | EP + Error guessing |
| BR-00-08 | CAPA root_cause + corrective + preventive bắt buộc trước Submit | `IMM CAPA Record.before_submit()` (IMM-00) | Decision Table |
| BR-00-09 | CAPA quá `due_date` → auto Overdue | `check_capa_overdue()` (IMM-00) | Use Case (cron) |

### I.2.c. Từ Activity Flow / Exception (→ 02 §II.8, §IV.5)
| Exception/Edge ID | Use Case | Branch chính | Branch ngoại lệ |
|---|---|---|---|
| EX-12-01 | UC-01 Submit Critical | Submit có clinical_impact | Thiếu clinical_impact → VALIDATION |
| EX-12-03 | UC-04/05 RCA | High/Critical close sau RCA Completed | Close trực tiếp không RCA → BUSINESS_RULE |
| EX-12-04 | UC-08 Scheduler | Tạo RCA chronic mới | Đã có RCA mở → skip (idempotent) |
| EX-12-05 | UC-09 Auto OOS | Asset Active → OOS | Asset đã OOS/Decommissioned → skip, vẫn audit |
| EX-12-06 | UC-06 Close CAPA | Đủ 3 field → close | Thiếu field → VALIDATION (BR-00-08) |

## I.3. Risk-based Priority

| Component (I.1) | Likelihood (1-5) | Impact (1-5) | Risk = L×I | Priority |
|---|---|---|---|---|
| `validate_incident_close_gate()` (BR-12-02 RCA gate) | 3 | 5 | 15 | **Critical** |
| `report_incident()` Critical → OOS (BR-12-04) | 3 | 5 | 15 | **Critical** |
| `_log()` audit chain integrity (BR-12-05) | 2 | 5 | 10 | **High** |
| `submit_rca()` → CAPA chain (BR-12-06) | 3 | 4 | 12 | **High** |
| `detect_chronic_failures()` idempotency (BR-12-03) | 3 | 4 | 12 | **High** |
| Incident workflow transitions (10) | 3 | 4 | 12 | **High** |
| `report_incident()` clinical_impact (BR-12-01) | 4 | 3 | 12 | **High** |
| DocPerm matrix Incident/RCA/CAPA | 2 | 5 | 10 | **High** |
| `_map_severity()` / `_needs_rca()` | 2 | 3 | 6 | Medium |
| Read endpoints (`list_incidents`, `get_dashboard`) | 3 | 2 | 6 | Medium |
| FE dashboard render | 2 | 2 | 4 | Low |

**Quy ước priority**: Critical (R ≥ 15) test trước, fail = block release · High (10 ≤ R < 15) bắt buộc trước go-live · Medium (5 ≤ R < 10) trong sprint · Low (R < 5) chỉ khi báo bug.

## I.4. Scope

**In-scope:**
- Service layer (`services/imm12.py`): report/acknowledge/resolve/close/cancel + create/submit RCA + detect chronic + close gate.
- Workflow state machine (14 transition: 10 Incident + 4 RCA).
- Audit chain integrity (BR-12-05) + RCA→CAPA chain (BR-12-06).
- API envelope + permission (14 endpoint).
- DocPerm matrix + vendor/role isolation (Phần VI).

**Out-of-scope:**
- Performance/load test → giao Phần III.8 (target xác định, chưa chạy thực).
- E2E browser → Phần III.7, chạy sau khi FE views ổn định trên staging.
- Cross-module IMM-15 (Vigilance reporting BYT) → chỉ smoke; thuộc module khác.
- SMS/email notification delivery → integration test riêng.

**Assumptions:** Master data (`AC Asset`, fault code) đã seed; tester accounts đã tạo trên UAT site; IMM-00 (`log_audit_event`, `create_capa`, CAPA gate) đã LIVE; browser Chrome/Edge ≥ 120.

---

# Phần II — Test Design Techniques (Kỹ thuật thiết kế test case)

> Mỗi test phải truy được về 1 kỹ thuật ở dưới.

## II.1. Black-box techniques

| Kỹ thuật | Khi nào dùng | Áp dụng vào IMM-12 | Số test sinh ra |
|---|---|---|---|
| **Equivalence Partitioning (EP)** | Input có miền chia nhóm tương đương | `severity` (Low/Medium/High/Critical), `incident_type`, `rca_method`, `status` enum | 1 test/partition |
| **Boundary Value Analysis (BVA)** | Numeric / date / length có biên | Ngưỡng chronic = 3 incident / 90 ngày (2 vs 3 vs 4); `clinical_impact` length | 2-3 test/biên |
| **Decision Table** | Multi-condition gate | `validate_incident_close_gate()` (severity × RCA status × CAPA status); BR-12-04 (severity × asset status) | 2^N rút gọn |
| **State Transition Testing** | Workflow finite state machine | `imm_12_incident_workflow.json` + `imm_12_rca_workflow.json` | Mỗi transition + invalid |
| **Use Case Testing** | End-to-end actor flow | UAT scenarios, RCA→CAPA chain, chronic detection | 1/main + 1/alt + 1/exception |
| **Error Guessing** | Lỗi kinh nghiệm: null, asset Decommissioned, double-acknowledge | `report_incident`, `acknowledge_incident` idempotency (EC-12-03) | Bổ sung |

## II.2. White-box techniques

| Kỹ thuật | Áp dụng vào | Tiêu chí đạt | Công cụ |
|---|---|---|---|
| **Statement coverage** | Service functions I.1 (#6-16) | ≥ 85% line | `coverage report` |
| **Branch / Decision coverage** | `resolve_incident` (Minor vs High/Critical branch), `_needs_rca`, `_process_chronic_group` | ≥ 80% branch | `coverage --branch` |
| **Condition / MC/DC** | `validate_incident_close_gate()` (RCA gate multi-AND) | Mỗi sub-condition kiểm soát outcome độc lập | Manual + coverage |
| **Path coverage** | `_advance_incident_after_rca()` (guard chuỗi RCA→CAPA→advance) | Toàn bộ path (RCA chưa Completed / đã Completed / CAPA tồn tại) | Manual |

## II.3. Mapping Component → Kỹ thuật

| Loại component | Kỹ thuật chính | Kỹ thuật phụ |
|---|---|---|
| `validate_incident_close_gate()` (gate) | Decision Table | MC/DC |
| `_map_severity()` / `_needs_rca()` | EP | BVA |
| Workflow transition (Incident + RCA) | State Transition | Use Case |
| `report_incident` / `resolve_incident` / `submit_rca` | EP + Branch coverage | BVA, Error guessing |
| `detect_chronic_failures()` (scheduler) | Use Case (setup → run → assert) | BVA (ngưỡng 3), Error guessing (idempotent) |
| API endpoint (14) | Use Case + EP | Pairwise (form input) |
| FE view (Playwright) | Use Case end-to-end | Error guessing (network 4xx/5xx, role gate) |

---

# Phần III — Test Plan (Kế hoạch thực thi)

## III.1. Test Pyramid

```
                  ┌────────────┐
                  │  E2E / UAT │   ~5%  (Playwright; 2 Golden Scenarios)
                 ─┴────────────┴─
              ┌──────────────────────┐
              │   API Integration    │   ~15% (14 endpoint)
             ─┴──────────────────────┴─
          ┌────────────────────────────────┐
          │  Workflow + DocType lifecycle  │   ~25% (14 transition)
         ─┴────────────────────────────────┴─
      ┌────────────────────────────────────────────┐
      │         Unit — Service Layer               │   ~55%
     ─┴────────────────────────────────────────────┴─
```

CLAUDE.md §17 (TDD mandatory).

## III.2. Unit test — Service Layer

**File:** `assetcore/tests/test_imm12.py`. Test class đã tồn tại được đánh dấu ✅ Live; coverage mở rộng = ⬜ Planned.

| Test class | Function cover | Kỹ thuật | Cases (happy/negative) | Trạng thái |
|---|---|---|---|---|
| `TestIncidentCreation` | `report_incident()` | EP + Error guessing | 4 (test_create_medium_severity_incident, test_create_critical_with_clinical_impact_succeeds / test_nonexistent_asset_raises_error, test_critical_without_clinical_impact_raises_error) | ✅ Live |
| `TestIncidentWorkflow` | report→acknowledge→resolve→close (`test_full_workflow_open_to_closed`) | State Transition | 1 happy end-to-end | ✅ Live |
| `TestIncidentCancellation` | `cancel_incident()` (`test_cancel_from_open`) | State Transition | 1 happy | ✅ Live |
| `TestRCAToCAPAAndIncidentChain` | `on_rca_completed()` / `_advance_incident_after_rca()` / `submit_rca()` | Use Case + Path coverage | 5 (test_rca_completed_creates_capa_and_advances_incident, test_capa_chain_idempotent_when_capa_exists / test_rca_no_incident_link_skips_silently, test_rca_invalid_incident_skips_silently, test_advance_skipped_when_not_in_rca_required) | ✅ Live |
| `TestRcaAllowedTransitions` (Round 9) | `_RCA_VALID_TRANSITIONS` / `get_rca()` BR-12-19 | SoT-divergence guard | map ↔ `fixtures/workflow.json` "IMM-12 RCA Workflow" edge-by-edge; codomain ⊆ enum `status`; `get_rca` payload có `allowed_transitions`==`_RCA_VALID_TRANSITIONS[status]` + `can_manage_rca` int(0/1) | ⬜ Planned (test TRƯỚC, đỏ→xanh) |
| `TestRcaStateMachine` (Round 9) | `start_rca()`/`submit_rca()`/`cancel_rca()` BR-12-20/21/22 | State Transition + Error guessing | start: `RCA Required→In Progress` OK / status≠Required→`IMM12_RCA_START_INVALID_STATE`(409); **submit từ `RCA Required`→`IMM12_RCA_SUBMIT_INVALID_STATE`(chặn nhảy-cóc)**, từ `In Progress`→Completed+CAPA OK; cancel: active→Cancelled OK / Completed\|Cancelled→`IMM12_RCA_CANCEL_INVALID_STATE`, thiếu reason→422; mỗi transition sinh audit token `rca_started`/`rca_completed`/`rca_cancelled` | ⬜ Planned |
| `TestRcaCapGate` (Round 9, AC5 axis-A) | cap `corrective.write` gate 3 endpoint | RBAC dead-gate prove | base `AssetCore System User`→cap-403/ServiceError trên start/submit/cancel; `AssetCore Super Admin`→**TẤT CẢ** transition OK (không dead-gate); khớp allowed roles `fixtures/workflow.json` | ⬜ Planned |
| `TestRcaWorkflowParity` (Round 30, CR-WF-12-RCA) | desk↔endpoint role parity `imm_12_rca_workflow.json` ⇄ `_RCA_VALID_TRANSITIONS` ⇄ `corrective.write` | INVARIANT / SoT-divergence guard | **INV-RCA-PARITY-A**: parse workflow-JSON codomain(state→{next_state}) == `_RCA_VALID_TRANSITIONS` codomain EXACT set (`RCA Required→{RCA In Progress,Cancelled}`; `RCA In Progress→{Completed,Cancelled}`; `Completed→∅`; `Cancelled→∅`) — mirror `TestIncidentAllowedTransitions`. **INV-RCA-PARITY-B**: ∀ action∈{Bắt đầu phân tích RCA, Hoàn thành RCA, Hủy RCA} → `workflow.allowed_role_set(action) ⊇ roles(corrective.write) ∪ {AssetCore Super Admin, System Manager}`; `roles(corrective.write)` resolve ĐỘNG qua `rbac.CAPABILITY_MAP` + DocPerm write=1 (KHÔNG hardcode role-name); dùng **⊇** không `==`. **RED trước fix** (Start/Complete thiếu Corrective Manager). **INV-RCA-PARITY-C**: `fixtures/workflow.json` "IMM-12 RCA Workflow" tuple-set (state,action,next_state,allowed) == source `imm_12_rca_workflow.json`. | ⬜ Planned (RED→GREEN) |
| `TestCloseGate` (đề xuất) | `validate_incident_close_gate()` BR-12-02 | Decision Table | High + RCA Completed→pass / High + RCA In Progress→raise | ⬜ Planned |
| `TestChronicDetect` (đề xuất) | `detect_chronic_failures()` BR-12-03 | BVA + idempotency | 3 IR/90d→RCA / 2 IR→no RCA / RCA mở sẵn→no dup | ⬜ Planned |
| `TestChronicSoT` (đề xuất) | `chronic_failure_count()` / `get_incident_stats().chronic` BR-12-12 | SoT consolidation + RED-prove | (1) `stats.chronic == len(get_chronic_failures())` (cùng SoT); (2) **RED-prove lifecycle**: 3+ IR aged-out >90d (cờ `chronic_failure_flag=1` còn) ∧ 0 nhóm live ⇒ `stats.chronic == 0` (revert SoT→`_count(chronic_failure_flag=1)` ⇒ FAIL); (3) **invariant 1 payload**: `get_dashboard()` → `stats.chronic == len(dashboard["chronic_failures"])` (data ≤5 nhóm) hoặc == `len(get_chronic_failures())` FULL (data >5); (4) no-regression: badge cờ vẫn set bởi `_process_chronic_group` khi cụm live (BR-12-03 KHÔNG đổi); (5) grep-guard: 0 inline `chronic_failure_flag` cho KPI tile trong `get_incident_stats()` | ⬜ Planned |
| `TestCriticalOOS` (đề xuất) | `report_incident()` BR-12-04 | Decision Table | Critical→asset OOS / asset đã OOS→skip+audit | ⬜ Planned |
| `TestIncidentIdempotency` (Round 32, CR-24) | `report_incident()` BR-12-25 idempotency `client_request_id` | State + Error guessing + **RED-before** | **`TC-12-IDEMP-01`** gọi 2× cùng `client_request_id` (cùng reporter) → `frappe.db.count("Incident Report", {client_request_id:crid})==1` ∧ call#2 return `name`==call#1 (KHÔNG insert #2). **`TC-12-IDEMP-02`** sau call trùng #2: `count(Asset Lifecycle Event, event_type="incident_reported", root_record=IR)==1` ∧ `count(IMM Audit Trail cho IR)==1` (0 double — NĐ98). **`TC-12-IDEMP-03`** `client_request_id` rỗng/thiếu, 2 call → **2 phiếu** riêng (backward-compat NGUYÊN VẸN). **`TC-12-IDEMP-04`** 2 `client_request_id` KHÁC nhau → 2 phiếu. **`TC-12-IDEMP-05`** field `client_request_id` persist trên phiếu (đọc lại `db.get_value`) + có DB index (`frappe.db.get_column_index`/`SHOW INDEX` chứa cột — hoặc doctype meta `search_index`). **`TC-12-IDEMP-06`** dedupe-hit return shape == create thường (3-key `{name,status,severity}`). **RED-before proof:** bỏ dedupe guard → TC-01 FAIL (count==2). | ⬜ Planned (RED→GREEN) |
| `TestMapSeverity` (đề xuất) | `_map_severity()` / `_needs_rca()` | EP | Low/Medium→no RCA, High/Critical→RCA | ⬜ Planned |

## III.3. Integration — DocType lifecycle

**File:** `assetcore/tests/test_imm12.py` (`TestIncidentCreation`, `TestIncidentWorkflow` đã cover validate/submit lifecycle). Cover hook `validate` (`validate_incident_close_gate`).

| Test | Setup | Action | Assert | Kỹ thuật | Trạng thái |
|---|---|---|---|---|---|
| `test_critical_without_clinical_impact_raises_error` | Asset Active, severity=Critical, clinical_impact rỗng | `report_incident()` | raise (VALIDATION, BR-12-01) | EP | ✅ Live |
| `test_create_critical_with_clinical_impact_succeeds` | Asset Active, Critical + clinical_impact | `report_incident()` | IR tạo OK | EP | ✅ Live |
| `test_nonexistent_asset_raises_error` | Asset không tồn tại | `report_incident()` | raise | Error guessing | ✅ Live |
| `test_critical_submit_sets_asset_oos` (đề xuất) | Asset Active, Critical | submit | `AC Asset.lifecycle_status = Out of Service` (BR-12-04) | Decision Table | ⬜ Planned |
| `test_submit_rca_needs_root_cause` (đề xuất) | RCA In Progress, root_cause rỗng | `submit_rca()` | raise (BR-12-07) | Error guessing | ⬜ Planned |

Fixture trong `setUp` phải có cleanup — xem `assetcore-test` LL-TEST-17.

## III.4. Integration — Workflow transitions

**File:** `assetcore/tests/test_imm12.py`. **Bắt buộc** cover 14 transition (10 Incident + 4 RCA). Số liệu xác minh: `python3 -c "import json;print(len(json.load(open('assetcore/assetcore/workflow/imm_12_incident_workflow.json'))['transitions']))"` → 10; RCA → 4.

### Incident workflow (`imm_12_incident_workflow.json`)
| Transition (action) | From → To | Role required | Test pass | Test fail | Trạng thái |
|---|---|---|---|---|---|
| Tiếp nhận sự cố | Open → Acknowledged | Corrective Manager | ☑ | wrong role | ✅ (`test_full_workflow_open_to_closed`) |
| Hủy sự cố | Open → Cancelled | System Manager | ☑ | — | ✅ (`test_cancel_from_open`) |
| Bắt đầu xử lý | Acknowledged → In Progress | Corrective User | ☑ | — | ✅ |
| Hủy sự cố | Acknowledged → Cancelled | System Manager | ☐ | — | ⬜ Planned |
| Đánh dấu đã giải quyết | In Progress → Resolved | Corrective User | ☑ | — | ✅ |
| Hủy sự cố | In Progress → Cancelled | System Manager | ☐ | — | ⬜ Planned |
| Yêu cầu RCA | Resolved → RCA Required | Compliance Manager, AssetCore Super Admin (endpoint `request_rca`, cap `compliance.submit`) | ☐ (`TC-12-REQRCA-01`) | reason rỗng→`IMM12_RCA_REASON_REQUIRED`; status≠Resolved→`IMM12_REQUEST_RCA_BAD_STATE` (422); base/Corrective User/Compliance User→cap-403 | ⬜ Planned (BR-12-24, Round 38) |
| Đóng sự cố | Resolved → Closed | System Manager | ☑ | — | ✅ |
| RCA hoàn tất - đóng sự cố | RCA Required → Closed | System Manager | ☐ | RCA In Progress → gate fail | ⬜ Planned |
| Mở lại điều tra | Resolved → In Progress | System Manager, AssetCore Super Admin (endpoint `reopen_incident`, cap `incident.close`) | ☐ (`TC-12-REOPEN-01`) | reason rỗng→`IMM12_REOPEN_REASON_REQUIRED`; status≠Resolved→`IMM12_BAD_STATE`; base/Corrective User→cap-403 | ⬜ Planned (BR-12-23, Round 12) |

#### III.4.a. Guard SSoT-divergence Incident `_VALID_TRANSITIONS` ⇄ workflow JSON (CR-WF-12, Round 12) — RED→GREEN

- **File / class:** `assetcore/tests/test_imm12.py::TestIncidentAllowedTransitions` (mirror `TestRCAAllowedTransitions:2739`). Import `_VALID_TRANSITIONS` từ service; load `imm_12_incident_workflow.json`.
- **Build:** `WF = {(t["state"], t["next_state"]) for t in workflow["transitions"]}` (dedupe theo cặp, bỏ chiều role); `SVC = {(f, t) for f, tos in _VALID_TRANSITIONS.items() for t in tos}`; `EXCEPTION_EDGES = {("RCA Required", "Closed")}`.
- **`test_ssot_map_matches_spec`** — assert `_VALID_TRANSITIONS` khớp verbatim đặc tả đã fix: `Open→[Acknowledged,Cancelled]`, `Acknowledged→[In Progress,Cancelled]`, `In Progress→[Resolved,Cancelled]` (**KHÔNG có RCA Required** — drift b), `Resolved→[Closed,RCA Required,In Progress]` (**CÓ In Progress** — drift a fixed).
- **`test_inv1_service_subset_workflow`** (INV-1) — assert `SVC <= WF`. *RED trước fix: `("In Progress","RCA Required")` ∈ `SVC \ WF`.*
- **`test_inv2_workflow_subset_service_or_exception`** (INV-2) — assert `WF <= SVC | EXCEPTION_EDGES`. *RED trước fix: `("Resolved","In Progress")` ∈ `WF \ (SVC ∪ EXCEPTION)`.*
- **`test_codomain_within_canonical_states`** — mọi state trong `SVC` ⊆ 7 state chuẩn.
- **`test_get_incident_detail_emits_allowed_transitions`** — với incident ở mỗi status, `get_incident_detail(name)["allowed_transitions"] == _VALID_TRANSITIONS.get(status, [])`; đặc biệt status=`Resolved` → chứa `"In Progress"` (reopen surface).
- **Non-regression:** KHÔNG đụng workflow JSON ⇒ `TestWorkflowAdminOverride` (`test_workflow_admin_override.py`) GIỮ GREEN (Super Admin vẫn phủ mọi transition-group). `bench --site miyano run-tests --module assetcore.tests.test_imm12` + `--module assetcore.tests.test_workflows` in `Ran N OK` THẬT (đọc dòng cuối, không false-green).

**TC reopen behavior (`TestIncidentReopen`, mirror `TestRCAStartTransition`):**
- `TC-12-REOPEN-01` — Resolved → In Progress OK; return `{name, status:"In Progress"}`; audit IMM Audit Trail 1 record `from="Resolved" to="In Progress"` change_summary chứa "Mở lại điều tra".
- `TC-12-REOPEN-02` — status ≠ Resolved (vd Open/Closed) → `IMM12_BAD_STATE` (in-handler HTTP-200 Error envelope).
- `TC-12-REOPEN-03` — reason rỗng/space → `IMM12_REOPEN_REASON_REQUIRED` (422 bucket).
- `TC-12-REOPEN-04` — base `AssetCore System User` / Corrective User (chỉ `incident.acknowledge`) → cap-403; System Manager / AssetCore Super Admin → OK (AC axis-A).
- `TC-12-REOPEN-05` — reopen KHÔNG đổi asset `lifecycle_status` (Critical/OOS incident: asset vẫn `Out of Service` sau reopen).

**TC request_rca behavior (`TestIncidentRequestRca`, mirror `TestIncidentReopen` — BR-12-24, Round 38):**
- `TC-12-REQRCA-01` — Resolved → RCA Required OK; `status` field Select == `"RCA Required"` VÀ `workflow_state` == `"RCA Required"` (qua `apply_workflow`, KHÔNG chỉ 1 field); return `{name, status:"RCA Required", rca_record}`; audit IMM Audit Trail 1 record `from="Resolved" to="RCA Required"` change_summary chứa "Yêu cầu RCA". `event_type` == `"Incident"` (KHÔNG có option Select mới).
- `TC-12-REQRCA-02` — status ≠ Resolved (vd Open/In Progress/Closed) → **`IMM12_REQUEST_RCA_BAD_STATE` (422 bucket, in-handler HTTP-200 Error envelope)** — assert MÃ 422 (KHÔNG phải `IMM12_BAD_STATE` 409); status KHÔNG đổi.
- `TC-12-REQRCA-03` — rca_reason rỗng/space → `IMM12_RCA_REASON_REQUIRED` (422 bucket).
- `TC-12-REQRCA-04` — base `AssetCore System User` / Corrective User / Compliance User (chỉ `compliance.create`) → cap-403 (message == `_MSG_FORBIDDEN`, KHÔNG leak raw cap `compliance.submit`); **Compliance Manager / AssetCore Super Admin → OK** (AC axis-A). Assert cap-403 message KHÔNG chứa chuỗi "compliance.submit".
- `TC-12-REQRCA-05` — **idempotent RCA reuse:** Incident đã có `rca_record` hợp lệ (vd Critical auto-tạo ở resolve) → `request_rca` KHÔNG tạo RCA trùng (đếm `IMM RCA Record` theo `incident_report` == 1, KHÔNG 2); `rca_record` giữ nguyên; KHÔNG raise 409.
- `TC-12-REQRCA-06` — **downstream loop:** sau `request_rca` (RCA Required) → `start_rca` → `submit_rca` (RCA Completed) → `_advance_incident_after_rca` auto đẩy Incident → `Closed` (ENTRY↔EXIT khép kín).

> **Invariant / non-regression (BR-12-24):** `request_rca` **KHÔNG đổi `_VALID_TRANSITIONS` / `imm_12_incident_workflow.json`** (state edge `Resolved→RCA Required` đã reconciled Round 12) ⇒ `TestIncidentAllowedTransitions` (§III.4.a, INV-1/INV-2) GIỮ GREEN + `TestWorkflowAdminOverride` **22/22** GREEN. `test_get_incident_detail_emits_allowed_transitions` (§III.4.a) vốn đã assert `Resolved.allowed_transitions ⊇ {'RCA Required'}` — round này bổ **driver THẬT** (endpoint), KHÔNG đổi assert. **RED-before demo (bắt buộc):** TRƯỚC khi thêm `request_rca` (endpoint chưa tồn tại) → `TC-12-REQRCA-01` FAIL (`AttributeError`/404: CTA advertise `'RCA Required'` nhưng gọi `request_rca` fail) → sau khi thêm → GREEN. Cap ⊆ workflow: assert role-set `compliance.submit` (DocPerm submit `IMM CAPA Record`, resolve ĐỘNG qua `rbac.CAPABILITY_MAP`) ⊆ workflow "Yêu cầu RCA" allowed → KHÔNG false-clickable.
> **DoD:** `bench --site miyano run-tests --module assetcore.tests.test_imm12` → `Ran N OK` THẬT (đọc dòng cuối, KHÔNG false-green) · `--module assetcore.tests.test_workflows` → `Ran N OK` (admin-override 22/22) · FE `vitest` `IncidentDetailView.requestRca.test.ts` xanh (gating server-driven: cap ∧ status ∧ allowed_transitions; dead-control reason==param; required-reason disable) · live: Compliance Manager mở Incident Resolved THẤY + BẤM được "Yêu cầu phân tích RCA" → refetch stepper nhánh RCA Required + badge cập nhật. **KHÔNG git commit/push — working tree để USER duyệt.**

### RCA workflow (`imm_12_rca_workflow.json` / `fixtures/workflow.json` "IMM-12 RCA Workflow") — dual-track với endpoint (Round 9)
| Transition (action) | From → To | Endpoint | Cap gate | Allowed roles (fixture) | Trạng thái |
|---|---|---|---|---|---|
| Bắt đầu phân tích RCA | RCA Required → RCA In Progress | `start_rca` | `corrective.write` | Corrective User, **Corrective Manager\*** (Round 30 — THÊM), System Manager, AssetCore Super Admin | ⬜ Planned |
| Hoàn thành RCA | RCA In Progress → Completed | `submit_rca` | `corrective.write` | Corrective User, **Corrective Manager\*** (Round 30 — THÊM), System Manager, AssetCore Super Admin | ⬜ Planned |
| Hủy RCA | RCA Required → Cancelled | `cancel_rca` | `corrective.write` | Corrective User, Corrective Manager, System Manager, AssetCore Super Admin (đủ 4 — ADR-IMM12-RCA-CTA D2) | ⬜ Planned |
| Hủy RCA | RCA In Progress → Cancelled | `cancel_rca` | `corrective.write` | Corrective User, Corrective Manager, System Manager, AssetCore Super Admin (đủ 4) | ⬜ Planned |

> \* **CR-WF-12-RCA (Round 30):** Corrective Manager có DocPerm write trên Incident Report ⇒ `corrective.write`=True (gọi được `start_rca`/`submit_rca`) NHƯNG workflow desk "Bắt đầu/Hoàn thành" thiếu row Corrective Manager ⇒ desk chặn (asymmetry). Fix = THÊM 1 row Corrective Manager vào 2 transition đó trong **cả source `imm_12_rca_workflow.json` + `fixtures/workflow.json`** để `native-workflow-allowed == endpoint-cap-allowed` — mở rộng ADR-IMM12-RCA-CTA D2 (lần trước chỉ vá "Hủy RCA"). State Transition Testing — mỗi edge = 1 test pass (đúng cap) + 1 test fail (base user → cap-403 / sai trạng thái → 409 inline VN). Endpoint thao tác trên `status` (dual-track), KHÔNG `apply_workflow`.

#### III.4.b. Guard desk↔endpoint parity RCA workflow (CR-WF-12-RCA, Round 30) — RED→GREEN

- **File / class:** `assetcore/tests/test_imm12.py::TestRcaWorkflowParity` (mirror `TestIncidentAllowedTransitions` §III.4.a + incident guard `test_imm12.py:3095`). Import `_RCA_VALID_TRANSITIONS` + `rbac` từ service; load `imm_12_rca_workflow.json` + `fixtures/workflow.json` "IMM-12 RCA Workflow".
- **INV-RCA-PARITY-A** (`test_inv_a_ssot_matches_workflow_codomain`) — build `WF_CODOMAIN = {state: {t["next_state"] for t in tr if t["state"]==state}}` từ workflow-JSON; assert `== {k: set(v) for k,v in _RCA_VALID_TRANSITIONS.items()}` EXACT (`RCA Required→{RCA In Progress,Cancelled}`; `RCA In Progress→{Completed,Cancelled}`; `Completed→∅`; `Cancelled→∅`). *RED nếu map lệch JSON.*
- **INV-RCA-PARITY-B** (`test_inv_b_desk_role_superset_endpoint_cap`) — resolve `roles_write = frappe.get_all("DocPerm", filters={"parent": rbac.CAPABILITY_MAP["corrective.write"][0], "write": 1}, pluck="role")` (ĐỘNG, KHÔNG hardcode); `required = set(roles_write) | {"AssetCore Super Admin", "System Manager"}`; ∀ action ∈ {Bắt đầu phân tích RCA, Hoàn thành RCA, Hủy RCA}: `allowed_set = {t["allowed"] for t in tr if t["action"]==action}`; assert `required <= allowed_set`. **RED trước fix**: Start/Complete `allowed_set` thiếu `Corrective Manager` → `required - allowed_set == {"Corrective Manager"}` ≠ ∅. **GREEN sau fix.**
- **INV-RCA-PARITY-C** (`test_inv_c_fixture_equals_source`) — `src = {(t["state"],t["action"],t["next_state"],t["allowed"]) for t in source_json["transitions"]}`; `fx = {…}` từ `fixtures/workflow.json` block "IMM-12 RCA Workflow"; assert `src == fx`.
- **RED-before demo (bắt buộc trong QA):** gỡ TẠM 1 row `Corrective Manager` (vd "Bắt đầu phân tích RCA") khỏi source+fixture → chạy `bench --site miyano run-tests --module assetcore.tests.test_imm12` → **INV-RCA-PARITY-B FAIL đúng chỗ** (`{'Corrective Manager'}` uncovered cho action Start) → restore → **GREEN**.
- **Non-regression:** chỉ THÊM role vào transition-group đã có (KHÔNG xoá / KHÔNG tạo group mới) ⇒ `test_workflows` admin-override (Super Admin + System Manager, **22/22**) GIỮ GREEN. `_RCA_VALID_TRANSITIONS` (runtime) KHÔNG đổi ⇒ `TestRCAAllowedTransitions` + `rcaDetailCtaGating.test.ts` KHÔNG regress.
- **DoD:** `bench --site miyano run-tests --module assetcore.tests.test_imm12` → `Ran N OK` THẬT (đọc dòng cuối, không false-green) · `--module assetcore.tests.test_workflows` → `Ran N OK` (admin-override 22/22) · live: user role Corrective Manager mở phiếu RCA ở desk THẤY + BẤM được "Bắt đầu/Hoàn thành" (sau `backfill_workflow_admin.run` / fixture re-import — KHÔNG `bench migrate`). **KHÔNG git commit/push — working tree để USER duyệt.**

### FE gating test (Round 9, AC7)
- **File:** `frontend/src/views/incident/rcaDetailCtaGating.test.ts` (vitest). Mount `RCADetailView` với các combo `(status, allowed_transitions, can_manage_rca)`: (a) `RCA Required`+`can_manage=1` → chỉ "Bắt đầu phân tích RCA"+"Hủy RCA"; (b) `RCA In Progress` → "Hoàn thành RCA"+"Hủy RCA"; (c) `Completed`/`Cancelled` (`allowed_transitions=[]`) → KHÔNG nút action; (d) `can_manage_rca=0` → nút disabled/ẩn; (e) badge = `rcaStatusLabel(status)` VI đầy đủ, KHÔNG lộ mã thô; (f) KHÔNG còn `rca.status === 'X'` gate action. `vue-tsc` sạch.

## III.5. Integration — Audit chain integrity

2 test chính (BR-12-05):
- (a) Sau N mutation (report → acknowledge → resolve → close), chain hash SHA-256 hợp lệ end-to-end — `verify_audit_chain(asset) == True`. ⬜ Planned.
- (b) Khi 1 entry bị tamper (sửa `change_summary` / `hash_sha256` trực tiếp DB), verify endpoint trả `chain_broken=true`. ⬜ Planned.

→ 04 Backend §Audit Trail · DocType `IMM Audit Trail` (kế thừa IMM-00). Hook qua `_log()` → `imm00.log_audit_event()`; không bypass.

### III.5.a V4-GATE — Canonical lifecycle event `incident_reported` + provenance (BR-12-16 / TC-12-LIFECYCLE-PROV)

> Mục tiêu (AC2): sau `report_incident` thành công → trục lifecycle event canonical + provenance nguồn báo hỏng + hash-chain KHÔNG vỡ.

| Test | Setup | Verify | Trạng thái |
|---|---|---|---|
| `test_report_emits_incident_reported_lifecycle` | `report_incident(asset, ...)` thành công | ≥1 `Asset Lifecycle Event` `event_type='incident_reported'` cho asset (KHÔNG còn CHỈ generic audit `event_type='Incident'`) | ⬜ Planned |
| `test_provenance_qr_scan` | `report_incident(..., source="qr-scan")` | lifecycle `notes` chứa "qr-scan" + audit `change_summary` chứa "qr-scan" | ⬜ Planned |
| `test_provenance_manual_default` | `report_incident(...)` (không truyền source) | `notes`/`change_summary` chứa "manual" (default) | ⬜ Planned |
| `test_provenance_invalid_source_falls_back_manual` | `report_incident(..., source="bogus")` | coi như "manual" (KHÔNG throw) | ⬜ Planned |
| `test_audit_chain_valid_after_report` | `report_incident(...)` | `verify_audit_chain(asset)['valid'] == True` (lifecycle KHÔNG trong chain; audit-row mới hash hợp lệ) | ⬜ Planned |
| `test_lifecycle_root_link_set` | `report_incident(...)` | lifecycle event `root_doctype="Incident Report"` + `root_record=<IR>` (KHÔNG bị nuốt — pattern IMM-09) | ⬜ Planned |

### III.5.b V4-GATE — FE field-lock + source (BR-12-16 D3 / TC-12-LOCK-SRC)

**File (MỚI):** `frontend/src/views/incident/IncidentCreateView.test.ts`.

| Test | Setup | Verify | Trạng thái |
|---|---|---|---|
| `test_qr_scan_locks_asset` | mount `?asset=X&source=qr-scan` | `SmartSelect` `disabled` (user KHÔNG đổi được) + prefill `X` | ⬜ Planned |
| `test_qr_scan_payload_source` | submit với deep-link qr-scan | `reportIncident` payload chứa `source='qr-scan'` | ⬜ Planned |
| `test_manual_editable_no_regression` | mount `/incidents/new` (không query) | `SmartSelect` editable + payload `source='manual'` | ⬜ Planned |
| `test_qr_scan_without_asset_not_locked` | `?source=qr-scan` (KHÔNG asset) | `SmartSelect` KHÔNG khoá (fallback editable) | ⬜ Planned |

## III.6. API test

**File:** `assetcore/tests/test_imm12.py` (API layer — 14 endpoint LIVE). Cover: happy + envelope `success=true`, invalid params → `VALIDATION`, no permission → 403/`FORBIDDEN`, pagination, idempotent retry.

| Test | Endpoint | Verify | Kỹ thuật | Trạng thái |
|---|---|---|---|---|
| `test_list_default` | `api/imm12.list_incidents` | page=1, total ≥ 0, success=true | Use Case | ⬜ Planned |
| `test_list_filter_severity` | `list_incidents?severity=Critical` | mọi row severity==Critical | EP | ⬜ Planned |
| `test_get_existing` | `get_incident?name=IR-…` | success=true, fields + linked RCA/CAPA | Use Case | ⬜ Planned |
| `test_get_not_found` | `get_incident?name=FAKE` | success=false / NOT_FOUND | Error guessing | ⬜ Planned |
| `test_report_incident_happy` | `report_incident` (Medium) | success=true, IR name | Use Case | ⬜ Planned |
| `test_report_critical_no_clinical_impact` | `report_incident` (Critical, no impact) | VALIDATION | EP | ⬜ Planned |
| `test_report_no_permission` **(V4 BR-12-15 / TC-12-CAPGATE)** | `report_incident` — user CÓ `corrective.read` NHƯNG KHÔNG `corrective.create` | **403** + message KHÔNG chứa raw `'corrective.create'` (no-leak) | EP (permission partition) | ⬜ Planned |
| `test_report_has_create_ok` **(V4 BR-12-15)** | `report_incident` — user CÓ `corrective.create` | 200 + Incident tạo | EP | ⬜ Planned |
| `test_capgate_3tier_parity` **(V4 BR-12-15)** | route-guard `IncidentCreate` ∧ scan-action `report_failure.capability` ∧ API gate | ĐỀU == `corrective.create` (test tương đẳng 3 binding) | Equivalence | ⬜ Planned |
| `test_acknowledge_incident` | `acknowledge_incident` | status=Acknowledged, acknowledged_at set | Use Case | ⬜ Planned |
| `test_resolve_high_triggers_rca` | `resolve_incident` (High) | RCA Required + RCA created | Use Case | ⬜ Planned |
| `test_close_high_rca_incomplete` | `close_incident` (High, RCA In Progress) | BUSINESS_RULE (BR-12-02) | Decision Table | ⬜ Planned |
| `test_submit_rca` | `submit_rca` (full fields) | success=true, CAPA created | Use Case | ⬜ Planned |
| `test_get_chronic_failures` | `get_chronic_failures` | list chronic | Use Case | ⬜ Planned |
| `test_get_dashboard` | `get_dashboard` | MTTA/MTTR/open/critical fields | Use Case | ⬜ Planned |
| `test_get_incident_stats` | `get_incident_stats` | count theo status | Use Case | ⬜ Planned |

Toàn bộ 14 endpoint: `report_incident`, `cancel_incident`, `create_rca`, `get_rca`, `submit_rca`, `get_asset_incident_history`, `get_chronic_failures`, `get_dashboard`, `list_incidents`, `get_incident`, `acknowledge_incident`, `resolve_incident`, `close_incident`, `get_incident_stats`.

## III.7. E2E browser (Playwright)

Dùng cho flow UI khó cover bằng API: dropdown asset cascade, severity → hiện `clinical_impact`, workflow button visibility theo role, RCA 5-Why table.

**File (cần tạo):** `assetcore/tests/e2e/test_imm12_golden.py` — ⬜ Planned (sau khi FE views ổn định).
- **Golden 1 — Minor lifecycle:** Reporting User báo IR Medium → Corrective Manager Acknowledge → link Repair WO → Resolve → Close trực tiếp (no RCA) → verify audit + ALE.
- **Golden 2 — Critical + RCA + CAPA:** IR Critical → asset OOS auto → Acknowledge + phân công → Resolve → auto RCA → điền 5-Why → Submit RCA → CAPA auto-create → Compliance close CAPA → IR Closed.

→ `assetcore-test` skill Phần 2 (Playwright MCP recipes + R-1..R-9 data rules).

## III.8. Performance test

⬜ Planned (target xác định, chưa chạy thực). Tool **k6** / `pytest-benchmark`.

| Metric | Target | Method |
|---|---|---|
| `list_incidents` p95 (500 IR) | ≤ 800 ms | k6 ramping 20 VU |
| `report_incident` p95 | ≤ 1.5 s | k6 POST batch |
| `get_dashboard` p95 | ≤ 2 s | k6 GET |
| Scheduler `detect_chronic_failures` (10k IR) | ≤ 60 s | `time bench execute …` |
| List view FE render (100 rows) | ≤ 1 s DOMContentLoaded | Lighthouse / Playwright |

## III.9. Test data & Fixtures

| Loại | Cách seed | File |
|---|---|---|
| Master data (Asset Category, Vendor, Department) | `fixtures/*.json` (qua `bench migrate`) | `assetcore/fixtures/` |
| AC Asset test (4) | `test_records.json` / setup script | *(Cần khảo sát — seed script chưa tạo)* |
| Fault code dictionary | seed script | *(Cần khảo sát)* |
| Chronic history IR (≥3 same fault) | seed script | *(Cần khảo sát)* |
| UAT full seed | Python script | `assetcore/scripts/uat/uat_imm12.py` — ⬜ Planned |

UAT data phải thực tế (tên bệnh viện VN, mã NCC chuẩn). Backend fixture mới dùng prefix `_Test` — `assetcore-test` R-0/R-1.

## III.10. Run commands & Coverage gate

```bash
# Module test (file đã tồn tại ✅)
bench --site assetcore.local run-tests --app assetcore --module assetcore.tests.test_imm12
# Coverage
coverage run -m unittest assetcore.tests.test_imm12 && coverage report
# Full suite (CI)
bench --site assetcore.local run-tests --app assetcore --coverage
```

| Layer | Target coverage | Đo |
|---|---|---|
| Service (`services/imm12.py`) | ≥ 85% line + ≥ 80% branch | `coverage --branch` |
| DocType lifecycle (Incident + RCA) | ≥ 70% | `coverage report` |
| API (`api/imm12.py`) | ≥ 60% | `coverage report` |
| Frontend (vue-tsc) | 0 error | `npm run build` |

> Coverage % thực tế: *(Cần khảo sát — chạy `coverage report` trên test hiện hữu).*

---

# Phần IV — Traceability Matrices

> Mọi test ở Phần III phải xuất hiện ở cả 3 bảng.

## IV.1. US → Test mapping

| US ID | AC | Test ID (III.x) | Layer | Status |
|---|---|---|---|---|
| US-12-01 | AC-01 (Critical→OOS) | `TestCriticalOOS::test_critical_submit_sets_asset_oos` | Unit/Integration | ⬜ Planned |
| US-12-01 | AC-02 (thiếu clinical_impact) | `TestIncidentCreation::test_critical_without_clinical_impact_raises_error` | Unit | ✅ Live |
| US-12-02 | AC-01 (≥3/90d→RCA) | `TestChronicDetect` | Unit/Cron | ⬜ Planned |
| US-12-02 | AC-02 (idempotent) | `TestRCAToCAPAAndIncidentChain::test_capa_chain_idempotent_when_capa_exists` (idempotency pattern) + `TestChronicDetect` | Unit | ✅ Live (partial) / ⬜ Planned |

Mọi US trong 02 §IV.1 có ≥ 1 dòng. Cột Status không trống.

## IV.2. BR → Test mapping

| BR ID | Phát biểu (rút gọn) | Test ID | Kỹ thuật | Happy / Negative |
|---|---|---|---|---|
| BR-12-01 | Critical → clinical_impact bắt buộc | `test_critical_without_clinical_impact_raises_error` + `test_create_critical_with_clinical_impact_succeeds` | EP | 1 / 1 ✅ |
| BR-12-02 | High/Critical → RCA Completed trước Close | `TestCloseGate` | Decision Table | ⬜ 1 / 1 Planned |
| BR-12-03 | ≥3/90d → auto RCA + flag | `TestChronicDetect` | BVA | ⬜ 1 / 2 Planned |
| BR-12-04 | Critical→OOS report; High→OOS acknowledge | `TestCriticalOOS` | Decision Table | ⬜ 1 / 1 Planned |
| BR-12-05 | Mọi transition → audit (SHA-256) | `test_audit_chain_intact` / `test_audit_chain_breaks_on_tamper` | Use Case | ⬜ 1 / 1 Planned |
| BR-12-06 | Submit RCA → auto CAPA + linked_capa | `test_rca_completed_creates_capa_and_advances_incident` | Use Case | 1 ✅ / ⬜ negative |
| BR-12-07 | RCA root_cause + rca_method bắt buộc | `test_submit_rca_needs_root_cause` | Error guessing | ⬜ 1 / 1 Planned |
| BR-12-08 | SLA breach tracking (set cờ + due-time từ policy) | `test_sla_breach_flags_overdue_incident` | BVA | ⬜ 1 / 1 Planned |
| BR-12-09 | Breach 0→1 → bắn ĐÚNG 1 notification (in-app+email) + idempotent + audit escalated | `TC-12-SLA-ESC-01..05` (xem dưới) | State transition + EP | ⬜ Planned |
| BR-12-10 | Critical/High breach → thêm QA Officer + Ops Manager (NĐ98 gate) | `TC-12-SLA-ESC-NĐ98` | Decision Table | ⬜ Planned |
| BR-12-13 | KPI "Vi phạm SLA tiếp nhận/xử lý" = LIVE predicate `sla_breach_filter(kind)` (cờ=1 OR đang-mở∧quá-hạn); kill undercount cửa-sổ-trễ-scheduler; per-row enrich `is_*_breached` (list/dashboard **+ `get_incident_detail`**, mobile CR-21); parity 3 surface (INV-SLA-5) + terminal nhánh cờ (INV-SLA-6); idempotent; grep-guard 1 SoT; FE detail server-flag KHÔNG client-clock | `TC-12-SLA-LIVE-01..06` + `TC-12-SLA-DETAIL-01..04` (xem dưới) + FE `slaBreachLiveTile.test.ts` + `incidentDetailSlaBadge.test.ts` | BVA + State transition + EP | ⬜ Planned (DoD vòng 4 + CR-21) |
| BR-12-17 | Đính ảnh: permission (reporter/write) + validation (type/size/max-5) + File private; reject KHÔNG tạo File | `TC-12-PHOTO-01..07` (xem dưới) | EP + BVA + Decision Table | ⬜ Planned (DoD vòng này) |
| BR-12-18 | Bằng chứng NĐ98: đúng 1 lifecycle `incident_photo_attached`/success; `scene_photos` parity count==rows | `TC-12-PHOTO-EVIDENCE-01..03` (xem dưới) | State transition + EP | ⬜ Planned (DoD vòng này) |

**TC-12-PHOTO-* (BR-12-17/18) — bắt buộc cho DoD vòng này (BE `test_imm12`; ảnh giả = bytes JPG/PNG hợp lệ nhỏ + content-type):**

| Test ID | Given | When | Then |
|---|---|---|---|
| TC-12-PHOTO-01 (HAPPY reporter) | user = `reported_by` của incident đang mở; ảnh JPG hợp lệ | `attach_incident_photo(incident_name, file)` | 200 Decision-B `{success:true, data:{file_url, file_name}}`; **đúng 1** `File` `is_private=1, attached_to_doctype="Incident Report", attached_to_name=<IR>` |
| TC-12-PHOTO-02 (HAPPY write-cap) | user KHÁC reporter nhưng có `incident.write` trên phiếu; ảnh PNG | attach | 200 success; File private tạo đúng 1 |
| TC-12-PHOTO-03 (FORBIDDEN) | user KHÔNG phải reporter VÀ KHÔNG `incident.write` (vd Vendor ngoài scope — AUTH-10) | attach | `success:false, code=FORBIDDEN`, HTTP-200 body; message KHÔNG leak raw cap; **0 File tạo** |
| TC-12-PHOTO-04 (VALIDATION type) | reporter; file content-type ∉ {jpg,png} (vd application/pdf) | attach | `success:false, code=VALIDATION, fields.file="Tệp phải là ảnh JPG hoặc PNG"`; **0 File** |
| TC-12-PHOTO-05 (VALIDATION size) | reporter; ảnh size > `MAX_INCIDENT_PHOTO_BYTES` | attach | `code=VALIDATION, fields.file` chứa dung lượng cho phép; **0 File** |
| TC-12-PHOTO-06 (VALIDATION max-5) | incident đã có 5 ảnh (`len(_scene_photos)==5`); reporter | attach ảnh thứ 6 | `code=VALIDATION, fields.file="Tối đa 5 ảnh"`; **0 File** (vẫn 5) |
| TC-12-PHOTO-07 (GUEST) | `frappe.set_user("Guest")` | attach | dispatcher-403 (KHÔNG vào handler; endpoint `@whitelist` không `allow_guest`) |

**TC-12-PHOTO-EVIDENCE-* (BR-12-18):**

| Test ID | Given | When | Then |
|---|---|---|---|
| TC-12-PHOTO-EVIDENCE-01 | reporter đính 1 ảnh thành công | sau attach | **đúng 1** `Asset Lifecycle Event` `event_type='incident_photo_attached'`, `root_record=<IR>`, `actor==session.user`, `timestamp` set. **RED-prove:** bỏ emit ⇒ 0 event ⇒ FAIL |
| TC-12-PHOTO-EVIDENCE-02 (parity count==rows) | incident có k ảnh (0≤k≤5) | `get_incident_detail(name)` | `len(scene_photos)==k`, mỗi phần tử `{file_url,file_name}`; `[]` khi k=0. Số này == số dùng chặn ảnh-thứ-6 (`_scene_photos` 1 SoT) |
| TC-12-PHOTO-EVIDENCE-03 (reject no-audit) | nhánh FORBIDDEN/VALIDATION bất kỳ (TC-12-PHOTO-03..06) | sau reject | 0 `File` MỚI + 0 `Asset Lifecycle Event` `incident_photo_attached` MỚI (không ghi im lặng nửa vời) |

> **Precondition schema (deploy):** enum `incident_photo_attached` phải có trong Select `Asset Lifecycle Event.event_type` TRƯỚC khi chạy (deploy `bench reload-doctype "Asset Lifecycle Event"`) — nếu thiếu, emit throw ⇒ TC-12-PHOTO-EVIDENCE-01 fail (ValidationError select). Xem `08 §I.5`.

**TC-12-SLA-LIVE-* (BR-12-13) — bắt buộc cho DoD vòng 4 (BE `test_imm12`/`test_dashboard`):**

| Test ID | Inv | Given | When | Then |
|---|---|---|---|---|
| TC-12-SLA-LIVE-01 | INV-SLA-1 | incident OPEN, `resolution_due_at = now()−2h`, `resolution_breached=0`, scheduler CHƯA chạy | `get_incident_stats()` | `sla_resolution_breached == 1` (LIVE). **RED-prove:** revert KPI về `_count({"resolution_breached":1})` ⇒ =0 ⇒ FAIL |
| TC-12-SLA-LIVE-02 | INV-SLA-2 | incident OPEN chưa `acknowledged_at`, `response_due_at = now()−1h`, `response_breached=0`, scheduler chưa chạy | `get_incident_stats()` | `sla_response_breached == 1` |
| TC-12-SLA-LIVE-03 | INV-SLA-3 | incident `Closed`/`Resolved` với `resolution_breached=1` (lịch sử, due KHÔNG còn live-open) | `get_incident_stats()` | VẪN được đếm (nhánh cờ=1). Không regression count cũ |
| TC-12-SLA-LIVE-04 | INV-SLA-4 | sau khi `check_incident_sla_breach()` stamp cờ trên incident đã đếm vì live | gọi `get_incident_stats()` TRƯỚC + SAU scheduler | `sla_resolution_breached` BẰNG nhau (idempotent — đếm vì live = đếm vì cờ, 2 nhánh exclusive) |
| TC-12-SLA-LIVE-05 | INV-SLA-5 | incident OPEN overdue, cờ DB còn 0 | `list_incidents()` + `get_dashboard()` | mỗi row có `is_resolution_breached=1` (derive live); số row `is_*_breached=1` == tile tương ứng |
| TC-12-SLA-LIVE-06 | INV-SLA-6 | incident `Cancelled`/`Closed`/`Resolved` đóng đúng hạn, cờ=0 | `get_incident_stats()` + row enrich | KHÔNG bị tính live-overdue (`is_*_breached=0`); không phantom-count |
| TC-12-SLA-LIVE-GREP | — | grep `get_incident_stats` body | static | KHÔNG còn `_count({"response_breached":1})`/`_count({"resolution_breached":1})` đơn lẻ; CHỈ `sla_breach_count("response"/"resolution")`. RED-prove: revert ⇒ LIVE-01/02/04/05 FAIL |

**FE `slaBreachLiveTile.test.ts` (BR-12-13):** FE-01 badge bind `ir.is_response_breached`/`ir.is_resolution_breached` (KHÔNG cờ thô) — row `is_resolution_breached=1` ∧ `resolution_breached=0` ⇒ badge "Vi phạm SLA xử lý" hiện; **RED-prove** revert binding→cờ thô ⇒ badge ẩn ⇒ FAIL. FE-02 tile `sla_response_breached`/`sla_resolution_breached` == số badge live trong list (INV-SLA-5 không lệch). Nhãn KPI giữ VI 'Vi phạm SLA tiếp nhận/xử lý'; KHÔNG leak raw code/EN status. `vue-tsc` 0.

**TC-12-SLA-DETAIL-* (BR-12-13 / mobile CR-21) — parity màn Chi tiết `get_incident_detail`, bắt buộc DoD round 4 (BE `test_imm12::TestIncidentDetailSlaLive`, `test_imm12.py:884`):**

| Test ID (AC-S6) | Inv | Given | When | Then |
|---|---|---|---|---|
| TC-12-SLA-DETAIL-01 (AC#1) | INV-SLA-5 | incident OPEN, `resolution_due_at = now()−h` (quá khứ), `resolution_breached=0` | `get_incident_detail(name)` | `is_resolution_breached == 1` (derive LIVE; cờ thô DB vẫn 0) |
| TC-12-SLA-DETAIL-02 (AC#2) | INV-SLA-5 | incident OPEN, `resolution_due_at = now()+h` (tương lai) | `get_incident_detail(name)` | `is_resolution_breached == 0` |
| TC-12-SLA-DETAIL-03 (AC#3) | INV-SLA-5 | incident OPEN, `acknowledged_at` unset, `response_due_at = now()−h` (quá khứ) | `get_incident_detail(name)` | `is_response_breached == 1` |
| TC-12-SLA-DETAIL-04 (AC#4) | INV-SLA-6 (nhánh cờ) | incident terminal **`Closed`** + cờ thô `resolution_breached=1` | `get_incident_detail(name)` | `is_resolution_breached == 1` (breach qua **nhánh cờ**, KHÔNG live — terminal) |
| TC-12-SLA-DETAIL-PARITY | INV-SLA-5 | cùng 1 incident OPEN overdue | so `get_incident_detail(name)` vs `list_incidents()` row cùng `name` | `is_response_breached` + `is_resolution_breached` BẰNG nhau (1 SoT `_enrich_sla_breach`). `test_detail_list_sla_parity:968` |
| TC-12-SLA-DETAIL-TERMINAL0 | INV-SLA-6 (exclude) | incident `Closed` cờ=0, `due_at` quá khứ | `get_incident_detail(name)` | `is_*_breached == 0` (terminal đóng đúng hạn → KHÔNG live-overdue). `test_get_incident_detail_sla_terminal:955` |

> **Lưu ý phủ (delta round 4):** test hiện có (`test_get_incident_detail_sla_live:939`) đã phủ AC#2+AC#3 trong 1 case; `test_get_incident_detail_sla_terminal:955` phủ **terminal-exclude (cờ=0→0)**. Round 4 BỔ SUNG: **AC#1** (OPEN resolution quá hạn → 1) + **AC#4** (terminal `Closed` cờ=1 → 1, nhánh cờ) để đủ 4 nhánh AC-S6. Chạy `bench --site miyano run-tests` in `Ran N OK` là bằng chứng XANH của vòng (không parse curl-live — worker stale HARD-STOP).

**FE `incidentDetailSlaBadge.test.ts` (BR-12-13 / CR-21):** DETAIL-FE-01 section "Tình trạng SLA" bind `form.is_resolution_breached ?? form.resolution_breached` — form `is_resolution_breached=1` ∧ `resolution_breached=0` ⇒ badge "Vi phạm SLA xử lý" hiện (server-flag ưu tiên). DETAIL-FE-02 fallback: form CHỈ có cờ thô `resolution_breached=1` (không `is_*`) ⇒ badge vẫn hiện (nhánh `?? cờ thô`). DETAIL-FE-03 terminal-flag: `is_resolution_breached=1` (từ nhánh cờ) ⇒ badge hiện; cờ=0 dòng → pill "Trong hạn". **RED-prove:** đổi binding sang so `new Date(due_at) < Date.now()` ⇒ test client-clock FAIL (KHÔNG client-clock). Nhãn VI qua SSoT, KHÔNG leak `breached`/EN. `vue-tsc` 0.

**TC-12-SLA-ESC-* (BR-12-09 / BR-12-10) — bắt buộc cho DoD vòng này:**

| Test ID | Given | When | Then |
|---|---|---|---|
| TC-12-SLA-ESC-01 | 1 incident `assigned_to` set, quá `response_due_at`, `response_breached=0` | `check_incident_sla_breach()` chạy | `response_breached=1` + ĐÚNG 1 Notification Log (subject chứa "tiếp nhận") cho `assigned_to`; email enqueue cho user bật email |
| TC-12-SLA-ESC-02 | như trên, quá `resolution_due_at` | sweep | `resolution_breached=1` + 1 notification (subject chứa "xử lý"); nội dung nêu số giờ quá hạn + asset name |
| TC-12-SLA-ESC-03 (IDEMPOTENT) | incident đã `response_breached=1` từ lần trước | sweep chạy LẦN 2 | KHÔNG có notification mới (count Notification Log không đổi); cờ vẫn =1 |
| TC-12-SLA-ESC-04 (NO RECIPIENT) | incident không `assigned_to`/`reported_by`, policy không escalation_l*, severity=Low/Medium | sweep | set cờ + audit "phát hiện" như cũ; KHÔNG bắn rỗng; KHÔNG crash; KHÔNG audit "escalated" |
| TC-12-SLA-ESC-05 (BATCH RESILIENCE) | 2 incident, #1 lỗi policy resolve | sweep | #1 `log_error` + skip; #2 vẫn được set cờ + escalate; batch không dừng |
| TC-12-SLA-ESC-NĐ98 (BR-12-10) | incident severity=Critical breach, policy KHÔNG set escalation_l*_user | sweep | recipient bao gồm user giữ role `QA_OFFICER` + `OPS_MANAGER` (resolve qua `notify_roles`) — KHÔNG hardcode role-name |
| TC-12-SLA-ESC-AUDIT (BR-12-05) | incident escalate thành công | sweep | có 2 lifecycle entry: "phát hiện" (cũ) GIỮ NGUYÊN + "escalated → <recipients>" (mới) |

**Regression:** `test_notify_roles_contract` (TC-R21-01..04) vẫn xanh sau khi thêm block escalation incident vào `notify_roles.py`. KHÔNG đổi hành vi `notifications.run_sla_breach_scan` (IMM-09 Asset Repair) — chạy lại suite notification để xác nhận.

Mọi BR có ≥ 1 happy + ≥ 1 negative. BR Critical (BR-12-02, BR-12-04) cần Decision Table đầy đủ.

## IV.3. Component → Test mapping

| Component (I.1) | Test ID | Test layer | Coverage % | Risk priority (I.3) |
|---|---|---|---|---|
| `services/imm12::report_incident` | `TestIncidentCreation` (4) | Unit | *(Cần khảo sát)* | Critical |
| `services/imm12::validate_incident_close_gate` | `TestCloseGate` ⬜ | Unit | *(Cần khảo sát)* | Critical |
| `services/imm12::on_rca_completed` / `_advance_incident_after_rca` | `TestRCAToCAPAAndIncidentChain` (5) | Integration | *(Cần khảo sát)* | High |
| Incident workflow (10) | `TestIncidentWorkflow`, `TestIncidentCancellation` | Integration | 4/10 transition cover | High |
| RCA workflow (4) | `TestRCAToCAPAAndIncidentChain` | Integration | 1/4 transition cover | High |
| `services/imm12::detect_chronic_failures` | `TestChronicDetect` ⬜ | Unit/Cron | *(Cần khảo sát)* | High |
| `api/imm12::*` (14) | `test_imm12_api` ⬜ | API | *(Cần khảo sát)* | High/Medium |

Component Critical/High phải đạt coverage target III.10 trước go-live.

---

# Phần V — UAT Script

## V.1. Phạm vi UAT

- **In-scope:** tạo IR (Medium/High/Critical) + BR-12-01 validation; Acknowledge + phân công; Critical → auto OOS; Resolve Minor → Close trực tiếp; Resolve High/Critical → auto RCA; RCA 5-Why → Submit → CAPA auto-create; Close CAPA (BR-00-08) → Close Incident; chronic detection (BR-12-03); audit immutability; permission scope.
- **Out-of-scope:** load testing (III.8), security pentest (Phần VI), SMS notification, Vigilance BYT (IMM-15).
- **Pre-condition:** UAT site deploy version hiện hành, fixture loaded (`uat_imm12.py` ⬜ Planned), tester accounts active, Chrome/Edge ≥ 120.

## V.2. Tester accounts

⬜ Tạo khi UAT chuẩn bị. Roles khớp DocPerm thực tế của module.

| Username | Role | Vai trò UAT |
|---|---|---|
| `reporter.uat` | AssetCore System User | Báo cáo sự cố (read-only nâng cao); test permission FORBIDDEN |
| `tech.uat` | Corrective User | Resolve, bắt đầu RCA, hoàn thành RCA |
| `manager.uat` | Corrective Manager | Acknowledge, submit Incident, cancel |
| `qa.uat` | Compliance Manager | Yêu cầu RCA, xử lý + close CAPA |
| `auditor.uat` | AssetCore Auditor | Read-only, verify audit trail |
| `admin.uat` | AssetCore Super Admin | Full — setup/reset |

> Phải có account role thấp (`AssetCore System User`) để cover FORBIDDEN case, không chỉ Admin.

## V.3. Test data đã seed

⬜ Seed khi implement; reset script `uat_imm12.py` đi kèm.

| DocType | Số lượng | Ghi chú |
|---|---|---|
| AC Asset | 4 | 1 Class III life-support, 2 Class II, 1 thường — đủ cover Critical/High/Minor |
| Fault code dictionary | ≥ 8 | cho test chronic + cascade gợi ý |
| Incident Report (pre-seeded) | 3 | 2 IR cùng fault_code/asset/90d (cho TC chronic) + 1 backdated cho MTTA |
| Asset Repair WO | 1 | để test link Repair WO khi Resolve |

## V.4. UAT Scenarios — Suy ra từ US + Activity

ID `UAT-IMM-12-NN`. Mỗi US → ≥ 1 happy; mỗi exception branch → ≥ 1; mỗi role mutate → ≥ 1 permission verify; mỗi terminal transition → ≥ 1 audit verify.

| ID | Actor | Pre-condition | US/BR cover | Kỹ thuật | Kết quả mong đợi |
|---|---|---|---|---|---|
| UAT-IMM-12-01 | AssetCore System User | Asset Active | US-12-01 AC-01/02, BR-12-01, BR-12-04 | Use Case happy + EX-12-01 | IR Medium OK; Critical thiếu clinical_impact → block; Critical đủ → asset OOS auto + ALE |
| UAT-IMM-12-02 | Corrective Manager | IR Open | US-12-01 | Use Case + EP permission | Acknowledge OK, acknowledged_at set; System User Acknowledge → 403 |
| UAT-IMM-12-03 | Corrective User | IR Medium In Progress | BR-12-02 negative (Minor không RCA) | Use Case happy | Resolve → Resolved, không RCA; Manager Close → Closed |
| UAT-IMM-12-04 | Corrective User → Compliance Manager | IR High In Progress | US-12-01, BR-12-02, BR-12-06 | State Transition + EX-12-03 | Resolve High → RCA Required + RCA tạo; Close khi RCA In Progress → block (BR-12-02); Submit RCA → CAPA auto; Close OK |
| UAT-IMM-12-05 | Corrective User | RCA In Progress | BR-12-07 | EP + Error guessing | Submit RCA thiếu root_cause/rca_method → block; đủ → OK |
| UAT-IMM-12-06 | Compliance Manager | CAPA Open, đủ field | US-12-01, BR-00-08 | Use Case + permission | Compliance close CAPA OK; Corrective Manager close CAPA → 403 |
| UAT-IMM-12-07 | System (scheduler) + Corrective User | 2 IR cùng fault_code/asset/90d | US-12-02, BR-12-03 | BVA ngưỡng + idempotency | Tạo IR thứ 3 → run `detect_chronic_failures` → RCA chronic + flag; chạy lần 2 → không tạo trùng (EX-12-04) |
| UAT-IMM-12-08 | AssetCore Super Admin / Auditor | Có audit entries | BR-12-05, BR-00-03 | State Transition (tamper) | IMM Audit Trail read-only; DELETE/EDIT → block; `verify_audit_chain` = True |
| UAT-IMM-12-09 | Compliance Manager | Có IR/RCA dữ liệu | KPI §02 §II.6 | Use Case | Dashboard hiển thị MTTA/MTTR/open/critical; drill-down OK |
| UAT-IMM-12-10 | AssetCore System User | — | RBAC §VI.1 | EP permission | Không Acknowledge/Resolve/Close; chỉ Read theo scope |

## V.5. Tổng hợp kết quả & Bug found

⬜ Điền khi UAT thực hiện.

| Scenario | Status | Tester | Ngày | Ghi chú |
|---|---|---|---|---|
| UAT-IMM-12-01 … 10 | ⬜ Pending | | | |

**Bug log:** `Issue ID · Severity (Blocker/Major/Minor/Trivial) · Mô tả · Fix status` — điền khi phát sinh.

**Acceptance:** ≥ 95% PASS, Blocker = 0, Major ≤ 2 (có workaround). Critical TC bắt buộc 100% Pass: UAT-IMM-12-04, UAT-IMM-12-07, UAT-IMM-12-08.

**Sign-off:**

| Vai trò | Người | Ngày | Chữ ký |
|---|---|---|---|
| BA Lead | | | |
| QA Lead | | | |
| Module Owner (IMM-12) | | | |
| Đại diện end-user (Workshop Manager) | | | |

---

# Phần VI — Security Review (gate)

## VI.1. RBAC

**Role definitions** (`fixtures/role.json` + `role_profile.json`):

| Role | Quyền hạn trên IMM-12 |
|---|---|
| AssetCore Super Admin | Full (Incident + RCA + CAPA) |
| Corrective Manager | Incident: Read/Write/Create/Submit/Cancel/Delete |
| Corrective User | Incident + RCA: Read/Write/Create (no Submit) |
| Compliance Manager | CAPA: Read/Write/Create/Submit/Close; yêu cầu RCA |
| Compliance User | CAPA: Read/Write/Create (no Submit) |
| AssetCore Auditor | Read-only toàn bộ; verify audit trail |
| AssetCore System User | Read-only (scope) |

**DocPerm matrix — `Incident Report`** (xác minh từ `incident_report.json`):

| Role | Read | Write | Create | Submit | Cancel | Delete |
|---|---|---|---|---|---|---|
| AssetCore Super Admin | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Corrective Manager | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Corrective User | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| AssetCore Auditor | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| AssetCore System User | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |

**DocPerm matrix — `IMM RCA Record`** (xác minh từ `imm_rca_record.json`):

| Role | Read | Write | Create | Submit |
|---|---|---|---|---|
| AssetCore Super Admin | ✅ | ✅ | ✅ | ✅ |
| Corrective Manager | ✅ | ✅ | ✅ | ✅ |
| Corrective User | ✅ | ✅ | ✅ | ❌ |
| AssetCore Auditor | ✅ | ❌ | ❌ | ❌ |
| AssetCore System User | ✅ | ❌ | ❌ | ❌ |

**DocPerm matrix — `IMM CAPA Record`** (xác minh từ `imm_capa_record.json`, kế thừa IMM-00):

| Role | Read | Write | Create | Submit |
|---|---|---|---|---|
| AssetCore Super Admin | ✅ | ✅ | ✅ | ✅ |
| Compliance Manager | ✅ | ✅ | ✅ | ✅ |
| Compliance User | ✅ | ✅ | ✅ | ❌ |
| AssetCore Auditor | ✅ | ❌ | ❌ | ❌ |
| AssetCore System User | ✅ | ❌ | ❌ | ❌ |

**Field-level permission (permlevel):** hiện DocType IMM-12 chưa khai báo field permlevel ≠ 0. *(Cần khảo sát — đề xuất nâng permlevel cho `clinical_impact`, `root_cause`, CAPA `corrective_action`/`preventive_action`; chưa có trong JSON thực tế.)*

**User Permission (row-level):** `permission_query_conditions` cho scope theo department/asset — *(Cần khảo sát — chưa thấy hook query cho Incident Report trong codebase).*

**Kỹ thuật:** Decision Table — mỗi (role × action × state) = 1 row, expected Allow/Deny.

## VI.2. API security

| Mục | Trạng thái | Ghi chú |
|---|---|---|
| Whitelist hygiene | ⬜ Cần rà | 14 `@frappe.whitelist`; có `_has_role()` helper trong `api/imm12.py`; verify mỗi mutating endpoint gọi check role + docstring |
| CSRF | ✅ Frappe default | `X-Frappe-CSRF-Token` |
| Input validation | ⬜ Cần rà | `asset` Link validate trước dùng; `description` Text Editor sanitize XSS |
| SQL injection | ✅ ORM | dùng `frappe.get_all` / param query; không raw f-string SQL trong `imm12.py` (cần re-confirm `_build_incident_filters`) |
| Rate limit | ⬜ Roadmap | `report_incident` (clinical user có thể spam) |

## VI.3. Audit trail integrity

- Mọi state change sinh `IMM Audit Trail` qua `_log()` → `imm00.log_audit_event()` (SHA-256 chain). Không gọi trực tiếp, không bypass.
- Verify endpoint: `assetcore.utils.lifecycle.verify_audit_chain(asset)`.
- `IMM Audit Trail` DocPerm no-delete kế thừa IMM-00 (ISO 13485:7.5.9).
- Test tamper `test_audit_chain_breaks_on_tamper()` → III.5, ⬜ Planned.
- Retention ≥ 5 năm (NĐ98/2021/NĐ-CP Điều 7); CAPA ≥ 7 năm (ISO 13485).

## VI.4. Authentication & session

Login Frappe default; session timeout + lockout (3 fail → lock 15 phút) + password policy kế thừa cấu hình chung (08_Deployment §III.4). Reporting/System User từ mobile: validate session token, không cấp API key dài hạn. 2FA roadmap.

## VI.5. Data sensitivity

| Loại | Trường | Sensitivity | Bảo vệ |
|---|---|---|---|
| Mô tả sự cố lâm sàng | `clinical_impact`, `description` | Internal | Role permission |
| Thông tin bệnh nhân | `patient_impact_description` (Check `patient_affected`) | Restricted | Policy: KHÔNG lưu patient ID, chỉ mô tả tác động thiết bị |
| RCA root cause | `root_cause`, `five_why_steps` | Confidential | đề xuất permlevel 1 *(Cần khảo sát)* |
| CAPA action | `corrective_action`, `preventive_action` | Internal | Compliance role only |
| Chronic flag | `chronic_failure_flag` | Internal | đề xuất permlevel 1 *(Cần khảo sát)* |

Khẳng định: hệ thống KHÔNG lưu patient identifier — chỉ mô tả thiết bị.

## VI.6. Vendor isolation

Vendor External KHÔNG có quyền trên `Incident Report` / `IMM RCA Record` / `IMM CAPA Record` (không có trong DocPerm). Nếu mở rộng cho vendor contractor: chỉ thấy IR của asset trong contract của họ (qua `permission_query_conditions`); KHÔNG thấy RCA content, CAPA action, audit trail incident khác; KHÔNG export. → test ở III.6 (low-role API call).

## VI.7. Secrets management

Không có secrets mới trong IMM-12. Cấm commit `.env`/credential; `site_config.json` không lên git; external token lưu `frappe.conf`; backup encrypt at-rest off-site.

## VI.8. Logging & monitoring

⬜ Cấu hình khi vận hành. PII/token KHÔNG vào log.

| Sự kiện | Log level | Where | Alert? |
|---|---|---|---|
| Critical Incident tạo | WARNING | `IMM Audit Trail` + email | ✅ Workshop Lead + Dept Head |
| Chronic Failure phát hiện | WARNING | `frappe.log_error` + email | ✅ Workshop Lead + QA |
| CAPA overdue > due_date | WARNING | Scheduler log + email | ✅ Compliance (daily) |
| Audit chain tamper | ERROR | `frappe.log_error` | ✅ System Admin |
| Mass incident creation (>10 IR/phút) | WARNING | Nginx log | ✅ DevOps |

## VI.9. Threat model (STRIDE-lite)

| Threat | Vector | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| **S**poofing | Báo cáo sự cố giả để chiếm WO | Low | Medium | `reported_by` gắn session user; audit actor |
| **T**ampering (severity) | Hạ Critical → Medium tránh RCA | Low | High | sau Submit chỉ Corrective Manager+ sửa được; audit |
| **T**ampering (audit) | Sửa `IMM Audit Trail` DB | Low | Critical | DocPerm no-delete (IMM-00); verify chain |
| **R**epudiation | Phủ nhận đã Resolve | Low | High | `resolved_at` + actor + audit hash |
| **I**nfo disclosure | Xem IR ngoài scope | Low | Medium | DocPerm read scope; `permission_query_conditions` (⬜ cần implement) |
| **D**oS | Scheduler quét 100k+ IR | Medium | Medium | index `fault_code + asset + reported_at`; batch chronic |
| **E**levation of privilege | System User tự Submit/Close CAPA | Low | High | DocPerm: CAPA Submit chỉ Compliance Manager+; Incident Submit chỉ Corrective Manager+ |

## VI.10. Penetration test

⬜ Trước release đầu tiên: Burp/ZAP scan trên UAT site, sqlmap (an toàn), CSRF test, role escalation (`report_incident` no clinical_impact → block; CAPA close by System User → 403; chronic detect idempotent). Report lưu `docs/security/pentest_imm12_v1.md`.

## VI.11. Sign-off

⬜ Điền khi security review hoàn tất.

| Role | Người | Ngày | Quyết định |
|---|---|---|---|
| QA Lead | | | ☐ Pass / ☐ Pass with conditions / ☐ Fail |
| Tech Lead | | | ☐ Pass / ☐ Pass with conditions / ☐ Fail |
| Module Owner | | | ☐ Pass / ☐ Pass with conditions / ☐ Fail |

---

# Phần VII — Code Quality

## VII.1. Tool matrix

> Code đã LIVE — áp dụng tiêu chuẩn sau cho mỗi PR.

| Tool | Mục tiêu | Target | Cadence |
|---|---|---|---|
| **SonarQube** (BE Python) | bug 0 critical, code smell ≤ 5, duplication ≤ 3%, coverage ≥ 70%, security hotspot review 100% | Quality Gate pass | Mỗi PR (CI gate) |
| **Lighthouse** (FE — IMM12Dashboard) | Performance ≥ 90, Accessibility ≥ 95, Best Practices ≥ 90, SEO ≥ 80 | ≥ target | Mỗi release lớn + monthly |
| **ESLint + vue-tsc** (FE) | 0 error, 0 warning prod build | pass | Mỗi PR FE |
| **ruff / black** (BE) | 0 error, PEP8 | pass | Mỗi PR |
| **Bundle size** (FE chunk imm12) | main ≤ 250KB gzip, async ≤ 80KB gzip | ≤ budget | Mỗi PR FE |

## VII.2. Cadence

- SonarQube: mỗi PR (CI gate, fail nếu Quality Gate fail).
- Lighthouse: mỗi release lớn + monthly audit.
- ESLint / ruff: mỗi PR (CI gate).
- Bundle size: mỗi PR FE (CI report, fail nếu vượt budget).

Gắn screenshot SonarQube + Lighthouse vào file 09 §Release Notes khi báo cáo final.

---

# Phụ lục A — Template per UAT scenario

```markdown
### UAT-IMM-12-<NN> — <Tên>

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
### TC-IMM-12-<LAYER>-<NN> — <Tên>

**Component (I.1)**: <…>
**Liên kết**: US-<NN> | BR-<NN> | ACT-<NN>
**Kỹ thuật (II.1/II.2)**: BVA boundary `<field>=<value>`
**Priority (I.3)**: Critical / High / Medium / Low
**Test type**: Unit / Integration / API / E2E
**Pre-condition**: <fixture / state setup>

**Input**:
- <field>: <value>

**Steps**:
1. <…>
2. <…>

**Expected**:
- ServiceError(code=VALIDATION, message contains "BR-12-…")
- doc.workflow_state unchanged

**Post-condition**: <DB rollback / fixture cleanup>
```

# Phụ lục C — Workflow State Transition Test template

```markdown
### TC-IMM-12-WF-<NN> — <action>: <from> → <to>

**Workflow JSON**: `assetcore/assetcore/workflow/imm_12_incident_workflow.json` (hoặc `imm_12_rca_workflow.json`)
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
- [x] Test class structure cho service public function (I.1)
- [x] ≥ 1 happy + 1 negative test mỗi function (specified; một số ⬜ Planned)
- [ ] Workflow transitions cover 100% — hiện 5/14 transition có test ✅, còn 9 ⬜ Planned
- [ ] Audit chain test (intact + tampered) — ⬜ Planned
- [ ] API test ≥ 60% coverage + permission matrix — ⬜ Planned (14 endpoint specified)
- [x] Performance target xác định (chưa chạy)
- [x] CI command chạy clean (`bench run-tests --module …`, file đã tồn tại)
- [ ] SonarQube Quality Gate pass + Lighthouse ≥ target — chưa có evidence

## IV. Traceability
- [x] IV.1 US → Test: mọi US có ≥ 1 Test ID
- [x] IV.2 BR → Test: mọi BR có dòng (một số negative ⬜ Planned)
- [ ] IV.3 Component → Test: Critical/High đạt coverage target — coverage % *(Cần khảo sát)*

## V. UAT
- [x] Mỗi US có ≥ 1 UAT scenario
- [x] ≥ 1 negative + permission + audit verify scenario
- [ ] Test data seed script `uat_imm12.py` chạy được — ⬜ Planned
- [ ] Tester accounts đã tạo ở UAT site — ⬜ Planned (đã liệt kê role)
- [x] Sign-off section sẵn sàng

## VI. Security
- [x] DocPerm matrix đầy đủ (Incident + RCA + CAPA — xác minh từ JSON)
- [ ] Mọi field nhạy cảm có permlevel ≠ 0 — chưa khai báo trong JSON *(Cần khảo sát)*
- [ ] SQL injection + CSRF test pass — CSRF default ✅, SQL/inj test ⬜ Planned
- [ ] Audit chain test pass (intact + tampered) — ⬜ Planned
- [ ] Vendor isolation test pass — ⬜ Planned (policy documented)
- [x] Threat model đủ 6 STRIDE với mitigation
- [ ] Sign-off đầy đủ trước go-live — ⬜ Pending

## VII. Code Quality
- [ ] SonarQube Quality Gate pass — chưa có evidence
- [ ] Lighthouse ≥ target — chưa có evidence
- [ ] Bundle size ≤ budget — chưa đo
- [ ] Screenshot báo cáo gắn vào file 09 — ⬜ Pending
