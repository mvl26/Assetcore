# AssetCore — Backend Readiness Audit

| Thuộc tính | Giá trị |
|---|---|
| Tài liệu | BE Readiness Audit — DocType & API Design |
| Phiên bản | 1.0.0 |
| Ngày | 2026-04-18 |
| Phạm vi | IMM-00, IMM-04, IMM-05, IMM-08, IMM-09, IMM-11, IMM-12 |
| Tác giả | AssetCore Team (Claude Code audit) |

---

## Kết luận tổng quan

**OVERALL READINESS: PARTIAL**

| Module | DocTypes | API Endpoints | Service Functions | Workflow | BR Enforced | Verdict |
|---|---|---|---|---|---|---|
| **IMM-00** (Foundation) | 13/13 ✅ | N/A (lib) | 11/11 ✅ | N/A | 10/10 ✅ | **READY** ✅ |
| **IMM-04** (Install) | 5/5 ✅ | 17/17 ✅ | 11/11 ✅ | ✅ JSON | 8/8 ✅ | **READY** ✅ |
| **IMM-05** (Document) | 3/3 ✅ | 14/14 ✅ | 3/3 (controller) | ✅ JSON | 10/10 ✅ | **READY** ✅ |
| **IMM-08** (PM) | 6/6 ✅ | 9/9 ✅ | 2/2 ✅ | controller SM | 10/10 ✅ | **READY** ✅ |
| **IMM-09** (Repair) | 4/4 ✅ | 12/12 ✅ | 13/13 ✅ | controller SM | 7/7 ✅ | **READY** ✅ |
| **IMM-11** (Calibration) | 0/3 ❌ | 0/? ❌ | 0/8 ❌ | ❌ | 0/7 ❌ | **NOT READY** ❌ |
| **IMM-12** (Incident/CAPA) | 1/4 ⚠️ | 0/? ❌ | 2/8 ⚠️ | ❌ | 2/7 ⚠️ | **PARTIAL** ⚠️ |

**→ Bắt đầu thiết kế API ngay cho IMM-04, 05, 08, 09** (52 endpoint đã sẵn, DocType đầy đủ).  
**→ IMM-12:** Thiết kế Incident CRUD có thể bắt đầu; RCA workflows bị block.  
**→ IMM-11:** Chưa có code nào — cần implement 3 sprint trước khi thiết kế API.

---

## 1. Foundation Layer — IMM-00

### DocTypes (13/13 ✅)

| Category | DocType | Naming | Status |
|---|---|---|---|
| Core | AC Asset | `AC-ASSET-.YYYY.-.#####` | ✅ 63+ fields |
| Core | AC Supplier | `AC-SUP-.YYYY.-.####` | ✅ |
| Core | AC Location | `AC-LOC-.YYYY.-.####` | ✅ |
| Core | AC Department | `AC-DEPT-.####` | ✅ |
| Core | AC Asset Category | by category_name | ✅ |
| Native | IMM Device Model | `IMM-MDL-.YYYY.-.####` | ✅ 43 fields |
| Native | IMM SLA Policy | by policy_name | ✅ |
| Native | IMM Audit Trail | `IMM-AUD-.YYYY.-.#######` | ✅ Append-only, SHA-256 |
| Native | IMM CAPA Record | `CAPA-.YYYY.-.#####` | ✅ ~50 fields |
| Native | Asset Lifecycle Event | `ALE-.YYYY.-.#######` | ✅ Immutable |
| Native | Incident Report | `IR-.YYYY.-.####` | ✅ 30+ fields |
| Child | IMM Device Spare Part | (child) | ✅ |
| Child | AC Authorized Technician | (child) | ✅ |

### Service Functions (11/11 ✅)

