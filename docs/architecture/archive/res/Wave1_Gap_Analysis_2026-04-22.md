# Wave 1 — Gap Analysis & Action Plan
**Ngày phân tích:** 2026-04-22  
**Phạm vi:** IMM-04, IMM-05, IMM-08, IMM-09, IMM-11, IMM-12 (+ IMM-00 foundation)  
**Phương pháp:** So sánh trực tiếp code BE (services/, api/, doctype/) với code FE (views/, stores/, api/, router/) và docs/imm-xx

---

## Tổng quan nhanh

| Module | BE Service | BE API | FE View | FE Store | Workflow | UAT | Trạng thái |
|--------|-----------|--------|---------|----------|----------|-----|------------|
| IMM-00 (Foundation) | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | Cơ bản xong, vài điểm thiếu |
| IMM-04 (Installation) | ✅ | ✅ | ✅ | ✅ | ✅ json | ⚠️ | Gần hoàn thiện |
| IMM-05 (Registration) | ✅ | ✅ | ✅ | ✅ | ✅ json | ⚠️ | Gần hoàn thiện |
| IMM-08 (PM) | ✅ | ✅ | ✅ | ✅ | ❌ | ⚠️ | Logic xong, thiếu workflow DocType |
| IMM-09 (CM/Repair) | ✅ | ✅ | ✅ | ✅ | ❌ | ⚠️ | Logic xong, thiếu workflow DocType |
| IMM-11 (Calibration) | ✅ | ✅ | ✅ | ❌ | ❌ | ⚠️ | FE dùng API trực tiếp, thiếu store |
| IMM-12 (Corrective/Incident) | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | Mới triển khai, chưa UAT |

---

## 1. IMM-00 — Foundation (Asset, Model, SLA, Firmware)

### Trạng thái thực tế
- DocTypes: `imm_device_model`, `imm_sla_policy`, Firmware CR (trong `imm00.py`) — **đã có**
- API: CRUD đầy đủ cho device model, SLA policy, firmware CR, asset lifecycle events
- FE: `DeviceModelListView`, `SlaPolicyListView`, `FirmwareCrListView`, `AssetListView` — **đã có**

### Vấn đề phát hiện

**[CRITICAL] FirmwareCR thiếu Detail View**
- Router `/cm/firmware/:id` redirect về `/cm/firmware?focus=:id` — không có trang chi tiết thực sự
- `FirmwareCrListView.vue` tích hợp form inline (create/edit), nhưng không có route `/cm/firmware/:id` riêng
- Thiếu: workflow duyệt FCR (Draft → Approved → Deployed → Rejected)

**[HIGH] SLA Policy thiếu CRUD đầy đủ**
- `SlaPolicyListView.vue` có form inline edit nhưng không validate required fields ở FE
- Không có link từ Asset → SLA Policy đang áp dụng trên UI

**[MEDIUM] Asset Commission flow chưa hiển thị timeline đầy đủ**
- `CommissioningTimelineView.vue` tồn tại nhưng không xuất hiện trong sidebar hoặc deep link từ Asset Detail

---

## 2. IMM-04 — Installation & Commissioning

### Trạng thái thực tế
- Service: `imm04.py` (1075 lines) — đầy đủ: create, transition_state, submit, NC, barcode, QR, handover PDF
- Workflow JSON: `imm_04_workflow.json` — **đã có**
- FE: `CommissioningListView`, `CommissioningCreateView`, `CommissioningDetailView`, `CommissioningNCView`, `CommissioningTimelineView` — **đầy đủ**

### Vấn đề phát hiện

**[HIGH] `generate_handover_pdf` chưa có template PDF**
- API `generate_handover_pdf(name)` tồn tại nhưng service trả về placeholder (chưa có Frappe Print Format)
- UI có nút "In biên bản" nhưng PDF output chưa được design

**[HIGH] Workflow transition không hiển thị lịch sử state trên FE**
- `CommissioningDetailView` hiển thị `workflow_state` hiện tại nhưng không có timeline transitions
- `CommissioningTimelineView.vue` có, nhưng không hiển thị workflow audit trail từ Frappe

