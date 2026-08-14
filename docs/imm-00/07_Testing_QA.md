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
| `AssetDetailView.qrPrint.test.ts` (D6) | mock caps `{asset.read:true}` (KHÔNG print) | nút "In nhãn QR" KHÔNG render |
| `AssetDetailView.qrPrint.test.ts` (D6) | mock caps `{asset.print:true}` | nút "In nhãn QR" render |
| `AssetDetailView.qrRegenerate.test.ts` (D6) | mock caps `{asset.print:true}` (KHÔNG rotate) | nút "Sinh lại mã QR" KHÔNG render (tách quyền) |
| `AssetDetailView.qrRegenerate.test.ts` (D6) | mock caps `{asset.qr.rotate:true}` | nút "Sinh lại mã QR" render |
| `AssetListView.batchSelect.test.ts` (D6) | mock caps `{asset.read:true}` (KHÔNG print) | nút "In nhãn hàng loạt" KHÔNG render |
| `routeAccess.test.ts` (D6) | guard `AssetLabelPrint` với caps `{asset.read:true}` | unauthorized; `{asset.print:true}` → allow |
| `AssetDetailView.rbacAffordance.test.ts` (D6) | caps `{asset.print:true}` only | "In nhãn QR" hiện, "Sinh lại mã QR"/"Chỉnh sửa" ẩn (least-privilege) |

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

File BE: thêm class `TestGetAssetScanInfo` vào `assetcore/tests/test_imm00.py` (cạnh `TestResolveQrToken` A2 — line ~2045). FE: `frontend/src/views/asset/tests/AssetScanInfoView.test.ts` (NEW) + cập nhật `QrResolveView.test.ts` (regression).

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

File BE: thêm class `TestAssetScanInfoPmOverdue` vào `assetcore/tests/test_imm00.py` (cạnh `TestGetAssetScanInfo`). FE: cập nhật `frontend/src/views/asset/tests/AssetScanInfoView.test.ts` (thêm TC badge). **RED-first:** class/TC chưa tồn tại → fail → impl `_is_pm_overdue` + thêm field payload → GREEN. Đo QUA `build_asset_scan_info` (KHÔNG mock `getdate`/`nowdate` — set `next_pm_date` thật quanh `nowdate()` để check ranh giới strict `<`).

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

File BE: thêm class `TestAssetScanInfoCalibrationOverdue` vào `assetcore/tests/test_imm00.py` (cạnh `TestAssetScanInfoPmOverdue`). FE: cập nhật `frontend/src/views/asset/tests/AssetScanInfoView.test.ts` (thêm TC badge hiệu chuẩn). **RED-first BẮT BUỘC:** class/TC chưa tồn tại → fail → impl `_is_calibration_overdue` + thêm `next_calibration_date` vào fields-list + 2 field payload → GREEN. Đo QUA `build_asset_scan_info` (KHÔNG mock `getdate`/`nowdate` — set `next_calibration_date` thật quanh `nowdate()` để check ranh giới strict `<`). **DISTINCT với III.6.a-PMOVERDUE** (chiều hiệu chuẩn, field+signal khác).

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

File BE: **bổ sung** class `TestScanInfoManufacturerSn` (`assetcore/tests/test_imm00.py` — cạnh `TestAssetScanInfo`). File FE: cập nhật `frontend/src/views/asset/tests/AssetScanInfoView.test.ts` (thêm TC dòng "Số serial NSX" + empty-fallback). **RED-first BẮT BUỘC:** TC `assert 'manufacturer_sn' in payload` + `== <giá-trị-thật>` ĐỎ trước fix (key absent → KeyError/None) → thêm `"manufacturer_sn"` vào fields-list `db.get_value` + key payload `row.get("manufacturer_sn") or ""` → GREEN; TC FE `serialText==='Chưa rõ'` khi rỗng ĐỎ trước thêm computed → GREEN. Đo QUA `build_asset_scan_info` THẬT (Administrator có mọi DocPerm — KHÔNG mock; tạo AC Asset thật, set `manufacturer_sn` thật + biến thể rỗng). Spec: [`04 §II.1.8d-SCANSN`](./04_Backend_Design.md) + [`05 §get_asset_scan_info payload 12-field`](./05_API_Specification.md) + [`02 §IV.28 / BR-00-52`](./02_Analysis_Design.md) + [`06 §II.3d-SERIALSN`](./06_Frontend_Design.md) + [ADR §D13](./ADR-IMM00-QR-SCAN-ACTION.md).

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

File FE: cập nhật `frontend/src/views/asset/tests/AssetScanInfoView.test.ts` (thêm TC pill a11y + anchor + exactly-one). **KHÔNG file BE** (FE-only, KHÔNG đụng `build_asset_scan_info`/payload). **RED-first BẮT BUỘC:** TC assert `wrapper.get('[data-test="scan-status"]')` + `role==='status'` + `aria-label` khớp `'Trạng thái thiết bị: ' + statusLabel` ĐỎ trước khi thêm 3 attr (pill cũ chỉ có `class`/`:class` → `[data-test="scan-status"]` không tồn tại / `role` undefined) → thêm `data-test="scan-status"` + `role="status"` + `:aria-label` lên `<span>` pill (`AssetScanInfoView.vue:445-450`) → GREEN. Đo QUA mount THẬT `AssetScanInfoView` (mock `getAssetScanInfo` trả payload với `lifecycle_status` biến thể — KHÔNG mock `lifecycleStatusLabel`; aria-label phải bằng giá-trị `statusLabel` THẬT để chứng minh SSoT-shared). Spec: [`02 §IV.29 / FR-00-104 / BR-00-53`](./02_Analysis_Design.md) + [`06 §II.3e-PILLA11Y`](./06_Frontend_Design.md) + [ADR §D14](./ADR-IMM00-QR-SCAN-ACTION.md). Parity §II.3e-PILLNOLEAK (no-EN/raw-code/empty leak — Vòng 8) cho nhánh aria-label.

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

File FE: cập nhật `frontend/src/views/asset/tests/AssetScanInfoView.risk.test.ts` (thêm TC cờ urgency — file vòng 38 đã có TC nhãn `riskText`) + `AssetScanInfoView.test.ts` (TC integration). **KHÔNG file BE** (FE-only, KHÔNG đụng `build_asset_scan_info`/payload — BE đã emit `risk_classification` coalesce `''`). **RED-first BẮT BUỘC:** TC assert `wrapper.find('[data-test="scan-risk-urgent"]')` tồn tại + `role==='status'` + `aria-label` khớp `'Cảnh báo rủi ro cao: ' + riskText` ĐỎ trước khi thêm (dòng risk cũ chỉ có `riskText`, KHÔNG cờ) → thêm computed `riskUrgent` + 3 hằng VI + phần tử `data-test="scan-risk-urgent"` vào `AssetScanInfoView.vue` (dòng `:466-473`) → GREEN. Đo QUA mount THẬT `AssetScanInfoView` (mock `getAssetScanInfo` trả payload với `risk_classification` biến thể — KHÔNG mock `riskClassificationLabel`; aria-label phải bằng giá-trị `riskText` THẬT để chứng minh SSoT-shared). Spec: [`02 §IV.30 / FR-00-105 / BR-00-54`](./02_Analysis_Design.md) + [`06 §II.3f-SCANRISKURGENT`](./06_Frontend_Design.md) + [ADR §D15](./ADR-IMM00-QR-SCAN-ACTION.md). Parity nguyên-tắc overdue-SSoT vòng 21 (derive cờ server, no client-clock) + status-pill a11y vòng 39 (role=status + aria-label SSoT-shared).

**Acceptance — chạy XANH:** `vitest` (`AssetScanInfoView.risk.test.ts` TC urgency mới + `AssetScanInfoView.test.ts` + baseline riskText nhãn vòng 38/40 + pill-a11y/serial/overdue) GREEN + `vue-tsc` 0 + full asset-domain vitest no-regression. **KHÔNG BE test / KHÔNG `bench migrate` / KHÔNG reload** (FE-only template + computed — `riskText`/`RISK_CLASSIFICATION_LABEL`/`constants/labels.ts`/payload KHÔNG đổi). `CAP_SET_VERSION` GIỮ `v97.c30c69b8974d`. **Verify Playwright/quét-QR-thật BLOCKED reload gunicorn --preload (HARD-STOP USER) → vitest + code-audit là gate hợp lệ; KHÔNG tuyên bố DONE live.**

| TC (FE — `AssetScanInfoView.risk.test.ts` / `AssetScanInfoView.test.ts`) | Kịch bản | Verify |
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

**REG (acceptance đề mục):** §II.3f-SCANRISKURGENT mới + nhãn `riskText` (vòng 38, `AssetScanInfoView.risk.test.ts` TC1-TC7) — GIỮ GREEN 0 regression; §II.3e-PILLA11Y (status-pill), §II.3c-PMOVERDUE/§II.3d-CALOVERDUE (overdue badge), §III.6.m-SCANSN (serial) — GIỮ XANH. FE-only: KHÔNG đổi `riskText`/`RISK_CLASSIFICATION_LABEL` logic / BE payload / RBAC / `available_actions` shape.

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

File BE: **bổ sung** class `TestScanInfoAvailableActions` (`assetcore/tests/test_imm00.py:3463` — ĐÃ tồn tại từ vòng QR-SCAN-ACTION) + **SIẾT** `test_unknown_status_safe_default` (`:3719`). File FE: cập nhật `frontend/src/views/asset/tests/AssetScanInfoView.test.ts` (thêm TC reason non-rỗng + non-dangling aria-describedby). **RED-first BẮT BUỘC:** TC unknown/empty-status assert `reason == _LIFECYCLE_REASON_UNKNOWN` + bất biến `enabled=False ⟹ reason!=""` ĐỎ trước fix (hiện `reason==""` cho status rỗng/lạ + Admin) → thêm hằng `_LIFECYCLE_REASON_UNKNOWN` + bậc-3 `or` ở `_build_available_actions` → GREEN. Đo QUA `build_asset_scan_info` THẬT (Administrator có mọi DocPerm = nhánh lifecycle thuần; monkeypatch `svc.rbac.can` ép thiếu cap — KHÔNG mock `getdate`/`nowdate`). Spec: [`04 §II.1.8f`](./04_Backend_Design.md) + [`05 §III.1 available_actions`](./05_API_Specification.md) + [`02 §IV.18 / BR-00-41`](./02_Analysis_Design.md) + [`06 §reason-render`](./06_Frontend_Design.md) + [ADR §D9](./ADR-IMM00-QR-SCAN-ACTION.md).

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

> **Đề mục factory vòng 8 (2026-06-11 — scan-action / status-pill no-EN-leak — Self-Correction lỗi thiết kế gốc FE-formatter).** **FE-only** — BE KHÔNG đổi (`build_asset_scan_info`/`resolve_qr_token` GIỮ `or ""`). File FE: `frontend/src/constants/tests/labels.test.ts` (mở rộng block `lifecycleStatusLabel`/`lifecycleStatusClass` — ĐÃ có) + `frontend/src/views/asset/tests/AssetScanInfoView.test.ts` (thêm TC pill rỗng/lạ). **RED-first BẮT BUỘC:** TC mã-lạ (`'In Use'`/`'Retired'`/`'active'`) + rỗng (`''`/null/undefined) assert `=== 'Không xác định'` ĐỎ trước fix (hiện `?? v` trả raw/empty) → thêm hằng `LIFECYCLE_STATUS_UNKNOWN_LABEL` + đổi fallback formatter → GREEN. Spec: [`06 §status-pill-safe`](./06_Frontend_Design.md) + [`02 §IV.19 / BR-00-42`](./02_Analysis_Design.md) + [ADR §D10](./ADR-IMM00-QR-SCAN-ACTION.md).

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

File BE: thêm class `TestRegenerateAssetQrToken` vào `assetcore/tests/test_imm00.py` (cạnh `TestAssetLabelData` / `TestGetAssetScanInfo`). FE: `frontend/src/views/asset/tests/AssetDetailView.qrRegenerate.test.ts` (NEW) + cập nhật `routeAccess.test.ts` (không route mới — gate ở nút). **RED-first BẮT BUỘC** (class chưa tồn tại → ImportError/AttributeError → impl → GREEN). Đo QUA layer `require` với **user THẬT** có/không `asset.write` (KHÔNG mock `require`/`has_permission` — chống false-green; baseline 116 test giữ xanh).

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
| `AssetDetailView.qrRegenerate.test.ts` (D6) | mock caps `{asset.read:true}` (KHÔNG rotate) | nút "Sinh lại mã QR" KHÔNG render |
| `AssetDetailView.qrRegenerate.test.ts` (D6) | mock caps `{asset.print:true}` (in được, KHÔNG rotate) | nút "Sinh lại mã QR" KHÔNG render (tách quyền) |
| `AssetDetailView.qrRegenerate.test.ts` (D6) | mock caps `{asset.qr.rotate:true}` | nút "Sinh lại mã QR" render |
| `AssetDetailView.qrRegenerate.test.ts::click_opens_modal_no_confirm_no_api` | click nút | **KHÔNG** gọi `window.confirm`; mở `BaseModal` cảnh báo "vô hiệu hoá mọi nhãn QR đã in"; API **chưa** gọi |
| `AssetDetailView.qrRegenerate.test.ts::confirm_calls_api_refetch_toast` | bấm "Xác nhận" | `regenerateAssetQrToken(id)` gọi **1 lần** đúng id; refetch asset; toast VI thành công |
| `AssetDetailView.qrRegenerate.test.ts::cancel_noop` | bấm "Huỷ" | đóng modal; **0** API call; KHÔNG đổi gì |
| `AssetDetailView.qrRegenerate.test.ts::error_403_no_leak` | mock API 403 | toast/alert lỗi VI; KHÔNG leak token/mã EN/raw method |

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

File FE: `frontend/src/api/tests/errors.test.ts` (httpStatusToCode) + `frontend/src/views/asset/tests/AssetDetailView.qrRegenerate.test.ts` (mở rộng — cạnh TC B-2 hiện có). Spec: [`06 §II.3e-RATELIMIT`](./06_Frontend_Design.md) + [`02 FR-00-87/88`](./02_Analysis_Design.md).

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

File FE: helper `frontend/src/utils/navigation.ts::isSafeInternalRedirect` (NEW export, thuần) + block redirect-safety trong `frontend/src/views/auth/tests/LoginView.test.ts`. **FE-only** — KHÔNG đổi BE/DocType/route/schema/patch; `bench`/`test_imm00` baseline KHÔNG đụng. Spec contract: [`06 §II.4c`](./06_Frontend_Design.md) + [`02 BR-00-32`](./02_Analysis_Design.md). **RED-first** (helper chưa tồn tại → import fail / assert đỏ → impl → GREEN).

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

> Spec: [`04_Backend_Design.md §II.1.7-SURFACE + ADR-IMM00-LIFECYCLE-SURFACE`](./04_Backend_Design.md) + [`05_API_Specification.md §get_asset`](./05_API_Specification.md). File BE `test_imm00.py`, FE `AssetDetailView.transitionAuthz.test.ts` + `AssetDetailView.test.ts`.

**TC-00-WF-SURFACE-01 — `_surfaceable_asset_transitions` DRIVER cho reconcile-test (single-SSoT, no 2nd copy):** Trong `TC-00-WF-RECON-01` (`test_asset_lifecycle_map_matches_workflow`) THAY biểu thức inline `set(nexts) − exc_codom` bằng gọi `_surfaceable_asset_transitions(s)` → assert `_surfaceable_asset_transitions(s) == sorted(wf_codomain[s])` cho mọi state `s`. Chứng minh helper PURE = Desk workflow codomain (GỒM 2 cạnh Thanh lý `Active/Out of Service → Decommissioned`). *(Không tạo bản-sao-thứ-2 bảng transition — dẫn xuất từ `_VALID_ASSET_TRANSITIONS` + `_LIFECYCLE_EXCEPTION_EDGES`.)*

**TC-00-WF-SURFACE-02 — `asset_allowed_transitions` khớp SSoT + BẤT-VARIANT no-Decommissioned (pure, cap=True):** với caller CÓ `asset.write` (test-user Administrator/Super Admin, `frappe.set_user`), assert `asset_allowed_transitions(s)` **BẰNG NHAU** với `sorted(_VALID_ASSET_TRANSITIONS[s] − {tất cả cạnh →Decommissioned})` cho cả 8 status (đối chiếu bảng 8-status 04 §II.1.7-SURFACE — KHÔNG hardcode expected list, tính từ SSoT). Assert **`'Decommissioned' not in asset_allowed_transitions(s)` cho MỌI `s`** (BẤT-VARIANT). Assert `asset_allowed_transitions("Decommissioned") == []` (terminal). **RED-before:** nếu helper chỉ `− _LIFECYCLE_EXCEPTION_EDGES` (không loại-hẳn-Decommissioned) → `asset_allowed_transitions("Active")` CHỨA `Decommissioned` → assert BẤT-VARIANT FAIL.

**TC-00-WF-SURFACE-03 — capability filter (read-only → []):** user THẬT có DocPerm `read` NHƯNG KHÔNG `write` trên AC Asset (`frappe.set_user` + Role/Custom DocPerm — KHÔNG monkeypatch `rbac.can`) → `asset_allowed_transitions(s) == []` cho MỌI status. User có `asset.write` → subset đúng (TC-02). Mirror precedent test `firmware_allowed_transitions`.

**TC-00-WF-SURFACE-04 — `get_asset` emit field:** GET `get_asset(name)` với asset ở status non-terminal + caller có `asset.write` → response chứa key `allowed_transitions` = list đúng theo status (subset, sorted, no Decommissioned). Caller read-only → `allowed_transitions == []`. (Parity 2 cờ overdue: field dẫn-xuất, KHÔNG lưu DB.)

**TC-00-WF-SURFACE-05 — FE vitest (server-driven, no hardcode):**
- `AssetDetailView.test.ts` / `AssetDetailView.transitionAuthz.test.ts`: mock `store.currentAsset.allowed_transitions` → nút "→ <state>" render **đúng bằng** list mock (KHÔNG phụ thuộc `lifecycle_status` thô, KHÔNG phụ thuộc bảng hardcode đã xóa). Cập nhật mock `currentAsset` (`lifecycle_status: 'Active'`) THÊM `allowed_transitions: ['Under Maintenance','Under Repair','Calibrating','Out of Service']`.
- T6 (affordance-leak guard, thay đổi contract): server `[]` (read-only) → `currentAsset.allowed_transitions = []` → **KHÔNG render** nút →state nào (block ẩn theo `allowed_transitions?.length`). *(Chứng minh gate chuyển từ client-cap sang server-field; capability filter chứng minh ở BE TC-03.)*
- Happy-path + FE-2 (403 → `notify.fromError`) của CR-WF-00-TRANSITION-AUTHZ (Vòng 39) GIỮ NGUYÊN (endpoint `transition_status` vẫn gate server).
- Guard chống tái phạm: `grep`/AST khẳng định `AssetDetailView.vue` KHÔNG còn `const TRANSITIONS` (0 bảng transition hardcode FE).
- `vue-tsc --noEmit` sạch (type `AcAsset.allowed_transitions?` mới).

### DoD (không regression 8 file tham chiếu map)
`bench --site miyano run-tests` cho `imm00 / imm08 / imm09 / imm11 / imm14 / test_depreciation_oos` → `Ran N OK` THẬT (đọc dòng cuối). Chuỗi phải còn hợp lệ: CM `Cannot Repair`→`Out of Service`→`Decommission` (qua IMM-14) · PM `Under Maintenance`→`Active` · Cal→`Active`. 8 file tham chiếu map: `test_imm00, test_imm00_smoke, test_imm08, test_imm09, test_imm11, test_imm14, test_depreciation_oos, _asset_cleanup`. **KHÔNG** `git commit/push`; **KHÔNG** `bench migrate` (đổi workflow chỉ cần `reload_workflow`/backfill live — HARD-STOP user duyệt working tree).

> **DoD bổ sung Vòng 41 (CR-WF-00-LIFECYCLE-SURFACE):** BE `bench --site miyano run-tests test_imm00` (`Ran N OK` — gồm reconcile TC-00-WF-RECON-01 nay driven bởi `_surfaceable_asset_transitions` + TC-00-WF-SURFACE-01..04 + guards R32/R39 cũ). FE `npm test` (vitest) `AssetDetailView` + `AssetDetailView.transitionAuthz.test.ts` XANH + `vue-tsc --noEmit` sạch. `⚠️ api/imm00.py + services/imm00.py` edit ⇒ gunicorn reload để LIVE (HARD-STOP user); `bench run-tests` fresh-import KHÔNG cần reload. Guard: `AssetDetailView.vue` KHÔNG còn `const TRANSITIONS` (0 bảng transition hardcode FE).

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

> Spec: 04 §II.1.13-CANCELAUTHZ / ADR-IMM00-CANCEL-AUTHZ · 05 §III.12-CANCELAUTHZ · 06 §II.3a-CANCELAUTHZ. Test file: `assetcore/tests/test_imm00.py` (BE — class MỚI `TestTransferCancelAuthz`, mirror `TestTransferReceiveAuthzAndFlags` `:690`) + `AssetTransferDetailView.ctaGate.test.ts` (FE). Helper tái dùng `_mk_transfer(status)` / `_mk_user(email, roles)` từ class receive.

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

---

## XVI. ROWSCOPE-INVARIANT — `BaseRepository.list(scope=…)`: rows permission-aware KHỚP count (INV-ROWSCOPE, 2026-07-25)

> **SSoT quyết định:** [`ADR-IMM00-LIST-SCOPE.md` §8](./ADR-IMM00-LIST-SCOPE.md) (D4–D7 + §8.9 bảng bất biến). Module test MỚI: `assetcore/tests/test_rowscope_invariant.py`.

### Bối cảnh (finding CRITICAL vòng trước)

KTV_A (`Repair User`) **ĐỌC được** phiếu `Asset Repair` của KTV_B trên `/cm/work-orders`, nhưng bấm "Đính ảnh" → **403**; và "Tổng N" ≠ số dòng. Root cause: `BaseRepository.list` đếm bằng `frappe.get_list` (permission-aware) nhưng lấy rows bằng `frappe.get_all` (**KHÔNG** áp `permission_query_conditions`) — `repositories/base.py:64-75`.

### ⚠️ Bẫy XANH-GIẢ số 1 — chạy dưới Administrator

`Administrator` / `AssetCore Super Admin` **bypass** `permission_query_conditions` (`permissions.py:113-121` trả `""`) ⇒ mọi assert row-scope sẽ XANH dù bug còn nguyên. **BẮT BUỘC** `frappe.set_user(<ktv_a>)` trong test (fixture user THẬT có role `Repair User`/`PM User`), `addCleanup(frappe.set_user, "Administrator")` để không rò session sang test khác.

### ⚠️ Bẫy XANH-GIẢ số 2 — assert `total == len(rows)` khi cả 2 cùng = 0

Fixture rỗng ⇒ `0 == 0` XANH vacuous. Mỗi TC row-scope phải **seed ≥ 2 phiếu (1 của KTV_A, 1 của KTV_B)** và assert **cả 2 chiều**: (a) `total == len(rows)`, (b) `total >= 1` (non-vacuous) + (c) **0 phiếu của KTV_B** trong kết quả.

### Test matrix

| TC | Test method (INV) | Setup / Assert | Kỹ thuật |
|---|---|---|---|
| TC-00-RS-01 | `test_user_scope_total_equals_rows` (INV-ROWSCOPE-1) | Seed ≥2 phiếu; `scope="user"`, `page_size` ≥ total → `pg["total"] == len(rows)`, `total >= 1` | Invariant, non-vacuous |
| TC-00-RS-02 | `test_system_scope_total_equals_rows` (INV-ROWSCOPE-2) | Cùng dataset, `scope="system"` → `pg["total"] == len(rows)`, `total >= 2` (thấy cả 2 phiếu) | Invariant, non-vacuous |
| TC-00-RS-03 | `test_invalid_scope_raises` (INV-ROWSCOPE-3) | `scope="System"` / `""` / `None` → `assertRaises(ValueError)` | Fail-fast / RED-proof |
| TC-00-RS-04 | `test_imm09_list_excludes_other_technician` (INV-ROWSCOPE-4) | `frappe.set_user(KTV_A)`; `api.imm09.list_repair_work_orders()` **KHÔNG** truyền `mine` → `0` row có `assigned_to == KTV_B`; `pagination.total == len(data.data)` | Row-scope + invariant |
| TC-00-RS-05 | `test_read_implies_write_repair_photo` (INV-ROWSCOPE-5) | ∀ row trong list của KTV_A: `services.imm09._assert_can_attach_repair_photo(RepairRepo.get(name))` KHÔNG raise ⇒ **0 phiếu đọc-được-nhưng-cấm-đính-ảnh** | **Đóng finding CRITICAL** |
| TC-00-RS-06 | `test_imm08_list_excludes_other_technician` (INV-ROWSCOPE-6) | Đối xứng PM: `api.imm08.list_pm_work_orders()` với KTV_A → 2 assert như TC-00-RS-04 | Row-scope + invariant |
| TC-00-RS-07 | `test_senior_sees_all` (INV-ROWSCOPE-7) | `frappe.set_user(<Repair Manager>)` → thấy ĐỦ 2 phiếu, `total == 2` (**không over-block**) | Anti-over-block |
| TC-00-RS-08 | `test_vendor_not_widened` (INV-ROWSCOPE-8) | Vendor Engineer THUẦN → KHÔNG thấy phiếu ngoài scope (D2 bất biến, CLAUDE.md §5) | Isolation no-regress |
| TC-00-RS-09 | `test_missing_docperm_returns_error_envelope` (INV-ROWSCOPE-9) | Persona thiếu DocPerm `read` (vd `Calibration User` trên `Asset Repair`) gọi list → **HTTP-200 + envelope `success:false`** (KHÔNG 500, KHÔNG list rỗng giả) — BR-00-ROWSCOPE-403 | Error-contract |
| TC-00-RS-10 | `test_card_equals_drill_per_persona` (INV-ROWSCOPE-10, D7) | KTV_A: `cm_sla_breach_count()` == số row drill `?sla_breached_live=1`; `count_overdue_pm()` == số row drill `?overdue=1` | Card==drill parity |
| TC-00-RS-FE | vitest `CMWorkOrderListView` | `pagination.total = 2` + `workOrders.length = 40` ⇒ header chứa `Tổng 2`, KHÔNG chứa `Tổng 40`; `pagination` chưa nạp ⇒ `Tổng 0`; "Hiển thị" vẫn `.length` | Guard chống fallback client-count quay lại |

### Fixture contract

- User test: `_rowscope_ktv_a@assetcore.test` (role `Repair User` + `PM User`), `_rowscope_ktv_b@assetcore.test`, `_rowscope_mgr@assetcore.test` (`Repair Manager` + `PM Manager`). Prefix `_` ⇒ nằm trong reserved-prefix exclusion, KHÔNG lẫn data thật.
- Teardown BẮT BUỘC: xoá phiếu + asset + user seed (reuse `assetcore/tests/_asset_cleanup.py`), `addCleanup(frappe.set_user, "Administrator")`. Fixture-leak = nguồn "full BE suite đỏ" giả.

### DoD (ROWSCOPE-INVARIANT)

- `bench --site miyano run-tests --app assetcore --module assetcore.tests.test_rowscope_invariant` → **`Ran N OK` THẬT** (đọc dòng cuối), N ≥ 10.
- **RED-before (BẮT BUỘC demo THẬT)**: chạy TC-00-RS-04/05 trên `base.py` CHƯA có `scope` (rows = `frappe.get_all`) → **ĐỎ**; thêm `scope="user"` → XANH. Guard không có răng = không nhận.
- Regression XANH: `test_imm09`, `test_imm08`, `test_imm11`, `test_imm05`, `test_imm00`, `test_rbac`, `test_list_search_filter`. FE: `npm run test` + `vue-tsc` xanh.
- **Call site đỏ vì `get_list` strip field `permlevel > 0`** → chuyển ĐÚNG site đó sang `scope="system"` + comment `# [ROWSCOPE-FALLBACK]` + ghi backlog. **TUYỆT ĐỐI KHÔNG nới DocPerm** (ADR §8.7).
- **KHÔNG** `git commit/push/merge` · **KHÔNG** `reset DB`/`drop site`/`bench restart`/reload gunicorn (HARD-STOP — quyền USER). Working tree để user review.


