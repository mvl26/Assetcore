# DATA DICTIONARY — ASSETCORE / IMMIS CH1
# Tầng 1 + Tầng 2 Foundation
# Version 0.1 | April 2026

---

## PHẦN 1 — CUSTOM FIELDS TRÊN tabAsset (ERPNext Core)

| Field Name | Label | Type | Required | Default | Options / Link | Rule nghiệp vụ |
|---|---|---|---|---|---|---|
| imm_device_model | Model thiết bị (IMM) | Link | N | — | IMM Device Model | Phải chọn trước khi commissioning |
| imm_medical_device_class | Phân loại TBYT | Select | N | — | Class I / II / III | Theo NĐ 98/2021 |
| imm_registration_number | Số đăng ký BYT | Data | N | — | — | Bắt buộc với Class II, III |
| imm_serial_number_manufacturer | Serial Number (NSX) | Data | N | — | — | Unique per device |
| imm_lifecycle_status | Trạng thái vòng đời | Select | N | Commissioning | Commissioning/Active/Under Repair/Calibrating/Inactive/Decommissioned | Sync từ IMM Asset Profile |
| imm_risk_class | Mức độ rủi ro | Select | N | — | Low/Medium/High/Critical | Auto từ device class |
| imm_department | Khoa/Phòng sử dụng | Link | N | — | Department | Cập nhật khi điều chuyển |
| imm_responsible_technician | KTV phụ trách | Link | N | — | User (role=IMM Technician) | — |
| imm_last_pm_date | Ngày PM cuối | Date | N | — | — | Read only, cập nhật khi WO PM completed |
| imm_next_pm_date | Ngày PM tiếp theo | Date | N | — | — | Dùng để trigger alert |
| imm_last_calibration_date | Ngày hiệu chuẩn cuối | Date | N | — | — | Read only |
| imm_next_calibration_date | Ngày hiệu chuẩn tiếp theo | Date | N | — | — | Dùng để trigger alert |

---

## PHẦN 2 — IMM DEVICE MODEL

**DocType:** `IMM Device Model` | **Module:** imm_master | **Naming:** IMM-MDL-.YYYY.-.####

| Field | Label | Type | Req | Default | Options/Link | Rule |
|---|---|---|---|---|---|---|
| model_name | Tên model | Data | Y | — | — | Unique per manufacturer |
| manufacturer | Nhà sản xuất | Data | Y | — | — | — |
| country_of_origin | Nước sản xuất | Data | N | — | — | — |
| device_category | Danh mục tài sản | Link | N | — | Asset Category | — |
| medical_device_class | Phân loại TBYT | Select | Y | — | Class I/II/III | Theo WHO + NĐ98 |
| gmdn_code | Mã GMDN | Data | N | — | — | Global Medical Device Nomenclature |
| hsn_code | Mã HS (BYT VN) | Data | N | — | — | — |
| risk_classification | Mức rủi ro | Select | N | — | Low/Medium/High/Critical | Auto từ class |
| power_supply | Nguồn điện | Data | N | — | — | VD: 220V/50Hz/300W |
| recommended_pm_frequency | Chu kỳ PM | Select | N | — | Monthly/Quarterly/Semi-annual/Annual | — |
| recommended_calibration_frequency | Chu kỳ hiệu chuẩn | Select | N | — | 6 months/Annual/2 years/3 years/5 years | — |
| expected_lifespan_years | Tuổi thọ dự kiến (năm) | Int | N | — | — | — |
| registration_required | Cần đăng ký BYT | Check | N | 1 | — | — |
| notes | Ghi chú | Text Editor | N | — | — | — |

---

## PHẦN 3 — IMM ASSET PROFILE

**DocType:** `IMM Asset Profile` | **Module:** imm_master | **Naming:** IMM-ASP-.YYYY.-.####

