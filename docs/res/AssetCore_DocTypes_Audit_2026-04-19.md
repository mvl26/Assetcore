# AssetCore — DocType Audit (Giai đoạn hiện tại)

**Ngày rà soát:** 2026-04-19
**Phạm vi:** Toàn bộ DocType đã build trong app `assetcore`
**Module:** AssetCore (Frappe-only, không phụ thuộc ERPNext)

---

## 1. Tổng quan

| Chỉ số | Số lượng |
|---|---|
| Tổng DocType đã build | **34** |
| Submittable (có workflow duyệt) | 11 |
| Child table (`istable`) | 9 |
| Tree (`is_tree`) | 2 |
| Master / setup | 9 |
| Operational / transactional | 14 |

**Phân bố theo module:**

| Module | Phạm vi | DocType |
|---|---|---|
| IMM-00 Foundation | Master + governance | 17 |
| IMM-04 Commissioning | Lắp đặt & nghiệm thu | 5 |
| IMM-05 Documents | Hồ sơ tài liệu | 3 |
| IMM-08 Preventive Maintenance | Bảo trì định kỳ | 6 |
| IMM-09 Corrective Maintenance | Sửa chữa | 3 |

---

## 2. IMM-00 — Foundation (17 DocType)

Lớp nền tảng cho toàn bộ hệ thống: danh mục thiết bị, tổ chức, quản trị rủi ro, audit trail, CAPA, sự cố, chuyển giao, hợp đồng dịch vụ.

### 2.1 Master Data

#### **AC Asset** · submittable · naming `AC-ASSET-.YYYY.-.#####`
- **Mục đích:** Bản ghi chính thiết bị y tế — quản lý vòng đời HTM (commissioning, PM, calibration, insurance).
- **Field trọng yếu:**
  - `asset_name` (Data, reqd), `asset_code` (Data, unique)
  - `asset_category` → AC Asset Category (reqd)
  - `device_model` → IMM Device Model
  - `lifecycle_status` (Select, reqd): Commissioned / Active / Under Repair / Calibrating / Out of Service / Decommissioned
  - `location` → AC Location, `department` → AC Department, `custodian` → User, `responsible_technician` → User
  - `supplier` → AC Supplier, `manufacturer_sn`, `udi_code`, `gmdn_code`
  - `byt_reg_no`, `byt_reg_expiry` (NĐ98)
  - `is_pm_required`, `pm_interval_days`, `next_pm_date`
  - `is_calibration_required`, `calibration_interval_days`, `next_calibration_date`
  - **Bảo hiểm:** `insurance_policy_no`, `insurer_name`, `insured_value`, `insurance_start_date`, `insurance_end_date`
- **Business rule:**
  - BR-00-02: `lifecycle_status` immutable khi edit trực tiếp — chỉ đổi qua `transition_asset_status()`
  - VR-00-04/05: `purchase_date` không ở tương lai; `warranty_expiry_date` ≥ `purchase_date`
  - Auto-compute `next_pm_date`, `next_calibration_date` từ last + interval
- **Roles:** IMM System Admin, IMM Department Head, IMM Operations Manager, IMM Workshop Lead, IMM Technician, IMM Document Officer, IMM QA Officer

#### **AC Asset Category** · master · naming `field:category_name`
- **Mục đích:** Phân loại thiết bị với default PM/calibration interval.
- **Field trọng yếu:** `category_name` (reqd, unique), `default_pm_required`, `default_pm_interval_days`, `default_calibration_required`, `default_calibration_interval_days`, `has_radiation`, `is_active`
- **Business rule:** VR-00-16: `default_pm_interval_days > 0` khi `default_pm_required=1`

#### **AC Location** · master · tree · naming `AC-LOC-.YYYY.-.####`
- **Mục đích:** Vị trí vật lý cấp bậc (ICU, OR, Lab, Imaging, Ward, Storage, Office).
- **Field trọng yếu:** `location_name` (reqd), `location_code` (unique), `parent_location` → AC Location, `clinical_area_type` (Select), `infection_control_level`, `power_backup_available`, `is_active`

#### **AC Department** · master · tree · naming `AC-DEPT-.####`
- **Mục đích:** Cơ cấu tổ chức phòng ban cấp bậc.
- **Field trọng yếu:** `department_name` (reqd), `department_code` (unique), `parent_department` → AC Department, `is_group`, `dept_head` → User, `is_active`

