# 03 — Biểu đồ kỹ thuật — IMM-00 Foundation (Master / Cross-cutting)

| Mục | Giá trị |
|---|---|
| Module | IMM-00 — Foundation / Master Cross-cutting |
| Phạm vi | Foundation — cross-cutting |
| Owner | System Architect / Tech Lead / DBA |
| Liên kết | [02 Analysis & Design](./02_Analysis_Design.md) · [04 Backend Design](./04_Backend_Design.md) |

---

# Phần I — Entity Relationship Diagram (ERD)

## I.1. ERD — Foundation DocTypes (Core + Governance)

```mermaid
erDiagram
    AC_ASSET_CATEGORY ||--o{ IMM_DEVICE_MODEL : "asset_category → inherit gmdn_code + pm_defaults"
    IMM_DEVICE_MODEL ||--o{ AC_ASSET : "device_model → inherit gmdn_code + pm_intervals"
    AC_ASSET }o--|| AC_ASSET_CATEGORY : "asset_category (direct link)"
    AC_ASSET }o--|| AC_LOCATION : "location"
    AC_ASSET }o--|| AC_DEPARTMENT : "department"
    AC_ASSET }o--|| AC_SUPPLIER : "supplier"
    AC_ASSET ||--o{ ASSET_LIFECYCLE_EVENT : "emits"
    AC_ASSET ||--o{ IMM_AUDIT_TRAIL : "logged_by"
    AC_ASSET ||--o{ INCIDENT_REPORT : "reported_on"
    INCIDENT_REPORT ||--o| IMM_CAPA_RECORD : "linked_capa"
    IMM_DEVICE_MODEL ||--o{ IMM_DEVICE_SPARE_PART : "spare_parts_list"
    IMM_DEVICE_SPARE_PART }o--|| AC_SPARE_PART : "spare_part"
    AC_SUPPLIER ||--o{ AC_AUTHORIZED_TECHNICIAN : "authorized_technicians"
    AC_LOCATION ||--o| AC_LOCATION : "parent_location (tree)"
    AC_DEPARTMENT ||--o| AC_DEPARTMENT : "parent_department (tree)"
    AC_WAREHOUSE ||--o{ AC_SPARE_PART_STOCK : "has stock"
    AC_SPARE_PART ||--o{ AC_SPARE_PART_STOCK : "stocked at"
    AC_STOCK_MOVEMENT ||--o{ AC_STOCK_MOVEMENT_ITEM : "items"
    AC_STOCK_MOVEMENT_ITEM }o--|| AC_SPARE_PART : "spare_part"

    AC_ASSET {
        varchar name PK "AC-ASSET-YYYY-#####"
        varchar asset_name
        varchar asset_code
        varchar device_model FK
        varchar asset_category FK
        varchar location FK
        varchar department FK
        varchar supplier FK
        varchar responsible_technician FK
        varchar lifecycle_status "8 states"
        varchar risk_classification "Low/Medium/High/Critical"
        varchar udi_code
        varchar gmdn_code "inherit từ device_model.gmdn_code — trục lọc/quản lý"
        varchar byt_reg_no
        date byt_reg_expiry
        date next_pm_date
        date next_calibration_date
        date commissioning_date
    }

    IMM_AUDIT_TRAIL {
        varchar name PK "IMM-AUD-YYYY-#######"
        varchar asset FK
        varchar event_type
        varchar actor
        datetime timestamp
        varchar from_status
        varchar to_status
        varchar ref_doctype
        varchar ref_name
        varchar hash_sha256
        varchar prev_hash
    }

    ASSET_LIFECYCLE_EVENT {
        varchar name PK "ALE-YYYY-#######"
        varchar asset FK
        varchar event_type
        datetime timestamp
        varchar actor
        varchar from_status
        varchar to_status
        varchar root_doctype
        varchar root_record
        text notes
    }

    IMM_CAPA_RECORD {
        varchar name PK "CAPA-YYYY-#####"
        varchar asset FK
        varchar source_type
        varchar source_ref
        varchar severity
        varchar status "Open/InProgress/Overdue/Closed"
        varchar responsible FK
        date due_date
        text root_cause
        text corrective_action
        text preventive_action
        varchar linked_incident FK
        date closed_date
    }

    INCIDENT_REPORT {
        varchar name PK "IR-YYYY-####"
        varchar asset FK
        varchar severity
        varchar status
        datetime incident_datetime
        varchar reporter FK
        int patient_affected
        int reported_to_byt
        date byt_report_date
        varchar linked_capa FK
    }

    AC_ASSET_CATEGORY {
        varchar name PK "by category_name"
        varchar category_name
        varchar gmdn_code "Nguồn GMDN — kế thừa xuống Device Model"
        int default_pm_required
        int default_pm_interval_days
        int default_calibration_required
        int default_calibration_interval_days
        varchar default_depreciation_method
        int total_depreciation_months
    }

    IMM_DEVICE_MODEL {
        varchar name PK "IMM-MDL-YYYY-####"
        varchar model_name
        varchar manufacturer
        varchar asset_category FK "→ AC Asset Category"
        varchar medical_device_class "I/II/III"
        varchar risk_classification "auto từ class"
        varchar gmdn_code "inherit từ asset_category.gmdn_code; có thể override"
        varchar emdn_code
        int pm_interval_days
        int calibration_interval_days
    }

    IMM_SLA_POLICY {
        varchar name PK
        varchar policy_name
        varchar priority "P1/P2/P3/P4"
        varchar risk_class
        int response_time_minutes
        float resolution_time_hours
        int is_default
    }
```

