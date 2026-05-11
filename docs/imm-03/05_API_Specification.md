# 05 — Đặc tả API — IMM-03 Đánh giá Nhà cung cấp & Quyết định Mua sắm

> ✅ Module LIVE — Wave 2. Tất cả endpoints đã `@frappe.whitelist()` trong `assetcore/api/imm03.py`.

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-03 — Vendor Evaluation & Procurement Decision |
| Phiên bản | 0.1.0 |
| Ngày | 2026-05-08 |
| Base path | `/api/method/assetcore.api.imm03.<endpoint>` |
| Trạng thái | LIVE — Wave 2 |

---

## 1. Tổng quan

### 1.1 Response Envelope (MANDATORY)

Mọi API của AssetCore dùng envelope sau — KHÔNG dùng `{"message": ...}` của Frappe gốc:

```json
// Thành công
{"success": true, "data": { ... }}

// Thất bại
{"success": false, "error": "Mô tả lỗi tiếng Việt", "code": "ERROR_CODE_ENUM"}
```

HTTP status: **luôn 200**. FE phân biệt thành công/thất bại qua `success`.

### 1.2 Authentication

- Frappe session cookie (browser) hoặc API Key / Secret Header.
- Mọi endpoint yêu cầu login (`@frappe.whitelist()`).

### 1.3 Pagination

```json
{"success": true, "data": {"items": [...], "total": 120, "page": 1, "page_size": 20}}
```

### 1.4 Helper Pattern

```python
from assetcore.utils.helpers import _ok, _err
from assetcore.services.shared import ServiceError, ErrorCode

@frappe.whitelist()
def my_endpoint(**kwargs):
    try:
        result = imm03_service.do_something(**kwargs)
        return _ok(result)
    except ServiceError as e:
        return _err(str(e), e.code)
```

---

## 2. Role Constants & Permission Matrix

```python
# assetcore/constants.py
ROLE_PROCUREMENT  = "IMM Procurement Officer"   # ĐT-HĐ-NCC
ROLE_PLANNING     = "IMM Planning Officer"       # KH-TC
ROLE_HTM_ENGINEER = "IMM HTM Engineer"           # Nhóm HTM
ROLE_FINANCE      = "IMM Finance Officer"        # TCKT
ROLE_RISK         = "IMM Risk Officer"           # QA Risk
ROLE_DEPT_HEAD    = "IMM Department Head"        # PTP Khối 1
ROLE_BOARD        = "IMM Board Approver"         # VP Block1 / BGĐ
ROLE_ADMIN        = "IMM System Admin"           # CMMS Admin
```

| Endpoint | Procurement | Planning | HTM | Finance | Risk | Dept Head | Board | Admin |
|---|---|---|---|---|---|---|---|---|
| `list_vendor_profiles` | R | R | R | R | R | R | R | R |
| `get_vendor_profile` | R | R | R | R | R | R | R | R |
| `create_vendor_profile` | W | — | — | — | — | — | — | W |
| `add_vendor_cert` | W | — | — | — | W | — | — | W |
| `list_avl` | R | R | R | R | R | R | R | R |
| `create_avl_entry` | W | — | — | — | — | — | — | W |
| `approve_avl` | — | — | — | — | — | — | W | W |
| `suspend_avl` | — | — | — | — | W | — | W | W |
| `list_evaluations` | R | R | R | — | R | R | R | R |
| `add_candidate` | W | — | — | — | — | — | — | W |
| `submit_quotations` | W | — | — | — | — | — | — | W |
| `score_evaluation` | — | W(Comm) | W(Tech) | W(Fin) | W(Comp) | — | — | W |
| `transition_eval_workflow` | W | — | — | — | — | W | — | W |
| `create_decision` | W | — | — | — | — | — | — | W |
| `award_decision` | — | — | — | — | — | — | W | W |
| `record_contract` | — | — | — | W | — | — | — | W |
| `dashboard_kpis` | — | R | — | — | — | R | R | R |
| `get_vendor_scorecard` | R | R | R | R | R | R | R | R |

---

## 3. Endpoint Specifications

