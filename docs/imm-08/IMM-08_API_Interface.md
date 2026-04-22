# IMM-08 — API Interface Specification

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-08 — Preventive Maintenance |
| Phiên bản | 2.0.0 |
| Ngày cập nhật | 2026-04-18 |
| Trạng thái | LIVE |
| Base URL | `/api/method/assetcore.api.imm08` |
| Tác giả | AssetCore Team |

---

## 1. Authentication

Mọi endpoint yêu cầu Frappe session hoặc API token.

```http
# API Token (server-to-server)
Authorization: token <api_key>:<api_secret>

# Session cookie (browser SPA)
Cookie: sid=<session_id>
X-Frappe-CSRF-Token: <csrf_token>
```

| Lỗi | HTTP | Khi nào |
|---|---|---|
| 401 | Unauthorized | Thiếu/sai credential |
| 403 | Forbidden | Thiếu role (Workshop Head, HTM Technician, CMMS Admin, VP Block2, Biomed Engineer) |

---

## 2. Response Format

Frappe wrap mọi response trong `message`. Helper chuẩn hoá tại `assetcore/utils/helpers.py`:

```python
def _ok(data): return {"success": True, "data": data}
def _err(msg, code="ERROR"): return {"success": False, "error": msg, "code": code}
```

**Success:**

```json
{ "message": { "success": true, "data": { ... } } }
```

**Error (HTTP 200, success=false):**

```json
{ "message": { "success": false, "error": "Mô tả lỗi", "code": "NOT_FOUND" } }
```

> **Lưu ý:** Frappe luôn trả HTTP 200 cho whitelisted method ngay cả khi business error. Client kiểm tra `message.success`.

---

## 3. Endpoints

Tổng cộng **9 endpoint**, đều public qua `@frappe.whitelist()` trong `assetcore/api/imm08.py`.

| # | Function | Method | Mô tả | Permission |
|---|---|---|---|---|
| 1 | `list_pm_work_orders` | GET | Danh sách PM WO + pagination | All IMM roles |
| 2 | `get_pm_work_order` | GET | Chi tiết 1 WO + checklist | All IMM roles |
| 3 | `assign_technician` | POST | Phân công KTV cho WO Open/Overdue | Workshop Head, CMMS Admin |
| 4 | `submit_pm_result` | POST | KTV nộp kết quả PM (submit WO) | HTM Technician, Workshop Head |
| 5 | `report_major_failure` | POST | Dừng PM + tạo CM khẩn + Asset Out of Service | HTM Technician, Workshop Head |
| 6 | `get_pm_calendar` | GET | Events theo tháng cho calendar view | Workshop Head, HTM Technician |
| 7 | `get_pm_dashboard_stats` | GET | KPI compliance + trend 6 tháng | Workshop Head, VP Block2, CMMS Admin |
| 8 | `reschedule_pm` | POST | Hoãn lịch PM (lý do bắt buộc) | Workshop Head, CMMS Admin |
| 9 | `get_asset_pm_history` | GET | Lịch sử PM Task Log của 1 thiết bị | All IMM roles |

---

### 3.1 `list_pm_work_orders` — Danh sách PM Work Order

| Thuộc tính | Giá trị |
|---|---|
| Method | GET |
| Path | `assetcore.api.imm08.list_pm_work_orders` |

**Request params:**

| Param | Kiểu | Default | Ghi chú |
|---|---|---|---|
| `filters` | JSON string | `"{}"` | Frappe filter dict, vd `{"status":"Overdue"}` |
| `page` | int | 1 | 1-based |
| `page_size` | int | 20 | — |

**Response 200:**

```json
{
  "message": {
    "success": true,
    "data": {
      "data": [
        {
          "name": "PM-WO-2026-00001",
          "asset_ref": "AC-ASSET-2026-0003",
          "asset_name": "Máy thở Drager Evita V500",
          "pm_type": "Quarterly",
          "wo_type": "Preventive",
          "status": "Open",
          "due_date": "2026-04-17",
          "completion_date": null,
          "assigned_to": "ktv1@bv.vn",
          "overall_result": null,
          "is_late": false,
          "source_pm_wo": null
        }
      ],
      "pagination": {
        "page": 1, "page_size": 20, "total": 1, "total_pages": 1
      }
    }
  }
}
```

**Errors:** `INVALID_PARAMS` (filters JSON sai).