### Chuỗi kế thừa GMDN / PM Defaults

```
AC Asset Category          (nguồn dữ liệu — gmdn_code + pm/calibration defaults)
        │  before_insert (IMMDeviceModel)
        ▼
IMM Device Model           (kế thừa gmdn_code từ category; có thể override thủ công)
        │  before_insert (ACAsset — via fetch_from + on_insert hook nếu cần)
        ▼
AC Asset                   (nhận gmdn_code từ device_model — trục lọc/quản lý thiết bị)
```

- **`gmdn_code`**: mã phân loại thiết bị y tế toàn cầu (5–6 chữ số). Sống ở `AC Asset Category` vì một GMDN code tương ứng với một *loại* thiết bị (không phải từng model cụ thể). Model kế thừa để có thể tra nhanh mà không cần join qua category.
> **Note (2026-05-19):** Field trạng thái sử dụng GMDN (cũ) trên Asset đã bị loại bỏ — trùng ngữ nghĩa với `lifecycle_status`. Lọc/quản lý nhóm thiết bị nay dùng `gmdn_code`. Xem [analysis §6](../res/gmdn-asset-category-analysis.md).

---

## I.2. ERD — Inventory Sub-domain (v4)

```mermaid
erDiagram
    AC_WAREHOUSE ||--o{ AC_SPARE_PART_STOCK : "has"
    AC_SPARE_PART ||--o{ AC_SPARE_PART_STOCK : "stocked_at"
    AC_STOCK_MOVEMENT ||--o{ AC_STOCK_MOVEMENT_ITEM : "items"
    AC_STOCK_MOVEMENT_ITEM }o--|| AC_SPARE_PART : "spare_part"
    AC_WAREHOUSE }o--|| AC_LOCATION : "location"
    AC_WAREHOUSE }o--|| AC_DEPARTMENT : "department"

    AC_WAREHOUSE {
        varchar name PK "AC-WH-####"
        varchar warehouse_code
        varchar warehouse_name
        varchar location FK
        varchar department FK
        varchar manager FK
        int is_active
    }

    AC_SPARE_PART {
        varchar name PK "AC-SP-YYYY-####"
        varchar part_code
        varchar part_name
        varchar part_category
        varchar preferred_supplier FK
        decimal unit_cost
        int min_stock_level
        int max_stock_level
        int is_active
    }

    AC_SPARE_PART_STOCK {
        varchar name PK "{warehouse}::{spare_part}"
        varchar warehouse FK
        varchar spare_part FK
        float qty_on_hand
        float reserved_qty
        float available_qty
        datetime last_movement_date
    }

    AC_STOCK_MOVEMENT {
        varchar name PK "AC-SM-YYYY-#####"
        varchar movement_type "Receipt/Issue/Transfer/Adjustment"
        datetime movement_date
        varchar from_warehouse FK
        varchar to_warehouse FK
        varchar reference_type
        varchar reference_name
        varchar requested_by FK
        varchar status "Draft/Submitted/Cancelled"
    }
```

