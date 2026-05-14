# AssetCore Frontend — Router & Navigation Map

| Thuộc tính | Giá trị |
|---|---|
| Tài liệu | Frontend Router, Navigation Flow & Business Logic |
| Phiên bản | 1.0.0 |
| Ngày | 2026-04-19 |
| Phạm vi | IMM-00 (Master Data) · IMM-04 (Commissioning) · IMM-05 (Document) · IMM-08 (PM) · IMM-09 (CM/Repair) |
| Router source | `frontend/src/router/index.ts` (399 dòng, ~35 routes) |
| Phụ thuộc docs | `docs/imm-00/…`, `docs/imm-04/…`, `docs/imm-05/…`, `docs/imm-08/…`, `docs/imm-09/…` |

---

## 0. Kiến trúc điều hướng

**Layout chính:** `DefaultLayout.vue` (sidebar + topbar) — dùng cho mọi route trừ `/login` (dùng `AuthLayout.vue`).

**Auth guard:** `router.beforeEach` check session → redirect `/login` nếu chưa login.

**Sidebar Navigation Groups** (theo flow nghiệp vụ HTM):

```
🏠 Dashboard         → /dashboard

📦 Master Data (IMM-00)
 ├── Thiết bị        → /assets
 ├── Nhà cung cấp    → /suppliers
 ├── Device Model    → /device-models
 ├── SLA Policy      → /sla-policies
 └── Reference Data  → /reference-data

🚚 IMM-04 — Tiếp nhận
 ├── Dashboard       → /dashboard (shared)
 ├── Danh sách phiếu → /commissioning
 └── Tạo phiếu mới   → /commissioning/new

📄 IMM-05 — Hồ sơ
 ├── Quản lý tài liệu → /documents
 ├── Yêu cầu tài liệu → /documents/requests
 └── Audit Trail     → /audit-trail

🔧 IMM-08 — Bảo trì định kỳ (PM)
 ├── Dashboard PM    → /pm/dashboard
 ├── Lịch PM         → /pm/calendar
 ├── Work Orders     → /pm/work-orders
 ├── PM Schedule     → /pm/schedules
 └── PM Template     → /pm/templates

🛠 IMM-09 — Sửa chữa (CM)
 ├── Dashboard CM    → /cm/dashboard
 ├── Tạo WO sửa chữa → /cm/create
 ├── Work Orders     → /cm/work-orders
 ├── Firmware CR     → /cm/firmware
 └── MTTR report     → /cm/mttr

🚨 Sự cố & CAPA
 ├── Sự cố          → /incidents
 └── CAPA           → /capas

📤 Khác
 ├── Luân chuyển    → /asset-transfers
 ├── Hợp đồng DV    → /service-contracts
 ├── Hiệu chuẩn     → /calibration
 └── Khấu hao       → /depreciation
```

---

## 1. Bản đồ Route đầy đủ

### 1.1 Auth & Root

| Path | Name | View file | Auth |
|---|---|---|---|
| `/login` | Login | `LoginView.vue` | Public |
| `/` | — | redirect → `/dashboard` | Required |
| `/dashboard` | Dashboard | `DashboardView.vue` | Required |

### 1.2 IMM-00 — Master Data

| Path | Name | View | Mục đích |
|---|---|---|---|
| `/assets` | AssetList | `AssetListView.vue` | Danh sách AC Asset (phân trang, filter theo status/dept) |
| `/assets/new` | AssetCreate | `AssetCreateView.vue` | Form tạo AC Asset trực tiếp (hiếm — thường tạo qua IMM-04) |
| `/assets/:id` | AssetDetail | `AssetDetailView.vue` | Chi tiết thiết bị + tabs: Overview, Docs (IMM-05), PM (IMM-08), CM (IMM-09), Lifecycle |
| `/suppliers` | SupplierList | `SupplierListView.vue` | Danh sách AC Supplier |
| `/suppliers/new` | SupplierCreate | `SupplierFormView.vue` | Tạo NCC |
| `/suppliers/:id` | SupplierEdit | `SupplierFormView.vue` | Sửa NCC (component dùng chung mode new/edit) |
| `/device-models` | DeviceModelList | `DeviceModelListView.vue` | Danh sách IMM Device Model |
| `/device-models/new` | DeviceModelCreate | `DeviceModelFormView.vue` | Tạo Device Model (PM interval, calibration defaults, risk class) |
| `/device-models/:id` | DeviceModelEdit | `DeviceModelFormView.vue` | Sửa Device Model |
| `/sla-policies` | SlaPolicyList | `SlaPolicyListView.vue` | Matrix SLA theo priority × risk class |
| `/reference-data` | ReferenceData | `ReferenceDataView.vue` | AC Location, AC Department, AC Asset Category |

