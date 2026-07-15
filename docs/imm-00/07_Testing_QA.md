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
| 25 | AC Asset permission query (Vendor isolated; KTV nội bộ read-all — ADR-IMM00-LIST-SCOPE) | Permission hook | `permissions.py::ac_asset_query` + `ac_asset_has_permission`; INVARIANT `count==rows` | Integration (RBAC isolation) |
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
| FR-00-89 | **Hard-cap `page_size [1,100]` ở 11 list-endpoint imm00 (BR-00-39, factory vòng 5)** — SSoT `clamp_page_size()`+`MAX_PAGE_SIZE` | `page_size=100000`→`len(items)<=100` ∧ `pagination.page_size==100`; `<=0`→`>=1`; `<=100` giữ nguyên; non-int→`ValueError`; `list_assets` count==drill GIỮ; no field-leak; 1 SSoT (no literal 100 rải rác); EXCLUDE depreciation | API + BVA(boundary) + Regression + grep-guard |
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
| BR-00-39 | Hard-cap `page_size [1,100]` ở 11 list-endpoint imm00 (RC-LIST-PAGESIZE): SSoT `clamp_page_size()`; `page_size>100`→limit thực+metadata=100; `<=0`→1; `<=100` giữ nguyên; non-int→`ValueError` (no nuốt lỗi); `list_assets` count==drill/count==rows giữ (clamp chỉ đụng `limit_page_length`); no field-leak; no literal 100 rải rác; EXCLUDE `list_assets_depreciation` | `utils/pagination.py::clamp_page_size()` + 11 endpoint `api/imm00.py` | BVA(boundary 0/1/100/100000) + API(parity 11 endpoint) + Regression(count==drill) + grep-guard(1 SSoT) |

#### TC cho BR-00-39 — hard-cap `page_size [1,100]` (factory vòng 5)
> File: bổ sung class `TestListPageSizeCap` vào `assetcore/tests/test_imm00.py` (chạy `bench --site miyano run-tests --module assetcore.tests.test_imm00`). Verify logic-level, fresh-import — KHÔNG cần reload gunicorn / KHÔNG bench migrate / KHÔNG tuyên bố verify HTTP/Playwright live (STALE-WORKER gate).

| TC | Request | Expected | Kỹ thuật | AC |
|---|---|---|---|---|
| TC-00-PS-01 | `list_assets(page=1, page_size=100000)` (≥101 asset trong DB) | `len(resp['data']['items']) <= 100` **VÀ** `resp['data']['pagination']['page_size'] == 100` (metadata == limit thực) | BVA (vượt cap) | AC1 |
| TC-00-PS-02 | MỖI endpoint trong 11 (`list_assets`/`get_asset_timeline`/`list_lifecycle_events`/`list_suppliers`/`list_device_models`/`list_audit_trail`/`list_capas`/`list_overdue_capas`/`list_incidents`/`list_transfers`/`list_service_contracts`) với `page_size=100000` | `len(items) <= 100` ∧ `pagination.page_size == 100` (parity toàn module) | API (parity) | AC2 |
| TC-00-PS-03 | `page_size=0` và `page_size=-5` | clamp về `>= 1` (`pagination.page_size == 1`, KHÔNG 0/âm → KHÔNG trả 0 row sai) | BVA (biên dưới) | AC3 |
| TC-00-PS-04 | `page_size=20` (hợp lệ) | giữ NGUYÊN 20 (KHÔNG regress trang nhỏ); `len(items) <= 20` | BVA (no-regress) | AC3 |
| TC-00-PS-05 | `page_size='abc'` (non-int) | raise `ValueError` (giữ hành vi cũ — KHÔNG nuốt lỗi thầm, KHÔNG trả envelope 200) | Error guessing | AC3 |
| TC-00-PS-06 | `list_assets(page_size=100000)` đủ data ở trang | `len(items) == pagination.page_size` (==100) ∧ `<= 100` | INVARIANT | AC4 |
| TC-00-PS-07 | `list_assets` count==drill / count==rows hiện có (vendor + KTV nội bộ) | KHÔNG regress sau fix — clamp KHÔNG đụng `filters`/`or_filters`/`permission_query_conditions` (suite ADR-IMM00-LIST-SCOPE GIỮ XANH) | Regression (invariant) | AC4 |
| TC-00-PS-08 | `test_list_assets_no_qr_token` (hiện có) | GIỮ XANH — fix KHÔNG thêm field-select | Regression (no-leak) | AC6 |
| TC-00-PS-09 | grep `grep -n "min(.*100\|100)" assetcore/api/imm00.py` (loại comment) | literal cap `100` chỉ ở `utils/pagination.py` (`MAX_PAGE_SIZE`) — KHÔNG copy-paste rải rác trong api | grep-guard (1 SSoT) | AC2 |

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
| `transition_status` authz 3-lớp (`asset.write`+IDOR) | `api/imm00.transition_status` | 403 cap / 403 vendor / 403-not-404 / happy | EP + security | ⬜ Planned (xem §III.6.0e-TRANSITIONAUTHZ) |
| `verify_chain` | `api/imm00.verify_chain` | `{verified, count, last_hash}` | Use Case | ⬜ Planned |

### III.6.0b — D6 (EXECUTED Vòng 3): TÁCH cap in/rotate `asset.print` + `asset.qr.rotate` (ADR-IMM00-QR-SCAN-ACTION)

File BE: class `TestLabelWriteCapability` + `TestRegenerateQrToken` (`assetcore/tests/test_imm00.py`). **D6 RECONCILE:** in nhãn gate `asset.write`→**`asset.print`** (DocPerm print=1 sẵn cho persona vận hành → in được); rotate gate `asset.write`→**`asset.qr.rotate`** (=write, chỉ Super Admin/được cấp). Đo QUA layer `require` với **user THẬT** (KHÔNG mock `require`/`has_permission` → tránh false-green; luật skill).

**Acceptance — ĐÃ XANH (2026-06-08):** `bench --site miyano run-tests test_imm00` (254 OK) + `test_rbac` (53 OK); `bench migrate` sạch; **cap-set version `v95.3388ee5629c1` → `v97.c30c69b8974d`** (thêm 2 cap); `vue-tsc` 0; `vitest` 941 OK. Toàn bộ test cũ xanh (regression).

| TC (BE) | Kịch bản (user THẬT, qua layer `require`) | Verify | Kỹ thuật |
|---|---|---|---|
| `test_label_data_print_user_200` | user CÓ `asset.print` NHƯNG KHÔNG `asset.write` (Commissioning User: read=1,write=0,print=1) gọi `get_asset_label_data` | **200**, payload đủ 8 key (KHÔNG 403) | Use Case (D6 positive) |
| `test_label_batch_print_user_200` | cùng user gọi `get_asset_label_data_batch([a])` | **200** | Use Case |
| `test_mark_printed_print_user_200` | cùng user gọi `mark_label_printed([a])` | **200**; ĐÚNG 1 `label_printed` + 1 audit | Use Case + state-based |
| `test_label_data_no_print_user_403` | user KHÔNG `asset.print` (Guest) gọi `get_asset_label_data` | `PermissionError` (403) VI sạch | EP (least-privilege) |
| `test_mark_printed_no_print_user_403_no_side_effect` | Guest gọi `mark_label_printed([a])` | 403; KHÔNG ghi `label_printed`/audit (count trước=sau) | EP + state-based |
| `test_label_data_write_user_200` | Super Admin (print=1+write=1) gọi `get_asset_label_data` | 200, 8 key | Use Case |
| `test_readonly_qr_endpoints_keep_asset_read` | user print (read=1) gọi `resolve_qr_token`/`get_asset_scan_info`/`get_asset` | 200 (read-only GIỮ `asset.read`) | Regression (negative-scope) |
| `test_label_idor_unchanged_after_print_gate` | user CÓ `asset.print` (Vendor Engineer) NHƯNG vendor ngoài scope | **403 IDOR** — đổi gate KHÔNG nới IDOR | IDOR (regression) |
| `test_regenerate_print_only_user_403` | user CÓ `asset.print` NHƯNG KHÔNG `asset.qr.rotate` gọi rotate | **403**; qr_token KHÔNG đổi (no side-effect) | EP (tách quyền) |
| `test_regenerate_write_user_200_new_token` | user `asset.qr.rotate` (write=1) gọi rotate | 200; token mới ≠ cũ; no-raw-token | Use Case |
| `test_cap_set_version_changed_after_split_caps` | sau `bench migrate` | `CAP_SET_VERSION == "v97.c30c69b8974d"` (≠ v95…); `asset.print`→(AC Asset,"print"); `asset.qr.rotate`→(AC Asset,"write") ∈ CAPABILITY_MAP; KHÔNG `asset.print_label` | White-box (version guard) |

> **KHÔNG test false-green:** test tạo user thật + cấp/không-cấp DocPerm `print`/`write` trên `AC Asset` (qua Role/Custom DocPerm), `frappe.set_user(...)`, rồi gọi endpoint. KHÔNG `monkeypatch rbac.require`/`frappe.has_permission`. Gate đi đúng đường `require("asset.print")`/`require("asset.qr.rotate")` → `can` → `frappe.has_permission("AC Asset", permtype)`.

| TC (FE) | Kịch bản | Verify |
|---|---|---|
| `assetDetailQrPrint.test.ts` (D6) | mock caps `{asset.read:true}` (KHÔNG print) | nút "In nhãn QR" KHÔNG render |
| `assetDetailQrPrint.test.ts` (D6) | mock caps `{asset.print:true}` | nút "In nhãn QR" render |
| `assetDetailQrRegenerate.test.ts` (D6) | mock caps `{asset.print:true}` (KHÔNG rotate) | nút "Sinh lại mã QR" KHÔNG render (tách quyền) |
| `assetDetailQrRegenerate.test.ts` (D6) | mock caps `{asset.qr.rotate:true}` | nút "Sinh lại mã QR" render |
| `assetListBatchSelect.test.ts` (D6) | mock caps `{asset.read:true}` (KHÔNG print) | nút "In nhãn hàng loạt" KHÔNG render |
| `routeAccess.test.ts` (D6) | guard `AssetLabelPrint` với caps `{asset.read:true}` | unauthorized; `{asset.print:true}` → allow |
| `assetDetailRbacAffordance.test.ts` (D6) | caps `{asset.print:true}` only | "In nhãn QR" hiện, "Sinh lại mã QR"/"Chỉnh sửa" ẩn (least-privilege) |

### III.6.0e-TRANSITIONAUTHZ — Vòng 39 / CR-WF-00-TRANSITION-AUTHZ: gate `asset.write` + IDOR tầng endpoint cho `transition_status` (BR-00-57 / FR-00-108)

File BE: class MỚI `TestTransitionStatusAuthz` (`assetcore/tests/test_imm00.py`). **Template parity:** mirror get_asset cap-gate tests (`test_imm00.py:6139+` — `rbac.require('asset.read')` ĐẦU TIÊN, no existence-oracle) + write-cap+IDOR pattern (`:6856+`). Đo QUA layer `require`/`assert_vendor_can_access` với **user THẬT** (cấp/không-cấp DocPerm write trên AC Asset qua Role/Custom DocPerm + `frappe.set_user`). **KHÔNG** `monkeypatch rbac.require`/`frappe.has_permission` (chống false-green). RED-first: viết test TRƯỚC khi thêm gate (assert đổi được trạng thái = RED), thêm gate → GREEN.

**Acceptance — `bench --site miyano run-tests --module assetcore.tests.test_imm00` (authz) + `test_imm08`/`test_imm09` (regression) `Ran N OK` THẬT** (đọc số thật, KHÔNG marker-trust). `CAP_SET_VERSION` GIỮ (0 cap mới). ⚠️ `api/imm00.py` reload-gated (gunicorn --preload) — HTTP-live BLOCKED (HARD-STOP user); gate hợp lệ = `bench run-tests` fresh-import + code-audit thứ-tự-lớp.

| TC (BE) | Kịch bản (user THẬT, qua layer thật) | Verify | AC |
|---|---|---|---|
| `test_transition_no_write_cap_403_no_mutation` | user KHÔNG DocPerm `asset.write` (base `AssetCore System User`) POST `transition_status(asset, to_status)` | `frappe.PermissionError` (**403 status-line**); `frappe.db.get_value(asset,'lifecycle_status')` trước==sau (bất biến) | AC1 |
| `test_transition_vendor_out_of_scope_403_no_mutation` | Vendor Engineer CÓ `asset.write` nhưng asset NGOÀI scope (không PM/CM WO giao) | `ServiceError`→`_err` `error_code=FORBIDDEN`; `lifecycle_status` bất biến | AC2 |
| `test_transition_no_cap_nonexistent_asset_403_not_404` | user thiếu `asset.write` + `name` KHÔNG tồn tại | **403 KHÔNG 404** (rbac.require chạy TRƯỚC `frappe.db.exists` — no existence-oracle) | AC3 |
| `test_transition_write_holder_happy_path` | Administrator/Super Admin (write=1) + in-scope + transition hợp state-machine (vd Commissioned→Active) | `_ok {name, lifecycle_status}`; ĐÚNG 1 Asset Lifecycle Event + 1 IMM Audit Trail `event_type='State Change'` | AC4 |
| `test_transition_service_still_perm_free` | gọi THẲNG service `transition_asset_status(asset, to, actor=KTV)` bằng user KTV KHÔNG write | success (KHÔNG raise) — gate CHỈ ở endpoint | AC5 |
| `test_cap_write_binding_unchanged` | white-box | `CAPABILITY_MAP['asset.write'] == ('AC Asset','write')`; `CAP_SET_VERSION` KHÔNG đổi (0 cap mới) | dead-gate guard |

**Regression (PHẢI GREEN):** `test_imm08` (PM WO-complete → asset Active/Under Maintenance) + `test_imm09` (Repair WO-complete → Under Repair/Active/Completed) — các luồng gọi thẳng service, KHÔNG qua endpoint ⇒ gate endpoint KHÔNG chạm (AC5). `test_imm00` transition cũ (`:297/:1061/:2028` gọi service `actor="Administrator"`) GIỮ XANH.

> **KHÔNG test false-green:** test tạo user thật + cấp/không-cấp DocPerm `write` trên `AC Asset` (Role/Custom DocPerm), `frappe.set_user(...)`, rồi gọi endpoint. Gate đi đúng đường `require("asset.write")`→`can`→`frappe.has_permission("AC Asset","write")`; IDOR đúng đường `assert_vendor_can_access`. KHÔNG mock.

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

### III.6.0 — V10: Coerce an toàn tham số `assets` (3 endpoint nhãn) — `TestLabelCoerceAssets` (ADR-IMM00-LABEL-PDF D17)

File BE: class MỚI `TestLabelCoerceAssets` trong `assetcore/tests/test_imm00.py` (cạnh `TestAssetLabelData`). **Guard Python thuần tier API/service** → fresh-import qua `run-tests`, KHÔNG cần reload gunicorn/migrate.

**Acceptance — chạy XANH:** `bench --site miyano run-tests test_imm00` GREEN (288+ baseline 0 regression + TC mới). **RED-first chứng minh:** trước fix `assets='AC-2026-00001'` FAIL (raise `JSONDecodeError`/500) → sau fix GREEN. KHÔNG cần `vue-tsc`/`vitest` (BE-only). Toàn bộ test nhãn cũ (`TestAssetLabelData`, `TestLabelPdfPipeline`, cap-tests) GIỮ xanh.

> **Vector chuẩn (dùng chung 3 endpoint):** `BAD = ['AC-2026-00001', '', '   ', 'not-json', '"AC-1"', '123', '{"a":1}']` (string KHÔNG-list-hợp-lệ) · `GOOD = (['AC-1','AC-2'], '["AC-1"]')` (list + JSON-array-string) · `MIXED = [1, 'AC-1', None]` (list lẫn non-str).

