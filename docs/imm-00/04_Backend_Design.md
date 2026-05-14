# 04 — Backend Design — IMM-00 Foundation (Master / Cross-cutting)

| Mục | Giá trị |
|---|---|
| Module | IMM-00 — Foundation / Master Cross-cutting |
| Phạm vi | Foundation — cross-cutting |
| Owner | Tech Lead / BE Lead |
| Liên kết | [03 Diagrams](./03_Diagrams.md) · [05 API Specification](./05_API_Specification.md) |
| Phiên bản | 4.1.0 |
| Trạng thái | **Live ✅** — đã implement, synced vs codebase 2026-05-14 |

---

# Phần I — DocType Catalog

## I.1. DocTypes chính của IMM-00 Foundation (tất cả đã Live)

DocType folder path: `assetcore/assetcore/doctype/` (78 folders tổng — bảng sau liệt kê các DocType nằm trong phạm vi IMM-00 foundation và cross-cutting).

| # | DocType (snake_case folder) | Tên hiển thị | Submittable | Tree | Ghi chú |
|---|---|---|---|---|---|
| 1 | `ac_asset` | AC Asset | — | — | Core asset registry |
| 2 | `ac_asset_category` | AC Asset Category | — | — | Danh mục thiết bị |
| 3 | `ac_asset_depreciation_schedule` | AC Asset Depreciation Schedule | — | — | Child table khấu hao |
| 4 | `ac_asset_downtime_log` | AC Asset Downtime Log | — | — | Log dừng máy |
| 5 | `ac_authorized_technician` | AC Authorized Technician | — | — | Child table của AC Supplier |
| 6 | `ac_department` | AC Department | — | ✅ | Khoa/phòng ban (tree) |
| 7 | `ac_location` | AC Location | — | ✅ | Vị trí (tree) |
| 8 | `ac_spare_part` | AC Spare Part | — | — | Danh mục phụ tùng |
| 9 | `ac_spare_part_stock` | AC Spare Part Stock | — | — | Tồn kho phụ tùng |
| 10 | `ac_stock_movement` | AC Stock Movement | ✅ | — | Phiếu nhập/xuất kho |
| 11 | `ac_stock_movement_item` | AC Stock Movement Item | — | — | Child table stock movement |
| 12 | `ac_supplier` | AC Supplier | — | — | Nhà cung cấp / vendor |
| 13 | `ac_warehouse` | AC Warehouse | — | — | Kho vật tư |
| 14 | `asset_lifecycle_event` | Asset Lifecycle Event | — | — | Append-only lifecycle log |
| 15 | `asset_transfer` | Asset Transfer | — | — | Phiếu luân chuyển |
| 16 | `document_request` | Document Request | — | — | Yêu cầu hồ sơ tài liệu |
| 17 | `firmware_change_request` | Firmware Change Request | — | — | Yêu cầu thay đổi firmware |
| 18 | `imm_audit_trail` | IMM Audit Trail | — | — | SHA-256 chain audit log |
| 19 | `imm_capa_record` | IMM CAPA Record | ✅ | — | CAPA nghiệp vụ |
| 20 | `imm_device_model` | IMM Device Model | — | — | Model thiết bị y tế |
| 21 | `imm_device_spare_part` | IMM Device Spare Part | — | — | Child table spare parts BOM |
| 22 | `imm_sla_policy` | IMM SLA Policy | — | — | Chính sách SLA |
| 23 | `incident_report` | Incident Report | ✅ | — | Báo cáo sự cố |
| 24 | `pm_checklist_template` | PM Checklist Template | — | — | Template checklist PM |
| 25 | `pm_schedule` | PM Schedule | — | — | Lịch PM định kỳ |
| 26 | `service_contract` | Service Contract | ✅ | — | Hợp đồng dịch vụ |
| 27 | `service_contract_asset` | Service Contract Asset | — | — | Child: assets trong HĐ |

> Các DocType khác (imm_needs_request, imm_procurement_plan, asset_commissioning, v.v.) thuộc phạm vi các module IMM-01→IMM-17.
> Xem danh sách đầy đủ tại `assetcore/assetcore/doctype/` (78 folders).

---

# Phần II — DocType Schemas

## II.1. AC Asset

**File:** `assetcore/assetcore/doctype/ac_asset/ac_asset.json`  
**Controller:** `assetcore/assetcore/doctype/ac_asset/ac_asset.py`  
**Module:** AssetCore  
**is_submittable:** — (không submit) · **track_changes:** 1 · **allow_import:** 1

### II.1.1 Fields — Thông tin cơ bản

| Field | DB Type | Required | Description | BR/Note |
|---|---|---|---|---|
| `name` | varchar(140) PK | YES | Autoname AC-ASSET-2026-00001 | Unique, immutable |
| `asset_name` | varchar(140) | YES | Tên thiết bị | in_list_view, reqd |
| `asset_code` | varchar(140) | NO | Mã tài sản nội bộ | UNIQUE nếu có; IDX; dùng QR/barcode |
| `asset_category` | varchar(140) | YES | Link → AC Asset Category | IDX |
| `status` | varchar(50) | YES | Trạng thái Frappe native | Select: Submitted/Active/Out of Service/… |

