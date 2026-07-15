# 05 — Đặc tả API — IMM-15 Theo dõi tồn kho phụ tùng

> ✅ Implemented — Wave 2. Cả `api/inventory.py` (AC backbone) và `api/imm15.py` (IMM transaction layer) đều LIVE. FE đã wire qua `frontend/src/api/imm15.ts` và `frontend/src/api/inventory.ts`.

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-15 — Spare Parts Inventory Tracking |
| Phiên bản | 0.0.2 |
| Ngày | 2026-05-27 |
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
| `api/imm15.py` | **LIVE** | Transaction endpoints (Allocation / Cycle Count / Forecast / Watchlist / Dashboard / Low-Stock alerts) — **21 whitelist methods** (verified `grep -c "^@frappe.whitelist" assetcore/api/imm15.py` = 21 on 2026-05-27). Xem `assetcore/api/imm15.py` để biết signature chính xác |

> Endpoint bổ sung so với draft 0.1.0 (đã có trong code 0.2.0): `submit_cycle_count` (đếm xong → Reviewed), `return_allocation` (alias path), `get_stock_snapshot`, `get_critical_watchlist`. Mọi endpoint giữ envelope `{success, data}` qua `_handle()` wrapper (xem `api/imm15.py:29`).

---

## 2. Role Constants & Permission Matrix

```python
# assetcore/constants.py (IMM-15 — aligned with 30-role catalog in fixtures/role.json)
ROLE_INVENTORY_USER     = "Inventory User"
ROLE_INVENTORY_MANAGER  = "Inventory Manager"
ROLE_REPAIR_USER        = "Repair User"          # CM/repair requesters
ROLE_PM_USER            = "PM User"              # PM requesters
ROLE_COMPLIANCE_MANAGER = "Compliance Manager"   # QA / CAPA
ROLE_SUPER_ADMIN        = "AssetCore Super Admin"

_APPROVE_ALLOCATION_ROLES = {ROLE_INVENTORY_MANAGER, ROLE_SUPER_ADMIN}
_ISSUE_ROLES              = {ROLE_INVENTORY_USER, ROLE_INVENTORY_MANAGER, ROLE_SUPER_ADMIN}
_OVERRIDE_ROLES           = {ROLE_INVENTORY_MANAGER, ROLE_SUPER_ADMIN}
_FORECAST_APPROVE_ROLES   = {ROLE_INVENTORY_MANAGER, ROLE_SUPER_ADMIN}
```

| Endpoint | Inventory User | Inventory Manager | Repair User | PM User | Compliance Manager | Super Admin |
|---|---|---|---|---|---|---|
| `list_allocations` | R | R | R | R | R | R |
| `get_allocation` | R | R | R | R | R | R |
| `create_allocation` | W | W | W | W | — | W |
| `approve_allocation` | — | W | — | — | — | W |
| `issue_allocation` | W | W | — | — | — | W |
| `cancel_allocation` | — | W | — | — | — | W |
| `return_items` | W | W | — | — | — | W |
| `return_allocation` | W | W | — | — | — | W |
| `list_cycle_counts` | R | R | — | R | R | R |
| `get_cycle_count` | R | R | — | R | R | R |
| `create_cycle_count` | W | W | — | — | — | W |
| `submit_cycle_count` | W | W | — | — | — | W |
| `post_cycle_count` | — | W | — | — | — | W |
| `recount_cycle_count` | — | W | — | — | — | W |
| `list_spare_forecasts` | R | R | — | — | R | R |
| `generate_spare_forecast` | W | W | — | — | — | W |
| `approve_forecast` | — | W | — | — | — | W |
| `list_watchlist` | R | R | R | R | R | R |
| `add_to_watchlist` | — | W | — | — | — | W |
| `check_part_availability` | R | R | R | R | R | R |
| `get_stock_snapshot` | R | R | R | R | R | R |
| `get_critical_watchlist` | R | R | R | R | R | R |
| `get_dashboard_stats` | R | R | — | — | R | R |
| `get_low_stock_alerts` | R | R | — | — | R | R |