## I.3. Entity catalog

**Foundation DocTypes (IMM-00 sở hữu):**

| Entity | DocType name | Naming | Volume/năm |
|---|---|---|---|
| AC Asset | tabAC Asset | AC-ASSET-.YYYY.-.##### | ~1000 assets/site |
| AC Supplier | tabAC Supplier | AC-SUP-.YYYY.-.#### | ~100 NCC/site |
| AC Location | tabAC Location | AC-LOC-.YYYY.-.#### | ~200 locations/site |
| AC Department | tabAC Department | AC-DEPT-.#### | ~50 departments/site |
| AC Asset Category | tabAC Asset Category | by category_name | ~20 categories |
| IMM Device Model | tabIMM Device Model | IMM-MDL-.YYYY.-.#### | ~500 models |
| IMM SLA Policy | tabIMM SLA Policy | by policy_name | ~20 policies |
| IMM Audit Trail | tabIMM Audit Trail | IMM-AUD-.YYYY.-.####### | ~5M records |
| IMM CAPA Record | tabIMM CAPA Record | CAPA-.YYYY.-.##### | ~200/năm |
| Asset Lifecycle Event | tabAsset Lifecycle Event | ALE-.YYYY.-.####### | ~10k/năm |
| Incident Report | tabIncident Report | IR-.YYYY.-.#### | ~300/năm |

**Child DocTypes:**

| Child DocType | Parent | Mục đích |
|---|---|---|
| IMM Device Spare Part | IMM Device Model | BOM phụ tùng đề xuất |
| AC Authorized Technician | AC Supplier | KTV ủy quyền của NCC |
| AC Stock Movement Item | AC Stock Movement | Chi tiết từng phụ tùng |

---

# Phần II — Class Diagram

## II.1. Shared utility classes

```mermaid
classDiagram
    class FrappeDocument {
        <<framework>>
        +name: str
        +modified: datetime
        +docstatus: int
        +validate()
        +before_insert()
        +on_insert()
        +before_submit()
        +on_submit()
    }

    class ACAset {
        <<DocType controller>>
        +asset_name: str
        +lifecycle_status: str
        +risk_classification: str
        +device_model: Link
        +next_pm_date: date
        +gmdn_code: str
        +validate()
        +before_save()
        +on_submit()
    }

    class IMMDeviceModel {
        <<DocType controller>>
        +model_name: str
        +medical_device_class: str
        +risk_classification: str
        +pm_interval_days_default: int
        +validate()
    }

    class IMMAuditTrail {
        <<DocType controller - append-only>>
        +asset: Link
        +event_type: str
        +hash_sha256: str
        +prev_hash: str
        +validate()
    }

    class IMMCAPARecord {
        <<DocType controller - submittable>>
        +status: str
        +root_cause: str
        +corrective_action: str
        +due_date: date
        +validate()
        +before_submit()
    }

    class Imm00Service {
        <<service module>>
        +log_audit_event(asset, event_type, actor, ...) None
        +create_lifecycle_event(asset, event_type, ...) str
        +transition_asset_status(asset, to_status, ...) dict
        +get_sla_policy(priority, risk_class) dict
        +create_capa(asset, source_type, ...) str
        +close_capa(capa_name, ...) None
        +validate_asset_for_operations(asset) None
        +check_capa_overdue() None
        +check_vendor_contract_expiry() None
        +check_registration_expiry() None
    }

    class Imm00Api {
        <<API module>>
        +list_assets(...) dict
        +get_asset(name) dict
        +create_asset(...) dict
        +update_asset(...) dict
        +transition_asset_status(...) dict
        +verify_audit_chain(asset) dict
        +create_capa(...) dict
        +close_capa(...) dict
        +create_incident(...) dict
        +submit_incident(name) dict
    }

    class ResponseUtils {
        <<utils/response.py>>
        +_ok(data) dict
        +_err(msg, code) dict
    }

    class LifecycleUtils {
        <<utils/lifecycle.py>>
        +create_lifecycle_event(...) str
        +transition_status(asset, from_s, to_s) None
    }

    class EmailUtils {
        <<utils/email.py>>
        +get_role_emails(roles) list
        +safe_sendmail(recipients, subject, template, args) None
    }

    ACAset --|> FrappeDocument
    IMMDeviceModel --|> FrappeDocument
    IMMAuditTrail --|> FrappeDocument
    IMMCAPARecord --|> FrappeDocument
    Imm00Service ..> ACAset : uses
    Imm00Service ..> IMMAuditTrail : creates
    Imm00Service ..> IMMCAPARecord : creates
    Imm00Service ..> LifecycleUtils : delegates
    Imm00Service ..> EmailUtils : delegates
    Imm00Api ..> Imm00Service : delegates
    Imm00Api ..> ResponseUtils : wraps
    ACAset ..> Imm00Service : calls hooks
```

