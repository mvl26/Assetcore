# IMM-05 — API Interface Specification

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-05 — Asset Document Repository |
| Phiên bản | 2.0.0 |
| Ngày cập nhật | 2026-04-18 |
| Trạng thái | LIVE |
| Base URL | `/api/method/assetcore.api.imm05` |
| Tác giả | AssetCore Team |

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
| 403 | User không có Role hợp lệ; hoặc gọi `_can_see_internal()` fail; hoặc `_APPROVE_ROLES` / `_EXEMPT_ROLES` không match |

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

14 whitelist endpoints, group theo nghiệp vụ:

### 3.1 Document CRUD

#### 3.1.1 `list_documents` — Liệt kê có filter + pagination

| Thuộc tính | Giá trị |
|---|---|
| Method | GET |
| Path | `assetcore.api.imm05.list_documents` |
| Permission | All authenticated; auto áp `_apply_visibility_filter` |

**Params (query string):**

| Param | Kiểu | Default | Mô tả |
|---|---|---|---|
| `filters` | JSON string | `"{}"` | Frappe filter dict |
| `page` | int | 1 | Trang (1-based) |
| `page_size` | int | 20 | Max 100 |

**Response data:**

```json
{
  "items": [{
    "name": "DOC-AC-ASSET-2026-0001-2026-00001",
    "asset_ref": "AC-ASSET-2026-0001",
    "doc_category": "Legal",
    "doc_type_detail": "Giấy phép nhập khẩu",
    "doc_number": "NK-2026-0042",
    "version": "1.0",
    "workflow_state": "Active",
    "expiry_date": "2027-06-30",
    "days_until_expiry": 442,
    "visibility": "Public",
    "is_exempt": 0,
    "modified": "2026-04-18 10:00:00"
  }],
  "pagination": {"page": 1, "page_size": 20, "total": 137, "total_pages": 7}
}
```

**Errors:**

| code | Khi |
|---|---|
| `INVALID_FILTERS` | `filters` không phải JSON hợp lệ |

#### 3.1.2 `get_document` — Chi tiết 1 doc

| Method | GET |
|---|---|
| Path | `assetcore.api.imm05.get_document` |

**Params:** `name` (string)

**Errors:**

| code | Mô tả |
|---|---|
| `NOT_FOUND` | DocType không tồn tại |
| `FORBIDDEN` | `visibility=Internal_Only` và user không thuộc internal roles |

#### 3.1.3 `create_document` — Tạo Draft

| Method | POST |
|---|---|
| Path | `assetcore.api.imm05.create_document` |

**Body:** `doc_data` (JSON string) — gồm các field của `Asset Document`. Auto-default `workflow_state="Draft"`, `version="1.0"`.

**Response:** `{name, workflow_state}`

**Errors:** `INVALID_DATA`, `VALIDATION_ERROR`, `CREATE_ERROR`

#### 3.1.4 `update_document` — Sửa metadata

| Method | POST |
|---|---|
| Path | `assetcore.api.imm05.update_document` |

**Body:** `name`, `doc_data` (JSON)

**Constraint:** `workflow_state IN ("Draft", "Rejected")` — ngược lại trả `INVALID_STATE`.

### 3.2 Workflow Actions

#### 3.2.1 `approve_document`

| Method | POST |
|---|---|
| Path | `assetcore.api.imm05.approve_document` |
| Roles | `_APPROVE_ROLES` = {Biomed Engineer, Tổ HC-QLCL, CMMS Admin} |

**Body:** `name`

**Hành vi:**

1. Validate state = `Pending_Review` (không thì `INVALID_STATE`)
2. Validate user thuộc `_APPROVE_ROLES` (không thì `FORBIDDEN`)
3. Query Active docs cùng (`asset_ref` + `doc_type_detail`) ≠ `name` → set `workflow_state="Archived"`
4. Set `workflow_state="Active"`, `approved_by`, `approval_date=today`
5. Save với `ignore_permissions=True`

**Response:** `{name, new_state: "Active", approved_by}`

#### 3.2.2 `reject_document`

| Method | POST |
|---|---|
| Path | `assetcore.api.imm05.reject_document` |

**Body:** `name`, `rejection_reason` (bắt buộc — VR-06)

