# 05 — API Specification — IMM-06 Đào tạo & Quản lý năng lực

| Mục | Giá trị |
|---|---|
| Module | IMM-06 — User Training & Competency Management |
| Phiên bản tài liệu | 0.1.0 |
| Ngày cập nhật | 2026-05-08 |
| Base path | `assetcore.api.imm06` |
| URL pattern | `/api/method/assetcore.api.imm06.<function>` |
| Liên kết | [02 Analysis](./02_Analysis_Design.md) · [04 Backend](./04_Backend_Design.md) · [06 Frontend](./06_Frontend_Design.md) |

> ✅ Implemented (Wave 2) — endpoints đã whitelist trong `assetcore/api/imm06.py` (**25** `@frappe.whitelist()` functions, đếm ngày 2026-05-18 trên branch `feature/hieuc/wave-2`). Khi có drift, code wins; cập nhật doc.

---

## §I API Conventions

### §I.1 Base URL

```
/api/method/assetcore.api.imm06.<function_name>
```

### §I.2 Response Envelope (chuẩn AssetCore)

**Thành công — HTTP 200:**

```json
{
  "success": true,
  "data": { /* payload */ }
}
```

**Lỗi — HTTP 200 (always):**

```json
{
  "success": false,
  "error": "Mô tả lỗi tiếng Việt",
  "code": "IDENTIFIER"
}
```

> **QUAN TRỌNG:** AssetCore dùng `{"success": true, "data": {...}}` — KHÔNG dùng `{"message": {"success": true, ...}}` (Frappe outer wrapper). Frontend parse: `response.json().message` để lấy object trên.
>
> Helpers tại `assetcore/utils/helpers.py`:
> ```python
> def _ok(data): return {"success": True, "data": data}
> def _err(msg, code="ERROR"): return {"success": False, "error": msg, "code": code}
> ```

### §I.3 Error Codes (chuẩn AssetCore `constants.py`)

| Code | Ý nghĩa |
|---|---|
| `NOT_FOUND` | Record không tồn tại |
| `FORBIDDEN` | Role không match |
| `VALIDATION` | VR-XX failure — kèm field name trong error message |
| `BUSINESS_RULE` | BR-XX failure |
| `INVALID_PARAMS` | Tham số không hợp lệ (parse fail, type error) |
| `INTERNAL` | Lỗi server ngoài tầm kiểm soát |

Module-specific prefixed codes: `TRN-001..TRN-099` (Program/Session), `COMP-001..COMP-099` (Competency).

### §I.4 Authentication

| Phương thức | Header / Cookie |
|---|---|
| API Token | `Authorization: token <api_key>:<api_secret>` |
| Session (FE SPA) | `Cookie: sid=<session_id>` |

User không có Role hợp lệ → HTTP 200 `{"success": false, "error": "...", "code": "FORBIDDEN"}`.

### §I.5 Pagination (list endpoints)

```json
{
  "items": [...],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 137,
    "total_pages": 7
  }
}
```

`page` 1-based. `page_size` max = 100 (enforce server-side).

---

## §II Role Constants

```python
# assetcore/api/imm06.py

_DOCTYPE_PROGRAM    = "IMM Training Program"
_DOCTYPE_SESSION    = "IMM Training Session"
_DOCTYPE_COMPETENCY = "IMM User Competency"

_PROGRAM_WRITE_ROLES = {"IMM Training Officer", "IMM System Admin"}
_SESSION_WRITE_ROLES = {
    "IMM Training Officer", "IMM Biomed Technician",
    "IMM Workshop Lead", "IMM System Admin"
}
_SIGNOFF_ROLES = {
    "Department Manager", "IMM Workshop Lead",
    "IMM Training Officer", "IMM System Admin"
}
_REVOKE_ROLES  = {"IMM Training Officer", "IMM System Admin"}   # ⚠️ DEPRECATED — xem note dưới
_DASHBOARD_ROLES = {
    "IMM Workshop Lead", "IMM Training Officer",
    "IMM System Admin", "VP Block2"
}
```

> ⚠️ **Enforce THẬT là capability-based (`services/shared/rbac.py`), KHÔNG phải role-name set trên.** Các hằng role ở đây là tham chiếu lịch sử. **3 CTA vòng đời năng lực (sign-off/revoke/recertify) gate DUY NHẤT capability `training.submit`** (`_REVOKE_ROLES`/`_SIGNOFF_ROLES` **KHÔNG dùng** để enforce revoke/recertify từ Vòng 15 — ADR-IMM-06-04). Cấm hardcode role-name (anti-pattern RBAC dead-gate); đổi "ai được duyệt/thu hồi" = sửa DocPerm `delete` trên IMM Training Session ở `/app`, KHÔNG deploy code.

---

## §III Endpoints

### Group A — Training Program

#### A.1 `list_programs`

| Method | GET |
|---|---|
| Path | `/api/method/assetcore.api.imm06.list_programs` |
| Permission | All authenticated |

**Query params:**

| Param | Kiểu | Bắt buộc | Mô tả |
|---|---|---|---|
| `filters` | JSON string | Không | Frappe-style filter object |
| `page` | int | Không | Trang (default 1) |
| `page_size` | int | Không | Kích thước (default 20, max 100) |

**Response 200:**

```json
{
  "success": true,
  "data": {
    "items": [
      {
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
      }
    ],
    "pagination": {"page": 1, "page_size": 20, "total": 23, "total_pages": 2}
  }
}
```

**Errors:** `INVALID_PARAMS` (filters JSON parse fail).

---

#### A.2 `get_program`

| Method | GET |
|---|---|
| Path | `/api/method/assetcore.api.imm06.get_program` |
| Permission | All authenticated |

**Query params:** `?name=TRN-MON-INIT-01`

**Response 200:**

```json
{
  "success": true,
  "data": {
    "name": "TRN-MON-INIT-01",
    "program_name": "Đào tạo cơ bản Monitor Philips X3",
    "training_type": "Initial",
    "target_device_model": "MDL-MON-PHILIPS-X3",
    "validity_period_months": 24,
    "passing_score_pct": 70,
    "assessment_method": "Both",
    "instructor_qualification_required": "Biomed Engineer",
    "content_outline": "<p>1. Tổng quan thiết bị ...</p>",
    "is_mandatory_for_operation": 1,
    "is_active": 1,
    "qms_doc_ref": "WI-IMMIS-06-01"
  }
}
```

