# 07 — Kiểm thử & An ninh (Testing & QA & Security)

| Mục | Giá trị |
|---|---|
| Module | IMM-00 — Master / Cross-cutting (Foundation) |
| Phạm vi | Per-module |
| Owner | QA Lead + Security Officer |
| Liên kết | 02 Analysis (FR, BR, Activity, BPMN) · 03 Diagrams · 04 Backend · 05 API · 06 Frontend |

> **Mục đích**: Suy ra test case **có hệ thống** từ phân tích (file 02) bằng kỹ thuật black-box + white-box, không liệt kê tự phát. Bao gồm: phân tích đối tượng test → chọn kỹ thuật → viết test → traceability → UAT → security → code quality. Phần VI (Security) là gate go-live.
>
> IMM-00 là foundation layer — lỗi tại đây ảnh hưởng tất cả 17 module (IMM-01→IMM-17). Do đó coverage target cao hơn module nghiệp vụ thường.

---

# Phần I — Test Analysis (Phân tích đối tượng test)

> Mục tiêu Phần I: trả lời 4 câu hỏi trước khi viết test case: **(1) test cái gì** (component inventory) **(2) suy ra từ đâu** (FR/BR/Activity) **(3) ưu tiên cái nào** (risk) **(4) loại trừ cái nào** (out-of-scope).

## I.1. Component Inventory — Liệt kê phần mềm cần test

Toàn bộ artefact test được của foundation layer. Mỗi dòng → ≥ 1 test class ở Phần III. (Module có 105 endpoint + 31 service function + 105 DocType — bảng dưới liệt kê các artefact **trọng yếu của foundation lifecycle**; nhóm depreciation / transfer / firmware là sub-domain mở rộng.) → 04 Backend §DocType + §Service · 05 API §Catalog · 06 Frontend §Components.

| # | Component | Loại | File / Tên | Test layer áp dụng |
|---|---|---|---|---|
| 1 | AC Asset | DocType | `ac_asset/ac_asset.json` | Integration (lifecycle) |
| 2 | IMM Audit Trail | DocType | `imm_audit_trail/imm_audit_trail.json` | Integration (audit chain) |
| 3 | Asset Lifecycle Event | DocType | `asset_lifecycle_event/*.json` | Integration (append-only) |
| 4 | IMM CAPA Record | DocType (submittable) | `imm_capa_record/*.json` | Integration (lifecycle) |
| 5 | IMM SLA Policy | DocType | `imm_sla_policy/*.json` | Unit (resolve logic) |
| 6 | IMM Device Model | DocType | `imm_device_model/*.json` | Integration (BR-00-01 mapping) |
| 7 | Incident Report | DocType | `incident_report/*.json` | Integration |
| 8 | AC Asset lifecycle | Workflow | `workflow/ac_asset_lifecycle_workflow.json` | Integration (state transition) |
| 9 | `log_audit_event` | Service function | `services/imm00.py::log_audit_event` | Unit + Integration (SHA-256) |
| 10 | `verify_audit_chain` | Service function | `services/imm00.py::verify_audit_chain` | Unit + Integration |
| 11 | `transition_asset_status` | Service function | `services/imm00.py::transition_asset_status` | Integration (state + side effects) |
| 12 | `validate_asset_for_operations` | Validator | `services/imm00.py::validate_asset_for_operations` | Unit (EP gate) |
| 13 | `get_sla_policy` | Service function | `services/imm00.py::get_sla_policy` | Unit (Decision Table fallback) |
| 14 | `create_capa` / `close_capa` | Service function | `services/imm00.py::create_capa`, `::close_capa` | Unit + Integration (BR-00-08) |
| 15 | `check_capa_overdue` | Scheduler job | `services/imm00.py::check_capa_overdue` | Unit + Cron simulation |
| 16 | `check_*_expiry` (vendor/registration/insurance/service_contract) | Scheduler job | `services/imm00.py::check_*_expiry` | Unit + Cron simulation |
| 17 | `rollup_asset_kpi` | Scheduler job | `services/imm00.py::rollup_asset_kpi` | Unit |
| 18 | Transfer request flow | Service function | `services/imm00.py::create/approve/reject/confirm/cancel_transfer_request` | Integration |
| 19 | GMDN inheritance/resync | Service function | `services/imm00.py::resync_assets_gmdn_from_model`, `::cascade_category_gmdn` | Integration (BR-00-13/14) |
| 20 | `list_assets` (+ GMDN filter) | API endpoint | `api/imm00.py::list_assets` | API integration |
| 21 | `transition_status` | API endpoint | `api/imm00.py::transition_status` | API integration |
| 22 | `verify_chain` | API endpoint | `api/imm00.py::verify_chain` | API integration |
| 23 | `open_capa` / `close_capa_record` | API endpoint | `api/imm00.py::open_capa`, `::close_capa_record` | API integration |
| 24 | `update_user_roles` | API/service | role management (RBAC) | Integration (permission) |
| 25 | AC Asset permission query | Permission hook | `permission.py::get_ac_asset_permission_query()` | Integration (RBAC isolation) |
| 26 | ReferenceDataView / SlaPolicyListView | FE view | `frontend/src/views/master-data/*.vue` | E2E (Playwright) |
| 27 | useAssetStore / useRefDataStore / useCapaStore / useIncidentStore | Pinia store | `frontend/src/stores/imm00.ts` | Unit (vitest) |

## I.2. Trace nguồn test — Functional Requirements, Activity Flows, Business Rules

> IMM-00 đặc tả nghiệp vụ theo **FR-00-NN** (Functional Requirement) thay vì User Story; mỗi FR là input test tương đương US. Mỗi FR/BR phải có ≥ 1 test ở Phần III và xuất hiện trong matrix Phần IV. → 02 §Functional Specs (FR) · 02 §Business Rules · 03 Sequence diagrams.

### I.2.a. Từ Functional Requirement
| FR ID | Tiêu đề ngắn | Acceptance Criteria # | Test layer dự kiến |
|---|---|---|---|
| FR-00-01 | Tạo AC Asset auto naming | naming series `AC-ASSET-#####`, lifecycle_status init | Integration + API + UAT |
| FR-00-02 | List AC Asset filter (department/location/status/risk/gmdn) | filter chính xác, pagination | API + UAT |
| FR-00-03 | Update AC Asset (trừ lifecycle_status) | block payload `lifecycle_status` | API + Integration |
| FR-00-04 | Transition qua `transition_asset_status()` | đổi status + sinh ALE + audit | Integration + UAT |
| FR-00-05 | Gate `validate_asset_for_operations()` | block Out of Service / Decommissioned | Unit + UAT |
| FR-00-06..09 | AC Supplier CRUD + ISO 17025 + inactive block | warning ISO, autoname | Integration |
| FR-00-19..22 | Audit Trail append-only + SHA-256 + verify | chain hợp lệ, immutable | Integration + Security |
| FR-00-23..27 | CAPA create/close/overdue/link | before_submit gate, auto-overdue | Unit + Integration + UAT |
| FR-00-28..30 | Lifecycle Event append-only + 1 ALE/transition | in_create enforce | Integration |
| FR-00-43..46 | GMDN hierarchy (Category→Model→Asset) | inherit at before_insert, override | Integration |
| FR-00-47..52 | Kế thừa luật khấu hao Category→Asset (SoT `inherit_depreciation_rules_from_category`) + nút global backfill | inherit at before_insert (months/residual), no-clobber, compute_all backfill-rồi-sinh, idempotent, audit | Unit + Integration + API |
| FR-00-53..55 | **Per-asset self-heal (RC-04, Round-2)** tại `regenerate_depreciation_schedule` cho asset CŨ | inherit-trước-precheck (200/periods>0), no-che-master-data (422 đúng field), no-clobber, preserve Executed, idempotent + audit (ALE+IMM Audit Trail chỉ khi did_inherit) | Unit + Integration + API + grep-guard |
| FR-00-56..58 | **`bulk_regenerate_by_category` hợp nhất về SoT (RC-05, Round-4)** — nút "Áp dụng khấu hao theo từng Danh mục" | no-clobber (route qua SoT, bỏ 4 dòng inline), N+1 đóng (1 query GROUP BY executed-history), payload 7-key `+inherited+skipped_no_rule`, preserve Executed, idempotent, audit (per-asset ALE + 1 IMM Audit Trail tổng), FE BaseModal thay window.confirm | Unit + Integration + Performance(query-count) + grep-guard + FE vitest |
| FR-00-59..62 | **Thanh lý hủy kỳ Pending khấu hao (RC-07, Vòng 8)** — `transition_asset_status(Decommissioned)` → `_cancel_pending_depreciation_on_decommission` | hủy MỌI Pending → Cancelled (pending_periods=0), Executed bất biến (accumulated/book không đổi), cron không đào lại (executed_rows=0), idempotent (0 Pending→0 event), ≥1 hủy → 1 ALE `depreciation_stopped` + 1 IMM Audit Trail `System`, best-effort (lỗi audit không vỡ transition), schema-delta `event_type+=depreciation_stopped` | Unit + Integration(cron+audit) + State/Idempotent + fault-injection + schema (RED-first TC-DEP-80) |
| FR-00-63..69 | **Tạm ngừng sử dụng: PAUSE + DỜI lịch khấu hao (RC-08, Vòng 9) + nhãn `restored` single-emit (RC-09, Vòng 14)** — `transition_asset_status('Out of Service')` → `_pause_depreciation_on_oos`; `transition_asset_status('Active' từ prev='Out of Service')` → emit ĐÚNG 1 ALE `restored` (qua `_lifecycle_event_for(to,from)`) + `_reschedule_pending_depreciation_on_restore` (CHỈ audit) | PAUSE: executor không trích trong window OoS (executed_rows=0, book bất biến); NO PHANTOM CATCH-UP (bug chính RC-08): delta_accumulated=0 cho kỳ idle sau restore; RESCHEDULE: kỳ Pending dời `scheduled_date += oos_days` (count/sum/period_number/amount bất biến); Executed/Cancelled bất biến; oos_start SoT (downtime log → fallback ALE → no-op không raise); idempotent (Active→Active no-op không dời kép); **audit (RC-09): ≥1 ALE `out_of_service`(pause) + ĐÚNG 1 ALE `restored`(resume, do transition) + 0 `activated` + ≥1 IMM Audit Trail — bất kể có/không Pending (consistency); KHÔNG double-emit**; đường về Active không-từ-OoS giữ `activated`; KHÔNG schema-delta | Unit + Integration(cron+audit) + State/Idempotent + fault-injection + fallback (RED-first TC-DEP-92 + TC-ALE-RESTORE-01) |

