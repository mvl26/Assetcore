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

### III.6.0b — Vòng B: SIẾT RBAC in nhãn QR `asset.read`→`asset.write` (ADR-001 D4)

File BE: cập nhật class `TestAssetLabelData` (`assetcore/tests/test_imm00.py` ~:2429). **Giữ** `test_label_endpoints_require_asset_read` (no-cap/Guest vẫn 403) NHƯNG **THÊM** test phân-tách read vs write — đo QUA layer `require` với **user THẬT** có/không `asset.write` (KHÔNG mock `require`, KHÔNG mock `has_permission` → tránh test false-green; luật skill: test mới phải đi QUA layer require).

**Acceptance — chạy XANH:** `bench --site miyano run-tests test_imm00` + `test_rbac` GREEN; `bench migrate` sạch (cap-set version GIỮ `v95.3388ee5629c1`); `vue-tsc` 0; `vitest` GREEN. Toàn bộ test cũ vẫn xanh (regression).

| TC (BE) | Kịch bản (user THẬT, qua layer `require`) | Verify | Kỹ thuật |
|---|---|---|---|
| `test_label_data_read_only_user_403` | user có `asset.read` NHƯNG KHÔNG `asset.write` (DocPerm AC Asset: read=1, write=0) gọi `get_asset_label_data` | `PermissionError` (403) | EP (least-privilege) |
| `test_label_batch_read_only_user_403` | cùng user trên gọi `get_asset_label_data_batch([a])` | `PermissionError` (403) | EP |
| `test_mark_printed_read_only_user_403` | cùng user trên gọi `mark_label_printed([a])` | `PermissionError` (403); KHÔNG ghi `label_printed`/audit (count trước=sau) | EP + state-based |
| `test_label_data_write_user_200` | user có `asset.write` (DocPerm write=1) gọi `get_asset_label_data` | 200, payload đủ 6 key | Use Case (positive) |
| `test_mark_printed_write_user_200` | user có `asset.write` gọi `mark_label_printed([a])` | 200; ĐÚNG 1 `label_printed` + 1 audit / asset | Use Case (positive) |
| `test_readonly_qr_endpoints_keep_asset_read` | user có `asset.read` (KHÔNG write) gọi `resolve_qr_token` / `get_asset_scan_info` / `get_asset` | 200 (read-only GIỮ `asset.read` — KHÔNG bị siết) | Regression (negative-scope) |
| `test_label_idor_unchanged_after_write_gate` | user có `asset.write` NHƯNG vendor ngoài scope (Vendor Engineer) | **403 IDOR** (`assert_vendor_can_access`) — siết RBAC KHÔNG nới IDOR | IDOR (regression) |
| `test_cap_set_version_unchanged` | sau `bench migrate` | `CAP_SET_VERSION == "v95.3388ee5629c1"`; `"asset.write" in CAPABILITY_MAP`; KHÔNG có `"asset.print_label"` | White-box (no-churn guard) |

> **KHÔNG test false-green:** test tạo user thật + cấp/không-cấp DocPerm `write` trên `AC Asset` (qua Role có DocPerm tương ứng), `frappe.set_user(...)`, rồi gọi endpoint. KHÔNG `monkeypatch rbac.require`/`frappe.has_permission`. Gate đi đúng đường `require("asset.write")` → `can` → `frappe.has_permission("AC Asset","write")`.

| TC (FE) | Kịch bản | Verify |
|---|---|---|
| `AssetDetailView.test.ts::print_btn_hidden_read_only` | mock caps `{asset.read:true, asset.write:false}` | nút "In nhãn QR" KHÔNG render |
| `AssetDetailView.test.ts::print_btn_shown_with_write` | mock caps `{asset.write:true}` | nút "In nhãn QR" render |
| `AssetListView.test.ts::batch_print_btn_gated_write` | mock caps `{asset.write:false}` | nút "In nhãn hàng loạt" KHÔNG render |
| `router.test.ts::label_print_route_requires_write` | guard `AssetLabelPrint` với caps `{asset.read:true,asset.write:false}` | redirect Unauthorized (KHÔNG vào view) |

### III.6.0c — Vòng 22 / B-6: Cap batch nhãn QR — 413 payload-DoS (ADR-001 D3/D4, BR-00-33)

File BE: cập nhật class `TestAssetLabelData` (`assetcore/tests/test_imm00.py`) — **THÊM** test cap (RED-first: assert 413 trước khi impl). Đo QUA layer thật (user có `asset.write`, gọi endpoint với `len(names)` ở các biên). KHÔNG mock `require`/`has_permission` (chống false-green). FE: cập nhật `AssetListView.test.ts` + `AssetLabelPrintView.test.ts` (hoặc suite label tương ứng).

**Acceptance — chạy XANH:** `bench --site miyano run-tests test_imm00` (class `TestAssetLabelData` + test cap mới) GREEN; `bench migrate` sạch (cap-set GIỮ `v95.3388ee5629c1`); `vue-tsc` 0; `vitest` (label suites) GREEN. Toàn bộ test cũ vẫn xanh (regression — thứ tự output batch, `AC-E001` index, no-N+1, all-or-nothing, IDOR 403-toàn-call).

| TC (BE) | Kịch bản (user có `asset.write`) | Verify | Kỹ thuật |
|---|---|---|---|
| `test_label_batch_at_cap_ok` | `get_asset_label_data_batch(names)` với `len == _MAX_LABEL_BATCH` (=200; dùng 200 name — name không tồn tại OK, vẫn đi tiếp) | KHÔNG 413; trả list 200 entry (mỗi entry payload hoặc `{name,error:"AC-E001"}`) | Boundary (biên dưới PASS) |
| `test_label_batch_over_cap_413` | `get_asset_label_data_batch(names)` với `len == _MAX_LABEL_BATCH + 1` (=201) | **413**; message VI cố định (`_ERR_LABEL_BATCH_TOO_LARGE`); KHÔNG leak asset name nào trong body; KHÔNG build payload | Boundary (biên trên 413) |
| `test_mark_printed_over_cap_413_no_side_effect` | `mark_label_printed(names)` với `len == 201` | **413**; **KHÔNG** ghi `label_printed`/audit nào (count trước = sau — chặn TRƯỚC vòng write) | Boundary + state-based |
| `test_mark_printed_at_cap_ok` | `mark_label_printed(names)` với `len == 200` (toàn asset hợp lệ) | 200; ĐÚNG 200 `label_printed` + 200 audit (1/asset) | Boundary (biên dưới PASS) |
| `test_label_batch_empty_no_413` | `get_asset_label_data_batch([])` / `(None)` | 200 `data: []`; KHÔNG 413, KHÔNG side-effect | EP (rỗng giữ hành vi cũ) |
| `test_mark_printed_empty_no_413` | `mark_label_printed([])` / `(None)` | 200 `{printed:[],event_count:0}`; KHÔNG 413, KHÔNG ghi event | EP (rỗng giữ hành vi cũ) |
| `test_label_batch_single_ok` | `len == 1` | bình thường (200) | EP |
| `test_cap_check_after_rbac_before_idor` | user **chỉ-đọc** (KHÔNG `asset.write`) gọi batch `len == 201` | **403** (RBAC chạy TRƯỚC cap) — KHÔNG 413 → khách KHÔNG dò được ngưỡng | Ordering (no-leak) |
| `test_max_label_batch_is_ssot` | white-box | `_MAX_LABEL_BATCH` định nghĩa ĐÚNG 1 nơi (`services/imm00.py`); api `import` (không redefine); `grep '> 200'`/literal `200` ở api/imm00.py batch path = 0 | White-box (SSoT guard) |
| `test_cap_set_version_unchanged_round22` | sau `bench migrate` | `CAP_SET_VERSION == "v95.3388ee5629c1"` (cap GIỮ — đề mục KHÔNG thêm cap) | White-box (no-churn guard) |

| TC (FE) | Kịch bản | Verify |
|---|---|---|
| `AssetListView.test.ts::batch_print_at_cap_navigates` | `selectedNames.length == 200`, click "In nhãn hàng loạt" | điều hướng sang `AssetLabelPrint` bình thường (KHÔNG cảnh báo) |
| `AssetListView.test.ts::batch_print_over_cap_warns_no_nav` | `selectedNames.length == 201` | KHÔNG navigate; hiện cảnh báo VI (`"Chỉ in tối đa 200 nhãn mỗi lần..."`) |
| `AssetLabelPrintView.test.ts::query_names_over_cap_error_bucket` | `route.query.names` CSV 201 phần tử | render bucket lỗi VI `too-large`; **KHÔNG** gọi `getAssetLabelDataBatch` |
| `AssetLabelPrintView.test.ts::api_413_maps_vi_bucket` | mock `getAssetLabelDataBatch`/`markLabelPrinted` trả HTTP 413 (paste URL) | render bucket lỗi VI `too-large`; KHÔNG raw `.message`, KHÔNG trang trắng, KHÔNG EN-leak (parity `QrResolveView`/`AssetScanInfoView`) |
| `label.test.ts::fe_cap_matches_be` | so khớp | `frontend/src/constants/label.ts::_MAX_LABEL_BATCH == 200` (đồng bộ BE — guard drift) |

