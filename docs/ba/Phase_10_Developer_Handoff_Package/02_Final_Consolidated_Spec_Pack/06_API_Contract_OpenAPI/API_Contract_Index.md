> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# API CONTRACT INDEX — WAVE 1

**Tham chiếu:**
- OpenAPI 3.x: Phase_07/05.
- Auth Flow: Phase_07/06.
- Webhook: Phase_07/07.
- Error Handling: Phase_07/08.

---

## 1. Endpoint groups Wave 1

| Group | Path | Method |
|-------|------|--------|
| Asset | `/api/v1/assets` | GET, POST |
| Asset detail | `/api/v1/assets/{asset_code}` | GET |
| Asset timeline | `/api/v1/assets/{asset_code}/timeline` | GET |
| Work Order | `/api/v1/work-orders` | GET, POST |
| Work Order detail | `/api/v1/work-orders/{wo_id}` | GET |
| Work Order transition | `/api/v1/work-orders/{wo_id}:transition` | POST |
| Failure Report | `/api/v1/failure-reports` | POST |
| Document | `/api/v1/documents` | GET |
| Document detail | `/api/v1/documents/{doc_id}` | GET, POST |
| Webhooks inbound | `/api/v1/webhooks/inbound` | POST |
| Health | `/api/method/ping` | GET |
| Token | `/oauth2/token` | POST |

## 2. Auth scheme
- OAuth2 client_credentials.
- Scope theo Phase_07/05 §6.
- mTLS cho regulatory.
- Webhook outbound: HMAC.

## 3. Build artifacts cần giao
- `openapi.yaml` đầy đủ.
- Postman collection auto-generated.
- Mock server (Prism) cho early integration test.
- Sample payloads (Phase_07/03 + 04).

## 4. Versioning
- Path-based `/v1/`, `/v2/`.
- Deprecation ≥ 6 tháng.

## 5. Rate limit
- 60 req/min/client default.
- Header `X-RateLimit-*`.

## 6. Tiêu chí nghiệm thu
- OpenAPI lint pass.
- Mock server hoạt động.
- Postman test 100% endpoint.
- Webhook HMAC verify pass.