#### **AC Supplier** · submittable · naming `AC-SUP-.YYYY.-.####`
- **Mục đích:** Nhà cung cấp (manufacturer / distributor / calibration lab / service provider) với chứng chỉ ISO 17025 / 13485 và danh sách kỹ thuật viên được ủy quyền.
- **Field trọng yếu:** `supplier_name` (reqd), `supplier_group` (Select, reqd), `vendor_type` (Select, reqd), `country`, `contact_email`, `iso_17025_cert`, `iso_13485_cert`, `contract_expiry_date`, `contract_end`, `authorized_technicians` → Table(AC Authorized Technician), `is_active`

#### **AC Authorized Technician** · child table của AC Supplier
- **Field:** `tech_name` (reqd), `certification_no`, `valid_until` (Date), `phone`, `email`, `authorized_for_models`

#### **IMM Device Model** · master · naming `IMM-MDL-.YYYY.-.####`
- **Mục đích:** Model thiết bị chuẩn với phân loại y tế (Class I/II/III), GMDN, default PM/calibration.
- **Field trọng yếu:** `model_name` (reqd), `manufacturer` (reqd), `asset_category` → AC Asset Category (reqd), `medical_device_class` (Select: Class I/II/III, reqd), `risk_classification`, `is_radiation_device`, `gmdn_code`, `is_pm_required`, `pm_interval_days`, `is_calibration_required`, `calibration_interval_days`, `spare_parts_list` → Table(IMM Device Spare Part)
- **Business rule:** BR-00-01: Class III → `risk_classification=High/Critical` tự động

#### **IMM Device Spare Part** · child table của IMM Device Model
- **Field:** `part_name` (reqd), `manufacturer_part_no`, `estimated_cost`, `recommended_stock_level`, `notes`

#### **IMM SLA Policy** · master · naming `field:policy_name`
- **Mục đích:** Ma trận SLA theo priority × risk_class với response/resolution time + escalation.
- **Field trọng yếu:** `policy_name` (reqd, unique), `priority` (Select: P1 Critical/P1 High/P2/P3/P4, reqd), `risk_class`, `response_time_minutes` (reqd), `resolution_time_hours` (reqd), `working_hours_only`, `escalation_l1_role` → Role, `escalation_l2_role` → Role, `is_default`, `is_active`
- **Business rule:** BR-00-05: Duy nhất 1 policy active cho mỗi (priority, risk_class)

### 2.2 Governance & Audit

#### **IMM Audit Trail** · log · naming `IMM-AUD-.YYYY.-.#######`
- **Mục đích:** Nhật ký append-only với SHA-256 hash chain cho mọi sự kiện quan trọng (ISO 13485, NĐ98).
- **Field trọng yếu:** `asset` → AC Asset (reqd), `event_type` (Select: **State Change / CAPA / Maintenance / Calibration / Document / Incident / Audit / System / Transfer**, reqd), `timestamp` (reqd), `actor` → User (reqd), `change_summary`, `from_status`, `to_status`, `ref_doctype` + `ref_name` (Dynamic Link), `hash_sha256` (read_only, 64 ký tự), `prev_hash` (read_only, 64 ký tự)
- **Business rule:** BR-00-04: Tamper detection qua hash chain; không cho phép update/delete

#### **Asset Lifecycle Event** · log · naming `ALE-.YYYY.-.#######`
- **Mục đích:** Nhật ký chuyển trạng thái thiết bị theo vòng đời WHO HTM.
- **Field trọng yếu:** `asset` → AC Asset (reqd), `event_type` (Select: commissioned / activated / pm_started / pm_completed / repair_opened / repair_completed / calibration_started / calibration_passed / calibration_failed / incident_reported / out_of_service / restored / decommissioned / **transferred** / registered, reqd), `timestamp`, `actor` → User, `from_status`, `to_status`, `root_doctype`, `root_record`, `notes`

