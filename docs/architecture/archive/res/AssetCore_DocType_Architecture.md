# AssetCore — Phân tích ERPNext Asset & Kiến trúc DocType

**Phiên bản:** 1.0 | **Ngày:** 2026-04-17
**Mục tiêu:** Phân tích nền tảng ERPNext Asset, xác định những gì kế thừa và những gì cần xây mới để AssetCore thành hệ thống quản lý vòng đời tài sản y tế hoàn chỉnh.

---

## 1. Tổng quan — Tại sao không dùng ERPNext Asset thuần?

ERPNext Asset module được thiết kế cho **kế toán tài sản cố định** (fixed asset accounting) — khấu hao, sổ sách tài chính, vốn hóa. Đây là một công cụ tài chính, không phải HTM (Health Technology Management).

| Tiêu chí | ERPNext Asset | AssetCore cần |
|---|---|---|
| Mục tiêu chính | Khấu hao & kế toán | Vòng đời vận hành |
| Work Order | Chỉ có Asset Repair (cơ bản) | PM WO, CM WO, Calibration WO, Incident |
| Calibration | Không có | Bắt buộc (WHO HTM §5.4) |
| Risk classification | Không có | Class I/II/III, P1–P4 SLA |
| QMS / Audit trail | Minimal | Bắt buộc per action |
| Document lifecycle | Không có | Hết hạn, phê duyệt, NĐ98 |
| Scheduler automation | Không có | PM/Cal/Doc expiry daily jobs |
| CAPA | Không có | Bắt buộc khi calibration fail |
| Commissioning | Không có | IMM-04 full workflow |
| Inventory (medical) | Không có | UDI, GMDN, device model |

**Chiến lược của AssetCore:** Giữ ERPNext Asset làm **registry (sổ đăng ký)** duy nhất — mọi DocType mới của AssetCore link về đây. Không override core, chỉ extend.

---

## 2. ERPNext Asset — Phân tích chi tiết 21 DocType gốc

### 2.1 Nhóm Core Registry

#### `Asset` _(Submittable — track_changes: 1)_
Trung tâm của toàn bộ hệ thống. AssetCore link mọi thứ về đây.

| Field quan trọng | Kiểu | Ghi chú |
|---|---|---|
| `asset_name` | Data | Tên tài sản |
| `item_code` | Link → Item | Mã vật tư ERPNext |
| `asset_category` | Link → Asset Category | Phân loại |
| `location` | Link → Location | Vị trí hiện tại |
| `custodian` | Link → Employee | Người phụ trách |
| `company` | Link → Company | Công ty sở hữu |
| `purchase_date` | Date | Ngày mua |
| `gross_purchase_amount` | Currency | Giá trị mua |
| `status` | Select | Draft/Submitted/Sold/Scrapped/**In Maintenance**/**Out of Order**/Capitalized |
| `calculate_depreciation` | Check | Bật khấu hao |
| `depreciation_method` | Select | Phương pháp khấu hao |
| `finance_books` | Table | Asset Finance Book |
| `insurance_*` | — | Thông tin bảo hiểm |

**Thiếu cho HTM (cần Custom Fields):**
- UDI / GMDN code
- Device Model (IMM Device Model)
- Medical device class (Class I/II/III)
- Risk class (Low/Medium/High/Critical)
- BYT registration number
- Manufacturer serial number
- Department (Link → Department)
- Responsible technician
- Last/Next PM date, Last/Next calibration date
- IMM lifecycle status (Active/Under Repair/Calibrating/OOS/Decommissioned)
- Calibration status (In Tolerance / Out of Tolerance)

#### `Asset Category`
Dùng cho PM Checklist Template (per category + PM type). **Giữ nguyên, không sửa.**

#### `Location` _(Hierarchical)_
Cây vị trí: Bệnh viện → Tòa nhà → Tầng → Khoa → Phòng.
**Giữ nguyên.** AssetCore tạo `IMM Location Ext` để mở rộng thêm thông tin khoa lâm sàng.

### 2.2 Nhóm Maintenance & Repair

#### `Asset Maintenance`
Quản lý đội bảo trì và lịch bảo trì template. **Quá sơ sài cho HTM** — không có Work Order, không có checklist theo category, không có SLA.

→ **AssetCore không dùng.** Thay bằng `IMM PM Work Order` + `IMM PM Schedule`.

#### `Asset Maintenance Log`
Log bảo trì đơn giản. Không submittable, không audit trail đủ mức.

→ **AssetCore không dùng.** Thay bằng `IMM PM Task Log` (immutable).

#### `Asset Repair` _(Submittable)_
ERPNext cơ bản nhất: `failure_date`, `repair_status` (Pending/Completed), `repair_cost`. Thiếu: SLA, fault code, MTTR, spare parts tracking đúng nghĩa, firmware, sign-off workflow.

→ **AssetCore extend:** `IMM CM Work Order` kế thừa cấu trúc nhưng thêm toàn bộ HTM fields.

#### `Asset Maintenance Team` / `Asset Maintenance Task`
Đội bảo trì và task template. **Không dùng** — AssetCore dùng Frappe User + Role thay.

### 2.3 Nhóm Depreciation & Finance

| DocType | Dùng cho | AssetCore |
|---|---|---|
| Asset Finance Book | Khấu hao theo sổ | Giữ nguyên — kế toán |
| Asset Depreciation Schedule | Lịch khấu hao | Giữ nguyên — kế toán |
| Asset Value Adjustment | Điều chỉnh giá trị | Giữ nguyên — kế toán |
| Asset Shift Allocation | Khấu hao ca | Giữ nguyên — kế toán |
| Asset Shift Factor | Hệ số ca | Giữ nguyên — kế toán |
| Asset Capitalization | Vốn hóa | Giữ nguyên — kế toán |

**Nhận xét:** Toàn bộ nhóm này là tài chính thuần túy. AssetCore không chạm vào.

### 2.4 Nhóm Utility & Tracking

#### `Asset Movement` _(Submittable)_
Issue / Receipt / Transfer / Transfer and Issue. Theo dõi điều chuyển vật lý thiết bị.

→ **AssetCore dùng lại.** IMM-13 (Decommission) sẽ link về đây khi điều chuyển.

#### `Asset Activity`
Log các hoạt động asset. **Dùng làm nơi AssetCore ghi lifecycle events.**

