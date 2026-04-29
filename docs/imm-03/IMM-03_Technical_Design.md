# IMM-03 — Technical Design

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-03 — Vendor Eval & Procurement Decision |
| Phiên bản | 0.1.0 |
| Ngày cập nhật | 2026-04-29 |
| Trạng thái | DRAFT |

---

## 1. Tổng quan

```
Frappe v15 / ERPNext v15 / MariaDB 10.11
   ▼
AssetCore — module AssetCore
   • DocTypes: 6 primary + 7 child
   • Custom fields: AC Supplier, AC Purchase (Wave 1 DocTypes — KHÔNG dùng ERPNext core)
   • Service:  assetcore/services/imm03.py
   • API:      assetcore/api/imm03.py
   • Workflow: 3 file (eval, decision, avl)
   • Scheduler: tasks_imm03.py
```

---

## 2. Schema — Primary

### 2.1 ~~IMM Vendor Profile~~ → Custom fields trên `AC Supplier`

**KHÔNG tạo DocType mới** (xem WAVE2_ALIGNMENT §7). Vendor master gốc là `AC Supplier` (Wave 1). Wave 2 patch bổ sung custom fields:

| Section | Field | Type | Req | Note |
|---|---|---|---|---|
| Identity | vendor_code | (đã có trên AC Supplier — kiểm tra `ac_supplier.json`) | — | — |
|  | (link gốc) | name `AC Supplier` | — | KHÔNG cần field link riêng |
|  | legal_name | Data | Y | — |
|  | vat_code | Data | Y | MST |
|  | country | Data | Y | — |
| Contact | rep_name | Data | Y | — |
|  | rep_phone | Data | Y | — |
|  | rep_email | Email | Y | — |
| Banking | bank_name | Data | N | — |
|  | bank_account | Data | N | — |
| Capability | device_categories | Small Text | Y | comma list, dùng cho AVL filter |
|  | scope_of_supply | Long Text | N | — |
|  | financial_health | Select | N | A/B/C/Unknown |
| Cert | certifications | Table → Vendor Cert | Y | ≥ 1 ISO 9001/13485 |
| AVL | avl_status | Select (auto) | N | Approved/Conditional/Suspended/Expired/Not Applicable |
| Score | overall_score | Float (auto) | N | từ Scorecard mới nhất |
|  | last_audit_date | Date | N | mirror Supplier |
|  | next_audit_date | Date | N | mirror |

### 2.2 IMM Vendor Evaluation

Naming: `VE-.YY.-.#####`. Submittable.

| Field | Type | Note |
|---|---|---|
| spec_ref | Link → IMM Tech Spec | Y |
| plan_line | Data | mirror |
| draft_date | Date | Y |
| weighting_scheme | JSON | 5 group weights |
| criteria | Table → Vendor Eval Criterion | Y |
| candidates | Table → Vendor Eval Candidate | Y |
| quotations | Table → Vendor Quotation Line | C (after RFQ) |
| recommended_candidate | Data | row name top weighted |
| workflow_state | — | Eval workflow |
| lifecycle_events | Table | audit |

### 2.3 IMM Procurement Decision

Naming: `PD-.YY.-.#####`. Submittable.

| Field | Type | Note |
|---|---|---|
| spec_ref | Link → IMM Tech Spec | Y |
| evaluation_ref | Link → IMM Vendor Evaluation | Y |
| plan_ref | Link → IMM Procurement Plan | Y |
| plan_line | Data | mirror |
| procurement_method | Select | Chỉ định / Chào hàng / Đấu thầu rộng rãi / Mua sắm trực tiếp / Mua sắm tập trung |
| method_legal_basis | Long Text | C | Bắt buộc với "Chỉ định thầu" |
| winner_candidate | Data | row name từ evaluation.candidates |
| awarded_vendor | Link → Supplier | Y |
| awarded_price | Currency | Y |
| envelope_check_pct | Percent (auto) | awarded / allocated_budget |
| funding_source | Select | Y |
| funding_evidence | Attach | C |
| board_approver | Link → User | C trước Awarded |
| contract_no | Data | C ở Contract Signed |
| contract_doc | Attach | C |
| ac_purchase_ref | Link → AC Purchase | C ở PO Issued |
| awarded_date | Date | auto |
| workflow_state | — | Decision workflow |
| (audit) | KHÔNG child — `IMM Audit Trail` (root_doctype=IMM Procurement Decision) | — |

