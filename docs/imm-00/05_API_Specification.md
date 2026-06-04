# 05 — API Specification — IMM-00 Foundation (Master / Cross-cutting)

| Mục | Giá trị |
|---|---|
| Module | IMM-00 — Foundation / Master Cross-cutting |
| Phạm vi | Foundation — cross-cutting |
| Owner | BE Lead |
| Liên kết | [04 Backend Design](./04_Backend_Design.md) · [06 Frontend Design](./06_Frontend_Design.md) |
| Base URL | `/api/method/assetcore.api.imm00` |
| Phiên bản API | 3.1.1 |
| Trạng thái | **Live ✅** — synced vs `api/imm00.py` 2026-05-19 (`list_locations` đổi fields: gộp contact, patch v3_1.007) |

---

# Phần I — Conventions & Standards

## I.1. Response Envelope

Mọi response (success và error) đều dùng format chuẩn AssetCore. Client parse `response.json().message`.

**Success (HTTP 200 — luôn luôn 200):**

```json
{
  "message": {
    "success": true,
    "data": { }
  }
}
```

**Error (HTTP 400/401/403/404/409/422/500):**

```json
{
  "message": {
    "success": false,
    "error": "Thông báo lỗi tiếng Việt",
    "code": 422
  }
}
```

> **Quy tắc bắt buộc:** KHÔNG sử dụng `{"message": {...}}` trực tiếp ở tầng nghiệp vụ — luôn wrap qua `_ok(data)` / `_err(msg, code)`.

Helper chuẩn hoá (`assetcore/utils/response.py`):

```python
def _ok(data: dict | list) -> dict:
    return {"success": True, "data": data}

def _err(msg: str, code: int = 400) -> dict:
    return {"success": False, "error": msg, "code": code}
```

## I.2. Authentication

```http
# API Token (server-to-server)
Authorization: token <api_key>:<api_secret>

# Session cookie (browser / SPA)
Cookie: sid=<session_id>
X-Frappe-CSRF-Token: <csrf_token>
```

Thiếu credential → HTTP 401. Sai Role → HTTP 403.

### I.2b. Capability resolution endpoint (RBAC — stale-safe)

FE gate UX bằng capability, KHÔNG so role-name. BE là chốt chặn thật (`rbac.require`).

| Method | Verb | Path | Auth |
|---|---|---|---|
| `assetcore.api.auth.get_capabilities` | GET | `/api/method/assetcore.api.auth.get_capabilities` | Session (mọi user đã đăng nhập) |

- **Request:** không param. Resolve cho `frappe.session.user`.
- **Response:** envelope `{success: true, data: {<cap>: <bool>, ...}}` — TOÀN BỘ key trong `CAPABILITY_MAP` (shape KHÔNG đổi qua các vòng — AC5). Ví dụ trích:
  ```json
  { "success": true, "data": {
      "pm.read": true, "pm.write": true, "pm.create": false,
      "decommission.read": true, "decommission.create": true, "decommission.approve": false
  } }
  ```
- **Cache:** server cache `ac_caps::<user>` TTL 1h (xem 04 §III.1c). Sau `bench migrate` cache bị bust → lần gọi đầu trả cap-set mới (AC2).
- **Cap LẠ:** không bao giờ xuất hiện trong response (chỉ resolve key có trong map). FE hỏi cap không tồn tại → `can()=false` (KHÔNG lỗi).
- **Version-stamp (AC4):** response GỘP thêm khóa kỹ thuật `__cap_set_version__: <int>` = hằng `CAP_SET_VERSION` ở BE (bump khi tập cap đổi số lượng/tên). FE so version để invalidate persisted-caps cũ trước render gate-button. (Khóa bắt đầu `__` → FE loại khỏi vòng lặp hiển thị cap thường.)

> **Tác động cap lạ ở mọi endpoint nhạy cảm:** mọi whitelisted method gọi `rbac.require('<cap>')` đầu hàm. Nếu cap chưa nạp ở worker → `require` deny → **HTTP 403 + message VI "Khong du quyen: <cap>"**, KHÔNG 500 KeyError. Verify: `api.imm14.create_decommission` khi `decommission.create` chưa có trong worker map → 403, KHÔNG 500.

## I.3. HTTP Status Codes

| Code | Ý nghĩa | Khi nào |
|---|---|---|
| 200 | OK | Thành công (kể cả error business — parse `success` field) |
| 400 | Bad Request | Payload sai schema / thiếu param |
| 401 | Unauthorized | Sai / hết hạn token / session |
| 403 | Forbidden | Thiếu Role |
| 404 | Not Found | Record không tồn tại |
| 409 | Conflict | Vi phạm uniqueness |
| 422 | Unprocessable Entity | Vi phạm business rule |
| 429 | Too Many Requests | Rate limit |
| 500 | Internal Server Error | Lỗi không xác định |

## I.4. Business Error Codes

| Code | HTTP | Business Rule | Mô tả |
|---|---|---|---|
| `AC-E001` | 400 | — | Asset không tồn tại |
| `AC-E002` | 422 | BR-00-02 | Transition lifecycle_status không hợp lệ |
| `AC-E003` | 403 | BR-00-05 | Asset Out of Service / Decommissioned — block operation |
| `AC-E004` | 400 | — | SLA Policy không tìm được |
| `AC-E005` | 422 | BR-00-08 | CAPA thiếu required field khi đóng |
| `AC-E006` | 422 | BR-00-06 | Calibration Lab thiếu ISO 17025 |
| `AC-E007` | 422 | BR-00-07 | SLA response_time ≥ resolution_time |
| `AC-E008` | 422 | — | Incident Critical chưa báo cáo BYT |
| `AC-E009` | 422 | — | Patient affected thiếu mô tả |
| `AC-E010` | 422 | BR-00-03 | Audit Trail SHA-256 chain bị tamper |
| `AC-E011` | 409 | — | asset_code / serial_no trùng |
| `AC-E012` | 409 | — | Device Model (model_name + manufacturer) trùng |

## I.5. Pagination

List endpoint hỗ trợ pagination qua query string:

| Param | Kiểu | Default | Max | Ghi chú |
|---|---|---|---|---|
| `page` | int | 1 | — | 1-based |
| `page_size` | int | 20 | 100 | server cap tại 100 |
| `sort` | string | `modified desc` | — | Frappe order_by syntax |

**Response shape (list):**

```json
{
  "success": true,
  "data": {
    "items": [ ],
    "page": 1,
    "page_size": 20,
    "total": 137,
    "total_pages": 7
  }
}
```

## I.6. Filter Convention

```json
{ "lifecycle_status": "Active" }
{ "next_pm_date": ["<=", "2026-05-01"] }
{ "risk_class": ["in", ["High", "Critical"]] }
{ "asset_name": ["like", "%MRI%"] }
```

## I.7. Rate Limiting

| Nhóm endpoint | Giới hạn |
|---|---|
| GET (list / detail) | 300 req/phút/user |
| POST / PUT (mutation) | 60 req/phút/user |
| Scheduler trigger (admin) | 5 req/phút/user |

Vượt hạn → HTTP 429.

---

# Phần II — Permission Matrix

