# IMM-00 — API Interface Specification

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-00 Foundation |
| Phiên bản | **3.0.0** |
| Ngày cập nhật | 2026-04-18 |
| Trạng thái | **DRAFT** |
| Base URL | `/api/method/assetcore.api.imm00` |
| Tác giả | AssetCore Team |

---

## 1. Overview & Convention

### 1.1 Phạm vi

Tài liệu này đặc tả 42 endpoint REST của module IMM-00 Foundation (AssetCore v3). Tất cả endpoint đều được public qua cơ chế `@frappe.whitelist()` trong module Python `assetcore.api.imm00`.

Endpoint phục vụ 9 nhóm đối tượng tương ứng 9 DocType (+ scheduler trigger):

1. **AC Asset** — 8 endpoint
2. **AC Supplier** — 4 endpoint
3. **AC Location / AC Department / AC Asset Category** — 6 endpoint
4. **IMM Device Model** — 4 endpoint
5. **IMM SLA Policy** — 2 endpoint
6. **IMM Audit Trail** — 3 endpoint
7. **IMM CAPA Record** — 5 endpoint
8. **Asset Lifecycle Event** — 2 endpoint
9. **Incident Report** — 5 endpoint
10. **Scheduler manual trigger** — 3 endpoint (admin only)

AssetCore v3 **chỉ phụ thuộc Frappe Framework v15**. Không dùng ERPNext. 13 DocType lõi: `AC Asset`, `AC Supplier`, `AC Location`, `AC Department`, `AC Asset Category`, `IMM Device Model`, `IMM SLA Policy`, `IMM Audit Trail`, `IMM CAPA Record`, `Asset Lifecycle Event`, `Incident Report` + 2 child (`IMM Device Spare Part`, `AC Authorized Technician`).

> **Breaking change v3:** Các endpoint sidecar của v2 (`sync_single_asset_profile`, `sync_asset_profile_status`, endpoint trên `IMM Asset Profile`, `Vendor Profile`, `Location Ext`) **bị xoá hoàn toàn**. HTM fields đã nằm trực tiếp trên `AC Asset`.

### 1.2 Authentication

Mọi endpoint yêu cầu xác thực. Hai phương thức hỗ trợ:

```http
# API Token (server-to-server, khuyến nghị cho integration)
Authorization: token <api_key>:<api_secret>

# Session cookie (browser - Frappe UI / SPA)
Cookie: sid=<session_id>
```

Nếu thiếu hoặc sai credential → HTTP 401. Nếu user không có Role hợp lệ cho endpoint → HTTP 403.

### 1.3 Response Envelope

Tất cả response (success + error) đều gói trong `message` theo convention Frappe. Client parse `response.json().message`.

**Success (HTTP 200):**

```json
{
  "message": {
    "success": true,
    "data": { /* payload: object hoặc list */ }
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

Helper chuẩn hoá: `assetcore/utils/response.py`

```python
def _ok(data): return {"success": True, "data": data}
def _err(msg, code=400): return {"success": False, "error": msg, "code": code}
```

### 1.4 Pagination

List endpoint hỗ trợ pagination qua `utils/pagination.py`.

| Param | Kiểu | Default | Max | Ghi chú |
|---|---|---|---|---|
| `page` | int | 1 | — | Trang hiện tại (1-based) |
| `page_size` | int | 20 | 100 | Số record mỗi trang; server cap tại 100 |
| `sort` | string | `modified desc` | — | Cú pháp Frappe order_by |

**Response shape (list):**

```json
{
  "success": true,
  "data": {
    "items": [ /* ... */ ],
    "page": 1,
    "page_size": 20,
    "total": 137,
    "total_pages": 7
  }
}
```

### 1.5 Filter Convention

Các list endpoint nhận `filters` là JSON object. Các toán tử hỗ trợ:

- Exact match: `{"lifecycle_status": "Active"}`
- Operator: `{"next_pm_date": ["<=", "2026-05-01"]}`
- IN: `{"risk_class": ["in", ["High", "Critical"]]}`
- Like: `{"asset_name": ["like", "%MRI%"]}`

### 1.6 Rate Limiting

Sử dụng rate limit mặc định của Frappe Framework (`rate_limit` qua `frappe.conf.rate_limit`). Khuyến nghị production:

| Nhóm endpoint | Giới hạn |
|---|---|
| GET (list / detail) | 300 req/phút/user |
| POST / PUT (mutation) | 60 req/phút/user |
| Scheduler trigger (admin) | 5 req/phút/user |

Vượt hạn → HTTP 429, message `"Too many requests"`.

---

## 2. Error Code Table

### 2.1 HTTP Status Codes (global)

| Code | Ý nghĩa | Khi nào trả |
|---|---|---|
| 200 | OK | Thành công |
| 400 | Bad Request | Payload sai schema / thiếu param bắt buộc |
| 401 | Unauthorized | Không có / sai token / session hết hạn |
| 403 | Forbidden | User không có Role phù hợp hoặc asset đang bị block operations |
| 404 | Not Found | Record không tồn tại |
| 409 | Conflict | Vi phạm uniqueness (asset_code, serial_no, model+manufacturer…) |
| 422 | Unprocessable Entity | Vi phạm business rule (BR-00-xx) / validation rule |
| 429 | Too Many Requests | Rate limit |
| 500 | Internal Server Error | Lỗi không xác định; ghi log đầy đủ |

### 2.2 Business Exception Codes (từ Technical Design §11)

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

### 2.3 Validation Rule Codes (VR-00-xx)

| Code | Áp dụng | Mô tả |
|---|---|---|
| `VR-00-01` | AC Asset | `serial_no` bắt buộc nếu `device_model.requires_serial = 1` |
| `VR-00-02` | AC Asset | `commissioning_date ≤ today` |
| `VR-00-03` | IMM Device Model | `class` ↔ `risk_class` theo BR-00-01 |
| `VR-00-04` | Incident Report | Severity = Critical → yêu cầu xác nhận BYT |
| `VR-00-05` | IMM CAPA Record | `due_date ≥ created_date` |
| `VR-00-06` | AC Supplier | `contract_start ≤ contract_end` |

---

## 3. Endpoints

Base path Python: `assetcore.api.imm00.<function>`

URL pattern: `POST|GET /api/method/assetcore.api.imm00.<function>`

> **Quy ước Frappe:** `@frappe.whitelist(methods=["GET"])` cho đọc, `methods=["POST"]` cho mutation. Frappe router không phân biệt HTTP verb nghiêm ngặt — tài liệu ghi verb mong muốn để client tuân thủ REST.

---

### 3.1 AC Asset (8 endpoints)

#### 3.1.1 `list_assets` — Liệt kê Asset có filter & pagination

| Thuộc tính | Giá trị |
|---|---|
| Method | GET |
| Path | `assetcore.api.imm00.list_assets` |
| Permission | IMM Department Head / Operations Manager / Technician (scoped) / Admin |

**Request params (query string):**

```json
{
  "filters": {
    "lifecycle_status": "Active",
    "risk_class": ["in", ["High", "Critical"]],
    "department": "AC-DEPT-0001",
    "next_pm_date": ["<=", "2026-05-01"]
  },
  "page": 1,
  "page_size": 20,
  "sort": "next_pm_date asc"
}
```

**Fields trả về mỗi asset:** `name, asset_name, asset_code, serial_no, device_model, asset_category, department, location, lifecycle_status, risk_class, next_pm_date, next_calibration_date, byt_reg_expiry, responsible_technician, modified`.

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
        "serial_no": "SN123456",
        "device_model": "IMM-MDL-2026-0001",
        "lifecycle_status": "Active",
        "risk_class": "High",
        "next_pm_date": "2026-04-30",
        "department": "AC-DEPT-0001",
        "modified": "2026-04-18 09:12:00"
      }
    ],
    "page": 1, "page_size": 20, "total": 1, "total_pages": 1
  }
}
```