#### `Linked Location`
Junction table asset-location. **Giữ nguyên.**

---

## 3. Mapping: ERPNext Asset → AssetCore DocType

```
ERPNext Core (GIỮ NGUYÊN)          AssetCore Extension
═══════════════════════════         ═══════════════════════════════════════
Asset                      ←────── IMM Commissioning Record (IMM-04)
  ↑ custom fields added             IMM Asset Document (IMM-05)
  │                                 IMM PM Work Order (IMM-08)
  │                                 IMM PM Schedule (IMM-08)
  │                                 IMM CM Work Order (IMM-09)  ← extends Asset Repair
  │                                 IMM Calibration Record (IMM-11)
  │                                 IMM Calibration Schedule (IMM-11)
  │                                 IMM Incident Report (IMM-12)
  │                                 IMM CAPA Record (IMM-11/12)
  │
Asset Category             ←────── IMM PM Checklist Template (IMM-08)
Asset Repair               ←────── IMM CM Work Order kế thừa cấu trúc
Asset Movement             ←────── IMM Asset Transfer (IMM-13)
Asset Activity             ←────── IMM Audit Trail ghi vào đây
Location                   ←────── IMM Location Ext (mở rộng thông tin khoa)
Item                       ←────── IMM Device Model (master thiết bị y tế)
Supplier                   ←────── IMM Vendor Profile (hồ sơ nhà cung cấp)
Department                 ←────── Dùng trực tiếp (không extend)
```

---

## 4. AssetCore DocType Architecture — Toàn bộ 42 DocType

### 4.1 Sơ đồ tổng thể

```
┌─────────────────────────────────────────────────────────────────────┐
│                        MASTER DATA LAYER                            │
│  IMM Device Model  │  IMM Vendor Profile  │  IMM Location Ext       │
│  IMM Risk Profile  │  IMM SLA Policy      │  IMM Audit Trail        │
└─────────────────────────────────────────────────────────────────────┘
                              │ link
┌─────────────────────────────▼───────────────────────────────────────┐
│                    ASSET REGISTRY (ERPNext Core)                    │
│                    Asset + Custom Fields (12 fields)                │
└────────────────────┬────────────────────────────────────────────────┘
                     │
     ┌───────────────┼─────────────────────────────────┐
     ▼               ▼               ▼                 ▼
┌─────────┐   ┌──────────┐   ┌────────────┐   ┌──────────────┐
│ IMM-04  │   │  IMM-05  │   │  IMM-08    │   │   IMM-09     │
│Commission│  │ Document │   │    PM      │   │   Repair     │
│ Record  │   │ Lifecycle│   │ Schedule   │   │  CM Work     │
│         │   │          │   │ Work Order │   │   Order      │
└────┬────┘   └────┬─────┘   └─────┬──────┘   └──────┬───────┘
     │              │               │                  │
     │              │      ┌────────┼──────────┐       │
     │              │      ▼        ▼          ▼       │
     │              │  IMM-11    IMM-12    IMM-15      │
     │              │  Calibra-  Incident  Spare       │
     │              │  tion      Report    Parts       │
     │              │            CAPA               ───┘
     │              │
     ▼              ▼
 IMM-13/14      IMM QMS
 Decommission   (CAPA, RCA,
 Disposal       Change Ctrl)
```

---

### 4.2 MASTER DATA — 6 DocTypes

#### M-01: `IMM Device Model`
> Master catalog thiết bị y tế. Một Model → nhiều Asset (instance thực tế).

| Field | Kiểu | Bắt buộc | Mô tả |
|---|---|---|---|
| `model_name` | Data | ✅ | Tên model thiết bị |
| `manufacturer` | Link → Supplier | ✅ | Hãng sản xuất |
| `model_code` | Data | ✅ | Mã model nội bộ |
| `gmdn_code` | Data | | Global Medical Device Nomenclature |
| `emdn_code` | Data | | European MD Nomenclature |
| `device_category` | Link → Asset Category | ✅ | Phân loại ERPNext |
| `medical_device_class` | Select: Class I/II/III | ✅ | Phân loại rủi ro BYT |
| `risk_class` | Select: Low/Medium/High/Critical | ✅ | Theo WHO HTM |
| `is_calibration_required` | Check | ✅ | Có cần hiệu chuẩn không |
| `calibration_interval_days` | Int | | Chu kỳ hiệu chuẩn (ngày) |
| `is_pm_required` | Check | ✅ | Có cần bảo trì định kỳ không |
| `pm_interval_days` | Int | | Chu kỳ PM (ngày) |
| `expected_lifespan_years` | Float | | Tuổi thọ dự kiến |
| `ifm_document` | Link → IMM Asset Document | | IFU (hướng dẫn sử dụng) |
| `service_manual` | Link → IMM Asset Document | | Service Manual |
| `spare_parts_list` | Table | | Danh mục phụ tùng mặc định |
| `firmware_version_current` | Data | | Firmware hiện tại |

**Kế thừa từ:** ERPNext `Item` (mã vật tư gốc)

---

#### M-02: `IMM Vendor Profile`
> Mở rộng thông tin nhà cung cấp/nhà sản xuất thiết bị y tế.

| Field | Kiểu | Mô tả |
|---|---|---|
| `supplier` | Link → Supplier | ERPNext supplier gốc |
| `vendor_type` | Select: Manufacturer/Distributor/Service Agent | |
| `iso_13485_certified` | Check | Chứng nhận ISO 13485 |
| `iso_17025_certified` | Check | Phòng lab ISO/IEC 17025 |
| `moh_registration_no` | Data | Số đăng ký BYT |
| `support_contact` | Data | Hotline hỗ trợ kỹ thuật |
| `service_contract_ref` | Data | Số hợp đồng bảo hành |
| `contract_start` / `contract_end` | Date | Thời hạn hợp đồng |
| `sla_response_hours` | Int | Cam kết thời gian phản hồi |
| `authorized_technicians` | Table | Danh sách KTV được ủy quyền |

---

#### M-03: `IMM Location Ext`
> Mở rộng `Location` ERPNext với thông tin khoa lâm sàng BV.

