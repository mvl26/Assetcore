# AssetCore Wave 1 — Phân tích & Chuẩn hóa Module

**Phiên bản:** 1.0  
**Ngày:** 2026-04-17  
**Trạng thái:** Tài liệu sống — cập nhật theo tiến độ sprint  
**Phạm vi:** IMM-04, IMM-05, IMM-08, IMM-09, IMM-11, IMM-12

---

## Tổng quan trạng thái Wave 1

| Module | Tên | Tài liệu thiết kế | Backend (DocType+API) | Frontend (Vue) | Scheduler | UAT |
| --- | --- | --- | --- | --- | --- | --- |
| IMM-04 | Installation & Commissioning | ✅ Đầy đủ | ✅ Hoàn chỉnh | ✅ Hoàn chỉnh | ✅ 2 tasks | ✅ 31/32 PASS |
| IMM-05 | Document Repository | ✅ Đầy đủ | ✅ Hoàn chỉnh | ✅ Hoàn chỉnh | ✅ 3 tasks | ✅ Pass |
| IMM-08 | Preventive Maintenance | ✅ Đầy đủ | ❌ Chưa code | ❌ Chưa code | ❌ Chưa code | ❌ |
| IMM-09 | Corrective Maintenance | ⚠️ BA sơ bộ | ❌ Chưa code | ❌ Chưa code | ❌ Chưa code | ❌ |
| IMM-11 | Calibration & Inspection | ⚠️ BA sơ bộ | ❌ Chưa code | ❌ Chưa code | ❌ Chưa code | ❌ |
| IMM-12 | Corrective Maint. + SLA | ⚠️ BA sơ bộ | ❌ Chưa code | ❌ Chưa code | ❌ Chưa code | ❌ |

**Huyền thoại:** ✅ Hoàn chỉnh · ⚠️ Một phần · ❌ Chưa có

---

## Kiến trúc chung (áp dụng tất cả module)

```
Frontend (Vue 3 + Pinia)
  └── /frontend/src/
       ├── views/         ← Page-level views (route)
       ├── components/    ← imm04/, imm05/, imm08/, common/
       ├── api/           ← imm04.ts, imm05.ts, imm08.ts ...
       ├── stores/        ← Pinia stores per module
       └── types/         ← TypeScript interfaces

Backend (Frappe v15 Python)
  └── assetcore/assetcore/
       ├── doctype/       ← DocType JSON + Python controller
       ├── api/           ← imm04.py, imm05.py, imm08.py ...
       ├── tasks.py       ← Scheduled jobs (cron)
       └── hooks.py       ← scheduler_events, fixtures
```

**Quy tắc bất biến:**
- API: luôn trả `_ok(data)` hoặc `_err(message, code)` — không raw dict
- Controller: chỉ `validate()` + gọi service — không có business logic
- Mọi state change: tạo Lifecycle Event record
- Tên DocType: dùng hằng số `_DOCTYPE = "Asset Document"` — không string rải rác
- Frontend: validation thủ công (không Vuelidate), hiển thị lỗi tiếng Việt

---

## IMM-04 — Installation & Commissioning

### Trạng thái: ✅ HOÀN CHỈNH

### DocTypes đã implement

| DocType | File | Mục đích |
| --- | --- | --- |
| Asset Commissioning | `doctype/asset_commissioning/` | Phiếu lắp đặt chính — submittable |
| Commissioning Checklist | `doctype/commissioning_checklist/` | Child table kiểm tra baseline |
| Commissioning Document Record | `doctype/commissioning_document_record/` | Child table hồ sơ đính kèm |
| Asset QA Non Conformance | `doctype/asset_qa_non_conformance/` | Phiếu NC / DOA độc lập |

**Custom Fields trên Asset (core ERPNext):**
`custom_vendor_sn`, `custom_internal_qr`, `custom_comm_ref`, `custom_doc_completeness_pct`, `custom_document_status`

### Workflow States

```
Draft
  → [HTM Technician: Submit] → Pending_Doc_Verify
  → [HTM Technician: Verify_Pass] → To_Be_Installed
  → [Vendor: Start_Work] → Installing
  → [Vendor: Assemble_Done] → Identification
  → [Biomed Engineer: Tag_Scanned] → Initial_Inspection
  → [Biomed Engineer: Release_Pass] → Clinical_Release  ← TERMINAL (docstatus=1)
  → [Biomed Engineer: Fail_Test] → Re_Inspection
  → [Workshop Head: Hold] → Clinical_Hold
  → [Workshop Head: Resolve] → Clinical_Release
```

