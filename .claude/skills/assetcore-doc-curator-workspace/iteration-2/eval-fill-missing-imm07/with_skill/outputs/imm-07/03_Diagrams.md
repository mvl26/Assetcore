# IMM-07 — Sơ đồ (Diagrams)

| Mục | Giá trị |
|---|---|
| Module | IMM-07 — Theo dõi hiệu suất |
| Trạng thái | Skeleton (BE chưa scaffold — diagram chi tiết bổ sung sau Sprint Wave 3.1) |

## I. ERD (Entity Relationship)

Sơ đồ overview các entity dự kiến của IMM-07. Field detail *(Thiết kế trong Sprint Wave 3)*.

```mermaid
erDiagram
    ASSET ||--o{ PERFORMANCE_RECORD : has
    PERFORMANCE_RECORD ||--o{ DATA_QUALITY_FLAG : may_have
    ASSET ||--o{ REPLACEMENT_SIGNAL : may_emit
    KPI_DEFINITION ||--o{ PERFORMANCE_RECORD : applies
    KPI_DEFINITION ||--o{ KPI_DEFINITION_VERSION : has_versions
    DEPARTMENT ||--o{ ASSET : owns

    ASSET {
        string asset_code
        string department
        string status
    }
    PERFORMANCE_RECORD {
        string record_id
        date period
        decimal availability
        decimal utilization
        decimal mtbf
        decimal mttr
    }
    REPLACEMENT_SIGNAL {
        string signal_id
        string severity
        string status
    }
    KPI_DEFINITION {
        string kpi_code
        string formula_ref
        int active_version
    }
```

*Hình 3.1 — ERD overview IMM-07. Field chi tiết và link tới `AC Asset`, `Department` thực tế xem `04_Backend_Design.md`.*

## II. BPMN — To-Be (swimlane)

```mermaid
flowchart LR
    subgraph IMM_08_09_11_12[IMM-08/09/11/12]
        A[Event: PM done / Repair done / Cal done]
    end
    subgraph Scheduler
        B[Aggregator nightly 02:00]
    end
    subgraph IMM_07[IMM-07 Service]
        C[Tính KPI per asset]
        D[Data Quality Gate]
        E{Vượt ngưỡng?}
        F[Tạo Replacement Signal]
    end
    subgraph Consumers
        G[Dashboard 4 tầng]
        H[IMM-13 Review]
    end

    A -->|repository feed| B
    B --> C --> D --> E
    E -->|Yes| F --> H
    E -->|No| G
    D --> G
```

*Hình 3.2 — BPMN To-Be IMM-07.*

## III. Class diagram (overview)

```mermaid
classDiagram
    class PerformanceAggregatorService {
        +run_nightly()
        +compute_for_asset(asset_id)
    }
    class KpiCalculator {
        +availability(asset, period)
        +mtbf(asset, period)
        +mttr(asset, period)
    }
    class DataQualityGate {
        +flag_missing(record)
        +flag_outlier(record)
    }
    class ReplacementSignalService {
        +evaluate(asset)
        +emit(signal)
    }
    class PerformanceRepo {
        +save(record)
        +load_history(asset, range)
    }

    PerformanceAggregatorService --> KpiCalculator
    PerformanceAggregatorService --> DataQualityGate
    PerformanceAggregatorService --> PerformanceRepo
    PerformanceAggregatorService --> ReplacementSignalService
```

*Hình 3.3 — Class diagram tầng service. Method signature cụ thể *(Thiết kế trong Sprint Wave 3.1)*.*

## IV. Sequence — UC-07-05 Replacement Signal

```mermaid
sequenceDiagram
    participant Sched as Scheduler
    participant Agg as PerformanceAggregator
    participant Repo as PerformanceRepo
    participant Sig as ReplacementSignalService
    participant IMM13 as IMM-13 Inbox

    Sched->>Agg: run_nightly()
    Agg->>Repo: load_history(asset, 12m)
    Repo-->>Agg: records
    Agg->>Sig: evaluate(asset, kpis)
    Sig-->>Agg: signal_or_none
    alt Signal raised
        Sig->>IMM13: notify(signal)
    end
```

*Hình 3.4 — Sequence UC-07-05.*

## V. State machine — Replacement Signal

```mermaid
stateDiagram-v2
    [*] --> Open
    Open --> Acknowledged : PTP xác nhận
    Acknowledged --> Reviewing : IMM-13 mở review
    Reviewing --> Resolved : Quyết định OK
    Reviewing --> Dismissed : False positive
    Resolved --> [*]
    Dismissed --> [*]
```

*Hình 3.5 — State machine Replacement Signal. Workflow JSON chi tiết *(Sprint Wave 3.2)*.*

*(Sequence cho UC-07-01..04, 06 bổ sung khi service được scaffold thật.)*