### I.2.b. Từ Business Rule
| BR ID | Phát biểu | Component liên quan (I.1) | Kỹ thuật test phù hợp |
|---|---|---|---|
| BR-00-01 | Class I→Low; II→Medium; III→High/Critical | IMM Device Model `.validate()` | Decision Table / EP |
| BR-00-02 | `lifecycle_status` chỉ đổi qua `transition_asset_status()` | AC Asset controller + service | EP (block direct mutate) |
| BR-00-03 | IMM Audit Trail + ALE immutable | Controller + Permission | Error guessing (update/delete) |
| BR-00-04 | Decommissioned → suspend PM/Calibration schedule | `transition_asset_status()` → `_suspend_all_schedules()` | State Transition |
| BR-00-05 | Out of Service / Decommissioned → block Work Order | `validate_asset_for_operations()` | EP (status partition) |
| BR-00-24 | Decommissioned → hủy MỌI kỳ khấu hao Pending → Cancelled (chốt sổ); Executed bất biến; cron không đào lại; idempotent; ≥1 hủy → 1 ALE `depreciation_stopped` + 1 IMM Audit Trail `System`; best-effort audit; schema-delta `event_type+=depreciation_stopped` | `transition_asset_status()` → `_cancel_pending_depreciation_on_decommission()` | State Transition + Integration(cron+audit) + Idempotent + fault-injection + schema |
| BR-00-25 | Out of Service → TẠM DỪNG trích (executor không chạy, book bất biến); Out of Service → Active → DỜI kỳ Pending `scheduled_date += oos_days` (diệt phantom catch-up, delta_accumulated=0 cho kỳ idle); Executed/Cancelled bất biến; oos_start SoT (downtime log → fallback ALE → no-op không raise); idempotent (no double-shift); audit ALE `out_of_service`(pause) + IMM Audit Trail; KHÔNG schema-delta | `transition_asset_status()` → `_pause_depreciation_on_oos()` + `_reschedule_pending_depreciation_on_restore()` | State Transition + Integration(cron+audit) + Idempotent + fault-injection + fallback |
| BR-00-27 | **Nhãn sự kiện khôi phục `restored` ĐÚNG 1 — single-emit (RC-09, Vòng 14):** 1 transition `Out of Service → Active` → ĐÚNG 1 ALE `restored` + 0 `activated` (bất kể có/không Pending — consistency); `_lifecycle_event_for(to='Active',from='Out of Service')='restored'`, from khác='activated'; helper reschedule KHÔNG emit ALE (kill double-emit); đồng nhất 2 call-site (service + workflow `on_update`); audit-trail bất biến (hash-chain không vỡ, count không giảm); KHÔNG schema-delta. **REGRESSION:** test_imm09:839 + test_imm11:1317/branch-A (`activated`) GIỮ. | `_lifecycle_event_for(to,from)`; `transition_asset_status()` + `ac_asset.on_update()` | State Transition + Decision table + Integration(audit chain) + no-regression (TC-ALE-RESTORE-01..07) |
| BR-00-06 | Calibration Lab thiếu iso_17025_cert → warning | `ACSupplier.validate()` | EP (warning, không block) |
| BR-00-07 | response_min < resolution_hours × 60 | `IMMSLAPolicy.validate()` | BVA |
| BR-00-08 | CAPA before_submit: root_cause + corrective + preventive | `IMMCAPARecord.before_submit()` | Decision Table |
| BR-00-09 | CAPA quá due_date → auto Overdue (scheduler) | `check_capa_overdue()` | BVA (date boundary) |
| BR-00-10 | Mỗi đổi lifecycle_status → 1 ALE | `transition_asset_status()` | State Transition |
| BR-00-13 | GMDN kế thừa một chiều Category→Model→Asset | `before_insert` hooks | EP + Integration |
| BR-00-14 | Override GMDN cho phép cả 3 cấp; không ghi đè sau insert | `before_insert` chỉ điền khi trống | EP |
| BR-00-16 | `list_capas` conjoin (AND) explicit status + virtual not_closed/overdue; KHÔNG clobber | `list_capas()` | Decision Table + set-algebra |
| BR-00-18 | Kế thừa luật khấu hao SoT; residual = `round(gross*pct/100,2)`; idempotent | `inherit_depreciation_rules_from_category()` | EP + BVA (months=0 boundary) |
| BR-00-19 | Không clobber months/residual user nhập; per-field độc lập | `before_insert` chỉ điền field trống | Decision Table (4 combo: months set/unset × residual set/unset) |
| BR-00-20 | Category months=0 → không bịa số; regenerate 422 đúng | `inherit_...` no-op + `regenerate_depreciation_schedule()` | EP (negative — không che lỗi master-data) |
| BR-00-21 | `compute_all` backfill-rồi-sinh; preserve Executed history; idempotent; RBAC 403; audit event | `compute_all_depreciation()` | Integration + State + Security |
| BR-00-22 | Per-asset self-heal tại `regenerate` (RC-04): inherit-trước-precheck; precheck chạy LẠI sau; no-clobber; preserve Executed; idempotent; audit chỉ khi did_inherit; grep-guard 1 SoT | `regenerate_depreciation_schedule()` → `inherit_depreciation_rules_from_category()` | EP + Decision Table + State + Integration + grep-guard |
| BR-00-23 | `bulk_regenerate_by_category` route qua SoT (RC-05): no-clobber 4 field user; N+1 đóng (1 query GROUP BY executed-history); preserve Executed; skipped_no_rule không che master-data; idempotent; payload 7-key; audit per-asset ALE + 1 IMM Audit Trail; grep-guard 0 inline copy | `bulk_regenerate_by_category()` → `inherit_depreciation_rules_from_category()` | Decision Table + Performance(query-count) + State + Integration + grep-guard |
| BR-05-13 | SoT `effective_book_value` fix falsy-zero (RC-06): None→gross, 0.0→0.0 (KHÔNG `or gross`); fully_depreciated đếm asset book=0.0; total_book/by_category no-phantom; count==drill; no-regression book=None; grep-guard 0 idiom `or gross` | `effective_book_value()` → `compute_depreciation()` + `_depr_enrich_row()` + `get_depreciation_stats()` + `is_fully_depreciated()` | EP(boundary None/0.0) + Decision Table(RED-first) + Integration(invariant) + Regression + grep-guard |

#### TC cho BR-00-16 — filter composition (conjoin, no-clobber)
| TC | Request | Expected | Kỹ thuật |
|---|---|---|---|
| TC-00-CAPA-01 | `?not_closed=1&status=Overdue` | CHỈ tập Overdue (subset), KHÔNG full open-set (KHÔNG còn 117 như trước fix) | set-algebra (∧) |
| TC-00-CAPA-02 | `?not_closed=1&status=Closed` | 0 rows (tập rỗng — `(NOT IN Closed) ∧ (== Closed)`) | minh chứng AND thật |
| TC-00-CAPA-03 | `?overdue=1&status=Open` | 0 rows (`Open` ∉ tập flip Overdue) | overdue ∧ explicit status |
| TC-00-CAPA-04 | mọi tổ hợp `{status} × {not_closed\|overdue\|none}` | `pagination.total == len(items)` (count & get_list cùng filter) | INVARIANT count==drill |
| TC-00-CAPA-05 | `?not_closed=1` (no status) | == `_open_capa_filter()` byte-for-byte | no-regression BR-00-15 |
| TC-00-CAPA-06 | `?overdue=1` (no status) | == `_overdue_capa_filter()` byte-for-byte | no-regression BR-00-09 (round 10/11) |

### I.2.c. Từ Activity Flow / Sequence
| Flow ID | Use Case | Branch chính | Branch ngoại lệ |
|---|---|---|---|
| SEQ-audit | Log audit + SHA-256 chain | Mutation → log_audit_event → chain link | Tamper record → verify_chain false |
| SEQ-transition | Transition asset status | Active→Under Repair (happy) | Bypass field, Decommissioned→X (invalid) |
| SEQ-capa | CAPA lifecycle | Open→fill→Close (submit) | Thiếu root_cause → throw; quá hạn → Overdue |
| SEQ-sched | Scheduler check_capa_overdue | Open + due<today → Overdue + email | Server down → idempotent retry (RISK-00-03) |

## I.3. Risk-based Priority

| Component (I.1) | Likelihood (1-5) | Impact (1-5) | Risk = L×I | Priority |
|---|---|---|---|---|
| `log_audit_event` / SHA-256 chain | 3 | 5 | 15 | **Critical** |
| `transition_asset_status` (state machine) | 4 | 5 | 20 | **Critical** |
| AC Asset permission query (RBAC isolation) | 4 | 5 | 20 | **Critical** |
| `close_capa` before_submit gate (BR-00-08) | 3 | 4 | 12 | High |
| `validate_asset_for_operations` gate | 3 | 4 | 12 | High |
| `get_sla_policy` fallback | 3 | 3 | 9 | Medium |
| `check_capa_overdue` / `check_*_expiry` scheduler | 3 | 3 | 9 | Medium |
| BR-00-01 class/risk mapping | 2 | 4 | 8 | Medium |
| GMDN inheritance / resync | 3 | 3 | 9 | Medium |
| Reference data list views (read-only) | 2 | 2 | 4 | Low |

**Quy ước priority**:
- **Critical** (R ≥ 15): test trước, fail = block release
- **High** (10 ≤ R < 15): bắt buộc trước go-live
- **Medium** (5 ≤ R < 10): trong sprint khi có thời gian
- **Low** (R < 5): chỉ test khi báo cáo bug

## I.4. Scope

- **In-scope**: foundation lifecycle (AC Asset state machine), audit trail SHA-256 chain + verify, CAPA lifecycle gate (BR-00-08), SLA resolve fallback, RBAC permission query isolation, BR-00-01 class/risk mapping, GMDN inheritance.
- **Out-of-scope**:
  - Performance test → giao Phần III.8 (target-only, chưa chạy k6 baseline).
  - Cross-module (IMM-01→17 gọi foundation service) → chỉ smoke; deep test thuộc file 07 của từng module.
  - Depreciation/transfer/firmware sub-domain → unit-level riêng, không trong gate go-live foundation.
- **Assumptions**: master data (AC Asset Category, AC Department, AC Location, IMM SLA Policy fixtures) đã seed qua `bench migrate`; test users đủ các role (PM User, PM Manager, System Manager, AssetCore Super Admin); chạy trên site test với `--app assetcore`.

---

# Phần II — Test Design Techniques (Kỹ thuật thiết kế test case)

> Mỗi test phải truy được về 1 kỹ thuật ở dưới.

## II.1. Black-box techniques

| Kỹ thuật | Khi nào dùng | Áp dụng vào IMM-00 | Số test sinh ra |
|---|---|---|---|
| **Equivalence Partitioning (EP)** | Input có miền giá trị chia nhóm | `lifecycle_status` enum, `medical_device_class`, `priority × risk_class`, role partition | 1 test/partition |
| **Boundary Value Analysis (BVA)** | Numeric / date có biên | `response_time_minutes` vs `resolution_time_hours×60` (BR-00-07); `due_date` quá hạn (BR-00-09) | 2-3 test/biên |
| **Decision Table** | Multi-condition gate | BR-00-08 (root_cause AND corrective AND preventive); BR-00-01 class→risk map; SLA exact-vs-default | 2^N rút gọn |
| **State Transition Testing** | Workflow finite state machine | `ac_asset_lifecycle_workflow.json` — 16 transition + invalid transition (Decommissioned terminal) | mỗi transition + invalid |
| **Use Case Testing** | End-to-end actor flow | UAT scenarios (V.4), API integration | 1/main + 1/alt + 1/exception |
| **Error Guessing** | null, empty, tamper, race | Audit tamper, direct lifecycle_status mutate, scheduler double-run | bổ sung |

## II.2. White-box techniques

| Kỹ thuật | Áp dụng vào | Tiêu chí đạt | Công cụ |
|---|---|---|---|
| **Statement coverage** | `services/imm00.py` | ≥ 85% line | `coverage report` |
| **Branch / Decision coverage** | `transition_asset_status`, `get_sla_policy`, `_sync_downtime_log` (if/else) | ≥ 80% branch | `coverage --branch` |
| **Condition / MC/DC** | BR-00-08 before_submit gate, BR-00-01 class map | mỗi sub-condition kiểm soát outcome độc lập | manual + coverage |
| **Path coverage** | `_lifecycle_event_for`, `_suspend_all_schedules` | toàn bộ path (loop 0,1,N) | manual |

Ưu tiên Branch coverage cho service layer; MC/DC chỉ áp dụng gate BR-00-08 (3 condition AND → 4 test).

## II.3. Mapping Component → Kỹ thuật

| Loại component | Kỹ thuật chính | Kỹ thuật phụ |
|---|---|---|
| Field validator (`.validate()` controller) | BVA + EP | Error guessing |
| Gate logic (BR-00-08 before_submit, validate_for_operations) | Decision Table | MC/DC |
| Workflow transition (lifecycle) | State Transition | Use Case |
| Service function (get_sla_policy, log_audit_event) | EP + Branch coverage | BVA |
| API endpoint | Use Case + EP | Pairwise (filter combo) |
| Scheduler (check_capa_overdue, check_*_expiry) | Use Case (setup→run→assert) | Error guessing (idempotent) |
| FE view (Playwright) | Use Case end-to-end | Error guessing (role gate, 4xx) |

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

Theo CLAUDE.md §17 (TDD mandatory). Hiện trạng IMM-00: phần lớn test là **Integration (DocType lifecycle)** vì foundation chủ yếu kiểm side-effect DB.

## III.2. Unit test — Service Layer

File: `assetcore/tests/test_imm00.py` (live), `assetcore/tests/test_imm00_smoke.py` (live).

