# IMM-05 — API Specification

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-05 — Asset Document Repository |
| Template | 05_API_Specification v4.1+ |
| Base URL | `/api/method/assetcore.api.imm05` |
| Ngày tạo | 2026-05-08 |
| Trạng thái | Live (Wave 1) |

---

## §0 — API Catalog

| # | Endpoint | Method | Nhóm | Mô tả |
|---|---|---|---|---|
| 1 | `list_documents` | GET | CRUD | Liệt kê tài liệu có filter + pagination |
| 2 | `get_document` | GET | CRUD | Chi tiết 1 tài liệu |
| 3 | `create_document` | POST | CRUD | Tạo Draft mới |
| 4 | `update_document` | POST | CRUD | Sửa metadata (Draft/Rejected) |
| 5 | `submit_for_review` | POST | Workflow | Draft/Rejected → Pending Review |
| 6 | `approve_document` | POST | Workflow | Phê duyệt → Active |
| 7 | `reject_document` | POST | Workflow | Từ chối + lý do |
| 8 | `archive_document` | POST | Workflow | Lưu trữ tài liệu (Active → Archived) |
| 9 | `get_asset_documents` | GET | Asset-centric | Tài liệu theo Asset |
| 10 | `get_dashboard_stats` | GET | Dashboard | KPI + expiry timeline + compliance |
| 11 | `get_expiring_documents` | GET | Dashboard | Tài liệu sắp hết hạn |
| 12 | `get_compliance_by_dept` | GET | Dashboard | Compliance theo khoa |
| 13 | `get_document_history` | GET | Audit | Lịch sử thay đổi (Frappe Version) |
| 14 | `create_document_request` | POST | Request | Tạo yêu cầu bổ sung tài liệu |
| 15 | `get_document_requests` | GET | Request | Liệt kê Document Request |
| 16 | `mark_exempt` | POST | Exempt | Đánh dấu Miễn đăng ký NĐ98 |

---

## §1 — Conventions

### §1.1 Authentication

```http
# API Token (server-to-server)
Authorization: token <api_key>:<api_secret>

# Session cookie (browser)
Cookie: sid=<session_id>
```

| HTTP code | Khi nào trả |
|---|---|
| 401 | Thiếu / sai credential |
| 403 | User không có Role hợp lệ; hoặc `_can_see_internal()` fail |

### §1.2 Response envelope — SUCCESS

> **AssetCore envelope** — KHÔNG dùng Frappe outer `{"message": ...}` wrapper trong tài liệu này.

```jsonc
// HTTP 200 — success
{
  "success": true,
  "data": {
    // payload cụ thể theo endpoint
  }
}
```

### §1.3 Response envelope — ERROR

```jsonc
// HTTP 200 — application error (kiểm tra success field)
{
  "success": false,
  "error": "Mô tả lỗi tiếng Việt",
  "code": "ERROR_CODE",
  "fields": {
    // optional: field-level errors
    "expiry_date": "Ngày hết hạn phải sau ngày cấp."
  }
}
```

### §1.4 Error code catalog

| Code | Endpoint áp dụng | Mô tả |
|---|---|---|
| `INVALID_FILTERS` | `list_documents` | `filters` JSON parse fail |
| `INVALID_DATA` | `create_document`, `update_document` | `doc_data` JSON parse fail |
| `NOT_FOUND` | get/update/approve/reject, `get_asset_documents`, `get_document_history`, `mark_exempt`, `create_document_request` | DocType không tồn tại |
| `FORBIDDEN` | `get_document`, `approve_document`, `mark_exempt` | Không có quyền (visibility/role) |
| `INVALID_STATE` | `update_document`, `approve_document`, `reject_document` | workflow_state không phù hợp action |
| `VALIDATION_ERROR` | `create_document`, `reject_document`, `mark_exempt` | VR-XX failure |
| `CREATE_ERROR` | `create_document`, `create_document_request` | Insert exception |
| `EXEMPT_ERROR` | `mark_exempt` | Insert exception khi tạo doc exempt |
| `INTERNAL_ERROR` | Tất cả | Unhandled exception |

### §1.5 Visibility filter

Endpoints `list_documents` và `get_asset_documents` tự động áp visibility filter. User không thuộc `_INTERNAL_VIEW_ROLES` chỉ thấy `visibility IN ("Public", "", null)`.

