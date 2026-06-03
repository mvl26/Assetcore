# 04 — Backend Design — IMM-00 Foundation (Master / Cross-cutting)

| Mục         | Giá trị                                                                                               |
| ------------ | ------------------------------------------------------------------------------------------------------- |
| Module       | IMM-00 — Foundation / Master Cross-cutting                                                             |
| Phạm vi     | Foundation — cross-cutting                                                                             |
| Owner        | Tech Lead / BE Lead                                                                                     |
| Liên kết   | [03 Diagrams](./03_Diagrams.md) · [05 API Specification](./05_API_Specification.md)                          |
| Phiên bản  | 0.0.3                                                                                                   |
| Cập nhật   | 2026-05-29                                                                                              |
| Trạng thái | **Live ✅** — synced vs codebase 2026-05-27; RBAC 30 roles (patch v3_2.001), SLA P1-P4 (patch v3_1.010), AC Location schema gộp contact fields (patch v3_1.007). Notification Framework E1–E6 (vòng 1–8): E6 SLA breach/warning IMM-09 — xem §III.1b-6 |

---

# Phần I — DocType Catalog

## I.1. DocTypes chính của IMM-00 Foundation (tất cả đã Live)

DocType folder path: `assetcore/assetcore/doctype/` (78 folders tổng — bảng sau liệt kê các DocType nằm trong phạm vi IMM-00 foundation và cross-cutting).

| #  | DocType (snake_case folder)        | Tên hiển thị                | Submittable | Tree | Ghi chú                      |
| -- | ---------------------------------- | ------------------------------ | ----------- | ---- | ----------------------------- |
| 1  | `ac_asset`                       | AC Asset                       | ✅          | —   | Core asset registry           |
| 2  | `ac_asset_category`              | AC Asset Category              | —          | —   | Danh mục thiết bị          |
| 3  | `ac_asset_depreciation_schedule` | AC Asset Depreciation Schedule | —          | —   | Child table khấu hao         |
| 4  | `ac_asset_downtime_log`          | AC Asset Downtime Log          | —          | —   | Log dừng máy                |
| 5  | `ac_authorized_technician`       | AC Authorized Technician       | —          | —   | Child table của AC Supplier  |
| 6  | `ac_department`                  | AC Department                  | —          | ✅   | Khoa/phòng ban (tree)        |
| 7  | `ac_location`                    | AC Location                    | —          | ✅   | Vị trí (tree)               |
| 8  | `ac_spare_part`                  | AC Spare Part                  | —          | —   | Danh mục phụ tùng          |
| 9  | `ac_spare_part_stock`            | AC Spare Part Stock            | —          | —   | Tồn kho phụ tùng           |
| 10 | `ac_stock_movement`              | AC Stock Movement              | ✅          | —   | Phiếu nhập/xuất kho        |
| 11 | `ac_stock_movement_item`         | AC Stock Movement Item         | —          | —   | Child table stock movement    |
| 12 | `ac_supplier`                    | AC Supplier                    | ✅          | —   | Nhà cung cấp / vendor       |
| 13 | `ac_warehouse`                   | AC Warehouse                   | —          | —   | Kho vật tư                  |
| 14 | `asset_lifecycle_event`          | Asset Lifecycle Event          | —          | —   | Append-only lifecycle log     |
| 15 | `asset_transfer`                 | Asset Transfer                 | —          | —   | Phiếu luân chuyển          |
| 16 | `document_request`               | Document Request               | —          | —   | Yêu cầu hồ sơ tài liệu  |
| 17 | `firmware_change_request`        | Firmware Change Request        | —          | —   | Yêu cầu thay đổi firmware |
| 18 | `imm_audit_trail`                | IMM Audit Trail                | —          | —   | SHA-256 chain audit log       |
| 19 | `imm_capa_record`                | IMM CAPA Record                | ✅          | —   | CAPA nghiệp vụ              |
| 20 | `imm_device_model`               | IMM Device Model               | —          | —   | Model thiết bị y tế        |
| 21 | `imm_device_spare_part`          | IMM Device Spare Part          | —          | —   | Child table spare parts BOM   |
| 22 | `imm_sla_policy`                 | IMM SLA Policy                 | —          | —   | Chính sách SLA              |
| 23 | `incident_report`                | Incident Report                | ✅          | —   | Báo cáo sự cố             |
| 24 | `pm_checklist_template`          | PM Checklist Template          | —          | —   | Template checklist PM         |
| 25 | `pm_schedule`                    | PM Schedule                    | —          | —   | Lịch PM định kỳ           |
| 26 | `service_contract`               | Service Contract               | —          | —   | Hợp đồng dịch vụ         |
| 27 | `service_contract_asset`         | Service Contract Asset         | —          | —   | Child: assets trong HĐ       |

> Các DocType khác (imm_needs_request, imm_procurement_plan, asset_commissioning, v.v.) thuộc phạm vi các module IMM-01→IMM-17.
> Xem danh sách đầy đủ tại `assetcore/assetcore/doctype/` (78 folders).

---

# Phần II — DocType Schemas

## II.1. AC Asset

**File:** `assetcore/assetcore/doctype/ac_asset/ac_asset.json`
**Controller:** `assetcore/assetcore/doctype/ac_asset/ac_asset.py`
**Module:** AssetCore
**is_submittable:** 1 · **track_changes:** 1 · **allow_import:** 1

### II.1.1 Fields — Thông tin cơ bản

| Field              | DB Type         | Required | Description                                                   | BR/Note                                    |
| ------------------ | --------------- | -------- | ------------------------------------------------------------- | ------------------------------------------ |
| `name`           | varchar(140) PK | YES      | Autoname `AC-ASSET-.YYYY.-.#####` (vd: AC-ASSET-2026-00001) | Unique, immutable                          |
| `asset_name`     | varchar(140)    | YES      | Tên thiết bị                                               | in_list_view, reqd                         |
| `asset_code`     | varchar(140)    | NO       | Mã tài sản nội bộ                                        | UNIQUE nếu có; IDX; dùng QR/barcode     |
| `asset_category` | varchar(140)    | YES      | Link → AC Asset Category                                     | IDX                                        |
| `status`         | varchar(50)     | YES      | Trạng thái Frappe native                                    | Select: Submitted/Active/Out of Service/… |

### II.1.2 Fields — Vị trí và phụ trách

| Field                      | DB Type      | Required | Description           | BR/Note               |
| -------------------------- | ------------ | -------- | --------------------- | --------------------- |
| `location`               | varchar(140) | NO       | Link → AC Location   | IDX                   |
| `department`             | varchar(140) | NO       | Link → AC Department | IDX                   |
| `custodian`              | varchar(140) | NO       | Link → User          | Người giữ          |
| `responsible_technician` | varchar(140) | NO       | Link → User          | IDX; Permission Query |

### II.1.3 Fields — HTM (Health Technology Management)

| Field                    | DB Type      | Required | Description                                       | BR/Note                                                                                               |
| ------------------------ | ------------ | -------- | ------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| `device_model`         | varchar(140) | NO       | Link → IMM Device Model                          | IDX; fetch source                                                                                     |
| `medical_device_class` | varchar(20)  | NO       | Class I/II/III                                    | fetch_from device_model                                                                               |
| `risk_classification`  | varchar(20)  | NO       | Low/Medium/High/Critical                          | read_only; fetch_from                                                                                 |
| `manufacturer_sn`      | varchar(140) | NO       | Số serial NSX                                    | IDX; UNIQUE nếu có                                                                                  |
| `udi_code`             | varchar(140) | NO       | Mã UDI (GS1/HIBC)                                | IDX                                                                                                   |
| `gmdn_code`            | varchar(20)  | NO       | Mã GMDN (5–6 số)                               | fetch_from device_model — dùng làm trục lọc/quản lý thiết bị                                       |

> **Note (2026-05-19):** Field trạng thái sử dụng GMDN (cũ) đã được loại bỏ (patch `v3_1/008_drop_...`). Lọc và quản lý thiết bị theo `gmdn_code` (kế thừa từ Asset Category → Device Model → Asset). Tham chiếu: [docs/res/analysis/gmdn-asset-category-analysis.md](../res/analysis/gmdn-asset-category-analysis.md) §6.

### II.1.4 Fields — Đăng ký BYT

| Field              | DB Type      | Required | Description                   | BR/Note                   |
| ------------------ | ------------ | -------- | ----------------------------- | ------------------------- |
| `byt_reg_no`     | varchar(140) | NO       | Số đăng ký lưu hành BYT | IDX                       |
| `byt_reg_expiry` | date         | NO       | Hạn đăng ký               | IDX; scheduler cảnh báo |

### II.1.5 Fields — Lifecycle

| Field                  | DB Type      | Required | Description                                                                | BR/Note                     |
| ---------------------- | ------------ | -------- | -------------------------------------------------------------------------- | --------------------------- |
| `lifecycle_status`   | varchar(50)  | YES      | Commissioned/Active/Under Repair/Calibrating/Out of Service/Decommissioned | IDX; chỉ đổi qua service |
| `commissioning_date` | date         | NO       | Ngày nghiệm thu từ IMM-04                                               | —                          |
| `commissioning_ref`  | varchar(140) | NO       | Tham chiếu biên bản                                                     | Dynamic Link                |

### II.1.6 Fields — PM và Calibration

| Field                         | DB Type    | Required | Description                   | BR/Note                                                                                                                   |
| ----------------------------- | ---------- | -------- | ----------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| `is_pm_required`            | tinyint(1) | NO       | Cần PM định kỳ            | Check;`fetch_from device_model` (Frappe native form); **FE tự fill qua `getDeviceModel()` — xem BR-00-FE-02** |
| `pm_interval_days`          | int(11)    | COND     | Chu kỳ PM (ngày)            | reqd nếu is_pm_required=1                                                                                                |
| `last_pm_date`              | date       | NO       | Ngày PM gần nhất           | read_only; cập nhật bởi IMM-08                                                                                         |
| `next_pm_date`              | date       | NO       | Ngày PM tiếp theo           | IDX; auto = last + interval                                                                                               |
| `is_calibration_required`   | tinyint(1) | NO       | Cần hiệu chuẩn             | Check;`fetch_from device_model` (Frappe native form); **FE tự fill qua `getDeviceModel()` — xem BR-00-FE-02** |
| `calibration_interval_days` | int(11)    | COND     | Chu kỳ hiệu chuẩn (ngày)  | reqd nếu is_calibration_required=1                                                                                       |
| `last_calibration_date`     | date       | NO       | Ngày hiệu chuẩn gần nhất | read_only; cập nhật bởi IMM-11                                                                                         |
| `next_calibration_date`     | date       | NO       | Ngày hiệu chuẩn tiếp theo | IDX; auto = last + interval                                                                                               |

> **Ghi chú FE:** DocType JSON có `fetch_from: device_model.is_pm_required` v.v. nhưng đây là cơ chế của Frappe Desk — không áp dụng trong Vue FE custom. Vue FE thực hiện auto-fill phía client qua `watch(() => form.device_model)` → `getDeviceModel()` → điền form (BR-00-FE-02 trong `06_Frontend_Design.md`).

### II.1.7 State machine — lifecycle_status

State machine được định nghĩa tại `_VALID_ASSET_TRANSITIONS` trong `services/imm00.py`. Trạng thái đầu (khi insert mới, chưa qua lifecycle) = `Draft`; không validate transition nếu `prev_status` rỗng.

| Từ               | Sang (allowed)                                                               | Trigger                  | Service                       |
| ----------------- | ---------------------------------------------------------------------------- | ------------------------ | ----------------------------- |
| Draft             | Commissioned, Decommissioned                                                 | IMM-04 Complete / direct | `transition_asset_status()` |
| Commissioned      | Active, Out of Service, Decommissioned                                       | Confirm operational      | `transition_asset_status()` |
| Active            | Under Maintenance, Under Repair, Calibrating, Out of Service, Decommissioned | WO created / manual      | `transition_asset_status()` |
| Under Maintenance | Active, Under Repair, Out of Service, Decommissioned                         | PM completed / manual    | `transition_asset_status()` |
| Under Repair      | Active, Out of Service, Decommissioned                                       | Repair WO completed      | `transition_asset_status()` |
| Calibrating       | Active, Out of Service, Decommissioned                                       | Calibration WO completed | `transition_asset_status()` |
| Out of Service    | Active, Under Repair, Decommissioned                                         | Phê duyệt khôi phục  | `transition_asset_status()` |
| Decommissioned    | (terminal)                                                                   | —                       | —                            |

Hàm `_lifecycle_event_for(to_status)` map status → event type:

| to_status         | event_type              |
| ----------------- | ----------------------- |
| Active            | `activated`           |
| Commissioned      | `commissioned`        |
| Under Maintenance | `pm_started`          |
| Under Repair      | `repair_opened`       |
| Calibrating       | `calibration_started` |
| Out of Service    | `out_of_service`      |
| Decommissioned    | `decommissioned`      |
| (default)         | `restored`            |

Khi `to_status = Decommissioned`, hàm `_suspend_all_schedules(asset_name)` tự động set `is_pm_required=0`, `is_calibration_required=0`, `next_pm_date=None`, `next_calibration_date=None`.

Downtime log (AC Asset Downtime Log) tự động open/close qua `_sync_downtime_log()`: các status `Under Maintenance, Under Repair, Calibrating, Out of Service` là downtime states; chuyển vào → open log, chuyển ra → close log.

## II.2. AC Supplier

**Autoname:** `AC-SUP-.YYYY.-.####` · **is_submittable:** 1 · **track_changes:** 1