**Hành vi:** Set `workflow_state="Rejected"`, lưu `rejection_reason`.

**Errors:** `VALIDATION_ERROR` (thiếu reason), `NOT_FOUND`, `INVALID_STATE`.

### 3.3 Asset-centric Views

#### 3.3.1 `get_asset_documents` — Toàn bộ docs theo Asset

| Method | GET |
|---|---|
| Path | `assetcore.api.imm05.get_asset_documents` |

**Params:** `asset` (Asset name)

**Response data:**

```json
{
  "asset": "AC-ASSET-2026-0001",
  "completeness_pct": 71.4,
  "document_status": "Compliant",
  "documents": {
    "Legal": [{...}, {...}],
    "Technical": [{...}],
    "Certification": [{...}]
  },
  "missing_required": ["Warranty Card"]
}
```

Auto áp `_apply_visibility_filter`. `completeness_pct` và `document_status` đọc từ `Asset.custom_doc_completeness_pct`, `Asset.custom_document_status`.

### 3.4 Dashboard / Reports

#### 3.4.1 `get_dashboard_stats`

| Method | GET |
|---|---|
| Path | `assetcore.api.imm05.get_dashboard_stats` |

**Response data:**

```json
{
  "kpis": {
    "total_active": 412,
    "expiring_90d": 28,
    "expired_not_renewed": 5,
    "assets_missing_docs": 17
  },
  "expiry_timeline": [{"name", "asset_ref", "doc_type_detail", "expiry_date", "days_until_expiry"}],
  "compliance_by_dept": [{"dept", "total_assets", "compliant", "pct"}]
}
```

#### 3.4.2 `get_expiring_documents`

| Method | GET |
|---|---|
| Path | `assetcore.api.imm05.get_expiring_documents` |

**Params:** `days` (int, default 90, max 365)

**Response:** `{days, count, items: [...]}` — fields: name, asset_ref, doc_category, doc_type_detail, expiry_date, days_until_expiry, issuing_authority

#### 3.4.3 `get_compliance_by_dept`

| Method | GET |
|---|---|
| Path | `assetcore.api.imm05.get_compliance_by_dept` |

**Response:** Array `{dept, total_assets, compliant, incomplete, non_compliant, expiring_soon, pct}`. Trả `[]` nếu query SQL fail (graceful degradation).

#### 3.4.4 `get_document_history`

| Method | GET |
|---|---|
| Path | `assetcore.api.imm05.get_document_history` |

**Params:** `name`

Wrap Frappe `Version` DocType. Response item:

```json
{
  "timestamp": "2026-04-18 10:00:00",
  "user": "biomed@hosp.vn",
  "action": "Workflow Transition",
  "from_state": "Pending_Review",
  "to_state": "Active",
  "changes": [{"field": "approved_by", "old": null, "new": "biomed@hosp.vn"}]
}
```

### 3.5 Document Request

#### 3.5.1 `create_document_request`

| Method | POST |
|---|---|
| Path | `assetcore.api.imm05.create_document_request` |

**Params:** `asset_ref`, `doc_type_required`, `doc_category` (default "Legal"), `assigned_to` (default session.user), `due_date` (default today+30), `priority` (default "Medium"), `request_note`, `source_type` (default "Manual")

**Response:** `{name, status: "Open"}`

#### 3.5.2 `get_document_requests`

| Method | GET |
|---|---|
| Path | `assetcore.api.imm05.get_document_requests` |

**Params:** `asset_ref` (optional), `status` (optional)

**Response:** `{count, items: [...]}` — fields: name, asset_ref, doc_type_required, doc_category, assigned_to, due_date, status, priority, escalation_sent, source_type, fulfilled_by

### 3.6 Exempt (NĐ98)

#### 3.6.1 `mark_exempt`

| Method | POST |
|---|---|
| Path | `assetcore.api.imm05.mark_exempt` |
| Roles | `_EXEMPT_ROLES` = {Tổ HC-QLCL, CMMS Admin, Workshop Head} |

**Params (all required):** `asset_ref`, `doc_type_detail`, `exempt_reason`, `exempt_proof` (file path)

**Hành vi:**

