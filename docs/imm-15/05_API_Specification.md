# 05 — Đặc tả API — IMM-15 Theo dõi tồn kho phụ tùng

> ✅ Implemented — Wave 2. Cả `api/inventory.py` (AC backbone) và `api/imm15.py` (IMM transaction layer) đều LIVE. FE đã wire qua `frontend/src/api/imm15.ts` và `frontend/src/api/inventory.ts`.

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-15 — Spare Parts Inventory Tracking |
| Phiên bản | 0.2.0 |
| Ngày | 2026-05-14 |
| Base path (AC backbone) | `/api/method/assetcore.api.inventory.<endpoint>` |
| Base path (IMM-15) | `/api/method/assetcore.api.imm15.<endpoint>` |
| Trạng thái | IMPLEMENTED |

---

## 1. Tổng quan

### 1.1 Response Envelope (MANDATORY)

```json
// Thành công
{"success": true, "data": { ... }}

// Thất bại
{"success": false, "error": "Mô tả lỗi tiếng Việt", "code": "ERROR_CODE_ENUM"}
```

HTTP status: **luôn 200**. FE phân biệt qua `success`.

### 1.2 Authentication

Frappe session / API Key. Mọi endpoint yêu cầu login.

### 1.3 Phân chia API

| File | Status | Mô tả |
|---|---|---|
| `api/inventory.py` | **LIVE** | ~30 endpoints master + movement (AC backbone) — IMM-15 FE tái sử dụng |
| `api/imm15.py` | **LIVE** | Transaction endpoints (Allocation / Cycle Count / Forecast / Watchlist / Dashboard / Low-Stock alerts) — 21 whitelist methods. Xem `assetcore/api/imm15.py` để biết signature chính xác |

> Endpoint bổ sung so với draft 0.1.0 (đã có trong code 0.2.0): `submit_cycle_count` (đếm xong → Reviewed), `return_allocation` (alias path), `get_stock_snapshot`, `get_critical_watchlist`. Mọi endpoint giữ envelope `{success, data}` qua `_handle()` wrapper (xem `api/imm15.py:29`).

---

## 2. Role Constants & Permission Matrix

```python
# assetcore/constants.py (IMM-15 additions)
ROLE_STOREKEEPER       = "IMM Storekeeper"
ROLE_WORKSHOP_LEAD     = "IMM Workshop Lead"
ROLE_BIOMED_TECH       = "IMM Biomed Technician"
ROLE_TECHNICIAN        = "IMM Technician"
ROLE_QA_OFFICER        = "IMM QA Officer"
ROLE_OPS_MANAGER       = "IMM Operations Manager"
ROLE_IMM_ADMIN         = "IMM System Admin"

_APPROVE_ALLOCATION_ROLES = {ROLE_WORKSHOP_LEAD, ROLE_OPS_MANAGER, ROLE_IMM_ADMIN}
_ISSUE_ROLES              = {ROLE_STOREKEEPER, ROLE_OPS_MANAGER, ROLE_IMM_ADMIN}
_OVERRIDE_ROLES           = {ROLE_WORKSHOP_LEAD, ROLE_OPS_MANAGER, ROLE_IMM_ADMIN}
_FORECAST_APPROVE_ROLES   = {ROLE_WORKSHOP_LEAD, ROLE_OPS_MANAGER, ROLE_IMM_ADMIN}
```

| Endpoint | Storekeeper | Workshop Lead | Biomed Tech | Technician | QA Officer | Ops Manager | Admin |
|---|---|---|---|---|---|---|---|
| `list_allocations` | R | R | R | R | R | R | R |
| `get_allocation` | R | R | R | R | R | R | R |
| `create_allocation` | W | — | W | W | — | W | W |
| `approve_allocation` | — | W | — | — | — | W | W |
| `issue_allocation` | W | — | — | — | — | W | W |
| `return_items` | W | — | — | — | — | W | W |
| `return_allocation` | W | — | — | — | — | W | W |
| `list_cycle_counts` | R | R | — | R | R | R | R |
| `create_cycle_count` | W | W | — | — | — | W | W |
| `submit_cycle_count` | W | W | — | — | — | W | W |
| `post_cycle_count` | — | W | — | — | — | W | W |
| `list_spare_forecasts` | R | R | — | — | R | R | R |
| `generate_spare_forecast` | W | W | — | — | — | W | W |
| `approve_forecast` | — | W | — | — | — | W | W |
| `list_watchlist` | R | R | R | R | R | R | R |
| `add_to_watchlist` | — | W | — | — | — | W | W |
| `check_part_availability` | R | R | R | R | R | R | R |
| `get_stock_snapshot` | R | R | R | R | R | R | R |
| `get_critical_watchlist` | R | R | R | R | R | R | R |
| `get_dashboard_stats` | R | R | — | — | R | R | R |
| `get_low_stock_alerts` | R | R | — | — | R | R | R |

