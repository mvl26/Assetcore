> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# REFERENCE ARCHITECTURE DOCUMENTATION — ASSETCORE

**Phiên bản:** 1.0 (cập nhật từ Phase_02)
**Owner:** SA Lead

---

## Mục đích
Tài liệu kiến trúc tham chiếu duy nhất cho Dev IT — gộp tinh thần kiến trúc từ Phase 02 + cập nhật theo các quyết định ADR.

## 1. Tóm tắt kiến trúc

AssetCore là **operating architecture thống nhất** trên ERPNext v15 / Frappe:
- ERPNext core: System of Record cho Item, Asset, Purchase, Stock, Supplier.
- Custom app `assetcore`: Domain Layer cho HTM/QMS với 6 engine cốt lõi.
- Modular monolith Wave 1; micro-services chỉ Wave 3 (predictive ML, IoT).
- 1 site Frappe + DR site warm standby.

## 2. 7 tầng kiến trúc

(Tham chiếu Phase_02/02 — chi tiết.)
1. User / Channel Layer
2. Workflow / Application Service Layer
3. Domain / Business Layer (6 engine)
4. Data / Document Layer
5. Integration Layer
6. Analytics / Dashboard / Alert Layer
7. QMS / Governance Layer

## 3. 6 Engines

| Engine | Trách nhiệm | DocType chính |
|--------|-------------|---------------|
| Asset Registry | SoR thiết bị | AC Medical Asset, Identifier, Custodian, Device Model, Location |
| Lifecycle Event | Audit + outbox | AC Lifecycle Event, Event Type |
| Unified Work Order | PM/CM/Cal/Inspection/Install/Recall/Retire | AC Work Order + Tasks + Spare Items |
| Document & QMS | Tài liệu pháp lý + QMS 4 tier | AC Document Record, AC QMS Artifact |
| Compliance / CAPA / Audit | NC, CAPA, Compliance Case, Risk, Change Control, Audit | AC NC, CAPA, Compliance Case, Risk Entry, Change Control, Audit, Management Review |
| Metric / Dashboard / Alert | KPI snapshot + alert | AC Metric Definition, Dashboard Snapshot, Widget, Alert Rule |

## 4. Patterns chính

| Pattern | Áp dụng |
|---------|--------|
| Outbox | Mọi outbound webhook qua Lifecycle Event |
| Repository | Domain service truy DB qua repository wrap |
| ACL | ERPNextAssetSync giữa MA và Asset |
| Aggregate Root | Mỗi DocType lớn là 1 aggregate |
| Domain Events | Publisher pattern cho Lifecycle Event |
| Bounded Context | 7 context (Phase_03/02) |

## 5. Quan hệ với ERPNext core

(Tham chiếu Phase_03/07 — chi tiết.)

Quy tắc cứng:
- Không sửa core schema.
- AC Medical Asset 1..1 ERPNext Asset.
- Custom field qua Custom Field DocType.
- Hooks 2 chiều đồng bộ field critical.

## 6. Nguyên tắc bất di bất dịch

1. State chỉ chuyển qua workflow (không bypass).
2. Lifecycle Event immutable — không update/delete.
3. Mọi action QMS-critical e-signature.
4. Validator ≠ Executor (segregation).
5. Naming convention prefix `AC `.
6. Mọi file QMS-critical lưu bucket WORM.
7. Audit trail không có gap.
8. KPI mọi widget có drill-down về record nguồn.

## 7. Triển khai vật lý

```
DMZ:
  Nginx + WAF (TLS 1.3, ModSec OWASP CRS)

App Tier (HA 2 nodes):
  Frappe + ERPNext + assetcore
  Gunicorn + Background workers (RQ)

Data Tier:
  MariaDB primary + replica
  Redis HA (Sentinel)
  MinIO HA (Object Lock cho QMS-critical)

Backup:
  Daily full + binlog continuous
  Off-site cold storage 90 ngày

DR:
  Warm standby
  RPO ≤ 1h, RTO ≤ 4h

Monitoring:
  Prometheus + Grafana + Loki
  Frappe error log + alert pipeline
```

## 8. Tích hợp

- Wave 1: ERPNext core (cùng site), SSO, Email, SMS (W1.5).
- Wave 2: HIS/EMR/LIS/RIS/PACS qua FHIR R4; ERP Finance (nếu tách).
- Wave 3: IoT, Predictive ML, Multi-site federation.

## 9. Bảo mật cấp nhà

- AuthN: OAuth2/OIDC SSO + Frappe local cho admin.
- AuthZ: Role + User Permission + ABAC custom.
- E-sig: plugin Frappe + HSM optional Wave 1.5.
- Audit: Lifecycle Event immutable + Frappe Version + Login log.
- Encryption: TLS 1.3 + at-rest cho file + DB column nhạy cảm.
- Vendor scoped + VPN.

## 10. Tài liệu liên quan
- Phase_02 (Solution Architecture) — chi tiết tầng + engine.
- Phase_03 (Data & Domain) — ERD + DocType + state machine.
- Phase_04 (Process & Workflow) — workflow + permission + audit.
- Phase_07 (Integration) — API + FHIR + webhook.

## 11. Tiêu chí nghiệm thu
- Tài liệu này được Tech Lead + ARB approve.
- ADR log đầy đủ (Phase_02/04).
- Dev IT có thể implement mà không phải hỏi BA về kiến trúc.