> **Thực tế vs Spec ban đầu:** Endpoints `list_vendor_profiles`, `get_vendor_profile`, `create_vendor_profile`, `add_vendor_cert` KHÔNG tồn tại trong `api/imm03.py` hiện tại. Vendor Profile management đi qua AC Supplier trực tiếp (ERPNext core). Các endpoints thực tế được implement:
>
> **Vendor Evaluation:** `list_evaluations`, `get_evaluation`, `create_evaluation`, `add_candidate`, `submit_quotations`, `score_evaluation`, `transition_eval_workflow`
>
> **AVL:** `list_avl`, `get_avl`, `create_avl_entry`, `approve_avl`, `suspend_avl`
>
> **Procurement Decision:** `list_decisions`, `get_decision`, `create_decision`, `award_decision`, `record_contract`, `transition_decision_workflow`
>
> **Dashboard:** `dashboard_kpis`, `get_vendor_scorecard`

### 3.1 `list_vendor_profiles` _(Spec only — chưa implement)_

```
GET /api/method/assetcore.api.imm03.list_vendor_profiles
```

**Query params:**

| Param | Type | Default | Mô tả |
|---|---|---|---|
| `avl_status` | string | — | Filter Approved/Conditional/Suspended/Expired |
| `device_category` | string | — | Filter theo nhóm thiết bị |
| `min_score` | float | — | Filter điểm tổng ≥ |
| `audit_overdue` | bool | false | Chỉ hiện vendor quá hạn audit |
| `page` | int | 1 | Trang |
| `page_size` | int | 20 | Kích thước trang |

