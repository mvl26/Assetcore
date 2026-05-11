# 05 — API Specification — IMM-01 Đánh giá Nhu cầu & Dự toán

> **Wave 2 — Live.** Tất cả endpoint dưới đây đã được implement tại `assetcore/api/imm01.py` với decorator `@frappe.whitelist()`.

| Mục | Giá trị |
|---|---|
| Module | IMM-01 — Đánh giá nhu cầu và dự toán |
| Base path | `assetcore.api.imm01` |
| URL pattern | `/api/method/assetcore.api.imm01.<function>` |
| Phiên bản | 0.1.0 — Wave 2 Live |

---

## §1 Tổng quan

### §1.1 Response Envelope

**Thành công:**

```json
{
  "success": true,
  "data": { /* payload */ }
}
```

**Lỗi:**

```json
{
  "success": false,
  "error": "Thông báo lỗi tiếng Việt",
  "code": "VALIDATION"
}
```

> Helpers `_ok(data)` / `_err(code, msg)` tại `assetcore/utils/helpers.py`.
> HTTP status luôn là **200** — FE parse `response.json().message.success` để phân biệt.
> Frappe wraps response trong `message`. FE parse: `response.json().message`.

### §1.2 Authentication

| Phương thức | Header / Cookie |
|---|---|
| API Token | `Authorization: token <api_key>:<api_secret>` |
| Session (FE SPA) | `Cookie: sid=<session_id>` |

User không có Role hợp lệ → HTTP 200 + `{success: false, code: "FORBIDDEN"}`.

### §1.3 Phân trang

```json
{
  "success": true,
  "data": {
    "items": [ /* list */ ],
    "total": 87,
    "page": 1,
    "page_size": 20
  }
}
```

`page` 1-based, `page_size` mặc định 20.

### §1.4 API Catalog

| # | Function | Method | Role | Mô tả |
|---|---|---|---|---|
| 3.1 | `list_needs_requests` | GET | All IMM roles | List + filter Needs Request (`filters`, `page`, `page_size`, `order_by`) |
| 3.2 | `get_needs_request` | GET | All IMM roles | Chi tiết 1 phiếu |
| 3.3 | `get_allowed_transitions` | GET | All IMM roles | Trả các workflow action user hiện tại được phép — FE dùng để render nút bấm |
| 3.4 | `create_needs_request` | POST | IMM Clinical User | Tạo Draft (payload JSON) |
| 3.5 | `update_needs_request` | POST | Owner / Clinical Head (Draft only) | Edit phiếu (payload JSON) |
| 3.6 | `submit_needs_request` | POST | IMM Clinical User | Frappe submit (docstatus 0→1) |
| 3.7 | `score_needs_request` | POST | IMM HTM Engineer, IMM Planning Officer | Ghi scoring_rows và recompute weighted_score |
| 3.8 | `submit_budget_estimate` | POST | IMM Finance Officer | Ghi budget_lines, set funding_source / funding_evidence |
| 3.9 | `transition_workflow` | POST | role-by-state | Áp dụng 1 workflow action (`frappe.model.workflow.apply_workflow`) |
| 3.10 | `approve_needs_request` | POST | IMM Board Approver | Pending Approval → Approved (set board_approver, submit) |
| 3.11 | `reject_needs_request` | POST | IMM Board Approver | Pending Approval → Rejected (rejection_reason bắt buộc) |
| 3.12 | `list_procurement_plans` | GET | IMM Planning Officer, IMM Department Head, IMM Board Approver | List Procurement Plan |
| 3.13 | `roll_into_plan` | POST | IMM Planning Officer | Gom Approved NR vào Plan (`plan_year`, `plan_period`, `needs_requests` JSON array) |
| 3.14 | `get_demand_forecast` | GET | IMM Planning Officer, IMM Department Head | Demand Forecast theo `forecast_year` và `device_category` |
| 3.15 | `dashboard_kpis` | GET | IMM Planning Officer, IMM Department Head, IMM Board Approver | KPI: `backlog_over_30d`, `by_state`, `g01_pass_rate`, `envelope_utilization` |

---

## §2 Role Constants

```typescript
// Các Frappe Role áp dụng cho IMM-01 (Wave 2)
const ROLES = {
  CLINICAL_USER:    "IMM Clinical User",        // Wave 1 (reuse)
  HTM_ENGINEER:     "IMM HTM Engineer",          // Wave 2 mới
  PLANNING_OFFICER: "IMM Planning Officer",      // Wave 2 mới
  FINANCE_OFFICER:  "IMM Finance Officer",       // Wave 2 mới
  DEPT_HEAD:        "IMM Department Head",       // Wave 1 (reuse)
  BOARD_APPROVER:   "IMM Board Approver",        // Wave 2 mới
  SYSTEM_ADMIN:     "IMM System Admin",          // Wave 1 (reuse)
} as const
```