| Field | Label | Type | Req | Default | Options/Link | Rule |
|---|---|---|---|---|---|---|
| asset | Tài sản (ERPNext) | Link | Y | — | Asset | Unique: 1 profile per asset |
| device_model | Model thiết bị | Link | Y | — | IMM Device Model | — |
| imm_asset_code | Mã tài sản nội bộ | Data | Y | — | — | Unique toàn hệ thống |
| barcode | Barcode | Data | N | — | — | — |
| serial_number_manufacturer | S/N nhà sản xuất | Data | N | — | — | — |
| registration_number | Số đăng ký BYT | Data | N | — | — | Required if Class II/III |
| registration_expiry | Hạn đăng ký | Date | N | — | — | Alert 60 ngày trước |
| current_location | Vị trí hiện tại | Link | N | — | Location | — |
| current_department | Khoa/Phòng | Link | N | — | Department | — |
| lifecycle_status | Trạng thái vòng đời | Select | Y | Commissioning | Commissioning/Active/Under Repair/Calibrating/Inactive/Decommissioned | Sync về Asset custom field |
| commissioning_date | Ngày đưa vào sử dụng | Date | N | — | — | — |
| pm_frequency | Chu kỳ PM | Select | N | — | Monthly/Quarterly/Semi-annual/Annual | Kế thừa từ Device Model |
| calibration_required | Cần hiệu chuẩn | Check | N | — | — | — |
| document_attachments | Hồ sơ đính kèm | Child Table | N | — | IMM Profile Document | — |
| imm_status | Trạng thái IMM | Select | N | Active | Active/Inactive | — |

---

## PHẦN 4 — IMM AUDIT TRAIL

**DocType:** `IMM Audit Trail` | **Module:** imm_master | **Naming:** auto | **Is Submittable:** No

| Field | Label | Type | Req | Default | Options/Link | Rule |
|---|---|---|---|---|---|---|
| asset | Tài sản | Link | Y | — | Asset | — |
| event_type | Loại sự kiện | Select | Y | — | Status Change/Document Submitted/WO Created/WO Completed/Calibration Done/Incident Reported/Transfer/Decommission/System Event | — |
| event_datetime | Thời điểm | Datetime | Y | now | — | Auto, không chỉnh sửa |
| from_status | Trạng thái trước | Data | N | — | — | — |
| to_status | Trạng thái sau | Data | N | — | — | — |
| reference_doctype | Loại chứng từ | Link | N | — | DocType | — |
| reference_name | Mã chứng từ | Dynamic Link | N | — | reference_doctype | — |
| performed_by | Thực hiện bởi | Link | N | current user | User | — |
| role_at_time | Role tại thời điểm | Data | N | — | — | Auto |
| remarks | Ghi chú | Small Text | N | — | — | — |

---

## PHẦN 5 — IMM DOCUMENT REPOSITORY (IMM-05)

**DocType:** `IMM Document Repository` | **Module:** imm_deployment | **Naming:** IMM-05-DOC-.YYYY.-.####

| Field | Label | Type | Req | Default | Options/Link | Rule |
|---|---|---|---|---|---|---|
| title | Tiêu đề | Data | Y | — | — | — |
| document_category | Nhóm hồ sơ | Select | Y | — | Legal/Technical/Commercial/Training/Maintenance/Calibration/CAPA/Other | — |
| document_type | Loại hồ sơ | Select | N | — | (xem danh sách đầy đủ) | — |
| linked_to | Liên kết về | Select | Y | Asset | Asset/Device Model | — |
| asset | Tài sản | Link | N | — | Asset | Bắt buộc nếu linked_to=Asset |
| device_model | Model | Link | N | — | IMM Device Model | Bắt buộc nếu linked_to=Device Model |
| document_number | Số hiệu tài liệu | Data | N | — | — | — |
| issuing_authority | Cơ quan cấp | Data | N | — | — | — |
| issue_date | Ngày cấp | Date | N | — | — | — |
| expiry_date | Ngày hết hạn | Date | N | — | — | Alert 30 ngày trước |
| is_permanent | Không có hạn | Check | N | 0 | — | Nếu True, clear expiry_date |
| version | Phiên bản | Data | N | 1.0 | — | — |
| primary_attachment | File đính kèm chính | Attach | Y | — | — | Bắt buộc trước submit |
| document_status | Trạng thái hồ sơ | Select | Y | Draft | Draft/Active/Expired/Superseded/Cancelled | Auto update |
| controlled_copy | Bản kiểm soát | Check | N | 0 | — | — |
| next_review_date | Ngày xem xét tiếp | Date | N | — | — | — |

---

## PHẦN 6 — IMM PM WORK ORDER (IMM-08)

**DocType:** `IMM PM Work Order` | **Module:** imm_operations | **Naming:** IMM-08-PM-.YYYY.-.####

