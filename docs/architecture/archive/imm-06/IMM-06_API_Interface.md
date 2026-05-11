# IMM-06 — API Interface Specification

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-06 — User Training & Competency Management |
| Phiên bản | 0.1.0 (Wave 2 — DRAFT) |
| Ngày cập nhật | 2026-05-04 |
| Trạng thái | PLANNED |
| Base URL | `/api/method/assetcore.api.imm06` |
| Tác giả | AssetCore Team |

---

## 1. Authentication

Mọi endpoint yêu cầu xác thực Frappe (token hoặc session cookie):

```http
Authorization: token <api_key>:<api_secret>
# hoặc
Cookie: sid=<session_id>
```

| HTTP code | Khi nào trả |
|---|---|
| 401 | Thiếu / sai credential |
| 403 | User không có Role hợp lệ; hoặc gọi endpoint yêu cầu role đặc biệt (`_APPROVE_ROLES`, `_REVOKE_ROLES`, `_SIGNOFF_ROLES`) |

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

**Pagination shape (list endpoints):**

```json
{
  "items": [...],
  "pagination": {"page": 1, "page_size": 20, "total": 137, "total_pages": 7}
}
```

---

## 3. Endpoints

19 whitelist endpoints, group theo nghiệp vụ.

**Constants:**

```python
_DOCTYPE_PROGRAM    = "IMM Training Program"
_DOCTYPE_SESSION    = "IMM Training Session"
_DOCTYPE_COMPETENCY = "IMM User Competency"

_PROGRAM_WRITE_ROLES = {"Tổ HC-QLCL", "CMMS Admin"}
_SESSION_WRITE_ROLES = {"Tổ HC-QLCL", "Biomed Engineer", "Workshop Head", "CMMS Admin"}
_SIGNOFF_ROLES       = {"Department Manager", "Workshop Head", "Tổ HC-QLCL", "CMMS Admin"}
_REVOKE_ROLES        = {"Tổ HC-QLCL", "CMMS Admin"}
```

---

### 3.1 Training Program

#### 3.1.1 `list_programs`

| Method | GET |
|---|---|
| Path | `assetcore.api.imm06.list_programs` |
| Permission | All authenticated |

**Params:** `filters` (JSON), `page`, `page_size` (max 100).

**Response data:**

```json
{
  "items": [{
    "name": "TRN-MON-INIT-01",
    "program_name": "Đào tạo cơ bản Monitor Philips X3",
    "training_type": "Initial",
    "target_device_model": "MDL-MON-PHILIPS-X3",
    "duration_hours": 8,
    "validity_period_months": 24,
    "passing_score_pct": 70,
    "is_active": 1,
    "is_mandatory_for_operation": 1,
    "modified": "2026-05-01 09:00:00"
  }],
  "pagination": {"page": 1, "page_size": 20, "total": 23, "total_pages": 2}
}
```

**Errors:** `INVALID_FILTERS`.

#### 3.1.2 `get_program`

| Method | GET |
|---|---|
| Permission | All authenticated |

**Params:** `name`.

**Response:** Full program object.

**Errors:** `NOT_FOUND`.

#### 3.1.3 `create_program`

| Method | POST |
|---|---|
| Roles | `_PROGRAM_WRITE_ROLES` |

**Body:** `program_data` (JSON) — fields theo DocType schema.

**Response:** `{name, is_active}`.

**Errors:** `FORBIDDEN`, `INVALID_DATA`, `VALIDATION_ERROR` (VR-02/03/11), `CREATE_ERROR`.

**Example request:**

```json
{
  "program_data": {
    "program_code": "TRN-MON-INIT-01",
    "program_name": "Đào tạo cơ bản Monitor Philips X3",
    "training_type": "Initial",
    "target_device_model": "MDL-MON-PHILIPS-X3",
    "duration_hours": 8,
    "validity_period_months": 24,
    "passing_score_pct": 70,
    "assessment_method": "Both",
    "instructor_qualification_required": "Biomed Engineer",
    "is_mandatory_for_operation": 1,
    "content_outline": "<p>1. Tổng quan thiết bị ...</p>"
  }
}
```

#### 3.1.4 `update_program`

| Method | POST |
|---|---|
| Roles | `_PROGRAM_WRITE_ROLES` |

**Body:** `name`, `program_data` (JSON).