> Lưu ý so với draft: `create_allocation` cho phép `Storekeeper` (code: `_require_storekeeper_or_tech` bao gồm `Roles.STOREKEEPER`); `generate_spare_forecast` cho phép Storekeeper (code: `_require_any_role` bao gồm `Roles.STOREKEEPER`). `return_allocation` là alias backward-compat của `return_items`.

---

## 3. Endpoint Specifications — IMPLEMENTED (`assetcore/api/imm15.py`)

### 3.1 `list_allocations`

```
GET /api/method/assetcore.api.imm15.list_allocations
```

**Query params:** `workflow_state`, `asset`, `work_order_ref`, `urgency`, `page`, `page_size`

**Response:**
```json
{
  "success": true,
  "data": {
    "data": [
      {
        "name": "SAL-2026-00045",
        "work_order_ref": "WO-2026-00234",
        "asset": "AC-ASSET-00045",
        "urgency": "Routine",
        "allocation_status": "Issued",
        "stock_movement_ref": "AC-SM-2026-00234",
        "total_value": 1500000,
        "requested_date": "2026-05-08"
      }
    ],
    "pagination": {"total": 48, "page": 1, "page_size": 20, "total_pages": 3}
  }
}
```

> Lưu ý: key là `data` (không phải `items`), kèm object `pagination` — khớp với `BaseRepository.list()` contract và TypeScript type `ListEnvelope<T>` trong `api/imm15.ts`.
```

---

### 3.2 `create_allocation`

```
POST /api/method/assetcore.api.imm15.create_allocation
```

**Request body:**
```json
{
  "work_order_doctype": "IMM PM Work Order",
  "work_order_ref": "WO-2026-00234",
  "asset": "AC-ASSET-00045",
  "warehouse_from": "WH-01",
  "urgency": "Routine",
  "required_date": "2026-05-11",
  "items": [
    {
      "spare_part": "AC-SP-2024-0001",
      "qty_requested": 2,
      "used_for": "Replacement"
    }
  ]
}
```

**Response:**
```json
{"success": true, "data": {"name": "SAL-2026-00045", "workflow_state": "Requested"}}
```

**Errors:**
```json
{"success": false, "error": "VR-15-01: Cấp phát phụ tùng phải liên kết Work Order", "code": "BUSINESS_RULE"}
{"success": false, "error": "VR-15-13: Kho WH-01 không còn hoạt động", "code": "VALIDATION"}
```

---

### 3.3 `approve_allocation`

```
POST /api/method/assetcore.api.imm15.approve_allocation
```

**Request body:**
```json
{"name": "SAL-2026-00045"}
```

**Response:**
```json
{"success": true, "data": {"name": "SAL-2026-00045", "workflow_state": "Approved"}}
```

**Errors:**
```json
{"success": false, "error": "Chỉ IMM Workshop Lead / Operations Manager mới được duyệt allocation", "code": "FORBIDDEN"}
{"success": false, "error": "SAL-2026-00045 không ở trạng thái Requested", "code": "BAD_STATE"}
```

---

### 3.4 `issue_allocation`

```
POST /api/method/assetcore.api.imm15.issue_allocation
```

**Request body:**
```json
{
  "name": "SAL-2026-00045",
  "items": [
    {
      "spare_part": "AC-SP-2024-0001",
      "qty_issued": 2,
      "batch_no": "BATCH-2025-001"
    }
  ]
}
```

**Side effects:**
- Tạo và submit `AC Stock Movement` (Issue, reference_type=IMM Spare Allocation)
- `apply_stock_movement()` → `AC Spare Part Stock.qty_on_hand -= qty_issued`
- Ghi `IMM Audit Trail` (action=ISSUED)

**Response:**
```json
{
  "success": true,
  "data": {
    "name": "SAL-2026-00045",
    "workflow_state": "Issued",
    "stock_movement_ref": "AC-SM-2026-00234"
  }
}
```

**Errors:**
```json
{"success": false, "error": "VR-15-03: Tồn kho không đủ — available: 1, cần: 2", "code": "BUSINESS_RULE"}
{"success": false, "error": "VR-15-02: Phụ tùng AC-SP-2024-0001 yêu cầu số lô/serial", "code": "VALIDATION"}
{"success": false, "error": "Tạo AC Stock Movement thất bại", "code": "INTERNAL"}
```

---

### 3.5 `return_items`

```
POST /api/method/assetcore.api.imm15.return_items
```

**Request body:**
```json
{
  "name": "SAL-2026-00045",
  "items": [
    {
      "spare_part": "AC-SP-2024-0001",
      "qty_returned": 1,
      "return_condition": "Good"
    }
  ]
}
```

**Side effects:**
- `return_condition=Good` → to_warehouse = warehouse_from (nhập kho lại)
- `return_condition=Damaged` → to_warehouse = QC Hold warehouse

**Response:**
```json
{
  "success": true,
  "data": {
    "name": "SAL-2026-00045",
    "workflow_state": "Returned",
    "stock_movement_return_ref": "AC-SM-2026-00235"
  }
}
```

**Errors:**
```json
{"success": false, "error": "VR-15-08: Số lượng trả (3) vượt số đã xuất (2)", "code": "VALIDATION"}
```

---

### 3.6 `create_cycle_count`

```
POST /api/method/assetcore.api.imm15.create_cycle_count
```

**Request body:**
```json
{
  "warehouse": "WH-01",
  "count_date": "2026-05-10",
  "count_type": "ABC_A_Monthly",
  "counted_by": "storekeeper@hospital.vn",
  "spare_parts": ["AC-SP-2024-0001", "AC-SP-2024-0002"]
}
```

**Side effects:**
- Snapshot `system_qty` từ `AC Spare Part Stock.qty_on_hand` tại thời điểm tạo
- Tạo `IMM Cycle Count Item` per spare_part

**Response:**
```json
{
  "success": true,
  "data": {
    "name": "CYC-2026-00012",
    "workflow_state": "Planned",
    "items_count": 2
  }
}
```

---

### 3.7 `post_cycle_count`

```
POST /api/method/assetcore.api.imm15.post_cycle_count
```

**Request body:**
```json
{
  "name": "CYC-2026-00012",
  "verified_by": "workshop.lead@hospital.vn",
  "notes": "Kiểm kê tháng 5 chu kỳ A"
}
```

**Pre-condition:** Cycle Count ở trạng thái Reviewed; VR-15-11 verified_by ≠ counted_by

**Side effects:**
- Tạo và submit `AC Stock Movement` (Adjustment, reference_type=IMM Stock Cycle Count)
- `qty_on_hand := counted_qty` cho từng item
- Seed CAPA cho items capa_required=1

**Response:**
```json
{
  "success": true,
  "data": {
    "name": "CYC-2026-00012",
    "workflow_state": "Posted",
    "adjustment_ref": "AC-SM-2026-00235",
    "capa_created": 1
  }
}
```

**Errors:**
```json
{"success": false, "error": "VR-15-11: Người kiểm tra phải khác người kiểm kê (segregation)", "code": "BUSINESS_RULE"}
{"success": false, "error": "Một số item chưa điền root_cause cho variance > 5%", "code": "VALIDATION"}
```

---

### 3.8 `generate_spare_forecast`

```
POST /api/method/assetcore.api.imm15.generate_spare_forecast
```

**Request body:**
```json
{
  "forecast_period": "2026-Q3",
  "method": "Moving_Avg"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "name": "SFC-2026-00008",
    "forecast_period": "2026-Q3",
    "workflow_state": "Draft",
    "items_count": 145
  }
}
```

---

### 3.9 `approve_forecast`

```
POST /api/method/assetcore.api.imm15.approve_forecast
```

**Request body:**
```json
{"name": "SFC-2026-00008"}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "name": "SFC-2026-00008",
    "workflow_state": "Approved",
    "reorder_recommendations": 12
  }
}
```

---

### 3.10 `add_to_watchlist`

```
POST /api/method/assetcore.api.imm15.add_to_watchlist
```

**Request body:**
```json
{
  "watchlist_name": "ICU-Ventilator-Circuit",
  "critical_asset": "AC-ASSET-00045",
  "spare_part": "AC-SP-2024-0099",
  "min_required_on_hand": 2,
  "warehouse": "WH-01"
}
```

**Pre-condition:** spare_part.imm_part_class = "Critical" (VR-15-09)

**Response:**
```json
{"success": true, "data": {"name": "ICU-Ventilator-Circuit", "active": true}}
```

**Errors:**
```json
{"success": false, "error": "VR-15-09: Chỉ phụ tùng Critical mới được thêm vào Watchlist", "code": "VALIDATION"}
```

---

### 3.5b `return_allocation` (backward-compat alias)

```
POST /api/method/assetcore.api.imm15.return_allocation
```

**Deprecated**: Giữ để backward compat — gọi `svc.return_items` nội bộ. Prefer `return_items` (§3.5).

**Request body:**
```json
{"allocation_name": "SAL-2026-00045", "return_items": [{"spare_part": "...", "qty_returned": 1}]}
```

---

### 3.6b `list_cycle_counts`

```
GET /api/method/assetcore.api.imm15.list_cycle_counts
```

**Query params:** `status`, `warehouse`, `page`, `page_size`

**Response:**
```json
{
  "success": true,
  "data": {
    "data": [{"name": "CYC-2026-00012", "warehouse": "WH-01", "count_date": "2026-05-10", "status": "Posted", "variance_count": 1}],
    "pagination": {"total": 48, "page": 1, "page_size": 20, "total_pages": 3}
  }
}
```

---

### 3.7b `submit_cycle_count` (internal review step)

```
POST /api/method/assetcore.api.imm15.submit_cycle_count
```

Chuyển trạng thái Planned/Counting → Reviewed, tính variance. Thường được gọi nội bộ trước `post_cycle_count`.

**Request body:**
```json
{"count_name": "CYC-2026-00012", "counted_items": [{"spare_part": "AC-SP-001", "counted_qty": 4}]}
```

**Response:**
```json
{"success": true, "data": {"name": "CYC-2026-00012", "workflow_state": "Reviewed", "variance_count": 1}}
```

---

### 3.8b `list_spare_forecasts`

```
GET /api/method/assetcore.api.imm15.list_spare_forecasts
```

**Query params:** `filters` (JSON), `page`, `page_size`

**Response:**
```json
{
  "success": true,
  "data": {
    "data": [{"name": "SFC-2026-00008", "forecast_period": "2026-Q3", "method": "Moving_Avg", "workflow_state": "Draft"}],
    "pagination": {"total": 8, "page": 1, "page_size": 20, "total_pages": 1}
  }
}
```

---

### 3.10b `list_watchlist`

```
GET /api/method/assetcore.api.imm15.list_watchlist
```

**Query params:** `active_only` (default 1), `page`, `page_size`

**Response:**
```json
{
  "success": true,
  "data": {
    "data": [{"name": "ICU-Ventilator-Circuit", "spare_part": "AC-SP-0099", "min_required_on_hand": 2, "active": 1}],
    "pagination": {"total": 47, "page": 1, "page_size": 50, "total_pages": 1}
  }
}
```

---

### 3.11b `get_stock_snapshot`

```
GET /api/method/assetcore.api.imm15.get_stock_snapshot?warehouse=WH-01
```

**Response:**
```json
{
  "success": true,
  "data": [
    {"spare_part": "AC-SP-001", "part_name": "X-ray Tube", "qty_on_hand": 1, "reserved_qty": 0, "available_qty": 1, "last_movement_date": "2026-05-08"}
  ]
}
```

---

### 3.11c `get_critical_watchlist`

```
GET /api/method/assetcore.api.imm15.get_critical_watchlist
```

**Mô tả**: Legacy endpoint — trả danh sách watchlist entries đang vi phạm mức tối thiểu (`below_minimum=true`). Khác với `list_watchlist` (trả toàn bộ).

**Response:**
```json
{
  "success": true,
  "data": [
    {"name": "ICU-Ventilator-Circuit", "spare_part": "AC-SP-0099", "available_qty": 0, "min_required": 2, "below_minimum": true}
  ]
}
```

---

### 3.11 `check_part_availability`

```
GET /api/method/assetcore.api.imm15.check_part_availability
  ?items=[{"spare_part":"AC-SP-2024-0001","qty":3},{"spare_part":"AC-SP-2024-0002","qty":1}]
  &warehouse=WH-01
  &include_alternatives=1