### 1.3 IMM-04 — Commissioning

| Path | Name | View | Mục đích |
|---|---|---|---|
| `/commissioning` | CommissioningList | `CommissioningListView.vue` | Danh sách phiếu, filter theo workflow_state |
| `/commissioning/new` | CommissioningCreate | `CommissioningCreateView.vue` | Tạo phiếu từ PO (7 section: Procurement, Installation, Identification, QA, Baseline, Docs, Output) |
| `/commissioning/:id` | CommissioningDetail | `CommissioningDetailView.vue` | Chi tiết phiếu + action buttons theo state (Start Install, Baseline Submit, Release, Hold, NC…) |
| `/commissioning/:id/nc` | CommissioningNC | `CommissioningNCView.vue` | Danh sách NC liên quan phiếu, form báo DOA, đóng NC |
| `/commissioning/:id/timeline` | CommissioningTimeline | `CommissioningTimelineView.vue` | Audit trail lifecycle events (immutable, SHA-256 chain) |

### 1.4 IMM-05 — Document Repository

| Path | Name | View | Mục đích |
|---|---|---|---|
| `/documents` | DocumentManagement | `DocumentManagement.vue` | Grid toàn bộ Asset Document (filter theo asset, category, status) |
| `/documents/new` | DocumentCreate | `DocumentCreateView.vue` | Upload tài liệu mới (Legal/Technical/Certification/Training/QA) |
| `/documents/view/:name` | DocumentDetail | `DocumentDetailView.vue` | Chi tiết + version history + Approve/Reject (workflow) |
| `/documents/asset/:assetId` | DocumentsByAsset | (redirect filter) | Xem tài liệu của 1 asset (query `?asset=...`) |
| `/documents/requests` | DocumentRequestList | `DocumentRequestListView.vue` | Yêu cầu tài liệu từ NCC (Document Request) |
| `/audit-trail` | AuditTrail | `AuditTrailListView.vue` | IMM Audit Trail (ISO 13485 §4.2.5) |

### 1.5 IMM-08 — Preventive Maintenance

| Path | Name | View | Mục đích |
|---|---|---|---|
| `/pm/dashboard` | PMDashboard | `PMDashboardView.vue` | KPI: % PM on-time, overdue, due 7/30 ngày |
| `/pm/calendar` | PMCalendar | `PMCalendarView.vue` | Lịch PM theo tháng (drag-drop reschedule) |
| `/pm/work-orders` | PMWorkOrderList | `PMWorkOrderListView.vue` | Danh sách PM WO (7 state: Open, In Progress, Pending-Device Busy, Overdue, Completed, Halted-Major Failure, Cancelled) |
| `/pm/work-orders/:id` | PMWorkOrderDetail | `PMWorkOrderDetailView.vue` | Chi tiết WO + checklist form + overall_result |
| `/pm/schedules` | PmScheduleList | `PmScheduleListView.vue` | PM Schedule master (next_pm_date auto-calc) |
| `/pm/templates` | PmTemplateList | `PmTemplateListView.vue` | PM Checklist Template |

### 1.6 IMM-09 — Corrective Maintenance (Repair)

| Path | Name | View | Mục đích |
|---|---|---|---|
| `/cm/dashboard` | CMDashboard | `CMDashboardView.vue` | KPI: SLA compliance, MTTR, repeat failures |
| `/cm/create` | CMCreate | `CMCreateView.vue` | Tạo repair WO từ Incident / PM Fail-Major |
| `/cm/work-orders` | CMWorkOrderList | `CMWorkOrderListView.vue` | Danh sách Asset Repair (8 state: Open → Assigned → Diagnosing → [Pending Parts/In Repair] → Pending Inspection → Completed/Cannot Repair) |
| `/cm/work-orders/:id` | CMWorkOrderDetail | `CMWorkOrderDetailView.vue` | Chi tiết + transition buttons theo state |
| `/cm/work-orders/:id/diagnose` | CMDiagnose | `CMDiagnoseView.vue` | Form chẩn đoán (diagnosis_notes, root_cause_category) |
| `/cm/work-orders/:id/parts` | CMParts | `CMPartsView.vue` | Quản lý spare parts + stock_entry_ref (BR-09-02) |
| `/cm/work-orders/:id/checklist` | CMChecklist | `CMChecklistView.vue` | Repair checklist (BR-09-04: 100% Pass trước submit) |
| `/cm/firmware` | FirmwareCrList | `FirmwareCrListView.vue` | Firmware Change Request (BR-09-03) |
| `/cm/mttr` | CMMttr | `CMMttrView.vue` | MTTR report theo khoa/model |

