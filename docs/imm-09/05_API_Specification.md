# IMM-09 — API Specification

| Thuộc tính | Giá trị |
|---|---|
| Module | **IMM-09 — Corrective Maintenance / Repair** |
| Phiên bản tài liệu | 1.0 |
| Ngày cập nhật | 2026-05-14 |
| Trạng thái | Chuẩn hóa từ IMM-09_API_Interface.md |
| Base path | `assetcore.api.imm09` |
| URL pattern | `/api/method/assetcore.api.imm09.<function>` |

---

## §1 Tổng quan

### §1.1 Response Envelope

**Thành công:**

```json
{
  "success": true,
  "data": { /* payload */ }
}
```

**Lỗi:**

```json
{
  "success": false,
  "error": "Thông báo lỗi tiếng Việt",
  "code": "CM-XXX"
}
```

> Helpers `_ok(data)` / `_err(code, msg)` tại `assetcore/utils/helpers.py`.
> Frappe wraps toàn bộ phản hồi trong `message`. FE parse: `response.json().message`.

### §1.2 Authentication

| Phương thức | Header / Cookie |
|---|---|
| API Token | `Authorization: token <api_key>:<api_secret>` |
| Session (FE SPA) | `Cookie: sid=<session_id>` |

User không có Role hợp lệ → HTTP 403 + `CM-010`.

### §1.3 Phân trang

```json
{
  "data": [ /* items */ ],
  "pagination": { "page": 1, "page_size": 20, "total": 137, "total_pages": 7 }
}
```

`page` 1-based, `page_size` mặc định 20.

### §1.4 API Catalog

| # | Function | Method | Permission | Mô tả |
|---|---|---|---|---|
| 3.1 | `list_repair_work_orders` | GET | Tất cả có đăng nhập | Danh sách WO + filter + phân trang |
| 3.2 | `get_repair_work_order` | GET | Tất cả có đăng nhập | Chi tiết WO + asset_info enriched |
| 3.3 | `create_repair_work_order` | POST | Workshop Manager / CMMS Admin | Tạo WO mới |
| 3.4 | `assign_technician` | POST | Workshop Manager | Phân công Kỹ thuật viên |
| 3.5 | `submit_diagnosis` | POST | KTV HTM | Nộp chẩn đoán |
| 3.6 | `request_spare_parts` | POST | KTV HTM / Kho | Cập nhật stock_entry_ref |
| 3.7 | `start_repair` | POST | KTV HTM | Bắt đầu sửa chữa |
| 3.8 | `close_work_order` | POST | KTV HTM / Workshop Manager | Đóng WO → Pending Inspection (Completed) hoặc Cannot Repair |
| 3.9 | `confirm_inspection` | POST | Dept Head / QA Officer | Nghiệm thu: Pending Inspection → Completed (submit docstatus=1) |
| 3.10 | `get_repair_kpis` | GET | PTP / Manager | KPI tháng hiện tại |
| 3.11 | `get_mttr_report` | GET | PTP / Manager | MTTR trend + breakdown 6 tháng |
| 3.12 | `search_spare_parts` | GET | KTV HTM | Tìm kiếm vật tư (Item) |
| 3.13 | `get_asset_repair_history` | GET | Tất cả có đăng nhập | Lịch sử sửa chữa 1 thiết bị |

---

## §2 Whitelist & Permission Matrix