| Field | Kiểu | Mô tả |
|---|---|---|
| `location` | Link → Location | ERPNext location gốc |
| `dept_code` | Data | Mã khoa nội bộ |
| `dept_head` | Link → Employee | Trưởng khoa |
| `clinical_area_type` | Select: ICU/OR/Ward/Lab/Radiology/Emergency/Outpatient/Admin | |
| `floor_plan_ref` | Attach | Sơ đồ tầng (PDF) |
| `asset_count` | Int (computed) | Số thiết bị trong khoa |
| `emergency_contact` | Data | SĐT liên hệ khi sự cố |

---

#### M-04: `IMM SLA Policy`
> Định nghĩa SLA theo risk class và loại sự cố. Dùng chung IMM-09, IMM-12.

| Field | Kiểu | Mô tả |
|---|---|---|
| `policy_name` | Data | Tên chính sách |
| `priority_level` | Select: P1/P2/P3/P4 | |
| `risk_class` | Select: Critical/High/Medium/Low | |
| `response_time_minutes` | Int | Thời gian phản hồi (phút) |
| `resolution_time_hours` | Int | Thời gian giải quyết (giờ) |
| `escalation_level_1_hours` | Int | Escalate Level 1 sau N giờ |
| `escalation_level_2_hours` | Int | Escalate BGĐ sau N giờ |
| `effective_date` | Date | Ngày áp dụng |

---

#### M-05: `IMM Audit Trail`
> Log immutable mọi thay đổi trạng thái trong hệ thống. Append-only.

| Field | Kiểu | Mô tả |
|---|---|---|
| `asset` | Link → Asset | Thiết bị liên quan |
| `source_doctype` | Data | DocType phát sinh event |
| `source_name` | Dynamic Link | Document phát sinh |
| `event_type` | Select | State Change/Submit/Cancel/Comment/Alert/CAPA/Escalation |
| `from_status` | Data | Trạng thái trước |
| `to_status` | Data | Trạng thái sau |
| `actor` | Link → User | Người thực hiện |
| `event_timestamp` | Datetime | Thời điểm (UTC) |
| `ip_address` | Data | IP client |
| `remarks` | Text | Ghi chú |
| `hash` | Data | SHA-256 của record (tamper detection) |

**Nguyên tắc:** `is_immutable = 1` — không update, không delete, chỉ insert.

---

#### M-06: `IMM CAPA Record`
> Corrective and Preventive Action. Dùng chung IMM-11 (cal fail) và IMM-12 (P1/P2 incident).

| Field | Kiểu | Mô tả |
|---|---|---|
| `capa_number` | Autoname: `CAPA-.YYYY.-.#####` | |
| `asset` | Link → Asset | Thiết bị |
| `source_doctype` | Select: IMM Asset Calibration/IMM Incident Report | Nguồn phát sinh |
| `source_name` | Dynamic Link | |
| `capa_type` | Select: Corrective/Preventive | |
| `severity` | Select: Critical/Major/Minor | |
| `description` | Text | Mô tả vấn đề |
| `root_cause` | Text | Phân tích nguyên nhân gốc |
| `corrective_action` | Text | Hành động khắc phục |
| `preventive_action` | Text | Hành động ngăn ngừa |
| `assigned_to` | Link → User | Người phụ trách |
| `due_date` | Date | Hạn chót |
| `status` | Select: Open/In Progress/Pending Verification/Closed/Overdue | |
| `closed_by` | Link → User | |
| `closed_date` | Date | |
| `verification_result` | Select: Effective/Partially Effective/Not Effective | |
| `linked_rca` | Link → IMM RCA Record | RCA nếu có |

---

### 4.3 BLOCK 2 — DEPLOYMENT (IMM-04, IMM-05, IMM-06)

#### D-01: `IMM Commissioning Record` _(hiện có: Asset Commissioning)_
> Toàn bộ quy trình lắp đặt, định danh, kiểm tra ban đầu. **Đã implement.**

| Field nhóm | Nội dung |
|---|---|
| **Procurement** | PO reference, vendor, master item (Device Model) |
| **Installation** | Installation date, vendor engineer, site checklist pass |
| **Identification** | Vendor serial no (barcode), internal QR tag, MOH code |
| **Risk** | Device class, risk class, radiation device flag |
| **Baseline Tests** | Child table: Commissioning Checklist (pass/fail per parameter) |
| **Documents** | Child table: Commissioning Document Record |
| **QA** | Overall inspection result (Pass/Fail/Conditional Pass) |
| **Release** | Clinical release date, released by, final_asset (created Asset) |
| **Audit** | Lifecycle Events (child table) |

**Workflow states:** `Draft → Site_Ready → Installation → Baseline_Test → QA_Review → Clinical_Hold → Clinical_Release → Archived`

**Integration triggers on `Clinical_Release`:**
- Tạo `IMM PM Schedule` (nếu device model có PM)
- Tạo `IMM Calibration Schedule` (nếu device model có calibration)
- Tạo `Asset` trong ERPNext
- Ghi `IMM Audit Trail`

**Child DocTypes:**
- `IMM Commissioning Checklist` (baseline test items)
- `IMM Commissioning Document` (document compliance per commissioning)
- `IMM Asset Lifecycle Event` (audit per action)
- `IMM Asset QA Non-Conformance` (DOA, damage tracking)

---

#### D-02: `IMM Asset Document` _(hiện có: Asset Document)_
> Quản lý hồ sơ tài sản có vòng đời (hết hạn, phê duyệt, NĐ98). **Đã implement.**

| Field nhóm | Nội dung |
|---|---|
| **Reference** | Asset ref, Device Model, is_model_level |
| **Classification** | doc_category, doc_type_detail, doc_number |
| **Validity** | issued_date, expiry_date, issuing_authority |
| **File** | file_attachment (attach) |
| **Version** | version, superseded_by, archive_date |
| **Exemption** | is_exempt, exempt_reason (theo NĐ98) |
| **Approval** | approved_by, rejection_reason |

**Workflow states:** `Draft → Submitted → Under_Review → Approved → Active → Expired → Superseded`

**Scheduler jobs:**
- `check_document_expiry()` — daily, gửi alert 90/60/30/7 ngày trước hạn
- `update_asset_completeness()` — tính % hoàn thiện hồ sơ
- `check_overdue_document_requests()` — escalate request quá hạn

**Child/Linked DocTypes:**
- `IMM Document Request` (yêu cầu bổ sung hồ sơ)
- `IMM Expiry Alert Log` (log thông báo hết hạn)

