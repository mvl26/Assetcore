# 05 — API Specification (IMM-14 Giải nhiệm thiết bị)

| Mục | Giá trị |
|---|---|
| Module | IMM-14 — Giải nhiệm thiết bị |
| Phạm vi | Endpoint catalog + envelope + error code |
| Owner | BE Architect |
| Liên kết | [04 Backend](./04_Backend_Design.md) · [06 Frontend](./06_Frontend_Design.md) |

> From-scratch — endpoint shape (request body, response shape) chốt khi BE scaffold (Sprint W3-1). File này liệt kê **tên endpoint + verb + mô tả + auth + error code** để FE và QA có thể plan trước.

---

## §0. Envelope chuẩn AssetCore

Tất cả endpoint trả JSON theo envelope `CONVENTIONS.md §3`:

```json
// Success
{ "success": true, "data": <object|array> }

// Error
{ "success": false, "error": "<message i18n>", "code": "<ErrorCode>" }
```

Auth mặc định: Frappe session cookie + role-based (`@frappe.whitelist()`). Mọi endpoint đều yêu cầu login.

---

## §1. Endpoint catalog (10 endpoint)

| # | Method | Path | Auth role | Mô tả 1 dòng |
|---|---|---|---|---|
| 1 | POST | `/api/method/assetcore.api.imm14.create_closure` | HTM Engineer | Tạo closure draft từ Decommission Decision |
| 2 | GET | `/api/method/assetcore.api.imm14.get_closure` | All IMM-14 roles | Lấy closure detail |
| 3 | GET | `/api/method/assetcore.api.imm14.list_closure` | All IMM-14 roles | List closure (filter status, asset, period) |
| 4 | POST | `/api/method/assetcore.api.imm14.update_reconciliation` | Storekeeper, Accountant | Cập nhật dòng đối soát (kho hoặc kế toán) |
| 5 | POST | `/api/method/assetcore.api.imm14.sign_sanitization` | DPO | Ký xác nhận sanitization |
| 6 | POST | `/api/method/assetcore.api.imm14.attach_document` | QLCL Officer | Đính kèm biên bản / scan |
| 7 | POST | `/api/method/assetcore.api.imm14.submit_for_approval` | HTM Engineer | Chuyển Reconciling → Pending Approval |
| 8 | POST | `/api/method/assetcore.api.imm14.finalize` | Department Head | Approve → asset = decommissioned |
| 9 | POST | `/api/method/assetcore.api.imm14.request_rollback` | Department Head | Yêu cầu rollback closure (2-step) |
| 10 | POST | `/api/method/assetcore.api.imm14.confirm_rollback` | Accountant | Xác nhận rollback (đảo asset_status) |

Endpoint dashboard tổng hợp (read-only, refer IMM-07 / IMM-16 dashboard service) sẽ tái sử dụng — không tạo riêng trong IMM-14.

---

## §2. Endpoint chi tiết (skeleton)

Ghi chú: request/response body chính xác sẽ chốt sprint W3-1. Skeleton dưới đây cố định **tên field bắt buộc** + envelope, đủ cho FE bắt đầu thiết kế UI.

### 2.1. POST `create_closure`

- **Body**: `{ "decision_no": "<IMM-13 decision>" }`
- **Response success**: `{ success, data: { closure_no, asset_no, workflow_state: "Draft" } }`
- **Error**: `IMM14_DUPLICATE_CLOSURE`, `IMM13_DECISION_NOT_APPROVED`
- **Side effect**: tạo `IMM Asset Closure`, copy snapshot decision metadata.

### 2.2. POST `update_reconciliation`

- **Body**: `{ "closure_no", "lines": [ { "name?", "scope", "ref_doctype?", "ref_name?", "qty_or_amount?", "status", "note?" } ] }`
- **scope ∈** `{spare_stock, book_value, work_order, document}`
- **Response**: `{ success, data: { lines: [...] } }`
- **Error**: `IMM14_LINE_NOT_FOUND`, `IMM14_PERMISSION_DENIED` (role không khớp scope)

### 2.3. POST `sign_sanitization`

- **Body**: `{ "closure_no", "items": [ { "item", "checked", "note?" } ] }`
- Toàn bộ items phải `checked=true` mới ký được.
- **Error**: `IMM14_SANITIZATION_INCOMPLETE`, `IMM14_PERMISSION_DENIED` (chỉ DPO)

### 2.4. POST `submit_for_approval`

- **Body**: `{ "closure_no" }`
- Validate BR-14-01 (7 mục) + BR-14-08.
- **Response**: state Reconciling → Pending Approval.
- **Error**: `IMM14_INCOMPLETE`, `IMM14_PENDING_RECONCILE`, `IMM14_OPEN_WO`, `IMM14_SANITIZATION_REQUIRED`

### 2.5. POST `finalize`

- **Body**: `{ "closure_no" }`
- **Behavior**: validate full + transaction (cập nhật asset, archive IMM-05 docs, lifecycle event).
- **Response**: `{ success, data: { closure_no, workflow_state: "Closed", asset_status: "decommissioned" } }`
- **Error**: `IMM14_INCOMPLETE`, `IMM14_SOD_VIOLATION`, `IMM14_DOCS_ARCHIVE_FAIL`