### II.1.2 Fields — Vị trí và phụ trách

| Field | DB Type | Required | Description | BR/Note |
|---|---|---|---|---|
| `location` | varchar(140) | NO | Link → AC Location | IDX |
| `department` | varchar(140) | NO | Link → AC Department | IDX |
| `custodian` | varchar(140) | NO | Link → User | Người giữ |
| `responsible_technician` | varchar(140) | NO | Link → User | IDX; Permission Query |

### II.1.3 Fields — HTM (Health Technology Management)

| Field | DB Type | Required | Description | BR/Note |
|---|---|---|---|---|
| `device_model` | varchar(140) | NO | Link → IMM Device Model | IDX; fetch source |
| `medical_device_class` | varchar(20) | NO | Class I/II/III | fetch_from device_model |
| `risk_classification` | varchar(20) | NO | Low/Medium/High/Critical | read_only; fetch_from |
| `manufacturer_sn` | varchar(140) | NO | Số serial NSX | IDX; UNIQUE nếu có |
| `udi_code` | varchar(140) | NO | Mã UDI (GS1/HIBC) | IDX |
| `gmdn_code` | varchar(20) | NO | Mã GMDN (5–6 số) | fetch_from device_model |
| `gmdn_status` | varchar(50) | NO | Select `In Use` / `Not Use` (DocType options) | default `Not Use`; `read_only=1` (chỉ đổi qua `update_gmdn_status` / `toggle_gmdn_status`) |

### II.1.4 Fields — Đăng ký BYT

| Field | DB Type | Required | Description | BR/Note |
|---|---|---|---|---|
| `byt_reg_no` | varchar(140) | NO | Số đăng ký lưu hành BYT | IDX |
| `byt_reg_expiry` | date | NO | Hạn đăng ký | IDX; scheduler cảnh báo |

### II.1.5 Fields — Lifecycle

| Field | DB Type | Required | Description | BR/Note |
|---|---|---|---|---|
| `lifecycle_status` | varchar(50) | YES | Commissioned/Active/Under Repair/Calibrating/Out of Service/Decommissioned | IDX; chỉ đổi qua service |
| `commissioning_date` | date | NO | Ngày nghiệm thu từ IMM-04 | — |
| `commissioning_ref` | varchar(140) | NO | Tham chiếu biên bản | Dynamic Link |

### II.1.6 Fields — PM và Calibration

| Field | DB Type | Required | Description | BR/Note |
|---|---|---|---|---|
| `is_pm_required` | tinyint(1) | NO | Cần PM định kỳ | Check; fetch_from device_model |
| `pm_interval_days` | int(11) | COND | Chu kỳ PM (ngày) | reqd nếu is_pm_required=1 |
| `last_pm_date` | date | NO | Ngày PM gần nhất | read_only; cập nhật bởi IMM-08 |
| `next_pm_date` | date | NO | Ngày PM tiếp theo | IDX; auto = last + interval |
| `is_calibration_required` | tinyint(1) | NO | Cần hiệu chuẩn | Check; fetch_from device_model |
| `calibration_interval_days` | int(11) | COND | Chu kỳ hiệu chuẩn (ngày) | reqd nếu is_calibration_required=1 |
| `last_calibration_date` | date | NO | Ngày hiệu chuẩn gần nhất | read_only; cập nhật bởi IMM-11 |
| `next_calibration_date` | date | NO | Ngày hiệu chuẩn tiếp theo | IDX; auto = last + interval |

### II.1.7 State machine — lifecycle_status

| Từ | Sang | Trigger | Service |
|---|---|---|---|
| (new) | Commissioned | IMM-04 Complete | `create_lifecycle_event("commissioned")` |
| Commissioned | Active | Confirm operational | `transition_asset_status()` |
| Active | Under Repair | Tạo Repair WO (IMM-09) | `transition_asset_status()` |
| Active | Calibrating | Tạo Calibration WO (IMM-11) | `transition_asset_status()` |
| Active | Out of Service | Manual + lý do | `transition_asset_status()` |
| Under Repair | Active | WO sửa chữa hoàn thành | `transition_asset_status()` |
| Calibrating | Active | WO hiệu chuẩn hoàn thành | `transition_asset_status()` |
| Out of Service | Active | Phê duyệt khôi phục | `transition_asset_status()` |
| * | Decommissioned | IMM-13 End of Life | `transition_asset_status()` — không hoàn tác |

## II.2. AC Supplier

**Autoname:** `AC-SUP-.YYYY.-.####` · **is_submittable:** 1 · **track_changes:** 1

