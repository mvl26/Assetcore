# 04 — Thiết kế Backend — IMM-03 Đánh giá Nhà cung cấp & Quyết định Mua sắm

> ✅ Module LIVE — Wave 2. File `assetcore/services/imm03.py` và `assetcore/api/imm03.py` đã implement đầy đủ.

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-03 — Vendor Evaluation & Procurement Decision |
| Phiên bản | 0.1.0 |
| Ngày | 2026-05-08 |
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
| `recommended_candidate` | Đề xuất | Data | N | 0 | Row name top weighted (auto) |
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
| `valid_to` | Ngày hết hạn | Date | N | 0 | Auto = valid_from + validity_years |
| `status` | Trạng thái | Select | Y | 0 | Draft/Approved/Conditional/Suspended/Expired |
| `approval_doc` | Tài liệu phê duyệt | Attach | C | 0 | Bắt buộc khi Approved |
| `approver` | Người ký AVL | Link → User | C | 0 | Bắt buộc khi Approved |
| `condition_notes` | Điều kiện | Long Text | C | 0 | Bắt buộc khi Conditional |
| `suspension_reason` | Lý do đình chỉ | Long Text | C | 0 | Bắt buộc khi Suspended |
| `workflow_state` | Trạng thái | Workflow State | Y | 0 | AVL workflow |
| `docstatus` | Doc Status | Int | Y | 0 | 0/1 |

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
| `candidate_row` | Data | Row name từ candidates table |
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

Patch `add_supplier_imm_fields` bổ sung:

```python
custom_fields = {
    "AC Supplier": [
        {"fieldname": "imm_avl_status",      "label": "Trạng thái AVL",
         "fieldtype": "Select",
         "options": "Approved\nConditional\nSuspended\nExpired\nNot Applicable",
         "read_only": 1, "insert_after": "supplier_type"},
        {"fieldname": "imm_avl_categories",  "label": "Nhóm thiết bị AVL",
         "fieldtype": "Small Text", "read_only": 1},
        {"fieldname": "imm_last_audit_date", "label": "Ngày audit gần nhất",
         "fieldtype": "Date", "read_only": 1},
        {"fieldname": "imm_next_audit_date", "label": "Ngày audit tiếp theo",
         "fieldtype": "Date", "read_only": 1},
        {"fieldname": "imm_overall_score",   "label": "Điểm tổng hợp",
         "fieldtype": "Float", "read_only": 1},
        {"fieldname": "certifications",      "label": "Chứng chỉ",
         "fieldtype": "Table", "options": "Vendor Cert"},
    ]
}
```

Các field hồ sơ pháp lý (`legal_name`, `vat_code`, `country`, `rep_name`, `rep_phone`, `rep_email`, `bank_name`, `bank_account`, `device_categories`, `scope_of_supply`, `financial_health`) — kiểm tra `ac_supplier.json` trước; chỉ thêm nếu chưa có để tránh duplicate.

### IV.2 AC Purchase (Wave 1 — LIVE)

Patch `add_po_imm_fields` bổ sung:

```python
custom_fields = {
    "AC Purchase": [
        {"fieldname": "imm_procurement_decision", "label": "Quyết định mua sắm",
         "fieldtype": "Link", "options": "IMM Procurement Decision",
         "read_only": 1},
        {"fieldname": "imm_tech_spec",            "label": "Tech Spec",
         "fieldtype": "Link", "options": "IMM Tech Spec",
         "read_only": 1},
        {"fieldname": "imm_funding_source",       "label": "Nguồn vốn",
         "fieldtype": "Select",
         "options": "NSNN\nTài trợ\nXã hội hóa\nBHYT\nKhác"},
    ]
}
```

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


def add_vendor_to_evaluation(eval_name: str, supplier: str) -> dict:
    """Thêm candidate vào Vendor Evaluation; kiểm tra AVL.

    Args:
        eval_name: tên IMM Vendor Evaluation
        supplier: tên AC Supplier

    Returns:
        dict: {"row": row_name, "in_avl": bool, "warning": str | None}

    Raises:
        ServiceError(BAD_STATE): nếu Evaluation không ở Draft/Open RFQ
        ServiceError(DUPLICATE): nếu supplier đã là candidate
    """
    ...


