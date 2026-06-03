# 03 — Biểu đồ kỹ thuật (UML Diagrams)

| Mục | Giá trị |
|---|---|
| Module | IMM-11 — Hiệu chuẩn (Calibration) |
| Phạm vi | Per-module |
| Owner | System Analyst / Tech Lead / DBA |
| Liên kết | 02 Analysis & Design · 04 Backend Design |
| Cập nhật | 2026-05-18 |
| Trạng thái | ✅ Live — ERD + Class diagram + Sequence diagram phản ánh đúng `services/imm11.py` + DocType hiện hành |

---

# Phần I — Entity Relationship Diagram (ERD)

## I.1. ERD logic

```mermaid
erDiagram
    AC_Asset ||--o{ IMM_Calibration_Schedule : "has schedule"
    AC_Asset ||--o{ IMM_Asset_Calibration : "has calibrations"
    AC_Asset ||--o{ Asset_Lifecycle_Event : "emits events"
    IMM_Device_Model ||--o{ AC_Asset : "model of"
    AC_Supplier ||--o{ IMM_Asset_Calibration : "performs (Calibration Lab)"
    IMM_Calibration_Schedule ||--o{ IMM_Asset_Calibration : "generates"
    IMM_Asset_Calibration ||--o{ IMM_Calibration_Measurement : "has measurements"
    IMM_Asset_Calibration ||--o| IMM_CAPA_Record : "triggers on Fail"

    AC_Asset {
        string name PK
        string asset_name
        string device_model FK
        string lifecycle_status
        date last_calibration_date
        date next_calibration_date
        string calibration_status
    }

    IMM_Calibration_Schedule {
        string name PK
        string asset FK
        string device_model FK
        string calibration_type
        int interval_days
        date next_due_date
        string preferred_lab FK
        bool is_active
    }

    IMM_Asset_Calibration {
        string name PK
        string calibration_schedule FK
        string asset FK
        string calibration_type
        string status
        string overall_result
        date certificate_date
        string lab_supplier FK
        string technician FK
        bool is_recalibration
        string capa_record FK
    }

    IMM_Calibration_Measurement {
        string name PK
        string parent FK
        string parameter_name
        float nominal_value
        float tolerance_positive
        float tolerance_negative
        float measured_value
        bool out_of_tolerance
        string pass_fail
    }

    IMM_CAPA_Record {
        string name PK
        string asset FK
        string source_doctype
        string source_name
        string status
        text root_cause
        bool lookback_required
        string lookback_status
    }
```

## I.3. Entity catalog

### Entities module sở hữu (✅ Live)

| Entity | DocType | Naming | Lifecycle | Volume/năm/site |
|---|---|---|---|---|
| IMM Calibration Schedule | `IMM Calibration Schedule` (folder `imm_calibration_schedule`) | `CAL-SCH-.YYYY.-.#####` | Non-submittable, tồn tại đến khi asset Decommissioned | 1 per calibratable asset |
| IMM Asset Calibration | `IMM Asset Calibration` (folder `imm_asset_calibration`) | `CAL-.YYYY.-.#####` | Submittable, immutable sau Submit | ~500–2000 |
| IMM Calibration Measurement | `IMM Calibration Measurement` (folder `imm_calibration_measurement`) — child table | (auto) | Child của IMM Asset Calibration | ~5000–20000 rows |

### Entities tham chiếu cross-module (từ IMM-00)

| Entity | Owner | Vai trò |
|---|---|---|
| AC Asset | IMM-00 | Thiết bị được hiệu chuẩn |
| IMM Device Model | IMM-00 | Cung cấp `calibration_interval_days` |
| AC Supplier | IMM-00 | Calibration Lab (iso_17025_certified) |
| IMM CAPA Record | IMM-00 | Auto-created khi Fail (BR-11-02) |
| Asset Lifecycle Event | IMM-00 | Log 5 event types calibration |
| IMM Audit Trail | IMM-00 | SHA-256 chain mọi mutation |

## I.4. Data dictionary

### Bảng 1.1: IMM Calibration Schedule ✅ Live