| Field | DB Type | Required | Description | BR/Note |
|---|---|---|---|---|
| `supplier_name` | varchar(140) | YES | Tên NCC | in_list_view |
| `supplier_code` | varchar(140) | NO | Mã NCC nội bộ | UNIQUE nếu có |
| `vendor_type` | varchar(50) | YES | Manufacturer/Distributor/Calibration Lab/Service Provider | IDX |
| `iso_17025_cert` | varchar(140) | NO | Số chứng chỉ ISO/IEC 17025 | BR-00-06: warning nếu Calibration Lab + trống |
| `iso_17025_expiry` | date | NO | Hết hạn ISO 17025 | — |
| `iso_13485_cert` | varchar(140) | NO | Số chứng chỉ ISO 13485 | — |
| `contract_start` | date | NO | Ngày bắt đầu HĐ | — |
| `contract_end` | date | NO | Ngày kết thúc HĐ | IDX; scheduler cảnh báo |
| `contract_value` | decimal(21,9) | NO | Giá trị HĐ (VND) | Currency |
| `is_active` | tinyint(1) | NO | Còn hoạt động | default 1 |
| `authorized_technicians` | Table | NO | Child → AC Authorized Technician | — |

## II.3. AC Asset Category

**Autoname:** `by category_name` · **track_changes:** 1

> **Nguồn dữ liệu GMDN.** Mỗi danh mục thiết bị gắn với một mã GMDN — đây là cấp đầu tiên trong chuỗi kế thừa: `Category → Device Model → Asset`.

| Field | DB Type | Required | Description | BR/Note |
|---|---|---|---|---|
| `category_name` | varchar(140) | YES | Tên danh mục | Unique; autoname source |
| `gmdn_code` | varchar(20) | NO | **Mã GMDN (5–6 chữ số)** | **Nguồn kế thừa** — Device Model sẽ copy khi tạo mới nếu để trống |
| `description` | text | NO | Mô tả danh mục | — |
| `default_pm_required` | tinyint(1) | NO | PM là bắt buộc theo mặc định? | Check; kế thừa xuống Device Model |
| `default_pm_interval_days` | int(11) | COND | Chu kỳ PM mặc định (ngày) | > 0 nếu default_pm_required=1 |
| `default_calibration_required` | tinyint(1) | NO | Calibration là bắt buộc theo mặc định? | Check; kế thừa xuống Device Model |
| `default_calibration_interval_days` | int(11) | COND | Chu kỳ calibration mặc định (ngày) | — |
| `default_depreciation_method` | varchar(50) | NO | Phương pháp khấu hao | Select: Straight Line / WDV / Double Declining |
| `total_depreciation_months` | int(11) | NO | Tổng số tháng khấu hao | — |
| `depreciation_frequency` | varchar(20) | NO | Tần suất tính khấu hao | Monthly / Quarterly / Yearly |
| `default_residual_value_pct` | decimal | NO | Tỉ lệ giá trị thu hồi (%) | — |
| `has_radiation` | tinyint(1) | NO | Thiết bị bức xạ? | Ảnh hưởng risk_classification ở Device Model |
| `is_active` | tinyint(1) | NO | Còn sử dụng | default 1 |

## II.4. IMM Device Model

**Autoname:** `IMM-MDL-.YYYY.-.####` · **track_changes:** 1

> Kế thừa `gmdn_code` + PM/Calibration defaults từ `AC Asset Category` khi tạo mới (`before_insert → _inherit_pm_calibration_defaults()`). Người dùng có thể override thủ công sau khi lưu.

| Field | DB Type | Required | Description | BR/Note |
|---|---|---|---|---|
| `model_name` | varchar(140) | YES | Tên model thiết bị | — |
| `manufacturer` | varchar(140) | YES | Nhà sản xuất | — |
| `asset_category` | varchar(140) | YES | Link → AC Asset Category | Nguồn kế thừa GMDN + PM defaults |
| `medical_device_class` | varchar(20) | YES | Class I/II/III | BR-00-01 mapping |
| `risk_classification` | varchar(20) | YES | Low/Medium/High/Critical | auto-set theo class + is_radiation_device |
| `gmdn_code` | varchar(20) | NO | **Mã GMDN 5–6 số** | **Kế thừa từ `asset_category.gmdn_code`** khi tạo nếu để trống; có thể override |
| `emdn_code` | varchar(20) | NO | Mã EMDN (European) | — |
| `hsn_code` | varchar(20) | NO | Mã HSN (hải quan) | — |
| `is_pm_required` | tinyint(1) | NO | Cần PM | inherit từ category.default_pm_required |
| `pm_interval_days` | int(11) | COND | Chu kỳ PM (ngày) | inherit từ category nếu trống |
| `is_calibration_required` | tinyint(1) | NO | Cần calibration | inherit từ category |
| `calibration_interval_days` | int(11) | COND | Chu kỳ calibration (ngày) | inherit từ category nếu trống |
| `spare_parts_list` | Table | NO | Child → IMM Device Spare Part | BOM |
| `is_active` | tinyint(1) | NO | Còn active | default 1 |

**Controller — `_inherit_pm_calibration_defaults()` (before_insert):**

