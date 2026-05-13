# IMM-15 — API Interface Specification

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-15 — Spare Parts Inventory Tracking |
| Phiên bản | 0.2 (aligned với AC inventory backbone) |
| Ngày cập nhật | 2026-05-04 |
| Trạng thái | PARTIAL — `inventory.py` LIVE, `imm15.py` PLANNED |
| Base URL (LIVE) | `/api/method/assetcore.api.inventory.<func>` |
| Base URL (NEW) | `/api/method/assetcore.api.imm15.<func>` |
| Tác giả | AssetCore Team |

---

## 1. Authentication

```http
# API Token (server-to-server)
Authorization: token <api_key>:<api_secret>

# Session cookie (browser)
Cookie: sid=<session_id>
```

| HTTP code | Khi nào trả |
|---|---|
| 401 | Thiếu / sai credential |
| 403 | User không có Role hợp lệ; hoặc role không match `_APPROVE_ALLOCATION_ROLES` / `_ISSUE_ROLES` / `_OVERRIDE_ROLES` |

---

## 2. Response Format

Frappe wrap mọi response trong outer envelope `{"message": ...}`. Bên trong là `_ok()` / `_err()`:

**Success (HTTP 200):**

```json
{ "message": { "success": true, "data": { /* payload */ } } }
```

**Error:**

```json
{ "message": { "success": false, "error": "Mô tả tiếng Việt", "code": "ERROR_CODE" } }
```

Helper `assetcore/utils/helpers.py`:

```python
def _ok(data): return {"success": True, "data": data}
def _err(msg, code="ERROR"): return {"success": False, "error": msg, "code": code}
```

**Pagination shape:**

```json
{ "items": [...], "pagination": {"page": 1, "page_size": 20, "total": 137, "total_pages": 7} }
```

---

## 3. Endpoints đã có (LIVE — `assetcore/api/inventory.py`)

> File: `assetcore/api/inventory.py` (~991 LOC, 30 endpoint). IMM-15 UI **tái sử dụng** các endpoint này cho master + giao dịch. **Không cần re-implement**.

### 3.1 Master — `AC Spare Part`

| Endpoint | Method | Mô tả |
|---|---|---|
| `list_spare_parts` | GET | Pagination + filter (q, category, active_only); enrich `_enrich_stock_totals` (tổng qty across warehouses) |
| `get_spare_part` | GET | Detail master (params: `name`) |
| `create_spare_part` | POST | Tạo mới (payload: full doc) |
| `update_spare_part` | POST | Update (params: `name`) |
| `delete_spare_part` | POST | Soft check trước khi xóa |
| `search_parts_autocomplete` | GET | Autocomplete cho UI dropdown |

### 3.2 UOM

| Endpoint | Method | Mô tả |
|---|---|---|
| `list_uoms` / `list_uoms_full` | GET | Liệt kê AC UOM |
| `get_uom`, `create_uom`, `update_uom`, `delete_uom` | GET/POST | CRUD AC UOM |
| `seed_ac_uoms` | POST | Seed UOM mặc định |
| `list_parts_uom`, `list_parts_missing_uom` | GET | Audit UOM |
| `update_part_uom`, `bulk_assign_default_uom` | POST | Cập nhật UOM hàng loạt |
| `upsert_uom_conversion`, `remove_uom_conversion` | POST | Bảng quy đổi |
| `get_uom_info`, `convert_qty` | GET | Quy đổi đơn vị runtime |

### 3.3 Warehouse — `AC Warehouse`

| Endpoint | Method | Mô tả |
|---|---|---|
| `list_warehouses` | GET | Filter `active_only` |
| `get_warehouse` | GET | — |
| `create_warehouse`, `update_warehouse`, `delete_warehouse` | POST | CRUD |

### 3.4 Stock Level — `AC Spare Part Stock`

| Endpoint | Method | Mô tả |
|---|---|---|
| `get_stock_overview` | GET | Tổng quan: tổng tồn, items, low-stock count |
| `list_stock_levels` | GET | Per (warehouse, spare_part) — filter mode `low` / `all` |

### 3.5 Movement — `AC Stock Movement`

