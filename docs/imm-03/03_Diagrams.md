# 03 — Sơ đồ kỹ thuật — IMM-03 Đánh giá Nhà cung cấp & Quyết định Mua sắm

> ✅ Module LIVE — Wave 2. Backend và Frontend đã triển khai.

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-03 — Vendor Evaluation & Procurement Decision |
| Phiên bản | 0.1.0 |
| Ngày | 2026-05-08 |
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
    IMM_SUPPLIER_AUDIT }o--|| AC_SUPPLIER : "vendor"

    VENDOR_EVAL_CANDIDATE }o--|| AC_SUPPLIER : "supplier"
    IMM_AVL_ENTRY }o--|| AC_SUPPLIER : "supplier"

    AC_PURCHASE }o--|| IMM_PROCUREMENT_DECISION : "imm_procurement_decision"
    AC_PURCHASE }o--|| IMM_TECH_SPEC : "imm_tech_spec"

    AC_SUPPLIER {
        string name PK
        string supplier_name
        string imm_avl_status
        string imm_avl_categories
        date imm_last_audit_date
        date imm_next_audit_date
        float imm_overall_score
        string legal_name
        string vat_code
        string country
        string financial_health
    }

    IMM_VENDOR_EVALUATION {
        string name PK
        string spec_ref FK
        string plan_line
        date draft_date
        json weighting_scheme
        string recommended_candidate
        string workflow_state
        int docstatus
    }

    IMM_PROCUREMENT_DECISION {
        string name PK
        string spec_ref FK
        string evaluation_ref FK
        string plan_ref FK
        string procurement_method
        string winner_candidate
        string awarded_vendor FK
        currency awarded_price
        float envelope_check_pct
        string funding_source
        string board_approver
        string contract_no
        string ac_purchase_ref FK
        date awarded_date
        string workflow_state
        int docstatus
    }

    IMM_AVL_ENTRY {
        string name PK
        string supplier FK
        string device_category
        int validity_years
        date valid_from
        date valid_to
        string status
        string approver
        string workflow_state
        int docstatus
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
        string vendor FK
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
        string candidate_row
        string quotation_no
        date quotation_date
        date quotation_validity
        currency price
        string currency
        int delivery_days
        int warranty_months
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
        +seed_evaluation_from_spec(spec: dict) IMM_Vendor_Evaluation
        +add_vendor_to_evaluation(eval_name: str, vendor: str) dict
        +compute_eval_score(eval_doc: Document) None
        +validate_evaluation(eval_doc: Document) None
        +validate_decision(decision_doc: Document) None
        +before_submit_decision(decision_doc: Document) None
        +award_decision(decision_doc: Document) None
        +on_cancel_decision(decision_doc: Document) None
        +validate_avl(avl_doc: Document) None
        +activate_avl(avl_doc: Document) None
        +on_submit_audit(audit_doc: Document) None
        +validate_ac_purchase_imm_link(po_doc: Document) None
        +update_vendor_scorecard(vendor: str, period: dict) None
        -_vr01_min_candidates(doc: Document) None
        -_vr02_avl_check(doc: Document) None
        -_vr03_quotation_validity(doc: Document) None
        -_vr04_decision_within_envelope(doc: Document) None
        -_vr05_avl_active_required(doc: Document) None
        -_vr06_immutable_lifecycle_events(doc: Document) None
        -_vr07_unique_decision_per_spec(doc: Document) None
        -_validate_gate_g01(doc: Document) None
        -_validate_gate_g02(doc: Document) None
        -_validate_gate_g03(doc: Document) None
        -_validate_gate_g04(doc: Document) None
        -_validate_gate_g05(doc: Document) None
    }

    class Imm03Tasks {
        +check_avl_expiry() None
        +check_audit_due() None
        +check_decision_overdue() None
        +update_vendor_scorecard() None
    }

    class Imm03Api {
        +list_vendor_profiles(**kwargs) dict
        +get_vendor_profile(name: str) dict
        +create_vendor_profile(**kwargs) dict
        +add_vendor_cert(**kwargs) dict
        +list_avl(**kwargs) dict
        +create_avl_entry(**kwargs) dict
        +approve_avl(**kwargs) dict
        +suspend_avl(**kwargs) dict
        +list_evaluations(**kwargs) dict
        +add_candidate(**kwargs) dict
        +submit_quotations(**kwargs) dict
        +score_evaluation(**kwargs) dict
        +transition_eval_workflow(**kwargs) dict
        +create_decision(**kwargs) dict
        +award_decision(**kwargs) dict
        +record_contract(**kwargs) dict
        +dashboard_kpis(**kwargs) dict
        +get_vendor_scorecard(**kwargs) dict
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
    Imm03Tasks --> Imm03Service : delegates
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
    UI->>API: POST award_decision {name, winner_candidate, awarded_price, ...}
    API->>SVC: validate_decision(doc)
    SVC->>SVC: _vr05_avl_active_required(doc)
    SVC->>SVC: _vr04_decision_within_envelope(doc)
    SVC->>SVC: _validate_gate_g05(doc)
    alt Gate G05 fail
        SVC-->>API: raise ServiceError(BUSINESS_RULE, "G05: Thiếu contract_doc")
        API-->>UI: {success: false, error: "G05...", code: "BUSINESS_RULE"}
    end
    SVC->>CTRL: before_submit_decision(doc)
    CTRL->>DB: frappe.workflow.apply_transition("Awarded")
    CTRL->>SVC: award_decision(doc)
    SVC->>DB: frappe.new_doc("AC Purchase") → insert
    DB-->>SVC: po.name = "AC-PUR-2026-00112"
    SVC->>DB: doc.ac_purchase_ref = po.name; doc.save()
    SVC->>DB: write_audit_trail(doc, "PO Created", ...)
    SVC->>DB: update_plan_line_status(plan_ref, plan_line, "Awarded")
    SVC->>RT: frappe.publish_realtime("imm03_decision_awarded", {...})
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

    PROCUREMENT->>API: POST create_avl_entry {vendor, device_category, validity_years, valid_from}
    API->>SVC: validate_avl(doc)
    SVC->>DB: insert AVL Entry (status=Draft)
    API-->>PROCUREMENT: {success: true, data: {name: "AVL-2026-00045"}}

    VP->>API: POST approve_avl {name, approver, approval_doc}
    API->>SVC: activate_avl(doc)
    SVC->>DB: doc.status = "Approved"
    SVC->>DB: doc.valid_to = valid_from + validity_years (years)
    SVC->>DB: AC_Supplier.imm_avl_status = "Approved"
    SVC->>DB: AC_Supplier.imm_avl_categories += device_category
    DB-->>SVC: saved
    API-->>VP: {success: true, data: {name: "AVL-2026-00045", valid_to: "2028-04-30"}}

    Note over SCHED,DB: Scheduler daily check_avl_expiry()
    SCHED->>DB: SELECT * FROM imm_avl_entry WHERE valid_to <= today
    DB-->>SCHED: [AVL-2026-00045 (if expired)]
    SCHED->>DB: avl.status = "Expired"; supplier.imm_avl_status update
    SCHED->>DB: frappe.sendmail(ĐT-HĐ-NCC, "AVL hết hạn")
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

    HTM->>API: POST score_evaluation {name, scorer_role: "HTM", scores_by_candidate: {...}}
    API->>SVC: validate scorer_role vs criteria.group
    SVC->>DB: update candidate.scores (Technical criteria)
    SVC->>SVC: compute_eval_score(eval_doc) — partial
    DB-->>API: partial weighted scores

    KHTC->>API: POST score_evaluation {name, scorer_role: "KH-TC", scores_by_candidate: {...}}
    SVC->>DB: update candidate.scores (Commercial criteria)

    QA->>API: POST score_evaluation {name, scorer_role: "QA Risk", scores_by_candidate: {...}}
    SVC->>DB: update candidate.scores (Compliance criteria)
    SVC->>SVC: compute_eval_score(eval_doc) — all 5 groups complete
    SVC->>DB: eval_doc.recommended_candidate = top_candidate.name

    HTM->>API: POST transition_eval_workflow {name, action: "Hoàn tất chấm điểm"}
    API->>SVC: _validate_gate_g01(doc)
    alt G01 fail — Compliance chưa đủ
        SVC-->>API: raise ServiceError(BUSINESS_RULE, "G01: Thiếu scoring nhóm Compliance")
        API-->>HTM: {success: false, error: "G01:..."}
    else G01 pass
        SVC->>DB: workflow_state = "Evaluated"; docstatus = 1
        API-->>HTM: {success: true, data: {recommended: "abc123", weighted_score: 4.32}}
    end
```

---

## IV. Communication Diagram (Cross-module)

```
┌──────────────────────────────────────────────────────────────────────┐
│                     IMM-03 Cross-module Dependencies                 │
└──────────────────────────────────────────────────────────────────────┘

  IMM-02 (Tech Spec)
    │  [event] imm02_spec_locked → seed_evaluation_from_spec()
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
│   └── imm03.py                   ← 18 whitelisted endpoints
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
├── tasks_imm03.py                 ← Scheduler jobs
│                                     (check_avl_expiry — daily)
│                                     (check_audit_due — daily)
│                                     (check_decision_overdue — daily)
│                                     (update_vendor_scorecard — cron quarterly)
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
│   │   ├── imm_03_vendor_eval_workflow.json     ← 5 states
│   │   ├── imm_03_decision_workflow.json         ← 9 states
│   │   └── imm_03_avl_workflow.json              ← 4 states
│   │
│   └── custom/
│       ├── custom_field_ac_supplier_imm03.json   ← imm_avl_*, certifications
│       └── custom_field_ac_purchase_imm03.json   ← imm_procurement_decision, imm_tech_spec
│
├── patches/
│   ├── v0_1_0/
│   │   ├── create_imm03_doctypes.py
│   │   ├── add_supplier_imm_fields.py
│   │   ├── add_po_imm_fields.py
│   │   ├── install_imm03_workflows.py
│   │   ├── seed_eval_criteria_default.py
│   │   └── seed_procurement_method_config.py
│
└── tests/
    └── test_imm03.py               ← Unit + integration tests
```