```python
def _inherit_pm_calibration_defaults(self) -> None:
    """Kế thừa từ AC Asset Category: gmdn_code + PM/Calibration defaults.
    Chỉ fill nếu field đang trống — không ghi đè input thủ công.
    """
    if not self.asset_category:
        return
    cat = frappe.db.get_value(
        "AC Asset Category", self.asset_category,
        ["gmdn_code", "default_pm_required", "default_pm_interval_days",
         "default_calibration_required", "default_calibration_interval_days"],
        as_dict=True,
    )
    if not cat:
        return
    # GMDN inheritance
    if not self.gmdn_code and cat.get("gmdn_code"):
        self.gmdn_code = cat["gmdn_code"]
    # PM defaults
    if not self.is_pm_required and cat.get("default_pm_required"):
        self.is_pm_required = 1
        if not self.pm_interval_days and cat.get("default_pm_interval_days"):
            self.pm_interval_days = cat["default_pm_interval_days"]
    # Calibration defaults
    if not self.is_calibration_required and cat.get("default_calibration_required"):
        self.is_calibration_required = 1
        if not self.calibration_interval_days and cat.get("default_calibration_interval_days"):
            self.calibration_interval_days = cat["default_calibration_interval_days"]
```

**Business Rule BR-00-01:**

| medical_device_class | risk_classification |
|---|---|
| Class I | Low |
| Class II | Medium |
| Class III | High hoặc Critical |

## II.4. IMM Audit Trail

**Autoname:** `IMM-AUD-.YYYY.-.#######` · **append-only** (no Update/Delete perm)

| Field | DB Type | Required | Description | BR/Note |
|---|---|---|---|---|
| `asset` | varchar(140) | YES | Link → AC Asset | IDX |
| `event_type` | varchar(140) | YES | State Change / CAPA Opened / Incident / etc. | IDX |
| `actor` | varchar(200) | YES | session.user | IDX |
| `timestamp` | datetime | YES | now() | IDX; auto |
| `from_status` | varchar(50) | NO | Trạng thái trước | — |
| `to_status` | varchar(50) | NO | Trạng thái sau | — |
| `ref_doctype` | varchar(140) | NO | DocType nguồn gây ra sự kiện | — |
| `ref_name` | varchar(140) | NO | Name của record nguồn | — |
| `change_summary` | text | NO | Mô tả thay đổi | — |
| `hash_sha256` | varchar(64) | YES | SHA-256 của payload | BR-00-03; VR-00-27 |
| `prev_hash` | varchar(64) | NO | Hash của record trước | Tạo hash chain |

**Controller rule:** `validate()` throws nếu `not is_new()` — record không thể sửa (BR-00-03).

## II.5. IMM CAPA Record

**Autoname:** `CAPA-.YYYY.-.#####` · **is_submittable:** 1

| Field | DB Type | Required | Description | BR/Note |
|---|---|---|---|---|
| `asset` | varchar(140) | YES | Link → AC Asset | IDX |
| `source_type` | varchar(50) | YES | Incident / PM / Audit / Calibration | — |
| `source_ref` | varchar(140) | YES | Tham chiếu nguồn (IR name hoặc WO name) | — |
| `severity` | varchar(20) | YES | Minor / Major / Critical | — |
| `status` | varchar(50) | YES | Open/In Progress/Pending Verification/Overdue/Closed | IDX |
| `responsible` | varchar(200) | YES | Link → User | IDX |
| `opened_date` | date | YES | Ngày mở | auto = today() |
| `due_date` | date | YES | Hạn hoàn thành | >= opened_date |
| `description` | text | YES | Mô tả vấn đề | — |
| `root_cause` | text | COND | Phân tích nguyên nhân gốc rễ | reqd before_submit |
| `corrective_action` | text | COND | Hành động khắc phục | reqd before_submit |
| `preventive_action` | text | COND | Hành động phòng ngừa | reqd before_submit |
| `effectiveness_check` | text | NO | Kết quả kiểm tra hiệu quả | — |
| `closed_date` | date | NO | Ngày đóng | auto khi close_capa() |
| `linked_incident` | varchar(140) | NO | Link → Incident Report | bidirectional |

**CAPA State Machine:**

```
Draft → Open (auto-submit khi tạo)
Open → In Progress (cập nhật root_cause)
In Progress → Pending Verification (gửi QA Officer)
Pending Verification → Closed (close_capa() + docstatus=1)
Open/In Progress → Overdue (scheduler daily)
```

## II.6. Asset Lifecycle Event

**Autoname:** `ALE-.YYYY.-.#######` · **append-only** (in_create=1, no Update/Delete perm)

| Field | DB Type | Required | Description | BR/Note |
|---|---|---|---|---|
| `asset` | varchar(140) | YES | Link → AC Asset | IDX |
| `event_type` | varchar(140) | YES | commissioned/pm_completed/repair_opened/decommissioned/… | IDX |
| `timestamp` | datetime | YES | auto = now() | IDX |
| `actor` | varchar(200) | YES | session.user | — |
| `from_status` | varchar(50) | NO | lifecycle_status trước | — |
| `to_status` | varchar(50) | NO | lifecycle_status sau | — |
| `root_doctype` | varchar(140) | NO | Module gây ra event | — |
| `root_record` | varchar(140) | NO | WO name / IR name / … | — |
| `notes` | text | NO | Ghi chú bổ sung | — |

