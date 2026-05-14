# 03 — Sơ đồ kỹ thuật — IMM-03 Đánh giá Nhà cung cấp & Quyết định Mua sắm

> ✅ Module LIVE — Wave 2. Backend và Frontend đã triển khai.

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-03 — Vendor Evaluation & Procurement Decision |
| Phiên bản | 0.1.0 |
| Ngày | 2026-05-14 |
| Trạng thái | LIVE — Wave 2 |

---

## I. Entity-Relationship Diagram

```mermaid
erDiagram
    AC_SUPPLIER ||--o{ VENDOR_CERT : "certifications"
    AC_SUPPLIER ||--o{ IMM_AVL_ENTRY : "có AVL"
    AC_SUPPLIER ||--o{ IMM_VENDOR_SCORECARD : "được đánh giá"
    AC_SUPPLIER ||--o{ IMM_SUPPLIER_AUDIT : "được audit"

    IMM_VENDOR_EVALUATION ||--o{ VENDOR_EVAL_CRITERION : "criteria"
    IMM_VENDOR_EVALUATION ||--o{ VENDOR_EVAL_CANDIDATE : "candidates"
    IMM_VENDOR_EVALUATION ||--o{ VENDOR_QUOTATION_LINE : "quotations"
    IMM_VENDOR_EVALUATION }o--|| IMM_TECH_SPEC : "spec_ref"

    IMM_PROCUREMENT_DECISION }o--|| IMM_VENDOR_EVALUATION : "evaluation_ref"
    IMM_PROCUREMENT_DECISION }o--|| IMM_TECH_SPEC : "spec_ref"
    IMM_PROCUREMENT_DECISION }o--|| IMM_PROCUREMENT_PLAN : "plan_ref"
    IMM_PROCUREMENT_DECISION ||--o| AC_PURCHASE : "ac_purchase_ref"
    IMM_PROCUREMENT_DECISION ||--o{ IMM_AUDIT_TRAIL : "lifecycle events"

    IMM_VENDOR_SCORECARD ||--o{ SCORECARD_KPI_ROW : "kpi_rows"
    IMM_VENDOR_SCORECARD }o--|| AC_SUPPLIER : "supplier"

    IMM_SUPPLIER_AUDIT ||--o{ AUDIT_FINDING : "findings"
    IMM_SUPPLIER_AUDIT }o--|| AC_SUPPLIER : "supplier"

    VENDOR_EVAL_CANDIDATE }o--|| AC_SUPPLIER : "supplier"
    IMM_AVL_ENTRY }o--|| AC_SUPPLIER : "supplier"

    AC_PURCHASE }o--|| IMM_PROCUREMENT_DECISION : "imm_procurement_decision"
    AC_PURCHASE }o--|| IMM_TECH_SPEC : "imm_tech_spec"

    AC_SUPPLIER {
        string name PK
        string supplier_name
        string supplier_code
        string supplier_group
        string country
        string tax_id
        string imm_avl_status "custom field (patch v3_1.003)"
        string imm_avl_categories "custom field"
        date imm_last_audit_date "custom field"
        date imm_next_audit_date "custom field"
        float imm_overall_score "custom field"
        table imm_certifications "custom field → Vendor Cert"
    }

    IMM_VENDOR_EVALUATION {
        string name PK
        string spec_ref FK
        date draft_date
        string workflow_state
        string recommended_candidate
        string plan_line
        json weighting_scheme
        int docstatus
        string amended_from
    }

    IMM_PROCUREMENT_DECISION {
        string name PK
        string spec_ref FK
        string evaluation_ref FK
        string workflow_state
        string plan_ref FK
        string plan_line
        string procurement_method
        text method_legal_basis
        string winner_supplier FK
        currency awarded_price
        float envelope_check_pct
        int quantity
        string funding_source
        string funding_evidence
        string board_approver
        date awarded_date
        string contract_no
        string contract_doc
        string ac_purchase_ref FK
        int docstatus
        string amended_from
    }

    IMM_AVL_ENTRY {
        string name PK
        string supplier FK
        string device_category
        string workflow_state
        int validity_years
        date valid_from
        date valid_to
        string approver
        string approval_doc
        text condition_notes
        text suspension_reason
        int docstatus
        string amended_from
    }

    IMM_VENDOR_SCORECARD {
        string name PK
        int period_year
        int period_quarter
        string supplier FK
        float overall_score
        string commentary
        datetime generated_at
    }

    IMM_SUPPLIER_AUDIT {
        string name PK
        string supplier FK
        date audit_date
        string audit_type
        string overall_result
        boolean capa_required
        date follow_up_date
        int docstatus
    }

    VENDOR_EVAL_CRITERION {
        string name PK
        string parent FK
        string group
        string criterion
        float weight_pct
        string scorer_role
    }

    VENDOR_EVAL_CANDIDATE {
        string name PK
        string parent FK
        string supplier FK
        boolean in_avl
        string sign_off_non_avl
        json scores
        float weighted_score
    }

    VENDOR_QUOTATION_LINE {
        string name PK
        string parent FK
        string candidate_supplier
        string quotation_no
        date quotation_date
        date quotation_validity
        currency price
        string currency
        string payment_terms
        int delivery_days
        int warranty_months
        string attachment
    }

    VENDOR_CERT {
        string name PK
        string parent FK
        string cert_type
        string cert_number
        string issued_by
        date issued_date
        date expiry_date
        string status
    }

    SCORECARD_KPI_ROW {
        string name PK
        string parent FK
        string dimension
        float weight_pct
        float raw_value
        float normalized_score
        float weighted
        string source_module
    }

    AUDIT_FINDING {
        string name PK
        string parent FK
        string severity
        string category
        string description
        string capa_status
        date capa_due
    }

    IMM_AUDIT_TRAIL {
        string name PK
        string root_doctype
        string root_name
        string action
        string from_state
        string to_state
        string actor
        datetime timestamp
        string remarks
    }
```

