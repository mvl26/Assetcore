> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# TIER 4 — BM/HS/KPI-DASH (Biểu mẫu / Hồ sơ / KPI Dashboard)

**Phiên bản:** 1.0
**Owner:** QMS Officer

---

## A. BM (Biểu mẫu) — Form templates phục vụ vận hành

### BM-001 Báo hỏng thiết bị
- Triggers Failure Report DocType.
- Field: asset, severity, description, location, photo, reporter.

### BM-002 PM Checklist
- 1 template / Device Model.
- Triggers WO Task tự sinh khi WO PM tạo.
- Trường: task_no, description, expected_value, evidence_required.

### BM-003 Calibration Certificate
- Print Format Frappe.
- Trường: asset, performed_by, date, measurements, result, signatory, reference_standard.

### BM-004 Biên bản lắp đặt
- Print Format gắn vào WO Install closed.

### BM-005 IQ/OQ/PQ Form
- Bộ 3 form gắn vào AC IQ-OQ-PQ Record.

### BM-006 Stand-down Form
- Trường: asset, reason, evidence, expected_resume_date, approver chain.

### BM-007 Decommission Technical Assessment
- Trường: kỹ thuật, an toàn, kinh tế, lý do; evidence; recommendations.

### BM-008 Disposal/Donation Form
- Trường: phương thức, recipient, evidence pháp lý, hình ảnh.

### BM-009 Training Attendance + Competency Form
- Trường: session, attendees, score, competency rating.

### BM-010 Recall Response per asset
- Trường: asset, action_taken, vendor_confirm, evidence.

### BM-011 CAPA Template
- Trường: source NC, RCA method, action plan, effectiveness check.

### BM-012 Change Control Request Form
- Trường: scope, reason, impact, approval chain.

## B. HS (Hồ sơ) — Living records

| HS | Mô tả | Source |
|----|-------|--------|
| HS-001 Asset Profile | Hồ sơ sống cho từng thiết bị | View tổng hợp Medical Asset + Document + WO + Lifecycle Event |
| HS-002 Hồ sơ Pháp lý | Document Records (LEGAL) gắn asset | – |
| HS-003 Hồ sơ PM/CM/Cal lịch sử | Filtered list WO + Lifecycle Event | – |

## C. KPI-DASH — Dashboard widgets & metric definitions

### KPI-DASH-001 PM Compliance Rate
- Definition: MET-W1-001.
- Widget: gauge + trend chart (12 tháng).
- Drill-down: list WO PM completed late → WO detail.

### KPI-DASH-002 Cal Compliance Rate
- Definition: MET-W1-002.
- Widget: gauge.

### KPI-DASH-003 Avg MTTR (h)
- Definition: MET-W1-003.
- Widget: line chart by month.

### KPI-DASH-004 Downtime hours/tháng
- Definition: MET-W1-005.
- Widget: bar chart by department.

### KPI-DASH-005 License expiring 30/60/90
- Definition: MET-W1-006.
- Widget: stacked bar.

### KPI-DASH-006 CAPA aging
- Definition: MET-W1-008.
- Widget: histogram + count by severity.

### KPI-DASH-007 Recurring failures
- Definition: MET-W1-009.
- Widget: leaderboard of asset.

### KPI-DASH-008 Vendor SLA breach
- Definition: MET-W1-011.
- Widget: count by vendor.

### KPI-DASH-009 Adoption rate WO
- Definition: MET-W1-015.
- Widget: pct gauge (target 90% sau hypercare).

### KPI-DASH-010 License expired & in-use
- Definition: MET-W1-024.
- Widget: list count + drill-down.

(Mở rộng theo `Phase_02/Metric_Dashboard_Engine_Spec §3` — 25 KPI Wave 1.)

## D. Quan hệ giữa Tier 4 và DocType

| Artifact | DocType liên quan | Cơ chế |
|----------|--------------------|--------|
| BM-* | Frappe Print Format / Form template | Trigger từ DocType liên quan |
| HS-* | View/Report tổng hợp | Frappe Report |
| KPI-DASH-* | AC Metric Definition + AC Dashboard Widget | Frappe Dashboard |

## E. Quy tắc phát hành Tier 4
- Owner: QMS Officer.
- Review tần suất 3 tháng.
- Phiên bản hóa khi đổi cấu trúc; không cần approve lên Tier cao hơn nếu không thay đổi nguyên tắc.
- Mọi instance dữ liệu (Document Record dạng biểu mẫu) sinh ra dùng version artifact đang effective.

## F. Tiêu chí nghiệm thu Tier 4
- 12 BM + 3 HS + 25 KPI baseline đã có cấu hình + dashboard.
- Tất cả KPI có drill-down về record nguồn.
- Print Format render đúng cho biểu mẫu in giấy nếu cần.
- Người dùng tương ứng được training trên BM họ dùng.
