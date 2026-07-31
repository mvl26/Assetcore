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
| 9 | `get_asset_documents` | GET | Asset-centric | Hồ sơ pháp lý theo Asset + mức đầy đủ **tính thật** & trạng thái **xét hiệu lực** (CR-75, §2.7) |
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

> **CR-75 — phạm vi visibility trong `get_asset_documents`:** filter này áp cho **danh sách hiển thị** `documents` (kèm `hidden_count`), **KHÔNG** áp cho phần **tính toán tuân thủ** (`required_*`, `completeness_pct`, `document_status`, 3 mảng) — tỷ lệ tuân thủ là sự thật của tổ chức, không phụ thuộc người xem (BR-05-20 / ADR-IMM05-03, [02 §IV.2.a](./02_Analysis_Design.md)). Role-gate/row-scope KHÔNG bị nới: truy vấn hiển thị (`scope="user"`) chạy trước truy vấn tính toán (`scope="internal"`).

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
// Dùng SPACE (đồng bộ với workflow fixture + service constants).
// LƯU Ý (BR-05-16): KHÔNG có "Expired" — "hết hạn" là thuộc tính DẪN XUẤT
// (is_expired + predicate EXPIRED_FILTER), KHÔNG phải workflow_state.
export type DocumentWorkflowState =
  | "Draft"
  | "Pending Review"
  | "Active"
  | "Rejected"
  | "Archived";

// Bộ lọc "tình trạng hết hạn" (semantic, không phải state) — gửi qua filter
// `expiry_status` của list_documents (§2.1). Chỉ 'expired' được BE dịch sang
// EXPIRED_FILTER; '' = không ràng buộc.
export type ExpiryStatus = "" | "expired";

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
  // Server-driven CTA (chỉ có ở get_document — chi tiết; §2.2 + 06 §7.5).
  // FE `AssetDocumentDetail` (frontend/src/api/imm05.ts) thêm 2 field này.
  allowed_transitions?: string[];   // _DOC_VALID_TRANSITIONS.get(workflow_state, [])
  can_approve?: 0 | 1;              // int(rbac.can('doc.approve'))
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

> 🔗 **Cross-module (IMM-04 · mobile CR-11d):** endpoint `imm04.get_commissioning_origin` (tab "Nguồn gốc thiết bị" màn Chi tiết thiết bị mobile) đọc **số tài-liệu chuyển-giao** của thiết bị = `frappe.db.count("Asset Document", {asset_ref, source_commissioning})` → field `transferred_doc_count` (integer) trong `CommissioningOriginRecord`. Đây là **read-only count** trên `Asset Document` (repo IMM-05), lọc theo `asset_ref` (thiết bị) + `source_commissioning` (phiếu nghiệm-thu gốc). Không mutate; không cần endpoint IMM-05 mới. Contract: [`ADR-MOBILE-041`](../mobile/ADR-MOBILE-041.md) + [`docs/imm-04/05_API_Specification.md §2.19`](../imm-04/05_API_Specification.md).

### §2.1 `list_documents` — Liệt kê tài liệu

| Thuộc tính | Giá trị |
|---|---|
| Method | GET |
| Path | `assetcore.api.imm05.list_documents` |
| Permission | All authenticated (server auto-filter visibility) |

**Query params:**

| Param | Kiểu | Default | Mô tả |
|---|---|---|---|
| `filters` | JSON string | `"{}"` | Frappe filter dict + 1 marker semantic `expiry_status` (xem dưới) |
| `page` | int | 1 | Trang (1-based) |
| `page_size` | int | 20 | Tối đa 100 |

**Marker `expiry_status` (BR-05-16 — SoT drill "Đã hết hạn"):**

`filters` có thể chứa key đặc biệt `expiry_status` (KHÔNG phải field DB — là marker semantic). Service `list_documents` **pop** marker này trước khi build Frappe filter và dịch sang predicate SoT `EXPIRED_FILTER`:

| `expiry_status` | Service hành vi |
|---|---|
| `"expired"` | Áp **EXPIRED_FILTER** = `{"expiry_date": ["<", today], ...}` + `workflow_state` `["not in", ["Archived","Rejected"]]` (xác định trong `services/imm05.py::EXPIRED_FILTER`). Merge với các filter khác (AND). |
| `""` / vắng | Không ràng buộc hết-hạn. |

> **Bất biến INV-EXP-1:** `get_dashboard_stats().kpis.expired_not_renewed` (count) == `len(list_documents({"expiry_status":"expired"}).items)` (toàn bộ trang) cho mọi tập dữ liệu — cả hai cùng tiêu thụ **một** hằng `EXPIRED_FILTER`. FE KHÔNG gửi `{workflow_state:'Expired'}` (dead-state — đã loại, grep-guard).

> **Tại sao marker thay vì để FE gửi thẳng filter dict?** Predicate `not in [Archived,Rejected]` + `expiry_date<today` là **compliance rule NĐ98 Điều 41** — phải neo ở BE (security/compliance chokepoint), không để FE tự ghép (FE có thể gửi sai/cũ → over/under-count). FE chỉ phát biểu **ý định** (`expiry_status:'expired'`); BE là nơi DUY NHẤT vật chất hóa predicate.

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

**Response data:** Full `AssetDocument` object **+ 2 khóa server-driven CTA** (thêm mới, KHÔNG đổi/bỏ khóa cũ):