---

## §3 Endpoint Specifications

### 3.1 `list_needs_requests`

**Mô tả:** Lấy danh sách Needs Request với filter và phân trang.

| Method | Path |
|---|---|
| GET | `/api/method/assetcore.api.imm01.list_needs_requests` |

**Query params:**

| Param | Kiểu | Mô tả |
|---|---|---|
| `workflow_state` | string | Filter theo state (Draft, Submitted, ...) |
| `requesting_department` | string | Filter theo khoa |
| `request_type` | string | New / Replacement / Upgrade / Add-on |
| `priority_class` | string | P1 / P2 / P3 / P4 |
| `page` | int | Trang hiện tại (mặc định 1) |
| `page_size` | int | Kích thước trang (mặc định 20) |
| `order_by` | string | `request_date_desc` (mặc định) |

**Response 200:**

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "name": "NR-26-04-00012",
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
  }
}
```

---

### 3.2 `get_needs_request`

**Mô tả:** Chi tiết đầy đủ 1 Needs Request.

| Method | Path |
|---|---|
| GET | `/api/method/assetcore.api.imm01.get_needs_request?name=NR-26-04-00012` |

**Response 200:**

```json
{
  "success": true,
  "data": {
    "name": "NR-26-04-00012",
    "request_type": "Replacement",
    "requesting_department": "ICU",
    "device_model_ref": "IMM-MDL-2024-0007",
    "quantity": 2,
    "target_year": 2027,
    "clinical_justification": "...",
    "replacement_for_asset": "ASSET-ICU-0014",
    "utilization_pct_12m": 92.0,
    "downtime_hr_12m": 120.0,
    "weighted_score": 4.32,
    "priority_class": "P1",
    "workflow_state": "Submitted",
    "total_capex": 0,
    "total_opex_5y": 0,
    "tco_5y": 0,
    "scoring_rows": [],
    "budget_lines": [],
    "lifecycle_events": []
  }
}
```

**Lỗi:** `{success: false, error: "IMM Needs Request không tồn tại", code: "NOT_FOUND"}`

---

### 3.3 `create_needs_request`

**Mô tả:** Tạo Needs Request ở trạng thái Draft.

| Method | Path |
|---|---|
| POST | `/api/method/assetcore.api.imm01.create_needs_request` |

**Request body:**

```json
{
  "request_type": "Replacement",
  "requesting_department": "ICU",
  "device_model_ref": "IMM-MDL-2024-0007",
  "quantity": 2,
  "target_year": 2027,
  "clinical_justification": "...≥200 chars...",
  "replacement_for_asset": "ASSET-ICU-0014"
}
```

**Response 200:**

```json
{
  "success": true,
  "data": {
    "name": "NR-26-04-00012",
    "workflow_state": "Draft"
  }
}
```

**Lỗi:**

| Tình huống | code | Ví dụ error |
|---|---|---|
| Replacement thiếu Decommission Plan | `BUSINESS_RULE` | "VR-01-02: Replacement yêu cầu Decommission Plan IMM-13 ở trạng thái Pending/Approved" |
| clinical_justification < 200 ký tự | `VALIDATION` | "VR-01-03: clinical_justification phải ≥ 200 ký tự" |
| target_year < current_year | `VALIDATION` | "VR-01-04: target_year không được nhỏ hơn năm hiện tại" |

---

### 3.4 `submit_needs_request`

**Mô tả:** Chuyển Draft → Submitted (validate G01).

| Method | Path |
|---|---|
| POST | `/api/method/assetcore.api.imm01.submit_needs_request` |

**Request body:**

```json
{ "name": "NR-26-04-00012" }
```

**Response 200:**

```json
{
  "success": true,
  "data": {
    "name": "NR-26-04-00012",
    "workflow_state": "Submitted"
  }
}
```

**Lỗi:** `BUSINESS_RULE` nếu G01 fail (thiếu utilization data cho Replacement/Upgrade).

---

### 3.5 `score_needs_request`

**Mô tả:** Lưu 6 scoring rows và recompute weighted_score.

| Method | Path |
|---|---|
| POST | `/api/method/assetcore.api.imm01.score_needs_request` |

**Request body:**

```json
{
  "name": "NR-26-04-00012",
  "scoring_rows": [
    {"criterion": "clinical_impact",    "score": 5, "evidence": "Cứu sinh ICU"},
    {"criterion": "risk",               "score": 5, "evidence": "Class III"},
    {"criterion": "utilization_gap",    "score": 4, "evidence": "Util 92%"},
    {"criterion": "replacement_signal", "score": 5, "evidence": "MTBF 40% benchmark"},
    {"criterion": "compliance_gap",     "score": 3, "evidence": "Tuân thủ phần lớn"},
    {"criterion": "budget_fit",         "score": 3, "evidence": "Trong envelope"}
  ]
}
```

**Response 200:**

```json
{
  "success": true,
  "data": {
    "weighted_score": 4.32,
    "priority_class": "P1"
  }
}
```

---

### 3.6 `get_allowed_transitions`

**Mô tả:** Trả về các workflow action user hiện tại được phép thực hiện. FE dùng để render nút bấm theo role (tránh "Not a valid Workflow Action" error).

| Method | Path |
|---|---|
| GET | `/api/method/assetcore.api.imm01.get_allowed_transitions?name=NR-26-04-00012` |

**Response 200:**

```json
{
  "success": true,
  "data": {
    "workflow_state": "Submitted",
    "transitions": [
      {"action": "Tiếp nhận rà soát", "next_state": "Reviewing"},
      {"action": "Yêu cầu bổ sung", "next_state": "Draft"}
    ]
  }
}
```

> Note: endpoint dedupe các action trùng (1 row per unique action+next_state pair).

---

### 3.7 `submit_budget_estimate`

**Mô tả:** Lưu budget_lines (CAPEX + OPEX 5y), set funding_source.

| Method | Path |
|---|---|
| POST | `/api/method/assetcore.api.imm01.submit_budget_estimate` |

**Request body:**

```json
{
  "name": "NR-26-04-00012",
  "budget_lines": [
    {"budget_section": "CAPEX", "line_type": "Device",  "year_offset": 0, "qty": 2, "unit_cost": 1500000000},
    {"budget_section": "CAPEX", "line_type": "Install", "year_offset": 0, "qty": 1, "unit_cost": 80000000},
    {"budget_section": "OPEX",  "line_type": "PM",      "year_offset": 1, "qty": 4, "unit_cost": 15000000},
    {"budget_section": "OPEX",  "line_type": "PM",      "year_offset": 2, "qty": 4, "unit_cost": 16000000},
    {"budget_section": "OPEX",  "line_type": "PM",      "year_offset": 3, "qty": 4, "unit_cost": 17000000},
    {"budget_section": "OPEX",  "line_type": "PM",      "year_offset": 4, "qty": 4, "unit_cost": 18000000},
    {"budget_section": "OPEX",  "line_type": "PM",      "year_offset": 5, "qty": 4, "unit_cost": 19000000}
  ],
  "funding_source": "NSNN",
  "funding_evidence": "/files/funding-letter-2027.pdf"
}
```

**Response 200:**

```json
{
  "success": true,
  "data": {
    "total_capex": 3080000000,
    "total_opex_5y": 340000000,
    "tco_5y": 3420000000
  }
}
```

---

### 3.8 `transition_workflow`

**Mô tả:** Chạy 1 workflow action cụ thể.

| Method | Path |
|---|---|
| POST | `/api/method/assetcore.api.imm01.transition_workflow` |

**Request body:**

```json
{ "name": "NR-26-04-00012", "action": "Hoàn tất chấm điểm" }
```

**Response 200:**

```json
{
  "success": true,
  "data": {
    "name": "NR-26-04-00012",
    "workflow_state": "Prioritized"
  }
}
```

**Lỗi:** `BAD_STATE` nếu action không hợp lệ với state hiện tại.

---

### 3.9 `approve_needs_request`

**Mô tả:** VP Block1 phê duyệt NR ở Pending Approval (validate G05).

| Method | Path |
|---|---|
| POST | `/api/method/assetcore.api.imm01.approve_needs_request` |

**Request body:**

```json
{
  "name": "NR-26-04-00012",
  "board_approver": "vp.block1@hospital.vn",
  "remarks": "Duyệt theo CV 123/BV-2026"
}
```

**Response 200:**

```json
{
  "success": true,
  "data": {
    "name": "NR-26-04-00012",
    "workflow_state": "Approved",
    "approval_date": "2026-05-08"
  }
}
```

---

### 3.10 `reject_needs_request`

**Mô tả:** VP Block1 từ chối NR với lý do bắt buộc.

| Method | Path |
|---|---|
| POST | `/api/method/assetcore.api.imm01.reject_needs_request` |

**Request body:**

```json
{
  "name": "NR-26-04-00012",
  "rejection_reason": "Trùng đề xuất NR-26-03-00007"
}
```

**Response 200:** `{ "success": true, "data": { "workflow_state": "Rejected" } }`

**Lỗi:** `VALIDATION` nếu rejection_reason rỗng.

---

### 3.11 `list_procurement_plans`

**Mô tả:** Danh sách Procurement Plan theo năm/kỳ.

| Method | Path |
|---|---|
| GET | `/api/method/assetcore.api.imm01.list_procurement_plans?plan_year=2027&plan_period=Annual` |

**Response 200:**

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "name": "PP-26-001",
        "plan_year": 2027,
        "plan_period": "Annual",
        "budget_envelope": 50000000000,
        "allocated_capex": 38400000000,
        "utilization_pct": 76.8,
        "workflow_state": "Approved",
        "item_count": 12
      }
    ],
    "total": 1,
    "page": 1,
    "page_size": 20
  }
}
```