| Test class | Function cover | Kỹ thuật | Trạng thái |
|---|---|---|---|
| `TestIMSLAPolicy` (`test_resolve_default_policy`, `test_resolve_fallback_to_default`) | `get_sla_policy` / `resolve_sla_policy` | Decision Table (exact vs default) | ✅ Live |
| `TestIMMDeviceModel` (`test_model_created`) | `IMMDeviceModel.validate` BR-00-01 | EP | ✅ Live |
| `TestS04_DeviceModelClassMappingRisk` (`test_class_ii_maps_to_medium`) | BR-00-01 Class II→Medium | Decision Table | ✅ Live |
| `TestS05_DeviceModelFetchPayload` (`test_get_device_model_returns_autofill_fields`) | `get_device_model` autofill | EP | ✅ Live |
| `TestS11_CheckCapaOverdueScheduler` (`test_check_capa_overdue_runs_without_error`) | `check_capa_overdue` | Use Case (cron sim) | ✅ Live |
| `*(Cần khảo sát)* unit thuần `get_sla_policy` boundary BR-00-07 | `IMMSLAPolicy.validate` | BVA | ⬜ Planned |

### III.2b. Notification Framework — TDD test cases (viết TRƯỚC implement)

File: `assetcore/tests/test_notifications.py`. Chạy: `bench --site miyano run-tests --module assetcore.tests.test_notifications`. Dùng `frappe.flags.in_test` (notification log tạo đồng bộ) + `frappe.flags.mute_emails=False` mock `_safe_sendmail` để assert gọi.

| TC ID | Test | Cover | Assert | Kỹ thuật |
|---|---|---|---|---|
| TC-NTF-01 | `test_notify_assignment_creates_notification_log` | `notify_assignment` | Notification Log tạo cho `assigned_to`, type=Alert, document_type/name khớp WO | EP |
| TC-NTF-02 | `test_notify_assignment_skips_self_assign` | `resolve_recipients` | actor == assignee → KHÔNG tạo Notification Log | EP |
| TC-NTF-03 | `test_notify_assignment_idempotent_when_unchanged` | listener idempotent | save lại không đổi assigned_to → không tạo log trùng | State Transition |
| TC-NTF-04 | `test_notify_approval_pending_resolves_approver` | `notify_approval_pending` | workflow_state → pending-approval → log cho approver (role + supervisor) | Decision Table |
| TC-NTF-10 | `test_state_needs_approval_dynamic_from_workflow` | `_state_needs_approval` | Repair `Pending Inspection` (transition→Completed bởi System Manager) ⇒ True; `Open`/state do role thường ⇒ False. Không hard-code tên state. | Decision Table |
| TC-NTF-11 | `test_resolve_approvers_by_workflow_role` | `resolve_approvers_by_workflow` | Asset Repair vào `Pending Inspection` → approver = user enabled giữ role `System Manager`, KHÔNG cần field `supervisor`; actor bị loại; dedupe. | Decision Table |
| TC-NTF-12 | `test_resolve_approvers_includes_supervisor_when_present` | `resolve_approvers_by_workflow` | doc có `supervisor` set → approver = union(role-users, supervisor), dedupe. | Decision Table |
| TC-NTF-13 | `test_approval_pending_noop_when_state_not_approval` | `notify_approval_pending` | state mà transition kế tiếp do role thường → KHÔNG tạo Notification Log (tránh false-positive). | Error guessing |
| TC-NTF-05 | `test_email_sent_when_user_enabled` | `_user_wants_email`+`_dispatch` | enable_email_notifications=1 → `_safe_sendmail` được gọi với recipient | Decision Table |
| TC-NTF-06 | `test_email_skipped_when_user_disabled` | `_user_wants_email` | enable_email_notifications=0 → `_safe_sendmail` KHÔNG gọi (bell vẫn tạo) | Decision Table |
| TC-NTF-07 | `test_get_notification_preferences_returns_envelope` | API `get_notification_preferences` | `{success:true, data:{email_enabled:bool}}` | EP |
| TC-NTF-08 | `test_set_email_enabled_persists` | API `set_email_enabled` | set False → đọc lại = False; Notification Settings updated | State Transition |
| TC-NTF-09 | `test_listener_handles_cancelled_doc` | listener `docstatus=2` | cancel WO → không crash, không tạo log thừa | Error guessing |
| TC-NTF-14 | `test_notify_incident_created_dispatches_to_assignee` | `notify_incident_created` (E3) | Incident có `assigned_to` set → Notification Log cho assignee, type=Alert, document_type=Incident Report, subject chứa severity | EP |
| TC-NTF-15 | `test_notify_incident_created_fallback_reported_by` | `notify_incident_created` (E3) | Incident KHÔNG có `assigned_to` → fallback `reported_by` nhận thông báo | Decision Table |
| TC-NTF-16 | `test_notify_incident_created_skips_self` | `notify_incident_created` (E3) | actor == **assigned_to** (cross-assign tự gán) → KHÔNG dispatch (self-notify noise vẫn bị chặn). KHÁC self-confirm (xem TC-NTF-24). | EP |
| TC-NTF-17 | `test_notify_calibration_due_dispatches_on_status_change` | `notify_calibration_due` (E4) | old=ON_SCHEDULE, new=DUE_SOON → dispatch cho `responsible_technician`; old=DUE_SOON, new=OVERDUE → dispatch lại (escalation) | Decision Table |
| TC-NTF-18 | `test_notify_calibration_due_noop_when_status_unchanged` | `notify_calibration_due` (E4) anti-spam | old=DUE_SOON, new=DUE_SOON → KHÔNG dispatch; new=ON_SCHEDULE → KHÔNG dispatch | State Transition |
| TC-NTF-19 | `test_notify_calibration_due_fallback_custodian` | `notify_calibration_due` (E4) | asset KHÔNG có `responsible_technician` → fallback `custodian` | Decision Table |
| TC-NTF-20 | `test_render_email_contains_subject_and_deeplink` | `_render_email` (vòng 4) | doc có doctype+name → HTML chứa `subject`, chứa `body_html` nguyên văn, chứa URL `get_url_to_form` (nút "Mở phiếu"), chứa footer branding "AssetCore" | EP |
| TC-NTF-21 | `test_render_email_omits_deeplink_when_no_doc_ref` | `_render_email` (vòng 4) | doc thiếu doctype/name → HTML vẫn dựng (subject+body+footer), KHÔNG có nút deep-link, không raise | Error guessing |
| TC-NTF-22 | `test_dispatch_sends_html_email_with_deeplink` | `_dispatch`+`_render_email` (vòng 4) | user bật email → `_safe_sendmail` nhận `message` là HTML (chứa subject + deep-link), bell `email_content` vẫn là `message` ngắn | Decision Table |
| TC-NTF-23 | `test_render_email_reused_across_events` | `_render_email` (vòng 4) | gọi với subject/body của E1..E4 (4 doctype khác nhau) → mỗi HTML chứa đúng subject + body tương ứng, cùng khung header/footer (1 template tái dùng) | EP |
| TC-NTF-24 | `test_notify_incident_created_self_confirm` | `notify_incident_created` (E3, self-confirm vòng 9) | `assigned_to=None`, `reported_by == actor` → tạo **đúng 1** Notification Log cho actor; `subject` chứa "Đã ghi nhận". (Trước vòng 9: trả rỗng = bug.) Spec 04 §III.1b-2b, FR-00-NTF-07. | Decision Table |
| TC-NTF-25 | `test_resolve_recipients_include_self_flag` | `resolve_recipients` (self-confirm vòng 9) | `include_self=True` → list chứa actor; `include_self=False` (mặc định) → loại actor. Bảo vệ hành vi mặc định KHÔNG đổi (mọi caller cũ an toàn). | Decision Table |

### III.2b-1. Vòng 4 — HTML email template (TDD)

> Bổ sung TC-NTF-20..23 cho builder `_render_email` (spec §III.1b-3, file `04_Backend_Design.md`). Viết TRƯỚC implement. Email plain-text fallback do Frappe core sinh tự động (`set_html_as_text`) → không test thủ công phần text, chỉ assert `message` truyền vào sendmail là HTML. Regression: TC-NTF-01..19 (19 test) phải vẫn xanh — builder KHÔNG đổi recipient/guard logic.

### III.2b-2. Vòng 9 — Self-confirm cho người tự báo (TDD)

> Bổ sung TC-NTF-24/25 (spec §III.1b-2b, FR-00-NTF-07). Viết TRƯỚC implement. Thay đổi semantics recipient cho **đúng 1 nhánh** (Incident `reported_by`-fallback khi chưa assign) qua param opt-in `resolve_recipients(..., include_self=True)`. **Regression bắt buộc:** TC-NTF-15 (cross-report) và TC-NTF-16 (self-assign block) phải VẪN xanh — chứng minh self-confirm KHÔNG phá hành vi cũ. Default `include_self=False` ⇒ mọi caller hiện hữu không đổi.

### III.2c. RC-03 — Kế thừa luật khấu hao Category→Asset (TDD, viết TRƯỚC implement)

> File: `assetcore/tests/test_depreciation.py` (mở rộng) + `assetcore/tests/test_imm00.py` (compute_all). Chạy: `bench --site miyano run-tests --module assetcore.tests.test_depreciation` / `...test_imm00`. **RED-first BẮT BUỘC:** chứng minh từng TC FAIL trước khi implement SoT (vd before_insert chưa wire → months vẫn None → assert fail). Setup: tạo Category có luật (`total_depreciation_months>0`, `default_residual_value_pct` ví dụ 5%) + Category trống luật (`total_depreciation_months=0`). Teardown: dùng `_asset_cleanup` shared (memory test_session_20260529_wave1) để purge asset tạo trong test.

| TC ID | Test | Cover (FR/BR) | Assert | Kỹ thuật |
|---|---|---|---|---|
| TC-DEP-30 | `test_before_insert_inherits_months_and_residual_from_category` | FR-00-48, BR-00-18 | Tạo `AC Asset` gross>0 + asset_category CÓ luật, KHÔNG truyền months/residual → `.insert()` → `total_depreciation_months == Category.total_depreciation_months` và `residual_value == round(gross*pct/100,2)`. **Verify LIVE** `frappe.get_doc(...).insert()`. | EP |
| TC-DEP-31 | `test_regenerate_no_422_after_inherit` | FR-00-51 | Asset ở TC-DEP-30 → `regenerate_depreciation_schedule(asset)` KHÔNG trả 422 "Thiếu: Số tháng khấu hao"; `periods>0`. (Lỗi user báo.) | EP (positive path) |
| TC-DEP-32 | `test_category_without_rule_no_fabrication` | FR-00-50, BR-00-20 | Category `total_depreciation_months=0` → before_insert KHÔNG bịa số, KHÔNG raise; asset lưu với `months=0`; `regenerate` vẫn trả **422 đúng** (Category cũng thiếu). | EP (negative — không che lỗi master-data) |
| TC-DEP-33 | `test_no_clobber_user_months` | FR-00-49, BR-00-19 | Asset truyền sẵn `total_depreciation_months=48` (khác Category) → before_insert GIỮ 48, không ghi đè bằng Category. | Decision Table |
| TC-DEP-34 | `test_no_clobber_user_residual` | FR-00-49, BR-00-19 | Asset truyền sẵn `residual_value` khác 0 → before_insert GIỮ nguyên residual user. months vẫn được inherit nếu trống (per-field độc lập). | Decision Table |
| TC-DEP-35 | `test_inherit_idempotent` | BR-00-18 | Gọi `inherit_depreciation_rules_from_category(doc)` lần 2 trên asset đã đủ luật → trả 0, không đổi field. | EP |
| TC-DEP-36 | `test_residual_formula_matches_imm04_and_bulk` | BR-00-18 grep-guard | Cùng gross+pct → residual của SoT == residual của `create_ac_asset` == `bulk_regenerate_by_category` (sau khi đồng bộ `round(...,2)`). | EP (formula parity) |
| TC-DEP-40 | `test_compute_all_backfills_then_generates` | FR-00-52, BR-00-21 | Asset gross>0 + Category có luật nhưng asset thiếu method/months → `compute_all_depreciation()` → `inherited≥1`, `generated≥1`, asset có schedule (KHÔNG còn skip). | Integration |
| TC-DEP-41 | `test_compute_all_preserves_executed_history` | BR-00-21 | Asset có ≥1 kỳ Executed → KHÔNG backfill/regenerate; đếm `skipped_has_history`; `accumulated` không đổi. | State Transition |
| TC-DEP-42 | `test_compute_all_idempotent` | FR-00-52 | Chạy 2 lần liên tiếp → lần 2 `inherited==0`, không tạo trùng schedule, không đổi accumulated asset Executed. | State |
| TC-DEP-43 | `test_compute_all_payload_shape` | FR-00-52 | Response có đủ 6 key `{inherited, generated, executed_rows, updated_assets, skipped_has_history, skipped_no_rule}`; `skipped_no_rule` đếm asset Category cũng thiếu luật. | EP (contract) |
| TC-DEP-44 | `test_compute_all_rbac_non_admin_403` | FR-00-52, RBAC | Gọi bằng user non-admin → 403, KHÔNG leak data. | Security |
| TC-DEP-45 | `test_compute_all_emits_audit_event` | BR-00-21 | Sau backfill ≥1 asset → có lifecycle/audit event ("Depreciation Backfill" hoặc per-asset) — audit trail (CLAUDE.md §5). | Integration |

#### III.2c-1. RC-04 — Per-asset self-heal tại `regenerate_depreciation_schedule` (TDD, Round-2)

> File: `assetcore/tests/test_depreciation.py` (mở rộng — block RC-04) + `assetcore/tests/test_imm00.py` (depreciation block, regenerate path). **RED-first BẮT BUỘC:** mô phỏng asset CŨ — tạo asset rồi RESET `total_depreciation_months=0` qua `frappe.db.set_value` (bypass `before_insert` để giả lập asset tạo trước round-1), chứng minh `regenerate_depreciation_schedule` trả 422 TRƯỚC khi wire self-heal, GREEN sau. Setup tái dùng Category-có-luật / Category-trống-luật của §III.2c. Teardown: `_asset_cleanup` shared.

| TC ID | Test | Cover (FR/BR) | Assert | Kỹ thuật |
|---|---|---|---|---|
| TC-DEP-50 | `test_regenerate_selfheals_old_asset_no_422` | FR-00-53, BR-00-22 | Asset gross>0 + Category CÓ luật, `db.set_value(months=0)` (giả asset cũ) → `regenerate_depreciation_schedule(asset)` → **HTTP 200**, `periods>0`; KHÔNG còn 422 "Thiếu: Số tháng khấu hao". (Lỗi user goal C.) | EP (positive — chính lỗi user) |
| TC-DEP-51 | `test_regenerate_selfheal_single_sot_call` | FR-00-53, BR-00-22 grep-guard | `grep -c` trong `api/imm00.py`: 0 occurrence gán `total_depreciation_months`/`residual_value` từ Category ngoài lời gọi `inherit_depreciation_rules_from_category`. Self-heal CHỈ qua SoT. | Static / grep-guard |
| TC-DEP-52 | `test_regenerate_precheck_runs_after_inherit` | FR-00-53, BR-00-22 | Category cũng thiếu luật (`months=0`) → regenerate inherit no-op → **VẪN 422** message liệt kê đúng field thiếu (months). KHÔNG che lỗi master-data. | EP (negative) |
| TC-DEP-53 | `test_regenerate_no_category_still_422` | FR-00-54, BR-00-20/22 | Asset gross>0 KHÔNG có `asset_category` → inherit no-op → **422** đúng field thiếu. | EP (negative) |
| TC-DEP-54 | `test_regenerate_selfheal_no_clobber_user` | FR-00-54, BR-00-19 | Asset đã có `total_depreciation_months=48` (≠ Category) hoặc `residual_value` user nhập → regenerate GIỮ NGUYÊN giá trị user, sinh lịch theo giá trị hiện hữu (inherit no-op trên field đã có). | Decision Table |
| TC-DEP-55 | `test_regenerate_selfheal_preserves_executed_history` | FR-00-54, BR-00-21 | Asset có ≥1 kỳ Executed → self-heal KHÔNG override months/residual đã chạy; kỳ Executed bất biến (chỉ Pending bị xoá-sinh-lại khi force=1). | State Transition |
| TC-DEP-56 | `test_regenerate_idempotent_no_garbage_event` | FR-00-55, BR-00-22 | Gọi regenerate 2 lần liên tiếp cùng asset → cùng số `periods`; lần 2 `did_inherit=False` → KHÔNG sinh ALE/Audit event mới (đếm event TRƯỚC/SAU lần 2 bằng nhau). | State / Idempotent |
| TC-DEP-57 | `test_regenerate_selfheal_emits_audit` | FR-00-55, BR-00-22 | Self-heal có kế thừa thật (`did_inherit=True`) → sinh **1** Asset Lifecycle Event `event_type='depreciation_rules_inherited'` + **1** IMM Audit Trail `event_type='System'` cho asset đó. | Integration (audit trail) |

**DoD:** BE 983-suite + `test_depreciation` (31 + RC-04 mới = ≥38) + `test_imm00` (depreciation block) GREEN; `before_insert` path (RC-03 round-1) KHÔNG đổi hành vi (regression TC-DEP-30..45 vẫn GREEN); FE vue-tsc 0 + vitest GREEN. Grep-guard SoT: ngoài `inherit_depreciation_rules_from_category` + `create_ac_asset` + `bulk_regenerate_by_category`, không nhánh nào copy months/residual từ Category; trong `api/imm00.py` 0 occurrence copy ngoài lời gọi SoT.

#### III.2c-2. RC-05 — `bulk_regenerate_by_category` hợp nhất về SoT (TDD, Round-4)

> File: `assetcore/tests/test_depreciation.py` (mở rộng — block RC-05). Chạy: `bench --site miyano run-tests --module assetcore.tests.test_depreciation` / `...test_imm00`. **RED-first BẮT BUỘC cho 2 TC trọng yếu:** (a) `test_bulk_no_clobber` — chứng minh code inline cũ **clobber** field user (asset months=24, Category=120 → bulk cũ ghi đè thành 120 ⇒ assert `==24` FAIL trên code cũ, PASS sau khi route qua SoT); (b) `test_bulk_n1_query_count` — đếm số query executed-history (`frappe.db.count`/`get_all` filter status='Executed') ⇒ trên code inline cũ = N (per-asset) ⇒ assert `==1` FAIL, PASS sau khi prefetch GROUP BY. Setup tái dùng Category-có-luật / Category-trống-luật của §III.2c. Teardown: `_asset_cleanup` shared.

| TC ID | Method | Maps | Mô tả | Kỹ thuật |
|---|---|---|---|---|
| TC-DEP-60 | `test_bulk_no_clobber_user_fields` | FR-00-56, BR-00-19/23 | 1 asset `total_depreciation_months=24` + `residual_value≠0` + `depreciation_method`/`depreciation_frequency` user-nhập, Category months=120 → sau `bulk_regenerate_by_category` 4 field user **GIỮ NGUYÊN** (months==24…). **RED-proven** trên code inline cũ. | Decision Table (RED-first) |
| TC-DEP-61 | `test_bulk_n1_single_executed_query` | FR-00-57, BR-00-23 | Mock/đếm: số query kiểm executed-history == **1** bất kể N asset (prefetch `executed_parents` GROUP BY) — KHÔNG `frappe.db.count` per-asset. **RED-proven** trên code `db.count`-in-loop cũ. | Performance (query-count, RED-first) |
| TC-DEP-62 | `test_bulk_no_inline_copy_grep_guard` | FR-00-56, BR-00-23 grep-guard | `grep` trong thân `bulk_regenerate_by_category` (`services/depreciation.py`): **0** occurrence gán `asset_doc.(total_depreciation_months\|residual_value\|depreciation_method\|depreciation_frequency)=…` ngoài lời gọi `inherit_depreciation_rules_from_category`. | Static / grep-guard |
| TC-DEP-63 | `test_bulk_payload_shape_7key` | FR-00-57 | Response có đủ 7 key `{category, total_assets, inherited, regenerated, skipped_has_history, skipped_no_rule, errors}`; `inherited` + `skipped_no_rule` xuất hiện đúng. | EP (contract) |
| TC-DEP-64 | `test_bulk_skipped_no_rule_when_category_unconfigured` | FR-00-57, BR-00-20 | Asset thuộc Category `total_depreciation_months=0` (hoặc asset `gross<=0`) → `skipped_no_rule≥1`, KHÔNG bịa số, KHÔNG raise. | EP (negative — không che master-data) |
| TC-DEP-65 | `test_bulk_preserves_executed_history` | FR-00-57, BR-00-23 | Asset có ≥1 kỳ Executed → `skipped_has_history++` qua prefetch; `accumulated_depreciation`/`current_book_value` **bất biến** sau bulk. | State Transition |
| TC-DEP-66 | `test_bulk_idempotent_second_run` | FR-00-57, BR-00-23 | Bulk lần 2 trên cùng dataset → `inherited==0`; payload ổn định; `accumulated` asset Executed không đổi. | State / Idempotent |
| TC-DEP-67 | `test_bulk_emits_audit` | FR-00-58, BR-00-23 | Bulk có inherit ≥1 asset → per-asset ALE `depreciation_rules_inherited` + **1** IMM Audit Trail `System` TỔNG; lỗi audit (mock raise) KHÔNG chặn payload (best-effort). | Integration (audit trail) |

**FE — `ReferenceDataView.applyToExistingAssets` (RC-05):** vitest `referenceDataApplyDepreciation.test.ts` (mới):
- `TC-FE-RD-01` — click nút "Áp dụng khấu hao theo từng Danh mục" → **KHÔNG** gọi `window.confirm`; mở BaseModal; API **chưa** gọi.
- `TC-FE-RD-02` — bấm "Xác nhận" trong modal → `bulkRegenerateScheduleByCategory` gọi đúng 1 lần.
- `TC-FE-RD-03` — mock payload 7-key → toast/modal render đủ `inherited + regenerated + skipped_has_history + skipped_no_rule + errors`; không crash khi key=0; KHÔNG leak raw method/token.

**DoD (RC-05):** `test_depreciation` block RC-05 (TC-DEP-60..67) + regression RC-03/RC-04 (TC-DEP-30..57) GREEN; `test_imm00` depreciation block GREEN; FE vue-tsc 0 + vitest (DepreciationView + ReferenceDataView) GREEN. **Grep-guard cập nhật:** ngoài `inherit_depreciation_rules_from_category` + **`create_ac_asset` (insert-path)**, KHÔNG nhánh nào copy months/residual từ Category — `bulk_regenerate_by_category` KHÔNG còn inline copy. RED-proven cho TC-DEP-60 (no-clobber) + TC-DEP-61 (N+1 query-count) TRƯỚC GREEN.

#### III.2c-3. RC-06 — SoT `effective_book_value` (fix falsy-zero, BR-05-13, TDD viết TRƯỚC)

> File: `assetcore/tests/test_depreciation.py` (SoT unit) + `assetcore/tests/test_imm00.py` (stats/list integration). Chạy: `bench --site miyano run-tests --module assetcore.tests.test_depreciation` / `...test_imm00`. **RED-first BẮT BUỘC:** revert SoT về idiom `current_book_value or gross` → TC-DEP-70 (fully_depreciated-count) + TC-DEP-71 (total_book no-phantom) **FAIL**; restore → GREEN. Setup: asset `gross>0, residual=0, configured`, `frappe.db.set_value('AC Asset', name, 'current_book_value', 0.0)` (book đã KH hết về 0 hợp lệ). Teardown: `_asset_cleanup` shared.

| TC ID | Method | Maps | Mô tả | Kỹ thuật |
|---|---|---|---|---|
| TC-DEP-68 | `test_effective_book_value_none_returns_gross` | BR-05-13, INV-DEP-8 | `effective_book_value({gross:100, current_book_value:None})` == `100.0` (asset CHƯA chạy KH → fallback gross — no regression). | EP (boundary None) |
| TC-DEP-69 | `test_effective_book_value_zero_returns_zero` | BR-05-13, INV-DEP-8 | `effective_book_value({gross:100, current_book_value:0.0})` == `0.0` (đã KH hết → giá trị thật, KHÔNG phantom gross). **Đây là lỗi gốc.** | EP (boundary 0.0 — RED-first) |
| TC-DEP-70 | `test_stats_counts_fully_depreciated_book_zero` | BR-05-13, INV-DEP-6 | asset `gross>0, residual=0, configured, current_book_value=0.0` → `get_depreciation_stats().fully_depreciated` đếm asset này (trước: bị loại vì book thổi về gross). **RED-proven** revert → FAIL. | Decision Table (RED-first) |
| TC-DEP-71 | `test_stats_total_book_no_phantom_gross` | BR-05-13, INV-DEP-7 | cùng asset book=0.0 → `get_depreciation_stats().total_book_value` & `by_category[cat].book_value` cộng `0.0` (KHÔNG `gross`). **RED-proven** revert → FAIL. | Decision Table (RED-first) |
| TC-DEP-72 | `test_compute_depreciation_returns_zero_book` | BR-05-13 | asset KH hết → `compute_depreciation(name).book_value == 0.0` (không phantom gross trong payload single-asset). | EP (payload) |
| TC-DEP-73 | `test_enrich_row_book_zero_for_depleted` | BR-05-13 | `_depr_enrich_row` trên asset book=0.0 → `row['current_book_value'] == 0.0`; drill hiện 0đ. | EP (enrich) |
| TC-DEP-74 | `test_count_equals_drill_with_book_zero` | BR-05-13, INV-DEP-5 | dataset có ≥1 asset book=0.0 → `get_depreciation_stats().fully_depreciated == de-dup len(list_assets_depreciation(depreciation_filter='fully_depreciated') mọi trang)` (count==drill, cùng SoT mới). | Integration (invariant) |
| TC-DEP-75 | `test_no_falsy_zero_idiom_grep_guard` | BR-05-13 grep-guard | `grep -c 'current_book_value") or gross' assetcore/api/imm00.py` → **0** occurrence. Mọi suy book ngoài đường ghi DB qua `effective_book_value`. | Static / grep-guard |
| TC-DEP-76 | `test_book_none_no_regression` | BR-05-13, INV-DEP-8 | asset CHƯA chạy KH (`current_book_value IS NULL`) → stats/list/payload book == `gross` y như trước (full-suite no-regression cho asset chưa KH). | Regression |

**FE — `DepreciationView.vue` (RC-06): zero-change logic.** vitest `depreciationBookValue.test.ts` (mới — confirm render, KHÔNG sửa component):
- `TC-FE-DV-01` — mock `list_assets_depreciation` trả asset `current_book_value: 0` → cột "Giá trị còn lại" render `0đ` (KHÔNG gross).
- `TC-FE-DV-02` — mock `get_depreciation_stats` trả `total_book_value` đã trừ phantom → KPI hiển thị verbatim số BE.

**DoD (RC-06):** `test_depreciation` (TC-DEP-68..76) + `test_imm00` stats/list GREEN; RED-proven TC-DEP-69/70/71 TRƯỚC GREEN; full BE suite no-regression (asset book>0 / book=None giữ y số). FE vue-tsc 0 + vitest GREEN **không sửa logic** (zero-change). Grep-guard TC-DEP-75 = 0 occurrence.

#### III.2c-4. RC-07 — Thanh lý hủy kỳ Pending khấu hao (BR-00-24, TDD viết TRƯỚC)

> File: `assetcore/tests/test_imm00.py` (block decommission-depreciation) — nơi đặt vì feature sống ở `services/imm00.py::transition_asset_status`. Chạy: `bench --site miyano run-tests --module assetcore.tests.test_imm00`. **RED-first BẮT BUỘC:** TC-DEP-80 (`pending_periods==0` sau decommission) **FAIL** trên code hiện tại (`_suspend_all_schedules` không đụng depreciation rows) → GREEN sau khi wire `_cancel_pending_depreciation_on_decommission`. **Setup chuẩn:** tạo asset `gross>0` + Category-có-luật, `generate_schedule(force=True)` → có ≥3 kỳ Pending; `run_due_depreciation(as_of=<quá khứ>)` execute ≥1 kỳ rồi giữ ≥1 kỳ Pending (asset thanh lý **mid-life**). Đưa asset về `Active` trước (NEG-09 chặn decommission từ Under-* — phải qua Active). Teardown: `_asset_cleanup` shared (purge asset + child rows + ALE + audit).

| TC ID | Method | Maps | Mô tả | Kỹ thuật |
|---|---|---|---|---|
| TC-DEP-80 | `test_decommission_cancels_all_pending` | FR-00-59, BR-00-24 | Asset mid-life (≥1 Executed + ≥2 Pending) → `transition_asset_status(asset,'Decommissioned')` → MỌI dòng `status='Pending'` thành `'Cancelled'`; `get_depreciation_schedule(asset).summary.pending_periods == 0`. **RED-proven** trên code hiện tại (FAIL: pending>0). | EP (positive — chính lỗi user, RED-first) |
| TC-DEP-81 | `test_decommission_preserves_executed_rows` | FR-00-59, BR-00-24 | Dòng `status='Executed'` BẤT BIẾN sau decommission (`depreciation_amount/accumulated_amount/remaining_value/executed_on` y nguyên); `summary.executed_periods` không đổi; `asset.accumulated_depreciation` + `current_book_value` không đổi. | State Transition (invariant) |
| TC-DEP-82 | `test_decommission_idempotent_no_double_cancel` | FR-00-60, BR-00-24 | Gọi `_cancel_pending_depreciation_on_decommission(asset)` lần 2 (0 Pending còn) → trả `0`; KHÔNG đổi DB; KHÔNG sinh ALE/Audit mới (đếm event TRƯỚC/SAU bằng nhau). | State / Idempotent |
| TC-DEP-83 | `test_cron_no_execute_after_decommission` | FR-00-61, BR-00-24 | Sau decommission, `run_due_depreciation(as_of=<tương lai xa>, asset=name)` → `executed_rows==0` cho asset đó (filter lifecycle + rows đã Cancelled). KHÔNG phantom overdue. | Integration (cron) |
| TC-DEP-84 | `test_decommission_emits_one_depreciation_stopped` | FR-00-62, BR-00-24 | Hủy ≥1 kỳ → ĐÚNG **1** Asset Lifecycle Event `event_type='depreciation_stopped'` (asset, root_doctype='AC Asset', notes nêu số kỳ + book value) + **1** IMM Audit Trail `event_type='System'`. SONG SONG với event `decommissioned` (state-change) — đếm cả 2 đều tồn tại. | Integration (audit trail) |
| TC-DEP-85 | `test_decommission_no_pending_no_event` | FR-00-60/62, BR-00-24 | Asset KH hết (0 Pending) HOẶC asset không có schedule → decommission → 0 dòng Cancelled, **KHÔNG** sinh event `depreciation_stopped`/audit thừa (no garbage). | EP (negative — no garbage) |
| TC-DEP-86 | `test_decommission_audit_failure_does_not_break_transition` | FR-00-62, BR-00-24 | Mock `create_lifecycle_event` raise → transition VẪN hoàn tất: `lifecycle_status=='Decommissioned'` ∧ mọi Pending đã `Cancelled` (rows commit TRƯỚC audit; audit best-effort try/except). | Integration (best-effort / fault injection) |
| TC-DEP-87 | `test_decommission_event_type_in_select_options` | BR-00-24 schema-delta | DocType `Asset Lifecycle Event` field `event_type` Select options CHỨA `depreciation_stopped` (`frappe.get_meta(...).get_field('event_type').options` split bao gồm value) → tạo ALE không lỗi validate Select. | Static / schema |

**DoD (RC-07):** `test_imm00` block RC-07 (TC-DEP-80..87) GREEN; RED-proven TC-DEP-80 TRƯỚC GREEN; regression toàn `test_depreciation` (TC-DEP-30..76) + `test_imm00` state-transition (SEQ-transition, BR-00-04/05) **không đổi hành vi**; `bench migrate` áp option Select `depreciation_stopped` (verify `bench --site miyano console` get_meta). FE zero-change (transition_status response shape không đổi) — chỉ cần `DepreciationView`/timeline render dòng `Cancelled` + event `depreciation_stopped` không crash (TC-FE bổ sung nếu QA yêu cầu, không bắt buộc cho vòng này).

#### III.2c-5. RC-08 — Tạm ngừng sử dụng: PAUSE + DỜI lịch khấu hao (BR-00-25, TDD viết TRƯỚC)

> File: `assetcore/tests/test_imm00.py` (block oos-depreciation) — feature sống ở `services/imm00.py::transition_asset_status` (2 nhánh mới `Out of Service` + `Active←Out of Service`). Chạy: `bench --site miyano run-tests --module assetcore.tests.test_imm00`. **RED-first BẮT BUỘC:** TC-DEP-92 (`delta_accumulated==0` cho kỳ idle sau restore + `run_due_depreciation(today)`) **FAIL** trên code hiện tại (chưa dời lịch → phantom catch-up trích bù toàn bộ N kỳ idle 1 lần) → GREEN sau khi wire `_reschedule_pending_depreciation_on_restore`. **Setup chuẩn:** tạo asset `gross>0` + Category-có-luật, `generate_schedule(force=True)` → ≥4 kỳ Pending với `scheduled_date` rải theo tháng; `run_due_depreciation(as_of=<quá khứ>)` execute 1 kỳ để có baseline accumulated; đưa asset về `Active`. **Mô phỏng OoS-window:** `transition_asset_status(asset,'Out of Service')` (mở downtime log → `start_time`=mốc OoS); để N kỳ Pending có `scheduled_date < restore_date` (giả lập ngừng dài ngày — set `start_time` downtime log về quá khứ hoặc chèn ALE `out_of_service` quá khứ để `oos_days` đủ lớn). Teardown: `_asset_cleanup` shared (purge asset + child rows + downtime log + ALE + audit).

| TC ID | Tên test | FR/BR | Kịch bản | Kỹ thuật |
|---|---|---|---|---|
| TC-DEP-90 | `test_oos_executor_does_not_run_during_window` | FR-00-63, BR-00-25 | Asset `Out of Service` có kỳ Pending đến hạn → `run_due_depreciation(today)` 1+ lần → `executed_rows==0` cho asset đó; `accumulated_depreciation`/`current_book_value` BẤT BIẾN trong toàn window OoS. | Integration (cron) — PAUSE |
| TC-DEP-91 | `test_oos_pause_emits_lifecycle_note` | FR-00-64, BR-00-25 | Vào `Out of Service` với ≥1 kỳ Pending → có ≥1 ALE `event_type='out_of_service'` note chứa `'depreciation paused'`. 0 kỳ Pending → KHÔNG sinh note pause thừa (no garbage). | Integration (audit) |
| TC-DEP-92 | `test_restore_no_phantom_catch_up` | FR-00-65, BR-00-25 (**BUG CHÍNH, RED-first**) | Asset OoS có N kỳ Pending quá hạn → `Out of Service → Active` → `run_due_depreciation(today)` → `delta_accumulated == 0` cho các kỳ rơi trong khoảng OoS; `current_book_value` KHÔNG tụt đột ngột. **RED-proven** trên code hiện tại (FAIL: trích bù N kỳ 1 lần, book tụt). | EP (positive — chính lỗi, RED-first) |
| TC-DEP-93 | `test_restore_reschedules_pending_by_oos_days` | FR-00-66, BR-00-25 | `Out of Service → Active` → mỗi kỳ `status='Pending'` có `scheduled_date_mới == scheduled_date_cũ + oos_days`; `count(Pending) trước==sau`; `sum(depreciation_amount Pending) trước==sau`; `period_number`/`depreciation_amount`/`accumulated_amount`/`remaining_value` GIỮ NGUYÊN. | State Transition (invariant) |
| TC-DEP-94 | `test_restore_preserves_executed_and_cancelled` | FR-00-66, BR-00-25 | Kỳ `Executed` + kỳ `Cancelled` BẤT BIẾN sau restore (`scheduled_date`/`amount`/`accumulated`/`remaining`/`executed_on` y nguyên — chỉ dời `Pending`). | State (invariant) |
| TC-DEP-95 | `test_restore_oos_start_from_downtime_log` | FR-00-67, BR-00-25 | `oos_start_date` lấy từ `start_time` Downtime Log OoS gần nhất (priority-1) — chứng minh dùng được DÙ log đã bị `_sync_downtime_log` đóng (`is_open=0`) trước reschedule (ordering); `oos_days` tính đúng từ mốc đó → dời đúng số ngày. | Integration (SoT mốc + ordering) |
| TC-DEP-96 | `test_restore_oos_start_fallback_to_ale` | FR-00-67, BR-00-25 | Xóa/đóng Downtime Log → `_resolve_oos_start_date` fallback `creation` ALE `out_of_service` gần nhất; vẫn dời đúng. | Integration (fallback) |
| TC-DEP-97 | `test_restore_no_oos_marker_is_noop_no_raise` | FR-00-67, BR-00-25 | Không Downtime Log mở + không ALE `out_of_service` (mốc không xác định) → `_reschedule_…` trả `{rescheduled:0, oos_days:0}`, KHÔNG raise; `scheduled_date` Pending KHÔNG đổi. `oos_days<=0` (cùng ngày/đồng hồ lệch) → cũng no-op. | EP (negative — fallback an toàn) |
| TC-DEP-98 | `test_restore_idempotent_no_double_shift` | FR-00-68, BR-00-25 | Sau 1 chu kỳ OoS→Active, gọi lại `transition_asset_status(asset,'Active')` (same-status no-op qua guard `prev==to → return`) → `scheduled_date` Pending KHÔNG dời lần 2; 0 ALE/audit thừa. | State / Idempotent |
| TC-DEP-99 | `test_restore_emits_one_restored_event_and_audit` | FR-00-68/69, BR-00-25/27 (**SỬA RC-09, Vòng 14**) | Dời ≥1 kỳ → ĐÚNG **1** ALE `event_type='restored'` (emit bởi `transition_asset_status`, KHÔNG còn từ helper) + **0** ALE `activated` + ≥1 IMM Audit Trail `event_type='State Change'` (entry helper note **số kỳ dời** + **oos_days**). **KHÔNG còn double-emit** (trước fix có-Pending→2 event `activated`+`restored`). Mock audit raise (best-effort) → transition VẪN hoàn tất (`lifecycle_status=='Active'` ∧ rows đã dời). | Integration (audit + best-effort/fault injection) |
| TC-DEP-9A | `test_restore_no_pending_no_config_noop` | FR-00-68, BR-00-25 | Asset không cấu hình khấu hao / 0 kỳ Pending → `Out of Service → Active` → no-op reschedule (`rescheduled==0`); KHÔNG audit rác. **RC-09:** vẫn ĐÚNG 1 ALE `restored` (do transition, KHÔNG phụ thuộc Pending) + 0 `activated` — **consistency** với nhánh có-Pending. | EP (negative — no garbage + consistency) |
| TC-DEP-9B | `test_restore_only_from_oos_not_other_active` | FR-00-66, BR-00-25 | `Active` từ `Under Repair`/`Calibrating`/`Under Maintenance`/`Commissioned` (KHÔNG phải từ Out of Service) → KHÔNG dời lịch (nhánh reschedule chỉ chạy khi `prev_status=='Out of Service'`); `scheduled_date` Pending KHÔNG đổi. **RC-09:** các đường này giữ nhãn ALE `activated` (KHÔNG `restored`). | EP (branch isolation) |

**RC-09 (Vòng 14) — INV-ALE-RESTORE: nhãn sự kiện khôi phục `restored` ĐÚNG 1 (BR-00-27 / FR-00-69, TDD viết TRƯỚC):**

> File: `assetcore/tests/test_imm00.py` (block ale-restore-label) — feature ở `services/imm00.py::_lifecycle_event_for(to, from)` + `transition_asset_status` + `_reschedule_pending_depreciation_on_restore` (bỏ emit ALE) + controller `ac_asset.py::on_update`. **RED-first BẮT BUỘC:** TC-ALE-RESTORE-01 (có-Pending → đếm `activated`==0 ∧ `restored`==1) **FAIL** trên code hiện tại (double-emit: `activated`+`restored`) → GREEN sau fix. Helper count ALE theo `event_type` + `to_status='Active'`. **REGRESSION đặc biệt cần verify:** `test_imm09:839` (`activated` từ Under Repair→Active) + `test_imm11:1317`/branch-A (`activated` từ Calibrating→Active) PHẢI vẫn pass — fix CHỈ đổi nhãn đường `from='Out of Service'`.

| TC ID | Tên test | FR/BR | Kịch bản | Kỹ thuật |
|---|---|---|---|---|
| TC-ALE-RESTORE-01 | `test_restore_oos_to_active_with_pending_one_restored` | FR-00-69, BR-00-27 (**BUG CHÍNH, RED-first**) | Asset OoS có ≥1 kỳ Pending để dời → `Out of Service → Active` → ĐÚNG **1** ALE `event_type='restored'` (to=Active) ∧ **0** ALE `activated`. **RED-proven** trên code hiện tại (FAIL: có cả `activated`+`restored` = double-emit). | EP (positive — chính lỗi, RED-first) |
| TC-ALE-RESTORE-02 | `test_restore_oos_to_active_no_pending_one_restored` | FR-00-69, BR-00-27 | Asset OoS **0 kỳ Pending** (chưa cấu hình KH / đã hết) → `Out of Service → Active` → vẫn ĐÚNG **1** ALE `restored` ∧ **0** `activated`. **Consistency** với TC-01 (trước fix: nhánh này chỉ có 1 `activated`). | EP (positive — consistency có/không Pending) |
| TC-ALE-RESTORE-03 | `test_lifecycle_event_for_from_status_mapping` | FR-00-69, BR-00-27 | Unit thuần: `_lifecycle_event_for('Active','Out of Service')=='restored'`; `_lifecycle_event_for('Active', s)=='activated'` ∀ `s ∈ {'Under Repair','Calibrating','Under Maintenance','Commissioned'}`; các (from,to) khác giữ map cũ (`Commissioned→commissioned`, `Out of Service→out_of_service`, …). | Decision table (predicate thuần) |
| TC-ALE-RESTORE-04 | `test_reschedule_helper_no_longer_emits_ale` | FR-00-68/69, BR-00-27 | Gọi/chạy `_reschedule_pending_depreciation_on_restore` (qua transition) khi có ≥1 Pending → **KHÔNG** sinh ALE từ helper (chỉ `transition_asset_status` sinh `restored`); IMM Audit Trail `State Change` của helper VẪN có (note số kỳ dời + oos_days). | Integration (source isolation) |
| TC-ALE-RESTORE-05 | `test_workflow_action_oos_to_active_emits_restored` | FR-00-69, BR-00-27 (INV-ALE-RESTORE-4) | Đổi `Out of Service → Active` qua Frappe Workflow Action (path `ac_asset.on_update`, set flag `ac_asset_workflow_transition`) → emit `restored` (KHÔNG `activated`) — chứng minh fix tại `_lifecycle_event_for` áp dụng đồng nhất 2 call-site. | Integration (controller workflow path) |
| TC-ALE-RESTORE-06 | `test_audit_trail_invariant_on_restore` | BR-00-27 (audit bất biến) | 1 transition OoS→Active → IMM Audit Trail vẫn ≥1 entry `State Change`; `verify_audit_chain(asset).valid==True` (hash-chain KHÔNG vỡ); count IMM Audit Trail KHÔNG giảm so trước fix. | Integration (audit chain) |
| TC-ALE-RESTORE-07 | `test_activated_paths_unchanged_regression` | BR-00-27 (regression) | Under Repair→Active + Calibrating→Active → vẫn ĐÚNG nhãn `activated` (bảo toàn `test_imm09:839` + `test_imm11:1317`/branch-A); KHÔNG đường nào bị đổi thành `restored`. | EP (no-regression nhãn `activated`) |

**DoD (RC-08):** `test_imm00` block RC-08 (TC-DEP-90..9B) GREEN; RED-proven TC-DEP-92 (no-phantom-catch-up) TRƯỚC GREEN; regression toàn `test_depreciation` (TC-DEP-30..76) + RC-07 block (TC-DEP-80..87) + `test_imm00` state-transition (SEQ-transition, BR-00-04/05) + `test_imm04` **không đổi hành vi**; **KHÔNG schema-delta** (event_type `out_of_service`/`restored` đã có — KHÔNG `bench migrate` cho schema). FE zero-change (transition_status response shape không đổi) — `AssetDepreciationSchedule.vue` render `scheduled_date` đã-dời verbatim + KHÔNG leak raw status EN; `vue-tsc` 0; vitest depreciation suite GREEN no-regression.

## III.3. Integration — DocType lifecycle

File: `assetcore/tests/test_imm00.py`. Cover hook `validate / before_save / on_submit / before_submit`.

| Test class · method | Setup | Action | Assert | Kỹ thuật |
|---|---|---|---|---|
| `TestACAssetCategory::test_category_created/fields` | — | `insert()` | `name == category_name` | EP |
| `TestACDepartment::test_naming_series` | — | `insert()` | autoname `AC-DEPT-####` | EP |
| `TestACLocation::test_location_created/naming_series` | tree node | `insert()` | lft/rgt set | EP |
| `TestACSupplier::test_supplier_created/naming_series` | — | `insert()` | autoname | EP |
| `TestACAsset::test_asset_created_with_naming_series` | device_model | `insert()` | naming series + autofill | EP |
| `TestACAsset::test_decommission_suspends_pm_schedule` | Active asset, PM on | `transition_asset_status(...,Decommissioned)` | `is_pm_required==0`, `next_pm_date is None` (BR-00-04) | State Transition |
| `TestACAsset::test_cannot_operate_decommissioned_asset` | Decommissioned | `validate_asset_for_operations` | raise (BR-00-05) | EP |
| `TestIMMCAPARecord::test_create_capa/close_capa` | asset | `create_capa` / `close_capa` | status Open→Closed (BR-00-08) | Decision Table |
| `TestIncidentReport::test_create_incident/patient_impact_required_when_patient_affected` | — | `insert()` | patient_impact required | EP |
| `TestFKDeleteIntegrity::test_delete_model_blocked/allowed`, `test_delete_location_blocked/allowed` | asset refs model/location | `delete()` | block khi có dependent | Error guessing |