| Function | Whitelist | Roles |
|---|---|---|
| `list_repair_work_orders` | `@frappe.whitelist()` | All authenticated |
| `get_repair_work_order` | `@frappe.whitelist()` | All authenticated |
| `create_repair_work_order` | `@frappe.whitelist()` | Workshop Manager, CMMS Admin |
| `assign_technician` | `@frappe.whitelist()` | Workshop Manager |
| `submit_diagnosis` | `@frappe.whitelist()` | KTV HTM, Workshop Manager |
| `request_spare_parts` | `@frappe.whitelist()` | KTV HTM, Workshop Manager, Kho vật tư |
| `start_repair` | `@frappe.whitelist(methods=["POST"])` | KTV HTM, Workshop Manager |
| `close_work_order` | `@frappe.whitelist()` | KTV HTM, Workshop Manager, CMMS Admin |
| `get_repair_kpis` | `@frappe.whitelist()` | PTP Khối 2, Workshop Manager, CMMS Admin |
| `get_mttr_report` | `@frappe.whitelist()` | PTP Khối 2, Workshop Manager, CMMS Admin |
| `search_spare_parts` | `@frappe.whitelist()` | KTV HTM, Workshop Manager, Kho vật tư |
| `get_asset_repair_history` | `@frappe.whitelist()` | All authenticated |

---

## §3 Endpoint Specifications

### 3.1 `list_repair_work_orders`

**Mô tả:** Lấy danh sách Asset Repair WO với filter động và phân trang.

| Method | Path |
|---|---|
| GET | `/api/method/assetcore.api.imm09.list_repair_work_orders` |

**Query params:**

| Param | Kiểu | Bắt buộc | Mô tả |
|---|---|---|---|
| `filters` | JSON string | Không | Filter Frappe-style: exact, `["in",[...]]`, `[">=",val]`, `["like","%x%"]` |
| `page` | int | Không | Trang hiện tại (mặc định 1) |
| `page_size` | int | Không | Kích thước trang (mặc định 20) |

**Ví dụ request:**

```bash
curl -G "https://acme.local/api/method/assetcore.api.imm09.list_repair_work_orders" \
  -H "Authorization: token KEY:SECRET" \
  --data-urlencode 'filters={"status":["in",["Open","Assigned"]],"priority":"Urgent"}' \
  --data-urlencode 'page=1' --data-urlencode 'page_size=20'
```

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

**Fields trả về:** `name`, `asset_ref`, `asset_name`, `repair_type`, `priority`, `status`, `open_datetime`, `completion_datetime`, `mttr_hours`, `sla_breached`, `is_repeat_failure`, `assigned_to`, `root_cause_category`, `risk_class`.

---

### 3.2 `get_repair_work_order`

**Mô tả:** Chi tiết đầy đủ 1 WO, bao gồm `asset_info` enriched từ AC_Asset.

| Method | Path |
|---|---|
| GET | `/api/method/assetcore.api.imm09.get_repair_work_order` |

**Query params:** `?name=WO-CM-2026-00042`

