# 04 — Thiết kế Backend — IMM-03 Đánh giá Nhà cung cấp & Quyết định Mua sắm

> ✅ Module LIVE — Wave 2. File `assetcore/services/imm03.py` và `assetcore/api/imm03.py` đã implement đầy đủ.

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-03 — Vendor Evaluation & Procurement Decision |
| Phiên bản | 0.1.1 |
| Ngày | 2026-05-18 |
| Trạng thái | LIVE — Wave 2 (updated: set_actual_delivery, validate_receipt_against_po, _mint_ac_purchase) |

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
| `plan_line` | Dòng kế hoạch | Data | N | 0 | read_only=1 — chỉ hiển thị; mirror từ spec |
| `draft_date` | Ngày lập | Date | Y | 0 | Auto today |
| `weighting_scheme` | Trọng số nhóm | JSON | N | 0 | Optional; default {Tech:35, Comm:25, Fin:10, Sup:15, Comp:15} trong service |
| `criteria` | Tiêu chí | Table → Vendor Eval Criterion | N | 0 | Optional ở DocType; service tính score từ criteria.weight_pct |
| `candidates` | Nhà cung cấp | Table → Vendor Eval Candidate | N | 0 | ≥ 1; không reqd ở DocType level |
| `quotations` | Báo giá | Table → Vendor Quotation Line | N | 0 | Optional; VR-03-03 chỉ chạy khi có rows |
| `recommended_candidate` | Đề xuất | Data | N | 0 | **Supplier name** top weighted **DUY NHẤT** (auto, set bởi `_compute_eval_scores`). **Rỗng/None khi đỉnh HÒA** (≥2 candidate cùng điểm tối đa) — xem INV-VE-TIE (§IV.7) |
| `has_top_tie` | Hòa đỉnh | Check (Int 0/1) | N | 0 | Auto, set bởi `_compute_eval_scores` = 1 khi ≥2 candidate đồng hạng nhất (read_only). Surface cờ cho FE + audit |
| `tied_candidates` | NCC đồng hạng | Small Text | N | 0 | Auto, CSV supplier name đồng hạng nhất (read_only) khi `has_top_tie=1`; rỗng khi không hòa |
| `workflow_state` | Trạng thái | Workflow State | Y | 0 | 5 states |
| `docstatus` | Doc Status | Int | Y | 0 | 0/1/2 |
| `amended_from` | Sửa đổi từ | Link → IMM Vendor Evaluation | N | 0 | — |

### II.2 IMM Procurement Decision

| Field | Label | Type | Req | Permlevel | Note |
|---|---|---|---|---|---|
| `name` | Mã quyết định | Data (auto) | Y | 0 | Naming: `PD-.YY.-.#####` |
| `spec_ref` | Tech Spec | Link → IMM Tech Spec | Y | 0 | — |
| `evaluation_ref` | Phiếu đánh giá | Link → IMM Vendor Evaluation | Y | 0 | — |
| `plan_ref` | Kế hoạch | Link → IMM Procurement Plan | N | 0 | Auto-set từ spec.source_plan trong `create_decision` |
| `plan_line` | Dòng kế hoạch | Data | N | 0 | Mirror từ spec.source_plan_line |
| `procurement_method` | Phương án | Select | Y | 0 | Chỉ định/Chào hàng/Đấu thầu rộng rãi/Mua sắm trực tiếp/Mua sắm tập trung |
| `method_legal_basis` | Cơ sở pháp lý | Long Text | C | 0 | Bắt buộc với Chỉ định thầu |
| `winner_supplier` | NCC trúng thầu | Link → AC Supplier | N | 0 | Từ evaluation.recommended_candidate; bắt buộc tại `award_decision` (VR-03-05) |
| `awarded_price` | Giá trúng thầu | Currency | N | **1** | Bắt buộc tại Award; Chỉ KH-TC/TCKT/PTP Khối 1/VP Block1 xem được |
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
| `approver` | Người ký AVL | Link → User | C | 0 | Set = `frappe.session.user` khi approve (KHÔNG nhận từ client — chống spoof, ADR-IMM-03-04) |
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
    """Hook on_submit — gate ở workflow transition; NẾU doc.has_top_tie: ghi 1 dòng
    IMM Audit Trail bất biến (event_type='System', change_summary mở đầu
    'eval_tie_unresolved' + spec_ref + tied_candidates + điểm) qua
    utils.lifecycle.log_audit_event(asset=None, ...). Idempotent: bỏ qua nếu đã có
    audit row cho (ref_doctype='IMM Vendor Evaluation', ref_name=doc.name,
    event_type='System') chứa 'eval_tie_unresolved' (chống nhân đôi khi amend/resubmit)."""

def _vr01_min_candidates(doc: Document) -> None:
    """VR-03-01: msgprint warning nếu < 3 candidates (soft)."""

def _vr03_quotation_validity(doc: Document) -> None:
    """VR-03-03: throw ServiceError(VALIDATION) nếu có quotation hết hạn."""

def _check_avl_warnings(doc: Document) -> None:
    """Set in_avl flag per candidate; warning nếu non-AVL."""