---

### 3.12 `roll_into_plan`

**Mô tả:** Gom các Approved NR vào Procurement Plan kỳ kế.

| Method | Path |
|---|---|
| POST | `/api/method/assetcore.api.imm01.roll_into_plan` |

**Request body:**

```json
{
  "plan_year": 2027,
  "plan_period": "Annual",
  "needs_requests": ["NR-26-04-00012", "NR-26-04-00013"]
}
```

**Response 200:**

```json
{
  "success": true,
  "data": {
    "plan_name": "PP-26-001",
    "items_added": 2,
    "allocated_capex": 38400000000,
    "utilization_pct": 76.8
  }
}
```

---

### 3.13 `get_demand_forecast`

**Mô tả:** Lấy Demand Forecast theo năm/category.

| Method | Path |
|---|---|
| GET | `/api/method/assetcore.api.imm01.get_demand_forecast?forecast_year=2027&horizon_years=5&device_category=Imaging` |

**Response 200:**

```json
{
  "success": true,
  "data": {
    "forecast_year": 2027,
    "horizon_years": 5,
    "device_category": "Imaging",
    "matrix": [
      {"year": 2027, "projected_qty": 5, "projected_capex": 7500000000},
      {"year": 2028, "projected_qty": 4, "projected_capex": 6200000000},
      {"year": 2029, "projected_qty": 6, "projected_capex": 9300000000},
      {"year": 2030, "projected_qty": 5, "projected_capex": 8000000000},
      {"year": 2031, "projected_qty": 4, "projected_capex": 6500000000}
    ],
    "drivers": [
      {"driver_type": "replacement",       "weight_pct": 50, "projected_value": 12},
      {"driver_type": "utilization_growth","weight_pct": 25, "projected_value": 4},
      {"driver_type": "service_expansion", "weight_pct": 25, "projected_value": 3}
    ],
    "accuracy_prev": 0.87
  }
}
```

