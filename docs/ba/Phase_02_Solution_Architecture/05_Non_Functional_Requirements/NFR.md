> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# NON-FUNCTIONAL REQUIREMENTS — ASSETCORE

**Phiên bản:** 1.0
**Owner:** SA Lead + IT Lead

---

## 1. Performance

| ID | Yêu cầu | Mục tiêu Wave 1 | Mục tiêu Wave 2 |
|----|---------|------------------|------------------|
| NFR-P-01 | Trang list view chính (asset, WO) | p95 ≤ 1.5s với 5k record/page | p95 ≤ 1.5s với 50k record qua server-side pagination |
| NFR-P-02 | Form record detail | p95 ≤ 800ms | p95 ≤ 800ms |
| NFR-P-03 | Dashboard render | p95 ≤ 2s | p95 ≤ 2s |
| NFR-P-04 | Mobile scan QR → mở record | p95 ≤ 1.2s | – |
| NFR-P-05 | Tạo WO từ Failure Report | p95 ≤ 1s | – |
| NFR-P-06 | Submit large WO (50 spare items) | p95 ≤ 3s | – |
| NFR-P-07 | Background job latency (PM scheduler) | ≤ 5 phút sau cron tick | – |

## 2. Scalability

| ID | Yêu cầu | Wave 1 | Wave 2/3 |
|----|---------|--------|----------|
| NFR-S-01 | Số asset hoạt động | 10.000 | 50.000+ |
| NFR-S-02 | Số WO/tháng | 5.000 | 20.000 |
| NFR-S-03 | Số Lifecycle Event/ngày | 50.000 | 500.000 |
| NFR-S-04 | Concurrent users | 200 | 1.000 |
| NFR-S-05 | File storage | 500 GB | 5 TB+ |

## 3. Availability & Reliability

| ID | Yêu cầu | Mục tiêu |
|----|---------|---------|
| NFR-A-01 | Uptime giờ vận hành | 99.5%/tháng |
| NFR-A-02 | Uptime 24/7 (Wave 2+) | 99.9%/tháng |
| NFR-A-03 | RPO | ≤ 1h |
| NFR-A-04 | RTO | ≤ 4h |
| NFR-A-05 | Backup | Daily full + binlog continuous |
| NFR-A-06 | DR site readiness | Warm standby; tested quý |
| NFR-A-07 | Mobile offline mode (sync sau) | Hỗ trợ failure report + completed task offline |

## 4. Data Integrity

| ID | Yêu cầu |
|----|---------|
| NFR-D-01 | Lifecycle Event immutable — chống update/delete kể cả System Admin |
| NFR-D-02 | E-signature không bị thay đổi sau ký |
| NFR-D-03 | Foreign key consistency: AC Medical Asset ↔ ERPNext Asset đồng bộ trong 5 phút |
| NFR-D-04 | Stock Entry consumption đối chiếu WO Spare Item daily |
| NFR-D-05 | Audit log không có gap thời gian (không thiếu phút nào) |

## 5. Security

| ID | Yêu cầu |
|----|---------|
| NFR-SEC-01 | TLS 1.3 in-transit; HSTS bật |
| NFR-SEC-02 | Encryption at-rest cho DB (column nhạy cảm) + bucket file |
| NFR-SEC-03 | Password policy: min 12 ký tự, MFA cho admin/QMS |
| NFR-SEC-04 | Session timeout: 30 phút inactivity desktop; 24h mobile |
| NFR-SEC-05 | Audit log immutable, lưu 10 năm |
| NFR-SEC-06 | Penetration test trước go-live; quý sau go-live |
| NFR-SEC-07 | Vulnerability scanning weekly |
| NFR-SEC-08 | Tách network DB/App/Backup; DB không truy cập trực tiếp từ Internet |
| NFR-SEC-09 | Vendor external chỉ qua VPN + scoped role |
| NFR-SEC-10 | Secret management: Vault / hashicorp / Frappe encrypted |

## 6. Privacy & Compliance

| ID | Yêu cầu |
|----|---------|
| NFR-PR-01 | Không lưu PHI (thông tin định danh bệnh nhân) trừ khi tích hợp HIS — và phải có hợp đồng riêng |
| NFR-PR-02 | Tuân thủ Nghị định 13/2023/NĐ-CP về bảo vệ dữ liệu cá nhân |
| NFR-PR-03 | Audit truy cập dữ liệu nhạy cảm |
| NFR-PR-04 | Right-to-be-deleted (đối với user account) tuân thủ pháp lý |

## 7. Maintainability

| ID | Yêu cầu |
|----|---------|
| NFR-M-01 | Custom code có unit test coverage ≥ 70% (Wave 1); ≥ 80% (Wave 2) |
| NFR-M-02 | Code review bắt buộc |
| NFR-M-03 | Linter + format pipeline |
| NFR-M-04 | Naming convention bắt buộc (Phase_00/07) |
| NFR-M-05 | Documentation in-line + README per module |
| NFR-M-06 | Migration scripts versioned |

## 8. Observability

| ID | Yêu cầu |
|----|---------|
| NFR-O-01 | Centralized log (ELK/Loki) |
| NFR-O-02 | Metrics hạ tầng (Prometheus + Grafana) |
| NFR-O-03 | Alert hạ tầng (CPU, RAM, disk, queue depth) |
| NFR-O-04 | Frappe error log → Slack/Email |
| NFR-O-05 | OpenTelemetry trace cho integration (Wave 2) |
| NFR-O-06 | Dashboard SOC: outbox depth, failed jobs, slow queries |

## 9. Usability

| ID | Yêu cầu |
|----|---------|
| NFR-U-01 | Mobile-first cho KTV/Vendor SE |
| NFR-U-02 | Tiếng Việt mặc định, song ngữ Việt-Anh cho tài liệu QMS Tier 1/2 |
| NFR-U-03 | WCAG 2.1 AA cho UI |
| NFR-U-04 | Trợ giúp ngữ cảnh (tooltip + link SOP) |
| NFR-U-05 | Số bước thao tác ≤ 5 cho action thường gặp (báo hỏng, scan QR, submit PM result) |

## 10. Compatibility

| ID | Yêu cầu |
|----|---------|
| NFR-C-01 | Browser: Chrome/Edge/Firefox/Safari 2 phiên bản gần nhất |
| NFR-C-02 | Mobile: Android 10+ và iOS 14+ |
| NFR-C-03 | API tuân thủ OpenAPI 3.x |
| NFR-C-04 | FHIR R4 cho integration y tế |
| NFR-C-05 | Tương thích ERPNext v15.x.x (test patch lên major mới khi release) |

## 11. Capacity Planning (Wave 1 baseline)

| Tài nguyên | Quy mô đề xuất |
|-----------|----------------|
| App nodes | 2 × 8 vCPU / 16 GB |
| DB primary | 1 × 8 vCPU / 32 GB / 500 GB SSD |
| DB replica | 1 × 8 vCPU / 32 GB |
| Redis | 2 × 4 vCPU / 8 GB (HA) |
| File storage | 500 GB ban đầu, mở rộng |
| Backup storage | 2 TB (rolling 30 ngày + cold) |

## 12. Tiêu chí nghiệm thu NFR
- Performance test pass tất cả NFR-P-*.
- Pen-test pass; không có vulnerability High open trước go-live.
- DR drill thành công ≥ 1 lần.
- Backup/restore drill quý.
- Observability dashboard hoạt động + alert tested.