> **KHÔNG test false-green:** test cap đi QUA endpoint thật với `len(names)` ở biên; KHÔNG monkeypatch `_MAX_LABEL_BATCH` xuống số nhỏ rồi assert (giữ test phản ánh ngưỡng prod). Dùng đúng 200/201 name (name giả `"AC-ASSET-FAKE-{i}"` cho test 413 — vì cap chặn TRƯỚC `exists` nên không cần asset thật cho biên trên).

### III.6.a — A6: `get_asset_scan_info` — màn info mobile-first khi quét QR (ADR-001 V7)

File BE: thêm class `TestGetAssetScanInfo` vào `assetcore/tests/test_imm00.py` (cạnh `TestResolveQrToken` A2 — line ~2045). FE: `frontend/src/views/asset/AssetScanInfoView.test.ts` (NEW) + cập nhật `QrResolveView.test.ts` (regression).

**Acceptance — chạy XANH:** `bench --site miyano run-tests` (BE A6) + `bench migrate` sạch + `vue-tsc` 0 lỗi + `vitest` (view mới + regression).

| TC (BE) | Kịch bản | Verify | Kỹ thuật |
|---|---|---|---|
| `test_scan_info_returns_mobile_payload_shape` | token hợp lệ + user có `asset.read` | 200; payload có ĐÚNG keys: `name, asset_code, asset_name, device_model_name, location_name, lifecycle_status, lifecycle_status_label, last_maintenance, next_pm_date`; **KHÔNG có** `gross_purchase_amount`/`current_book_value`/`accumulated_depreciation`/`supplier`/audit | Use Case + field-whitelist |
| `test_scan_info_status_label_vi_not_raw_en` | asset `lifecycle_status="Active"` | `lifecycle_status_label == "Đang hoạt động"` (qua SSoT `labels.py`); KHÔNG leak mã EN làm nhãn | EP |
| `test_scan_info_last_maintenance_latest_only` | asset có 2 `pm_completed` + 1 `repair_completed` ở mốc khác nhau | `last_maintenance` = sự kiện mới nhất (timestamp lớn nhất), 1 object (KHÔNG mảng timeline); `event_type_label` VI | Boundary |
| `test_scan_info_no_maintenance_returns_null` | asset chưa có sự kiện bảo trì | `last_maintenance is None` (KHÔNG lỗi) | EP |
| `test_scan_info_by_name_param` | `get_asset_scan_info(name=<asset>)` (không token) | 200 cùng payload | EP |
| `test_scan_info_unknown_token_404` | token rỗng / sai định dạng / không tồn tại | **404** generic (KHÔNG 500, KHÔNG phân biệt sai-định-dạng vs không-tồn-tại) | Error guessing (leak-safe) |
| `test_scan_info_without_capability_403` | user KHÔNG có `asset.read` (Guest) | `PermissionError` (403); gate chạy TRƯỚC resolve (token tồn tại vẫn 403) | EP (permission) |
| `test_scan_info_vendor_out_of_scope_403_no_leak` | vendor user, asset NGOÀI scope | **403** (`assert_vendor_can_access`); KHÔNG trả data | IDOR |
| `test_scan_info_no_audit_side_effect` | gọi `get_asset_scan_info` N lần | **KHÔNG** tạo `Asset Lifecycle Event` / `IMM Audit Trail` mới (count trước = sau); KHÔNG gọi `ensure_asset_qr_token` | State-based (no-write) |
| `test_scan_info_no_nplus1` | asset có nhiều ALE | số query bảo trì gần nhất = 1 (`order_by timestamp desc limit 1`), KHÔNG load toàn timeline | White-box (query count) |

| TC (FE) | Kịch bản | Verify |
|---|---|---|
| `QrResolveView.test.ts::regression_no_land_asset_detail` | resolve thành công | `router.replace` gọi với `name:'AssetScanInfo'`, **KHÔNG** `'AssetDetail'` — assert NEGATIVE (chống regress) |
| `AssetScanInfoView.test.ts::renders_mobile_payload` | mock 200 | render `asset_name`, status pill VI (`lifecycle_status_label`), bảo trì gần nhất; KHÔNG render giá/khấu hao |
| `AssetScanInfoView.test.ts::loading_aria_busy` | trạng thái loading | có `aria-busy="true"`, KHÔNG trang trắng |
| `AssetScanInfoView.test.ts::error_403_alert` / `error_404_alert` | mock 403 / 404 | `role="alert"` + message VI tương ứng + nút Quét lại / Về trang chủ |
| `AssetScanInfoView.test.ts::no_mutation_buttons` | render thành công | KHÔNG có nút edit / delete / transition / workflow (read-only) |
| `labels.test.ts::vi_label_no_drift` | so khớp | `LIFECYCLE_STATUS_LABEL_VI` (BE mirror) khớp value với FE `constants/labels.ts::LIFECYCLE_STATUS_LABEL` (guard drift) |

#### III.6.a-PMOVERDUE — A6-hardening (Vòng 27 B): cờ `pm_overdue` server-side — BR-00-36 / FR-00-85

File BE: thêm class `TestAssetScanInfoPmOverdue` vào `assetcore/tests/test_imm00.py` (cạnh `TestGetAssetScanInfo`). FE: cập nhật `frontend/src/views/asset/AssetScanInfoView.test.ts` (thêm TC badge). **RED-first:** class/TC chưa tồn tại → fail → impl `_is_pm_overdue` + thêm field payload → GREEN. Đo QUA `build_asset_scan_info` (KHÔNG mock `getdate`/`nowdate` — set `next_pm_date` thật quanh `nowdate()` để check ranh giới strict `<`).

**Acceptance — chạy XANH:** `bench --site miyano run-tests test_imm00` (`TestAssetScanInfo` baseline + `TestAssetScanInfoPmOverdue` mới) + `bench migrate` exit 0 + `vue-tsc` 0 lỗi + `vitest AssetScanInfoView.test.ts` GREEN. `CAP_SET_VERSION` GIỮ `v95.3388ee5629c1`.

| TC (BE) | Kịch bản | Verify | Kỹ thuật |
|---|---|---|---|
| `test_payload_has_pm_overdue_key_8_fields_intact` | asset bất kỳ, gọi `build_asset_scan_info` | payload CÓ key `pm_overdue` (bool) **+ 8 field hiện có GIỮ NGUYÊN** (`name, asset_code, asset_name, lifecycle_status, device_model_name, location_name, next_pm_date, recent_maintenance`) — KHÔNG mất/đổi tên field | Field-whitelist (delta) |
| `test_pm_overdue_true_when_past_date_active` | `next_pm_date = add_days(nowdate(), -1)`, `lifecycle_status="Active"` | `pm_overdue is True` | EP (positive) |
| `test_pm_overdue_false_when_next_pm_null` | `next_pm_date=None`/`""` | `pm_overdue is False` (KHÔNG lỗi) | EP (null) |
| `test_pm_overdue_false_when_today` | `next_pm_date = nowdate()` | `pm_overdue is False` (STRICT `<` — hôm nay CHƯA quá hạn) | Boundary |
| `test_pm_overdue_false_when_future` | `next_pm_date = add_days(nowdate(), +1)` | `pm_overdue is False` | Boundary |
| `test_pm_overdue_false_when_out_of_service` | `next_pm_date` quá khứ, `lifecycle_status="Out of Service"` | `pm_overdue is False` (status ∈ `BLOCKED_FOR_WO`) | EP (status exclude) |
| `test_pm_overdue_false_when_decommissioned` | `next_pm_date` quá khứ, `lifecycle_status="Decommissioned"` | `pm_overdue is False` | EP (status exclude) |
| `test_pm_overdue_true_when_under_repair_past_due` | `next_pm_date` quá khứ, `lifecycle_status="Under Repair"` | `pm_overdue is True` (chỉ `Out of Service`/`Decommissioned` bị loại — Under Repair vẫn tính) | EP (status include) |
| `test_pm_overdue_uses_server_nowdate_not_client` | so `_is_pm_overdue` với `getdate(nowdate())` | mốc so là `nowdate()` server (timezone-safe) — KHÔNG `datetime.now()` | White-box |
| `test_scan_info_pm_overdue_no_audit_side_effect` | gọi `get_asset_scan_info` (asset quá hạn) N lần | KHÔNG tạo `Asset Lifecycle Event`/`IMM Audit Trail` mới (đọc cờ = read-only) | State-based (no-write) |
| `test_pm_overdue_guard_empty_asset_returns_none` | `build_asset_scan_info("")` | trả `None` (guard rỗng GIỮ nguyên — KHÔNG raise vì pm_overdue) | EP (guard) |

| TC (FE) | Kịch bản | Verify |
|---|---|---|
| `AssetScanInfoView.test.ts::badge_when_pm_overdue_true` | mock `getAssetScanInfo` trả `pm_overdue:true` | render badge "Quá hạn bảo trì" (`getByRole('status')`/`getByText`); ngày `next_pm_date` vẫn hiển thị |
| `AssetScanInfoView.test.ts::no_badge_when_pm_overdue_false` | mock `pm_overdue:false` | KHÔNG có text "Quá hạn bảo trì"; ngày `next_pm_date` GIỮ NGUYÊN hiển thị |
| `AssetScanInfoView.test.ts::badge_a11y_not_color_only` | mock `pm_overdue:true` | badge có text + `role="status"` + `aria-label` (a11y — KHÔNG chỉ dựa màu) |
| `AssetScanInfoView.test.ts::no_client_date_compare` | mock `pm_overdue:false` NHƯNG `next_pm_date` quá khứ | KHÔNG render badge (FE KHÔNG tự so ngày — chỉ theo cờ BE) |

