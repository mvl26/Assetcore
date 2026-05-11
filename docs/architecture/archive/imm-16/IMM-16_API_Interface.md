# IMM-16 — API Interface Specification

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-16 — Compliance Monitoring & CAPA |
| Phiên bản | 0.2.0 (Wave 2 — alignment with existing CAPA backbone) |
| Ngày cập nhật | 2026-05-04 |
| Trạng thái | PARTIAL — endpoints CAPA cơ bản đã LIVE qua `assetcore.api.imm00`; IMM-16 endpoints PLANNED |
| Base URL (mới) | `/api/method/assetcore.api.imm16` |
| Base URL (đã có — REUSE) | `/api/method/assetcore.api.imm00` |
| Tác giả | AssetCore Team |

---

## 0. Trạng thái endpoint hiện có vs cần thêm mới

### 0.1 Đã có (REUSE — không thiết kế lại)

`assetcore/api/imm00.py` đã expose CAPA Record endpoints, dùng chung với IMM-12:

| Endpoint | Method | Mô tả | DocType |
|---|---|---|---|
| `assetcore.api.imm00.open_capa` | POST | Tạo CAPA Record (delegate `services.imm00.create_capa`) | IMM CAPA Record |
| `assetcore.api.imm00.list_capas` | GET | List CAPA Record + filter | IMM CAPA Record |
| `assetcore.api.imm00.get_capa` | GET | Detail | IMM CAPA Record |
| `assetcore.api.imm00.close_capa_record` | POST | Close CAPA (delegate `services.imm00.close_capa`) | IMM CAPA Record |
| `assetcore.api.dashboard.*` | GET | Dashboard counts đã đọc `IMM CAPA Record` | — |

**IMM-16 gọi lại** các endpoint trên cho thao tác CRUD CAPA cơ bản. IMM-16 chỉ thêm endpoint **chuyên biệt cho compliance lifecycle** (advance state, effectiveness check, gate, scorecard, MR...).

### 0.2 Mới (PLANNED — `assetcore/api/imm16.py`)

~30 endpoints chuyên biệt IMM-16 (xem §3). Các endpoint thao tác trên `IMM CAPA Record` đều set/đọc Custom Field IMM-16 (`imm_*`).

---

## 1. Authentication

Mọi endpoint yêu cầu xác thực Frappe (token hoặc session cookie):

```http
# API Token (server-to-server)
Authorization: token <api_key>:<api_secret>

# Session cookie (browser)
Cookie: sid=<session_id>
```

| HTTP code | Khi nào trả |
|---|---|
| 401 | Thiếu / sai credential |
| 403 | User không có Role hợp lệ; hoặc không thuộc `_WAIVE_ROLES` / `_PUBLISH_SCORECARD_ROLES` / `_FINALIZE_MR_ROLES` / `_CLOSE_AUDIT_ROLES` tương ứng |

---

## 2. Response Format

Frappe wrap mọi response trong outer envelope `{"message": ...}`. Bên trong là `_ok()` / `_err()`:

**Success (HTTP 200):**

```json
{ "message": { "success": true, "data": { /* payload */ } } }
```

**Error:**

```json
{ "message": { "success": false, "error": "Mô tả tiếng Việt", "code": "ERROR_CODE" } }
```

Helper `assetcore/utils/helpers.py`:

```python
def _ok(data): return {"success": True, "data": data}
def _err(msg, code="ERROR"): return {"success": False, "error": msg, "code": code}
```

**Pagination shape:**

```json
{
  "items": [...],
  "pagination": {"page": 1, "page_size": 20, "total": 137, "total_pages": 7}
}
```

---

## 3. Endpoints

~30 whitelist endpoints, group theo nghiệp vụ:

### 3.1 Compliance Rule (master)

#### 3.1.1 `list_rules`

| Thuộc tính | Giá trị |
|---|---|
| Method | GET |
| Path | `assetcore.api.imm16.list_rules` |
| Permission | All authenticated |

**Params:** `filters` (JSON), `page`, `page_size`

**Response:** items theo schema `IMM Compliance Rule` + pagination.

#### 3.1.2 `get_rule`

| Method | GET |
|---|---|

**Params:** `name` (rule_code)

**Errors:** `NOT_FOUND`

