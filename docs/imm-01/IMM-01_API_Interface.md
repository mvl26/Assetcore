# IMM-01 — API Interface

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-01 — Đánh giá nhu cầu và dự toán |
| Phiên bản | 0.1.0 |
| Ngày cập nhật | 2026-04-29 |
| Trạng thái | DRAFT |
| Base path | `/api/method/assetcore.api.imm01.<endpoint>` |

---

## 1. Conventions

> **⚠ Đọc kèm `docs/WAVE2_ALIGNMENT.md`** — bộ docs này được hiệu chỉnh khớp Wave 1 LIVE. Mọi điểm dưới đây đã align với `assetcore/utils/helpers.py` + `assetcore/services/shared/constants.py`.

- Authentication: Frappe session cookie hoặc `Authorization: token <api_key>:<api_secret>`.
- Content-Type: `application/json`.
- Helper chuẩn: `from assetcore.utils.helpers import _ok, _err`; `from assetcore.services.shared import ErrorCode, ServiceError`.
- Tất cả response theo envelope Wave 1:
  ```json
  // success
  { "success": true, "data": { ... } }
  // error
  { "success": false, "error": "Mô tả lỗi tiếng Việt", "code": "VALIDATION" }
  ```
- Error codes (enum `ErrorCode`): `VALIDATION` · `INVALID_PARAMS` · `BUSINESS_RULE` · `BAD_STATE` · `CONFLICT` · `DUPLICATE` · `NOT_FOUND` · `FORBIDDEN` · `UNAUTHORIZED` · `RATE_LIMITED` · `INTERNAL`.
- Mã VR/Gate (`VR-01-02`, `G01`, ...) chỉ xuất hiện trong `error` message + log; `code` luôn là enum chuẩn.
- Tất cả endpoint mutating ghi audit qua `IMM Audit Trail` (không có DocType `Needs Lifecycle Event` riêng).

---

## 2. Endpoint catalog (14)

| # | Endpoint | Method | Role | Mục đích |
|---|---|---|---|---|
| 1 | `list_needs_requests` | GET | All IMM roles | List + filter Needs Request |
| 2 | `get_needs_request` | GET | All IMM roles | Detail 1 phiếu |
| 3 | `create_needs_request` | POST | Department User, Clinical Head | Tạo Draft |
| 4 | `update_needs_request` | POST | Owner / Clinical Head (Draft/Reviewing) | Edit |
| 5 | `submit_needs_request` | POST | Clinical Head | Draft → Submitted |
| 6 | `score_needs_request` | POST | HTM Reviewer / KH-TC Officer | Update scoring rows |
| 7 | `compute_priority` | POST | HTM Reviewer / KH-TC | Recompute weighted_score |
| 8 | `submit_budget_estimate` | POST | TCKT Officer | Add budget_lines, set funding_source |
| 9 | `transition_workflow` | POST | role-by-state | Chạy 1 transition cụ thể |
| 10 | `approve_needs_request` | POST | VP Block1 / BGĐ | Pending Approval → Approved |
| 11 | `reject_needs_request` | POST | VP Block1 / BGĐ | Reject |
| 12 | `list_procurement_plans` | GET | KH-TC, PTP Khối 1, VP Block1 | List Procurement Plan |
| 13 | `roll_into_plan` | POST | KH-TC Officer | Gom Approved Needs Request vào Plan |
| 14 | `get_demand_forecast` | GET | KH-TC, PTP Khối 1 | Demand Forecast theo năm |
| 15 | `dashboard_kpis` | GET | KH-TC, PTP Khối 1, VP Block1 | KPI 6 chỉ số |

---

## 3. Endpoint specs

### 3.1 `list_needs_requests`

**Request**

```
GET /api/method/assetcore.api.imm01.list_needs_requests
   ?workflow_state=Submitted&requesting_department=ICU&request_type=Replacement
   &page=1&page_size=20&order_by=request_date_desc
```

**Response**

```json
{ "success": true, "data": {
    "items": [
      {
        "name": "IMM01-NR-26-04-00012",
        "request_type": "Replacement",
        "device_model_ref": "IMM-MDL-2024-0007",
        "requesting_department": "ICU",
        "quantity": 2,
        "weighted_score": 4.32,
        "priority_class": "P1",
        "workflow_state": "Submitted",
        "request_date": "2026-04-25",
        "total_capex": 0,
        "tco_5y": 0
      }
    ],
    "total": 87,
    "page": 1,
    "page_size": 20
}}
```

