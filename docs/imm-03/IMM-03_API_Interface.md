# IMM-03 — API Interface

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-03 — Vendor Eval & Procurement Decision |
| Phiên bản | 0.1.0 |
| Ngày cập nhật | 2026-04-29 |
| Trạng thái | DRAFT |
| Base path | `/api/method/assetcore.api.imm03.<endpoint>` |

---

## 1. Conventions

> **⚠ Đọc kèm `docs/WAVE2_ALIGNMENT.md`** — envelope + error code align Wave 1; PO/vendor/asset đã đổi sang DocType `AC Purchase` / `AC Supplier` / `AC Asset`.

- Auth Frappe session / API key.
- Helper: `from assetcore.utils.helpers import _ok, _err`; `from assetcore.services.shared import ErrorCode, ServiceError`.
- Envelope: `{success: true, data}` / `{success: false, error, code}`.
- Error code enum `ErrorCode` (`VALIDATION`, `INVALID_PARAMS`, `BUSINESS_RULE`, `BAD_STATE`, `CONFLICT`, `DUPLICATE`, `NOT_FOUND`, `FORBIDDEN`, `INTERNAL`). Mã VR/Gate xuất hiện trong `error`, không trong `code`.
- Vendor master = custom field bổ sung trên `AC Supplier` (KHÔNG có DocType `IMM Vendor Profile` riêng — xem WAVE2_ALIGNMENT §7).
- PO mint = tạo `AC Purchase` (naming `AC-PUR-.YYYY.-.#####`), KHÔNG dùng ERPNext AC Purchase.
- Audit trail qua `IMM Audit Trail`.

---

## 2. Endpoint catalog (18)

| # | Endpoint | Method | Role | Mục đích |
|---|---|---|---|---|
| 1 | `list_vendor_profiles` | GET | All IMM | List vendor |
| 2 | `get_vendor_profile` | GET | All IMM | Detail |
| 3 | `create_vendor_profile` | POST | ĐT-HĐ-NCC | Tạo profile (link Supplier) |
| 4 | `add_vendor_cert` | POST | ĐT-HĐ-NCC | Thêm chứng chỉ |
| 5 | `list_avl` | GET | All IMM | List AVL |
| 6 | `create_avl_entry` | POST | ĐT-HĐ-NCC | Tạo AVL Draft |
| 7 | `approve_avl` | POST | VP Block1 | Approve AVL |
| 8 | `suspend_avl` | POST | VP Block1 / QA Risk | Suspend |
| 9 | `list_evaluations` | GET | All IMM | List Vendor Evaluation |
| 10 | `add_candidate` | POST | ĐT-HĐ-NCC | Thêm candidate (AVL check) |
| 11 | `submit_quotations` | POST | ĐT-HĐ-NCC | Bulk add quotation |
| 12 | `score_evaluation` | POST | HTM/KH-TC/QA Risk | Update scores by group |
| 13 | `transition_eval_workflow` | POST | role-by-state | Eval transition |
| 14 | `create_decision` | POST | ĐT-HĐ-NCC | Tạo Decision Draft từ Eval |
| 15 | `award_decision` | POST | VP Block1 | Pending Approval → Awarded (mint PO) |
| 16 | `record_contract` | POST | TCKT Officer | Contract Signed substate |
| 17 | `dashboard_kpis` | GET | KH-TC, PTP Khối 1 | KPI 7 chỉ số |
| 18 | `get_vendor_scorecard` | GET | All IMM | Scorecard chi tiết |

---

## 3. Endpoint specs

### 3.1 `create_vendor_profile`

```json
POST {
  "vendor_code": "VINAMED",
  "supplier": "Vinamed JSC",
  "legal_name": "CTCP Vinamed",
  "vat_code": "0301234567",
  "country": "VN",
  "rep_name": "Nguyễn Văn A",
  "rep_phone": "0901234567",
  "rep_email": "a.nguyen@vinamed.vn",
  "device_categories": "Imaging,Life Support",
  "certifications": [
    {"cert_type":"ISO 9001","cert_number":"ISO-9001-2024-VINAMED","issued_date":"2024-01-15","expiry_date":"2027-01-15"}
  ]
}
```

### 3.2 `create_avl_entry` + `approve_avl`

```json
POST create_avl_entry {
  "vendor_profile": "VINAMED",
  "device_category": "Imaging",
  "validity_years": 2,
  "valid_from": "2026-05-01"
}
```

```json
POST approve_avl {
  "name": "AVL-2026-00045",
  "approver": "vp.block1@hospital.vn",
  "approval_doc": "/files/avl-approval-45.pdf"
}
```

Effect: status=Approved, valid_to=valid_from + validity_years; Supplier.imm_avl_status update.

### 3.3 `add_candidate`

```json
POST { "name": "VE-26-00120", "vendor_profile": "HAMILTON-VN" }
```

Response: `{ "row": "abc123", "in_avl": false, "warning": "Vendor non-AVL — cần sign-off VP Block1" }`.

### 3.4 `submit_quotations`

```json
POST {
  "name": "VE-26-00120",
  "quotations": [
    {"candidate_row":"abc123","quotation_no":"QT-2026-001","quotation_date":"2026-05-10","quotation_validity":"2026-07-10","price":2100000000,"currency":"VND","payment_terms":"30/60","delivery_days":45,"warranty_months":24}
  ]
}
```

