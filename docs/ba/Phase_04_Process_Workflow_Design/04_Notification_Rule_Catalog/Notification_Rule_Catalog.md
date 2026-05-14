> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# NOTIFICATION RULE CATALOG — ASSETCORE

**Phiên bản:** 1.0
**Owner:** BA Lead + IT Lead

---

## 1. Cơ chế
- Sử dụng Frappe Notification + custom DocType `AC Notification Template` (cho phép template HTML/SMS).
- Trigger: `event-based` (Lifecycle Event), `record-event` (DocType change), `schedule` (cron), `threshold` (KPI).
- Channel: in-app, email, SMS (W1.5), webhook.

## 2. Quy ước rule
- ID `NTF-XXX`.
- `name`, `trigger_type`, `trigger`, `recipients`, `channels`, `template`, `dedupe_key`, `quiet_hours`.

## 3. Asset Lifecycle

| ID | Trigger | Recipient | Channel |
|----|---------|-----------|---------|
| NTF-001 | LE-03 installed | KS BME + Asset Manager | in-app + email |
| NTF-002 | LE-04 commissioned | QMS Officer + Asset Manager + Trưởng khoa | in-app + email |
| NTF-003 | LE-06 released_for_use | Asset Manager + Trưởng khoa + Khoa lâm sàng | in-app + email |
| NTF-004 | LE-14 stand_down | Asset Manager + QMS + Trưởng khoa + Khoa | in-app + email |
| NTF-005 | LE-15 retired | Asset Manager + Finance + Pháp chế + QMS | in-app + email |
| NTF-006 | LE-16 disposed | Asset Manager + Finance + QMS | email |

## 4. Document / License

| ID | Trigger | Recipient | Channel |
|----|---------|-----------|---------|
| NTF-011 | Document submitted | Approver theo type | in-app + email |
| NTF-012 | Document approved | Owner + linked Asset custodian | in-app |
| NTF-013 | License expiry 90 ngày | Pháp chế + Asset Manager | email |
| NTF-014 | License expiry 60 ngày | Pháp chế + Asset Manager | email |
| NTF-015 | License expiry 30 ngày | Pháp chế + Asset Manager + Trưởng khoa | email |
| NTF-016 | License expiry 15 ngày | Pháp chế + Asset Manager + BGĐ phụ trách | email + in-app |
| NTF-017 | License expiry 7 ngày | Pháp chế + Asset Manager + BGĐ + QMS | email + in-app + (SMS W1.5) |
| NTF-018 | License đã hết hạn (Compliance Case) | Pháp chế + Asset Manager + QMS Lead + BGĐ | email + in-app |

## 5. PM / Calibration

| ID | Trigger | Recipient | Channel |
|----|---------|-----------|---------|
| NTF-021 | WO PM tạo (lead time) | Assignee (KTV/Vendor) + Trưởng khoa | in-app + email |
| NTF-022 | WO PM due trong 3 ngày | Assignee | in-app |
| NTF-023 | WO PM overdue | Assignee + KS BME trưởng | email + in-app |
| NTF-024 | LE-07 pm_completed | Asset Manager + QMS Officer | in-app |
| NTF-025 | WO Cal due trong 14 ngày | Cal Lab Eng / Vendor Cal + KS BME | email |
| NTF-026 | WO Cal Fail | QMS Officer + Asset Manager + Trưởng khoa | email + in-app |

## 6. CM / Failure

| ID | Trigger | Recipient | Channel |
|----|---------|-----------|---------|
| NTF-031 | Failure Report submit | KS BME on-call + Assignment | in-app + email |
| NTF-032 | Failure Critical | KS BME on-call + Phó VTTBYT | SMS (W1.5) + in-app |
| NTF-033 | WO CM assigned | Assignee | in-app + email |
| NTF-034 | WO CM SLA breach | Asset Manager + Phó VTTBYT | in-app + email |
| NTF-035 | LE-10 repaired | Reporter + Trưởng khoa | in-app |
| NTF-036 | LE-11 software_updated | Asset Manager + QMS | in-app |

## 7. CAPA / Compliance

| ID | Trigger | Recipient | Channel |
|----|---------|-----------|---------|
| NTF-041 | NC submitted | QMS Officer | in-app |
| NTF-042 | CAPA assigned | Owner + Approver | in-app + email |
| NTF-043 | CAPA action due | Action owner | in-app |
| NTF-044 | CAPA action overdue | Action owner + QMS Lead | email |
| NTF-045 | CAPA close | QMS Lead + linked Asset/WO/Doc | in-app |
| NTF-046 | Compliance Case opened | QMS Officer + Trưởng QLCL | in-app + email |
| NTF-047 | Recall confirmed | QMS Lead + BGĐ + Pháp chế + Asset Manager | email + in-app |

## 8. Asset Movement / Stand-Down / Decommission

| ID | Trigger | Recipient | Channel |
|----|---------|-----------|---------|
| NTF-051 | Asset Movement submitted | Trưởng khoa cũ + mới + Asset Manager | in-app + email |
| NTF-052 | Movement approved | Receivers | in-app |
| NTF-053 | Stand-Down submitted | Asset Manager + QMS | in-app + email |
| NTF-054 | Decommission submitted | KTTC + Pháp chế + QMS + BGĐ | email |
| NTF-055 | Disposal completed | KTTC + Pháp chế + QMS | email |

## 9. KPI / Dashboard threshold

| ID | Trigger | Recipient | Channel |
|----|---------|-----------|---------|
| NTF-061 | Open CAPA > 50 | QMS Lead | email |
| NTF-062 | PM compliance < 80% | Asset Manager | email |
| NTF-063 | Vendor SLA breach > 5/tháng | Procurement + Asset Manager | email |
| NTF-064 | License expired & in-use > 0 | BGĐ + Asset Manager + QMS | email + in-app |

## 10. System / Security

| ID | Trigger | Recipient | Channel |
|----|---------|-----------|---------|
| NTF-071 | LE-65 security_breach | IT Lead + ATTT | email + in-app + (SMS) |
| NTF-072 | Backup fail | IT Admin | email |
| NTF-073 | Outbox dispatcher backlog > N | IT Admin | email + in-app |

## 11. Quy tắc dedupe & quiet hours

- **Dedupe key:** kết hợp `(rule_id, subject_doctype, subject_name, period)` để không spam cùng nội dung.
- **Quiet hours:** mặc định 22:00 → 06:00 chỉ gửi alert Critical real-clock; còn lại defer sáng.
- **Per-user preference:** user có thể opt-out kênh email/SMS cho rule không Critical.

## 12. Template chuẩn (ví dụ NTF-017)

```
Subject: [AssetCore] License sắp hết hạn — {{asset_code}} (còn {{days_left}} ngày)

Kính gửi {{recipient_name}},

Giấy phép {{document_no}} của thiết bị {{asset_code}} ({{device_model}}) tại {{location}} sẽ hết hạn ngày {{expiry_date}} (còn {{days_left}} ngày).

Vui lòng:
- Kiểm tra và gia hạn nếu cần.
- Hoặc đề xuất stand-down/replace.

Truy cập hồ sơ: {{deep_link}}

— AssetCore
```

## 13. Tiêu chí nghiệm thu
- 70+ rule baseline hoạt động Wave 1.
- Dedupe + quiet hours hoạt động.
- Test all template render đúng.
- Per-user preference tested.
- SMS gateway integration test pass (W1.5).