**Behavior:** Trigger BR-06-04 — nếu critical fields thay đổi → flag tất cả Active Competency tương ứng cho re-cert (`needs_recert=1`) và tạo Document Request style task cho Tổ HC-QLCL.

**Response:** `{name, recert_triggered: bool, affected_competencies_count: int}`.

---

### 3.2 Training Session

#### 3.2.1 `list_sessions`

| Method | GET |
|---|---|

**Params:** `filters`, `page`, `page_size`.

**Response data:**

```json
{
  "items": [{
    "name": "TRN-2026-0042",
    "training_program": "TRN-MON-INIT-01",
    "session_date": "2026-05-20",
    "location": "Phòng đào tạo F3",
    "instructor": "biomed1@hosp.vn",
    "session_type": "Onsite",
    "workflow_state": "Confirmed",
    "participant_count": 15,
    "duration_planned_hours": 8
  }],
  "pagination": {...}
}
```

#### 3.2.2 `get_session`

**Params:** `name`.

**Response:** Full session + `participants` (child rows).

#### 3.2.3 `create_session`

| Method | POST |
|---|---|
| Roles | `_SESSION_WRITE_ROLES` |

**Body:** `session_data` (JSON) — gồm `participants` array.

**Behavior:** Tạo session `workflow_state="Planned"`. Validate VR-04 (instructor qualification), VR-10 (date not past). Gửi email mời participant với link xác nhận.

**Response:** `{name, workflow_state, participant_count}`.

**Errors:** `FORBIDDEN`, `VALIDATION_ERROR`, `CREATE_ERROR`.

#### 3.2.4 `confirm_session`

| Method | POST |
|---|---|
| Roles | `Tổ HC-QLCL`, `CMMS Admin` |

**Body:** `name`.

**Behavior:** Validate VR-05 (≥1 participant), chuyển workflow Planned → Confirmed.

**Response:** `{name, new_state: "Confirmed"}`.

**Errors:** `INVALID_STATE`, `VALIDATION_ERROR`, `FORBIDDEN`.

#### 3.2.5 `complete_session`

| Method | POST |
|---|---|
| Roles | `Tổ HC-QLCL`, `Biomed Engineer` (instructor), `CMMS Admin` |

**Body:** `name`, `participants_results` (array of `{user, theory_score, practical_score, attendance_pct, remarks}`).

**Behavior:**

1. Validate VR-06 (scores reqd).
2. Compute `overall_result` cho mỗi participant.
3. Chuyển workflow In Progress → Completed.
4. Gọi `services.imm06.create_competency_from_session(name)` → tạo Pending Assessment competency cho mọi Pass.
5. Gửi email cho supervisor (Department Manager).

**Response:**

```json
{
  "name": "TRN-2026-0042",
  "new_state": "Completed",
  "participants_summary": {"pass": 13, "fail": 1, "conditional": 1},
  "competencies_created": ["COMP-2026-0301", "..."]
}
```

**Errors:** `INVALID_STATE`, `VALIDATION_ERROR`, `FORBIDDEN`.

#### 3.2.6 `cancel_session`

| Method | POST |
|---|---|
| Roles | `Tổ HC-QLCL`, `CMMS Admin` |

**Body:** `name`, `cancel_reason`.

**Behavior:** Block nếu state = Verified hoặc Closed (BR-06-12).

**Response:** `{name, new_state: "Cancelled"}`.

---

### 3.3 User Competency

#### 3.3.1 `list_competencies`

| Method | GET |
|---|---|
| Permission | Tự lọc theo role: Operator chỉ thấy own; Department Manager / Clinical Head thấy own dept; Tổ HC-QLCL / Workshop Head / CMMS Admin thấy toàn bộ |

**Params:** `filters`, `page`, `page_size`.

**Response:**

```json
{
  "items": [{
    "name": "COMP-2026-0301",
    "user": "ktv1@hosp.vn",
    "user_full_name": "Nguyễn Văn A",
    "device_model": "MDL-MON-PHILIPS-X3",
    "training_program": "TRN-MON-INIT-01",
    "competency_level": "Operator",
    "achieved_date": "2026-05-20",
    "expiry_date": "2028-05-20",
    "days_until_expiry": 745,
    "workflow_state": "Active",
    "department_at_assessment": "ICU"
  }],
  "pagination": {...}
}
```

#### 3.3.2 `get_user_competencies` (self-service)

