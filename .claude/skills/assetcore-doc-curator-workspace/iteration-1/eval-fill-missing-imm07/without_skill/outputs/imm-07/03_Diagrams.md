# 03 — Biểu đồ UML (Diagrams)

| Mục | Giá trị |
|---|---|
| Module | IMM-07 — Theo dõi hiệu suất |
| Phạm vi | Per-module |
| Owner | System Analyst + Tech Lead |
| Liên kết | 02 Analysis · 04 Backend · 05 API |

> Bộ biểu đồ UML cho module IMM-07: ERD · Class · Sequence · Communication · Package. Render bằng Mermaid (mặc định) hoặc PlantUML (khi Mermaid không hỗ trợ native).

---

## I. ERD — Entity Relationship Diagram

```mermaid
erDiagram
    AC_ASSET ||--o{ AC_KPI_SNAPSHOT : "has snapshots"
    AC_ASSET ||--o{ AC_REPLACEMENT_SIGNAL : "may trigger"
    AC_ASSET ||--o{ AC_LIFECYCLE_EVENT : "emits events"
    AC_KPI_SNAPSHOT ||--o{ AC_LIFECYCLE_EVENT : "computed from"
    AC_REPLACEMENT_SIGNAL ||--|| AC_KPI_SNAPSHOT : "based on"
    AC_KPI_THRESHOLD_CONFIG ||--o{ AC_REPLACEMENT_SIGNAL : "rule"

    AC_ASSET {
        string name PK
        string asset_name
        string status
        date commissioning_date
        string department
        string model
    }
    AC_KPI_SNAPSHOT {
        string name PK
        link asset FK
        datetime window_start
        datetime window_end
        string granularity "hourly|daily|monthly"
        float availability
        float utilization
        float mtbf_hours
        float mttr_hours
        int repair_count
        int incident_count
        string data_quality "Ok|Stale|Empty|Anomaly"
        string prev_hash
        string hash
    }
    AC_REPLACEMENT_SIGNAL {
        string name PK
        link asset FK
        link triggering_snapshot FK
        string state "Open|Acknowledged|Suppressed|Closed"
        string reason
        datetime raised_at
        datetime acknowledged_at
        link acknowledged_by
    }
    AC_KPI_THRESHOLD_CONFIG {
        string name PK
        string asset_class
        float mtbf_hours_min
        int min_age_years
        int min_repair_count_12m
        int cooldown_days
    }
    AC_LIFECYCLE_EVENT {
        string name PK
        link asset FK
        string event_type
        datetime timestamp
        string root_record
        string actor
    }
```

**Indexes** (đề xuất):
- `AC_KPI_SNAPSHOT (asset, window_start, granularity)` — UNIQUE
- `AC_KPI_SNAPSHOT (window_start)` — range query
- `AC_REPLACEMENT_SIGNAL (asset, state)`
- `AC_LIFECYCLE_EVENT (asset, timestamp)`

---

## II. Class Diagram (service + repo + DTO)

```mermaid
classDiagram
    class KpiService {
        +compute_kpi_snapshot(window: str) dict
        +list_kpi_snapshots(filters, page, page_size) tuple
        +get_kpi_snapshot(name) dict
        +detect_replacement_signal(snapshot) Signal | None
        +acknowledge_signal(name, note) dict
        +verify_chain(asset) tuple
        -_compute_availability(events, window) float
        -_compute_mtbf(events) float
        -_compute_mttr(events) float
        -_apply_threshold_rule(snapshot, config) bool
    }

    class KpiRepo {
        +get(name) Document
        +list(filters, page, page_size) tuple
        +insert_snapshot(payload) Document
        +list_events_for_window(asset, start, end) list
        +last_snapshot(asset, granularity) Document
    }

    class ReplacementSignalRepo {
        +get(name) Document
        +list(filters) list
        +has_open_signal(asset, cooldown_days) bool
        +create(payload) Document
        +update_state(name, new_state, actor) Document
    }

    class KpiSnapshotDTO {
        +name: str
        +asset: str
        +window_start: datetime
        +window_end: datetime
        +availability: float
        +utilization: float
        +mtbf_hours: float
        +mttr_hours: float
        +data_quality: str
    }

    class ReplacementSignalDTO {
        +name: str
        +asset: str
        +state: str
        +reason: str
        +raised_at: datetime
    }

    KpiService --> KpiRepo
    KpiService --> ReplacementSignalRepo
    KpiService ..> KpiSnapshotDTO : returns
    KpiService ..> ReplacementSignalDTO : returns
```

---

## III. Sequence Diagrams

### SEQ-01 — Compute KPI snapshot (UC-01)

```mermaid
sequenceDiagram
    autonumber
    participant Cron as Frappe Scheduler
    participant API as api/imm07.py
    participant SVC as services/imm07.py
    participant REPO as KpiRepo
    participant DB as MariaDB
    participant AUD as audit chain

    Cron->>SVC: compute_kpi_snapshot(window="1h")
    SVC->>REPO: list_active_assets()
    REPO->>DB: SELECT * FROM AC Asset WHERE status='In Use'
    DB-->>REPO: assets[]
    REPO-->>SVC: assets[]
    loop per asset
        SVC->>REPO: list_events_for_window(asset, start, end)
        REPO->>DB: SELECT * FROM AC Lifecycle Event ...
        DB-->>REPO: events[]
        REPO-->>SVC: events[]
        SVC->>SVC: _compute_availability/utilization/mtbf/mttr
        SVC->>AUD: compute_hash(prev_hash, payload)
        AUD-->>SVC: hash
        SVC->>REPO: insert_snapshot({...})
        REPO->>DB: INSERT AC KPI Snapshot
    end
    SVC->>SVC: detect_replacement_signal()
```

