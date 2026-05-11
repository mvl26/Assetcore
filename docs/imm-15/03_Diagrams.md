# 03 — Sơ đồ kỹ thuật — IMM-15 Theo dõi tồn kho phụ tùng

> ⚠️ Module PLANNED — Wave 3. AC Inventory Backbone LIVE; IMM transaction layer chưa triển khai.

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-15 — Spare Parts Inventory Tracking |
| Phiên bản | 0.1.0 |
| Ngày | 2026-05-08 |
| Trạng thái | PLANNED |

---

## I. Entity-Relationship Diagram

```mermaid
erDiagram
    %% LIVE DocTypes (AC backbone)
    AC_SPARE_PART {
        string name PK
        string part_code
        string part_name
        string part_category
        string manufacturer
        float min_stock_level
        float max_stock_level
        int shelf_life_months
        boolean is_critical
        boolean is_active
        string imm_part_class
        string imm_abc_class
        string imm_xyz_class
        int imm_lead_time_days
        int imm_safety_stock_days
        boolean imm_traceability_required
        string imm_storage_condition
    }

    AC_SPARE_PART_STOCK {
        string name PK
        string warehouse FK
        string spare_part FK
        float qty_on_hand
        float reserved_qty
        float available_qty
        date last_movement_date
    }

    AC_STOCK_MOVEMENT {
        string name PK
        string movement_type
        string from_warehouse FK
        string to_warehouse FK
        string reference_type
        string reference_name
        float total_value
        int docstatus
    }

    AC_STOCK_MOVEMENT_ITEM {
        string name PK
        string parent FK
        string spare_part FK
        float qty
        float unit_cost
        float total_cost
        string serial_no
    }

    AC_WAREHOUSE {
        string name PK
        string warehouse_code
        string warehouse_name
        string location
        boolean is_active
    }

    %% PLANNED DocTypes (IMM-15 layer)
    IMM_SPARE_ALLOCATION {
        string name PK
        string work_order_ref
        string asset FK
        string warehouse_from FK
        string urgency
        string workflow_state
        string stock_movement_ref FK
        string stock_movement_return_ref FK
        string audit_flags
        int docstatus
    }

    IMM_SPARE_ALLOCATION_ITEM {
        string name PK
        string parent FK
        string spare_part FK
        float qty_requested
        float qty_approved
        float qty_issued
        float qty_returned
        string batch_no
        string serial_no
        string return_condition
    }

    IMM_STOCK_CYCLE_COUNT {
        string name PK
        string warehouse FK
        date count_date
        string count_type
        string counted_by FK
        string verified_by FK
        string workflow_state
        int variance_count
        currency variance_value
        string posted_movement_ref FK
        int docstatus
    }

    IMM_CYCLE_COUNT_ITEM {
        string name PK
        string parent FK
        string spare_part FK
        float system_qty
        float counted_qty
        float variance_qty
        float variance_pct
        string root_cause
        boolean capa_required
        string capa_ref
    }

    IMM_CRITICAL_SPARE_WATCHLIST {
        string name PK
        string critical_asset FK
        string spare_part FK
        float min_required_on_hand
        string warehouse FK
        datetime last_breach_date
        int breach_count_30d
        boolean active
    }

    IMM_SPARE_PART_FORECAST {
        string name PK
        string forecast_period
        date period_start
        date period_end
        string method
        string workflow_state
        string approved_by
        int docstatus
    }

    IMM_SPARE_FORECAST_ITEM {
        string name PK
        string parent FK
        string spare_part FK
        float forecast_qty
        float reorder_point
        float safety_stock
        float current_qty
        float historical_consumption_12m
        string recommended_action
    }

    IMM_SPARE_ALTERNATIVE {
        string name PK
        string parent FK
        string alt_spare_part FK
        int priority
        string notes
    }

    IMM_SPARE_BATCH {
        string name PK
        string spare_part FK
        string batch_no
        date manufacturing_date
        date expiry_date
        string supplier_lot
        string received_movement_ref FK
    }

    AC_ASSET {
        string name PK
        string asset_name
        string status
    }

    IMM_AUDIT_TRAIL {
        string name PK
        string root_doctype
        string root_name
        string actor
        string action
        datetime timestamp
    }

    %% Relationships
    AC_SPARE_PART ||--o{ AC_SPARE_PART_STOCK : "tồn theo kho"
    AC_SPARE_PART ||--o{ IMM_SPARE_ALTERNATIVE : "imm_alternative_parts"
    AC_SPARE_PART ||--o{ IMM_SPARE_BATCH : "lot tracking"

    AC_WAREHOUSE ||--o{ AC_SPARE_PART_STOCK : "chứa"
    AC_WAREHOUSE ||--o{ IMM_SPARE_ALLOCATION : "warehouse_from"
    AC_WAREHOUSE ||--o{ IMM_STOCK_CYCLE_COUNT : "được kiểm kê"
    AC_WAREHOUSE ||--o{ IMM_CRITICAL_SPARE_WATCHLIST : "warehouse"

    AC_STOCK_MOVEMENT ||--o{ AC_STOCK_MOVEMENT_ITEM : "items"
    AC_STOCK_MOVEMENT ||--o| IMM_SPARE_ALLOCATION : "stock_movement_ref"
    AC_STOCK_MOVEMENT ||--o| IMM_STOCK_CYCLE_COUNT : "posted_movement_ref"

    IMM_SPARE_ALLOCATION ||--o{ IMM_SPARE_ALLOCATION_ITEM : "items"
    IMM_SPARE_ALLOCATION ||--o{ IMM_AUDIT_TRAIL : "audit events"

    IMM_STOCK_CYCLE_COUNT ||--o{ IMM_CYCLE_COUNT_ITEM : "items"

    IMM_SPARE_PART_FORECAST ||--o{ IMM_SPARE_FORECAST_ITEM : "items"

    AC_ASSET ||--o{ IMM_CRITICAL_SPARE_WATCHLIST : "critical_asset"
    AC_ASSET ||--o{ IMM_SPARE_ALLOCATION : "asset"
```

