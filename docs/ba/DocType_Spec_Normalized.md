# DocType Specification — Normalized

> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).**
> File này viết theo BA pack gốc (giả định ERPNext + prefix `AC ` thống nhất + DocType `AC Medical Asset`/`AC Work Order`/`AC Lifecycle Event`). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix). Khi đọc, ánh xạ tên DocType qua **`docs/ba/00_RECONCILIATION_v3.md` §2**, hoặc đọc bản đã rewrite tại **`Phase_03_Data_Domain_Design/05_DocType_Specification_Sheet/DocType_Spec_Wave1.md`**.

---

**Dự án:** AssetCore on Frappe v15 (Frappe-only — KHÔNG dependency ERPNext)
**Nguồn:** Tập 3 — Data & DocType Specification v1.0 (2026-05-05)
**Chuẩn hoá theo format:** DocType Spec Standard v1
**Ghi chú:** `[TBD - cần làm rõ]` = thông tin chưa đủ trong tài liệu gốc, cần xác nhận trước khi build.

---

## Mục lục DocType

### DocType Chính (Document)
1. [Medical Asset](#1-medical-asset)
2. [Device Model](#2-device-model)
3. [Asset Identifier](#3-asset-identifier)
4. [AC Work Order](#4-ac-work-order)
5. [Maintenance Plan](#5-maintenance-plan)
6. [Calibration Plan](#6-calibration-plan)
7. [Failure Report](#7-failure-report)
8. [Initial Inspection](#8-initial-inspection)
9. [Document Record](#9-document-record)
10. [QMS Artifact](#10-qms-artifact)
11. [Lifecycle Event](#11-lifecycle-event)
12. [Compliance Record](#12-compliance-record)
13. [Compliance Case](#13-compliance-case)
14. [CAPA Case](#14-capa-case)
15. [Asset Audit Log](#15-asset-audit-log)
16. [Metric Definition](#16-metric-definition)
17. [Metric Snapshot](#17-metric-snapshot)

### DocType Phụ (Child / Doc bổ trợ)
18. [AC Work Order Task](#18-ac-work-order-task)
19. [AC Spare Consumption](#19-ac-spare-consumption)
20. [Document Record Link](#20-document-record-link)
21. [Document File](#21-document-file)
22. [Document Distribution](#22-document-distribution)
23. [Maintenance Plan Task](#23-maintenance-plan-task)
24. [Maintenance Plan Spare](#24-maintenance-plan-spare)
25. [Calibration Plan Test Point](#25-calibration-plan-test-point)
26. [Initial Inspection Item](#26-initial-inspection-item)
27. [CAPA Action](#27-capa-action)
28. [CAPA Effectiveness Check](#28-capa-effectiveness-check)
29. [Root Cause Analysis](#29-root-cause-analysis)
30. [Adverse Event Report](#30-adverse-event-report)
31. [Recall Notice](#31-recall-notice)
32. [Software Update Record](#32-software-update-record)
33. [Service Contract](#33-service-contract)
34. [Decommission Record](#34-decommission-record)
35. [Decision Record](#35-decision-record)
36. [Management Review](#36-management-review)
37. [Change Control](#37-change-control)

---

## 1. Medical Asset

**Module:** `asset_registry` — phục vụ IMM-04, IMM-05, IMM-07 → IMM-12  
**Type:** Document  
**Linked to ERPNext:** `Asset` (1-1 bắt buộc), `Department`, `Warehouse` (Location), `Asset Category`, `Supplier` (qua Service Contract)  
**Naming rule:** `MA-.YYYY.-.\#\#\#\#\#`  
**Title field:** `asset_id`  
**Lifecycle Events triggered:** `installed`, `commissioned`, `released_for_use`, `transferred`, `in_repair`, `retired`, `disposed`, `state_changed` (mọi thay đổi state)

### Fields

| fieldname | label | fieldtype | options/link | mandatory | default | description |
|---|---|---|---|---|---|---|
| asset_id | Asset ID | Data | — | Yes (unique) | Auto naming | ID nội bộ AssetCore, duy nhất, không đổi suốt vòng đời |
| primary_qr | Primary QR/Barcode | Data | — | Yes (unique) | — | Mã QR chính dán trên thiết bị, khớp asset_id |
| asset_doc | Asset (ERPNext) | Link | Asset | Yes | — | Liên kết Asset core ERPNext (1-1) |
| device_model | Device Model | Link | Device Model | Yes | — | Mẫu thiết bị |
| item_code | Item | Link (read-only) | Item | No | fetch_from device_model | Item của Device Model, fetch_from |
| serial_no | Serial Number | Data | — | No | — | Serial của nhà sản xuất |
| mfg_date | Manufacturing Date | Date | — | No | — | Ngày sản xuất |
| installation_date | Installation Date | Date | — | No | — | Ngày lắp đặt thực tế |
| commissioning_date | Commissioning Date | Date | — | No | — | Ngày commissioning |
| release_date | Release Date | Date | — | No | — | Ngày released_for_use |
| risk_class | Risk Class | Link | Risk Class | Yes | — | A/B/C/D theo Nghị định 98 |
| criticality | Criticality | Link | Criticality | Yes | — | Critical / Major / Minor |
| asset_category | Category | Link | Asset Category | Yes | — | Danh mục (imaging, lab, surgery…) |
| department | Owning Department | Link | Department | Yes | — | Khoa sở hữu |
| location | Location | Link | Warehouse | Yes | — | Vị trí vật lý hiện tại |
| custodian | Custodian | Link | User | No | — | Người chịu trách nhiệm thường nhật |
| state | Lifecycle State | Select | need_registered / installed_pending / installed / commissioned / released_for_use / in_use / in_repair / out_of_service / idle / transferred / retired / disposed / donated / stored_long_term | Yes | need_registered | Trạng thái lifecycle (workflow controlled) |
| calibration_required | Calibration Required | Check | — | No | [TBD - cần làm rõ: auto True với Class C/D, nhưng default cho A/B?] | Cờ bật/tắt yêu cầu calibration |
| legal_license_status | Legal License Status | Select | ok / expiring_soon / expired / missing | No | — | Auto tổng hợp từ Compliance Record (IMM-05) |
| warranty_until | Warranty Until | Date | — | No | — | Hạn bảo hành nhà sản xuất |
| service_contract | Service Contract | Link | Service Contract | No | — | Hợp đồng dịch vụ kỹ thuật hiện hành |
| last_pm_date | Last PM Date | Date (read-only) | — | No | — | Tự cập nhật từ WO PM qua scheduled job |
| next_pm_due | Next PM Due | Date (read-only) | — | No | — | Auto từ Maintenance Plan active |
| last_calibration_date | Last Calibration Date | Date (read-only) | — | No | — | Tự cập nhật từ Calibration WO |
| next_calibration_due | Next Calibration Due | Date (read-only) | — | No | — | Auto từ Calibration Plan |
| uptime_30d | Uptime 30d | Percent (read-only) | — | No | — | Cập nhật bởi Metric Snapshot |
| mtbf_90d | MTBF 90d (hours) | Float (read-only) | — | No | — | Snapshot từ Metric engine |
| mttr_90d | MTTR 90d (hours) | Float (read-only) | — | No | — | Snapshot từ Metric engine |
| replacement_signal | Replacement Signal | Check (read-only) | — | No | — | Bật bởi IMM-17 predictive engine |
| notes | Notes | Text Editor | — | No | — | Ghi chú tự do |

### Validations

```python
# validate()
if risk_class in ("C", "D"):
    self.calibration_required = True

if self.risk_class != self.device_model.risk_class_default:
    if risk_level(self.risk_class) < risk_level(self.device_model.risk_class_default):
        frappe.throw("risk_class không được thấp hơn default của Device Model (DQ-CONS-001)")

# before_insert
if frappe.db.exists("Medical Asset", {"primary_qr": self.primary_qr}):
    frappe.throw("primary_qr đã tồn tại — phải unique (DQ-UNIQ-002)")

# released_for_use state check (DQ-COMP-001)
if self.state == "released_for_use":
    required = ["device_model", "risk_class", "criticality", "department", "location",
                "custodian", "primary_qr", "serial_no"]
    for f in required:
        if not self.get(f):
            frappe.throw(f"Field '{f}' bắt buộc trước khi released_for_use")

# ABAC permission_query_conditions — BE/Operator/Dept Head chỉ thấy asset thuộc khoa được gán
```

### Workflow

**States:**
`need_registered` → `installed_pending` → `installed` → `commissioned` → `released_for_use` → `in_use` ↔ `in_repair` / `out_of_service` / `idle` / `transferred` → `retired` → `disposed` / `donated` / `stored_long_term`

**Transitions:**

| From | To | Trigger | Guard | Actor |
|---|---|---|---|---|
| need_registered | installed_pending | Installation WO submitted | WO type = INSTALLATION | HTM Manager / Biomed Engineer |
| installed_pending | installed | Physical installation confirmed | Installation WO completed | HTM Manager / Biomed Engineer |
| installed | commissioned | Initial Inspection passed | overall_result = pass | HTM Manager |
| commissioned | released_for_use | Commissioning sign-off | DQ-COMP-001 passed | HTM Manager |
| released_for_use | in_use | Manual transition | — | HTM Manager |
| in_use | in_repair | Failure Report submitted | CM WO created | HTM Manager / Biomed Engineer |
| in_repair | in_use | CM WO completed (validated) | validation_result = pass | HTM Manager |
| in_use | out_of_service | Manual decision | — | HTM Manager |
| in_use | transferred | Asset Movement submitted | ac_movement_reason set | HTM Manager |
| * | retired | Decommission Record submitted | Sponsor sign-off | HTM Manager / Sponsor |
| retired | disposed / donated / stored_long_term | Decommission method confirmed | — | HTM Manager / Sponsor |

### Hooks

**before_insert:** Validate naming rule; kiểm tra `primary_qr` unique toàn site (DQ-UNIQ-002).

**before_save:** [TBD - cần làm rõ: có cần re-validate DQ-CONS-001 mỗi lần save không?]

**on_update:** Nếu `state` thay đổi → gọi Lifecycle Event engine tạo `Lifecycle Event` tương ứng. Cập nhật `Asset.ac_medical_asset` reverse link.

**on_submit:** [TBD - cần làm rõ: Medical Asset không submittable — confirm lại]

**on_cancel:** [TBD - cần làm rõ: Medical Asset không submittable]

**permission_query_conditions:** Enforce ABAC theo department cho roles Biomed Engineer, Operator, Department Head.

**Scheduled jobs (không trong hooks):**
- Daily: cập nhật `last_pm_date`, `next_pm_due` từ Maintenance Plan active.
- Daily: tổng hợp `legal_license_status` từ Compliance Records.
- Metric snapshot job (hourly/daily): cập nhật `uptime_30d`, `mtbf_90d`, `mttr_90d`, `replacement_signal`.

### Permissions

| Role | Read | Write | Create | Submit | Cancel | Amend |
|---|---|---|---|---|---|---|
| AssetCore HTM Manager | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| AssetCore Biomed Engineer | ✓ (ABAC scope) | ✓ | — | — | — | — |
| AssetCore Department Head | ✓ (dept scope) | — | — | — | — | — |
| AssetCore Operator | ✓ (narrow scope) | — | — | — | — | — |
| AssetCore QMS Officer | ✓ | — | — | — | — | — |
| AssetCore Auditor | ✓ | — | — | — | — | — |

---

## 2. Device Model

**Module:** `asset_registry` — phục vụ IMM-04  
**Type:** Document  
**Linked to ERPNext:** `Item` (1-1), `Supplier` (Manufacturer)  
**Naming rule:** `DM-{model_code}`  
**Title field:** `model_name`  
**Lifecycle Events triggered:** Không trực tiếp sinh Lifecycle Event (chỉ là master data); thay đổi được track qua `Track Changes = Yes`.

### Fields

| fieldname | label | fieldtype | options/link | mandatory | default | description |
|---|---|---|---|---|---|---|
| model_code | Model Code | Data | — | Yes (unique) | — | Mã model nhà sản xuất |
| model_name | Model Name | Data | — | Yes | — | Tên model đầy đủ |
| manufacturer | Manufacturer | Link | Supplier | Yes | — | Nhà sản xuất |
| item_code | Linked Item | Link | Item | Yes | — | Item master tương ứng |
| device_type | Device Type | Select | imaging / lab / surgery / icu / general / [TBD - cần làm rõ: danh sách đầy đủ] | Yes | — | Loại thiết bị |
| risk_class_default | Default Risk Class | Link | Risk Class | Yes | — | Default cho asset thuộc model này |
| calibration_required_default | Calibration Required Default | Check | — | No | — | Default calibration flag cho asset mới |
| pm_template | PM Template | Link | Maintenance Plan Template | No | — | Template PM áp dụng auto khi tạo asset |
| calibration_template | Calibration Template | Link | Calibration Plan Template | No | — | Template Calibration áp dụng auto |
| expected_lifetime_years | Expected Lifetime (years) | Int | — | No | — | Vòng đời kỹ thuật dự kiến |
| spec_sheet | Spec Sheet | Attach | — | No | — | PDF spec từ vendor |
| user_manual | User Manual | Attach | — | No | — | PDF user manual |
| service_manual | Service Manual | Attach | — | No | — | PDF service manual |

### Validations

```python
# validate()
if not self.model_code:
    frappe.throw("model_code bắt buộc")

if frappe.db.exists("Device Model", {"model_code": self.model_code, "name": ("!=", self.name)}):
    frappe.throw("model_code đã tồn tại cho Manufacturer này (DQ-UNIQ-004)")

if self.is_new() or self.get_doc_before_save().get("is_active"):
    if not self.spec_sheet and not self.user_manual:
        frappe.throw("Model active phải có ít nhất spec_sheet hoặc user_manual")
```

### Workflow

**States:** [TBD - cần làm rõ: Device Model không có workflow state machine rõ ràng trong tài liệu gốc — chỉ có Track Changes. Cần quyết định có cần active/inactive state không]

**Transitions:** [TBD - cần làm rõ]

### Hooks

**before_insert:** [TBD - cần làm rõ]

**before_save:** Validate `model_code` unique.

**on_submit:** [TBD - Device Model không submittable]

**on_cancel:** [TBD - Device Model không submittable]

### Permissions

| Role | Read | Write | Create | Submit | Cancel | Amend |
|---|---|---|---|---|---|---|
| AssetCore HTM Manager | ✓ | ✓ | ✓ | — | — | — |
| AssetCore Biomed Engineer | ✓ | ✓ | [TBD] | — | — | — |
| AssetCore Department Head | ✓ | — | — | — | — | — |
| AssetCore Operator | ✓ | — | — | — | — | — |
| AssetCore QMS Officer | ✓ | — | — | — | — | — |
| AssetCore Auditor | ✓ | — | — | — | — | — |

---

## 3. Asset Identifier

**Module:** `asset_registry` — phục vụ IMM-04  
**Type:** Document  
**Linked to ERPNext:** Không trực tiếp; Medical Asset link Asset core gián tiếp  
**Naming rule:** `AID-.YYYY.-.\#\#\#\#\#`  
**Title field:** `name`  
**Lifecycle Events triggered:** [TBD - cần làm rõ: có sinh Lifecycle Event khi primary identifier thay đổi không?]

### Fields

| fieldname | label | fieldtype | options/link | mandatory | default | description |
|---|---|---|---|---|---|---|
| medical_asset | Medical Asset | Link | Medical Asset | Yes | — | Asset gắn với identifier này |
| identifier_type | Identifier Type | Select | internal_qr / external_serial / asset_tag / regulatory_id | Yes | — | Loại định danh |
| identifier_value | Identifier Value | Data | — | Yes (unique per type) | — | Giá trị identifier |
| is_primary | Primary | Check | — | No | 0 | Mỗi asset chỉ 1 primary per identifier_type=internal_qr |
| issued_date | Issued Date | Date | — | No | — | Ngày in/cấp |
| valid_until | Valid Until | Date | — | No | — | Hạn (nếu có) |
| printed_format | Printed Format | Select | sticker / laser / metal_tag / none | No | — | Định dạng vật lý |
| notes | Notes | Small Text | — | No | — | Ghi chú |

### Validations

```python
# validate()
# DQ-UNIQ-002: identifier_value unique theo identifier_type
existing = frappe.db.exists("Asset Identifier", {
    "identifier_type": self.identifier_type,
    "identifier_value": self.identifier_value,
    "name": ("!=", self.name)
})
if existing:
    frappe.throw(f"identifier_value '{self.identifier_value}' đã tồn tại cho type '{self.identifier_type}'")

# Chỉ 1 is_primary cho cặp (medical_asset, identifier_type='internal_qr')
if self.is_primary and self.identifier_type == "internal_qr":
    existing_primary = frappe.db.exists("Asset Identifier", {
        "medical_asset": self.medical_asset,
        "identifier_type": "internal_qr",
        "is_primary": 1,
        "name": ("!=", self.name)
    })
    if existing_primary:
        frappe.throw("Asset này đã có primary internal_qr identifier")
```

### Workflow

**States:** [TBD - cần làm rõ: không có workflow state machine; chỉ là record data]

**Transitions:** [TBD - cần làm rõ]

### Hooks

**before_insert:** Validate `identifier_value` unique theo `identifier_type`.

**before_save:** Re-validate primary constraint.

**on_submit:** [TBD - Asset Identifier không submittable]

**on_cancel:** [TBD - Asset Identifier không submittable]

### Permissions

| Role | Read | Write | Create | Submit | Cancel | Amend |
|---|---|---|---|---|---|---|
| AssetCore HTM Manager | ✓ | ✓ | ✓ | — | — | — |
| AssetCore Biomed Engineer | ✓ (ABAC) | ✓ | ✓ | — | — | — |
| AssetCore Department Head | ✓ | — | — | — | — | — |
| AssetCore Operator | ✓ | — | — | — | — | — |
| AssetCore QMS Officer | ✓ | — | — | — | — | — |
| AssetCore Auditor | ✓ | — | — | — | — | — |

---

## 4. AC Work Order

**Module:** `work_order` — phục vụ IMM-08 (PM), IMM-09 (CM/Repair), IMM-11 (Calibration), IMM-04 (Installation), IMM-12 (Recall/CAPA)  
**Type:** Document  
**Linked to ERPNext:** `Item` (qua Spare Consumption → Stock Entry), `HR Team`, `User`  
**Naming rule:** `WO-{wo_type_short}-.YYYY.-.\#\#\#\#\#`  
**Title field:** `subject`  
**Is Submittable:** Yes  
**Lifecycle Events triggered:** `pm_completed`, `repaired`, `calibration_completed`, `installation_completed`, `recall_actioned`, `wo_cancelled` (on_cancel)

### Fields

| fieldname | label | fieldtype | options/link | mandatory | default | description |
|---|---|---|---|---|---|---|
| subject | Subject | Data | — | Yes | — | Tóm tắt WO |
| wo_type | Work Order Type | Link | Work Order Type | Yes | — | PM / CM / Inspection / Calibration / Recall / Retirement / Installation |
| medical_asset | Medical Asset | Link | Medical Asset | Yes | — | Asset đối tượng |
| from_plan | From Plan | Dynamic Link | Maintenance Plan / Calibration Plan | No | — | Nếu sinh từ plan |
| from_failure_report | From Failure Report | Link | Failure Report | No | — | Nếu CM |
| from_recall | From Recall Notice | Link | Recall Notice | No | — | Nếu Recall |
| severity | Severity | Select | S1 / S2 / S3 / S4 | No | — | Cho CM; bắt buộc khi wo_type=CM |
| priority | Priority | Select | Critical / High / Medium / Low | No | — | Auto theo severity & criticality matrix |
| planned_start | Planned Start | Datetime | — | No | — | Lịch dự kiến bắt đầu |
| planned_end | Planned End | Datetime | — | No | — | Lịch dự kiến kết thúc |
| actual_start | Actual Start | Datetime | — | No | — | Thực tế bắt đầu; bắt buộc khi submit |
| actual_end | Actual End | Datetime | — | No | — | Thực tế kết thúc; bắt buộc khi submit |
| sla_due | SLA Due | Datetime | — | No | — | Auto tính theo severity matrix |
| assigned_team | Assigned Team | Link | HR Team | No | — | Đội thực hiện |
| assigned_to | Assigned To | Link | User | No | — | Cá nhân thực hiện |
| state | State | Select | planned / scheduled / in_progress / paused / completed / closed / overdue / cancelled | Yes | planned | Workflow controlled |
| downtime_hours | Downtime (hours) | Float | — | No | — | Tự tính hoặc nhập tay (DQ-CONS-004) |
| root_cause | Root Cause | Small Text | — | No | — | Cho CM |
| action_taken | Action Taken | Text Editor | — | No | — | Mô tả công việc thực hiện; bắt buộc khi submit |
| close_code | Close Code | Select | completed_ok / completed_with_findings / transferred / cancelled | No | — | Code đóng WO |
| validation_result | Validation Result | Select | pass / fail / n_a | No | — | Kết quả test sau khi hoàn thành |
| linked_capa | Linked CAPA | Link | CAPA Case | No | — | Nếu cần CAPA |
| cost_labor | Cost — Labor | Currency | — | No | — | Chi phí nhân công |
| cost_parts | Cost — Parts | Currency | — | No | — | Chi phí phụ tùng (từ Spare Consumption) |
| cost_external | Cost — External Service | Currency | — | No | — | Chi phí service provider bên ngoài |
| wo_tasks | Tasks | Table | AC Work Order Task | No | — | Child checklist |
| spare_consumption | Spare Consumption | Table | AC Spare Consumption | No | — | Child spare parts |
| evidences | Evidences | Table | Document Record Link | No | — | Đính kèm chuẩn hoá; ≥ 1 bắt buộc khi submit |

### Validations

```python
# validate()
if self.wo_type == "CM" and not self.severity:
    frappe.throw("severity bắt buộc cho WO type CM (BR-IMM09-001)")

if self.severity and self.priority:
    expected = severity_to_priority_map(self.severity, self.medical_asset.criticality)
    if self.priority != expected:
        frappe.msgprint(f"priority nên là '{expected}' theo severity & criticality matrix")

if self.actual_start and self.actual_end:
    if self.actual_end < self.actual_start:
        frappe.throw("actual_end phải sau actual_start (DQ-CONS-003)")

# before_submit()
required_on_submit = ["actual_start", "actual_end", "action_taken"]
for f in required_on_submit:
    if not self.get(f):
        frappe.throw(f"Field '{f}' bắt buộc trước khi submit")

if not self.evidences:
    frappe.throw("Phải có ít nhất 1 evidence trước khi submit (DQ-COMP-004)")

# Downtime auto-calc (DQ-CONS-004)
if self.actual_start and self.actual_end and not self.downtime_hours:
    delta = time_diff_in_hours(self.actual_end, self.actual_start)
    self.downtime_hours = max(0, delta)
```

### Workflow

**States:** `planned`, `scheduled`, `in_progress`, `paused`, `completed`, `closed`, `overdue`, `cancelled`

**Transitions:**

| From | To | Trigger | Guard | Actor |
|---|---|---|---|---|
| planned | scheduled | Schedule confirmed | planned_start set | HTM Manager / Biomed Engineer |
| scheduled | in_progress | Work started | actual_start filled | Biomed Engineer |
| in_progress | paused | Work paused | reason provided | Biomed Engineer / HTM Manager |
| paused | in_progress | Work resumed | — | Biomed Engineer |
| in_progress | completed | WO submitted | before_submit validations pass | HTM Manager |
| completed | closed | Closed by manager | — | HTM Manager |
| planned / scheduled / in_progress | overdue | Scheduled job (hourly) | now > sla_due | System (auto) |
| * | cancelled | Cancel action | HTM Manager with reason | HTM Manager |

**docstatus mapping:**
- `planned / scheduled / in_progress / paused / overdue` → docstatus = 0
- `completed / closed` → docstatus = 1 (Submitted)
- `cancelled` → docstatus = 2 (Cancelled)

### Hooks

**before_insert:** [TBD - cần làm rõ: auto-fill `sla_due` từ severity matrix khi tạo?]

**before_save:** Validate severity/priority consistency; auto-calc `downtime_hours`.

**on_submit:** Tạo `Lifecycle Event` tương ứng (`pm_completed` / `repaired` / `calibration_completed`…). Trigger scheduled job cập nhật `asset.last_pm_date` hoặc `last_calibration_date`.

**on_cancel:** Chỉ cho phép HTM Manager với reason; sinh Lifecycle Event `wo_cancelled`.

**Scheduled job (hourly):** Kiểm tra `sla_due` → nếu quá hạn: set `state = overdue`, escalate notification.

### Permissions

| Role | Read | Write | Create | Submit | Cancel | Amend |
|---|---|---|---|---|---|---|
| AssetCore HTM Manager | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| AssetCore Biomed Engineer | ✓ | ✓ | ✓ | ✓ | — | — |
| AssetCore Technician | ✓ | ✓ | — | — | — | — |
| AssetCore Department Head | ✓ | — | — | — | — | — |
| AssetCore QMS Officer | ✓ | — | — | — | — | — |
| AssetCore Auditor | ✓ | — | — | — | — | — |

---

## 5. Maintenance Plan

**Module:** `maintenance_plan` — phục vụ IMM-08  
**Type:** Document  
**Linked to ERPNext:** `Item` (qua Maintenance Plan Spare)  
**Naming rule:** `MP-.YYYY.-.\#\#\#\#\#`  
**Title field:** `name`  
**Is Submittable:** Yes  
**Lifecycle Events triggered:** `pm_plan_activated`, `pm_plan_deactivated` [TBD - cần làm rõ: event cụ thể]

### Fields

| fieldname | label | fieldtype | options/link | mandatory | default | description |
|---|---|---|---|---|---|---|
| medical_asset | Medical Asset | Link | Medical Asset | Yes | — | Asset đối tượng |
| plan_template | Plan Template | Link | Maintenance Plan Template | No | — | Áp dụng template (tuỳ chọn) |
| frequency | Frequency | Select | monthly / quarterly / semi / annual / biennial / usage-based | Yes | — | Tần suất PM |
| interval_days | Interval (days) | Int | — | No | — | Nếu custom interval |
| interval_usage_hours | Interval (usage hours) | Int | — | No | — | Nếu usage-based |
| next_due_date | Next Due Date | Date (read-only) | — | Yes | — | Auto tính từ last_completed_date + interval |
| last_completed_date | Last Completed Date | Date (read-only) | — | No | — | Auto cập nhật từ WO submitted |
| active | Active | Check | — | No | 1 | Có sinh WO hay không |
| effective_from | Effective From | Date | — | Yes | — | Ngày bắt đầu áp dụng |
| effective_until | Effective Until | Date | — | No | — | Ngày hết hiệu lực |
| tasks | Tasks | Table | Maintenance Plan Task | No | — | Checklist mặc định cho WO |
| estimated_duration_hours | Estimated Duration (hours) | Float | — | No | — | Cho phép planning nhân lực |
| required_skills | Required Skills | Small Text | — | No | — | Kỹ năng kỹ thuật cần |
| spare_estimate | Spare Estimate | Table | Maintenance Plan Spare | No | — | Phụ tùng dự kiến mỗi lần PM |
| sop_reference | SOP Reference | Link | QMS Artifact | No | — | SOP áp dụng cho PM này |

### Validations

```python
# validate()
# DQ-COMP-003: ≥ 3 task
if self.active and len(self.tasks) < 3:
    frappe.throw("Maintenance Plan active phải có ít nhất 3 task (DQ-COMP-003)")

# Chỉ 1 plan active per asset per frequency (BR-IMM08-001)
if self.active:
    existing = frappe.db.exists("Maintenance Plan", {
        "medical_asset": self.medical_asset,
        "frequency": self.frequency,
        "active": 1,
        "name": ("!=", self.name)
    })
    if existing:
        frappe.throw(f"Đã có Maintenance Plan active với frequency '{self.frequency}' cho asset này")

# effective_until > effective_from
if self.effective_until and self.effective_until <= self.effective_from:
    frappe.throw("effective_until phải sau effective_from")
```

### Workflow

**States:** `draft` → `active` → `inactive` / `expired` [TBD - cần làm rõ: workflow state machine đầy đủ không được định nghĩa trong tài liệu gốc]

**Transitions:**

| From | To | Trigger | Guard | Actor |
|---|---|---|---|---|
| draft | active | Submit | tasks ≥ 3, effective_from set | HTM Manager / Biomed Engineer |
| active | inactive | Deactivate (active=0) | — | HTM Manager |
| active | expired | Scheduler daily | now > effective_until | System (auto) |

**docstatus:** 0 (draft), 1 (submitted/active), 2 (cancelled)

### Hooks

**before_insert:** [TBD - cần làm rõ]

**before_save:** Validate single active plan per asset per frequency.

**on_submit:** Set `active = True`; tính `next_due_date`.

**on_cancel:** Set `active = False`.

**Scheduled job (daily):**
- Tính `next_due_date = last_completed_date + interval_days` (hoặc theo frequency).
- Nếu `next_due_date - today` ∈ {14, 7, 3, 1}: tạo PM WO trạng thái `planned` (idempotent — không tạo duplicate nếu WO chưa closed).

### Permissions

| Role | Read | Write | Create | Submit | Cancel | Amend |
|---|---|---|---|---|---|---|
| AssetCore HTM Manager | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| AssetCore Biomed Engineer | ✓ | ✓ | ✓ | ✓ | — | — |
| AssetCore Department Head | ✓ | — | — | — | — | — |
| AssetCore QMS Officer | ✓ | — | — | — | — | — |
| AssetCore Auditor | ✓ | — | — | — | — | — |
| AssetCore Technician | ✓ | — | — | — | — | — |

---

## 6. Calibration Plan

**Module:** `calibration` — phục vụ IMM-11  
**Type:** Document  
**Linked to ERPNext:** `Supplier` (Service Provider nếu external)  
**Naming rule:** `CP-.YYYY.-.\#\#\#\#\#`  
**Title field:** `name`  
**Is Submittable:** Yes  
**Lifecycle Events triggered:** `calibration_plan_activated` [TBD - cần làm rõ]

### Fields

| fieldname | label | fieldtype | options/link | mandatory | default | description |
|---|---|---|---|---|---|---|
| medical_asset | Medical Asset | Link | Medical Asset | Yes | — | Asset cần calibration |
| plan_template | Plan Template | Link | Calibration Plan Template | No | — | Template áp dụng |
| calibration_type | Calibration Type | Select | internal / external / regulatory / safety | Yes | — | Loại calibration |
| frequency_months | Frequency (months) | Int | — | Yes | — | Chu kỳ tính theo tháng |
| next_due_date | Next Due Date | Date (read-only) | — | Yes | — | Auto tính |
| last_completed_date | Last Completed Date | Date (read-only) | — | No | — | Auto cập nhật từ Calibration WO |
| service_provider | Service Provider | Link | Supplier | No | — | Bắt buộc nếu external/regulatory |
| tolerance_spec | Tolerance Specification | Text Editor | — | Yes | — | Tham chiếu SOP/standard dung sai |
| test_points | Test Points | Table | Calibration Plan Test Point | No | — | Các điểm đo |
| sop_reference | SOP Reference | Link | QMS Artifact | Yes | — | SOP áp dụng |
| active | Active | Check | — | No | 1 | Có sinh Calibration WO |

### Validations

```python
# validate()
# Nếu external/regulatory thì service_provider bắt buộc (BR-IMM11-005)
if self.calibration_type in ("external", "regulatory") and not self.service_provider:
    frappe.throw("service_provider bắt buộc với calibration_type external/regulatory")

# DQ-CONS-002: nếu asset.calibration_required=1 phải có ≥ 1 active Calibration Plan
# (check này thực hiện từ Medical Asset validate hoặc scheduler)
```

### Workflow

**States:** `draft` → `active` → `inactive` / `expired` [TBD - cần làm rõ: giống Maintenance Plan]

**Transitions:**

| From | To | Trigger | Guard | Actor |
|---|---|---|---|---|
| draft | active | Submit | tolerance_spec + sop_reference set | HTM Manager |
| active | inactive | Deactivate | — | HTM Manager |

### Hooks

**before_insert:** [TBD - cần làm rõ]

**before_save:** Validate service_provider cho external/regulatory.

**on_submit:** Set `active = True`; tính `next_due_date`.

**on_cancel:** Set `active = False`.

**Scheduled job (daily):** Tính `next_due_date`; nếu `next_due_date - today` ∈ {30, 14, 7, 3}: sinh Calibration WO trạng thái `planned`.

### Permissions

| Role | Read | Write | Create | Submit | Cancel | Amend |
|---|---|---|---|---|---|---|
| AssetCore HTM Manager | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| AssetCore Biomed Engineer | ✓ | ✓ | ✓ | ✓ | — | — |
| AssetCore QMS Officer | ✓ | — | — | — | — | — |
| AssetCore Auditor | ✓ | — | — | — | — | — |

---

## 7. Failure Report

**Module:** `corrective` — phục vụ IMM-09, IMM-12  
**Type:** Document  
**Linked to ERPNext:** `User`  
**Naming rule:** `FR-.YYYY.-.\#\#\#\#\#`  
**Title field:** `name`  
**Is Submittable:** Yes  
**Lifecycle Events triggered:** `failure_reported`, `in_repair` (asset state change on_submit)

### Fields

| fieldname | label | fieldtype | options/link | mandatory | default | description |
|---|---|---|---|---|---|---|
| medical_asset | Medical Asset | Link | Medical Asset | Yes | — | Asset xảy ra sự cố |
| reported_by | Reported By | Link | User | Yes | — | Người báo cáo (nurse, doctor, BE) |
| reported_at | Reported At | Datetime | — | Yes | — | Thời điểm báo cáo |
| severity | Severity | Select | S1 / S2 / S3 / S4 | Yes | — | Mức độ nghiêm trọng |
| description | Description | Text Editor | — | Yes | — | Mô tả triệu chứng (≥ 50 ký tự) |
| clinical_impact | Clinical Impact | Select | patient_harm / no_patient_harm / near_miss / none | Yes | — | Ảnh hưởng lâm sàng |
| happened_during | Happened During | Select | scheduled_use / unscheduled / PM / calibration / idle / other | No | — | Bối cảnh xảy ra |
| evidences | Evidences | Table | Document Record Link | No | — | Ảnh, video, log |
| resulting_wo | Resulting CM Work Order | Link (read-only) | AC Work Order | No | — | Auto-create khi submit |
| status | Status | Select | open / in_triage / wo_created / closed | Yes | open | Trạng thái xử lý |

### Validations

```python
# validate()
if len(self.description or "") < 50:
    frappe.throw("description phải ≥ 50 ký tự")
```

### Workflow

**States:** `open` → `in_triage` → `wo_created` → `closed`

**Transitions:**

| From | To | Trigger | Guard | Actor |
|---|---|---|---|---|
| open | in_triage | Biomed Engineer nhận | — | Biomed Engineer / HTM Manager |
| in_triage | wo_created | Submit (auto-create CM WO) | severity set | Biomed Engineer / HTM Manager |
| wo_created | closed | CM WO closed | — | HTM Manager |

**docstatus:** 0 (open/in_triage), 1 (submitted → wo_created), 2 (cancelled) [TBD - cần làm rõ: mapping docstatus chính xác]

### Hooks

**before_insert:** [TBD - cần làm rõ]

**before_save:** Validate description ≥ 50 ký tự.

**on_submit:**
1. Auto-set `asset.state → in_repair` (precautionary).
2. Auto-create CM `AC Work Order` với `from_failure_report = self.name`; fill `resulting_wo`.
3. Nếu `clinical_impact = patient_harm` → tự động tạo `Adverse Event Report` linked.

**on_cancel:** [TBD - cần làm rõ: có rollback asset.state không?]

### Permissions

| Role | Read | Write | Create | Submit | Cancel | Amend |
|---|---|---|---|---|---|---|
| AssetCore HTM Manager | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| AssetCore Biomed Engineer | ✓ | ✓ | ✓ | ✓ | — | — |
| AssetCore Technician | ✓ | ✓ | ✓ | — | — | — |
| AssetCore Operator | ✓ | ✓ | ✓ | — | — | — |
| AssetCore Department Head | ✓ | — | — | — | — | — |
| AssetCore QMS Officer | ✓ | — | — | — | — | — |
| AssetCore Auditor | ✓ | — | — | — | — | — |

---

## 8. Initial Inspection

**Module:** `asset_registry` — phục vụ IMM-04  
**Type:** Document  
**Linked to ERPNext:** `User`  
**Naming rule:** `II-.YYYY.-.\#\#\#\#\#`  
**Title field:** `name`  
**Is Submittable:** Yes  
**Lifecycle Events triggered:** `commissioned` (nếu pass), `installed_failed` (nếu fail)

### Fields

| fieldname | label | fieldtype | options/link | mandatory | default | description |
|---|---|---|---|---|---|---|
| medical_asset | Medical Asset | Link | Medical Asset | Yes | — | Asset được kiểm tra |
| inspection_date | Inspection Date | Date | — | Yes | — | Ngày kiểm tra |
| inspector | Inspector | Link | User | Yes | — | Người kiểm tra |
| checklist_template | Checklist Template | Link | Initial Inspection Template | No | — | Template checklist (nếu có) |
| items | Items | Table | Initial Inspection Item | Yes | — | Các điểm kiểm tra; ≥ 1 |
| overall_result | Overall Result | Select | pass / fail / conditional | Yes | — | Kết luận tổng thể |
| evidences | Evidences | Table | Document Record Link | No | — | Ảnh, biên bản kiểm tra |
| approved_by | Approved By | Link | User | No | — | HTM Manager ký duyệt |
| approval_date | Approval Date | Date | — | No | — | Ngày HTM Manager ký |

### Validations

```python
# validate()
if not self.items:
    frappe.throw("Phải có ít nhất 1 Inspection Item")

if not self.evidences:
    frappe.throw("Phải có ít nhất 1 evidence (ảnh/biên bản)")

# before_submit()
if not self.overall_result:
    frappe.throw("overall_result bắt buộc trước khi submit")
```

### Workflow

**States:** `draft` → `submitted`

**Transitions:**

| From | To | Trigger | Guard | Actor |
|---|---|---|---|---|
| draft | submitted | Submit | overall_result set + ≥ 1 evidence | Inspector / HTM Manager |

### Hooks

**before_insert:** [TBD - cần làm rõ]

**before_save:** Validate ≥ 1 evidence.

**on_submit:**
- Nếu `overall_result = pass` → set `asset.state → commissioned`; sinh Lifecycle Event `commissioned`.
- Nếu `overall_result = fail` → set `asset.state → installed_failed` [TBD - cần làm rõ: state `installed_failed` có trong state machine không?]; sinh Lifecycle Event `inspection_failed`.
- Nếu `overall_result = conditional` → [TBD - cần làm rõ: xử lý conditional pass như thế nào?]

**on_cancel:** [TBD - cần làm rõ: rollback asset.state?]

### Permissions

| Role | Read | Write | Create | Submit | Cancel | Amend |
|---|---|---|---|---|---|---|
| AssetCore HTM Manager | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| AssetCore Biomed Engineer | ✓ | ✓ | ✓ | ✓ | — | — |
| AssetCore QMS Officer | ✓ | — | — | — | — | — |
| AssetCore Auditor | ✓ | — | — | — | — | — |

---

## 9. Document Record

**Module:** `document_qms` — phục vụ IMM-05, IMM-10, cross-module  
**Type:** Document  
**Linked to ERPNext:** `User`, `DocType` (dynamic scope)  
**Naming rule:** `DOC-.YYYY.-.\#\#\#\#\#`  
**Title field:** `name`  
**Is Submittable:** Yes  
**Lifecycle Events triggered:** `document_effective`, `document_expired`, `document_superseded`

### Fields

| fieldname | label | fieldtype | options/link | mandatory | default | description |
|---|---|---|---|---|---|---|
| title | Title | Data | — | Yes | — | Tiêu đề tài liệu |
| document_type | Document Type | Link | Document Type | Yes | — | Loại tài liệu (LIC-MOH-REG, DOC-SOP, …) |
| scope_doctype | Scope DocType | Link | DocType | No | — | Phạm vi: Medical Asset / Vendor / Site / Global |
| scope_doc | Scope Doc | Dynamic Link | scope_doctype | No | — | Bản ghi cụ thể trong scope |
| version | Version | Data | — | Yes | — | Phiên bản (vd: 1.0, 1.1) |
| effective_from | Effective From | Date | — | Yes | — | Ngày hiệu lực (= ngày approver ký) |
| effective_until | Effective Until | Date | — | No | — | Ngày hết hiệu lực |
| status | Status | Select | draft / in_review / effective / superseded / retired / expired | Yes | draft | Trạng thái tài liệu |
| owner_user | Document Owner | Link | User | Yes | — | Chủ tài liệu (khác người tạo) |
| approved_by | Approved By | Link | User | No | — | Người duyệt |
| approval_date | Approval Date | Date | — | No | — | Ngày duyệt |
| distribution_list | Distribution List | Table | Document Distribution | No | — | Danh sách phân phối |
| files | Files | Table | Document File | Yes | — | File đính kèm có metadata; ≥ 1 |
| language | Language | Select | vi / en / vi+en | Yes | vi | Ngôn ngữ tài liệu |
| is_qms_artifact | Is QMS Artifact | Check | — | No | 0 | Cờ xác định tier QMS |
| qms_tier | QMS Tier | Select | QC / PR-SOP / WI-JD / BM-HS-KPI | No | — | Bắt buộc nếu is_qms_artifact=1 |
| retention_years | Retention (years) | Int | — | Yes | — | Theo loại tài liệu / quy định |
| supersedes | Supersedes | Link | Document Record | No | — | Bản cũ bị thay thế |

### Validations

```python
# validate()
if self.is_qms_artifact and not self.qms_tier:
    frappe.throw("qms_tier bắt buộc khi is_qms_artifact = 1")

if self.effective_until and self.effective_until <= self.effective_from:
    frappe.throw("effective_until phải sau effective_from")

# before_submit() — transition to effective
if self.status == "effective":
    if not self.approved_by:
        frappe.throw("approved_by bắt buộc trước khi effective")
    if not self.approval_date:
        frappe.throw("approval_date bắt buộc trước khi effective")
    if not self.files:
        frappe.throw("Phải có ít nhất 1 file đính kèm")

# DQ-UNIQ-005: chỉ 1 effective tại 1 thời điểm cho cùng scope + document_type LIC-MOH-REG
if self.document_type == "LIC-MOH-REG" and self.status == "effective":
    existing = frappe.db.exists("Document Record", {
        "scope_doc": self.scope_doc,
        "document_type": self.document_type,
        "status": "effective",
        "name": ("!=", self.name)
    })
    if existing:
        frappe.throw("Đã có Document Record effective loại LIC-MOH-REG cho asset này (DQ-UNIQ-005)")
```

### Workflow

**States:** `draft` → `in_review` → `effective` → `superseded` / `retired` / `expired`

**Transitions:**

| From | To | Trigger | Guard | Actor |
|---|---|---|---|---|
| draft | in_review | Submit for review | ≥ 1 file | Document Owner |
| in_review | effective | Approve + Submit | approved_by + approval_date set | QMS Officer |
| in_review | draft | Send back | — | QMS Officer |
| effective | superseded | New version effective | supersedes link set | QMS Officer |
| effective | retired | Manual retire | — | QMS Officer |
| effective | expired | Scheduler daily | now > effective_until | System (auto) |

**docstatus:** 0 (draft/in_review), 1 (effective/superseded/retired/expired), 2 (cancelled)

### Hooks

**before_insert:** [TBD - cần làm rõ]

**before_save:** Validate QMS tier nếu is_qms_artifact; validate approved_by trước effective.

**on_submit (effective):** Retire bản cũ cùng scope + document_type (BR-IMM05-004); nếu is_qms_artifact = 1 → tạo/link QMS Artifact record.

**on_cancel:** [TBD - cần làm rõ: không cho cancel Document Record đã effective?]

**Scheduled job (daily):** Kiểm tra `effective_until` → set `status = expired`; sinh notification cho Document Owner + QMS Officer.

### Permissions

| Role | Read | Write | Create | Submit | Cancel | Amend |
|---|---|---|---|---|---|---|
| AssetCore HTM Manager | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| AssetCore Biomed Engineer | ✓ | ✓ | ✓ | — | — | — |
| AssetCore QMS Officer | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| AssetCore Department Head | ✓ | — | — | — | — | — |
| AssetCore Operator | ✓ | — | — | — | — | — |
| AssetCore Auditor | ✓ | — | — | — | — | — |

---

## 10. QMS Artifact

**Module:** `document_qms` — phục vụ IMM-05, QMS layer  
**Type:** Document  
**Linked to ERPNext:** `DocType` (dynamic scope), `User`  
**Naming rule:** `QMS-.YYYY.-.\#\#\#\#\#`  
**Title field:** `name`  
**Is Submittable:** Yes  
**Lifecycle Events triggered:** [TBD - cần làm rõ: sinh Lifecycle Event khi QMS Artifact effective không?]

### Fields

| fieldname | label | fieldtype | options/link | mandatory | default | description |
|---|---|---|---|---|---|---|
| document_record | Document Record | Link | Document Record | Yes (unique) | — | 1-1 với Document Record |
| qms_tier | QMS Tier | Select | QC / PR-SOP / WI-JD / BM-HS-KPI | Yes | — | Tầng QMS (4 tầng) |
| scope | Scope | Select | global / department / asset_category / device_model / asset | Yes | — | Phạm vi áp dụng |
| scope_doctype | Scope DocType | Link | DocType | No | — | Tuỳ scope |
| scope_doc | Scope Doc | Dynamic Link | scope_doctype | No | — | Bản ghi cụ thể |
| mandatory_for_roles | Mandatory For Roles | Table | QMS Mandatory Role | No | — | Role bắt buộc đọc/đào tạo |
| required_training | Required Training | Check | — | No | 0 | Có yêu cầu training khi MAJOR change |
| review_frequency_months | Review Frequency (months) | Int | — | No | — | Chu kỳ review tài liệu |
| next_review_date | Next Review Date | Date | — | No | — | Auto tính từ review_frequency_months |

### Validations

```python
# validate()
# 1-1 unique với Document Record
if frappe.db.exists("QMS Artifact", {
    "document_record": self.document_record,
    "name": ("!=", self.name)
}):
    frappe.throw("Document Record này đã có QMS Artifact liên kết")

if self.scope in ("department", "asset_category", "device_model", "asset"):
    if not self.scope_doctype or not self.scope_doc:
        frappe.throw("scope_doctype và scope_doc bắt buộc với scope này")

if self.review_frequency_months and not self.next_review_date:
    from frappe.utils import add_months, today
    self.next_review_date = add_months(today(), self.review_frequency_months)
```

### Workflow

**States:** [TBD - cần làm rõ: QMS Artifact có workflow riêng hay inherit từ Document Record?]

**Transitions:** [TBD - cần làm rõ]

### Hooks

**before_insert:** Validate 1-1 với Document Record.

**before_save:** Auto-fill `next_review_date` nếu `review_frequency_months` thay đổi.

**on_submit:** [TBD - cần làm rõ]

**on_cancel:** [TBD - cần làm rõ]

**Scheduled job (daily):** Kiểm tra `next_review_date` → sinh notification review cho mandatory_for_roles.

### Permissions

| Role | Read | Write | Create | Submit | Cancel | Amend |
|---|---|---|---|---|---|---|
| AssetCore HTM Manager | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| AssetCore QMS Officer | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| AssetCore Biomed Engineer | ✓ | — | — | — | — | — |
| AssetCore Department Head | ✓ | — | — | — | — | — |
| AssetCore Auditor | ✓ | — | — | — | — | — |

---

## 11. Lifecycle Event

**Module:** `lifecycle` — cross-module (tất cả IMM)  
**Type:** Document (**Append-only** — không cho update sau insert)  
**Linked to ERPNext:** `DocType` (dynamic source), `User`  
**Naming rule:** `LCE-.YYYY.-.\#\#\#\#\#\#`  
**Title field:** `name`  
**Is Submittable:** No  
**Lifecycle Events triggered:** N/A (chính là engine sinh event)

### Fields

| fieldname | label | fieldtype | options/link | mandatory | default | description |
|---|---|---|---|---|---|---|
| medical_asset | Medical Asset | Link | Medical Asset | Yes | — | Asset liên quan |
| event_type | Event Type | Select | need_registered / procurement_approved / installed / commissioned / released_for_use / in_use / pm_completed / failure_reported / repaired / calibration_completed / recalled / transferred / retired / disposed / donated / wo_cancelled / state_changed / imported_legacy / [TBD - danh sách đầy đủ] | Yes | — | Loại lifecycle event |
| event_at | Event At | Datetime | — | Yes | — | Thời điểm xảy ra event |
| actor | Actor | Link | User | No | — | Người gây ra event (nếu có) |
| source_doctype | Source DocType | Link | DocType | No | — | DocType nguồn sinh event |
| source_doc | Source Doc | Dynamic Link | source_doctype | No | — | Bản ghi nguồn |
| payload_json | Payload (JSON) | Long Text | — | No | — | Chi tiết structured (JSON schema validated) |
| state_before | State Before | Data | — | No | — | Asset state trước event |
| state_after | State After | Data | — | No | — | Asset state sau event |
| reason_code | Reason Code | Data | — | No | — | Mã lý do (nếu có) |
| notes | Notes | Small Text | — | No | — | Ghi chú |

### Validations

```python
# validate() — append-only enforcement
if not self.is_new():
    frappe.throw("Lifecycle Event là append-only; không được sửa sau khi tạo")

# JSON Schema validation cho payload_json
if self.payload_json:
    import json
    try:
        json.loads(self.payload_json)
    except json.JSONDecodeError:
        frappe.throw("payload_json phải là JSON hợp lệ")
```

### Workflow

**States:** N/A — không có workflow; chỉ insert, không update/delete.

**Transitions:** N/A

### Hooks

**before_insert:** Validate payload_json là JSON hợp lệ; enforce append-only.

**before_save:** Nếu `self.flags.ignore_permissions` không set và không phải `is_new()` → raise ValidationError.

**on_submit:** N/A (không submittable)

**on_cancel:** N/A

### Permissions

| Role | Read | Write | Create | Submit | Cancel | Amend |
|---|---|---|---|---|---|---|
| AssetCore HTM Manager | ✓ | — | — | — | — | — |
| AssetCore Auditor | ✓ | — | — | — | — | — |
| System (API only) | — | — | ✓ (via hook) | — | — | — |
| AssetCore Biomed Engineer | [TBD - cần làm rõ] | — | — | — | — | — |
| AssetCore QMS Officer | ✓ | — | — | — | — | — |

---

## 12. Compliance Record

**Module:** `compliance` — phục vụ IMM-05, IMM-10, IMM-16  
**Type:** Document  
**Linked to ERPNext:** Không trực tiếp  
**Naming rule:** `CR-.YYYY.-.\#\#\#\#\#`  
**Title field:** `name`  
**Is Submittable:** No  
**Lifecycle Events triggered:** [TBD - cần làm rõ: sinh Lifecycle Event khi status đổi sang expired không?]

### Fields

| fieldname | label | fieldtype | options/link | mandatory | default | description |
|---|---|---|---|---|---|---|
| medical_asset | Medical Asset | Link | Medical Asset | Yes | — | Asset cần theo dõi compliance |
| document_type | Document Type | Link | Document Type | Yes | — | Loại hồ sơ pháp lý |
| document_record | Document Record | Link | Document Record | No | — | Hồ sơ hiện hành |
| status | Status | Select | compliant / expiring_soon / expired / missing / exempted | Yes | missing | Trạng thái compliance |
| valid_from | Valid From | Date | — | No | — | Hiệu lực từ |
| valid_until | Valid Until | Date | — | No | — | Ngày hết hạn |
| last_checked_at | Last Checked At | Datetime | — | No | — | Auto khi scheduler chạy |
| notes | Notes | Small Text | — | No | — | Ghi chú |

### Validations

```python
# validate()
if self.valid_until and self.valid_from and self.valid_until <= self.valid_from:
    frappe.throw("valid_until phải sau valid_from")

# DQ-COMP-002 (kiểm từ scheduler hoặc Medical Asset validate)
# Class C/D asset phải có ≥ 1 Compliance Record loại LIC-MOH-REG compliant
```

### Workflow

**States:** N/A (không có workflow state machine — status được auto-update bởi scheduler)

**Transitions:** N/A

### Hooks

**before_insert:** [TBD - cần làm rõ]

**before_save:** [TBD - cần làm rõ]

**on_submit:** N/A (không submittable)

**on_cancel:** N/A

**Scheduled job (daily):**
```python
for cr in frappe.get_all("Compliance Record", filters={"status": ("not in", ["exempted"])}):
    doc = frappe.get_doc("Compliance Record", cr.name)
    today = getdate()
    if not doc.valid_until:
        doc.status = "missing"
    elif doc.valid_until < today:
        doc.status = "expired"
    elif doc.valid_until <= add_days(today, 30):
        doc.status = "expiring_soon"
    else:
        doc.status = "compliant"
    doc.last_checked_at = now_datetime()
    doc.save(ignore_permissions=True)
    # Sinh notification nếu expiring_soon hoặc expired
```

### Permissions

| Role | Read | Write | Create | Submit | Cancel | Amend |
|---|---|---|---|---|---|---|
| AssetCore HTM Manager | ✓ | ✓ | ✓ | — | — | — |
| AssetCore Biomed Engineer | ✓ | ✓ | ✓ | — | — | — |
| AssetCore QMS Officer | ✓ | ✓ | ✓ | — | — | — |
| AssetCore Department Head | ✓ | — | — | — | — | — |
| AssetCore Auditor | ✓ | — | — | — | — | — |

---

## 13. Compliance Case

**Module:** `compliance` — phục vụ IMM-12, IMM-16  
**Type:** Document  
**Linked to ERPNext:** `User`  
**Naming rule:** `CC-.YYYY.-.\#\#\#\#\#`  
**Title field:** `name`  
**Is Submittable:** Yes  
**Lifecycle Events triggered:** `compliance_case_opened`, `compliance_case_resolved`

### Fields

| fieldname | label | fieldtype | options/link | mandatory | default | description |
|---|---|---|---|---|---|---|
| title | Title | Data | — | Yes | — | Tóm tắt case |
| case_type | Case Type | Select | adverse_event / audit_finding / license_breach / recall / other | Yes | — | Loại case |
| severity | Severity | Select | high / medium / low | Yes | — | Mức độ nghiêm trọng |
| medical_asset | Medical Asset | Link | Medical Asset | No | — | Nếu liên quan asset cụ thể |
| opened_at | Opened At | Datetime | — | Yes | — | Thời điểm mở case |
| opened_by | Opened By | Link | User | Yes | — | Người mở case |
| assigned_to | Assigned To | Link | User | No | — | Người xử lý |
| state | State | Select | open / investigating / awaiting_capa / resolved / closed | Yes | open | Workflow state |
| root_cause_analysis | RCA | Link | Root Cause Analysis | No | — | Phân tích nguyên nhân gốc |
| linked_capa | Linked CAPA | Link | CAPA Case | No | — | CAPA phát sinh |
| evidences | Evidences | Table | Document Record Link | No | — | Hồ sơ bằng chứng |
| resolution_summary | Resolution Summary | Text Editor | — | No | — | Tóm tắt giải quyết |
| closed_at | Closed At | Datetime | — | No | — | Thời điểm đóng |
| closed_by | Closed By | Link | User | No | — | Người đóng |

### Validations

```python
# validate()
# BR-IMM12-002: severity=high → require RCA trong 7 ngày
if self.severity == "high" and not self.root_cause_analysis:
    days_open = date_diff(today(), self.opened_at)
    if days_open > 7:
        frappe.throw("Compliance Case severity HIGH phải có RCA trong 7 ngày (BR-IMM12-002)")
```

### Workflow

**States:** `open` → `investigating` → `awaiting_capa` → `resolved` → `closed`

**Transitions:**

| From | To | Trigger | Guard | Actor |
|---|---|---|---|---|
| open | investigating | Assign to investigator | assigned_to set | QMS Officer / HTM Manager |
| investigating | awaiting_capa | RCA complete | root_cause_analysis linked | QMS Officer |
| awaiting_capa | resolved | CAPA closed effective | linked_capa.state = closed | HTM Manager / QMS Officer |
| resolved | closed | Final close | resolution_summary set | HTM Manager |

### Hooks

**before_insert:** [TBD - cần làm rõ]

**before_save:** Validate RCA requirement cho severity=high.

**on_submit:** Sinh Lifecycle Event `compliance_case_opened`.

**on_cancel:** [TBD - cần làm rõ]

### Permissions

| Role | Read | Write | Create | Submit | Cancel | Amend |
|---|---|---|---|---|---|---|
| AssetCore HTM Manager | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| AssetCore QMS Officer | ✓ | ✓ | ✓ | ✓ | — | — |
| AssetCore Biomed Engineer | ✓ | ✓ | — | — | — | — |
| AssetCore Auditor | ✓ | — | — | — | — | — |

---

## 14. CAPA Case

**Module:** `capa` — phục vụ IMM-12  
**Type:** Document  
**Linked to ERPNext:** `User`  
**Naming rule:** `CAPA-.YYYY.-.\#\#\#\#\#`  
**Title field:** `name`  
**Is Submittable:** Yes  
**Lifecycle Events triggered:** `capa_opened`, `capa_closed`

### Fields

| fieldname | label | fieldtype | options/link | mandatory | default | description |
|---|---|---|---|---|---|---|
| title | Title | Data | — | Yes | — | Tóm tắt CAPA |
| compliance_case | From Compliance Case | Link | Compliance Case | No | — | Compliance Case nguồn |
| medical_asset | Medical Asset | Link | Medical Asset | No | — | Nếu liên quan asset |
| device_model | Device Model | Link | Device Model | No | — | Nếu áp dụng cho cả model |
| opened_at | Opened At | Datetime | — | Yes | — | Thời điểm mở |
| owner_user | CAPA Owner | Link | User | Yes | — | Người chịu trách nhiệm |
| due_date | Due Date | Date | — | Yes | — | Hạn hoàn thành; ≤ 90 ngày cho preventive |
| state | State | Select | open / in_action / awaiting_eff_check / closed / reopened | Yes | open | Workflow state |
| actions | Actions | Table | CAPA Action | Yes | — | Danh sách hành động; ≥ 1 |
| effectiveness_check | Effectiveness Check | Link | CAPA Effectiveness Check | No | — | Kết quả kiểm tra hiệu quả |
| closed_at | Closed At | Datetime | — | No | — | Thời điểm đóng |
| closure_summary | Closure Summary | Text Editor | — | No | — | Tóm tắt đóng CAPA |

### Validations

```python
# validate()
# BR-IMM12-003: ≥ 1 action
if not self.actions:
    frappe.throw("CAPA Case phải có ít nhất 1 action (BR-IMM12-003)")

# BR-IMM12-004: due_date ≤ 90 ngày cho preventive
action_types = [a.action_type for a in self.actions]
if "preventive" in action_types:
    if date_diff(self.due_date, self.opened_at) > 90:
        frappe.throw("due_date không được quá 90 ngày cho preventive CAPA (BR-IMM12-004)")
```

### Workflow

**States:** `open` → `in_action` → `awaiting_eff_check` → `closed` ↔ `reopened`

**Transitions:**

| From | To | Trigger | Guard | Actor |
|---|---|---|---|---|
| open | in_action | Start actions | ≥ 1 action defined | CAPA Owner |
| in_action | awaiting_eff_check | All actions completed | — | CAPA Owner |
| awaiting_eff_check | closed | Effectiveness check passed | effectiveness_check.conclusion = effective | QMS Officer / HTM Manager |
| awaiting_eff_check | reopened | Effectiveness check failed | effectiveness_check.conclusion = not_effective | QMS Officer |
| reopened | in_action | Restart actions | — | CAPA Owner |

### Hooks

**before_insert:** [TBD - cần làm rõ]

**before_save:** Validate ≥ 1 action; validate due_date.

**on_submit:** Sinh Lifecycle Event `capa_opened`.

**on_cancel:** [TBD - cần làm rõ: điều kiện cancel CAPA?]

### Permissions

| Role | Read | Write | Create | Submit | Cancel | Amend |
|---|---|---|---|---|---|---|
| AssetCore HTM Manager | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| AssetCore QMS Officer | ✓ | ✓ | ✓ | ✓ | — | — |
| AssetCore Biomed Engineer | ✓ | ✓ | — | — | — | — |
| AssetCore Auditor | ✓ | — | — | — | — | — |

---

## 15. Asset Audit Log

**Module:** `audit` — cross-module  
**Type:** Document (**Append-only, hash-chained** — không cho update/delete)  
**Linked to ERPNext:** `User`  
**Naming rule:** `AAL-.YYYY.-.\#\#\#\#\#\#\#`  
**Title field:** `name`  
**Is Submittable:** No  
**Lifecycle Events triggered:** N/A

### Fields

| fieldname | label | fieldtype | options/link | mandatory | default | description |
|---|---|---|---|---|---|---|
| doctype_name | DocType | Data | — | Yes | — | Tên DocType được log |
| doc_name | Doc Name | Data | — | Yes | — | Tên bản ghi được log |
| action | Action | Select | create / update / submit / cancel / delete / state_change / permission_change | Yes | — | Loại hành động |
| actor | Actor | Link | User | Yes | — | Người thực hiện |
| action_at | Action At | Datetime | — | Yes | — | Thời điểm |
| before_json | Before (JSON) | Long Text | — | No | — | Snapshot trạng thái trước |
| after_json | After (JSON) | Long Text | — | No | — | Snapshot trạng thái sau |
| ip_address | IP Address | Data | — | No | — | IP của người thực hiện |
| session_id | Session ID | Data | — | No | — | Session ID |
| entry_hash | Entry Hash | Data (read-only) | — | Yes | — | SHA-256 của (prev_hash + payload) |
| prev_hash | Previous Hash | Data (read-only) | — | No | — | Hash của entry trước (hash chain) |
| chain_index | Chain Index | Int | — | Yes | — | Số thứ tự trong chain |

### Validations

```python
# before_insert()
import hashlib, json

# Tính prev_hash: lấy entry cuối cùng
last_entry = frappe.db.get_value("Asset Audit Log",
    {"doctype_name": self.doctype_name},
    ["entry_hash", "chain_index"],
    order_by="chain_index desc"
)
self.prev_hash = last_entry[0] if last_entry else "0" * 64
self.chain_index = (last_entry[1] + 1) if last_entry else 1

payload = json.dumps({
    "doctype_name": self.doctype_name,
    "doc_name": self.doc_name,
    "action": self.action,
    "actor": self.actor,
    "action_at": str(self.action_at),
    "after_json": self.after_json
}, sort_keys=True)
self.entry_hash = hashlib.sha256((self.prev_hash + payload).encode()).hexdigest()

# validate() — append-only
if not self.is_new():
    frappe.throw("Asset Audit Log là append-only; không được sửa sau khi tạo")
```

### Workflow

**States:** N/A — không có workflow.

**Transitions:** N/A

### Hooks

**before_insert:** Tính `prev_hash`, `chain_index`, `entry_hash` (SHA-256).

**before_save:** Nếu không phải `is_new()` → raise ValidationError (append-only).

**on_submit:** N/A

**on_cancel:** N/A

### Permissions

| Role | Read | Write | Create | Submit | Cancel | Amend |
|---|---|---|---|---|---|---|
| AssetCore HTM Manager | ✓ | — | — | — | — | — |
| AssetCore Auditor | ✓ | — | — | — | — | — |
| AssetCore QMS Officer | ✓ | — | — | — | — | — |
| System (hooks only) | — | — | ✓ | — | — | — |

---

## 16. Metric Definition

**Module:** `metric` — phục vụ IMM-07, IMM-17  
**Type:** Document  
**Linked to ERPNext:** `User`  
**Naming rule:** `MET-{metric_code}`  
**Title field:** `name`  
**Is Submittable:** No  
**Lifecycle Events triggered:** N/A

### Fields

| fieldname | label | fieldtype | options/link | mandatory | default | description |
|---|---|---|---|---|---|---|
| metric_code | Metric Code | Data | — | Yes (unique) | — | Mã metric (uptime_30d, mtbf_90d, …) |
| metric_name | Metric Name | Data | — | Yes | — | Tên đầy đủ |
| category | Category | Select | operational / clinical / compliance / financial / quality | Yes | — | Danh mục metric |
| unit | Unit | Data | — | Yes | — | Đơn vị (%, hours, count) |
| scope | Scope | Select | asset / department / asset_category / global | Yes | — | Phạm vi tính |
| calc_logic_md | Calculation Logic (Markdown) | Text Editor | — | Yes | — | Mô tả công thức (Markdown) |
| calc_function | Calc Function (Python path) | Data | — | Yes | — | Module:function (vd: assetcore.metrics.uptime.calc) |
| snapshot_freq | Snapshot Frequency | Select | hourly / daily / weekly / monthly | Yes | — | Tần suất chạy snapshot |
| owner_user | Metric Owner | Link | User | Yes | — | Người chịu trách nhiệm metric |
| target_value | Target | Float | — | No | — | Mục tiêu (để so sánh dashboard) |
| alert_threshold | Alert Threshold | Float | — | No | — | Ngưỡng cảnh báo |
| lineage_md | Data Lineage (Markdown) | Text Editor | — | Yes | — | Mô tả truy về DocType nguồn |

### Validations

```python
# validate()
if frappe.db.exists("Metric Definition", {"metric_code": self.metric_code, "name": ("!=", self.name)}):
    frappe.throw("metric_code phải unique")

# Validate calc_function format: "module:function"
if ":" not in (self.calc_function or ""):
    frappe.throw("calc_function phải theo format 'module:function'")
```

### Workflow

**States:** [TBD - cần làm rõ: không có workflow trong tài liệu gốc]

**Transitions:** [TBD - cần làm rõ]

### Hooks

**before_insert:** [TBD - cần làm rõ]

**before_save:** Validate `metric_code` unique; validate `calc_function` format.

**on_submit:** N/A (không submittable)

**on_cancel:** N/A

### Permissions

| Role | Read | Write | Create | Submit | Cancel | Amend |
|---|---|---|---|---|---|---|
| AssetCore HTM Manager | ✓ | ✓ | ✓ | — | — | — |
| AssetCore QMS Officer | ✓ | ✓ | ✓ | — | — | — |
| AssetCore Biomed Engineer | ✓ | — | — | — | — | — |
| AssetCore Auditor | ✓ | — | — | — | — | — |
| AssetCore Department Head | ✓ | — | — | — | — | — |

---

## 17. Metric Snapshot

**Module:** `metric` — phục vụ IMM-07, IMM-17  
**Type:** Document (**Append-only** — generated by scheduled job)  
**Linked to ERPNext:** `DocType` (dynamic scope)  
**Naming rule:** `SNP-.YYYY.-.\#\#\#\#\#\#`  
**Title field:** `name`  
**Is Submittable:** No  
**Lifecycle Events triggered:** N/A

### Fields

| fieldname | label | fieldtype | options/link | mandatory | default | description |
|---|---|---|---|---|---|---|
| metric_definition | Metric | Link | Metric Definition | Yes | — | Metric được chụp |
| scope_doctype | Scope DocType | Link | DocType | No | — | Phạm vi scope |
| scope_doc | Scope Doc | Dynamic Link | scope_doctype | No | — | Bản ghi cụ thể trong scope |
| snapshot_at | Snapshot At | Datetime | — | Yes | — | Thời điểm snapshot |
| value | Value | Float | — | Yes | — | Giá trị tính được |
| meta_json | Meta (JSON) | Long Text | — | No | — | Metadata tính toán (bộ phận) |

### Validations

```python
# validate()
if not self.is_new():
    frappe.throw("Metric Snapshot là append-only; không được sửa sau khi tạo")
```

### Workflow

**States:** N/A

**Transitions:** N/A

### Hooks

**before_insert:** [TBD - cần làm rõ: validate JSON format cho meta_json?]

**before_save:** Append-only enforcement.

**on_submit:** N/A

**on_cancel:** N/A

**Scheduled jobs:** Theo `snapshot_freq` trong Metric Definition (hourly/daily/weekly/monthly): gọi `calc_function`, tạo Metric Snapshot record mới; cập nhật read-only fields trên Medical Asset (uptime_30d, mtbf_90d, mttr_90d).

### Permissions

| Role | Read | Write | Create | Submit | Cancel | Amend |
|---|---|---|---|---|---|---|
| AssetCore HTM Manager | ✓ | — | — | — | — | — |
| AssetCore QMS Officer | ✓ | — | — | — | — | — |
| AssetCore Auditor | ✓ | — | — | — | — | — |
| AssetCore Department Head | ✓ | — | — | — | — | — |
| System (scheduled job) | — | — | ✓ | — | — | — |

---

## 18. AC Work Order Task

**Module:** `work_order`  
**Type:** Child (of AC Work Order)  
**Linked to ERPNext:** `User`  
**Lifecycle Events triggered:** N/A

### Fields

| fieldname | label | fieldtype | options/link | mandatory | default | description |
|---|---|---|---|---|---|---|
| task_text | Task | Data | — | Yes | — | Mô tả bước công việc |
| completed | Completed | Check | — | No | 0 | Đã hoàn thành chưa |
| completed_by | Completed By | Link | User | No | — | Người hoàn thành |
| completed_at | Completed At | Datetime | — | No | — | Thời điểm hoàn thành |
| result_pass_fail | Result | Select | pass / fail / n_a | No | — | Kết quả bước này |
| notes | Notes | Small Text | — | No | — | Ghi chú bước |

### Validations

```python
# validate() — trong context parent AC Work Order
if self.completed and not self.completed_by:
    frappe.throw("completed_by bắt buộc khi task marked completed")
if self.completed and not self.completed_at:
    self.completed_at = now_datetime()
```

### Workflow / Hooks / Permissions

[TBD - cần làm rõ: child table không có workflow độc lập; permissions kế thừa từ parent AC Work Order]

---

## 19. AC Spare Consumption

**Module:** `work_order`  
**Type:** Child (of AC Work Order)  
**Linked to ERPNext:** `Item`, `Warehouse`, `Stock Entry`  
**Lifecycle Events triggered:** N/A

### Fields

| fieldname | label | fieldtype | options/link | mandatory | default | description |
|---|---|---|---|---|---|---|
| item | Item | Link | Item | Yes | — | Phụ tùng sử dụng |
| qty | Quantity | Float | — | Yes | — | Số lượng |
| warehouse | Warehouse | Link | Warehouse | Yes | — | Kho xuất |
| stock_entry | Stock Entry | Link | Stock Entry | No | — | Stock Entry sinh từ việc xuất kho thật |
| unit_cost | Unit Cost | Currency | — | No | — | Đơn giá (auto từ Item) |
| total_cost | Total Cost | Currency | — | No | — | qty × unit_cost |
| returned_qty | Returned Qty | Float | — | No | 0 | Số lượng hoàn trả |

### Validations

```python
# validate()
if self.qty <= 0:
    frappe.throw("qty phải > 0")
self.total_cost = self.qty * (self.unit_cost or 0)
```

### Workflow / Hooks / Permissions

[TBD - cần làm rõ: Stock Entry được tạo tự động khi WO submit hay phải tạo thủ công? Cần spec rõ flow stock movement]

---

## 20. Document Record Link

**Module:** `document_qms`  
**Type:** Child (of AC Work Order, Initial Inspection, Compliance Case, CAPA Case, v.v.)  
**Linked to ERPNext:** Không  
**Lifecycle Events triggered:** N/A

### Fields

| fieldname | label | fieldtype | options/link | mandatory | default | description |
|---|---|---|---|---|---|---|
| document_record | Document Record | Link | Document Record | Yes | — | Tài liệu đính kèm |
| evidence_type | Evidence Type | Select | photo / video / report / certificate / log / other | No | — | Loại bằng chứng |
| notes | Notes | Small Text | — | No | — | Ghi chú về tài liệu này |

### Validations / Workflow / Hooks / Permissions

[TBD - cần làm rõ: child table đơn giản; permissions kế thừa từ parent]

---

## 21. Document File

**Module:** `document_qms`  
**Type:** Child (of Document Record)  
**Linked to ERPNext:** Không  
**Lifecycle Events triggered:** N/A

### Fields

| fieldname | label | fieldtype | options/link | mandatory | default | description |
|---|---|---|---|---|---|---|
| file | File | Attach | — | Yes | — | File đính kèm |
| file_type | File Type | Select | pdf / docx / xlsx / jpg / png / mp4 / other | No | — | Loại file |
| capture_date | Capture Date | Date | — | No | — | Ngày tạo/chụp file |
| language | Language | Select | vi / en / vi+en | No | — | Ngôn ngữ file |

### Validations / Workflow / Hooks / Permissions

[TBD - cần làm rõ: kế thừa từ parent Document Record]

---

## 22. Document Distribution

**Module:** `document_qms`  
**Type:** Child (of Document Record)  
**Linked to ERPNext:** `User`, `Role`  
**Lifecycle Events triggered:** N/A

### Fields

| fieldname | label | fieldtype | options/link | mandatory | default | description |
|---|---|---|---|---|---|---|
| user | User | Link | User | No | — | Cá nhân nhận |
| role | Role | Link | Role | No | — | Role nhận (nếu không chỉ định cá nhân) |
| group | Group | Data | — | No | — | Nhóm nhận [TBD - cần làm rõ: link tới DocType nào?] |
| acknowledged_at | Acknowledged At | Datetime | — | No | — | Thời điểm xác nhận đã đọc |

### Validations / Workflow / Hooks / Permissions

[TBD - cần làm rõ: cơ chế ghi nhận acknowledge như thế nào? Email link hay button trên form?]

---

## 23. Maintenance Plan Task

**Module:** `maintenance_plan`  
**Type:** Child (of Maintenance Plan)  
**Linked to ERPNext:** Không  
**Lifecycle Events triggered:** N/A

### Fields

| fieldname | label | fieldtype | options/link | mandatory | default | description |
|---|---|---|---|---|---|---|
| task_text | Task | Data | — | Yes | — | Mô tả bước PM |
| default_duration | Default Duration (min) | Int | — | No | — | Thời gian dự kiến bước này |
| required_skill | Required Skill | Data | — | No | — | Kỹ năng cần [TBD - cần làm rõ: link tới DocType kỹ năng không?] |
| sop_reference | SOP Reference | Link | QMS Artifact | No | — | SOP/WI cho bước này |

### Validations / Workflow / Hooks / Permissions

[TBD - cần làm rõ: kế thừa từ parent Maintenance Plan]

---

## 24. Maintenance Plan Spare

**Module:** `maintenance_plan`  
**Type:** Child (of Maintenance Plan)  
**Linked to ERPNext:** `Item`  
**Lifecycle Events triggered:** N/A

### Fields

| fieldname | label | fieldtype | options/link | mandatory | default | description |
|---|---|---|---|---|---|---|
| item | Item | Link | Item | Yes | — | Phụ tùng dự kiến |
| default_qty | Default Qty | Float | — | Yes | — | Số lượng dự kiến mỗi PM |
| optional | Optional | Check | — | No | 0 | Có thể không cần |

### Validations / Workflow / Hooks / Permissions

[TBD - cần làm rõ: kế thừa từ parent Maintenance Plan]

---

## 25. Calibration Plan Test Point

**Module:** `calibration`  
**Type:** Child (of Calibration Plan)  
**Linked to ERPNext:** Không  
**Lifecycle Events triggered:** N/A

### Fields

| fieldname | label | fieldtype | options/link | mandatory | default | description |
|---|---|---|---|---|---|---|
| point_label | Point Label | Data | — | Yes | — | Nhãn điểm đo (vd: Channel 1, Low Range) |
| expected_value | Expected Value | Float | — | Yes | — | Giá trị chuẩn |
| tolerance | Tolerance | Float | — | Yes | — | Dung sai cho phép |
| unit | Unit | Data | — | Yes | — | Đơn vị đo |

### Validations / Workflow / Hooks / Permissions

[TBD - cần làm rõ: kế thừa từ parent Calibration Plan]

---

## 26. Initial Inspection Item

**Module:** `asset_registry`  
**Type:** Child (of Initial Inspection)  
**Linked to ERPNext:** Không  
**Lifecycle Events triggered:** N/A

### Fields

| fieldname | label | fieldtype | options/link | mandatory | default | description |
|---|---|---|---|---|---|---|
| item_text | Item | Data | — | Yes | — | Mô tả hạng mục kiểm tra |
| expected | Expected | Data | — | No | — | Kết quả mong đợi |
| observed | Observed | Data | — | No | — | Kết quả quan sát thực tế |
| result_pass_fail | Result | Select | pass / fail / n_a | Yes | — | Kết luận hạng mục |
| notes | Notes | Small Text | — | No | — | Ghi chú |

### Validations / Workflow / Hooks / Permissions

[TBD - cần làm rõ: kế thừa từ parent Initial Inspection]

---

## 27. CAPA Action

**Module:** `capa`  
**Type:** Child (of CAPA Case)  
**Linked to ERPNext:** `User`  
**Lifecycle Events triggered:** N/A

### Fields

| fieldname | label | fieldtype | options/link | mandatory | default | description |
|---|---|---|---|---|---|---|
| action_text | Action | Data | — | Yes | — | Mô tả hành động |
| action_type | Action Type | Select | corrective / preventive / containment | Yes | — | Loại hành động |
| owner | Owner | Link | User | Yes | — | Người thực hiện |
| due_date | Due Date | Date | — | Yes | — | Hạn hoàn thành |
| completed_at | Completed At | Datetime | — | No | — | Thời điểm hoàn thành thực tế |
| evidence | Evidence | Attach | — | No | — | Bằng chứng hoàn thành |

### Validations / Workflow / Hooks / Permissions

[TBD - cần làm rõ: kế thừa từ parent CAPA Case]

---

## 28. CAPA Effectiveness Check

**Module:** `capa`  
**Type:** Document  
**Linked to ERPNext:** `User`  
**Naming rule:** [TBD - cần làm rõ]  
**Title field:** `name`  
**Lifecycle Events triggered:** N/A

### Fields

| fieldname | label | fieldtype | options/link | mandatory | default | description |
|---|---|---|---|---|---|---|
| capa | CAPA Case | Link | CAPA Case | Yes | — | CAPA được kiểm tra |
| check_date | Check Date | Date | — | Yes | — | Ngày thực hiện kiểm tra |
| method | Method | Data | — | Yes | — | Phương pháp kiểm tra (audit, observation, data review) |
| conclusion | Conclusion | Select | effective / not_effective / inconclusive | Yes | — | Kết luận |
| notes | Notes | Text Editor | — | No | — | Ghi chú chi tiết |

### Validations

```python
# validate()
if not self.method:
    frappe.throw("method kiểm tra bắt buộc")
```

### Workflow

**States:** `draft` → `completed` [TBD - cần làm rõ]

**Transitions:** [TBD - cần làm rõ]

### Hooks / Permissions

[TBD - cần làm rõ: role nào được tạo Effectiveness Check? QMS Officer?]

---

## 29. Root Cause Analysis

**Module:** `compliance`  
**Type:** Document  
**Linked to ERPNext:** Không  
**Naming rule:** [TBD - cần làm rõ]  
**Title field:** `name`  
**Lifecycle Events triggered:** N/A

### Fields

| fieldname | label | fieldtype | options/link | mandatory | default | description |
|---|---|---|---|---|---|---|
| compliance_case | Compliance Case | Link | Compliance Case | Yes | — | Case liên quan |
| technique | Technique | Select | 5whys / fishbone / fmea / other | Yes | — | Phương pháp RCA |
| conclusion_md | Conclusion | Text Editor | — | Yes | — | Kết luận phân tích nguyên nhân gốc |
| evidence_table | Evidence | Table | Document Record Link | No | — | Hồ sơ bằng chứng RCA |

### Validations

```python
# validate()
if len(self.conclusion_md or "") < 100:
    frappe.throw("conclusion_md phải có ít nhất 100 ký tự [TBD - xác nhận threshold]")
```

### Workflow / Hooks / Permissions

[TBD - cần làm rõ: ai được submit RCA? QMS Officer hay HTM Manager?]

---

## 30. Adverse Event Report

**Module:** `compliance`  
**Type:** Document  
**Linked to ERPNext:** `User`, `Medical Asset`  
**Naming rule:** [TBD - cần làm rõ]  
**Title field:** `name`  
**Is Submittable:** [TBD - cần làm rõ]  
**Lifecycle Events triggered:** `adverse_event_reported`

### Fields

| fieldname | label | fieldtype | options/link | mandatory | default | description |
|---|---|---|---|---|---|---|
| medical_asset | Medical Asset | Link | Medical Asset | Yes | — | Asset liên quan |
| reported_at | Reported At | Datetime | — | Yes | — | Thời điểm xảy ra |
| severity_clinical | Clinical Severity | Select | [TBD - cần làm rõ: scale cụ thể] | Yes | — | Mức độ lâm sàng |
| patient_outcome | Patient Outcome | Select | [TBD - cần làm rõ: near_miss / minor_harm / serious_harm / death] | Yes | — | Hậu quả với bệnh nhân |
| narrative | Narrative | Text Editor | — | Yes | — | Mô tả sự cố chi tiết |
| reported_to_authority | Reported to Authority | Check | — | No | 0 | Đã báo cáo cơ quan quản lý |
| authority_ref_no | Authority Reference No | Data | — | No | — | Số tham chiếu từ cơ quan quản lý |

### Validations / Workflow

[TBD - cần làm rõ: quy trình báo cáo cơ quan chức năng (Bộ Y tế) được trigger như thế nào? SLA báo cáo bao nhiêu ngày?]

### Hooks

**on_submit:** Tạo `Compliance Case` linked với `case_type = adverse_event`.

### Permissions

[TBD - cần làm rõ: ai được tạo Adverse Event Report? Chỉ Biomed Engineer/HTM Manager hay cả Operator?]

---

## 31. Recall Notice

**Module:** `corrective` [TBD - cần làm rõ: module chính xác]  
**Type:** Document  
**Linked to ERPNext:** `Supplier` (Vendor), `Device Model`  
**Naming rule:** [TBD - cần làm rõ]  
**Title field:** `name`  
**Lifecycle Events triggered:** `recalled`

### Fields

| fieldname | label | fieldtype | options/link | mandatory | default | description |
|---|---|---|---|---|---|---|
| vendor | Vendor | Link | Supplier | Yes | — | Nhà cung cấp/nhà sản xuất phát lệnh recall |
| device_model | Device Model | Link | Device Model | Yes | — | Model bị recall |
| scope_assets | Scope Assets | Table | [TBD - cần làm rõ: child table liệt kê Medical Asset bị ảnh hưởng] | No | — | Danh sách asset bị ảnh hưởng |
| severity | Severity | Select | [TBD - cần làm rõ: FSCA severity scale] | Yes | — | Mức độ |
| deadline | Deadline | Date | — | Yes | — | Hạn xử lý |
| source_doc | Source Doc | Data | — | No | — | Tham chiếu văn bản recall từ nhà sản xuất/Bộ Y tế |

### Validations / Workflow / Hooks

[TBD - cần làm rõ: sau khi Recall Notice submit, hệ thống tự tạo Recall WO cho từng asset trong scope_assets không?]

### Permissions

[TBD - cần làm rõ]

---

## 32. Software Update Record

**Module:** `corrective` [TBD - cần làm rõ: hoặc `asset_registry`?]  
**Type:** Document  
**Linked to ERPNext:** `User`  
**Naming rule:** [TBD - cần làm rõ]  
**Title field:** `name`  
**Lifecycle Events triggered:** `software_updated`

### Fields

| fieldname | label | fieldtype | options/link | mandatory | default | description |
|---|---|---|---|---|---|---|
| medical_asset | Medical Asset | Link | Medical Asset | Yes | — | Asset được cập nhật |
| from_version | From Version | Data | — | Yes | — | Phiên bản firmware/software cũ |
| to_version | To Version | Data | — | Yes | — | Phiên bản mới |
| release_note | Release Note | Link | Document Record | No | — | Document Record chứa release notes |
| applied_at | Applied At | Datetime | — | Yes | — | Thời điểm áp dụng |
| applied_by | Applied By | Link | User | Yes | — | Người thực hiện |
| evidence | Evidence | Attach | — | No | — | Bằng chứng cập nhật |

### Validations / Workflow / Hooks / Permissions

[TBD - cần làm rõ: có cần Change Control trước khi apply software update không?]

---

## 33. Service Contract

**Module:** [TBD - cần làm rõ: `vendor_management` hay `corrective`?]  
**Type:** Document  
**Linked to ERPNext:** `Supplier`  
**Naming rule:** [TBD - cần làm rõ]  
**Title field:** `name`  
**Lifecycle Events triggered:** N/A

### Fields

| fieldname | label | fieldtype | options/link | mandatory | default | description |
|---|---|---|---|---|---|---|
| vendor | Vendor | Link | Supplier | Yes | — | Nhà cung cấp dịch vụ kỹ thuật |
| scope_assets | Scope Assets | Table | [TBD - cần làm rõ: child table link Medical Asset] | No | — | Danh sách asset trong phạm vi hợp đồng |
| sla_terms | SLA Terms | Text Editor | — | Yes | — | Điều khoản SLA |
| start_date | Start Date | Date | — | Yes | — | Ngày bắt đầu |
| end_date | End Date | Date | — | Yes | — | Ngày kết thúc |
| value | Contract Value | Currency | — | No | — | Giá trị hợp đồng |
| contract_doc | Contract Document | Link | Document Record | No | — | Hồ sơ hợp đồng |

### Validations

```python
# validate()
if self.end_date <= self.start_date:
    frappe.throw("end_date phải sau start_date")
```

### Workflow / Hooks / Permissions

[TBD - cần làm rõ: có workflow approve hợp đồng không? Ai ký? Scheduler cảnh báo expiry trước bao nhiêu ngày?]

---

## 34. Decommission Record

**Module:** [TBD - cần làm rõ: `end_of_life`?]  
**Type:** Document  
**Linked to ERPNext:** `User`  
**Naming rule:** [TBD - cần làm rõ]  
**Title field:** `name`  
**Is Submittable:** [TBD - cần làm rõ]  
**Lifecycle Events triggered:** `retired`, `disposed`, `donated`

### Fields

| fieldname | label | fieldtype | options/link | mandatory | default | description |
|---|---|---|---|---|---|---|
| medical_asset | Medical Asset | Link | Medical Asset | Yes | — | Asset bị giải nhiệm |
| decision_date | Decision Date | Date | — | Yes | — | Ngày quyết định giải nhiệm |
| method | Method | Select | dispose / donate / store | Yes | — | Phương thức giải nhiệm |
| recipient | Recipient | Data | — | No | — | Đơn vị nhận nếu donate |
| evidence | Evidence | Table | Document Record Link | Yes | — | Hồ sơ bằng chứng giải nhiệm |
| sponsor_signoff | Sponsor Sign-off | Link | User | Yes | — | Người có thẩm quyền ký |

### Validations / Workflow / Hooks

**on_submit:** Set `asset.state → disposed / donated / stored_long_term` theo method; sinh Lifecycle Event tương ứng.

### Permissions

[TBD - cần làm rõ: chỉ HTM Manager + Sponsor có quyền tạo và submit]

---

## 35. Decision Record

**Module:** `governance`  
**Type:** Document  
**Linked to ERPNext:** `User`  
**Naming rule:** [TBD - cần làm rõ]  
**Title field:** `title`  
**Lifecycle Events triggered:** N/A

### Fields

| fieldname | label | fieldtype | options/link | mandatory | default | description |
|---|---|---|---|---|---|---|
| decision_id | Decision ID | Data | — | Yes | — | Mã quyết định |
| title | Title | Data | — | Yes | — | Tiêu đề quyết định |
| context | Context | Text Editor | — | Yes | — | Bối cảnh / vấn đề cần quyết định |
| decision_md | Decision | Text Editor | — | Yes | — | Nội dung quyết định (Markdown) |
| alternatives | Alternatives | Text Editor | — | No | — | Các phương án đã xem xét |
| owner | Owner | Link | User | Yes | — | Người đề xuất |
| signed_by | Signed By | Link | User | Yes | — | Người có thẩm quyền ký |
| signed_at | Signed At | Datetime | — | Yes | — | Thời điểm ký |

### Validations / Workflow / Hooks / Permissions

[TBD - cần làm rõ: Decision Record thuộc Management Review hay độc lập? Có approval workflow không?]

---

## 36. Management Review

**Module:** `governance`  
**Type:** Document  
**Linked to ERPNext:** `User`  
**Naming rule:** [TBD - cần làm rõ]  
**Title field:** `name`  
**Lifecycle Events triggered:** N/A

### Fields

| fieldname | label | fieldtype | options/link | mandatory | default | description |
|---|---|---|---|---|---|---|
| review_date | Review Date | Date | — | Yes | — | Ngày họp review |
| period | Period | Data | — | Yes | — | Kỳ xem xét (vd: Q1-2026) |
| attendees | Attendees | Table | [TBD - cần làm rõ: child table User] | Yes | — | Danh sách người tham dự |
| kpi_snapshot_table | KPI Snapshot Table | Table | [TBD - cần làm rõ: child table hoặc link Metric Snapshot] | No | — | Bảng KPI kỳ này |
| capa_review | CAPA Review | Text Editor | — | No | — | Tóm tắt CAPA đang mở |
| decisions | Decisions | Table | [TBD - cần làm rõ: child table link Decision Record] | No | — | Quyết định từ họp |
| minutes | Minutes | Link | Document Record | No | — | Biên bản họp (Document Record) |

### Validations / Workflow / Hooks / Permissions

[TBD - cần làm rõ: tần suất Management Review? Ai triệu tập? Workflow approve biên bản?]

---

## 37. Change Control

**Module:** `document_qms` [TBD - cần làm rõ: hoặc `governance`?]  
**Type:** Document  
**Linked to ERPNext:** `User`  
**Naming rule:** [TBD - cần làm rõ]  
**Title field:** `title`  
**Is Submittable:** [TBD - cần làm rõ]  
**Lifecycle Events triggered:** N/A

### Fields

| fieldname | label | fieldtype | options/link | mandatory | default | description |
|---|---|---|---|---|---|---|
| title | Title | Data | — | Yes | — | Tiêu đề thay đổi |
| change_type | Change Type | Select | [TBD - cần làm rõ: procedure / document / asset_config / software / process] | Yes | — | Loại thay đổi |
| scope | Scope | Select | asset / document / process | Yes | — | Phạm vi tác động |
| risk_assessment | Risk Assessment | Text Editor | — | Yes | — | Đánh giá rủi ro của thay đổi |
| plan_md | Change Plan | Text Editor | — | Yes | — | Kế hoạch thực hiện thay đổi |
| approver | Approver | Link | User | Yes | — | Người phê duyệt |
| status | Status | Select | draft / under_review / approved / rejected / implemented / cancelled | Yes | draft | Trạng thái |
| effective_date | Effective Date | Date | — | No | — | Ngày thay đổi có hiệu lực |

### Validations / Workflow

**States:** `draft` → `under_review` → `approved` / `rejected` → `implemented` / `cancelled`

**Transitions:** [TBD - cần làm rõ: SLA review Change Control là bao nhiêu ngày? Ai có quyền approve?]

### Hooks / Permissions

[TBD - cần làm rõ: Change Control có trigger notification tới các bên liên quan không?]

---

## Phụ lục: Danh sách [TBD] cần làm rõ theo ưu tiên

### Ưu tiên Cao (Chặn build Wave 1)

| # | DocType | Vấn đề cần làm rõ |
|---|---|---|
| 1 | Medical Asset | `installed_failed` — có phải state chính thức trong machine không? |
| 2 | Medical Asset | Default `calibration_required` cho Risk Class A/B là gì? |
| 3 | Initial Inspection | Xử lý `overall_result = conditional` → asset state nào? |
| 4 | AC Work Order | SLA matrix (severity S1-S4 × criticality → hours) — cần bảng đầy đủ |
| 5 | AC Work Order | `wo_type_short` cho naming rule — định nghĩa mapping (PM→PM, CM→CM…) |
| 6 | AC Spare Consumption | Stock Entry tạo tự động khi WO submit hay thủ công? |
| 7 | Failure Report | Rollback asset.state khi Failure Report bị cancel? |
| 8 | Lifecycle Event | Danh sách đầy đủ `event_type` (enum) — cần chốt trước khi code |

### Ưu tiên Trung bình (Chặn Wave 1 completion)

| # | DocType | Vấn đề cần làm rõ |
|---|---|---|
| 9 | Document Record | Có cho cancel Document Record đã effective không? |
| 10 | QMS Artifact | Có workflow state machine riêng hay inherit từ Document Record? |
| 11 | Compliance Record | Thresholds cảnh báo `expiring_soon`: 30 ngày hay khác nhau theo document_type? |
| 12 | Adverse Event Report | SLA báo cáo cơ quan quản lý: bao nhiêu ngày theo loại sự cố? |
| 13 | Recall Notice | Tự động tạo Recall WO cho từng asset sau khi submit? |
| 14 | CAPA Effectiveness Check | Naming rule, module, permission matrix |

### Ưu tiên Thấp (Wave 2+)

| # | DocType | Vấn đề cần làm rõ |
|---|---|---|
| 15 | Service Contract | Workflow approve hợp đồng, scheduler cảnh báo expiry |
| 16 | Decommission Record | Naming rule và module |
| 17 | Decision Record | Relation với Management Review |
| 18 | Management Review | Tần suất, người triệu tập, workflow approve biên bản |
| 19 | Change Control | SLA review, người approve, notification |
| 20 | Software Update Record | Có cần Change Control trước khi apply không? |

---

*Tài liệu này được sinh tự động từ Tập 3 — Data & DocType Specification v1.0 (2026-05-05). Mọi thay đổi DocType sau khi tài liệu này được phê duyệt phải đi qua Change Control.*
