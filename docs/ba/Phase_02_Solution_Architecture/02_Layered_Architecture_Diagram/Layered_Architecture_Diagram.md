> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# LAYERED ARCHITECTURE DIAGRAM — ASSETCORE

**Phiên bản:** 1.0
**Owner:** SA Lead

---

## 1. 7-layer model

AssetCore áp dụng phân tầng nghiêm ngặt, mỗi tầng có mục tiêu riêng và ranh giới rõ — domain logic không nằm chung với hạ tầng.

### 1.1 User / Channel Layer
- Web UI (Frappe Desk) cho admin/back-office.
- Mobile/Tablet UI custom (PWA hoặc Frappe Mobile) cho KTV, Vendor SE — quét QR, nhập kết quả PM/CM/Cal.
- Email notifications + in-app notifications + SMS (cho alert critical).
- Vendor portal (scoped access).
- Public API cho hệ thống đối tác (Wave 2+).

### 1.2 Workflow / Application Service Layer
- Frappe Workflow Engine — định nghĩa state machine + transitions cho mọi DocType submittable.
- Custom Application Services: PM Scheduler, Calibration Scheduler, Alert Dispatcher, Integration Bridge.
- Authorization service (RBAC + User Permission + ABAC nếu cần cho Vendor scope).
- E-signature service (orchestrate digital signing).
- Notification dispatcher (email/SMS/in-app/webhook).

### 1.3 Domain / Business Layer (lõi nghiệp vụ)
- 6 engine trung tâm: Asset Registry, Lifecycle Event, Unified WO, Document/QMS, Compliance/CAPA, Metric/Dashboard.
- Domain rules implement bằng Python module trong app `assetcore` — KHÔNG để rule rải rác client script.
- Mỗi engine có public API rõ (Frappe whitelist functions).
- Layer này test được độc lập (unit test).

### 1.4 Data / Document Layer
- ERPNext core DocTypes (Item, Asset, Supplier, Stock Entry, Purchase Receipt…).
- AC custom DocTypes (`AC Medical Asset`, `AC Work Order`, `AC Lifecycle Event`, `AC Document Record`…).
- File storage (Frappe File): structured cho LEGAL/IQOQPQ/CALCERT/QMS — bucket immutable.
- Search: Frappe global search + custom indexed fields.

### 1.5 Integration Layer
- REST API (OpenAPI 3.x) — outbound + inbound.
- Webhook outbound cho event quan trọng (Lifecycle Event QMS-critical).
- FHIR adapter (Device, Location, Practitioner, ServiceRequest, Observation).
- Bridge connectors: HIS/EMR/LIS/RIS/PACS/BHYT/Finance/IoT.
- AuthN: OAuth2 client_credentials, mTLS với cơ quan QLNN.

### 1.6 Analytics / Dashboard / Alert Layer
- Frappe Dashboard + custom Vue dashboard cho điều hành.
- Snapshot store (`AC Dashboard Snapshot`) lưu chỉ số tháng/quý.
- Drill-down link: mọi widget có liên kết về record nguồn.
- Alert engine: schedule + trigger + dispatch theo rule.
- Realtime push qua Frappe Socket.IO cho dashboard SOC.

### 1.7 QMS / Governance Layer
- Document control (Document Record + QMS Artifact 4-tier).
- CAPA + NC + Compliance Case.
- Risk Register + Change Control + Management Review.
- Audit trail toàn hệ thống (Lifecycle Event + Frappe Version + Login Log).
- Internal audit + external audit support (export evidence).

## 2. Sequence Diagram — ví dụ "Báo hỏng → Sửa chữa"

```
User           PWA Mobile        Workflow Service        Domain (WO Engine)        DB              Notification        Vendor SE
 │                │                    │                       │                    │                   │                   │
 │ Quét QR        │                    │                       │                    │                   │                   │
 │───────────────►│                    │                       │                    │                   │                   │
 │                │ POST /failure_rep  │                       │                    │                   │                   │
 │                │───────────────────►│                       │                    │                   │                   │
 │                │                    │ on_submit Failure Rep │                    │                   │                   │
 │                │                    │──────────────────────►│                    │                   │                   │
 │                │                    │                       │ create AC Work     │                   │                   │
 │                │                    │                       │ Order (CM)         │                   │                   │
 │                │                    │                       │───────────────────►│                   │                   │
 │                │                    │                       │ create LE          │                   │                   │
 │                │                    │                       │ failure_reported   │                   │                   │
 │                │                    │                       │───────────────────►│                   │                   │
 │                │                    │                       │ pick assignee     │                   │                   │
 │                │                    │                       │ (rule engine)      │                   │                   │
 │                │                    │                       │ start SLA timer    │                   │                   │
 │                │                    │                       │                    │                   │                   │
 │                │                    │                       │ notify             │                   │                   │
 │                │                    │                       │───────────────────────────────────────►│                   │
 │                │                    │                       │                    │                   │ email/in-app to   │
 │                │                    │                       │                    │                   │ Vendor SE         │
 │                │                    │                       │                    │                   │──────────────────►│
 │                │                    │                       │                    │                   │                   │
```

