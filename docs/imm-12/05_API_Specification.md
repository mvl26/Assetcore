# 05 — API Specification

| Mục | Giá trị |
|---|---|
| Module | IMM-12 — Incident & CAPA Management |
| Phạm vi | Per-module |
| Owner | BE Lead |
| Base URL | `/api/method/assetcore.api.imm12.<function>` |
| Auth | Frappe session HOẶC `Authorization: token <key>:<secret>` |
| Cập nhật | 2026-05-27 |
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

### 1.3. Error code catalog (Notification Contract — Sprint 2026-05-29)

> **Cột `message_code`** trỏ vào registry `assetcore/utils/messages.py:MESSAGES`.
> BE raise qua `nthrow(MSG.<code>, **ctx)` (service) / `nthrow_in_hook(MSG.<code>)`
> (DocType hook); handler `api_handler.handle()` tự hydrate `title/severity/action_hint`
> từ registry rồi đưa vào envelope `_err`. FE đọc `messageCode` → `useNotify().fromError()`.
> Xem **§11 Notification Contract** (single source of truth).

| BE bucket (`code`) | HTTP | Severity | `message_code` (MSG.*) | Business Rule | Khi nào |
|---|---|---|---|---|---|
| `NOT_FOUND` | 404 | warning | `IMM12_INCIDENT_NOT_FOUND` | — | Incident Report không tồn tại |
| `NOT_FOUND` | 404 | warning | `IMM12_RCA_NOT_FOUND` | — | RCA Record không tồn tại |
| `NOT_FOUND` | 404 | warning | `IMM12_ASSET_NOT_FOUND` | — | `asset` không tồn tại khi tạo incident |
| `BUSINESS_RULE` | 422 | critical | `IMM12_CLINICAL_IMPACT_REQUIRED` | BR-12-01 | Incident Critical thiếu `clinical_impact` |
| `BUSINESS_RULE` | 422 | warning | `IMM12_RESOLUTION_NOTES_REQUIRED` | — | Resolve thiếu `resolution_notes` |
| `BUSINESS_RULE` | 422 | warning | `IMM12_CANCEL_REASON_REQUIRED` | — | Cancel thiếu lý do hủy |
| `BUSINESS_RULE` | 422 | warning | `IMM12_RCA_ROOT_CAUSE_REQUIRED` | BR-12-07 | Submit RCA thiếu `root_cause` |
| `BUSINESS_RULE` | 422 | warning | `IMM12_RCA_CORRECTIVE_REQUIRED` | BR-12-07 | Submit RCA thiếu `corrective_action` |
| `CONFLICT` | 409 | warning | `IMM12_RCA_ALREADY_EXISTS` | — | Incident đã có RCA Record (create_rca idempotent) |
| `CONFLICT` | 409 | warning | `IMM12_RCA_ALREADY_COMPLETED` | — | Submit RCA khi RCA đã Completed |
| `BAD_STATE` | 409 | warning | `IMM12_BAD_STATE` | — | State machine transition không hợp lệ |
| `BUSINESS_RULE` | 422 | critical | `IMM12_CLOSE_RCA_REQUIRED` | BR-12-02 / NEG-11 | Đóng IR Major/Critical khi chưa có RCA |
| `BUSINESS_RULE` | 422 | critical | `IMM12_CLOSE_RCA_INCOMPLETE` | BR-12-02 / NEG-11 | Đóng IR Major/Critical khi RCA chưa Completed |
| `FORBIDDEN` | 403 | warning | `AUTH_FORBIDDEN` | — | Không có quyền (role / Permission Query) |
| `INVALID_PARAMS` | 400 | warning | `SYS_INVALID_PARAMS` | — | JSON param malformed (`parse_json`) |
| `INTERNAL` | 500 | error | `SYS_INTERNAL` | — | Lỗi hệ thống unexpected |
| _(success)_ | 200 | success | `IMM12_REPORT_SUCCESS` | — | Tạo incident thành công (envelope `_ok`) |

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

## 11. Notification Contract (Sprint Notification 2026-05-29) — SINGLE SOURCE OF TRUTH

Mọi tương tác IMM-12 trả về **envelope chuẩn** đã chuẩn hoá BE → FE. FE KHÔNG
hardcode câu chữ — chỉ đọc `messageCode` rồi render qua `useNotify`. Contract đã
chốt vòng 1 (pilot IMM-09) — vòng 2 áp dụng cho IMM-12.