| Endpoint nhóm | System Admin | Dept Head | Ops Manager | Workshop Lead | Technician | QA Officer | Doc Officer | Storekeeper |
|---|---|---|---|---|---|---|---|---|
| list/get assets | ✓ | ✓ | ✓ | ✓ | ✓ (scoped) | ✓ | ✓ | — |
| create/update asset | ✓ | ✓ | ✓ | — | — | — | — | — |
| transition_status | ✓ | ✓ | ✓ | — | — | ✓ | — | — |
| list/get supplier | ✓ | ✓ | ✓ | — | — | — | — | ✓ |
| create/update supplier | ✓ | — | ✓ | — | — | — | — | — |
| list_locations / list_departments | All | All | All | All | All | All | All | All |
| create location/dept/category | ✓ | ✓ (dept) | — | ✓ (cat) | — | — | — | — |
| list/get device_model | All | All | All | All | All | All | All | — |
| create/update device_model | ✓ | — | — | ✓ | — | — | — | — |
| list/get SLA | All | All | All | All | All | All | All | All |
| list_audit_trail / get_audit_entry | ✓ | — | — | — | — | ✓ | ✓ | — |
| verify_chain | ✓ | — | — | — | — | ✓ | — | — |
| list/get CAPA | ✓ | ✓ | ✓ | — | — | ✓ | — | — |
| open_capa | ✓ | — | ✓ | ✓ | — | ✓ | — | — |
| close_capa_record | ✓ | — | — | — | — | ✓ | — | — |
| list/get lifecycle_events | All | All | All | All | All | All | All | All |
| list/get/create/submit incident | All | All | All | All | All | All | — | All |
| scheduler triggers | ✓ | — | — | — | — | — | — | — |
| inventory endpoints | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | ✓ |

---

# Phần III — Endpoints

Base Python path: `assetcore.api.imm00.<function>`  
URL pattern: `POST|GET /api/method/assetcore.api.imm00.<function>`

---

## III.1. AC Asset (11 endpoints)

> **Thực tế từ code:** `api/imm00.py` cung cấp 11 endpoints cho AC Asset (không phải 8). Xem danh sách đầy đủ phía dưới.

### `list_assets` — Liệt kê Asset

| Thuộc tính | Giá trị |
|---|---|
| Method | GET |
| Path | `assetcore.api.imm00.list_assets` |
| Permission | IMM Department Head / Operations Manager / Technician (scoped) / Admin |

**Request params:**

```json
{
  "filters": {
    "lifecycle_status": "Active",
    "risk_class": ["in", ["High", "Critical"]],
    "department": "AC-DEPT-0001"
  },
  "page": 1,
  "page_size": 20,
  "sort": "next_pm_date asc"
}
```