### 2.4 IMM AVL Entry

Naming: `AVL-.YYYY.-.#####`. Submittable.

| Field | Type | Note |
|---|---|---|
| vendor_profile | Link → IMM Vendor Profile | Y |
| supplier | Link → Supplier | Y (mirror) |
| device_category | Link → Asset Category | Y |
| validity_years | Int | Y; 1–3 |
| valid_from | Date | Y |
| valid_to | Date (auto) | Y |
| status | Select | Draft/Approved/Conditional/Suspended/Expired |
| approval_doc | Attach | C khi Approved |
| approver | Link → User | C |
| condition_notes | Long Text | C khi Conditional |
| suspension_reason | Long Text | C khi Suspended |

### 2.5 IMM Vendor Scorecard

Naming: `VS-.YYYY.-.QN-{Vendor}`. Not submittable.

| Field | Type | Note |
|---|---|---|
| period_year | Int | — |
| period_quarter | Int | 1–4 |
| vendor_profile | Link → IMM Vendor Profile | Y |
| supplier | Link → Supplier | Y |
| kpi_rows | Table → Scorecard KPI Row | 5 dimension |
| overall_score | Float (auto) | — |
| commentary | Long Text | — |
| generated_at | Datetime | — |

### 2.6 IMM Supplier Audit

Naming: `SA-.YY.-.#####`. Submittable.

| Field | Type | Note |
|---|---|---|
| vendor_profile | Link → IMM Vendor Profile | Y |
| audit_date | Date | Y |
| audit_type | Select | Initial/Periodic/For-Cause |
| auditors | Small Text | Y |
| findings | Table → Audit Finding | — |
| overall_result | Select | Pass/Conditional/Fail |
| capa_required | Check | — |
| follow_up_date | Date | C khi Conditional/Fail |

---

## 3. Child Tables

### 3.1 Vendor Eval Criterion

| Field | Type |
|---|---|
| group | Select (Technical/Commercial/Financial/Support/Compliance) |
| criterion | Data |
| weight_pct | Percent |
| description | Small Text |
| scorer_role | Select (HTM/KH-TC/TCKT/QA Risk) |

### 3.2 Vendor Eval Candidate

| Field | Type |
|---|---|
| vendor_profile | Link → IMM Vendor Profile |
| supplier | Link → Supplier (mirror) |
| in_avl | Check (auto) |
| sign_off_non_avl | Link → User (C nếu non-AVL) |
| scores | JSON | per-criterion scores |
| weighted_score | Float (auto) |
| notes | Small Text |

### 3.3 Vendor Quotation Line

| Field | Type |
|---|---|
| candidate_row | Data | row name |
| quotation_no | Data | — |
| quotation_date | Date | — |
| quotation_validity | Date | — |
| price | Currency | — |
| currency | Link → Currency | — |
| payment_terms | Data | — |
| delivery_days | Int | — |
| warranty_months | Int | — |
| attachment | Attach | — |

### 3.4 Vendor Cert

| Field | Type |
|---|---|
| cert_type | Select (ISO 9001/ISO 13485/ĐKLH BYT/GSP/GDP/CE/FDA/Other) |
| cert_number | Data |
| issued_by | Data |
| issued_date | Date |
| expiry_date | Date |
| attachment | Attach |
| status | Select (auto: Active/Expiring/Expired) |

### 3.5 ~~Decision Lifecycle Event~~ — reuse `IMM Audit Trail`

KHÔNG tạo child table. Audit ghi vào `IMM Audit Trail` (root_doctype=IMM Procurement Decision). VR-03-06 enforce tại tầng IMM Audit Trail.

### 3.6 Audit Finding

| Field | Type |
|---|---|
| severity | Select (Minor/Major/Critical) |
| category | Select (Quality/Compliance/Delivery/Documentation/Other) |
| description | Long Text |
| capa_action | Long Text |
| capa_owner | Link → User |
| capa_due | Date |
| capa_status | Select (Open/In Progress/Closed) |

