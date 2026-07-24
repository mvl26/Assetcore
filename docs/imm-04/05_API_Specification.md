# 05 — API Specification

| Mục | Giá trị |
|---|---|
| Module | IMM-04 — Lắp đặt, Định danh & Kiểm tra Ban đầu |
| Phạm vi | Per-module |
| Owner | BE Lead |
| Base URL | `/api/method/assetcore.api.imm04.<function>` |
| Auth | Frappe session cookie + `X-Frappe-CSRF-Token` (browser) hoặc `Authorization: token <key>:<secret>` (API) |

---

## 0. API Catalog — Toàn bộ endpoint module

> Ground truth: `assetcore/api/imm04.py` — **33** `@frappe.whitelist()` endpoints (Wave-2 branch, 2026-05-14).

| # | Endpoint | Method | Mô tả ngắn | Idempotent |
|---|---|---|---|---|
| 1 | `get_form_context` | GET | Chi tiết phiếu + allowed transitions | ✓ |
| 2 | `list_commissioning` | GET | Danh sách phiếu + pagination | ✓ |
| 3 | `get_barcode_lookup` | GET | Tra cứu barcode/QR | ✓ |
| 4 | `get_dashboard_stats` | GET | KPI dashboard | ✓ |
| 5 | `generate_qr_label` | GET | Sinh dữ liệu QR label | ✓ |
| 6 | `get_po_details` | GET | Auto-fill từ AC Purchase | ✓ |
| 7 | `search_link` | GET | Autocomplete Link fields | ✓ |
| 8 | `check_sn_unique` | GET | Kiểm tra serial unique (on-blur) | ✓ |
| 9 | `list_non_conformances` | GET | Danh sách NC theo phiếu | ✓ |
| 10 | `generate_handover_pdf` | GET | Sinh URL PDF biên bản bàn giao | ✓ |
| 11 | `get_users_by_role` | GET | Danh sách user theo Frappe role | ✓ |
| 12 | `get_gate_status` | GET | Trạng thái G01–G06 gate cho phiếu | ✓ |
| 13 | `list_my_pending_approvals` | GET | Phiếu tôi cần duyệt | ✓ |
| 14 | `get_commissioning_origin` | GET | Truy xuất nguồn gốc commissioning của asset | ✓ |
| 15 | `transition_state` | POST | Workflow transition (+`board_approver` optional khi CR-bound · BR-04-12) | ✗ |
| 16 | `submit_commissioning` | POST | Submit phiếu (docstatus 0→1) | ✗ |
| 17 | `save_commissioning` | POST | Lưu field inline | ✓ |
| 18 | `create_commissioning` | POST | Tạo phiếu mới | ✗ |
| 19 | `report_nonconformance` | POST | Tạo NC | ✗ |
| 20 | `close_nonconformance` | POST | Đóng NC | ✗ |
| 21 | `assign_identification` | POST | Gán SN + QR | ✓ |
| 22 | `submit_baseline_checklist` | POST | Nộp kết quả đo kiểm | ✗ |
| 23 | `clear_clinical_hold` | POST | Gỡ Clinical Hold | ✗ |
| 24 | `retry_mint_asset` | POST | Retry tạo AC Asset (sau lỗi `mint_asset_pending`) | ✗ |
| 25 | `upload_document` | POST | Upload hồ sơ CO/CQ/... | ✓ |
| 26 | `approve_clinical_release` | POST | Set board_approver + approve | ✗ |
| 27 | `report_doa` | POST | Báo DOA | ✗ |
| 28 | `delete_commissioning` | POST | Xóa phiếu (Draft only) | ✗ |
| 29 | `cancel_commissioning` | POST | Hủy phiếu (Submitted) | ✗ |
| 30 | `submit_for_approval` | POST | Gửi phiếu cho người duyệt | ✗ |
| 31 | `approve_pending` | POST | Duyệt / Từ chối phiếu chờ | ✗ |
| 32 | `create_from_purchase` | POST | Tạo phiếu từ AC Purchase (link) | ✗ |
| 33 | `get_lifecycle_timeline` | GET | Timeline `Asset Lifecycle Event` của phiếu | ✓ |

---

## 0b. Catalog đầy đủ (34 endpoints)

> Ground truth refreshed 2026-05-27: `grep -c "^@frappe.whitelist" assetcore/api/imm04.py` = **34**.
> So với §0 cũ (snapshot 2026-05-14, 33 endpoint), bổ sung `generate_internal_qr`.
> Categorization: **Primary** = thuộc happy path 11-state workflow, **Support** = utility/helper UI/dashboard, **Internal** = admin/diagnostic/retry/cancel.

| # | Method | Path | Mô tả ngắn | Use case |
|---|---|---|---|---|
| 01 | POST | /api/method/assetcore.api.imm04.create_commissioning | Tạo phiếu nghiệm thu mới | Primary |
| 02 | POST | /api/method/assetcore.api.imm04.create_from_purchase | Tạo phiếu từ AC Purchase (link) | Primary |
| 03 | POST | /api/method/assetcore.api.imm04.save_commissioning | Lưu inline field (Draft/edit) | Primary |
| 04 | POST | /api/method/assetcore.api.imm04.transition_state | Workflow transition (G01–G06) + cấp `board_approver` 4-mắt khi CR-bound (BR-04-12 · §5b) | Primary |
| 05 | POST | /api/method/assetcore.api.imm04.submit_commissioning | Submit phiếu (docstatus 0→1, mint Asset) | Primary |
| 06 | POST | /api/method/assetcore.api.imm04.assign_identification | Gán SN + sinh QR | Primary |
| 07 | POST | /api/method/assetcore.api.imm04.submit_baseline_checklist | Nộp kết quả đo kiểm IQ/OQ/PQ | Primary |
| 08 | POST | /api/method/assetcore.api.imm04.clear_clinical_hold | Gỡ Clinical Hold (có license) | Primary |
| 09 | POST | /api/method/assetcore.api.imm04.approve_clinical_release | Set board_approver + duyệt release | Primary |
| 10 | POST | /api/method/assetcore.api.imm04.submit_for_approval | Gửi phiếu cho người duyệt | Primary |
| 11 | POST | /api/method/assetcore.api.imm04.approve_pending | Duyệt / Từ chối phiếu chờ | Primary |
| 12 | POST | /api/method/assetcore.api.imm04.report_nonconformance | Tạo NC trên phiếu | Primary |
| 13 | POST | /api/method/assetcore.api.imm04.close_nonconformance | Đóng NC (root cause + action) | Primary |
| 14 | POST | /api/method/assetcore.api.imm04.report_doa | Báo DOA (Dead on Arrival) | Primary |
| 15 | POST | /api/method/assetcore.api.imm04.upload_document | Upload CO/CQ/Manual/License | Primary |
| 16 | GET  | /api/method/assetcore.api.imm04.get_form_context | Chi tiết phiếu + allowed transitions (📱 mobile DETAIL-ENTRY · CR-25b — §21) | Support |
| 17 | GET  | /api/method/assetcore.api.imm04.list_commissioning | Danh sách phiếu + pagination/filter (📱 mobile LIST-ENTRY · CR-25a — §20) | Support |
| 18 | GET  | /api/method/assetcore.api.imm04.list_non_conformances | NC theo phiếu | Support |
| 19 | GET  | /api/method/assetcore.api.imm04.list_my_pending_approvals | Phiếu tôi cần duyệt | Support |
| 20 | GET  | /api/method/assetcore.api.imm04.get_dashboard_stats | KPI dashboard | Support |
| 21 | GET  | /api/method/assetcore.api.imm04.get_gate_status | Trạng thái G01–G06 cho phiếu | Support |
| 22 | GET  | /api/method/assetcore.api.imm04.get_lifecycle_timeline | Timeline `Asset Lifecycle Event` | Support |
| 23 | GET  | /api/method/assetcore.api.imm04.get_commissioning_origin | Truy xuất phiếu nguồn của Asset | Support |
| 24 | GET  | /api/method/assetcore.api.imm04.get_po_details | Auto-fill từ AC Purchase | Support |
| 25 | GET  | /api/method/assetcore.api.imm04.get_barcode_lookup | Tra cứu barcode/QR | Support |
| 26 | GET  | /api/method/assetcore.api.imm04.check_sn_unique | Kiểm tra serial unique (on-blur) | Support |
| 27 | GET  | /api/method/assetcore.api.imm04.search_link | Autocomplete Link fields | Support |
| 28 | GET  | /api/method/assetcore.api.imm04.get_users_by_role | Danh sách user theo Frappe role | Support |
| 29 | GET  | /api/method/assetcore.api.imm04.generate_qr_label | Sinh dữ liệu QR label (in tem) | Support |
| 30 | POST | /api/method/assetcore.api.imm04.generate_internal_qr | (Re)generate internal QR cho phiếu | Support |
| 31 | GET  | /api/method/assetcore.api.imm04.generate_handover_pdf | Sinh URL PDF biên bản bàn giao | Support |
| 32 | POST | /api/method/assetcore.api.imm04.retry_mint_asset | Retry tạo AC Asset sau lỗi mint | Internal |
| 33 | POST | /api/method/assetcore.api.imm04.cancel_commissioning | Hủy phiếu (Submitted) | Internal |
| 34 | POST | /api/method/assetcore.api.imm04.delete_commissioning | Xóa phiếu (Draft only) | Internal |

> Schema chi tiết (request/response/errors/side effects) chỉ document cho 6 endpoint Primary trọng yếu ở §2 bên dưới (`get_form_context`, `create_commissioning`, `submit_commissioning`, `assign_identification`, `submit_baseline_checklist`, `generate_qr_label`, `get_dashboard_stats`). Các endpoint còn lại tuân thủ envelope chuẩn AssetCore (§1.1–1.4) và mapping role/permission ở §2 / `04_Backend_Design.md`.

---

## 1. Quy ước chung

### 1.1. Response success — format chuẩn AssetCore

AssetCore dùng **envelope custom** thay vì Frappe `message` default — wrap qua helper `_ok(data)`:

```jsonc
{
  "success": true,
  "data": <payload tùy endpoint>
}
```

FE đọc `response.data.data` (axios + Frappe outer wrap thêm `message`, FE helper tự strip).

**HTTP status:** Frappe luôn trả **HTTP 200** khi service không raise exception ngoài kiểm soát. Phân biệt success/error qua field `success` trong body.

### 1.2. Response error — format chuẩn

```jsonc
{
  "success": false,
  "error": "Thiết bị đã ngưng sử dụng.",   // tiếng Việt cho FE hiển thị
  "code": "BAD_STATE",                      // ErrorCode enum
  "fields": {                               // (optional) field-level errors
    "vendor_serial_no": "Serial đã được gán cho phiếu ACC-..."
  }
}
```

### 1.3. Error code catalog

| Code | HTTP gợi ý | Khi nào |
|---|---|---|
| `NOT_FOUND` | 404 | Phiếu / PO / NC không tồn tại |
| `FORBIDDEN` | 403 | Không có quyền (role check) |
| `UNAUTHORIZED` | 401 | Chưa đăng nhập |
| `VALIDATION` | 400 | Input validation fail (VR-xx) |
| `BUSINESS_RULE` | 422 | Vi phạm rule nghiệp vụ |
| `BAD_STATE` | 422 | State machine fail (sai workflow state) |
| `CONFLICT` | 409 | Concurrent modify |
| `DUPLICATE` | 409 | Serial trùng (VR-01) |
| `INVALID_PARAMS` | 400 | JSON parse fail |
| `INTERNAL` | 500 | Lỗi hệ thống |

**Codes riêng IMM-04 (cũ, cần map về standard):**

| Code cũ | Map về | Khi nào |
|---|---|---|
| `WRONG_STATE` | `BAD_STATE` | Submit khi state ≠ Clinical Release |
| `TRANSITION_NOT_ALLOWED` | `FORBIDDEN` | Action không trong allowed transitions |
| `OPEN_NC` | `BUSINESS_RULE` | Còn NC chưa đóng (G05) |
| `QR_NOT_GENERATED` | `BAD_STATE` | Phiếu chưa có internal_tag_qr |
| `PERMISSION_DENIED` | `FORBIDDEN` | Không đủ role |
| `VALIDATION_ERROR` | `VALIDATION` | VR-xx failure |
| `SYSTEM_ERROR` | `INTERNAL` | Exception không xác định |

### 1.4. Mapping FE ↔ BE error code

| BE (ErrorCode) | FE (ErrorCode) |
|---|---|
| `VALIDATION` | `VALIDATION_ERROR` |
| `BUSINESS_RULE` | `BUSINESS_RULE_VIOLATION` |
| `NOT_FOUND` | `NOT_FOUND` |
| `FORBIDDEN` | `FORBIDDEN` |
| `BAD_STATE` | `BAD_STATE` |
| `INTERNAL` | `INTERNAL_ERROR` |
| `INVALID_PARAMS` | `INVALID_PARAMS` |

### 1.5. Type definitions

> Source of truth: `frontend/src/types/imm04.ts` và `frontend/src/api/imm04.ts`.

```ts
// frontend/src/types/imm04.ts (actual — trích dẫn chính)

export type WorkflowState =
  | 'Draft'
  | 'Pending Doc Verify'
  | 'To Be Installed'
  | 'Installing'
  | 'Identification'
  | 'Initial Inspection'
  | 'Non Conformance'
  | 'Clinical Hold'
  | 'Re Inspection'
  | 'Clinical Release'
  | 'Return To Vendor'

export type RiskClass = 'A' | 'B' | 'C' | 'D' | 'Radiation' | ''

export interface CommissioningDoc {
  name: string
  workflow_state: WorkflowState
  docstatus: 0 | 1 | 2
  po_reference: string
  master_item: string             // IMM Device Model (PK)
  master_item_name?: string       // display name resolved by BE
  vendor: string                  // AC Supplier (PK)
  vendor_name?: string
  clinical_dept: string           // AC Department (PK)
  clinical_dept_name?: string
  vendor_serial_no: string
  internal_tag_qr: string
  risk_class: RiskClass
  is_radiation_device: 0 | 1
  board_approver: string
  final_asset: string
  baseline_tests: BaselineTest[]
  commissioning_documents: DocumentRecord[]
  lifecycle_events: LifecycleEvent[]
  allowed_transitions: WorkflowTransition[]
  is_locked: boolean
}

export interface WorkflowTransition {
  action: string
  next_state: WorkflowState
  allowed_role: string
}

// transition_state — BR-04-12 (04 §5.4). board_approver optional; CHỈ honor khi
// next_state của `action` == 'Clinical Release', ngược lại bị bỏ qua (backward-compat).
export interface TransitionStateRequest {
  name: string
  action: string
  board_approver?: string          // reqd khi transition CR-bound; 4-eyes SoD
}

export interface TransitionResult {
  name: string
  action_applied: string
  new_state: WorkflowState
  docstatus: 0 | 1 | 2
  final_asset: string
  board_approver: string           // additive — persist sau CR-bound transition
}
```

