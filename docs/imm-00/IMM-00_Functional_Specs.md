# IMM-00 — Nền tảng Hệ thống (Foundation Module)
## Functional Specifications

**Module:** IMM-00 | **Version:** 1.0 | **Ngày:** 2026-04-18
**Trạng thái:** Draft — Chờ review

---

## 1. Phạm vi

Tài liệu này mô tả yêu cầu chức năng cho IMM-00, bao gồm: user stories, acceptance criteria, business rules, validation rules, role permission matrix và error messages cho toàn bộ 7 DocType nền tảng của hệ thống AssetCore.

---

## 2. Actors & Roles

| Actor thực tế tại BV | Frappe Role | Trách nhiệm chính |
|---|---|---|
| Trưởng phòng VT,TBYT | IMM Department Head | Phê duyệt, xem toàn bộ, báo cáo |
| PTP Khối 2 (CMMS) | IMM Operations Manager | Phê duyệt WO, xem dashboard, quản lý SLA |
| Trưởng workshop | IMM Workshop Lead | Tạo/phân công WO, approve sửa chữa |
| Kỹ thuật viên TBYT | IMM Technician | Thực hiện WO, cập nhật kết quả |
| Nhân viên hồ sơ | IMM Document Officer | Quản lý hồ sơ, tạo Asset Profile |
| Nhân viên kho | IMM Storekeeper | Xem WO CM, quản lý phụ tùng |
| QLCL / Tổ HC-QLCL | IMM QA Officer | CAPA, audit, compliance, RCA |
| Admin CNTT | IMM System Admin | Toàn quyền, setup master data |

---

## 3. User Stories — IMM Device Model

### US-00-01: Tạo Device Model cho thiết bị y tế mới

```
As an IMM Document Officer
I want to create a new IMM Device Model for a medical device
So that all subsequent commissioning and maintenance activities can reference standardized device specifications
```

**Acceptance Criteria:**
```gherkin
Given I am logged in with role "IMM Document Officer"
When I navigate to IMM Device Model list and click "New"
And I fill in model_name = "SAVINA 300", manufacturer = "Draeger", medical_device_class = "Class III"
And I set pm_interval_days = 90, calibration_interval_days = 365, is_calibration_required = 1
And I click Save
Then a new IMM Device Model is created with naming series IMM-MDL-.YYYY.-.####
And risk_classification is auto-set to "Critical" based on Class III
And I can see the record in IMM Device Model list

Given a Device Model with model_name = "SAVINA 300" and manufacturer = "Draeger" already exists
When I try to create another Device Model with the same model_name + manufacturer combination
Then the system throws: "Model 'SAVINA 300' của nhà sản xuất 'Draeger' đã tồn tại trong hệ thống."
And no record is created
```

### US-00-02: Tìm kiếm Device Model khi commissioning

```
As an IMM Technician
I want to search for a Device Model when creating a Commissioning Record
So that I can quickly find the correct device specifications without re-entering data
```

**Acceptance Criteria:**
```gherkin
Given I am creating an Asset Commissioning Record
When I click on the "Device Model" field
Then I see a search dropdown with fields: model_name, manufacturer, medical_device_class, risk_classification
And I can filter by manufacturer name or device category
And selecting a model auto-populates: pm_interval_days, calibration_required, calibration_interval_days

Given I search for "siemens"
Then the system returns all Device Models where manufacturer contains "Siemens" (case-insensitive)
```

### US-00-03: Cập nhật chu kỳ PM/Calibration khi có thay đổi từ NSX

```
As an IMM Department Head
I want to update PM interval and calibration interval on a Device Model
So that all future PM Schedules and Calibration Schedules created for this device type use the updated intervals
```

**Acceptance Criteria:**
```gherkin
Given a Device Model "GE Venue 40" with pm_interval_days = 180
When I update pm_interval_days to 90
And I save
Then the change is recorded in the document's modified history
And existing IMM PM Schedules linked to this Device Model are NOT automatically changed (only new ones inherit the new value)
And a system alert is shown: "Lưu ý: Thay đổi chu kỳ chỉ áp dụng cho lịch PM/Hiệu chuẩn tạo mới sau thời điểm này."
```

---

## 4. User Stories — IMM Asset Profile

### US-00-04: Tạo Asset Profile sau khi Asset được tạo trong ERPNext

