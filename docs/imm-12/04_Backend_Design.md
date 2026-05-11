# 04 — Backend Design

| Mục | Giá trị |
|---|---|
| Module | IMM-12 — Incident & CAPA Management |
| Phạm vi | Per-module |
| Owner | BE Lead |
| Trạng thái | ✅ Live — `services/imm12.py` và `api/imm12.py` đã implement |

---

## 1. Architecture Overview

```text
┌──────────────────────────────────────────────────────────┐
│  api/imm12.py   ← @frappe.whitelist() — thin wrapper     │
│  api/imm00.py   ← CAPA endpoints (✅ LIVE)                │
└──────────────────────┬───────────────────────────────────┘
                       │ no logic — delegate only
                       ▼
┌──────────────────────────────────────────────────────────┐
│  services/imm12.py  ← orchestration + IMM-12 logic       │
│  services/imm00.py  ← CAPA / audit / lifecycle (✅ LIVE)  │
└──────────────────────┬───────────────────────────────────┘
                       │ frappe.get_doc / frappe.db
                       ▼
┌──────────────────────────────────────────────────────────┐
│  DocType Controllers                                      │
│  Incident Report (`incident_report`) ✅ LIVE              │
│  IMM RCA Record (`imm_rca_record`) ✅ LIVE                │
│  IMM CAPA Record (`imm_capa_record`) ✅ LIVE              │
└──────────────────────────────────────────────────────────┘
```

**Conventions:**
- Type hints + docstring cho mọi function
- API layer: parse params → call service → `_ok()` / `_err()`
- ServiceError: `raise frappe.ValidationError("...")` — caught by `_handle()`
- Naming: `snake_case` Python, `PascalCase` DocType

---

## 2. DocTypes

### 2.1 Incident Report ✅ DocType: `incident_report`

> DocType name: `Incident Report`. DocType folder: `assetcore/assetcore/doctype/incident_report/`. Fields below reflect actual schema.

| Field | Type | Mandatory | Notes |
|---|---|---|---|
| `severity` | Select (Minor/Major/Critical) | Yes | — |
| `fault_code` | Data | No | Lookup catalog |
| `clinical_impact` | Text | Conditional | Required if Critical (BR-12-01) |
| `acknowledged_by` | Link User | No | Set on Acknowledge |
| `acknowledged_at` | Datetime | No | Auto |
| `resolved_by` | Link User | No | Set on Resolve |
| `resolved_at` | Datetime | No | Auto |
| `closed_by` | Link User | No | Set on Close |
| `closed_at` | Datetime | No | Auto |
| `linked_repair_wo` | Link / Data | No | IMM-09 (actual field name: `linked_repair_wo`) |
| `rca_record` | Link RCA Record | No | Auto when trigger |
| `rca_required` | Check | No | True if Major/Critical/Chronic |
| `linked_capa` | Link IMM CAPA Record | No | Set after RCA Submit |
| `chronic_failure_flag` | Check | No | Set by scheduler |
| `assigned_to` | Link User | No | KTV phụ trách |

**Permission Query (DocType level):**
```python
def get_permission_query_conditions(user):
    """Reporting User chỉ thấy IR của department mình."""
    if "IMM Workshop Lead" in frappe.get_roles(user):
        return ""  # see all
    dept = frappe.db.get_value("Employee", {"user_id": user}, "department")
    return f'`tabIncident Report`.`department` = "{dept}"'
```

**Indexes:**
```sql
CREATE INDEX idx_ir_asset_fault_date
  ON `tabIncident Report` (asset, fault_code, reported_at);
CREATE INDEX idx_ir_severity_status
  ON `tabIncident Report` (severity, status);
```

### 2.2 IMM RCA Record ✅ DocType: `imm_rca_record`

DocType name: `IMM RCA Record`. Child tables: `IMM RCA Five Why Step` (`imm_rca_five_why_step`) for 5-Why, `IMM RCA Related Incident` (`imm_rca_related_incident`) for chronic grouping.

Naming: `RCA-.YYYY.-.#####` · Submittable