---

## II. Class Diagram

```mermaid
classDiagram
    class ImmVendorEvaluationController {
        +validate()
        +on_submit()
        +on_cancel()
        -_run_gate_checks()
    }

    class ImmProcurementDecisionController {
        +validate()
        +before_submit()
        +on_submit()
        +on_cancel()
        -_run_gate_checks()
    }

    class ImmAvlEntryController {
        +validate()
        +on_submit()
    }

    class ImmSupplierAuditController {
        +on_submit()
    }

    class Imm03Service {
        +validate_evaluation(doc: Document) None
        +on_submit_evaluation(doc: Document) None
        +validate_decision(doc: Document) None
        +before_submit_decision(doc: Document) None
        +on_submit_decision(doc: Document) None
        +on_cancel_decision(doc: Document) None
        +validate_avl(doc: Document) None
        +activate_avl(doc: Document) None
        +on_submit_audit(doc: Document) None
        +validate_ac_purchase_imm_link(doc, method) None
        +check_avl_expiry() None
        +check_audit_due() None
        +check_decision_overdue() None
        +update_vendor_scorecard() None
        -_vr01_min_candidates(doc: Document) None
        -_vr03_quotation_validity(doc: Document) None
        -_check_avl_warnings(doc: Document) None
        -_is_supplier_in_avl(supplier, category) int
        -_compute_eval_scores(doc: Document) None
        -_validate_gate_g04_method(doc: Document) None
        -_vr04_envelope_check(doc: Document) None
        -_vr05_winner_avl_required(doc: Document) None
        -_vr07_unique_decision_per_spec(doc: Document) None
        -_validate_gate_g05(doc: Document) None
        -_mint_ac_purchase(doc: Document) str
        -_sync_supplier_avl_status(supplier: str) None
    }

    note for Imm03Service "Scheduler jobs ở cùng module — KHÔNG có module Imm03Tasks riêng. G01/G02/G03 (eval-side gates) chưa được implement: workflow JSON cho phép transition; gate enforcement nằm ở Decision tier (G04/G05)."

    class Imm03Api {
        +list_vendor_profiles(filters, page, page_size) dict
        +get_vendor_profile(name) dict
        +create_vendor_profile(payload) dict
        +add_vendor_cert(supplier, cert_type, ...) dict
        +list_avl(filters) dict
        +get_avl(name) dict
        +create_avl_entry(supplier, device_category, validity_years, valid_from) dict
        +approve_avl(name, approver, approval_doc) dict
        +suspend_avl(name, suspension_reason) dict
        +list_evaluations(filters, page, page_size) dict
        +get_evaluation(name) dict
        +create_evaluation(spec_ref, weighting_scheme) dict
        +add_candidate(name, supplier, sign_off_non_avl) dict
        +submit_quotations(name, quotations) dict
        +score_evaluation(name, scorer_role, scores_by_supplier) dict
        +transition_eval_workflow(name, action) dict
        +list_decisions(filters, page, page_size) dict
        +get_decision(name) dict
        +create_decision(evaluation_ref, procurement_method, method_legal_basis) dict
        +award_decision(name, winner_supplier, awarded_price, funding_source, board_approver, contract_doc, remarks) dict
        +record_contract(name, contract_no, contract_doc, signed_date) dict
        +transition_decision_workflow(name, action) dict
        +get_vendor_scorecard(supplier, year, quarter) dict
        +dashboard_kpis() dict
    }

    class ServiceError {
        +code: ErrorCode
        +message: str
        +raise(code: ErrorCode, msg: str)
    }

    class ErrorCode {
        <<enumeration>>
        VALIDATION
        INVALID_PARAMS
        BUSINESS_RULE
        BAD_STATE
        CONFLICT
        DUPLICATE
        NOT_FOUND
        FORBIDDEN
        INTERNAL
    }

    ImmVendorEvaluationController --> Imm03Service : calls
    ImmProcurementDecisionController --> Imm03Service : calls
    ImmAvlEntryController --> Imm03Service : calls
    ImmSupplierAuditController --> Imm03Service : calls
    Imm03Api --> Imm03Service : delegates
    Imm03Service --> ServiceError : raises
    ServiceError --> ErrorCode : uses
```