---

## II. Class Diagram

```mermaid
classDiagram
    class IMMSpareAllocationController {
        +validate()
        +before_submit()
        +on_submit()
        +on_cancel()
    }

    class IMMStockCycleCountController {
        +validate()
        +on_submit()
    }

    class IMMSparePartForecastController {
        +validate()
        +on_submit()
    }

    class AllocationService {
        +vr_01_wo_link_required(doc) None
        +vr_02_traceability_check_per_item(doc) None
        +vr_05_urgency_enum(doc) None
        +vr_08_return_qty_per_item(doc) None
        +vr_10_override_two_approvers_if_emergency(doc) None
        +vr_13_warehouse_active(doc) None
        +compute_total_value(doc) None
        +create_ac_stock_movement_for_issue(doc) Document
        +cancel_ac_stock_movement(doc) None
        +process_return(doc, return_items) Document
        +check_emergency_override(doc) bool
        +reserve_for_pm(wo_doc) None
        +reserve_for_cm(wo_doc) None
        +reserve_for_repair(repair_doc) None
        +write_audit_trail(doc, action, payload) None
    }

    class CycleCountService {
        +vr_04_variance_capa_per_item(doc) None
        +vr_11_segregation_check(doc) None
        +compute_variance_summary(doc) None
        +snapshot_system_qty(doc) None
        +post_to_ac_stock_movement(doc) Document
        +seed_capa_for_variance(doc) None
        +write_audit_trail(doc, action) None
    }

    class ForecastService {
        +generate_forecast_moving_avg(spare_part, period) dict
        +generate_forecast_pm_driven(spare_part, period) dict
        +generate_forecast_failure_rate(spare_part, period) dict
        +reclassify_abc() None
    }

    class WatchlistService {
        +evaluate_breach() None
        +seed_capa_for_breach(watchlist_entry) None
        +flag_obsolete_on_decommission(asset_doc) None
    }

    class InventoryQueryService {
        +get_available_qty(spare_part, warehouse) float
        +check_part_availability_bulk(parts) dict
    }

    class AuditWriter {
        +log(actor, action, ref, payload) None
    }

    class Imm15API {
        +list_allocations(**kwargs) dict
        +get_allocation(name) dict
        +create_allocation(**kwargs) dict
        +approve_allocation(**kwargs) dict
        +issue_allocation(**kwargs) dict
        +return_items(**kwargs) dict
        +cancel_allocation(**kwargs) dict
        +list_cycle_counts(**kwargs) dict
        +create_cycle_count(**kwargs) dict
        +post_cycle_count(**kwargs) dict
        +list_spare_forecasts(**kwargs) dict
        +generate_spare_forecast(**kwargs) dict
        +approve_forecast(**kwargs) dict
        +list_watchlist(**kwargs) dict
        +add_to_watchlist(**kwargs) dict
        +remove_from_watchlist(**kwargs) dict
        +get_dashboard_stats(**kwargs) dict
        +get_low_stock_alerts(**kwargs) dict
        +check_part_availability(**kwargs) dict
    }

    class Imm15Tasks {
        +check_low_stock_alerts() None
        +check_critical_spare_breach() None
        +check_expiring_batches() None
        +generate_spare_demand_forecast() None
        +compute_inventory_kpis() None
    }

    class ServiceError {
        +code: ErrorCode
        +message: str
    }

    class ErrorCode {
        <<enumeration>>
        VALIDATION
        BUSINESS_RULE
        BAD_STATE
        CONFLICT
        NOT_FOUND
        FORBIDDEN
        INTERNAL
    }

    IMMSpareAllocationController --> AllocationService : calls
    IMMStockCycleCountController --> CycleCountService : calls
    IMMSparePartForecastController --> ForecastService : calls
    Imm15API --> AllocationService : delegates
    Imm15API --> CycleCountService : delegates
    Imm15API --> ForecastService : delegates
    Imm15API --> WatchlistService : delegates
    Imm15API --> InventoryQueryService : delegates
    Imm15Tasks --> AllocationService : delegates
    Imm15Tasks --> WatchlistService : delegates
    Imm15Tasks --> ForecastService : delegates
    AllocationService --> AuditWriter : uses
    CycleCountService --> AuditWriter : uses
    AllocationService --> ServiceError : raises
    CycleCountService --> ServiceError : raises
    ServiceError --> ErrorCode : uses
```