> ⚠️ `allowed_transitions` là **bề mặt CTA nghiệm thu** — sinh server-side bởi `_get_workflow_transitions()` (`services/imm04.py:667`), role-filtered live. Nếu workflow bị rename / hằng-lookup `"IMM-04 Workflow"` sai / `_DT` drift → service `return []` **câm** → FE mất toàn bộ nút nghiệm thu. Bất biến khoá lỗ này (INV-04-WF-1..4) đặc tả ở `04 §3.1` + BR-04-24 + ADR-IMM-04-01, guard `TestImm04WorkflowSurfaceGuard` (`07 §III.4a`). FE **KHÔNG** hardcode nút theo `workflow_state`; luôn render CTA từ `allowed_transitions` server-driven (GATE-8 / `assetcore-fe`).

**Lưu ý:** Workflow state values dùng **space** (`Pending Doc Verify`, `Clinical Release`, ...) — đồng bộ giữa workflow fixture, service constants, và TypeScript enum. Tech debt naming cũ (underscore) đã được resolve.

### 1.6. Pagination & Datetime

- Pagination: `page=1` (1-based), `page_size=20` (max 100)
- Response pagination shape: `{items: [...], pagination: {page, page_size, total, total_pages}}`
- Datetime: ISO 8601 UTC string (`"2026-04-18T09:00:00Z"`)

---

## 2. Endpoint chi tiết

### 1. get_form_context — Chi tiết phiếu đầy đủ

| Mục | Giá trị |
|---|---|
| Method | GET |
| Path | `/api/method/assetcore.api.imm04.get_form_context` |
| Role | All authenticated (read permission trên Asset Commissioning) |
| Idempotent | Yes |
| Type Request | `{name: string}` |
| Type Response | `CommissioningDetail` |

**Request:**
```jsonc
// Query params
?name=ACC-26-04-00001
```

**Response success:**
```jsonc
{
  "success": true,
  "data": {
    "name": "ACC-26-04-00001",
    "workflow_state": "Identification",
    "docstatus": 0,
    "po_reference": "PO-2026-00023",
    "master_item": "ITM-XRAY-001",
    "vendor": "Philips Healthcare VN",
    "clinical_dept": "Khoa CĐHA",
    "expected_installation_date": "2026-04-20",
    "vendor_serial_no": "PHI-SN98765",
    "internal_tag_qr": "BV-CDHA-2026-0001",
    "is_radiation_device": 1,
    "risk_class": "C",
    "final_asset": null,
    "baseline_tests": [
      {"idx": 1, "parameter": "Leakage Current", "test_result": "Pass", "measured_val": 0.08, "unit": "mA", "is_critical": true}
    ],
    "commissioning_documents": [
      {"idx": 1, "doc_type": "CO", "is_mandatory": 1, "status": "Received", "file_url": "/private/files/co.pdf"}
    ],
    "lifecycle_events": [
      {"event_type": "Identification", "from_status": "Installing", "to_status": "Identification", "actor": "biomed@hospital.vn", "event_timestamp": "2026-04-18T09:00:00Z"}
    ],
    "allowed_transitions": [
      {"action": "Bắt đầu kiểm tra", "next_state": "Initial Inspection", "allowed_role": "Biomed Engineer"}
    ],
    "is_locked": false
  }
}
```

**Response error:**
```jsonc
{
  "success": false,
  "error": "Không tìm thấy phiếu ACC-26-04-99999.",
  "code": "NOT_FOUND"
}
```

**Side effects:** Không có

**Curl ví dụ:**
```bash
curl 'http://site/api/method/assetcore.api.imm04.get_form_context?name=ACC-26-04-00001' \
  -H 'Authorization: token key:secret'
```

---

### 3. create_commissioning — Tạo phiếu mới

| Mục | Giá trị |
|---|---|
| Method | POST |
| Path | `/api/method/assetcore.api.imm04.create_commissioning` |
| Role | HTM Technician / Biomed Engineer / CMMS Admin |
| Idempotent | No |
| Type Request | `CreateCommissioningRequest` |
| Type Response | `CommissioningCreated` |
| Liên kết US | US-04-01 |

**Request:**
```jsonc
{
  "data": {
    "po_reference": "PO-2026-00023",   // required
    "master_item": "ITM-XRAY-001",     // required
    "vendor": "Philips Healthcare VN", // required
    "clinical_dept": "Khoa CĐHA",      // required
    "expected_installation_date": "2026-04-20"  // required
  }
}
```

| Trường | Type | Required | Validation |
|---|---|---|---|
| `po_reference` | string | ✓ | PO tồn tại |
| `master_item` | string | ✓ | Item exists |
| `vendor` | string | ✓ | Supplier exists |
| `clinical_dept` | string | ✓ | Department exists |
| `expected_installation_date` | date ISO | ✓ | date string |

**Response success:**
```jsonc
{
  "success": true,
  "data": {
    "name": "ACC-26-04-00001",
    "workflow_state": "Draft",
    "message": "Phiếu ACC-26-04-00001 đã được tạo thành công"
  }
}
```

**Errors có thể:**
| Code (BE) | Code (FE) | Khi nào |
|---|---|---|
| `VALIDATION` | `VALIDATION_ERROR` | Thiếu field bắt buộc |
| `NOT_FOUND` | `NOT_FOUND` | PO không tồn tại |
| `INVALID_PARAMS` | `INVALID_PARAMS` | `data` không phải JSON hợp lệ |
| `INTERNAL` | `INTERNAL_ERROR` | Insert exception |

**Side effects:**
- Tạo `Asset Commissioning` record (Draft)
- Populate `commissioning_documents` với CO, CQ, Manual + License nếu risk_class C/D/Radiation
- Log lifecycle event `commissioning_created`

**Curl:**
```bash
curl -X POST 'http://site/api/method/assetcore.api.imm04.create_commissioning' \
  -H 'Authorization: token key:secret' \
  -H 'Content-Type: application/json' \
  -d '{"data": {"po_reference":"PO-2026-00023","master_item":"ITM-XRAY-001","vendor":"Philips","clinical_dept":"Khoa CĐHA","expected_installation_date":"2026-04-20"}}'
```

---

### 15. transition_state — Workflow transition (+ cấp `board_approver` 4-mắt khi CR-bound · BR-04-12, 04 §5.4)

> Catalog #15 (§0). Đặt cạnh `submit_commissioning` (#6) theo trình tự nghiệp vụ: transition → Clinical Release → Submit.

| Mục | Giá trị |
|---|---|
| Method | POST |
| Path | `/api/method/assetcore.api.imm04.transition_state` |
| Role | Theo `Workflow Transition.allowed` của state hiện tại (server-driven; `allowed_transitions[]`) |
| Idempotent | No |
| Type Response | `TransitionResult` |

**Signature:** `transition_state(name: str, action: str, board_approver: str = "")`

`board_approver` **optional**, **CHỈ có tác dụng** khi `action` là transition có `next_state == "Clinical Release"` (3 cạnh: `Phê duyệt phát hành` từ Initial Inspection · `Gỡ giữ lâm sàng` từ Clinical Hold · `Phê duyệt sau tái kiểm` từ Re Inspection). Với mọi action khác → tham số **bị bỏ qua** (backward-compat, không ghi vào field nào).

**Request (CR-bound — gỡ deadlock):**
```jsonc
{"name": "ACC-26-04-00001", "action": "Phê duyệt phát hành", "board_approver": "director@hospital.vn"}
```

**Request (non-CR — param bỏ qua):**
```jsonc
{"name": "ACC-26-04-00001", "action": "Bắt đầu lắp đặt"}
```

**Response success:**
```jsonc
{
  "success": true,
  "data": {
    "name": "ACC-26-04-00001",
    "action_applied": "Phê duyệt phát hành",
    "new_state": "Clinical Release",
    "docstatus": 0,
    "final_asset": "AC-ASSET-2026-00001",
    "board_approver": "director@hospital.vn"
  }
}
```

**Response error — thiếu người duyệt (Decision-B, HTTP-200 `success:false`, KHÔNG raw 417):**
```jsonc
{
  "success": false,
  "error": "Gate G06: Phải chọn Người Phê duyệt Ban Giám đốc (board_approver) trước khi Phát hành Lâm sàng.",
  "code": "VALIDATION",
  "http_status": 422,
  "message_code": "IMM04-GATE-G06-APPROVER",
  "context": {"missing": ["board_approver"]},
  "severity": "warning",
  "title": "Chưa chọn người phê duyệt Ban Giám đốc",
  "action_hint": "Chọn người phê duyệt Ban Giám đốc rồi gửi lại yêu cầu phát hành."
}
```

**Response error — vi phạm 4-mắt (NĐ98 SoD):**
```jsonc
{
  "success": false,
  "error": "Separation-of-duties (4-eyes): bạn (...) đã ký ở vai trò `clinical_head` trên phiếu này; không thể đồng thời ký thêm vai khác.",
  "code": "FORBIDDEN",
  "http_status": 403
}
```
→ phiếu **KHÔNG đổi state**, `board_approver` **KHÔNG bị ghi**.

**Errors có thể:**
| Code (BE) | Code (FE) | Khi nào |
|---|---|---|
| `NOT_FOUND` | `NOT_FOUND` | Phiếu không tồn tại |
| `FORBIDDEN` | `FORBIDDEN` | (a) thiếu quyền `write`; (b) 4-eyes: `board_approver` trùng `owner`/`clinical_head`/`qa_officer`/`pending_approver` (`assert_distinct_signers`) |
| `INVALID_PARAMS` | `VALIDATION_ERROR` | `action` không hợp lệ từ state hiện tại |
| `VALIDATION` | `VALIDATION_ERROR` | **CR-bound thiếu `board_approver`** (`message_code=IMM04-GATE-G06-APPROVER`, `context.missing=['board_approver']`) — Decision-B, thay cho 417 legacy |

**Side effects (CR-bound):**
- Ghi `board_approver` (khi caller cấp mới) TRƯỚC `apply_workflow` → gate G06 save-time pass cùng lượt.
- `apply_workflow` → `workflow_state = Clinical Release`.
- Stamp `commissioning_date` (BR-04-11, idempotent).
- Auto-mint `AC Asset` (`create_ac_asset`, idempotent theo `final_asset` — best-effort, không chặn transition nếu lỗi).

**Boundaries:** xem 04 §5.4. Điểm chốt cho FE: đọc `allowed_transitions[]` từ `CommissioningDetail` (GATE-8, server-driven CTA) — với transition CR-bound, thu `board_approver` (dùng `ApproverSelect context="user"` / `list_assignable_users`, **KHÔNG** `SmartSelect doctype="User"` trần) rồi truyền vào `transition_state`; nếu `message_code == IMM04-GATE-G06-APPROVER` → highlight control người-duyệt (đọc `context.missing`).

**Curl:**
```bash
curl -X POST 'http://site/api/method/assetcore.api.imm04.transition_state' \
  -H 'Authorization: token key:secret' \
  -H 'Content-Type: application/json' \
  -d '{"name":"ACC-26-04-00001","action":"Phê duyệt phát hành","board_approver":"director@hospital.vn"}'
```

> ⚠️ Mobile OAS (`docs/mobile/openapi/assetcore-mobile.openapi.yaml`) **KHÔNG** expose `transition_state` như write-op (IMM-04 mobile hiện chỉ read: `list`/`detail` + `allowed_transitions[]`). Curate write-op cho mobile = **[ROADMAP]** mobile-BE round riêng (giữ op-count baseline; `test_mobile_oas` KHÔNG đụng vòng này).

---

### 6. submit_commissioning — Submit phiếu

| Mục | Giá trị |
|---|---|
| Method | POST |
| Path | `/api/method/assetcore.api.imm04.submit_commissioning` |
| Role | Workshop Head / VP Block2 |
| Idempotent | No |
| Type Response | `SubmitResult` |

**Request:**
```jsonc
{"name": "ACC-26-04-00001"}
```

**Response success:**
```jsonc
{
  "success": true,
  "data": {
    "name": "ACC-26-04-00001",
    "docstatus": 1,
    "final_asset": "ACC-ASS-2026-00001",
    "message": "Phiếu đã được Submit. Tài sản ACC-ASS-2026-00001 đã được tạo."
  }
}
```

**Response error:**
```jsonc
{
  "success": false,
  "error": "Phiếu chưa ở trạng thái Clinical Release.",
  "code": "BAD_STATE"
}
```

**Errors có thể:**
| Code (BE) | Code (FE) | Khi nào |
|---|---|---|
| `FORBIDDEN` | `FORBIDDEN` | User không có role Workshop Head / VP Block2 |
| `BAD_STATE` | `BAD_STATE` | workflow_state ≠ Clinical Release |
| `VALIDATION` | `VALIDATION_ERROR` | G05 (Open NC tồn tại) / G06 (thiếu board_approver) / GW-2 |
| `CONFLICT` | `CONFLICT` | Phiếu đã submit (docstatus=1) |

**Side effects:**
- `docstatus = 1`
- **Stamp `commissioning_date = nowdate()` nếu còn NULL** (BR-04-11 — `_stamp_commissioning_date`; idempotent, không ghi đè). Bảo hiểm cho phiếu vào Clinical Release từ trước fix mà chưa stamp.
- Tạo `Asset` record (`final_asset`)
- Auto-import hồ sơ sang IMM-05 (`create_initial_document_set`)
- **`on_submit` doc_events (`hooks.py:194-197`) phát lịch bảo trì + hiệu chuẩn** — `imm08.create_pm_schedule_from_commissioning` (PM schedule) + `imm11.create_calibration_schedule_from_commissioning` (Calibration schedule). Đây là mắt xích `Commissioning → Operation`: sau gỡ deadlock (§5.4 / BR-04-12), phiếu tới được `Clinical Release` → Submit → 2 lịch được phát ⇒ mạch `Needs→Operation` không còn nút chết.
- Publish realtime `imm04_asset_released`
- Notify Purchase User role

> Side-effect **stamp `commissioning_date`** (BR-04-11) áp dụng cho CẢ 3 write-path vào Clinical Release: `transition_state` (action → Clinical Release), `submit_commissioning` (trên), `approve_clinical_release`. Idempotent — chỉ path ĐẦU TIÊN chạm Clinical Release ghi ngày; path sau no-op. `approve_clinical_release` đổi return `commissioning_date` từ `str(doc.commissioning_date or nowdate())` → `str(doc.commissioning_date)` (sau stamp luôn non-NULL).

**Curl:**
```bash
curl -X POST 'http://site/api/method/assetcore.api.imm04.submit_commissioning' \
  -H 'Authorization: token key:secret' \
  -H 'Content-Type: application/json' \
  -d '{"name": "ACC-26-04-00001"}'
```

---

### 8. assign_identification — Gán Serial + sinh QR

| Mục | Giá trị |
|---|---|
| Method | POST |
| Path | `/api/method/assetcore.api.imm04.assign_identification` |
| Role | Biomed Engineer / CMMS Admin |
| Idempotent | Yes (idempotent nếu SN giống) |
| Type Request | `AssignIdentificationRequest` |
| Type Response | `IdentificationResult` |
| Liên kết US | US-04-02 |

**Request:**
```jsonc
{
  "name": "ACC-26-04-00001",
  "vendor_serial_no": "PHI-SN98765",     // required, UNIQUE (VR-01)
  "internal_tag_qr": "",                  // optional; auto-sinh nếu rỗng
  "custom_moh_code": "QLSP-2026-001"     // optional
}
```

