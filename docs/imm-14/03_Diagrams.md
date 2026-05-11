# 03 — Diagrams (IMM-14 Giải nhiệm thiết bị)

| Mục | Giá trị |
|---|---|
| Module | IMM-14 — Giải nhiệm thiết bị |
| Phạm vi | ERD + Class + Sequence + State |
| Owner | System Analyst + BE Architect |
| Liên kết | [02 Analysis](./02_Analysis_Design.md) · [04 Backend](./04_Backend_Design.md) |

> Diagram dạng overview cho module from-scratch. Chi tiết field DocType và service shape sẽ chốt khi BE scaffold (Đợt 3) — xem [04 Backend Design](./04_Backend_Design.md).

---

## 1. ERD — Entity quan hệ chính

```mermaid
erDiagram
    AC_Asset ||--o| IMM_Asset_Closure : "đóng vòng đời 1-1"
    IMM_Asset_Closure }o--|| IMM_Decommission_Decision : "input từ IMM-13"
    IMM_Asset_Closure ||--o{ IMM_Reconciliation_Line : "đối soát kho/kế toán"
    IMM_Asset_Closure ||--o{ IMM_Sanitization_Item : "checklist sanitization"
    IMM_Asset_Closure ||--o{ IMM_Closure_Document : "biên bản · hồ sơ"
    IMM_Asset_Closure ||--o{ Asset_Lifecycle_Event : "phát sinh event"
    IMM_Asset_Closure }o--o{ IMM_Document : "archive hồ sơ IMM-05"
    AC_Asset ||--o{ IMM_Spare_Part_Stock : "phụ tùng tồn IMM-15"
    IMM_Reconciliation_Line }o--|| IMM_Spare_Part_Stock : "ref dòng kho"

    AC_Asset {
        string asset_no PK
        string asset_status
        boolean has_patient_data
        decimal book_value
    }
    IMM_Asset_Closure {
        string closure_no PK
        string asset FK
        string decommission_decision FK
        string disposal_method
        decimal final_value
        date sanitization_date
        date approved_date
        string workflow_state
    }
    IMM_Reconciliation_Line {
        string parent FK
        string scope
        string ref_doctype
        string ref_name
        decimal qty_or_amount
        string status
    }
    IMM_Sanitization_Item {
        string parent FK
        string item
        boolean checked
        string signed_by
    }
```

*Hình 1.1 — ERD chính của IMM-14. Quan hệ `}o--o{` với `IMM Document` thể hiện archive cross-module.*

---

## 2. Class diagram — Service layer (3-tier)

```mermaid
classDiagram
    class ClosureAPI {
        +create_closure(asset)
        +update_reconciliation(closure, lines)
        +sign_sanitization(closure)
        +finalize(closure)
        +rollback(closure, reason)
    }
    class ClosureService {
        +create_from_decision(decision)
        +validate_finalize(closure)
        +run_finalize_transaction(closure)
        +run_rollback(closure, reason)
    }
    class ReconciliationService {
        +load_open_wo(asset)
        +load_spare_stock(asset)
        +load_book_value(asset)
        +mark_line_done(line)
    }
    class SanitizationService {
        +load_template(asset)
        +sign(closure, dpo)
    }
    class ClosureRepo {
        +get_active(asset)
        +create(payload)
        +update_state(closure, state)
    }
    class AssetRepo {
        +set_status(asset, status)
        +lock_asset(asset)
    }
    class DocumentRepo {
        +archive_for_asset(asset)
        +unarchive_for_asset(asset)
    }
    ClosureAPI --> ClosureService
    ClosureService --> ReconciliationService
    ClosureService --> SanitizationService
    ClosureService --> ClosureRepo
    ClosureService --> AssetRepo
    ClosureService --> DocumentRepo
```

*Hình 2.1 — Class diagram tuân thủ kiến trúc 3-tier (`assetcore-be-module`): API → Service → Repository. ReconciliationService và SanitizationService là sub-service tách theo bounded context.*

---

## 3. Sequence — UC-14-07 Phê duyệt closure cuối