#### **IMM CAPA Record** · submittable · naming `CAPA-.YYYY.-.#####`
- **Mục đích:** Corrective/Preventive Action — xử lý sự cố/không phù hợp theo ISO 13485.
- **Field trọng yếu:**
  - `asset` → AC Asset (reqd), `severity` (Select: Minor/Major/Critical, reqd)
  - `status` (Select: Open / In Progress / Pending Verification / Closed / Overdue, reqd)
  - `source_type` (Select: **Incident Report** / Non-Conformance / Complaint / PM Finding / Calibration Finding, reqd), `source_ref` (Dynamic Link theo `source_type`)
  - `description` (reqd), `root_cause`, `corrective_action`, `preventive_action`, `effectiveness_check`
  - `responsible` → User (reqd), `due_date` (reqd), `closed_date`, `linked_incident` → Incident Report
- **Business rule:**
  - BR-00-06: Không submit khi thiếu root_cause + corrective_action + preventive_action
  - BR-00-08: Critical Incident tự sinh CAPA khi `on_submit` (auto-link via `source_ref`)

### 2.3 Operational — Events

#### **Incident Report** · submittable · naming `IR-.YYYY.-.####`
- **Mục đích:** Ghi nhận sự cố thiết bị (failure / safety event / malfunction) với đánh giá ảnh hưởng bệnh nhân + báo cáo BYT.
- **Field trọng yếu:** `asset` → AC Asset (reqd), `incident_type` (Select: Failure/Safety Event/Near Miss/Malfunction, reqd), `severity` (Select: Low/Medium/High/Critical, reqd), `status` (Select), `reported_by` → User (reqd), `reported_at` (reqd), `description` (Text Editor, reqd), `patient_affected`, `patient_impact_description` (reqd khi patient_affected=1), `reported_to_byt`, `linked_capa` → IMM CAPA Record
- **Business rule:**
  - BR-INC-01: severity=Critical → yêu cầu reported_to_byt (NĐ98)
  - BR-INC-02: patient_affected=1 → patient_impact_description bắt buộc
  - BR-00-08: on_submit + Critical → tự tạo CAPA (verified in UAT 2026-04-18)

#### **Asset Transfer** · submittable · naming `AT-.YYYY.-.####`
- **Mục đích:** Chuyển giao thiết bị giữa location/department/custodian (Internal/Loan/External/Return).
- **Field trọng yếu:** `asset` → AC Asset (reqd), `transfer_date` (reqd), `transfer_type` (Select, reqd), `from_location/from_department/from_custodian` (read_only, tự capture khi submit), `to_location` → AC Location (reqd), `to_department`, `to_custodian` → User, `reason` (reqd), `approved_by` → User, `expected_return_date` (reqd khi `transfer_type=Loan`)
- **Business rule:**
  - on_submit → cập nhật AC Asset (location/dept/custodian) + tạo Asset Lifecycle Event ("transferred") + IMM Audit Trail (event_type="Transfer")
  - Delete: Draft → xóa hẳn; Submitted → chỉ cancel (giữ audit theo BR-00-04)

#### **Service Contract** · submittable · naming `SC-.YYYY.-.####`
- **Mục đích:** Hợp đồng dịch vụ với NCC (PM / Calibration / Repair / Full Service / Warranty Extension) — phủ nhiều thiết bị qua child table.
- **Field trọng yếu:** `contract_title` (reqd), `supplier` → AC Supplier (reqd), `contract_type` (Select, reqd), `contract_start` (reqd), `contract_end` (reqd), `contract_value` (Currency), `auto_renew`, `sla_response_hours`, `coverage_description`, `covered_assets` → Table(Service Contract Asset)
- **Business rule:** `contract_end > contract_start`; không sửa sau khi submit

#### **Service Contract Asset** · child table của Service Contract
- **Field:** `asset` → AC Asset (reqd), `asset_name` (fetch_from: asset.asset_name, read_only), `coverage_note`

#### **Expiry Alert Log** · log · naming `EAL-{YYYY}-{MM}-{#####}`
- **Mục đích:** Log cảnh báo hết hạn tài liệu thiết bị (Info/Warning/Critical/Danger).
- **Field trọng yếu:** `asset_document` → Asset Document (reqd, read_only), `asset_ref` → AC Asset (reqd, read_only), `expiry_date`, `days_remaining`, `alert_level` (Select: Info/Warning/Critical/Danger, read_only), `alert_date`, `notified_users`

---

## 3. IMM-04 — Commissioning (5 DocType)