Từ `services/imm05.py`:
```python
_INTERNAL_VIEW_ROLES = {
    Roles.SYS_ADMIN, Roles.QA, Roles.DEPT_HEAD, Roles.OPS_MANAGER,
    Roles.WORKSHOP, Roles.TECHNICIAN, Roles.DOC_OFFICER,
    "IMM Technician", "IMM QA Officer", "IMM Biomed Technician",
    "IMM Workshop Lead", "IMM System Admin", "System Manager",
}
```

`_APPROVE_ROLES` (cho approve/reject): `{Roles.SYS_ADMIN, Roles.QA, Roles.DEPT_HEAD, Roles.OPS_MANAGER, "IMM Biomed Technician", "IMM QA Officer", "IMM System Admin"}`

`_EXEMPT_ROLES` (cho mark_exempt): `{Roles.SYS_ADMIN, Roles.QA, Roles.OPS_MANAGER, "IMM QA Officer", "IMM System Admin", "IMM Workshop Lead"}`

### §1.6 TypeScript types (FE reference)

> **Lưu ý:** `frontend/src/types/imm05.ts` chỉ re-export từ `@/api/imm05`. Các types thực tế được định nghĩa trong `frontend/src/api/imm05.ts`.

```typescript
// Workflow state values — ground truth từ services/imm05.py class DocState
// Dùng SPACE (đồng bộ với workflow fixture + service constants)
export type DocumentWorkflowState =
  | "Draft"
  | "Pending Review"
  | "Active"
  | "Rejected"
  | "Archived"
  | "Expired";

export type DocumentVisibility = "Public" | "Internal_Only";

export type DocumentCategory = "Legal" | "Technical" | "Certification" | "Training" | "QA";

export interface AssetDocument {
  name: string;
  asset_ref: string;
  model_ref?: string;
  is_model_level: boolean;
  clinical_dept?: string;
  source_commissioning?: string;
  source_module?: string;
  doc_category: DocumentCategory;
  doc_type_detail: string;
  doc_number: string;
  version: string;
  issued_date: string;
  expiry_date?: string;
  issuing_authority?: string;
  days_until_expiry?: number;
  is_expired: boolean;
  file_attachment: string;
  file_name_display?: string;
  approved_by?: string;
  approval_date?: string;
  rejection_reason?: string;
  superseded_by?: string;
  archived_by_version?: string;
  archive_date?: string;
  change_summary?: string;
  visibility: DocumentVisibility;
  is_exempt: boolean;
  exempt_reason?: string;
  exempt_proof?: string;
  notes?: string;
  workflow_state: DocumentWorkflowState;
  modified: string;
}

export interface DocumentRequest {
  name: string;
  asset_ref: string;
  doc_type_required: string;
  doc_category: DocumentCategory;
  status: "Open" | "In_Progress" | "Overdue" | "Fulfilled" | "Cancelled";
  priority: "Low" | "Medium" | "High" | "Critical";
  assigned_to: string;
  due_date: string;
  source_type: "Manual" | "Dashboard" | "GW2_Block" | "Scheduler";
  escalation_sent: boolean;
  request_note?: string;
  fulfilled_by?: string;
}

export interface Pagination {
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}
```

---

## §2 — Endpoint Specifications

### §2.1 `list_documents` — Liệt kê tài liệu

| Thuộc tính | Giá trị |
|---|---|
| Method | GET |
| Path | `assetcore.api.imm05.list_documents` |
| Permission | All authenticated (server auto-filter visibility) |

**Query params:**

| Param | Kiểu | Default | Mô tả |
|---|---|---|---|
| `filters` | JSON string | `"{}"` | Frappe filter dict |
| `page` | int | 1 | Trang (1-based) |
| `page_size` | int | 20 | Tối đa 100 |

**Response data:**

```jsonc
{
  "success": true,
  "data": {
    "items": [
      {
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
        "is_exempt": false,
        "modified": "2026-04-18 10:00:00"
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total": 137,
      "total_pages": 7
    }
  }
}
```

**Errors:** `INVALID_FILTERS` (filters JSON parse fail).

---

### §2.2 `get_document` — Chi tiết tài liệu

| Thuộc tính | Giá trị |
|---|---|
| Method | GET |
| Path | `assetcore.api.imm05.get_document` |

**Params:** `name` (string)

**Response data:** Full `AssetDocument` object.

**Errors:**

