# IMM-07 — Đặc tả API

| Mục | Giá trị |
|---|---|
| Module | IMM-07 — Theo dõi hiệu suất |
| Trạng thái | Skeleton (endpoint shape sẽ chốt khi BE scaffold — Sprint Wave 3.1) |

## §0. Envelope chuẩn

Tuân thủ envelope chung của AssetCore (refer `CONVENTIONS.md §3`).

**Success:**
```json
{ "success": true, "data": { ... } }
```

**Error:**
```json
{ "success": false, "error": "Mô tả ngắn", "code": "ERROR_CODE_FROM_CONSTANTS" }
```

Mọi endpoint IMM-07 dùng `@frappe.whitelist()` và trả envelope chuẩn. ErrorCode lấy từ `assetcore/services/shared/constants.py` — KHÔNG hardcode literal trong api layer.

## §1. Catalog endpoint dự kiến

Endpoint name + verb + mô tả 1 dòng. Request/response shape *(Sprint Wave 3.1 — sau khi BE scaffold)*.

| # | Method | Path | Auth | Mô tả |
|---|---|---|---|---|
| 1 | GET | `/api/method/assetcore.api.imm07.get_performance_record` | Login | Lấy performance record của 1 asset trong khoảng thời gian |
| 2 | GET | `/api/method/assetcore.api.imm07.get_dashboard_summary` | Login | Tổng hợp KPI theo khoa/quý cho dashboard |
| 3 | POST | `/api/method/assetcore.api.imm07.trigger_aggregation` | KPI Owner | Chạy aggregation thủ công (recompute) |
| 4 | POST | `/api/method/assetcore.api.imm07.verify_data_quality_flag` | Data Steward | Xác minh / bỏ qua flag chất lượng |
| 5 | POST | `/api/method/assetcore.api.imm07.acknowledge_replacement_signal` | KPI Owner | PTP xác nhận tín hiệu thay thế |
| 6 | GET | `/api/method/assetcore.api.imm07.list_replacement_signals` | KPI Owner / IMM-13 | Liệt kê tín hiệu replacement đang Open |
| 7 | POST | `/api/method/assetcore.api.imm07.create_kpi_definition_version` | KPI Owner | Tạo version mới của KPI definition |
| 8 | GET | `/api/method/assetcore.api.imm07.get_kpi_history` | Login | Lấy lịch sử KPI của 1 asset (cho drill-down) |

*Path chính thức và payload contract chốt sau khi BE scaffold.*

## §2. ErrorCode

Module IMM-07 sử dụng các ErrorCode khai báo tại `assetcore/services/shared/constants.py`. Code cụ thể cho IMM-07 *(bổ sung khi BE scaffold — không bịa tại doc này)*.

Pattern ErrorCode tuân thủ CONVENTIONS §3:
- Domain-specific: `IMM07_*`
- Generic reuse: `VALIDATION_*`, `PERMISSION_*`, `NOT_FOUND`

## §3. Authentication & Permission

- Tất cả endpoint yêu cầu user login (Frappe session).
- Permission gate trong service layer (CONVENTIONS §5), không chỉ dựa DocPerm.
- Endpoint `trigger_aggregation` và `create_kpi_definition_version` yêu cầu role `IMM-07 KPI Owner`.
- Endpoint dashboard scope theo department permission của user.

## §4. Rate limit & idempotency

- `trigger_aggregation`: rate limit 1 request / 5 phút / user (chống spam recompute).
- `acknowledge_replacement_signal`: idempotent theo `signal_id`.

Chi tiết headers / token *(Sprint Wave 3.1)*.

## §5. Tham chiếu

- Envelope: `CONVENTIONS.md §3`
- ErrorCode source: `assetcore/services/shared/constants.py`
- Phase BA: `docs/ba/Phase_07_Integration_API_Design/`