---

## XVII. AC-CR-80 — Picker "người nhận việc": capability-SSoT + hết cắt IM LẶNG (INV-ASSIGN-1..8)

> Spec: [`05_API_Specification.md` §III.23](./05_API_Specification.md) · ADR: [`ADR-IMM00-TRUNCATION-SSOT.md` §7](./ADR-IMM00-TRUNCATION-SSOT.md) · code-shape: [`04_Backend_Design.md` §V.6](./04_Backend_Design.md).
> Module test: `assetcore/tests/test_imm00_base_role.py` (class `TestListAssignableUsers` — **đã tồn tại**, mở rộng) + guard contract `assetcore/tests/test_mobile_oas.py` (`TestMobileAssignableUsersContract`, **đã LANDED ở Bước-2**).

### XVII.1 TC backend (BE Bước-4)

| TC | Ý đồ | Chấm bằng |
|---|---|---|
| **TC-00-ASSIGN-01** | Shape mới: `data` là **dict** có ĐỦ 4 khoá `items/total/truncated/limit` | `set(res["data"]) == {"items","total","truncated","limit"}` |
| **TC-00-ASSIGN-02** | INV-ASSIGN-1: `len(items) <= limit` với `limit` nhỏ (vd 2) trên tập ≥3 người hợp lệ | seed ≥3 user `repair`-capable |
| **TC-00-ASSIGN-03** | INV-ASSIGN-3 (cắt): `limit=2` & tập ≥3 ⇒ `truncated == 1` ∧ `total > 2` ∧ `total == len(capable)` | |
| **TC-00-ASSIGN-04** | INV-ASSIGN-3 (không cắt): `limit=100` ⇒ `truncated == 0` ∧ `total == len(items)` | |
| **TC-00-ASSIGN-05** | INV-ASSIGN-4: `isinstance(res["data"]["truncated"], bool) is False` ∧ `truncated in (0,1)` ∧ `total`/`limit` là `int` ≥ 0 | **KHÔNG** dùng `assertEqual(truncated, 0)` một mình — `False == 0` là True ⇒ test mù |
| **TC-00-ASSIGN-06** | INV-ASSIGN-7: `limit=0` ⇒ `data["limit"] == 1`; `limit=500` ⇒ `data["limit"] == 100` ∧ `truncated` tính theo 100 | |
| **TC-00-ASSIGN-07** | INV-ASSIGN-2: `total` đếm **SAU** lọc năng lực — seed N người capable + M người base-role KHÔNG capable ⇒ `total == N` (KHÔNG N+M) | ca này bắt đúng lỗi `count_ac_users` |
| **TC-00-ASSIGN-08** | INV-ASSIGN-5 (parity xuôi): ∀ `u ∈ items` với `context='repair'` ⇒ `services.imm09._is_repair_capable(u["name"])` True — thử ở **nhiều** `limit` (2, 20, 100) | 0 dead-pick |
| **TC-00-ASSIGN-09** | INV-ASSIGN-6 (parity nghịch): user base-role chỉ có vai read-only (vd `Auditor`) KHÔNG bao giờ xuất hiện; gọi `_assert_valid_technician(u)` ⇒ raise, envelope `code='VALIDATION_ERROR'` ∧ `http_status == 422` ∧ `message_code == 'IMM09-INVALID-TECHNICIAN'` | chứng minh picker là **tấm gương** của validator |
| **TC-00-ASSIGN-10** | INV-ASSIGN-8: `context='bogus'` ⇒ `success is False` ∧ `code == 'VALIDATION_ERROR'` ∧ `http_status == 400`; **KHÔNG** raise (không HTTP-500) | |
| **TC-00-ASSIGN-11** | INV-ASSIGN-8 (0 leak): message KHÔNG chứa bất kỳ giá trị nào trong `_ASSIGNABLE_CONTEXTS` (tên DocType) và KHÔNG chứa `tab`/`SELECT` | duyệt cả 5 DocType |
| **TC-00-ASSIGN-12** | `context='user'`: KHÔNG lọc năng lực (user chỉ có `Document User` vẫn hiện) nhưng **vẫn** có đủ 4 khoá + truncation đúng | ghim ngữ nghĩa 2 chế độ |

**Fixture**: dùng khuôn `_insert(suffix, roles)` sẵn có (`test_imm00_base_role.py`), luôn kèm `search='_test_lau_<suffix>'` để **cách ly** khỏi dữ liệu thật; `tearDown` xoá user đã tạo (đang có).
⚠️ **Regression bắt buộc**: `_names()` (`:301`) hiện đọc `res["data"]` như mảng ⇒ đổi `res["data"]["items"]`, nếu không **7 TC cũ ĐỎ**.

### XVII.2 Guard contract (ĐÃ LANDED — Bước-2, `test_mobile_oas` 967→975)

| Guard | Ghim gì | Mutation đã verify |
|---|---|---|
| `cr80_a` | path GET-only + opId + tag + slot {200,401,403} + membership `_MVP_BUSINESS_PATHS`/401/403 | — |
| `cr80_b` | enum `context` == `{_ANY_USER_CONTEXT}` ∪ keys(`_ASSIGNABLE_CONTEXTS`) — **import THẬT** | ✅ bỏ 1 giá trị enum ⇒ ĐỎ |
| `cr80_c` | 3 param khớp `inspect.signature` LIVE + clamp `minimum:1`/`maximum:100` | — |
| `cr80_d` | `data` object closed 4 khoá đều required; `truncated` **integer enum[0,1]** | ✅ đổi sang `boolean` ⇒ ĐỎ |
| `cr80_e` | cite-parity AST **3 tầng** (`api/user.py`, `services/imm09.py`, `services/shared/truncation.py`) + bắt buộc nêu 6 symbol | ✅ rot cite `:1047`→`:2000` ⇒ ĐỎ |
| `cr80_f` | item closed 4 khoá, 3 nullable, **0 khoá nhạy cảm** (`roles`/`imm_roles`/`api_key`…) | — |
| `cr80_g` | mô tả nêu đủ token hành vi (`HTTP-200`, `KHÔNG LOGOUT`, `truncated`, `total`, `Đang hiển thị`, `VALIDATION_ERROR`, `422`) | — |
| `cr80_h` | 200 = oneOf ĐÚNG 2 nhánh + tổng `paths 108` / `schemas 283` / `parameters 38` + no-orphan | — |

### XVII.3 TC frontend (FE Bước-4)

| TC | Ý đồ |
|---|---|
| **TC-FE-ASSIGN-01** | `listAssignableUsers` trả object ⇒ trả nguyên; trả **mảng** (BE chưa reload) ⇒ chuẩn hoá `{items, total=len, truncated:0, limit}` |
| **TC-FE-ASSIGN-02** | **RENDER**: mock `{items: 20, total: 47, truncated: 1}` ⇒ DOM chứa `Đang hiển thị 20/47 người` |
| **TC-FE-ASSIGN-03** | **RENDER**: `truncated: 0` ⇒ DOM **KHÔNG** chứa `Đang hiển thị` |
| **TC-FE-ASSIGN-04** | `full_name: null` ⇒ chip + dòng gợi ý fallback `name`, **không** throw |
| **TC-FE-ASSIGN-05** | `props`/`emit` của `ApproverSelect` không đổi (mount với `modelValue` + `context`, emit `update:modelValue` như cũ) |

### XVII.4 DoD vòng

- BE: `test_imm00_base_role` · `test_ac_user_source` · `test_imm00_user_approval` · `test_imm09` · `test_imm08` — **OK**.
- Contract: `test_mobile_oas` **975 OK** · `test_mobile_docset` **9 OK** *(đã đạt ở Bước-2)*.
- FE: `npx vue-tsc --noEmit` 0 lỗi · `npx vitest run` xanh.
- ⏱ Mọi lệnh `bench run-tests` đặt timeout tool **≥ 600000ms** — kill giữa chừng = `tearDownClass` không chạy = **nhiễm DB**, KHÔNG phải bug sản phẩm.

---

## XVIII. AC-CR-87 — «Bản ghi liên quan» là CÂY DỮ LIỆU THẬT (INV-CONN-1..17 · §XVIII.4 FE vòng 2 · §XVIII.5 FE vòng 3 · §XVIII.6 BE+FE vòng 4 · **§XVIII.7 FE vòng 5 — deep-link «Xem tất cả» CÓ LỌC** · §XVIII.8 AC-CR-93 chỉ render ô CÓ dữ liệu · **§XVIII.9 AC-CR-94 — deep-link ĐẾN ĐÍCH 2 màn LỊCH + `count == drill` cross-endpoint** · **§XVIII.10 AC-CR-95 — thăng hạng 4 màn đích còn lại, `LIST_TARGET_NO_FILTER` 9→5** · **§XVIII.11 AC-CR-92 — ô 12→9 khoá, `capped: bool`→`total_capped: int`, RATIFY cổng I/O**)

> Spec: [`05 §III.24`](./05_API_Specification.md) · ADR: [`ADR-IMM00-CONNECTIONS-TREE.md`](./ADR-IMM00-CONNECTIONS-TREE.md) · code shape: [`04 §V.7`](./04_Backend_Design.md).
> **File test MỚI**: `assetcore/tests/test_connections_tree.py`. **`test_connections.py` (11 TC) và `test_doctype_connectivity.py` KHÔNG được sửa một dòng nào** — chúng chính là oracle "không phá FE hiện tại".

### XVIII.1 Fixture tối thiểu (dùng lại khuôn `test_connections.py`)

- 1 `AC Asset Category` + 1 `AC Asset` **A6** (seed **6** `PM Work Order` → chứng minh cắt) + 1 `AC Asset` **A3** (seed **3** PM WO → chứng minh không cắt) + 1 `AC Asset` **A0** (0 liên kết).
- Insert bỏ qua workflow bằng `frappe.flags.in_install` (khuôn có sẵn); dọn bằng `tests/_asset_cleanup.purge_asset` / `purge_category_by_name` trong `tearDownClass`.
- 1 user **hạn chế** (chỉ base role `AssetCore System User`) cho nhóm phân quyền.

### XVIII.2 Test case ↔ invariant ↔ acceptance

| TC | Nội dung | INV | Acceptance |
|---|---|---|---|
| **TC-CONN-T-01** | Mỗi ô của `get_connections("AC Asset", A6)` có **đủ 12 khoá**; `type(truncated) is int` ∧ `isinstance(truncated, bool) is False` ∧ `truncated ∈ {0,1}` | INV-CONN-1 | A1 |
| **TC-CONN-T-02** | A6: ô `PM Work Order` ⇒ `total == 6` ∧ `truncated == 1` ∧ `len(items) == 5` | INV-CONN-3/4 | A2 |
| **TC-CONN-T-03** | A3: ô `PM Work Order` ⇒ `total == 3` ∧ `truncated == 0` ∧ `len(items) == 3` | INV-CONN-3/4 | A2 |
| **TC-CONN-T-04** | **ZERO-COST**: patch `frappe.db.count` + `frappe.db.sql` bằng mock raise; gọi A3 ⇒ **không** raise. Đồng thời wrap `frappe.get_list` đếm lời gọi ⇒ **đúng 1 lần/ô** | INV-CONN-6 | A2/A3 |
| **TC-CONN-T-05** | **AST guard** trên `api/connections.py` **và** `services/connections.py`: 0 hit `frappe.db.count`, 0 hit `frappe.get_all`, 0 kwarg `ignore_permissions`; **có** `frappe.get_list` | INV-CONN-5 | A3 |
| **TC-CONN-T-06** | Bất biến toàn cục: duyệt **mọi ô của mọi hub** trong `_ALLOWED_SOURCE_DOCTYPES` (dùng bản ghi seed hoặc bản ghi thật đầu tiên) ⇒ `len(items) == min(total, preview_limit)` ∧ `count == total` | INV-CONN-2/3 | A3 |
| **TC-CONN-T-07** | Mỗi phần tử `items[]` có đúng 5 khoá, **không khoá nào `None`**, tất cả `str`; `title != ""`; `date` khớp `^\d{4}-\d{2}-\d{2}$` hoặc `""` | INV-CONN-14 | A4 |
| **TC-CONN-T-08** | `status_label` VI: PM WO `status='In Progress'` ⇒ `'Đang thực hiện'`; giá trị lạ ⇒ `'Chưa rõ'` (**không** rò chuỗi tiếng Anh) | INV-CONN-13 | A4 |
| **TC-CONN-T-09** | **Parity lifecycle**: ∀ 8 mã canonical `AC Asset.lifecycle_status` ⇒ `status_label("AC Asset", s) == services.imm00._lifecycle_vi(s)` | INV-CONN-11 | A4 |
| **TC-CONN-T-10** | **PARITY NHÃN (duyệt module dashboard THẬT)**: import động mọi `assetcore/assetcore/doctype/*/*_dashboard.py`, gom `transactions[].items[]` ⇒ mọi doctype có khoá trong `LABEL_VI` ∧ `LABEL_VI[dt] != dt`. **KHÔNG** hardcode danh sách thứ hai | INV-CONN-7 | A5 |
| **TC-CONN-T-11** | **PREVIEW_FIELDS hợp lệ**: ∀ field khai ⇒ tồn tại trên `frappe.get_meta(dt)` ∧ `permlevel == 0` ∧ fieldtype đúng vai (status = Select \| Link `Workflow State` \| Data; date = Date \| Datetime) ∧ **không** thuộc họ tài chính/định danh cá nhân | INV-CONN-12 | A4 |
| **TC-CONN-T-12** | **PHỦ NHÃN TRẠNG THÁI**: ∀ dt ∈ `PREVIEW_FIELDS` có trường status ⇒ mọi giá trị enum có nhãn VI. Nguồn enum: `options` (Select) **hoặc** `states[].state` trong `assetcore/assetcore/workflow/*.json` khớp `document_type` (vì `workflow_state` là **Link**, không phải Select) | INV-CONN-13 | A5 |
| **TC-CONN-T-13** | Allowlist: `doctype` **rác** ⇒ `NOT_FOUND`; **bản ghi rác** ⇒ `NOT_FOUND` **CÙNG message**; `AC Asset Category` (tồn tại, ∉ allowlist) ⇒ `success == True` ∧ `groups == []` *(đính chính A6 — xem ADR §D6)* | INV-CONN-* | A6 |
| **TC-CONN-T-14** | `preview_limit` = `0` / `99` / `'abc'` / `-3` ⇒ clamp `[1,10]` (hoặc về `5`), **không** raise; `truncated` tính theo trần **đã clamp** | INV-CONN-14 | A6 |
| **TC-CONN-T-15** | `deep_link_filters`: mọi khoá ∈ `_ALLOWED_DEEP_LINK_KEYS[dt]`; mọi value `isinstance(v, str)`; ca `internal_links` ⇒ khoá `name` = chuỗi mã nối bằng dấu phẩy; `count > 0 ⇒ deep_link_filters != {}` | INV-CONN-10 | A7 |
| **TC-CONN-T-16** | `can_create == False ⟺ create_route_hint == ""` (kiểm **hai chiều** trên mọi ô của mọi hub) | INV-CONN-8 | A8 |
| **TC-CONN-T-17** | Dưới user **hạn chế** (chỉ base role): mọi ô trả về ⇒ `can_create is False` ∧ `create_route_hint == ""` | INV-CONN-9 | A8 |
| **TC-CONN-T-18** | Nhóm `internal_links` (liên kết **xuôi**, vd `AC Asset` trong đồ thị của `Asset Repair`) ⇒ `can_create is False` dù có quyền tạo | INV-CONN-9 | A8 |
| **TC-CONN-T-19** | **Cổng vòng đời**: A6 đặt `lifecycle_status = 'Decommissioned'` ⇒ mọi ô `can_create is False`; đặt lại `'Active'` ⇒ ô `PM Work Order` `can_create is True` (dùng **cùng hằng** `AssetStatus.BLOCKED_FOR_WO` với `validate_asset_for_operations`) | INV-CONN-9 | A8 |
| **TC-CONN-T-20** | **No-regress hợp đồng cũ**: `data.total` vẫn là **tổng cộng dồn `count`**; `filters` giữ dạng cũ (kể cả `["in", [...]]`); `label` vẫn là `_(doctype)`; `capped` vẫn `bool` | INV-CONN-2 | A9/A1 |
| **TC-CONN-T-21** | **Nhánh CHẠM TRẦN của INV-CONN-2** (fixture ≤ 6 bản ghi không bao giờ chạm ⇒ trước TC này, gỡ hẳn `min(len(rows), CAP)` vẫn 21/21 XANH): tiêm `list_fn` giả (**0 seed, 0 truy vấn đọc dòng**) trả `150` / `CAP+1` / `CAP` dòng ⇒ `count == total == 100` ở cả ba; `capped is True` cho 2 ca đầu và **`False`** cho ca `CAP` chẵn (predicate là `len(rows) > CAP`, **không** `>=`) ⇒ D4: `capped=True` biến `total` thành **cận dưới**, FE render `"100+"` | INV-CONN-2 / D4 | A1 |
| **TC-CONN-T-22** | **Cổng `has_permission(linked_dt,'read')`**: patch `frappe.has_permission` từ chối đúng `PM Work Order` ⇒ ô **biến mất HẲN** (không phải ô `count: 0`), các ô khác còn nguyên, **0 nhóm rỗng**. Trước TC này mutation M5 (gỡ 2 dòng gate) chỉ bị `test_connections.py` bắt — mà file đó sẽ bị tỉa ở vòng 3 | ADR §D1 luật 1 | A1 |

### XVIII.3 DoD vòng (chấm ĐỎ nếu thiếu bất kỳ mục nào)

- `bench --site miyano run-tests --app assetcore --module assetcore.tests.test_connections` **XANH** (11 TC, **0 assert bị sửa**).
- `bench --site miyano run-tests --app assetcore --module assetcore.tests.test_connections_tree` **XANH**.
- `bench --site miyano run-tests --app assetcore --module assetcore.tests.test_doctype_connectivity` **XANH** (không sửa file).
- `npx vitest run src/components/common/tests/RelatedRecords.test.ts src/api` **XANH**; `npx vue-tsc --noEmit` 0 lỗi.
- `git diff --name-only` **chỉ** chứa: `assetcore/api/connections.py` · `assetcore/services/connections.py` · `assetcore/services/shared/connection_meta.py` · `assetcore/tests/test_connections_tree.py` · `frontend/src/api/connections.ts` · (nếu suite thật lệch) file guard count · docs vòng này.
- Guard count (`_EXPECTED_TEST_COUNT` @`tests/test_mobile_oas.py:212` · `_GUARD_SUITE_SUM` @`tests/test_mobile_docset.py:956`): cập theo **DELTA**, đọc số **trên đĩa** ngay trước khi sửa — số trong spec/STATE luôn có thể stale (đọc 2026-07-27: `1024` / `1167`). Endpoint này **không** có mirror OAS ⇒ nếu file test mới không thuộc guard-suite thì **KHÔNG** đụng 3 hằng.
- ⏱ Mọi lệnh `bench run-tests` đặt timeout tool **≥ 600000ms** — kill giữa chừng = `tearDownClass` không chạy = **nhiễm DB**, KHÔNG phải bug sản phẩm.
- ⚠️ `--preload`: sửa `api/*.py` **không** có hiệu lực qua HTTP tới khi USER reload ⇒ **chấm bằng `run-tests`, KHÔNG curl** (curl 417/traceback ≠ bug sản phẩm — LL-DEPLOY-07/08).

### XVIII.4 AC-CR-88 (vòng 2/5 — FE): test RENDER cho `RelatedRecords.vue` (INV-CONNFE-1..11)

> Spec thực thi: [`06 §VIII.4.2`](./06_Frontend_Design.md) · quyết định: [`ADR-IMM00-CONNECTIONS-TREE.md` §10](./ADR-IMM00-CONNECTIONS-TREE.md).
> **File**: `frontend/src/components/common/tests/RelatedRecords.test.ts` (**VIẾT LẠI** — test cũ khoá card chrome + dòng "Tổng 3" nay đã bị D-FE-1 gỡ) · `frontend/src/guards/connectionsApi.guard.test.ts` (**CHỈ APPEND** ca helper; 4 describe cũ về `DOCTYPE_ROUTE`/`DOCTYPE_DETAIL_ROUTE` **không được sửa một assert nào** — chúng là guard chống link chết).
> Lệnh chấm: `cd frontend && npx vitest run` (0 fail) + `npx vue-tsc --noEmit` (0 lỗi). **KHÔNG** `npm run build` (= deploy live).

**Fixture chuẩn (dựng trong file test, KHÔNG phải bản đồ sản phẩm):** `PAYLOAD_20` = 1 payload phủ **toàn bộ 20 khoá** của `DOCTYPE_ROUTE`, mỗi ô có `label_vi` tiếng Việt + `total>0` + ≥1 dòng `items[]`. Việc nhãn VI nằm trong fixture là hợp lệ (SSoT thật vẫn là `connection_meta.LABEL_VI` ở BE — INV-CONN-7 canh phía BE).

| TC | Nội dung | INV | Acceptance |
|---|---|---|---|
| **TC-CONNFE-01** | Mount với `PAYLOAD_20` ⇒ `∀ dt ∈ Object.keys(DOCTYPE_ROUTE): !wrapper.text().includes(dt)` (loop, **không** liệt kê tay) ∧ text chứa đủ 20 nhãn VI | INV-CONNFE-1 | A1 |
| **TC-CONNFE-02** | Ô thiếu `label_vi` ⇒ hiện `label`; thiếu **cả hai** ⇒ hiện `doctype`; không ô nào nhãn rỗng | INV-CONNFE-2 | A1 |
| **TC-CONNFE-03** | Ô `items` 5 dòng ⇒ DOM chứa **5** `title` + **5** `status_label`; **không** chứa `status` thô (fixture đặt `status:'In Progress'` ≠ `status_label:'Đang thực hiện'`); **không** chứa `'undefined'`/`'null'`; ngày khớp `formatDate(row.date)` (**không** hardcode chuỗi ngày — bẫy ICU) | INV-CONNFE-3 | A2 |
| **TC-CONNFE-04** | `date: ''` ⇒ dòng vẫn render, hiện `'—'`, DOM **không** có `'undefined'`; `status_label: ''` ⇒ **0** chip trạng thái trong dòng đó | INV-CONNFE-3 | A2 |
| **TC-CONNFE-05** | Click dòng của `Asset Repair`/`AR-2026-0001` ⇒ `push` gọi **đúng 1 lần** với **chuỗi** `/cm/work-orders/AR-2026-0001` | INV-CONNFE-5 | A3 |
| **TC-CONNFE-06** | Doctype **có** `DOCTYPE_ROUTE` nhưng **không** `DOCTYPE_DETAIL_ROUTE` (vd `Asset Document`) ⇒ dòng là `conn-row-static`, **không** phải `<button>`, click ⇒ `push` **không** được gọi (0 nút chết) | INV-CONNFE-4 | A3 |
| **TC-CONNFE-07** | Ô `{deep_link_filters:{asset:'AC-ASSET-2026-00001'}}` + route ⇒ có `conn-see-all`; click ⇒ `push({path:'/incidents/list', query:{asset:'AC-ASSET-2026-00001'}})` | INV-CONNFE-6 | A4 |
| **TC-CONNFE-08** | **Bug người dùng báo**: `{count:7, total:7, deep_link_filters:{}}` ⇒ trong ô đó **0** `conn-see-all` (dù `count > 0`) | INV-CONNFE-7 | A4 |
| **TC-CONNFE-09** | BE cũ (`deep_link_filters === undefined`): `filters:{name:['in',['A','B']]}` ⇒ **0** nút; `filters:{asset:'X'}` ⇒ có nút với `query:{asset:'X'}`; **không** URL nào chứa `in,A,B` | INV-CONNFE-8 | A4 |
| **TC-CONNFE-10** | `{total:12, truncated:1, capped:false, items:5}` ⇒ text chứa `Đang xem 5/12`; `{total:3, truncated:0, items:3}` ⇒ **không** chứa `Đang xem` | INV-CONNFE-9 | A5 |
| **TC-CONNFE-11** | `{count:100, total:100, capped:true, truncated:1, items:5}` ⇒ text chứa `100+` ∧ **không** chứa `còn ` ∧ **không** chứa `95` | INV-CONNFE-9 | A5 |
| **TC-CONNFE-12** | Ô LEGACY (`items === undefined`, `count:6`) ⇒ hiện nhãn + `6`; **0** `conn-row`; **0** `conn-band` (KHÔNG `Đang xem 0/6`) | INV-CONNFE-9 | A5/A8 |
| **TC-CONNFE-13** | Hình dạng tab: `wrapper.findAll('section').length === 0` ∧ text **không** chứa `"Bản ghi liên quan"` ∧ `vm.total === payload.total` ∧ `typeof vm.reload === 'function'` | INV-CONNFE-10 | A6 |
| **TC-CONNFE-14** | Nhóm toàn ô `total:0` ⇒ **0** phần tử bấm được ∧ **0** `conn-row` trong nhóm ∧ có `conn-empty-summary` chứa nhãn **tiếng Việt** của các ô rỗng | INV-CONNFE-2 | A6 |
| **TC-CONNFE-15** | Ô `{can_create:false, create_route_hint:''}` ⇒ trong **phạm vi ô đó** không tồn tại `[data-testid="conn-create"]` (test còn đúng sau vòng 4) | INV-CONNFE-11 | A7 |
| **TC-CONNFE-16** | Trạng thái phụ trợ: đang tải ⇒ `conn-loading`; API reject ⇒ `conn-error` + nút «Thử lại» ⇒ click gọi lại `getConnections` và render thành công; `groups: []` ⇒ câu tiếng Việt có nghĩa; **không** exception thoát ra ngoài component | — | A8 |
| **TC-CONNFE-17** | *(unit, append vào `connectionsApi.guard.test.ts`)* `connectionLabel` 3 bậc · `connectionCounts` (badge `100+` · band rỗng khi `shown===0` · `truncated` suy ra khi BE cũ) · `deepLinkQuery` (`{}` giữ nguyên `{}` · loại value mảng · ép `String(number)`) · `canSeeAll` (3 điều kiện) | INV-CONNFE-6..9 | A9 |

**Chống test giả xanh (đọc trước khi khai DONE):**
- TC-CONNFE-01 phải **loop `Object.keys(DOCTYPE_ROUTE)`**, không liệt kê tay 20 chuỗi — thêm doctype vào bảng route mà quên nhãn phải **đỏ tự động**.
- TC-CONNFE-08 và -09 chấm trên **phạm vi ô** (`conn-cell` chứa `data-doctype`), không phải toàn wrapper — nút của ô khác sẽ che mất lỗi.
  > ⚠️ **Đính chính 2026-07-28 (AC-CR-93 · [ADR §14 D-CR93-1](./ADR-IMM00-CONNECTIONS-TREE.md))** — bảng testid ở §XVIII.4/§XVIII.8 **không** còn đồng nhất với đoạn trên: tên **CHỐT** là `conn-item` / `conn-count` / `conn-meta` / `conn-row`; `conn-cell` / `conn-badge` / `conn-band` / `conn-row-static` / `conn-loading` / `conn-error` / `conn-retry` / `conn-empty` **retired**. `data-doctype` **KHÔNG** được thêm (3 TC assert `wrapper.html()` sạch tên DocType) ⇒ chấm theo phạm vi ô bằng **nhãn tiếng Việt** hoặc chỉ số. **SSoT hiện hành = §XVIII.8 (cuối file này)**.
- Không assert `wrapper.html()` cho A1: `data-doctype` (hợp lệ theo D-FE-2) sẽ làm test đỏ sai.
- Không hardcode chuỗi ngày (`20/07/2026`): `formatDate` không zero-pad tháng trên ICU chuẩn.

### XVIII.5 AC-CR-89 (vòng 3/5 — FE): TAB riêng + mount lười ở 5 màn Detail (INV-CONNTAB-1..12)

