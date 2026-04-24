# Sync State — Step 1 Complete
# (Feed file for Step 2: ERPNext Mapping Strategy)

| Phiên bản | 1.0.0 |
|---|---|
| Ngày | 2026-04-22 |
| Nguồn | IMM-01_02_03_BA_Business_Analysis.md |
| Dùng cho | Step 2 — IMM-01_02_03_ERPNext_Mapping_Strategy.md |

---

## 1. CORE ENTITIES ĐÃ ĐỊNH NGHĨA

```
MODULE: imm_planning  (Frappe module name)

IMM-01:
  - DocType: Needs Assessment
    naming: NA-.YY.-.MM.-.#####
    submittable: true
    status_field: status (Select)
    states: [Draft, Submitted, Under Review, Approved, Rejected, Planned]

IMM-02:
  - DocType: Procurement Plan
    naming: PP-.YY.-.#####
    submittable: true
    states: [Draft, Under Review, Approved, Budget Locked]

  - DocType: Procurement Plan Item  (child table of Procurement Plan)
    item_status: [Pending, PO Raised, Ordered, Delivered, Cancelled]

IMM-03:
  - DocType: Technical Specification
    naming: TS-.YY.-.#####
    submittable: true
    states: [Draft, Under Review, Approved]

  - DocType: Vendor Evaluation
    naming: VE-.YY.-.#####
    submittable: true
    states: [Draft, In Progress, Approved, Cancelled]

  - DocType: Vendor Evaluation Item  (child table of Vendor Evaluation)
    tiêu chí chấm: Technical, Financial, VendorProfile, Risk

  - DocType: Purchase Order Request
    naming: POR-.YY.-.#####
    submittable: true
    states: [Draft, Under Review, Approved, Released, Fulfilled, Cancelled]
```

---

## 2. BUSINESS RULES QUAN TRỌNG (cho ERPNext Mapping)

```
BR-NA-01: Mỗi Needs Assessment phải có requesting_dept, equipment_type, quantity,
          estimated_budget, clinical_justification, priority
BR-NA-02: Chỉ Department Head submit NA — permission level role check
BR-NA-03: NA.approved_budget có thể ≠ NA.estimated_budget (Finance adjusts)
BR-NA-04: NA.status → Planned khi được link vào PP Item (auto via controller)

BR-PP-01: Mỗi năm chỉ 1 PP ở Approved hoặc Budget Locked — unique constraint per plan_year
BR-PP-02: remaining_budget = approved_budget - SUM(items.total_cost) — calculated field
BR-PP-03: Budget Locked → items child table read-only — JS client script
BR-PP-04: PP Item link 1:1 về Needs Assessment đã Approved

BR-TS-01: TS phải link về Procurement Plan Item — FK mandatory
BR-TS-02: regulatory_class (I/II/III) bắt buộc — NĐ98 compliance

BR-VE-01: Tối thiểu 2 vendors trong VE — len(items) ≥ 2 in validate()
BR-VE-02: Score formula per vendor: Tech×0.4 + Fin×0.3 + Profile×0.2 + Risk×0.1

BR-POR-01: POR.total_amount ≤ PP_item.total_cost × 1.10 (10% variance)
BR-POR-02: POR > 500M VND → require Director role approval
BR-POR-03: on POR Released → PP Item status = Ordered (auto)
BR-POR-04: on POR Released → trigger IMM-04 readiness notification
```

---

## 3. INPUT / OUTPUT PARAMETERS (cho Frontend & API)

```
IMM-01 — Needs Assessment:
  CREATE input:
    requesting_dept: Link → Department (required)
    request_date: Date (auto = today)
    requested_by: Link → User (auto = frappe.session.user)
    equipment_type: Data (required)
    linked_device_model: Link → IMM Device Model (optional)
    quantity: Int (required, 1–100)
    clinical_justification: Text Editor (required, ≥50 chars on submit)
    estimated_budget: Currency (required, >0, ≤50B)
    priority: Select [Critical, High, Medium, Low] (required)
    current_equipment_age: Int (optional)
    failure_frequency: Select [Never,Rarely,Monthly,Weekly,Daily] (optional)

  REVIEW fields (HTM Manager fills):
    htmreview_notes: Text

  APPROVE fields (Finance Director fills):
    approved_budget: Currency
    finance_notes: Text

  REJECT fields:
    reject_reason: Text (required on reject)

  OUTPUT:
    name: "NA-YY-MM-#####"
    status: one of states
    workflow_state: synced with status

IMM-02 — Procurement Plan:
  CREATE input:
    plan_year: Int (required)
    approved_budget: Currency (required)
  
  ITEM input (child):
    needs_assessment: Link → Needs Assessment (required, status must be Approved)
    device_model: Link → IMM Device Model (optional)
    equipment_description: Data
    quantity: Int
    estimated_unit_cost: Currency
    total_cost: Currency (calculated = qty × unit_cost)
    priority: Select [Critical, High, Medium, Low]
    planned_quarter: Select [Q1, Q2, Q3, Q4]
    vendor_shortlist: Text

  OUTPUT:
    name: "PP-YY-#####"
    remaining_budget: Currency (calculated)
    status: one of states

IMM-03 — Technical Specification:
  CREATE input:
    linked_plan_item: Link → Procurement Plan Item (required)
    device_model: Link → IMM Device Model (optional)
    performance_requirements: Text Editor (required)
    safety_standards: Text (required)
    regulatory_class: Select [Class I, Class II, Class III] (required)
    accessories_included: Text
    warranty_terms: Data
    reference_documents: Attach Multiple

IMM-03 — Vendor Evaluation:
  CREATE input:
    linked_technical_spec: Link → Technical Specification (required)
    evaluation_date: Date
    items: Child Table → Vendor Evaluation Item
      - vendor: Link → Supplier (required)
      - technical_score: Float (0–10)
      - financial_score: Float (0–10)
      - profile_score: Float (0–10)
      - risk_score: Float (0–10)
      - total_score: Float (calculated, weighted)
      - notes: Text
    recommended_vendor: Link → Supplier (required on approve)
    selection_justification: Text (required if not highest score)

IMM-03 — Purchase Order Request:
  CREATE input:
    linked_plan_item: Link → Procurement Plan Item (required)
    linked_evaluation: Link → Vendor Evaluation (required)
    linked_technical_spec: Link → Technical Specification (required)
    vendor: Link → Supplier (required)
    quantity: Int
    unit_price: Currency
    total_amount: Currency (calculated = qty × unit_price)
    delivery_terms: Data
    payment_terms: Data
    expected_delivery_date: Date

  OUTPUT:
    name: "POR-YY-#####"
    status: one of states
    approved_by: Link → User
```