**Response:**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "name": "VINAMED",
        "supplier_name": "Vinamed JSC",
        "imm_avl_status": "Approved",
        "imm_avl_categories": "Imaging,Life Support",
        "imm_overall_score": 4.3,
        "imm_last_audit_date": "2026-01-15",
        "imm_next_audit_date": "2027-01-15",
        "cert_count": 3,
        "cert_expiring_soon": 1
      }
    ],
    "total": 24,
    "page": 1,
    "page_size": 20
  }
}
```

---

### 3.2 `get_vendor_profile` _(Spec only — chưa implement)_

```
GET /api/method/assetcore.api.imm03.get_vendor_profile?name=VINAMED
```

**Response:**
```json
{
  "success": true,
  "data": {
    "name": "VINAMED",
    "supplier_name": "Vinamed JSC",
    "legal_name": "CTCP Vinamed",
    "vat_code": "0301234567",
    "country": "VN",
    "rep_name": "Nguyễn Văn A",
    "rep_phone": "0901234567",
    "rep_email": "a.nguyen@vinamed.vn",
    "device_categories": "Imaging,Life Support",
    "financial_health": "A",
    "imm_avl_status": "Approved",
    "imm_overall_score": 4.3,
    "certifications": [
      {
        "cert_type": "ISO 9001",
        "cert_number": "ISO-9001-2024-VINAMED",
        "expiry_date": "2027-01-15",
        "status": "Active"
      }
    ],
    "avl_entries": [
      {"name": "AVL-2026-00045", "device_category": "Imaging", "status": "Approved", "valid_to": "2028-04-30"}
    ],
    "scorecard_history": [
      {"period": "2026-Q1", "overall_score": 4.1},
      {"period": "2025-Q4", "overall_score": 4.3}
    ]
  }
}
```

**Errors:**
```json
{"success": false, "error": "Vendor VINAMED không tồn tại", "code": "NOT_FOUND"}
```

---

### 3.3 `create_vendor_profile` _(Spec only — chưa implement)_

```
POST /api/method/assetcore.api.imm03.create_vendor_profile
```

**Request body:**
```json
{
  "supplier": "Vinamed JSC",
  "legal_name": "CTCP Vinamed",
  "vat_code": "0301234567",
  "country": "VN",
  "rep_name": "Nguyễn Văn A",
  "rep_phone": "0901234567",
  "rep_email": "a.nguyen@vinamed.vn",
  "device_categories": "Imaging,Life Support",
  "financial_health": "A",
  "certifications": [
    {
      "cert_type": "ISO 9001",
      "cert_number": "ISO-9001-2024-VINAMED",
      "issued_by": "Bureau Veritas",
      "issued_date": "2024-01-15",
      "expiry_date": "2027-01-15"
    }
  ]
}
```

**Side effects:**
- Cập nhật custom fields trên `AC Supplier`
- Set `imm_avl_status = "Not Applicable"` nếu chưa có AVL

**Response:**
```json
{"success": true, "data": {"name": "VINAMED", "supplier": "Vinamed JSC"}}
```

**Errors:**
```json
{"success": false, "error": "AC Supplier 'Vinamed JSC' không tồn tại trong hệ thống", "code": "NOT_FOUND"}
{"success": false, "error": "VR-03-XX: Thiếu certifications — cần ≥ 1 chứng chỉ ISO 9001 hoặc ISO 13485", "code": "VALIDATION"}
```

---

### 3.4 `create_avl_entry`

```
POST /api/method/assetcore.api.imm03.create_avl_entry
```

**Request body:**
```json
{
  "supplier": "Vinamed JSC",
  "device_category": "Imaging",
  "validity_years": 2,
  "valid_from": "2026-05-01"
}
```

**Response:**
```json
{"success": true, "data": {"name": "AVL-2026-00045", "valid_to": "2028-04-30", "status": "Draft"}}
```

**Errors:**
```json
{"success": false, "error": "validity_years phải từ 1 đến 3", "code": "VALIDATION"}
```

---

### 3.5 `approve_avl`

```
POST /api/method/assetcore.api.imm03.approve_avl
```

**Request body:**
```json
{
  "name": "AVL-2026-00045",
  "approver": "vp.block1@hospital.vn",
  "approval_doc": "/files/avl-approval-45.pdf"
}
```

**Side effects:**
- `avl.status = "Approved"`
- `avl.valid_to = valid_from + relativedelta(years=validity_years)`
- `AC Supplier.imm_avl_status = "Approved"`
- `AC Supplier.imm_avl_categories` thêm device_category

**Response:**
```json
{"success": true, "data": {"name": "AVL-2026-00045", "status": "Approved", "valid_to": "2028-04-30"}}
```

**Errors:**
```json
{"success": false, "error": "Chỉ IMM Board Approver mới có thể phê duyệt AVL", "code": "FORBIDDEN"}
{"success": false, "error": "AVL-2026-00045 đã ở trạng thái Approved", "code": "BAD_STATE"}
```

---

### 3.6 `suspend_avl`

```
POST /api/method/assetcore.api.imm03.suspend_avl
```

**Request body:**
```json
{
  "name": "AVL-2026-00045",
  "suspension_reason": "Audit For-Cause phát hiện vi phạm chất lượng nghiêm trọng"
}
```

**Response:**
```json
{"success": true, "data": {"name": "AVL-2026-00045", "status": "Suspended"}}
```

---

### 3.7 `add_candidate`

```
POST /api/method/assetcore.api.imm03.add_candidate
```

**Request body:**
```json
{
  "name": "VE-26-00120",
  "supplier": "Hamilton Vietnam"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "row": "abc123",
    "supplier": "Hamilton Vietnam",
    "in_avl": false,
    "warning": "Vendor non-AVL cho danh mục Imaging — cần sign-off IMM Board Approver trước khi submit"
  }
}
```

**Errors:**
```json
{"success": false, "error": "IMM Vendor Evaluation VE-26-00120 không ở trạng thái Draft/Open RFQ", "code": "BAD_STATE"}
{"success": false, "error": "Hamilton Vietnam đã là candidate trong VE-26-00120", "code": "DUPLICATE"}
```

---

### 3.8 `submit_quotations`

```
POST /api/method/assetcore.api.imm03.submit_quotations
```

**Request body:**
```json
{
  "name": "VE-26-00120",
  "quotations": [
    {
      "candidate_row": "abc123",
      "quotation_no": "QT-2026-001",
      "quotation_date": "2026-05-10",
      "quotation_validity": "2026-07-10",
      "price": 2100000000,
      "currency": "VND",
      "payment_terms": "30/60",
      "delivery_days": 45,
      "warranty_months": 24,
      "attachment": "/files/qt-vinamed-2026-001.pdf"
    }
  ]
}
```

**Response:**
```json
{"success": true, "data": {"quotations_added": 3, "state": "Quotation Received"}}
```

**Errors:**
```json
{"success": false, "error": "VR-03-03: Quotation QT-2026-001 hết hiệu lực ngày 2026-05-09", "code": "VALIDATION"}
{"success": false, "error": "G02: Chưa đủ ≥ 1 báo giá hợp lệ", "code": "BUSINESS_RULE"}
```

---

### 3.9 `score_evaluation`

```
POST /api/method/assetcore.api.imm03.score_evaluation
```

**Request body:**
```json
{
  "name": "VE-26-00120",
  "scorer_role": "HTM",
  "scores_by_supplier": {
    "Vinamed JSC": {"Spec match": 5, "Brand strength": 4, "Local support": 4},
    "Hamilton VN": {"Spec match": 4, "Brand strength": 4, "Local support": 5},
    "Mindray VN": {"Spec match": 3, "Brand strength": 4, "Local support": 3}
  }
}
```

> **Lưu ý thực tế:** Param là `scores_by_supplier` (key = supplier name, khớp `cand.supplier`), không phải `scores_by_candidate` (row name) như spec ban đầu.

```json
```

**Response:**
```json
{
  "success": true,
  "data": {
    "weighted_scores": {
      "abc123": 4.32,
      "def456": 4.18,
      "ghi789": 3.45
    },
    "recommended": "abc123",
    "all_groups_complete": false,
    "missing_groups": ["Financial", "Support", "Compliance"]
  }
}
```

**Errors:**
```json
{"success": false, "error": "Vai trò HTM không được chấm nhóm Commercial", "code": "FORBIDDEN"}
{"success": false, "error": "IMM Vendor Evaluation phải ở trạng thái Quotation Received để chấm điểm", "code": "BAD_STATE"}
```

---

### 3.10 `transition_eval_workflow`

```
POST /api/method/assetcore.api.imm03.transition_eval_workflow
```

**Request body:**
```json
{
  "name": "VE-26-00120",
  "action": "Hoàn tất chấm điểm"
}
```

**Response:**
```json
{"success": true, "data": {"name": "VE-26-00120", "workflow_state": "Evaluated", "docstatus": 1}}
```

**Errors:**
```json
{"success": false, "error": "G01: Thiếu scoring nhóm Compliance — QA Risk chưa chấm", "code": "BUSINESS_RULE"}
{"success": false, "error": "Transition 'Hoàn tất chấm điểm' không hợp lệ với state Draft", "code": "BAD_STATE"}
```

---

### 3.11 `create_decision`

```
POST /api/method/assetcore.api.imm03.create_decision
```

**Request body:**
```json
{
  "evaluation_ref": "VE-26-00120",
  "procurement_method": "Đấu thầu rộng rãi",
  "method_legal_basis": ""
}
```

**Response:**
```json
{"success": true, "data": {"name": "PD-26-00045", "workflow_state": "Draft"}}
```

**Errors:**
```json
{"success": false, "error": "VR-03-07: Tech Spec TS-26-00045 đã có Decision Awarded — không tạo được Decision mới", "code": "DUPLICATE"}
{"success": false, "error": "VE-26-00120 chưa ở trạng thái Evaluated", "code": "BAD_STATE"}
```

---

### 3.12 `award_decision`

```
POST /api/method/assetcore.api.imm03.award_decision
```

**Request body:**
```json
{
  "name": "PD-26-00045",
  "winner_supplier": "Vinamed JSC",
  "awarded_price": 2000000000,
  "funding_source": "NSNN",
  "board_approver": "vp.block1@hospital.vn",
  "contract_doc": "/files/contract-2026-045.pdf",
  "remarks": ""
}
```

> **Lưu ý:** Field name thực tế là `winner_supplier` (Link → AC Supplier), không phải `winner_candidate`/`awarded_vendor` như thiết kế ban đầu.

**Pre-conditions:** state `Pending Approval`, Gate G05 pass.

**Side effects:**
- `docstatus = 1`, `workflow_state = "Awarded"`, `awarded_date = today`
- Mint `AC Purchase` → `ac_purchase_ref`
- `AC Purchase.imm_procurement_decision = doc.name`
- Ghi `IMM Audit Trail` ("Awarded", "PO Created")
- Cập nhật `IMM Procurement Plan Line.status = "Awarded"`
- Publish `frappe.publish_realtime("imm03_decision_awarded", {...})`

**Response:**
```json
{
  "success": true,
  "data": {
    "name": "PD-26-00045",
    "workflow_state": "Awarded",
    "ac_purchase_ref": "AC-PUR-2026-00112",
    "envelope_check_pct": 80.0,
    "awarded_date": "2026-06-01"
  }
}
```

**Errors:**
```json
{"success": false, "error": "VR-03-04: Awarded 108% envelope — cần giải trình PTP Khối 1", "code": "CONFLICT"}
{"success": false, "error": "VR-03-05: Winner Vinamed JSC phải có AVL Active hoặc Conditional + sign-off", "code": "BUSINESS_RULE"}
{"success": false, "error": "G05: Thiếu contract_doc — phải đính kèm hợp đồng", "code": "BUSINESS_RULE"}
{"success": false, "error": "Mint AC Purchase thất bại — Decision đã rollback về Pending Approval", "code": "INTERNAL"}
{"success": false, "error": "Chỉ IMM Board Approver mới có thể Award Decision", "code": "FORBIDDEN"}
```

---

### 3.13 `record_contract`

```
POST /api/method/assetcore.api.imm03.record_contract
```

**Request body:**
```json
{
  "name": "PD-26-00045",
  "contract_no": "HD-2026-045",
  "contract_doc": "/files/contract-signed.pdf",
  "signed_date": "2026-06-15"
}
```

**Side effects:**
- `workflow_state = "Contract Signed"`
- Ghi IMM Audit Trail

**Response:**
```json
{"success": true, "data": {"name": "PD-26-00045", "workflow_state": "Contract Signed"}}
```

---

### 3.14 `get_vendor_scorecard`

```
GET /api/method/assetcore.api.imm03.get_vendor_scorecard?supplier=Vinamed JSC&year=2026&quarter=2
```

**Response:**
```json
{
  "success": true,
  "data": {
    "name": "VS-2026-Q2-Vinamed-JSC",
    "supplier": "Vinamed JSC",
    "period_year": 2026,
    "period_quarter": 2,
    "overall_score": 4.3,
    "kpi_rows": [
      {"dimension": "Delivery", "weight_pct": 20, "raw_value": 94.5, "normalized_score": 4.5, "weighted": 0.9, "source_module": "IMM-04"},
      {"dimension": "Quality", "weight_pct": 25, "raw_value": 0.5, "normalized_score": 4.4, "weighted": 1.1, "source_module": "IMM-04/IMM-10"},
      {"dimension": "Aftersales", "weight_pct": 20, "raw_value": 18.3, "normalized_score": 4.2, "weighted": 0.84, "source_module": "IMM-09"},
      {"dimension": "Spare", "weight_pct": 15, "raw_value": 97.0, "normalized_score": 4.1, "weighted": 0.62, "source_module": "IMM-15"},
      {"dimension": "Compliance", "weight_pct": 20, "raw_value": 0, "normalized_score": 4.0, "weighted": 0.8, "source_module": "IMM-10"}
    ],
    "commentary": "Vinamed đạt hiệu suất tốt Q2/2026",
    "generated_at": "2026-07-01T02:00:00"
  }
}
```

---

### 3.15 `dashboard_kpis`

```
GET /api/method/assetcore.api.imm03.dashboard_kpis?period=2026-Q2
```

**Response:**
```json
{
  "success": true,
  "data": {
    "period": "2026-Q2",
    "lead_time_eval_to_awarded_days": {"value": 55, "target": 60, "status": "green"},
    "avl_pick_rate_pct": {"value": 92, "target": 90, "status": "green"},
    "avg_vendor_score": {"value": 4.1, "target": 4.0, "status": "green"},
    "avl_coverage_pct": {"value": 82, "target": 80, "status": "green"},
    "audit_completion_rate_pct": {"value": 97, "target": 95, "status": "green"},
    "supplier_nc_rate_pct": {"value": 0.8, "target": null, "status": "down"},
    "cost_saving_pct": {"value": 7.2, "target": 5, "status": "green"}
  }
}
```

---

### 3.16 `list_evaluations`

```
GET /api/method/assetcore.api.imm03.list_evaluations?workflow_state=Quotation+Received&page=1
```

**Response:**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "name": "VE-26-00120",
        "spec_ref": "TS-26-00045",
        "workflow_state": "Quotation Received",
        "candidate_count": 3,
        "draft_date": "2026-04-15",
        "recommended_candidate": null
      }
    ],
    "total": 8,
    "page": 1,
    "page_size": 20
  }
}
```