def compute_eval_score(eval_doc: "Document") -> None:
    """Tính weighted_score cho mọi candidate; set recommended_candidate.

    Công thức: Σ(score_i × criterion_weight_i × group_weight_g) per candidate.
    Sort candidates desc by weighted_score.

    Args:
        eval_doc: IMM Vendor Evaluation document (mutable)
    """
    weights = eval_doc.weighting_scheme  # group weights dict
    for cand in eval_doc.candidates:
        cand_total = 0.0
        for crit in eval_doc.criteria:
            score = (cand.scores or {}).get(crit.criterion, 0)
            grp_w = weights.get(crit.group, 0) / 100
            crit_w = crit.weight_pct / 100
            cand_total += score * grp_w * crit_w
        cand.weighted_score = round(cand_total, 4)
    eval_doc.candidates.sort(key=lambda c: c.weighted_score, reverse=True)
    eval_doc.recommended_candidate = (
        eval_doc.candidates[0].name if eval_doc.candidates else None
    )


def validate_evaluation(eval_doc: "Document") -> None:
    """Hook validate cho IMM Vendor Evaluation.

    Gọi: _vr01, _vr02, _vr03; compute_eval_score.
    """
    ...


def _vr01_min_candidates(doc: "Document") -> None:
    """VR-03-01: Số candidate phù hợp phương án mua sắm.

    Đấu thầu rộng rãi / Chào hàng cạnh tranh: ≥ 3.
    Chỉ định thầu / Mua sắm trực tiếp: = 1.

    Raises:
        ServiceError(BUSINESS_RULE, "VR-03-01: ...")
    """
    ...


def _vr02_avl_check(doc: "Document") -> None:
    """VR-03-02: Vendor non-AVL phải có sign_off_non_avl trước submit.

    Raises:
        ServiceError(BUSINESS_RULE, "VR-03-02: Vendor non-AVL — cần sign-off IMM Board Approver")
    """
    ...


def _vr03_quotation_validity(doc: "Document") -> None:
    """VR-03-03: Quotation chưa hết hạn (quotation_validity >= today).

    Raises:
        ServiceError(VALIDATION, "VR-03-03: Quotation hết hiệu lực")
    """
    ...


def validate_decision(decision_doc: "Document") -> None:
    """Hook validate cho IMM Procurement Decision.

    Gọi: _vr04, _vr05, _vr06, _vr07.
    """
    ...


def _vr04_decision_within_envelope(doc: "Document") -> None:
    """VR-03-04: awarded_price ≤ 105% allocated_budget.

    Warning (không block) nếu 100%–105%; throw nếu > 105% và không có justification.

    Raises:
        ServiceError(CONFLICT, "VR-03-04: Awarded > 105% envelope — cần giải trình")
    """
    ...


def _vr05_avl_active_required(doc: "Document") -> None:
    """VR-03-05: Winner phải có AVL Active hoặc Conditional + sign-off.

    Raises:
        ServiceError(BUSINESS_RULE, "VR-03-05: Winner phải có AVL Active hoặc Conditional + sign-off")
    """
    ...


def _vr06_immutable_lifecycle_events(doc: "Document") -> None:
    """VR-03-06: IMM Audit Trail không được sửa/xóa.

    Raises:
        ServiceError(BUSINESS_RULE, "VR-03-06: Audit trail bất biến")
    """
    ...


def _vr07_unique_decision_per_spec(doc: "Document") -> None:
    """VR-03-07: 1 Tech Spec ↔ 1 IMM Procurement Decision Awarded.

    Raises:
        ServiceError(DUPLICATE, "VR-03-07: Tech Spec đã có Decision Awarded")
    """
    ...


def _validate_gate_g01(doc: "Document") -> None:
    """Gate G01: Vendor Evaluation đủ candidate + criteria full + scoring complete (tất cả 5 group).

    Raises:
        ServiceError(BUSINESS_RULE, "G01: ...")
    """
    ...


