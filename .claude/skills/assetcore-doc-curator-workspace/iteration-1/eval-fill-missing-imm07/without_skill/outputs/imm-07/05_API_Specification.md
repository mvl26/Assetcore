# 05 — API Specification

| Mục | Giá trị |
|---|---|
| Module | IMM-07 — Theo dõi hiệu suất |
| Phạm vi | Per-module |
| Owner | BE Lead |
| Liên kết | 02 Analysis · 04 Backend · 06 Frontend |

> **Quy chuẩn**:
> - Envelope success: `{success: true, data: <payload>}`
> - Envelope error: `{success: false, error: "<msg VN>", code: "<ERROR_CODE>", fields?: {...}}`
> - HTTP status luôn 200 — phân biệt qua field `success`
> - DTO mirror 1-1 với FE TypeScript types ở `frontend/src/types/imm07.ts`

---

## §0. API Catalog

| # | Method | Path | Mục đích | Role required |
|---|---|---|---|---|
| 1 | GET  | `/api/method/assetcore.api.imm07.list_kpi_snapshots` | Liệt kê KPI snapshot có filter + paging | IMM07 User |
| 2 | GET  | `/api/method/assetcore.api.imm07.get_kpi_snapshot` | Chi tiết 1 snapshot | IMM07 User |
| 3 | GET  | `/api/method/assetcore.api.imm07.list_replacement_signals` | Danh sách signal | IMM07 User |
| 4 | POST | `/api/method/assetcore.api.imm07.acknowledge_signal` | Open → Acknowledged | IMM07 Manager |
| 5 | POST | `/api/method/assetcore.api.imm07.suppress_signal` | Open → Suppressed (false-positive) | IMM07 Manager |
| 6 | POST | `/api/method/assetcore.api.imm07.verify_chain` | Verify hash chain per asset | IMM07 User + Auditor |
| 7 | GET  | `/api/method/assetcore.api.imm07.get_threshold_config` | Lấy cấu hình ngưỡng theo asset class | IMM07 Manager |
| 8 | POST | `/api/method/assetcore.api.imm07.update_threshold_config` | Cập nhật ngưỡng | IMM07 Manager |

---

## §1. Cross-cutting

### 1.1. Authentication

- Frappe session cookie (FE) **hoặc** API key + secret (BI tool)
- Header `X-Frappe-CSRF-Token` cho POST từ FE

### 1.2. Response envelope

```json
// success
{ "success": true, "data": { ... } }

// error
{ "success": false, "error": "Không tìm thấy thiết bị", "code": "NOT_FOUND" }

// validation error có fields
{ "success": false, "error": "Giá trị không hợp lệ", "code": "VALIDATION", "fields": {"window_start": "phải nhỏ hơn window_end"} }
```

### 1.3. ErrorCode

| Code | Khi nào |
|---|---|
| `NOT_FOUND` | Snapshot/Signal/Config không tồn tại |
| `FORBIDDEN` | Không đủ role |
| `UNAUTHORIZED` | Chưa đăng nhập |
| `VALIDATION` | Field validation fail |
| `BUSINESS_RULE` | Vi phạm BR (vd KPI > 100%) |
| `BAD_STATE` | Acknowledge khi state ≠ Open |
| `DUPLICATE` | Snapshot trùng (asset, window) |
| `INVALID_PARAMS` | JSON malformed, missing field |
| `INTERNAL` | Compute fail / hash chain broken |

### 1.4. TypeScript types (mirror — `frontend/src/types/imm07.ts`)

```ts
export interface KpiSnapshot {
  name: string
  asset: string
  window_start: string  // ISO datetime
  window_end: string
  granularity: 'hourly' | 'daily' | 'monthly'
  availability: number  // 0..1
  utilization: number
  mtbf_hours: number
  mttr_hours: number
  repair_count: number
  incident_count: number
  planned_downtime_hours: number
  unplanned_downtime_hours: number
  data_quality: 'Ok' | 'Stale' | 'Empty' | 'Anomaly'
}

export interface ReplacementSignal {
  name: string
  asset: string
  triggering_snapshot: string
  state: 'Open' | 'Acknowledged' | 'Suppressed' | 'Closed'
  reason: string
  raised_at: string
  acknowledged_at?: string
  acknowledged_by?: string
}

export interface KpiThresholdConfig {
  name: string
  asset_class: string
  mtbf_hours_min: number
  min_age_years: number
  min_repair_count_12m: number
  cooldown_days: number
  enabled: boolean
}

export interface ListResult<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}
```

---

## §2. Endpoints

### EP-01 — `list_kpi_snapshots`