| Khóa | Kiểu | Nguồn | Ý nghĩa |
|---|---|---|---|
| `allowed_transitions` | `list[str]` | `_DOC_VALID_TRANSITIONS.get(workflow_state, [])` (services/imm05.py) | Tập **next-state hợp lệ** từ state hiện tại — khớp EXACT fixture `'IMM-05 Document Workflow'`. FE render nút CTA theo tập này (KHÔNG hardcode `workflow_state === 'X'`). |
| `can_approve` | `int` (0/1) | `int(rbac.can('doc.approve'))` | 1 nếu user có capability `doc.approve` (submit trên Asset Document). Gate bổ sung cho nút Phê duyệt / Từ chối / Lưu trữ. |

> **INV-CTA-1 (chống drift):** `set(allowed_transitions)` == `set(next_state hợp lệ của workflow_state trong fixtures/workflow.json)`. Test invariant (07 §III.4) đọc `fixtures/workflow.json` và assert cho MỖI state: `set(next_states từ transitions) == set(_DOC_VALID_TRANSITIONS[state])` + key-set(map) == states[] fixture → thêm/sửa transition mà quên cập nhật map = RED (mirror `_CAL_VALID_TRANSITIONS` imm11).

**Ánh xạ `_DOC_VALID_TRANSITIONS` (grounded fixtures/workflow.json + §3.2 04):**

| workflow_state | allowed_transitions | Action FE |
|---|---|---|
| `Draft` | `["Pending Review", "Archived"]` | Gửi duyệt · Hủy bỏ |
| `Pending Review` | `["Active", "Rejected"]` | Phê duyệt · Từ chối |
| `Rejected` | `["Pending Review"]` | Gửi lại |
| `Active` | `["Archived"]` | Lưu trữ |
| `Archived` | `[]` | (terminal — chỉ xem) |
| `Expired` | `[]` | (declared-dead terminal — chỉ xem, xem ADR-IMM-05-02) |

**Ví dụ response (state = Pending Review, user có doc.approve):**

```json
{
  "success": true,
  "data": {
    "name": "DOC-ASSET-0001-2026-00007",
    "workflow_state": "Pending Review",
    "...": "...(mọi field AssetDocument như cũ)",
    "allowed_transitions": ["Active", "Rejected"],
    "can_approve": 1
  }
}
```

**Errors:**

| Code | Khi |
|---|---|
| `NOT_FOUND` | DocType không tồn tại |
| `FORBIDDEN` | `visibility=Internal_Only` và user không thuộc internal roles |

> **Lưu ý 403 (DONE-gate spec-contract):** `get_document` KHÔNG là action bị hạn chế theo capability — chỉ chặn bằng **visibility** (Internal_Only → in-handler `FORBIDDEN` HTTP-200 Error envelope, KHÔNG raise 4xx). Còn `can_approve=0` **KHÔNG** làm `get_document` trả 403; nó chỉ là cờ để FE ẩn nút. 403 thật cho hành động duyệt xảy ra ở `approve_document`/`reject_document`/`archive_document` (in-handler cap-403 qua `_require_approve_role()`), không phải ở `get_document`.

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

### §2.7 `get_asset_documents` — Hồ sơ pháp lý theo Asset (CR-75)

| Thuộc tính | Giá trị |
|---|---|
| Method | GET |
| Path | `assetcore.api.imm05.get_asset_documents` |
| Handler | `api/imm05.py::get_asset_documents` → `_handle(svc.get_asset_documents, asset)` |
| Service | `services/imm05.py::get_asset_documents` (`@rowscoped`) |
| Consumer | Web IMM-04 `CommissioningDetailView.vue` / `CommissioningForm.vue` (thẻ "Trạng thái Hồ sơ") · Mobile Spec 61 (`getAssetDocuments`, OAS §2.7.b) |
| Audit | KHÔNG (read-only, không sinh Lifecycle Event) |

**Params:** `asset` — `AC Asset.name` (required, query).

> **⚠️ Self-Correction CR-75 (thay thế hợp đồng cũ).** Bản trước của mục này mô tả `completeness_pct = 0` (hằng số stub) và `document_status ∈ {Complete, Incomplete}` — **hợp đồng đó SAI và đã bị thu hồi**. Hai lỗi thiết kế gốc: (1) `completeness_pct` là literal `0` ⇒ mọi consumer đọc mù, thẻ web luôn hiện "0% đầy đủ" dù hồ sơ đủ; (2) `document_status` chỉ đo **SỰ-CÓ-MẶT** (`missing` rỗng ⇒ `Complete`) **KHÔNG đo HIỆU-LỰC** ⇒ hồ sơ bắt buộc **đã quá hạn** vẫn báo `Complete` (dương-tính-giả, vi phạm NĐ98 Điều 41 — xem BR-05-17..BR-05-21 tại [02 §IV.2](./02_Analysis_Design.md)). Ngoài ra từ vựng `Complete|Incomplete` **phân kỳ** với enum SSoT 5 giá trị của `_compute_document_status()` mà 09/02/07 đang trace ⇒ 2 bộ từ vựng cho 1 khái niệm. Bản dưới đây là hợp đồng **duy nhất** kể từ CR-75.

**Response data (mọi khoá LUÔN xuất hiện — không có khoá điều kiện):**