**Response 200:**

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "name": "AC-ASSET-2026-00001",
        "asset_name": "MRI Siemens Magnetom Aera 1.5T",
        "asset_code": "MRI-001",
        "lifecycle_status": "Active",
        "risk_class": "High",
        "next_pm_date": "2026-04-30",
        "department": "AC-DEPT-0001"
      }
    ],
    "page": 1, "page_size": 20, "total": 1, "total_pages": 1
  }
}
```

**Query params bổ sung:**

| Param | Kiểu | Mô tả |
|---|---|---|
| `lifecycle_status` | str | Lọc theo trạng thái vòng đời |
| `department` / `location` / `asset_category` | str | Lọc theo Link field |
| `gmdn_code` | str | **Lọc thiết bị theo mã GMDN** (kế thừa từ Asset Category). Dùng cho recall/FSCA, KPI per-GMDN |
| `byt_status` | str | **Drill số ĐKLH BYT (BR-00-17 — SoT `byt_expiry_filter`).** `'expiring'` → `byt_reg_expiry ∈ [today, today+30]`; `'expired'` → `byt_reg_expiry < today`. CẢ HAI loại bản ghi `byt_reg_expiry` rỗng/NULL. Khi set → **conjoin (AND)** với mọi filter hiện có (lifecycle_status/department/…) KHÔNG clobber; `apply_vendor_scope` áp SAU. Giá trị khác → **no-op** (bỏ qua, KHÔNG throw). |
| `search` | str | Tìm theo `asset_name`, `asset_code`, `manufacturer_sn`, **`gmdn_code`** (LIKE substring) |

> **Note (2026-05-19):** Tham số lọc theo trạng thái sử dụng GMDN (cũ) đã bị loại bỏ cùng field tương ứng. Trục lọc/quản lý thiết bị nay là `gmdn_code`. Tham chiếu: [docs/res/analysis/gmdn-asset-category-analysis.md](../res/analysis/gmdn-asset-category-analysis.md) §6.

> **INVARIANT count==drill (BR-00-17 — Vòng 31):** `list_assets(byt_status='expiring')` `pagination.total` == KPI `get_overview().assets.byt_expiring_30d`; `list_assets(byt_status='expired')` `pagination.total` == `get_overview().assets.byt_expired`, byte-for-byte trên CÙNG dataset + CÙNG vendor scope (cả 2 read-path gọi SoT `byt_expiry_filter`). FE tile NĐ98 click → `/assets?byt_status=expiring\|expired`; header "Tổng N" của list == giá trị tile vừa click. KHÔNG inline literal window — xem [04 Backend §III.1a](../imm-00/04_Backend_Design.md).

---

### `get_asset` — Chi tiết Asset

| Method | GET |
|---|---|
| Path | `assetcore.api.imm00.get_asset` |

**Request:** `?name=AC-ASSET-2026-00001`

**Response 200** — đầy đủ HTM fields (asset_name, udi_code, gmdn_code, byt_reg_no, byt_reg_expiry, lifecycle_status, risk_classification, next_pm_date, next_calibration_date, commissioning_date, …).

**Errors:** 404 (`AC-E001`), 401, 403.

---

### `create_asset` — Tạo Asset mới

| Method | POST |
|---|---|
| Path | `assetcore.api.imm00.create_asset` |
| Permission | IMM System Admin / Department Head / Operations Manager |

**Required body:** `asset_name, asset_code, device_model, asset_category, department, location`

Khi `device_model` được set → auto-fetch `risk_class`, `gmdn_code`, `pm_interval_days`, `is_calibration_required` từ IMM Device Model qua `fetch_from`.

> **GMDN propagation (BR-00-13/14):** `gmdn_code` trên AC Asset được populate tự động từ `device_model.gmdn_code`. Không nhập tay trực tiếp — đây là field `fetch_from`. Để thay đổi `gmdn_code` của Asset, đổi `device_model` hoặc cập nhật `gmdn_code` trên Device Model tương ứng.

**Response 200:** `{ "success": true, "data": { "name": "AC-ASSET-2026-00001" } }`

**Errors:** 409 `AC-E011` (trùng asset_code/serial_no), 422 validation.

---

### `update_asset` — Cập nhật Asset

| Method | POST |
|---|---|
| Path | `assetcore.api.imm00.update_asset` |

**Body:** `{ "name": "AC-ASSET-..." }` + bất kỳ field nào cần cập nhật (trừ `lifecycle_status`).

> Muốn đổi trạng thái vòng đời phải dùng `transition_status` (BR-00-02).

---

### `transition_status` — Đổi lifecycle_status

| Method | POST |
|---|---|
| Path | `assetcore.api.imm00.transition_status` |
| Permission | IMM Department Head / Operations Manager (validated bởi service layer) |

**Body:**

```json
{
  "name": "AC-ASSET-2026-00001",
  "to_status": "Under Repair",
  "reason": "Incident IR-2026-0007 — tube cooling failure"
}
```

**Response 200:**

```json
{
  "success": true,
  "data": {
    "name": "AC-ASSET-2026-00001",
    "lifecycle_status": "Under Repair"
  }
}
```

**Errors:** 404 (asset not found), 422 (invalid transition — BR-00-02), 422 (NEG-09: chặn thanh lý khi asset đang `Under Maintenance/Under Repair/Calibrating`).

> **Khi `to_status='Decommissioned'` (BR-00-24 / RC-07 — Vòng 8):** ngoài đổi status + sinh event `decommissioned`, service tự **chốt sổ khấu hao**: hủy MỌI kỳ `AC Asset Depreciation Schedule.status='Pending'` → `'Cancelled'` (`Executed` bất biến). Nếu hủy ≥1 kỳ → sinh thêm 1 Asset Lifecycle Event `event_type='depreciation_stopped'` + 1 IMM Audit Trail `System`. Response shape KHÔNG đổi (vẫn `{name, lifecycle_status}`) — hệ quả chỉ phản ánh qua `get_depreciation_schedule` (`pending_periods=0` sau đó) và `get_asset_timeline` (có thêm event `depreciation_stopped`). Best-effort: lỗi audit KHÔNG làm transition fail.

> **Khi `to_status='Out of Service'` (BR-00-25 / RC-08 — Vòng 9):** ngoài đổi status + sinh event `out_of_service`, service **TẠM DỪNG** khấu hao: trong suốt thời gian asset Out of Service, executor `run_due_depreciation` KHÔNG trích kỳ nào của asset (`accumulated_depreciation`/`current_book_value` bất biến). KHÔNG hủy kỳ (khác Decommissioned) — kỳ Pending GIỮ nguyên, chờ dời lịch khi khôi phục. Best-effort: ghi thêm 1 ALE `out_of_service` note `'depreciation paused'`. Response shape KHÔNG đổi (`{name, lifecycle_status}`).

> **Khi `to_status='Active'` từ `prev_status='Out of Service'` (BR-00-25 / RC-08 — Vòng 9; nhãn event sửa RC-09 / BR-00-27 — Vòng 14):** service sinh **ĐÚNG 1** Asset Lifecycle Event `event_type='restored'` (KHÔNG `activated`) cho transition này — do `transition_asset_status` emit theo (from=`Out of Service`, to=`Active`) qua `_lifecycle_event_for(to, from)`. Ngoài đổi status, service **DỜI LỊCH** khấu hao: mọi kỳ `status='Pending'` được dời `scheduled_date += oos_days` (`oos_days = restore_date − oos_start_date`), GIỮ NGUYÊN `depreciation_amount`/`period_number`/số kỳ; `Executed`/`Cancelled` bất biến. **Diệt phantom catch-up:** các kỳ idle quá hạn trong lúc OoS KHÔNG bị `run_due_depreciation(today)` trích bù 1 lần — chỉ kỳ đến hạn SAU restore (sau dời) mới trích. **RC-09 (Vòng 14):** helper RESCHEDULE **KHÔNG còn** emit ALE `restored` (trước đây ⇒ double-emit) — chỉ best-effort 1 IMM Audit Trail `State Change` (note nêu số kỳ dời + oos_days). ⟹ **bất kể** có kỳ Pending để dời hay không, transition luôn sinh ĐÚNG 1 `restored` + 0 `activated` (consistency). `oos_start_date` không xác định (thiếu downtime log + ALE) → no-op an toàn, KHÔNG raise. Response shape KHÔNG đổi (`{name, lifecycle_status}`) — hệ quả phản ánh qua `get_depreciation_schedule` (`scheduled_date` các kỳ Pending đã dời) + `get_asset_timeline` (ĐÚNG 1 event `restored`). **Lưu ý:** chỉ nhánh `Active` **từ** `Out of Service` mới dời lịch + nhãn `restored`; `Active` từ `Under Repair`/`Calibrating`/`Under Maintenance`/`Commissioned` KHÔNG dời + giữ nhãn `activated` (các đường đó không pause khấu hao).

---

### `get_asset_timeline` — Lịch sử vòng đời

| Method | GET |
|---|---|
| Path | `assetcore.api.imm00.get_asset_timeline` |

**Params:** `name, page=1, page_size=50`

Trả về paginated `Asset Lifecycle Event[]` sorted desc theo timestamp.

---

### `validate_for_operations` — Kiểm tra thiết bị hoạt động được

| Method | GET |
|---|---|
| Path | `assetcore.api.imm00.validate_for_operations` |

**Params:** `?name=AC-ASSET-...`

**Response 200:** `{ "valid": true }` hoặc `{ "valid": false, "reason": "..." }`

---

### `get_asset_kpi` — KPI thiết bị

| Method | GET |
|---|---|
| Path | `assetcore.api.imm00.get_asset_kpi` |

**Params:** `?name=AC-ASSET-...`

**Response 200:** `{ uptime_pct, mtbf_days, mttr_hours, pm_compliance_pct, total_repair_cost, next_pm_date, next_calibration_date, byt_reg_expiry }`

---

### `delete_asset` — Xóa Asset

| Method | POST |
|---|---|
| Path | `assetcore.api.imm00.delete_asset` |

**Body:** `{ "name": "AC-ASSET-..." }`

> Endpoints không còn tồn tại (được loại khỏi spec): `search_assets_by_udi`, `get_assets_due_pm`, `get_asset_lifecycle_history` — không có trong `api/imm00.py`.

---

## III.2. AC Supplier (4 endpoints)

### `list_suppliers`

GET `assetcore.api.imm00.list_suppliers`

Filters: `vendor_type`, `is_active`, `contract_end` (operator syntax).

### `get_supplier`

GET `assetcore.api.imm00.get_supplier?name=AC-SUP-2026-0001`

Trả chi tiết + `authorized_technicians` child table.

**Response 200 example:**

```json
{
  "success": true,
  "data": {
    "name": "AC-SUP-2026-0001",
    "supplier_name": "Siemens Healthineers VN",
    "vendor_type": "Service Provider",
    "contract_end": "2026-12-31",
    "authorized_technicians": [
      { "technician_name": "Nguyễn Văn A", "cert_no": "SIE-TECH-001", "cert_expiry": "2027-06-30" }
    ]
  }
}
```

### `create_supplier`

POST. Body required: `supplier_name, vendor_type`.

Nếu `vendor_type = "Calibration Lab"` mà thiếu `iso_17025_cert` → warning (không block) trả `data.warnings[{code: "AC-E006", message: "..."}]`.

### `update_supplier`

POST `assetcore.api.imm00.update_supplier`. Body: `name` (param) + fields cần cập nhật.

---

## III.3. Location / Department / Asset Category (9 endpoints)

> **Thực tế từ code:** Mỗi entity có GET (list) + GET (detail) + POST (create) + POST (update) + POST (delete) = 5 endpoints/entity. Một số đã implement đầy đủ CRUD.

### `list_locations`

GET `assetcore.api.imm00.list_locations` — Params: `parent` (optional). Trả flat list với fields: `name, location_name, location_code, parent_location, is_group, clinical_area_type, infection_control_level, power_backup_available, dept_head, contact_phone, notes` (+ enrich `dept_head_name` từ User.full_name).

> **Đổi schema (2026-05-19):** 3 trường liên hệ cũ (`emergency_contact`, `dept_head`, `technical_contact`) được gộp còn 2: `dept_head` (Link → User, label "Người phụ trách") + `contact_phone` (Data, `fetch_from: dept_head.phone`, label "Số liên hệ"). Migrate qua patch `v3_1.007_ac_location_simplify_contacts`. Xem README §Changelog.

### `get_location`

GET `assetcore.api.imm00.get_location?name=...`

### `create_location`

POST. Body: `location_name` (required) + optional fields.

### `update_location`

POST. Body: `{ "name": "...", ...fields }`

### `delete_location`

POST. Body: `{ "name": "..." }` — block nếu có asset đang link.

### `list_departments`

GET `assetcore.api.imm00.list_departments` — Params: `parent` (optional).

### `get_department` / `create_department` / `update_department` / `delete_department`

Pattern tương tự locations.

### `list_asset_categories`

GET `assetcore.api.imm00.list_asset_categories` — Flat list. Fields: `name, category_name, gmdn_code, description, default_pm_required, default_pm_interval_days, default_calibration_required, default_calibration_interval_days, default_depreciation_method, total_depreciation_months, depreciation_frequency, default_residual_value_pct, has_radiation, is_active`.

### `get_asset_category` / `create_asset_category` / `update_asset_category` / `delete_asset_category`

Pattern tương tự locations.

`create_asset_category` body: `category_name` (required) + optional fields bao gồm `gmdn_code`.

> `gmdn_code` tại đây là **nguồn kế thừa** — tất cả `IMM Device Model` thuộc danh mục này sẽ kế thừa giá trị này khi tạo mới (nếu chưa nhập tay). Xem BR-00-13.

---

## III.4. IMM Device Model (4 endpoints)

### `list_device_models`

GET. Filters: `manufacturer`, `asset_category`, `class` (I/II/III), `risk_class`, `gmdn_code`, `is_active`.

### `get_device_model`

GET `?name=IMM-MDL-2026-0001` → chi tiết + `spare_parts_list` child table.

### `create_device_model`

POST. Required: `model_name, manufacturer, asset_category, class`.

Validation BR-00-01: `class ↔ risk_class` mapping bắt buộc.

> **GMDN inheritance (BR-00-13):** Nếu `gmdn_code` không được cung cấp trong body, hệ thống tự động kế thừa từ `asset_category.gmdn_code` tại `before_insert`. Người dùng có thể override bằng cách truyền `gmdn_code` tường minh.

### `update_device_model`

POST `assetcore.api.imm00.update_device_model`. Body: `name` (param) + fields cần cập nhật.

---

## III.5. IMM SLA Policy (5 endpoints — full CRUD + lookup)

### `list_sla_policies`

GET `assetcore.api.imm00.list_sla_policies` — Params: `priority, risk_class, is_active` (tất cả optional). Trả không paginated. Fields: `name, policy_name, priority, risk_class, is_default, is_active, response_time_minutes, resolution_time_hours`.

### `get_sla_policy` — Lấy chi tiết 1 policy

GET `assetcore.api.imm00.get_sla_policy?name=...` — Trả full policy fields.

### `resolve_sla_policy` — Lookup SLA theo priority × risk_class

GET `assetcore.api.imm00.resolve_sla_policy?priority=P2+Urgent&risk_class=High`

Logic: exact match `(priority, risk_class)` → fallback `is_default=1` cùng priority.

**Response 200:**

```json
{
  "success": true,
  "data": {
    "name": "SLA-P2-High",
    "priority": "P2 Urgent",
    "risk_class": "High",
    "response_time_minutes": 60,
    "resolution_time_hours": 8,
    "is_default": 0
  }
}
```

**Errors:** 404 nếu không tìm được cả exact lẫn default.

### `create_sla_policy` / `update_sla_policy` / `delete_sla_policy`

POST CRUD. Body check fields (`is_active`, `is_default`) được coerce sang int 0/1 tự động.

---

## III.6. IMM Audit Trail (3 endpoints — read-only)

> Audit Trail là read-only qua API. Mọi record sinh từ service `log_audit_event()` nội bộ.

### `list_audit_trail`

GET `assetcore.api.imm00.list_audit_trail`. Params: `asset? (AC Asset name), q? (free-text search), page, page_size`.

Response items: `name, asset, asset_name, event_type, actor, change_summary, from_status, to_status, ref_doctype, ref_name, timestamp, hash`.

### `get_audit_entry`

GET `assetcore.api.imm00.get_audit_entry?name=IMM-AUD-...`. Chi tiết full payload.

### `verify_chain`

GET `assetcore.api.imm00.verify_chain?asset=AC-ASSET-...`

Duyệt toàn bộ audit trail của asset, tính lại SHA-256 chain.

**Response 200:** `{ "valid": true/false, "count": N, "broken_at": "IMM-AUD-..." (nếu có) }`

**Response 200 (OK):**

```json
{
  "success": true,
  "data": {
    "asset": "AC-ASSET-2026-00001",
    "verified": true,
    "total_records": 137,
    "first_record": "IMM-AUD-2024-0000001",
    "last_record": "IMM-AUD-2026-0001234"
  }
}
```

**Response 200 (tamper detected):**

```json
{
  "success": true,
  "data": {
    "verified": false,
    "tampered_at": "IMM-AUD-2025-0000789",
    "expected_hash": "a1b2c3...",
    "actual_hash": "ffee00..."
  }
}
```

Kể cả tampered vẫn trả HTTP 200 — frontend xử lý alert. Service tự tạo 1 record `"Integrity Violation"` (`AC-E010`) và email QA Officer.

---

## III.7. IMM CAPA Record (5 endpoints)

### `list_capas`

GET `assetcore.api.imm00.list_capas`. Filters: `status, capa_type, asset`. Paginated.

**Virtual drill filters (SoT — KHÔNG inline literal):**
- `not_closed=1` → **conjoin (AND) SoT `_open_capa_filter()`** (services/imm00): `status NOT IN ('Closed')`. Drill total BẰNG KPI `capa_open` (dashboard.py) == scorecard `capa_open_count` == quality-dash `capa_open` == `get_capa_aging.total_open`, byte-for-byte trên cùng dataset (khi KHÔNG có explicit status). CAPA `Overdue` VẪN nằm trong tập (open ⊇ overdue) → count bất biến sau cron flip Open→Overdue.
- `overdue=1` → **conjoin (AND) SoT `_overdue_capa_filter()`**: `status NOT IN ('Closed') AND due_date IS NOT NULL AND due_date < today` (strict `<`). Khi cả hai cờ cùng gửi, `overdue` thắng `not_closed` (overdue ⊂ open) — chỉ áp `_overdue_capa_filter()`.

**BR-00-16 — Filter composition (conjoin, KHÔNG clobber):** explicit `status` (giá trị enum, vd `Overdue`/`Open`/`Closed`) và virtual filter `not_closed`/`overdue` đặt điều kiện trên CÙNG field `status`. Một Frappe **dict-filter KHÔNG biểu diễn được 2 điều kiện trên cùng 1 field** (key trùng → ghi đè). Do đó endpoint PHẢI build filter dạng **list-of-conditions** `[[doctype, field, op, value], ...]` để cả `["status", "=", status]` (explicit) VÀ `["status", "not in", ["Closed"]]` (virtual) cùng tồn tại = **AND thật**. TUYỆT ĐỐI KHÔNG `dict.update(_open_capa_filter())` đè lên `filters["status"]` (= clobber → đổi AND thành either-or, trả nhầm full open-set).

| Request | Tập kết quả (AND đúng) | Lý do |
|---|---|---|
| `?not_closed=1&status=Overdue` | `(status NOT IN [Closed]) ∧ (status == 'Overdue')` = các CAPA `Overdue` | giao 2 điều kiện; KHÔNG ra full open-set |
| `?not_closed=1&status=Closed` | `(status NOT IN [Closed]) ∧ (status == 'Closed')` = **0 rows** | tập rỗng — minh chứng AND thật, không bị clobber thành either-or |
| `?overdue=1&status=Open` | `(due_date<today flip→'Overdue') ∧ (status == 'Open')` = **0 rows** | `Open` không nằm trong tập đã flip `Overdue` → AND không giao |
| `?not_closed=1` (không status) | `_open_capa_filter()` byte-for-byte | no-regression — khớp KPI `capa_open` |
| `?overdue=1` (không status) | `_overdue_capa_filter()` byte-for-byte | no-regression — khớp KPI `capa_overdue` (round 10/11) |

**INVARIANT count==drill:** `pagination.total` (qua `frappe.db.count`) và `items` (qua `frappe.get_list`) PHẢI dùng CÙNG bộ filter đã conjoin cho MỌI tổ hợp `{status} × {not_closed | overdue | none}` → `pagination.total == len(items)` (trên cùng trang khi đủ chứa). FE `CAPAListView` gửi `status=CODE` + `not_closed/overdue` đồng thời → số "Tổng N hồ sơ" == số dòng render (không còn "chọn status=Quá hạn mà vẫn 117").

### `get_capa`

GET `assetcore.api.imm00.get_capa?name=CAPA-...` → full CAPA fields.

### `open_capa` — Tạo CAPA mới

POST `assetcore.api.imm00.open_capa`. Body required: `asset, severity, description, responsible`. Optional: `source_type (default: Nonconformance), source_ref, due_days (default: 30)`.

**Response 200:** `{ "success": true, "data": { "name": "CAPA-2026-00007" } }`

### `close_capa_record` — Đóng CAPA

POST `assetcore.api.imm00.close_capa_record`. Body: `name` (param) + `root_cause, corrective_action, preventive_action` (required) + `effectiveness_check` (**bắt buộc để đóng** — phải = `Effective`; xem cổng VR-06/VR-07).

```json
{
  "root_cause": "Worn bearing in cooling pump",
  "corrective_action": "Replaced bearing per OEM SOP",
  "preventive_action": "Shorten PM interval from 6m to 3m",
  "effectiveness_check": "Effective"
}
```

> **round 12 — `effectiveness_check` là enum đóng cổng, KHÔNG phải free-text.** Giá trị hợp lệ: `Effective` / `Partially Effective` / `Not Effective`. CHỈ `Effective` cho phép đóng (VR-07). null/rỗng → VR-06 chặn.

**Response 200:** `{ "name": "CAPA-...", "status": "Closed" }`

**Errors:**
- `422 VALIDATION` — thiếu `root_cause / corrective_action / preventive_action` (BR-00-08). *(check sớm, message "Thiếu trường bắt buộc: ...")*.
- `422 VALIDATION` + `message_code: "FIN-007"` — **round 12 (cổng hiệu quả):**
  - `effectiveness_check` null/thiếu → VR-06: *"Phải xác minh hiệu quả (effectiveness_check) trước khi đóng CAPA."* CAPA KHÔNG chuyển Closed, KHÔNG submit.
  - `effectiveness_check ∈ {Not Effective, Partially Effective}` → VR-07: *"effectiveness_check phải = 'Effective' để đóng CAPA"*. KHÔNG đóng.

> **BE delta bắt buộc (round 12):** `api/imm00.py::close_capa_record` hiện **chỉ** `except frappe.exceptions.ValidationError` (line 1020) → `ServiceError` từ `assert_capa_effectiveness_gate` sẽ KHÔNG bị bắt và thoát ra 500. PHẢI thêm `except ServiceError as e: return _err(e.message, e.code, message_code=e.message_code)` **trước** nhánh `ValidationError`. Như vậy envelope trả `code=VALIDATION` (422) + `message_code=FIN-007` → FE match được.

### `list_overdue_capas`

GET `assetcore.api.imm00.list_overdue_capas`. Paginated. **Filter = SoT `_overdue_capa_filter()`** (services/imm00): `status NOT IN ('Closed') AND due_date IS NOT NULL AND due_date < today` (strict `<`; `due_date == today` CHƯA quá hạn). KHÔNG inline predicate. Drill rows BẰNG KPI `capa_overdue` (dashboard.py) và `imm16.get_overdue_actions().overdue_capas` trên cùng dataset. CAPA status `Overdue` VẪN xuất hiện (NOT IN Closed) → count bất biến sau cron flip.

---

## III.8. Asset Lifecycle Event (2 endpoints — read-only)

> Read-only. Event sinh tự động bởi service `create_lifecycle_event()` / `transition_asset_status()`.

### `list_lifecycle_events`

GET `assetcore.api.imm00.list_lifecycle_events`. Params: `asset` (required), `page, page_size, event_type` (optional).

Event types (từ `_lifecycle_event_for()` trong services/imm00.py): `activated, commissioned, pm_started, repair_opened, calibration_started, out_of_service, decommissioned, restored, transferred`. Ngoài state-change, các event khấu hao sinh trực tiếp: `depreciated` (cron chạy kỳ), `depreciation_rules_inherited` (kế thừa luật từ Category), `depreciation_stopped` (**MỚI Vòng 8 / BR-00-24** — thanh lý hủy kỳ Pending còn lại). Toàn bộ giá trị này PHẢI nằm trong Select `event_type` của DocType `Asset Lifecycle Event`.

### `get_lifecycle_event`

GET `assetcore.api.imm00.get_lifecycle_event?name=...` → full event fields.

---

## III.9. Incident Report (6 endpoints)

### `list_incidents`

GET `assetcore.api.imm00.list_incidents`. Params: `status, severity, asset, page, page_size`.

### `get_incident`

GET `assetcore.api.imm00.get_incident?name=IR-...` → full Incident fields.

### `create_incident`

POST `assetcore.api.imm00.create_incident`. Required: `asset, severity, incident_type, description`.

### `update_incident`

POST `assetcore.api.imm00.update_incident`. Body: `name` (param) + fields cần cập nhật.

### `submit_incident`

POST `assetcore.api.imm00.submit_incident`. Body: `{ "name": "IR-..." }`

**Response 200:** `{ "name": "IR-...", "status": "..." }` (status từ doc sau khi submit).

**Errors:** 422 nếu đã submit rồi.

### `delete_incident`

POST `assetcore.api.imm00.delete_incident`. Body: `{ "name": "IR-..." }`.

> **Không còn tồn tại:** `close_incident` — không có trong `api/imm00.py`. Đóng Incident thực hiện qua `update_incident` + `submit_incident`.

---

## III.10. (Đã loại bỏ — GMDN Status)

> **Note (2026-05-19):** Nhóm endpoint quản lý trạng thái sử dụng GMDN (cũ) đã bị loại bỏ cùng field tương ứng trên `AC Asset`. Quản lý thiết bị nay theo `gmdn_code`. Lọc thiết bị qua `list_assets?gmdn_code=...`. Tham chiếu: [docs/res/analysis/gmdn-asset-category-analysis.md](../res/analysis/gmdn-asset-category-analysis.md) §6.

---

## III.12. Asset Transfer (6 endpoints)

### `list_transfers` / `get_transfer` / `create_transfer` / `delete_transfer`

CRUD cơ bản. `delete_transfer` thực ra là cancel (chỉ khi Pending/Rejected).

### `approve_transfer` / `reject_transfer` / `receive_transfer`

Workflow endpoints — POST với body `{ "name": "..." }`.

### `get_transfer_full` / `update_transfer`

GET chi tiết + POST update (chỉ khi Pending Approval).

---

## III.13. Service Contract (5 endpoints)

`list_service_contracts`, `get_service_contract`, `create_service_contract`, `update_service_contract`, `delete_service_contract` + `list_asset_contracts` (GET contracts của 1 asset).

---

## III.14. PM Schedule (5 endpoints)

`list_pm_schedules`, `get_pm_schedule`, `create_pm_schedule`, `update_pm_schedule`, `delete_pm_schedule`. Served bởi `assetcore.api.imm00`.

---

## III.15. PM Checklist Template (5 endpoints)

`list_pm_templates`, `get_pm_template`, `create_pm_template`, `update_pm_template`, `delete_pm_template`.

> **Lưu ý:** FE client (`frontend/src/api/imm00.ts`) route các PM Template endpoints sang `assetcore.api.imm08` (service-based xử lý checklist_items JSON), nhưng BE có cả 2 implementations.

### `list_pm_templates` — GET

| Method | GET |
|---|---|
| Path | `assetcore.api.imm00.list_pm_templates` |
| Params | `page=1, page_size=50` |
| Permission | All IMM roles |

Response: paginated list `PmTemplate{name, template_name, asset_category?, pm_type?, version?, checklist_items?}`.

### `get_pm_template` / `create_pm_template` / `update_pm_template` / `delete_pm_template`

CRUD pattern. POST body: `{ "name": "..." }` + fields.

**Errors:** `AC-E001` (404), `AC-E011` (409 trùng template_name + version).

---

## III.16. Firmware Change Request (5 endpoints)

`list_firmware_crs`, `get_firmware_cr`, `create_firmware_cr`, `update_firmware_cr`, `delete_firmware_cr`.

### `list_firmware_crs` — GET

| Method | GET |
|---|---|
| Path | `assetcore.api.imm00.list_firmware_crs` |
| Params | `page=1, page_size=20, status?, asset?` |

Response items: `FirmwareCR{name, asset_ref, version_before?, version_after?, status?, ...}`.

### `get_firmware_cr` — GET `?name=...`

### `create_firmware_cr` — POST

Body required: `asset_ref` (Link AC Asset), `version_after`. Optional: `version_before`, `status`, attachments.

**Response 200:** `{ "name": "FCR-..." }`.

**Errors:** 422 nếu thiếu `asset_ref`.

### `update_firmware_cr` / `delete_firmware_cr`

POST. Body `{ "name": "..." }` + update fields (resp. `{ "name": "..." }` for delete).

---

## III.17. Document Request (5 endpoints)

`list_document_requests`, `get_document_request`, `create_document_request`, `update_document_request`, `delete_document_request`.

### `list_document_requests` — GET

| Method | GET |
|---|---|
| Path | `assetcore.api.imm00.list_document_requests` |
| Params | `page=1, page_size=20, status?, asset?` |

Response items: `DocumentRequest{name, asset_ref, doc_type_required, status?, priority?, ...}`.

### `get_document_request` / `create_document_request` / `update_document_request` / `delete_document_request`

Standard CRUD. `create` requires: `asset_ref`, `doc_type_required`. Returns `{ "name": "DR-..." }`.

**Errors:** 422 thiếu required; 404 (`AC-E001`) khi không tìm thấy.

---

## III.18. Depreciation (9 endpoints)

### `compute_depreciation` (POST)

Body: `name` (AC Asset). Trả `{ accumulated, book_value, method?, days_elapsed?, note? }`.

> **`book_value` qua SoT `effective_book_value` (BR-05-13 / RC-06).** `book_value` suy bằng SoT DUY NHẤT `services/depreciation.py::effective_book_value(asset_row)` — KHÔNG idiom falsy `current_book_value or gross`. Asset đã khấu hao **hết** về `current_book_value=0.0` (residual=0) → trả **`0.0`** (đúng), KHÔNG phantom `gross`. Asset CHƯA chạy KH (`current_book_value IS NULL`) → trả `gross` (no regression).

### `get_depreciation_schedule` (GET)

Params: `asset_name`. Trả `{ asset, asset_info, rows[], summary{total_periods, executed_periods, pending_periods, total_depreciated} }`.

> **Sau thanh lý (BR-00-24 / RC-07 — Vòng 8):** với asset đã `Decommissioned`, các kỳ Pending đã được chuyển sang `Cancelled` ⇒ `summary.pending_periods == 0`. Các dòng `Cancelled` VẪN xuất hiện trong `rows[]` (`status='Cancelled'`) — KHÔNG bị xoá; chỉ không còn được đếm vào `pending_periods` và không bị cron chạy. `executed_periods` + `total_depreciated` + `asset_info.accumulated_depreciation/current_book_value` bất biến so với trước thanh lý.

> **Sau khôi phục từ Out of Service (BR-00-25 / RC-08 — Vòng 9):** với asset đã `Out of Service → Active`, các kỳ `status='Pending'` có `scheduled_date` **đã được dời** `+= oos_days` (`rows[].scheduled_date` mới = ngày-cũ + số-ngày-ngừng). `summary.pending_periods` KHÔNG đổi (không mất/thêm kỳ), `sum(depreciation_amount)` các kỳ Pending KHÔNG đổi. `executed_periods` + `accumulated_depreciation`/`current_book_value` bất biến (PAUSE — không trích trong lúc OoS, không trích bù khi khôi phục). FE render `rows[].scheduled_date` verbatim ⇒ tự hiện ngày đã dời + banner "Kỳ tiếp theo" (`nextPendingRow`) trỏ kỳ Pending đầu tiên với `scheduled_date` mới — **zero shape-change** ở response (`get_depreciation_schedule` giữ nguyên field).

**Errors:** 404 (`AC-E001`) khi không tồn tại asset.

### `regenerate_depreciation_schedule` (POST)

Params: `asset_name, force=1`. Sinh lại schedule (xoá cũ nếu force=1). Service: `assetcore.services.depreciation.generate_schedule`.

**Luồng (RC-04 — self-heal-rồi-pre-check, Round-2):**
1. **Self-heal TRƯỚC pre-check:** `frappe.get_doc(asset)` → `inherit_depreciation_rules_from_category(asset)` (SoT round-1). Nếu `did_inherit=True` → `save(ignore_permissions=True)` + sinh audit (ALE `depreciation_rules_inherited` + IMM Audit Trail `System`).
2. **Pre-validate 4 input CHẠY LẠI SAU inherit** (method, `total_depreciation_months>0`, `gross>0`, start_date — đọc state SAU self-heal) → thiếu bất kỳ → **422** với message VI nêu rõ field thiếu (vd `Thiếu: Số tháng khấu hao (total_depreciation_months)`).
3. Pass → `generate_schedule(force)` → **200** `{periods, ...}`.

> **RC-04 (Self-Correction 2026-06-03, Round-2 — goal C):** lỗi user báo — asset CŨ (tạo TRƯỚC khi `before_insert` wire SoT) có Category CÓ luật nhưng `asset.total_depreciation_months=0` → bấm "Sinh lịch khấu hao" trả 422 oan. Fix: endpoint **TỰ kế thừa luật** từ Category qua **SoT DUY NHẤT** `inherit_depreciation_rules_from_category` TRƯỚC pre-check → **KHÔNG còn 422 "Thiếu: Số tháng khấu hao"**, sinh được schedule (`periods > 0`).
> - **KHÔNG che lỗi master-data:** Category cũng thiếu luật (`total_depreciation_months=0`) HOẶC asset không có `asset_category` → inherit no-op → **VẪN 422** liệt kê đúng field thiếu (BR-00-20/22).
> - **KHÔNG clobber user:** months/residual user đã nhập tay → inherit no-op (BR-00-19).
> - **Bảo toàn lịch sử:** asset có kỳ Executed → self-heal KHÔNG override months/residual đã chạy (BR-00-21).
> - **Idempotent + audit:** gọi 2 lần → cùng `periods`; `did_inherit=True` → 1 ALE + 1 IMM Audit Trail; no-op → KHÔNG event rác (FR-00-55).
> - **Grep-guard:** `api/imm00.py` — 0 occurrence copy months/residual từ Category ngoài lời gọi SoT.
> - **RC-03 (round-1) vẫn đúng:** asset MỚI tạo qua `before_insert` đã kế thừa sẵn → đường này self-heal no-op (đã đủ luật).

### `preview_depreciation_schedule` (GET)

Params: `gross, residual, method, total_months, frequency, start_date`. Preview rows không lưu DB. Phục vụ form before-commit.

### `run_due_depreciation_now` (POST) — Admin only

Params: `as_of?` (date string). Chạy thủ công job depreciation due. Guard: `_assert_system_admin()` — role `System Manager` hoặc `IMM System Admin`.

### `bulk_regenerate_schedule_by_category` (POST) — Admin only

Nút **"Áp dụng khấu hao theo từng Danh mục"** (`ReferenceDataView.vue`, form Category). Params: `category_name`. Service: `assetcore.services.depreciation.bulk_regenerate_by_category`. RBAC: `_assert_system_admin()` → non-admin **403** (không leak).

**Hành vi (RC-05 — route qua SoT, KHÔNG clobber — Round-4):** với mỗi asset thuộc Category (`docstatus != 2`):
1. Asset có ≥1 kỳ **Executed** → KHÔNG đụng (preserve history) → `skipped_has_history`. Xác định qua **1 query GROUP BY parent** (`executed_parents` prefetch) chạy MỘT LẦN trước loop — KHÔNG `frappe.db.count` per-asset (N+1 đóng, mirror `compute_all` round-3).
2. Else gọi **SoT DUY NHẤT** `inherit_depreciation_rules_from_category(asset)` (thay 4 dòng inline cũ) → đếm `inherited` nếu ≥1 field thay đổi. **No-clobber:** `months/residual/method/frequency` user đã nhập → GIỮ NGUYÊN (BR-00-19/23).
3. Asset `gross<=0` HOẶC Category cũng thiếu luật (`cat.months<=0`) → `skipped_no_rule` (KHÔNG che lỗi master-data — BR-00-20).
4. Else `generate_schedule(force=True)` (asset chưa-Executed → xoá-sinh-lại) → `regenerated`.
5. Audit best-effort: per-asset ALE `depreciation_rules_inherited` (option round-1, KHÔNG migrate) + **1** IMM Audit Trail `System` TỔNG cho lần bulk — KHÔNG chặn payload (CLAUDE.md §5).

**Response 200 (payload 7-key — chuẩn hoá khớp `compute_all`):**
```json
{ "category": "CAT-0659", "total_assets": 0,
  "inherited": 0, "regenerated": 0,
  "skipped_has_history": 0, "skipped_no_rule": 0, "errors": 0 }