```mermaid
sequenceDiagram
    actor TPP as Trưởng phòng
    participant FE as Vue FE
    participant API as imm14 API
    participant Svc as ClosureService
    participant Recon as ReconciliationService
    participant Sant as SanitizationService
    participant ARepo as AssetRepo
    participant DRepo as DocumentRepo
    participant Audit as IMM Audit Trail

    TPP->>FE: Click Approve
    FE->>API: POST /finalize {closure_no}
    API->>Svc: validate_finalize(closure)
    Svc->>Recon: check_all_lines_done
    Svc->>Sant: check_sanitization_signed
    Svc->>Svc: BR-14-01 (7 mục) + BR-14-02 (SoD)
    alt validate fail
        Svc-->>API: error code IMM14_INCOMPLETE
        API-->>FE: {success:false, error}
    else validate pass
        Svc->>Svc: begin transaction
        Svc->>ARepo: set_status(asset, 'decommissioned')
        Svc->>DRepo: archive_for_asset(asset)
        Svc->>Svc: emit Asset Lifecycle Event 'decommissioned'
        Svc->>Audit: log finalize
        Svc->>Svc: commit + emit hook imm14_asset_closed
        Svc-->>API: ok
        API-->>FE: {success:true, data}
    end
```

*Hình 3.1 — Sequence finalize closure. Toàn bộ thao tác trong một transaction; nếu archive hồ sơ IMM-05 fail → rollback (NFR Reliability).*

---

## 4. Sequence — UC-14-08 Rollback closure

```mermaid
sequenceDiagram
    actor TPP as Trưởng phòng
    actor KTC as Kế toán
    participant API as imm14 API
    participant Svc as ClosureService
    participant ARepo as AssetRepo
    participant DRepo as DocumentRepo

    TPP->>API: POST /rollback {closure_no, reason}
    API->>Svc: validate_rollback_window
    alt out of window
        Svc-->>API: error IMM14_ROLLBACK_EXPIRED
    else in window
        Svc->>Svc: state Closed→Rollback Requested
        Svc-->>KTC: notify
        KTC->>API: POST /rollback/confirm
        API->>Svc: run_rollback
        Svc->>ARepo: set_status(asset, 'pending_decommission')
        Svc->>DRepo: unarchive_for_asset(asset)
        Svc->>Svc: state Rollback Requested→Reopened
        Svc->>Svc: emit lifecycle event 'closure_rolled_back'
    end
```

*Hình 4.1 — Rollback cần 2 bước (TPP yêu cầu, KH-TC xác nhận) — implement BR-14-04.*

---

## 5. State diagram — IMM Asset Closure

```mermaid
stateDiagram-v2
    [*] --> Draft
    Draft --> Reconciling: lines created
    Reconciling --> Pending_Approval: all lines done + sanitization signed
    Pending_Approval --> Closed: TPP approve
    Pending_Approval --> Reconciling: send back
    Closed --> Rollback_Requested: TPP request (in window)
    Rollback_Requested --> Reopened: KH-TC confirm
    Rollback_Requested --> Closed: KH-TC reject
    Reopened --> Reconciling: tiếp tục chỉnh
    Closed --> [*]
```

*Hình 5.1 — State machine. Mapping docstatus chi tiết xem [04 §III](./04_Backend_Design.md).*

---

## 6. State diagram — Asset (góc nhìn IMM-14)

```mermaid
stateDiagram-v2
    pending_decommission --> decommissioned: closure approved
    decommissioned --> pending_decommission: closure rolled back
    decommissioned --> [*]: keep view-only forever
```

*Hình 6.1 — Asset chỉ vào `decommissioned` qua IMM-14. Nguồn vào `pending_decommission` là IMM-13.*

---

## 7. Package diagram — IMM-14 trong AssetCore

```mermaid
flowchart LR
    subgraph EOL["Khối D — End-of-life"]
        IMM13[IMM-13<br/>Decommission Decision]
        IMM14[IMM-14<br/>Asset Closure]
    end
    subgraph OP["Khối C — Operation"]
        IMM05[IMM-05 Hồ sơ]
        IMM15[IMM-15 Phụ tùng]
        IMM08[IMM-08 PM]
        IMM09[IMM-09 Repair]
        IMM11[IMM-11 Calibration]
        IMM16[IMM-16 Tuân thủ]
    end
    IMM13 --> IMM14
    IMM05 -.archive.-> IMM14
    IMM15 -.reconcile.-> IMM14
    IMM08 -.close WO.-> IMM14
    IMM09 -.close WO.-> IMM14
    IMM11 -.close cert.-> IMM14
    IMM14 -.evidence.-> IMM16
```

*Hình 7.1 — Vị trí IMM-14 trong tổng thể; cross-link xem [00 hồ sơ kiến trúc](../architecture/Ho_so_kien_truc_IMMIS.md) line 260.*

---

*Hết file 03 — diagrams overview. Khi BE scaffold xong, bổ sung Sequence chi tiết cho UC-14-01, UC-14-04 và Component diagram microservice nếu tách.*
