# 05 — API Specification

| Mục | Giá trị |
|---|---|
| Module | IMM-12 — Incident & CAPA Management |
| Phạm vi | Per-module |
| Owner | BE Lead |
| Base URL | `/api/method/assetcore.api.imm12.<function>` |
| Auth | Frappe session HOẶC `Authorization: token <key>:<secret>` |
| Cập nhật | 2026-05-14 |
| Trạng thái | ✅ Live — `assetcore/api/imm12.py` deployed (14 endpoint) |

---

## 0. API Catalog

✅ Tất cả IMM-12 endpoint đã implement trong `assetcore/api/imm12.py`.

| # | Endpoint (actual @frappe.whitelist name) | Method | Mô tả | Role guard | US |
|---|---|---|---|---|---|
| 1 | `assetcore.api.imm12.report_incident` | POST | Tạo Incident Report | authenticated | US-12-01 |
| 2 | `assetcore.api.imm12.get_incident` | GET | Chi tiết 1 IR (calls `get_incident_detail`) | authenticated | US-12-07 |
| 3 | `assetcore.api.imm12.list_incidents` | GET | List IR với filter + pagination | authenticated | US-12-07 |
| 4 | `assetcore.api.imm12.acknowledge_incident` | POST | Open → Acknowledged (hoặc → In Progress) | ROLES_INVESTIGATE | US-12-02 |
| 5 | `assetcore.api.imm12.resolve_incident` | POST | In Progress → Resolved + auto RCA cho High/Critical | ROLES_INVESTIGATE | US-12-02 |
| 6 | `assetcore.api.imm12.close_incident` | POST | Resolved → Closed (validate RCA Completed) | ROLES_CLOSE | US-12-02 |
| 7 | `assetcore.api.imm12.cancel_incident` | POST | Huỷ IR (false alarm) | ROLES_INVESTIGATE | US-12-02 |
| 8 | `assetcore.api.imm12.create_rca` | POST | Tạo IMM RCA Record liên kết IR | ROLES_INVESTIGATE | US-12-03 |
| 9 | `assetcore.api.imm12.get_rca` | GET | Chi tiết 1 IMM RCA Record | authenticated | US-12-07 |
| 10 | `assetcore.api.imm12.submit_rca` | POST | Submit RCA → auto create IMM CAPA Record | ROLES_INVESTIGATE | US-12-03 |
| 11 | `assetcore.api.imm12.get_chronic_failures` | GET | Danh sách asset chronic (≥3/90d) | authenticated | US-12-04 |
| 12 | `assetcore.api.imm12.get_dashboard` | GET | Dashboard: stats + active + rcas + chronic | authenticated | US-12-05 |
| 13 | `assetcore.api.imm12.get_incident_stats` | GET | KPI counts per status+severity | authenticated | US-12-05 |
| 14 | `assetcore.api.imm12.get_asset_incident_history` | GET | Incident history của 1 asset | authenticated | US-12-07 |

---

## 1. Quy ước chung

### 1.1. Response success — format chuẩn AssetCore

```jsonc
{
  "success": true,
  "data": <payload — object / array / null>
}
```

FE đọc `response.data.data` (axios + Frappe lớp ngoài đã wrap).

**HTTP status:** Frappe luôn trả HTTP 200. Phân biệt success/error qua field `success`.

### 1.2. Response error — format chuẩn

```jsonc
{
  "success": false,
  "error": "Thông báo lỗi tiếng Việt",
  "code": "BUSINESS_RULE",
  "fields": {
    "clinical_impact": "Sự cố Critical bắt buộc mô tả tác động lâm sàng"
  }
}
```

### 1.3. Error code catalog

| Code | Khi nào |
|---|---|
| `NOT_FOUND` | IR / RCA / CAPA không tồn tại |
| `FORBIDDEN` | Không có quyền (role / Permission Query) |
| `VALIDATION` | Input validation fail (field thiếu, format sai) |
| `BUSINESS_RULE` | Vi phạm BR-12-xx (clinical_impact missing, RCA incomplete) |
| `CONFLICT` | Đã có RCA open cho incident này; IR đã Acknowledged |
| `BAD_STATE` | State machine fail (Close IR khi RCA chưa Completed) |
| `INTERNAL` | Lỗi hệ thống unexpected |