#### III.6.b-CALOVERDUE — A6-hardening (Vòng 28 B): cờ `calibration_overdue` + `next_calibration_date` server-side — BR-00-37 / FR-00-86

File BE: thêm class `TestAssetScanInfoCalibrationOverdue` vào `assetcore/tests/test_imm00.py` (cạnh `TestAssetScanInfoPmOverdue`). FE: cập nhật `frontend/src/views/asset/AssetScanInfoView.test.ts` (thêm TC badge hiệu chuẩn). **RED-first BẮT BUỘC:** class/TC chưa tồn tại → fail → impl `_is_calibration_overdue` + thêm `next_calibration_date` vào fields-list + 2 field payload → GREEN. Đo QUA `build_asset_scan_info` (KHÔNG mock `getdate`/`nowdate` — set `next_calibration_date` thật quanh `nowdate()` để check ranh giới strict `<`). **DISTINCT với III.6.a-PMOVERDUE** (chiều hiệu chuẩn, field+signal khác).

**Acceptance — chạy XANH:** `bench --site miyano run-tests test_imm00` (`TestAssetScanInfo` baseline + `TestAssetScanInfoPmOverdue` + `TestAssetScanInfoCalibrationOverdue` mới) + `bench migrate` exit 0 + `vue-tsc` 0 lỗi + `vitest AssetScanInfoView.test.ts` GREEN. `CAP_SET_VERSION` GIỮ `v95.3388ee5629c1`.

| TC (BE) | Kịch bản | Verify | Kỹ thuật |
|---|---|---|---|
| `test_payload_has_calibration_fields_9_fields_intact` | asset bất kỳ, gọi `build_asset_scan_info` | payload CÓ key `next_calibration_date` (str\|None) + `calibration_overdue` (bool) **+ 9 field FR-00-85 GIỮ NGUYÊN** (`name, asset_code, asset_name, lifecycle_status, device_model_name, location_name, next_pm_date, recent_maintenance, pm_overdue`) — KHÔNG mất/đổi tên/đổi giá trị field | Field-whitelist (delta) |
| `test_calibration_overdue_true_when_past_date_active` | `next_calibration_date = add_days(nowdate(), -1)`, `lifecycle_status="Active"` | `calibration_overdue is True` | EP (positive) |
| `test_calibration_overdue_false_when_next_cal_null` | `next_calibration_date=None`/`""` | `calibration_overdue is False`; `next_calibration_date is None` (KHÔNG lỗi) | EP (null) |
| `test_calibration_overdue_false_when_today` | `next_calibration_date = nowdate()` | `calibration_overdue is False` (STRICT `<` — hôm nay CHƯA quá hạn) | Boundary |
| `test_calibration_overdue_false_when_future` | `next_calibration_date = add_days(nowdate(), +1)` | `calibration_overdue is False` | Boundary |
| `test_calibration_overdue_false_when_out_of_service` | `next_calibration_date` quá khứ, `lifecycle_status="Out of Service"` | `calibration_overdue is False` (status ∈ `BLOCKED_FOR_WO`) | EP (status exclude) |
| `test_calibration_overdue_false_when_decommissioned` | `next_calibration_date` quá khứ, `lifecycle_status="Decommissioned"` | `calibration_overdue is False` | EP (status exclude) |
| `test_calibration_overdue_true_when_under_repair_past_due` | `next_calibration_date` quá khứ, `lifecycle_status="Under Repair"` | `calibration_overdue is True` (chỉ `Out of Service`/`Decommissioned` bị loại) | EP (status include) |
| `test_calibration_overdue_independent_of_pm_overdue` | `next_pm_date` tương lai (pm_overdue=False) NHƯNG `next_calibration_date` quá khứ (Active) | `pm_overdue is False` ∧ `calibration_overdue is True` — 2 cờ ĐỘC LẬP, KHÔNG ảnh hưởng nhau | EP (orthogonal — non-duplicate) |
| `test_calibration_overdue_uses_server_nowdate_not_client` | so `_is_calibration_overdue` với `getdate(nowdate())` | mốc so là `nowdate()` server (timezone-safe) — KHÔNG `datetime.now()` | White-box |
| `test_scan_info_calibration_overdue_no_audit_side_effect` | gọi `get_asset_scan_info` (asset hiệu chuẩn quá hạn) N lần | KHÔNG tạo `Asset Lifecycle Event`/`IMM Audit Trail` mới (đọc cờ = read-only) | State-based (no-write) |
| `test_calibration_overdue_guard_empty_asset_returns_none` | `build_asset_scan_info("")` | trả `None` (guard rỗng GIỮ nguyên — KHÔNG raise vì calibration_overdue) | EP (guard) |

| TC (FE) | Kịch bản | Verify |
|---|---|---|
| `AssetScanInfoView.test.ts::badge_when_calibration_overdue_true` | mock `getAssetScanInfo` trả `calibration_overdue:true` | render badge "Quá hạn hiệu chuẩn" (`getByText`/2nd `role=status`); ngày `next_calibration_date` vẫn hiển thị |
| `AssetScanInfoView.test.ts::no_badge_when_calibration_overdue_false` | mock `calibration_overdue:false` | KHÔNG có text "Quá hạn hiệu chuẩn"; ngày `next_calibration_date` GIỮ NGUYÊN hiển thị |
| `AssetScanInfoView.test.ts::cal_next_date_shows_chua_len_lich_when_null` | mock `next_calibration_date:null` | dòng "Hiệu chuẩn kế tiếp" render "Chưa lên lịch" |
| `AssetScanInfoView.test.ts::cal_badge_a11y_not_color_only` | mock `calibration_overdue:true` | badge có text + `role="status"` + `aria-label` (a11y — KHÔNG chỉ dựa màu) |
| `AssetScanInfoView.test.ts::cal_no_client_date_compare` | mock `calibration_overdue:false` NHƯNG `next_calibration_date` quá khứ | KHÔNG render badge (FE KHÔNG tự so ngày — chỉ theo cờ BE) |

### III.6.b — B item 2: `regenerate_asset_qr_token` — rotate QR token (ADR-001 D1/D3/D4)

File BE: thêm class `TestRegenerateAssetQrToken` vào `assetcore/tests/test_imm00.py` (cạnh `TestAssetLabelData` / `TestGetAssetScanInfo`). FE: `frontend/src/views/asset/assetDetailQrRegenerate.test.ts` (NEW) + cập nhật `routeAccess.test.ts` (không route mới — gate ở nút). **RED-first BẮT BUỘC** (class chưa tồn tại → ImportError/AttributeError → impl → GREEN). Đo QUA layer `require` với **user THẬT** có/không `asset.write` (KHÔNG mock `require`/`has_permission` — chống false-green; baseline 116 test giữ xanh).

| TC (BE) | Kịch bản | Expect | Kỹ thuật |
|---|---|---|---|
| `test_regenerate_creates_new_token_different` | asset có `qr_token=old` → `regenerate_asset_qr_token(asset)` | `qr_token` MỚI ≠ old; URL-safe ~22 ký tự (`secrets.token_urlsafe(16)`) | EP (positive) |
| `test_regenerate_overwrites_not_idempotent` | gọi regenerate 2 lần | mỗi lần ra token KHÁC nhau (KHÔNG idempotent — đối lập `ensure_asset_qr_token`) | State (rotate≠ensure) |
| `test_regenerate_old_token_no_longer_resolves` | rotate xong | `resolve_qr_token(old)` → `None`/404; `resolve_qr_token(new)` → asset đúng | Use Case (vô hiệu hoá nhãn cũ — acceptance) |
| `test_regenerate_emits_qr_regenerated_event` | rotate có quyền | ĐÚNG **1** `Asset Lifecycle Event` `event_type='qr_regenerated'` (root_doctype/record='AC Asset'/name) | Integration (lifecycle) |
| `test_regenerate_emits_audit_no_raw_token` | rotate | ĐÚNG **1** `IMM Audit Trail`; `change_summary` nêu rotate/vô-hiệu-hoá; **KHÔNG chứa** giá trị `old`/`new` token (assert token NOT IN change_summary/notes) | Integration (no-leak audit) |
| `test_regenerate_read_only_user_403` | user có `asset.read` NHƯNG KHÔNG `asset.write` (Guest/nurse) | `PermissionError` (403); `qr_token` KHÔNG đổi; KHÔNG ghi event/audit (count trước=sau) | EP + state-based |
| `test_regenerate_write_user_200` | user có `asset.write` | 200; token đổi; 1 event + 1 audit | Use Case (positive) |
| `test_regenerate_unknown_asset_404` | asset không tồn tại | **404** `AC-E001` (KHÔNG 500, KHÔNG đoán id); KHÔNG ghi gì | Error guessing (leak-safe) |
| `test_regenerate_vendor_out_of_scope_403_no_leak` | vendor user (có asset.write), asset NGOÀI scope | **403** (`assert_vendor_can_access`); token KHÔNG đổi; KHÔNG ghi event | IDOR |
| `test_regenerate_label_reflects_new_token` | rotate xong → `get_asset_label_data(asset)` | `qr_url` chứa token MỚI (deep-link mới), KHÔNG còn token cũ | Integration (nhãn phản ánh token mới) |
| `test_regenerate_response_no_raw_token` | rotate 200 | envelope `data` = `{name, qr_url}`; **KHÔNG** field token thô | Contract (no-leak) |
| `test_regenerate_cap_set_version_unchanged` | sau khi thêm endpoint | `CAP_SET_VERSION == "v95.3388ee5629c1"` (KHÔNG cap mới) | Static (regression cap-set) |

