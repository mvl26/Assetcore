# 03 — Diagrams

| Mục | Giá trị |
|---|---|
| Module | IMM-12 — Incident & CAPA Management |
| Phạm vi | Per-module |
| Owner | BA + Architect |
| Cập nhật | 2026-05-18 |
| Trạng thái | ✅ Live — ERD / class / sequence diagrams khớp DocType + `services/imm12.py` hiện hành |

---

## 1. ERD

```mermaid
erDiagram
    AC_Asset ||--o{ IncidentReport : "has incidents"
    AC_Asset ||--o{ IMM_CAPA_Record : "has CAPAs"
    AC_Asset ||--o{ Asset_Lifecycle_Event : "tracks lifecycle"
    AC_Asset ||--o{ IMM_Audit_Trail : "audit history"

    IncidentReport ||--o| RCA_Record : "triggers (Major/Critical/Chronic)"
    IncidentReport ||--o| IMM_CAPA_Record : "results in"

    RCA_Record ||--o{ RCA_Related_Incident : "groups (chronic failure)"
    RCA_Related_Incident }o--|| IncidentReport : "links to"
    RCA_Record ||--o{ RCA_Five_Why_Step : "5-Why steps"
    RCA_Record ||--|| IMM_CAPA_Record : "creates (BR-12-06)"

    IMM_CAPA_Record {
        string name PK
        string asset FK
        string source_doctype
        string source_name
        string fault_severity
        text root_cause
        text corrective_action
        text preventive_action
        date due_date
        string status
    }

    IncidentReport {
        string name PK
        string asset FK
        string severity
        string fault_code
        text clinical_impact
        string status
        string rca_record FK
        string linked_capa FK
        bool chronic_failure_flag
        datetime reported_at
    }

    RCA_Record {
        string name PK
        string asset FK
        string incident_report FK
        string trigger_type
        string rca_method
        text root_cause
        date due_date
        string status
        string linked_capa FK
    }

    RCA_Related_Incident {
        string parent FK
        string incident_report FK
        datetime reported_at
        string severity
    }

    RCA_Five_Why_Step {
        string parent FK
        int step_number
        string question
        text answer
    }
```

---

## 2. Entity Catalog

| Entity | DocType | Trạng thái | Owner |
|---|---|---|---|
| AC Asset | AC Asset | ✅ LIVE (IMM-00) | IMM-00 |
| Incident Report | Incident Report | ✅ LIVE (IMM-00 base) + ⚠️ Custom fields (IMM-12) | IMM-12 |
| IMM CAPA Record | IMM CAPA Record | ✅ LIVE (IMM-00) | IMM-00 |
| Asset Lifecycle Event | Asset Lifecycle Event | ✅ LIVE (IMM-00) | IMM-00 |
| IMM Audit Trail | IMM Audit Trail | ✅ LIVE (IMM-00) | IMM-00 |
| IMM RCA Record | IMM RCA Record (folder `imm_rca_record`) | ✅ Live (IMM-12) | IMM-12 |
| RCA Related Incident | RCA Related Incident | ✅ Live — Child table | IMM-12 |
| RCA Five Why Step | RCA Five Why Step | ✅ Live — Child table | IMM-12 |

---

## 3. Data Dictionary

### 3.1 Incident Report — Custom Fields (✅ Live IMM-12)

> Base fields LIVE từ IMM-00: `asset`, `reported_by`, `reported_at`, `fault_description`, `status`, `resolution_notes`.

| Field | Type | Ràng buộc | Notes |
|---|---|---|---|
| `severity` | Select | Required | Minor / Major / Critical |
| `fault_code` | Data | Optional | Catalog dictionary |
| `clinical_impact` | Text | Required if Critical (BR-12-01) | Tác động lâm sàng |
| `acknowledged_by` | Link User | Set khi Acknowledge | — |
| `acknowledged_at` | Datetime | Auto | — |
| `resolved_by` | Link User | Set khi Resolve | — |
| `resolved_at` | Datetime | Auto | — |
| `closed_by` | Link User | Set khi Close | — |
| `closed_at` | Datetime | Auto | — |
| `repair_wo` | Link Repair Work Order | Optional | IMM-09 link |
| `rca_record` | Link RCA Record | Auto when trigger | — |
| `rca_required` | Check | True if Major/Critical/Chronic | — |
| `linked_capa` | Link IMM CAPA Record | Set after RCA Submit | — |
| `chronic_failure_flag` | Check | True if chronic group | Set by scheduler |
| `assigned_to` | Link User | Technician in charge | — |

### 3.2 RCA Record (✅ Live)

Naming: `RCA-YYYY-NNNNN` · Submittable