---

#### D-03: `IMM Training Record` _(chưa có — IMM-06)_
> Theo dõi đào tạo người dùng thiết bị y tế. **Wave 2.**

| Field | Kiểu | Mô tả |
|---|---|---|
| `asset` | Link → Asset | Thiết bị đào tạo |
| `device_model` | Link → IMM Device Model | |
| `trainee` | Link → Employee | Người được đào tạo |
| `trainer` | Link → Employee | Người đào tạo |
| `training_type` | Select: Initial/Refresher/Upgrade | |
| `training_date` | Date | |
| `competency_level` | Select: Aware/Competent/Proficient | |
| `certificate_file` | Attach | Chứng chỉ |
| `expiry_date` | Date | Hạn hiệu lực |
| `dept` | Link → Department | |

---

### 4.4 BLOCK 3 — OPERATIONS & MAINTENANCE

#### O-01: `IMM PM Schedule` _(chưa có — IMM-08)_
> Lịch PM định kỳ tự động tạo sau commissioning. Non-submittable, master record.

| Field | Kiểu | Bắt buộc | Mô tả |
|---|---|---|---|
| `schedule_name` | Autoname: `PMS-.YYYY.-.#####` | | |
| `asset` | Link → Asset | ✅ | Thiết bị |
| `device_model` | Link → IMM Device Model | | |
| `pm_type` | Select: Quarterly/Semi-Annual/Annual/Ad-hoc | ✅ | Loại PM |
| `pm_interval_days` | Int | ✅ | Chu kỳ (ngày) |
| `checklist_template` | Link → IMM PM Checklist Template | ✅ | Template checklist |
| `responsible_technician` | Link → User | | |
| `alert_days_before` | Int (default: 30) | | Cảnh báo trước N ngày |
| `status` | Select: Active/Paused/Suspended | | |
| `first_pm_date` | Date | ✅ | = commissioning_date + interval |
| `last_pm_date` | Date | | Cập nhật sau mỗi lần hoàn thành |
| `next_due_date` | Date | | = last completion_date + interval |
| `created_from_commissioning` | Link → IMM Commissioning Record | | |

---

#### O-02: `IMM PM Checklist Template` _(chưa có — IMM-08)_
> Reusable template checklist theo Asset Category + PM type. Versioned.

| Field | Kiểu | Mô tả |
|---|---|---|
| `template_name` | Data | Tên template |
| `asset_category` | Link → Asset Category | |
| `pm_type` | Select: Quarterly/Semi-Annual/Annual | |
| `version` | Data (default: 1.0) | |
| `effective_date` | Date | |
| `approved_by` | Link → User | |
| `checklist_items` | Table → IMM PM Checklist Item | Danh mục hạng mục |

**Child: `IMM PM Checklist Item`**

| Field | Mô tả |
|---|---|
| `item_name` | Tên hạng mục |
| `description` | Mô tả chi tiết |
| `measurement_type` | Numeric/Pass-Fail/Visual/N/A |
| `is_critical` | Hạng mục quan trọng (fail → stop PM) |
| `unit` | Đơn vị đo |
| `expected_min` / `expected_max` | Ngưỡng chấp nhận |

---

#### O-03: `IMM PM Work Order` _(chưa có — IMM-08)_
> Lệnh công việc PM cho từng lần thực hiện. Submittable.

| Field | Kiểu | Mô tả |
|---|---|---|
| `wo_number` | Autoname: `PM-WO-.YYYY.-.#####` | |
| `asset` | Link → Asset | |
| `pm_schedule` | Link → IMM PM Schedule | |
| `pm_type` | Select | |
| `due_date` | Date | |
| `scheduled_date` | Date | |
| `completion_date` | Date | |
| `assigned_to` | Link → User | KTV được phân công |
| `assigned_by` | Link → User | Workshop Manager |
| `status` | Select: Open/Assigned/In Progress/Pending-Device Busy/Overdue/Halted-Major Failure/Completed/Cancelled | |
| `is_late` | Check (computed) | = completion_date > due_date |
| `days_late` | Int (computed) | |
| `overall_result` | Select: Pass/Pass with Minor Issues/Fail | |
| `technician_notes` | Text | |
| `duration_minutes` | Int | |
| `photo_before` / `photo_after` | Attach | Bắt buộc Class III (BR-08-06) |
| `checklist_results` | Table → IMM PM Checklist Result | |
| `source_cm_wo` | Link → IMM CM Work Order | CM WO nếu phát sinh lỗi |

**Workflow states:** `Draft → Scheduled → Assigned → In Progress → Pending-Device Busy → Overdue → Halted-Major Failure → Completed → Cancelled`

**On Submit:**
- Nếu `is_late`: ghi vào IMM Audit Trail
- Tính `next_due_date = completion_date + interval` (BR-08-03)
- Cập nhật `IMM PM Schedule.last_pm_date` và `next_due_date`
- Cập nhật `Asset.custom_imm_last_pm_date`
- Nếu `overall_result = Fail`: tạo `IMM CM Work Order`
- Tạo `IMM PM Task Log` (immutable)

---

#### O-04: `IMM PM Task Log` _(chưa có — IMM-08)_
> Hồ sơ bất biến sau mỗi lần PM hoàn thành. Insert-only, không update/delete.

| Field | Mô tả |
|---|---|
| `asset` | Thiết bị |
| `pm_work_order` | WO tham chiếu |
| `pm_type` | Loại PM |
| `completion_date` | Ngày hoàn thành |
| `technician` | KTV |
| `overall_result` | Kết quả |
| `is_late` | Có trễ không |
| `days_late` | Số ngày trễ |
| `next_pm_date` | Ngày PM tiếp theo |

---

#### O-05: `IMM CM Work Order` _(chưa có — IMM-09)_
> Lệnh sửa chữa CM (Corrective Maintenance). Extend ERPNext Asset Repair.