**Event type enum:**
`commissioned, pm_completed, repair_opened, repair_closed, calibration_completed, capa_opened, capa_closed, status_changed, incident_reported, incident_closed, decommissioned, relocated, reassigned, gmdn_status_changed`

## II.7. Incident Report

**Autoname:** `IR-.YYYY.-.####` · **is_submittable:** 1

| Field | DB Type | Required | Description | BR/Note |
|---|---|---|---|---|
| `asset` | varchar(140) | YES | Link → AC Asset | IDX |
| `severity` | varchar(20) | YES | Minor / Major / Critical | — |
| `status` | varchar(50) | YES | Draft/Open/Under Investigation/Closed | IDX |
| `incident_datetime` | datetime | YES | Thời điểm xảy ra | — |
| `reporter` | varchar(200) | YES | Link → User; auto = session.user | — |
| `description` | text | YES | Mô tả sự cố | — |
| `patient_affected` | tinyint(1) | NO | Có bệnh nhân bị ảnh hưởng | — |
| `patient_impact_description` | text | COND | reqd nếu patient_affected=1 | VR-00-24 |
| `reported_to_byt` | tinyint(1) | NO | Đã báo cáo BYT | reqd nếu severity=Critical |
| `byt_report_date` | date | COND | Ngày báo cáo BYT | reqd nếu reported_to_byt=1 |
| `linked_capa` | varchar(140) | NO | Link → IMM CAPA Record | bidirectional |
| `linked_repair_wo` | varchar(140) | NO | Link → Repair Work Order | — |
| `resolution_notes` | text | COND | reqd khi close incident | — |
| `closed_date` | date | NO | auto khi close | — |

---

# Phần III — Service Layer

## III.1. File: `assetcore/services/imm00.py`

| Function | Signature thực (từ code) | Output | Caller modules | Mô tả |
|---|---|---|---|---|
| `log_audit_event()` | `(**kwargs) -> str` | audit_trail_name: str | Tất cả IMM modules | Re-export từ `utils.lifecycle`; tạo IMM Audit Trail bất biến SHA-256 chain |
| `create_lifecycle_event()` | `(**kwargs) -> str` | event_name: str | IMM-04, 09, 11, 12, 13 | Re-export từ `utils.lifecycle`; tạo Asset Lifecycle Event append-only |
| `verify_audit_chain()` | `(asset: str) -> dict` | `{valid, count, broken_at?}` | QA, API | Re-export từ `utils.lifecycle`; duyệt SHA-256 chain |
| `transition_asset_status()` | `(asset_name, to_status, actor=None, reason="", root_doctype=None, root_record=None) -> None` | None | IMM-09, 12, 13 | Đổi lifecycle_status + gọi create_lifecycle_event + log_audit_event + _sync_downtime_log; suspend schedules nếu Decommissioned |
| `update_gmdn_status()` | `(asset_name, gmdn_status, reason) -> dict` | `{name, gmdn_status, previous}` | API | Cập nhật GMDN Status, validate BR-00-11/12, ghi Audit Trail |
| `toggle_gmdn_status_via_qr()` | `(asset_name) -> dict` | `{name, gmdn_status, previous}` | API (QR scan) | Toggle GMDN In Use↔Not Use, reason auto = "Quét QR @ timestamp" |
| `validate_asset_for_operations()` | `(asset_name) -> None` | None / raises | IMM-08, 09, 11 | Gate: frappe.throw nếu lifecycle_status ∈ {Out of Service, Decommissioned} |
| `get_sla_policy()` | `(priority, risk_class=None) -> dict` | policy_dict hoặc `{}` | IMM-08, 09, 11 | Tra SLA exact (priority × risk_class) rồi fallback is_default |
| `create_capa()` | `(asset, source_type, source_ref, severity, description, responsible, due_days=30) -> str` | capa_name: str | IMM-09, 11, 12 | Tạo IMM CAPA Record status=Open, ghi Audit Trail |
| `close_capa()` | `(capa_name, root_cause, corrective_action, preventive_action, effectiveness_check=None, actor=None) -> None` | None | IMM-12, QA | Đóng CAPA, set status=Closed, submit, ghi Audit Trail |
| `create_transfer_request()` | `(data: dict) -> dict` | `{name, status}` | API | Tạo phiếu luân chuyển Asset Transfer status=Pending Approval |
| `approve_transfer_request()` | `(name: str) -> dict` | `{name, status}` | API | Phê duyệt phiếu: cập nhật vị trí asset + notify requester |
| `reject_transfer_request()` | `(name, rejection_reason) -> dict` | `{name, status}` | API | Từ chối phiếu luân chuyển |
| `confirm_receipt()` | `(name, handover_notes="") -> dict` | `{name, status, received_by}` | API | Bên nhận xác nhận tiếp nhận (status → Received) |
| `cancel_transfer_request()` | `(name) -> dict` | `{name, status}` | API | Hủy phiếu (chỉ Pending/Rejected) |
| `transfer_asset()` | `(asset_name, to_location, to_department=None, to_custodian=None, transfer_doc=None, actor=None) -> None` | None | approve_transfer_request | Cập nhật location/department/custodian + ghi lifecycle event + audit |
| `check_capa_overdue()` | `() -> None` | None | Scheduler daily | Mark CAPA Overdue + email QA Officer + responsible |
| `check_vendor_contract_expiry()` | `() -> None` | None | Scheduler daily | Cảnh báo HĐ NCC 90/60/30 ngày |
| `check_registration_expiry()` | `() -> None` | None | Scheduler daily | Cảnh báo BYT expiry 90/60/30/7 ngày |
| `check_insurance_expiry()` | `() -> None` | None | Scheduler daily | Cảnh báo bảo hiểm 90/60/30/7 ngày |
| `check_service_contract_expiry()` | `() -> None` | None | Scheduler daily | Cảnh báo hợp đồng dịch vụ 90/60/30 ngày |
| `rollup_asset_kpi()` | `() -> None` | None | Scheduler monthly | Rollup MTTR avg + uptime_pct cho từng asset |

