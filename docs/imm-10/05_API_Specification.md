# IMM-10 — API Specification

| Mục | Giá trị |
|---|---|
| Module | IMM-10 — Hậu kiểm và tuân thủ |
| Đợt | 3 |
| Trạng thái | Skeleton (BE chưa scaffold — request/response shape là placeholder) |
| Cập nhật | 2026-05-10 |

> Endpoint dưới đây là **catalog dự kiến**. Path, request body, response shape, ErrorCode cụ thể sẽ được lock khi scaffold Sprint Wave 3. Tham chiếu CONVENTIONS §3 cho envelope chuẩn.

---

## §0 — Envelope chuẩn

Tất cả endpoint IMM-10 dùng envelope AssetCore (CONVENTIONS §3):

**Success:**
```json
{
  "success": true,
  "data": { ... }
}
```

**Error:**
```json
{
  "success": false,
  "error": "Human-readable message (vi)",
  "code": "IMM10_<ERROR_CODE>"
}
```

ErrorCode catalog: refer `assetcore/services/shared/constants.py`. Code IMM-10 specific sẽ append vào `ErrorCode` enum khi scaffold (KHÔNG được tự đặt code prefix khác).

---

## §1 — Authentication / Permission

- Tất cả endpoint yêu cầu Frappe session auth (`@frappe.whitelist()`).
- Permission gate qua role + `permission_query_conditions` (refer `04_Backend_Design.md` §IV.3).
- Vendor endpoint scope nghiêm: chỉ xem case có `vendor` = vendor của chính user.

---

## §2 — Endpoint Catalog

| # | Method | Path | Mô tả | Roles |
|---|---|---|---|---|
| 1 | POST | `/api/method/assetcore.api.imm10.open_case` | Mở Compliance Case mới | IMM QA Officer |
| 2 | POST | `/api/method/assetcore.api.imm10.find_scope` | Auto-find affected assets | IMM QA Officer |
| 3 | POST | `/api/method/assetcore.api.imm10.lock_scope` | Khoá scope (immutable) | IMM QA Officer |
| 4 | POST | `/api/method/assetcore.api.imm10.send_disclosure` | Gửi công văn regulator + log | IMM Document Officer |
| 5 | POST | `/api/method/assetcore.api.imm10.bulk_create_recall_wo` | Bulk-create recall WO | IMM QA Officer |
| 6 | POST | `/api/method/assetcore.api.imm10.update_action_status` | Cập nhật status từng affected asset | IMM Workshop Lead |
| 7 | POST | `/api/method/assetcore.api.imm10.close_case` | Đóng case (cần BGĐ approve) | IMM Operations Manager |
| 8 | POST | `/api/method/assetcore.api.imm10.run_effectiveness_check` | Đánh dấu check 30/60/90 ngày | IMM QA Officer |
| 9 | GET | `/api/method/assetcore.api.imm10.get_case` | Lấy chi tiết case | All authorized |
| 10 | GET | `/api/method/assetcore.api.imm10.list_cases` | List với filter (state, severity, type) | All authorized |
| 11 | GET | `/api/method/assetcore.api.imm10.list_capa_tracker` | CAPA tracker xuyên module | IMM QA Officer + BGĐ |
| 12 | GET | `/api/method/assetcore.api.imm10.dashboard_summary` | Compliance dashboard | IMM QA Officer + BGĐ |
| 13 | POST | `/api/method/assetcore.api.imm10.subscribe_signal` | Đăng ký signal từ IMM-12/11/09 (internal call) | (System) |

*(Path trên là **dự kiến** theo convention `assetcore.api.imm<NN>.<verb>`. Có thể đổi khi scaffold — refer code thật khi ready.)*

---

## §3 — Endpoint detail (skeleton)

### 3.1 — `open_case`

- **Method:** POST
- **Mô tả:** Tạo Compliance Case mới.
- **Request body:** *(Sprint Wave 3 — sau khi BE scaffold)*
  ```
  {
    case_type: "Recall" | "FSCA" | "PMS Signal",
    severity: "Low" | "Medium" | "High" | "Critical",
    source_ref: { vendor_notice_no? , regulator_doc_no? , internal_signal_ref? },
    scope_criteria: { model? , lot_range? , serial_range? , mfg_date_range? },
    description: string
  }
  ```
- **Response (success):** `{ success:true, data:{ case_no, workflow_state, disclosure_due_at? } }`
- **Possible errors:** `IMM10_INVALID_SOURCE`, `IMM10_INVALID_SCOPE_CRITERIA` *(code chính thức khi scaffold)*.