> Lưu ý so với draft cũ: `create_allocation` cho phép `Inventory User` (code: `_require_storekeeper_or_tech`); `generate_spare_forecast` cho phép `Inventory User` (code: `_require_any_role`). `return_allocation` là alias backward-compat của `return_items`. Các role legacy (`IMM Storekeeper`, `IMM Workshop Lead`, …) đã ngừng dùng từ 2026-05-27 sau RBAC consolidation — xem `assetcore/fixtures/role.json` (30-role catalog).

---

## 3. Endpoint Specifications — IMPLEMENTED (`assetcore/api/imm15.py`)

### 3.0 `get_allocation` (detail + allowed_transitions) — **allowed_transitions NEW (vòng 16, CR-WF-15-ALLOC)**

```
GET /api/method/assetcore.api.imm15.get_allocation?name=SAL-2026-00045
```

> `get_allocation` đã tồn tại (api/imm15.py:66 = `_handle(svc.get_allocation, name)`; service imm15.py:224). Vòng 16 CHỈ THÊM key `allowed_transitions` vào `data` — server-driven CTA cho màn AllocationDetail (GATE-8/LL-FE-51: client KHÔNG hardcode `allocation_status===`). API layer KHÔNG đổi (passthrough).

**BE contract (delta vòng 16):** cuối `get_allocation`, sau enrich header/items, thêm:
```python
data["allowed_transitions"] = _allocation_allowed_transitions(doc.allocation_status)
```
- `_allocation_allowed_transitions(status)` = SSoT `_ALLOCATION_ALLOWED_TRANSITIONS.get(status, [])` — **next-state strings** (KHÔNG token; khác `get_cycle_count`), **KHÔNG role-gate**. Xem 04 §VI.1.1 + ADR-IMM-15-10.
- Not-found → `raise ServiceError(NOT_FOUND)` (in-handler **HTTP-200 + Error envelope** qua `_handle`, KHÔNG raise→4xx — DONE-gate).

**`allowed_transitions` — SSoT gating per `allocation_status`:**

| `allocation_status` | `allowed_transitions` | CTA phía FE → endpoint |
|---|---|---|
| `Requested` | `["Approved", "Issued", "Cancelled"]` | "Duyệt" → `approve_allocation` · "Xuất kho (khẩn)" → `issue_allocation` · "Hủy" → `cancel_allocation` |
| `Approved` | `["Issued", "Cancelled"]` | "Xuất kho" → `issue_allocation` (shortcut, bỏ qua Pick chưa-wire) · "Hủy" → `cancel_allocation` |
| `Picked` | `["Cancelled"]` | "Hủy" → `cancel_allocation` (defensive — Picked chỉ tới được qua desk workflow) |
| `Issued` | `["Returned"]` | "Trả phụ tùng" → `return_items` |
| `Returned` | `[]` | (terminal — read-only) |
| `Cancelled` | `[]` | (terminal — read-only) |

> **Deferred (04 §VI.1.1 EXCEPTION):** `Approved→Picked`, `Picked→Issued` (Pick chain chưa wire), `Returned→Issued` ("Đóng phiếu" re-close, chưa có service fn) — workflow json khai nhưng KHÔNG surface CTA. `Approved→Issued` là SHORTCUT (service xuất trực tiếp).

