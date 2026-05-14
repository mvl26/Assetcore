# 04 — Thiết kế Backend — IMM-03 Đánh giá Nhà cung cấp & Quyết định Mua sắm

> ✅ Module LIVE — Wave 2. File `assetcore/services/imm03.py` và `assetcore/api/imm03.py` đã implement đầy đủ.

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-03 — Vendor Evaluation & Procurement Decision |
| Phiên bản | 0.1.0 |
| Ngày | 2026-05-14 |
| Trạng thái | LIVE — Wave 2 |

---

## I. DocType Catalog

| # | DocType | Naming | Submittable | Module | Mô tả |
|---|---|---|---|---|---|
| 1 | `IMM Vendor Evaluation` | `VE-.YY.-.#####` | Yes | IMM-03 | Phiếu chấm điểm vendor đa tiêu chí |
| 2 | `IMM Procurement Decision` | `PD-.YY.-.#####` | Yes | IMM-03 | Quyết định mua sắm — chốt vendor + PO |
| 3 | `IMM AVL Entry` | `AVL-.YYYY.-.#####` | Yes | IMM-03 | Approved Vendor List per category |
| 4 | `IMM Vendor Scorecard` | `VS-.YYYY.-.QN-.{Vendor}` | No | IMM-03 | KPI vendor theo quý |
| 5 | `IMM Supplier Audit` | `SA-.YY.-.#####` | Yes | IMM-03 | Audit năng lực cung ứng |
| C1 | `Vendor Eval Criterion` | — | — | IMM-03 (child) | Tiêu chí chấm điểm |
| C2 | `Vendor Eval Candidate` | — | — | IMM-03 (child) | Vendor được chấm |
| C3 | `Vendor Quotation Line` | — | — | IMM-03 (child) | Báo giá chi tiết |
| C4 | `Vendor Cert` | — | — | IMM-03 (child) | Chứng chỉ pháp lý vendor |
| C5 | `Audit Finding` | — | — | IMM-03 (child) | Phát hiện audit + CAPA |
| C6 | `Scorecard KPI Row` | — | — | IMM-03 (child) | KPI chi tiết per dimension |

**Ghi chú:** Không tạo DocType `IMM Vendor Profile` riêng — vendor master là `AC Supplier` (Wave 1) được enrich bằng custom fields. Audit trail dùng `IMM Audit Trail` (chung toàn hệ thống).

---

## II. Field Tables — Primary DocTypes

### II.1 IMM Vendor Evaluation

| Field | Label | Type | Req | Permlevel | Note |
|---|---|---|---|---|---|
| `name` | Mã đánh giá | Data (auto) | Y | 0 | Naming: `VE-.YY.-.#####` |
| `spec_ref` | Tech Spec | Link → IMM Tech Spec | Y | 0 | Từ IMM-02 |
| `plan_line` | Dòng kế hoạch | Data | N | 0 | Mirror từ spec |
| `draft_date` | Ngày lập | Date | Y | 0 | Auto today |
| `weighting_scheme` | Trọng số nhóm | JSON | Y | 0 | Default: {Tech:35, Comm:25, Fin:10, Sup:15, Comp:15} |
| `criteria` | Tiêu chí | Table → Vendor Eval Criterion | Y | 0 | Seed từ default |
| `candidates` | Nhà cung cấp | Table → Vendor Eval Candidate | Y | 0 | ≥ 1 |
| `quotations` | Báo giá | Table → Vendor Quotation Line | C | 0 | Bắt buộc sau Open RFQ |
| `recommended_candidate` | Đề xuất | Data | N | 0 | **Supplier name** top weighted (auto, set bởi `_compute_eval_scores`) |
| `workflow_state` | Trạng thái | Workflow State | Y | 0 | 5 states |
| `docstatus` | Doc Status | Int | Y | 0 | 0/1/2 |
| `amended_from` | Sửa đổi từ | Link → IMM Vendor Evaluation | N | 0 | — |

### II.2 IMM Procurement Decision