---

## III. Sequence Diagrams

### III.1 Luồng Award Decision → Mint AC Purchase

```mermaid
sequenceDiagram
    actor VP as VP Block1
    participant UI as Frontend
    participant API as imm03.py API
    participant SVC as Imm03Service
    participant CTRL as Decision Controller
    participant DB as MariaDB
    participant RT as Frappe Realtime

    VP->>UI: Click "Awarded" trên PD-26-00045
    UI->>API: POST award_decision {name, winner_supplier, awarded_price, funding_source, board_approver, contract_doc, remarks}
    API->>SVC: validate_decision(doc) [hook validate]
    SVC->>SVC: _validate_gate_g04_method(doc)
    SVC->>SVC: _vr04_envelope_check(doc)
    SVC->>SVC: _vr07_unique_decision_per_spec(doc)
    API->>SVC: before_submit_decision(doc)
    SVC->>SVC: _vr05_winner_avl_required(doc)
    SVC->>SVC: _validate_gate_g05(doc)
    alt Gate G05 fail
        SVC-->>API: raise ServiceError(BUSINESS_RULE, "G05: Thiếu funding_source/board_approver/contract_doc")
        API-->>UI: {success: false, error: "G05...", code: "BUSINESS_RULE"}
    end
    CTRL->>DB: doc.submit() → docstatus=1, workflow_state="Awarded"
    API->>SVC: on_submit_decision(doc)
    SVC->>SVC: _mint_ac_purchase(doc)
    SVC->>DB: frappe.new_doc("AC Purchase") → insert (devices child)
    DB-->>SVC: po.name = "AC-PUR-2026-00112"
    SVC->>DB: doc.db_set("ac_purchase_ref", po.name)
    SVC->>DB: _update_plan_line_status(plan_ref, plan_line, "Awarded")
    SVC->>RT: frappe.publish_realtime("imm03_decision_awarded", {name, ac_purchase, winner_supplier, spec_ref, plan_line})
    Note over API,SVC: Audit trail ghi qua log_audit_event() trong endpoint award_decision (event_type=imm03_decision_awarded)
    RT-->>UI: event imm03_decision_awarded
    API-->>UI: {success: true, data: {ac_purchase_ref: "AC-PUR-2026-00112", envelope_check_pct: 80.0}}
    UI->>VP: Toast "Awarded — PO AC-PUR-2026-00112 đã tạo"
```

### III.2 Luồng AVL Approval