**[MEDIUM] Barcode lookup không có fallback khi barcode không tồn tại**
- `get_barcode_lookup(barcode)` trong API không trả về lỗi thân thiện khi không tìm thấy
- FE không hiển thị rõ khi scan thất bại

---

## 3. IMM-05 — Document & Registration Management

### Trạng thái thực tế
- Service: `imm05.py` (521 lines) — CRUD + approve/reject + get_expiring
- Workflow JSON: `imm_05_document_workflow.json` — **đã có**
- FE: `DocumentManagement`, `DocumentCreateView`, `DocumentDetailView`, `DocumentRequestListView` — **có**

### Vấn đề phát hiện

**[CRITICAL] Không có DocumentEditView**
- Router không có route `/documents/:name/edit`
- `DocumentDetailView.vue` có nút "Sửa" nhưng điều hướng đến đâu? → cần kiểm tra, khả năng là broken
- API `update_document(name, doc_data)` tồn tại nhưng FE không gọi được qua route

**[HIGH] Workflow approve/reject chưa kiểm soát role**
- `approve_document()` trong service không kiểm tra user role (chỉ kiểm tra login)
- Bất kỳ user đăng nhập nào đều có thể approve tài liệu

**[HIGH] Document expiry notification không có trigger**
- `get_expiring_documents(days=90)` API tồn tại nhưng không có cron job hoặc scheduler hook tự động notify
- Tài liệu hết hạn chỉ hiện thị khi user chủ động vào xem

**[MEDIUM] Asset-document link từ Asset Detail chưa hoàn thiện**
- Route `/documents/asset/:assetId` redirect về `/documents?asset=assetId` — không filter tự động trên FE
- `DocumentManagement.vue` không nhận query param `asset` để filter

---

## 4. IMM-08 — PM (Preventive Maintenance)

### Trạng thái thực tế
- Service: `imm08.py` (789 lines) — đầy đủ: schedule, create WO, assign, submit result, reschedule, calendar
- **Không có Workflow JSON** cho `pm_work_order` — chỉ có status field trong service
- FE: `PMDashboardView`, `PMWorkOrderListView`, `PMWorkOrderDetailView`, `PMWorkOrderCreateView`, `PMCalendarView`, `PmScheduleListView`, `PmTemplateListView` — **đầy đủ**
- Store: `imm08.ts` — **có**

### Vấn đề phát hiện

**[CRITICAL] Thiếu Frappe Workflow cho `pm_work_order`**
- Status transitions (Scheduled → In Progress → Completed → Overdue) được thực hiện hoàn toàn trong service code
- Frappe không track workflow audit trail → vi phạm QMS audit trail requirement
- Cần tạo `imm_08_workflow.json` và bind vào `pm_work_order` DocType

**[HIGH] `pm_work_order` DocType: `is_submittable` = 0?**
- Nếu WO không submittable, Frappe không lock record sau khi hoàn thành
- Cần verify và set `is_submittable: 1`

**[HIGH] IMM-08 → IMM-12 auto-incident chưa có**
- `report_major_failure()` API tồn tại nhưng không tự động tạo `IncidentReport`
- Khi PM phát hiện hỏng hóc lớn, technician phải thủ công vào IMM-12 báo cáo
- Cần hook: khi `major_failure = True` trong `submit_pm_result()` → gọi `imm12.report_incident()`

**[MEDIUM] PM Calendar không hiển thị trạng thái WO màu sắc**
- `PMCalendarView.vue` render calendar nhưng không phân biệt màu Scheduled/Overdue/Completed

---

## 5. IMM-09 — CM (Corrective Maintenance / Repair)

### Trạng thái thực tế
- Service: `imm09.py` (726 lines) — đầy đủ: create, assign, diagnose, start_repair, parts, close, KPIs
- **Không có Workflow JSON** cho `asset_repair` DocType
- FE: `CMDashboardView`, `CMWorkOrderListView`, `CMWorkOrderDetailView`, `CMCreateView`, `CMDiagnoseView`, `CMPartsView`, `CMChecklistView`, `CMMttrView` — **đầy đủ nhất trong Wave 1**
- Store: `imm09.ts` — **có**

