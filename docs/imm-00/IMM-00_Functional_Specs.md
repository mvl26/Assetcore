# IMM-00 — Functional Specifications

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-00 Foundation |
| Phiên bản | 3.0.0 |
| Ngày cập nhật | 2026-04-18 |
| Trạng thái | **DRAFT** |
| Chuẩn tham chiếu | WHO HTM 2025, NĐ 98/2021/NĐ-CP, ISO 13485:2016, ISO/IEC 17025 |
| Dependency | **Chỉ Frappe Framework v15** (không dùng ERPNext) |

---

## 1. Mục đích & Scope

### 1.1 Mục đích

IMM-00 là **foundation layer tự chứa** của AssetCore, cung cấp toàn bộ DocTypes lõi, service functions, scheduler jobs và governance records cho 17 module IMM-xx kế tiếp. Module này thiết lập:

- Master data (AC Asset, AC Supplier, AC Location, AC Department, AC Asset Category)
- Domain catalog (IMM Device Model + Spare Part child)
- Policy store (IMM SLA Policy)
- Governance records (IMM Audit Trail, IMM CAPA Record, Asset Lifecycle Event, Incident Report)
- Shared services (`assetcore/services/imm00.py`) và utils (`response`, `lifecycle`, `email`, `pagination`)
- 4 daily schedulers (CAPA overdue, contract expiry, BYT expiry, KPI rollup)

### 1.2 In Scope

| # | Hạng mục | Ghi chú |
|---|---|---|
| 1 | 13 DocTypes (5 core kế thừa schema ERPNext + 6 governance + 2 child) | Tái tạo native, prefix `AC`/`IMM` |
| 2 | Lifecycle state machine cho `AC Asset.lifecycle_status` | 6 states, transition qua service layer |
| 3 | Audit trail bất biến với SHA-256 chain | Append-only, perm không có Write/Delete |
| 4 | CAPA workflow (Open → In Progress → Pending Verification → Closed / Overdue) | Submittable DocType |
| 5 | SLA lookup engine theo priority × risk_class | Fallback `is_default` |
| 6 | Incident Report → trigger Repair WO + CAPA | Submittable |
| 7 | Scheduler jobs (daily) | 4 jobs |
| 8 | Role fixtures + permission query | 8 roles IMM |

### 1.3 Out of Scope (defer sang giai đoạn sau)

| # | Hạng mục | Lý do defer |
|---|---|---|
| 1 | AC Item, AC Stock Entry, AC Purchase Order | Sẽ làm khi IMM-09 cần quản lý vật tư sửa chữa |
| 2 | AC Asset Movement | Sẽ làm khi IMM-06 (Asset Transfer) triển khai |
| 3 | Work Order DocType (PM/CM/Cal) | Thuộc IMM-08/09/11 |
| 4 | FHIR/HIS integration | IMM-15/16/17 |
| 5 | FE form builders ngoài AC Asset | Làm cuốn chiếu theo từng IMM-xx |

---

## 2. Actors & User Stories

### 2.1 Actors

| Role | Mô tả | Trách nhiệm chính trong IMM-00 |
|---|---|---|
| IMM System Admin | Quản trị viên hệ thống | Cấu hình SLA Policy, Device Model; seed fixtures; phân quyền |
| IMM Department Head | Trưởng phòng HTM / BGĐ kỹ thuật | Phê duyệt Device Model; nhận cảnh báo HĐ NCC, BYT expiry |
| IMM Operations Manager | Quản lý vận hành | CRUD AC Asset, AC Supplier; quản lý dữ liệu vận hành |
| IMM Workshop Lead | Trưởng xưởng kỹ thuật | Cập nhật Device Model; tạo CAPA; đóng Incident |
| IMM Technician | Kỹ thuật viên | Xem AC Asset (chỉ những thiết bị được gán); cập nhật PM/cal date sau thực hiện |
| IMM Document Officer | Nhân viên tài liệu | Xem Audit Trail; xuất báo cáo traceability |
| IMM Storekeeper | Thủ kho | Cập nhật AC Supplier, spare parts catalog |
| IMM QA Officer | Nhân viên QA/QC | Tạo/đóng CAPA; audit review; verify hash chain |

### 2.2 User Stories