## II.2. Layer mapping

```mermaid
flowchart TB
    FE["Frontend Vue 3\n9 route groups + shared stores"]
    API["api/imm00.py + api/inventory.py\n42 + 15 endpoints"]
    SVC["services/imm00.py + services/inventory.py\n10 + 7 shared functions"]
    CTL["DocType controllers\nvalidate / before_submit / on_submit / on_trash"]
    UTILS["utils/: response, lifecycle, email, pagination"]
    ORM["Frappe ORM + MariaDB"]
    SCH["Frappe Scheduler\n4 daily jobs"]

    FE -->|HTTP| API
    API --> SVC
    API --> UTILS
    SCH --> SVC
    SVC --> CTL
    SVC --> UTILS
    CTL --> ORM
    SVC --> ORM
```

---

# Phần III — Sequence Diagrams

## III.1. Sequence — log_audit_event (SHA-256 chain)

```mermaid
sequenceDiagram
    participant Caller as Caller Module (e.g. IMM-09)
    participant SVC as services.imm00
    participant DB as MariaDB
    participant AUD as IMM Audit Trail

    Caller->>SVC: log_audit_event(asset, event_type, actor, ref_doctype, ref_name, ...)
    SVC->>DB: SELECT last IMM Audit Trail WHERE asset ORDER BY timestamp DESC LIMIT 1
    DB-->>SVC: {hash_sha256: "prev_hash_value"}
    SVC->>SVC: payload = canonical_json(asset, event_type, actor, timestamp, change_summary)
    SVC->>SVC: hash_sha256 = SHA256(prev_hash + payload)
    SVC->>AUD: frappe.new_doc("IMM Audit Trail")
    SVC->>AUD: doc.set(hash_sha256, prev_hash, ...)
    AUD->>DB: INSERT (immutable, no update/delete perm)
    DB-->>SVC: "IMM-AUD-2026-0001234"
    SVC-->>Caller: "IMM-AUD-2026-0001234"
```

## III.2. Sequence — transition_asset_status