---

### 3.17 `list_avl`

```
GET /api/method/assetcore.api.imm03.list_avl?status=Approved&device_category=Imaging
```

**Response:**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "name": "AVL-2026-00045",
        "supplier": "Vinamed JSC",
        "device_category": "Imaging",
        "status": "Approved",
        "valid_from": "2026-05-01",
        "valid_to": "2028-04-30",
        "days_remaining": 722
      }
    ],
    "total": 12,
    "page": 1,
    "page_size": 20
  }
}
```

---

### 3.18 `add_vendor_cert` _(Spec only — chưa implement)_

```
POST /api/method/assetcore.api.imm03.add_vendor_cert
```

**Request body:**
```json
{
  "supplier": "Vinamed JSC",
  "cert_type": "ISO 13485",
  "cert_number": "ISO-13485-2024-VINAMED",
  "issued_by": "TUV SUD",
  "issued_date": "2024-03-01",
  "expiry_date": "2027-03-01",
  "attachment": "/files/iso-13485-vinamed.pdf"
}
```

**Response:**
```json
{"success": true, "data": {"cert_row": "xyz789", "cert_type": "ISO 13485", "status": "Active"}}
```

---

## 4. Error Code Catalog

| Tình huống | code | Ví dụ `error` |
|---|---|---|
| Số candidate không phù hợp method | `BUSINESS_RULE` | "VR-03-01: Đấu thầu rộng rãi yêu cầu ≥ 3 candidate, hiện có 2" |
| Vendor non-AVL chưa sign-off tại submit | `BUSINESS_RULE` | "VR-03-02: Vendor Hamilton Vietnam non-AVL — cần sign-off IMM Board Approver" |
| Quotation hết hạn | `VALIDATION` | "VR-03-03: Quotation QT-2026-001 hết hiệu lực ngày 2026-05-09" |
| Awarded > 105% envelope | `CONFLICT` | "VR-03-04: Awarded 108% envelope — cần giải trình PTP Khối 1" |
| Winner không có AVL Active | `BUSINESS_RULE` | "VR-03-05: Winner Vinamed JSC phải có AVL Active hoặc Conditional + sign-off" |
| Cố sửa audit trail | `BUSINESS_RULE` | "VR-03-06: IMM Audit Trail bất biến sau khi tạo" |
| Spec đã có Decision Awarded | `DUPLICATE` | "VR-03-07: Tech Spec TS-26-00045 đã có Decision Awarded" |
| PO TBYT không có Decision | `BUSINESS_RULE` | "VR-03-08: AC Purchase TBYT phải đi qua IMM-03 Procurement Decision" |
| G01 Gate fail — scoring chưa đủ | `BUSINESS_RULE` | "G01: Thiếu scoring nhóm Compliance — QA Risk chưa chấm" |
| G02 Gate fail — thiếu quotation | `BUSINESS_RULE` | "G02: Cần ≥ 1 báo giá hợp lệ trước Quotation Received" |
| G03 Gate fail — AVL check | `BUSINESS_RULE` | "G03: Winner phải có AVL Active hoặc Conditional + sign-off" |
| G04 Gate fail — method bất hợp pháp | `BUSINESS_RULE` | "G04: Chỉ định thầu vượt ngưỡng 50 triệu — cần cơ sở pháp lý" |
| G05 Gate fail — thiếu docs | `BUSINESS_RULE` | "G05: Thiếu contract_doc / funding_source / board_approver" |
| Mint AC Purchase thất bại | `INTERNAL` | "Mint AC Purchase thất bại — Decision rollback về Pending Approval" |
| Transition workflow sai state | `BAD_STATE` | "Transition 'Hoàn tất chấm điểm' không hợp lệ với state Draft" |
| Không đủ quyền | `FORBIDDEN` | "Chỉ IMM Board Approver mới có thể Award Decision" |
| Không tìm thấy record | `NOT_FOUND` | "IMM Vendor Evaluation VE-26-00999 không tồn tại" |

---

## 5. FE ↔ BE Error Mapping

| `code` | FE xử lý |
|---|---|
| `VALIDATION` | Hiển thị lỗi inline bên cạnh field tương ứng |
| `BUSINESS_RULE` | Toast màu đỏ + detail modal nếu cần giải thích |
| `CONFLICT` | Toast cảnh báo vàng + yêu cầu nhập justification |
| `DUPLICATE` | Toast "Đã tồn tại — xem record hiện có" + link |
| `BAD_STATE` | Toast "Thao tác không hợp lệ ở trạng thái hiện tại" |
| `FORBIDDEN` | Toast "Bạn không có quyền thực hiện thao tác này" |
| `NOT_FOUND` | Redirect 404 page |
| `INTERNAL` | Toast đỏ "Lỗi hệ thống — liên hệ CMMS Admin" + log |

---

## 6. TypeScript Types

> **Thực tế:** `frontend/src/types/imm03.ts` dùng tên interfaces khác so với spec ban đầu. Tên thực tế:
> - `EvalListItem`, `EvalDoc` (không phải `VendorEvaluation`)
> - `AvlListItem` (không phải `AVLEntry`)
> - `DecisionListItem`, `DecisionDoc` (không phải `ProcurementDecision`)
> - `DashboardKpis` (không phải `DashboardKPIs`)
> - `VendorEvalCandidate` (không phải `EvalCandidate`)
> - `VendorQuotationLine` (không phải `QuotationLine`)
>
> Xem `frontend/src/types/imm03.ts` cho ground truth. Spec types dưới đây là thiết kế ban đầu — dùng làm reference.

```typescript
// types/imm03.ts — SPEC (thiết kế ban đầu). Ground truth: frontend/src/types/imm03.ts