### 1.4. Mapping FE ↔ BE error code

| BE (`code`) | FE (`ErrorCode`) | Lý do |
|---|---|---|
| `VALIDATION` | `VALIDATION_ERROR` | Field-level inline error |
| `BUSINESS_RULE` | `BUSINESS_RULE_VIOLATION` | Toast + block action |
| `NOT_FOUND` | `NOT_FOUND` | Redirect 404 |
| `FORBIDDEN` | `FORBIDDEN` | Hide action button |
| `CONFLICT` | `CONFLICT` | Toast warning |
| `BAD_STATE` | `BAD_STATE` | Modal explain + action blocked |
| `INTERNAL` | `INTERNAL_ERROR` | Generic error toast |

### 1.5. Pagination convention

```jsonc
{
  "success": true,
  "data": {
    "data": [...],
    "page": 1,
    "page_size": 20,
    "total": 67,
    "total_pages": 4
  }
}
```

---

## 2. Endpoint chi tiết

### 1. report_incident — Tạo Incident Report ✅ LIVE

| Mục | Giá trị |
|---|---|
| Method | POST |
| Path | `/api/method/assetcore.api.imm12.report_incident` |
| Role | Authenticated (Guest → 401) |
| Idempotent | No |

**Request (actual parameters — `fault_description` KHÔNG tồn tại):**
```jsonc
{
  "asset": "ACC-ASSET-2026-00012",           // required
  "incident_type": "Malfunction",            // required (actual field name)
  "severity": "Critical",                    // Low | Medium | High | Critical
  "description": "Máy thở alarm P_HIGH liên tục", // required (actual field: description)
  "fault_code": "VENT_ALARM_HIGH",           // optional
  "clinical_impact": "Bệnh nhân phụ thuộc, đã chuẩn bị bóng ambu", // required if Critical (BR-12-01)
  "workaround_applied": 0,                   // int, not bool
  "patient_affected": 0,
  "patient_impact_description": "",
  "immediate_action": "",
  "linked_repair_wo": ""
}
```

**Response success:**
```jsonc
{
  "success": true,
  "data": {
    "name": "IR-2026-0042",
    "asset": "ACC-ASSET-2026-00012",
    "severity": "Critical",
    "status": "Open",
    "reported_at": "2026-04-18T08:12:00+07:00",
    "asset_lifecycle_status": "Out of Service",
    "lifecycle_event": "ALE-2026-0089"
  }
}
```

**Errors:**
| Code (BE) | Code (FE) | Khi nào |
|---|---|---|
| `BUSINESS_RULE` | `BUSINESS_RULE_VIOLATION` | Critical + không có clinical_impact (BR-12-01) |
| `VALIDATION` | `VALIDATION_ERROR` | Thiếu required fields |
| `NOT_FOUND` | `NOT_FOUND` | Asset không tồn tại |

**Side effects (Critical):**
- `imm00.transition_asset_status(asset, "Out of Service")`
- `imm00.create_lifecycle_event(asset, "incident_reported", ...)`
- `imm00.log_audit_event(...)`
- Email BGĐ + Workshop Lead

---

### 5. resolve_incident — Resolve + auto create RCA ✅ LIVE

| Mục | Giá trị |
|---|---|
| Method | POST |
| Path | `/api/method/assetcore.api.imm12.resolve_incident` |
| Role | ROLES_INVESTIGATE |
| Idempotent | Yes (repeat → return current state) |

**Request:**
```jsonc
{
  "name": "IR-2026-0042",
  "resolution_notes": "Đã thay pressure sensor và calibrate lại.",
  "root_cause": ""                           // optional
}
```