| Field | Label | Type | Req | Default | Options/Link | Rule |
|---|---|---|---|---|---|---|
| asset | Tài sản | Link | Y | — | Asset | Không được ở trạng thái Decommissioned |
| pm_type | Loại PM | Select | Y | Preventive Maintenance | Preventive Maintenance/Periodic Inspection/Lubrication/Cleaning/Calibration Check | — |
| scheduled_date | Ngày lên lịch | Date | Y | — | — | in_list_view |
| scheduled_duration_hours | Thời gian dự kiến (giờ) | Float | N | 2.0 | — | — |
| assigned_technician | Kỹ thuật viên | Link | Y | — | User | Role phải là IMM Technician |
| actual_start_datetime | Bắt đầu thực tế | Datetime | N | — | — | — |
| actual_end_datetime | Kết thúc thực tế | Datetime | N | — | — | — |
| actual_duration_hours | Thời gian thực (giờ) | Float | N | — | — | Auto tính |
| checklist_items | Checklist | Child Table | N | — | IMM PM Checklist Item | — |
| checklist_completion_pct | % hoàn thành checklist | Percent | N | 0 | — | Auto tính |
| pm_result | Kết quả | Select | Y* | — | Pass/Pass with Observation/Fail/Inconclusive | *Required before submit |
| findings | Phát hiện | Text Editor | N | — | — | — |
| follow_up_required | Cần theo dõi | Check | N | 0 | — | Nếu True: tạo CM WO |
| spare_parts_used | Phụ tùng sử dụng | Child Table | N | — | IMM PM Spare Part Used | — |
| imm_status | Trạng thái | Select | Y | Draft | Draft/Scheduled/Assigned/In Progress/Completed/Verified/Cancelled | Workflow controlled |
| is_overdue | Quá hạn | Check | N | 0 | — | Auto từ scheduler |
| overdue_days | Số ngày quá hạn | Int | N | 0 | — | Auto tính |

---

## PHẦN 7 — IMM CM WORK ORDER (IMM-09 + IMM-12)

**DocType:** `IMM CM Work Order` | **Module:** imm_operations | **Naming:** IMM-09-CM-.YYYY.-.####

| Field | Label | Type | Req | Default | Options/Link | Rule |
|---|---|---|---|---|---|---|
| asset | Tài sản | Link | Y | — | Asset | — |
| failure_datetime | Thời điểm hỏng | Datetime | Y | — | — | — |
| reported_by | Báo cáo bởi | Link | Y | current | User | — |
| failure_description | Mô tả sự cố | Text Editor | Y | — | — | — |
| failure_category | Phân loại | Select | Y | — | Electrical/Mechanical/Software/User Error/Unknown/Wear & Tear/Accident/Other | — |
| severity_level | Mức độ nghiêm trọng | Select | Y | — | Critical/High/Medium/Low | Quyết định SLA |
| sla_target_hours | SLA (giờ) | Float | N | — | — | Auto: Critical=4, High=24, Medium=72, Low=168 |
| triage_result | Kết quả triage | Select | N | — | Repair In-house/Send to Vendor/Replace Component/Decommission/No Fault Found | — |
| assigned_technician | KTV phụ trách | Link | N | — | User | — |
| root_cause | Nguyên nhân gốc | Text Editor | N | — | — | — |
| repair_actions | Hành động sửa chữa | Text Editor | N | — | — | — |
| spare_parts_used | Phụ tùng | Child Table | N | — | IMM CM Spare Part Used | — |
| vendor_repair | Sửa bên ngoài | Check | N | 0 | — | — |
| vendor_name | Nhà cung cấp | Link | N | — | Supplier | Required nếu vendor_repair=True |
| repair_result | Kết quả sửa chữa | Select | N | — | Repaired/Partially Repaired/Cannot Repair/Replaced | — |
| actual_downtime_hours | Thời gian ngừng hoạt động (giờ) | Float | N | — | — | Auto tính từ failure_datetime đến end |
| sla_breach | Vi phạm SLA | Check | N | 0 | — | Auto |
| rca_required | Cần RCA | Check | N | 0 | — | Bắt buộc nếu severity=Critical/High |
| imm_status | Trạng thái | Select | Y | Reported | Reported/Triaged/Assigned/Diagnosing/In Repair/Waiting Parts/Testing/Completed/Closed/Cancelled | Workflow |
| reference_asset_repair | Asset Repair (ERPNext) | Link | N | — | Asset Repair | Tạo và link sau submit |

---

## PHẦN 8 — IMM CALIBRATION RECORD (IMM-11)

**DocType:** `IMM Calibration Record` | **Module:** imm_operations | **Naming:** IMM-11-CAL-.YYYY.-.####