**Response (ví dụ status=Requested):**
```json
{
  "success": true,
  "data": {
    "name": "SAL-2026-00045",
    "work_order_ref": "WO-2026-00234",
    "asset": "AC-ASSET-00045",
    "asset_name": "Máy CT Scanner",
    "warehouse_from": "WH-01",
    "warehouse_name": "Kho trung tâm",
    "requested_by": "storekeeper@hospital.vn",
    "requested_by_name": "Nguyễn Văn A",
    "urgency": "Routine",
    "allocation_status": "Requested",
    "total_value": 1500000,
    "docstatus": 0,
    "items": [
      {"spare_part": "AC-SP-2024-0001", "part_name": "Bóng đèn CT", "qty_requested": 1, "qty_approved": 0, "qty_issued": 0, "uom": "Cái", "unit_value": 1500000}
    ],
    "allowed_transitions": ["Approved", "Issued", "Cancelled"]
  }
}
```

> **Mobile (Trục B — CR-29b, 2026-07-14):** endpoint DETAIL này đã được curate vào OAS mirror
> `docs/mobile/openapi/assetcore-mobile.openapi.yaml` (path `GET .../imm15.get_allocation`, `operationId:
> getAllocation`, tag `inventory`) — **F9-DETAIL** (sibling của `listAllocations` R40/ADR-MOBILE-049) màn
> **"Xuất kho phụ tùng phục vụ WO"**. Contract-only (0 `.py`). Param `name` = **query, required, string**.
> 200 = inline `oneOf [SpareAllocationDetailEnvelope, Error]` (Decision-B: `NOT_FOUND` đến TRÊN HTTP-200 —
> KHÔNG 404 status-line; slot `{200,401,403}`, 403 = **dispatcher-403 ONLY** vì `@whitelist` bare KHÔNG
> `rbac.require`). 2 schema `SpareAllocationItem` (13 field child) + `SpareAllocationDetail` (27 prop header +
> `items[]` + 3 enrich + `allowed_transitions[]`) — **⚠️ CẢ HAI `additionalProperties:true` (OPEN)** vì
> service trả `doc.as_dict()` (mirror `CalibrationDetail`/`TransferDetail`); CHỈ envelope đóng. `used_for`/
> `return_condition` = string nullable KHÔNG enum (Select **leading-blank** `''` unset); `allocation_status` =
> enum 6; `approval_required` = `integer enum[0,1]`. Quyết định: **ADR-MOBILE-050**.

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
>
> **Mobile (Trục B — CR-29a, 2026-07-14):** endpoint này đã được curate vào OAS mirror
> `docs/mobile/openapi/assetcore-mobile.openapi.yaml` (path `GET .../imm15.list_allocations`, `operationId:
> listAllocations`, tag `inventory`) — LIST-ENTRY màn **F9 "Xuất kho phụ tùng phục vụ WO"**. Contract-only
> (0 `.py`). Envelope là **DOUBLE-DATA** `data.data[]` (⚠️ KHÁC `listCommissioning` `data.items[]`);
> item = 14 field (11 `AllocationRepo.list` + 3 enrich `asset_name`/`warehouse_name`/`requested_by_name`,
> out-field theo special-case `services/imm15.py:189-196`). Quyết định: **ADR-MOBILE-049**.
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
{"success": false, "error": "Chỉ Inventory Manager mới được duyệt allocation", "code": "FORBIDDEN"}
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
- VR-15-03 đọc `available_qty` THẬT (= qty_on_hand − reserved_qty của allocation OPEN khác) → chống double-issue
- Tạo và submit `AC Stock Movement` (Issue, reference_type=IMM Spare Allocation)
- `apply_stock_movement()` → `AC Spare Part Stock.qty_on_hand -= qty_issued`
- **RELEASE reserved:** dòng rời HOLDING → `recompute_reserved(warehouse_from, spare_part)` → reserved giải phóng (không double-count)
- Ghi `IMM Audit Trail` `event_type="allocation_issued"` (xem note audit-slug dưới §3.4b)

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

### 3.4b `cancel_allocation`

```
POST /api/method/assetcore.api.imm15.cancel_allocation
```

**Request body:** `{"name": "SAL-2026-00045"}` (hoặc `allocation`/`allocation_name`)