Quy trình nghiệm thu lắp đặt thiết bị mới từ PO → handover.

#### **Asset Commissioning** · submittable · naming `IMM04-.YY.-.MM.-.#####`
- **Mục đích:** Workflow lắp đặt thiết bị: PO → reception → facility check → baseline test → document handover → tạo AC Asset.
- **Field trọng yếu:** `po_reference` (reqd), `master_item` → IMM Device Model (reqd), `vendor` → AC Supplier (reqd), `clinical_dept` → AC Department (reqd), `expected_installation_date` (reqd), `vendor_serial_no` (reqd), `installation_location` → AC Location, `facility_checklist_pass`, `baseline_tests` → Table(Commissioning Checklist, reqd), `commissioning_documents` → Table(Commissioning Document Record), `final_asset` → AC Asset (read_only, tạo khi submit)

#### **Commissioning Checklist** · child table
- **Field:** `parameter` (reqd), `is_critical`, `measurement_type` (Numeric/Pass Fail/Visual), `measured_val`, `expected_min/max`, `unit`, `test_result` (Pass/Fail/N/A), `fail_note` (reqd khi Fail)

#### **Commissioning Document Record** · child table
- **Field:** `doc_type` (CO/CQ/Packing List/Manual/Warranty/Training/Other), `doc_number`, `is_mandatory`, `status` (Pending/Received/Missing/Rejected/Waived), `received_date`, `expiry_date`, `file_url`

#### **Asset QA Non-Conformance** · submittable · naming `NC-.YY.-.MM.-.#####`
- **Mục đích:** Ghi nhận vấn đề chất lượng khi commissioning (DOA/Missing/Crash) với phạt NCC.
- **Field trọng yếu:** `ref_commissioning` → Asset Commissioning (reqd), `nc_type` (Select, reqd), `severity` (Minor/Major/Critical), `resolution_status` (Open/Under Review/Resolved/Closed/Transferred, reqd), `description` (reqd), `root_cause`, `damage_proof` (Attach Image, reqd khi DOA), `penalty_amount` (Currency, permlevel 1)

#### **Firmware Change Request** · submittable · naming `FCR-.YYYY.-.#####`
- **Mục đích:** Quản lý cập nhật firmware/software với rollback capability.
- **Field trọng yếu:** `asset_ref` → AC Asset (reqd), `asset_repair_wo` → Asset Repair, `version_before` (reqd), `version_after` (reqd), `change_notes` (Text, reqd), `status` (Draft/Pending Approval/Approved/Applied/Rollback Required/Rolled Back), `approved_by` → User, `applied_datetime` (read_only)

---

## 4. IMM-05 — Documents (3 DocType)

Kho hồ sơ tài liệu thiết bị với version control & document request workflow.

#### **Asset Document** · naming `DOC-{asset_ref}-{YYYY}-{#####}`
- **Mục đích:** Kho tài liệu thiết bị (Legal/Technical/Certification/Training/QA) với version control + expiry tracking.
- **Field trọng yếu:** `asset_ref` → AC Asset (reqd), `doc_category` (Select, reqd), `doc_type_detail` (reqd), `doc_number` (reqd), `version` (default 1.0), `issued_date` (reqd), `expiry_date`, `file_attachment` (Attach, reqd), `approved_by` → User (read_only), `is_expired` (read_only), `visibility` (Public/Internal_Only), `is_exempt`, `change_summary` (reqd khi version ≠ 1.0), `model_ref` → IMM Device Model, `supersedes` → Asset Document

#### **Document Request** · naming `DOCREQ-{YYYY}-{MM}-{#####}`
- **Mục đích:** Workflow yêu cầu bổ sung tài liệu thiếu với escalation theo due_date.
- **Field trọng yếu:** `asset_ref` → AC Asset (reqd), `doc_type_required` (reqd), `doc_category` (Select, reqd), `status` (Open/In_Progress/Overdue/Fulfilled/Cancelled, reqd), `priority` (Low/Medium/High/Critical), `assigned_to` → User (reqd), `due_date` (reqd), `fulfilled_by` → Asset Document (read_only)

