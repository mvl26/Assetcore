# IMM-05 — Diagrams

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-05 — Asset Document Repository |
| Template | 03_Diagrams v4.1+ |
| Ngày tạo | 2026-05-08 |
| Trạng thái | Draft |

---

## Phần I — ERD (Entity Relationship Diagram)

### I.1 ERD Tổng thể

```mermaid
erDiagram
    ASSET ||--o{ ASSET_DOCUMENT : "has"
    ASSET ||--o{ DOCUMENT_REQUEST : "has"
    ASSET_DOCUMENT ||--o{ ASSET_DOCUMENT : "superseded_by (self-ref)"
    ASSET_DOCUMENT }o--|| ASSET_COMMISSIONING : "source_commissioning"
    ASSET_DOCUMENT }o--|| WORKFLOW_STATE : "workflow_state"
    DOCUMENT_REQUEST }o--|| ASSET_DOCUMENT : "fulfilled_by"
    REQUIRED_DOCUMENT_TYPE }o--|| ASSET_CATEGORY : "applies_to_asset_category"

    ASSET {
        string name PK
        string item_code
        string location
        string asset_category
    }
    ASSET_DOCUMENT {
        string name PK
        string asset_ref FK
        string model_ref
        bool is_model_level
        string clinical_dept
        string source_commissioning FK
        string source_module
        enum doc_category
        string doc_type_detail
        string doc_number
        string version
        date issued_date
        date expiry_date
        string issuing_authority
        int days_until_expiry
        bool is_expired
        string file_attachment
        string file_name_display
        string approved_by
        date approval_date
        text rejection_reason
        string superseded_by FK
        string archived_by_version
        date archive_date
        text change_summary
        enum visibility
        bool is_exempt
        text exempt_reason
        string exempt_proof
        text notes
        string workflow_state FK
    }
    DOCUMENT_REQUEST {
        string name PK
        string asset_ref FK
        string doc_type_required
        enum doc_category
        enum status
        enum priority
        string assigned_to
        date due_date
        enum source_type
        bool escalation_sent
        text request_note
        string fulfilled_by FK
    }
    REQUIRED_DOCUMENT_TYPE {
        string name PK
        enum doc_category
        bool has_expiry
        bool is_mandatory
        string applies_to_asset_category FK
        bool applies_when_radiation
    }
    ASSET_COMMISSIONING {
        string name PK
        string asset_ref FK
    }
    WORKFLOW_STATE {
        string name PK
        int doc_status
        string type
    }
    ASSET_CATEGORY {
        string name PK
    }
```

### I.2 Cheatsheet cardinality

| Ký hiệu | Nghĩa |
|---|---|
| `||--o{` | 1 bắt buộc — 0 hoặc nhiều |
| `}o--||` | 0 hoặc nhiều — 1 bắt buộc |
| `||--||` | 1 bắt buộc — 1 bắt buộc |
| `}o--o{` | 0 hoặc nhiều — 0 hoặc nhiều |

### I.3 Entity catalog

| Entity | Thuộc module | DocType name | Ghi chú |
|---|---|---|---|
| Asset | Core (Frappe) | AC Asset | Registry thiết bị |
| Asset Document | IMM-05 (owned) | Asset Document | Tài liệu hồ sơ thiết bị |
| Document Request | IMM-05 (owned) | Document Request | Yêu cầu bổ sung tài liệu |
| Required Document Type | IMM-05 (owned) | Required Document Type | Master config tài liệu bắt buộc |
| Asset Commissioning | IMM-04 (cross-module) | Asset Commissioning | Nguồn của tài liệu (auto-import) |
| Workflow State | Core (Frappe) | Workflow State | Quản lý trạng thái workflow |

### I.4 Data Dictionary

**Bảng 1.1 — tabAsset Document**

