> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# DASHBOARD & REPORT CATALOG — ASSETCORE

**Phiên bản:** 1.0
**Owner:** BA Lead + UX

---

## 1. Quy ước
Mỗi dashboard/report có:
- Mã (DASH-XXX, RPT-XXX).
- Audience (role).
- Mục đích.
- Widgets / Columns.
- Source (DocType/metric).
- Drill-down path.
- Export formats.

## 2. Dashboard Catalog

### DASH-001 Asset Manager Home
- Audience: AC Asset Manager.
- Widgets:
  - KPI: PM Compliance, Cal Compliance, Avg MTTR, Downtime.
  - Alerts: License expiring 30, Open CAPA, Recall in progress.
  - Recent WO breach SLA.
  - Asset criticality A health (% pm_compliance).
- Drill-down: → list filter tương ứng → detail.

### DASH-002 BME Engineer Home
- Audience: AC BME Engineer.
- Widgets: WO của team, FR cần triage, PM tuần này, Cal tuần này.

### DASH-003 Technician Mobile Home
- Mobile.
- Widgets: WO hôm nay, FR mới gắn cho tôi, scan QR shortcut.

### DASH-004 QMS Officer Home
- Audience: AC QMS Officer.
- Widgets: NC mới, CAPA pending, Compliance Case open, Document review queue, Validate WO queue.

### DASH-005 QMS Lead / Trưởng QLCL Dashboard
- Widgets: QMS health (CAPA aging, audit findings, training compliance, document expiring), Recall tracker, Risk heatmap.

### DASH-006 Department Head Dashboard
- Audience: AC Department Head.
- Widgets: Asset trong khoa, FR mới, training compliance khoa, PM compliance khoa.

### DASH-007 Clinical User Mobile Home
- Asset thuộc khoa user, alerts, "báo hỏng" shortcut.

### DASH-008 Procurement Officer Dashboard (Wave 2)
- Need pipeline, Vendor evaluation, Contract expiring, Vendor SLA breach.

### DASH-009 Finance Officer Dashboard
- ERPNext Asset reconciliation, Decommission queue, Disposal pending, WO Cost summary.

### DASH-010 Legal Officer Dashboard
- License expiring (multi bucket), Recall disclosure pending, Decommission legal queue.

### DASH-011 Auditor Dashboard
- Audit Trail Search, Audit Findings tracker, Lifecycle Event Timeline search.

### DASH-012 Vendor SE Portal Home
- Assigned WO, upcoming PM, recent completed.

### DASH-013 Executive Dashboard (BGĐ)
- High-level: Asset count by state, PM compliance overall, Downtime trend, Open CAPA, License expired & in-use, Recall progress.
- Drill-down: → role-specific dashboard.

### DASH-014 System Admin Dashboard
- System Health: queue depth, failed jobs, integration errors, backup status, audit gaps.

## 3. Report Catalog (formal reports — exportable)

### RPT-001 Asset Profile Report
- Per asset; gồm Identifier, Document, PM/CM/Cal history, Lifecycle Event timeline.
- Format: PDF.

### RPT-002 PM Compliance Report (per period)
- Filter by department / criticality / vendor.
- Format: Excel + PDF.

### RPT-003 Calibration Compliance Report
- Tương tự RPT-002.

### RPT-004 Downtime Report
- Per asset / department / vendor.

### RPT-005 License Expiry Report
- 30/60/90 days bucket.

### RPT-006 CAPA Aging Report
- By severity / department.

### RPT-007 Compliance Case Report
- By case_type / period.

### RPT-008 Recall Tracker Report
- Per case + per asset.

### RPT-009 Vendor SLA Performance Report
- By vendor / contract.

### RPT-010 Spare Consumption Report (Wave 2)
- By Item / Device Model.

### RPT-011 Asset Movement Report
- Per period.

### RPT-012 Decommission/Disposal Report
- Per period.

### RPT-013 Training Compliance Report
- Per artifact / department.

### RPT-014 Audit Trail Report
- Per asset / case / period.
- Gồm chữ ký số chứng minh tính nguyên vẹn.

### RPT-015 Management Review Inputs Pack
- Gói tự động cho Management Review.

### RPT-016 KPI Snapshot Report (monthly/quarterly)
- All 25 KPI Wave 1.

### RPT-017 Risk Register Report
- Heatmap + list.

### RPT-018 Cost per Asset Report
- PM + CM cost breakdown.

### RPT-019 Adverse Event Report (Wave 2)
- Per period.

### RPT-020 Bộ Y tế / Sở Y tế export packages (Wave 2)
- Templates theo yêu cầu pháp lý.

## 4. Drill-down convention

```
KPI Widget ──► Filtered List ──► Record Detail ──► Lifecycle Event Timeline ──► Evidence Files
```

## 5. Export rules
- PDF cho hồ sơ chính thức + Audit Trail (có signature hash).
- Excel cho phân tích.
- CSV cho data ETL.
- API (JSON) cho integration.

## 6. Role audience map (selected)

| Dashboard | Audience |
|-----------|----------|
| DASH-001 | AC Asset Manager |
| DASH-002 | AC BME Engineer |
| DASH-003 | AC Technician (mobile) |
| DASH-004 | AC QMS Officer |
| DASH-005 | AC QMS Lead |
| DASH-006 | AC Department Head |
| DASH-007 | AC Clinical User (mobile) |
| DASH-008 | AC Procurement Officer (Wave 2) |
| DASH-009 | AC Finance Officer |
| DASH-010 | AC Legal Officer |
| DASH-011 | AC Auditor |
| DASH-012 | AC Vendor SE (portal) |
| DASH-013 | AC Executive Viewer |
| DASH-014 | AC System Admin |

## 7. Tiêu chí nghiệm thu
- 14 dashboard + 20 report Wave 1 baseline.
- Drill-down 100% pass.
- Performance render ≤ 2s p95.
- Export tested cho mọi format.
- Permission enforced theo role.