---

## III. Sequence Diagrams

### III.1 Luồng Issue Allocation → AC Stock Movement

```mermaid
sequenceDiagram
    actor BIO as Biomed Technician
    actor WL as Workshop Lead
    actor SK as Storekeeper
    participant API as imm15.py API
    participant SVC as AllocationService
    participant INV as inventory.py (LIVE)
    participant DB as MariaDB
    participant AUDIT as IMM Audit Trail

    BIO->>API: POST create_allocation {work_order_ref, asset, items}
    API->>SVC: vr_01_wo_link_required(doc)
    API->>SVC: vr_13_warehouse_active(doc)
    API->>DB: Insert IMM Spare Allocation (Requested)
    API-->>BIO: {success: true, data: {name: "SAL-2026-00045"}}

    WL->>API: POST approve_allocation {name: "SAL-2026-00045"}
    API->>SVC: check role IN _APPROVE_ALLOCATION_ROLES
    API->>DB: workflow_state = "Approved"
    API-->>WL: {success: true, data: {state: "Approved"}}

    SK->>API: POST issue_allocation {name: "SAL-2026-00045"}
    API->>INV: get_available_qty(spare_part, warehouse)
    INV-->>API: available_qty = 5
    API->>SVC: vr_03_stock_sufficient → pass (qty=2 ≤ 5)
    API->>SVC: create_ac_stock_movement_for_issue(doc)
    SVC->>DB: new AC Stock Movement (movement_type=Issue, reference_type=IMM Spare Allocation)
    SVC->>DB: sm.submit() → apply_stock_movement() → qty_on_hand -= 2
    SVC->>DB: allocation.stock_movement_ref = sm.name
    SVC->>AUDIT: log(actor=SK, action=ISSUED, ref=SAL-2026-00045)
    DB-->>SVC: saved
    API-->>SK: {success: true, data: {state: "Issued", stock_movement_ref: "AC-SM-2026-00234"}}
```

### III.2 Luồng Cycle Count → Posted

