# 05 — API Specification (IMM-07 — Theo dõi hiệu suất)

| Mục | Giá trị |
|---|---|
| Module | IMM-07 — Theo dõi hiệu suất |
| Trạng thái | Skeleton — endpoint shape sẽ chốt sau khi BE scaffold (Wave 3) |
| Cập nhật | 2026-05-10 |

---

## 0. API Catalog

| # | Method | Path | Mô tả 1 dòng |
|---|---|---|---|
| 1 | POST | `/api/method/assetcore.api.imm07.build_snapshot` | Tổng hợp KPI snapshot cho 1 chu kỳ + scope |
| 2 | POST | `/api/method/assetcore.api.imm07.verify_snapshot` | Verify (4-mắt) và đóng kỳ snapshot |
| 3 | POST | `/api/method/assetcore.api.imm07.reopen_snapshot` | Mở lại snapshot đã verify (kèm lý do) |
| 4 | GET | `/api/method/assetcore.api.imm07.get_snapshot` | Lấy 1 snapshot + KPI values + event_ids |
| 5 | GET | `/api/method/assetcore.api.imm07.list_snapshots` | Liệt kê snapshot theo filter (period, scope, status) |
| 6 | GET | `/api/method/assetcore.api.imm07.get_kpi_timeseries` | Lấy timeseries 1 KPI cho 1 asset/scope |
| 7 | GET | `/api/method/assetcore.api.imm07.get_cockpit` | Dữ liệu tổng hợp cho performance cockpit |
| 8 | POST | `/api/method/assetcore.api.imm07.evaluate_rules` | Chạy thủ công rule engine cho snapshot |
| 9 | GET | `/api/method/assetcore.api.imm07.list_signals` | Liệt kê replacement signal theo filter |
| 10 | POST | `/api/method/assetcore.api.imm07.resolve_signal` | Đóng signal với resolution + lý do |
| 11 | POST | `/api/method/assetcore.api.imm07.dismiss_signal` | Bỏ qua signal (false positive) |
| 12 | POST | `/api/method/assetcore.api.imm07.export_report` | Xuất báo cáo định kỳ PDF (ký số) |

Request/response body chi tiết — *(Sprint Wave 3 — sau khi BE scaffold)*.

## 1. Quy ước chung

### 1.1. Response success (CONVENTIONS §3)

```json
{ "success": true, "data": { } }
```

### 1.2. Response error (CONVENTIONS §3)

```json
{ "success": false, "error": { "code": "<ERROR_CODE>", "message": "..." } }
```

### 1.3. Error code catalog

Theo `ErrorCode` chuẩn AssetCore — refer `assetcore/services/shared/constants.py`. Module IMM-07 sẽ dùng các code:
- Code chung: `VALIDATION_ERROR`, `NOT_FOUND`, `PERMISSION_DENIED`, `STATE_INVALID`.
- Code module: chốt khi BE scaffold (refer `services/shared/constants.py` ErrorCode enum).

### 1.4. Mapping FE ↔ BE

FE consume cùng enum trong `frontend/src/types/imm07.ts` *(tạo khi FE scaffold)*.

### 1.5. Type definitions

Schema TypeScript cho `KPISnapshot`, `KPIValue`, `ReplacementSignal` — *(Sprint Wave 3 — đồng bộ 2 đầu BE/FE)*.

## 2. Endpoint detail

Body request / response cho từng endpoint — *(Bổ sung sau khi BE scaffold; mỗi endpoint dùng template `99` của file template chuẩn)*.

## 3. List / Query endpoints

Endpoint #5, #9 dùng pagination chuẩn AssetCore: `?page=&page_size=&sort=&filters=`.

## 4. Webhook / Event

IMM-07 chỉ phát `AC Lifecycle Event` qua doc_events nội bộ, **không** expose webhook ngoài Wave 3. Nếu cần, Wave 4 mở.

## 5. Versioning

API version `v1` mặc định. Bump version khi breaking — refer 09_Release.md §II.5.

## 6. Rate limit

Endpoint `build_snapshot`, `evaluate_rules`, `export_report`: hạn chế 1 request đồng thời cho cùng `(scope, period)` (lock theo Frappe `frappe.cache().lock`).

## 7. Smoke test playbook

*(Soạn cùng file 07 §I.7 + 08 §I.6)*

---

## DoD — File 05 (IMM-07)

- [x] API catalog 12 endpoint (skeleton)
- [x] Envelope chuẩn
- [x] Reference ErrorCode constants
- [ ] *(Pending: request/response shape sau BE scaffold)*