| Code | Khi |
|---|---|
| `NOT_FOUND` | DocType không tồn tại |
| `FORBIDDEN` | `visibility=Internal_Only` và user không thuộc internal roles |

---

### §2.3 `create_document` — Tạo Draft

| Thuộc tính | Giá trị |
|---|---|
| Method | POST |
| Path | `assetcore.api.imm05.create_document` |
| Permission | HTM Technician, Biomed Engineer, Tổ HC-QLCL, Workshop Head, CMMS Admin |

**Request body:**

```jsonc
{
  "doc_data": "{\"asset_ref\": \"AC-ASSET-2026-0001\", \"doc_category\": \"Legal\", \"doc_type_detail\": \"Giấy phép nhập khẩu\", \"doc_number\": \"NK-2026-0042\", \"issued_date\": \"2026-01-15\", \"expiry_date\": \"2027-06-30\", \"issuing_authority\": \"Bộ Y tế\", \"file_attachment\": \"/files/nk-2026-0042.pdf\", \"visibility\": \"Public\"}"
}
```

Auto-default: `workflow_state = "Draft"`, `version = "1.0"`.

**Response data:**

```jsonc
{
  "success": true,
  "data": {
    "name": "DOC-AC-ASSET-2026-0001-2026-00001",
    "workflow_state": "Draft"
  }
}
```

**Errors:** `INVALID_DATA`, `VALIDATION_ERROR` (VR-XX fail), `CREATE_ERROR`.

---

### §2.4 `update_document` — Sửa metadata

| Thuộc tính | Giá trị |
|---|---|
| Method | POST |
| Path | `assetcore.api.imm05.update_document` |

**Request body:** `name`, `doc_data` (JSON string)

**Constraint:** `workflow_state IN ("Draft", "Rejected")` — ngược lại trả `INVALID_STATE` (BAD_STATE trong service code).

**Request body:** `name` (string), `doc_data` (JSON string của patch dict)

---

### §2.4b `submit_for_review` — Gửi duyệt

| Thuộc tính | Giá trị |
|---|---|
| Method | POST |
| Path | `assetcore.api.imm05.submit_for_review` |
| Service | `services/imm05.py::submit_for_review` |

**Request body:** `name` (string).

**Constraint:** `workflow_state IN ("Draft", "Rejected")` — ngược lại trả `INVALID_STATE`. Set `workflow_state = "Pending Review"`.

**Response data:**

```jsonc
{ "success": true, "data": { "name": "...", "new_state": "Pending Review" } }
```

**Errors:** `NOT_FOUND`, `INVALID_STATE`, `INTERNAL_ERROR`.

---

### §2.5 `approve_document` — Phê duyệt

| Thuộc tính | Giá trị |
|---|---|
| Method | POST |
| Path | `assetcore.api.imm05.approve_document` |
| Roles | `_APPROVE_ROLES` = {Biomed Engineer, Tổ HC-QLCL, CMMS Admin} |

**Request body:**

```jsonc
{ "name": "DOC-AC-ASSET-2026-0001-2026-00001" }
```

**Hành vi:**
1. Validate user IN `_APPROVE_ROLES` → else `FORBIDDEN`
2. Validate `workflow_state = "Pending Review"` → else `INVALID_STATE`
3. Query Active docs cùng `(asset_ref, doc_type_detail)` ≠ name → set `workflow_state = "Archived"`
4. Set `workflow_state = "Active"`, `approved_by = session.user`, `approval_date = today`
5. Save với `flags.ignore_links = True`

**Response data:**

```jsonc
{
  "success": true,
  "data": {
    "name": "DOC-AC-ASSET-2026-0001-2026-00001",
    "new_state": "Active",
    "approved_by": "qlcl@hosp.vn"
  }
}
```

**Errors:** `NOT_FOUND`, `INVALID_STATE`, `FORBIDDEN`, `INTERNAL_ERROR`.

---

### §2.6 `reject_document` — Từ chối

| Thuộc tính | Giá trị |
|---|---|
| Method | POST |
| Path | `assetcore.api.imm05.reject_document` |
| Roles | `_APPROVE_ROLES` |

**Request body:**

```jsonc
{
  "name": "DOC-AC-ASSET-2026-0001-2026-00001",
  "rejection_reason": "Tài liệu thiếu con dấu cơ quan cấp phép."
}
```