```

**Params:**

| Param | Type | Reqd | Mô tả |
|---|---|---|---|
| `items` | JSON array `[{"spare_part": str, "qty": int}]` | * | Danh sách phụ tùng cần kiểm tra (bulk) |
| `warehouse` | Data | * | Kho kiểm tra tồn kho |
| `include_alternatives` | Int (0/1) | — | Có trả về phụ tùng thay thế (default 0) |

**Wrap:** `services.inventory.get_available_qty` (per item)

**Response:**
```json
{
  "success": true,
  "data": {
    "warehouse": "WH-01",
    "results": [
      {
        "spare_part": "AC-SP-2024-0001",
        "qty_on_hand": 5,
        "reserved_qty": 1,
        "available_qty": 4,
        "qty_needed": 3,
        "sufficient": true,
        "imm_part_class": "Critical",
        "imm_alternative_parts": [
          {"alt_spare_part": "AC-SP-2024-0099", "priority": 1, "available_qty": 2}
        ]
      },
      {
        "spare_part": "AC-SP-2024-0002",
        "qty_on_hand": 0,
        "reserved_qty": 0,
        "available_qty": 0,
        "qty_needed": 1,
        "sufficient": false,
        "imm_part_class": "Major",
        "imm_alternative_parts": []
      }
    ],
    "all_sufficient": false
  }
}
```

---

### 3.12 `get_dashboard_stats`

```
GET /api/method/assetcore.api.imm15.get_dashboard_stats?period=2026-05
```

**Response:**
```json
{
  "success": true,
  "data": {
    "period": "2026-05",
    "stock_turnover_year": {"value": 4.2, "target": 4.0, "status": "green"},
    "days_on_hand_avg": {"value": 45, "target_min": 30, "target_max": 60, "status": "green"},
    "stockout_incidents_30d": {"value": 1, "target": 2, "status": "green"},
    "critical_breach_hours_30d": {"value": 0, "target": 0, "status": "green"},
    "cycle_count_accuracy_pct": {"value": 98.5, "target": 98, "status": "green"},
    "forecast_mape_pct": {"value": 22, "target": 25, "status": "green"},
    "emergency_override_count_30d": {"value": 2, "target": 3, "status": "green"},
    "low_stock_alerts": 5,
    "pending_allocations": 8,
    "pending_cycle_counts": 2
  }
}
```

---

### 3.13 `get_low_stock_alerts`

```
GET /api/method/assetcore.api.imm15.get_low_stock_alerts?warehouse=WH-01
```

**Response:**
```json
{
  "success": true,
  "data": {
    "alerts": [
      {
        "spare_part": "AC-SP-2024-0001",
        "part_name": "Dây mạch máy thở",
        "warehouse": "WH-01",
        "qty_on_hand": 0.5,
        "min_stock_level": 2,
        "imm_part_class": "Critical",
        "is_in_watchlist": true
      }
    ],
    "total": 5
  }
}
```

---

## 4. LIVE Endpoints (api/inventory.py — Tái sử dụng)

IMM-15 FE tái sử dụng các endpoint LIVE sau từ `api/inventory.py`:

| Endpoint | Mục đích IMM-15 |
|---|---|
| `list_spare_parts` | Danh sách phụ tùng + filter imm_part_class |
| `get_spare_part` | Chi tiết phụ tùng + custom fields IMM |
| `update_spare_part` | Cập nhật imm_part_class, imm_abc_class, imm_lead_time_days ... |
| `list_warehouses` | Chọn kho cho Allocation |
| `list_stock_levels` | Tồn kho hiện tại per (spare, warehouse) |
| `get_stock_overview` | Dashboard tổng quan tồn kho |
| `list_stock_movements` | Lịch sử movement (filter reference_type=IMM Spare Allocation) |
| `search_parts_autocomplete` | Tìm kiếm phụ tùng khi tạo Allocation |
| `create_stock_movement` | Fallback manual (non-workflow) |

---

## 5. Error Code Catalog

| Tình huống | code | Ví dụ `error` |
|---|---|---|
| Allocation không có WO link | `BUSINESS_RULE` | "VR-15-01: Cấp phát phụ tùng phải liên kết Work Order" |
| Thiếu batch/serial | `VALIDATION` | "VR-15-02: Phụ tùng SP-FILTER-001 yêu cầu số lô/serial" |
| Tồn kho không đủ | `BUSINESS_RULE` | "VR-15-03: Tồn kho không đủ — available: 1, cần: 2" |
| Variance không có root_cause | `VALIDATION` | "VR-15-04: Chênh lệch 20% — cần nhập nguyên nhân" |
| Urgency không hợp lệ | `VALIDATION` | "VR-15-05: Mức độ khẩn cấp không hợp lệ" |
| Reorder < safety stock | `VALIDATION` | "VR-15-07: Điểm đặt hàng phải ≥ safety stock" |
| Trả vượt số xuất | `VALIDATION` | "VR-15-08: Số lượng trả (3) vượt số đã xuất (2)" |
| Watchlist: không phải Critical | `VALIDATION` | "VR-15-09: Chỉ phụ tùng Critical mới được thêm vào Watchlist" |
| Emergency: 2 approver giống nhau | `BUSINESS_RULE` | "VR-15-10: Emergency override cần 2 người duyệt khác nhau" |
| Cycle count: segregation fail | `BUSINESS_RULE` | "VR-15-11: Người kiểm tra phải khác người kiểm kê" |
| Kho không hoạt động | `VALIDATION` | "VR-15-13: Kho WH-01 không còn hoạt động" |
| AC Stock Movement fail | `INTERNAL` | "Tạo AC Stock Movement thất bại" |
| Sai state | `BAD_STATE` | "SAL-2026-00045 không ở trạng thái Requested" |
| Không đủ quyền | `FORBIDDEN` | "Chỉ IMM Workshop Lead mới được duyệt" |
| Không tìm thấy | `NOT_FOUND` | "IMM Spare Allocation SAL-2026-99999 không tồn tại" |

---

## 6. TypeScript Types

```typescript
// types/imm15.ts