| Cột | Kiểu | Nullable | Ghi chú |
|---|---|:---:|---|
| `name` | varchar(140) | N | PK, autoname `DOC-{asset_ref}-{YYYY}-{#####}` |
| `asset_ref` | varchar(140) | N | FK → tabAsset, search_index |
| `model_ref` | varchar(140) | Y | FK → IMM Device Model, auto-fetch |
| `is_model_level` | tinyint(1) | Y | Áp dụng toàn model |
| `clinical_dept` | varchar(140) | Y | fetch_from asset_ref.location, read_only |
| `source_commissioning` | varchar(140) | Y | FK → Asset Commissioning |
| `source_module` | varchar(140) | Y | Module tạo tài liệu, read_only |
| `doc_category` | varchar(140) | N | Enum: Legal/Technical/Certification/Training/QA |
| `doc_type_detail` | varchar(140) | N | Tên loại tài liệu, title_field |
| `doc_number` | varchar(140) | N | Số hiệu, search_index |
| `version` | varchar(140) | N | default "1.0" |
| `issued_date` | date | N | Ngày cấp |
| `expiry_date` | date | Y | Bắt buộc nếu Legal/Certification (VR-07) |
| `issuing_authority` | varchar(255) | Y | Bắt buộc nếu Legal (VR-04) |
| `days_until_expiry` | int(11) | Y | Computed, read_only |
| `is_expired` | tinyint(1) | Y | Computed, read_only |
| `file_attachment` | text | N | File path Frappe, VR-08 ext validation |
| `file_name_display` | varchar(255) | Y | Display name, read_only |
| `approved_by` | varchar(140) | Y | FK → User, read_only |
| `approval_date` | date | Y | read_only |
| `rejection_reason` | text | Y | Bắt buộc nếu Rejected (VR-06) |
| `superseded_by` | varchar(140) | Y | FK → Asset Document (self-ref), read_only |
| `archived_by_version` | varchar(140) | Y | Version thay thế, read_only |
| `archive_date` | date | Y | read_only |
| `change_summary` | text | Y | Bắt buộc nếu version != "1.0" (VR-09) |
| `visibility` | varchar(140) | Y | Enum: Public/Internal_Only, default Public |
| `is_exempt` | tinyint(1) | Y | Miễn đăng ký NĐ98 |
| `exempt_reason` | text | Y | Bắt buộc nếu is_exempt=1 (VR-10) |
| `exempt_proof` | text | Y | File path bắt buộc nếu is_exempt=1 (VR-10) |
| `notes` | longtext | Y | Ghi chú tự do |
| `workflow_state` | varchar(140) | Y | FK → Workflow State, in_list_view |

**Bảng 1.2 — tabDocument Request**

| Cột | Kiểu | Nullable | Ghi chú |
|---|---|:---:|---|
| `name` | varchar(140) | N | PK, autoname `DOCREQ-{YYYY}-{MM}-{#####}` |
| `asset_ref` | varchar(140) | N | FK → tabAsset |
| `doc_type_required` | varchar(255) | N | Loại tài liệu yêu cầu |
| `doc_category` | varchar(140) | N | Enum: Legal/.../QA |
| `status` | varchar(140) | N | Enum: Open/In_Progress/Overdue/Fulfilled/Cancelled, default Open |
| `priority` | varchar(140) | Y | Enum: Low/Medium/High/Critical, default Medium |
| `assigned_to` | varchar(140) | N | FK → User |
| `due_date` | date | N | Hạn hoàn thành |
| `source_type` | varchar(140) | Y | Enum: Manual/Dashboard/GW2_Block/Scheduler, read_only |
| `escalation_sent` | tinyint(1) | Y | 1 khi scheduler đã gửi cảnh báo, read_only |
| `request_note` | text | Y | Ghi chú yêu cầu |
| `fulfilled_by` | varchar(140) | Y | FK → Asset Document khi hoàn thành |

**Bảng 1.3 — tabRequired Document Type**