### 1.7 Incident & CAPA

| Path | Name | View | Mục đích |
|---|---|---|---|
| `/incidents` | IncidentList | `IncidentListView.vue` | Danh sách Incident Report |
| `/incidents/new` | IncidentCreate | `IncidentCreateView.vue` | Báo sự cố (severity Critical → auto CAPA) |
| `/incidents/:id` | IncidentDetail | `IncidentDetailView.vue` | Chi tiết + resolve/close |
| `/capas` | CAPAList | `CAPAListView.vue` | IMM CAPA Record |
| `/capas/:id` | CAPADetail | `CAPADetailView.vue` | Root cause + corrective + preventive (ISO 13485:8.5) |

### 1.8 Asset Transfer / Service Contract / Calibration / Depreciation

| Path | Name | View | Mục đích |
|---|---|---|---|
| `/asset-transfers` | AssetTransferList | `AssetTransferListView.vue` | Luân chuyển thiết bị giữa khoa |
| `/asset-transfers/new` | AssetTransferCreate | `AssetTransferCreateView.vue` | Form chuyển giao |
| `/asset-transfers/:id` | AssetTransferDetail | `AssetTransferDetailView.vue` | Chi tiết + approval |
| `/service-contracts` | ServiceContractList | `ServiceContractListView.vue` | Hợp đồng dịch vụ |
| `/service-contracts/new` | ServiceContractCreate | `ServiceContractCreateView.vue` | Tạo HĐ (PM/Calibration/Repair/Full Service/Warranty Extension) |
| `/service-contracts/:id` | ServiceContractDetail | `ServiceContractDetailView.vue` | Chi tiết |
| `/calibration` | CalibrationList | `CalibrationListView.vue` | (IMM-11 — DRAFT) |
| `/depreciation` | Depreciation | `DepreciationView.vue` | Khấu hao tài sản |

---

## 2. Navigation Flows — User Journey theo nghiệp vụ

### 2.1 Flow chính: Tiếp nhận thiết bị (IMM-04 → IMM-05 → IMM-08 kick-off)

```
[Dashboard]
    │
    │ click "+ Tạo phiếu" hoặc "Nhận hàng mới"
    ▼
[/commissioning/new]  ← HTM Technician tạo phiếu
    │  • LinkSearch: PO → auto-fill AC Supplier, items
    │  • LinkSearch: IMM Device Model → auto-fill risk_class, PM interval
    │  • LinkSearch: AC Department, AC Location
    │  • Pre-fill commissioning_documents mandatory (CO, CQ, Manual)
    │
    │ POST /api/method/assetcore.api.imm04.create_commissioning
    │ state: Draft
    ▼
[/commissioning/:id]
    │  ┌─ Action: "Xác nhận đủ tài liệu" (G01 validate CO/CQ/Manual = Received)
    │  │  state: Draft → Pending_Doc_Verify → To_Be_Installed
    │  │
    │  ├─ Action: "Bắt đầu lắp đặt"
    │  │  state: To_Be_Installed → Installing (installation_date auto set)
    │  │
    │  ├─ Action: "Định danh" (nhập vendor_serial_no + auto QR)
    │  │  state: Installing → Identification
    │  │  VR-01 check: SN unique trên AC Asset + Commissioning
    │  │
    │  ├─ Action: "Đo Baseline"  → tab Baseline Tests
    │  │  state: Identification → Initial_Inspection
    │  │  VR-03: 100% Pass/N/A; Fail → force Re_Inspection
    │  │
    │  ├─ Class C/D/Radiation → Auto → Clinical_Hold
    │  │  QA Officer upload qa_license_doc → clear_clinical_hold
    │  │
    │  ├─ Action: "Phê duyệt Release" (Workshop Head / VP Block2)
    │  │  G05: No open NC. G06: board_approver set. GW-2: IMM-05 có ĐKLH
    │  │  state: → Clinical_Release
    │  │
    │  └─ Submit:
    │     • mint_core_asset() → AC Asset tạo (navigate → /assets/<new>)
    │     • create_initial_document_set() → Asset Document draft cho mỗi doc Received
    │     • fire_release_event() → IMM-08 listener tạo PM Schedule
    │
    ▼
[/assets/:id]  ← Asset mới
    │  Tabs:
    │  • Overview: lifecycle_status=Commissioned, PM next_date
    │  • Documents → /documents?asset=<id>  (IMM-05)
    │  • PM → /pm/work-orders?asset=<id>    (IMM-08)
    │  • CM → /cm/work-orders?asset=<id>    (IMM-09)
    ▼
(sẵn sàng vận hành)
```

