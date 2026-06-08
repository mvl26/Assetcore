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

Hàm `_lifecycle_event_for(to_status, from_status="")` map (from,to) → event type. **`from_status` BẮT BUỘC** để phân biệt 2 ngữ nghĩa của `to='Active'` (xem RC-09 / BR-00-27):

| to_status         | from_status                                              | event_type              |
| ----------------- | -------------------------------------------------------- | ----------------------- |
| Active            | `Out of Service`                                         | `restored`            |
| Active            | Under Repair / Calibrating / Under Maintenance / Commissioned (mọi from khác `Out of Service`) | `activated`           |
| Commissioned      | (any)                                                    | `commissioned`        |
| Under Maintenance | (any)                                                    | `pm_started`          |
| Under Repair      | (any)                                                    | `repair_opened`       |
| Calibrating       | (any)                                                    | `calibration_started` |
| Out of Service    | (any)                                                    | `out_of_service`      |
| Decommissioned    | (any)                                                    | `decommissioned`      |
| (default)         | (any)                                                    | `restored`            |

> **RC-09 (Vòng 14 — BR-00-27): `restored` vs `activated` SoT theo from-status.** Trước Vòng 14 `_lifecycle_event_for` CHỈ nhận `to_status` ⇒ mọi đường về `Active` đều nhãn `activated` (mislabel cho khôi phục sau **tạm ngừng** OoS — đáng lẽ `restored`), và `_reschedule_pending_depreciation_on_restore` **lại tự** emit thêm 1 ALE `restored` → **double-emit** khi có kỳ Pending để dời (có-Pending→2 event `activated`+`restored`; không-Pending→1 event `activated` — KHÔNG nhất quán). Fix: `_lifecycle_event_for` nhận thêm `from_status`; khôi phục `Out of Service→Active` ⇒ DUY NHẤT 1 ALE `restored` emit bởi `transition_asset_status`; helper reschedule **KHÔNG còn** emit ALE (chỉ giữ `log_audit_event` State Change). Đường về Active **không** từ OoS (repair/calib/PM/commission) GIỮ nhãn `activated`. Áp dụng đồng nhất cả 2 call-site: service `transition_asset_status` + controller `ac_asset.on_update` (workflow-action path).

### II.1.8 Fields — QR cấp tài sản (Asset-level QR) — ADR-001

> **Nguồn:** [`../imm-04/ADR-001-asset-qr.md`](../imm-04/ADR-001-asset-qr.md) — quyết định cuối. Đề mục QR cấp tài sản (factory QR vòng 1). Schema-delta này thuộc **A1 (V2)** — chưa scaffold trong code (`ac_asset.json` hiện 0 field QR — verified 2026-06-04).

| Field        | DB Type      | Required | Description                                                                 | BR/Note                                                                 |
| ------------ | ------------ | -------- | --------------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| `qr_token` | varchar(32)  | NO (auto)| Khóa tra cứu mờ (opaque) cho deep-link QR. `secrets.token_urlsafe(16)` (~22 ký tự URL-safe). | **read_only**; **UNIQUE** (IDX); sinh `before_insert`; **idempotent** (sinh 1 lần, KHÔNG đổi khi update); enumeration-safe. Xem D1. |

**Sinh giá trị (3-tier — A1, hardening Vòng 17 B):**
- Service `assetcore/services/imm00.py`: helper PURE `generate_qr_token() -> str` = `secrets.token_urlsafe(16)` (1 lần thử, KHÔNG check DB); helper **SSoT collision-safe** `generate_unique_qr_token(exclude=None) -> str` (§II.1.8-COLL — loop `generate_qr_token` tới khi token KHÔNG trùng `AC Asset.qr_token` nào VÀ `!= exclude`); helper `ensure_asset_qr_token(asset_name) -> str` (idempotent: trả token có sẵn HOẶC `generate_unique_qr_token()` + set + emit `qr_generated`).
- Controller `ac_asset.py::before_insert`: nếu `not self.qr_token` → `self.qr_token = generate_unique_qr_token()` (collision-safe **pre-write** qua SSoT, KHÔNG gọi `generate_qr_token()` trần — §II.1.8-COLL).
- KHÔNG sinh trong `validate`/`on_update` (tránh đổi token khi update → hỏng nhãn đã in).

**Deep-link (D2):** URL tuyệt đối build bằng helper SSoT `_build_qr_url(qr_token)` (§II.1.8-QRBASE) — host = base-URL **công khai cấu hình được** (site_config `assetcore_qr_base_url`), fallback `frappe.utils.get_url(f"/a/{qr_token}")` khi chưa cấu hình. Resolve qua endpoint `resolve_qr_token(token)` (RBAC `asset.read`, A2).

**Vì sao field MỚI (KHÔNG dùng `name`/`internal_tag_qr`):** `name` = `AC-ASSET-.YYYY.-.#####` tuần tự → đoán được (enumeration); `internal_tag_qr` = `BV-{DEPT}-{YYYY}-{SEQ}` đoán được + doc-bound (chỉ sống ở commissioning). Chi tiết bảng loại bỏ: ADR-001 D1.

**Backfill (D5):** patch `v3_2.008_backfill_asset_qr_token` sinh `qr_token` cho mọi asset cũ/import/legacy (`qr_token` rỗng) — idempotent, collision-safe (qua **CÙNG** SSoT `generate_unique_qr_token` — §II.1.8-COLL, KHÔNG còn loop+catch Duplicate riêng), emit `qr_generated`. Xem §Migration.

**Tương thích ngược (D6):** GIỮ `internal_tag_qr` ở IMM-04 commissioning — `qr_token` chạy song song, KHÔNG thay thế. Dedup về 1 service ở vòng B.

---

#### II.1.8-COLL — SSoT sinh token chống va chạm UNIQUE (`generate_unique_qr_token`) — ADR-001 D1.1 / BR-00-31 — **NEW (Vòng 17 B)**

> **Đề mục Vòng 17 B (hardening / enumeration-safe & collision-safety).** Self-Correction lỗi thiết kế gốc: A1/D1 đặc tả collision-safety **rải rác 3 kiểu KHÔNG nhất quán** ở các đường ghi `qr_token`, tạo **2+ bản logic song song** + 1 đường HỞ:
> - `_ensure_qr_token` (before_insert) + `ensure_asset_qr_token`: gọi `generate_qr_token()` **TRẦN** — **0 guard va chạm** → token random trùng asset khác → INSERT/set_value đụng UNIQUE → `IntegrityError` thô (HTTP 500) lọt UI, abort INSERT.
> - `regenerate_asset_qr_token`: vòng `while new == old` chỉ guard token **CŨ**, KHÔNG guard token **asset khác** → vẫn có thể đụng UNIQUE → 500.
> - patch `v3_2.008`: tự loop **write-then-catch Duplicate** (`_set_token_collision_safe`) — bản logic THỨ 2, độc lập, post-write.
>
> Đây là **lỗi thiết kế gốc** (BA chưa đặc tả 1 SSoT pre-write check cho collision-safety). Fix: gom về **1 helper DUY NHẤT** `generate_unique_qr_token(exclude)` (pre-write check qua `frappe.db.exists`), MỌI đường ghi runtime + patch DELEGATE. Nguồn quyết định: [`../imm-04/ADR-001-asset-qr.md`](../imm-04/ADR-001-asset-qr.md) §D1.1. Spec ràng buộc đầy đủ: [`02_Analysis_Design.md`](./02_Analysis_Design.md) **BR-00-31** + **FR-00-76..79**. **Schema-delta: KHÔNG** (thuần helper + delegate + test; KHÔNG cap/field/DocType/enum/patch mới — chỉ sửa patch 008 sẵn có để delegate). `CAP_SET_VERSION` GIỮ `v95.3388ee5629c1`. FE KHÔNG đổi (BE-only).

**Helper SSoT `generate_unique_qr_token(exclude: str | None = None) -> str`** (`services/imm00.py` — MỚI, cạnh `generate_qr_token`):

```python
_MAX_QR_TOKEN_RETRY = 5  # bounded retry — CSPRNG 128-bit va ~0, vẫn guard UNIQUE

def generate_unique_qr_token(exclude: str | None = None) -> str:
    """SSoT collision-safe: sinh qr_token KHÔNG trùng AC Asset nào + != exclude.

    PURE token-gen (KHÔNG ghi DB — chỉ đọc qua frappe.db.exists để pre-check).
    Loop generate_qr_token() tối đa _MAX_QR_TOKEN_RETRY lần tới khi token:
      (a) frappe.db.exists("AC Asset", {"qr_token": token}) là falsy (chưa ai dùng), VÀ
      (b) token != exclude (chặn token cũ khi rotate — rotate trùng cũ = vô nghĩa).
    Cạn retry → frappe.throw (= frappe.ValidationError) message VI sạch — KHÔNG để
    IntegrityError thô (500) abort INSERT. Caller (before_insert/ensure/regenerate/
    patch) set token này rồi mới ghi DB → INSERT/set_value KHÔNG đụng UNIQUE.
    """
    for _attempt in range(_MAX_QR_TOKEN_RETRY):   # KHÔNG dùng `_` (shadow gettext _)
        token = generate_qr_token()
        if exclude is not None and token == exclude:
            continue
        if not frappe.db.exists(_DOCTYPE_ASSET, {"qr_token": token}):
            return token
    frappe.throw(
        _("Không sinh được mã QR duy nhất sau nhiều lần thử. Vui lòng thử lại."),
        title=_("Lỗi sinh mã QR"))
```

| Quy tắc Vòng 17 B | Lý do |
|---|---|
| **1 SSoT DUY NHẤT** `generate_unique_qr_token` — `grep 'generate_qr_token()' assetcore/` KHÔNG còn gọi trần ở đường GHI | root-cause dedup: 1 nguồn collision-safety, KHÔNG 2+ bản logic song song (before_insert hở + regenerate guard-một-nửa + patch write-then-catch). |
| Pre-write check qua `frappe.db.exists("AC Asset", {"qr_token": token})` (UNIQUE IDX → O(log n)) | bắt va chạm TRƯỚC khi ghi → INSERT/set_value KHÔNG bao giờ đụng UNIQUE → KHÔNG IntegrityError thô; không cần catch DB-exception phân tán. |
| Bounded retry `_MAX_QR_TOKEN_RETRY = 5`; cạn → `frappe.throw` (= `frappe.ValidationError`) message VI | CSPRNG 128-bit va ~0; 5 lần thừa sức. Cạn (bất khả nhưng guard) → lỗi domain rõ ràng (message VI sạch qua envelope), TUYỆT ĐỐI KHÔNG `IntegrityError` thô. Test contract `assertRaises(frappe.ValidationError)` (07 §QA). ⚠️ Loop dùng biến `_attempt`, KHÔNG `_` (tránh shadow gettext `_`). |
| Hàm **thuần token-gen — KHÔNG ghi DB** (chỉ `frappe.db.exists` read) | tách trách nhiệm: helper trả token unique; caller quyết định set vào doc (before_insert) hay `set_value` (ensure/regenerate/patch). Test gọi trực tiếp KHÔNG đụng DB-write. |
| `exclude` param chặn token cũ khi rotate | `regenerate_asset_qr_token(exclude=old)` → guard CẢ token cũ (rotate phải đổi) CẢ token asset khác (UNIQUE) trong **1** vòng → bỏ vòng `while new == old` cũ (guard-một-nửa). |
| 3 đường ghi runtime + patch 008 **DELEGATE** | `_ensure_qr_token` (before_insert), `ensure_asset_qr_token`, `regenerate_asset_qr_token`, `_set_token_collision_safe` (patch) — đều gọi helper, KHÔNG tự loop/catch. Patch vẫn idempotent + re-run = no-op. |

**Import delta `services/imm00.py`:** KHÔNG cần import thêm — `frappe`, `from frappe import _`, `_DOCTYPE_ASSET` đã có sẵn ở đầu file (helper dùng `frappe.throw` + `_()` cho message VI). KHÔNG raise `ServiceError` ở đây — test contract bám `frappe.ValidationError`.

**Import delta patch `v3_2/008`:** đổi `from assetcore.services.imm00 import generate_qr_token, emit_qr_generated` → `from assetcore.services.imm00 import generate_unique_qr_token, emit_qr_generated`; `_set_token_collision_safe(name)` gọi `generate_unique_qr_token()` (1 lần, đã unique) → `set_value` + `commit` (KHÔNG còn loop+catch Duplicate riêng). Helper cạn-retry raise → patch log_error + bỏ qua asset đó (GIỮ behavior idempotent best-effort).

> **BR-00-31 (Vòng 17 B): SSoT collision-safe qr_token.** Mọi đường sinh `qr_token` (before_insert + ensure + regenerate + backfill) PHẢI delegate `generate_unique_qr_token(exclude=None)` (pre-write check `frappe.db.exists` + bounded retry `_MAX_QR_TOKEN_RETRY=5` + cạn→`frappe.throw`/`frappe.ValidationError` message VI, KHÔNG IntegrityError thô). KHÔNG còn `generate_qr_token()` trần ở đường ghi (chỉ helper SSoT gọi bare). Helper thuần token-gen (KHÔNG ghi DB). Phân biệt: `ensure` idempotent if-empty (đã có token → no-op, KHÔNG gọi helper, KHÔNG emit lần 2); `regenerate` luôn overwrite (`exclude=old`). Xem §II.1.8-COLL + 02 FR-00-76..79.

---

#### II.1.8-QRBASE — Base-URL deep-link công khai cấu hình được (`_build_qr_url` / `_qr_base_url`) — ADR-001 D2.1 / BR-00-30 — **NEW (Vòng 14 B)**

> **Đề mục Vòng 14 B (hardening / deep-link host).** Self-Correction lỗi thiết kế gốc: D2 cũ coi `frappe.utils.get_url(f"/a/{token}")` là final → trên site nội bộ ra `http://miyano/a/<token>` (host LAN) → camera điện thoại KHÔNG mở được (P2 blocker tái diễn eval Vòng 4/9/10). Nguồn quyết định: [`../imm-04/ADR-001-asset-qr.md`](../imm-04/ADR-001-asset-qr.md) §D2.1. Spec ràng buộc đầy đủ: [`02_Analysis_Design.md`](./02_Analysis_Design.md) **BR-00-30**. **Schema-delta: KHÔNG** (thuần helper + đọc `frappe.conf` + regression test; site_config là config runtime). `CAP_SET_VERSION` GIỮ `v95.3388ee5629c1`. FE KHÔNG đổi (BE-only).

**Helper SSoT `_build_qr_url(token: str) -> str`** (`services/imm00.py` — đổi thân, GIỮ signature):
1. `base = _qr_base_url()` (đọc + validate `frappe.conf.get("assetcore_qr_base_url")` nội bộ).
2. `base` hợp lệ → return `f"{base}/a/{token}"` (base đã strip `/` cuối → đúng 1 `/`).
3. `base` rỗng/None (vắng config HOẶC config sai đã reject) → return `frappe.utils.get_url(f"/a/{token}")` (fallback — hành vi cũ, dev/test KHÔNG vỡ).
4. Token nối THẲNG (KHÔNG `quote`/encode) — token urlsafe `[A-Za-z0-9_-]` không có ký tự cần escape; bảo toàn token y nguyên (BR-00-30 §5).

**Helper `_qr_base_url() -> str | None`** (đọc `frappe.conf` + validate ở 1 chỗ DUY NHẤT; config-time, KHÔNG đụng `frappe.db` → an toàn no-request/batch):
- `frappe.conf.get("assetcore_qr_base_url")` rỗng/None/non-str/whitespace-only → `None` (im lặng — vắng config là hợp lệ, KHÔNG cảnh báo).
- Strip whitespace + `rstrip("/")` (dấu `/` thừa cuối). Parse `urllib.parse.urlsplit(base)`. Reject (→ `None` qua `_qr_base_url_reject()` = `frappe.logger().warning` cảnh báo **1 lần** + return None, KHÔNG throw) khi BẤT KỲ:
  - `scheme ∉ {"http","https"}` (thiếu scheme hoặc scheme lạ);
  - `netloc` rỗng (không có host);
  - `path` khác rỗng (có path — gồm chứa `/a/...` lồng nhau);
  - `query` hoặc `fragment` khác rỗng;
  - chứa khoảng trắng giữa chuỗi (check `any(c.isspace())` trước parse).
- Hợp lệ → return `f"{scheme}://{netloc}"` (nối `/a/` ở `_build_qr_url`).

**Consumer (1 SSoT — KHÔNG nơi nào tự `get_url('/a/...')`):**
| Consumer | Vị trí | Dùng |
|---|---|---|
| `build_asset_label_data` | `services/imm00.py:393` | `_build_qr_url(token)` |
| `build_asset_label_data_batch` | `services/imm00.py:452` | `_build_qr_url(token)` |
| `regenerate_asset_qr_token` payload | `api/imm00.py:414` | `_build_qr_url(new)` |
| `imm04.generate_qr_label` (B-3 dedup) | `services/imm04.py:1012` | `_build_qr_url(token)` (lazy import — Pattern B) |
| `resolve_qr_token` | `services/imm00.py:226` | **KHÔNG** trả `qr_url` (read-only payload) — KHÔNG đụng |

**Grep-guard:** `grep -rn "get_url(.*\/a\/\|\"/a/\|'/a/'" services/` → chỉ còn 1 điểm sinh URL (trong `_build_qr_url`). Mọi `get_url('/a/...')` khác đã loại.

**Regression (token thật eval):** `_build_qr_url('AanTF-3HT9K3dFyWyaZLNw')`:
- base `https://htm.benhvien.vn/` → `https://htm.benhvien.vn/a/AanTF-3HT9K3dFyWyaZLNw` (token y nguyên, đúng 1 `/`).
- không config → `<get_url>/a/AanTF-3HT9K3dFyWyaZLNw` (fallback, token y nguyên).
- config sai (`ftp://x`, `htm.benhvien.vn` thiếu scheme, `https://x/a/b`, `https://x?q=1`, `"https://x /y"`) → fallback `get_url` + cảnh báo, KHÔNG throw.

---

#### II.1.8a — A2: Resolve deep-link `qr_token → asset` (`resolve_qr_token`) — ADR-001 D2/D4

> **Đề mục A2 (V3).** Endpoint resolve + route FE `/a/:token`. RBAC `asset.read` (xem §III.1c-1 — A2 thêm domain Asset). Chi tiết envelope ở [`05_API_Specification.md`](./05_API_Specification.md) §III.1 `resolve_qr_token`.

**Endpoint:** `assetcore.api.imm00.resolve_qr_token(token: str)` — `@frappe.whitelist()` (GET, auth-required, KHÔNG `allow_guest`).

**Contract (3-tier — API → service → repo):**

```python
# api/imm00.py
from frappe.rate_limiter import rate_limit          # top-of-file import (precedent auth.py:10)
AC_QR_RESOLVE_RATE_LIMIT = 30                        # 30 req/60s/IP/endpoint — Vòng 12 B (BR-00-29) — resolve/scan (đọc)
AC_QR_REGEN_RATE_LIMIT = 10                          # 10 req/60s/IP — Vòng 27 B (BR-00-38) — rotate (ghi); RIÊNG, THẤP hơn resolve

@frappe.whitelist()
@rate_limit(limit=AC_QR_RESOLVE_RATE_LIMIT, seconds=60, ip_based=True)  # chạy TRƯỚC thân hàm → 429 trước RBAC
def resolve_qr_token(token: str = ""):
    from assetcore.services.shared import rbac
    rbac.require("asset.read")                       # 403 PermissionError nếu không có cap
    name = frappe.db.get_value("AC Asset", {"qr_token": token}, "name")
    if not name:
        return _err(_(_ERR_ASSET_NOT_FOUND), 404)    # token sai → 404, KHÔNG 500, KHÔNG leak
    try:
        assert_vendor_can_access("AC Asset", name)    # IDOR/vendor isolation — TÁI DÙNG
    except ServiceError as e:
        return _err(e.message, e.code)                # vendor ngoài scope → 403
    return _ok({
        "name": name,
        "asset_code":        frappe.db.get_value("AC Asset", name, "asset_code") or "",
        "lifecycle_status":  frappe.db.get_value("AC Asset", name, "lifecycle_status") or "",
        "device_model_name": ...,   # enrich qua device_model → IMM Device Model.model_name
        "location_name":     ...,   # enrich qua location → AC Location.location_name
    })
```

| Quy tắc A2 | Lý do |
|---|---|
| Gate `rbac.require("asset.read")` **đầu hàm**, TRƯỚC mọi DB read | RBAC-gate; cap resolve qua `frappe.has_permission("AC Asset","read")` (DocPerm), KHÔNG hardcode role |
| Token không tồn tại → **404** (`AC-E001`), KHÔNG 500 | enumeration/leak-safe — lookup 1 query, message generic |
| IDOR: tái dùng `assert_vendor_can_access("AC Asset", name)` (`services/shared/scope.py:160`) | vendor ngoài scope → 403, KHÔNG re-implement, KHÔNG trả data |
| Payload tối thiểu màn redirect: `name, asset_code, lifecycle_status, device_model_name, location_name` | A2 CHỈ resolve+redirect; màn info đầy đủ = A6/V7 |
| **KHÔNG ghi audit/lifecycle khi resolve** | read-only lookup; tránh spam audit chain mỗi lần quét (chốt ADR D4). `qr_generated` ghi ở A1 (sinh token), `label_printed` ghi ở A3 `mark_label_printed` (sự kiện in) |

**Verify cap tồn tại (acceptance, chống RBAC dead-gate):**
```python
from assetcore.services.shared.rbac import CAPABILITY_MAP
assert "asset.read" in CAPABILITY_MAP   # XANH chỉ SAU khi A2 thêm "Asset" vào _DOMAIN_PRIMARY
```

##### II.1.8a-RL — Rate-limit 2 endpoint QR deep-link resolve (Vòng 12 B — BR-00-29) — **NEW**

> **Đề mục Vòng 12 B (hardening/security).** Áp `@rate_limit` lên **CẢ HAI** entry-point camera điện thoại: `resolve_qr_token` (`/a/<token>`) VÀ `get_asset_scan_info` (`/scan/:token`). Chống brute-force token + DoS. Thuần thêm decorator + hằng + test — **KHÔNG** cap/field/DocType/patch mới; `CAP_SET_VERSION` GIỮ `v95.3388ee5629c1`; FE KHÔNG đổi. Ngưỡng + lý do chốt: [`05_API_Specification.md`](./05_API_Specification.md) §I.7a + [`02_Analysis_Design.md`](./02_Analysis_Design.md) BR-00-29.