---

### 3.2 `get_pm_work_order` — Chi tiết PM WO

| Method | Path |
|---|---|
| GET | `assetcore.api.imm08.get_pm_work_order` |

**Request:** `?name=PM-WO-2026-00001`

**Response 200 (rút gọn):**

```json
{
  "message": {
    "success": true,
    "data": {
      "name": "PM-WO-2026-00001",
      "asset_ref": "AC-ASSET-2026-0003",
      "asset_name": "Máy thở Drager Evita V500",
      "asset_category": "Mechanical Ventilator",
      "risk_class": "III",
      "pm_type": "Quarterly",
      "wo_type": "Preventive",
      "status": "In Progress",
      "due_date": "2026-04-17",
      "scheduled_date": "2026-04-17",
      "completion_date": null,
      "assigned_to": "ktv1@bv.vn",
      "overall_result": null,
      "technician_notes": null,
      "pm_sticker_attached": false,
      "is_late": false,
      "duration_minutes": null,
      "source_pm_wo": null,
      "checklist_results": [
        {
          "idx": 1,
          "checklist_item_idx": 1,
          "description": "Kiểm tra điện áp đầu vào",
          "measurement_type": "Numeric",
          "unit": "V",
          "result": null,
          "measured_value": null,
          "notes": null,
          "photo": null
        }
      ]
    }
  }
}
```

**Errors:** `NOT_FOUND`.

---

### 3.3 `assign_technician` — Phân công KTV

| Method | Path |
|---|---|
| POST | `assetcore.api.imm08.assign_technician` |

**Body:**

```json
{
  "name": "PM-WO-2026-00001",
  "technician": "ktv1@bv.vn",
  "scheduled_date": "2026-04-17"
}
```

**Side-effects:** `assigned_to`, `assigned_by = session.user`, `scheduled_date`, `status = In Progress`.

**Response 200:**

```json
{ "message": { "success": true,
  "data": { "name": "PM-WO-2026-00001", "status": "In Progress", "assigned_to": "ktv1@bv.vn" } } }
```

**Errors:** `NOT_FOUND` · `INVALID_STATE` (WO không ở Open/Overdue) — VR-08-08.

---

### 3.4 `submit_pm_result` — KTV nộp kết quả PM

| Method | Path |
|---|---|
| POST | `assetcore.api.imm08.submit_pm_result` |

**Body:**

```json
{
  "name": "PM-WO-2026-00001",
  "checklist_results": [
    { "idx": 1, "result": "Pass", "measured_value": 220.5, "notes": "" },
    { "idx": 2, "result": "Fail–Minor", "measured_value": null, "notes": "Rò rỉ van 2" }
  ],
  "overall_result": "Pass with Minor Issues",
  "technician_notes": "Sticker đã gắn",
  "pm_sticker_attached": 1,
  "duration_minutes": 52
}
```

**Logic:**

1. Cập nhật `checklist_results` row theo `idx`.
2. Set `status = Completed`, `completion_date = today()`, `is_late` (BR-08-05).
3. `wo.submit()` → trigger `on_submit` controller:
   - Advance PM Schedule (BR-08-03).
   - Sync Asset `custom_*_pm_date` fields.
   - Tạo PM Task Log (immutable, BR-08-10).
   - Auto-create CM WO nếu Fail-Minor/Major (BR-08-09).

**Response 200:**

```json
{
  "message": {
    "success": true,
    "data": {
      "name": "PM-WO-2026-00001",
      "new_status": "Completed",
      "is_late": false,
      "next_pm_date": "2026-07-17",
      "cm_wo_created": "PM-WO-2026-00018"
    }
  }
}
```

**Errors:**

| Code | Khi nào |
|---|---|
| `NOT_FOUND` | WO không tồn tại |
| `INVALID_PARAMS` | `checklist_results` không phải JSON |
| `ALREADY_SUBMITTED` | WO đã `docstatus=1` (VR-08-10) |
| `SUBMIT_ERROR` | Validate fail (BR-08-06, BR-08-08) — message tiếng Việt |

---

### 3.5 `report_major_failure` — Dừng PM + Asset Out of Service

| Method | Path |
|---|---|
| POST | `assetcore.api.imm08.report_major_failure` |

**Body:**

```json
{
  "pm_wo_name": "PM-WO-2026-00003",
  "failure_description": "Compressor không khởi động — điện áp 0V",
  "failed_item_indexes": "[2]"
}
```