### 3.2 — `find_scope`

- **Method:** POST
- **Request:** `{ case: case_no }`
- **Response:** `{ success:true, data:{ n_assets, sample:[...], reconcile_notes:[...] } }`
- **Errors:** `IMM10_CASE_NOT_FOUND`, `IMM10_SCOPE_LOCKED`.

### 3.3 — `send_disclosure`

- **Method:** POST
- **Request:** `{ case, regulator: "BoYTe"|"SoYTe", doc_no, doc_pdf_attachment }`
- **Response:** `{ success:true, data:{ disclosure_log_id, sent_at } }`
- **Errors:** `IMM10_ALREADY_DISCLOSED`, `IMM10_NOT_REGULATORY_GRADE`.
- **Side effect:** stop disclosure timer; transition workflow → `Action Pending`.

### 3.4 — `bulk_create_recall_wo`

- **Method:** POST
- **Request:** `{ case, wo_type: "PM"|"Repair", default_priority: "P1"|"P2", action_required: "Replace"|"Repair"|"Quarantine"|"Update Software" }`
- **Response:** `{ success:true, data:{ created:[wo_id...], skipped:[asset_ref...], n_created } }`
- **Idempotent:** re-call không tạo WO trùng (check `case_ref` field trên WO).
- **Errors:** `IMM10_SCOPE_NOT_LOCKED`, `IMM10_NO_ELIGIBLE_ASSETS`.

### 3.5 — `close_case`

- **Method:** POST
- **Request:** `{ case, approver_note }`
- **Response:** `{ success:true, data:{ case_no, closed_at, completion_pct } }`
- **Errors:** `IMM10_INCOMPLETE_ACTIONS`, `IMM10_CAPA_NOT_OPEN` (BR-10-06), `IMM10_NEED_APPROVER`.

*(Detail body/response các endpoint còn lại — Sprint Wave 3.)*

---

## §4 — ErrorCode (placeholder)

ErrorCode chính thức sẽ append vào `assetcore/services/shared/constants.py` (enum `ErrorCode`). Tên code TUÂN THỦ pattern `IMM10_*` snake_case upper. Danh sách tham khảo:

- `IMM10_CASE_NOT_FOUND`
- `IMM10_INVALID_SOURCE`
- `IMM10_INVALID_SCOPE_CRITERIA`
- `IMM10_SCOPE_LOCKED`
- `IMM10_SCOPE_NOT_LOCKED`
- `IMM10_NO_ELIGIBLE_ASSETS`
- `IMM10_ALREADY_DISCLOSED`
- `IMM10_NOT_REGULATORY_GRADE`
- `IMM10_DISCLOSURE_BREACH`
- `IMM10_INCOMPLETE_ACTIONS`
- `IMM10_CAPA_NOT_OPEN`
- `IMM10_NEED_APPROVER`
- `IMM10_PERMISSION_DENIED`

> ⚠️ KHÔNG hard-code chuỗi error trong service. PHẢI dùng `ErrorCode.IMM10_*`. Refer `services/shared/constants.py` để xem pattern.

---

## §5 — Pagination & Filter

`list_cases`, `list_capa_tracker` dùng pagination chuẩn AssetCore (refer `assetcore/utils/pagination.py`):

```
?limit=50&offset=0&filters={"severity":"Critical","workflow_state":"Action Pending"}
```

Response shape:
```json
{
  "success": true,
  "data": {
    "items": [ ... ],
    "total": 123,
    "limit": 50,
    "offset": 0
  }
}
```

---

## §6 — Webhook / Internal call

`subscribe_signal` là internal-only (không expose ra ngoài cluster). Trigger qua doc_events hooks IMM-09/11/12, không qua HTTP.

---

## §7 — Cross-module API surface

IMM-10 expose 1 helper cho IMM-16 consume:

- `assetcore.services.imm10.get_disclosure_breach_cases() -> list[case]` — IMM-16 Rule Engine query để tạo Compliance Finding.

Ngược lại, IMM-10 consume từ IMM-16:

- `assetcore.services.imm16.register_compliance_rule(rule_code, ...)` — IMM-10 đăng ký 4 rule trong `04_Backend_Design.md` §V.

(Cụ thể signature — refer `docs/imm-16/05_API_Specification.md`.)

---

*Cập nhật: 2026-05-10. Skeleton — endpoint shape sẽ lock khi scaffold Sprint Wave 3. Envelope tuân thủ CONVENTIONS §3.*