### API — `assetcore/api/imm04.py` (861 dòng)

| Endpoint | Method | Mục đích |
| --- | --- | --- |
| `get_form_context` | GET | Load context tạo phiếu |
| `get_commissioning_list` | GET | Danh sách phân trang |
| `get_commissioning_detail` | GET | Chi tiết 1 phiếu |
| `create_commissioning` | POST | Tạo phiếu mới |
| `update_commissioning` | POST | Cập nhật phiếu Draft |
| `change_workflow_state` | POST | Chuyển trạng thái |
| `generate_qr_label` | GET | Tạo QR code label |
| `get_po_details` | GET | Lấy thông tin PO |
| `search_link` | GET | Autocomplete Link fields |

### Validation Rules đã code

| VR | Nội dung | Vị trí code |
| --- | --- | --- |
| VR-01 | Serial không trùng trong DB | `validate_unique_serial()` |
| VR-02 | Documents required đủ trước verify | `validate_required_documents()` |
| VR-03 | Checklist 100% trước release | `validate_checklist_completion()` |
| VR-04 | Block release nếu NC còn mở | `block_release_if_nc_open()` |
| VR-07 | Thiết bị bức xạ bắt buộc ảnh chứng nhận | `validate_radiation_hold()` |

### GW-2 Gate (tích hợp IMM-05)

```python
# asset_commissioning.py — on_submit
def _gw2_check_document_compliance(self):
    """Block submit nếu IMM-05 phát hiện thiếu tài liệu bắt buộc."""

def create_initial_document_set(self):
    """Auto-import tài liệu từ commissioning vào Asset Document Repository."""
```

### Frontend — `/frontend/src/components/imm04/`

| File | Chức năng |
| --- | --- |
| `CommissioningForm.vue` | Form tạo/sửa phiếu |
| `BaselineTestTable.vue` | Grid điền checklist |
| `DocumentChecklist.vue` | Danh sách tài liệu đính kèm |
| `QRLabel.vue` | In nhãn QR (qrcode library) |
| `WorkflowActions.vue` | Nút chuyển trạng thái |
| `AssetDashboard.vue` | Dashboard thiết bị |

**Views:** `CommissioningListView.vue`, `CommissioningCreateView.vue`, `CommissioningDetailView.vue`

### Scheduler Tasks (`tasks.py`)

| Task | Cron | Mục đích |
| --- | --- | --- |
| `check_clinical_hold_aging()` | Daily | Alert khi Clinical Hold quá N ngày |
| `check_commissioning_sla()` | Daily | SLA tracking phiếu lắp đặt |

### UAT: 31/32 PASS (KB05-1 PARTIAL — không có role VP Block2 trong test env)

---

## IMM-05 — Asset Document Repository

### Trạng thái: ✅ HOÀN CHỈNH

### DocTypes đã implement

| DocType | File | Mục đích |
| --- | --- | --- |
| Asset Document | `doctype/asset_document/` | Hồ sơ tài liệu chính — có workflow |
| Document Request | `doctype/document_request/` | Task yêu cầu bổ sung tài liệu |
| Expiry Alert Log | `doctype/expiry_alert_log/` | Log cảnh báo hết hạn (immutable) |
| Required Document Type | `doctype/required_document_type/` | Master config loại tài liệu bắt buộc |

### Workflow States

```
Draft
  → [Any: Submit] → Pending_Review
  → [Biomed/QLCL/Admin: Approve] → Active  ← auto-archive phiên bản cũ
  → [Biomed/QLCL/Admin: Reject + reason] → Rejected
  → [System: expiry_date passed] → Expired
  → [System/Admin: Archive] → Archived
```

### API — `assetcore/api/imm05.py` (624 dòng)