## III.2. Shared utilities

### `assetcore/utils/response.py`

```python
from assetcore.utils.response import _ok, _err, ErrorCode

def _ok(data: dict | list) -> dict:
    """Wrap response thành format chuẩn AssetCore."""
    return {"success": True, "data": data}

def _err(msg: str, code: int | str = 400, **kwargs) -> dict:
    """Wrap error thành format chuẩn AssetCore."""
    return {"success": False, "error": msg, "code": code, **kwargs}
```

### `assetcore/utils/lifecycle.py`

```python
from assetcore.utils.lifecycle import (
    log_audit_event,
    create_lifecycle_event,
    verify_audit_chain,
)

def create_lifecycle_event(
    asset: str,
    event_type: str,
    actor: str,
    from_status: str | None = None,
    to_status: str | None = None,
    root_doctype: str | None = None,
    root_record: str | None = None,
    notes: str | None = None,
) -> str:
    """Tạo Asset Lifecycle Event append-only. Trả về tên record mới."""
    ...

def verify_audit_chain(asset: str) -> dict:
    """Duyệt SHA-256 chain của IMM Audit Trail cho 1 asset."""
    ...
```

### `assetcore/utils/email.py`

```python
from assetcore.utils.email import get_role_emails, safe_sendmail

def get_role_emails(roles: list[str]) -> list[str]:
    """Lấy email của tất cả user có role trong danh sách."""
    ...

def safe_sendmail(
    recipients: list[str],
    subject: str,
    message: str,
) -> None:
    """Gửi email an toàn — bắt exception, ghi log nếu thất bại."""
    ...
```

### `assetcore/utils/pagination.py`

```python
from assetcore.utils.pagination import paginate

def paginate(
    total: int,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """Trả về pagination metadata: {total, page, page_size, total_pages, offset}."""
    ...
```

### `assetcore/services/shared/` — Centralized constants & errors

```python
# assetcore/services/shared/constants.py
from assetcore.services.shared.constants import Roles, AssetStatus, ErrorCode

class Roles:        # 19 roles — Wave 1 + Wave 2
class AssetStatus:  # lifecycle_status constants (DRAFT, COMMISSIONED, ACTIVE, …)
class ErrorCode:    # string codes: NOT_FOUND, FORBIDDEN, VALIDATION, CONFLICT, …

# assetcore/services/shared/errors.py
from assetcore.services.shared.errors import ServiceError, not_found, forbidden, validation

class ServiceError(Exception):
    def __init__(self, code: str, message: str, *, http_status: int = 400): ...

# assetcore/services/shared/permissions.py
from assetcore.services.shared.permissions import require_role, has_any_role, is_admin
```

## III.3. Service error pattern

```python
from assetcore.services.shared.errors import ServiceError
from assetcore.services.shared.constants import ErrorCode

# Ví dụ raise lỗi trong service
def validate_asset_for_operations(asset_name: str) -> None:
    """Gate function: block nếu thiết bị không vận hành được."""
    status = frappe.db.get_value("AC Asset", asset_name, "lifecycle_status")
    if status in ("Out of Service", "Decommissioned"):
        frappe.throw(
            frappe._("Khong the tao Work Order - thiet bi dang o trang thai '{0}' (BR-00-05).").format(status)
        )
```

> **Lưu ý:** `validate_asset_for_operations()` dùng `frappe.throw()` trực tiếp (không raise `ServiceError`) — API layer bắt `frappe.exceptions.ValidationError`.

ErrorCode string identifiers (từ `assetcore/services/shared/constants.py`):