---

## 4. LIÊN KẾT ERPNext CORE CẦN DÙNG

```
- ERPNext DocType: Department → used by NA.requesting_dept
- ERPNext DocType: Supplier → used by VE.vendor, POR.vendor
- ERPNext DocType: User → used by NA.requested_by, POR.approved_by
- IMM Wave 1 DocType: IMM Device Model → used by NA, PP Item, TS
- IMM Wave 1 DocType: IMM Audit Trail → all status transitions write here
- Custom Field trên Asset: imm_lifecycle_status (already defined Wave 1)
```

---

## 5. FRAPPE MODULE & FILE STRUCTURE (cho Step 2)

```
assetcore/imm_planning/
├── __init__.py
├── doctype/
│   ├── needs_assessment/
│   │   ├── needs_assessment.json
│   │   ├── needs_assessment.py         ← validate(), before_submit(), on_submit()
│   │   ├── needs_assessment.js
│   │   └── test_needs_assessment.py
│   ├── procurement_plan/
│   │   ├── procurement_plan.json
│   │   ├── procurement_plan.py
│   │   ├── procurement_plan.js
│   │   └── test_procurement_plan.py
│   ├── procurement_plan_item/
│   │   └── procurement_plan_item.json  ← child table, no controller
│   ├── technical_specification/
│   │   ├── technical_specification.json
│   │   ├── technical_specification.py
│   │   └── test_technical_specification.py
│   ├── vendor_evaluation/
│   │   ├── vendor_evaluation.json
│   │   ├── vendor_evaluation.py
│   │   └── test_vendor_evaluation.py
│   ├── vendor_evaluation_item/
│   │   └── vendor_evaluation_item.json ← child table
│   └── purchase_order_request/
│       ├── purchase_order_request.json
│       ├── purchase_order_request.py
│       └── test_purchase_order_request.py
└── api/
    ├── imm01.py    ← 6 endpoints: create, submit_for_review, begin_review,
    │                              approve, reject, link_to_plan
    ├── imm02.py    ← 5 endpoints: create, add_item, submit, approve, lock_budget
    └── imm03.py    ← 7 endpoints: create_ts, approve_ts, create_ve, approve_ve,
                                   create_por, approve_por, release_por
```

---

## 6. WORKFLOWS CẦN TẠO (cho Step 2)

```
1. Needs Assessment Workflow
   DocType: Needs Assessment
   States: Draft → Submitted → Under Review → Approved | Rejected → Planned
   Roles: Clinical User → Department Head → Operations Manager → Finance Director

2. Procurement Plan Workflow
   DocType: Procurement Plan
   States: Draft → Under Review → Approved → Budget Locked
   Roles: Operations Manager → Department Head → Finance Director

3. Technical Specification Workflow
   DocType: Technical Specification
   States: Draft → Under Review → Approved
   Roles: Operations Manager → Technical Reviewer

4. Vendor Evaluation Workflow
   DocType: Vendor Evaluation
   States: Draft → In Progress → Approved → Cancelled
   Roles: Operations Manager → Technical Reviewer + Finance Officer

5. Purchase Order Request Workflow
   DocType: Purchase Order Request
   States: Draft → Under Review → Approved → Released → Fulfilled | Cancelled
   Roles: Document Officer → Operations Manager → Department Head (if >500M)
```

---

## 7. UNRESOLVED DEPENDENCIES (chuyển tiếp cho Step 2)

```
- [ ] Xác nhận IMM Device Model đã có đủ fields từ Wave 1 để lookup
- [ ] Xác nhận IMM Audit Trail schema từ Wave 1 đủ để ghi event mới
- [ ] Cần kiểm tra Role map: "IMM Technical Reviewer" và "IMM Finance Officer"
      có trong roles.json Wave 1 chưa hay phải thêm mới
- [ ] Cần xác định vendor scoring algorithm: float 0-10 per criterion
      hay select band (A/B/C/D)
- [ ] Confirm regulatory_class mapping: Class I/II/III theo NĐ98 hay theo MDD
- [ ] IMM-04 trigger mechanism: webhook hay Frappe Server Script?
```
