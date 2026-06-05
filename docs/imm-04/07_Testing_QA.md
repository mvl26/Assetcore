# 07 — Kiểm thử & An ninh (Testing & QA & Security)

| Mục | Giá trị |
|---|---|
| Module | IMM-04 — Lắp đặt, định danh và kiểm tra ban đầu |
| Phạm vi | Per-module |
| Owner | QA Lead + Security Officer |
| Liên kết | 02 Analysis (US, BR, Activity, BPMN) · 03 Diagrams · 04 Backend · 05 API · 06 Frontend |

> **Mục đích**: Suy ra test case có hệ thống từ phân tích (file 02) bằng kỹ thuật black-box + white-box, không liệt kê tự phát. Bao gồm: phân tích đối tượng test → chọn kỹ thuật → viết test → traceability → UAT → security → code quality. Phần VI (Security) là gate go-live.

---

# Phần I — Test Analysis (Phân tích đối tượng test)

> Mục tiêu Phần I: trả lời 4 câu hỏi trước khi viết test case: **(1) test cái gì** (component inventory) **(2) suy ra từ đâu** (US/BR/Activity) **(3) ưu tiên cái nào** (risk) **(4) loại trừ cái nào** (out-of-scope).

## I.1. Component Inventory — Liệt kê phần mềm cần test

Toàn bộ artefact test được của IMM-04. Mỗi dòng → ≥ 1 test class ở Phần III. Nguồn: 04 Backend §Service/§Hook · 05 API §Catalog · 06 Frontend §Components.

| # | Component | Loại | File / Tên | Test layer áp dụng |
|---|---|---|---|---|
| 1 | `Asset Commissioning` | DocType | `asset_commissioning/asset_commissioning.json` | Integration (lifecycle) |
| 2 | `Asset QA Non Conformance` | DocType | `asset_qa_non_conformance/*.json` | Integration |
| 3 | `Commissioning Checklist` / `Commissioning Document Record` | Child DocType | `commissioning_checklist`, `commissioning_document_record` | Integration |
| 4 | `IMM-04 Workflow` | Workflow | `workflow/imm_04_workflow.json` (11 state, 23 transition) | Integration (state transition) |
| 5 | `initialize_commissioning`, `create_ac_asset`, `log_lifecycle_event`, `check_auto_clinical_hold` | Service function | `services/imm04.py` | Unit |
| 6 | `validate_gate_g01`, `validate_gate_g03`, `validate_gate_g05_g06` | Gate validator | `services/imm04.py` | Unit (Decision Table / BVA) |
| 7 | `_vr01_unique_serial_number`, `_vr05_risk_class_change_warning`, `_vr06_immutable_lifecycle_events`, `_validate_document_expiry` | Field validator | `services/imm04.py` | Unit (BVA/EP) |
| 8 | API endpoints (35 whitelist, xem I.1.a) | API endpoint | `api/imm04.py` | API integration |
| 9 | Lifecycle event `commissioned` + `IMM Audit Trail` | Lifecycle event | `log_lifecycle_event` → `utils/lifecycle.py` | Integration (audit chain) |
| 10 | `check_commissioning_overdue` | Scheduler job | `services/imm04.py::check_commissioning_overdue` | Unit + Cron simulation |
| 11 | Commissioning list/form/dashboard views | FE view | `frontend/src/views/imm04/*.vue` | E2E (Playwright) |

### I.1.a. API endpoint catalog (verify từ `@frappe.whitelist`)

35 endpoint trong `api/imm04.py`. Read (GET): `get_form_context`, `list_commissioning`, `get_barcode_lookup`, `get_dashboard_stats`, `generate_qr_label`, `get_po_details`, `search_link`, `check_sn_unique`, `list_non_conformances`, `generate_handover_pdf`, `get_users_by_role`, `get_gate_status`, `list_my_pending_approvals`, `get_commissioning_origin`, `get_lifecycle_timeline`. Mutating (POST): `transition_state`, `submit_commissioning`, `save_commissioning`, `create_commissioning`, `report_nonconformance`, `close_nonconformance`, `assign_identification`, `generate_internal_qr`, `submit_baseline_checklist`, `clear_clinical_hold`, `retry_mint_asset`, `upload_document`, `approve_clinical_release`, `report_doa`, `delete_commissioning`, `cancel_commissioning`, `submit_for_approval`, `approve_pending`, `create_from_purchase`.

## I.2. Trace nguồn test — User Stories, Activity Flows, Business Rules

Mỗi US/BR/Activity phải có ≥ 1 test ở Phần III và xuất hiện trong matrix Phần IV. Nguồn: → 02 §Functional Specs (US + AC) · 02 §Business Rules (IV.2) · 02 §II.10 Activity diagram per UC.

### I.2.a. Từ User Story
| US ID | Tiêu đề ngắn | Acceptance Criteria # | Test layer dự kiến |
|---|---|---|---|
| US-04-01 | Tạo phiếu từ PO hợp lệ | AC-01, AC-02 | Unit + API + UAT |
| US-04-02 | VR-01 block serial trùng | AC-01, AC-02 | Unit + API + UAT |
| US-04-03 | Gate G01 block khi thiếu CO | *(AC trong 02 §IV.1)* | Unit + API + UAT |
| US-04-04 | Baseline Fail → Re Inspection (G03) | *(AC trong 02 §IV.1)* | Unit + API + UAT |
| US-04-05 | Auto Clinical Hold (VR-07) | *(AC trong 02 §IV.1)* | Unit + UAT |
| US-04-06 | Block release + Submit sinh Asset (G05/G06) | *(AC trong 02 §IV.1)* | Unit + Integration + UAT |
| US-04-07 | Board approver bắt buộc (G06) | *(AC trong 02 §IV.1)* | Unit + UAT |
| US-04-08 | Khai báo DOA | *(AC trong 02 §IV.1)* | Integration + UAT |

### I.2.b. Từ Business Rule
| BR ID | Phát biểu | Component liên quan (I.1) | Kỹ thuật test phù hợp |
|---|---|---|---|
| BR-04-01 | Asset chỉ tạo qua `create_ac_asset()` trong `on_submit` | `create_ac_asset`, hook `on_submit` | Use Case + State Transition |
| BR-04-02 (G01) | CO/CQ/Manual mandatory phải Received/Waived trước rời Pending Doc Verify | `validate_gate_g01` | Decision Table / EP |
| BR-04-03 (VR-01) | `vendor_serial_no` UNIQUE trên Asset + Commissioning | `_vr01_unique_serial_number` | EP + Error guessing |
| BR-04-04 (G03) | 100% baseline Pass/N/A; Fail → Re Inspection | `validate_gate_g03` | Decision Table |
| BR-04-05 (VR-07) | Class C/D/Radiation → Clinical Hold + license bắt buộc | `check_auto_clinical_hold` | Decision Table / EP |
| BR-04-06 (VR-04/G05) | No Open NC trước Release | `validate_gate_g05_g06` | Decision Table |
| BR-04-07 (G06) | `board_approver` bắt buộc trước Submit/Release | `validate_gate_g05_g06` | EP (present/absent) |
| BR-04-08 (GW-2) | Asset có CN ĐK lưu hành Active/Exempt trước Submit | `_validate_document_expiry` + GW-2 check | Decision Table |
| BR-04-11 | Stamp `commissioning_date` tại Clinical Release (idempotent, 3 write-path) + KPI `released_this_month` đếm theo `commissioning_date ∈ tháng` (KHÔNG `modified`) | `_stamp_commissioning_date`, `get_dashboard_stats` | Invariant + Idempotency + BVA (biên tháng) |