**Exception flows từ `/commissioning/:id`:**

| Nhánh | Trigger | Route |
|---|---|---|
| DOA | Nhận hàng bị hỏng → "Báo DOA" | `/commissioning/:id/nc` → tạo NC type=DOA, severity=Critical |
| Baseline Fail | Có ≥1 row test_result=Fail | Auto force state → `Re_Inspection` |
| Clinical Hold | Class C/D/Radiation sau Initial_Inspection | state → `Clinical_Hold`, button "Upload Giấy phép" |
| Return to Vendor | NC không khắc phục được | state → `Return_To_Vendor`, không mint Asset |
| Audit | Click "Xem lịch sử" | `/commissioning/:id/timeline` |

---

### 2.2 Flow: Quản lý Hồ sơ (IMM-05)

```
Entry 1: từ /commissioning/:id sau Release
    │ auto: create_initial_document_set() → draft docs
    ▼
[/documents?asset=ACC-ASS-2026-xxxxx]
    │ (query-filter view)
    │
Entry 2: từ sidebar "Hồ sơ" → /documents
    │
    ├─ Tạo mới: click "+ Tải lên" → /documents/new
    │  • LinkSearch AC Asset (hoặc check "Model-level" để bỏ qua)
    │  • 5 category: Legal, Technical, Certification, Training, QA
    │  • VR-01: expiry > issued
    │  • VR-09: version != 1.0 → cần change_summary
    │  • Legal/Certification → bắt buộc expiry_date
    │  • Upload file PDF/JPG/PNG/DOCX ≤ 25MB
    │  │
    │  │ POST /api/method/assetcore.api.imm05.create_document
    │  │ state: Draft
    │  ▼
    │  [/documents/view/<name>]
    │     │
    │     ├─ QA Risk Team click "Submit for Review"
    │     │  state: Draft → Pending_Review
    │     ├─ PTP Block2 "Approve" → state: Active
    │     │  BR-05-01: Auto archive phiên bản cũ
    │     └─ "Reject" → state: Rejected
    │
    ├─ Filter theo asset / category / expiry
    ├─ Badge màu: Active (xanh), Expiring<30d (vàng), Expired (đỏ)
    └─ Auto alert scheduler: check_document_expiry (90/60/30/0 day)

Entry 3: từ /commissioning/:id GW-2 block
    │ "Thiếu Chứng nhận ĐKLH" → click → /documents/new?asset=<id>&doc_type_detail=...
```

---

### 2.3 Flow: PM Work Order (IMM-08)

```
[/pm/dashboard]
    │ KPI cards: Due 7d (12), Overdue (3), On-time rate 94%
    │
    ├─ Click "Due 7d" → /pm/work-orders?status=Open&due_before=7d
    │
[/pm/work-orders]
    │ Filter theo asset, status, assigned_to
    │
    ▼
[/pm/work-orders/:id]
    │  state: Open
    │  │
    │  ├─ "Nhận việc" → Assigned
    │  ├─ "Bắt đầu" → In_Progress
    │  │   (nếu device busy → Pending-Device Busy)
    │  │
    │  ├─ Tab Checklist: fill PM Checklist Result
    │  │   BR-08-08: 100% rows có result
    │  │
    │  ├─ overall_result = Pass → submit → Completed
    │  │   • pm_schedule.last_pm_date = today
    │  │   • pm_schedule.next_pm_date = today + pm_interval_days
    │  │
    │  ├─ overall_result = Pass with Minor Issues
    │  │   BR-08-09 → auto tạo CM WO priority=Medium → navigate /cm/work-orders/<new>
    │  │
    │  └─ overall_result = Fail → Halted-Major Failure
    │      BR-08-09 → auto tạo CM WO priority=Critical + link source_pm_wo
    │
    ▼
(lịch PM kế tiếp auto-advance)
```