| ID | As | I want | So that |
|---|---|---|---|
| US-00-01 | IMM Technician | Tra cứu thông số Device Model (PM interval, spare parts) | Chuẩn bị đúng vật tư trước PM |
| US-00-02 | IMM Operations Manager | Tạo mới AC Asset và liên kết Device Model | Bắt đầu theo dõi thiết bị trong hệ thống |
| US-00-03 | IMM Operations Manager | Cập nhật vị trí và khoa sử dụng của AC Asset | Phản ánh đúng thực tế bàn giao |
| US-00-04 | IMM Workshop Lead | Chuyển trạng thái thiết bị từ Active → Under Repair khi có sự cố | Block vận hành và kích hoạt quy trình sửa |
| US-00-05 | IMM Storekeeper | Quản lý NCC với chứng chỉ ISO 17025/13485 | Đảm bảo chỉ dùng lab hiệu chuẩn hợp pháp |
| US-00-06 | IMM System Admin | Cấu hình ma trận SLA P1–P4 × risk class | Các module IMM-08/09/11 tra cứu tự động |
| US-00-07 | IMM QA Officer | Xem toàn bộ Audit Trail với hash chain | Chứng minh tính toàn vẹn cho ISO 13485 audit |
| US-00-08 | IMM QA Officer | Tạo CAPA từ Incident hoặc audit finding | Thực hiện CAPA theo ISO 13485:8.5 |
| US-00-09 | IMM Department Head | Nhận email cảnh báo hợp đồng NCC sắp hết hạn | Kịp thời gia hạn, không gián đoạn dịch vụ |
| US-00-10 | IMM Department Head | Nhận cảnh báo đăng ký BYT hết hạn 90/60/30/7 ngày | Chủ động làm lại hồ sơ đăng ký |
| US-00-11 | Điều dưỡng / KTV | Báo cáo sự cố thiết bị qua Incident Report | Thiết bị được ngưng sử dụng và mở WO sửa chữa |
| US-00-12 | IMM Operations Manager | Xem danh sách thiết bị theo Department / Location tree | Phân bổ lại thiết bị khi cần |

---

## 3. Functional Requirements

### 3.1 Nhóm AC Asset (FR-00-01 → FR-00-05)

| FR ID | Mô tả | Actor | DocType chính | Phương thức |
|---|---|---|---|---|
| FR-00-01 | Tạo mới AC Asset với auto naming `AC-ASSET-.YYYY.-.#####` | Operations Manager, System Admin | AC Asset | POST `/api/method/assetcore.api.imm00.create_asset` |
| FR-00-02 | Đọc / list AC Asset với filter theo department, location, lifecycle_status, risk_classification | Tất cả role IMM | AC Asset | GET `/api/method/assetcore.api.imm00.list_assets` |
| FR-00-03 | Cập nhật AC Asset (trừ các read-only field: `lifecycle_status`, `risk_classification` fetched, `last_pm_date`, `last_calibration_date`) | Operations Manager | AC Asset | PUT `/api/method/assetcore.api.imm00.update_asset` |
| FR-00-04 | Chuyển trạng thái `lifecycle_status` qua service `transition_asset_status()` — không cho phép update trực tiếp | Workshop Lead, Operations Manager | AC Asset + Asset Lifecycle Event | Service call |
| FR-00-05 | Gate kiểm tra `validate_asset_for_operations()` — block nếu `lifecycle_status IN (Out of Service, Decommissioned)` | System (caller từ IMM-08/09/11) | AC Asset | Service call |

### 3.2 Nhóm AC Supplier (FR-00-06 → FR-00-09)

| FR ID | Mô tả | Actor | DocType chính | Phương thức |
|---|---|---|---|---|
| FR-00-06 | Tạo NCC với autoname `AC-SUP-.YYYY.-.####` | Storekeeper, Operations Manager | AC Supplier | POST create_supplier |
| FR-00-07 | Validate chứng chỉ ISO 17025 bắt buộc khi `vendor_type = Calibration Lab` | System | AC Supplier | `validate()` controller |
| FR-00-08 | Quản lý child table `authorized_technicians` (AC Authorized Technician) | Storekeeper | AC Supplier | Child table CRUD |
| FR-00-09 | Đánh dấu NCC không hoạt động (`is_active = 0`) — block khi AC Asset mới tham chiếu | System | AC Supplier | `validate()` AC Asset |

### 3.3 Nhóm AC Location / AC Department (FR-00-10 → FR-00-12)

| FR ID | Mô tả | Actor | DocType chính | Phương thức |
|---|---|---|---|---|
| FR-00-10 | Quản lý AC Location dạng tree (is_tree=1, parent_location, is_group) | System Admin, Operations Manager | AC Location | Tree view / POST create_location |
| FR-00-11 | Quản lý AC Department (phẳng hoặc tree) với mã khoa `AC-DEPT-.####` | System Admin | AC Department | CRUD |
| FR-00-12 | Validate AC Location không cho xoá khi còn AC Asset tham chiếu | System | AC Location | `on_trash()` hook |

### 3.4 Nhóm IMM Device Model (FR-00-13 → FR-00-15)

| FR ID | Mô tả | Actor | DocType chính | Phương thức |
|---|---|---|---|---|
| FR-00-13 | Tạo Device Model với autoname `IMM-MDL-.YYYY.-.####` | Workshop Lead, System Admin | IMM Device Model | POST create_device_model |
| FR-00-14 | Mapping tự động `medical_device_class` → `risk_classification` (Class I → Low; II → Medium; III → High/Critical) | System | IMM Device Model | `validate()` controller (BR-00-01) |
| FR-00-15 | Quản lý child table `spare_parts_list` (IMM Device Spare Part) | Workshop Lead, Storekeeper | IMM Device Model | Child CRUD |

### 3.5 Nhóm IMM SLA Policy (FR-00-16 → FR-00-18)