| Field | Label | Type | Req | Default | Options/Link | Rule |
|---|---|---|---|---|---|---|
| asset | Tài sản | Link | Y | — | Asset | — |
| calibration_type | Loại hiệu chuẩn | Select | Y | — | Internal Calibration/External Calibration/Legal Inspection/Performance Test/Functional Check | — |
| scheduled_date | Ngày lên kế hoạch | Date | Y | — | — | — |
| actual_date | Ngày thực hiện | Date | N | — | — | — |
| calibrating_entity | Đơn vị thực hiện | Select | N | — | Internal/Accredited Lab/Manufacturer/Regulatory Body | — |
| calibrating_lab_name | Tên lab/đơn vị | Data | N | — | — | — |
| accreditation_number | Số công nhận | Data | N | — | — | — |
| calibration_result | Kết quả | Select | N | — | Pass/Pass with Conditions/Fail/Out of Tolerance | — |
| certificate_number | Số chứng chỉ | Data | N | — | — | — |
| certificate_expiry | Hạn hiệu lực chứng chỉ | Date | N | — | — | Alert 30 ngày trước, in_list_view |
| measurement_results | Kết quả đo lường | Child Table | N | — | IMM Calibration Measurement | — |
| out_of_tolerance | Ngoài dung sai | Check | N | 0 | — | — |
| certificate_attachment | File chứng chỉ | Attach | N | — | — | Required khi result=Pass |
| imm_status | Trạng thái | Select | Y | Scheduled | Scheduled/In Progress/Completed/Expired/Cancelled | — |

---

## PHẦN 9 — IMM COMMISSIONING RECORD (IMM-04)

**DocType:** `IMM Commissioning Record` | **Module:** imm_deployment | **Naming:** IMM-04-COM-.YYYY.-.####

| Field | Label | Type | Req | Default | Options/Link | Rule |
|---|---|---|---|---|---|---|
| asset | Tài sản | Link | Y | — | Asset | — |
| device_model | Model | Link | Y | — | IMM Device Model | — |
| installation_date | Ngày lắp đặt | Date | Y | — | — | — |
| installation_location | Vị trí lắp đặt | Link | Y | — | Location | — |
| installation_department | Khoa/Phòng | Link | N | — | Department | — |
| manufacturer_serial_no | S/N nhà sản xuất | Data | Y | — | — | — |
| internal_asset_code | Mã tài sản nội bộ | Data | N | — | — | — |
| inspection_checklist | Checklist kiểm tra | Child Table | N | — | IMM Commissioning Checklist | — |
| overall_inspection_result | Kết quả kiểm tra tổng | Select | N | — | Pass/Pass with Observations/Fail | — |
| electrical_safety_test | Kiểm tra an toàn điện | Select | N | — | Pass/Fail/N/A | — |
| functional_test | Kiểm tra chức năng | Select | N | — | Pass/Fail/N/A | — |
| performance_baseline | Baseline hiệu năng | Text Editor | N | — | — | — |
| documents_received | Tài liệu đã nhận | Child Table | N | — | IMM Commissioning Document | — |
| release_for_use | Cho phép sử dụng | Check | N | 0 | — | Chỉ set khi Pass |
| release_date | Ngày cho phép sử dụng | Date | N | — | — | — |
| commissioning_report | Biên bản nghiệm thu | Attach | N | — | — | — |
| imm_status | Trạng thái | Select | Y | Draft | Draft/In Progress/Completed/Approved/Rejected | — |

---

## PHẦN 10 — BẢNG TRẠNG THÁI VÒNG ĐỜI TÀI SẢN

| Trạng thái | Mô tả | Cho phép WO PM | Cho phép WO CM | Cho phép Calibration |
|---|---|---|---|---|
| Commissioning | Đang lắp đặt/kiểm tra | Không | Không | Không |
| Active | Đang hoạt động bình thường | Có | Có | Có |
| Under Repair | Đang sửa chữa | Không | Có (1 WO CM) | Không |
| Calibrating | Đang hiệu chuẩn | Không | Không | Có (1 record) |
| Inactive | Tạm ngừng sử dụng | Không | Có | Không |
| Decommissioned | Đã thanh lý/loại bỏ | Không | Không | Không |

---

## PHẦN 11 — SLA MATRIX (CM Work Order)

| Severity | SLA Target | Escalation Threshold | Notification |
|---|---|---|---|
| Critical | 4 giờ | 2 giờ | SMS + Email → IMM Operations Manager |
| High | 24 giờ | 12 giờ | Email → IMM Workshop Lead |
| Medium | 72 giờ | 48 giờ | Email → IMM Technician |
| Low | 168 giờ (7 ngày) | 120 giờ (5 ngày) | Email → IMM Technician |
