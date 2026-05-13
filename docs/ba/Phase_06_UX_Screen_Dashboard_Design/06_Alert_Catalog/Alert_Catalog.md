> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# ALERT CATALOG — ASSETCORE

**Phiên bản:** 1.0
**Owner:** BA Lead + IT Lead

---

## 1. Phân loại Alert
- **Schedule alerts:** cron-based (ví dụ License expiring 90 ngày).
- **Event alerts:** Lifecycle Event-driven (Failure Critical).
- **Threshold alerts:** Metric/KRI vượt ngưỡng.

## 2. Schedule Alerts

| ID | Trigger | Frequency | Recipient | Channel |
|----|---------|-----------|-----------|---------|
| ALR-S-01 | License expiring 90 ngày | daily | Pháp chế + Asset Manager | Email |
| ALR-S-02 | License expiring 60 ngày | daily | + email | Email |
| ALR-S-03 | License expiring 30 ngày | daily | + Trưởng khoa | Email + in-app |
| ALR-S-04 | License expiring 15 ngày | daily | + BGĐ phụ trách | Email + in-app |
| ALR-S-05 | License expiring 7 ngày | daily | + QMS Lead | Email + in-app + (SMS) |
| ALR-S-06 | PM due trong 14 ngày | daily | KS BME / Vendor SE | In-app |
| ALR-S-07 | PM overdue | daily | + KS BME trưởng | Email + in-app |
| ALR-S-08 | Cal due trong 14 ngày | daily | Cal Lab Eng / Vendor Cal | Email |
| ALR-S-09 | Cal overdue | daily | + Trưởng VTTBYT + QMS | Email |
| ALR-S-10 | QMS Artifact next_review trong 30 ngày | daily | Owner | Email |
| ALR-S-11 | CAPA action due hôm nay | daily | Action owner | In-app |
| ALR-S-12 | CAPA action overdue | daily | + QMS Lead | Email |
| ALR-S-13 | Effectiveness check timepoint hôm nay | daily | Assessor | In-app |
| ALR-S-14 | Backup status report | daily | IT Admin | Email |
| ALR-S-15 | DR drill schedule reminder | quarterly | IT Lead | Email |
| ALR-S-16 | Internal audit schedule | quarterly | QMS Lead | Email |
| ALR-S-17 | Management Review schedule | bi-annual | BGĐ + QMS Lead | Email |
| ALR-S-18 | Risk review due | per cycle | Risk Owner | In-app |
| ALR-S-19 | Snapshot KPI monthly | end of month | BA Lead | Email |
| ALR-S-20 | Migration data quality issue summary | weekly | Migration Lead | Email |

## 3. Event Alerts

| ID | Trigger event | Recipient | Channel |
|----|---------------|-----------|---------|
| ALR-E-01 | LE-09 failure_reported severity=Critical | KS BME on-call + Phó VTTBYT | (SMS) + in-app + Email |
| ALR-E-02 | LE-10 repaired | Reporter + Trưởng khoa + Asset Manager | In-app |
| ALR-E-03 | LE-12 recalled | QMS Lead + BGĐ + Pháp chế + Asset Manager | Email + in-app |
| ALR-E-04 | LE-22 capa_opened | QMS Lead + linked owner | In-app |
| ALR-E-05 | LE-25 capa_closed | QMS Lead + Asset Manager | In-app |
| ALR-E-06 | LE-49 wo_breach_sla | Asset Manager + Phó VTTBYT | Email + in-app |
| ALR-E-07 | LE-65 security_breach_detected | IT Lead + ATTT + BGĐ | (SMS) + Email + in-app |
| ALR-E-08 | LE-32 risk_entry_created (Critical) | QMS Lead + Risk Owner | In-app |
| ALR-E-09 | LE-30 change_control_approved | All affected users | In-app |
| ALR-E-10 | LE-15/16 retired/disposed | Asset Manager + KTTC + Pháp chế + QMS | Email |
| ALR-E-11 | LE-04 commissioned | Asset Manager + QMS + Trưởng khoa | In-app |
| ALR-E-12 | LE-06 released_for_use | Asset Manager + Trưởng khoa + Khoa | In-app |
| ALR-E-13 | LE-21 nc_opened severity=1 | QMS Lead | In-app |
| ALR-E-14 | LE-26 compliance_case_opened | QMS Lead + Trưởng QLCL | In-app |

## 4. Threshold Alerts (KRI-based)

| ID | Trigger | Recipient | Channel |
|----|---------|-----------|---------|
| ALR-T-01 | KRI-003 License Expired & In-Use ≥ 1 | BGĐ + Asset Manager + QMS + Pháp chế | Email + in-app |
| ALR-T-02 | KRI-004 PM Compliance < 80% (tháng) | Asset Manager + QMS Lead | Email |
| ALR-T-03 | KRI-005 CAPA Effectiveness fail rate > 20% | QMS Lead + Trưởng QLCL | Email |
| ALR-T-04 | KRI-008 Outbox dispatcher backlog > N | IT Admin | Email + in-app |
| ALR-T-05 | Open CAPA count > 50 | QMS Lead | Email |
| ALR-T-06 | Vendor SLA breach > 5/tháng | Procurement + Asset Manager | Email |
| ALR-T-07 | Recall in progress > 7 ngày | QMS Lead + BGĐ | In-app |
| ALR-T-08 | DQ issue critical > 10/ngày | Migration Lead + Data Architect | Email |

## 5. Quiet hours & dedupe
- Quiet hours mặc định 22:00–06:00; chỉ gửi alert Critical real-clock.
- Dedupe key: rule_id + subject + period (tránh spam).
- Per-user opt-out kênh (trừ Critical).

## 6. Escalation
- Mỗi alert cấp Critical real-clock có tối đa 3 cấp escalation:
  - Cấp 1: cấp dưới trực tiếp.
  - Cấp 2: cấp trên (Phó/Trưởng).
  - Cấp 3: BGĐ phụ trách.
- Time gap: 15/30/60 phút (configurable).

## 7. Audit alert delivery
- Mỗi alert ghi log: rule_id, recipient, channel, sent_at, delivery_status, ack_at.
- Failed delivery → retry 3 lần, nếu vẫn fail → cảnh báo IT.

## 8. Tiêu chí nghiệm thu Alert Catalog
- 50+ alert rule baseline Wave 1.
- Schedule + Event + Threshold tested.
- Escalation chain test pass.
- Dedupe + quiet hours hoạt động.
- Audit log alert delivery đầy đủ.