**Response 200:**

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
      {
        "item_code": "CAP-100UF-25V",
        "qty": 2,
        "unit_cost": 25000,
        "total_cost": 50000,
        "stock_entry_ref": "STE-2026-00456"
      }
    ],
    "repair_checklist": [],
    "firmware_updated": 0,
    "asset_info": {
      "asset_name": "Máy thở Drager Evita V800",
      "asset_category": "Ventilator",
      "lifecycle_status": "Under Repair",
      "risk_classification": "Class III",
      "manufacturer_sn": "DRG-2024-001234",
      "department": "ICU-01",
      "location": "LOC-A3"
    }
  }
}
```

**Lỗi:** `CM-011` (404) nếu WO không tồn tại.

---

### 3.3 `create_repair_work_order`

**Mô tả:** Tạo mới Asset Repair WO, validate nguồn (BR-09-01), kiểm tra duplicate (BR-09-05), tính SLA target, tạo Asset Lifecycle Event `repair_opened`.

| Method | Path |
|---|---|
| POST | `/api/method/assetcore.api.imm09.create_repair_work_order` |

**Request body:**

| Field | Kiểu | Bắt buộc | Mô tả |
|---|---|---|---|
| `asset_ref` | string | Có | Link đến AC_Asset |
| `repair_type` | string | Có | `"Corrective"` / `"Emergency"` / `"Warranty"` |
| `priority` | string | Có | `"Normal"` / `"Urgent"` / `"Emergency"` |
| `failure_description` | string | Có | Mô tả sự cố ban đầu |
| `incident_report` | string | Có* | Link đến Incident Report (bắt buộc nếu không có `source_pm_wo`) |
| `source_pm_wo` | string | Có* | Link đến PM Work Order nguồn (bắt buộc nếu không có `incident_report`) |

\* Phải có ít nhất một trong hai.

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
1. Validate BR-09-01 (nguồn) + BR-09-05 (kiểm tra duplicate WO active).
2. Tính `sla_target_hours` qua `get_sla_target(risk_class, priority)`.
3. Insert Asset Repair với `status = "Open"`, `open_datetime = now()`.
4. `frappe.db.set_value("Asset", asset_ref, "status", "Under Repair")`.
5. Tạo Asset Lifecycle Event `event_type = "repair_opened"`.
6. `frappe.db.commit()`.

**Response 200:**

```json
{
  "success": true,
  "data": {
    "name": "WO-CM-2026-00042",
    "status": "Open",
    "sla_target_hours": 24.0
  }
}
```

**Lỗi:**

| Code | Mô tả |
|---|---|
| `CM-001` | Thiếu cả `incident_report` và `source_pm_wo` |
| `CM-002` | Asset đã có WO active |
| `CM-009` | `asset_ref` không tồn tại |

---

### 3.4 `assign_technician`

**Mô tả:** Phân công KTV cho WO đang ở trạng thái `Open`.

| Method | Path |
|---|---|
| POST | `/api/method/assetcore.api.imm09.assign_technician` |

**Request body:**

| Field | Kiểu | Bắt buộc | Mô tả |
|---|---|---|---|
| `name` | string | Có | WO name |
| `technician` | string | Có | Email KTV |
| `priority` | string | Không | Override priority nếu cần |

```json
{
  "name": "WO-CM-2026-00042",
  "technician": "ktv.anha@hospital.vn",
  "priority": "Urgent"
}
```

**Side-effects:**
- Chỉ thực hiện khi `status = "Open"`.
- Set `assigned_to`, `assigned_by = frappe.session.user`, `assigned_datetime = now()`, `status = "Assigned"`.

**Response 200:**

```json
{
  "success": true,
  "data": {
    "name": "WO-CM-2026-00042",
    "status": "Assigned",
    "assigned_to": "ktv.anha@hospital.vn"
  }
}
```

**Lỗi:** `CM-012` (422) nếu status không phải `"Open"`.

---

### 3.5 `submit_diagnosis`

**Mô tả:** KTV nộp kết quả chẩn đoán — xác định nguyên nhân gốc rễ và nhu cầu vật tư.

| Method | Path |
|---|---|
| POST | `/api/method/assetcore.api.imm09.submit_diagnosis` |

**Request body:**

| Field | Kiểu | Bắt buộc | Mô tả |
|---|---|---|---|
| `name` | string | Có | WO name |
| `diagnosis_notes` | string | Có | Mô tả kỹ thuật chẩn đoán |
| `needs_parts` | int | Có | `1` = cần vật tư (→ Pending Parts), `0` = không cần (→ In Repair) |

```json
{
  "name": "WO-CM-2026-00042",
  "diagnosis_notes": "Tụ điện C12 trên board nguồn bị phồng và cháy. Thay tương đương CAP-100UF-25V.",
  "needs_parts": 1
}
```

**Side-effects:**
- Chỉ thực hiện khi `status IN ("Assigned", "Diagnosing")`.
- Set `diagnosis_notes`, `root_cause_category`.
- Nếu `needs_parts = 1` → `status = "Pending Parts"`.
- Nếu `needs_parts = 0` → `status = "In Repair"`.
- Sinh ALE `event_type = "diagnosis_submitted"`.

**Response 200:**

```json
{
  "success": true,
  "data": {
    "name": "WO-CM-2026-00042",
    "status": "Pending Parts"
  }
}
```

**Lỗi:** `CM-012` nếu status không hợp lệ cho transition.

---

### 3.6 `request_spare_parts`

**Mô tả:** Gắn phiếu xuất kho (`stock_entry_ref`) vào các dòng vật tư của WO.

| Method | Path |
|---|---|
| POST | `/api/method/assetcore.api.imm09.request_spare_parts` |

**Request body:**

| Field | Kiểu | Bắt buộc | Mô tả |
|---|---|---|---|
| `name` | string | Có | WO name |
| `parts` | JSON string | Có | List `[{"item_code": "...", "stock_entry_ref": "..."}]` |

```json
{
  "name": "WO-CM-2026-00042",
  "parts": "[{\"item_code\":\"CAP-100UF-25V\",\"stock_entry_ref\":\"STE-2026-00456\"}]"
}
```

**Side-effects:**
- Cập nhật `stock_entry_ref` trên các row `spare_parts_used` khớp `item_code`.
- Nếu `status = "Pending Parts"` → chuyển sang `"In Repair"`.

> Lưu ý: Endpoint chỉ gắn chứng từ, không tạo spare part row mới. Các row phải được thêm qua FE form trước.

**Response 200:**

```json
{
  "success": true,
  "data": {
    "name": "WO-CM-2026-00042",
    "status": "In Repair",
    "updated": 1
  }
}
```

---

### 3.7 `start_repair`

**Mô tả:** Chuyển WO sang trạng thái `In Repair` khi KTV bắt đầu sửa chữa thực tế.

| Method | Path |
|---|---|
| POST | `/api/method/assetcore.api.imm09.start_repair` |

**Request body:**

```json
{ "name": "WO-CM-2026-00042" }
```

**Side-effects:**
- Chỉ thực hiện khi `status IN ("Assigned", "Diagnosing", "Pending Parts")`.
- Set `status = "In Repair"`.

**Response 200:**

```json
{
  "success": true,
  "data": {
    "name": "WO-CM-2026-00042",
    "status": "In Repair"
  }
}
```

**Lỗi:** `CM-012` nếu status không hợp lệ cho transition.

---

### 3.8 `close_work_order`

**Mô tả:** KTV hoàn thành sửa chữa → WO chuyển sang `Pending Inspection` (chờ nghiệm thu cấp khoa). Sau đó cần `confirm_inspection` để chốt "Completed". Mode thứ hai là `Cannot Repair`.

| Method | Path |
|---|---|
| POST | `/api/method/assetcore.api.imm09.close_work_order` |

**Request body:**

| Field | Kiểu | Bắt buộc | Mô tả |
|---|---|---|---|
| `name` | string | Có | WO name |
| `repair_summary` | string | Có* | Tóm tắt kết quả sửa chữa (mode Completed) |
| `root_cause_category` | string | Có* | Phân loại nguyên nhân gốc rễ |
| `dept_head_name` | string | Có* | Họ tên trưởng khoa phòng xác nhận (BR-09-04) |
| `checklist_results` | JSON string | Có* | List `[{idx, test_description, result, measured_value}]` |
| `spare_parts` | JSON string | Không | Cập nhật bổ sung vật tư (list SparePartRow) |
| `firmware_updated` | int | Không | `1` = có cập nhật firmware |
| `firmware_change_request` | string | Không | FCR name (bắt buộc nếu `firmware_updated=1`) |
| `cannot_repair` | int | Không | `1` = không thể sửa chữa |
| `cannot_repair_reason` | string | Có** | Lý do không thể sửa (bắt buộc nếu `cannot_repair=1`) |

\* Bắt buộc khi `cannot_repair = 0`.
\*\* Bắt buộc khi `cannot_repair = 1`.

**Mode Completed — request:**

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

**Side-effects (mode `cannot_repair=0`):**
1. Set các trường từ body (`repair_summary`, `root_cause_category`, `dept_head_name`, `checklist_results`, `spare_parts`, `firmware_*`).
2. `status = "Pending Inspection"` — **WO chưa submit ở bước này**.
3. ALE `event_type = "repair_pending_inspection"`.

> Nghiệm thu thực sự xảy ra ở `confirm_inspection` (endpoint 3.9).

**Response 200 (mode Pending Inspection):**

```json
{
  "success": true,
  "data": {
    "name": "WO-CM-2026-00042",
    "status": "Pending Inspection"
  }
}
```

**Side-effects (Cannot Repair mode):**
1. Set `cannot_repair_reason`, `status = "Cannot Repair"`.
2. `Asset.status = "Out of Service"`.
3. ALE `event_type = "cannot_repair"`.

**Response 200 (Cannot Repair):**

```json
{
  "success": true,
  "data": {
    "name": "WO-CM-2026-00042",
    "status": "Cannot Repair",
    "asset_status": "Out of Service"
  }
}
```

**Lỗi trong submit (Completed mode):**

| Code | HTTP | Mô tả |
|---|---|---|
| `CM-003` | 422 | Spare parts row thiếu `stock_entry_ref` |
| `CM-004` | 422 | `stock_entry_ref` không tồn tại trong DB |
| `CM-005` | 422 | `firmware_updated=1` nhưng không có FCR linked |
| `CM-006` | 422 | FCR linked status ≠ `"Approved"` |
| `CM-007` | 422 | Checklist row chưa điền `result` |
| `CM-008` | 422 | Checklist có row `result = "Fail"` |
| `CM-013` | 400 | Thiếu `dept_head_name` |

---

### 3.9 `confirm_inspection`

**Mô tả:** Nghiệm thu sau sửa chữa — bước kiểm soát chất lượng cuối. Chuyển WO từ `Pending Inspection` → `Completed` (submit docstatus=1), kích hoạt `complete_repair()` để tính MTTR, SLA, đưa Asset về Active.

| Method | Path |
|---|---|
| POST | `/api/method/assetcore.api.imm09.confirm_inspection` |

**Role:** `CAN_APPROVE_DEP` (Dept Head / QA Officer / Workshop Manager)

**Request body:**

```json
{ "name": "WO-CM-2026-00042" }
```

**Side-effects:**
1. Kiểm tra status = "Pending Inspection", role `CAN_APPROVE_DEP`.
2. Set `dept_head_confirmation_datetime = now()`.
3. `doc.submit()` → `before_submit` (validate BR-09-02/03/04) → `on_submit` → `complete_repair()`.
4. `complete_repair()`: tính `mttr_hours` (calendar time), set `completion_datetime`, `sla_breached`, Asset→Active, ALE `repair_completed`.
5. Nếu `root_cause_category` chứa từ khóa lặp lại ("lặp lại", "recurring", "chronic"...) → tự động gọi `imm12.detect_chronic_failures()` (non-blocking).

**Response 200:**

```json
{
  "success": true,
  "data": {
    "name": "WO-CM-2026-00042",
    "status": "Completed",
    "mttr_hours": 18.5,
    "sla_breached": 0
  }
}
```

**Errors:**

| Code | Mô tả |
|---|---|
| `NOT_FOUND` | WO không tồn tại |
| `BAD_STATE` | WO không ở trạng thái "Pending Inspection" |
| `FORBIDDEN` | Không có quyền `CAN_APPROVE_DEP` |

---

### 3.11 `get_repair_kpis`

**Mô tả:** KPI bảo trì sửa chữa trong tháng: MTTR, SLA compliance, repeat failure, backlog.

| Method | Path |
|---|---|
| GET | `/api/method/assetcore.api.imm09.get_repair_kpis` |

**Query params:** `?year=2026&month=4` (mặc định = tháng hiện tại)

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

### 3.12 `get_mttr_report`

**Mô tả:** MTTR trend 6 tháng, First-Time Fix Rate, backlog phân theo khoa phòng.

| Method | Path |
|---|---|
| GET | `/api/method/assetcore.api.imm09.get_mttr_report` |

**Query params:** `?year=2026&month=4` (mặc định = tháng hiện tại)

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

**Ghi chú:**
- `first_fix_rate` = `(1 − tỷ lệ is_repeat_failure) × 100`.
- `cost_per_repair` = avg `total_parts_cost` của WO Completed trong tháng.

---

### 3.13 `search_spare_parts`

**Mô tả:** Tìm kiếm vật tư (từ DocType `IMM Device Spare Part`) để thêm vào WO.

| Method | Path |
|---|---|
| GET | `/api/method/assetcore.api.imm09.search_spare_parts` |

**Query params:** `?query=tụ&limit=10` (default limit=10; tối thiểu 2 ký tự mới trả kết quả)

**Response 200:**

```json
{
  "success": true,
  "data": [
    {
      "item_code": "CAP-100UF-25V",
      "item_name": "Tụ điện 100uF 25V",
      "manufacturer_part_no": "CAP-100UF-25V",
      "qty": 1,
      "uom": "Cái",
      "unit_cost": 25000,
      "total_cost": 25000,
      "stock_entry_ref": "",
      "notes": "",
      "idx": 0
    }
  ]
}
```

> **Ghi chú:** Source là `tabIMM Device Spare Part`, tìm theo `part_name` LIKE hoặc `manufacturer_part_no` LIKE. FE `CMPartsView.vue` gọi qua `searchSpareParts()` từ `@/api/imm09`.

---

### 3.14 `get_asset_repair_history`

**Mô tả:** Lịch sử tất cả WO sửa chữa đã hoàn thành của một thiết bị, dùng cho traceability và phát hiện tái hỏng.

| Method | Path |
|---|---|
| GET | `/api/method/assetcore.api.imm09.get_asset_repair_history` |

**Query params:** `?asset_ref=AC-ASSET-2026-00042&limit=10`

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
        "repair_summary": "Thay tụ C12 trên board nguồn..."
      }
    ]
  }
}
```