| Field nhóm | Nội dung |
|---|---|
| **Identity** | `WO-CM-.YYYY.-.#####`, asset, device_model, serial_no |
| **Source** | incident_report, source_pm_wo, repair_type (Corrective/Emergency/Warranty) |
| **Priority** | priority (Normal/Urgent/Emergency), risk_class |
| **Status** | Open/Assigned/Diagnosing/Pending Parts/In Repair/Pending Inspection/Completed/Cannot Repair/Cancelled |
| **SLA** | sla_policy, sla_target_hours, mttr_hours (computed), sla_breached |
| **Timeline** | open_datetime, assigned_datetime, completion_datetime |
| **Fault** | fault_code, fault_description, root_cause_category |
| **Repair** | diagnosis_notes, repair_summary, spare_parts_used (child table) |
| **Checklist** | repair_checklist (child table — post-repair verification) |
| **Firmware** | firmware_updated, firmware_change_request (Link → IMM Firmware Change Request) |
| **Sign-off** | dept_head_name, dept_head_confirmation_datetime |
| **Finance** | total_parts_cost, labor_cost, warranty_claim_ref |

**Workflow states:** `Draft → Open → Assigned → Diagnosing → Pending Parts → In Repair → Pending Inspection → Completed / Cannot Repair / Cancelled`

**On Submit (Completed):**
- Tính `mttr_hours` theo công thức working hours (Mon–Fri 07:00–17:00)
- Kiểm tra SLA breach → ghi log
- Cập nhật `Asset.status = Active`
- Nếu firmware updated → tạo `IMM Firmware Change Request`
- Nếu asset là measuring device → trigger `IMM Calibration Schedule`
- Ghi `IMM Audit Trail`

**Child DocTypes:**
- `IMM Spare Parts Used` (parts consumed + cost)
- `IMM Repair Checklist` (post-repair inspection items)

---

#### O-06: `IMM Firmware Change Request` _(chưa có — IMM-09)_
> Theo dõi cập nhật firmware trong quá trình sửa chữa.

| Field | Mô tả |
|---|---|
| `fcr_number` | Autoname: `FCR-.YYYY.-.#####` |
| `asset` | Thiết bị |
| `asset_repair_wo` | Link → IMM CM Work Order |
| `version_before` | Firmware version trước |
| `version_after` | Firmware version sau |
| `change_notes` | Ghi chú thay đổi |
| `source_reference` | Security bulletin / vendor advisory |
| `status` | Draft/Pending Approval/Approved/Applied/Rollback Required/Rolled Back |
| `approved_by` | Link → User |
| `rollback_reason` | Text |

---

#### O-07: `IMM Calibration Schedule` _(chưa có — IMM-11)_
> Lịch hiệu chuẩn định kỳ. Tương tự PM Schedule nhưng cho calibration.

| Field | Kiểu | Mô tả |
|---|---|---|
| `schedule_name` | Autoname: `CAL-SCH-.YYYY.-.#####` | |
| `asset` | Link → Asset | |
| `device_model` | Link → IMM Device Model | |
| `calibration_type` | Select: External/In-House | Track A hoặc B |
| `calibration_interval_days` | Int | Chu kỳ (ngày) |
| `alert_days_before` | Int (default: 30) | |
| `accredited_lab` | Link → IMM Vendor Profile | Cho External track |
| `reference_standard_asset` | Link → Asset | Cho In-House track |
| `status` | Select: Active/Paused/Suspended | |
| `first_calibration_date` | Date | = commissioning_date + interval |
| `last_calibration_date` | Date | |
| `next_due_date` | Date | = cert_date + interval (BR-11-04) |
| `created_from_commissioning` | Link → IMM Commissioning Record | |

---

#### O-08: `IMM Asset Calibration` _(chưa có — IMM-11)_
> Record từng lần hiệu chuẩn. Submittable, immutable sau submit.

| Field nhóm | Nội dung |
|---|---|
| **Identity** | `CAL-.YYYY.-.#####`, asset, device_model |
| **Schedule** | calibration_schedule, calibration_type (External/In-House) |
| **Track A (External)** | lab_name, lab_accreditation_number (ISO/IEC 17025), certificate_file (bắt buộc), certificate_date, certificate_number |
| **Track B (In-House)** | reference_standard_asset, performed_by (certified tech), in_house_procedure |
| **Measurements** | calibration_measurements (child table) |
| **Result** | overall_result (Pass/Fail/Conditionally Passed), fail_details |
| **Dates** | calibration_date, certificate_date, next_calibration_date (computed: cert_date + interval) |
| **Status** | Scheduled/Sent to Lab/In Progress/Certificate Received/Passed/Failed/Conditionally Passed/Cancelled |

**On Submit (Pass):**
- Cập nhật `Asset.custom_imm_last_calibration_date` và `custom_imm_next_calibration_date`
- Set `Asset.custom_imm_calibration_status = In Tolerance`
- Tạo alert cho next calibration
- Ghi `IMM Audit Trail`

**On Submit (Fail — BR-11-02):**
- Set `Asset.status = Out of Order`
- Set `Asset.custom_imm_calibration_status = Out of Tolerance`
- Auto-tạo `IMM CAPA Record` (bắt buộc)
- Thực hiện `perform_lookback_assessment()` (BR-11-03)

**Child DocTypes:**
- `IMM Calibration Measurement` (kết quả từng tham số)

---

#### O-09: `IMM Calibration Measurement` _(Child table — IMM-11)_

| Field | Mô tả |
|---|---|
| `parameter_name` | Tên tham số đo |
| `unit` | Đơn vị |
| `nominal_value` | Giá trị danh nghĩa |
| `measured_value` | Giá trị đo được |
| `tolerance_lower` / `tolerance_upper` | Ngưỡng chấp nhận |
| `result` | Pass/Fail/N/A |
| `uncertainty` | Độ không chắc chắn (U95) |

---

#### O-10: `IMM Incident Report` _(chưa có — IMM-12)_
> Báo cáo sự cố thiết bị. Trigger từ clinical staff khi thiết bị hỏng.

| Field nhóm | Nội dung |
|---|---|
| **Identity** | `IR-.YYYY.-.#####`, asset, device_model, serial_no |
| **Reporter** | reported_by, reporting_dept, report_datetime |
| **Incident** | incident_type (Equipment Failure/Adverse Event/Near Miss/Performance Degradation), incident_description |
| **Severity** | severity (P1/P2/P3/P4), risk_class |
| **Patient Safety** | patient_involved (Check), patient_impact |
| **SLA** | sla_policy, sla_target_hours, response_deadline, resolution_deadline |
| **Assignment** | triaged_by, assigned_to, assignment_datetime |
| **CM WO** | cm_work_order (Link → IMM CM Work Order) — tạo sau triage |
| **Status** | Reported/Triaged/Assigned/In Progress/Resolved/Closed/Escalated |
| **Escalation** | escalation_level, escalated_to, escalation_reason |
| **Closure** | resolution_summary, closed_by, closed_datetime |
| **Adverse Event** | is_adverse_event, adverse_event_ref (báo cáo BYT nếu có) |

