# 05 — API Specification

| Mục | Giá trị |
|---|---|
| Module | IMM-07 — Theo dõi hiệu suất |
| Phạm vi | Endpoint catalog + envelope chuẩn + error code |
| Owner | Tech Lead BE |
| Liên kết | [04 Backend](./04_Backend_Design.md) · [06 Frontend](./06_Frontend_Design.md) |

> Toàn bộ endpoint của IMM-07 tuân thủ envelope chuẩn AssetCore (`{success, data}` / `{success, error, code}`) theo `.claude/skills/CONVENTIONS.md` §3. Endpoint thật sẽ scaffold trong Sprint Wave 3.

---

## 0. API Catalog — bảng tổng hợp toàn bộ endpoint của module

| # | Method | Path | Function | Auth role | Mô tả |
|---|---|---|---|---|---|
| 1 | POST | `/api/method/assetcore.api.imm07.recompute_one` | `recompute_one(asset, date)` | Workshop Lead, Admin | Recompute snapshot 1 asset |
| 2 | GET | `/api/method/assetcore.api.imm07.get_snapshot` | `get_snapshot(asset, period_start, period_type)` | Trưởng phòng, WS Lead, KTV (own dept) | Trả snapshot đơn |
| 3 | GET | `/api/method/assetcore.api.imm07.list_snapshots` | `list_snapshots(filters)` | Trưởng phòng, WS Lead | Bảng snapshot có filter |
| 4 | GET | `/api/method/assetcore.api.imm07.drill_down` | `drill_down(asset, period_start, kpi_code)` | Trưởng phòng, WS Lead, KTV (own dept) | Record nguồn |
| 5 | GET | `/api/method/assetcore.api.imm07.cockpit_summary` | `cockpit_summary(scope)` | Trưởng phòng | KPI tổng + signal count |
| 6 | POST | `/api/method/assetcore.api.imm07.transition_signal` | `transition_signal(name, action, note)` | Trưởng phòng | Take/Plan/Close/MarkFP |
| 7 | GET | `/api/method/assetcore.api.imm07.list_signals` | `list_signals(filters)` | Trưởng phòng, WS Lead | Bảng signal |
| 8 | POST | `/api/method/assetcore.api.imm07.verify_chain` | `verify_chain(period_start, period_end)` | QMS Risk, Admin | Verify hash chain |
| 9 | POST | `/api/method/assetcore.api.imm07.upsert_kpi_definition` | `upsert_kpi_definition(payload)` | CNTT Admin | KPI definition CRUD |
| 10 | POST | `/api/method/assetcore.api.imm07.upsert_threshold` | `upsert_threshold(payload)` | WS Lead (maker), Trưởng phòng (checker) | Threshold workflow |

*(Tổng 10 endpoint — chi tiết spec mỗi endpoint sẽ thêm ở §99 sau khi BE scaffold.)*

## 1. Quy ước chung

Tham chiếu `CONVENTIONS.md` §3.

### 1.1. Response success — format chuẩn AssetCore

```json
{
  "success": true,
  "data": {
    "...": "..."
  }
}
```

### 1.2. Response error — format chuẩn (BẮT BUỘC)

```json
{
  "success": false,
  "error": "Thông báo tiếng Việt",
  "code": "IMM07_<ENUM>"
}
```

API layer wrap exception:

```python
# assetcore/api/imm07.py
@frappe.whitelist()
def drill_down(asset: str, period_start: str, kpi_code: str):
    try:
        svc = PerformanceService(...)
        data = svc.drill_down(asset, period_start, kpi_code)
        return {"success": True, "data": data}
    except PermissionError as e:
        return {"success": False, "error": str(e), "code": "IMM07_PERMISSION_DENIED"}
    except ValueError as e:
        return {"success": False, "error": str(e), "code": "IMM07_INVALID_INPUT"}
```

### 1.3. Error code catalog — actual values (BE)

| Code | Mô tả | HTTP semantic |
|---|---|---|
| `IMM07_JOB_ALREADY_RUNNING` | Cron job khác đang chạy | 409 |
| `IMM07_ASSET_RETIRED_MIDPERIOD` | Asset retire giữa chu kỳ — partial snapshot | 200 (with warning) |
| `IMM07_KPI_DEFINITION_LOCKED` | KPI definition đang dùng — không edit được | 409 |
| `IMM07_AUDIT_CHAIN_BROKEN` | Hash chain mismatch | 500 |
| `IMM07_PERMISSION_DENIED` | User không quyền xem cross-department | 403 |
| `IMM07_THRESHOLD_NOT_CONFIGURED` | Chưa có threshold cho asset_class | 200 (skip) |
| `IMM07_INVALID_INPUT` | Input không hợp lệ | 400 |
| `IMM07_SNAPSHOT_NOT_FOUND` | Snapshot không tồn tại | 404 |
| `IMM07_SIGNAL_INVALID_TRANSITION` | Transition không hợp lệ | 400 |

