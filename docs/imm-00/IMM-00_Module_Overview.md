# IMM-00 — Nền tảng Hệ thống (Foundation Module)
## Module Overview

**Module:** IMM-00
**Version:** 1.0
**Ngày:** 2026-04-17
**Trạng thái:** NOT CODED — Tài liệu thiết kế (Docs Only)
**Wave:** Pre-Wave 1 (Foundation — phải hoàn thành trước tất cả module khác)

---

## 1. Mục đích Module

IMM-00 là lớp nền tảng (foundation layer) của toàn hệ thống AssetCore. Module này thiết lập và quản lý toàn bộ master data dùng chung: danh mục thiết bị y tế (Device Model), hồ sơ tài sản HTM mở rộng (Asset Profile), hồ sơ nhà cung cấp (Vendor Profile), mở rộng vị trí (Location Ext), chính sách SLA, audit trail bất biến, hồ sơ CAPA và vai trò/phân quyền.

**Không có IMM-00 thì không có module nào hoạt động được.** Tất cả 17 module từ IMM-01 đến IMM-17 đều phụ thuộc vào master data và infrastructure mà IMM-00 thiết lập.

**Nguyên tắc cốt lõi:**
- ERPNext Asset = registry (định danh vật lý) → IMM-00 mở rộng thành HTM Asset Profile đầy đủ
- Không bao giờ sửa ERPNext core — chỉ extend bằng DocType mới hoặc Custom Field
- Mọi thay đổi trạng thái tài sản phải được ghi vào IMM Audit Trail (append-only)
- CAPA là cơ chế kiểm soát chất lượng xuyên suốt — gắn với IMM-11, IMM-12, IMM-09

---

## 2. Trạng thái Triển khai

| Hạng mục | Trạng thái |
|---|---|
| IMM Device Model DocType | Chưa tạo |
| IMM Asset Profile DocType | Chưa tạo |
| IMM Vendor Profile DocType | Chưa tạo |
| IMM Location Ext DocType | Chưa tạo |
| IMM SLA Policy DocType | Chưa tạo |
| IMM Audit Trail DocType | Chưa tạo |
| IMM CAPA Record DocType | Chưa tạo |
| Custom Fields trên tabAsset (16 fields) | Chưa cài đặt |
| 8 Roles & Permission Matrix | Chưa cấu hình |
| Scheduler Jobs (daily/weekly) | Chưa code |
| Workflow (CAPA) | Chưa cấu hình |
| Backend Logic / Service Layer | Chưa code |
| API | Chưa code |
| Test | Chưa viết |

---

## 3. Vị trí trong Asset Lifecycle

```
                    ┌─────────────────────────────────────────────────┐
                    │              IMM-00: FOUNDATION                  │
                    │                                                   │
                    │  Device Model  │  Asset Profile  │  Vendor Profile│
                    │  Location Ext  │  SLA Policy     │  Audit Trail   │
                    │  CAPA Record   │  Roles & Perms  │  Custom Fields │
                    └─────────────────────────────────────────────────┘
                                          │
                         Cung cấp master data cho toàn bộ hệ thống
                                          │
         ┌────────────┬────────────┬──────┴──────┬────────────┬────────────┐
         │            │            │             │            │            │
    IMM-01/03    IMM-04/05    IMM-08/09    IMM-11/12    IMM-13/14    IMM-15/17
   (Planning)  (Deployment)  (PM/CM)     (CAL/Corr.)   (End-of-Life)  (Analytics)

WHO HTM Lifecycle:
Needs → Procurement → [IMM-00 Foundation] → Installation → Operation → Maintenance → Decommission
```

**Vai trò của IMM-00 trong từng giai đoạn:**
- **IMM-04/05** → dùng `IMM Device Model` để xác định class, risk, PM/CAL interval khi lắp đặt
- **IMM-08** → dùng `IMM Asset Profile`.pm_interval_days để lập lịch PM đầu tiên
- **IMM-09/12** → dùng `IMM Vendor Profile` để tra cứu nhà cung cấp dịch vụ, SLA response time
- **IMM-11** → dùng `IMM CAPA Record` khi calibration fail; dùng `IMM Audit Trail` ghi event
- **IMM-13/14** → lifecycle_status = Decommissioned trong `IMM Asset Profile` kích hoạt suspend PM/CAL