## III.4. Integration — Workflow transitions

File: `assetcore/tests/test_imm00.py` + `test_imm00_smoke.py`. Workflow `ac_asset_lifecycle_workflow.json` có **16 transition** (verified: `python3 -c "import json;print(len(json.load(open('assetcore/assetcore/workflow/ac_asset_lifecycle_workflow.json'))['transitions']))"`).

State Transition Testing — mỗi edge = 1 test pass + 1 test fail (wrong role).

| # | Action | From → To | Role required | Test pass | Test fail (wrong role) |
|---|---|---|---|---|---|
| 1 | Commission | Draft → Commissioned | PM User | ⬜ Planned | ⬜ Planned |
| 2 | Activate | Commissioned → Active | PM User | ✅ Live (`test_transition_status_commissioned_to_active`) | ⬜ Planned |
| 3 | Bắt đầu bảo trì | Active → Under Maintenance | PM User | ⬜ Planned | ⬜ Planned |
| 4 | Hoàn thành bảo trì | Under Maintenance → Active | PM User | ⬜ Planned | ⬜ Planned |
| 5 | Bắt đầu sửa chữa | Active → Under Repair | PM User | ✅ Live (`test_s07_active_to_under_repair...`) | ⬜ Planned |
| 6 | Bắt đầu sửa chữa | Under Maintenance → Under Repair | PM User | ⬜ Planned | ⬜ Planned |
| 7 | Bắt đầu hiệu chuẩn | Active → Calibrating | PM User | ⬜ Planned | ⬜ Planned |
| 8 | Đưa ra khỏi sử dụng | Active → Out of Service | PM Manager | 🟡 Planned (BR-00-25 PAUSE — TC-DEP-90/91, RC-08 Vòng 9) | ⬜ Planned |
| 9 | Hoàn thành sửa chữa | Under Repair → Active | PM User | ⬜ Planned | ⬜ Planned |
| 10 | Không thể sửa chữa | Under Repair → Out of Service | PM Manager | ⬜ Planned | ⬜ Planned |
| 11 | Hiệu chuẩn đạt | Calibrating → Active | PM User | ⬜ Planned | ⬜ Planned |
| 12 | Hiệu chuẩn không đạt | Calibrating → Out of Service | PM Manager | ⬜ Planned | ⬜ Planned |
| 13 | Khôi phục hoạt động | Out of Service → Active | PM Manager | 🟡 Planned (BR-00-25 RESCHEDULE — TC-DEP-92..9B, RC-08 Vòng 9; BR-00-27 nhãn `restored` ĐÚNG 1 — TC-ALE-RESTORE-01..07, RC-09 Vòng 14) | ⬜ Planned |
| 14 | Sửa chữa lại | Out of Service → Under Repair | PM User | ⬜ Planned | ⬜ Planned |
| 15 | Thanh lý | Out of Service → Decommissioned | System Manager | ✅ Live (`test_decommission_suspends_pm_schedule` via service) | ⬜ Planned |
| 16 | Thanh lý | Active → Decommissioned | System Manager | ⬜ Planned | ⬜ Planned |
| — | Invalid: Decommissioned → bất kỳ | (terminal) | — | ⬜ Planned (negative, UAT II.2) | — |