**Side effects:**
- `{Requested, Approved, Picked}` → `Cancelled`; `qty_on_hand` KHÔNG đổi (chưa từng trừ)
- **RELEASE reserved:** `recompute_reserved(warehouse_from, spare_part)` cho mọi dòng → reserved giải phóng
- Ghi `IMM Audit Trail` `event_type="allocation_cancelled"` (xem note audit-slug dưới)

**Response:** `{"success": true, "data": {"name": "SAL-2026-00045", "workflow_state": "Cancelled"}}`

> **Note audit-slug allocation (vòng 12, CR-WF-15-AUDIT · ADR-IMM-15-09):** 5 transition allocation qua helper `_write_allocation_audit(name, action, payload)` ghi ĐÚNG **1** `IMM Audit Trail` mỗi cái, `event_type=f"allocation_{action.lower()}"` ∈ {`allocation_created` (create @258), `allocation_approved` (approve @282), `allocation_issued` (issue @361), `allocation_returned` (return @409), `allocation_cancelled` (cancel @450)}. 5 slug + `cycle_count_posted` = SSoT `IMM15_AUDIT_EVENT_TYPES` PHẢI ⊆ Select options. **Trước vòng 12:** slug ∉ Select ⇒ ValidationError bị `except: pass` @1374 nuốt CÂM ⇒ **0 dòng** (BEFORE 0 / AFTER 1). Fix: register 6 slug + bare `pass`→`log_error` (non-blocking best-effort). Xem 04 §IV-AUDIT + 07 §III.4b.

**Errors:**
```json
{"success": false, "error": "Không thể hủy Allocation đã Issued/Returned", "code": "BAD_STATE"}
{"success": false, "error": "Chỉ Inventory Manager mới được hủy allocation", "code": "FORBIDDEN"}
```

> `recompute_reserved(warehouse, spare_part)` là **hàm nội bộ** (`services.inventory`), KHÔNG whitelist endpoint — chỉ gọi bên trong transition allocation. Consumer đọc `reserved_qty`/`available_qty` qua `get_stock_snapshot` / `check_part_availability` / `get_low_stock_alerts` đã có sẵn.

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

### 3.6a `get_cycle_count` (detail + allowed_transitions) — **NEW (vòng 2, 2026-07-01)**

> Endpoint **MỚI** — chưa tồn tại trong `api/imm15.py`/`services/imm15.py` (verified 2026-07-01). Bổ sung để surface màn **CycleCountDetailView**. `06_Frontend_Design.md` §II.8 đã tham chiếu `imm15.get_cycle_count` từ trước nhưng BE chưa hiện thực → đây là spec-before-code contract để BE build. GATE-8/LL-FE-51: server-driven CTA (client KHÔNG hardcode `status===`).

```
GET /api/method/assetcore.api.imm15.get_cycle_count?name=CYC-2026-00012
```

**BE contract:**
- `api/imm15.py`: `@frappe.whitelist() def get_cycle_count(name: str) -> dict: return _handle(svc.get_cycle_count, name)`
- `services/imm15.py`: `def get_cycle_count(name: str) -> dict` — pattern **giống hệt** `get_calibration` (imm11.py:1033) / `get_allocation` (imm15.py):
  1. `doc = CycleCountRepo.get(name)`; nếu `None` → `raise ServiceError(ErrorCode.NOT_FOUND, ...)` (in-handler **HTTP-200 + Error envelope** qua `_handle`, KHÔNG raise→4xx — DONE-gate spec-contract).
  2. `data = doc.as_dict()` + enrich display-name header: `warehouse_name` (AC Warehouse.warehouse_name), `counted_by_name` / `verified_by_name` (User.full_name).
  3. Enrich mỗi item line (child **`IMM Cycle Count Item`** — xem ⚠️ dưới): `part_name` (AC Spare Part.part_name). Item đã có sẵn `system_qty` (snapshot lúc create), `counted_qty`, `variance_qty`, `variance_pct`, `variance_value`, `capa_required`, `root_cause`, `notes`.
  4. `data["allowed_transitions"] = _cycle_allowed_transitions(doc.status)` (Self-Correct vòng 11: chữ ký THẬT 1-arg `status`, KHÔNG `(doc, user)` — hàm đọc session user qua `rbac.can` bên trong).