> Quyết định: [`ADR-IMM00-CONNECTIONS-TREE.md` §11](./ADR-IMM00-CONNECTIONS-TREE.md) (D-TAB-1..12) · spec thực thi: [`06 §VIII.5`](./06_Frontend_Design.md) · nghiệp vụ: [`02 §IV.39`](./02_Analysis_Design.md) (FR-00-CONN-02 / BR-00-CONN-18..24).
> **File test**: `frontend/src/views/detailRelatedTab.test.ts` (**MỚI** — guard vị trí + mount lười + ẩn thân trang + prop + nhãn, dùng chung cho 5 màn) · `frontend/src/components/common/tests/DetailTabBar.test.ts` (**MỚI** — unit a11y/RWD) · `frontend/src/views/asset/tests/AssetDetailView.tabBarResponsive.test.ts` (**CẬP NHẬT** — 6 tab, class chấm trên `DetailTabBar.vue`) · `frontend/src/integration/detailReadForbiddenGate.integration.test.ts` (**KHÔNG SỬA MỘT ASSERT NÀO** — nó là bằng chứng A7).
> Lệnh chấm: `cd frontend && npx vitest run` (0 fail toàn suite) + `npx vue-tsc --noEmit` (0 lỗi). **KHÔNG** `npm run build` (= deploy live).

**Hằng số dùng chung của file test (SSoT của guard — thêm màn Detail thứ 6 phải thêm vào đây):**

```ts
const DETAIL_VIEWS = [
  { path: 'src/views/asset/AssetDetailView.vue',              doctype: 'AC Asset' },
  { path: 'src/views/pm/PMWorkOrderDetailView.vue',           doctype: 'PM Work Order' },
  { path: 'src/views/cm/CMWorkOrderDetailView.vue',           doctype: 'Asset Repair' },
  { path: 'src/views/calibration/CalibrationDetailView.vue',  doctype: 'IMM Asset Calibration' },
  { path: 'src/views/incident/IncidentDetailView.vue',        doctype: 'Incident Report' },
] as const
```

| TC | Nội dung | INV | Acceptance |
|---|---|---|---|
| **TC-CONNTAB-01** | *(source-scan, loop `DETAIL_VIEWS`)* mỗi file: `<RelatedRecords` xuất hiện **đúng 1** lần ∧ `indexOf('data-testid="tab-panel-related"') < indexOf('<RelatedRecords')` ∧ thẻ mở panel liên quan chứa `v-if` **và không** chứa `v-show` ∧ thẻ mở panel chính chứa `v-show` | INV-CONNTAB-1/2 | A1 |
| **TC-CONNTAB-02** | Mount `PMWorkOrderDetailView` (phiếu hợp lệ, tab mặc định) ⇒ spy `getConnections` gọi **0** lần ∧ `find('[data-testid="related-records"]').exists() === false` | INV-CONNTAB-3 | A2 |
| **TC-CONNTAB-03** | Cùng wrapper: `trigger('click')` trên `[data-testid="tab-related"]` + `flushPromises()` ⇒ `getConnections` gọi **đúng 1** lần ∧ `findAll('[data-testid="related-records"]').length === 1` | INV-CONNTAB-4 | A2 |
| **TC-CONNTAB-04** | Tab liên quan active ⇒ `find('[data-testid="tab-panel-detail"]').attributes('style')` **chứa** `display: none`; bấm về tab chính ⇒ style **không** chứa `display: none` ∧ `[data-testid="tab-panel-related"]` **không tồn tại** | INV-CONNTAB-5/6 | A3 |
| **TC-CONNTAB-05** | Màn PM: `setValue('ghi chú thử')` vào `#tech-notes` → sang tab liên quan → quay lại ⇒ `element.value === 'ghi chú thử'` (đọc từ DOM, **không** đọc ref) | INV-CONNTAB-7 | A4 |
| **TC-CONNTAB-06** | Đổi tab qua-lại 1 vòng ⇒ spy nạp chi tiết gọi **đúng 1** lần: PM `fetchWorkOrder`, Sự cố `getIncident` | INV-CONNTAB-8 | A4 |
| **TC-CONNTAB-07** | *(loop 5 màn, stub `RelatedRecords` ghi lại props)* mở tab liên quan ⇒ `findComponent(Stub).props()` khớp **đúng** cặp: `AC Asset`/`store.currentAsset.name` · `PM Work Order`/`wo.name` · `Asset Repair`/`wo.name` · `IMM Asset Calibration`/`props.id` · `Incident Report`/`name` | INV-CONNTAB-9 | A5 |
| **TC-CONNTAB-08** | Nhãn tab: `DETAIL_RELATED_TABS` = đúng `[Chi tiết, Bản ghi liên quan]`; DOM tab bar của **cả 5** màn ⇒ text ⊂ tập nhãn VI đã duyệt, **không** chứa bất kỳ `doctype` nào của `DETAIL_VIEWS`, **không** chứa `[A-Za-z]{3,}` ngoài danh sách VI cho phép (ví dụ hợp lệ duy nhất ở màn Tài sản: nhãn cũ giữ nguyên) | INV-CONNTAB-10 | A6 |
| **TC-CONNTAB-09** | Gác: (a) trạng thái đang tải ⇒ `[data-testid="detail-tab-bar"]` **không tồn tại** ở cả 5 màn; (b) 403 in-envelope (fixture của `detailReadForbiddenGate`) ⇒ **không** tab bar ∧ **không** `related-records`; (c) `detailReadForbiddenGate.integration.test.ts` chạy lại **xanh, 0 assert bị sửa** | INV-CONNTAB-12 | A7 |
| **TC-CONNTAB-10** | *(unit `DetailTabBar.test.ts`)* `role="tablist"` **1** phần tử; mỗi nút `role="tab"` + `type="button"`; **đúng 1** nút `aria-selected="true"` và nó là tab đang chọn; click nút phát `update:modelValue` với **đúng** `key`; container class chứa `overflow-x-auto`; nút chứa `shrink-0` ∧ `whitespace-nowrap` | INV-CONNTAB-11 | A8 |
| **TC-CONNTAB-11** | *(cập nhật `AssetDetailView.tabBarResponsive.test.ts`)* `AssetDetailView.vue` khai **6** khoá tab (5 cũ + `related`) ∧ nhãn `Bản ghi liên quan` có mặt; phần class cuộn ngang (`overflow-x-auto` · `shrink-0`/`whitespace-nowrap`) chấm trên **`DetailTabBar.vue`**; bỏ `overflow-x-auto` ở component ⇒ test **phải đỏ** (tự kiểm bằng cách sửa tạm rồi hoàn nguyên) | INV-CONNTAB-11 | A9 |
| **TC-CONNTAB-12** | *(sentinel biên thay đổi)* `RelatedRecords.vue` **không** chứa `tab-panel` / `DetailTabBar`; `api/connections.ts` **không** chứa `activeTab` — hợp đồng vòng 1+2 còn đóng băng. *(Đây là **proxy**; bằng chứng chính của A10 là `git diff --name-only` ở DoD.)* | — | A10 |
| **TC-CONNTAB-13** | Màn Tài sản: mount ⇒ tab mặc định `info`, `getConnections` **0** lần (trước vòng này là **1** — đây là điểm đo rõ nhất của cải thiện); mở tab `related` ⇒ **1** lần ∧ panel `info` **không** còn chứa `related-records` | INV-CONNTAB-3/4 | A2 |
| **TC-CONNTAB-14** | Màn CM: chuỗi `v-if` cũ còn nguyên — `store.loading && !wo` ⇒ khung xương ∧ **0** tab bar; `loadBlocked` ⇒ `detail-load-error` ∧ **0** tab bar; `wo` ⇒ có tab bar ∧ lưới `md:grid-cols-5` nằm **trong** `tab-panel-detail` | INV-CONNTAB-12 | A7 |
| **TC-CONNTAB-15** | *(ghi nhận hành vi đã ratify D-TAB-8)* mở tab liên quan → về tab chính → mở lại ⇒ `getConnections` gọi **2** lần (nạp lại là CHỦ ĐÍCH, không phải rò rỉ); test này khoá quyết định "không `<KeepAlive>`" | — | A2 |

**Chống test giả xanh (đọc trước khi khai DONE):**
- **TC-CONNTAB-02/03/13 KHÔNG được stub `RelatedRecords`.** Stub `true` ⇒ spy không bao giờ chạy ⇒ TC-02 xanh **giả** (0 gọi vì bị stub, không phải vì lười) và TC-03 đỏ. Dùng component thật + **partial mock** module: `vi.mock('@/api/connections', async () => ({ ...(await vi.importActual(…)), getConnections: spy }))` — giữ `routeForDoctype`/`detailRouteForDoctype`/`viLabel`/`countBadge`/`previewMeta`/`linkFilters` **thật**, nếu không component sẽ nổ khi render.
- **TC-CONNTAB-07 mới được stub** `RelatedRecords` (mục đích là đọc prop). Hai mục đích ⇒ hai wrapper/file khác nhau; đừng gộp.
- **A2 phải đo bằng spy**, không được suy ra từ mã nguồn ("có `v-if` nên chắc là lười") — `v-if` đặt sai nhánh vẫn có thể mount.
- **Style của `v-show`**: khi panel đang hiện, `attributes('style')` có thể là `undefined` hoặc `''` ⇒ assert `not.toContain('display: none')`, **không** assert bằng `toBe('')`.
- **TC-CONNTAB-05 đọc `element.value` từ DOM**, không đọc `vm.techNotes`: ref sống sót không chứng minh input còn giá trị nếu panel bị unmount rồi tạo lại.
- **TC-CONNTAB-01 phải loop `DETAIL_VIEWS`**, không viết 5 `it()` chép tay — thêm màn Detail thứ 6 mà quên tab phải **đỏ tự động** (đó là toàn bộ giá trị của guard này).
- **TC-CONNTAB-09(c)**: nếu `detailReadForbiddenGate.integration.test.ts` đỏ, **sửa view**, tuyệt đối không sửa assert của nó — đỏ ở đó nghĩa là tab bar đang render trên phiếu bị từ chối đọc (nút tab chết).
- **Đếm file test**: toàn suite phải đi từ ≥268 lên ≥273 file; suite giảm hoặc đứng yên ⇒ có file bị ghi đè nhầm.

---

### XVIII.6 AC-CR-90 (vòng 4/5 — BE+FE): `can_create` là GƯƠNG của enforcement + `create_prefill` (INV-CONN4-1..10 · INV-CONNFE4-1..5)

> Hợp đồng: [`05 §III.24.7`](./05_API_Specification.md) · quyết định: [ADR §12](./ADR-IMM00-CONNECTIONS-TREE.md) · code shape BE: [`04 §V.8`](./04_Backend_Design.md) · FE: [`06 §VIII.6`](./06_Frontend_Design.md).
> **File test BE**: `assetcore/tests/test_connections_tree.py` (**append**) + `assetcore/tests/test_connections_create.py` (**MỚI** — parity 3 điểm + oracle ma trận) + `assetcore/tests/test_imm12.py` (**append** — EC-12-05).
> **`test_connections.py` (11 TC) vẫn KHÔNG được sửa một dòng nào.** TC cũ `TC-CONN-T-19` (cổng vòng đời chặn-tất) **PHẢI đổi kỳ vọng** — đây là **breakage đã khai báo trước**, hợp lệ, xem XVIII.6.4.

#### XVIII.6.1 Fixture

- 3 `AC Asset` **cùng category**, mỗi cái đặt sẵn một `lifecycle_status`: `Active` · `Out of Service` · `Decommissioned` (đặt bằng `frappe.db.set_value` — vòng này test **vị-từ đọc**, không test cỗ máy transition).
- Mỗi thiết bị **mới tinh**: **0** `Asset Repair` đang mở (nếu không, oracle đỏ vì `IMM09_ASSET_HAS_OPEN_WO` — biến nhiễu, xem D-CR4-6).
- 1 user **đủ 4 capability** (`pm.create` · `repair.create` · `calibration.create` · `corrective.create`) cho nhóm oracle; 1 user **hạn chế** (chỉ base role) cho nhóm phân quyền.
- Dọn bằng `tests/_asset_cleanup.purge_asset` / `purge_category_by_name` trong `tearDownClass`; **mọi bản ghi do oracle tạo ra** (PM WO / Asset Repair / Calibration / Incident) phải bị xoá — oracle **tạo thật**, không mock.

#### XVIII.6.2 Test case ↔ invariant ↔ acceptance

| TC | Nội dung | INV | AC |
|---|---|---|---|
| **TC-CONN4-01** | Mỗi ô của mọi hub có **đủ 13 khoá**; `create_prefill` là `dict`, mọi value `str` | INV-CONN4-8 | AC1 |
| **TC-CONN4-02** | **Bất biến BA CHIỀU** trên **toàn bộ** doctype allowlist: `can_create == False ⟺ create_route_hint == "" ∧ create_prefill == {}` — **0 ô vi phạm** | INV-CONN4-1 | AC1 |
| **TC-CONN4-03** | **Binding token**: `∀ (dt, token) ∈ CREATE_CAPABILITY ⇒ rbac.CAPABILITY_MAP[token] == (dt, "create")` | INV-CONN4-2 | AC2 |
| **TC-CONN4-04** | **Parity 3 điểm** cho 5 doctype khai token — cả 3 giá trị **derive từ nguồn**: (1) chuỗi cap tại **chính** hàm tạo trong `api/imm08\|imm09\|imm11\|imm12\|purchase.py` (đọc AST/nguồn, **không** chép hằng), (2) `CREATE_CAPABILITY[dt]`, (3) `requiredCapabilities` của route có `path == CREATE_CONTEXT[dt].route` đọc từ `frontend/src/router/index.ts` ⇒ **ba bằng nhau** | INV-CONN4-3 | AC2 |
| **TC-CONN4-05** | `AC Asset` @ **`Out of Service`** ⇒ `can_create is True` cho «Phiếu sửa chữa» + «Sự cố»; `is False` cho «Phiếu bảo trì (PM)» + «Phiếu hiệu chuẩn» | INV-CONN4-4 | AC3 |
| **TC-CONN4-06** | `AC Asset` @ **`Decommissioned`** ⇒ `can_create is False` cho **cả 4** | INV-CONN4-5 | AC3 |
| **TC-CONN4-07** | **ORACLE 4×3** (12 ca): với user đủ cap, `can_create` của ô **==** `(gọi THẬT service tạo tương ứng KHÔNG raise)` — `imm08.create_adhoc_work_order` · `imm09.create_work_order` · `imm11.create_calibration` · `imm12.report_incident`. Ca "không raise" phải **thật sự tạo** rồi dọn; ca "raise" khẳng định **0 bản ghi mới** | INV-CONN4-6 | AC4 |
| **TC-CONN4-08** | **Anti-false-green cho oracle**: đảo **một** nhánh của `_create_lifecycle_allows` (vd cho `Asset Repair` dùng `BLOCKED_FOR_WO`) ⇒ TC-CONN4-07 **phải đỏ**. Ghi kỹ thuật kiểm chứng vào docstring (không cần commit mutation) | INV-CONN4-6 | AC4 |
| **TC-CONN4-09** | **Prefill đúng khoá**: `AC Asset` @ `Active` ⇒ ô «Phiếu bảo trì (PM)» `create_prefill == {"asset": <mã thiết bị>}`; ô «Phiếu sửa chữa» tương tự; hub `Incident Report` ⇒ ô «Phiếu sửa chữa» `{"incident": <mã sự cố>}`; hub `PM Work Order` ⇒ ô «Phiếu sửa chữa» `{"pm_wo": <mã phiếu>}` | INV-CONN4-8 | AC5 |
| **TC-CONN4-10** | **Prefill ⊆ khoá màn ĐỌC**: ∀ (dt, parent) ∈ `query_keys` ⇒ khoá đó xuất hiện dưới dạng `route.query.<key>` trong **chính** file `.vue` của route `CREATE_CONTEXT[dt].route` (đọc `router/index.ts` để lấy đường dẫn component) | INV-CONN4-7 | AC5 |
| **TC-CONN4-11** | **ZERO-COST không đổi**: wrap `frappe.get_list` ⇒ vẫn **đúng 1 lời gọi/ô**; `frappe.db.count`/`frappe.db.sql` patch raise ⇒ **không** raise; `lifecycle_status` đọc **đúng 1 lần/cây** (đếm lời gọi `frappe.db.get_value` trên `AC Asset`) | INV-CONN4-10 | AC7 |
| **TC-CONN4-12** | User **hạn chế** (0 cap): mọi ô ⇒ `can_create is False` ∧ `create_route_hint == ""` ∧ `create_prefill == {}` | INV-CONN4-1/2 | AC1 |
| **TC-CONN4-13** | `api/imm00.create_incident` — thiếu `corrective.create` ⇒ **`frappe.PermissionError`**; `count("Incident Report")` **trước == sau** | INV-CONN4-9 | AC6 |
| **TC-CONN4-14** | `api/imm00.create_incident` — `asset` **không tồn tại** ⇒ envelope `success is False` ∧ `code == NOT_FOUND` (**HTTP-200 in-envelope**, không raise); `count("Incident Report")` **trước == sau** | INV-CONN4-9 | AC6 |
| **TC-CONN4-15** | `api/imm00.create_incident` — payload hợp lệ **kèm** khoá độc (`status='Closed'`, `reported_by='x@y.z'`, `reported_to_byt=1`, `docstatus=1`) ⇒ tạo được, nhưng bản ghi **KHÔNG** mang giá trị nào trong số đó (whitelist ăn) | INV-CONN4-9 | AC6 |
| **TC-CONN4-16** | `services/imm12.report_incident` — asset `Decommissioned` ⇒ lỗi nghiệp vụ mã `IMM12-ASSET-DECOMMISSIONED` (`http_status 422`), **0** bản ghi mới; asset `Out of Service` ⇒ **tạo được** (EC-12-05 chỉ chặn `Decommissioned`) | BR-12-29 | AC3/AC4 |
| **TC-CONN4-17** | **Registry parity**: `MSG.IMM12_ASSET_DECOMMISSIONED` ∈ registry `utils/messages.py` với đủ `title/template/action_hint/severity/http_status` và có **call-site THẬT** trong `services/imm12.py` | BR-12-29 | AC6 |

> ⚠️ **TC-CONN4-04 phải neo theo TÊN HÀM, không phải "hit đầu tiên trong file"** — cùng một token xuất hiện ở **nhiều** call-site: `pm.create` có **4** call-site trong `api/imm08.py`, `calibration.create` có **2** trong `api/imm11.py` (`create_calibration_schedule` **và** `create_calibration`), `repair.create` có **2** trong `api/imm09.py`. Grep cả file rồi lấy hit đầu = **guard đỏ giả hoặc xanh giả**. Bảng neo (verify @source 2026-07-28):
>
> | DocType đích | Module API | **Hàm neo** | Cách đọc |
> |---|---|---|---|
> | `PM Work Order` | `api/imm08.py` | `create_pm_work_order` | AST: `rbac.require("<cap>")` **trong thân hàm này** |
> | `Asset Repair` | `api/imm09.py` | `create_repair_work_order` | như trên |
> | `IMM Asset Calibration` | `api/imm11.py` | `create_calibration` | như trên (**không** phải `create_calibration_schedule`) |
> | `Incident Report` | `api/imm12.py` | hằng module `_CAP_REPORT` | AST: gán hằng (`rbac.can` + 403 in-envelope, không `rbac.require`) |
> | `AC Purchase` | `api/purchase.py` | `create_purchase` | AST: `rbac.require("<cap>")` trong thân hàm |
>
> Tương tự, đọc `requiredCapabilities` phải neo theo **`path` khớp `CREATE_CONTEXT[dt].route`**, không phải theo thứ tự xuất hiện. Guard phải chịu được `meta` xuống dòng và nháy đơn/kép; khi đỏ, phân biệt **"đổi cap"** (bug thật) với **"đổi hình thức khai"** (sửa guard).

#### XVIII.6.3 Test FE (`RelatedRecords.test.ts` — append)

| TC | Nội dung | INV |
|---|---|---|
| **TC-CONNFE4-01** | `can_create:false` (kể cả khi `create_route_hint`/`create_prefill` bị BE lỗi gửi kèm) ⇒ **0** nút `related-create-*` trong DOM | INV-CONNFE4-1 |
| **TC-CONNFE4-02** | `create_route_hint` **không phân giải** được trong router giả ⇒ **0** nút (resolve-or-hide) | INV-CONNFE4-1 |
| **TC-CONNFE4-03** | Click nút ⇒ `router.push` gọi với **`{ path: '/cm/create', query: { asset: 'AC-ASSET-…' } }`** — khẳng định **đối số object**, không phải chuỗi/`path` trần | INV-CONNFE4-2 |
| **TC-CONNFE4-04** | `create_prefill` thiếu (`undefined`, BE chưa reload) ⇒ `router.push` gọi với `{ path }` (không khoá bịa, không `?` cụt) | INV-CONNFE4-3 |
| **TC-CONNFE4-05** | Nhãn nút = `Tạo phiếu sửa chữa`; `wrapper.text()` **không** chứa `Asset Repair`, **không** khớp `/\b[a-z]+\.(create|read|write)\b/` | INV-CONNFE4-4 |
| **TC-CONNFE4-06** | Ô `total: 0` ∧ `can_create: true` ⇒ **vẫn có** nút tạo | INV-CONNFE4-5 |

#### XVIII.6.4 Breakage đã khai báo trước (hợp lệ — QA không chấm là nới guard)

- **`TC-CONN-T-19`** (§XVIII.2) hiện khẳng định *"`Decommissioned` ⇒ **mọi** ô `can_create is False`"* dựa trên cổng chặn-tất `BLOCKED_FOR_WO`. Sau vòng 4, mệnh đề `Decommissioned` **vẫn đúng cho 4 doctype phiếu** nhưng **không còn đúng cho `Asset Document`/`Asset Transfer`/`AC Purchase`/`Service Contract`** (chúng không có cổng vòng đời — gương của service). ⇒ **thu hẹp** TC-CONN-T-19 về 4 doctype phiếu và **thêm** TC-CONN4-05/06 cho ma trận đầy đủ. Sau khi sửa, TC vẫn phải **đỏ** nếu ai bỏ cổng vòng đời của PM/Hiệu chuẩn.
- **`TC-CONN-T-01`** (đủ 12 khoá) → **13 khoá**.
- Không TC nào khác của §XVIII.2 được đổi assert.

#### XVIII.6.5 DoD vòng 4 (chấm ĐỎ nếu thiếu bất kỳ mục nào)

- `bench --site miyano run-tests --app assetcore --module assetcore.tests.test_connections` **XANH** (11 TC, **0 assert bị sửa**).
- `bench --site miyano run-tests --app assetcore --module assetcore.tests.test_connections_tree` **XANH**.
- `bench --site miyano run-tests --app assetcore --module assetcore.tests.test_connections_create` **XANH** (file MỚI).
- `bench --site miyano run-tests --app assetcore --module assetcore.tests.test_imm09` **XANH** · `... test_imm12` **XANH**.
- `cd frontend && npx vitest run` **0 fail**; `npx vue-tsc --noEmit` **0 lỗi**.
- **Guard count: DELTA = 0.** `_EXPECTED_TEST_COUNT` (`tests/test_mobile_oas.py`) và `_GUARD_SUITE_SUM` (`tests/test_mobile_docset.py`) là counter của **guard-suite MOBILE/OAS 7 module**; vòng này **0 op OAS**, test mới **không** thuộc suite ⇒ **KHÔNG đụng**. Nếu vì lý do nào đó phải đụng: đọc số **trên đĩa** trước (đọc 2026-07-28: `1024` / `1167` / `_MOBILE_OAS_TOTAL 1193`) và chỉ sửa theo delta THẬT.
- `git diff --name-only` chỉ chứa: `services/shared/connection_meta.py` · `services/connections.py` · `api/imm00.py` · `services/imm12.py` · `utils/messages.py` · 3 file test BE · `frontend/src/api/connections.ts` · `frontend/src/components/common/RelatedRecords.vue` · file test FE · `docs/imm-00/*` · `docs/imm-12/*`.
- ⏱ Mọi lệnh `bench run-tests` đặt timeout tool **≥ 600000ms** (kill giữa chừng = `tearDownClass` không chạy = **nhiễm DB**, không phải bug sản phẩm).
- ⚠️ `--preload`: sửa `api/*.py` **không** có hiệu lực qua HTTP tới khi USER reload ⇒ **chấm bằng `run-tests`, KHÔNG curl**.

---

### XVIII.7 AC-CR-91 (vòng 5/5 — FE): «Xem tất cả» dẫn tới danh sách **ĐÃ LỌC** (INV-CONNFE5-1..11 · INV-CONN-16/17)

> Quyết định: [ADR §13](./ADR-IMM00-CONNECTIONS-TREE.md) · spec FE: [`06 §VIII.7`](./06_Frontend_Design.md).
> **File test FE**: `frontend/src/guards/connectionsListParity.guard.test.ts` (**MỚI** — guard tĩnh) + `api/connectionsApi.guard.test.ts` (**append** + **1 assert sửa**) + `components/common/RelatedRecords.test.ts` (**append**) + test render 2 màn wire.
> **File test BE**: `assetcore/tests/test_connections_tree.py` (**chỉ append 2 TC**). **Payload BE 0 thay đổi** ⇒ `test_connections.py` (11 TC) **không sửa một dòng nào**.

#### XVIII.7.1 Vì sao 4 vòng test xanh vẫn để lọt 13/16 ô

`INV-CONNFE-6` chỉ đòi *"ô có ≥ 1 khoá lọc"* — nó đếm **sự tồn tại của khoá**, không hỏi **khoá đó có ai đọc không**. Nút vẫn render, `router.push` vẫn đúng đối số, test vẫn xanh — trong khi màn đích **bỏ qua** query. Đây là *test đúng mệnh đề sai*: mệnh đề cần là **"khoá tới được nơi có người đọc"**.

Vòng 4 đã bịt đúng lỗ này cho nhánh **tạo** (`connectionsCreateParity.guard.test.ts`: đối chiếu khoá ⇄ `route.query.<key>` trong **chính** file view). Vòng 5 mang **nguyên khuôn** đó sang nhánh **danh sách**. Bài học chung: *deep-link chỉ được chấm xanh khi guard đọc tới file view của route đích* — không có đường tắt nào rẻ hơn mà đúng.

#### XVIII.7.2 Guard tĩnh MỚI — `frontend/src/guards/connectionsListParity.guard.test.ts`

Mirror `connectionsCreateParity.guard.test.ts`: đọc `src/router/index.ts` bằng phân tích văn bản → cắt block route theo `path: '<p>'` → lấy file view từ `component: () => import('@/…')` → `readFileSync` file view → assert.

| TC | Nội dung | INV |
|---|---|---|
| **TC-CONNLIST-01** | ∀ entry ∈ `DOCTYPE_LIST_TARGET`: `path` **có** trong `router/index.ts` ∧ phân giải được ra file view tồn tại | INV-CONNFE5-1 |
| **TC-CONNLIST-02** | ∀ entry: source file view **chứa** `route.query.<queryKey>` ⇒ không ai khai được khoá mà màn đích không đọc | INV-CONNFE5-2 |
| **TC-CONNLIST-03** | ∀ doctype ∈ `LIST_TARGET_NO_FILTER`: view của `DOCTYPE_ROUTE[doctype]` **KHÔNG** chứa `route.query.asset` (allowlist **chỉ-giảm**) | INV-CONNFE5-3 |
| **TC-CONNLIST-04** | `keys(DOCTYPE_ROUTE)` == `keys(DOCTYPE_LIST_TARGET) ∪ LIST_TARGET_NO_FILTER` ∧ giao == ∅ ⇒ **0 doctype vùng xám** (20 = 9 + 11) | INV-CONNFE5-4 |
| **TC-CONNLIST-05** | ∀ doctype ∈ `DOCTYPE_LIST_TARGET`: `DOCTYPE_LIST_TARGET[dt].path === DOCTYPE_ROUTE[dt]` ⇒ hai bản đồ **không** lệch đường dẫn | INV-CONNFE5-1 |