---

## 4. DocTypes cần tạo

| DocType | Naming Series | Module Frappe | Mục đích | Trường chính |
|---|---|---|---|---|
| **IMM Device Model** | `DM-.YYYY.-.#####` | imm_master | Danh mục mẫu thiết bị y tế | model_name, manufacturer, gmdn_code, device_category, medical_device_class, risk_classification, pm_interval_days, calibration_interval_days |
| **IMM Asset Profile** | `AP-.YYYY.-.#####` | imm_master | Hồ sơ HTM mở rộng 1:1 với ERPNext Asset | asset(unique link), device_model, imm_asset_code, serial_number_manufacturer, udi_code, lifecycle_status, responsible_technician |
| **IMM Vendor Profile** | `VP-.YYYY.-.#####` | imm_master | Hồ sơ NCC mở rộng Supplier | vendor, vendor_type, iso_13485_certified, moh_registration_no, sla_response_hours, contract_end |
| **IMM Location Ext** | `LE-.YYYY.-.#####` | imm_master | Mở rộng Location với thông tin lâm sàng | location(unique link), dept_code, clinical_area_type, dept_head, emergency_contact |
| **IMM SLA Policy** | `SLA-.YYYY.-.#####` | imm_master | Chính sách SLA theo loại công việc và priority | policy_name, applies_to, priority, response_time_minutes, resolution_time_hours, escalation_l1_hours |
| **IMM Audit Trail** | `AT-.YYYY.-.######` | imm_master | Log bất biến mọi sự kiện vòng đời | asset, event_type, from_status, to_status, actor, event_timestamp, hash |
| **IMM CAPA Record** | `CAPA-.YYYY.-.#####` | imm_master | Hồ sơ hành động khắc phục/phòng ngừa | capa_number, asset, capa_type, severity, description, root_cause, corrective_action, status |

**Child Tables:**

| Child Table | Parent | Mục đích |
|---|---|---|
| IMM Device Spare Part | IMM Device Model | Danh sách phụ tùng tiêu chuẩn theo model |
| IMM Vendor Authorized Tech | IMM Vendor Profile | Danh sách KTV được ủy quyền từ NCC |

---

## 5. Custom Fields trên tabAsset (ERPNext Core)

Thêm 16 custom field vào ERPNext Asset DocType qua `bench migrate` (không sửa core):

| Field Name | Field Type | Options / Link | Mục đích |
|---|---|---|---|
| `imm_device_model` | Link | IMM Device Model | Liên kết tới Device Model catalog |
| `imm_asset_profile` | Link | IMM Asset Profile | Liên kết tới HTM Asset Profile |
| `imm_medical_class` | Select | Class I, Class II, Class III | Phân loại trang thiết bị y tế |
| `imm_risk_class` | Select | Low, Medium, High, Critical | Phân loại rủi ro |
| `imm_byt_reg_no` | Data | — | Số đăng ký Bộ Y Tế |
| `imm_manufacturer_sn` | Data | — | Serial number nhà sản xuất |
| `imm_udi_code` | Data | — | Mã UDI (Unique Device Identifier) |
| `imm_gmdn_code` | Data | — | Mã GMDN |
| `imm_lifecycle_status` | Select | Active, Under Repair, Calibrating, OOS, Decommissioned | Trạng thái vòng đời HTM |
| `imm_calibration_status` | Select | In Tolerance, OOT, Not Required, Overdue | Trạng thái hiệu chuẩn |
| `imm_department` | Link | Department | Khoa phòng quản lý |
| `imm_responsible_tech` | Link | User | KTV phụ trách |
| `imm_last_pm_date` | Date | — | Ngày PM gần nhất |
| `imm_next_pm_date` | Date | — | Ngày PM tiếp theo |
| `imm_last_calibration_date` | Date | — | Ngày hiệu chuẩn gần nhất |
| `imm_next_calibration_date` | Date | — | Ngày hiệu chuẩn tiếp theo |

---

## 6. Workflow States — IMM CAPA Record