#### 3.1.3 `create_rule`

| Method | POST |
|---|---|
| Roles | Tổ HC-QLCL, CMMS Admin |

**Body:** `rule_data` (JSON)

**Validation:** VR-01 threshold JSON schema, VR-02 evaluation_frequency.

**Response:** `{name, version: "1.0", is_active: 1}`

**Errors:** `VALIDATION_ERROR`, `CREATE_ERROR`

#### 3.1.4 `update_rule`

| Method | POST |
|---|---|
| Roles | Tổ HC-QLCL, CMMS Admin |

**Body:** `name`, `rule_data`, `change_summary` (reqd nếu threshold/severity đổi — VR-11)

**Hành vi:** Bump version, lưu `previous_version`, ghi `change_summary` (BR-16-05).

#### 3.1.5 `deactivate_rule`

| Method | POST |
|---|---|

**Body:** `name`, `reason`

**Hành vi:** Set `is_active=0`. Không xóa cứng — rule vẫn audit trail.

---

### 3.2 Compliance Finding

#### 3.2.1 `list_findings`

| Method | GET |
|---|---|

**Params:** `filters` (status, severity, responsible_dept, asset, source_module, date_range), `page`, `page_size`

**Response:**

```json
{
  "items": [{
    "name": "FND-2026-0001",
    "rule": "R-IMM08-PM-COMP-90",
    "detected_date": "2026-05-01 03:00:00",
    "asset": "AC-ASSET-2026-0001",
    "responsible_dept": "ICU",
    "severity": "High",
    "status": "Under Review",
    "current_value": "78",
    "threshold_value": "90",
    "capa_ref": null
  }],
  "pagination": {...}
}
```

#### 3.2.2 `get_finding`

| Method | GET |
|---|---|

**Params:** `name`

**Errors:** `NOT_FOUND`

#### 3.2.3 `confirm_finding`

| Method | POST |
|---|---|
| Roles | Tổ HC-QLCL, Internal Auditor, CMMS Admin |

**Body:** `name`, `notes`

**Hành vi:** `status="Confirmed NC"`, `reviewer=session.user`, `review_date=now`.

**Errors:** `INVALID_STATE` (không phải Under Review), `FORBIDDEN`

#### 3.2.4 `mark_false_positive`

| Method | POST |
|---|---|
| Roles | Tổ HC-QLCL, Internal Auditor, CMMS Admin |

**Body:** `name`, `notes` (reason)

**Hành vi:** `status="False Positive"`, `reviewer`, `review_date`.

#### 3.2.5 `waive_finding`

| Method | POST |
|---|---|
| Roles | `_WAIVE_ROLES = {VP Block2, CMMS Admin}` (BR-16-06) |

**Body (all reqd):** `name`, `waiver_reason` (≥ 50 chars), `waiver_evidence` (file path), `waiver_expiry` (date > today)

**Validation:** VR-04 toàn bộ trường + role check.

**Hành vi:** `status="Waived"`. Sau `waiver_expiry`, scheduler tự reopen → "Open".

**Errors:** `FORBIDDEN`, `VALIDATION_ERROR`

#### 3.2.6 `link_to_capa`

| Method | POST |
|---|---|
| Roles | Tổ HC-QLCL, Workshop Head, CMMS Admin |

**Body:** `finding_name`, `capa_data` (JSON cho CAPA mới) HOẶC `capa_name` (link CAPA đã có)

**Hành vi:** Tạo IMM CAPA mới (status="Draft") hoặc link với existing; set `finding.capa_ref`.

**Response:** `{finding_name, capa_name}`

---

### 3.3 Internal Audit

#### 3.3.1 `list_audits`

| Method | GET |
|---|---|

**Params:** `filters` (status, audit_type, year), pagination.

#### 3.3.2 `create_audit`

| Method | POST |
|---|---|
| Roles | Tổ HC-QLCL, CMMS Admin |

**Body:** `audit_data` JSON (audit_code, type, scope_modules, scope_departments, planned_start/end, lead_auditor, auditor_team)

**Response:** `{name, status: "Planned"}`

#### 3.3.3 `start_audit`

| Method | POST |
|---|---|
| Roles | Lead Auditor, Tổ HC-QLCL, CMMS Admin |

