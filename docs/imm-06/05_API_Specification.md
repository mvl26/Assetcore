# 05 — API Specification — IMM-06 Đào tạo & Quản lý năng lực

| Mục | Giá trị |
|---|---|
| Module | IMM-06 — User Training & Competency Management |
| Phiên bản tài liệu | 0.1.0 |
| Ngày cập nhật | 2026-05-08 |
| Base path | `assetcore.api.imm06` |
| URL pattern | `/api/method/assetcore.api.imm06.<function>` |
| Liên kết | [02 Analysis](./02_Analysis_Design.md) · [04 Backend](./04_Backend_Design.md) · [06 Frontend](./06_Frontend_Design.md) |

> ⚠️ Pending implementation — Wave 2. Endpoints chưa được whitelist. Tài liệu này là thiết kế spec.

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
_REVOKE_ROLES  = {"IMM Training Officer", "IMM System Admin"}
_DASHBOARD_ROLES = {
    "IMM Workshop Lead", "IMM Training Officer",
    "IMM System Admin", "VP Block2"
}
```

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
| Permission | All authenticated |

**Query params:** `?name=TRN-2026-00042`

**Response 200:** Full session object + `participants` array (child rows).

**Errors:** `NOT_FOUND`

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

#### C.2 `get_user_competencies` (self-service)

| Method | GET |
|---|---|
| Permission | All authenticated; nếu `user` param != session.user → cần `_SIGNOFF_ROLES` hoặc `IMM Workshop Lead` / `IMM Training Officer` |

**Query params:** `?user=ktv1@hosp.vn` (default = session.user)

**Response 200:**

```json
{
  "success": true,
  "data": {
    "user": "ktv1@hosp.vn",
    "user_full_name": "Nguyễn Văn A",
    "competencies": [
      {
        "name": "COMP-2026-0301",
        "device_model": "MDL-MON-PHILIPS-X3",
        "device_model_name": "Monitor Philips X3",
        "competency_level": "Operator",
        "achieved_date": "2026-05-20",
        "expiry_date": "2028-05-20",
        "days_until_expiry": 745,
        "workflow_state": "Active",
        "recertification_due_date": "2028-03-21",
        "certificate_file": "AD-2026-0001"
      }
    ],
    "summary": {
      "active": 3,
      "expiring": 1,
      "expired": 0,
      "revoked": 0
    }
  }
}
```

**Errors:** `FORBIDDEN`

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

**Query params:** `?days=90` (default 90, max 365)

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

#### C.6 `revoke_competency`

| Method | POST |
|---|---|
| Roles | `_REVOKE_ROLES` = {IMM Training Officer, IMM System Admin} |

**Request body:**

```json
{
  "name": "COMP-2026-0301",
  "revoke_reason": "Vi phạm quy trình vận hành — liên quan tới sự cố INC-2026-0033 (tối thiểu 30 ký tự)",
  "revoke_capa_ref": "CAPA-2026-0011"
}
```

**Behavior:**
1. Validate `_REVOKE_ROLES` — FORBIDDEN nếu fail.
2. Validate VR-08: nếu `revoke_reason` chứa keyword in `["incident","sự cố","tai nạn","sai phạm"]` → `revoke_capa_ref` reqd.
3. Set `workflow_state="Revoked"`, `revoked_by=session.user`, `revoked_date=now()`.
4. `invalidate_authorization_cache(user, device_model)`.
5. Log IMM Audit Trail `action="REVOKE"`.
6. Quét WO open assigned cho user → flag + email IMM Workshop Lead.

**Response 200:**

```json
{
  "success": true,
  "data": {
    "name": "COMP-2026-0301",
    "new_state": "Revoked",
    "flagged_work_orders": ["WO-PM-2026-0042", "WO-CM-2026-0011"]
  }
}
```

**Errors:** `FORBIDDEN`, `NOT_FOUND`, `BUSINESS_RULE` (đã Revoked), `VALIDATION` (VR-08)

---

#### C.7 `recertify_competency`

| Method | POST |
|---|---|
| Roles | `IMM Training Officer`, `IMM System Admin` |

**Request body:** `{"name": "COMP-2026-0301", "auto_create_session": true}` hoặc `{"name": "COMP-2026-0301", "new_session_name": "TRN-2026-0099"}`

**Behavior:** Gọi `services.imm06.trigger_recertification(name)` → tạo Refresher Session Planned hoặc liên kết session đã có.

**Response 200:**

```json
{
  "success": true,
  "data": {
    "name": "COMP-2026-0301",
    "new_session": "TRN-2026-0099",
    "action": "created"
  }
}
```

**Errors:** `FORBIDDEN`, `NOT_FOUND`

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
// frontend/src/types/imm06.ts
// ⚠️ Pending implementation

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
