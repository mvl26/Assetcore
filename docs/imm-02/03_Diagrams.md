# IMM-02 — Sơ đồ Kiến trúc (Diagrams)

> ⚠️ Pending implementation — Wave 2

| Mục | Giá trị |
|---|---|
| Module | **IMM-02 — Thông số Kỹ thuật & Phân tích Thị trường** |
| Phiên bản | 1.0.0 |
| Ngày cập nhật | 2026-05-08 |
| Owner | Tech Lead |
| Liên kết | [02 Analysis Design](./02_Analysis_Design.md) · [04 Backend Design](./04_Backend_Design.md) |

---

# Phần I — Entity Relationship Diagram (ERD)

```mermaid
erDiagram
    IMM_Tech_Spec {
        string name PK
        string spec_id
        date draft_date
        string source_plan FK
        string source_plan_line
        string source_needs_request FK
        string device_model_ref FK
        string device_category
        int quantity
        string spec_template_ref
        string parent_spec FK
        string version
        int total_mandatory
        int total_optional
        string benchmark_ref FK
        int candidate_count
        string infra_status_overall
        string lock_in_risk_ref FK
        float lock_in_score
        text mitigation_plan
        string approver FK
        date approval_date
        text withdrawal_reason
        string workflow_state
    }

    IMM_Market_Benchmark {
        string name PK
        string spec_ref FK
        date benchmark_date
        string recommended_candidate
        json weighting_scheme
    }

    IMM_Lock_in_Risk_Assessment {
        string name PK
        string spec_ref FK
        date assessment_date
        float lock_in_score
        float threshold_used
        text mitigation_plan
        string mitigation_evidence
    }

    Tech_Spec_Requirement {
        string name PK
        string parent FK
        int seq
        string group
        string parameter
        string value_or_range
        string unit
        int is_mandatory
        int weight
        string test_method
        string evidence
        string remark
    }

    Benchmark_Candidate {
        string name PK
        string parent FK
        string manufacturer
        string model
        string country
        float spec_match_pct
        float price_estimate
        string price_source
        string support_tier
        string local_partner
        int in_avl
        float recommendation_score
        string notes
    }

    Infra_Compatibility_Item {
        string name PK
        string parent FK
        string domain
        string current_state
        string required_state
        string compatibility_status
        string upgrade_owner FK
        date upgrade_eta
        float upgrade_cost_estimate
        string evidence
    }

    Lock_in_Risk_Item {
        string name PK
        string parent FK
        string dimension
        int score
        float weight_pct
        float weighted
        string rationale
        string mitigation
    }

    Tech_Spec_Document {
        string name PK
        string parent FK
        string doc_type
        string file_attachment
        string version
        date issued_date
    }

    IMM_Audit_Trail {
        string name PK
        string root_doctype
        string root_record FK
        string event_type
        datetime timestamp
        string actor FK
        string from_status
        string to_status
        string notes
        string hash
    }

    IMM_Procurement_Plan {
        string name PK
    }

    IMM_Needs_Request {
        string name PK
    }

    IMM_Device_Model {
        string name PK
        string spec_template_ref
    }

    IMM_Tech_Spec ||--o{ Tech_Spec_Requirement : "requirements"
    IMM_Tech_Spec ||--o{ Infra_Compatibility_Item : "infra_compat"
    IMM_Tech_Spec ||--o{ Tech_Spec_Document : "documents"
    IMM_Tech_Spec ||--o| IMM_Market_Benchmark : "benchmark_ref"
    IMM_Tech_Spec ||--o| IMM_Lock_in_Risk_Assessment : "lock_in_risk_ref"
    IMM_Tech_Spec }o--|| IMM_Procurement_Plan : "source_plan"
    IMM_Tech_Spec }o--|| IMM_Needs_Request : "source_needs_request"
    IMM_Tech_Spec }o--|| IMM_Device_Model : "device_model_ref"
    IMM_Tech_Spec }o--o| IMM_Tech_Spec : "parent_spec (reissue)"
    IMM_Market_Benchmark ||--o{ Benchmark_Candidate : "candidates"
    IMM_Lock_in_Risk_Assessment ||--o{ Lock_in_Risk_Item : "items"
    IMM_Tech_Spec ||--o{ IMM_Audit_Trail : "root_record (IMM Tech Spec)"
```

---

# Phần II — Class Diagram

