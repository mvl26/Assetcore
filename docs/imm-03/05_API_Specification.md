# 05 — Đặc tả API — IMM-03 Đánh giá Nhà cung cấp & Quyết định Mua sắm

> ✅ Module LIVE — Wave 2. Tất cả endpoints đã `@frappe.whitelist()` trong `assetcore/api/imm03.py`.

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-03 — Vendor Evaluation & Procurement Decision |
| Phiên bản | 0.1.0 |
| Ngày | 2026-05-18 |
| Base path | `/api/method/assetcore.api.imm03.<endpoint>` |
| Trạng thái | LIVE — Wave 2 (cập nhật response shapes thực tế) |

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

> **Catalog endpoint thực tế** (`api/imm03.py`, 24 endpoints):
>
> **Vendor Profile (BE-03-01):** `list_vendor_profiles`, `get_vendor_profile`, `create_vendor_profile`, `add_vendor_cert` — ✅ LIVE; thao tác qua `AC Supplier` + custom fields IMM (`imm_avl_status`, `imm_avl_categories`, `imm_overall_score`, `imm_last_audit_date`, `imm_next_audit_date`, `imm_certifications` table → Vendor Cert).
>
> **Vendor Evaluation:** `list_evaluations`, `get_evaluation`, `create_evaluation`, `add_candidate`, `submit_quotations`, `score_evaluation`, `transition_eval_workflow`
>
> **AVL:** `list_avl`, `get_avl`, `create_avl_entry`, `approve_avl`, `suspend_avl`
>
> **Procurement Decision:** `list_decisions`, `get_decision`, `create_decision`, `award_decision`, `record_contract`, `transition_decision_workflow`
>
> **Dashboard:** `dashboard_kpis`, `get_vendor_scorecard`

### 3.1 `list_vendor_profiles` ✅ LIVE

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

**Response:** (fields fixed bởi `_list_vendor_profiles`; `cert_count` + `cert_expiring_soon` enrich post-query qua `_enrich_vendor_cert_counts`; `audit_overdue` filter chạy in-Python sau khi load do MariaDB không có boolean computed)
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

### 3.2 `get_vendor_profile` ✅ LIVE

```
GET /api/method/assetcore.api.imm03.get_vendor_profile?name=VINAMED
```

**Response:** payload là `AC Supplier.as_dict()` (kèm core + custom fields) + 2 trường tổng hợp `avl_entries` và `scorecard_history`.
```json
{
  "success": true,
  "data": {
    "name": "VINAMED",
    "supplier_name": "Vinamed JSC",
    "supplier_code": "VINAMED",
    "supplier_group": "Manufacturer",
    "country": "Vietnam",
    "tax_id": "0301234567",
    "email_id": "a.nguyen@vinamed.vn",
    "phone": "0901234567",
    "imm_avl_status": "Approved",
    "imm_avl_categories": "Imaging, Life Support",
    "imm_overall_score": 4.3,
    "imm_last_audit_date": "2026-01-15",
    "imm_next_audit_date": "2027-01-15",
    "imm_certifications": [
      {"cert_type": "ISO 9001", "cert_number": "ISO-9001-2024-VINAMED",
       "expiry_date": "2027-01-15", "status": "Active"}
    ],
    "avl_entries": [
      {"name": "AVL-2026-00045", "device_category": "Imaging",
       "status": "Approved", "valid_from": "2026-05-01", "valid_to": "2028-04-30"}
    ],
    "scorecard_history": [
      {"name": "VS-2026-Q1-...", "period_year": 2026, "period_quarter": 1, "overall_score": 4.1}
    ]
  }
}
```

> Lưu ý: field child Table là `imm_certifications` (KHÔNG phải `certifications`). Trong `avl_entries` SQL alias `workflow_state as status` → FE thấy key `status`.

**Errors:**
```json
{"success": false, "error": "Vendor VINAMED không tồn tại", "code": "NOT_FOUND"}
```

---

### 3.3 `create_vendor_profile` ✅ LIVE