| FR ID | Mô tả | Actor | DocType chính | Phương thức |
|---|---|---|---|---|
| FR-00-16 | Tạo / cập nhật SLA Policy với ma trận priority × risk_class | System Admin | IMM SLA Policy | CRUD |
| FR-00-17 | Service `get_sla_policy(priority, risk_class)` trả về policy match; fallback `is_default=1` nếu không match | System (IMM-08/09/11) | IMM SLA Policy | Service call |
| FR-00-18 | Validate `response_time_minutes < resolution_time_hours × 60` (BR-00-07) | System | IMM SLA Policy | `validate()` |

### 3.6 Nhóm IMM Audit Trail (FR-00-19 → FR-00-22)

| FR ID | Mô tả | Actor | DocType chính | Phương thức |
|---|---|---|---|---|
| FR-00-19 | Service `log_audit_event(asset, event_type, actor, ref_doctype, ref_name, change_summary, from_status, to_status)` tạo record append-only | System (tất cả IMM modules) | IMM Audit Trail | Service call |
| FR-00-20 | Tính `hash_sha256` và liên kết `prev_hash` tạo hash chain | System | IMM Audit Trail | `log_audit_event()` |
| FR-00-21 | Block mọi update/delete trên IMM Audit Trail (controller throw, perm không có Write/Delete) | System | IMM Audit Trail | `validate()` + perm |
| FR-00-22 | API `verify_audit_chain(asset=None, from_date=None)` kiểm tra tính toàn vẹn hash chain | QA Officer | IMM Audit Trail | GET verify_audit_chain |

### 3.7 Nhóm IMM CAPA Record (FR-00-23 → FR-00-27)

| FR ID | Mô tả | Actor | DocType chính | Phương thức |
|---|---|---|---|---|
| FR-00-23 | Service `create_capa(asset, source_type, source_ref, severity, description, responsible, due_date)` tạo CAPA Draft | Workshop Lead, QA Officer | IMM CAPA Record | Service call |
| FR-00-24 | Validate `before_submit`: `root_cause`, `corrective_action`, `preventive_action` không trống; `status = Closed`; `due_date >= opened_date` | System | IMM CAPA Record | `before_submit()` (BR-00-08) |
| FR-00-25 | Service `close_capa(capa_name, effectiveness_check, verification_notes)` đóng CAPA và set `closed_date = today()` | QA Officer | IMM CAPA Record | Service call |
| FR-00-26 | Auto-mark Overdue khi `status IN (Open, In Progress)` và `due_date < today()` | System (scheduler) | IMM CAPA Record | `check_capa_overdue()` (BR-00-09) |
| FR-00-27 | Liên kết CAPA với Incident Report (`linked_incident`) — bidirectional | System | IMM CAPA Record + Incident Report | `on_submit()` + `on_submit()` Incident |

### 3.8 Nhóm Asset Lifecycle Event (FR-00-28 → FR-00-30)

| FR ID | Mô tả | Actor | DocType chính | Phương thức |
|---|---|---|---|---|
| FR-00-28 | Service `create_lifecycle_event(asset, event_type, actor, from_status, to_status, root_doctype, root_record, notes)` | System (tất cả modules) | Asset Lifecycle Event | Service call |
| FR-00-29 | Append-only enforcement (`in_create=1`, `validate()` block update) | System | Asset Lifecycle Event | Controller + perm |
| FR-00-30 | `transition_asset_status()` bắt buộc tạo 1 Asset Lifecycle Event mỗi lần đổi `lifecycle_status` (BR-00-10) | System | AC Asset + Asset Lifecycle Event | Service layer |

### 3.9 Nhóm Incident Report (FR-00-31 → FR-00-34)

| FR ID | Mô tả | Actor | DocType chính | Phương thức |
|---|---|---|---|---|
| FR-00-31 | Tạo Incident Report (Draft) với autoname `IR-.YYYY.-.####` | Điều dưỡng, KTV, Workshop Lead | Incident Report | POST create_incident |
| FR-00-32 | Validate `severity = Critical` → `reported_to_byt = 1` bắt buộc (NĐ98); `patient_affected = 1` → `patient_impact_description` bắt buộc | System | Incident Report | `validate()` (BR-INC-01/02) |
| FR-00-33 | On submit → auto tạo Asset Lifecycle Event `incident_reported` và gợi ý tạo CAPA nếu `severity >= High` (warning non-blocking) | System | Incident Report + ALE + CAPA | `on_submit()` (BR-INC-03/04) |
| FR-00-34 | Đóng Incident khi `status = Closed` và có `resolution_notes` — set `closed_date = today()` | Workshop Lead | Incident Report | Update + service |

### 3.10 Nhóm GMDN Status Management (FR-00-38 → FR-00-42)

> **Phạm vi:** Theo dõi thiết bị đang được sử dụng hay không (ví dụ: máy đang phục vụ bệnh nhân). Trạng thái mặc định là `Không sử dụng` — bác sĩ/KTV quét QR khi bắt đầu dùng, quét lại khi kết thúc.

