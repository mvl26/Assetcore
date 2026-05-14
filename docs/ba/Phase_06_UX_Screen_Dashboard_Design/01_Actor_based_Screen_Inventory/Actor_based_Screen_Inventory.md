> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# ACTOR-BASED SCREEN INVENTORY — ASSETCORE

**Phiên bản:** 1.0
**Owner:** UX + BA Lead
**Nguyên tắc:** Mỗi actor có "home view" + danh mục screen rõ ràng. Không thiết kế UI theo DocType — thiết kế theo mục đích sử dụng.

---

## 1. AC Asset Manager (Trưởng/Phó VTTBYT)

### Home Dashboard
- KPI VTTBYT (PM Compliance, Downtime, Open CAPA, Vendor SLA breach).
- Alerts: License expiring, PM overdue, Recall in progress.
- Quick actions: tạo PM Plan, mở Asset Movement, xem outbox.

### Screen list
1. Home Dashboard.
2. Asset List (filter by department/criticality/state).
3. Asset Profile detail (timeline, document, WO history).
4. Work Order List (open, today, breach).
5. PM Calendar.
6. Cal Calendar.
7. Approval Inbox (PM Plan, Movement, Decommission).
8. Document Library (in-scope).
9. CAPA Tracker (overview).
10. Reports & Exports.
11. Settings (in-scope).

## 2. AC BME Engineer

### Home
- WO của tôi đang xử lý.
- WO sắp đến hạn.
- Failure Report mới.

### Screens
1. Home.
2. WO List (assigned to me / team).
3. WO Detail.
4. Failure Report Triage Queue.
5. PM Plan management.
6. Calibration Plan management.
7. Spare consumption review.
8. Asset Profile.
9. Root Cause / CAPA propose.

## 3. AC Technician

### Mobile-first.
1. Home (Today's WO list).
2. QR scan.
3. Failure Report submit.
4. WO detail + checklist (mobile).
5. Spare request.
6. WO history (own).

## 4. AC Calibration Lab Engineer

1. Home (Cal due today).
2. Cal WO List.
3. Cal Record entry (measurement).
4. Cal Cert upload + e-sign.
5. Reference standard tracker.

## 5. AC Spare Warehouse Officer

1. Home (Reorder alerts).
2. Spare master.
3. Stock Entry queue (gắn WO).
4. Reorder requests.
5. Inventory by Device Model.

## 6. AC QMS Officer

### Home
- NC mới.
- CAPA pending.
- Document review queue.
- Compliance Cases open.

### Screens
1. Home.
2. NC list / triage.
3. CAPA tracker.
4. Compliance Case list (by type).
5. Recall workflow board.
6. Document Library + approval queue.
7. QMS Artifact tracker (4 tier).
8. Risk Register.
9. Audit findings.
10. Training tracker.
11. Validate WO queue (QMS-critical WO).

## 7. AC QMS Lead / Trưởng QLCL

- Tất cả screen của QMS Officer +
- Internal Audit dashboard.
- Management Review entry.
- High-level QMS dashboard (BGĐ-style).

## 8. AC Department Head (Trưởng khoa lâm sàng)

1. Home (Asset trong khoa, status, alerts).
2. Asset List (department scope).
3. Failure Reports of dept.
4. Approve Movement (incoming asset).
5. Approve Stand-down (own dept).
6. View training compliance.

## 9. AC Clinical User (BS, ĐD, KTV vận hành)

### Mobile-friendly.
1. Home (My assets, alerts).
2. QR scan thiết bị.
3. Submit Failure Report.
4. View "device manual" / "WI" link.

## 10. AC Procurement Officer (Wave 2)

1. Home (Procurement pipeline).
2. Need Assessment list.
3. Spec building.
4. Vendor evaluation.
5. Contract management.
6. Vendor performance.

## 11. AC Finance Officer (KTTC)

1. Home (Asset capitalization, Decommission queue).
2. ERPNext Asset cross-link.
3. Decommission/Disposal financial steps.
4. WO Cost report.
5. Contract value report.

## 12. AC Legal Officer (Pháp chế)

1. Home (License expiring, Document review).
2. Document Library (LEGAL).
3. License expiry tracker.
4. Decommission / Recall legal workflow.
5. Disclosure log.

## 13. AC Auditor (Internal)

- Read-only across system.
- Audit Trail Search.
- Lifecycle Event Timeline.
- Audit findings + CAPA.
- Export evidence.

## 14. AC Vendor Service Engineer (External)

- Mobile + portal scoped.
1. Home (Assigned WO).
2. WO detail / execute.
3. Upload report file.
4. View asset basic profile (only asset gắn WO).

## 15. AC Vendor Calibration (External)

1. Home (Cal WO assigned).
2. Cal Record entry.
3. Upload cert.

## 16. AC Vendor Trainer (External)

1. Training Session schedule.
2. Attendance management.
3. Upload competency.

## 17. AC Executive Viewer (BGĐ)

1. Executive Dashboard (top KPI, big-picture).
2. Drill-down to asset / case.
3. Compliance overview.
4. Resource view (PM/CM cost).

## 18. AC System Admin (IT)

1. System Health Dashboard (queue, backup, errors).
2. Audit Log Search.
3. User / Role / Permission management.
4. Integration logs + retry.
5. CR queue (technical).

## 19. Tổng quan số screen

| Role | Số screen Wave 1 |
|------|-------------------|
| Asset Manager | ~11 |
| BME Engineer | ~9 |
| Technician (mobile) | ~6 |
| Cal Lab Eng | ~5 |
| Spare Warehouse | ~5 |
| QMS Officer | ~11 |
| QMS Lead | ~14 |
| Department Head | ~6 |
| Clinical User | ~4 |
| Finance | ~5 |
| Legal | ~5 |
| Auditor | ~5 |
| Vendor SE | ~4 |
| Vendor Cal | ~3 |
| Vendor Trainer | ~3 |
| Executive | ~4 |
| System Admin | ~5 |

(Tổng ~100 screen logic, một số shared cross-role.)

## 20. Tiêu chí nghiệm thu
- Mỗi role có Home + ≤ 12 screen Wave 1.
- Mọi action quan trọng ≤ 5 click.
- Mobile UI cho 4 role chính (Technician, Vendor SE, Vendor Cal, Clinical User).
- KPI mọi widget có drill-down.