```
As an IMM Document Officer
I want to create an IMM Asset Profile for a newly registered ERPNext Asset
So that the asset has full HTM-specific data including device class, serial number, and lifecycle tracking
```

**Acceptance Criteria:**
```gherkin
Given an ERPNext Asset "ACC-ASS-2026-00001" exists in status "Submitted"
When I navigate to IMM Asset Profile and create a New record
And I link asset = "ACC-ASS-2026-00001" and device_model = "IMM-MDL-2026-00003"
And I enter serial_number_manufacturer = "SN-DRG-2026-0045", imm_asset_code = "NDIH1-TBYT-2026-001"
And I click Save
Then the IMM Asset Profile is created with naming IMM-ASP-.YYYY.-.####
And Asset custom fields are updated:
  - custom_imm_device_model = "IMM-MDL-2026-00003"
  - custom_imm_asset_profile = the new profile name
  - custom_imm_lifecycle_status = "Active"
  - custom_imm_medical_class = (from Device Model)
  - custom_imm_risk_class = (from Device Model)

Given an IMM Asset Profile already exists for "ACC-ASS-2026-00001"
When I try to create another IMM Asset Profile with the same asset
Then the system throws: "Tài sản 'ACC-ASS-2026-00001' đã có Hồ sơ IMM. Mỗi tài sản chỉ có một hồ sơ duy nhất."
```

### US-00-05: Thay đổi lifecycle_status khi thiết bị đưa vào sửa chữa

```
As an IMM Workshop Lead
I want to update lifecycle_status to "Under Repair" when a CM Work Order is created for a device
So that the asset status accurately reflects its current operational state
```

**Acceptance Criteria:**
```gherkin
Given asset "ACC-ASS-2026-00001" has lifecycle_status = "Active"
When I change lifecycle_status to "Under Repair" (via API imm00.update_asset_lifecycle_status)
And provide reason = "CM WO-CM-2026-00012 - Máy thở hỏng nguồn"
Then lifecycle_status in IMM Asset Profile is updated to "Under Repair"
And Asset.custom_imm_lifecycle_status is synced to "Under Repair"
And an IMM Audit Trail entry is created:
  - event_type = "State Change"
  - from_status = "Active"
  - to_status = "Under Repair"
  - actor = current user
  - remarks = "CM WO-CM-2026-00012 - Máy thở hỏng nguồn"
```

### US-00-06: Decommission thiết bị và đình chỉ lịch PM/Calibration

```
As an IMM Department Head
I want to decommission an asset
So that all related PM and Calibration schedules are automatically suspended and no new WOs are created
```

**Acceptance Criteria:**
```gherkin
Given asset "ACC-ASS-2026-00001" has lifecycle_status = "Active"
And has 2 active IMM PM Schedules and 1 active IMM Calibration Schedule
When I update lifecycle_status to "Decommissioned"
Then all linked IMM PM Schedules have status set to "Suspended"
And all linked IMM Calibration Schedules have status set to "Suspended"
And IMM Audit Trail entry is created for each status change
And Asset.status (ERPNext) is set to "Out of Order" if not already Scrapped/Sold
And no new PM WO or Calibration Record can be created for this asset
```

---

## 5. User Stories — IMM Vendor Profile

### US-00-07: Ghi nhận chứng nhận ISO/IEC 17025 của tổ chức hiệu chuẩn

```
As an IMM Document Officer
I want to mark a Supplier as ISO/IEC 17025 certified
So that the system knows this vendor can perform accredited external calibrations
```

**Acceptance Criteria:**
```gherkin
Given a Supplier "Viện Đo lường Việt Nam" exists in ERPNext
When I create an IMM Vendor Profile for this supplier
And set vendor_type = "Service Agent", iso_17025_certified = 1
And enter moh_registration_no = "ĐLVN-2026-001"
Then this vendor appears in the lookup when creating an External Calibration Schedule
And is labeled "[ISO 17025 Certified]" in the dropdown

Given I try to link an External Calibration Schedule to a vendor with iso_17025_certified = 0
Then the system throws a warning: "Nhà cung cấp này chưa được công nhận ISO/IEC 17025. Xác nhận tiếp tục?"
```

### US-00-08: Cảnh báo hợp đồng NCC sắp hết hạn