**Errors:** 401, 403, 400 (filter JSON sai).

**cURL:**

```bash
curl -X GET "https://acme.local/api/method/assetcore.api.imm00.list_assets?page=1&page_size=20&filters=%7B%22lifecycle_status%22%3A%22Active%22%7D" \
  -H "Authorization: token KEY:SECRET"
```

---

#### 3.1.2 `get_asset` — Chi tiết Asset + HTM fields

| Thuộc tính | Giá trị |
|---|---|
| Method | GET |
| Path | `assetcore.api.imm00.get_asset` |
| Permission | IMM Department Head / Operations Manager / Technician (chỉ asset được gán) / Admin |

**Request:** `?name=AC-ASSET-2026-00001`

**Response 200 — đầy đủ HTM fields:**

```json
{
  "success": true,
  "data": {
    "name": "AC-ASSET-2026-00001",
    "asset_name": "MRI Siemens Magnetom Aera 1.5T",
    "asset_code": "MRI-001",
    "serial_no": "SN123456",
    "device_model": "IMM-MDL-2026-0001",
    "asset_category": "Imaging",
    "department": "AC-DEPT-0001",
    "location": "AC-LOC-2026-0001",
    "supplier": "AC-SUP-2026-0001",
    "responsible_technician": "tech01@hospital.vn",
    "lifecycle_status": "Active",
    "risk_class": "High",
    "udi": "(01)00844868011234",
    "gmdn_code": "35147",
    "byt_reg_no": "BYT-2024-001",
    "byt_reg_expiry": "2029-03-15",
    "commissioning_date": "2024-06-01",
    "commissioning_ref": "ACC-2024-0001",
    "next_pm_date": "2026-04-30",
    "next_calibration_date": "2026-07-15",
    "purchase_date": "2024-05-20",
    "warranty_end": "2027-05-20"
  }
}
```

**Errors:** 404 (`AC-E001`), 401, 403.

---

#### 3.1.3 `create_asset` — Tạo Asset mới

| Thuộc tính | Giá trị |
|---|---|
| Method | POST |
| Path | `assetcore.api.imm00.create_asset` |
| Permission | IMM System Admin / Department Head / Operations Manager |

**Required body:** `asset_name, asset_code, device_model, asset_category, department, location`.

Khi `device_model` được set, các field default (`risk_class`, `gmdn_code`, `requires_calibration`, PM interval…) **fetch tự động** từ `IMM Device Model` (server-side `fetch_from`).

**Body:**

```json
{
  "asset_name": "MRI Siemens Magnetom Aera 1.5T",
  "asset_code": "MRI-001",
  "serial_no": "SN123456",
  "device_model": "IMM-MDL-2026-0001",
  "asset_category": "Imaging",
  "department": "AC-DEPT-0001",
  "location": "AC-LOC-2026-0001",
  "supplier": "AC-SUP-2026-0001",
  "udi": "(01)00844868011234",
  "byt_reg_no": "BYT-2024-001",
  "byt_reg_expiry": "2029-03-15",
  "purchase_date": "2024-05-20",
  "warranty_end": "2027-05-20"
}
```

**Response 200:** `{ "success": true, "data": { "name": "AC-ASSET-2026-00001" } }`

**Errors:**
- 400 thiếu required field
- 409 `AC-E011` trùng asset_code / serial_no
- 422 `VR-00-01` serial_no bắt buộc mà bỏ trống
- 422 `VR-00-02` commissioning_date tương lai

**cURL:**

```bash
curl -X POST "https://acme.local/api/method/assetcore.api.imm00.create_asset" \
  -H "Authorization: token KEY:SECRET" \
  -H "Content-Type: application/json" \
  -d '{"payload": {"asset_name":"MRI","asset_code":"MRI-001","device_model":"IMM-MDL-2026-0001","asset_category":"Imaging","department":"AC-DEPT-0001","location":"AC-LOC-2026-0001"}}'
```

---

#### 3.1.4 `update_asset` — Cập nhật Asset

| Thuộc tính | Giá trị |
|---|---|
| Method | PUT |
| Path | `assetcore.api.imm00.update_asset` |
| Permission | IMM System Admin / Department Head / Operations Manager |

**Body:** `{ "name": "AC-ASSET-2026-00001", "payload": { ... } }`

