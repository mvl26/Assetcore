> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# SLA & ESCALATION RULE CATALOG — ASSETCORE

**Phiên bản:** 1.0
**Owner:** BA Lead + IT Lead
**Tham chiếu:** Phase_01/09 SLA Catalog (kinh doanh) — tài liệu này thiên về **kỹ thuật cài đặt**.

---

## 1. Cơ chế chung
Mỗi rule có:
- `rule_id` (`SLAR-XXX`)
- `subject_doctype` + `subject_filter`
- `start_field` (datetime), `stop_field` (datetime)
- `target_minutes` hoặc `target_hours`
- `business_clock` (true/false): tính giờ hành chính theo `AC Holiday Calendar`
- `pause_field_table` (cho WO có pause window)
- `breach_action` (notify / create_compliance_case / escalate)
- `escalation_steps` (array: after_minutes, recipient_type, channel)

## 2. Cài đặt trong Frappe
- Sử dụng custom DocType `AC SLA Rule` để lưu definition.
- Background worker `assetcore.sla.monitor` chạy mỗi phút.
- Scan các record open có `sla_due_at` < now → set `sla_breached=true` + publish LE-49.
- Escalation: dispatcher xử lý theo step.

## 3. SLA Rule Catalog (Wave 1)

### 3.1 Failure Report → WO assigned
| ID | Subject | Trigger Start | Trigger Stop | Target | Clock | Breach Action |
|----|---------|----------------|---------------|--------|-------|----------------|
| SLAR-001 | AC Failure Report (severity=Critical) | reported_at | linked_wo.assigned_at | 30 phút | real | LE-49 + escalate |
| SLAR-002 | Severity=High | reported_at | – | 2h | business | – |
| SLAR-003 | Severity=Medium | reported_at | – | 1 ngày | business | – |
| SLAR-004 | Severity=Low | reported_at | – | 3 ngày | business | – |

**Escalation SLAR-001:**
- 15' không assigned → notify Phó VTTBYT.
- 30' không assigned → notify Trưởng VTTBYT.
- 60' không assigned → notify BGĐ phụ trách + open Compliance Case.

### 3.2 WO CM open → repaired
| ID | Subject | Start | Stop | Target | Clock | Action |
|----|---------|-------|------|--------|-------|--------|
| SLAR-011 | WO CM Critical | failure_reported_at | repaired_at | 24h | real | LE-49 + Compliance Case |
| SLAR-012 | WO CM High | – | – | 3 ngày | business | – |
| SLAR-013 | WO CM Medium | – | – | 7 ngày | business | – |
| SLAR-014 | WO CM Low | – | – | 30 ngày | business | – |

### 3.3 PM
| ID | Subject | Start | Stop | Target |
|----|---------|-------|------|--------|
| SLAR-021 | PM due → completed | pm_plan.next_due | wo.completed_at | 7 ngày business |
| SLAR-022 | PM completed → validated | wo.completed_at | wo.validated_at | 3 ngày business |

### 3.4 Calibration
| ID | Subject | Start | Stop | Target |
|----|---------|-------|------|--------|
| SLAR-031 | Cal due → completed | calibration_plan.next_due | wo.completed_at | 14 ngày business |
| SLAR-032 | Cal cert phát hành | wo.completed_at | doc.uploaded_at | 3 ngày business |
| SLAR-033 | Cal Fail → CAPA | cal.result_at | capa.opened_at | 1 ngày |

### 3.5 Document
| ID | Subject | Start | Stop | Target |
|----|---------|-------|------|--------|
| SLAR-041 | License expiry alert (90/60/30/15/7 ngày) | – | – | schedule |
| SLAR-042 | Document review | submitted_at | review_at | 2 ngày |
| SLAR-043 | Document approve | review_at | approved_at | 3 ngày |

### 3.6 QMS / CAPA / Compliance
| ID | Subject | Target |
|----|---------|--------|
| SLAR-051 | NC sev1 → CAPA opened | 24h |
| SLAR-052 | NC sev2 → CAPA opened | 5 ngày |
| SLAR-053 | CAPA action overdue | 7 ngày → escalate QMS Lead |
| SLAR-054 | CAPA effectiveness check | per timepoint plan |
| SLAR-055 | Recall disclosure to Bộ Y tế | 48h real-clock |

### 3.7 Workflow approval generic
| ID | Subject | Target |
|----|---------|--------|
| SLAR-061 | PM Plan submit → approve | 5 ngày |
| SLAR-062 | CAPA submit → approve | 3 ngày |
| SLAR-063 | Asset Movement chain | 5 ngày total |
| SLAR-064 | Decommission chain | 14 ngày |

## 4. Rule example (JSON)

```json
{
  "rule_id": "SLAR-011",
  "subject_doctype": "AC Work Order",
  "subject_filter": {"wo_type": "CM", "priority": "Critical"},
  "start_field": "failure_reported_at",
  "stop_field": "repaired_at",
  "target_hours": 24,
  "business_clock": false,
  "pause_field_table": "pause_log",
  "breach_action": ["set_sla_breached", "publish_LE49", "create_compliance_case"],
  "escalation_steps": [
    {"after_hours": 12, "recipient_role": "AC Asset Manager", "channel": "in_app"},
    {"after_hours": 24, "recipient_role": "AC Asset Manager", "channel": "email"},
    {"after_hours": 30, "recipient_role": "AC Executive Viewer", "channel": "email"}
  ]
}
```

## 5. Escalation channels
- **In-app:** Frappe Notification.
- **Email:** Frappe Email Queue + template.
- **SMS (Wave 1.5):** gateway nội bộ (Viettel/MobiFone) — chỉ cho rule SLA real-clock.
- **Webhook:** outbound tới hệ thống bên ngoài (vd Slack/Teams).

## 6. Pause window
- Hợp lệ pause = (paused_from, paused_to) nằm trong vòng đời WO.
- Quá 7 ngày pause cùng lúc → cần lý do + approval Trưởng VTTBYT.

## 7. Holiday Calendar
- Mỗi BV có thể cấu hình ngày nghỉ; SLA business_clock áp dụng.
- Cron load lịch nghỉ hằng năm.

## 8. KPI từ SLA
- MET-W1-011 Vendor SLA breach.
- MET-W1-021 Time-to-assign WO Critical.
- MET-W1-005 Downtime hours.

## 9. Tiêu chí nghiệm thu
- Background SLA monitor chạy mỗi phút, độ trễ ≤ 30s.
- 0 false positive breach trong test.
- Escalation chain test pass (real + business clock).
- Pause window tính đúng.