---

### 2.4 Flow: Sửa chữa CM (IMM-09)

```
Entry 1: từ Incident Critical
[/incidents/new] → severity=Critical → BR-12 auto tạo CAPA + Link CM WO
    │
Entry 2: từ PM Fail-Major
[/pm/work-orders/:id] Fail → auto CM WO
    │
Entry 3: user tạo manual
[/cm/create]
    │  • LinkSearch AC Asset
    │  • incident_report hoặc source_pm_wo (BR-09-01 — ít nhất 1)
    │  • priority (Critical/Urgent/Normal) + risk_class → SLA target
    │  • diagnosis_notes, root_cause_category
    │
    ▼
[/cm/work-orders/:id]
    │  state: Open
    │  │
    │  ├─ Assign KTV → Assigned
    │  │
    │  ├─ "Chẩn đoán" → /cm/work-orders/:id/diagnose → Diagnosing
    │  │
    │  ├─ "Quản lý phụ tùng" → /cm/work-orders/:id/parts
    │  │   BR-09-02: mọi row spare_parts_used phải có stock_entry_ref
    │  │   LinkSearch Stock Entry (ERPNext) → auto pull qty
    │  │   state: → Pending Parts (chờ) hoặc In_Repair
    │  │
    │  ├─ Firmware update → FCR → /cm/firmware/<id>
    │  │   BR-09-03: firmware_updated=1 phải link FCR Approved
    │  │
    │  ├─ Repair Checklist → /cm/work-orders/:id/checklist
    │  │   BR-09-04: 100% Pass trước submit
    │  │   state: → Pending_Inspection
    │  │
    │  ├─ Dept Head Sign-off → Completed
    │  │   • Asset.lifecycle_status: Under_Repair → Active
    │  │   • update MTTR avg (scheduler monthly)
    │  │   • repeat_failure check (30-day window) → flag BR-09-06
    │  │
    │  └─ Cannot Repair → Cannot_Repair state
    │      • Asset.lifecycle_status → Out_of_Service (hoặc Decommissioned)
    │
    ▼
/cm/mttr (báo cáo tháng)
```

---

### 2.5 Flow: Master Data (IMM-00) — điều kiện tiền đề

**Trình tự seed ban đầu (1 lần khi go-live):**

```
/reference-data  (AC Location, AC Department, AC Asset Category — seed CSV import)
    │
    ▼
/suppliers  (+ Tạo mới NCC với ISO 13485/17025 cert)
    │
    ▼
/device-models  (+ Tạo IMM Device Model với PM/calibration interval)
    │   → sẽ là source cho IMM-04 auto-fill
    ▼
/sla-policies  (SLA matrix priority × risk_class)
    │
    ▼
(sẵn sàng vận hành IMM-04)
```

**Mỗi thiết bị → AC Asset chỉ được tạo qua 1 trong 2 đường:**
- **Qua IMM-04** (khuyến nghị): `mint_core_asset()` trên `on_submit` của Commissioning
- **Trực tiếp** `/assets/new`: chỉ dùng cho data migration / test

---

## 3. Ma trận Workflow ↔ UI State

### 3.1 IMM-04 Commissioning

| Workflow State (BE) | Route hiển thị | Action buttons hiện |
|---|---|---|
| `Draft` | `/commissioning/:id` | "Xác nhận đủ tài liệu" · Edit · Cancel |
| `Pending_Doc_Verify` | — | Tab Documents active · "Ghi nhận đã nhận" |
| `To_Be_Installed` | — | "Bắt đầu lắp đặt" · Upload site photo |
| `Installing` | — | "Hoàn tất lắp đặt" · "Báo DOA" |
| `Identification` | — | "Nhập SN + QR" · Tab Identification active |
| `Initial_Inspection` | — | Tab Baseline active · "Submit Baseline" |
| `Non_Conformance` | `/commissioning/:id/nc` | Form NC · "Đóng NC" · "Return to Vendor" |
| `Clinical_Hold` | — | QA Officer thấy "Upload License" + "Clear Hold" |
| `Re_Inspection` | — | "Re-submit Baseline" |
| `Clinical_Release` | — | VP Block2 thấy "Submit & Mint Asset" |
| `Return_To_Vendor` | — | Read-only · link NC |
| `DOA_Incident` | — | Read-only · link NC type=DOA |