**Ghi chú:** Chỉ trả về WO có `docstatus = 1` (đã Submit). Sort theo `open_datetime desc`. `limit` mặc định 10.

---

## §4 Error Code Catalog

| Code | HTTP | Business Rule | Mô tả |
|---|---|---|---|
| `CM-001` | 400 | BR-09-01 | WO thiếu cả `incident_report` và `source_pm_wo` |
| `CM-002` | 409 | BR-09-05 | Asset đã có WO active (status ≠ Completed / Cannot Repair / Cancelled) |
| `CM-003` | 422 | BR-09-02 | Spare parts row thiếu `stock_entry_ref` |
| `CM-004` | 422 | BR-09-02 | `stock_entry_ref` không tồn tại trong DB |
| `CM-005` | 422 | BR-09-03 | `firmware_updated=1` nhưng không có FCR linked |
| `CM-006` | 422 | BR-09-03 | FCR linked status ≠ `"Approved"` |
| `CM-007` | 422 | BR-09-04 | Checklist row chưa điền `result` |
| `CM-008` | 422 | BR-09-04 | Checklist có row `result = "Fail"` |
| `CM-009` | 404 | — | `asset_ref` không tồn tại |
| `CM-010` | 403 | — | User không có quyền (role mismatch) |
| `CM-011` | 404 | — | WO `name` không tồn tại |
| `CM-012` | 422 | — | Transition status không hợp lệ |
| `CM-013` | 400 | — | Thiếu `dept_head_name` khi close mode Completed |