| Field | Type | Ràng buộc | Notes |
|---|---|---|---|
| `asset` | Link AC Asset | Required | — |
| `incident_report` | Link Incident Report | Required | Primary source IR |
| `related_incidents` | Table | Optional | Child: RCA Related Incident |
| `fault_code` | Data | Optional | — |
| `trigger_type` | Select | Required | Major Incident / Critical Incident / Chronic Failure / Manual |
| `incident_count` | Int | Optional | Số IR liên quan (90 ngày, Chronic) |
| `rca_method` | Select | Required before Submit (BR-12-07) | 5Why / Fishbone / Other |
| `root_cause` | Text | Required before Submit (BR-12-07) | — |
| `contributing_factors` | Text | Optional | — |
| `five_why_steps` | Table | Optional | Child: RCA Five Why Step |
| `corrective_action_plan` | Text | Optional | Proposed CAPA content |
| `preventive_action_plan` | Text | Optional | Proposed CAPA content |
| `due_date` | Date | Required | +7d (Major/Critical) · +14d (Chronic) |
| `status` | Select | Required | RCA Required / RCA In Progress / Completed / Cancelled |
| `assigned_to` | Link User | Required | — |
| `completed_by` | Link User | Set on Submit | — |
| `completed_date` | Date | Auto | — |
| `linked_capa` | Link IMM CAPA Record | Auto after Submit | BR-12-06 |

### 3.3 IMM CAPA Record — Key Fields (✅ LIVE, IMM-00)

| Field | Type | Notes |
|---|---|---|
| `asset` | Link AC Asset | Required |
| `source_doctype` | Data | "Incident Report" / "RCA Record" |
| `source_name` | Dynamic Link | Reference |
| `fault_severity` | Select | Minor / Major / Critical |
| `root_cause` | Text | Required before Submit (BR-00-08) |
| `corrective_action` | Text | Required before Submit |
| `preventive_action` | Text | Required before Submit |
| `due_date` | Date | `due_days` from create |
| `status` | Select | Open / In Progress / Pending Verification / Closed / Overdue |

---

## 4. Class Diagram

```mermaid
classDiagram
    class IncidentReport {
        +string name
        +string asset
        +string severity
        +string fault_code
        +text clinical_impact
        +string status
        +bool chronic_failure_flag
        +before_insert()
        +validate()
        +on_submit()
    }

    class RCARecord {
        +string name
        +string asset
        +string trigger_type
        +string rca_method
        +text root_cause
        +string status
        +before_submit()
    }

    class Imm12Service {
        +report_incident(asset, fault_code, severity, ...) str
        +acknowledge_incident(name, assigned_to, notes) None
        +resolve_incident(name, resolution_notes) str|None
        +trigger_rca_if_required(incident_name) str|None
        +submit_rca_and_create_capa(rca_name, ...) str
        +close_incident(name) None
        +detect_chronic_failures() None
    }

    class Imm00Service {
        <<LIVE — IMM-00>>
        +create_capa(asset, source_doctype, ...) str
        +close_capa(capa_name, corrective_action, ...) None
        +log_audit_event(asset, event_type, ...) str
        +create_lifecycle_event(asset, event_type, ...) str
        +transition_asset_status(asset, new_status, reason) None
        +check_capa_overdue() None
    }

    class Imm12Api {
        +report_incident()
        +acknowledge_incident()
        +resolve_incident()
        +close_incident()
        +submit_rca()
        +get_chronic_failures()
        +get_dashboard()
    }

    Imm12Api --> Imm12Service : delegates
    Imm12Service --> Imm00Service : orchestrates
    Imm12Service --> IncidentReport : reads/writes
    Imm12Service --> RCARecord : creates
    IncidentReport --> RCARecord : triggers
    RCARecord --> Imm00Service : create_capa on submit
```

---

## 5. Sequence Diagram — report_incident Critical

```mermaid
sequenceDiagram
    actor User as Reporting User
    participant API as api/imm12.py
    participant SVC as imm12.report_incident()
    participant SVC00 as imm00 (LIVE)
    participant DB as Frappe DB

    User->>API: POST report_incident (severity=Critical)
    API->>SVC: report_incident(asset, fault_code, severity, clinical_impact, ...)

    SVC->>SVC: _validate_clinical_impact_if_critical()
    SVC->>DB: frappe.get_doc("Incident Report").insert()
    Note over DB: IR status = Open

    SVC->>SVC00: transition_asset_status(asset, "Out of Service")
    SVC00->>DB: Update AC Asset.lifecycle_status

    SVC->>SVC00: create_lifecycle_event(asset, "incident_reported", ...)
    SVC00->>DB: Insert Asset Lifecycle Event

    SVC->>SVC00: log_audit_event(asset, "incident_reported", ...)
    SVC00->>DB: Insert IMM Audit Trail

    SVC->>SVC: _notify_critical(asset, ir_name)
    Note over SVC: Email BGĐ + Workshop Lead

    SVC-->>API: ir_name
    API-->>User: {success: true, data: {name, status, asset_lifecycle_status: "Out of Service"}}
```

---

## 6. Sequence Diagram — submit_rca → CAPA

