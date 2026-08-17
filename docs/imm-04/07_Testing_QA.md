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
| 4 | `IMM-04 Workflow` | Workflow | `workflow/imm_04_workflow.json` (11 state, **71 transition-row → 15 cạnh distinct**) | Integration (state transition) + surface-integrity guard (§III.4a) |
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
| BR-04-12 (G06 · gỡ deadlock) | Cấp `board_approver` atomic trong `transition_state(…, board_approver=…)` khi transition CR-bound; thiếu ⇒ ServiceError `IMM04-GATE-G06-APPROVER` Decision-B (KHÔNG 417); 4-mắt `assert_distinct_signers`; non-CR ⇒ param bỏ qua | `transition_state`, `assert_distinct_signers`, MSG `IMM04_GATE_G06_APPROVER` | State Transition + EP + SoD (§III.4c) |
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

- **In-scope**: gate logic G01/G03/G05/G06 (I.1 #6), validator VR-01/05/06 (#7), workflow 71 transition-row / 15 cạnh + surface-integrity guard (#4, §III.4a), auto-mint Asset + audit chain (#5,#9), API permission matrix (#8).
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
| **State Transition Testing** | Workflow FSM | `imm_04_workflow.json` 71 transition-row / 15 cạnh (11 state) | mỗi transition + invalid |
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
          │  Workflow + DocType lifecycle  │   ~25% (11 state, 45 row / 15 cạnh)
         ─┴────────────────────────────────┴─
      ┌────────────────────────────────────────────┐
      │         Unit — Service Layer               │   ~55% (gates + VRs)
     ─┴────────────────────────────────────────────┴─
```

Mọi service function phải có test trước khi code (TDD — → CLAUDE.md §17). Mỗi gate (G01/G03/G05/G06) và validation rule có ≥ 1 happy + 1 negative test.

> **Trạng thái thực tế (2026-05-29)**: test hiện consolidate trong **một file** `assetcore/tests/imm04/test_imm04.py` (391 LOC). Các file con (`test_imm04_service.py`, `_validators.py`, `_workflow.py`, `_audit.py`, `_api.py`, `test_asset_commissioning_doctype.py`, e2e `test_imm04_golden.py`) là **kế hoạch chia file** — đánh dấu ⬜ Planned ở dưới.

## III.2. Unit test — Service Layer

File hiện tại: `assetcore/tests/imm04/test_imm04.py`. Mỗi test class trace về ≥ 1 dòng I.1.

| Test class | Function cover | Kỹ thuật | Cases | Trạng thái |
|---|---|---|---|---|
| `TestGateG01` | `validate_gate_g01` | Decision Table | 8 (all received/waived, pending mandatory, non-mandatory, skip Draft/Pending Doc Verify, incomplete flag ±note) | ✅ Live |
| `TestGateG03` | `validate_gate_g03` | Decision Table | 4 (all pass, N/A=pass, one fail blocks, skip non-release state) | ✅ Live |
| `TestGateG05G06` | `validate_gate_g05_g06` | Decision Table | 3 (no NC + approver pass, no approver blocks, skip non-release) | ✅ Live |
| `TestVR01UniqueSerial` | `_vr01_unique_serial_number` | EP + Error guessing | 2 (empty SN skip, new SN pass) | ✅ Live |
| `TestVR07ClinicalHold` | `check_auto_clinical_hold` | EP/Decision Table | 6 (A/B no hold, C/D/Radiation hold, radiation flag) | ✅ Live — ⚠️ **AC-CR-85 phải viết lại `test_radiation_class_sets_flag`** (đang assert chính side-effect bị gỡ; đo qua `gate_g04_applies` — xem §III.4f.3 bẫy 5) |
| `TestGateG04Applicability` | `gate_g04_applies` · `gate_g04_ok` · `evaluate_gate_status` · VR-07 | Decision Table + Invariant (bảng chân trị) + Mutation | **13** (ma trận A 12 ô không-suy-giảm + ma trận B 10 ô INV-G04-1 + ô gỡ deadlock phiếu THẬT + mutation-probe thường trực TC-13) | ✅ Live (AC-CR-85 — §III.4f; `test_imm04` 97 → **110 OK**) |
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

File: `tests/test_imm04_workflow.py` (⬜ Planned). Workflow `imm_04_workflow.json` có **11 state, 45 transition-row → 15 cạnh distinct** (đếm: `python3 -c "import json;print(len(json.load(open('assetcore/assetcore/workflow/imm_04_workflow.json'))['transitions']))"` = **45**; 45 row = 15 cạnh logic × role-variant). Phải cover 100%.

> ⚠️ Self-Correction (2026-07-14): số "23 transition" ở các bản trước là **stale** — sau backfill admin-override (`AssetCore Super Admin` bồi vào MỌI cạnh, memory `workflow_admin_override_rbac`), file thực tế = **45 row / 15 cạnh distinct**. Verified 2026-07-14.

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

> 45 transition-row vật lý = 15 action logic (cạnh distinct) × role-variant. Mỗi action có ≥ 1 test pass + 1 test fail (wrong role hoặc gate fail). State Transition Testing — vẽ state graph; mỗi edge = 1 pass + 1 fail.

## III.4a. Guard — Workflow-Surface Integrity (CR-WF-04-SURFACE · silent-CTA-loss)

File: `tests/test_imm04.py` → class **`TestImm04WorkflowSurfaceGuard`** (⬜ Planned, **test-only** — 0 chạm runtime `.py`, 0 reload/migrate). Khoá 4 invariant INV-04-WF-1..4 (spec: `04 §3.1` + BR-04-24 + ADR-IMM-04-01). Đóng lỗ mà guard toàn cục `test_workflow_admin_override` **KHÔNG** bắt (glob JSON, không kiểm hằng-lookup service `services/imm04.py:727`).

**Oracle độc lập:** parse file `assetcore/assetcore/workflow/imm_04_workflow.json` (JSON) + `import assetcore.services.imm04 as svc` (đọc `svc._DT`, gọi `svc._get_workflow_transitions`); assert trên workflow **live** (DB) + emit service **live**.

| TC | Invariant | Assertion (chính xác) | Bắt lỗi |
|---|---|---|---|
| **TC-04-WF-SURFACE-01** | INV-04-WF-1 | `frappe.get_doc("Workflow", "IMM-04 Workflow")` KHÔNG raise (`DoesNotExistError`); `workflow.document_type == svc._DT == "Asset Commissioning"`. | rename workflow · drift `_DT` |
| **TC-04-WF-SURFACE-02** | INV-04-WF-2 | Parse 45 transition-row → gom `{(state,action,next_state)}` = 15 cạnh distinct; **mỗi** cạnh có `"AssetCore Super Admin"` ∈ set `allowed`. `assertEqual(edges_missing_super_admin, [])`. | cạnh nghiệm thu tụt admin-override |
| **TC-04-WF-SURFACE-03** | INV-04-WF-3 | Với 1 phiếu **Draft** thật + `frappe.set_user(<AssetCore Super Admin>)`: `emit = svc._get_workflow_transitions(draft.name)`; `assertTrue(len(emit) > 0)`; `draft_out = {t.next_state for file-rows where state=="Draft"}` (`=={"Pending Doc Verify"}`); `assert {e["next_state"] for e in emit} ⊆ draft_out`. | hằng-lookup @:671 sai → `[]` (RED) · emit stale ≠ file |
| **TC-04-WF-SURFACE-04** | INV-04-WF-4 | Cùng phiếu Draft, `frappe.set_user(<role-nghèo: không role ∈ allowed cạnh Draft-out>)`: `poor = svc._get_workflow_transitions(draft.name)`; `assert {e["action"] for e in poor} ⊆ {e["action"] for e in emit_superadmin}` (subset chặt, thường `poor == []`). | false-permissive CTA (rò rỉ vượt quyền) |
| **TC-04-WF-SURFACE-05** | INV-04-WF-1/3 (coupling) | Couple file ⇄ live: `file_name = json["name"]`; `assertEqual(file_name, "IMM-04 Workflow")`; `frappe.get_doc("Workflow", file_name)` KHÔNG raise. Đổi `name` trong `imm_04_workflow.json` → `file_name` mới ∉ DB live → raise → FAIL (0 migrate). | rename `name` trong file JSON |

**RED-before / GREEN-after (chứng minh giá trị — BẮT BUỘC verify, KHÔNG false-green):**
1. **GREEN baseline:** `bench --site miyano run-tests --module assetcore.tests.imm04.test_imm04` → `Ran 62 OK` (57 cũ + 5 mới), 0 fail / 0 error.
2. **RED vector A (hằng lookup):** tạm đổi `services/imm04.py:727` `"IMM-04 Workflow"` → `"IMM-04 Workflow-X"` → chạy lại → **TC-04-WF-SURFACE-03** FAIL (`emit == []`) → revert.
3. **RED vector B (rename file):** tạm đổi `name` trong `imm_04_workflow.json` → chạy lại → **TC-04-WF-SURFACE-05** FAIL (`file_name ∉ DB live`) → revert.
4. **Đối chứng lỗ toàn cục:** với vector A hoặc B, `test_workflow_admin_override` vẫn **GREEN** (glob JSON, không kiểm hằng-lookup) → chứng minh guard module-local là cần thiết.

**Boundary (Never):** KHÔNG sửa `services/imm04.py:723-736` để test xanh. Nếu thêm `log_error` thay `return []` (observability) = thay đổi runtime → **HARD-STOP USER reload worker**, tách khỏi CR test-only này, `[ROADMAP]`.

## III.4b. Baseline verdict — chặn Pass-giả + UPSERT (BR-04-04 · silent-completion lens)

File: `tests/test_imm04.py` → class **`TestImm04BaselineVerdict`** (⬜ Planned). Spec: `04 §5.3` + BR-04-04a..d + ADR-IMM-04-02. **Flow THẬT bắt buộc** (KHÔNG shortcut set `workflow_state` trực tiếp, KHÔNG pre-seed `baseline_tests` ở `create_commissioning`): `create_commissioning(...)` **không** child `baseline_tests` → chạy các transition qua `svc.transition_state` / `apply_workflow` tới **Initial Inspection** → gọi `svc.submit_baseline_checklist(name, results)`. Re-get bằng `CommissioningRepo.get(name)` (fresh) để kiểm persist. Đây là điều kiện tái tạo bug gốc (phiếu vào Initial Inspection với `baseline_tests` rỗng).

| TC | Vế BR | Setup (flow thật) | Assertion (chính xác) | Bắt lỗi |
|---|---|---|---|---|
| **TC-04-BASELINE-01** | 04a — Pass-giả 0 đo | phiếu @Initial Inspection, `baseline_tests` rỗng | `submit_baseline_checklist(name, [])` → `assertRaises(ServiceError)` code `VALIDATION`; **re-get** `overall_inspection_result != "Pass"` (rỗng/None) | auto-Pass câm (bug gốc) |
| **TC-04-BASELINE-02** | 04b — UPSERT append + persist | phiếu @Initial Inspection, `baseline_tests` rỗng | `submit_baseline_checklist(name, [{parameter:"Leakage Current", measured_val:0.08, test_result:"Pass"}])` → success; **re-get**: `len(baseline_tests)==1`, row `parameter=="Leakage Current"` + `measured_val≈0.08` + `test_result=="Pass"` (KHÔNG drop câm) | drop-câm parameter chưa seed |
| **TC-04-BASELINE-03** | 04d — tests_recorded THỰC + Pass | như 02 nhưng 2 param Pass/N/A (1 mới append + 1 append) | return `overall_result=="Pass"` + **`tests_recorded == 2`** (số row thực ghi, KHÔNG `len(results)` mù); re-get `overall_inspection_result=="Pass"` | `tests_recorded` = len(payload) mù |
| ~~**TC-04-BASELINE-04**~~ | ~~04c — Fail~~ | — | **⛔ SUPERSEDED 2026-07-24 → TC-04-BLFAIL-01 (§III.4d).** TC cũ đòi `assertRaises(VALIDATION)` **đồng thời** đòi "row Fail vẫn persist" — **hai vế mâu thuẫn**: service raise TRƯỚC `doc.save()` nên không bao giờ persist được. Vế BR-04-04c đã bị thay bởi BR-04-04e (verdict dẫn xuất, KHÔNG raise). | mâu thuẫn nội tại của TC cũ |
| **TC-04-BASELINE-05** | Green path cũ giữ nguyên | phiếu @Initial Inspection với `baseline_tests` **seed sẵn** N row, `results` all Pass/N/A cho từng param | success `overall_result=="Pass"`, **`tests_recorded == N`** (== số row seed); re-get `overall_inspection_result=="Pass"` | regress luồng seed-sẵn |
| **TC-04-BASELINE-06** | 04a — có row nhưng 0 ghi verdict | phiếu @Initial Inspection có row seed nhưng `test_result` rỗng, `results=[]` | `assertRaises` `VALIDATION` (`tests_recorded==0`); re-get `overall_inspection_result != "Pass"` | Pass-giả biến thể (row rỗng verdict) |

**RED-before / GREEN-after (BẮT BUỘC — chứng minh test bắt bug thật):**
1. **RED:** chạy 6 TC trên code hiện tại (`services/imm04.py:1493-1512`) → TC-04-BASELINE-01/03/06 **FAIL** (bản cũ auto-Pass + không có `tests_recorded`), TC-04-BASELINE-02 **FAIL** (drop câm, `len==0`). Chứng minh test có giá trị.
2. **GREEN:** sau khi BE land `04 §5.3` → `bench --site miyano run-tests --module assetcore.tests.imm04.test_imm04` → `Ran N OK` (0 fail / 0 error), module-isolated.
3. **Guard OAS:** `grep -c '^@frappe.whitelist' api/imm04.py` bất biến (endpoint đã tồn tại) ⇒ `test_oas_baseline` (owner IMM-10 Blocker#3) KHÔNG bị đụng.

**Boundary (Never):** KHÔNG set `workflow_state` trực tiếp để bỏ qua transition (test giả); KHÔNG pre-seed `baseline_tests` ở `create_commissioning` cho TC-01..04 (phải tái tạo phiếu rỗng); KHÔNG assert `tests_recorded == len(results)` (đó chính là bug cần chặn).

## III.4c. Gỡ deadlock board_approver — 4-mắt trong transition (BR-04-12 · Self-Correction vòng 5)

File: `tests/test_imm04.py` → class **`TestImm04BoardApproverTransition`** (⬜ Planned). Spec: `04 §5.4` + BR-04-12a..e + ADR-IMM-04-03 + `05 §15`. **Flow THẬT bắt buộc** (KHÔNG shortcut set `workflow_state`): `create_commissioning(...)` → chạy transition qua `svc.transition_state` tới **Initial Inspection** với baseline 100% Pass/N/A (dùng `submit_baseline_checklist`, KHÔNG NC Open) → gọi `svc.transition_state(name, "Phê duyệt phát hành", board_approver=…)`. Re-get bằng `CommissioningRepo.get(name)` / `frappe.db.get_value` (fresh) để kiểm persist. Cần ≥2 user phân biệt cho 4-eyes: người-tạo/submit vs `board_approver`.

| TC | Vế | Kịch bản (Given → When) | Then | Bug chặn |
|---|---|---|---|---|
| **TC-04-BA-01** | 12a/12d — DEADLOCK GỠ | phiếu @Initial Inspection, baseline 100% Pass/N/A, 0 NC Open | `transition_state(name, "Phê duyệt phát hành", board_approver=<user hợp lệ ≠ owner>)` → success; re-get `workflow_state == "Clinical Release"` + `board_approver == <user>` persist | deadlock 417 (bất khả trước fix) |
| **TC-04-BA-02** | 12b — STRUCTURED, KHÔNG 417 | như 01 nhưng `board_approver=""` VÀ `doc.board_approver` rỗng | gọi qua **API layer** `api.imm04.transition_state` → envelope `success==false`, `code=="VALIDATION"`, `message_code=="IMM04-GATE-G06-APPROVER"`, `context["missing"]==["board_approver"]`; **KHÔNG** raise `frappe.ValidationError`/417; re-get `workflow_state == "Initial Inspection"` (state bất biến) | 417 thô (nthrow_in_hook) |
| **TC-04-BA-03** | 12c — 4-eyes: trùng owner/submitter | phiếu @Initial Inspection do `user_A` tạo | `transition_state(..., board_approver="user_A")` → `assertRaises(ServiceError)` code `FORBIDDEN` (`assert_distinct_signers`); re-get `workflow_state == "Initial Inspection"` + `board_approver` rỗng (KHÔNG ghi) | self-approval rubber-stamp (NĐ98 SoD) |
| **TC-04-BA-04** | 12c — 4-eyes: đã đeo hat khác | phiếu @Initial Inspection với `clinical_head=user_B` (hoặc `qa_officer`/`pending_approver`) | `transition_state(..., board_approver="user_B")` → `ServiceError` FORBIDDEN; state bất biến, field KHÔNG ghi | 1 người ký ≥2 vai |
| **TC-04-BA-05** | 12e — BACKWARD-COMPAT (non-CR ignore) | phiếu @To Be Installed | `transition_state(name, "Bắt đầu lắp đặt", board_approver="user_X")` → success; re-get `board_approver` rỗng (param BỎ QUA, không lọt field khác), `workflow_state` đổi đúng theo action | param rò sang field khác / đổi state ngoài ý |
| **TC-04-BA-06** | 12e — caller cũ (không truyền param) | phiếu @To Be Installed | `transition_state(name, "Bắt đầu lắp đặt")` (2-arg, chữ ký cũ) → success y hệt hôm nay | vỡ chữ ký cũ |
| **TC-04-BA-07** | PATH END-TO-END | sau TC-04-BA-01 (đã @Clinical Release, board_approver set), user có `commissioning.submit` cap | `submit_commissioning(name)` → re-get `docstatus==1`; assert `on_submit` phát ĐỦ: ≥1 PM schedule (`imm08.create_pm_schedule_from_commissioning`) + ≥1 Calibration schedule (`imm11.create_calibration_schedule_from_commissioning`) cho asset (`final_asset`) | nút chết Needs→Operation |

**RED-before / GREEN-after (BẮT BUỘC):**
1. **RED:** chạy TC-04-BA-01/02 trên code hiện tại (`transition_state` 2-arg, `services/imm04.py:1156`) → TC-04-BA-01 **FAIL/ERROR** (deadlock: gate G06 raise lúc save → 417), TC-04-BA-02 **FAIL** (chưa có `message_code=IMM04-GATE-G06-APPROVER`, hiện là 417). Chứng minh test bắt bug thật.
2. **GREEN:** sau khi BE land `04 §5.4` (service `transition_state` +param · `api/imm04.py:92` passthrough · MSG entry `IMM04_GATE_G06_APPROVER`) → `bench --site miyano run-tests --module assetcore.tests.imm04.test_imm04` → `Ran N OK` (0 fail / 0 error), module-isolated. ⚠️ `services/imm04.py` + `api/imm04.py` dưới gunicorn `--preload` ⇒ live-HTTP CHỜ USER reload; DoD = run-tests XANH, **KHÔNG** curl.
3. **Guard OAS:** `grep -c '^@frappe.whitelist' api/imm04.py` bất biến (endpoint `transition_state` đã tồn tại — **0 whitelist mới**); mobile OAS KHÔNG có op `transition_state` ⇒ `test_mobile_oas` + op-count baseline KHÔNG đụng.

**Boundary (Never):** KHÔNG set `workflow_state` trực tiếp bỏ qua transition; KHÔNG dùng `frappe.throw`/`nthrow_in_hook` cho case thiếu approver ở path `transition_state` (đó là bug 417 cần chặn); KHÔNG cấp cùng user cho owner và board_approver trong TC happy-path (4-eyes sẽ FORBIDDEN); KHÔNG thêm `@frappe.whitelist` / op OAS mới.

## III.4d. Fail-path baseline — ghi nhận KHÔNG ĐẠT · Tái kiểm · gate G03 structured (BR-04-04e/f · BR-04-13 · BR-04-14)

File **MỚI**: `tests/test_imm04_baseline_fail_path.py` → class **`TestImm04BaselineFailPath`** (⬜ Planned). Spec: `04 §5.5` + ADR-IMM-04-04/05 + `05 §10/§5`.

**Flow THẬT bắt buộc** (KHÔNG shortcut set `workflow_state` trực tiếp): `create_commissioning(...)` → transition qua `svc.transition_state` tới **Initial Inspection** → `svc.submit_baseline_checklist(...)`. Re-get fresh bằng `CommissioningRepo.get(name)` / `doc.reload()`.

> ⚠️ **BẪY FIXTURE (đọc trước khi viết test — 2 gate KHÁC chạy cùng `doc.save()`):**
> 1. **G01 `validate_gate_g01`** (`services/imm04.py:349`) — `nthrow_in_hook(IMM04_DOCS_INCOMPLETE)` ⇒ **417** ở MỌI state ≠ `{Draft, Pending Doc Verify}` nếu còn `commissioning_documents` mandatory chưa `Received/Waived`. `initialize_commissioning` **tự seed** bộ hồ sơ mandatory ⇒ fixture PHẢI set `status="Received"`/`"Waived"` cho chúng, **hoặc** set `documents_incomplete=1` + `documents_incomplete_note="<lý do>"`. Bỏ qua bước này ⇒ test đỏ vì **G01**, dễ chẩn nhầm thành lỗi baseline.
> 2. **VR-03a `validate_checklist_completion`** (`asset_commissioning.py:111-123`) — MỌI dòng `baseline_tests` phải có `test_result`, và dòng `Fail` phải có `fail_note`. Fixture nộp verdict cho **mọi** dòng.
> 3. `_vr01_unique_serial_number` — `vendor_serial_no` phải duy nhất; dùng suffix ngẫu nhiên + teardown purge (`tests/_asset_cleanup.py`).

| TC | AC | Setup (flow thật) | Assertion (chính xác) | Bug chặn |
|---|---|---|---|---|
| **TC-04-BLFAIL-01** | AC1 — ghi nhận được KHÔNG ĐẠT | phiếu @Initial Inspection, `baseline_tests` rỗng | `submit_baseline_checklist(name, [{parameter:"Earth Resistance", measured_val:0.12, test_result:"Fail", fail_note:"Vượt 0.1Ω"}])` → **KHÔNG raise**; `doc.reload()`: dòng `Earth Resistance` **TỒN TẠI** với `test_result=="Fail"` + `measured_val≈0.12` + `fail_note` non-rỗng; `overall_inspection_result == "Fail"` (**KHÔNG** `"Pass"`); `workflow_state == "Initial Inspection"` (bất biến) | mất bằng chứng KHÔNG ĐẠT (raise trước save) |
| **TC-04-BLFAIL-02** | AC1 — response 5-key | như 01, 2 dòng (1 Pass + 1 Fail) | return `{"overall_result":"Fail", "tests_recorded":2, "failed_parameters":["Earth Resistance"], ...}`; `set(return) ⊇ {name, overall_result, tests_recorded, failed_parameters, clinical_hold_required}` | thiếu key ⇒ FE/mobile banner chết |
| **TC-04-BLFAIL-03** | AC2 — nộp được ở Re Inspection | phiếu @Re Inspection (đến qua `transition_state(name,"Báo cáo lỗi baseline")` sau TC-01) | `submit_baseline_checklist(...)` **KHÔNG** raise `INVALID_PARAMS` | dead-end vĩnh viễn (state-guard chỉ Initial Inspection) |
| **TC-04-BLFAIL-04** | AC2 — đo lại Fail→Pass | @Re Inspection, dòng `Earth Resistance` đang `Fail` | `submit_baseline_checklist(name, [{parameter:"Earth Resistance", measured_val:0.05, test_result:"Pass", fail_note:""}])` → `overall_result=="Pass"`, `failed_parameters==[]`; `doc.reload()`: **vẫn 1 dòng** (upsert-by-`parameter`, KHÔNG nhân đôi), `test_result=="Pass"`; `overall_inspection_result=="Pass"`; `workflow_state=="Re Inspection"` | append trùng dòng · verdict không cập nhật |
| **TC-04-BLFAIL-05** | AC3 — nút hết chết | phiếu @Initial Inspection sau TC-01 (≥1 dòng `Fail` đã persist, mọi dòng có verdict, `Fail` có `fail_note`, hồ sơ G01 sạch) | gọi qua **API layer** `api.imm04.transition_state(name, "Báo cáo lỗi baseline")` → envelope `success==true`, `data["new_state"]=="Re Inspection"`; **KHÔNG** `frappe.ValidationError`/417; sinh **1** bản ghi **`IMM Audit Trail`** filter `{ref_doctype:"Asset Commissioning", ref_name:<name>, to_status:"Re Inspection"}` — ⚠️ **KHÔNG** assert `Asset Lifecycle Event` (IMM-04 không có child table đó, xem `04 §5.5.0 SC#4`) | 417 câm ở đúng tình huống duy nhất cần nút |
| **TC-04-BLFAIL-06** | AC4 — cổng KHÔNG nới (Initial Inspection) | phiếu @Initial Inspection còn ≥1 dòng `Fail` | `api.imm04.transition_state(name, "Phê duyệt phát hành", board_approver=<hợp lệ>)` → `success==false`, `code=="VALIDATION"`, `http_status==422`, `message_code=="IMM04-GATE-G03-BASELINE"`, `context["failed"]` chứa parameter Fail; re-get `workflow_state=="Initial Inspection"` **và** `docstatus==0` **và** `board_approver` rỗng | nới cổng an toàn · 417 câm · ghi approver khi bị chặn |
| **TC-04-BLFAIL-07** | AC4 — cổng KHÔNG nới (Re Inspection) | phiếu @Re Inspection còn ≥1 dòng `Fail` | `api.imm04.transition_state(name, "Phê duyệt sau tái kiểm", board_approver=<hợp lệ>)` → cùng envelope như TC-06; `workflow_state=="Re Inspection"`, `docstatus==0` | đường vòng qua Tái kiểm lọt cổng |
| **TC-04-BLFAIL-08** | AC4 — G03 chạy TRƯỚC G06 | phiếu @Initial Inspection còn `Fail`, **KHÔNG** truyền `board_approver` | `message_code == "IMM04-GATE-G03-BASELINE"` (**KHÔNG** phải `IMM04-GATE-G06-APPROVER`) | thứ tự gate sai ⇒ user bị hỏi người duyệt cho thiết bị chưa đạt |
| **TC-04-BLFAIL-09** | AC5 — guard cũ còn hiệu lực | phiếu @Initial Inspection | (a) `submit_baseline_checklist(name, [])` → `assertRaises(ServiceError)` `VALIDATION`; (b) phiếu có row seed nhưng `test_result` rỗng + `results=[]` → cùng raise; cả 2: re-get `overall_inspection_result` **KHÔNG** `"Pass"` và **KHÔNG** `"Fail"` | tái mở lỗ silent-completion khi sửa Fail-path |
| **TC-04-BLFAIL-10** | AC6 — parity message-code | — | `from assetcore.utils.messages import MSG, MESSAGES`: `MSG.IMM04_GATE_G03_BASELINE in MESSAGES`; đọc `frontend/src/locales/messages.ts` → chuỗi `IMM04-GATE-G03-BASELINE` **có mặt** | FE rơi về toast `SYS-500` "liên hệ IT" |

**RED-before / GREEN-after (BẮT BUỘC):**
1. **RED (trên code hiện tại):** TC-01/02 **FAIL** (`ServiceError` VALIDATION, 0 dòng persist) · TC-03 **FAIL** (`INVALID_PARAMS`) · TC-05 **ERROR/417** · TC-06/07/08 **FAIL** (chưa có `IMM04-GATE-G03-BASELINE`; hiện 417 hoặc lọt cổng) · TC-10 **FAIL** (code chưa tồn tại). TC-04/09 phụ thuộc TC trước. Chứng minh test bắt bug thật.
2. **GREEN (sau khi BE land `04 §5.5`):** cả **3 module** phải `Ran N OK`, module-isolated:
   ```bash
   bench --site miyano run-tests --module assetcore.tests.imm04.test_imm04_baseline_fail_path
   bench --site miyano run-tests --module assetcore.tests.imm04.test_imm04_baseline_silent_completion
   bench --site miyano run-tests --module assetcore.tests.imm04.test_imm04
   ```
   ⚠️ **KHÔNG dùng curl** để nghiệm thu: `services/imm04.py` + `api/imm04.py` chạy dưới gunicorn `--preload` ⇒ HTTP live stale tới khi USER reload (LL-DEPLOY-07 — 417 phantom). **DoD = run-tests XANH.**
3. **KHÔNG `bench migrate`:** delta chỉ chạm `.py` + `messages.ts` (generated) + `docs/`; **0** thay đổi `asset_commissioning.json` / `commissioning_checklist.json` / `imm_04_workflow.json` — verify bằng `git status --porcelain | grep -E '\.json$'` = rỗng cho 3 file đó.
4. **Regression guard bắt buộc XANH (không được sửa để "cho xanh"):** `test_imm04_baseline_silent_completion` — 7 TC assert `validate_checklist_completion()` **CÓ** raise ở `Initial Inspection` (checklist rỗng · dòng chưa đo · `Fail` thiếu note). Nếu ai đó nới `validate_checklist_completion` để "sửa 417" ⇒ suite này **ĐỎ** ⇒ **sai hướng, dừng lại** (xem `04 §5.5.0 SC#3`: chỉ cần sửa service là đủ mở nút).

**Boundary (Never):** ❌ set `workflow_state` trực tiếp bỏ qua transition (test giả); ❌ sửa `validate_checklist_completion` / `test_imm04_baseline_silent_completion` cho "xanh"; ❌ assert `overall_result` luôn `"Pass"`; ❌ mock `doc.save` trong TC-01/04 (persist chính là điều cần chứng minh — mock = false-green); ❌ dùng curl làm bằng chứng DoD; ❌ thêm `@frappe.whitelist` mới.

## III.4e. Thẻ cổng ⟺ enforcement parity + read-gate 3 lớp (BR-04-15 · BR-04-16 · CR-76)

File: `tests/test_imm04.py` → class **`TestGateStatusEnforcementParity`** (mở rộng `TestGateG05CardValidatorParity` đã live) + `tests/test_rowscope_docperm_gate.py` / `test_rowscope_invariant.py` cho lớp quyền. Spec: `04 §5.6` + ADR-IMM-04-06/07 + `05 §24`.

**Ma trận fixture (ĐẶT PHIẾU Ở TRẠNG THÁI CỔNG ĐƯỢC GÁC — xem `04 §5.6.1` cột 4).** Mỗi hàng chạy **2 phép đo**: giá trị thẻ (`get_gate_status(name).data[gXX]`) và enforcement (raise / không raise).

| TC | Cổng | Fixture | Thẻ kỳ vọng | Enforcement kỳ vọng | Lỗi bị chặn |
|---|---|---|---|---|---|
| **TC-04-GATE-01** | G01 | **0 dòng** `commissioning_documents` `is_mandatory` (xoá sạch bộ seed của `initialize_commissioning`), state `To Be Installed` | `g01_docs is True`, `g01_waived is False` | `validate_gate_g01(doc)` **không raise** | **E1 báo oan** — hiện hằng `False` @`api/imm04.py:257` |
| **TC-04-GATE-02** | G01 | ≥1 hồ sơ bắt buộc `Pending` **+** `documents_incomplete=1` + `documents_incomplete_note="CO/CQ về sau"` | `g01_docs is True`, **`g01_waived is True`** | không raise (msgprint cảnh báo) | **E2 báo oan** — thẻ không biết nhánh giải trình |
| **TC-04-GATE-03** | G01 | ≥1 hồ sơ bắt buộc `Pending`, **không** giải trình | `g01_docs is False`, `g01_waived is False` | `assertRaises(frappe.ValidationError)` | nới cổng khi sửa E1/E2 |
| **TC-04-GATE-04** | G01 | mọi hồ sơ bắt buộc `Received`; **thêm** 1 hồ sơ **không** bắt buộc `Pending` | `g01_docs is True`, `g01_waived is False` | không raise | tính nhầm hồ sơ tuỳ chọn vào cổng |
| **TC-04-GATE-05** | G01 | ≥1 hồ sơ bắt buộc `Pending` + `documents_incomplete=1` + note **rỗng/chỉ khoảng trắng** | `g01_docs is False`, `g01_waived is False` | raise | waiver "rỗng" lọt cổng (predicate phải `.strip()`) |
| **TC-04-GATE-06** | G03 | `baseline_tests` **rỗng**, state `Initial Inspection` | `g03_baseline is False` | pre-check BR-04-13 raise `IMM04-GATE-G03-BASELINE` khi `transition_state(..., "Phê duyệt phát hành")` | `bool(tests)` bị bỏ khi refactor |
| **TC-04-GATE-07** | G03 | 2 dòng `Pass` + 1 dòng `N/A` | `g03_baseline is True` | không raise (nhánh G03) | thu hẹp `_G03_PASSING` câm |
| **TC-04-GATE-08** | G03 | 1 dòng `Fail` (có `fail_note`) | `g03_baseline is False` | raise, `context["failed"]` chứa parameter đó | — |
| **TC-04-GATE-09** | G03 | 1 dòng `test_result = " Pass"` (thừa khoảng trắng) | `g03_baseline is True` | không raise | **E3** — thẻ cũ không `.strip()` ⇒ lệch với pre-check |
| **TC-04-GATE-10** | G03 | `grep -n '"Pass", "N/A"' assetcore/api/imm04.py` | **0 hit** | — | literal tái sinh ở tầng api (AC3) |
| **TC-04-GATE-11** | G05 | 1 NC `Open` | `g05_nc is False` | `validate_gate_g05_g06` raise | *(đã live — giữ)* |
| **TC-04-GATE-12** | G05 | 1 NC `Resolved` + 1 `Under Review` + 1 `Transferred` (0 `Open`) | `g05_nc is True` | không raise | regress CR-54 §3 |
| **TC-04-GATE-13** | G06 | `board_approver` rỗng, state `Clinical Release` | `g06_approver is False` | raise `IMM04_BOARD_APPROVER_REQUIRED` | — |
| **TC-04-GATE-14** | G06 | `board_approver` đã set | `g06_approver is True` | không raise (nhánh G06) | — |
| **TC-04-GATE-15** | quyền | persona **0 DocPerm read** `Asset Commissioning`, `name` **có thật** | envelope `success is False`, `code == "FORBIDDEN"`, `http_status == 403`; `set(data or {}) ∩ {khoá bắt đầu "g0"} == ∅` | — | **E4 IDOR-đọc** |
| **TC-04-GATE-16** | quyền | persona **0 DocPerm read**, `name` **bịa** | **cùng** envelope FORBIDDEN như TC-15 (byte-identical `code`/`http_status`) | — | existence-oracle (L0 phải chạy TRƯỚC EXISTS) |
| **TC-04-GATE-17** | quyền | persona **đủ quyền**, `name` **bịa** | `code == "NOT_FOUND"`, `message_code == "IMM04-NOT-FOUND"` | — | mất 404 cho người có quyền |
| **TC-04-GATE-18** | quyền | persona **đủ quyền**, `name` có thật | 200, `set(data)` == **8 khoá** (6 cũ + `g01_waived` + `g04_applicable` — cập nhật AC-CR-85); mọi khoá cũ giữ **nguyên tên + kiểu `bool`** | — | vỡ hợp đồng cũ (additive) |
| **TC-04-GATE-19** | quyền | guard tĩnh | cặp `("services/imm04.py", "evaluate_gate_status")` **KHÔNG** ∈ `_DETAIL_READ_UNGATED_BACKLOG`; **CÓ** ∈ vế *named* (`_CR76_NAMED_DETAIL_GATES`); `test_rowscope_scope_guard` G5a/G5b **xanh** | — | thêm dòng allowlist để "cho xanh" = mở lại lỗ (AC5) |

**Quy tắc chấm parity (INV-GATE-PARITY):** với mỗi hàng TC-01..14, hai phép đo phải **đồng dấu**: `card is True ⟺ enforcement không raise`. Test viết dạng **bảng chân trị** (một helper `_assert_parity(gate_key, expect_pass)`), **KHÔNG** viết 2 assert rời rạc — mục đích là chứng minh *tương đương*, không phải *hai sự thật độc lập*.

**Bẫy fixture (kế thừa III.4d + mới):**
1. **G01 chạy ở MỌI state ≠ `{Draft, Pending Doc Verify}`** ⇒ fixture cho TC G03/G05/G06 phải làm sạch G01 trước (Received/Waived **hoặc** waiver), nếu không đỏ vì nhầm cổng.
2. **TC-15/16/17 PHẢI chạy dưới session user THẬT** (`frappe.set_user(<persona>)`): `Administrator` short-circuit `frappe/permissions.py:107-109` ⇒ **xanh giả**.
3. Ma trận G01 cần **xoá** bộ hồ sơ mandatory do `initialize_commissioning` tự seed (TC-01) — dùng `doc.set("commissioning_documents", [])` rồi `db_update`, KHÔNG sửa `initialize_commissioning`.
4. `tearDown` **phải** purge NC + phiếu (mirror `TestGateG05CardValidatorParity`) — fixture rơi ⇒ TC khác đỏ oan (LL: mọi `bench run-tests` đặt `timeout` tool ≥ **600000ms**, kill giữa chừng = nhiễm DB).

**RED-before / GREEN-after (BẮT BUỘC — chống xanh giả, AC8):**
1. **RED trên code hiện tại:** TC-01 (thẻ `False`, validator không raise) · TC-02 (thẻ `False`) · TC-09 (thẻ `False`) · TC-15/16 (hiện **200 + đủ khoá** cho persona 0 quyền) · TC-17 (hiện `code` là `404` số, không `NOT_FOUND` envelope) · TC-18 (thiếu `g01_waived`) · TC-19 (chưa có vế named).
2. **Mutation-verified sau khi xanh:** hoàn nguyên nhánh **no-mandatory-docs** ⇒ TC-01 **ĐỎ**; hoàn nguyên nhánh **waiver** ⇒ TC-02 **ĐỎ**; gỡ `assert_can_read_doc` ⇒ TC-15/TC-19 **ĐỎ**; rot 1 cite OAS ⇒ TC cite-parity `test_mobile_oas` **ĐỎ**; hoàn nguyên tất cả ⇒ **XANH**. Ghi bằng chứng vào báo cáo vòng.
3. **Suite phải XANH THẬT (module-isolated):**
   ```bash
   bench --site miyano run-tests --module assetcore.tests.imm04.test_imm04
   bench --site miyano run-tests --module assetcore.tests.imm04.test_imm04_baseline_fail_path
   bench --site miyano run-tests --module assetcore.tests.guards.test_rowscope_scope_guard
   bench --site miyano run-tests --module assetcore.tests.integration.test_rowscope_docperm_gate
   bench --site miyano run-tests --module assetcore.tests.integration.test_rowscope_invariant
   bench --site miyano run-tests --module assetcore.tests.guards.test_mobile_oas
   bench --site miyano run-tests --module assetcore.tests.guards.test_mobile_docset
   ```
   FE: `npx vitest run src/components/commissioning/tests/ApprovalPanel.gate.test.ts` + `npx vue-tsc --noEmit` (0 lỗi).
   ⚠️ **KHÔNG curl** (gunicorn `--preload` ⇒ stale worker, LL-DEPLOY-07). **DoD = run-tests XANH.**
4. **Zero-behavior-change (AC7):** `git diff` các hàm `transition_state` / `validate_gate_g01` / `validate_gate_g05_g06` / `AssetCommissioning.validate` chỉ được chứa **trích xuất predicate** — **0** nhánh `raise`/`nthrow*` thêm/bớt/đổi điều kiện. Reviewer đọc diff theo tiêu chí này trước khi chấm xong.

**Boundary (Never):** ❌ gọi validator trong `try/except` để dựng thẻ (side-effect `msgprint` + state-guard — xem ADR-IMM-04-06 alternative (b)); ❌ copy state-guard vào thẻ (sinh "xanh rồi đỏ"); ❌ assert bằng `Administrator` cho TC quyền; ❌ thêm dòng vào `_DETAIL_READ_UNGATED_BACKLOG`; ❌ sửa `_count_open_ncs` sang `!= 'Closed'` (chưa ratify); ❌ đụng `validate_gate_g03` / `validate_radiation_hold` (backlog C1/C2).

## III.4f. Cổng G04 gác ĐÚNG 1 domain — predicate SSoT + gỡ deadlock (BR-04-17 · AC-CR-85)

File: `tests/test_imm04.py` → class **`TestGateG04Applicability`** (đã land, 13 TC) + cập nhật `TestVR07ClinicalHold` (`test_imm04.py:335-375` — TC cuối đổi tên thành `test_radiation_class_is_gated_by_g04`).
Spec: `02 §IV.2` BR-04-17 · `04 §5.7` · `05 §24.6` · ADR-IMM-04-08 / ADR-IMM-04-09.
**Baseline trước vòng này (đo thật 2026-07-27):** `test_imm04` = **97 OK**.

### III.4f.1. Ma trận A — `check_auto_clinical_hold` KHÔNG suy giảm (**12 ô**, không phải 10)

⚠️ **Self-Correction so với acceptance:** ma trận `5 risk_class × 2 cờ` **bỏ sót nhánh fallback**. Biểu thức là `doc.risk_class in (...) if doc.risk_class else bool(doc.is_radiation_device)` ⇒ với **mọi** giá trị enum, `risk_class` luôn truthy nên nhánh `else` **không bao giờ chạy**. Nếu chỉ chốt 10 ô thì ai đó xoá nhánh fallback vẫn xanh 10/10 — test rỗng đúng thứ A10 muốn cấm. Phải có **6** giá trị `risk_class` (5 enum + **rỗng**).

| TC | `risk_class` | `is_radiation_device` | Trả về | Nhánh |
|---|---|---|---|---|
| TC-04-G04-01 | `A` | 0 → `False` · 1 → `False` | `False` | enum |
| TC-04-G04-02 | `B` | 0 → `False` · 1 → `False` | `False` | enum |
| TC-04-G04-03 | `C` | 0 → `True` · 1 → `True` | `True` | enum |
| TC-04-G04-04 | `D` | 0 → `True` · 1 → `True` | `True` | enum |
| TC-04-G04-05 | `Radiation` | 0 → `True` · 1 → `True` | `True` | enum |
| **TC-04-G04-06** | **`''` (rỗng)** | **0 → `False` · 1 → `True`** | theo cờ | **fallback — 2 ô mà 5×2 bỏ sót** |

Assert: giá trị **giống hệt** hành vi trước fix ở cả **12/12** ô ⇒ `clinical_hold_required` (`services/imm04.py:1774`) và Clinical Hold routing **bất biến**.

### III.4f.2. Ma trận B — INV-G04-1 hai chiều (**10 ô**: 5 `risk_class` × 2 `qa_license_doc`)

Mỗi ô chạy **3 phép đo** trên **cùng** một phiếu: `gate_g04_applies(doc)` · `evaluate_gate_status(name)["g04_applicable"]`/`["g04_radiation"]` · VR-07 (`validate_radiation_hold`, state `Clinical Release`).

| TC | Fixture | Kỳ vọng |
|---|---|---|
| **TC-04-G04-07** | Device Model `is_radiation_device=0`, `risk_class ∈ {A,B,C,D}`, `qa_license_doc` rỗng | `applies=False` · `g04_applicable is False` · `g04_radiation is True` · VR-07 **không raise** |
| **TC-04-G04-08** | như trên nhưng **có** `qa_license_doc` | `g04_applicable is False` · `g04_radiation is True` · không raise (giấy phép thừa không đổi kết quả) |
| **TC-04-G04-09** | Model `is_radiation_device=1` (⇒ `risk_class='Radiation'` do `_autofill_from_device_model`), `qa_license_doc` **rỗng** | `applies=True` · `g04_applicable is True` · `g04_radiation is False` · VR-07 **raise** |
| **TC-04-G04-10** | như TC-09 nhưng **có** `qa_license_doc` | `g04_applicable is True` · `g04_radiation is True` · không raise |
| **TC-04-G04-11** | Model `is_radiation_device=0` **nhưng** người dùng đặt `risk_class='Radiation'`, `qa_license_doc` rỗng | `applies=True` · `g04_radiation is False` · VR-07 **raise** — **chống suy giảm an toàn**: đây chính là ô mà bỏ vế `risk_class == 'Radiation'` sẽ mất cổng |
| **TC-04-G04-12** | **Ô người dùng thật (gỡ deadlock, A6)** — `risk_class='C'`, Model **không** bức xạ, `qa_license_doc` **rỗng**, `workflow_state='Clinical Release'` | `doc.save()` **KHÔNG** throw «…Giấy phép của Cục An toàn Bức xạ Hạt nhân»; đọc lại DB `frappe.db.get_value('Asset Commissioning', name, 'is_radiation_device') == 0` (A1) |

**Quy tắc chấm (INV-G04-1):** `g04_applicable is False ⇒ g04_radiation is True` **và** VR-07 không raise, ở **mọi** ô; ô `{False, False}` không được xuất hiện lần nào.

### III.4f.3. Bẫy fixture (đọc trước khi viết test — tránh xanh giả / đỏ oan)

1. **`_autofill_from_device_model` ghi đè `risk_class` ở `before_insert`** (`services/imm04.py:250-268`): khi `is_new()`, `medical_device_class` được map `Class I/II/III → A/B/C`; nếu model gắn cờ bức xạ thì `risk_class` bị ép `'Radiation'`. ⇒ Muốn phiếu có `risk_class='C'` với model Class III thì map đã cho đúng `C`; muốn `'D'` hoặc `''` thì **set sau khi insert rồi `save()`**, đừng truyền vào lúc tạo rồi assert.
2. **`fetch_from` chạy TRƯỚC `validate()`** (`frappe/model/document.py:302/309/413/414` → `_validate_links` → `set_fetch_from_value`): sau khi gỡ ghi đè, `is_radiation_device` **luôn** bằng giá trị Device Model tại mỗi lần lưu. Assert **phải đọc lại từ DB** (`frappe.db.get_value`), **không** assert trên object trong bộ nhớ.
3. **VR-07 chỉ gác ở `{Clinical Release, Pending Release}`** — fixture ở state khác sẽ "không raise" vì **sai state**, không phải vì predicate đúng ⇒ xanh giả. Ma trận B **phải** đặt state đúng.
4. **G01/G03 chạy trước trong `validate()`** (`asset_commissioning.py:36-47`) ⇒ phiếu dùng cho ma trận B phải sạch hồ sơ bắt buộc + có baseline hợp lệ, nếu không đỏ vì **nhầm cổng**.
5. `TestVR07ClinicalHold::test_radiation_class_sets_flag` (`test_imm04.py:355-358`) **assert chính cái side-effect đang bị gỡ** ⇒ **phải viết lại**: thay `assertEqual(doc.is_radiation_device, 1)` bằng `assertTrue(gate_g04_applies(doc))` (giữ nguyên ý định "phiếu Radiation vẫn bị cổng G04 gác", bỏ cách đo qua side-effect). Đây là **sửa test theo spec mới**, không phải "sửa test cho khớp code".
6. `tearDown` purge phiếu + Device Model tạm (`memory/test_session_*` — fixture rơi = nhiễm suite khác). Mọi `bench run-tests` đặt `timeout` tool ≥ **600000ms**.

### III.4f.4. RED-before / GREEN-after + mutation (chống test rỗng — A10)

**RED trên code hiện tại (phải đỏ TRƯỚC khi sửa):** TC-04-G04-07 (hiện `g04_applicable` chưa tồn tại; với `risk_class='C'` server bơm cờ ⇒ `g04_radiation is False`) · TC-04-G04-12 (hiện **throw** VR-07 + DB đọc ra `1`) · guard `cr85_g` nhánh parity.

**Mutation-probe (chạy SAU khi xanh, khôi phục nguyên trạng + verify `md5sum`):**

| # | Đột biến | Phải làm ĐỎ |
|---|---|---|
| M1 | `gate_g04_applies` → `return True` | ≥ 3 TC: TC-04-G04-07, TC-04-G04-08, TC-04-G04-12 (+ ma trận thẻ) |
| M2 | `gate_g04_applies` → `return False` | TC-04-G04-09, TC-04-G04-10, TC-04-G04-11 |
| M3 | Bỏ vế `or doc.get("risk_class") == "Radiation"` | **TC-04-G04-11** (ô chống suy giảm an toàn) |
| M4 | Xoá khoá `g04_applicable` khỏi `evaluate_gate_status` | TC-04-GATE-18 + guard OAS `cr85_g` |
| M5 | Khôi phục `doc.is_radiation_device = 1` trong `check_auto_clinical_hold` | TC-04-G04-12 (đọc DB) + `cr85_g` |
| M6 | VR-07 quay lại đọc `self.is_radiation_device` | TC-04-G04-11 vẫn xanh nhưng **TC-04-G04-12 ĐỎ** ⇒ chứng minh parity là **hai chiều**, không chỉ một |
| M7 | Xoá nhánh fallback `else bool(doc.is_radiation_device)` | **TC-04-G04-06** (2 ô mà ma trận 5×2 bỏ sót) |

#### III.4f.4-bis. KẾT QUẢ THẬT sau land (BE Bước-4, 2026-07-27 — `md5sum` khôi phục khớp 2/2 file)

Baseline `test_imm04` = **97 OK** → sau land **110 OK** (+13: TC-04-G04-01..13; `TestVR07ClinicalHold::test_radiation_class_sets_flag` **đổi tên** `test_radiation_class_is_gated_by_g04`, đo qua `gate_g04_applies` — bẫy 5).

**RED-before (đo thật, dựng shim predicate rồi chạy):** 5 FAIL + 12 ERROR — TC-04-G04-03/04/05 (side-effect ghi cờ), TC-04-G04-07/08/09/10/11/13 (`g04_applicable` chưa tồn tại ⇒ KeyError), **TC-04-G04-12 FAIL với chính chuỗi «Giấy phép của Cục An toàn Bức xạ Hạt nhân»** (deadlock tái hiện trên phiếu THẬT), TC-04-GATE-18 (key-set 7→8).

| # | Kỳ vọng (spec) | ĐỎ THẬT | Khớp? |
|---|---|---|---|
| M1 | ≥3 TC | TC-07 (×4 subTest) · TC-08 (×4) · TC-12 · TC-13 (+2 ERROR ở `TestTransitionBoardApprover` — phiếu thật không release được) | ✅ |
| M2 | TC-09/10/11 | TC-09 · TC-10 · TC-11 · `test_radiation_class_is_gated_by_g04` | ✅ |
| M3 | TC-11 | TC-11 · `test_radiation_class_is_gated_by_g04` | ✅ |
| M4 | TC-04-GATE-18 + `cr85_g` | TC-GATE-18 + 13 ERROR + `cr85_g` **(chỉ sau khi siết guard — xem dưới)** | ⚠️ self-correction |
| M5 | TC-12 + `cr85_g` | TC-03 · TC-04 · TC-05 · TC-12 + `cr85_g` | ✅ (rộng hơn kỳ vọng) |
| M6 | «TC-11 xanh, TC-12 ĐỎ» | **TC-11 ĐỎ · TC-13 ĐỎ · `cr85_g` ĐỎ; TC-12 XANH** | ⚠️ self-correction |
| M7 | TC-06 | TC-06 · `test_radiation_hold` | ✅ |

**2 self-correction so với bảng dự kiến (ghi lại vì cả hai đều là bài học chống test rỗng):**

1. **M4 KHÔNG làm đỏ `cr85_g` ở lần chạy đầu** — guard đo `emits` bằng `ast.dump` **cả hàm**, mà docstring `evaluate_gate_status` có nhắc tên khoá ⇒ xoá khoá khỏi `return` vẫn XANH (vacuous). Đã **SIẾT** (không nới): đọc **khoá thật của dict `return`**; đồng thời khẳng định "tính qua predicate SSoT" chuyển sang đo `ast.Call` (helper `_cr85_called_names`) thay vì tìm chuỗi trong dump. Chạy lại M4 ⇒ ĐỎ. Số TC **giữ 1015** (siết assertion ≠ thêm TC).
2. **M6 làm đỏ TC-11/TC-13 chứ không phải TC-12.** Dự đoán cũ giả định ghi-đè cờ VẪN còn; sau khi A1 gỡ ghi đè, phiếu Class C giữ cờ `0` nên VR-07-đọc-cờ cũng không chặn ⇒ TC-12 không phân biệt được M6. Chiều "advertise ⊇ enforce" nay do **TC-04-G04-11** (phiếu người dùng phân loại `Radiation`, cờ model = 0) và **TC-04-G04-13** (mutation-probe thường trực) bắt. Parity vẫn 2 chiều, chỉ đổi TC gác.

**Suite phải XANH THẬT (module-isolated, `timeout` ≥ 600000ms):**

```bash
bench --site miyano run-tests --module assetcore.tests.imm04.test_imm04              # 97 → 110 OK (+13)
bench --site miyano run-tests --module assetcore.tests.imm04.test_imm04_baseline_fail_path
bench --site miyano run-tests --module assetcore.tests.imm04.test_imm04_baseline_silent_completion
bench --site miyano run-tests --module assetcore.tests.guards.test_mobile_oas         # 1015 OK
bench --site miyano run-tests --module assetcore.tests.guards.test_mobile_docset      # 9 OK
```

FE: `npm run test` + `npx vue-tsc --noEmit`. **TUYỆT ĐỐI 0 `bench migrate`** (không sửa DocType JSON — mọi field đã tồn tại). **KHÔNG curl** (gunicorn `--preload` ⇒ stale worker, LL-DEPLOY-07): DoD = `run-tests` xanh.

**Boundary (Never) — §III.4f:** ❌ đo "1 diễn giải" bằng `grep -c` toàn file (8 hit hợp lệ ngoài vùng cổng — dùng AST-scoped như `cr85_g`); ❌ sửa `validate_gate_g01`/`validate_gate_g05_g06`/pre-check BR-04-13 để "cho khớp"; ❌ sửa `_autofill_from_device_model` (writer hợp lệ, ngoài scope); ❌ nới guard kiến trúc (`_DETAIL_READ_UNGATED_BACKLOG`, key-set contract) để hợp spec; ❌ viết patch backfill dữ liệu cũ (B-CR85-1 — cần USER duyệt).

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

**FE (vitest):** `frontend/src/components/commissioning/tests/QRLabel.test.ts` — case deep-link:
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
bench --site assetcore.local run-tests --app assetcore --module assetcore.tests.imm04.test_imm04
# Coverage
coverage run -m unittest assetcore.tests.imm04.test_imm04 && coverage report
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
| BR-04-15 | Thẻ cổng G01–G06 = CHÍNH predicate enforcement (BLOCKING-parity · `g01_waived` additive · `_G03_PASSING` SSoT · G02 tham khảo) | `TestGateStatusEnforcementParity` TC-04-GATE-01..14 (§III.4e) + FE `ApprovalPanel.gate.test.ts` | Decision Table + Invariant (bảng chân trị) + Mutation | ⬜ Planned (RED-before ở TC-01/02/09) |
| BR-04-17 | Cổng G04 gác ĐÚNG 1 domain — predicate SSoT `gate_g04_applies` + `g04_applicable` + INV-G04-1 (AC-CR-85) | `TestGateG04Applicability` TC-04-G04-01..13 (§III.4f) + `TestMobileGateStatusApplicability` cr85_a..g + FE `ApprovalPanel` FE-G04-1..7 | Decision Table + Invariant + Mutation (M1–M7) | ✅ 13/13 (RED-before đo thật ở TC-03/04/05/07..13 + TC-GATE-18; mutation 7/7 ĐỎ — §III.4f.4-bis) |
| BR-04-16 | Read-gate 3 lớp ROLE→EXISTS→ROW cho `get_gate_status`; 403 in-envelope trên HTTP-200; 0 existence-oracle | TC-04-GATE-15..19 (§III.4e) + `test_rowscope_docperm_gate` / `test_rowscope_invariant` / `test_rowscope_scope_guard` G5a/G5b | Invariant + Guard tĩnh (AST) | ⬜ Planned (RED-before ở TC-15/16/18/19) |

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

## VIII. AC-CR-98 + AC-CR-106 — `list_commissioning` MỘT ENGINE + vendor-scope là PHÉP GIAO (chốt 2026-07-30)

> **SSoT quyết định:** [`../imm-00/ADR-IMM00-LIST-SCOPE.md §10`](../imm-00/ADR-IMM00-LIST-SCOPE.md) (`ADR-IMM00-LIST-SCOPE-04/05` · `INV-COMM-SCOPE-1..4` · `INV-VENDORSCOPE-1..4` · enforce `INV-CONN-21`/`INV-CONN-27`) · BE `§10.4/§10.5` · FE [`06 §11`](./06_Frontend_Design.md).
>
> **QA đọc TRƯỚC khi chấm — 3 đính chính so với đề mục** (§10.1 RC-10.3): (1) shape trả về là `{"items", "pagination"}`, `total` nằm **trong** `pagination` — **không có** `res['total']`/`res['records']`; (2) persona rò dữ liệu là **`Vendor Engineer` + `Commissioning User`** (vendor **thuần** không có DocPerm read ⇒ nhận **Error envelope**, không phải danh sách); (3) yêu cầu "0 hit `frappe.get_all` trong thân hàm" áp cho **DocType row-scoped** (`Asset Commissioning`, `AC Asset`) — 4 lookup **nhãn** trên DocType không-row-scoped **giữ** `get_all`, đổi chúng sẽ **mất nhãn** hiển thị.

### VIII.1 BE — bảng test case (đỏ TRƯỚC / xanh SAU, KHÔNG "xanh suông")

| TC | Bất biến | Nơi đặt | Phát biểu chấm được |
|---|---|---|---|
| **TC-IMM04-SCOPE-01** | INV-COMM-SCOPE-1 | `test_rowscope_scope_guard.py` (delta) | AST thân `list_commissioning`: **0** `frappe.get_all`/`frappe.db.count`/`frappe.db.get_all` trên DocType ∈ `hooks.permission_query_conditions`; 4 lookup nhãn (`IMM Device Model`·`AC Supplier`·`AC Department`·`AC Purchase`) **được phép** tồn tại |
| **TC-IMM04-SCOPE-02** | INV-COMM-SCOPE-4 | `test_rowscope_scope_guard.py` (delta) | `("services/imm04.py","list_commissioning") not in _RAW_QUERY_UNGATED_BACKLOG` ∧ `len(_RAW_QUERY_UNGATED_BACKLOG) <= 16` (cấm thăng-hạng-ngược) ∧ `test_raw_queries_on_rowscoped_doctypes_are_gated` XANH |
| **TC-IMM04-SCOPE-03** | INV-COMM-SCOPE-2 | class mới trong `test_rowscope_invariant.py` | `frappe.set_user(<vendor+commissioning>)`; seed 2 phiếu (1 `owner`=persona, 1 `owner`=người khác) ⇒ phiếu người khác **vắng** ở CẢ `items` LẪN `pagination.total`. **ĐỎ trước fix** (hôm nay có mặt ở cả hai) |
| **TC-IMM04-SCOPE-04** | INV-COMM-SCOPE-3 | 〃 | 3 persona (§10.2): `pagination.total == len(items)` khi tổng ≤ `page_size` |
| **TC-IMM04-SCOPE-05** | INV-COMM-SCOPE-3 (vế > trang) | 〃 | seed ≥ `page_size+2` phiếu, gọi `page_size=2` ⇒ `total` == số dòng **row-scoped** đếm qua cùng predicate (**không** phải `COUNT(*)` toàn bảng); `len(items) == 2` |
| **TC-IMM04-SCOPE-06** | §10.6 | 〃 | `Vendor Engineer` **thuần** ⇒ **HTTP-200 + Error envelope** `FORBIDDEN` (chấm qua `api/imm04.list_commissioning`, KHÔNG qua service) — **không** phải `items: []` |
| **TC-IMM04-SCOPE-07** | INV-CONN-27 (enforce) | 〃 | **cùng session, cùng thiết bị X**, cho **3 persona**: `cell.total == len(drill.items) + #{docstatus==2}` ∧ `cell.total_capped == 0` ∧ **mọi** dòng drill có `final_asset == X`. Dung sai phải khai **tường minh** trong assert kèm cite `AC-CR-99` |
| **TC-IMM04-SCOPE-08** | INV-CONN-27 (không vacuous) | 〃 | seed cả `docstatus` 0 **và** 1 cho X ⇒ công thức không vacuous; ô «Phiếu nghiệm thu lắp đặt» **có mặt** (`assertIn` **trước** khi so số — cấm `dict.get(k, default)`) |
| **TC-VSCOPE-01..08** | INV-VENDORSCOPE-1 | **file MỚI** `test_vendor_scope_intersect.py` | đủ **8 dòng** bảng đại số §10.4 (absent · vô hướng trong/ngoài phạm vi · `=` · `in` · list literal · `!=` · `not in` · op không tính được ⇒ `__none__`) |
| **TC-VSCOPE-09** | INV-VENDORSCOPE-1 (phủ 5 doctype) | 〃 | chạy đại số cho **cả 5** khoá `_VENDOR_SCOPE_FIELD_MAP` với đúng field của từng doctype (`name`/`asset_ref`/`asset`) |
| **TC-VSCOPE-10** | INV-VENDORSCOPE-2 | 〃 | dict-in ⇒ **dict**-out; shape ra **luôn** `["in", <list>]`; `type(out) is dict` |
| **TC-VSCOPE-11** | INV-VENDORSCOPE-2 (liên thông) | 〃 | `imm11._extract_asset_in_scope(out["asset"])` trả đúng IN-list ⇒ chứng minh `services/imm11.py:916` **không cần** đổi |
| **TC-VSCOPE-12** | INV-VENDORSCOPE-3 | 〃 | non-vendor · Guest · doctype ngoài map · bypass-role ⇒ **passthrough byte-identical** (`out is filters` hoặc `out == filters` + không thêm khoá) |
| **TC-VSCOPE-13** | INV-VENDORSCOPE-3 (0 hồi quy) | `test_rbac.py` | `test_apply_vendor_scope_*` (`:570-604`) XANH **không sửa một dòng** |
| **TC-VSCOPE-14** | §10.4 nhánh list | 〃 | `filters` dạng **list** ⇒ trả **list**, có thêm đúng 1 điều kiện `[<doctype thật>, field, "in", assigned]`; nhãn doctype **không** được là alias `Calibration Schedule`/`Calibration Record` (hoặc: test chứng minh nhánh list **không** tới được từ 5 call site — `AC-CR-109`) |
| **TC-VSCOPE-15** | INV-CONN-21 (enforce) | class mới trong `test_rowscope_invariant.py` | Vendor Engineer + deep-link 1 thiết bị: `list_calibration_schedules('{"asset":X}')`, `list_pm_work_orders('{"asset_ref":X}')`, `list_repair_work_orders('{"asset_ref":X}')` ⇒ **chỉ** dòng của X; thiết bị Y (cũng được giao) **vắng**. **ĐỎ trước fix** |
| **TC-IMM04-SCOPE-09** | INV-VENDORSCOPE-4 | `test_imm04.py` (chạy lại, **không sửa**) | `TestOverdueSlaLiveInvariant` (`:724+`, gồm `list_commissioning({"overdue":1})` `:786` và `{"overdue":1,"workflow_state":…}` `:861`) XANH ⇒ đường **filter-list form** đi qua engine đếm mới không hồi quy |
| **TC-IMM04-SCOPE-10** | ADR-…-05 D3 | `test_vendor_scope_intersect.py` hoặc guard | `count_with_or` annotation là `dict | list | None` ∧ gọi được với **list** filters (không `TypeError`) ∧ thân hàm **không** đổi logic |

### VIII.2 FE — xem [`06 §11.4`](./06_Frontend_Design.md): `TC-FE-COMM-SE-01..06` (file mới `CommissioningListView.scopedEmpty.test.ts`).

### VIII.3 Ràng buộc chấm (BẮT BUỘC — vi phạm = kết quả vô nghĩa)

- **Session user THẬT** `frappe.set_user(...)` cho mọi TC row-scope — `Administrator` bypass `permission_query_conditions` ⇒ **XANH GIẢ**.
- **CẤM** mock `frappe.get_list` / `frappe.db.count`: mock chứng minh chữ ký, không chứng minh predicate.
- **CẤM** phụ thuộc `vendor_engineer_name` khớp email (là field `Data`, không phải `Link → User` — nợ `AC-CR-108`); dùng `owner` để dựng ca "trong phạm vi".
- Fixture master **uuid-suffix** + `tearDownClass` dọn sạch (tên cố định tự chặn chính nó sau crash).
- Asset mới **luôn** có sẵn 1 `Asset Lifecycle Event` `qr_generated` (`ac_asset.py:83`) — đừng giả định "asset mới = 0 event".
- **DoD chấm bằng test module-isolated, KHÔNG curl** (blocked-reload gunicorn `--preload` — LL-DEPLOY-07/08); `timeout` tool **≥ 600000 ms**; chấm theo **DELTA đo từ đĩa** (baseline trong prompt/STATE luôn có thể stale).
- `QueryDeadlockError` do đa-phiên = **ĐỎ GIẢ** ⇒ chờ quiescence rồi chạy lại, **KHÔNG** "sửa cho xanh".
- **Run list:** `test_rowscope_scope_guard` · `test_rowscope_invariant` · `test_vendor_scope_intersect` (mới) · `test_imm04` · `test_rbac` · `test_connections_tree` · `test_connections_list_filter_parity` · `test_imm08` · `test_imm09` · `test_imm11` · `test_imm00`.
- `.py` prod đổi vòng này (`services/imm04.py`, `services/shared/scope.py`, `services/shared/filters.py`) ⇒ **bồi vào danh sách chờ `bench restart`** (blocker #1 STATE). **KHÔNG** `git commit` / `bench migrate` / `bench restart` / xoá dữ liệu prod.

---

## IX. AC-CR-112 — ĐÓNG NỢ VERIFY của §VIII: chạy thật 5+3 module + bịt nhánh `overdue=1` dưới row-scope (chốt 2026-07-30)

> **SSoT quyết định:** [`../imm-00/ADR-IMM00-LIST-SCOPE.md §11`](../imm-00/ADR-IMM00-LIST-SCOPE.md) (`ADR-IMM00-LIST-SCOPE-06/07` · `INV-COMM-SCOPE-5/6` · hạ cấp `INV-VENDORSCOPE-4` → `SMOKE-VENDORSCOPE-4`) · FE [`06 §11.5`](./06_Frontend_Design.md) · BE [`04 §11.1`](./04_Backend_Design.md).
>
> **Vòng này KHÔNG thiết kế lại gì.** Mã prod của AC-CR-98/AC-CR-106 đã có trên đĩa. Việc phải làm: **chạy** những gì §VIII prescribe (4 file test **chưa từng chạy**) và **thêm 2 TC BE + 2 TC FE** cho nhánh predicate duy nhất còn hở.

### IX.0 Baseline **đo từ đĩa 2026-07-30** — chấm theo DELTA (số trong prompt/STATE luôn có thể stale)

| Module / file | Baseline (đĩa) | Sau vòng này (kỳ vọng) | Git |
|---|---|---|---|
| `assetcore.tests.integration.test_vendor_scope_intersect` | **18** `def test_` | ≥ 18 (0 TC mới) | untracked |
| `assetcore.tests.guards.test_rowscope_scope_guard` | **11** | ≥ 11 (0 TC mới) | untracked |
| `assetcore.tests.integration.test_rowscope_invariant` | **28** | **30** (+`TC-IMM04-OVD-01/02`) | untracked |
| `assetcore.tests.integration.test_rowscope_docperm_gate` | **22** | ≥ 22 (0 TC mới) | untracked |
| `assetcore.tests.imm04.test_imm04` | **110** | ≥ 110 (0 TC mới) | tracked |
| `assetcore.tests.imm08.test_imm08` · `test_imm09` · `test_imm11` | **196** · **278** · **136** | ≥ nguyên trạng | tracked |
| `CommissioningListView.scopedEmpty.test.ts` | **8** `it()` (8/8 PASS 14:59) | **≥ 10** (+`TC-FE-COMM-SE-07/08`) | untracked |
| Tổng file test FE | **287** `*.test.ts` | ≥ 287 | — |

**Số TC chạy được của mỗi module PHẢI ≥ baseline** — module chạy ra ít TC hơn = có TC bị skip/mất, **không** phải "chạy nhanh hơn".

### IX.1 Nghi thức chạy (A1 + A2) — **module-isolated**, `timeout` tool ≥ **600000 ms** MỖI lần

```bash
# A1 — 5 suite cốt lõi (GATE: 0 failures ∧ 0 errors ∧ N ≥ baseline cho CẢ 5)
bench --site miyano run-tests --module assetcore.tests.integration.test_vendor_scope_intersect
bench --site miyano run-tests --module assetcore.tests.guards.test_rowscope_scope_guard
bench --site miyano run-tests --module assetcore.tests.integration.test_rowscope_invariant
bench --site miyano run-tests --module assetcore.tests.integration.test_rowscope_docperm_gate
bench --site miyano run-tests --module assetcore.tests.imm04.test_imm04
# A2 — 3 suite CALL-SITE của apply_vendor_scope (GÁN→GIAO chạm 5 call site:
#   api/imm00.py:413 · api/imm08.py:39 · api/imm09.py:36 · api/imm11.py:30 + :83)
bench --site miyano run-tests --module assetcore.tests.imm08.test_imm08
bench --site miyano run-tests --module assetcore.tests.imm09.test_imm09
bench --site miyano run-tests --module assetcore.tests.imm11.test_imm11
```

- **Bằng chứng bắt buộc:** dán **nguyên văn** dòng `Ran N tests in …s` + `OK` của **từng** module. Không có dòng đó ⇒ coi như **chưa chạy** (`ADR-IMM00-LIST-SCOPE-06`).
- **A2-bis (khuyến nghị, KHÔNG chặn):** `test_rbac` · `test_connections_tree` · `test_connections_list_filter_parity` · `test_imm00` — 4 module còn lại của DoD §VIII.3 mà cũng chưa có bằng chứng chạy. Chạy nếu còn thời gian; **không** được ghi «§VIII DoD đạt đủ» khi chưa chạy chúng.
- **KHÔNG `curl`** để chấm (gunicorn `--preload` ⇒ HTTP lệch đĩa — LL-DEPLOY-07/08). **KHÔNG** `bench restart` / `bench migrate` / `git commit`.
- `QueryDeadlockError` (đa-phiên) = **ĐỎ GIẢ** ⇒ chờ quiescence rồi chạy lại; ghi rõ trong báo cáo, **KHÔNG** "sửa cho xanh".

### IX.2 BE — 2 TC MỚI (A3): nhánh `overdue=1` **list-form** dưới persona row-scoped

**Nơi đặt:** **class MỚI** `TestCommissioningOverdueRowScope` trong `assetcore/tests/integration/test_rowscope_invariant.py` (read-fresh rồi **append** — file đang dirty ở phiên khác). **CẤM** sửa/dùng lại fixture của `TestCommissioningOneEngineScope` (`:776`) vì fixture đó **không** set `reception_date` và 3 TC của nó khẳng định tập dòng chính xác ⇒ thêm phiếu vào đó = làm ĐỎ TC đang xanh.

**Fixture bắt buộc (uuid-suffix, `tearDownClass` dọn sạch; `_OVERDUE_ANCHOR="reception_date"` `services/imm04.py:64` · `OVERDUE_DAYS=30` `:63`):**

| Phiếu | `owner` | `workflow_state` | `reception_date` | Vai trò trong assert |
|---|---|---|---|---|
| `own_overdue_1` | persona | `To Be Installed` | `today-35` | **đếm** (trong phạm vi ∧ quá hạn) |
| `own_overdue_hold` | persona | `Clinical Hold` | `today-35` | đếm ∧ ca conjoin `workflow_state` |
| `own_in_window` | persona | `Installing` | `today-1` | **loại** ⇒ predicate overdue thật sự lọc (chống vacuous) |
| `own_terminal` | persona | `Clinical Release` | `today-35` | **loại** ⇒ `workflow_state not in` còn sống |
| `foreign_overdue` | `Administrator` | `To Be Installed` | `today-35` | **loại** ⇒ mutation M1/M2 ĐỎ có thật (nếu thiếu dòng này, `db.count` có thể tình cờ bằng ⇒ mutation không ĐỎ) |

> Persona = user MỚI có `AssetCore System User` + **`Commissioning User`** + **`Vendor Engineer`** (§VIII.3: vendor **thuần** không có DocPerm read ⇒ dừng ở lớp ROLE, không kiểm được row-scope). Phiếu "trong phạm vi" dựng bằng **`owner`** (`frappe.set_user` khi insert) — **CẤM** dựa vào `vendor_engineer_name` khớp email (`AC-CR-108`).

| TC | Bất biến | Phát biểu chấm được |
|---|---|---|
| **TC-IMM04-OVD-01** | **INV-COMM-SCOPE-5** | `frappe.set_user(persona)`; `svc.list_commissioning({"overdue": 1}, page=1, page_size=100)` ⇒ (a) `pagination.total == len(items)`; (b) `foreign_overdue ∉ items`; (c) `{own_overdue_1, own_overdue_hold} ⊆ items` ∧ `own_in_window ∉` ∧ `own_terminal ∉`; (d) lặp `page_size=1` ⇒ `len(items) == 1` ∧ `pagination.total ==` số dòng row-scoped (2 trong fixture), **KHÔNG** phải tổng toàn bảng |
| **TC-IMM04-OVD-02** | **INV-COMM-SCOPE-6** | cùng persona; `{"overdue": 1, "workflow_state": "Clinical Hold"}` ⇒ chỉ `own_overdue_hold`; `pagination.total == len(items)`; mọi dòng có `workflow_state == "Clinical Hold"`; `own_overdue_1 ∉` (chứng minh **AND**, không clobber). Assert **≥1** dòng (chống vacuous) |

**Ràng buộc chấm:** session user THẬT (`Administrator` bypass hook `permissions.py:140` ⇒ XANH GIẢ) · **CẤM** mock `frappe.get_list`/`frappe.db.count` · assert dùng **delta trên tập fixture** (`& set(fixture_names)`) vì DB dev là data-live, nhưng (a) và (d) phải so trên **toàn bộ** `pagination.total`/`items` mới bắt được count thừa.

### IX.3 Proof-by-mutation (A3/A5 — thiếu = DoD KHÔNG đạt)

| # | Mutate mã prod | Kỳ vọng | Ghi lại |
|---|---|---|---|
| **M1** | `services/imm04.py:1113` → `total = frappe.db.count(_DT, query_filters)` | **ĐỎ** TC-IMM04-OVD-01 | **dán nguyên văn** output ĐỎ. `db.count` nổ với list-form ⇒ ĐỎ dạng *error* — vẫn tính, ghi rõ loại |
| **M2** | 〃 → `total = count_ignore_permissions(_DT, query_filters, None)` | **ĐỎ** TC-IMM04-OVD-01 (cùng shape ⇒ cô lập nguyên nhân row-scope) | 1 dòng kết luận |
| **M3** | `services/imm04.py:1102` → bỏ list-form, `safe_filters.update(overdue_commissioning_filter())` | **ĐỎ** TC-IMM04-OVD-02 | 1 dòng |
| **M4** | `CommissioningListView.vue:199` → `Tổng ${store.list.length} phiếu` | **ĐỎ** TC-FE-COMM-SE-07 | dán nguyên văn |

Sau mỗi mutation: **hoàn nguyên** (`git diff` phải sạch phần mutation) rồi chạy lại ⇒ XANH.

### IX.4 A4 — 7 TC đang có phải XANH THẬT (không sửa một ký tự)

| TC (file `test_rowscope_invariant.py`) | Dòng | Phát biểu phải giữ |
|---|---|---|
| `test_inv_conn_21_pm_deep_link_returns_only_that_asset` | `:1111` | deep-link 1 thiết bị ⇒ chỉ phiếu PM của **chính** thiết bị đó |
| `test_inv_conn_21_repair_deep_link_returns_only_that_asset` | `:1123` | 〃 cho phiếu sửa chữa |
| `test_inv_conn_21_calibration_schedule_deep_link_returns_only_that_asset` | `:1131` | 〃 cho lịch hiệu chuẩn |
| `test_inv_conn_21_out_of_scope_asset_yields_zero_rows_not_403` | `:1144` | thiết bị ngoài phạm vi ⇒ **0 dòng**, **KHÔNG 403**, **KHÔNG** "mọi thiết bị của tôi" (ratify §11.4) |
| `test_inv_comm_scope_2_vendor_never_sees_foreign_commissioning` | `:929` | hết rò dữ liệu |
| `test_inv_comm_scope_3_total_equals_rows_all_personas` | `:946` | `count == rows` 3 persona, 2 nhánh phân trang |
| `test_inv_conn_27_cell_total_equals_drill_plus_cancelled` | `:977` | ô đếm == drill + `#{docstatus==2}` (dung sai `AC-CR-99`) |

### IX.5 FE (A5) — xem [`06 §11.5`](./06_Frontend_Design.md): `TC-FE-COMM-SE-07/08` (8 → **≥10** `it()`); `npx vitest run` toàn bộ **0 fail** + `npx vue-tsc --noEmit` **0 error**.

### IX.6 ĐỎ **CẤM SỬA** vòng này (chỉ báo cáo + backlog, kèm bằng chứng `grep`)

alias `Calibration Record`/`Calibration Schedule` (`AC-CR-109`) · vendor-IDOR IMM-11 · `assert_vendor_can_access` · `_VENDOR_SCOPE_FIELD_MAP` · `http_status` 400-vs-403 · whitelist `filters` IMM-11 · cổng G01–G06 · mobile OAS · notification.

**OUT-OF-SCOPE (0 đổi):** 3 counter `test_mobile_oas` (`_EXPECTED_TEST_COUNT` / `_GUARD_SUITE_SUM` / `_MOBILE_OAS_TOTAL` — vòng này **0** đổi OAS ⇒ **0** đổi counter) · tiebreaker ALE `api/imm00.py:293` (`AC-CR-100`) · `AC-CR-99` · Việt hoá `PREVIEW_FIELDS` · tab «Bản ghi liên quan» · 403 ba nhánh vận hành · prefill nháp. **AC-CR-112 KHÔNG vào sổ `docs/imm-09/05 §10.4`** (sổ đó dành cho CR contract/OAS mobile; vòng này 0 đổi OAS).

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
- [x] CI command chạy clean (`bench run-tests --module assetcore.tests.imm04.test_imm04`)
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