def _avl_is_live(supplier: str, category: str | None = None) -> int:
    """SoT predicate 'AVL còn hiệu lực' (INV-AVL-LIVE, 02 §IV.6).
    Return 1 ⇔ tồn tại AVL của supplier với docstatus=1
              AND workflow_state ∈ {Approved, Conditional}
              AND (valid_to IS NULL OR valid_to >= CURDATE()).
    1 truy vấn (db.exists/get_value/sql 1 câu) — KHÔNG loop, KHÔNG migration.
    >= inclusive ⇒ biên valid_to==hôm-nay vẫn LIVE; khớp check_avl_expiry dùng <.
    Đây là predicate DUY NHẤT — mọi điểm gọi eligibility/cổng/KPI ủy quyền về đây."""

def _is_supplier_in_avl(supplier: str, category: str | None) -> int:
    """Eligibility flag candidate. Thân = `return _avl_is_live(supplier, category)`
    (giữ tên public cho backward-compat). KHÔNG còn check workflow_state thuần."""

def _compute_eval_scores(doc: Document) -> None:
    """Compute weighted_score per candidate: Σ(score × criterion_weight × group_weight),
    round(·×5, 4). Sau khi tính điểm:

    INV-VE-TIE (cổng tie-break — §IV.7):
      1. top = max(weighted_score) trên candidates.
      2. Nếu top <= 0 (chưa chấm): recommended_candidate=None, has_top_tie=0,
         tied_candidates=''  (giữ hành vi cũ — empty/zero PASS).
      3. tied = [c.supplier for c in candidates if abs((c.weighted_score or 0) - top) <= 1e-9].
      4. Nếu len(tied) == 1: recommended_candidate = tied[0]; has_top_tie=0;
         tied_candidates=''  (giữ hành vi cũ — higher-score-wins PASS).
      5. Nếu len(tied) >= 2 (HÒA đỉnh): recommended_candidate = None (KHÔNG auto-gợi-ý),
         KHÔNG raise; has_top_tie=1; tied_candidates = ','.join(sorted(tied)); +
         frappe.logger('imm03').warning structured 'eval_tie_unresolved' (spec_ref,
         suppliers, score=top). Audit Trail bất biến ghi ở on_submit_evaluation.

    Ordering tie-break THỨ CẤP (sorted supplier asc) CHỈ dùng để hiển thị thứ hạng FE,
    KHÔNG dùng để auto-chọn winner khi đỉnh hòa (phi-tất-định bị cấm — INV-VE-TIE).
    Hàm phải an toàn ở validate context (chạy mỗi save) — KHÔNG ghi DB ở đây."""


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
    """VR-03-05: winner_supplier phải có AVL **còn hiệu lực** cho device_category.
    Dùng `_avl_is_live(winner_supplier, category)` (SoT, 02 §IV.6) → raise
    ServiceError(BUSINESS_RULE) nếu trả 0. Chặn trao thầu cho AVL hết hạn trong
    cửa sổ trễ scheduler (INV-AVL-LIVE-1)."""

def _vr07_unique_decision_per_spec(doc: Document) -> None:
    """VR-03-07: 1 spec_ref ↔ 1 Decision Awarded/Contract Signed/PO Issued."""

def _validate_gate_g05(doc: Document) -> None:
    """G05: contract_doc + funding_source + board_approver đều phải có."""

def _mint_ac_purchase(doc: Document) -> str:
    """Tạo AC Purchase từ Decision.
    Wave 2 (2026-05-16): set `procurement_decision_ref` (native back-ref) ĐẦU TIÊN;
    nếu legacy field `imm_procurement_decision` tồn tại → cũng set (backward compat).
    Nếu `doc.plan_ref` có và `imm_procurement_plan` tồn tại → cũng set."""

def _update_plan_line_status(plan_name: str, plan_line: str, status: str) -> None:
    """Cập nhật status của 1 row trong IMM Procurement Plan.plan_items.
    Gọi bởi on_submit_decision (→ 'Awarded') và on_cancel_decision (→ 'In Procurement').
    Wrap trong try/except — failure không block submit."""


# ─── AVL ─────────────────────────────────────────────────────────────────────
def validate_avl(doc: Document) -> None:
    """Auto-compute valid_to = valid_from + validity_years."""

def activate_avl(doc: Document) -> None:
    """on_submit: gọi _sync_supplier_avl_status nếu state='Approved'."""

def _sync_supplier_avl_status(supplier: str) -> None:
    """Sync AC Supplier.imm_avl_status + imm_avl_categories từ active AVL entries.
    Mệnh đề 'active' (workflow_state ∈ {Approved,Conditional} AND (valid_to IS NULL
    OR valid_to >= CURDATE())) là **reference predicate** của `_avl_is_live`
    (INV-AVL-LIVE-3 parity). KHÔNG đổi mệnh đề này lẻ — đổi phải đồng bộ `_avl_is_live`."""


# ─── Supplier Audit ───────────────────────────────────────────────────────────
def on_submit_audit(doc: Document) -> None:
    """on_submit: update imm_last_audit_date/imm_next_audit_date; suspend AVL nếu Critical finding."""


# ─── AC Purchase hooks ────────────────────────────────────────────────────────
def validate_ac_purchase_imm_link(doc: Document, method: str | None = None) -> None:
    """Soft warning (V1) nếu AC Purchase có device rows nhưng thiếu imm_procurement_decision."""