**Response:**
```json
{
  "success": true,
  "data": {
    "name": "CYC-2026-00012",
    "warehouse": "WH-01",
    "warehouse_name": "Kho trung tâm",
    "count_date": "2026-07-01",
    "count_type": "ABC_A_Monthly",
    "status": "Reviewed",
    "counted_by": "storekeeper@hospital.vn",
    "counted_by_name": "Nguyễn Văn A",
    "verified_by": null,
    "verified_by_name": "",
    "variance_count": 1,
    "variance_value": 650000,
    "posted_movement_ref": null,
    "notes": "",
    "docstatus": 0,
    "items": [
      {"spare_part": "AC-SP-2024-0001", "part_name": "Bóng đèn CT", "system_qty": 6, "counted_qty": 4, "variance_qty": -2, "variance_pct": 33.3, "variance_value": -650000, "capa_required": 1, "root_cause": "Damage", "notes": ""}
    ],
    "allowed_transitions": ["Recount", "Post"]
  }
}
```

**`allowed_transitions` — SSoT gating (ADR-IMM-15-06 + ADR-IMM-15-08, xem 02 §IV.6 + 04 §VI.2.1):**

> **Self-Correct vòng 11 (doc↔code drift):** bảng cũ ghi value = tên **next-state** (`["Reviewed"]`/`["Posted"]`). Code THẬT (`_cycle_allowed_transitions`) + FE (`CycleCountAction = 'Submit' | 'Post' | 'Recount'`) dùng **token hành động ngữ nghĩa** `Submit`/`Post`/`Recount`, KHÔNG phải next-state. Bảng dưới đã sửa cho khớp.

`_CYCLE_VALID_TRANSITIONS: dict[str, list[str]]` (keyed by `status`, value = **token hành động**; token→status đích + capability xem 04 §VI.2.1):

| `status` hiện tại | Tokens (thứ tự) | Cap | CTA phía FE → endpoint |
|---|---|---|---|
| `Planned` | `["Submit"]` | `inventory.write` | "Hoàn tất kiểm kê" → `submit_cycle_count` (→ Reviewed) |
| `Counting` | `["Submit"]` | `inventory.write` | "Hoàn tất kiểm kê" → `submit_cycle_count` (→ Reviewed) |
| `Reviewed` | `["Recount", "Post"]` (**cap-gated**) | `inventory.submit` | "Sửa đếm lại" → `recount_cycle_count` (→ Counting) · "Post — Ghi điều chỉnh tồn" → `post_cycle_count` (→ Posted) |
| `Posted` | `[]` (terminal) | — | — |

- **Capability filter**: `Recount` + `Post` chỉ có mặt khi user có cap `inventory.submit` (`_CAP_APPROVE`). User chỉ có `inventory.write` (`_CAP_OPERATE`) → từ `Reviewed` nhận `[]` (không thấy cả Sửa-đếm-lại lẫn Post). Ràng buộc **enforce lần 2** trong service (`recount_cycle_count` / `post_cycle_count` gọi `_require_any_role` → in-handler cap-403 HTTP-200 Error envelope nếu FE bị bypass).
- **Recount đặt TRƯỚC Post** trong list (thứ tự render nút).
- Trạng thái `Counting` reachable qua **Recount** (Reviewed→Counting) — trước vòng 11 chỉ đạt được từ desk. Cạnh `Planned→Counting` ("Bắt đầu đếm" trong workflow json) KHÔNG surface CTA (dual-track collapse — service gộp Planned→Reviewed); khai báo `_CYCLE_EXCEPTION_EDGES` để INVARIANT không báo drift (04 §VI.2.1).