### Vấn đề phát hiện

**[CRITICAL] Thiếu Frappe Workflow cho `asset_repair`**
- Tương tự IMM-08: status (Pending → In Progress → Waiting Parts → Completed) chạy trong service code
- Frappe không có workflow audit trail → vi phạm QMS

**[HIGH] Stock entry validation có fallback skip**
- Trong `imm09.py`, khi tạo stock movement cho spare parts: nếu `imm_device_spare_part` DocType không available thì skip validation
- Rủi ro: spare part request được approved mà không có stock record → số liệu inventory sai

**[HIGH] `close_work_order()` không trigger IMM-12 nếu root cause = "Chronic"**
- Khi đóng WO với `root_cause_category = "Chronic Failure"`, không tự động tạo hoặc link RCA record
- Cần hook sang `imm12.detect_chronic_failures()` hoặc `imm12.create_rca()`

**[MEDIUM] FCR (Firmware Change Request) trong IMM-09 chưa khớp**
- `close_repair_work_order()` có field `firmware_updated` và `firmware_change_request`
- FE `CMWorkOrderDetailView.vue` hiển thị FCR nhưng link `/cm/firmware/:id` chỉ redirect — không detail view
- Flow: CM WO → FCR cần được theo dõi đến khi firmware deployed

---

## 6. IMM-11 — Calibration

### Trạng thái thực tế
- Service: `imm11.py` (737 lines) — đầy đủ: schedule, create, submit, send_to_lab, receive_certificate, cancel, KPIs
- **Không có Workflow JSON** cho `imm_asset_calibration`
- FE: `CalibrationDashboard`, `CalibrationListView`, `CalibrationDetailView`, `CalibrationCreateView`, `CalibrationScheduleListView` — **có**
- **Không có store `imm11.ts`** — views gọi API trực tiếp (không qua Pinia)

### Vấn đề phát hiện

**[CRITICAL] Thiếu Pinia store cho IMM-11**
- `CalibrationDashboard.vue`, `CalibrationListView.vue` gọi API functions trực tiếp mà không qua store
- Loading state, error state, pagination không centralized → khó maintain
- Cần tạo `frontend/src/stores/imm11.ts` theo pattern của `useImm12Store.ts`

**[CRITICAL] Thiếu Frappe Workflow cho `imm_asset_calibration`**
- Status: Draft → Scheduled → In Progress → Sent to Lab → Certificate Received → Completed / Failed
- Không có workflow JSON — transitions chạy thuần trong service
- Khi calibration FAIL → IMM-12 incident đã được thêm hook (imm11→imm12) nhưng chưa có workflow audit trail

**[HIGH] `send_to_lab()` không validate External Lab record**
- `send_to_lab(name, lab_name, sent_date, contact)` nhận `lab_name` là free text, không link đến Supplier record
- Không traceability với vendor/supplier module

**[HIGH] `receive_certificate()` không attach file vào DocType**
- API nhận `certificate_number` và `valid_until` nhưng không có file attachment cho PDF certificate
- Certificate number là text chỉ — không thể verify

**[MEDIUM] Calibration schedule không auto-tạo Work Order**
- `CalibrationScheduleListView.vue` hiển thị schedule nhưng không có nút "Tạo lịch" → phải thủ công vào `CalibrationCreateView`
- Service `imm11.py` có `create_calibration_schedule()` và `create_calibration()` riêng biệt — không auto-link

---

## 7. IMM-12 — Corrective Maintenance / Incident & RCA

### Trạng thái thực tế (mới hoàn thiện 2026-04-22)
- Service: `imm12.py` (677 lines) — đầy đủ: report, acknowledge, resolve, close, cancel, RCA workflow, chronic detection
- API: 15 endpoints — đầy đủ cho Wave 1
- FE: `IMM12DashboardView`, `IncidentListView`, `IncidentDetailView`, `IncidentCreateView`, `RCADetailView` — **đầy đủ**
- Store: `useImm12Store.ts` — **có**
- Cross-module: IMM-11 → IMM-12 hook — **đã có**

