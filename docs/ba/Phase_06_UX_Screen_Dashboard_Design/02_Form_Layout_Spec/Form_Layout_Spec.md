> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# FORM LAYOUT SPECIFICATION — ASSETCORE

**Phiên bản:** 1.0
**Owner:** UX + BA Lead

---

## 1. Quy ước
- Mỗi DocType lớn có form layout chuẩn hóa: **Section → Tab → Group → Field**.
- Trên mobile: collapse thành accordion.
- Quick action buttons ở header (Submit, Approve, Validate, Print, Timeline).
- Conditional display: ẩn field không relevant theo state/wo_type.

## 2. AC Medical Asset

### Tabs
1. **Overview** (default)
2. **Lifecycle** (timeline + state)
3. **Documents** (linked Document Records)
4. **Maintenance** (PM/Cal/CM history)
5. **Risk** (Risk Entries)
6. **Movement** (history)
7. **Custodian** (history)
8. **Integration** (ERPNext Asset link)
9. **Audit Trail**

### Tab Overview
- Section "Định danh": asset_code, qr_url, rfid_epc, serial_no, manufacturer_serial.
- Section "Phân loại": device_model, item_template (read), risk_class, criticality.
- Section "Vị trí": facility, building, department, room, custodian_user, owner_department.
- Section "Vận hành": state, commission_date, released_for_use_at, warranty_expiry, replacement_signal.
- Section "PM/Cal nhanh": last_pm_date, next_pm_due, last_calibration_date, next_calibration_due, pm_compliance.

### Quick actions
- "Báo hỏng" (mở Failure Report tự gắn asset).
- "Tạo PM Plan".
- "Stand down".
- "Xem timeline".
- "In hồ sơ asset (PDF)".

### Conditional
- `erpnext_asset` chỉ visible khi state ≥ released_for_use.
- Field `legacy_ref` chỉ hiện khi `imported_from_legacy=1`.

## 3. AC Work Order (Unified)

### Tabs
1. **Overview**
2. **Tasks** (checklist)
3. **Spare Items**
4. **Pause Log**
5. **Validation**
6. **Cost** (chỉ hiện cho role được phép)
7. **Linked Records** (PM Plan, Cal Plan, Failure Report, CAPA)
8. **Audit Trail**

### Overview
- Section "Loại WO": wo_type (read-only sau khi tạo), priority, severity.
- Section "Asset & Location": medical_asset (link), location, department.
- Section "Lịch trình": planned_start_at, planned_end_at, sla_due_at, sla_breached.
- Section "Thực hiện": actual_start_at, actual_end_at, downtime_minutes.
- Section "Người thực hiện": assigned_team, assigned_user, executed_by_vendor, vendor_service_user.
- Section "Kết quả": close_code, root_cause, action_taken, validation_result.

### Conditional
- `severity` hiện chỉ wo_type=CM.
- Tab Validation chỉ hiện khi `validator_required=true`.
- Tab Cost chỉ visible Asset Manager + Finance.

### Quick actions
- Start / Pause / Resume / Complete / Validate / Close / Cancel.
- "Mở CAPA" (cho WO CM severity High).

## 4. AC Failure Report

### Mobile-first single page
- Asset (auto từ QR scan).
- Severity (Critical/High/Medium/Low).
- Location (auto từ asset).
- Description.
- Photo upload (camera button).
- Submit.

## 5. AC Document Record

### Tabs
1. **Overview**
2. **Linked Assets**
3. **Versions** (supersede chain)
4. **Approval History**
5. **Training** (nếu áp dụng)
6. **Audit Trail**

### Overview
- Section "Loại": document_type, subtype.
- Section "Số hiệu": document_no, version, language, issuing_authority.
- Section "Hiệu lực": effective_date, expiry_date, state.
- Section "File": attachment_file, original_lost.
- Section "Bảo mật": confidentiality, retention_period_years.

## 6. AC QMS Artifact

Tabs tương tự AC Document Record + thêm:
- **Approver Chain** (table)
- **Training Records**
- **Linked Processes** (modules / DocTypes)

## 7. AC PM Plan / Calibration Plan

- Section "Phạm vi": medical_asset hoặc asset_filter (1 trong 2).
- Section "Tần suất": frequency, lead_time_days, sla_minutes.
- Section "Tasks Template": child table với task description.
- Section "Validate": validator_required, vendor_service_provider.

## 8. AC CAPA

### Tabs
1. **Overview**
2. **Sources (NC linked)**
3. **Root Cause Analysis**
4. **Action Plan** (table)
5. **Effectiveness Check** (timepoints)
6. **Linked Assets / WO**
7. **Audit Trail**

### Quick actions
- Submit / Approve / Begin / Mark Effectiveness Pending / Close / Reopen.

## 9. AC Compliance Case

### Tabs
1. **Overview**
2. **Affected Assets** (list)
3. **Disclosure Log** (cho Recall)
4. **Action Plan**
5. **Linked CAPA**
6. **Audit Trail**

## 10. AC Asset Movement / Stand-Down / Decommission / Disposal

- Section "Asset"
- Section "Lý do" (reason, evidence)
- Section "Approver chain" (multi-step)
- Section "Hồ sơ tài chính" (cho Decom/Dispose)
- Section "Hồ sơ pháp lý" (cho Decom/Dispose)
- Section "Audit Trail"

## 11. AC Audit / Management Review

Layout đơn giản: Inputs (table) → Findings/Decisions (table) → Closure.

## 12. Common UI components

### 12.1 Lifecycle Event Timeline widget
- Hiển thị toàn bộ event của subject hiện tại.
- Có filter theo type + actor.
- Drill-down về source record.

### 12.2 Document Quick View
- Trong asset profile: hiển thị document hiệu lực gần nhất theo type.
- Click → mở Document Record.

### 12.3 Status Badge
- Màu theo state (theo workflow `style`).

### 12.4 Approval Step Indicator
- Hiển thị progress bar approval chain (1/3 cấp duyệt…).

## 13. Mobile considerations

- Layout single column.
- Form chia thành steps (wizard) cho action quan trọng (Failure Report, WO complete).
- Camera + QR scan integrate.
- Offline mode cho 2 form: Failure Report + WO complete.

## 14. Tiêu chí nghiệm thu Form Layout
- 100% DocType Wave 1 có layout spec.
- Mobile UI tested trên Android/iOS.
- Conditional display test pass.
- Quick action accessible ≤ 1 click.
