# IMM-17 — API Specification (Skeleton)

| Mục | Giá trị |
|---|---|
| Module | IMM-17 — Phân tích dự đoán |
| Trạng thái | Skeleton — endpoint name + verb + 1 dòng. Body/response shape chốt khi BE scaffold. |
| Cập nhật | 2026-05-10 |

> Tuân thủ R-02 (3-tier): API layer chỉ whitelist + validate + delegate. File: `assetcore/api/imm17.py` (chưa tạo).
> Envelope chuẩn theo CONVENTIONS.md §3 *(refer skill `assetcore-be-module`)*. ErrorCode dùng hằng số trong `services/shared/constants.py` — không bịa code mới.

---

## 1. Endpoint catalog

| Method | Endpoint | Mô tả 1 dòng | Roles |
|---|---|---|---|
| POST | `/api/method/assetcore.api.imm17.run_for_asset` | On-demand inference cho 1 asset (debug/manual) | IMM System Admin, IMM HTM Engineer |
| GET | `/api/method/assetcore.api.imm17.list_insights` | List `AC Predictive Insight` với filter (asset, severity, date range) | Operations Manager, HTM Engineer, QA, Auditor |
| GET | `/api/method/assetcore.api.imm17.get_insight` | Detail 1 insight + contributing factors | (idem) |
| POST | `/api/method/assetcore.api.imm17.acknowledge_insight` | UC-17-03 — actor ack + decision (open_replacement / open_pm / dismiss) + reason | Operations Manager, HTM Engineer |
| POST | `/api/method/assetcore.api.imm17.whatif_pm_cycle` | UC-17-05 — what-if simulator (read-only) | HTM Engineer |
| GET | `/api/method/assetcore.api.imm17.cockpit_summary` | Top-N rủi ro + slice theo khoa/loại | Operations Manager, HTM Engineer |
| GET | `/api/method/assetcore.api.imm17.list_models` | List `IMM Predictive Model` versions | System Admin, Data Scientist |
| POST | `/api/method/assetcore.api.imm17.register_model` | Đăng ký model mới (artifact_ref + metadata) | Data Scientist + System Admin |
| POST | `/api/method/assetcore.api.imm17.activate_model` | Activate version cụ thể | System Admin |
| GET | `/api/method/assetcore.api.imm17.run_logs` | Lịch sử chạy pipeline | System Admin, QA, Auditor |

> Body / response schema *(Thiết kế trong sprint Wave 3 dùng skill `assetcore-be-module`)*.

---

## 2. Envelope chuẩn (refer CONVENTIONS.md §3)

Tất cả endpoint trả về JSON envelope chung của AssetCore — KHÔNG định nghĩa lại tại đây. Format thực tế xem trong `assetcore/utils/response.py`.

```json
{
  "ok": true,
  "data": { ... },
  "error": null,
  "meta": { "request_id": "...", "ts": "..." }
}
```

Khi lỗi:
```json
{
  "ok": false,
  "data": null,
  "error": { "code": "<ErrorCode>", "message": "...", "details": {} }
}
```

---

## 3. ErrorCode dự kiến

> Theo `ErrorCode` chuẩn (refer `assetcore/services/shared/constants.py`). Các code dưới đây là **dự kiến** — chốt khi BE scaffold:

- `IMM17_MODEL_NOT_FOUND` — version không tồn tại
- `IMM17_MODEL_NOT_ACTIVE` — chưa activate
- `IMM17_INSUFFICIENT_HISTORY` — asset không đủ dữ liệu để inference
- `IMM17_INSIGHT_ALREADY_ACK` — đã acknowledge
- `IMM17_DATA_QUALITY_GATE_FAIL` — pipeline bị stop do data quality kém
- `IMM17_INVALID_ACK_DECISION` — decision không thuộc tập cho phép

> KHÔNG hardcode trong client. Frontend đọc qua `ErrorCode` enum chia sẻ.

---

## 4. Webhook / Event (outbound — Wave 3 cuối)

Không có webhook ở Wave 3 đầu. Khi tích hợp vendor ML qua INT-13:

| Event | Payload | Direction |
|---|---|---|
| `predictive_dataset_export.requested` | dataset snapshot ref | Outbound → vendor |
| `predictive_inference.received` | per-asset score | Inbound ← vendor |

> Chi tiết xem `ba/Phase_07_Integration_API_Design/01_Integration_Landscape_Map/Integration_Landscape_Map.md` §INT-13.

---

## 5. Rate limit / Performance

- `run_for_asset`: rate-limit 1 request / asset / phút (tránh abuse).
- `list_insights`: pagination mặc định 50 items/page (CONVENTIONS pagination utility).
- `cockpit_summary`: cache 5 phút (server-side) — *(quyết định khi profiling thực tế)*.

---

## 6. Auth & CSRF

- Tất cả endpoint require login (Frappe session) + role match.
- Không expose anonymous endpoint.
- Vendor ML service (Wave 3 cuối): dùng API key dedicated trong `frappe.conf`, KHÔNG hardcode (R-09).