**Body:** `name`

**Hành vi:** `status="In Progress"`, `actual_start=today`.

#### 3.3.4 `complete_audit_checklist`

| Method | POST |
|---|---|
| Roles | Lead Auditor, Internal Auditor, CMMS Admin |

**Body:** `audit_name`, `items` (Array of checklist item updates)

**Hành vi cho mỗi item finding_status="Major NC" hoặc "Minor NC":**

1. Sinh IMM Compliance Finding tự động:
   - `severity = High` cho Major NC; `Medium` cho Minor NC
   - `source_record_doctype = "IMM Internal Audit"`, `source_record = audit_name`
   - `responsible_dept` = scope dept của audit
2. Set `item.linked_finding = finding.name`

**Response:** `{audit_name, items_count, findings_created}`

#### 3.3.5 `close_audit`

| Method | POST |
|---|---|
| Roles | `_CLOSE_AUDIT_ROLES = {Tổ HC-QLCL, VP Block2, CMMS Admin}` |

**Body:** `name`, `audit_report` (file path)

**Validation (VR-08, BR-16-04):** Mọi Major NC item phải có `linked_finding.capa_ref` set (CAPA đã được tạo). Nếu thiếu → `VALIDATION_ERROR` "Còn N Major NC chưa mở CAPA".

**Hành vi:** `status="Closed"`, `actual_end=today`, lưu `audit_report`.

---

### 3.4 CAPA — operate on `IMM CAPA Record` (LIVE)

> CRUD cơ bản REUSE `assetcore.api.imm00.*` (đã LIVE). IMM-16 chỉ thêm endpoint chuyên biệt: advance state, effectiveness check, reopen.

#### 3.4.1 `list_capas` — REUSE `assetcore.api.imm00.list_capas`

| Method | GET |
|---|---|
| Path | `assetcore.api.imm00.list_capas` |

**Params:** `status`, `capa_type`, `asset`, `page`, `page_size`. IMM-16 frontend gọi với thêm filter trên Custom Field `imm_risk_level`, `source_type` qua REST `frappe.client.get_list` cho nhu cầu nâng cao.

#### 3.4.2 `get_capa` — REUSE `assetcore.api.imm00.get_capa`

| Method | GET |
|---|---|
| Path | `assetcore.api.imm00.get_capa` |

**Response:** Full CAPA Record + action_steps (Custom Field child `imm_action_plan`) + linked Finding/Audit.

#### 3.4.3 `create_capa` — REUSE `assetcore.api.imm00.open_capa`

| Method | POST |
|---|---|
| Path | `assetcore.api.imm00.open_capa` |
| Roles | Tổ HC-QLCL, Internal Auditor, Workshop Head, Biomed Engineer, Trưởng phòng, CMMS Admin |

**Body:** `asset`, `source_type` (extend Select option để nhận `Compliance Finding` / `Audit Finding` / `Management Review`), `source_ref`, `severity`, `description`, …

**IMM-16 augment (PLANNED `assetcore.api.imm16.create_capa_from_finding`):**

| Method | POST |
|---|---|
| Path | `assetcore.api.imm16.create_capa_from_finding` |

**Body:** `finding_name`, `imm_risk_level`, `imm_root_cause_method` (optional), `responsible`, `due_date`.

**Hành vi:** Gọi `services.imm00.create_capa(...)` → set Custom Field IMM-16 (`imm_compliance_finding_ref`, `imm_risk_level`, `workflow_state="Open"`) → set `Compliance Finding.capa_ref`.

**Response:** `{capa_name, finding_name}`

#### 3.4.4 `advance_capa_state` — NEW (`assetcore.api.imm16.advance_capa_state`)

| Method | POST |
|---|---|
| Path | `assetcore.api.imm16.advance_capa_state` |