> ⚠️ **Cách TC-CONNLIST-03 được phép ĐỎ:** một view trong allowlist bắt đầu đọc `route.query.asset` ⇒ **đỏ có chủ đích** ⇒ người sửa phải **thăng hạng** doctype đó sang `DOCTYPE_LIST_TARGET` (allowlist chỉ được **giảm**, không được phình). Đỏ ở đây **không** phải guard hỏng.
> ⚠️ `routeBlock()` cắt tới `path: '` kế tiếp ⇒ **thứ tự khai route quan trọng**. `/incidents/list` phải được tìm bằng chuỗi **chính xác** `path: '/incidents/list'` (đừng khớp tiền tố `/incidents`), và `/rca` đừng khớp nhầm `/rca/:id`. Dùng so khớp **nguyên chuỗi có nháy đóng**.

#### XVIII.7.3 Test thuần (`api/connectionsApi.guard.test.ts` — append + **1 assert sửa**)

| TC | Nội dung | INV |
|---|---|---|
| **TC-FE-CONN-30** | **DỊCH khoá**: `{doctype:'PM Work Order', deep_link_filters:{asset_ref:'AC-1'}}` ⇒ `{path:'/pm/work-orders', query:{asset:'AC-1'}}`. Tương tự `Asset Commissioning`/`final_asset` ⇒ **`null`** (không có trong bản đồ) | INV-CONNFE5-5 |
| **TC-FE-CONN-31** | `deep_link_filters = {name:'a,b,c'}` ⇒ **`null`** (internal_links nhiều bản ghi) | INV-CONNFE5-6 |
| **TC-FE-CONN-32** | `deep_link_filters = {}` ∧ `filters = {asset_ref:'AC-1'}` ⇒ **`null`** (**KHÔNG** fallback — D-FE-6 quy tắc 1) | INV-CONNFE5-6 |
| **TC-FE-CONN-33** | `deep_link_filters` **vắng mặt** (`undefined`) ∧ `filters = {asset_ref:'AC-1'}` ⇒ vẫn dịch được (tolerant reader cho backend **thật sự cũ**) | INV-CONNFE5-5 |
| **TC-FE-CONN-34** | 2 khoá còn lại sau khi loại `name` ⇒ **`null`**; value rỗng/khoảng trắng ⇒ **`null`** | INV-CONNFE5-6 |
| **TC-FE-CONN-35** | Doctype ∈ `LIST_TARGET_NO_FILTER` (vd `IMM CAPA Record`) ⇒ **`null`** dù có khoá lọc hợp lệ | INV-CONNFE5-6 |
| **⚠️ SỬA** `linkFilters` | Assert cũ `'deep_link_filters rỗng ⇒ fallback filters (backend cũ)'` ⇒ **đổi kỳ vọng thành `null`** | ADR §13.2 |

> **Breakage đã khai báo trước (hợp lệ — QA KHÔNG chấm là nới guard):** assert `linkFilters({deep_link_filters:{}, filters:{asset:'A1'}}) === {asset:'A1'}` đang **ossify một cài đặt phản D-FE-6**. Hợp đồng đúng từ vòng 2; code lệch; test khoá cái lệch. Sửa **test theo hợp đồng**, không sửa hợp đồng theo test. Chi tiết + hậu quả production: ADR §13.2.

#### XVIII.7.4 Test render (`RelatedRecords.test.ts` — append)

| TC | Nội dung | INV |
|---|---|---|
| **TC-CONNFE5-01** | Ô `total > 0`, doctype ∈ `LIST_TARGET_NO_FILTER` ⇒ **0** `[data-testid="conn-see-all"]` trong ô **∧** preview 5 dòng **vẫn render** (mất nút ≠ mất dữ liệu) | INV-CONNFE5-7 |
| **TC-CONNFE5-02** | Ô `PM Work Order` + `deep_link_filters:{asset_ref:'AC-1'}` ⇒ click ⇒ `router.push` gọi **đúng 1 lần** với `{path:'/pm/work-orders', query:{asset:'AC-1'}}` — khẳng định **object**, và khẳng định **`asset_ref` KHÔNG** có trong đối số | INV-CONNFE5-8 |
| **TC-CONNFE5-03** | `can` stub trả `false` cho cap của route đích ⇒ **0** nút «Xem tất cả» trong ô đó (dead-gate `/unauthorized`) | INV-CONNFE5-9 |
| **TC-CONNFE5-04** | Ô `internal_links` (`deep_link_filters:{name:'A,B'}`) ⇒ **0** nút, **0** `router.push` | INV-CONNFE5-7 |
| **TC-CONNFE5-05** | `wrapper.text()` + `wrapper.html()` **không** chứa `asset_ref` / `final_asset` / `critical_asset` / tên DocType tiếng Anh nào (LL-FE-53) | INV-CONNFE5-11 |
| **TC-CONNFE5-06** | **Đếm trên payload GIỐNG THẬT** (19 ô của `ac_asset_dashboard`): số ô có `conn-see-all` **== 9**; số nút mà `listTarget` trả `null` **== 0** ⇒ acceptance "≥ 8 lọc / 0 không lọc" được **khoá bằng test**, không chỉ đo tay | AC vòng |

#### XVIII.7.5 Test render 2 màn wire (Incident · RCA)

| TC | Nội dung | INV |
|---|---|---|
| **TC-CONNFE5-07** | Mount `IncidentListView` với `route.query = {asset:'AC-1'}` ⇒ `listIncidents` (mock) được gọi **kèm `asset:'AC-1'`** ngay lần nạp **đầu tiên** (không nạp-rồi-lọc-lại) | INV-CONNFE5-10 |
| **TC-CONNFE5-08** | DOM chứa chip **`Thiết bị: AC-1`** + nút bỏ lọc; bấm bỏ lọc ⇒ gọi lại **không** kèm `asset` | INV-CONNFE5-10 |
| **TC-CONNFE5-09** | Đổi `route.query.asset` → `AC-2` ⇒ gọi lại kèm `asset:'AC-2'` (drill lần 2 trên cùng route) | INV-CONNFE5-10 |
| **TC-CONNFE5-10** | `asset` **cộng dồn** với `status`/`severity` (Incident) và `method`/`status` (RCA): đặt lọc thiết bị **không** xoá lọc trạng thái đang có và ngược lại | ADR §D-CR5-7 |
| **TC-CONNFE5-11** | Cùng bộ TC-07..10 cho `RCAListView` với `listRcas` | INV-CONNFE5-10 |

> ⚠️ **Bẫy xanh-giả số 1:** assert "view đọc `route.query.asset`" **không đủ** — phải assert **đối số gọi API**. Một view đọc query rồi quên truyền xuống store sẽ qua guard tĩnh nhưng người dùng vẫn thấy danh sách đầy đủ.
> ⚠️ **Bẫy xanh-giả số 2:** mock store trả mảng rỗng cho **mọi** tham số ⇒ "lọc" và "không lọc" nhìn giống nhau. Mock phải phân biệt được: trả **tập khác nhau** theo `params.asset`.

#### XVIII.7.6 Test BE (`test_connections_tree.py` — **chỉ append 2 TC**, payload KHÔNG đổi)

| TC | Nội dung | INV |
|---|---|---|
| **TC-CONN-T-23** | ∀ hub ∈ `iter_dashboard_modules()`, ∀ ô: ô **reverse-link** ⇒ `len(deep_link_filters) == 1` ∧ khoá **≠** `"name"`; ô **internal-link** ⇒ khoá **==** `"name"` | **INV-CONN-16** |
| **TC-CONN-T-24** | Ô **reverse-link**: **giá trị** của khoá `deep_link_filters` **==** mã bản ghi cha (`name` truyền vào `build_connections`) | **INV-CONN-17** |

Hai TC này đóng đinh chính hai giả định mà `listTarget` dựa vào. Vỡ INV-CONN-16 ⇒ FE trả `null` ⇒ **nút biến mất câm lặng**. Vỡ INV-CONN-17 ⇒ dịch khoá giữ nguyên value ⇒ lọc ra **nhầm hồ sơ** (tệ hơn không lọc, vì trông như đã lọc đúng).

> Dùng lại fixture + reader giả sẵn có của file (`list_fn` tiêm vào) ⇒ **0 truy vấn thật**, **0** ảnh hưởng ZERO-COST (INV-CONN-6). **KHÔNG** sửa assert của 23 TC hiện có.

#### XVIII.7.7 DoD vòng 5 (chấm ĐỎ nếu thiếu bất kỳ mục nào)

- `cd frontend && npx vitest run` **0 fail**. Baseline **trước vòng: 278 file / 2591 test, toàn xanh** (đo 2026-07-28) ⇒ báo cáo **trước → sau**.
- `npx vue-tsc --noEmit` **0 lỗi**.
- `bench --site miyano run-tests --app assetcore --module assetcore.tests.test_connections_tree` **XANH**. Baseline **trước vòng: 23 TC** (`grep -c '    def test_'`) → **sau: 25**.
- `bench --site miyano run-tests --app assetcore --module assetcore.tests.test_connections` **XANH** (11 TC, **0 assert bị sửa** — payload BE không đổi).
- Đo trên tab của **1 AC Asset** (persona đủ capability): ô «Xem tất cả» **đã lọc** ≥ **8** (dự kiến **9**) · nút mở ra danh sách **KHÔNG lọc** = **0** · 404/route chết = **0**.
- **Guard count: DELTA = 0.** Vòng này **0 op OAS, 0 endpoint mới** ⇒ **KHÔNG đụng** `_EXPECTED_TEST_COUNT` / `_GUARD_SUITE_SUM` / `_MOBILE_OAS_TOTAL`.
  > 📌 **Giá trị ĐÚNG đọc THẲNG từ đĩa 2026-07-28: `1024` / `1167` / `1193`.** Con số `983 / 1126 / 1152` lưu hành trong prompt/STATE là **STALE** (chụp trước khi AC-CR-80..86 land). Truy nguyên xong ⇒ **không chỉnh số cho khớp bên nào**: vòng này delta 0, cứ để nguyên giá trị trên đĩa. Vòng sau nếu phải sửa counter thì **đọc lại đĩa trước**, đừng tin số trong tài liệu bàn giao.
- ⏱ Mọi lệnh `bench run-tests` đặt timeout tool **≥ 600000ms**.
- ⛔ **KHÔNG** `npm run build` (= deploy live) · **KHÔNG** `git commit/push` · **KHÔNG** `bench migrate`.

### XVIII.8 AC-CR-93 (FE): **chỉ render ô có dữ liệu** + ô rỗng gộp một dòng/nhóm (INV-CONNFE6-1..9)

> Quyết định: [ADR §14](./ADR-IMM00-CONNECTIONS-TREE.md) (D-CR93-1..7 · §14.7 danh mục supersede · §14.8 breakage) · spec thực thi: [`06 §VIII.8`](./06_Frontend_Design.md) · nghiệp vụ: [`02 §IV.39`](./02_Analysis_Design.md) (FR-00-CONN-04 / BR-00-CONN-35..41).
> **File test**: `frontend/src/components/common/tests/RelatedRecords.test.ts` (**append 7 TC + đúng 1 TC sửa** — TC-FE-CONN-10 `:283`, xem §XVIII.8.4) · `frontend/src/guards/connectionsApi.guard.test.ts` (**chỉ append** 4 TC helper thuần; **0** assert cũ bị sửa).
> **Quy ước số hiệu (chốt để không sinh hệ thứ ba)**: TC render/unit của họ Connections đánh số **tiếp** theo *file test đã ship* — `TC-FE-CONN-24..30` (render) và `TC-FE-CONN-40..43` (unit). Hệ `TC-CONNFE-xx` / `TC-CONNFE5-xx` ở §XVIII.4/§XVIII.7 là **tên tài liệu của vòng 2/5**, giữ nguyên để truy vết, **không** dùng cho TC mới.
> Lệnh chấm: `cd frontend && npx vitest run` (0 fail toàn suite) + `npx vue-tsc --noEmit` (0 lỗi). **KHÔNG** `npm run build` (= deploy live) · **KHÔNG** chạy suite BE (vòng FE-thuần; phải chạy = scope sai).

#### XVIII.8.1 Fixture — **giống thật**, không fixture 2 ô cho tiện

```ts
// PAYLOAD_19: khuôn đồ thị `ac_asset_dashboard` — 19 ô / ĐÚNG 3 ô có dữ liệu / 4 nhóm,
// trong đó ≥1 nhóm có MỌI ô total:0 (ca AC5). Mỗi ô có label_vi tiếng Việt.
// Ô rỗng: total:0, truncated:0, items:[]  ·  Ô có dữ liệu: total>0 + ≥1 dòng items[]
```

Fixture 2 ô **không đủ**: acceptance đòi *giảm ≥ 84%* và *số tiêu đề nhóm == số nhóm có dữ liệu* — cả hai chỉ có nghĩa trên payload nhiều nhóm. Nhãn VI trong fixture là **fixture**, không phải bản đồ sản phẩm (SSoT vẫn là `connection_meta.LABEL_VI` — INV-CONN-7 canh phía BE).

#### XVIII.8.2 Test RENDER (`RelatedRecords.test.ts` — append)

| TC | Nội dung | INV | AC |
|---|---|---|---|
| **TC-FE-CONN-24** | Mount `PAYLOAD_19` ⇒ `findAll('[data-testid="conn-item"]').length === 3` (**không** 19) ∧ tỉ lệ giảm `1 - 3/19 ≥ 0.84`. Đếm bằng **`findAll(testid).length`**, KHÔNG bằng `text().includes` | INV-CONNFE6-1 | AC1 |
| **TC-FE-CONN-25** | **∀ ô `total===0`**: nhãn VI của nó xuất hiện trong **đúng 1** `[data-testid="conn-empty-summary"]` **thuộc chính `conn-group`** của nó ∧ mỗi `conn-group` có **≤1** dòng gộp ∧ dòng gộp khớp `/^Chưa có: /` ∧ `summary.html()` chứa **0** chuỗi ∈ `Object.keys(DOCTYPE_ROUTE)` (**loop**, không liệt kê tay) | INV-CONNFE6-2/3 | AC2 |
| **TC-FE-CONN-26** | Trong **mỗi** `conn-empty-summary`: `findAll('button')` **0** ∧ `findAll('a')` **0** ∧ `[data-testid="conn-row"]` **0** ∧ `conn-see-all` **0** ∧ `conn-create` **0**; `html()` **không** chứa `role="button"` / `cursor-pointer` | INV-CONNFE6-4 | AC3 |
| **TC-FE-CONN-27** | (a) Ô LEGACY `{count:6, total:undefined, items:undefined}` ⇒ **có** `conn-item` riêng ∧ nhãn + `6` hiện ra. (b) **∀ ô bị gộp** (nhãn nằm trong dòng gộp): `total ?? count ?? 0 === 0` — tính **từ chính fixture**, khẳng định 0 ô mang dữ liệu bị nuốt | INV-CONNFE6-5 | AC4 |
| **TC-FE-CONN-28** | Payload 3 nhóm (2 nhóm có ≥1 ô dữ liệu, 1 nhóm toàn rỗng) ⇒ `findAll('[data-testid="conn-group-label"]').length === 2` ∧ trong nhóm toàn rỗng: **0** `conn-item`, **0** `conn-group-label`, **đúng 1** `conn-empty-summary` | INV-CONNFE6-6 | AC5 |
| **TC-FE-CONN-29** | Payload **mọi** ô `total:0` (groups **không** rỗng) ⇒ **0** `conn-item` ∧ text chứa `Chưa có bản ghi nào liên quan tới hồ sơ này.` ∧ `findAll('[data-testid="conn-empty-summary"]').length >= 1` ∧ `(vm as {total:number}).total === 0` | INV-CONNFE6-7 | AC5 |
| **TC-FE-CONN-30** | Trạng thái phụ trợ **không** được nói "chưa có": đang tải (promise chưa resolve) ⇒ **0** `conn-empty-summary`; API reject ⇒ **0** `conn-empty-summary` ∧ vẫn có nút «Thử lại»; `groups: []` ⇒ câu VI ∧ **0** `conn-empty-summary` | INV-CONNFE6-7 | AC5 |

#### XVIII.8.3 Test HELPER thuần (`api/connectionsApi.guard.test.ts` — chỉ append)

| TC | Nội dung | INV |
|---|---|---|
| **TC-FE-CONN-40** | `hasConnectionRecords`: `{total:0}` ⇒ `false` · `{total:undefined, count:3}` ⇒ `true` (ô LEGACY) · `{}` ⇒ `false` · `{total:0, items:[row,row]}` ⇒ `false` (**theo con số**, không theo `items.length`) | INV-CONNFE6-5 |
| **TC-FE-CONN-41** | `dataCells`: giữ **đúng thứ tự** payload ∧ loại mọi ô rỗng ∧ nhóm `items: []` ⇒ `[]` | INV-CONNFE6-1 |
| **TC-FE-CONN-42** | `emptyLabels`: ưu tiên `label_vi`, thiếu ⇒ `label`; ô thiếu **cả hai** ⇒ **bị loại** (KHÔNG trả `doctype`) | INV-CONNFE6-3 |
| **TC-FE-CONN-43** | `emptySummary`: 2 ô rỗng ⇒ **đúng chuỗi** `Chưa có: A, B` (khớp `toBe`, không `toContain`) · 0 ô rỗng ⇒ `''` · mọi nhãn rỗng ⇒ `''` | INV-CONNFE6-2 |

#### XVIII.8.4 Breakage đã khai báo TRƯỚC — **đúng 1** TC (QA KHÔNG chấm là nới guard)

**TC-FE-CONN-10** @`RelatedRecords.test.ts:283`: chuyển phạm vi chấm *"ô count 0 render gọn"* từ `conn-item` (`:300`) sang `[data-testid="conn-empty-summary"]`; **giữ nguyên** `0 button` (`:301`) + `0 conn-row` (`:302`) + 3 assert đầu; **bồi** assert nhãn VI ô rỗng nằm trong dòng gộp. Assert cũ đang khoá một cài đặt **phản hợp đồng** (D-FE-8 vòng 2 nói ô rỗng KHÔNG có ô riêng) ⇒ sửa **test theo hợp đồng**, tiền lệ §XVIII.7.3. **22 TC còn lại: 0 assert bị sửa** (mọi ô trong fixture của chúng đều có số đếm > 0 — soát @source: `:139` `count:2` · `:153` `total:1` · `:247` `total:7` · `:320` `total:1` · `:420`-`:425` `total:1`).

#### XVIII.8.5 Chống test giả xanh (đọc trước khi khai DONE)

1. **Đếm phần tử, không đếm chữ**: `expect(w.findAll('[data-testid="conn-item"]').length).toBe(3)`. `text().includes('Chưa có')` xanh cả khi 19 ô vẫn còn nguyên.
2. **Chấm dòng gộp theo PHẠM VI NHÓM** (`conn-group`), không toàn wrapper: một dòng gộp ở nhóm khác sẽ che mất nhóm thiếu (đúng bẫy §XVIII.4 hàng 2 đã gặp).
3. **`html()` cho ca rò tên Anh, `text()` cho ca nhãn VI** — và vì vòng này **cấm** `data-doctype`, `html()` phải sạch **mọi** khoá `DOCTYPE_ROUTE` (loop, không liệt kê tay).
4. **Ô LEGACY là ca dương** (`count>0`, thiếu `total`): thiếu TC-FE-CONN-27(a) thì một cài đặt dùng `items.length` sẽ **xanh** trong khi nuốt ô có dữ liệu.
5. **Không assert số tuyệt đối của suite** (278/2591/2649 đều **có thể stale**): báo cáo **trước → sau** đọc từ chính lần chạy, chấm theo **delta ≥ +6**.
6. **Mutation-check khi land** (guard phải sống): (a) bỏ `v-if` của `conn-group-label` ⇒ TC-28 ĐỎ; (b) đổi vị-từ sang `items.length > 0` ⇒ TC-27/40 ĐỎ; (c) đổi `Chưa có:` thành chuỗi khác ⇒ TC-43 ĐỎ; (d) thêm 1 `<button>` vào dòng gộp ⇒ TC-26 ĐỎ; (e) bỏ lọc `dataCells` ⇒ TC-24 ĐỎ. **5 phép đột biến ⇒ 5 lần đỏ**; không đỏ = test template.

#### XVIII.8.6 DoD vòng AC-CR-93 (chấm ĐỎ nếu thiếu bất kỳ mục nào)

- `cd frontend && npx vitest run` **0 fail** — báo cáo **trước → sau** (ngưỡng **≥ 278 file / ≥ 2591 test**, **+≥6 test mới**; đo trên đĩa 2026-07-28: **280 file**, lần chạy đầy đủ gần nhất **280 file / 2649 test**).
- `npx vue-tsc --noEmit` **0 lỗi**.
- 5 phép mutation-check ở §XVIII.8.5 (6) đều **đỏ** đúng chỗ.
- `git status`: **0** file `.py` thay đổi bởi vòng này; `git diff --name-only` phía FE **chỉ** 4 file ở `06 §VIII.8`; diff của `api/connections.ts` **không** chứa dòng nào thuộc `DOCTYPE_LIST_TARGET` (`:287`) / `LIST_TARGET_NO_FILTER` (`:321`) ⇒ **INV-CONNFE5-4 vẫn phủ kín 20 doctype**.
- **Guard count DELTA = 0**: `_EXPECTED_TEST_COUNT` **1024** · `_GUARD_SUITE_SUM` **1167** · `_MOBILE_OAS_TOTAL` **1193** · OAS **110 / 290 / 38** (đọc THẲNG từ đĩa 2026-07-28) — **không đụng**, và **không** chạy suite BE.
- ⛔ **KHÔNG** `npm run build` · **KHÔNG** `git commit/push` · **KHÔNG** `bench migrate`.

### XVIII.9 AC-CR-94 (FE + 1 nhánh BE): deep-link **ĐẾN ĐÍCH** 2 màn LỊCH + `count == drill` **cross-endpoint** (INV-CONN-18..22 · INV-CONNFE7-1..8)

> Quyết định: [`ADR-IMM00-CONNECTIONS-TREE.md` §15](./ADR-IMM00-CONNECTIONS-TREE.md) (D-CR94-1..9) · FE: [`06 §VIII.9`](./06_Frontend_Design.md) · nghiệp vụ: [`02 §IV.39`](./02_Analysis_Design.md) FR-00-CONN-05 / BR-00-CONN-42..49 · hợp đồng drill: [`05 §III.24.8`](./05_API_Specification.md).
> **File test**: `assetcore/tests/test_connections_tree.py` (**append 2 TC + sửa ĐÚNG 1 assert vacuous**, xem §XVIII.9.4) · `frontend/src/guards/connectionsApi.guard.test.ts` (**chỉ append**) · `frontend/src/views/pm/tests/PmScheduleListView.deepLink.test.ts` + `frontend/src/views/calibration/calibrationScheduleListDeepLink.test.ts` (**MỚI** — hoặc append vào 2 file drilldown có sẵn).
> **CẤM sửa**: `frontend/src/guards/connectionsListParity.guard.test.ts` (guard xanh **là** bằng chứng thăng hạng) · `assetcore/tests/test_connections.py` (11 TC hợp đồng cũ).
> **Quy ước số hiệu (tiếp theo §XVIII.8, không sinh hệ thứ ba)**: BE `TC-CONN-T-25/26` · FE render `TC-FE-CONN-31..36` · FE unit `TC-FE-CONN-44/45`.

#### XVIII.9.1 Fixture BE — **ràng buộc schema phải tôn trọng, nếu không cháy 1 vòng**

Thêm **một** asset riêng (`ConnTree Asset Sched`) vào `setUpClass` hiện có + purge trong `tearDownClass` (`purge_asset` đã phủ **cả hai** doctype lịch — `tests/_asset_cleanup.py:24-25`):

| Fixture | Ràng buộc **bắt buộc** (verify @source 2026-07-28) | Vi phạm thì |
|---|---|---|
| **3 `PM Schedule`** trên cùng asset: `Quarterly`+`Active` · `Semi-Annual`+`Active` · `Annual`+`Paused` | `autoname = format:PMS-{asset_ref}-{pm_type}` (`pm_schedule.json`) ⇒ **3 `pm_type` PHẢI khác nhau** | `DuplicateEntryError` — không thể có 2 lịch cùng loại trên 1 thiết bị |
| cả 3 dùng `checklist_template = cls.template` | `PMSchedule.validate` đòi `template.asset_category == asset.asset_category` (`pm_schedule.py:29-37`) | `frappe.throw` "Template … không khớp loại thiết bị" |
| `pm_interval_days = 3650`, **không** set `last_pm_date` | `before_save` ⇒ `next_due_date = today + 3650`; `on_update` chỉ tạo PM WO khi `next_due_date <= today + alert_days` (`pm_schedule.py:39-60`) | lịch `Active` **tự sinh PM Work Order** ⇒ ô `PM Work Order` lệch + fixture mồ côi |
| **2 `IMM Calibration Schedule`** trên cùng asset: `External`+`is_active=1` · `In-House`+`is_active=0`, `interval_days` reqd, `next_due_date` tương lai | không unique constraint (`autoname` series); controller chỉ điền `device_model` | — |

#### XVIII.9.2 Test BE — `count == drill` gọi **THẬT** cả hai đầu

| TC | Bất biến | Assert (đủ **cả hai** vế) |
|---|---|---|
| **TC-CONN-T-25** | **INV-CONN-18** | `total` ô `'PM Schedule'` == **3** == `len(imm00.list_pm_schedules(asset=X, page_size=50)['data']['items'])` ∧ **mọi** dòng `asset_ref == X` ∧ tập chứa **cả** lịch `Paused` (assert có ≥1 dòng `status == 'Paused'`) ∧ ô `count == ô total` |
| **TC-CONN-T-26** | **INV-CONN-19 + INV-CONN-20** | `total` ô `'IMM Calibration Schedule'` == **2** == `len(imm11.list_calibration_schedules(filters='{"asset":"X"}')['data']['data'])` ∧ mọi dòng `asset == X` ∧ tập chứa **cả** dòng `is_active == 0`; **và** `filters={"asset":X,"overdue":1}` trả tập **⊆** `filters={"asset":X}` (giao, không clobber) |

- Chạy dưới `Administrator` (khớp `setUpClass`) — 2 doctype này **không** có `permission_query_conditions` (`hooks.py:439-447`) nên bất biến **không** phụ thuộc row-scope; ca DocPerm/vendor là **backlog có tên** (ADR §15.8), **cấm** biến TC này thành TC an ninh.
- **Đọc envelope đúng tầng**: `list_pm_schedules` trả `{success, data:{items,total,…}}`; `list_calibration_schedules` trả `{success, data:{data,pagination}}` (2 shape KHÁC nhau — lấy sai tầng ⇒ `len()` của dict = số khoá = **xanh giả**).
- **RED-before bắt buộc**: TC-CONN-T-26 phải **ĐỎ** trên mã hiện tại (BE nuốt `asset` ⇒ drill trả mọi lịch của site) và **XANH** sau khi land nhánh vô hướng `_extract_asset_in_scope`. Nếu nó xanh **trước** khi sửa BE ⇒ fixture/tầng envelope sai, KHÔNG phải "BE đã đúng".

#### XVIII.9.3 Test FE

**Unit thuần (`api/connectionsApi.guard.test.ts` — append):**

| TC | Assert |
|---|---|
| TC-FE-CONN-44 | `listTarget({doctype:'PM Schedule', deep_link_filters:{asset_ref:'AC-ASSET-X'}})` == `{path:'/pm/schedules', query:{asset:'AC-ASSET-X'}}`; `{doctype:'IMM Calibration Schedule', deep_link_filters:{asset:'AC-ASSET-X'}}` == `{path:'/calibration/schedules', query:{asset:'AC-ASSET-X'}}` |
| TC-FE-CONN-45 | Phân hoạch: `|DOCTYPE_LIST_TARGET| == 11` ∧ `|LIST_TARGET_NO_FILTER| == 9` ∧ 2 doctype mới **không** còn trong `LIST_TARGET_NO_FILTER` ∧ hợp == `keys(DOCTYPE_ROUTE)` (20) ∧ giao == ∅ |

**Render 2 màn lịch (INV-CONNFE7-3..8):**