```
- `inherited` = số asset được SoT kế thừa ≥1 field. `skipped_no_rule` = asset `gross<=0` hoặc Category chưa cấu hình luật.
- `skipped_has_history` = asset đã có kỳ Executed (bỏ qua bảo toàn lịch sử) → `accumulated/book` bất biến.

**Idempotent:** chạy 2 lần liên tiếp trên cùng dataset → lần 2 `inherited = 0` (đã đủ luật); `accumulated` của asset đã Executed không đổi.

> **Self-Correction (Round-4 / RC-05):** payload cũ 5-key `{ category, total_assets, regenerated, skipped_has_history, errors }` (inline copy → **clobber** field user nhập; thiếu `inherited`/`skipped_no_rule`; N+1 `db.count` per-asset) đã được thay bằng shape 7-key trên + route qua SoT. FE `bulkRegenerateScheduleByCategory()` (06 §V.1) cập nhật type theo shape mới (thêm `inherited` + `skipped_no_rule`).

### `list_assets_depreciation` (GET) — Asset Finance Hub

Params: `page=1, page_size=50, method_filter?, status_filter?, category_filter?, depreciation_filter?`. Trả paginated list assets kèm: `gross_purchase_amount, residual_value, accumulated_depreciation, current_book_value, depreciation_method, total_depreciation_months, depreciation_frequency, configured, pct_depreciated, executed_periods, total_periods`.

> **`current_book_value` enriched qua SoT `effective_book_value` (BR-05-13 / RC-06).** Mỗi dòng (`_depr_enrich_row`) gán `current_book_value = effective_book_value(row)` — KHÔNG `or gross`. Asset KH hết về 0 → field trả **`0.0`** (drill hiện `0đ`), KHÔNG phantom `gross`. Dòng enriched này cũng nuôi `is_fully_depreciated` (cùng book SoT → count==drill khớp).

**`depreciation_filter`** (mới — drill cho ô KPI "Hết khấu hao", BR-05-15):
- `'fully_depreciated'` → danh sách CHỈ chứa asset thỏa SoT `is_fully_depreciated` (`configured ∧ current_book_value ≤ residual_value + 1`). Áp **post-enrich**, AND với `method/status/category` filter sẵn có (không clobber).
- Khi set, `pagination.total` == số phần tử thỏa SoT (đếm trên tập đã lọc, KHÔNG `frappe.db.count` thô) → `items` không lệch `total`.
- Để rỗng → hành vi cũ (không lọc theo trạng thái khấu hao).
- Predicate là SoT DUY NHẤT ở `services/depreciation.py::is_fully_depreciated` — KHÔNG inline lại. Chi tiết: [imm-05/04 §2.5.1](../imm-05/04_Backend_Design.md).

> **INV-DEP-5 (đo trên data-live):** `len(list_assets_depreciation(depreciation_filter='fully_depreciated', page_size=lớn).items)` (de-dup theo `name`) == `get_depreciation_stats().fully_depreciated` — card count == drill rows.

### `get_depreciation_stats` (GET)

Trả tổng hợp tài chính toàn danh mục: `{ total_assets, configured_count, unconfigured_count, fully_depreciated, total_gross, total_accumulated, total_book_value, overall_pct, by_method[], by_category[] }`.

`fully_depreciated` đếm bằng SoT `is_fully_depreciated` (thay biểu thức inline cũ `book <= residual + 1`) — **backward-compat: cùng tập, cùng số**. Các key khác KHÔNG đổi.

> **`total_book_value` & `by_category[].book_value` qua SoT `effective_book_value` (BR-05-13 / RC-06).** Mỗi asset cộng book = `effective_book_value(row)` thay vì `current_book_value or gross`. Asset đã khấu hao **hết** về `0.0` → cộng **`0.0`**, KHÔNG phantom `gross` (trước: over-count = `gross`). Cùng book SoT nuôi `is_fully_depreciated` → INVARIANT: asset `gross>0 ∧ residual=0 ∧ configured ∧ book=0.0` ĐƯỢC đếm `fully_depreciated` (trước bị loại vì book thổi về `gross > residual+1`). Asset `current_book_value IS NULL` (chưa chạy KH) → cộng `gross` (no regression).

### `compute_all_depreciation` (POST) — Admin only

Nút global **"Áp dụng khấu hao cho TẤT CẢ tài sản"** (Asset Finance Hub). RBAC: `_assert_system_admin()` → non-admin **403** (không leak).

**Hành vi (RC-03 — backfill-rồi-sinh, thay vì skip):** với mỗi asset `docstatus != 2`:
1. Nếu có ≥1 kỳ **Executed** → KHÔNG đụng (preserve history) → đếm `skipped_has_history`.
2. Else nếu asset thiếu `method/months` **và** Category có luật → gọi SoT `inherit_depreciation_rules_from_category()` để **backfill TRƯỚC** (đếm `inherited` nếu ≥1 field thay đổi), rồi `generate_schedule(force=False)` (đếm `generated`).
3. Nếu asset thiếu luật **và** Category cũng không có luật → `skipped_no_rule` (không bịa số — BR-00-20).
4. Sau vòng lặp: `run_due_depreciation(None)` cập nhật `accumulated/book` đến `today` → `executed_rows`, `updated_assets`.
5. Sinh lifecycle/audit event cho hành động backfill (1 event tổng hoặc per-asset inherited — BR-00-21, audit trail).

**Response 200:** payload có cấu trúc rõ:
```json
{ "inherited": 0, "generated": 0, "executed_rows": 0,
  "updated_assets": 0, "skipped_has_history": 0, "skipped_no_rule": 0 }