**⚠️ Data note (Cần khảo sát / BE cleanup — KHÔNG tự sửa ở task này):** tồn tại **2** child DocType — `IMM Cycle Count Item` (**LIVE**, được parent `IMM Stock Cycle Count.items` tham chiếu qua `options`) và `IMM Stock Cycle Count Item` (**orphan**, field khác: có `warehouse`/`batch_no`, thiếu `capa_ref`/`notes`; `root_cause` là Data thay vì Select). `get_cycle_count` PHẢI đọc child **LIVE = `IMM Cycle Count Item`**. Orphan nên được BE dọn trong task riêng.

---

### 3.6b `submit_cycle_count` ↔ FE `submitCycleCount` (reconciliation)

FE nhập số đếm rồi gọi **`submit_cycle_count`** (`api/imm15.ts::submitCycleCount(count_name, counted_items[])`), KHÔNG có endpoint `save_counted_qty` (tên cũ trong 06 §store draft là stale — dùng `submit_cycle_count`). Payload `counted_items: [{spare_part, counted_qty, root_cause?}]` → BE tính variance per-line, set `status=Reviewed`, trả `{name, workflow_state:"Reviewed", variance_count}`. Xem §3.7b.

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
- **Audit (vòng 12, CR-WF-15-AUDIT):** ghi ĐÚNG **1** `IMM Audit Trail` `event_type="cycle_count_posted"`, `ref_doctype=CycleCountRepo.DOCTYPE`, `ref_name=<name>`, `actor=verified_by`, `from_status="Reviewed"`, `to_status="Posted"`. `cycle_count_posted` PHẢI ∈ Select options (ADR-IMM-15-09 — trước vòng 12 slug ∉ Select ⇒ ValidationError bị nuốt ⇒ **0 dòng** persist). Audit non-blocking best-effort; fail → `frappe.log_error` (KHÔNG bare pass).

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

### 3.7c `recount_cycle_count` (Reviewed → Counting, "Sửa đếm lại") — **NEW (vòng 11, CR-WF-15-CC)**

> Surface cạnh workflow `Reviewed→Counting` (đã có sẵn trong `imm_15_cycle_count_workflow.json`, action "Sửa đếm lại") thành **CTA server-driven** để Inventory Manager / Super Admin gửi phiếu đã rà soát VỀ đếm lại (khi phát hiện số đếm cần sửa trước khi Post). Trước vòng 11 cạnh này bị **ẩn câm** — INVARIANT `TestCycleCountAllowedTransitions` RED (xem 07). GATE-8/LL-FE-51: client KHÔNG hardcode `status==='Reviewed'`.

```
POST /api/method/assetcore.api.imm15.recount_cycle_count
```

**BE contract:**
- `api/imm15.py`:
  ```python
  @frappe.whitelist(methods=["POST"])
  def recount_cycle_count(count_name: str = "", name: str = "", reason: str = "") -> dict:
      return _handle(svc.recount_cycle_count, count_name or name, reason)
  ```
  Bare `@whitelist` (KHÔNG `allow_guest`) — dispatcher chặn guest TRƯỚC handler. Mirror alias `count_name or name` như `submit_cycle_count`.
- `services/imm15.py`: `def recount_cycle_count(count_name: str, reason: str = "") -> dict` — xem 04 §cycle_count_service (skeleton) + §VI.2.1.

**Request body:**
```json
{ "count_name": "CYC-2026-00012", "reason": "Lệch ca A/B — đếm lại kệ 3" }
```

**Response (HTTP-200):**
```json
{ "success": true, "data": { "name": "CYC-2026-00012", "workflow_state": "Counting" } }
```

