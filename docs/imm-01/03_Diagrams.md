# 03 — Diagrams — IMM-01 Đánh giá Nhu cầu & Dự toán

> ⚠️ Pending implementation — Wave 2. Các diagram dưới đây là thiết kế dự kiến, chưa có code.

| Mục | Giá trị |
|---|---|
| Module | IMM-01 — Đánh giá nhu cầu và dự toán |
| Liên kết | [02 Analysis](./02_Analysis_Design.md) · [04 Backend](./04_Backend_Design.md) · [05 API](./05_API_Specification.md) |

---

## §I ERD (Entity Relationship Diagram)

```mermaid
erDiagram
    IMM_Needs_Request {
        string name PK
        string request_type
        string requesting_department
        string device_model_ref
        int quantity
        int target_year
        string workflow_state
        float weighted_score
        string priority_class
        currency total_capex
        currency total_opex_5y
        currency tco_5y
        string funding_source
        string board_approver
        date approval_date
        string rejection_reason
        string replacement_for_asset
        float utilization_pct_12m
        float downtime_hr_12m
        bool compliance_driven
        string procurement_plan
        string tech_spec_ref
    }

    Needs_Priority_Scoring {
        string parent FK
        string criterion
        int score
        float weight_pct
        float weighted
        text evidence
    }

    Budget_Estimate_Line {
        string parent FK
        string budget_section
        string line_type
        int year_offset
        float qty
        currency unit_cost
        currency amount
        string benchmark_source
    }

    IMM_Procurement_Plan {
        string name PK
        string plan_period
        int plan_year
        currency budget_envelope
        currency allocated_capex
        float utilization_pct
        string workflow_state
        string approved_by
        date approved_date
    }

    Procurement_Plan_Line {
        string parent FK
        string needs_request
        int priority_rank
        currency allocated_budget
        string target_quarter
        string status
    }

    IMM_Demand_Forecast {
        string name PK
        int forecast_year
        int horizon_years
        string device_category
        int projected_qty
        currency projected_capex
        float accuracy_prev
        datetime generated_at
        string generated_by
    }

    Forecast_Driver {
        string parent FK
        string driver_type
        float weight_pct
        float projected_value
        string source_module
    }

    IMM_Audit_Trail {
        string name PK
        string root_doctype
        string root_record
        string event_type
        string from_status
        string to_status
        string actor
        datetime timestamp
        string ip_address
        text notes
    }

    IMM_Device_Model {
        string name PK
        string model_name
        string device_category
    }

    Department {
        string name PK
    }

    Asset {
        string name PK
        string status
    }

    IMM_Needs_Request ||--o{ Needs_Priority_Scoring : "scoring_rows"
    IMM_Needs_Request ||--o{ Budget_Estimate_Line : "budget_lines"
    IMM_Needs_Request }o--|| IMM_Procurement_Plan : "procurement_plan"
    IMM_Procurement_Plan ||--o{ Procurement_Plan_Line : "plan_items"
    Procurement_Plan_Line }o--|| IMM_Needs_Request : "needs_request"
    IMM_Demand_Forecast ||--o{ Forecast_Driver : "drivers"
    IMM_Needs_Request }o--|| IMM_Device_Model : "device_model_ref"
    IMM_Needs_Request }o--|| Department : "requesting_department"
    IMM_Needs_Request }o--o| Asset : "replacement_for_asset"
    IMM_Audit_Trail }o--|| IMM_Needs_Request : "root_record (root_doctype=IMM Needs Request)"
    IMM_Audit_Trail }o--|| IMM_Procurement_Plan : "root_record (root_doctype=IMM Procurement Plan)"
```

---

## §II Class Diagram