| TC (FE) | Kịch bản | Verify |
|---|---|---|
| `assetDetailQrRegenerate.test.ts::btn_hidden_read_only` | mock caps `{asset.read:true, asset.write:false}` | nút "Sinh lại mã QR" KHÔNG render |
| `assetDetailQrRegenerate.test.ts::btn_shown_with_write` | mock caps `{asset.write:true}` | nút "Sinh lại mã QR" render |
| `assetDetailQrRegenerate.test.ts::click_opens_modal_no_confirm_no_api` | click nút | **KHÔNG** gọi `window.confirm`; mở `BaseModal` cảnh báo "vô hiệu hoá mọi nhãn QR đã in"; API **chưa** gọi |
| `assetDetailQrRegenerate.test.ts::confirm_calls_api_refetch_toast` | bấm "Xác nhận" | `regenerateAssetQrToken(id)` gọi **1 lần** đúng id; refetch asset; toast VI thành công |
| `assetDetailQrRegenerate.test.ts::cancel_noop` | bấm "Huỷ" | đóng modal; **0** API call; KHÔNG đổi gì |
| `assetDetailQrRegenerate.test.ts::error_403_no_leak` | mock API 403 | toast/alert lỗi VI; KHÔNG leak token/mã EN/raw method |

> **DoD B-2:** `bench --site miyano run-tests test_imm00` GREEN (baseline **116** + class mới); `bench migrate` sạch (enum ALE +`qr_regenerated`, KHÔNG destructive); `CAP_SET_VERSION` GIỮ `v95.3388ee5629c1`; vue-tsc 0; vitest GREEN (baseline + TC FE mới). Grep-guard: 0 occurrence token thô trong `change_summary`/`notes` của `emit_qr_regenerated`.

### III.6.c — Vòng 12 B: Rate-limit 2 endpoint QR deep-link resolve (BR-00-29) — **NEW**

File BE: thêm class `TestQrResolveRateLimit` vào `assetcore/tests/test_imm00.py` (cạnh `TestQrWhitelistHttpLayer` ~:3060). **BE-only** — FE KHÔNG đổi (vue-tsc/vitest baseline GIỮ NGUYÊN). Spec contract: [`05 §I.7a`](./05_API_Specification.md) + [`04 §II.1.8a-RL`](./04_Backend_Design.md) + [`02 BR-00-29`](./02_Analysis_Design.md).

**Cốt lõi hạ tầng test (BẮT BUỘC — nếu sai → test false-green):** `frappe.rate_limiter.rate_limit` có `if not frappe.request: return fn(...)` → gọi hàm TRỰC TIẾP (như `TestResolveQrToken`) **KHÔNG** trip limiter. Để chạm 429 phải mô phỏng HTTP context:
```python
def _http_ctx(self, cmd):
    frappe.local.request = type("R", (), {"method": "GET", "host": "miyano", "headers": {}})()
    frappe.local.request_ip = "10.0.0.99"          # IP cố định/test → bucket per-IP
    frappe.form_dict = frappe._dict({"cmd": cmd})   # cache key cần cmd → bucket per-endpoint
# teardown: xoá frappe.local.request, frappe.cache().delete_keys("rl:*") (hoặc IP/cmd duy nhất mỗi test)
```

| TC (BE) | Kịch bản | Expect | Kỹ thuật |
|---|---|---|---|
| `test_resolve_under_limit_ok` | dội ĐÚNG 30 call `resolve_qr_token` (HTTP ctx, token thật) | tất cả 200 (happy-path KHÔNG vỡ ở trần) | Boundary (≤N) |
| `test_resolve_over_limit_429` | call thứ 31 `resolve_qr_token` cùng IP/cmd/60s | `frappe.RateLimitExceededError` (⊂ `TooManyRequestsError`, HTTP **429**) | Boundary (>N) |
| `test_scan_info_over_limit_429` | call thứ 31 `get_asset_scan_info` cùng IP | 429 (endpoint thứ 2 cũng rate-limited) | Boundary |
| `test_two_endpoints_separate_buckets` | dội 30 `resolve_qr_token` (chạm trần) → 1 `get_asset_scan_info` | `get_asset_scan_info` **200** (bucket riêng, KHÔNG bị trần resolve) | EP (per-endpoint isolation) |
| `test_429_runs_before_rbac` | user KHÔNG `asset.read`, dội >30 → call vượt trần | **429** (KHÔNG 403) — RL chặn trước RBAC | Order (RL→RBAC) |
| `test_429_no_leak_payload` | vượt trần với token thật | exception 429; KHÔNG `name`/`asset_code`/payload trong message | Security (no-leak parity) |
| `test_404_calls_count_toward_limit` | dội 30 call token-SAI (404) → call 31 token-sai | call 31 → **429** (404 vẫn bị tính → chống enumeration) | Security (count-all) |
| `test_no_request_context_bypasses_limit` | gọi `resolve_qr_token` TRỰC TIẾP >30 lần (không set `frappe.local.request`) | tất cả 200/404 bình thường, KHÔNG 429 (bypass test/CLI có chủ đích) | Negative (bypass) |
| `test_label_endpoints_not_rate_limited` | dội >30 `get_asset_label_data` (HTTP ctx, asset.write user) | KHÔNG 429 (chỉ 200/403/404) — nhóm GHI KHÔNG bị rate-limit | EP (scope exclusion) |
| `test_rate_limit_constant_value` | `from assetcore.api.imm00 import AC_QR_RESOLVE_RATE_LIMIT` | `== 30` (hằng tồn tại, KHÔNG literal rải rác) | Static |
| `test_cap_set_version_unchanged` | sau khi thêm decorator | `CAP_SET_VERSION == "v95.3388ee5629c1"` | Static (regression) |

> **DoD Vòng 12 B:** `bench --site miyano run-tests test_imm00` GREEN (baseline **108+** + class `TestQrResolveRateLimit`); `bench migrate` sạch (KHÔNG schema/patch); `CAP_SET_VERSION` GIỮ `v95.3388ee5629c1`; FE KHÔNG đổi (vue-tsc/vitest baseline GIỮ NGUYÊN — BE-only). Grep-guard: hằng `AC_QR_RESOLVE_RATE_LIMIT` xuất hiện đúng 1 định nghĩa; `@rate_limit` áp đúng 2 endpoint resolve, **+1 rotate** (`regenerate_asset_qr_token` — bucket/hằng RIÊNG, §III.6.d-ROTATERL), 0 trên 3 endpoint in-nhãn. Teardown PHẢI xoá `rl:*` cache (tránh rò trần sang test khác).

### III.6.d-ROTATERL — Vòng 27 B: Rate-limit rotate `regenerate_asset_qr_token` (BR-00-38) — **NEW**

File BE: thêm class `TestQrRegenerateRateLimit` vào `assetcore/tests/test_imm00.py` (cạnh `TestQrResolveRateLimit` ~:4396, tái dùng pattern `_http_call`/`_drain`/IP-uniq/teardown `rl:`). **BE-only test** (cặp FE riêng dưới — §III.6.d-FE429). Spec contract: [`05 §III.1 regenerate_asset_qr_token` + §I.7b](./05_API_Specification.md) + [`04 §II.1.8d`](./04_Backend_Design.md) + [`02 BR-00-38`](./02_Analysis_Design.md).

**Hạ tầng test (BẮT BUỘC):** mô phỏng HTTP context (`frappe.local.request` truthy + `request_ip` per-test-uniq + `frappe.form_dict.cmd = "assetcore.api.imm00.regenerate_asset_qr_token"`); user `asset.write` (Administrator). Teardown xoá `rl:*`. Bypass test cũ (`TestRegenerateQrToken` gọi trực tiếp, không HTTP ctx) KHÔNG regress.