```mermaid
sequenceDiagram
    actor Actor as Actor (Workshop Lead / Ops Manager)
    participant API as api.imm00
    participant SVC as services.imm00
    participant Asset as AC Asset
    participant ALE as Asset Lifecycle Event
    participant AUD as IMM Audit Trail
    database DB

    Actor->>API: POST transition_asset_status {name, new_status, reason}
    API->>SVC: transition_asset_status(asset_name, to_status, actor, reason, root_doctype, root_record)

    alt to_status = lifecycle_status (no change)
        SVC-->>API: ServiceError(VALIDATION, "Trạng thái không thay đổi")
        API-->>Actor: {success: false, ...}
    else Invalid transition (e.g. Decommissioned → Active)
        SVC-->>API: ServiceError(AC-E002, "Transition không hợp lệ")
        API-->>Actor: {success: false, ...}
    else Happy path
        SVC->>Asset: db.set_value("lifecycle_status", to_status)
        Asset->>DB: UPDATE tabAC Asset
        SVC->>ALE: create_lifecycle_event(asset, event_type, from_s, to_s, root, notes)
        ALE->>DB: INSERT (append-only)
        SVC->>SVC: log_audit_event(asset, "State Change", actor, ...)
        SVC->>DB: INSERT IMM Audit Trail
        alt to_status = "Decommissioned"
            SVC->>Asset: db.set_value is_pm_required=0, next_pm_date=NULL (BR-00-04)
            Asset->>DB: UPDATE
        end
        SVC-->>API: {asset, from_status, to_status, lifecycle_event, audit_trail}
        API-->>Actor: {success: true, data: {...}}
    end
```

## III.3. Sequence — check_capa_overdue (Daily scheduler)

```mermaid
sequenceDiagram
    participant SCH as Frappe Scheduler (02:00)
    participant SVC as services.imm00
    participant DB as MariaDB
    participant Email as utils.email

    SCH->>SVC: check_capa_overdue()
    SVC->>DB: get_all("IMM CAPA Record") WHERE status IN ("Open", "In Progress") AND due_date < today()
    DB-->>SVC: [capa_list]

    loop for each overdue CAPA
        SVC->>DB: db.set_value("IMM CAPA Record", name, "status", "Overdue")
        SVC->>SVC: log_audit_event(asset, "CAPA Overdue", "Scheduler", ...)
        SVC->>Email: get_role_emails(["IMM QA Officer"])
        SVC->>Email: safe_sendmail(recipients=[responsible, qa_emails], template="CAPA_Overdue", ...)
    end
    SVC-->>SCH: {marked_overdue: N, emails_sent: M}
```

## III.4. Sequence — verify_audit_chain

```mermaid
sequenceDiagram
    actor QA as QA Officer
    participant API as api.imm00
    participant SVC as services.imm00
    participant DB as MariaDB

    QA->>API: POST verify_audit_chain {asset: "AC-ASSET-2026-00001"}
    API->>SVC: verify_audit_chain(asset)
    SVC->>DB: SELECT * FROM tabIMM Audit Trail WHERE asset ORDER BY timestamp ASC
    DB-->>SVC: [all audit records sorted]

    SVC->>SVC: prev_hash = ""
    loop for each record in order
        SVC->>SVC: expected = SHA256(prev_hash + record.canonical_json)
        alt expected != record.hash_sha256
            SVC-->>API: {verified: false, tampered_at: record.name, expected, actual}
            SVC->>SVC: log_audit_event("Integrity Violation") + email QA Officer
            API-->>QA: {success: true, data: {verified: false, tampered_at: ...}}
        end
        SVC->>SVC: prev_hash = record.hash_sha256
    end
    SVC-->>API: {verified: true, total_records: N, last_hash: "..."}
    API-->>QA: {success: true, data: {verified: true, ...}}
```

---

# Phần IV — Communication Diagram

## IV.1. Communication — create_asset (full flow)

```plantuml
@startuml
object "browser:VueSPA" as B
object ":Imm00Api" as API
object ":Imm00Service" as SVC
object ":ACAssetDoc" as DOC
object ":IMMDeviceModel" as MDL
object ":AuditTrail" as AUD
database ":MariaDB" as DB

B    --> API  : 1: POST create_asset {payload}
API  --> SVC  : 2: validate inputs
SVC  --> MDL  : 3: frappe.get_doc(device_model) → fetch risk_class, pm_interval
MDL  --> DB   : 3.1: SELECT
SVC  --> DOC  : 4: frappe.new_doc("AC Asset")
SVC  --> DOC  : 4.1: set all fields
DOC  --> DB   : 5: INSERT tabAC Asset
SVC  --> AUD  : 6: log_audit_event("Asset Created")
AUD  --> DB   : 6.1: INSERT tabIMM Audit Trail
API  --> B    : 7: 200 {success: true, data: {name: "AC-ASSET-2026-00001"}}
@enduml
```