```mermaid
classDiagram
    class IMMTechSpecController {
        +name: str
        +workflow_state: str
        +before_insert()
        +validate()
        +before_submit()
        +on_submit()
        +before_save()
    }

    class IMMMarketBenchmarkController {
        +name: str
        +spec_ref: str
        +validate()
    }

    class IMMLockInRiskController {
        +name: str
        +spec_ref: str
        +validate()
    }

    class Imm02Service {
        +draft_from_plan(plan: str, plan_lines: List[str]) -> List[str]
        +seed_default_requirements(doc: Document) -> None
        +validate_tech_spec(doc: Document) -> None
        +_vr01_unique_per_plan_line(doc: Document) -> None
        +_vr02_mandatory_min_count(doc: Document) -> None
        +_vr03_test_method_present(doc: Document) -> None
        +_vr04_benchmark_min_3(doc: Document) -> None
        +_vr05_infra_completeness(doc: Document) -> None
        +_vr06_immutable_lifecycle_events(doc: Document) -> None
        +validate_gate_g01(doc: Document) -> None
        +validate_gate_g02(doc: Document) -> None
        +validate_gate_g03(doc: Document) -> None
        +validate_gate_g04(doc: Document) -> None
        +before_submit_tech_spec(doc: Document) -> None
        +lock_spec(doc: Document) -> None
        +validate_benchmark(doc: Document) -> None
        +compute_lock_in(doc: Document) -> None
        +compare_to_baseline(spec: Document) -> dict
        +check_overdue_drafts() -> None
        +withdraw_spec(spec_name: str, reason: str) -> dict
        +reissue_spec(spec_name: str) -> str
        +log_lifecycle_event(doc: Document, event_type: str) -> None
    }

    class Imm02API {
        +list_tech_specs(workflow_state, device_category, page, page_size) -> dict
        +get_tech_spec(name) -> dict
        +draft_from_plan(plan, plan_lines) -> dict
        +update_tech_spec(name, data) -> dict
        +add_requirement(name, requirement) -> dict
        +bulk_import_requirements(name, file_url) -> dict
        +submit_benchmark(spec_name, benchmark_data) -> dict
        +submit_infra_compat(spec_name, compat_data) -> dict
        +submit_lock_in_assessment(spec_name, assessment_data) -> dict
        +transition_workflow(name, action) -> dict
        +lock_spec(name) -> dict
        +withdraw_spec(name, reason) -> dict
        +reissue_spec(name) -> dict
        +dashboard_kpis() -> dict
    }

    class ServiceError {
        +code: ErrorCode
        +message: str
        +__init__(code, message)
    }

    class ErrorCode {
        <<enumeration>>
        VALIDATION
        BUSINESS_RULE
        BAD_STATE
        DUPLICATE
        NOT_FOUND
        FORBIDDEN
        INVALID_PARAMS
        INTERNAL
    }

    IMMTechSpecController --> Imm02Service : delegates
    IMMMarketBenchmarkController --> Imm02Service : delegates
    IMMLockInRiskController --> Imm02Service : delegates
    Imm02API --> Imm02Service : calls
    Imm02Service --> ServiceError : raises
    ServiceError --> ErrorCode : uses
```

---

# Phần III — Sequence Diagrams

## SD-01: Tạo Tech Spec từ Procurement Plan

```
KH-TC Officer    Imm02API        Imm02Service     Frappe DB       IMM-01
     │               │                │                │               │
     │─draft_from_plan(plan, lines)──►│                │               │
     │               │─validate PP exists──────────────►               │
     │               │◄─PP doc────────────────────────────             │
     │               │─draft_from_plan()──►            │               │
     │               │                │─_vr01 check─────►              │
     │               │                │◄─no conflict──────             │
     │               │                │─get Device Model──►            │
     │               │                │◄─spec_template_ref─            │
     │               │                │─create Tech Spec───►           │
     │               │                │─seed_default_requirements()    │
     │               │                │─insert()────────────►          │
     │               │                │─log_lifecycle_event()──►       │
     │               │                │─update plan_line status────────►│
     │               │◄─{success, created:[TS names]}──               │
     │◄─response─────│                │                │               │
```

## SD-02: Gate G01 — Gửi Rà Soát (Draft → Reviewing)

```
HTM Engineer     Imm02API        Imm02Service     Frappe WF
     │               │                │                │
     │─transition(G01 action)────────►│                │
     │               │─validate_tech_spec()──►         │
     │               │                │─_vr02 mandatory ≥1 ✓          │
     │               │                │─_vr03 test_method ✓           │
     │               │─validate_gate_g01()──►          │
     │               │                │─count mandatory────►           │
     │               │                │  < 8? → ServiceError(BUSINESS_RULE)
     │               │                │  ≥ 8? continue                │
     │               │                │─check test_method 100%──►     │
     │               │                │  missing? → ServiceError      │
     │               │─apply_workflow("Gửi rà soát")──►│               │
     │               │                │◄─state=Reviewing──             │
     │               │─log_lifecycle_event("Reviewing")───►            │
     │◄─{success, data:{state: "Reviewing"}}                           │
```

## SD-03: Lock Spec + Trigger IMM-03

