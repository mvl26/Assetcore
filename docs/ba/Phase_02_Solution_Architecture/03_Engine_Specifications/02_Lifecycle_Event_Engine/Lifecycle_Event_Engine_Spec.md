> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# LIFECYCLE EVENT ENGINE — SPEC

**Phiên bản:** 1.0
**Owner:** SA Lead
**Wave:** 1 (mở rộng dần Wave 2/3)

---

## 1. Mục tiêu
- Là **single source of truth** cho mọi sự kiện business quan trọng trong hệ thống.
- Cho phép truy vết: ai, làm gì, khi nào, trên record nào, dựa trên evidence nào.
- Là kênh phát outbound cho Compliance, Dashboard, Audit.

## 2. Cốt lõi: DocType `AC Lifecycle Event`

| Field | Type | Bắt buộc | Mô tả |
|-------|------|---------|-------|
| name | Naming series `LCE-.YYYY.-.########` | – | – |
| event_type | Link AC Event Type | Có | "installed", "pm_completed"… |
| occurred_at | Datetime | Có | – |
| actor_user | Link User | Có | – |
| actor_role | Data | Có | – |
| subject_doctype | Data | Có | – |
| subject_name | Dynamic Link | Có | – |
| source_doctype | Data | Có | – |
| source_name | Dynamic Link | Có | – |
| payload | JSON | Có | – |
| evidence_refs | Table (file refs) | Tùy | – |
| audit_class | Select info/critical/QMS-critical | Có | – |
| wave_introduced | Data | Có | – |
| correlation_id | Data | Tùy | Truy vết cross-event |
| immutable | Check (default 1) | Có | Không cho update sau insert |

**Một event là immutable** — chỉnh sửa = phát event mới có `correction_of` link tới event cũ.

## 3. Event Catalog
Tham chiếu `Phase_01/06_Event_List/Event_List.md` (50+ event Wave 1.5).

DocType `AC Event Type` là master:
- name (snake_case)
- display_label (tiếng Việt)
- audit_class
- expected_payload_schema (JSON Schema)
- handlers_enabled (table) — danh sách handler cho event này

## 4. Producers

Mọi domain entity là producer. Quy ước:
- Không tự tạo `AC Lifecycle Event` bằng client script.
- Dùng helper `assetcore.lifecycle.publish(event_type, subject, source, payload, evidence)`.
- Helper validate payload theo JSON Schema từ `AC Event Type`.

## 5. Consumers

| Consumer | Hành động |
|----------|-----------|
| Compliance Engine | Phát hiện pattern → mở Compliance Case |
| Metric Engine | Tăng counter, snapshot |
| Notification | Gửi email/SMS theo rule |
| Outbound Webhook | Đẩy event QMS-critical sang Finance/Audit hệ thống ngoài |
| Risk Engine | Cập nhật risk score |

Consumer dùng pattern **outbox** — event được lưu vào DB trước, background worker pick lên dispatch.

## 6. Outbox / Dispatcher

```
Domain action ──► publish() ──► AC Lifecycle Event (DB)
                                          │
                                          │  (background)
                                          ▼
                      ┌───────── Dispatcher ─────────┐
                      │                              │
                      ▼                              ▼
            Internal handlers           Outbound webhooks
              (Compliance,                 (Finance, IS, etc.)
              Metric, Alerts)
```

- Dispatch retry: 3 lần exponential backoff.
- Dead-letter queue: `AC Lifecycle Event Dead Letter` cho event fail dispatch sau cùng.

## 7. Idempotency & Ordering
- Mỗi event có `correlation_id` (vd `WO-2026-000123:repaired`).
- Consumer phải idempotent (xử lý lại không gây double effect).
- Ordering: sequential trong cùng `subject_name`; cross-subject không bảo đảm strict order.

## 8. Retention & Immutability
- Retention: 10 năm.
- Lưu vào bảng có constraint `BEFORE UPDATE TRIGGER` chặn update.
- Storage: DB primary + cold archive sau 5 năm sang cold storage.

## 9. Truy vấn & Replay
- API `assetcore.lifecycle.timeline(asset_code, since, until, types)` — trả timeline đầy đủ.
- Replay endpoint `assetcore.lifecycle.replay(correlation_id)` — chỉ admin, ghi log mỗi lần replay.

## 10. Bảo mật
- View toàn bộ: AC Auditor + System Admin.
- View per asset/owner: phụ thuộc User Permission (qua `subject_name`).
- Không API delete; tất cả thử xóa trả 403.

## 11. Tiêu chí nghiệm thu Wave 1
- ≥ 27 event types Wave 1 hoạt động.
- Outbox dispatcher chịu được 1.000 event/phút.
- Retention 10 năm verified bằng test storage.
- 100% domain action quan trọng đều có lifecycle event tương ứng.
- Test idempotency pass.