| Field                      | DB Type       | Required | Description                                               | BR/Note                                         |
| -------------------------- | ------------- | -------- | --------------------------------------------------------- | ----------------------------------------------- |
| `supplier_name`          | varchar(140)  | YES      | Tên NCC                                                  | in_list_view                                    |
| `supplier_code`          | varchar(140)  | NO       | Mã NCC nội bộ                                          | UNIQUE nếu có                                 |
| `vendor_type`            | varchar(50)   | YES      | Manufacturer/Distributor/Calibration Lab/Service Provider | IDX                                             |
| `iso_17025_cert`         | varchar(140)  | NO       | Số chứng chỉ ISO/IEC 17025                             | BR-00-06: warning nếu Calibration Lab + trống |
| `iso_17025_expiry`       | date          | NO       | Hết hạn ISO 17025                                       | —                                              |
| `iso_13485_cert`         | varchar(140)  | NO       | Số chứng chỉ ISO 13485                                 | —                                              |
| `contract_start`         | date          | NO       | Ngày bắt đầu HĐ                                      | —                                              |
| `contract_end`           | date          | NO       | Ngày kết thúc HĐ                                      | IDX; scheduler cảnh báo                       |
| `contract_value`         | decimal(21,9) | NO       | Giá trị HĐ (VND)                                       | Currency                                        |
| `is_active`              | tinyint(1)    | NO       | Còn hoạt động                                         | default 1                                       |
| `authorized_technicians` | Table         | NO       | Child → AC Authorized Technician                         | —                                              |

## II.3. AC Asset Category

**Autoname:** `by category_name` · **track_changes:** 1

> **Nguồn dữ liệu GMDN.** Mỗi danh mục thiết bị gắn với một mã GMDN — đây là cấp đầu tiên trong chuỗi kế thừa: `Category → Device Model → Asset`.

| Field                                 | DB Type      | Required | Description                                  | BR/Note                                                                                                                                                                              |
| ------------------------------------- | ------------ | -------- | -------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `category_name`                     | varchar(140) | YES      | Tên danh mục                               | Unique; autoname source                                                                                                                                                              |
| `gmdn_code`                         | varchar(20)  | NO       | **Mã GMDN (5–6 chữ số)**           | **Nguồn kế thừa** — Device Model sẽ copy khi tạo mới nếu để trống; **UNIQUE constraint** (patch 006, 2026-05-16) — NULL được phép, non-NULL phải unique |
| `gmdn_term`                         | varchar(140) | NO       | Tên thuật ngữ GMDN                        | Mô tả text tương ứng với `gmdn_code`                                                                                                                                         |
| `description`                       | text         | NO       | Mô tả danh mục                            | —                                                                                                                                                                                   |
| `default_pm_required`               | tinyint(1)   | NO       | PM là bắt buộc theo mặc định?          | Check; kế thừa xuống Device Model                                                                                                                                                 |
| `default_pm_interval_days`          | int(11)      | COND     | Chu kỳ PM mặc định (ngày)               | > 0 nếu default_pm_required=1                                                                                                                                                       |
| `default_calibration_required`      | tinyint(1)   | NO       | Calibration là bắt buộc theo mặc định? | Check; kế thừa xuống Device Model                                                                                                                                                 |
| `default_calibration_interval_days` | int(11)      | COND     | Chu kỳ calibration mặc định (ngày)      | —                                                                                                                                                                                   |
| `default_depreciation_method`       | varchar(50)  | NO       | Phương pháp khấu hao                     | Select: Straight Line / WDV / Double Declining                                                                                                                                       |
| `total_depreciation_months`         | int(11)      | NO       | Tổng số tháng khấu hao                   | —                                                                                                                                                                                   |
| `depreciation_frequency`            | varchar(20)  | NO       | Tần suất tính khấu hao                   | Monthly / Quarterly / Yearly                                                                                                                                                         |
| `default_residual_value_pct`        | decimal      | NO       | Tỉ lệ giá trị thu hồi (%)               | —                                                                                                                                                                                   |
| `has_radiation`                     | tinyint(1)   | NO       | Thiết bị bức xạ?                         | Ảnh hưởng risk_classification ở Device Model                                                                                                                                     |
| `is_active`                         | tinyint(1)   | NO       | Còn sử dụng                               | default 1                                                                                                                                                                            |

## II.4. IMM Device Model

**Autoname:** `IMM-MDL-.YYYY.-.####` · **track_changes:** 1

> Kế thừa `gmdn_code` + PM/Calibration defaults từ `AC Asset Category` khi tạo mới (`before_insert → _inherit_pm_calibration_defaults()`). Người dùng có thể override `gmdn_code` thủ công — khi đó cờ `gmdn_inherited` tự chuyển 0 và Model được bảo vệ khỏi cascade (P3 Hybrid, xem dưới).

| Field                         | DB Type      | Required | Description                    | BR/Note                                                                                           |
| ----------------------------- | ------------ | -------- | ------------------------------ | ------------------------------------------------------------------------------------------------- |
| `model_name`                | varchar(140) | YES      | Tên model thiết bị          | —                                                                                                |
| `manufacturer`              | varchar(140) | YES      | Nhà sản xuất                | —                                                                                                |
| `asset_category`            | varchar(140) | YES      | Link → AC Asset Category      | Nguồn kế thừa GMDN + PM defaults                                                               |
| `medical_device_class`      | varchar(20)  | YES      | Class I/II/III                 | BR-00-01 mapping                                                                                  |
| `risk_classification`       | varchar(20)  | YES      | Low/Medium/High/Critical       | auto-set theo class + is_radiation_device                                                         |
| `gmdn_code`                 | varchar(20)  | NO       | **Mã GMDN 5–6 số**    | **Kế thừa từ `asset_category.gmdn_code`** khi tạo nếu để trống; có thể override |
| `gmdn_inherited`            | tinyint(1)   | NO       | Cờ kế thừa GMDN (P3)         | read_only, default 1; hệ thống tự đặt trong `validate()`. 1 = kế thừa (cascade khi Category đổi); 0 = override cố ý (KHÔNG cascade) |
| `emdn_code`                 | varchar(20)  | NO       | Mã EMDN (European)            | —                                                                                                |
| `hsn_code`                  | varchar(20)  | NO       | Mã HSN (hải quan)            | —                                                                                                |
| `is_pm_required`            | tinyint(1)   | NO       | Cần PM                        | inherit từ category.default_pm_required                                                          |
| `pm_interval_days`          | int(11)      | COND     | Chu kỳ PM (ngày)             | inherit từ category nếu trống                                                                  |
| `is_calibration_required`   | tinyint(1)   | NO       | Cần calibration               | inherit từ category                                                                              |
| `calibration_interval_days` | int(11)      | COND     | Chu kỳ calibration (ngày)    | inherit từ category nếu trống                                                                  |
| `spare_parts_list`          | Table        | NO       | Child → IMM Device Spare Part | BOM                                                                                               |
| `is_active`                 | tinyint(1)   | NO       | Còn active                    | default 1                                                                                         |

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

**P3 Hybrid — GMDN cascade Category → Model → Asset (2026-05-19):**

`AC Asset Category.gmdn_code` là single source of truth. Cơ chế chống drift:

| Thành phần | File | Vai trò |
| --- | --- | --- |
| `gmdn_inherited` (Check, default 1, read_only) | `imm_device_model.json` | Phân biệt Model kế thừa vs override |
| `IMMDeviceModel._set_gmdn_inherited_flag()` (`validate`) | `imm_device_model.py` | Đặt cờ: rỗng/`==Category` → 1; khác → 0 |
| `ACAssetCategory.on_update()` + `has_value_changed("gmdn_code")` | `ac_asset_category.py` | Trigger cascade CHỈ khi gmdn_code thực sự đổi (idempotent, không đệ quy) |
| `cascade_category_gmdn(category, old, new)` | `services/imm00.py` | Cascade tới Model `gmdn_inherited=1`; bỏ qua Model override (log danh sách) |
| `resync_assets_gmdn_from_model(model, code)` | `services/imm00.py` | Re-sync `AC Asset.gmdn_code` + `log_audit_event(event_type="System")` mỗi Asset đổi |
| Patch `v3_1/009_set_gmdn_inherited_flag` (post_model_sync) | `patches/v3_1/` | Backfill cờ cho Model cũ; CHỈ set cờ, KHÔNG đụng gmdn_code |

Quy tắc: Model `gmdn_inherited=0` (override cố ý) **không bao giờ bị cascade đè**. Audit trail: mỗi Asset thực sự đổi giá trị → 1 dòng `IMM Audit Trail` (`change_summary` mô tả from→to, ref = Device Model). Idempotent: chạy lại với cùng giá trị không sinh audit thừa. Ref: [docs/res/plans/2026-05-19-gmdn-code-sync-strategy.md](../res/plans/2026-05-19-gmdn-code-sync-strategy.md) §5/§6, [gmdn-asset-category-analysis.md §2.2](../res/analysis/gmdn-asset-category-analysis.md).

**Business Rule BR-00-01:**

| medical_device_class | risk_classification |
| -------------------- | ------------------- |
| Class I              | Low                 |
| Class II             | Medium              |
| Class III            | High hoặc Critical |

## II.4. IMM Audit Trail

**Autoname:** `IMM-AUD-.YYYY.-.#######` · **append-only** (no Update/Delete perm)

| Field              | DB Type      | Required | Description                                  | BR/Note            |
| ------------------ | ------------ | -------- | -------------------------------------------- | ------------------ |
| `asset`          | varchar(140) | YES      | Link → AC Asset                             | IDX                |
| `event_type`     | varchar(140) | YES      | State Change / CAPA Opened / Incident / etc. | IDX                |
| `actor`          | varchar(200) | YES      | session.user                                 | IDX                |
| `timestamp`      | datetime     | YES      | now()                                        | IDX; auto          |
| `from_status`    | varchar(50)  | NO       | Trạng thái trước                         | —                 |
| `to_status`      | varchar(50)  | NO       | Trạng thái sau                             | —                 |
| `ref_doctype`    | varchar(140) | NO       | DocType nguồn gây ra sự kiện             | —                 |
| `ref_name`       | varchar(140) | NO       | Name của record nguồn                      | —                 |
| `change_summary` | text         | NO       | Mô tả thay đổi                           | —                 |
| `hash_sha256`    | varchar(64)  | YES      | SHA-256 của payload                         | BR-00-03; VR-00-27 |
| `prev_hash`      | varchar(64)  | NO       | Hash của record trước                     | Tạo hash chain    |

**Controller rule:** `validate()` throws nếu `not is_new()` — record không thể sửa (BR-00-03).

## II.5. IMM CAPA Record

**Autoname:** `CAPA-.YYYY.-.#####` · **is_submittable:** 1

| Field                   | DB Type      | Required | Description                                          | BR/Note               |
| ----------------------- | ------------ | -------- | ---------------------------------------------------- | --------------------- |
| `asset`               | varchar(140) | YES      | Link → AC Asset                                     | IDX                   |
| `source_type`         | varchar(50)  | YES      | Incident / PM / Audit / Calibration                  | —                    |
| `source_ref`          | varchar(140) | YES      | Tham chiếu nguồn (IR name hoặc WO name)           | —                    |
| `severity`            | varchar(20)  | YES      | Minor / Major / Critical                             | —                    |
| `status`              | varchar(50)  | YES      | Open/In Progress/Pending Verification/Overdue/Closed | IDX                   |
| `responsible`         | varchar(200) | YES      | Link → User                                         | IDX                   |
| `opened_date`         | date         | YES      | Ngày mở                                            | auto = today()        |
| `due_date`            | date         | YES      | Hạn hoàn thành                                    | >= opened_date        |
| `description`         | text         | YES      | Mô tả vấn đề                                    | —                    |
| `root_cause`          | text         | COND     | Phân tích nguyên nhân gốc rễ                   | reqd before_submit    |
| `corrective_action`   | text         | COND     | Hành động khắc phục                             | reqd before_submit    |
| `preventive_action`   | text         | COND     | Hành động phòng ngừa                            | reqd before_submit    |
| `effectiveness_check` | text         | NO       | Kết quả kiểm tra hiệu quả                       | —                    |
| `closed_date`         | date         | NO       | Ngày đóng                                         | auto khi close_capa() |
| `linked_incident`     | varchar(140) | NO       | Link → Incident Report                              | bidirectional         |

**CAPA State Machine:**

```
Draft → Open (auto-submit khi tạo)
Open → In Progress (cập nhật root_cause)
In Progress → Pending Verification (gửi QA Officer)
Pending Verification → Closed (close_capa() + docstatus=1)
Open/In Progress/Pending Verification → Overdue (scheduler daily; idempotent; due_date NULL không flip)
```

## II.6. Asset Lifecycle Event

**Autoname:** `ALE-.YYYY.-.#######` · **append-only** (in_create=1, no Update/Delete perm)

| Field            | DB Type      | Required | Description                                               | BR/Note |
| ---------------- | ------------ | -------- | --------------------------------------------------------- | ------- |
| `asset`        | varchar(140) | YES      | Link → AC Asset                                          | IDX     |
| `event_type`   | varchar(140) | YES      | commissioned/pm_completed/repair_opened/decommissioned/… | IDX     |
| `timestamp`    | datetime     | YES      | auto = now()                                              | IDX     |
| `actor`        | varchar(200) | YES      | session.user                                              | —      |
| `from_status`  | varchar(50)  | NO       | lifecycle_status trước                                  | —      |
| `to_status`    | varchar(50)  | NO       | lifecycle_status sau                                      | —      |
| `root_doctype` | varchar(140) | NO       | Module gây ra event                                      | —      |
| `root_record`  | varchar(140) | NO       | WO name / IR name / …                                    | —      |
| `notes`        | text         | NO       | Ghi chú bổ sung                                         | —      |

**Event type enum:**
`commissioned, pm_completed, repair_opened, repair_closed, calibration_completed, capa_opened, capa_closed, status_changed, incident_reported, incident_closed, decommissioned, relocated, reassigned`

## II.7. Incident Report

**Autoname:** `IR-.YYYY.-.####` · **is_submittable:** 1

| Field                          | DB Type      | Required | Description                           | BR/Note                     |
| ------------------------------ | ------------ | -------- | ------------------------------------- | --------------------------- |
| `asset`                      | varchar(140) | YES      | Link → AC Asset                      | IDX                         |
| `severity`                   | varchar(20)  | YES      | Minor / Major / Critical              | —                          |
| `status`                     | varchar(50)  | YES      | Draft/Open/Under Investigation/Closed | IDX                         |
| `incident_datetime`          | datetime     | YES      | Thời điểm xảy ra                  | —                          |
| `reporter`                   | varchar(200) | YES      | Link → User; auto = session.user     | —                          |
| `description`                | text         | YES      | Mô tả sự cố                       | —                          |
| `patient_affected`           | tinyint(1)   | NO       | Có bệnh nhân bị ảnh hưởng      | —                          |
| `patient_impact_description` | text         | COND     | reqd nếu patient_affected=1          | VR-00-24                    |
| `reported_to_byt`            | tinyint(1)   | NO       | Đã báo cáo BYT                    | reqd nếu severity=Critical |
| `byt_report_date`            | date         | COND     | Ngày báo cáo BYT                   | reqd nếu reported_to_byt=1 |
| `linked_capa`                | varchar(140) | NO       | Link → IMM CAPA Record               | bidirectional               |
| `linked_repair_wo`           | varchar(140) | NO       | Link → Repair Work Order             | —                          |
| `resolution_notes`           | text         | COND     | reqd khi close incident               | —                          |
| `closed_date`                | date         | NO       | auto khi close                        | —                          |