---

## §5 FE ↔ BE Error Mapping

| BE code | FE xử lý |
|---|---|
| `CM-001` | Toast đỏ "Phải có Incident Report hoặc PM Work Order nguồn" |
| `CM-002` | Toast đỏ + link đến WO đang mở của thiết bị |
| `CM-003` | Highlight dòng vật tư thiếu phiếu xuất kho màu đỏ |
| `CM-004` | Hiển thị ⚠ cạnh ô `stock_entry_ref` không hợp lệ |
| `CM-005` | Nhắc "Cần tạo Firmware Change Request trước khi hoàn thành" |
| `CM-006` | Nhắc "FCR chưa được phê duyệt" + link đến FCR |
| `CM-007` / `CM-008` | Highlight dòng checklist chưa đủ / có Fail |
| `CM-010` | Redirect về trang 403 |
| `CM-011` | Trang 404 "Phiếu sửa chữa không tồn tại" |
| `CM-012` | Toast "Không thể thực hiện hành động ở trạng thái hiện tại" |

---

## §6 TypeScript Types

```typescript
// types/imm09.ts

export type RepairStatus =
  | 'Open'
  | 'Assigned'
  | 'Diagnosing'
  | 'Pending Parts'
  | 'In Repair'
  | 'Pending Inspection'
  | 'Completed'
  | 'Cannot Repair'
  | 'Cancelled'

export interface RepairWO {
  name: string
  asset_ref: string
  asset_name: string
  asset_category: string
  risk_class: string
  serial_no: string
  incident_report: string | null
  source_pm_wo: string | null
  repair_type: string
  priority: 'Normal' | 'Urgent' | 'Emergency'
  status: RepairStatus
  open_datetime: string
  assigned_datetime: string | null
  completion_datetime: string | null
  sla_target_hours: number
  mttr_hours: number | null
  sla_breached: boolean
  is_repeat_failure: boolean
  is_warranty_claim: boolean
  assigned_to: string | null
  diagnosis_notes: string | null
  root_cause_category: string | null
  spare_parts_used: SparePartRow[]
  total_parts_cost: number
  repair_checklist: ChecklistRow[]
  firmware_updated: boolean
  firmware_change_request: string | null
  dept_head_name: string | null
  asset_info?: AssetInfo
}

export interface SparePartRow {
  idx: number
  item_code: string
  item_name: string
  qty: number
  uom: string
  unit_cost: number
  total_cost: number
  stock_entry_ref: string | null
}

export interface ChecklistRow {
  idx: number
  test_description: string
  test_category: string
  result: 'Pass' | 'Fail' | 'N/A' | null
  measured_value: string | null
  expected_value: string | null
  notes: string | null
}

export interface AssetInfo {
  asset_name: string
  asset_category: string
  lifecycle_status: string
  risk_classification: string
  manufacturer_sn: string
  department: string | null
  location: string | null
}

export interface RepairKpis {
  total_completed: number
  mttr_avg_hours: number
  sla_compliance_pct: number
  repeat_failure_count: number
  open_wos: number
}

export interface MttrReport {
  mttr_avg: number
  first_fix_rate: number
  backlog_count: number
  cost_per_repair: number
  mttr_trend: { month: string; value: number }[]
  backlog_by_dept: { dept: string; count: number }[]
}
```