export interface VendorProfile {
  name: string;
  supplier_name: string;
  legal_name: string;
  vat_code: string;
  country: string;
  rep_name: string;
  rep_phone: string;
  rep_email: string;
  device_categories: string;
  financial_health: "A" | "B" | "C" | "Unknown";
  imm_avl_status: AVLStatus;
  imm_overall_score: number;
  imm_last_audit_date: string | null;
  imm_next_audit_date: string | null;
  certifications: VendorCert[];
}

export type AVLStatus =
  | "Approved"
  | "Conditional"
  | "Suspended"
  | "Expired"
  | "Not Applicable";

export interface VendorCert {
  cert_type: string;
  cert_number: string;
  issued_by: string;
  issued_date: string;
  expiry_date: string;
  status: "Active" | "Expiring" | "Expired";
  attachment?: string;
}

export interface AVLEntry {
  name: string;
  supplier: string;
  device_category: string;
  validity_years: number;
  valid_from: string;
  valid_to: string;
  status: AVLStatus;
  approver?: string;
}

export interface VendorEvaluation {
  name: string;
  spec_ref: string;
  plan_line: string;
  draft_date: string;
  weighting_scheme: WeightingScheme;
  criteria: EvalCriterion[];
  candidates: EvalCandidate[];
  quotations: QuotationLine[];
  recommended_candidate: string | null;
  workflow_state: EvalState;
  docstatus: 0 | 1 | 2;
}