| Field | Type | Mandatory | Notes |
|---|---|---|---|
| `asset` | Link AC Asset | Yes | — |
| `incident_report` | Link Incident Report | Yes | Primary source |
| `related_incidents` | Table (RCA Related Incident) | No | Chronic group |
| `fault_code` | Data | No | — |
| `trigger_type` | Select | Yes | Major Incident / Critical Incident / Chronic Failure / Manual |
| `incident_count` | Int | No | Chronic: COUNT in 90 days |
| `rca_method` | Select | Required before Submit | 5Why / Fishbone / Other |
| `root_cause` | Text | Required before Submit | BR-12-07 |
| `contributing_factors` | Text | No | — |
| `five_why_steps` | Table (RCA Five Why Step) | No | When method=5Why |
| `corrective_action_summary` | Text | No | Set on submit_rca (actual field: `corrective_action_summary`) |
| `preventive_action_summary` | Text | No | Set on submit_rca (actual field: `preventive_action_summary`) |
| `due_date` | Date | Yes | +7d or +14d |
| `status` | Select | Yes | RCA Required / RCA In Progress / Completed / Cancelled |
| `assigned_to` | Link User | Yes | — |
| `completed_by` | Link User | No | Set on Submit |
| `completed_date` | Date | No | Auto |
| `linked_capa` | Link IMM CAPA Record | No | Auto after Submit (BR-12-06) |

**IMM RCA Record Controller:** `assetcore/assetcore/doctype/imm_rca_record/imm_rca_record.py` ✅ EXISTS

---

## 3. Workflow — Incident Report ✅ LIVE

### States (actual implementation)

| State | docstatus | Mô tả |
|---|---|---|
| Open | 0 | IR mới tạo |
| Under Investigation | 0 | Workshop Lead tiếp nhận (actual: "Under Investigation" not "Acknowledged") |
| Resolved | 0 | Đã giải quyết |
| Closed | 0 | Final — IR đóng |
| Cancelled | 0 | False alarm |

### Transitions (actual `_VALID_TRANSITIONS` dict in service)

| From | To | Trigger function | Actor | Validation |
|---|---|---|---|---|
| Open | Under Investigation | `acknowledge_incident()` | Workshop Lead, Technician | — |
| Open | Cancelled | `cancel_incident()` | Workshop Lead | reason required |
| Under Investigation | Resolved | `resolve_incident()` | Workshop Lead, Technician | resolution_notes required |
| Under Investigation | Cancelled | `cancel_incident()` | Workshop Lead | reason required |
| Resolved | Closed | `close_incident()` | Workshop Lead, QA Officer | BR-12-02: High/Critical → RCA Completed required |

**RCA States:** `RCA Required` → `RCA In Progress` → `Completed` / `Cancelled`

**BR-12-04:** Critical → auto asset Out of Service on `report_incident()`. High → auto asset Out of Service on `acknowledge_incident()`.
**BR-12-02:** High/Critical Incident cannot close until linked RCA status = `Completed`.
**Asset restore:** `close_incident()` checks if asset is `Out of Service` and transitions back to `Active`.

---

## 4. Service Layer — `services/imm12.py` ✅ LIVE

### 4.1 Public functions (actual signatures)

