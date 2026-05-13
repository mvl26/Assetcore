# 03 — Diagrams — IMM-06 Đào tạo & Quản lý năng lực

| Mục | Giá trị |
|---|---|
| Module | IMM-06 — User Training & Competency Management |
| Phiên bản tài liệu | 0.1.0 |
| Ngày cập nhật | 2026-05-08 |
| Liên kết | [02 Analysis](./02_Analysis_Design.md) · [04 Backend](./04_Backend_Design.md) · [05 API](./05_API_Specification.md) · [06 Frontend](./06_Frontend_Design.md) |

> ⚠️ Pending implementation — Module PLANNED (Wave 2). Tất cả diagram là thiết kế spec, chưa implement.

---

## §I ERD (Entity Relationship Diagram)

```mermaid
erDiagram
    IMM_Training_Program {
        string program_code PK
        string program_name
        string training_type
        link target_device_model
        link target_device_category
        int validity_period_months
        float passing_score_pct
        string assessment_method
        int is_mandatory_for_operation
        int is_active
        link qms_doc_ref
    }

    IMM_Training_Session {
        string name PK
        link training_program FK
        date session_date
        string session_type
        string location
        link instructor
        string instructor_external_name
        float duration_planned_hours
        float duration_actual_hours
        string workflow_state
    }

    IMM_Training_Participant {
        string name PK
        link parent FK
        link user
        link department
        float attendance_pct
        float theory_score
        float practical_score
        string overall_result
        link competency_record
    }

    IMM_User_Competency {
        string name PK
        link user
        link device_model
        link training_program FK
        link training_session FK
        string competency_level
        date achieved_date
        int validity_months
        date expiry_date
        date recertification_due_date
        string workflow_state
        link supervisor_signoff
        date signoff_date
        link certificate_file
        string revoke_reason
        link revoke_capa_ref
        link revoked_by
        link department_at_assessment
    }

    IMM_Competency_Gap_Report {
        string name PK
        date report_date
        string scope
        int total_assets_class3
        int assets_with_gap_count
        text gap_details
    }

    IMM_Competency_Alert_Log {
        string name PK
        link competency FK
        date alert_date
        string milestone
        string alert_level
        string sent_to
    }

    AC_Asset {
        string name PK
        link device_model
        string asset_class
        link location
        int custom_operator_coverage_count
        string custom_operator_coverage_status
    }

    IMM_Audit_Trail {
        string name PK
        string doctype_ref
        string record_name
        string action
        datetime timestamp
        link actor
        text metadata
    }

    IMM_Training_Program ||--o{ IMM_Training_Session : "1 program → many sessions"
    IMM_Training_Session ||--|{ IMM_Training_Participant : "1 session → N participants (child)"
    IMM_Training_Participant }o--|| IMM_User_Competency : "Pass participant → 1 competency"
    IMM_Training_Program ||--o{ IMM_User_Competency : "program linked"
    IMM_Training_Session ||--o{ IMM_User_Competency : "session linked"
    IMM_User_Competency ||--o{ IMM_Competency_Alert_Log : "1 competency → many alert logs"
    AC_Asset }o--|| IMM_User_Competency : "device_model → competency coverage"
    IMM_User_Competency ||--o| IMM_Audit_Trail : "changes → audit trail"
```

### Cross-module links (external entities)

| Entity | Relationship | Note |
|---|---|---|
| `AC Asset` | `device_model` → `IMM User Competency.device_model` | Coverage check, IMM-04 gate |
| `IMM Audit Trail` | All Competency status changes → Audit Trail log | Cross-cutting, reuse |
| `Asset Document` (IMM-05) | `IMM User Competency.certificate_file` → Asset Document | `doc_category=Training` |
| `CAPA` | `IMM User Competency.revoke_capa_ref` → CAPA | BR-06-06 |
| Frappe `User` | `user`, `instructor`, `supervisor_signoff`, `revoked_by` | Source of truth cho người dùng |

---

## §II Class Diagram

```mermaid
classDiagram
    class IMMUserCompetency {
        +validate()
        +before_save()
        +on_update()
        +on_trash()
        +vr_01_expiry_after_achieved()
        +vr_07_signoff_required_active()
        +vr_12_competency_level_match_type()
        +set_computed_fields()
    }

    class IMMTrainingSession {
        +validate()
        +before_save()
        +on_update()
        +vr_04_instructor_qualified()
        +vr_05_min_participants_for_confirm()
        +vr_06_scores_required_complete()
        +vr_10_session_date_not_past()
        +compute_overall_results()
        +notify_supervisors_for_signoff()
    }

    class IMMTrainingProgram {
        +validate()
        +on_update()
        +vr_02_passing_score_range()
        +vr_03_validity_range()
        +vr_11_target_device_model_active()
        +flag_recertification_needed()
    }

    class IMM06Service {
        +create_competency_from_session(session_name: str) list
        +signoff_competency(competency_name: str, supervisor_user: str) dict
        +archive_old_competency(user: str, device_model: str, exclude: str) int
        +compute_operator_coverage(asset: str) dict
        +validate_user_authorization(user: str, device_model: str) dict
        +trigger_recertification(competency_name: str) str
        +generate_gap_report(scope: str) str
        +invalidate_authorization_cache(user: str, device_model: str)
        +handle_user_dept_change(doc, method)
    }

    IMMTrainingSession --> IMM06Service : "on_update(Completed) → create_competency_from_session()"
    IMMUserCompetency --> IMM06Service : "on_update(Active) → archive_old_competency() + invalidate_cache()"
    IMMTrainingProgram --> IMM06Service : "on_update(critical fields) → flag_recertification_needed()"
    IMM06Service ..> IMMUserCompetency : "creates Competency records"
    IMM06Service ..> IMMTrainingSession : "trigger_recertification() creates Session"
```