**Decorator layout (BẮT BUỘC — precedent `auth.py:66-68`):**
```python
@frappe.whitelist()                                              # ngoài cùng (dispatch)
@rate_limit(limit=AC_QR_RESOLVE_RATE_LIMIT, seconds=60, ip_based=True)  # SÁT def
def resolve_qr_token(token: str = ""): ...

@frappe.whitelist()
@rate_limit(limit=AC_QR_RESOLVE_RATE_LIMIT, seconds=60, ip_based=True)
def get_asset_scan_info(token: str = "", name: str = ""): ...
```

| Quy tắc RL | Lý do |
|---|---|
| Hằng `AC_QR_RESOLVE_RATE_LIMIT = 30` (đầu `api/imm00.py`), `seconds=60`, `ip_based=True` | 1 chỗ chỉnh, KHÔNG literal rải rác; `ip_based` đồng nhất `register_user` (`auth.py:67`); KHÔNG `key=` (token đổi mỗi request → bucket vô dụng) |
| `@rate_limit` bọc NGOÀI thân hàm → 429 **TRƯỚC** `rbac.require` | frappe tăng counter rồi `frappe.throw(RateLimitExceededError)` trước khi gọi `fn` → no-leak (0 byte asset build); thứ tự RL→RBAC nhất quán |
| Mỗi endpoint **bucket RIÊNG** | cache key `rl:{frappe.form_dict.cmd}:{ip}` gồm `cmd` → 2 endpoint KHÔNG chung trần; 1 scan = 1 resolve + 1 scan_info đếm riêng |
| Đếm MỌI call (kể cả 404/403) | counter++ trước thân hàm → dò token-sai (404) vẫn bị tính → chống enumeration |
| Vượt → `frappe.RateLimitExceededError` (HTTP **429**), body generic | no-leak parity 404/403; KHÔNG payload/name/asset_code/lý-do |
| **KHÔNG** áp lên `get_asset_label_data[_batch]`/`mark_label_printed` (3 endpoint in-nhãn) | đã `asset.write`-gated, low-volume admin; in-nhãn-hàng-loạt là tần-suất-cao hợp lệ → least-surprise |
| **CÓ** áp lên `regenerate_asset_qr_token` (rotate) — hằng RIÊNG `AC_QR_REGEN_RATE_LIMIT=10`, bucket RIÊNG (Vòng 27 B / BR-00-38) | **Self-Correction:** rotate KHÁC in-nhãn — là GHI bảo mật (vô hiệu hoá nhãn đã in + audit), có thể bị spam-rotate (DoS nhãn + write-amplification). Ngưỡng THẤP hơn resolve (rotate hiếm hơn quét). KHÔNG chung counter resolve/scan. Chi tiết §II.1.8d + 02 BR-00-38 |
| Test/CLI bypass có chủ đích | `rate_limit` wrapper `if not frappe.request: return fn(...)` → unit test cũ (gọi hàm trực tiếp, không set `frappe.local.request`) KHÔNG trip limiter → A2/A6 suite cũ KHÔNG regress |

**Test 429 (HTTP context):** class test MỚI phải set `frappe.local.request` truthy (giống `_http_call` của `TestQrWhitelistHttpLayer`) + `frappe.local.request_ip` + `frappe.form_dict.cmd` (cache key cần `cmd`), dội >30 call → `assertRaises(frappe.RateLimitExceededError)`; ≤30 → vẫn 200/404/403. Xem [`07_Testing_QA.md`](./07_Testing_QA.md) §III.6.c. **Lưu ý dọn dẹp:** test phải xoá cache key `rl:*` ở teardown (hoặc dùng IP/cmd duy nhất mỗi test) → tránh rò trần sang test khác.

#### II.1.8-NORAWTOKEN — No-raw-token parity trên đường ĐỌC AC Asset (`get_asset` strip + guard) — ADR-001 §D4.1 / BR-00-34 — **NEW (Vòng 24 B)**

> **Đề mục Vòng 24 B (hardening / enumeration-safe — no-raw-token on asset-read).** Self-Correction lỗi thiết kế gốc: rule 9 (D4) chốt no-raw-token CHỈ cho `regenerate_asset_qr_token` (đường GHI), KHÔNG cho đường ĐỌC. `get_asset` build payload bằng `frappe.get_doc("AC Asset", name).as_dict()` → trả NGUYÊN dict gồm `qr_token` thô → token (khóa tra cứu MỜ enumeration-safe, D1) rời BE qua đường đọc → mở rộng bề mặt tấn công. Nguồn quyết định: [`../imm-04/ADR-001-asset-qr.md`](../imm-04/ADR-001-asset-qr.md) §D4.1. Spec ràng buộc đầy đủ: [`02_Analysis_Design.md`](./02_Analysis_Design.md) **BR-00-34**. **Schema-delta: KHÔNG** (thuần strip 1 key + guard test). `CAP_SET_VERSION` GIỮ `v95.3388ee5629c1`. FE KHÔNG đổi (BE-only — 0 FE đọc field `data.qr_token` từ payload đọc-asset; verified `grep -rn qr_token frontend/src` = chỉ endpoint-name/comment/URL-flow, KHÔNG consumer payload).

**Strip trong `get_asset` (`api/imm00.py`):**
```python
@frappe.whitelist()
def get_asset(name: str):
    if not frappe.db.exists(_DT_ASSET, name):
        return _err(_(_ERR_ASSET_NOT_FOUND), 404)
    try:
        assert_vendor_can_access(_DT_ASSET, name)        # IDOR 403 — GIỮ NGUYÊN
    except ServiceError as e:
        return _err(e.message, e.code)
    doc = frappe.get_doc(_DT_ASSET, name).as_dict()
    doc.pop("qr_token", None)                            # B-24: STRIP token thô (no-raw-token)
    # … enrich display names (category_name/location_name/device_model_name/…) GIỮ NGUYÊN …
    return _ok(doc)
```

| Quy tắc B-24 | Lý do |
|---|---|
| **STRIP `qr_token`** (`doc.pop("qr_token", None)`) SAU `as_dict()`, TRƯỚC enrich/`_ok` | token thô KHÔNG rời BE qua đường đọc; opaque-key/enumeration-safe (D1) chỉ giữ giá trị nếu token không lộ |
| **KHÔNG re-whitelist** — chỉ pop 1 key | `get_asset` GIỮ "trả đầy đủ HTM fields" (FE `AssetDetailView` cần đủ data); whitelist tường minh có rủi ro rớt field khác → FE thiếu data |
| RBAC/IDOR/404 **GIỮ NGUYÊN** | B-24 CHỈ strip token; `frappe.db.exists` 404 + `assert_vendor_can_access` 403 KHÔNG đổi (không nới/siết quyền) |
| `qr_token` KHÔNG cần ở client | hiển thị → field nghiệp vụ (đã có); deep-link/in nhãn → `qr_url` server-side qua `get_asset_label_data`/`regenerate_asset_qr_token`. `get_asset` KHÔNG là nguồn deep-link |

**Parity các đường đọc khác (KHÔNG đụng code — test khẳng định):**

| Endpoint | Trạng thái | Vì sao parity |
|---|---|---|
| `get_asset_timeline(name)` | ✅ tự nhiên | `frappe.get_list("Asset Lifecycle Event", fields=[…])` — list event field tường minh, KHÔNG đọc `AC Asset`, KHÔNG `qr_token` |
| `get_asset_kpi(name)` | ✅ tự nhiên | `frappe.get_doc` chỉ để đọc field KPI; payload build dict tường minh (`name`, `lifecycle_status`, `uptime_pct`, `mtbf_days`, …) — KHÔNG `as_dict()` → KHÔNG `qr_token` |
| `resolve_qr_token`, `get_asset_scan_info`, `get_asset_label_data[_batch]` | ✅ đã có | payload whitelist tường minh (A2/A6/A3 — "KHÔNG `as_dict()` rồi pop") |

**Guard chống tái phát (Grep/AST — BẮT BUỘC):** test khẳng định 0 endpoint trong `assetcore/api/imm00.py` (và mọi `api/*.py`) trả `frappe.get_doc(_DT_ASSET, …).as_dict()` mà KHÔNG strip `qr_token` trước `_ok`. Phát hiện qua AST (`ast.walk` tìm node `Call` `.as_dict()` trên `get_doc("AC Asset"/_DT_ASSET, …)` thiếu `pop("qr_token")` cùng hàm) HOẶC grep-pattern. Chống regress khi thêm endpoint asset-read MỚI. Chi tiết: [`07_Testing_QA.md`](./07_Testing_QA.md) §Guard no-raw-token.

#### II.1.13-TESTPREFIX — Reserved test-prefix exclusion ở `list_assets` + count SSoT escape-safe — BR-00-35 — **NEW (Vòng 25 B)**

> **Đề mục Vòng 25 B (hardening / data-hygiene — reserved test-prefix exclusion ở list + count SSoT).** Self-Correction lỗi thiết kế gốc: `list_assets` + 3 nguồn count KHÔNG có predicate loại asset rác test/security-audit (`_Test*`/`_Probe*` theo Frappe fixture convention prefix `_`; `name` series `SI-*` của security-injection probe SEC-02) → user thật thấy record rác ở `/assets` trang 1 + thẻ KPI "Tổng thiết bị" đếm DƯ (memory `test_session_20260529*`: 53 asset leak từng phải purge tay). **KHÔNG xoá data** — record giữ lại cho test/audit; chỉ ẨN khỏi UI vận hành + count. Spec ràng buộc đầy đủ: [`02_Analysis_Design.md`](./02_Analysis_Design.md) **BR-00-35** + **FR-00-80..83**. **Schema-delta: KHÔNG** (thuần helper + 4 wiring + test). `CAP_SET_VERSION` GIỮ `v95.3388ee5629c1`. FE list/count **tự hưởng lợi, KHÔNG đổi component** (BE-only).

**SSoT predicate `reserved_test_prefix_sql` (`services/imm00.py`):**
```python
def reserved_test_prefix_sql(alias: str = "") -> tuple[str, list]:
    """SSoT (BR-00-35): raw WHERE-fragment loại asset rác test/security-audit.

    Trả ``(cond_sql, params)`` để AND vào MỌI query list/count AC Asset:
      - asset_name KHÔNG bắt đầu literal '_'  (LIKE r'\_%' ESCAPE '\' — '_' đầu
        chuỗi là LITERAL, KHÔNG phải wildcard 1-ký-tự; '_' ở GIỮA tên vô can).
      - name KHÔNG bắt đầu 'SI-'              (LIKE 'SI-%').
    Escape-safe TƯỜNG MINH (ESCAPE '\\') — KHÔNG dựa default-backslash MariaDB.
    Params bound (KHÔNG nội suy → no-injection). 1 SSoT — grep-guard 0 literal lặp.

    Args:
        alias: prefix bảng (vd 'a') khi query có JOIN/alias → '{alias}.'; rỗng
            khi query bảng trần (`tabAC Asset`). KHÔNG nội suy giá trị user.
    """
    a = f"{alias}." if alias else ""
    cond = f"{a}asset_name NOT LIKE %s ESCAPE '\\\\' AND {a}name NOT LIKE %s"
    return cond, [r"\_%", "SI-%"]
```

| Quy tắc B-25 | Lý do |
|---|---|
| **Raw fragment + `ESCAPE '\\'` tường minh** (KHÔNG filter-operator `["not like", …]`) | Frappe v15 operator `not like` (`operator_map.py:140`→pypika `not_like`) emit `NOT LIKE` **THIẾU `ESCAPE`** → escape `_` chỉ dựa default-backslash MariaDB (mong manh, vỡ nếu `NO_BACKSLASH_ESCAPES`). Raw + ESCAPE tường minh = escape-safe portable (acceptance) |
| **Params bound** `[r"\_%", "SI-%"]` (KHÔNG f-string giá trị vào SQL) | chống injection; chỉ `alias` (hằng nội bộ caller, KHÔNG user input) nội suy vào tên cột |
| **1 SSoT** — literal `'\_%'`/`'_%'`/`'SI-%'` chỉ trong thân helper | grep-guard: `grep -rn "SI-%\|\\\\_%" assetcore/api assetcore/services` ⟹ chỉ helper. KHÔNG lặp ở 4 call-site |
| **Predicate AND THÊM** — KHÔNG clobber filter/scope hiện có | `byt_expiry_filter`/search `or_filters` (field KHÁC `name`) GIỮ NGUYÊN; **`apply_vendor_scope` cũng dùng field `name`** ⟹ xem RC-LIST-VENDORCLOBBER bên dưới (compose AND qua filter-list form, KHÔNG dict-merge) |

**Wiring 4 điểm (INVARIANT `total == len(items)`):** vì `frappe.db.count(dt, filters)` **KHÔNG nhận raw-SQL + params** (chỉ filter dict/list — `database.py:1269`) và `frappe.get_list` **KHÔNG nhận raw AND-condition mang `ESCAPE`**, predicate được áp như sau để 4 nguồn ĐỒNG NHẤT tập kết quả:

| # | Call-site | Cách áp predicate | Ghi chú parity |
|---|---|---|---|
| 1 | `list_assets` **list query** (`api/imm00.py:200` `get_list`) | bổ sung 2 filter-operator `["asset_name","not like", r"\_%"]` + `["name","not like","SI-%"]` vào `filters` (AND với base) — `get_list` ANDs vào WHERE; trên MariaDB default-escape = backslash ⟹ tập kết quả TRÙNG raw-ESCAPE count | list & count cùng engine MariaDB → cùng tập rows ⟹ `total==len(items)` |
| 2 | `list_assets` **non-search count** (`api/imm00.py:188`) | thay `frappe.db.count(_DT_ASSET, filters)` bằng **raw count dùng `reserved_test_prefix_sql()`** (build `WHERE` từ filters-dict + AND `cond`, params bound) HOẶC `frappe.db.count` với CÙNG 2 filter-operator như #1 (escape-safe đảm bảo ở nguồn search #3 + INVARIANT-test) | đếm CÙNG predicate với list #1 |
| 3 | `list_assets` **search raw-SQL count** (`api/imm00.py:181-186`) | nối ` AND (<cond>)` từ `reserved_test_prefix_sql()` vào `WHERE` raw SQL hiện có; params = `[like×4] + ["\\_%","SI-%"]` | đây là nguồn ESCAPE-tường-minh chính thức |
| 4 | `get_overview.assets_total` (`dashboard.py:57`) | `_count(_DT_ASSET)` → thêm filter-operator `["asset_name","not like", r"\_%"]` + `["name","not like","SI-%"]` (helper `_count` nhận filters) HOẶC raw count CÙNG predicate | thẻ KPI "Tổng thiết bị" == list mặc định (parity dashboard↔list) |