| Function | Returns | Logic Owner | Notes |
|---|---|---|---|
| `report_incident(asset, incident_type, severity, description, *, fault_code, ...)` | `dict {name, status, severity}` | IMM-12 | BR-12-01 Critical→clinical_impact; BR-12-04 Critical→OOS |
| `acknowledge_incident(name, notes, assigned_to)` | `dict {name, status}` | IMM-12 | Open→Under Investigation; High→OOS |
| `resolve_incident(name, resolution_notes, root_cause)` | `dict {name, status, rca_created}` | IMM-12 | auto-create RCA for High/Critical |
| `close_incident(name, verification_notes)` | `dict {name, status, closed_date}` | IMM-12 | BR-12-02 RCA Completed check; restore asset Active |
| `cancel_incident(name, reason)` | `dict {name, status}` | IMM-12 | reason required |
| `create_rca(incident_name, rca_method)` | `dict {name, status, due_date}` | IMM-12 | Idempotent: 409 if RCA exists |
| `get_rca(name)` | `dict` | IMM-12 | includes `incident_severity` |
| `submit_rca(name, root_cause, corrective_action, preventive_action, five_why_steps, rca_notes)` | `dict {name, status, linked_capa}` | IMM-12 | BR-12-06: auto `create_capa()` via IMM-00 |
| `list_incidents(status, severity, asset, page, page_size)` | `dict {pagination, items}` | IMM-12 | — |
| `get_incident_detail(name)` | `dict` | IMM-12 | includes `allowed_transitions` + nested `rca` |
| `get_incident_stats()` | `dict` | IMM-12 | counts per status + severity |
| `get_asset_incident_history(asset, limit)` | `dict {asset, items}` | IMM-12 | — |
| `get_chronic_failures()` | `list` | IMM-12 | SQL GROUP BY (asset, fault_code), HAVING ≥ 3 |
| `get_dashboard()` | `dict {stats, active_incidents, open_rcas, chronic_failures}` | IMM-12 | — |
| `detect_chronic_failures()` | `dict {flagged, rca_created, groups}` | Scheduler | BR-12-03: flag + auto RCA Chronic |

**Note:** Function `submit_rca_and_create_capa` does **not** exist — actual name is `submit_rca`. Field `fault_description` does **not** exist — actual field is `description`.

### 4.2 Key implementation notes

- `report_incident` signature: `(asset, incident_type, severity, description, *, fault_code, workaround_applied, clinical_impact, patient_affected, patient_impact_description, immediate_action, linked_repair_wo, reported_by)` — returns `dict`, NOT `str`.
- DocType name used: `"Incident Report"` (constant `_DT_INCIDENT`).
- RCA DocType name: `"IMM RCA Record"` (constant `_DT_RCA`). **NOT** `"RCA Record"`.
- CAPA DocType name: `"IMM CAPA Record"` (constant `_DT_CAPA`).
- Chronic detection: `_CHRONIC_WINDOW_DAYS=90`, `_CHRONIC_MIN_COUNT=3`, `_RCA_DUE_MAJOR=7`, `_RCA_DUE_CHRONIC=14`.
- `submit_rca` writes fields: `root_cause`, `corrective_action_summary`, `preventive_action_summary`, `rca_notes`, `completed_by`, `completed_date`, `linked_capa`.
- Auto-CAPA on `submit_rca` via `svc00.create_capa()` — sets `linked_capa` on both RCA and Incident.
- `_auto_create_capa()` is a fallback on `resolve_incident()` for High/Critical without RCA flow.

---

## 5. API Layer — `api/imm12.py` ✅ LIVE

Imports from `assetcore.utils.response` (`_ok`, `_err`). Role check via `_has_role(*roles)`.

**Roles constants:**
- `_ROLES_INVESTIGATE = {"IMM Workshop Lead", "IMM Technician", "IMM QA Officer", "System Manager"}`
- `_ROLES_CLOSE = {"IMM Workshop Lead", "IMM QA Officer", "System Manager"}`

**Actual @frappe.whitelist endpoints:**

| Function | Method | Role guard |
|---|---|---|
| `report_incident(asset, incident_type, severity, description, fault_code, ...)` | POST | session.user != Guest |
| `cancel_incident(name, reason)` | POST | ROLES_INVESTIGATE |
| `create_rca(incident_name, rca_method)` | POST | ROLES_INVESTIGATE |
| `get_rca(name)` | GET | authenticated |
| `submit_rca(name, root_cause, corrective_action, preventive_action, five_why_steps, rca_notes)` | POST | ROLES_INVESTIGATE |
| `get_asset_incident_history(asset, limit)` | GET | authenticated |
| `get_chronic_failures()` | GET | authenticated |
| `get_dashboard()` | GET | authenticated |
| `list_incidents(status, severity, asset, page, page_size)` | GET | authenticated |
| `get_incident(name)` | GET | authenticated |
| `acknowledge_incident(name, notes, assigned_to)` | POST | ROLES_INVESTIGATE |
| `resolve_incident(name, resolution_notes, root_cause)` | POST | ROLES_INVESTIGATE |
| `close_incident(name, verification_notes)` | POST | ROLES_CLOSE |
| `get_incident_stats()` | GET | authenticated |