---

## §7 Webhook Events (Realtime)

| Channel | Trigger | Payload | Subscriber |
|---|---|---|---|
| `cm_sla_breached` | Scheduler hourly phát hiện WO vượt SLA | `{"wo": "WO-CM-...", "asset": "AC-ASSET-..."}` | KTV được gán (`assigned_to`) |

Phát qua `frappe.publish_realtime(channel, payload, user=assigned_to)`. FE subscribe trong `stores/imm09.ts` qua socket event `cm_sla_breached`.

---

## §8 Endpoint ↔ Business Rule Mapping

| Endpoint | Business Rule áp dụng |
|---|---|
| `create_repair_work_order` | BR-09-01 (nguồn), BR-09-05 (no duplicate), BR-09-06 (SLA tính) |
| `assign_technician` | State machine: Open → Assigned |
| `submit_diagnosis` | State machine: Assigned/Diagnosing → Pending Parts/In Repair |
| `request_spare_parts` | BR-09-02 (gắn stock_entry_ref) |
| `start_repair` | State machine |
| `close_work_order` (Completed) | BR-09-02 (stock entry), BR-09-03 (FCR), BR-09-04 (checklist) — chuyển sang Pending Inspection |
| `confirm_inspection` | Nghiệm thu: role CAN_APPROVE_DEP → submit doc → complete_repair() → MTTR/SLA/ALE |
| `close_work_order` (Cannot Repair) | BR-09-05 (Asset → Out of Service) |
| `get_repair_kpis` / `get_mttr_report` | BR-09-07 (theo dõi KPI MTTR) |
| `get_asset_repair_history` | Audit trail + BR-09-06 (detect repeat failure) |