### 3.2 `get_needs_request`

```
GET ?name=NR-26-04-00012
```

Response: full doc + `scoring_rows`, `budget_lines`, `lifecycle_events`, computed fields.

### 3.3 `create_needs_request`

```json
POST {
  "request_type": "Replacement",
  "requesting_department": "ICU",
  "device_model_ref": "IMM-MDL-2024-0007",
  "quantity": 2,
  "target_year": 2027,
  "clinical_justification": "...≥200 chars...",
  "replacement_for_asset": "ASSET-ICU-0014"
}
```

Response: `{ "name": "NR-26-04-00012", "workflow_state": "Draft" }`

Errors:
- `VR-01-02` Replacement requires Decommission Plan
- `VR-01-03` clinical_justification < 200 chars

### 3.4 `submit_needs_request`

```
POST { "name": "NR-26-04-00012" }
```

Pre-conditions: G01 pass.
Effect: workflow_state Draft → Submitted; lifecycle_event ghi.

### 3.5 `score_needs_request`

```json
POST {
  "name": "NR-26-04-00012",
  "scoring_rows": [
    {"criterion": "clinical_impact",  "score": 5, "evidence": "Cứu sinh ICU"},
    {"criterion": "risk",              "score": 5, "evidence": "Class III"},
    {"criterion": "utilization_gap",   "score": 4, "evidence": "Util 92%"},
    {"criterion": "replacement_signal","score": 5, "evidence": "MTBF 40% benchmark"},
    {"criterion": "compliance_gap",    "score": 3, "evidence": "Tuân thủ phần lớn"},
    {"criterion": "budget_fit",        "score": 3, "evidence": "Trong envelope"}
  ]
}
```

Response: `{ "weighted_score": 4.32, "priority_class": "P1" }`.

### 3.6 `submit_budget_estimate`

```json
POST {
  "name": "NR-26-04-00012",
  "budget_lines": [
    {"budget_section":"CAPEX","line_type":"Device","year_offset":0,"qty":2,"unit_cost":1500000000},
    {"budget_section":"CAPEX","line_type":"Install","year_offset":0,"qty":1,"unit_cost":80000000},
    {"budget_section":"OPEX","line_type":"PM","year_offset":1,"qty":4,"unit_cost":15000000},
    ...
  ],
  "funding_source": "NSNN",
  "funding_evidence": "/files/funding-letter-2027.pdf"
}
```

Effect: total_capex, total_opex_5y, tco_5y auto-compute; lifecycle_event "Budgeted".

### 3.7 `transition_workflow`

```json
POST { "name": "NR-26-04-00012", "action": "Hoàn tất chấm điểm" }
```

Server map action → transition theo workflow JSON; trả về `workflow_state` mới hoặc `code: WORKFLOW-INVALID`.

### 3.8 `approve_needs_request`

```json
POST {
  "name": "NR-26-04-00012",
  "board_approver": "vp.block1@hospital.vn",
  "remarks": "Duyệt theo CV 123/BV-2026"
}
```

Pre: state = Pending Approval; G05 pass.
Effect: docstatus = 1, workflow_state = Approved, lifecycle_event "Approved", trigger `roll_into_plan` nếu config auto-roll.

### 3.9 `reject_needs_request`

```json
POST {
  "name": "NR-26-04-00012",
  "rejection_reason": "Trùng đề xuất NR-26-03-00007"
}
```

### 3.10 `list_procurement_plans`

```
GET ?plan_year=2027&plan_period=Annual
```

Response: list Plan với `allocated_capex`, `utilization_pct`, `status_breakdown`.

### 3.11 `roll_into_plan`

```json
POST {
  "plan_year": 2027,
  "plan_period": "Annual",
  "needs_requests": ["NR-26-04-00012","NR-26-04-00013"]
}
```

Effect: tạo / append Procurement Plan; sort plan_items by weighted_score desc; cập nhật `procurement_plan` field trên Needs Request.

### 3.12 `get_demand_forecast`

```
GET ?forecast_year=2027&horizon_years=5&device_category=Imaging
```

Response:

```json
{ "ok": true, "data": {
    "forecast_year": 2027,
    "horizon_years": 5,
    "device_category": "Imaging",
    "matrix": [
      {"year": 2027, "projected_qty": 5, "projected_capex": 7500000000},
      {"year": 2028, "projected_qty": 4, "projected_capex": 6200000000},
      ...
    ],
    "drivers": [
      {"driver_type":"replacement","weight_pct":50,"projected_value":12},
      {"driver_type":"utilization_growth","weight_pct":25,"projected_value":4},
      {"driver_type":"service_expansion","weight_pct":25,"projected_value":3}
    ],
    "accuracy_prev": 0.87
}}
```

### 3.13 `dashboard_kpis`

```
GET ?period=2026-Q2
```

Response: 6 KPI (mục 10 Module Overview) + delta theo kỳ trước.

---

## 4. Webhooks / Realtime events

| Event | Channel | Payload | Subscriber |
|---|---|---|---|
| `imm01_needs_submitted` | publish_realtime | `{name, requesting_department, priority_class}` | PTP Khối 1 dashboard |
| `imm01_needs_approved` | publish_realtime | `{name, plan, allocated_budget}` | KH-TC, IMM-02 trigger |
| `imm01_demand_forecast_published` | publish_realtime | `{forecast_year, horizon}` | IMM-15, IMM-17 |

---

## 5. Error catalog

`code` luôn là enum `ErrorCode`; mã VR/Gate chỉ xuất hiện trong `error` message.

| Tình huống | code (enum) | HTTP | Ví dụ `error` |
|---|---|---|---|
| Trùng Active Replacement Request cho Asset | `DUPLICATE` | 409 | "VR-01-01: Asset đã có Needs Request Replacement Active" |
| Replacement thiếu Decommission Plan IMM-13 | `BUSINESS_RULE` | 422 | "VR-01-02: Replacement yêu cầu Decommission Plan IMM-13" |
| clinical_justification < 200 ký tự | `VALIDATION` | 400 | "VR-01-03: clinical_justification phải ≥ 200 ký tự" |
| target_year < current_year | `VALIDATION` | 400 | "VR-01-04: target_year không được nhỏ hơn năm hiện tại" |
| weighted_score sai số | `VALIDATION` | 400 | "VR-01-05: weighted_score không khớp Σ score×weight" |
| Cấm sửa lifecycle event đã có | `BUSINESS_RULE` | 422 | "VR-01-06: Audit trail bất biến" |
| G01–G05 Gate fail | `BUSINESS_RULE` | 422 | "G01: Cần utilization data 12 tháng trước Submit" |
| Transition workflow không hợp lệ | `BAD_STATE` | 409 | "Transition X không áp dụng cho state Y" |
| Role không đủ quyền | `FORBIDDEN` | 403 | "Vai trò hiện tại không được phép Approve" |
| Không tìm thấy doc | `NOT_FOUND` | 404 | "IMM Needs Request không tồn tại" |
| Tham số API sai dạng | `INVALID_PARAMS` | 400 | "filters không phải JSON hợp lệ" |
| Lỗi server không lường trước | `INTERNAL` | 500 | "Lỗi hệ thống — vui lòng thử lại" |

---

## 6. OpenAPI 3.0 (excerpt)

```yaml
openapi: 3.0.3
info:
  title: AssetCore IMM-01 API
  version: 0.1.0
paths:
  /assetcore.api.imm01.create_needs_request:
    post:
      summary: Create Needs Request (Draft)
      requestBody:
        content:
          application/json:
            schema: { $ref: '#/components/schemas/NeedsRequestCreate' }
      responses:
        '200':
          content:
            application/json:
              schema: { $ref: '#/components/schemas/EnvelopeOk' }
components:
  schemas:
    NeedsRequestCreate:
      type: object
      required: [request_type, requesting_department, device_model_ref, quantity, target_year, clinical_justification]
      properties:
        request_type: { type: string, enum: [New, Replacement, Upgrade, Add-on] }
        requesting_department: { type: string }
        device_model_ref: { type: string }
        quantity: { type: integer, minimum: 1 }
        target_year: { type: integer, minimum: 2026 }
        clinical_justification: { type: string, minLength: 200 }
        replacement_for_asset: { type: string }
    EnvelopeOk:
      type: object
      properties:
        message:
          type: object
          properties:
            ok: { type: boolean, example: true }
            data: { type: object }
```

(File đầy đủ sẽ tạo tại `assetcore/api/openapi/imm01.yaml` khi triển khai.)

*End of API Interface v0.1.0 — IMM-01*