```mermaid
sequenceDiagram
    actor QA as QA Officer
    participant API as api/imm12.py
    participant SVC as imm12.submit_rca_and_create_capa()
    participant SVC00 as imm00 (LIVE)
    participant DB as Frappe DB

    QA->>API: POST submit_rca (rca_name, rca_method, root_cause, five_why_steps)
    API->>SVC: submit_rca_and_create_capa(rca_name, ...)

    SVC->>SVC: _validate_rca_complete (BR-12-07: root_cause + rca_method required)
    SVC->>DB: Update RCA Record (status=Completed, completed_date=today)

    SVC->>SVC00: create_capa(asset, "IMM RCA Record", rca_name, fault_severity, due_days=30)
    SVC00->>DB: Insert IMM CAPA Record (status=Open)
    SVC00-->>SVC: capa_name

    SVC->>DB: Update RCA Record.linked_capa = capa_name
    SVC->>DB: Update IR.linked_capa = capa_name

    SVC->>SVC00: log_audit_event(asset, "rca_completed", ...)
    SVC00->>DB: Insert IMM Audit Trail

    SVC-->>API: capa_name
    API-->>QA: {success: true, data: {name: rca_name, status: "Completed", linked_capa: capa_name}}
```

---

## 7. Sequence Diagram — detect_chronic_failures (Scheduler)

```mermaid
sequenceDiagram
    participant SCH as Scheduler (daily 02:00)
    participant SVC as imm12.detect_chronic_failures()
    participant SVC00 as imm00 (LIVE)
    participant DB as Frappe DB

    SCH->>SVC: detect_chronic_failures()
    SVC->>DB: SQL GROUP BY (asset, fault_code) HAVING COUNT >= 3 (90 days)
    DB-->>SVC: [rows]

    loop for each chronic group
        SVC->>DB: Check existing open RCA (idempotency guard)
        alt no open RCA
            SVC->>DB: Insert RCA Record (trigger_type=Chronic Failure, due +14d)
            SVC->>DB: Update IR.chronic_failure_flag = True for all in group
            SVC->>DB: Update AC Asset.chronic_failure_flag = True
            SVC->>SVC00: log_audit_event(asset, "chronic_failure_detected", ...)
            SVC->>SVC: _notify_chronic(asset, fault_code, rca_name)
        else RCA already open
            Note over SVC: Skip — idempotent
        end
    end

    SVC->>DB: frappe.db.commit()
```

---

## 8. Backend Package Diagram

```mermaid
flowchart TD
    subgraph api ["api/ (thin wrapper)"]
        A1["imm12.py ✅ Live\n• report_incident\n• acknowledge_incident\n• resolve_incident\n• close_incident\n• submit_rca\n• get_dashboard"]
        A0["imm00.py ✅ LIVE\n• create_capa\n• close_capa\n• list_capa"]
    end

    subgraph svc ["services/ (business logic)"]
        S12["imm12.py ✅ Live\n• report_incident()\n• trigger_rca_if_required()\n• detect_chronic_failures()\n• submit_rca_and_create_capa()"]
        S00["imm00.py ✅ LIVE\n• create_capa()\n• close_capa()\n• log_audit_event()\n• create_lifecycle_event()\n• transition_asset_status()"]
    end

    subgraph doctype ["DocType Controllers"]
        D12["IncidentReport.py ✅ Live\n(custom fields + validate)"]
        DRCA["RCARecord.py ✅ Live"]
        D00["IMMCAPARecord.py ✅ LIVE"]
    end

    A1 --> S12
    A0 --> S00
    S12 --> S00
    S12 --> D12
    S12 --> DRCA
    S00 --> D00
```

---

## 9. Frontend Package Diagram

```mermaid
flowchart TD
    subgraph views ["views/imm12/ ✅ Live"]
        V1["IncidentListView.vue"]
        V2["IncidentFormView.vue"]
        V3["CAPAListView.vue"]
        V4["CAPAFormView.vue"]
        V5["RCAFormView.vue"]
        V6["ChronicFailureView.vue"]
        V7["Imm12DashboardView.vue"]
    end

    subgraph comps ["components/imm12/ ✅ Live"]
        C1["SeverityBadge.vue"]
        C2["IncidentStatusBadge.vue"]
        C3["CAPAStatusBadge.vue"]
        C4["RCAFiveWhyEditor.vue"]
        C5["CAPACloseDialog.vue"]
        C6["IncidentTimeline.vue"]
    end

    subgraph store ["stores/ ✅ Live"]
        ST["imm12.ts (Pinia)\nuseImm12Store"]
    end

    subgraph api_layer ["api/ ✅ Live"]
        AP["imm12.ts\n• reportIncident()\n• acknowledgeIncident()\n• submitRCA()"]
    end

    views --> comps
    views --> store
    store --> api_layer
```

---

## DoD — File 03 hoàn chỉnh

- [x] ERD Mermaid với 8 entities (LIVE + Pending phân biệt rõ)
- [x] Entity catalog (owner + status)
- [x] Data dictionary: IR custom fields + RCA Record + CAPA key fields
- [x] Class diagram (Controller · Service · API layer)
- [x] Sequence diagram: `report_incident` Critical path
- [x] Sequence diagram: `submit_rca` → CAPA creation
- [x] Sequence diagram: `detect_chronic_failures` Scheduler
- [x] Backend package diagram
- [x] Frontend package diagram
- [ ] ⚠️ Reviewed bởi Architect + BA (Pending)
- [ ] ⚠️ Diagrams verified vs code after implementation