```mermaid
classDiagram
    class IMMNeedsRequestController {
        +before_insert(doc)
        +validate(doc)
        +before_submit(doc)
        +on_submit(doc)
        +on_cancel(doc)
    }

    class IMMProcurementPlanController {
        +validate(doc)
        +on_submit(doc)
    }

    class Imm01Service {
        +initialize_needs_request(doc) void
        +compute_priority_score(doc) float
        +validate_budget_estimate(doc) void
        +validate_needs_request(doc) void
        +before_submit_needs_request(doc) void
        +on_submit_needs_request(doc) void
        +on_cancel_needs_request(doc) void
        +validate_procurement_plan(doc) void
        +on_submit_procurement_plan(doc) void
        +roll_into_procurement_plan(doc) str
        +generate_demand_forecast(period) str
        +check_pending_request_overdue() void
        +log_lifecycle_event(doc, event_type, from_status, to_status) void
        -_vr01_unique_active_request_per_asset(doc) void
        -_vr02_replacement_requires_decom_plan(doc) void
        -_vr03_clinical_justification(doc) void
        -_vr04_target_year(doc) void
        -_vr05_score_consistency(doc) void
        -_vr06_immutable_lifecycle_events(doc) void
        -validate_gate_g01(doc) void
        -validate_gate_g02(doc) void
        -validate_gate_g03(doc) void
        -validate_gate_g04(doc) void
        -validate_gate_g05(doc) void
    }

    class Imm01API {
        +list_needs_requests(filters, page, page_size) dict
        +get_needs_request(name) dict
        +create_needs_request(request_type, ...) dict
        +update_needs_request(name, ...) dict
        +submit_needs_request(name) dict
        +score_needs_request(name, scoring_rows) dict
        +compute_priority(name) dict
        +submit_budget_estimate(name, budget_lines, funding_source) dict
        +transition_workflow(name, action) dict
        +approve_needs_request(name, board_approver, remarks) dict
        +reject_needs_request(name, rejection_reason) dict
        +list_procurement_plans(plan_year, plan_period) dict
        +roll_into_plan(plan_year, plan_period, needs_requests) dict
        +get_demand_forecast(forecast_year, horizon_years) dict
        +dashboard_kpis(period) dict
    }

    class ServiceError {
        +code: ErrorCode
        +message: str
    }

    class ErrorCode {
        <<enum>>
        VALIDATION
        BUSINESS_RULE
        BAD_STATE
        DUPLICATE
        NOT_FOUND
        FORBIDDEN
        INVALID_PARAMS
        INTERNAL
    }

    IMMNeedsRequestController --> Imm01Service : delegates
    IMMProcurementPlanController --> Imm01Service : delegates
    Imm01API --> Imm01Service : calls
    Imm01Service ..> ServiceError : raises
    ServiceError --> ErrorCode : uses
```

---

## §III Sequence Diagrams

### SD-01: Tạo và Submit Needs Request (Happy Path)

```mermaid
sequenceDiagram
    participant CH as Clinical Head
    participant FE as Frontend Vue
    participant API as API imm01
    participant SVC as Service imm01
    participant DB as MariaDB
    participant AT as IMM Audit Trail

    CH->>FE: Mở form Needs Request mới
    FE->>API: GET device_model_ref options
    API->>DB: frappe.get_list("IMM Device Model")
    DB-->>API: [models]
    API-->>FE: [{name, label}]

    CH->>FE: Fill form (request_type=New, device_model, justification ≥200, quantity, target_year)
    CH->>FE: Nhấn "Gửi đề xuất"
    FE->>API: POST create_needs_request + submit_needs_request
    API->>SVC: initialize_needs_request(doc)
    SVC->>DB: set request_date=today, fetch clinical_head
    API->>SVC: validate_needs_request(doc)
    SVC->>SVC: _vr03_clinical_justification (≥200 pass)
    SVC->>SVC: _vr04_target_year (≥2026 pass)
    SVC->>SVC: validate_gate_g01 (New type → skip utilization)
    API->>DB: doc.insert() + workflow_state=Submitted
    API->>SVC: log_lifecycle_event(doc, "submitted", "Draft", "Submitted")
    SVC->>AT: Insert IMM Audit Trail record
    API->>DB: frappe.sendmail(PTP Khối 1, KH-TC)
    API-->>FE: {success: true, data: {name: "NR-26-04-00012", workflow_state: "Submitted"}}
    FE-->>CH: Toast "Phiếu đã gửi thành công"
```

### SD-02: Chấm điểm ưu tiên và chuyển Prioritized

```mermaid
sequenceDiagram
    participant HTM as HTM Reviewer
    participant FE as Frontend Vue
    participant API as API imm01
    participant SVC as Service imm01
    participant DB as MariaDB

    HTM->>FE: Mở NR ở Reviewing, Tab "Chấm điểm"
    HTM->>FE: Nhập 6 scoring rows (criteria + scores)
    FE->>API: POST score_needs_request(name, scoring_rows)
    API->>SVC: compute_priority_score(doc)
    SVC->>DB: get_master_weights() hoặc dùng DEFAULT_WEIGHTS
    SVC->>SVC: weighted_score = Σ score_i × weight_i = 4.30
    SVC->>SVC: priority_class = "P1" (score ≥ 4.0)
    API-->>FE: {success: true, data: {weighted_score: 4.30, priority_class: "P1"}}
    FE-->>HTM: Dial hiển thị 4.30/5.0, badge P1 đỏ

    HTM->>FE: Nhấn "Hoàn tất chấm điểm"
    FE->>API: POST transition_workflow(name, action="Hoàn tất chấm điểm")
    API->>SVC: validate_gate_g02(doc)
    SVC->>SVC: count scoring_rows = 6/6 pass
    API->>DB: apply_workflow_action → state = Prioritized
    API->>SVC: log_lifecycle_event("prioritized", "Reviewing", "Prioritized")
    API-->>FE: {success: true, data: {workflow_state: "Prioritized"}}
    FE-->>HTM: Stepper cập nhật → ●Prioritized
```

### SD-03: BGĐ Approve và Roll into Procurement Plan