| Cột | Kiểu | Nullable | Ghi chú |
|---|---|:---:|---|
| `name` | varchar(140) | N | PK = type_name |
| `doc_category` | varchar(140) | N | Enum: Legal/.../QA |
| `has_expiry` | tinyint(1) | Y | Có ngày hết hạn |
| `is_mandatory` | tinyint(1) | Y | Bắt buộc cho compliance |
| `applies_to_asset_category` | varchar(140) | Y | FK → AC Asset Category |
| `applies_when_radiation` | tinyint(1) | Y | Chỉ áp dụng thiết bị bức xạ |

### I.5 Constraints & Indexes

```sql
-- Index Frappe auto-tạo từ search_index=1
CREATE INDEX idx_assetdoc_asset_ref      ON `tabAsset Document` (asset_ref);
CREATE INDEX idx_assetdoc_doc_number     ON `tabAsset Document` (doc_number);
CREATE INDEX idx_assetdoc_workflow_state ON `tabAsset Document` (workflow_state);
CREATE INDEX idx_assetdoc_model_ref      ON `tabAsset Document` (model_ref);
CREATE INDEX idx_assetdoc_expiry_date    ON `tabAsset Document` (expiry_date);

-- Composite index khuyến nghị (manual SQL)
CREATE INDEX idx_asd_asset_type_state
    ON `tabAsset Document` (asset_ref, doc_type_detail, workflow_state);
CREATE INDEX idx_asd_state_expiry
    ON `tabAsset Document` (workflow_state, expiry_date);

-- Index Document Request
CREATE INDEX idx_docreq_asset_status ON `tabDocument Request` (asset_ref, status);
```

> **VR-02 Unique check:** Không có DB UNIQUE constraint — kiểm tra bằng `frappe.db.exists()` trong controller `vr_02_unique_doc_number`. Thêm DB constraint là Tech-debt (Sprint 7).

---

## Phần II — Class Diagram

### II.1 Class Diagram — 4 lớp kiến trúc

```mermaid
classDiagram
    class APILayer {
        <<module: assetcore.api.imm05>>
        +list_documents(filters, page, page_size) dict
        +get_document(name) dict
        +create_document(doc_data) dict
        +update_document(name, doc_data) dict
        +approve_document(name) dict
        +reject_document(name, rejection_reason) dict
        +get_asset_documents(asset) dict
        +get_dashboard_stats() dict
        +get_expiring_documents(days) dict
        +get_compliance_by_dept() dict
        +get_document_history(name) dict
        +create_document_request(asset_ref, ...) dict
        +get_document_requests(asset_ref, status) dict
        +mark_exempt(asset_ref, doc_type_detail, ...) dict
        -_ok(data) dict
        -_err(msg, code) dict
        -_can_see_internal() bool
        -_apply_visibility_filter(filters) None
    }

    class AssetDocument {
        <<DocType: asset_document.py>>
        +asset_ref: str
        +doc_category: str
        +doc_type_detail: str
        +doc_number: str
        +version: str
        +issued_date: date
        +expiry_date: date
        +workflow_state: str
        +visibility: str
        +is_exempt: bool
        +validate()
        +before_save()
        +on_update()
        +on_trash()
        +auto_fetch_model_and_dept()
        +set_computed_fields()
        +archive_old_versions()
        +update_asset_completeness()
        -_compute_document_status() str
        -vr_01_expiry_after_issued()
        -vr_02_unique_doc_number()
        -vr_03_file_required_for_review()
        -vr_04_legal_requires_authority()
        -vr_05_no_state_regression()
        -vr_06_rejection_reason_required()
        -vr_07_legal_requires_expiry()
        -vr_08_file_format_check()
        -vr_09_change_summary_required()
        -vr_10_exempt_fields_required()
        -vr_11_exempt_doc_type_check()
    }

    class DocumentRequest {
        <<DocType: document_request.py>>
        +asset_ref: str
        +doc_type_required: str
        +status: str
        +priority: str
        +assigned_to: str
        +due_date: date
        +source_type: str
        +escalation_sent: bool
        +fulfilled_by: str
    }

    class SchedulerTasks {
        <<module: assetcore.tasks>>
        +check_document_expiry() None
        +update_asset_completeness() None
        +check_overdue_document_requests() None
    }

    class FrappeORM {
        <<Frappe Framework>>
        +get_doc(doctype, name) Document
        +new_doc(doctype) Document
        +db.get_list(doctype, ...) list
        +db.exists(doctype, filters) str
        +db.sql(query, values) list
        +publish_realtime(event, data, ...) None
    }

    APILayer --> AssetDocument : CRUD + workflow actions
    APILayer --> DocumentRequest : create + list
    APILayer --> FrappeORM : query
    AssetDocument --> FrappeORM : ORM
    DocumentRequest --> FrappeORM : ORM
    SchedulerTasks --> AssetDocument : batch update
    SchedulerTasks --> DocumentRequest : status update
    SchedulerTasks --> FrappeORM : SQL queries
```