| FR ID | Mô tả | Actor | DocType chính | Phương thức |
|---|---|---|---|---|
| FR-00-38 | AC Asset có field `gmdn_status` (Select: `Đang sử dụng` / `Không sử dụng`, **default=`Không sử dụng`**) — riêng biệt với `gmdn_code` (mã GMDN fetch từ Device Model) | Operations Manager, System Admin | AC Asset | DocType field |
| FR-00-39 | Filter và hiển thị `gmdn_status` trong `list_assets()` + cột GMDN trong `AssetListView` | Tất cả role IMM | AC Asset | GET `list_assets?gmdn_status=...` |
| FR-00-40 | API `update_gmdn_status(name, gmdn_status, reason)` — cập nhật thủ công có lý do, ghi IMM Audit Trail event `gmdn_status_changed` | Operations Manager, System Admin | AC Asset + IMM Audit Trail | POST `update_gmdn_status` |
| FR-00-41 | **QR Scan Toggle Flow:** quét QR → API `toggle_gmdn_status(name)` tự động đảo trạng thái (`Không sử dụng ↔ Đang sử dụng`) với reason auto-generated `"Quét QR lúc <timestamp>"`. Không cần nhập lý do | KTV / Bác sĩ tại hiện trường | AC Asset | POST `toggle_gmdn_status` qua `/qr-scan` |
| FR-00-42 | Block chuyển `gmdn_status → Đang sử dụng` khi `lifecycle_status IN (Decommissioned, Out of Service)` — thiết bị đã nghỉ hưu không thể kích hoạt | System | AC Asset | `validate()` + service (BR-00-11) |

**Business Rule mới:**

| BR ID | Business Rule | Enforce tại | Chuẩn |
|---|---|---|---|
| BR-00-11 | `gmdn_status` không thể chuyển về `Đang sử dụng` khi `lifecycle_status ∈ {Decommissioned, Out of Service}` | `update_gmdn_status()` service | NĐ 98/2021 |
| BR-00-12 | Mọi thay đổi `gmdn_status` phải có `reason` (≥ 5 ký tự) và ghi IMM Audit Trail | Service layer | ISO 13485:8.2 |

**User Stories bổ sung:**

| ID | As | I want | So that |
|---|---|---|---|
| US-00-13 | IMM Technician | Quét QR thiết bị và toggle GMDN status ngay tại hiện trường | Cập nhật nhanh trạng thái GMDN mà không cần mở máy tính |
| US-00-14 | IMM Operations Manager | Lọc danh sách thiết bị theo GMDN status | Xác định thiết bị nào đang/không còn đăng ký GMDN |
| US-00-15 | IMM QA Officer | Xem audit trail đầy đủ mỗi lần thay đổi GMDN status | Chứng minh traceability đăng ký GMDN theo NĐ98 |

### 3.11 Nhóm Scheduler Jobs (FR-00-35 → FR-00-37)

| FR ID | Mô tả | Tần suất | Đối tượng nhận email |
|---|---|---|---|
| FR-00-35 | `check_capa_overdue` — CAPA Open/In Progress + `due_date < today` → status = Overdue + email | Daily 02:00 | `responsible` + IMM QA Officer |
| FR-00-36 | `check_vendor_contract_expiry` — `contract_end - today IN (90, 60, 30)` → email cảnh báo | Daily 02:15 | IMM Department Head + IMM Storekeeper |
| FR-00-37 | `check_registration_expiry` — `byt_reg_expiry - today IN (90, 60, 30, 7)` AND `lifecycle_status != Decommissioned` → email | Daily 02:30 | IMM Department Head + IMM Operations Manager |

(FR-00-38 extra) `rollup_asset_kpi` — tính MTTR avg, PM compliance %, CAPA closure rate; ghi vào table `tabAssetCore KPI Snapshot` (không gửi email) — Daily 03:00.

---

## 4. Business Rules

Copy từ IMM-00 Module Overview §8. Tất cả BR bắt buộc enforce.

