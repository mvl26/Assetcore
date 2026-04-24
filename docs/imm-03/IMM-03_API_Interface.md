# IMM-03 — API Interface

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-03 — Đánh Giá Nhà Cung Cấp & Quyết Định Mua Sắm |
| Base URL | `/api/method/assetcore.api.imm03` |
| Auth | Frappe session cookie / API key |
| Response format | `{"success": bool, "data": {...}}` hoặc `{"success": false, "error": "...", "code": "..."}` |

---

## Technical Specification Endpoints

### POST `create_technical_spec`

**Request:**
```json
{
  "linked_plan_item": "Procurement Plan Item-001",
  "procurement_plan": "PP-26-00001",
  "equipment_description": "Máy thở ICU",
  "performance_requirements": "FiO2 21–100%, VT 20–2000mL, PEEP 0–35 cmH2O...",
  "safety_standards": "IEC 60601-1, IEC 60601-1-8, ISO 80601-2-12",
  "regulatory_class": "Class B",
  "mdd_class": "Class IIb",
  "warranty_terms": "24 tháng tại chỗ",
  "expected_delivery_weeks": 12
}
```
**Response 200:**
```json
{"success": true, "data": {"name": "TS-26-00001", "status": "Draft"}}
```
**Errors:** `VALIDATION_ERROR` (VR-03-01, VR-03-02)

---

### POST `submit_ts_for_review`

**Request:**
```json
{"name": "TS-26-00001"}
```
**Response:** `{"success": true, "data": {"status": "Under Review"}}`

---

### POST `approve_technical_spec`

**Request:**
```json
{
  "name": "TS-26-00001",
  "review_notes": "Đạt yêu cầu kỹ thuật theo chuẩn IEC"
}
```
**Response:** `{"success": true, "data": {"status": "Approved"}}`
**Errors:** `PERMISSION_ERROR` (role ≠ IMM Technical Reviewer)

---

### POST `resubmit_technical_spec`

_MINOR-01: Ops Manager resubmit TS sau khi nhận feedback (Revised → Under Review)_

**Request:**
```json
{"name": "TS-26-00001"}
```
**Response:** `{"success": true, "data": {"status": "Under Review"}}`
**Errors:** `INVALID_STATE` (TS không ở trạng thái Revised)

---

### GET `get_technical_spec`

`?name=TS-26-00001`

**Response:** Full document dict

---

### GET `list_technical_specs`

`?status=Approved&year=2026&page=1&page_size=20`

**Response:**
```json
{
  "success": true,
  "data": {
    "items": [
      {"name": "TS-26-00001", "equipment_description": "Máy thở ICU",
       "regulatory_class": "Class B", "status": "Approved"}
    ],
    "total": 12, "page": 1
  }
}
```

---

## Vendor Evaluation Endpoints

### POST `create_vendor_evaluation`

**Request:**
```json
{
  "linked_technical_spec": "TS-26-00001",
  "evaluation_method": "RFQ",
  "evaluation_date": "2026-05-10"
}
```
**Response:**
```json
{
  "success": true,
  "data": {
    "name": "VE-26-00001",
    "status": "Draft",
    "linked_plan_item": "Procurement Plan Item-001"
  }
}
```
_MINOR-03: `linked_plan_item` được tự động suy ra từ TS.linked_plan_item — không cần truyền vào._

---

### POST `add_vendor_to_evaluation`

**Request:**
```json
{
  "ve_name": "VE-26-00001",
  "vendor": "ACC-SUPPLIER-00012",
  "quoted_price": 420000000,
  "technical_score": 8.5,
  "financial_score": 7.0,
  "profile_score": 8.0,
  "risk_score": 9.0,
  "compliant_with_ts": 1,
  "has_nd98_registration": 1,
  "notes": "Có kinh nghiệm BV Nhi Đồng 2"
}
```
**Response:**
```json
{
  "success": true,
  "data": {
    "vendor": "ACC-SUPPLIER-00012",
    "total_score": 8.05,
    "score_band": "A (≥8)"
  }
}
```
**Logic:** `total_score = 8.5×0.4 + 7.0×0.3 + 8.0×0.2 + 9.0×0.1 = 8.05`

---

### POST `approve_ve_technical`