| TC | Màn | Assert |
|---|---|---|
| TC-FE-CONN-31 | `/pm/schedules?asset=X` | `listPmSchedules` được gọi **ngay lần đầu** kèm `asset:'X'` ∧ **không** có `status`/`pm_type` trong tham số (undefined) |
| TC-FE-CONN-32 | `/pm/schedules?asset=X` | DOM chứa chip `Thiết bị: <asset_name>` (dùng `asset_name` của dòng khớp; fixture 0 dòng ⇒ chip hiện **mã**) |
| TC-FE-CONN-33 | `/pm/schedules?asset=X` | Bỏ chip ⇒ `router.replace` được gọi với `query` **không** có `asset` ∧ lần gọi API kế tiếp **không** có `asset` |
| TC-FE-CONN-34 | `/calibration/schedules?asset=X` | `listCalibrationSchedules` nhận `filters` **có** `asset:'X'`; với `?asset=X&overdue=1` ⇒ `filters` có **cả** `asset` và `overdue:1`; tắt `overdue` ⇒ vẫn còn `asset` (và ngược lại) |
| TC-FE-CONN-35 | `/calibration/schedules?asset=X` | chip `Thiết bị: …` + bỏ chip ⇒ `router.replace` sạch `asset` + refetch **không** có khoá `asset`; `is_active` **không** bị tự thêm |
| TC-FE-CONN-36 | cả 2 màn | Đổi `route.query.asset` X → Y ⇒ gọi lại kèm **Y** (INV-CONNFE7-7) ∧ DOM **không** chứa `asset_ref` / tên DocType tiếng Anh (INV-CONNFE7-8) |

**Mutation-check khi land (guard sống, không phải template xanh):** (a) bỏ `asset` khỏi `buildFilters()` ⇒ TC-34/35 ĐỎ; (b) thêm `status:'Active'` mặc định ở PM ⇒ TC-31 ĐỎ; (c) bỏ `router.replace` khi bỏ chip ⇒ TC-33/35 ĐỎ; (d) trả 2 entry về `LIST_TARGET_NO_FILTER` ⇒ TC-45 + guard parity ĐỎ.

#### XVIII.9.4 Sửa **đúng 1** assert vacuous (breakage đã khai báo trước — QA KHÔNG chấm là nới guard)

`test_connections_tree.py:579-581` (trong `TC-CONN-T-20`):

- **Đang**: `empty.get("PM Work Order", {}).get("count", 0) == 0` + `.get("items", []) == []` ⇒ xanh **cả khi ô biến mất hoàn toàn** (mutation "xoá ô rỗng khỏi payload" sống sót).
- **Sau** (BR-00-CONN-49 · INV-CONN-22): `assertIn('PM Work Order', empty)` **trước**, rồi `total == 0` ∧ `type(truncated) is int and truncated == 0` (**không** `bool`) ∧ `label_vi` khác rỗng ∧ `label_vi != 'PM Work Order'`.
- **Vì sao hợp lệ**: assert cũ không khoá được mệnh đề nó tự nhận; sửa **test theo hợp đồng** (payload luôn liệt kê ô rỗng — D1/§III.24.3), không sửa hợp đồng theo test. Cùng khuôn tiền lệ §13.2 / §14.8.
- **24 TC còn lại của file: 0 assert được sửa.** `assertEqual(payload["total"], sum(count))` của TC-CONN-T-20 vẫn đúng sau khi thêm fixture (tổng cộng dồn tính theo **cùng** payload).

#### XVIII.9.5 DoD vòng AC-CR-94 (chấm ĐỎ nếu thiếu bất kỳ mục nào)

- **BE, module-isolated, `timeout` tool ≥ 600000ms** (kill giữa chừng ⇒ `tearDownClass` không chạy ⇒ fixture mồ côi ⇒ ĐỎ GIẢ):
  `bench --site miyano run-tests --app assetcore --module assetcore.tests.test_connections_tree` (25 → **27** OK) và `--module assetcore.tests.test_connections` (**11** OK, file **không** sửa).
- Nếu BE đã đụng `services/imm11.py` ⇒ chạy thêm `--module assetcore.tests.test_imm11` (no-regress cho 3 nhánh `overdue`/`due_soon`/`due_before` + vendor-scope).
- **FE**: `npx vitest run` 0 ĐỎ, delta **≥ +5 test** so với baseline **đọc từ đĩa** (đo 2026-07-28: **280 file / 2660 test**); `npx vue-tsc --noEmit` 0 lỗi; guard `connectionsListParity.guard.test.ts` xanh **không sửa**.
- **DoD chấm bằng test, KHÔNG curl** — `.py` prod vừa đổi mà gunicorn chạy `--preload` ⇒ mọi kết luận HTTP trước khi USER `bench restart` là **vô nghĩa** (LL-DEPLOY-07/08). Liệt kê file `.py` đã đụng trong bàn giao để USER reload.
- **3 counter guard: delta 0** — `_EXPECTED_TEST_COUNT` / `_GUARD_SUITE_SUM` / `_MOBILE_OAS_TOTAL` chỉ đếm 7 module guard mobile-OAS (`test_mobile_docset.py:499-809`); `test_connections_tree.py` **không** thuộc tập đó ⇒ **chạm vào là sai**.
- ⛔ **KHÔNG** `git commit/push` · **KHÔNG** `bench migrate` · **KHÔNG** `bench restart` · **KHÔNG** `npm run build`.

---


---

### XVIII.10 AC-CR-95 (FE + 1 file test BE): thăng hạng **4 màn đích** còn lại — `LIST_TARGET_NO_FILTER` 9 → **5** (INV-CONN-23..28 · INV-CONNFE8-1..10)

> Quyết định: [ADR §16](./ADR-IMM00-CONNECTIONS-TREE.md) (D-CR95-1..10) · FE: [`06 §VIII.10`](./06_Frontend_Design.md) · hợp đồng drill: [`05 §III.24.9`](./05_API_Specification.md) · nghiệp vụ: [`02 §IV.39`](./02_Analysis_Design.md) BR-00-CONN-50..58.
>
> **QA đọc TRƯỚC khi chấm — 4 đính chính của vòng này** (ADR §16.7): (1) `AC-CR-95` = **vòng này**, backlog nút-tạo-ô-rỗng đổi số thành `AC-CR-97`; (2) 3 counter guard **delta = 0**, đề mục ghi "tăng đúng số TC thêm" là **SAI**; (3) khoá ngoại lai của `Firmware Change Request` là **`{name:…}`** (internal-link), **không** phải `{asset_repair_wo:…}`; (4) baseline FE để chấm delta = **282 file / 2682 test** (đo từ đĩa 2026-07-28), không phải 280/2660 hay 278/2591.

#### XVIII.10.1 BE — **1 file test MỚI**, 0 file prod `.py` đổi

File: `assetcore/tests/test_connections_list_promotion.py` (**mới** — **cấm** append vào `test_connections_tree.py`/`test_connections.py`: cả hai đang uncommitted từ vòng trước và là shared-file của phiên song song).

> ⚠️ **DRIFT doc ↔ đĩa (verify 2026-07-30, `ls assetcore/tests/`): file `test_connections_list_promotion.py` KHÔNG TỒN TẠI.** TC-CONN-P-01..08 dưới đây **chưa bao giờ được viết** ⇒ vẫn là **nợ mở**, không phải "đã phủ". Phân hoạch lại từ 2026-07-30:
> - **TC-CONN-P-04 / P-05 / P-08 → HẤP THU** vào vòng `AC-CR-98`: chuyển thành `TC-IMM04-SCOPE-07/08` + `TC-IMM04-SCOPE-03..06`, đặt trong `assetcore/tests/test_rowscope_invariant.py`, chấm cho **3 persona** thay vì chỉ `Administrator`. Spec: [`../imm-04/07 §VIII`](../imm-04/07_Testing_QA.md) · SSoT: [`ADR-IMM00-LIST-SCOPE §10`](./ADR-IMM00-LIST-SCOPE.md).
> - **TC-CONN-P-01 / P-02 / P-03 / P-06 / P-07 → VẪN MỞ** (Firmware CR · Decommission · CAPA · deep-link keys · anti-drift schema). Giữ nguyên đặc tả dưới đây; vòng nào viết thì tạo file theo đúng tên trên.
> - Câu «test chạy dưới `Administrator` và INV-CONN-27 chưa được phủ» của **TC-CONN-P-08** đã **HẾT hiệu lực** — INV-CONN-27 nay là **enforce** ([`05 §III.24.9`](./05_API_Specification.md)). File mới (nếu viết) phải nêu rõ điều này thay vì lặp lại câu cũ.

| TC | Bất biến | Phát biểu chấm được |
|---|---|---|
| **TC-CONN-P-01** | INV-CONN-23 | Seed 1 `AC Asset` + ≥2 `Firmware Change Request` (`asset_ref`) + ≥1 FCR của thiết bị KHÁC ⇒ ô `'Firmware Change Request'`.`total` == `len(list_firmware_crs(asset=X).items)` ∧ **mọi** dòng `asset_ref == X` |
| **TC-CONN-P-02** | INV-CONN-24 | Tương tự cho `Asset Decommission` ⇄ `imm14.list_decommissions(filters={"asset":X})` (đọc `data.data`) |
| **TC-CONN-P-03** | INV-CONN-25 | `IMM CAPA Record` ⇄ `imm00.list_capas(asset=X)`; **phải** seed ≥1 CAPA `status='Closed'` và assert nó **có** trong cả hai tập (chứng minh drill không tự tiêm `not_closed`) |
| **TC-CONN-P-04** | INV-CONN-26 | `Asset Commissioning` ⇄ `imm04.list_commissioning({"final_asset":X})`: `cell.total == len(items) + #{docstatus==2}`; seed **cả** trạng thái docstatus 0 và 1 ⇒ công thức **không vacuous** |
| **TC-CONN-P-05** | INV-CONN-26 (vế predicate) | `list_commissioning` **có** tiêm `docstatus != 2` khi caller không truyền: gọi với `{"final_asset":X}` trên dữ liệu có 1 phiếu `docstatus=2` ⇒ phiếu đó **không** trong `items` |
| **TC-CONN-P-06** | INV-CONN-28 | 4 khoá ngoại lai đi qua `_safe_deep_link`: `deep_link_keys('Asset Commissioning') ⊇ {final_asset, vendor, master_item, name}` ∧ `deep_link_keys('IMM CAPA Record') ⊇ {asset, linked_incident, capa_record, name}` ∧ `deep_link_keys('Firmware Change Request') ⊇ {asset_ref, name}` — chứng minh nghĩa vụ chặn **thuộc FE** |
| **TC-CONN-P-07** | ADR §16.1 #10 (anti-drift schema) | 4 anchor mà `ac_asset_dashboard.get_data()` phát == `{FCR: asset_ref, Commissioning: final_asset, Decommission: asset, CAPA: asset}` ∧ **mỗi** anchor là `Link → AC Asset` trong `<slug>.json` ⇒ đổi tên field trong DocType ⇒ ĐỎ ở BE **trước khi** FE ra danh sách rỗng |
| **TC-CONN-P-08** | ADR §D-CR95-5 (khai session) | Docstring/comment của module **nói rõ** test chạy dưới `Administrator` và INV-CONN-27 (`Asset Commissioning` + Vendor Engineer) **chưa** được phủ ⇒ chấm bằng assert `"Administrator"` xuất hiện trong `setUpClass`/docstring **và** `AC-CR-98` được cite |

**Ràng buộc test BE:**
- `setUpClass` seed dữ liệu **riêng** với prefix nhận diện được; `tearDownClass` **phải** dọn (fixture mồ côi ⇒ suite ĐỎ GIẢ — xem `_asset_cleanup.py`).
- Chạy **cùng session** cho cả hai đầu (ô đếm + drill) — khác session là chứng minh khác thứ.
- **Cấm** mock: mock chứng minh bảng dịch khoá, không chứng minh hai endpoint cùng thấy một tập dòng (ADR §D-CR94-2).
- **Cấm** `dict.get(k, default)` trong assert "ô có mặt" (assert vacuous — D-CR94-8): `assertIn(<doctype>, cells)` **trước**, rồi so số.

#### XVIII.10.2 FE — 4 file test mount + append 2 test thuần

| TC | Bất biến | Nơi chấm |
|---|---|---|
| **TC-CONNFE8-01** | INV-CONNFE8-1 | `router/connectionsListParity.guard.test.ts` xanh **không sửa** + assert `|DOCTYPE_LIST_TARGET| == 15` ∧ `LIST_TARGET_NO_FILTER` == đúng 5 phần tử (tập liệt kê) |
| **TC-CONNFE8-02** | INV-CONNFE8-2 | `api/connectionsApi.guard.test.ts` — `listTarget` cho **cả 4** doctype mới với anchor đúng ⇒ `{path, query:{asset:X}}` |
| **TC-CONNFE8-03** | INV-CONNFE8-3 | `api/connectionsApi.guard.test.ts` — 4 payload **ngoại lai THẬT**: `{name:'FCR-…'}` · `{vendor:'SUP-…'}` · `{master_item:'MODEL-…'}` · `{linked_incident:'INC-…'}` ⇒ **`null`** |
| **TC-CONNFE8-04** | INV-CONNFE8-4/5/6 | 4 file mount (1/màn): mount với `route.query.asset='AC-ASSET-X'` ⇒ **lời gọi thứ nhất** của spy API/store đã mang khoá đúng (`final_asset` cho `/commissioning`; `asset` cho 3 màn) ∧ **không** mang khoá trạng thái nào của §VIII.10.5 |
| **TC-CONNFE8-05** | INV-CONNFE8-7 | DOM chứa `Thiết bị: <tên hoặc mã>` — assert **chuỗi tiếng Việt**, không assert riêng mã |
| **TC-CONNFE8-06** | INV-CONNFE8-8 | Bấm bỏ chip ⇒ `router.replace` được gọi **không** kèm `asset` ∧ lời gọi API kế tiếp **không** mang khoá asset |
| **TC-CONNFE8-07** | INV-CONNFE8-9 | Đổi `route.query.asset` X → Y (không remount) ⇒ nạp lại kèm **Y** |
| **TC-CONNFE8-08** | INV-CONNFE8-10 | `wrapper.html()` của 4 màn **không** chứa `final_asset` / `asset_ref` / `critical_asset` |

#### XVIII.10.3 Mutation check (bắt buộc — chứng minh guard SỐNG, không phải template xanh)

| Đột biến | Kỳ vọng |
|---|---|
| Xoá `route.query.asset` khỏi **bất kỳ** 1/4 view | **≥2** ĐỎ: (1) guard tĩnh `connectionsListParity.guard.test.ts:68-81` — doctype đã ở `DOCTYPE_LIST_TARGET` mà file view **không** chứa `route.query.asset`; (2) TC-CONNFE8-04 của màn đó (lời gọi đầu không mang khoá) |
| Đổi `sourceKeys` của `Asset Commissioning` → `['vendor']` | ĐỎ ở `connectionsListParity.guard.test.ts:83-103` (`vendor` là `Link → AC Supplier`, không phải `AC Asset`) |
| Đưa 1 doctype ngược từ `DOCTYPE_LIST_TARGET` về `LIST_TARGET_NO_FILTER` | ĐỎ ở `:109-118` (allowlist chỉ-giảm: view **đã** đọc `route.query.asset`) |
| Bỏ `docstatus != 2` khỏi `list_commissioning` | ĐỎ ở TC-CONN-P-05 |
| Đổi `ac_asset_dashboard` anchor `final_asset` → `asset` | ĐỎ ở TC-CONN-P-07 |

#### XVIII.10.4 DoD vòng AC-CR-95 (chấm ĐỎ nếu thiếu bất kỳ mục nào)

- **BE, module-isolated, `timeout` tool ≥ 600000ms** (kill giữa chừng ⇒ `tearDownClass` không chạy ⇒ fixture mồ côi ⇒ ĐỎ GIẢ):
  `bench --site miyano run-tests --app assetcore --module assetcore.tests.test_connections_list_promotion` (**8** OK) · `--module assetcore.tests.test_connections_tree` (**27** OK, file **không** sửa) · `--module assetcore.tests.test_connections` (**11** OK, file **không** sửa).
- **`git diff --name-only` phía BE: 0 file `.py` prod** — chỉ 1 file test mới. Có file prod `.py` trong diff ⇒ ra khỏi A-biên ⇒ ĐỎ.
- **FE**: `npx vitest run` 0 ĐỎ, delta **≥ +8 test** so với baseline **đọc từ đĩa** (**282 file / 2682 test**, đo 2026-07-28); `npx vue-tsc --noEmit` 0 lỗi; guard `connectionsListParity.guard.test.ts` xanh **không sửa**.
- **Mutation check §XVIII.10.3 chạy thật ít nhất 2 dòng đầu** và **revert** — báo cáo tên test đã ĐỎ (không chỉ nói "guard sống").
- **3 counter guard: delta 0** — `_EXPECTED_TEST_COUNT` (1024) / `_GUARD_SUITE_SUM` (1167) / `_MOBILE_OAS_TOTAL` (1193) chỉ đếm 7 module guard mobile-OAS; file test mới **không** thuộc tập đó ⇒ **chạm vào là sai**. Đọc lại 3 số **từ đĩa** trước khi kết luận.
- **KHÔNG phát sinh blocker `bench restart` mới**: vòng này 0 file `.py` prod ⇒ live-HTTP không đổi. Nợ restart của các vòng **trước** vẫn còn (thuộc USER) — QA **không** được gán lỗi live cũ cho vòng này.
- ⛔ **KHÔNG** `git commit/push` · **KHÔNG** `bench migrate` · **KHÔNG** `bench restart` · **KHÔNG** `npm run build`.

---

### XVIII.11 AC-CR-92 (BE+FE): ô **12 → 9 khoá**, `capped: bool` → `total_capped: int`, RATIFY cổng I/O (INV-CONN-29..34 · INV-CONNFE9-1..6)

> Quyết định: [ADR §17](./ADR-IMM00-CONNECTIONS-TREE.md) (D-CR92-1..9) · hợp đồng: [`05 §III.24.10`](./05_API_Specification.md) · BE: [`04 §V.9`](./04_Backend_Design.md) + [`04 §V.7.1` NGOẠI LỆ cổng I/O](./04_Backend_Design.md) · FE: [`06 §VIII.12`](./06_Frontend_Design.md) · nghiệp vụ: [`02 §IV.39`](./02_Analysis_Design.md) BR-00-CONN-59..66.
> **BREAKING** ⇒ BE + FE **cùng vòng**. Fixture: **dùng lại** `test_connections_tree.py` (asset 6 phiếu / 3 phiếu / 0 phiếu) — **0 fixture mới** (nhánh chạm trần tiêm `list_fn` giả).

#### XVIII.11.1 TC backend — `assetcore/tests/test_connections_tree.py`

| TC | Nội dung | Invariant | AC |
|---|---|---|---|
| **`t01`** (viết lại) | `set(item) == {doctype, label_vi, total, truncated, total_capped, items, deep_link_filters, can_create, create_route_hint}` — **so sánh TẬP** (`assertEqual`, **KHÔNG** `assertIn`), trên **mọi ô của MỌI hub đã seed**. Kèm kiểu: `type(truncated) is int` ∧ `type(total_capped) is int` ∧ `not isinstance(…, bool)` ∧ `∈ {0,1}`; `total: int`; `can_create: bool`; `create_route_hint: str`; `label_vi: str` | INV-CONN-29 | A1 |
| **`t21`** (viết lại) | Tiêm `list_fn` giả 3 mốc: **150 dòng** ⇒ `(total=100, total_capped=1)` · **CAP+1** ⇒ `(100, 1)` · **ĐÚNG CAP** ⇒ `(100, **0**)` — predicate `len(rows) > CAP`, **không** `>=`. Thêm vế `total_capped == 1 ⇒ truncated == 1` | INV-CONN-30 / 32 | A2 |
| **`t20`** (dời assert) | `payload["total"] == sum(it["total"] for it in items)`; ô RỖNG: `assertIn` **trước**, rồi `total == 0` ∧ `items == []` ∧ `truncated == 0` (int thuần) ∧ `total_capped == 0` (int thuần) ∧ `label_vi` khác `""` **và** khác `"PM Work Order"` | INV-CONN-31 · INV-CONN-22 | A3 |
| **`t27`** (MỚI) | AST `services/connections.py`: **0** lời gọi `frappe.get_list` · `frappe.get_all` · `frappe.db.get_all` · `frappe.db.get_list` · `frappe.db.count` · `frappe.db.sql`. Tên bắt buộc: `test_t27_service_layer_has_zero_row_reading_orm` | INV-CONN-33 | A4(a) |
| **`t28`** (MỚI) | AST `api/connections.py`: `frappe.get_list` xuất hiện **đúng 1 lần** ∧ nằm **trong thân `_row_scoped_rows`** (đi từ `ast.FunctionDef` tên đó rồi `ast.walk` bên trong — **không** đếm trên cả module). Tên bắt buộc: `test_t28_api_layer_has_exactly_one_get_list_inside_the_port` | INV-CONN-34 | A4(b) |
| **`t04`** (không đổi) | 1 lời gọi `list_fn`/ô ∧ **0** truy vấn COUNT xuống DB | INV-CONN-6 | A5 |
| **`t02`/`t03`/`t06`/`t15`/`t15b`/`t22`/`t23`/`t25`/`t26`** (dời khoá) | `item["count"]` → `item["total"]`; `item["filters"]` → `item["deep_link_filters"]`; xoá assert `item["label"] == frappe._(doctype)`. Nội dung nghiệp vụ **không đổi** | INV-CONN-2/6/16/17/18..28 | A5/A6 |

#### XVIII.11.2 TC backend — `assetcore/tests/test_connections.py` (hợp đồng cũ)

| Ràng buộc | Chi tiết |
|---|---|
| **Số TC** | GIỮ **ĐÚNG 11** `def test_` — 0 test bị xoá (A6) |
| **TC ĐÓNG BĂNG** | `test_counts_run_under_session_user_not_administrator` — **0 dòng sửa**. Nó vẫn xanh vì `frappe.get_list` **vẫn ở** `api/connections.py` (D-CR92-6). Nếu ai đó dời ORM xuống service, TC này ĐỎ **đúng thiết kế** (A4(c)) |
| `test_counts_reflect_declared_graph` | `count` → `total` (2 chỗ); `assertFalse(capped)` → `assertEqual(total_capped, 0)` |
| `test_counts_do_not_bleed_across_records` | `assertIn("Incident Report", items)` **trước** (chống vacuous), rồi `total == 0`; `Asset Lifecycle Event` `count` → `total` |
| `test_non_standard_fieldname_is_used_for_filters` | `filters` → `deep_link_filters` == `{"asset_ref": <mã>}` |
| `test_filters_let_frontend_drill` | `deep_link_filters` == `{"asset": <mã>}` **và** `frappe.get_all("Incident Report", filters=item["deep_link_filters"])` trả **đúng** `item["total"]` — bất biến `count == drill` phải chứng minh THẬT, không chỉ đổi tên khoá |
| `test_groups_carry_vietnamese_labels` | **KHÔNG đổi** — `g["label"]` là nhãn **NHÓM**, khoá được GIỮ (D-CR92-4) |

#### XVIII.11.3 TC frontend

| TC | Nội dung | Invariant | AC |
|---|---|---|---|
| **TC-CONNFE9-01** | `vue-tsc --noEmit` 0 lỗi với `ConnectionItem` đã siết (8 khoá bắt buộc + `doctype`; 4 legacy xoá; `create_prefill?` giữ) | INV-CONNFE9-1 | A7 |
| **TC-CONNFE9-02** | Guard tĩnh: 0 hit `/\.capped\b/` · `/\bitem\.count\b/` · `/\bitem\.filters\b/` · `/\bscalarFilters\b/` · `/\blinkFilters\b/` trong `frontend/src/**/*.{ts,vue}`; allowlist **duy nhất** `api/imm00.ts` (`totals_uncapped`) | INV-CONNFE9-2 | A10 |
| **TC-CONNFE9-03** | **MOUNT** `RelatedRecords` với ô `{total:100, total_capped:1, truncated:1, items:5}` ⇒ `[data-testid=conn-count]` === `'100+'` ∧ `[data-testid=conn-meta]` chứa `'Đang xem 5/100+'` ∧ **0** badge `'100'` trần ∧ **0** chuỗi `'95'`/`'còn 95'` | INV-CONNFE9-3 | A8 |
| **TC-CONNFE9-04** | **MOUNT** ô `{total:7, total_capped:0}` ⇒ badge `'7'` | INV-CONNFE9-4 | A8 |
| **TC-CONNFE9-05** | `countBadge` với `total_capped` **VẮNG MẶT** ⇒ `'7'` (không crash, không `'7+'`) | INV-CONNFE9-5 | A9 |
| **TC-CONNFE9-06** | Bỏ `truncated` khỏi ô 5/7 ⇒ dải cắt **MẤT** (chứng minh `previewMeta` không suy từ `items.length`) | INV-CONNFE9-6 | A7 |
| **TC-CONNFE9-07** | `listTarget` đọc **chỉ** `deep_link_filters` (`undefined` ⇒ `null`); 2 guard parity route xanh **không bị sửa** | INV-CONNFE5-1..4 | A7 |

#### XVIII.11.4 Mutation check — chạy THẬT rồi REVERT (không chỉ khai)

| Mutation | Phải ĐỎ ở |
|---|---|
| `total_capped = len(rows) > CAP` (bool) | `t01` (`type is int`) |
| `>=` thay `>` trong predicate | `t21` mốc "đúng CAP" |
| Bồi lại khoá `count` vào ô | `t01` (so sánh tập) |
| Dời `frappe.get_list` xuống service | `t27` **và** `t28` **và** `test_connections.py::test_counts_run_under_session_user_not_administrator` |
| `payload total` cộng dồn biến thứ hai lệch | `t20` |
| FE: `countBadge` đọc `item.total_capped` bằng truthiness trên chuỗi `'0'` | TC-CONNFE9-04 |

#### XVIII.11.5 DoD vòng AC-CR-92 (chấm ĐỎ nếu thiếu bất kỳ mục nào)

- **BE, module-isolated, `timeout` tool ≥ 600000ms** (kill giữa chừng ⇒ `tearDownClass` không chạy ⇒ fixture mồ côi ⇒ **ĐỎ GIẢ**): `bench --site miyano run-tests --app assetcore --module assetcore.tests.test_connections` **XANH** (đúng **11** TC) **và** `--module assetcore.tests.test_connections_tree` **XANH**.
- **FE**: `npx vue-tsc --noEmit` **0 lỗi** · `npm run test:unit` **0 ĐỎ**. **Đọc baseline TỪ ĐĨA trước khi chấm** (số **2591** trong đề mục là baseline cuối run-3, **đã stale** — ADR §13.9 ghi 2649 sau vòng 5, còn AC-CR-93/94/95 bồi thêm) ⇒ chấm **delta ≥ 0** so với số đo trên đĩa, **không** so với 2591.
- **3 counter guard: delta 0** — `_EXPECTED_TEST_COUNT` **1024** (`tests/test_mobile_oas.py:212`) · `_GUARD_SUITE_SUM` **1167** (`tests/test_mobile_docset.py:956`) · `_MOBILE_OAS_TOTAL` **1193** (`:1145`). Lý do đo được: `test_connections*.py` **không** thuộc `_GUARD_SUITE_EXPECTED` (0 hit `test_connections` trong `test_mobile_docset.py`) và `get_connections` có **0 hit** trong `docs/mobile/openapi/assetcore-mobile.openapi.yaml`. ⇒ QA **không** được chấm vòng này bằng counter, và **không ai** được "cập nhật" counter cho khớp.
- `git diff --name-only`: BE **4** file (`services/connections.py`, `api/connections.py` — chỉ docstring, 2 file test) · FE **9** file (`api/connections.ts` + 7 fixture test + 1 guard mới). File khác ⇒ ra khỏi biên ⇒ ĐỎ.
- **Blocker mới phải khai**: đụng `.py` prod ⇒ **1 blocker `bench restart`** (USER, `gunicorn --preload`). QA **KHÔNG** chấm bằng curl/HTTP (LL-DEPLOY-07/08).
- **A-biên "không làm" là PASS**: **KHÔNG** thêm `create_prefill` (nợ `AC-CR-90(b)`, ADR §17.8) · **KHÔNG** sửa `connection_meta.py` / `*_dashboard.py` / 5 màn Detail / `RelatedRecords.vue` / 2 guard parity route / OAS.
- ⛔ **KHÔNG** `git commit/push/merge` · **KHÔNG** `bench migrate` / `bench restart` · **KHÔNG** `npm run build` · **KHÔNG** reset DB.