```
POST /api/method/assetcore.api.imm03.create_vendor_profile
```

**Wrapper:** body cần gói trong `payload` (string JSON) khi gọi qua `frappePost`.

**Payload (JSON object):**
```json
{
  "supplier": "Vinamed JSC",
  "country": "Vietnam",
  "tax_id": "0301234567",
  "email_id": "a.nguyen@vinamed.vn",
  "phone": "0901234567",
  "imm_avl_categories": "Imaging, Life Support",
  "certifications": [
    {"cert_type": "ISO 9001", "cert_number": "ISO-9001-2024-VINAMED",
     "issued_by": "Bureau Veritas", "issued_date": "2024-01-15",
     "expiry_date": "2027-01-15"}
  ]
}
```

**Side effects:**
- Nếu `AC Supplier` chưa tồn tại → tạo mới với `supplier_name = supplier`; ngược lại update các fields có trong payload (qua `setattr`).
- `imm_avl_status` mặc định "Not Applicable" nếu chưa set.
- Thay thế `imm_certifications` child table bằng list mới (clear + append); mỗi cert default `status="Active"` nếu thiếu.
- VR: nếu thiếu `certifications` → throw `VALIDATION` "VR-03-XX: Thiếu certifications — cần ≥ 1 chứng chỉ ISO 9001 hoặc ISO 13485".

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

**Response (thực tế — không có `"status"` key):**
```json
{"success": true, "data": {"name": "AVL-2026-00045", "valid_to": "2028-04-30"}}
```

> Note: `_create_avl_entry` trả về `{"name": avl.name, "valid_to": avl.valid_to}`. Không có `"status"` key — state mặc định là "Draft" nhưng không được include trong response. FE dùng `workflow_state` khi cần hiển thị trạng thái (qua `get_avl`).

**Errors:** Không có validation về `validity_years` range trong code thực tế — BE nhận bất kỳ int nào. Validation là trách nhiệm FE.

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
- `avl.workflow_state = "Approved"` (KHÔNG phải `avl.status` — AVL không có field `status` riêng)
- `avl.approver = approver`, `avl.approval_doc = approval_doc`
- Nếu state là Draft → `avl.submit()` (docstatus → 1). Nếu Conditional/Suspended → `avl.save()` + `_sync_supplier_avl_status`
- `AC Supplier.imm_avl_status` và `imm_avl_categories` được sync qua `_sync_supplier_avl_status`

**Response (thực tế — không có `"valid_to"`):**
```json
{"success": true, "data": {"name": "AVL-2026-00045", "workflow_state": "Approved"}}
```

**Errors:**
```json
{"success": false, "error": "AVL ở state Approved không thể Approve", "code": "BAD_STATE"}
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

**Response (thực tế — `workflow_state` thay vì `status`):**
```json
{"success": true, "data": {"name": "AVL-2026-00045", "workflow_state": "Suspended"}}
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

**Response (thực tế — `row_count` thay vì `row`; `in_avl` là 0/1 int):**
```json
{
  "success": true,
  "data": {
    "row_count": 2,
    "in_avl": 0,
    "warning": "Vendor non-AVL — cần sign-off IMM Board Approver"
  }
}
```

> Note: Response thực tế từ `_add_candidate`: `{"row_count": len(ve.candidates), "in_avl": in_avl, "warning": warn}`. Không có `"row"` (row name) hay `"supplier"` key. `in_avl` là `int` (0 hoặc 1), không phải `bool`. `warning` là `null` nếu vendor đã có AVL.

**Errors:**
```json
{"success": false, "error": "Eval đã submit", "code": "BAD_STATE"}
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

**Response (thực tế — chỉ `quotations_count`; không có `quotations_added` hay `state`):**
```json
{"success": true, "data": {"quotations_count": 3}}
```

> Note: `_submit_quotations` chỉ append rows và save, trả về `{"quotations_count": len(ve.quotations)}`. Validation `VR-03-03` (quotation_validity) chạy qua `validate_evaluation` hook khi save.

**Errors:**
```json
{"success": false, "error": "Eval đã submit", "code": "BAD_STATE"}
{"success": false, "error": "VR-03-03: Quotation đã hết hạn: QT-2026-001", "code": "VALIDATION"}
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