> **Quan trọng:** Endpoint này **từ chối** payload chứa field `lifecycle_status`. Muốn đổi trạng thái phải dùng `transition_asset_status` (BR-00-02). Nếu payload có `lifecycle_status` → HTTP 422 `AC-E002` với message `"Dùng transition_asset_status để đổi lifecycle_status"`.

**Response 200:** `{ "success": true, "data": { "name": "...", "modified": "..." } }`

**Errors:** 404 `AC-E001`, 422 `AC-E002`, 409 `AC-E011`.

---

#### 3.1.5 `transition_asset_status` — Đổi lifecycle_status qua state machine

| Thuộc tính | Giá trị |
|---|---|
| Method | POST |
| Path | `assetcore.api.imm00.transition_asset_status` |
| Permission | IMM Department Head / Operations Manager / QA Officer (cho Decommissioned) |

Wrapper cho service `transition_asset_status(asset_name, to_status, actor, reason, root_doctype, root_record)`.

Side-effect:
- Tạo `Asset Lifecycle Event` (BR-00-10)
- Tạo `IMM Audit Trail` với `from_status → to_status`
- Nếu `to_status = Decommissioned`: suspend PM/Cal schedules (BR-00-04)

**Body:**

```json
{
  "name": "AC-ASSET-2026-00001",
  "new_status": "Under Repair",
  "reason": "Incident IR-2026-0007 — tube cooling failure"
}
```

Giá trị `new_status` hợp lệ: `Draft, Commissioning, Active, Under Repair, Out of Service, Decommissioned`. State machine chi tiết — xem Technical Design §6.

**Response 200:**

```json
{
  "success": true,
  "data": {
    "asset": "AC-ASSET-2026-00001",
    "from_status": "Active",
    "to_status": "Under Repair",
    "lifecycle_event": "ALE-2026-0000123",
    "audit_trail": "IMM-AUD-2026-0001234"
  }
}
```

**Errors:**
- 404 `AC-E001`
- 422 `AC-E002` transition không hợp lệ (vd Decommissioned → Active)
- 403 nếu actor không có Role

**cURL:**

```bash
curl -X POST "https://acme.local/api/method/assetcore.api.imm00.transition_asset_status" \
  -H "Authorization: token KEY:SECRET" -H "Content-Type: application/json" \
  -d '{"name":"AC-ASSET-2026-00001","new_status":"Under Repair","reason":"tube fail"}'
```

---

#### 3.1.6 `get_asset_lifecycle_history` — Toàn bộ sự kiện + audit của Asset

| Thuộc tính | Giá trị |
|---|---|
| Method | GET |
| Path | `assetcore.api.imm00.get_asset_lifecycle_history` |
| Permission | IMM Department Head / Operations Manager / QA Officer / Technician (scoped) |

**Request:** `?name=AC-ASSET-2026-00001`

Trả về 2 list sắp xếp desc theo timestamp:
- `lifecycle_events`: tất cả `Asset Lifecycle Event` của asset
- `audit_trail`: tất cả `IMM Audit Trail` của asset

**Response 200:**

```json
{
  "success": true,
  "data": {
    "asset": "AC-ASSET-2026-00001",
    "lifecycle_events": [
      { "name": "ALE-2026-0000123", "event_type": "repair_opened",
        "from_status": "Active", "to_status": "Under Repair",
        "timestamp": "2026-04-18 10:00:00", "actor": "tech01@hospital.vn",
        "root_doctype": "Incident Report", "root_record": "IR-2026-0007" }
    ],
    "audit_trail": [
      { "name": "IMM-AUD-2026-0001234", "event_type": "State Change",
        "change_summary": "Active → Under Repair", "timestamp": "2026-04-18 10:00:00",
        "sha256_current": "a1b2..." }
    ]
  }
}
```

**Errors:** 404 `AC-E001`, 401, 403.

---

#### 3.1.7 `search_assets_by_udi` — Tra cứu Asset theo UDI

| Thuộc tính | Giá trị |
|---|---|
| Method | GET |
| Path | `assetcore.api.imm00.search_assets_by_udi` |
| Permission | All authenticated IMM roles |

**Request:** `?udi_code=(01)00844868011234`

Tra chính xác (exact match) trên field `udi`. Hỗ trợ tra bằng GS1 barcode scanner.

**Response 200:**

```json
{
  "success": true,
  "data": {
    "matches": [
      { "name": "AC-ASSET-2026-00001", "asset_name": "MRI Siemens Magnetom Aera 1.5T",
        "serial_no": "SN123456", "lifecycle_status": "Active" }
    ]
  }
}
```

Trả `matches: []` nếu không tìm được (không coi là 404).

---

#### 3.1.8 `get_assets_due_pm` — Asset đến hạn PM trong N ngày

| Thuộc tính | Giá trị |
|---|---|
| Method | GET |
| Path | `assetcore.api.imm00.get_assets_due_pm` |
| Permission | IMM Department Head / Operations Manager / Technician |

**Request:** `?within_days=30` (default 30, max 365)

Logic filter: `next_pm_date ≤ today + within_days` **AND** `lifecycle_status NOT IN ("Decommissioned", "Out of Service")`.

**Response 200:**

```json
{
  "success": true,
  "data": {
    "within_days": 30,
    "reference_date": "2026-04-18",
    "items": [
      { "name": "AC-ASSET-2026-00001", "asset_name": "MRI ...",
        "next_pm_date": "2026-04-30", "days_remaining": 12,
        "responsible_technician": "tech01@hospital.vn" }
    ]
  }
}
```

**Errors:** 400 nếu `within_days > 365` hoặc < 1.

---

### 3.2 AC Supplier (4 endpoints)

#### 3.2.1 `list_suppliers`

| Thuộc tính | Giá trị |
|---|---|
| Method | GET |
| Path | `assetcore.api.imm00.list_suppliers` |
| Permission | IMM System Admin / Operations Manager / Storekeeper / Department Head |

**Filters:** `vendor_type` (`Manufacturer / Distributor / Service Provider / Calibration Lab`), `is_active`, `contract_end` (operator syntax).