| State | Mô tả | Actor | Trigger / Entry Condition |
|---|---|---|---|
| **Open** | CAPA vừa được tạo, chờ phân công | System Auto / QA Officer | Calibration fail (IMM-11), Incident critical (IMM-12), hoặc Manual |
| **In Progress** | Đã phân công, đang điều tra nguyên nhân | Assigned User | `assigned_to` được điền + action started |
| **Pending Verification** | Hành động khắc phục đã thực hiện, chờ QA xác nhận | QA Officer | Assigned User submit corrective action |
| **Closed** | QA xác nhận hiệu quả, CAPA hoàn thành | QA Officer | verification_result = Effective / Partially Effective |
| **Overdue** | CAPA Open > 30 ngày chưa tiến triển | CMMS Scheduler | `today - creation_date > 30 AND status in (Open, In Progress)` |

**Transition Rules:**
- Open → In Progress: `assigned_to` phải được điền
- In Progress → Pending Verification: `corrective_action` + `root_cause` bắt buộc
- Pending Verification → Closed: `verification_result` bắt buộc + `closed_by` = QA Officer role
- Pending Verification → In Progress: Nếu QA từ chối (verification_result = Not Effective)
- Any → Overdue: Scheduler tự động sau 30 ngày

---

## 7. Business Rules

| Mã | Rule | Kiểm soát |
|---|---|---|
| **BR-00-01** | IMM Device Model phải được tạo trước khi tạo IMM Asset Profile | Validate: `device_model` mandatory; check exists on save |
| **BR-00-02** | IMM Asset Profile là 1:1 với ERPNext Asset — một Asset chỉ có một Profile | Unique constraint trên field `asset`; validate trong `before_insert` |
| **BR-00-03** | `lifecycle_status` trong IMM Asset Profile luôn sync về `Asset.imm_lifecycle_status` | `on_update` hook tự động ghi vào tabAsset |
| **BR-00-04** | IMM Audit Trail là append-only — không có Update/Delete endpoint, không có Delete permission cho bất kỳ role nào | DocType không submittable; permission `delete = 0` cho tất cả roles kể cả System Admin |
| **BR-00-05** | CAPA phải được tạo trước khi Calibration fail record có thể Submit | IMM-11 on_submit fail path: check CAPA exists hoặc auto-create; block Submit nếu không tạo được |
| **BR-00-06** | SLA Policy phải có ít nhất 1 default policy cho mỗi priority level (P1/P2/P3/P4) | Validate trên SLA Policy save: check `is_default` per priority |
| **BR-00-07** | IMM Vendor Profile phải có ít nhất 1 record cho mỗi Supplier được dùng trong Commissioning | IMM-04 on_submit: check vendor has Vendor Profile; block nếu thiếu |
| **BR-00-08** | Khi lifecycle_status → Decommissioned, tất cả active PM Schedule và Calibration Schedule phải bị Suspended | `on_update` IMM Asset Profile: nếu status → Decommissioned, gọi `suspend_all_schedules(asset)` |

---

## 8. Scheduler Jobs

| Job Function | Tần suất | Mô tả |
|---|---|---|
| `sync_asset_profile_status()` | Hàng ngày | Sync `lifecycle_status` từ IMM Asset Profile về `Asset.imm_lifecycle_status` cho tất cả asset; phát hiện drift |
| `check_vendor_contract_expiry()` | Hàng ngày | So sánh `contract_end` với ngày hiện tại; gửi alert 90/60/30 ngày trước hạn cho IMM Operations Manager |
| `check_byt_registration_expiry()` | Hàng ngày | So sánh `registration_expiry` trong IMM Asset Profile với today; alert 90/60/30 ngày trước hạn |
| `check_capa_overdue()` | Hàng ngày | CAPA có status Open/In Progress và `creation > 30 ngày` → set status = Overdue, gửi alert QA Officer và Department Head |
| `compute_asset_kpi_snapshot()` | Hàng tuần | Tính KPI per asset (availability, compliance rate, CAPA closure), lưu vào IMM Performance KPI snapshot |

---

## 9. Integration Points

### IMM-00 → Tất cả module (Foundation Provider)

