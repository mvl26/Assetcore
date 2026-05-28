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
| 15 | `transition_state` | POST | Workflow transition | ✗ |
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
| 04 | POST | /api/method/assetcore.api.imm04.transition_state | Workflow transition (G01–G06) | Primary |
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
| 16 | GET  | /api/method/assetcore.api.imm04.get_form_context | Chi tiết phiếu + allowed transitions | Support |
| 17 | GET  | /api/method/assetcore.api.imm04.list_commissioning | Danh sách phiếu + pagination/filter | Support |
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
```

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
- Tạo `Asset` record (`final_asset`)
- Auto-import hồ sơ sang IMM-05 (`create_initial_document_set`)
- Publish realtime `imm04_asset_released`
- Notify Purchase User role

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

**Response success (all pass):**
```jsonc
{
  "success": true,
  "data": {
    "name": "ACC-26-04-00001",
    "overall_result": "Pass",
    "clinical_hold_required": true
  }
}
```

**Response error (có Fail):**
```jsonc
{
  "success": false,
  "error": "BR-04-04: Thông số sau không đạt: Earth Resistance. Phiếu phải chuyển về Re Inspection.",
  "code": "VALIDATION"
}
```

---

### 13. generate_qr_label — Sinh dữ liệu QR

| Mục | Giá trị |
|---|---|
| Method | GET |
| Path | `/api/method/assetcore.api.imm04.generate_qr_label` |
| Role | All |
| Idempotent | Yes |

**Request:** `?name=ACC-26-04-00001`

**Response success:**
```jsonc
{
  "success": true,
  "data": {
    "qr_value": "BV-CDHA-2026-0001",
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
      "status": "Identification",
      "asset_id": "Chưa có",
      "print_date": "2026-04-18"
    },
    "scan_url": "/app/asset-commissioning/ACC-26-04-00001"
  }
}
```

**Errors:** `BAD_STATE` nếu `internal_tag_qr` chưa được sinh (phiếu chưa qua Identification).

---

### 18. get_dashboard_stats — KPI dashboard

| Mục | Giá trị |
|---|---|
| Method | GET |
| Path | `/api/method/assetcore.api.imm04.get_dashboard_stats` |
| Role | HTM Technician+ (không Vendor Engineer) |
| Idempotent | Yes |

**Response success:**
```jsonc
{
  "success": true,
  "data": {
    "kpis": {
      "pending_count": 12,
      "hold_count": 2,
      "open_nc_count": 3,
      "released_this_month": 8,
      "overdue_sla": 1
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

## 3. List / Query endpoints

- `list_commissioning`: endpoint riêng vì cần business filter (whitelist filter keys, default loại cancelled)
- Response luôn trả field denormalized `vendor_name`, `item_name` để FE không cần extra call
- Whitelist filter keys: `workflow_state, po_reference, master_item, vendor, clinical_dept, docstatus, is_radiation_device, vendor_serial_no`

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