| Field | Label | Type | Req | Permlevel | Note |
|---|---|---|---|---|---|
| `name` | Mã quyết định | Data (auto) | Y | 0 | Naming: `PD-.YY.-.#####` |
| `spec_ref` | Tech Spec | Link → IMM Tech Spec | Y | 0 | — |
| `evaluation_ref` | Phiếu đánh giá | Link → IMM Vendor Evaluation | Y | 0 | — |
| `plan_ref` | Kế hoạch | Link → IMM Procurement Plan | Y | 0 | — |
| `plan_line` | Dòng kế hoạch | Data | N | 0 | Mirror |
| `procurement_method` | Phương án | Select | Y | 0 | Chỉ định/Chào hàng/Đấu thầu rộng rãi/Mua sắm trực tiếp/Mua sắm tập trung |
| `method_legal_basis` | Cơ sở pháp lý | Long Text | C | 0 | Bắt buộc với Chỉ định thầu |
| `winner_supplier` | NCC trúng thầu | Link → AC Supplier | Y | 0 | Từ evaluation.recommended_candidate |
| `awarded_price` | Giá trúng thầu | Currency | Y | **1** | Chỉ KH-TC/TCKT/PTP Khối 1/VP Block1 |
| `envelope_check_pct` | % envelope | Percent | N | **1** | Auto = awarded/allocated*100 |
| `funding_source` | Nguồn vốn | Select | Y | **1** | NSNN/Tài trợ/Xã hội hóa/BHYT/Khác |
| `funding_evidence` | Chứng từ nguồn vốn | Attach | C | **1** | Bắt buộc khi Tài trợ/XHH |
| `board_approver` | Người phê duyệt | Link → User | C | **1** | Bắt buộc trước Awarded |
| `contract_no` | Số hợp đồng | Data | C | 0 | Bắt buộc ở Contract Signed |
| `contract_doc` | Hợp đồng | Attach | C | **1** | Bắt buộc ở G05 |
| `ac_purchase_ref` | AC Purchase | Link → AC Purchase | N | 0 | Auto sau award (read-only) |
| `awarded_date` | Ngày awarded | Date | N | 0 | Auto on_submit |
| `workflow_state` | Trạng thái | Workflow State | Y | 0 | 9 states |
| `docstatus` | Doc Status | Int | Y | 0 | 0/1/2 |

### II.3 IMM AVL Entry

| Field | Label | Type | Req | Permlevel | Note |
|---|---|---|---|---|---|
| `name` | Mã AVL | Data (auto) | Y | 0 | Naming: `AVL-.YYYY.-.#####` |
| `supplier` | Nhà cung cấp | Link → AC Supplier | Y | 0 | — |
| `device_category` | Nhóm thiết bị | Link → Asset Category | Y | 0 | — |
| `validity_years` | Hiệu lực (năm) | Int | Y | 0 | 1–3 |
| `valid_from` | Ngày hiệu lực | Date | Y | 0 | — |
| `valid_to` | Ngày hết hạn | Date | N | 0 | Auto = valid_from + validity_years (validate_avl) |
| `workflow_state` | Trạng thái | Workflow State | Y | 0 | Draft/Approved/Conditional/Suspended/Expired (AVL workflow). KHÔNG có field `status` riêng — chỉ dùng `workflow_state`. |
| `approver` | Người ký AVL | Link → User | C | 0 | Set khi approve |
| `approval_doc` | Tài liệu phê duyệt | Attach | C | 0 | Set khi approve |
| `condition_notes` | Điều kiện | Long Text | C | 0 | Khi Conditional |
| `suspension_reason` | Lý do đình chỉ | Long Text | C | 0 | `_suspend_avl` enforce non-empty |
| `docstatus` | Doc Status | Int | Y | 0 | 0/1 |
| `amended_from` | Amended From | Link | N | 0 | — |

### II.4 IMM Vendor Scorecard

| Field | Label | Type | Req | Permlevel | Note |
|---|---|---|---|---|---|
| `name` | Mã Scorecard | Data (auto) | Y | 0 | `VS-.YYYY.-.QN-.{Vendor}` |
| `period_year` | Năm | Int | Y | 0 | — |
| `period_quarter` | Quý | Int | Y | 0 | 1–4 |
| `supplier` | Nhà cung cấp | Link → AC Supplier | Y | 0 | — |
| `kpi_rows` | KPI chi tiết | Table → Scorecard KPI Row | Y | 0 | 5 dimensions |
| `overall_score` | Điểm tổng | Float | N | 0 | Auto từ kpi_rows |
| `commentary` | Nhận xét | Long Text | N | 0 | — |
| `generated_at` | Thời điểm tạo | Datetime | N | 0 | Auto |

