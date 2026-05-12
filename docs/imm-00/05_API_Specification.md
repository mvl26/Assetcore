# 05 — API Specification — IMM-00 Foundation (Master / Cross-cutting)

| Mục | Giá trị |
|---|---|
| Module | IMM-00 — Foundation / Master Cross-cutting |
| Phạm vi | Foundation — cross-cutting |
| Owner | BE Lead |
| Liên kết | [04 Backend Design](./04_Backend_Design.md) · [06 Frontend Design](./06_Frontend_Design.md) |
| Base URL | `/api/method/assetcore.api.imm00` |
| Phiên bản API | 3.1.0 |
| Trạng thái | **Live ✅** — reviewed vs `api/imm00.py` 2026-05-08 |

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
| transition_asset_status | ✓ | ✓ | ✓ | — | — | ✓ | — | — |
| search_assets_by_udi | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| list/get supplier | ✓ | ✓ | ✓ | — | — | — | — | ✓ |
| create/update supplier | ✓ | — | ✓ | — | — | — | — | — |
| list_locations_tree | All | All | All | All | All | All | All | All |
| create location/dept/category | ✓ | ✓ (dept) | — | ✓ (cat) | — | — | — | — |
| list/get device_model | All | All | All | All | All | All | All | — |
| create/update device_model | ✓ | — | — | ✓ | — | — | — | — |
| list/get SLA | All | All | All | All | All | All | All | All |
| list/get audit_events | ✓ | — | — | — | — | ✓ | ✓ | — |
| verify_audit_chain | ✓ | — | — | — | — | ✓ | — | — |
| list/get CAPA | ✓ | ✓ | ✓ | — | — | ✓ | — | — |
| create_capa | ✓ | — | ✓ | ✓ | — | ✓ | — | — |
| update/close CAPA | ✓ | — | — | — | — | ✓ | — | — |
| list/get lifecycle_events | All | All | All | All | All | All | All | All |
| list/get/create incident | All | All | All | All | All | All | — | All |
| close_incident | ✓ | ✓ | — | — | — | ✓ | — | — |
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

---

### `get_asset` — Chi tiết Asset

| Method | GET |
|---|---|
| Path | `assetcore.api.imm00.get_asset` |

**Request:** `?name=AC-ASSET-2026-00001`

**Response 200** — đầy đủ HTM fields (asset_name, udi_code, gmdn_code, byt_reg_no, byt_reg_expiry, lifecycle_status, risk_classification, next_pm_date, next_calibration_date, commissioning_date, gmdn_status, …).

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

**Errors:** 404 (asset not found), 422 (invalid transition — BR-00-02).

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

GET `assetcore.api.imm00.list_locations` — Params: `parent` (optional). Trả flat list với fields: `name, location_name, location_code, parent_location, is_group, clinical_area_type, infection_control_level, power_backup_available, emergency_contact, dept_head, technical_contact, notes`.

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

### `get_capa`

GET `assetcore.api.imm00.get_capa?name=CAPA-...` → full CAPA fields.

### `open_capa` — Tạo CAPA mới

POST `assetcore.api.imm00.open_capa`. Body required: `asset, severity, description, responsible`. Optional: `source_type (default: Nonconformance), source_ref, due_days (default: 30)`.

**Response 200:** `{ "success": true, "data": { "name": "CAPA-2026-00007" } }`

### `close_capa_record` — Đóng CAPA

POST `assetcore.api.imm00.close_capa_record`. Body: `name` (param) + `root_cause, corrective_action, preventive_action` (required) + `effectiveness_check` (optional).

```json
{
  "root_cause": "Worn bearing in cooling pump",
  "corrective_action": "Replaced bearing per OEM SOP",
  "preventive_action": "Shorten PM interval from 6m to 3m",
  "effectiveness_check": "3-month follow-up: no recurrence"
}
```

**Response 200:** `{ "name": "CAPA-...", "status": "Closed" }`

**Errors:** 422 thiếu root_cause / corrective_action / preventive_action (BR-00-08).

### `list_overdue_capas`

GET `assetcore.api.imm00.list_overdue_capas`. Paginated. Filter: `status IN (Open, In Progress)` AND `due_date < today`.

---

## III.8. Asset Lifecycle Event (2 endpoints — read-only)

> Read-only. Event sinh tự động bởi service `create_lifecycle_event()` / `transition_asset_status()`.

### `list_lifecycle_events`

GET `assetcore.api.imm00.list_lifecycle_events`. Params: `asset` (required), `page, page_size, event_type` (optional).

Event types (từ `_lifecycle_event_for()` trong services/imm00.py): `activated, commissioned, pm_started, repair_opened, calibration_started, out_of_service, decommissioned, restored, transferred`.

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

## III.10. GMDN Status (2 endpoints)

### `update_gmdn_status`

POST `assetcore.api.imm00.update_gmdn_status`. Body: `{ "name": "AC-ASSET-...", "gmdn_status": "In Use", "reason": "Bắt đầu ca phẫu thuật" }`