| TC (BE) | Kịch bản | Verify | Kỹ thuật |
|---|---|---|---|
| `test_pdf_bad_assets_no_500_returns_label_empty_422` | `print_asset_labels_pdf(assets=v)` ∀ `v ∈ BAD` (Administrator có cap) | **KHÔNG raise** (no JSONDecodeError/TypeError/500); coerce-`[]` → `_err` HTTP-200, `http_status==422`, message == `_ERR_LABEL_EMPTY`; KHÔNG traceback trong body; KHÔNG set `frappe.local.response` PDF | EP + no-500 |
| `test_batch_bad_assets_no_500_returns_ok_empty` | `get_asset_label_data_batch(assets=v)` ∀ `v ∈ BAD` | KHÔNG raise; `success==True`, `data == []` (KHÔNG 4-entry char-walk); KHÔNG 500 | EP + count==rows |
| `test_mark_bad_assets_no_500_no_side_effect` | `mark_label_printed(assets=v)` ∀ `v ∈ BAD` | KHÔNG raise; coerce-`[]` → vòng exists rỗng → `success==True` no-side-effect (0 `label_printed` + 0 audit, count trước==sau); KHÔNG 500 | State-based no-side-effect |
| `test_scalar_string_no_char_walk` | `get_asset_label_data_batch(assets='"AC-1"')` mock/spy `frappe.db.exists` | `db.exists` gọi **0 lần** (coerce-`[]`, KHÔNG 4 lần trên `'A','C','-','1'`); `data == []` — char-walk guard | White-box (call-count == #asset hợp lệ ≠ #ký-tự) |
| `test_number_object_no_typeerror` | `print_asset_labels_pdf(assets='123')` + `(assets='{"a":1}')` | KHÔNG `TypeError` trên `len()`/iterate; `_err` 422 VI sạch | Error guessing (type-coerce) |
| `test_valid_list_byte_for_byte` | `get_asset_label_data_batch(assets=['AC-1','AC-2'])` (asset thật) | render/đọc ĐÚNG như trước fix (payload đầy đủ, giữ thứ tự) — 0 regression đường hợp lệ | Regression |
| `test_valid_json_array_string_byte_for_byte` | `get_asset_label_data_batch(assets='["AC-1"]')` (asset thật) | đọc đúng (parse JSON-array-string → list) — đường HTTP hợp lệ giữ nguyên | Regression |
| `test_mixed_list_filters_non_str` | `mark_label_printed(assets=[1, a.name, None])` (a thật) | chỉ ghi cho `a.name`; `1`/`None` bị lọc — KHÔNG đẩy vào `db.exists`/`assert_vendor_can_access`; 1 `label_printed` | White-box (per-element filter) |
| `test_coerce_runs_after_rbac_guest_403` | Guest gọi 3 endpoint với `assets='AC-2026-00001'` | **403** (PermissionError dispatcher) TRƯỚC coerce — coerce KHÔNG rò giới hạn/empty-path cho khách chưa-auth; thứ tự gate giữ | Ordering (no-leak) |
| `test_coerce_8_single_ssot_helper_no_bare_parse_json` | đọc source `assetcore/api/imm00.py` | regex `parse_json\(assets\)` match **đúng 1 lần** — BÊN TRONG `_coerce_asset_names` (helper ĐỊNH NGHĨA ở `api/imm00.py:126`, NOT `services/imm00.py`); handler-pattern trần `parse_json(assets) if isinstance` match **0 lần** — drift-guard | White-box (grep source) |

> **KHÔNG test false-green:** RED-first BẮT BUỘC — viết `test_pdf_bad_assets_no_500…` TRƯỚC fix, chứng kiến FAIL (raise/500), rồi mới impl `_coerce_asset_names`. Char-walk guard đếm `db.exists` call-count == số asset-name **hợp lệ** (KHÔNG == số ký tự của scalar-string) — nếu bỏ list-gate, test này FAIL (4 call). Đường hợp lệ phải PASS cùng assertion với test cũ (superset an toàn). ⚠️ **Drift-note:** SSoT `_coerce_asset_names` THỰC-TẾ ở `api/imm00.py:126` (NOT `services/imm00.py` như bản cũ ghi — `test_coerce_8…` đọc source `api/imm00.py` xác nhận).

### III.6.0-DEDUP — V15: Khử trùng-lặp asset TRONG-CALL ở SSoT `_coerce_asset_names` — `TestLabelCoerceDedup` (ADR-IMM00-LABEL-PDF D19 / BR-00-47 / FR-00-98)

File BE: class MỚI `TestLabelCoerceDedup` trong `assetcore/tests/test_imm00.py` (cạnh `TestLabelCoerceAssets`). **Guard Python thuần tier API** → fresh-import qua `run-tests`, KHÔNG cần reload gunicorn/migrate. **RED-first:** `_coerce_asset_names(['AC-1','AC-1','AC-2','AC-1'])` → 4 phần tử (FAIL) TRƯỚC fix → `['AC-1','AC-2']` (GREEN) sau khi thêm `list(dict.fromkeys(...))`.

**Acceptance — chạy XANH:** `bench --site miyano run-tests test_imm00` GREEN (baseline 0 regression + 7 TC mới). Bộ test nhãn cũ (`TestAssetLabelData`/`TestLabelPdfPipeline`/`TestLabelCoerceAssets`/cap-tests) + **`test_mark_label_printed_idempotent_count` (`:4342`)** GIỮ XANH. FE: vitest baseline 135 file 0 regression (validNames đã unique — KHÔNG sửa FE, KHÔNG cần `vue-tsc`).

| TC (BE) | ID | Kịch bản | Verify | Kỹ thuật |
|---|---|---|---|---|
| `test_coerce_dedup_in_call_keep_first_order` | TC-LABEL-DEDUP-01 | `_coerce_asset_names(['AC-1','AC-1','AC-2','AC-1'])` + `(['AC-2','AC-1','AC-2'])` | → `['AC-1','AC-2']` + `['AC-2','AC-1']` (giữ lần xuất-hiện-ĐẦU, bỏ trùng SAU, **KHÔNG sort**) | EP + order-preserve (unit, no DB) |
| `test_coerce_dedup_compose_after_type_filter` | TC-LABEL-DEDUP-02 | `_coerce_asset_names([1,'AC-X',None,'AC-X',''])` + `'["AC-1","AC-1"]'` | → `['AC-X']` + `['AC-1']` (lọc-kiểu D17 TRƯỚC, dedup D19 SAU; áp cả đường JSON-array-string) | White-box (compose) |
| `test_mark_label_printed_dedup_one_call_one_event` | TC-LABEL-DEDUP-03 | `mark_label_printed(assets=[a1.name,a1.name,a1.name])` (1 call, a1 thật) | `success`; `data.event_count==1`, `data.printed==[a1.name]`; `COUNT(ALE label_printed)`==before+1 ∧ `COUNT(IMM Audit Trail)`==before+1 (**KHÔNG +3**) | State-based (no-amplify) |
| `test_print_pdf_dedup_one_page` | TC-LABEL-DEDUP-04 | `print_asset_labels_pdf(assets=[a1.name,a1.name])` (a1 thật, cap) | bytes `%PDF-`; **`len(pypdf.PdfReader(BytesIO(pdf)).pages)==1`** (HARD invariant — KHÔNG 2 trang trùng); MediaBox khổ-DỌC đúng tỷ-lệ portrait 60:100 — `width<height` ∧ `height/width ≈ 100/60` (tol ±2%). ⚠️ KHÔNG assert pt-tuyệt-đối: wkhtmltopdf có thể emit MediaBox theo **px@96DPI** (60mm→226.77px, 100mm→377.95px) KHÁC pt (170.08×283.46) tuỳ engine → assert tỷ-lệ + portrait, KHÔNG hardcode pt | Output-based (pypdf page-count HARD + MediaBox ratio) |
| `test_batch_dedup_one_element` | TC-LABEL-DEDUP-05 | `get_asset_label_data_batch(assets=[a1.name,a1.name])` (a1 thật) | `success`; `len(data)==1` (count==rows: 1 unique == 1 row); `data[0].name==a1.name` | EP + count==rows |
| `test_cap_measured_on_deduped_list` | TC-LABEL-DEDUP-06 | (a) `get_asset_label_data_batch(assets=[a1.name]*300)` (300 trùng, a1 thật); (b) `>200 asset UNIQUE` thật | (a) **KHÔNG 413** — dedup `[a1]` (len 1 ≤ 200), `_ok` 1-item; (b) **413** `_ERR_LABEL_BATCH_TOO_LARGE` GIỮ (cap đo unique) | Boundary (cap-on-dedup, trực giao cap) |
| `test_mark_label_printed_idempotent_count` (HIỆN HỮU `:4342`) | TC-LABEL-DEDUP-07 | 2 lần gọi RIÊNG `mark_label_printed([a1.name])` | **2** event `label_printed` cho a1 (cross-call KHÔNG dedup — dedup CHỈ trong-call) — bất biến PHẢI vẫn XANH | Regression (cross-call invariant) |

> **KHÔNG test false-green:** RED-first — viết TC-01/03/04/05 TRƯỚC khi thêm `list(dict.fromkeys(...))`, chứng kiến FAIL (4 phần tử / event_count=3 / 2 trang / 2 phần tử), rồi mới impl. **Cross-call guard (TC-07) BẮT BUỘC PASS cả trước-lẫn-sau fix** — nếu fix vô tình thêm state xuyên-call (cache/DB-lookup) thì TC-07 FAIL → reject. **pypdf** đã có ở bench (dùng đọc page-count + MediaBox; KHÔNG đếm chuỗi `%PDF` thô). Malformed→`[]` (TC `TestLabelCoerceAssets` cũ) GIỮ XANH (dedup `[]`→`[]` no-op).

### III.6.k-LABELQREMPTY — Guard render-tier `qr_url` rỗng/whitespace → ô-QR-lỗi an toàn ở tem PDF (Vòng 30 — BR-00-49 / FR-00-100 / ADR §D20)

File BE: class MỚI `TestLabelQrEmpty` trong `assetcore/tests/test_imm00.py` (cạnh `TestLabelPdfPipeline`). **Guard Python thuần render-tier (`services/imm00.py::_label_block`/`render_asset_labels_pdf`)** → fresh-import qua `run-tests`, KHÔNG reload gunicorn/migrate. **RED-first:** `_label_block({...,"qr_url":""},...)` chứa `<svg>` QR-rác rỗng (FAIL) TRƯỚC fix → ô-QR-lỗi VI `Không tạo được mã QR` KHÔNG `<svg>` (GREEN) sau guard. FE: revert-proof vitest `AssetQrLabel` (xoá guard `:73`→ĐỎ, khôi phục→XANH). **pypdf** đo TẦNG PDF THẬT (page-count + extract_text + MediaBox; KHÔNG đếm `<svg>` ở HTML trung gian — đo bytes PDF cuối).

**Acceptance — chạy XANH:** `bench --site miyano run-tests test_imm00` GREEN (baseline 0 regression + 6 TC mới). Bộ test nhãn cũ (`TestAssetLabelData`/`TestLabelPdfPipeline`/`TestLabelCoerceAssets`/`TestLabelCoerceDedup`/cap/AC-E001) GIỮ XANH. FE: `AssetQrLabel.*.test.ts` GREEN + revert-proof guard.

| TC | ID | Kịch bản | Verify | Kỹ thuật |
|---|---|---|---|---|
| `test_label_block_empty_qr_url_safe_cell` | TC-LABEL-QREMPTY-01 | `_label_block({"asset_code":"A-1","asset_name":"X","qr_url":""}, "tem-60x100", True)` + lặp `qr_url:"   "` (whitespace) | HTML KHÔNG chứa `"<svg"` ∧ KHÔNG chứa `data-qr-url=""` (rỗng) ∧ CHỨA `Không tạo được mã QR` ∧ CHỨA field-chữ `A-1`/`X`; whitespace cho CÙNG kết quả (strip ≡ rỗng) | Unit white-box (HTML assert) |
| `test_label_block_qr_svg_inline_not_called_when_empty` | TC-LABEL-QREMPTY-02 | spy/monkeypatch `_qr_svg_inline`; `_label_block` item `{qr_url:""}` + `{qr_url:"   "}` | `_qr_svg_inline` 0-call (HOẶC assert `pyqrcode.create` KHÔNG nhận `''`/`'   '`); 0 raise, 0 junk-QR | Guard-trước-create (spy) |
| `test_render_pdf_empty_qr_url_n_to_n_pages` | TC-LABEL-QREMPTY-03 | `render_asset_labels_pdf([a_ok, a_empty_qr, a_ok2])` (a_empty_qr = asset thật nhưng qr_url drift rỗng) | bytes `%PDF-`; **`len(pypdf.PdfReader(BytesIO(pdf)).pages)==3`** (N→N — 1 asset xấu KHÔNG giết batch); trang[1] `extract_text()` chứa `Không tạo được mã QR` ∧ KHÔNG `<svg>`-marker; MediaBox portrait đúng khổ (`width<height` ∧ `height/width≈100/60` tol ±2% — KHÔNG hardcode pt) | Output-based (pypdf page-count HARD + text + MediaBox ratio) |
| `test_render_pdf_empty_qr_url_no_raise_no_junk` | TC-LABEL-QREMPTY-04 | inject `_label_block`/`render_asset_labels_pdf` item `{qr_url:""}` + `{qr_url:"   "}` | 0 raise (KHÔNG `_ERR_LABEL_RENDER` toàn-call); PDF bytes KHÔNG chứa chuỗi `qr_url` rỗng/junk embed cho ô đó | No-raise batch |
| `test_label_no_regression_ace001_and_valid_qr` | TC-LABEL-QREMPTY-05 | `[valid, "KHONG-TON-TAI"]` (§D7 AC-E001) + asset QR-hợp-lệ | AC-E001 VẪN 2 trang (1 QR-thật + 1 "Không tìm thấy tài sản" KHÔNG QR); asset QR-hợp-lệ VẪN có `<svg>` + `data-qr-url=/a/<token>` trong HTML | Regression (AC-E001 + đường QR-hợp-lệ) |
| `test_fe_assetqrlabel_empty_qr_guard_revert_proof` | TC-LABEL-QREMPTY-06 | (vitest) `AssetQrLabel` `qr_url:''` → `qrFailed==true` + ô-fallback render "Không tạo được mã QR"; xoá guard `:73`→ĐỎ, khôi phục→XANH | guard `:73` CÒN RĂNG (LL-TEST-26); parity nhãn VI on-screen ≡ PDF | FE revert-proof (vitest) |

> **KHÔNG test false-green:** RED-first — viết TC-01/03 TRƯỚC khi thêm guard, chứng kiến FAIL (HTML chứa `<svg>` QR-rác / PDF trang ô-rỗng có `<svg>`), rồi mới impl. **Đo ở TẦNG PDF THẬT (pypdf)** cho TC-03/04 — KHÔNG đếm `<svg>` ở HTML trung gian (đo bytes PDF cuối: `extract_text()` + MediaBox). **N→N trang (TC-03) HARD invariant** — nếu fix vô tình raise toàn-call (giết batch) thì `pages != 3` → reject. **pyqrcode KHÔNG BAO GIỜ nhận `''`/`'   '`** (TC-02 spy) — guard TRƯỚC create. AC-E001 (asset∄, §D7) + đường QR-hợp-lệ + §D2/D3/D13/D17/D19 GIỮ XANH (TC-05). **KHÁC AC-E001:** nhánh #3 (qr_url rỗng) VẪN render 5 field chữ (asset có data) — assert field-chữ hiện diện (TC-01).

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

#### III.6.f-PMDATESTR — A6-hardening (Vòng 11): `next_pm_date` → `str\|None` (parity `next_calibration_date`) — FR-00-86

File BE: thêm **đúng 1 TC** `test_scan_info_next_pm_date_is_str_or_none` vào class `TestAssetScanInfoPmOverdue` (cùng `assetcore/tests/test_imm00.py`) — mirror chính xác `test_payload_has_calibration_fields_9_fields_intact` (vốn assert `next_calibration_date` là `str|None`). FE: **KHÔNG đổi** (`scheduleLabel('next_pm_date')` đã chịu được str/null/absent — `vitest` GIỮ XANH). **RED-first BẮT BUỘC:** TC chưa tồn tại + `build_asset_scan_info` còn emit `row.get("next_pm_date") or None` (date object thô) → assert `isinstance(str)` + `== getdate(...).strftime('%Y-%m-%d')` FAIL → đổi 1 dòng sang `_date_str_or_none(row.get("next_pm_date"))` → GREEN. Đo QUA `build_asset_scan_info`/`get_asset_scan_info` THẬT (KHÔNG mock — tạo asset thật, set `next_pm_date` thật).

**Acceptance — chạy XANH:** `bench --site miyano run-tests test_imm00` (`TestAssetScanInfo` + `TestAssetScanInfoPmOverdue` + `TestAssetScanInfoCalibrationOverdue` GIỮ baseline + TC mới). KHÔNG `bench migrate` (zero schema), KHÔNG reload gunicorn. `CAP_SET_VERSION` GIỮ `v95.3388ee5629c1`.

| TC (BE) | Input | Expected | Kỹ thuật |
|---|---|---|---|
| `test_scan_info_next_pm_date_is_str_or_none` | `next_pm_date = add_days(nowdate(), -1)`, gọi `build_asset_scan_info` | `isinstance(data["next_pm_date"], str)` **AND** `data["next_pm_date"] == getdate(add_days(nowdate(),-1)).strftime("%Y-%m-%d")` — KHÔNG còn `datetime.date` object | Type + value-exact |
| `test_scan_info_next_pm_date_none_when_null` | KHÔNG set `next_pm_date` | `data["next_pm_date"] is None` (rỗng/NULL → None, KHÔNG raise) | EP (null) |
| `test_scan_info_pm_overdue_unaffected_by_str_normalize` | `next_pm_date = add_days(nowdate(), -1)`, Active | `pm_overdue is True` ∧ `next_pm_date` là str `'YYYY-MM-DD'` — cờ derive từ RAW row TRƯỚC normalize (KHÔNG hồi quy) | Invariant (orthogonal) |
| `test_scan_info_payload_shape_unchanged_after_pmdate_str` | asset bất kỳ | `set(data.keys())` == 9 FR-00-85 + `next_calibration_date` + `calibration_overdue` + `available_actions` (KHÔNG thêm/bớt key — chỉ đổi KIỂU value `next_pm_date`) | Field-whitelist (no-delta) |

#### III.6.c-TOKENNORM — factory vòng 6: chuẩn hoá whitespace `qr_token` ở SSoT resolve — BR-00-40 / FR-00-90/91 / ADR §D8

File BE: thêm class `TestResolveQrTokenWhitespace` vào `assetcore/tests/test_imm00.py` (cạnh `TestResolveQrToken` A2 + `TestGetAssetScanInfo`). FE: **KHÔNG đổi** (BE-only — FE `QrResolveView.vue:34`/`QRScanView.vue:45` trim đã có làm defense-in-depth lớp 1, `vitest` GIỮ XANH). **RED-first BẮT BUỘC:** class/TC chưa tồn tại + `resolve_qr_token` chưa strip → TC token-kèm-`\n`/space FAIL (false-404) → thêm `token = token.strip()` đầu hàm `services/imm00.py::resolve_qr_token` → GREEN. Đo QUA `resolve_qr_token`/`get_asset_scan_info` THẬT (KHÔNG mock `frappe.db.get_value` — tạo asset thật, tra token thật).

**Acceptance — chạy XANH:** `bench --site miyano run-tests test_imm00` (`TestResolveQrToken` + `TestAssetScanInfo` baseline + `TestResolveQrTokenWhitespace` mới + label-pdf suite) GREEN — 0 regression. `bench migrate` KHÔNG cần (0 schema/patch). `CAP_SET_VERSION` GIỮ NGUYÊN. **Logic-level fresh-import — KHÔNG tuyên bố verify HTTP/Playwright live** (endpoint live HTTP cần USER reload gunicorn — STATE 🔴#1; round này doc+test introspection/logic-level).

| TC (BE) | Kịch bản | Verify | Kỹ thuật |
|---|---|---|---|
| `test_resolve_token_with_leading_trailing_space` | asset có `qr_token=<tok>` → `resolve_qr_token(token=f' {tok} ')` | `success is True`; `data["name"] == asset.name`; `data["asset_code"] == asset.asset_code` — KHÔNG false-404 | EP (positive, FR-00-90 BE-1) |
| `test_resolve_token_with_trailing_newline` | `resolve_qr_token(token=f'{tok}\n')` (artifact encode QR tem nhiệt) | `success is True`; `data["name"] == asset.name` | EP (positive, FR-00-90 BE-1) |
| `test_resolve_token_with_tabs_mixed_whitespace` | `resolve_qr_token(token=f'\t {tok} \n')` | `success is True`; `data["name"] == asset.name` | EP (robustness) |
| `test_resolve_whitespace_only_token_404_no_query` | `resolve_qr_token(token='   ')` / `'\t'` / `'\n'` | `success is False`; `http_status==404`; **assert 0 query trên AC Asset** (đếm SQL/`get_value` trên path rỗng-sau-strip — return None tại guard TRƯỚC `get_value`) | White-box (query-count=0, FR-00-90 BE-3) |
| `test_resolve_whitespace_no_match_404_leak_safe` | `resolve_qr_token(token=' khong-ton-tai-zzz ')` | `success is False`; `http_status==404`; KHÔNG 500/417; KHÔNG raw exception/traceback trong message | EP (negative leak-safe, FR-00-90 BE-5) |
| `test_resolve_empty_string_still_404_no_query` *(regression)* | `resolve_qr_token(token='')` | `http_status in (400,404)`; 0 query (guard rỗng GIỮ — đối xứng whitespace-only) | EP (regression baseline) |
| `test_scan_info_token_with_space_returns_payload` | `get_asset_scan_info(token=f' {tok} ')` | `success is True`; payload A6 (11-field) đúng asset — parity với resolve | EP (parity, FR-00-91 BE-2) |
| `test_scan_info_token_with_newline_returns_payload` | `get_asset_scan_info(token=f'{tok}\n')` | `success is True`; payload A6 đúng | EP (parity, FR-00-91 BE-2) |
| `test_scan_info_whitespace_only_token_404_no_query` | `get_asset_scan_info(token='   ')` | `http_status==404`; KHÔNG query asset thừa (SSoT strip → None TRƯỚC build payload) | White-box (FR-00-91 BE-3) |
| `test_scan_info_name_branch_not_affected_by_token_strip` | `get_asset_scan_info(name=asset.name)` (nhánh name, KHÔNG token) | payload A6 đúng — nhánh `name` KHÔNG bị ép strip-TOKEN (đường khác; nhánh name có chuẩn-hoá riêng `name.strip()` — xem §III.6.l-NAMENORM Vòng 31) | EP (boundary — name branch intact) |
| `test_normalization_single_ssot_grep` | grep `.strip()` cho token-resolve toàn `services/imm00.py`/`api/imm00.py` | chỉ **1** điểm strip token-resolve (trong `resolve_qr_token`) — KHÔNG fork nhánh strip thứ 2 ở API/scan-info | Grep-guard (FR-00-90 BE-4) |
| `test_resolve_whitespace_no_audit_side_effect` *(regression)* | `resolve_qr_token(token=f' {tok} ')` N lần | KHÔNG tạo `Asset Lifecycle Event`/`IMM Audit Trail` (read-only GIỮ — A2/D4) | State-based (no-write) |

> **Pattern đo query-count = 0 (path whitespace-only):** bọc call trong context đếm SQL (vd monkeypatch `frappe.db.sql`/`get_value` đếm invocation trên `AC Asset`, HOẶC `frappe.db.sql_list` counter) → assert 0 query khi token rỗng-sau-strip (return None tại guard TRƯỚC `frappe.db.get_value`). So sánh với token rỗng `''` (cùng = 0 query) để chứng minh đối xứng.

**REG (acceptance đề mục):** 100% test QR-asset BE hiện có — `TestResolveQrToken` (token hợp lệ/unknown-404/empty-404/no-cap-403/IDOR-403/no-audit), `TestAssetScanInfo` (+ `TestAssetScanInfoPmOverdue`/`TestAssetScanInfoCalibrationOverdue`), `TestQrWhitelistHttpLayer`, label-pdf suite (`test_imm00` print/preset) — GIỮ GREEN, 0 regression. KHÔNG đổi `qr_url`/encode/no-raw-token parity (BR-00-34) / rate-limit (BR-00-29).

#### III.6.l-NAMENORM — Vòng 31: chuẩn hoá whitespace tham số `name` ở `get_asset_scan_info` (parity nhánh token) — FR-00-101 / BR-00-50 / ADR §D12

File BE: **bổ sung** class `TestAssetScanInfoNameWhitespace` (`assetcore/tests/test_imm00.py` — cạnh `TestAssetScanInfo`). **RED-first BẮT BUỘC:** TC `name='  <name>  '` assert `http_status==200` + payload A6 đúng asset ĐỎ trước fix (hiện `db.exists("  A-042  ")` = False → 404) → thêm `name = name.strip()` trong `get_asset_scan_info` (sau coerce-str, TRƯỚC nhánh `elif name and frappe.db.exists`) → GREEN. Đo QUA `get_asset_scan_info` THẬT (Administrator có mọi DocPerm — KHÔNG mock; tạo 1 AC Asset thật rồi gọi với biến thể whitespace). Spec: [`04 §II.1.8a-NAMENORM`](./04_Backend_Design.md) + [`05 §get_asset_scan_info case-table`](./05_API_Specification.md) + [`02 §IV.26 / BR-00-50`](./02_Analysis_Design.md) + [ADR §D12](./ADR-IMM00-QR-SCAN-ACTION.md).

**Acceptance — chạy XANH:** `bench --site miyano run-tests test_imm00` (`TestAssetScanInfoNameWhitespace` mới + `TestAssetScanInfo`/`TestResolveQrToken`/`TestResolveQrTokenWhitespace` baseline + label-pdf suite) GREEN — 0 regression. `bench migrate` KHÔNG cần (0 schema/patch). `CAP_SET_VERSION` GIỮ `v97.c30c69b8974d`. **Logic-level fresh-import (sửa `api/imm00.py` live ở run-tests) — KHÔNG tuyên bố verify HTTP/Playwright live** (endpoint live HTTP cần USER reload gunicorn --preload → backlog [BLOCKED reload]; STATE 🔴#1).

| TC (BE) | Kịch bản | Verify | Kỹ thuật |
|---|---|---|---|
| `test_scan_info_name_with_leading_trailing_space_200` | AC Asset thật `name=A` → `get_asset_scan_info(name=f'  {A}  ')` | `success is True`; `http_status==200`; `data["name"]==A`; payload A6 (11-field) — KHÔNG false-404 | EP (positive, FR-00-101 #2) |
| `test_scan_info_name_with_trailing_newline_200` | `get_asset_scan_info(name=f'{A}\n')` (copy-paste / deep-link artifact) | `success is True`; `data["name"]==A` | EP (positive, FR-00-101 #2) |
| `test_scan_info_name_with_tabs_mixed_whitespace_200` | `get_asset_scan_info(name=f'\t{A}\t')` | `success is True`; `data["name"]==A` | EP (robustness) |
| `test_scan_info_name_whitespace_only_404_no_full_scan` | `get_asset_scan_info(name='   ')` / `'\n'` / `'\t'` | `success is False`; `http_status==404` (`AC-E001`); **assert 0 query `frappe.db.exists` trên AC Asset** (strip→`''`→`elif name and …` short-circuit) — KHÔNG full-scan | White-box (query-count=0, FR-00-101 #3) |
| `test_scan_info_name_inner_space_still_404` | `get_asset_scan_info(name='A 042')` (space GIỮA — name hỏng thật) | `success is False`; `http_status==404`; KHÔNG 500; CHỈ strip leading/trailing (không lowercase/collapse) | EP (negative, FR-00-101 #4 — KHÔNG over-normalize) |
| `test_scan_info_name_with_space_no_audit_side_effect` *(regression)* | `get_asset_scan_info(name=f'  {A}  ')` N lần | KHÔNG tạo `Asset Lifecycle Event`/`IMM Audit Trail` (read-only GIỮ — A2/D4) | State-based (no-write) |
| `test_scan_info_name_with_space_idor_403_unchanged` *(regression)* | vendor user ngoài scope → `get_asset_scan_info(name=f'  {A}  ')` | `http_status==403` (`assert_vendor_can_access` GIỮ — strip xảy ra TRƯỚC resolve, IDOR sau) | Regression (IDOR no-regression) |
| `test_scan_info_name_strip_single_grep` | grep `name.strip()` trong `get_asset_scan_info` (`api/imm00.py`) | đúng **1** điểm strip cho nhánh `name`; KHÔNG đụng `_svc_resolve_qr_token` (token-path bất động) | Grep-guard (FR-00-101 #5) |

> **Pattern đo query-count = 0 (name whitespace-only):** monkeypatch/đếm `frappe.db.exists` trên `AC Asset` → assert 0 invocation khi `name` rỗng-sau-strip (`elif name and …` short-circuit do `name` falsy). So với `name=''` (cùng 0 query) chứng minh đối xứng — KHÔNG full-scan.

**REG (acceptance đề mục):** `TestAssetScanInfo` (+ `…PmOverdue`/`…CalibrationOverdue`/`…AvailableActions`), `TestResolveQrToken`/`TestResolveQrTokenWhitespace`, `TestQrWhitelistHttpLayer`, label-pdf suite — GIỮ GREEN, 0 regression. Token-path BẤT ĐỘNG (parity Vòng 6 BR-00-40 GIỮ). KHÔNG đổi payload shape / no-raw-token (BR-00-34) / rate-limit (BR-00-29) / RBAC / IDOR.

#### III.6.m-SCANSN — Vòng 37: `manufacturer_sn` (Số serial NSX) vào payload `build_asset_scan_info` + FE `serialText` fallback `'Chưa rõ'` — FR-00-103 / BR-00-52 / ADR §D13

File BE: **bổ sung** class `TestScanInfoManufacturerSn` (`assetcore/tests/test_imm00.py` — cạnh `TestAssetScanInfo`). File FE: cập nhật `frontend/src/views/asset/AssetScanInfoView.test.ts` (thêm TC dòng "Số serial NSX" + empty-fallback). **RED-first BẮT BUỘC:** TC `assert 'manufacturer_sn' in payload` + `== <giá-trị-thật>` ĐỎ trước fix (key absent → KeyError/None) → thêm `"manufacturer_sn"` vào fields-list `db.get_value` + key payload `row.get("manufacturer_sn") or ""` → GREEN; TC FE `serialText==='Chưa rõ'` khi rỗng ĐỎ trước thêm computed → GREEN. Đo QUA `build_asset_scan_info` THẬT (Administrator có mọi DocPerm — KHÔNG mock; tạo AC Asset thật, set `manufacturer_sn` thật + biến thể rỗng). Spec: [`04 §II.1.8d-SCANSN`](./04_Backend_Design.md) + [`05 §get_asset_scan_info payload 12-field`](./05_API_Specification.md) + [`02 §IV.28 / BR-00-52`](./02_Analysis_Design.md) + [`06 §II.3d-SERIALSN`](./06_Frontend_Design.md) + [ADR §D13](./ADR-IMM00-QR-SCAN-ACTION.md).

**Acceptance — chạy XANH:** `bench --site miyano run-tests test_imm00` (`TestScanInfoManufacturerSn` mới + `TestAssetScanInfo`/`…PmOverdue`/`…CalibrationOverdue`/`…AvailableActions`/`TestResolveQrToken` baseline + label-pdf suite) GREEN — 0 regression. `bench migrate` KHÔNG cần (0 schema/patch — `manufacturer_sn` đã là field AC Asset). `CAP_SET_VERSION` GIỮ `v97.c30c69b8974d`. FE: `vitest AssetScanInfoView.test.ts` GREEN + `vue-tsc` 0 + full asset-domain vitest no-regression. **Logic-level fresh-import (BE) + vitest (FE render — KHÔNG cần reload) — KHÔNG tuyên bố verify HTTP/Playwright/quét-QR-thật live** (endpoint live HTTP cần USER reload gunicorn --preload → backlog [BLOCKED reload]; STATE 🔴#1).

| TC (BE) | Kịch bản | Verify | Kỹ thuật |
|---|---|---|---|
| `test_scan_info_has_manufacturer_sn_key` | AC Asset thật `manufacturer_sn='SN-12345'` → `build_asset_scan_info(asset.name)` | `'manufacturer_sn' in payload`; `payload['manufacturer_sn'] == 'SN-12345'` (str nguyên văn) | EP (positive, FR-00-103 #1 — RED-first absent) |
| `test_scan_info_manufacturer_sn_empty_coalesces_to_str` | asset `manufacturer_sn` null/rỗng → `build_asset_scan_info` | `payload['manufacturer_sn'] == ''` (str); `payload['manufacturer_sn'] is not None`; KHÔNG raw object | EP (empty → `''`, FR-00-103 #2 — parity `asset_code`/`asset_name`) |
| `test_scan_info_manufacturer_sn_no_extra_round_trip` | grep/AST `build_asset_scan_info` | `"manufacturer_sn"` nằm trong CÙNG `frappe.db.get_value([...], as_dict=True)`; KHÔNG `get_value(_DOCTYPE_ASSET, …, "manufacturer_sn")` riêng (no-N+1) | White-box / Grep-guard (FR-00-103 #3) |
| `test_scan_info_empty_name_returns_none_unchanged` *(regression)* | `build_asset_scan_info('')` / `None` / non-str | `is None` (early-return GIỮ); KHÔNG query toàn bảng | EP (no-regress guard, FR-00-103 #4) |
| `test_scan_info_no_sensitive_field_leak_with_sn` *(regression)* | `build_asset_scan_info(asset.name)` | `'qr_token' not in payload` (BR-00-34 GIỮ); KHÔNG `gross_purchase_amount`/`current_book_value`/`accumulated_depreciation`/`supplier` trong payload | State-based (no-leak, FR-00-103 #5) |

| TC (FE — `AssetScanInfoView.test.ts`) | Kịch bản | Verify |
|---|---|---|
| `serial line renders verbatim` | mock `getAssetScanInfo` → `manufacturer_sn:'SN-12345'` | `[data-test="scan-serial"]` text == `'SN-12345'` (FR-00-103 #7) |
| `serial empty → 'Chưa rõ'` | `manufacturer_sn` ∈ {`''`, `null`, `undefined`, `'   '`} | text == `'Chưa rõ'`; KHÔNG `'—'`; KHÔNG `'null'`/`'undefined'` (FR-00-103 #8 — RED-first) |
| `serial empty does NOT leak docname` | `manufacturer_sn:''` + `name:'AST-0042-x9'` | `[data-test="scan-serial"]` text == `'Chưa rõ'` (KHÔNG `'AST-0042-x9'`) (FR-00-103 #9 — no-raw-docname-leak) |
| `serialText no info.name fallback (grep)` | grep `serialText` trong `AssetScanInfoView.vue` | KHÔNG chứa `info.name`/`info.value?.name`; đúng 1 hằng `SERIAL_UNKNOWN='Chưa rõ'` (FR-00-103 #9/#10) |

> **Pattern empty-fallback (FE):** TC empty dùng `it.each(['', null, undefined, '   '])` → mỗi biến thể assert `serialText`/DOM == `'Chưa rõ'` — bao trùm coalesce-BE-`''` + defensive-FE (null/undefined/whitespace payload partial/stale). KHÔNG so `info.name` ⟹ chứng minh no-docname-leak ngay cả khi serial rỗng + name có giá trị.

**REG (acceptance đề mục):** `TestAssetScanInfo` (+ `…PmOverdue`/`…CalibrationOverdue`/`…AvailableActions`), `TestResolveQrToken`/`TestResolveQrTokenWhitespace`/`TestAssetScanInfoNameWhitespace`, `TestQrWhitelistHttpLayer`, label-pdf suite — GIỮ GREEN, 0 regression. Payload shape additive (11→12-field, FE chịu được key mới). KHÔNG đổi RBAC / IDOR / rate-limit (BR-00-29) / no-raw-token (BR-00-34) / no-audit (A2/D4) / `available_actions` shape.

#### III.6.n-PILLA11Y — Vòng 39: status pill lifecycle `role="status"` + `aria-label` VI (SSoT `statusLabel`) + anchor `data-test="scan-status"` — FR-00-104 / BR-00-53 / ADR §D14 — **NEW (FE-only)**

File FE: cập nhật `frontend/src/views/asset/AssetScanInfoView.test.ts` (thêm TC pill a11y + anchor + exactly-one). **KHÔNG file BE** (FE-only, KHÔNG đụng `build_asset_scan_info`/payload). **RED-first BẮT BUỘC:** TC assert `wrapper.get('[data-test="scan-status"]')` + `role==='status'` + `aria-label` khớp `'Trạng thái thiết bị: ' + statusLabel` ĐỎ trước khi thêm 3 attr (pill cũ chỉ có `class`/`:class` → `[data-test="scan-status"]` không tồn tại / `role` undefined) → thêm `data-test="scan-status"` + `role="status"` + `:aria-label` lên `<span>` pill (`AssetScanInfoView.vue:445-450`) → GREEN. Đo QUA mount THẬT `AssetScanInfoView` (mock `getAssetScanInfo` trả payload với `lifecycle_status` biến thể — KHÔNG mock `lifecycleStatusLabel`; aria-label phải bằng giá-trị `statusLabel` THẬT để chứng minh SSoT-shared). Spec: [`02 §IV.29 / FR-00-104 / BR-00-53`](./02_Analysis_Design.md) + [`06 §II.3e-PILLA11Y`](./06_Frontend_Design.md) + [ADR §D14](./ADR-IMM00-QR-SCAN-ACTION.md). Parity §II.3e-PILLNOLEAK (no-EN/raw-code/empty leak — Vòng 8) cho nhánh aria-label.

**Acceptance — chạy XANH:** `vitest AssetScanInfoView.test.ts` (TC pill-a11y mới + baseline pill no-leak/PM-overdue/cal-overdue/serial/available-actions) GREEN + `vue-tsc` 0 + full asset-domain vitest no-regression. **KHÔNG BE test / KHÔNG `bench migrate` / KHÔNG reload** (FE-only template attr — `statusLabel`/`statusClass`/`constants/labels.ts`/payload KHÔNG đổi). `CAP_SET_VERSION` GIỮ `v97.c30c69b8974d`. **Verify Playwright/quét-QR-thật BLOCKED reload gunicorn --preload (HARD-STOP USER) → vitest + code-audit là gate hợp lệ; KHÔNG tuyên bố DONE live.**

| TC (FE — `AssetScanInfoView.test.ts`) | Kịch bản | Verify |
|---|---|---|
| `status pill has stable anchor` | mount với `lifecycle_status:'Active'` | `wrapper.get('[data-test="scan-status"]')` tồn tại; text == `statusLabel` (`'Đang hoạt động'`) (FR-00-104 #1) |
| `status pill role=status` | mount bất kỳ `lifecycle_status` | `[data-test="scan-status"]` attr `role==='status'` (FR-00-104 #2 — RED-first) |
| `aria-label shares statusLabel (SSoT)` | `lifecycle_status:'Active'` | `aria-label === 'Trạng thái thiết bị: Đang hoạt động'` (== `'Trạng thái thiết bị: ' + statusLabel`); KHÔNG hardcode wording riêng (FR-00-104 #3) |
| `aria-label WCAG 1.4.1 non-empty` | mount | pill có (text != '' ∧ role=status ∧ aria-label != '') — parity 2 overdue badge (FR-00-104 #4) |
| `aria-label no-EN/empty leak` | `it.each(['', 'In Use', 'LegacyUnknown', null, undefined])` | text pill VÀ `aria-label === 'Trạng thái thiết bị: Không xác định'`; `aria-label` KHÔNG chứa `'In Use'`/`'LegacyUnknown'` (FR-00-104 #5 — parity §II.3e-PILLNOLEAK) |
| `class/màu giữ nguyên` | `lifecycle_status:'Active'` vs `''` | `[data-test="scan-status"]` `:class` == `statusClass` cũ (Active → màu cũ; rỗng/lạ → `bg-gray-100 text-gray-600`) — chỉ THÊM attr, KHÔNG đổi class (FR-00-104 #6) |
| `exactly one scan-status anchor` | mount payload có `pm_overdue:true` + `calibration_overdue:true` + ≥1 CTA enabled urgency | `wrapper.findAll('[data-test="scan-status"]').length === 1` (2 overdue badge + CTA chip/button KHÔNG nhận selector) (FR-00-104 #7) |
| `overdue badges a11y intact` *(regression)* | `pm_overdue:true`/`calibration_overdue:true` | badge `getByText('Quá hạn bảo trì')`/`('Quá hạn hiệu chuẩn')` vẫn `role=status` + `aria-label` riêng; KHÔNG bị anchor mới ảnh hưởng (FR-00-104 #8) |

> **Pattern aria-label-SSoT (FE):** TC aria-label assert bằng `'Trạng thái thiết bị: ' + statusLabel` (ghép động từ CHÍNH `statusLabel`) — KHÔNG so literal cứng — chứng minh aria-label đọc chung SSoT `lifecycleStatusLabel`, đổi nhãn → aria-label đổi theo (no-drift). Nhánh empty/lạ tái dùng `it.each` của §II.3e-PILLNOLEAK ⟹ no-EN/raw-code/empty leak bao trùm CẢ text pill LẪN aria-label.

**REG (acceptance đề mục):** §II.3e-PILLNOLEAK (`lifecycleStatusLabel` no-leak), §II.3c-PMOVERDUE/§II.3d-CALOVERDUE (overdue badge a11y), §III.6.m-SCANSN (serial), §III.6.d-REASONNONEMPTY (action reason) — GIỮ GREEN, 0 regression. FE-only: KHÔNG đổi `statusClass`/màu / `constants/labels.ts` logic / BE payload / RBAC / `available_actions` shape.

#### III.6.o-SCANRISKURGENT — Vòng 47: dòng "Phân loại rủi ro" cờ urgency High/Critical (`role="status"` + `aria-label` VI SSoT `riskText` + anchor `data-test="scan-risk-urgent"`) — derive THUẦN enum-equality (no client-clock) — FR-00-105 / BR-00-54 / ADR §D15 — **NEW (FE-only)**

File FE: cập nhật `frontend/src/views/asset/assetScanInfoRisk.test.ts` (thêm TC cờ urgency — file vòng 38 đã có TC nhãn `riskText`) + `AssetScanInfoView.test.ts` (TC integration). **KHÔNG file BE** (FE-only, KHÔNG đụng `build_asset_scan_info`/payload — BE đã emit `risk_classification` coalesce `''`). **RED-first BẮT BUỘC:** TC assert `wrapper.find('[data-test="scan-risk-urgent"]')` tồn tại + `role==='status'` + `aria-label` khớp `'Cảnh báo rủi ro cao: ' + riskText` ĐỎ trước khi thêm (dòng risk cũ chỉ có `riskText`, KHÔNG cờ) → thêm computed `riskUrgent` + 3 hằng VI + phần tử `data-test="scan-risk-urgent"` vào `AssetScanInfoView.vue` (dòng `:466-473`) → GREEN. Đo QUA mount THẬT `AssetScanInfoView` (mock `getAssetScanInfo` trả payload với `risk_classification` biến thể — KHÔNG mock `riskClassificationLabel`; aria-label phải bằng giá-trị `riskText` THẬT để chứng minh SSoT-shared). Spec: [`02 §IV.30 / FR-00-105 / BR-00-54`](./02_Analysis_Design.md) + [`06 §II.3f-SCANRISKURGENT`](./06_Frontend_Design.md) + [ADR §D15](./ADR-IMM00-QR-SCAN-ACTION.md). Parity nguyên-tắc overdue-SSoT vòng 21 (derive cờ server, no client-clock) + status-pill a11y vòng 39 (role=status + aria-label SSoT-shared).

**Acceptance — chạy XANH:** `vitest` (`assetScanInfoRisk.test.ts` TC urgency mới + `AssetScanInfoView.test.ts` + baseline riskText nhãn vòng 38/40 + pill-a11y/serial/overdue) GREEN + `vue-tsc` 0 + full asset-domain vitest no-regression. **KHÔNG BE test / KHÔNG `bench migrate` / KHÔNG reload** (FE-only template + computed — `riskText`/`RISK_CLASSIFICATION_LABEL`/`constants/labels.ts`/payload KHÔNG đổi). `CAP_SET_VERSION` GIỮ `v97.c30c69b8974d`. **Verify Playwright/quét-QR-thật BLOCKED reload gunicorn --preload (HARD-STOP USER) → vitest + code-audit là gate hợp lệ; KHÔNG tuyên bố DONE live.**

| TC (FE — `assetScanInfoRisk.test.ts` / `AssetScanInfoView.test.ts`) | Kịch bản | Verify |
|---|---|---|
| `risk urgent flag for High` | mount `risk_classification:'High'` | `riskUrgent===true`; `findAll('[data-test="scan-risk-urgent"]').length===1`; phần tử chứa icon ⚠ + nhãn VI `'Rủi ro cao'` (FR-00-105 #1 — RED-first) |
| `risk urgent flag for Critical` | mount `risk_classification:'Critical'` | `findAll('[data-test="scan-risk-urgent"]').length===1`; (FR-00-105 #1) |
| `no false-alarm Low/Medium` | `it.each(['Low','Medium'])` | `riskUrgent===false`; `findAll('[data-test="scan-risk-urgent"]').length===0` (FR-00-105 #2) |
| `no false-alarm empty/Other` | `it.each(['', null, undefined, '   ', 'UNKNOWN_DRIFT'])` | `riskUrgent===false`; 0 urgent-anchor (FR-00-105 #2) |
| `derive pure enum-equality (no client-clock)` | grep source `AssetScanInfoView.vue` | `riskUrgent` KHÔNG chứa `Date(`/`Date.now`/`new Date`/so-ngày; tập = hằng `RISK_URGENT_VALUES` SSoT (FR-00-105 #3) |
| `urgent element role=status` | mount `risk_classification:'Critical'` | `[data-test="scan-risk-urgent"]` attr `role==='status'` (KHÔNG `'alert'` — BA chốt) (FR-00-105 #4) |
| `aria-label shares riskText (SSoT)` | `'Critical'` → `'Nghiêm trọng'`; `'High'` → `'Cao'` | `aria-label === 'Cảnh báo rủi ro cao: Nghiêm trọng'` / `'…: Cao'` (== `'Cảnh báo rủi ro cao: ' + riskText`); KHÔNG hardcode wording riêng (FR-00-105 #5) |
| `no-EN-leak ở cờ + aria-label` | `'High'`/`'Critical'` | urgent-anchor + `aria-label` KHÔNG chứa `'High'`/`'Critical'` thô; nhãn = từ VI `'Rủi ro cao'` (FR-00-105 #6) |
| `riskText + nhãn-mức GIỮ no-regress` | `it.each([['High','Cao'],['Critical','Nghiêm trọng'],['Low','Thấp'],['Medium','Trung bình'],['','Chưa phân loại'],['UNKNOWN_DRIFT','Khác']])` | dòng `data-test="scan-risk"` text == `'Phân loại rủi ro: ' + viLabel` byte-for-byte (vòng 38/40) (FR-00-105 #7) |
| `scan-risk anchor exactly-one + urgent exactly-one` | mount `'Critical'` | `findAll('[data-test="scan-risk"]').length===1` (no-regress); `findAll('[data-test="scan-risk-urgent"]').length===1`; KHÔNG đụng overdue/status-pill/CTA chip (FR-00-105 #8) |
| `WCAG 1.4.1 non-color-only` | mount `'High'` | urgent có (icon ⚠ aria-hidden + text VI `'Rủi ro cao'` ∧ `role=status` ∧ `aria-label!=''`) — parity overdue badge (FR-00-105 #9) |

> **Pattern aria-label-SSoT (FE):** TC aria-label assert bằng `'Cảnh báo rủi ro cao: ' + riskText` (ghép động từ CHÍNH `riskText`) — KHÔNG so literal cứng — chứng minh aria-label đọc chung SSoT `riskClassificationLabel`, đổi nhãn → aria-label đổi theo (no-drift), no-EN-leak bao trùm.

**REG (acceptance đề mục):** §II.3f-SCANRISKURGENT mới + nhãn `riskText` (vòng 38, `assetScanInfoRisk.test.ts` TC1-TC7) — GIỮ GREEN 0 regression; §II.3e-PILLA11Y (status-pill), §II.3c-PMOVERDUE/§II.3d-CALOVERDUE (overdue badge), §III.6.m-SCANSN (serial) — GIỮ XANH. FE-only: KHÔNG đổi `riskText`/`RISK_CLASSIFICATION_LABEL` logic / BE payload / RBAC / `available_actions` shape.

#### III.6.q-SAFEDATE — Vòng 50: crash-safe `getdate` ở 4 hàm xử-lý-ngày của `build_asset_scan_info` (`_is_warranty_expired`/`_is_pm_overdue`/`_is_calibration_overdue`/`_date_str_or_none`) degrade graceful ngày drift → `None`/`False`, bịt HTTP-500 traceback-leak — FR-00-107 / BR-00-56 / ADR §D17 — **NEW (BE-only)**

File BE: **bổ sung** vào `assetcore/tests/test_imm00.py` — mở rộng `TestWarrantyExpiredHelper` (BE-WAR-EDGE-1..3 helper parse-fail) + `TestWarrantyInScanInfo` (BE-WAR-EDGE-4 integration degrade) HOẶC class mới `TestScanDateCrashSafe`. **KHÔNG file FE** (BE-only — payload type `str|None`/`bool` GIỮ; FE đọc cờ server như cũ). **RED-first BẮT BUỘC:** TC `_is_warranty_expired('not-a-date')` assert `is False` ĐỎ trước fix (`getdate` raise `frappe.exceptions.ValidationError` → test fail vì exception, KHÔNG return) → thêm helper SSoT `_safe_getdate` + đổi 4 hàm dùng nó (vế giá-trị-DB) → GREEN; TC integration `build_asset_scan_info` trên asset 1-field-ngày-drift assert no-raise + payload 16-key ĐỎ trước fix (build raise) → GREEN. Đo QUA helper + `build_asset_scan_info` THẬT (Administrator; tạo AC Asset thật rồi inject chuỗi drift qua `frappe.db.sql UPDATE` raw — KHÔNG `get_doc().insert()` vì Frappe chặn Date-validate — HOẶC monkeypatch `frappe.db.get_value` trả row có chuỗi xấu). Spec: [`04 §II.1.8e-SAFEDATE`](./04_Backend_Design.md) + [`02 §IV.32 / FR-00-107 / BR-00-56`](./02_Analysis_Design.md) + [ADR §D17](./ADR-IMM00-QR-SCAN-ACTION.md). Parity FE `formatIsoDateLabel` ISO-strict (vòng 18-19 — nay đối xứng ở BE).

**Acceptance — chạy XANH:** `bench --site miyano run-tests --module assetcore.tests.test_imm00` GREEN (fresh-import, KHÔNG reload — service `.py`, test import trực tiếp; KHÁC `api/imm00.py` reload-gated) gồm BE-WAR-EDGE-1..6 mới + `TestWarrantyExpiredHelper` BE-WAR-1..5 + `TestWarrantyInScanInfo` BE-WAR-6..8 + `TestAssetScanInfo`(+`…PmOverdue`/`…CalibrationOverdue`/`…AvailableActions`) baseline — 0 regression. `bench migrate` KHÔNG cần (0 schema/patch). `CAP_SET_VERSION` GIỮ `v97.c30c69b8974d`. **KHÔNG marker-trust — đọc OK count THẬT.** **Verify HTTP/Playwright/quét-QR-thật BLOCKED reload gunicorn --preload (HARD-STOP USER) → `bench run-tests` + code-audit là gate hợp lệ; KHÔNG tuyên bố DONE live.**

| TC (BE) | Kịch bản | Verify | Kỹ thuật |
|---|---|---|---|
| `test_be_war_edge_1_warranty_garbage_date_false_no_raise` | `_is_warranty_expired('not-a-date')` / `_is_warranty_expired('2020-13-45')` | trả `False`; KHÔNG ném `frappe.exceptions.ValidationError` (bọc `try`/`assertRaises`-negative) | EP (parse-fail → False, BE-WAR-EDGE-1 — RED-first: `getdate` raise trước fix) |
| `test_be_war_edge_2_overdue_garbage_date_false_no_raise` | `_is_pm_overdue('garbage', None)` + `_is_calibration_overdue('2020-99-99', None)` | cả 2 trả `False`; KHÔNG raise (parity warranty — date dị-dạng KHÔNG bịa cờ quá hạn) | EP (parity overdue, BE-WAR-EDGE-2) |
| `test_be_war_edge_3_date_str_or_none_garbage_returns_none` | `_date_str_or_none('not-a-date')` | trả `None`; KHÔNG raise; KHÔNG leak `'not-a-date'` verbatim (parity FE ISO-strict) | EP (parse-fail → None, BE-WAR-EDGE-3) |
| `test_be_war_edge_4_scan_info_drift_date_degrades_field_independent` *(assert-chính, integration)* | AC Asset thật, inject `warranty_expiry_date='not-a-date'` (hoặc `next_pm_date`/`next_calibration_date`) qua `frappe.db.sql UPDATE` raw / monkeypatch `get_value` → `build_asset_scan_info(asset.name)` | KHÔNG raise; `set(payload.keys())` == 16-key đầy-đủ; field-lỗi degrade (`warranty_expired is False` / `pm_overdue is False` / `warranty_expiry_date is None`); 13 field còn lại GIỮ (vd `asset_code`/`asset_name`/`lifecycle_status` đúng); cấm-financial ∩ keys = ∅; KHÔNG traceback-leak | State-based (degrade field-độc-lập, BE-WAR-EDGE-4 — RED-first: build raise trước fix) |
| `test_be_war_edge_5_valid_values_no_regress` *(regression)* | `it`/loop: `date(2020,1,1)` (past) → `_is_warranty_expired`→`True`; `nowdate()`→`False`; `add_days(nowdate(),30)`→`False`; `None`/`''`→`False`; `_date_str_or_none(date(2020,1,15))`→`'2020-01-15'`; `_date_str_or_none(None/'')`→`None` | mọi giá-trị HỢP LỆ GIỮ NGUYÊN hành vi cũ; `TestWarrantyExpiredHelper` BE-WAR-1..5 + `TestWarrantyInScanInfo` BE-WAR-6..8 byte-for-byte XANH | EP (no-regress, BE-WAR-EDGE-5) |
| `test_be_war_edge_6_guard_only_swallows_parse_error` *(no-mask)* | grep/AST 4 helper + `_safe_getdate` | `except` clause CHỈ `(frappe.exceptions.ValidationError, ValueError, TypeError)`; KHÔNG `except Exception`/`except:` trần; comment giải-thích degrade-an-toàn (drift/legacy) tồn tại; (tùy) inject exception KHÁC parse (vd `KeyError`) vào getdate-path → VẪN propagate | White-box / Grep-guard (no-mask-real-bug, BE-WAR-EDGE-6) |

> **Pattern inject-drift (BE):** Date col KHÔNG nhận chuỗi rác qua `frappe.get_doc().insert()` (Frappe Date-validate). 2 cách hợp lệ: (a) `frappe.db.sql("UPDATE \`tabAC Asset\` SET warranty_expiry_date=%s WHERE name=%s", ('not-a-date', asset.name))` (mô phỏng drift raw-SQL/legacy import — MariaDB chấp nhận syntax) rồi `build_asset_scan_info` đọc lại; (b) monkeypatch `frappe.db.get_value` trả row dict có chuỗi xấu (deterministic, KHÔNG phụ thuộc SQL-mode). Cả 2 chứng minh degrade — BE chọn; teardown rollback sạch. **`_safe_getdate` test trực-tiếp** (BE-WAR-EDGE-1..3) độc lập DB — gọi hàm với chuỗi literal.

**REG (acceptance đề mục):** `TestWarrantyExpiredHelper` (BE-WAR-1..5) + `TestWarrantyInScanInfo` (BE-WAR-6..8) + `TestAssetScanInfo`(+`…PmOverdue`/`…CalibrationOverdue`/`…AvailableActions`) + §III.6.f-PMDATESTR + §III.6.b-CALOVERDUE (3 trường-ngày scan-info) — GIỮ GREEN, 0 regression (giá-trị hợp-lệ degrade-path KHÔNG kích hoạt). BE-only: KHÔNG đổi payload type/key/shape / RBAC / IDOR / rate-limit / no-audit / `available_actions` shape; FE KHÔNG đụng.

#### III.6.d-REASONNONEMPTY — factory vòng 7: action disabled LUÔN kèm `reason` VI — bịt lỗ status rỗng/lạ — FR-00-92 / BR-00-41 / ADR §D9

File BE: **bổ sung** class `TestScanInfoAvailableActions` (`assetcore/tests/test_imm00.py:3463` — ĐÃ tồn tại từ vòng QR-SCAN-ACTION) + **SIẾT** `test_unknown_status_safe_default` (`:3719`). File FE: cập nhật `frontend/src/views/asset/AssetScanInfoView.test.ts` (thêm TC reason non-rỗng + non-dangling aria-describedby). **RED-first BẮT BUỘC:** TC unknown/empty-status assert `reason == _LIFECYCLE_REASON_UNKNOWN` + bất biến `enabled=False ⟹ reason!=""` ĐỎ trước fix (hiện `reason==""` cho status rỗng/lạ + Admin) → thêm hằng `_LIFECYCLE_REASON_UNKNOWN` + bậc-3 `or` ở `_build_available_actions` → GREEN. Đo QUA `build_asset_scan_info` THẬT (Administrator có mọi DocPerm = nhánh lifecycle thuần; monkeypatch `svc.rbac.can` ép thiếu cap — KHÔNG mock `getdate`/`nowdate`). Spec: [`04 §II.1.8f`](./04_Backend_Design.md) + [`05 §III.1 available_actions`](./05_API_Specification.md) + [`02 §IV.18 / BR-00-41`](./02_Analysis_Design.md) + [`06 §reason-render`](./06_Frontend_Design.md) + [ADR §D9](./ADR-IMM00-QR-SCAN-ACTION.md).

**Acceptance — chạy XANH:** `bench --site miyano run-tests test_imm00` (`TestScanInfoAvailableActions` mở rộng + baseline) GREEN + `vitest AssetScanInfoView` GREEN. `bench migrate` KHÔNG cần (0 schema/patch). `CAP_SET_VERSION` GIỮ NGUYÊN. **Logic-level / vitest — KHÔNG tuyên bố verify HTTP/Playwright live** (endpoint live cần USER reload — STATE 🔴#1).

| TC (BE) | Kịch bản | Verify | Kỹ thuật |
|---|---|---|---|
| `test_empty_status_with_cap_reason_unknown` | asset `lifecycle_status=''` (`set_value`) + Admin (đủ 4 cap) | 4 action `enabled is False`; `reason == _LIFECYCLE_REASON_UNKNOWN` ("Thiết bị không ở trạng thái cho phép thao tác này") | EP (FR-00-92 D9-2) |
| `test_unknown_status_with_cap_reason_unknown` | `lifecycle_status='Trạng-thái-lạ'` + Admin | 4 action disabled; `reason == _LIFECYCLE_REASON_UNKNOWN` | EP (mã lạ ngoài enum) |
| `test_unknown_status_missing_cap_reason_capability` | `lifecycle_status=''` + monkeypatch `rbac.can` ép `pm.create=False` | `request_pm.reason == _CAPABILITY_REASON` (bậc 2 ưu tiên bậc 3, KHÔNG unknown, KHÔNG rỗng); các action có cap → `_LIFECYCLE_REASON_UNKNOWN` | EP (FR-00-92 D9-3 — ưu tiên cap) |
| `test_disabled_always_has_reason_all_statuses` | quét 7+ status `{Active, Commissioned, Under Maintenance, Under Repair, Calibrating, Out of Service, Decommissioned, Draft, '', 'Trạng-thái-lạ'}` × 4 action | `for a in available_actions: a["enabled"] is False ⟹ a["reason"] != ""` (KHÔNG ô disabled-rỗng) | Integration (bất biến D9-1) |
| `test_enabled_reason_empty_invariant` *(regression)* | Active + đủ cap | mọi action `enabled is True` ⟹ `reason == ""` | EP (bất biến cũ D9-5) |
| `test_known_status_reason_byte_for_byte` *(regression)* | Decommissioned / Out of Service / Draft + đủ cap | reason **byte-for-byte**: "Thiết bị đã thanh lý" / "Thiết bị đang ngừng hoạt động — chỉ cho phép báo hỏng / yêu cầu sửa chữa" (pm/cal) / "Thiết bị chưa đưa vào vận hành" — KHÔNG đổi | EP (no-regression D9-4) |
| `test_unknown_status_safe_default` *(SIẾT)* | `lifecycle_status=''` qua payload | GIỮ 4 disabled + **THÊM** assert `a["reason"] != ""` (trước đây chỉ `isinstance(str)` = false-green) | White-box (siết hole) |
| `test_reason_no_en_leak` | mọi reason non-rỗng | reason ∈ tập 4 hằng VI BE; grep KHÔNG ký tự EN-status thô / KHÔNG `[a-z]{3,}` tiếng Anh lọt | Static (no-EN-leak) |
| `test_shape_unchanged_with_unknown_status` *(regression)* | `lifecycle_status=''` | mỗi phần tử `set(a.keys()) == {key,label,route,enabled,reason}` — KHÔNG field thừa | EP (shape D9-7) |

| TC (FE — `AssetScanInfoView.test.ts`) | Kịch bản | Verify |
|---|---|---|
| `disabled action có reason → title + li#reason tồn tại` | payload action `{enabled:false, reason:'Thiết bị đã thanh lý'}` | nút `disabled`; `title==reason`; tồn tại `<li id="reason-<key>">` (aria-describedby trỏ element THẬT); `aria-label` kết thúc bằng reason thực (KHÔNG trailing `: `) |
| `mọi nút disabled đều có li reason (no-dangling)` | payload 4 action disabled reason non-rỗng | `li[id^="reason-"]` count == số nút disabled; KHÔNG `aria-describedby` dangling |
| `nút enabled không có aria-describedby/title` *(regression)* | action `enabled:true, reason:''` | `aria-describedby`/`title` undefined |

> **Pattern siết false-green:** TC cũ `test_unknown_status_safe_default` chỉ `assertIsInstance(a["reason"], str)` ⟹ `""` PASS (lỗ hổng). Đổi/thêm assert `assertNotEqual(a["reason"], "")` (HOẶC `self.assertTrue(a["reason"])`) → ĐỎ trước fix → chứng minh test thật bắt được hole.

**REG (acceptance đề mục):** `TestScanInfoAvailableActions` baseline (Active 4-enabled / Decommissioned-Draft-OoS reason / missing-cap / lifecycle>capability priority / shape / capability-map-D1 / no-raw-token parity) GIỮ GREEN; reason 5 status đã biết byte-for-byte; shape `{key,label,route,enabled,reason}` + `CAP_SET_VERSION` KHÔNG đổi; FE `vitest` baseline (badge PM/calibration + 4-action enabled/disabled) GIỮ XANH; `vue-tsc` 0 lỗi. KHÔNG schema/migration/reload.

#### III.6.e-PILLNOLEAK — factory vòng 8: status pill VI an toàn — `lifecycleStatusLabel` no-EN/raw-code/empty leak — FR-00-93 / BR-00-42 / ADR §D10

> **Đề mục factory vòng 8 (2026-06-11 — scan-action / status-pill no-EN-leak — Self-Correction lỗi thiết kế gốc FE-formatter).** **FE-only** — BE KHÔNG đổi (`build_asset_scan_info`/`resolve_qr_token` GIỮ `or ""`). File FE: `frontend/src/constants/labels.test.ts` (mở rộng block `lifecycleStatusLabel`/`lifecycleStatusClass` — ĐÃ có) + `frontend/src/views/asset/AssetScanInfoView.test.ts` (thêm TC pill rỗng/lạ). **RED-first BẮT BUỘC:** TC mã-lạ (`'In Use'`/`'Retired'`/`'active'`) + rỗng (`''`/null/undefined) assert `=== 'Không xác định'` ĐỎ trước fix (hiện `?? v` trả raw/empty) → thêm hằng `LIFECYCLE_STATUS_UNKNOWN_LABEL` + đổi fallback formatter → GREEN. Spec: [`06 §status-pill-safe`](./06_Frontend_Design.md) + [`02 §IV.19 / BR-00-42`](./02_Analysis_Design.md) + [ADR §D10](./ADR-IMM00-QR-SCAN-ACTION.md).

**Acceptance — chạy XANH:** `vitest` (`labels.test.ts` + `AssetScanInfoView.test.ts`) GREEN + `vue-tsc` 0 lỗi + full asset-domain vitest suite no-regression. **KHÔNG cần reload/migrate** (FE-only — BE KHÔNG đổi). KHÔNG tuyên bố verify HTTP/Playwright live.

| TC (FE — `labels.test.ts`) | Kịch bản | Verify |
|---|---|---|
| `lifecycleStatusLabel mã lạ legacy → 'Không xác định'` *(RED-first)* | `lifecycleStatusLabel('In Use')` / `'Retired'` / `'active'` (chữ thường) | `=== 'Không xác định'`; `!== 'In Use'`/`!== 'Retired'`/`!== 'active'` (no-EN/raw-code leak) |
| `lifecycleStatusLabel('') → 'Không xác định'` *(RED-first)* | `''` (BE phát `or ""` cho legacy asset) | `=== 'Không xác định'` (KHÔNG `''` — pill không box trống) |
| `lifecycleStatusLabel null/undefined → 'Không xác định'` | `null as any` / `undefined as any` | `=== 'Không xác định'` (phòng thủ) |
| `lifecycleStatusLabel no-EN-leak grep` | mọi `v` lạ | kết quả KHÔNG chứa mã English `[A-Za-z]{2,}` ngoài từ VI có dấu |
| `lifecycleStatusLabel 7 canonical byte-for-byte` *(regression, FROZEN)* | mỗi mã canonical | nhãn VI cũ (Active→'Đang hoạt động', Under Maintenance→'Đang bảo trì', …) — KHÔNG đổi |
| `lifecycleStatusClass mã lạ/rỗng → gray` *(verify giữ nguyên)* | `'In Use'` / `''` / `'Retired'` | `=== 'bg-gray-100 text-gray-600'` (chip trung tính — KHÔNG rơi màu trạng thái khác) |
| `lifecycleStatusClass 7 canonical màu cũ` *(regression, FROZEN)* | mỗi mã canonical | màu cũ (Active→green, Under Maintenance→orange, Out of Service→red, …) — KHÔNG đổi |

| TC (FE — `AssetScanInfoView.test.ts`) | Kịch bản | Verify |
|---|---|---|
| `pill status rỗng → 'Không xác định' no-raw-code` | payload `info.lifecycle_status=''` | text status pill = `'Không xác định'`; snapshot/text KHÔNG chứa mã English; class pill = gray trung tính |
| `pill status lạ → 'Không xác định' no-EN-leak` | `info.lifecycle_status='In Use'` (legacy/drift) | text pill = `'Không xác định'`, KHÔNG `'In Use'`; KHÔNG `[A-Za-z]{2,}` mã English trên pill |
| `pill status canonical → nhãn VI đúng` *(regression)* | `info.lifecycle_status='Active'` | text pill = `'Đang hoạt động'`; class = green (byte-for-byte) |

> **Pattern RED-first:** TC mã-lạ/rỗng FAIL trước fix vì `lifecycleStatusLabel(v) = ... ?? v` trả `'In Use'`/`''` thô → assert `=== 'Không xác định'` ĐỎ → đổi fallback `?? LIFECYCLE_STATUS_UNKNOWN_LABEL` → GREEN. Chứng minh test thật bắt được leak.

**REG (acceptance đề mục):** block `lifecycleStatusLabel`/`lifecycleStatusClass` baseline (`labels.test.ts` — 7 canonical phủ-đủ + wording-drift-guard khớp `translateStatus` + FROZEN 6 mã) GIỮ GREEN; `AssetScanInfoView.test.ts` baseline (renders_mobile_payload + badge PM/calibration + 4-action) GIỮ XANH; `vue-tsc` 0 lỗi; full asset-domain vitest no-regression. BE KHÔNG đổi → `CAP_SET_VERSION`/schema/payload-shape KHÔNG đổi; KHÔNG migration/reload.

### III.6.b — B item 2: `regenerate_asset_qr_token` — rotate QR token (ADR-001 D1/D3/D4)

File BE: thêm class `TestRegenerateAssetQrToken` vào `assetcore/tests/test_imm00.py` (cạnh `TestAssetLabelData` / `TestGetAssetScanInfo`). FE: `frontend/src/views/asset/assetDetailQrRegenerate.test.ts` (NEW) + cập nhật `routeAccess.test.ts` (không route mới — gate ở nút). **RED-first BẮT BUỘC** (class chưa tồn tại → ImportError/AttributeError → impl → GREEN). Đo QUA layer `require` với **user THẬT** có/không `asset.write` (KHÔNG mock `require`/`has_permission` — chống false-green; baseline 116 test giữ xanh).

| TC (BE) | Kịch bản | Expect | Kỹ thuật |
|---|---|---|---|
| `test_regenerate_creates_new_token_different` | asset có `qr_token=old` → `regenerate_asset_qr_token(asset)` | `qr_token` MỚI ≠ old; URL-safe ~22 ký tự (`secrets.token_urlsafe(16)`) | EP (positive) |
| `test_regenerate_overwrites_not_idempotent` | gọi regenerate 2 lần | mỗi lần ra token KHÁC nhau (KHÔNG idempotent — đối lập `ensure_asset_qr_token`) | State (rotate≠ensure) |
| `test_regenerate_old_token_no_longer_resolves` | rotate xong | `resolve_qr_token(old)` → `None`/404; `resolve_qr_token(new)` → asset đúng | Use Case (vô hiệu hoá nhãn cũ — acceptance) |
| `test_regenerate_emits_qr_regenerated_event` | rotate có quyền | ĐÚNG **1** `Asset Lifecycle Event` `event_type='qr_regenerated'` (root_doctype/record='AC Asset'/name) | Integration (lifecycle) |
| `test_regenerate_emits_audit_no_raw_token` | rotate | ĐÚNG **1** `IMM Audit Trail`; `change_summary` nêu rotate/vô-hiệu-hoá; **KHÔNG chứa** giá trị `old`/`new` token (assert token NOT IN change_summary/notes) | Integration (no-leak audit) |
| `test_regenerate_print_only_user_403` *(D6: đổi từ `_read_only_user_403`)* | user CÓ `asset.print` NHƯNG KHÔNG `asset.qr.rotate` (Commissioning User write=0) | `PermissionError` (403); `qr_token` KHÔNG đổi; KHÔNG ghi event/audit | EP (tách quyền) |
| `test_regenerate_write_user_200_new_token` | user có `asset.qr.rotate` (write=1) | 200; token đổi; 1 event + 1 audit | Use Case (positive) |
| `test_regenerate_unknown_asset_404` | asset không tồn tại | **404** `AC-E001` (KHÔNG 500, KHÔNG đoán id); KHÔNG ghi gì | Error guessing (leak-safe) |
| `test_regenerate_vendor_out_of_scope_forbidden_no_leak` | vendor user (có asset.qr.rotate), asset NGOÀI scope | **403** (`assert_vendor_can_access`); token KHÔNG đổi; KHÔNG ghi event | IDOR |
| `test_regenerate_label_reflects_new_token` | rotate xong → `get_asset_label_data(asset)` | `qr_url` chứa token MỚI (deep-link mới), KHÔNG còn token cũ | Integration (nhãn phản ánh token mới) |
| `test_regenerate_response_no_raw_token` | rotate 200 | envelope `data` = `{name, qr_url}`; **KHÔNG** field token thô | Contract (no-leak) |
| `test_rotate_cap_in_map_and_version_changed` *(D6)* | sau migrate | `CAP_SET_VERSION == "v97.c30c69b8974d"`; `asset.qr.rotate`→(AC Asset,"write") ∈ CAPABILITY_MAP | Static (version guard) |

| TC (FE) | Kịch bản | Verify |
|---|---|---|
| `assetDetailQrRegenerate.test.ts` (D6) | mock caps `{asset.read:true}` (KHÔNG rotate) | nút "Sinh lại mã QR" KHÔNG render |
| `assetDetailQrRegenerate.test.ts` (D6) | mock caps `{asset.print:true}` (in được, KHÔNG rotate) | nút "Sinh lại mã QR" KHÔNG render (tách quyền) |
| `assetDetailQrRegenerate.test.ts` (D6) | mock caps `{asset.qr.rotate:true}` | nút "Sinh lại mã QR" render |
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

> **DoD Vòng 12 B:** `bench --site miyano run-tests test_imm00` GREEN (baseline **108+** + class `TestQrResolveRateLimit`); `bench migrate` sạch (KHÔNG schema/patch); `CAP_SET_VERSION` GIỮ `v95.3388ee5629c1`; FE KHÔNG đổi (vue-tsc/vitest baseline GIỮ NGUYÊN — BE-only). Grep-guard: hằng `AC_QR_RESOLVE_RATE_LIMIT` xuất hiện đúng 1 định nghĩa; `@rate_limit` áp đúng 2 endpoint resolve, **+1 rotate** (`regenerate_asset_qr_token` — bucket/hằng RIÊNG, §III.6.d-ROTATERL). **⚠️ Cập nhật Vòng 14 (§III.6.i-LABELRL):** `mark_label_printed` + `get_asset_label_data_batch` + `print_asset_labels_pdf` NAY CŨNG có `@rate_limit` (bucket/hằng RIÊNG) → CHỈ `get_asset_label_data` (single) còn unthrottled. Teardown PHẢI xoá `rl:*` cache (tránh rò trần sang test khác).

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

### III.6.i-LABELRL — Vòng 14: Rate-limit `mark_label_printed` (write-audit-amplification) + `get_asset_label_data_batch` (read) (BR-00-45 / BR-00-46 / FR-00-96/97) — **NEW** (Self-Correction, mirror rotate)

File BE: thêm class `TestLabelMarkBatchRateLimit` vào `assetcore/tests/test_imm00.py` (cạnh `TestQrRegenerateRateLimit`, **tái dùng pattern** `_http_call`/`_drain`/IP-uniq/teardown `rl:`). **BE-only test** (FE 429→RATE_LIMITED+VI ĐÃ CÓ từ §III.6.d-FE429 / FR-00-87/88 — KHÔNG cần TC FE mới). Spec contract: [`05 §I.7c` + `§III.1 mark_label_printed`/`get_asset_label_data_batch`](./05_API_Specification.md) + [`04 §II.1.8b-LABELRL`](./04_Backend_Design.md) + [`02 BR-00-45/46`](./02_Analysis_Design.md) + [ADR-IMM00-LABEL-PDF §D18](./ADR-IMM00-LABEL-PDF.md).

**Hạ tầng test (BẮT BUỘC — sai → false-green):** mô phỏng HTTP context (`frappe.local.request` truthy + `request_ip` per-test-uniq + `frappe.form_dict.cmd` = đúng path mỗi endpoint); user `asset.print` (DocPerm print=1 — Administrator hoặc role vận hành). Teardown xoá `rl:*`. Bypass test cũ (`TestMarkLabelPrinted`/batch suite gọi trực tiếp, không HTTP ctx) KHÔNG regress.

| TC (BE) | Kịch bản | Expect | Kỹ thuật |
|---|---|---|---|
| `test_label_mark_constant_value` | `from assetcore.api.imm00 import AC_LABEL_MARK_RATE_LIMIT` | `== 10` (hằng RIÊNG tồn tại) | Static (constant-value guard) |
| `test_label_batch_constant_value` | `from … import AC_LABEL_BATCH_RATE_LIMIT` | `== 20` | Static (constant-value guard) |
| `test_label_mark_le_regen` | `AC_LABEL_MARK_RATE_LIMIT <= AC_QR_REGEN_RATE_LIMIT` | True (mark cùng họ write-amplify như rotate → ngưỡng thấp) | Static (asymmetry-logic) |
| `test_label_batch_gt_mark` | `AC_LABEL_BATCH_RATE_LIMIT > AC_LABEL_MARK_RATE_LIMIT` | True (read-only ngưỡng cao hơn) | Static |
| `test_label_consts_distinct` | 2 hằng KHÔNG tái dùng `AC_QR_RESOLVE`/`AC_QR_REGEN` (giá-trị có thể trùng pdf nhưng tên RIÊNG) | tên hằng tồn tại độc lập | Static (no-reuse) |
| `test_label_decorator_presence` | `inspect.getsource(mark_label_printed)`/`get_asset_label_data_batch` | chứa `@rate_limit` + tên hằng đúng (`AC_LABEL_MARK_RATE_LIMIT`/`AC_LABEL_BATCH_RATE_LIMIT`); chống tái-gỡ âm thầm | Static (decorator-presence guard) |
| `test_mark_under_limit_ok` | dội ĐÚNG `AC_LABEL_MARK_RATE_LIMIT` call mark (HTTP ctx, asset thật, asset.print) | tất cả **200** `_ok`; ghi 2×N record/call như cũ | Boundary (≤N) |
| `test_mark_over_limit_429` | call thứ `AC_LABEL_MARK_RATE_LIMIT+1` mark cùng IP/cmd/60s | `frappe.RateLimitExceededError` (HTTP **429**) | Boundary (>N) |
| `test_mark_429_no_side_effect` | trước call vượt trần: count ALE `label_printed` + count IMM Audit Trail của asset; gọi call vượt trần | sau 429: **0 ALE `label_printed` MỚI + 0 IMM Audit Trail MỚI** (so trước+sau) | Security (no side-effect — CỐT LÕI) |
| `test_mark_429_no_leak` | vượt trần với asset thật | exception 429; message KHÔNG chứa `name`/`asset_code`/số-record | Security (no-leak parity) |
| `test_mark_429_runs_before_rbac` | user KHÔNG `asset.print` (Guest/chỉ-read), dội >N → call vượt trần | **429** (KHÔNG 403) — RL chặn TRƯỚC `rbac.require("asset.print")` | Order (RL→RBAC) |
| `test_batch_under_limit_ok` | dội ĐÚNG `AC_LABEL_BATCH_RATE_LIMIT` call batch | tất cả **200** `_ok` payload N-item | Boundary (≤N) |
| `test_batch_over_limit_429` | call thứ `AC_LABEL_BATCH_RATE_LIMIT+1` batch | `RateLimitExceededError` (429); 0 byte payload build | Boundary (>N) |
| `test_mark_batch_separate_bucket` | dội `AC_LABEL_MARK_RATE_LIMIT` mark (chạm trần mark) → 1 `get_asset_label_data_batch` cùng IP | batch **200** (bucket RIÊNG — mark KHÔNG bóp batch) | EP (per-endpoint isolation) |
| `test_label_no_request_context_bypasses` | gọi mark/batch TRỰC TIẾP >N lần (không HTTP ctx) | KHÔNG 429 (bypass test/CLI có chủ đích) — suite cũ KHÔNG regress | Negative (bypass) |
| `test_cap_set_version_unchanged` | sau khi thêm 2 decorator | `CAP_SET_VERSION == "v97.c30c69b8974d"` | Static (regression) |

**⚠️ ĐẢO test cũ `test_write_endpoints_not_rate_limited` (`test_imm00.py:5828`) — BẮT BUỘC:**
- Phần (a) static: XOÁ `mark_label_printed` + `get_asset_label_data_batch` khỏi danh sách "KHÔNG mang `@rate_limit`" → CHỈ còn `get_asset_label_data` (single) trong danh sách miễn (D18.5); THÊM assert 2 endpoint kia NAY MANG `@rate_limit` + hằng RIÊNG (mirror dòng 5848-5854 đã làm cho rotate).
- Phần (b) behavior: nhánh `dội >N batch → KHÔNG 429` ĐẢO thành `dội >AC_LABEL_BATCH_RATE_LIMIT → call thứ +1 raise RateLimitExceededError` (hoặc CHUYỂN behavior-branch sang class `TestLabelMarkBatchRateLimit` mới và để `test_write_endpoints_not_rate_limited` chỉ giữ static-guard cho `get_asset_label_data`).
- Đổi tên/docstring cho khớp (vd `test_only_single_label_endpoint_unthrottled`) để tránh hiểu nhầm về sau.

> **DoD Vòng 14:** `bench --site miyano run-tests test_imm00` GREEN (baseline label-pdf/coerce/mark/batch suite + class mới `TestLabelMarkBatchRateLimit`, RED-first chứng minh `>10 mark / >20 batch` KHÔNG raise TRƯỚC fix → raise SAU); `test_write_endpoints_not_rate_limited` ĐÃ ĐẢO GREEN; **fresh-import (guard Python thuần tier API) — KHÔNG cần reload gunicorn / KHÔNG `bench migrate`** (decorator + hằng trong suốt khi không có HTTP request); `CAP_SET_VERSION` GIỮ `v97.c30c69b8974d`; resolve/scan/rotate/pdf rate-limit cũ KHÔNG đổi hành vi; FE KHÔNG đổi (vue-tsc/vitest baseline GIỮ — 429→RATE_LIMITED+VI ĐÃ CÓ). Grep-gate: `AC_LABEL_MARK_RATE_LIMIT` + `AC_LABEL_BATCH_RATE_LIMIT` mỗi hằng đúng 1 định nghĩa (khối hằng đầu `api/imm00.py`, cạnh `AC_LABEL_PDF_RATE_LIMIT`); KHÔNG literal `10`/`20` rải rác ở handler; `@rate_limit` áp đúng **6 endpoint** (2 resolve `resolve_qr_token`+`get_asset_scan_info` + 1 rotate + 1 pdf + 1 mark + 1 batch); `get_asset_label_data` (single) là endpoint nhãn DUY NHẤT KHÔNG có decorator. Teardown xoá `rl:*`. KHÔNG commit (working tree để user review).

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

#### III.6.h-SEARCHESCAPE — Vòng 13: Escape LIKE-metachar trong `search` của `list_assets` (ADR-IMM00-SEARCH-ESCAPE / BR-00-44) — **NEW**

File BE: thêm class `TestListAssetsSearchEscape` vào `assetcore/tests/test_imm00_list_assets.py` (cạnh `TestListAssetsGmdnFilter`) HOẶC `tests/test_imm00_reserved_prefix.py` (tái dùng `_SeedMixin`). **RED-first BẮT BUỘC:** trên code hiện tại (`like = f"%{search}%"` trần) — `test_search_underscore_is_literal_not_wildcard` PHẢI ĐỎ (search='_' trả gần-như-mọi-row) TRƯỚC khi thêm `escape_like_term` → GREEN. **Guard Python thuần tier API/service** → fresh-import qua `run-tests`, KHÔNG cần reload gunicorn/migrate. Spec contract: [`ADR-IMM00-SEARCH-ESCAPE.md`](./ADR-IMM00-SEARCH-ESCAPE.md) §6 + [`04 §II.1.13-SEARCHESCAPE`](./04_Backend_Design.md) + [`05 §list_assets search`](./05_API_Specification.md).

> **Seed bắt buộc (để test có ý nghĩa, KHÔNG phụ thuộc data prod):** seed ≥3 asset có metachar LITERAL trong cột searchable + ≥1 không-metachar:
> - `_SE_underscore_a` (asset_name chứa `_` literal) · `_SE_percent_%a` (chứa `%`) · `_SE_back\slash` (chứa `\`) · `_SE_ventil` (không metachar, control).
> - Dùng prefix `_` để KHÔNG rò vào list prod (reserved-exclusion §III.6.h ẩn chúng khỏi list user thật) — NHƯNG test escape phải đo qua chính `list_assets` thấy được. Lưu ý: reserved-exclusion ẩn asset_name prefix `_` → seed control hợp lệ KHÔNG prefix `_` (vd `SETEST_ventil` với asset_name không bắt đầu `_`), HOẶC đo escape ở tầng helper `escape_like_term` (unit) + đo INVARIANT count==rows qua `list_assets` trên data sạch. **BE tự chốt:** kết hợp (a) unit-test `escape_like_term` thuần (no DB) cho ngữ nghĩa escape + (b) integration `list_assets` cho INVARIANT/no-throw/no-regress.
> - Teardown: xoá scratch qua direct DB delete (asset có lifecycle/audit → `delete_doc` bị WR-03 chặn; xoá `AC Lifecycle Event`/`AC Audit Trail Entry` con TRƯỚC, rồi `frappe.db.delete` asset — KHÔNG để leak).

| TC | Đo gì | Kỳ vọng |
|---|---|---|
| `test_escape_like_term_unit` | `escape_like_term('_')`=='\\_' · `('%')`=='\\%' · `('\\')`=='\\' (KHÔNG đổi) · `('vent')`=='vent' · `('a_b%c')`=='a\\_b\\%c' | escape ĐÚNG `%`/`_`, KHÔNG đụng `\`, no-op text |
| `test_search_underscore_is_literal_not_wildcard` (SE-1) | `list_assets(search='_')` | KHÔNG trả toàn bộ; chỉ row có `_` literal trong 4 cột; `total < tổng-tập` |
| `test_search_percent_is_literal_not_matchall` (SE-2) | `list_assets(search='%')` | KHÔNG match-all; chỉ row có `%` literal |
| `test_search_backslash_no_error_literal` (SE-3) | `list_assets(search='\\')` | KHÔNG throw/500/SQL-error; khớp row có `\` literal |
| `test_search_escaped_count_equals_rows` (SE-4) | `list_assets(search='_', page_size=2000)` + non-search | `pagination.total == len(items)` cả 2 path |
| `test_search_by_gmdn_code_substring` (SE-5) | giữ test cũ + smoke `vent`/`AC-ASSET`/`35304` | match như trước (no-regress) |
| `test_search_param_is_sqli_safe` (SE-6) | giữ test cũ `x' OR '1'='1` | 0-row + `total==len(items)`, no-throw |
| `test_escape_like_single_source` (SE-7) | grep `api/imm00.py` | KHÔNG có `.replace("%"`/`.replace("_"` LIKE-escape thủ công NGOÀI helper SSoT |
| `test_search_many_percent_no_dos_matchall` (SE-8) | `list_assets(search='%%%%%%%%%%')` | `total==len(items)` hữu hạn + KHÔNG match-all |

> **DoD Vòng 13 (SEARCH-ESCAPE):** `bench --site miyano run-tests test_imm00_list_assets` (+ `test_imm00_reserved_prefix` nếu đặt class ở đó) GREEN (baseline + class `TestListAssetsSearchEscape`); RED đã prove (search='_'/'%' match-all ĐỎ trước fix); SE-1..SE-8 pass; INVARIANT `total==len(items)` cho CẢ search & non-search, MỌI persona; `test_search_param_is_sqli_safe` + `test_search_by_gmdn_code_substring` GIỮ XANH; grep-guard 1-SSoT pass; `bench migrate` exit 0 (KHÔNG schema/cap/field/DocType/enum/patch delta — thuần 1 helper + 2-dòng wiring + test); `CAP_SET_VERSION` GIỮ NGUYÊN; FE KHÔNG đổi (BE-only — list/search tự hưởng lợi). Teardown sạch (0 scratch leak). KHÔNG commit (working tree để user review).

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
- **User Permission**: row-scope qua `permissions.py::ac_asset_query` (+ `ac_asset_has_permission` IDOR gate) — **ADR-IMM00-LIST-SCOPE (2026-06-08):** CHỈ Vendor Engineer scope `responsible_technician`; KTV nội bộ (Role Profile "Kỹ thuật viên") **read-all**. Count permission-aware → INVARIANT `count==rows` (RISK-00-04, NFR-00-07). Test: INV-1..INV-7 trong ADR (INV-3 chứng minh vendor vẫn isolated sau khi mở KTV read-all).

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

---

## XII. INVARIANT — Reconcile lifecycle map ⇄ workflow (CR-WF-00-LIFECYCLE, Vòng 32)

> **File:** `assetcore/tests/test_imm00.py`. Spec đầy đủ: [`04_Backend_Design.md §II.1.7-RECON`](./04_Backend_Design.md) + **ADR-IMM00-LIFECYCLE-SM**. Chạy: `bench --site miyano run-tests --module assetcore.tests.test_imm00`. Guard bất-biến chống drift SSoT `_VALID_ASSET_TRANSITIONS` ⇄ `ac_asset_lifecycle_workflow.json` ⇄ `fixtures/workflow.json`.

**SSoT khai trong test (đối xứng precedent `test_imm06.py::_SESSION_EXCEPTION_EDGES`):**
```python
EXCEPTION_EDGES = frozenset({
    ("Draft", "Decommissioned"), ("Commissioned", "Decommissioned"),
    ("Under Maintenance", "Decommissioned"), ("Under Repair", "Decommissioned"),
    ("Calibrating", "Decommissioned"),
})  # 5 cạnh — TẤT CẢ →Decommissioned
```

### TC-00-WF-RECON-01 — `test_asset_lifecycle_map_matches_workflow` (INVARIANT chính)
Đọc TRỰC TIẾP `ac_asset_lifecycle_workflow.json` (KHÔNG hardcode danh sách cạnh). Build `wf_pairs = {(t["state"], t["next_state"])}`, `map_pairs = {(s, nxt) for s, nexts in _VALID_ASSET_TRANSITIONS.items() for nxt in nexts}`. Assert **edge-by-edge**:
- `map_pairs − wf_pairs == EXCEPTION_EDGES` — mọi cạnh map-không-surface PHẢI được giải trình (0 cạnh drift không giải trình). Tương đương công thức acceptance: `∀ state s: set(_VALID_ASSET_TRANSITIONS[s]) − {e[1] for e in EXCEPTION_EDGES if e[0]==s} == wf_codomain[s]`.
- `wf_pairs − map_pairs == set()` — 0 cạnh workflow mồ côi (mọi CTA Desk ⊆ map; không có nút Desk dẫn tới transition state-machine cấm).
- `len(wf["states"]) == 8` và `{s["state"] for s in wf["states"]} == {AssetStatus.<8 giá trị>}` — grounding count (8 state workflow == 8 member `AssetStatus` enum, constants.py:88-95).
- 2 cạnh SURFACE (`Commissioned→Out of Service`, `Under Maintenance→Out of Service`) mỗi cạnh PHẢI có transition với `allowed ∈ {AssetCore Super Admin, System Manager}` (đủ cả 2 role).
- (anti-drift nhãn) mọi `t["action"]` ∈ tập action-label đã khai.

**RED-before (BẮT BUỘC demo THẬT):** gỡ 4 transition object mới khỏi `ac_asset_lifecycle_workflow.json` → `map_pairs − wf_pairs` = **7 cạnh** ≠ `EXCEPTION_EDGES` (5) → assert đầu FAIL, in đúng 2 cạnh thiếu surface `{(Commissioned, Out of Service), (Under Maintenance, Out of Service)}`. Restore → GREEN.

### TC-00-WF-RECON-02 — `test_lifecycle_workflow_source_matches_fixture` (lockstep parity)
Source JSON (`assetcore/assetcore/workflow/ac_asset_lifecycle_workflow.json`) ⇄ block `AC Asset Lifecycle` trong `assetcore/fixtures/workflow.json`. Assert:
- edge-set distinct BẰNG NHAU 2 file (`{(state,next_state)}` source == fixtures) — fresh-install `_sync_workflows` parity.
- Với mỗi cạnh SURFACE + mọi cạnh cũ: coverage role `AssetCore Super Admin` của source == fixtures (không lệch role admin-override — nếu workflow gains edges thì fixtures cũng phải có, kèm Super Admin).

**RED-before:** thêm cạnh vào source mà KHÔNG thêm vào fixtures → edge-set lệch → FAIL.

### TC-00-WF-RECON-03 — `test_is_valid_asset_transition_reflects_neg09` (helper ⇄ guard)
- Assert `is_valid_asset_transition(s, "Decommissioned") == False` với `s ∈ {Under Maintenance, Under Repair, Calibrating}` (helper phản ánh NEG-09).
- Assert `is_valid_asset_transition("Draft","Decommissioned") == True` và `("Commissioned","Decommissioned") == True` (KHÔNG NEG-09; chặn ở IMM-14 gate lớp DB, ngoài phạm vi helper thuần).
- Assert cạnh →Under Repair KHÔNG đổi (regression guard cho `test_imm09.py:431` + `imm09.py:1309`): `("Active","Under Repair")`, `("Under Maintenance","Under Repair")`, `("Out of Service","Under Repair")` vẫn `True`; `("Draft","Under Repair")` vẫn `False`.

**RED-before:** trên code hiện tại (helper CHƯA vá) `is_valid_asset_transition("Under Maintenance","Decommissioned")` trả `True` → assert đầu FAIL → GREEN sau khi thêm nhánh NEG-09 vào helper.

### TC-00-WF-SURFACE — `allowed_transitions` server-driven get_asset + FE render (CR-WF-00-LIFECYCLE-SURFACE, Vòng 41 / FR-00-109 / BR-00-58) — **NEW**

> Spec: [`04_Backend_Design.md §II.1.7-SURFACE + ADR-IMM00-LIFECYCLE-SURFACE`](./04_Backend_Design.md) + [`05_API_Specification.md §get_asset`](./05_API_Specification.md). File BE `test_imm00.py`, FE `assetDetailTransitionAuthz.test.ts` + `AssetDetailView.test.ts`.

**TC-00-WF-SURFACE-01 — `_surfaceable_asset_transitions` DRIVER cho reconcile-test (single-SSoT, no 2nd copy):** Trong `TC-00-WF-RECON-01` (`test_asset_lifecycle_map_matches_workflow`) THAY biểu thức inline `set(nexts) − exc_codom` bằng gọi `_surfaceable_asset_transitions(s)` → assert `_surfaceable_asset_transitions(s) == sorted(wf_codomain[s])` cho mọi state `s`. Chứng minh helper PURE = Desk workflow codomain (GỒM 2 cạnh Thanh lý `Active/Out of Service → Decommissioned`). *(Không tạo bản-sao-thứ-2 bảng transition — dẫn xuất từ `_VALID_ASSET_TRANSITIONS` + `_LIFECYCLE_EXCEPTION_EDGES`.)*

**TC-00-WF-SURFACE-02 — `asset_allowed_transitions` khớp SSoT + BẤT-VARIANT no-Decommissioned (pure, cap=True):** với caller CÓ `asset.write` (test-user Administrator/Super Admin, `frappe.set_user`), assert `asset_allowed_transitions(s)` **BẰNG NHAU** với `sorted(_VALID_ASSET_TRANSITIONS[s] − {tất cả cạnh →Decommissioned})` cho cả 8 status (đối chiếu bảng 8-status 04 §II.1.7-SURFACE — KHÔNG hardcode expected list, tính từ SSoT). Assert **`'Decommissioned' not in asset_allowed_transitions(s)` cho MỌI `s`** (BẤT-VARIANT). Assert `asset_allowed_transitions("Decommissioned") == []` (terminal). **RED-before:** nếu helper chỉ `− _LIFECYCLE_EXCEPTION_EDGES` (không loại-hẳn-Decommissioned) → `asset_allowed_transitions("Active")` CHỨA `Decommissioned` → assert BẤT-VARIANT FAIL.

**TC-00-WF-SURFACE-03 — capability filter (read-only → []):** user THẬT có DocPerm `read` NHƯNG KHÔNG `write` trên AC Asset (`frappe.set_user` + Role/Custom DocPerm — KHÔNG monkeypatch `rbac.can`) → `asset_allowed_transitions(s) == []` cho MỌI status. User có `asset.write` → subset đúng (TC-02). Mirror precedent test `firmware_allowed_transitions`.

**TC-00-WF-SURFACE-04 — `get_asset` emit field:** GET `get_asset(name)` với asset ở status non-terminal + caller có `asset.write` → response chứa key `allowed_transitions` = list đúng theo status (subset, sorted, no Decommissioned). Caller read-only → `allowed_transitions == []`. (Parity 2 cờ overdue: field dẫn-xuất, KHÔNG lưu DB.)

**TC-00-WF-SURFACE-05 — FE vitest (server-driven, no hardcode):**
- `AssetDetailView.test.ts` / `assetDetailTransitionAuthz.test.ts`: mock `store.currentAsset.allowed_transitions` → nút "→ <state>" render **đúng bằng** list mock (KHÔNG phụ thuộc `lifecycle_status` thô, KHÔNG phụ thuộc bảng hardcode đã xóa). Cập nhật mock `currentAsset` (`lifecycle_status: 'Active'`) THÊM `allowed_transitions: ['Under Maintenance','Under Repair','Calibrating','Out of Service']`.
- T6 (affordance-leak guard, thay đổi contract): server `[]` (read-only) → `currentAsset.allowed_transitions = []` → **KHÔNG render** nút →state nào (block ẩn theo `allowed_transitions?.length`). *(Chứng minh gate chuyển từ client-cap sang server-field; capability filter chứng minh ở BE TC-03.)*
- Happy-path + FE-2 (403 → `notify.fromError`) của CR-WF-00-TRANSITION-AUTHZ (Vòng 39) GIỮ NGUYÊN (endpoint `transition_status` vẫn gate server).
- Guard chống tái phạm: `grep`/AST khẳng định `AssetDetailView.vue` KHÔNG còn `const TRANSITIONS` (0 bảng transition hardcode FE).
- `vue-tsc --noEmit` sạch (type `AcAsset.allowed_transitions?` mới).

### DoD (không regression 8 file tham chiếu map)
`bench --site miyano run-tests` cho `imm00 / imm08 / imm09 / imm11 / imm14 / test_depreciation_oos` → `Ran N OK` THẬT (đọc dòng cuối). Chuỗi phải còn hợp lệ: CM `Cannot Repair`→`Out of Service`→`Decommission` (qua IMM-14) · PM `Under Maintenance`→`Active` · Cal→`Active`. 8 file tham chiếu map: `test_imm00, test_imm00_smoke, test_imm08, test_imm09, test_imm11, test_imm14, test_depreciation_oos, _asset_cleanup`. **KHÔNG** `git commit/push`; **KHÔNG** `bench migrate` (đổi workflow chỉ cần `reload_workflow`/backfill live — HARD-STOP user duyệt working tree).

> **DoD bổ sung Vòng 41 (CR-WF-00-LIFECYCLE-SURFACE):** BE `bench --site miyano run-tests test_imm00` (`Ran N OK` — gồm reconcile TC-00-WF-RECON-01 nay driven bởi `_surfaceable_asset_transitions` + TC-00-WF-SURFACE-01..04 + guards R32/R39 cũ). FE `npm test` (vitest) `AssetDetailView` + `assetDetailTransitionAuthz.test.ts` XANH + `vue-tsc --noEmit` sạch. `⚠️ api/imm00.py + services/imm00.py` edit ⇒ gunicorn reload để LIVE (HARD-STOP user); `bench run-tests` fresh-import KHÔNG cần reload. Guard: `AssetDetailView.vue` KHÔNG còn `const TRANSITIONS` (0 bảng transition hardcode FE).

## XIII. TRANSFER-AUTHZ — gate `confirm_receipt` + server-driven CTA flags (CR-WF-00-TRANSFER-AUTHZ, Vòng 48 / FR-00-TRF-02 / BR-00-TRF-02)

> Spec: 04 §II.1.13-TRANSFERAUTHZ / ADR-IMM00-TRANSFER-AUTHZ · 05 §III.12-AUTHZ · 06 §II.3a-TRANSFERAUTHZ. Test file: `assetcore/tests/test_imm00.py` (BE) + `AssetTransferDetailView` vitest (FE).

### TC-00-TRF-AUTHZ-01 — RED-first: base user KHÔNG có cap receive → `confirm_receipt` raise PermissionError (đóng lỗ P1)
- **Setup**: phiếu `Asset Transfer` status `Approved`; `frappe.set_user(<base AssetCore System User, KHÔNG Commissioning role>)`.
- **Assert**: `receive_transfer(name)` / `confirm_receipt(name)` → `self.assertRaises(frappe.PermissionError)`. **Trước fix** = xác nhận THÀNH CÔNG (status→Received) = **false-pass** ⇒ test RED trước, GREEN sau khi thêm `rbac.require(_TRANSFER_RECEIVE_CAP)`.
- **Đối chiếu**: status VẪN `Approved` (KHÔNG bị đổi), 0 audit `Transfer`, 0 lifecycle `transferred` sinh ra khi bị chặn.

### TC-00-TRF-AUTHZ-02 — happy-path: user CÓ cap receive → confirm_receipt thành công (giữ hành vi)
- **Setup**: phiếu `Approved`; user role có DocPerm write Asset Commissioning (vd Commissioning User — `write=1`).
- **Assert**: `confirm_receipt(name, handover_notes="ok")` → `status=='Received'` ∧ `received_by==session.user` ∧ 1 audit `event_type=='Transfer'` ∧ 1 lifecycle `event_type=='transferred'` ∧ `handover_notes` lưu. (Regression happy-path — KHÔNG đổi.)

### TC-00-TRF-AUTHZ-03 — server-driven flags `get_transfer_full` fail-closed cho base user
- **Setup**: base user (không cap). Phiếu-P `Pending Approval`, phiếu-A `Approved`.
- **Assert**: `get_transfer_full(P)["data"]` → `can_approve==0 ∧ can_receive==0`; `get_transfer_full(A)["data"]` → `can_approve==0 ∧ can_receive==0` (fail-closed cả 2 dù state khớp). Khóa `can_approve`/`can_receive` PRESENT (int, KHÔNG thiếu key).

### TC-00-TRF-AUTHZ-04 — flags cấp đúng khi CÓ cap + state khớp
- **Setup**: user Commissioning Manager (write=1, submit=1).
- **Assert**: `get_transfer_full(P)["data"]["can_approve"]==1` (Pending + submit); `get_transfer_full(A)["data"]["can_receive"]==1` (Approved + write). Cross-check state-gate: phiếu `Received`/`Rejected` → cả 2 flag `0` (sai state dù có cap). Commissioning User (write=1/submit=0) trên phiếu-A → `can_receive==1 ∧ can_approve==0` (least-privilege).

### TC-00-TRF-AUTHZ-05 — regression: enrich/pagination 5 TC (test_imm00 ~585-672) VẪN xanh
- TC-1..TC-5 (`test_list_transfers_enriches_*` / `test_get_transfer_detail_enriches_names` / N+1 guard / pagination total) KHÔNG đỏ: `get_transfer_full` thêm 2 int-key `can_approve`/`can_receive` là **additive** (TC-3 assert 6 `*_name` + success, KHÔNG assert absence). `get_transfer` KHÔNG đổi (byte-identical). approve/reject VẪN `rbac.require(_TRANSFER_APPROVE_CAP)`.

### TC-00-TRF-AUTHZ-06 (FE vitest) — gate 3 nút CTA + fail-closed
- Xem 06 §II.3a-TRANSFERAUTHZ test-block: `can_receive:1`→nút "Xác nhận tiếp nhận" hiện, `:0`→ẩn; `can_approve:1`→Phê duyệt/Từ chối hiện, `:0`→ẩn nhưng "Hủy phiếu" GIỮ; flag vắng→0 nút CTA. `vue-tsc --noEmit` sạch.

### DoD (TRANSFER-AUTHZ)
`bench --site miyano run-tests test_imm00` → `Ran N OK` THẬT (TC-00-TRF-AUTHZ-01..05 + 5 enrich/pagination cũ + suite hiện có). FE `npm test` (vitest `AssetTransferDetailView`) XANH + `vue-tsc --noEmit` sạch. **⚠️ NEW `rbac.require` trong `services/imm00.py`** ⇒ gunicorn reload để LIVE (HARD-STOP user); `bench run-tests` fresh-import KHÔNG cần reload. **0 migrate** (`commissioning.write` đã có → 0 CAP_SET_VERSION bump). **KHÔNG** `git commit/push`. Mobile OAS `test_mobile_oas.py` GIỮ XANH (403 shape KHÔNG đổi — xem 05 §III.12-AUTHZ ⚠️ Mobile drift; cập nhật description = backlog mobile-BE, không blocking).

## XIV. TRANSFER-CANCEL-AUTHZ — gate `cancel_transfer_request` + audit-on-cancel + flag `can_cancel` (CR-WF-00-CANCEL-AUTHZ, Vòng 41 / FR-00-TRF-03 / BR-00-TRF-03)

> Spec: 04 §II.1.13-CANCELAUTHZ / ADR-IMM00-CANCEL-AUTHZ · 05 §III.12-CANCELAUTHZ · 06 §II.3a-CANCELAUTHZ. Test file: `assetcore/tests/test_imm00.py` (BE — class MỚI `TestTransferCancelAuthz`, mirror `TestTransferReceiveAuthzAndFlags` `:690`) + `assetTransferDetailCtaGate.test.ts` (FE). Helper tái dùng `_mk_transfer(status)` / `_mk_user(email, roles)` từ class receive.

### TC-00-TRF-CANCEL-01 — RED-first: base user KHÔNG có cap → `cancel_transfer_request` raise PermissionError (đóng lỗ P1 missing-authz)
- **Setup**: phiếu `Asset Transfer` status `Pending Approval`; `frappe.set_user(<base AssetCore System User, KHÔNG Commissioning role>)`.
- **Assert**: `cancel_transfer_request(name)` → `self.assertRaises(frappe.PermissionError)`. **Trước fix** = hủy THÀNH CÔNG (status→Cancelled) = **lỗ hổng thật / false-pass** ⇒ test RED trước, GREEN sau khi thêm `rbac.require(_TRANSFER_CANCEL_CAP)`.
- **Đối chiếu**: status VẪN `Pending Approval` (KHÔNG bị đổi khi bị chặn).

### TC-00-TRF-CANCEL-02 — happy-path: user CÓ cap hủy phiếu Pending & Rejected → Cancelled + ĐÚNG 1 audit chứa 'Hủy' (đóng lỗ P1 silent-audit-loss)
- **Setup**: 2 phiếu — P1 `Pending Approval`, P2 `Rejected`; user Commissioning User (`write=1`, `submit=0`).
- **Assert**: `cancel_transfer_request(P1)` → `{name, status=='Cancelled'}` ∧ `db status=='Cancelled'`; tương tự `P2` (Rejected → Cancelled). **Audit**: mỗi lần hủy sinh **ĐÚNG 1** `IMM Audit Trail` với `{ref_doctype:'Asset Transfer', ref_name:P1, event_type:'Transfer'}` ∧ `change_summary` chứa `'Hủy'` (`frappe.db.count` == 1, KHÔNG 0/2). **Trước fix** = 0 dòng audit ⇒ assert RED trước, GREEN sau khi thêm `log_audit_event`.

### TC-00-TRF-CANCEL-03 — ordering exists→require→status: NOT-FOUND vs 403 KHÔNG rò trạng thái
- **Setup**: base user (không cap). (a) tên phiếu KHÔNG tồn tại; (b) phiếu CÓ tồn tại status `Approved` (sai-status-để-hủy).
- **Assert**: (a) `cancel_transfer_request('AT-KHONG-TON-TAI')` → `self.assertRaises(frappe.exceptions.ValidationError)` (NOT-FOUND, existence-check TRƯỚC rbac — KHÔNG phải PermissionError). (b) `cancel_transfer_request(<Approved>)` → `self.assertRaises(frappe.PermissionError)` (rbac TRƯỚC status-check ⇒ base user KHÔNG chạm thông báo "Chỉ có thể hủy phiếu Pending/Rejected" ⇒ KHÔNG rò trạng thái); status VẪN `Approved`.

### TC-00-TRF-CANCEL-04 — server-driven `can_cancel` fail-closed cho base user + state-gate cho user có cap
- **Setup**: base user + Commissioning User. Phiếu ở 5 status: Pending Approval / Rejected / Approved / Received / Cancelled.
- **Assert**: base user → `get_transfer_full(t)["data"]["can_cancel"]==0` ở **MỌI** status (fail-closed; key PRESENT int). Commissioning User → `can_cancel==1` CHỈ khi status∈{Pending Approval, Rejected}; `==0` ở Approved/Received/Cancelled (state-gate dù có cap).

### TC-00-TRF-CANCEL-05 — regression: flags receive/approve + suite Vòng 48 VẪN xanh
- `get_transfer_full` thêm khóa `can_cancel` là **additive** → TC-00-TRF-AUTHZ-01..05 (receive/approve flags) KHÔNG đỏ (assert theo key cụ thể, KHÔNG assert absence). `approve/reject/confirm_receipt` gate GIỮ NGUYÊN. `get_transfer`/`list_transfers` byte-identical (KHÔNG có `can_cancel`).

### TC-00-TRF-CANCEL-06 (FE vitest) — gate nút "Hủy phiếu" theo can_cancel + fail-closed
- Xem 06 §II.3a-CANCELAUTHZ test-block: `{status:'Pending Approval', can_cancel:1}`→nút `cta-cancel` hiện; `{...can_cancel:0}`→ẩn + hint; `{status:'Rejected', can_cancel:1}`→hiện; flag vắng→fail-closed ẩn. **Cập nhật 2 assert cũ** (`cta-cancel` true khi `can_approve:0`) → phụ thuộc `can_cancel`. `vue-tsc --noEmit` sạch.

### DoD (TRANSFER-CANCEL-AUTHZ)
`bench --site miyano run-tests test_imm00` → `Ran N OK` THẬT (TC-00-TRF-CANCEL-01..05 + TC-00-TRF-AUTHZ-01..05 Vòng 48 + suite hiện có). FE `npm test` (vitest `assetTransferDetailCtaGate`) XANH + `vue-tsc --noEmit` sạch. **⚠️ NEW `rbac.require` + `log_audit_event` trong `cancel_transfer_request` (`services/imm00.py`)** ⇒ gunicorn reload để LIVE (HARD-STOP user); `bench run-tests` fresh-import KHÔNG cần reload. **0 migrate** (`commissioning.write` đã có → 0 CAP_SET_VERSION bump). **KHÔNG** `git commit/push`. `delete_transfer` + `get_transfer_full` KHÔNG có trong mobile OAS ⇒ `test_mobile_oas.py` KHÔNG bị chạm (0 mobile drift).

## XIV-EDIT. TRANSFER-EDIT-AUTHZ — gate `update_transfer` (endpoint-level) + flag `can_edit` (CR-WF-00-EDIT-AUTHZ, Vòng 46 / FR-00-TRF-04 / BR-00-TRF-04)

> Spec: 04 §II.1.13-EDITAUTHZ / ADR-IMM00-EDIT-AUTHZ · 05 §III.12-EDITAUTHZ · 06 §II.3a-EDITAUTHZ. Test file: `assetcore/tests/test_imm00.py` (BE — class MỚI `TestTransferEditAuthz`, mirror `TestTransferReceiveAuthzAndFlags` / `TestTransferCancelAuthz`) + vitest `AssetTransferDetailView`. Helper tái dùng `_mk_transfer(status)` / `_mk_user(email, roles)`.
>
> **⚠️ Testing detail:** `update_transfer` là ENDPOINT đọc payload sửa từ `frappe.local.form_dict` (qua `_generic_update`). Test set `frappe.local.form_dict = frappe._dict({"reason": "...", "to_department": "...", ...})` TRƯỚC khi gọi `update_transfer(name)`. Cap-fail → `rbac.require` **raise** `frappe.PermissionError` (propagate, KHÔNG try/except) ⇒ `assertRaises`. Status-fail/not-found → **return dict envelope** `{success:False, http_status:422|404}` (HTTP-200 wire) ⇒ assert `resp["http_status"]`.

### TC-00-TRF-EDIT-01 — RED-first: user chỉ `inventory.read` (KHÔNG `commissioning.write`) → `update_transfer` phiếu Pending raise PermissionError (đóng lỗ P1 custody-hole)
- **Setup**: phiếu `Asset Transfer` status `Pending Approval`; `frappe.set_user(<user role có inventory.read, KHÔNG DocPerm write Asset Commissioning>)`; `frappe.local.form_dict = frappe._dict({"reason": "sửa lý do", "to_department": "<khoa khác>"})`.
- **Assert**: `update_transfer(name)` → `self.assertRaises(frappe.PermissionError)`. **Trước fix** = trả `{success:True}` + field `reason`/`to_department` đổi THẬT (re-fetch xác nhận) = **custody-hole / false-pass** ⇒ test RED trước, GREEN sau khi thêm `rbac.require(_TRANSFER_EDIT_CAP)`.
- **Đối chiếu**: field phiếu (`reason`/`to_department`) VẪN GIÁ TRỊ CŨ (KHÔNG bị đổi khi bị chặn) — re-fetch `frappe.db.get_value`.

### TC-00-TRF-EDIT-02 — happy-path: user CÓ `commissioning.write` + phiếu Pending → 200 + field THẬT cập nhật (re-fetch xác nhận)
- **Setup**: phiếu `Pending Approval`; user Commissioning User (`write=1`, `submit=0`); `frappe.local.form_dict = frappe._dict({"reason": "lý do mới", "to_department": "<khoa mới>", "notes": "ghi chú"})`.
- **Assert**: `update_transfer(name)` → `resp["success"] is True`; **re-fetch** `frappe.db.get_value("Asset Transfer", name, ["reason","to_department","notes"])` == giá trị MỚI (field đích/khoa/người-nhận/ngày/lý do/ghi-chú THẬT cập nhật). (Regression happy-path — giữ hành vi `_generic_update`.)

### TC-00-TRF-EDIT-03 — status-gate 422 GIỮ NGUYÊN cho user CÓ cap (KHÔNG bị rbac che thành 403)
- **Setup**: user Commissioning User (`write=1`). 3 phiếu: `Approved`, `Received`, `Cancelled`; `frappe.local.form_dict = frappe._dict({"reason": "thử sửa"})`.
- **Assert**: mỗi phiếu → `update_transfer(name)` return dict `resp["success"] is False` ∧ `resp["http_status"] == 422` ∧ message chứa `"Chỉ có thể chỉnh sửa phiếu đang Pending Approval"`. **KHÔNG** raise PermissionError (user CÓ cap → `rbac.require` không fire → chạm status-check → 422). field phiếu KHÔNG đổi.

### TC-00-TRF-EDIT-04 — server-driven `can_edit` fail-closed + state-gate + parity invariant
- **Setup**: base user (inventory.read) + Commissioning User (write=1). Phiếu ở 5 status: Pending Approval / Approved / Received / Rejected / Cancelled.
- **Assert**: base user → `get_transfer_full(t)["data"]["can_edit"]==0` ở **MỌI** status (fail-closed; key PRESENT int). Commissioning User → `can_edit==1` CHỈ khi status=='Pending Approval'; `==0` ở Approved/Received/Rejected/Cancelled (state-gate dù có cap). **Parity invariant**: với session Commissioning User + phiếu Pending, `get_transfer_full["data"]["can_edit"]==1` ⇒ `update_transfer(name)` (cùng session, `form_dict` hợp lệ) → `success is True` KHÔNG raise PermissionError (button-affordance ⇔ action).

### TC-00-TRF-EDIT-05 — ordering rbac-first (no existence-oracle) + regression additive
- **Ordering**: base user (không cap) gọi `update_transfer('AT-KHONG-TON-TAI')` → `self.assertRaises(frappe.PermissionError)` (rbac-first: cap-403 TRƯỚC exists — no existence-oracle, mirror `transition_status`). user CÓ cap gọi `update_transfer('AT-KHONG-TON-TAI')` → return `{http_status:404}` (existence-check sau rbac).
- **Regression**: `get_transfer_full` thêm khóa `can_edit` là **additive** → TC-00-TRF-AUTHZ-01..05 (receive/approve) + TC-00-TRF-CANCEL-01..05 (cancel) KHÔNG đỏ (assert theo key cụ thể, KHÔNG assert absence). `approve/reject/confirm_receipt/cancel` gate GIỮ NGUYÊN. `get_transfer`/`list_transfers` byte-identical (KHÔNG có `can_edit`).

### TC-00-TRF-EDIT-06 (FE vitest) — `isEditable` ← `can_edit` + fail-closed
- Xem 06 §II.3a-EDITAUTHZ test-block: `{status:'Pending Approval', can_edit:1}`→form editable + nút "Lưu thay đổi" hiện; `{...can_edit:0}`→form disabled + nút Lưu ẩn; `{status:'Pending Approval'}` (không key)→fail-closed read-only; `{status:'Approved', can_edit:0}`→read-only. `vue-tsc --noEmit` sạch.

### DoD (TRANSFER-EDIT-AUTHZ)
`bench --site miyano run-tests test_imm00` → `Ran N OK` THẬT (TC-00-TRF-EDIT-01..05 + TC-00-TRF-AUTHZ-01..05 Vòng 48 + TC-00-TRF-CANCEL-01..05 Vòng 41 + suite hiện có). FE `npm test` (vitest `AssetTransferDetailView`) XANH + `vue-tsc --noEmit` sạch. **⚠️ NEW `rbac.require` trong `api/imm00.py::update_transfer`** ⇒ gunicorn reload để LIVE (HARD-STOP user); `bench run-tests` fresh-import KHÔNG cần reload. **0 migrate** (`commissioning.write` đã có → 0 CAP_SET_VERSION bump). **KHÔNG** `git commit/push`. `update_transfer` + `get_transfer_full` KHÔNG có trong mobile OAS ⇒ `test_mobile_oas.py` KHÔNG bị chạm (0 mobile drift).

## XV. FIXTURE-SRC-RECONCILE — bất-biến 2-chiều `fixtures/workflow.json` ⇄ 22 source `workflow/*.json` cho MỌI workflow (CR-WF-00-FXSRC-RECONCILE, Vòng 43 / FR-00-FXSRC / BR-00-FXSRC)

> Spec thiết kế: [`04_Backend_Design.md §II.1.8-FXSRC + ADR-IMM00-WF-FXSRC-RECONCILE`](./04_Backend_Design.md). File test MỚI: `assetcore/tests/test_workflow_fixture_source_reconcile.py`. **0 file runtime `.py` đổi** (test-only) → 0 gunicorn reload, 0 `bench migrate`, KHÔNG commit.

### Bối cảnh (đóng lỗ seed-drift 2-đường-cài-đặt)
AssetCore có **2 đường seed workflow lệch nguồn** — drift 1-phía tái sinh **CÂM** bug "QTV không duyệt được" ở site cài mới:
- **Fresh-install** `_sync_workflows()` (`setup/install.py:507-527`) `import_doc` từ thư mục **SOURCE** `assetcore/assetcore/workflow/*.json` (22 file).
- **`bench migrate` / Frappe fixture-import** + `setup/backfill_workflow_admin.run` + MỌI invariant hiện có (`test_workflows.py` INV-A/B/C, `test_workflow_admin_override.py`, `test_workflow_admin_override_livedb.py`) đọc **FIXTURE** `assetcore/fixtures/workflow.json`.

Guard hiện có `TC-00-WF-RECON-02` (§XII) chỉ reconcile **1 workflow** (AC Asset Lifecycle, edge-set `{(state,next_state)}`). `INV-C` (`test_workflows`) reconcile **transitions** cho 22 workflow (`{(state,action,next_state)→set(roles)}`) NHƯNG **KHÔNG so states** (`doc_status`/`allow_edit` có thể drift câm → đổi docstatus-envelope hoặc role-được-sửa-trong-state = họ hàng bug QTV) và **KHÔNG có meta-test RED-first** (guard no-op qua câm = false-green, META rule). Section này bổ sung 1 module hợp nhất, self-contained, KHÓA cả **states + edges (kèm `allowed`) + admin-override 2-phía**, và **tự chứng minh có răng**.

### Đơn vị so sánh — projection tránh false-RED do export-artifact
Source JSON **viết tay tối giản**; fixture là bản Frappe **export** (thêm field default + plumbing). So full-dict ⇒ false-RED hàng loạt. Chỉ so **projection load-bearing** (grounding: đối chiếu key-diff thực tế 22 file):
- **STATE** (STRICT set-equal) = `(state, str(doc_status), allow_edit or "")`. LOẠI `type` (source-only — metadata Workflow-State master, KHÔNG phải field child Frappe enforce; fixture drop) + mọi plumbing fixture-only (`parent/parentfield/parenttype/workflow_builder_id/message/next_action_email_template/update_field/update_value/avoid_status_override/is_optional_state/send_email`).
- **EDGE** (STRICT set-equal) = `(state, action, next_state, allowed or "")` — **INCLUDING `allowed`** ⇒ drift admin-override 1-phía = RED. LOẠI plumbing fixture-only (`parent*/workflow_builder_id/send_email_to_creator`). *(`condition`/`allow_self_approval` KHÔNG trong edge-identity Vòng 43 — parity INV-C; hardening riêng `[ROADMAP]`.)*
- **HEADER check-field** = `{is_active, send_email_alert, override_status}` **normalize None↔0** trước so (source thiếu `override_status`→None; fixture=0 → benign, ĐÃ verify src=None vs fx=0). `norm0(v) = 0 if v in (None,'',0,'0',False) else 1`.
- **Scope-filter fixture** về đúng 22 tên source TRƯỚC khi so (mirror `test_workflows._fixture_assetcore_workflows` — loại foreign multi-app mvl/antmed/workflowcore nếu tương lai lọt vào shared fixture). Hiện `fixtures/workflow.json` chứa ĐÚNG 22 Workflow AssetCore (đã verify) — filter là defensive.
- **Admin role-set** = `import backfill_workflow_admin.ADMIN_ROLES` (SoT, KHÔNG hardcode — mirror `test_workflow_admin_override_livedb.ADMIN_SET`) ⇒ SoT đổi role-set thì guard tự bám.

### Kiến trúc reconcile — RAISE-based để meta-test cắn được (chống no-op)
Module có helper thuần trả `list[str]` drift cho từng lát + 1 hàm top-level `reconcile(source_map, fixture_map) -> None` gom drift 5 lát rồi `assert not drift, msg` ⇒ **RAISE `AssertionError`** khi có bất kỳ drift. 5 test-positive gọi helper-lát (`assertEqual(drift, [])` — thông điệp fail granular); 2 meta-test gọi `reconcile()` trên bản **deepcopy in-memory đã mutate** (KHÔNG persist ra file).

| TC | Test method (INV) | Setup / Assert | Kỹ thuật |
|---|---|---|---|
| TC-00-FXSRC-01 | `test_name_set_parity` (INV-FXSRC-1) | `{workflow_name của 22 source}` == `{name của entry fixture scope}`; `len==22` cả 2. **0 workflow lệch 1-phía** (thêm/xoá 1 bên → RED, in `only_source`/`only_fixture`). | EP (set-equal) |
| TC-00-FXSRC-02 | `test_states_parity_strict` (INV-FXSRC-2) | ∀ workflow: `state_set(source) == state_set(fixture)` với projection `(state, str(doc_status), allow_edit or "")`. STRICT. Drift → in `only_src`/`only_fix` state-tuple. **Đây là guard MỚI vs INV-C** (bắt `allow_edit`/`doc_status` drift). | EP (set-equal, STRICT) |
| TC-00-FXSRC-03 | `test_edges_parity_including_allowed` (INV-FXSRC-3) | ∀ workflow: `edge_set(source) == edge_set(fixture)`, `edge = (state, action, next_state, allowed or "")`. STRICT, kèm `allowed`. | EP (set-equal, STRICT) |
| TC-00-FXSRC-04 | `test_admin_override_both_sides` (INV-FXSRC-4) | ∀ transition-group `(state,action,next_state)` ở **CẢ** source **VÀ** fixture: `roles ⊇ {AssetCore Super Admin, System Manager}` (import `ADMIN_ROLES`). Chứng minh SOURCE (nguồn `_sync_workflows` dùng) KHÔNG thiếu quyền — không chỉ fixture. | EP (superset, 2-phía) |
| TC-00-FXSRC-05 | `test_toplevel_checkfields_parity_normalized` | ∀ workflow: `{is_active, send_email_alert, override_status}` normalize None↔0 → source == fixture. **0 false-RED** do export-artifact (`override_status` src=None vs fx=0 → cả 2 =0). | EP (normalize + equal) |
| TC-00-FXSRC-06 | `test_reconcile_raises_on_source_admin_strip` (INV-FXSRC-5a) | `deepcopy(source_map)`; gỡ `'System Manager'` khỏi `allowed` của 1 transition (hoặc drop row admin đó) → `with self.assertRaises(AssertionError): reconcile(mutated_source, fixture_map)`. Chứng minh admin-override + edge guard **cắn**. KHÔNG persist. | Mutation / RED-proof |
| TC-00-FXSRC-07 | `test_reconcile_raises_on_fixture_phantom_edge` (INV-FXSRC-5b) | `deepcopy(fixture_map)`; append 1 phantom transition `(state,action,next_state,allowed)` mới vào 1 workflow → `with self.assertRaises(AssertionError): reconcile(source_map, mutated_fixture)`. Chứng minh edge-parity guard **cắn** 1-phía. KHÔNG persist. | Mutation / RED-proof |

### DoD (FIXTURE-SRC-RECONCILE)
- `bench --site miyano run-tests --app assetcore --module assetcore.tests.test_workflow_fixture_source_reconcile` → **`Ran N OK` THẬT** (đọc dòng cuối), **N ≥ 5** (spec 7 method). GREEN trên trạng thái hiện tại (đã verify BA: name-set 22=22, states 0 drift, edges 0 drift, header check-field 0 drift sau normalize).
- **RED-before (BẮT BUỘC demo THẬT)**: chạy TC-00-FXSRC-06/07 trên `reconcile()` CHƯA gom đủ lát (vd bỏ helper admin-override) → `assertRaises` FAIL (guard no-op) → thêm lát → GREEN. Chứng minh guard có răng, không nhận suông.
- **Regression GREEN (không đỏ)**: `test_workflows` (INV-A/B/C), `test_workflow_admin_override`, `test_workflow_admin_override_livedb` — module MỚI là **ADDITIVE**, TUYỆT ĐỐI KHÔNG xoá/làm yếu guard cũ.
- **0 file runtime `.py` đổi** → 0 gunicorn reload, 0 `bench migrate`, 0 CAP_SET_VERSION. **KHÔNG** `git commit/push`. Working tree để user review.
