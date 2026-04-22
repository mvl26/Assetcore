# IMM-04 — API Interface Specification

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-04 — Lắp đặt, Định danh & Kiểm tra Ban đầu |
| Phiên bản | 2.0.0 |
| Ngày cập nhật | 2026-04-18 |
| Trạng thái | LIVE — 31/32 UAT PASS |
| Tác giả | AssetCore Team |
| Base path | `/api/method/assetcore.api.imm04.<function>` |

---

## 1. Authentication

| Phương thức | Header | Dùng cho |
|---|---|---|
| API Token | `Authorization: token <api_key>:<api_secret>` | Server-to-server, integration |
| Session cookie | `Cookie: sid=<session_id>` (kèm `X-Frappe-CSRF-Token` cho POST) | Browser / Vue SPA |

Thiếu / sai credential → HTTP 401. Thiếu role → HTTP 403 với `code = "PERMISSION_DENIED"`.

---

## 2. Response Format

Tất cả endpoint trả `{success, data}` hoặc `{success, error, code}` qua helper `assetcore/utils/helpers.py`.

**Success:**

```json
{ "message": { "success": true, "data": { /* payload */ } } }
```

**Error:**

```json
{ "message": { "success": false, "error": "Thông báo tiếng Việt", "code": "ERROR_CODE" } }
```

Helper:

```python
def _ok(data): return {"success": True, "data": data}
def _err(message, code="ERROR"): return {"success": False, "error": message, "code": code}
```

### 2.1 Error Codes chuẩn

| Code | HTTP gợi ý | Ý nghĩa |
|---|---|---|
| `MISSING_PARAM` | 400 | Thiếu query/body bắt buộc |
| `MISSING_FIELDS` | 400 | Thiếu field bắt buộc trong payload |
| `INVALID_PARAM` | 400 | Param sai schema (filters/data không phải JSON hợp lệ) |
| `INVALID_DATA` | 400 | nc_data / results / fields không parse được |
| `NOT_FOUND` | 404 | Phiếu / NC / PO không tồn tại |
| `PERMISSION_DENIED` | 403 | User không đủ role |
| `FORBIDDEN_DOCTYPE` | 403 | doctype không nằm whitelist `_ALLOWED_DOCTYPES` (search_link) |
| `INVALID_STATE` | 422 | Action không hợp lệ ở workflow_state hiện tại |
| `WRONG_STATE` | 422 | Submit khi state ≠ Clinical_Release |
| `TRANSITION_NOT_ALLOWED` | 422 | Action không nằm trong allowed transitions của user role |
| `VALIDATION_ERROR` | 422 | Vi phạm VR-xx / Gate Gxx |
| `OPEN_NC` | 422 | Còn NC chưa đóng (G05) |
| `DOC_LOCKED` | 422 | Phiếu đã Submit |
| `DOC_CANCELLED` | 422 | Phiếu đã Cancel |
| `ALREADY_SUBMITTED` | 422 | Submit phiếu đã docstatus=1 |
| `QR_NOT_GENERATED` | 422 | Phiếu chưa có internal_tag_qr |
| `PDF_ERROR` | 500 | Lỗi sinh PDF Biên bản |
| `SYSTEM_ERROR` | 500 | Exception không xác định |
| `CREATE_ERROR` | 500 | Lỗi insert NC |
| `SEARCH_ERROR` | 500 | Lỗi query autocomplete |

---

## 3. Endpoints (17)

Module: `assetcore.api.imm04`

### 3.1 Form & List

#### 3.1.1 `get_form_context` — Document đầy đủ + workflow allowed transitions

| Thuộc tính | Giá trị |
|---|---|
| Method | GET |
| Path | `assetcore.api.imm04.get_form_context` |
| Permission | `read` trên Asset Commissioning |

**Params:** `?name=IMM04-26-04-00001`

**Response 200:**