| TC (BE) | Kịch bản | Expect | Kỹ thuật |
|---|---|---|---|
| `test_regen_constant_value` | `from assetcore.api.imm00 import AC_QR_REGEN_RATE_LIMIT` | `== 10` (hằng RIÊNG tồn tại, KHÔNG dùng chung `AC_QR_RESOLVE_RATE_LIMIT`) | Static |
| `test_regen_constant_distinct_from_resolve` | `AC_QR_REGEN_RATE_LIMIT != AC_QR_RESOLVE_RATE_LIMIT` ∧ `AC_QR_REGEN_RATE_LIMIT < AC_QR_RESOLVE_RATE_LIMIT` | True (ngưỡng rotate THẤP hơn resolve) | Static |
| `test_regen_under_limit_ok` | dội ĐÚNG `AC_QR_REGEN_RATE_LIMIT` call rotate (HTTP ctx, asset thật, asset.write) | tất cả **200** `{name, qr_url}`, KHÔNG key `qr_token` thô (no-raw-token, regression B-2) | Boundary (≤N) |
| `test_regen_over_limit_429` | call thứ N+1 rotate cùng IP/cmd/60s | `frappe.RateLimitExceededError` (⊂ `TooManyRequestsError`, HTTP **429**) | Boundary (>N) |
| `test_regen_429_no_side_effect` | trước call vượt trần: lưu `qr_token` + count ALE `qr_regenerated` + count IMM Audit Trail của asset; gọi call vượt trần | sau 429: `qr_token` **KHÔNG đổi**; 0 ALE `qr_regenerated` MỚI; 0 IMM Audit Trail MỚI (chặn trước thân hàm) | Security (no side-effect) |
| `test_regen_429_no_leak` | vượt trần với asset thật | exception 429; message KHÔNG chứa `name`/`asset_code`/`qr_token`(cũ/mới) | Security (no-leak parity) |
| `test_regen_separate_bucket_from_resolve` | dội `AC_QR_REGEN_RATE_LIMIT` rotate (chạm trần rotate) → 1 `resolve_qr_token` cùng IP | `resolve_qr_token` **200** (bucket riêng — rotate KHÔNG bóp resolve) | EP (per-endpoint isolation) |
| `test_regen_429_runs_before_rbac` | user KHÔNG `asset.write` (chỉ read), dội >N → call vượt trần | **429** (KHÔNG 403) — RL chặn TRƯỚC `rbac.require("asset.write")` | Order (RL→RBAC) |
| `test_regen_no_request_context_bypasses` | gọi `regenerate_asset_qr_token` TRỰC TIẾP >N lần (không HTTP ctx) | KHÔNG 429 (bypass test/CLI có chủ đích) — `TestRegenerateQrToken` cũ KHÔNG regress | Negative (bypass) |
| `test_cap_set_version_unchanged` | sau khi thêm decorator | `CAP_SET_VERSION == "v95.3388ee5629c1"` | Static (regression) |

### III.6.d-FE429 — Vòng 27 B: FE map 429 → bucket VI trên rotate (FR-00-87/88) — **NEW**

File FE: `frontend/src/api/errors.test.ts` (httpStatusToCode) + `frontend/src/views/asset/assetDetailQrRegenerate.test.ts` (mở rộng — cạnh TC B-2 hiện có). Spec: [`06 §II.3e-RATELIMIT`](./06_Frontend_Design.md) + [`02 FR-00-87/88`](./02_Analysis_Design.md).

| TC (FE vitest) | Kịch bản | Expect |
|---|---|---|
| `httpStatusToCode(429) === RATE_LIMITED` | gọi `httpStatusToCode(429)` | `=== ErrorCode.RATE_LIMITED` (KHÔNG `UNKNOWN`) |
| rotate 429 → message VI | mock `regenerateAssetQrToken` reject `ApiError(code=RATE_LIMITED, httpStatus=429)` → bấm "Xác nhận" | toast hiển thị `'Bạn thao tác quá nhanh, vui lòng thử lại sau ít phút.'`; **KHÔNG** chứa "rate limit"/"Too Many"/raw-code |
| rotate 429 → modal GIỮ MỞ | sau 429 | `showRegenModal` vẫn true (modal KHÔNG đóng); `regenerating` reset false |
| rotate 403/404 GIỮ luồng cũ | mock reject `ApiError(code=FORBIDDEN, 403)` | `notify.fromError` chạy (VI verbatim BE), modal GIỮ MỞ — KHÔNG nhầm sang nhánh 429 |
| grep gate no-EN-leak | snapshot toast text trên đường 429 | 0 EN-leak, 0 raw-code |

> **DoD Vòng 27 B:** `bench --site miyano run-tests test_imm00` GREEN (baseline `TestRegenerateQrToken` + class mới `TestQrRegenerateRateLimit`, RED-first); `bench migrate` exit 0 (KHÔNG schema/cap/field/DocType/enum/patch); `CAP_SET_VERSION` GIỮ `v95.3388ee5629c1`; resolve/scan rate-limit cũ (BR-00-29) KHÔNG đổi hành vi; FE `vitest` GREEN (errors + assetDetailQrRegenerate) + `vue-tsc` 0; grep-gate: `AC_QR_REGEN_RATE_LIMIT` đúng 1 định nghĩa cạnh `AC_QR_RESOLVE_RATE_LIMIT`, `@rate_limit` áp đúng 3 endpoint (2 resolve + 1 rotate), 0 EN-leak/0 raw-code trên đường 429 FE. KHÔNG commit (working tree để user review).

### III.6.d — Vòng 14 B: Base-URL deep-link QR công khai cấu hình được (BR-00-30) — **NEW**

File BE: thêm class `TestBuildQrUrl` vào `assetcore/tests/test_imm00.py` (cạnh `TestResolveQrToken`). **BE-only** — FE KHÔNG đổi (vue-tsc/vitest baseline GIỮ NGUYÊN). Spec contract: [`04 §II.1.8-QRBASE`](./04_Backend_Design.md) + [`02 BR-00-30`](./02_Analysis_Design.md) + [`../imm-04/ADR-001-asset-qr.md`](../imm-04/ADR-001-asset-qr.md) §D2.1.

**Cốt lõi hạ tầng test:** đổi `assetcore_qr_base_url` per-test qua `frappe.conf` (vd `frappe.local.conf["assetcore_qr_base_url"] = "..."`); teardown PHẢI khôi phục/xoá key (tránh rò sang test khác). Token thật eval: `AanTF-3HT9K3dFyWyaZLNw`.

| TC (BE) | Kịch bản | Expect | Kỹ thuật |
|---|---|---|---|
| `test_build_qr_url_with_public_base` | base `https://htm.benhvien.vn` | `_build_qr_url('TOK') == 'https://htm.benhvien.vn/a/TOK'` | Happy-path |
| `test_build_qr_url_strips_trailing_slash` | base `https://htm.benhvien.vn/` (và `///`) | `... == 'https://htm.benhvien.vn/a/TOK'` (đúng 1 `/`, KHÔNG `//`) | Boundary |
| `test_build_qr_url_fallback_when_unset` | key vắng/rỗng | `_build_qr_url('TOK')` == `frappe.utils.get_url('/a/TOK')` (hành vi cũ) | Negative (fallback) |
| `test_build_qr_url_token_verbatim` | base public + token thật `AanTF-3HT9K3dFyWyaZLNw` | URL chứa token Y NGUYÊN (KHÔNG URL-encode `-`/`_`) | Regression (eval token) |
| `test_normalize_rejects_no_scheme` | base `htm.benhvien.vn` (thiếu scheme) | fallback `get_url` + log cảnh báo, KHÔNG throw | Negative (validate) |
| `test_normalize_rejects_bad_scheme` | base `ftp://htm.benhvien.vn` | fallback `get_url`, KHÔNG throw | Negative |
| `test_normalize_rejects_path_query_fragment` | `https://x/a/b`, `https://x?q=1`, `https://x#f` | fallback `get_url` (KHÔNG path/query/fragment; KHÔNG `/a/` lồng) | Negative |
| `test_normalize_rejects_whitespace` | `"https://x /y"` (có khoảng trắng) | fallback `get_url`, KHÔNG throw | Negative |
| `test_label_data_uses_build_qr_url` | `build_asset_label_data(asset)` với base public | `data['qr_url']` == `<base>/a/<token>` (consumer dùng SSoT) | Integration |
| `test_grep_single_url_gen_point` | static: `grep '/a/'` trong `services/imm00.py`+`imm04.py` | chỉ 1 điểm sinh URL (trong `_build_qr_url`) | Static (SSoT) |
| `test_cap_set_version_unchanged` | sau thay đổi | `CAP_SET_VERSION == "v95.3388ee5629c1"` | Static (regression) |

> **DoD Vòng 14 B:** `bench --site miyano run-tests test_imm00` + `test_imm04` GREEN (baseline + class `TestBuildQrUrl`); `bench migrate` exit 0 (KHÔNG schema/patch); `CAP_SET_VERSION` GIỮ `v95.3388ee5629c1`; `vue-tsc` exit 0 + `vitest` GREEN (FE KHÔNG đổi — BE-only). Grep-guard: `grep -rn '/a/' services/` → 1 điểm sinh URL (trong `_build_qr_url`); KHÔNG còn consumer tự `get_url('/a/...')`. Site_config `assetcore_qr_base_url` documented ở [`08 §II.2`](./08_Deployment.md).

### III.6.e — Vòng 17 B: SSoT sinh `qr_token` chống va chạm UNIQUE (BR-00-31 / FR-00-76..79) — **NEW**

File BE: class `TestGenerateUniqueQrToken` trong `assetcore/tests/test_imm00.py` (cạnh `TestAssetQRToken` ~:1772, ngay sau `test_backfill_patch_idempotent`). **BE-only** — FE KHÔNG đổi (vue-tsc/vitest baseline GIỮ NGUYÊN). Spec contract: [`04 §II.1.8-COLL`](./04_Backend_Design.md) + [`02 BR-00-31`](./02_Analysis_Design.md) + [`../imm-04/ADR-001-asset-qr.md`](../imm-04/ADR-001-asset-qr.md) §D1.1. **RED-first** (helper chưa tồn tại → AttributeError → impl → GREEN; đã chứng minh: RED `AttributeError: no attribute 'generate_unique_qr_token'`).