| Endpoint | Method | Mô tả |
|---|---|---|
| `list_stock_movements` | GET | Filter (movement_type, warehouse, status, date_from/to) |
| `get_stock_movement` | GET | Detail (params: `name`) |
| `create_stock_movement` | POST | Tạo Draft (payload JSON) |
| `submit_stock_movement` | POST | Submit → trigger `services.inventory.apply_stock_movement` (cập nhật `AC Spare Part Stock`) |
| `cancel_stock_movement` | POST | Cancel → trigger `services.inventory.reverse_stock_movement` |
| `update_stock_movement` | POST | Update Draft |
| `delete_stock_movement` | POST | — |
| `search_reference_docs` | GET | Tìm WO/Purchase ref cho dynamic link (Asset Repair / PM Work Order / AC Purchase). **IMM-15 sẽ thêm options `IMM Spare Allocation`, `IMM Stock Cycle Count` qua Property Setter.** |

> **IMM-15 dùng các endpoint trên thay vì re-implement.** UI Spare Item List, Stock Level, Stock Movement Detail (đã có ở frontend) tiếp tục dùng inventory.py. IMM-15 thêm UI cho Allocation/Cycle Count/Forecast/Watchlist (gọi imm15.py mới) và liên kết tới các trang LIVE.

---

## 4. Endpoints mới (PLANNED — `assetcore/api/imm15.py`)

~16 endpoint nghiệp vụ transaction-level.

### 4.1 Allocation CRUD & Workflow

#### 4.1.1 `list_allocations`

| Method | GET |
|---|---|
| Path | `assetcore.api.imm15.list_allocations` |

**Params:** `filters` (JSON), `work_order_ref`, `asset`, `status`, `urgency`, `page`, `page_size`

**Response:** `{items: [...], pagination}` — fields: `name, work_order_ref, asset, urgency, allocation_status, total_value, requested_date, requested_by, stock_movement_ref`

#### 4.1.2 `get_allocation`

| Method | GET |
|---|---|

**Params:** `name`

**Response:** Full doc + child items + audit_flags + stock_movement_ref + stock_movement_return_ref

**Errors:** `NOT_FOUND`

#### 4.1.3 `create_allocation`

| Method | POST |
|---|---|
| Roles | All authenticated với perm tạo (Biomed, Technician, Storekeeper, Workshop Lead, Operations Manager, System Admin) |

**Body:**

```json
{
  "work_order_doctype": "IMM PM Work Order",
  "work_order_ref": "WO-PM-2026-0007",
  "asset": "AC-ASSET-2026-0001",
  "warehouse_from": "AC-WH-0001",
  "urgency": "Routine",
  "required_date": "2026-05-10",
  "items": [
    {"spare_part": "AC-SP-2026-0001", "qty_requested": 2, "used_for": "Replacement"}
  ],
  "notes": "PM quý 2"
}
```

**Response:** `{name, workflow_state: "Requested", total_value, approval_required}`

**Errors:** `INVALID_DATA`, `VALIDATION_ERROR` (VR-15-01/05/13), `CREATE_ERROR`

#### 4.1.4 `approve_allocation`

| Method | POST |
|---|---|
| Roles | `_APPROVE_ALLOCATION_ROLES` |

**Body:** `name`, `qty_approved_overrides` (optional dict {spare_part: qty})

**Hành vi:**

1. Validate state = `Requested` (`INVALID_STATE`)
2. Validate user thuộc `_APPROVE_ALLOCATION_ROLES` (`FORBIDDEN`)
3. Set `qty_approved` mặc định = `qty_requested`, hoặc override theo body
4. workflow_state → `Approved`, set `approved_by`, `approval_date`
5. Update `AC Spare Part Stock.reserved_qty` += `qty_approved`
6. Audit log

**Response:** `{name, new_state: "Approved", approved_by, approval_date}`

#### 4.1.5 `issue_allocation`

| Method | POST |
|---|---|
| Roles | `_ISSUE_ROLES` |

**Body:**

```json
{
  "name": "SAL-2026-0042",
  "items": [
    {"spare_part": "AC-SP-2026-0001", "qty_issued": 2, "batch_no": "BATCH-2026-04", "serial_no": null}
  ],
  "override": {
    "approver_2": "ops_mgr@hosp.vn",
    "reason": "CT khẩn cấp 03:00 sáng, không kịp chờ đặt"
  }
}
```