| Field | Type | Length | Required | Default | PII | Validation | Mô tả |
|---|---|---|---|---|---|---|---|
| `name` | varchar | 30 | ✓ | autoname | — | `CAL-SCH-YYYY-NNNNN` | PK |
| `asset` | Link | 140 | ✓ | — | — | AC Asset exists | Thiết bị |
| `device_model` | Link | 140 | ✓ | auto-fetch | — | — | Auto từ asset |
| `calibration_type` | Select | — | ✓ | External | — | External, In-House | Loại |
| `interval_days` | Int | — | ✓ | từ Device Model | — | > 0 | Chu kỳ (ngày) |
| `next_due_date` | Date | — | ✓ | computed | — | — | Ngày đến hạn |
| `preferred_lab` | Link | 140 | ✗ | — | — | iso_17025_certified=1 | Lab ưu tiên |
| `is_active` | Check | — | ✓ | 1 | — | — | Đang hoạt động |

### Bảng 1.2: IMM Asset Calibration ✅ Live

| Field | Type | Length | Required | Default | PII | Validation | Mô tả |
|---|---|---|---|---|---|---|---|
| `name` | varchar | 30 | ✓ | autoname | — | `CAL-YYYY-NNNNN` | PK |
| `asset` | Link | 140 | ✓ | — | — | Active or is_recalibration | Thiết bị |
| `calibration_type` | Select | — | ✓ | — | — | External, In-House | Loại |
| `status` | Select | — | ✓ | Scheduled | — | 8 states | Trạng thái |
| `overall_result` | Select | — | ✗ | — | — | Passed, Failed, Conditionally Passed | Kết quả tổng |
| `lab_supplier` | Link | 140 | Conditional | — | — | iso_17025_certified=1 (External) | Lab |
| `certificate_file` | Attach | — | Conditional | — | — | PDF, bắt buộc External Submit | Chứng chỉ |
| `certificate_date` | Date | — | Conditional | — | — | ≤ today | Ngày cấp cert |
| `technician` | Link | 140 | ✓ | — | — | — | KTV |
| `is_recalibration` | Check | — | ✗ | 0 | — | — | Tái cal sau CAPA |
| `amendment_reason` | Small Text | 255 | Conditional | — | — | Bắt buộc khi Amend | Lý do Amend |

### Bảng 1.3: IMM Calibration Measurement ✅ Live

| Field | Type | Length | Required | Default | PII | Validation | Mô tả |
|---|---|---|---|---|---|---|---|
| `parameter_name` | Data | 140 | ✓ | — | — | — | Tên tham số |
| `unit` | Data | 40 | ✓ | — | — | — | Đơn vị |
| `nominal_value` | Float | — | ✓ | — | — | — | Giá trị danh định |
| `tolerance_positive` | Float | — | ✓ | — | — | > 0 | Dung sai (+) % |
| `tolerance_negative` | Float | — | ✓ | — | — | > 0 | Dung sai (-) % |
| `measured_value` | Float | — | ✓ | — | — | Required before Submit | Giá trị đo |
| `out_of_tolerance` | Check | — | ✗ | computed | — | Auto | Ngoài dung sai |
| `pass_fail` | Select | — | ✗ | computed | — | Pass, Fail | Kết quả |

## I.8. Volume & retention

| Entity | Volume/năm/site | Retention | Archive policy |
|---|---|---|---|
| IMM Calibration Schedule | ~500 | Suốt đời asset | Lưu tất cả, không xóa |
| IMM Asset Calibration | ~1000–2000 | ≥ 7 năm (NĐ98 Điều 40) | Archive sau 7 năm, không xóa |
| IMM Calibration Measurement | ~10000–20000 | ≥ 7 năm | Cùng với parent |

---

# Phần II — Class Diagram

## II.1.a. Biểu đồ lớp tổng quát