## III.5. Integration — Audit chain integrity

- (a) Sau N mutation, chain SHA-256 hợp lệ end-to-end → `TestIMMauditTrail::test_verify_chain_valid` ✅ Live; `TestS12_...test_s12_verify_audit_chain_valid` ✅ Live.
- (b) Audit entry immutable / không xóa được → `TestIMMauditTrail::test_audit_trail_cannot_be_deleted` ✅ Live; `test_audit_trail_created_on_transition` ✅ Live.
- (c) Tamper 1 record → `verify_chain` trả `verified=false` → ⬜ Planned (cần test sửa trực tiếp DB rồi verify).

→ 04 Backend §Audit Trail · `IMM Audit Trail` DocType (FR-00-19..22).

## III.6. API test

File: `assetcore/tests/test_imm00_list_assets.py` (live). Envelope `{success, data}`.

| Test · method | Endpoint | Verify | Kỹ thuật | Trạng thái |
|---|---|---|---|---|
| `TestListAssetsGmdnFilter::test_filter_by_gmdn_code_returns_only_matching_assets` | `api/imm00.list_assets` | chỉ trả asset khớp gmdn_code | EP | ✅ Live |
| `TestListAssetsGmdnFilter::test_search_by_gmdn_code_substring` | `api/imm00.list_assets` | search substring | EP | ✅ Live |
| `TestListAssetsGmdnFilter::test_gmdn_status_param_removed` | `api/imm00.list_assets` | param gmdn_status đã bỏ | Error guessing | ✅ Live |
| Happy `create_asset` + envelope `success=true` | `api/imm00.create_asset` | success, name set | Use Case | ⬜ Planned |
| Permission `list_assets` low-role | `api/imm00.list_assets` | scope filter (chỉ asset gán) | EP (permission) | ⬜ Planned (xem Security VI.6) |
| `transition_status` invalid → error | `api/imm00.transition_status` | error envelope | Error guessing | ⬜ Planned |
| `verify_chain` | `api/imm00.verify_chain` | `{verified, count, last_hash}` | Use Case | ⬜ Planned |