| # | Endpoint | Method | Mục đích |
| --- | --- | --- | --- |
| 1 | `list_documents` | GET | Danh sách phân trang + filter |
| 2 | `get_document` | GET | Chi tiết 1 tài liệu |
| 3 | `create_document` | POST | Upload tài liệu mới |
| 4 | `update_document` | POST | Sửa metadata (Draft only) |
| 5 | `approve_document` | POST | Approve → Active + archive old |
| 6 | `reject_document` | POST | Reject + lý do bắt buộc |
| 7 | `get_asset_documents` | GET | Tất cả docs của 1 asset |
| 8 | `get_dashboard_stats` | GET | KPI dashboard |
| 9 | `get_expiring_documents` | GET | Docs sắp hết hạn |
| 10 | `get_compliance_by_dept` | GET | Compliance % theo khoa |
| 11 | `get_document_history` | GET | Lịch sử thay đổi (Frappe Version) |
| 12 | `create_document_request` | POST | Tạo task yêu cầu tài liệu |
| 13 | `get_document_requests` | GET | Danh sách tasks |
| 14 | `mark_exempt` | POST | Miễn trừ theo NĐ98 |

### Validation Rules đã code

| VR | Nội dung |
| --- | --- |
| VR-01 | `expiry_date > issued_date` |
| VR-02 | Unique `doc_number` per type per asset |
| VR-03 | `file_attachment` required trước Pending_Review |
| VR-04 | `issuing_authority` required với Legal docs |
| VR-05 | Không revert Archived/Expired |
| VR-06 | `rejection_reason` required khi Reject |
| VR-07 | `expiry_date` required với Legal/Certification |
| VR-08 | File format: PDF/JPG/PNG/DOCX only |
| VR-09 | `change_summary` required khi version ≠ "1.0" |
| VR-10 | `exempt_reason + exempt_proof` required khi `is_exempt=1` |
| VR-11 | `is_exempt` chỉ áp dụng docs đăng ký |

### Scheduler Tasks (`tasks.py`)

| Task | Cron | Mục đích |
| --- | --- | --- |
| `check_document_expiry()` | Daily 00:30 | Cảnh báo 90/60/30/0 ngày, auto-expire |
| `update_asset_completeness()` | Daily 01:00 | Batch update % completeness trên Asset |
| `check_overdue_document_requests()` | Daily | Escalate task quá hạn |

### Frontend — `/frontend/src/`

| File | Chức năng |
| --- | --- |
| `views/DocumentManagement.vue` | Danh sách + filter + KPI banner |
| `views/DocumentDetailView.vue` | Chi tiết tài liệu + approve/reject |
| `components/imm05/DocumentRow.vue` | Row trong bảng danh sách |
| `components/imm05/DocumentRequestModal.vue` | Modal tạo yêu cầu tài liệu |
| `components/imm05/ExemptModal.vue` | Modal đánh dấu miễn trừ |
| `utils/docUtils.ts` | `stateLabel()`, `formatDate()` — shared |

---

## IMM-08 — Preventive Maintenance (Bảo trì Định kỳ)

### Trạng thái: ✅ THIẾT KẾ ĐẦY ĐỦ · ❌ CHƯA CODE

**Tài liệu tham chiếu:**
- `docs/imm-08/IMM-08_Functional_Specs.md`
- `docs/imm-08/IMM-08_Technical_Design.md`

### DocTypes cần tạo

#### 1. `PM Schedule` — Lịch bảo trì định kỳ

**Naming:** `PMS-{asset_ref}-{pm_type}-{YYYY}` (custom)  
**Không Submittable**

| Field | Type | Notes |
| --- | --- | --- |
| `asset_ref` | Link→Asset | **Mandatory** |
| `pm_type` | Select | Quarterly/Semi-Annual/Annual/Ad-hoc |
| `pm_interval_days` | Int | 90/180/365 |
| `checklist_template` | Link→PM Checklist Template | **Mandatory** |
| `last_pm_date` | Date | Cập nhật sau mỗi PM hoàn thành |
| `next_due_date` | Date | Computed: `last_pm_date + pm_interval_days` |
| `status` | Select | Active/Paused/Suspended |
| `alert_days_before` | Int | Default: 7 |
| `responsible_technician` | Link→User | |
| `created_from_commissioning` | Link→Asset Commissioning | Read-only |

**Controller hooks:**
- `before_save`: validate checklist_template tồn tại cho asset.asset_category
- `on_update`: nếu `last_pm_date` thay đổi → tính lại `next_due_date`