**Side-effects:**

- `Asset.status = "Out of Service"` (BR-08-04).
- PM WO `status = "Halted–Major Failure"`.
- Tạo CM WO (`wo_type=Corrective`, `source_pm_wo`, `due_date=today`, `technician_notes` chứa `[MAJOR FAILURE]` prefix).
- Email khẩn tới Workshop Head + VP Block2.

**Response 200:**

```json
{
  "message": {
    "success": true,
    "data": {
      "pm_wo": "PM-WO-2026-00003",
      "new_status": "Halted–Major Failure",
      "cm_wo_created": "PM-WO-2026-00019",
      "asset_status": "Out of Service"
    }
  }
}
```

**Errors:** `NOT_FOUND`.

---

### 3.6 `get_pm_calendar` — Calendar view tháng

| Method | Path |
|---|---|
| GET | `assetcore.api.imm08.get_pm_calendar` |

**Request params:**

| Param | Kiểu | Bắt buộc | Ghi chú |
|---|---|---|---|
| `year` | int | ✅ | 4 chữ số |
| `month` | int | ✅ | 1–12 |
| `asset_ref` | string | — | Filter theo Asset |
| `technician` | string | — | Filter theo `assigned_to` |

**Response 200:**

```json
{
  "message": {
    "success": true,
    "data": {
      "month": "2026-04",
      "events": [
        { "name": "PM-WO-2026-00001", "asset_ref": "AC-ASSET-2026-0003",
          "asset_name": "Máy thở Drager Evita V500",
          "pm_type": "Quarterly", "due_date": "2026-04-17",
          "status": "Completed", "assigned_to": "ktv1@bv.vn", "is_late": false }
      ],
      "summary": { "total": 16, "completed": 14, "overdue": 2, "pending": 0 }
    }
  }
}
```

---

### 3.7 `get_pm_dashboard_stats` — KPI dashboard

| Method | Path |
|---|---|
| GET | `assetcore.api.imm08.get_pm_dashboard_stats` |

**Request:** `?year=2026&month=4` (optional — mặc định month/year hiện tại).

**Response 200:**

```json
{
  "message": {
    "success": true,
    "data": {
      "kpis": {
        "compliance_rate_pct": 87.5,
        "total_scheduled": 16,
        "completed_on_time": 14,
        "overdue": 2,
        "avg_days_late": 3.5
      },
      "trend_6months": [
        { "month": "2025-11", "total": 14, "on_time": 12, "rate": 85.7 },
        { "month": "2026-04", "total": 16, "on_time": 14, "rate": 87.5 }
      ]
    }
  }
}
```

---

### 3.8 `reschedule_pm` — Hoãn lịch PM

| Method | Path |
|---|---|
| POST | `assetcore.api.imm08.reschedule_pm` |

**Body:**

```json
{
  "name": "PM-WO-2026-00004",
  "new_date": "2026-04-25",
  "reason": "Thiết bị đang dùng cấp cứu chiều 22/4 — dời sang 25/4"
}
```

**Side-effects:**

- `due_date = new_date`.
- `status = "Pending–Device Busy"`.
- Append `technician_notes`: `[Hoãn lịch {old_date} → {new_date}]: {reason}`.

**Response 200:**

```json
{
  "message": {
    "success": true,
    "data": {
      "name": "PM-WO-2026-00004",
      "old_date": "2026-04-22",
      "new_date": "2026-04-25",
      "status": "Pending–Device Busy"
    }
  }
}
```

**Errors:** `MISSING_REASON` (lý do < 5 ký tự — VR-08-09) · `NOT_FOUND`.

---

### 3.9 `get_asset_pm_history` — Lịch sử PM của thiết bị

| Method | Path |
|---|---|
| GET | `assetcore.api.imm08.get_asset_pm_history` |

**Request:** `?asset_ref=AC-ASSET-2026-0003&limit=10`

**Response 200:**

```json
{
  "message": {
    "success": true,
    "data": {
      "asset_ref": "AC-ASSET-2026-0003",
      "history": [
        {
          "name": "PMTL-2026-04-00012",
          "pm_work_order": "PM-WO-2026-00001",
          "pm_type": "Quarterly",
          "completion_date": "2026-04-17",
          "technician": "ktv1@bv.vn",
          "overall_result": "Pass with Minor Issues",
          "is_late": false,
          "days_late": 0,
          "next_pm_date": "2026-07-17",
          "summary": "Sticker đã gắn"
        }
      ]
    }
  }
}
```