```mermaid
sequenceDiagram
    participant VP as VP Block1
    participant FE as Frontend Vue
    participant API as API imm01
    participant SVC as Service imm01
    participant DB as MariaDB
    participant AT as IMM Audit Trail

    VP->>FE: Mở NR ở Pending Approval
    VP->>FE: Nhập board_approver=self, funding_source="NSNN", remarks
    VP->>FE: Nhấn "Phê duyệt"
    FE->>API: POST approve_needs_request(name, board_approver, remarks)
    API->>SVC: validate_gate_g05(doc)
    SVC->>SVC: board_approver + funding_source set → pass
    API->>DB: doc.submit() → docstatus=1, workflow_state=Approved
    API->>SVC: log_lifecycle_event("approved", "Pending Approval", "Approved")
    SVC->>AT: Insert audit record
    API-->>FE: {success: true, data: {workflow_state: "Approved"}}
    FE-->>VP: Toast "Phiếu đã được phê duyệt"

    Note over API,SVC: Auto-roll nếu config auto_roll_into_plan=1
    API->>SVC: roll_into_procurement_plan(doc)
    SVC->>DB: frappe.get_doc("IMM Procurement Plan", {plan_year, plan_period}) hoặc tạo mới
    SVC->>DB: append plan_item, sort by weighted_score desc
    SVC->>DB: update IMM Needs Request.procurement_plan = plan.name
```

---

## §IV Communication Diagram (Cross-module)

```
IMM-01 (Needs Assessment)
    │
    ├── INPUT ← IMM-07 (Performance Tracking)
    │           API: imm07.get_asset_kpi_12m(asset)
    │           Trả về: utilization_pct, downtime_hr_12m
    │
    ├── INPUT ← IMM-13 (Decommission)
    │           API: imm13.get_active_decom_plan(asset)
    │           Trả về: plan_name, status (Pending/Approved)
    │
    ├── INPUT ← IMM-10 (Compliance)
    │           Hook: on_compliance_gap_new → compliance_driven=1
    │
    ├── OUTPUT → IMM-02 (Tech Spec)
    │           API: imm02.draft_from_plan(plan, plan_items)
    │           Trigger: Procurement Plan action "Generate Tech Spec Drafts"
    │
    ├── OUTPUT → IMM-03 (Vendor / PO)
    │           API: imm03.create_vendor_eval_from_plan(plan)
    │           Trigger: Sau khi Tech Spec lock
    │
    ├── OUTPUT → IMM-15 (Spare Parts)
    │           Event: imm01_demand_forecast_published
    │           Payload: {forecast_year, horizon_years, device_category}
    │
    └── OUTPUT → IMM-17 (Predictive)
                Event: imm01_demand_forecast_published
                Payload: {forecast_year, matrix[]}
```

---

## §V Package Diagram (File layout)

```
assetcore/
├── assetcore/
│   ├── doctype/
│   │   ├── imm_needs_request/         ⚠️ PLANNED
│   │   │   ├── imm_needs_request.json
│   │   │   ├── imm_needs_request.py
│   │   │   └── test_imm_needs_request.py
│   │   ├── imm_procurement_plan/      ⚠️ PLANNED
│   │   │   ├── imm_procurement_plan.json
│   │   │   └── imm_procurement_plan.py
│   │   ├── imm_demand_forecast/       ⚠️ PLANNED
│   │   ├── needs_priority_scoring/    ⚠️ PLANNED (child)
│   │   ├── budget_estimate_line/      ⚠️ PLANNED (child)
│   │   ├── procurement_plan_line/     ⚠️ PLANNED (child)
│   │   └── forecast_driver/           ⚠️ PLANNED (child)
│   └── workflow/
│       └── imm_01_needs_workflow.json ⚠️ PLANNED
├── services/
│   └── imm01.py                       ⚠️ PLANNED
├── api/
│   └── imm01.py                       ⚠️ PLANNED
├── tasks_imm01.py                     ⚠️ PLANNED
└── tests/
    ├── test_imm01_service.py          ⚠️ PLANNED
    ├── test_imm_needs_request.py      ⚠️ PLANNED
    ├── test_imm01_workflow.py         ⚠️ PLANNED
    └── test_imm01_api.py              ⚠️ PLANNED

frontend/src/
├── views/imm01/
│   ├── NeedsRequestList.vue           ⚠️ PLANNED
│   ├── NeedsRequestCreate.vue         ⚠️ PLANNED
│   ├── NeedsRequestDetail.vue         ⚠️ PLANNED
│   ├── ProcurementPlanList.vue        ⚠️ PLANNED
│   ├── ProcurementPlanDetail.vue      ⚠️ PLANNED
│   ├── DemandForecastView.vue         ⚠️ PLANNED
│   └── Imm01Dashboard.vue             ⚠️ PLANNED
├── stores/
│   └── imm01.ts                       ⚠️ PLANNED
└── api/
    └── imm01.ts                       ⚠️ PLANNED
```
