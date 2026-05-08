> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# SLA CATALOG — ASSETCORE

**Phiên bản:** 1.0
**Owner:** BA Lead + QMS Lead
**Quy ước thời gian:** Giờ làm việc (8h–17h, T2–T7) trừ khi có chú thích "đồng hồ thực".

---

## A. Báo hỏng & sửa chữa (CM)

| ID | Sự kiện đo | Start | Stop | Mức ưu tiên | SLA | Escalation 1 | Escalation 2 |
|----|-------------|-------|------|-------------|-----|--------------|--------------|
| SLA-CM-01 | Failure Report → WO assigned | failure_reported_at | wo.assignee_set_at | Critical | 30 phút (đồng hồ thực) | Phó VTTBYT (15') | Trưởng VTTBYT (30') |
| SLA-CM-02 | Failure Report → WO assigned | (như trên) | (như trên) | High | 2 giờ | KS BME trưởng | Trưởng VTTBYT |
| SLA-CM-03 | Failure Report → WO assigned | (như trên) | (như trên) | Medium | 1 ngày làm việc | KS BME trưởng | Trưởng VTTBYT |
| SLA-CM-04 | Failure Report → WO assigned | (như trên) | (như trên) | Low | 3 ngày làm việc | – | KS BME trưởng |
| SLA-CM-05 | WO open → repaired | failure_reported_at | repaired_at | Critical | 24h (đồng hồ thực) | Trưởng VTTBYT (24h) | BGĐ + escalate vendor (48h) |
| SLA-CM-06 | WO open → repaired | (như trên) | (như trên) | High | 3 ngày | Trưởng VTTBYT | – |
| SLA-CM-07 | WO open → repaired | (như trên) | (như trên) | Medium | 7 ngày | – | – |
| SLA-CM-08 | WO open → repaired | (như trên) | (như trên) | Low | 30 ngày | – | – |
| SLA-CM-09 | WO repaired → closed (validate) | repaired_at | wo.closed_at | Tất cả | 2 ngày làm việc | QMS Officer | QMS Lead |

## B. Bảo trì định kỳ (PM)

| ID | Sự kiện đo | Start | Stop | SLA | Escalation |
|----|-------------|-------|------|-----|------------|
| SLA-PM-01 | PM due → WO completed | pm_due_date | wo.completed_at | ≤ 7 ngày | Sau 7 ngày → Compliance Case warning |
| SLA-PM-02 | PM completed → validated/closed | wo.completed_at | wo.closed_at | ≤ 3 ngày | QMS Lead |
| SLA-PM-03 | Vendor service deadline (theo hợp đồng) | wo.assigned_to_vendor_at | wo.completed_at | Theo hợp đồng | Procurement |

## C. Hiệu chuẩn

| ID | Sự kiện đo | Start | Stop | SLA | Escalation |
|----|-------------|-------|------|-----|------------|
| SLA-CAL-01 | Cal due → WO completed | next_calibration_due | wo.completed_at | ≤ 14 ngày | Sau 14 ngày → Stand-down |
| SLA-CAL-02 | Cal Fail → CAPA opened | cal.result=fail | capa_opened_at | ≤ 1 ngày | QMS Lead |
| SLA-CAL-03 | Cal cert phát hành → upload Document | cal_completed_at | doc.uploaded_at | ≤ 3 ngày | QMS |

## D. Hồ sơ pháp lý

| ID | Sự kiện đo | Start | Stop | SLA | Notification |
|----|-------------|-------|------|-----|--------------|
| SLA-DOC-01 | License expiry alert | expiry_date − 90/60/30/15/7 | – | Theo lịch | VTTBYT + Pháp chế |
| SLA-DOC-02 | Document submit → review | doc.submitted_at | doc.review_at | ≤ 2 ngày | QMS Officer |
| SLA-DOC-03 | Document review → approve | doc.review_at | doc.approved_at | ≤ 3 ngày | QMS Lead |
| SLA-DOC-04 | License hết hạn nhưng asset vẫn `released_for_use` | expiry_date | (cảnh báo) | Đồng thời | Compliance Case + BGĐ |