```mermaid
classDiagram
    class FrappeDocument {
        <<framework>>
        +name: str
        +modified: datetime
        +docstatus: int
        +validate()
        +on_submit()
        +on_cancel()
    }

    class IMMAssetCalibration {
        <<DocType controller>>
        +asset: Link
        +calibration_type: str
        +status: str
        +overall_result: str
        +measurements: list
        +is_recalibration: bool
        +validate()
        +before_submit()
        +on_submit()
        +on_cancel()
    }
    IMMAssetCalibration --|> FrappeDocument

    class IMMCalibrationMeasurement {
        <<DocType child>>
        +parent: Link
        +nominal_value: float
        +measured_value: float
        +out_of_tolerance: bool
        +pass_fail: str
    }
    IMMAssetCalibration "1" *-- "1..*" IMMCalibrationMeasurement

    class Imm11Service {
        <<service module>>
        +create_calibration_schedule_from_commissioning(doc) str
        +create_due_calibration_wos() int
        +handle_calibration_pass(cal_doc) None
        +handle_calibration_fail(cal_doc) None
        +perform_lookback_assessment(device_model, exclude) list
        +create_post_repair_calibration(asset) str
    }

    class Imm11Api {
        <<API module>>
        +create_calibration(**kwargs) dict
        +submit_calibration_results(name, measurements) dict
        +close_capa(name, root_cause) dict
    }
    Imm11Api ..> Imm11Service : delegates

    class Imm00Service {
        <<service module — IMM-00>>
        +transition_asset_status(asset, status) None
        +create_capa(asset, source_type, source_ref) str
        +log_audit_event(...) str
        +create_lifecycle_event(...) str
    }
    Imm11Service ..> Imm00Service : calls
```

## II.2. Layer mapping

```mermaid
flowchart TB
    FE[Vue 3 SPA] -->|REST| API[api/imm11.py]
    API -->|calls| SVC[services/imm11.py]
    SVC -->|calls| IMM00[services/imm00.py]
    SVC -->|insert/update| DOC[IMM Asset Calibration]
    SVC -->|insert| SCH[IMM Calibration Schedule]
    DOC -->|inherits| Frappe[Frappe Document Framework]
    IMM00 -->|writes| CAPA[IMM CAPA Record]
    IMM00 -->|writes| ALE[Asset Lifecycle Event]
    IMM00 -->|writes| AUD[IMM Audit Trail]
```

---

# Phần III — Sequence Diagram

## III.3. Sequence: Submit kết quả Pass

```mermaid
sequenceDiagram
    actor KTV
    participant Browser
    participant API as api.imm11
    participant Svc as services.imm11
    participant Doc as IMMAssetCalibration
    participant Imm00 as services.imm00
    participant DB

    KTV->>Browser: click "Submit"
    Browser->>API: POST submit_calibration_results
    API->>Svc: handle_submit_results(name, measurements)
    Svc->>DB: get IMM Asset Calibration
    DB-->>Svc: doc

    Svc->>Doc: _compute_measurement_results()
    Note over Doc: overall_result = "Passed"
    Doc->>DB: UPDATE measurements + overall_result

    Svc->>Imm00: handle_calibration_pass(doc)
    Imm00->>DB: SET AC Asset.next_calibration_date
    Imm00->>DB: INSERT Asset Lifecycle Event "calibration_completed"
    Imm00->>DB: INSERT IMM Audit Trail (SHA-256)
    Imm00-->>Svc: done

    Svc-->>API: {name, status="Passed", next_calibration_date}
    API-->>Browser: {"success": true, "data": {...}}
```

## III.3. Sequence: Submit kết quả Fail → CAPA + Lookback

```mermaid
sequenceDiagram
    actor KTV
    participant API as api.imm11
    participant Svc as services.imm11
    participant Imm00 as services.imm00
    participant DB

    KTV->>API: POST submit_calibration_results (Fail case)
    API->>Svc: handle_submit_results(name, measurements)
    Svc->>DB: compute → overall_result = "Failed"

    alt overall_result == "Failed"
        Svc->>Imm00: transition_asset_status(asset, "Out of Service")
        Imm00->>DB: UPDATE AC Asset.lifecycle_status
        Imm00->>DB: INSERT Asset Lifecycle Event

        Svc->>Imm00: create_capa(asset, "IMM Asset Calibration", name, "Major")
        Imm00->>DB: INSERT IMM CAPA Record
        Imm00-->>Svc: capa_name

        Svc->>Svc: perform_lookback_assessment(device_model, exclude_asset)
        Svc->>DB: SELECT AC Asset WHERE device_model = X AND status = Active
        DB-->>Svc: [asset_B, asset_C, ...]

        Svc->>DB: UPDATE CAPA lookback_assets + lookback_status
        Svc->>Imm00: create_lifecycle_event("calibration_failed")
        Svc->>Imm00: log_audit_event(...)
        Svc->>DB: send email notification
    end

    Svc-->>API: {name, status="Failed", capa_created, lookback_assets}
    API-->>KTV: {"success": true, "data": {...}}
```