**Response success (Low/Medium — no RCA):**
```jsonc
{
  "success": true,
  "data": {
    "name": "IR-2026-0042",
    "status": "Resolved",
    "rca_created": null
  }
}
```

**Response success (High/Critical — RCA auto-created):**
```jsonc
{
  "success": true,
  "data": {
    "name": "IR-2026-0042",
    "status": "Resolved",
    "rca_created": "IMM-RCA-2026-0012"
  }
}
```

> **Note:** Status goes to `"Resolved"` always (not `"RCA Required"`). RCA is auto-created in background. IMM-12 states in actual code: Open → Under Investigation → Resolved → Closed.

---

### 10. submit_rca — Submit RCA → auto create IMM CAPA Record ✅ LIVE

> **Endpoint is `submit_rca`, NOT `submit_rca_and_create_capa`.**

| Mục | Giá trị |
|---|---|
| Method | POST |
| Path | `/api/method/assetcore.api.imm12.submit_rca` |
| Role | ROLES_INVESTIGATE |
| Idempotent | No (409 if already Completed) |

**Request (actual parameters):**
```jsonc
{
  "name": "IMM-RCA-2026-0012",              // required
  "root_cause": "Pressure sensor degraded do nhiệt độ ICU vượt 28°C",  // required (BR-12-07)
  "corrective_action": "Thay sensor + calibrate",   // required (BR-12-07, actual param name)
  "preventive_action": "PM HVAC tích hợp vào CMMS", // optional
  "five_why_steps": "[{\"why_number\":1,\"why_question\":\"Why?\",\"why_answer\":\"...\"}]", // JSON string
  "rca_notes": ""
}
```

> `five_why_steps` is sent as JSON string from FE (serialized by `submitRca()` in imm12.ts).

**Response success:**
```jsonc
{
  "success": true,
  "data": {
    "name": "RCA-2026-0012",
    "status": "Completed",
    "completed_date": "2026-04-22",
    "linked_capa": "CAPA-2026-0023",
    "capa_due_date": "2026-05-22"
  }
}
```

**Errors:**
| Code | Khi nào |
|---|---|
| `422` | Thiếu `root_cause` hoặc `corrective_action` (BR-12-07) |
| `409` | RCA đã Completed |
| `404` | IMM RCA Record không tồn tại |
| `403` | Không có role ROLES_INVESTIGATE |

**Side effects (BR-12-06):**
- `svc00.create_capa(asset, source_type="IMM RCA Record", source_ref=rca.name, severity=...)` → IMM CAPA Record
- Sets `rca.linked_capa` + `incident.linked_capa`
- `svc00.log_audit_event(asset, "RCA Completed", ...)`

**Curl ví dụ:**
```bash
curl -X POST 'https://hospital.assetcore.vn/api/method/assetcore.api.imm12.submit_rca' \
  -H 'Authorization: token <key>:<secret>' \
  -H 'Content-Type: application/json' \
  -d '{"name":"IMM-RCA-2026-0012","root_cause":"Sensor degraded","corrective_action":"Thay sensor"}'
```

---

### 11. get_chronic_failures — Danh sách chronic assets ✅ LIVE

| Mục | Giá trị |
|---|---|
| Method | GET |
| Path | `/api/method/assetcore.api.imm12.get_chronic_failures` |
| Role | Authenticated |
| Idempotent | Yes |

**Request:** No parameters

**Response success:**
```jsonc
{
  "success": true,
  "data": [
    {
      "asset": "ACC-ASSET-2026-00042",
      "asset_name": "Máy siêu âm GE Vivid E9",
      "department": "Tim mạch",
      "fault_code": "PROBE_DISCONNECT",
      "incident_count": 3,
      "first_incident": "2026-02-15",
      "last_incident": "2026-04-17",
      "rca_record": "RCA-2026-0007",
      "rca_status": "RCA Required",
      "rca_due_date": "2026-05-01",
      "related_incidents": ["IR-2026-0010", "IR-2026-0031", "IR-2026-0055"]
    }
  ]
}
```

---

### 12. get_dashboard — Dashboard ✅ LIVE