**Response 200:** list items gồm `name, supplier_name, vendor_type, is_active, contract_start, contract_end, iso_17025_cert, country`.

---

#### 3.2.2 `get_supplier`

| Thuộc tính | Giá trị |
|---|---|
| Method | GET |
| Path | `assetcore.api.imm00.get_supplier` |
| Permission | IMM System Admin / Operations Manager / Storekeeper |

**Request:** `?name=AC-SUP-2026-0001`

Trả về chi tiết + bảng con `authorized_technicians` (child DocType `AC Authorized Technician`).

```json
{
  "success": true,
  "data": {
    "name": "AC-SUP-2026-0001",
    "supplier_name": "Siemens Healthineers VN",
    "vendor_type": "Service Provider",
    "iso_17025_cert": null,
    "contract_start": "2025-01-01",
    "contract_end": "2026-12-31",
    "authorized_technicians": [
      { "technician_name": "Nguyễn Văn A", "email": "a.nguyen@siemens.com",
        "cert_no": "SIE-TECH-001", "cert_expiry": "2027-06-30" }
    ]
  }
}
```

---

#### 3.2.3 `create_supplier`

| Thuộc tính | Giá trị |
|---|---|
| Method | POST |
| Path | `assetcore.api.imm00.create_supplier` |
| Permission | IMM System Admin / Operations Manager |

**Body required:** `supplier_name, vendor_type`.

Nếu `vendor_type = "Calibration Lab"` mà thiếu `iso_17025_cert` → **warning** (BR-00-06 / `AC-E006`) — không block nhưng trả về trong `data.warnings[]`.

**Response 200 (có warning):**

```json
{
  "success": true,
  "data": {
    "name": "AC-SUP-2026-0002",
    "warnings": [
      { "code": "AC-E006", "message": "Nhà cung cấp hiệu chuẩn nên có chứng chỉ ISO/IEC 17025" }
    ]
  }
}
```

**Errors:** 422 `VR-00-06` nếu `contract_start > contract_end`.

---

#### 3.2.4 `update_supplier`

| Thuộc tính | Giá trị |
|---|---|
| Method | PUT |
| Path | `assetcore.api.imm00.update_supplier` |
| Permission | IMM System Admin / Operations Manager |

**Body:** `{ "name": "AC-SUP-...", "payload": { ... } }`

Trả warning tương tự 3.2.3 nếu chuyển sang vendor_type Calibration Lab mà không có ISO 17025.

---

### 3.3 AC Location / AC Department / AC Asset Category (6 endpoints)

3 DocType dạng cây (tree). List endpoint trả về cấu trúc nested.

#### 3.3.1 `list_locations_tree`

| Method | GET |
|---|---|
| Path | `assetcore.api.imm00.list_locations_tree` |
| Permission | All authenticated IMM roles |

**Response 200:**

```json
{
  "success": true,
  "data": {
    "tree": [
      { "name": "AC-LOC-2026-0001", "location_name": "Tòa A",
        "is_group": 1, "clinical_area_type": null,
        "children": [
          { "name": "AC-LOC-2026-0002", "location_name": "Khoa Chẩn đoán hình ảnh",
            "is_group": 1, "clinical_area_type": "Imaging Suite",
            "children": [
              { "name": "AC-LOC-2026-0003", "location_name": "Phòng MRI 01",
                "is_group": 0, "infection_control_level": "Standard",
                "children": [] }
            ]
          }
        ]
      }
    ]
  }
}
```

---

#### 3.3.2 `create_location`

| Method | POST |
|---|---|
| Path | `assetcore.api.imm00.create_location` |
| Permission | IMM System Admin / Department Head |

**Body:**

```json
{
  "location_name": "Phòng MRI 02",
  "parent_location": "AC-LOC-2026-0002",
  "is_group": 0,
  "clinical_area_type": "Imaging Suite",
  "infection_control_level": "Standard"
}
```

**Errors:** 404 nếu `parent_location` không tồn tại; 409 nếu trùng `location_name` cùng parent.

---

#### 3.3.3 `list_departments_tree`

| Method | GET |
|---|---|
| Path | `assetcore.api.imm00.list_departments_tree` |
| Permission | All authenticated IMM roles |

Trả tree tương tự 3.3.1 cho `AC Department`. Fields: `name, department_name, is_group, head_user, cost_center_code, children`.

---

#### 3.3.4 `create_department`

| Method | POST |
|---|---|
| Path | `assetcore.api.imm00.create_department` |
| Permission | IMM System Admin |

**Body:** `department_name, parent_department, is_group, head_user?, cost_center_code?`.

---

#### 3.3.5 `list_asset_categories`

| Method | GET |
|---|---|
| Path | `assetcore.api.imm00.list_asset_categories` |
| Permission | All authenticated IMM roles |

Flat list (không tree) — AC Asset Category là flat taxonomy.

```json
{
  "success": true,
  "data": {
    "items": [
      { "name": "Imaging", "category_name": "Imaging",
        "default_risk_class": "High", "default_pm_interval_months": 6 },
      { "name": "Laboratory", "category_name": "Laboratory",
        "default_risk_class": "Medium", "default_pm_interval_months": 12 }
    ]
  }
}
```

---

#### 3.3.6 `create_asset_category`

| Method | POST |
|---|---|
| Path | `assetcore.api.imm00.create_asset_category` |
| Permission | IMM System Admin / Workshop Lead |

**Body:** `category_name, default_risk_class?, default_pm_interval_months?, requires_calibration?`.

**Errors:** 409 nếu trùng `category_name`.

---

### 3.4 IMM Device Model (4 endpoints)

#### 3.4.1 `list_device_models`

| Method | GET |
|---|---|
| Path | `assetcore.api.imm00.list_device_models` |
| Permission | All authenticated IMM roles |

**Filters:** `manufacturer`, `asset_category`, `class` (I/II/III), `risk_class`, `is_active`.

Response fields: `name, model_name, manufacturer, asset_category, class, risk_class, requires_calibration, default_pm_interval_months, is_active`.

---

#### 3.4.2 `get_device_model`