**Errors:** `{"success": false, "error": "Chương trình đào tạo không tồn tại.", "code": "NOT_FOUND"}`

---

#### A.3 `create_program`

| Method | POST |
|---|---|
| Path | `/api/method/assetcore.api.imm06.create_program` |
| Roles | `_PROGRAM_WRITE_ROLES` |

**Request body:**

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

**Response 200:**

```json
{
  "success": true,
  "data": {
    "name": "TRN-MON-INIT-01",
    "is_active": 1
  }
}
```

**Errors:**

| Code | Mô tả |
|---|---|
| `FORBIDDEN` | Role không trong `_PROGRAM_WRITE_ROLES` |
| `INVALID_PARAMS` | `program_data` JSON parse fail |
| `VALIDATION` | VR-02 (điểm đạt), VR-03 (hiệu lực), VR-11 (device model không active) |
| `INTERNAL` | Insert exception |

---

#### A.4 `update_program`

| Method | POST |
|---|---|
| Path | `/api/method/assetcore.api.imm06.update_program` |
| Roles | `_PROGRAM_WRITE_ROLES` |

**Request body:** `{"name": "TRN-MON-INIT-01", "program_data": {...}}`

**Behavior:** Trigger BR-06-04 — nếu critical fields (`content_outline`, `passing_score_pct`, `assessment_method`, `duration_hours`) thay đổi → flag tất cả Active Competency tương ứng cho re-cert và tạo Document Request task cho Tổ HC-QLCL.

**Response 200:**

```json
{
  "success": true,
  "data": {
    "name": "TRN-MON-INIT-01",
    "recert_triggered": true,
    "affected_competencies_count": 23
  }
}
```

**Errors:** `FORBIDDEN`, `NOT_FOUND`, `VALIDATION`, `INVALID_PARAMS`

---

### Group B — Training Session

#### B.1 `list_sessions`

| Method | GET |
|---|---|
| Path | `/api/method/assetcore.api.imm06.list_sessions` |
| Permission | All authenticated |

**Query params:** `filters`, `page`, `page_size`