## 3. Component Diagram — Domain Layer

```
┌──────────────────────────────────────────────────────────────────────────┐
│                              DOMAIN LAYER                                │
│                                                                          │
│   ┌────────────────────┐                  ┌────────────────────────┐     │
│   │ Asset Registry     │ ◄──manages──────►│ Lifecycle Event Engine │     │
│   │                    │                  │                        │     │
│   │ - AC Medical Asset │                  │ - AC Lifecycle Event   │     │
│   │ - AC Device Model  │                  │ - Event handlers       │     │
│   │ - AC Asset Identifier ────publishes────►│ - Outbox pattern      │     │
│   │ - Location Hierarchy│                  └────────┬───────────────┘     │
│   └────────┬───────────┘                           │                     │
│            │                                        │                     │
│            ▼                                        ▼                     │
│   ┌────────────────────┐                  ┌────────────────────────┐     │
│   │ Unified WO Engine  │                  │ Document/QMS Engine    │     │
│   │                    │                  │                        │     │
│   │ - AC Work Order    │ ◄──evidence─────►│ - AC Document Record   │     │
│   │ - PM Plan / Cal    │                  │ - AC QMS Artifact      │     │
│   │ - Failure Report   │                  │ - Approval workflow    │     │
│   │ - Spare Item       │                  └────────┬───────────────┘     │
│   └────────┬───────────┘                           │                     │
│            │                                        │                     │
│            ▼                                        ▼                     │
│   ┌────────────────────┐                  ┌────────────────────────┐     │
│   │ Compliance/CAPA/   │                  │ Metric/Dashboard/      │     │
│   │ Audit Engine       │ ◄────metrics─────►│ Alert Engine           │     │
│   │ - AC Compliance    │                  │ - AC Metric Definition │     │
│   │ - AC CAPA          │                  │ - AC Dashboard Snapshot│     │
│   │ - AC Risk Entry    │                  │ - Alert dispatcher     │     │
│   └────────────────────┘                  └────────────────────────┘     │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

## 4. Cross-cutting concerns

| Concern | Cơ chế |
|---------|--------|
| AuthN | OAuth2 SSO bệnh viện + Frappe local user |
| AuthZ | Role + User Permission + DocType-level + field-level |
| Logging | Python logging + Frappe Logger + ELK/Loki |
| Tracing | OpenTelemetry (Wave 2) cho integration |
| Caching | Redis (Frappe) cho master data |
| Background jobs | Frappe RQ workers + cron |
| Realtime | Socket.IO (Frappe) |
| File storage | Frappe File + S3-compatible (MinIO) cho QMS-critical |
| Search | Frappe global + dedicated indexed fields cho asset_code/serial |
| Localization | Frappe i18n; tiếng Việt + tiếng Anh |

## 5. Layer interaction rules

1. Tầng trên gọi tầng dưới; **không** ngược lại.
2. Domain Layer **không** gọi trực tiếp Integration Layer; outbound qua Application Service (publish-subscribe).
3. Mọi rule nghiệp vụ đặt ở Domain Layer; Channel Layer chỉ render + validate cú pháp.
4. Audit log **đi xuyên** mọi tầng nhưng được tập trung tại QMS/Governance Layer.
5. Performance bottleneck ở tầng Data Layer xử lý bằng index + materialized view, không phải ở Domain Layer.

## 6. Đầu ra cho Phase 03–07

- Phase 03 (Data): chi tiết DocType cho mỗi engine.
- Phase 04 (Workflow): state machine cho từng DocType submittable.
- Phase 05 (QMS): cấu trúc artifact 4 tầng + chu trình.
- Phase 06 (UX): screen theo Channel Layer.
- Phase 07 (Integration): contract OpenAPI + FHIR theo Integration Layer.