export type AllocationState =
  | "Requested"
  | "Approved"
  | "Picked"
  | "Issued"
  | "Returned"
  | "Cancelled";

export type UrgencyLevel = "Routine" | "Urgent" | "Emergency";
export type PartClass = "Critical" | "Major" | "Consumable" | "Tool";
export type ABCClass = "A" | "B" | "C";
export type XYZClass = "X" | "Y" | "Z";
export type ReturnCondition = "Good" | "Damaged" | "Used";
export type CycleCountType = "Full" | "ABC_A_Monthly" | "Cycle" | "Spot";
export type CycleCountState = "Planned" | "Counting" | "Reviewed" | "Posted";
export type ForecastMethod = "Moving_Avg" | "PM_Driven" | "Failure_Rate" | "Manual";
export type RecommendedAction = "Hold" | "Reorder" | "ReduceMin" | "Obsolete";

export interface AllocationItem {
  spare_part: string;
  part_name: string;
  qty_requested: number;
  qty_approved?: number;
  qty_issued?: number;
  qty_returned?: number;
  uom: string;
  batch_no?: string;
  serial_no?: string;
  unit_value: number;
  line_value: number;
  used_for?: string;
  return_condition?: ReturnCondition;
}

export interface IMMSpareAllocation {
  name: string;
  work_order_doctype?: string;
  work_order_ref?: string;
  asset: string;
  warehouse_from: string;
  urgency: UrgencyLevel;
  items: AllocationItem[];
  total_value: number;
  workflow_state: AllocationState;
  stock_movement_ref?: string;
  stock_movement_return_ref?: string;
  audit_flags?: string;
  override_approver_2?: string;
  override_reason?: string;
  docstatus: 0 | 1 | 2;
}