**Response (thực tế — key là supplier name; không có `all_groups_complete`/`missing_groups`):**
```json
{
  "success": true,
  "data": {
    "weighted_scores": {
      "Vinamed JSC": 4.32,
      "Hamilton VN": 4.18,
      "Mindray VN": 3.45
    },
    "recommended": "Vinamed JSC"
  }
}
```

> Note: `weighted_scores` key là supplier name (`cand.supplier`), KHÔNG phải row name. `recommended` là supplier name của top scorer. Không có `"all_groups_complete"` hay `"missing_groups"` — đây là design spec chưa implement. Thực tế `_score_evaluation` chỉ merge scores rồi lưu, không validate nhóm nào đã đủ.

**Errors:**
```json
{"success": false, "error": "Eval đã submit", "code": "BAD_STATE"}
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

**Response (thực tế — không có `"awarded_date"`):**
```json
{
  "success": true,
  "data": {
    "name": "PD-26-00045",
    "workflow_state": "Awarded",
    "ac_purchase_ref": "AC-PUR-2026-00112",
    "envelope_check_pct": 80.0
  }
}
```

> Note: `awarded_date` được set trên doc (`doc.awarded_date = today()` trong `before_submit_decision`) nhưng KHÔNG được trả về trong response. FE cần gọi `get_decision` để lấy `awarded_date` sau khi Award.

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
- Pre-condition: Decision phải đã submit (`docstatus=1` — state Awarded). Nếu chưa → throw `BAD_STATE`.
- Update `contract_no` + `contract_doc` qua `frappe.db.set_value` (safe trên doc đã submitted).
- Field `contract_signed_date` KHÔNG tồn tại trong DocType schema — param `signed_date` được nhận nhưng skip.
- Gọi `frappe.model.workflow.apply_workflow(doc, "Ký HĐ")` → `workflow_state = "Contract Signed"`.
- Audit log qua `log_audit_event(event_type="imm03_contract_signed")`.

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
GET /api/method/assetcore.api.imm03.dashboard_kpis
```

> **Thực tế V1:** endpoint trả về funnel state counts + AVL active/expiring — KHÔNG có các KPI "lead_time/avl_pick_rate/cost_saving" (đó là roadmap Wave 3). Không nhận param `period`.

**Response:**
```json
{
  "success": true,
  "data": {
    "eval_states": {"Draft": 2, "Open RFQ": 1, "Quotation Received": 3, "Evaluated": 8},
    "decision_states": {"Draft": 1, "Method Selected": 2, "Pending Approval": 1, "Awarded": 5, "Contract Signed": 4, "PO Issued": 12},
    "avl_active": 24,
    "avl_expiring_30d": 3
  }
}
```

`eval_states` / `decision_states`: COUNT(*) GROUP BY `workflow_state` cho docstatus<2. `avl_active`: AVL docstatus=1 và state ∈ (Approved, Conditional). `avl_expiring_30d`: AVL docstatus=1, state ∈ (Approved, Conditional), `DATEDIFF(valid_to, CURDATE()) BETWEEN 0 AND 30`.

---

### 3.16 `list_evaluations`

```
GET /api/method/assetcore.api.imm03.list_evaluations?workflow_state=Quotation+Received&page=1
```