def _validate_gate_g02(doc: "Document") -> None:
    """Gate G02: ≥ 1 quotation hợp lệ (không hết hạn).

    Raises:
        ServiceError(BUSINESS_RULE, "G02: Cần ≥ 1 báo giá hợp lệ trước Quotation Received")
    """
    ...


def _validate_gate_g03(doc: "Document") -> None:
    """Gate G03: AVL check pass (Active) hoặc Conditional + sign-off trước Award Recommended.

    Raises:
        ServiceError(BUSINESS_RULE, "G03: ...")
    """
    ...


def _validate_gate_g04(doc: "Document") -> None:
    """Gate G04: phương án mua sắm hợp pháp theo NĐ — giá trị + loại hàng + số lượng quote.

    Raises:
        ServiceError(BUSINESS_RULE, "G04: Phương án mua sắm không hợp lệ — ...")
    """
    ...


def _validate_gate_g05(doc: "Document") -> None:
    """Gate G05: contract_doc + funding_source + board_approver đều có.

    Raises:
        ServiceError(BUSINESS_RULE, "G05: Thiếu contract_doc / funding_source / board_approver")
    """
    ...


def award_decision(decision_doc: "Document") -> None:
    """on_submit hook: mint AC Purchase từ Procurement Decision.

    Side effects:
        - Tạo AC Purchase với imm_procurement_decision link
        - Ghi IMM Audit Trail
        - Cập nhật Procurement Plan Line.status = "Awarded"
        - Publish realtime imm03_decision_awarded

    Raises:
        ServiceError(INTERNAL, "Mint AC Purchase thất bại — Decision rollback về Pending Approval")
    """
    ...


def on_cancel_decision(decision_doc: "Document") -> None:
    """on_cancel hook: rollback AC Purchase nếu có.

    Raises:
        ServiceError(BAD_STATE, "Không thể huỷ Decision đã PO Issued")
    """
    ...


def validate_avl(avl_doc: "Document") -> None:
    """Hook validate cho IMM AVL Entry.

    Raises:
        ServiceError(VALIDATION, "validity_years phải từ 1–3")
    """
    ...


def activate_avl(avl_doc: "Document") -> None:
    """on_submit hook: set valid_to; cập nhật AC Supplier.imm_avl_status.

    Side effects:
        - avl_doc.valid_to = valid_from + relativedelta(years=validity_years)
        - AC Supplier.imm_avl_status = "Approved"
        - AC Supplier.imm_avl_categories thêm device_category
    """
    ...


def on_submit_audit(audit_doc: "Document") -> None:
    """on_submit hook cho IMM Supplier Audit.

    Side effects:
        - Cập nhật AC Supplier.imm_last_audit_date, imm_next_audit_date
        - Nếu có finding Critical → suspend AVL + email VP Block1
    """
    ...


def validate_ac_purchase_imm_link(po_doc: "Document") -> None:
    """Hook validate trên AC Purchase — gate IMM-03 compliance.

    Nếu item là thiết bị y tế (AC Asset Category in HTM scope)
    và imm_procurement_decision rỗng → throw.

    Raises:
        ServiceError(BUSINESS_RULE,
            "VR-03-08: AC Purchase TBYT phải đi qua IMM-03 Procurement Decision")
    """
    ...


def update_vendor_scorecard(vendor: str | None = None,
                            period: dict | None = None) -> None:
    """Scheduler quarterly: tổng hợp KPI từ IMM-04/09/15/10 → upsert Scorecard.

    Args:
        vendor: tên AC Supplier (None = tất cả active vendors)
        period: {"year": int, "quarter": int} (None = current quarter)

    Idempotent: re-run cùng (year, quarter, vendor) không tạo duplicate.
    """
    ...


def check_avl_expiry() -> None:
    """Scheduler daily: set AVL Expired + cảnh báo 60/30 ngày.

    Side effects:
        - AVL valid_to <= today → status = "Expired"; Supplier.imm_avl_status update
        - AVL valid_to in [today+1..today+60] → sendmail cảnh báo
    """
    ...


def check_audit_due() -> None:
    """Scheduler daily: vendor > 12 tháng chưa audit → tạo IMM Supplier Audit task.

    Side effects:
        - Tạo SA record cho QA Risk Team
    """
    ...