**Hành vi:** Validate `rejection_reason` không rỗng (VR-06), validate `workflow_state = "Pending Review"`, set `workflow_state = "Rejected"` + lưu `rejection_reason`.

**Errors:** `VALIDATION_ERROR` (thiếu reason — VR-06), `NOT_FOUND`, `INVALID_STATE`.

---

### §2.6b `archive_document` — Lưu trữ tài liệu (Active → Archived)

| Thuộc tính | Giá trị |
|---|---|
| Method | POST |
| Path | `assetcore.api.imm05.archive_document` |
| Service | `services/imm05.py::archive_document` |
| Roles | `_APPROVE_ROLES` (Biomed Engineer, Tổ HC-QLCL, CMMS Admin) |

**Request body:**

```jsonc
{
  "name": "DOC-AC-ASSET-2026-0001-2026-00001",
  "reason": "Thiết bị đã decommission ngày 2026-05-20 — không còn áp dụng."
}
```

**Constraint:** `workflow_state = "Active"` — ngược lại trả `INVALID_STATE`. `reason` tùy chọn nhưng khuyến nghị để audit trail (lưu vào `change_summary`).

**Hành vi:**
1. Validate user IN `_APPROVE_ROLES` → else `FORBIDDEN`
2. Validate `workflow_state = "Active"` → else `INVALID_STATE`
3. Set `workflow_state = "Archived"`, `archive_date = today`, `archived_by_version = session.user`, append `change_summary`
4. Save với `flags.ignore_links = True`

**Response data:**

```jsonc
{
  "success": true,
  "data": {
    "name": "DOC-AC-ASSET-2026-0001-2026-00001",
    "new_state": "Archived",
    "archive_date": "2026-05-27"
  }
}
```

**Errors:** `NOT_FOUND`, `INVALID_STATE`, `FORBIDDEN`, `INTERNAL_ERROR`.

> **Phân biệt với auto-archive:** `archive_old_versions` (gọi nội bộ trong `approve_document`) tự lưu trữ các Active doc cùng `(asset_ref, doc_type_detail)` khi version mới được duyệt. `archive_document` (endpoint này) là manual trigger cho admin/QA khi doc không còn áp dụng nhưng chưa có version thay thế (vd. decommission, đổi quy trình).

---

### §2.7 `get_asset_documents` — Tài liệu theo Asset

| Thuộc tính | Giá trị |
|---|---|
| Method | GET |
| Path | `assetcore.api.imm05.get_asset_documents` |

**Params:** `asset` (Asset name)

**Response data:**

> **Lưu ý:** `document_status` trả `"Complete"` hoặc `"Incomplete"` (không phải `"Compliant"`), xác nhận từ `services/imm05.py` line `"document_status": "Incomplete" if missing else "Complete"`. `completeness_pct` hiện trả `0` (placeholder — chưa implement tính toán).

```jsonc
{
  "success": true,
  "data": {
    "asset": "AC-ASSET-2026-0001",
    "completeness_pct": 0,
    "document_status": "Complete",
    "documents": {
      "Legal": [
        {
          "name": "DOC-AC-ASSET-2026-0001-2026-00001",
          "doc_type_detail": "Giấy phép nhập khẩu",
          "doc_number": "NK-2026-0042",
          "workflow_state": "Active",
          "expiry_date": "2027-06-30",
          "days_until_expiry": 442,
          "version": "1.0"
        }
      ],
      "Technical": [],
      "Certification": []
    },
    "missing_required": ["Warranty Card"]
  }
}
```

Auto áp `_apply_visibility_filter`. Compliance tính on-the-fly (v3).

---

### §2.8 `get_dashboard_stats` — KPI Dashboard

| Thuộc tính | Giá trị |
|---|---|
| Method | GET |
| Path | `assetcore.api.imm05.get_dashboard_stats` |
| Permission | Workshop Head, VP Block2, CMMS Admin, Tổ HC-QLCL |

**Response data:**

```jsonc
{
  "success": true,
  "data": {
    "kpis": {
      "total_active": 412,
      "expiring_90d": 28,
      "expired_not_renewed": 5,
      "assets_missing_docs": 17
    },
    "expiry_timeline": [
      {
        "name": "DOC-AC-ASSET-2026-0001-2026-00001",
        "asset_ref": "AC-ASSET-2026-0001",
        "doc_type_detail": "Chứng chỉ hiệu chuẩn",
        "expiry_date": "2026-06-15",
        "days_until_expiry": 38
      }
    ],
    "compliance_by_dept": [
      {
        "dept": "ICU",
        "total_assets": 12,
        "compliant": 11,
        "pct": 91.7
      }
    ]
  }
}
```