### 3.2 IMM-05 Asset Document

| State | Route | Action |
|---|---|---|
| `Draft` | `/documents/view/:name` | "Submit for Review" · Edit · Delete |
| `Pending_Review` | — | PTP Block2: "Approve" · "Reject" |
| `Active` | — | "Upload New Version" · "Archive" |
| `Archived` | — | Read-only (vẫn truy cập được) |
| `Expired` | — | "Renew" → tạo version mới |
| `Rejected` | — | "Resubmit" (tạo draft mới) |

### 3.3 IMM-08 PM Work Order

| State | Route | Action |
|---|---|---|
| `Open` | `/pm/work-orders/:id` | "Nhận việc" · Reschedule |
| `In_Progress` | — | Tab Checklist · "Pause (Device Busy)" |
| `Pending-Device Busy` | — | "Resume" |
| `Overdue` | — | Same as Open + red badge |
| `Completed` | — | Read-only · export PDF |
| `Halted-Major Failure` | — | Auto redirect → CM WO |

### 3.4 IMM-09 CM Work Order

| State | Route | Action |
|---|---|---|
| `Open` | `/cm/work-orders/:id` | "Assign KTV" |
| `Assigned` | — | "Diagnose" → /diagnose |
| `Diagnosing` | — | "Need Parts" / "Start Repair" |
| `Pending Parts` | `/cm/work-orders/:id/parts` | Search + add parts |
| `In_Repair` | — | "Checklist" → /checklist |
| `Pending_Inspection` | — | Dept Head "Sign-off" |
| `Completed` | — | Read-only · MTTR updated |
| `Cannot_Repair` | — | "Mark Out_of_Service" |

---

## 4. Cross-Module Navigation Links (từ một entity → module khác)

| Từ view | Link tới | Trigger | Query params |
|---|---|---|---|
| `/assets/:id` | `/documents?asset=<id>` | Tab "Hồ sơ" | `?asset=` |
| `/assets/:id` | `/pm/work-orders?asset=<id>` | Tab "Bảo trì" | `?asset=` |
| `/assets/:id` | `/cm/work-orders?asset=<id>` | Tab "Sửa chữa" | `?asset=` |
| `/assets/:id` | `/commissioning/<commissioning_ref>` | "Xem phiếu nghiệm thu" | — |
| `/commissioning/:id` | `/assets/<final_asset>` | Sau Submit | — |
| `/commissioning/:id` | `/documents/new?asset=<final_asset>&doc_type_detail=...` | GW-2 block | query pre-fill |
| `/pm/work-orders/:id` | `/cm/work-orders/<new>?source_pm_wo=<id>` | overall_result=Fail-Major | `?source_pm_wo=` |
| `/incidents/:id` | `/capas/<auto-created>` | severity=Critical | — |
| `/incidents/:id` | `/cm/create?incident_report=<id>` | "Tạo phiếu sửa chữa" | `?incident_report=` |
| `/cm/work-orders/:id` | `/cm/firmware/<fcr>` | firmware_updated=1 | — |
| `/cm/work-orders/:id` | `/assets/<asset_ref>` | Header "Xem thiết bị" | — |

---

## 5. Route → DocType → API mapping

| Route | Primary DocType | API module | Endpoint chính |
|---|---|---|---|
| `/commissioning/**` | Asset Commissioning | `assetcore.api.imm04` | list, get_form_context, create, transition, submit |
| `/documents/**` | Asset Document | `assetcore.api.imm05` | list, create, approve, reject, get_history |
| `/pm/work-orders/**` | PM Work Order | `assetcore.api.imm08` | list, get, submit_checklist |
| `/cm/work-orders/**` | Asset Repair | `assetcore.api.imm09` | list, create, assign, save_parts, submit_checklist |
| `/assets/**` | AC Asset | `assetcore.api.imm00` | list_assets, get_asset, create_asset |
| `/suppliers/**` | AC Supplier | `assetcore.api.imm00` | list_suppliers, create_supplier |
| `/device-models/**` | IMM Device Model | `assetcore.api.imm00` | list_device_models, get_device_model |
| `/incidents/**` | Incident Report | `assetcore.api.imm00` | list_incidents, create_incident |
| `/capas/**` | IMM CAPA Record | `assetcore.api.imm00` | list_capas, get_capa |
| `/asset-transfers/**` | Asset Transfer | `assetcore.api.imm00` | list_transfers, create_transfer |
| `/service-contracts/**` | Service Contract | `assetcore.api.imm00` | list_contracts, create_contract |

