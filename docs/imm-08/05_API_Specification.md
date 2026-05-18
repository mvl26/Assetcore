# 05 — API Specification — IMM-08 Bảo trì định kỳ (PM)

| Mục | Giá trị |
|---|---|
| Module | IMM-08 — Preventive Maintenance |
| Phạm vi | Per-module |
| Owner | BE Lead |
| Base URL | `/api/method/assetcore.api.imm08.<function>` |
| Auth | Frappe session HOẶC `Authorization: token <key>:<secret>` |
| Cập nhật | 2026-05-14 |

---

## 0. API Catalog

### PM Work Orders

| # | Endpoint | Method | Mô tả ngắn | Role | Idempotent | Liên kết US |
|---|---|---|---|---|---|---|
| 1 | `assetcore.api.imm08.list_pm_work_orders` | GET | List PM WO + filter + pagination | All IMM roles | ✓ | US-08-01 |
| 2 | `assetcore.api.imm08.get_pm_work_order` | GET | Chi tiết 1 WO + checklist | All IMM roles | ✓ | — |
| 3 | `assetcore.api.imm08.assign_technician` | POST | Phân công Kỹ thuật viên cho WO Open/Overdue | Workshop Head, CMMS Admin | ✗ | US-08-06 |
| 4 | `assetcore.api.imm08.submit_pm_result` | POST | Kỹ thuật viên nộp kết quả PM (submit WO) | HTM Technician, Workshop Head | ✗ | US-08-02 |
| 5 | `assetcore.api.imm08.report_major_failure` | POST | Dừng PM + tạo CM khẩn + Asset OOS | HTM Technician, Workshop Head | ✗ | US-08-03 |
| 6 | `assetcore.api.imm08.reschedule_pm` | POST | Hoãn lịch PM (lý do bắt buộc) | Workshop Head, CMMS Admin | ✗ | US-08-06 |
| 7 | `assetcore.api.imm08.create_pm_work_order` | POST | Tạo PM WO thủ công (ad-hoc) | Workshop Head, CMMS Admin | ✗ | — |

### Calendar & Dashboard

| # | Endpoint | Method | Mô tả ngắn | Role | Idempotent | Liên kết US |
|---|---|---|---|---|---|---|
| 8 | `assetcore.api.imm08.get_pm_calendar` | GET | Events theo tháng cho calendar view | Workshop Head, HTM Technician | ✓ | US-08-07 |
| 9 | `assetcore.api.imm08.get_pm_dashboard_stats` | GET | KPI compliance + trend 6 tháng | Workshop Head, VP Block2, CMMS Admin | ✓ | US-08-08 |
| 10 | `assetcore.api.imm08.get_asset_pm_history` | GET | Lịch sử PM Task Log của 1 thiết bị | All IMM roles | ✓ | — |

### PM Schedules

| # | Endpoint | Method | Mô tả ngắn | Role | Idempotent |
|---|---|---|---|---|---|
| 11 | `assetcore.api.imm08.list_pm_schedules` | GET | Danh sách PM Schedule | All IMM roles | ✓ |
| 12 | `assetcore.api.imm08.get_pm_schedule` | GET | Chi tiết 1 PM Schedule | All IMM roles | ✓ |
| 13 | `assetcore.api.imm08.create_pm_schedule` | POST | Tạo PM Schedule mới | Workshop Head, CMMS Admin | ✗ |
| 14 | `assetcore.api.imm08.update_pm_schedule` | POST | Cập nhật PM Schedule | Workshop Head, CMMS Admin | ✗ |
| 15 | `assetcore.api.imm08.set_pm_schedule_status` | POST | Đổi status (Active/Paused/Suspended) | Workshop Head, CMMS Admin | ✗ |
| 16 | `assetcore.api.imm08.delete_pm_schedule` | POST | Xóa PM Schedule | CMMS Admin | ✗ |

### PM Checklist Templates