**Hành vi:**

1. Validate state IN (`Approved`, `Picked`) — Emergency có thể từ `Requested`
2. VR-15-02 traceability check (theo `AC Spare Part.imm_traceability_required`)
3. VR-15-03 stock sufficient (`AC Spare Part Stock.available_qty FOR UPDATE`) — nếu Emergency + Critical + insufficient → require override
4. VR-15-10 hai approver khác nhau
5. Service `allocation_service.create_ac_stock_movement_for_issue()` — sinh **`AC Stock Movement`** với `movement_type="Issue"`, `from_warehouse=warehouse_from`, `reference_type="IMM Spare Allocation"`, `reference_name=name`. Submit → `apply_stock_movement` (LIVE) tự động giảm `qty_on_hand` và `reserved_qty`.
6. workflow_state → `Issued`; `stock_movement_ref` set
7. Audit log với `audit_flags="EMERGENCY_OVERRIDE"` nếu có

**Response:** `{name, new_state: "Issued", stock_movement: "AC-SM-2026-#####"}`

**Errors:** `INVALID_STATE`, `FORBIDDEN`, `VALIDATION_ERROR` (VR-15-02/03/10), `REQUIRE_OVERRIDE`, `STOCK_ERROR`

#### 4.1.6 `return_items`

| Method | POST |
|---|---|
| Roles | Storekeeper, Operations Manager, System Admin |

**Body:**

```json
{
  "name": "SAL-2026-0042",
  "items": [
    {"spare_part": "AC-SP-2026-0001", "qty_returned": 1, "return_condition": "Good"}
  ]
}
```

**Hành vi:**

1. Validate state = `Issued`
2. VR-15-08 `qty_returned ≤ qty_issued`
3. `return_condition="Damaged"` → tạo `AC Stock Movement` với `to_warehouse="AC-WH-QC-HOLD"` (BR-15-08); ngược lại trả về `warehouse_from` ban đầu
4. Submit movement
5. workflow_state → `Returned`

**Response:** `{name, new_state: "Returned", return_movement: "AC-SM-..."}`

#### 4.1.7 `cancel_allocation`

| Method | POST |
|---|---|
| Roles | Workshop Lead, Operations Manager, System Admin |

**Body:** `name`, `reason`

**Hành vi:** Chỉ cho phép từ {Requested, Approved, Picked}. Nếu state=Approved/Picked → giảm `reserved_qty`. Sau Issued không cancel — phải Return.

### 4.2 Cycle Count

#### 4.2.1 `list_cycle_counts`

| Method | GET |
|---|---|

**Params:** `warehouse`, `count_type`, `status`, `from_date`, `to_date`, `page`, `page_size`

#### 4.2.2 `create_cycle_count`

| Method | POST |
|---|---|
| Roles | Storekeeper, Workshop Lead, Operations Manager, System Admin |

**Body:**

```json
{
  "warehouse": "AC-WH-0001",
  "count_date": "2026-05-15",
  "count_type": "ABC_A_Monthly",
  "counted_by": "storekeeper@hosp.vn",
  "items": [
    {"spare_part": "AC-SP-2026-0001"},
    {"spare_part": "AC-SP-2026-0002"}
  ]
}
```

`system_qty` được auto-fetch từ `AC Spare Part Stock.qty_on_hand` khi create. UI điền `counted_qty` sau khi đếm thực.

**Response:** `{name, status: "Planned"}`

#### 4.2.3 `post_cycle_count`

| Method | POST |
|---|---|
| Roles | Workshop Lead, Operations Manager, System Admin |

**Body:** `name`

**Hành vi:**

1. Validate status = `Reviewed`
2. VR-15-04 + VR-15-11 đã pass khi save Reviewed
3. Service `cycle_count_service.post_to_ac_stock_movement()` — tạo **`AC Stock Movement`** với `movement_type="Adjustment"`, `from_warehouse=warehouse` (nếu giảm) hoặc `to_warehouse` (nếu tăng), `reference_type="IMM Stock Cycle Count"`, `reference_name=name`. Submit → cập nhật `qty_on_hand` về `counted_qty` qua `apply_stock_movement` (LIVE)
4. status → `Posted`, `posted_movement_ref` set
5. Auto-seed CAPA cho item `capa_required=1` (BR-15-05)