| BR ID | Business Rule | Enforce tại | Chuẩn |
|---|---|---|---|
| BR-00-01 | Class I → Low; Class II → Medium; Class III → High/Critical (mapping cứng) | `IMMDeviceModel.validate()` | NĐ 98/2021 |
| BR-00-02 | `AC Asset.lifecycle_status` chỉ thay đổi qua `transition_asset_status()` (không set trực tiếp) | Service layer + `AC Asset.validate()` | Internal |
| BR-00-03 | IMM Audit Trail và Asset Lifecycle Event immutable (không Update/Delete perm, controller block is_new()=False) | Controller + Permission | ISO 13485:7.5.9 |
| BR-00-11 | `gmdn_status` không thể chuyển về `Đang sử dụng` khi `lifecycle_status ∈ {Decommissioned, Out of Service}` | `update_gmdn_status()` service + `validate()` | NĐ 98/2021 |
| BR-00-12 | Mọi thay đổi `gmdn_status` phải có `reason` ≥ 5 ký tự và ghi IMM Audit Trail event `gmdn_status_changed` | `update_gmdn_status()` service | ISO 13485:8.2 |
| BR-00-04 | Decommissioned → auto suspend tất cả PM/Calibration Schedule liên quan | `transition_asset_status()` | WHO HTM |
| BR-00-05 | Out of Service / Decommissioned → block tạo Work Order (PM/CM/Cal) | `validate_asset_for_operations()` | WHO HTM |
| BR-00-06 | AC Supplier `vendor_type = Calibration Lab` → warning nếu thiếu `iso_17025_cert` | `ACSupplier.validate()` | ISO/IEC 17025 |
| BR-00-07 | SLA `response_time_minutes < resolution_time_hours × 60` | `IMMSLAPolicy.validate()` | Internal |
| BR-00-08 | CAPA `before_submit` bắt buộc có `root_cause + corrective_action + preventive_action` | `IMMCAPARecord.before_submit()` | ISO 13485:8.5 |
| BR-00-09 | CAPA quá `due_date` → auto Overdue qua daily scheduler | `check_capa_overdue()` | Internal |
| BR-00-10 | Mọi thay đổi `lifecycle_status` phải sinh 1 Asset Lifecycle Event | `transition_asset_status()` | Audit trail |

---

## 5. Non-Functional Requirements

| NFR ID | Category | Yêu cầu | Target |
|---|---|---|---|
| NFR-00-01 | Performance — List query | GET list AC Asset với filter chuẩn | P95 < 200 ms với 100k records |
| NFR-00-02 | Performance — Detail | GET single AC Asset (full) | P95 < 500 ms |
| NFR-00-03 | Performance — Audit write | `log_audit_event()` | P95 < 100 ms |
| NFR-00-04 | Concurrency | Cùng 1 AC Asset bị 2 user edit | Optimistic lock qua Frappe `modified` timestamp; user thứ 2 nhận TimestampMismatchError |
| NFR-00-05 | Audit retention | Không xoá IMM Audit Trail, Asset Lifecycle Event | Giữ tối thiểu 7 năm (theo NĐ98) |
| NFR-00-06 | Backup | Daily full DB backup + hourly binlog | RPO ≤ 1h, RTO ≤ 4h |
| NFR-00-07 | Security — Perm | Role-based + Permission Query cho IMM Technician (chỉ AC Asset được gán) | Enforced qua `permission.py` |
| NFR-00-08 | Security — Audit integrity | SHA-256 chain phải verify thành công cho toàn bộ bản ghi | API `verify_audit_chain` trả về `{valid: true, count, last_hash}` |
| NFR-00-09 | Internationalization | Toàn bộ error message qua `frappe._()` | Gói ngôn ngữ `vi.csv` |
| NFR-00-10 | Logging | Tất cả service function log request_id + actor | `frappe.logger("imm00")` |
| NFR-00-11 | API contract | Response chuẩn `_ok(data)` / `_err(msg, code)` | Enforce qua `utils/response.py` |
| NFR-00-12 | Scheduler reliability | 4 scheduler jobs phải idempotent | Retry tối đa 3 lần, fail → ERROR log + email admin |
| NFR-00-13 | Tree query | AC Location tree depth ≤ 6 | Lft/rgt nested set (Frappe NestedSet) |
| NFR-00-14 | Scalability | Hệ thống chịu 500k AC Asset, 5M IMM Audit Trail | Index theo §10 Technical Design |

---

## 6. Validation Rules

### 6.1 AC Asset (VR-00-01 → VR-00-08)

| VR ID | Field | Rule | Error Message (vi) |
|---|---|---|---|
| VR-00-01 | `asset_code` | UNIQUE nếu có giá trị | "Mã tài sản {code} đã tồn tại." |
| VR-00-02 | `manufacturer_sn` | UNIQUE nếu có giá trị | "Số serial NSX {sn} đã tồn tại." |
| VR-00-03 | `pm_interval_days` | Bắt buộc nếu `is_pm_required = 1`; > 0 | "Phải nhập chu kỳ PM (ngày) khi bật Yêu cầu PM." |
| VR-00-04 | `calibration_interval_days` | Bắt buộc nếu `is_calibration_required = 1`; > 0 | "Phải nhập chu kỳ hiệu chuẩn (ngày)." |
| VR-00-05 | `next_pm_date` | Auto = `last_pm_date + pm_interval_days` (on save) | — (auto) |
| VR-00-06 | `next_calibration_date` | Auto = `last_calibration_date + calibration_interval_days` | — (auto) |
| VR-00-07 | `byt_reg_expiry` | >= `purchase_date` nếu cả 2 có giá trị | "Hạn đăng ký BYT phải sau ngày mua." |
| VR-00-08 | `lifecycle_status` | Chỉ đổi qua service (BR-00-02) | "Trạng thái vòng đời chỉ thay đổi qua `transition_asset_status()`." |

### 6.2 AC Supplier (VR-00-09 → VR-00-12)