```json
{
  "success": true,
  "data": {
    "name": "IMM04-26-04-00001",
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
    "baseline_tests": [{ "idx": 1, "parameter": "Leakage Current", "test_result": "Pass", "measured_val": 0.08, "unit": "mA" }],
    "commissioning_documents": [{ "idx": 1, "doc_type": "CO", "is_mandatory": 1, "status": "Received", "file_url": "/private/files/co.pdf" }],
    "lifecycle_events": [{ "event_type": "Identification", "from_status": "Installing", "to_status": "Identification", "actor": "biomed@hospital.vn", "event_timestamp": "2026-04-18 09:00:00" }],
    "allowed_transitions": [{ "action": "Bắt đầu kiểm tra", "next_state": "Initial Inspection", "allowed_role": "Biomed Engineer" }],
    "is_locked": false,
    "current_user_roles": ["Biomed Engineer"]
  }
}
```

**Errors:** 404 `NOT_FOUND`, 403 `PERMISSION_DENIED`, 400 `MISSING_PARAM`.

---

#### 3.1.2 `list_commissioning` — Paginated list với filters

| Method | GET | Path | `assetcore.api.imm04.list_commissioning` |
|---|---|---|---|

**Params:** `filters` (JSON), `page` (default 1), `page_size` (default 20, max 100).

Whitelist filter keys: `workflow_state, po_reference, master_item, vendor, clinical_dept, docstatus, is_radiation_device, doa_incident, vendor_serial_no, internal_tag_qr, expected_installation_date, final_asset`.

Default: `docstatus != 2` (loại Cancelled).

**Response 200:**

```json
{
  "success": true,
  "data": {
    "items": [{ "name": "IMM04-26-04-00001", "workflow_state": "Identification", "vendor": "Philips", "modified": "2026-04-18 10:00" }],
    "pagination": { "page": 1, "page_size": 20, "total": 1, "total_pages": 1 }
  }
}
```

---

### 3.2 Create & Save

#### 3.2.1 `create_commissioning`

| Method | POST | Path | `assetcore.api.imm04.create_commissioning` |
|---|---|---|---|

**Body:** `{ "data": { ... } }`. Required: `po_reference, master_item, vendor, clinical_dept, expected_installation_date`.

`vendor_serial_no` set ở bước Identification (không yêu cầu lúc tạo).

Service `initialize_commissioning()` tự: set `reception_date=today`, fetch `risk_class` từ Item, populate mandatory docs (CO, CQ, Manual + License/Radiation License nếu C/D/Radiation).

**Response 200:**

```json
{ "success": true, "data": { "name": "IMM04-26-04-00001", "workflow_state": "Draft", "message": "Phiếu IMM04-26-04-00001 đã được tạo thành công" } }
```

**Errors:** 400 `MISSING_FIELDS`, 422 `VALIDATION_ERROR`, 500 `SYSTEM_ERROR`.

---

#### 3.2.2 `save_commissioning` — Inline edit

| Method | POST | Path | `assetcore.api.imm04.save_commissioning` |
|---|---|---|---|

**Body:** `{ "name", "fields": { /* whitelist */ } }`.

Whitelist top-level: `vendor_engineer_name, qa_license_doc, site_photo, installation_evidence, custom_moh_code, risk_class, reception_date, clinical_head, qa_officer, board_approver, facility_checklist_pass, overall_inspection_result, handover_doc, radiation_license_no, notes`.

Cũng nhận `baseline_tests[]` và `commissioning_documents[]` (update theo `idx`).

Block nếu `docstatus = 1` → `DOC_LOCKED`.

---

### 3.3 Workflow

#### 3.3.1 `transition_state`

| Method | POST | Path | `assetcore.api.imm04.transition_state` |
|---|---|---|---|

**Body:** `{ "name", "action" }` (action là tiếng Việt theo workflow JSON, ví dụ "Xác nhận đủ tài liệu", "Giữ lâm sàng", "Phê duyệt phát hành").

Validate action ∈ allowed transitions (state hiện tại × user roles). Apply qua `frappe.model.workflow.apply_workflow()`.

**Response 200:**

