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

| Code | Khi nào | message_code (xem §11) |
|---|---|---|
| `NOT_FOUND` | Record không tồn tại | `IMM08-WO-NOT-FOUND` / `IMM08-SCHEDULE-NOT-FOUND` / `IMM08-TEMPLATE-NOT-FOUND` |
| `FORBIDDEN` | Không có role phù hợp | `AUTH-403` |
| `VALIDATION` | Input validation fail | `IMM08-CHECKLIST-INCOMPLETE` / `IMM08-DURATION-REQUIRED` / `IMM08-STICKER-REQUIRED` / `IMM08-PHOTO-REQUIRED` / `IMM08-SOURCE-PM-REQUIRED` |
| `BAD_STATE` | State machine fail (vd WO đã submitted) | `IMM08-BAD-STATE` |
| `CONFLICT` | Concurrent modify / đã submit | `IMM08-ALREADY-SUBMITTED` |
| `INVALID_PARAMS` | JSON parse fail | `VAL-INVALID-PARAMS` |
| `INTERNAL` | Lỗi hệ thống | `SYS-500` |

> Từ Sprint Notification vòng 3, error envelope IMM-08 hydrate thêm `message_code`,
> `severity`, `title`, `action_hint` qua `api_handler.handle()`. Xem **§11**.

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

**Virtual filter keys (drill-down từ KPI — `_normalize_filters`):**

| Key | Ngữ nghĩa BE | Predicate sinh ra |
|---|---|---|
| `due_before` | **PM đến hạn (due-soon window)** — drill từ KPI `pm_due_7d` (BR-08-12) | `due_date BETWEEN [today, due_before]` (cận dưới = today, inclusive 2 biên) AND `status NOT IN [Completed, Cancelled]` → gọi SoT `due_soon_filter(due_before)`. **KHÔNG** còn dịch `due_date <= due_before` (cũ thiếu cận dưới → WO quá hạn leak vào danh sách). |
| `overdue=1` | **PM quá hạn** — drill từ KPI `pm_overdue` (BR-08-11) | `status == Overdue`. Disjoint với `due_before` (overdue có `due_date < today`; due-soon có `due_date >= today`). |

> **INVARIANT (BR-08-12):** `count(KPI pm_due_7d) == pagination.total` khi drill `?filters={"due_before":"<today+7>"}` — card == drill byte-for-byte. KPI `pm_due_next7` (`dashboard.py`) và filter này dùng CHUNG `due_soon_filter` (1 SoT). FE forward `due_before` verbatim — BE lo cận dưới, FE KHÔNG inline-compute membership. Zero contract change ngoài label chip (xem 06_Frontend_Design §3.3).

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

## 11. Notification Contract (Sprint Notification 2026-05-29 vòng 3) — SINGLE SOURCE OF TRUTH

Mọi tương tác IMM-08 trả về **envelope chuẩn** đã chuẩn hoá BE → FE. FE KHÔNG
hardcode câu chữ — chỉ đọc `message_code` rồi render qua `useNotify`. Contract đã
chốt vòng 1 (pilot IMM-09), vòng 2 (IMM-12) — vòng 3 áp dụng cho IMM-08.

### 11.1 Envelope shape

Success (`_ok`):
```json
{ "success": true, "data": { ... } }
```
Lỗi (`_err`, hydrate từ registry qua `api_handler.handle()`):
```json
{
  "success": false,
  "error": "Tất cả mục checklist phải có kết quả trước khi hoàn thành PM.",
  "code": "VALIDATION",
  "message_code": "IMM08-CHECKLIST-INCOMPLETE",
  "severity": "warning",
  "title": "Checklist chưa hoàn tất",
  "action_hint": "Điền kết quả cho mọi mục checklist rồi thử lại.",
  "context": { "item": "Kiểm tra nguồn điện" },
  "http_status": 422
}
```