| Method | GET |
|---|---|
| Path | `assetcore.api.imm00.get_device_model` |
| Permission | All authenticated IMM roles |

**Request:** `?name=IMM-MDL-2026-0001`

Trả chi tiết + child table `spare_parts_list` (`IMM Device Spare Part`).

```json
{
  "success": true,
  "data": {
    "name": "IMM-MDL-2026-0001",
    "model_name": "Magnetom Aera 1.5T",
    "manufacturer": "Siemens Healthineers",
    "class": "III",
    "risk_class": "High",
    "requires_calibration": 1,
    "default_pm_interval_months": 6,
    "spare_parts_list": [
      { "part_name": "RF Coil", "part_code": "RFC-001",
        "recommended_stock": 1, "unit_cost": 45000000 }
    ]
  }
}
```

---

#### 3.4.3 `create_device_model`

| Method | POST |
|---|---|
| Path | `assetcore.api.imm00.create_device_model` |
| Permission | IMM System Admin / Workshop Lead |

**Body required:** `model_name, manufacturer, asset_category, class`.

**Validation:** BR-00-01 / `VR-00-03` — `class ↔ risk_class`:

| class | risk_class bắt buộc |
|---|---|
| I | Low |
| II | Medium |
| III | High hoặc Critical |

Nếu sai → HTTP 422 `AC-E012` hoặc validation message tiếng Việt.

**Errors:**
- 409 `AC-E012` trùng `(model_name, manufacturer)`
- 422 `VR-00-03` class/risk mismatch

---

#### 3.4.4 `update_device_model`

| Method | PUT |
|---|---|
| Path | `assetcore.api.imm00.update_device_model` |
| Permission | IMM System Admin / Workshop Lead |

**Body:** `{ "name": "IMM-MDL-...", "payload": { ... } }`

Giữ validate `class ↔ risk_class`.

---

### 3.5 IMM SLA Policy (2 endpoints)

#### 3.5.1 `list_sla_policies`

| Method | GET |
|---|---|
| Path | `assetcore.api.imm00.list_sla_policies` |
| Permission | All authenticated IMM roles |

Không paginated — thường chỉ có < 30 policy.

```json
{
  "success": true,
  "data": {
    "items": [
      { "name": "SLA-P1-Critical", "policy_name": "SLA-P1-Critical",
        "priority": "P1 Critical", "risk_class": "Critical",
        "response_time_minutes": 15, "resolution_time_hours": 4,
        "is_default": 0 },
      { "name": "SLA-P1-Default", "policy_name": "SLA-P1-Default",
        "priority": "P1 Critical", "risk_class": null,
        "response_time_minutes": 30, "resolution_time_hours": 8,
        "is_default": 1 }
    ]
  }
}
```

---

#### 3.5.2 `get_sla_for` — Lookup SLA theo priority × risk_class

| Method | GET |
|---|---|
| Path | `assetcore.api.imm00.get_sla_for` |
| Permission | All authenticated IMM roles |

Wrapper cho service `get_sla_policy(priority, risk_class)`. Logic fallback: nếu không khớp exact, chọn record có `is_default = 1` cùng priority.

**Request:** `?priority=P2&risk_class=High`

**Response 200:**

```json
{
  "success": true,
  "data": {
    "matched_policy": "SLA-P2-High",
    "priority": "P2",
    "risk_class": "High",
    "response_time_minutes": 60,
    "resolution_time_hours": 24,
    "is_default": 0
  }
}
```

**Errors:** 400 `AC-E004` nếu không tìm được cả exact lẫn default.

---

### 3.6 IMM Audit Trail (3 endpoints)

> **Audit Trail là read-only qua API.** Không có endpoint create / update / delete — mọi record sinh từ service `log_audit_event()` gọi nội bộ từ các module khác (BR-00-03).

#### 3.6.1 `list_audit_events`

| Method | GET |
|---|---|
| Path | `assetcore.api.imm00.list_audit_events` |
| Permission | IMM System Admin / QA Officer / Document Officer |

**Params:** `asset` (optional), `from_date`, `to_date`, `event_type`, `page`, `page_size`.

**Response 200 items field:**

```json
{
  "name": "IMM-AUD-2026-0001234",
  "asset": "AC-ASSET-2026-00001",
  "event_type": "State Change",
  "actor": "tech01@hospital.vn",
  "timestamp": "2026-04-18 10:00:00",
  "from_status": "Active", "to_status": "Under Repair",
  "change_summary": "Incident IR-2026-0007 — tube cooling failure",
  "ref_doctype": "Incident Report", "ref_name": "IR-2026-0007",
  "sha256_previous": "9f8e...", "sha256_current": "a1b2..."
}
```

---

#### 3.6.2 `get_audit_event`

| Method | GET |
|---|---|
| Path | `assetcore.api.imm00.get_audit_event` |
| Permission | IMM System Admin / QA Officer / Document Officer |

**Request:** `?name=IMM-AUD-2026-0001234`. Trả chi tiết như 3.6.1.

---

#### 3.6.3 `verify_audit_chain` — Kiểm tra SHA-256 chain integrity

| Method | POST |
|---|---|
| Path | `assetcore.api.imm00.verify_audit_chain` |
| Permission | IMM System Admin / QA Officer |

**Body:** `{ "asset": "AC-ASSET-2026-00001" }`

Duyệt toàn bộ audit trail của asset theo timestamp asc, tính lại `sha256(sha256_previous + record_canonical_json)` và so khớp `sha256_current`.

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

Kể cả tampered vẫn trả HTTP 200 — frontend xử lý alert. Nếu tampered, service tự tạo 1 record mới với `event_type = "Integrity Violation"` (`AC-E010`) và email QA Officer.

**Errors:** 403 nếu user không có Role; 404 nếu asset không có audit trail nào.

---

### 3.7 IMM CAPA Record (5 endpoints)

#### 3.7.1 `list_capas`

| Method | GET |
|---|---|
| Path | `assetcore.api.imm00.list_capas` |
| Permission | QA Officer / Department Head / Operations Manager |