---

## XIX. AC-CR-100 — tab «Lịch sử»: TỔNG THẬT của server + phân trang «Tải thêm» + 3 trạng thái tách rời (INV-TL-1..11)

> **CR**: `AC-CR-100` (đề mục PM gọi «AC-CR-96» — số đã bị chiếm; bảng đối chiếu [ADR §8.0](./ADR-IMM00-TRUNCATION-SSOT.md)). Quyết định: **ADR-IMM00-TRUNCATION-SSOT §8**. FR-00-TL-01 / BR-00-TL-01..09: [02 §IV.40](./02_Analysis_Design.md). API: [05 §III.25](./05_API_Specification.md). FE: [06 §VIII.11](./06_Frontend_Design.md).
>
> **Biên test**: **1 file FE mới** `frontend/src/views/asset/assetDetailTimelinePagination.test.ts` + **1 class BE mới** trong `assetcore/tests/test_imm00.py`. **KHÔNG** sửa guard cũ (`relatedRecordsTabParity.guard.test.ts`, `assetDetail*.test.ts`, `test_mobile_oas`, `test_mobile_docset`). 3 counter guard mobile: **delta 0**.

### XIX.1 Fixture tối thiểu (BE)

- 1 `AC Asset` seed qua khuôn `_purge_asset` sẵn có (`tests/_asset_cleanup.py`) — **bắt buộc** teardown, nếu không ⇒ rác fixture (LL-TEST).
- **≥3** `Asset Lifecycle Event` cho asset đó, trong đó **≥2 event CÙNG `timestamp`** (ép đúng ca mà `ORDER BY` thiếu tiebreaker sẽ vỡ — nếu mọi timestamp khác nhau thì test **xanh giả**).
- Chạy dưới **session user không phải Administrator** ở TC-TL-B4 (bẫy xanh-giả số 1 của §XVI).

### XIX.2 TC backend (BE Bước-4) — guard chống regress "total = len(items)" + phân trang lặp/sót

| TC | Kịch bản | Kỳ vọng | Invariant |
|---|---|---|---|
| TC-TL-B1 | `get_asset_timeline(name, page=1, page_size=2)` trên asset ≥3 ALE | `success` ∧ `len(items) == 2` ∧ `pagination.page_size == 2` | INV-TL-9 |
| TC-TL-B2 | cùng ca trên | `pagination.total == frappe.db.count("Asset Lifecycle Event", {"asset": name})` ∧ `total >= 3` ∧ `total > len(items)` | INV-TL-9 |
| TC-TL-B3 | cùng ca trên | `pagination.total_pages == math.ceil(total / 2)` ∧ `pagination.offset == 0` | INV-TL-9 |
| TC-TL-B4 | gọi `page=1` rồi `page=2` (`page_size=2`) | `set(names(page1)) ∩ set(names(page2)) == ∅` ∧ union ⊆ tập name thật ∧ `len(union) == 4` (khi total ≥4) | INV-TL-9 + BR-00-TL-08 |
| TC-TL-B5 | **RED-first**: đọc hằng `_ORDER_EVENT_TS_DESC` từ `assetcore.api.imm00` | chuỗi **chứa** dấu `,` và kết thúc bằng tiebreaker (`name desc` hoặc `creation desc`) — assert trên **hằng THẬT** (import, KHÔNG grep chuỗi trong file) | BR-00-TL-08 / D-TL-2 |
| TC-TL-B6 | `frappe.get_hooks("permission_query_conditions")` | **KHÔNG** chứa khoá `"Asset Lifecycle Event"`; message lỗi nêu rõ: *thêm PQC cho ALE thì `total` phải đổi sang engine permission-aware (`frappe.get_list`) chứ không được giữ `frappe.db.count`* | **INV-TL-10** (D6/INV-ROWSCOPE) |
| TC-TL-B7 | asset ∄ (`name='AC-ASSET-KHONG-TON-TAI'`) | **HTTP-200** + `success == False` ∧ `code == 404` (in-handler envelope, KHÔNG raise) | hợp đồng lỗi (05 §III.25.1) |
| TC-TL-B8 | asset tồn tại, **0** ALE | `success` ∧ `items == []` ∧ `pagination.total == 0` ∧ `total_pages == 0` (KHÔNG 404) | phân biệt rỗng-thật vs 404 |
| TC-TL-B9 | `page_size=100000` | `pagination.page_size == 100` ∧ `len(items) <= 100` (parity TC-00-PS-02, **không** hồi quy) | BR-00-39 / INV-TRUNC-LIMIT |

**⚠️ Bẫy xanh-giả:** TC-TL-B4 **vô nghĩa** nếu fixture không có ALE trùng `timestamp` (thứ tự vô tình ổn định). Fixture §XIX.1 là **điều kiện chấm**, không phải gợi ý.

### XIX.3 TC frontend (FE Bước-4) — test **mount**, không grep

Khuôn: `frontend/src/views/asset/tests/AssetDetailView.transitionAuthz.test.ts` (mock store/router/capabilities). `getAssetTimeline` là `vi.fn()` **đếm được** + **kiểm tham số**.

| TC | Kịch bản (mock) | Kỳ vọng | Acceptance |
|---|---|---|---|
| TC-TL-F1 | mount, `activeTab = 'info'` | `getAssetTimeline` gọi **0** lần; `getConnections` **0** lần | A6 / INV-TL-11 |
| TC-TL-F2 | mở tab `timeline`; trả `{pagination:{total:137,page:1,page_size:100,total_pages:2,offset:0}, items: 100 dòng}` | `getAssetTimeline` gọi **đúng 1** lần với `(id, 1, 100)`; text `timeline-total` == `137 sự kiện`; `timeline-viewing` == `Đang xem 100/137`; **100** dòng render | A2 / INV-TL-2/4 |
| TC-TL-F3 | cùng ca F2 | `timeline-load-more` **tồn tại** | A3 / INV-TL-3 |
| TC-TL-F4 | `total = 7`, trang 1 trả 7 dòng | `timeline-total` == `7 sự kiện`; **KHÔNG** có `timeline-viewing`; **KHÔNG** có `timeline-load-more` | A3 / INV-TL-3/4 |
| TC-TL-F5 | từ F2, click `timeline-load-more`; trang 2 trả 37 dòng | lời gọi thứ 2 = `(id, 2, 100)` — `page_size` **GIỮ 100**; **137** dòng render (APPEND, không thay thế); nút biến mất; `timeline-viewing` tắt | A4 / INV-TL-3/6 |
| TC-TL-F6 | trang 2 trả **42** dòng trong đó **5 dòng trùng `name`** với trang 1 | số dòng render == **137** ∧ **0** `name` trùng ∧ nút ẩn ∧ `timeline-viewing` tắt ∧ **không** có `timeline-error`; **không** crash `:key` | A4 / D-TL-5 |
| TC-TL-F15 | trang 2 trả **37** dòng trong đó 5 trùng ⇒ render **132 < 137** (trang cuối ngắn mà vẫn thiếu) | nút **ẩn** ∧ `timeline-viewing` == `Đang xem 132/137` ∧ `timeline-error` text chứa `đã thay đổi trong lúc tải` ∧ `timeline-retry` gọi `(id, 1, 100)` — **cấm** trạng thái "thiếu mà không có đường lấy" | **INV-TL-8** / D-TL-8 |
| TC-TL-F7 | mở tab `timeline`, `getAssetTimeline` **reject** | `timeline-error` hiện, text chứa `Không tải được dòng thời gian`; **KHÔNG** có `timeline-empty`; `notify.fromError` gọi 1 lần | A5 / INV-TL-7 |
| TC-TL-F8 | `total = 0`, `items = []` | `timeline-empty` hiện (chuỗi cũ `Chưa có sự kiện vòng đời`); **KHÔNG** có `timeline-error`; **KHÔNG** có `timeline-total` | A5 / INV-TL-7 |
| TC-TL-F9 | từ F2, click «Tải thêm» → trang 2 **reject** | 100 dòng **GIỮ NGUYÊN** (không mất); `timeline-error` hiện; click `timeline-retry` ⇒ gọi lại **đúng** `(id, 2, 100)` | D-TL-7 / INV-TL-8 |
| TC-TL-F10 | từ F2, click «Tải thêm» → trang 2 trả **0 dòng mới** (danh sách đổi) | nút **ẩn**; `timeline-error` text chứa `đã thay đổi trong lúc tải`; `timeline-retry` gọi `(id, 1, 100)` (reset) | D-TL-8 / INV-TL-8 |
| TC-TL-F11 | mock `pagination.total = 3` trong khi đã render 5 dòng | `timeline-total` == `5 sự kiện` (không bao giờ `M > N`) | INV-TL-5 / D-TL-6 |
| TC-TL-F12 | asset 0 event: mở tab `timeline` → sang tab `info` → mở lại `timeline` | `getAssetTimeline` **đúng 1** lần (không nạp lại vì `timelinePage > 0`) | D-TL-3 / A6 |
| TC-TL-F13 | lỗi trang 1 → sang `info` → mở lại `timeline` | có nạp lại (`timelinePage` vẫn 0) ⇒ 2 lần gọi | D-TL-3/7 |
| TC-TL-F14 | trong lúc `timelineLoading` true, click «Tải thêm» 3 lần | tổng lời gọi thêm **≤ 1** (chống double-fetch) | D-TL-8 (idempotent) |

**Mutation check (chứng minh guard SỐNG — chạy thật ≥2, rồi revert):**
1. Đổi `timelineTotal` thành `timeline.value.length` ⇒ **TC-TL-F2/F4/F11 ĐỎ**.
2. Đổi điều kiện `timeline-empty` về `!timeline.length` ⇒ **TC-TL-F7 ĐỎ**.
3. Đổi `TIMELINE_PAGE_SIZE` thành `200` ⇒ **TC-TL-F5 ĐỎ**.
4. Xoá `_ORDER_EVENT_TS_DESC` tiebreaker ⇒ **TC-TL-B5 ĐỎ**.

### XIX.4 DoD vòng AC-CR-100 (chấm ĐỎ nếu thiếu bất kỳ mục nào)

- **BE, module-isolated, `timeout` tool ≥ 600000ms** (kill giữa chừng ⇒ `tearDownClass` không chạy ⇒ fixture mồ côi ⇒ **ĐỎ GIẢ**): `bench --site miyano run-tests --app assetcore --module assetcore.tests.test_imm00` **XANH** (baseline + class `TestAssetTimelinePaginationContract` mới, TC-TL-B1..B9).
- **FE**: `npx vitest run` 0 ĐỎ + `npx vue-tsc --noEmit` 0 lỗi. **Đọc baseline TỪ ĐĨA trước khi chấm** (đo lúc chốt spec 2026-07-28: **283 file** `*.test.ts`; các số 2591/2682 trong đề mục & STATE **đều có thể stale**) ⇒ chấm theo **delta ≥ +10 test** (bộ TC có **15** ca ⇒ ≥15 nếu viết 1 `it` mỗi TC).
- **3 counter guard: delta 0** — `_EXPECTED_TEST_COUNT` (**1024**, `tests/test_mobile_oas.py:212`) · `_GUARD_SUITE_SUM` (**1167**, `tests/test_mobile_docset.py:956`) · `_MOBILE_OAS_TOTAL` (**1193**, `:1145`). Đọc lại **từ đĩa** trước khi kết luận; **chạm vào là sai** (vòng này 0 OAS delta, file test mới không thuộc 7 module guard mobile).
- `git diff --name-only`: phía BE **đúng 2** file (`assetcore/api/imm00.py` — **chỉ 1 dòng hằng**, `assetcore/tests/test_imm00.py`); phía FE **đúng 2** file (`AssetDetailView.vue`, test mới). File khác trong diff ⇒ ra khỏi biên ⇒ **ĐỎ**.
- **Blocker mới phải khai**: vòng này **đụng `.py` prod** ⇒ **1 blocker `bench restart`** (thuộc USER, `gunicorn --preload`). QA **KHÔNG** chấm bằng curl/HTTP (LL-DEPLOY-07/08) và **KHÔNG** gán nợ restart của vòng trước cho vòng này.
- **A9 (out-of-scope, đo được)**: **0** file ngoài 4 file trên bị sửa; **KHÔNG** render 3 nhánh lịch sử PM/CM/Sự cố lên màn Chi tiết tài sản (nợ có tên `AC-CR-102`, ADR §8.7) — QA chấm việc **không làm** là **PASS**. ⚠️ **HẾT HIỆU LỰC từ `AC-CR-102` (2026-07-30)**: A9 chỉ áp cho **vòng `AC-CR-100`**. Từ `AC-CR-102`, 3 nhánh **PHẢI** render trong tab «Bản ghi liên quan» — QA chấm theo **`§XX` (INV-OPH-1..18)** + [`ADR-IMM00-ASSET-OP-HISTORY §2`](./ADR-IMM00-ASSET-OP-HISTORY.md); **đừng** dùng A9 để chấm vòng sau FAIL.
- ⛔ **KHÔNG** `git commit/push/merge` · **KHÔNG** `bench migrate` · **KHÔNG** `bench restart` · **KHÔNG** `npm run build` · **KHÔNG** reset DB.

---

## XX. AC-CR-102 — hồ sơ **VẬN HÀNH** của thiết bị render THẬT trong tab «Bản ghi liên quan» (INV-OPH-1..18)

> Spec: [`ADR-IMM00-ASSET-OP-HISTORY`](./ADR-IMM00-ASSET-OP-HISTORY.md) · FR-00-OPH-01 / BR-00-OPH-01..18 ([`02 §IV.41`](./02_Analysis_Design.md)) · hợp đồng ĐỌC [`05 §III.26`](./05_API_Specification.md) · FE [`06 §VIII.13`](./06_Frontend_Design.md).
>
> ⚠️ **Đọc trước khi chấm**: `§XIX A9` («KHÔNG render 3 nhánh …») chỉ áp cho vòng `AC-CR-100` và **đã hết hiệu lực**. Từ vòng này, **không render = FAIL**.

### XX.1 Invariants

| ID | Bất biến | Cách chấm |
|---|---|---|
| **INV-OPH-1** | Mount `AssetDetailView` → click `[data-testid=tab-related]` ⇒ **đúng 1** `[asset-op-history]` chứa **đúng 3** `[op-history-section]`, `data-branch` = `pm,cm,incident` **theo thứ tự**; ~~`[op-history-title]`~~ → **`.text()` của `[op-history-toggle]`** của 3 section chứa «Kết quả bảo trì» / «Lần sửa chữa đã hoàn thành» / «Sự cố đã ghi nhận». *(⚠️ **CẢI CHÍNH 2026-07-30 / `AC-CR-115`**: testid `op-history-title` **không tồn tại trên đĩa** — chuỗi tiêu đề nằm trong `op-history-toggle` `AssetOperationalHistory.vue:327`. Test hiện có đã chấm đúng cách này (`AssetOperationalHistory.test.ts:146`); doc là chỗ sai, không phải mã.)* | vitest render |
| **INV-OPH-2** | **0 chi phí mở máy**: sau khi vào tab, mỗi mock `getAssetPMHistory`/`getAssetRepairHistory`/`getAssetIncidentHistory` có `toHaveBeenCalledTimes(0)` ∧ `[op-history-row]` = **0**. Bung section *i* ⇒ mock *i* = **1**, hai mock kia = **0**. | vitest + `vi.fn()` |
| **INV-OPH-3** | **Cache**: bung → thu → bung lại ⇒ mock **vẫn 1**. | vitest |
| **INV-OPH-4** | **Cache khoá theo thiết bị**: đổi prop `assetName` A→B rồi bung ⇒ mock gọi **lại** (2 lần, tham số lần 2 = B) ∧ **không** còn dòng của A trong DOM. | vitest |
| **INV-OPH-5** | **Thanh tab GIỮ 6 tab**: tập `data-testid` khớp `tab-info/depreciation/timeline/kpi/audit/related`, **không** có tab thứ 7; `tabLabelParity` xanh. | vitest |
| **INV-OPH-6** | **0 link chết**: mọi `[op-history-row-link]` có `href` **∈** ảnh của `detailRouteForDoctype` (`/pm/work-orders/<wo>` · `/cm/work-orders/<name>` · `/incidents/<name>`); PM `row.pm_work_order` rỗng/null ⇒ **0 `<a>`** trong dòng đó ∧ `wrapper.html()` **không chứa** `/pm/work-orders/undefined` **và không chứa** `/pm/work-orders/"` (path trần). | vitest |
| **INV-OPH-7** | Đích PM dựng từ **`pm_work_order`**, **không** từ `name`: fixture `{name:'PMTL-9', pm_work_order:'WO-PM-1'}` ⇒ `href === '/pm/work-orders/WO-PM-1'` ∧ **không** chứa `PMTL-9`. | vitest |
| **INV-OPH-8** | «Xem tất cả»: **đúng 1** `[op-history-see-all]` / section, `href` == `/pm/work-orders?asset=<TS>` · `/cm/work-orders?asset=<TS>` · `/incidents/list?asset=<TS>`. ~~và **bằng** `listRouteForAsset(<doctype>, <TS>)`~~ *(⚠️ **CẢI CHÍNH 2026-07-30 / `AC-CR-115`**: `listRouteForAsset` **chưa bao giờ được cài** — `grep -rn 'listRouteForAsset' frontend/src` ⇒ **0 hit**; trên đĩa là hàm cục bộ `seeAllHref` (`AssetOperationalHistory.vue:278-282`) đọc `DOCTYPE_LIST_TARGET` trực tiếp và **bỏ** guard `LIST_TARGET_ANCHOR`. Mệnh đề "bằng helper" treo thành nợ **`AC-CR-116`** [P2 — fe]; phần còn lại của INV-OPH-8 **vẫn chấm bình thường**.)* | vitest |
| **INV-OPH-9** | **Parity route SSoT**: 3 doctype dùng ở khối đều **∈** `DOCTYPE_LIST_TARGET` ∧ `spec.queryKey === 'asset'` ∧ `LIST_TARGET_ANCHOR['asset'] === 'AC Asset'` ∧ `spec.path` phân giải được bằng `router.resolve()` (không 404) ∧ 3 doctype **∈** `DOCTYPE_DETAIL_ROUTE`. Đổi bảng mà quên khối ⇒ **ĐỎ**. | vitest (`assetOpHistoryRouteParity.test.ts`) |
| **INV-OPH-10** | **0 URL literal**: đọc file `AssetOperationalHistory.vue` bằng `fs.readFileSync` trong test ⇒ **0 match** `/pm/work-orders`, `/cm/work-orders`, `/incidents` (cấm bản đồ route thứ hai, D-CR5-1). | vitest static-read |
| **INV-OPH-11** | **Đếm trung thực**: fixture `rows=10, total=34` ⇒ ~~`[op-history-heading]`~~ → **`[op-history-count]`** (badge trong `[op-history-toggle]`) `.text()` == **`'34'`** ∧ **không** chứa `10`. *(⚠️ **CẢI CHÍNH 2026-07-30 / `AC-CR-115`**: testid thật là `op-history-count` (`AssetOperationalHistory.vue:332`) và chuỗi là **số trần**, không phải «{total} bản ghi». Từ `AC-CR-115` badge in **`totalDisplay = max(total, rows.length)`** — cùng một số với dải cắt.)* | vitest |
| **INV-OPH-12** | **3 trạng thái tách**: (a) `total===0` ⇒ có `[op-history-empty]` ∧ **0** `[op-history-see-all]` ∧ 0 `[op-history-row]`; (b) API reject ⇒ có `[op-history-error]` + `[op-history-retry]` ∧ **KHÔNG** có `[op-history-empty]`; (c) chưa bung ⇒ **không** có cả hai; (d) bấm «Thử lại» sau lỗi ⇒ mock gọi **lần 2** (guard cache không chặn retry). | vitest |
| **INV-OPH-13** | **Không lặp ô connections (6 dấu hiệu)**: DOM render chứa (1) nhãn kết quả VI (`Đạt`/`Không đạt`), (2) «Trễ {N} ngày», (3) «Thời gian khắc phục», (4) «Vượt cam kết thời gian», (5) nhãn mức độ VI (`Nghiêm trọng`…), (6) «Mã lỗi:». **Đủ 6** mới PASS. | vitest |
| **INV-OPH-14** | **Chữ VI**: `wrapper.text()` **0 match** `/\b(Pass|Fail|Preventive|Critical|High|Warranty Repair|MTTR|SLA)\b/` với fixture phủ **mọi** giá trị enum của 3 field (`overall_result` 3 giá trị · `repair_type` 3 · `severity` 4) ∧ mọi giá trị enum có khoá VI trong map tương ứng (`OVERALL_RESULT_LABEL`/`REPAIR_TYPE_LABEL`/`INCIDENT_SEVERITY_LABEL`) ⇒ **0 fallback EN**. | vitest |
| **INV-OPH-15** | **Kiểu không dối**: `npx vue-tsc --noEmit` 0 lỗi; `grep -n 'history: PMWorkOrder\[\]' frontend/src/api/imm08.ts` ⇒ **0 hit**; `PMTaskLogHistoryItem` có **đúng 10** khoá khớp `fields` @`services/imm08.py:1747-1749`. | vue-tsc + BE guard (dưới) |
| **INV-OPH-16** | **Sự cố: 2 số BẰNG NHAU** — cùng asset, `get_asset_incident_history(asset).total == frappe.db.count('Incident Report', {'asset': asset})` (cả hai "mọi docstatus"). | BE `run-tests` |
| **INV-OPH-17** | **CM: section ⊆ ô** — `get_asset_repair_history(asset).total == frappe.db.count('Asset Repair', {'asset_ref': asset, 'docstatus': 1})` ∧ `≤ frappe.db.count('Asset Repair', {'asset_ref': asset})`. Chứng minh tiêu đề «đã hoàn thành» nói đúng tập. | BE `run-tests` |
| **INV-OPH-18** | **0 delta BE**: `git diff --stat -- 'assetcore/api/*.py' 'assetcore/services/**/*.py'` **không tăng path** so với đầu vòng; OAS `docs/mobile/openapi/*.yaml` không đổi; 3 counter (1024/1167/1193) **delta 0** — đọc lại **từ đĩa**. | shell |

### XX.2 Test matrix

**FE — `frontend/src/components/asset/tests/AssetOperationalHistory.test.ts`** (TC-OPH-F1..F14)

| TC | Nội dung | INV |
|---|---|---|
| F1 | Vào tab ⇒ 1 khối · 3 section · đúng 3 tiêu đề VI · đúng thứ tự | 1 |
| F2 | Vào tab ⇒ 0 dòng ∧ 3 mock đều 0 lần | 2 |
| F3 | Bung `pm` ⇒ mock pm = 1, cm = 0, incident = 0 (và đối xứng cho `cm`, `incident`) | 2 |
| F4 | Thu → bung lại ⇒ mock vẫn 1 | 3 |
| F5 | Đổi `assetName` ⇒ refetch + 0 dòng cũ | 4 |
| F6 | Thanh tab vẫn 6 tab (không tab thứ 7) | 5 |
| F7 | 3 dòng → 3 `href` đúng khuôn `detailRouteForDoctype` | 6,7 |
| F8 | PM `pm_work_order` `''`/`null` ⇒ 0 `<a>` + `op-history-row-static` + 0 `undefined` trong html | 6 |
| F9 | 1 `see-all`/section, href đúng 3 đích, `total>0` | 8 |
| F10 | `rows=10 / total=34` ⇒ heading chứa `34`, không chứa `10 bản ghi` | 11 |
| F11 | `total=0` ⇒ `empty` ∧ 0 `see-all` | 12 |
| F12 | API reject ⇒ `error` + `retry` ∧ **không** `empty`; bấm retry ⇒ mock lần 2 | 12 |
| F13 | Đủ **6 dấu hiệu** không-lặp-ô | 13 |
| F14 | Fixture phủ mọi enum ⇒ 0 chuỗi EN thô (`Pass/Fail/Preventive/Critical/High/Warranty Repair/MTTR/SLA`) | 14 |

**FE — `frontend/src/router/assetOpHistoryRouteParity.test.ts`** (TC-OPH-R1..R4)

| TC | Nội dung | INV |
|---|---|---|
| R1 | 3 doctype ∈ `DOCTYPE_LIST_TARGET`, `queryKey==='asset'`, anchor `AC Asset`, `path` resolve được | 9 |
| R2 | 3 doctype ∈ `DOCTYPE_DETAIL_ROUTE`; `'PM Task Log'` **∉** cả 2 bảng (nếu ai đó thêm ⇒ ĐỎ để buộc xem lại D-OPH-7) | 9 |
| R3 | `listRouteForAsset` trả `null` khi doctype ngoài bảng / `assetName` rỗng / `queryKey` không neo `AC Asset`; `encodeURIComponent` áp cho mã có ký tự đặc biệt | 8,9 |
| R4 | Static-read file component ⇒ 0 URL literal | 10 |

**BE — `assetcore/tests/test_asset_operational_history_contract.py`** (TC-OPH-B1..B6, **chỉ đọc, 0 dòng prod đổi**)

| TC | Nội dung | INV |
|---|---|---|
| B1 | `fields` thật của 3 service == bảng `05 §III.26.3` (introspect `inspect.getsource` hoặc gọi endpoint trên fixture rồi so **tập khoá** của 1 dòng) | 15 |
| B2 | Rows-key: imm08/imm09 trả `history` + `asset_ref`; imm12 trả **`items`** + **`asset`** (chống ai đó "đồng bộ" khoá làm FE rỗng câm) | — |
| B3 | `limit=0` ⇒ **10 dòng tối đa** (không phải toàn bộ) ∧ `limit=500` ⇒ **≤100** cho **cả 3** endpoint (parity `clamp_page_size`) | — |
| B4 | `total` là COUNT **trước** khi cắt: seed 12 bản ghi, `limit=10` ⇒ `len(rows)==10 ∧ total==12 ∧ truncated==1`; seed 10, `limit=10` ⇒ `truncated==0` (không báo cắt oan) | 11 |
| B5 | `INV-OPH-16` sự cố: `total == db.count(asset)` | 16 |
| B6 | `INV-OPH-17` CM: `total == db.count(docstatus=1) ≤ db.count(all)` | 17 |

> Fixture BE **phải** dọn trong `tearDownClass` + tên có **uuid-suffix** (LL-TEST: fixture tên cố định tự chặn chính nó sau crash — xem STATE §DATA-PURGE).

### XX.3 DoD vòng AC-CR-102 (QA chấm — đọc baseline TỪ ĐĨA)

- **BE, module-isolated, `timeout` tool ≥ 600000ms**: `bench --site miyano run-tests --app assetcore --module assetcore.tests.test_asset_operational_history_contract` **XANH**. (Không bắt buộc chạy full suite; nếu chạy, ĐỎ do nhiễm fixture phiên khác **không** tính cho vòng này — LL-TEST-30.)
- **FE**: `npx vitest run` **0 ĐỎ** + `npx vue-tsc --noEmit` **0 lỗi**; số file `*.test.ts` **284 → ≥286** (đo lúc chốt spec 2026-07-30 = **284**) ⇒ chấm **delta**.
- **3 counter guard delta 0**: `_EXPECTED_TEST_COUNT` **1024** (`tests/test_mobile_oas.py:212`) · `_GUARD_SUITE_SUM` **1167** (`tests/test_mobile_docset.py:956`) · `_MOBILE_OAS_TOTAL` **1193** (`:1145`).
- **`git diff --name-only`**: phía FE **đúng 8** file sản phẩm + **2** test mới; phía BE **đúng 1** file (`assetcore/tests/…`, thêm mới). Ngoại lệ duy nhất được phép: `stores/assetHistoryTruncation.test.ts` (guard cache) — phải khai.
- **`git diff --stat -- 'assetcore/api/*.py' 'assetcore/services/**/*.py'` không tăng path** ⇒ **0 blocker reload mới**. QA **KHÔNG** chấm bằng curl (LL-DEPLOY-07/08) và **KHÔNG** gán nợ `bench restart` của vòng trước cho vòng này.
- **Ngoài biên — chấm việc KHÔNG làm là PASS**: ~~dải «Đang xem {M}/{N} — còn {N−M} chưa hiển thị» + «Tải thêm» cho 3 section = **VÒNG 5** (khuôn `AC-CR-96`)~~ ⚠️ **HẾT HIỆU LỰC từ `AC-CR-115` (2026-07-30)**: dải **PHẢI** render (chấm theo **§XXII**); «Tải thêm» thì **LOẠI VĨNH VIỄN** (3 endpoint không có `offset` ⇒ nút chết, `D-OPH-19`) ⇒ **không** dựng «Tải thêm» vẫn là **PASS**, còn **không** dựng dải là **FAIL**. Các mục sau **vẫn ngoài biên**: hợp nhất 2 map `REPAIR_TYPE_LABEL(S)` = `AC-CR-103`; «lịch sử cùng thiết bị» trên màn chi tiết PM/CM/Sự cố = `AC-CR-104`; loại `docstatus==2` khỏi ô đếm = `AC-CR-99`.
- ⛔ **KHÔNG** `git commit/push/merge` · **KHÔNG** `bench migrate` · **KHÔNG** `bench restart` · **KHÔNG** `npm run build` · **KHÔNG** reset DB.