def check_decision_overdue() -> None:
    """Scheduler daily: Decision Draft/Negotiation > 60 ngày → cảnh báo PTP Khối 1."""
    ...
```

---

## VI. Controller Hooks (LIVE)

File: `hooks.py`

> ✅ Hàm `on_submit_decision` (không phải `award_decision`) được dùng cho IMM Procurement Decision on_submit.

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

event_listeners = {
    "imm02_spec_locked": "assetcore.services.imm03.seed_evaluation_from_spec",
}

scheduler_events = {
    "daily": [
        "assetcore.tasks_imm03.check_avl_expiry",
        "assetcore.tasks_imm03.check_audit_due",
        "assetcore.tasks_imm03.check_decision_overdue",
    ],
    "cron": {
        # Frappe v15 không có key "quarterly" → dùng cron expression
        "0 2 1 1,4,7,10 *": ["assetcore.tasks_imm03.update_vendor_scorecard"],
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
| `Approved` | Chuyển điều kiện | `Conditional` | IMM Board Approver |
| `Approved` / `Conditional` | Đình chỉ | `Suspended` | IMM Board Approver / IMM Risk Officer |
| (auto scheduler) | — | `Expired` | System |

Workflow file: `imm_03_avl_workflow.json`

---

## VIII. Schedulers

| Job | File | Tần suất | Mô tả |
|---|---|---|---|
| `check_avl_expiry` | `tasks_imm03.py` | daily | AVL hết hạn → Expired; 30/60d trước → cảnh báo email |
| `check_audit_due` | `tasks_imm03.py` | daily | Vendor > 12 tháng chưa audit → tạo SA task |
| `check_decision_overdue` | `tasks_imm03.py` | daily | Decision Draft/Negotiation > 60d → cảnh báo PTP Khối 1 |
| `update_vendor_scorecard` | `tasks_imm03.py` | cron `0 2 1 1,4,7,10 *` | Tổng hợp KPI vendor từ IMM-04/09/15/10 |

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
CREATE INDEX idx_imm_avl_status ON `tabIMM AVL Entry`(status, valid_to);

-- IMM Vendor Scorecard
CREATE INDEX idx_imm_vs_period ON `tabIMM Vendor Scorecard`(period_year, period_quarter, supplier);
CREATE UNIQUE INDEX uidx_imm_vs ON `tabIMM Vendor Scorecard`(period_year, period_quarter, supplier);

-- IMM Supplier Audit
CREATE INDEX idx_imm_sa_vendor ON `tabIMM Supplier Audit`(vendor, audit_date);
```

---

## X. Migration Patches

| Patch | File | Mục đích |
|---|---|---|
| `v0_1_0.create_imm03_doctypes` | `patches/v0_1_0/create_imm03_doctypes.py` | Bootstrap 5 primary DocType + 6 child |
| `v0_1_0.add_supplier_imm_fields` | `patches/v0_1_0/add_supplier_imm_fields.py` | Custom fields `imm_avl_*` trên AC Supplier |
| `v0_1_0.add_po_imm_fields` | `patches/v0_1_0/add_po_imm_fields.py` | Custom fields `imm_procurement_*` trên AC Purchase |
| `v0_1_0.install_imm03_workflows` | `patches/v0_1_0/install_imm03_workflows.py` | Deploy 3 Workflow JSON |
| `v0_1_0.seed_eval_criteria_default` | `patches/v0_1_0/seed_eval_criteria_default.py` | Default criteria 5 nhóm + trọng số |
| `v0_1_0.seed_procurement_method_config` | `patches/v0_1_0/seed_procurement_method_config.py` | Master ngưỡng giá theo NĐ hiện hành |

Đăng ký trong `patches.txt`:
```
assetcore.patches.v0_1_0.create_imm03_doctypes
assetcore.patches.v0_1_0.add_supplier_imm_fields
assetcore.patches.v0_1_0.add_po_imm_fields
assetcore.patches.v0_1_0.install_imm03_workflows
assetcore.patches.v0_1_0.seed_eval_criteria_default
assetcore.patches.v0_1_0.seed_procurement_method_config
```