**On Submit:**
- Tính `response_deadline = report_datetime + sla.response_time_minutes`
- Tính `resolution_deadline = report_datetime + sla.resolution_time_hours`
- Ghi `IMM Audit Trail`

**Scheduler:**
- Mỗi 30 phút: `check_sla_breaches()` — alert khi sắp breach
- Daily 02:00: `detect_chronic_failures()` — ≥3 incidents cùng fault_code trên 1 asset trong 90 ngày → auto tạo `IMM RCA Record`

---

#### O-11: `IMM SLA Compliance Log` _(IMM-12 — immutable)_
> Ghi log tuân thủ SLA. Insert-only, không sửa không xóa.

| Field | Mô tả |
|---|---|
| `incident_report` | Link → IMM Incident Report |
| `asset` | |
| `priority` | P1/P2/P3/P4 |
| `sla_target_hours` | |
| `actual_hours` | |
| `sla_met` | Check |
| `breach_minutes` | Số phút vi phạm (nếu có) |
| `log_datetime` | Datetime |

---

#### O-12: `IMM RCA Record` _(chưa có — IMM-12)_
> Root Cause Analysis cho sự cố mãn tính hoặc P1.

| Field | Mô tả |
|---|---|
| `rca_number` | Autoname: `RCA-.YYYY.-.#####` |
| `asset` | Thiết bị |
| `trigger_incidents` | Table: link các Incident Reports liên quan |
| `trigger_type` | Select: Chronic Failure/P1 Escalation/Manual |
| `rca_method` | Select: 5-Why/Fishbone/FMEA/Other |
| `problem_statement` | Text |
| `root_cause` | Text |
| `contributing_factors` | Text |
| `corrective_actions` | Table: action + owner + deadline |
| `assigned_to` | Link → User |
| `status` | Open/In Progress/Pending Review/Closed |
| `linked_capa` | Link → IMM CAPA Record |

---

#### O-13: `IMM Spare Parts Inventory` _(chưa có — IMM-15)_
> Tồn kho phụ tùng thiết bị y tế. Wave 2 nhưng cần thiết cho CM WO.

| Field | Mô tả |
|---|---|
| `part_code` | Autoname: `PART-.YYYY.-.#####` |
| `part_name` | Tên phụ tùng |
| `device_model` | Link → IMM Device Model (compatible với model nào) |
| `manufacturer_part_no` | Số part nhà sản xuất |
| `current_qty` | Float |
| `min_qty` | Float (reorder point) |
| `unit_cost` | Currency |
| `location` | Link → Location (kho lưu trữ) |
| `expiry_date` | Date (cho phụ tùng có hạn sử dụng) |
| `last_restocked` | Date |
| `supplier` | Link → Supplier |

---

### 4.5 BLOCK 4 — END-OF-LIFE (IMM-13, IMM-14)

#### E-01: `IMM Asset Transfer` _(chưa có — IMM-13)_
> Điều chuyển thiết bị giữa các khoa/cơ sở.

| Field | Mô tả |
|---|---|
| `transfer_number` | Autoname: `TRF-.YYYY.-.#####` |
| `asset` | Link → Asset |
| `from_location` | Link → Location |
| `to_location` | Link → Location |
| `from_dept` | Link → Department |
| `to_dept` | Link → Department |
| `transfer_reason` | Select: Redeployment/Loan/Permanent Transfer |
| `transfer_date` | Date |
| `approval_status` | Draft/Approved/Completed/Cancelled |
| `approved_by` | Link → User |
| `asset_movement_ref` | Link → Asset Movement (ERPNext) |
| `condition_at_transfer` | Select: Good/Fair/Poor |
| `condition_notes` | Text |

---

#### E-02: `IMM Asset Disposal` _(chưa có — IMM-14)_
> Thanh lý / loại bỏ thiết bị.

| Field | Mô tả |
|---|---|
| `disposal_number` | Autoname: `DSP-.YYYY.-.#####` |
| `asset` | Link → Asset |
| `disposal_reason` | Select: End of Life/Beyond Economic Repair/Obsolete/Safety Hazard/Theft/Donation |
| `disposal_method` | Select: Scrap/Sell/Donate/Return to Vendor |
| `disposal_date` | Date |
| `book_value_at_disposal` | Currency |
| `disposal_value` | Currency |
| `approved_by` | Link → User (BGĐ) |
| `disposal_certificate` | Attach |
| `radiation_disposal_required` | Check |
| `environmental_clearance` | Attach |
| `historical_archive_created` | Check |

---

### 4.6 QMS LAYER — 4 DocTypes

#### Q-01: `IMM Change Control` _(chưa có)_
> Kiểm soát thay đổi quy trình/cấu hình/chính sách.

| Field | Mô tả |
|---|---|
| `change_number` | Autoname: `CHG-.YYYY.-.#####` |
| `change_type` | Select: Process/Configuration/Policy/Software |
| `description` | Mô tả thay đổi |
| `impact_assessment` | Text |
| `risk_level` | Select: Low/Medium/High |
| `approved_by` | Link → User |
| `effective_date` | Date |
| `rollback_plan` | Text |
| `status` | Draft/Pending/Approved/Implemented/Closed |

---

#### Q-02: `IMM Performance KPI` _(chưa có)_
> Dashboard KPI per module. Computed daily by scheduler.

| Field | Mô tả |
|---|---|
| `kpi_date` | Date |
| `module` | Select: IMM-04/05/08/09/11/12 |
| `kpi_name` | Data |
| `kpi_value` | Float |
| `kpi_target` | Float |
| `kpi_unit` | Select: %/Hours/Count |
| `is_below_target` | Check |
| `period_type` | Select: Daily/Weekly/Monthly |

---

## 5. Custom Fields thêm vào ERPNext `Asset`

Theo RULE-F03 — không tạo DocType mới cho Asset, chỉ thêm Custom Fields:

```python
# Nhóm: IMM Medical Device Classification
custom_imm_device_model          Link → IMM Device Model
custom_imm_medical_class         Select: Class I / Class II / Class III
custom_imm_risk_class            Select: Low / Medium / High / Critical
custom_imm_byt_registration_no   Data   # Số đăng ký BYT
custom_imm_manufacturer_serial   Data   # S/N nhà sản xuất
custom_imm_udi_code              Data   # Unique Device Identifier

# Nhóm: IMM Operational Status
custom_imm_lifecycle_status      Select: Active / Inactive / Under Repair / Calibrating / Out of Service / Decommissioned
custom_imm_calibration_status    Select: In Tolerance / Out of Tolerance / Not Required / Overdue
custom_imm_department            Link → Department

# Nhóm: IMM Maintenance Dates
custom_imm_last_pm_date          Date   # Cập nhật khi PM WO submit
custom_imm_next_pm_date          Date
custom_imm_last_calibration_date Date   # Cập nhật khi Cal submit
custom_imm_next_calibration_date Date

# Nhóm: IMM Accountability
custom_imm_responsible_tech      Link → User   # KTV phụ trách chính
custom_imm_commissioning_ref     Link → IMM Commissioning Record
custom_imm_gmdn_code             Data
custom_imm_emdn_code             Data
```

**Tổng: 16 Custom Fields thêm vào ERPNext Asset.**

---

## 6. Summary: Tổng hợp 42 DocType AssetCore

| # | DocType | Module | Loại | Trạng thái |
|---|---|---|---|---|
| **MASTER DATA** | | | | |
| 1 | IMM Device Model | Master | Standard | ❌ Chưa có |
| 2 | IMM Vendor Profile | Master | Standard | ❌ Chưa có |
| 3 | IMM Location Ext | Master | Standard | ❌ Chưa có |
| 4 | IMM SLA Policy | Master | Standard | ❌ Chưa có |
| 5 | IMM Audit Trail | Master | Standard (append-only) | ❌ Chưa có |
| 6 | IMM CAPA Record | Master/QMS | Submittable | ❌ Chưa có |
| **DEPLOYMENT — IMM-04** | | | | |
| 7 | IMM Commissioning Record | IMM-04 | Submittable | ✅ Implement (Asset Commissioning) |
| 8 | IMM Commissioning Checklist | IMM-04 | Child Table | ✅ Implement |
| 9 | IMM Commissioning Document | IMM-04 | Child Table | ✅ Implement |
| 10 | IMM Asset Lifecycle Event | IMM-04 | Child Table | ✅ Implement |
| 11 | IMM Asset QA Non-Conformance | IMM-04 | Submittable | ✅ Implement |
| **DEPLOYMENT — IMM-05** | | | | |
| 12 | IMM Asset Document | IMM-05 | Standard (workflow) | ✅ Implement |
| 13 | IMM Document Request | IMM-05 | Standard | ✅ Implement |
| 14 | IMM Required Document Type | IMM-05 | Fixture | ✅ Implement |
| 15 | IMM Expiry Alert Log | IMM-05 | Standard (append-only) | ✅ Implement |
| **DEPLOYMENT — IMM-06** | | | | |
| 16 | IMM Training Record | IMM-06 | Submittable | ❌ Wave 2 |
| **OPERATIONS — IMM-08** | | | | |
| 17 | IMM PM Schedule | IMM-08 | Standard | ❌ Chưa có |
| 18 | IMM PM Checklist Template | IMM-08 | Standard | ❌ Chưa có |
| 19 | IMM PM Checklist Item | IMM-08 | Child Table | ❌ Chưa có |
| 20 | IMM PM Work Order | IMM-08 | Submittable | ❌ Chưa có |
| 21 | IMM PM Checklist Result | IMM-08 | Child Table | ❌ Chưa có |
| 22 | IMM PM Task Log | IMM-08 | Standard (append-only) | ❌ Chưa có |
| **OPERATIONS — IMM-09** | | | | |
| 23 | IMM CM Work Order | IMM-09 | Submittable | ❌ Chưa có |
| 24 | IMM Spare Parts Used | IMM-09 | Child Table | ❌ Chưa có |
| 25 | IMM Repair Checklist | IMM-09 | Child Table | ❌ Chưa có |
| 26 | IMM Firmware Change Request | IMM-09 | Submittable | ❌ Chưa có |
| **OPERATIONS — IMM-11** | | | | |
| 27 | IMM Calibration Schedule | IMM-11 | Standard | ❌ Chưa có |
| 28 | IMM Asset Calibration | IMM-11 | Submittable | ❌ Chưa có |
| 29 | IMM Calibration Measurement | IMM-11 | Child Table | ❌ Chưa có |
| **OPERATIONS — IMM-12** | | | | |
| 30 | IMM Incident Report | IMM-12 | Submittable | ❌ Chưa có |
| 31 | IMM SLA Compliance Log | IMM-12 | Standard (append-only) | ❌ Chưa có |
| 32 | IMM RCA Record | IMM-12 | Submittable | ❌ Chưa có |
| **OPERATIONS — IMM-15** | | | | |
| 33 | IMM Spare Parts Inventory | IMM-15 | Standard | ❌ Wave 2 |
| **END-OF-LIFE — IMM-13** | | | | |
| 34 | IMM Asset Transfer | IMM-13 | Submittable | ❌ Wave 3 |
| **END-OF-LIFE — IMM-14** | | | | |
| 35 | IMM Asset Disposal | IMM-14 | Submittable | ❌ Wave 3 |
| **QMS LAYER** | | | | |
| 36 | IMM Change Control | QMS | Submittable | ❌ Wave 2 |
| 37 | IMM Performance KPI | QMS | Standard | ❌ Wave 2 |
| **ERPNext Custom Fields** | | | | |
| — | Asset (16 custom fields) | Cross-module | Custom Fields | ⚠️ Định nghĩa, chưa migrate |

### Thống kê theo trạng thái

| Trạng thái | Số DocType |
|---|---|
| ✅ Đã implement | 9 |
| ❌ Wave 1 (cần làm ngay) | 16 |
| ❌ Wave 2 | 7 |
| ❌ Wave 3 | 5 |
| **Tổng** | **37** |

---

## 7. Relationship Map — Toàn bộ hệ thống