**Filters:** `severity` (Minor/Major/Critical), `status` (Draft/Open/In Progress/Overdue/Closed), `responsible` (user), `asset`, `due_date`.

---

#### 3.7.2 `get_capa`

| Method | GET |
|---|---|
| Path | `assetcore.api.imm00.get_capa` |
| Permission | QA Officer / Department Head / assigned responsible user |

**Request:** `?name=CAPA-2026-00007`

```json
{
  "success": true,
  "data": {
    "name": "CAPA-2026-00007",
    "asset": "AC-ASSET-2026-00001",
    "source_type": "Incident",
    "source_ref": "IR-2026-0007",
    "severity": "Major",
    "status": "Open",
    "description": "Tube cooling intermittent failure",
    "root_cause": null,
    "corrective_action": null,
    "preventive_action": null,
    "responsible": "qa01@hospital.vn",
    "due_date": "2026-05-18",
    "effectiveness_check": null
  }
}
```

---

#### 3.7.3 `create_capa`

| Method | POST |
|---|---|
| Path | `assetcore.api.imm00.create_capa` |
| Permission | QA Officer / Workshop Lead / Operations Manager |

Wrapper service `create_capa(asset, source_type, source_ref, severity, description, responsible)`.

Workflow: `Draft → Open` (auto-submit sang Open sau khi tạo).

**Body:**

```json
{
  "asset": "AC-ASSET-2026-00001",
  "source_type": "Incident",
  "source_ref": "IR-2026-0007",
  "severity": "Major",
  "description": "Tube cooling intermittent failure",
  "responsible": "qa01@hospital.vn",
  "due_date": "2026-05-18"
}
```

**Response:** `{ "success": true, "data": { "name": "CAPA-2026-00007", "status": "Open" } }`

**Errors:** 404 `AC-E001` asset không tồn tại; 422 `VR-00-05` due_date quá khứ.

---

#### 3.7.4 `update_capa`

| Method | PUT |
|---|---|
| Path | `assetcore.api.imm00.update_capa` |
| Permission | QA Officer / assigned responsible |

**Body:** `{ "name": "CAPA-...", "payload": { ... } }`

**Business Rule:** Nếu `status = Closed` → HTTP 422 với message `"CAPA đã đóng không thể chỉnh sửa"` (BR-00-03 immutability). Mọi thay đổi ghi IMM Audit Trail.

---

#### 3.7.5 `close_capa`

| Method | POST |
|---|---|
| Path | `assetcore.api.imm00.close_capa` |
| Permission | QA Officer |

Wrapper service `close_capa(capa_name, root_cause, corrective_action, preventive_action, effectiveness_check, actor)`.

Workflow: `Open | In Progress | Overdue → Closed` (submit).

**Body:**

```json
{
  "name": "CAPA-2026-00007",
  "verification_notes": "Root cause: worn bearing; replaced + PM interval shortened",
  "effectiveness_check": "3-month follow-up: no recurrence"
}
```

> Server parse `verification_notes` (client-friendly alias) + map sang fields chuẩn (`root_cause`, `corrective_action`, `preventive_action`) nếu UI gửi object đầy đủ. Khuyến nghị gửi tách:

```json
{
  "name": "CAPA-2026-00007",
  "root_cause": "Worn bearing in cooling pump",
  "corrective_action": "Replaced bearing per OEM SOP",
  "preventive_action": "Shorten PM interval from 6m to 3m; add vibration monitoring",
  "effectiveness_check": "3-month follow-up: no recurrence"
}
```

**Response 200:**

```json
{ "success": true, "data": { "name": "CAPA-2026-00007", "status": "Closed", "closed_at": "2026-04-18 14:30:00" } }
```

**Errors:**
- 422 `AC-E005` thiếu root_cause / corrective_action / preventive_action (BR-00-08)
- 404 nếu CAPA không tồn tại

---

### 3.8 Asset Lifecycle Event (2 endpoints)

> Read-only. Event được sinh tự động bởi service `create_lifecycle_event` hoặc `transition_asset_status` — không có create API.

#### 3.8.1 `list_lifecycle_events`

| Method | GET |
|---|---|
| Path | `assetcore.api.imm00.list_lifecycle_events` |
| Permission | All authenticated IMM roles |

**Filters:** `asset`, `event_type`, `from_date`, `to_date`, `actor`, `root_doctype`.

Event type enum: `commissioned, pm_completed, repair_opened, repair_closed, calibration_completed, capa_opened, capa_closed, status_changed, incident_reported, decommissioned, relocated, reassigned`.

---

#### 3.8.2 `get_lifecycle_event`

| Method | GET |
|---|---|
| Path | `assetcore.api.imm00.get_lifecycle_event` |
| Permission | All authenticated IMM roles |

**Request:** `?name=ALE-2026-0000123`

```json
{
  "success": true,
  "data": {
    "name": "ALE-2026-0000123",
    "asset": "AC-ASSET-2026-00001",
    "event_type": "repair_opened",
    "timestamp": "2026-04-18 10:00:00",
    "actor": "tech01@hospital.vn",
    "from_status": "Active", "to_status": "Under Repair",
    "root_doctype": "Incident Report", "root_record": "IR-2026-0007",
    "notes": "Tube cooling intermittent failure"
  }
}
```

---

### 3.9 Incident Report (5 endpoints)

#### 3.9.1 `list_incidents`

| Method | GET |
|---|---|
| Path | `assetcore.api.imm00.list_incidents` |
| Permission | All authenticated IMM roles |

**Filters:** `severity` (Minor/Major/Critical), `status` (Draft/Open/Under Investigation/Closed), `reported_to_byt` (0/1), `asset`, `from_date`, `to_date`, `patient_affected`.

---

#### 3.9.2 `get_incident`

| Method | GET |
|---|---|
| Path | `assetcore.api.imm00.get_incident` |
| Permission | All authenticated IMM roles |