```mermaid
sequenceDiagram
    actor SK as Storekeeper
    actor WL as Workshop Lead
    participant API as imm15.py API
    participant SVC as CycleCountService
    participant INV as inventory.py (LIVE)
    participant DB as MariaDB

    Note over SK,DB: Cycle Count CYC-2026-00012 ở trạng thái Counting

    SK->>API: POST (update counted_qty for items)
    API->>SVC: vr_04_variance_capa_per_item(doc)
    SVC->>SVC: variance_pct = (8-10)/10 × 100 = 20%
    SVC->>SVC: 20% > threshold 5% → capa_required=1
    Note over API,DB: root_cause bắt buộc cho items variance > 5%

    SK->>API: POST (nhập root_cause=Mis-issue cho item SP-BATTERY-001)
    API->>DB: save cycle count

    WL->>API: POST transition Reviewed
    API->>SVC: vr_11_segregation_check → verified_by ≠ counted_by ✓
    API->>DB: workflow_state = "Reviewed"

    WL->>API: POST post_cycle_count {name: "CYC-2026-00012"}
    API->>SVC: post_to_ac_stock_movement(doc)
    SVC->>DB: new AC Stock Movement (Adjustment, reference_type=IMM Stock Cycle Count)
    SVC->>DB: sm.submit() → apply_stock_movement() → qty_on_hand = counted_qty
    SVC->>SVC: seed_capa_for_variance(doc)
    SVC->>DB: Create IMM CAPA records for variance items
    SVC->>DB: allocation.posted_movement_ref = sm.name
    API-->>WL: {success: true, data: {state: "Posted", adjustment_ref: "AC-SM-2026-00235"}}
```

### III.3 Luồng Watchlist Breach Alert

```mermaid
sequenceDiagram
    participant SCHED as Scheduler (Daily 02:30)
    participant SVC as WatchlistService
    participant INV as inventory.py (LIVE)
    participant DB as MariaDB
    participant EMAIL as Email System
    participant CAPA as IMM CAPA (IMM-16)

    SCHED->>SVC: check_critical_spare_breach()
    SVC->>DB: SELECT * FROM IMM Critical Spare Watchlist WHERE active=1
    DB-->>SVC: [entry: asset=AC-ASSET-00045, spare=SP-CIRCUIT-CRITICAL, min=2, wh=WH-01]
    SVC->>INV: get_available_qty(spare=SP-CIRCUIT-CRITICAL, wh=WH-01)
    INV-->>SVC: available_qty=1 (< min=2)
    SVC->>SVC: BREACH DETECTED
    SVC->>DB: watchlist.last_breach_date=now(), watchlist.breach_count_30d += 1
    SVC->>DB: Check: existing open CAPA for (spare, asset)?
    DB-->>SVC: No open CAPA
    SVC->>CAPA: seed_capa_for_breach(watchlist_entry)
    SVC->>EMAIL: sendmail(to=[Workshop Lead, Operations Manager, System Admin], template="critical_breach")
    SVC-->>SCHED: done — 1 breach processed
```

---

## IV. Communication Diagram (Cross-module)

```
IMM-08 (PM Work Order)
  │  [hook] before_submit → allocation_service.reserve_for_pm(wo_doc)
  │  → Tạo IMM Spare Allocation (Requested) với items từ imm_planned_spares
  └──────────────────────────────────► IMM-15 Spare Allocation

IMM-09 (Repair Work Order)
  │  [hook] before_submit → allocation_service.reserve_for_repair(repair_doc)
  │  → Thin wrapper tạo IMM Spare Allocation từ Spare Parts Used child
  └──────────────────────────────────► IMM-15 Spare Allocation

IMM-12 (CM Work Order)
  │  [Emergency path] urgency=Emergency → bypass VR-15-03 double-approval
  └──────────────────────────────────► IMM-15 Spare Allocation (Emergency)

IMM-13 / IMM-14 (Decommission)
  │  [hook] AC Asset.status=Decommissioned
  │  → watchlist_service.flag_obsolete_on_decommission(asset_doc)
  │  → AC Spare Part.imm_obsolete_review_required = 1
  └──────────────────────────────────► IMM-15 (AC Spare Part CF)

IMM-15 (Stock Movement submitted)
  │  [data] AC Stock Movement (Issue/Receipt/Adjustment)
  │  → AC Spare Part Stock.qty_on_hand updated via apply_stock_movement()
  └──────────────────────────────────► AC Inventory backbone (LIVE)

IMM-15 (Watchlist breach)
  │  [data] breach_count, accuracy_pct → Compliance KPI
  └──────────────────────────────────► IMM-16 (Compliance Monitoring)

IMM-15 (Forecast)
  │  [data] historical_consumption → failure_rate driven forecast
  │  [data] failure_rate từ IMM-17 → forecast_qty
  └──────────────────────────────────► IMM-17 (Predictive Maintenance)

IMM-15 (Stock accuracy %, breach hours)
  │  [data] KPI snapshot daily → dashboard
  └──────────────────────────────────► IMM-16 Compliance Score

IMM-03 (Vendor Scorecard quarterly)
  │  [data] spare fill rate per vendor → Scorecard dimension "Spare"
  └──────────────────────────────────► IMM-15 → IMM-03 Scorecard pipeline
```