export type EvalState =
  | "Draft"
  | "Open RFQ"
  | "Quotation Received"
  | "Evaluated"
  | "Cancelled";

export interface WeightingScheme {
  Technical: number;
  Commercial: number;
  Financial: number;
  Support: number;
  Compliance: number;
}

export interface EvalCriterion {
  group: "Technical" | "Commercial" | "Financial" | "Support" | "Compliance";
  criterion: string;
  weight_pct: number;
  scorer_role: string;
}

export interface EvalCandidate {
  name: string;
  supplier: string;
  in_avl: boolean;
  sign_off_non_avl?: string;
  scores: Record<string, number>;
  weighted_score: number;
  notes?: string;
}

export interface QuotationLine {
  candidate_row: string;
  quotation_no: string;
  quotation_date: string;
  quotation_validity: string;
  price: number;
  currency: string;
  payment_terms: string;
  delivery_days: number;
  warranty_months: number;
}

export interface ProcurementDecision {
  name: string;
  spec_ref: string;
  evaluation_ref: string;
  plan_ref: string;
  procurement_method: ProcurementMethod;
  method_legal_basis?: string;
  winner_candidate: string;
  awarded_vendor: string;
  awarded_price: number;
  envelope_check_pct: number;
  funding_source: FundingSource;
  board_approver?: string;
  contract_no?: string;
  ac_purchase_ref?: string;
  awarded_date?: string;
  workflow_state: DecisionState;
  docstatus: 0 | 1 | 2;
}