### Notes

- `IMMUserCompetency.on_trash()` → `frappe.throw()` (BR-06-09: không xóa cứng)
- `IMM06Service.validate_user_authorization()` — cached 5 min TTL qua `frappe.cache`
- `IMM06Service.compute_operator_coverage()` — returns `{asset, device_model, department, operator_count, required_min, gate_pass}`

---

## §III Sequence Diagrams

### SD-1: Complete Session → Auto-create Competency

```mermaid
sequenceDiagram
    participant Instructor
    participant API as API Layer (imm06.py)
    participant Service as IMM06Service
    participant DB as Frappe ORM
    participant Competency as IMM User Competency
    participant Supervisor

    Instructor->>API: POST complete_session(name, participants_results)
    API->>API: validate role IN {Tổ HC-QLCL, Biomed Engineer, CMMS Admin}
    API->>DB: get_doc("IMM Training Session", name)
    DB-->>API: session doc
    API->>API: validate VR-06 (scores reqd nếu assessment_method=Both)
    API->>API: compute overall_result per participant (Pass/Fail/Conditional)
    API->>DB: update session.workflow_state = "Completed"
    API->>Service: create_competency_from_session(session_name)
    Service->>DB: get Pass participants
    loop for each Pass participant
        Service->>DB: insert IMM User Competency
        Note over DB: status=Pending Assessment<br/>achieved_date=session_date<br/>expiry_date=achieved+validity_months<br/>recert_due=expiry-60d
        DB-->>Competency: COMP-YYYY-#####
    end
    Service-->>API: [competency_name_list]
    API->>Supervisor: send_email("Pending sign-off") for each competency
    API-->>Instructor: {"success": true, "data": {new_state, participants_summary, competencies_created}}
```

### SD-2: Supervisor Sign-off Competency

```mermaid
sequenceDiagram
    participant Supervisor
    participant API as API Layer (imm06.py)
    participant Service as IMM06Service
    participant DB as Frappe ORM
    participant User as Competency Owner

    Supervisor->>API: POST signoff_competency(name)
    API->>API: validate role IN _SIGNOFF_ROLES
    API->>DB: get_doc("IMM User Competency", name)
    DB-->>API: competency doc
    API->>API: validate workflow_state = "Pending Assessment"
    API->>API: validate VR-07 (supervisor_signoff reqd)
    API->>API: validate scope (Department Manager → own dept only)
    API->>DB: set supervisor_signoff, signoff_date
    API->>DB: compute expiry_date = achieved_date + validity_months
    API->>DB: compute recertification_due_date = expiry_date - 60d
    API->>DB: workflow_state = "Active"
    API->>Service: archive_old_competency(user, device_model, exclude=name)
    Service->>DB: set old competency status = "Suspended"
    API->>Service: invalidate_authorization_cache(user, device_model)
    API->>User: send_email("Bạn đã được cấp năng lực vận hành ...")
    API-->>Supervisor: {"success": true, "data": {name, new_state: "Active", expiry_date, recertification_due_date}}
```

### SD-3: Authorization Gate (IMM-08/09/12 hook)

```mermaid
sequenceDiagram
    participant WO as Work Order Controller (IMM-08/09/12)
    participant Service as IMM06Service
    participant Cache as frappe.cache (5 min TTL)
    participant DB as MariaDB

    WO->>Service: validate_user_authorization(user, device_model)
    Service->>Cache: get_value("imm06:auth:{user}:{device_model}")
    alt Cache HIT
        Cache-->>Service: cached_result
        Service-->>WO: {authorized, status, expiry_date, ...}
    else Cache MISS
        Service->>DB: SELECT * FROM tabIMM User Competency<br/>WHERE user=%s AND device_model=%s AND workflow_state='Active'<br/>ORDER BY expiry_date DESC LIMIT 1
        DB-->>Service: competency row (or empty)
        alt competency found AND status=Active
            Service->>Cache: set_value(key, result, expires=300)
            Service-->>WO: {authorized: true, competency, status, expiry_date}
        else no Active competency
            Service->>Cache: set_value(key, result, expires=300)
            Service-->>WO: {authorized: false, reason: "Người dùng chưa có Active competency..."}
        end
    end
    alt authorized = false
        WO->>WO: frappe.throw("BR-06-01: Kỹ thuật viên chưa có năng lực ...")
    end
```