**Response 200:**

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "name": "TRN-2026-00042",
        "training_program": "TRN-MON-INIT-01",
        "session_date": "2026-05-20",
        "location": "Phòng đào tạo F3",
        "instructor": "biomed1@hosp.vn",
        "session_type": "Onsite",
        "workflow_state": "Confirmed",
        "participant_count": 15,
        "duration_planned_hours": 8
      }
    ],
    "pagination": {"page": 1, "page_size": 20, "total": 8, "total_pages": 1}
  }
}
```

---

#### B.2 `get_session`

| Method | GET |
|---|---|
| Service | `services/imm06.py::get_session` |
| Permission | All authenticated (dispatcher-auth) |
| Envelope | Decision-B `{ "success": true, "data": {...} }` |

**Query params:** `?name=TRN-2026-00042`

**Response 200:** Full session object + `participants` array (child rows) + **`allowed_transitions: string[]`** (enriched, KHÔNG phải DocType field).

`data.allowed_transitions` = danh sách **next-state hợp lệ** của máy trạng thái Session, tính SERVER-SIDE từ hằng SSoT `_SESSION_VALID_TRANSITIONS[workflow_state]` (xem 04 §VI.1a). Khớp EXACT theo từng state:

| `workflow_state` | `allowed_transitions` |
|---|---|
| Planned | `["Confirmed", "In Progress", "Cancelled"]` |
| Confirmed | `["In Progress", "Cancelled"]` |
| In Progress | `["Completed"]` |
| Completed | `["Verified"]` |
| Verified | `["Closed"]` |
| Closed | `[]` (terminal) |
| Cancelled | `[]` (terminal) |

FE gate mỗi CTA bằng `allowed_transitions.includes('<next-state>') && <capability>` (2 lớp — xem 06). `allowed_transitions` CHỈ là lớp state-machine; quyền vẫn do BE `_require_training_officer()` (training.write) enforce khi gọi CTA endpoint.

```json
{
  "success": true,
  "data": {
    "name": "TRN-2026-00042",
    "workflow_state": "Planned",
    "participants": [ /* child rows */ ],
    "allowed_transitions": ["Confirmed", "In Progress", "Cancelled"]
  }
}
```

**Errors:** `NOT_FOUND` (in-handler HTTP-200 + Error envelope, không phải HTTP-4xx).

---

#### B.3 `create_session`

| Method | POST |
|---|---|
| Roles | `_SESSION_WRITE_ROLES` |

**Request body:**

```json
{
  "session_data": {
    "training_program": "TRN-MON-INIT-01",
    "session_date": "2026-05-20",
    "location": "Phòng đào tạo F3",
    "instructor": "biomed1@hosp.vn",
    "session_type": "Onsite",
    "duration_planned_hours": 8,
    "participants": [
      {"user": "ktv1@hosp.vn", "department": "ICU", "role_at_session": "Operator"},
      {"user": "ktv2@hosp.vn", "department": "ICU", "role_at_session": "Operator"}
    ]
  }
}
```

**Side-effects:** Tạo session `workflow_state="Planned"`. Validate VR-04, VR-10. Gửi email mời participants.

**Response 200:**

```json
{
  "success": true,
  "data": {
    "name": "TRN-2026-00042",
    "workflow_state": "Planned",
    "participant_count": 15
  }
}
```

**Errors:** `FORBIDDEN`, `VALIDATION` (VR-04/VR-10), `INTERNAL`

---

#### B.4 `confirm_session`

| Method | POST |
|---|---|
| Roles | `IMM Training Officer`, `IMM System Admin` |

**Request body:** `{"name": "TRN-2026-00042"}`

**Behavior:** Validate VR-05 (≥1 participant), chuyển workflow Planned → Confirmed.

**Response 200:**

```json
{
  "success": true,
  "data": {
    "name": "TRN-2026-00042",
    "new_state": "Confirmed"
  }
}
```

**Errors:** `FORBIDDEN`, `NOT_FOUND`, `VALIDATION` (VR-05), `BUSINESS_RULE` (sai state)

---

#### B.4b `start_session`

| Method | POST |
|---|---|
| Roles | `_SESSION_WRITE_ROLES` |
| Service | `services/imm06.py::start_training_session` |

**Request body:** `{"name": "TRN-2026-00042"}`

**Behavior:** Confirmed → In Progress. Validate `session_date` không ở quá khứ quá ngưỡng. Đặt `started_at = now`.

**Response 200:** `{ "success": true, "data": { "name": "...", "new_state": "In Progress" } }`

**Errors:** `FORBIDDEN`, `NOT_FOUND`, `BUSINESS_RULE` (sai state), `VALIDATION`

---

#### B.4c `enroll_participants`

| Method | POST |
|---|---|
| Roles | `_SESSION_WRITE_ROLES` |
| Service | `services/imm06.py::enroll_participants` |

**Request body:** `{"name": "TRN-2026-00042", "participants": [{"user": "ktv1@hosp.vn", "department": "ICU", "role_at_session": "Operator"}, ...]}`

**Behavior:** Thêm participants vào child table `participants`. Validate không trùng user trong cùng session.

**Response 200:** `{ "success": true, "data": { "name": "...", "enrolled": 3 } }`

**Errors:** `FORBIDDEN`, `NOT_FOUND`, `VALIDATION` (duplicate user)

---

#### B.4d `remove_participant`

| Method | POST |
|---|---|
| Roles | `_SESSION_WRITE_ROLES` |
| Service | `services/imm06.py::remove_participant` |

**Request body:** `{"name": "TRN-2026-00042", "row_name": "<child_row_name>"}`

**Behavior:** Xóa 1 participant row khỏi session. Chỉ cho phép khi session ở trạng thái Planned/Confirmed.

**Response 200:** `{ "success": true, "data": { "removed": true } }`

**Errors:** `FORBIDDEN`, `NOT_FOUND`, `BUSINESS_RULE` (session đã bắt đầu)

---

#### B.5 `complete_session`

| Method | POST |
|---|---|
| Roles | `IMM Training Officer`, `IMM Biomed Technician` (instructor), `IMM System Admin` |

**Request body:**

```json
{
  "name": "TRN-2026-00042",
  "participants_results": [
    {
      "user": "ktv1@hosp.vn",
      "theory_score": 85,
      "practical_score": 80,
      "attendance_pct": 100,
      "remarks": ""
    },
    {
      "user": "ktv2@hosp.vn",
      "theory_score": 55,
      "practical_score": 60,
      "attendance_pct": 75,
      "remarks": "Vắng buổi sáng"
    }
  ]
}
```

**Behavior:**
1. Validate VR-06 (scores reqd nếu `program.assessment_method="Both"`).
2. Compute `overall_result` per participant: `attendance_pct >= 80% AND avg(theory, practical) >= passing_score_pct` → Pass.
3. Chuyển workflow In Progress → Completed.
4. Gọi `services.imm06.create_competency_from_session(name)` → tạo Pending Assessment competency cho mọi Pass.
5. Gửi email cho supervisor (Department Manager) yêu cầu sign-off.

**Response 200:**

```json
{
  "success": true,
  "data": {
    "name": "TRN-2026-00042",
    "new_state": "Completed",
    "participants_summary": {
      "total": 15,
      "pass": 13,
      "fail": 1,
      "conditional": 1
    },
    "competencies_created": ["COMP-2026-0301", "COMP-2026-0302"]
  }
}
```

**Errors:** `FORBIDDEN`, `NOT_FOUND`, `VALIDATION` (VR-06), `BUSINESS_RULE` (sai state), `INTERNAL`

---

#### B.6 `cancel_session`

| Method | POST |
|---|---|
| Roles | `IMM Training Officer`, `IMM System Admin` |

**Request body:** `{"name": "TRN-2026-00042", "cancel_reason": "Giảng viên bệnh"}`

**Behavior:** Block nếu `workflow_state IN ("Verified", "Closed")` (BR-06-12).

**Response 200:**

```json
{
  "success": true,
  "data": {
    "name": "TRN-2026-00042",
    "new_state": "Cancelled"
  }
}
```

**Errors:** `FORBIDDEN`, `NOT_FOUND`, `BUSINESS_RULE` (BR-06-12 — không thể hủy sau Verified)

---

#### B.7 `verify_session`

| Method | POST |
|---|---|
| Roles | `IMM QA Officer`, `IMM Training Officer`, `IMM System Admin` |
| Service | `services/imm06.py::verify_session` |

**Request body:** `{"name": "TRN-2026-00042"}`

**Behavior:** Completed → Verified. QA Officer xác nhận kết quả buổi đào tạo trước khi competency được phép `signoff`. Ghi `verified_by`, `verified_at`.

**Response 200:** `{ "success": true, "data": { "name": "...", "new_state": "Verified" } }`

**Errors:** `FORBIDDEN`, `NOT_FOUND`, `BUSINESS_RULE` (sai state)

---

#### B.8 `close_session`

| Method | POST |
|---|---|
| Roles | `IMM Training Officer`, `IMM System Admin` |
| Service | `services/imm06.py::close_session` |

**Request body:** `{"name": "TRN-2026-00042"}`

**Behavior:** Verified → Closed. Khoá final state — không sửa được participant results. Gắn audit trail.

**Response 200:** `{ "success": true, "data": { "name": "...", "new_state": "Closed" } }`

**Errors:** `FORBIDDEN`, `NOT_FOUND`, `BUSINESS_RULE` (chưa Verified)

---

### Group C — User Competency

#### C.1 `list_competencies`

| Method | GET |
|---|---|
| Permission | Role-scoped: Operator → own only; Department Manager / Clinical Head → own dept; Tổ HC-QLCL / Workshop Lead / CMMS Admin → toàn bộ |

**Query params:** `filters`, `page`, `page_size`

**Response 200:**

```json
{
  "success": true,
  "data": {
    "items": [
      {
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
      }
    ],
    "pagination": {"page": 1, "page_size": 20, "total": 287, "total_pages": 15}
  }
}
```

---

#### C.1b `get_competency` (server-driven CTA — MỚI Vòng 15)

| Method | GET |
|---|---|
| Path | `/api/method/assetcore.api.imm06.get_competency?name=COMP-2026-0301` |
| Service | `services/imm06.py::get_competency` (MỚI — parity `get_session`) |
| Permission | All authenticated (đọc); ghi qua C.5b/C.6/C.7/C.8/C.9 |

**Response 200:** Full IMM User Competency object (enriched `user_full_name`, `device_model_name`) + **2 field enriched (KHÔNG phải DocType field)**:
- **`allowed_transitions: string[]`** — nhãn ACTION hợp lệ của máy trạng thái năng lực, tính SERVER-SIDE từ SSoT `_COMPETENCY_VALID_TRANSITIONS[workflow_state]` (xem 04 §VI.2a/§VI.2b). Value ∈ `{"Sign-off","Revoke","Recertify","Suspend","Restore"}` — **KHÁC `get_session`** (session trả next-state).
- **`can_signoff` / `can_revoke` / `can_recertify` / `can_suspend` / `can_restore: boolean`** — cờ quyền = `(ACTION in allowed_transitions) && rbac.can("training.submit")` (lọc CẢ state LẪN capability — chống dead-control). FE gate = `allowed_transitions.includes('<Action>') && can_<action>` (2 lớp AND — xem 06).

| `workflow_state` | `allowed_transitions` |
|---|---|
| `Pending Assessment` | `["Sign-off"]` |
| `Active` | `["Revoke", "Suspend"]` |
| `Expiring` | `["Recertify", "Revoke"]` |
| `Expired` | `["Recertify", "Revoke"]` |
| `Suspended` | `["Restore", "Revoke"]` |
| `Revoked` (terminal) | `[]` |

> **Vòng 26:** `Active` chứa `Suspend` (thứ tự `["Revoke","Suspend"]`); `Suspended == ["Restore","Revoke"]` (thứ tự ổn định — FE/test list-eq). Xem C.8/C.9.

```json
{
  "success": true,
  "data": {
    "name": "COMP-2026-0301",
    "user": "ktv1@hosp.vn",
    "user_full_name": "Nguyễn Văn A",
    "device_model": "MDL-MON-PHILIPS-X3",
    "device_model_name": "Monitor Philips X3",
    "competency_level": "Operator",
    "workflow_state": "Expiring",
    "achieved_date": "2026-05-20",
    "expiry_date": "2026-08-20",
    "days_until_expiry": 41,
    "recertification_due_date": "2026-06-21",
    "supervisor_signoff": "manager@hosp.vn",
    "signoff_date": "2026-05-21",
    "allowed_transitions": ["Recertify", "Revoke"],
    "can_signoff": false,
    "can_revoke": true,
    "can_recertify": true
  }
}
```

**Errors:** `NOT_FOUND` (name không tồn tại)

> **Endpoint ghi (CTA vòng đời):** `signoff_competency` (C.5b), `revoke_competency` (C.6), `recertify_competency` (C.7) — cùng gate capability `training.submit` (ADR-IMM-06-04), state-guard theo SSoT `_COMPETENCY_VALID_TRANSITIONS`. Xem cuối Group C.

---

#### C.2 `get_user_competencies` (self-service)

| Method | GET |
|---|---|
| Path | `/api/method/assetcore.api.imm06.get_user_competencies` — handler `api/imm06.py:189` → `_run(svc.get_user_competencies, user or frappe.session.user)` |
| Service | `services/imm06.py:1527` → `return {"user": target_user, "items": rows}` (`:1546`) |
| Permission | **AS-IS**: mọi user authenticated (bare `@whitelist`, **0 `rbac.require`**). Bỏ trống `user` ⇒ `frappe.session.user`. ⚠️ Cross-user (`?user=<người-khác>`) **hiện KHÔNG enforce** — xem Self-Correction dưới. |

**Query params:** `?user=ktv1@hosp.vn` (optional — default = `frappe.session.user`)

**Response 200** (VERBATIM shape LIVE — grounded `services/imm06.py:1539-1546`):

```json
{
  "success": true,
  "data": {
    "user": "ktv1@hosp.vn",
    "items": [
      {
        "name": "COMP-2026-0301",
        "device_model": "MDL-MON-PHILIPS-X3",
        "training_program": "TP-2026-0007",
        "competency_level": "Operator",
        "workflow_state": "Active",
        "achieved_date": "2026-05-20",
        "expiry_date": "2028-05-20",
        "days_until_expiry": 745,
        "is_expired": 0,
        "last_assessment_score": 88.5
      }
    ]
  }
}
```

**Item = 10 field** (đúng field-select `UserCompetencyRepo.list`): `name` · `device_model` (Link id RAW, nullable) · `training_program` (Link id RAW, nullable) · `competency_level` (Select `[Trainee/Operator/Senior Operator/Trainer]`, nullable) · `workflow_state` (`[Pending Assessment/Active/Expiring/Expired/Suspended/Revoked]`) · `achieved_date`/`expiry_date` (date, nullable) · `days_until_expiry` (integer **SIGNED** — âm=quá hạn) · `is_expired` (integer **0/1** — Check-quirk READ) · `last_assessment_score` (number, nullable). `items` RỖNG hợp-lệ (user 0 năng lực). Order: `expiry_date asc`, `page_size=500` (KHÔNG pagination-param).

**Errors:** guest → dispatcher-403 (status-line); lỗi khác → HTTP-200 body `Error` (`_run` `_err`).

> ⚠️ **Self-Correction 2026-07-15 (CR-34) — response CŨ STALE, đã sửa khớp LIVE:** bản trước ghi `data.competencies[]` + `user_full_name` + `summary{}` + item-field `recertification_due_date`/`certificate_file`/`device_model_name` — **KHÔNG khớp service THẬT**. `get_user_competencies` @`:1527-1546` trả DUY NHẤT `{user, items[10-field]}` (KHÔNG `user_full_name`/`summary`/enrich display — enrich CHỈ có ở `get_competency` @`:1584`). Đã đổi `competencies`→`items`, gỡ field không tồn tại, thêm 10 field THẬT. Permission "cross-user cần `_SIGNOFF_ROLES`" cũng **aspirational** (handler LIVE 0 gate cross-user) → sửa thành AS-IS + flag `T-IMM06-AUTHZ` (có nên gate? = backend change → follow-on).

> 📱 **Cross-ref Mobile-BE contract (CR-34 — MỞ NHÁNH IMM-06, mobile Trục B, 2026-07-15):** endpoint này được surface trong OpenAPI mobile [`docs/mobile/openapi/assetcore-mobile.openapi.yaml`](../mobile/openapi/assetcore-mobile.openapi.yaml) tại path `/api/method/assetcore.api.imm06.get_user_competencies` (opId **`getUserCompetencies`**, **tag `training` MỚI** — endpoint IMM-06 ĐẦU TIÊN trong mirror). **1 typed query-param** `user` (`in:query, type:string, required:false`, KHÔNG `default` — BE default động `session.user`; pattern CR-05). 200 = `oneOf [UserCompetenciesEnvelope, Error]` (route-by-VALUE `body.success`, 0 discriminator — `_run` CÓ nhánh `_err`); **3 schema CLOSED**: `UserCompetencyListItem` (10 field VERBATIM — `is_expired` integer `enum[0,1]` Check-quirk CR-01, `days_until_expiry` integer SIGNED, `competency_level`/`workflow_state` enum) / `UserCompetenciesData` `{user, items[]}` / `UserCompetenciesEnvelope` `{success.enum[true], data}`. **∈ `_MVP_READ_ENVELOPE` ∉ `_MVP_LIST_ENVELOPE`** (flat-object read). Slot `{200,401,403}`; 403 SINGLE dispatcher-only. Enrich `device_model_name` **DEFERRED** (backend+reload = HARD-STOP) + authz cross-user AS-IS = follow-on. **CONTRACT-ONLY** (0 `.py`/reload/migrate). Chi tiết hợp đồng + ADR: [`docs/mobile/04-api-contract.md §8.53`](../mobile/04-api-contract.md) + [`ADR-MOBILE-059.md`](../mobile/ADR-MOBILE-059.md).

---

#### C.3 `get_asset_operator_coverage`

| Method | GET |
|---|---|
| Permission | All authenticated |

**Query params:** `?asset=AC-ASSET-2026-0001`

**Response 200:**

```json
{
  "success": true,
  "data": {
    "asset": "AC-ASSET-2026-0001",
    "device_model": "MDL-MON-PHILIPS-X3",
    "department": "ICU",
    "asset_class": "III",
    "operator_count": 5,
    "operator_users": ["ktv1@hosp.vn", "ktv2@hosp.vn"],
    "required_min": 2,
    "gate_pass": true
  }
}
```

**Used by:** IMM-04 Clinical Release validate gate.

**Errors:** `NOT_FOUND` (asset không tồn tại)

---

#### C.4 `get_competency_gaps_by_dept`

| Method | GET |
|---|---|
| Permission | `_DASHBOARD_ROLES` |

**Response 200:**

```json
{
  "success": true,
  "data": {
    "report_date": "2026-05-04",
    "departments": [
      {
        "department": "ICU",
        "device_class_II": {
          "total_assets": 15,
          "competent_users": 28,
          "required_min": 15,
          "gap": 0,
          "pct": 100
        },
        "device_class_III": {
          "total_assets": 5,
          "competent_users": 7,
          "required_min": 10,
          "gap": 3,
          "pct": 70
        }
      }
    ],
    "total_gap_assets": 8
  }
}
```

**Errors:** `FORBIDDEN`

---

#### C.5 `get_expiring_competencies`

| Method | GET |
|---|---|
| Permission | `_DASHBOARD_ROLES` |

**Query params:** `?days=60` (default **60** = `EXPIRY_WINDOW_DAYS`; drill có thể truyền 90/365, max 365)

> **BR-06-14 parity (2026-06-04):** Khi gọi với `days=60` (default), filter của endpoint **bằng** `_expiring_competency_filter()` SoT → `count` ở response = `get_dashboard_stats().competencies.expiring` (card == drill, INVARIANT đo được). Predicate LIVE: `workflow_state ∈ {Active, Expiring} ∧ expiry_date ∈ [today, today+days]` (window đóng 2 đầu, loại Revoked/Suspended). Chi tiết: `04_Backend_Design.md §V.2`.

**Response 200:**

```json
{
  "success": true,
  "data": {
    "days": 90,
    "count": 24,
    "items": [
      {
        "name": "COMP-2026-0099",
        "user": "ktv3@hosp.vn",
        "user_full_name": "Trần Thị B",
        "device_model": "MDL-CT-SIEMENS-S5",
        "expiry_date": "2026-06-15",
        "days_until_expiry": 38,
        "department_at_assessment": "Radiology"
      }
    ]
  }
}
```

---

#### C.5b `signoff_competency` — Phê duyệt (Pending Assessment → Active)

| Method | POST |
|---|---|
| Path | `/api/method/assetcore.api.imm06.signoff_competency` — Service `svc.signoff_competency_by_name(name)` |
| Body | `{ "name": "COMP-2026-0301" }` |
| Permission | **capability `training.submit`** (Super Admin / Training Manager) — in-handler gate (đã có, imm06.py:204) |
| State guard | Chỉ từ `Pending Assessment` (SSoT `_COMPETENCY_VALID_TRANSITIONS` → `_assert_competency_action`) |

**RBAC:** API gate `rbac.can("training.submit")` **inline TRƯỚC `_run`** → thiếu quyền trả **HTTP-200** `{"success": false, "code": "FORBIDDEN"}` (in-handler cap-403, KHÔNG raise→HTTP-4xx). Side-effect: set `supervisor_signoff`=session.user, `signoff_date`, `workflow_state = Active`; recompute `expiry_date`/`recertification_due_date` (SoT §V.1); archive bản Active cũ (BR-06-11, user × device_model → Suspended); invalidate auth-cache; Lifecycle Event `competency_signoff` (audit — CLAUDE.md §5 / NĐ98).

**Response 200:** `{ "name": "…", "workflow_state": "Active", "expiry_date": "…" }`

**Errors:** `FORBIDDEN` (thiếu `training.submit`), `NOT_FOUND`, `BAD_STATE` (state ≠ Pending Assessment).

---

#### C.6 `revoke_competency` — Thu hồi (→ Revoked, terminal)

| Method | POST |
|---|---|
| Path | `/api/method/assetcore.api.imm06.revoke_competency` — Service `svc.revoke_competency_with_capa(name, reason, capa_ref)` |
| Body | `{ "name": "COMP-2026-0301", "reason": "…", "capa_ref": "CAPA-2026-0011" }` (`reason` bắt buộc; `capa_ref` tùy chọn) |
| Permission | **capability `training.submit`** — in-handler gate (Vòng 15: parity signoff; TRƯỚC đây service gate `training.write` → asymmetry, xem ADR-IMM-06-04) |
| State guard | Từ `Active` / `Expiring` / `Expired` / `Suspended` (KHÔNG `Pending Assessment`, KHÔNG `Revoked`) |

**RBAC (Vòng 15 — sửa asymmetry):** thêm inline `rbac.can("training.submit")` ở API `revoke_competency` (api/imm06.py:213, parity signoff) **và** đổi service gate `_require_training_officer()`(→training.write) → `rbac.require("training.submit")` trong `revoke_competency` (imm06.py:418). Side-effect: `workflow_state = Revoked`, `revoke_reason`=reason, `revoked_by`, `revoked_date`, optional `revoke_capa_ref`; invalidate auth-cache; Lifecycle Event `competency_revoked`.

> ⚠️ **Field name (Self-Correction):** body dùng **`reason`** + **`capa_ref`** (khớp signature `revoke_competency(name, reason, capa_ref)` — api/imm06.py:213), KHÔNG phải `revoke_reason`/`revoke_capa_ref` (tên field DocType nội bộ). Bản doc cũ ghi sai — đã sửa.

**Response 200:** `{ "name": "…", "workflow_state": "Revoked" }`

**Errors:** `FORBIDDEN` (thiếu `training.submit` — HTTP-200 envelope, **state KHÔNG đổi**), `NOT_FOUND`, `VALIDATION` (thiếu `reason`), `BAD_STATE` (state = Pending Assessment / Revoked).

---

#### C.7 `recertify_competency` — Tái chứng nhận (tạo bản mới + old → Expired)

| Method | POST |
|---|---|
| Path | `/api/method/assetcore.api.imm06.recertify_competency` — Service `svc.recertify_competency(name, new_session)` |
| Body | `{ "name": "<old-comp>", "new_session": "TRN-2026-0099" }` |
| Permission | **capability `training.submit`** — in-handler gate (Vòng 15: parity; TRƯỚC đây service `training.write`) |
| State guard | Bản cũ ở `Expiring` / `Expired` (Vòng 15 thêm guard — service cũ KHÔNG kiểm state nguồn) |

**RBAC (Vòng 15):** inline `rbac.can("training.submit")` ở API `recertify_competency` (api/imm06.py:219) + service `rbac.require("training.submit")` (imm06.py:1416). Precondition nghiệp vụ (giữ nguyên): `new_session` phải `Completed`, participant = `old.user` với `overall_result == Pass`. Side-effect: tạo **IMM User Competency mới** (`Pending Assessment`, dates theo SoT §V.1) từ session Refresher; mark bản cũ → `Expired` + `is_expired=1`; Lifecycle Event `competency_recertified` (from old).

> ⚠️ **Signature (Self-Correction):** bản doc cũ mô tả `auto_create_session`/`new_session_name` + `trigger_recertification` — SAI. Signature thật = `recertify_competency(name, new_session)`; caller PHẢI truyền `new_session` (mã Refresher Session đã Completed). `trigger_recertification` là job scheduler tạo placeholder, KHÔNG phải endpoint này.

**Response 200:** `{ "old_competency": "<old>", "new_competency": "<new-COMP>" }`

**Errors:** `FORBIDDEN` (thiếu `training.submit` — HTTP-200, state cũ KHÔNG đổi), `NOT_FOUND` (comp/session), `BAD_STATE` (bản cũ ∉ {Expiring, Expired}), `VALIDATION` (session chưa Completed / participant chưa Pass).

> **Note 2 loại 403 (spec-contract, LL-BE-42..49):** cả 3 CTA — lỗi thiếu quyền = **in-handler cap-403 → HTTP-200 + Error envelope `FORBIDDEN`** (KHÔNG raise). Chỉ khi Guest/thiếu token → dispatcher-403 (HTTP-403 ở tầng Frappe `_guard()`, trước khi vào handler).

---

#### C.8 `suspend_competency` — Tạm ngưng (Active → Suspended) — MỚI Vòng 26

| Method | POST |
|---|---|
| Path | `/api/method/assetcore.api.imm06.suspend_competency` — Service `svc.suspend_competency(name, reason)` |
| Body | `{ "name": "COMP-2026-0301", "reason": "KTV nghỉ phép dài hạn / đang điều tra sự cố" }` |
| Permission | **capability `training.submit`** — in-handler gate (parity C.6 revoke) |
| State guard | Nguồn = `Active` (SSoT `_COMPETENCY_VALID_TRANSITIONS`); nguồn ≠ Active → `BAD_STATE` |

**Ngữ nghĩa:** tạm ngưng hiệu lực năng lực **có thể đảo ngược** (KHÁC `revoke` terminal). `Suspended ∉ AUTHORIZED` ⇒ operator MẤT authorization vận hành thiết bị (`validate_user_authorized_for_asset` fail) cho tới khi `restore`. `reason` **BẮT BUỘC** (rỗng/whitespace → `VALIDATION`/422). Side-effect: `workflow_state = Suspended` (`flags.ignore_workflow_status_check`); invalidate auth-cache `(user, device_model)`; IMM Audit Trail action **`SUSPENDED`** → `event_type = competency_suspended` (reason vào `change_summary`).

**Response 200:** `{ "name": "COMP-2026-0301", "workflow_state": "Suspended" }`

**Errors (thứ tự kiểm):**
- `FORBIDDEN` (403) — thiếu `training.submit`; **HTTP-200 Error envelope, `workflow_state` KHÔNG đổi** (gate ở API trước khi vào service).
- `NOT_FOUND` (404) — `name` không tồn tại.
- `BAD_STATE` (409) — nguồn ≠ `Active` (vd đang `Suspended`/`Revoked`/`Pending Assessment`/`Expiring`/`Expired`).
- `VALIDATION` (422) — `reason` rỗng.

---

#### C.9 `restore_competency` — Khôi phục (Suspended → Active) — MỚI Vòng 26

| Method | POST |
|---|---|
| Path | `/api/method/assetcore.api.imm06.restore_competency` — Service `svc.restore_competency(name)` |
| Body | `{ "name": "COMP-2026-0301" }` |
| Permission | **capability `training.submit`** — in-handler gate (parity C.6/C.8) |
| State guard | Nguồn = `Suspended` (SSoT); nguồn ≠ Suspended → `BAD_STATE` |

**Ngữ nghĩa:** khôi phục hiệu lực năng lực về `Active` ⇒ tái cấp authorization vận hành. **KHÔNG cần `reason`**. Side-effect: `workflow_state = Active` (`flags.ignore_workflow_status_check`); invalidate auth-cache; IMM Audit Trail action **`RESTORED`** → `event_type = competency_restored`. ⚠️ Ranh giới (ADR-IMM-06-07): `Suspended` có thể là bản auto-archive (BR-06-11) — khôi phục là quyết định có chủ đích của Training Manager; KHÔNG re-activate hàng loạt.

**Response 200:** `{ "name": "COMP-2026-0301", "workflow_state": "Active" }`

**Errors (thứ tự kiểm):**
- `FORBIDDEN` (403) — thiếu `training.submit`; **HTTP-200 Error envelope, `workflow_state` KHÔNG đổi**.
- `NOT_FOUND` (404) — `name` không tồn tại.
- `BAD_STATE` (409) — nguồn ≠ `Suspended`.

> **Note 2 loại 403 (spec-contract, LL-BE-42..49):** C.8/C.9 — thiếu quyền = **in-handler cap-403 → HTTP-200 + Error envelope `FORBIDDEN`** (KHÔNG raise → HTTP-4xx). Guest/thiếu token → dispatcher-403 (HTTP-403 ở `_guard()` trước handler). Cả 2 endpoint yêu cầu `event_type` Select của **IMM Audit Trail** đã thêm `competency_suspended`/`competency_restored` (04 §VI.2b) — nếu chưa, audit rớt câm.

---

### Group D — Dashboard & Authorization

#### D.1 `get_dashboard_stats`

| Method | GET |
|---|---|
| Permission | `_DASHBOARD_ROLES` |

**Response 200:**

```json
{
  "success": true,
  "data": {
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
      {
        "name": "COMP-2026-0099",
        "user": "ktv3@hosp.vn",
        "device_model": "MDL-CT-SIEMENS-S5",
        "expiry_date": "2026-05-15",
        "days_until_expiry": 7
      }
    ],
    "compliance_by_dept": [
      {
        "dept": "ICU",
        "total_users": 30,
        "competent_users": 28,
        "pct": 93.3,
        "gap_class3": 0
      }
    ],
    "recent_sessions": [
      {
        "name": "TRN-2026-0042",
        "training_program": "TRN-MON-INIT-01",
        "session_date": "2026-05-20",
        "participant_count": 15,
        "pass_count": 13
      }
    ]
  }
}
```

**Errors:** `FORBIDDEN`

> **Ground-truth envelope (BR-06-14 — predicate LIVE, 2026-06-04):** Shape JSON ở trên là **bản mở rộng theo roadmap** (kpis/expiry_timeline/compliance_by_dept). **Implementation hiện tại** của `services.imm06.get_dashboard_stats()` trả về nhóm `competencies` theo trạng thái — FE/BE phải bind theo shape THẬT này:
>
> ```json
> {
>   "success": true,
>   "data": {
>     "sessions":     { "total": 0, "planned": 0, "confirmed": 0, "in_progress": 0, "completed": 0, "cancelled": 0 },
>     "competencies": { "total": 0, "pending": 0, "active": 0, "expiring": 0, "expired": 0, "revoked": 0 },
>     "programs":     { "total": 0, "active": 0 }
>   }
> }
> ```
>
> **Hợp đồng KPI (INVARIANT, đo được):**
> - `data.competencies.expiring` = `COUNT` theo `_expiring_competency_filter()` (LIVE date-derived: `workflow_state ∈ {Active,Expiring} ∧ expiry_date ∈ [today, today+60]`) — **KHÔNG** còn `frappe.db.count(workflow_state==Expiring)` thuần.
> - `data.competencies.expired` = `COUNT` theo `_expired_competency_filter()` (LIVE: `workflow_state ∈ {Active,Expiring,Expired} ∧ expiry_date < today`, loại Revoked/Suspended).
> - **`data.competencies.expiring == get_expiring_competencies(60).count`** với MỌI tập dữ liệu (card == drill). Click tile "Sắp hết hạn" → drill `get_expiring_competencies` PHẢI khớp số.
> - `data.competencies.active` giữ nguyên `COUNT(workflow_state==Active)` (tổng cờ — không đổi).
>
> Chi tiết predicate + 2 helper SoT: `04_Backend_Design.md §V.2`. Khi nhóm `kpis.expiring_90d`/`expired_not_renewed` (roadmap) được ship, giá trị cũng PHẢI phái sinh qua 2 helper SoT (không count cờ thuần).

---

#### D.2 `check_user_authorization`

| Method | GET |
|---|---|
| Permission | All authenticated — **internal hook** cho IMM-08/09/11/12 |

**Query params:** `?user=ktv1@hosp.vn&device_model=MDL-MON-PHILIPS-X3`

**Behavior:** Cached 5 min TTL.

**Response 200 (authorized):**

```json
{
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
```

**Response 200 (not authorized — Expired):**

```json
{
  "success": true,
  "data": {
    "authorized": false,
    "competency": "COMP-2026-0099",
    "status": "Expired",
    "reason": "Năng lực đã hết hạn từ 2026-04-30 — yêu cầu tái chứng nhận"
  }
}
```

**Response 200 (not authorized — None):**

```json
{
  "success": true,
  "data": {
    "authorized": false,
    "competency": null,
    "status": "None",
    "reason": "Người dùng chưa có Active competency cho thiết bị này"
  }
}
```

**Errors:** `NOT_FOUND` (device_model không tồn tại)

> **Lưu ý:** Cross-module call từ IMM-08/09/11/12 dùng Python import trực tiếp (không qua HTTP):
> ```python
> from assetcore.services.imm06 import validate_user_authorization
> result = validate_user_authorization(user, asset.device_model)
> ```

---

#### D.3 `signoff_competency`

| Method | POST |
|---|---|
| Roles | `_SIGNOFF_ROLES` |

**Request body:** `{"name": "COMP-2026-0301"}`

**Behavior:**
1. Validate role IN `_SIGNOFF_ROLES` AND scope (Department Manager chỉ sign-off người trong khoa).
2. Validate VR-07 + `workflow_state = "Pending Assessment"`.
3. Set `supervisor_signoff = session.user`, `signoff_date = today`.
4. Compute `expiry_date`, `recertification_due_date`.
5. `workflow_state = "Active"`.
6. `archive_old_competency(user, device_model, exclude=name)` (BR-06-11).
7. `invalidate_authorization_cache`.
8. Gửi email cho user.

**Response 200:**

```json
{
  "success": true,
  "data": {
    "name": "COMP-2026-0301",
    "new_state": "Active",
    "expiry_date": "2028-05-20",
    "recertification_due_date": "2028-03-21"
  }
}
```

**Errors:** `FORBIDDEN`, `NOT_FOUND`, `VALIDATION` (VR-07), `BUSINESS_RULE` (sai state)

---

## §IV Error Catalog

| Code | Module prefix | Business Rule | Mô tả |
|---|---|---|---|
| `TRN-001` | Program | VR-02 | `passing_score_pct` ngoài khoảng 1-100 |
| `TRN-002` | Program | VR-03 | `validity_period_months` ngoài khoảng 1-60 |
| `TRN-003` | Program | VR-11 | `target_device_model` không tồn tại hoặc inactive |
| `TRN-004` | Session | VR-04 | Giảng viên không đủ điều kiện theo Program |
| `TRN-005` | Session | VR-05 | Session chưa có participant khi Confirm |
| `TRN-006` | Session | VR-06 | Thiếu điểm lý thuyết hoặc thực hành khi Complete |
| `TRN-007` | Session | VR-10 | `session_date` trong quá khứ (non-backdated) |
| `TRN-008` | Session | BR-06-12 | Không thể Hủy sau trạng thái Verified/Closed |
| `COMP-001` | Competency | VR-01 | `expiry_date` không sau `achieved_date` |
| `COMP-002` | Competency | VR-07 | Thiếu supervisor sign-off khi chuyển Active |
| `COMP-003` | Competency | VR-08 | Thiếu CAPA reference khi revoke do sự cố |
| `COMP-004` | Competency | VR-12 | `competency_level` không tương thích `training_type` |
| `COMP-005` | Competency | BR-06-09 | Không thể xóa cứng competency |
| `COMP-006` | Competency | BR-06-11 | Lỗi archive old competency |
| `NOT_FOUND` | All | — | Record không tồn tại |
| `FORBIDDEN` | All | — | Role không match |
| `INVALID_PARAMS` | All | — | Tham số không hợp lệ |
| `INTERNAL` | All | — | Lỗi server |

---

## §V TypeScript Types

```typescript
// frontend/src/types/imm06.ts (đã có)

export type TrainingType = 'Initial' | 'Refresher' | 'Advanced' | 'Certification'
export type SessionType = 'Onsite' | 'Online' | 'Hybrid'
export type SessionState =
  | 'Planned' | 'Confirmed' | 'In Progress'
  | 'Completed' | 'Verified' | 'Closed' | 'Cancelled'
export type CompetencyState =
  | 'Pending Assessment' | 'Active' | 'Expiring'
  | 'Expired' | 'Suspended' | 'Revoked'
export type CompetencyLevel = 'Trainee' | 'Operator' | 'Senior Operator' | 'Trainer'

export interface TrainingProgram {
  name: string
  program_name: string
  training_type: TrainingType
  target_device_model: string | null
  target_device_category: string | null
  duration_hours: number
  validity_period_months: number
  passing_score_pct: number
  assessment_method: 'Theory' | 'Practical' | 'Both'
  instructor_qualification_required: string | null
  is_mandatory_for_operation: boolean
  is_active: boolean
  qms_doc_ref: string | null
}

export interface TrainingSession {
  name: string
  training_program: string
  session_date: string
  session_type: SessionType
  location: string | null
  instructor: string | null
  instructor_external_name: string | null
  duration_planned_hours: number
  duration_actual_hours: number | null
  workflow_state: SessionState
  participants: TrainingParticipant[]
}

export interface TrainingParticipant {
  user: string
  department: string | null
  role_at_session: string | null
  attendance_pct: number | null
  theory_score: number | null
  practical_score: number | null
  overall_result: 'Pass' | 'Fail' | 'Conditional' | null
  competency_record: string | null
  remarks: string | null
}

export interface UserCompetency {
  name: string
  user: string
  device_model: string
  training_program: string
  training_session: string | null
  competency_level: CompetencyLevel
  achieved_date: string
  validity_months: number
  expiry_date: string | null
  recertification_due_date: string | null
  workflow_state: CompetencyState
  days_until_expiry: number | null
  supervisor_signoff: string | null
  signoff_date: string | null
  certificate_file: string | null
  department_at_assessment: string | null
  theory_score: number | null
  practical_score: number | null
}

export interface DashboardStats {
  kpis: {
    total_active_competencies: number
    expiring_90d: number
    expired_not_renewed: number
    users_competent_pct: number
    training_completion_rate_90d: number
    average_pass_rate_90d: number
    total_gap_assets_class3: number
  }
  expiry_timeline: {
    name: string
    user: string
    device_model: string
    expiry_date: string
    days_until_expiry: number
  }[]
  compliance_by_dept: {
    dept: string
    total_users: number
    competent_users: number
    pct: number
    gap_class3: number
  }[]
  recent_sessions: {
    name: string
    training_program: string
    session_date: string
    participant_count: number
    pass_count: number
  }[]
}

export interface AuthorizationResult {
  authorized: boolean
  competency: string | null
  competency_level: CompetencyLevel | null
  status: CompetencyState | 'None'
  expiry_date: string | null
  days_until_expiry: number | null
  reason: string | null
}
```