| ErrorCode | Mô tả |
|---|---|
| `NOT_FOUND` | Record không tồn tại |
| `FORBIDDEN` | Không đủ quyền |
| `UNAUTHORIZED` | Chưa đăng nhập |
| `VALIDATION` | Vi phạm validation rule |
| `BUSINESS_RULE` | Gate / VR nghiệp vụ (HTTP 422) |
| `CONFLICT` | Vi phạm uniqueness / conflict state |
| `BAD_STATE` | Sai trạng thái (HTTP 409) |
| `DUPLICATE` | Trùng lặp |
| `INVALID_PARAMS` | Tham số không hợp lệ |
| `INTERNAL` | Lỗi server không xác định |

---

# Phần IV — Setup Guide (Installation & Migration)

## IV.1. Yêu cầu hệ thống

| Thành phần | Phiên bản tối thiểu | Ghi chú |
|---|---|---|
| OS | Ubuntu 22.04 / Debian 12 | LTS khuyến nghị |
| Python | 3.10+ | Frappe v15 yêu cầu |
| MariaDB | 10.6+ | hoặc MySQL 8.0+ |
| Redis | 6.0+ | Queue + cache + socketio |
| Node.js | 18.x | FE build (Vite) |
| Frappe Framework | v15+ | **Dependency DUY NHẤT — không cần ERPNext** |

## IV.2. Fresh install

```bash
# Tạo site mới (không install ERPNext)
bench new-site assetcore.local \
  --mariadb-root-password <root-pw> \
  --admin-password <admin-pw>

# Get và install app
bench get-app https://github.com/<org>/assetcore.git --branch master
bench --site assetcore.local install-app assetcore
bench --site assetcore.local migrate
```

## IV.3. Migration patch (từ v2 ERPNext-based)

**File:** `assetcore/patches/v3_0/001_migrate_from_v2.py`

Patch thực hiện:
1. Copy dữ liệu `IMM Asset Profile` → `AC Asset`
2. Copy `IMM Vendor Profile` → `AC Supplier`
3. Copy `IMM Location Ext` → `AC Location`
4. Drop 3 bảng sidecar cũ
5. Xóa 16 custom fields `custom_imm_*` trên tabAsset ERPNext

Đăng ký trong `assetcore/patches.txt`:
```
assetcore.patches.v3_0.001_migrate_from_v2
```

## IV.4. Load fixtures

```bash
# Fixtures được apply tự động qua migrate
bench --site <site> migrate

# Manual verify roles
bench --site <site> console <<'PY'
import frappe
roles = ["IMM System Admin", "IMM Department Head", "IMM Operations Manager",
         "IMM Workshop Lead", "IMM Technician", "IMM Document Officer",
         "IMM Storekeeper", "IMM QA Officer"]
for r in roles:
    print(r, "→", "OK" if frappe.db.exists("Role", r) else "MISSING")
PY
```

Fixtures shipped (verified vs `assetcore/fixtures/` 2026-05-14):

```
assetcore/fixtures/
├── role.json                          # 19 IMM roles (Wave 1 + Wave 2) — commit 5b4158e
├── has_role.json                      # IMM↔User pre-seed (commit 5b4158e)
├── role_profile.json                  # Role bundling per persona
├── module_profile.json                # Workspaces/sidebar grouping
├── workflow.json                      # Tất cả workflows AssetCore module
├── workflow_state.json                # State catalog (Open, In Progress, …)
├── workflow_action_master.json        # Action labels VN
├── workspace.json                     # Sidebar workspaces
├── imm_sla_policy.json                # SLA policy defaults (P1–P4 × risk_class)
├── imm15_custom_fields.json           # IMM-15 Spare Parts custom fields
└── imm16_custom_field_capa_record.json # IMM-16 CAPA custom field
```

> Fixture roles trước đây tên `imm_roles.json` đã được thay bằng `role.json` + `has_role.json` (commit `5b4158e` "install assetcore with fixtures/has_role").

## IV.5. SLA Policy defaults

9 policies theo ma trận `{P1,P2,P3} × {Low,Medium,High,Critical}` + 1 default cho mỗi priority:

| Priority | Risk Class | Response (min) | Resolution (h) | is_default |
|---|---|---|---|---|
| P1 Critical | Critical | 5 | 0.5 | 0 |
| P1 Critical | High | 10 | 1 | 0 |
| P1 Critical | (fallback) | 30 | 4 | 1 |
| P2 Urgent | Critical | 30 | 4 | 0 |
| P2 Urgent | High | 60 | 8 | 0 |
| P2 Urgent | (fallback) | 120 | 24 | 1 |
| P3 Normal | Critical | 60 | 8 | 0 |
| P3 Normal | (fallback) | 240 | 48 | 1 |
| P4 Low | (fallback) | 480 | 72 | 1 |

---

# Phần V — Hooks Registration

## V.1. `assetcore/hooks.py` — Scheduler