**Cốt lõi hạ tầng test (BẮT BUỘC — nếu sai → test false-green):** mô phỏng va chạm bằng monkeypatch (`svc.generate_qr_token = _fake`) lên `assetcore.services.imm00.generate_qr_token` (KHÔNG patch `generate_unique_qr_token` — nó là cái-đang-test) trả side-effect = [token-đã-tồn-tại-ở-DB, token-mới-unique] → chứng minh helper retry. Token-đã-tồn-tại là `qr_token` của 1 asset SEED THẬT trong DB. Teardown: `frappe.db.rollback()` + `_purge_asset` từng asset + commit. KHÔNG patch `frappe.db.exists` (đo qua DB thật — chống false-green).

| TC (BE) — tên THẬT đã implement | Kịch bản | Expect | Kỹ thuật |
|---|---|---|---|
| `test_generate_unique_qr_token_retries_on_collision` | patch `generate_qr_token` → [`<token seed>`, `<token mới>`] → `generate_unique_qr_token()` | trả `<token mới>` (unique); gọi `generate_qr_token` đúng 2 lần; KHÔNG raise; KHÔNG IntegrityError; KHÔNG ghi DB | Use Case (retry thành công) |
| `test_generate_unique_qr_token_no_collision_single_call` | token đầu unique | trả ngay; gọi `generate_qr_token` đúng 1 lần (no wasted retry) | EP (happy-path) |
| `test_generate_unique_qr_token_exhausts_retry_raises` | patch `generate_qr_token` luôn trả token-đã-tồn-tại | `frappe.ValidationError` (qua `frappe.throw`, message VI); **KHÔNG** `IntegrityError`/500 thô; KHÔNG loop vô hạn; gọi đúng `_MAX_QR_TOKEN_RETRY` lần | Boundary (cạn retry) |
| `test_generate_unique_qr_token_respects_exclude` | `generate_unique_qr_token(exclude="OLD")` patch trả [OLD, NEW] | trả NEW (≠ OLD) kể cả khi DB chưa có OLD (cho rotate) | EP (exclude guard) |
| `test_before_insert_token_unique_after_collision` | patch [`<token seed>`, `<token mới>`]; tạo AC Asset mới (before_insert) | asset INSERT THÀNH CÔNG; `qr_token` = `<token mới>` unique; INSERT KHÔNG bị abort bởi lỗi DB thô | Use Case (insert hardening — acceptance) |
| `test_ensure_asset_qr_token_collision_safe` | asset token-less + collision lần đầu → `ensure_asset_qr_token`; rồi asset đã-có-token | (1) trả token unique; (2) idempotent: đã có token → KHÔNG gọi `generate_unique_qr_token` (spy False), KHÔNG emit `qr_generated` lần 2 (count trước=sau) | Use Case + State (idempotency GIỮ) |
| `test_regenerate_collision_with_other_asset` | asset A token=old; asset B token=X; patch [X, new] → `regenerate_asset_qr_token(A)` | A.qr_token = `new` (≠ old ∧ ≠ X); unique toàn bảng; KHÔNG đụng UNIQUE; emit `qr_regenerated` đúng 1 lần | Use Case (rotate guard cả old cả asset khác — acceptance) |
| `test_backfill_patch_delegates_unique_helper` | patch 008 sau collision lần đầu (monkeypatch [`<token seed>`, `<token mới>`]); asset legacy token-less | backfill token unique cho legacy qua helper; re-run patch = no-op (idempotent, 0 asset trống) | Integration (patch delegate SSoT) |

> **DoD Vòng 17 B (ĐẠT 2026-06-05):** `bench --site miyano run-tests test_imm00` GREEN (**157** tests — 148 baseline + 9 class `TestGenerateUniqueQrToken`); baseline QR class (`TestAssetQRToken`/`TestResolveQrToken`/`TestBuildQrUrl`) GIỮ XANH (`test_qr_token_unique_constraint`, `test_backfill_patch_idempotent` PASS); `bench migrate` exit 0 (KHÔNG schema/patch mới — patch 008 chỉ đổi import+thân, vẫn idempotent re-run=no-op); `CAP_SET_VERSION` GIỮ `v95.3388ee5629c1`; FE KHÔNG đổi (BE-only — 0 file `frontend/`). Grep-guard: `grep -rn 'generate_qr_token()' assetcore/` → 0 gọi trần ở đường ghi (`ac_asset.py`/`services/imm00.py` ensure+regenerate/`patches/v3_2/008`), chỉ trong thân `generate_unique_qr_token` (line 149). ⚠️ Pitfall đã bắt (RED): loop dùng biến `_attempt`, KHÔNG `_` — `for _ in range(...)` shadow gettext `_` → `TypeError: 'int' object is not callable` ở `frappe.throw(_(...))`.

### III.6.f — Vòng 21 B: Open-redirect safety trên login deep-link (BR-00-32) — **NEW**

File FE: helper `frontend/src/utils/navigation.ts::isSafeInternalRedirect` (NEW export, thuần) + block redirect-safety trong `frontend/src/views/auth/LoginView.test.ts`. **FE-only** — KHÔNG đổi BE/DocType/route/schema/patch; `bench`/`test_imm00` baseline KHÔNG đụng. Spec contract: [`06 §II.4c`](./06_Frontend_Design.md) + [`02 BR-00-32`](./02_Analysis_Design.md). **RED-first** (helper chưa tồn tại → import fail / assert đỏ → impl → GREEN).

**Cốt lõi hạ tầng test:** unit-test helper thuần KHÔNG cần DOM (gọi `isSafeInternalRedirect(raw)` trực tiếp → boolean). Test LoginView 2 call-site: (a) **onMounted đã-auth** — mount với `auth.isAuthenticated=true` + `route.query.redirect=<payload>` → assert `router.push` nhận `/dashboard` (REJECT) hoặc payload (ACCEPT); (b) **sau-login-OK** — mock `auth.login()→true` + `route.query.redirect=<payload>` → submit → assert `router.push` đích đúng. Mock `useRoute`/`useRouter` (pattern hiện có trong `LoginView.test.ts`).

| TC (FE) | Kịch bản | Expect | Kỹ thuật |
|---|---|---|---|
| `redirect_helper_accepts_internal_single_slash` | `isSafeInternalRedirect` cho `/dashboard`, `/a/TOK`, `/assets/AC-ASSET-2026-00001/info` | `true` (single-leading-slash) | EP (ACCEPT) |
| `redirect_helper_rejects_protocol_relative` | `//evil.com` | `false` | Boundary (`//`) |
| `redirect_helper_rejects_absolute` | `https://x.com`, `http://x.com` | `false` | Negative (scheme) |
| `redirect_helper_rejects_js_scheme` | `javascript:alert(1)` | `false` | Negative (XSS scheme) |
| `redirect_helper_rejects_backslash` | `\evil.com`, `/\evil` | `false` | Negative (backslash ≡ `/`) |
| `redirect_helper_rejects_whitespace_prefix` | ` //evil`, `\t//evil` | `false` | Boundary (control/whitespace) |
| `redirect_helper_rejects_non_slash_and_nonstring` | `evil.com`, ``, `undefined`, `['/a','/b']` | `false` | Negative (không single-`/` / không-string) |
| `LV-FE-08: onMounted đã-auth + redirect ngoài → push /dashboard` | `isAuthenticated=true`, `query.redirect='https://evil.com'` | `router.push('/dashboard')` (KHÔNG push evil) | Use Case (call-site 1) |
| `LV-FE-08b: onMounted đã-auth + redirect nội bộ → push y nguyên` | `isAuthenticated=true`, `query.redirect='/a/TOK'` | `router.push('/a/TOK')` (QR deep-link GIỮ) | Use Case (no-regression ADR-001 D4) |
| `LV-FE-09: sau login OK + redirect ngoài → push /dashboard` | `login→true`, `query.redirect='//evil.com'` | `router.push('/dashboard')` | Use Case (call-site 2) |
| `LV-FE-09b: sau login OK + redirect nội bộ → push y nguyên` | `login→true`, `query.redirect='/incidents'` | `router.push('/incidents')` (LV-FE-07b GIỮ) | Use Case (no-regression) |
| `redirect_grep_guard_no_raw_push` | static: `grep` FE | 0 chỗ `router.push(<route.query.redirect>)` không qua helper | Static (SSoT) |

> **DoD Vòng 21 B:** `vitest` full GREEN (block redirect-safety mới + LV-FE-01..07b baseline GIỮ XANH); `vue-tsc` app exit 0; eslint 0 error trên file chạm (`navigation.ts`, `LoginView.vue`, `LoginView.test.ts`); FE-only (0 file BE/DocType/route/schema/patch); `CAP_SET_VERSION` GIỮ `v95.3388ee5629c1`. Grep-guard: `grep -rn 'query.redirect' frontend/src` → mọi consume qua `isSafeInternalRedirect`. QR deep-link ADR-001 D4 (`/a/<token>`, `/assets/:id/info`) KHÔNG hồi quy (ACCEPT).