### I.2.c. Từ Activity Flow / BPMN
| Activity ID | Use Case | Branch chính | Branch ngoại lệ |
|---|---|---|---|
| UC-04-01 | Tạo phiếu từ PO | PO hợp lệ → populate docs → Draft | PO NOT_FOUND; risk_class C/D/Radiation thêm row License |
| UC-04-05 | Gán Serial + sinh QR | SN mới → QR sinh → Initial Inspection | SN trùng → VR-01 block |
| UC-04 (G03) | Baseline inspection | All Pass/N/A → Clinical Release/Hold | 1 critical Fail → Re Inspection |
| UC-08 (DOA) | Khai báo DOA | Installing → NC → khắc phục → To Be Installed | NC → Return To Vendor (terminal) |

## I.3. Risk-based Priority

| Component (I.1) | Likelihood (1-5) | Impact (1-5) | Risk = L×I | Priority |
|---|---|---|---|---|
| `create_ac_asset` (mint Asset on_submit) | 3 | 5 | 15 | **Critical** |
| `validate_gate_g05_g06` (release gate + approver) | 3 | 5 | 15 | **Critical** |
| `validate_gate_g01` (mandatory docs) | 4 | 4 | 16 | **Critical** |
| `_vr06_immutable_lifecycle_events` (audit integrity) | 2 | 5 | 10 | High |
| `_vr01_unique_serial_number` | 4 | 3 | 12 | High |
| `validate_gate_g03` (baseline pass) | 3 | 4 | 12 | High |
| `check_auto_clinical_hold` (VR-07) | 3 | 4 | 12 | High |
| Workflow transitions (23) | 3 | 3 | 9 | Medium |
| `check_commissioning_overdue` (scheduler) | 2 | 3 | 6 | Medium |
| `get_dashboard_stats` (read-only) | 2 | 2 | 4 | Low |

**Quy ước priority**: Critical (R ≥ 15) test trước, fail = block release · High (10–14) bắt buộc trước go-live · Medium (5–9) trong sprint · Low (< 5) chỉ test khi báo bug.

## I.4. Scope

