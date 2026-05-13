# IMM-09 — API Interface Specification

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-09 — Corrective Maintenance / Repair |
| Phiên bản | 2.0.0 |
| Ngày cập nhật | 2026-04-18 |
| Trạng thái | LIVE |
| Base path | `assetcore.api.imm09` |
| URL pattern | `/api/method/assetcore.api.imm09.<function>` |
| Tác giả | AssetCore Team |

---

## 1. Authentication

| Phương thức | Header / Cookie |
|---|---|
| API Token | `Authorization: token <api_key>:<api_secret>` |
| Session (FE SPA) | `Cookie: sid=<session_id>` |

Permission per endpoint xem §3 chi tiết. User không có Role hợp lệ → HTTP 403.

---

## 2. Response Format

Helpers: `assetcore/utils/helpers.py` (`_ok`, `_err`).

**Success:**

```json
{ "message": { "success": true, "data": { /* payload */ } } }
```

**Error:**

```json
{ "message": { "success": false, "error": "Thông báo tiếng Việt", "code": "CM-XXX" } }
```

Frappe wrap toàn bộ trong `message`. Client parse `response.json().message`.

### 2.1 Pagination convention

```json
{
  "data": [ /* items */ ],
  "pagination": { "page": 1, "page_size": 20, "total": 137, "total_pages": 7 }
}
```

`page` 1-based, `page_size` mặc định 20.

---

## 3. Endpoints (12)

| # | Function | Method | Permission | Mô tả |
|---|---|---|---|---|
| 3.1 | `list_repair_work_orders` | GET | All authenticated | List WO + filter + pagination |
| 3.2 | `get_repair_work_order` | GET | All authenticated | Detail WO + asset_info |
| 3.3 | `create_repair_work_order` | POST | Workshop Manager / CMMS Admin | Tạo WO mới |
| 3.4 | `assign_technician` | POST | Workshop Manager | Phân công KTV |
| 3.5 | `submit_diagnosis` | POST | KTV HTM | Nộp chẩn đoán |
| 3.6 | `request_spare_parts` | POST | KTV / Kho | Cập nhật stock_entry_ref |
| 3.7 | `start_repair` | POST | KTV HTM | Bắt đầu sửa chữa |
| 3.8 | `close_work_order` | POST | KTV / Workshop Manager | Đóng WO (Completed hoặc Cannot Repair) |
| 3.9 | `get_repair_kpis` | GET | PTP / Manager | KPI tháng |
| 3.10 | `get_mttr_report` | GET | PTP / Manager | MTTR trend + breakdown |
| 3.11 | `search_spare_parts` | GET | KTV HTM | Tìm Item vật tư (chưa whitelist trong code v2.0; xem §6) |
| 3.12 | `get_asset_repair_history` | GET | All authenticated | Lịch sử sửa chữa của 1 thiết bị |

---

### 3.1 `list_repair_work_orders`

| Method | Path |
|---|---|
| GET | `assetcore.api.imm09.list_repair_work_orders` |

**Query params:**

```json
{
  "filters": "{\"status\":[\"in\",[\"Open\",\"Assigned\"]],\"priority\":\"Urgent\"}",
  "page": 1,
  "page_size": 20
}
```

`filters` là JSON string. Toán tử Frappe-style: exact, `["in", [...]]`, `[">=", val]`, `["like", "%x%"]`.

**Fields trả về:** `name, asset_ref, asset_name, repair_type, priority, status, open_datetime, completion_datetime, mttr_hours, sla_breached, is_repeat_failure, assigned_to, root_cause_category, risk_class`.

**Response 200:**

```json
{
  "success": true,
  "data": {
    "data": [
      {
        "name": "WO-CM-2026-00042",
        "asset_ref": "AC-ASSET-2026-00042",
        "asset_name": "Máy thở Drager Evita V800",
        "repair_type": "Corrective",
        "priority": "Urgent",
        "status": "In Repair",
        "open_datetime": "2026-04-14 07:15:00",
        "completion_datetime": null,
        "mttr_hours": null,
        "sla_breached": 0,
        "is_repeat_failure": 0,
        "assigned_to": "ktv.anha@hospital.vn",
        "root_cause_category": "Electrical",
        "risk_class": "Class III"
      }
    ],
    "pagination": { "page": 1, "page_size": 20, "total": 1, "total_pages": 1 }
  }
}
```