```
                    ┌─────────────────────────────────────────┐
                    │        IMM Device Model (M-01)          │
                    │  gmdn, class, pm_interval, cal_interval │
                    └──────────────────┬──────────────────────┘
                                       │ 1:N
                    ┌──────────────────▼──────────────────────┐
                    │        ERPNext Asset (Registry)          │
                    │  + 16 Custom Fields (IMM extensions)     │
                    └──┬──────┬──────┬──────┬──────┬──────────┘
                       │      │      │      │      │
             ┌─────────▼──┐   │   ┌──▼───┐  │  ┌──▼──────────┐
             │ IMM-04      │   │   │IMM-05│  │  │  IMM-11     │
             │ Commission  │   │   │ Doc  │  │  │ Cal Schedule│
             │ Record      │   │   │ Mgmt │  │  │ Cal Record  │
             └──────┬──────┘   │   └──────┘  │  └──────┬──────┘
                    │          │              │         │ fail
                    │ on_submit│              │         ▼
                    │ Clinical │              │  ┌─────────────┐
                    │ Release  │              │  │ IMM CAPA    │
                    ├──────────┼──────────────┤  │ Record      │
                    ▼          ▼              │  └─────────────┘
             ┌──────────┐ ┌──────────┐       │
             │ IMM-08   │ │  IMM-11  │       │
             │ PM       │ │ Cal      │       │
             │ Schedule │ │ Schedule │       │
             └────┬─────┘ └──────────┘       │
                  │                           │
                  ▼                           │
             ┌──────────┐                    │
             │ IMM-08   │ fail               │
             │ PM Work  ├──────────┐         │
             │ Order    │          │         │
             └────┬─────┘          │         │
                  │ complete       │         │
                  ▼                ▼         │
             ┌──────────┐   ┌──────────┐    │
             │ IMM-08   │   │ IMM-09   │    │
             │ PM Task  │   │ CM Work  ├────┘
             │ Log      │   │ Order    │
             └──────────┘   └────┬─────┘
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
             ┌──────────┐ ┌──────────┐ ┌──────────┐
             │ Spare    │ │ Repair   │ │ Firmware │
             │ Parts    │ │ Check-   │ │ Change   │
             │ Used     │ │ list     │ │ Request  │
             └──────────┘ └──────────┘ └──────────┘

             ┌──────────────────────────────────────┐
             │           IMM-12 (Incidents)          │
             │  Incident Report → SLA Log → RCA      │
             │  Chronic (≥3/90d) → auto RCA          │
             │  P1/P2 → auto CAPA                    │
             └──────────────────────────────────────┘

             ┌──────────────────────────────────────┐
             │        IMM Audit Trail (append-only)  │
             │  Receives events from ALL modules     │
             └──────────────────────────────────────┘
```

---

## 8. Nguyên tắc xây dựng bắt buộc

### 8.1 ERPNext Integration Rules

```
RULE-I01: Mọi IMM DocType phải có field `asset` (Link → Asset) — trừ Master Data
RULE-I02: KHÔNG tạo DocType mới cho Asset — dùng Custom Fields
RULE-I03: KHÔNG sửa bất kỳ ERPNext core DocType
RULE-I04: Dùng `frappe.get_doc("Asset", name)` để đọc/ghi, không SQL trực tiếp
RULE-I05: Mọi thay đổi `Asset.status` phải đi qua IMM API, không hardcode
```

### 8.2 Data Integrity Rules

```
RULE-D01: Audit Trail là append-only — không có update/delete endpoint
RULE-D02: PM Task Log là append-only sau submit
RULE-D03: SLA Compliance Log là append-only
RULE-D04: Calibration Record là immutable sau submit (chỉ Amend với lý do)
RULE-D05: Naming series bắt buộc cho mọi transaction DocType
RULE-D06: Mọi state transition phải ghi IMM Audit Trail
```

### 8.3 Business Logic Rules

```
RULE-B01: Không có action nào ngoài Work Order (PM WO / CM WO / Cal Record)
RULE-B02: next_pm_date = completion_date + interval (KHÔNG phải due_date)
RULE-B03: next_cal_date = cert_date + interval (KHÔNG phải due_date)
RULE-B04: MTTR tính bằng working hours (Mon-Fri 07:00-17:00)
RULE-B05: Calibration Fail → mandatory CAPA + lookback cùng device_model
RULE-B06: Chronic failure (≥3/90 ngày) → auto tạo RCA
RULE-B07: Asset OOS → không tạo PM WO mới
RULE-B08: Class III → bắt buộc photo trước/sau PM
```

---

## 9. Thứ tự implement Wave 1

Dựa trên dependency chain:

```
1. IMM Device Model          ← Master data, mọi thứ link vào đây
2. IMM Vendor Profile         ← Cần cho Calibration Schedule
3. IMM SLA Policy             ← Cần cho CM WO và Incident Report
4. IMM Audit Trail            ← Cần sớm để mọi module ghi vào
5. Custom Fields → Asset      ← bench migrate

6. IMM PM Schedule            ← IMM-08, phụ thuộc Device Model
7. IMM PM Checklist Template  ← IMM-08, phụ thuộc Asset Category
8. IMM PM Checklist Item      ← Child table của Template
9. IMM PM Work Order          ← IMM-08, phụ thuộc Schedule + Template
10. IMM PM Checklist Result   ← Child table của PM WO
11. IMM PM Task Log           ← IMM-08 append-only

12. IMM CM Work Order         ← IMM-09, phụ thuộc Asset + SLA Policy
13. IMM Spare Parts Used      ← Child table CM WO
14. IMM Repair Checklist      ← Child table CM WO
15. IMM Firmware Change Req   ← IMM-09, standalone

16. IMM Calibration Schedule  ← IMM-11, phụ thuộc Device Model
17. IMM Asset Calibration     ← IMM-11, phụ thuộc Schedule
18. IMM Calibration Measurement ← Child table Cal Record
19. IMM CAPA Record           ← IMM-11/12, phụ thuộc Cal Record

20. IMM Incident Report       ← IMM-12, phụ thuộc SLA Policy
21. IMM SLA Compliance Log    ← Append-only, linked to Incident
22. IMM RCA Record            ← IMM-12, phụ thuộc Incident Report

→ Fix IMM-04 integration triggers:
   approve_clinical_release() → tạo PM Schedule + Calibration Schedule
```

**Tổng: 22 DocType cần tạo trong Wave 1 + fix 1 integration trong IMM-04.**