### 3.7 Scorecard KPI Row

| Field | Type |
|---|---|
| dimension | Select (Delivery/Quality/Aftersales/Spare/Compliance) |
| weight_pct | Percent |
| raw_value | Float |
| normalized_score | Float (1–5) |
| weighted | Float |
| source_module | Data |

---

## 4. Custom fields trên DocType core AssetCore Wave 1

### 4.1 AC Supplier (Wave 1 — đã LIVE)

Patch Wave 2 thêm:
```
imm_avl_status            Select (Approved/Conditional/Suspended/Expired/Not Applicable)
imm_avl_categories        Small Text
imm_last_audit_date       Date
imm_next_audit_date       Date
imm_overall_score         Float
certifications            Table → Vendor Cert
```

Các field hồ sơ pháp lý / banking (`legal_name`, `vat_code`, `country`, `rep_*`, `bank_*`, `device_categories`, `scope_of_supply`, `financial_health`) — kiểm tra `ac_supplier.json` trước; chỉ thêm những field còn thiếu để tránh duplicate.

### 4.2 AC Purchase (Wave 1 — đã LIVE)

Patch Wave 2 thêm:
```
imm_procurement_decision  Link → IMM Procurement Decision (read-only)
imm_tech_spec             Link → IMM Tech Spec (read-only)
imm_funding_source        Select (NSNN/Tài trợ/Xã hội hóa/BHYT/Khác)
```

`AC Purchase` Hook validate: nếu item nhóm thiết bị y tế (`AC Asset Category` thuộc scope HTM) mà thiếu `imm_procurement_decision` → throw "VR-03-08: AC Purchase TBYT phải đi qua IMM-03 Procurement Decision".

---

## 5. Validation Rules & Gates

| ID | Rule |
|---|---|
| VR-03-01 | Min candidates phù hợp method (≥3 Đấu thầu rộng rãi/CHCT; =1 Chỉ định) |
| VR-03-02 | Vendor non-AVL cần sign_off_non_avl (warn at add, throw at submit) |
| VR-03-03 | Quotation chưa hết hạn |
| VR-03-04 | Awarded ≤ 105% allocated_budget (warn) hoặc justification |
| VR-03-05 | Awarded vendor có AVL Active hoặc Conditional + sign-off |
| VR-03-06 | Lifecycle event bất biến |
| VR-03-07 | 1 Tech Spec ↔ 1 Decision Awarded |

| Gate | Yêu cầu | Block |
|---|---|---|
| G01 | Eval đủ candidate + criteria full + scoring complete | Eval → Evaluated |
| G02 | ≥ 1 quotation hợp lệ | RFQ → Quotation Received |
| G03 | AVL pass / sign-off | Award Recommended |
| G04 | procurement_method hợp pháp với giá trị + loại hàng | Method Selected |
| G05 | contract_doc + funding_source + board_approver | Pending Approval → Awarded |

---

## 6. Algorithms

### 6.1 Compute weighted_score per candidate

```python
def compute_eval_score(eval_doc):
    weights = eval_doc.weighting_scheme  # group weights
    for cand in eval_doc.candidates:
        cand_total = 0.0
        for crit in eval_doc.criteria:
            score = cand.scores.get(crit.criterion, 0)
            grp_w = weights.get(crit.group, 0) / 100
            crit_w = crit.weight_pct / 100
            cand_total += score * grp_w * crit_w
        cand.weighted_score = round(cand_total, 4)
    eval_doc.candidates.sort(key=lambda c: c.weighted_score, reverse=True)
    eval_doc.recommended_candidate = eval_doc.candidates[0].name if eval_doc.candidates else None
```

### 6.2 Procurement method legality (G04)

```python
RULES = [
  # (method, max_value, conditions)
  ("Chỉ định thầu", 50_000_000, ["sole_source"]),
  ("Mua sắm trực tiếp", 100_000_000, []),
  ("Chào hàng cạnh tranh", 1_000_000_000, ["min_3_quote"]),
  ("Đấu thầu rộng rãi", None, ["min_3_quote", "public_tender"]),
  ("Mua sắm tập trung", None, ["central_procurement"]),
]
```

