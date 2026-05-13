> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# REPORT & DASHBOARD INDEX — WAVE 1

**Tham chiếu:**
- Dashboard & Report Catalog: Phase_06/04.
- KPI Metric Dictionary: Phase_06/05.
- Alert Catalog: Phase_06/06.

---

## 1. Dashboards Wave 1
14 dashboards (Phase_06/04 §2): DASH-001 → DASH-014.

## 2. Reports Wave 1
20 reports (Phase_06/04 §3): RPT-001 → RPT-020.

## 3. KPIs Wave 1
25 metrics: MET-W1-001 → MET-W1-025.

## 4. Implementation guidance

### Dashboard
- Frappe Dashboard + custom Vue widget khi cần.
- Mỗi widget có:
  - `metric_id` link.
  - `drill_down_route` link.
  - `role_audience` filter.
- Performance: server-side aggregation + cache.

### Report
- Frappe Query Report cho report đơn giản.
- Frappe Script Report cho logic phức tạp.
- Print Format cho output PDF chính thức.

### KPI Metric
- Lưu definition trong DocType `AC Metric Definition`.
- Snapshot job daily/monthly → `AC Dashboard Snapshot`.
- Truy vấn drill-down qua API `assetcore.metrics.compute()`.

## 5. Build sequence
- Sprint 4: 5 KPI cốt lõi (PM Compl, Cal Compl, MTTR, Downtime, License Expiring).
- Sprint 4-5: 15 KPI mở rộng.
- Sprint 6: 5 KPI còn lại + drill-down hoàn thiện.
- Sprint 7: snapshot strategy + alert threshold.

## 6. Tiêu chí nghiệm thu
- 25 KPI có data lineage + drill-down.
- 14 dashboard render < 2s p95.
- 20 report export đúng format.
- Alert threshold tested (Phase_06/06).