---

## XXI. AC-CR-105 — «Tạo từ ngữ cảnh cha» hết là nút chết: `create_prefill` LIVE + token `CREATE_CAPABILITY` + chip cho ô 0 bản ghi (INV-CONN105-1..4 · INV-CONN4-1/2/3/7/10)

> Quyết định: [ADR §18](./ADR-IMM00-CONNECTIONS-TREE.md) (D-CR105-1..9) · hợp đồng API: [`05 §III.24.11`](./05_API_Specification.md) · code shape BE: [`04 §V.10`](./04_Backend_Design.md) · FE: [`06 §VIII.14`](./06_Frontend_Design.md) · nghiệp vụ: [`02 §IV.42`](./02_Analysis_Design.md) FR-00-CONN-06 / BR-00-CONN-67..76.
> **File test**: `assetcore/tests/test_connections_tree.py` (**append 6 TC** `t29..t34` + **2** TC hiện có sửa **đã khai trước**) · `frontend/src/components/common/tests/RelatedRecords.test.ts` (**append** + **2 dòng** breakage `:772-773`) · `frontend/src/guards/connectionsApi.guard.test.ts` (**chỉ append**) · `frontend/src/guards/connectionsLegacyKeys.guard.test.ts` (**9→10** + tập optional **rỗng**).
> **CẤM sửa**: `assetcore/tests/test_connections.py` (11 TC hợp đồng cũ) · `frontend/src/guards/connectionsListParity.guard.test.ts` · `frontend/src/guards/connectionsCreateParity.guard.test.ts` · `TC-FE-CONN-24/25/27/28/29/30` · **7 assert in-summary của TC-FE-CONN-26** (`RelatedRecords.test.ts:764-770`) và **hàng TC-FE-CONN-26 ở §XVIII.8.2 — không sửa một chữ**.
> **Quy ước số hiệu**: BE `t29..t34` (tiếp theo `t28`, tổng **29 → 35** TC). FE render **TC-FE-CONN-60..64**, FE unit **TC-FE-CONN-70..72** — nhảy khoảng cố ý: dải 31..45 đã bị AC-CR-94/95 dùng ở cả doc lẫn mã, chọn dải mới để **không** phải tra chéo khi đọc lỗi đỏ.

### XXI.1 Fixture BE — **tái dùng tối đa**, thêm đúng 1 asset + 1 sự cố

| Fixture | Dùng cho | Ràng buộc (verify @source 2026-07-30) |
|---|---|---|
| `cls.asset6` / `cls.asset3` / `cls.asset0` (có sẵn) | hub `AC Asset` — t29/t30/t32 | **0 dòng sửa**; ô `total` của chúng là kỳ vọng của TC khác |
| `cls.wo6[0]` (có sẵn) | hub `PM Work Order` — t31/t32 | Ô «Phiếu sửa chữa» của hub này **không cần bản ghi nào**: ô vẫn được phát khi `total == 0` (INV-CONN-22) ⇒ prefill vẫn tính |
| **MỚI** `cls.asset_inc` + `cls.incident` | hub `Incident Report` — t31 | `Incident Report` reqd: `naming_series="IR-.YYYY.-.####"` · `asset` · `incident_type` ∈ {Failure,…} · `severity` ∈ {Low,…} · `description` (Text Editor); `reported_by`/`reported_at`/`status` có default. `is_submittable = 1` ⇒ dùng `_insert_bypassing_workflow` (docstatus 0 là đủ — ô đếm không lọc docstatus) |

- **Teardown**: `purge_asset(cls.asset_inc)` là đủ — `Incident Report` **có** trong `_ASSET_DEPENDENTS` (`tests/_asset_cleanup.py:30`). Bổ sung 1 dòng vào `tearDownClass`, **không** viết teardown riêng.
- **Serial của asset mới phải có hậu tố băm** (`frappe.generate_hash(length=6)`): fixture tên **cố định** tự chặn chính nó sau một lần crash không chạy teardown (LL-TEST — đã cháy 1 vòng ở run-4).
- **KHÔNG** gắn sự cố vào `cls.asset0`: TC "không lẫn dữ liệu giữa các bản ghi" đang khẳng định asset đó **0 liên kết**.

### XXI.2 TC backend — append **6**, sửa **2** (đã khai ở ADR §18.5)

| TC | Nội dung (oracle) | INV |
|---|---|---|
| **t29** `test_t29_create_keys_are_consistent_and_prefill_is_always_a_dict` | ∀ hub đã seed, ∀ ô: `isinstance(item["create_prefill"], dict)` (**không** `None`) ∧ mọi key/value là `str` non-empty (`type(x) is str`) ∧ **3 mệnh đề D-CR105-2**: (1) `can_create is False ⟺ create_route_hint == ""`; (2) `can_create is False ⇒ create_prefill == {}`; (3) **KHÔNG** assert `can_create is True ⇒ prefill != {}`. Thêm assert **dương** cho vế "không prefill mồ côi": `prefill != {} ⇒ can_create is True and hint != ""` | INV-CONN105-1 · INV-CONN4-1 |
| **t30** `test_t30_prefill_uses_the_url_query_key_not_the_link_fieldname` | Hub `AC Asset` (`cls.asset6`): 5 ô «Phiếu bảo trì định kỳ» / «Phiếu sửa chữa» / «Phiếu hiệu chuẩn» / «Báo cáo sự cố» / «Hồ sơ thiết bị» ⇒ `create_prefill == {"asset": cls.asset6}` (so **bằng `assertEqual` trên cả dict**, không `assertIn`). **Assert TƯỜNG MINH** khoá cấm: `assertNotIn(k, prefill)` với `k ∈ {"asset_ref","source_pm_wo","incident_report","final_asset","critical_asset"}` — đây là chỗ duy nhất phân biệt "đúng khoá URL" với "vô tình trùng" | INV-CONN105-2 |
| **t31** `test_t31_prefill_key_follows_the_parent_hub` | Hub `PM Work Order` (`cls.wo6[0]`) ⇒ ô «Phiếu sửa chữa» có `create_prefill == {"pm_wo": cls.wo6[0]}`. Hub `Incident Report` (`cls.incident`) ⇒ ô «Phiếu sửa chữa» có `create_prefill == {"incident": cls.incident}`. **Cùng một doctype đích, ba hub, ba khoá khác nhau** — TC này là thứ duy nhất chứng minh khoá derive từ `source_doctype` chứ không phải hằng `"asset"` | INV-CONN105-2 |
| **t32** `test_t32_create_screens_without_query_keys_get_empty_prefill` | (a) Ô `Asset Transfer` trên hub `AC Asset` ⇒ `create_prefill == {}` **dù** `can_create` có thể `True` (assert vế prefill; **không** assert `can_create is True` — nó phụ thuộc DocPerm của người chạy test). (b) Ô «Phiếu hiệu chuẩn» trên hub `PM Work Order` ⇒ `create_prefill == {}` (màn `/calibration/new` không đọc `pm_wo`). (c) Ô `internal_links` (hub `PM Work Order` → «Thiết bị», «Lịch bảo trì định kỳ») ⇒ `can_create is False ∧ create_route_hint == "" ∧ create_prefill == {}` | INV-CONN4-1 · D-CR105-4 |
| **t33** `test_t33_create_capability_tokens_bind_to_the_same_doctype_create` | `len(cmeta.CREATE_CAPABILITY) == 5` ∧ ∀ `(dt, token)`: `rbac.CAPABILITY_MAP[token] == (dt, "create")` ∧ `dt in cmeta.CREATE_CONTEXT` ∧ 3 doctype `{"Asset Document","Asset Transfer","Service Contract"}` **KHÔNG** có trong bảng (khai thêm = ĐỎ, buộc đọc ADR §12.9 trước) | INV-CONN4-2 |
| **t34** `test_t34_create_capability_parity_three_points` | ∀ 5 doctype: **derive** rồi khẳng định **ba bằng nhau** — (1) chuỗi cap tại **chính hàm tạo** của module API, (2) `CREATE_CAPABILITY[dt]`, (3) `requiredCapabilities` của route `CREATE_CONTEXT[dt].route` đọc từ `frontend/src/router/index.ts`. Bảng neo `(dt) → (module, hàm, dạng)` khai trong TC: `imm08/create_pm_work_order/require` · `imm09/create_repair_work_order/require` · `imm11/create_calibration/require` · `imm12/report_incident/const:_CAP_REPORT` · `purchase/create_purchase/require`. **FAIL-CLOSED**: không tìm thấy hàm / route / không parse được list literal ⇒ **ĐỎ** (tuyệt đối không `skip`/`continue`) | INV-CONN4-3 |
| **t01** *(SỬA — khai trước)* | `_ITEM_KEYS_V2` **9 → 10** (`+"create_prefill"`), đổi tên TC thành `…exactly_ten_keys…`; **giữ** phép so **TẬP** + phép chặn `_LEGACY_ITEM_KEYS` | INV-CONN-1 |
| **t04** *(SỬA — khai trước, siết chặt hơn)* | **bồi 1 assert**: `lifecycle_status` được đọc **đúng 1 lần** cho cả cây (spy quanh `frappe.db.get_value`, hoặc đếm truy vấn). Số lời gọi `list_fn` và số COUNT **giữ nguyên con số cũ** — **cấm nới ngưỡng** | INV-CONN4-10 · INV-CONN-6 |

### XXI.3 TC frontend — render (mount, KHÔNG grep) + unit thuần

| TC | Nội dung | INV |
|---|---|---|
| **TC-FE-CONN-60** | `payload19({can_create: true, create_route_hint: '/cm/create', create_prefill: {asset: 'AC-ASSET-2026-00001'}})` ⇒ mỗi `conn-group` có ô rỗng qua gate: **đúng 1** `conn-empty-actions`; **mọi** `conn-create` của wrapper nằm **bên trong** một `conn-empty-actions` **hoặc** một `conn-item` (0 chip lang thang); số chip == số ô rỗng qua đủ 3 gate (tính **từ chính fixture**, không hằng số) | INV-CONN105-4 |
| **TC-FE-CONN-61** | Cùng payload: `conn-empty-summary` **vẫn** `findAll('button') === 0` ∧ `findAll('a') === 0` ∧ `html()` không chứa `role="button"`; và nhãn VI của ô **có chip** **vẫn** xuất hiện trong câu «Chưa có: …» (dư thừa CÓ CHỦ ĐÍCH — D-CR105-7) | INV-CONN105-4 · INV-CONNFE6-2 |
| **TC-FE-CONN-62** | Bấm chip của ô rỗng `Asset Repair` ⇒ `push` gọi **đúng** `{ path: '/cm/create', query: { asset: 'AC-ASSET-2026-00001' } }`. Ô rỗng có `create_prefill: {}` ⇒ `push({ path: '/cm/create' })` ∧ `hasOwnProperty('query') === false` (URL **không** mọc `?`) | INV-CONN4-1 |
| **TC-FE-CONN-63** | Gate fail-CLOSED: (a) `caps.delete('repair.create')` ⇒ **0** chip cho ô rỗng đó, **nhưng** nhãn vẫn trong câu gộp; (b) `create_route_hint: '/route/khong-ton-tai'` ⇒ 0 chip; (c) `can_create: false` kèm hint+prefill hợp lệ ⇒ 0 chip ∧ `push` **không** được gọi | INV-CONN105-4 |
| **TC-FE-CONN-64** | Nhóm **toàn rỗng** có ô qua gate ⇒ `conn-group-label` **vẫn 0** (chip KHÔNG làm mọc tiêu đề — luật §14 giữ nguyên) ∧ `conn-item` 0 ∧ `conn-empty-summary` 1 ∧ `conn-empty-actions` 1 | D-CR105-7 |
| **TC-FE-CONN-70** | `emptyCells`: phân hoạch — `dataCells(g).length + emptyCells(g).length === g.items.length` trên `payload19` **và** trên nhóm `items: []`; vị-từ đọc `total` (ô `{total: 0, items: [row, row]}` ⇒ thuộc `emptyCells`) | INV-CONN105-3 |
| **TC-FE-CONN-71** | `emptyLabels` sau refactor: **cùng kết quả** cho 3 ca cũ (ưu tiên `label_vi`; thiếu cả hai ⇒ bị loại) ⇒ chứng minh refactor **0 đổi hành vi** | INV-CONNFE6-3 |
| **TC-FE-CONN-72** | `createTarget` với `create_prefill` **bắt buộc**: `{}` ⇒ `{path}` (không khoá `query`); khoá ngoài `CREATE_PREFILL_QUERY_KEYS[route]` ⇒ **loại im lặng**; value rỗng/`'   '`/không phải chuỗi ⇒ loại. (Ca `create_prefill: undefined` **giữ nguyên** trong TC-FE-CONN-16 — phòng thủ cửa sổ deploy) | INV-CONN105-2 |
| **guard `connectionsLegacyKeysRetired.acr92`** | `ConnectionItem` khai **ĐÚNG 10** khoá (so **TẬP**) ∧ tập khoá optional **RỖNG** (`expect(optional).toEqual([])`) ∧ 4 khoá legacy vẫn **0 hit** toàn `src/**` | INV-CONN105-1 |

### XXI.4 Chống test **giả xanh** (đọc trước khi khai DONE)

1. **`assertEqual` trên cả dict prefill, không `assertIn`**: `assertIn("asset", prefill)` xanh cả khi BE gửi kèm `asset_ref` — đúng thứ vòng này cấm. `assertNotIn` cho 5 khoá cấm là **bắt buộc**, không phải tô điểm.
2. **Mệnh đề (3) của D-CR105-2 KHÔNG được biến thành assert**: viết `can_create is True ⇒ prefill != {}` sẽ ĐỎ ở đúng 3 doctype **hợp lệ** ⇒ người sửa tiếp theo sẽ "chữa" bằng cách bịa khoá prefill (`asset_ref`!) hoặc tắt nút. TC nào đỏ theo kiểu đó ⇒ **sửa TC**, KHÔNG sửa BE.
3. **Parity 3 điểm phải DERIVE**: viết 3 chuỗi hằng cạnh nhau rồi so với nhau là **chép**, không phải parity — luôn xanh, không bao giờ bắt được drift. Và parser **fail-closed**: "không tìm thấy ⇒ bỏ qua" là guard chết (tiền lệ §XVIII.8.5).
4. **CẤM Python regex `frontend/src/router/routeAccess.ts`**: `:141` viết `'doc' + 'ument.write'` (nối chuỗi để né lint chặn `document.write`) ⇒ regex literal **không** khớp và guard sẽ kết luận sai. Vế FE-gate đã đóng bằng **import giá trị TS** ở `connectionsCreateParity.guard.test.ts:18` — đừng làm lại ở Python.
5. **Đếm PHẦN TỬ, không đếm chữ** (FE): `w.text().includes('Tạo phiếu sửa chữa')` xanh cả khi chip nằm sai chỗ (trong `<p>`) hoặc render 16 lần. Đếm `findAll('[data-testid="conn-empty-actions"] [data-testid="conn-create"]').length` và so với số ô tính **từ fixture**.
6. **`vue-tsc` là một phần của oracle**: bỏ `?` khỏi `create_prefill` mà quên bổ sung fixture ⇒ `vitest` vẫn xanh (runtime không kiểm kiểu) nhưng hợp đồng chưa được siết. `npx vue-tsc --noEmit` **0 lỗi** là điều kiện cần.
7. **Không assert số tuyệt đối của suite** (**286** file FE / **29** TC BE — đo từ đĩa 2026-07-30; số **284** ở §XX.3 đã stale sau vòng 1 run-5): đo từ đĩa, báo cáo **trước → sau**, chấm theo **delta**.
8. **Guard FE `connectionsCreateParity.guard.test.ts` PARSE `CREATE_CONTEXT` bằng văn bản** (`:117-128`, cắt tới `'\n}'` cột 0): sau khi thêm `query_keys`, **đếm lại** số route nó parse được (`beRoutes.length` phải là **8**). Guard cắt khối sớm ⇒ kiểm ít route hơn mà **vẫn xanh** — kiểu yếu-đi-âm-thầm không có triệu chứng. Chi tiết luật viết mã: `04 §V.10.3` bẫy 7.
9. **Mutation-check khi land (BE)**: (a) đổi khoá prefill sang `ctx.parents[source]` ⇒ t30 ĐỎ; (b) tính `prefill` **trước** khi kiểm quyền ⇒ t29 ĐỎ (prefill mồ côi); (c) đổi `CREATE_CAPABILITY["Asset Repair"] = "repair.write"` ⇒ t33 **và** t34 ĐỎ; (d) hardcode khoá `"asset"` cho mọi hub ⇒ t31 ĐỎ; (e) bồi khoá thứ 11 ⇒ t01 ĐỎ. **5 đột biến ⇒ 5 lần đỏ**; không đỏ = test template.

### XXI.5 DoD vòng AC-CR-105 (QA chấm — đọc baseline TỪ ĐĨA, **KHÔNG curl**)

- **BE, module-isolated, `timeout` tool ≥ 600000ms**: `bench --site miyano run-tests --app assetcore --module assetcore.tests.test_connections_tree` **XANH** với **≥ 35 TC** (baseline **29** đo từ đĩa 2026-07-30: `grep -c '    def test_' assetcore/tests/test_connections_tree.py` ⇒ chấm **delta ≥ +6**).
- **BE hồi quy tối thiểu**: `--module assetcore.tests.test_connections` **XANH** (**11 TC, 0 assert sửa** — payload chỉ **thêm** khoá) và `--module assetcore.tests.test_connections_list_filter_parity` **XANH** (11 TC). ĐỎ do nhiễm fixture phiên khác **không** tính (LL-TEST-30) — chờ quiescence rồi chạy lại.
- **FE**: `cd frontend && npx vitest run` **0 ĐỎ** + `npx vue-tsc --noEmit` **0 lỗi**. **`personaDashboards.test.ts` ĐỎ 1 TC là PRE-EXISTING** (đã chứng minh ở vòng 1 run-5 bằng revert) ⇒ **KHÔNG** tính vào DoD, và **KHÔNG** ai được "sửa cho xanh" trong vòng này.
- **0 DocType mới ⇒ 0 `bench migrate`**; 3 counter guard **delta 0**: `_EXPECTED_TEST_COUNT` **1024** (`tests/test_mobile_oas.py:212`) · `_GUARD_SUITE_SUM` **1167** · `_MOBILE_OAS_TOTAL` **1193**; OAS **0 op đụng** (`grep -c connections docs/mobile/openapi/*.yaml` = **0**).
- **`git diff --name-only`**: BE **đúng 4** path (`services/shared/connection_meta.py` · `services/connections.py` · `api/connections.py` **chỉ docstring** · `tests/test_connections_tree.py`); FE **đúng 5** path (`06 §VIII.14.1`). Path thứ 6 ở mỗi phía = **scope creep**, phải giải thích hoặc revert.
- **Blocked-reload (LL-DEPLOY-07/08 · LL-QA-15)**: `services/*.py` + `api/connections.py` đổi ⇒ HTTP live **vẫn** trả shape worker cũ cho tới khi **USER** `bench restart`. QA **KHÔNG** chấm bằng `curl`/Playwright trước reload, và **KHÔNG** kết luận "BE chưa land" từ HTTP — bằng chứng được chấp nhận trong vòng này là `run-tests` + `vitest` + `vue-tsc` + đọc mã.
- **Ngoài biên — chấm việc KHÔNG làm là PASS** (ADR §18.6): P4 vòng đời per-doctype (`AC-CR-90(c)`) ⇒ ô «Phiếu sửa chữa»/«Sự cố» **vẫn tắt** ở `Out of Service`, **INV-CONN4-4/5/6 vẫn `[CHƯA CÀI]`** · lỗ ghi `api/imm00.create_incident` (INV-CONN4-9) · EC-12-05 · nhóm toàn-rỗng giữ danh tính nhóm · loại `docstatus==2` khỏi ô đếm (`AC-CR-99`).
- ⛔ **KHÔNG** `git commit/push/merge` · **KHÔNG** `bench migrate` · **KHÔNG** `bench restart` · **KHÔNG** `npm run build` · **KHÔNG** reset DB.

---

## XXII. AC-CR-115 — **dải cắt render THẬT** cho 3 nhánh vận hành + **BẢN GHI trước Ô CHỨC NĂNG** (INV-OPH-19..30)

> Spec: [`ADR-IMM00-ASSET-OP-HISTORY §10`](./ADR-IMM00-ASSET-OP-HISTORY.md) (`D-OPH-17..20`) · FR-00-OPH-02 / BR-00-OPH-19..30 ([`02 §IV.43`](./02_Analysis_Design.md)) · hợp đồng đọc [`05 §III.26.6`](./05_API_Specification.md) · FE [`06 §VIII.15`](./06_Frontend_Design.md).
>
> ⚠️ **Đọc trước khi chấm — 3 điều dễ chấm sai:**
> 1. `§XX.3` dòng «Ngoài biên» từng nói dải cắt = **VÒNG 5, không làm là PASS**. **HẾT HIỆU LỰC**: từ vòng này **không có dải = FAIL**. «Tải thêm» thì ngược lại — **có** «Tải thêm» = **FAIL** (`D-OPH-19`).
> 2. `AssetOperationalHistory.test.ts:298-307` **PHẢI được sửa** (nó assert `not.toContain('Đang xem')`). Đây là **đổi hợp đồng có văn bản** (`D-OPH-20`), **KHÔNG** tính là "test cũ chuyển đỏ" của AC9. Danh sách đỏ-dự-kiến khai trước ở [ADR §10.5](./ADR-IMM00-ASSET-OP-HISTORY.md) — file thứ 3 bị sửa = **scope creep**.
> 3. Vòng này **0 dòng `.py` prod** ⇒ **0 blocker reload mới**. Nếu invariant BE mới ĐỎ ⇒ **bug BE thật**, ghi vào backlog + báo PM/BA; **KHÔNG** ai được sửa `services/*.py` để làm nó xanh (`BR-00-OPH-30`).

### XXII.1 Invariants (INV-OPH-19..30) — chấm được bằng test, không bằng mắt

| ID | Nội dung | Oracle |
|---|---|---|
| **INV-OPH-19** | **Cắt ⟺ báo cắt (hai chiều)**: `[op-history-truncation]` tồn tại trong section *i* **⟺** `N_i − M_i > 0`, với `M = số [op-history-row] của nhánh i`, `N = số trong [op-history-count] của nhánh i`. Fixture `rows=10/total=34` ⇒ **đúng 1** dải **trong chính nhánh đó**, text chứa **cả 3** số `10`, `34`, `24` và khớp **nguyên chuỗi** «Đang xem 10/34 — còn 24 chưa hiển thị»; 2 nhánh chưa bung ⇒ **0** dải. | vitest render (AC1) |
| **INV-OPH-20** | **KHÔNG báo cắt oan**: `total == len(rows)` (vd 7/7) ⇒ **0** `[op-history-truncation]`, **KỂ CẢ** khi payload gửi `truncated: 1`. | vitest (AC2) |
| **INV-OPH-21** | **KHÔNG che phần thiếu**: `total=34 / rows=10 / truncated=0` ⇒ **VẪN** đúng 1 dải, text vẫn 3 số 10/34/24. | vitest (AC3) |
| **INV-OPH-22** | **Cờ không cầm lái**: `grep -n 'Truncated' frontend/src/components/asset/AssetOperationalHistory.vue` ⇒ **0 hit** (static-read trong test, khuôn `INV-OPH-10`) ∧ 2 fixture nghịch của INV-OPH-20/21 cho ra đúng **0** và **1** dải. | vitest static-read + render |
| **INV-OPH-23** | **Rỗng thật không hồi quy**: `total == 0` ⇒ **0** dải ∧ **0** `[op-history-see-all]` ∧ **đúng 1** `[op-history-empty]` (`TC-FE-OPH-12` xanh **không sửa**). | vitest (AC4) |
| **INV-OPH-24** | **BẢN GHI trước CHỨC NĂNG + 2 tiêu đề**: trong `[tab-panel-related]`, `[asset-op-history]` đứng **trước** `[related-records]` theo **thứ tự DOM** (dùng `panel.element.querySelectorAll('[data-testid=asset-op-history],[data-testid=related-records]')` rồi so `[0]` — **KHÔNG** so `indexOf` trên chuỗi `html()`) ∧ **đúng 2** `[related-block-heading]`, text = «Dữ liệu vận hành của thiết bị» → «Liên kết nhanh theo chức năng» **theo thứ tự**. *(Lưu ý chấm: nhãn NHÓM trong `RelatedRecords.vue:212` dùng testid **`conn-group-label`** — testid KHÁC ⇒ **không** làm số `related-block-heading` vượt 2; nếu đếm ra >2 thì có người đã thêm heading thứ ba, ĐỎ đúng.)* | vitest (AC6) |
| **INV-OPH-25** | **Lối ra THẬT, 0 dead-control**: nhánh có dải ⇒ **đúng 1** `[op-history-see-all]`; trong `[asset-op-history]` **0** phần tử chứa chuỗi «Tải thêm» ∧ `grep -n 'Tải thêm' <component>` ⇒ **0 hit**. | vitest render + static-read (AC5) |
| **INV-OPH-26** | **GỌN — diện tích mặc định không tăng**: vào tab ⇒ `[op-history-row]` = **0** ∧ `[op-history-truncation]` = **0** ∧ `getAssetPMHistory`/`getAssetRepairHistory`/`getAssetIncidentHistory` mỗi hàm **0** lần gọi (`TC-FE-OPH-02/03` xanh **không sửa**) ∧ `[role=tab]` = **6**, nhãn 100% VI (`TC-CONNTAB-09` xanh). | vitest (AC7 · AC8) |
| **INV-OPH-27** | **BE — `total >= len(rows)`** cho **cả 3** endpoint, ở **3 ca**: dưới trần · **vừa khít** trần · trên trần. | `run-tests` |
| **INV-OPH-28** | **BE — cờ khớp số**: `truncated == (1 if total > len(rows) else 0)` cho cả 3 endpoint, 3 ca như trên. ĐỎ ⇒ **bug BE thật** (báo, không sửa prod). | `run-tests` |
| **INV-OPH-29** | **BE — số bị che đếm ĐÚNG**: thiết bị có `limit + k` bản ghi hợp lệ (`k=3`, `limit=10`) ⇒ `total − len(rows) == 3` **chính xác**. | `run-tests` |
| **INV-OPH-30** | **BE — rỗng thật**: thiết bị 0 bản ghi ⇒ `rows == [] ∧ total == 0 ∧ truncated == 0` (cả 3 endpoint). | `run-tests` |

### XXII.2 Test matrix

> **Cách đếm delta (AC9)**: đơn vị là **`it()` block**, không phải hàng TC trong bảng. Bảng dưới cho **8 TC mới** (`TC-FE-OPH-14..21`) ⇒ tối thiểu **8 `it()` mới**; TC nào có ≥2 mệnh đề độc lập (vd `TC-FE-OPH-17`, `TC-FE-OPH-21`) **nên** tách thành 2 `it()` để khi đỏ biết ngay mệnh đề nào chết. `TC-FE-OPH-09` là **SỬA**, không tính vào delta.