def set_actual_delivery_on_received(doc: Document, method: str | None = None) -> None:
    """Wave 2 (2026-05-16): khi AC Purchase chuyển sang status='Received' mà chưa có
    actual_delivery_date → tự set = today(). Idempotent. Wired vào hooks.py::doc_events."""

def validate_receipt_against_po(po_name: str, received_items: list) -> None:
    """Wave 2 (2026-05-16): kiểm tra hàng nhận vs PO — từng item (device_model / spare_part)
    phải có trong PO lines. Raise ServiceError(BUSINESS_RULE) nếu có mismatch.
    Gọi bởi stock agent trước khi ghi nhận receipt. Không idempotent — chỉ validate."""


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

### V.b List & Dashboard predicate đồng nhất `docstatus<2` (INV-DEC-DRILL — 02 §IV.8)

File: `assetcore/api/imm03.py`. Hai hàm phải đếm **cùng predicate** để bảo toàn INVARIANT card==drill cho 3 tile decision (`Awarded`/`Pending Approval`/`PO Issued`):

```python
def _dashboard_kpis():
    # decision_states = reference predicate (đã đúng): chỉ docstatus<2.
    decision_states = dict(frappe.db.sql(
        f"SELECT workflow_state, COUNT(*) FROM `tab{_DT_PD}` "
        f"WHERE docstatus<2 GROUP BY workflow_state"          # loại cancelled
    ))
    # ... eval_states / avl_active / avl_expiring_30d không đổi

def _list_decisions(filters, page, page_size):
    f = _parse_json(filters)
    f, or_filters = pop_search(f, ["name", "spec_ref"],
        link_search={"winner_supplier": (_DT_SUPPLIER, "supplier_name")})
    # INV-DEC-DRILL: bơm docstatus<2 mặc định nếu caller chưa truyền tường minh
    # → cả frappe.get_list (items) lẫn count_with_or (total) đều loại cancelled,
    #   khớp _dashboard_kpis.decision_states. Override được bằng filters={"docstatus": 2}.
    if "docstatus" not in f:
        f["docstatus"] = ["<", 2]
    page_size = max(1, min(page_size, 100))
    start = (max(1, page) - 1) * page_size
    items = frappe.get_list(_DT_PD, filters=f or None, or_filters=or_filters,
        fields=[...], order_by="creation desc", start=start, page_length=page_size)
    # ... enrich vendor_name / tech_spec_ref_name / ac_purchase_ref_name không đổi
    return {"items": items, "total": count_with_or(_DT_PD, f or None, or_filters)}
```

**Lý do (root cause):** `IMM Procurement Decision` là submittable; khi cancel (`docstatus=2`), `workflow_state` KHÔNG tự xoá. `frappe.get_list`/`frappe.db.count` (Frappe v15: `db_query.docstatus = docstatus or []`) KHÔNG áp `docstatus<2` mặc định → list cũ đếm dư bản huỷ so với tile. Bơm `docstatus<2` vào `f` (cùng dict dùng cho cả `get_list` và `count_with_or`) đảm bảo `items` và `total` đồng nhất với tile.

**Ràng buộc:** KHÔNG đổi field trả về, search, enrich, pagination, hay hành vi `_dashboard_kpis` ngoài việc giữ predicate đồng nhất. KHÔNG thêm field/migration/index (index `idx_imm_pd_workflow(workflow_state, docstatus)` §IX đã phủ cho count nhanh).

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
| `Method Selected` | Bắt đầu thương thảo | `Negotiation` | IMM Procurement Officer | — |
| `Negotiation` | Đề xuất trúng thầu | `Award Recommended` | IMM Procurement Officer | G01+G03 |
| `Award Recommended` | Trình BGĐ | `Pending Approval` | IMM Department Head | — |
| `Pending Approval` | Phê duyệt trúng thầu | `Awarded` | IMM Board Approver | G05 |
| `Pending Approval` | Huỷ Decision | `Cancelled` | IMM Department Head | — |
| `Awarded` | Ký HĐ | `Contract Signed` | IMM Finance Officer | — |
| `Contract Signed` | Phát hành PO | `PO Issued` | IMM Procurement Officer | — |

Workflow file: `imm_03_decision_workflow.json` (SoT = `fixtures/workflow.json` entry `'IMM-03 Decision Workflow'` — 9 state · **8 transition**).

> **⚠️ Self-Correction (drift action-label ↔ fixture — load-bearing cho server-driven CTA §VII.2.a).** Bảng cũ ghi 3 nhãn action **KHÔNG khớp** `fixtures/workflow.json`: `"Phê duyệt & Award"` → thực tế `"Phê duyệt trúng thầu"`; `"Ký hợp đồng"` → `"Ký HĐ"`; `"Bắt đầu thương lượng"` → `"Bắt đầu thương thảo"`. Ngoài ra cạnh huỷ **KHÔNG** phải "bất kỳ (trước Awarded)" — fixture chỉ khai **một** cạnh huỷ: `Pending Approval --[Huỷ Decision]--> Cancelled` (role `Procurement Manager`, `AssetCore Super Admin`, `System Manager`). Vì `allowed_transitions` (§VII.2.a) và invariant test khớp EXACT chuỗi action của fixture, mọi nhãn ở đây đã sửa về đúng SoT. Bảng canonical action+role cho 8 transition ở **07 §III.4** (đã đúng từ trước — dùng làm tham chiếu). Cột `Role` ở bảng này là **persona nghiệp vụ** (mapping người-dùng), khác `allowed` trong fixture là **Frappe workflow role** (`Procurement Manager`/`Commissioning Manager`/`Needs Manager` + `AssetCore Super Admin`/`System Manager`) — hai lớp, không lẫn.