Tham số `max_value` được expose qua master `IMM Procurement Method Config` để cập nhật theo NĐ.

### 6.3 Award decision → mint PO

```python
def award_decision(doc):
    if doc.po_ref:
        return
    po = frappe.new_doc("AC Purchase")            # Wave 1 DocType
    po.supplier = doc.awarded_vendor               # Link → AC Supplier
    po.naming_series = "AC-PUR-.YYYY.-.#####"
    po.imm_procurement_decision = doc.name
    po.imm_tech_spec = doc.spec_ref
    po.imm_funding_source = doc.funding_source
    po.append("devices", {                          # AC Purchase Device Item child
        "device_model": doc.device_model_ref,
        "qty": doc.quantity,
        "unit_price": doc.awarded_price / doc.quantity,
    })
    po.insert()
    doc.ac_purchase_ref = po.name
    write_audit_trail(doc, "PO Created", doc.workflow_state, "Awarded",
                      f"AC Purchase {po.name}")    # ghi vào IMM Audit Trail
    update_plan_line_status(doc.plan_ref, doc.plan_line, "Awarded")
    frappe.publish_realtime("imm03_decision_awarded",
                            {"name": doc.name, "ac_purchase": po.name})
```

### 6.4 Vendor Scorecard quarterly

```
Pipeline:
  for vendor in active_vendors():
    delivery   = compute_delivery_kpi(vendor, period)   # IMM-04
    quality    = compute_quality_kpi(vendor, period)    # IMM-04 + IMM-10
    aftersales = compute_repair_kpi(vendor, period)     # IMM-09
    spare      = compute_spare_kpi(vendor, period)      # IMM-15
    compliance = compute_compliance_kpi(vendor, period) # IMM-10
    overall    = weighted_sum(...)
    upsert Vendor Scorecard (idempotent on (year, quarter, vendor))
    Supplier.imm_overall_score = overall
```

---

## 7. Hooks

```python
doc_events = {
  "IMM Vendor Evaluation": {
    "validate":  "assetcore.services.imm03.validate_evaluation",
    "on_submit": "assetcore.services.imm03.on_submit_evaluation",
  },
  "IMM Procurement Decision": {
    "validate":     "assetcore.services.imm03.validate_decision",
    "before_submit":"assetcore.services.imm03.before_submit_decision",
    "on_submit":    "assetcore.services.imm03.award_decision",
    "on_cancel":    "assetcore.services.imm03.on_cancel_decision",
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
  "daily":     ["assetcore.tasks_imm03.check_avl_expiry",
                "assetcore.tasks_imm03.check_audit_due",
                "assetcore.tasks_imm03.check_decision_overdue"],
  # Frappe v15 không có key "quarterly" → dùng cron expression
  "cron": {
      "0 2 1 1,4,7,10 *": ["assetcore.tasks_imm03.update_vendor_scorecard"],  # 02:00 ngày 1 mỗi quý
  },
}
```

---

## 8. Permissions

Permlevel 1 cho `awarded_price`, `funding_source`, `funding_evidence`, `contract_doc`, `board_approver` (chỉ KH-TC + TCKT + PTP Khối 1 + VP Block1 + CMMS Admin).

---

## 9. Migration

| Patch | Mục đích |
|---|---|
| `v0_1_0.create_imm03_doctypes` | Bootstrap 6 DocType |
| `v0_1_0.add_supplier_imm_fields` | Custom fields Supplier |
| `v0_1_0.add_po_imm_fields` | Custom fields PO |
| `v0_1_0.install_imm03_workflows` | 3 Workflow JSON |
| `v0_1_0.seed_eval_criteria_default` | Default criteria 5 nhóm |
| `v0_1_0.seed_procurement_method_config` | Master ngưỡng theo NĐ |

---

## 10. Test strategy

- Unit: 7 VR + 5 Gate + scoring + scorecard pipeline + PO mint.
- Integration: full Eval Draft → Decision Awarded → PO created.
- AVL lifecycle: Approve → Conditional → Suspended → Expired auto.
- Scheduler: scorecard idempotent re-run.
- Compliance: PO TBYT direct create không có Decision → throw.

*End of Technical Design v0.1.0 — IMM-03*