### 11.1 Envelope shape

Success (`_ok`):
```json
{ "success": true, "data": { ... } }
```
Lỗi (`_err`, hydrate từ registry qua `api_handler.handle()`):
```json
{
  "success": false,
  "error": "Không thể đóng sự cố mức Critical khi RCA chưa hoàn thành.",
  "code": "BUSINESS_RULE",
  "message_code": "IMM12-CLOSE-RCA-INCOMPLETE",
  "severity": "critical",
  "title": "Chưa thể đóng sự cố",
  "action_hint": "Hoàn thành RCA Record liên kết trước khi đóng sự cố.",
  "context": { "severity": "Critical", "rca": "IMM-RCA-2026-0012" },
  "http_status": 422
}
```

**Bất biến (contract):** mọi error envelope IMM-12 PHẢI có `message_code`, `severity`,
`title`. Không còn `IncidentError` thô và không còn `frappe.throw(_("..."))` leak
message Frappe ra FE. Class `IncidentError` bị loại bỏ — service raise qua
`nthrow(MSG.IMM12_*)`; DocType hook (NEG-11 close gate) raise qua
`nthrow_in_hook(MSG.IMM12_*)`.

### 11.2 Danh mục MSG cần bổ sung vào `utils/messages.py`

13 mã mới + tái dùng 3 mã hệ thống (`AUTH_FORBIDDEN`, `SYS_INVALID_PARAMS`,
`SYS_INTERNAL` — đã có). Severity tuân quy tắc §11.4.

| MSG.* | code (kebab) | severity | http | title | template (VI) | action_hint |
|---|---|---|---|---|---|---|
| `IMM12_INCIDENT_NOT_FOUND` | `IMM12-INCIDENT-NOT-FOUND` | warning | 404 | Không tìm thấy sự cố | Không tìm thấy báo cáo sự cố: {name}. | Kiểm tra lại mã sự cố trong danh sách. |
| `IMM12_RCA_NOT_FOUND` | `IMM12-RCA-NOT-FOUND` | warning | 404 | Không tìm thấy RCA | Không tìm thấy bản phân tích nguyên nhân gốc: {name}. | Kiểm tra lại mã RCA trong danh sách. |
| `IMM12_ASSET_NOT_FOUND` | `IMM12-ASSET-NOT-FOUND` | warning | 404 | Không tìm thấy thiết bị | Không tìm thấy thiết bị: {asset}. | Kiểm tra lại mã thiết bị trong danh mục tài sản. |
| `IMM12_CLINICAL_IMPACT_REQUIRED` | `IMM12-CLINICAL-IMPACT-REQUIRED` | critical | 422 | Thiếu mô tả tác động lâm sàng | Sự cố mức Critical bắt buộc mô tả tác động lâm sàng. | Nhập tác động lâm sàng trước khi báo cáo sự cố nghiêm trọng. |
| `IMM12_RESOLUTION_NOTES_REQUIRED` | `IMM12-RESOLUTION-NOTES-REQUIRED` | warning | 422 | Thiếu ghi chú giải quyết | Cần nhập ghi chú giải quyết khi chuyển sự cố sang Đã xử lý. | Nhập ghi chú giải quyết rồi thử lại. |
| `IMM12_CANCEL_REASON_REQUIRED` | `IMM12-CANCEL-REASON-REQUIRED` | warning | 422 | Thiếu lý do hủy | Cần nhập lý do khi hủy sự cố. | Nhập lý do hủy rồi thử lại. |
| `IMM12_RCA_ROOT_CAUSE_REQUIRED` | `IMM12-RCA-ROOT-CAUSE-REQUIRED` | warning | 422 | Thiếu nguyên nhân gốc rễ | Cần nhập nguyên nhân gốc rễ để hoàn thành RCA. | Nhập nguyên nhân gốc rễ rồi gửi lại RCA. |
| `IMM12_RCA_CORRECTIVE_REQUIRED` | `IMM12-RCA-CORRECTIVE-REQUIRED` | warning | 422 | Thiếu hành động khắc phục | Cần nhập hành động khắc phục để hoàn thành RCA. | Nhập hành động khắc phục rồi gửi lại RCA. |
| `IMM12_RCA_ALREADY_EXISTS` | `IMM12-RCA-ALREADY-EXISTS` | warning | 409 | Sự cố đã có RCA | Sự cố này đã có bản phân tích nguyên nhân gốc: {rca}. | Mở RCA hiện có thay vì tạo mới. |
| `IMM12_RCA_ALREADY_COMPLETED` | `IMM12-RCA-ALREADY-COMPLETED` | warning | 409 | RCA đã hoàn thành | Bản phân tích nguyên nhân gốc này đã hoàn thành. | Không cần gửi lại — RCA đã chốt. |
| `IMM12_BAD_STATE` | `IMM12-BAD-STATE` | warning | 409 | Sai trạng thái sự cố | Không thể chuyển sự cố từ '{from_state}' sang '{to_state}'. | Chỉ thực hiện hành động hợp lệ với trạng thái hiện tại. |
| `IMM12_CLOSE_RCA_REQUIRED` | `IMM12-CLOSE-RCA-REQUIRED` | critical | 422 | Chưa thể đóng sự cố | Sự cố mức {severity} bắt buộc có RCA hoàn tất trước khi đóng. | Tạo và hoàn thành RCA Record trước khi đóng sự cố. |
| `IMM12_CLOSE_RCA_INCOMPLETE` | `IMM12-CLOSE-RCA-INCOMPLETE` | critical | 422 | Chưa thể đóng sự cố | Không thể đóng sự cố mức {severity} khi RCA ({rca}) chưa hoàn thành. | Hoàn thành RCA Record liên kết trước khi đóng sự cố. |
| _(success)_ `IMM12_REPORT_SUCCESS` | `IMM12-REPORT-SUCCESS` | success | 200 | Đã ghi nhận sự cố | Đã ghi nhận báo cáo sự cố {name}. | — |