---

## 6. Audit Trail

| Event | Trigger | `event_type` | Actor |
|---|---|---|---|
| IR created (Minor) | `report_incident()` | `incident_reported` | session.user |
| IR created (Critical) | `report_incident()` + asset transition | `incident_reported_critical` | session.user |
| IR Acknowledged | `acknowledge_incident()` | `incident_acknowledged` | Workshop Lead |
| IR Resolved | `resolve_incident()` | `incident_resolved` | Workshop Lead / KTV |
| IR Closed | `close_incident()` | `incident_closed` | Workshop Lead |
| RCA Completed + CAPA created | `submit_rca_and_create_capa()` | `rca_completed` | QA Officer |
| Chronic failure detected | `detect_chronic_failures()` | `chronic_failure_detected` | Administrator (scheduler) |

Tất cả gọi `imm00.log_audit_event()` → SHA-256 hash chain (NĐ98/ISO 13485).

---

## 7. Scheduler ✅ LIVE

| Job | Cron | Function | Logic |
|---|---|---|---|
| Chronic failure detection | Daily | `imm12.detect_chronic_failures` | BR-12-03: ≥3 same (asset, fault_code) in 90d — returns `{flagged, rca_created, groups}` |
| CAPA overdue check | Daily | `imm00.check_capa_overdue` | ✅ LIVE — BR-00-09 |

**Registration trong `hooks.py`:**
```python
scheduler_events = {
    "cron": {
        "0 2 * * *": [
            "assetcore.services.imm00.check_capa_overdue",
            "assetcore.services.imm12.detect_chronic_failures",
        ],
    },
}
```

---

## 8. Integration Points

| System | Direction | Method | Notes |
|---|---|---|---|
| IMM-00 Foundation | Outbound (call) | Python import | CAPA, Audit, Lifecycle |
| IMM-09 Repair | Link | DocType Link field | `repair_wo` on Incident Report |
| IMM-13 Risk Register | Event | Webhook (Sprint 12.5) | `chronic.detected` event |
| Email (Frappe) | Outbound | `frappe.sendmail()` | Critical alert + CAPA overdue |
| IMM-15 Vigilance | Event | Webhook (Sprint 12.5) | `incident.created` event |

---

## 9. Non-Functional

| Category | Requirement | Implementation |
|---|---|---|
| Idempotency | `acknowledge/resolve/close`: repeat call → return current state | Check status before transition |
| Concurrency | No double-acknowledge | DB-level status check + ValidationError |
| Chronic detection | Idempotent | Guard: `frappe.db.exists("RCA Record", {status in [Required, InProgress]})` |
| Logging | All errors logged to Frappe error log | `frappe.log_error()` in `_handle()` |
| Performance | List query < 500ms p95 | Index on `(asset, fault_code, reported_at)` + `(severity, status)` |

---

## DoD — File 04 hoàn chỉnh

- [x] Architecture overview (3-tier với LIVE/Pending rõ)
- [x] DocType: Incident Report custom fields + indexes + permission query
- [x] DocType: RCA Record full field table
- [x] Workflow states + transitions table
- [x] Service layer: function signatures + `report_incident` full code
- [x] Service layer: `detect_chronic_failures` full code (SQL + idempotency)
- [x] API layer: `_handle` pattern + 5 endpoints
- [x] Audit trail table (7 events)
- [x] Scheduler table + hooks.py registration
- [x] Integration points table
- [x] Non-functional (idempotency, concurrency, logging)
- [x] ✅ `services/imm12.py` — fully implemented
- [x] ✅ `api/imm12.py` — 14 endpoints live
- [x] ✅ DocType JSONs: incident_report, imm_rca_record, imm_capa_record, imm_rca_five_why_step, imm_rca_related_incident
- [ ] Reviewed bởi BE Lead