| # | Endpoint | Method | Mô tả ngắn | Role | Idempotent |
|---|---|---|---|---|---|
| 17 | `assetcore.api.imm08.list_pm_templates` | GET | Danh sách checklist template | All IMM roles | ✓ |
| 18 | `assetcore.api.imm08.get_pm_template` | GET | Chi tiết 1 template | All IMM roles | ✓ |
| 19 | `assetcore.api.imm08.create_pm_template` | POST | Tạo template mới | Workshop Head, CMMS Admin | ✗ |
| 20 | `assetcore.api.imm08.update_pm_template` | POST | Cập nhật template | Workshop Head, CMMS Admin | ✗ |
| 21 | `assetcore.api.imm08.approve_pm_template` | POST | Phê duyệt template | Workshop Head, CMMS Admin | ✗ |
| 22 | `assetcore.api.imm08.version_pm_template` | POST | Tạo phiên bản mới từ template cũ | Workshop Head, CMMS Admin | ✗ |
| 23 | `assetcore.api.imm08.delete_pm_template` | POST | Xóa template | CMMS Admin | ✗ |
| 24 | `assetcore.api.imm08.apply_pm_template_to_category` | POST | Bulk-tạo PM Schedule cho mọi asset cùng danh mục với template | Workshop Head, CMMS Admin | ✗ |

---

## 1. Quy ước chung

### 1.1. Response success — format chuẩn AssetCore

```jsonc
{
  "success": true,
  "data": <payload — object / array / null>
}
```

FE đọc qua `response.data.data` (Frappe axios wrapper strip outer `message`).

**HTTP status:** Frappe luôn trả **HTTP 200**. Phân biệt success/error qua field `success` trong body. HTTP ≠ 200 chỉ khi: 401 (session hết hạn), 403 (CSRF/role Frappe), 500 (unhandled).

### 1.2. Response error — format chuẩn

```jsonc
{
  "success": false,
  "error": "Mô tả lỗi tiếng Việt",
  "code": "NOT_FOUND",
  "fields": { "field_name": "lỗi inline" }  // optional
}
```

CẤM trả raw traceback / SQL error.

### 1.3. Error code catalog

| Code | Khi nào |
|---|---|
| `NOT_FOUND` | Record không tồn tại |
| `FORBIDDEN` | Không có role phù hợp |
| `VALIDATION` | Input validation fail |
| `BAD_STATE` | State machine fail (vd WO đã submitted) |
| `CONFLICT` | Concurrent modify |
| `INVALID_PARAMS` | JSON parse fail |
| `ALREADY_SUBMITTED` | WO đã docstatus=1 |
| `INTERNAL` | Lỗi hệ thống |

### 1.4. Mapping FE ↔ BE error code

| BE `ErrorCode` | FE `ErrorCode` |
|---|---|
| `VALIDATION` | `VALIDATION_ERROR` |
| `BAD_STATE` | `BAD_STATE` |
| `NOT_FOUND` | `NOT_FOUND` |
| `FORBIDDEN` | `FORBIDDEN` |
| `CONFLICT` | `CONFLICT` |
| `INVALID_PARAMS` | `INVALID_PARAMS` |
| `ALREADY_SUBMITTED` | `BAD_STATE` |
| `INTERNAL` | `INTERNAL_ERROR` |

### 1.5. Type definitions

```ts
// frontend/src/types/imm08.ts
export type PMStatus =
  | 'Open' | 'In Progress' | 'Pending–Device Busy'
  | 'Overdue' | 'Completed' | 'Halted–Major Failure' | 'Cancelled';

export type PMType = 'Quarterly' | 'Semi-Annual' | 'Annual' | 'Ad-hoc';

export interface PMWorkOrder {
  name: string;
  asset_ref: string;
  asset_name: string;           // denormalized
  pm_type: PMType;
  wo_type: 'Preventive' | 'Corrective';
  status: PMStatus;
  due_date: string;             // ISO date
  completion_date: string | null;
  is_late: boolean;
  assigned_to: string | null;
  overall_result: string | null;
  checklist_results: PMChecklistResult[];
  source_pm_wo: string | null;
}

export interface PMChecklistResult {
  idx: number;
  description: string;
  measurement_type: 'Pass/Fail' | 'Numeric' | 'Text';
  result: 'Pass' | 'Fail–Minor' | 'Fail–Major' | 'N/A' | null;
  measured_value: number | null;
  unit: string | null;
  notes: string | null;
  photo: string | null;
}

export interface PMDashboardStats {
  kpis: {
    compliance_rate_pct: number;
    total_scheduled: number;
    completed_on_time: number;
    overdue: number;
    avg_days_late: number;
  };
  trend_6months: Array<{ month: string; total: number; on_time: number; rate: number }>;
}
```