**FE — `frontend/src/components/asset/tests/AssetOperationalHistory.test.ts`** (sửa 1 TC + thêm `TC-FE-OPH-14..18`, `TC-FE-OPH-21`)

| TC | Nội dung | INV | AC |
|---|---|---|---|
| **TC-FE-OPH-09** *(SỬA — `:298-307`)* | Đảo `not.toContain('Đang xem')` → assert **đúng 1** `[op-history-truncation]` **trong nhánh pm**, `.text()` khớp nguyên «Đang xem 10/34 — còn 24 chưa hiển thị»; bỏ chữ «vòng sau» khỏi tên `it()`; giữ nguyên 2 assert cũ (10 dòng · badge `34`) | 19 | AC1 |
| **TC-FE-OPH-14** | Bung **1** nhánh (rows=10/total=34) ⇒ dải trong **CHÍNH** nhánh đó (`data-branch` khớp) ∧ **toàn khối** chỉ **1** dải (2 nhánh chưa bung: 0) | 19 · 26 | AC1 · AC7 |
| **TC-FE-OPH-15** | `total=7 / rows=7 / truncated:1` ⇒ **0** dải (số thắng cờ) | 20 · 22 | AC2 |
| **TC-FE-OPH-16** | `total=34 / rows=10 / truncated:0` ⇒ **1** dải, đủ 3 số | 21 · 22 | AC3 |
| **TC-FE-OPH-17** | Static-read component: **0 hit** `Truncated` · **0 hit** `Tải thêm` · **0 hit** `vòng sau`; và trong DOM đã bung: **0** phần tử chứa «Tải thêm» | 22 · 25 | AC5 · AC11 |
| **TC-FE-OPH-18** | Nhánh có dải ⇒ **đúng 1** `[op-history-see-all]` (href mang `?asset=`); nhánh `total=0` ⇒ **0** dải ∧ **0** see-all ∧ **1** `[op-history-empty]` | 23 · 25 | AC4 · AC5 |
| **TC-FE-OPH-21** | **Một số, một nguồn**: số trong `[op-history-count]` == `N` trong dải (fixture 10/34 ⇒ badge `'34'` ∧ dải chứa `/34`); ca nghịch `total=3 / rows=5` (BE trả tổng nhỏ hơn số dòng) ⇒ badge **`'5'`** ∧ **0** dải (`Math.max` chặn số âm — không bao giờ in «còn -2 chưa hiển thị») | 19 · 22 | AC1 |

**FE — `frontend/src/views/asset/tests/AssetDetailView.relatedTab.test.ts`** (thêm `TC-FE-OPH-19..20`)

| TC | Nội dung | INV | AC |
|---|---|---|---|
| **TC-FE-OPH-19** | Vào tab ⇒ thứ tự DOM `[asset-op-history]` **trước** `[related-records]` (so bằng `querySelectorAll`, không bằng `indexOf(html())`) | 24 | AC6 |
| **TC-FE-OPH-20** | **Đúng 2** `[related-block-heading]`, text đúng thứ tự + **0 acronym EN chưa dịch** (regex `/\b(PM|CM|WO|SLA|KPI|CAPA|RCA)\b/` ⇒ 0 match trên 2 chuỗi tiêu đề) | 24 | AC6 |

**BE — `assetcore/tests/test_asset_operational_history_contract.py`** (**thêm** `TC-OPH-B7..B10` vào file đã có, **0 dòng prod đổi**)

| TC | Nội dung | INV |
|---|---|---|
| B7 | 3 endpoint × 3 ca (dưới/vừa khít/trên trần) ⇒ `total >= len(rows)` | 27 |
| B8 | 3 endpoint × 3 ca ⇒ `truncated == (1 if total > len(rows) else 0)` | 28 |
| B9 | `limit + 3` bản ghi ⇒ `total − len(rows) == 3` (cả 3 endpoint) | 29 |
| B10 | asset sạch ⇒ `rows == [] ∧ total == 0 ∧ truncated == 0` | 30 |

> Fixture BE **phải** dùng asset/bản ghi có hậu tố ngẫu nhiên và dọn trong `tearDown` (LL-TEST-30 + bài học `TestTransferEditAuthzAndFlags`: fixture tên CỐ ĐỊNH tự chặn chính nó sau crash).

### XXII.3 DoD vòng AC-CR-115 (QA chấm — đọc baseline TỪ ĐĨA, chấm DELTA)

- **FE**: `cd frontend && npx vitest run` **0 ĐỎ** (trừ `personaDashboards.test.ts` — **1 TC ĐỎ PRE-EXISTING**, không tính, **không** sửa cho xanh) với **delta ≥ +8 test case mới** ∧ **0 test cũ chuyển đỏ** *(ngoại lệ duy nhất được phép: `TC-FE-OPH-09` bị **sửa** theo `D-OPH-20` — có văn bản, không tính là đỏ)*; `npx vue-tsc --noEmit` **0 lỗi**. Số file `*.test.ts` = **287** đo TỪ ĐĨA 2026-07-30 (số 284/286 ở `§XX.3`/`06 §VIII.14` là snapshot cũ) ⇒ **đo lại, chấm delta**.
- **BE, module-isolated, `timeout` tool ≥ 600000ms**: `bench --site miyano run-tests --app assetcore --module assetcore.tests.test_asset_operational_history_contract` **XANH** với **≥3 invariant mới** (spec 4: `INV-OPH-27..30`). Không bắt buộc full suite; nếu chạy, ĐỎ do nhiễm fixture phiên khác **không** tính (LL-TEST-30).
- **`git diff --name-only`**: phía FE **đúng 2** file sản phẩm (`components/asset/AssetOperationalHistory.vue` · `views/asset/AssetDetailView.vue`) + **≤3** file test; phía BE **đúng 1** path (`assetcore/tests/test_asset_operational_history_contract.py`). **`git diff --stat -- 'assetcore/api/*.py' 'assetcore/services/**/*.py'` ⇒ 0 path** ⇒ **0 blocker reload mới** (blocker #1 BLOCKED-RELOAD **không bị chạm**).
- **3 counter guard delta 0**: `_EXPECTED_TEST_COUNT` **1024** · `_GUARD_SUITE_SUM` **1167** · `_MOBILE_OAS_TOTAL` **1193** (đọc lại từ đĩa) · OAS `docs/mobile/openapi/*.yaml` **0 đổi**.
- **Cite-drift đóng CÙNG VÒNG (AC11)** — QA grep xác nhận **7 chỗ** ở [ADR §10.7](./ADR-IMM00-ASSET-OP-HISTORY.md): 4 chỗ doc đã supersede (`D-OPH-12` · ADR §7 hàng «VÒNG 5» · ADR §5.3 3 hàng testid · `ADR-IMM00-TRUNCATION-SSOT §8.7` hàng [P2 — fe]) + `06 §VIII.13.2` + `07 §XX` (INV-OPH-1/8/11 + dòng «Ngoài biên» §XX.3) + **mã**: `grep -n 'vòng sau' frontend/src/components/asset/AssetOperationalHistory.vue` ⇒ **0 hit**.
- **Mutation-check** (5 đột biến ⇒ 5 lần đỏ): xem `06 §VIII.15.5`. Nếu đột biến nào **không** làm đỏ ⇒ test là template, chấm **FAIL**.
- **Ngoài biên — chấm việc KHÔNG làm là PASS**: `AC-CR-116` (`listRouteForAsset` + guard `LIST_TARGET_ANCHOR`) · `AC-CR-117` (dòng bảo trì render `pm_type` Data tự do) · `AC-CR-118` (chuỗi «Xem tất cả» trần, câu đầy đủ ở `aria-label`) · phân trang thật cho 3 endpoint · `AC-CR-99` (ô đếm chưa loại `docstatus==2`) · `AC-CR-103`/`AC-CR-104`.
- **KHÔNG chấm bằng `curl`/Playwright** (LL-DEPLOY-07/08 · LL-QA-15): bằng chứng được chấp nhận = `run-tests` + `vitest` + `vue-tsc` + đọc mã.
- ⛔ **KHÔNG** `git commit/push/merge` · **KHÔNG** `bench migrate` · **KHÔNG** `bench restart` · **KHÔNG** `npm run build` · **KHÔNG** reset DB.

---

## XXIII. AC-CR-119 — **bịt 403 CHẾT** ở 3 nhánh vận hành: cap SOUND ở BE + trạng thái **KHOÁ** ở FE (INV-OPH-31..42)

> Nguồn: [`ADR-IMM00-ASSET-OP-HISTORY §11`](./ADR-IMM00-ASSET-OP-HISTORY.md) (`D-OPH-21..27`) · [`02 §IV.44`](./02_Analysis_Design.md) (`FR-00-OPH-03`, `BR-00-OPH-31..42`) · [`05 §III.26.7`](./05_API_Specification.md) · [`06 §VIII.16`](./06_Frontend_Design.md).
>
> **Nguyên tắc chấm của mục này:** soundness của một vị-từ quyền **KHÔNG** được chấm bằng cách đọc mã («cap này trông đúng doctype») — phải chấm bằng **hành vi hai chiều** (cap True ⇒ không 403; cap False ⇒ đúng envelope 403). Đọc mã là cách bug `pm.read`→`PM Work Order` sống sót qua nhiều vòng.

### XXIII.1 Invariants BE — `INV-OPH-31..36`

| Mã | Invariant | Chấm bằng |
|---|---|---|
| **INV-OPH-31** | **Soundness 2 CHIỀU, đo bằng HÀNH VI.** ∀ nhánh *b* ∈ {pm, cm, incident}: (a) user có `rbac.can(cap_b) is True` ⇒ gọi endpoint *b* trả `success is True` (**KHÔNG** FORBIDDEN); (b) user có `rbac.can(cap_b) is False` ⇒ trả **ĐÚNG** `{"success": False, "code": "FORBIDDEN", "http_status": 403}` với `message == MSG.AUTH_FORBIDDEN`. **KHÔNG** HTTP-500, **KHÔNG** dispatcher-403, **KHÔNG** `{"success": True, data:{... []}}` (list rỗng giả). | `test_asset_op_history_acl` |
| **INV-OPH-32** | **Bảng là RÀNG BUỘC.** ∀ `(cap, doctype)` ∈ `connection_meta.OP_HISTORY_BRANCH_GATE.values()`: `CAPABILITY_MAP[cap] == (doctype, "read")`. Và tập khoá **đúng** `{"pm","cm","incident"}` (không thừa, không thiếu). | idem |
| **INV-OPH-33** | **Doctype khai == doctype truy vấn THẬT** (chống «bảng đúng, mã đọc bảng khác»): `OP_HISTORY_BRANCH_GATE["pm"][1] == PMTaskLogRepo.DOCTYPE` ∧ `["cm"][1] == RepairRepo.DOCTYPE` ∧ `["incident"][1] == imm12._DT_INCIDENT`. So với **hằng của tầng repo/service**, KHÔNG với chuỗi gõ lại. | idem |
| **INV-OPH-34** | **`pm.read` KHÔNG SOUND — chứng minh bằng user thật.** User mang **duy nhất** role `Commissioning Manager`: `rbac.can("pm.read") is True` **∧** `rbac.can("pm.read_history") is False` **∧** `get_asset_pm_history` trả envelope FORBIDDEN. Đây là **bằng chứng cứng** rằng cap cũ không dùng được để gate nhánh này. | idem |
| **INV-OPH-35** | **Không leak nội bộ khi 403.** Chuỗi hoá **toàn bộ** payload trả về (`json.dumps(resp, ensure_ascii=False)`) của cả 3 nhánh ở ca 403 **KHÔNG** chứa: `"PM Task Log"`, `"Asset Repair"`, `"Incident Report"`, `"Traceback"`, `"SELECT"`, `"tab"` + tên bảng. Kiểm **cả** `frappe.local.response.get("_server_messages")` (nơi `frappe.throw` sẽ rò — `permissions.py:69-73`). | idem |
| **INV-OPH-36** | **Khe hở `select`-only không tồn tại.** ∀ dt ∈ 3 doctype: `frappe.only_has_select_perm(dt) is False` cho user test, **và** 0 dòng DocPerm/Custom DocPerm nào trên 3 doctype có `select=1 ∧ read=0`. (Nếu ĐỎ ⇒ cap sẽ khoá quá — **fail-closed, không rò** — nhưng phải báo BA, **không** tự nới.) | idem |

### XXIII.2 Invariants FE — `INV-OPH-37..42`

| Mã | Invariant | Chấm bằng |
|---|---|---|
| **INV-OPH-37** | **0 request vô vọng.** `capState(cap) === 'denied'` ⇒ bung nhánh: `fetchPMHistory`/`fetchRepairHistory`/`fetchIncidentHistory` (spy tầng transport `getAssetPMHistory`/`getAssetRepairHistory`/`getAssetIncidentHistory`) được gọi **0** lần; thu rồi bung lại vẫn **0**. | `AssetOperationalHistory.test.ts` |
| **INV-OPH-38** | **Khối `locked` không có lối ra giả.** Trong CHÍNH `[op-history-section]` của nhánh bị khoá: **1** `[op-history-locked]` ∧ **0** `[op-history-retry]` ∧ **0** `[op-history-see-all]` ∧ **0** `[op-history-count]` ∧ **0** `[op-history-error]` ∧ **0** `[op-history-empty]` ∧ **0** `[op-history-row]`. Đếm **trong section**, KHÔNG trong toàn wrapper. | idem |
| **INV-OPH-39** | **Microcopy trung tính (đo bằng chuỗi).** `.text()` của `[op-history-locked]`: **0** `Lỗi`/`lỗi` · **0** `403` · **0** `FORBIDDEN` · **0** `AUTH-403` · **0** `PM Task Log`/`Asset Repair`/`Incident Report` · **0** `Chưa có` · khớp **nguyên văn** 1 trong 3 câu SSoT + câu 2 dùng chung. | idem |
| **INV-OPH-40** | **Self-heal caps stale ⇒ CÙNG khối.** cap `granted` mà API reject bằng `new ApiError('…', { code: ErrorCode.FORBIDDEN, httpStatus: 403 })` ⇒ **1** `[op-history-locked]` ∧ **0** `[op-history-error]` ∧ **0** `[op-history-retry]`. Lặp lại với `httpStatus: 403` + `code` khác (vd `UNKNOWN`) ⇒ **vẫn** locked (`isForbiddenError` nhận cả 2 tín hiệu). | idem |
| **INV-OPH-41** | **Không over-block.** Lỗi **không** 403 (`new Error('lỗi mạng')` · `ApiError code INTERNAL_ERROR httpStatus 500`) ⇒ **1** `[op-history-error]` ∧ **đúng 1** `[op-history-retry]` ∧ **0** `[op-history-locked]`; bấm «Thử lại» ⇒ spy +**1** lần, thành công ⇒ render `[op-history-row]`. | idem |
| **INV-OPH-42** | **`capState` ⟺ `can`, và version khớp BE.** (a) ∀ cap, ∀ trạng thái store (`{}` · `{cap:false}` · `{cap:true}` · admin): `can(cap) === (capState(cap) === 'granted')`; (b) `capState` trả `'unknown'` **⟺** khoá vắng ∧ không admin; (c) `frontend/src/stores/auth.ts::CAP_SET_VERSION` **khớp byte** giá trị `rbac.CAP_SET_VERSION` đo từ BE. | `auth.capabilities.test.ts` + đối chiếu tay (c) |

### XXIII.3 Test case BE — module MỚI `assetcore/tests/test_asset_op_history_acl.py`

| TC | Loại | Nội dung |
|---|---|---|
| TC-OPHACL-01 | unit | `"pm.read_history" in CAPABILITY_MAP` ∧ `CAPABILITY_MAP["pm.read_history"] == ("PM Task Log", "read")` |
| TC-OPHACL-02 | unit | `OP_HISTORY_BRANCH_GATE` có **đúng** 3 khoá `{"pm","cm","incident"}`; ∀ nhánh `CAPABILITY_MAP[cap] == (doctype, "read")` (`INV-OPH-32`) |
| TC-OPHACL-03 | unit | doctype khai == hằng tầng repo/service: `PMTaskLogRepo.DOCTYPE` · `RepairRepo.DOCTYPE` · `imm12._DT_INCIDENT` (`INV-OPH-33`) |
| TC-OPHACL-04 | integration | User **chỉ** role `Commissioning Manager`: `can("pm.read") is True` ∧ `can("pm.read_history") is False` ∧ `api.imm08.get_asset_pm_history(asset)` ⇒ envelope FORBIDDEN 403 (`INV-OPH-34`) |
| TC-OPHACL-05 | integration | ∀ nhánh, user **thiếu** cap ⇒ envelope `{success:False, code:"FORBIDDEN", http_status:403}` + `message == MSG.AUTH_FORBIDDEN`; **assert phủ định**: `resp.get("success") is not True` ∧ `"data" not in resp or not resp["data"].get(rows_key)` (chống list-rỗng-giả) (`INV-OPH-31b`) |
| TC-OPHACL-06 | integration | ∀ nhánh, user **có** cap (role miền tương ứng: `PM User` / `Repair User` / `Corrective User`) ⇒ `success is True`, **không** FORBIDDEN (`INV-OPH-31a`) |
| TC-OPHACL-07 | integration | Ca 403 của cả 3 nhánh: `json.dumps(resp)` + `_server_messages` **không** chứa tên DocType / `Traceback` / `SELECT` (`INV-OPH-35`) |
| TC-OPHACL-08 | unit | ∀ 3 doctype: 0 dòng DocPerm có `select=1 ∧ read=0`; `frappe.only_has_select_perm(dt) is False` cho user test (`INV-OPH-36`) |

**Fixture — bắt buộc theo lesson đã có trong sổ:**
- Email user test **có hậu tố `uuid`** (`_test_ophacl_{uuid4().hex[:8]}@assetcore.test`) — fixture tên **CỐ ĐỊNH** tự chặn chính nó sau crash (unique index chặn re-insert khi teardown không chạy).
- Sau khi gán role: **bắt buộc** `rbac.invalidate_capabilities(email)` (cache 1h theo user — `rbac.py:217`) **trước** khi đọc `can()`; nếu không, test đọc caps của lần chạy trước ⇒ **xanh giả**.
- `frappe.set_user(u)` trong `try`, `frappe.set_user("Administrator")` trong `finally`; xoá user trong teardown (`force=True, ignore_permissions=True`).
- Asset dùng làm tham số **không cần tồn tại** cho ca 403 (gate chạy TRƯỚC truy vấn) ⇒ **không** tạo asset rác. Ca 200 (TC-06) dùng asset seed sẵn hoặc asset tạo-rồi-xoá trong cùng test; nhớ **asset mới LUÔN có sẵn 1 ALE `qr_generated`** (`ac_asset.py:83`).

### XXIII.4 Test case FE — `frontend/src/components/asset/tests/AssetOperationalHistory.test.ts`

| TC | Nội dung |
|---|---|
| TC-FE-OPH-22 | caps `{'pm.read_history': false, 'repair.read': true, 'corrective.read': true}` ⇒ bung nhánh pm: **0** lời gọi cả 3 spy (`INV-OPH-37`) |
| TC-FE-OPH-23 | idem ⇒ section pm có **1** `[op-history-locked]`, và trong section đó **0** retry / **0** see-all / **0** count / **0** error / **0** empty / **0** row (`INV-OPH-38`) |
| TC-FE-OPH-24 | Chuỗi `[op-history-locked]` khớp **nguyên văn** SSoT; `not.toMatch(/[Ll]ỗi|403|FORBIDDEN|AUTH-403|PM Task Log|Asset Repair|Incident Report|Chưa có/)` (`INV-OPH-39`) |
| TC-FE-OPH-25 | 3 nhánh **cùng** bị khoá ⇒ **3** `[op-history-locked]` (1/section, `data-branch` đúng) ∧ **0** request; `[op-history-toggle]` của mỗi nhánh có `data-locked="1"` **trước cả khi bung** |
| TC-FE-OPH-26 | caps `{'pm.read_history': true}` mà spy reject `ApiError(code FORBIDDEN, httpStatus 403)` ⇒ **1** locked ∧ **0** error ∧ **0** retry (`INV-OPH-40`); biến thể `httpStatus 403` + `code UNKNOWN` ⇒ **vẫn** locked |
| TC-FE-OPH-27 | caps đủ + `new Error('Không tải được dữ liệu')` ⇒ **1** error ∧ **đúng 1** retry ∧ **0** locked; bấm retry ⇒ spy gọi **2** lần, lần 2 OK ⇒ **2** `[op-history-row]` (`INV-OPH-41`) — **thay thế** `TC-FE-OPH-11` case 1 (xem `06 §VIII.16.5`) |
| TC-FE-OPH-28 | caps **vắng khoá** (`capabilities = {}`, không admin) ⇒ bung nhánh **VẪN gọi** API **1** lần (`unknown` KHÔNG khoá — `BR-00-OPH-37`); payload OK ⇒ render row bình thường |
| TC-FE-OPH-29 | **Không hồi quy `AC-CR-102/115`**: caps đủ + fixture `rows=10,total=34` ⇒ **10** `[op-history-row]` ∧ **1** `[op-history-truncation]` («Đang xem 10/34 — còn 24 chưa hiển thị») ∧ `[op-history-count]` = `34` ∧ **1** `[op-history-see-all]` ∧ **0** locked |

**Harness:** `auth` store là Pinia store thật (`setActivePinia(createPinia())` đã có ở `beforeEach:167`) ⇒ set caps bằng `useAuthStore().capabilities = {…}` **trước** `mountBlock()`; ca admin dùng cờ role admin thật, **KHÔNG** stub `can()` (stub sẽ bỏ qua chính `capState` đang test).

### XXIII.5 Test hiện có phải giữ XANH **không sửa** (nếu đỏ ⇒ ra ngoài biên)

- `assetcore/tests/test_asset_operational_history_contract.py` — parity `fields` @source ⇄ `05 §III.26.3`: vòng này **0** đổi `fields`/`filters`/`order_by`/`page_size`/khoá response ⇒ **phải xanh không sửa**. Đỏ = có người đổi hợp đồng đọc ⇒ **ĐỎ VÒNG**.
- `frontend/src/stores/tests/assetHistoryTruncation.test.ts` — 3 store chỉ **thêm** 1 ref, **không** đổi logic total/truncated ⇒ phải xanh; sửa nó = dấu hiệu đụng ngoài biên.
- `assetcore/tests/test_rowscope_scope_guard.py` · `test_rowscope_docperm_gate.py` — thêm gate tường minh ở `imm08.get_asset_history` là **cộng** thêm gate, không gỡ ⇒ phải xanh.
- `assetcore/tests/test_connections_tree.py` — `connection_meta.py` chỉ **thêm** 1 bảng, **0** đổi `LABEL_VI`/`PREVIEW_FIELDS`/`CREATE_CAPABILITY` ⇒ phải xanh.

### XXIII.6 Danh sách **ĐỎ dự kiến** khai TRƯỚC (ngoài danh sách này = scope creep)

Thêm 1 cap ⇒ `len(CAPABILITY_MAP)` **104 → 105** ⇒ `CAP_SET_VERSION` **`v104.e46d05d9a66d` → `v105.<digest>`**. **13 điểm / 4 file** — chi tiết dòng ở [ADR §11.9](./ADR-IMM00-ASSET-OP-HISTORY.md):

| File | Điểm | Xử lý |
|---|---|---|
| `tests/test_mobile_capability_map.py` | `:52` `_EXPECTED_CAP_SET_VERSION` · `:53` `_EXPECTED_CAP_COUNT` | giá trị **ĐO** + comment cite `AC-CR-119` |
| `tests/test_imm00.py` | `:4233` prefix · `:4237` count · **8×** `assertEqual(CAP_SET_VERSION, …)` (`:8974,9601,9913,10207,10569,10939,11102,11405`) | cập nhật giá trị + message ghi thêm lý do |
| `tests/test_purchase.py` | `:26` `_EXPECTED_CAP_VERSION_PREFIX` | `"v105."` |
| `frontend/src/stores/auth.ts` | `:51` `CAP_SET_VERSION` (**prod**) | bump theo giá trị ĐO |

⛔ **CẤM nới assert cho xanh** (AC5): `_EXPECTED_CAP_COUNT`/`_EXPECTED_CAP_SET_VERSION` phải là **hằng đo được**, **không** được thay bằng `len(CAPABILITY_MAP)` / regex lỏng / `skip`. Guard đang làm **đúng** việc của nó: đổi cap-set ⇒ buộc BA/BE cập nhật tường minh.

### XXIII.7 DoD vòng `AC-CR-119`

1. `bench --site miyano run-tests` **module-isolated** (timeout tool **≥600000ms** mỗi module) XANH: `assetcore.tests.test_asset_op_history_acl` (**MỚI**) · `test_mobile_capability_map` · `test_imm00` · `test_purchase` · `test_imm08` · `test_imm09` · `test_imm12` · `test_rbac` · `test_connections_tree` · `test_rowscope_scope_guard` · `test_asset_operational_history_contract`.
2. `npx vitest run` XANH **toàn bộ**; `npx vue-tsc --noEmit` **0 lỗi**.
3. Cap-set version **ĐO** bằng `bench --site miyano execute assetcore.services.shared.rbac._compute_cap_set_version` — **cùng một** giá trị ở BE test **và** `frontend/src/stores/auth.ts`. **KHÔNG** gõ hash tay.
4. **Biên file `.py` prod — chấm bằng DELTA so với ĐẦU VÒNG** (working tree đã DIRTY từ các vòng trước ⇒ `git diff` tuyệt đối **không** dùng được làm ngưỡng): tập path `assetcore/api/*.py` **KHÔNG TĂNG** thêm path nào; tập path `assetcore/services/**/*.py` tăng **đúng 3** path và đúng 3 path đó là `shared/rbac.py` · `shared/connection_meta.py` · `imm08.py`. Cách chấm: chụp `git diff --name-only -- 'assetcore/api/*.py' 'assetcore/services/**/*.py' | sort` **trước** khi code, so `diff` với ảnh chụp **sau** khi code. Nội dung 3 file: `rbac.py` +**1** cặp khoá-giá-trị · `connection_meta.py` +**1** bảng (+docstring) · `imm08.py` +**1** hằng +**1** lời gọi gate — **0** đổi `fields`/`filters`/`order_by`/`page_size`/khoá response.
5. `0` OAS delta (`docs/mobile/openapi/*.yaml` không đổi) · 3 counter `_EXPECTED_TEST_COUNT` / `_GUARD_SUITE_SUM` / `_MOBILE_OAS_TOTAL` **delta 0** (đọc lại **từ đĩa** trước khi chấm).
6. `0` schema/patch/fixture delta ⇒ **KHÔNG** `bench migrate`.
7. **Ngoài biên — chấm việc KHÔNG làm là PASS**: `AC-CR-120` (đồng bộ cap-count/version `docs/mobile/`, đang v97) · `AC-CR-121` (OAS khai 403 là dispatcher trong khi in-handler 403 đến trên HTTP-200) · `AC-CR-122` (áp `capState` cho `RelatedRecords.vue` + 5 màn Detail) · nới DocPerm cho role mới (**quyết định cấp quyền — USER/quản trị**) · `AC-CR-116/117/118` · `AC-CR-99` · phân trang thật 3 endpoint.
8. **KHÔNG chấm bằng `curl`/Playwright** (LL-DEPLOY-07/08 · LL-QA-15): vòng này **THÊM 1 nhu cầu reload** vào blocker BLOCKED-RELOAD (3 file `.py` prod) ⇒ mọi kết luận live **trước** `bench restart` + `bench --site miyano clear-cache` là **vô nghĩa**. Bằng chứng được chấp nhận = `run-tests` + `vitest` + `vue-tsc` + đọc mã.
9. ⛔ **KHÔNG** `git commit/push/merge` · **KHÔNG** `bench migrate` · **KHÔNG** `bench restart` · **KHÔNG** `bench clear-cache` · **KHÔNG** `npm run build` · **KHÔNG** reset DB (**HARD-STOP — thuộc USER**). Hai lệnh reload phải **ghi vào handoff** cho USER, không tự chạy.