- `log_audit_event()` — SHA-256 chain, immutable
- `create_lifecycle_event()` — event types defined
- `transition_asset_status()` — cascades suspend schedules
- `validate_asset_for_operations()` — gate for operations
- `get_sla_policy()` — priority × risk_class matrix
- `create_capa()` / `close_capa()` — CAPA lifecycle
- `check_capa_overdue()` — daily scheduler
- `check_vendor_contract_expiry()` / `check_registration_expiry()` — daily
- `rollup_asset_kpi()` — monthly

### Business Rules (10/10 ✅)

BR-00-01 đến BR-00-10 đều đã được enforce qua service layer.

---

## 2. IMM-04 — Lắp đặt & Định danh

**Trạng thái:** LIVE — 31/32 UAT PASS

### DocTypes (5/5 ✅)

| DocType | Type | Status |
|---|---|---|
| Asset Commissioning | Submittable | ✅ Full JSON + controller |
| Commissioning Checklist | Child | ✅ |
| Commissioning Document Record | Child | ✅ |
| Asset Lifecycle Event | Shared (IMM-00) | ✅ |
| Asset QA Non Conformance | Independent | ✅ |

**Field completeness — Asset Commissioning:** Tất cả sections đầy đủ: procurement, installation, identification, QA, baseline tests, documents, workflow state, risk classification, radiation flags, QR code fields.

### API Endpoints (17/17 ✅)

File: `assetcore/api/imm04.py`

Endpoints: list, get, create, update, approve, validate, generate_qr, dashboard_stats + NC management, timeline, PO lookup.

### Service Layer (11/11 ✅)

File: `assetcore/services/imm04.py`

Functions: `initialize_commissioning`, `validate_commissioning`, VR-01→VR-07, gate validations G01→G06, schedulers.

### Workflow JSON ✅

File: `imm_04_workflow.json` — 11 states, 14 transitions.

States: Draft → Pending Doc Verify → To Be Installed → Installing → Identification → Initial Inspection → [Clinical Hold / Re Inspection] → Clinical Release / Return To Vendor

### Business Rules (8/8 ✅)

BR-04-01 → BR-04-08 đầy đủ (mint_core_asset, GW gates, unique serial, baseline test, board approver).

### Issues tồn đọng ⚠️

- TC-32 FAIL: PM auto-create hook fires event nhưng IMM-08 listener chưa active
- Print Format Biên bản Bàn giao (PDF) chưa generate

**→ VERDICT: READY FOR API DESIGN** ✅

---

## 3. IMM-05 — Document Repository

**Trạng thái:** LIVE

### DocTypes (3/3 ✅)

| DocType | Type | Status |
|---|---|---|
| Asset Document | Submittable | ✅ 30 fields, 12 sections |
| Document Request | Operational | ✅ Full JSON |
| Required Document Type | Master config | ✅ |

**Field completeness — Asset Document:** Đầy đủ: Liên kết Thiết bị, Phân loại, Hiệu lực, File, Phê duyệt, Version Control, Quyền truy cập, Exempt.

### API Endpoints (14/14 ✅)

File: `assetcore/api/imm05.py`

Endpoints: list_documents, get, create, update, approve, reject, get_asset_documents, dashboard_stats, expiring_documents, compliance_by_dept, document_history, create_request, get_requests, mark_exempt.

### Service Layer ⚠️

**Tech Debt:** `services/imm05.py` không tồn tại — logic nằm trong controller + `tasks.py`.

Schedulers trong `tasks.py`:
- `check_document_expiry` (90/60/30/0 days, idempotent via Expiry Alert Log)
- `update_asset_completeness`
- `check_overdue_document_requests`

### Workflow JSON ✅

File: `imm_05_document_workflow.json` — 6 states, 10 transitions.

States: Draft → Pending Review → Active → [Archived / Expired / Rejected]

### Business Rules (10/10 ✅)

BR-05-01 → BR-05-10 đầy đủ (auto-archive, no hard delete, expiry alerts, auto-import từ IMM-04, GW-2 gate, visibility filter).

### Issues tồn đọng ⚠️