> **Khuyến nghị impl (BE tự chốt, giữ INVARIANT):** để CHẮC CHẮN `total == len(items)` byte-for-byte VÀ escape-safe ở MỌI nguồn, ưu tiên dùng `reserved_test_prefix_sql()` (raw + ESCAPE tường minh) cho CẢ list lẫn count qua **1 WHERE-builder chung** (tránh lệch giữa filter-operator path và raw-ESCAPE path). Nếu dùng filter-operator cho `get_list`/`db.count` (đường ngắn), test INVARIANT (#2 dưới §07) PHẢI khẳng định 2 path trả CÙNG tập trên data có cả `_Test*`/`SI-*` lẫn `Model_X`/`TS-…`.

**0 false-positive (FR-00-83):** `'\_%'` neo ĐẦU chuỗi ⟹ `Model_X` (`_` ở GIỮA) KHÔNG khớp; `'SI-%'` chỉ khớp `name` mở đầu `SI-` ⟹ `AC-ASSET-2026-00001`, `TS-2025-USG-001` an toàn; asset tên thường (`Máy thở`) hiện đầy đủ.

---

**RC-LIST-VENDORCLOBBER — Self-Correction Vòng 26 B (HIGH security regression — AUTH-01 vendor isolation).** **▶️ ĐÂY là đề mục Vòng 26 B — phần ƯU TIÊN; phần wiring/escape-safe ở trên (Vòng 25) GIỮ NGUYÊN trừ điểm merge dưới đây.**

> **Reconcile tên helper (đọc trước):** code đã ship dùng bộ 3 helper trong `services/imm00.py`: `reserved_prefix_sql(alias="") -> (frag, params)` (raw ESCAPE-safe), `reserved_asset_names() -> list[str]` (NEGATE → tên `name` rác), `reserved_prefix_filter() -> dict` (= `{"name": ["not in", names]}`, rỗng → `{}`). **KHÔNG đổi tên** sang `reserved_test_prefix_sql` (bản nháp Vòng 25) — **0 rename** (acceptance). Mọi reference `reserved_test_prefix_sql` trong tài liệu này = đồng nghĩa với bộ 3 helper đã ship; phần fix Vòng 26 CHỈ đụng điểm MERGE trong `list_assets`, KHÔNG đụng thân helper (wiring dashboard.py + 2 depreciation đang GREEN).

**Triệu chứng ([QA] báo):** Vendor Engineer gọi `list_assets` nhận **MỌI asset non-reserved** thay vì chỉ asset được giao việc → vỡ AUTH-01.

**Root cause (phân tích code thật):**
1. `apply_vendor_scope(filters, _DT_ASSET)` (`api/imm00.py:167`) cho Vendor Engineer (không bypass) đặt `filters["name"] = ["in", assigned]` — vì `_VENDOR_SCOPE_FIELD_MAP["AC Asset"] = "name"` (`services/shared/scope.py:99,152`).
2. Ngay sau (`api/imm00.py:176`) `filters.update(reserved_prefix_filter())` đặt `filters["name"] = ["not in", reserved]`.
3. `dict.update` với CÙNG key `name` ⟹ **GHI ĐÈ** → predicate vendor-scope biến mất; chỉ còn reserved-exclusion ⟹ vendor thấy tất cả asset non-reserved. Comment "name chưa từng là filter-key" SAI.
4. INVARIANT `total == len(items)` vẫn giữ (count #2/#3 cũng clobber như list) ⟹ test Vòng 25 xanh giả; `test_imm00_reserved_prefix` chỉ cover field `department` (≠ `name`); suite chính chạy Administrator (bypass scope) → KHÔNG lộ.

**Fix (CHỈ điểm MERGE, KHÔNG đụng SSoT helper) — compose AND qua filter-list form:**
- `reserved_prefix_filter()` và `apply_vendor_scope` cùng nhắm field `name` ⟹ KHÔNG được sống chung trong 1 filter-dict (key trùng → 1 thắng).
- `frappe.get_list` / `frappe.db.count` / `count_with_or` (`services/shared/filters.py`) đều nhận **filters dạng list-of-conditions** `[[doctype, field, op, value], ...]`, trong đó **cùng một field có thể xuất hiện ở NHIỀU dòng** và được **AND** lại → biểu diễn được `name in assigned` **AND** `name not in reserved` đồng thời.
- **Khuyến nghị impl (BE tự chốt — fix chỉ ở `list_assets`):** sau `apply_vendor_scope`, KHÔNG `filters.update(reserved_prefix_filter())`. Thay vào: chuyển `filters` (dict) sang filter-list, rồi APPEND 1 dòng `[_DT_ASSET, "name", "not in", reserved]` (lấy `reserved = reserved_asset_names()`; rỗng → bỏ qua, no-op). Dòng `name in assigned` từ `apply_vendor_scope` (đã có khi vendor) đứng RIÊNG → cả hai cùng tồn tại, ANDed. Truyền filter-list này cho CẢ `count_with_or` (#2/#3) lẫn `get_list` (#1) → 1 nguồn predicate ⟹ INVARIANT giữ.
  - Lưu ý cài đặt: `apply_vendor_scope` đã hỗ trợ shape `list` (`scope.py:154-155`: nếu `filters` là list → append `[doctype, field, "in", assigned]`). Có thể chuyển `filters` sang list-form NGAY từ đầu (trước `apply_vendor_scope`) để cả scope lẫn reserved cùng append dòng vào list — sạch hơn. Bất kỳ cách nào, **kết quả phải là: hai dòng `name` cùng tồn tại trong filter-list, ANDed**.
- **Đã xác minh thực nghiệm trên site miyano** (`bench console`, AC Asset, 3 tên thật): dict.update → 889 row (clobber); filter-list 2 dòng `name` → đúng `assigned ∖ reserved`; `frappe.db.count(dt, filters=<list-form>)` == `len(get_list(...))`; `get_all` + `or_filters` (search) cùng đúng; empty-scope `["__none__"]` AND reserved → 0 row.

**Bất biến phải đạt (FR-00-84):**
| Điều kiện | Yêu cầu |
|---|---|
| Vendor Engineer có scope | `result ⊆ assigned` ∧ `result ∩ reserved = ∅` (= `name ∈ assigned ∖ reserved`) |
| Vendor Engineer scope RỖNG | `assigned=["__none__"]` AND reserved-exclusion → **0 row** (KHÔNG fallback toàn bộ) |
| INVARIANT count==list | `total == len(items)` cho MỌI persona: Administrator/bypass + **KTV nội bộ read-all** + Vendor Engineer (isolated). **Điều kiện đủ (ADR-IMM00-LIST-SCOPE §4b):** count phải permission-aware như `get_list` (`count_with_or` dùng `frappe.get_list(limit_page_length=0)`, KHÔNG `db.count`/`get_all`). Trước fix, KTV nội bộ vỡ INVARIANT (count 1430 không scope vs rows 0 scoped) — P1 factory run2. |
| Administrator / bypass-role | scope no-op (filters không có `name in …`) → chỉ reserved-exclusion áp; baseline GIỮ XANH |

**Phạm vi (đã verify):** CHỈ `list_assets` bị (endpoint DUY NHẤT chèn `name in assigned` rồi merge reserved). 2 endpoint depreciation **KHÔNG đổi hành vi**: `list_assets_depreciation` (`api/imm00.py:2570`) + `get_depreciation_stats` (`:2643`) KHÔNG gọi `apply_vendor_scope` và base filter KHÔNG có key `name` (chỉ `docstatus`/`depreciation_method`/`lifecycle_status`/`asset_category`) ⟹ `filters.update(reserved_prefix_filter())` vẫn an toàn ở đó (test khẳng định no-regress). Wiring `dashboard.py` GIỮ NGUYÊN (get_overview không vendor-scope).

#### II.1.8b — A3: Dữ liệu in nhãn + sự kiện in (`get_asset_label_data` / batch / `mark_label_printed`) — ADR-001 D3

> **Đề mục A3 (V4) + B (siết RBAC, V8+).** BE: endpoint trả payload nhãn (1 + batch) READ-ONLY về print-event + endpoint ghi sự kiện in (`label_printed`) + audit. Envelope chi tiết ở [`05_API_Specification.md`](./05_API_Specification.md) §III.1 (`get_asset_label_data`, `get_asset_label_data_batch`, `mark_label_printed`). Vị trí code: **`api/imm00.py` + `services/imm00.py`** (cùng nhà với `resolve_qr_token`/`ensure_asset_qr_token` — đây là logic registry cấp `AC Asset`; IMM-04 chỉ cross-link, KHÔNG đụng `internal_tag_qr` ở vòng A — ADR D6).
> **Vòng B (2026-06-04):** 3 endpoint trên SIẾT gate `require("asset.read")` → `require("asset.write")` (least-privilege — in nhãn là hành-động-ghi). *(superseded bởi D6 dưới.)*
> **✅ D6 (EXECUTED Vòng 3, 2026-06-08 — ADR-IMM00-QR-SCAN-ACTION):** TÁCH cap riêng — 3 endpoint in nhãn `require("asset.write")` → **`require("asset.print")`** (→(AC Asset,"print"); DocPerm print=1 sẵn cho persona vận hành KTV/QL vật tư → in được NGAY); `regenerate_asset_qr_token` `require("asset.write")` → **`require("asset.qr.rotate")`** (→(AC Asset,"write"); rotate = GHI). Thêm 2 cap → **`CAP_SET_VERSION` v95.3388ee5629c1 → v97.c30c69b8974d** (FE `auth.ts` ĐÃ bump). Read-only `resolve_qr_token`/`get_asset_scan_info`/`get_asset` GIỮ `asset.read`. IDOR `assert_vendor_can_access` GIỮ NGUYÊN. Lý do: `asset.write` chỉ Super Admin có → trước D6 KTV/QL vật tư KHÔNG in/rotate được (self-correction P2).
> **Consumer cross-module (vòng 13 / B-3 — ADR-001 §D6.1):** IMM-04 `services.imm04.generate_qr_label` **tái dùng** `ensure_asset_qr_token(final_asset)` + `_build_qr_url(token)` (lazy import — Pattern B) để dựng `qr_url=/a/<token>` cho nhãn commissioning (dedup về 1 deep-link). 2 helper này KHÔNG đổi signature/behavior — IMM-00 là SSoT sinh token + URL. Vì `ensure_asset_qr_token` idempotent → consumer KHÔNG gây double-emit `qr_generated`. Spec IMM-04: [`../imm-04/04_Backend_Design.md`](../imm-04/04_Backend_Design.md) §8.1.1.

**Import delta `api/imm00.py`** (thêm vào block `from assetcore.services.imm00 import (...)` line 20-36): `ensure_asset_qr_token, build_asset_label_data, build_asset_label_data_batch, emit_label_printed`. **Vòng 22 (BR-00-33):** thêm `_MAX_LABEL_BATCH` vào CÙNG block import (hằng SSoT ở service — KHÔNG redefine literal ở api). `assert_vendor_can_access` + `rbac` + `_ok`/`_err` đã import sẵn (line 14-19). `frappe.utils.get_url` dùng trực tiếp (đã import `frappe`). Message `_ERR_LABEL_BATCH_TOO_LARGE` đặt cạnh `_ERR_ASSET_NOT_FOUND` trong `api/imm00.py` (nội suy `{_MAX_LABEL_BATCH}` để khỏi drift).

**Service constants/helpers cần thêm trong `services/imm00.py`** (hiện chưa có):
- `LABEL_PRINTED_EVENT = "label_printed"` (cạnh `QR_GENERATED_EVENT` line 100).
- **`_MAX_LABEL_BATCH = 200`** (Vòng 22 / BR-00-33): hằng SSoT DUY NHẤT giới hạn số asset/lần cho `get_asset_label_data_batch` + `mark_label_printed`. Đặt cạnh các hằng QR khác (vd dưới `_MAX_QR_TOKEN_RETRY`). KHÔNG literal `200` lặp ở `api/imm00.py` — api `import` hằng này. (Service-side thuần là HẰNG; cap-CHECK đặt ở API tier vì là gate HTTP-status, đồng nhất pattern gate ở api/imm00.py.)
- `build_asset_label_data(asset_name: str) -> dict` (service): lấy 1 row + enrich `device_model_name`/`location_name`; gọi `ensure_asset_qr_token(asset_name)` (idempotent) rồi `qr_url = _build_qr_url(token)` (SSoT §II.1.8-QRBASE — host công khai cấu hình được, fallback `get_url`). **KHÔNG emit `label_printed`** (read-only về sự kiện in).
- `build_asset_label_data_batch(names: list[str]) -> list[dict]` (service): **1 truy vấn gộp** `frappe.get_all("AC Asset", filters={"name":["in",names]}, fields=["name","asset_code","lifecycle_status","device_model","location","qr_token"])` → map theo `name`; resolve `device_model`→`model_name` + `location`→`location_name` qua **2 IN-query gộp** → dict; build `qr_url` từ `qr_token` đã lấy (token-less → `ensure_asset_qr_token` chỉ cho asset thiếu); trả theo **đúng thứ tự `names`**; name không có row → `{"name": n, "error": "AC-E001"}`. **KHÔNG N+1** (cấm loop `get_value` mỗi asset).
- `emit_label_printed(asset_name, actor=None)` (service): 1 `create_lifecycle_event(event_type=LABEL_PRINTED_EVENT, root_doctype="AC Asset", root_record=asset_name, from_status="", to_status="")` + 1 `log_audit_event(event_type="System", ref_doctype="AC Asset", ref_name=asset_name, change_summary="In nhãn QR cấp tài sản.")`. Khác `emit_qr_generated` (best-effort): `mark_label_printed` ghi sự kiện in NĐ98 → **KHÔNG nuốt lỗi** (lỗi ghi event → raise → 422/500, all-or-nothing).

**Contract API (3-tier — gate ở API tier, logic ở service):**

```python
# api/imm00.py — D6 (EXECUTED Vòng 3): gate đổi asset.write → asset.print (in nhãn)
@frappe.whitelist()                                       # GET — dữ liệu in nhãn (nhóm PRINT)
def get_asset_label_data(asset: str = ""):               # P1: str="" (KHÔNG str|None → tránh 417)
    rbac.require("asset.print")                           # D6: 403 nếu user KHÔNG có asset.print
    if not asset or not frappe.db.exists(_DT_ASSET, asset):
        return _err(_(_ERR_ASSET_NOT_FOUND), 404)         # leak-safe, KHÔNG 500
    assert_vendor_can_access(_DT_ASSET, asset)            # IDOR → 403 (GIỮ NGUYÊN — không nới)
    return _ok(build_asset_label_data(asset))             # qr_url tuyệt đối, KHÔNG rỗng

@frappe.whitelist()                                       # GET batch
def get_asset_label_data_batch(assets=None):
    rbac.require("asset.print")                           # D6: gate PRINT (DocPerm print=1)
    names = frappe.parse_json(assets) if isinstance(assets, str) else (assets or [])
    if len(names) > _MAX_LABEL_BATCH:                     # Vòng 22 (BR-00-33): payload-DoS cap
        return _err(_(_ERR_LABEL_BATCH_TOO_LARGE), 413)  # SAU rbac, TRƯỚC exists/IDOR; no-leak
    for n in names:                                       # IDOR: 403 toàn call nếu ≥1 ngoài scope
        if frappe.db.exists(_DT_ASSET, n):
            assert_vendor_can_access(_DT_ASSET, n)        # KHÔNG leak asset nào thuộc/không scope
    return _ok(build_asset_label_data_batch(names))       # đúng thứ tự; missing → {name,error}

@frappe.whitelist(methods=["POST"])                       # POST — ghi sự kiện in
def mark_label_printed(assets=None):
    rbac.require("asset.print")                           # D6: in = quyền PRINT (label_printed là hệ quả)
    names = frappe.parse_json(assets) if isinstance(assets, str) else (assets or [])
    if len(names) > _MAX_LABEL_BATCH:                     # Vòng 22 (BR-00-33): cap TRƯỚC vòng write
        return _err(_(_ERR_LABEL_BATCH_TOO_LARGE), 413)  # chặn khuếch đại 2-record/asset/transaction
    for n in names:                                       # all-or-nothing: validate TRƯỚC khi ghi
        if not frappe.db.exists(_DT_ASSET, n):
            return _err(_(_ERR_ASSET_NOT_FOUND), 404)     # ≥1 không tồn tại → 404, KHÔNG ghi event
        assert_vendor_can_access(_DT_ASSET, n)            # IDOR → 403 toàn call
    for n in names:
        ensure_asset_qr_token(n)                          # đảm bảo có token để in được
        emit_label_printed(n)                             # 1 ALE label_printed + 1 audit / asset
    frappe.db.commit()
    return _ok({"printed": names, "event_count": len(names)})
```

> **Hằng SSoT (Vòng 22 / BR-00-33):** `services/imm00.py::_MAX_LABEL_BATCH = 200` — CẢ HAI endpoint trên `import` + tham chiếu HẰNG này (KHÔNG literal `200` lặp ở `api/imm00.py`). Message VI cố định `_ERR_LABEL_BATCH_TOO_LARGE = "Chỉ in tối đa 200 nhãn mỗi lần. Vui lòng chọn ít hơn."` (đặt cạnh `_ERR_ASSET_NOT_FOUND` trong `api/imm00.py`; nội suy `200` từ `_MAX_LABEL_BATCH` để KHÔNG drift — `f"Chỉ in tối đa {_MAX_LABEL_BATCH} nhãn mỗi lần. Vui lòng chọn ít hơn."`). `_err(_(...), 413)` → bucket HTTP 413 RIÊNG (KHÔNG nhầm 404/403/429), KHÔNG render raw `.message`, KHÔNG leak asset name. Biên: `len==_MAX_LABEL_BATCH` PASS, `+1` → 413, `0`/`None` → empty (KHÔNG 413, KHÔNG side-effect).

| Quy tắc (vòng B) | Lý do |
|---|---|
| Cả 3 endpoint gate `rbac.require("asset.print")` **đầu hàm** (D6 EXECUTED — đổi từ `asset.write`) | in nhãn = quyền PRINT (`label_printed`+audit là hệ quả của in). Cap `asset.print`→(AC Asset,"print") qua DocPerm (KHÔNG hardcode role); **DocPerm print=1 sẵn cho mọi role vận hành** → KTV/QL vật tư in được NGAY. **2 cap mới** `asset.print`+`asset.qr.rotate` → `CAP_SET_VERSION` v95.3388ee5629c1→**v97.c30c69b8974d**, FE `auth.ts` ĐÃ bump. Read-only `resolve_qr_token`/`get_asset_scan_info`/`get_asset` GIỮ `asset.read`. |
| `qr_url = _build_qr_url(token)` | URL tuyệt đối, host = base-URL **công khai cấu hình được** (site_config `assetcore_qr_base_url`), fallback `get_url` — KHÔNG hardcode (BR-00-30; §II.1.8-QRBASE). Tem quét được bằng camera điện thoại thật, KHÔNG lộ host nội bộ. |
| Token-less asset → `ensure_asset_qr_token` TRƯỚC khi build `qr_url` | KHÔNG trả `qr_url` rỗng (BR-00-28); emit `qr_generated` 1 lần (idempotent — KHÔNG phải print event) |
| GET `get_asset_label_data[_batch]` **KHÔNG emit `label_printed`/audit** | preview nhãn ≠ in nhãn — read-only về print event, tránh spam chain (D3/D4, giống resolve A2) |
| Batch: 1 truy vấn gộp + IN-clause cho enrich | **KHÔNG N+1**; thứ tự output = thứ tự input; missing → `{name,error:"AC-E001"}` (KHÔNG drop → giữ index FE) |
| `mark_label_printed`: 1 ALE `label_printed` + 1 audit / asset / lần in | mỗi lần in 1 event (đúng nghiệp vụ); gọi N lần = N×len event (KHÔNG dedup theo asset) |
| `mark_label_printed` all-or-nothing | validate PRINT gate + tồn tại + IDOR TẤT CẢ asset TRƯỚC khi ghi event nào → tránh audit chain lệch. Thứ tự: `require("asset.print")` → **cap-check (413)** → tồn-tại → IDOR → ghi |
| **Batch-size cap `_MAX_LABEL_BATCH=200` → 413** (Vòng 22 / BR-00-33) | per-request payload-DoS: `len(names) > _MAX_LABEL_BATCH` → `_err(_ERR_LABEL_BATCH_TOO_LARGE, 413)`. Hằng SSoT DUY NHẤT ở `services/imm00.py`; CẢ 2 endpoint (read batch + mark write) tham chiếu — KHÔNG literal lặp. Cap chạy **SAU `rbac.require("asset.print")`, TRƯỚC** vòng `exists`/IDOR → chỉ user đã-auth-print chạm ngưỡng (no-leak). 413 = bucket RIÊNG (KHÔNG nhầm 404/403/429), KHÔNG leak asset name. KHÁC rate-limit BR-00-29 (req/phút). `len==200` PASS, `+1` → 413, `0`/`None` → empty (KHÔNG side-effect). |
| Asset không tồn tại → **404 `AC-E001`** | leak-safe, KHÔNG 500, KHÔNG đoán id nội bộ |
| IDOR → `assert_vendor_can_access("AC Asset", name)` (TÁI DÙNG `scope.py:160`) | vendor ngoài scope → 403; batch/POST → 403 toàn call, KHÔNG partial, KHÔNG leak |

**Verify acceptance (chống dead-gate + regression):**
```python
from assetcore.services.shared.rbac import CAPABILITY_MAP, CAP_SET_VERSION
assert "asset.read" in CAPABILITY_MAP and "asset.write" in CAPABILITY_MAP  # A2 domain Asset
assert CAP_SET_VERSION == "v95.3388ee5629c1"  # B KHÔNG thêm cap → version KHÔNG đổi
# get_asset_label_data 1 asset → data.qr_url khớp r"^https?://.+/a/[A-Za-z0-9_-]{20,}$"
# get_asset_label_data_batch([a,b]) → len==2, order khớp input, mỗi entry có qr_url HOẶC error
# mark_label_printed([a]) gọi 2 lần → 2 ALE label_printed cho a (N lần = N event)
# RBAC B (đo QUA layer require, user THẬT): user có asset.read NHƯNG KHÔNG asset.write
#   → get_asset_label_data / mark_label_printed raise PermissionError (403);
#   user có asset.write → 200. KHÔNG test false-green (KHÔNG mock require).
# vendor ngoài scope → 403; asset không tồn tại → 404 (KHÔNG 500)
```

> **BR-00-28 (A3): `qr_url` không bao giờ rỗng.** Endpoint dữ liệu nhãn PHẢI đảm bảo asset có `qr_token` (qua `ensure_asset_qr_token` idempotent) trước khi build `qr_url`. Asset legacy/import lọt backfill D5 → sinh token on-demand (emit `qr_generated` 1 lần), KHÔNG trả `qr_url` rỗng → tem in ra luôn quét được.

#### II.1.8c — A6: Thông tin thiết bị mobile-first khi quét (`get_asset_scan_info`) — ADR-001 V7

> **Đề mục A6 (V7) — Self-Correction của A2.** A2 redirect màn quét sang `AssetDetail` (admin 926 dòng). A6 đổi đích sang màn info mobile-first MỚI + endpoint payload riêng. Envelope chi tiết ở [`05_API_Specification.md`](./05_API_Specification.md) §III.1 `get_asset_scan_info`. Vị trí code: **`api/imm00.py` + `services/imm00.py`** (cùng nhà `resolve_qr_token`). **KHÔNG cap/field/DocType mới** — tái dùng `asset.read` + `AC Asset.qr_token`/`next_pm_date`/`last_pm_date`.

**Import delta `api/imm00.py`** (thêm vào block `from assetcore.services.imm00 import (...)`): `build_asset_scan_info`. `rbac`, `assert_vendor_can_access`, `_ok`/`_err` đã import sẵn.

**Endpoint (`api/imm00.py`):**
```python
@frappe.whitelist()
@rate_limit(limit=AC_QR_RESOLVE_RATE_LIMIT, seconds=60, ip_based=True)  # Vòng 12 B — 429 TRƯỚC RBAC (BR-00-29, §II.1.8a-RL)
def get_asset_scan_info(token: str = "", name: str = ""):
    rbac.require("asset.read")                                  # 403 nếu thiếu cap — TRƯỚC mọi DB read
    asset_name = name
    if token:                                                   # luồng quét QR → resolve token→name
        asset_name = frappe.db.get_value("AC Asset", {"qr_token": token}, "name") or ""
    if not asset_name or not frappe.db.exists("AC Asset", asset_name):
        return _err(_("Không tìm thấy thiết bị"), 404)          # leak-safe: token sai = name sai = 404
    assert_vendor_can_access("AC Asset", asset_name)            # 403 IDOR — vendor ngoài scope
    return _ok(build_asset_scan_info(asset_name))
```

**Service (`services/imm00.py`) — `build_asset_scan_info(asset_name: str) -> dict` (READ-ONLY):**
- 1 `frappe.db.get_value("AC Asset", asset_name, [...], as_dict=True)` lấy: `name, asset_code, asset_name, lifecycle_status, device_model, location, next_pm_date`.
- Enrich `device_model_name` (1 `get_value` `IMM Device Model.model_name`) + `location_name` (1 `get_value` `AC Location.location_name`).
- `lifecycle_status_label = LIFECYCLE_STATUS_LABEL_VI.get(status, status)` (SSoT VI — xem §III.1c-6 dưới; fallback = mã gốc, KHÔNG để rỗng).
- **Bảo trì gần nhất — 1 truy vấn giới hạn (KHÔNG N+1, KHÔNG load timeline):**
  ```python
  ev = frappe.get_all("Asset Lifecycle Event",
      filters={"asset": asset_name,
               "event_type": ["in", ["pm_completed", "repair_completed", "calibration_passed"]]},
      fields=["event_type", "timestamp"],
      order_by="timestamp desc", limit_page_length=1)
  last_maintenance = None
  if ev:
      last_maintenance = {
          "event_type": ev[0]["event_type"],
          "event_type_label": LIFECYCLE_EVENT_LABEL_VI.get(ev[0]["event_type"], ev[0]["event_type"]),
          "date": str(getdate(ev[0]["timestamp"])),
      }
  ```
- **`pm_overdue: bool` — DERIVE SERVER-SIDE (Vòng 27 B / A6-hardening, BR-00-36).** Field thứ 9 thêm vào payload (sau `next_pm_date`/`recent_maintenance`). Cờ "Quá hạn bảo trì" tính 100% ở BE — xem block riêng §II.1.8c-PMOVERDUE dưới đây. **KHÔNG đổi 8 field hiện có.**
- **`next_calibration_date: str\|None` + `calibration_overdue: bool` — DERIVE SERVER-SIDE (Vòng 28 B / A6-hardening, BR-00-37 — chiều HIỆU CHUẨN).** ĐÚNG 2 field thứ 10–11 thêm vào payload (sau `pm_overdue`). `next_calibration_date` đọc field AC Asset **đã có** (`ac_asset.json:453`, chỉ thêm vào fields-list của `db.get_value`); cờ "Quá hạn hiệu chuẩn" tính 100% ở BE qua helper `_is_calibration_overdue` (mirror `_is_pm_overdue`) — xem block riêng §II.1.8e-CALOVERDUE dưới đây. **KHÔNG đổi 9 field FR-00-85.**
- Trả **whitelist tường minh** (chỉ các field A6) — KHÔNG `as_dict()` toàn doc rồi pop. **KHÔNG** trả `gross_purchase_amount`, `current_book_value`, `accumulated_depreciation`, audit chain, `supplier`/internal code, chi tiết `byt_reg_no`.
- **KHÔNG emit lifecycle/audit, KHÔNG gọi `ensure_asset_qr_token`** (read-only — đồng nhất quyết định A2/D4: mỗi lần quét KHÔNG sinh record).

| Quy tắc A6 | Lý do |
|---|---|
| Gate `rbac.require("asset.read")` TRƯỚC resolve token | guest không phân biệt được token tồn tại hay không (403 trước cả 404) |
| token sai/định-dạng-lạ và name sai đều → **404 generic** | leak-safe — KHÔNG phân biệt sai-định-dạng vs không-tồn-tại, KHÔNG 500 |
| `assert_vendor_can_access` SAU khi có name | IDOR — vendor resolve token asset ngoài scope → 403, KHÔNG leak |
| `lifecycle_status_label` từ SSoT VI, KHÔNG ghép chuỗi tại view | KHÔNG leak mã EN thô ra UI; 1 nguồn nhãn cho mọi surface |
| `last_maintenance`/`recent_maintenance` = ALE `ORDER BY timestamp DESC LIMIT 1` (filtered event_type) | bảo trì gần nhất, KHÔNG load toàn timeline (chống N+1) |
| `next_pm_date` đọc field denormalized trên `AC Asset` | KHÔNG truy PM Schedule/Work Order (đã denormalize ở IMM-08) |
| `pm_overdue` derive SERVER-SIDE (nowdate timezone-safe) | SSoT quá-hạn ở BE; FE KHÔNG so ngày bằng client clock (chống lệch timezone máy quét vs server) |
| `next_calibration_date` đọc field denormalized trên `AC Asset` (đã có) | KHÔNG truy Calibration Schedule/Work Order (đã denormalize ở IMM-11) |
| `calibration_overdue` derive SERVER-SIDE (nowdate timezone-safe) | SSoT quá-hạn hiệu chuẩn ở BE; FE KHÔNG so ngày client (Vòng 28 B / BR-00-37) |
| READ-ONLY — KHÔNG emit event/audit | chống spam audit chain mỗi lần quét (ADR D4) |

> **getdate/nowdate import:** `from frappe.utils import getdate, nowdate` — **đã có sẵn** ở `services/imm00.py:10` (KHÔNG cần thêm import; dùng lại để giữ timezone-safe).

##### II.1.8c-PMOVERDUE — A6-hardening (Vòng 27 B): cờ `pm_overdue` server-side — BR-00-36

> **Đề mục Vòng 27 B (hardening / compliance signal).** Màn THÔNG TIN thiết bị khi quét QR phải báo trực quan **PM quá hạn** cho kỹ thuật viên tại hiện trường. Quyết định kiến trúc: **derive 100% ở BE** (timezone-safe), payload thêm **DUY NHẤT 1 field** `pm_overdue: bool`. **KHÔNG endpoint/cap/schema/DocType mới** — `CAP_SET_VERSION` GIỮ `v95.3388ee5629c1`; KHÔNG đổi 8 field payload hiện có (`name, asset_code, asset_name, lifecycle_status, device_model_name, location_name, next_pm_date, recent_maintenance`).

**Vì sao BE là SSoT (KHÔNG để FE so ngày):** thiết bị quét bằng camera điện thoại của KTV/khách — múi giờ + đồng hồ máy client KHÔNG đáng tin (có thể lệch ngày). So sánh `next_pm_date < hôm-nay` bằng `Date()` của trình duyệt → cùng 1 thiết bị có thể "quá hạn" trên máy này, "chưa" trên máy kia. Vì vậy BE chốt cờ bằng `nowdate()` (giờ server, đồng nhất NĐ98 audit) → FE **chỉ render**, TUYỆT ĐỐI KHÔNG tự so ngày.

**Định nghĩa (bất biến BR-00-36):**

```
pm_overdue == True  ⟺  next_pm_date không rỗng (NOT NULL/"")
                       ∧ getdate(next_pm_date) < getdate(nowdate())     # STRICT < (hôm nay CHƯA quá hạn)
                       ∧ lifecycle_status ∉ {Out of Service, Decommissioned}   # = AssetStatus.BLOCKED_FOR_WO (ngừng dùng vĩnh viễn)
mọi nhánh khác  →  False
```

| Nhánh | next_pm_date | so ngày | lifecycle_status | pm_overdue |
|---|---|---|---|---|
| Quá hạn thật | `2026-05-01` | `< nowdate()` | `Active`/`Commissioned`/`Under …` | **True** |
| NULL / rỗng | `None` / `""` | — | bất kỳ | False |
| Hôm nay | `= nowdate()` | KHÔNG `<` (strict) | bất kỳ | False |
| Tương lai | `> nowdate()` | KHÔNG `<` | bất kỳ | False |
| Ngừng dùng | `< nowdate()` | `<` | `Out of Service` | False |
| Ngừng dùng | `< nowdate()` | `<` | `Decommissioned` | False |

> **"ngừng dùng vĩnh viễn" = `AssetStatus.BLOCKED_FOR_WO` = `("Out of Service", "Decommissioned")`** (SSoT `services/shared/constants.py:98`). KHÔNG có status "Retired" riêng trong enum AssetCore — acceptance "retired/decommissioned/ngừng-vĩnh-viễn" map về 2 mã canonical này. Asset ở các trạng thái này KHÔNG còn phải bảo trì → cờ quá-hạn gây nhiễu (false alarm) → ÉP False. (Asset `Under Maintenance`/`Under Repair`/`Calibrating`/`Out of Service`… — chỉ `Out of Service`+`Decommissioned` bị loại; tạm-ngừng-sử-dụng đã `next_pm_date=None` qua BR-00-04 nên rơi vào nhánh NULL→False.)

**Snippet derive (trong `build_asset_scan_info`, SAU khi đã có `row`, trước `return`):**

```python
from assetcore.services.shared.constants import AssetStatus   # AssetStatus.BLOCKED_FOR_WO

def _is_pm_overdue(next_pm_date, lifecycle_status: str) -> bool:
    """Cờ PM quá hạn — DERIVE SERVER-SIDE (timezone-safe, BR-00-36 / Vòng 27 B).

    True ⟺ next_pm_date không rỗng ∧ getdate(next_pm_date) < getdate(nowdate())
            ∧ lifecycle_status ∉ AssetStatus.BLOCKED_FOR_WO.
    Mọi nhánh khác (NULL, hôm-nay/tương-lai, ngừng-dùng) → False. SSoT quá-hạn ở BE;
    FE CHỈ render cờ — KHÔNG so ngày bằng client clock (chống lệch timezone).
    """
    if not next_pm_date:
        return False
    if lifecycle_status in AssetStatus.BLOCKED_FOR_WO:
        return False
    return getdate(next_pm_date) < getdate(nowdate())   # strict <: hôm nay CHƯA quá hạn
```

Trong payload `build_asset_scan_info`:
```python
    return {
        # … 8 field hiện có giữ NGUYÊN …
        "pm_overdue": _is_pm_overdue(row.get("next_pm_date"), row.get("lifecycle_status") or ""),
    }
```

| Quy tắc | Lý do |
|---|---|
| Dùng `getdate(nowdate())` (KHÔNG `datetime.now()`, KHÔNG client date) | nowdate = ngày theo timezone server (NĐ98 audit dùng cùng mốc); timezone-safe |
| STRICT `<` (KHÔNG `<=`) | đồng nhất precedent overdue trong module (`services/imm00.py:1227` "due == ref → CHƯA quá hạn") |
| Loại `BLOCKED_FOR_WO` bằng CONSTANT (KHÔNG literal) | chống status-string drift; SSoT enum 1 chỗ |
| Guard `asset_name` rỗng vẫn trả `None` (KHÔNG đổi) | hành vi cũ giữ nguyên — `pm_overdue` chỉ tồn tại khi có payload |
| READ-ONLY — KHÔNG emit event/audit khi đọc cờ | đồng nhất A2/A6/D4: quét KHÔNG sinh record |

**DoD BE (Vòng 27 B):** `bench --site miyano run-tests test_imm00` GREEN (baseline `TestAssetScanInfo` + class mới `pm_overdue`); `bench migrate` exit 0 (KHÔNG schema/patch); `CAP_SET_VERSION` GIỮ `v95.3388ee5629c1`. Test xem 07 §III.6.a-PMOVERDUE.

##### II.1.8e-CALOVERDUE — A6-hardening (Vòng 28 B): cờ `calibration_overdue` + `next_calibration_date` server-side — BR-00-37

> **Đề mục Vòng 28 B (hardening / compliance signal — chiều HIỆU CHUẨN).** Mở rộng CÙNG màn quét QR sang tín hiệu **hiệu chuẩn**. Quyết định kiến trúc: **mirror chính xác** §II.1.8c-PMOVERDUE (derive 100% ở BE, timezone-safe) cho hiệu chuẩn. Payload thêm **ĐÚNG 2 field**: `next_calibration_date: str\|None` + `calibration_overdue: bool`. **KHÔNG endpoint/cap/schema/DocType/field/enum/patch mới** — `next_calibration_date` là field AC Asset **đã có** (`ac_asset.json:453`, `fieldtype=Date`, `read_only`), CHỈ thêm vào fields-list của `frappe.db.get_value` + dict trả về; `CAP_SET_VERSION` GIỮ `v95.3388ee5629c1`; KHÔNG đổi 9 field FR-00-85 (`name, asset_code, asset_name, lifecycle_status, device_model_name, location_name, next_pm_date, recent_maintenance, pm_overdue`).

> **DISTINCT với Vòng 27 (non-duplicate guard):** Vòng 27 = chiều PM (`pm_overdue`/`next_pm_date`, nguồn `next_pm_date`); Vòng 28 = chiều HIỆU CHUẨN (`calibration_overdue`/`next_calibration_date`, nguồn `next_calibration_date`). Field + signal khác hẳn; helper `_is_calibration_overdue` SONG SONG `_is_pm_overdue` (KHÔNG tái dùng — nguồn ngày khác). Cùng logic STRICT `<`, cùng loại trừ `BLOCKED_FOR_WO`, cùng `nowdate()`.

**Vì sao BE là SSoT (KHÔNG để FE so ngày):** giống PM — camera điện thoại KTV/khách lệch múi giờ/đồng hồ ⟹ cùng thiết bị "quá hạn hiệu chuẩn" trên máy này, "chưa" trên máy kia nếu FE tự so. BE chốt cờ bằng `nowdate()` (giờ server, đồng nhất NĐ98 audit) → FE **chỉ render**.

**Định nghĩa (bất biến BR-00-37):**

```
calibration_overdue == True  ⟺  next_calibration_date không rỗng (NOT NULL/"")
                                ∧ getdate(next_calibration_date) < getdate(nowdate())   # STRICT < (hôm nay CHƯA quá hạn)
                                ∧ lifecycle_status ∉ {Out of Service, Decommissioned}    # = AssetStatus.BLOCKED_FOR_WO
mọi nhánh khác  →  False
```

| Nhánh | next_calibration_date | so ngày | lifecycle_status | calibration_overdue |
|---|---|---|---|---|
| Quá hạn thật | `2026-05-01` | `< nowdate()` | `Active`/`Commissioned`/`Under …` | **True** |
| NULL / rỗng | `None` / `""` | — | bất kỳ | False |
| Hôm nay | `= nowdate()` | KHÔNG `<` (strict) | bất kỳ | False |
| Tương lai | `> nowdate()` | KHÔNG `<` | bất kỳ | False |
| Ngừng dùng | `< nowdate()` | `<` | `Out of Service` | False |
| Ngừng dùng | `< nowdate()` | `<` | `Decommissioned` | False |

> Cùng quy ước "ngừng dùng vĩnh viễn" = `AssetStatus.BLOCKED_FOR_WO` = `("Out of Service", "Decommissioned")` (SSoT `services/shared/constants.py:98`) như §II.1.8c. Asset `Under Maintenance`/`Under Repair`/`Calibrating` vẫn tính (chỉ 2 mã ngừng-dùng-vĩnh-viễn bị loại).

**Snippet derive (helper SONG SONG `_is_pm_overdue`, cùng file `services/imm00.py`):**

```python
from assetcore.services.shared.constants import AssetStatus   # AssetStatus.BLOCKED_FOR_WO (đã import sẵn ở _is_pm_overdue)

def _is_calibration_overdue(next_calibration_date, lifecycle_status: str) -> bool:
    """Cờ HIỆU CHUẨN quá hạn — DERIVE SERVER-SIDE (timezone-safe, BR-00-37 / Vòng 28 B).

    True ⟺ next_calibration_date không rỗng ∧ getdate(next_calibration_date) < getdate(nowdate())
            ∧ lifecycle_status ∉ AssetStatus.BLOCKED_FOR_WO.
    Mọi nhánh khác (NULL, hôm-nay/tương-lai, ngừng-dùng) → False. SSoT quá-hạn ở BE;
    FE CHỈ render cờ — KHÔNG so ngày bằng client clock. Mirror _is_pm_overdue (chiều hiệu chuẩn).
    """
    if not next_calibration_date:
        return False
    if lifecycle_status in AssetStatus.BLOCKED_FOR_WO:
        return False
    return getdate(next_calibration_date) < getdate(nowdate())   # strict <: hôm nay CHƯA quá hạn
```

**Delta trong `build_asset_scan_info` (2 chỗ):**

1. Thêm `next_calibration_date` vào fields-list `frappe.db.get_value` (hiện: `["name", "asset_code", "asset_name", "lifecycle_status", "device_model", "location", "next_pm_date"]` → thêm `"next_calibration_date"`).
2. Thêm 2 key vào dict trả về (sau `pm_overdue`):
```python
    return {
        # … 9 field FR-00-85 giữ NGUYÊN (… "pm_overdue": _is_pm_overdue(...) ) …
        "next_calibration_date": row.get("next_calibration_date") or None,
        "calibration_overdue": _is_calibration_overdue(
            row.get("next_calibration_date"), row.get("lifecycle_status") or ""
        ),
    }
```

| Quy tắc | Lý do |
|---|---|
| Dùng `getdate(nowdate())` (KHÔNG `datetime.now()`, KHÔNG client date) | timezone-safe; đồng nhất §II.1.8c + NĐ98 audit |
| STRICT `<` (KHÔNG `<=`) | đồng nhất precedent overdue PM (hôm nay CHƯA quá hạn) |
| Loại `BLOCKED_FOR_WO` bằng CONSTANT (KHÔNG literal) | chống status-string drift; SSoT enum 1 chỗ |
| `next_calibration_date` rỗng → `None` (chuẩn hoá `""`→`None`) | parity với `next_pm_date`; FE hiển thị "Chưa lên lịch" |
| Guard `asset_name` rỗng vẫn trả `None` (KHÔNG đổi) | hành vi cũ giữ — 2 field mới chỉ tồn tại khi có payload |
| READ-ONLY — KHÔNG emit event/audit khi đọc cờ | đồng nhất A2/A6/D4: quét KHÔNG sinh record |

**DoD BE (Vòng 28 B):** `bench --site miyano run-tests test_imm00` GREEN (baseline `TestAssetScanInfo` + `TestAssetScanInfoPmOverdue` + class mới `TestAssetScanInfoCalibrationOverdue`, RED-first); `bench migrate` exit 0 (KHÔNG schema/patch — `next_calibration_date` đã tồn tại); `CAP_SET_VERSION` GIỮ `v95.3388ee5629c1`. Test xem 07 §III.6.b-CALOVERDUE.

#### II.1.8d — B-2: Sinh-lại (rotate) `qr_token` (`regenerate_asset_qr_token`) — ADR-001 D1/D3/D4

> **Đề mục B item 2 (hardening).** Vô hiệu hoá QR bị lộ + cấp token MỚI. **KHÁC `ensure_asset_qr_token`** (idempotent if-empty — KHÔNG overwrite token đang có). Envelope chi tiết ở [`05_API_Specification.md`](./05_API_Specification.md) §III.1 `regenerate_asset_qr_token`. Vị trí code: **`api/imm00.py` + `services/imm00.py`** (cùng nhà `resolve_qr_token`/`ensure_asset_qr_token`). **KHÔNG cap/field/DocType mới** (tái dùng `asset.write` + `AC Asset.qr_token`); schema-delta DUY NHẤT = **+1 option `qr_regenerated`** vào `Asset Lifecycle Event.event_type` (xem §II.6 / §II.1d-B2).

**Import delta `api/imm00.py`** (thêm vào block `from assetcore.services.imm00 import (...)`): `regenerate_asset_qr_token as _svc_regenerate_qr_token`. `rbac`, `assert_vendor_can_access`, `_ok`/`_err`, `_ERR_ASSET_NOT_FOUND`, `_DT_ASSET`, `ServiceError` đã import sẵn.

**Service (`services/imm00.py`) — thêm cạnh `emit_label_printed`:**
- `QR_REGENERATED_EVENT = "qr_regenerated"` (cạnh `LABEL_PRINTED_EVENT` line 100/233).
- `emit_qr_regenerated(asset_name, actor=None) -> None`: 1 `create_lifecycle_event(event_type=QR_REGENERATED_EVENT, root_doctype="AC Asset", root_record=asset_name, from_status="", to_status="", notes="Sinh lại mã QR cấp tài sản — vô hiệu hoá nhãn QR cũ.")` + 1 `log_audit_event(event_type="System", ref_doctype="AC Asset", ref_name=asset_name, change_summary="Sinh lại (rotate) mã QR cấp tài sản; nhãn QR cũ bị vô hiệu hoá.")`. **KHÔNG nuốt lỗi** (≠ `emit_qr_generated` best-effort — đây là sự kiện bảo mật, audit BẮT BUỘC ghi được; lỗi → raise). **TUYỆT ĐỐI KHÔNG đưa token thô (cũ/mới) vào `notes`/`change_summary`** (token = khoá tra cứu mờ; log token = leak deep-link).
- `regenerate_asset_qr_token(asset_name: str, actor=None) -> dict`:
  ```python
  def regenerate_asset_qr_token(asset_name: str, actor: str | None = None) -> dict:
      """SERVICE (B-2): rotate qr_token — overwrite token cũ bằng token MỚI.

      KHÁC ensure_asset_qr_token (idempotent if-empty). LUÔN sinh token mới + GHI ĐÈ
      (vô hiệu hoá nhãn QR đã in). Gate quyền + IDOR do API tier (require asset.write
      + assert_vendor_can_access) — service chỉ rotate + emit.
      """
      old = frappe.db.get_value(_DOCTYPE_ASSET, asset_name, "qr_token") or ""
      new = generate_unique_qr_token(exclude=old)        # SSoT collision-safe (§II.1.8-COLL):
                                                         # != old (rotate đổi) VÀ != qr_token asset khác (UNIQUE)
      frappe.db.set_value(_DOCTYPE_ASSET, asset_name, "qr_token", new,
                          update_modified=False)         # overwrite, KHÔNG bump modified
      emit_qr_regenerated(asset_name, actor=actor)       # KHÔNG nuốt lỗi
      return {"name": asset_name, "qr_url": frappe.utils.get_url(f"/a/{new}")}
  ```
  - **Collision-safe (Vòng 17 B):** delegate **CÙNG** SSoT `generate_unique_qr_token(exclude=old)` (§II.1.8-COLL) — pre-write check `frappe.db.exists` đảm bảo `new` KHÔNG trùng token asset khác (UNIQUE) **TRƯỚC** set_value → KHÔNG IntegrityError thô. `exclude=old` guard thêm token cũ (rotate phải đổi). BỎ vòng `while new == old` cũ (chỉ guard token cũ, hở token asset khác). Khi nâng cấp `_build_qr_url` (D2.1) → dòng `qr_url` dùng `_build_qr_url(new)`.
  - **Token cũ chết:** lookup `resolve_qr_token` qua field `qr_token` đã đổi → `resolve_qr_token(old)` → `None` → 404; `resolve_qr_token(new)` → asset đúng (acceptance).

**Endpoint (`api/imm00.py`) — thêm cạnh `mark_label_printed`:**
```python
@frappe.whitelist(methods=["POST"])
@rate_limit(limit=AC_QR_REGEN_RATE_LIMIT, seconds=60, ip_based=True)  # Vòng 27 B — 429 TRƯỚC rbac.require (BR-00-38); bucket RIÊNG (cmd), ngưỡng RIÊNG (KHÔNG dùng chung resolve=30)
def regenerate_asset_qr_token(asset: str = ""):
    # 0. @rate_limit (BR-00-38): vượt AC_QR_REGEN_RATE_LIMIT/60s/IP → RateLimitExceededError (429)
    #    TRƯỚC thân hàm ⇒ KHÔNG side-effect (0 token mới, 0 ALE qr_regenerated, 0 audit), no-leak.
    rbac.require("asset.qr.rotate")                      # D6: rotate=GHI →(AC Asset,write); 403 nếu chỉ-đọc/chỉ-print/Guest
    if not asset or not frappe.db.exists(_DT_ASSET, asset):
        return _err(_(_ERR_ASSET_NOT_FOUND), 404)        # 404 leak-safe, KHÔNG 500
    try:
        assert_vendor_can_access(_DT_ASSET, asset)        # 403 IDOR — vendor ngoài scope
    except ServiceError as e:
        return _err(e.message, e.code)
    result = _svc_regenerate_qr_token(asset)
    frappe.db.commit()
    return _ok(result)                                   # {name, qr_url} — qr_url deep-link MỚI
```

> **Hằng RIÊNG (BR-00-38) — đặt cạnh `AC_QR_RESOLVE_RATE_LIMIT` đầu `api/imm00.py`:** `AC_QR_REGEN_RATE_LIMIT = 10` (10 req/60s/IP — rotate hiếm hơn quét, ngưỡng THẤP hơn 30 do BA chốt; **KHÔNG** tái dùng `AC_QR_RESOLVE_RATE_LIMIT`). `from frappe.rate_limiter import rate_limit` đã import sẵn (Vòng 12). Bucket RIÊNG: cache key frappe gồm `frappe.form_dict.cmd` ⟹ counter rotate TÁCH BIỆT resolve/scan.

| Quy tắc B-2 | Lý do |
|---|---|
| **`@rate_limit(AC_QR_REGEN_RATE_LIMIT/60s/IP)` ĐẶT NGOÀI thân hàm, sát `def` (Vòng 27 B / BR-00-38)** | đóng bất đối xứng read-throttled/write-rotate-unthrottled. Decorator bọc ngoài → 429 chạy TRƯỚC `rbac.require("asset.qr.rotate")` ⇒ vượt ngưỡng → KHÔNG side-effect (0 token mới, 0 ALE, 0 audit), no-leak. Hằng + bucket RIÊNG (KHÔNG chung resolve=30). Thứ tự: `@frappe.whitelist(methods=["POST"])` (trên) → `@rate_limit(...)` (sát `def`). |
| Gate `rbac.require("asset.qr.rotate")` ĐẦU HÀM (D6 EXECUTED — đổi từ `asset.write`) | rotate = overwrite token + emit event/audit ⇒ GHI rõ nghĩa. Cap `asset.qr.rotate`→(AC Asset,"write") qua DocPerm (KHÔNG hardcode role — chống dead-gate); KHÔNG đủ với `asset.print` (in ≠ rotate). `CAP_SET_VERSION` v95.3388ee5629c1→**v97.c30c69b8974d** (cap mới), FE `auth.ts` ĐÃ bump. |
| Token mới qua SSoT `generate_unique_qr_token(exclude=old)` (Vòng 17 B) | enumeration-safe (CSPRNG, không tuần tự); guard CẢ token cũ (`exclude=old` — rotate phải đổi) CẢ token asset khác (pre-write `frappe.db.exists` → UNIQUE-safe, KHÔNG 500). Thay vòng `while new == old` cũ (guard-một-nửa). |
| GHI ĐÈ `qr_token` `update_modified=False` | KHÁC `ensure_asset_qr_token` (chỉ set if-empty). Rotate LUÔN overwrite → nhãn QR cũ chết. KHÔNG bump `modified` (metadata kỹ thuật, không phải sửa nghiệp vụ — tránh nhiễu "Sửa lần cuối"). |
| `emit_qr_regenerated` KHÔNG nuốt lỗi (≠ `emit_qr_generated`) | sự kiện bảo mật (ứng phó lộ token) → audit BẮT BUỘC ghi được; lỗi ghi event → raise → 422/500, KHÔNG để asset đổi token mà thiếu audit (NĐ98 truy xuất). |
| `change_summary`/`notes` KHÔNG chứa token thô | token = khoá tra cứu mờ; ghi token vào audit chain = leak deep-link (audit có thể export/đọc rộng hơn). Chỉ ghi hành động "rotate/vô hiệu hoá". |
| `assert_vendor_can_access` TRƯỚC rotate | IDOR — vendor KHÔNG rotate được asset ngoài scope → 403. Đồng nhất leak-safe với `resolve_qr_token`. |
| Thứ tự gate: **`@rate_limit` (429)** → `require("asset.qr.rotate")` (403) → tồn-tại (404) → IDOR (403) → rotate | **429 chạy NGOÀI/TRƯỚC thân hàm** (BR-00-38) ⇒ vượt ngưỡng → 0 side-effect (KHÔNG dò được, KHÔNG ghi). Sau RL: gate ROTATE ĐẦU TIÊN → user chỉ-đọc/chỉ-print KHÔNG dò được asset nào tồn tại; all-or-nothing (commit sau khi rotate+emit OK). |
| `qr_url` trả về = deep-link MỚI; nhãn (A3 `get_asset_label_data`) tự phản ánh token mới | FE refetch asset → preview/print dùng deep-link mới (acceptance). KHÔNG cần đụng A3 (đọc `qr_token` field hiện tại). KHÔNG trả token thô trong envelope. |

> **BR-00-29 (B-2): Rotate vô hiệu hoá nhãn cũ.** `regenerate_asset_qr_token` PHẢI sinh token KHÁC token cũ + GHI ĐÈ (KHÔNG idempotent). Sau rotate: `resolve_qr_token(old_token)` → 404 (nhãn đã in chết), `resolve_qr_token(new_token)` → asset đúng. Mỗi rotate ghi đúng **1** ALE `qr_regenerated` + **1** audit (no raw token). Phân biệt rõ với BR-00-28 (`ensure_asset_qr_token` idempotent if-empty — KHÔNG overwrite).

> **BR-00-38 (Vòng 27 B): Rate-limit rotate.** `regenerate_asset_qr_token` mang `@rate_limit(limit=AC_QR_REGEN_RATE_LIMIT=10, seconds=60, ip_based=True)` — hằng + bucket RIÊNG (KHÔNG chung resolve=30). Vượt ngưỡng/60s/IP → `RateLimitExceededError` (429) NGOÀI/TRƯỚC thân hàm ⇒ **0 side-effect** (KHÔNG token mới, KHÔNG ALE `qr_regenerated`, KHÔNG audit), no-leak. Happy-path ≤10/60s rotate vẫn 200 `{name, qr_url}` no-raw-token (regression B-2). Đóng bất đối xứng read-throttled (BR-00-29) / write-rotate-unthrottled. FE cặp: FR-00-87/88 (429→RATE_LIMITED + message VI). Test: `TestQrRegenerateRateLimit` (07 §III.6.d-ROTATERL).

### II.1d-B2. Schema-delta của B item 2 (regenerate)

| DocType | Field | Thay đổi | Migration |
|---|---|---|---|
| `Asset Lifecycle Event` | `event_type` (Select) | **THÊM** option `qr_regenerated` vào cuối chuỗi options (`...\nqr_generated\nlabel_printed\nqr_regenerated`) | `bench migrate` (Select option add — KHÔNG đổi cột DB, KHÔNG destructive) |
| `IMM Audit Trail` | `event_type` (Select) | **KHÔNG đổi** — dùng `System` đã có sẵn | Không |

> **KHÔNG field mới trên `AC Asset`** (tái dùng `qr_token` đã có từ A1). **KHÔNG cap mới** (`CAP_SET_VERSION` GIỮ `v95.3388ee5629c1`). **KHÔNG patch backfill** (rotate là on-demand, không backfill). Migration B-2 = duy nhất Select-option add + deploy code.

Khi `to_status = Decommissioned`, nhánh cuối `transition_asset_status` chạy **2** hành động chốt sổ:
1. `_suspend_all_schedules(asset_name)` — set `is_pm_required=0`, `is_calibration_required=0`, `next_pm_date=None`, `next_calibration_date=None` (BR-00-04, lịch PM/Hiệu chuẩn).
2. `_cancel_pending_depreciation_on_decommission(asset_name)` — **MỚI (RC-07, Vòng 8 — BR-00-24):** hủy mọi kỳ khấu hao `Pending` còn lại của asset. Xem §II.1c.

> **RC-07 — vì sao cần.** Trước Vòng 8, `transition_asset_status(Decommissioned)` CHỈ gọi `_suspend_all_schedules` — hàm này KHÔNG đụng child table `AC Asset Depreciation Schedule`. Asset thanh lý **mid-life** (còn kỳ chưa chạy) bị kẹt `Pending` vĩnh viễn: `run_due_depreciation` đã lọc `lifecycle_status NOT IN ('Decommissioned','Out of Service')` (`depreciation.py:416`) nên kỳ Pending KHÔNG bao giờ chạy NHƯNG cũng KHÔNG bao giờ đóng → "phantom overdue" treo mãi trong KPI/drill (`pending_periods > 0`). Helper mới chốt sổ tại thời điểm thanh lý.

### II.1c. `_cancel_pending_depreciation_on_decommission(asset_name)` — BR-00-24 (RC-07)

> **BE prerequisites trong `services/imm00.py`** (hiện chưa có — phải thêm khi implement):
> - import `flt`: đổi `from frappe.utils import add_days, nowdate` → `from frappe.utils import add_days, flt, nowdate`.
> - định nghĩa hằng cạnh `_DOCTYPE_ASSET`: `_DT_DEPR_SCHED = "AC Asset Depreciation Schedule"`.
> - `create_lifecycle_event` / `log_audit_event` đã re-export sẵn trong cùng file (dùng trực tiếp).

```python
def _cancel_pending_depreciation_on_decommission(asset_name: str) -> int:
    """Hủy mọi kỳ khấu hao Pending còn lại khi asset bị thanh lý (BR-00-24).

    - Chỉ đụng dòng status='Pending' → 'Cancelled'. Dòng 'Executed' BẤT BIẾN.
    - KHÔNG ghi lại accumulated_depreciation / current_book_value (chốt tại giá trị
      hiện hành — lũy kế đã-Executed không đổi).
    - Idempotent: 0 Pending → return 0, không event/audit.
    - cancelled_count >= 1 → 1 ALE 'depreciation_stopped' + 1 IMM Audit Trail 'System'
      (best-effort try/except; lỗi audit KHÔNG vỡ transition).

    Returns: số kỳ Pending đã chuyển sang Cancelled.
    """
    pending = frappe.get_all(
        _DT_DEPR_SCHED,                       # "AC Asset Depreciation Schedule"
        filters={"parent": asset_name, "parenttype": _DOCTYPE_ASSET,
                 "status": "Pending"},
        fields=["name"], limit_page_length=0,
    )
    if not pending:
        return 0
    for row in pending:
        frappe.db.set_value(_DT_DEPR_SCHED, row["name"], "status", "Cancelled",
                            update_modified=False)
    cancelled = len(pending)

    # Audit/lifecycle — best-effort (CLAUDE.md §5). Lỗi KHÔNG vỡ transition.
    try:
        book = flt(frappe.db.get_value(_DOCTYPE_ASSET, asset_name,
                                       "current_book_value") or 0)
        notes = (f"Thanh lý tài sản: hủy {cancelled} kỳ khấu hao chưa chạy "
                 f"(Pending → Cancelled). Giá trị còn lại chốt sổ: {book:,.0f} VND.")
        create_lifecycle_event(
            asset=asset_name, event_type="depreciation_stopped",
            actor=frappe.session.user, from_status="", to_status="",
            root_doctype=_DOCTYPE_ASSET, root_record=asset_name, notes=notes,
        )
        log_audit_event(
            asset=asset_name, event_type="System", actor=frappe.session.user,
            ref_doctype=_DOCTYPE_ASSET, ref_name=asset_name,
            change_summary=notes,
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(),
                         "_cancel_pending_depreciation_on_decommission audit failed")
    return cancelled
```

**INVARIANT:**
- Hủy chạy **SAU** khi `lifecycle_status` đã set `Decommissioned` và **SAU** event `decommissioned` (state-change) — event `depreciation_stopped` SONG SONG, KHÔNG thay thế.
- Dòng `Executed` không nằm trong filter `status='Pending'` ⇒ bất biến tuyệt đối.
- `event_type='depreciation_stopped'` PHẢI có trong Select options của `Asset Lifecycle Event` (schema-delta — xem §II.1d). `event_type='System'` của IMM Audit Trail đã có sẵn.

### II.1d. Schema-delta DUY NHẤT của Vòng 8

| DocType | Field | Thay đổi | Migrate? |
|---|---|---|---|
| `Asset Lifecycle Event` | `event_type` (Select) | **THÊM** option `depreciation_stopped` vào cuối chuỗi options hiện hữu (`...\ndepreciated\ndepreciation_rules_inherited\ndepreciation_stopped`) | `bench migrate` (Select option add — không đổi cột DB) |
| `AC Asset Depreciation Schedule` | `status` (Select) | **KHÔNG đổi** — option `Cancelled` đã có sẵn (`Pending\nExecuted\nCancelled`) | Không |
| `IMM Audit Trail` | `event_type` (Select) | **KHÔNG đổi** — dùng `System` đã có sẵn | Không |

Downtime log (AC Asset Downtime Log) tự động open/close qua `_sync_downtime_log()`: các status `Under Maintenance, Under Repair, Calibrating, Out of Service` là downtime states; chuyển vào → open log, chuyển ra → close log.

### II.1e. Out of Service ↔ Active: PAUSE + RESCHEDULE khấu hao — BR-00-25 (RC-08, Vòng 9)

> **Ghi chú naming-drift (Self-Correction phụ).** Doc §II.1c gọi helper decommission là `_cancel_pending_depreciation_on_decommission`, **NHƯNG code thật** (`services/imm00.py:246`) tên là **`_cancel_pending_depreciation`** + audit tách ra `_record_depreciation_stopped` (gọi trong nhánh Decommissioned của `transition_asset_status`). Vòng 9 dùng **tên hàm thật của code** cho 2 helper mới để BE wire chính xác, KHÔNG đổi tên hàm cũ.

> **RC-08 — vì sao cần.** Trước Vòng 9, `Out of Service` chỉ "pause-không-dời": executor lọc `lifecycle_status NOT IN ('Decommissioned','Out of Service')` (`depreciation.py:422`) nên trong window OoS không kỳ nào bị trích (đúng). NHƯNG khi `Out of Service → Active`, các kỳ Pending có `scheduled_date < restore_date` (quá hạn trong lúc OoS) lập tức "đến hạn" → lần `run_due_depreciation(today)` kế tiếp **trích bù 1 lần toàn bộ N kỳ idle** (back-dated catch-up) → `current_book_value` tụt đột ngột. Vi phạm nguyên tắc: tài sản tạm ngừng KHÔNG trích KH trong kỳ ngừng, phải DỜI lịch (kéo dài vòng đời) tương ứng số ngày ngừng. Fix: tại transition về `Active` từ `Out of Service`, DỜI `scheduled_date` của mọi kỳ Pending thêm `oos_days` → mọi kỳ idle đẩy sang tương lai → executor KHÔNG còn back-dated catch-up.

**Wire vào `transition_asset_status` (2 nhánh mới, sau khối state-change/audit/downtime đã có):**

```python
# ... cuối transition_asset_status, sau _sync_downtime_log(...) ...

    if to_status == _STATUS_DECOMMISSIONED:
        _suspend_all_schedules(asset_name)
        cancelled = _cancel_pending_depreciation(asset_name)        # đã có (BR-00-24)
        if cancelled >= 1:
            _record_depreciation_stopped(asset_name, cancelled, actor=actor)

    # ── BR-00-25 (RC-08): PAUSE khi vào OoS ─────────────────────────────────
    elif to_status == _STATUS_OUT_OF_SERVICE:
        _pause_depreciation_on_oos(asset_name, actor=actor)         # best-effort

    # ── BR-00-25 (RC-08): RESCHEDULE khi khôi phục Out of Service → Active ───
    elif to_status == _STATUS_ACTIVE and prev_status == _STATUS_OUT_OF_SERVICE:
        _reschedule_pending_depreciation_on_restore(asset_name, actor=actor)
```

> **INVARIANT wire:** dùng `prev_status` (đã đọc đầu hàm `transition_asset_status`) để phân biệt "Active từ OoS" (dời lịch) với "Active từ Under Repair / Calibrating / Commissioned" (KHÔNG dời — các đường đó không pause khấu hao). Guard same-status `prev_status == to_status → return` đầu hàm đã chặn `Active→Active` / `OoS→OoS` no-op (idempotent — không dời kép, không pause kép).

**Helper 1 — `_resolve_oos_start_date` (SoT mốc bắt đầu OoS, FR-00-67):**

```python
_DT_DOWNTIME_LOG = "AC Asset Downtime Log"
_DT_LIFECYCLE_EVENT = "Asset Lifecycle Event"

def _resolve_oos_start_date(asset_name: str):
    """SoT mốc 'asset bắt đầu Out of Service' (BR-00-25 / FR-00-67).

    Thứ tự ưu tiên (an toàn, KHÔNG raise):
      1. start_time của AC Asset Downtime Log Out-of-Service GẦN NHẤT của asset
         (reason='Hỏng hóc' = reason map cho OoS — _DOWNTIME_REASON_MAP[OUT_OF_SERVICE]).
         **KHÔNG lọc is_open=1** — xem ORDERING dưới: tại nhánh restore, log OoS đã bị
         `_sync_downtime_log` ĐÓNG (is_open=0) TRƯỚC khi reschedule chạy. Lấy log mới
         nhất theo start_time (bất kể đóng/mở) → vẫn đúng mốc bắt đầu ngừng.
      2. fallback: creation của Asset Lifecycle Event event_type='out_of_service'
         GẦN NHẤT của asset (khi không có downtime log OoS nào).
    Cả 2 thiếu → trả None (caller no-op, KHÔNG raise).
    Trả về `date` (getdate) hoặc None.
    """
    row = frappe.get_all(
        _DT_DOWNTIME_LOG,
        filters={"asset": asset_name,
                 "reason": _DOWNTIME_REASON_MAP[_STATUS_OUT_OF_SERVICE]},  # 'Hỏng hóc'
        fields=["start_time"], order_by="start_time desc", limit=1,
    )
    if row and row[0].get("start_time"):
        return getdate(row[0]["start_time"])

    ev = frappe.get_all(
        _DT_LIFECYCLE_EVENT,
        filters={"asset": asset_name, "event_type": "out_of_service"},
        fields=["creation"], order_by="creation desc", limit=1,
    )
    if ev and ev[0].get("creation"):
        return getdate(ev[0]["creation"])
    return None
```

> **Lưu ý import:** thêm `getdate` vào `from frappe.utils import ...` của `services/imm00.py` (hiện có `add_days, flt, nowdate`). `_DT_LIFECYCLE_EVENT`/`_DT_DOWNTIME_LOG` đặt cạnh `_DT_DEPR_SCHED`. `_DOWNTIME_REASON_MAP` + `_STATUS_OUT_OF_SERVICE` đã có sẵn trong file.

> **⚠️ ORDERING (CHÍ MẠNG — BA chỉ rõ để BE wire đúng).** Trong `transition_asset_status`, `_sync_downtime_log(...)` chạy **TRƯỚC** khối trailing (nhánh Decommissioned/OoS/restore). Khi `Out of Service → Active`, `_sync_downtime_log` thấy `was_down=True` → gọi `_close_open_downtime_log(asset)` → set `is_open=0` cho log OoS **TRƯỚC KHI** `_reschedule_pending_depreciation_on_restore` chạy. ⟹ Nếu `_resolve_oos_start_date` lọc `is_open=1` sẽ **KHÔNG tìm thấy** log (đã đóng) → luôn rơi vào fallback ALE. Để priority-1 (downtime log) hoạt động đúng, helper **KHÔNG lọc `is_open`** mà lấy log OoS mới nhất theo `start_time` (đóng hay mở đều được — `start_time` không đổi khi đóng log). Fallback ALE vẫn giữ cho trường hợp downtime log bị tắt/không có. **TUYỆT ĐỐI KHÔNG** đảo thứ tự gọi (đặt reschedule trước `_sync_downtime_log`) — sẽ phá vỡ semantics đóng/mở downtime hiện hữu.

**Helper 2 — `_pause_depreciation_on_oos` (PAUSE audit, FR-00-64, best-effort):**

```python
def _pause_depreciation_on_oos(asset_name: str, actor: str | None = None) -> int:
    """Best-effort: đánh dấu khấu hao TẠM DỪNG khi asset vào Out of Service.

    KHÔNG đụng dữ liệu khấu hao (PAUSE thực thi bởi filter executor — FR-00-63).
    Chỉ ghi 1 ALE 'out_of_service' note 'depreciation paused' + số kỳ Pending bị
    tạm dừng (audit rõ ràng). 0 kỳ Pending → no-op (không event rác). Lỗi audit
    KHÔNG vỡ transition (status đã 'Out of Service' trước khi gọi).

    Returns: số kỳ Pending đang bị tạm dừng (để test/assert).
    """
    pending = frappe.db.count(_DT_DEPR_SCHED, {
        "parent": asset_name, "parenttype": _DOCTYPE_ASSET, "status": "Pending",
    })
    if not pending:
        return 0
    try:
        create_lifecycle_event(
            asset=asset_name, event_type="out_of_service",
            actor=actor or frappe.session.user, from_status="", to_status="",
            root_doctype=_DOCTYPE_ASSET, root_record=asset_name,
            notes=(f"depreciation paused — tạm dừng trích khấu hao trong thời gian "
                   f"tạm ngừng sử dụng ({pending} kỳ Pending chờ dời lịch khi khôi phục)."),
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(),
                         "_pause_depreciation_on_oos audit failed")
    return pending
```

**Helper 3 — `_reschedule_pending_depreciation_on_restore` (RESCHEDULE, FR-00-65/66/68):**

```python
def _reschedule_pending_depreciation_on_restore(
    asset_name: str, actor: str | None = None,
) -> dict:
    """DỜI scheduled_date mọi kỳ Pending += oos_days khi Out of Service → Active.

    Diệt phantom catch-up (BR-00-25 / FR-00-65): mọi kỳ Pending quá hạn trong lúc
    OoS được đẩy sang tương lai (cũ + oos_days) → executor KHÔNG trích bù 1 lần.

    INVARIANT:
      - CHỈ dời kỳ status='Pending'. Executed/Cancelled BẤT BIẾN.
      - GIỮ NGUYÊN depreciation_amount, period_number, accumulated_amount,
        remaining_value, số kỳ. Chỉ đổi scheduled_date.
      - oos_days = restore_date(today) − oos_start_date (số ngày nguyên).
      - oos_start_date None (FR-00-67) HOẶC oos_days <= 0 → no-op (rescheduled=0).
        KHÔNG raise.
      - Idempotent (GUARD chính = transition same-status): helper CHỈ chạy trong
        nhánh transition `Active←Out of Service`, MỘT lần/khôi phục. Gọi lại
        `transition_asset_status(asset,'Active')` khi asset đã Active → guard đầu hàm
        `prev_status == to_status → return` chặn (KHÔNG vào nhánh reschedule) ⇒ KHÔNG
        dời kép. ⟹ Helper KHÔNG @frappe.whitelist (không expose standalone) để tránh
        gọi trực tiếp lần 2 (với mốc OoS cũ vẫn còn) gây dời kép. Test idempotent =
        re-call transition Active→Active (no-op qua guard prev==to), KHÔNG gọi helper
        trực tiếp 2 lần.

    Returns: {"rescheduled": N, "oos_days": int}
    """
    oos_start = _resolve_oos_start_date(asset_name)
    if oos_start is None:
        return {"rescheduled": 0, "oos_days": 0}

    oos_days = (getdate(nowdate()) - oos_start).days
    if oos_days <= 0:                       # đồng hồ lệch / cùng ngày → no-op
        return {"rescheduled": 0, "oos_days": 0}

    pending = frappe.get_all(
        _DT_DEPR_SCHED,
        filters={"parent": asset_name, "parenttype": _DOCTYPE_ASSET,
                 "status": "Pending"},
        fields=["name", "scheduled_date"], limit_page_length=0,
    )
    if not pending:
        return {"rescheduled": 0, "oos_days": oos_days}

    for row in pending:
        new_date = add_days(getdate(row["scheduled_date"]), oos_days)
        frappe.db.set_value(_DT_DEPR_SCHED, row["name"], "scheduled_date",
                            new_date, update_modified=False)
    rescheduled = len(pending)

    # Audit — best-effort (FR-00-68). Lỗi KHÔNG vỡ transition.
    # ⚠️ RC-09 (Vòng 14): KHÔNG còn create_lifecycle_event('restored') ở đây —
    # ALE 'restored' DUY NHẤT do transition_asset_status emit (single-emit SoT).
    # Helper CHỈ giữ log_audit_event 'State Change' với note chi-tiết-dời-kỳ để
    # audit trail vẫn truy được số kỳ đã dời + oos_days (chi tiết khấu hao).
    try:
        notes = (f"Khôi phục sau tạm ngừng sử dụng: dời {rescheduled} kỳ khấu hao "
                 f"Pending thêm {oos_days} ngày (oos_days={oos_days}). Không trích bù "
                 f"kỳ ngừng — vòng đời khấu hao kéo dài tương ứng.")
        log_audit_event(
            asset=asset_name, event_type="State Change",
            actor=actor or frappe.session.user,
            ref_doctype=_DOCTYPE_ASSET, ref_name=asset_name, change_summary=notes,
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(),
                         "_reschedule_pending_depreciation_on_restore audit failed")
    return {"rescheduled": rescheduled, "oos_days": oos_days}
```

**INVARIANT tổng (BR-00-25):**

| # | Bất biến | Đo |
|---|---|---|
| INV-DEP-OOS-1 | PAUSE: `run_due_depreciation` khi asset OoS → `executed_rows=0` cho asset đó; `accumulated_depreciation`/`current_book_value` bất biến (chạy 1+ lần) | filter `lifecycle_status NOT IN (...)` (đã có) |
| INV-DEP-OOS-2 | NO PHANTOM CATCH-UP: sau restore + `run_due_depreciation(today)`, `delta_accumulated == 0` cho kỳ rơi trong khoảng OoS | dời lịch đẩy mọi kỳ Pending > today |
| INV-DEP-OOS-3 | RESCHEDULE: `count(Pending) trước==sau`; `sum(depreciation_amount Pending) trước==sau`; mỗi `scheduled_date += oos_days` | so 2 snapshot Pending |
| INV-DEP-OOS-4 | Executed/Cancelled BẤT BIẾN (scheduled_date/amount/accumulated/remaining không đổi) | filter chỉ `status='Pending'` |
| INV-DEP-OOS-5 | AUDIT (RC-09, Vòng 14 — SỬA): 1 chu kỳ OoS→Active → ≥1 ALE `out_of_service` (pause) + **ĐÚNG 1** ALE `restored` (resume, emit bởi `transition_asset_status` — KHÔNG còn từ helper reschedule) + **0** ALE `activated` + ≥1 IMM Audit Trail `State Change`. Bất kể có kỳ Pending để dời hay không (consistency) | đếm event sau chu kỳ — xem INV-ALE-RESTORE-1 |
| INV-DEP-OOS-6 | IDEMPOTENT: `Active→Active` no-op (guard prev==to) → KHÔNG dời kép | re-call transition |
| INV-DEP-OOS-7 | FALLBACK: `oos_start_date` không xác định → `{rescheduled:0}`, KHÔNG raise | xóa downtime log + ALE out_of_service → restore |
| INV-DEP-OOS-8 | 0 kỳ Pending / asset không cấu hình KH → no-op không lỗi | asset không schedule → restore |

**Schema-delta Vòng 9:** **KHÔNG có.** `event_type` `out_of_service` + `restored` đã có trong `Asset Lifecycle Event` (round-1); `IMM Audit Trail.event_type='State Change'` đã có; child `AC Asset Depreciation Schedule.scheduled_date` (Date) + `status` (Pending/Executed/Cancelled) đã đủ — **KHÔNG `bench migrate` cho schema** (chỉ deploy code).

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
| `effectiveness_check` | varchar(50)  | COND     | Kết quả xác minh hiệu quả: `Effective` / `Partially Effective` / `Not Effective` (null = chưa xác minh) | **GATE đóng CAPA** (VR-06/VR-07) — reqd & phải = `Effective` để Close |
| `closed_date`         | date         | NO       | Ngày đóng                                         | auto khi close_capa() |
| `linked_incident`     | varchar(140) | NO       | Link → Incident Report                              | bidirectional         |

**CAPA State Machine:**

```
Draft → Open (auto-submit khi tạo)
Open → In Progress (cập nhật root_cause)
In Progress → Pending Verification (gửi QA Officer)
Pending Verification → Closed (close_capa() + docstatus=1) ── GATE: assert_capa_effectiveness_gate()
Open/In Progress/Pending Verification → Overdue (scheduler daily; idempotent; due_date NULL không flip)
```

### II.5.a. CAPA Effectiveness Gate — Single Source of Truth (VR-06 / VR-07) — round 12

> **Self-Correction (round 12):** thiết kế gốc để `close_capa()` (legacy path) đóng CAPA **không qua bất kỳ cổng hiệu quả nào** — chỉ kiểm 3-field `root_cause/corrective_action/preventive_action` (BR-00-08) qua `capa_record_before_submit`. Điều này cho phép đóng CAPA với `effectiveness_check = None` hoặc `'Not Effective'`, vi phạm VR-06/VR-07 vốn đã enforce đúng ở `services/imm16.py::advance_capa_state`. Đường `capa_record_validate` thì để **điều kiện kép** `status=='Closed' AND workflow_state=='Closed'` → save-to-Closed nào không set `workflow_state` lọt cổng. → Hợp nhất 1 SoT.

**INVARIANT-1 — Predicate duy nhất:** tồn tại 1 guard
`services/imm00.py::assert_capa_effectiveness_gate(doc) -> None` định nghĩa điều kiện đóng CAPA. KHÔNG lặp literal điều kiện effectiveness ở >1 nơi với độ chặt khác nhau.

```python
def assert_capa_effectiveness_gate(doc) -> None:
    """SoT cổng hiệu quả CAPA (VR-06/VR-07). Raise ServiceError(VALIDATION, 'FIN-007')
    nếu CAPA chưa đủ điều kiện đóng. Idempotent, không side-effect, không DB write."""
    ec = (getattr(doc, "effectiveness_check", None) or "").strip()
    if not ec:
        raise ServiceError(ErrorCode.VALIDATION,
                           _("VR-06: Phải xác minh hiệu quả (effectiveness_check) "
                             "trước khi đóng CAPA."),
                           message_code="FIN-007")
    if ec != "Effective":
        raise ServiceError(ErrorCode.VALIDATION,
                           _("VR-07: effectiveness_check phải = 'Effective' để đóng CAPA "
                             "(hiện tại: {0}).").format(ec),
                           message_code="FIN-007")
```

**Hai field code — KHÔNG nhầm lẫn (quyết định SoT round 12):**

| Trường envelope | Giá trị | Vai trò |
|---|---|---|
| `code` (ErrorCode bucket) | `VALIDATION` (HTTP 422) | FE phân nhánh UX coarse-grained (`isUserFacing` = true → toast/inline, không modal lỗi hệ thống). `FIN-007` KHÔNG nằm trong enum `ErrorCode`/`_HTTP_FOR_CODE` (nếu dùng làm `code` → default HTTP 400 + FE rơi vào nhánh `UNKNOWN`/system-error → leak). |
| `message_code` | `FIN-007` | Domain code ổn định, FE match để render thông báo VI cố định "Chưa xác minh hiệu quả — không thể đóng CAPA" + audit/log. Đồng bộ với `docs/imm-16/05_API_Specification.md` (FIN-007 = VR-07, 422). |

> **Lưu ý:** AC vòng 12 ghi *"RAISE ServiceError VALIDATION code 'FIN-007'"* — đây là gộp 2 field: bucket = `VALIDATION`, domain code = `FIN-007` (qua `message_code`). `advance_capa_state` hiện raise `ServiceError("FIN-007", ...)` (code=`FIN-007` thuần) — giữ NGUYÊN hành vi (AC-4: "advance_capa_state KHÔNG đổi hành vi"), nhưng `assert_capa_effectiveness_gate` là guard MỚI cho 2 path legacy, dùng bucket `VALIDATION` + `message_code='FIN-007'` để API `close_capa_record` bắt được `ServiceError` và trả 422 đúng cho FE.

**Cả 2 đường đóng gọi CÙNG predicate:**

1. `close_capa()` (legacy, `services/imm00.py:539`) — gọi `assert_capa_effectiveness_gate(doc)` **TRƯỚC** `doc.submit()` (sau khi set `effectiveness_check` từ tham số).
2. `capa_record_validate()` (`services/imm16.py:600`) — fire gate khi `status=='Closed'` **BẤT KỂ** `workflow_state` (bỏ điều kiện kép `AND workflow_state=='Closed'`); gọi cùng `assert_capa_effectiveness_gate(doc)` thay literal `if not doc.effectiveness_check`. Vì là controller `validate` (Frappe `frappe.throw`), wrap: bắt `ServiceError` → `frappe.throw(e.message)` để giữ semantics controller (mọi save-to-Closed: controller UI, `set_value` submit đều qua cổng).

**KHÔNG đụng (giữ nguyên hành vi — AC-4/AC-5):**
- `advance_capa_state` (VR-06/VR-07 đã đúng) — workflow API path, KHÔNG đổi.
- `_open_capa_filter()` / `is_capa_open()` — CAPA chưa qua effectiveness vẫn `status NOT IN ('Closed')` → vẫn đếm "mở"; KPI `capa_open`/`capa_overdue` KHÔNG đổi; không CAPA nào kẹt trạng thái lai.
- `perform_effectiveness_check` (IMM-16) — đường set `effectiveness_check` + workflow, không phải đường đóng legacy.

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

**Event type enum (live — verify `asset_lifecycle_event.json`):**
`commissioned, activated, pm_started, pm_completed, repair_opened, repair_completed, parts_hold_started, parts_hold_resumed, calibration_started, calibration_passed, calibration_failed, incident_reported, out_of_service, restored, decommissioned, transferred, registered, depreciated, depreciation_rules_inherited, depreciation_stopped`

**Schema-delta ADR-001 (A1/A3 + B-2):** QR cấp tài sản — `qr_generated`+`label_printed` đã có trong enum `event_type` (A1/A3 sync JSON; verify `asset_lifecycle_event.json` line 54). **B-2 THÊM option thứ 3 `qr_regenerated`** (verify enum live 2026-06-04: CHƯA có — schema-delta DUY NHẤT của B-2, xem §II.1d-B2):

| event_type | Emit khi | Emit bởi | root_doctype / root_record | Vòng |
|---|---|---|---|---|
| `qr_generated` | Lần đầu sinh `qr_token` (`before_insert` / backfill / token-less on-demand) | `emit_qr_generated` qua `ensure_asset_qr_token` (best-effort) | `AC Asset` / `<asset name>` | A1 |
| `label_printed` | In nhãn QR (1 hoặc batch — **1 event / asset / lần in**) | `emit_label_printed` qua `mark_label_printed` (KHÔNG nuốt lỗi — all-or-nothing) | `AC Asset` / `<asset name>` | **A3** |
| `qr_regenerated` | **Rotate** (sinh-lại) `qr_token` — vô hiệu hoá token cũ + cấp token mới | `emit_qr_regenerated` qua `regenerate_asset_qr_token` (**KHÔNG nuốt lỗi** — sự kiện bảo mật) | `AC Asset` / `<asset name>` | **B-2** |

> Nguồn: [`../imm-04/ADR-001-asset-qr.md`](../imm-04/ADR-001-asset-qr.md) D3. Helper: `create_lifecycle_event(...)` (`utils/lifecycle.py:72`). `get_asset_label_data[_batch]` (GET preview) **KHÔNG** emit `label_printed` — chỉ `mark_label_printed` (POST, người dùng thực sự in) ghi. Xem §II.1.8b. `qr_regenerated` ghi **1 event / lần rotate**, `change_summary`/`notes` **KHÔNG chứa token thô** (xem §II.1.8d). Xem §II.1.8d.

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
| `transition_asset_status()`       | `(asset_name, to_status, actor=None, reason="", root_doctype=None, root_record=None) -> None`                 | None                              | IMM-09, 12, 13           | Đổi lifecycle_status + gọi `create_lifecycle_event(event_type=_lifecycle_event_for(to, **from**=prev))` + log_audit_event + _sync_downtime_log. **RC-09 (Vòng 14):** event nhãn theo (from,to) ⇒ `Out of Service→Active`=`restored` (ĐÚNG 1 ALE, single-emit SoT), các đường khác về Active=`activated`. **Decommissioned:** `_suspend_all_schedules` + `_cancel_pending_depreciation` + `_record_depreciation_stopped` (BR-00-24); **Out of Service:** `_pause_depreciation_on_oos` (BR-00-25); **Active từ prev=Out of Service:** `_reschedule_pending_depreciation_on_restore` (BR-00-25, KHÔNG còn emit ALE — chỉ audit) |
| `_lifecycle_event_for()`          | `(to_status, from_status="") -> str`                                                                          | event_type: str                   | (internal — `transition_asset_status` + `ac_asset.on_update`) | **SỬA (RC-09, BR-00-27, Vòng 14).** Thêm tham số `from_status`. Map (from,to)→event_type: `to='Active'` ∧ `from='Out of Service'`→`restored`; `to='Active'` ∧ from khác→`activated`; còn lại theo bảng §II.1. SoT nhãn `restored`/`activated` cho 2 call-site (service + controller workflow path) — fix tại helper áp dụng đồng nhất. Thuần (no I/O). |
| `_cancel_pending_depreciation()` | `(asset_name) -> int`                                                                          | `cancelled_count: int`            | (internal, gọi bởi `transition_asset_status`) | **(RC-07, BR-00-24).** Tên hàm THẬT trong code (doc §II.1c dùng `_..._on_decommission` là drift). Hủy mọi kỳ `AC Asset Depreciation Schedule.status='Pending'` → `'Cancelled'`; `Executed` bất biến; idempotent. Audit tách ở `_record_depreciation_stopped` (≥1 hủy → 1 ALE `depreciation_stopped` + 1 IMM Audit Trail). Xem §II.1c. |
| `_resolve_oos_start_date()` | `(asset_name) -> date \| None`                                                                          | `date` hoặc `None`            | (internal, BR-00-25) | **MỚI (RC-08, BR-00-25).** SoT mốc bắt đầu OoS: (1) `start_time` Downtime Log đang mở; (2) fallback `creation` ALE `out_of_service` gần nhất; cả 2 thiếu → `None` (caller no-op, KHÔNG raise). Xem §II.1e. |
| `_pause_depreciation_on_oos()` | `(asset_name, actor=None) -> int`                                                                          | `pending_count: int`            | (internal, gọi bởi `transition_asset_status` nhánh Out of Service) | **MỚI (RC-08, BR-00-25).** Best-effort: ghi 1 ALE `out_of_service` note `'depreciation paused'` + số kỳ Pending tạm dừng. 0 Pending → no-op. KHÔNG đụng dữ liệu KH (PAUSE thực thi bởi filter executor). Lỗi audit KHÔNG vỡ transition. Xem §II.1e. |
| `_reschedule_pending_depreciation_on_restore()` | `(asset_name, actor=None) -> dict`                                                                          | `{rescheduled:N, oos_days:int}`            | (internal, gọi bởi `transition_asset_status` nhánh Active từ prev=Out of Service) | **MỚI (RC-08, BR-00-25).** Dời `scheduled_date` mọi kỳ Pending `+= oos_days`; `Executed`/`Cancelled` bất biến; GIỮ `depreciation_amount`/`period_number`/số kỳ. `oos_start` None / `oos_days<=0` → no-op không raise. ≥1 dời → **CHỈ** 1 IMM Audit Trail `State Change` (best-effort) — **RC-09 (Vòng 14): KHÔNG còn emit ALE `restored`** (ALE `restored` do `transition_asset_status` emit, single-emit). Diệt phantom catch-up. Xem §II.1e. |
| `validate_asset_for_operations()` | `(asset_name) -> None`                                                                                        | None / raises                     | IMM-08, 09, 11           | Gate: frappe.throw nếu lifecycle_status ∈ {Out of Service, Decommissioned}                                                       |
| `get_sla_policy()`                | `(priority, risk_class=None) -> dict`                                                                         | policy_dict hoặc `{}`          | IMM-08, 09, 11           | Tra SLA exact (priority × risk_class) rồi fallback is_default                                                                    |
| `create_capa()`                   | `(asset, source_type, source_ref, severity, description, responsible, due_days=30) -> str`                    | capa_name: str                    | IMM-09, 11, 12, 16       | Tạo IMM CAPA Record status=Open, ghi Audit Trail. **⚠️ SoT severity note (Vòng 13, RC-CAPA-ESC):** hàm này CHỈ set field `severity` (Minor/Major/Critical) — KHÔNG set `imm_risk_level`. Do đó escalation IMM-16 (`_escalate_capa`) phải đọc **effective-risk** = `imm_risk_level` khi High/Critical else fallback `severity` normalized (`_capa_escalation_severity`, xem `docs/imm-16/04 §VI.2.1`), nếu không CAPA `severity=Critical` sẽ không bao giờ leo thang. KHÔNG đổi chữ ký `create_capa` round này. |
| `assert_capa_effectiveness_gate()` | `(doc) -> None`                                                                                             | None / raises ServiceError       | SoT guard (round 12)     | **SoT cổng hiệu quả (INVARIANT-1, VR-06/VR-07).** Raise `ServiceError(VALIDATION, message_code='FIN-007')` nếu `effectiveness_check` null/rỗng (VR-06) hoặc != `Effective` (VR-07). Idempotent, no DB write. Gọi bởi `close_capa()` + `capa_record_validate()`. Xem §II.5.a |
| `close_capa()`                    | `(capa_name, root_cause, corrective_action, preventive_action, effectiveness_check=None, actor=None) -> None` | None / raises                     | IMM-12, QA               | Đóng CAPA: set 3-field + effectiveness_check → **`assert_capa_effectiveness_gate(doc)` (round 12, TRƯỚC submit)** → status=Closed, submit, ghi Audit Trail (change_summary có effectiveness) + ALE. RAISE FIN-007 nếu chưa qua cổng (KHÔNG submit, KHÔNG đổi Closed) |
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

### III.1b. SoT — Giá trị còn lại "hiệu dụng" (`effective_book_value`, BR-05-13 / RC-06)

**Bối cảnh / lỗi thiết kế gốc (Self-Correction 2026-06-03 — falsy-zero):** giá trị còn lại của tài sản (`current_book_value`) được suy ra ở **3 nơi BE** bằng idiom `float(a.get("current_book_value") or gross)`:

| # | Call-site | File:line | Dùng book để |
|---|---|---|---|
| 1 | `compute_depreciation` (payload sau khi chạy KH 1 asset) | `api/imm00.py:1640` | trả `book_value` cho FE |
| 2 | `_depr_enrich_row` (làm giàu mỗi dòng list) | `api/imm00.py:2232` | gán `current_book_value` enriched cho drill + nuôi `is_fully_depreciated` |
| 3 | `get_depreciation_stats` (KPI tổng) | `api/imm00.py:2355` | cộng `total_book` + `by_category[cat]` + nuôi `is_fully_depreciated` (đếm `fully_depreciated`) |

**Lỗi:** `or` là toán tử **falsy**, KHÔNG phân biệt 2 trạng thái KHÁC NHAU của `current_book_value`:

- `None` (asset CHƯA từng chạy KH → field NULL) → **đúng** phải fallback `gross` (nguyên giá ban đầu).
- `0.0` (asset đã khấu hao **hết** về 0 — `residual=0`, giá trị đã chạy & lưu hợp lệ) → `0.0 or gross` **trả nhầm `gross`** (phantom).

Hệ quả (đếm sai + cộng sai khi asset khấu hao hết về đúng 0):

1. **`fully_depreciated` đếm thiếu:** asset `gross>0, residual=0, configured, current_book_value=0.0` đáng lẽ `is_fully_depreciated()=True` (book `0 ≤ residual+1`). Nhưng book bị thổi về `gross > residual+1` → predicate trả **False** → KHÔNG được đếm.
2. **`total_book_value` over-count phantom:** cùng asset cộng nhầm `gross` thay vì `0.0` → tổng "Giá trị còn lại" của Hub bị thổi phồng. `by_category[cat]` cũng over-count `gross`.
3. **FE hiện sai:** cột "Giá trị còn lại" của asset đã KH hết hiện `gross` thay vì `0đ`.

**Fix — SoT DUY NHẤT** đặt trong `services/depreciation.py`:

```python
def effective_book_value(asset_row: dict) -> float:
    """SoT (BR-05-13): giá trị còn lại "hiệu dụng" của tài sản.

    Phân biệt rõ None vs 0.0 — KHÔNG dùng idiom falsy `current_book_value or gross`:
      - current_book_value IS NONE (NULL — asset CHƯA từng chạy KH) → trả gross
        (nguyên giá; hành vi cũ với asset chưa khấu hao GIỮ NGUYÊN, không regression).
      - current_book_value đã set (kể cả 0.0) → trả float(current_book_value)
        (giá trị thật đã lưu; asset KH hết về 0 trả 0.0, KHÔNG phantom gross).

    gross = float(gross_purchase_amount or 0). Pure (không đụng DB) — caller đã
    có sẵn current_book_value & gross_purchase_amount trong dict.

    SoT DUY NHẤT: cả 3 call-site BE (compute_depreciation, _depr_enrich_row,
    get_depreciation_stats) PHẢI gọi hàm này — KHÔNG inline lại `or gross`
    (drift risk → count/total sai kiểu falsy-zero). is_fully_depreciated cũng
    suy book qua hàm này (nhất quán count == drill).
    """
    gross = flt(asset_row.get("gross_purchase_amount") or 0)
    raw_book = asset_row.get("current_book_value")
    return flt(raw_book) if raw_book is not None else gross
```

**Wiring (3 call-site BE + 1 predicate SoT — XOÁ idiom `or gross` inline):**
- `compute_depreciation()` (api/imm00.py:~1640): `book_value = effective_book_value(a)` (lazy-import). `a` đã có `current_book_value` + `gross_purchase_amount` từ `frappe.db.get_value`.
- `_depr_enrich_row()` (api/imm00.py:~2232): `book_value = effective_book_value(a)` → gán `a["current_book_value"]`. Dòng enriched này nuôi cả drill rows lẫn `is_fully_depreciated` (list_assets path).
- `get_depreciation_stats()` (api/imm00.py:~2355): `book = effective_book_value(a)` → cộng `total_book` + `by_category[cat]` + truyền `current_book_value=book` vào dict gọi `is_fully_depreciated`.
- `is_fully_depreciated()` / SoT predicate (services/depreciation.py): nhánh suy book hiện tại (`book = flt(raw_book) if raw_book is not None else gross`, dòng ~188) **gọi lại** `effective_book_value(asset_row)` → 1 chỗ DUY NHẤT định nghĩa "None→gross, set→giá-trị-thật". Hành vi predicate KHÔNG đổi (logic byte-for-byte) — chỉ rút về SoT chung.

**INVARIANT (sau fix — đo trên data-live):**

| ID | Phát biểu |
|---|---|
| INV-DEP-6 | asset `gross>0 ∧ residual=0 ∧ configured ∧ current_book_value=0.0` → `is_fully_depreciated()=True` → được `get_depreciation_stats().fully_depreciated` đếm (trước: bị loại do book thổi về gross). |
| INV-DEP-7 | `total_book_value` & `by_category[cat]` KHÔNG cộng phantom `gross` cho asset book=0.0 (cộng đúng `0.0`). |
| INV-DEP-8 | `current_book_value IS NULL/None` → `effective_book_value == gross` (asset chưa chạy KH GIỮ hành vi cũ, no regression); `current_book_value=0.0` → `== 0.0`. |
| INV-DEP-5 | (giữ nguyên) `get_depreciation_stats().fully_depreciated == de-dup len(list_assets_depreciation(depreciation_filter='fully_depreciated') mọi trang)` — count == drill. Cả hai cùng dùng SoT mới (trước cùng-sai-cùng-kiểu, nay cùng-đúng). |

**Grep-guard (CI / review):** sau fix, `grep -n 'current_book_value") or gross' assetcore/api/imm00.py` → **0 occurrence**. Mọi suy `current_book_value` ngoài đường ghi DB phải qua `effective_book_value` (HOẶC qua `is_fully_depreciated` đã route về nó). Đường GHI book value (cron / `run_due_depreciation` → `_clamp_book_value`) KHÔNG bị guard này tác động (đó là persister, không phải read-derive).

**RED-proven (DoD test gate):** revert SoT về `or gross` → test `fully_depreciated`-count (INV-DEP-6) + `total_book`-no-phantom (INV-DEP-7) **FAIL**; restore → **GREEN**. Full BE suite KHÔNG regression (asset có book>0 / book=None giữ y nguyên số).

### III.1c. SoT — Kế thừa luật khấu hao Category → Asset (`inherit_depreciation_rules_from_category`, BR-00-18..21 / RC-03)

**Bối cảnh / lỗi thiết kế gốc (Self-Correction 2026-06-03):** luật khấu hao (`total_depreciation_months`, `residual_value`) CHỈ được điền khi asset đi qua đường `create_ac_asset` (IMM-04, `services/imm04.py:541-544,556-561`). Asset tạo trực-tiếp `frappe.get_doc("AC Asset",...).insert()` / import:
- `ACAsset.before_insert()` chỉ gọi `_inherit_gmdn_from_device_model()` — KHÔNG đụng months/residual.
- `ACAsset.before_save()` (RC-02) chỉ điền `depreciation_method` / `depreciation_frequency` / `depreciation_start_date` — **KHÔNG** điền `total_depreciation_months` / `residual_value`.

Hệ quả (verify LIVE site miyano 2026-06-03 — Category `CAT-0659` rule=120 tháng; asset in-memory sau `before_insert` vẫn `total_depreciation_months=None`): gọi `regenerate_depreciation_schedule` → **422 "Thiếu: Số tháng khấu hao (total_depreciation_months)"** dù Category đã có luật. **Đây là lỗi user báo.**

**Fix — SoT DUY NHẤT** đặt trong `services/depreciation.py`:

```python
def inherit_depreciation_rules_from_category(asset) -> bool:
    """SoT (BR-00-18): copy luật khấu hao từ AC Asset Category xuống Asset
    KHI field đang thiếu. Mutate `asset` in-place, trả True nếu ≥1 field
    (months hoặc residual) được backfill, ngược lại False (no-op / không đủ điều kiện).
    [Round-2 align — implementation thực trả `bool`, KHÔNG `int`: did_inherit semantics.]

    Điều kiện điền (gate chung):
      - gross_purchase_amount > 0  (asset không có nguyên giá → không khấu hao).
      - asset_category trỏ tới Category tồn tại & có luật (total_depreciation_months > 0).

    Per-field (độc lập, KHÔNG clobber — BR-00-19):
      - months:   chỉ điền khi int(asset.total_depreciation_months or 0) <= 0.
                  → asset.total_depreciation_months = Category.total_depreciation_months
      - residual: chỉ điền khi flt(asset.residual_value or 0) == 0.
                  → asset.residual_value = round(gross * Category.default_residual_value_pct/100, 2)
      - method/frequency: tận dụng RC-02 (before_save) — KHÔNG trùng lặp ở đây
                  (helper tập trung 2 field bị bỏ sót: months + residual).

    KHÔNG raise khi Category thiếu luật (BR-00-20) → trả 0 (asset lưu với months=0;
    422 ở regenerate là ĐÚNG — lỗi master-data, không che).
    Idempotent (BR-00-18): asset đã đủ luật → 0 field đổi → trả 0.

    Công thức residual CHUẨN HOÁ = round(gross * pct/100, 2). Đối chiếu:
      - imm04.create_ac_asset (:543-544): gross*pct/100 (KHÔNG round) → đường insert-path
        hợp lệ duy nhất ngoài SoT; đối chiếu để KHÔNG lệch công thức.
      - depreciation.bulk_regenerate_by_category: Round-4 RC-05 ĐÃ route qua SoT này
        (KHÔNG còn inline copy gross*pct/100) → residual luôn round(...,2) nhất quán.
    """
```

**Wiring (4 caller SoT — KHÔNG có nhánh tự copy months/residual ngoài insert-path):**
- `ACAsset.before_insert()` thêm 1 dòng **sau** `self._inherit_gmdn_from_device_model()`:
  `from assetcore.services.depreciation import inherit_depreciation_rules_from_category; inherit_depreciation_rules_from_category(self)` (lazy-import tránh circular). → fix asset MỚI tạo/import.
- `compute_all_depreciation()` (api/imm00.py) gọi cùng helper trên asset thiếu method/months **trước** `generate_schedule` (xem dưới III.1c-1). → fix HÀNG LOẠT (nút global).
- **`regenerate_depreciation_schedule()` (api/imm00.py) — Round-2 RC-04, per-asset self-heal:** gọi cùng helper trên asset CŨ (tạo trước round-1, chưa từng kế thừa) **trước** pre-check 4-field (xem dưới III.1c-2). → fix 1 asset cũ ngay tại nút "Sinh lịch khấu hao" mà KHÔNG cần admin / KHÔNG cần chạy backfill global.
- **`bulk_regenerate_by_category()` (services/depreciation.py) — Round-4 RC-05, bulk theo Danh mục:** gọi cùng helper cho từng asset thuộc Category, thay 4 dòng inline gán method/months/frequency/residual (xem dưới III.1c-3). → fix nút "Áp dụng khấu hao theo từng Danh mục" mà KHÔNG clobber giá trị user.

**Grep-guard (CI / review — cập nhật Round-4 RC-05):** ngoài `inherit_depreciation_rules_from_category`, **chỉ `create_ac_asset` (IMM-04, insert-path)** được copy `total_depreciation_months`/`residual_value` từ Category. `grep -rn "total_depreciation_months\s*=\|residual_value\s*=" assetcore/services assetcore/api assetcore/assetcore/doctype` → mọi gán months/residual-từ-Category phải nằm trong SoT helper **HOẶC** `create_ac_asset`; nhánh thứ 3 = vi phạm SoT. Đặc biệt: **`bulk_regenerate_by_category` KHÔNG còn được phép inline copy** (round-1 từng cho phép — round-4 đã route qua SoT). 2 đường copy còn lại PHẢI cùng công thức residual `round(gross*pct/100, 2)`.

#### III.1c-1. `compute_all_depreciation` — backfill-rồi-sinh (BR-00-21)

Thay hành vi cũ **skip** asset thiếu method/months bằng **backfill-rồi-generate**. Pseudo-code:

```python
def compute_all_depreciation():
    _assert_system_admin()                      # RBAC: non-admin → 403 (không leak)
    from assetcore.services.depreciation import (
        inherit_depreciation_rules_from_category, generate_schedule, run_due_depreciation,
    )
    res = {"inherited": 0, "generated": 0, "executed_rows": 0,
           "updated_assets": 0, "skipped_has_history": 0, "skipped_no_rule": 0}
    for a in assets(docstatus != 2):
        if has_executed_period(a):              # ≥1 kỳ Executed → bảo toàn lịch sử
            res["skipped_has_history"] += 1; continue
        doc = frappe.get_doc("AC Asset", a.name)
        if missing_method_or_months(doc):
            n = inherit_depreciation_rules_from_category(doc)   # SoT
            if n: doc.save(ignore_permissions=True); res["inherited"] += 1
        if still_missing_rule(doc):             # Category cũng không có luật
            res["skipped_no_rule"] += 1; continue
        if not has_schedule(doc.name):
            generate_schedule(doc.name, force=False); res["generated"] += 1
    run = run_due_depreciation(None)
    res["executed_rows"]  = run["executed_rows"]
    res["updated_assets"] = run["updated_assets"]
    # Audit trail (BR-00-21 / CLAUDE.md §5): 1 lifecycle/audit event tổng cho hành động
    # backfill global (actor, inherited count, generated count) — hoặc per-asset inherited.
    if res["inherited"] or res["generated"]:
        log_audit_event(... event_type="Depreciation Backfill",
                        change_summary=f"inherited={res['inherited']} generated={res['generated']}")
    return _ok(res)
```

**Idempotent:** lần chạy thứ 2 — mọi asset đã đủ luật → `inherit_...` trả 0 → `inherited=0`; `has_schedule` True → `generated=0`; asset Executed vẫn `skipped_has_history` (không đổi `accumulated`). **Không tạo trùng schedule.**

**Payload shape (thay payload cũ 4-key):** `{inherited, generated, executed_rows, updated_assets, skipped_has_history, skipped_no_rule}` — `skipped_no_rule` = asset không có cả luật ở Category (master-data chưa cấu hình). FE map sang toast (06 §III.10b-bis).

#### III.1c-2. `regenerate_depreciation_schedule` — per-asset self-heal (BR-00-22 / RC-04, Round-2)

**Lỗi user báo (goal C):** asset CŨ tạo TRƯỚC round-1 (khi `before_insert` chưa wire SoT inherit) có `gross>0` + `asset_category` CÓ luật (`total_depreciation_months>0`) NHƯNG `asset.total_depreciation_months=0` (chưa kế thừa). Bấm nút **"Sinh lịch khấu hao"** → `regenerate_depreciation_schedule` chạy pre-check 4-field → fail ngay ở months=0 → **422 "Thiếu: Số tháng khấu hao (total_depreciation_months)"** dù Category đã có luật. Nút global `compute_all_depreciation` đã fix hàng-loạt nhưng chỉ admin chạy được; user muốn self-heal **1 asset cũ tại chỗ**.

**Fix — chèn 1 lần gọi SoT TRƯỚC pre-check, KHÔNG inline lại copy months/residual:**

```python
@frappe.whitelist(methods=["POST"])
def regenerate_depreciation_schedule(asset_name, force=1):
    from assetcore.services import depreciation as depr_svc
    if not frappe.db.exists(_DT_ASSET, asset_name):
        return _err(_(_ERR_ASSET_NOT_FOUND), 404)

    # ── RC-04 self-heal: asset CŨ chưa kế thừa luật → nạp doc, gọi SoT DUY NHẤT.
    #    KHÔNG copy months/residual inline ở đây (grep-guard: 0 occurrence trong
    #    api/imm00.py ngoài lời gọi này). did_inherit=True ⇒ save + audit.
    asset_doc = frappe.get_doc(_DT_ASSET, asset_name)
    did_inherit = depr_svc.inherit_depreciation_rules_from_category(asset_doc)   # SoT (round-1)
    if did_inherit:
        asset_doc.flags.ignore_links = True
        asset_doc.flags.ignore_mandatory = True
        asset_doc.save(ignore_permissions=True)
        _log_regenerate_selfheal_audit(asset_name)        # ALE + IMM Audit Trail

    # ── Pre-check CHẠY LẠI SAU inherit — đọc state SAU self-heal (KHÔNG đọc trước).
    a = frappe.db.get_value(_DT_ASSET, asset_name,
        ["depreciation_method", "total_depreciation_months", "gross_purchase_amount",
         "depreciation_start_date", "in_service_date", "commissioning_date"], as_dict=True) or {}
    missing = [...]   # 4-field check Y NGUYÊN (method / months>0 / gross>0 / start_date)
    if missing:
        return _err(_("Không đủ thông tin để sinh lịch khấu hao. Thiếu: {0}.")
                    .format("; ".join(missing)), 422)
    ...   # generate_schedule(...) Y NGUYÊN từ đây
```

**INVARIANT (BR-00-22):**

| # | GIVEN | WHEN regenerate | THEN |
|---|---|---|---|
| 1 | asset gross>0, Category CÓ luật, `asset.months=0` (chưa kế thừa) | self-heal | inherit → `did_inherit=True` → save → pre-check **pass** → **200**, `periods>0`. KHÔNG còn 422 "Thiếu: Số tháng". (Lỗi user.) |
| 2 | asset gross>0 NHƯNG Category cũng thiếu luật (`cat.months<=0`) HOẶC asset không `asset_category` | self-heal no-op | `did_inherit=False` → pre-check chạy lại → **VẪN 422** liệt kê đúng field thiếu (months / start_date / gross / method). KHÔNG che lỗi master-data (BR-00-20). |
| 3 | asset đã có `months>0` HOẶC `residual_value` do user nhập tay | inherit no-op trên field đã có | giá trị user **GIỮ NGUYÊN** (BR-00-19 no-clobber) → chỉ sinh lịch theo giá trị hiện hữu. |
| 4 | asset đã có ≥1 kỳ **Executed** | self-heal KHÔNG override months/residual đã chạy | giữ invariant không phá lịch sử (BR-00-21). `force=1` xoá-sinh-lại các kỳ **Pending** nhưng months/residual đã-Executed bất biến (inherit no-op vì field đã có). |
| 5 | gọi regenerate **2 lần liên tiếp** cùng asset | idempotent | cùng số `periods`; lần 2 `did_inherit=False` (đã đủ luật) → KHÔNG sinh audit event rác. |

**Pre-check chạy LẠI SAU inherit (KHÔNG trước):** điểm mấu chốt RC-04 — round-1 đọc 4-field MỘT LẦN ở đầu rồi 422. Round-2 phải **nạp doc + inherit + save TRƯỚC**, rồi `db.get_value` lại để pre-check thấy months đã được điền. Nếu vẫn đọc-trước-inherit → 422 oan như cũ.

**Audit (BR-00-22 / CLAUDE.md §5) — chỉ khi `did_inherit=True`:**

```python
def _log_regenerate_selfheal_audit(asset_name: str) -> None:
    """1 ALE 'depreciation_rules_inherited' + 1 IMM Audit Trail 'System' cho self-heal
    per-asset. Best-effort (try/except) — KHÔNG để lỗi audit chặn sinh lịch."""
    try:
        from assetcore.services.imm00 import create_lifecycle_event, log_audit_event
        actor = frappe.session.user or "Administrator"
        create_lifecycle_event(asset=asset_name, event_type="depreciation_rules_inherited",
            actor=actor, from_status="", to_status="",
            root_doctype=_DT_ASSET, root_record=asset_name,
            notes="Self-heal: kế thừa luật khấu hao từ Category khi sinh lịch (RC-04).")
        log_audit_event(asset=asset_name, event_type="System", actor=actor,
            ref_doctype=_DT_ASSET, ref_name=asset_name,
            change_summary=f"Self-heal kế thừa luật khấu hao từ Category cho {asset_name} "
                           f"khi 'Sinh lịch khấu hao'.")
    except Exception:
        frappe.log_error(frappe.get_traceback(), "regenerate self-heal audit failed")
```

- `event_type='depreciation_rules_inherited'` = Select option HỢP LỆ (đã thêm round-1 vào `asset_lifecycle_event.json`) — KHÔNG cần migrate thêm.
- IMM Audit Trail `event_type='System'` = enum governance hiện hữu (KHÔNG mở rộng).
- **inherit no-op (did_inherit=False) → KHÔNG sinh event** → tránh audit rác khi user bấm lại trên asset đã đủ luật (invariant #5).

**Grep-guard (CI / review, mở rộng round-1):** trong `api/imm00.py`, **0 occurrence** copy `total_depreciation_months`/`residual_value` từ Category NGOÀI lời gọi `inherit_depreciation_rules_from_category(...)`. `regenerate_depreciation_schedule` + `compute_all_depreciation` đều CHỈ qua SoT. (Đường copy hợp lệ duy nhất ngoài SoT vẫn là `create_ac_asset` (imm04) + `bulk_regenerate_by_category` (depreciation) — KHÔNG nằm trong api/imm00.py.)

**Regression bất biến:** đường `before_insert` (RC-03 round-1) KHÔNG đổi hành vi — RC-04 chỉ thêm self-heal ở endpoint regenerate, không đụng controller. `force=1` xoá-sinh-lại Pending Y NGUYÊN. Các trả-về 404/422-link/500 hiện hữu giữ nguyên format VI (nhãn field trong ngoặc — đúng round-1, KHÔNG leak raw method/token).

#### III.1c-3. `bulk_regenerate_by_category` — hợp nhất về SoT (BR-00-23 / RC-05, Round-4)

**Lỗi thiết kế gốc (Self-Correction 2026-06-03, Round-4):** `services/depreciation.py::bulk_regenerate_by_category` (`:454-521`) — nút **"Áp dụng khấu hao theo từng Danh mục"** — vẫn **inline 4 dòng** copy luật từ Category xuống asset (`:495-504`):

```python
# ❌ TRƯỚC (round-1): inline copy — clobber + N+1 + no audit
asset_doc.depreciation_method      = cat.get("default_depreciation_method") or ""
asset_doc.total_depreciation_months = int(cat.get("total_depreciation_months") or 0)
asset_doc.depreciation_frequency   = cat.get("depreciation_frequency") or "Monthly"
asset_doc.residual_value           = round(gross * residual_pct / 100, 2) if residual_pct else 0
```

3 lỗi: (a) **clobber** — ghi đè `months/residual/method/frequency` user đã nhập tay (gán vô điều kiện, không check field đã có); (b) **N+1** — `frappe.db.count(_DT_SCHED, {parent, status:'Executed'})` chạy per-asset trong loop (`:485-488`); (c) **không audit/lifecycle**, payload thiếu `inherited` + `skipped_no_rule` (lệch `compute_all`).

**Fix — route 100% qua SoT + mirror N+1 fix `compute_all` round-3:**

```python
def bulk_regenerate_by_category(category_name: str) -> dict:
    if not frappe.db.exists(_DT_CATEGORY, category_name):
        return {"error": "Category not found"}

    assets = frappe.get_all(_DT_ASSET,
        filters={"asset_category": category_name, "docstatus": ("!=", 2)},
        fields=["name"], limit_page_length=10000)

    # ── N+1 fix: 1 query GROUP BY parent (executed-history) chạy MỘT LẦN trước loop
    #    (mirror compute_all round-3). Set lookup O(1) trong loop → KHÔNG db.count per-asset.
    executed_parents = {
        r["parent"] for r in frappe.get_all(_DT_SCHED,
            filters={"parenttype": _DT_ASSET, "status": "Executed"},
            fields=["parent"], group_by="parent")
    }

    inherited = regenerated = skipped_has_history = skipped_no_rule = errors = 0
    inherited_assets: list[str] = []
    for a in assets:
        try:
            if a.name in executed_parents:          # bảo toàn lịch sử (BR-00-23)
                skipped_has_history += 1; continue

            asset_doc = frappe.get_doc(_DT_ASSET, a.name)
            did_inherit = inherit_depreciation_rules_from_category(asset_doc)  # SoT — KHÔNG inline
            if did_inherit:
                asset_doc.flags.ignore_links = True
                asset_doc.flags.ignore_mandatory = True
                asset_doc.save(ignore_permissions=True)
                inherited += 1
                inherited_assets.append(a.name)

            # asset gross<=0 HOẶC Category cũng thiếu luật → KHÔNG có gì sinh → skipped_no_rule
            if int(asset_doc.total_depreciation_months or 0) <= 0 \
               or flt(asset_doc.gross_purchase_amount or 0) <= 0:
                skipped_no_rule += 1; continue

            generate_schedule(a.name, force=True)    # force=True: asset chưa-Executed → xoá-sinh-lại
            regenerated += 1
        except Exception as e:
            frappe.logger().warning(f"Bulk regen failed for {a.name}: {e}")
            errors += 1

    frappe.db.commit()
    _log_bulk_regen_audit(category_name, inherited, regenerated, inherited_assets)  # best-effort
    return {
        "category": category_name, "total_assets": len(assets),
        "inherited": inherited, "regenerated": regenerated,
        "skipped_has_history": skipped_has_history,
        "skipped_no_rule": skipped_no_rule, "errors": errors,
    }
```

**INVARIANT (BR-00-23):**

| # | GIVEN | WHEN bulk theo Danh mục | THEN |
|---|---|---|---|
| 1 | asset thiếu luật, Category CÓ luật | SoT inherit | `inherited++`, `regenerated++`; `months/residual` == Category (round 2dp). |
| 2 | asset đã có `months>0` / `residual≠0` / `method` / `frequency` user nhập | SoT no-op trên field đã có | giá trị user **GIỮ NGUYÊN** (no-clobber — BR-00-19). KHÔNG còn 4 dòng inline ghi đè. |
| 3 | asset có ≥1 kỳ **Executed** | bỏ qua qua `executed_parents` prefetch | `skipped_has_history++`; `accumulated_depreciation/current_book_value` **bất biến**. |
| 4 | asset `gross<=0` HOẶC Category cũng thiếu luật (`cat.months<=0`) | SoT no-op | `skipped_no_rule++` (KHÔNG bịa số, KHÔNG che lỗi master-data — BR-00-20). |
| 5 | chạy bulk **lần 2** trên cùng dataset | idempotent | `inherited=0` (đã đủ luật) + `regenerated=0` (asset đã có schedule rows → `generate_schedule` skip) → payload ổn định. |

> **`force=True` vs idempotent (#5):** asset chưa-Executed dùng `generate_schedule(force=True)` để áp luật Category MỚI (xoá-sinh-lại Pending). Idempotent #5 đúng vì sau lần 1 luật đã khớp Category ⇒ lần 2 `inherited=0`; `regenerated` đếm số asset thực sự sinh lại — nếu dataset KHÔNG đổi luật Category giữa 2 lần, dùng cùng đầu vào ⇒ schedule giống hệt (số `periods` bất biến, `accumulated` không đổi vì chưa Executed). Test idempotent kiểm `inherited=0` + payload-stable; nếu spec QA muốn `regenerated=0` tuyệt đối ở lần 2, chuyển nhánh sang `generate_schedule(force=False)` (skip khi đã có rows) — **quyết định:** giữ `force=True` cho asset chưa-Executed (đúng mục đích "áp luật MỚI"), assert idempotent ở `inherited=0` + `skipped_has_history` bất biến + `accumulated` bất biến.

**N+1 đóng (mirror `compute_all` round-3):** `frappe.db.count(parent=…, status='Executed')` per-asset (2×? → N query) bị thay bằng **ĐÚNG 1 query** `frappe.get_all(_DT_SCHED, filters={parenttype, status:'Executed'}, group_by='parent')` → `executed_parents` set, lookup O(1) trong loop. Số query cho phép kiểm executed-history KHÔNG còn phụ thuộc tuyến tính vào N.

**Audit (BR-00-23 / CLAUDE.md §5) — best-effort, KHÔNG chặn payload:**

```python
def _log_bulk_regen_audit(category, inherited, regenerated, inherited_assets):
    """Per-asset ALE 'depreciation_rules_inherited' + 1 IMM Audit Trail 'System' TỔNG.
    Best-effort try/except — lỗi audit KHÔNG để chặn payload trả về (CLAUDE.md §5)."""
    try:
        from assetcore.services.imm00 import create_lifecycle_event, log_audit_event
        actor = frappe.session.user or "Administrator"
        for asset_name in inherited_assets:                 # per-asset guard riêng
            try:
                create_lifecycle_event(asset=asset_name,
                    event_type="depreciation_rules_inherited",   # option có sẵn round-1
                    actor=actor, from_status="", to_status="",
                    root_doctype=_DT_ASSET, root_record=asset_name,
                    notes=f"Kế thừa luật khấu hao từ Category {category} (bulk theo Danh mục).")
            except Exception:
                frappe.logger().warning(f"bulk regen ALE failed for {asset_name}")
        if inherited or regenerated:
            log_audit_event(asset=(inherited_assets[0] if inherited_assets else category),
                event_type="System", actor=actor,
                ref_doctype=_DT_CATEGORY, ref_name=category,
                change_summary=f"Áp dụng khấu hao theo Danh mục {category}: "
                               f"inherited={inherited}, regenerated={regenerated}.")
    except Exception:
        frappe.log_error(frappe.get_traceback(), "bulk regen audit failed")
```

- `event_type='depreciation_rules_inherited'` = Select option HỢP LỆ (đã thêm round-1 vào `asset_lifecycle_event.json`) — **KHÔNG migrate thêm**.
- IMM Audit Trail `event_type='System'` = enum governance hiện hữu (KHÔNG mở rộng).
- IMM Audit Trail TỔNG chỉ sinh khi `inherited or regenerated` (có thay đổi thật) → KHÔNG audit rác khi bulk no-op trên Category đã đồng bộ.

**Payload chuẩn hoá (7-key, khớp `compute_all`):** `{category, total_assets, inherited, regenerated, skipped_has_history, skipped_no_rule, errors}` — thêm `inherited` + `skipped_no_rule` so với payload cũ 5-key `{category, total_assets, regenerated, skipped_has_history, errors}`. FE map sang toast (06 §III.10d) + `api/imm00.ts` type (06 §V.1).

**Grep-guard (CI / review):** trong thân `bulk_regenerate_by_category`, **0 occurrence** copy `total_depreciation_months`/`residual_value`/`depreciation_method`/`depreciation_frequency` từ Category NGOÀI lời gọi `inherit_depreciation_rules_from_category(...)` (giống guard round-1 cho regenerate path). `grep -n "asset_doc\.\(total_depreciation_months\|residual_value\|depreciation_method\|depreciation_frequency\)\s*=" services/depreciation.py` → 0 dòng trong hàm này.

**TDD (RED→GREEN):** test `test_no_clobber` (asset months=24 user-nhập + Category months=120 → sau bulk months **vẫn 24**) PHẢI **RED-proven** trước GREEN (chứng minh bug clobber cũ thật). Test `test_n1_query_count` (đếm `frappe.db.sql`/`get_all` call cho executed-history == 1 bất kể N asset) PHẢI **RED-proven** trên code inline `db.count` cũ trước GREEN. `bench --site miyano run-tests` cho `test_depreciation` + `test_imm00` PASS.

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

## III.1c. RBAC Capability Layer — `assetcore/services/shared/rbac.py` (stale-safe)

> **SSoT của resolution capability.** Code hỏi *capability* (`pm.write`, `decommission.create`…), KHÔNG so role-name (tránh anti-pattern "RBAC dead-gate"). Binding `capability → (DocType, ptype)` ở `CAPABILITY_MAP`; quyền THẬT do DocPerm/Workflow (data) quyết qua `frappe.has_permission`. Đổi quyền = sửa DocPerm ở `/app`, KHÔNG deploy code.
> **Self-Correction (2026-06-04, USER REWORK IMM-14):** thiết kế gốc gãy end-to-end trên gunicorn worker đang chạy. Mục này định nghĩa hành vi **stale-safe** thay cho hành vi cũ. Đổi gì / vì sao → bảng "Delta thiết kế" cuối mục.

### III.1c-1. CAPABILITY_MAP — auto-gen + override

`CAPABILITY_MAP: dict[str, tuple[str, str]]` sinh từ `_DOMAIN_PRIMARY` × `_PTYPES` (`read/write/create/delete/submit/cancel`) rồi `.update()` các override đặc thù. Các cap IMM-14 (override):

| Capability | (DocType, ptype) | Ý nghĩa |
|---|---|---|
| `decommission.read` | `("Asset Decommission", "read")` | Xem hồ sơ giải nhiệm |
| `decommission.create` | `("Asset Decommission", "create")` | Tạo hồ sơ giải nhiệm |
| `decommission.approve` | `("Asset Decommission", "submit")` | Duyệt = giải nhiệm thật (submit) |

#### III.1c-1a. A2 (ADR-001 D4) — domain `asset.*` cho QR resolve

> **Đề mục QR A2 (V3).** Trước A2: `asset.read` **KHÔNG tồn tại** — `AC Asset` chỉ ở `_DOMAIN_DOCTYPES["_shared"]` (rbac.py:55, dùng cho `DOCTYPE_DOMAIN` grouping), KHÔNG có khóa `"Asset"` trong `_DOMAIN_PRIMARY` → 0 cap bind `AC Asset`. Gate `resolve_qr_token` bằng cap chưa tồn tại = RBAC dead-gate (lesson r1-25) → BẮT BUỘC thêm trước.

**Thay đổi A2 (`services/shared/rbac.py`):** thêm 1 khóa vào `_DOMAIN_PRIMARY`:
```python
_DOMAIN_PRIMARY = {
    ...,
    "Compliance": "IMM CAPA Record",
    "Asset": "AC Asset",          # ← A2: auto-sinh asset.read/write/create/delete/submit/cancel
}
```
Vòng lặp `for _dom, _dt in _DOMAIN_PRIMARY.items()` (rbac.py:79) tự sinh 6 cap bind `("AC Asset", <ptype>)`:

| Capability | (DocType, ptype) | Dùng ở |
|---|---|---|
| `asset.read` | `("AC Asset", "read")` | **A2** — gate read-only: `resolve_qr_token`, `get_asset_scan_info`, `get_asset`; route FE `/a/:token`, `/assets/:id`, `/assets/:id/info` |
| `asset.write` | `("AC Asset", "write")` | gate sửa asset: nút "Chỉnh sửa" (`AssetDetailView`), transition trạng thái. *(KHÔNG còn gate in nhãn — D6 tách sang `asset.print`.)* |
| `asset.create` / `delete` / `submit` / `cancel` | `("AC Asset", <ptype>)` | sinh kèm (chưa wire endpoint riêng — dùng dần) |
| `asset.print` | `("AC Asset", "print")` | **D6 (EXECUTED Vòng 3)** — gate in nhãn: `get_asset_label_data[_batch]`, `mark_label_printed`; route FE `AssetLabelPrint`; nút "In nhãn QR" + "In nhãn hàng loạt". DocPerm print=1 sẵn cho mọi role vận hành. |
| `asset.qr.rotate` | `("AC Asset", "write")` | **D6 (EXECUTED Vòng 3)** — gate rotate token: `regenerate_asset_qr_token`; nút "Sinh lại mã QR". Rotate=GHI ⇒ bind "write" (chỉ Super Admin/role được cấp). |

- **KHÔNG đụng `_shared`:** giữ `"AC Asset"` trong `_DOMAIN_DOCTYPES["_shared"]`. Hai map độc lập (grouping vs cap-primary) — không xung đột.
- **Resolve thật:** `can("asset.read")` → `frappe.has_permission("AC Asset", "read", doc)` theo DocPerm `AC Asset` (KHÔNG hardcode role-name).
- **Cap-set version (lesson IMM-14):** thêm 6 cap `asset.*` → `len(CAPABILITY_MAP)` 89→95 → `CAP_SET_VERSION` `v89.2df4c16c2bbd` → `v95.3388ee5629c1`. **D6 (Vòng 3) thêm 2 cap `asset.print`+`asset.qr.rotate`** → 95→**97** → `CAP_SET_VERSION` **`v95.3388ee5629c1` → `v97.c30c69b8974d`** (giá trị hiện hành). Hệ quả wiring (xem III.1c-3):
  - BE: `after_migrate` (`assetcore.setup.install.after_migrate`, đã wired install.py:156) gọi `rbac.invalidate_capabilities()` bust `ac_caps::*` → user lấy cap-set mới (có `asset.*`) ngay lần gọi đầu sau migrate.
  - FE: hằng số `auth.ts::CAP_SET_VERSION` PHẢI bump khớp giá trị BE mới → `isCapCacheStale()` bỏ persisted-caps cũ (rỗng `asset.*`) lúc init → nút/route `asset.read` hoạt động KHÔNG cần xóa localStorage tay.
- **Acceptance guard:** `from assetcore.services.shared.rbac import CAPABILITY_MAP; assert "asset.read" in CAPABILITY_MAP`.

### III.1c-2. Hàm — contract chuẩn (stale-safe)

| Hàm | Signature | Trả | Hành vi BẮT BUỘC |
|---|---|---|---|
| `can` | `(cap: str, doc=None) -> bool` | bool | **Cap LẠ (không có trong `CAPABILITY_MAP`) → trả `False`** (dùng `CAPABILITY_MAP.get(cap)`), TUYỆT ĐỐI KHÔNG `KeyError`. Cap hợp lệ → `bool(frappe.has_permission(dt, ptype, doc))`. |
| `require` | `(cap: str, doc=None) -> None` | None | `if not can(cap): frappe.throw(_("Khong du quyen: {0}").format(cap), frappe.PermissionError)` → **HTTP 403** VI, KHÔNG 500. Cap lạ đi qua `can()=False` → cũng 403 (deny-by-default), KHÔNG KeyError. |
| `get_capabilities` | `(user=None) -> dict[str,bool]` | dict | Resolve TOÀN BỘ key trong `CAPABILITY_MAP`. Cache Redis `ac_caps::<user>` TTL **3600s** (1h). Cache-hit → trả ngay; miss → compute `{c: can(c) for c in CAPABILITY_MAP}` rồi set. |
| `invalidate_capabilities` | `(user=None) -> None` | None | `user` set → `delete_value(ac_caps::<user>)`; `user=None` → `delete_keys("ac_caps::*")` (bust toàn bộ). |

> **AC1 fix (no-500 on unknown cap):** thay `dt, ptype = CAPABILITY_MAP[cap]` (fail-loud KeyError → 500) bằng:
> ```python
> def can(cap: str, doc=None) -> bool:
>     binding = CAPABILITY_MAP.get(cap)
>     if binding is None:
>         return False          # cap lạ → deny, KHÔNG KeyError→500
>     dt, ptype = binding
>     return bool(frappe.has_permission(dt, ptype, doc=doc))
> ```
> Lý do đổi từ fail-loud → deny-safe: cap lạ chỉ xảy ra khi worker gunicorn cũ chưa nạp `CAPABILITY_MAP` mới (deploy chưa reload). Fail-loud biến lỗi-vận-hành thành HTTP 500 traceback lọt UI (vi phạm "KHÔNG leak Internal Server Error"). Deny-safe = đúng ngữ nghĩa RBAC (không biết cap ⇒ không cấp) + trả 403 VI sạch.

### III.1c-3. Cache-bust on deploy (AC2)

Cache Redis `ac_caps::*` TTL 1h ⇒ sau khi thêm capability mới (vd `decommission.*`) hoặc đổi DocPerm, FE có thể chờ tới 1h mới thấy cap mới. Fix: `after_migrate` PHẢI bust cache.

- **`assetcore/setup/install.py::after_migrate()`** thêm bước cuối:
  ```python
  from assetcore.services.shared import rbac
  rbac.invalidate_capabilities()   # bust ac_caps::* — cap mới có hiệu lực lần gọi đầu sau migrate
  ```
- Đặt SAU `_apply_rbac_matrix()` / `_apply_core_permissions()` (đảm bảo DocPerm đã sync rồi mới xóa cache cũ).
- **Invariant:** sau `bench migrate`, `get_capabilities(<user có DocPerm Asset Decommission>)` trả dict CHỨA `decommission.read/create/approve = True` ngay **lần gọi đầu**, KHÔNG đợi TTL.
- Cache vẫn được bust khi đổi Role/Has Role/Role Profile runtime qua hook `role_hooks.invalidate_caps` (đã có ở `hooks.py` cho `User.on_update/on_trash`, `Has Role`, `Role Profile`). `after_migrate` phủ trường hợp deploy code (map đổi) mà runtime hook KHÔNG bắt được.

### III.1c-4. Delta thiết kế (so với bản trước)

| Hành vi cũ (gãy) | Hành vi mới (stale-safe) | AC |
|---|---|---|
| `can()` dùng `CAPABILITY_MAP[cap]` → KeyError → HTTP 500 khi cap lạ | `.get()` → trả `False` (deny) | AC1 |
| `require()` cap lạ → 500 traceback | qua `can()=False` → `PermissionError` 403 VI | AC1 |
| `after_migrate` KHÔNG bust `ac_caps::*` → cap mới chờ TTL 1h | `after_migrate` gọi `invalidate_capabilities()` | AC2 |
| TTL 1h cho cap hợp lệ | **GIỮ NGUYÊN** 1h (không regression AC5) | AC5 |

### III.1c-6. SSoT nhãn VI — `assetcore/services/shared/labels.py` (A6 — chống leak mã EN)

> **Đề mục A6.** Payload `get_asset_scan_info` trả `lifecycle_status_label` + `last_maintenance.event_type_label` bằng tiếng Việt — **KHÔNG leak mã EN thô** ra UI mobile. Hiện FE có `constants/labels.ts` (SSoT phía FE) và `api/dashboard.py::_STATUS_LABELS_VI` (map module-local) → **2 nguồn rời rạc, dễ drift**. A6 promote 1 SSoT BE dùng chung.

**File MỚI `assetcore/services/shared/labels.py`** (chỉ là map hằng + getter — KHÔNG I/O, KHÔNG DB):
```python
# SSoT nhãn VI cho AC Asset.lifecycle_status — đồng bộ FE constants/labels.ts::LIFECYCLE_STATUS_LABEL.
LIFECYCLE_STATUS_LABEL_VI: dict[str, str] = {
    "Active":          "Đang hoạt động",
    "Under Maintenance": "Đang bảo trì",
    "Under Repair":    "Đang sửa chữa",
    "Calibrating":     "Đang hiệu chuẩn",
    "Out of Service":  "Ngừng hoạt động",
    "Commissioned":    "Đã đưa vào sử dụng",
    "Decommissioned":  "Đã thanh lý",
}

# SSoT nhãn VI cho Asset Lifecycle Event.event_type (chỉ các loại bảo trì A6 dùng + thông dụng).
LIFECYCLE_EVENT_LABEL_VI: dict[str, str] = {
    "pm_completed":       "Hoàn tất bảo trì định kỳ",
    "repair_completed":   "Hoàn tất sửa chữa",
    "calibration_passed": "Hiệu chuẩn đạt",
    # (mở rộng dần khi surface khác cần)
}

def status_label_vi(status: str) -> str:
    """Nhãn VI cho lifecycle_status; fallback = mã gốc (KHÔNG rỗng, KHÔNG raise)."""
    return LIFECYCLE_STATUS_LABEL_VI.get(status or "", status or "")

def event_label_vi(event_type: str) -> str:
    """Nhãn VI cho event_type; fallback = mã gốc."""
    return LIFECYCLE_EVENT_LABEL_VI.get(event_type or "", event_type or "")
```

**Quy tắc:**
- `build_asset_scan_info` import từ đây (`from assetcore.services.shared.labels import status_label_vi, event_label_vi`).
- **Fallback = mã gốc** (KHÔNG để rỗng): status enum mới chưa map → vẫn hiển thị mã thay vì trống (degrade an toàn). Bổ sung key khi thêm enum.
- **Chống drift (light-touch, KHÔNG bắt buộc refactor cùng vòng):** `dashboard.py::_STATUS_LABELS_VI` NÊN re-export từ `labels.py` ở vòng dọn (ghi `[ROADMAP]` — không ép trong A6 để giữ scope). FE `constants/labels.ts` giữ bản FE; 2 bản PHẢI khớp value — guard bằng test so khớp khoá/nhãn (xem 07 §A6).
- **KHÔNG** thêm DocType/field — chỉ hằng số Python.

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

### IV.3a. Patch backfill `qr_token` — ADR-001 D5 (A1, chưa scaffold)

**File:** `assetcore/patches/v3_2/008_backfill_asset_qr_token.py` · đăng ký `assetcore.patches.v3_2.008_backfill_asset_qr_token`

Sinh `qr_token` cho mọi `AC Asset` cũ/import/legacy có `qr_token` rỗng:

- `frappe.get_all("AC Asset", filters={"qr_token": ["in", ["", None]]}, pluck="name")` → mỗi asset: `generate_unique_qr_token()` (SSoT §II.1.8-COLL) → `frappe.db.set_value("AC Asset", name, "qr_token", token)` → `commit`.
- **Idempotent:** chỉ chạm asset `qr_token` rỗng → re-run = no-op.
- **Collision-safe (Vòng 17 B):** `_set_token_collision_safe(name)` DELEGATE **CÙNG** SSoT `generate_unique_qr_token()` (pre-write check `frappe.db.exists`) — KHÔNG còn tự loop `secrets.token_urlsafe` + catch Duplicate riêng (root-cause dedup: 1 bản logic collision-safe, KHÔNG 2 song song). Helper cạn-retry raise `ServiceError` → patch `log_error` + bỏ qua asset đó (best-effort, GIỮ idempotent). Import đổi: `from assetcore.services.imm00 import generate_unique_qr_token, emit_qr_generated`.
- **Lifecycle:** emit `qr_generated` event/asset (best-effort try/except — lỗi audit KHÔNG vỡ patch).
- Nguồn: [`../imm-04/ADR-001-asset-qr.md`](../imm-04/ADR-001-asset-qr.md) D5 + D1.1.

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
# Thực tế (hooks.py:382-394): 5 DocType + bộ has_permission song hành (IDOR gate).
permission_query_conditions = {
    "AC Asset":            "assetcore.permissions.ac_asset_query",
    "Incident Report":     "assetcore.permissions.incident_report_query",
    "Asset Repair":        "assetcore.permissions.asset_repair_query",
    "PM Work Order":       "assetcore.permissions.pm_work_order_query",
    "Asset Commissioning": "assetcore.permissions.asset_commissioning_query",
}
has_permission = {  # detail/IDOR gate — frappe.has_permission KHÔNG tự áp query-conditions
    "AC Asset":            "assetcore.permissions.ac_asset_has_permission",
    "Incident Report":     "assetcore.permissions.incident_report_has_permission",
    "Asset Repair":        "assetcore.permissions.asset_repair_has_permission",
    "PM Work Order":       "assetcore.permissions.pm_work_order_has_permission",
    "Asset Commissioning": "assetcore.permissions.asset_commissioning_has_permission",
}
```

> **⚠️ ĐÃ ĐỔI WIRING & PREDICATE (đính chính 2026-06-08):** wiring thực tế trỏ `assetcore.permissions.ac_asset_query` (file `permissions.py`, KHÔNG phải `permission.py`); ngoài ra còn `Incident Report`/`Asset Repair`/`PM Work Order`/`Asset Commissioning` + bộ `has_permission` (IDOR gate). Snippet cũ dưới đây (chỉ technician scope) **STALE** — thay bằng predicate chốt ở **[`ADR-IMM00-LIST-SCOPE.md`](./ADR-IMM00-LIST-SCOPE.md)**.

**`assetcore/permissions.py::ac_asset_query` (sau ADR-IMM00-LIST-SCOPE — D1/D2 chốt 2026-06-08):**

```python
# Senior (Super Admin + Manager) + Auditor → read-all (return "").
# KTV NỘI BỘ (PM/Repair/Calibration/Corrective User = _TECHNICIAN_ROLES,
#   = Role Profile "Kỹ thuật viên") → read-all (D1). KHÔNG scope responsible_technician.
# VENDOR ENGINEER (role gán thủ công cho nhân sự NCC, KHÔNG thuộc 8 Role Profile)
#   → GIỮ isolation: responsible_technician = <user> (D2 — bất biến CLAUDE.md §5).
def ac_asset_query(user=None):
    user = user or frappe.session.user
    roles = _user_roles(user)
    if _is_senior(roles) or _AUDITOR_ROLE in roles:
        return ""
    if roles & _TECHNICIAN_ROLES:           # KTV nội bộ → read-all (D1)
        return ""
    if _VENDOR_ROLE in roles:               # Vendor → isolation (D2)
        safe = _esc(user)
        return f"(`tabAC Asset`.responsible_technician = '{safe}')"
    return ""
```

> **INVARIANT `count == rows` (ADR-IMM00-LIST-SCOPE §4b):** count trong `list_assets` phải permission-aware như `get_list` → `count_with_or` dùng `frappe.get_list(..., limit_page_length=0)` (KHÔNG `frappe.db.count`/`frappe.get_all` — 2 hàm này bỏ qua `permission_query_conditions` ⟹ đếm 1430 trong khi `get_list` scoped 0 = lỗi P1 factory run2). `apply_vendor_scope` + reserved-exclusion (RC-LIST-VENDORCLOBBER) GIỮ NGUYÊN, ADR này CỘNG THÊM permission-awareness. `ac_asset_has_permission` (IDOR detail gate) sửa đồng bộ: KTV nội bộ `ptype=read` → `True` (read-all); vendor → GIỮ scope. Chi tiết role nội-bộ vs vendor + 7 invariant test: [`ADR-IMM00-LIST-SCOPE.md`](./ADR-IMM00-LIST-SCOPE.md).

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