## II.8. Service Contract

**Autoname:** naming_series · **is_submittable:** 0 (không submit — quản lý qua workflow_state trực tiếp) · **track_changes:** 1

| Field                    | DB Type      | Required | Description                                              | BR/Note                                                                    |
| ------------------------ | ------------ | -------- | -------------------------------------------------------- | -------------------------------------------------------------------------- |
| `contract_code`        | varchar(140) | YES      | Mã hợp đồng                                          | Unique key hiển thị                                                      |
| `contract_title`       | varchar(140) | YES      | Tiêu đề hợp đồng                                   | —                                                                         |
| `supplier`             | varchar(140) | YES      | Link → AC Supplier                                      | NCC cung cấp dịch vụ                                                    |
| `contract_type`        | varchar(50)  | YES      | Loại: Bảo hành/Bảo trì/Hiệu chuẩn/Dịch vụ khác | —                                                                         |
| `contract_start`       | date         | YES      | Ngày bắt đầu                                         | —                                                                         |
| `contract_end`         | date         | YES      | Ngày kết thúc                                         | IDX; scheduler `check_service_contract_expiry` cảnh báo 90/60/30 ngày |
| `sign_date`            | date         | NO       | Ngày ký                                                | —                                                                         |
| `contract_value`       | decimal      | NO       | Giá trị HĐ (VND)                                      | Currency                                                                   |
| `amount_in_words`      | Small Text   | NO       | Số tiền bằng chữ (VN)                                | Auto-gen bởi `num_to_words_vi()` trong Wave 2                           |
| `auto_renew`           | tinyint(1)   | NO       | Tự gia hạn?                                            | Check                                                                      |
| `sla_response_hours`   | int          | NO       | Cam kết phản hồi SLA (giờ)                           | Bổ sung Wave 2                                                            |
| `coverage_description` | text         | NO       | Phạm vi dịch vụ                                       | —                                                                         |
| `covered_assets`       | Table        | NO       | Child → Service Contract Asset                          | Danh sách thiết bị được bao phủ                                     |
| `notes`                | Text Editor  | NO       | Ghi chú                                                 | —                                                                         |

> `amount_in_words` và `sla_response_hours` được bổ sung trong Wave 2 (commit `41fabd8`, 2026-05-16).
> Controller: `service_contract.py` — tự điền `amount_in_words` qua `num_to_words_vi(contract_value)` trước khi lưu.

## II.9. AC Location

**File:** `assetcore/assetcore/doctype/ac_location/ac_location.json`
**Autoname:** `AC-LOC-.YYYY.-.####` · **is_tree:** 1 (NestedSet, `parent_location`) · **track_changes:** 1

| Field | DB Type | Required | Description | BR/Note |
|---|---|---|---|---|
| `location_name` | varchar(140) | YES | Tên vị trí | in_list_view |
| `location_code` | varchar(140) | NO | Mã vị trí | UNIQUE; set_only_once; trống → tự sinh series |
| `parent_location` | varchar(140) | NO | Link → AC Location | NestedSet parent |
| `is_group` | tinyint(1) | NO | Là node nhóm (tree) | default 0 |
| `clinical_area_type` | varchar(50) | NO | ICU/OR/Lab/Imaging/General Ward/Storage/Office | search_index |
| `infection_control_level` | varchar(50) | NO | Standard/Enhanced/Isolation | — |
| `power_backup_available` | tinyint(1) | NO | Có UPS/máy phát | — |
| `dept_head` | varchar(140) | NO | Link → User, label **"Người phụ trách"** | Người chịu trách nhiệm vị trí |
| `contact_phone` | varchar(140) | NO | Data, label **"Số liên hệ"** | `fetch_from: dept_head.phone` — tự điền từ SĐT người phụ trách, có thể override |
| `notes` | Small Text | NO | Ghi chú | — |

> **Đổi schema (2026-05-19, patch `v3_1.007_ac_location_simplify_contacts`):** Bỏ `emergency_contact` (Data) và `technical_contact` (Link User). Gộp về 1 người phụ trách (`dept_head`) + 1 số liên hệ tự fetch (`contact_phone`). Migrate dữ liệu: `emergency_contact → contact_phone`, `technical_contact → dept_head` (nếu trống) trước khi drop cột.
>
> **Ghi chú FE:** `fetch_from: dept_head.phone` là cơ chế Frappe Desk. Vue FE (`ReferenceDataView.vue`) tự fetch phía client qua `frappe.client.get_value` (lấy `phone`, fallback `mobile_no`) khi đổi người phụ trách — không ghi đè khi đang load dữ liệu edit.

---

## II.10. User Account & Approval (Frappe User extension)

IMM-00 KHÔNG tạo DocType riêng cho người dùng — mở rộng Frappe **User** bằng Custom Fields (`assetcore/setup/install.py::_USER_CUSTOM_FIELDS`). Quản lý qua API `assetcore/api/user.py` + view FE `/user-profiles`.

| Field | DB Type | Description | BR/Note |
|---|---|---|---|
| `imm_approval_status` | Select | `''` / Pending / Approved / Rejected | **default `''`** (KHÔNG phải Pending — xem invariant) |
| `imm_approved_by` | Link → User | Người duyệt | read_only, stamp khi approve |
| `imm_approved_at` | Datetime | Thời điểm duyệt | read_only |
| `imm_rejection_reason` | Small Text | Lý do từ chối | set khi reject |
| `ac_department` | Link → AC Department | Khoa/phòng | — |

**Invariant trạng thái duyệt (BR-00-USR-01):**
`Pending ⟺ enabled=0` — chỉ user qua luồng **self-signup** (`auth_service.register_user` → tạo User `enabled=0` + `Pending`) mới mang trạng thái này; user `enabled=1` LUÔN đã có quyền truy cập ⇒ phải là `Approved` (hoặc `''` nếu nằm ngoài luồng IMM, vd Administrator).

**Luồng:**
1. **Self-signup** (`/register`, guest) → `register_user` → User `enabled=0`, `imm_approval_status=Pending` → notify admin.
2. **Admin duyệt** (`/user-profiles/:user`, view `UserProfileFormView.vue`, nút Duyệt/Từ chối chỉ hiện khi `Pending`) → `approve_registration` → approve: `enabled=1` + `Approved` + stamp `approved_by/at`; reject: `enabled=0` + `Rejected` + reason.
3. **Admin tạo trực tiếp** (`create_system_user`) → bỏ qua luồng duyệt → `enabled=1` + `Approved` ngay.

> **Sửa thiết kế (2026-06-01, patch `v3_2.007_reconcile_user_approval_status`):** Custom Field cũ đặt `default='Pending'`. Hậu quả: mọi User tạo ngoài 3 luồng trên (test fixture, ERPNext desk, bench, import) inherit `Pending` dù `enabled=1` → badge "Chờ duyệt" giả trên `/user-profiles`, không có gate duyệt thật phía sau (root-cause user phản ánh "không thấy logic"). Fix: (a) `default` → `''`; (b) `_reconcile_approval_status_field()` ép default lệch về `''` trên Custom Field đã tồn tại (idempotent, chạy trong `after_migrate`); (c) patch backfill `enabled=1 AND Pending → Approved` (stamp `approved_by=Administrator`), Administrator → `''`. Self-signup `enabled=0 + Pending` giữ nguyên.

---

## II.x. Bảo mật endpoint tra trạng thái đăng nhập (BR-00-USR-02 — chống user enumeration)

> **Sửa thiết kế bảo mật (2026-06-01, security finding MEDIUM — user enumeration / information disclosure).**

**Vấn đề gốc (thiết kế cũ G5):** `auth.check_account_status(email)` là endpoint `allow_guest` trả nhãn **phân biệt** cho BẤT KỲ email nào mà **không cần chứng minh biết mật khẩu**:
- `not_found` (email chưa đăng ký) **vs** `active`/`pending`/`rejected`/`disabled` (email đã đăng ký) → kẻ tấn công liệt kê được email nào tồn tại trong hệ thống.
- `pending`/`rejected`/`disabled` → lộ trạng thái tài khoản của email bất kỳ.
- Rate-limit chỉ theo IP (10/60s), không theo email.

**Bằng chứng luồng login thật (frappe/auth.py `LoginManager.authenticate`, dòng 270-281):**
- Frappe xác thực **mật khẩu TRƯỚC** (`find_by_credentials`). Sai mật khẩu → `fail("Invalid login credentials")`.
- **Chỉ khi mật khẩu đúng** mà `enabled=0` (bao trùm MỌI Pending/Rejected/Disabled vì các trạng thái này luôn `enabled=0`) → `fail("User disabled or missing")` — nhãn KHÁC, nhưng **chỉ phát ra sau khi mật khẩu đúng**.
- Kết luận: **đã có sẵn tín hiệu hậu-xác-thực**. Không cần (và không được) một endpoint guest để phân biệt trạng thái nhạy cảm trước khi user chứng minh biết mật khẩu.

**Nguyên tắc thiết kế (MANDATORY):**
- Endpoint guest **KHÔNG** được phân biệt "email tồn tại hay không" và **KHÔNG** lộ trạng thái nhạy cảm (pending/rejected/disabled) trước khi user chứng minh biết mật khẩu.
- Trạng thái nhạy cảm chỉ được surface **SAU KHI mật khẩu đúng**.

**Thiết kế mới (2 endpoint tách bạch):**

1. **`check_account_status(email)`** — `allow_guest`, **non-enumerable**:
   - Trả **một nhãn đồng nhất `unknown`** cho cả email không tồn tại VÀ email active/pending/rejected/disabled. Không bao giờ tiết lộ tồn tại hay trạng thái.
   - Rate-limit kép: per-IP (10/60s) **và** per-email (5/60s) để chống dò hàng loạt.
   - Giữ lại chỉ để FE có một probe "không cần phân biệt gì" — vì nó không còn lộ gì, không còn là vector enumeration.

2. **`account_state(usr, pwd)`** — endpoint MỚI, `allow_guest` nhưng **password-gated**:
   - Bước 1: xác thực mật khẩu qua `frappe.utils.password.check_password(usr, pwd)`. **Sai mật khẩu / email không tồn tại** → trả nhãn ĐỒNG NHẤT `invalid_credentials` (timing đồng nhất, không phân biệt email tồn tại hay không).
   - Bước 2 (chỉ khi mật khẩu ĐÚNG): trả trạng thái chính xác `pending`/`rejected`/`disabled`/`active` để FE render thông báo đăng nhập đúng.
   - Rate-limit kép per-IP (10/60s) + per-email (5/60s). Không trả role/profile/dữ liệu nghiệp vụ — chỉ 1 nhãn trạng thái.
   - Lý do dùng `account_state` thay vì đọc message `"User disabled or missing"` từ `/api/method/login`: tránh phụ thuộc chuỗi message nội bộ của Frappe (dễ vỡ khi nâng cấp core) và Frappe login với `enabled=0` không tạo session — `account_state` là contract ổn định, không sửa core.

**Luồng FE login mới (`LoginView.vue`):**
1. Gọi `/api/method/login(usr, pwd)`.
2. Thành công → vào app.
3. Thất bại → gọi `account_state(usr, pwd)` (đưa CHÍNH mật khẩu user vừa nhập):
   - `pending`/`rejected`/`disabled` → hiển thị thông báo trạng thái tương ứng (chỉ tới được đây khi mật khẩu đúng ⇒ thông báo chính xác, an toàn).
   - `invalid_credentials` (sai mật khẩu HOẶC email không tồn tại) → thông báo trung lập "email/mật khẩu không đúng" — KHÔNG phân biệt được email tồn tại hay không.
   - `active` → mật khẩu đúng + tài khoản bình thường nhưng login vẫn fail (vd 2FA / IP / giờ login) → thông báo chung.

**Tradeoff UX:** không còn phân biệt "email chưa đăng ký" vs "sai mật khẩu" (cả hai → cùng thông báo trung lập) — đây là chuẩn an toàn (GitHub/Google đều làm vậy). Thông báo pending/rejected/disabled **vẫn hiện đúng** nhưng chỉ khi user nhập đúng mật khẩu, đó là hành vi mong muốn.

---

# Phần III — Service Layer

## III.1. File: `assetcore/services/imm00.py`