```jsonc
{
  "success": true,
  "data": {
    "asset": "AC-ASSET-2026-0001",

    // ─ Mức đầy đủ (số THẬT, KHÔNG stub) ─
    "required_total": 4,          // int ≥ 0 — mẫu số: loại bắt buộc ÁP DỤNG cho asset
    "required_satisfied": 3,      // int 0..required_total — loại có bản Active CÒN HIỆU LỰC
    "completeness_pct": 75,       // int 0..100 = round(satisfied / total * 100); total==0 ⇒ 100

    // ─ Trạng thái (enum SSoT 5 giá trị + khoá máy-đọc) ─
    "document_status": "Non-Compliant",   // Compliant | Compliant (Exempt) | Expiring_Soon | Non-Compliant | Incomplete
    "is_compliant": 0,                    // int 0|1 — consumer KHÔNG so chuỗi

    // ─ Ba tập rời nhau, mỗi phần tử là `Required Document Type.type_name`, sort A→Z ─
    "missing_required":  ["Hợp đồng bảo trì"],            // chưa có bản Active nào
    "expired_required":  ["Chứng nhận đăng ký lưu hành"], // CÓ bản Active nhưng ĐÃ QUÁ HẠN
    "expiring_required": [],                              // còn hiệu lực, hết hạn trong ≤ 30 ngày

    // ─ Minh bạch phân quyền ─
    "hidden_count": 1,            // int ≥ 0 — số tài liệu bị ẩn khỏi `documents` do visibility

    // ─ Danh sách hiển thị: grouped OBJECT theo doc_category (KHÔNG phải mảng) ─
    "documents": {
      "Legal": [
        {
          "name": "DOC-AC-ASSET-2026-0001-2026-00001",
          "doc_category": "Legal",
          "doc_type_detail": "Chứng nhận đăng ký lưu hành",
          "doc_number": "NK-2026-0042",
          "version": "1.0",
          "workflow_state": "Active",
          "expiry_date": "2026-06-30",
          "days_until_expiry": -26,   // DẪN XUẤT lúc đọc (server clock), KHÔNG đọc cột đã lưu
          "is_expired": 1,            // int 0|1 — DẪN XUẤT lúc đọc theo predicate SSoT
          "visibility": "Public",
          "is_exempt": 0,             // Check → int 0|1
          "approved_by": "qa@benhvien.vn",
          "approval_date": "2025-06-30"
        }
      ],
      "Technical": []
    }
  }
}
```

**Khoá bị thu hồi / đổi nghĩa:**

| Khoá | Trước CR-75 | Từ CR-75 |
|---|---|---|
| `completeness_pct` | hằng `0` | int 0..100 tính thật (§2.7.a) |
| `document_status` | `"Complete"` / `"Incomplete"` | enum 5 giá trị SSoT `_compute_document_status()` |
| `missing_required` | loại bắt buộc **toàn cục** thiếu bản Active | loại bắt buộc **ÁP DỤNG** thiếu bản Active **còn hiệu lực**, đã tách phần quá hạn sang `expired_required` |
| `documents[].days_until_expiry` | cột đã lưu (stale từ lần save cuối) | dẫn xuất lúc đọc theo server clock |
| *(mới)* | — | `required_total`, `required_satisfied`, `is_compliant`, `expired_required`, `expiring_required`, `hidden_count`, `documents[].is_expired` |
| *(mới — AC-CR-81)* | — | `documents[].file_url`, `documents[].file_name`, `documents[].file_size`, `documents[].is_private`, `documents[].has_file` — **xem §2.7.c** (ví dụ trên chỉ liệt kê 13 khoá của CR-75; mỗi dòng THẬT có **18** khoá) |

> **Backward-compat:** thay đổi là **additive + sửa giá trị sai**, KHÔNG xoá/đổi tên khoá cũ ⇒ `frontend/src/stores/imm05.ts::fetchAssetDocuments` (đọc `documents` / `completeness_pct` / `document_status` / `missing_required`) vẫn chạy không sửa. Chỉ consumer **so chuỗi** `document_status` phải đổi sang `is_compliant` (xem [06 §4.4](./06_Frontend_Design.md) + A5).

**Errors:** `NOT_FOUND` (asset không tồn tại — `MSG.IMM05_ASSET_NOT_FOUND`) · `FORBIDDEN` **in-handler trên HTTP-200** khi `@rowscoped` bắt `frappe.PermissionError` (thiếu DocPerm read `Asset Document`) — **KHÔNG** raise HTTP-4xx (LL-BE-42..49).

---

### §2.7.a Thuật toán chuẩn (normative) — mẫu số ÁP DỤNG + xét hiệu lực

Ký hiệu: `today = nowdate()` (server clock, KHÔNG client).

**B1 — Mẫu số `required_total` (BR-05-17).** Lấy `Required Document Type` với `is_mandatory = 1`, giữ loại `t` **áp dụng** cho asset:

```
applies(t, asset) ⟺ (not t.applies_to_asset_category)                    # rỗng/NULL ⇒ áp mọi nhóm
                    or t.applies_to_asset_category == asset.asset_category
```

`asset.asset_category` đọc bằng `frappe.db.get_value("AC Asset", asset, "asset_category")`. `required_total = |{t : is_mandatory ∧ applies(t, asset)}|`.