#### 2. `PM Checklist Template` — Mẫu checklist theo loại thiết bị

**Naming:** `PMCT-{asset_category}-{pm_type}`

| Field | Type | Notes |
| --- | --- | --- |
| `template_name` | Data | **Mandatory**, unique |
| `asset_category` | Link→Asset Category | |
| `pm_type` | Select | Quarterly/Semi-Annual/Annual |
| `version` | Data | Default "1.0" |
| `approved_by` | Link→User | |
| `checklist_items` | Table→PM Checklist Item | Child table |

**Child: `PM Checklist Item`**

| Field | Type | Notes |
| --- | --- | --- |
| `description` | Text | Mô tả công việc |
| `measurement_type` | Select | Pass/Fail / Numeric / Text |
| `unit` | Data | V, A, mmHg (khi Numeric) |
| `expected_min` | Float | Khi Numeric |
| `expected_max` | Float | Khi Numeric |
| `is_critical` | Check | Fail → Major Failure |
| `reference_section` | Data | Ví dụ: "Service Manual §3.2" |

#### 3. `PM Work Order` — Phiếu thực hiện bảo trì

**Naming Series:** `PM-WO-YYYY-#####`  
**Submittable**

| Field | Type | Notes |
| --- | --- | --- |
| `asset_ref` | Link→Asset | **Mandatory** |
| `pm_schedule` | Link→PM Schedule | **Mandatory** |
| `pm_type` | Data | Read-only từ PM Schedule |
| `wo_type` | Select | Preventive / Corrective (từ PM) |
| `source_pm_wo` | Link→PM Work Order | Mandatory khi wo_type=Corrective |
| `due_date` | Date | Từ PM Schedule.next_due_date |
| `completion_date` | Date | Set on Submit |
| `assigned_to` | Link→User | KTV thực hiện |
| `status` | Select | Open/In Progress/Pending–Device Busy/Overdue/Completed/Halted–Major Failure/Cancelled |
| `is_late` | Check | `completion_date > due_date` |
| `checklist_results` | Table→PM Checklist Result | Child table |
| `overall_result` | Select | Pass / Pass with Minor Issues / Fail |
| `pm_sticker_attached` | Check | |
| `duration_minutes` | Int | |

**Child: `PM Checklist Result`**

| Field | Type | Notes |
| --- | --- | --- |
| `checklist_item` | Link→PM Checklist Item | |
| `description` | Data | Read-only từ template |
| `result` | Select | Pass / Fail–Minor / Fail–Major / N/A |
| `measured_value` | Float | |
| `notes` | Text | |

**Controller hooks:**
- `validate`: tất cả checklist_results phải điền
- `validate`: item `is_critical=True` bị Fail → block, yêu cầu "Report Major Failure"
- `on_submit`: set `completion_date`, tính `is_late`, update PM Schedule, tính `next_due_date`
- `on_submit`: nếu `overall_result = Fail` → tạo CM Work Order con tự động

#### 4. `PM Task Log` — Nhật ký audit trail (immutable)

**Không submittable, không deletable**

| Field | Type | Notes |
| --- | --- | --- |
| `asset_ref` | Link→Asset | |
| `pm_work_order` | Link→PM Work Order | |
| `completion_date` | Date | |
| `technician` | Link→User | |
| `overall_result` | Select | |
| `is_late` | Check | |
| `days_late` | Int | |
| `next_pm_date` | Date | |

**Tạo tự động:** `on_submit` của PM Work Order

### Workflow States (PM Work Order)

```
Open
  → [Workshop Manager: Assign] → In Progress
  → [KTV: Device Busy] → Pending–Device Busy
  → [KTV: No Parts] → Pending–Parts Wait
  → [KTV: Complete checklist] → Completed  (nếu no failure)
  → [KTV: Major Failure] → Halted–Major Failure
       → [System: auto] → CM Work Order Created
```

### API cần tạo — `assetcore/api/imm08.py`