- `services/imm05.py` cần extract (tech debt — không block API)
- Email notification templates inline trong `tasks.py` (nên là fixtures)
- Dashboard KPI frontend component chưa có (API đã sẵn)

**→ VERDICT: READY FOR API DESIGN** ✅

---

## 4. IMM-08 — Preventive Maintenance

**Trạng thái:** LIVE

### DocTypes (6/6 ✅)

| DocType | Type | Status |
|---|---|---|
| PM Schedule | Master, non-submittable | ✅ |
| PM Checklist Template | Master, non-submittable | ✅ |
| PM Work Order | Submittable | ✅ Full JSON + controller |
| PM Task Log | Audit, in_create=1 | ✅ |
| PM Checklist Item | Child | ✅ |
| PM Checklist Result | Child | ✅ |

**Field completeness — PM Work Order:** Đầy đủ: asset_ref, pm_schedule, pm_type, wo_type, status (7 states), due_date, completion_date, assigned_to/by, overall_result, checklist_results, source_pm_wo.

### API Endpoints (9/9 ✅)

File: `assetcore/api/imm08.py` (459 lines)

### Service Layer (2/2 ✅)

File: `assetcore/services/imm08.py`

- `generate_pm_work_orders` — daily scheduler
- `check_pm_overdue` — daily scheduler

Controller: `pm_work_order.py` — validate(), on_submit() với checklist validation, PM schedule advancement, CM auto-creation.

### Business Rules (10/10 ✅)

BR-08-01 → BR-08-10 đầy đủ (PM template required, CM phải có source, next_pm_date calculation, Out of Service block, 100% checklist before submit, Fail → CM priority mapping).

### Issues tồn đọng ⚠️

- Wave 1 vẫn dùng ERPNext Asset core + custom_* fields (migration lên AC Asset pending v3)
- IMM-04 → IMM-08 hook: fire_release_event() tồn tại nhưng listener chưa active

**→ VERDICT: READY FOR API DESIGN** ✅

---

## 5. IMM-09 — Corrective Maintenance / Repair

**Trạng thái:** LIVE

### DocTypes (4/4 ✅)

| DocType | Type | Status |
|---|---|---|
| Asset Repair | Submittable | ✅ Full JSON + controller |
| Spare Parts Used | Child | ✅ (bao gồm stock_entry_ref) |
| Repair Checklist | Child | ✅ |
| Firmware Change Request | Submittable | ✅ |

**Field completeness — Asset Repair:** Đầy đủ: Asset info, Source (incident + PM), Classification, Time tracking, SLA, Assignment, Diagnosis (diagnosis_notes, root_cause_category, repair_summary), Spare parts với stock_entry_ref, Repair checklist, Firmware section, Dept head confirmation.

### API Endpoints (12/12 ✅)

File: `assetcore/api/imm09.py` (411 lines)

### Service Layer (13/13 ✅)

File: `assetcore/services/imm09.py`

Functions: validate_repair_source, validate_asset_not_under_repair, check_repeat_failure, set_asset_under_repair, validate_spare_parts_stock_entries, validate_firmware_change_request, validate_repair_checklist_complete, get_sla_target, complete_repair.

Schedulers: `check_repair_sla_breach` (hourly), `check_repair_overdue` (daily), `update_asset_mttr_avg` (monthly).

### SLA Matrix ✅

| Risk Class | Critical | Urgent | Normal |
|---|---|---|---|
| Class III | 4h | 24h | 120h |
| Class II | 8h | 48h | 72h |
| Class I | 24h | 72h | 480h |

### Business Rules (7/7 ✅)

BR-09-01 → BR-09-07: repair source, stock_entry_ref, FCR approval, 100% checklist, asset status transitions, repeat failure detection (30-day window), SLA breach + MTTR.

### Issues tồn đọng ⚠️

- Post-repair calibration trigger → IMM-11 pending (IMM-11 chưa implement)

**→ VERDICT: READY FOR API DESIGN** ✅