> **[ROADMAP] `applies_when_radiation`** — `Required Document Type.applies_when_radiation` (Check) **KHÔNG** tham gia mẫu số ở CR-75. Dữ liệu bức xạ tồn tại ở `AC Asset Category.has_radiation` (không phải trên `AC Asset`) nên mở rộng sẽ đổi mẫu số cho nhóm thiết bị không bức xạ ⇒ thay đổi ngoài phạm vi A1. Backlog **CR-75b**: `applies(t, asset)` bổ sung `∧ (not t.applies_when_radiation or category.has_radiation)`. Cho tới khi đó, loại có `applies_when_radiation=1` được xử lý **như loại thường** (chỉ lọc theo category).

**B2 — Predicate hiệu lực (SSoT DUY NHẤT, BR-05-18).** Dùng đúng predicate `expired_filter()` (`services/imm05.py`, BR-05-16):

```
expired(d) ⟺ d.expiry_date is set ∧ d.expiry_date < today ∧ d.workflow_state ∉ {Archived, Rejected}
```

Bản Python (dùng cho row đã nạp) là **cặp song sinh** `is_expired_row(row, today=None)` — bắt buộc trả kết quả trùng khít với query dùng `expired_filter()` (invariant **INV-EXP-2**, [04 §4.4](./04_Backend_Design.md)). **Cấm** viết lại biểu thức ngày ở chỗ khác; **cấm** đọc cột đã lưu `Asset Document.is_expired` cho response.

**B3 — Phân loại từng loại bắt buộc `t`.** Đặt `live(t) = {d : d.doc_type_detail == t ∧ d.workflow_state == 'Active' ∧ ¬expired(d)}`:

| Điều kiện | Kết quả |
|---|---|
| `live(t) ≠ ∅` | `t` **satisfied** (`required_satisfied += 1`) |
| `live(t) = ∅` ∧ ∃ `d` Active với `expired(d)` | `t ∈ expired_required` |
| `live(t) = ∅` ∧ không có bản Active nào | `t ∈ missing_required` |

`missing_required ∩ expired_required = ∅` và `|missing| + |expired| = required_total − required_satisfied` (**INV-DOC-2**). Ba mảng sort tăng dần theo `type_name` (output tất định).

**B4 — `expiring_required` (ngưỡng 30 ngày).** Với `t` satisfied: `cover(t) = max(date_diff(d.expiry_date, today) for d ∈ live(t))`; bản không có `expiry_date` ⇒ `+∞` (không bao giờ sắp hết hạn). `t ∈ expiring_required ⟺ cover(t) ≤ 30`. Ngưỡng 30 = tier `Critical` của `_ALERT_THRESHOLDS` (`services/imm05.py`) — **KHÔNG** hằng số mới.

**B5 — `completeness_pct`.** `required_total == 0 ⇒ 100` (không chia 0). Ngược lại `round(required_satisfied / required_total * 100)` → int 0..100.

**B6 — `document_status` (BR-05-19).** Gọi **đúng** SSoT `_compute_document_status(pct, has_expiring, has_expired, is_exempt)` (`assetcore/assetcore/doctype/asset_document/asset_document.py`, lazy-import trong hàm), truyền:

```
pct          = completeness_pct
has_expired  = bool(expired_required)
has_expiring = bool(expiring_required)
is_exempt    = required_total > 0 ∧ required_satisfied == required_total
               ∧ not expired_required ∧ not expiring_required
               ∧ ∃ t áp dụng, ∃ d ∈ live(t) với d.is_exempt == 1        # "narrowed exempt"
```

Thứ tự ưu tiên của hàm SSoT **giữ nguyên** (`is_exempt → has_expired → has_expiring → pct ≥ 100 → Incomplete`); việc **thu hẹp đối số `is_exempt` tại call-site** là thứ chặn dương-tính-giả "1 giấy miễn đăng ký ⇒ cả hồ sơ Compliant (Exempt)" — xem ADR-IMM05-02 ([02 §IV.2.a](./02_Analysis_Design.md)).

**B7 — `is_compliant`.** `is_compliant = 1 ⟺ document_status ∈ {Compliant, Compliant (Exempt), Expiring_Soon}`, ngược lại `0`. Tương đương máy-kiểm: `is_compliant == int(required_satisfied == required_total) == int(completeness_pct == 100)` (**INV-DOC-3**). `Expiring_Soon` **KHÔNG** kéo `is_compliant` xuống 0 (hồ sơ vẫn còn hiệu lực — cảnh báo, không phải vi phạm).

**B8 — Hai truy vấn, hai vai (BR-05-20).**

| Truy vấn | Filters | `scope` | Dùng cho |
|---|---|---|---|
| **V** (hiển thị) | `_apply_visibility_filter({"asset_ref": asset})` | mặc định `"user"` | `documents` (group theo `doc_category`, fallback `"Other"`) |
| **C** (tính toán) | `{"asset_ref": asset}` — **KHÔNG** lọc visibility | `LIST_SCOPE_INTERNAL` | `required_*`, `completeness_pct`, 3 mảng, `document_status` |

Thứ tự bắt buộc: chạy **V trước C**. V (`scope="user"` → `frappe.get_list`) giữ nguyên role-gate/row-scope; nếu user thiếu DocPerm read thì `PermissionError` phát ra **trước** khi tới C ⇒ `@rowscoped` trả 403 in-envelope. C là **aggregate nội bộ** (giống pattern denorm-enrich `scope="internal"` ở `list_documents`), KHÔNG phải bề mặt phân quyền. `hidden_count = |C| − |V|`.