### SEQ-02 — Replacement signal raised (UC-02)

```mermaid
sequenceDiagram
    autonumber
    participant SVC as services/imm07.py
    participant CFG as ThresholdConfigRepo
    participant SIG as ReplacementSignalRepo
    participant LCE as LifecycleEventRepo
    participant NOTIFY as Notify (email/in-app)

    SVC->>CFG: get_config(asset_class)
    CFG-->>SVC: config
    SVC->>SVC: _apply_threshold_rule(snapshot, config)
    alt rule matched
        SVC->>SIG: has_open_signal(asset, cooldown)
        SIG-->>SVC: false
        SVC->>SIG: create({asset, snapshot, reason, state="Open"})
        SIG-->>SVC: signal
        SVC->>LCE: emit("replacement_signal_raised", asset, signal)
        SVC->>NOTIFY: send to Trưởng phòng VT-TBYT
    else not matched OR cooldown active
        SVC-->>SVC: skip
    end
```

### SEQ-03 — Load cockpit (UC-05)

```mermaid
sequenceDiagram
    autonumber
    participant FE as Vue Cockpit
    participant API as api/imm07.list_kpi_snapshots
    participant SVC as services/imm07.list_kpi_snapshots
    participant REPO as KpiRepo
    participant DB as MariaDB

    FE->>API: GET ?filters={"site":"S1","date_range":"7d"}&page=1
    API->>API: _parse_json(filters)
    API->>SVC: list_kpi_snapshots(filters, page, 50)
    SVC->>REPO: list(filters, page, page_size)
    REPO->>DB: SELECT ... LIMIT
    DB-->>REPO: rows
    REPO-->>SVC: (rows, total)
    SVC-->>API: {items, total, page}
    API-->>FE: {success: true, data: {...}}
    FE->>FE: render heatmap + cards
```

### SEQ-04 — Verify hash chain (UC-08)

```mermaid
sequenceDiagram
    autonumber
    participant AUD as Auditor
    participant API as api/imm07.verify_chain
    participant SVC as services/imm07.verify_chain
    participant REPO as KpiRepo

    AUD->>API: POST verify_chain(asset="A1")
    API->>SVC: verify_chain("A1")
    SVC->>REPO: list snapshots ordered by window_start
    REPO-->>SVC: snapshots[]
    loop each snapshot
        SVC->>SVC: recompute_hash(prev, payload) == stored hash?
    end
    alt all match
        SVC-->>API: (true, None)
    else broken
        SVC-->>API: (false, broken_at_name)
    end
    API-->>AUD: {success: true, data: {valid: bool, broken_at: ...}}
```

---

## IV. Communication Diagram

```plantuml
@startuml
object "Scheduler" as SCH
object "api/imm07" as API
object "services/imm07" as SVC
object "KpiRepo" as KREPO
object "ReplacementSignalRepo" as SREPO
object "AC KPI Snapshot (DB)" as DB1
object "AC Replacement Signal (DB)" as DB2
object "Lifecycle Event" as LCE
object "Notify" as NTF
object "FE Cockpit" as FE

SCH --> SVC : 1: compute_kpi_snapshot()
SVC --> KREPO : 2: list_events / insert_snapshot
KREPO --> DB1 : 3: SQL
SVC --> SREPO : 4: create signal
SREPO --> DB2 : 5: INSERT
SVC --> LCE : 6: emit event
SVC --> NTF : 7: notify Trưởng phòng
FE --> API : 8: list_kpi_snapshots
API --> SVC : 9: delegate
@enduml
```

---

## V. Package Diagram

```plantuml
@startuml
package "frontend/src" {
    package "views/imm07" {
        component "PerformanceCockpit.vue"
        component "AssetDrillDown.vue"
        component "ReplacementSignalList.vue"
    }
    package "stores" {
        component "imm07Store (Pinia)"
    }
    package "api" {
        component "imm07.ts"
    }
    package "types" {
        component "imm07.ts"
    }
}

package "assetcore" {
    package "api" {
        component "imm07.py"
    }
    package "services" {
        component "imm07.py"
        component "shared/constants.py"
        component "shared/errors.py"
        component "lifecycle.py"
    }
    package "repositories" {
        component "kpi_repo.py"
        component "replacement_signal_repo.py"
    }
    package "doctype" {
        component "AC KPI Snapshot"
        component "AC Replacement Signal"
        component "AC KPI Threshold Config"
    }
    package "patches" {
        component "v1/00x_imm07_init.py"
    }
}

"PerformanceCockpit.vue" --> "imm07Store (Pinia)"
"imm07Store (Pinia)" --> "imm07.ts"
"imm07.ts" --> "imm07.py"
"api/imm07.py" --> "services/imm07.py"
"services/imm07.py" --> "kpi_repo.py"
"services/imm07.py" --> "replacement_signal_repo.py"
"services/imm07.py" --> "lifecycle.py"
@enduml
```

---

## DoD — File 03

- [x] ERD vẽ đủ entity + index đề xuất
- [x] Class diagram service + repo + DTO
- [x] ≥ 1 sequence per UC chính (đã có 4)
- [x] Communication diagram tổng quan
- [x] Package diagram FE + BE
- [ ] Reviewed bởi Tech Lead + System Analyst