### II.5 IMM Supplier Audit

> Ground truth: doctype `imm_supplier_audit`. Parent ref tới AC Supplier dùng fieldname `supplier` (không phải `vendor`).

| Field | Label | Type | Req | Permlevel | Note |
|---|---|---|---|---|---|
| `name` | Mã audit | Data (auto) | Y | 0 | `SA-.YY.-.#####` |
| `supplier` | Nhà cung cấp | Link → AC Supplier | Y | 0 | — |
| `audit_date` | Ngày audit | Date | Y | 0 | — |
| `audit_type` | Loại audit | Select | Y | 0 | Initial/Periodic/For-Cause |
| `auditors` | Kiểm toán viên | Small Text | Y | 0 | — |
| `findings` | Phát hiện | Table → Audit Finding | N | 0 | — |
| `overall_result` | Kết quả | Select | Y | 0 | Pass/Conditional/Fail |
| `capa_required` | Cần CAPA | Check | N | 0 | — |
| `follow_up_date` | Ngày theo dõi | Date | C | 0 | Bắt buộc khi Conditional/Fail |
| `docstatus` | Doc Status | Int | Y | 0 | 0/1 |

---

## III. Field Tables — Child DocTypes

### III.1 Vendor Eval Criterion

| Field | Type | Note |
|---|---|---|
| `group` | Select | Technical/Commercial/Financial/Support/Compliance |
| `criterion` | Data | Tên tiêu chí |
| `weight_pct` | Percent | Trọng số trong nhóm |
| `description` | Small Text | Mô tả |
| `scorer_role` | Select | HTM/KH-TC/TCKT/QA Risk |

### III.2 Vendor Eval Candidate

| Field | Type | Note |
|---|---|---|
| `supplier` | Link → AC Supplier | — |
| `in_avl` | Check | Auto check AVL active for device category |
| `sign_off_non_avl` | Link → User | Bắt buộc nếu non-AVL (cảnh báo lúc add, throw lúc submit) |
| `scores` | JSON | `{"criterion_name": score_1_to_5}` per candidate |
| `weighted_score` | Float | Auto = Σ(score × criterion_weight × group_weight) |
| `notes` | Small Text | Nhận xét tổng |

### III.3 Vendor Quotation Line

| Field | Type | Note |
|---|---|---|
| `candidate_supplier` | Link → AC Supplier | Mapping với `candidates[].supplier` (KHÔNG dùng row name) |
| `quotation_no` | Data | Số báo giá |
| `quotation_date` | Date | — |
| `quotation_validity` | Date | VR-03-03: phải ≥ today tại thời điểm submit |
| `price` | Currency | — |
| `currency` | Link → Currency | — |
| `payment_terms` | Data | VD: 30/60 |
| `delivery_days` | Int | Ngày giao hàng |
| `warranty_months` | Int | Bảo hành (tháng) |
| `attachment` | Attach | File báo giá scan |

### III.4 Vendor Cert

| Field | Type | Note |
|---|---|---|
| `cert_type` | Select | ISO 9001/ISO 13485/ĐKLH BYT/GSP/GDP/CE/FDA/Other |
| `cert_number` | Data | Số chứng chỉ |
| `issued_by` | Data | Tổ chức cấp |
| `issued_date` | Date | — |
| `expiry_date` | Date | — |
| `attachment` | Attach | File scan |
| `status` | Select | Auto: Active (≥ 31d) / Expiring (≤ 30d) / Expired |

### III.5 Audit Finding

| Field | Type | Note |
|---|---|---|
| `severity` | Select | Minor/Major/Critical |
| `category` | Select | Quality/Compliance/Delivery/Documentation/Other |
| `description` | Long Text | Mô tả phát hiện |
| `capa_action` | Long Text | Hành động khắc phục |
| `capa_owner` | Link → User | Người chịu trách nhiệm |
| `capa_due` | Date | Hạn hoàn thành |
| `capa_status` | Select | Open/In Progress/Closed |

### III.6 Scorecard KPI Row

| Field | Type | Note |
|---|---|---|
| `dimension` | Select | Delivery/Quality/Aftersales/Spare/Compliance |
| `weight_pct` | Percent | Trọng số dimension |
| `raw_value` | Float | Giá trị thô (%, ngày, count) |
| `normalized_score` | Float | Scale 1–5 |
| `weighted` | Float | normalized × weight_pct / 100 |
| `source_module` | Data | VD: "IMM-04", "IMM-09" |