#### **Required Document Type** · master · naming `field:type_name`
- **Mục đích:** Định nghĩa loại tài liệu bắt buộc theo danh mục thiết bị + điều kiện áp dụng.
- **Field trọng yếu:** `type_name` (reqd, unique), `doc_category` (Select, reqd), `has_expiry`, `is_mandatory`, `applies_to_asset_category` → AC Asset Category, `applies_when_radiation`

---

## 5. IMM-08 — Preventive Maintenance (6 DocType)

Lịch bảo trì định kỳ + template checklist + work order.

#### **PM Work Order** · submittable · naming `PM-WO-.YYYY.-.#####`
- **Mục đích:** Lệnh bảo trì định kỳ với SLA monitoring, assigned technician, checklist.
- **Field trọng yếu:** `asset_ref` → AC Asset (reqd), `pm_schedule` → PM Schedule (reqd), `status` (Select: Open/In Progress/Pending-Device Busy/Overdue/Completed/Halted-Major Failure/Cancelled), `due_date` (reqd), `completion_date` (read_only), `assigned_to` → User, `overall_result` (Pass/Pass with Minor Issues/Fail), `checklist_results` → Table(PM Checklist Result), `wo_type` (Preventive/Corrective, default Preventive), `source_pm_wo` → PM Work Order (nếu corrective)

#### **PM Schedule** · master · naming `PMS-{asset_ref}-{pm_type}`
- **Mục đích:** Lịch bảo trì định kỳ cho từng thiết bị với template-driven checklist.
- **Field trọng yếu:** `asset_ref` → AC Asset (reqd), `pm_type` (Quarterly/Semi-Annual/Annual/Ad-hoc, reqd), `status` (Active/Paused/Suspended, default Active), `pm_interval_days` (reqd), `checklist_template` → PM Checklist Template (reqd), `alert_days_before` (default 7), `responsible_technician` → User, `next_due_date`, `created_from_commissioning` → Asset Commissioning

#### **PM Checklist Template** · master · naming `PMCT-{asset_category}-{pm_type}`
- **Mục đích:** Template checklist tái sử dụng theo category + pm_type, có versioning.
- **Field trọng yếu:** `template_name` (reqd), `asset_category` → AC Asset Category (reqd), `pm_type` (Select, reqd), `version` (default 1.0), `effective_date`, `approved_by` → User, `checklist_items` → Table(PM Checklist Item)

#### **PM Checklist Item** · child table
- **Field:** `item_code` (read_only), `description` (reqd), `measurement_type` (Pass/Fail / Numeric / Text, reqd), `unit` (reqd khi Numeric), `expected_min/max`, `is_critical`, `reference_section`

#### **PM Checklist Result** · child table của PM Work Order
- **Field:** `checklist_item_idx`, `description` (read_only), `result` (Pass / Fail–Minor / Fail–Major / N/A, reqd), `measured_value`, `notes` (reqd khi Fail), `photo` (Attach)

#### **PM Task Log** · log
- **Mục đích:** Log hoàn thành PM cho audit & analytics (is_late, days_late, next_pm_date).
- **Field trọng yếu:** `asset_ref` → AC Asset (reqd), `pm_work_order` → PM Work Order (reqd), `completion_date` (reqd), `technician` → User, `overall_result`, `is_late`, `days_late`, `next_pm_date`

---

## 6. IMM-09 — Corrective Maintenance (3 DocType)

Work order sửa chữa khẩn cấp / bảo hành với spare parts + SLA tracking.

#### **Asset Repair** · submittable · naming `WO-CM-.YYYY.-.#####`
- **Mục đích:** Work order sửa chữa (Corrective/Emergency/Warranty) với MTTR + SLA monitoring.
- **Field trọng yếu:**
  - `asset_ref` → AC Asset (reqd)
  - `incident_report` → Incident Report, `source_pm_wo` → PM Work Order
  - `repair_type` (Corrective/Emergency/Warranty Repair, reqd), `priority` (Normal/Urgent/Emergency, reqd)
  - `status` (Open/Assigned/Diagnosing/Pending Parts/In Repair/Pending Inspection/Completed/Cannot Repair/Cancelled)
  - `assigned_to` → User, `diagnosis_notes`, `root_cause_category` (Mechanical/Electrical/Software/User Error/Wear and Tear/Unknown)
  - `spare_parts_used` → Table(Spare Parts Used), `repair_checklist` → Table(Repair Checklist)
  - `sla_target_hours` (read_only), `mttr_hours` (read_only), `sla_breached` (read_only), `completion_datetime`