| Method | GET |
|---|---|
| Permission | All authenticated; nếu `user` param != session.user thì cần role `_SIGNOFF_ROLES` hoặc `Workshop Head`/`Tổ HC-QLCL` |

**Params:** `user` (default session.user).

**Response:**

```json
{
  "user": "ktv1@hosp.vn",
  "competencies": [
    {"name": "...", "device_model": "...", "expiry_date": "...",
     "status": "Active", "days_until_expiry": 745,
     "recertification_due_date": "...", "certificate_file": "..."}
  ],
  "summary": {"active": 3, "expiring": 1, "expired": 0, "revoked": 0}
}
```

**Errors:** `FORBIDDEN`.

#### 3.3.3 `get_asset_operator_coverage`

| Method | GET |
|---|---|
| Permission | All authenticated |

**Params:** `asset` (Asset name).

**Response:**

```json
{
  "asset": "AC-ASSET-2026-0001",
  "device_model": "MDL-MON-PHILIPS-X3",
  "department": "ICU",
  "asset_class": "III",
  "operator_count": 5,
  "operator_users": ["ktv1@hosp.vn", "ktv2@...", "..."],
  "required_min": 2,
  "gate_pass": true
}
```

**Used by:** IMM-04 Clinical_Release validate.

**Errors:** `NOT_FOUND` (asset không tồn tại).

#### 3.3.4 `get_competency_gaps_by_dept`

| Method | GET |
|---|---|
| Permission | Workshop Head, VP Block2, CMMS Admin, Tổ HC-QLCL |

**Response:**

```json
{
  "report_date": "2026-05-04",
  "departments": [
    {
      "department": "ICU",
      "device_class_II": {"total_assets": 15, "competent_users": 28, "required_min": 15, "gap": 0, "pct": 100},
      "device_class_III": {"total_assets": 5, "competent_users": 7, "required_min": 10, "gap": 3, "pct": 70}
    }
  ],
  "total_gap_assets": 8
}
```

#### 3.3.5 `get_expiring_competencies`

| Method | GET |
|---|---|

**Params:** `days` (int, default 90, max 365).

**Response:** `{days, count, items: [...]}` — fields: name, user, device_model, expiry_date, days_until_expiry, department_at_assessment.

#### 3.3.6 `revoke_competency`

| Method | POST |
|---|---|
| Roles | `_REVOKE_ROLES` = {Tổ HC-QLCL, CMMS Admin} |

**Body:** `name`, `revoke_reason` (reqd, ≥ 30 ký tự), `revoke_capa_ref` (Link CAPA, reqd nếu reason chứa "incident"/"sự cố" — VR-08).

**Behavior:**

1. Validate `_REVOKE_ROLES` (FORBIDDEN nếu fail).
2. Validate VR-08.
3. Set `workflow_state="Revoked"`, `revoked_by=session.user`, `revoked_date=now()`.
4. `invalidate_authorization_cache`.
5. Log IMM Audit Trail action="REVOKE".
6. Quét WO open assigned cho user → flag + email Workshop Head.

**Response:** `{name, new_state: "Revoked", flagged_work_orders: [...]}`.

**Errors:** `FORBIDDEN`, `NOT_FOUND`, `INVALID_STATE` (đã Revoked), `VALIDATION_ERROR`.

#### 3.3.7 `recertify_competency`

| Method | POST |
|---|---|
| Roles | Tổ HC-QLCL, CMMS Admin |

**Body:** `name`, `new_session_name` (nếu đã có session đầu vào) | `auto_create_session=true` (tạo placeholder).

**Behavior:** Gọi `services.imm06.trigger_recertification(name)` → tạo Refresher Session Planned hoặc liên kết session đã có.

**Response:** `{name, new_session: "TRN-2026-0099", action: "created"|"linked"}`.

#### 3.3.8 `signoff_competency`

| Method | POST |
|---|---|
| Roles | `_SIGNOFF_ROLES` |

**Body:** `name`.

**Behavior:**

1. Validate session.user thuộc `_SIGNOFF_ROLES` AND user của competency thuộc khoa của session.user (Department Manager scope) HOẶC role thuộc {Workshop Head, Tổ HC-QLCL, CMMS Admin} (override scope).
2. Validate VR-07 + workflow state = Pending Assessment.
3. Set `supervisor_signoff`, `signoff_date`, compute `expiry_date = achieved_date + validity_months`, `recertification_due_date = expiry_date - 60d`.
4. Chuyển workflow → Active.
5. Gọi `archive_old_competency(user, device_model, exclude=name)` (BR-06-11).
6. `invalidate_authorization_cache`.
7. Email user.