> Lưu ý content: tuân `messages.py` §quy chuẩn — Chủ thể + Hậu quả + Hành động,
> không từ kỹ thuật, không đổ lỗi user. Sau khi thêm vào `messages.py`, chạy
> `python scripts/gen_fe_messages.py` để regen `frontend/src/i18n/messages.ts`.

### 11.3 BE migration checklist (cho assetcore-be)

- `services/imm12.py`: **xóa class `IncidentError`**; 15 `raise IncidentError(...)` →
  `nthrow(MSG.IMM12_*, **ctx)`. Map theo bảng §11.2.
- `services/imm12.py` hook `validate_incident_close_gate` (NEG-11, ~line 888/895):
  2 `frappe.throw(_(...))` → `nthrow_in_hook(MSG.IMM12_CLOSE_RCA_REQUIRED)` /
  `nthrow_in_hook(MSG.IMM12_CLOSE_RCA_INCOMPLETE)`. Đây là DocType `validate` hook
  → BẮT BUỘC dùng `nthrow_in_hook` (không phải `nthrow`).
- `api/imm12.py`: bỏ `IncidentError` import + try/except cục bộ + `_ok`/`_err` thủ công
  → dùng `from assetcore.utils.api_handler import handle, parse_json`. Giữ guard
  Guest→401 và role-check→403 (raise `nthrow(MSG.AUTH_FORBIDDEN)` hoặc giữ `_err` 403
  trước khi gọi `handle`).
- Audit trail (`_log` / `log_lifecycle_event`) KHÔNG đổi — message framework chỉ
  chuẩn hoá phản hồi user. Auto-RCA / auto-CAPA side-effects KHÔNG đổi.

### 11.4 FE migration checklist (cho assetcore-fe)

- Store `stores/imm12.ts`: expose `lastApiError`; mọi action catch → set
  `lastApiError` từ error envelope (giống `stores/imm09.ts`).
- Views `incident/*` + `rca/*`: thay `toast.error(msg)` / hardcode success →
  `notify.fromError(store.lastApiError)` trong catch, `notify.show({ code:
  MSG.IMM12_REPORT_SUCCESS, ctx })` hoặc `notify.fromOk(resp)` khi thành công.
- KHÔNG còn `try/catch` tự build string từ `e.message` BE.

### 11.5 Quy tắc severity (chốt cho IMM-12)

- `warning` = lỗi nghiệp vụ user tự sửa được (validation, bad-state, not-found,
  conflict) → toast vàng, GIỮ form, không reload.
- `critical` = chặn vì tuân thủ NĐ98 (BR-12-01 clinical impact, BR-12-02 / NEG-11
  RCA gate trước khi đóng sự cố Major/Critical) → modal blocking.
- `error` = lỗi hệ thống (`SYS-*`) → toast đỏ.
- `success` = thao tác thành công → toast xanh.

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
