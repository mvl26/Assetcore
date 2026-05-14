# 03 — Diagrams (IMM-13)

| Mục | Giá trị |
|---|---|
| Module | IMM-13 — Ngừng sử dụng và điều chuyển |
| Trạng thái | Skeleton — entity / class chốt sau Sprint Wave 3 (BE scaffold) |
| Liên kết | [02 Analysis](./02_Analysis_Design.md) · [04 Backend](./04_Backend_Design.md) |

> File này tổng hợp các diagram **đúc kết** từ 02 (BA) + 04 (BE). Để tránh lệch ground truth, không tạo entity/class chưa được liệt kê ở 04.

---

## I. ERD — Entity Relationship

```mermaid
erDiagram
    AC_ASSET ||--o{ IMM_ASSET_REASSIGNMENT : "is subject of"
    AC_ASSET ||--o{ IMM_REPLACEMENT_REVIEW : "is subject of"
    IMM_REPLACEMENT_REVIEW ||--|| IMM_RESIDUAL_RISK : "requires"
    IMM_RESIDUAL_RISK ||--o{ IMM_RESIDUAL_RISK_ITEM : "contains"
    IMM_ASSET_REASSIGNMENT }o--|| LOCATION : "from_location"
    IMM_ASSET_REASSIGNMENT }o--|| LOCATION : "to_location"
    IMM_ASSET_REASSIGNMENT ||--o{ LIFECYCLE_EVENT : "emits"
    IMM_REPLACEMENT_REVIEW ||--o{ LIFECYCLE_EVENT : "emits retire_proposed"
    AC_ASSET ||--o{ LIFECYCLE_EVENT : "tracked by"
    USER ||--o{ E_SIGNATURE : "signs"
    IMM_ASSET_REASSIGNMENT ||--o{ E_SIGNATURE : "has"
    IMM_RESIDUAL_RISK ||--o{ E_SIGNATURE : "has"

```