**Errors (parity submit/post — in-handler ⇒ HTTP-200 + Error envelope, KHÔNG raise→4xx):**
```json
{"success": false, "error": "IMM15_RECOUNT_REASON_REQUIRED: Phải nhập lý do gửi đếm lại", "code": "VALIDATION"}
{"success": false, "error": "Không thể gửi đếm lại ở trạng thái: Posted", "code": "BAD_STATE"}
{"success": false, "error": "Không có quyền gửi phiếu về đếm lại", "code": "FORBIDDEN"}
```

| Case | Điều kiện | Bucket HTTP | Cách trả |
|---|---|---|---|
| Guest / no-token | chưa đăng nhập | **401** | **dispatcher** (Frappe re-auth — HTTP status THẬT, KHÔNG envelope) |
| Thiếu cap `inventory.submit` | user login nhưng không có cap | **403** FORBIDDEN | **in-handler** cap-403 → HTTP-200 Error envelope (`_require_any_role`) |
| `reason` rỗng/whitespace | `reason.strip()==""` | **422** VALIDATION | in-handler `IMM15_RECOUNT_REASON_REQUIRED`, HTTP-200 envelope |
| `status ≠ Reviewed` | ví dụ Planned/Counting/Posted | **409** BAD_STATE | in-handler, HTTP-200 envelope |

> **2 loại 403/401 (DONE-gate LL-BE-42..49):** guest/no-token = **dispatcher-401** (không tới handler, HTTP status thật). User đã login nhưng thiếu `inventory.submit` = **in-handler cap-403** (HTTP-200, Error envelope code=`FORBIDDEN`). KHÔNG dùng `raise`→HTTP-4xx cho lỗi nghiệp vụ.

**Cap:** `inventory.submit` (`_CAP_APPROVE`) — send-back là hành vi Manager-level (đối xứng Post; cùng role-set workflow {Inventory Manager, AssetCore Super Admin, System Manager}).

**Audit:** đúng **1** record `IMM Audit Trail` `from_status="Reviewed"`, `to_status="Counting"`, `event_type="State Change"` (∈ Select — Self-Correct: KHÔNG dùng value ngoài Select như `cycle_count_posted`), `change_summary` chứa `reason`. BR-15-10 "mọi transition → audit". Xem 04 §cycle_count_service (`_cycle_audit`).

---

### 3.8 `generate_spare_forecast`

```
POST /api/method/assetcore.api.imm15.generate_spare_forecast
```

**Request body:**
```json
{
  "horizon_months": 3,
  "forecast_period": "2026-Q3",
  "method": "Moving_Avg"
}
```

| Param | Type | Default | Note |
|---|---|---|---|
| `horizon_months` | Int | 3 | Tầm dự báo. `lookback_months = max(horizon×4, 12)` chỉ ảnh hưởng `forecast_qty`/`reorder_point`/`safety_stock`. KHÔNG ảnh hưởng `historical_consumption_12m` (VR-15-15). |
| `forecast_period` | Data | (auto) | VD "2026-Q3"; auto-suy nếu rỗng |
| `method` | Select | Moving_Avg | Moving_Avg/PM_Driven/Failure_Rate/Manual (VR-15-12) |

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

> **Data-contract (VR-15-15):** mỗi `IMM Spare Forecast Item.historical_consumption_12m` LUÔN = tổng qty Issue (docstatus=1) trong CHÍNH XÁC 12 tháng trailing, độc lập `horizon_months`. KHÔNG đổi schema/label DB ("Tiêu thụ 12 tháng", read_only=1). KHÔNG leak nhãn/code thô ra response.

> **Tồn khả dụng (BR-15-17 / VR-15-17, vòng 23):** `IMM Spare Forecast Item.current_qty` = `Σ (qty_on_hand − COALESCE(reserved_qty,0))` toàn kho của part (`_sum_part_stock`, 1 aggregate — no N+1), KHÔNG còn `Σ qty_on_hand` vật lý. `recommended_action='Reorder'` khi `current_qty < reorder_point` → kích cho part **giữ-chỗ-hết** (available < reorder_point) mà on-hand ≥ reorder_point trước đây bị bỏ sót. `forecast_qty`/`safety_stock`/`reorder_point`/`historical_consumption_12m` **BẤT BIẾN**.

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