| VR ID | Field | Rule | Error Message (vi) |
|---|---|---|---|
| VR-00-09 | `iso_17025_cert` | Warning nếu `vendor_type = Calibration Lab` và trống | "Cảnh báo: NCC là Calibration Lab nhưng chưa có chứng chỉ ISO 17025." |
| VR-00-10 | `contract_end` | >= `contract_start` nếu cả 2 có giá trị | "Ngày kết thúc hợp đồng phải >= ngày bắt đầu." |
| VR-00-11 | `email_id` | Email format hợp lệ | "Email không đúng định dạng." |
| VR-00-12 | `supplier_code` | UNIQUE nếu có giá trị | "Mã NCC {code} đã tồn tại." |

### 6.3 IMM Device Model (VR-00-13 → VR-00-15)

| VR ID | Field | Rule | Error Message (vi) |
|---|---|---|---|
| VR-00-13 | `risk_classification` | Auto-set theo `medical_device_class` (BR-00-01) | — (auto) |
| VR-00-14 | `gmdn_code` | 5–6 ký tự số nếu có giá trị | "Mã GMDN phải gồm 5–6 ký tự số." |
| VR-00-15 | `pm_interval_days_default` | > 0 nếu `requires_pm = 1` | "Chu kỳ PM mặc định phải > 0." |

### 6.4 IMM SLA Policy (VR-00-16 → VR-00-17)

| VR ID | Field | Rule | Error Message (vi) |
|---|---|---|---|
| VR-00-16 | `response_time_minutes` | < `resolution_time_hours × 60` (BR-00-07) | "Thời gian phản hồi phải nhỏ hơn thời gian xử lý." |
| VR-00-17 | (fixture) | Mỗi `priority` phải có ít nhất 1 policy `is_default = 1` | "Priority {p} chưa có policy mặc định." |

### 6.5 IMM CAPA Record (VR-00-18 → VR-00-22)

| VR ID | Field | Rule | Error Message (vi) |
|---|---|---|---|
| VR-00-18 | `due_date` | >= `opened_date` | "Hạn hoàn thành phải sau ngày mở CAPA." |
| VR-00-19 | `closed_date` | >= `opened_date` nếu có | "Ngày đóng phải sau ngày mở CAPA." |
| VR-00-20 | `root_cause` | reqd before_submit | "Phải nhập phân tích nguyên nhân gốc rễ trước khi Submit CAPA." |
| VR-00-21 | `corrective_action` | reqd before_submit | "Phải nhập hành động khắc phục trước khi Submit CAPA." |
| VR-00-22 | `preventive_action` | reqd before_submit | "Phải nhập hành động phòng ngừa trước khi Submit CAPA." |

### 6.6 Incident Report (VR-00-23 → VR-00-25)

| VR ID | Field | Rule | Error Message (vi) |
|---|---|---|---|
| VR-00-23 | `reported_to_byt` | Phải = 1 nếu `severity = Critical` (BR-INC-01) | "Sự cố mức Critical phải được báo cáo Bộ Y tế (NĐ98)." |
| VR-00-24 | `patient_impact_description` | reqd nếu `patient_affected = 1` | "Phải mô tả tác động đến bệnh nhân." |
| VR-00-25 | `byt_report_date` | reqd nếu `reported_to_byt = 1` | "Phải nhập ngày báo cáo BYT." |

### 6.7 IMM Audit Trail & Asset Lifecycle Event (VR-00-26 → VR-00-27)

| VR ID | Field | Rule | Error Message (vi) |
|---|---|---|---|
| VR-00-26 | (record) | `not is_new()` → throw | "Bản ghi Audit Trail/Lifecycle Event là bất biến, không được sửa." |
| VR-00-27 | `hash_sha256` | Bắt buộc có giá trị trước insert | "Thiếu hash SHA-256, không thể ghi Audit Trail." |

---

## 7. Acceptance Criteria (Gherkin)

### 7.1 AC Asset Lifecycle

**Scenario 7.1.1: Tạo AC Asset mới thành công**
```gherkin
Given tôi có vai trò "IMM Operations Manager"
And đã có IMM Device Model "IMM-MDL-2026-0001" (Class II, Medium)
When tôi POST /api/method/assetcore.api.imm00.create_asset với
  {"asset_name": "Monitor Philips", "device_model": "IMM-MDL-2026-0001",
   "location": "AC-LOC-2026-0001", "department": "AC-DEPT-0001"}
Then response.status = 200
And response.data.name khớp regex "^AC-ASSET-2026-\d{5}$"
And doc.risk_classification = "Medium" (fetched từ device_model)
And có 1 IMM Audit Trail event_type="State Change", actor=session.user
```

**Scenario 7.1.2: Chuyển trạng thái Active → Under Repair**
```gherkin
Given AC Asset "AC-ASSET-2026-00001" đang ở lifecycle_status = "Active"
When IMM-09 gọi transition_asset_status(asset="AC-ASSET-2026-00001",
  to_status="Under Repair", root_doctype="Work Order", root_record="WO-2026-0001")
Then AC Asset.lifecycle_status = "Under Repair"
And có 1 Asset Lifecycle Event event_type="repair_opened", from_status="Active", to_status="Under Repair"
And có 1 IMM Audit Trail liên kết
```