**Method**: GET
**Path**: `/api/method/assetcore.api.imm07.list_kpi_snapshots`

**Query params**:
| Tên | Type | Required | Mô tả |
|---|---|---|---|
| `filters` | JSON string | – | `{"site": "...", "asset": "...", "granularity": "daily", "date_range": [...]}` |
| `page` | int | – (default 1) | – |
| `page_size` | int | – (default 50, max 200) | – |

**Response 200 success**:
```json
{
  "success": true,
  "data": {
    "items": [{ "name": "KPI-2026-05-00001", "asset": "AST-001", "window_start": "2026-05-10T00:00:00", "availability": 0.97, "...": "..." }],
    "total": 1284,
    "page": 1,
    "page_size": 50
  }
}
```

**Errors**: `INVALID_PARAMS` (filters JSON malformed), `FORBIDDEN`.

---

### EP-02 — `get_kpi_snapshot`

**Method**: GET
**Params**: `name: str`

**Response data**: `KpiSnapshot` đầy đủ + thêm `prev_hash`, `hash`, `note`.

**Errors**: `NOT_FOUND`, `FORBIDDEN`.

---

### EP-03 — `list_replacement_signals`

**Method**: GET
**Query**: tương tự EP-01 — `filters` chấp nhận `state`, `asset`, `date_range`.

**Response data**: `ListResult<ReplacementSignal>`.

---

### EP-04 — `acknowledge_signal`

**Method**: POST
**Body** (JSON):
```json
{ "name": "RPLS-2026-00001", "note": "Đã chuyển kế hoạch thay thế Q3" }
```

**Response success**:
```json
{ "success": true, "data": { "name": "RPLS-2026-00001", "state": "Acknowledged", "acknowledged_at": "2026-05-10T08:30:00", "acknowledged_by": "user@hospital.vn" } }
```

**Errors**:
- `NOT_FOUND` — signal không tồn tại
- `BAD_STATE` — state hiện tại ≠ Open
- `FORBIDDEN` — không có role IMM07 Manager

---

### EP-05 — `suppress_signal`

**Method**: POST
**Body**: `{ "name": "...", "reason": "..." }` (`reason` bắt buộc).

**Errors**: `NOT_FOUND`, `BAD_STATE`, `VALIDATION` (reason rỗng), `FORBIDDEN`.

---

### EP-06 — `verify_chain`

**Method**: POST
**Body**: `{ "asset": "AST-001" }`

**Response data**:
```json
{ "valid": true, "checked_count": 245, "broken_at": null }
```
hoặc khi lỗi:
```json
{ "valid": false, "checked_count": 245, "broken_at": "KPI-2026-04-00123" }
```

---

### EP-07 — `get_threshold_config`

**Method**: GET
**Params**: `asset_class: str`

**Response data**: `KpiThresholdConfig`.

**Errors**: `NOT_FOUND` nếu chưa cấu hình asset class này → FE fallback config mặc định.

---

### EP-08 — `update_threshold_config`

**Method**: POST
**Body**:
```json
{
  "payload": {
    "name": "KPICFG-00001",
    "asset_class": "Imaging",
    "mtbf_hours_min": 2000,
    "min_age_years": 7,
    "min_repair_count_12m": 3,
    "cooldown_days": 30,
    "enabled": true
  }
}
```

**Errors**: `VALIDATION` (negative number), `FORBIDDEN`, `NOT_FOUND`.

**Audit**: emit `kpi_threshold_updated` Lifecycle Event với before/after diff.

---

## §3. Rate limiting

- `verify_chain`: max 10 req/min/user (heavy CPU)
- `update_threshold_config`: max 30 req/min/user
- Các GET: max 600 req/min/user (cockpit refresh 30s OK)

Khi vượt → `RATE_LIMITED`.

---

## §4. Pagination & Ordering

- `page` ≥ 1, `page_size` ≤ 200
- Default order: `window_start DESC` (snapshot), `raised_at DESC` (signal)
- FE truyền `order_by` qua filters: `{"order_by": "availability asc"}` (whitelist field).

---

## §5. Backwards compatibility

- v1 stable. Schema thêm field mới phải **non-breaking** — FE đọc field optional.
- Nếu drop/rename field → bump major version qua `assetcore.api.imm07_v2`.

---

## DoD — File 05

- [x] API Catalog liệt kê 8 endpoint
- [x] Envelope success/error rõ ràng
- [x] ErrorCode list khớp `services/shared/constants.py`
- [x] TypeScript types mirror BE (1-1)
- [x] Mỗi endpoint có method, params, response, errors
- [x] Rate limit declare
- [ ] Reviewed bởi BE Lead + FE Lead (mirror types)