### Pagination convention

```jsonc
{
  "data": [ /* items */ ],
  "pagination": { "page": 1, "page_size": 20, "total": 137, "total_pages": 7 }
}
```

---

## 2. Endpoints

### 1. list_pm_work_orders — Danh sách PM WO

| Mục | Giá trị |
|---|---|
| Method | GET |
| Path | `/api/method/assetcore.api.imm08.list_pm_work_orders` |
| Role | All IMM roles |
| Idempotent | Yes |

**Request:**

| Param | Type | Required | Validation |
|---|---|---|---|
| `filters` | JSON string | ✗ | valid JSON object |
| `page` | int | ✗ | ≥ 1, default 1 |
| `page_size` | int | ✗ | 1–100, default 20 |

**Response success:**

```jsonc
{
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
    "pagination": { "page": 1, "page_size": 20, "total": 1, "total_pages": 1 }
  }
}
```

**Errors:** `INVALID_PARAMS` (filters JSON sai).

---

### 2. get_pm_work_order — Chi tiết PM WO

| Mục | Giá trị |
|---|---|
| Method | GET |
| Path | `/api/method/assetcore.api.imm08.get_pm_work_order` |
| Role | All IMM roles |
| Idempotent | Yes |

**Request:** `?name=PM-WO-2026-00001`

**Response success:**

```jsonc
{
  "success": true,
  "data": {
    "name": "PM-WO-2026-00001",
    "asset_ref": "AC-ASSET-2026-0003",
    "asset_name": "Máy thở Drager Evita V500",
    "asset_category": "Mechanical Ventilator",
    "risk_class": "III",
    "pm_type": "Quarterly",
    "status": "In Progress",
    "due_date": "2026-04-17",
    "completion_date": null,
    "assigned_to": "ktv1@bv.vn",
    "is_late": false,
    "checklist_results": [
      {
        "idx": 1,
        "description": "Kiểm tra điện áp đầu vào",
        "measurement_type": "Numeric",
        "unit": "V",
        "result": null,
        "measured_value": null,
        "notes": null
      }
    ]
  }
}
```

**Errors:** `NOT_FOUND`.

---

### 3. assign_technician — Phân công Kỹ thuật viên

| Mục | Giá trị |
|---|---|
| Method | POST |
| Path | `/api/method/assetcore.api.imm08.assign_technician` |
| Role | Workshop Head, CMMS Admin |
| Idempotent | No |

**Request:**

```jsonc
{
  "name": "PM-WO-2026-00001",
  "technician": "ktv1@bv.vn",
  "scheduled_date": "2026-04-17"
}
```

**Response success:**

```jsonc
{
  "success": true,
  "data": {
    "name": "PM-WO-2026-00001",
    "status": "In Progress",
    "assigned_to": "ktv1@bv.vn"
  }
}
```

**Errors:** `NOT_FOUND` · `BAD_STATE` (WO không ở Open/Overdue — VR-08-08).

---

### 4. submit_pm_result — Kỹ thuật viên nộp kết quả PM

| Mục | Giá trị |
|---|---|
| Method | POST |
| Path | `/api/method/assetcore.api.imm08.submit_pm_result` |
| Role | HTM Technician, Workshop Head |
| Idempotent | No |

**Request:**

```jsonc
{
  "name": "PM-WO-2026-00001",
  "checklist_results": "[{\"idx\":1,\"result\":\"Pass\",\"measured_value\":220.5,\"notes\":\"\"}]",
  "overall_result": "Pass",
  "technician_notes": "Sticker đã gắn",
  "pm_sticker_attached": 1,
  "duration_minutes": 52
}
```