### III.6.g — Vòng 24 B: No-raw-token parity trên đường ĐỌC AC Asset (BR-00-34 / ADR-001 §D4.1) — **NEW** {#guard-no-raw-token}

File BE: thêm class `TestAssetReadNoRawToken` vào `assetcore/tests/test_imm00.py` (cạnh `TestAssetQRToken`/`TestResolveQrToken` — nhóm QR). **BE-only** — FE KHÔNG đổi (vue-tsc/vitest baseline GIỮ NGUYÊN; 0 FE đọc field `data.qr_token` từ payload đọc-asset). Spec contract: [`04 §II.1.8-NORAWTOKEN`](./04_Backend_Design.md) + [`05 §get_asset`](./05_API_Specification.md) + [`02 BR-00-34`](./02_Analysis_Design.md) + [`../imm-04/ADR-001-asset-qr.md`](../imm-04/ADR-001-asset-qr.md) §D4.1. **RED-first BẮT BUỘC** (assert `'qr_token' not in data` ĐỎ trước khi strip → impl `doc.pop("qr_token", None)` → GREEN).

**Cốt lõi hạ tầng test (BẮT BUỘC — nếu sai → test false-green):** seed 1 AC Asset THẬT (có `qr_token` đã sinh qua `before_insert`/`ensure_asset_qr_token`) → gọi endpoint QUA layer thật (user có `asset.read`; KHÔNG mock `frappe.get_doc`/`require`/`has_permission`) → đọc `res["data"]` từ envelope → assert key `qr_token`/`token` vắng + các field nghiệp vụ CÒN đủ. Teardown: `_purge_asset` + `frappe.db.rollback()`. Guard test (TC cuối) đọc AST của `assetcore/api/imm00.py` (và `api/*.py`) bằng `ast.parse` → walk tìm vi phạm — KHÔNG cần DB/HTTP.

| TC (BE) | Kịch bản | Expect | Kỹ thuật |
|---|---|---|---|
| `test_get_asset_strips_qr_token` | seed asset có token → `get_asset(name)` | `'qr_token' not in data` ∧ `'token' not in data` | EP (acceptance cốt lõi) |
| `test_get_asset_keeps_business_fields` | cùng asset → `get_asset(name)` | `data` CÒN đủ `name`, `asset_code`, `lifecycle_status`, `device_model_name`, `location_name`, `category_name`, `supplier_name`, `responsible_technician_name` (enrich KHÔNG mất) | Use Case (FE AssetDetail không thiếu data) |
| `test_get_asset_timeline_no_token` | seed asset + ≥1 lifecycle event → `get_asset_timeline(name)` | mỗi item ∧ payload `'qr_token' not in …` ∧ `'token' not in …` (parity tự nhiên) | EP (parity) |
| `test_get_asset_kpi_no_token` | seed asset → `get_asset_kpi(name)` | `'qr_token' not in data` ∧ `'token' not in data`; KPI field (`uptime_pct`,`mtbf_days`,…) GIỮ | EP (parity) |
| `test_readonly_qr_endpoints_no_token_parity` | `resolve_qr_token`/`get_asset_scan_info`/`get_asset_label_data` (đã whitelist) | KHÔNG có `qr_token`/`token` trong data (regression — đồng nhất rule 9/A6) | Regression (parity toàn cụm) |
| `test_get_asset_rbac_idor_404_unchanged` | (a) user KHÔNG `asset.read` → 403; (b) vendor ngoài scope → 403 IDOR; (c) name không tồn tại → 404 `AC-E001` | gate GIỮ NGUYÊN (B-24 chỉ strip token) | Regression (no-regression RBAC/IDOR/404) |
| `test_ast_guard_no_raw_token_asset_read` | static: AST `assetcore/api/imm00.py` (+ `api/*.py`) | 0 hàm trả `get_doc(_DT_ASSET/"AC Asset", …).as_dict()` mà KHÔNG `pop("qr_token")`/strip cùng hàm (chống regress endpoint asset-read mới) | Static (Grep/AST guard) |

> **DoD Vòng 24 B:** `bench --site miyano run-tests test_imm00` GREEN (baseline + class `TestAssetReadNoRawToken`); baseline QR class (`TestAssetQRToken`/`TestResolveQrToken`/`TestBuildQrUrl`/`TestGenerateUniqueQrToken`/`TestAssetLabelData`/`TestGetAssetScanInfo`/`TestRegenerateAssetQrToken`) GIỮ XANH; `bench migrate` exit 0 (KHÔNG schema/patch mới — thuần strip + guard test); `CAP_SET_VERSION` GIỮ `v95.3388ee5629c1`; FE KHÔNG đổi (BE-only — 0 file `frontend/`; `vue-tsc` exit 0 + `vitest` GREEN baseline; 0 FE đọc field `data.qr_token` từ payload đọc-asset → `AssetDetailView` KHÔNG vỡ). Grep-guard bổ trợ AST: `grep -n 'as_dict()' assetcore/api/imm00.py` → mọi `get_doc(_DT_ASSET).as_dict()` đi kèm `pop("qr_token")`. KHÔNG commit (working tree để user review).

### III.6.h — Vòng 25 B: Reserved test-prefix exclusion ở `list_assets` + count SSoT (BR-00-35 / FR-00-80..83) — **NEW** {#guard-test-prefix}

File BE: thêm class `TestReservedTestPrefixExclusion` vào `assetcore/tests/test_imm00.py` (cạnh `TestListAssetsGmdnFilter` — nhóm list/count). **BE-only** — FE list/count tự hưởng lợi, KHÔNG đổi component (vue-tsc/vitest baseline GIỮ NGUYÊN). Spec contract: [`04 §II.1.13-TESTPREFIX`](./04_Backend_Design.md) + [`05 §list_assets`](./05_API_Specification.md) + [`02 BR-00-35 / FR-00-80..83`](./02_Analysis_Design.md). **RED-first BẮT BUỘC** (seed `_Test*`/`SI-*` → assert chúng VẮNG khỏi `items` + `total` ĐỎ trước khi áp predicate → impl → GREEN).

**Cốt lõi hạ tầng test (BẮT BUỘC — nếu sai → test false-green):** seed dataset HỖN HỢP record THẬT trong cùng transaction: (a) **phải-ẩn**: ≥1 asset `asset_name='_Test Máy thở'`, ≥1 `asset_name='_Probe X'`, ≥1 có `name` series `SI-…` (set name tường minh để khớp `'SI-%'`); (b) **phải-giữ**: `asset_name='Máy thở'`, `asset_name='Model_X'` (`_` ở GIỮA — false-positive guard), `name` kiểu `TS-2025-USG-001`/`AC-ASSET-…`. Gọi endpoint QUA layer thật (KHÔNG mock `get_list`/`db.count`/`db.sql`). Teardown qua `tests/_asset_cleanup.py` + `frappe.db.rollback()`. **Đo INVARIANT trên CÙNG data** (không mock count) để bắt lệch list↔count.