---

## IV. Custom Fields trên Wave 1 DocTypes

### IV.1 AC Supplier (Wave 1 — LIVE)

Patch `assetcore/patches/v3_1/003_install_imm03.py` gọi `create_custom_fields({"AC Supplier": _AC_SUPPLIER_CFIELDS}, ignore_validate=True, update=True)`:

```python
_AC_SUPPLIER_CFIELDS = [
    {"fieldname": "section_imm_avl", "fieldtype": "Section Break",
     "label": "IMM AVL & Audit", "insert_after": "notes"},
    {"fieldname": "imm_avl_status", "fieldtype": "Select",
     "label": "AVL Status", "insert_after": "section_imm_avl",
     "options": "\nApproved\nConditional\nSuspended\nExpired\nNot Applicable",
     "read_only": 1, "in_standard_filter": 1},
    {"fieldname": "imm_avl_categories", "fieldtype": "Small Text",
     "label": "AVL Categories", "insert_after": "imm_avl_status", "read_only": 1},
    {"fieldname": "imm_overall_score", "fieldtype": "Float",
     "label": "Overall Score", "insert_after": "imm_avl_categories",
     "read_only": 1, "precision": "4"},
    {"fieldname": "imm_last_audit_date", "fieldtype": "Date",
     "label": "Last Audit Date", "insert_after": "imm_overall_score", "read_only": 1},
    {"fieldname": "imm_next_audit_date", "fieldtype": "Date",
     "label": "Next Audit Due", "insert_after": "imm_last_audit_date", "read_only": 1},
    {"fieldname": "imm_certifications", "fieldtype": "Table",
     "label": "Certifications", "options": "Vendor Cert",
     "insert_after": "imm_next_audit_date"},
]
```

**Lưu ý field naming:** child Table custom field tên là `imm_certifications` (KHÔNG phải `certifications`). API `create_vendor_profile` set qua `doc.set("imm_certifications", [])`.

AC Supplier core fields đã có: `supplier_name`, `supplier_code`, `supplier_group`, `country`, `tax_id`, `website`, `address`, `phone`, `email_id`, `vendor_type`, `iso_17025_cert`, `iso_17025_expiry`, `iso_13485_cert`, `iso_13485_expiry`, `contract_start`, `contract_end`, `contract_value`, `service_contract_ref`, `authorized_technicians`. Các field tiếng Việt phụ (legal_name, vat_code, rep_name, bank_account, device_categories, financial_health) KHÔNG có trong core; nếu nghiệp vụ cần phải bổ sung qua patch riêng.

### IV.2 AC Purchase (Wave 1 — LIVE)

Patch `v3_1.003_install_imm03` bổ sung qua `create_custom_fields({"AC Purchase": _AC_PURCHASE_CFIELDS, ...})`:

```python
_AC_PURCHASE_CFIELDS = [
    {"fieldname": "section_imm03", "fieldtype": "Section Break",
     "label": "IMM-03 Procurement", "insert_after": "notes"},
    {"fieldname": "imm_procurement_decision", "fieldtype": "Link",
     "label": "Procurement Decision", "options": "IMM Procurement Decision",
     "insert_after": "section_imm03", "read_only": 1, "in_standard_filter": 1},
    {"fieldname": "imm_tech_spec", "fieldtype": "Link",
     "label": "Tech Spec", "options": "IMM Tech Spec",
     "insert_after": "imm_procurement_decision", "read_only": 1},
    {"fieldname": "imm_funding_source", "fieldtype": "Select",
     "label": "Funding Source", "insert_after": "imm_tech_spec",
     "options": "\nNSNN\nTài trợ\nXã hội hóa\nBHYT\nKhác"},
]
```

AC Purchase core fields hiện tại: `naming_series`, `purchase_date`, `status`, `supplier`, `invoice_no`, `expected_delivery`, `devices` (child → AC Purchase Device Item), `items` (child → AC Purchase Item), `total_value`, `notes`.

---

## V. Service Layer — Function Signatures (LIVE)

File: `assetcore/services/imm03.py`

> ✅ Đã implement đầy đủ. Các hàm chính:

```python
from __future__ import annotations
import frappe
from frappe import _
from assetcore.services.shared import ServiceError, ErrorCode


# ─── Vendor Evaluation ───────────────────────────────────────────────────────
def validate_evaluation(doc: Document) -> None:
    """Hook validate: gọi _vr01, _vr03, _check_avl_warnings, _compute_eval_scores."""

def on_submit_evaluation(doc: Document) -> None:
    """Hook on_submit — no-op V1 (gate ở workflow transition)."""

def _vr01_min_candidates(doc: Document) -> None:
    """VR-03-01: msgprint warning nếu < 3 candidates (soft)."""

def _vr03_quotation_validity(doc: Document) -> None:
    """VR-03-03: throw ServiceError(VALIDATION) nếu có quotation hết hạn."""

def _check_avl_warnings(doc: Document) -> None:
    """Set in_avl flag per candidate; warning nếu non-AVL."""

def _is_supplier_in_avl(supplier: str, category: str | None) -> int:
    """Return 1 nếu supplier có AVL Approved/Conditional cho category."""

def _compute_eval_scores(doc: Document) -> None:
    """Compute weighted_score per candidate: Σ(score × criterion_weight × group_weight).
    Set recommended_candidate = top supplier name."""


# ─── Procurement Decision ────────────────────────────────────────────────────
def validate_decision(doc: Document) -> None:
    """Hook validate: gọi _validate_gate_g04_method, _vr04_envelope_check, _vr07_unique_decision_per_spec."""

def before_submit_decision(doc: Document) -> None:
    """Hook before_submit: gọi _vr05_winner_avl_required, _validate_gate_g05; set awarded_date."""

def on_submit_decision(doc: Document) -> None:
    """Hook on_submit: mint AC Purchase, update Plan Line, publish imm03_decision_awarded."""

def on_cancel_decision(doc: Document) -> None:
    """Hook on_cancel: revert Plan Line về 'In Procurement'."""

def _validate_gate_g04_method(doc: Document) -> None:
    """G04: method hợp pháp với awarded_price threshold; Chỉ định thầu cần method_legal_basis."""

def _vr04_envelope_check(doc: Document) -> None:
    """VR-03-04: awarded_price ≤ 105% allocated_budget; set envelope_check_pct."""

def _vr05_winner_avl_required(doc: Document) -> None:
    """VR-03-05: winner_supplier phải có AVL Approved/Conditional cho device_category."""

def _vr07_unique_decision_per_spec(doc: Document) -> None:
    """VR-03-07: 1 spec_ref ↔ 1 Decision Awarded/Contract Signed/PO Issued."""

def _validate_gate_g05(doc: Document) -> None:
    """G05: contract_doc + funding_source + board_approver đều phải có."""

def _mint_ac_purchase(doc: Document) -> str:
    """Tạo AC Purchase từ Decision; link imm_procurement_decision, imm_tech_spec, imm_funding_source."""


# ─── AVL ─────────────────────────────────────────────────────────────────────
def validate_avl(doc: Document) -> None:
    """Auto-compute valid_to = valid_from + validity_years."""

def activate_avl(doc: Document) -> None:
    """on_submit: gọi _sync_supplier_avl_status nếu state='Approved'."""

def _sync_supplier_avl_status(supplier: str) -> None:
    """Sync AC Supplier.imm_avl_status + imm_avl_categories từ active AVL entries."""


# ─── Supplier Audit ───────────────────────────────────────────────────────────
def on_submit_audit(doc: Document) -> None:
    """on_submit: update imm_last_audit_date/imm_next_audit_date; suspend AVL nếu Critical finding."""


# ─── AC Purchase hook (BR-03-08) ──────────────────────────────────────────────
def validate_ac_purchase_imm_link(doc: Document, method: str | None = None) -> None:
    """Soft warning (V1) nếu AC Purchase có device rows nhưng thiếu imm_procurement_decision."""


# ─── Schedulers ───────────────────────────────────────────────────────────────
def check_avl_expiry() -> None:
    """Daily: set AVL Expired cho valid_to < today; gọi _sync_supplier_avl_status."""

def check_audit_due() -> None:
    """Daily: log vendors có imm_next_audit_date <= today."""

def check_decision_overdue() -> None:
    """Daily: log Decisions Draft/Negotiation > 60 ngày."""

def update_vendor_scorecard() -> None:
    """Cron quarterly: tạo IMM Vendor Scorecard skeleton per active AVL supplier (idempotent)."""
```