```json
{ "success": true, "data": { "name": "...", "action_applied": "Xác nhận đủ tài liệu", "new_state": "To Be Installed", "docstatus": 0 } }
```

**Errors:** 422 `TRANSITION_NOT_ALLOWED`, 422 `VALIDATION_ERROR` (gate fail), 500 `SYSTEM_ERROR`.

---

#### 3.3.2 `submit_commissioning`

| Method | POST | Path | `assetcore.api.imm04.submit_commissioning` |
|---|---|---|---|

Chỉ role `VP Block2` hoặc `Workshop Head`. Yêu cầu `workflow_state = "Clinical_Release"` (lưu ý dấu underscore trong API) và `docstatus = 0`.

Trigger `on_submit` chain: validate → `mint_core_asset()` → `create_initial_document_set()` → `_log_lifecycle_event` → `fire_release_event`.

**Response 200:**

```json
{ "success": true, "data": { "name": "...", "docstatus": 1, "final_asset": "ACC-ASS-2026-00001", "message": "..." } }
```

**Errors:** 403 `PERMISSION_DENIED`, 422 `WRONG_STATE`, 422 `ALREADY_SUBMITTED`, 422 `DOC_CANCELLED`, 422 `VALIDATION_ERROR`.

---

#### 3.3.3 `approve_clinical_release`

| Method | POST | Path | `assetcore.api.imm04.approve_clinical_release` |
|---|---|---|---|

**Body:** `{ "commissioning", "board_approver", "approval_remarks" }`.

Yêu cầu state = "Clinical Release". Validate `board_approver` (G06) + count Open NC = 0 (G05/VR-04). Append remarks vào `notes`. Gọi `doc.submit()`.

**Response 200:**

```json
{
  "success": true,
  "data": {
    "commissioning": "IMM04-26-04-00001",
    "new_status": "Clinical Release",
    "asset_ref": "ACC-ASS-2026-00001",
    "commissioning_date": "2026-04-18",
    "pm_schedule_created": false,
    "device_record_queued": true
  }
}
```

**Errors:** 422 `INVALID_STATE`, 422 `VALIDATION_ERROR` (board_approver), 422 `OPEN_NC`.

---

### 3.4 Identification & Inspection

#### 3.4.1 `assign_identification`

| Method | POST | Path | `assetcore.api.imm04.assign_identification` |
|---|---|---|---|

**Body:** `{ "name", "vendor_serial_no", "internal_tag_qr", "custom_moh_code" }`.

Yêu cầu state = "Identification". Validate VR-01 (SN unique).

**Response 200:** `{ "name", "vendor_serial_no", "internal_tag_qr" }`

**Errors:** 422 `INVALID_STATE`, 422 `VALIDATION_ERROR` (SN trùng).

---

#### 3.4.2 `check_sn_unique`

| Method | GET | Path | `assetcore.api.imm04.check_sn_unique` |
|---|---|---|---|

**Params:** `?vendor_sn=...&exclude_name=...`

**Response 200:**

```json
{ "success": true, "data": { "is_unique": false, "existing_commissioning": "IMM04-26-03-00012", "item": "ITM-XRAY-001" } }
```

---

#### 3.4.3 `submit_baseline_checklist`

| Method | POST | Path | `assetcore.api.imm04.submit_baseline_checklist` |
|---|---|---|---|

**Body:** `{ "name", "results": [ { "parameter", "measured_val", "test_result", "fail_note" } ] }`.

Yêu cầu state = "Initial Inspection". BR-04-04: nếu có Fail → trả `VALIDATION_ERROR`.

Sau khi Pass: gọi `check_auto_clinical_hold()`. Set `overall_inspection_result = "Pass"`.

**Response 200:**

```json
{ "success": true, "data": { "name": "...", "overall_result": "Pass", "clinical_hold_required": true } }
```

---

#### 3.4.4 `clear_clinical_hold`

| Method | POST | Path | `assetcore.api.imm04.clear_clinical_hold` |
|---|---|---|---|