| Module Nhận | Dữ liệu từ IMM-00 | Khi nào |
|---|---|---|
| **IMM-04** (Installation) | `IMM Device Model`: medical_device_class, risk_classification, pm_interval_days, calibration_interval_days | Khi tạo Commissioning Record — điền thông số tự động từ Device Model |
| **IMM-05** (Registration) | `IMM Asset Profile`: udi_code, gmdn_code, registration_number, device_model | Khi tạo hồ sơ đăng ký BYT — dữ liệu pre-filled từ Profile |
| **IMM-08** (PM) | `IMM Asset Profile`: pm_interval_days, last_pm_date, next_pm_date; `IMM SLA Policy`: response_time, priority | Lập PM Schedule đầu tiên; xác định SLA cho WO |
| **IMM-09** (CM/Repair) | `IMM Vendor Profile`: sla_response_hours, support_hotline, authorized_technicians; `IMM SLA Policy` | Xác định SLA CM, tìm NCC sửa chữa được ủy quyền |
| **IMM-11** (Calibration) | `IMM Device Model`: calibration_interval_days; `IMM Asset Profile`: calibration_required; `IMM CAPA Record` | Lập Calibration Schedule; auto-create CAPA khi fail |
| **IMM-12** (Corrective) | `IMM SLA Policy`: priority escalation; `IMM Audit Trail`: lịch sử incident | Xác định P1/P2/P3 SLA; trace lịch sử sự cố |
| **IMM-13** (Decommission) | `IMM Asset Profile`: lifecycle_status = Decommissioned triggers; `IMM Audit Trail`: full history | Khi decommission, Archive Profile + Print Audit Trail đầy đủ |
| **IMM-15** (Spare Parts) | `IMM Device Model`: spare_parts_list (child table) | Danh mục phụ tùng chuẩn theo model để quản lý tồn kho |
| **IMM-16** (Compliance) | `IMM Audit Trail`: toàn bộ event log; `IMM CAPA Record`: closure status | Dashboard tuân thủ theo tiêu chuẩn; audit evidence |
| **IMM-17** (Analytics) | `IMM Asset Profile`: lifecycle_status history; `IMM CAPA Record`: trends | Predictive analytics dựa trên lịch sử sự kiện |

### Tất cả module → IMM-00 (Foundation Consumer)

| Module Gửi | Dữ liệu về IMM-00 | Khi nào |
|---|---|---|
| **IMM-04** on_submit | Tạo IMM Asset Profile đầu tiên; ghi IMM Audit Trail event = "commissioned" | Khi Clinical Release được Submit |
| **IMM-08** on_submit | Ghi IMM Audit Trail event = "pm_completed"; cập nhật Asset Profile.last_pm_date | Khi PM WO hoàn thành |
| **IMM-09** on_submit | Ghi IMM Audit Trail event = "repaired"; cập nhật lifecycle_status | Khi CM WO Closed |
| **IMM-11** on_submit | Ghi IMM Audit Trail event = "calibration_completed/failed"; tạo CAPA nếu fail | Khi Calibration record Submit |
| **IMM-12** on_submit | Ghi IMM Audit Trail event = "incident_closed"; mở CAPA nếu severity Critical | Khi Corrective WO Closed |
| **IMM-13** on_submit | Cập nhật lifecycle_status = "Decommissioned"; ghi Audit Trail "decommissioned" | Khi Decommission được phê duyệt |

---

## 10. KPI Definitions

| KPI | Công thức | Mục tiêu | Nguồn dữ liệu |
|---|---|---|---|
| **Asset Data Completeness** | `Count(Asset với IMM Profile đầy đủ) / Total Active Assets × 100%` | 100% | IMM Asset Profile |
| **Vendor SLA Coverage** | `Count(Supplier có Vendor Profile + SLA) / Count(Supplier dùng trong WO) × 100%` | 100% | IMM Vendor Profile |
| **BYT Registration Current** | `Count(Asset có registration_expiry > today) / Count(Assets yêu cầu ĐK) × 100%` | ≥ 95% | IMM Asset Profile |
| **CAPA Closure Rate (30 ngày)** | `Count(CAPA Closed ≤ 30 ngày) / Count(Total CAPA) × 100%` | ≥ 90% | IMM CAPA Record |
| **CAPA Overdue Rate** | `Count(CAPA Overdue) / Count(Total CAPA Open) × 100%` | ≤ 5% | IMM CAPA Record |
| **Audit Trail Integrity** | `Count(Audit Trail records với valid hash) / Total AT records × 100%` | 100% | IMM Audit Trail |
| **Asset Lifecycle Sync Rate** | `Count(Asset.imm_lifecycle_status == Profile.lifecycle_status) / Total Assets × 100%` | 100% | IMM Asset Profile + tabAsset |