**Response:** fields = `name`, `spec_ref`, `draft_date`, `workflow_state`, `recommended_candidate` + enrich `tech_spec_ref_name` (display IMM Tech Spec.device_model_ref) + `vendor_name` (display AC Supplier.supplier_name của recommended_candidate).
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "name": "VE-26-00120",
        "spec_ref": "TS-26-00045",
        "tech_spec_ref_name": "DM-MRI-3T-Siemens",
        "draft_date": "2026-04-15",
        "workflow_state": "Quotation Received",
        "recommended_candidate": null,
        "vendor_name": null
      }
    ],
    "total": 8
  }
}
```

---

### 3.17 `list_avl`

```
GET /api/method/assetcore.api.imm03.list_avl?filters={"workflow_state":"Approved","device_category":"Imaging"}
```

> Endpoint nhận 1 arg `filters` (JSON string). KHÔNG có pagination — `page_length=100` hard-coded. KHÔNG có `total`. Trả về `workflow_state` (KHÔNG có field `status`).

**Response:** fields = `name`, `supplier`, `device_category`, `workflow_state`, `valid_from`, `valid_to` + enrich `vendor_name` (AC Supplier.supplier_name) + `device_category_name` (AC Asset Category.category_name).
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "name": "AVL-2026-00045",
        "supplier": "VINAMED",
        "vendor_name": "Vinamed JSC",
        "device_category": "CAT-IMAGING",
        "device_category_name": "Imaging",
        "workflow_state": "Approved",
        "valid_from": "2026-05-01",
        "valid_to": "2028-04-30"
      }
    ]
  }
}
```

---

### 3.18 `add_vendor_cert` ✅ LIVE

```
POST /api/method/assetcore.api.imm03.add_vendor_cert
```

**Params (flat — không gói `payload`):** `supplier`, `cert_type`, `cert_number` (bắt buộc); `issued_by`, `issued_date`, `expiry_date`, `attachment` (optional).

**Side effects:**
- Append row vào `AC Supplier.imm_certifications` (status mặc định "Active").
- Audit log `event_type="vendor_cert_added"` qua `log_audit_event`.

**Response:**
```json
{"success": true, "data": {"cert_row": "xyz789", "cert_type": "ISO 13485", "status": "Active"}}
```

---

### 3.19 `get_evaluation` ✅ LIVE

```
GET /api/method/assetcore.api.imm03.get_evaluation?name=VE-26-00120
```

**Response:** `IMM Vendor Evaluation.as_dict()` với enrich: `supplier_name` per candidate + `candidate_supplier_name` per quotation. Gọi `_enrich_decision_chain` để add `plan_ref_name`.

---

### 3.20 `get_decision` ✅ LIVE

```
GET /api/method/assetcore.api.imm03.get_decision?name=PD-26-00045
```

**Response:** `IMM Procurement Decision.as_dict()` với enrich: `supplier_name` per candidate + `winner_supplier_name` (display name). Gọi `_enrich_decision_chain` để add `plan_ref_name` + `ac_purchase_ref_name`.

---

### 3.21 `get_avl` ✅ LIVE

```
GET /api/method/assetcore.api.imm03.get_avl?name=AVL-2026-00045
```

**Response:** `IMM AVL Entry.as_dict()`.

---

### 3.22 `list_decisions` ✅ LIVE

```
GET /api/method/assetcore.api.imm03.list_decisions?filters={}&page=1&page_size=20
```

**Response:** fields = `name`, `spec_ref`, `winner_supplier`, `awarded_price`, `envelope_check_pct`, `workflow_state`, `ac_purchase_ref`, `creation` + enrich `vendor_name` (AC Supplier.supplier_name) + `tech_spec_ref_name` (IMM Tech Spec.device_model_ref).

---

### 3.23 `create_evaluation` ✅ LIVE

```
POST /api/method/assetcore.api.imm03.create_evaluation
```

**Request:** `spec_ref` (bắt buộc), `weighting_scheme` (JSON object, optional).
**Response:** `{"name": "VE-26-00120", "workflow_state": "Draft"}`

---

### 3.24 `transition_decision_workflow` ✅ LIVE

```
POST /api/method/assetcore.api.imm03.transition_decision_workflow
```

**Request:** `name`, `action` (workflow action string).
**Response:** `{"name": "PD-26-00045", "workflow_state": "...", "docstatus": 0}` — tương tự `transition_eval_workflow` nhưng cho IMM Procurement Decision. Ghi audit log `imm03_decision_workflow_transition`.

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
