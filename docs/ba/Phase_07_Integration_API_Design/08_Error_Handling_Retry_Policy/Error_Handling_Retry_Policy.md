> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# ERROR HANDLING & RETRY POLICY — ASSETCORE

**Phiên bản:** 1.0
**Owner:** SA Lead + IT Lead

---

## 1. Phân loại lỗi

### 1.1 Theo nguồn
- **Internal**: validation, business rule.
- **Integration**: timeout, 5xx partner, signature fail, schema invalid.
- **Infrastructure**: DB down, queue down, file storage down.

### 1.2 Theo mức
- **User-facing**: lỗi nghiệp vụ → trả message rõ + hướng dẫn.
- **Recoverable**: lỗi tạm thời → retry tự động.
- **Non-recoverable**: lỗi nghiêm trọng → log + alert + dead-letter.

## 2. Mã lỗi chuẩn

| Code | HTTP | Ý nghĩa |
|------|------|---------|
| ASSETCORE_VALIDATION_FAILED | 400 | Field validation fail |
| ASSETCORE_PERMISSION_DENIED | 403 | Không đủ quyền |
| ASSETCORE_NOT_FOUND | 404 | Không tìm thấy |
| ASSETCORE_CONFLICT | 409 | State conflict / version mismatch |
| ASSETCORE_RATE_LIMIT | 429 | Quá giới hạn |
| ASSETCORE_INTERNAL_ERROR | 500 | Lỗi hệ thống |
| ASSETCORE_INTEGRATION_TIMEOUT | 504 | Partner timeout |
| ASSETCORE_INTEGRATION_SIGNATURE_INVALID | 401 | Webhook chữ ký sai |
| ASSETCORE_INTEGRATION_SCHEMA_INVALID | 422 | Schema partner sai |

Format response:
```json
{
  "error": {
    "code": "ASSETCORE_VALIDATION_FAILED",
    "message": "<readable>",
    "fields": [{"field": "asset_code", "rule": "regex", "msg": "..."}],
    "request_id": "..."
  }
}
```

## 3. Retry Policy

### 3.1 Outbound webhook
- Initial timeout 10s.
- Retry: 30s → 5m → 30m (3 lần).
- Sau 3 lần fail → dead-letter queue.

### 3.2 Background job
- Frappe RQ retry: 3 lần với exponential.
- Critical job (PM scheduler, SLA monitor): retry 5 lần + alert.

### 3.3 Integration outbound (synchronous call)
- Timeout 10s + 1 retry tức thời nếu 5xx.
- Nếu 4xx (client error) → không retry, log + escalate.
- Idempotency key (header `Idempotency-Key`) bắt buộc cho POST.

### 3.4 Inbound webhook
- AssetCore lưu vào outbox trước → ack 2xx.
- Xử lý sau theo background; lỗi xử lý không yêu cầu partner retry.
- Partner replay nếu cần.

### 3.5 DB transaction
- Retry deadlock 3 lần.
- Long transaction cảnh báo khi > 30s.

## 4. Dead-letter Queue (DLQ)

### 4.1 Cho webhook
- DocType `AC Webhook Dead Letter`:
  - subscription, event_id, payload, last_error, attempt_count, last_attempt_at, status.
- Admin có thể replay từ DLQ sau khi sửa lỗi partner.

### 4.2 Cho job
- Frappe failed jobs queue.
- Admin retry từ UI System Admin.

## 5. User-facing error UX

- Form validation: highlight field + message tiếng Việt.
- Workflow transition fail: dialog rõ lý do + gợi ý.
- Critical action fail: ghi vào "Action History" của user để dễ quay lại.

## 6. Logging chuẩn

- Error log gắn `request_id`, `user_id`, `subject_doctype`, `subject_name`.
- Không log password / token / signature.
- Sentry / ELK ingestion.

## 7. Circuit breaker (cho integration)

- Sau N consecutive fail liên tiếp → mở circuit (tạm dừng gọi).
- Half-open sau cooldown 5 phút.
- Nếu tiếp tục fail → đóng circuit + alert.

## 8. Alert
- DLQ > 10 → email IT.
- Failed background job critical > 5/giờ → alert.
- Circuit open > 30 phút → alert.

## 9. Recovery procedures

- DLQ replay tool.
- Reconcile MA ↔ Asset (cron daily) — phát hiện lệch field.
- Restore from backup khi cần.

## 10. Tiêu chí nghiệm thu
- Mã lỗi chuẩn áp dụng toàn API.
- Retry + DLQ test pass cho webhook.
- Background job retry tested.
- Circuit breaker tested.
- Alert pipeline hoạt động.
- Recovery runbook documented.
