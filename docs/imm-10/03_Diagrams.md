# IMM-10 — Diagrams

| Mục | Giá trị |
|---|---|
| Module | IMM-10 — Hậu kiểm và tuân thủ |
| Đợt | 3 |
| Trạng thái | In Progress (BE chưa scaffold — ERD/Class ở mức conceptual) |
| Cập nhật | 2026-05-10 |

> Diagram trong file này là **conceptual** dựa trên §I–§IV của `02_Analysis_Design.md`. Chi tiết entity/field sẽ được lock khi BE scaffold Sprint Wave 3.

---

## Hình 1 — Use Case Overview

```mermaid
graph LR
  U1[Compliance Officer]
  U2[Workshop Lead]
  U3[Phap che]
  U4[Truong khoa]
  U5[BGD]
  U6[Vendor]
  S1[Scheduler]
  S2[IMM-16 Engine]

  U1 --> UC01[UC-10-01 Open Case Vendor]
  U1 --> UC02[UC-10-02 Open Case FSCA]
  U1 --> UC03[UC-10-03 Open Case PMS]
  S2 --> UC03
  U1 --> UC04[UC-10-04 Auto Scope]
  U3 --> UC05[UC-10-05 Disclosure 48h]
  U1 --> UC06[UC-10-06 Bulk Recall WO]
  U2 --> UC06
  U4 --> UC07[UC-10-07 Stand-down]
  U1 --> UC08[UC-10-08 Close Case]
  U5 --> UC08
  U1 --> UC09[UC-10-09 CAPA Tracker]
  S1 --> UC10[UC-10-10 Effectiveness Check]
  U1 --> UC10
  U1 --> UC11[UC-10-11 Mgmt Review feed]
  U1 --> UC12[UC-10-12 Dashboard]
  U5 --> UC12
  U6 -.->|cung cap lot list| UC04
```

*Hình 1 — Use Case overview module IMM-10.*

---

## Hình 2 — ERD (conceptual)

```mermaid
erDiagram
  IMM_COMPLIANCE_CASE ||--o{ IMM_AFFECTED_ASSET : "scope"
  IMM_COMPLIANCE_CASE ||--o{ IMM_DISCLOSURE_LOG : "regulatory comm"
  IMM_COMPLIANCE_CASE ||--o{ IMM_CAPA_RECORD : "preventive CAPA"
  IMM_COMPLIANCE_CASE ||--o{ IMM_EFFECTIVENESS_CHECK : "30/60/90"
  IMM_AFFECTED_ASSET }o--|| AC_ASSET : "ref"
  IMM_AFFECTED_ASSET }o--o| WORK_ORDER : "recall WO"
  IMM_COMPLIANCE_CASE }o--|| AC_SUPPLIER : "vendor"
  IMM_COMPLIANCE_CASE }o--o| IMM_DEVICE_MODEL : "model scope"
  IMM_COMPLIANCE_CASE ||--o{ IMM_AUDIT_TRAIL : "hash chain"

  IMM_COMPLIANCE_CASE {
    string case_no PK
    string case_type
    string severity
    datetime recall_confirmed_at
    datetime disclosure_due_at
    string source_ref
    string workflow_state
  }
  IMM_AFFECTED_ASSET {
    string parent FK
    string asset FK
    bool historical
    string action_required
    string status
  }
  IMM_DISCLOSURE_LOG {
    string parent FK
    datetime sent_at
    string regulator
    string doc_no
  }
  IMM_EFFECTIVENESS_CHECK {
    string parent FK
    int day_offset
    string result
    datetime checked_at
  }
```

*Hình 2 — ERD conceptual. Field detail sẽ lock trong `04_Backend_Design.md` khi scaffold.*

> **Reuse**: `AC Asset`, `IMM Device Model`, `AC Supplier`, `IMM CAPA Record`, `IMM Audit Trail`, `Work Order` (PM hoặc Asset Repair) đã có trong codebase Wave 1/2. IMM-10 KHÔNG tạo mới các entity này.

---

## Hình 3 — Class Diagram (Service tầng)

```mermaid
classDiagram
  class ComplianceCaseService {
    +open_case(payload) Case
    +find_scope(case) AffectedAssets
    +start_disclosure_timer(case)
    +bulk_create_recall_wo(case)
    +close_case(case)
  }
  class DisclosureService {
    +send_to_regulator(case, template)
    +log_disclosure(case, log)
    +check_breach() List~Case~
  }
  class CAPATrackerService {
    +list_open_capa(filters)
    +schedule_effectiveness_check(case)
    +mark_effectiveness(check, result)
  }
  class ScopeFinder {
    +query_by_model(model) List~Asset~
    +query_by_lot(lot_range) List~Asset~
    +query_by_serial(serial_range) List~Asset~
    +reconcile_with_transfer_history()
  }
  class ComplianceCaseRepo {
    +get(name) Case
    +list(filters) List~Case~
    +save(case)
  }

  ComplianceCaseService --> ComplianceCaseRepo
  ComplianceCaseService --> ScopeFinder
  ComplianceCaseService --> DisclosureService
  CAPATrackerService --> ComplianceCaseRepo
```

*Hình 3 — Class diagram tầng service (3-tier theo CONVENTIONS §2). API layer wrap các method này.*

---