---

### §2.9 `get_expiring_documents` — Tài liệu sắp hết hạn

| Thuộc tính | Giá trị |
|---|---|
| Method | GET |
| Path | `assetcore.api.imm05.get_expiring_documents` |

**Params:** `days` (int, default 90, max 365)

**Response data:**

```jsonc
{
  "success": true,
  "data": {
    "days": 90,
    "count": 28,
    "items": [
      {
        "name": "DOC-...",
        "asset_ref": "AC-ASSET-2026-0001",
        "doc_category": "Legal",
        "doc_type_detail": "Giấy phép nhập khẩu",
        "expiry_date": "2026-06-15",
        "days_until_expiry": 38,
        "issuing_authority": "Bộ Y tế"
      }
    ]
  }
}
```

---

### §2.10 `get_compliance_by_dept` — Compliance theo khoa

| Thuộc tính | Giá trị |
|---|---|
| Method | GET |
| Path | `assetcore.api.imm05.get_compliance_by_dept` |

**Response data:**

```jsonc
{
  "success": true,
  "data": [
    {
      "dept": "ICU",
      "total_assets": 12,
      "compliant": 11,
      "incomplete": 1,
      "non_compliant": 0,
      "expiring_soon": 2,
      "pct": 91.7
    }
  ]
}
```

Graceful degradation: trả `[]` nếu SQL query fail.

---

### §2.11 `get_document_history` — Lịch sử Frappe Version

| Thuộc tính | Giá trị |
|---|---|
| Method | GET |
| Path | `assetcore.api.imm05.get_document_history` |

**Params:** `name`

**Response data:**

```jsonc
{
  "success": true,
  "data": [
    {
      "timestamp": "2026-04-18 10:00:00",
      "user": "qlcl@hosp.vn",
      "action": "Workflow Transition",
      "from_state": "Pending Review",
      "to_state": "Active",
      "changes": [
        {"field": "approved_by", "old": null, "new": "qlcl@hosp.vn"},
        {"field": "approval_date", "old": null, "new": "2026-04-18"}
      ]
    }
  ]
}
```

---

### §2.12 `create_document_request` — Tạo Request

| Thuộc tính | Giá trị |
|---|---|
| Method | POST |
| Path | `assetcore.api.imm05.create_document_request` |

**Request body:**

```jsonc
{
  "asset_ref": "AC-ASSET-2026-0001",
  "doc_type_required": "Warranty Card",
  "doc_category": "QA",
  "assigned_to": "ktv@hosp.vn",
  "due_date": "2026-06-07",
  "priority": "High",
  "request_note": "Thiếu warranty card từ đợt nhập mới nhất.",
  "source_type": "Manual"
}
```

Defaults: `due_date = today + 30`, `assigned_to = session.user`, `source_type = "Manual"`, `priority = "Medium"`.

**Response data:**

```jsonc
{
  "success": true,
  "data": {
    "name": "DOCREQ-2026-05-00003",
    "status": "Open"
  }
}
```

---

### §2.13 `get_document_requests` — Liệt kê Request

| Thuộc tính | Giá trị |
|---|---|
| Method | GET |
| Path | `assetcore.api.imm05.get_document_requests` |

**Params:** `asset_ref` (optional), `status` (optional)

**Response data:**

```jsonc
{
  "success": true,
  "data": {
    "count": 3,
    "items": [
      {
        "name": "DOCREQ-2026-05-00003",
        "asset_ref": "AC-ASSET-2026-0001",
        "doc_type_required": "Warranty Card",
        "doc_category": "QA",
        "assigned_to": "ktv@hosp.vn",
        "due_date": "2026-06-07",
        "status": "Open",
        "priority": "High",
        "escalation_sent": false,
        "source_type": "Manual",
        "fulfilled_by": null
      }
    ]
  }
}
```

---

### §2.14 `mark_exempt` — Đánh dấu Miễn NĐ98

| Thuộc tính | Giá trị |
|---|---|
| Method | POST |
| Path | `assetcore.api.imm05.mark_exempt` |
| Roles | `_EXEMPT_ROLES` = {Tổ HC-QLCL, CMMS Admin, Workshop Head} |