**cURL:**

```bash
curl -G "https://acme.local/api/method/assetcore.api.imm09.list_repair_work_orders" \
  -H "Authorization: token KEY:SECRET" \
  --data-urlencode 'filters={"status":["in",["Open","Assigned"]]}' \
  --data-urlencode 'page=1' --data-urlencode 'page_size=20'
```

---

### 3.2 `get_repair_work_order`

| Method | Path |
|---|---|
| GET | `assetcore.api.imm09.get_repair_work_order` |

**Params:** `?name=WO-CM-2026-00042`

**Response 200:** full doc + `asset_info` enrichment:

```json
{
  "success": true,
  "data": {
    "name": "WO-CM-2026-00042",
    "asset_ref": "AC-ASSET-2026-00042",
    "asset_name": "Máy thở Drager Evita V800",
    "asset_category": "Ventilator",
    "risk_class": "Class III",
    "serial_no": "DRG-2024-001234",
    "incident_report": "IR-2026-00123",
    "source_pm_wo": null,
    "repair_type": "Corrective",
    "priority": "Urgent",
    "status": "In Repair",
    "open_datetime": "2026-04-14 07:15:00",
    "assigned_datetime": "2026-04-14 08:30:00",
    "sla_target_hours": 24.0,
    "mttr_hours": null,
    "sla_breached": 0,
    "is_repeat_failure": 0,
    "assigned_to": "ktv.anha@hospital.vn",
    "diagnosis_notes": "Tụ điện C12 phồng và cháy",
    "root_cause_category": "Electrical",
    "spare_parts_used": [
      { "item_code": "CAP-100UF-25V", "qty": 2, "unit_cost": 25000,
        "total_cost": 50000, "stock_entry_ref": "STE-2026-00456" }
    ],
    "repair_checklist": [],
    "firmware_updated": 0,
    "asset_info": {
      "asset_name": "Máy thở Drager Evita V800",
      "asset_category": "Ventilator",
      "status": "Under Repair",
      "custom_risk_class": "Class III",
      "serial_no": "DRG-2024-001234",
      "custom_last_repair_date": "2026-01-15",
      "custom_mttr_avg_hours": 16.4
    }
  }
}
```

**Errors:** 404 `NOT_FOUND` nếu WO không tồn tại.

---

### 3.3 `create_repair_work_order`

| Method | Path |
|---|---|
| POST | `assetcore.api.imm09.create_repair_work_order` |

**Body required:** `asset_ref, repair_type, priority, failure_description`. Phải có `incident_report` HOẶC `source_pm_wo`.

```json
{
  "asset_ref": "AC-ASSET-2026-00042",
  "repair_type": "Corrective",
  "priority": "Urgent",
  "failure_description": "Máy thở không tạo được áp suất, báo alarm E-04",
  "incident_report": "IR-2026-00123",
  "source_pm_wo": ""
}
```

**Side-effects:**

- Validate BR-09-01 (nguồn) + check duplicate active WO.
- Tính `sla_target_hours` qua `get_sla_target(risk_class, priority)`.
- Insert Asset Repair với `status = Open`, `open_datetime = now()`.
- `frappe.db.set_value("Asset", asset_ref, "status", "Under Repair")`.
- Tạo `Asset Lifecycle Event` event_type `repair_opened`.
- `frappe.db.commit()`.

**Response 200:**

```json
{ "success": true, "data": { "name": "WO-CM-2026-00042", "status": "Open", "sla_target_hours": 24.0 } }
```

**Errors:**

- `CM-001` — thiếu cả `incident_report` và `source_pm_wo`.
- `CM-002` — asset đã có WO active (`status NOT IN (Completed, Cannot Repair, Cancelled)`).
- `NOT_FOUND` — `asset_ref` không tồn tại.

---

### 3.4 `assign_technician`

| Method | Path |
|---|---|
| POST | `assetcore.api.imm09.assign_technician` |

**Body:** `name, technician, priority?`

```json
{ "name": "WO-CM-2026-00042", "technician": "ktv.anha@hospital.vn", "priority": "Urgent" }
```

**Side-effects:**

- Chỉ chạy khi `status = "Open"`.
- Set `assigned_to`, `assigned_by = session.user`, `assigned_datetime = now()`, `status = "Assigned"`.