**B9 — DocItem dẫn xuất lúc đọc (BR-05-21).** Mỗi dòng trong `documents`: `is_expired = int(is_expired_row(row))`; `days_until_expiry = date_diff(expiry_date, today)` khi có `expiry_date`, ngược lại `null`. Cột DB `Asset Document.is_expired` / `days_until_expiry` **không đổi** (scheduler + `list_documents` giữ nguyên) — chỉ response của endpoint này là dẫn xuất.

**Ví dụ chốt biên (test-fixed):**

| Tình huống | `is_expired` dòng | Trạng thái loại | `document_status` |
|---|---|---|---|
| Active, `expiry_date = today` | 0 | satisfied + expiring (cover=0) | `Expiring_Soon` |
| Active, `expiry_date = today − 1` | 1 | `expired_required` | `Non-Compliant` |
| Active, `expiry_date = today + 30` | 0 | satisfied + expiring | `Expiring_Soon` |
| Active, `expiry_date = today + 31` | 0 | satisfied | `Compliant` |
| **Archived**, `expiry_date = today − 100` | **0** | không phải bản Active ⇒ không tính | theo loại khác |
| `required_total == 0` | — | — | `Compliant`, `pct = 100` |

---

### §2.7.b OAS mobile — op `getAssetDocuments` (CR-61(a) parity, A6)

`docs/mobile/openapi/assetcore-mobile.openapi.yaml` hiện có **0 op imm05**. CR-75 curate op này. Ràng buộc: **áp dụng cùng lượt với thay đổi `services/imm05.py`** để cite `@source` trỏ đúng dòng (guard cite-parity), thêm `paths` +1, `components.schemas` +3, và **đồng bộ counters** `_EXPECTED_TEST_COUNT` / `_GUARD_SUITE_EXPECTED['test_mobile_oas.py']` / `_GUARD_SUITE_SUM` / `_MOBILE_OAS_TOTAL` theo số TC guard thực thêm (xem [07 §III.6](./07_Testing_QA.md)).

- **Path:** `/api/method/assetcore.api.imm05.get_asset_documents` · **GET** · `operationId: getAssetDocuments` · tag imm05.
- **Param:** `asset` (query, **required**, string) — signature `get_asset_documents(asset)` không default ⇒ `required: true` (typed-query-param parity CR-05).
- **200:** `oneOf [AssetDossierEnvelope (success:true) | Error (success:false)]`, CLOSED-SCHEMA Decision-B, KHÔNG discriminator (mirror `getPmCalendar`). **401** dispatcher (guest/no-token) · **403 in-envelope trên HTTP-200** (`@rowscoped`), KHÔNG status-line 403.
- **Schemas mới (3):**

```yaml
AssetDossierEnvelope:      # success:true + data: $ref AssetDossier — required [success, data]
AssetDossier:              # additionalProperties: false
  required: [asset, required_total, required_satisfied, completeness_pct,
             document_status, is_compliant, missing_required, expired_required,
             expiring_required, hidden_count, documents]
  properties:
    completeness_pct:  { type: integer, minimum: 0, maximum: 100 }
    required_total:    { type: integer, minimum: 0 }
    required_satisfied:{ type: integer, minimum: 0 }
    document_status:   { type: string, enum: ['Compliant', 'Compliant (Exempt)',
                                              'Expiring_Soon', 'Non-Compliant', 'Incomplete'] }
    is_compliant:      { type: integer, enum: [0, 1] }
    missing_required:  { type: array, items: { type: string } }
    expired_required:  { type: array, items: { type: string } }
    expiring_required: { type: array, items: { type: string } }
    hidden_count:      { type: integer, minimum: 0 }
    documents:         { type: object, additionalProperties:
                           { type: array, items: { $ref: AssetDossierDocItem } } }   # GROUPED-OBJECT
AssetDossierDocItem:       # additionalProperties: false
  required: [name, doc_category, doc_type_detail, doc_number, version, workflow_state,
             expiry_date, days_until_expiry, is_expired, visibility, is_exempt,
             approved_by, approval_date]
  # expiry_date/days_until_expiry/approved_by/approval_date: nullable
  # is_expired, is_exempt: integer enum [0,1]  (Check emit int — quirk CR-01, KHÔNG bool)
  # workflow_state: enum 6 (Draft|Pending Review|Active|Archived|Expired|Rejected)
  # doc_category:  enum 5 + 'Other' (fallback khi doc_category rỗng)
```

- **Bẫy phải ghi trong `description`** (nguồn: `/home/miyano/assetcore-mobile/docs/api/CONTRACT-REQUESTS.md` CR-61): (1) rows-key = `data.documents` **object**, KHÔNG `data.items[]`; (2) `is_expired`/`is_exempt` là int 0/1; (3) mobile **KHÔNG** so ngày bằng đồng hồ máy — dùng `is_expired` (SSoT overdue server-flag, khử workaround `resolveDossierCompliance` client-side ở Spec 61 §3c/§4a); (4) `document_status` nay **có** xét hiệu lực ⇒ gỡ ghi chú "chỉ đo sự-có-mặt"; (5) `completeness_pct` hết stub ⇒ gỡ guard "chỉ render khi > 0".
- **KHÔNG thuộc CR-75 (giữ mở):** CR-61(b) `file_url` / stream private-file (họ G6) — vẫn chặn tính năng mở/tải file trên mobile. → **ĐÃ ĐÓNG PHẦN METADATA tại AC-CR-81, xem §2.7.c** (phần *stream/proxy tệp riêng tư* vẫn mở, xem §2.7.c mục "Ngoài phạm vi").