**Request body:**

```jsonc
{
  "asset_ref": "AC-ASSET-2026-0001",
  "doc_type_detail": "Chứng nhận đăng ký lưu hành",
  "exempt_reason": "Thiết bị nghiên cứu nhập theo Nghị định 142/2020 điều 15, miễn yêu cầu CN ĐK lưu hành.",
  "exempt_proof": "/files/exempt-proof-nd142.pdf"
}
```

`doc_type_detail` phải IN `EXEMPT_DOC_TYPES = {"Chứng nhận đăng ký lưu hành", "Giấy phép nhập khẩu"}` (VR-11).

**Hành vi:**
1. Validate user IN `_EXEMPT_ROLES`
2. Validate Asset tồn tại
3. Tạo Asset Document với `is_exempt=1`, `workflow_state="Active"`, `doc_number="EXEMPT-{asset_ref}"`, `source_module="IMM-05-Exempt"`, `approved_by=session.user`
4. GW-2 gate trong IMM-04 sẽ tự unblock khi query Active doc với is_exempt=1

**Response data:**

```jsonc
{
  "success": true,
  "data": {
    "document_name": "DOC-AC-ASSET-2026-0001-2026-00002",
    "is_exempt": true,
    "new_asset_document_status": "Compliant (Exempt)"
  }
}
```

**Errors:** `FORBIDDEN`, `NOT_FOUND`, `VALIDATION_ERROR` (thiếu reason/proof hoặc VR-11 fail), `EXEMPT_ERROR`.

---

## §4 — Webhook / Realtime Events

IMM-05 hiện chưa publish realtime event qua `frappe.publish_realtime`. Audit qua Frappe Version DocType.

| Event | Trigger | Audit qua |
|---|---|---|
| document_created | `create_document` | Frappe Version |
| document_approved | `approve_document` | Frappe Version (workflow_state change) |
| document_rejected | `reject_document` | Frappe Version |
| document_archived | `archive_old_versions` (auto) | Frappe Version + `superseded_by` |
| document_expired | `check_document_expiry` scheduler | Expiry Alert Log |
| document_request_created | `create_document_request` | Frappe Version |
| document_request_overdue | `check_overdue_document_requests` | `escalation_sent=1` |

**Roadmap:** Realtime push qua Socket.IO cho dashboard live update — backlog Sprint 8.

---

## §6 — Rate Limits

| Endpoint | Limit | Ghi chú |
|---|---|---|
| `list_documents` | 60 req/min | `page_size` tối đa 100 |
| `get_document` | 120 req/min | |
| `create_document` | 30 req/min | |
| `approve_document` | 60 req/min | |
| `mark_exempt` | 10 req/min | Nhạy cảm — cần audit trail |
| `get_dashboard_stats` | 30 req/min | SQL aggregate query |

---

## §7 — Smoke Test Playbook

```bash
BASE="https://hosp.local/api/method/assetcore.api.imm05"
AUTH="-H 'Authorization: token api_key:api_secret'"

# 1. List tài liệu
curl $AUTH "$BASE.list_documents?page=1&page_size=5"

# 2. Tạo draft
curl -X POST $AUTH "$BASE.create_document" \
  -d "doc_data={\"asset_ref\":\"AC-ASSET-2026-0001\",\"doc_category\":\"Legal\",\"doc_type_detail\":\"Giấy phép nhập khẩu\",\"doc_number\":\"NK-TEST-001\",\"issued_date\":\"2026-01-01\",\"expiry_date\":\"2027-01-01\",\"issuing_authority\":\"Bộ Y tế\",\"file_attachment\":\"/files/test.pdf\"}"

# 3. Approve (thay DOC-NAME)
curl -X POST $AUTH "$BASE.approve_document" -d "name=DOC-NAME"

# 4. Dashboard stats
curl $AUTH "$BASE.get_dashboard_stats"
```

Expected: `{"success": true, "data": {...}}` cho tất cả. Không có `{"message": ...}` outer wrapper.

---

## 11. Notification Contract (BE → FE)

Chuẩn hóa thông báo end-to-end (vòng 5 — cụm Deployment). IMM-05 = quản trị hồ sơ/đăng ký
tài liệu theo asset/model (NĐ98). Mọi lỗi nghiệp vụ raise qua `nthrow(MSG.IMM05_*)`; API wrap
qua shared `handle`/`parse_json` (`assetcore/utils/api_handler.py`) để auto-hydrate envelope.