**Response success:**
```jsonc
{
  "success": true,
  "data": {
    "name": "ACC-26-04-00001",
    "vendor_serial_no": "PHI-SN98765",
    "internal_tag_qr": "BV-CDHA-2026-0001"
  }
}
```

**Errors có thể:**
| Code (BE) | Code (FE) | Khi nào |
|---|---|---|
| `VALIDATION` | `VALIDATION_ERROR` | VR-01 serial trùng |
| `BAD_STATE` | `BAD_STATE` | State ≠ Identification |
| `NOT_FOUND` | `NOT_FOUND` | Phiếu không tồn tại |

**Side effects:**
- Set `vendor_serial_no`, `internal_tag_qr`, `custom_moh_code`
- Log lifecycle event `identification`

---

### 10. submit_baseline_checklist — Nộp kết quả đo kiểm

| Mục | Giá trị |
|---|---|
| Method | POST |
| Path | `/api/method/assetcore.api.imm04.submit_baseline_checklist` |
| Role | Biomed Engineer / CMMS Admin |
| Idempotent | No |
| Liên kết US | US-04-04 |

**Request:**
```jsonc
{
  "name": "ACC-26-04-00001",
  "results": [
    {"parameter": "Leakage Current", "measured_val": 0.08, "test_result": "Pass", "fail_note": ""},
    {"parameter": "Earth Resistance", "measured_val": 0.12, "test_result": "Fail", "fail_note": "Vượt ngưỡng 0.1 Ω"}
  ]
}
```

> **Ngữ nghĩa (BR-04-04 · silent-completion guard — xem `04_Backend_Design.md §5.3`, ADR-IMM-04-02):**
> - **UPSERT-by-parameter:** `result` cho parameter **chưa có** row trong `baseline_tests` → BE **append** row mới + persist (phiếu tạo không pre-seed child vẫn ghi được đo hiện trường). KHÔNG drop câm.
> - **`tests_recorded`** = số row THỰC ghi `test_result` (Pass/Fail/N/A) sau upsert — KHÔNG `len(results)` mù. `overall_result='Pass'` ⟺ `tests_recorded > 0`.
> - **0 phép đo** (`results` rỗng AND `baseline_tests` rỗng, hoặc 0 row có `test_result`) → **KHÔNG auto-Pass**; trả Error `VALIDATION` (BR-04-04a). `overall_inspection_result` KHÔNG set `Pass`.

**Response success (all pass, N phép đo):**
```jsonc
{
  "success": true,
  "data": {
    "name": "ACC-26-04-00001",
    "overall_result": "Pass",
    "tests_recorded": 2,
    "clinical_hold_required": true
  }
}
```

**Response error (có Fail — BR-04-04c):**
```jsonc
{
  "success": false,
  "error": "BR-04-04: Thông số sau không đạt: Earth Resistance. Phiếu phải chuyển về Re Inspection.",
  "code": "VALIDATION"
}
```

**Response error (0 phép đo — BR-04-04a, chặn Pass-giả):**
```jsonc
{
  "success": false,
  "error": "BR-04-04: Không thể nghiệm thu — chưa có phép đo baseline nào. Nhập kết quả đo trước khi nộp.",
  "code": "VALIDATION"
}
```

---

### 13. generate_qr_label — Sinh dữ liệu QR (dedup deep-link — vòng 13 / ADR-001 §D6.1)

| Mục | Giá trị |
|---|---|
| Method | GET |
| Path | `/api/method/assetcore.api.imm04.generate_qr_label` |
| Role | All (gate `has_permission("Asset Commissioning","read")`) |
| Idempotent | Yes (`qr_url` dựng qua `ensure_asset_qr_token` idempotent — KHÔNG double-emit) |

**Request:** `?name=ACC-26-04-00001`

**Response success — phiếu ĐÃ có `final_asset` (đã Clinical Release / mint asset):**
```jsonc
{
  "success": true,
  "data": {
    "qr_value": "BV-CDHA-2026-0001",          // GIỮ — fallback + tương thích nhãn cũ + scanner-wedge
    "qr_url": "https://assetcore.benhvien.vn/a/Xk7p2Qm9_aZ4Lr8sT0wVcQ",  // MỚI: deep-link tuyệt đối /a/<token> (enumeration-safe) — ẢNH QR mã hoá field này
    "label": {
      "title": "ASSETCORE — NHÃN THIẾT BỊ",
      "commissioning_id": "ACC-26-04-00001",
      "internal_qr": "BV-CDHA-2026-0001",
      "vendor_serial": "PHI-SN98765",
      "model": "ITM-XRAY-001",
      "vendor": "Philips Healthcare VN",
      "dept": "Khoa CĐHA",
      "moh_code": "QLSP-2026-001",
      "installation_date": "2026-04-18T14:30:00Z",
      "status": "Clinical Release",
      "asset_id": "AC-ASSET-2026-00123",
      "print_date": "2026-04-18"
    },
    "docs_url": "/documents/asset/AC-ASSET-2026-00123"   // GIỮ — không trong scope vòng 13
  }
}
```

**Response success — phiếu CHƯA có `final_asset` (edge):**
```jsonc
{
  "success": true,
  "data": {
    "qr_value": "BV-CDHA-2026-0001",
    "qr_url": null,            // KHÔNG sinh token, KHÔNG throw — nhãn fallback dùng commissioning_id; ẢNH QR fallback mã hoá qr_value
    "label": { /* ... asset_id: "Chưa có", status: "Identification" ... */ },
    "docs_url": null
  }
}
```

**Delta vòng 13 (ADR-001 §D6.1 — RC dedup):**
- **`+qr_url`** — chuỗi tuyệt đối `/a/<token>` khi `final_asset` có; `null` khi chưa mint asset. Dựng qua **tái dùng** `services.imm00.ensure_asset_qr_token(final_asset)` + `_build_qr_url(token)` (1 helper duy nhất — KHÔNG copy logic sinh token/URL).
- **`−scan_url`** — field `scan_url=/app/asset-commissioning/<name>` (desk-login) **BỎ HẲN** khỏi contract. FE đọc `qr_url`.
- ẢNH QR (FE `QRLabel.vue`) mã hoá `qr_url` khi có (deep-link → camera điện thoại mở `AssetScanInfo` A6); fallback `qr_value` (tag) CHỈ khi `qr_url` rỗng → KHÔNG còn chuỗi tag tuần tự `BV-DEPT-YYYY-SEQ` quét-được.
- `docs_url` GIỮ nguyên.
- **Lifecycle:** `ensure_asset_qr_token` idempotent → KHÔNG double-emit `qr_generated` (đã emit lần đầu ở A1/backfill). `generate_qr_label` KHÔNG emit event mới.

**Errors:**
- `BAD_STATE` (`QR_NOT_GENERATED`) nếu `internal_tag_qr` chưa được sinh (phiếu chưa qua Identification).
- `FORBIDDEN` nếu user không có quyền read trên `Asset Commissioning`.
- `NOT_FOUND` nếu `name` không tồn tại.
- Edge `final_asset` rỗng KHÔNG phải lỗi → `qr_url=null` (success).

---

### 18. get_dashboard_stats — KPI dashboard

| Mục | Giá trị |
|---|---|
| Method | GET |
| Path | `/api/method/assetcore.api.imm04.get_dashboard_stats` |
| Role | HTM Technician+ (không Vendor Engineer) |
| Idempotent | Yes |

**`kpis.overdue_sla`** = `frappe.db.count("Asset Commissioning", overdue_commissioning_filter())` (BR-04-10). Anchor = `reception_date` (KHÔNG `expected_installation_date`); ngưỡng `OVERDUE_DAYS=30`. Giá trị này **bằng đúng** `pagination.total` của `list_commissioning({overdue:1})` → card click drill được.

**`kpis.released_this_month`** (BR-04-11, label FE "Bàn giao tháng này") = `frappe.db.count("Asset Commissioning", {workflow_state: Clinical Release, docstatus: 1, commissioning_date: ("between", [first_day_of_month, today])})`. Anchor = `commissioning_date` (NGÀY vào Clinical Release, được stamp bởi `_stamp_commissioning_date` ở 3 write-path) — **KHÔNG** `modified`. Hệ quả fix: phiếu Released tháng-trước bị edit (note/doc) tháng này KHÔNG còn bị đếm lại; phiếu legacy `commissioning_date` NULL bị `BETWEEN` loại tự nhiên (không crash, không over/under-count). Type bất biến `number`; FE label bất biến. Các KPI còn lại (`pending_count` / `hold_count` / `open_nc_count`) GIỮ NGUYÊN định nghĩa.

**Response success:**
```jsonc
{
  "success": true,
  "data": {
    "kpis": {
      "pending_count": 12,
      "hold_count": 2,
      "open_nc_count": 3,
      "released_this_month": 8, // count theo commissioning_date ∈ tháng (BR-04-11, KHÔNG modified)
      "overdue_sla": 1        // == pagination.total của list_commissioning({overdue:1})
    },
    "states_breakdown": [
      {"workflow_state": "Identification", "count": 5},
      {"workflow_state": "Initial Inspection", "count": 4},
      {"workflow_state": "Clinical Hold", "count": 2}
    ],
    "recent_list": [
      {"name": "ACC-26-04-00001", "workflow_state": "Identification", "master_item": "ITM-XRAY-001", "modified": "2026-04-18T10:00:00Z"}
    ]
  }
}
```

---

### 19. get_commissioning_origin — Nguồn gốc thiết bị (📱 mobile asset-detail sub-tab #4 · CR-11d)

| Mục | Giá trị |
|---|---|
| Method | GET |
| Path | `/api/method/assetcore.api.imm04.get_commissioning_origin` |
| Handler | `api/imm04.py:315` → `_handle(svc.get_commissioning_origin, asset_name)` (Decision-B) |
| Service | `services/imm04.py:1972-1997` (SoT payload) |
| Role | Bare `@whitelist` — permission-aware qua `_handle`; guest → dispatcher-403. KHÔNG `rbac.require` in-handler |
| Idempotent | Yes (read-only, KHÔNG audit) |

Trả **nguồn-gốc/xuất-xứ** của 1 thiết bị (`AC Asset`) cho tab "Nguồn gốc thiết bị" màn Chi tiết thiết bị mobile (sau quét QR) — truy-vết provenance **NĐ98/2021** (PO gốc → NCC → model → tiếp-nhận/lắp-đặt).

- **Param:** `asset_name` (query, **required**, string — positional no-default @`:1972`; service `raise ServiceError(NOT_FOUND)` khi asset∄ @`:1975` → Error envelope HTTP-200 `http_status 404`).
- **Payload** `{asset, commissioning}`: key `commissioning` **LUÔN present**, value `null` khi asset chưa gắn `commissioning_ref` (@`:1979`) HOẶC commissioning-doc biến-mất (@`:1989`); ngược lại = record 12 field = `get_value(Asset Commissioning, [name, workflow_state, po_reference, vendor, master_item, reception_date, commissioning_date, vendor_serial_no, purchase_price, warranty_expiry_date, commissioned_by])` @`:1983-1985` + `transferred_doc_count` = `frappe.db.count("Asset Document", {asset_ref, source_commissioning})` @`:1992-1996`.
- **⚠️ `purchase_price` = FINANCIAL** — render theo persona ở FE (gate quyền xem giá), curate nguyên trong contract.

**Response success:**
```jsonc
{
  "success": true,
  "data": {
    "asset": "AC-ASSET-2026-00001",
    "commissioning": {              // null khi asset chưa có hồ-sơ nghiệm-thu/lắp-đặt
      "name": "ACC-26-04-00001",
      "workflow_state": "Clinical Release",
      "po_reference": "PO-2026-0007",
      "vendor": "SUP-0003", "master_item": "ITM-XRAY-001",
      "reception_date": "2026-03-01", "commissioning_date": "2026-03-15",
      "vendor_serial_no": "SN-XR-88231",
      "purchase_price": 1250000000,      // FINANCIAL — persona-gate FE
      "warranty_expiry_date": "2028-03-15", "commissioned_by": "kts@hospital.vn",
      "transferred_doc_count": 4         // số Asset Document đã chuyển-giao (→ imm-05)
    }
  }
}
```

> 📱 **Mobile OAS contract:** curated vào `docs/mobile/openapi/assetcore-mobile.openapi.yaml` (opId `getAssetCommissioningOrigin`, 200 = oneOf `[AssetCommissioningOriginEnvelope, Error]`, wrapper `AssetCommissioningOrigin` + nested `CommissioningOriginRecord`) — CONTRACT-ONLY (handler+service ĐÃ LIVE, 0 `.py`/reload/migrate). Quyết định + schema đầy đủ: [`ADR-MOBILE-041`](../mobile/ADR-MOBILE-041.md) + [`docs/mobile/04-api-contract.md §8.43`](../mobile/04-api-contract.md). `transferred_doc_count` nguồn từ DocType `Asset Document` (IMM-05) — xem `docs/imm-05` cross-ref.

---

### 20. list_commissioning — Mobile LIST-ENTRY màn "Tiếp nhận & Nghiệm thu hiện trường" (📱 Trục B · CR-25a · MỞ NHÁNH IMM-04 F6)

**Actor:** KTV / Commissioning User (mobile) · **Verb:** GET · **Handler:** `assetcore.api.imm04.list_commissioning` (`api/imm04.py:24`) → `svc.list_commissioning` (`services/imm04.py:831`).
**Deliverable = curate endpoint LIST-ENTRY vào OAS mirror.** Đây là endpoint list phiếu `Asset Commissioning` — màn khởi động luồng field-tech (chọn phiếu để tiếp nhận & nghiệm thu). CONTRACT-ONLY: **backend ĐÃ LIVE** (0 `.py` runtime change / 0 reload / 0 migrate). Curate là **pure-YAML** vào `docs/mobile/openapi/assetcore-mobile.openapi.yaml` + đồng bộ test guard.

