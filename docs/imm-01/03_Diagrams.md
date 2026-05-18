# 03 — Diagrams — IMM-01 Đánh giá Nhu cầu & Dự toán

> **Wave 2 — Live.** Các diagram phản ánh code thực tế. Các phần đánh dấu `(planned)` là roadmap chưa wire.

| Mục | Giá trị |
|---|---|
| Module | IMM-01 — Đánh giá nhu cầu và dự toán |
| Cập nhật | 2026-05-14 |
| Liên kết | [02 Analysis](./02_Analysis_Design.md) · [04 Backend](./04_Backend_Design.md) · [05 API](./05_API_Specification.md) |

---

## §I ERD (Entity Relationship Diagram)

```mermaid
erDiagram
    IMM_Needs_Request {
        string name PK
        string naming_series
        date request_date
        string request_type
        string requesting_department FK
        string clinical_head
        string workflow_state
        string priority_class
        string device_model_ref FK
        string device_category
        int quantity
        int target_year
        float weighted_score
        text clinical_justification
        string replacement_for_asset FK
        float utilization_pct_12m
        float downtime_hr_12m
        bool compliance_driven
        currency total_capex
        currency total_opex_5y
        currency tco_5y
        string funding_source
        string funding_evidence
        string board_approver
        date approval_date
        text rejection_reason
        string procurement_plan FK
        string tech_spec_ref
        string amended_from
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
        string asset_category
    }

    AC_Department {
        string name PK
        string department_name
        string dept_head
    }

    AC_Asset {
        string name PK
        string asset_name
        string imm_lifecycle_status
    }

    IMM_Needs_Request ||--o{ Needs_Priority_Scoring : "scoring_rows"
    IMM_Needs_Request ||--o{ Budget_Estimate_Line : "budget_lines"
    IMM_Needs_Request }o--|| IMM_Procurement_Plan : "procurement_plan"
    IMM_Procurement_Plan ||--o{ Procurement_Plan_Line : "plan_items"
    Procurement_Plan_Line }o--|| IMM_Needs_Request : "needs_request"
    IMM_Demand_Forecast ||--o{ Forecast_Driver : "drivers"
    IMM_Needs_Request }o--|| IMM_Device_Model : "device_model_ref"
    IMM_Needs_Request }o--|| AC_Department : "requesting_department"
    IMM_Needs_Request }o--o| AC_Asset : "replacement_for_asset"
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
        +before_insert_needs_request(doc) void
        +validate_needs_request(doc) void
        +before_submit_needs_request(doc) void
        +on_submit_needs_request(doc) void
        +on_cancel_needs_request(doc) void
        +validate_procurement_plan(doc) void
        +on_submit_procurement_plan(doc) void
        +roll_into_plan(plan_year, plan_period, needs_requests) str
        +generate_demand_forecast() void
        +check_pending_request_overdue() void
        +budget_envelope_alert() void
        +write_audit_trail(doc, event_type, from, to, notes) void
        -_compute_priority_score(doc) void
        -_classify_priority(score) str
        -_rollup_budget(doc) void
        -_rollup_plan_capex(doc) void
        -_vr01_unique_active_request_per_asset(doc) void
        -_vr02_replacement_requires_decom_plan(doc) void
        -_vr04_target_year(doc) void
        -_vr05_score_consistency(doc) void
        -_check_workflow_gates(doc) void
        -_validate_gate_g01(doc) void
        -_validate_gate_g02(doc) void
        -_validate_gate_g03(doc) void
        -_validate_gate_g04(doc) void
        -_validate_gate_g05(doc) void
        -_sync_clinical_head_from_department(doc) void
        -_autofetch_replacement_metrics(doc) void
    }

    class Imm01API {
        +list_needs_requests(filters, page, page_size, order_by) dict
        +get_needs_request(name) dict
        +get_allowed_transitions(name) dict
        +create_needs_request(payload) dict
        +update_needs_request(name, payload) dict
        +submit_needs_request(name) dict
        +score_needs_request(name, scoring_rows) dict
        +submit_budget_estimate(name, budget_lines, funding_source, funding_evidence) dict
        +transition_workflow(name, action) dict
        +approve_needs_request(name, board_approver, remarks) dict
        +reject_needs_request(name, rejection_reason) dict
        +list_procurement_plans(filters, page, page_size) dict
        +get_procurement_plan(name) dict
        +create_procurement_plan(plan_year, plan_period, budget_envelope) dict
        +set_budget_envelope(name, budget_envelope) dict
        +approve_plan(name) dict
        +activate_plan(name) dict
        +close_plan(name) dict
        +roll_into_plan(plan_year, plan_period, needs_requests) dict
        +remove_from_plan(plan_name, needs_request) dict
        +get_demand_forecast(forecast_year, device_category) dict
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

    CH->>FE: Fill form (request_type=New, device_model, justification, quantity, target_year)
    CH->>FE: Nhấn "Tạo phiếu"
    FE->>API: POST create_needs_request(payload)
    API->>SVC: before_insert_needs_request(doc)
    SVC->>SVC: set request_date=today, sync clinical_head từ AC Department
    API->>SVC: validate_needs_request(doc)
    SVC->>SVC: _vr04_target_year, _vr01_unique_active_request_per_asset
    SVC->>SVC: _compute_priority_score, _rollup_budget
    SVC->>SVC: _check_workflow_gates(state=Draft) → no-op
    API->>DB: doc.insert() (workflow_state=Draft)
    API-->>FE: {success: true, data: {name: "NR-26-04-00012", workflow_state: "Draft"}}

    CH->>FE: Nhấn "Gửi đề xuất"
    FE->>API: POST transition_workflow(name, action="Gửi đề xuất")
    API->>SVC: apply_workflow → Submitted
    API-->>FE: {success: true, data: {workflow_state: "Submitted"}}
    Note over AT: IMM Audit Trail chỉ ghi khi replacement_for_asset có giá trị<br/>(via write_audit_trail). Pre-asset: Frappe Version track_changes.
    FE-->>CH: Toast "Phiếu đã gửi"
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
    API->>SVC: doc.save() → validate_needs_request → _compute_priority_score(doc)
    SVC->>SVC: weights = DEFAULT_PRIORITY_WEIGHTS (hardcoded, master config = placeholder)
    SVC->>SVC: weighted_score = Σ score_i × weight_i (precision=4)
    SVC->>SVC: priority_class via _classify_priority (P1 ≥ 4.0)
    API-->>FE: {success: true, data: {weighted_score: 4.35, priority_class: "P1"}}
    FE-->>HTM: Dial hiển thị 4.35/5.0, badge P1 đỏ

    HTM->>FE: Nhấn "Hoàn tất chấm điểm"
    FE->>API: POST transition_workflow(name, action="Hoàn tất chấm điểm")
    API->>SVC: apply_workflow → khi target state = Prioritized, validate chạy
    SVC->>SVC: _check_workflow_gates → _validate_gate_g02 (cần 6/6 criterion keys)
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

    VP->>FE: Mở NR ở Pending Approval (funding_source + board_approver đã set từ submit_budget_estimate)
    VP->>FE: Nhập board_approver, remarks, nhấn "Phê duyệt"
    FE->>API: POST approve_needs_request(name, board_approver, remarks)
    API->>SVC: set doc.board_approver, doc.workflow_state="Approved"
    API->>SVC: doc.submit() → before_submit_needs_request → _validate_gate_g05
    SVC->>SVC: G05: funding_source + board_approver bắt buộc → pass
    SVC->>SVC: before_submit set approval_date=today nếu chưa có
    API->>SVC: on_submit_needs_request → write_audit_trail
    SVC->>AT: IMM Audit Trail (CHỈ nếu replacement_for_asset có) — gắn vào asset
    API-->>FE: {success: true, data: {name, workflow_state: "Approved"}}
    FE-->>VP: Toast "Phiếu đã được phê duyệt"

    Note over API,SVC: Auto-roll vào Procurement Plan = placeholder (TODO trong on_submit_needs_request)
    Note over API,SVC: KH-TC Officer thủ công gọi roll_into_plan(plan_year, plan_period, [nr_names])
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
│   │   ├── imm_needs_request/         ✅
│   │   │   ├── imm_needs_request.json
│   │   │   └── imm_needs_request.py
│   │   ├── imm_procurement_plan/      ✅
│   │   │   ├── imm_procurement_plan.json
│   │   │   └── imm_procurement_plan.py
│   │   ├── imm_demand_forecast/       ✅
│   │   ├── needs_priority_scoring/    ✅ (child)
│   │   ├── budget_estimate_line/      ✅ (child)
│   │   ├── procurement_plan_line/     ✅ (child)
│   │   └── forecast_driver/           ✅ (child)
│   └── workflow/
│       ├── imm_01_needs_workflow.json ✅
│       └── imm_01_plan_workflow.json  ✅
├── services/
│   └── imm01.py                       ✅ (~500 LOC)
├── api/
│   └── imm01.py                       ✅ (~430 LOC, 22 endpoints)
├── patches/v3_1/
│   └── 001_install_imm01.py           ✅ (idempotent — workflow upsert)
└── tests/
    └── test_imm01.py                  ✅ (scoring + classification — `TestPriorityClassification`, `TestComputePriorityScore`)

frontend/src/
├── views/needs/                       ✅ (5 files)
│   ├── NeedsRequestListView.vue
│   ├── NeedsRequestCreateView.vue
│   ├── NeedsRequestDetailView.vue
│   ├── ProcurementPlanListView.vue
│   └── ProcurementPlanDetailView.vue
├── stores/
│   └── imm01.ts                       ✅
├── api/
│   └── imm01.ts                       ✅
└── types/
    └── imm01.ts                       ✅
```

> Dashboard view chuyên biệt `Imm01Dashboard.vue` chưa tách riêng — `dashboard_kpis` được hiển thị ngay trên `NeedsRequestListView.vue` (xem 06 §I). Demand Forecast heatmap = roadmap.