---

### 3.14 `dashboard_kpis`

**Mô tả:** KPI tổng hợp IMM-01. `period` là optional (placeholder — v0.1 trả tổng hợp toàn bộ active).

| Method | Path |
|---|---|
| GET | `/api/method/assetcore.api.imm01.dashboard_kpis` |

**Query params:**

| Param | Kiểu | Mô tả |
|---|---|---|
| `period` | string? | `'YYYY-Qx'` — optional, hiện chưa filter |

**Response 200:**

```json
{
  "success": true,
  "data": {
    "backlog_over_30d": 12,
    "by_state": {
      "Draft": 5,
      "Submitted": 8,
      "Reviewing": 3,
      "Prioritized": 4,
      "Budgeted": 2,
      "Pending Approval": 1,
      "Approved": 15,
      "Rejected": 2
    },
    "g01_pass_rate": 96.0,
    "envelope_utilization": 76.8
  }
}
```

> `envelope_utilization` = `allocated_capex / budget_envelope × 100` trên tất cả Plans docstatus=1.

---

## §4 Error Code Catalog

`code` luôn là enum `ErrorCode`; mã VR/Gate chỉ xuất hiện trong `error` message.

| Tình huống | code | Ví dụ `error` |
|---|---|---|
| Trùng Active Replacement Request cho Asset | `DUPLICATE` | "VR-01-01: Asset đã có Needs Request Replacement Active" |
| Replacement thiếu Decommission Plan IMM-13 | `BUSINESS_RULE` | "VR-01-02: Replacement yêu cầu Decommission Plan IMM-13" |
| clinical_justification < 200 ký tự | `VALIDATION` | "VR-01-03: clinical_justification phải ≥ 200 ký tự" |
| target_year < current_year | `VALIDATION` | "VR-01-04: target_year không được nhỏ hơn năm hiện tại" |
| weighted_score không khớp Σ score×weight | `VALIDATION` | "VR-01-05: weighted_score không khớp — hệ thống sẽ tự recompute" |
| Cấm sửa lifecycle event đã có | `BUSINESS_RULE` | "VR-01-06: Audit trail bất biến" |
| G01 thiếu utilization data | `BUSINESS_RULE` | "G01: Cần utilization data 12 tháng cho Replacement/Upgrade trước khi Submit" |
| G02 thiếu scoring row | `BUSINESS_RULE` | "G02: Cần đủ 6/6 tiêu chí chấm điểm trước khi chuyển Prioritized" |
| G03 thiếu OPEX year | `BUSINESS_RULE` | "G03: Budget Estimate phải có cả CAPEX + OPEX 5 năm" |
| G04 vượt envelope | `BUSINESS_RULE` | "G04: Tổng dự toán vượt 100% budget envelope" |
| G05 thiếu board_approver / funding_source | `BUSINESS_RULE` | "G05: board_approver và funding_source bắt buộc trước khi Approve" |
| Transition workflow không hợp lệ | `BAD_STATE` | "Transition 'X' không áp dụng cho state 'Y'" |
| Rejection thiếu reason | `VALIDATION` | "rejection_reason bắt buộc khi Reject" |
| Role không đủ quyền | `FORBIDDEN` | "Vai trò hiện tại không được phép thực hiện thao tác này" |
| Không tìm thấy doc | `NOT_FOUND` | "IMM Needs Request không tồn tại" |
| Tham số API sai dạng | `INVALID_PARAMS` | "Tham số không hợp lệ" |
| Lỗi server | `INTERNAL` | "Lỗi hệ thống — vui lòng thử lại" |