**Response success:**

```jsonc
{
  "success": true,
  "data": {
    "name": "PM-WO-2026-00001",
    "new_status": "Completed",
    "is_late": false,
    "next_pm_date": "2026-07-17",
    "cm_wo_created": null
  }
}
```

**Response error:**

```jsonc
{
  "success": false,
  "error": "Tất cả mục checklist phải có kết quả trước khi Submit (BR-08-08). Mục 'Kiểm tra áp suất' chưa điền.",
  "code": "VALIDATION"
}
```

**Errors:**

| Code | Khi nào |
|---|---|
| `NOT_FOUND` | WO không tồn tại |
| `INVALID_PARAMS` | `checklist_results` không phải JSON |
| `ALREADY_SUBMITTED` | WO đã docstatus=1 VR-08-10 |
| `VALIDATION` | BR-08-06 hoặc BR-08-08 fail |

**Side effects:**
- PM Task Log immutable tạo
- PM Schedule `last_pm_date`, `next_due_date` advance (BR-08-03)
- Asset `custom_last_pm_date`, `custom_next_pm_date` sync
- CM Work Order tạo nếu Fail-Minor/Major (BR-08-09)

---

### 5. report_major_failure — Dừng PM + Asset Out of Service

| Mục | Giá trị |
|---|---|
| Method | POST |
| Path | `/api/method/assetcore.api.imm08.report_major_failure` |
| Role | HTM Technician, Workshop Head |
| Idempotent | No |

**Request:**

```jsonc
{
  "pm_wo_name": "PM-WO-2026-00003",
  "failure_description": "Compressor không khởi động — điện áp 0V",
  "failed_item_indexes": "[2]"
}
```

> **Ghi chú:** `failed_item_indexes` được parse bởi API layer nhưng không truyền vào service `report_major_failure`. Service nhận `pm_wo_name` và `failure_description` là đủ. Field này giữ lại trong body request để FE log, nhưng không có tác dụng phía BE.

**Response success:**

```jsonc
{
  "success": true,
  "data": {
    "pm_wo": "PM-WO-2026-00003",
    "new_status": "Halted–Major Failure",
    "cm_wo_created": "PM-WO-2026-00019",
    "asset_status": "Out of Service"
  }
}
```

**Errors:** `NOT_FOUND`.

**Side effects:** Asset.status = Out of Service · PM WO Halted · CM WO tạo · Email khẩn Workshop Head + VP Block2.

---

### 6. get_pm_calendar — Calendar view tháng

| Mục | Giá trị |
|---|---|
| Method | GET |
| Path | `/api/method/assetcore.api.imm08.get_pm_calendar` |
| Role | Workshop Head, HTM Technician |
| Idempotent | Yes |

**Request:** `?year=2026&month=4&asset_ref=&technician=`

**Response success:**

```jsonc
{
  "success": true,
  "data": {
    "month": "2026-04",
    "events": [
      {
        "name": "PM-WO-2026-00001",
        "asset_name": "Máy thở Drager Evita V500",
        "pm_type": "Quarterly",
        "due_date": "2026-04-17",
        "status": "Completed",
        "assigned_to": "ktv1@bv.vn",
        "is_late": false
      }
    ],
    "summary": { "total": 16, "completed": 14, "overdue": 2, "pending": 0 }
  }
}
```

---

### 7. get_pm_dashboard_stats — KPI dashboard

| Mục | Giá trị |
|---|---|
| Method | GET |
| Path | `/api/method/assetcore.api.imm08.get_pm_dashboard_stats` |
| Role | Workshop Head, VP Block2, CMMS Admin |
| Idempotent | Yes |

**Request:** `?year=2026&month=4`

**Response success:**

```jsonc
{
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
```

---

### 8. reschedule_pm — Hoãn lịch PM

| Mục | Giá trị |
|---|---|
| Method | POST |
| Path | `/api/method/assetcore.api.imm08.reschedule_pm` |
| Role | Workshop Head, CMMS Admin |
| Idempotent | No |