```json
{
  "success": true,
  "data": {
    "name": "IR-2026-0007",
    "asset": "AC-ASSET-2026-00001",
    "severity": "Major",
    "status": "Open",
    "incident_datetime": "2026-04-18 09:45:00",
    "reporter": "tech01@hospital.vn",
    "description": "Tube cooling alarm during MRI scan",
    "patient_affected": 0,
    "patient_impact_description": null,
    "reported_to_byt": 0,
    "linked_capa": null,
    "linked_repair_wo": null
  }
}
```

---

#### 3.9.3 `create_incident`

| Method | POST |
|---|---|
| Path | `assetcore.api.imm00.create_incident` |
| Permission | All authenticated IMM roles (Technician, Operator, Department Head, QA) |

**Body required:** `asset, severity, incident_datetime, description`.

**Validation:**
- Nếu `severity = Critical` AND `patient_affected = 1` mà thiếu xác nhận `reported_to_byt` → trả `data.warnings[]` với `AC-E008` (không block).
- Nếu `patient_affected = 1` mà thiếu `patient_impact_description` → 422 `AC-E009`.

Status khởi tạo: `Draft`.

**Body:**

```json
{
  "asset": "AC-ASSET-2026-00001",
  "severity": "Critical",
  "incident_datetime": "2026-04-18 09:45:00",
  "description": "Tube cooling alarm during MRI scan",
  "patient_affected": 1,
  "patient_impact_description": "Patient scan postponed; no physical harm",
  "reported_to_byt": 0
}
```

**Response 200 (với warning):**

```json
{
  "success": true,
  "data": {
    "name": "IR-2026-0007",
    "status": "Draft",
    "warnings": [
      { "code": "AC-E008", "message": "Sự cố Critical có bệnh nhân bị ảnh hưởng — xác nhận báo cáo Bộ Y tế theo NĐ98/2021" }
    ]
  }
}
```

---

#### 3.9.4 `submit_incident` — Workflow transition Draft → Open → Under Investigation

| Method | POST |
|---|---|
| Path | `assetcore.api.imm00.submit_incident` |
| Permission | Reporter / Department Head / QA Officer |

**Body:** `{ "name": "IR-2026-0007" }`

Logic:
- Từ `Draft` → `Open` (submit; docstatus=1); sinh Lifecycle Event `incident_reported`; log Audit Trail.
- Từ `Open` → `Under Investigation` (gán `assigned_investigator = current_user` nếu là QA).

**Response 200:**

```json
{
  "success": true,
  "data": {
    "name": "IR-2026-0007",
    "from_status": "Draft",
    "to_status": "Open",
    "lifecycle_event": "ALE-2026-0000124"
  }
}
```

**Errors:** 422 nếu status đã Closed; 422 `AC-E008` nếu Critical chưa xác nhận BYT trước khi submit.

---

#### 3.9.5 `close_incident`

| Method | POST |
|---|---|
| Path | `assetcore.api.imm00.close_incident` |
| Permission | QA Officer / Department Head |

**Body:**

```json
{
  "name": "IR-2026-0007",
  "resolution_notes": "Tube replaced; functional test passed",
  "linked_capa": "CAPA-2026-00007",
  "linked_repair_wo": "WO-2026-00042"
}
```

Workflow: `Under Investigation → Closed`. Sinh `Asset Lifecycle Event` `incident_closed`.

**Validation:**
- Với severity Major/Critical: **bắt buộc** `linked_capa` hoặc `linked_repair_wo` (ít nhất 1).
- Nếu thiếu → 422 với message `"Sự cố Major/Critical phải liên kết CAPA hoặc Repair Work Order trước khi đóng"`.

**Response 200:**

```json
{
  "success": true,
  "data": {
    "name": "IR-2026-0007",
    "status": "Closed",
    "closed_at": "2026-04-22 16:20:00",
    "linked_capa": "CAPA-2026-00007",
    "linked_repair_wo": "WO-2026-00042"
  }
}
```

---

### 3.10 Scheduler Manual Trigger (3 endpoints — Admin only)

Cung cấp cho QA / System Admin chạy thủ công các scheduler daily (debug / truy hồi sự kiện bỏ lỡ). Production scheduler vẫn chạy qua hook `scheduler_events` hằng ngày.

Tất cả 3 endpoint dưới đây yêu cầu role `IMM System Admin` (hoặc `System Manager`). User khác → HTTP 403.

#### 3.10.1 `trigger_check_capa_overdue`

| Method | POST |
|---|---|
| Path | `assetcore.api.imm00.trigger_check_capa_overdue` |
| Permission | IMM System Admin |

**Body:** `{}` (không cần payload)

Gọi service `check_capa_overdue()`. Mark Open CAPA quá `due_date → Overdue`; gửi email QA Officer + responsible.

**Response 200:**

```json
{
  "success": true,
  "data": {
    "job": "check_capa_overdue",
    "executed_at": "2026-04-18 14:30:00",
    "marked_overdue": 3,
    "emails_sent": 4
  }
}
```

---

#### 3.10.2 `trigger_check_vendor_contract_expiry`

| Method | POST |
|---|---|
| Path | `assetcore.api.imm00.trigger_check_vendor_contract_expiry` |
| Permission | IMM System Admin |

Gọi `check_vendor_contract_expiry()`. Cảnh báo HĐ 90/60/30 ngày.

**Response 200:**

```json
{
  "success": true,
  "data": {
    "job": "check_vendor_contract_expiry",
    "executed_at": "2026-04-18 14:30:00",
    "warnings_90d": 2, "warnings_60d": 1, "warnings_30d": 0,
    "emails_sent": 3
  }
}
```

---

#### 3.10.3 `trigger_check_registration_expiry`

| Method | POST |
|---|---|
| Path | `assetcore.api.imm00.trigger_check_registration_expiry` |
| Permission | IMM System Admin |

Gọi `check_registration_expiry()`. Cảnh báo đăng ký BYT 90/60/30/7 ngày (filter `lifecycle_status != Decommissioned`).

**Response 200:**

```json
{
  "success": true,
  "data": {
    "job": "check_registration_expiry",
    "executed_at": "2026-04-18 14:30:00",
    "warnings_90d": 5, "warnings_60d": 2, "warnings_30d": 1, "warnings_7d": 0,
    "emails_sent": 8
  }
}
```