1. Validate user thuộc `_EXEMPT_ROLES` (`FORBIDDEN`)
2. Validate Asset tồn tại (`NOT_FOUND`)
3. Tạo Asset Document với `is_exempt=1`, `workflow_state="Active"`, `doc_number="EXEMPT-{asset_ref}"`, `source_module="IMM-05-Exempt"`, `approved_by=session.user`
4. Set `Asset.custom_document_status = "Compliant (Exempt)"`

**Response:** `{document_name, is_exempt: true, new_asset_document_status: "Compliant (Exempt)"}`

**Errors:** `FORBIDDEN`, `NOT_FOUND`, `VALIDATION_ERROR` (thiếu reason/proof, hoặc VR-11 doc_type không hợp lệ), `EXEMPT_ERROR`

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
| `INVALID_FILTERS` | list_documents | filters JSON parse fail |
| `INVALID_DATA` | create/update_document | doc_data JSON parse fail |
| `NOT_FOUND` | get/update/approve/reject, get_asset_documents, get_document_history, mark_exempt, create_document_request | DocType không tồn tại |
| `FORBIDDEN` | get_document, approve_document, mark_exempt | Không có quyền (visibility/role) |
| `INVALID_STATE` | update/approve/reject_document | workflow_state không phù hợp action |
| `VALIDATION_ERROR` | create/reject_document, mark_exempt | VR-XX failure |
| `CREATE_ERROR` | create_document, create_document_request | Insert exception |
| `EXEMPT_ERROR` | mark_exempt | Insert exception |

---

## 5. Webhook / Realtime Events

IMM-05 hiện **chưa publish realtime event** qua `frappe.publish_realtime`. Các sự kiện sau được track qua Frappe Version DocType (truy cập qua `get_document_history`):

| Event | Trigger | Audit qua |
|---|---|---|
| document_created | `create_document` | Frappe Version |
| document_approved | `approve_document` | Frappe Version (workflow_state change) |
| document_rejected | `reject_document` | Frappe Version |
| document_archived | `archive_old_versions` (auto) | Frappe Version + `superseded_by` |
| document_expired | `check_document_expiry` scheduler | Expiry Alert Log |
| document_request_created | `create_document_request` | Frappe Version |
| document_request_overdue | `check_overdue_document_requests` scheduler | `escalation_sent=1` |

**Roadmap:** Realtime push qua Socket.IO cho dashboard live update — backlog.

---

## 6. Implementation Notes

| # | Note |
|---|---|
| 1 | `_apply_visibility_filter` áp dụng cho `list_documents` và `get_asset_documents`. Endpoint `get_document` check riêng + trả `FORBIDDEN`. |
| 2 | `approve_document` dùng `ignore_permissions=True` khi save → bypass Frappe perm để workflow chạy được; chính sách kiểm soát qua `_APPROVE_ROLES`. |
| 3 | `archive_old_versions` chạy cả ở 2 nơi: (a) controller `on_update` khi workflow_state chuyển Active, (b) trong `approve_document`. Idempotent. |
| 4 | `update_document` chỉ cho phép sửa khi `workflow_state IN ("Draft", "Rejected")`. Sửa sau Active phải qua "upload version mới". |
| 5 | `get_dashboard_stats` SQL query có `try/except` graceful — nếu custom field chưa sync → trả `dept_stats=[]`. |
| 6 | Naming series Asset Document: `DOC-{asset_ref}-{YYYY}-{#####}` (autoname Expression). Document Request: `DOCREQ-{YYYY}-{MM}-{#####}`. |
| 7 | File upload qua Frappe File API thông thường (`/api/method/upload_file`). IMM-05 chỉ nhận đường dẫn vào field `file_attachment`. |
| 8 | Workflow JSON dùng "Pending Review" có space, controller/API code dùng "Pending_Review" — DocType field workflow_state ghi nhận giá trị workflow đang cập nhật (LIVE). |
| 9 | Service layer `services/imm05.py` chưa có; logic nằm trong controller `asset_document.py` + `tasks.py`. Tech-debt cần refactor. |
| 10 | GW-2 compliance gate được implement trong IMM-04 `asset_commissioning.validate()` — query Asset Document `workflow_state="Active"` cho doc_type_detail "Chứng nhận đăng ký lưu hành" hoặc `is_exempt=1`. |