#### **Repair Checklist** · child table của Asset Repair
- **Field:** `test_description` (reqd), `test_category` (Electrical/Mechanical/Software/Safety/Performance, reqd), `expected_value`, `measured_value`, `result` (Pass/Fail/N/A), `notes`, `photo`

#### **Spare Parts Used** · child table của Asset Repair
- **Field:** `item_code` (reqd), `item_name` (reqd), `manufacturer_part_no`, `qty` (Float, reqd), `uom` (reqd), `unit_cost` (Currency, reqd), `total_cost` (read_only, auto-compute), `stock_entry_ref`, `notes`

---

## 7. Ma trận quan hệ (Entity Relationships)

```
                    ┌─────────────────┐
                    │  AC Asset       │◄──┬─── AC Asset Category (master)
                    │  (core)         │   ├─── IMM Device Model (master)
                    └────┬────────────┘   ├─── AC Location (tree)
                         │                ├─── AC Department (tree)
                         │                └─── AC Supplier
                         │
         ┌───────────────┼───────────────────────────────────┐
         │               │                                   │
         ▼               ▼                                   ▼
   Asset Transfer    PM Work Order ──► PM Schedule     Incident Report
   (submittable)     (submittable)     │                 (submittable)
         │               │              └─► PM Checklist Template │
         │               │                    └─► PM Checklist Item
         │               │                                   │
         ▼               ▼                                   ▼
  Asset Lifecycle    PM Task Log                    IMM CAPA Record
      Event                                           (submittable)
         │                                                 │
         └──────────┬────────────────┬──────────────────────┘
                    ▼                ▼
              IMM Audit Trail   Asset Repair
              (SHA-256 chain)   (submittable)
                                 │
                                 ├─► Repair Checklist
                                 └─► Spare Parts Used

   Asset Commissioning (submittable)
     ├─► Commissioning Checklist (child)
     ├─► Commissioning Document Record (child)
     ├─► Asset QA Non-Conformance
     └─► Firmware Change Request

   Service Contract (submittable)
     └─► Service Contract Asset (child) ──► AC Asset

   Asset Document ──► AC Asset
     └─► Expiry Alert Log
   Document Request ──► Asset Document
   Required Document Type (master)
```

---

## 8. Danh mục Submittable (11)

| DocType | Module | Mục đích submit |
|---|---|---|
| AC Asset | IMM-00 | Công nhận đưa vào vận hành |
| AC Supplier | IMM-00 | Phê duyệt NCC |
| Incident Report | IMM-00 | Ghi nhận chính thức sự cố (→ auto CAPA nếu Critical) |
| IMM CAPA Record | IMM-00 | Đóng CAPA khi đã có root cause + action |
| Asset Transfer | IMM-00 | Xác nhận chuyển giao (→ cập nhật Asset + audit trail) |
| Service Contract | IMM-00 | Kích hoạt hợp đồng |
| Asset Commissioning | IMM-04 | Hoàn tất nghiệm thu → tạo AC Asset |
| Asset QA Non-Conformance | IMM-04 | Xử phạt NCC |
| Firmware Change Request | IMM-04 | Duyệt cập nhật firmware |
| PM Work Order | IMM-08 | Nghiệm thu bảo trì |
| Asset Repair | IMM-09 | Nghiệm thu sửa chữa (ghi MTTR) |

---

## 9. Danh mục Child Table (9)

| DocType | Cha | Vai trò |
|---|---|---|
| AC Authorized Technician | AC Supplier | Danh sách KTV được ủy quyền + chứng chỉ |
| IMM Device Spare Part | IMM Device Model | Danh mục phụ tùng chuẩn theo model |
| Commissioning Checklist | Asset Commissioning | Đo lường an toàn điện & baseline test |
| Commissioning Document Record | Asset Commissioning | Tracking CO/CQ/Manual/Warranty |
| PM Checklist Item | PM Checklist Template | Hạng mục kiểm tra chuẩn |
| PM Checklist Result | PM Work Order | Kết quả đo thực tế per item |
| Service Contract Asset | Service Contract | Thiết bị thuộc phạm vi HĐ |
| Repair Checklist | Asset Repair | Test nghiệm thu sau sửa chữa |
| Spare Parts Used | Asset Repair | Phụ tùng tiêu hao |