**cURL ví dụ:**

```bash
curl -X POST "https://acme.local/api/method/assetcore.api.imm00.trigger_check_registration_expiry" \
  -H "Authorization: token ADMIN_KEY:ADMIN_SECRET"
```

---

## 4. Rate Limiting

Rate limit dựa trên Frappe default (`frappe.rate_limiter`). Mặc định cấu hình khuyến nghị trong `common_site_config.json`:

```json
{
  "rate_limit": {
    "window": 60,
    "limit": 300
  }
}
```

Khi bị rate limit → HTTP 429 với header `Retry-After: <seconds>`.

Cho scheduler trigger (3.10.x) — cài giới hạn thấp hơn qua decorator `@frappe.rate_limit(limit=5, seconds=60)` để tránh lạm dụng.

---

## 5. Permission Matrix — Tổng hợp

| Endpoint nhóm | System Admin | Dept Head | Ops Manager | Workshop Lead | Technician | QA Officer | Document Officer | Storekeeper |
|---|---|---|---|---|---|---|---|---|
| list_assets, get_asset | ✓ | ✓ | ✓ | ✓ | ✓ (scoped) | ✓ | ✓ | — |
| create_asset, update_asset | ✓ | ✓ | ✓ | — | — | — | — | — |
| transition_asset_status | ✓ | ✓ | ✓ | — | — | ✓ | — | — |
| search_assets_by_udi | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| list/get supplier | ✓ | ✓ | ✓ | — | — | — | — | ✓ |
| create/update supplier | ✓ | — | ✓ | — | — | — | — | — |
| list_locations_tree, list_departments_tree | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| create_location/department/category | ✓ | ✓ (dept) | — | ✓ (category) | — | — | — | — |
| list/get device_model | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| create/update device_model | ✓ | — | — | ✓ | — | — | — | — |
| list_sla, get_sla_for | All | All | All | All | All | All | All | All |
| list/get audit_events | ✓ | — | — | — | — | ✓ | ✓ | — |
| verify_audit_chain | ✓ | — | — | — | — | ✓ | — | — |
| list/get capa | ✓ | ✓ | ✓ | — | — | ✓ | — | — |
| create_capa | ✓ | — | ✓ | ✓ | — | ✓ | — | — |
| update_capa, close_capa | ✓ | — | — | — | — | ✓ | — | — |
| list/get lifecycle_events | All | All | All | All | All | All | All | All |
| list/get incident | All | All | All | All | All | All | All | All |
| create_incident, submit_incident | All | All | All | All | All | All | — | All |
| close_incident | ✓ | ✓ | — | — | — | ✓ | — | — |
| scheduler triggers | ✓ | — | — | — | — | — | — | — |

---

## 6. Changelog

### v3.0.0 — 2026-04-18 (breaking)

**Added:**
- Endpoint `transition_asset_status` — wrapper service duy nhất để đổi `lifecycle_status` (BR-00-02).
- Endpoint `verify_audit_chain` — kiểm tra SHA-256 integrity của IMM Audit Trail (BR-00-03).
- Endpoint `get_asset_lifecycle_history` — trả toàn bộ Lifecycle Event + Audit Trail của 1 asset.
- Endpoint `search_assets_by_udi` và `get_assets_due_pm`.
- 3 scheduler manual trigger cho admin: `trigger_check_capa_overdue`, `trigger_check_vendor_contract_expiry`, `trigger_check_registration_expiry`.
- Response envelope mới: `{success, data}` / `{success, error, code}` — thay thế `{status, message, data}` của v2.
- Utils helpers `_ok(data)` / `_err(msg, code)` tại `assetcore/utils/response.py`.
- Pagination chuẩn hoá qua `utils/pagination.py` (`page`, `page_size` max 100).

**Changed:**
- Tên field DocType theo native AssetCore prefix `AC-`: `AC Asset`, `AC Supplier`, `AC Location`, `AC Department`, `AC Asset Category`.
- Permission matrix cập nhật theo Role fixtures mới (`fixtures/imm_roles.json`).
- Error codes chuẩn hoá `AC-Exxx` + `VR-00-xx` + HTTP standard.

**Removed (breaking):**
- Toàn bộ endpoint sidecar trên `IMM Asset Profile` (v2) — xoá.
- Endpoint `sync_single_asset_profile`, `sync_asset_profile_status` — xoá.
- Endpoint trên `Vendor Profile` và `Location Ext` — xoá (DocType không còn).
- Field HTM trên profile sidecar đã di chuyển lên `AC Asset` first-class.

**Migration từ v2:**
- Client phải đổi path: `assetcore.api.imm00.sync_single_asset_profile` → **xoá khỏi integration**.
- Đổi tất cả reference `ERPNext Asset` / `Supplier` / `Location` → `AC Asset` / `AC Supplier` / `AC Location`.
- Cập nhật parser response: `response.message.data` vẫn giữ; `response.message.status = "ok"` đổi sang `response.message.success = true`.

### v2.0.0 — 2025-11 (deprecated)

Bản cũ dùng IMM Asset Profile sidecar kết hợp ERPNext Asset. Không còn được hỗ trợ từ v3.0.0.

---

## 7. Phụ lục — Mapping endpoint ↔ Business Rule

| Endpoint | Business Rule áp dụng |
|---|---|
| `create_device_model`, `update_device_model` | BR-00-01, VR-00-03 |
| `transition_asset_status`, `update_asset` | BR-00-02, BR-00-04, BR-00-10 |
| `list_audit_events`, `verify_audit_chain` | BR-00-03 |
| `create_asset`, `update_asset` (validate), Work Order APIs (module khác) | BR-00-05 (gọi `validate_asset_for_operations`) |
| `create_supplier`, `update_supplier` | BR-00-06 |
| SLA Policy controller (validate) | BR-00-07 |
| `close_capa` | BR-00-08 |
| Scheduler `trigger_check_capa_overdue` | BR-00-09 |
| `create_incident`, `submit_incident`, `close_incident` | VR-00-04, AC-E008, AC-E009 |

---

**Hết tài liệu — IMM-00 API Interface v3.0.0**