## IV.2. Communication — close_capa

```plantuml
@startuml
object "browser:VueSPA" as B
object ":Imm00Api" as API
object ":Imm00Service" as SVC
object ":CAPADoc" as CAPA
object ":AuditTrail" as AUD
database ":MariaDB" as DB

B    --> API  : 1: POST close_capa {name, root_cause, corrective_action, preventive_action, effectiveness_check}
API  --> SVC  : 2: close_capa(capa_name, ...)
SVC  --> CAPA : 3: frappe.get_doc("IMM CAPA Record", name)
CAPA --> DB   : 3.1: SELECT
SVC  --> SVC  : 4: validate root_cause + corrective_action + preventive_action (BR-00-08)
alt Missing required fields
    SVC  --> API  : 5a: ServiceError(AC-E005, "Thiếu thông tin CAPA")
    API  --> B    : 5b: {success: false, code: "AC-E005"}
else Happy path
    SVC  --> CAPA : 5: set status="Closed", closed_date=today()
    CAPA --> DB   : 5.1: UPDATE
    SVC  --> CAPA : 6: doc.submit() → docstatus=1
    CAPA --> DB   : 6.1: UPDATE docstatus
    SVC  --> AUD  : 7: log_audit_event("CAPA Closed")
    AUD  --> DB   : 7.1: INSERT
    API  --> B    : 8: {success: true, data: {name, status: "Closed", closed_at}}
end
@enduml
```

---

# Phần V — Package / Dependency Diagram

## V.1. Backend package diagram

```mermaid
flowchart TB
    subgraph api_layer["api/"]
        ApiImm00["api.imm00\n42 endpoints"]
        ApiInventory["api.inventory\n15 endpoints"]
    end

    subgraph services_layer["services/"]
        SvcImm00["services.imm00\n10 shared functions"]
        SvcInventory["services.inventory\n7 functions"]
    end

    subgraph utils_layer["utils/"]
        UtilResponse["utils.response\n_ok() / _err()"]
        UtilLifecycle["utils.lifecycle\ncreate_lifecycle_event()"]
        UtilEmail["utils.email\nget_role_emails() / safe_sendmail()"]
        UtilPagination["utils.pagination\npaginate()"]
    end

    subgraph doctype_layer["doctype/"]
        DtACAsset["ac_asset/ac_asset.py"]
        DtACSupplier["ac_supplier/ac_supplier.py"]
        DtIMMDevice["imm_device_model/imm_device_model.py"]
        DtAuditTrail["imm_audit_trail/imm_audit_trail.py"]
        DtCAPARecord["imm_capa_record/imm_capa_record.py"]
        DtALE["asset_lifecycle_event/asset_lifecycle_event.py"]
        DtIncident["incident_report/incident_report.py"]
    end

    subgraph permission_layer["permission/"]
        Permission["permission.py\nget_ac_asset_permission_query()"]
    end

    subgraph fixtures_layer["fixtures/"]
        Roles["imm_roles.json"]
        SLAPolicies["imm_sla_policies.json"]
        Workflows["imm_workflows.json"]
    end

    ApiImm00 --> SvcImm00
    ApiImm00 --> UtilResponse
    ApiInventory --> SvcInventory
    SvcImm00 --> UtilLifecycle
    SvcImm00 --> UtilEmail
    SvcImm00 --> DtAuditTrail
    SvcImm00 --> DtALE
    SvcImm00 --> DtCAPARecord
    DtACAsset --> SvcImm00
    DtIncident --> SvcImm00
    ApiImm00 --> UtilPagination
```

## V.2. Frontend package diagram