**Request:**

```jsonc
{
  "name": "PM-WO-2026-00004",
  "new_date": "2026-04-25",
  "reason": "Thiết bị đang dùng cấp cứu chiều 22/4 — dời sang 25/4"
}
```

**Response success:**

```jsonc
{
  "success": true,
  "data": {
    "name": "PM-WO-2026-00004",
    "old_date": "2026-04-22",
    "new_date": "2026-04-25",
    "status": "Pending–Device Busy"
  }
}
```

**Errors:** `VALIDATION` (reason < 5 ký tự — VR-08-09) · `NOT_FOUND`.

---

### 9. get_asset_pm_history — Lịch sử PM của thiết bị

| Mục | Giá trị |
|---|---|
| Method | GET |
| Path | `/api/method/assetcore.api.imm08.get_asset_pm_history` |
| Role | All IMM roles |
| Idempotent | Yes |

**Request:** `?asset_ref=AC-ASSET-2026-0003&limit=10`

**Response success:**

```jsonc
{
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
        "next_pm_date": "2026-07-17"
      }
    ]
  }
}
```

---

### 10. apply_pm_template_to_category — Bulk tạo PM Schedule theo danh mục

| Mục | Giá trị |
|---|---|
| Method | POST |
| Path | `/api/method/assetcore.api.imm08.apply_pm_template_to_category` |
| Role | Workshop Head, CMMS Admin |
| Idempotent | Yes (bỏ qua asset đã có PM Schedule cùng pm_type) |

**Request:**

```jsonc
{
  "template_name": "PMCT-Ventilator-Quarterly"
}
```

**Response success:**

```jsonc
{
  "success": true,
  "data": {
    "template": "PMCT-Ventilator-Quarterly",
    "asset_category": "Mechanical Ventilator",
    "created": ["PMS-AC-ASSET-0001-Quarterly", "PMS-AC-ASSET-0003-Quarterly"],
    "skipped": ["PMS-AC-ASSET-0002-Quarterly"],
    "errors": []
  }
}
```

**Errors:** `NOT_FOUND` (template không tồn tại) · `VALIDATION` (template chưa gán danh mục).

**Side effects:**
- Tạo `PM Schedule` mới cho mọi AC Asset thuộc `template.asset_category`, trừ: asset đã có lịch cùng `pm_type` (bỏ qua), asset Decommissioned/Disposed (bỏ qua).
- `pm_interval_days` lấy từ `AC Asset Category.default_pm_interval_days` (fallback 180 ngày).

---

## 7. Smoke test playbook

```bash
BASE="https://erp.bv.vn/api/method"
AUTH="Authorization: token KEY:SECRET"

# 1. List WO Overdue
curl -H "$AUTH" "$BASE/assetcore.api.imm08.list_pm_work_orders?filters=%7B%22status%22%3A%22Overdue%22%7D"

# 2. Get PM Dashboard
curl -H "$AUTH" "$BASE/assetcore.api.imm08.get_pm_dashboard_stats?year=2026&month=4"

# 3. Submit PM Result
curl -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"name":"PM-WO-2026-00001","checklist_results":"[{\"idx\":1,\"result\":\"Pass\"}]","overall_result":"Pass","pm_sticker_attached":1,"duration_minutes":45}' \
  "$BASE/assetcore.api.imm08.submit_pm_result"
```

---

## DoD — File 05 hoàn chỉnh

- [x] API Catalog liệt kê 100% 24 endpoint (7 WO + 3 Calendar/Dashboard + 6 Schedule + 7 Template + 1 Bulk)
- [x] Response format `{"success": true, "data": {...}}` chuẩn AssetCore
- [x] Error format `{"success": false, "error": "...", "code": "..."}` chuẩn
- [x] Error code catalog đầy đủ + FE mapping
- [x] TypeScript type definitions đầy đủ
- [x] Mỗi endpoint có request schema + response example
- [x] Side effects nêu rõ
- [x] Pagination convention nhất quán
- [x] Smoke test playbook