**Bất biến (contract):** mọi error envelope IMM-08 PHẢI có `message_code`, `severity`,
`title`. Không còn `frappe.throw(_("..."))` leak message Frappe ra FE. Service raise
qua `nthrow(MSG.IMM08_*)`; DocType `validate` hook (BR-08-06/08/09/10/02) raise qua
`nthrow_in_hook(MSG.IMM08_*)`.

### 11.2 Danh mục MSG cần bổ sung vào `utils/messages.py`

11 mã mới + tái dùng mã hệ thống (`AUTH_FORBIDDEN`, `VAL_INVALID_PARAMS`, `SYS_500`
— đã có). Severity tuân quy tắc §11.5.

| MSG.* | code (kebab) | severity | http | title | template (VI) | action_hint |
|---|---|---|---|---|---|---|
| `IMM08_WO_NOT_FOUND` | `IMM08-WO-NOT-FOUND` | warning | 404 | Không tìm thấy lệnh PM | Không tìm thấy lệnh bảo trì định kỳ: {name}. | Kiểm tra lại mã lệnh PM trong danh sách. |
| `IMM08_SCHEDULE_NOT_FOUND` | `IMM08-SCHEDULE-NOT-FOUND` | warning | 404 | Không tìm thấy lịch PM | Không tìm thấy lịch bảo trì định kỳ: {name}. | Kiểm tra lại mã lịch PM trong danh sách. |
| `IMM08_TEMPLATE_NOT_FOUND` | `IMM08-TEMPLATE-NOT-FOUND` | warning | 404 | Không tìm thấy mẫu checklist | Không tìm thấy mẫu checklist PM: {name}. | Kiểm tra lại mã mẫu trong danh sách. |
| `IMM08_BAD_STATE` | `IMM08-BAD-STATE` | warning | 409 | Sai trạng thái lệnh PM | Không thể thực hiện hành động khi lệnh PM đang ở trạng thái '{state}'. | Chỉ thực hiện hành động hợp lệ với trạng thái hiện tại. |
| `IMM08_ALREADY_SUBMITTED` | `IMM08-ALREADY-SUBMITTED` | warning | 409 | Lệnh PM đã chốt | Lệnh bảo trì định kỳ này đã được hoàn thành và chốt. | Không cần thao tác lại — lệnh PM đã chốt. |
| `IMM08_CHECKLIST_INCOMPLETE` | `IMM08-CHECKLIST-INCOMPLETE` | warning | 422 | Checklist chưa hoàn tất | Tất cả mục checklist phải có kết quả trước khi hoàn thành PM. Mục '{item}' chưa điền. | Điền kết quả cho mọi mục checklist rồi thử lại. |
| `IMM08_DURATION_REQUIRED` | `IMM08-DURATION-REQUIRED` | warning | 422 | Thiếu thời gian thực hiện | Thời gian thực hiện (phút) phải lớn hơn 0 trước khi hoàn thành PM. | Nhập thời gian thực hiện rồi thử lại. |
| `IMM08_STICKER_REQUIRED` | `IMM08-STICKER-REQUIRED` | warning | 422 | Chưa gắn tem bảo trì | Phải xác nhận đã gắn tem bảo trì trước khi hoàn thành PM. | Gắn tem bảo trì và tích xác nhận rồi thử lại. |
| `IMM08_PHOTO_REQUIRED` | `IMM08-PHOTO-REQUIRED` | warning | 422 | Thiếu ảnh bằng chứng | Thiết bị nguy cơ cao ({risk_class}) bắt buộc đính kèm ảnh trước/sau PM. | Đính kèm ảnh bằng chứng rồi thử lại. |
| `IMM08_SOURCE_PM_REQUIRED` | `IMM08-SOURCE-PM-REQUIRED` | warning | 422 | Thiếu lệnh PM gốc | Lệnh khắc phục (CM) phải tham chiếu lệnh PM gốc. | Chọn lệnh PM gốc rồi thử lại. |
| _(success)_ `IMM08_SUBMIT_SUCCESS` | `IMM08-SUBMIT-SUCCESS` | success | 200 | Đã hoàn thành PM | Đã ghi nhận kết quả bảo trì định kỳ {name}. | — |