export type ProcurementMethod =
  | "Chỉ định thầu"
  | "Chào hàng cạnh tranh"
  | "Đấu thầu rộng rãi"
  | "Mua sắm trực tiếp"
  | "Mua sắm tập trung";

export type FundingSource =
  | "NSNN"
  | "Tài trợ"
  | "Xã hội hóa"
  | "BHYT"
  | "Khác";

export type DecisionState =
  | "Draft"
  | "Method Selected"
  | "Negotiation"
  | "Award Recommended"
  | "Pending Approval"
  | "Awarded"
  | "Contract Signed"
  | "PO Issued"
  | "Cancelled";

export interface VendorScorecard {
  name: string;
  supplier: string;
  period_year: number;
  period_quarter: number;
  overall_score: number;
  kpi_rows: ScorecardKPIRow[];
  commentary?: string;
  generated_at: string;
}

export interface ScorecardKPIRow {
  dimension: "Delivery" | "Quality" | "Aftersales" | "Spare" | "Compliance";
  weight_pct: number;
  raw_value: number;
  normalized_score: number;
  weighted: number;
  source_module: string;
}

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  code?: string;
}
```

---

## 7. Webhook / Realtime Events

| Event | Payload | Phát bởi | Subscriber |
|---|---|---|---|
| `imm03_eval_seeded` | `{"name": "VE-26-00120", "spec_ref": "TS-26-00045"}` | `seed_evaluation_from_spec()` | UI ĐT-HĐ-NCC inbox |
| `imm03_decision_awarded` | `{"name": "PD-26-00045", "ac_purchase_ref": "AC-PUR-...", "winner_vendor": "Vinamed JSC", "plan_line": "..."}` | `award_decision()` | IMM-04 prep listener; IMM-01 plan line update |
| `imm03_avl_expired` | `{"supplier": "VINAMED", "device_category": "Imaging", "avl": "AVL-2026-00045"}` | `check_avl_expiry()` | KH-TC dashboard |
| `imm03_audit_finding_critical` | `{"supplier": "VINAMED", "audit": "SA-26-00012", "finding_count": 1}` | `on_submit_audit()` | QA Risk + VP Block1 |

---

## 8. Business Rule ↔ API Mapping

| BR ID | Rule | Enforce tại | Error code |
|---|---|---|---|
| BR-03-01 | 1 Tech Spec ↔ 1 Decision Awarded | `create_decision`, `award_decision` | `DUPLICATE` |
| BR-03-02 | Min candidate phù hợp method | `submit_quotations`, `transition_eval_workflow` | `BUSINESS_RULE` |
| BR-03-03 | Vendor non-AVL cần sign-off | `submit_quotations`, `award_decision` | `BUSINESS_RULE` |
| BR-03-04 | Quotation không hết hạn | `submit_quotations` | `VALIDATION` |
| BR-03-05 | Awarded ≤ 105% envelope | `award_decision` | `CONFLICT` |
| BR-03-06 | Method hợp pháp | `create_decision`, transition đến `Method Selected` | `BUSINESS_RULE` |
| BR-03-07 | Winner có AVL Active/Conditional | `award_decision` | `BUSINESS_RULE` |
| BR-03-08 | PO TBYT qua Decision | `AC Purchase validate hook` | `BUSINESS_RULE` |

---

## 9. Smoke Test

```bash
# 1. List vendor profiles
curl -X GET "http://localhost:8000/api/method/assetcore.api.imm03.list_vendor_profiles" \
  -H "X-Frappe-CSRF-Token: <token>"