**Body:** `{ "name", "license_no" }`.

Yêu cầu state = "Clinical Hold". Bắt buộc `qa_license_doc` đã upload hoặc `license_no` truyền vào (BR-04-05).

---

### 3.5 Documents & QR

#### 3.5.1 `upload_document`

| Method | POST | Path | `assetcore.api.imm04.upload_document` |
|---|---|---|---|

**Body:** `{ "commissioning", "doc_index", "doc_type", "file_url", "expiry_date", "doc_number" }`.

Update row trong `commissioning_documents`: status=Received, file_url, uploaded_by, uploaded_at. Trả `all_mandatory_received` boolean.

**Response 200:**

```json
{ "success": true, "data": { "commissioning": "...", "doc_index": 1, "all_mandatory_received": true } }
```

---

#### 3.5.2 `generate_qr_label`

| Method | GET | Path | `assetcore.api.imm04.generate_qr_label` |
|---|---|---|---|

**Params:** `?name=...`. Yêu cầu `internal_tag_qr` đã có (≥ Identification).

**Response 200:**

```json
{
  "success": true,
  "data": {
    "qr_value": "BV-CDHA-2026-0001",
    "label": {
      "title": "ASSETCORE — NHÃN THIẾT BỊ",
      "commissioning_id": "IMM04-26-04-00001",
      "internal_qr": "BV-CDHA-2026-0001",
      "vendor_serial": "PHI-SN98765",
      "model": "ITM-XRAY-001",
      "vendor": "Philips Healthcare VN",
      "dept": "Khoa CĐHA",
      "moh_code": "QLSP-2026-001",
      "installation_date": "2026-04-18 14:30:00",
      "status": "Identification",
      "asset_id": "Chưa có",
      "print_date": "2026-04-18"
    },
    "scan_url": "/app/asset-commissioning/IMM04-26-04-00001",
    "docs_url": null
  }
}
```

**Errors:** 422 `QR_NOT_GENERATED`.

---

#### 3.5.3 `get_barcode_lookup`

| Method | GET | Path | `assetcore.api.imm04.get_barcode_lookup` |
|---|---|---|---|

**Params:** `?barcode=BV-CDHA-2026-0001` (tra ưu tiên `internal_tag_qr`, fallback `vendor_serial_no`).

**Response 200:** `commissioning_id, workflow_state, docstatus, is_released, device:{...}, asset_id, baseline_tests[]`.

---

#### 3.5.4 `generate_handover_pdf`

| Method | GET | Path | `assetcore.api.imm04.generate_handover_pdf` |
|---|---|---|---|

Yêu cầu state = "Clinical Release". Trả URL `/api/method/frappe.utils.pdf.get_pdf?...&format=Biên+bản+Bàn+giao`.

⚠️ Print Format chưa được config trong Frappe — endpoint trả URL nhưng PDF có thể fail (TODO).

---

### 3.6 Lookup & Auto-fill

#### 3.6.1 `get_po_details`

| Method | GET | Path | `assetcore.api.imm04.get_po_details` |
|---|---|---|---|

**Params:** `?po_name=PO-2026-00023`.

**Response 200:** `{ "po_name", "supplier", "supplier_name", "transaction_date", "items": [{ "item_code", "item_name", "qty", "is_radiation" }] }`.

---

#### 3.6.2 `search_link` — Autocomplete cho Link fields

| Method | GET | Path | `assetcore.api.imm04.search_link` |
|---|---|---|---|

**Params:** `?doctype=Purchase Order&query=PO-2026&page_length=10`.

DocType cho phép: `Purchase Order, Item, Supplier, Department`. Khác → `FORBIDDEN_DOCTYPE`.

**Response 200:** `[{ "value", "label", "description" }]`.

---

### 3.7 Non-Conformance

#### 3.7.1 `report_nonconformance`

| Method | POST | Path | `assetcore.api.imm04.report_nonconformance` |
|---|---|---|---|

**Body:** `{ "commissioning_name", "nc_data": { "nc_type", "severity", "description" } }`.