**Hình 1.1 — ERD IMM-13** (entity-level skeleton — *field detail chốt trong Sprint Wave 3 sau khi BE scaffold; xem [04 §I](./04_Backend_Design.md#i-doctype-skeleton)*).

Quan hệ chính:
- 1 Asset → N Reassignment, N Replacement Review (N qua thời gian, không cùng lúc).
- 1 Replacement Review ↔ 1 Residual Risk (1-1 mandatory trước khi approve retire).
- Reassignment + Residual Risk đều có chuỗi e-signature (≥ 1 → N).
- Mọi thay đổi state Asset đi qua Lifecycle Event (xem [04 §IV hooks](./04_Backend_Design.md#iv-hooks)).

---

## II. Class Diagram (service layer)

```mermaid
classDiagram
    class IMM13Service {
        +stand_down(asset, reason, evidence, actor) str
        +request_reassignment(asset, target_location, reason) str
        +confirm_reassignment(reassignment, role)
        +commit_reassignment(reassignment)
        +create_replacement_review(asset) str
        +submit_residual_risk(review, items, signature)
        +approve_retire(review, signature) str
        +escalate_stale_oos(now)
        +verify_location_consistency()
    }
    class AssetReassignmentRepo {
        +find_by_asset(asset)
        +find_pending_dept_confirm(facility)
        +update_state(name, new_state)
    }
    class ReplacementReviewRepo {
        +find_for_asset(asset)
        +submit(name, payload)
    }
    class ResidualRiskRepo {
        +attach_items(review, items)
        +verify_signature_chain(review)
    }
    class LifecycleEventService {
        +create(asset, type, payload, actor)
    }
    class AuditService {
        +log_audit_event(doctype, name, action, actor, hash)
    }
    class AssetRegistry {
        +get_asset(name)
        +set_location(name, location)
        +set_lifecycle_state(name, state)
    }

    IMM13Service --> AssetReassignmentRepo
    IMM13Service --> ReplacementReviewRepo
    IMM13Service --> ResidualRiskRepo
    IMM13Service --> LifecycleEventService
    IMM13Service --> AuditService
    IMM13Service --> AssetRegistry
```

**Hình 2.1 — Class diagram service layer** — strict 3-tier theo `CONVENTIONS.md §2`.

---

## III. Sequence Diagrams

### SEQ-01 — Stand-down (UC-01)

```mermaid
sequenceDiagram
    actor KTV
    actor Dept as Trưởng khoa
    actor PTP as PTP Khối 2
    participant API as api/imm13
    participant SVC as services/imm13
    participant Repo as AssetReassignmentRepo
    participant LE as LifecycleEventService
    participant Audit as AuditService
    participant Asset as AssetRegistry

    KTV->>API: POST create_stand_down_request(asset, reason)
    API->>SVC: stand_down(...)
    SVC->>Asset: get_asset(asset)
    Asset-->>SVC: Asset(state=Active)
    SVC->>Repo: insert(state=PendingDeptConfirm)
    SVC->>Audit: log_audit_event(...)
    SVC-->>API: name
    API-->>KTV: {name, state}

    Dept->>API: POST confirm_reassignment(name, role=source)
    API->>SVC: confirm_reassignment(...)
    SVC->>Repo: update_state(PendingApproval)
    SVC->>Audit: log

    PTP->>API: POST approve_reassignment(name, signature)
    API->>SVC: approve + commit_reassignment(...)
    SVC->>Asset: set_lifecycle_state(asset, "Out of Service")
    SVC->>LE: create(asset, "stand_down", ...)
    SVC->>Audit: log + hash
    SVC->>Repo: update_state(Approved)
    SVC-->>API: ok
```

**Hình 3.1 — Stand-down sequence**.

### SEQ-02 — Reassign nội viện (UC-02)

```mermaid
sequenceDiagram
    actor KTV
    actor DeptSrc as Trưởng khoa nguồn
    actor DeptDst as Trưởng khoa đích
    actor PTP
    participant API as api/imm13
    participant SVC as services/imm13
    participant Asset
    participant LE
    participant IMM04 as IMM-04 service

    KTV->>API: POST create_reassignment
    API->>SVC: request_reassignment
    SVC->>SVC: cascade validate Khoa→Phòng→Vị trí
    SVC->>SVC: check competency (IMM-06)
    SVC-->>API: {name, needs_recommissioning}
    DeptSrc->>API: confirm_reassignment(role=source)
    DeptDst->>API: confirm_reassignment(role=target)
    PTP->>API: approve_reassignment(signature)
    API->>SVC: commit_reassignment
    SVC->>Asset: set_location atomic
    SVC->>LE: create(asset, "reassigned")
    alt needs_recommissioning
        SVC->>IMM04: trigger_lite_recommissioning(asset)
    end
    SVC-->>API: ok
```

**Hình 3.2 — Reassign sequence**.

### SEQ-03 — Retire approval + hand-off IMM-14 (UC-05/06)

```mermaid
sequenceDiagram
    actor KTV
    actor TCKT
    actor QA as QMS Officer
    actor PTP
    participant API as api/imm13
    participant SVC as services/imm13
    participant LE
    participant IMM14 as IMM-14 listener

    KTV->>API: create_replacement_review(asset)
    TCKT->>API: fill_replacement_cost
    QA->>API: submit_residual_risk(items, signature)
    PTP->>API: approve_retire_proposal(signature)
    API->>SVC: approve_retire
    SVC->>SVC: gate check (review + risk signed?)
    SVC->>LE: emit retire_proposed
    LE->>IMM14: notify (event channel)
    alt IMM14 ack
        IMM14-->>SVC: ack
        SVC-->>API: {state=Approved, imm14_handoff_id}
    else IMM14 fail
        SVC->>SVC: enqueue retry (cron hourly, max 3)
        SVC-->>API: {state=Approved (pending IMM14)}
    end
```

**Hình 3.3 — Retire hand-off sequence**.

---

## IV. State diagram (consolidated)

(Đã có ở [02 §IV.3](./02_Analysis_Design.md#iv3-state-machine) cho `IMM Asset Reassignment`. Cho `IMM Replacement Review` và `IMM Residual Risk` xem [04 §III](./04_Backend_Design.md#iii-workflow).)

`AC Asset Lifecycle` KHÔNG vẽ lại ở đây — đã có canonical version trong [`Workflow_Specification.md`](../ba/Phase_04_Process_Workflow_Design/01_Workflow_Specification/Workflow_Specification.md) §1 (8 states · 16 transitions). IMM-13 chỉ *invoke* transition `Đưa ra khỏi sử dụng` và transition cập nhật location.

---

## V. Package / Component diagram

```mermaid
flowchart LR
    subgraph FE["Frontend (Vue 3)"]
        F1[ReassignmentList/Create/Detail]
        F2[ReplacementReview]
        F3[ResidualRiskForm]
        F4[Dashboard]
        F5[api/imm13.ts]
    end
    subgraph BE["Backend (Frappe)"]
        B1[api/imm13.py]
        B2[services/imm13.py]
        B3[repositories/*_repo.py]
        B4[events/imm13.py]
        B5[doctype/IMM_Asset_Reassignment]
        B6[doctype/IMM_Replacement_Review]
        B7[doctype/IMM_Residual_Risk]
    end
    subgraph SHARED["Shared"]
        S1[Lifecycle Event]
        S2[Audit Trail]
        S3[AC Asset]
    end
    subgraph EXT["Other modules"]
        E1[IMM-09 Repair]
        E2[IMM-11 Calibration]
        E3[IMM-04 Re-commissioning]
        E4[IMM-14 Decommission]
        E5[IMM-06 Training/Competency]
    end

    F1 --> F5
    F2 --> F5
    F3 --> F5
    F4 --> F5
    F5 -->|HTTPS| B1
    B1 --> B2
    B2 --> B3
    B3 --> B5
    B3 --> B6
    B3 --> B7
    B2 --> S1
    B2 --> S2
    B2 --> S3
    E1 -.event.-> B4
    E2 -.event.-> B4
    B2 -.trigger.-> E3
    B2 -.event.-> E4
    B2 -.read.-> E5
```

**Hình 5.1 — Package diagram IMM-13 + ngữ cảnh module**.

---

*Tất cả diagram là design intent; sau Sprint Wave 3 sẽ verify lại entity/field thực tế và regenerate.*