_Actor: IMM Technical Reviewer — Step 1 of 2-step VE approval (PATCH-04)_

**Request:**
```json
{"name": "VE-26-00001", "notes": "Đạt tiêu chí kỹ thuật, đủ chứng nhận NĐ98"}
```
**Response:** `{"success": true, "data": {"status": "Tech Reviewed", "tech_reviewed_by": "reviewer@hospital.vn"}}`
**Errors:** `PERMISSION_ERROR` (role ≠ IMM Technical Reviewer)

---

### POST `approve_ve_financial`

_Actor: IMM Finance Officer — Step 2 of 2-step VE approval (PATCH-04)_

**Request:**
```json
{
  "name": "VE-26-00001",
  "recommended_vendor": "ACC-SUPPLIER-00012",
  "selection_justification": "Điểm cao nhất, có đăng ký BYT, kinh nghiệm tại BV Nhi"
}
```
**Response:** `{"success": true, "data": {"status": "Approved", "recommended_vendor": "ACC-SUPPLIER-00012"}}`
**Errors:** `VALIDATION_ERROR` (VR-03-04, VR-03-05), `INVALID_STATE` (VE chưa ở Tech Reviewed)

---

## Purchase Order Request Endpoints

### POST `create_purchase_order_request`

**Request:**
```json
{
  "linked_plan_item": "Procurement Plan Item-001",
  "linked_evaluation": "VE-26-00001",
  "linked_technical_spec": "TS-26-00001",
  "vendor": "ACC-SUPPLIER-00012",
  "equipment_description": "Máy thở ICU Mindray SV300",
  "quantity": 2,
  "unit_price": 210000000,
  "delivery_terms": "CIF Hồ Chí Minh",
  "payment_terms": "30% đặt cọc, 70% khi giao hàng",
  "expected_delivery_date": "2026-08-01",
  "warranty_period_months": 24
}
```
**Response:**
```json
{
  "success": true,
  "data": {
    "name": "POR-26-00001",
    "total_amount": 420000000,
    "requires_director_approval": 0,
    "status": "Draft"
  }
}
```
**Errors:** `VALIDATION_ERROR` (VR-03-06, VR-03-07)

---

### POST `approve_por`

**Request:**
```json
{"name": "POR-26-00001", "notes": "Giá phù hợp ngân sách, đúng vendor đề xuất"}
```
**Response:** `{"success": true, "data": {"status": "Approved", "approved_by": "user@hospital.vn"}}`
**Errors:** `PERMISSION_ERROR` (không đủ thẩm quyền theo threshold 500M)

---

### POST `release_por`

**Request:**
```json
{"name": "POR-26-00001"}
```
**Response:**
```json
{
  "success": true,
  "data": {
    "status": "Released",
    "release_date": "2026-05-20",
    "pp_item_status": "Ordered",
    "imm04_notify": "queued"
  }
}
```
**Side effects:**
- `PP Item.status` → `Ordered` (synchronous)
- `frappe.enqueue(notify_imm04_readiness)` (async, queue=default)
- `Asset Lifecycle Event` ghi `por_released` (domain=imm_planning)

---

### POST `confirm_por_delivery`

_Actor: IMM Storekeeper — xác nhận hàng thực tế về kho. POR → Fulfilled, PP Item → Delivered (PATCH-05)_

**Request:**
```json
{
  "name": "POR-26-00001",
  "delivery_notes": "Đã nhận đủ 2 máy, số seri: SN001, SN002. Kiện hàng nguyên vẹn."
}
```
**Response:**
```json
{
  "success": true,
  "data": {
    "status": "Fulfilled",
    "pp_item_status": "Delivered"
  }
}
```
**Errors:** `PERMISSION_ERROR` (role ≠ IMM Storekeeper), `INVALID_STATE` (POR chưa Released)

---

### GET `get_planning_dashboard_data`

`?year=2026`

**Response:**
```json
{
  "success": true,
  "data": {
    "ts_stats": {"total": 8, "approved": 5, "pending": 3},
    "ve_stats": {"total": 5, "approved": 4},
    "por_stats": {
      "total": 4, "released": 3, "pending_approval": 1,
      "total_value_released": 1680000000,
      "director_required": 1
    },
    "avg_days_to_release": 18,
    "budget_variance_avg_pct": 102.3
  }
}
```