**Scenario 7.1.3: Block update trực tiếp lifecycle_status**
```gherkin
Given AC Asset "AC-ASSET-2026-00001" ở Active
When tôi PUT /api/method/assetcore.api.imm00.update_asset với {"lifecycle_status": "Decommissioned"}
Then response.status = 400
And response.error.message chứa "chỉ thay đổi qua `transition_asset_status()`"
```

**Scenario 7.1.4: Gate validate_asset_for_operations block**
```gherkin
Given AC Asset ở lifecycle_status = "Out of Service"
When IMM-08 gọi validate_asset_for_operations("AC-ASSET-2026-00001")
Then service throw ValidationError với code "ASSET_NOT_OPERATIONAL"
And message "Thiết bị ở trạng thái Out of Service, không thể tạo Work Order"
```

**Scenario 7.1.5: Decommission suspend PM schedules**
```gherkin
Given AC Asset có is_pm_required=1, next_pm_date=2026-06-01
When transition_asset_status(to_status="Decommissioned", reason="End of Life")
Then AC Asset.lifecycle_status = "Decommissioned"
And AC Asset.is_pm_required = 0 (suspended)
And AC Asset.next_pm_date = NULL
And có Asset Lifecycle Event event_type="decommissioned"
```

### 7.2 AC Supplier

**Scenario 7.2.1: Warning khi Calibration Lab thiếu ISO 17025**
```gherkin
Given tôi tạo AC Supplier với vendor_type="Calibration Lab", iso_17025_cert=""
When save
Then nhận msgprint warning "NCC là Calibration Lab nhưng chưa có chứng chỉ ISO 17025"
And record vẫn được lưu (warning, không block)
```

**Scenario 7.2.2: Block contract_end trước contract_start**
```gherkin
Given AC Supplier với contract_start="2026-01-01", contract_end="2025-12-31"
When save
Then throw ValidationError "Ngày kết thúc hợp đồng phải >= ngày bắt đầu"
```

### 7.3 IMM SLA Policy

**Scenario 7.3.1: Tra cứu SLA match priority × risk_class**
```gherkin
Given fixture có policy {priority: "P1 Critical", risk_class: "Critical", response: 15, resolution: 4}
When gọi get_sla_policy(priority="P1 Critical", risk_class="Critical")
Then trả về policy có response_time_minutes=15, resolution_time_hours=4
```

**Scenario 7.3.2: Fallback is_default khi không match risk_class**
```gherkin
Given fixture có policy P2 với is_default=1, risk_class=NULL, response=240, resolution=48
And không có policy P2 với risk_class="Medium"
When gọi get_sla_policy(priority="P2", risk_class="Medium")
Then trả về policy is_default
```

**Scenario 7.3.3: Block response_time >= resolution_time × 60**
```gherkin
Given tôi tạo SLA Policy với response_time_minutes=300, resolution_time_hours=4
When save
Then throw ValidationError "Thời gian phản hồi phải nhỏ hơn thời gian xử lý" (300 !< 240)
```

### 7.4 IMM Audit Trail

**Scenario 7.4.1: Ghi audit với SHA-256 chain**
```gherkin
Given IMM Audit Trail mới nhất có hash_sha256 = "abc123..."
When log_audit_event(asset="AC-ASSET-2026-00001", event_type="State Change", ...)
Then record mới có prev_hash = "abc123..."
And hash_sha256 tính từ SHA256(payload + prev_hash)
```

**Scenario 7.4.2: Block update IMM Audit Trail**
```gherkin
Given IMM Audit Trail "IMM-AUD-2026-0000001" đã tồn tại
When tôi thử frappe.db.set_value hoặc doc.save() trên record này
Then throw ValidationError "Bản ghi Audit Trail bất biến, không được sửa"
```

**Scenario 7.4.3: verify_audit_chain toàn vẹn**
```gherkin
Given 1000 IMM Audit Trail liên tiếp tạo qua log_audit_event
When GET /api/method/assetcore.api.imm00.verify_audit_chain
Then response.data = {valid: true, count: 1000, last_hash: "..."}
```

### 7.5 IMM CAPA Record

**Scenario 7.5.1: Tạo CAPA từ Incident**
```gherkin
Given Incident Report "IR-2026-0001" severity=Major đã submitted
When QA Officer gọi create_capa(asset, source_type="Incident", source_ref="IR-2026-0001", ...)
Then CAPA Draft được tạo, status="Open", linked_incident="IR-2026-0001"
And Incident.linked_capa = "CAPA-2026-00001"
```

**Scenario 7.5.2: Block submit CAPA thiếu root_cause**
```gherkin
Given CAPA Draft với root_cause=NULL
When submit
Then throw ValidationError "Phải nhập phân tích nguyên nhân gốc rễ trước khi Submit CAPA"
```

**Scenario 7.5.3: Auto Overdue CAPA quá hạn**
```gherkin
Given CAPA status="Open", due_date="2026-04-10" (today=2026-04-18)
When scheduler check_capa_overdue chạy
Then CAPA.status = "Overdue"
And email gửi tới responsible + IMM QA Officer
```

