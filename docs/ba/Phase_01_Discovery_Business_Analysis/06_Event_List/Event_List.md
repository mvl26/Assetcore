> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# EVENT LIST — ASSETCORE

**Phiên bản:** 1.0
**Owner:** BA Lead + SA Lead
**Mục đích:** Danh mục đầy đủ business event được capture vào `AC Lifecycle Event Engine` + audit trail.

---

## Quy ước

Mỗi event có 8 trường:
- **ID** (`LE-XX`)
- **Tên kỹ thuật** (snake_case)
- **Tên hiển thị**
- **Trigger** (DocType + state change / hành động)
- **Actor**
- **Payload chính**
- **Audit class** (info/critical/QMS-critical)
- **Wave**

---

## A. Event vòng đời thiết bị (Asset Lifecycle)

| ID | Tên kỹ thuật | Hiển thị | Trigger | Actor | Payload chính | Audit | Wave |
|----|--------------|----------|---------|-------|----------------|-------|------|
| LE-01 | need_registered | Đăng ký nhu cầu | AC Need Assessment submit | Trưởng khoa, Trưởng VTTBYT | demand_id, requestor, dept, justification | info | 2 |
| LE-02 | procurement_approved | Duyệt mua sắm | AC Procurement Decision submit | BGĐ + Hội đồng | po_ref, vendor, amount | critical | 2 |
| LE-03 | installed | Đã lắp đặt | AC Work Order Install state=installed | KS BME + Vendor | install_date, install_team, location | critical | 1 |
| LE-04 | commissioned | Đã commissioning | IQ/OQ/PQ approved | QMS Officer | iq_oq_pq_ref, qms_signoff | QMS-critical | 1 |
| LE-05 | license_registered | Đăng ký giấy phép | Document Record state=effective (license) | Pháp chế | doc_id, license_no, expiry | QMS-critical | 1 |
| LE-06 | released_for_use | Phát hành sử dụng | MA state=released_for_use | QMS Officer + Trưởng VTTBYT | release_date, release_authority | QMS-critical | 1 |
| LE-07 | pm_completed | Hoàn tất PM | WO PM state=closed | KTV/Vendor + QMS validate | wo_id, pm_plan_id, completed_at | critical | 1 |
| LE-08 | calibrated | Đã hiệu chuẩn | WO Cal state=closed | Cal Lab Eng/Vendor | cert_id, result, next_due | QMS-critical | 1 |
| LE-09 | failure_reported | Báo hỏng | Failure Report submit | Người dùng | severity, location, description | critical | 1 |
| LE-10 | repaired | Đã sửa | WO CM state=repaired | KS BME / Vendor | wo_id, root_cause, parts_used | critical | 1 |
| LE-11 | software_updated | Cập nhật firmware/SW | Software Update Record submit | KS BME / Vendor | from_ver, to_ver, validation | QMS-critical | 1.5 |
| LE-12 | recalled | Recall | Compliance Case (Recall) approved | QMS Officer | recall_ref, scope, action | QMS-critical | 1.5 |
| LE-13 | transferred | Điều chuyển | Asset Movement approved | Trưởng VTTBYT | from_loc, to_loc, custodian_to | critical | 2 |
| LE-14 | stand_down | Tạm ngưng | Stand-Down Record approved | Trưởng VTTBYT + QMS | reason, effective_from | QMS-critical | 2 |
| LE-15 | retired | Giải nhiệm | Decommission Record approved | Trưởng VTTBYT + QMS + KTTC | reason, effective_from | QMS-critical | 2 |
| LE-16 | disposed | Thanh lý/tiêu hủy | Disposal Record approved | KTTC + Pháp chế + QMS | method, evidence | QMS-critical | 2 |

## B. Event QMS / Compliance / CAPA