---

## 4. Error Codes

| Code | HTTP | Mô tả | Endpoint |
|---|---|---|---|
| `NOT_FOUND` | 200 | Record không tồn tại | 1, 2, 3, 4, 5, 8, 9 |
| `INVALID_PARAMS` | 200 | JSON sai hoặc kiểu sai | 1, 4 |
| `INVALID_STATE` | 200 | Action không hợp lệ ở state hiện tại (vd assign khi Completed) | 3 |
| `ALREADY_SUBMITTED` | 200 | WO đã docstatus=1 | 4 |
| `SUBMIT_ERROR` | 200 | Validation thất bại trong `wo.submit()` (BR-08-06, BR-08-08) | 4 |
| `MISSING_REASON` | 200 | Reason rỗng hoặc < 5 ký tự (VR-08-09) | 8 |
| `FORBIDDEN` | 200 | Thiếu role | tất cả |

---

## 5. Webhook / Realtime Events

IMM-08 sử dụng email + (kế hoạch) `frappe.publish_realtime`:

| Event | Trigger | Recipients | Channel |
|---|---|---|---|
| Daily WO summary | `tasks.generate_pm_work_orders` cuối job | Workshop Head | Email |
| PM WO Overdue alert | `tasks.check_pm_overdue` (≤7d) | Workshop Head | Email |
| PM Overdue escalation | `tasks.check_pm_overdue` (8–30d) | VP Block2 | Email |
| PM Overdue critical | `tasks.check_pm_overdue` (>30d) | BGĐ | Email |
| Major Failure khẩn | `report_major_failure` | Workshop Head + VP Block2 | Email (HTML có link) |
| (Planned) `pm_overdue_alert` | check_pm_overdue | UI subscribers | `frappe.publish_realtime` |
| (Planned) `pm_major_failure` | report_major_failure | UI subscribers | `frappe.publish_realtime` |

---

## 6. Implementation Notes

### 6.1 Source

| Layer | File |
|---|---|
| API endpoints | `assetcore/api/imm08.py` |
| Controller | `assetcore/assetcore/doctype/pm_work_order/pm_work_order.py` |
| Schedulers | `assetcore/tasks.py` (`generate_pm_work_orders`, `check_pm_overdue`) |
| Hook IMM-04 → IMM-08 | `assetcore/services/imm04.py` (on_submit `Asset Commissioning`) |
| Helpers | `assetcore/utils/helpers.py` (`_ok`, `_err`, `_get_role_emails`, `_safe_sendmail`) |

### 6.2 Conventions

- Mọi endpoint dùng `@frappe.whitelist()` (cho phép cả GET và POST — Frappe không phân biệt verb).
- Mọi response qua `_ok(data)` / `_err(msg, code)`.
- Mọi user-facing message tiếng Việt qua `frappe.throw(_(...))`.
- Naming series: `PM-WO-.YYYY.-.#####`, `PMS-{asset_ref}-{pm_type}`, `PMCT-{asset_category}-{pm_type}`.

### 6.3 Roles dùng trong API guard

```python
_ROLE_WORKSHOP = "Workshop Head"
_ROLE_KTV = "HTM Technician"
_ROLE_PTP = "VP Block2"
_ROLE_ADMIN = "CMMS Admin"
```

### 6.4 cURL ví dụ

```bash
# Liệt kê WO Overdue
curl -H "Authorization: token KEY:SECRET" \
  "https://erp.bv.vn/api/method/assetcore.api.imm08.list_pm_work_orders?filters=%7B%22status%22%3A%22Overdue%22%7D&page=1&page_size=20"

# Submit kết quả PM
curl -X POST -H "Authorization: token KEY:SECRET" -H "Content-Type: application/json" \
  -d '{"name":"PM-WO-2026-00001","checklist_results":"[{\"idx\":1,\"result\":\"Pass\"}]","overall_result":"Pass","pm_sticker_attached":1,"duration_minutes":45}' \
  "https://erp.bv.vn/api/method/assetcore.api.imm08.submit_pm_result"
```

---

*End of API Interface v2.0.0 — IMM-08 Preventive Maintenance*