| Function                            | Signature thực (từ code)                                                                                      | Output                            | Caller modules           | Mô tả                                                                                                                            |
| ----------------------------------- | --------------------------------------------------------------------------------------------------------------- | --------------------------------- | ------------------------ | ---------------------------------------------------------------------------------------------------------------------------------- |
| `log_audit_event()`               | `(**kwargs) -> str`                                                                                           | audit_trail_name: str             | Tất cả IMM modules     | Re-export từ `utils.lifecycle`; tạo IMM Audit Trail bất biến SHA-256 chain                                                   |
| `create_lifecycle_event()`        | `(**kwargs) -> str`                                                                                           | event_name: str                   | IMM-04, 09, 11, 12, 13   | Re-export từ `utils.lifecycle`; tạo Asset Lifecycle Event append-only                                                          |
| `verify_audit_chain()`            | `(asset: str) -> dict`                                                                                        | `{valid, count, broken_at?}`    | QA, API                  | Re-export từ `utils.lifecycle`; duyệt SHA-256 chain                                                                            |
| `transition_asset_status()`       | `(asset_name, to_status, actor=None, reason="", root_doctype=None, root_record=None) -> None`                 | None                              | IMM-09, 12, 13           | Đổi lifecycle_status + gọi create_lifecycle_event + log_audit_event + _sync_downtime_log; suspend schedules nếu Decommissioned |
| `validate_asset_for_operations()` | `(asset_name) -> None`                                                                                        | None / raises                     | IMM-08, 09, 11           | Gate: frappe.throw nếu lifecycle_status ∈ {Out of Service, Decommissioned}                                                       |
| `get_sla_policy()`                | `(priority, risk_class=None) -> dict`                                                                         | policy_dict hoặc `{}`          | IMM-08, 09, 11           | Tra SLA exact (priority × risk_class) rồi fallback is_default                                                                    |
| `create_capa()`                   | `(asset, source_type, source_ref, severity, description, responsible, due_days=30) -> str`                    | capa_name: str                    | IMM-09, 11, 12           | Tạo IMM CAPA Record status=Open, ghi Audit Trail                                                                                  |
| `close_capa()`                    | `(capa_name, root_cause, corrective_action, preventive_action, effectiveness_check=None, actor=None) -> None` | None                              | IMM-12, QA               | Đóng CAPA, set status=Closed, submit, ghi Audit Trail                                                                            |
| `create_transfer_request()`       | `(data: dict) -> dict`                                                                                        | `{name, status}`                | API                      | Tạo phiếu luân chuyển Asset Transfer status=Pending Approval                                                                   |
| `approve_transfer_request()`      | `(name: str) -> dict`                                                                                         | `{name, status}`                | API                      | Phê duyệt phiếu: cập nhật vị trí asset + notify requester                                                                   |
| `reject_transfer_request()`       | `(name, rejection_reason) -> dict`                                                                            | `{name, status}`                | API                      | Từ chối phiếu luân chuyển                                                                                                     |
| `confirm_receipt()`               | `(name, handover_notes="") -> dict`                                                                           | `{name, status, received_by}`   | API                      | Bên nhận xác nhận tiếp nhận (status → Received)                                                                             |
| `cancel_transfer_request()`       | `(name) -> dict`                                                                                              | `{name, status}`                | API                      | Hủy phiếu (chỉ Pending/Rejected)                                                                                                |
| `transfer_asset()`                | `(asset_name, to_location, to_department=None, to_custodian=None, transfer_doc=None, actor=None) -> None`     | None                              | approve_transfer_request | Cập nhật location/department/custodian + ghi lifecycle event + audit                                                             |
| `is_capa_overdue()`               | `(status, due_date, ref_date=None) -> bool`                                                                   | bool                              | SoT predicate            | **SoT thuần** CAPA overdue: `status NOT IN ('Closed') AND due_date IS NOT NULL AND due_date < ref_date` (strict `<`)               |
| `_overdue_capa_filter()`          | `(ref_date=None) -> dict`                                                                                     | dict filter                       | SoT filter-builder       | **SoT filter** cho count/get_all/get_list — KPI/scorecard/quality-dash/drill ĐỀU gọi (byte-for-byte). Null-guard qua `between [floor, ref-1]` |
| `is_capa_open()`                  | `(status) -> bool`                                                                                            | bool                              | SoT predicate            | **SoT thuần** CAPA open (chưa đóng): `status NOT IN ('Closed')`. `'open'` = SUPERSET của `'overdue'` (Overdue VẪN open). None/rỗng → open |
| `_open_capa_filter()`             | `() -> dict`                                                                                                  | dict filter                       | SoT filter-builder       | **SoT filter** capa_open cho count/get_all/get_list — KPI dashboard / scorecard `capa_open_count` / quality-dash `capa_open` / drill `list_capas(not_closed=1)` / `get_capa_aging` `total_open` / **IMM-16 gate** (`check_asset_compliance_status` BR-16-09: Critical-CAPA-open ENFORCEMENT — `gate_wo_submit` IMM-08/09 + commissioning IMM-04) ĐỀU gọi (byte-for-byte). Bất biến dưới cron flip ('Overdue' VẪN ∈ tập mở → gate VẪN block). |