**Scenario 7.5.4: Close CAPA với effectiveness check**
```gherkin
Given CAPA status="Pending Verification", đã có root_cause + corrective + preventive
When close_capa(name, effectiveness_check="Effective", verification_notes="...")
Then CAPA.status = "Closed", closed_date=today()
And docstatus = 1
```

### 7.6 Incident Report

**Scenario 7.6.1: Critical severity phải báo cáo BYT**
```gherkin
Given Incident với severity="Critical", reported_to_byt=0
When submit
Then throw ValidationError "Sự cố mức Critical phải được báo cáo Bộ Y tế (NĐ98)"
```

**Scenario 7.6.2: Submit Incident sinh Asset Lifecycle Event**
```gherkin
Given Incident Draft hợp lệ, severity="High"
When submit
Then có 1 Asset Lifecycle Event event_type="incident_reported"
And nhận msgprint gợi ý tạo CAPA (severity >= High)
```

### 7.7 Scheduler Jobs

**Scenario 7.7.1: Cảnh báo hợp đồng NCC sắp hết hạn**
```gherkin
Given AC Supplier "AC-SUP-2026-0001" có contract_end=2026-07-17 (today=2026-04-18, diff=90 ngày)
When scheduler check_vendor_contract_expiry chạy
Then email gửi tới IMM Department Head + IMM Storekeeper
And subject "Hợp đồng NCC sắp hết hạn (90 ngày): AC-SUP-2026-0001"
```

**Scenario 7.7.2: Cảnh báo BYT expiry bỏ qua Decommissioned**
```gherkin
Given AC Asset A có byt_reg_expiry=2026-07-17, lifecycle_status="Active"
And AC Asset B có cùng byt_reg_expiry, lifecycle_status="Decommissioned"
When scheduler check_registration_expiry chạy
Then chỉ có email cho Asset A, không gửi cho B
```

### 7.8 Asset Lifecycle Event

**Scenario 7.8.1: Append-only**
```gherkin
Given Asset Lifecycle Event "ALE-2026-0000001" đã tồn tại
When tôi thử update hoặc delete
Then throw ValidationError "Bản ghi Lifecycle Event bất biến"
```

---

## 8. Dependencies & Integration Points

| Module | Phụ thuộc IMM-00 qua |
|---|---|
| IMM-04 Installation | `create_lifecycle_event("commissioned")`, `validate_asset_for_operations()`, AC Asset.commissioning_date |
| IMM-05 Registration | AC Asset.byt_reg_no, byt_reg_expiry, `check_registration_expiry` |
| IMM-08 PM | `get_sla_policy()`, `validate_asset_for_operations()`, AC Asset.next_pm_date, `create_lifecycle_event("pm_completed")` |
| IMM-09 Repair | Incident Report trigger, `transition_asset_status(Active ↔ Under Repair)`, `create_capa()` |
| IMM-11 Calibration | AC Supplier.iso_17025_cert gate, AC Asset.next_calibration_date, `get_sla_policy()` |
| IMM-12 Corrective | `create_capa()` từ audit finding, `transition_asset_status(→ Out of Service)` |
| IMM-13 End of Life | `transition_asset_status(→ Decommissioned)`, suspend schedules |

---

## 9. Revision History

| Version | Date | Author | Thay đổi chính |
|---|---|---|---|
| 1.0.0 | 2025-12-15 | AssetCore Team | Bản khởi tạo (ERPNext Asset + sidecar profiles) |
| 2.0.0 | 2026-03-10 | AssetCore Team | Chuẩn hoá sidecar + service layer |
| **3.0.0** | **2026-04-18** | **AssetCore Team** | **Tái cấu trúc Frappe-only; 13 DocTypes native; bỏ sidecar; đổi số FR theo 10 nhóm; cập nhật VR/BR/Gherkin** |
| **3.1.0** | **2026-04-22** | **AssetCore Team** | **Bổ sung FR-00-38→42: GMDN Status Management + QR scan toggle + BR-00-11/12** |

---

## 10. Glossary

| Thuật ngữ | Nghĩa |
|---|---|
| AC | AssetCore — prefix cho core DocType (Asset, Supplier, Location, Department, Asset Category) |
| IMM | Installation & Medical Maintenance — prefix cho governance DocType |
| ALE | Asset Lifecycle Event — sự kiện vòng đời chuẩn hoá |
| CAPA | Corrective And Preventive Action (ISO 13485:8.5) |
| SLA | Service Level Agreement — ma trận priority × risk_class |
| HTM | Health Technology Management (WHO) |
| BYT | Bộ Y tế Việt Nam |
| GMDN | Global Medical Device Nomenclature |
| UDI | Unique Device Identifier (GS1/HIBC) |
| NĐ98 | Nghị định 98/2021/NĐ-CP về quản lý trang thiết bị y tế |

---

*End of Functional Specifications v3.0.0 — IMM-00 Foundation Module*