**Response:** `{name, new_state: "Active", expiry_date, recertification_due_date}`.

---

### 3.4 Authorization Gate (cross-module hook)

#### 3.4.1 `check_user_authorization`

| Method | GET |
|---|---|
| Permission | All authenticated; **internal use** bởi IMM-08/09/12 |

**Params:** `user`, `device_model`.

**Behavior:** Cached 5 min TTL. Query:

```sql
SELECT name, workflow_state, expiry_date, competency_level
FROM `tabIMM User Competency`
WHERE user = %s AND device_model = %s AND workflow_state = 'Active'
ORDER BY expiry_date DESC LIMIT 1
```

**Response (authorized):**

```json
{
  "authorized": true,
  "competency": "COMP-2026-0301",
  "competency_level": "Operator",
  "status": "Active",
  "expiry_date": "2028-05-20",
  "days_until_expiry": 745
}
```

**Response (not authorized):**

```json
{
  "authorized": false,
  "competency": null,
  "status": "None",
  "reason": "Người dùng chưa có Active competency cho thiết bị này"
}
```

Hoặc:

```json
{
  "authorized": false,
  "competency": "COMP-2026-0099",
  "status": "Expired",
  "reason": "Năng lực đã hết hạn từ 2026-04-30 — yêu cầu tái chứng nhận"
}
```

**Errors:** `NOT_FOUND` (device_model không tồn tại).

---

### 3.5 Dashboard

#### 3.5.1 `get_dashboard_stats`

| Method | GET |
|---|---|
| Permission | Workshop Head, VP Block2, CMMS Admin, Tổ HC-QLCL |

**Response:**

```json
{
  "kpis": {
    "total_active_competencies": 287,
    "expiring_90d": 24,
    "expired_not_renewed": 6,
    "users_competent_pct": 78.5,
    "training_completion_rate_90d": 92.0,
    "average_pass_rate_90d": 87.5,
    "total_gap_assets_class3": 8
  },
  "expiry_timeline": [
    {"name": "COMP-...", "user": "...", "device_model": "...",
     "expiry_date": "...", "days_until_expiry": 7}
  ],
  "compliance_by_dept": [
    {"dept": "ICU", "total_users": 30, "competent_users": 28,
     "pct": 93.3, "gap_class3": 0}
  ],
  "recent_sessions": [
    {"name": "TRN-...", "training_program": "...",
     "session_date": "...", "participant_count": 15, "pass_count": 13}
  ]
}
```

---

## 4. Error Codes

### 4.1 HTTP Status

| Code | Ý nghĩa |
|---|---|
| 200 | OK (kiểm tra `success` trong body) |
| 401 | Thiếu/sai auth |
| 403 | Frappe permission deny |
| 500 | Server error (xem `frappe.log_error`) |

### 4.2 Application Error Codes

| Code | Endpoint | Mô tả |
|---|---|---|
| `INVALID_FILTERS` | list_* | filters JSON parse fail |
| `INVALID_DATA` | create/update_* | body JSON parse fail |
| `NOT_FOUND` | get_*, update_*, complete/cancel_session, signoff/revoke/recertify_competency, check_user_authorization, get_asset_operator_coverage | Record không tồn tại |
| `FORBIDDEN` | create/update_program, create/confirm/complete/cancel_session, signoff/revoke_competency | Role không match |
| `INVALID_STATE` | confirm/complete/cancel_session, signoff/revoke_competency, recertify | workflow_state không phù hợp action |
| `VALIDATION_ERROR` | create/update_*, complete_session, signoff/revoke | VR-XX failure |
| `CREATE_ERROR` | create_program, create_session | Insert exception |
| `NOT_AUTHORIZED` | check_user_authorization | (Trong response body, không phải HTTP code) — flag user thiếu competency |

---

## 5. Webhook / Realtime Events

IMM-06 publish realtime event qua `frappe.publish_realtime` cho dashboard live update:

| Event channel | Payload | Trigger |
|---|---|---|
| `imm06_competency_changed` | `{user, device_model, old_state, new_state}` | `IMMUserCompetency.on_update` workflow_state change |
| `imm06_session_completed` | `{session, pass_count, fail_count}` | `complete_session` API |
| `imm06_gap_alert` | `{department, device_class, gap_count}` | Weekly gap report nếu gap > 0 |