### 11.1. Envelope

```jsonc
{
  "severity": "warning",            // success | error | warning | info
  "message_code": "IMM05-DOC-NOT-FOUND",
  "title": "Không tìm thấy tài liệu",
  "message": "Không tìm thấy tài liệu: {name}.",
  "action_hint": "Tải lại danh sách hồ sơ để kiểm tra.",
  "context": { "name": "..." }
}
```

FE bắt tập trung ở `composables/useApi.ts` → `useNotify.fromError`.

### 11.2. Severity rule

| Tình huống | severity | http_status |
|---|---|---|
| Validation input (VR-03/VR-06, file thiếu) | `warning` | 422 |
| Không tìm thấy tài liệu / Asset | `warning` | 404 |
| Không có quyền duyệt / Exempt / xem | `error` | 403 |
| Thao tác thành công | `success` | 200 |

### 11.3. Bảng mã MSG.IMM05_*

| message_code | severity | http | Khi nào | Nguồn (service) |
|---|---|---|---|---|
| `IMM05-DOC-NOT-FOUND` | warning | 404 | Tài liệu (AC Document) không tồn tại | `get/submit/approve/reject/archive` |
| `IMM05-ASSET-NOT-FOUND` | warning | 404 | Asset tham chiếu không tồn tại | `get_asset_documents`, dashboard scope |
| `IMM05-FORBIDDEN-APPROVE` | error | 403 | Không có quyền duyệt/từ chối tài liệu | `approve/reject_document` |
| `IMM05-FORBIDDEN-EXEMPT` | error | 403 | Không có quyền đánh dấu Miễn NĐ98 | `mark_exempt` |
| `IMM05-FORBIDDEN-VIEW` | error | 403 | Không có quyền xem tài liệu này | `get_document` |
| `IMM05-FILE-REQUIRED` | warning | 422 | VR-03: phải upload file trước khi gửi duyệt | `submit_for_review` |
| `IMM05-REJECT-REASON-REQUIRED` | warning | 422 | VR-06: lý do từ chối là bắt buộc | `reject_document` |
| `IMM05-VALIDATION` | warning | 422 | Lỗi validation chung (DocType validate) | wrapper `except ValidationError` |
| `IMM05-SUCCESS` | success | 200 | Thao tác hồ sơ thành công (gửi/duyệt/lưu trữ) | các action chính |

> Cảnh báo mềm (hồ sơ sắp hết hạn <30 ngày) giữ `frappe.msgprint(alert=True)` — không raise.

### 11.4. BE checklist

- [ ] Import `from assetcore.utils.notify import MSG, nthrow`.
- [ ] Mọi `raise ServiceError(ErrorCode.*, ...)` nghiệp vụ → `nthrow(MSG.IMM05_*)`.
- [ ] Wrapper `except frappe.ValidationError` rồi bọc `ServiceError(VALIDATION, str(e))` làm rớt
      `message_code`/`severity` → re-`nthrow(MSG.IMM05_VALIDATION, detail=str(e))` (bài học vòng 3).
- [ ] `api/imm05.py` dùng shared `handle`/`parse_json`.
- [ ] Regen FE i18n: `python scripts/gen_fe_messages.py`.

### 11.5. FE checklist

- [ ] Store `stores/imm05.ts` expose `lastApiError` + helper `_captureError`.
- [ ] Action success → `notify.show(MSG.IMM05_*)`; fail → `notify.fromError(store.lastApiError)`.
- [ ] Test store khi phù hợp (vitest).

---

## DoD Checklist

- [x] API Catalog 16 endpoints đầy đủ (incl. `submit_for_review`, `archive_document`)
- [x] Envelope chuẩn `{"success": true, "data": ...}` (KHÔNG Frappe message wrapper)
- [x] Error envelope `{"success": false, "error": ..., "code": ...}`
- [x] Error code catalog đầy đủ
- [x] Visibility filter documented
- [x] TypeScript types cho FE reference
- [x] 16 endpoint specs với request/response examples (incl. `archive_document` §2.6b — bổ sung 2026-05-27)
- [x] Webhook/realtime events table
- [x] Rate limits
- [x] Smoke test playbook