---

## §IV Communication Diagram — Cross-module Dependencies

```
IMM-06 User Training & Competency Management
├── OUT → IMM-04 Installation (Clinical Release gate)
│         Caller: asset_commissioning.py validate()
│         Call: services.imm06.compute_operator_coverage(asset)
│         Gate: operator_count >= required_min (2 cho Class III)
│         Block: frappe.throw nếu gate_pass = false
│
├── IN ← IMM-05 Document Repository
│         IMM-06 lưu certificate PDF:
│         Asset Document {doc_category=Training, is_model_level=1}
│         Link: IMM User Competency.certificate_file → Asset Document
│
├── OUT → IMM-08 PM / IMM-09 Repair / IMM-11 Calibration / IMM-12 Corrective
│         Caller: work_order.py validate_assignee()
│         Call: services.imm06.validate_user_authorization(user, device_model)
│         Block: frappe.throw("BR-06-01: ...") nếu authorized = false
│         Note: cross-module import (không qua HTTP để tránh overhead)
│
├── IN ← IMM-10 Compliance / Incident (Wave 3)
│         CAPA action item type="revoke_competency" → auto-call revoke_competency API
│         services/imm10.py → services/imm06.py (Wave 3 integration)
│
├── OUT → IMM-16 Compliance Dashboard
│         Cung cấp: training_compliance_pct, coverage_class3_pct
│         API: get_dashboard_stats, get_competency_gaps_by_dept
│
└── OUT → IMM Audit Trail (cross-cutting)
          Mọi revoke/suspend/sign-off → log_audit_trail(doc, action, metadata)
          Actor traceability đầy đủ
```

---

## §V Package Diagram — File Layout

```
assetcore/
├── assetcore/
│   └── doctype/
│       ├── imm_training_program/
│       │   ├── imm_training_program.json       ⚠️ Pending
│       │   └── imm_training_program.py         ⚠️ Pending  (IMMTrainingProgram controller)
│       ├── imm_training_session/
│       │   ├── imm_training_session.json       ⚠️ Pending
│       │   └── imm_training_session.py         ⚠️ Pending  (IMMTrainingSession controller)
│       ├── imm_training_participant/
│       │   ├── imm_training_participant.json   ⚠️ Pending  (child table)
│       │   └── imm_training_participant.py     ⚠️ Pending
│       ├── imm_user_competency/
│       │   ├── imm_user_competency.json        ⚠️ Pending
│       │   ├── imm_user_competency.py          ⚠️ Pending  (IMMUserCompetency controller)
│       │   └── test_imm_user_competency.py     ⚠️ Pending
│       ├── imm_competency_gap_report/
│       │   ├── imm_competency_gap_report.json  ⚠️ Pending
│       │   └── imm_competency_gap_report.py    ⚠️ Pending
│       └── imm_competency_alert_log/
│           └── imm_competency_alert_log.json   ⚠️ Pending  (idempotent log)
│
├── workflow/
│   ├── imm_06_session_workflow.json            ⚠️ Pending  (7 states)
│   └── imm_06_competency_workflow.json         ⚠️ Pending  (6 states)
│
├── services/
│   ├── imm06.py                                ⚠️ Pending  (IMM06Service — 7 functions)
│   └── test_imm06.py                           ⚠️ Pending
│
├── api/
│   └── imm06.py                                ⚠️ Pending  (19 @frappe.whitelist endpoints)
│
├── tasks.py                                    ⚠️ Pending  (4 scheduler jobs thêm mới)
│
└── frontend/src/
    ├── views/imm06/
    │   ├── CompetencyDashboard.vue             ⚠️ Pending
    │   ├── ProgramListView.vue                 ⚠️ Pending
    │   ├── ProgramDetailView.vue               ⚠️ Pending
    │   ├── SessionCreateView.vue               ⚠️ Pending
    │   ├── SessionDetailView.vue               ⚠️ Pending
    │   ├── SessionRunView.vue                  ⚠️ Pending
    │   ├── CompetencyListView.vue              ⚠️ Pending
    │   ├── CompetencyDetailView.vue            ⚠️ Pending
    │   ├── MyCompetenciesView.vue              ⚠️ Pending
    │   └── GapReportView.vue                   ⚠️ Pending
    ├── components/imm06/
    │   ├── RevokeCompetencyModal.vue           ⚠️ Pending
    │   └── SignoffModal.vue                    ⚠️ Pending
    ├── stores/
    │   └── imm06Store.ts                       ⚠️ Pending
    └── types/
        └── imm06.ts                            ⚠️ Pending
```