---

## 6. IMM-11 — Calibration / Hiệu chuẩn

**Trạng thái:** DRAFT — chưa có code nào

### DocTypes (0/3 ❌)

| DocType | Status |
|---|---|
| IMM Calibration Schedule | ❌ KHÔNG TỒN TẠI |
| IMM Asset Calibration | ❌ KHÔNG TỒN TẠI |
| IMM Calibration Measurement (child) | ❌ KHÔNG TỒN TẠI |

Custom fields trên AC Asset (`custom_imm_calibration_status`, `custom_imm_next_calibration_date`, `custom_imm_last_calibration_date`) — ❌ chưa có.

### Service Layer (0/8 ❌)

`services/imm11.py` — **KHÔNG TỒN TẠI**

8 functions pending implementation:
- `create_calibration_schedule_from_commissioning`
- `create_due_calibration_wos`
- `check_calibration_expiry`
- `handle_calibration_pass` / `handle_calibration_fail`
- `perform_lookback_assessment`
- `create_post_repair_calibration`
- `compute_measurement_results`

### API Layer (0/? ❌)

`api/imm11.py` — **KHÔNG TỒN TẠI**

### Business Rules (0/7 ❌)

BR-11-01 → BR-11-07 pending: ISO 17025 validation, Fail → Out of Service + CAPA, lookback assessment, next date calculation, immutable records, decommissioned → suspend, gate validation.

### Dependencies sẵn có từ IMM-00 ✅

IMM-00 foundation đầy đủ để support IMM-11 sau khi implement:
- `AC Supplier` có `iso_17025_certified` field
- `IMM Device Model` có `calibration_interval_days`
- `create_capa`, `log_audit_event`, `transition_asset_status`, `create_lifecycle_event`

### Roadmap bắt buộc trước khi thiết kế API

| Sprint | Hạng mục |
|---|---|
| 11.1 | DocType JSON scaffold: IMM Calibration Schedule, IMM Asset Calibration, IMM Calibration Measurement + custom fields trên AC Asset |
| 11.2 | `services/imm11.py` — 8 functions + integrate IMM-00 services |
| 11.3 | `api/imm11.py` + scheduler jobs + hooks |
| Sau 11.3 | ← **Bắt đầu thiết kế API contract** |

**→ VERDICT: NOT READY FOR API DESIGN** ❌  
Ước tính: cần 3 sprint trước khi API design có thể bắt đầu.

---

## 7. IMM-12 — Incident & Corrective Action (CAPA)

**Trạng thái:** DRAFT — code một phần (CAPA từ IMM-00 dùng được, Incident Report partial)

### DocTypes (1/4 ⚠️)

| DocType | Status | Ghi chú |
|---|---|---|
| Incident Report | ✅ Partial | Thiếu 4 extension fields |
| IMM CAPA Record | ✅ (từ IMM-00) | Đủ cho CAPA lifecycle |
| RCA Record | ❌ KHÔNG TỒN TẠI | Core cho IMM-12 |
| RCA Related Incident (child) | ❌ KHÔNG TỒN TẠI | |
| RCA Five Why Step (child) | ❌ KHÔNG TỒN TẠI | |

**Incident Report — fields hiện có:**

```
naming_series: IR-.YYYY.-.####
asset (Link, reqd), reported_by (Link User, reqd), reported_at (Datetime, reqd)
incident_type: Failure/Safety Event/Near Miss/Malfunction
severity: Low/Medium/High/Critical
status: Open/Under Investigation/Resolved/Closed
description (Text Editor, reqd), patient_affected (Check), patient_impact_description
reported_to_byt (Check), byt_report_date
linked_repair_wo, linked_capa (Link IMM CAPA Record)
root_cause_summary, resolution_notes, closed_date
```

**Fields còn thiếu theo spec:**  
`rca_method`, `rca_record` (Link RCA Record), `clinical_impact`, `chronic_failure_flag`