### VII.2.a Server-driven CTA — `_DECISION_VALID_TRANSITIONS` + enrich `get_decision` (GATE-8 / LL-FE-51)

> **Bối cảnh lỗi thiết kế gốc (Self-Correction — desync client-map).** `DecisionDetailView.vue` gate nút CTA bằng hằng **client-side** `TRANSITIONS_BY_STATE` (5 key: Draft/Method Selected/Negotiation/Award Recommended/Contract Signed) + hardcode `workflow_state === 'Pending Approval'` (canAward) / `=== 'Awarded'` (canRecordContract). Client-map **THIẾU HẲN** nhánh `Pending Approval → ['Phê duyệt trúng thầu','Huỷ Decision']` và `Awarded → ['Ký HĐ']`. Hệ quả: ở **Pending Approval**, `availableActions` = `[]` → **KHÔNG render nút "Huỷ Decision"** dù fixture CẤP quyền huỷ cho `Procurement Manager`/`AssetCore Super Admin`/`System Manager` (QTV) → **QTV/Procurement Manager không huỷ được Decision**. Đây là anti-pattern dead-gate (cùng họ GATE-8/LL-FE-51 đã áp cho các màn *Detail khác) + drift (sửa fixture mà quên sửa FE map).

**Quyết định**: `get_decision` phát thêm khóa **server-driven** `allowed_transitions` = `_DECISION_VALID_TRANSITIONS.get(workflow_state, [])`. Map định nghĩa cạnh next-**action** hợp lệ cho MỖI workflow_state (khớp EXACT fixture). FE render nút CTA theo tập này, KHÔNG hardcode `workflow_state === 'X'`.

```python
# api/imm03.py — module-level const (near _DT_* constants, cùng module với get_decision)
# LƯU Ý ngữ nghĩa: value = tập ACTION (nhãn transition), KHÁC IMM-05
# (_DOC_VALID_TRANSITIONS value = next-STATE). Lý do: FE Decision gate theo nhãn
# hành động ('Phê duyệt trúng thầu'/'Ký HĐ') + endpoint transition_decision_workflow
# nhận `action`. Invariant test parse `t["action"]` (KHÔNG `t["next_state"]`).
_DECISION_VALID_TRANSITIONS: dict[str, list[str]] = {
    "Draft":             ["Chọn phương án"],
    "Method Selected":   ["Bắt đầu thương thảo"],
    "Negotiation":       ["Đề xuất trúng thầu"],
    "Award Recommended": ["Trình BGĐ"],
    "Pending Approval":  ["Phê duyệt trúng thầu", "Huỷ Decision"],
    "Awarded":           ["Ký HĐ"],
    "Contract Signed":   ["Phát hành PO"],
    "PO Issued":         [],   # terminal
    "Cancelled":         [],   # terminal
}
```

Trong `get_decision._get` (sau `_enrich_decision_chain`):

```python
doc["allowed_transitions"] = _DECISION_VALID_TRANSITIONS.get(doc.get("workflow_state"), [])
```

- **9 key** = đủ 9 state của fixture (kể cả 2 terminal `PO Issued`/`Cancelled` → `[]`). `.get(..., [])` = default-an-toàn cho state lạ/None → "không nút".
- `allowed_transitions` **CHỈ là hint hiển thị** (⊆ tập guard cho phép). **Enforcement thật** vẫn ở guard role của `apply_workflow` (qua `transition_decision_workflow`) + `award_decision` + `record_contract` — GIỮ NGUYÊN, KHÔNG nới lỏng. FE ẩn nút chỉ để UX (hết false-permissive "hiện nút rồi bấm mới 403").

**INV-CTA-03 (invariant chống drift — test bắt buộc, 07 §III.4):** đọc `fixtures/workflow.json` entry `'IMM-03 Decision Workflow'`, dựng `codomain[state] = set(t["action"] for t in transitions where t.state==state)`, seed MỌI state từ `states[]` (terminal → `set()`). Assert: (1) `set(_DECISION_VALID_TRANSITIONS.keys()) == set(states[])` (9 key); (2) với MỖI state `set(_DECISION_VALID_TRANSITIONS[state]) == codomain[state]`. Mirror `test_get_document_allowed_transitions_matches_workflow_fixture` của IMM-05. Thêm/sửa transition mà quên map → RED.

> **⚠️ Vị trí const (khớp code thật):** `_DECISION_VALID_TRANSITIONS` sống trong **`services/imm03.py`** (module-level, gần `_DT_*`), `get_decision` trong `api/imm03.py` gọi qua `svc._DECISION_VALID_TRANSITIONS.get(...)` — comment code-block ở trên ("api/imm03.py") là stale; giữ light-touch, đọc code là chuẩn. `_EVAL_VALID_TRANSITIONS` (§VII.2.b) đặt CÙNG chỗ `services/imm03.py` để đối xứng.