---

## §5 TypeScript Types

File: `frontend/src/types/imm01.ts` — **Đã implement. Xem file thực tế để biết full schema.**

Các type chính:

```typescript
// Actual types — frontend/src/types/imm01.ts

export type RequestType = 'New' | 'Replacement' | 'Upgrade' | 'Add-on'
export type PriorityClass = '' | 'P1' | 'P2' | 'P3' | 'P4'
export type FundingSource = '' | 'NSNN' | 'Tài trợ' | 'Xã hội hóa' | 'BHYT' | 'Khác'

export type NeedsRequestState =
  | 'Draft' | 'Submitted' | 'Reviewing' | 'Prioritized'
  | 'Budgeted' | 'Pending Approval' | 'Approved' | 'Rejected'

export type ProcurementPlanState = 'Draft' | 'Approved' | 'Active' | 'Closed'

export type ScoringCriterion =
  | 'clinical_impact' | 'risk' | 'utilization_gap'
  | 'replacement_signal' | 'compliance_gap' | 'budget_fit'

// Main doc interface
export interface NeedsRequestDoc { /* name, request_type, requesting_department, clinical_head,
  device_model_ref, quantity, target_year, clinical_justification, replacement_for_asset,
  utilization_pct_12m, downtime_hr_12m, compliance_driven, scoring_rows, budget_lines,
  total_capex, total_opex_5y, tco_5y, weighted_score, priority_class,
  funding_source, funding_evidence, board_approver, approval_date, rejection_reason,
  procurement_plan, workflow_state, docstatus */ }

// List item (lighter shape returned by list_needs_requests)
export interface NeedsRequestListItem { /* name, request_type, device_model_ref,
  requesting_department, quantity, weighted_score, priority_class,
  workflow_state, request_date, total_capex, tco_5y */ }

// Dashboard KPIs (returned by dashboard_kpis)
export interface DashboardKpis {
  backlog_over_30d: number
  by_state: Record<string, number>
  g01_pass_rate: number
  envelope_utilization: number
}
```

> **Quan trọng:** Interface `NeedsRequestDoc.clinical_head` là read-only — BE auto-fetch từ `AC Department.dept_head`. FE không gửi field này trong payload create.

---

## §6 Realtime Events

| Event | Channel | Payload | Subscriber |
|---|---|---|---|
| `imm01_needs_submitted` | `publish_realtime` | `{name, requesting_department, priority_class}` | PTP Khối 1 dashboard |
| `imm01_needs_approved` | `publish_realtime` | `{name, plan, allocated_budget}` | KH-TC, IMM-02 trigger |
| `imm01_demand_forecast_published` | `publish_realtime` | `{forecast_year, horizon_years}` | IMM-15, IMM-17 |