```mermaid
sequenceDiagram
    actor PROCUREMENT as ĐT-HĐ-NCC Officer
    actor VP as VP Block1
    participant API as imm03.py API
    participant SVC as Imm03Service
    participant DB as MariaDB
    participant SCHED as Scheduler (Daily)

    PROCUREMENT->>API: POST create_avl_entry {supplier, device_category, validity_years, valid_from}
    API->>SVC: validate_avl(doc) [auto-compute valid_to]
    SVC->>DB: insert AVL Entry (workflow_state=Draft, docstatus=0)
    API-->>PROCUREMENT: {success: true, data: {name: "AVL-2026-00045", valid_to: "2028-04-30"}}

    VP->>API: POST approve_avl {name, approver, approval_doc}
    API->>SVC: _approve_avl: doc.workflow_state="Approved"; doc.submit()
    SVC->>SVC: activate_avl(doc) [on_submit hook]
    SVC->>SVC: _sync_supplier_avl_status(supplier)
    SVC->>DB: db.set_value AC Supplier.imm_avl_status, imm_avl_categories
    DB-->>SVC: saved (docstatus=1)
    API-->>VP: {success: true, data: {name: "AVL-2026-00045", workflow_state: "Approved"}}

    Note over SCHED,DB: Scheduler daily check_avl_expiry()
    SCHED->>DB: SELECT name,supplier FROM tabIMM AVL Entry WHERE docstatus=1 AND workflow_state IN ('Approved','Conditional') AND valid_to < CURDATE()
    DB-->>SCHED: [AVL-2026-00045]
    SCHED->>DB: db.set_value workflow_state="Expired" (bypass re-submit)
    SCHED->>SVC: _sync_supplier_avl_status(supplier)
    Note over SCHED: V1: chỉ update state; chưa wire frappe.sendmail cho cảnh báo 60/30d (TODO)
```

### III.3 Luồng Vendor Evaluation — Scoring

```mermaid
sequenceDiagram
    actor HTM as HTM Engineer
    actor KHTC as KH-TC Officer
    actor QA as QA Risk Team
    participant API as imm03.py API
    participant SVC as Imm03Service
    participant DB as MariaDB

    Note over HTM,DB: Evaluation VE-26-00120 ở state Quotation Received

    HTM->>API: POST score_evaluation {name, scorer_role: "HTM", scores_by_supplier: {supplier_name: {criterion: score}}}
    API->>SVC: _score_evaluation: merge scores vào candidate.scores (JSON)
    SVC->>DB: ve.save() → trigger validate_evaluation → _compute_eval_scores
    DB-->>API: partial weighted_scores + recommended_candidate

    KHTC->>API: POST score_evaluation {name, scorer_role: "KH-TC", scores_by_supplier: {...}}
    SVC->>DB: merge Commercial scores; recompute weighted

    QA->>API: POST score_evaluation {name, scorer_role: "QA Risk", scores_by_supplier: {...}}
    SVC->>DB: merge Compliance scores; recompute weighted; set recommended_candidate = top supplier name

    HTM->>API: POST transition_eval_workflow {name, action: "Hoàn tất chấm điểm"}
    API->>DB: frappe.model.workflow.apply_workflow(doc, action)
    Note over SVC: V1: gate enforcement Eval-side (G01/G02) chưa implement trong service; workflow JSON cho phép transition. Gate Decision-side (G04/G05) được enforce ở Decision tier.
    DB-->>API: workflow_state="Evaluated", docstatus=1
    API->>SVC: log_audit_event(event_type=imm03_eval_workflow_transition)
    API-->>HTM: {success: true, data: {workflow_state: "Evaluated", docstatus: 1}}
```

---

## IV. Communication Diagram (Cross-module)