### II.2 Class Catalog

| Class | Layer | File | Trách nhiệm |
|---|---|---|---|
| `APILayer` | API | `assetcore/api/imm05.py` | 14 whitelist endpoints, visibility filter, role check |
| `AssetDocument` | Controller | `assetcore/doctype/asset_document/asset_document.py` | 11 VR + 4 business methods, lifecycle hooks |
| `DocumentRequest` | Controller | `assetcore/doctype/document_request/document_request.py` | Yêu cầu bổ sung tài liệu |
| `SchedulerTasks` | Scheduler | `assetcore/tasks.py` | 3 cron jobs IMM-05 |
| `FrappeORM` | Data | Frappe core | Database access abstraction |

> **Tech-debt:** Chưa có `services/imm05.py`. Logic nghiệp vụ nằm trong `AssetDocument` controller. Khi refactor, tách `archive_old_versions`, `update_asset_completeness`, `_compute_document_status` ra service layer.

---

## Phần III — Sequence Diagrams

### III.1 Convention

| Ký hiệu | Nghĩa |
|---|---|
| `->` | Synchronous call |
| `-->` | Return |
| `+` | Activate lifeline |
| `-` | Deactivate lifeline |
| `alt` | Conditional branch |
| `Note` | Annotation |

### III.2 SD-05-01 — Tạo Asset Document (happy path)

```mermaid
sequenceDiagram
    autonumber
    actor KTV as KTV / Biomed
    participant FE as Frontend (Vue)
    participant API as imm05.create_document
    participant Ctrl as AssetDocument Controller
    participant DB as MariaDB

    KTV->>FE: Điền form tạo tài liệu, click [Lưu Draft]
    FE->>+API: POST create_document(doc_data)
    API->>API: Parse doc_data JSON
    API->>+Ctrl: frappe.new_doc("Asset Document")
    Ctrl->>Ctrl: Set fields từ doc_data
    Ctrl->>Ctrl: validate() → 11 VR checks
    alt VR fail
        Ctrl-->>API: raise ValidationError
        API-->>FE: {"success": false, "error": "...", "code": "VALIDATION_ERROR"}
        FE-->>KTV: Toast lỗi tiếng Việt
    else VR pass
        Ctrl->>DB: INSERT tabAsset Document
        DB-->>Ctrl: name = "DOC-AC-ASSET-2026-0001-2026-00001"
        Ctrl-->>API: doc.name
        API-->>-FE: {"success": true, "data": {"name": "...", "workflow_state": "Draft"}}
        FE-->>KTV: Toast "✅ Đã tạo tài liệu DOC-..."
        FE->>FE: Navigate to DocumentDetailView
    end
```

### III.3 SD-05-02 — Phê duyệt tài liệu (Approve)