Dashboard frontend subscribe channel để refresh KPI mà không cần poll.

---

## 6. Implementation Notes

| # | Note |
|---|---|
| 1 | `check_user_authorization` được cache 5 min TTL. Cache invalidate trong `IMMUserCompetency.on_update` và `auto_expire_competency` scheduler. |
| 2 | `complete_session` là endpoint phức tạp nhất — wrap trong transaction; nếu tạo competency fail giữa chừng phải rollback session state. Dùng `frappe.db.savepoint`. |
| 3 | `signoff_competency` permission scope check 2 lớp: (a) role IN `_SIGNOFF_ROLES`, (b) Department Manager chỉ sign-off người trong khoa. Workshop Head / Tổ HC-QLCL / CMMS Admin override scope. |
| 4 | `revoke_competency` keyword detection cho VR-08 dùng case-insensitive search trong `revoke_reason`: `["incident","sự cố","tai nạn","sai phạm"]`. |
| 5 | `get_asset_operator_coverage` query cần JOIN AC Asset + IMM User Competency theo device_model + department — chuẩn bị composite index. |
| 6 | `update_program` BR-06-04 trigger: dùng `Document.has_value_changed()` cho từng field — không trigger nếu chỉ sửa metadata không trọng yếu (ví dụ sửa description). |
| 7 | Self-service `get_user_competencies` không cần param nếu xem own → tự fill `user=session.user`. |
| 8 | `recertify_competency` không tự động chuyển status Expired → Active — vẫn phải qua workflow new session.complete + sign-off. |
| 9 | Pagination: max `page_size=100` enforce server-side cho mọi list endpoint. |
| 10 | Naming series Session: `TRN-.YYYY.-.#####`; Competency: `COMP-.YYYY.-.#####`; Gap Report: `GAP-.YYYY.-.#####`; Program: bằng `program_code` (user-defined). |
| 11 | Tất cả error message tiếng Việt qua `frappe._()` — front-end hiển thị trực tiếp `response.error`. |
| 12 | Cross-module call: IMM-08/09/12 import `from assetcore.services.imm06 import validate_user_authorization` — không gọi qua HTTP để tránh overhead. |

---

## 7. OpenAPI Excerpt

Đặc tả OpenAPI 3.0 đầy đủ sẽ generate qua skill `/dev:generate-api-contract imm06`. Excerpt:

```yaml
openapi: 3.0.3
info:
  title: AssetCore IMM-06 Training & Competency API
  version: 0.1.0
servers:
  - url: /api/method/assetcore.api.imm06
paths:
  /check_user_authorization:
    get:
      summary: Validate user authorization for device model
      parameters:
        - name: user
          in: query
          required: true
          schema: {type: string}
        - name: device_model
          in: query
          required: true
          schema: {type: string}
      responses:
        '200':
          description: OK
          content:
            application/json:
              schema:
                type: object
                properties:
                  message:
                    type: object
                    properties:
                      success: {type: boolean}
                      data:
                        type: object
                        properties:
                          authorized: {type: boolean}
                          competency: {type: string, nullable: true}
                          status: {type: string}
                          expiry_date: {type: string, format: date, nullable: true}
                          reason: {type: string, nullable: true}
```

---

## 8. Sample Cross-module Call (IMM-08 PM)

```python
# assetcore/.../doctype/work_order/work_order.py (IMM-08)
def assign_technician(self, technician_user):
    from assetcore.services.imm06 import validate_user_authorization
    asset = frappe.get_doc("AC Asset", self.asset)
    auth = validate_user_authorization(technician_user, asset.device_model)
    if not auth["authorized"]:
        frappe.throw(_("BR-06-01: Không thể giao Work Order — {reason}")
                     .format(reason=auth["reason"]),
                     title=_("Năng lực không đủ"))
    self.assigned_to = technician_user
    self.save()
```

Hoặc qua HTTP từ frontend:

```http
GET /api/method/assetcore.api.imm06.check_user_authorization?user=ktv1@hosp.vn&device_model=MDL-MON-PHILIPS-X3
```

```json
{
  "message": {
    "success": true,
    "data": {
      "authorized": true,
      "competency": "COMP-2026-0301",
      "competency_level": "Operator",
      "status": "Active",
      "expiry_date": "2028-05-20",
      "days_until_expiry": 745
    }
  }
}
```