**Response:** `{name, new_state: "Posted", stock_movement: "AC-SM-...", capa_seeded: 2}`

### 4.3 Spare Part Forecast (PART-level — distinct với IMM Demand Forecast IMM-01)

#### 4.3.1 `list_spare_forecasts`

| Method | GET |
|---|---|

**Params:** `period`, `workflow_state`, `page`

#### 4.3.2 `generate_spare_forecast`

| Method | POST |
|---|---|
| Roles | Workshop Lead, Storekeeper, Operations Manager, System Admin |

**Body:** `period` (string), `method` (Moving_Avg/PM_Driven/Failure_Rate/Manual)

**Hành vi:** Trigger thủ công thay scheduler. Tạo `IMM Spare Part Forecast` Draft.

**Response:** `{name, period, method, items_count, status: "Draft"}`

#### 4.3.3 `approve_forecast`

| Method | POST |
|---|---|
| Roles | `_FORECAST_APPROVE_ROLES` |

**Body:** `name`

**Hành vi:**

1. Validate state = `Draft`
2. Set `workflow_state = "Approved"`, `approved_by`
3. Mỗi item có `current_qty < reorder_point` → `recommended_action = "Reorder"`
4. **Wave 2:** UI hiển thị danh sách reorder để user tạo `AC Purchase` thủ công. Wave 3: auto-tạo `AC Purchase` Draft.

**Response:** `{name, new_state: "Approved", reorder_count: 27}`

### 4.4 Critical Spare Watchlist

#### 4.4.1 `list_watchlist`

| Method | GET |
|---|---|

**Params:** `asset` (optional), `active` (default true)

**Response data:**

```json
{
  "count": 47,
  "items": [{
    "name": "WL-CT-TUBE",
    "critical_asset": "AC-ASSET-CT-01",
    "spare_part": "AC-SP-CT-TUBE-01",
    "min_required_on_hand": 1,
    "warehouse": "AC-WH-0001",
    "qty_on_hand": 0,
    "is_breach": true,
    "last_breach_date": "2026-04-30",
    "breach_count_30d": 3
  }]
}
```

#### 4.4.2 `add_to_watchlist`

| Method | POST |
|---|---|
| Roles | Workshop Lead, Operations Manager, System Admin |

**Body:** `critical_asset`, `spare_part`, `min_required_on_hand`, `warehouse`

**Validate:** VR-15-09 (`AC Spare Part.imm_part_class=Critical`)

**Response:** `{name, active: true}`

#### 4.4.3 `remove_from_watchlist`

| Method | POST |
|---|---|

**Body:** `name` — soft (`active=0`).

### 4.5 Dashboard / Reports

#### 4.5.1 `get_dashboard_stats`

| Method | GET |
|---|---|

**Response data:**

```json
{
  "kpis": {
    "stock_turnover_year": 4.2,
    "days_on_hand_avg": 47,
    "stockout_incidents_30d": 1,
    "critical_breach_hours_30d": 0,
    "cycle_accuracy_pct": 98.6,
    "forecast_mape_q": 18.4,
    "emergency_override_count_30d": 1,
    "total_inventory_value": 4200000000
  },
  "low_stock_top10": [...],
  "critical_breach_active": [...],
  "consumption_trend_90d": [
    {"date": "2026-04-01", "pm": 8, "cm": 2, "repair": 1, "value": 12500000}
  ],
  "abc_distribution": {"A": 84, "B": 126, "C": 202}
}
```

#### 4.5.2 `get_low_stock_alerts`

| Method | GET |
|---|---|

**Params:** `warehouse` (optional), `escalation_only` (default false — chỉ items thuộc Watchlist)

**Response:** `{count, items: [{spare_part, warehouse, qty_on_hand, min, shortage, lead_time_days, in_watchlist}]}`

#### 4.5.3 `get_consumption_by_asset`

| Method | GET |
|---|---|

**Params:** `asset`, `from_date`, `to_date`

**Response:** `{asset, total_value, by_part_class: {...}, allocations: [...]}` — derive từ `IMM Spare Allocation` filter `asset=...`

#### 4.5.4 `get_consumption_by_wo`

| Method | GET |
|---|---|

**Params:** `work_order_ref`