## III.7. E2E browser (Playwright)

Dùng cho flow UI khó cover bằng API: ReferenceDataView (tree node CRUD), SlaPolicyListView filter, workflow button visibility theo role. → `assetcore-test` skill Phần 2 (Playwright MCP recipes). Trạng thái: ⬜ Planned (FE views built nhưng chưa có E2E spec).

### III.7.a — Notification Framework E2E (Playwright MCP, vòng 6 — 2026-05-29) — ✅ PASS

Mục tiêu: kiểm chứng UI thật (bell badge + dropdown + KPI card + email toggle) hoạt
động end-to-end, vì 5 vòng trước chỉ dựa unit test + `bench execute`. Stack live khi
chạy: gunicorn :8000 (proxy :80) + vite FE :3000 + socketio :9000. Session đăng nhập
sẵn: `chuvanhieu357@gmail.com` (role thật `System Manager` + `AssetCore Super Admin`).

| TC | Kịch bản (UI thật) | Kết quả |
|----|---------------------|---------|
| E2E-NTF-01 | Render `/settings/notifications` với System Manager | ✅ Toggle email render `switch[checked]`; KPI section "Độ phủ thông báo (30 ngày)" hiển thị |
| E2E-NTF-02 | Bell badge ban đầu | ✅ "0 thông báo chưa đọc", không có badge span |
| E2E-NTF-03 | Sinh notification thật: insert Incident `IR-2026-0130` bởi actor khác (`_test_notif_actor`), `assigned_to`=System Manager → `after_insert`→`notify_incident_created` | ✅ Notification Log tạo cho user nhận (DELTA +1) |
| E2E-NTF-04 | Reload FE → bell badge | ✅ Badge "1", title "1 thông báo chưa đọc" (poll/refresh cập nhật) |
| E2E-NTF-05 | Mở dropdown chuông | ✅ Item render đúng: subject "Sự cố mới [High]: IR-2026-0130", body HTML `<b>` sanitize, tag "Incident Report", thời gian tương đối, tab "Chưa đọc 1" |
| E2E-NTF-06 | Click notification → deep-link + mark-read | ✅ Điều hướng `/incidents/IR-2026-0130` (resolveNotificationRoute); badge về 0 sau khi đọc |
| E2E-NTF-07 | KPI card số liệu (System Manager) | ✅ delivery_rate=None→'—' ("0 gửi · 0 lỗi"); opt_out_rate=0.0→'0%' ("0/9 người dùng") — khớp `get_delivery_kpi` BE |
| E2E-NTF-08 | KPI gating âm (non-admin) | ✅ `get_delivery_kpi` raise `ServiceError[FORBIDDEN]` cho `_test_notif_lowrole`; FE `v-if=isAdmin` + `enabled:isAdmin` chặn cả render lẫn gọi API. `isAdmin` đọc role thật từ auth store (`roles[]` chứa "System Manager"), KHÔNG phụ thuộc display-persona |
| E2E-NTF-09 | Email toggle round-trip thật | ✅ Tắt switch → `set_email_enabled` POST → DB `enable_email_notifications=0`; bật lại → =1 (khôi phục trạng thái) |

Bug phát hiện: KHÔNG. Cleanup: đã xoá `IR-2026-0130` + Notification Log tạo trong
session; email setting khôi phục về 1. Regression: `test_notifications` 36/36 + 
`test_imm12_notify` 12/12 xanh sau e2e.

Giới hạn đã ghi rõ: chỉ chạy được persona System Manager (session sẵn có); KHÔNG
log-in được persona technician riêng qua browser vì không được reset mật khẩu tài
khoản dùng chung (classifier denial). Nhánh "technician nhận notification" verify ở
tầng engine (`after_insert` hook → Notification Log) + unit test, KHÔNG qua browser.
Gating âm verify ở server-side (authoritative) + đọc auth-store role, KHÔNG qua
browser login của non-admin.

## III.8. Performance test

Target-only (chưa chạy baseline). Tool k6 / `pytest-benchmark`.

| Metric | Target (NFR 02) | Method |
|---|---|---|
| GET `list_assets` p95 (100k record) | < 200ms (NFR-00-01) | k6 GET |
| GET `get_asset` full p95 | < 500ms (NFR-00-02) | k6 GET |
| `log_audit_event` p95 | < 100ms (NFR-00-03) | `pytest-benchmark` |
| Scheduler `check_capa_overdue` N record | *(Cần khảo sát)* | `time bench execute` |

## III.9. Test data & Fixtures

| Loại | Cách seed | File |
|---|---|---|
| Master data (Asset Category, Department, Location, SLA Policy, Role) | `fixtures/*.json` (qua `bench migrate`) | `assetcore/fixtures/` |
| Workflow (lifecycle) | `fixtures/workflow.json` + `ac_asset_lifecycle_workflow.json` | `assetcore/assetcore/workflow/` |
| Test records (inline) | `make_test_*` helper trong test file | `tests/test_imm00.py` setUpClass |
| UAT seed | *(Cần khảo sát — chưa có script uat_imm00.py)* | ⬜ Planned |

Backend test fixture dùng prefix `_Test` / `AC-...-TEST-` — xem `assetcore-test` R-0/R-1.

## III.10. Run commands & Coverage gate