Tạo `Asset QA Non Conformance` (autoname `NC-YY-MM-#####`) với `resolution_status = "Open"`, `ref_commissioning` link.

---

#### 3.7.2 `report_doa`

| Method | POST | Path | `assetcore.api.imm04.report_doa` |
|---|---|---|---|

**Body:** `{ "commissioning", "description", "evidence_file" }`.

Shortcut: tạo NC với `nc_type="DOA"`, `severity="Critical"`. User tự transition `Báo cáo DOA` để vào state Non Conformance.

---

#### 3.7.3 `close_nonconformance`

| Method | POST | Path | `assetcore.api.imm04.close_nonconformance` |
|---|---|---|---|

**Body:** `{ "nc_name", "root_cause", "corrective_action" }`. Cả 2 evidence bắt buộc.

Set `resolution_status="Closed"`, `closed_by=session.user`, `closed_date=today`.

---

### 3.8 Dashboard

#### 3.8.1 `get_dashboard_stats`

| Method | GET | Path | `assetcore.api.imm04.get_dashboard_stats` |
|---|---|---|---|

**Response 200:**

```json
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
      { "workflow_state": "Identification", "count": 5 },
      { "workflow_state": "Initial Inspection", "count": 4 }
    ],
    "recent_list": [{ "name": "IMM04-26-04-00001", "workflow_state": "Identification", "modified": "..." }]
  }
}
```

`overdue_sla`: `expected_installation_date < today - 30 ngày` AND state không terminal.

---

## 4. Webhook / Realtime Events

| Channel | Trigger | Payload |
|---|---|---|
| `imm04_asset_released` | `fire_release_event()` sau Submit | `{ event_code: "imm04.release.approved", root_record_id, asset_id, actor, from_state: "Re_Inspection", to_state: "Clinical_Release", immutable: true }` |
| `imm04_notify_purchasing` | Sau release, gửi tới mọi user có role `Purchase User` | `{ message, commissioning_ref, asset }` |

---

## 5. Permission Matrix tổng hợp

| Endpoint | HTM Tech | Biomed Eng | Vendor Eng | QA Officer | Workshop Head | VP Block2 | CMMS Admin |
|---|---|---|---|---|---|---|---|
| `get_form_context`, `list_commissioning` | R | R | R (own) | R | R | R | R |
| `create_commissioning` | W | W | — | — | — | — | W |
| `save_commissioning` | W | W | — | W | — | — | W |
| `transition_state` | role-checked | | | | | | |
| `assign_identification`, `submit_baseline_checklist` | — | W | — | — | — | — | W |
| `clear_clinical_hold` | — | — | — | W | — | — | W |
| `report_nonconformance`, `report_doa` | W | W | W | — | W | — | W |
| `close_nonconformance` | — | W | — | W | W | — | W |
| `approve_clinical_release` | — | — | — | — | — | W | W |
| `submit_commissioning` | — | — | — | — | W | W | — |
| `generate_qr_label`, `get_barcode_lookup` | R | R | R | R | R | R | R |
| `get_dashboard_stats` | R | R | — | R | R | R | R |
| `generate_handover_pdf` | R | W | — | — | R | R | R |
| `get_po_details`, `search_link`, `check_sn_unique` | R | R | R | R | R | R | R |

---

## 6. Implementation Notes

- Module Python: `assetcore/api/imm04.py` (~1200 dòng); chỉ là wrapper — business logic ở `services/imm04.py`.
- Helper response: `from assetcore.utils.helpers import _ok, _err`.
- Workflow apply: `frappe.model.workflow.apply_workflow(doc, action)` rồi `doc.save()`.
- Mọi exception bọc qua `try/except frappe.ValidationError` → trả `VALIDATION_ERROR`; `Exception` → log + `SYSTEM_ERROR`.
- Filter list whitelist key tránh SQL injection qua field name.
- Pagination cap `page_size = 100`.

*End of API Interface v2.0.0 — IMM-04*