**Response 200:** `{ "name": "...", "status": "Assigned", "assigned_to": "ktv.anha@hospital.vn" }`

**Errors:** generic 400 nếu status không hợp lệ.

---

### 3.5 `submit_diagnosis`

| Method | Path |
|---|---|
| POST | `assetcore.api.imm09.submit_diagnosis` |

**Body:** `name, diagnosis_notes, needs_parts (0|1)`

```json
{
  "name": "WO-CM-2026-00042",
  "diagnosis_notes": "Tụ điện C12 trên board nguồn bị phồng và cháy. Thay tương đương CAP-100UF-25V.",
  "needs_parts": 1
}
```

**Side-effects:**

- Chỉ chạy khi `status IN (Assigned, Diagnosing)`.
- Set `diagnosis_notes`, `status = Pending Parts` (nếu `needs_parts=1`) hoặc `In Repair`.
- Sinh ALE `diagnosis_submitted`.

**Response 200:** `{ "name": "...", "status": "Pending Parts" }`

---

### 3.6 `request_spare_parts`

| Method | Path |
|---|---|
| POST | `assetcore.api.imm09.request_spare_parts` |

**Body:** `name, parts` (JSON list of `{item_code, stock_entry_ref}`)

```json
{
  "name": "WO-CM-2026-00042",
  "parts": "[{\"item_code\":\"CAP-100UF-25V\",\"stock_entry_ref\":\"STE-2026-00456\"}]"
}
```

**Side-effects:** cập nhật `stock_entry_ref` trên các row `spare_parts_used` khớp `item_code`. Nếu `status = Pending Parts` → chuyển sang `In Repair`.

**Response:** `{ "name": "...", "status": "In Repair", "updated": 1 }`

> Note: Endpoint này yêu cầu các spare part rows đã tồn tại sẵn trên WO (qua FE form). Endpoint chỉ gắn chứng từ.

---

### 3.7 `start_repair`

| Method | Path |
|---|---|
| POST (whitelist methods=["POST"]) | `assetcore.api.imm09.start_repair` |

**Body:** `{ "name": "WO-CM-2026-00042" }`

Chỉ chạy khi `status IN (Assigned, Diagnosing, Pending Parts)`. Đổi `status = In Repair`.

---

### 3.8 `close_work_order`

| Method | Path |
|---|---|
| POST | `assetcore.api.imm09.close_work_order` |

**Body:**

```json
{
  "name": "WO-CM-2026-00042",
  "repair_summary": "Đã thay tụ C12, đo điện áp đầu ra board nguồn 24V DC ± 0.5V — đạt.",
  "root_cause_category": "Electrical",
  "dept_head_name": "BS. CK2 Nguyễn Văn Hùng",
  "checklist_results": "[{\"idx\":1,\"test_description\":\"Điện áp đầu vào\",\"result\":\"Pass\",\"measured_value\":\"218V\"}]",
  "spare_parts": "[]",
  "firmware_updated": 0,
  "firmware_change_request": "",
  "cannot_repair": 0,
  "cannot_repair_reason": ""
}
```

**Two modes:**

| Mode | `cannot_repair` | Hành vi |
|---|---|---|
| Completed | 0 | Set fields, `status = Pending Inspection`, `doc.submit()` (kích hoạt `before_submit` validate BR-09-02/03/04 + `on_submit` complete_repair) |
| Cannot Repair | 1 | Set `cannot_repair_reason`, `status = Cannot Repair`; `Asset.status = Out of Service`; ALE `cannot_repair` |

**Response 200 (Completed):**

```json
{ "success": true, "data": { "name": "WO-CM-2026-00042", "status": "Completed", "mttr_hours": 18.5, "sla_breached": 0 } }
```

**Response 200 (Cannot Repair):**

```json
{ "success": true, "data": { "name": "WO-CM-2026-00042", "status": "Cannot Repair", "asset_status": "Out of Service" } }
```

**Errors trong submit:** `CM-003` (stock entry), `CM-005`/`CM-006` (FCR), `CM-007`/`CM-008` (checklist).

---

### 3.9 `get_repair_kpis`

| Method | Path |
|---|---|
| GET | `assetcore.api.imm09.get_repair_kpis` |

**Params:** `?year=2026&month=4` (default = tháng hiện tại)