## E. QMS / CAPA / Compliance

| ID | Sự kiện đo | Start | Stop | SLA |
|----|-------------|-------|------|-----|
| SLA-QMS-01 | NC severity 1 → CAPA opened | nc_opened_at | capa_opened_at | ≤ 24h |
| SLA-QMS-02 | NC severity 2 → CAPA opened | nc_opened_at | capa_opened_at | ≤ 5 ngày |
| SLA-QMS-03 | CAPA action assigned → completed | action_assigned_at | action_completed_at | Theo plan; nếu overdue 7 ngày → escalate QMS Lead |
| SLA-QMS-04 | CAPA effectiveness check | capa_action_completed_at + 30/60/90 ngày | check_completed_at | Đúng kỳ |
| SLA-QMS-05 | Compliance Case (Recall) → thông báo cơ quan | recall_confirmed_at | regulatory_notified_at | ≤ 48h |
| SLA-QMS-06 | Management Review | định kỳ 6 tháng | – | Đúng kỳ |
| SLA-QMS-07 | Internal audit closeout | audit_completed_at | findings_closed_at | ≤ 90 ngày |

## F. Workflow phê duyệt chung

| ID | Sự kiện đo | Đối tượng | SLA | Escalation |
|----|-------------|-----------|-----|------------|
| SLA-WF-01 | PM Plan submit → approve | KS BME → Trưởng VTTBYT | ≤ 5 ngày | Phó VTTBYT |
| SLA-WF-02 | CAPA submit → approve | QMS Officer → QMS Lead | ≤ 3 ngày | Trưởng QLCL |
| SLA-WF-03 | Procurement Decision approve | Hội đồng | Theo quy chế nội bộ | – |
| SLA-WF-04 | Asset Movement approve | Trưởng khoa cũ → Trưởng khoa mới → Trưởng VTTBYT | ≤ 5 ngày | Phó VTTBYT |
| SLA-WF-05 | Decommission approve | VTTBYT → Pháp chế → KTTC → QMS | ≤ 14 ngày | BGĐ |

## G. Vận hành hệ thống (Operational SLA)

| ID | Đối tượng | SLA |
|----|----------|-----|
| SLA-OPS-01 | Uptime AssetCore | ≥ 99.5%/tháng |
| SLA-OPS-02 | RPO (recovery point) | ≤ 1h |
| SLA-OPS-03 | RTO (recovery time) | ≤ 4h |
| SLA-OPS-04 | Backup full | hằng ngày |
| SLA-OPS-05 | Restore drill | quý |
| SLA-OPS-06 | Bug Critical bug fix | ≤ 24h |
| SLA-OPS-07 | Bug High bug fix | ≤ 5 ngày làm việc |
| SLA-OPS-08 | Hỗ trợ vận hành (helpdesk) | response 1h, resolve theo severity |

## H. Tổng hợp Tốc độ tính SLA

- SLA "đồng hồ thực" áp dụng cho: Critical CM (SLA-CM-01, 05), Recall (SLA-QMS-05).
- SLA "giờ làm việc" áp dụng phần còn lại (8–17h, T2–T7), tuy nhiên có thể cấu hình per khoa nếu khoa hoạt động 24/7.
- Tất cả SLA breach → tự sinh sự kiện `wo_breach_sla` (LE-49) hoặc Compliance Case.

## I. Phụ lục — Lifecycle Event sinh khi SLA breach
| Loại SLA breach | Action |
|-----------------|--------|
| WO SLA | LE-49 wo_breach_sla |
| PM overdue | tạo Compliance Case "PM Overdue" + BR-026 |
| Calibration overdue | Stand-down + Compliance Case |
| License expiry | Compliance Case "License Expired" + BR-014 |
| CAPA action overdue | Escalation theo SLA-QMS-03 |