### Vấn đề phát hiện

**[CRITICAL] `incident_report` DocType: `workflow` = None**
- `is_submittable: 1` nhưng `workflow: None` — không có Frappe Workflow binding
- State transitions (Open→Under Investigation→Resolved→Closed) chạy trong service nhưng Frappe không track
- Cần tạo `imm_12_incident_workflow.json`

**[CRITICAL] `imm_rca_record` DocType: `is_submittable: 0`**
- RCA record không submittable → không có lock sau complete, không có amendment trail
- Cần set `is_submittable: 1` và tạo workflow JSON cho RCA

**[HIGH] Chronic failure detection chỉ chạy on-demand**
- `detect_chronic_failures()` được gọi qua API thủ công, không có scheduler hook
- Cần Frappe scheduled job (`hourly` hoặc `daily`) tự động detect và flag

**[HIGH] IMM-08 → IMM-12 hook chưa có**
- PM major failure → incident chưa được hook (chỉ có IMM-11 → IMM-12)
- Cần thêm vào `imm08.py:report_major_failure()` → gọi `imm12.report_incident()`

**[MEDIUM] RCADetailView thiếu form nhập 5-Why steps**
- `RCADetailView.vue` hiển thị RCA record nhưng không có UI để nhập/sửa `five_why_steps` child table
- `imm_rca_five_why_step` DocType tồn tại nhưng FE không expose

**[MEDIUM] `imm_rca_related_incident` DocType mới tạo nhưng chưa dùng**
- Folder `imm_rca_related_incident/` tồn tại (untracked) nhưng không có UI link

---

## 8. Cross-Module Integration Gaps

| Flow | Trạng thái | Vấn đề |
|------|-----------|--------|
| IMM-11 → IMM-12 (cal fail → incident) | ✅ Hook có | Chạy trong try/except, không test |
| IMM-08 → IMM-12 (PM major fail → incident) | ❌ Thiếu | Phải thủ công |
| IMM-09 → IMM-12 (CM chronic root cause → RCA) | ❌ Thiếu | Không auto-link |
| IMM-12 → IMM-09 (incident → repair WO) | ⚠️ Partial | `linked_repair_wo` field có, nhưng không tự tạo WO |
| IMM-12 → CAPA (RCA complete → CAPA) | ⚠️ Partial | `linked_capa` field có, không auto-tạo |
| IMM-04 → Asset Lifecycle Event | ✅ Có | `ac_asset_lifecycle_workflow.json` tồn tại |
| PM schedule → WO auto-create | ❌ Thiếu | Schedule list không tự tạo WO |
| Calibration schedule → Calibration auto-create | ❌ Thiếu | Phải thủ công |

---

## 9. Hệ thống QMS / Audit Trail

| Requirement | Trạng thái |
|-------------|-----------|
| Frappe Workflow cho IMM-04 | ✅ `imm_04_workflow.json` |
| Frappe Workflow cho IMM-05 | ✅ `imm_05_document_workflow.json` |
| Frappe Workflow cho IMM-08 PM WO | ❌ Không có |
| Frappe Workflow cho IMM-09 Repair WO | ❌ Không có |
| Frappe Workflow cho IMM-11 Calibration | ❌ Không có |
| Frappe Workflow cho IMM-12 Incident | ❌ Không có |
| Frappe Workflow cho IMM-12 RCA | ❌ Không có |
| Audit trail DocType (`imm_audit_trail`) | ✅ Có |
| CAPA record (`imm_capa_record`) | ✅ Có DocType, partial UI |

**5 workflow JSON còn thiếu** là gap nghiêm trọng nhất về QMS compliance.

---

## 10. FE Architecture Gaps

### Missing Stores
| Module | Store cần có | Hiện trạng |
|--------|-------------|-----------|
| IMM-11 Calibration | `imm11.ts` | ❌ Views gọi API trực tiếp |