```

> **Lưu ý:** Block "spec ban đầu" liệt kê thêm các helper như `add_vendor_to_evaluation`, `compute_eval_score`, `_vr02_avl_check`, `_vr06_immutable_lifecycle_events`, `_validate_gate_g01/02/03` ĐÃ ĐƯỢC REMOVE khỏi tài liệu vì KHÔNG có trong code. Các tên thực tế ở trên là ground truth.

---

## VI. Controller Hooks (LIVE)

File: `hooks.py`

> ✅ Hàm `on_submit_decision` (không phải `award_decision`) được dùng cho IMM Procurement Decision on_submit. Scheduler binding wire vào `services.imm03.*` (không có module `tasks_imm03`).

```python
doc_events = {
    "IMM Vendor Evaluation": {
        "validate":  "assetcore.services.imm03.validate_evaluation",
        "on_submit": "assetcore.services.imm03.on_submit_evaluation",
    },
    "IMM Procurement Decision": {
        "validate":      "assetcore.services.imm03.validate_decision",
        "before_submit": "assetcore.services.imm03.before_submit_decision",
        "on_submit":     "assetcore.services.imm03.on_submit_decision",  # mint AC Purchase
        "on_cancel":     "assetcore.services.imm03.on_cancel_decision",
    },
    "IMM AVL Entry": {
        "validate":  "assetcore.services.imm03.validate_avl",
        "on_submit": "assetcore.services.imm03.activate_avl",
    },
    "IMM Supplier Audit": {
        "on_submit": "assetcore.services.imm03.on_submit_audit",
    },
    "AC Purchase": {
        "validate":  "assetcore.services.imm03.validate_ac_purchase_imm_link",
    },
}

# Note: event listener `imm02_spec_locked → seed_evaluation_from_spec` đã được
# spec ban đầu, hiện CHƯA wire trong `hooks.py` và CHƯA implement trong
# `services/imm03.py` (Evaluation được khởi tạo qua endpoint `create_evaluation`).