| # | Endpoint | Method | Mục đích |
| --- | --- | --- | --- |
| 1 | `get_pm_calendar` | GET | Calendar view theo tháng |
| 2 | `list_pm_work_orders` | GET | Danh sách WO phân trang |
| 3 | `get_pm_work_order` | GET | Chi tiết WO + checklist |
| 4 | `submit_pm_result` | POST | KTV nộp kết quả PM |
| 5 | `report_major_failure` | POST | Dừng PM, tạo CM WO khẩn |
| 6 | `reschedule_pm` | POST | Hoãn lịch PM |
| 7 | `get_pm_dashboard_stats` | GET | KPI: compliance rate, overdue |
| 8 | `get_asset_pm_history` | GET | Lịch sử PM của 1 asset |

### Scheduler Tasks cần thêm (`tasks.py`)

| Task | Cron | Mục đích |
| --- | --- | --- |
| `generate_pm_work_orders()` | Daily 06:00 | Tạo WO tự động khi đến hạn (idempotent) |
| `check_pm_overdue()` | Daily 08:00 | Đánh Overdue + escalation |

**Hàm event hook (từ IMM-04):**
```python
def create_pm_schedule_from_commissioning(commissioning_doc):
    """Triggered on_submit của Asset Commissioning — tạo PM Schedule đầu tiên."""
```

### Custom Fields cần add trên `Asset`

| Field | Type | Notes |
| --- | --- | --- |
| `custom_last_pm_date` | Date | Cập nhật từ PM Task Log |
| `custom_next_pm_date` | Date | Cập nhật từ PM Schedule |
| `custom_pm_status` | Select | On Schedule/Due Soon/Overdue/No Schedule |
| `custom_pm_compliance_pct` | Float | % PM đúng hạn (YTD) |

### Frontend cần tạo — `/frontend/src/`

| File | Chức năng |
| --- | --- |
| `views/PMCalendarView.vue` | Calendar view lịch PM tháng |
| `views/PMWorkOrderDetailView.vue` | KTV điền checklist PM |
| `views/PMDashboardView.vue` | KPI: compliance rate, overdue |
| `components/imm08/PMChecklistForm.vue` | Grid điền kết quả checklist |
| `components/imm08/MajorFailureDialog.vue` | Dialog báo lỗi major |
| `components/imm08/PMScheduleCard.vue` | Card hiển thị lịch PM |
| `api/imm08.ts` | API client |
| `stores/imm08Store.ts` | Pinia store |

### Business Rules

| BR | Nội dung | Kiểm soát |
| --- | --- | --- |
| BR-08-01 | PM WO phải có checklist template trước khi assign | Validate on WO creation |
| BR-08-02 | CM từ PM phải có `source_pm_wo` | `source_pm_wo` mandatory |
| BR-08-03 | `next_pm_date = completion_date + interval` (không phải due_date) | `on_submit` hook |
| BR-08-04 | Asset "Out of Service" không tạo PM WO mới | Scheduler condition check |
| BR-08-05 | PM hoàn thành sau due_date → `is_late = True` | Computed field |
| BR-08-06 | Class III: bắt buộc ảnh trước/sau PM | Attachment mandatory by risk class |
| BR-08-07 | Nhiều loại PM/asset → nhiều PM Schedule độc lập | `pm_type` phân biệt |
| BR-08-08 | Checklist 100% trước Submit WO | Validate before submit |

---

## IMM-09 — Corrective Maintenance (Sửa chữa / Khắc phục)

### Trạng thái: ⚠️ BA SƠ BỘ · ❌ CHƯA CODE

**Cần tạo tài liệu:** `docs/imm-09/IMM-09_Functional_Specs.md` + `IMM-09_Technical_Design.md`

### DocTypes cần thiết kế & tạo

#### 1. `CM Work Order` — Phiếu sửa chữa

**Naming Series:** `CM-WO-YYYY-#####`  
**Submittable**

**Fields cần bao gồm:**

| Field | Type | Notes |
| --- | --- | --- |
| `asset_ref` | Link→Asset | |
| `source_type` | Select | Ad-hoc Report / From PM / From IMM-12 |
| `source_pm_wo` | Link→PM Work Order | Khi source_type = "From PM" |
| `source_incident` | Link→Incident Report | Khi source_type = "From IMM-12" |
| `failure_description` | Text | |
| `priority` | Select | P1 Critical / P2 High / P3 Medium / P4 Low |
| `assigned_to` | Link→User | |
| `status` | Select | Open/Assigned/In Progress/Pending–Parts/Completed/Cancelled |
| `root_cause` | Text | Bắt buộc trước khi close |
| `resolution` | Text | Bắt buộc trước khi close |
| `completion_date` | Datetime | |
| `downtime_hours` | Float | Computed: completion - breakdown |
| `mttr_hours` | Float | Mean Time To Repair |
| `repair_cost` | Currency | |
| `spare_parts_used` | Table→CM Spare Part Usage | |
| `is_under_warranty` | Check | Linked từ Asset.warranty_expiry |
| `firmware_updated` | Check | Nếu có firmware change |
| `firmware_change_request` | Link→Firmware Change Request | Khi firmware_updated = True |