export interface CycleCountItem {
  spare_part: string;
  system_qty: number;
  counted_qty?: number;
  variance_qty?: number;
  variance_pct?: number;
  variance_value?: number;
  root_cause?: string;
  capa_required: boolean;
  capa_ref?: string;
}

export interface IMMStockCycleCount {
  name: string;
  warehouse: string;
  count_date: string;
  count_type: CycleCountType;
  counted_by: string;
  verified_by?: string;
  workflow_state: CycleCountState;
  items: CycleCountItem[];
  variance_count: number;
  variance_value: number;
  posted_movement_ref?: string;
  docstatus: 0 | 1;
}

export interface SparePartWithIMM {
  name: string;
  part_code: string;
  part_name: string;
  imm_part_class: PartClass;
  imm_abc_class: ABCClass;
  imm_xyz_class: XYZClass;
  imm_lead_time_days: number;
  imm_safety_stock_days: number;
  imm_traceability_required: boolean;
  imm_storage_condition: string;
  min_stock_level: number;
  max_stock_level: number;
  is_critical: boolean;
  is_active: boolean;
}

export interface PartAvailabilityResult {
  spare_part: string;
  warehouse: string;
  qty_on_hand: number;
  reserved_qty: number;
  available_qty: number;
  qty_needed: number;
  sufficient: boolean;
  imm_part_class: PartClass;
  imm_alternative_parts: Array<{
    alt_spare_part: string;
    priority: number;
    available_qty: number;
  }>;
}