```
VP Block1        Imm02API        Imm02Service     Frappe DB    IMM-03 Service
     │               │                │                │               │
     │─lock_spec(name)───────────────►│                │               │
     │               │─before_submit_tech_spec()──►    │               │
     │               │                │─validate_gate_g04()──►         │
     │               │                │─lock_in_score check──►         │
     │               │                │  > threshold + no mit? → Error │
     │               │─frappe.submit()─────────────────►               │
     │               │─lock_spec() on_submit──────►    │               │
     │               │                │─set Locked state──►            │
     │               │                │─log audit trail───►            │
     │               │                │─publish_realtime "imm02_spec_locked"────►
     │               │                │                │          seed Vendor Eval
     │               │                │─update IMM-01 plan_line status─►
     │               │                │─create IMM-10 Risk entry (if high lock-in)
     │◄─{success, data:{state: "Locked"}}                              │
```

---

# Phần IV — Communication Diagram (Cross-Module)

```
                        IMM-02 Tech Spec
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
          ▼                    ▼                    ▼
    IMM-01 Plan          IMM-04 Prep          IMM-10 Risk
    (Input trigger)    (Infra upgrade tasks) (Lock-in register)
    plan_line link     Need Major Upgrade     lock_in_score > threshold
          │                    │                    │
          │             IMM-03 Vendor         IMM-17 Predictive
          │             (Output trigger)      (Market data mart)
          │             imm02_spec_locked     benchmark export
          │
    IMM Device Model
    (spec_template_ref seed)

Cross-module calls:
─────────────────────────────────────────────────────────────────
IMM-01 → IMM-02:  draft_from_plan() triggered by PP.on_submit
IMM-02 → IMM-01:  set plan_line.status = "In Procurement" after Lock
IMM-02 → IMM-03:  publish_realtime("imm02_spec_locked") → seed vendor eval
IMM-02 → IMM-04:  auto-create IMM-04 Prep Item when infra "Need Upgrade"
IMM-02 → IMM-10:  create Risk Register entry when lock_in_score > threshold
IMM-02 → IMM-17:  export benchmark data to market trend data mart
```

---

# Phần V — Package Diagram (File Layout)

```
assetcore/                                    ⚠️ PLANNED
├── assetcore/
│   ├── doctype/
│   │   ├── imm_tech_spec/                    ⚠️ PLANNED
│   │   │   ├── imm_tech_spec.json
│   │   │   ├── imm_tech_spec.py
│   │   │   └── test_imm_tech_spec.py
│   │   ├── imm_market_benchmark/             ⚠️ PLANNED
│   │   │   ├── imm_market_benchmark.json
│   │   │   ├── imm_market_benchmark.py
│   │   │   └── test_imm_market_benchmark.py
│   │   ├── imm_lock_in_risk_assessment/      ⚠️ PLANNED
│   │   │   ├── imm_lock_in_risk_assessment.json
│   │   │   └── imm_lock_in_risk_assessment.py
│   │   ├── tech_spec_requirement/            ⚠️ PLANNED
│   │   ├── benchmark_candidate/              ⚠️ PLANNED
│   │   ├── infra_compatibility_item/         ⚠️ PLANNED
│   │   ├── lock_in_risk_item/                ⚠️ PLANNED
│   │   └── tech_spec_document/               ⚠️ PLANNED
│   ├── workflow/
│   │   └── imm_02_spec_workflow.json         ⚠️ PLANNED
│   └── fixtures/
│       ├── imm_lock_in_weights.json          ⚠️ PLANNED
│       └── imm_default_spec_templates.json   ⚠️ PLANNED
├── services/
│   └── imm02.py                              ⚠️ PLANNED
├── api/
│   └── imm02.py                              ⚠️ PLANNED
├── tasks_imm02.py                            ⚠️ PLANNED
└── patches/
    └── v1_1_0/
        ├── create_imm02_doctypes.py          ⚠️ PLANNED
        ├── install_imm02_workflow.py         ⚠️ PLANNED
        ├── seed_lock_in_weights.py           ⚠️ PLANNED
        └── seed_default_spec_templates.py    ⚠️ PLANNED

frontend/src/
├── views/imm02/
│   ├── TechSpecList.vue                      ⚠️ PLANNED
│   ├── TechSpecDetail.vue                    ⚠️ PLANNED
│   ├── MarketBenchmarkDetail.vue             ⚠️ PLANNED
│   ├── LockInRiskDetail.vue                  ⚠️ PLANNED
│   └── Imm02Dashboard.vue                   ⚠️ PLANNED
├── components/imm02/
│   ├── RequirementEditor.vue                 ⚠️ PLANNED
│   ├── BenchmarkTable.vue                    ⚠️ PLANNED
│   ├── InfraCompatCardGrid.vue               ⚠️ PLANNED
│   ├── LockInRadar.vue                       ⚠️ PLANNED
│   ├── WorkflowStepper.vue                   ⚠️ PLANNED
│   └── VersionTimeline.vue                  ⚠️ PLANNED
├── stores/
│   └── imm02.ts                              ⚠️ PLANNED
└── api/
    └── imm02.ts                              ⚠️ PLANNED
```