```
As an IMM Operations Manager
I want to receive alerts when a vendor service contract is expiring
So that I can renew contracts before service interruptions occur
```

**Acceptance Criteria:**
```gherkin
Given an IMM Vendor Profile with contract_end = 2026-05-30 (30 days away)
When the daily scheduler job "check_vendor_contract_expiry()" runs
Then an email/notification is sent to IMM Department Head and IMM Operations Manager
With subject: "[CẢNH BÁO] Hợp đồng NCC sắp hết hạn: Draeger Vietnam — còn 30 ngày"
And the alert is logged in the system

Given contract_end is 90 days away → send first alert
Given contract_end is 60 days away → send second alert
Given contract_end is 30 days away → send third alert (escalate to Dept Head)
Given contract_end is 7 days away → send critical alert + appear in dashboard widget
```

---

## 6. User Stories — IMM SLA Policy

### US-00-09: Tra cứu SLA áp dụng cho sự cố P1

```
As the IMM System (automated)
I want to automatically determine the correct SLA policy when a new incident is reported
So that response deadlines are calculated correctly without manual input
```

**Acceptance Criteria:**
```gherkin
Given an IMM SLA Policy exists with priority = "P1", risk_class_trigger = "Critical"
And response_time_minutes = 30, resolution_time_hours = 4
When a new Incident Report is created with severity = "P1" and asset risk_class = "Critical"
Then the system calls imm00.get_sla_policy("P1", "Critical")
And returns the SLA Policy record
And Incident.response_deadline = incident.report_datetime + 30 minutes
And Incident.resolution_deadline = incident.report_datetime + 4 hours

Given no SLA Policy exists for the given priority + risk_class combination
Then the system falls back to the nearest matching priority level
And logs a warning to IMM Audit Trail with event_type = "System Event"
```

---

## 7. User Stories — IMM Audit Trail

### US-00-10: Xem lịch sử đầy đủ của một tài sản

```
As an IMM QA Officer
I want to view the complete audit history of any asset
So that I can trace all state changes, work orders, calibrations, and incidents for compliance purposes
```

**Acceptance Criteria:**
```gherkin
Given asset "ACC-ASS-2026-00001" has been in service for 2 years
When I navigate to IMM Asset Profile and click "Xem Audit Trail"
Then I see a chronological list of all IMM Audit Trail entries for this asset
Including: commissioning events, PM completions, CM WO lifecycle, calibration results, status changes
And I can filter by: date range, event_type, actor
And I can export to CSV

Given I attempt to edit any IMM Audit Trail record
Then no Edit button is shown (read-only form)
And the API endpoint for update returns 403 Forbidden
```

### US-00-11: Audit Trail ghi nhận tự động khi submit WO

```
As the IMM System (automated)
I want to automatically create an Audit Trail entry when any IMM document is submitted
So that all significant state changes are recorded without requiring manual action
```

**Acceptance Criteria:**
```gherkin
Given an IMM PM Work Order "PM-WO-2026-00012" is submitted with status "Completed"
When the WO is submitted (docstatus = 1)
Then an IMM Audit Trail entry is automatically created with:
  - asset = WO.asset
  - source_doctype = "IMM PM Work Order"
  - source_name = "PM-WO-2026-00012"
  - event_type = "State Change"
  - to_status = "Completed"
  - actor = current user
  - hash = SHA-256 of (asset + source_name + event_timestamp + to_status)
And the hash field is stored to detect any future tampering
```

---

## 8. User Stories — IMM CAPA Record

### US-00-12: Tạo CAPA bắt buộc khi hiệu chuẩn fail

```
As the IMM System (automated)
I want to automatically create a CAPA Record when a Calibration result is "Failed"
So that corrective action is tracked and cannot be skipped
```

**Acceptance Criteria:**
```gherkin
Given an IMM Asset Calibration record is submitted with overall_result = "Failed"
When the on_submit hook fires for IMM Asset Calibration
Then a CAPA Record is automatically created with:
  - source_doctype = "IMM Asset Calibration"
  - source_name = the calibration record name
  - capa_type = "Corrective"
  - severity = "Major" (or "Critical" if asset is Class III)
  - status = "Open"
  - assigned_to = asset.imm_responsible_tech
  - due_date = today + 30 days
And the Calibration Record stores the CAPA name in field "linked_capa"
And an email notification is sent to the assigned_to user

Given I try to Submit a Calibration Record with result = "Failed" without a CAPA being created
Then the system throws: "Kết quả hiệu chuẩn FAIL bắt buộc phải có CAPA Record. Hệ thống đang tạo CAPA tự động..."
```