```bash
# Module test
bench --site <site> run-tests --app assetcore --module assetcore.tests.test_imm00
bench --site <site> run-tests --app assetcore --module assetcore.tests.test_imm00_smoke
bench --site <site> run-tests --app assetcore --module assetcore.tests.test_imm00_list_assets
# Coverage
coverage run -m unittest assetcore.tests.test_imm00 && coverage report
```

| Layer | Target coverage | Đo |
|---|---|---|
| Service (`services/imm00.py`) | ≥ 85% line + ≥ 80% branch | `coverage --branch` |
| DocType lifecycle | ≥ 70% | `coverage report` |
| API (`api/imm00.py`) | ≥ 60% | `coverage report` |
| Frontend (vue-tsc) | 0 error | `npm run build` |

Coverage % thực tế: *(Cần khảo sát — chưa chạy `coverage report` trong lần sync này; chỉ target.)*

---

# Phần IV — Traceability Matrices

> Mọi test ở Phần III phải xuất hiện ở cả 3 bảng.

## IV.1. FR → Test mapping

| FR ID | AC | Test ID (III.x) | Layer | Status |
|---|---|---|---|---|
| FR-00-01 | naming series | `TestACAsset::test_asset_created_with_naming_series` | Integration | ✅ Live |
| FR-00-02 | filter gmdn | `TestListAssetsGmdnFilter::*` | API | ✅ Live |
| FR-00-04 | transition | `TestACAsset::test_transition_status_commissioned_to_active` | Integration | ✅ Live |
| FR-00-04 | sinh ALE | `TestACAsset::test_transition_creates_lifecycle_event` | Integration | ✅ Live |
| FR-00-05 | block OOS/Decom | `TestACAsset::test_cannot_operate_decommissioned_asset` | Integration | ✅ Live |
| FR-00-06..09 | supplier | `TestACSupplier::*` | Integration | ✅ Live |
| FR-00-19..21 | audit immutable | `TestIMMauditTrail::test_audit_trail_cannot_be_deleted` | Integration | ✅ Live |
| FR-00-22 | verify chain | `TestIMMauditTrail::test_verify_chain_valid`; `TestS12_*` | Integration | ✅ Live |
| FR-00-23..25 | CAPA create/close | `TestIMMCAPARecord::test_create_capa/close_capa` | Integration | ✅ Live |
| FR-00-26 | overdue scheduler | `TestS11_CheckCapaOverdueScheduler` | Unit | ✅ Live |
| FR-00-28..30 | ALE append-only | `TestACAsset::test_transition_creates_lifecycle_event` | Integration | ✅ Live |
| FR-00-43..46 | GMDN filter | `TestListAssetsGmdnFilter::*` | API | ✅ Live |
| FR-00-47..51 | depr inherit before_insert + no-422 | `TC-DEP-30..36` | Unit + Integration | ⬜ Planned (RED-first) |
| FR-00-52 | compute_all backfill-rồi-sinh | `TC-DEP-40..45` | Integration + Security | ⬜ Planned (RED-first) |
| FR-00-53..55 | regenerate self-heal (RC-04) | `TC-DEP-50..57` | Unit + Integration + grep-guard | ⬜ Planned (RED-first) |
| FR-00-56..58 | bulk_regenerate route qua SoT (RC-05) | `TC-DEP-60..67` + `TC-FE-RD-01..03` | Decision Table + Performance + Integration + FE vitest | ⬜ Planned (RED-first) |
| FR-00-03 | block lifecycle_status payload | direct-update block test | Integration | ⬜ Planned |

## IV.2. BR → Test mapping

| BR ID | Phát biểu (rút gọn) | Test ID | Kỹ thuật | Happy / Negative |
|---|---|---|---|---|
| BR-00-01 | Class→Risk map | `TestS04_DeviceModelClassMappingRisk` | Decision Table | 1 / ⬜ (cần Class I/III) |
| BR-00-02 | lifecycle_status chỉ qua service | direct-mutate block test | EP | ⬜ Planned |
| BR-00-03 | Audit/ALE immutable | `TestIMMauditTrail::test_audit_trail_cannot_be_deleted` | Error guessing | 0 / 1 |
| BR-00-04 | Decom → suspend schedule | `TestACAsset::test_decommission_suspends_pm_schedule` | State Transition | 1 / 0 |
| BR-00-05 | block Work Order OOS/Decom | `TestACAsset::test_cannot_operate_decommissioned_asset` | EP | 0 / 1 |
| BR-00-07 | response < resolution×60 | SLA validate BVA | BVA | ⬜ Planned |
| BR-00-08 | CAPA 3-field gate | `TestIMMCAPARecord::test_close_capa`; `TestCAPASmoke::test_s08_submit_capa_without_root_cause_fails` | Decision Table | 1 / 1 ✅ |
| BR-00-26 | **CAPA effectiveness gate — SoT đơn (round 12)** | **AC-1** `test_close_capa_blocks_when_effectiveness_none` (effectiveness=None → raise FIN-007, KHÔNG Closed, KHÔNG submit); **AC-2** `test_close_capa_blocks_when_not_effective` ('Not Effective'/'Partially Effective' → raise FIN-007); **AC-3** `test_close_capa` (happy: 'Effective' → Closed+submitted+ALE — KHÔNG regress); **AC-4** `test_capa_validate_fires_gate_regardless_workflow_state` (status='Closed' + workflow_state≠'Closed' → vẫn raise); `advance_capa_state` (VR-06/VR-07) GIỮ xanh; **AC-5** `test_capa_open_count_unchanged_after_gate` (`_open_capa_filter` đếm CAPA chưa-effectiveness là 'mở'; KPI capa_open/capa_overdue bất biến) | Decision Table + Negative | ⬜ Planned |
| BR-00-09 | CAPA auto-overdue | `TestS11_CheckCapaOverdueScheduler` | BVA | 1 / ⬜ |
| BR-00-16 | `list_capas` conjoin no-clobber | TC-00-CAPA-01..06 (test_imm00 / test_capa_open_sot / test_capa_overdue_sot) | Decision Table + set-algebra | ⬜ Planned |
| BR-00-10 | 1 ALE / transition | `TestACAsset::test_transition_creates_lifecycle_event` | State Transition | 1 / 0 |
| BR-00-13/14 | GMDN inheritance | `TestListAssetsGmdnFilter::*` (filter); inherit test | EP | partial ✅ |
| BR-00-18 | depr inherit SoT + round residual + idempotent | `TC-DEP-30/35/36` | EP + BVA | ⬜ Planned (RED-first) |
| BR-00-19 | no-clobber months/residual (per-field) | `TC-DEP-33/34` | Decision Table | 0 / ⬜ |
| BR-00-20 | Category months=0 → no fabrication, 422 đúng | `TC-DEP-32` | EP (negative) | ⬜ Planned |
| BR-00-21 | compute_all preserve Executed + idempotent + RBAC + audit | `TC-DEP-40..45` | Integration + Security | ⬜ Planned (RED-first) |
| BR-00-22 | regenerate self-heal (RC-04): inherit-trước-precheck + no-clobber + preserve Executed + idempotent + audit + grep-guard | `TC-DEP-50..57` | EP + Decision Table + State + grep-guard | ⬜ Planned (RED-first) |
| BR-00-23 | bulk_regenerate route SoT (RC-05): no-clobber + N+1 đóng + skipped_no_rule + preserve Executed + idempotent + payload 7-key + audit + grep-guard | `TC-DEP-60..67` | Decision Table + Performance + State + Integration + grep-guard | ⬜ Planned (RED-first) |
| BR-05-13 | effective_book_value SoT (RC-06): None→gross / 0.0→0.0 + fully_depreciated đếm book=0.0 + total_book no-phantom + count==drill + no-regression book=None + grep-guard 0 idiom | `TC-DEP-68..76` | EP(boundary) + Decision Table + Integration + Regression + grep-guard | ⬜ Planned (RED-first) |

## IV.3. Component → Test mapping

| Component (I.1) | Test ID | Test layer | Coverage % | Risk priority (I.3) |
|---|---|---|---|---|
| `transition_asset_status` | `TestACAsset::test_transition_*`, `TestS07_*` | Integration | *(Cần khảo sát)* | Critical |
| `log_audit_event` / chain | `TestIMMauditTrail::*`, `TestS12_*` | Integration | *(Cần khảo sát)* | Critical |
| AC Asset permission query | `TestS13_TechnicianScopeFilter::test_s13_tech_user_sees_zero_others_incidents` | Integration | *(Cần khảo sát)* | Critical |
| `close_capa` (BR-00-08) | `TestIMMCAPARecord::test_close_capa`, `TestCAPASmoke::*` | Integration | *(Cần khảo sát)* | High |
| `validate_asset_for_operations` | `TestACAsset::test_cannot_operate_decommissioned_asset` | Integration | *(Cần khảo sát)* | High |
| `get_sla_policy` | `TestIMSLAPolicy::test_resolve_*` | Unit | *(Cần khảo sát)* | Medium |
| `check_capa_overdue` | `TestS11_*` | Unit | *(Cần khảo sát)* | Medium |
| `update_user_roles` (RBAC) | `TestUserRoleManagement::*` | Integration | *(Cần khảo sát)* | Critical |
| FK delete integrity | `TestFKDeleteIntegrity::*` | Integration | *(Cần khảo sát)* | Medium |
| `list_assets` API | `TestListAssetsGmdnFilter::*` | API | *(Cần khảo sát)* | Medium |

---

# Phần V — UAT Script

## V.1. Phạm vi UAT

- **In-scope**: setup validation foundation (smoke V.4), lifecycle chain integrity, CAPA lifecycle, permission scope.
- **Out-of-scope**: performance (III.8), security pentest (Phần VI.10).
- **Pre-condition**: site UAT deploy version đang sync vs code (2026-05-27), fixture loaded (`bench migrate`), tester accounts active đủ các role.

## V.2. Tester accounts

| Username | Role | Vai trò UAT |
|---|---|---|
| admin@uat.vn | AssetCore Super Admin | Setup, role mgmt, decommission |
| pmuser@uat.vn | PM User | Commission/Activate/repair transitions |
| pmmanager@uat.vn | PM Manager | Out of Service transitions |
| qa@uat.vn | Compliance Manager / AssetCore Auditor | CAPA, verify audit chain |
| tech@uat.vn | (low-role, không phải responsible) | FORBIDDEN / scope filter case |

Phải có account low-role (`tech@uat.vn`) để cover scope-filter case (không chỉ Admin).

## V.3. Test data đã seed

| DocType | Số lượng | Ghi chú |
|---|---|---|
| AC Asset Category | ≥ 3 | có gmdn_code để test inheritance |
| IMM Device Model | ≥ 3 | Class I / II / III để test BR-00-01 |
| AC Asset | ≥ 5 | trạng thái khác nhau (Active, Decommissioned, Out of Service) |
| IMM SLA Policy | ≥ 2 | 1 exact + 1 is_default (test fallback) |
| Incident Report | ≥ 2 | 1 gán tech@uat.vn, 1 không (test scope) |

Reset: *(Cần khảo sát — dùng `scripts/purge_test_data` cho cleanup.)*

## V.4. UAT Scenarios — Suy ra từ FR + Activity

Mỗi scenario theo template §Phụ lục A. ID `UAT-IMM-00-NN`.

| ID | Actor | Pre-condition | FR/BR cover | Kỹ thuật | Kết quả mong đợi |
|---|---|---|---|---|---|
| UAT-IMM-00-01 | System Admin | category + model seeded | FR-00-01, BR-00-01 | Use Case happy | AC Asset tạo, autofill class/risk/gmdn |
| UAT-IMM-00-02 | PM User | Asset Commissioned | FR-00-04, BR-00-10 | State Transition | Active→Under Repair→Active, mỗi bước 1 ALE + 1 audit |
| UAT-IMM-00-03 | System Manager | Active asset | BR-00-04 | State Transition | Decommissioned → is_pm_required=0, next_pm_date=null |
| UAT-IMM-00-04 | PM User | Decommissioned asset | BR-00-05 | EP negative | `validate_for_operations` block (không tạo WO) |
| UAT-IMM-00-05 | QA Officer | Incident Major submitted | FR-00-23, BR-00-08 | Use Case alt | CAPA thiếu root_cause → submit fail; đủ field → Closed |
| UAT-IMM-00-06 | QA Officer | 1 asset có ≥ 1 audit | FR-00-22 | Use Case | `verify_chain` trả `{verified:true, count}` |
| UAT-IMM-00-07 | tech@uat.vn (low-role) | 2 incidents, 1 gán tech | RISK-00-04, NFR-00-07 | EP permission | List chỉ thấy incident được gán (scope filter) |
| UAT-IMM-00-08 | Admin | CAPA Open quá due_date | BR-00-09 | BVA | scheduler → status Overdue + email |

## V.5. Tổng hợp kết quả & Bug found

- Bảng `Scenario · Status (Pass/Fail/Block) · Tester · Ngày · Ghi chú` — điền khi chạy UAT.
- Bug list: `Issue ID · Severity (Blocker/Major/Minor/Trivial) · Mô tả · Fix status`.
- Acceptance: ≥ 95% PASS, Blocker = 0, Major ≤ 2 (có workaround).
- Sign-off: BA Lead + QA Lead + Module Owner (System Architect).

---

# Phần VI — Security Review (gate)

## VI.1. RBAC

- **Role definitions**: `fixtures/role.json` (PM User, PM Manager, AssetCore System User, AssetCore Super Admin, AssetCore Auditor, Compliance Manager/User, + per-module *User roles) + `role_profile.json`.
- **DocPerm matrix** (Decision Table — mỗi (role × action) là 1 row):