### Service Layer (2/8 ⚠️)

2 functions có sẵn từ IMM-00 (`create_capa`, `close_capa`).

`services/imm12.py` — **KHÔNG TỒN TẠI**

6 functions pending:
- `report_incident`
- `acknowledge_incident`
- `resolve_incident`
- `trigger_rca_if_required`
- `detect_chronic_failures` (scheduler)
- `submit_rca_and_create_capa`

### API Layer (0/? ❌)

`api/imm12.py` — **KHÔNG TỒN TẠI**

### Business Rules (2/7 ⚠️)

- ✅ BR-00-08, BR-00-09 (CAPA từ IMM-00) đang enforce
- ❌ BR-12-01 → BR-12-05 (IMM-12 specific) pending

### Phân tích khả thi theo Phase

**Phase 1 — có thể bắt đầu ngay:**
- Incident CRUD API (create, get, list, update status)
- Basic CAPA lifecycle (delegate to IMM-00 services)
- Ước tính: 1 sprint

**Phase 2 — bị block:**
- RCA workflow API (trigger_rca, submit rca, 5-why)
- Chronic failure detection (scheduler)
- Cần: RCA Record DocType + `services/imm12.py`

### Roadmap bắt buộc

| Sprint | Hạng mục |
|---|---|
| 12.1 | Custom fields extension Incident Report (4 fields) |
| 12.2 | RCA Record DocType + child tables |
| 12.3 | `services/imm12.py` (6 functions) |
| 12.4 | `api/imm12.py` REST endpoints (merge Phase 1 + Phase 2) |
| 12.5 | Scheduler `detect_chronic_failures` |

**→ VERDICT: PARTIAL — Incident CRUD có thể bắt đầu; RCA/CAPA complex bị block** ⚠️

---

## 8. Tech Debt Tổng hợp (không block API design)

| # | Module | Issue | Priority |
|---|---|---|---|
| TD-01 | IMM-05 | `services/imm05.py` chưa tách khỏi controller | Medium |
| TD-02 | IMM-05 | Email templates inline trong `tasks.py` (nên là fixtures) | Low |
| TD-03 | IMM-04/08/09 | Dùng ERPNext Asset core + custom_* fields (migration lên AC Asset pending v3) | Medium |
| TD-04 | IMM-04→08 | PM Schedule auto-create: fire_release_event() tồn tại nhưng IMM-08 listener chưa active (TC-32 FAIL) | High |
| TD-05 | IMM-09→11 | Post-repair calibration trigger pending (IMM-11 phải implement trước) | Blocked |

---

## 9. Kế hoạch hành động

### Tuần 1–2 — NGAY (IMM-04/05/08/09 API Contract)

- [ ] Viết OpenAPI 3.0 spec cho 52 endpoints hiện có
- [ ] Cross-check IMM-00 foundation service calls (14+ cross-module calls)
- [ ] Fix TD-04: activate IMM-08 listener cho PM Schedule creation
- [ ] Fix TD-01: extract `services/imm05.py`

### Tuần 2–3 — Song song (IMM-11 DocType scaffold)

- [ ] Implement Sprint 11.1: 3 DocType JSON + custom fields AC Asset
- [ ] Implement Sprint 11.2: `services/imm11.py` (8 functions)
- [ ] Sau đó: bắt đầu API design IMM-11

### Tuần 3–4 — Song song (IMM-12 Phase 1 + Phase 2)

- [ ] Implement Sprint 12.1: Extension fields Incident Report
- [ ] Implement Sprint 12.2: RCA Record DocType
- [ ] Implement Sprint 12.3: `services/imm12.py`
- [ ] Viết API contract Phase 1 (Incident CRUD) ngay tuần 3
- [ ] Merge API contract Phase 2 (RCA) tuần 5

---

*Audit thực hiện bởi Claude Code — 2026-04-18. Verify lại trước mỗi sprint bằng cách đọc source code trực tiếp.*