**Body:** `name` (CAPA-YYYY-#####), `target_state` (IN Investigating/Action Plan/Implementation/Verification/Closed), `payload` (JSON tuỳ state)

**Hành vi:** Set `workflow_state` + map `status` (xem Technical_Design §8.3) qua hook `capa_record_validate`. KHÔNG sửa core controller.

**State-specific validation:**

| target_state | Validation |
|---|---|
| Action Plan | VR-05 `imm_root_cause_method` reqd; VR-12 `due_date > today` |
| Implementation | Tất cả `imm_action_plan` rows có `owner` + `planned_date` |
| Verification | Tất cả `imm_action_plan` rows `status="Done"` |
| Closed | VR-06 `effectiveness_check` reqd; VR-07 phải = "Effective" |

**Errors:** `VALIDATION_ERROR`, `INVALID_STATE`

#### 3.4.5 `perform_effectiveness_check` — NEW

| Method | POST |
|---|---|
| Path | `assetcore.api.imm16.perform_effectiveness_check` |
| Roles | Tổ HC-QLCL, CMMS Admin |

**Body:** `name`, `result` (Effective / Not Effective / Partially Effective), `effectiveness_evidence` (file path)

**Hành vi:**

- Set `effectiveness_check` (field LIVE) + `imm_effectiveness_check_date` + `imm_effectiveness_evidence`.
- `Effective` → call `advance_capa_state(target_state="Closed")` (đồng thời gọi `services.imm00.close_capa`).
- `Not Effective` → set `workflow_state="Re-opened"`, sau đó về `Investigating`; `imm_reopen_count++`. BR-16-03.

**Response:** `{name, new_state, imm_reopen_count}`

#### 3.4.6 `reopen_capa` — NEW

| Method | POST |
|---|---|
| Path | `assetcore.api.imm16.reopen_capa` |
| Roles | Tổ HC-QLCL, CMMS Admin |

**Body:** `name`, `reason`

**Hành vi:** Force re-open kể cả từ "Closed" (sử dụng ERPNext `amend_from` pattern nếu CAPA đã submit, hoặc workflow_state="Re-opened" nếu chưa). `imm_reopen_count++`.

> Lưu ý: `IMM CAPA Record` là `is_submittable=1`. Sau khi đã `Closed` (docstatus=1), reopen cần amend (tạo bản mới `amended_from` cũ) — UI handle bằng button "Amend" của Frappe.

---

### 3.5 Compliance Scorecard

#### 3.5.1 `list_scorecards`

| Method | GET |
|---|---|

**Params:** `period_year`, `period_month` (optional), `scope`, pagination.

#### 3.5.2 `get_current_scorecard`

| Method | GET |
|---|---|

Trả scorecard tháng hiện tại (đang Draft) hoặc tháng gần nhất đã publish.

#### 3.5.3 `get_scorecard_by_period`

| Method | GET |
|---|---|

**Params:** `year`, `month`, `scope`, `scope_value`

**Response:**

```json
{
  "name": "SCR-2026-04-0001",
  "period_year": 2026,
  "period_month": 4,
  "scope": "Hospital",
  "score_pct": 87.5,
  "trend_vs_prev_month": +2.3,
  "score_by_module": [
    {"module": "IMM-08", "score": 91.0},
    {"module": "IMM-11", "score": 78.5}
  ],
  "score_by_department": [
    {"dept": "ICU", "score": 92.0},
    {"dept": "OR", "score": 81.0}
  ],
  "capa_open_count": 12,
  "capa_overdue_count": 3,
  "is_published": 1
}
```

#### 3.5.4 `publish_scorecard`

| Method | POST |
|---|---|
| Roles | `_PUBLISH_SCORECARD_ROLES = {Tổ HC-QLCL, VP Block2, CMMS Admin}` |

**Body:** `name`

**Validation (VR-10, BR-16-08):** Quý trước phải có IMM Management Review status="Closed". Nếu không → `VALIDATION_ERROR`.

**Hành vi:** `is_published=1`, `published_at=now`, `approved_by_for_review=session.user`. Sau publish → immutable (BR-16-07, VR-09).

---

### 3.6 Management Review

#### 3.6.1 `list_management_reviews`

| Method | GET |
|---|---|

#### 3.6.2 `create_management_review`

| Method | POST |
|---|---|
| Roles | Tổ HC-QLCL, VP Block2, CMMS Admin |

**Body:** `mr_data` (review_date, chair, attendees, scorecard_ref, ...)

**Default:** `status="Draft"`, `quarter` auto-compute từ `review_date`.

#### 3.6.3 `finalize_management_review`

| Method | POST |
|---|---|
| Roles | `_FINALIZE_MR_ROLES = {VP Block2, CMMS Admin}` |

**Body:** `name`, `minutes_doc` (file), `output_actions` (JSON array)

**Hành vi:** `status="Minutes Approved"` → "Closed".

---

### 3.7 Dashboard / Reports

#### 3.7.1 `get_dashboard_stats`

| Method | GET |
|---|---|

**Response:**

```json
{
  "kpis": {
    "overall_compliance_pct": 87.5,
    "findings_open": 24,
    "findings_critical": 3,
    "capa_open": 18,
    "capa_overdue": 5,
    "audits_in_progress": 2,
    "mr_quarterly_status": "Done" | "Pending" | "Overdue"
  },
  "trend_12m": [{"month": "2025-06", "score_pct": 82.0}, ...],
  "top_modules_low": [{"module": "IMM-11", "score": 72.0}, ...],
  "recent_findings": [...]
}
```

#### 3.7.2 `get_compliance_heatmap`

| Method | GET |
|---|---|

**Params:** `period_year`, `period_month` (optional, default current)

**Response:**

```json
{
  "modules": ["IMM-04","IMM-05","IMM-06","IMM-08","IMM-09","IMM-11","IMM-12","IMM-15"],
  "departments": ["ICU","OR","ER","CT","Internal Med","Pediatric"],
  "matrix": [
    {"module":"IMM-08","dept":"ICU","score":92.0,"findings_count":2},
    {"module":"IMM-08","dept":"OR","score":78.0,"findings_count":5},
    ...
  ]
}
```

Click cell trên FE → drill-down `list_findings?filters={module, dept, period}`.

#### 3.7.3 `get_capa_aging`

| Method | GET |
|---|---|

**Response:**

```json
{
  "buckets": [
    {"range": "0-7d",   "count": 6},
    {"range": "8-30d",  "count": 8},
    {"range": "31-60d", "count": 3},
    {"range": "61-90d", "count": 1},
    {"range": ">90d",   "count": 0}
  ],
  "by_severity": {
    "Critical": {"open": 3, "overdue": 1},
    "High":     {"open": 9, "overdue": 3},
    "Medium":   {"open": 5, "overdue": 1}
  }
}
```

#### 3.7.4 `get_overdue_actions`

| Method | GET |
|---|---|

Liệt kê CAPA + CAPA Action Step quá hạn, sort by overdue_days DESC.

**Response item:** `{capa_name, action_step_no, owner, planned_date, overdue_days, severity}`

---

### 3.8 Cross-module Gate

#### 3.8.1 `check_asset_compliance_status`

| Method | GET |
|---|---|
| Caller | `services/imm08.py.validate_*` + `services/imm09.py.validate_*` (BR-16-09); IMM-13/14 decommission gate |

**Params:** `asset` (AC Asset name)

**Query (server-side):** Read `IMM CAPA Record` filter:
```
asset = <asset>
imm_risk_level = "Critical"          # Custom Field IMM-16
status IN ("Open", "In Progress", "Pending Verification")
```

**Response:**

```json
{
  "blocked": true,
  "asset": "AC-ASSET-2026-0001",
  "reasons": [
    {
      "type": "CAPA_CRITICAL_OPEN",
      "ref": "CAPA-2026-00007",
      "status": "In Progress",
      "workflow_state": "Implementation",
      "message": "CAPA Critical chưa close"
    }
  ],
  "active_findings_count": 2,
  "active_capas_count": 1
}
```

Hoặc `{"blocked": false, "active_findings_count": 0, "active_capas_count": 0}` nếu pass.

---

## 4. Error Codes

### 4.1 HTTP Status

| Code | Ý nghĩa |
|---|---|
| 200 | OK (kiểm tra `success` trong body) |
| 401 | Thiếu/sai auth |
| 403 | Frappe permission deny |
| 500 | Server error |

### 4.2 Application Error Codes

| Code | Endpoint | Mô tả |
|---|---|---|
| `INVALID_FILTERS` | list_* | filters JSON parse fail |
| `INVALID_DATA` | create/update | body JSON parse fail |
| `NOT_FOUND` | get/update/* | DocType không tồn tại |
| `FORBIDDEN` | waive_finding, publish_scorecard, finalize_mr, close_audit | Role không hợp lệ |
| `INVALID_STATE` | confirm/advance_capa/start_audit | workflow_state không phù hợp action |
| `VALIDATION_ERROR` | create/advance/close/publish | VR-01..VR-12 fail |
| `CREATE_ERROR` | create_* | Insert exception |
| `MR_MISSING_QUARTERLY` | publish_scorecard | BR-16-08 quý trước thiếu MR |
| `CAPA_LINK_REQUIRED` | close_audit | BR-16-04 Major NC chưa link CAPA |
| `EFFECTIVENESS_REQUIRED` | advance_capa_state(Closed) | BR-16-03 |
| `SCORECARD_IMMUTABLE` | update Scorecard | BR-16-07 |
| `RULE_CHANGE_CONTROL` | update_rule | BR-16-05 thiếu change_summary |

---

## 5. Webhook / Realtime Events

IMM-16 publish realtime events qua `frappe.publish_realtime` cho dashboard live update:

| Event | Trigger | Payload |
|---|---|---|
| `imm16:finding_created` | Service `upsert_finding` | `{name, severity, asset, dept}` |
| `imm16:finding_status_changed` | confirm/false_positive/waive | `{name, status, reviewer}` |
| `imm16:capa_created` | create_capa | `{name, risk_level, source_ref}` |
| `imm16:capa_state_changed` | advance_capa_state | `{name, new_state, reopen_count}` |
| `imm16:scorecard_published` | publish_scorecard | `{name, period, score_pct}` |
| `imm16:audit_closed` | close_audit | `{name, findings_count}` |

Audit trail qua Frappe Version DocType cho mọi thay đổi field.

---

## 6. Implementation Notes

| # | Note |
|---|---|
| 1 | Service layer `services/imm16.py` chứa toàn bộ business logic — controller chỉ điều phối + validate. Khác IMM-05 (logic in controller, tech-debt). |
| 2 | Idempotent rule evaluation: UNIQUE INDEX `(rule, source_record, evaluation_date)` đảm bảo scheduler có thể chạy nhiều lần cùng ngày không tạo bản ghi trùng. |
| 3 | `check_asset_compliance_status` được IMM-08/09 gọi trong `validate()` trước Submit Work Order (BR-16-09). Cũng được IMM-13/14 gọi trước decommission. |
| 4 | Naming series IMM-16: Finding `FND-{YYYY}-{#####}`, Audit `AUD-INT-...`, CAPA `CAPA-...`, Scorecard `SCR-{YYYY}-{MM}-...`, MR `MR-{YYYY}-...`. |
| 5 | Scorecard immutability: sau khi `publish_scorecard` set `is_published=1`, controller `validate()` reject mọi thay đổi field (BR-16-07, VR-09). Nếu cần sửa → tạo Scorecard mới với `restate_of` link. |
| 6 | Quarterly MR gate: `publish_scorecard` query MR của quý trước (`status="Closed"`) — nếu không có → reject với code `MR_MISSING_QUARTERLY` (BR-16-08, VR-10). |
| 7 | CAPA Re-open: khi `effectiveness_result="Not Effective"` → `status="Re-opened"` → "Investigating", `reopen_count++`. BR-16-03 enforce trong VR-07 nếu cố Close mà chưa Effective. |
| 8 | Waiver permission: chỉ `_WAIVE_ROLES` (VP Block2, CMMS Admin) — không phải Tổ HC-QLCL. BR-16-06. |
| 9 | Audit close gate: scan tất cả checklist items với `finding_status` IN (Major NC, Minor NC) — nếu Major NC chưa link CAPA → reject (BR-16-04, VR-08). |
| 10 | Rule version control: thay đổi `threshold_definition` hoặc `severity` ⇒ controller `before_save` snapshot `previous_version`, bump `version`, yêu cầu `change_summary` (BR-16-05, VR-11). |
| 11 | File upload qua Frappe File API thông thường (`/api/method/upload_file`). IMM-16 chỉ nhận đường dẫn vào field `evidence`, `waiver_evidence`, `audit_report`, `effectiveness_evidence`, `minutes_doc`. |
| 12 | OpenAPI 3.0 contract cho IMM-16 sẽ được generate qua slash command `/dev:generate-api-contract imm16` khi implement. Hiện tại document này là spec authoritative. |