---

## 10. Business Rules — Tổng hợp

| Code | Nội dung | DocType | Trạng thái |
|---|---|---|---|
| BR-00-01 | Class III → risk_class=High/Critical tự động | IMM Device Model | ✅ |
| BR-00-02 | `lifecycle_status` immutable khi edit trực tiếp | AC Asset | ✅ UAT pass |
| BR-00-04 | Audit trail SHA-256 chain, không cho xóa submitted | IMM Audit Trail | ✅ UAT pass |
| BR-00-05 | Unique active SLA policy cho mỗi (priority, risk_class) | IMM SLA Policy | ✅ UAT pass |
| BR-00-06 | CAPA yêu cầu root_cause + corrective_action + preventive_action trước submit | IMM CAPA Record | ✅ |
| BR-00-08 | Critical Incident → auto-open CAPA | Incident Report → IMM CAPA Record | ✅ UAT pass (3/3 fire) |
| VR-00-04 | `purchase_date` không ở tương lai | AC Asset | ✅ |
| VR-00-05 | `warranty_expiry_date` ≥ `purchase_date` | AC Asset | ✅ |
| VR-00-16 | `default_pm_interval_days > 0` khi `default_pm_required=1` | AC Asset Category | ✅ |
| BR-INC-01 | Critical severity → reported_to_byt (NĐ98) | Incident Report | ⚠ msgprint only |
| BR-INC-02 | patient_affected=1 → patient_impact_description reqd | Incident Report | ✅ |
| BR-AT-01 | on_submit: update AC Asset + lifecycle event + audit trail | Asset Transfer | ✅ UAT pass |

---

## 11. Scheduler Jobs

| Job | Tần suất | Tác vụ |
|---|---|---|
| `check_capa_overdue` | Daily | Đánh dấu CAPA quá hạn + email IMM QA Officer |
| `check_vendor_contract_expiry` | Daily | Cảnh báo HĐ NCC hết hạn (90/60/30 ngày) |
| `check_registration_expiry` | Daily | Cảnh báo đăng ký BYT hết hạn (90/60/30/7 ngày) |
| `check_insurance_expiry` | Daily | Cảnh báo bảo hiểm thiết bị hết hạn (90/60/30/7 ngày) |
| `check_service_contract_expiry` | Daily | Cảnh báo Service Contract hết hạn (90/60/30 ngày) |
| `rollup_asset_kpi` | Monthly | Tổng hợp MTTR + uptime từ Asset Repair |

---

## 12. Compliance Coverage

| Tiêu chuẩn | Phạm vi | Coverage |
|---|---|---|
| **WHO HTM** | Full lifecycle 7 phases | 70% (Needs Assessment / Procurement chưa có) |
| **NĐ 98/2021** | UDI, BYT reg, incident reporting | 95% (BR-INC-01 cần block khi thiếu BYT report) |
| **ISO 13485:2016** | Audit trail, CAPA, Document control | 100% (full chain) |
| **ISO/IEC 17025** | Calibration traceability | 40% (IMM-11 calibration WO chưa build) |
| **ISO 14971** | Risk management | 20% (Risk Assessment chưa có) |
| **JCI** | Equipment management, incident | 50% |

---

## 13. Gaps & Roadmap

**Wave 2 (IMM-11 Calibration):** Calibration Work Order, Calibration Certificate — bổ sung ISO/IEC 17025 coverage
**Wave 2 (IMM-13 Disposal):** Asset Disposal, Retirement Certificate — đóng vòng đời
**Wave 2 (IMM-06 Training):** Training Record, Training Requirement — WHO HTM phase 4
**Wave 2 (IMM-15 Risk):** Risk Assessment, Risk Control Measure — ISO 14971

---

**Phiên bản:** v3.1 (sau Wave 1.5 — 2026-04-19)
**Người rà soát:** AssetCore Team
**Tham chiếu:**
- `docs/imm-00/IMM-00_Functional_Specs.md`
- `docs/imm-00/IMM-00_Technical_Design.md`
- `docs/res/IMM-00_Entity_Coverage_Analysis.md`
- `docs/res/IMM-00_UAT_Gap_Analysis.md`