**Response:** `{wo, allocations: [...], total_value, items: [...]}` — derive từ `IMM Spare Allocation.work_order_ref`

### 4.6 Inline Integration Helper

#### 4.6.1 `check_part_availability` — Caller IMM-08/09/12

| Method | GET (idempotent) |
|---|---|
| Performance | NFR-15-02 P95 < 300ms |

Wrap `services.inventory.get_available_qty` (LIVE) cho từng item, kèm thông tin `imm_lead_time_days` + `imm_alternative_parts`.

**Params:**

```
items=<JSON>: [{"spare_part": "AC-SP-2026-0001", "qty": 2}, {"spare_part": "AC-SP-2026-0002", "qty": 1}]
warehouse=<AC Warehouse name>
include_alternatives=<bool, default true>
```

**Response data:**

```json
{
  "warehouse": "AC-WH-0001",
  "results": [
    {
      "spare_part": "AC-SP-2026-0001",
      "required": 2,
      "available": 5,
      "sufficient": true,
      "lead_time_days": 30,
      "alternatives": []
    },
    {
      "spare_part": "AC-SP-2026-0002",
      "required": 1,
      "available": 0,
      "sufficient": false,
      "lead_time_days": 60,
      "alternatives": [
        {"spare_part": "AC-SP-2026-0002-ALT", "available": 2, "priority": 1}
      ]
    }
  ],
  "all_sufficient": false
}
```

Caller (IMM-08 PM `before_submit`) dùng `all_sufficient=false` để block hoặc gợi ý tạo `AC Purchase`.

---

## 5. Error Codes

### 5.1 HTTP Status

| Code | Ý nghĩa |
|---|---|
| 200 | OK (kiểm tra `success` trong body) |
| 401 | Thiếu/sai auth |
| 403 | Frappe permission deny |
| 500 | Server error |

### 5.2 Application Error Codes

| Code | Endpoint | Mô tả |
|---|---|---|
| `INVALID_FILTERS` | list_* | filters JSON parse fail |
| `INVALID_DATA` | create_* | body JSON parse fail |
| `NOT_FOUND` | get_*, approve_*, issue_*, return_*, cancel_* | DocType không tồn tại |
| `FORBIDDEN` | approve_allocation, issue_allocation, post_cycle_count, approve_forecast, manage_watchlist | Role/permission không match |
| `INVALID_STATE` | approve/issue/return/cancel/post | workflow_state không phù hợp |
| `VALIDATION_ERROR` | create/issue/return, post_cycle_count, add_to_watchlist | VR-15-01..13 failure |
| `REQUIRE_OVERRIDE` | issue_allocation | Stock không đủ + Critical + Emergency |
| `STOCK_ERROR` | issue_allocation, post_cycle_count | `AC Stock Movement` create/submit fail |
| `CREATE_ERROR` | create_allocation, create_cycle_count | Insert exception |
| `FORECAST_ERROR` | generate_spare_forecast, approve_forecast | Service forecast fail |

---

## 6. Realtime Events

```
imm15.allocation_created          → {name, asset, urgency, total_value}
imm15.allocation_issued           → {name, stock_movement, audit_flags}
imm15.cycle_count_posted          → {name, variance_value, capa_seeded, stock_movement}
imm15.critical_breach_detected    → {watchlist, asset, spare_part, qty_on_hand, min}
imm15.forecast_approved           → {name, period, reorder_count}
```

Audit qua `IMM Audit Trail` + Frappe Version + `AC Stock Movement` (submitted = immutable).

---

## 7. Implementation Notes