> Content tuân `messages.py` §quy chuẩn — Chủ thể + Hậu quả + Hành động, không từ
> kỹ thuật, không đổ lỗi user. Sau khi thêm vào `messages.py`, chạy
> `python scripts/gen_fe_messages.py` để regen `frontend/src/i18n/messages.ts`.

### 11.3 BE migration checklist (cho assetcore-be)

- `services/imm08.py` hook `validate_work_order`: 5 `frappe.throw(_(...))` (BR-08-08
  checklist, BR-08-09 duration, BR-08-10 sticker, BR-08-06 photo, BR-08-02 source PM)
  → `nthrow_in_hook(MSG.IMM08_*)` tương ứng. Đây là DocType `validate` hook → BẮT BUỘC
  dùng `nthrow_in_hook` (không phải `nthrow`).
- `services/imm08.py` service layer: các `raise ServiceError(ErrorCode.NOT_FOUND, ...)`
  cho PM WO / Schedule / Template → `nthrow(MSG.IMM08_WO_NOT_FOUND / _SCHEDULE_NOT_FOUND
  / _TEMPLATE_NOT_FOUND, name=...)`. `ErrorCode.CONFLICT` "đã Submit" →
  `nthrow(MSG.IMM08_ALREADY_SUBMITTED)`. `ErrorCode.BAD_STATE` reschedule →
  `nthrow(MSG.IMM08_BAD_STATE, state=...)`. Các wrap generic `str(e)` (VALIDATION/INTERNAL)
  GIỮ NGUYÊN — handler hydrate fallback.
- `api/imm08.py`: bỏ `_parse_json`/`_handle` cục bộ + `from utils.helpers import _err,_ok`
  → dùng `from assetcore.utils.api_handler import handle, parse_json` +
  `from assetcore.utils.response import _ok, _err`. Giữ guard rbac/vendor-scope trước `handle`.
- Audit trail (`log_lifecycle_event`, PM Task Log) KHÔNG đổi. Auto-CM-WO side-effect
  (`_create_cm_wo_from_failure`) KHÔNG đổi — message framework chỉ chuẩn hoá phản hồi user.

### 11.4 FE migration checklist (cho assetcore-fe)

- Store `stores/imm08.ts`: expose `lastApiError`; mọi action catch → set `lastApiError`
  từ error envelope (giống `stores/imm09.ts`).
- Views `pm/*` (PMWorkOrderDetailView, PMWorkOrderCreateView, PmScheduleListView,
  PmTemplateListView, …): thay `toast.error(msg)` / hardcode success →
  `notify.fromError(store.lastApiError)` trong catch; success →
  `notify.show(MSG.IMM08_SUBMIT_SUCCESS, ctx)` hoặc `notify.fromOk(resp)`.
- KHÔNG còn `try/catch` tự build string từ `e.message` BE.

### 11.5 Quy tắc severity (chốt cho IMM-08)

- `warning` = lỗi nghiệp vụ user tự sửa được (validation BR-08-*, bad-state, not-found,
  conflict) → toast vàng, GIỮ form, không reload.
- `error` = lỗi hệ thống (`SYS-*`) → toast đỏ.
- `success` = thao tác thành công → toast xanh.

> Lưu ý: BR-08-* của PM là validation nghiệp vụ user sửa được, KHÔNG phải compliance
> blocking như BR-12 (clinical impact / RCA gate). Do đó severity = `warning`, không
> `critical`. Photo evidence BR-08-06 dù bắt buộc theo ISO 13485 vẫn để `warning`
> (user tự đính kèm ảnh, không cần modal blocking).

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