### 2.6. POST `request_rollback`

- **Body**: `{ "closure_no", "reason" }`
- **Behavior**: state Closed → Rollback Requested. Notify Accountant.
- **Error**: `IMM14_ROLLBACK_EXPIRED`, `IMM14_PERMISSION_DENIED`

### 2.7. POST `confirm_rollback`

- **Body**: `{ "closure_no", "decision": "approve" | "reject" }`
- **Behavior**: nếu approve → đảo asset_status, unarchive IMM-05 docs, lifecycle event `closure_rolled_back`.
- **Error**: `IMM14_ROLLBACK_NOT_REQUESTED`, `IMM14_PERMISSION_DENIED`

### 2.8. GET `list_closure`

- **Query**: `{ status?, asset_no?, year?, disposal_method?, page?, page_size? }`
- **Response**: paginated list, dùng cho dashboard end-of-life và list page.

---

## §3. Error code catalog

Theo `services/shared/constants.py` chuẩn AssetCore. *Code dự kiến cho IMM-14 — chốt khi scaffold.*

| Code | Message i18n key | Ý nghĩa |
|---|---|---|
| `IMM14_INCOMPLETE` | imm14.error.incomplete | Closure thiếu 1+ mục bắt buộc (BR-14-01) |
| `IMM14_SOD_VIOLATION` | imm14.error.sod | Người tạo = người duyệt (BR-14-02) |
| `IMM14_DUPLICATE_CLOSURE` | imm14.error.duplicate | Asset đã có closure active (BR-14-03) |
| `IMM14_ROLLBACK_EXPIRED` | imm14.error.rollback_expired | Quá window (BR-14-04) |
| `IMM14_ROLLBACK_NOT_REQUESTED` | imm14.error.rollback_not_requested | Confirm khi chưa request |
| `IMM14_SANITIZATION_REQUIRED` | imm14.error.sanitization_required | Asset có PHI nhưng chưa ký (BR-14-05) |
| `IMM14_SANITIZATION_INCOMPLETE` | imm14.error.sanitization_incomplete | Item chưa check đủ |
| `IMM14_ASSET_LOCKED` | imm14.error.asset_locked | Asset đã decommissioned (BR-14-06) |
| `IMM14_DOCS_ARCHIVE_FAIL` | imm14.error.docs_archive_fail | Transaction archive IMM-05 fail |
| `IMM14_OPEN_WO` | imm14.error.open_wo | Còn WO mở chưa đóng |
| `IMM14_PENDING_RECONCILE` | imm14.error.pending_reconcile | Còn line đối soát pending |
| `IMM14_LINE_NOT_FOUND` | imm14.error.line_not_found | Reconciliation line không tồn tại |
| `IMM14_PERMISSION_DENIED` | imm14.error.permission | Role không đúng scope |
| `IMM13_DECISION_NOT_APPROVED` | imm13.error.not_approved | Decision IMM-13 chưa approved (cross-ref) |

Tất cả message i18n trong `frontend/src/locales/*.json` và backend dùng `frappe._(...)`.

---

## §4. Webhook / Hook out

| Event | Payload | Subscriber |
|---|---|---|
| `imm14_closure_created` | `{closure_no, asset_no, decision_no}` | IMM-15 (gợi ý đối soát kho) |
| `imm14_asset_closed` | `{closure_no, asset_no, asset_status, decommissioned_on}` | IMM-15 cron, IMM-16 audit, dashboard |
| `imm14_closure_rolled_back` | `{closure_no, asset_no, reason}` | IMM-15, IMM-16 |

---

## §5. Auth & Rate limit

- Tất cả endpoint dùng Frappe session-based auth (cookie + CSRF token theo `assetcore-security` skill).
- Endpoint `finalize`, `confirm_rollback` áp dụng RBAC chặt + log full audit (refer `IMM Audit Trail`).
- Rate limit: theo policy chung Frappe (default 1000 req/h per user). Endpoint `list_closure` cache 60s.

---

---

## §6. Wave 2 MVP — Cổng "Hồ sơ giải nhiệm" — CHỐT (2 endpoint)

> **Self-Correction (2026-06-04):** §1–§5 ở trên là catalog Đợt 3 (`IMM Asset Closure`, 10 endpoint, rollback…). MVP vòng 2 chỉ scaffold **2 endpoint** trên DocType **`Asset Decommission`** (xem `04 §IX`). Error code dùng **semantic `ErrorCode` bucket** (`utils/response.py`) — KHÔNG dùng string `IMM14_*` ở §3.

### §6.1. POST `create_decommission`

`/api/method/assetcore.api.imm14.create_decommission`