| ID | Tên kỹ thuật | Hiển thị | Trigger | Actor | Payload | Audit | Wave |
|----|--------------|----------|---------|-------|---------|-------|------|
| LE-21 | nc_opened | Mở nonconformity | NC submit | Bất kỳ | nc_id, scope | critical | 1 |
| LE-22 | capa_opened | Mở CAPA | CAPA Case submit | QMS Officer | capa_id, source_nc | QMS-critical | 1 |
| LE-23 | capa_action_completed | Hoàn tất action CAPA | CAPA Action state=done | Action owner | action_id, evidence | QMS-critical | 1.5 |
| LE-24 | capa_effectiveness_passed | Hiệu lực CAPA đạt | Effectiveness check pass | QMS Officer | capa_id, check_date | QMS-critical | 1.5 |
| LE-25 | capa_closed | Đóng CAPA | CAPA state=closed | QMS Officer | capa_id, closed_at | QMS-critical | 1.5 |
| LE-26 | compliance_case_opened | Mở case tuân thủ | Compliance Case submit | QMS Officer | case_id, type | QMS-critical | 1.5 |
| LE-27 | compliance_case_closed | Đóng case tuân thủ | Compliance Case state=closed | QMS Officer | case_id, outcome | QMS-critical | 1.5 |
| LE-28 | document_published | Phát hành tài liệu QMS | QMS Artifact state=effective | QMS Officer | artifact_id, tier | QMS-critical | 1 |
| LE-29 | document_obsoleted | Tài liệu hết hiệu lực | QMS Artifact state=obsolete | QMS Officer | artifact_id, replaced_by | QMS-critical | 1.5 |
| LE-30 | change_control_approved | Duyệt change control | Change Control Request approved | CCB | cr_id, scope | QMS-critical | 1.5 |
| LE-31 | management_review_completed | Soát xét lãnh đạo | Management Review submit | Trưởng QLCL | review_period, decisions | QMS-critical | 1.5 |
| LE-32 | risk_entry_created | Tạo rủi ro | Risk Entry submit | QMS Officer | risk_id, severity | critical | 1.5 |
| LE-33 | risk_entry_mitigated | Giảm thiểu rủi ro | Risk Entry state=mitigated | Owner | risk_id, action | critical | 1.5 |

## C. Event Work Order Engine

| ID | Tên kỹ thuật | Hiển thị | Trigger | Audit | Wave |
|----|--------------|----------|---------|-------|------|
| LE-41 | wo_planned | WO planned | WO state=planned | info | 1 |
| LE-42 | wo_assigned | WO giao việc | WO assignee set | info | 1 |
| LE-43 | wo_started | WO bắt đầu | started_at set | info | 1 |
| LE-44 | wo_paused | WO tạm dừng | state=paused | info | 1 |
| LE-45 | wo_resumed | WO tiếp tục | state=in_progress | info | 1 |
| LE-46 | wo_completed | WO hoàn thành | state=completed | critical | 1 |
| LE-47 | wo_validated | WO validate | QMS validate | QMS-critical | 1 |
| LE-48 | wo_closed | WO đóng | state=closed | critical | 1 |
| LE-49 | wo_breach_sla | WO vi phạm SLA | breach detected | critical | 1 |
| LE-50 | wo_cancelled | WO hủy | state=cancelled | critical | 1 |

## D. Event Tích hợp / Hệ thống

| ID | Tên kỹ thuật | Hiển thị | Trigger | Audit | Wave |
|----|--------------|----------|---------|-------|------|
| LE-61 | integration_inbound_received | Inbound từ HIS/LIS | Webhook in | info | 2 |
| LE-62 | integration_outbound_sent | Outbound to ERP/Finance | Webhook out | info | 2 |
| LE-63 | data_migration_batch_loaded | Migration batch nạp | Migration job | critical | 1 |
| LE-64 | system_backup_completed | Backup xong | Cron | info | 1 |
| LE-65 | security_breach_detected | Phát hiện vi phạm bảo mật | SOC | critical | 1 |
| LE-66 | role_changed | Thay đổi role user | User Permission update | critical | 1 |

## E. Event Tài chính / Tài sản (đồng bộ ERPNext)

| ID | Tên kỹ thuật | Hiển thị | Trigger | Audit | Wave |
|----|--------------|----------|---------|-------|------|
| LE-71 | asset_capitalized | Nhập tài sản kế toán | ERPNext Asset state=in_use | critical | 1 |
| LE-72 | asset_depreciation_posted | Hạch toán khấu hao | Asset Depreciation Schedule run | info | 1 |
| LE-73 | asset_value_adjusted | Điều chỉnh giá trị | ERPNext Asset Value Adjustment | critical | 2 |
| LE-74 | asset_disposed_finance | Disposal kế toán | ERPNext Asset Disposal | critical | 2 |

## F. Quy tắc payload chuẩn (apply cho mọi event)

```jsonc
{
  "event_id": "LE-2026-00001234",     // Naming Series
  "event_type": "pm_completed",        // tên kỹ thuật
  "occurred_at": "2026-05-12T10:34:00+07:00",
  "actor_user_id": "user_xyz",
  "actor_role": "AC Technician",
  "subject_doctype": "AC Medical Asset",
  "subject_name": "MA-2026-0001",
  "source_doctype": "AC Work Order",
  "source_name": "WO-2026-000123",
  "payload": { /* fields khác nhau theo event_type */ },
  "evidence_refs": ["File/abc.pdf", "File/xyz.jpg"],
  "audit_class": "QMS-critical",
  "wave_introduced": 1
}
```

## G. Tổng số event Wave 1 (cần build engine handle)
- Asset Lifecycle: 8 events (LE-03 → LE-10)
- QMS: 4 events (LE-21, 22, 28, 32)
- WO Engine: 9 events (LE-41 → LE-49)
- Tích hợp/Hệ thống: 4 events
- Tài chính: 2 events

**Tổng Wave 1: ~27 event** mà engine phải handle, alert, snapshot.