---

# Phần IV — Communication Diagram

## IV.4. Communication: Scheduler daily tạo CAL WO

```
1: trigger daily scheduler
browser:System → :TaskImm11 : 1: create_due_calibration_wos()
:TaskImm11 → :MariaDB : 2: SELECT IMM Calibration Schedule WHERE next_due_date <= today+30
:TaskImm11 → :Imm00Service : 3: validate_asset_for_operations(asset)
:TaskImm11 → :IMMAssetCalibration : 4: insert(draft)
:IMMAssetCalibration → :MariaDB : 4.1: INSERT tabIMM Asset Calibration
:TaskImm11 → :Imm00Service : 5: log_audit_event("calibration_scheduled")
:Imm00Service → :MariaDB : 5.1: INSERT IMM Audit Trail
```

---

# Phần V — Package / Dependency Diagram

## V.2. Backend package diagram

```mermaid
flowchart TB
    subgraph api["api/"]
        ApiImm11["api.imm11"]
    end
    subgraph services["services/"]
        SvcImm11["services.imm11"]
        SvcImm00["services.imm00 — LIVE"]
        SvcShared["services.shared (constants, dto)"]
    end
    subgraph doctype["assetcore/doctype/"]
        DocCal["imm_asset_calibration/"]
        DocSch["imm_calibration_schedule/"]
        DocMeas["imm_calibration_measurement/"]
    end
    subgraph tasks["tasks/"]
        TaskCron["tasks.imm11 (schedulers)"]
    end

    ApiImm11 --> SvcImm11
    SvcImm11 --> SvcImm00
    SvcImm11 --> SvcShared
    SvcImm11 -.-> DocCal
    SvcImm11 -.-> DocSch
    TaskCron --> SvcImm11
    DocCal --> SvcImm11
    DocMeas --> DocCal
```

## V.3. Frontend package diagram

```mermaid
flowchart TB
    subgraph views["views/imm11/"]
        VDash["CalibrationDashboard"]
        VList["CalibrationList"]
        VForm["CalibrationForm"]
        VDetail["CalibrationDetail"]
        VReport["ComplianceReport"]
    end
    subgraph stores["stores/"]
        SImm11["imm11.ts"]
    end
    subgraph components["components/imm11/"]
        MeasTable["MeasurementTable"]
        CertUpload["CertificateUploader"]
        LookbackPanel["LookbackPanel"]
        StatusBadge["CalibrationStatusBadge"]
    end
    subgraph api["api/"]
        ApiClient["imm11.ts"]
    end

    VList --> SImm11
    VForm --> SImm11
    VDetail --> LookbackPanel
    VForm --> MeasTable
    VForm --> CertUpload
    VList --> StatusBadge
    SImm11 --> ApiClient
```

---

## DoD — File 03 hoàn chỉnh

- [x] ERD diagram render Mermaid
- [x] Mọi entity sở hữu có catalog entry
- [x] Data dictionary — 1 bảng riêng per DocType
- [x] Volume + retention đủ
- [x] Class diagram tổng quát đủ 4 layer
- [x] Sequence diagram có happy path + fail path + audit log line
- [x] Package diagram BE + FE
- [ ] ⚠️ Class diagram chi tiết per major class (Pending khi implement)
- [ ] ⚠️ Communication diagram đủ 2 flow (Pending)
- [ ] ⚠️ Reviewed bởi DBA + Tech Lead (Pending)