### US-00-13: Đóng CAPA sau khi xác minh hiệu quả

```
As an IMM QA Officer
I want to close a CAPA after verifying that corrective actions were effective
So that the quality management cycle is formally completed
```

**Acceptance Criteria:**
```gherkin
Given a CAPA Record "CAPA-2026-00012" with status = "Pending Verification"
And corrective_action and preventive_action fields are filled in
When I set verification_result = "Effective" and click "Close CAPA"
Then status changes to "Closed"
And closed_by = current user, closed_date = today
And IMM Audit Trail entry is created: event_type = "CAPA", from_status = "Pending Verification", to_status = "Closed"
And a notification is sent to the CAPA assigned_to user

Given I try to close a CAPA where corrective_action is empty
Then the system throws: "Không thể đóng CAPA khi chưa điền 'Hành động khắc phục'."

Given a CAPA due_date has passed and status is still "Open" or "In Progress"
When the daily scheduler runs check_capa_overdue()
Then status is updated to "Overdue"
And IMM QA Officer and IMM Department Head receive an escalation notification
```

### US-00-14: Xem tổng quan CAPA cho một thiết bị

```
As an IMM Department Head
I want to see all open CAPAs for a specific asset on the Asset Profile page
So that I can assess the quality risk associated with that device
```

**Acceptance Criteria:**
```gherkin
Given asset "ACC-ASS-2026-00001" has 3 CAPA records:
  - 1 Closed, 1 In Progress, 1 Overdue
When I open the IMM Asset Profile for this asset
Then I see a "CAPA Summary" section showing:
  - Open: 0, In Progress: 1, Overdue: 1, Closed (30d): 1
And clicking "Xem tất cả CAPA" navigates to a filtered CAPA list for this asset
```

---

## 9. Business Rules

| Mã | Nội dung | Kiểm soát |
|---|---|---|
| **BR-00-01** | IMM Device Model phải được tạo trước khi tạo IMM Asset Profile | validate() trong IMM Asset Profile |
| **BR-00-02** | Mỗi ERPNext Asset chỉ có đúng một IMM Asset Profile | unique constraint trên field `asset` |
| **BR-00-03** | lifecycle_status trong IMM Asset Profile luôn sync về Asset.custom_imm_lifecycle_status trong vòng 1 transaction | on_update() hook |
| **BR-00-04** | IMM Audit Trail là append-only: không có Update/Delete permission cho bất kỳ role nào kể cả System Admin | Permission matrix: chỉ có Create và Read |
| **BR-00-05** | Calibration fail → CAPA bắt buộc. Không thể Submit Calibration Fail nếu CAPA chưa được tạo (hoặc đang trong quá trình auto-create) | before_submit() IMM Asset Calibration |
| **BR-00-06** | Mỗi priority level (P1/P2/P3/P4) phải có ít nhất 1 active SLA Policy record | validate khi tạo Incident Report |
| **BR-00-07** | Khi lifecycle_status chuyển sang "Decommissioned", tất cả IMM PM Schedule và IMM Calibration Schedule của asset phải được set status = "Suspended" | on_update() IMM Asset Profile |
| **BR-00-08** | CAPA không thể được đóng khi corrective_action hoặc preventive_action còn trống | validate() khi close CAPA |
| **BR-00-09** | Asset với lifecycle_status = "Out of Service" hoặc "Decommissioned" không thể tạo PM WO hoặc Calibration Record mới | validate_asset_for_operations() được gọi trước khi tạo WO |
| **BR-00-10** | IMM Audit Trail hash = SHA-256(asset + source_name + event_timestamp + to_status). Nếu hash không khớp khi verify → cảnh báo tamper | before_insert() IMM Audit Trail |
| **BR-00-11** | risk_classification trong IMM Device Model tự động set theo medical_device_class: Class I→Low, Class II→Medium, Class III→High hoặc Critical (có thể override) | validate() IMM Device Model |
| **BR-00-12** | Cảnh báo hết hạn BYT registration gửi ở mức 90/60/30/7 ngày | daily scheduler check_byt_registration_expiry() |
| **BR-00-13** | Cảnh báo hết hạn hợp đồng NCC gửi ở mức 90/60/30 ngày | daily scheduler check_vendor_contract_expiry() |
| **BR-00-14** | CAPA quá hạn (due_date < today, status không phải Closed) → escalate IMM QA Officer và IMM Department Head | daily scheduler check_capa_overdue() |