**Filter composition tại API layer — `list_capas` (BR-00-16, Self-Correction bug #4 Vòng 12).** `api/imm00.py::list_capas` nhận `status` (explicit) + `not_closed`/`overdue` (virtual). Cả hai đặt điều kiện trên field `status` ⇒ KHÔNG được dùng `filters.update(_open_capa_filter())` lên một filter-**dict** đã có `filters["status"]` (key trùng → clobber, biến AND thành either-or). Cách build đúng:

```python
conds = [[_DT_CAPA, "status", "=", status]] if status else []
if capa_type: conds.append([_DT_CAPA, "capa_type", "=", capa_type])
if asset:     conds.append([_DT_CAPA, "asset", "=", asset])
if int(overdue):          # overdue ⊂ open → thắng not_closed
    from assetcore.services.imm00 import _overdue_capa_filter
    for f, op, val in _as_conditions(_overdue_capa_filter()):
        conds.append([_DT_CAPA, f, op, val])
elif int(not_closed):
    from assetcore.services.imm00 import _open_capa_filter
    for f, op, val in _as_conditions(_open_capa_filter()):
        conds.append([_DT_CAPA, f, op, val])
# frappe.db.count(_DT_CAPA, filters=conds) và frappe.get_list(_DT_CAPA, filters=conds, ...)
# DÙNG CÙNG `conds` → pagination.total == len(items).
```

`_as_conditions(d)` = helper biến SoT dict (`{"status": ["not in", ["Closed"]], "due_date": ["between", [...]]}`) thành các tuple `(field, op, value)` để spread vào list-of-conditions. List-format cho phép 2 điều kiện cùng field `status` ⇒ AND thật. SoT filter-builder (`_open_capa_filter`/`_overdue_capa_filter`) **giữ nguyên** dict shape (không đổi — KPI dashboard/scorecard vẫn dùng trực tiếp); chỉ riêng `list_capas` (nơi có thể trùng field với explicit `status`) chuyển sang list-format.
| `check_capa_overdue()`            | `() -> None`                                                                                                  | None                              | Scheduler daily          | Flip {Open, In Progress, Pending Verification} quá hạn → Overdue + email QA. Idempotent + null-guard. Cùng INVARIANT SoT. KHÔNG đổi capa_open count (Overdue vẫn open) |
| `check_vendor_contract_expiry()`  | `() -> None`                                                                                                  | None                              | Scheduler daily          | Cảnh báo HĐ NCC 90/60/30 ngày                                                                                                  |
| `byt_expiry_filter()`             | `(bucket: str) -> dict`                                                                                       | dict filter                       | SoT filter-builder       | **SoT filter** số ĐKLH BYT sắp/đã hết hạn (BR-00-17). `'expiring'` → `{"byt_reg_expiry": ["between", [today, today+BYT_EXPIRY_SOON_DAYS]]}`; `'expired'` → `{"byt_reg_expiry": ["<", today]}`. CẢ HAI bucket loại bản ghi `byt_reg_expiry IS NULL/''` (chưa khai ĐKLH ≠ hết hạn). KPI `dashboard.get_overview` (count) + drill `list_assets(byt_status=…)` (list) gọi CÙNG helper → card == drill byte-for-byte. `BYT_EXPIRY_SOON_DAYS = 30` (named const, KHÔNG literal). |
| `check_registration_expiry()`     | `() -> None`                                                                                                  | None                              | Scheduler daily          | Cảnh báo BYT expiry 90/60/30/7 ngày                                                                                             |
| `check_insurance_expiry()`        | `() -> None`                                                                                                  | None                              | Scheduler daily          | Cảnh báo bảo hiểm 90/60/30/7 ngày                                                                                             |
| `check_service_contract_expiry()` | `() -> None`                                                                                                  | None                              | Scheduler daily          | Cảnh báo hợp đồng dịch vụ 90/60/30 ngày                                                                                    |
| `rollup_asset_kpi()`              | `() -> None`                                                                                                  | None                              | Scheduler monthly        | Rollup MTTR avg + uptime_pct cho từng asset                                                                                       |

### III.1a. SoT predicate — số ĐKLH BYT sắp/đã hết hạn (`byt_expiry_filter`, BR-00-17)

**Bối cảnh / lỗi thiết kế gốc (Self-Correction Vòng 31):** KPI "Đăng ký lưu hành Bộ Y tế" được đếm bằng **literal inline** trong `api/dashboard.py:62-63`
(`{"byt_reg_expiry": ["between", [today, today+30]]}` và `{"byt_reg_expiry": ["<", today]}`), trong khi `list_assets` (`api/imm00.py`) **không có** param `byt_status`
→ ô KPI **không drill được** (FE `get_overview` field `byt_expiring_30d`/`byt_expired` không có tile tiêu thụ; `AssetListView.vue` không có chip lọc theo ĐKLH).
Hệ quả: count KPI tồn tại nhưng không kiểm chứng được bằng danh sách → vi phạm INVARIANT "count == drill" (giống bug BR-08-12 PM due-soon & BR-05-15 depreciation).

**Fix:** rút predicate về **một** hàm SoT module-level `byt_expiry_filter(bucket)` (đặt cạnh `due_soon_filter`/`_overdue_capa_filter` trong `services/imm00.py`), gọi từ CẢ HAI read-path:
KPI count (`dashboard.get_overview`) **và** drill list (`list_assets(byt_status=…)`).

```python
BYT_EXPIRY_SOON_DAYS = 30  # NĐ98/2021 — cửa-sổ cảnh báo trước hạn cho dashboard quản trị (named const, KHÔNG literal)

def byt_expiry_filter(bucket: str) -> dict:
    """SoT (BR-00-17): filter dict cho 'số ĐKLH BYT sắp/đã hết hạn'.

    bucket = 'expiring' → byt_reg_expiry BETWEEN [today, today + BYT_EXPIRY_SOON_DAYS] (2 biên inclusive).
    bucket = 'expired'  → byt_reg_expiry < today (strict '<'; expiry == today CHƯA hết hạn).
    CẢ HAI bucket LOẠI bản ghi byt_reg_expiry IS NULL/'' — thiết bị CHƯA khai số ĐKLH
    KHÔNG phải 'hết hạn' (NĐ98: nghĩa vụ khai báo khác với nghĩa vụ gia hạn). Loại NULL/''
    qua điều kiện `["is", "set"]` (Frappe) — KHÔNG để between/`<` ngầm bắt chuỗi rỗng.

    INVARIANT (đo được): cùng DB →
      get_overview().assets.byt_expiring_30d == total của list_assets(byt_status='expiring')
      get_overview().assets.byt_expired     == total của list_assets(byt_status='expired')
    byte-for-byte (cùng predicate, cùng vendor scope). bucket khác → caller bỏ qua (no-op, KHÔNG throw).

    Ý nghĩa NĐ98/2021: số đăng ký lưu hành (ĐKLH) là điều kiện pháp lý để thiết bị y tế
    được lưu hành/sử dụng. ĐKLH hết hạn → thiết bị có thể phải dừng khai thác lâm sàng →
    tile danh sách phải drill được để Phòng QLTBYT rà soát & khởi tạo gia hạn kịp thời.
    """
```

**Khung tham chiếu (giống pattern đã ship):** `due_soon_filter` (BR-08-12, IMM-08) và `is_fully_depreciated` (BR-05-15, IMM-05) — cùng nguyên tắc "một predicate SoT, count == drill".

**Grep-guard (CI / review):** sau fix, `grep -n "byt_reg_expiry.*between\|byt_reg_expiry.*\[\"<\"" assetcore/api/dashboard.py assetcore/api/imm00.py` → **0 occurrence** literal-window NGOÀI thân `byt_expiry_filter`. `check_registration_expiry` (scheduler daily 90/60/30/7 — exact-day match, KHÔNG window) KHÔNG bị guard này tác động (predicate khác mục đích → giữ nguyên).

## III.1b. File: `assetcore/services/notifications.py` (Notification Framework — Wave N1)

> 3-tier: hook listener (entry) → service logic (recipient resolution + channel dispatch) → repository = Frappe core API (`enqueue_create_notification`, `Notification Settings`, `_safe_sendmail`). **KHÔNG modify core, KHÔNG DocType mới.** Type hints + docstring bắt buộc. Logic KHÔNG nằm trong controller.

| Function | Signature | Output | Caller | Mô tả |
|---|---|---|---|---|
| `notify_assignment` | `(doc, method=None) -> None` | None | hook `PM Work Order`/`Asset Repair` on_update+on_submit | Đọc `assigned_to`; nếu set & khác actor → `_dispatch` cho assignee. Idempotent: skip nếu assigned_to không đổi (so `doc.get_doc_before_save()`). |
| `notify_approval_pending` | `(doc, method=None) -> None` | None | hook `PM Work Order`/`Asset Repair` on_update+on_submit | Detect `workflow_state` đổi VÀO một state "cần duyệt" (xác định **động** qua metadata Workflow — xem §III.1b-1). Resolve approver(s) theo allowed-role của transition rời state đó → `_dispatch`. Idempotent: skip nếu workflow_state không đổi. |
| `resolve_recipients` | `(doc, role_or_field: str, include_self: bool = False) -> list[str]` | list[user] | service | Lấy recipient từ **field user** trên doc (vd `supervisor`, `assigned_to`); **mặc định loại bỏ actor** (`frappe.session.user`) để tránh self-notify (FR-00-NTF-04). **MỞ RỘNG (self-confirm, §III.1b-2b):** param opt-in `include_self=True` GIỮ actor lại để gửi xác nhận cho chính người báo. Mặc định `False` → hành vi cũ KHÔNG đổi (mọi caller hiện tại an toàn). Trả list duy nhất. |
| `resolve_approvers_by_workflow` | `(doc) -> list[str]` | list[user] | `notify_approval_pending` | **MỚI (vòng 2).** Đọc Workflow metadata của `doc.doctype`; với `doc.workflow_state` hiện tại, tìm các transition rời state này; lấy tập `allowed` role của các transition đó; resolve user enable đang giữ role (qua `frappe.get_users_with_role` hoặc tương đương). **Bổ sung** field `supervisor` nếu doc có & set. Loại actor + dedupe. |
| `_state_needs_approval` | `(doctype: str, state: str) -> bool` | bool | `notify_approval_pending` | **MỚI (vòng 2).** True nếu `state` là "cần duyệt" theo §III.1b-1: tồn tại ≥1 transition rời `state` mà `allowed` role thuộc tập role quản trị (mặc định `{"System Manager"}`, mở rộng được per-doctype qua `_APPROVAL_ROLES`). |
| `notify_incident_created` | `(doc, method=None) -> None` | None | hook `Incident Report` after_insert | **MỚI (vòng 3 — E3, IMM-12); MỞ RỘNG (vòng 9 — self-confirm).** Khi Incident Report vừa tạo → `_dispatch` cho người phụ trách. Recipient resolve động: (1) `assigned_to` nếu set (cross-assign — loại self như cũ); (2) nếu chưa assign → `reported_by`, **GỌI với `include_self=True`** để chính người tự báo nhận xác nhận "Đã ghi nhận sự cố của bạn" (self-confirm, FR-00-NTF-07). Subject/message phân nhánh: cross-assign = "Sự cố mới cần xử lý" vs self-confirm = "Đã ghi nhận sự cố của bạn". Skip docstatus=2. Xem §III.1b-2 + §III.1b-2b. |
| `notify_calibration_due` | `(asset_name, old_status, new_status) -> None` | None | service `imm11.check_calibration_expiry` (scheduler daily) | **MỚI (vòng 3 — E4, IMM-11).** Bắn 1 lần khi `calibration_status` của asset **chuyển VÀO** `DUE_SOON` hoặc `OVERDUE` (state-change guard: `old != new and new ∈ {DUE_SOON, OVERDUE}`) → chống spam mỗi ngày. Recipient: `responsible_technician` (primary), fallback `custodian` của AC Asset. Loại self-notify. Xem §III.1b-2. |
| `notify_escalation` | `(doc, method=None) -> None` | None | hook `PM Work Order` on_update | **MỚI (vòng 7 — E5, IMM-08).** Khi `workflow_state` **chuyển VÀO** một state ESCALATION (nguy cấp do role vận hành báo, KHÔNG phải finalize) → `_dispatch` cho supervisor + role quản trị để can thiệp. "State escalation" xác định **động** qua metadata Workflow (xem §III.1b-5), KHÔNG hard-code: state nháp (`doc_status=0`) kiểu `Danger` mà role vận hành (không phải role quản trị) chuyển VÀO. Bù khoảng trống E2 (E2 chỉ bắt state finalize do role quản trị → bỏ sót halt nguy cấp do KTV báo). Idempotent: skip nếu workflow_state không đổi; skip docstatus=2. Xem §III.1b-5. |
| `_state_is_escalation` | `(doctype: str, state: str) -> bool` | bool | `notify_escalation` | **MỚI (vòng 7).** True nếu `state`: (a) `doc_status=="0"` (chưa finalize, loại E2); (b) được **VÀO** bởi ≥1 transition do **role vận hành** (không thuộc `_approval_roles_for`); (c) có ≥1 transition **GỠ** rời state do **role quản trị** với `next_state` không thuộc `_NON_APPROVAL_NEXT_STATES`. KHÔNG dùng `State.type` "Danger" (không persist DB runtime — xem §III.1b-5). |
| `resolve_escalation_recipients` | `(doc) -> list[str]` | list[user] | `notify_escalation` | **MỚI (vòng 7).** Approver/can-thiệp = union(user giữ role quản trị có transition rời escalation-state) + field `supervisor` của doc nếu set. Tái dùng `get_users_with_role` + dedupe + loại actor (FR-00-NTF-04). |
| `_dispatch` | `(users: list[str], subject: str, message: str, doc) -> None` | None | service | Gọi `enqueue_create_notification(users, {subject, email_content, type:"Alert", document_type, document_name, from_user})` (bell — `email_content` giữ `message` ngắn như cũ). Với mỗi user, nếu `_user_wants_email(user)` → gửi **HTML** dựng qua `_render_email(subject, message, doc)` bằng `_safe_sendmail(recipients=[user], subject, message=<html>)`. **MỞ RỘNG (vòng 4):** email body là HTML có cấu trúc + deep-link, KHÔNG còn plain `message` thô. Xem §III.1b-3. |
| `_render_email` | `(subject: str, body_html: str, doc) -> str` | str (HTML) | `_dispatch` | **MỚI (vòng 4 — E5 template).** Dựng HTML email tái sử dụng cho **cả 4 event**: header (tiêu đề = `subject`), body (`body_html` — chính là `message` đã có `<b>`), **nút deep-link** tới record qua `frappe.utils.get_url_to_form(doc.doctype, doc.name)` khi doc có cả `doctype`+`name`, footer branding nhẹ "AssetCore". KHÔNG hard-code nội dung nghiệp vụ (subject/body do từng listener truyền vào). Frappe core tự sinh **plain-text fallback** từ HTML (`set_html_as_text` → `to_markdown`) → KHÔNG cần `text_content` thủ công. Xem §III.1b-3. |
| `run_sla_breach_scan` | `() -> None` | None | scheduler `hourly` | **MỚI (vòng 8 — E6, IMM-09).** Quét Asset Repair non-terminal (`docstatus=0`, `status ∉ {Completed, Cannot Repair, Cancelled}`), tính `pct = elapsed_h/sla×100` (deadline = `open_datetime + sla_target_hours`). WARNING khi `≥80%` & `<100%`; BREACH khi `≥100%` hoặc `sla_breached=1`. Anti-spam: BREACH dùng `sla_breached 0→1` state-change (set `sla_breached=1` đồng thời bắn 1 lần — giữ tương thích dashboard `cm_sla_breached`); WARNING dedupe qua Notification Log đã tồn tại cho WO. Per-WO try/except. Supersede `imm09.check_repair_sla_breach`. Xem §III.1b-6. |
| `_sla_recipients` | `(wo: dict) -> list[str]` | list[user] | `run_sla_breach_scan` | **MỚI (vòng 8).** Recipient động: `assigned_to` (primary), fallback `supervisor` + `get_users_with_role("Repair Manager")`. Loại self/Administrator + dedupe (FR-00-NTF-04). |
| `_warning_already_sent` | `(wo_name: str) -> bool` | bool | `run_sla_breach_scan` | **MỚI (vòng 8).** True nếu đã có Notification Log `document_type='Asset Repair' AND document_name=wo_name AND subject LIKE '%sắp vi phạm SLA%'` (dedupe WARNING Frappe-first, không field mới). |
| `_user_wants_email` | `(user: str) -> bool` | bool | `_dispatch` | True nếu `Notification Settings` của user có `enabled=1 AND enable_email_notifications=1` (default Frappe = bật). Tạo settings doc nếu chưa có (Frappe auto on user create). |
| `get_notification_preferences` | `(user: str \| None = None) -> dict` | `{email_enabled: bool}` | API | Service đọc toggle cho user hiện tại (hoặc truyền user). |
| `set_email_enabled` | `(enabled: bool, user: str \| None = None) -> dict` | `{email_enabled: bool}` | API | Set `enable_email_notifications` trên Notification Settings của user (chỉ self trừ System Manager). |

**Wiring `hooks.py::doc_events` (cùng commit với service):**
```python
"PM Work Order": {  # bổ sung vào entry hiện có
    "on_update": "assetcore.services.notifications.notify_assignment",
    "on_submit": "assetcore.services.notifications.notify_assignment",
},
"Asset Repair": {
    "on_update": "assetcore.services.notifications.notify_assignment",
    "on_submit": "assetcore.services.notifications.notify_assignment",
},
"Asset Repair": {  # notify_approval_pending wired cùng notify_assignment
    "on_update": "assetcore.services.notifications.notify_approval_pending",
},
"PM Work Order": {
    "on_update": "assetcore.services.notifications.notify_approval_pending",
},
# Vòng 3 — E3 Incident created
"Incident Report": {  # bổ sung vào entry hiện có (đã có validate gate IMM-12)
    "after_insert": "assetcore.services.notifications.notify_incident_created",
},
# Vòng 3 — E4 Calibration due: KHÔNG qua doc_events. Gọi trong scheduler
# imm11.check_calibration_expiry ngay sau khi set calibration_status mới.
# Vòng 7 — E5 Escalation: bổ sung listener vào on_update của PM Work Order
# (cùng entry đã có notify_assignment + notify_approval_pending).
"PM Work Order": {
    "on_update": "assetcore.services.notifications.notify_escalation",
},
```

### III.1b-1. Quy ước "state cần duyệt" + approver resolution (vòng 2 — sửa root-cause)

> **Bối cảnh / lý do thay đổi.** Bản Wave-N1 hard-code `_PENDING_APPROVAL_STATES = {"Pending Approval", "Chờ duyệt", ...}` và resolve approver qua field `supervisor`. Verify thực tế:
> - Cả 2 workflow Wave-1 (`imm_09_repair_workflow.json`, `imm_08_pm_workflow.json`) **KHÔNG có state nào** trùng whitelist trên → `notify_approval_pending` **chưa từng kích hoạt** trên dữ liệu thật (silent dead-code).
> - `Asset Repair` **không có field `supervisor`** (chỉ `requested_by`, `assigned_to`, `assigned_by`) → kể cả khi trúng state, approver luôn rỗng.
>
> Đây là lỗi thiết kế từ gốc (hard-code không khớp state machine thật). Sửa root, không vá triệu chứng.

**Quy ước chính thức (BA chốt):**

1. **"State cần duyệt" xác định ĐỘNG từ Workflow metadata, KHÔNG hard-code tên state.** Một `workflow_state` `S` của doctype `D` là "cần duyệt" khi: tồn tại ≥1 **Workflow Transition** rời `S` (`state == S`) thoả CẢ 3 điều kiện:
   - (a) `allowed` role thuộc tập **role phê duyệt** của doctype (mặc định `{"System Manager"}`, mở rộng per-doctype qua `_APPROVAL_ROLES: dict[str, frozenset[str]]`);
   - (b) `next_state` KHÔNG phải state hủy/từ chối (`_NON_APPROVAL_NEXT_STATES = {"Cancelled", "Đã hủy", "Rejected", "Từ chối"}`);
   - (c) **`next_state` là state finalize** — tức `doc_status == "1"` (submit) trong định nghĩa Workflow State. Đây là tín hiệu phân biệt **phê duyệt/chốt phiếu** với **phân công/điều phối** (dispatch giữ `doc_status=0`).

   Quy ước: *bước chuyển kế tiếp đưa phiếu sang trạng thái finalize (submit), không phải hủy, do vai trò quản trị thực hiện ⇒ state hiện tại đang chờ vai trò đó duyệt.*
   - **Vì sao cần điều kiện (c) — root-cause của false-positive (phát hiện khi chạy test thật TC-NTF-10):** Repair `Open` có transition `Open → Assigned` do `System Manager` (phân công KTV) — `next_state` không phải hủy, nên chỉ (a)+(b) sẽ coi `Open` là "cần duyệt" SAI. Nhưng `Assigned` có `doc_status=0` (vẫn nháp) → điều kiện (c) loại đúng. Còn `Pending Inspection → Completed` có `Completed.doc_status=1` (chốt phiếu) → giữ đúng.
   - Áp dụng thực tế (verify trên workflow Wave-1 thật): Repair `Pending Inspection` (`→ Completed`, System Manager, doc_status=1) ⇒ **cần duyệt**. Repair `Open` (`→ Assigned` doc_status=0; `→ Cancelled`) ⇒ KHÔNG. PM `In Progress` (tiến triển do `PM User`; `→ Cancelled` do System Manager) ⇒ KHÔNG. Repair `In Repair → Cannot Repair` (System Manager, doc_status=1) cũng là quyết định finalize của quản lý ⇒ cần duyệt (chấp nhận được — quản lý đang chốt kết luận).

2. **Approver = union(user giữ allowed-role phê duyệt của transition rời state) + field `supervisor` nếu có & set.** Resolve user theo role bằng API Frappe core (`frappe.get_users_with_role(role)` / `frappe.utils.user`), chỉ lấy user **enabled**. Loại actor hiện tại (FR-00-NTF-04) + dedupe. Nếu sau resolve không còn ai → không gửi (không lỗi).

3. **Đọc Workflow metadata Frappe-first.** Lấy Workflow active của doctype qua `frappe.get_all("Workflow", filters={"document_type": D, "is_active": 1})` rồi `frappe.get_doc("Workflow", name).transitions`. KHÔNG đọc trực tiếp JSON file. Cache trong request scope nếu cần. KHÔNG modify core, KHÔNG DocType mới.

4. **Idempotent + an toàn listener** (giữ nguyên contract Wave-N1): skip `docstatus==2`; chỉ bắn khi `workflow_state` thực sự đổi (so `get_doc_before_save()`); bọc `try/except` + `frappe.log_error`, KHÔNG làm vỡ luồng save.

5. **Hằng `_PENDING_APPROVAL_STATES` cũ bị loại bỏ** (thay bằng `_state_needs_approval` động). Đây là breaking-internal nhưng không đổi API public.

**Data model:** KHÔNG DocType mới. Notification Log (Frappe core) = record in-app + audit. Notification Settings (Frappe core) = per-user email toggle. Workflow / Workflow Transition (Frappe core) = nguồn metadata read-only cho resolution.

### III.1b-2. Mở rộng event vòng 3 — E3 Incident created (IMM-12) & E4 Calibration due (IMM-11)

> **Bối cảnh.** Engine vòng 1-2 (`_dispatch`, `resolve_recipients`) đã ổn định + 13 test xanh. Vòng 3 chỉ **tái dùng engine** + thêm 2 listener/recipient-mapping mới — KHÔNG viết lại dispatch, KHÔNG DocType mới, KHÔNG modify core. Cả 2 sự kiện nằm trong giai đoạn WHO HTM #5 (Maintenance), là loại sự kiện liên quan an toàn bệnh nhân (NĐ98 Art.67 incident reporting; Art.56 calibration).

**E3 — `notify_incident_created` (IMM-12, hook `Incident Report` after_insert):**

1. **Trigger:** `after_insert` — Incident vừa được tạo. Vì là after_insert nên KHÔNG cần idempotent-by-before-save (chỉ chạy đúng 1 lần/record); vẫn skip `docstatus==2` để an toàn.
2. **Recipient resolution (động):** `assigned_to` (Link User) nếu set → đó là người phụ trách xử lý; **fallback** `reported_by` nếu chưa phân công (để sự cố không "rơi"). Dùng `resolve_recipients(doc, "assigned_to")` (mặc định loại actor — cross-assign noise); nếu rỗng → `resolve_recipients(doc, "reported_by", include_self=True)`. **Cập nhật vòng 9 (self-confirm):** nhánh fallback `reported_by` DÙNG `include_self=True` để chính người tự báo (`reported_by == actor`) vẫn nhận xác nhận. Phân biệt 2 nhánh để chọn subject/message — xem §III.1b-2b. Loại Administrator + dedupe.
3. **Nội dung:** subject gồm `severity` + asset + incident number; message dẫn người nhận tới phiếu. `_dispatch` lo 2 kênh (bell luôn, email theo toggle).
4. **Audit:** Notification Log (Frappe core) = record bất biến → audit trail tự nhiên (FR-00-NTF-03). KHÔNG tạo lifecycle event riêng (Incident đã có audit chuỗi riêng của IMM-12).
5. **An toàn listener:** bọc `try/except` + `frappe.log_error`, KHÔNG làm vỡ luồng insert (LL-BE-20). Signature `(doc, method=None)` (LL-BE-6).

**E4 — `notify_calibration_due` (IMM-11, scheduler-driven):**

1. **Trigger:** gọi TRONG `imm11.check_calibration_expiry` (scheduler `daily` đã tồn tại). Scheduler này duyệt asset có `next_calibration_date`, tính `days_left`, set `calibration_status` ∈ {`OVERDUE`, `DUE_SOON`, `ON_SCHEDULE`}. Ngay TRƯỚC khi `AssetRepo.set_values`, đọc status cũ; sau khi xác định status mới, gọi `notify_calibration_due(asset_name, old_status, new_status)`.
2. **Anti-spam state-change guard (BẮT BUỘC):** chỉ `_dispatch` khi `old_status != new_status AND new_status ∈ {DUE_SOON, OVERDUE}`. Nhờ scheduler set ON_SCHEDULE/DUE_SOON/OVERDUE mỗi ngày, điều kiện "chuyển VÀO" đảm bảo mỗi lần escalation chỉ báo **đúng 1 lần** (ON_SCHEDULE→DUE_SOON báo 1 lần; DUE_SOON→OVERDUE báo lại 1 lần vì là escalation tăng mức; DUE_SOON→DUE_SOON KHÔNG báo). Đây là biến thể của idempotent-by-state-change đã dùng ở E1/E2.
3. **Recipient resolution (động):** đọc AC Asset → `responsible_technician` (Link User) primary; **fallback** `custodian` nếu chưa gán kỹ thuật viên. Loại actor (scheduler chạy dưới Administrator → thường không trùng) + dedupe.
4. **Nội dung:** subject phân biệt DUE_SOON ("sắp đến hạn hiệu chuẩn") vs OVERDUE ("QUÁ HẠN hiệu chuẩn"); message gồm asset + `next_calibration_date`.
5. **Audit + an toàn:** Notification Log = audit. Bọc `try/except` per-asset trong scheduler để 1 asset lỗi KHÔNG dừng cả batch.

**Data model (vòng 3):** KHÔNG DocType mới. Đọc field sẵn có: `Incident Report.assigned_to / reported_by / severity / asset`; `AC Asset.calibration_status / next_calibration_date / responsible_technician / custodian`. Audit = Notification Log (core).

### III.1b-2b. Self-confirm — xác nhận cho người tự báo (vòng 9 — FR-00-NTF-07)

> **Bối cảnh / lý do thay đổi (BA chốt).** FR-00-NTF-04 mặc định loại actor khỏi recipient để người gây action KHÔNG tự nhận noise (đúng cho assignment/approval/escalation/calibration/SLA — actor đã biết mình vừa làm gì). NHƯNG với **Incident Report tự báo** (`reported_by == actor`, chưa phân công người khác), `notify_incident_created` resolve `assigned_to` rỗng → fallback `reported_by` → `resolve_recipients` loại actor → **rỗng → không ai nhận**. Hệ quả thực tế: người vừa báo sự cố KHÔNG có bất kỳ phản hồi nào trên chuông, không rõ phiếu đã ghi nhận chưa (UX yếu, và với incident an toàn bệnh nhân — NĐ98 Art.67 — việc thiếu xác nhận đã-ghi-nhận là rủi ro). Đây là **lỗi thiết kế từ gốc của semantics recipient**, sửa root tại spec trước, không vá ở code.

**Quy ước chính thức (BA chốt):**

1. **Định nghĩa "self-confirm".** Là NGOẠI LỆ có kiểm soát của FR-00-NTF-04: với **event mà người báo chính là bên cần được xác nhận đã ghi nhận**, gửi 1 Notification Log cho chính actor dù actor == recipient. Đây KHÔNG phải "tự-notify mọi action": chỉ áp đúng các event được liệt kê (whitelist), KHÔNG mở cho action điều phối/phê duyệt.

2. **Phạm vi áp dụng (whitelist — đóng kín).** Vòng 9 self-confirm chỉ áp cho **Incident Report tự báo**: `notify_incident_created` nhánh fallback `reported_by` khi KHÔNG có `assigned_to`. Tất cả event còn lại GIỮ NGUYÊN FR-00-NTF-04 (mặc định loại actor):
   - `notify_assignment` — actor tự gán mình: KHÔNG self-notify (đã chủ động chọn, không cần xác nhận).
   - `notify_approval_pending` / `notify_escalation` — actor là người đẩy phiếu/báo lỗi: approver/cấp trên nhận, KHÔNG phải actor.
   - `notify_calibration_due` / `run_sla_breach_scan` — scheduler/Administrator: không có "self" thật, vẫn loại actor + Administrator.
   - **Khi Incident CÓ `assigned_to` (bất kể bằng ai, kể cả tự gán mình):** đi nhánh cross-assign như cũ — assignee≠actor nhận; nếu assignee==actor (tự gán) thì KHÔNG ai nhận (self-assign noise bị chặn, TC-NTF-16). Self-confirm CHỈ kích hoạt khi **field `assigned_to` thực sự rỗng/None** (chưa phân công ai). Phân biệt "assigned_to rỗng" với "assigned_to set nhưng resolve rỗng do là actor" là BẮT BUỘC để TC-NTF-16 (self-assign) không lọt sang nhánh self-confirm.

3. **Cơ chế (opt-in, KHÔNG đổi mặc định).** Thêm param `include_self: bool = False` cho `resolve_recipients`. Mặc định `False` ⇒ hành vi cũ giữ nguyên (mọi caller hiện hữu KHÔNG đổi). Chỉ nhánh self-confirm gọi `resolve_recipients(doc, "reported_by", include_self=True)`. KHÔNG thêm DocType/field; KHÔNG đổi `_dispatch`; KHÔNG modify core.

4. **Phân nhánh nội dung (subject/message).** `notify_incident_created` phải phân biệt:
   - **Cross-assign** (có `assigned_to` ≠ actor): subject "Sự cố mới [<severity>]: <name>", message "… Vui lòng kiểm tra và xử lý." (như cũ).
   - **Self-confirm** (fallback `reported_by`, recipient gồm actor): subject "Đã ghi nhận sự cố: <name>", message "Sự cố <name> bạn vừa báo đã được ghi nhận (mức độ …). Bộ phận kỹ thuật sẽ tiếp nhận xử lý." → ngữ nghĩa **xác nhận**, không phải "cần xử lý".
   - Lưu ý mixed-list: nếu fallback `reported_by` resolve ra **cả** reporter-là-actor **và** user khác (hiếm — `reported_by` là single Link, thực tế chỉ 1 user) → ưu tiên thông điệp self-confirm cho actor; giữ đơn giản: chọn template theo "recipient chứa actor".

5. **Idempotent + an toàn (giữ contract).** `after_insert` chạy 1 lần/record → không spam. Bọc `try/except` + `frappe.log_error`. Self-confirm chỉ sinh **1** Notification Log cho actor; KHÔNG gửi email nếu actor tắt toggle (FR-00-NTF-03 vẫn áp). Audit = Notification Log (FR-00-NTF-03).

**Test contract (BA chốt — KHÔNG phá test cũ):**

| TC | Trạng thái | Ý nghĩa |
|---|---|---|
| **TC-NTF-16** | **GIỮ NGUYÊN ngữ nghĩa, làm rõ scope** | `actor == assigned_to` (cross-assign tự gán) → KHÔNG dispatch (self-notify noise vẫn bị chặn). Setup: doc CÓ `assigned_to == actor`. Đây là nhánh cross-assign, KHÔNG phải self-confirm → assertion cũ đúng nguyên. |
| **TC-NTF-15** | GIỮ NGUYÊN | không `assigned_to`, `reported_by` ≠ actor → fallback reported_by nhận (cross-report). |
| **TC-NTF-24** (MỚI) | THÊM | **Self-confirm:** `assigned_to=None`, `reported_by == actor` → tạo **đúng 1** Notification Log cho actor; `subject` chứa "Đã ghi nhận". Đây là case trước đây trả rỗng (bug). |
| **TC-NTF-25** (MỚI) | THÊM | `resolve_recipients(doc, "reported_by", include_self=True)` trả list chứa actor; `include_self=False` (mặc định) loại actor → bảo vệ hành vi mặc định không đổi. |

> **Lưu ý ID:** TC-NTF-17/18 ĐÃ thuộc test calibration E4 — KHÔNG tái dùng. ID mới = TC-NTF-24/25 (kế tiếp sau TC-NTF-23 hiện hữu).

> **Phân biệt rạch ròi (chống hiểu nhầm khi code):** TC-NTF-16 (self-assign → chặn) và TC-NTF-17 (self-report → xác nhận) KHÔNG mâu thuẫn: khác nhau ở **field** (assigned_to vs reported_by) và **ngữ nghĩa nghiệp vụ** (điều phối vs ghi nhận). `include_self=True` CHỈ bật ở nhánh `reported_by`-fallback, nên self-assign vẫn bị `assigned_to`-resolve (mặc định) loại đúng.

**Data model (vòng 9):** KHÔNG DocType mới, KHÔNG field mới, KHÔNG sửa workflow/JSON. Chỉ thêm param `include_self` (default False) cho `resolve_recipients` + phân nhánh nội dung trong `notify_incident_created`. Audit = Notification Log (core).

### III.1b-3. HTML email template + deep-link (vòng 4 — nâng chất 4 event đã có)

> **Bối cảnh.** Engine vòng 1-3 gửi email bằng `message` thô (chuỗi có vài tag `<b>`) → trải nghiệm thật kém: không tiêu đề rõ, không link tới phiếu, không branding. Vòng 4 **chỉ nâng chất kênh email** của 4 event đã có, KHÔNG đổi recipient resolution, KHÔNG đổi anti-spam guard, KHÔNG DocType mới, KHÔNG modify core. Email là sự kiện liên quan vận hành (NĐ98 — thông báo phân công/duyệt/sự cố/hiệu chuẩn tới đúng người).

**Quy ước chính thức (BA chốt):**

1. **Một builder tái sử dụng cho CẢ 4 event — KHÔNG hard-code template trong từng listener.** `_render_email(subject, body_html, doc) -> str` nhận `subject` + `body_html` (chính là `message` mà listener đã dựng, đã có `<b>`) + `doc`, trả HTML hoàn chỉnh. Mỗi listener vẫn chỉ truyền subject + message như cũ → builder lo trình bày. Đây là điểm tái dùng duy nhất; thêm event mới chỉ cần gọi `_dispatch` như cũ.

2. **Cấu trúc HTML (Frappe-first, inline CSS — email client không đọc `<style>` ngoài):**
   - **Header**: dải tiêu đề chứa `subject` (đậm, nền nhạt).
   - **Body**: `body_html` nguyên văn (giữ `<b>` của listener).
   - **Deep-link** (điều kiện): nếu `doc` có CẢ `doctype` và `name` → nút "Mở phiếu" trỏ `frappe.utils.get_url_to_form(doctype, name)`. Đây là URL desk Frappe-native (`/app/<doctype>/<name>`) — luôn hợp lệ cho user Frappe đã đăng nhập; FE Vue SPA decoupled không có route ổn định cho mọi doctype nên KHÔNG dùng làm link email. Nếu doc thiếu doctype/name (vd `_dict` rời rạc) → bỏ nút, không vỡ.
   - **Footer**: dòng branding nhẹ "AssetCore — Hệ thống quản lý vòng đời thiết bị y tế" + lưu ý "email tự động, có thể tắt trong Cài đặt thông báo".

3. **Plain-text fallback = Frappe core, KHÔNG thủ công.** `frappe.sendmail`/email body khi nhận `message` là HTML và KHÔNG có `text_content` sẽ tự dựng phần `text/plain` qua `set_html_as_text` → `to_markdown(html)` (verify: `apps/frappe/frappe/email/email_body.py:186-190, 243-245`). Vì vậy `_dispatch` chỉ truyền `message=<html>`; multipart/alternative (html + text) sinh tự động. KHÔNG truyền `text_content`.

4. **Bell (in-app) KHÔNG đổi.** `enqueue_create_notification` vẫn nhận `email_content = message` ngắn như vòng 1-3 (Notification Log hiển thị chuông, không cần wrapper HTML). Chỉ kênh email dùng `_render_email`.

5. **An toàn:** builder thuần hàm dựng chuỗi, không I/O nghiệp vụ; `get_url_to_form` bọc trong try/except → lỗi sinh URL KHÔNG được làm vỡ `_dispatch` (vẫn gửi email không nút). Không escape `body_html` (đã do listener kiểm soát, không phải user input tự do).

**Data model (vòng 4):** KHÔNG DocType mới, KHÔNG field mới. Tái dùng `Notification Settings` (toggle email), `Notification Log` (bell + audit). Email Queue (core) lưu vết email đã gửi (cho KPI vòng sau, ngoài scope vòng 4).

### III.1b-4. KPI Notification Delivery — delivery rate & opt-out rate (vòng 5)

> **Bối cảnh (CLAUDE.md §18 — KPI bắt buộc).** Sau 4 vòng đã có engine 4 event + email HTML, nhưng KHÔNG đo được: email AssetCore có thực sự gửi đi không, và bao nhiêu user đã tắt email (giảm độ phủ thông báo). Vòng 5 thêm 2 KPI quản trị cho **System Manager**, đóng kín, **Frappe-first (KHÔNG DocType mới, KHÔNG modify core)**. Đây chính là phần "cho KPI vòng sau" mà §III.1b-3 đã hoãn.

**Vấn đề audit-linkage (BA chốt — quyết định thiết kế then chốt):**
Email do AssetCore gửi vòng 1-4 KHÔNG truy nguyên được trong `Email Queue` vì `_safe_sendmail` không truyền `reference_doctype`/`reference_name` → mọi record Email Queue có `reference_doctype = NULL`. Không thể tách email AssetCore khỏi email hệ thống khác → KPI delivery rate trên toàn bộ Email Queue sẽ nhiễu.

**Giải pháp (Frappe-first, nhẹ):** `_dispatch` truyền **reference của chính doc nghiệp vụ** vào `_safe_sendmail(reference_doctype=doc.doctype, reference_name=doc.name)`. `frappe.sendmail` ghi 2 field này vào Email Queue (verify: `apps/frappe/frappe/email/queue.py` — `add()` nhận `reference_doctype`/`reference_name`). Để tách riêng email AssetCore (vs email module khác có cùng doctype) ta lọc theo **tập doctype mà engine notify** (`AC Asset`, `Incident Report`, `PM Work Order`, `Asset Repair` — danh sách `_NOTIFY_REF_DOCTYPES`, mở rộng được). KHÔNG cần audit DocType riêng → audit trail = Email Queue (core, bất biến) + Notification Log (core). Email gửi từ vòng 5 trở đi sẽ linkable; email cũ (ref NULL) bị loại khỏi mẫu đo (nêu rõ giới hạn ở docstring + KPI response field `window_from`).

**Công thức KPI (BA chốt):**

| KPI | Công thức | Nguồn dữ liệu | Ngưỡng (màu) |
|-----|-----------|---------------|--------------|
| `delivery_rate` | `sent / (sent + failed)` × 100 | Email Queue: `status='Sent'` = sent; `status='Not Sent' AND error IS NOT NULL` = failed (Frappe ghi lỗi gửi vào `error`, status vẫn 'Not Sent'). Mẫu = chỉ email có `reference_doctype ∈ _NOTIFY_REF_DOCTYPES` trong cửa sổ `days` gần nhất (mặc định 30). `Not Sent` chưa có `error` = đang chờ queue → KHÔNG tính vào mẫu (tránh hạ tỷ lệ giả). | ≥95% xanh · 80–95% vàng · <80% đỏ |
| `opt_out_rate` | `opted_out / total_users` × 100 | `total_users` = User `enabled=1 AND user_type='System User'` (loại Administrator). `opted_out` = trong số đó, user có `Notification Settings` với `enable_email_notifications=0` OR `enabled=0`. User chưa có Notification Settings = mặc định nhận email (KHÔNG tính opt-out — Frappe default bật). | ≤10% xanh · 10–30% vàng · >30% đỏ |

**Edge cases (BẮT BUỘC xử lý — TDD):**
- Mẫu rỗng (chưa có email AssetCore nào trong cửa sổ) → `delivery_rate = None` (FE hiển thị "—", KHÔNG chia 0).
- `total_users = 0` → `opt_out_rate = None`.
- Cửa sổ `days` < 1 → clamp về 1.

**3-tier (CONVENTIONS §3):**

| Tier | Hàm | Chữ ký | Trách nhiệm |
|------|-----|--------|-------------|
| Repository | `notification_repo.count_email_delivery(ref_doctypes, days)` | `(frozenset[str], int) -> dict` | Đếm `sent`/`failed` từ Email Queue (raw count, KHÔNG tính tỷ lệ). |
| Repository | `notification_repo.count_email_opt_out()` | `() -> dict` | Đếm `total_users`/`opted_out` từ User + Notification Settings. |
| Service | `notifications.get_delivery_kpi(days=30)` | `(int) -> dict` | Gọi 2 repo, tính tỷ lệ + gắn ngưỡng màu, xử lý chia-0. Chỉ System Manager (kiểm tra `is_admin()`). |
| API | `api.notifications.get_delivery_kpi` | `@frappe.whitelist()` | Envelope `handle(svc.get_delivery_kpi, days)`. |

**KPI response shape:**
```jsonc
{
  "delivery_rate": 97.5,      // null nếu mẫu rỗng
  "sent": 39, "failed": 1,
  "opt_out_rate": 5.0,        // null nếu total_users=0
  "total_users": 20, "opted_out": 1,
  "window_days": 30,
  "delivery_status": "good",  // good|warn|bad|na — drive màu KPI card
  "opt_out_status": "good"
}
```

**Quyền:** chỉ System Manager (KPI quản trị toàn hệ thống) → `get_delivery_kpi` raise `ServiceError(FORBIDDEN)` nếu không phải admin. Repository đọc Email Queue/User là dữ liệu hệ thống — không thuộc vendor isolation.

**Data model (vòng 5):** KHÔNG DocType mới, KHÔNG field mới. Đọc: `Email Queue` (core — `status`, `error`, `reference_doctype`, `reference_name`, `creation`), `User` (core), `Notification Settings` (core). Ghi: chỉ thêm `reference_doctype`/`reference_name` vào email AssetCore gửi đi (đã có chỗ trong Email Queue, không thêm field).

### III.1b-5. E5 — Escalation lifecycle event (vòng 7 — IMM-08 Halted–Major Failure)

> **Bối cảnh / verify (đọc workflow JSON thật, không đoán).** Engine vòng 1-6 đã ổn định (36 test xanh, e2e production-ready). Khảo sát backlog "báo duyệt ở bước PM completion": đọc `imm_08_pm_workflow.json` → transition chốt phiếu `Hoàn thành PM` (`In Progress → Completed`) do **`PM User`** với `allow_self_approval=1`, **KHÔNG có approver gate** ở completion. Vậy việc "báo duyệt PM completion" **không tồn tại** trong state machine → loại đúng. (IMM-09 `Pending Inspection → Completed` do System Manager **đã** được E2 phủ — xem §III.1b-1 dòng "Áp dụng thực tế".)
>
> **Khoảng trống thật sự được tìm thấy:** PM Workflow có state `Halted–Major Failure` (`doc_status=0`, type=`Danger`): KTV (`PM User`) báo lỗi nghiêm trọng (`In Progress → Halted–Major Failure`), và chỉ **System Manager** mới gỡ được (`Tiếp tục sau xử lý → In Progress`) hoặc hủy (`Hủy phiếu → Cancelled`). Đây là **escalation vòng đời** đúng nghĩa (sự kiện có actor + from→to status, cần cấp trên can thiệp) nhưng **hiện KHÔNG bắn notification nào**: E1 chỉ bắt assignment, E2 cố ý loại state non-finalize (điều kiện (c) §III.1b-1). Vòng 7 đóng khoảng trống này = **E5 `notify_escalation`**.

**Quy ước chính thức (BA chốt):**

1. **"State escalation" xác định ĐỘNG từ Workflow metadata, KHÔNG hard-code tên state.** Một `workflow_state` `S` của doctype `D` là ESCALATION khi thoả CẢ 3:
   - (a) `S` có `doc_status == "0"` (chưa finalize) — **phân biệt rạch ròi với E2**: E2 chỉ bắt `doc_status==1` (finalize/chốt phiếu). Mỗi state thuộc đúng 1 trong 2 event → KHÔNG double-notify.
   - (b) `S` được **VÀO** bởi ≥1 transition do **role vận hành** (role KHÔNG thuộc `_approval_roles_for(D)`, vd `PM User`) — tức chính người thực thi đã đẩy phiếu vào trạng thái này (báo lỗi/sự cố), khác state khởi tạo (`Open` — không có transition VÀO) hay state do quản trị đặt (`Overdue` — vào bởi System Manager).
   - (c) tồn tại ≥1 transition **GỠ** rời `S` (`state == S`) do **role quản trị** (`_approval_roles_for(D)`) mà `next_state` KHÔNG thuộc `_NON_APPROVAL_NEXT_STATES` (hủy/từ chối) → cần cấp quản trị **can thiệp tích cực** để thoát (không phải chỉ còn nước hủy).
   - **Vì sao KHÔNG dùng `Workflow State.type == "Danger"` (sửa root-cause vòng 7 — phát hiện khi chạy test thật TC-NTF-30):** field style/`type` "Danger" CHỈ tồn tại trong file JSON fixture, **KHÔNG persist vào DB runtime** — `Workflow Document State` (child của Workflow) không có field `style`/`type`, và `Workflow State` master lưu `style=""` rỗng. Đọc `type` lúc runtime luôn None ⇒ điều kiện (b) cũ không bao giờ đúng. Thay bằng tín hiệu **có thật trong metadata transitions**: "vào bởi role vận hành + gỡ bởi role quản trị".
   - Áp dụng thực tế (verify workflow Wave-1 thật, đọc DB runtime): PM `Halted–Major Failure` (doc_status=0; VÀO bởi `PM User`; GỠ `Tiếp tục sau xử lý → In Progress` do System Manager) ⇒ **escalation**. PM `Open` (không có transition VÀO — state khởi tạo) ⇒ loại bởi (b). PM `Overdue` (VÀO bởi System Manager, không phải role vận hành) ⇒ loại bởi (b). PM `In Progress`/`Pending–Device Busy` (VÀO bởi PM User nhưng KHÔNG có lối GỠ do role quản trị — chỉ `Cancelled`) ⇒ loại bởi (c). PM `Completed`/Repair `Cannot Repair` (doc_status=1) ⇒ loại bởi (a), thuộc E2.

2. **Recipient = union(user giữ role quản trị của transition gỡ rời `S`) + `supervisor` của doc nếu set.** Tái dùng `get_users_with_role` (Frappe core) + dedupe + loại actor hiện tại (KTV vừa báo lỗi — FR-00-NTF-04) + loại Administrator. Rỗng → không gửi (không lỗi).

3. **Đọc Workflow metadata Frappe-first** (`_active_workflow` / `_active_workflow_transitions` / Workflow State con) — tái dùng helper §III.1b-1, KHÔNG đọc JSON file, KHÔNG modify core, KHÔNG DocType mới.

4. **Idempotent + an toàn listener:** skip `docstatus==2`; chỉ bắn khi `workflow_state` thực sự đổi VÀO `S` (so `get_doc_before_save()`); bọc `try/except` + `frappe.log_error`, KHÔNG làm vỡ luồng save. Signature `(doc, method=None)` (LL-BE-6).

5. **Nội dung:** subject `"Cảnh báo nâng cấp: <doctype> <name>"` (state nguy cấp); message nêu state + dẫn tới phiếu. `_dispatch` lo 2 kênh (bell luôn + email theo toggle), email HTML + deep-link tái dùng `_render_email`.

**Audit:** Notification Log (Frappe core) = record bất biến → audit trail tự nhiên (FR-00-NTF-03). KHÔNG tạo lifecycle event riêng (workflow_state đã là chuỗi audit của WO).

**Data model (vòng 7):** KHÔNG DocType mới, KHÔNG field mới, KHÔNG sửa workflow JSON. Đọc field/metadata sẵn có: `PM Work Order.workflow_state / supervisor`; `Workflow State.type / doc_status`; `Workflow Transition.state / allowed / next_state`. Audit = Notification Log (core). Email reference doctype `PM Work Order` đã có trong `_NOTIFY_REF_DOCTYPES` (vòng 5) → KPI delivery tự bao phủ E5.

### III.1b-6. E6 — SLA-about-to-expire / breach warning (vòng 8 — IMM-09 Asset Repair)

> **Bối cảnh / verify data model THẬT (đọc DocType JSON + service, không đoán).** Backlog "SLA-about-to-expire" cần per-record live deadline. Khảo sát 2 ứng viên:
> - **PM Work Order (IMM-08):** field thời gian là `due_date`/`scheduled_date`/`completion_date` kiểu **Date** (không phải Datetime), KHÔNG có link tới SLA Policy, KHÔNG có `sla_status`, KHÔNG có duration response/resolution per-WO. ⇒ **KHÔNG đủ** để tính deadline động chính xác theo giờ → **DEFER** (xem "Phần defer" cuối mục).
> - **Asset Repair (IMM-09):** CÓ ĐỦ data model live-SLA: `open_datetime` (Datetime, read_only, set lúc tạo qua `imm09.create_repair`) = mốc bắt đầu đồng hồ SLA; `sla_target_hours` (Float, read_only, set lúc tạo qua ma trận `get_sla_target(risk_class, priority)` — BR-09-05); `sla_breached` (Check, read_only); `status` có nhóm non-terminal (`Open/Assigned/Diagnosing/Pending Parts/In Repair/Pending Inspection`) và terminal (`Completed/Cannot Repair/Cancelled`); `assigned_to`. ⇒ **deadline = `open_datetime + sla_target_hours`**, `% đã trôi = elapsed_h / sla_target_hours × 100`. Đủ tính live, **KHÔNG cần migration / field mới**.
>
> **Khoảng trống thật sự được tìm thấy:** đã tồn tại scheduler `imm09.check_repair_sla_breach` (hourly) NHƯNG (1) **KHÔNG được đăng ký** trong `hooks.scheduler_events` (dead code — chỉ block `hourly` của imm16 đang chạy); (2) **chỉ** set `sla_breached=1` + `publish_realtime("cm_sla_breached")` — KHÔNG đi qua notification engine (không bell Notification Log, không email theo toggle, không deep-link, không vào KPI delivery); (3) **không có tầng cảnh báo "sắp hết hạn"** (warning ở ngưỡng %) — chỉ báo khi đã breach; (4) **không có anti-spam state-change guard** → bắn lại mỗi giờ. Vòng 8 đóng khoảng trống này = **E6 `notify_sla_breach_warning`** (scheduler-driven, biến thể idempotent-by-state giống E4).

**Quy ước chính thức (BA chốt):**

1. **Hai mức cảnh báo (tier), ngưỡng cấu hình ở service (KHÔNG hard-code rải rác):**
   - `WARNING` khi `pct_elapsed ≥ _SLA_WARN_PCT` (mặc định **80%**) và `< 100%` (chưa breach).
   - `BREACH` khi `pct_elapsed ≥ 100%` (đã quá deadline) **hoặc** `sla_breached == 1`.
   - WO terminal (`status ∈ {Completed, Cannot Repair, Cancelled}`) hoặc `docstatus != 0` → bỏ qua (đồng hồ SLA đã dừng).

2. **Anti-spam state-change guard (BẮT BUỘC — biến thể E4 idempotent-by-state, vì scheduler chạy lặp).** Mỗi WO chỉ báo đúng 1 lần cho MỖI mức leo thang. Vì Asset Repair KHÔNG có field lưu "đã báo SLA mức nào" và quy ước Frappe-first KHÔNG thêm field, dùng **2 tín hiệu CÓ THẬT, idempotent tự nhiên**:
   - **BREACH** dùng `sla_breached` (Check sẵn có) làm cờ state: chỉ bắn BREACH khi WO **vừa chuyển** `sla_breached 0→1` trong cùng lần quét (scheduler set `sla_breached=1` → đồng thời bắn 1 lần). Lần quét sau `sla_breached` đã =1 → KHÔNG bắn lại. Đây là "state-change" đúng nghĩa, bền vững qua restart.
   - **WARNING** (chưa có cờ DB) → dùng **dedupe qua Notification Log** (Frappe core, đã là audit): trước khi bắn WARNING, kiểm tra đã tồn tại Notification Log `document_type='Asset Repair' AND document_name=<wo> AND subject LIKE '%sắp vi phạm SLA%'` trong cửa sổ đời WO chưa; có rồi → skip. Frappe-first, không field mới, không state ngoài luồng. (BREACH dùng `sla_breached` vì rẻ hơn query; WARNING dùng Notification Log vì không có cờ.)

3. **Recipient (động, FR-00-NTF-04):** `assigned_to` (KTV đang xử lý) là primary; nếu chưa phân công → fallback `supervisor` (nếu có) rồi role quản trị Repair. Tái dùng `resolve_recipients(doc_like, "assigned_to")`; với union role quản trị dùng `get_users_with_role("Repair Manager")`. Loại self-notify + Administrator + dedupe. Rỗng → không gửi (không lỗi).

4. **Tính deadline Frappe-first:** `elapsed_h = time_diff_in_seconds(now_datetime(), open_datetime)/3600`; `sla = sla_target_hours or get_sla_target(risk_class, priority)` (tái dùng ma trận BR-09-05 đã có — KHÔNG nhân bản logic); `pct = elapsed_h / sla × 100` (guard chia-0: `sla <= 0` → bỏ qua WO đó).

5. **Idempotent + an toàn batch:** per-WO bọc `try/except` + `frappe.log_error` — 1 WO lỗi KHÔNG dừng cả batch (giống E4). `_dispatch` lo 2 kênh (bell luôn + email theo toggle), email HTML + deep-link tái dùng `_render_email`.

6. **Nội dung:** WARNING subject `"Sắp vi phạm SLA: Asset Repair <name>"`; BREACH subject `"VI PHẠM SLA: Asset Repair <name>"`; message nêu `% đã trôi` + giờ còn lại / giờ quá hạn + dẫn tới phiếu.

7. **Đăng ký scheduler:** thêm `assetcore.services.notifications.run_sla_breach_scan` vào `hooks.scheduler_events["hourly"]` (đồng bộ nhịp với scheduler `check_repair_sla_breach` cũ). E6 **supersede** `check_repair_sla_breach`: `run_sla_breach_scan` đảm nhiệm cả việc set `sla_breached=1` (giữ tương thích dashboard `cm_sla_breached`) **và** bắn notification — KHÔNG đăng ký song song 2 job để tránh trùng. `check_repair_sla_breach` cũ vẫn để nguyên (chưa từng được đăng ký nên không đụng) — không xoá file ngoài scope notification.

**Audit:** Notification Log (Frappe core) = record bất biến → audit trail tự nhiên (FR-00-NTF-03). Email reference doctype `Asset Repair` đã có trong `_NOTIFY_REF_DOCTYPES` (vòng 5) → KPI delivery tự bao phủ E6.

**Data model (vòng 8):** KHÔNG DocType mới, KHÔNG field mới, KHÔNG sửa workflow/DocType JSON. Đọc field sẵn có: `Asset Repair.open_datetime / sla_target_hours / sla_breached / status / priority / risk_class / assigned_to / supervisor`. Tái dùng `imm09.get_sla_target` (ma trận SLA BR-09-05) + engine `_dispatch`/`resolve_recipients`/`_render_email`.

**Phần DEFER — PM Work Order live-SLA (DESIGN, KHÔNG implement vòng 8):**

PM Work Order hiện KHÔNG đủ data để cảnh báo SLA động theo giờ. Để bật E6 cho PM WO ở vòng sau cần (đề xuất, chưa làm):
- **Field mới (migration patch):** `sla_policy` (Link → IMM SLA Policy) hoặc tối thiểu `resolution_due` (Datetime — deadline tuyệt đối tính lúc tạo WO); `started_at` (Datetime — mốc bắt đầu thực, thay `scheduled_date` kiểu Date thiếu giờ); `sla_breached` (Check). IMM SLA Policy đã có `response_time_minutes` + `resolution_time_hours` + `priority` (P1-P4) → nguồn duration sẵn sàng, chỉ thiếu liên kết WO↔Policy + mốc thời gian giờ.
- **Mapping priority:** PM WO chưa có field `priority`/`risk_class` riêng → cần thêm hoặc fetch từ asset/PM Schedule để chọn SLA Policy đúng.
- **Migration:** patch set `resolution_due` cho WO đang mở (backfill = `creation + resolution_time_hours` theo policy default).
- **Scheduler + ngưỡng:** tái dùng đúng `run_sla_breach_scan` (tổng quát hoá doctype) với cùng tier 80%/100% + anti-spam.
- **Lý do defer:** thêm field + migration trên DocType submittable đang Live (IMM-08) = thay đổi schema có rủi ro cao hơn nhiều so với reuse data sẵn có của IMM-09; vượt phạm vi "một vòng = một vấn đề". Ưu tiên giao trị thực (IMM-09 đóng kín) vòng này, PM WO làm vòng riêng sau khi review.

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

class Roles:        # 30 roles — 4 System + 26 Domain (13 module × Manager/User); see services/shared/constants.py::Roles
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

| ErrorCode          | Mô tả                              |
| ------------------ | ------------------------------------ |
| `NOT_FOUND`      | Record không tồn tại              |
| `FORBIDDEN`      | Không đủ quyền                   |
| `UNAUTHORIZED`   | Chưa đăng nhập                   |
| `VALIDATION`     | Vi phạm validation rule             |
| `BUSINESS_RULE`  | Gate / VR nghiệp vụ (HTTP 422)     |
| `CONFLICT`       | Vi phạm uniqueness / conflict state |
| `BAD_STATE`      | Sai trạng thái (HTTP 409)          |
| `DUPLICATE`      | Trùng lặp                          |
| `INVALID_PARAMS` | Tham số không hợp lệ             |
| `INTERNAL`       | Lỗi server không xác định       |

---

# Phần IV — Setup Guide (Installation & Migration)

## IV.1. Yêu cầu hệ thống

| Thành phần     | Phiên bản tối thiểu  | Ghi chú                                              |
| ---------------- | ------------------------ | ----------------------------------------------------- |
| OS               | Ubuntu 22.04 / Debian 12 | LTS khuyến nghị                                     |
| Python           | 3.10+                    | Frappe v15 yêu cầu                                  |
| MariaDB          | 10.6+                    | hoặc MySQL 8.0+                                      |
| Redis            | 6.0+                     | Queue + cache + socketio                              |
| Node.js          | 18.x                     | FE build (Vite)                                       |
| Frappe Framework | v15+                     | **Dependency DUY NHẤT — không cần ERPNext** |

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

# Manual verify roles — canonical 30 roles (post patch v3_2.001_module_role_redesign)
bench --site <site> console <<'PY'
import frappe
system_roles = ["AssetCore Super Admin", "AssetCore System User",
                "AssetCore Auditor", "Vendor Engineer"]
domain_managers = ["Data Manager", "Needs Manager", "Spec Manager", "Procurement Manager",
                   "Commissioning Manager", "Document Manager", "Training Manager",
                   "PM Manager", "Repair Manager", "Calibration Manager",
                   "Corrective Manager", "Inventory Manager", "Compliance Manager"]
domain_users = ["Data User", "Needs User", "Spec User", "Procurement User",
                "Commissioning User", "Document User", "Training User",
                "PM User", "Repair User", "Calibration User",
                "Corrective User", "Inventory User", "Compliance User"]
for r in system_roles + domain_managers + domain_users:
    print(r, "→", "OK" if frappe.db.exists("Role", r) else "MISSING")
PY
```

Fixtures shipped (verified vs `assetcore/fixtures/` 2026-05-27):

```
assetcore/fixtures/
├── role.json                          # 30 roles (4 System + 26 Domain) — patch v3_2.001
├── has_role.json                      # Role↔User pre-seed
├── role_profile.json                  # Role Profile (Frappe core) — gom bộ role chọn sẵn; persona là khái niệm FE (xem FE_Persona_Navigation.md §7.quinquies)
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

Priority chỉ còn **4 mức `P1..P4`** (P1 = khẩn cấp nhất). Bỏ tách `P1 Critical / P1 High` (dư thừa) — phân biệt mức độ đã do `risk_class` đảm nhận. Fixtures ship 5 policy active, mỗi priority có 1 `is_default=1`:

| Priority | Risk Class | Response (min) | Resolution (h) | is_default |
| -------- | ---------- | -------------- | -------------- | ---------- |
| P1       | Critical   | 15             | 4              | 1          |
| P1       | High       | 30             | 8              | 0          |
| P2       | Medium     | 240            | 48             | 1          |
| P3       | Low        | 480            | 120            | 1          |
| P4       | Low        | 1440           | 240            | 1          |

`get_sla_policy(priority, risk_class)` khớp chính xác `(priority, risk_class)` trước, fallback về policy `is_default=1` của priority đó (BR-00-05: mỗi `(priority, risk_class)` chỉ 1 policy active).

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
    """Domain User (PM User / Repair User / Calibration User) chỉ thấy AC Asset được gán cho mình.
    Vendor Engineer chỉ thấy Asset thuộc WO/PM/Repair/Cal được phân công.
    Nguồn: assetcore/permissions.py (post patch v3_2.001)."""
    roles = frappe.get_roles(user)
    technician_roles = {"PM User", "Repair User", "Calibration User"}
    if "AssetCore Super Admin" in roles:
        return ""
    if technician_roles & set(roles):
        return f"(`tabAC Asset`.responsible_technician = '{user}')"
    return ""
```

## V.3. `assetcore/hooks.py` — Fixtures

Fixtures hiện đăng ký qua file JSON trong `assetcore/fixtures/` (bench tự sync khi `bench migrate`):

| Fixture                                 | Doctype gốc           | Mục đích                  |
| --------------------------------------- | ---------------------- | ---------------------------- |
| `role.json`                           | Role                   | 30 roles (4 System + 26 Domain) |
| `has_role.json`                       | Has Role               | Default role assignments     |
| `role_profile.json`                   | Role Profile           | Gom bộ role chọn sẵn (Frappe core; persona = FE-only) |
| `module_profile.json`                 | Module Profile         | Workspace grouping           |
| `workflow.json`                       | Workflow               | Tất cả AssetCore workflows |
| `workflow_state.json`                 | Workflow State         | State catalog                |
| `workflow_action_master.json`         | Workflow Action Master | Action labels VN             |
| `workspace.json`                      | Workspace              | Sidebar layout               |
| `imm_sla_policy.json`                 | IMM SLA Policy         | SLA defaults                 |
| `imm15_custom_fields.json`            | Custom Field           | IMM-15 fields                |
| `imm16_custom_field_capa_record.json` | Custom Field           | IMM-16 CAPA field            |

## V.4. Database indexes

| Table                        | Index                             | Mục đích                   |
| ---------------------------- | --------------------------------- | ----------------------------- |
| `tabAC Asset`              | `lifecycle_status, docstatus`   | Dashboard filter              |
| `tabAC Asset`              | `next_pm_date`                  | PM due query                  |
| `tabAC Asset`              | `byt_reg_expiry`                | Registration expiry scheduler |
| `tabAC Asset`              | `responsible_technician`        | Permission Query              |
| `tabIMM Audit Trail`       | `asset, timestamp DESC`         | History per asset             |
| `tabIMM Audit Trail`       | `hash_sha256`                   | Verify chain lookup           |
| `tabAsset Lifecycle Event` | `asset, timestamp DESC`         | Timeline per asset            |
| `tabIMM CAPA Record`       | `status, due_date`              | Overdue scheduler             |
| `tabAC Supplier`           | `contract_end`                  | Expiry scheduler              |
| `tabAC Spare Part Stock`   | `UNIQUE(warehouse, spare_part)` | Stock integrity               |

---

## DoD — File 04 hoàn chỉnh

> Reviewed vs codebase 2026-05-08. Tất cả thông tin dưới đây đã được cross-check với code thực tế.

### I. DocType catalog

- [X] 27 DocTypes foundation IMM-00 đã liệt kê (verified vs `assetcore/assetcore/doctype/`)
- [X] Naming conventions AC / IMM / ALE / IR / CAPA
- [X] Trạng thái Live ✅

### II. DocType schemas

- [X] AC Asset (7 field groups + state machine)
- [X] AC Supplier (HTM fields + contract)
- [X] IMM Device Model (BR-00-01 mapping)
- [X] IMM Audit Trail (append-only + SHA-256)
- [X] IMM CAPA Record (state machine)
- [X] Asset Lifecycle Event (append-only + event type enum)
- [X] Incident Report (NĐ98 fields)
- [X] AC Location (tree + contact gộp `dept_head`/`contact_phone`, patch v3_1.007)

### III. Service layer

- [X] imm00.py: 22 public functions (verified vs code: lifecycle re-exports ×3, `transition_asset_status`, GMDN update/toggle, `validate_asset_for_operations`, `get_sla_policy`, CAPA open/close, 5 scheduler jobs, transfer CRUD ×5 + `transfer_asset`, monthly `rollup_asset_kpi`)
- [X] services/shared/: constants.py, errors.py, permissions.py (verified)
- [X] utils/: response, lifecycle, email, pagination (verified import paths)
- [X] ErrorCode string constants (verified vs constants.py)

### IV. Setup guide

- [X] System requirements (Frappe only, no ERPNext)
- [X] Fresh install + migration patch
- [X] Fixture load + SLA defaults

### V. Hooks registration

- [X] Scheduler events (daily + monthly)
- [X] Permission query condition
- [X] Fixtures
- [X] Database indexes