---

## V. Package Diagram

```
assetcore/
│
├── api/
│   ├── inventory.py              ← LIVE (30 endpoints — master/movement)
│   └── imm15.py                  ← PLANNED (~16 endpoints — transaction)
│                                    (create_allocation, approve_allocation,
│                                     issue_allocation, return_items,
│                                     create_cycle_count, post_cycle_count,
│                                     generate_spare_forecast, approve_forecast,
│                                     list_watchlist, add_to_watchlist,
│                                     get_dashboard_stats, check_part_availability)
│
├── services/
│   ├── inventory.py              ← LIVE (get_available_qty, _upsert_stock, check_low_stock)
│   └── imm15.py                  ← PLANNED
│                                    allocation_service.*
│                                    cycle_count_service.*
│                                    forecast_service.*
│                                    watchlist_service.*
│                                    inventory_query.*
│                                    audit_writer.*
│
├── tasks.py                      ← 5 scheduler IMM-15 (PLANNED)
│                                    check_low_stock_alerts (daily 02:00)
│                                    check_critical_spare_breach (daily 02:30)
│                                    check_expiring_batches (daily 03:00, gated)
│                                    generate_spare_demand_forecast (monthly 1st 02:00)
│                                    compute_inventory_kpis (daily 04:00)
│
├── assetcore/
│   ├── doctype/
│   │   ├── [LIVE — AC backbone]/
│   │   │   ├── ac_spare_part/
│   │   │   ├── ac_spare_part_stock/
│   │   │   ├── ac_stock_movement/ (+ item)
│   │   │   ├── ac_warehouse/
│   │   │   └── ac_uom/
│   │   │
│   │   └── [PLANNED — IMM-15 layer]/
│   │       ├── imm_spare_allocation/ (+ item)
│   │       ├── imm_stock_cycle_count/ (+ item)
│   │       ├── imm_spare_part_forecast/ (+ item)
│   │       ├── imm_critical_spare_watchlist/
│   │       ├── imm_spare_alternative/ (child for CF)
│   │       └── imm_spare_batch/ (gated)
│   │
│   ├── workflow/
│   │   ├── imm_15_allocation_workflow.json   ← 6 states / 9 transitions (PLANNED)
│   │   └── imm_15_cycle_count_workflow.json  ← 4 states / 5 transitions (PLANNED)
│   │
│   └── views/inventory/          ← LIVE (11 screens)
│       │   SparePartListView, SparePartDetailView
│       │   StockLevelView, StockMovementListView
│       │   WarehouseListView, UomConversionView ...
│       └── [PLANNED — IMM-15 additional screens]
│           AllocationListView, AllocationDetailView
│           CycleCountListView, CycleCountDetailView
│           WatchlistView, SparePartForecastView
│           Imm15DashboardView
│
├── fixtures/
│   ├── imm15_custom_fields.json  ← 7 CF + IMM Spare Alternative + Property Setter (PLANNED)
│   ├── imm15_workflows.json      ← 2 workflows (PLANNED)
│   └── imm15_critical_watchlist_seed.json  ← Top-50 critical assets (PLANNED)
│
├── patches/
│   └── v3_2_00x/
│       ├── apply_imm15_custom_fields.py
│       ├── deploy_imm15_doctypes.py
│       ├── install_imm15_workflows.py
│       ├── backfill_imm_part_class.py
│       └── seed_watchlist_top50.py
│
└── tests/
    ├── test_imm15_services.py
    ├── test_imm15_api.py
    ├── doctype/imm_spare_allocation/test_imm_spare_allocation.py
    ├── doctype/imm_stock_cycle_count/test_imm_stock_cycle_count.py
    └── doctype/imm_spare_part_forecast/test_imm_spare_part_forecast.py
```