---

## 10. Validation Rules

| Code | Trường | Điều kiện vi phạm | Thông báo lỗi (frappe.throw) |
|---|---|---|---|
| **VR-00-01** | model_name + manufacturer | Duplicate combination | `_("Model '{0}' của nhà sản xuất '{1}' đã tồn tại trong hệ thống.").format(model_name, manufacturer)` |
| **VR-00-02** | asset (IMM Asset Profile) | Đã có profile cho asset này | `_("Tài sản '{0}' đã có Hồ sơ IMM. Mỗi tài sản chỉ có một hồ sơ duy nhất.").format(asset)` |
| **VR-00-03** | medical_device_class | Class II/III nhưng registration_number trống | `_("Thiết bị Class {0} bắt buộc phải có Số đăng ký BYT.").format(medical_device_class)` |
| **VR-00-04** | pm_interval_days | is_pm_required=1 nhưng pm_interval_days = 0 hoặc null | `_("Chu kỳ PM không được để trống khi thiết bị yêu cầu bảo trì định kỳ.")` |
| **VR-00-05** | calibration_interval_days | is_calibration_required=1 nhưng interval = 0 | `_("Chu kỳ hiệu chuẩn không được để trống khi thiết bị yêu cầu hiệu chuẩn định kỳ.")` |
| **VR-00-06** | lifecycle_status (decommission) | Chuyển sang Decommissioned khi còn WO đang mở | `_("Không thể thanh lý tài sản '{0}' khi còn {1} lệnh công việc đang mở. Hãy đóng hoặc hủy tất cả WO trước.").format(asset, open_wo_count)` |
| **VR-00-07** | corrective_action (CAPA close) | Đóng CAPA khi corrective_action trống | `_("Không thể đóng CAPA khi chưa điền 'Hành động khắc phục'.")` |
| **VR-00-08** | preventive_action (CAPA close) | Đóng CAPA khi preventive_action trống | `_("Không thể đóng CAPA khi chưa điền 'Hành động ngăn ngừa'.")` |
| **VR-00-09** | response_time_minutes (SLA Policy) | response_time > resolution_time * 60 | `_("Thời gian phản hồi không thể lớn hơn thời gian giải quyết.")` |
| **VR-00-10** | iso_17025_certified (Vendor Profile) | Dùng làm External Lab nhưng chưa certified | Warning: `_("Cảnh báo: Nhà cung cấp '{0}' chưa được công nhận ISO/IEC 17025.")` |
| **VR-00-11** | imm_asset_code | Duplicate toàn hệ thống | `_("Mã tài sản nội bộ '{0}' đã được sử dụng. Vui lòng chọn mã khác.")` |
| **VR-00-12** | contract_end < contract_start | Ngày hết hạn trước ngày bắt đầu | `_("Ngày hết hạn hợp đồng phải sau ngày bắt đầu.")` |
| **VR-00-13** | escalation_l1_hours | l1_hours >= resolution_time_hours | `_("Thời gian escalate Level 1 phải nhỏ hơn thời gian giải quyết SLA.")` |
| **VR-00-14** | source_doctype (CAPA) | Submit CAPA khi source record đã bị cancel | `_("Không thể submit CAPA khi tài liệu nguồn '{0}' đã bị hủy.")` |
| **VR-00-15** | hash (Audit Trail) | Phát hiện hash không khớp khi verify | Warning: `_("CẢNH BÁO: Bản ghi Audit Trail '{0}' có thể đã bị chỉnh sửa bất hợp pháp. Hash không khớp!")` |

---

## 11. Role Permission Matrix

**Chú thích:** C=Create, R=Read, W=Write, D=Delete, S=Submit, Ca=Cancel, A=Amend, `—`=Không có quyền, `*`=Chỉ record của mình