### 3.5 `score_evaluation`

```json
POST {
  "name": "VE-26-00120",
  "scorer_role": "HTM",
  "scores_by_candidate": {
    "abc123": {"Spec match":5,"Brand strength":4,"Local support":4},
    "def456": {"Spec match":4,"Brand strength":4,"Local support":5}
  }
}
```

Response: `{ "weighted_scores": {"abc123":4.32,"def456":4.18}, "recommended":"abc123" }`.

### 3.6 `transition_eval_workflow`

```json
POST { "name":"VE-26-00120", "action":"Hoàn tất chấm điểm" }
```

### 3.7 `create_decision`

```json
POST {
  "evaluation_ref":"VE-26-00120",
  "procurement_method":"Đấu thầu rộng rãi",
  "method_legal_basis":""
}
```

### 3.8 `award_decision`

```json
POST {
  "name": "PD-26-00045",
  "winner_candidate": "abc123",
  "awarded_vendor": "Vinamed JSC",
  "awarded_price": 2000000000,
  "funding_source": "NSNN",
  "board_approver": "vp.block1@hospital.vn",
  "contract_doc": "/files/contract-2026-045.pdf"
}
```

Pre: state Pending Approval, G05 pass.
Effect: docstatus=1, state Awarded, PO mint, lifecycle event.
Response: `{ "ac_purchase_ref": "AC-PUR-2026-00112", "envelope_check_pct": 80.0 }`.

Errors:
- `VR-03-04` envelope > 105% chưa giải trình
- `VR-03-05` winner không trong AVL Active + chưa sign-off
- `PO-MINT-FAIL` PO mint thất bại (rollback Decision về Pending Approval)

### 3.9 `record_contract`

```json
POST {
  "name": "PD-26-00045",
  "contract_no": "HD-2026-045",
  "contract_doc": "/files/contract-signed.pdf",
  "signed_date": "2026-06-15"
}
```

### 3.10 `get_vendor_scorecard`

```
GET ?vendor=VINAMED&year=2026&quarter=2
```

Response: KPI rows + overall_score + commentary.

### 3.11 `dashboard_kpis`

```
GET ?period=2026-Q2
```

Response: 7 KPI (mục 10 Module Overview).

---

## 4. Realtime events

| Event | Payload | Subscriber |
|---|---|---|
| `imm03_eval_seeded` | `{name, spec_ref}` | UI ĐT-HĐ-NCC inbox |
| `imm03_decision_awarded` | `{name, po_ref, winner_vendor, plan_line}` | IMM-04 prep listener; IMM-01 plan line update |
| `imm03_avl_expired` | `{vendor_profile, device_category}` | KH-TC dashboard |
| `imm03_audit_finding_critical` | `{vendor_profile, finding_id}` | QA Risk + VP Block1 |

---

## 5. Error catalog

`code` luôn là enum `ErrorCode`.

| Tình huống | code | HTTP | Ví dụ `error` |
|---|---|---|---|
| Số candidate không phù hợp method | `BUSINESS_RULE` | 422 | "VR-03-01: Đấu thầu rộng rãi yêu cầu ≥ 3 candidate" |
| Vendor non-AVL chưa có sign-off | `BUSINESS_RULE` | 422 | "VR-03-02: Vendor non-AVL — cần sign-off IMM Board Approver" |
| Quotation hết hạn | `VALIDATION` | 400 | "VR-03-03: Quotation hết hiệu lực" |
| Awarded > 105% envelope | `CONFLICT` | 409 | "VR-03-04: Awarded > 105% envelope — cần giải trình" |
| Winner không có AVL Active | `BUSINESS_RULE` | 422 | "VR-03-05: Winner phải có AVL Active hoặc Conditional + sign-off" |
| Cấm sửa lifecycle | `BUSINESS_RULE` | 422 | "VR-03-06: Audit trail bất biến" |
| Tech Spec đã có Decision Awarded | `DUPLICATE` | 409 | "VR-03-07: Tech Spec đã có Decision Awarded" |
| G01–G05 Gate fail | `BUSINESS_RULE` | 422 | "G05: Thiếu contract_doc / funding_source / board_approver" |
| Tạo `AC Purchase` thất bại | `INTERNAL` | 500 | "Mint AC Purchase thất bại — Decision rollback về Pending Approval" |
| Transition workflow sai | `BAD_STATE` | 409 | "Transition không hợp lệ với state hiện tại" |
| Không đủ quyền | `FORBIDDEN` | 403 | "Vai trò hiện tại không được Award Decision" |

---

## 6. OpenAPI excerpt

```yaml
openapi: 3.0.3
info: { title: AssetCore IMM-03 API, version: 0.1.0 }
paths:
  /assetcore.api.imm03.award_decision:
    post:
      requestBody:
        content:
          application/json:
            schema:
              type: object
              required: [name, winner_candidate, awarded_vendor, awarded_price, funding_source, board_approver]
              properties:
                name: { type: string }
                winner_candidate: { type: string }
                awarded_vendor: { type: string }
                awarded_price: { type: number }
                funding_source: { type: string, enum: [NSNN, Tài trợ, Xã hội hóa, BHYT, Khác] }
                board_approver: { type: string }
                contract_doc: { type: string }
```

*End of API Interface v0.1.0 — IMM-03*