## Hình 4 — Sequence: Open Case + Auto Scope (UC-10-01 + UC-10-04)

```mermaid
sequenceDiagram
  actor U1 as Compliance Officer
  participant API as api/imm10.py
  participant SVC as services/imm10.py
  participant SF as ScopeFinder
  participant DB as Frappe DB
  participant AT as IMM Audit Trail

  U1->>API: POST open_case(vendor_notice, model, lot_range)
  API->>SVC: open_case(payload)
  SVC->>DB: insert IMM Compliance Case (Draft)
  SVC->>AT: log_audit_event("case.opened")
  SVC-->>API: case_no
  API-->>U1: {success:true, data:{case_no}}

  U1->>API: POST find_scope(case_no)
  API->>SVC: find_scope(case)
  SVC->>SF: query_by_model + query_by_lot
  SF->>DB: SELECT AC Asset WHERE model=? AND lot in ?
  DB-->>SF: assets[]
  SF->>SF: reconcile_with_transfer_history
  SF-->>SVC: scope_list
  SVC->>DB: insert IMM Affected Asset rows (child)
  SVC->>AT: log_audit_event("case.scope_found", count=N)
  SVC-->>API: {n_assets, sample:[...]}
  API-->>U1: {success:true, data}
```

*Hình 4 — Open + scope flow.*

---

## Hình 5 — Sequence: Disclosure 48h Timer (UC-10-05 + BR-10-05)

```mermaid
sequenceDiagram
  participant SCH as Scheduler (daily/hourly)
  participant SVC as services/imm10.py
  participant DB as Frappe DB
  participant NOTIF as Notification
  participant IMM16 as IMM-16 Engine

  SCH->>SVC: check_disclosure_breach()
  SVC->>DB: SELECT cases WHERE disclosure_due_at < now() AND disclosure_sent=false
  DB-->>SVC: breach_list
  loop each case
    SVC->>NOTIF: alert BGD + Phap che
    SVC->>IMM16: create_finding(rule="DISCLOSURE_BREACH", case_ref)
    SVC->>DB: update case (escalated=true)
  end
```

*Hình 5 — Disclosure breach detection và escalation sang IMM-16.*

---

## Hình 6 — Communication Diagram (Cross-module)

```mermaid
graph LR
  IMM10[IMM-10 Compliance Case]
  IMM16[IMM-16 Compliance Engine]
  IMM12[IMM-12 Incident/RCA/CAPA]
  IMM09[IMM-09 Repair WO]
  IMM08[IMM-08 PM WO]
  IMM11[IMM-11 Calibration]
  IMM04[IMM-04 Asset Master]
  IMM13[IMM-13 Transfer]

  IMM12 -->|chronic failure signal| IMM10
  IMM11 -->|cal fail signal| IMM10
  IMM09 -->|repair history| IMM10
  IMM10 -->|bulk recall WO| IMM08
  IMM10 -->|bulk recall WO| IMM09
  IMM10 -->|finding when breach| IMM16
  IMM10 -->|mgmt review entry| IMM16
  IMM16 -->|compliance rule subscribe| IMM10
  IMM04 -->|asset master| IMM10
  IMM13 -->|transfer history| IMM10
```

*Hình 6 — Trao đổi xuyên module. IMM-10 vừa là consumer (signal in) vừa là producer (recall WO out).*

---

## Hình 7 — State Machine: Compliance Case

```mermaid
stateDiagram-v2
  [*] --> Draft
  Draft --> Scope_Identification: confirm trigger
  Scope_Identification --> Disclosure_Pending: scope locked + regulatory
  Scope_Identification --> Action_Pending: scope locked + non-regulatory
  Disclosure_Pending --> Action_Pending: disclosure sent
  Disclosure_Pending --> Escalated: 48h breach
  Escalated --> Action_Pending: BGD intervene
  Action_Pending --> Verifying: 100% WO closed
  Verifying --> Closed: BGD approve close
  Verifying --> Action_Pending: re-open if defect
  Closed --> Effectiveness_Check: scheduler auto
  Effectiveness_Check --> [*]: pass 30/60/90
  Effectiveness_Check --> Action_Pending: fail check
```

*Hình 7 — State machine. Workflow JSON sẽ scaffold tại `04_Backend_Design.md` §III khi BE ready.*

---

## Hình 8 — Package Diagram

```mermaid
graph TD
  subgraph BE
    A[assetcore/api/imm10.py]
    S[assetcore/services/imm10.py]
    R[assetcore/repositories/compliance_case_repo.py]
    D[doctype/imm_compliance_case/]
    W[workflow/imm_10_compliance_workflow.json]
    F[fixtures/imm10_*.json]
  end
  subgraph FE
    V[frontend/src/views/Compliance*.vue]
    PS[frontend/src/stores/imm10.ts]
    T[frontend/src/types/imm10.ts]
  end
  subgraph Shared
    L[utils/lifecycle.py]
    C[services/shared/constants.py]
  end

  A --> S
  S --> R
  S --> L
  R --> D
  V --> PS
  PS --> A
  T -.-> A
  S -.-> C
```

*Hình 8 — Package layout dự kiến (mirror IMM-09/IMM-12).*

---

*Cập nhật: 2026-05-10. Diagram conceptual — chi tiết khoá khi BE scaffold.*