| DocType | Dept Head | Ops Manager | Workshop Lead | Technician | Doc Officer | Storekeeper | QA Officer | Sys Admin |
|---|---|---|---|---|---|---|---|---|
| **IMM Device Model** | CRWD | R | R | R | CRWD | — | R | All |
| **IMM Asset Profile** | CRWD | RW | RW | R | CRWD | R | R | All |
| **IMM Vendor Profile** | CRWD | RW | R | — | CRWD | — | R | All |
| **IMM Location Ext** | CRWD | RW | R | R | CRWD | — | R | All |
| **IMM SLA Policy** | R | R | R | — | — | — | R | CRWDAll |
| **IMM Audit Trail** | R | R | R | R* | R | — | R | R |
| **IMM CAPA Record** | CRWSCa | CRWS | R | R* | R | — | CRWSCaA | All |
| **Asset (ERPNext)** | CRWSCa | RW | RW | R | R | R | R | All |

**Ghi chú quan trọng:**
- `IMM Audit Trail`: **KHÔNG AI có quyền Delete** — kể cả Sys Admin. Đây là yêu cầu compliance bắt buộc.
- `IMM SLA Policy`: Chỉ Sys Admin có thể Create/Write. Các role khác chỉ Read.
- `IMM CAPA Record`: Chỉ IMM QA Officer mới có quyền Ca (Cancel) và A (Amend).
- `IMM Asset Profile` field `lifecycle_status`: Chỉ được sửa qua API `imm00.update_asset_lifecycle_status()`, không cho phép direct edit trừ Sys Admin.

---

## 12. Non-Functional Requirements

| NFR | Yêu cầu | Đo lường |
|---|---|---|
| **NFR-00-01: Performance** | API `get_asset_profile()` phải trả về < 300ms | 95th percentile với dataset 10.000 assets |
| **NFR-00-02: Audit completeness** | 100% state change phải có Audit Trail entry | Không có gap trong event sequence |
| **NFR-00-03: Tamper detection** | Hash verification cho Audit Trail | Alert nếu hash mismatch |
| **NFR-00-04: Data isolation** | IMM Asset Profile không expose financial data | No join với tabAsset Finance Book trong default queries |
| **NFR-00-05: Backward compatibility** | Custom Fields migration không làm hỏng existing Asset records | bench migrate chạy 0 error |
| **NFR-00-06: Scheduler reliability** | Daily jobs phải hoàn thành < 5 phút với 1.000 assets | Monitor job duration |

---

## 13. Acceptance Criteria cho Go-Live IMM-00

Hệ thống được coi là IMM-00 DONE khi tất cả điều kiện sau được đáp ứng:

```
FOUNDATION
  [ ] bench migrate thành công — 16 custom fields xuất hiện trong tabAsset
  [ ] 7 DocTypes tạo được và không có lỗi migrate
  [ ] 8 Roles được tạo với permission matrix đúng
  [ ] IMM SLA Policy có đủ 4 records (P1, P2, P3, P4)

DATA INTEGRITY
  [ ] VR-00-02: Không thể tạo 2 IMM Asset Profile cho cùng 1 Asset
  [ ] BR-00-04: Audit Trail không có Edit/Delete button dù đăng nhập System Manager
  [ ] BR-00-03: Thay đổi lifecycle_status → sync ngay về Asset custom field trong cùng request

AUTOMATION
  [ ] Scheduler daily jobs chạy không lỗi với mock data
  [ ] check_capa_overdue() tạo notification đúng format
  [ ] check_byt_registration_expiry() gửi alert đúng mức 90/60/30/7 ngày

CAPA
  [ ] Tạo CAPA Record manual thành công
  [ ] Close CAPA với verification_result
  [ ] Không thể close CAPA khi corrective_action trống (VR-00-07)

INTEGRATION READINESS
  [ ] imm00.validate_asset_for_operations() trả về đúng kết quả cho OOS asset
  [ ] imm00.get_sla_policy() trả về policy đúng theo priority + risk_class
  [ ] imm00.log_audit_event() tạo record với hash hợp lệ

TESTS
  [ ] Ít nhất 3 unit test cho mỗi DocType (create, validate_error, workflow_transition)
  [ ] Integration test: tạo Device Model → tạo Asset Profile → thay đổi lifecycle → verify Audit Trail
```