```mermaid
flowchart TB
    subgraph pages["pages/"]
        PDash["index.vue (Dashboard)"]
        PAssets["assets/index.vue + [name].vue + new.vue"]
        PSuppliers["suppliers/index.vue + [name].vue"]
        PLocations["locations/index.vue"]
        PDepts["departments/index.vue"]
        PMaster["master-data/ (device-models, sla, categories)"]
        PIncidents["incidents/index.vue + new.vue (wizard)"]
        PCAPA["capa/index.vue + [name].vue"]
        PAudit["audit-trail/index.vue"]
    end

    subgraph stores_layer["stores/"]
        AuthStore["authStore.ts\nhasRole() / user"]
        UIStore["uiStore.ts\nnotifications / loading"]
        NotifStore["notifStore.ts\nalerts / scheduler warnings"]
    end

    subgraph api_layer["api/"]
        ApiClient["client.ts\nAxios wrapper + CSRF interceptor"]
        ApiImm00["imm00.ts\nlist_assets, get_asset, create_asset..."]
        ApiInventory["inventory.ts\nstock endpoints"]
    end

    subgraph composables_layer["composables/"]
        UseAuth["useAuth.ts"]
        UsePagination["usePagination.ts"]
        UseOffline["useOffline.ts (IndexedDB queue)"]
    end

    subgraph layouts_layer["layouts/"]
        AppShell["AppShell.vue\nTopbar + Sidebar + Breadcrumb"]
        PrintLayout["PrintLayout.vue"]
    end

    PAssets --> AuthStore
    PAssets --> ApiImm00
    PCAPA --> AuthStore
    PCAPA --> ApiImm00
    PAudit --> ApiImm00
    ApiImm00 --> ApiClient
    ApiInventory --> ApiClient
    AppShell --> AuthStore
    AppShell --> NotifStore
```

## V.3. Cross-module dependency

```mermaid
flowchart LR
    IMM00["IMM-00\nFoundation Layer\n(27 DocTypes + shared services)"]

    IMM04["IMM-04\nInstallation"]
    IMM05["IMM-05\nRegistration"]
    IMM08["IMM-08\nPM"]
    IMM09["IMM-09\nRepair"]
    IMM11["IMM-11\nCalibration"]
    IMM12["IMM-12\nCorrective/CAPA"]
    IMM13["IMM-13\nEnd of Life"]
    IMM15_16["IMM-15/16\nIntegration"]

    IMM00 -->|"create_lifecycle_event\nvalidate_asset_for_operations"| IMM04
    IMM00 -->|"check_registration_expiry\nAC Asset.byt_reg_expiry"| IMM05
    IMM00 -->|"get_sla_policy\nvalidate_asset_for_operations\ncreate_lifecycle_event"| IMM08
    IMM00 -->|"transition_asset_status\ncreate_capa\nIncident Report"| IMM09
    IMM00 -->|"iso_17025_cert gate\nget_sla_policy"| IMM11
    IMM00 -->|"create_capa\ntransition_asset_status"| IMM12
    IMM00 -->|"transition_asset_status Decommissioned\nsuspend schedules"| IMM13
    IMM00 -->|"AC Asset master data"| IMM15_16
```

---

## DoD — File 03 hoàn chỉnh

### I. ERD
- [x] Foundation DocTypes ERD (Core + Governance)
- [x] Inventory sub-domain ERD
- [x] Entity catalog + naming + volume
- [x] Child DocTypes

### II. Class Diagram
- [x] Shared utility classes (Imm00Service, ResponseUtils, LifecycleUtils)
- [x] DocType controllers (ACAset, IMMDeviceModel, IMMAuditTrail, IMMCAPARecord)
- [x] Layer mapping flowchart

### III. Sequence Diagrams
- [x] log_audit_event (SHA-256 chain)
- [x] transition_asset_status (happy + error paths)
- [x] check_capa_overdue (daily scheduler)
- [x] verify_audit_chain (integrity check)

### IV. Communication Diagrams
- [x] create_asset (full flow)
- [x] close_capa

### V. Package Diagrams
- [x] Backend package (api → services → utils → doctype)
- [x] Frontend package (pages → stores → api → composables)
- [x] Cross-module dependency (IMM-00 → all downstream)