---

### §2.7.c AC-CR-81 — mỗi dòng hồ sơ phơi TỆP THẬT (5 khoá tệp)

> **Self-Correction (AC-CR-81).** Bản CR-75 **cố ý** không phát `file_url` (ghi "CR-61(b) họ G6, ngoài phạm vi"). Hệ quả đo được: màn "Hồ sơ pháp lý thiết bị" là **state chết** — người dùng thấy dòng "Giấy phép nhập khẩu · Active · còn 300 ngày" nhưng **không có đường nào mở tờ giấy phép**; mobile Spec 61 phải cắt tính năng đọc hồ sơ; web `DocumentDossierCard.vue` chỉ vẽ được thẻ tổng hợp. Mục này là hợp đồng bổ sung, **additive** — 0 khoá cũ bị đổi/xoá.

**Phạm vi:** CHỈ `services/imm05.py::get_asset_documents`. `list_documents` / `get_document` / `get_dashboard_stats` **KHÔNG đụng** (A5).

#### F0 — 5 khoá mới trên MỖI dòng `documents[<doc_category>][]`

| Khoá | Kiểu | Giá trị khi trống | Nguồn sự thật |
|---|---|---|---|
| `file_url` | `str` | `""` (KHÔNG `null`) | `File.file_url` của File doc khớp `Asset Document.file_attachment` |
| `file_name` | `str` | `""` | `File.file_name`; rỗng ⇒ basename của `file_url` |
| `file_size` | `int` (BYTE) | `0` | `File.file_size` |
| `is_private` | `int` `0\|1` | `0` | `File.is_private` |
| `has_file` | `int` `0\|1` | `0` | dẫn xuất — xem F3 |

**Always:** 5 khoá **LUÔN** xuất hiện trên mọi dòng (kể cả dòng chưa đính tệp) ⇒ client không null-check khoá (đối xứng nguyên tắc "không có khoá điều kiện" của §2.7). **Never:** `None`/`null` cho bất kỳ khoá nào trong 5 khoá; `bool` cho `has_file`/`is_private` (Frappe `Check` emit int — quirk **CR-01**; `True` lọt vào JSON làm vỡ strict-deser Dart/Kotlin và làm `type(x) is int` sai ở test).

#### F1 — Nguồn dữ liệu THÔ: `Asset Document.file_attachment` (Attach)

Field `file_attachment` (Attach, `asset_document.json`) chứa **chuỗi URL tự do**. Thực tế 3 nhóm giá trị cùng tồn tại:

1. URL hợp lệ trỏ 1 `File` doc (upload qua SSoT `api/files.upload_attachment`);
2. **link mồ côi** — chuỗi đúng dạng `/files/…` nhưng **không còn** `File` doc (dữ liệu import, hoặc ô "gõ tay đường dẫn" thời chưa có upload SSoT — xem `memory/file_attachment_upload_ssot.md`, hoặc File bị xoá);
3. rỗng (`""`/`None`) — hồ sơ chưa đính tệp (hợp lệ ở `Draft`; VR-03 chỉ chặn ở `Pending Review`).

#### F2 — Batch-resolve: **1 truy vấn `File` cho toàn payload** (chống N+1)

```
U = { row.file_attachment : row ∈ V, row.file_attachment truthy }        # V = tập ĐÃ lọc visibility
if U ≠ ∅:  M = { f.file_url → f for f in File where file_url ∈ U }       # ĐÚNG 1 query
else:      M = {}                                                        # 0 query — KHÔNG phát `IN ()`
```

- Tập vào là **`V`** (danh sách hiển thị đã lọc `_apply_visibility_filter`), **KHÔNG** phải `C` (tập tính toán org-truth) ⇒ URL của dòng bị ẩn **không bao giờ** được resolve, càng không ra response (**AC5**).
- Query `File` chạy **system-scope** (`ignore_permissions=True`): `File` có mô hình quyền riêng (theo `attached_to_*`), persona KTV không có DocPerm `File` ⇒ query permission-aware trả rỗng và **mọi** dòng sẽ `has_file=0` cho đúng nhóm người dùng chính — đó là **dead-gate** (cùng class-of-bug ADR-IMM09-SPARE-02). Chỉ đọc **4 field metadata** (`file_url`, `file_name`, `file_size`, `is_private`), **KHÔNG** đọc nội dung tệp, và chỉ cho URL của dòng người gọi ĐƯỢC XEM ⇒ không nới quyền.
- Số truy vấn `File` **KHÔNG** phụ thuộc số dòng (**INV-FILE-4**). Trùng URL giữa nhiều dòng ⇒ dedup trước khi query.
- 2 `File` doc cùng `file_url` (dữ liệu lịch sử): lấy bản **đầu tiên theo `creation asc`** (tất định, không phụ thuộc thứ tự MySQL).

#### F3 — Luật LINK MỒ CÔI (khoá nghiệp vụ của AC-CR-81)