- **Auth role:** capability "decommission asset" (Commissioning Manager / Department Head — chốt theo RBAC capability, KHÔNG hardcode role-name; refer `services/shared/rbac.py`).
- **Body:**
```json
{
  "asset": "AST-2024-0007",
  "disposal_method": "Huỷ",
  "decommission_reason": "Thiết bị hết khấu hao, sửa chữa không kinh tế, đã có quyết định thanh lý.",
  "patient_data_sanitized": true,
  "responsible": "manager@hospital.vn",
  "sanitization_note": "Đã format ổ cứng theo NIST 800-88 + huỷ vật lý."
}
```
- **Response success:**
```json
{ "success": true, "data": { "name": "DECOM-2026-0001", "asset": "AST-2024-0007", "workflow_state": "Draft", "docstatus": 0 } }
```
- **Side effect:** tạo `Asset Decommission` docstatus=0. **KHÔNG** đổi `lifecycle_status` asset.
- **Lỗi (envelope error):**
  - `BAD_STATE` — asset đã `Decommissioned` (BR-14-W2-06, terminal).
  - `CONFLICT` — đã có `Asset Decommission` active cho asset (BR-14-W2-07).
  - `BUSINESS_RULE` — thiếu/sai field bắt buộc (BR-14-W2-02..05).
  - `NOT_FOUND` — asset không tồn tại.

### §6.2. POST `approve_decommission`

`/api/method/assetcore.api.imm14.approve_decommission`

- **Auth role:** capability "approve decommission" (Department Head). SoD: vòng 2 KHÔNG bắt buộc SoD (đó là Đợt 3, BR-14-02) — ghi `[ROADMAP]`.
- **Body:** `{ "name": "DECOM-2026-0001" }`
- **Behavior:** validate `validate_before_approve` → `doc.submit()` (docstatus 0→1) → hook `on_submit` gọi `transition_asset_status(asset, Decommissioned, root_doctype="Asset Decommission", root_record=name, reason=<chứa disposal_method + patient_data_sanitized>)`. Atomic trong 1 transaction Frappe; nếu `transition_asset_status` raise (NEG-09 / gate) → submit roll-back, docstatus giữ 0, `lifecycle_status` asset GIỮ NGUYÊN.
- **Response success:**
```json
{ "success": true, "data": { "name": "DECOM-2026-0001", "workflow_state": "Approved", "docstatus": 1, "asset": "AST-2024-0007", "lifecycle_status": "Decommissioned", "decommissioned_on": "2026-06-04 10:22:01" } }
```
- **Lỗi (envelope error):**
  - `BUSINESS_RULE` — thiếu field bắt buộc / sanitization gate (BR-14-W2-02..05).
  - `BAD_STATE` — asset đã Decommissioned (idempotent: record đã docstatus=1 → no-op success, KHÔNG double effect; record khác cho asset terminal → chặn).
  - `BAD_STATE` (map từ `InvalidAssetTransition`) — NEG-09: asset đang Under Maintenance/Repair/Calibrating → message VI rõ ràng, `lifecycle_status` giữ nguyên.
- **API layer** bắt `InvalidAssetTransition` → trả envelope `{success:false, code:"BAD_STATE", error:<message VI từ exception>}` (KHÔNG để leak "Lỗi hệ thống"/traceback).

### §6.3. Error → ErrorCode map (CHỐT, thay §3 cho MVP)

| Tình huống | ErrorCode bucket | HTTP | message VI mẫu |
|---|---|---|---|
| Thiếu/sai field bắt buộc | `BUSINESS_RULE` | 422 | "Phải chọn phương thức xử lý / nhập lý do ≥ 20 ký tự / chỉ định người chịu trách nhiệm." |
| risk High/Critical mà chưa xác nhận xoá dữ liệu | `BUSINESS_RULE` | 422 | "Thiết bị phân loại C/D bắt buộc xác nhận đã xử lý dữ liệu bệnh nhân (WHO §3.6) trước khi duyệt." |
| Asset đã giải nhiệm (terminal) | `BAD_STATE` | 409 | "Thiết bị đã được giải nhiệm — không thể tạo/duyệt hồ sơ giải nhiệm khác." |
| Đã có hồ sơ giải nhiệm đang xử lý | `CONFLICT` | 409 | "Thiết bị đã có hồ sơ giải nhiệm đang xử lý (DECOM-…)." |
| NEG-09 đang bảo trì/sửa/hiệu chuẩn | `BAD_STATE` | 409 | (message từ `InvalidAssetTransition` — "Không thể thanh lý … khi đang ở trạng thái …") |
| Set Decommissioned không qua closure | `BAD_STATE` | 409 | "Chỉ được giải nhiệm thiết bị qua Hồ sơ giải nhiệm đã duyệt." |
| Asset không tồn tại | `NOT_FOUND` | 404 | "Không tìm thấy thiết bị." |

> message nên raise qua `nthrow(MSG.XXX, **ctx)` để FE có `message_code` + `action_hint`; nếu chưa có MSG entry → tạo trong registry cùng commit BE (refer `assetcore-be/references/notification-contract.md`).

*Hết file 05. §6 là CHỐT cho MVP vòng 2; §1–§5 giữ làm catalog Đợt 3.*