| DocType | Role | R | W | C | S | D |
|---|---|---|---|---|---|---|
| AC Asset | AssetCore Super Admin | ✓ | ✓ | ✓ | ✓ | — |
| AC Asset | AssetCore System User / Auditor / *User (PM, Repair, …) | ✓ | — | — | — | — |
| IMM Audit Trail | AssetCore Super Admin | ✓ | ✓ | ✓ | — | ✓ |
| IMM Audit Trail | AssetCore Auditor | ✓ | — | — | — | — |
| IMM CAPA Record | AssetCore Super Admin / Compliance Manager | ✓ | ✓ | ✓ | ✓ | — |
| IMM CAPA Record | Compliance User | ✓ | ✓ | ✓ | — | — |
| IMM CAPA Record | AssetCore Auditor / System User | ✓ | — | — | — | — |

> Ghi chú audit: Write/Create trên IMM Audit Trail chỉ cấp cho Super Admin nhằm phục vụ `log_audit_event` qua `ignore_permissions`; ở tầng application controller chặn update (BR-00-03). Cần xác nhận perm này không cho user thật sửa record (xem VI.3).

- **Field-level permission**: *(Cần khảo sát — chưa xác minh permlevel ≠ 0 cho field nhạy cảm như cost/funding trong các DocType foundation.)*
- **User Permission**: filter row theo responsible_technician qua `permission.py::get_ac_asset_permission_query()` (RISK-00-04, NFR-00-07).

## VI.2. API security

- **Whitelist hygiene**: 105 endpoint `@frappe.whitelist`; mutating endpoint dùng `methods=["POST"]`. Cần xác nhận mọi endpoint có docstring + rbac check + validate input — *(Cần khảo sát toàn diện)*.
- **CSRF**: Frappe default `X-Frappe-CSRF-Token`.
- **Input validation**: Link field validate qua `frappe.get_value` trước khi dùng (theo convention service layer).
- **SQL injection**: parameterized only; không f-string vào raw SQL — *(cần audit `list_audit_trail` / `list_assets` filter build)*.
- **Rate limit**: scheduler trigger endpoint chỉ cấp Super Admin/System Manager.

## VI.3. Audit trail integrity

Mọi mutation sinh `IMM Audit Trail`, SHA-256 chain (`hash_sha256` + `prev_hash`). Verify endpoint `verify_chain`. User KHÔNG được edit/delete (controller block `not is_new()` + DocPerm; ISO 13485:7.5.9). → III.5 test cases (`TestIMMauditTrail::test_audit_trail_cannot_be_deleted` ✅).

| TC ID | Test | Expected | Trạng thái |
|---|---|---|---|
| SEC-01 | Low-role GET `list_assets` | chỉ asset gán session.user | ⬜ Planned (scope test live cho incident) |
| SEC-02 | `frappe.db.set_value("IMM Audit Trail", ...)` | fail — controller block | ✅ Live (`test_audit_trail_cannot_be_deleted`) |
| SEC-03 | `update_asset` payload `lifecycle_status` | reject (BR-00-02) | ⬜ Planned |
| SEC-04 | delete Asset Lifecycle Event | block (append-only) | ⬜ Planned |
| SEC-05 | trigger scheduler với low-role | FORBIDDEN | ⬜ Planned |
| SEC-06 | verify_chain sau tamper DB | `verified=false` | ⬜ Planned |
| SEC-07 | non-admin `update_user_roles` | block | ✅ Live (`test_non_admin_cannot_set_roles`) |

## VI.4. Authentication & session

Login Frappe default; session timeout + lockout + password policy theo site_config. API key rotation thủ công. 2FA: roadmap. *(Cấu hình cụ thể — Cần khảo sát site UAT.)*

## VI.5. Data sensitivity

| Loại | Trường | Sensitivity | Bảo vệ |
|---|---|---|---|
| Asset registry | serial, udi, location | Internal | RBAC read |
| Audit trail | actor (email), change_summary | Internal | append-only, immutable |
| CAPA | root_cause, corrective_action | Confidential | Compliance role + submittable |
| Vendor | iso_17025_cert | Internal | RBAC |

Khẳng định: KHÔNG lưu patient data (GDPR/NĐ13); event payload chỉ `session.user` (email).

## VI.6. Vendor isolation

IMM-00 chưa expose vendor external portal trực tiếp; vendor isolation chủ yếu thuộc IMM-09/11. Foundation đảm bảo low-role chỉ thấy data được gán qua permission query (RISK-00-04). → test III.6 low-role + `TestS13_TechnicianScopeFilter` ✅ Live.

## VI.7. Secrets management

Cấm commit `.env` / credential; `site_config.json` không lên git; external token lưu `frappe.conf`. Backup encrypt at-rest off-site (NĐ98 Art.4: lưu ≥ 7 năm).

## VI.8. Logging & monitoring

| Sự kiện | Log level | Where | Alert? |
|---|---|---|---|
| service function entry/DONE | INFO | `frappe.logger("imm00")` | — |
| scheduler fail | ERROR | scheduler log | Email Admin (RISK-00-03) |
| permission deny | WARNING | frappe error log | — |

PII / token KHÔNG vào log; sanitize input trước khi log.

## VI.9. Threat model (STRIDE-lite)

| Threat | STRIDE | Vector | Likelihood | Impact | Mitigation |
|---|---|---|---|---|---|
| Giả mạo identity / session fixation | **S**poofing | mọi endpoint | Low | High | X-Frappe-CSRF-Token + Frappe session mgmt |
| Audit fabrication (fake prev_hash) | Spoofing | IMM Audit Trail | Low | High | prev_hash link tới record trước; chain không fake được không có chuỗi |
| Sửa Audit/ALE/CAPA sau tạo | **T**ampering | Audit/ALE/CAPA | Med | High | append-only controller + docstatus=1 + DocPerm |
| Bypass `transition_asset_status` (set field trực tiếp) | Tampering | AC Asset.lifecycle_status | Med | High | BR-00-02 service-only mutation; update_asset reject payload |
| Phủ nhận hành động | **R**epudiation | mutation | Low | Med | mọi mutation → audit entry với actor |
| IMM Technician thấy asset/incident không gán | **I**nfo disclosure | AC Asset / Incident | Med | High | permission_query_conditions; BE enforce; FE filter |
| Scheduler abuse / DB lock N+1 | **D**enial of service | scheduler endpoint | Low | Med | rate_limit + Admin-only + idempotent retry ≤3 |
| Low-role gọi admin endpoint (set roles, trigger) | **E**levation of privilege | role mgmt / scheduler | Med | High | `has_role` check (`test_non_admin_cannot_set_roles` ✅) |

## VI.10. Penetration test

Trước release đầu tiên: Burp/ZAP scan, sqlmap (an toàn), CSRF test, role escalation. Report lưu `docs/security/imm00-pentest.md`. Trạng thái: ⬜ Planned (xem README roadmap).

## VI.11. Sign-off

| Role | Người | Ngày | Quyết định |
|---|---|---|---|
| QA Lead | — | — | Pass / Pass with conditions / Fail |
| Security Officer | — | — | — |
| Module Owner (System Architect) | — | — | — |

---

# Phần VII — Code Quality

## VII.1. Tool matrix

| Tool | Mục tiêu | Target | Cadence |
|---|---|---|---|
| **SonarQube** (BE Python) | bug / smell / coverage | bug 0 critical, duplication ≤ 3%, coverage ≥ 70%, security hotspot review 100% | mỗi PR |
| **ruff** (BE) | PEP8 + flake8-compat | 0 error, 0 warning | mỗi PR |
| **black** (BE) | format | 100% formatted | mỗi PR |
| **mypy** (BE) | type hints | strict, 0 error trên `services/` | mỗi PR |
| **bandit** (BE) | security lint | 0 high severity | mỗi PR |
| **ESLint + vue-tsc** (FE) | lint + type | 0 error, 0 warning prod build | mỗi PR FE |
| **Lighthouse** (FE) | Perf/A11y | Performance ≥ 85, Accessibility ≥ 90, Best Practices ≥ 90 | release lớn + monthly |
| **Bundle size** (FE chunk imm00) | budget | main ≤ 250KB gzip, async ≤ 80KB gzip | mỗi PR FE |
| **Vitest** (FE) | unit composables/stores | ≥ 70% | mỗi PR FE |

Logging convention (mọi service function): `[function_name] key=value ... DONE|ERROR` qua `frappe.logger("imm00", allow_site=True)`.

## VII.2. Cadence

- SonarQube: mỗi PR (CI gate, fail nếu Quality Gate fail).
- Lighthouse: mỗi release lớn + monthly audit.
- ESLint / ruff / mypy / bandit: mỗi PR (CI gate).
- Bundle size: mỗi PR FE (CI report, fail nếu vượt budget).
- Gắn screenshot SonarQube + Lighthouse vào file 09 §Release Notes khi báo cáo final.

---

# Phụ lục A — Template per UAT scenario

```markdown
### UAT-IMM-00-<NN> — <Tên>

**Liên kết**: FR-<NN>, AC<N>, BR-<NN>
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
### TC-IMM-00-<LAYER>-<NN> — <Tên>

**Component (I.1)**: <…>
**Liên kết**: FR-<NN> | BR-<NN>
**Kỹ thuật (II.1/II.2)**: BVA boundary / Decision Table / EP
**Priority (I.3)**: Critical / High / Medium / Low
**Test type**: Unit / Integration / API / E2E
**Pre-condition**: <fixture / state setup>

**Input**:
- <field>: <value>

**Steps**:
1. <…>
2. <…>

**Expected**:
- frappe.exceptions.ValidationError (message contains "<…>")
- doc.lifecycle_status unchanged

**Post-condition**: <DB rollback / fixture cleanup>
```

# Phụ lục C — Workflow State Transition Test template

```markdown
### TC-IMM-00-WF-<NN> — <action>: <from> → <to>

**Workflow JSON**: `assetcore/assetcore/workflow/ac_asset_lifecycle_workflow.json`
**Role required**: <…>
**Pre-condition**: doc.lifecycle_status = <from>
**Action**: transition_asset_status(asset, "<to>", actor, reason)
**Expected (happy)**: doc.lifecycle_status = <to>, 1 Asset Lifecycle Event created, 1 IMM Audit Trail entry
**Expected (negative role)**: PermissionError / FORBIDDEN
**Expected (invalid transition)**: ValidationError (vd Decommissioned → bất kỳ)
```

---

# DoD — File 07 hoàn chỉnh

## I. Test Analysis
- [x] I.1 Component Inventory liệt kê artefact foundation (so với 04/05/06)
- [x] I.2 mỗi FR / BR / Activity có ≥ 1 dòng map
- [x] I.3 Risk priority gán cho mọi component (không trống)
- [x] I.4 Scope ghi rõ out-of-scope kèm lý do

## II. Test Design Techniques
- [x] II.1 chọn ≥ 4 black-box techniques (EP + BVA + Decision Table + State Transition)
- [x] II.2 white-box criteria xác định (statement + branch)
- [x] II.3 mapping component → kỹ thuật điền đầy đủ

## III. Test Plan
- [x] Test class structure cho service public function trọng yếu (I.1)
- [x] ≥ 1 happy + 1 negative test cho function trọng yếu (CAPA, transition có cả 2)
- [ ] Workflow transitions cover 100% — hiện 3/16 transition có test live (xem III.4)
- [ ] Audit chain test (intact ✅ + tampered ⬜) — case tamper chưa viết
- [ ] API test ≥ 60% coverage + permission matrix — mới có GMDN filter test, coverage chưa đo
- [x] Performance target xác định (NFR-00-01..03)
- [x] CI command chạy clean (`bench run-tests --module assetcore.tests.test_imm00*`)
- [ ] **SonarQube Quality Gate pass** + **Lighthouse score** — chưa chạy/đính kèm

## IV. Traceability
- [x] IV.1 FR → Test: FR trọng yếu có ≥ 1 Test ID (FR-00-03 còn Planned)
- [ ] IV.2 BR → Test: BR-00-02/07 chưa có test live (happy+negative chưa đủ)
- [ ] IV.3 Component → Test: coverage % thực tế chưa đo (*(Cần khảo sát)*)

## V. UAT
- [x] Mỗi FR trọng yếu có ≥ 1 UAT scenario (V.4, 8 scenario)
- [x] ≥ 1 negative + permission + audit verify scenario (UAT-04/07/06)
- [ ] Test data seed script chạy được — script `uat_imm00.py` chưa tồn tại
- [ ] Tester accounts đã tạo ở UAT site — bảng V.2 là kế hoạch, chưa provision
- [x] Sign-off section sẵn sàng (V.5 + VI.11)

## VI. Security
- [x] DocPerm matrix đầy đủ (Decision Table — AC Asset, Audit, CAPA)
- [ ] Mọi field nhạy cảm có permlevel ≠ 0 — *(Cần khảo sát)*, chưa xác minh
- [ ] SQL injection + CSRF test pass — CSRF default OK; SQL audit chưa chạy
- [ ] Audit chain test pass (intact ✅ + tampered ⬜)
- [x] Vendor/scope isolation test pass (low-role `TestS13_TechnicianScopeFilter` ✅)
- [x] Threat model đủ 6 STRIDE với mitigation
- [ ] Sign-off đầy đủ trước go-live — bảng VI.11 chưa ký

## VII. Code Quality
- [ ] SonarQube Quality Gate pass — chưa chạy
- [ ] Lighthouse ≥ target — chưa chạy
- [ ] Bundle size ≤ budget — chưa đo
- [ ] Screenshot báo cáo gắn vào file 09 — chưa có
