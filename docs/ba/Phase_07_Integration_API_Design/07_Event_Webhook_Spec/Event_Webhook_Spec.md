> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# EVENT / WEBHOOK SPEC — ASSETCORE

**Phiên bản:** 1.0
**Owner:** SA Lead

---

## 1. Mục tiêu
Định nghĩa cơ chế đẩy event ra ngoài (outbound webhook) + nhận event vào trong (inbound webhook), gắn với Lifecycle Event Engine (outbox pattern).

## 2. Outbound — AssetCore push event

### 2.1 Source
Mọi outbound webhook xuất phát từ `AC Lifecycle Event` sau khi insert. Dispatcher pick lên và đẩy.

### 2.2 Subscribers
DocType `AC Webhook Subscription`:
| Field | Mô tả |
|-------|-------|
| name | – |
| partner | – |
| event_types | Table (filter event_type) |
| filter_expression | optional |
| target_url | – |
| signing_secret | encrypted |
| auth_type | HMAC / Bearer |
| retry_policy | (default 3 lần) |
| state | active / paused |

### 2.3 Delivery Flow

```
LE inserted ──► Dispatcher picks ──► Build payload
                                           │
                                           ▼
                              Sign HMAC + timestamp
                                           │
                                           ▼
                              POST target_url (timeout 10s)
                                           │
                                           ▼
                       2xx ─► mark delivered + log
                       non-2xx / timeout ─► retry queue (30s, 5m, 30m)
                                           │
                                           ▼
                          After 3 fails → dead-letter + alert IT
```

### 2.4 Payload format

```json
{
  "event_id": "LCE-2026-00001234",
  "event_type": "wo_completed",
  "occurred_at": "2026-05-12T10:34:00+07:00",
  "subject_ref": {"type": "Device", "id": "MA-2026-0001"},
  "source_ref": {"type": "WorkOrder", "id": "WO-2026-000123"},
  "payload": {
    "wo_type": "PM",
    "completed_by": "user_id",
    "validation_result": "Pass"
  },
  "audit_class": "QMS-critical",
  "version": 1,
  "signature": "sha256=...",
  "timestamp": "2026-05-12T10:34:01+07:00"
}
```

### 2.5 Headers
- `X-AssetCore-Signature: sha256=<hex>`
- `X-AssetCore-Timestamp: <ISO 8601>`
- `X-AssetCore-Event-Id: <event_id>`
- `Content-Type: application/json`

### 2.6 Idempotency
- Subscriber nên dedupe theo `event_id`.
- Nếu re-deliver, payload + signature giữ nguyên.

## 3. Inbound — Partner push event into AssetCore

### 3.1 Endpoint
- `POST /api/v1/webhooks/inbound`
- AuthN: HMAC từ partner secret + mTLS optional.
- Validation: timestamp lệch ≤ 5 phút.

### 3.2 Supported event types Wave 1
- (Wave 1 chỉ ERPNext core trong cùng site → không cần inbound webhook)
- Wave 1.5: vendor recall notification (manual + email-based; không yêu cầu webhook).
- Wave 2: HIS/LIS event đẩy ServiceRequest, Patient context.

### 3.3 Routing

```
Inbound webhook ──► Validate signature ──► Identify event_type
                                                │
                                                ▼
                                        Route to handler
                                                │
                                ┌───────────────┴────────────────┐
                                ▼                                ▼
                      Domain handler                   Audit log only
                      (vd HIS push ServiceRequest      (vendor info)
                       → tạo WO Cal)
```

### 3.4 Failure handling
- Partner nhận 2xx ack chỉ khi lưu vào outbox AssetCore.
- Nếu xử lý sau lỗi → publish `LE-71 integration_inbound_received` với status=`error`.

## 4. Event Type Catalog (cho integration outbound)

Tham chiếu Phase_01/06_Event_List. Mọi LE QMS-critical có thể subscribed.

Sample subset Wave 1:
- LE-03 installed
- LE-04 commissioned
- LE-05 license_registered
- LE-06 released_for_use
- LE-07 pm_completed
- LE-08 calibrated
- LE-09 failure_reported
- LE-10 repaired
- LE-12 recalled
- LE-15 retired
- LE-16 disposed
- LE-22 capa_opened
- LE-25 capa_closed
- LE-49 wo_breach_sla

## 5. Performance & SLA
- Dispatcher latency p95 ≤ 5s từ LE insert đến send.
- Webhook timeout: 10s.
- Retry interval: 30s, 5m, 30m.
- Dead-letter queue depth alert ≥ 50.

## 6. Outbox depth monitoring
- Background metric: `outbox.pending_count`, `outbox.failed_count`.
- Dashboard SOC.
- Alert IT khi backlog > N (tùy hạ tầng).

## 7. Replay
- Admin endpoint `POST /admin/webhooks/replay` với event_id list.
- Audit replay.
- Subscriber expected idempotent.

## 8. Tiêu chí nghiệm thu Webhook Spec
- Outbound subscription DocType + dispatcher hoạt động.
- HMAC sign/verify test pass.
- Retry + dead-letter test pass.
- Inbound webhook (Wave 2 ready) framework sẵn.
- Replay endpoint hoạt động.
- Outbox depth monitoring.
