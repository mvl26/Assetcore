> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# NOTIFICATION & SLA RULE INDEX — WAVE 1

**Tham chiếu:**
- SLA Catalog (business): Phase_01/09.
- SLA Engine (technical): Phase_04/03.
- Notification Rule: Phase_04/04.
- Alert Catalog: Phase_06/06.

---

## 1. SLA Rules Wave 1

| Group | Count | ID range |
|-------|-------|----------|
| Failure → WO assigned | 4 | SLAR-001..004 |
| WO CM open → repaired | 4 | SLAR-011..014 |
| PM | 2 | SLAR-021..022 |
| Calibration | 3 | SLAR-031..033 |
| Document | 3 | SLAR-041..043 |
| QMS / CAPA / Compliance | 5 | SLAR-051..055 |
| Workflow approval generic | 4 | SLAR-061..064 |

**Tổng: 25 SLA rules baseline Wave 1.**

## 2. Notification Rules Wave 1

| Group | Count | ID range |
|-------|-------|----------|
| Asset Lifecycle | 6 | NTF-001..006 |
| Document / License | 8 | NTF-011..018 |
| PM / Calibration | 6 | NTF-021..026 |
| CM / Failure | 6 | NTF-031..036 |
| CAPA / Compliance | 7 | NTF-041..047 |
| Asset Movement / EoL | 5 | NTF-051..055 |
| KPI threshold | 4 | NTF-061..064 |
| System / Security | 3 | NTF-071..073 |

**Tổng: ~ 45 notification rules baseline Wave 1.**

## 3. Alerts Wave 1

| Group | Count | ID range |
|-------|-------|----------|
| Schedule | 20 | ALR-S-01..20 |
| Event | 14 | ALR-E-01..14 |
| Threshold | 8 | ALR-T-01..08 |

**Tổng: 42 alert rules baseline Wave 1.**

## 4. Implementation guidance

### SLA Rules
- DocType `AC SLA Rule`.
- Background worker `assetcore.sla.monitor` chạy mỗi phút.
- JSON config: subject_doctype, filter, start/stop fields, target, business_clock, escalation steps.
- Lifecycle Event `LE-49 wo_breach_sla` khi vi phạm.

### Notification Rules
- DocType `AC Notification Template` + Frappe Notification.
- Trigger types: event-based, record-event, schedule, threshold.
- Channels: email, in-app, SMS (W1.5), webhook.
- Dedupe key + quiet hours.

### Alerts
- DocType `AC Alert Rule` (Phase_02/Metric_Dashboard_Engine_Spec §2.4).
- Dispatcher với escalation chain.
- Audit log delivery.

## 5. Testing
- SLA test với mock time (freezegun).
- Notification test render template + dedupe.
- Escalation chain test pass cho mọi level.

## 6. Tiêu chí nghiệm thu
- 25 SLA + 45 Notification + 42 Alert rules baseline configured.
- Background worker chạy mỗi phút độ trễ ≤ 30s.
- Audit log delivery 100%.
- Test pass.