**Child: `CM Spare Part Usage`**

| Field | Type | Notes |
| --- | --- | --- |
| `item_code` | Link→Item | |
| `qty` | Float | |
| `warehouse` | Link→Warehouse | Default: kho Kỹ thuật TBYT |
| `actual_cost` | Currency | Read-only từ item valuation rate |

**Controller:** `on_submit` → tạo Stock Entry (Material Issue) nếu spare_parts_used có data

#### 2. `Firmware Change Request` — Yêu cầu nâng cấp firmware

**Naming Series:** `FCR-YYYY-#####`  
**Submittable — approval workflow**

| Field | Type | Notes |
| --- | --- | --- |
| `asset_ref` | Link→Asset | |
| `firmware_version_before` | Data | |
| `firmware_version_after` | Data | |
| `change_justification` | Text | |
| `approved_by` | Link→User | |
| `approval_date` | Date | |

**Workflow:** `Draft → Pending_Approval → Approved / Rejected`

### API cần tạo — `assetcore/api/imm09.py`

- `create_cm_work_order` — tạo WO từ PM, incident, hoặc ad-hoc
- `list_cm_work_orders` — danh sách + filter
- `get_cm_work_order` — chi tiết + spare parts
- `update_cm_work_order` — cập nhật tiến độ
- `close_cm_work_order` — đóng WO + root cause + resolution
- `get_cm_dashboard_stats` — MTTR, MTBF, repeat failure rate

### Business Rules (cần confirm với BA)

| BR | Nội dung |
| --- | --- |
| BR-09-01 | Tất cả spare parts phải traceable đến WO — tạo Stock Entry khi Submit |
| BR-09-02 | Firmware change phải có Firmware Change Request được Approve trước khi thực hiện |
| BR-09-03 | CM từ PM phải tham chiếu PM WO nguồn (`source_pm_wo`) |
| BR-09-04 | `root_cause` + `resolution` bắt buộc trước khi close WO |
| BR-09-05 | `MTTR = completion_datetime - created_datetime` |
| BR-09-06 | ≥3 lần sửa cùng lỗi trong 90 ngày → trigger RCA (IMM-12) |

---

## IMM-11 — Calibration & Inspection (Hiệu chuẩn)

### Trạng thái: ⚠️ BA SƠ BỘ · ❌ CHƯA CODE

**Cần tạo tài liệu:** `docs/imm-11/IMM-11_Functional_Specs.md` + `IMM-11_Technical_Design.md`

### DocTypes cần thiết kế & tạo

#### 1. `Calibration Work Order` — Phiếu hiệu chuẩn

**Naming Series:** `CAL-WO-YYYY-#####`  
**Submittable**

| Field | Type | Notes |
| --- | --- | --- |
| `asset_ref` | Link→Asset | |
| `calibration_type` | Select | Internal / External (ISO 17025 lab) |
| `due_date` | Date | Từ Asset.calibration_expiry_date |
| `assigned_to` | Link→User | |
| `lab_name` | Data | Tên lab ISO 17025 (nếu External) |
| `lab_accreditation_no` | Data | Số chứng chỉ ISO 17025 |
| `measurement_results` | Table→Calibration Measurement | |
| `overall_result` | Select | Pass / Fail–Minor / Fail–Out-of-Tolerance |
| `certificate_attached` | Attach | File chứng nhận |
| `new_expiry_date` | Date | Ngày hết hạn mới sau calibration |
| `clinical_impact_assessed` | Check | Bắt buộc khi Fail (lookback) |
| `clinical_impact_notes` | Text | |

#### 2. `CAPA Record` — Hành động khắc phục & phòng ngừa