```
has_file(row) = 1  ⟺  row.file_attachment truthy  ∧  row.file_attachment ∈ M
has_file(row) = 0  ⟹  file_url = "" ∧ file_name = "" ∧ file_size = 0 ∧ is_private = 0
```

Endpoint **KHÔNG phát link chết**: link mồ côi ⇒ `has_file = 0` ∧ `file_url = ""`. Lý do nghiệp vụ: một nút «Mở tệp» dẫn tới 404 giữa ca trực khiến kỹ thuật viên/thanh tra tin rằng bệnh viện **mất** hồ sơ NĐ98, trong khi sự thật là *bản ghi trỏ sai*; nhãn «Chưa đính kèm tệp» nói đúng việc phải làm (đính lại tệp).

`Asset Document.file_attachment` **thô KHÔNG BAO GIỜ** có mặt trong response (không phải khoá thứ 19) — nó bị `pop` khỏi dòng sau khi resolve.

#### F4 — `file_name` lấy từ `File`, KHÔNG dùng cột denorm

`Asset Document.file_name_display` được tính lúc `before_save` từ chuỗi URL (`asset_document.py:198-199`) ⇒ stale khi tệp bị thay và **không** phân biệt mồ côi. SSoT là `File.file_name`; rỗng ⇒ `file_url.rsplit("/", 1)[-1]`. Mobile CR-61(b) xin `file_name_display` — khoá thay thế chính thức là **`file_name`** (ghi rõ trong OAS `description`).

#### F5 — Tệp riêng tư (`is_private = 1`)

`file_url` dạng `/private/files/…` chỉ mở được **trong cùng phiên đăng nhập** (cookie `sid`, Frappe kiểm quyền ở tầng phục vụ tệp). Hợp đồng chỉ **công bố** `is_private` để client chọn cách mở (in-app WebView mang cookie thay vì trình duyệt ngoài). **Ngoài phạm vi AC-CR-81** (giữ mở, thuộc họ G6): endpoint stream/proxy tệp trả bytes, URL ký hạn (`signed URL`), tải offline.

#### F6 — 0 REGRESS nhánh tuân thủ (AC4)

9 khoá `completeness_pct` · `document_status` · `required_satisfied` · `required_total` · `is_compliant` · `missing_required` · `expired_required` · `expiring_required` · `hidden_count` **giữ nguyên giá trị** trước/sau. Nhánh tính toán (`_dossier_compliance`, `_applicable_required_types`, `_DOSSIER_COMPUTE_FIELDS`, truy vấn **C**) **KHÔNG được chạm** — 5 khoá tệp sinh **hoàn toàn** trên nhánh hiển thị **V**.

#### Invariants (đo được)

| ID | Phát biểu |
|---|---|
| **INV-FILE-1** | ∀ dòng: `{file_url, file_name, file_size, is_private, has_file} ⊆ keys(dòng)`, 0 giá trị `None`. |
| **INV-FILE-2** | `has_file == 1 ⟺ file_url != ""` (song ánh — không có trạng thái nửa vời). |
| **INV-FILE-3** | `has_file == 0 ⇒ file_name == "" ∧ file_size == 0 ∧ is_private == 0`. |
| **INV-FILE-4** | Số truy vấn `File` mỗi lượt gọi `= 1` khi `U ≠ ∅`, `= 0` khi `U = ∅` — **độc lập** số dòng. |
| **INV-FILE-5** | 9 khoá tuân thủ (F6) bất biến trước/sau AC-CR-81. |
| **INV-FILE-6** | ∀ URL được resolve: ∃ dòng ∈ `V` có `file_attachment` bằng URL đó (0 URL của dòng bị ẩn). |
| **INV-FILE-7** | `type(has_file) is int ∧ type(is_private) is int` — **không** `bool` (bool là subclass của int ⇒ test phải `assertNotIsInstance(v, bool)`). |
| **INV-FILE-8** | Key-set mỗi dòng == ĐÚNG 18 khoá (13 CR-75 + 5 tệp) — `file_attachment` thô KHÔNG lọt. |

#### Ví dụ payload (trích 1 dòng có tệp + 1 dòng mồ côi)

```jsonc
"documents": {
  "Legal": [
    {
      "name": "DOC-AC-ASSET-2026-0001-2026-00001",
      "doc_type_detail": "Chứng nhận đăng ký lưu hành",
      "workflow_state": "Active", "is_expired": 0, "days_until_expiry": 300,
      // ─ 5 khoá AC-CR-81 ─
      "file_url": "/private/files/nk-2026-0042.pdf",
      "file_name": "nk-2026-0042.pdf",
      "file_size": 245678,
      "is_private": 1,
      "has_file": 1
    },
    {
      "name": "DOC-AC-ASSET-2026-0001-2026-00002",
      "doc_type_detail": "Hợp đồng bảo trì",
      "workflow_state": "Draft", "is_expired": 0, "days_until_expiry": null,
      // file_attachment = "/files/import-2019.pdf" nhưng File doc KHÔNG còn ⇒ KHÔNG phát link chết
      "file_url": "", "file_name": "", "file_size": 0, "is_private": 0, "has_file": 0
    }
  ]
}
```

#### Boundaries — AC-CR-81