---

## 11. QMS Mapping

| Yêu cầu IMM-00 | WHO HTM | ISO 13485 | NĐ98/2021 | Ghi chú |
|---|---|---|---|---|
| Danh mục thiết bị y tế (Device Model) | WHO HTM §3.1 — Equipment inventory | §4.1 — System requirements | Điều 4 — Phân loại TTBYT | GMDN code + risk class bắt buộc |
| Hồ sơ thiết bị đầy đủ (Asset Profile) | WHO HTM §4.2 — Equipment database | §7.5 — Control of records | Điều 44 — Hồ sơ trang thiết bị | UDI, S/N, BYT registration mandatory |
| Thông tin nhà cung cấp (Vendor Profile) | WHO HTM §5.1 — Procurement records | §7.4 — Purchasing | Điều 22 — Nhà cung cấp dịch vụ | ISO 13485 cert của NCC cần lưu trữ |
| Quản lý vị trí lâm sàng (Location Ext) | WHO HTM §4.3 — Location tracking | §6.3 — Infrastructure | Điều 5 — Phân loại theo khu vực | Clinical area type cho phân tích risk |
| Chính sách SLA (SLA Policy) | WHO HTM §6.1 — Response time | §8.2.3 — Service requirement | Điều 35 — Thời gian phản hồi | P1 critical ≤ 1h; P4 low ≤ 24h |
| Audit Trail bất biến | WHO HTM §6.4 — Records management | §4.2.5 — Control of records | Điều 40 Khoản 3 — Lưu trữ hồ sơ | Append-only, SHA-256 hash, không xóa được |
| CAPA (Corrective & Preventive Action) | WHO HTM §5.5 — Corrective actions | §8.5.2 — Corrective action, §8.5.3 — Preventive action | Điều 40 — Xử lý sự cố | Root cause + verification mandatory |
| Phân quyền theo vai trò | WHO HTM §6.2 — Responsibility | §5.5 — Responsibility and authority | Điều 6 — Nhân sự | 8 roles với permission matrix đầy đủ |

---

## 12. Dependencies

### IMM-00 phụ thuộc vào (ERPNext Core — không sửa):

| ERPNext DocType | Lý do phụ thuộc |
|---|---|
| `Asset` | IMM Asset Profile link 1:1; Custom Fields được thêm vào |
| `Supplier` | IMM Vendor Profile mở rộng Supplier |
| `Location` | IMM Location Ext mở rộng Location |
| `Department` | IMM Asset Profile + Location Ext tham chiếu |
| `Employee` | IMM Location Ext.dept_head link Employee |
| `User` | IMM Asset Profile.responsible_technician; IMM Audit Trail.actor |
| `Item` | IMM Device Model.item_ref (catalog item) |
| `Asset Category` | IMM Device Model.device_category |
| `Role` | IMM SLA Policy.escalation_l2_role; Permission Matrix |

### Các module phụ thuộc vào IMM-00 (tất cả module):

- **IMM-01 đến IMM-17**: Tất cả đều cần IMM-00 hoàn thành trước khi bắt đầu build
- Thứ tự triển khai bắt buộc: `IMM-00 → IMM-04 → IMM-05 → IMM-08 → IMM-09 → IMM-11 → IMM-12`

---

## Tài liệu liên quan

- [Functional Specs](IMM-00_Functional_Specs.md) — User stories, acceptance criteria, business rules, permission matrix, validation rules
- [Technical Design](IMM-00_Technical_Design.md) — ERD, data dictionary, service layer, controller hooks
- [API Interface](IMM-00_API_Interface.md) — Endpoint specs, JSON payloads
- [UI/UX Guide](IMM-00_UI_UX_Guide.md) — Master data forms, search, inline validation
- [UAT Script](IMM-00_UAT_Script.md) — Test cases, acceptance scenarios
