> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# NONCONFORMITY & COMPLIANCE CASE SPEC — ASSETCORE

**Phiên bản:** 1.0
**Owner:** QMS Lead

---

## 1. Phân biệt NC vs Compliance Case
- **NC (Nonconformity):** lỗi chất lượng / không tuân thủ phát hiện cụ thể (1 sự việc).
- **Compliance Case:** vụ việc/tình huống tuân thủ rộng hơn, có thể bao hàm nhiều NC + actions.

## 2. AC Nonconformity (NC)

### 2.1 Trường chính
- nc_no
- source (WO/Audit/Complaint/Inspection/Recall/Internal Report)
- severity (1=Critical / 2=Major / 3=Minor)
- reported_at, reporter_user
- description
- linked_asset / linked_wo / linked_document (tùy nguồn)
- state: draft → triaged → linked_to_capa → closed (hoặc closed_no_action)

### 2.2 Quy trình
1. Mở NC.
2. Triage bởi QMS Officer (3 ngày).
3. Phân loại severity.
4. Quyết định:
   - Mở CAPA (sev 1/2 bắt buộc).
   - Đóng không action (sev 3 nếu không phát sinh).
5. Sau CAPA close → đóng NC.

## 3. AC Compliance Case

### 3.1 Trường chính
- case_no
- case_type:
  - License Expired
  - PM Overdue
  - Cal Overdue
  - Recall
  - FSCA
  - Audit Finding
  - Vendor SLA Breach
  - Adverse Event / Vigilance
  - Internal Investigation
  - Other
- linked_asset / linked_doc / linked_wo / linked_capa
- severity (1/2/3)
- regulatory_authority (Bộ Y tế / Sở Y tế / ISO Auditor / JCI / Internal)
- disclosure_required (Check)
- disclosure_due_at
- state: open → investigating → action_in_progress → resolved → closed

### 3.2 Trigger tự động (Compliance Detector)
- License Expired & in-use → mở case (BR-014).
- PM Overdue ≥ X ngày → mở case (BR-026).
- Cal Overdue → mở case.
- Vendor SLA breach > N → mở case.

### 3.3 Quy trình chung
1. Mở case (auto/manual).
2. Investigate → xác định root cause + scope.
3. Action plan (có thể tạo CAPA).
4. Implement actions.
5. Verify → closed.

### 3.4 Recall (subtype)
- Bổ sung field:
  - scope: model_code / lot_no / serial_range / batch.
  - affected_assets table.
  - vendor_recall_ref (nếu thông báo từ vendor).
  - regulatory_notification_log table.
  - action_required: replace / repair / quarantine / monitor.
- SLA disclosure 48h.
- Workflow: open → identify_scope → notify_authority → bulk_create_recall_wo → track_completion → resolved → closed.

## 4. Phân biệt CAPA vs Action trong Case
- **CAPA** áp dụng khi cần RCA + effectiveness check.
- **Action** đơn lẻ (immediate containment) trong Compliance Case có thể không cần CAPA.
- Tuy nhiên, mọi case sev 1/2 → bắt buộc có ≥ 1 CAPA gắn kèm.

## 5. SLA tóm tắt

| Loại | Action | SLA |
|------|--------|-----|
| Recall confirmed → notify Bộ Y tế | disclosure | 48h |
| Compliance Case sev 1 | resolve plan | 7 ngày |
| Compliance Case sev 2 | resolve plan | 14 ngày |
| Compliance Case sev 3 | resolve plan | 30 ngày |

## 6. Reporting / Dashboard
- Open cases by type.
- Cases breaching SLA disclosure.
- Recall progress (% asset xử lý).
- Cases by source (WO / Audit / Complaint).

## 7. Disclosure log
- Mỗi notification gửi cơ quan QLNN ghi vào table:
  - timestamp_sent
  - method (email/portal/letter/phone)
  - recipient
  - reference_no
  - acknowledgment_received

## 8. Tiêu chí nghiệm thu
- Compliance Detector hoạt động cho 4 trigger Wave 1.
- Recall workflow bulk-create WO test pass.
- Disclosure SLA timer chính xác.
- Dashboard hiển thị correct.