**Response 200:**

```json
{
  "success": true,
  "data": {
    "kpis": {
      "total_completed": 14,
      "mttr_avg_hours": 18.5,
      "sla_compliance_pct": 85.7,
      "repeat_failure_count": 2,
      "open_wos": 12
    },
    "root_cause_breakdown": [
      { "category": "Electrical", "count": 7 },
      { "category": "Mechanical", "count": 4 },
      { "category": "Software", "count": 2 },
      { "category": "User Error", "count": 1 }
    ]
  }
}
```

---

### 3.10 `get_mttr_report`

| Method | Path |
|---|---|
| GET | `assetcore.api.imm09.get_mttr_report` |

**Params:** `?year=2026&month=4`

**Response 200:**

```json
{
  "success": true,
  "data": {
    "mttr_avg": 18.5,
    "first_fix_rate": 85.7,
    "backlog_count": 12,
    "cost_per_repair": 450000,
    "mttr_trend": [
      { "month": "2025-11", "value": 22.0 },
      { "month": "2025-12", "value": 19.5 },
      { "month": "2026-01", "value": 25.1 },
      { "month": "2026-02", "value": 21.0 },
      { "month": "2026-03", "value": 20.6 },
      { "month": "2026-04", "value": 18.5 }
    ],
    "backlog_by_dept": [
      { "dept": "ICU", "count": 5 },
      { "dept": "OR", "count": 4 },
      { "dept": "Radiology", "count": 3 }
    ]
  }
}
```

`first_fix_rate` = `(1 − is_repeat_failure rate) × 100`. `cost_per_repair` = avg `total_parts_cost` của WO Completed trong tháng.

---

### 3.11 `search_spare_parts`

| Method | Path |
|---|---|
| GET | `assetcore.api.imm09.search_spare_parts` |

> **Implementation note:** chưa có function này trong `api/imm09.py` v2.0 (xem §6 Inconsistencies). FE `CMPartsView.vue` hiện gọi trực tiếp `frappe.client.get_list` với DocType `Item`. Khuyến nghị bổ sung endpoint chính thức.

**Params (proposed):** `?query=tụ&limit=20`

**Response shape (proposed):**

```json
{
  "success": true,
  "data": [
    { "item_code": "CAP-100UF-25V", "item_name": "Tụ điện 100uF 25V",
      "stock_uom": "Cái", "qty_in_stock": 5, "unit_cost": 25000 }
  ]
}
```

---

### 3.12 `get_asset_repair_history`

| Method | Path |
|---|---|
| GET | `assetcore.api.imm09.get_asset_repair_history` |

**Params:** `?asset_ref=AC-ASSET-2026-00042&limit=10`

**Response 200:**

```json
{
  "success": true,
  "data": {
    "asset_ref": "AC-ASSET-2026-00042",
    "history": [
      {
        "name": "WO-CM-2026-00042",
        "repair_type": "Corrective",
        "priority": "Urgent",
        "open_datetime": "2026-04-14 07:15:00",
        "completion_datetime": "2026-04-15 14:30:00",
        "mttr_hours": 31.25,
        "sla_breached": 1,
        "root_cause_category": "Electrical",
        "repair_summary": "Thay tụ C12..."
      }
    ]
  }
}
```

Chỉ trả về WO `docstatus = 1` (đã Submit). Sort `open_datetime desc`. `limit` mặc định 10.

---

## 4. Error Codes

| Code | HTTP | Business Rule | Mô tả |
|---|---|---|---|
| `CM-001` | 400 | BR-09-01 | WO thiếu cả `incident_report` và `source_pm_wo` |
| `CM-002` | 409 | BR-09-05 | Asset đã có WO active đang mở |
| `CM-003` | 422 | BR-09-02 | Spare parts row thiếu `stock_entry_ref` |
| `CM-004` | 422 | BR-09-02 | `stock_entry_ref` không tồn tại trong DB |
| `CM-005` | 422 | BR-09-03 | `firmware_updated=1` nhưng không có FCR linked |
| `CM-006` | 422 | BR-09-03 | FCR linked status ≠ `Approved` |
| `CM-007` | 422 | BR-09-04 | Checklist row chưa điền `result` |
| `CM-008` | 422 | BR-09-04 | Checklist có row `result = Fail` |
| `CM-009` | 404 | — | `asset_ref` không tồn tại |
| `CM-010` | 403 | — | User không có quyền (role mismatch) |
| `CM-011` | 404 | — | WO `name` không tồn tại |
| `CM-012` | 422 | — | Transition status không hợp lệ |
| `CM-013` | 400 | — | Thiếu `dept_head_name` khi close (Completed mode) |
| `NOT_FOUND` | 404 | — | Generic "not found" — dùng cho `get_repair_work_order`, `create_repair_work_order` (asset không tồn tại) |