---

## §9 Smoke Test Playbook

```bash
BASE="https://acme.local/api/method/assetcore.api.imm09"
AUTH="Authorization: token KEY:SECRET"

# 1. Tạo WO
curl -s -X POST "$BASE.create_repair_work_order" \
  -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"asset_ref":"AC-ASSET-0001","repair_type":"Corrective","priority":"Urgent",
       "failure_description":"Không khởi động","incident_report":"IR-0001","source_pm_wo":""}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin)['message']; print(d['data']['name'])"

WO="WO-CM-2026-00001"

# 2. Phân công KTV
curl -s -X POST "$BASE.assign_technician" -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"name\":\"$WO\",\"technician\":\"ktv@hospital.vn\"}" | python3 -c \
  "import sys,json; print(json.load(sys.stdin)['message']['data']['status'])"

# 3. Nộp chẩn đoán
curl -s -X POST "$BASE.submit_diagnosis" -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"name\":\"$WO\",\"diagnosis_notes\":\"Hỏng cầu chì\",\"needs_parts\":0}" | python3 -c \
  "import sys,json; print(json.load(sys.stdin)['message']['data']['status'])"

# 4. Đóng WO → Pending Inspection
curl -s -X POST "$BASE.close_work_order" -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"name\":\"$WO\",\"repair_summary\":\"Đã thay cầu chì\",\"root_cause_category\":\"Electrical\",
       \"dept_head_name\":\"BS Hùng\",\"checklist_results\":\"[]\",\"cannot_repair\":0}" | python3 -c \
  "import sys,json; print(json.load(sys.stdin)['message']['data']['status'])"
# expect: Pending Inspection

# 5. Nghiệm thu → Completed
curl -s -X POST "$BASE.confirm_inspection" -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"name\":\"$WO\"}" | python3 -c \
  "import sys,json; d=json.load(sys.stdin)['message']['data']; print(d['status'], d['mttr_hours'])"
# expect: Completed <float>

# 6. Kiểm tra KPI
curl -s -G "$BASE.get_repair_kpis" -H "$AUTH" \
  --data-urlencode "year=2026" --data-urlencode "month=4" | python3 -c \
  "import sys,json; print(json.load(sys.stdin)['message']['data']['kpis'])"
```