- `gmdn_status` nhận: `"In Use"` hoặc `"Not Use"` (không phải tiếng Việt)
- `reason` bắt buộc ≥ 5 ký tự (BR-00-12)
- Block nếu `lifecycle_status ∈ {Decommissioned, Out of Service}` (BR-00-11)
- Ghi IMM Audit Trail "State Change" với change_summary

**Response 200:** `{ "name": "AC-ASSET-...", "gmdn_status": "In Use", "previous": "Not Use" }`

### `toggle_gmdn_status`

POST `assetcore.api.imm00.toggle_gmdn_status`. Body: `{ "name": "AC-ASSET-..." }`

Tự động đảo `In Use ↔ Not Use`. Reason auto: `"Quét QR lúc <timestamp>"`. Dùng cho QR scanner tại hiện trường.

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

---

## III.16. Firmware Change Request (5 endpoints)

`list_firmware_crs`, `get_firmware_cr`, `create_firmware_cr`, `update_firmware_cr`, `delete_firmware_cr`.

---

## III.17. Document Request (5 endpoints)

`list_document_requests`, `get_document_request`, `create_document_request`, `update_document_request`, `delete_document_request`.

---

## III.18. Depreciation (6 endpoints)

- `compute_depreciation` (POST) — Tính depreciation cho 1 asset tại thời điểm gọi.
- `get_depreciation_schedule` (GET, params: `asset_name`) — Trả toàn bộ schedule rows + summary của asset.
- `regenerate_depreciation_schedule` (POST, params: `asset_name, force=1`) — Sinh lại schedule (xoá cũ nếu force=1).
- `preview_depreciation_schedule` (GET, params: `gross, residual, method, total_months, frequency, start_date`) — Preview không lưu DB.
- `run_due_depreciation_now` (POST, params: `as_of?`) — **Admin only** (System Manager / IMM System Admin). Chạy thủ công job depreciation due.
- `bulk_regenerate_schedule_by_category` (POST, params: `category_name`) — **Admin only**. Re-apply rule khấu hao của Category cho tất cả assets, skip kỳ Executed.

> Hai endpoint admin dùng `_assert_system_admin()` guard, kiểm tra role `System Manager` hoặc `IMM System Admin`.

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

# Phần IV — Endpoint → Business Rule Mapping

| Endpoint | Business Rule áp dụng |
|---|---|
| `create_device_model`, `update_device_model` | BR-00-01, VR-00-03 |
| `transition_asset_status`, `update_asset` | BR-00-02, BR-00-04, BR-00-10 |
| `list_audit_events`, `verify_audit_chain` | BR-00-03 |
| `create_asset` (validate), Work Order APIs | BR-00-05 (`validate_asset_for_operations`) |
| `create_supplier`, `update_supplier` | BR-00-06 |
| SLA Policy controller (validate) | BR-00-07 |
| `close_capa` | BR-00-08 |
| Scheduler `trigger_check_capa_overdue` | BR-00-09 |
| `create_incident`, `submit_incident`, `close_incident` | VR-00-04, AC-E008, AC-E009 |
| `update_gmdn_status`, `toggle_gmdn_status` | BR-00-11, BR-00-12 |
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
- [x] AC Asset (11 endpoints — list, get, create, update, delete, transition_status, get_asset_timeline, validate_for_operations, get_asset_kpi, update_gmdn_status, toggle_gmdn_status)
- [x] AC Supplier (5 endpoints — list, get, create, update, delete)
- [x] Location/Dept/Category (9+ endpoints — full CRUD per entity)
- [x] IMM Device Model (5 endpoints — list, get, create, update, delete + upload_device_model_file)
- [x] IMM SLA Policy (5 endpoints — list, get, resolve, create, update, delete)
- [x] IMM Audit Trail (3 endpoints — list_audit_trail, get_audit_entry, verify_chain)
- [x] IMM CAPA Record (5 endpoints — list, get, open_capa, close_capa_record, list_overdue_capas)
- [x] Asset Lifecycle Event (2 endpoints — list_lifecycle_events, get_lifecycle_event)
- [x] Incident Report (6 endpoints — list, get, create, update, submit, delete)
- [x] GMDN Status (2 endpoints — update_gmdn_status, toggle_gmdn_status)
- [x] Scheduler Trigger (3 endpoints — GET, Admin only: trigger_capa_overdue_check, trigger_contract_expiry_check, trigger_registration_expiry_check)
- [x] Asset Transfer (7 endpoints — CRUD + workflow: approve, reject, receive)
- [x] Service Contract (6 endpoints — CRUD + list_asset_contracts)
- [x] PM Schedule (5 endpoints)
- [x] PM Checklist Template (5 endpoints)
- [x] Firmware Change Request (5 endpoints)
- [x] Document Request (5 endpoints)
- [x] Depreciation Schedule (6 endpoints)
- [x] Asset Downtime Metrics (1 endpoint)

### IV. Business Rule mapping
- [x] Endpoint → BR table