### VII.2.b Server-driven CTA Evaluation — `_EVAL_VALID_TRANSITIONS` + enrich `get_evaluation` (parity §VII.2.a, GATE-8 / LL-FE-51)

> **Bối cảnh (Self-Correction — parity + drift-guard).** `VendorEvalDetailView.vue` gate 4 nút CTA (`Mở RFQ`/`Nhận báo giá xong`/`Hoàn tất chấm điểm`/`Huỷ Eval`) bằng hằng **client-side** `TRANSITIONS_BY_STATE` (3 key) — bản sao FE của `'IMM-03 Vendor Eval Workflow'`. Song song lỗi Decision (§VII.2.a) nhưng nhánh Eval CHƯA migrate. Client-map hiện TÌNH CỜ khớp fixture (chưa gãy nút), nên đây là **hardening parity + đóng drift**, không phóng đại "đang hỏng".

**Quyết định**: `get_evaluation` phát thêm khóa **server-driven** `allowed_transitions` = `_EVAL_VALID_TRANSITIONS.get(workflow_state, [])`. Map định nghĩa cạnh next-**action** hợp lệ cho MỖI workflow_state (khớp EXACT fixture `'IMM-03 Vendor Eval Workflow'`). FE render nút CTA theo tập này, KHÔNG hardcode `workflow_state === 'X'`.

```python
# services/imm03.py — module-level const (cạnh _DECISION_VALID_TRANSITIONS, đối xứng)
# value = tập ACTION (nhãn transition), giống Decision; FE POST `action` sang
# transition_eval_workflow(name, action). Invariant test parse `t["action"]`.
_EVAL_VALID_TRANSITIONS: dict[str, list[str]] = {
    "Draft":              ["Mở RFQ"],
    "Open RFQ":           ["Nhận báo giá xong", "Huỷ Eval"],
    "Quotation Received": ["Hoàn tất chấm điểm", "Huỷ Eval"],
    "Evaluated":          [],   # terminal (docstatus 1)
    "Cancelled":          [],   # terminal (docstatus 1)
}
```

Trong `get_evaluation._get` (parity `get_decision`, sau enrich supplier_name + `_enrich_decision_chain`):

```python
doc["allowed_transitions"] = svc._EVAL_VALID_TRANSITIONS.get(doc.get("workflow_state"), [])
```

- **5 key** = đủ 5 state của fixture (kể cả 2 terminal `Evaluated`/`Cancelled` → `[]`). `.get(..., [])` = default-an-toàn cho state lạ/None → "không nút".
- **KHÁC Decision**: Eval KHÔNG có action-form riêng (Decision có `award_decision`/`record_contract` cho 2 action). MỌI action Eval đi qua 1 endpoint `transition_eval_workflow(name, action)` → FE `availableActions = allowed_transitions` trọn tập (không `.filter`).
- `allowed_transitions` **CHỈ là hint hiển thị** (⊆ tập guard cho phép). **Enforcement thật** vẫn ở guard role của `apply_workflow` (qua `transition_eval_workflow`) — GIỮ NGUYÊN, KHÔNG nới lỏng. Lưu ý per-role: fixture cấp `Huỷ Eval` cho `Commissioning Manager`/`AssetCore Super Admin`/`System Manager` (KHÔNG `Procurement Manager`); `Hoàn tất chấm điểm` cho `Procurement Manager`+`Commissioning Manager`(+admin). `allowed_transitions` là state-level (không role-filter) → nếu sai role bấm vẫn 403 ở guard (defense-in-depth, đúng như Decision).

**INV-CTA-04 (invariant chống drift — test bắt buộc, 07 §III.4.b):** parity INV-CTA-03 nhưng entry `'IMM-03 Vendor Eval Workflow'`. Đọc fixture, dựng `codomain[state] = set(t["action"] for t in transitions where t.state==state)`, seed MỌI state từ `states[]` (terminal → `set()`). Assert: (1) `set(_EVAL_VALID_TRANSITIONS.keys()) == set(states[])` (5 key); (2) với MỖI state `set(_EVAL_VALID_TRANSITIONS[state]) == codomain[state]` (**equality — không thiếu/thừa**). Thêm/sửa transition mà quên map → RED.

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

**Workflow file**: `workflow/imm_03_avl_workflow.json` (5 states · 7 transitions). Cột **Role** ở bảng trên là **persona nghiệp vụ** (IMM Board Approver / IMM Risk Officer = mapping người-dùng); `allowed` trong `fixtures/workflow.json` là **Frappe workflow role** — hai lớp, KHÔNG lẫn:

| Action | Frappe role `allowed` (fixture) |
|---|---|
| Phê duyệt AVL · Phục hồi Approved | `Procurement Manager` + `AssetCore Super Admin` + `System Manager` |
| Cấp Conditional · Hạ xuống Conditional · Đình chỉ | `Spec Manager` + `AssetCore Super Admin` + `System Manager` |

Role-filter §VII.3.a + role-guard mutation dùng lớp Frappe role này (SoT).