```
┌──────────────────────────────────────────────────────────────────────┐
│                     IMM-03 Cross-module Dependencies                 │
└──────────────────────────────────────────────────────────────────────┘

  IMM-02 (Tech Spec)
    │  [data] spec_ref pull-mode (V1: KHÔNG có event listener)
    │  create_evaluation(spec_ref) → đọc IMM Tech Spec.device_category, source_plan, source_plan_line, quantity
    └──────────────────────────────────► IMM-03 Vendor Evaluation (Draft)

  IMM-01 (Procurement Plan)
    │  [data] plan_line.allocated_budget → envelope check (VR-04)
    │  [write] update plan_line.status = "Awarded" on award_decision()
    └──────────────────────────────────► IMM-03 Procurement Decision

  IMM-03 Procurement Decision (Awarded)
    │  [event] imm03_decision_awarded → commissioning prep
    └──────────────────────────────────► IMM-04 (Commissioning)

  IMM-03 AC Purchase (minted)
    │  [link] imm_procurement_decision back-reference
    └──────────────────────────────────► AC Purchase (Wave 1 DocType)

  IMM-04 (Commissioning feedback)
    │  [data] delivery KPI, quality rejection → scorecard Delivery + Quality
    └──────────────────────────────────► IMM-03 Vendor Scorecard (quarterly)

  IMM-09 (Repair)
    │  [data] MTTR, response time per vendor → scorecard After-sales
    └──────────────────────────────────► IMM-03 Vendor Scorecard (quarterly)

  IMM-15 (Spare Parts)
    │  [data] spare fill rate, lead time per vendor → scorecard Spare
    └──────────────────────────────────► IMM-03 Vendor Scorecard (quarterly)

  IMM-10 (Compliance)
    │  [data] NC count, recall, FSCA per vendor → scorecard Compliance
    └──────────────────────────────────► IMM-03 Vendor Scorecard (quarterly)

  IMM-16 (Compliance Monitoring)
    │  [data] read Vendor Scorecard → compliance risk dashboard
    └──────────────────────────────────► IMM-03 (read-only dependency)

  AC Supplier (Wave 1)
    │  [extend] custom fields imm_avl_status/categories/score patch
    └──────────────────────────────────► IMM-03 (enriches, does NOT replace)
```

---

## V. Package Diagram

```
assetcore/
│
├── api/
│   └── imm03.py                   ← 22 whitelisted endpoints
│                                     (list_vendor_profiles, create_vendor_profile,
│                                      create_avl_entry, approve_avl, suspend_avl,
│                                      add_candidate, submit_quotations,
│                                      score_evaluation, transition_eval_workflow,
│                                      create_decision, award_decision,
│                                      record_contract, dashboard_kpis,
│                                      get_vendor_scorecard, ...)
│
├── services/
│   └── imm03.py                   ← Business logic (NO logic in controller)
│                                     (VR-01..07, Gate G01..G05,
│                                      award_decision, compute_eval_score,
│                                      update_vendor_scorecard, check_avl_expiry)
│
│                                     (Scheduler jobs gộp ở cùng module:
│                                      check_avl_expiry / check_audit_due /
│                                      check_decision_overdue — daily;
│                                      update_vendor_scorecard — cron `0 2 1 1,4,7,10 *`)
│                                     [KHÔNG có module tasks_imm03.py riêng]
│
├── assetcore/
│   ├── doctype/
│   │   ├── imm_vendor_evaluation/
│   │   │   ├── imm_vendor_evaluation.json
│   │   │   └── imm_vendor_evaluation.py   ← thin controller
│   │   ├── imm_procurement_decision/
│   │   │   ├── imm_procurement_decision.json
│   │   │   └── imm_procurement_decision.py
│   │   ├── imm_avl_entry/
│   │   │   ├── imm_avl_entry.json
│   │   │   └── imm_avl_entry.py
│   │   ├── imm_vendor_scorecard/
│   │   │   ├── imm_vendor_scorecard.json
│   │   │   └── imm_vendor_scorecard.py
│   │   ├── imm_supplier_audit/
│   │   │   ├── imm_supplier_audit.json
│   │   │   └── imm_supplier_audit.py
│   │   └── [child doctypes]/
│   │       ├── vendor_eval_criterion.json
│   │       ├── vendor_eval_candidate.json
│   │       ├── vendor_quotation_line.json
│   │       ├── vendor_cert.json
│   │       ├── audit_finding.json
│   │       └── scorecard_kpi_row.json
│   │
│   ├── workflow/
│   │   ├── imm_03_vendor_eval_workflow.json     ← 5 states (Draft, Open RFQ, Quotation Received, Evaluated, Cancelled)
│   │   ├── imm_03_decision_workflow.json         ← 9 states (Draft→Method Selected→Negotiation→Award Recommended→Pending Approval→Awarded→Contract Signed→PO Issued + Cancelled)
│   │   └── imm_03_avl_workflow.json              ← 5 states (Draft, Approved, Conditional, Suspended, Expired)
│
├── patches/
│   └── v3_1/
│       └── 003_install_imm03.py                  ← Bootstrap: reload DocTypes + AC Supplier/AC Purchase custom fields (qua create_custom_fields) + upsert 3 Workflow
│
└── tests/
    └── test_imm03.py                              ← Unit tests (TestParseWeighting, TestParseJsonField, TestComputeEvalScores, TestGateG04Method, TestMethodRules)
```