> **SoT đồng nhất (VR-15-17, vòng 23):** `low_stock_alerts` (card) = `_count_low_stock()` =
> `count_low_stock_bins()` = `len(get_low_stock_alerts().alerts)` (drill, cùng predicate
> `LOW_STOCK_COND`). **KHÔNG divergence card-vs-drill** — 1 con số, 1 SoT. Predicate so theo
> tồn **khả dụng** `(qty_on_hand − reserved_qty) < effective_min` → bin reserved-full được đếm.

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

> **Predicate (BR-15-17 / VR-15-17, vòng 23):** drill dùng CHUNG `LOW_STOCK_COND` với card KPI
> → bin có `qty_on_hand` ≥ định mức nhưng **giữ chỗ hết** (`qty_on_hand − reserved_qty < effective_min`)
> vẫn xuất hiện. `min_stock_level` trả về = effective_min (per-bin override fallback part-min).
> Response giữ `qty_on_hand` (tồn vật lý, để FE hiển thị) — phán định low đã so theo tồn khả dụng.
> FE alert/badge: KHÔNG leak EN — nhãn VI ("Tồn khả dụng dưới định mức").

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
| Không đủ quyền | `FORBIDDEN` | "Chỉ Inventory Manager mới được duyệt" |
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
| `imm15_low_stock_alert` | `{"spare_part": "...", "warehouse": "...", "qty_on_hand": 0.5}` | Scheduler | Inventory User / Inventory Manager dashboard |
| `imm15_critical_breach` | `{"watchlist": "...", "asset": "...", "spare_part": "...", "qty": 1}` | `check_critical_spare_breach()` | Inventory Manager + Compliance Manager urgent inbox |
| `imm15_cycle_count_posted` | `{"name": "CYC-2026-00012", "adjustment_ref": "...", "capa_count": 1}` | `post_cycle_count()` | Compliance Manager dashboard |
| `imm15_forecast_approved` | `{"name": "SFC-2026-00008", "reorder_count": 12}` | `approve_forecast()` | Procurement dashboard (IMM-03 trigger) |

---

## 8. Implementation Notes

1. **RULE-F03:** Mọi movement phải sinh `AC Stock Movement` submitted. KHÔNG cập nhật `AC Spare Part Stock` trực tiếp.
2. **RULE-F04:** Allocation/CycleCount chỉ LINK tới `AC Stock Movement` qua `stock_movement_ref`. Không ghi stock trực tiếp.
3. **Emergency path:** API `issue_allocation` phải kiểm tra VR-15-10 (double-approval) trước khi bypass VR-15-03.
4. **Concurrency:** Issue allocation song song trên cùng spare_part → dùng `FOR UPDATE` lock trong `vr_03_stock_sufficient()`.
5. **Backward compat:** Mở rộng `reference_type` của `AC Stock Movement` qua Property Setter — KHÔNG sửa core JSON.
6. **Gated Spare Batch:** `check_expiring_batches()` gate bằng `frappe.db.table_exists("IMM Spare Batch")` — truyền **DocType name**, KHÔNG prefix `tab` (Frappe tự thêm; `"tabIMM Spare Batch"` → tìm `tabtabIMM Spare Batch` → luôn False → job chết âm thầm). Khi bảng tồn tại: chọn batch trong cửa sổ `[today, today+30]` có `qty_on_hand>0`, dùng field `batch_no` (Data, ≠ batch_code). Xem BR-15-11 / VR-15-16 / 04 §VII.
7. **ABC quarterly:** Khai trong `hooks.py` dưới `"cron"` key — Frappe v15 không hỗ trợ key `"quarterly"`.