---

## §10 Implementation Notes

### §10.1 Path map docs ↔ code (v2.0)

| Docs cũ (v1) | Code thực tế (v2.0) |
|---|---|
| `create_repair_wo` | `create_repair_work_order` |
| `submit_repair_result` | Gộp vào `close_work_order` |
| `complete_repair` | Tách 2 bước: `close_work_order(cannot_repair=0)` → Pending Inspection, rồi `confirm_inspection` → Completed |
| `mark_cannot_repair` | `close_work_order(cannot_repair=1)` |
| `get_repair_wo` | `get_repair_work_order` |
| `get_repair_list` | `list_repair_work_orders` |
| `get_repair_backlog` | Trích từ `get_mttr_report.backlog_*` |

### §10.2 Implementation status

| Hạng mục | Trạng thái |
|---|---|
| `search_spare_parts` endpoint | ✅ Đã implement — `api/imm09.py` + `services/imm09.py` + FE `@/api/imm09.searchSpareParts()` |
| `create_firmware_fcr` / `approve_firmware_fcr` | Quản lý qua Frappe Desk form — chưa có custom endpoint |
| MTTR theo working hours | Hiện tính calendar time; cần util `get_working_hours_between` khi cần chính xác hơn |

### §10.3 `ignore_permissions` & `ignore_links`

Production cần review: `doc.flags.ignore_links = True` và `save(ignore_permissions=True)` hiện dùng để tránh lỗi trong môi trường test. Bật đầy đủ permission check trước khi go-live.

---

*End of IMM-09 API Specification v1.0 — Corrective Maintenance.*