| TC (BE) | Kịch bản | Expect | Kỹ thuật |
|---|---|---|---|
| `test_list_excludes_underscore_prefix` | seed `_Test*`/`_Probe*` + asset thường → `list_assets(page_size lớn)` | 0 item có `asset_name` bắt đầu `_`; asset thường CÓ mặt | EP (acceptance cốt lõi) |
| `test_list_excludes_si_name_prefix` | seed asset `name` `SI-…` → `list_assets` | 0 item có `name` bắt đầu `SI-` | EP (acceptance cốt lõi) |
| `test_no_false_positive_underscore_middle` | seed `Model_X` (`_` GIỮA) + `TS-2025-USG-001` + `Máy thở` → `list_assets` | CẢ 3 CÓ mặt đầy đủ (KHÔNG ẩn nhầm) | Boundary (0 false-positive, FR-00-83) |
| `test_total_equals_len_items_non_search` | dataset hỗn hợp, KHÔNG search, page đủ chứa → `list_assets()` | `pagination.total == len(items)` (non-search count #2 == list #1) | Integration (INVARIANT) |
| `test_total_equals_len_items_search` | `list_assets(search=<substr khớp cả asset thật lẫn _Test>)` page đủ chứa | `pagination.total == len(items)`; 0 row `_`/`SI-` dù khớp substring search | Integration (INVARIANT, search raw-count #3) |
| `test_overview_total_excludes_test_prefix` | dataset hỗn hợp → `dashboard.get_overview()` | `data.assets.total` == `list_assets()` `pagination.total` (không-filter); KHÔNG đếm `_Test*`/`SI-*` (nguồn #4) | Integration (parity dashboard↔list) |
| `test_predicate_escape_safe_literal_underscore` | đo trực tiếp `reserved_test_prefix_sql()` + 1 query thật: seed `Model_X` vs `_X` | `Model_X` GIỮ, `_X` ẨN (chứng minh `_` là LITERAL ở `'\_%'`, KHÔNG wildcard 1-ký-tự) | Boundary (escape-safe) |
| `test_grep_guard_single_ssot_predicate` | static: grep `assetcore/api` + `assetcore/services` | literal `'\_%'`/`'_%'`/`'SI-%'` chỉ trong thân `reserved_prefix_sql` (0 lặp ngoài helper) | Static (Grep guard 1-SSoT) |

#### III.6.h-VENDORCLOBBER — Vòng 26 B: vendor-scope KHÔNG bị reserved-exclusion clobber (RC-LIST-VENDORCLOBBER / FR-00-84 / BR-00-35 mục 6) — **NEW (ƯU TIÊN)**

File BE: thêm class `TestListAssetsVendorScopeReserved` vào `assetcore/tests/test_imm00.py` (HOẶC vào `tests/test_imm00_reserved_prefix.py` cạnh `_SeedMixin`). **RED-first BẮT BUỘC:** trên code hiện tại (`filters.update(reserved_prefix_filter())` clobber) — `test_vendor_sees_only_assigned_minus_reserved` PHẢI ĐỎ (vendor thấy asset ngoài-scope) trước khi fix → fix điểm merge (filter-list form) → GREEN. Spec contract: [`04 §II.1.13-TESTPREFIX RC-LIST-VENDORCLOBBER`](./04_Backend_Design.md) + [`02 FR-00-84 / BR-00-35`](./02_Analysis_Design.md) + [`05 §list_assets`](./05_API_Specification.md).

**Hạ tầng test (BẮT BUỘC — giả-lập Vendor Engineer mà KHÔNG cần login/DocPerm phức tạp):**
- **Mock `frappe.get_roles`** trả `["Vendor Engineer"]` (KHÔNG kèm bypass-role `AssetCore Super Admin`/`Auditor`/`System Manager`) cho user test → `apply_vendor_scope` đi nhánh vendor (chèn `name in assigned`). Dùng `unittest.mock.patch("frappe.get_roles", ...)` HOẶC monkeypatch `frappe.session.user` sang user có đúng role Vendor Engineer (KHÔNG bypass). Vì `reserved_prefix_filter` query DB bằng `ignore_permissions` nội bộ helper → mock role là đủ để kích `apply_vendor_scope`.
- **Seed 3 nhóm asset THẬT (cùng transaction, teardown qua `_asset_cleanup.purge_asset`):**
  1. **assigned-thật** (≥1): asset `asset_name` THƯỜNG (vd `Máy thở VS`), gắn user test qua **PM Work Order `assigned_to=<user>`** (HOẶC `Asset Repair.assigned_to`) — `_resolve_vendor_assigned_assets` đọc 2 bảng này (`scope.py:112-122`). → PHẢI có trong kết quả.
  2. **assigned-reserved** (≥1): asset gán user test (PM WO `assigned_to`) NHƯNG `asset_name` bắt đầu `_` (vd `_TestVendorScope`) HOẶC `name` series `SI-…`. → bị loại bởi reserved-exclusion DÙ được giao → PHẢI VẮNG.
  3. **ngoài-scope** (≥1): asset `asset_name` THƯỜNG, KHÔNG gán user test. → PHẢI VẮNG (vendor isolation).

| TC (BE) | Kịch bản | Expect | Kỹ thuật |
|---|---|---|---|
| `test_vendor_sees_only_assigned_minus_reserved` | mock role Vendor Engineer + 3 nhóm seed → `list_assets(page_size lớn)` | `result_names ⊆ {assigned}` ∧ `result_names ∩ {reserved} = ∅`; assigned-thật CÓ; assigned-reserved VẮNG; ngoài-scope VẮNG. Cụ thể đề mục: được giao 1 asset thật + 1 reserved (`_TestVendorScope`) → list trả đúng 1 asset thật, 0 reserved | EP (acceptance cốt lõi — RED trên code clobber) |
| `test_vendor_invariant_total_equals_len` | như trên, page đủ chứa → `list_assets()` | `pagination.total == len(items)` (non-search count + get_list cùng predicate dưới vendor-scope) | Integration (INVARIANT vendor persona) |
| `test_vendor_invariant_total_equals_len_search` | mock role + `list_assets(search=<substr khớp cả assigned-thật lẫn ngoài-scope>)` | `total == len(items)`; 0 ngoài-scope/reserved dù khớp search (search raw-count #3 AND scope) | Integration (INVARIANT search + scope) |
| `test_vendor_empty_scope_returns_zero` | mock role Vendor Engineer + user KHÔNG có WO/Repair nào → `list_assets()` | `items == []` ∧ `total == 0` (sentinel `__none__` AND reserved-exclusion → tập rỗng, KHÔNG fallback toàn bộ asset) | Boundary (empty-scope, FR-00-84) |
| `test_admin_invariant_unchanged` | KHÔNG mock (Administrator/bypass) → `list_assets()` + dataset reserved | baseline GIỮ: `total == len(items)`, reserved VẮNG, mọi asset thường CÓ (scope no-op) | Regression (admin persona INVARIANT) |
| `test_depreciation_endpoints_no_regress` | `list_assets_depreciation()` + `get_depreciation_stats()` (KHÔNG vendor-scope, base filter không có key `name`) | reserved VẪN bị loại; `INV-DEP-5` count==drill GIỮ; hành vi KHÔNG đổi (chứng minh `filters.update(reserved_prefix_filter())` an toàn ở 2 endpoint này) | Regression (no-regress depreciation) |
| `test_helpers_not_renamed` | static/import: `from assetcore.services.imm00 import reserved_prefix_sql, reserved_prefix_filter, reserved_asset_names` | import OK (3 tên GIỮ NGUYÊN — 0 rename); `reserved_prefix_filter()` trả `{}` hoặc `{"name": ["not in", [...]]}` | Static (contract-lock tên helper) |

> **DoD Vòng 26 B (RC-LIST-VENDORCLOBBER):** `bench --site miyano run-tests test_imm00` + `bench --site miyano run-tests test_imm00_reserved_prefix` GREEN (baseline + class mới); RED đã prove (clobber → vendor thấy ngoài-scope ĐỎ trước fix); `result ⊆ assigned ∧ result ∩ reserved = ∅`; empty-scope → 0 row; INVARIANT `total == len(items)` cho CẢ Administrator lẫn Vendor Engineer (non-search + search); 2 endpoint depreciation no-regress; 3 helper SSoT KHÔNG rename; `bench migrate` exit 0; cap-set GIỮ `v95.3388ee5629c1` (0 schema/field/DocType/enum/patch delta — fix chỉ ở điểm MERGE trong `list_assets`); FE KHÔNG đổi (BE-only). KHÔNG commit (working tree để user review).

> **DoD Vòng 25 B:** `bench --site miyano run-tests test_imm00` GREEN (baseline + class `TestReservedTestPrefixExclusion`); `TestListAssetsGmdnFilter` + baseline list/count GIỮ XANH; INVARIANT `total == len(items)` đo trên data thật (3 nguồn count == list); 0 false-positive (`Model_X`/`TS-…`/`AC-ASSET-…` hiện đủ); grep-guard 1-SSoT pass; `bench migrate` exit 0 (KHÔNG schema/cap/field/DocType/enum/patch delta — thuần helper + 4 wiring + test); `CAP_SET_VERSION` GIỮ `v95.3388ee5629c1`; FE list/count tự hưởng lợi, KHÔNG đổi component (`vue-tsc` exit 0 + `vitest` GREEN baseline). KHÔNG commit (working tree để user review).

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
| FR-00-80..83 | reserved test-prefix exclusion + count SSoT + INVARIANT total==len(items) + 0 false-positive | `TestReservedTestPrefixExclusion::*` (III.6.h) | EP + Boundary + Integration(invariant) + Static(grep) | ⬜ Planned (RED-first) |
| FR-00-84 | vendor-scope (AUTH-01) + reserved-exclusion compose AND trên field `name` — KHÔNG clobber; empty-scope→0; INVARIANT mọi persona; depreciation no-regress; 0 rename helper | `TestListAssetsVendorScopeReserved::*` (III.6.h-VENDORCLOBBER) | EP + Boundary(empty-scope) + Integration(INVARIANT vendor+admin) + Regression(depreciation) + Static(helper-name) | ⬜ Planned (RED-first, ƯU TIÊN) |

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
| BR-00-35 (mục 1-5) | reserved test-prefix exclusion (RC-LIST-TESTPREFIX): list+3 count SSoT escape-safe `'\_%' ESCAPE '\\'`/`'SI-%'` + INVARIANT total==len(items) + 0 false-positive (`Model_X`/`TS-`/`AC-ASSET-` giữ) + grep-guard 1-SSoT | `TestReservedTestPrefixExclusion::*` (III.6.h) | EP + Boundary(escape-safe) + Integration(invariant) + Static(grep) | ⬜ Planned (RED-first) |
| BR-00-35 (mục 6) | vendor-scope + reserved compose AND trên field `name` KHÔNG clobber (RC-LIST-VENDORCLOBBER, Vòng 26 B): filter-list form, `result ⊆ assigned ∧ ∩ reserved=∅`, empty-scope→0, INVARIANT mọi persona, depreciation no-regress, 0 rename | `TestListAssetsVendorScopeReserved::*` (III.6.h-VENDORCLOBBER) | EP + Boundary(empty-scope) + Integration(INVARIANT vendor+admin) + Regression(vendor isolation + depreciation) + Static(helper-name) | ⬜ Planned (RED-first, ƯU TIÊN) |

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