export interface WatchlistEntry {
  name: string;
  critical_asset: string;
  spare_part: string;
  min_required_on_hand: number;
  warehouse: string;
  last_breach_date?: string;
  breach_count_30d: number;
  active: boolean;
}

export interface Imm15DashboardStats {
  period: string;
  stock_turnover_year: KPIValue;
  days_on_hand_avg: KPIValue;
  stockout_incidents_30d: KPIValue;
  critical_breach_hours_30d: KPIValue;
  cycle_count_accuracy_pct: KPIValue;
  forecast_mape_pct: KPIValue;
  emergency_override_count_30d: KPIValue;
  low_stock_alerts: number;
  pending_allocations: number;
}

export interface KPIValue {
  value: number;
  target?: number;
  status: "green" | "yellow" | "red";
}

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  code?: string;
}
```

---

## 7. Realtime Events

| Event | Payload | Phát bởi | Subscriber |
|---|---|---|---|
| `imm15_allocation_issued` | `{"name": "SAL-2026-00045", "asset": "...", "stock_movement_ref": "..."}` | `issue_allocation()` | WO dashboard (update spare status) |
| `imm15_low_stock_alert` | `{"spare_part": "...", "warehouse": "...", "qty_on_hand": 0.5}` | Scheduler | Storekeeper dashboard |
| `imm15_critical_breach` | `{"watchlist": "...", "asset": "...", "spare_part": "...", "qty": 1}` | `check_critical_spare_breach()` | Workshop Lead + Ops Manager urgent inbox |
| `imm15_cycle_count_posted` | `{"name": "CYC-2026-00012", "adjustment_ref": "...", "capa_count": 1}` | `post_cycle_count()` | QA Officer dashboard |
| `imm15_forecast_approved` | `{"name": "SFC-2026-00008", "reorder_count": 12}` | `approve_forecast()` | Procurement dashboard (IMM-03 trigger) |

---

## 8. Implementation Notes

1. **RULE-F03:** Mọi movement phải sinh `AC Stock Movement` submitted. KHÔNG cập nhật `AC Spare Part Stock` trực tiếp.
2. **RULE-F04:** Allocation/CycleCount chỉ LINK tới `AC Stock Movement` qua `stock_movement_ref`. Không ghi stock trực tiếp.
3. **Emergency path:** API `issue_allocation` phải kiểm tra VR-15-10 (double-approval) trước khi bypass VR-15-03.
4. **Concurrency:** Issue allocation song song trên cùng spare_part → dùng `FOR UPDATE` lock trong `vr_03_stock_sufficient()`.
5. **Backward compat:** Mở rộng `reference_type` của `AC Stock Movement` qua Property Setter — KHÔNG sửa core JSON.
6. **Gated Spare Batch:** Nếu `IMM Spare Batch` chưa build, `check_expiring_batches()` log "no-op (gated)" và return. `batch_no` field trên Allocation Item dùng làm Data.
7. **ABC quarterly:** Khai trong `hooks.py` dưới `"cron"` key — Frappe v15 không hỗ trợ key `"quarterly"`.