```mermaid
sequenceDiagram
    autonumber
    actor QLCL as Tổ HC-QLCL
    participant FE as Frontend (Vue)
    participant API as imm05.approve_document
    participant Ctrl as AssetDocument Controller
    participant DB as MariaDB

    QLCL->>FE: Click [Approve] trên DocumentDetailView
    FE->>+API: POST approve_document(name)
    API->>API: Check workflow_state = "Pending Review"
    alt state ≠ Pending Review
        API-->>FE: {"success": false, "code": "INVALID_STATE"}
    else
        API->>API: Check session user IN _APPROVE_ROLES
        alt role not authorized
            API-->>FE: {"success": false, "code": "FORBIDDEN"}
        else
            API->>DB: Query Active docs cùng (asset_ref + doc_type_detail)
            DB-->>API: List older versions
            API->>DB: UPDATE workflow_state = "Archived" cho older docs
            Note over API,DB: archive_old_versions — idempotent
            API->>+Ctrl: doc.workflow_state = "Active"
            Ctrl->>Ctrl: set approved_by, approval_date
            Ctrl->>Ctrl: on_update() → update_asset_completeness()
            Ctrl->>DB: UPDATE tabAsset Document
            DB-->>Ctrl: OK
            Ctrl-->>-API: saved
            API-->>-FE: {"success": true, "data": {"name": "...", "new_state": "Active", "approved_by": "..."}}}
            FE-->>QLCL: Toast + badge chuyển "✅ Đang hiệu lực"
        end
    end
```

### III.4 SD-05-03 — Scheduler check_document_expiry

```mermaid
sequenceDiagram
    autonumber
    participant Cron as Frappe Scheduler (00:30)
    participant Task as tasks.check_document_expiry
    participant DB as MariaDB
    participant Log as Expiry Alert Log
    participant Email as Email Service

    Cron->>+Task: trigger daily 00:30
    loop for milestone in [90, 60, 30, 0]
        Task->>DB: SELECT * FROM tabAsset Document<br/>WHERE workflow_state='Active'<br/>AND expiry_date = today + milestone
        DB-->>Task: List docs expiring at milestone
        loop for each doc
            Task->>Log: Check EXISTS (asset_document=doc.name, alert_date=today)
            alt Alert đã gửi hôm nay (idempotent)
                Task->>Task: skip
            else
                Task->>Log: INSERT Expiry Alert Log {milestone, expiry_date, today}
                alt milestone = 0
                    Task->>DB: UPDATE workflow_state = "Expired"
                    Note over Task,DB: VR-05: Expired là terminal state
                end
                Task->>Email: Send email (level: 90=Info, 60=Warning, 30=Critical, 0=Danger)
            end
        end
    end
    Task-->>-Cron: done
```

### III.5 Cross-reference Sequence ↔ Use Case

| Sequence Diagram | Use Case liên quan | API endpoint |
|---|---|---|
| SD-05-01 | UC-01 Tạo tài liệu | `create_document` |
| SD-05-02 | UC-03 Phê duyệt | `approve_document` |
| SD-05-03 | UC-09 Scheduler expiry | `check_document_expiry` (tasks) |

---

## Phần IV — Communication Diagram

### IV.1 Comm-05-01 — Topology Module IMM-05

```
                    ┌─────────────────┐
                    │   Frontend Vue  │
                    │  (imm05Store)   │
                    └────────┬────────┘
                             │ HTTP whitelist
                             ▼
              ┌──────────────────────────────┐
              │  API Layer (api/imm05.py)    │
              │  14 endpoints + helpers      │
              └───────┬──────────────────────┘
                      │
           ┌──────────┼──────────────────┐
           │          │                  │
           ▼          ▼                  ▼
  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐
  │ AssetDoc    │  │ Document     │  │ Frappe ORM /     │
  │ Controller  │  │ Request      │  │ MariaDB          │
  │ (11 VR +    │  │ Controller   │  │ tabAsset Document│
  │  4 methods) │  │              │  │ tabDoc Request   │
  └──────┬──────┘  └──────┬───────┘  │ tabReq Doc Type  │
         │                │           └──────────────────┘
         ▼                ▼
  ┌──────────────────────────────┐
  │  Scheduler (tasks.py)        │
  │  check_document_expiry       │
  │  update_asset_completeness   │
  │  check_overdue_requests      │
  └──────────────────────────────┘

Cross-module:
  IMM-04 → IMM-05: imm04_asset_released event → auto create Asset Document
  IMM-05 → IMM-04: GW-2 gate query: SELECT Active docs WHERE doc_type="CN ĐK lưu hành"
  IMM-05 → IMM-13: Archived on asset retired
```