> **⚠️ Self-Correction R-04-AVL-01 (2026-07-14 — doc↔code align, SUPERSEDE thiết kế `apply_workflow`).** Hai bản trước lệch với code LIVE: (1) bản 2026-06 set `workflow_state` thô (vi phạm LL-BE-62); (2) bản 2026-07-10 đề xuất "MỌI transition qua `apply_workflow` + `_apply_avl_transition` + tách `restore_avl`". **Code THỰC ĐÃ LAND (`api/imm03.py:437-553`, `services/imm03.py:98-165,516-553`) đi đường THỨ BA — KHÔNG dùng `apply_workflow`:** role guard tường minh `_require_avl_transition_role` (SoT `_AVL_VALID_TRANSITIONS` tuple-form) + `avl.submit()` (Draft 0→1) / `db.set_value` (submitted) + audit `_audit_avl` (`event_type='State Change'`). Cách này thoả LL-BE-62 (KHÔNG set state bỏ qua role — role check chạy TRƯỚC mutation) mà không cần Frappe workflow engine. §VII.3.a dưới đây viết lại theo code THẬT. Xem ADR-IMM-03-07 (02 §IV.13, SUPERSEDE cơ chế của ADR-IMM-03-04 — giữ ADR-04 làm lịch sử).

### VII.3.a Server-driven CTA AVL + role-filter + enforce qua `_require_avl_transition_role` (INV-CTA-05 · INV-AVL-ENDPOINT-MAP, GATE-8 / LL-FE-51 / LL-BE-62)

**SoT map — tuple-form** (`services/imm03.py:123`, cạnh `_DECISION_VALID_TRANSITIONS`/`_EVAL_VALID_TRANSITIONS` nhưng RICHER: mỗi transition mang `(action, next_state, roles)`):

```python
_AVL_APPROVE_ROLES = frozenset({"Procurement Manager", "AssetCore Super Admin", "System Manager"})
_AVL_SPEC_ROLES    = frozenset({"Spec Manager", "AssetCore Super Admin", "System Manager"})

_AVL_VALID_TRANSITIONS: dict[str, list[tuple[str, str, frozenset]]] = {   # state → [(action, next_state, roles)]
    "Draft":       [("Phê duyệt AVL", "Approved", _AVL_APPROVE_ROLES),
                    ("Cấp Conditional", "Conditional", _AVL_SPEC_ROLES)],
    "Approved":    [("Hạ xuống Conditional", "Conditional", _AVL_SPEC_ROLES),
                    ("Đình chỉ", "Suspended", _AVL_SPEC_ROLES)],
    "Conditional": [("Phục hồi Approved", "Approved", _AVL_APPROVE_ROLES),
                    ("Đình chỉ", "Suspended", _AVL_SPEC_ROLES)],
    "Suspended":   [("Phục hồi Approved", "Approved", _AVL_APPROVE_ROLES)],
    "Expired":     [],
}
```

Helpers (SoT-derived): `avl_allowed_transitions(state, user_roles)` (§05 emit) · `avl_transition_target(state, action) → (next_state, roles) | None` · `_require_avl_transition_role(state, action)` (raise BAD_STATE nếu action ∉ SoT; FORBIDDEN nếu `frappe.get_roles() ∩ roles == ∅`; return next_state).

**Emit `allowed_transitions` (role-filtered, N+1-free)** — `list_avl` mỗi row (`api/imm03.py:412`) + `get_avl`:

```python
user_roles = set(frappe.get_roles(frappe.session.user))          # tính 1 lần / request
row["allowed_transitions"] = svc.avl_allowed_transitions(state, user_roles)
# = [action for (action, _next, roles) in _AVL_VALID_TRANSITIONS.get(state, []) if roles & user_roles]
```

Per-row chỉ là Python list-filter (KHÔNG DB) → N+1-free. Role-filter → KHÔNG dead-control per-row (khác Decision/Eval state-level; xem ADR-IMM-03-03).

**3 endpoint CTA phục vụ 5 nhãn action — MỖI mutation qua submit/db.set_value + role guard tường minh (KHÔNG `apply_workflow`, LL-BE-62):**

| Endpoint | Action(s) phục vụ | From → To | Cơ chế mutation | Pre-fields (SERVER set) |
|---|---|---|---|---|
| `approve_avl(name, approval_doc='', **_ignore)` | `Phê duyệt AVL` (Draft) · `Phục hồi Approved` (Conditional/Suspended) | Draft→Approved · Cond/Susp→Approved | Draft: `avl.submit()` · else: `db.set_value` | `approver=frappe.session.user`, `approval_doc` (Draft) |
| `suspend_avl(name, suspension_reason)` | `Đình chỉ` | Approved/Conditional → Suspended | `db.set_value` | `suspension_reason` (non-empty, else VALIDATION) |
| `set_avl_conditional(name, condition_notes)` **⟵ MỚI vòng 33** | `Cấp Conditional` (Draft) · `Hạ xuống Conditional` (Approved) | Draft→Conditional · Approved→Conditional | Draft: `avl.submit()` · else: `db.set_value` | `condition_notes` (non-empty, else VALIDATION) |