**Naming Series:** `CAPA-YYYY-#####`  
**Submittable — full approval workflow**

| Field | Type | Notes |
| --- | --- | --- |
| `capa_type` | Select | Corrective / Preventive |
| `trigger_source` | Select | Calibration Fail / Incident / PM Fail / Audit |
| `source_record` | Dynamic Link | Calibration WO / CM WO / PM WO |
| `asset_ref` | Link→Asset | |
| `severity` | Select | Minor / Major / Critical |
| `description` | Text | |
| `root_cause` | Text | Bắt buộc trước close |
| `corrective_action` | Text | |
| `preventive_action` | Text | |
| `assigned_to` | Link→User | |
| `due_date` | Date | |
| `verification_date` | Date | |
| `closed_by` | Link→User | |

**Workflow:** `Open → Under Investigation → Action Defined → Action Implemented → Verified → Closed`

### Business Rules (cần confirm với BA)

| BR | Nội dung |
| --- | --- |
| BR-11-01 | Thiết bị đo lường phải có chứng nhận calibration còn hạn trước khi vận hành |
| BR-11-02 | Kết quả Fail–Out-of-Tolerance BẮT BUỘC tạo CAPA Record (không thể bỏ qua) |
| BR-11-03 | Chứng nhận phải từ lab được ISO 17025 công nhận (external calibration) |
| BR-11-04 | Lookback: phải đánh giá clinical impact của khoảng thời gian thiết bị dùng với calibration sai |
| BR-11-05 | Hết hạn calibration → Asset.status = "Pending_Calibration" (scheduler) |

### Scheduler Tasks cần thêm

| Task | Cron | Mục đích |
| --- | --- | --- |
| `check_calibration_expiry()` | Daily | Cảnh báo 60/30/7 ngày, set Pending_Calibration khi hết hạn |

---

## IMM-12 — Corrective Maintenance + SLA + RCA

### Trạng thái: ⚠️ BA SƠ BỘ · ❌ CHƯA CODE

**Cần tạo tài liệu:** `docs/imm-12/IMM-12_Functional_Specs.md` + `IMM-12_Technical_Design.md`

### DocTypes cần thiết kế & tạo

#### 1. `Incident Report` — Báo hỏng / Sự cố thiết bị

**Naming Series:** `IR-YYYY-#####`  
**Submittable**

| Field | Type | Notes |
| --- | --- | --- |
| `asset_ref` | Link→Asset | |
| `reported_by` | Link→User | |
| `reported_dept` | Link→Department | |
| `incident_description` | Text | |
| `priority` | Select | P1–Critical / P2–High / P3–Medium / P4–Low |
| `sla_response_deadline` | Datetime | Auto: reported_at + SLA per priority |
| `sla_resolution_deadline` | Datetime | Auto: based on priority |
| `sla_response_status` | Select | On Time / Breached / At Risk |
| `sla_resolution_status` | Select | On Time / Breached / At Risk |
| `assigned_cm_wo` | Link→CM Work Order | |
| `downtime_start` | Datetime | |
| `downtime_end` | Datetime | |
| `total_downtime_hours` | Float | Computed |
| `department_signoff` | Check | P1: bắt buộc trước khi close |

#### 2. `RCA Record` — Root Cause Analysis

**Naming Series:** `RCA-YYYY-#####`  
**Submittable**

| Field | Type | Notes |
| --- | --- | --- |
| `asset_ref` | Link→Asset | |
| `trigger_type` | Select | Chronic Failure (≥3x) / P1 Incident / Request |
| `incidents_referenced` | Table→RCA Incident Link | Danh sách incidents liên quan |
| `failure_pattern` | Text | Mô tả pattern lỗi lặp lại |
| `fishbone_analysis` | Text | 5-Why hoặc Ishikawa |
| `root_cause` | Text | |
| `corrective_actions` | Table→RCA Action Item | |
| `preventive_measures` | Text | |
| `capa_record` | Link→CAPA Record | Auto-tạo CAPA nếu severity >= Major |

### SLA Matrix