---

## Phần V — Package Diagram

### V.1 Backend Package Diagram

```mermaid
flowchart TB
    subgraph IMM05["Module IMM-05"]
        direction TB
        API["api/imm05.py\n14 endpoints"]
        CTRL["doctype/asset_document/\nasset_document.py"]
        DOCREQ["doctype/document_request/\ndocument_request.py"]
        RDT["doctype/required_document_type/\nrequired_document_type.py"]
        TASKS["tasks.py\n3 scheduler functions"]
        WF["workflow/\nimm_05_document_workflow.json"]
    end

    subgraph CORE["Core / Shared"]
        FRAPPE_ORM["Frappe ORM"]
        FRAPPE_WF["Frappe Workflow Engine"]
        FRAPPE_VER["Frappe Version (audit)"]
        FRAPPE_EMAIL["Frappe Email"]
    end

    subgraph CROSS["Cross-module"]
        IMM04["IMM-04\nAsset Commissioning"]
        IMM13["IMM-13\nEnd-of-Life"]
        IMM00["IMM-00\nfixtures/imm00_custom_fields.json"]
    end

    API --> CTRL
    API --> DOCREQ
    API --> FRAPPE_ORM
    CTRL --> FRAPPE_ORM
    CTRL --> FRAPPE_WF
    CTRL --> FRAPPE_VER
    TASKS --> CTRL
    TASKS --> DOCREQ
    TASKS --> FRAPPE_EMAIL
    TASKS --> FRAPPE_ORM
    WF --> FRAPPE_WF
    IMM04 --> CTRL
    CTRL --> IMM13
    IMM00 -.->|custom fields on Asset| FRAPPE_ORM
```

### V.2 Frontend Package Diagram

```mermaid
flowchart TB
    subgraph IMM05_FE["Frontend — IMM-05"]
        VIEWS["views/\nDocumentManagement.vue\nDocumentDetailView.vue\nDocumentCreateView.vue"]
        COMPS["components/imm05/\nDocumentRequestModal.vue\nExemptModal.vue\nStatusBadge.vue\nExpiryCountdown.vue"]
        STORE["stores/imm05Store.ts"]
        API_TS["api/imm05.ts"]
        TYPES["types/imm05.ts"]
    end

    subgraph SHARED_FE["Shared Frontend"]
        PINIA["Pinia"]
        VUEQ["TanStack Vue Query"]
        ROUTER["Vue Router"]
        USEAPI["composables/useApi()"]
    end

    subgraph ASSET_FE["Asset Detail (shared)"]
        ASSET_TAB["AssetDocumentsTab.vue"]
    end

    VIEWS --> STORE
    VIEWS --> COMPS
    VIEWS --> API_TS
    COMPS --> API_TS
    STORE --> PINIA
    API_TS --> USEAPI
    API_TS --> TYPES
    VIEWS --> VUEQ
    VIEWS --> ROUTER
    ASSET_TAB --> API_TS
    ASSET_TAB --> COMPS
```

### V.3 Anti-patterns

- **Không** query DB trực tiếp từ Frontend — phải qua API layer
- **Không** gọi `approve_document` từ Scheduler — chỉ `archive_old_versions` (idempotent)
- **Không** cache `document_status` trên Asset (đã bỏ v3) — tính on-the-fly qua SQL EXISTS
- **Không** cho FE tự filter `Internal_Only` — server-side enforcement duy nhất

---

## DoD Checklist

- [x] ERD Mermaid cho 3 owned entities + 3 cross-module
- [x] Data Dictionary đầy đủ cho 3 bảng chính
- [x] Composite index recommendation
- [x] Class diagram 4-layer với tech-debt note
- [x] 3 Sequence diagrams (happy path, approve, scheduler)
- [x] Communication diagram topology
- [x] Package diagram BE + FE
- [x] Anti-patterns list
