> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# INTERNAL AUDIT PLAN & CHECKLIST — ASSETCORE

**Phiên bản:** 1.0
**Owner:** QMS Lead + Kiểm toán nội bộ

---

## 1. Mục tiêu
- Định kỳ kiểm tra việc tuân thủ SOP/QMS, hiệu lực vận hành AssetCore.
- Phát hiện gap trước audit bên ngoài (ISO/JCI/Bộ Y tế).
- Trigger CAPA nếu phát hiện NC.

## 2. AC Audit (DocType)

| Field | Mô tả |
|-------|-------|
| audit_no | Naming `AUD-.YYYY.-.####` |
| audit_type | Internal / External / Pre-certification |
| period_from / period_to | – |
| scope | Modules / Departments / Assets sampling |
| auditor_team | Table |
| audit_plan_doc | Link Document Record |
| findings | Table (severity, description, linked_subject, NC link) |
| state | planned → in_progress → reported → closed |
| report_doc | Link Document Record |
| linked_capa | Table |

## 3. Tần suất
- Internal audit toàn hệ thống: 1 năm 1 lần.
- Internal audit module-specific: 1 lần/quý (rotational).
- External: tùy hợp đồng / lịch chứng nhận.

## 4. Quy trình audit

### 4.1 Plan
- QMS Lead lập audit plan.
- Approver: BGĐ phụ trách.

### 4.2 Notify
- Thông báo các đơn vị sẽ audit ≥ 2 tuần trước.

### 4.3 Execute
- Auditor sử dụng checklist.
- Phỏng vấn, walk-through, kiểm chứng records.

### 4.4 Findings
- Mỗi finding tạo NC nếu áp dụng.
- Severity: Major / Minor / Observation.

### 4.5 Report
- Audit report submit + approve.

### 4.6 Close
- Sau khi tất cả NC linked CAPA closed → audit closed.

## 5. Checklist Wave 1 (theo module IMM)

### 5.1 IMM-04 Tiếp nhận / Lắp đặt
- [ ] 100% asset Wave 1 có Asset Code tuân thủ Naming.
- [ ] Mỗi asset có ít nhất 1 Asset Identifier active.
- [ ] IQ/OQ/PQ pass cho asset đã commission.
- [ ] Asset state đúng vòng đời.

### 5.2 IMM-05 Hồ sơ pháp lý
- [ ] License effective cho 100% asset released_for_use.
- [ ] Expiry tracking + alert hoạt động.
- [ ] Không có asset license expired & in-use không có Compliance Case.

### 5.3 IMM-08 PM
- [ ] PM Plan tồn tại cho 100% asset criticality A/B.
- [ ] PM compliance ≥ 80%.
- [ ] WO PM closed có evidence + validate (QMS-critical).

### 5.4 IMM-09 Repair / Spare
- [ ] WO CM closed có root cause khi severity ≥ High.
- [ ] Phụ tùng tiêu thụ có Stock Entry.
- [ ] Software update có validation log.

### 5.5 IMM-11 Calibration
- [ ] Cal Plan tồn tại cho 100% asset cần Cal.
- [ ] Cert upload sau Cal Pass.
- [ ] Asset Fail Cal → stand-down + CAPA.

### 5.6 IMM-12 CM
- [ ] Failure Report → WO assigned trong SLA.
- [ ] Downtime tính đúng.
- [ ] CAPA mở khi recurring failure ≥ 3/90 ngày.

### 5.7 QMS / CAPA / Compliance
- [ ] CAPA tuân thủ SLA SLA-QMS-01..03.
- [ ] Effectiveness check thực hiện đúng kế hoạch.
- [ ] Compliance Case Recall thông báo Bộ Y tế trong 48h.

### 5.8 Document Control
- [ ] QMS Artifact Tier 1/2 effective.
- [ ] Periodic review không quá hạn quá 30 ngày.
- [ ] Training compliance ≥ 80%.

### 5.9 Audit Trail
- [ ] 100% transition QMS-critical có Lifecycle Event.
- [ ] Hash chain liên tục (W1.5).
- [ ] E-signature cho mọi action QMS-critical.

### 5.10 Permission / Security
- [ ] Role + User Permission đúng.
- [ ] Vendor scoped permission test pass.
- [ ] SoD violations = 0.

## 6. Sampling rule
- Random sampling theo strata: criticality + department + vendor.
- Cỡ mẫu tối thiểu: 10% asset hoặc 30 asset (lấy giá trị lớn hơn).

## 7. Auditor independence
- Auditor không được audit module/đơn vị mình thuộc.
- Auditor team có ≥ 1 thành viên từ Phòng KTNB.

## 8. Tích hợp dashboard
- Audit Findings Dashboard: số finding open theo module + dept.
- Closure rate.

## 9. Tiêu chí nghiệm thu
- Audit plan annual approved.
- Checklist 10 module thực thi đầy đủ.
- Mọi finding link NC + CAPA.
- Closure rate ≥ 90% trong 90 ngày.