| Priority | Trigger | Response SLA | Resolution SLA | Escalation |
| --- | --- | --- | --- | --- |
| P1–Critical | Life-critical equipment failure | ≤ 2h | ≤ 8h | Notify PTP + BGĐ at breach |
| P2–High | Important equipment OOS | ≤ 4h | ≤ 24h | Notify Workshop Head at breach |
| P3–Medium | Non-critical equipment | ≤ 24h | ≤ 72h | Notify Workshop Manager |
| P4–Low | Minor issue, workaround available | ≤ 72h | ≤ 7 days | Standard queue |

### Business Rules (cần confirm với BA)

| BR | Nội dung |
| --- | --- |
| BR-12-01 | P1 SLA breach → tự động notify PTP + BGĐ + ghi CAPA record |
| BR-12-02 | P1 WO không close được nếu thiếu `department_signoff` |
| BR-12-03 | ≥3 incidents cùng lỗi trên cùng asset trong 90 ngày → BẮT BUỘC mở RCA |
| BR-12-04 | Downtime tracking: `total_downtime_hours = downtime_end - downtime_start` |
| BR-12-05 | Asset status = "Out of Service" từ khi Incident reported đến khi CM WO closed |

### Scheduler Tasks cần thêm

| Task | Cron | Mục đích |
| --- | --- | --- |
| `check_sla_deadlines()` | Every 30 min | Check SLA breach + gửi cảnh báo |
| `check_chronic_failure_patterns()` | Daily | Phát hiện ≥3 incidents, mở RCA |

---

## Lộ trình triển khai đề xuất

### Sprint hiện tại (IMM-08 ưu tiên — tài liệu đã đầy đủ)

1. **Tuần 1:** Tạo 4 DocTypes (PM Schedule, PM Checklist Template, PM Work Order, PM Task Log)
2. **Tuần 1:** Tạo `assetcore/api/imm08.py` — 8 endpoints
3. **Tuần 1:** Thêm `generate_pm_work_orders()` + `check_pm_overdue()` vào `tasks.py`
4. **Tuần 2:** Hook vào `asset_commissioning.on_submit` → `create_pm_schedule_from_commissioning()`
5. **Tuần 2:** Frontend: PMCalendarView, PMWorkOrderDetailView, PMChecklistForm
6. **Tuần 2:** UAT: viết test cases theo `docs/imm-08/IMM-08_Functional_Specs.md`

### Sprint tiếp theo (IMM-09 + IMM-12 — cần viết spec trước)

- BA: viết `docs/imm-09/IMM-09_Functional_Specs.md`
- BA: viết `docs/imm-12/IMM-12_Functional_Specs.md`
- Sau khi spec được approve → implement BE + FE

### Sprint cuối Wave 1 (IMM-11 — phụ thuộc CAPA)

- CAPA DocType dùng chung cho IMM-11 và IMM-12 → thiết kế trước
- Calibration scheduler tích hợp với IMM-05 (document expiry pattern sẵn có)

---

## Dependency Map

```
IMM-04 (Installation)
  └── triggers → IMM-05 (creates initial document set)
  └── triggers → IMM-08 (creates PM Schedule on submit)

IMM-08 (PM)
  └── on failure → IMM-09 (CM Work Order, source_pm_wo)
  └── on major failure → IMM-12 (Incident Report)

IMM-12 (Incident)
  └── creates → IMM-09 (CM Work Order, source_incident)
  └── chronic failure → RCA Record → IMM-11 CAPA

IMM-11 (Calibration)
  └── on fail → CAPA Record
  └── shares CAPA DocType với IMM-12

IMM-05 (Documents)
  └── GW-2 blocks → IMM-04 Submit
  └── Service Manual docs → IMM-08 checklist template source
```

---

## Tài liệu tham chiếu

| Tài liệu | Đường dẫn |
| --- | --- |
| IMM-08 Functional Specs | `docs/imm-08/IMM-08_Functional_Specs.md` |
| IMM-08 Technical Design | `docs/imm-08/IMM-08_Technical_Design.md` |
| IMM-05 Functional Specs | `docs/imm-05/IMM-05_Functional_Specs.md` |
| IMM-05 Technical Design | `docs/imm-05/IMM-05_Technical_Design.md` |
| IMM-04 DocType Design | `docs/data-model/IMM-04_DocType_Design.md` |
| Wave 1 BA Analysis | `docs/architecture/AssetCore_Wave1_BA_Analysis.html` |
| Project Context | `CLAUDE.md` (root) |