*(Cần entry tương ứng trong `assetcore/services/shared/constants.py:ErrorCode` — `*(Sprint Wave 3)*`.)*

### 1.4. Mapping FE ↔ BE error code (CRITICAL)

| BE code | FE message i18n key | UX |
|---|---|---|
| `IMM07_PERMISSION_DENIED` | `error.permission_denied` | Toast đỏ |
| `IMM07_AUDIT_CHAIN_BROKEN` | `error.audit_chain_broken` | Modal cảnh báo + báo QMS |
| `IMM07_THRESHOLD_NOT_CONFIGURED` | `info.threshold_missing` | Banner vàng cấu hình |
| `IMM07_SIGNAL_INVALID_TRANSITION` | `error.invalid_transition` | Toast đỏ + reload state |

### 1.5. Type definitions (BẮT BUỘC chuẩn hóa 2 đầu)

TypeScript (FE) tham chiếu `frontend/src/types/imm07.ts` *(Sprint Wave 3)*:

```ts
export interface PerformanceSnapshot {
  name: string;
  asset: string;
  metric_definition: string;
  period_start: string;  // ISO
  period_end: string;
  period_type: 'daily' | 'weekly' | 'monthly';
  value: number;
  quality: 'complete' | 'incomplete';
  current_hash: string;
}

export interface ReplacementSignal {
  name: string;
  asset: string;
  detected_at: string;
  severity: 'low' | 'medium' | 'high';
  state: 'Draft' | 'Open' | 'InReview' | 'ActionPlanned' | 'FalsePositive' | 'Closed';
  reasoning: string;
}
```

## 2. Endpoint

Spec chi tiết per endpoint — dùng template §99. Hiện tại skeleton; full khi scaffold.

## 3. List / Query endpoints

`list_snapshots`, `list_signals` hỗ trợ filter: `asset`, `department`, `period_start_from`, `period_start_to`, `severity` (signal), `quality` (snapshot), pagination `page`, `page_size`.

## 4. Webhook / Event (nếu có)

Không có webhook outbound. Publish lifecycle event nội bộ qua `frappe.publish_realtime` cho cockpit cập nhật real-time *(roadmap)*.

## 5. Versioning

Path versioning qua module — không break backward compat. Khi thay đổi shape, thêm `_v2` suffix.

## 6. Rate limit

Frappe default + thêm rule cho `recompute_one`: ≤ 10 req/phút/user (chống abuse compute).

## 7. Smoke test playbook

```bash
# 1. List snapshots gần đây
curl -X GET "$SITE/api/method/assetcore.api.imm07.list_snapshots?page_size=10" \
  -H "Authorization: token $TOKEN"

# 2. Drill-down
curl -X GET "$SITE/api/method/assetcore.api.imm07.drill_down?asset=AC-ASSET-0001&period_start=2026-05-09&kpi_code=AVAILABILITY"

# 3. Cockpit summary
curl -X GET "$SITE/api/method/assetcore.api.imm07.cockpit_summary?scope=site"
```

Expected: `{"success": true, "data": {...}}`.

## 99. Template per endpoint (copy + sửa)

### 1. `recompute_one` — Re-compute snapshot 1 asset

| Mục | Giá trị |
|---|---|
| Method | POST |
| Path | `/api/method/assetcore.api.imm07.recompute_one` |
| Auth | Role: Workshop Lead, Admin |
| Idempotent | No (sinh snapshot mới supersede) |

**Request:**
```json
{
  "asset": "AC-ASSET-0001",
  "date": "2026-05-09"
}
```

**Response success:**
```json
{
  "success": true,
  "data": {
    "snapshot_name": "IMM-07-PM-2026-05-0042",
    "kpi_count": 6,
    "quality": "complete"
  }
}
```

**Response error:**
```json
{ "success": false, "error": "Asset retired", "code": "IMM07_ASSET_RETIRED_MIDPERIOD" }
```

*(Spec đầy đủ cho 9 endpoint còn lại — `*(Sprint Wave 3 — sau khi BE scaffold)*`.)*