> **`get_dashboard` returns `{stats, active_incidents, open_rcas, chronic_failures}` — NOT KPI period breakdown.**

| Mục | Giá trị |
|---|---|
| Method | GET |
| Path | `/api/method/assetcore.api.imm12.get_dashboard` |
| Role | Authenticated |
| Idempotent | Yes |

**Request:** No parameters

**Actual response structure:**
```jsonc
{
  "success": true,
  "data": {
    "stats": {
      "total": 42, "open": 5, "investigating": 3, "resolved": 8,
      "closed": 24, "cancelled": 2, "critical": 1, "high": 4,
      "rca_pending": 2, "chronic": 1
    },
    "active_incidents": [...],   // Open + Under Investigation, top 10
    "open_rcas": [...],          // RCA Required + RCA In Progress, by due_date asc, top 10
    "chronic_failures": [...]    // top 5 chronic groups
  }
}
```

Use `get_incident_stats()` endpoint for per-status KPI counts only.

---

## 7. Smoke test playbook

```bash
# 1. Tạo Incident Critical (actual field names)
curl -X POST 'https://hospital.assetcore.vn/api/method/assetcore.api.imm12.report_incident' \
  -H 'Authorization: token <key>:<secret>' \
  -H 'Content-Type: application/json' \
  -d '{"asset":"ACC-ASSET-2026-00012","incident_type":"Malfunction","description":"Alarm P_HIGH liên tục","severity":"Critical","clinical_impact":"Bệnh nhân phụ thuộc","fault_code":"VENT_ALARM_HIGH"}'

# 2. Acknowledge
curl -X POST 'https://hospital.assetcore.vn/api/method/assetcore.api.imm12.acknowledge_incident' \
  -H 'Authorization: token <key>:<secret>' \
  -d '{"name":"IR-2026-0042","notes":"Đang điều tra"}'

# 3. Resolve → auto create RCA for High/Critical
curl -X POST 'https://hospital.assetcore.vn/api/method/assetcore.api.imm12.resolve_incident' \
  -H 'Authorization: token <key>:<secret>' \
  -d '{"name":"IR-2026-0042","resolution_notes":"Đã thay sensor"}'

# 4. Submit RCA → auto CAPA (actual param names)
curl -X POST 'https://hospital.assetcore.vn/api/method/assetcore.api.imm12.submit_rca' \
  -H 'Authorization: token <key>:<secret>' \
  -d '{"name":"IMM-RCA-2026-0012","root_cause":"Sensor degraded","corrective_action":"Thay sensor"}'

# 5. Close Incident
curl -X POST 'https://hospital.assetcore.vn/api/method/assetcore.api.imm12.close_incident' \
  -H 'Authorization: token <key>:<secret>' \
  -d '{"name":"IR-2026-0042","verification_notes":"Đã xác nhận"}'
```

---

## DoD — File 05 hoàn chỉnh

- [x] API Catalog (§0) — 14 endpoints (actual @frappe.whitelist names from imm12.py)
- [x] Response success format `{"success": true, "data": {...}}`
- [x] Response error format `{"success": false, "error": "...", "code": "..."}`
- [x] Error code catalog (7 codes) + FE mapping
- [x] Endpoint `report_incident`: corrected request schema (incident_type, description — not fault_description)
- [x] Endpoint `resolve_incident`: corrected response (status=Resolved always, rca_created field)
- [x] Endpoint `submit_rca`: corrected params (corrective_action not corrective_action_plan; five_why_steps as JSON string)
- [x] Endpoint `get_chronic_failures`: response với all fields
- [x] Endpoint `get_dashboard`: actual response structure `{stats, active_incidents, open_rcas, chronic_failures}`
- [x] Pagination convention
- [x] Smoke test playbook (5 curl commands, corrected field names)
- [x] ✅ FE types: `frontend/src/api/imm12.ts` (IncidentDetail, RCADetail, ChronicFailure, IncidentStats, DashboardData)
- [ ] Reviewed bởi BE Lead + FE Lead
