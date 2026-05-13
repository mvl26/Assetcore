> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# SAMPLE DATASET & SEED DATA — ASSETCORE WAVE 1

**Phiên bản:** 1.0
**Owner:** QA + Migration Lead

---

## Mục đích
Bộ dữ liệu mẫu (synthetic) đủ phong phú để Dev/QA chạy E2E test trên DEV/UAT mà không phụ thuộc PROD anonymized.

## 1. Phạm vi mẫu

| Entity | Số lượng | Mục đích |
|--------|---------|---------|
| AC Manufacturer | 10 | GE, Siemens, Philips, Mindray, Drager, Roche, Abbott, Olympus, Karl Storz, Other |
| AC Location | 100 | 1 Facility + 5 Building + 30 Department + 100 Room |
| AC Device Model | 30 | đa dạng theo Imaging/Lab/Life Support/Monitoring/Surgical |
| AC Service Provider | 15 | Vendor service + Calibration lab |
| AC Contract | 25 | 10 mua, 10 bảo trì, 5 hiệu chuẩn |
| AC Medical Asset | 200 | đa dạng criticality + state |
| AC Asset Identifier | 250 | 1.25 ID/asset |
| AC Document Record | 500 | 200 LEGAL, 100 IQOQPQ, 50 CALCERT, 100 MANUAL, 50 MAINT |
| AC QMS Artifact | 60 | đầy đủ 4 tier baseline |
| AC PM Plan | 150 | 75% asset criticality A/B |
| AC Calibration Plan | 80 | asset cần Cal |
| AC Work Order (history 24m) | 1.000 | 50% PM, 30% CM, 15% Cal, 5% Inspection/Install |
| AC Failure Report | 300 | đa severity |
| AC Calibration Record | 200 | 95% pass, 5% fail |
| AC Lifecycle Event | 5.000 | tất cả type Wave 1 |
| AC Nonconformity | 50 | đa severity |
| AC CAPA | 25 | một số đang in_progress, một số closed |
| AC CAPA Action | 100 | 4 actions/CAPA average |
| AC Compliance Case | 15 | License Expired, PM Overdue, Recall scenario, Vendor SLA |
| AC Risk Entry | 40 | đa scope |
| AC Change Control Request | 10 | đa state |
| AC Asset Movement | 25 | – |
| AC Stand-Down Record | 10 | – |
| AC Decommission Record | 5 | – |
| AC Disposal Record | 3 | – |
| AC Audit | 3 | 1 internal complete + 1 in_progress + 1 planned |
| AC Management Review | 2 | 1 completed + 1 scheduled |
| AC Training Session | 50 | đa role |
| AC Metric Definition | 25 | tất cả Wave 1 KPI |
| AC Dashboard Snapshot | 300 | 12 tháng × 25 metrics |

## 2. User accounts seed

| Email | Role | Department |
|-------|------|-----------|
| asset.manager@bv1.local | AC Asset Manager | VTTBYT |
| bme.engineer@bv1.local | AC BME Engineer | VTTBYT |
| technician1@bv1.local | AC Technician | VTTBYT |
| technician2@bv1.local | AC Technician | VTTBYT |
| cal.lab@bv1.local | AC Calibration Lab Engineer | QLCL |
| spare.officer@bv1.local | AC Spare Warehouse Officer | VTTBYT |
| qms.officer@bv1.local | AC QMS Officer | QLCL |
| qms.lead@bv1.local | AC QMS Lead | QLCL |
| dept.head.cdh@bv1.local | AC Department Head | CĐHA |
| dept.head.icu@bv1.local | AC Department Head | ICU |
| clinical.user@bv1.local | AC Clinical User | CĐHA |
| finance@bv1.local | AC Finance Officer | KTTC |
| legal@bv1.local | AC Legal Officer | Pháp chế |
| auditor@bv1.local | AC Auditor | KTNB |
| vendor.ge@external.com | AC Vendor Service Engineer | (vendor GE) |
| executive@bv1.local | AC Executive Viewer | BGĐ |
| sysadmin@bv1.local | AC System Admin | CNTT |

## 3. Phân bổ asset (đa dạng)

| Khoa | Asset count | Criticality mix |
|------|-------------|-----------------|
| CĐHA (Imaging) | 50 | A=15, B=20, C=10, D=5 |
| ICU | 30 | A=20, B=8, C=2 |
| Phòng mổ | 25 | A=18, B=5, C=2 |
| Lab xét nghiệm | 30 | A=10, B=12, C=8 |
| Khoa Tim mạch | 20 | A=8, B=8, C=4 |
| Khoa Sản | 15 | B=8, C=5, D=2 |
| Khoa Nhi | 15 | A=5, B=6, C=3, D=1 |
| Hành chính / khác | 15 | C=10, D=5 |

## 4. Scenario seed

- Scenario A: 5 asset có license sắp expire 30/60/90 ngày → trigger expiry alert.
- Scenario B: 10 asset criticality A có PM overdue → Compliance Case.
- Scenario C: 1 asset có 3 WO CM trong 90 ngày → Recurring CAPA.
- Scenario D: 1 model recall — 8 asset bị ảnh hưởng → Recall workflow demo.
- Scenario E: 5 asset state=stand_down → testing resume/decommission.
- Scenario F: 3 CAPA closed, 5 CAPA in_progress, 2 reopened.
- Scenario G: WO history với mix vendor SE và in-house.

## 5. Implementation
- Python script `assetcore.setup.seed.run_full_seed` (run on DEV).
- Random seed cố định (seed=42) để reproducible.
- Data có flag `is_test_data=true` để dễ phân biệt khỏi dữ liệu thực.

## 6. Cleanup
- Script `assetcore.setup.seed.cleanup` xóa toàn bộ test data.

## 7. Tiêu chí nghiệm thu
- Seed script chạy < 10 phút.
- 200 asset đầy đủ profile + document.
- Mọi scenario A-G test pass.
- Metric snapshot 12 tháng có dữ liệu reasonable (PM Compliance ~ 90%, MTTR ~ 20h).