- **Always:** 5 khoá luôn có mặt, kiểu `int` cho cờ · batch **1** query `File` · tập vào = dòng ĐƯỢC XEM · link mồ côi ⇒ `has_file=0` ∧ `file_url=""` · `file_attachment` thô bị `pop` trước khi trả.
- **Ask first:** thêm khoá thứ 6 (`file_ext`, `uploaded_by`, `download_url` ký hạn) · đổi `has_file` sang boolean · cấp `file_url` cho dòng bị ẩn · resolve tệp cho `list_documents`/`get_document`.
- **Never:** phát `file_attachment` thô · resolve theo từng dòng (N+1) · resolve trên tập **C** · đọc `file_name_display` · chạm `_dossier_compliance` / `expired_filter()` / `list_documents` · thêm path/schema OAS · `bench migrate` (read-path thuần, 0 field DB mới).

**Errors:** KHÔNG đổi — `NOT_FOUND` (asset ∄) · `FORBIDDEN` **in-handler trên HTTP-200** (`@rowscoped`). Lỗi resolve tệp (File bị xoá) **KHÔNG** phải lỗi API: nó là dữ liệu, biểu diễn bằng `has_file = 0`.

---

### §2.7.d OAS mobile + guard AC-CR-81 (delta thực thi)

- **Schema chạm:** CHỈ `AssetDossierDocItem` — `properties` 13→**18**, `required` 13→**18**, `additionalProperties: false` GIỮ. `paths` GIỮ **108** · `components.schemas` GIỮ **283** · `components.parameters` GIỮ **38** (5 khoá là property **scalar**, KHÔNG tách schema con).
- **Cite `@source`:** mỗi `description` của 5 khoá chứa cite `services/imm05.py:<dòng> <symbol>` trỏ **đúng vùng AST** của symbol. Cite phải nằm trong `description`, **KHÔNG** trong comment YAML (comment không vào spec đã parse ⇒ rot không bắt được — bài học CR-76).
- **Guard:** `assetcore/tests/test_mobile_oas.py::TestMobileAssetDossierFileContract` — **8 TC** `cr81_a..h` (a: 5 khoá có mặt + required + 18-key closed · b: kiểu int/enum/non-nullable · c: cite-drift · d: khai luật mồ côi + batch + route theo `has_file` · e: paths/schemas không đổi · f: 0 regress `AssetDossier` 11 khoá + grouped-object + oneOf · g: anti-stale câu "file_url ngoài phạm vi" · h: khai anti-leak dòng bị ẩn). `cr75_g` được **SUPERSEDE** (13→18 khoá; `assertNotIn("file_url")` → `assertIn`).
- **Counters đồng bộ (delta +8):** `_EXPECTED_TEST_COUNT` 975→**983** (+2 echo trong cùng file) · `_GUARD_SUITE_EXPECTED['test_mobile_oas.py']` 975→**983** · `_GUARD_SUITE_SUM` 1118→**1126** · `_MOBILE_OAS_TOTAL` 1144→**1152** · thêm `cr81_asset_dossier_file_delta = 8` (kèm dòng trừ trong `pre_fc3_six`) tại `test_mobile_docset.py`.
- **⚠️ Cite refresh khi BE land:** cite hiện trỏ `services/imm05.py:610-618 get_asset_documents`. Khi BE tách helper batch-resolve riêng (§04 §4.4-bis), **PHẢI** refresh cite sang symbol + dòng THẬT — nếu không `cr81_c` ĐỎ **đúng thiết kế** (đây là guard, không phải phiền toái).

---

---

### §2.8 `get_dashboard_stats` — KPI Dashboard

| Thuộc tính | Giá trị |
|---|---|
| Method | GET |
| Path | `assetcore.api.imm05.get_dashboard_stats` |
| Permission | Workshop Head, VP Block2, CMMS Admin, Tổ HC-QLCL |

**KPI semantics (predicate đếm — phải đồng nhất với drill list):**

| KPI | Predicate (SoT) | Drill tile dẫn về |
|---|---|---|
| `total_active` | `workflow_state = 'Active'` | `list_documents({workflow_state:'Active'})` |
| `expiring_90d` | `workflow_state='Active' ∧ today < expiry_date ≤ today+90` | `list_documents` (expiry window 90, §2.1) |
| `expired_not_renewed` | **EXPIRED_FILTER** = `expiry_date IS NOT NULL ∧ expiry_date < today ∧ workflow_state NOT IN ('Archived','Rejected')` (BR-05-16) | `list_documents({expiry_status:'expired'})` — CÙNG hằng `EXPIRED_FILTER` |
| `assets_missing_docs` | `# AC Asset không có Active doc` (theo thiết bị, không drill — tile tĩnh) | — |

> **`expired_not_renewed` (BR-05-16, INV-EXP-1):** Đếm hồ sơ **còn sống** đã quá hạn = compliance-gap NĐ98 Điều 41 (thiết bị vận hành với giấy phép hết hạn phải hiện). **Đếm:** Active/Draft/Pending Review/(Rejected*) quá hạn. **KHÔNG đếm:** Archived/Rejected (đã thu hồi — không phải gap còn sống), doc `expiry_date` NULL (không có hạn). KPI count **bằng** `len(items)` của drill `{expiry_status:'expired'}` (chênh=0) vì cả hai gọi **một** hằng `EXPIRED_FILTER` trong `services/imm05.py`. *(Self-Correction Vòng 19: trước fix count đếm cả Archived/Rejected + drill lọc dead-state `Expired` → list rỗng. Xem 02 §IV.3 + BR-05-16.)*

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
