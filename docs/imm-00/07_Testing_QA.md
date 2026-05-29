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

### I.2.b. Từ Business Rule
| BR ID | Phát biểu | Component liên quan (I.1) | Kỹ thuật test phù hợp |
|---|---|---|---|
| BR-00-01 | Class I→Low; II→Medium; III→High/Critical | IMM Device Model `.validate()` | Decision Table / EP |
| BR-00-02 | `lifecycle_status` chỉ đổi qua `transition_asset_status()` | AC Asset controller + service | EP (block direct mutate) |
| BR-00-03 | IMM Audit Trail + ALE immutable | Controller + Permission | Error guessing (update/delete) |
| BR-00-04 | Decommissioned → suspend PM/Calibration schedule | `transition_asset_status()` | State Transition |
| BR-00-05 | Out of Service / Decommissioned → block Work Order | `validate_asset_for_operations()` | EP (status partition) |
| BR-00-06 | Calibration Lab thiếu iso_17025_cert → warning | `ACSupplier.validate()` | EP (warning, không block) |
| BR-00-07 | response_min < resolution_hours × 60 | `IMMSLAPolicy.validate()` | BVA |
| BR-00-08 | CAPA before_submit: root_cause + corrective + preventive | `IMMCAPARecord.before_submit()` | Decision Table |
| BR-00-09 | CAPA quá due_date → auto Overdue (scheduler) | `check_capa_overdue()` | BVA (date boundary) |
| BR-00-10 | Mỗi đổi lifecycle_status → 1 ALE | `transition_asset_status()` | State Transition |
| BR-00-13 | GMDN kế thừa một chiều Category→Model→Asset | `before_insert` hooks | EP + Integration |
| BR-00-14 | Override GMDN cho phép cả 3 cấp; không ghi đè sau insert | `before_insert` chỉ điền khi trống | EP |

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
| TC-NTF-16 | `test_notify_incident_created_skips_self` | `notify_incident_created` (E3) | actor == assigned_to → KHÔNG dispatch (self-notify) | EP |
| TC-NTF-17 | `test_notify_calibration_due_dispatches_on_status_change` | `notify_calibration_due` (E4) | old=ON_SCHEDULE, new=DUE_SOON → dispatch cho `responsible_technician`; old=DUE_SOON, new=OVERDUE → dispatch lại (escalation) | Decision Table |
| TC-NTF-18 | `test_notify_calibration_due_noop_when_status_unchanged` | `notify_calibration_due` (E4) anti-spam | old=DUE_SOON, new=DUE_SOON → KHÔNG dispatch; new=ON_SCHEDULE → KHÔNG dispatch | State Transition |
| TC-NTF-19 | `test_notify_calibration_due_fallback_custodian` | `notify_calibration_due` (E4) | asset KHÔNG có `responsible_technician` → fallback `custodian` | Decision Table |
| TC-NTF-20 | `test_render_email_contains_subject_and_deeplink` | `_render_email` (vòng 4) | doc có doctype+name → HTML chứa `subject`, chứa `body_html` nguyên văn, chứa URL `get_url_to_form` (nút "Mở phiếu"), chứa footer branding "AssetCore" | EP |
| TC-NTF-21 | `test_render_email_omits_deeplink_when_no_doc_ref` | `_render_email` (vòng 4) | doc thiếu doctype/name → HTML vẫn dựng (subject+body+footer), KHÔNG có nút deep-link, không raise | Error guessing |
| TC-NTF-22 | `test_dispatch_sends_html_email_with_deeplink` | `_dispatch`+`_render_email` (vòng 4) | user bật email → `_safe_sendmail` nhận `message` là HTML (chứa subject + deep-link), bell `email_content` vẫn là `message` ngắn | Decision Table |
| TC-NTF-23 | `test_render_email_reused_across_events` | `_render_email` (vòng 4) | gọi với subject/body của E1..E4 (4 doctype khác nhau) → mỗi HTML chứa đúng subject + body tương ứng, cùng khung header/footer (1 template tái dùng) | EP |

### III.2b-1. Vòng 4 — HTML email template (TDD)

> Bổ sung TC-NTF-20..23 cho builder `_render_email` (spec §III.1b-3, file `04_Backend_Design.md`). Viết TRƯỚC implement. Email plain-text fallback do Frappe core sinh tự động (`set_html_as_text`) → không test thủ công phần text, chỉ assert `message` truyền vào sendmail là HTML. Regression: TC-NTF-01..19 (19 test) phải vẫn xanh — builder KHÔNG đổi recipient/guard logic.

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
| 8 | Đưa ra khỏi sử dụng | Active → Out of Service | PM Manager | ⬜ Planned | ⬜ Planned |
| 9 | Hoàn thành sửa chữa | Under Repair → Active | PM User | ⬜ Planned | ⬜ Planned |
| 10 | Không thể sửa chữa | Under Repair → Out of Service | PM Manager | ⬜ Planned | ⬜ Planned |
| 11 | Hiệu chuẩn đạt | Calibrating → Active | PM User | ⬜ Planned | ⬜ Planned |
| 12 | Hiệu chuẩn không đạt | Calibrating → Out of Service | PM Manager | ⬜ Planned | ⬜ Planned |
| 13 | Khôi phục hoạt động | Out of Service → Active | PM Manager | ⬜ Planned | ⬜ Planned |
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
| BR-00-09 | CAPA auto-overdue | `TestS11_CheckCapaOverdueScheduler` | BVA | 1 / ⬜ |
| BR-00-10 | 1 ALE / transition | `TestACAsset::test_transition_creates_lifecycle_event` | State Transition | 1 / 0 |
| BR-00-13/14 | GMDN inheritance | `TestListAssetsGmdnFilter::*` (filter); inherit test | EP | partial ✅ |

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
