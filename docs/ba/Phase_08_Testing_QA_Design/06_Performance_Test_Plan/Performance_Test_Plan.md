> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# PERFORMANCE TEST PLAN — ASSETCORE

**Phiên bản:** 1.0
**Owner:** QA Lead + IT Lead

---

## 1. Phạm vi
Đảm bảo NFR-P-* và NFR-S-* được thỏa mãn trên môi trường STAGING (giống PROD).

## 2. Mục tiêu

| ID | Yêu cầu | Mục tiêu Wave 1 |
|----|---------|------------------|
| P-01 | List view chính | p95 ≤ 1.5s với 5k record |
| P-02 | Form record detail | p95 ≤ 800ms |
| P-03 | Dashboard render | p95 ≤ 2s |
| P-04 | Mobile QR → asset detail | p95 ≤ 1.2s |
| P-05 | Tạo WO từ FR | p95 ≤ 1s |
| P-06 | Submit WO 50 spare items | p95 ≤ 3s |
| P-07 | PM scheduler latency | ≤ 5 phút |
| S-01 | 10k assets active | OK |
| S-02 | 5k WO/tháng | OK |
| S-03 | 50k LE/ngày | OK |
| S-04 | 200 concurrent users | OK |

## 3. Scenarios test

### Scenario 1 — Browse load
- 200 user concurrent, browse list view + open detail.
- Tools: k6.
- Duration: 30 phút.
- Pass: NFR-P-01, P-02 met.

### Scenario 2 — WO load
- 50 user concurrent, scan QR + execute mobile WO.
- 1000 WO/giờ peak.
- Pass: NFR-P-04, P-06.

### Scenario 3 — Lifecycle Event ingest
- 50k LE/ngày = ~580 LE/phút sustained, peak 5x.
- Outbox dispatcher latency p95 ≤ 5s.
- Pass: NFR-O dispatcher.

### Scenario 4 — Webhook outbound
- 1000 webhook/phút.
- Pass: dead-letter rate < 0.1%.

### Scenario 5 — Background scheduler
- PM scheduler scan 10k PM Plan, sinh WO trong < 5 phút.

### Scenario 6 — Soak test
- 8h liên tục browsing + WO + LE ingest.
- Pass: không memory leak, không slowdown.

### Scenario 7 — Spike test
- 2x peak load trong 10 phút.
- Pass: graceful degradation, queue depth bounded.

### Scenario 8 — Capacity test
- Tăng dần load đến break point.
- Pass: tìm được trần năng lực + xác định bottleneck.

## 4. Profiling

- DB query slow log (> 100ms).
- Frappe slow log (> 500ms request).
- Redis hit rate.
- Worker queue depth.
- File storage latency.

## 5. Kết quả & Action

- Báo cáo p50/p95/p99 cho từng endpoint.
- So sánh baseline vs target.
- Bottleneck analysis.
- Recommendations: index, caching, query optimization.

## 6. Test environment

- STAGING giống PROD (cùng spec NFR §11).
- Dataset đầy: 10k assets, 5k WO, 200k LE seeded.

## 7. Tooling
- k6 chính.
- Locust phụ.
- Grafana monitoring.

## 8. Lịch chạy
- Trước UAT Sprint 4 (1 tuần).
- Sau mỗi major release (regression).

## 9. Tiêu chí nghiệm thu Performance
- 100% NFR-P-* và NFR-S-* met.
- Soak 8h pass.
- Bottleneck doc + fix plan.
- Capacity break point documented.