| # | Note |
|---|---|
| 1 | **RULE-F03/F04:** Mọi movement do IMM-15 sinh ra phải đi qua `AC Stock Movement` submitted (`reference_type="IMM Spare Allocation"` hoặc `"IMM Stock Cycle Count"`). KHÔNG ghi trực tiếp `AC Spare Part Stock`. |
| 2 | `issue_allocation` và `post_cycle_count` build payload `AC Stock Movement` rồi gọi `assetcore.api.inventory.create_stock_movement` + `submit_stock_movement` — tận dụng validation/transaction đã có. |
| 3 | Concurrency (NFR-15-03): `apply_stock_movement` (LIVE in `services/inventory.py`) đã dùng row-level update qua `frappe.db.set_value`. IMM-15 cần thêm `SELECT ... FOR UPDATE` trước khi check sufficient ở `vr_03_stock_sufficient`. |
| 4 | Emergency override: 2 approver phải khác nhau (`approved_by ≠ override_approver_2`), cùng IN `_OVERRIDE_ROLES`. |
| 5 | `check_part_availability` cache `qty_on_hand` trong Redis (TTL 30s) để đáp ứng NFR-15-02. |
| 6 | Wave 2 chưa auto tạo `AC Purchase` — chỉ recommended_action="Reorder". Wave 3 sẽ implement auto. |
| 7 | Naming series: Allocation `SAL-.YYYY.-.#####`, Cycle Count `CYC-.YYYY.-.#####`, Forecast `SFC-.YYYY.-.#####`, Spare Batch `BAT-.YYYY.-.#####`. |
| 8 | File upload (override proof) qua Frappe File API (`/api/method/upload_file`). API IMM-15 nhận đường dẫn vào field `override_proof` (Attach trong allocation). |
| 9 | Service layer `services/imm15.py` là nơi tập trung logic — controller chỉ gọi service (RULE-S01, CLAUDE.md §15). |
| 10 | Tất cả endpoint mutation gọi `audit_writer.log()` với (actor=session.user, action=ENUM, ref=doc.name, payload=diff). |
| 11 | `imm15.py` KHÔNG re-implement `list_spare_parts`, `list_warehouses`, `list_stock_levels`, `list_stock_movements` — UI gọi trực tiếp `inventory.py`. |
| 12 | Realtime channel = `imm15:{user_role}` — chỉ Workshop Lead + Storekeeper + Operations Manager + System Admin nhận `critical_breach_detected`. |
| 13 | Khi deploy IMM-15: Property Setter mở rộng `AC Stock Movement.reference_type` thêm `IMM Spare Allocation\nIMM Stock Cycle Count` để Dynamic Link `reference_name` hoạt động. |

---

## 8. OpenAPI snippet (extract — IMM-15 mới)

```yaml
openapi: 3.0.3
info:
  title: AssetCore IMM-15 API
  version: 0.2-draft
servers:
  - url: /api/method/assetcore.api.imm15
paths:
  /create_allocation:
    post:
      summary: Create spare part allocation (links to AC Spare Part / AC Warehouse)
      security:
        - frappeAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/AllocationCreateRequest'
      responses:
        '200':
          description: OK
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Envelope'
  /issue_allocation:
    post:
      summary: Issue allocation (creates submitted AC Stock Movement)
  /post_cycle_count:
    post:
      summary: Post cycle count (creates submitted AC Stock Movement Adjustment)
  /check_part_availability:
    get:
      summary: Inline availability check (used by IMM-08/09/12)
      parameters:
        - in: query
          name: items
          required: true
          schema: { type: string, description: "JSON array of {spare_part, qty}" }
        - in: query
          name: warehouse
          required: true
          schema: { type: string, description: "AC Warehouse name" }
components:
  schemas:
    Envelope:
      type: object
      properties:
        message:
          type: object
          properties:
            success: { type: boolean }
            data: { type: object }
            error: { type: string }
            code: { type: string }
    AllocationCreateRequest:
      type: object
      required: [asset, warehouse_from, urgency, items]
      properties:
        work_order_doctype: { type: string, enum: [IMM PM Work Order, IMM CM Work Order, Asset Repair] }
        work_order_ref: { type: string }
        asset: { type: string, description: "AC Asset name" }
        warehouse_from: { type: string, description: "AC Warehouse name" }
        urgency: { type: string, enum: [Routine, Urgent, Emergency] }
        required_date: { type: string, format: date }
        items:
          type: array
          items:
            $ref: '#/components/schemas/AllocationItemRequest'
        notes: { type: string }
    AllocationItemRequest:
      type: object
      required: [spare_part, qty_requested]
      properties:
        spare_part: { type: string, description: "AC Spare Part name" }
        qty_requested: { type: number }
        used_for: { type: string, enum: [Replacement, Test, Calibration, Spare] }
```

Đầy đủ xem `assetcore/api/openapi/imm15.yaml` (PLANNED — generate qua `/dev:generate-api-contract imm15`).