scheduler_events = {
    "daily": [
        "assetcore.services.imm03.check_avl_expiry",
        "assetcore.services.imm03.check_audit_due",
        "assetcore.services.imm03.check_decision_overdue",
    ],
    "cron": {
        # Frappe v15 không có key "quarterly" → dùng cron expression
        "0 2 1 1,4,7,10 *": ["assetcore.services.imm03.update_vendor_scorecard"],
    },
}
```

---

## VII. Workflow State Machine

### VII.1 IMM Vendor Evaluation

| From State | Action (tiếng Việt) | To State | Role | Gate |
|---|---|---|---|---|
| — | (tạo mới) | `Draft` | IMM Procurement Officer | — |
| `Draft` | Mở RFQ | `Open RFQ` | IMM Procurement Officer | — |
| `Open RFQ` | Nộp báo giá | `Quotation Received` | IMM Procurement Officer | G02 |
| `Quotation Received` | Hoàn tất chấm điểm | `Evaluated` | IMM Department Head | G01 |
| `Draft` / `Open RFQ` | Huỷ | `Cancelled` | IMM Department Head | — |

Workflow file: `imm_03_vendor_eval_workflow.json`

### VII.2 IMM Procurement Decision

| From State | Action (tiếng Việt) | To State | Role | Gate |
|---|---|---|---|---|
| — | (tạo mới) | `Draft` | IMM Procurement Officer | — |
| `Draft` | Chọn phương án | `Method Selected` | IMM Procurement Officer | G04 |
| `Method Selected` | Bắt đầu thương lượng | `Negotiation` | IMM Procurement Officer | — |
| `Negotiation` | Đề xuất trúng thầu | `Award Recommended` | IMM Procurement Officer | G01+G03 |
| `Award Recommended` | Trình BGĐ | `Pending Approval` | IMM Department Head | — |
| `Pending Approval` | Phê duyệt & Award | `Awarded` | IMM Board Approver | G05 |
| `Awarded` | Ký hợp đồng | `Contract Signed` | IMM Finance Officer | — |
| `Contract Signed` | Phát hành PO | `PO Issued` | IMM Procurement Officer | — |
| bất kỳ (trước Awarded) | Huỷ | `Cancelled` | IMM Department Head | — |

Workflow file: `imm_03_decision_workflow.json`

### VII.3 IMM AVL Entry

| From State | Action | To State | Role |
|---|---|---|---|
| — | (tạo mới) | `Draft` | IMM Procurement Officer |
| `Draft` | Phê duyệt AVL | `Approved` | IMM Board Approver |
| `Draft` | Cấp Conditional | `Conditional` | IMM Risk Officer |
| `Approved` | Hạ xuống Conditional | `Conditional` | IMM Risk Officer |
| `Approved` | Đình chỉ | `Suspended` | IMM Risk Officer |
| `Conditional` | Phục hồi Approved | `Approved` | IMM Board Approver |
| `Conditional` | Đình chỉ | `Suspended` | IMM Risk Officer |
| `Suspended` | Phục hồi Approved | `Approved` | IMM Board Approver |
| (auto scheduler) | — | `Expired` | System (`check_avl_expiry` qua `frappe.db.set_value`) |

Workflow file: `imm_03_avl_workflow.json` (5 states · 7 transitions). Endpoint `approve_avl` xử lý cả Draft→Approved (qua `doc.submit()`) và Conditional/Suspended→Approved (qua `doc.save()` trên submitted doc).

---

## VIII. Schedulers

| Job | File | Tần suất | Mô tả |
|---|---|---|---|
| `check_avl_expiry` | `services/imm03.py` | daily | AVL hết hạn → Expired; 30/60d trước → cảnh báo email |
| `check_audit_due` | `services/imm03.py` | daily | Vendor > 12 tháng chưa audit → tạo SA task |
| `check_decision_overdue` | `services/imm03.py` | daily | Decision Draft/Negotiation > 60d → cảnh báo PTP Khối 1 |
| `update_vendor_scorecard` | `services/imm03.py` | cron `0 2 1 1,4,7,10 *` | Tổng hợp KPI vendor từ IMM-04/09/15/10 |

> Ghi chú: spec ban đầu tách `tasks_imm03.py`; bản LIVE gộp scheduler vào `services/imm03.py` để giảm số module — wire trong `hooks.py` (`scheduler_events.daily` + `scheduler_events.cron`).

---

## IX. Database Indexes

```sql
-- IMM Vendor Evaluation
CREATE INDEX idx_imm_ve_spec_ref ON `tabIMM Vendor Evaluation`(spec_ref);
CREATE INDEX idx_imm_ve_workflow ON `tabIMM Vendor Evaluation`(workflow_state, docstatus);

-- IMM Procurement Decision
CREATE INDEX idx_imm_pd_spec_ref ON `tabIMM Procurement Decision`(spec_ref);
CREATE INDEX idx_imm_pd_vendor ON `tabIMM Procurement Decision`(winner_supplier, docstatus);
CREATE INDEX idx_imm_pd_workflow ON `tabIMM Procurement Decision`(workflow_state, docstatus);
CREATE INDEX idx_imm_pd_plan ON `tabIMM Procurement Decision`(plan_ref);

-- IMM AVL Entry
CREATE INDEX idx_imm_avl_supplier ON `tabIMM AVL Entry`(supplier, device_category);
CREATE INDEX idx_imm_avl_workflow ON `tabIMM AVL Entry`(workflow_state, valid_to);

-- IMM Vendor Scorecard
CREATE INDEX idx_imm_vs_period ON `tabIMM Vendor Scorecard`(period_year, period_quarter, supplier);
CREATE UNIQUE INDEX uidx_imm_vs ON `tabIMM Vendor Scorecard`(period_year, period_quarter, supplier);

-- IMM Supplier Audit
CREATE INDEX idx_imm_sa_supplier ON `tabIMM Supplier Audit`(supplier, audit_date);
```

---

## X. Migration Patches

> ✅ Thực tế bản LIVE gộp toàn bộ bootstrap IMM-03 vào 1 patch v3.1 (DocType + workflow + custom field + seed) thay vì 6 patch riêng như spec ban đầu.

| Patch | File | Mục đích |
|---|---|---|
| `v3_1.003_install_imm03` | `patches/v3_1/003_install_imm03.py` | Bootstrap DocType + custom field AC Supplier/AC Purchase + workflow + seed |

Đăng ký trong `patches.txt`:
```
assetcore.patches.v3_1.003_install_imm03
```