```python
scheduler_events = {
    "daily": [
        # IMM-00 foundation alerts
        "assetcore.services.imm00.check_capa_overdue",
        "assetcore.services.imm00.check_vendor_contract_expiry",
        "assetcore.services.imm00.check_registration_expiry",
        "assetcore.services.imm00.check_insurance_expiry",
        "assetcore.services.imm00.check_service_contract_expiry",
        # ... (các module IMM-05/08/11/12/15/16 + Wave 2 đăng ký thêm)
    ],
    "monthly": [
        "assetcore.services.imm00.rollup_asset_kpi",
    ],
}
```

> Foundation IMM-00 đóng góp **5 daily jobs** + **1 monthly job** (`rollup_asset_kpi`). Các IMM-05/08/11/12/15/16 đăng ký thêm scheduler riêng — xem `hooks.py::scheduler_events` để có danh sách đầy đủ.

## V.2. `assetcore/hooks.py` — Permission Query

```python
permission_query_conditions = {
    "AC Asset": "assetcore.permission.get_ac_asset_permission_query",
}
```

**`assetcore/permission.py`:**

```python
import frappe

def get_ac_asset_permission_query(user: str) -> str:
    """IMM Technician chỉ thấy AC Asset được gán cho mình."""
    roles = frappe.get_roles(user)
    if "IMM Technician" in roles and "IMM System Admin" not in roles:
        return f"(`tabAC Asset`.responsible_technician = '{user}')"
    return ""
```

## V.3. `assetcore/hooks.py` — Fixtures

Fixtures hiện đăng ký qua file JSON trong `assetcore/fixtures/` (bench tự sync khi `bench migrate`):

| Fixture | Doctype gốc | Mục đích |
|---|---|---|
| `role.json` | Role | 19 IMM roles |
| `has_role.json` | Has Role | Default role assignments |
| `role_profile.json` | Role Profile | Persona bundling |
| `module_profile.json` | Module Profile | Workspace grouping |
| `workflow.json` | Workflow | Tất cả AssetCore workflows |
| `workflow_state.json` | Workflow State | State catalog |
| `workflow_action_master.json` | Workflow Action Master | Action labels VN |
| `workspace.json` | Workspace | Sidebar layout |
| `imm_sla_policy.json` | IMM SLA Policy | SLA defaults |
| `imm15_custom_fields.json` | Custom Field | IMM-15 fields |
| `imm16_custom_field_capa_record.json` | Custom Field | IMM-16 CAPA field |

## V.4. Database indexes

| Table | Index | Mục đích |
|---|---|---|
| `tabAC Asset` | `lifecycle_status, docstatus` | Dashboard filter |
| `tabAC Asset` | `next_pm_date` | PM due query |
| `tabAC Asset` | `byt_reg_expiry` | Registration expiry scheduler |
| `tabAC Asset` | `responsible_technician` | Permission Query |
| `tabIMM Audit Trail` | `asset, timestamp DESC` | History per asset |
| `tabIMM Audit Trail` | `hash_sha256` | Verify chain lookup |
| `tabAsset Lifecycle Event` | `asset, timestamp DESC` | Timeline per asset |
| `tabIMM CAPA Record` | `status, due_date` | Overdue scheduler |
| `tabAC Supplier` | `contract_end` | Expiry scheduler |
| `tabAC Spare Part Stock` | `UNIQUE(warehouse, spare_part)` | Stock integrity |

---

## DoD — File 04 hoàn chỉnh

> Reviewed vs codebase 2026-05-08. Tất cả thông tin dưới đây đã được cross-check với code thực tế.

### I. DocType catalog
- [x] 27 DocTypes foundation IMM-00 đã liệt kê (verified vs `assetcore/assetcore/doctype/`)
- [x] Naming conventions AC / IMM / ALE / IR / CAPA
- [x] Trạng thái Live ✅

### II. DocType schemas
- [x] AC Asset (7 field groups + state machine)
- [x] AC Supplier (HTM fields + contract)
- [x] IMM Device Model (BR-00-01 mapping)
- [x] IMM Audit Trail (append-only + SHA-256)
- [x] IMM CAPA Record (state machine)
- [x] Asset Lifecycle Event (append-only + event type enum)
- [x] Incident Report (NĐ98 fields)

### III. Service layer
- [x] imm00.py: 23+ public functions (verified vs code: lifecycle re-exports, `transition_asset_status`, GMDN update/toggle, validate_asset_for_operations, get_sla_policy, CAPA open/close, transfer CRUD + workflow + `transfer_asset`, 5 daily scheduler + monthly KPI rollup)
- [x] services/shared/: constants.py, errors.py, permissions.py (verified)
- [x] utils/: response, lifecycle, email, pagination (verified import paths)
- [x] ErrorCode string constants (verified vs constants.py)

### IV. Setup guide
- [x] System requirements (Frappe only, no ERPNext)
- [x] Fresh install + migration patch
- [x] Fixture load + SLA defaults

### V. Hooks registration
- [x] Scheduler events (daily + monthly)
- [x] Permission query condition
- [x] Fixtures
- [x] Database indexes