- **In-scope**: gate logic G01/G03/G05/G06 (I.1 #6), validator VR-01/05/06 (#7), workflow 23 transition (#4), auto-mint Asset + audit chain (#5,#9), API permission matrix (#8).
- **Out-of-scope**: Performance test (giao Phần III.8); Penetration test (giao Phần VI.10); cross-module với IMM-05 (Asset Document set) và IMM-08 (PM auto-create) chỉ smoke — IMM-08 listener còn deferred (xem IMM04-BUG-032).
- **Assumptions**: master data (Device Model, Vendor, PO) đã seed qua `scripts/uat/uat_imm04.py`; test users đã tạo đủ role; browser Chrome ≥ 120.

---

# Phần II — Test Design Techniques (Kỹ thuật thiết kế test case)

> Mỗi test phải truy được về 1 kỹ thuật ở dưới.

## II.1. Black-box techniques

| Kỹ thuật | Khi nào dùng | Áp dụng vào IMM-04 | Số test sinh ra |
|---|---|---|---|
| **Equivalence Partitioning (EP)** | Input có miền giá trị chia nhóm | `risk_class` Select (A/B/C/D/Radiation), `overall_inspection_result` (Pass/Fail/Conditional Pass), permission partition theo role | 1 test/partition |
| **Boundary Value Analysis (BVA)** | Numeric/date/length có biên | `reception_date` (today vs tomorrow), `_validate_document_expiry` (past/today/<30d/future), SN length, file size (≤ 20 MB) | 2-3 test/biên |
| **Decision Table** | Multi-condition gate | G01 (mandatory × status), G03 (pass × critical), G05/G06 (NC open × approver set), VR-07 (risk_class → hold) | 2^N rút gọn |
| **State Transition Testing** | Workflow FSM | `imm_04_workflow.json` 23 transition (11 state) | mỗi transition + invalid |
| **Use Case Testing** | End-to-end actor flow | UAT golden scenario, API integration | 1/main + 1/alt + 1/exception |
| **Error Guessing** | null, empty, SN unicode, double-submit | `assign_identification`, `submit_commissioning` (idempotent), `_vr01` empty SN | Bổ sung |

## II.2. White-box techniques

| Kỹ thuật | Áp dụng vào | Tiêu chí đạt | Công cụ |
|---|---|---|---|
| **Statement coverage** | Service functions (I.1 #5-7) | ≥ 85% line | `coverage report` |
| **Branch / Decision coverage** | Functions có if/else, try/except | ≥ 80% branch | `coverage --branch` |
| **Condition / MC/DC** | Gates G01/G03/G05_G06 multi-AND | Mỗi sub-condition kiểm soát outcome độc lập | Manual test design + coverage |
| **Path coverage** | `check_auto_clinical_hold`, `_vr01` (≤ 20 LOC) | Toàn bộ path khả dĩ | Manual |

## II.3. Mapping Component → Kỹ thuật

| Loại component | Kỹ thuật chính | Kỹ thuật phụ |
|---|---|---|
| Field validator (`_vr*`, `_validate_document_expiry`) | BVA + EP | Error guessing |
| Gate logic (`validate_gate_*`) | Decision Table | MC/DC |
| Workflow transition | State Transition | Use Case |
| Service function pure (`check_auto_clinical_hold`) | EP + Branch coverage | BVA |
| API endpoint | Use Case + EP | Error guessing (double-submit) |
| Scheduler (`check_commissioning_overdue`) | Use Case (setup → run → assert) | Error guessing (batch partial) |
| FE view (Playwright) | Use Case end-to-end | Error guessing (network 4xx/5xx, role gate) |

---

# Phần III — Test Plan (Kế hoạch thực thi)

## III.1. Test Pyramid

```
                  ┌────────────┐
                  │  E2E / UAT │   ~5%  (Playwright golden scenario)
                 ─┴────────────┴─
              ┌──────────────────────┐
              │   API Integration    │   ~15% (35 whitelist endpoint)
             ─┴──────────────────────┴─
          ┌────────────────────────────────┐
          │  Workflow + DocType lifecycle  │   ~25% (11 state, 23 transition)
         ─┴────────────────────────────────┴─
      ┌────────────────────────────────────────────┐
      │         Unit — Service Layer               │   ~55% (gates + VRs)
     ─┴────────────────────────────────────────────┴─
```

Mọi service function phải có test trước khi code (TDD — → CLAUDE.md §17). Mỗi gate (G01/G03/G05/G06) và validation rule có ≥ 1 happy + 1 negative test.

> **Trạng thái thực tế (2026-05-29)**: test hiện consolidate trong **một file** `assetcore/tests/test_imm04.py` (391 LOC). Các file con (`test_imm04_service.py`, `_validators.py`, `_workflow.py`, `_audit.py`, `_api.py`, `test_asset_commissioning_doctype.py`, e2e `test_imm04_golden.py`) là **kế hoạch chia file** — đánh dấu ⬜ Planned ở dưới.

## III.2. Unit test — Service Layer

File hiện tại: `assetcore/tests/test_imm04.py`. Mỗi test class trace về ≥ 1 dòng I.1.

| Test class | Function cover | Kỹ thuật | Cases | Trạng thái |
|---|---|---|---|---|
| `TestGateG01` | `validate_gate_g01` | Decision Table | 8 (all received/waived, pending mandatory, non-mandatory, skip Draft/Pending Doc Verify, incomplete flag ±note) | ✅ Live |
| `TestGateG03` | `validate_gate_g03` | Decision Table | 4 (all pass, N/A=pass, one fail blocks, skip non-release state) | ✅ Live |
| `TestGateG05G06` | `validate_gate_g05_g06` | Decision Table | 3 (no NC + approver pass, no approver blocks, skip non-release) | ✅ Live |
| `TestVR01UniqueSerial` | `_vr01_unique_serial_number` | EP + Error guessing | 2 (empty SN skip, new SN pass) | ✅ Live |
| `TestVR07ClinicalHold` | `check_auto_clinical_hold` | EP/Decision Table | 6 (A/B no hold, C/D/Radiation hold, radiation flag) | ✅ Live |
| `TestLogLifecycleEvent` | `log_lifecycle_event` | Use Case | 2 (event appended, no-attr noop) | ✅ Live |
| `TestRC05AuditTrailNotEmpty` | `log_lifecycle_event` → audit trail | Integration | 1 (writes audit trail row) | ✅ Live |
| `TestAUTH05FourEyes` | four-eyes approval guard | Decision Table | 4 (same-user block, distinct pass, self-submitter block, other approve) | ✅ Live |
| `TestRC06AssetAutoMint` | `create_ac_asset` | Use Case | 1 (returns existing when already set) | ✅ Live |
| `TestInitializeCommissioning` | `initialize_commissioning`, `_populate_mandatory_documents` | EP | happy B/C/D/Radiation | ⬜ Planned |
| `TestVR06Immutability` | `_vr06_immutable_lifecycle_events` | Error guessing | edit existing row raise, new row pass | ⬜ Planned |
| `TestDocumentExpiry` | `_validate_document_expiry` | BVA | past/today/<30d/future | ⬜ Planned |
| `TestOverdueScheduler` | `check_commissioning_overdue` | Use Case + cron | 200-open simulation | ⬜ Planned |
| `TestOverdueSoT` (BR-04-10) | `overdue_commissioning_filter`, `get_dashboard_stats`, `list_commissioning(overdue=1)` | Invariant + EP | TC-04-30 helper trả đúng dict (anchor `reception_date`, `<today−OVERDUE_DAYS`, `workflow_state NOT IN terminal`, `docstatus!=2`); TC-04-31 `overdue_sla == list_commissioning({overdue:1}).pagination.total` (card==drill); TC-04-32 `overdue:1` AND filter khác không clobber + KHÔNG lọt raw column | ⬜ Planned |
| `TestCommissioningDateKpi` (BR-04-11) | `_stamp_commissioning_date`, `transition_state`/`submit_commissioning`/`approve_clinical_release`, `get_dashboard_stats().kpis.released_this_month` | Invariant + EP + BVA + idempotency | TC-04-33 stamp tại MỖI 3 write-path (phiếu vào Clinical Release → `commissioning_date == nowdate()`, != NULL); TC-04-34 idempotent (set sẵn `commissioning_date` tháng trước → 2nd write-path KHÔNG ghi đè); TC-04-35 **BUG CHÍNH (RED-prove)**: phiếu Clinical Release `commissioning_date` tháng-TRƯỚC nhưng `modified` HÔM NAY (edit note) → `released_this_month` KHÔNG đếm (chứng minh re-anchor khỏi `modified`); TC-04-36 SoT card==count cùng cửa sổ (`released_this_month == count({Clinical Release, docstatus=1, commissioning_date ∈ [first_day, today]})`); TC-04-37 NULL-safe legacy (`commissioning_date` NULL → loại khỏi count, KHÔNG crash); TC-04-38 BVA biên tháng (`commissioning_date == first_day` in, `== last_day_prev_month` out, `== today` in) | ✅ Live — `tests/test_imm04_commissioning_date_kpi.py` (12 test: helper unit stamp/idempotent/noop + KPI in-month/exclude-last-month-edited/NULL-safe/card==drill/anchor-DELTA + 3-path wiring grep-guard + no-`modified` guard). RED-proven: code cũ FAIL 3 (KPI modified anchor + card!=drill + grep). |

> **TC-04-30..32 (SoT overdue — vòng 32):** assert đo được trên data-live: tạo N phiếu `reception_date` vượt 30 ngày ở các state non-terminal + vài phiếu terminal/cancelled (không tính) → `overdue_sla` == số dòng `list_commissioning({overdue:1})`. Verify đổi anchor: phiếu có `expected_installation_date` quá hạn nhưng `reception_date` còn hạn → KHÔNG tính (chứng minh đã hợp nhất về `reception_date`). Verify `OVERDUE_DAYS` là constant (monkeypatch `=0` → mọi phiếu non-terminal tính overdue).

> **TC-04-33..38 (SoT commissioning-date / "Bàn giao tháng này" — vòng 16, BR-04-11):** RED-prove TC-04-35 TRƯỚC fix: seed 1 phiếu `workflow_state=Clinical Release, docstatus=1, commissioning_date=` ngày tháng-trước, rồi `.save()` để `modified=hôm nay` → code cũ (`modified >= first_day`) đếm phiếu này = +1 SAI; sau fix (`commissioning_date BETWEEN`) = 0 ĐÚNG. Stamp test (TC-04-33) chạy 3 write-path riêng: (a) `transition_state` action→Clinical Release, (b) phiếu sẵn Clinical Release → `submit_commissioning`, (c) `approve_clinical_release` — mỗi path assert `frappe.db.get_value(_DT, name, 'commissioning_date') == nowdate()`. Idempotency (TC-04-34): set `commissioning_date` = mốc cũ trước khi chạy write-path thứ 2 → giá trị bất biến. NULL-safe (TC-04-37): seed phiếu Clinical Release docstatus=1 với `commissioning_date=None` → `get_dashboard_stats()` KHÔNG raise + phiếu này KHÔNG vào `released_this_month`. Fixture tự-purge (đồng pattern test_imm04 hiện hữu); KHÔNG để leak Asset (mint asset trên Clinical Release → cleanup `final_asset`). Module test: `test_imm04` + `test_dashboard` + `test_workflows` no-regression.

## III.3. Integration — DocType lifecycle

File: `tests/test_asset_commissioning_doctype.py` (⬜ Planned). Cover hook `before_insert / validate / on_submit / on_cancel`.

| Test | Setup | Action | Assert | Kỹ thuật |
|---|---|---|---|---|
| `test_before_insert_populates_mandatory_docs` | Item Class C | `doc.insert()` | `commissioning_documents` có CO+CQ+Manual+License | EP |
| `test_class_b_no_license_row` | Item Class B | `doc.insert()` | không có row License | EP |
| `test_validate_blocks_future_reception_date` | reception_date = tomorrow | `doc.insert()` | ValidationError | BVA |
| `test_vr01_duplicate_serial` | Asset có SN tồn tại | nhập same SN → save | ValidationError chứa "VR-01" | EP |
| `test_on_submit_mints_asset` | all gates pass, board_approver set | `doc.submit()` | Asset tạo, `final_asset != None` | Use Case |
| `test_on_cancel_blocked_if_asset_exists` | final_asset populated | `doc.cancel()` | ValidationError "đã được kích hoạt" | EP |
| `test_clinical_hold_auto_on_class_c` | risk_class=C, baseline all Pass | G03 pass action | workflow_state = "Clinical Hold" | Decision Table |

## III.4. Integration — Workflow transitions

File: `tests/test_imm04_workflow.py` (⬜ Planned). Workflow `imm_04_workflow.json` có **11 state, 23 transition** (đếm: `python3 -c "import json;print(len(json.load(open('assetcore/assetcore/workflow/imm_04_workflow.json'))['transitions']))"` = 23). Phải cover 100%.

| Action | From → To | Role required | Test pass | Test fail |
|---|---|---|---|---|
| Gửi kiểm tra tài liệu | Draft → Pending Doc Verify | PM User / AssetCore Super Admin | ☐ | wrong role ☐ |
| Xác nhận đủ tài liệu | Pending Doc Verify → To Be Installed | PM User | ☐ | G01 not met ☐ |
| Yêu cầu bổ sung tài liệu | Pending Doc Verify → Draft | PM User | ☐ | |
| Bắt đầu lắp đặt | To Be Installed → Installing | PM User | ☐ | |
| Báo cáo sự cố | To Be Installed → Non Conformance | PM User / Vendor Engineer | ☐ | |
| Lắp đặt hoàn thành | Installing → Identification | PM User / Vendor Engineer | ☐ | |
| Báo cáo DOA | Installing → Non Conformance | PM User / Vendor Engineer | ☐ | |
| Bắt đầu kiểm tra | Identification → Initial Inspection | PM User | ☐ | VR-01 not set ☐ |
| Phê duyệt phát hành | Initial Inspection → Clinical Release | System Manager / AssetCore Super Admin | ☐ | G05 NC open / G06 no approver ☐ |
| Giữ lâm sàng | Initial Inspection → Clinical Hold | Compliance Manager / AssetCore Super Admin | ☐ | |
| Báo cáo lỗi baseline | Initial Inspection → Re Inspection | PM User | ☐ | |
| Gỡ giữ lâm sàng | Clinical Hold → Clinical Release | Compliance Manager / AssetCore Super Admin | ☐ | no license ☐ |
| Phê duyệt sau tái kiểm | Re Inspection → Clinical Release | System Manager / AssetCore Super Admin | ☐ | G03 still failing ☐ |
| Khắc phục xong | Non Conformance → To Be Installed | PM User | ☐ | |
| Trả lại nhà cung cấp | Non Conformance → Return To Vendor (terminal) | System Manager | ☐ | |

> 23 transition vật lý = 15 action logic × (role variants). Mỗi action có ≥ 1 test pass + 1 test fail (wrong role hoặc gate fail). State Transition Testing — vẽ state graph; mỗi edge = 1 pass + 1 fail.

## III.5. Integration — Audit chain integrity

File: `tests/test_imm04_audit.py` (một phần đã có trong `test_imm04.py::TestRC05AuditTrailNotEmpty` ✅ Live).
- (a) Sau N transition, mỗi lần `log_lifecycle_event` ghi 1 row `IMM Audit Trail` + 1 `lifecycle_events` child — verify chain end-to-end.
- (b) Tamper: sửa `lifecycle_events` child row → `_vr06_immutable_lifecycle_events` raise (⬜ Planned `TestVR06Immutability`).

→ 04 Backend §Audit Trail · `IMM Audit Trail` DocType · `utils/lifecycle.py`.

## III.6. API test

File: `tests/test_imm04_api.py` (⬜ Planned). Cover happy + envelope `success=true`, invalid params → `code=VALIDATION`, no permission → HTTP 403, idempotent retry.

| Test | Endpoint | Verify | Kỹ thuật |
|---|---|---|---|
| `test_list_default_pagination` | `list_commissioning` | page=1, page_size=20, total ≥ 0 | Use Case |
| `test_get_not_found` | `get_form_context?name=FAKE` | `success=false`, `code=NOT_FOUND` | EP |
| `test_create_happy` | `create_commissioning` | `success=true`, name khớp `ACC-\d{2}-\d{2}-\d{5}` | Use Case |
| `test_create_no_po` | `create_commissioning` (no po_reference) | `code=VALIDATION` | EP |
| `test_create_no_permission` | `create_commissioning` (low-role) | HTTP 403 | EP (permission partition) |
| `test_assign_identification_duplicate_sn` | `assign_identification` SN trùng | `code=VALIDATION` chứa "VR-01" | EP |
| `test_submit_documents_g01_block` | `transition_state` CO Pending | `code=VALIDATION` chứa "G01" | Decision Table |
| `test_approve_clinical_release_no_approver` | `approve_clinical_release` no board_approver | `code=VALIDATION` chứa "G06" | EP |
| `test_approve_clinical_release_nc_open` | `approve_clinical_release` với NC open | `code=VALIDATION` chứa "G05" | Decision Table |
| `test_approve_clinical_release_happy` | `approve_clinical_release` all pass | `success=true`, Asset tạo | Use Case |
| `test_check_sn_unique` | `check_sn_unique?vendor_sn=...` | trả `unique` đúng | EP |
| `test_get_dashboard_stats` | `get_dashboard_stats` | fields KPI hợp lệ | Use Case |
| `test_idempotent_submit` | `submit_commissioning` 2 lần | 2nd call → `code=BAD_STATE` | Error guessing |
| `test_barcode_lookup` | `get_barcode_lookup?barcode=...` | trả asset_ref đúng | Use Case |

### III.6.a — `TestGenerateQrLabelDeepLink` — dedup QR commissioning→asset (vòng 13 / ADR-001 §D6.1)

File: `tests/test_imm04.py` (class MỚI `TestGenerateQrLabelDeepLink`). RED trước (TDD). Verify `generate_qr_label` ủy quyền deep-link asset + bỏ `scan_url` desk + không double-emit.

| Test | Tình huống | Verify |
|---|---|---|
| `test_qr_url_present_when_final_asset` | Phiếu đã Clinical Release (có `final_asset` mang `qr_token`) | `res["qr_url"]` = chuỗi tuyệt đối kết thúc `/a/<token>`; token == `AC Asset.qr_token` của `final_asset`; `res` KHÔNG còn key `scan_url` |
| `test_qr_url_uses_shared_helper` | Patch `imm00.ensure_asset_qr_token` + `_build_qr_url` | `generate_qr_label` GỌI 2 helper đó (dedup THẬT — không tái hiện CSPRNG/`get_url` trong imm04); `qr_url` == giá trị helper trả |
| `test_qr_url_null_when_no_final_asset` | Phiếu chưa mint asset (`final_asset` rỗng, đã qua Identification → có `internal_tag_qr`) | `res["qr_url"] is None`; KHÔNG raise; `ensure_asset_qr_token` KHÔNG được gọi; `res["qr_value"] == internal_tag_qr` (fallback) |
| `test_no_double_emit_qr_generated` | `final_asset` đã có `qr_token` (đã emit ở mint/backfill) | Gọi `generate_qr_label` KHÔNG tạo thêm ALE `qr_generated` (count trước == sau) |
| `test_emit_once_when_asset_token_less` | `final_asset` tồn tại nhưng `qr_token` rỗng (legacy) | `generate_qr_label` → token sinh 1 lần + ĐÚNG 1 ALE `qr_generated`; gọi lần 2 → KHÔNG thêm event (idempotent) |
| `test_no_label_printed_emitted` | Bất kỳ | `generate_qr_label` (GET preview) KHÔNG tạo ALE `label_printed` (đó là `mark_label_printed`) |
| `test_rbac_unchanged_forbidden` | User không có read trên `Asset Commissioning` | `ServiceError(FORBIDDEN)` — gate giữ nguyên |
| `test_bad_state_no_internal_tag_qr` | Phiếu chưa qua Identification (`internal_tag_qr` rỗng) | `ServiceError(INVALID_PARAMS)` "Phiếu chưa có mã QR nội bộ" — không đổi |
| `test_internal_tag_qr_field_intact` | Sau dedup | `Asset Commissioning.internal_tag_qr` vẫn read-only + `get_barcode_lookup(internal_tag_qr)` vẫn resolve đúng (scanner-wedge không vỡ) |

**Baseline GIỮ XANH:** `test_imm00` (108+ test — `ensure_asset_qr_token`/`_build_qr_url` không đổi behavior), `test_imm04` (39 commissioning), `test_workflows`, `test_dashboard`.

**FE (vitest):** `frontend/src/components/commissioning/QRLabel.test.ts` — case deep-link:
- `encode_qr_url_when_present`: mock `generateQrLabel` trả `qr_url=/a/TOKEN` → `QRCode.toDataURL` gọi với `/a/TOKEN` (KHÔNG phải `qr_value`).
- `fallback_qr_value_when_url_empty`: `qr_url=null` → encode `qr_value` (tag); nhãn vẫn render, không lỗi.
- Type-check `vue-tsc` 0 error sau khi `QrLabelData` đổi (`+qr_url?`, `−scan_url`).

## III.7. E2E browser (Playwright)

Dùng cho flow UI khó cover bằng API: PO cascade auto-fill, modal NC/DOA confirm, workflow button visibility theo role, QR scan. → `assetcore-test` skill Phần 2 (Playwright MCP recipes + R-1..R-9 data rules). Golden scenario: Tạo từ PO → upload docs → G01 → lắp đặt → Identification (QR) → baseline → G03 → Clinical Release → verify Asset.

## III.8. Performance test

| Metric | Target | Method |
|---|---|---|
| `list_commissioning` p95 (200 row) | ≤ 800 ms | k6 ramping 20 VU |
| `create_commissioning` p95 | ≤ 1.5 s | k6 POST batch |
| `approve_clinical_release` full flow p95 | ≤ 3 s | k6 (tạo Asset + IMM-05 docs) |
| `check_commissioning_overdue` (200 open) | ≤ 30 s | `time bench execute …` |
| List view FE render (100 row) | ≤ 1 s DOMContentLoaded | Lighthouse / Playwright |

## III.9. Test data & Fixtures

| Loại | Cách seed | File |
|---|---|---|
| Master data (Device Model, Vendor, PO) | `fixtures/*.json` qua `bench migrate` + UAT script | `assetcore/fixtures/` |
| Item (Device Models) — Class B/C/D/Radiation | UAT seed | `scripts/uat/uat_imm04.py` |
| Asset Commissioning (5 record, mỗi state) | UAT seed | `scripts/uat/uat_imm04.py` |
| Commissioning Checklist Template (2: Imaging, Life Support) | UAT seed | `scripts/uat/uat_imm04.py` |

UAT data dùng tên bệnh viện VN, mã NCC chuẩn. Backend test fixture mới dùng prefix `_Test` (→ `assetcore-test` R-0/R-1). Reset: `bench --site assetcore.local execute assetcore.scripts.uat.uat_imm04.seed_data`.

## III.10. Run commands & Coverage gate

```bash
# Module test
bench --site assetcore.local run-tests --app assetcore --module assetcore.tests.test_imm04
# Coverage
coverage run -m unittest assetcore.tests.test_imm04 && coverage report
# Full suite (CI)
bench --site assetcore.local run-tests --app assetcore --coverage
```

| Layer | Target coverage | Đo |
|---|---|---|
| Service (`services/imm04.py`) | ≥ 85% line + ≥ 80% branch | `coverage --branch` |
| DocType lifecycle | ≥ 70% | `coverage report` |
| API (`api/imm04.py`) | ≥ 60% | `coverage report` |
| Frontend (vue-tsc) | 0 error | `npm run build` |

CI fail nếu coverage < target hoặc bất kỳ test nào fail.

---

# Phần IV — Traceability Matrices

> Mọi test ở Phần III phải xuất hiện ở cả 3 bảng.

## IV.1. US → Test mapping

| US ID | AC | Test ID (III.x) | Layer | Status |
|---|---|---|---|---|
| US-04-01 | AC-01, AC-02 | `TestInitializeCommissioning`; `test_create_happy` | Unit + API | ⬜ Planned |
| US-04-02 | AC-01, AC-02 | `TestVR01UniqueSerial::test_new_sn_passes`; `test_assign_identification_duplicate_sn` | Unit + API | ✅ Live (unit) / ⬜ Planned (API) |
| US-04-03 | G01 | `TestGateG01` (8 cases) | Unit | ✅ Live |
| US-04-04 | G03 | `TestGateG03` (4 cases) | Unit | ✅ Live |
| US-04-05 | VR-07 | `TestVR07ClinicalHold` (6 cases) | Unit | ✅ Live |
| US-04-06 | G05/G06 | `TestGateG05G06`; `TestRC06AssetAutoMint` | Unit | ✅ Live |
| US-04-07 | G06 approver | `TestGateG05G06::test_no_approver_blocks`; `TestAUTH05FourEyes` | Unit | ✅ Live |
| US-04-08 | DOA | `test_on_submit_mints_asset` neg path; DOA workflow | Integration | ⬜ Planned |

## IV.2. BR → Test mapping

| BR ID | Phát biểu (rút gọn) | Test ID | Kỹ thuật | Happy / Negative |
|---|---|---|---|---|
| BR-04-01 | Asset chỉ tạo qua on_submit | `TestRC06AssetAutoMint`; `test_on_submit_mints_asset` | Use Case | 1 / 1 |
| BR-04-02 (G01) | Mandatory docs Received/Waived | `TestGateG01` | Decision Table | 4 / 4 ✅ |
| BR-04-03 (VR-01) | SN unique | `TestVR01UniqueSerial` | EP | 1 / 1 (DB-neg ⬜) |
| BR-04-04 (G03) | 100% baseline Pass/N/A | `TestGateG03` | Decision Table | 2 / 2 ✅ |
| BR-04-05 (VR-07) | Class C/D/Radiation → Hold | `TestVR07ClinicalHold` | Decision Table | 3 / 3 ✅ |
| BR-04-06 (G05) | No Open NC trước Release | `TestGateG05G06` | Decision Table | 1 / 1 |
| BR-04-07 (G06) | board_approver bắt buộc | `TestGateG05G06::test_no_approver_blocks` | EP | 1 / 1 ✅ |
| BR-04-08 (GW-2) | CN ĐK lưu hành Active/Exempt | `TestDocumentExpiry` | Decision Table | ⬜ Planned |
| BR-04-10 | Overdue SoT drillable (anchor `reception_date`, `OVERDUE_DAYS=30`, KPI==drill) | `TestOverdueSoT` (TC-04-30..32) | Invariant + EP | 2 / 1 ⬜ Planned |
| BR-04-11 | Stamp `commissioning_date` tại Clinical Release (idempotent) + KPI `released_this_month` re-anchor `modified`→`commissioning_date` (card==count cùng cửa sổ tháng) | `tests/test_imm04_commissioning_date_kpi.py` (12 test) + FE `commissioningKpi.test.ts` (8) | Invariant + EP + BVA + idempotency | ✅ Done (BE 12 + FE 8 GREEN; no-regression test_imm04 39 / test_workflows 8 / test_dashboard 55; vue-tsc 0) |

## IV.3. Component → Test mapping

| Component (I.1) | Test ID | Test layer | Coverage % | Risk priority (I.3) |
|---|---|---|---|---|
| `validate_gate_g01` | `TestGateG01` | Unit | *(Cần khảo sát)* | Critical |
| `validate_gate_g05_g06` | `TestGateG05G06` | Unit | *(Cần khảo sát)* | Critical |
| `create_ac_asset` | `TestRC06AssetAutoMint` | Unit | *(Cần khảo sát)* | Critical |
| `validate_gate_g03` | `TestGateG03` | Unit | *(Cần khảo sát)* | High |
| `check_auto_clinical_hold` | `TestVR07ClinicalHold` | Unit | *(Cần khảo sát)* | High |
| `_vr01_unique_serial_number` | `TestVR01UniqueSerial` | Unit | *(Cần khảo sát)* | High |
| `log_lifecycle_event` | `TestLogLifecycleEvent`, `TestRC05AuditTrailNotEmpty` | Unit + Integration | *(Cần khảo sát)* | High |
| `_vr06_immutable_lifecycle_events` | `TestVR06Immutability` | Unit | ⬜ Planned | High |
| `api/imm04.py` endpoints | `test_imm04_api.py` | API | ⬜ target ≥ 60% | High |

---

# Phần V — UAT Script

## V.1. Phạm vi UAT

- **In-scope**: Tạo từ PO (BR-04-01) · G01 mandatory docs (BR-04-02) · VR-01 SN unique (BR-04-03) · G03 baseline (BR-04-04) · VR-07 auto Clinical Hold (BR-04-05) · G05/G06 (BR-04-06,07) · GW-2 IMM-05 compliance (BR-04-08) · audit immutability (VR-06) · auto-mint Asset + downstream · Dashboard KPIs · phân quyền role.
- **Out-of-scope**: Load testing (Phần III.8), penetration testing (Phần VI.10), PDF print format.
- **Pre-condition**: site UAT `uat.assetcore.vn` deploy bản mới nhất; `uat_imm04.py seed_data` chạy thành công; 7 tester account active; Chrome ≥ 120.

## V.2. Tester accounts

| Username | Email | Role | Vai trò UAT |
|---|---|---|---|
| `tbyt.le` | tbyt.le@hospital.vn | Commissioning User | Tạo phiếu từ PO, ghi nhận nhận hàng |
| `biomed.nguyen` | biomed.nguyen@hospital.vn | Commissioning User | Lắp đặt, gán SN, đo baseline |
| `vendor.tech` | vendor.tech@philips.com | Vendor Engineer | Xác nhận lắp đặt, báo DOA |
| `qa.pham` | qa.pham@hospital.vn | Compliance Manager | Clinical Hold, upload license, gỡ Hold |
| `ws.manager` | ws.manager@hospital.vn | Commissioning Manager | Submit/Cancel/Amend phiếu |
| `ceo.nguyen` | ceo.nguyen@hospital.vn | System Manager | Board approver phê duyệt phát hành |
| `cmms.admin` | cmms.admin@hospital.vn | AssetCore Super Admin | Override khi cần; verify immutability |

Phải có account role thấp (`Commissioning User`, `AssetCore System User`) để cover FORBIDDEN case. Mật khẩu UAT: `Assetcore@2026` (reset sau UAT).

## V.3. Test data đã seed

| DocType | Số lượng | Ghi chú |
|---|---|---|
| Item (Device Model) | 4 | Class B (pump), C (X-ray), D (ventilator), Radiation (LINAC) |
| Purchase Order | 3 | PO-2026-00023/24/25 |
| Asset Commissioning | 5 | Draft, Pending Doc Verify, Clinical Hold, Non Conformance, tiền-Release |
| Commissioning Checklist Template | 2 | Medical Imaging (6 item), Life Support (5 item) |
| Test users | 7 | Đủ role theo V.2 |

## V.4. UAT Scenarios — Suy ra từ US + Activity

Mỗi scenario theo template Phụ lục A, ID `UAT-IMM-04-NN`. Quy tắc suy: mỗi US → ≥ 1 happy; mỗi Activity branch ngoại lệ → ≥ 1; mỗi role mutate → ≥ 1 permission verify; mỗi workflow terminal → ≥ 1 audit verify; mỗi BR Critical → ≥ 1 negative.

| ID | Actor | Pre-condition | US/BR cover | Kỹ thuật | Kết quả mong đợi |
|---|---|---|---|---|---|
| UAT-IMM-04-01 | Commissioning User | PO-2026-00023 (X-ray Class C) tồn tại | US-04-01, BR-04-01 | Use Case happy | Phiếu ACC-YY-MM-#####, 4 row docs Pending (CO/CQ/Manual/License), event Draft |
| UAT-IMM-04-02 | Commissioning User | Item có category TTBYT | BR-04-01 negative | Use Case alt | Tạo Asset ERPNext trực tiếp bị chặn "phải tạo qua IMM-04" |
| UAT-IMM-04-03 | Commissioning User | Pending Doc Verify, CO=Pending | US-04-03, BR-04-02 | Decision Table | G01 block "Còn thiếu: CO"; sau khi Received → To Be Installed |
| UAT-IMM-04-04 | Commissioning User | Identification, SN trùng | US-04-02, BR-04-03 | EP | Inline error VR-01; SN mới → QR sinh, → Initial Inspection |
| UAT-IMM-04-05 | Commissioning User | Initial Inspection, 1 critical Fail | US-04-04, BR-04-04 | Decision Table | G03 block; status → Re Inspection; checklist read-only |
| UAT-IMM-04-06 | Commissioning User + Compliance Manager | Class C, baseline all Pass | US-04-05, BR-04-05, VR-07 | Decision Table | Auto Clinical Hold; QA upload license → Gỡ Hold → Clinical Release |
| UAT-IMM-04-07 | System Manager | Clinical Release pending, NC Open | US-04-06, BR-04-06 | Decision Table | G05 block "Còn 1 NC chưa đóng"; đóng NC → phê duyệt OK |
| UAT-IMM-04-08 | System Manager | Class B, all gates pass, board_approver set | US-04-06, BR-04-07/08 | Use Case happy | Asset mint, `final_asset` set, ≥ 3 IMM-05 Asset Document, event `released` |
| UAT-IMM-04-09 | Vendor Engineer + Commissioning Manager | Installing | US-04-08, BR-04-06 | State Transition | DOA → Non Conformance → Return To Vendor (terminal), không tạo Asset |
| UAT-IMM-04-10 | AssetCore Super Admin | Phiếu có ≥ 2 lifecycle event | VR-06 | Error guessing | Sửa event raise "VR-06"; timeline read-only |
| UAT-IMM-04-11 | Nhiều role | — | Security VI.1 | EP permission | `tbyt.le` gọi `approve_clinical_release` → 403; vendor gán Internal Tag → 403 |
| UAT-IMM-04-12 | Commissioning Manager | Dashboard | Functional §Dashboard | Use Case | KPI "Phiếu đang mở", "Quá hạn > 30 ngày" đúng; click card → list filter |

> Chi tiết step-by-step của 12 scenario giữ nguyên ở phiên bản v2 UAT (`scripts/uat/uat_imm04.py` + checklist nội bộ); template chi tiết per scenario ở Phụ lục A.

## V.5. Tổng hợp kết quả & Bug found

| Scenario | Status | Tester | Ngày | Ghi chú |
|---|---|---|---|---|
| UAT-IMM-04-01 … 12 | ☐ Pass / ☐ Fail / ☐ Block | | | điền khi chạy UAT |

**Bug log (đã biết)**:

| Issue ID | Severity | Mô tả | Fix status |
|---|---|---|---|
| IMM04-BUG-032 | Major | PM auto-create sau Clinical Release chưa có listener ở IMM-08 | Known — deferred IMM-08 Wave 2 (có workaround) |
| IMM04-BUG-033 | Minor | PDF Print Format Biên bản Bàn giao chưa config | Known — deferred |

**Acceptance**: ≥ 95% PASS, Blocker = 0, Major ≤ 2 (có workaround documented).

**Sign-off UAT**:

| Vai trò | Người | Ngày | Chữ ký |
|---|---|---|---|
| BA Lead | | | |
| QA Lead | | | |
| Module Owner (IMM-04) | | | |
| Đại diện end-user (HTM Officer) | | | |

---

# Phần VI — Security Review (gate)

## VI.1. RBAC

- **Role definitions**: `fixtures/role.json` + `role_profile.json`. Role thực gắn DocPerm `Asset Commissioning`: AssetCore Super Admin, Commissioning Manager, Commissioning User, AssetCore Auditor, AssetCore System User (+ Vendor Engineer, Compliance Manager, System Manager ở workflow transition).

**DocPerm matrix — `Asset Commissioning`** (verify từ `asset_commissioning.json`):

| Role | Read | Write | Create | Submit | Cancel | Amend |
|---|---|---|---|---|---|---|
| AssetCore Super Admin | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Commissioning Manager | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Commissioning User | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| AssetCore Auditor | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| AssetCore System User | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |

> Phân quyền theo state (Vendor Engineer chỉ Installing/To Be Installed; Compliance Manager chỉ Clinical Hold) thực thi qua **workflow transition `allowed`** (→ III.4), không phải DocPerm tĩnh.

- **Field-level permission**: `board_approver`, `approval_remarks`, `final_asset`, child `lifecycle_events` **đề xuất** permlevel ≠ 0. *(Cần khảo sát — hiện `asset_commissioning.json` chưa có field permlevel ≠ 0; đây là gap security cần đóng trước go-live.)*
- **User Permission (row-level)**: `permission_query_conditions` trong `assetcore/permissions.py`; single-hospital hiện không filter row, multi-tenant cần filter theo hospital.

**Kỹ thuật**: Decision Table — mỗi (role × action × state) = 1 row, expected Allow/Deny.

## VI.2. API security

- **Whitelist hygiene**: 35 `@frappe.whitelist` trong `api/imm04.py`; mọi mutating endpoint dùng `methods=["POST"]`. Mỗi endpoint cần docstring + role check + validate input. *(Cần khảo sát: rà soát từng endpoint có `rbac.require()`.)*
- **CSRF**: Frappe default `X-Frappe-CSRF-Token`.
- **Input validation**: Link field (po_reference, master_item) validate qua `frappe.get_value` / `get_po_details` trước khi dùng.
- **SQL injection**: Frappe ORM parameterized; không f-string vào raw SQL trong `imm04.py`.
- **Rate limit**: ⚠️ Roadmap — cần config cho `approve_clinical_release`, `create_commissioning`.

## VI.3. Audit trail integrity

Mọi state change sinh row `lifecycle_events` qua `log_lifecycle_event()` + ghi `IMM Audit Trail` global (`utils/lifecycle.py`). `_vr06_immutable_lifecycle_events` block edit. Verify tamper: `test_imm04.py::TestRC05AuditTrailNotEmpty` ✅ + `TestVR06Immutability` ⬜. User KHÔNG được edit/delete audit (ISO 13485:7.5.9). Retention ≥ 5 năm theo NĐ98/2021/NĐ-CP. → III.5.

## VI.4. Authentication & session

| Hạng mục | Config |
|---|---|
| Login | Frappe default username + password |
| Session timeout | 8 giờ (`frappe.conf.session_expiry`) |
| Lockout | Frappe default: 3 lần fail → lock 15 phút |
| Password policy | ≥ 8 ký tự, 1 hoa, 1 số |
| API key | Per-user, rotate 90 ngày |
| 2FA | Roadmap Phase 2 — TOTP via Frappe 2FA |

## VI.5. Data sensitivity

| Loại | Trường | Sensitivity | Bảo vệ |
|---|---|---|---|
| Serial thiết bị | `vendor_serial_no`, `internal_tag` | Internal | Role permission |
| Phê duyệt BGĐ | `board_approver`, `approval_remarks` | Confidential | permlevel ≠ 0 (đề xuất — xem VI.1) |
| Thông tin vendor | `vendor`, `po_reference` | Internal | Role permission |
| Giấy phép BYT | `commissioning_documents` row License | Confidential | Role permission |
| Dữ liệu bệnh nhân | Không lưu | N/A | AssetCore KHÔNG lưu patient data |

## VI.6. Vendor isolation

`Vendor Engineer` chỉ: edit/transition khi state `Installing` hoặc `To Be Installed` (action "Lắp đặt hoàn thành", "Báo cáo sự cố", "Báo cáo DOA" — III.4). KHÔNG thấy `board_approver`, `approval_remarks`, giá trị PO, audit trail vendor khác. KHÔNG export bulk, không print. → test ở III.6 (low-role API call). Thực thi chính qua workflow `allowed` + `permission_query_conditions`.

## VI.7. Secrets management

`site_config.json` không commit (`.gitignore`). External token (email/SMS) lưu `frappe.conf`, không hardcode. Backup encrypt at-rest off-site (→ 08 Deployment). Secret scan CI: `detect-secrets` pre-commit hook.

## VI.8. Logging & monitoring

| Sự kiện | Log level | Where | Alert? |
|---|---|---|---|
| Clinical Release thành công | INFO | IMM Audit Trail | ✅ Email Purchase User |
| Commissioning overdue > 30 ngày | WARNING | Scheduler log | ✅ Email Commissioning Manager |
| Cancel blocked (Asset exists) | WARNING | `frappe.log_error` | ❌ |
| API 4xx (permission denied) | INFO | Frappe access log | ❌ |
| Login fail | INFO | Frappe login log | ✅ (sau 3 lần) |
| Audit tamper attempt | ERROR | `frappe.log_error` | ✅ Email Super Admin |

PII / token KHÔNG vào log.

## VI.9. Threat model (STRIDE-lite)

| Threat | Vector | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| **S**poofing | Giả mạo session Commissioning User | Low | High | Session HttpOnly + SameSite; Frappe session verify |
| **T**ampering | Sửa `lifecycle_events` child row | Low | Critical | `_vr06_immutable_lifecycle_events` + permlevel (đề xuất) |
| **R**epudiation | Vendor phủ nhận đã lắp đặt | Low | Medium | `lifecycle_events` ghi actor + timestamp immutable |
| **I**nfo disclosure | Vendor thấy giá trị PO / board_approver | Low | Medium | Workflow `allowed` restriction + field permlevel (đề xuất) |
| **D**enial of service | Scheduler quét 10k+ commissioning | Low | Medium | Index `workflow_state + reception_date`; batch 200/run |
| **E**levation of privilege | Commissioning User tự Submit/approve | Low | High | DocPerm submit=0; workflow `allowed` = System Manager/Super Admin only |

## VI.10. Penetration test

Trước go-live bệnh viện đầu tiên: Burp/OWASP ZAP scan `uat.assetcore.vn` (0 High/Critical); sqlmap safe-mode trên `create_commissioning`, `approve_clinical_release`; CSRF test (curl no token); role escalation (`approve_clinical_release` với Commissioning User → 403). Report lưu `docs/security/pentest_imm04_v1.md`.

## VI.11. Sign-off

| Role | Người | Ngày | Quyết định |
|---|---|---|---|
| QA Lead | | | ☐ Pass / ☐ Pass with conditions / ☐ Fail |
| Tech Lead | | | ☐ Pass / ☐ Pass with conditions / ☐ Fail |
| Module Owner | | | ☐ Pass / ☐ Pass with conditions / ☐ Fail |

**Điều kiện go-live**: tất cả Sign-off Pass hoặc Pass with conditions (workaround documented).

---

# Phần VII — Code Quality

## VII.1. Tool matrix

| Tool | Mục tiêu | Target | Cadence |
|---|---|---|---|
| **SonarQube** (BE Python) | Bug 0 Critical, code smell ≤ 5, duplication ≤ 3%, coverage ≥ 70%, security hotspot review 100% | Quality Gate pass | Mỗi PR (CI gate) |
| **Lighthouse** (FE — Commissioning views) | Performance ≥ 90, Accessibility ≥ 95, Best Practices ≥ 90, SEO ≥ 80 | ≥ target | Mỗi release + monthly |
| **ESLint + vue-tsc** | 0 error, 0 warning prod build | pass | Mỗi PR FE (CI gate) |
| **ruff / black** (BE) | 0 error, format PEP8 | pass | Mỗi PR (CI gate) |
| **Bundle size** (FE chunk imm04) | main ≤ 250 KB gzip, async ≤ 80 KB gzip | ≤ budget | Mỗi PR FE (CI report) |

## VII.2. Cadence

- SonarQube: mỗi PR (CI gate, fail nếu Quality Gate fail)
- Lighthouse: mỗi release lớn + monthly audit
- ESLint / ruff: mỗi PR (CI gate)
- Bundle size: mỗi PR FE (CI report, fail nếu vượt budget)

Gắn screenshot SonarQube + Lighthouse vào file 09 §Release Notes khi báo cáo final.

---

# Phụ lục A — Template per UAT scenario

```markdown
### UAT-IMM-04-<NN> — <Tên>

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
### TC-IMM-04-<LAYER>-<NN> — <Tên>

**Component (I.1)**: <…>
**Liên kết**: US-<NN> | BR-<NN> | ACT-<NN>
**Kỹ thuật (II.1/II.2)**: BVA boundary `reception_date = today + 1`
**Priority (I.3)**: Critical / High / Medium / Low
**Test type**: Unit / Integration / API / E2E
**Pre-condition**: <fixture / state setup>

**Input**:
- <field>: <value>

**Steps**:
1. <…>
2. <…>

**Expected**:
- ServiceError(code=VALIDATION, message contains "VR-01")
- doc.workflow_state unchanged

**Post-condition**: <DB rollback / fixture cleanup>
```

# Phụ lục C — Workflow State Transition Test template

```markdown
### TC-IMM-04-WF-<NN> — <action>: <from> → <to>

**Workflow JSON**: `assetcore/assetcore/workflow/imm_04_workflow.json`
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
- [x] Test class structure cho mọi service public function (I.1)
- [x] ≥ 1 happy + 1 negative test mỗi gate/VR (một phần ✅ Live, một phần ⬜ Planned)
- [x] Workflow transitions liệt kê 100% (23 = JSON)
- [x] Audit chain test (intact ✅ Live, tampered ⬜ Planned)
- [x] API test plan ≥ 60% target + permission matrix
- [x] Performance target xác định
- [x] CI command chạy clean (`bench run-tests --module assetcore.tests.test_imm04`)
- [ ] **SonarQube Quality Gate pass** + **Lighthouse score ≥ target** — chưa chạy report thực tế

## IV. Traceability
- [x] IV.1 US → Test: mọi US có ≥ 1 Test ID
- [x] IV.2 BR → Test: mọi BR có happy + negative (BR-04-08 ⬜ Planned)
- [ ] IV.3 Component → Test: coverage % thực tế chưa đo (`*(Cần khảo sát)*`)

## V. UAT
- [x] Mỗi US có ≥ 1 UAT scenario
- [x] ≥ 1 negative + permission + audit verify scenario
- [x] Test data seed script (`uat_imm04.py`)
- [x] Tester accounts đã liệt kê (đủ role thấp lẫn cao)
- [x] Sign-off section sẵn sàng

## VI. Security
- [x] DocPerm matrix đầy đủ (verify từ JSON, 5 role)
- [ ] Mọi field nhạy cảm có permlevel ≠ 0 — **gap**: `asset_commissioning.json` hiện chưa set permlevel (VI.1)
- [ ] SQL injection + CSRF test pass — chưa chạy pentest thực tế
- [x] Audit chain test pass (intact ✅; tampered ⬜ Planned)
- [ ] Vendor isolation test pass (low-role API call) — ⬜ Planned (III.6)
- [x] Threat model đủ 6 STRIDE với mitigation
- [ ] Sign-off đầy đủ trước go-live — chưa ký

## VII. Code Quality
- [ ] SonarQube Quality Gate pass — chưa chạy
- [ ] Lighthouse ≥ target — chưa chạy
- [ ] Bundle size ≤ budget — chưa đo
- [ ] Screenshot báo cáo gắn vào file 09 — chưa có