---

## 5. Webhook Events (Realtime)

| Channel | Sự kiện | Payload | Subscriber |
|---|---|---|---|
| `cm_sla_breached` | Scheduler hourly phát hiện WO vượt SLA | `{ "wo": "WO-CM-...", "asset": "AC-ASSET-..." }` | KTV được gán (`assigned_to`) |

Phát qua `frappe.publish_realtime(channel, payload, user=...)`. FE subscribe trong `stores/imm09.ts` qua `socket.on('cm_sla_breached', ...)`.

---

## 6. Implementation Notes & Inconsistencies

### 6.1 Path map docs ↔ code

| Docs (v1) | Code thực tế (v2.0) |
|---|---|
| `create_repair_wo` | `create_repair_work_order` |
| `submit_repair_result` | (gộp vào `close_work_order` qua arg `spare_parts`/`checklist_results`) |
| `complete_repair` | `close_work_order` (mode Completed) |
| `mark_cannot_repair` | `close_work_order(cannot_repair=1)` |
| `get_repair_wo` | `get_repair_work_order` |
| `get_repair_list` | `list_repair_work_orders` |
| `get_repair_backlog` | (lấy từ `get_mttr_report.backlog_*`) |
| `create_firmware_fcr` / `approve_firmware_fcr` | (chưa có endpoint riêng — qua Frappe form `Firmware Change Request`) |

### 6.2 Pending implementation

| Hạng mục | Trạng thái |
|---|---|
| `search_spare_parts` endpoint | Chưa có trong `api/imm09.py` — FE đang gọi `frappe.client.get_list` (Item) |
| `create_firmware_fcr` / `approve_firmware_fcr` | Quản lý qua Frappe Desk form FCR |
| MTTR theo working hours (Mon–Fri 07:00–17:00) | `complete_repair()` hiện tính **calendar time** (`time_diff_in_seconds`). Spec cũ đề cập working hours — chưa implement util `get_working_hours_between` |
| `get_repair_backlog` standalone endpoint | Backlog gộp trong `get_mttr_report.backlog_count` + `backlog_by_dept` |

### 6.3 Whitelist & permission

Tất cả endpoint dùng `@frappe.whitelist()` (default GET+POST). `start_repair` dùng `@frappe.whitelist(methods=["POST"])`.

Function `_apply_checklist`, `_apply_spare_parts`, `_mark_cannot_repair`, `_month_range`, `_mttr_trend`, `_create_lifecycle_event` là helpers nội bộ — không expose qua API.

### 6.4 `ignore_permissions=True` & `ignore_links=True`

Hiện code dùng `doc.flags.ignore_links = True` và `save(ignore_permissions=True)` để tránh kiểm tra link vào ERPNext Asset / Stock Entry trong môi trường test. Production cần review để bật permission check đầy đủ.

---

## 7. Mapping endpoint ↔ Business Rule

| Endpoint | Business Rule áp dụng |
|---|---|
| `create_repair_work_order` | BR-09-01, BR-09-05, BR-09-06 |
| `assign_technician` | BR-09-05 (transition Open → Assigned) |
| `submit_diagnosis` | (state machine) |
| `request_spare_parts` | BR-09-02 (gắn stock_entry_ref) |
| `start_repair` | (state machine) |
| `close_work_order` (Completed) | BR-09-02, BR-09-03, BR-09-04, BR-09-05, BR-09-07 |
| `close_work_order` (Cannot Repair) | BR-09-05 (Asset → Out of Service) |
| `get_repair_kpis` / `get_mttr_report` | BR-09-07 (KPI tracking) |
| `get_asset_repair_history` | Audit / traceability (BR-09-06 detect repeat) |

---

*End of API Interface v2.0.0 — IMM-09 Corrective Maintenance.*