# 2. Create AVL entry
curl -X POST "http://localhost:8000/api/method/assetcore.api.imm03.create_avl_entry" \
  -H "Content-Type: application/json" \
  -d '{"supplier":"Vinamed JSC","device_category":"Imaging","validity_years":2,"valid_from":"2026-05-01"}'

# 3. Award decision (thực tế cần session có role IMM Board Approver)
curl -X POST "http://localhost:8000/api/method/assetcore.api.imm03.award_decision" \
  -H "Content-Type: application/json" \
  -d '{"name":"PD-26-00045","winner_supplier":"Vinamed JSC","awarded_price":2000000000,"funding_source":"NSNN","board_approver":"vp.block1@hospital.vn","contract_doc":"/files/contract.pdf"}'
```

---

## 10. Implementation Notes

1. Permlevel 1 cho các fields nhạy cảm: `awarded_price`, `envelope_check_pct`, `funding_source`, `funding_evidence`, `contract_doc`, `board_approver`. Chỉ roles KH-TC/TCKT/PTP Khối 1/VP Block1/CMMS Admin mới thấy.
2. PO mint dùng `frappe.new_doc("AC Purchase")` — KHÔNG dùng ERPNext Purchase Order. Naming: `AC-PUR-.YYYY.-.#####`.
3. Rollback Decision về `Pending Approval` nếu mint AC Purchase fail — dùng `frappe.db.rollback()` trước khi raise ServiceError.
4. Vendor Scorecard idempotent: `frappe.db.exists("IMM Vendor Scorecard", {"period_year": y, "period_quarter": q, "supplier": v})` → update nếu có, insert nếu chưa.
5. Scheduler quarterly: khai trong `hooks.py` dưới `"cron"` key với expression `"0 2 1 1,4,7,10 *"` — Frappe v15 KHÔNG hỗ trợ key `"quarterly"`.
6. Mọi state transition phải qua `frappe.workflow.apply_transition()` — không set `workflow_state` trực tiếp trong service.