Khuôn mỗi handler (`_approve_avl`/`_suspend_avl`/`_set_avl_conditional`):
1. (nếu có reason/notes param) guard non-empty → `ServiceError(VALIDATION)`.
2. `state = frappe.db.get_value(_DT_AVL, name, "workflow_state")`; rỗng → `ServiceError(NOT_FOUND)`.
3. derive `action` theo state (map 1-1 ở bảng trên); state ngoài SoT → `ServiceError(BAD_STATE)`.
4. `_require_avl_transition_role(state, action)` — BAD_STATE (action ∉ SoT) / FORBIDDEN (thiếu role) SẠCH, envelope 200. **KHÔNG set workflow_state trước khi role check qua (LL-BE-62).**
5. mutation: **Draft (docstatus 0)** → `avl.<field>=…; avl.workflow_state=<to>; avl.submit()` (0→1; `on_submit→activate_avl` chỉ sync khi to=="Approved" → bước 6 sync tường minh cho nhánh Conditional). **submitted (docstatus 1)** → `frappe.db.set_value(_DT_AVL, name, {"workflow_state": <to>, <field>: …}, update_modified=False)`.
6. `svc._sync_supplier_avl_status(supplier)` (INV-AVL-LIVE-3 — Conditional VẪN live) + `_audit_avl(name, action, from_state, to_state)` → 1 dòng IMM Audit Trail `event_type='State Change'`, `change_summary=f"AVL — {action}: {_AVL_STATE_VI[from]} → {_AVL_STATE_VI[to]}"` (best-effort).
7. `return {"name": name, "workflow_state": <to>}` (2-key).

`approver = frappe.session.user` (KHÔNG spoof). Kwarg `approver` client cũ nuốt an toàn qua `**_ignore` (backward-compat FE cũ, LL-BE-63).

> **INV-CTA-05 (chống drift — test 07 §III.4.c):** (a) `set(_AVL_VALID_TRANSITIONS.keys()) == fixture states` (5) + per-state `{action}` equality; (b) role nhúng trong tuple `[2]` == `{action: set(allowed)}` gom từ transitions fixture `'IMM-03 AVL Workflow'`. Thêm/sửa transition/role mà quên map → RED.
>
> **INV-AVL-ENDPOINT-MAP (AC4 vòng 33 — đóng "hidden-CTA-câm", 05 §3.6.c / test 07 §III.4.c):** `_AVL_ACTION_ENDPOINT` (dict SoT trong `api/imm03.py`) map MỖI nhãn action codomain `_AVL_VALID_TRANSITIONS` → 1 endpoint @whitelist IMPLEMENTED. Test: `emitted_actions == set(_AVL_ACTION_ENDPOINT.keys())` (không action nào thiếu map) VÀ ∀ endpoint value → tồn tại + whitelisted trong `api/imm03.py`. RED-before: `Cấp Conditional`+`Hạ xuống Conditional` chưa có `set_avl_conditional` → 2 FAIL. GREEN-after: land endpoint → mọi action có endpoint sống.
>
> **DONE-gate spec-contract:** lỗi nghiệp vụ (sai state / thiếu role / thiếu reason/notes) = **in-handler HTTP-200 + Error envelope** (BAD_STATE/FORBIDDEN/VALIDATION) qua `_handle` — KHÔNG raise→HTTP-4xx. Phân biệt **dispatcher-403** (guest/no-token, trước handler) với **in-handler cap-403** (`_require_avl_transition_role` FORBIDDEN → `_handle` map, HTTP-200).

---

## VII.4 RBAC hardening `AC Purchase` — `purchase.*` capability + gate endpoint + `mark_received` allow_on_submit (02 §IV.12, ADR-IMM-03-05/06)

> Bịt RBAC bypass (`ignore_permissions`/`db_set` → mọi user login tự Gửi duyệt/Nhận hàng/Huỷ/Xoá PO) + chuyển CTA sang server-driven `can_*`. Enforcement = `rbac.require` + DocPerm `AC Purchase` (capability-based, chống dead-gate). Files: `services/shared/rbac.py` · `api/purchase.py` · `assetcore/doctype/ac_purchase/ac_purchase.json`.

### VII.4.1 Capability map (`services/shared/rbac.py`)

Thêm domain-primary cho `AC Purchase` → auto-sinh 6 cap `purchase.{read,write,create,delete,submit,cancel}`:

```python
_DOMAIN_PRIMARY: dict[str, str] = {
    ...
    "Asset": "AC Asset",
    "Purchase": "AC Purchase",   # ADR-IMM-03-05 — cap prefix purchase.* độc lập
}
```

- Vòng lặp sinh `CAPABILITY_MAP` (rbac.py) tự tạo `purchase.read/write/create/delete/submit/cancel = ("AC Purchase", ptype)`.
- **Đối xứng `asset.*`**: `_DOMAIN_PRIMARY` và `DOCTYPE_DOMAIN` độc lập — `AC Purchase` ở domain `Procurement` (audit/scope) VÀ có prefix `purchase.*` (CRUD gating). KHÔNG đổi `_DOMAIN_PRIMARY["Procurement"]` (= `IMM Vendor Evaluation`).
- `inventory.create` (= `("AC Stock Movement","create")`) đã tồn tại sẵn (domain `Inventory`) → dùng gate `create_receipt_movement`, KHÔNG thêm cap mới.
- **Cap-set version**: `len(CAPABILITY_MAP)` 98 → **104**; `CAP_SET_VERSION = _compute_cap_set_version()` ĐỔI (hash sorted keys). Không đổi logic `can()`/`require()`/`get_capabilities()`.