Chung cho mọi LinkSearch dropdown: `GET /api/method/assetcore.api.imm04.search_link?doctype=...&query=...` (allow-list: Purchase Order, AC Supplier, AC Department, AC Location, AC Asset, AC Asset Category, IMM Device Model, User).

---

## 6. Route Guards & Permissions

**Global guard** (`router.beforeEach`):
1. Check session cookie → nếu không có → redirect `/login?next=<path>`
2. Tải `useAuthStore().fetchSession()` vào Pinia
3. Check role trong `meta.requiredRoles` (nếu có)

**Per-route meta ví dụ:**

```ts
{
  path: '/commissioning/new',
  meta: { requiredRoles: ['HTM Technician', 'Biomed Engineer', 'CMMS Admin'] },
},
{
  path: '/commissioning/:id',
  meta: { requiredRoles: [] /* open — BE filter theo row-level */ },
},
```

**Row-level perm** (BE xử lý): ví dụ Vendor Engineer chỉ xem phiếu có `vendor` link tới AC Supplier họ đại diện.

---

## 7. Đề xuất cải thiện navigation

1. **Breadcrumb chung:** component `<AppBreadcrumb>` tự derive từ route.matched → mọi detail view hiển thị `Module > List > Detail` (hiện mỗi view tự code)
2. **Sticky sidebar group state:** collapse/expand trạng thái trong `localStorage`
3. **Global command palette (Ctrl+K):** tìm nhanh asset/phiếu/WO/document theo SN/name
4. **Back button smart:** `router.back()` fallback `/dashboard` nếu history rỗng (deep-link)
5. **Tab persistence:** tab active trong `AssetDetailView` lưu query `?tab=docs` để shareable URL
6. **Realtime badge:** sidebar "CM Work Orders" hiển thị số SLA-breach count realtime (từ `publish_realtime`)
7. **Module IMM-12 (Incident RCA):** cần thêm `/rca`, `/rca/:id` khi BE triển khai
8. **Module IMM-11 (Calibration):** cần `/calibration/schedules`, `/calibration/:id`, `/calibration/:id/measurements` khi BE live
9. **Route alias** cho Vietnamese-friendly URL: `/phieu-nghiem-thu` → alias `/commissioning`
10. **Error boundary route:** `/errors/403`, `/errors/404`, `/errors/500` với layout riêng

---

## 8. Known gaps

| Gap | Impact | Ticket |
|---|---|---|
| TC-32 FAIL: `fire_release_event` không trigger IMM-08 listener | PM Schedule không tự tạo sau IMM-04 Release | TD-04 |
| `/calibration` trống (IMM-11 DRAFT) | Click từ sidebar ra trang rỗng | Sprint 11.5 |
| `/rca` chưa tồn tại (IMM-12 partial) | Incident Critical → CAPA chưa có RCA workflow | Sprint 12.2 |
| `AssetDetailView` tab Documents hiện chưa truyền `?asset=` filter | Dùng global list | FE-TD-01 |
| `DocumentManagement` vẫn dùng text input cho asset filter (không LinkSearch) | UX inconsistent | FE-TD-02 |

---

## 9. Tham chiếu

- Router source: `frontend/src/router/index.ts`
- Main layout: `frontend/src/layouts/DefaultLayout.vue`
- Sidebar: `frontend/src/components/layout/AppSidebar.vue`
- Docs nghiệp vụ theo module: `docs/imm-0X/IMM-0X_Functional_Specs.md`
- DocType schemas: `assetcore/assetcore/doctype/<name>/<name>.json`
- API endpoints: `assetcore/api/imm0X.py`
- Workflow JSONs: `imm_04_workflow.json`, `imm_05_document_workflow.json`

---

*Tài liệu này cần cập nhật sau mỗi sprint khi thêm route mới hoặc thay đổi workflow state — 2026-04-19.*