> ⚠️ **KHÔNG nhầm** với `getAssetCommissioningOrigin` (§19 — nguồn: `imm04.get_commissioning_origin`, sub-tab Asset Detail #4). Đây là **nguồn khác** (`imm04.list_commissioning`), tag/schema/opId riêng biệt (AC5 blast-radius = 0 với AssetCommissioningOrigin).

#### 20.1. Envelope — Asset-style `data.items[]` (KHÁC PM/calib `data.data[]`)

Service trả `{"items": records, "pagination": pg}` (`services/imm04.py:911`); `helpers._ok(...)` wrap → wire body:

```jsonc
{
  "success": true,
  "data": {
    "items":      [ /* CommissioningListItem × page_size */ ],
    "pagination": { "page":1, "page_size":20, "total":N, "total_pages":T, "offset":0 }
  }
}
```

Rows nằm dưới **`data.items[]`** (mirror `AssetListEnvelope` / `IncidentListEnvelope` — KHÁC `PmWorkOrderListEnvelope`/`CalibrationListEnvelope` dùng `data.data[]`).

> **⚠️ Self-Correction (ambiguity resolve — BA quyết định, đọc kỹ trước khi curate):** AC3 mô tả `CommissioningListPage` là "items=array + pagination=$ref" — đây mô tả **nội dung của khối `data`**, KHÔNG phải toàn bộ schema. Schema `CommissioningListPage` phải là **FULL success envelope** `{success: enum[true], data: {items[], pagination}}` — **mirror `AssetListEnvelope`** (`yaml:2059`) — vì live `helpers._ok` wrap thêm lớp `{success, data}` quanh `{items, pagination}` (`services/imm04.py:911`). Nếu curate `CommissioningListPage = {items, pagination}` TRẦN (thiếu wrapper `success`/`data`) → **SAI live-wire parity** (200-body thật có `success`+`data`). Đặt tên `...ListPage` (thay `...ListEnvelope`) là chủ ý AC, nhưng **vai trò = envelope**.

#### 20.2. Schemas cần curate (2 schema MỚI, closed)

**(a) `CommissioningListItem`** — `additionalProperties: false`, **ĐÚNG 20 property** = 13 `_LIST_FIELDS` (`services/imm04.py:117-123`) + 7 enrich (`services/imm04.py:902-907`). `required: [name]` (mirror `AssetListItem` — chỉ PK bắt buộc, còn lại optional). **KHÔNG có field Check int-0/1** (`is_radiation_device`/`doa_incident` chỉ là filter-key, KHÔNG ∈ `_LIST_FIELDS` → list-item **MIỄN CR-01 coercion**).

| # | Property | Type | Ghi chú (grounding) |
|---|---|---|---|
| 1 | `name` | string | PK phiếu (naming ACC-…). **required.** `_LIST_FIELDS` |
| 2 | `workflow_state` | string | Trạng thái workflow (Select nhiều giá trị → **string KHÔNG enum cứng**, mirror `AssetListItem.lifecycle_status`, tránh codegen vỡ khi thêm state) |
| 3 | `docstatus` | integer, `enum:[0,1,2]` | Frappe docstatus (0 Draft·1 Submitted·2 Cancelled). **KHÔNG phải Check** → int-enum hợp lệ, KHÔNG dính int-vs-bool trap. Default filter loại `2` (`!=2`) nhưng client có thể lọc `docstatus:2` → giữ `[0,1,2]` |
| 4 | `po_reference` | string, nullable | Link `AC Purchase` |
| 5 | `master_item` | string, nullable | Link `IMM Device Model` |
| 6 | `vendor` | string, nullable | Link `AC Supplier` |
| 7 | `clinical_dept` | string, nullable | Link `AC Department` |
| 8 | `expected_installation_date` | string, `format:date`, nullable | Ngày lắp đặt dự kiến |
| 9 | `installation_date` | string, `format:date`, nullable | Ngày lắp đặt thực tế |
| 10 | `vendor_serial_no` | string, nullable | Serial NCC |
| 11 | `internal_tag_qr` | string, nullable | Mã QR nội bộ |
| 12 | `final_asset` | string, nullable | Link `AC Asset` (asset đã mint) |
| 13 | `modified` | string | Frappe Datetime `'yyyy-MM-dd HH:mm:ss'` — **KHÔNG `format:date-time`** (space-sep ≠ RFC3339; mirror `AssetDowntimeLog.start_time`) |
| 14 | `master_item_name` | string | enrich `IMM Device Model.model_name` (default `''`/id) |
| 15 | `device_model_name` | string | **alias** = `master_item_name` (per DC contract, `services/imm04.py:904`) |
| 16 | `vendor_name` | string | enrich `AC Supplier.supplier_name` |
| 17 | `supplier_name` | string | **alias** = `vendor_name` (`services/imm04.py:906`) |
| 18 | `clinical_dept_name` | string | enrich `AC Department.department_name` |
| 19 | `po_ref_name` | string | enrich `AC Purchase.purchase_name` (fallback id) |
| 20 | `asset_name` | string | enrich `AC Asset.asset_name` |

**(b) `CommissioningListPage`** — `additionalProperties: false`, FULL success envelope (§20.1):
```yaml
CommissioningListPage:
  type: object
  additionalProperties: false
  properties:
    success: { type: boolean, enum: [true] }
    data:
      type: object
      additionalProperties: false        # né open-schema guard
      properties:
        items:      { type: array, items: { $ref: '#/components/schemas/CommissioningListItem' } }
        pagination: { $ref: '#/components/schemas/Pagination' }   # REUSE component @yaml:752 — KHÔNG tạo mới
      required: [items, pagination]
  required: [success, data]
```

#### 20.3. Path · params · responses

- **Path:** `GET /api/method/assetcore.api.imm04.list_commissioning` · **operationId:** `listCommissioning` · **tags:** `[commissioning]` (**inline operation-tag MỚI** — mirror `tags: [asset]`; OAS KHÔNG có top-level `tags:` registry nên chỉ cần thêm ở operation, KHÔNG cần đăng ký registry) · **security:** OAuth2/session (mirror `listAssets`).
- **Params:** `$ref Page` + `$ref PageSize` (REUSE, clamp 1..100 `pagination.py:8`) + **param MỚI `CommissioningFilters`**.
- **`CommissioningFilters`** (`name: filters`, `in: query`, `required: false`, `type: string` JSON-string, `default: '{}'`) — mirror `WorkOrderFilters` (`yaml:235`). Description liệt kê **12 key ∈ `_ALLOWED_FILTER_KEYS`** (`services/imm04.py:125-130`): `workflow_state · po_reference · master_item · vendor · clinical_dept · docstatus · is_radiation_device · doa_incident · vendor_serial_no · internal_tag_qr · expected_installation_date · final_asset`. Key ngoài whitelist → **bỏ qua** (`services/imm04.py:837`), KHÔNG throw. `example: '{"clinical_dept":"AC-DEPT-0001"}'`.
  - **BA note (completeness, KHÔNG bắt buộc mở rộng scope):** endpoint còn honor **virtual key `overdue=1`** (BR-04-10, `services/imm04.py:846`) — KHÔNG ∈ `_ALLOWED_FILTER_KEYS` (whitelist ảo riêng `_VIRTUAL_FILTER_KEYS`), AND thêm `overdue_commissioning_filter()`. Vì `filters` là JSON-string opaque, mô tả 12 key là contract chính; **được phép** thêm 1 câu mô tả `overdue` là virtual-key optional (drill "Quá hạn SLA"). KHÔNG khai `overdue` như raw column trong danh sách 12 (giữ đúng `_ALLOWED_FILTER_KEYS`).
- **Responses (slot `{200, 401}`):**
  - `200`: `oneOf [CommissioningListPage, Error]` — **Decision-B**: lỗi nghiệp vụ (service `raise ServiceError(FORBIDDEN)` khi blanket `has_permission(_DT, read)` fail, `services/imm04.py:833-836`) → `_handle` bắt → `_err` trên **HTTP-200 + Error envelope** (KHÔNG raise→4xx). closed-schema 2 nhánh disjoint (route-by-value, KHÔNG discriminator — read-path).
  - `401`: `$ref '#/components/responses/Unauthorized401'` (uniform mobile convention — bearer hết hạn → refresh; mirror `listIncidents` slot, `yaml:8908`).
  - **2 loại 403 — KHÔNG wire response 403 riêng:** (1) *dispatcher-403* (guest/no-token, `@frappe.whitelist()` bare) đến TRƯỚC handler = re-auth → phủ bởi 401 flow; (2) *in-handler cap-403* (`FORBIDDEN` khi thiếu quyền read) đến trên **HTTP-200** như nhánh `Error` của 200-oneOf (Decision-B). ⇒ slot `{200,401}` đủ, KHÔNG thêm `403`.

#### 20.4. Invariant · guard bump · RED→GREEN (AC6/AC7)

- **INVARIANT `count == rows`:** `pagination.total = frappe.db.count(_DT, query_filters)` (`services/imm04.py:854`) và `items = frappe.get_all(_DT, filters=query_filters, …)` (`:857-861`) dùng **CÙNG `query_filters`** ⇒ `total == len(items)` **được bảo đảm cấu trúc**. ⚠️ **KHÔNG khai "permission-aware row-level":** `Asset Commissioning` CÓ `permission_query_conditions` (`asset_commissioning_query`, `hooks.py:435`) + `has_permission` hook (`hooks.py:444`), NHƯNG cả `frappe.db.count` lẫn `frappe.get_all` **BỎ QUA** 2 hook đó (chỉ `frappe.get_list` áp) → count & rows **cùng bỏ qua** ⇒ vẫn khớp nhau (đây chính là lý do KHÔNG dính lỗi P1 `count!=rows` của `/assets`). Kiểm-soát-truy-cập của endpoint = **blanket `has_permission(_DT, read)` upfront** (`:833`, Decision-B FORBIDDEN nếu fail), **KHÔNG** row-scope theo `asset_commissioning_query`. Nếu mobile cần row-scope (vd KTV chỉ thấy phiếu khoa mình) → **[ROADMAP] xác nhận với QA/security** — KHÔNG phải deliverable CR-25a này. Description schema chỉ khai `total == len(items)`, KHÔNG khai "permission-aware".
- **Count/opId bump = +1 (KHÔNG hardcode 73→74).** ⚠️ **AC ghi "73→74" là STALE** — baseline **LIVE hiện tại = 75 path / 75 opId** (drift do phiên concurrent: `createTransfer` ADR-MOBILE-046 + khác). **Dev PHẢI đọc baseline LIVE ngay trước khi curate** (`grep -cE '^  /api/method' <yaml>`) rồi bump **live+1**. Delta bất biến: **+1 path · +1 opId · +2 schema (`CommissioningListItem`,`CommissioningListPage`) · +1 param (`CommissioningFilters`) · +N test-case**.
- **Guard counters đồng bộ (đọc LIVE, cộng delta):** `_EXPECTED_TEST_COUNT` (`tests/test_mobile_oas.py`, hiện 707) += số TC class mới; đồng bộ **3 counter** trong `tests/test_mobile_docset.py`: `_GUARD_SUITE_EXPECTED["test_mobile_oas.py"]` (707) · `_GUARD_SUITE_SUM` (850) · `_MOBILE_OAS_TOTAL` (876 = SUM + preflight 26). Bump theo đúng số TC thêm.
- **AC5 closed-schema guard:** `additionalProperties:false` trên MỌI schema mới (`CommissioningListItem`, `CommissioningListPage` + khối `data`); global closed-schema guard (`test_mobile_docset`) phải xanh; KHÔNG sửa path/schema hiện có (0 blast-radius).
- **AC7 RED→GREEN chứng minh (KHÔNG nhận "xanh suông"):** chạy guard TRƯỚC curate phải **ĐỎ** (path/opId/schema chưa tồn tại → assert fail); SAU curate phải **XANH THẬT** (`bench --site miyano run-tests` cho `test_mobile_oas` + `test_mobile_docset` = `Ran N OK`, **0 skip**).

#### ADR-IMM04-MOBILE-LIST-01 (dev mirror sang ADR-MOBILE-048 — hoặc số kế tiếp available; concurrent-drift, dev pin tại curation)

- **Status:** Accepted · **Date:** 2026-07-14
- **Context:** Mobile Trục B mở nhánh IMM-04 F6 — cần LIST-ENTRY cho màn field-tech "Tiếp nhận & Nghiệm thu hiện trường". Backend `list_commissioning` đã LIVE (web-FE dùng). Yêu cầu curate contract vào OAS mirror mà 0 đụng `.py`.
- **Decision:** (1) Envelope **Asset-style `data.items[]`** (mirror `AssetListEnvelope`) — vì service trả `{items, pagination}` (KHÁC WO/calib `data.data[]`). (2) `CommissioningListPage` = **full success envelope** (không phải `{items,pagination}` trần) để khớp live `_ok` wrap. (3) Lỗi quyền = **Decision-B** (HTTP-200 + Error), slot `{200,401}`, KHÔNG wire 403 riêng. (4) `docstatus` = int-enum `[0,1,2]` (KHÔNG Check → miễn int-vs-bool); `is_radiation_device`/`doa_incident` chỉ filter-key, KHÔNG ∈ list-item.
- **Alternatives:** (a) `data.data[]` như WO/calib — **loại** vì service literal trả `items` (parity-drift với live). (b) `CommissioningListPage = {items,pagination}` trần — **loại** vì mất wrapper `success`/`data` → sai live-wire. (c) Hard-enum `workflow_state` — **loại** vì Select nhiều state, codegen vỡ khi thêm.
- **Consequences:** +1 path/opId, +2 schema, +1 param, +N TC; 0 `.py`/reload/migrate (pure-YAML); guard counters phải bump đồng bộ; tag `commissioning` mở nhánh module-tag mới cho các endpoint IMM-04 kế tiếp.

#### Boundaries (Always / Never)

- **Always:** curate pure-YAML vào `docs/mobile/openapi/assetcore-mobile.openapi.yaml`; đọc baseline count **LIVE** trước bump; REUSE `Pagination`/`Page`/`PageSize`/`Unauthorized401`; `additionalProperties:false` mọi schema mới; ground field-set từ `services/imm04.py` (`_LIST_FIELDS`/enrich/`_ALLOWED_FILTER_KEYS`) — KHÔNG bịa; RED-before/GREEN-after chứng minh.
- **Never:** ❌ sửa `.py`/reload/migrate (backend LIVE); ❌ đụng `AssetCommissioningOrigin`/`getAssetCommissioningOrigin` (§19, nguồn khác); ❌ sửa path/schema hiện có (0 blast-radius); ❌ khai field Check int-0/1 trong `CommissioningListItem`; ❌ tạo `Pagination` mới; ❌ hardcode `73→74` (đọc live); ❌ nhận "xanh suông" khi test chưa assert path/schema mới.

> 📱 **Mobile OAS contract (tóm tắt):** curate `docs/mobile/openapi/assetcore-mobile.openapi.yaml` — opId `listCommissioning`, tag `commissioning`, 200 = oneOf `[CommissioningListPage, Error]` (Decision-B) + 401 `Unauthorized401`; schema `CommissioningListItem` (20 prop closed) + `CommissioningListPage` (full envelope) + param `CommissioningFilters` (12 key JSON-string). CONTRACT-ONLY (backend LIVE `api/imm04.py:24` / `services/imm04.py:831`, 0 `.py`/reload/migrate). Quyết định đầy đủ: `ADR-MOBILE-048` (dev tạo) + `docs/mobile/04-api-contract.md` (dev thêm §). ⚠️ Path/opId count LIVE-drift — đọc live baseline, bump +1.

---

### 21. get_form_context — Mobile DETAIL màn "Tiếp nhận & Nghiệm thu hiện trường" (📱 Trục B · CR-25b · MỞ NHÁNH IMM-04 F6 DETAIL)

**Actor:** KTV / Commissioning User (mobile) · **Verb:** GET · **Handler:** `assetcore.api.imm04.get_form_context` (`api/imm04.py:19-21`, bare `@frappe.whitelist()` → nhận GET) → `svc.get_form_context` (`services/imm04.py:796-808`).
**Deliverable = curate endpoint DETAIL-READ vào OAS mirror.** Đây là **sibling DETAIL** của `listCommissioning` (§20 list-entry) — mở phiếu `Asset Commissioning` CHI TIẾT để field-tech tiếp nhận & nghiệm thu (theo precedent list→detail R40→R42 `listAllocations→getAllocation`, R43→R44 `listInternalAudits→getInternalAudit`). CONTRACT-ONLY: **backend ĐÃ LIVE** (`get_form_context`/`_serialize_*` — 0 `.py` runtime change / 0 reload / 0 migrate). Curate là **pure-YAML** vào `docs/mobile/openapi/assetcore-mobile.openapi.yaml` + đồng bộ test guard.

> ⚠️ **KHÔNG nhầm** với `getAssetCommissioningOrigin` (§19 — nguồn `imm04.get_commissioning_origin`, sub-tab Asset Detail #4, wrapper `AssetCommissioningOrigin`). Đây là **nguồn khác** (`imm04.get_form_context`), tag `commissioning`, schema/opId riêng (blast-radius = 0).

#### 21.0. ⚠️ HAI SELF-CORRECTION so với acceptance (BA quyết định — CONTRACT phải bám wire THẬT, đọc kỹ trước khi curate)

Acceptance vòng 45 ground **sai 2 điểm** so với code LIVE. Core Doc (sau sửa) là **quyết định cuối** — dev implement theo mục này, KHÔNG theo chữ acceptance gốc:

- **SC#1 (BẮT BUỘC — factual, wire-shape):** acceptance ghi `allowed_transitions` là **`array[string]`**. **SAI.** `get_form_context` gán `result["allowed_transitions"] = _get_workflow_transitions(name)` (`services/imm04.py:807`); helper `_get_workflow_transitions` (`services/imm04.py:667-678`) **return `list[dict]`** = `[{action, next_state, allowed_role}, …]` (role-filtered). Web Core Doc ĐÃ model đúng là `WorkflowTransition[]` (§1.5 `05_API_Specification.md:213,217-221`). ⇒ CONTRACT-ONLY **phải** khai `allowed_transitions` = **`array` of `CommissioningTransitionItem`** (object 3-field), **KHÔNG** `array[string]`. ⚠️ **KHÔNG mirror mù `getInternalAudit`** (imm16 dùng helper KHÁC trả `array[string]` — `allowed_transitions` shape là per-module, PHẢI ground theo helper của IMM-04).
- **SC#2 (ADR-IMM04-MOBILE-DETAIL-01 — design, OPEN→CLOSED):** acceptance ghi `CommissioningDetail` + 3 child **OPEN** (`additionalProperties:true`) "theo deviation R44". **Áp sai tiền đề.** Deviation R44/R42 (`getInternalAudit`/`getAllocation`/`RepairWorkOrderDetail`) OPEN **CHỈ VÌ** serializer là `doc.as_dict()` — surface rò meta Frappe (`name/owner/creation/idx`; child `parent/parentfield/parenttype`) VƯỢT field nghiệp-vụ enumerable ⇒ closed sẽ "nói dối" → strict codegen crash. **`_serialize_commissioning` (`services/imm04.py:728-791`) + 3 child serializer là CURATED explicit-dict literal** (KHÔNG `as_dict()`) — surface **enumerable đầy đủ, 0 meta leak**, Y HỆT sibling cùng-module `CommissioningListItem` (§20, CLOSED) + `DueCalibrationListItem` (CLOSED). Quy tắc bất biến của codebase: **`as_dict` → OPEN · curated → CLOSED ("Option A", chỉ `name` required)**. R44 áp quy tắc (as_dict→OPEN, sửa acceptance-CLOSED). R45 áp **cùng quy tắc, chiều ngược** (curated→CLOSED, sửa acceptance-OPEN). ⇒ **`CommissioningDetail` + 3 child + `CommissioningTransitionItem` = CLOSED (`additionalProperties:false`)**; chỉ enrich thêm lợi ích: đóng native-pass global closed-schema guard, **KHÔNG** cần thêm vào OPEN-allowlist của `test_mobile_docset`. Chi tiết ở ADR cuối §.

#### 21.0.1. ⚠️ Trạng thái triển khai (vòng 47 — CR-25-FIX · đọc để KHÔNG over-scope) → `ADR-MOBILE-055`

§21 mô tả **target-state đầy đủ** (SC#1 + SC#2). Nhưng bản build CR-25 concurrent (ADR-MOBILE-053 + `04-api-contract.md §8.49` + YAML LIVE) đã curate endpoint ở trạng thái **5 schema OPEN + `allowed_transitions` `array[string]`** (theo acceptance gốc vòng 45). Vòng 47 (CR-25-FIX) đóng **CHỈ SC#1** — phân biệt rõ:

| | SC#1 — shape `allowed_transitions` | SC#2 — Detail+3child OPEN→CLOSED |
|---|---|---|
| Trạng thái LIVE (trước vòng 47) | `array[string]` (SAI wire) | `additionalProperties:true` (OPEN) |
| **Vòng 47 (CR-25-FIX)** | ✅ **SỬA** → `array[object]` `$ref CommissioningTransitionItem` (P1 codegen-crash) | ❌ **DEFER** (KHÔNG P1; flip = scope-creep) |
| Đích §21.2/§21.4(d2)/Boundaries | `array[object]` (đã đạt sau vòng 47) | CLOSED (lập luận sound, chờ **CR-25-FIX-2**) |

⇒ Dev vòng 47: implement §21.2(a) `CommissioningTransitionItem` (CLOSED) + đổi `allowed_transitions.items` sang `$ref` + sửa false-green assertion + thêm LIVE-emit parity (§21.4). **GIỮ `CommissioningDetail` + 3 child OPEN** vòng này (SC#2 defer). §21.2 "6 schema TẤT CẢ closed" + §21.4(d2) mô tả **đích cuối** — KHÔNG bắt buộc trong vòng 47 (chỉ `CommissioningTransitionItem` mới = CLOSED). Chi tiết quyết định + failure-mode + why-per-module: [`../mobile/ADR-MOBILE-055.md`](../mobile/ADR-MOBILE-055.md).

#### 21.1. Envelope — `data = $ref CommissioningDetail` TRỰC-TIẾP (detail-read, KHÁC list `data.items[]`)

`get_form_context` return `_serialize_commissioning(doc)` + gán thêm `allowed_transitions`; `helpers._ok(...)` (`utils/response.py:92`) wrap → wire body:

```jsonc
{
  "success": true,
  "data": { /* CommissioningDetail — object phẳng 44 header-field + allowed_transitions[] + 3 child[] */ }
}
```

`CommissioningDetailEnvelope` = **CLOSED** `{success: enum[true], data: $ref CommissioningDetail}` (grounded `_ok(result)` `utils/response.py:92`) — mirror `SpareAllocationDetailEnvelope`/`InternalAuditDetailEnvelope`/`RepairWorkOrderDetailEnvelope`.

#### 21.2. Schemas cần curate (6 schema MỚI — TẤT CẢ closed)

**(a) `CommissioningTransitionItem`** — `additionalProperties: false`, `required: [action, next_state, allowed_role]` (dict LUÔN đủ 3 key, `services/imm04.py:675`). Grounded `_get_workflow_transitions` (SC#1):

| # | Property | Type | Ghi chú (grounding) |
|---|---|---|---|
| 1 | `action` | string | Nhãn nút workflow (vd "Bắt đầu kiểm tra"). `t.action` `:675` |
| 2 | `next_state` | string | Trạng thái đích sau transition. `t.next_state` `:675` |
| 3 | `allowed_role` | string | Role được phép (đã role-filter theo session user). `t.allowed` `:675` |

**(b) `BaselineTestItem`** — `additionalProperties: false`, `required: [parameter]` (Data reqd; PK không có ở child). Grounded `_serialize_baseline_tests` (`services/imm04.py:681-694`) + doctype `Commissioning Checklist`. **11 property:**

| # | Property | Type | Ghi chú (grounding) |
|---|---|---|---|
| 1 | `idx` | integer | Số thứ tự dòng (Frappe row idx) |
| 2 | `parameter` | string | Tên thông số đo (Data, **reqd**). **required.** |
| 3 | `measured_val` | number, nullable | Giá trị đo (Float; `row.measured_val` raw) |
| 4 | `unit` | string | Đơn vị (Data) |
| 5 | `test_result` | string | Select `\nPass\nFail\nN/A` leading-blank ⇒ `""` hợp lệ → **string KHÔNG hard-enum** (ADR-MOBILE-051 §2.c.1) |
| 6 | `fail_note` | string, nullable | Ghi chú fail (Text; `row.fail_note` raw) |
| 7 | `is_critical` | integer | **Check → int 0\|1** (`row.get("is_critical") or 0`) — **CR-01, KHÔNG boolean** |
| 8 | `measurement_type` | string | Select `Numeric\nPass/Fail\nVisual` (`or ""`) → string |
| 9 | `expected_min` | number, nullable | Ngưỡng min (Float; `row.get("expected_min")` → có thể `null`) |
| 10 | `expected_max` | number, nullable | Ngưỡng max (Float; nullable) |
| 11 | `na_applicable` | integer | **Check → int 0\|1** (`or 0`) — **CR-01** |

**(c) `CommissioningDocumentItem`** — `additionalProperties: false`, `required: [doc_type, status]` (2 Select reqd). Grounded `_serialize_comm_documents` (`services/imm04.py:697-709`) + doctype `Commissioning Document Record`. **9 property:**

| # | Property | Type | Ghi chú (grounding) |
|---|---|---|---|
| 1 | `idx` | integer | Row idx |
| 2 | `doc_type` | string | Select 7 giá-trị (CO/CQ/Packing List/Manual/…) reqd → **string KHÔNG hard-enum**. **required.** |
| 3 | `status` | string | Select `Pending/Received/Missing/Rejected/Waived` reqd → **string KHÔNG hard-enum**. **required.** |
| 4 | `received_date` | string | `str(row.received_date or "")` ⇒ `""` HOẶC `YYYY-MM-DD` → **type:string KHÔNG `format:date`** (`""` không hợp RFC-full-date) |
| 5 | `remarks` | string | Small Text (`or ""`) |
| 6 | `is_mandatory` | integer | **Check → int 0\|1** (`or 0`) — **CR-01** |
| 7 | `file_url` | string | Attach path (`or ""`) |
| 8 | `doc_number` | string | Data (`or ""`) |
| 9 | `expiry_date` | string | `str(row.get("expiry_date") or "")` → **type:string KHÔNG `format:date`** |

**(d) `CommissioningLifecycleEventItem`** — `additionalProperties: false`, `required: []` (mọi field `or ""`; `lifecycle_events` là mảng inject-runtime `doc.get("lifecycle_events") or []`, KHÔNG child-table persisted của `Asset Commissioning`). Grounded `_serialize_lifecycle_events` (`services/imm04.py:712-725`). **8 property:**

| # | Property | Type | Ghi chú (grounding) |
|---|---|---|---|
| 1 | `idx` | integer | Row idx |
| 2 | `event_type` | string | Loại sự kiện vòng đời (`or ""`) |
| 3 | `from_status` | string | Trạng thái nguồn (`or ""`) |
| 4 | `to_status` | string | Trạng thái đích (`or ""`) |
| 5 | `actor` | string | User thực hiện (`or ""`) |
| 6 | `event_timestamp` | string | `str(... or "")` → `""` HOẶC datetime → **type:string KHÔNG `format:date-time`** |
| 7 | `ip_address` | string | IP nguồn (`or ""`) |
| 8 | `remarks` | string | Ghi chú (`or ""`) |

**(e) `CommissioningDetail`** — `additionalProperties: false`, **`required: [name]`** (Option A — chỉ PK bắt buộc, mirror `CommissioningListItem`). Grounded VERBATIM `_serialize_commissioning` (`services/imm04.py:728-791`, **44 scalar header key**) + `allowed_transitions` (`get_form_context:807`) + 3 child array = **48 property** *(acceptance ghi "45 field header" — conflate `allowed_transitions` vào header; con số chính xác grounded @source = **44 scalar + 4 array**)*.

**44 scalar header field** (thứ tự source `:744-787`):

| # | Property | Type | Ghi chú (grounding) |
|---|---|---|---|
| 1 | `name` | string | PK phiếu (naming ACC-…). **required.** `:744` |
| 2 | `workflow_state` | string | Select nhiều state → **string KHÔNG hard-enum** (codegen an toàn) `:745` |
| 3 | `docstatus` | integer, `enum:[0,1,2]` | Frappe docstatus — **KHÔNG Check** → int-enum hợp lệ `:746` |
| 4 | `po_reference` | string | Link `AC Purchase` `:747` |
| 5 | `master_item` | string | Link `IMM Device Model` `:748` |
| 6 | `master_item_name` | string | enrich `IMM Device Model.model_name` `:749` |
| 7 | `vendor` | string | Link `AC Supplier` `:750` |
| 8 | `vendor_name` | string | enrich `AC Supplier.supplier_name` `:751` |
| 9 | `clinical_dept` | string | Link `AC Department` `:752` |
| 10 | `clinical_dept_name` | string | enrich `AC Department.department_name` `:753` |
| 11 | `expected_installation_date` | string | `str(... or "")` → **string KHÔNG `format`** `:754` |
| 12 | `installation_date` | string | `str(... or "")` → **string KHÔNG `format`** `:755` |
| 13 | `reception_date` | string | `str(get or "")` → **string KHÔNG `format`** `:756` |
| 14 | `risk_class` | string | Select A/B/C/D/Radiation/`""` → **string KHÔNG hard-enum** `:757` |
| 15 | `board_approver` | string | Link User (`or ""`) `:758` |
| 16 | `pending_approver` | string | (`or ""`) `:759` |
| 17 | `approval_stage` | string | (`or ""`) `:760` |
| 18 | `approval_submitted_at` | string | `str(get or "")` → **string KHÔNG `format`** `:761` |
| 19 | `approval_remarks` | string | (`or ""`) `:762` |
| 20 | `clinical_head` | string | (`or ""`) `:763` |
| 21 | `qa_officer` | string | (`or ""`) `:764` |
| 22 | `facility_checklist_pass` | integer | **Check → int 0\|1** (`get or 0`) — **CR-01, KHÔNG boolean** `:765` |
| 23 | `overall_inspection_result` | string | (`or ""`) `:766` |
| 24 | `handover_doc` | string | (`or ""`) `:767` |
| 25 | `commissioned_by` | string | (`or ""`) `:768` |
| 26 | `commissioning_date` | string | `str(get or "")` → **string KHÔNG `format`** `:769` |
| 27 | `vendor_engineer_name` | string, nullable | Data raw (`doc.vendor_engineer_name`) `:770` |
| 28 | `is_radiation_device` | integer | **Check → int 0\|1** (raw) — **CR-01** `:771` |
| 29 | `doa_incident` | integer | **Check → int 0\|1** (raw) — **CR-01** `:772` |
| 30 | `documents_incomplete` | integer | **Check → int 0\|1** (`get or 0`) — **CR-01** `:773` |
| 31 | `documents_incomplete_note` | string | (`or ""`) `:774` |
| 32 | `vendor_serial_no` | string, nullable | Data raw `:775` |
| 33 | `internal_tag_qr` | string, nullable | Data raw `:776` |
| 34 | `custom_moh_code` | string, nullable | Data raw `:777` |
| 35 | `site_photo` | string, nullable | Attach raw `:778` |
| 36 | `installation_evidence` | string, nullable | Attach raw `:779` |
| 37 | `qa_license_doc` | string, nullable | Attach raw `:780` |
| 38 | `final_asset` | string, nullable | Link `AC Asset` raw `:781` |
| 39 | `amend_reason` | string, nullable | raw `:782` |
| 40 | `amended_from` | string, nullable | Link raw `:783` |
| 41 | `modified` | string | `str(doc.modified)` — space-sep → **string KHÔNG `format:date-time`** `:784` |
| 42 | `owner` | string | raw `:785` |
| 43 | `is_locked` | **boolean** | `doc.docstatus == 1` → Python bool → **type:boolean THẬT** (⚠️ KHÁC 4 Check-int trên — CR-01 phân biệt) `:786` |
| 44 | `current_user_roles` | array, items `type:string` | `frappe.get_roles(session.user)` `:787` |

**4 array field:**

| Property | Type | Ghi chú |
|---|---|---|
| `allowed_transitions` | array, items `$ref CommissioningTransitionItem` | **SC#1** — CTA server-driven (`:807`), object 3-field, **KHÔNG string** |
| `baseline_tests` | array, items `$ref BaselineTestItem` | child đo kiểm (`:788`) |
| `commissioning_documents` | array, items `$ref CommissioningDocumentItem` | child tài liệu (`:789`) |
| `lifecycle_events` | array, items `$ref CommissioningLifecycleEventItem` | log vòng đời inject-runtime (`:790`) |

**(f) `CommissioningDetailEnvelope`** — `additionalProperties: false`, `required: [success, data]`:
```yaml
CommissioningDetailEnvelope:
  type: object
  additionalProperties: false
  properties:
    success: { type: boolean, enum: [true] }
    data:    { $ref: '#/components/schemas/CommissioningDetail' }
  required: [success, data]
```

#### 21.3. Path · params · responses

- **Path:** `GET /api/method/assetcore.api.imm04.get_form_context` · **operationId:** `getCommissioning` (đặt theo **DOMAIN**, mirror `getRepairWorkOrder`/`getAllocation`/`getInternalAudit` — **KHÔNG** theo tên hàm `get_form_context`) · **tags:** `[commissioning]` (REUSE operation-tag đã mở ở §20) · **security:** OAuth2/session.
- **Params:** **1 param `name`** — `in: query`, `required: true`, `schema.type: string`. Description dẫn nguồn `api/imm04.py:19 get_form_context(name)` (VD `ACC-26-04-00001`). Mirror slot param `getAllocation`/`getInternalAudit` (`name` typed query required).
- **Responses (slot `{200, 401, 403}` — đối xứng path DETAIL khác `getAllocation`/`getInternalAudit`):**
  - `200`: `oneOf [CommissioningDetailEnvelope, Error]` — **Decision-B closed-schema** 2 nhánh disjoint required-set (route-by-value `body.success`, **KHÔNG discriminator**). Lỗi nghiệp-vụ đến trên **HTTP-200 + Error** (`Error.code ⊇ {NOT_FOUND, FORBIDDEN}`, `http_status` trong body): (i) **NOT_FOUND** — phiếu∄ → `nthrow(MSG.IMM04_NOT_FOUND, name=name)` (`services/imm04.py:801`, `MSG.IMM04_NOT_FOUND="IMM04-NOT-FOUND"` `utils/messages.py:86`); (ii) **in-handler cap-403 FORBIDDEN** — `frappe.has_permission(_DT, read, doc, throw=True)` fail → `raise ServiceError(FORBIDDEN, …)` (`services/imm04.py:802-805`) → `_handle`→`_err` HTTP-200. ⚠️ **KHÔNG thêm status-line `404`** (not-found về qua Error trên HTTP-200 body, KHÔNG raise→4xx — parity `getAllocation`/`getInternalAudit`).
  - `401`: `$ref '#/components/responses/Unauthorized401'` (bearer hết-hạn/invalid → refresh; uniform mobile convention).
  - `403`: `$ref '#/components/responses/Forbidden'` (**dispatcher-403** — guest/no-token trip TRƯỚC handler vì `@frappe.whitelist()` bare no-`allow_guest`; `FrappeRawError` HTTP-403 status-line THẬT). ⚠️ **2 loại 403 phân biệt rõ:** dispatcher-403 (guest) = slot `403`; in-handler cap-403 (permission read fail) = nhánh `Error` của 200-oneOf (Decision-B, HTTP-200) — KHÔNG double-wire.

#### 21.4. Invariant · guard bump · RED→GREEN (AC6/AC7)

- **Path/opId bump = +1 (đọc LIVE, KHÔNG hardcode).** Baseline LIVE 2026-07-15 = **83 path / 83 opId** → **84/84**. ⚠️ concurrent-drift — dev PHẢI `grep -cE '^  /api/method' <yaml>` ngay trước curate rồi bump **live+1**.
- **Guard counters (đọc LIVE, cộng `+N` = số TC class mới, ĐỒNG BỘ cả 4):** baseline LIVE 2026-07-15:
  - `_EXPECTED_TEST_COUNT` (`tests/test_mobile_oas.py`) = **758** → `758+N`
  - `_GUARD_SUITE_EXPECTED["test_mobile_oas.py"]` (`tests/test_mobile_docset.py`) = **758** → `758+N`
  - `_GUARD_SUITE_SUM` = **901** → `901+N`
  - `_MOBILE_OAS_TOTAL` = **927** (= SUM 901 + preflight 26) → `927+N`
  - ⚠️ nếu tồn tại counter business-path (`c5` / `_PARITY_BUSINESS_PATHS` / `_MVP_*`) — `getInternalAudit` bump `c5`+`_PARITY_BUSINESS_PATHS` `71→72`; getCommissioning là **business-path DETAIL** → **grep-verify LIVE + bump +1** (KHÔNG hardcode; đọc value hiện tại vì đã drift sau getInternalAudit). `_MVP_LIST_ENVELOPE` **GIỮ NGUYÊN** (detail ≠ list).
- **Guard test class MỚI** `TestMobileGetCommissioningDetailContract` (`tests/test_mobile_oas.py`, **RED-before/GREEN-after ≥2 TC**, mirror `TestMobileGetInternalAuditDetailContract`/`TestMobileGetAllocationDetailContract`):
  - **(a)** path `/api/method/assetcore.api.imm04.get_form_context` + `operationId: getCommissioning` + `tags:[commissioning]` tồn tại.
  - **(b)** param `name` `in:query` `required:true` `schema.type:string`.
  - **(c)** 200 `oneOf` **CHÍNH XÁC** `[CommissioningDetailEnvelope, Error]`.
  - **(d)** `CommissioningDetailEnvelope` closed (`additionalProperties:false`) + `success` const `enum:[true]` + `required:[success,data]`.
  - **(d2 — SC#2 anti-drift)** `CommissioningDetail` + `BaselineTestItem` + `CommissioningDocumentItem` + `CommissioningLifecycleEventItem` + `CommissioningTransitionItem` **đều CLOSED** (`additionalProperties:false`) — chống re-drift về OPEN.
  - **(d3 — SC#1 anti-drift)** `CommissioningDetail.properties.allowed_transitions.items.$ref == CommissioningTransitionItem` (**array of OBJECT**, KHÔNG `type:string`) + `CommissioningTransitionItem.required == [action,next_state,allowed_role]`.
  - **(e)** 4 array `$ref` (allowed_transitions/baseline_tests/commissioning_documents/lifecycle_events) resolve — 0 dangling.
  - **(f)** path-count mirror tăng **ĐÚNG +1** (assert số cũ→mới đọc-live, KHÔNG hardcode lẻ).
  - **(live)** `set(inspect.signature(imm04.get_form_context).parameters) == {"name"}` (live-sig parity) + pure-yaml (handler untouched).
  - **(live-emit — SC#1 anti-drift, CR-25-FIX vòng 47)** LIVE-emit source-parity (mirror sibling `test_pmtrans_f_live_emit_grounded`): `inspect.getsource(imm04.get_form_context)` chứa `"allowed_transitions"` VÀ `_get_workflow_transitions(`; `inspect.getsource(imm04._get_workflow_transitions)` chứa cả 3 literal `"action"`+`"next_state"`+`"allowed_role"` → chứng minh builder **dict-shaped** (contract `array[object]` khớp wire THẬT, chống drift contract↔live). +1 TC ⇒ guard counter `774→775` (`_EXPECTED_TEST_COUNT`/`_GUARD_SUITE_EXPECTED`) · `_GUARD_SUITE_SUM 917→918` · `_MOBILE_OAS_TOTAL 943→944` (đọc LIVE trước bump — đa-phiên drift).
- **RED→GREEN chứng minh (KHÔNG "xanh suông"):** chạy guard TRƯỚC curate = **ĐỎ** (path/opId/schema chưa tồn tại); SAU = **XANH THẬT** — `bench --site miyano run-tests` cho `test_mobile_oas` + `test_mobile_docset` (path-count/api-catalog) + `test_mobile_preflight` (YAML valid + `$ref` resolvable) = `Ran N OK`, **0 skip**.

#### ADR-IMM04-MOBILE-DETAIL-01 (dev mirror sang `ADR-MOBILE-053` — hoặc số kế available; concurrent-drift, dev pin tại curation)

- **Status:** Accepted · **Date:** 2026-07-15
- **Context:** Mobile Trục B mở nhánh IMM-04 F6 DETAIL — cần sibling chi-tiết cho `listCommissioning` (§20). Backend `get_form_context` đã LIVE (web-FE dùng). Curate contract vào OAS mirror mà 0 đụng `.py`. Acceptance ground 2 điểm sai vs code LIVE (§21.0).
- **Decision:** (1) **SC#1** — `allowed_transitions` = **`array` of `CommissioningTransitionItem`** {action,next_state,allowed_role} (grounded `_get_workflow_transitions` `:667-678` trả `list[dict]`), **KHÔNG** `array[string]`; per-module helper quyết định shape, KHÔNG mirror mù `getInternalAudit`. (2) **SC#2** — `CommissioningDetail` + 3 child + `CommissioningTransitionItem` = **CLOSED** (`additionalProperties:false`, `required:[name]` Option A) vì `_serialize_commissioning` là **curated explicit-dict** (KHÔNG `as_dict()`) → surface enumerable, parity sibling `CommissioningListItem`/`DueCalibrationListItem`. (3) `docstatus` int-enum `[0,1,2]`; 4 cờ Check (`facility_checklist_pass`/`is_radiation_device`/`doa_incident`/`documents_incomplete`) = `type:integer` (CR-01) — phân biệt `is_locked` = `type:boolean` THẬT (Python bool). (4) Slot `{200,401,403}`: NOT_FOUND+cap-403 qua Error HTTP-200 (Decision-B), dispatcher-403 = slot `403`, KHÔNG status-line 404. (5) Date/datetime child+header serialize `str(x or "")` → `type:string` **KHÔNG `format`** (empty-string né RFC-fail).
- **Alternatives:** (a) `allowed_transitions: array[string]` như acceptance/`getInternalAudit` — **loại**: sai wire (`_get_workflow_transitions` trả dict) → strict codegen deser crash / mất `next_state`+`allowed_role` FE cần. (b) Detail OPEN theo acceptance/R44 — **loại**: tiền đề R44 (`as_dict` meta-leak) KHÔNG áp cho curated serializer; OPEN làm lệch sibling cùng-module + mất anti-drift + phải thêm OPEN-allowlist thừa. (c) Hard-enum `workflow_state`/`risk_class`/Select child — **loại**: leading-blank ⇒ `""` hợp lệ, hard-enum reject-valid → codegen crash (ADR-MOBILE-051 §2.c.1). (d) `format:date`/`date-time` cho field ngày — **loại**: serializer emit `""` khi rỗng, không hợp RFC → live-validation fail.
- **Consequences:** +1 path/opId (83→84), +6 schema (5 detail/child/transition CLOSED + 1 envelope CLOSED), +1 param (`name`), +N TC; 0 `.py`/reload/migrate (pure-YAML — [AUTO], KHÔNG HARD-STOP); 4 guard counter + business-path counter bump ĐỒNG BỘ; CLOSED ⇒ native-pass global closed-schema guard (KHÔNG thêm OPEN-allowlist). Working tree để USER review (KHÔNG commit).

#### Boundaries (Always / Never)

- **Always:** curate pure-YAML vào `docs/mobile/openapi/assetcore-mobile.openapi.yaml`; đọc baseline count + 4 guard counter **LIVE** trước bump; REUSE `Unauthorized401`/`Forbidden`/`Error`; `additionalProperties:false` MỌI schema mới (6); ground field-set VERBATIM từ `_serialize_commissioning`/`_serialize_baseline_tests`/`_serialize_comm_documents`/`_serialize_lifecycle_events`/`_get_workflow_transitions` — KHÔNG bịa; `allowed_transitions` = array-of-OBJECT (SC#1); RED-before/GREEN-after chứng minh.
- **Never:** ❌ sửa `.py`/reload/migrate (backend LIVE); ❌ khai `allowed_transitions` là `array[string]` (SC#1 — wire là dict); ❌ để Detail/child OPEN (SC#2 — curated→CLOSED); ❌ hard-enum `workflow_state`/`risk_class`/Select child (leading-blank ⇒ `""`); ❌ `format:date`/`date-time` field serialize `str(x or "")`; ❌ đụng `AssetCommissioningOrigin`/`getAssetCommissioningOrigin` (§19); ❌ thêm status-line `404` (NOT_FOUND về qua Error HTTP-200); ❌ sửa path/schema hiện có (0 blast-radius); ❌ hardcode `83→84`/counter (đọc live); ❌ nhận "xanh suông" khi test chưa assert path/schema/SC#1/SC#2.

> 📱 **Mobile OAS contract (tóm tắt):** curate `docs/mobile/openapi/assetcore-mobile.openapi.yaml` — opId `getCommissioning`, tag `commissioning`, GET param `name` (query required), 200 = oneOf `[CommissioningDetailEnvelope, Error]` (Decision-B) + 401 `Unauthorized401` + 403 `Forbidden`; **6 schema CLOSED** = `CommissioningDetail` (44 header + 4 array) + `BaselineTestItem`/`CommissioningDocumentItem`/`CommissioningLifecycleEventItem` + `CommissioningTransitionItem` + `CommissioningDetailEnvelope`. **⚠️ 2 SELF-CORRECTION:** `allowed_transitions`=array-of-OBJECT (KHÔNG string, SC#1) · Detail+child=CLOSED (curated serializer, KHÔNG OPEN, SC#2). CONTRACT-ONLY (backend LIVE `api/imm04.py:19` / `services/imm04.py:796`, 0 `.py`/reload/migrate). Quyết định đầy đủ: `ADR-MOBILE-053` (dev tạo) + `docs/mobile/04-api-contract.md` (dev thêm §). ⚠️ Path/opId + 4 counter LIVE-drift — đọc live baseline, bump +1/+N.

---

### 22. submit_baseline_checklist — Mobile WRITE màn "Tiếp nhận & Nghiệm thu hiện trường" (📱 Trục B · CR-25c · MỞ NHÁNH IMM-04 F6 — WRITE-path ĐẦU TIÊN)

**Actor:** KTV / Commissioning User (mobile) · **Verb:** POST · **Handler:** `assetcore.api.imm04.submit_baseline_checklist` (`api/imm04.py:155-162`, `@frappe.whitelist(methods=["POST"])`) → `svc.submit_baseline_checklist` (`services/imm04.py:1437-1456`).
**Deliverable = curate endpoint WRITE-ACTION vào OAS mirror.** Đây là **nhánh WRITE ĐẦU TIÊN** của màn field-tech "Tiếp nhận & Nghiệm thu hiện trường" — sau `listCommissioning` (§20 list-entry, R35) + `getCommissioning` (§21 detail, R45), field-tech nộp kết quả **checklist đo kiểm cơ sở** (Initial Inspection): mỗi thông số baseline (measured_val / test_result / fail_note) → nếu **không có Fail** thì `overall_inspection_result = "Pass"` + tính `clinical_hold_required` (Class C/D/Radiation). ĐÓNG dead-end flow: KTV mở detail nhưng chưa có endpoint mobile để **hoàn tất đo kiểm**. CONTRACT-ONLY: **backend ĐÃ LIVE** (handler + service — 0 `.py` runtime change / 0 reload / 0 migrate). Curate là **pure-YAML** vào `docs/mobile/openapi/assetcore-mobile.openapi.yaml` + đồng bộ test guard. **Precedent cấu trúc = `submitPmResult`** (`yaml:13628`, action-POST mang child-array `checklist_results[]` + response domain-riêng) — mirror 1:1.

#### 22.0 — Self-Correction (BA quyết định, đọc TRƯỚC khi curate)

- **SC#1 (BẮT BUỘC — factual, wire-type):** acceptance ghi `BaselineChecklistResultInput` **"ĐÚNG 4 prop STRING {parameter, measured_val, test_result, fail_note}"**. **SAI ở `measured_val`.** Field `measured_val` của child doctype `Commissioning Checklist` là **`Float`** (`commissioning_checklist.json`), KHÔNG phải Data/string. Bằng chứng cứng: **OUTPUT schema `BaselineTestItem` (đã LIVE §21, CÙNG module CÙNG field)** khai `measured_val: {type: number, nullable: true}` (ground `_serialize_baseline_tests` `services/imm04.py:685`). Nếu curate INPUT `measured_val: string` → **VỠ read/write parity**: cùng 1 field mà read = `number`, write = `string` ⇒ codegen sinh 2 kiểu Dart/Kotlin lệch cho cùng thuộc-tính → client vỡ. `r.get("measured_val", "")` (`services/imm04.py:1447`) chỉ là **default Python khi absent**, KHÔNG quyết định KIỂU (default `""` gán vào Float, Frappe coerce khi `doc.save`). Web §10 ví dụ cũng gửi số `0.08`. ⇒ **`measured_val` = `type: number, nullable: true`** (KHÔNG string). 3 prop còn lại = string ĐÚNG: `parameter` (Data), `test_result` (Select), `fail_note` (Text). ⇒ **BaselineChecklistResultInput = 3 string + 1 number** (KHÔNG 4 string).
- **SC#2 (design — match-key required):** acceptance im-lặng về `required` của item. Ground: service lập `result_map = {r.get("parameter"): r for r in results}` (`services/imm04.py:1443`) + match `row.parameter in result_map` (`:1445`) ⇒ **`parameter` = KHOÁ MATCH** (dòng thiếu `parameter` bị key dưới `None`, vô-dụng). Mirror precedent `PmChecklistResultInput` `required: [idx]` (khoá match của PM). ⇒ **`BaselineChecklistResultInput.required = [parameter]`**.
- **SC#3 (design — test_result KHÔNG hard-enum):** `test_result` là Select `/Pass/Fail/N/A` **leading-blank** (`""` hợp lệ) ⇒ `type: string` **KHÔNG hard-enum** (mirror `BaselineTestItem.test_result` §21 + ADR-MOBILE-051 §2.c.1: hard-enum reject `""` → strict codegen crash). Mô tả liệt kê value Pass/Fail/N/A + ghi rõ `test_result == "Fail"` (`services/imm04.py:1450`) là dòng kích-hoạt gate BR-04-04.

#### 22.1 — Request: `SubmitBaselineChecklistRequest` (CLOSED, `required: [name]`)

`additionalProperties: false`. Chữ-ký handler `submit_baseline_checklist(name, results="")` (`api/imm04.py:156`) ⇒ **ĐÚNG 2 property**:

| # | Property | Type | Ground |
|---|---|---|---|
| 1 | `name` | string, **required** | Mã phiếu `Asset Commissioning` (positional `api/imm04.py:156`). ∄ ⇒ Error `NOT_FOUND` (`services/imm04.py:1440`); `workflow_state != Initial Inspection` ⇒ Error `INVALID_PARAMS` (`:1442`). |
| 2 | `results` | array, items `$ref BaselineChecklistResultInput`, **default `[]`** | JSON-string convention (mirror PM `checklist_results`) — client gửi JSON-array, BE `_parse_json(results, field_name="results", default=[])` (`api/imm04.py:159`); malformed ⇒ Error trên HTTP-200 (`_err` `api/imm04.py:161`). |

**`BaselineChecklistResultInput`** (CLOSED, `additionalProperties: false`, **`required: [parameter]`** — SC#2). ĐÚNG **4 property** (3 string + 1 number — SC#1), ground `services/imm04.py:1443-1447`:

| # | Property | Type | Ground |
|---|---|---|---|
| 1 | `parameter` | string | Thông số kiểm (Data) — **khoá match** `result_map` (`services/imm04.py:1443,1445`). |
| 2 | `measured_val` | **number, nullable: true** | Giá trị đo (**Float** `commissioning_checklist.json`) — ghi `row.measured_val` (`services/imm04.py:1447`). **SC#1: number KHÔNG string** (parity `BaselineTestItem` §21 output). |
| 3 | `test_result` | string (Select `Pass\|Fail\|N/A`, **KHÔNG hard-enum** — SC#3) | Ghi `row.test_result` (`services/imm04.py:1448`); `== "Fail"` kích gate BR-04-04 (`:1450`). |
| 4 | `fail_note` | string | Ghi chú khi Fail (Text) — ghi `row.fail_note` (`services/imm04.py:1449`). |

#### 22.2 — Response 200: oneOf `[SubmitBaselineChecklistEnvelope, Error]` (Decision-B, closed disjoint required-set)

**`SubmitBaselineChecklistResponse`** (CLOSED, `additionalProperties: false`, `required: [name, overall_result, clinical_hold_required]`). ĐÚNG **3 property**, ground return `services/imm04.py:1456`:

| # | Property | Type | Ground |
|---|---|---|---|
| 1 | `name` | string | Echo `doc.name` (`services/imm04.py:1456`). |
| 2 | `overall_result` | string | **HẰNG `"Pass"`** ở nhánh success (`doc.overall_inspection_result = "Pass"` `:1454`, return `"Pass"` `:1456`) — vì bất kỳ Fail nào đã raise VALIDATION TRƯỚC (`:1452`, tương tự `submitPmResult.new_status` luôn `"Completed"`). Mô tả ghi "luôn `Pass` khi success". |
| 3 | `clinical_hold_required` | **boolean** | **Boolean THẬT** (`check_auto_clinical_hold(doc)` return `bool` `services/imm04.py:405-410` — Class C/D/Radiation). **KHÔNG** Check int-0/1 ⇒ **KHÔNG** áp CR-01 coercion `type:integer`; đây là `type: boolean` như `is_locked`/`is_late` (phân biệt với 4 cờ Check `type:integer` của `CommissioningDetail` §21). |

**`SubmitBaselineChecklistEnvelope`** (CLOSED, `additionalProperties: false`, `required: [success, data]`): `success: {type: boolean, enum: [true]}` + `data: $ref SubmitBaselineChecklistResponse`. Mirror `PmSubmitResultEnvelope` (`yaml:6264`).

> 🔜 **POST-BE re-mirror (backlog mobile-mirror owner — CR-25c-followup):** BR-04-04 hardening (`04_Backend_Design.md §5.3` · ADR-IMM-04-02) đổi `submit_baseline_checklist` service trả **4-key** thêm `tests_recorded` (integer, số phép đo THỰC ghi). Response hiện mirror ở đây = CLOSED **3-key** cite `imm04.py:1456` (chữ ký cũ). Khi BE land: re-introspect `@source` (dòng return mới) → thêm `tests_recorded: {type: integer}` vào `SubmitBaselineChecklistResponse` + `required` → bump guard `TestMobileSubmitBaselineChecklistContract` (d) 3-prop → 4-prop. **Chưa curate ngay** (grounded-argspec: chỉ mirror field khi ĐÃ có ở `@source`; hiện service vẫn 3-key). Additive → không breaking codegen. **0 whitelist mới** ⇒ `test_oas_baseline` bất biến.

**Nhánh Error 200-oneOf** gom mọi **lỗi nghiệp vụ in-handler đến HTTP-200** (Decision-B, KHÔNG status-line): `NOT_FOUND` (phiếu∄ `:1440`) · `INVALID_PARAMS` (sai state `:1442`) · **`VALIDATION` BR-04-04** (còn thông số Fail `:1452`) · malformed JSON (`_parse_json` `api/imm04.py:161`). 2 nhánh phân biệt MÁY-ĐỌC bằng closed-schema + disjoint required-set (`Env req[success,data]` vs `Error req[success,error,code,http_status]`) — KHÔNG discriminator (§5c).

#### 22.3 — 401 / 403 (2 loại 403 — SINGLE-SHAPE Forbidden)

- **`401`:** `$ref '#/components/responses/Unauthorized401'` (bearer hết-hạn/invalid → refresh; uniform mobile convention).
- **`403`:** `$ref '#/components/responses/Forbidden'` — **SINGLE-SHAPE** (mirror `submitPmResult`/`createCalibration`, KHÁC `reportIncident` DUAL-403). ⚠️ **2 loại 403 đều về status-line 403 (KHÔNG dual):** (a) **dispatcher-403** guest/no-token trip TRƯỚC `_handle()`; (b) **in-handler cap-403** `rbac.require("commissioning.write")` (`api/imm04.py:157`) → `frappe.throw(..., frappe.PermissionError)` (`services/shared/rbac.py:190-195`) → propagate lên dispatcher → **HTTP-403 status-line THẬT** (KHÁC `reportIncident` dùng `_err(403)` in-handler → HTTP-200 body). ⇒ cả 2 = 1 shape `Forbidden`, KHÔNG khai `403` trong nhánh Error 200-oneOf. **KHÔNG status-line `404`** (NOT_FOUND về qua Error HTTP-200).
- **INVARIANT `count == rows`:** **N/A** — đây là WRITE-action (mutate 1 phiếu), KHÔNG list/drill.

#### 22.4 — Path / operationId / tag / count bump

- **Path:** `POST /api/method/assetcore.api.imm04.submit_baseline_checklist` · **operationId:** `submitBaselineChecklist` (DUY NHẤT — chưa tồn tại) · **tags:** `[commissioning]` (**REUSE** operation-tag đã mở ở §20/§21 — cùng tag `listCommissioning`/`getCommissioning`) · **security:** OAuth2/session · **requestBody:** `required: true`, `content: application/json`, `schema: $ref SubmitBaselineChecklistRequest` (Frappe RPC `/api/method` đọc `form_dict`; client native gửi JSON — 04 §4/§9).
- **Count/opId bump = +1.** Baseline **LIVE 2026-07-15 = 85 path / 85 opId**; `submit_baseline_checklist` **CHƯA có** ⇒ bump **85→86** (path + opId). ⚠️ **Đọc LIVE ngay trước curate** (`grep -cE '^  /api/method' <yaml>`) — count có thể drift do phiên concurrent; bump **live+1** (acceptance ghi 85→86 khớp baseline hiện tại). Delta bất biến: **+1 path · +1 opId · +4 schema** (`BaselineChecklistResultInput`, `SubmitBaselineChecklistRequest`, `SubmitBaselineChecklistResponse`, `SubmitBaselineChecklistEnvelope`) — **0 param mới** (POST body, KHÔNG query param).
- **4 schema mới resolve no-orphan:** `SubmitBaselineChecklistRequest.results.items` → `BaselineChecklistResultInput`; `SubmitBaselineChecklistEnvelope.data` → `SubmitBaselineChecklistResponse`; requestBody → `SubmitBaselineChecklistRequest`; 200-oneOf → `SubmitBaselineChecklistEnvelope` + `Error` (reuse). Mọi `$ref` resolve, 0 dangling, 0 orphan (`test_yaml_loads_all_refs_resolve_no_orphan` + `test_mobile_preflight`).
- **AC5 closed-schema guard:** `additionalProperties: false` trên **CẢ 4 schema mới** → native-pass global closed-schema guard (`test_mobile_docset`), **KHÔNG** thêm OPEN-allowlist. KHÔNG sửa path/schema hiện có (0 blast-radius). **KHÔNG reuse `BaselineTestItem`** (§21) làm input — output có 11 field (idx/unit/is_critical/…) ≠ 4 field write-input; input là schema RIÊNG (mirror PM: `PmChecklistResultInput` ≠ read-checklist).

#### 22.5 — Guard test (RED-before / GREEN-after — KHÔNG "xanh suông")

- **Class MỚI** `TestMobileSubmitBaselineChecklistContract` (`tests/test_mobile_oas.py`, ≥2 TC) mirror `TestMobileSubmit*`/precedent submitPmResult: (a) path `POST …submit_baseline_checklist` + `operationId: submitBaselineChecklist` + `tags:[commissioning]` tồn tại; (b) requestBody `$ref SubmitBaselineChecklistRequest` (required:[name], `results` array $ref, `measured_val` **type:number**, `parameter/test_result/fail_note` string, item required:[parameter], all CLOSED); (c) 200 oneOf ĐÚNG 2 nhánh `[SubmitBaselineChecklistEnvelope, Error]`; (d) `SubmitBaselineChecklistResponse` 3-prop CLOSED (`clinical_hold_required` **type:boolean**); (e) 401 Unauthorized401 + 403 Forbidden; (f) path-count mirror tăng **ĐÚNG +1** (assert đọc-live cũ→mới, KHÔNG hardcode lẻ); (g) 4 schema resolve no-orphan.
- **Count-guard bump `85→86` (≥13 vị trí path/opId trong `test_mobile_oas.py`):** vị trí acceptance nêu 2889/2900/2907/2908/5477/5479/5480/5815/5817/5818/6103/6105/6106 + **grep lại toàn bộ** `len(paths)==85` / `len(ids)==85` → 86; operationId vẫn DUY NHẤT. Đồng bộ counter test-count: `_EXPECTED_TEST_COUNT` (`tests/test_mobile_oas.py`, LIVE 774) `+= N` (số TC class mới); `_GUARD_SUITE_EXPECTED["test_mobile_oas.py"]` · `_GUARD_SUITE_SUM` · `_MOBILE_OAS_TOTAL` (`tests/test_mobile_docset.py`) `+= N`. ⚠️ **Đọc LIVE 4 counter trước bump** (drift đa-phiên).
- **RED→GREEN chứng minh:** chạy guard TRƯỚC curate = **ĐỎ** (path/opId/schema chưa tồn tại); SAU = **XANH THẬT** — `bench --site miyano run-tests` cho `test_mobile_oas` + `test_mobile_docset` + `test_mobile_preflight` = `Ran N OK`, **0 skip**. Xác nhận **0 backend `.py` runtime change** (chỉ yaml + test) → **0 gunicorn reload, 0 migrate**.

#### ADR-IMM04-MOBILE-WRITE-01 (dev mirror sang `ADR-MOBILE-056` — hoặc số kế available; concurrent-drift, dev pin tại curation)

- **Status:** Accepted · **Date:** 2026-07-15
- **Context:** Mobile Trục B mở **nhánh WRITE ĐẦU TIÊN** cho IMM-04 F6 — cần action nộp checklist đo kiểm cơ sở sau list (§20 R35) + detail (§21 R45). Backend `submit_baseline_checklist` đã LIVE (web-FE §10 dùng). Curate contract vào OAS mirror mà 0 đụng `.py`. Acceptance ground 1 điểm sai kiểu vs code LIVE (§22.0 SC#1).
- **Decision:** (1) **SC#1** — `BaselineChecklistResultInput.measured_val` = **`number` nullable:true** (Float `commissioning_checklist.json` + parity output `BaselineTestItem` §21 `services/imm04.py:685`), **KHÔNG** `string`; giữ read/write contract parity. (2) **SC#2** — item `required: [parameter]` (khoá match `result_map` `:1443`; mirror `PmChecklistResultInput.required:[idx]`). (3) **SC#3** — `test_result` = `type:string` **KHÔNG hard-enum** (Select leading-blank). (4) `clinical_hold_required` = **`type:boolean`** THẬT (`check_auto_clinical_hold` → `bool` `:405-410`) — KHÔNG CR-01 int-coerce. (5) 4 schema mới đều **CLOSED** (`additionalProperties:false`); input schema RIÊNG (KHÔNG reuse output `BaselineTestItem`). (6) Slot `{200,401,403}` Decision-B: NOT_FOUND/INVALID_PARAMS/VALIDATION/malformed qua Error HTTP-200; **403 SINGLE-SHAPE** (`rbac.require` → PermissionError → status-line, cả dispatcher-403 lẫn cap-403), KHÔNG status-line 404. (7) Cấu trúc mirror `submitPmResult` (`yaml:13628`).
- **Alternatives:** (a) `measured_val: string` như acceptance — **loại**: field Float + output đã `number` ⇒ vỡ read/write parity, codegen 2 kiểu lệch. (b) reuse `BaselineTestItem` (§21) làm input — **loại**: 11 field output ⊋ 4 field write-input (idx/unit/is_critical/measurement_type/expected_* thừa) → body "nói dối". (c) hard-enum `test_result` `[Pass,Fail,N/A]` — **loại**: leading-blank `""` hợp lệ → reject-valid crash (ADR-MOBILE-051 §2.c.1). (d) `clinical_hold_required: type:integer` (CR-01) — **loại**: return là Python `bool` THẬT, không phải Check int. (e) khai `403` trong nhánh Error 200-oneOf (dual) — **loại**: `rbac.require` raise → status-line, KHÔNG in-handler `_err(403)` như `reportIncident`.
- **Consequences:** +1 path/opId (85→86), +4 schema CLOSED, +0 param, +N TC; 0 `.py`/reload/migrate (pure-YAML — [AUTO], KHÔNG HARD-STOP); count-guard (≥13 vị trí) + 4 test-counter bump ĐỒNG BỘ (đọc live); CLOSED ⇒ native-pass global closed-schema guard (KHÔNG OPEN-allowlist). Working tree để USER review (KHÔNG commit).

#### Boundaries (Always / Never)

- **Always:** curate pure-YAML vào `docs/mobile/openapi/assetcore-mobile.openapi.yaml`; đọc baseline path-count + 4 test-counter **LIVE** trước bump; REUSE `Unauthorized401`/`Forbidden`/`Error` + tag `commissioning` (§20/§21); `additionalProperties:false` MỌI schema mới (4); ground field-set VERBATIM từ `services/imm04.py:1437-1456` + `commissioning_checklist.json` — KHÔNG bịa; `measured_val` = **number** (SC#1), item `required:[parameter]` (SC#2); mirror `submitPmResult` (`yaml:13628`); RED-before/GREEN-after chứng minh.
- **Never:** ❌ sửa `.py`/reload/migrate (backend LIVE); ❌ khai `measured_val` là `string` (SC#1 — Float, output đã number); ❌ hard-enum `test_result` (leading-blank `""`); ❌ `clinical_hold_required: integer` (bool THẬT); ❌ reuse `BaselineTestItem` output làm input; ❌ thêm status-line `404` (NOT_FOUND về qua Error HTTP-200); ❌ khai `403` dual trong nhánh Error 200-oneOf (rbac.require raise = status-line SINGLE); ❌ đụng `AssetCommissioningOrigin`/`listCommissioning`/`getCommissioning` schema hiện có (0 blast-radius); ❌ hardcode `85→86`/counter mù (đọc live); ❌ nhận "xanh suông" khi test chưa assert path/schema/SC#1.

> 📱 **Mobile OAS contract (tóm tắt):** curate `docs/mobile/openapi/assetcore-mobile.openapi.yaml` — opId `submitBaselineChecklist`, tag `commissioning`, POST requestBody `$ref SubmitBaselineChecklistRequest` (required, application/json), 200 = oneOf `[SubmitBaselineChecklistEnvelope, Error]` (Decision-B) + 401 `Unauthorized401` + 403 `Forbidden` (SINGLE-SHAPE). **4 schema CLOSED** = `SubmitBaselineChecklistRequest` (name+results, req:[name]) + `BaselineChecklistResultInput` (parameter/measured_val/test_result/fail_note, req:[parameter], CLOSED) + `SubmitBaselineChecklistResponse` (name/overall_result/clinical_hold_required, req all 3) + `SubmitBaselineChecklistEnvelope`. **⚠️ 1 SELF-CORRECTION chính (SC#1):** `measured_val` = **number** (Float, parity `BaselineTestItem` §21) — **KHÔNG string** như acceptance. `clinical_hold_required` = **boolean THẬT** (KHÔNG CR-01 int). CONTRACT-ONLY (backend LIVE `api/imm04.py:155` / `services/imm04.py:1437`, 0 `.py`/reload/migrate). Cấu trúc mirror `submitPmResult` (`yaml:13628`). Quyết định đầy đủ: `ADR-MOBILE-056` (dev tạo) + `docs/mobile/04-api-contract.md` (dev thêm §). ⚠️ Path/opId 85→86 + 4 counter LIVE-drift — đọc live baseline, bump +1/+N.

---

## 3. List / Query endpoints

- `list_commissioning`: endpoint riêng vì cần business filter (whitelist filter keys, default loại cancelled)
- Response luôn trả field denormalized `vendor_name`, `item_name` để FE không cần extra call
- Whitelist filter keys (raw column): `workflow_state, po_reference, master_item, vendor, clinical_dept, docstatus, is_radiation_device, vendor_serial_no, expected_installation_date, final_asset, internal_tag_qr, doa_incident`
- **Virtual filter `overdue=1`** (BR-04-10): KHÔNG phải raw column — khi truyền, AND thêm SoT `overdue_commissioning_filter()` (`reception_date < today−30`, `workflow_state NOT IN terminal`, `docstatus != 2`) vào `safe_filters`, **không clobber** filter khác. `'overdue'` ở whitelist ảo riêng (`_VIRTUAL_FILTER_KEYS`), KHÔNG lọt `_ALLOWED_FILTER_KEYS`. Drill từ KPI card "Quá hạn SLA". **INVARIANT:** `pagination.total` của `list_commissioning({overdue:1})` == `get_dashboard_stats().kpis.overdue_sla` (card == drill rows).
  - Ví dụ: `?filters={"overdue":1}&page=1&page_size=20` → chỉ phiếu quá hạn SLA. Kết hợp được: `{"overdue":1,"clinical_dept":"DEPT-ICU"}` → quá hạn ∩ khoa ICU.

## 4. Webhook / Realtime Events

| Channel | Trigger | Payload |
|---|---|---|
| `imm04_asset_released` | `fire_release_event()` sau Submit | `{event_code: "imm04.release.approved", root_record_id, asset_id, actor, from_state, to_state}` |
| `imm04_notify_purchasing` | Sau release, gửi tới Purchase User role | `{message, commissioning_ref, asset}` |

## 5. Versioning

API hiện tại = v1 (không prefix). Breaking change → suffix `_v2` + deprecate v1 1 release.

## 6. Rate limit

| Endpoint | Limit | Lý do |
|---|---|---|
| `create_commissioning` | 30/min/user | Mutation |
| `submit_commissioning` | 10/min/user | Submit action |
| `list_commissioning` | 300/min/user | Read |
| `check_sn_unique` | 120/min/user | On-blur realtime check |

## 7. Smoke test playbook

```bash
# 1. Lấy chi tiết phiếu
curl 'http://site/api/method/assetcore.api.imm04.get_form_context?name=ACC-26-04-00001' \
  -H 'Authorization: token key:secret'

# 2. Kiểm tra serial unique
curl 'http://site/api/method/assetcore.api.imm04.check_sn_unique?vendor_sn=PHI-TEST-001&exclude_name=' \
  -H 'Authorization: token key:secret'

# 3. Dashboard stats
curl 'http://site/api/method/assetcore.api.imm04.get_dashboard_stats' \
  -H 'Authorization: token key:secret'

# 4. List 5 phiếu đầu
curl 'http://site/api/method/assetcore.api.imm04.list_commissioning?filters={}&page=1&page_size=5' \
  -H 'Authorization: token key:secret'
```

---

## 11. Notification Contract (BE → FE)

Chuẩn hóa thông báo end-to-end (vòng 5 — cụm Deployment). Mọi lỗi nghiệp vụ raise qua
`nthrow(MSG.IMM04_*)` (service) / `nthrow_in_hook(MSG.IMM04_*)` (DocType hook); API wrap
qua shared `handle`/`parse_json` (`assetcore/utils/api_handler.py`) để auto-hydrate envelope.

### 11.1. Envelope

```jsonc
{
  "severity": "warning",            // success | error | warning | info
  "message_code": "IMM04-DUP-SERIAL",
  "title": "Trùng số serial",        // VI, ngắn
  "message": "VR-01: Serial '{serial}' đã được gán cho Tài sản {asset}.",  // VI, chi tiết
  "action_hint": "Kiểm tra lại serial hoặc tra cứu tài sản hiện hữu.",     // VI, gợi ý hành động
  "context": { "serial": "...", "asset": "..." }
}
```

FE bắt tập trung ở `composables/useApi.ts` → `useNotify.fromError` → toast/modal dùng chung.

### 11.2. Severity rule

| Tình huống | severity | http_status |
|---|---|---|
| Validation input / dữ liệu sai (VR-*) | `warning` | 422 |
| Không tìm thấy bản ghi | `warning` | 404 |
| Sai trạng thái / xung đột state machine | `warning` | 409 |
| Không có quyền (forbidden) | `error` | 403 |
| Lỗi hệ thống unexpected | `error` | 500 |
| Thao tác thành công | `success` | 200 |

### 11.3. Bảng mã MSG.IMM04_*

| message_code | severity | http | Khi nào | Nguồn (service) |
|---|---|---|---|---|
| `IMM04-NOT-FOUND` | warning | 404 | Asset Commissioning không tồn tại | `get_commissioning`, `submit_*` |
| `IMM04-BAD-STATE` | warning | 409 | Thao tác sai trạng thái; hủy ở state không cho phép | `handle_commissioning_cancel` |
| `IMM04-VENDOR-NOT-ASSIGNED` | warning | 422 | Chưa gán NCC khi submit | submit flow |
| `IMM04-DEFECT-BLOCKED` | warning | 422 | Còn lỗi/NC chưa khắc phục | submit flow |
| `IMM04-DUP-SERIAL` | warning | 422 | VR-01: serial trùng (Asset hoặc Phiếu nghiệm thu khác) | `_vr01_unique_serial_number` |
| `IMM04-LIFECYCLE-LOCKED` | warning | 422 | VR-06: nhật ký lifecycle không được sửa (ISO 13485 §4.2.5) | lifecycle validate hook |
| `IMM04-DOC-EXPIRED` | warning | 422 | Tài liệu commissioning đã hết hạn | `_validate_document_expiry` |
| `IMM04-DOCS-INCOMPLETE` | warning | 422 | VR-02 (Gate G01): thiếu tài liệu bắt buộc | gate G01 |
| `IMM04-BASELINE-FAILED` | warning | 422 | VR-03 (Gate G03): còn thông số baseline Fail | `validate_gate_g03` |
| `IMM04-OPEN-NC` | warning | 422 | VR-04 (Gate G05): còn NC chưa đóng | `validate_gate_g05_g06` |
| `IMM04-BOARD-APPROVER-REQUIRED` | warning | 422 | Gate G06: chưa chọn Người phê duyệt BGĐ | `validate_gate_g05_g06` |
| `IMM04-CANCEL-ASSET-ACTIVE` | warning | 409 | Không thể hủy: Tài sản đã kích hoạt | `handle_commissioning_cancel` |
| `IMM04-SUBMIT-SUCCESS` | success | 200 | Đã gửi/submit phiếu nghiệm thu | submit flow |

> Cảnh báo mềm (doc hết hạn <30 ngày, hồ sơ thiếu nhưng cho duyệt sớm) giữ nguyên `frappe.msgprint(alert=True)` — KHÔNG raise; không thuộc envelope error.

### 11.4. BE checklist

- [ ] Import `from assetcore.utils.notify import MSG, nthrow` (hook dùng `nthrow_in_hook`).
- [ ] Mọi `frappe.throw` nghiệp vụ → `nthrow(MSG.IMM04_*)`; bỏ exception class thô.
- [ ] Nếu wrapper bắt `frappe.ValidationError` rồi bọc `ServiceError(VALIDATION,...)` làm rớt
      `message_code`/`severity` → re-`nthrow(MSG.IMM04_*)` để hydrate đầy đủ (bài học vòng 3).
- [ ] `api/imm04.py` dùng shared `handle`/`parse_json`, bỏ `_handle`/`_parse_json` local.
- [ ] Regen FE i18n: `python scripts/gen_fe_messages.py`.

### 11.5. FE checklist

- [ ] Store `stores/imm04.ts` expose `lastApiError` + helper `_captureError`.
- [ ] Action success → `notify.show(MSG.IMM04_*)`; fail → `notify.fromError(store.lastApiError)`.
- [ ] Test store khi phù hợp (vitest).

---

## DoD — File 05 hoàn chỉnh

- [x] API Catalog (§0) liệt kê 33 endpoint — đối chiếu `assetcore/api/imm04.py` (Wave-2)
- [x] Response envelope chuẩn `{"success": true, "data": {...}}` — không `{"message": {...}}`
- [x] Error envelope chuẩn `{"success": false, "error": "msg vi", "code": "CODE"}`
- [x] Type definitions §1.5 đủ TypeScript interfaces
- [x] Mỗi endpoint chính có request schema + response example
- [x] Error code catalog + FE mapping
- [x] Side effects nêu rõ
- [x] Curl ví dụ cho endpoint chính
- [x] Webhook/Realtime events
- [x] Rate limit
- [x] Smoke test playbook