### Missing Views
| Feature | View cần có | Hiện trạng |
|---------|------------|-----------|
| Sửa Document (IMM-05) | `DocumentEditView.vue` | ❌ Không có route `/documents/:name/edit` |
| Chi tiết FCR | `FirmwareCrDetailView.vue` | ❌ `/cm/firmware/:id` chỉ redirect về list |
| Nhập 5-Why trong RCA | Form trong `RCADetailView.vue` | ⚠️ UI chỉ read-only |
| Related Incidents trong RCA | Section trong `RCADetailView.vue` | ❌ `imm_rca_related_incident` không dùng |

### Type Organization
- Types phân tán giữa `types/inventory.ts` và từng `api/*.ts` file
- Không có file `types/imm.ts` tổng hợp cho các IMM interfaces

---

## 11. Action Plan — Ưu tiên để hoàn thiện Wave 1

### Priority 1 — CRITICAL (Cần làm ngay, block UAT)

- [ ] **Tạo 5 Workflow JSON** cho IMM-08, IMM-09, IMM-11, IMM-12 Incident, IMM-12 RCA
  - File: `assetcore/assetcore/workflow/imm_08_workflow.json` v.v.
  - Bind vào DocType tương ứng
- [ ] **Set `is_submittable: 1`** cho `pm_work_order`, `asset_repair`, `imm_asset_calibration`, `imm_rca_record`
- [ ] **Tạo `DocumentEditView.vue`** + route `/documents/:name/edit`
- [ ] **Tạo `imm11.ts` Pinia store** theo pattern `useImm12Store.ts`

### Priority 2 — HIGH (Cần trước UAT formal)

- [ ] **Hook IMM-08 → IMM-12**: `report_major_failure()` → gọi `imm12.report_incident()`
- [ ] **Hook IMM-09 → IMM-12**: `close_work_order(root_cause="Chronic")` → `imm12.detect_chronic_failures()`
- [ ] **Scheduler job** cho `detect_chronic_failures()` — chạy daily
- [ ] **Document approval role check** — chỉ allow user có role "Document Approver"
- [ ] **5-Why steps UI** trong `RCADetailView.vue` — form nhập `five_why_steps` child table
- [ ] **Fix `/documents/asset/:assetId`** — filter query param hoạt động trên `DocumentManagement.vue`
- [ ] **Calibration schedule → auto-create calibration** — button trên `CalibrationScheduleListView`

### Priority 3 — MEDIUM (Sau UAT initial)

- [ ] **FCR Detail View** `/cm/firmware/:id` thực sự (không redirect về list)
- [ ] **FCR Workflow** Draft → Approved → Deployed → Rejected
- [ ] **PM Calendar**: màu sắc phân biệt WO status
- [ ] **Handover PDF template** (Print Format) cho IMM-04
- [ ] **Certificate attachment** cho calibration (`receive_certificate()` + file upload UI)
- [ ] **IMM-12 → CAPA auto-create** khi RCA completed với `corrective_action_summary`
- [ ] **`imm_rca_related_incident`** — UI liên kết trong RCA detail

### Priority 4 — LOW (Nice-to-have Wave 1)

- [ ] **Document expiry notification** — Frappe Scheduler cron → email/notification
- [ ] **Asset → SLA Policy link** hiển thị trên Asset Detail
- [ ] **Type consolidation** — tổ chức lại `types/` vs `api/*.ts` interfaces
- [ ] **Workflow transition history** hiển thị trên Commissioning Detail

---

## 12. Rủi ro kỹ thuật còn mở

| Rủi ro | Mức độ | Ghi chú |
|--------|--------|---------|
| Frappe Node version (cần Node 20+, system có Node 18) | HIGH | Dùng nvm v24 để build |
| `UserProfileFormView.vue:179` TS error pre-existing | MEDIUM | Không liên quan IMM, cần fix riêng |
| Stock entry validation skip trong IMM-09 | HIGH | Inventory có thể bị sai nếu DocType unavailable |
| Calibration lab_name là free text | MEDIUM | Không traceable về Supplier |
| IMM-11→IMM-12 hook chạy trong bare `except` | LOW | Log error nhưng không re-raise, có thể miss |

---

*Được tạo bởi phân tích trực tiếp source code ngày 2026-04-22. Cập nhật khi đóng gap.*