```
- `skipped_no_rule` = asset không có cả luật ở Category.
- `skipped_has_history` = asset đã có kỳ Executed (bỏ qua để bảo toàn lịch sử).

**Idempotent:** chạy 2 lần liên tiếp trên cùng dataset → lần 2 `inherited = 0` (không còn gì để backfill) và KHÔNG tạo trùng schedule / đổi `accumulated` của asset đã Executed.

> **Self-Correction:** payload cũ `{ generated_schedules, skipped, executed_rows, updated_assets }` (gộp mọi lý do skip vào 1 số `skipped`, và **skip** thay vì backfill) đã được thay bằng shape 6-key ở trên. FE `computeAllDepreciation()` (06 §V.1) cập nhật type theo shape mới.

> 3 endpoint admin (`run_due_depreciation_now`, `bulk_regenerate_schedule_by_category`, `compute_all_depreciation`) đều dùng `_assert_system_admin()` guard.

---

## III.19. Asset Downtime Metrics (1 endpoint)

`get_asset_downtime_metrics` — GET, params: `asset_name, year (optional)`.

---

## III.11. Scheduler Manual Trigger (3 endpoints — Admin only)

### `trigger_capa_overdue_check`

GET `assetcore.api.imm00.trigger_capa_overdue_check`. Permission: IMM System Admin / System Manager.

**Response 200:** `{ "triggered": "check_capa_overdue" }`

### `trigger_contract_expiry_check`

GET `assetcore.api.imm00.trigger_contract_expiry_check`. Permission: IMM System Admin.

**Response 200:** `{ "triggered": "check_vendor_contract_expiry" }`

### `trigger_registration_expiry_check`

GET `assetcore.api.imm00.trigger_registration_expiry_check`. Permission: IMM System Admin.

**Response 200:** `{ "triggered": "check_registration_expiry" }`

> **Lưu ý:** Các endpoints trigger là GET (không phải POST). Sử dụng `_assert_system_admin()` để check role.

---

## III.20. Inventory API — Spec only

> Inventory CRUD (Warehouse, Spare Part, Stock Movement) chưa có endpoint riêng trong `assetcore.api.imm00`. Các DocTypes `AC Warehouse`, `AC Spare Part`, `AC Spare Part Stock`, `AC Stock Movement` đã có trong codebase. Endpoints inventory sẽ được implement theo spec dưới đây khi cần.

Base path đề xuất: `assetcore.api.inventory.<function>`

Tất cả trả về `_ok(data)` / `_err(msg, code)` envelope chuẩn.

---

## III.21. Notification Preferences (3 endpoints — Notification Framework Wave N1)

Base path: `assetcore.api.notifications.<function>`. Envelope chuẩn `{success, data}`. Per-user — chỉ thao tác trên Notification Settings của chính user đang đăng nhập (System Manager có thể truyền `user`).

### `get_notification_preferences` — Đọc tùy chọn nhận email

`GET` · auth: session. Trả trạng thái toggle email của user hiện tại.

```jsonc
// Response
{ "success": true, "data": { "email_enabled": true } }
```

### `set_email_enabled` — Bật/tắt nhận email

`POST` · auth: session. Body: `{ "enabled": false }`. Set `Notification Settings.enable_email_notifications`.

```jsonc
// Request
{ "enabled": false }
// Response
{ "success": true, "data": { "email_enabled": false } }
```

> In-app (chuông) dùng API Frappe core sẵn có (`frappe.desk.doctype.notification_log.notification_log.get_notification_logs`, mark-as-read) — KHÔNG cần endpoint AssetCore riêng. Badge chuông là component desk/SPA Frappe core.

> **Vòng 3 — E3 (Incident created) & E4 (Calibration due): KHÔNG có API endpoint AssetCore mới.** E3 là hook `Incident Report.after_insert`; E4 chạy trong scheduler `imm11.check_calibration_expiry` (daily). Cả hai chỉ phát Notification Log + email — tiêu thụ qua đúng API chuông Frappe core ở trên. FE KHÔNG cần client mới cho 2 event này (badge chuông hiện hữu đã hiển thị).

> **Vòng 4 — HTML email template + deep-link: KHÔNG có API endpoint mới, KHÔNG đổi shape endpoint nào.** Nâng cấp thuần server-side ở `_dispatch` (dựng HTML qua `_render_email`, gửi qua `_safe_sendmail`). 2 endpoint preference ở trên giữ nguyên contract. FE KHÔNG đổi (email render phía server; bell UI không đổi). Spec: `04_Backend_Design.md §III.1b-3`.

### `get_delivery_kpi` — KPI Notification Delivery (vòng 5, System Manager only)

`GET` · auth: session + **role System Manager** (raise `FORBIDDEN` nếu không). Query: `days` (int, mặc định 30, cửa sổ Email Queue). Đo độ phủ thông báo: tỷ lệ email gửi thành công (`delivery_rate`) và tỷ lệ user tắt email (`opt_out_rate`). Chỉ tính email AssetCore (lọc theo `reference_doctype ∈ {AC Asset, Incident Report, PM Work Order, Asset Repair}`). Công thức + ngưỡng màu: `04_Backend_Design.md §III.1b-4`.

```jsonc
// GET .../get_delivery_kpi?days=30  →  Response
{ "success": true, "data": {
    "delivery_rate": 97.5,        // null nếu mẫu rỗng (chia-0 guard)
    "sent": 39, "failed": 1,
    "opt_out_rate": 5.0,          // null nếu total_users=0
    "total_users": 20, "opted_out": 1,
    "window_days": 30,
    "delivery_status": "good",    // good|warn|bad|na → màu KPI card FE
    "opt_out_status": "good"
} }
```

> **Vòng 5 — Audit linkage:** từ vòng 5, `_dispatch` truyền `reference_doctype`/`reference_name` của doc vào `_safe_sendmail` → email AssetCore trở nên truy nguyên trong Email Queue (core). Email gửi trước vòng 5 (ref NULL) bị loại khỏi mẫu KPI — giới hạn đã nêu trong docstring. KHÔNG DocType mới. FE: 1 KPI card tái dùng `KpiCard.vue` (chỉ hiển thị cho System Manager).

---

# Phần IV — Endpoint → Business Rule Mapping

| Endpoint | Business Rule áp dụng |
|---|---|
| `create_device_model`, `update_device_model` | BR-00-01, VR-00-03 |
| `transition_status`, `update_asset` | BR-00-02, BR-00-04, BR-00-10 |
| `list_audit_trail`, `get_audit_entry`, `verify_chain` | BR-00-03 |
| `create_asset` (validate), Work Order APIs | BR-00-05 (`validate_asset_for_operations`) |
| `create_supplier`, `update_supplier` | BR-00-06 |
| SLA Policy controller (validate) | BR-00-07 |
| `close_capa_record` | BR-00-08 |
| Scheduler `trigger_capa_overdue_check` | BR-00-09 |
| `create_incident`, `update_incident`, `submit_incident` | VR-00-04, AC-E008, AC-E009 |
| Inventory submit/cancel | BR-INV-01 → BR-INV-08 |

---

## DoD — File 05 hoàn chỉnh

### I. Conventions
- [x] Response envelope `{success, data}` — không dùng `{message: {...}}`
- [x] Authentication (Token + Session)
- [x] HTTP status codes
- [x] Business error codes (AC-E001 → AC-E012)
- [x] Pagination
- [x] Filter convention
- [x] Rate limiting

### II. Permission matrix
- [x] 8 roles × tất cả endpoint nhóm

### III. Endpoints (verified vs `api/imm00.py`)
- [x] AC Asset (9 endpoints — list [filter gmdn_code], get, create, update, delete, transition_status, get_asset_timeline, validate_for_operations, get_asset_kpi)
- [x] AC Supplier (5 endpoints — list, get, create, update, delete)
- [x] Location/Dept/Category (9+ endpoints — full CRUD per entity)
- [x] IMM Device Model (5 endpoints — list, get, create, update, delete + upload_device_model_file)
- [x] IMM SLA Policy (5 endpoints — list, get, resolve, create, update, delete)
- [x] IMM Audit Trail (3 endpoints — list_audit_trail, get_audit_entry, verify_chain)
- [x] IMM CAPA Record (5 endpoints — list, get, open_capa, close_capa_record, list_overdue_capas)
- [x] Asset Lifecycle Event (2 endpoints — list_lifecycle_events, get_lifecycle_event)
- [x] Incident Report (6 endpoints — list, get, create, update, submit, delete)
- [x] GMDN Status — đã loại bỏ (lọc thiết bị nay qua `list_assets?gmdn_code=`)
- [x] Scheduler Trigger (3 endpoints — GET, Admin only: trigger_capa_overdue_check, trigger_contract_expiry_check, trigger_registration_expiry_check)
- [x] Asset Transfer (7 endpoints — CRUD + workflow: approve, reject, receive)
- [x] Service Contract (6 endpoints — CRUD + list_asset_contracts)
- [x] PM Schedule (5 endpoints)
- [x] PM Checklist Template (5 endpoints)
- [x] Firmware Change Request (5 endpoints)
- [x] Document Request (5 endpoints)
- [x] Depreciation (9 endpoints — compute, get_schedule, regenerate, preview, run_due_now, bulk_regenerate, list_assets_depreciation [+ `depreciation_filter` BR-05-15], get_depreciation_stats, compute_all_depreciation)
- [x] Asset Downtime Metrics (1 endpoint)

### IV. Business Rule mapping
- [x] Endpoint → BR table