### VII.4.2 Schema delta `ac_purchase.json`

`status` và `actual_delivery_date` thêm `"allow_on_submit": 1` để `mark_received` chuyển `Submitted→Received` qua `doc.save()` trên doc `docstatus=1` (không dùng `db_set`). `status` giữ `read_only:1` (UI desk không sửa tay; API set programmatic). Deploy: `bench --site <site> reload-doctype "AC Purchase"` (KHÔNG data-migration).

### VII.4.3 Endpoint gate (`api/purchase.py`)

`import` thêm: `from assetcore.services.shared import rbac`. Mỗi endpoint đổi-trạng-thái đặt `rbac.require(...)` là câu lệnh ĐẦU (trước `_get_doc`/404) — `PermissionError` propagate cho framework → HTTP 403, msg `Không đủ quyền: purchase.X`.

```python
def create_purchase(payload=""):
    rbac.require("purchase.create")
    ...
    doc.insert()                       # GỠ ignore_permissions
    if int(data.get("auto_submit") or 0):
        rbac.require("purchase.submit")
        doc.submit()

def update_purchase(name, payload=""):
    rbac.require("purchase.write"); ...; doc.save()          # GỠ ignore_permissions
def submit_purchase(name):
    rbac.require("purchase.submit"); ...; doc.submit()
def cancel_purchase(name):
    rbac.require("purchase.cancel"); ...; doc.cancel()
def delete_purchase(name):
    rbac.require("purchase.delete"); ...; frappe.delete_doc(_DT_PUR, name)  # GỠ ignore_permissions

def mark_received(name):
    rbac.require("purchase.submit")                          # AC1/AC2 gate TRƯỚC
    doc = _get_doc(name); ...
    if doc.docstatus != 1 or doc.status != "Submitted":
        return _err(_("Chỉ được xác nhận nhận hàng cho phiếu đã duyệt"), 400)
    doc.status = "Received"
    if not doc.actual_delivery_date:
        doc.actual_delivery_date = frappe.utils.today()
    doc.save()                                               # GỠ db_set; Version audit + modified_by
    return _ok({"name": doc.name, "status": doc.status})

def create_receipt_movement(name, to_warehouse, requested_by="", auto_submit=0):
    rbac.require("inventory.create")                         # gate biên; service giữ nguyên
    ...
```

- **BE note (UpdateAfterSubmitError)**: `before_save` recompute `total_value`/child rows là idempotent (qty/unit_cost bất biến khi nhận hàng) → giá trị không đổi → save-after-submit KHÔNG raise. Nếu quan sát lỗi, guard `if self.docstatus == 0:` quanh recompute trong `ACPurchase.before_save`.
- **Không đổi**: endpoint đọc (`get_purchase`/`list_purchases`/`get_purchase_movements`/`get_purchase_commissionings`/`search_purchases`/`get_part_purchases`) — chỉ `get_purchase` bổ sung cờ (VII.4.4). `on_submit`/`on_cancel` controller giữ `db_set` status (chạy trong `submit()`/`cancel()` đã gate). Hook `auto_mark_purchase_received` giữ `frappe.db.set_value` (đường hệ thống downstream, ngoài scope).

### VII.4.4 `get_purchase` enrich cờ `can_*` (SoT gating FE)

```python
def get_purchase(name):
    doc = _get_doc(name)
    if not doc: return _err(_(_MSG_NOT_FOUND), 404)
    d = _enrich_purchase(doc.as_dict())
    ds, st = d.get("docstatus"), d.get("status")
    can_sub = rbac.can("purchase.submit")
    d["can_submit"]         = bool(can_sub and ds == 0)
    d["can_receive"]        = bool(can_sub and ds == 1 and st == "Submitted")
    d["can_cancel"]         = bool(rbac.can("purchase.cancel") and ds == 1 and st not in ("Received", "Cancelled"))
    d["can_create_receipt"] = bool(rbac.can("inventory.create") and ds == 1 and st == "Submitted")
    d["can_edit"]           = bool(rbac.can("purchase.write")  and ds == 0)
    d["can_delete"]         = bool(rbac.can("purchase.delete") and ds == 0)
    return _ok(d)
```

Backward-compatible (thêm khóa; consumer cũ bỏ qua). `can_*` = hint hiển thị, KHÔNG thay enforcement (`rbac.require`+DocPerm).

### VII.4.5 Test re-freeze (BẮT BUỘC — tránh false-green)

`tests/test_mobile_capability_map.py`: `_EXPECTED_CAP_COUNT` 98 → 104; `_EXPECTED_CAP_SET_VERSION` = giá trị `_compute_cap_set_version()` THẬT (chạy `bench --site <site> execute assetcore.services.shared.rbac._compute_cap_set_version` — KHÔNG bịa hash). Đây là cap-set đổi CÓ CHỦ ĐÍCH → re-freeze là đúng, KHÔNG skip/nới assertion.

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
