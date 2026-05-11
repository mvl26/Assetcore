# IMM-15 — Technical Design

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-15 — Spare Parts Inventory Tracking |
| Phiên bản | 0.2 (aligned với AC inventory backbone) |
| Ngày cập nhật | 2026-05-04 |
| Trạng thái | PARTIAL — backbone LIVE, IMM transaction layer PLANNED |
| Tác giả | AssetCore Team |

---

## 1. Overview

### 1.1 Layered architecture

```
Request (HTTP / Workflow Action / Scheduler / IMM-08/09/12 hook)
    │
    ▼
API Layer
    ├─ assetcore/api/inventory.py      (LIVE — 30 endpoints master/movement)
    └─ assetcore/api/imm15.py          (PLANNED — ~16 endpoints transaction)
    │   @frappe.whitelist()  →  _ok() / _err()
    ▼
Service Layer
    ├─ assetcore/services/inventory.py (LIVE — get_available_qty, validate/apply/reverse_stock_movement, check_low_stock, _upsert_stock)
    └─ assetcore/services/imm15.py     (PLANNED — allocation_service, cycle_count_service, forecast_service, watchlist_service, audit_writer)
    ▼
Controller (DocType .py)
    ├─ ac_spare_part.py / ac_spare_part_stock.py / ac_stock_movement.py / ac_warehouse.py  (LIVE)
    └─ imm_spare_allocation.py / imm_stock_cycle_count.py / imm_spare_part_forecast.py     (PLANNED)
    ▼
Frappe ORM → MariaDB
    │   tabAC Spare Part, tabAC Spare Part Stock, tabAC Stock Movement (+ Item),
    │   tabAC Warehouse, tabAC UOM, tabIMM Device Spare Part, tabSpare Parts Used   (LIVE)
    │   tabIMM Spare Allocation (+ Item), tabIMM Stock Cycle Count (+ Item),
    │   tabIMM Spare Part Forecast (+ Item), tabIMM Critical Spare Watchlist,
    │   tabIMM Spare Alternative, tabIMM Spare Batch (gated)                         (PLANNED)
    ▼
Side effects:
  - AC Stock Movement (Issue / Receipt / Adjustment) submitted = audit evidence
  - AC Spare Part Stock cập nhật qua services.inventory._upsert_stock (atomic)
  - IMM Audit Trail (mọi action)
  - Frappe Version (auto, track_changes=1)
  - Email Notification (low-stock, breach, expiring)
```

> **RULE-F01:** KHÔNG tạo DocType "Spare Item" mới — luôn dùng `AC Spare Part`.
> **RULE-F02:** KHÔNG tạo bảng tồn song song — luôn đọc/ghi qua `AC Spare Part Stock` (`services.inventory._upsert_stock`) hoặc submit `AC Stock Movement`.
> **RULE-F03:** Mọi movement phải sinh `AC Stock Movement` submitted.
> **RULE-F04:** IMM-15 transaction DocType chỉ LINK tới `AC Stock Movement` qua `stock_movement_ref`; KHÔNG ghi trực tiếp `AC Spare Part Stock`.
> **RULE-S01:** Logic nghiệp vụ ở `services/imm15.py`, KHÔNG ở controller (CLAUDE.md §15).

### 1.2 Files

| File | Vai trò | Status |
|---|---|---|
| `assetcore/assetcore/doctype/ac_spare_part/*.{json,py}` | Master phụ tùng | **LIVE** |
| `assetcore/assetcore/doctype/ac_spare_part_stock/*.{json,py}` | Bảng tồn | **LIVE** |
| `assetcore/assetcore/doctype/ac_stock_movement/*.{json,py}` (+ Item) | Phiếu giao dịch (submittable) | **LIVE** |
| `assetcore/assetcore/doctype/ac_warehouse/*.{json,py}` | Kho | **LIVE** |
| `assetcore/assetcore/doctype/ac_uom/*.{json,py}` | UOM | **LIVE** |
| `assetcore/assetcore/doctype/imm_device_spare_part/*.json` | Recommended spare per Device Model (child) | **LIVE** |
| `assetcore/assetcore/doctype/spare_parts_used/*.json` | Child trong Asset Repair WO | **LIVE** |
| `assetcore/api/inventory.py` (~991 LOC) | 30 REST endpoint master + giao dịch | **LIVE** |
| `assetcore/services/inventory.py` | Service tồn kho (low-stock, available_qty, upsert) | **LIVE** |
| `assetcore/fixtures/imm15_custom_fields.json` | 7 CF + child `IMM Spare Alternative` trên `AC Spare Part` | **PLANNED** |
| `assetcore/assetcore/doctype/imm_spare_allocation/*.{json,py,js}` (+ child Item) | Allocation | **PLANNED** |
| `assetcore/assetcore/doctype/imm_stock_cycle_count/*.{json,py,js}` (+ child Item) | Cycle Count | **PLANNED** |
| `assetcore/assetcore/doctype/imm_spare_part_forecast/*.{json,py}` (+ child Item) | Forecast (part-level) | **PLANNED** |
| `assetcore/assetcore/doctype/imm_critical_spare_watchlist/*.json` | Watchlist | **PLANNED** |
| `assetcore/assetcore/doctype/imm_spare_alternative/*.json` | Alt parts (child for CF) | **PLANNED** |
| `assetcore/assetcore/doctype/imm_spare_batch/*.json` | Lot/expiry tracking (gated) | **PLANNED-G** |
| `assetcore/assetcore/workflow/imm_15_allocation_workflow.json` | 6 states / 9 transitions | **PLANNED** |
| `assetcore/assetcore/workflow/imm_15_cycle_count_workflow.json` | 4 states / 5 transitions | **PLANNED** |
| `assetcore/api/imm15.py` | ~16 REST endpoints transaction | **PLANNED** |
| `assetcore/services/imm15.py` | Business logic IMM-15 | **PLANNED** |
| `assetcore/tasks.py` | 5 scheduler IMM-15 (1 wrap LIVE) | **PLANNED** |

---

## 2. DocType Schema

### 2.1 LIVE — AC backbone (tóm tắt, link JSON)

> Schema đã ổn định ở Wave 1. **Không re-define** ở đây.

| DocType | JSON | Naming | Submittable | Highlights |
|---|---|---|---|---|
| `AC Spare Part` | `assetcore/assetcore/doctype/ac_spare_part/ac_spare_part.json` | `AC-SP-.YYYY.-.####` | No | part_code, part_name, part_category (Electrical/Mechanical/Consumable/Filter/Battery/Sensor/Other), manufacturer, manufacturer_part_no, preferred_supplier, unit_cost, stock_uom, purchase_uom, min_stock_level, max_stock_level, shelf_life_months, uom_conversions (table), is_critical, is_active, specifications |
| `AC Spare Part Stock` | `…/ac_spare_part_stock/ac_spare_part_stock.json` | `field:stock_key` | No | warehouse, spare_part, qty_on_hand, reserved_qty, available_qty, last_movement_date, min_stock_override |
| `AC Stock Movement` | `…/ac_stock_movement/ac_stock_movement.json` | `AC-SM-.YYYY.-.#####` | **Yes** | movement_type (Receipt/Issue/Transfer/Adjustment), from_warehouse, to_warehouse, supplier, reference_type (Asset Repair / PM Work Order / AC Purchase / Manual / **+ IMM Spare Allocation / IMM Stock Cycle Count** mở rộng options khi IMM-15 deploy), reference_name (Dynamic Link), items (table), total_value |
| `AC Stock Movement Item` (child) | `…/ac_stock_movement_item/ac_stock_movement_item.json` | — | — | spare_part, part_name, uom, qty, unit_cost, total_cost, conversion_factor, stock_qty, serial_no |
| `AC Warehouse` | `…/ac_warehouse/ac_warehouse.json` | `AC-WH-{####}` | No | warehouse_code, warehouse_name, location, department, manager, is_active |
| `IMM Device Spare Part` (child) | `…/imm_device_spare_part/imm_device_spare_part.json` | — | — | part_name, manufacturer_part_no, recommended_stock_level (recommended BoM theo IMM Device Model) |
| `Spare Parts Used` (child) | `…/spare_parts_used/spare_parts_used.json` | — | — | item_code (soft-ref), qty, uom, unit_cost, stock_entry_ref (sẽ chứa `AC Stock Movement` name khi IMM-15 deploy) |

> **IMM-15 deploy phải:**
> 1. Thêm option `IMM Spare Allocation`, `IMM Stock Cycle Count` vào field `reference_type` của `AC Stock Movement` (qua patch / Property Setter, không sửa core JSON).
> 2. Đăng ký `IMM Spare Allocation` trong DocType picker của `reference_name` Dynamic Link.

### 2.2 NEW — IMM Spare Allocation (`tabIMM Spare Allocation`)

| Property | Value |
|---|---|
| name | IMM Spare Allocation |
| module | AssetCore |
| autoname | `SAL-.YYYY.-.#####` |
| naming_rule | Naming Series |
| is_submittable | 1 |
| track_changes | 1 |
| title_field | `work_order_ref` |

**Fields:**

#### Section: Liên kết WO & Asset

| # | fieldname | fieldtype | options | reqd | read_only |
|---|---|---|---|:---:|:---:|
| 1 | naming_series | Select | `SAL-.YYYY.-.#####` | * | 1 |
| 2 | workflow_state | Link → Workflow State | — | — | 1 |
| 3 | work_order_doctype | Select | `IMM PM Work Order\nIMM CM Work Order\nAsset Repair` | (cond.) | — |
| 4 | work_order_ref | Dynamic Link → `work_order_doctype` | — | (cond.) | — |
| 5 | asset | Link → `AC Asset` | — | * | — |
| 6 | warehouse_from | Link → `AC Warehouse` | — | * | — |

#### Section: Yêu cầu

| # | fieldname | fieldtype | reqd | default |
|---|---|---|:---:|---|
| 7 | requested_by | Link → User | * | session.user |
| 8 | requested_date | Date | * | today |
| 9 | required_date | Date | — | today + 3 |
| 10 | urgency | Select (Routine/Urgent/Emergency) | * | Routine |
| 11 | allocation_status | Select (Requested/Approved/Picked/Issued/Returned/Cancelled) | * | Requested |

#### Section: Items

| # | fieldname | fieldtype | options |
|---|---|---|---|
| 12 | items | Table → `IMM Spare Allocation Item` | * |
| 13 | total_value | Currency (read_only) | — |

#### Section: Phê duyệt

| # | fieldname | fieldtype |
|---|---|---|
| 14 | approval_required | Check (read_only) |
| 15 | approved_by | Link → User (read_only) |
| 16 | approval_date | Datetime (read_only) |
| 17 | override_approver_2 | Link → User (Emergency, read_only) |
| 18 | override_reason | Small Text |

#### Section: AC Stock Movement Link

| # | fieldname | fieldtype | options | read_only |
|---|---|---|---|:---:|
| 19 | stock_movement_ref | Link → `AC Stock Movement` | — | 1 |
| 20 | stock_movement_return_ref | Link → `AC Stock Movement` | — | 1 |

#### Section: Audit

| # | fieldname | fieldtype |
|---|---|---|
| 21 | notes | Text Editor |
| 22 | audit_flags | Small Text (read_only) |

### 2.3 IMM Spare Allocation Item (child)

| # | fieldname | fieldtype | options | reqd |
|---|---|---|---|:---:|
| 1 | spare_part | Link → `AC Spare Part` (filter: `is_active=1`) | — | * |
| 2 | part_name | Data (fetch_from spare_part.part_name) | — | — |
| 3 | qty_requested | Float | — | * |
| 4 | qty_approved | Float | — | — |
| 5 | qty_issued | Float | — | — |
| 6 | qty_returned | Float | — | — |
| 7 | uom | Link → `AC UOM` (fetch_from spare_part.stock_uom) | — | — |
| 8 | batch_no | Data (cond. khi `IMM Spare Batch` chưa build) hoặc Link → `IMM Spare Batch` (cond.) | — | — |
| 9 | serial_no | Data (cond.) | — | — |
| 10 | unit_value | Currency (fetch_from spare_part.unit_cost) | — | — |
| 11 | line_value | Currency (read_only) | — | — |
| 12 | used_for | Select (Replacement / Test / Calibration / Spare) | — | — |
| 13 | return_condition | Select (Good / Damaged / Used) | — | — |

### 2.4 IMM Stock Cycle Count (`tabIMM Stock Cycle Count`)

| Property | Value |
|---|---|
| autoname | `CYC-.YYYY.-.#####` |
| is_submittable | 1 |
| title_field | `warehouse` |

**Fields:**

| # | fieldname | fieldtype | options | reqd |
|---|---|---|---|:---:|
| 1 | naming_series | Select | `CYC-.YYYY.-.#####` | * |
| 2 | workflow_state | Link → Workflow State | — | — |
| 3 | warehouse | Link → `AC Warehouse` | — | * |
| 4 | count_date | Date | — | * |
| 5 | count_type | Select (Full / ABC_A_Monthly / Cycle / Spot) | — | * |
| 6 | counted_by | Link → User | — | * |
| 7 | verified_by | Link → User | — | — |
| 8 | status | Select (Planned/Counting/Reviewed/Posted) | — | * |
| 9 | items | Table → `IMM Cycle Count Item` | — | * |
| 10 | variance_count | Int (read_only) | — | — |
| 11 | variance_value | Currency (read_only) | — | — |
| 12 | posted_movement_ref | Link → `AC Stock Movement` (read_only) | — | — |
| 13 | notes | Text Editor | — | — |

### 2.5 IMM Cycle Count Item (child)

| # | fieldname | fieldtype | options | reqd |
|---|---|---|---|:---:|
| 1 | spare_part | Link → `AC Spare Part` | — | * |
| 2 | system_qty | Float (snapshot từ `AC Spare Part Stock.qty_on_hand`, read_only sau khi snapshot) | — | — |
| 3 | counted_qty | Float | — | * |
| 4 | variance_qty | Float (read_only) | — | — |
| 5 | variance_pct | Percent (read_only) | — | — |
| 6 | variance_value | Currency (read_only) | — | — |
| 7 | root_cause | Select (Damage/Lost/Mis-issue/System_Error/Found_Extra) | — | (cond.) |
| 8 | capa_required | Check (read_only) | — | — |
| 9 | capa_ref | Link → IMM CAPA (cond.) | — | — |
| 10 | notes | Small Text | — | — |

### 2.6 IMM Spare Part Forecast

> **Lưu ý:** DocType này KHÁC `IMM Demand Forecast` đã có (CATEGORY-level, IMM-01, naming `DF-.YYYY.-.#####`). Đặt tên `IMM Spare Part Forecast` (PART-level) để phân biệt rõ.

| Property | Value |
|---|---|
| autoname | `SFC-.YYYY.-.#####` |
| is_submittable | 1 |
| title_field | `forecast_period` |

**Fields:**

| # | fieldname | fieldtype | options | reqd |
|---|---|---|---|:---:|
| 1 | naming_series | Select | `SFC-.YYYY.-.#####` | * |
| 2 | forecast_period | Data (e.g. "2026-Q3") | — | * |
| 3 | period_start | Date | — | * |
| 4 | period_end | Date | — | * |
| 5 | method | Select (Moving_Avg/PM_Driven/Failure_Rate/Manual) | — | * |
| 6 | workflow_state | Link → Workflow State | — | — |
| 7 | generated_by | Link → User (read_only) | — | — |
| 8 | approved_by | Link → User (read_only) | — | — |
| 9 | items | Table → `IMM Spare Forecast Item` | — | * |

**IMM Spare Forecast Item (child):**

| fieldname | fieldtype | options |
|---|---|---|
| spare_part | Link → `AC Spare Part` | — |
| forecast_qty | Float | — |
| reorder_point | Float | — |
| safety_stock | Float | — |
| current_qty | Float (snapshot từ `AC Spare Part Stock`) | — |
| historical_consumption_12m | Float | — |
| recommended_action | Select (Hold/Reorder/ReduceMin/Obsolete) | — |

### 2.7 IMM Critical Spare Watchlist

| Property | Value |
|---|---|
| autoname | `field:watchlist_name` |
| is_submittable | 0 |

**Fields:**

| fieldname | fieldtype | options | reqd |
|---|---|---|:---:|
| watchlist_name | Data | — | * |
| critical_asset | Link → `AC Asset` | — | * |
| spare_part | Link → `AC Spare Part` (filter: `imm_part_class=Critical`) | — | * |
| min_required_on_hand | Float | — | * |
| warehouse | Link → `AC Warehouse` | — | * |
| last_breach_date | Datetime (read_only) | — | — |
| breach_count_30d | Int (read_only) | — | — |
| active | Check (default 1) | — | — |

### 2.8 IMM Spare Alternative (child for CF `imm_alternative_parts`)

| fieldname | fieldtype | options |
|---|---|---|
| alt_spare_part | Link → `AC Spare Part` | — |
| priority | Int (1 = best) | — |
| notes | Small Text | — |

### 2.9 IMM Spare Batch (gated, build only when traceability_required parts exist)

| Property | Value |
|---|---|
| autoname | `BAT-.YYYY.-.#####` |
| is_submittable | 0 |

| fieldname | fieldtype | options |
|---|---|---|
| spare_part | Link → `AC Spare Part` (reqd, filter `imm_traceability_required=1`) | — |
| batch_no | Data (reqd, unique theo spare_part) | — |
| manufacturing_date | Date | — |
| expiry_date | Date | — |
| supplier_lot | Data | — |
| received_movement_ref | Link → `AC Stock Movement` (read_only) | — |

> Nếu skip `IMM Spare Batch` ở Wave 2: `batch_no` trong Allocation Item dùng làm Data field, audit qua text. `check_expiring_batches` no-op.

---

## 3. Custom Fields trên `AC Spare Part`

File fixture: `assetcore/fixtures/imm15_custom_fields.json`. Chèn qua section break `imm_section_strategic` đặt sau section `section_flags`.

| # | fieldname | fieldtype | options | default | depends_on |
|---|---|---|---|---|---|
| 1 | imm_section_strategic | Section Break | "Phân loại chiến lược (IMM-15)" | — | — |
| 2 | imm_part_class | Select | `Critical\nMajor\nConsumable\nTool` | Major | — |
| 3 | imm_abc_class | Select | `A\nB\nC` | C | — |
| 4 | imm_xyz_class | Select | `X\nY\nZ` | Z | — |
| 5 | imm_lead_time_days | Int | — | 30 | — |
| 6 | imm_safety_stock_days | Int | — | 14 | — |
| 7 | imm_traceability_required | Check | — | 0 | — |
| 8 | imm_storage_condition | Select | `Normal\nCold_Chain\nESD\nHazardous` | Normal | — |
| 9 | imm_alternative_parts | Table | `IMM Spare Alternative` | — | — |
| 10 | imm_obsolete_review_required | Check (set bởi IMM-13/14 hook) | — | 0 | — |

> **KHÔNG thêm** `imm_min_strategic_stock`, `imm_max_strategic_stock`, `imm_oem_part_number`, `imm_shelf_life_months`, `imm_is_medical_spare` — đã có tương đương trên `AC Spare Part`:
> - min/max → `min_stock_level`, `max_stock_level`
> - OEM → `manufacturer_part_no`
> - shelf life → `shelf_life_months`
> - is_medical_spare → tự nhiên (mọi `AC Spare Part` đều là medical spare). Có thể filter qua `is_active`/`part_category`.

---

## 4. Validation Rules

Implement trong service layer + controller `validate()`:

| VR | Method | Trigger | Logic |
|---|---|---|---|
| VR-15-01 | `vr_01_wo_link_required` | `validate` allocation | reqd `work_order_ref` trừ `urgency=Emergency` AND `audit_flags has EMERGENCY_NOWO` |
| VR-15-02 | `vr_02_traceability_check` | `before_submit` allocation item | nếu `AC Spare Part.imm_traceability_required=1` AND `qty_issued>0` → batch_no/serial_no reqd |
| VR-15-03 | `vr_03_stock_sufficient` | `issue_allocation` API | `qty_issued ≤ AC Spare Part Stock.available_qty (FOR UPDATE)`; Emergency + Critical → bypass với double-approval |
| VR-15-04 | `vr_04_variance_capa` | `validate` cycle count | `|var_pct|>5` OR `|var_value|>5_000_000` → reqd `root_cause`, set `capa_required=1` |
| VR-15-05 | `vr_05_urgency_enum` | `validate` allocation | IN {Routine/Urgent/Emergency} |
| VR-15-06 | (deprecated) | — | Đã enforce trong AC Spare Part controller |
| VR-15-07 | `vr_07_reorder_safety` | `validate` forecast item | `reorder_point ≥ safety_stock` |
| VR-15-08 | `vr_08_return_qty` | `validate` allocation item | `qty_returned ≤ qty_issued` |
| VR-15-09 | `vr_09_watchlist_critical` | `validate` watchlist | `AC Spare Part.imm_part_class=Critical` AND `min_required_on_hand>0` |
| VR-15-10 | `vr_10_override_two_approvers` | `issue_allocation` Emergency | `approved_by ≠ override_approver_2`, both IN `_OVERRIDE_ROLES` |
| VR-15-11 | `vr_11_segregation_count` | `validate` cycle count Reviewed | `verified_by ≠ counted_by` |
| VR-15-12 | `vr_12_forecast_method` | `validate` forecast | `method` IN {Moving_Avg/PM_Driven/Failure_Rate/Manual} |
| VR-15-13 | `vr_13_warehouse_active` | `validate` allocation | `AC Warehouse.is_active=1` |

`_OVERRIDE_ROLES = {"IMM Workshop Lead", "IMM Operations Manager", "IMM System Admin"}`
`_VARIANCE_PCT_THRESHOLD = 5.0`
`_VARIANCE_VALUE_THRESHOLD = 5_000_000`

---

## 5. Hooks (Controller lifecycle)

### 5.1 IMM Spare Allocation controller

```python
class IMMSpareAllocation(Document):
    def validate(self):
        from assetcore.services.imm15 import allocation_service
        allocation_service.vr_01_wo_link_required(self)
        allocation_service.vr_05_urgency_enum(self)
        allocation_service.vr_08_return_qty_per_item(self)
        allocation_service.vr_13_warehouse_active(self)
        allocation_service.compute_total_value(self)

    def before_submit(self):
        from assetcore.services.imm15 import allocation_service
        allocation_service.vr_02_traceability_check_per_item(self)
        allocation_service.vr_10_override_two_approvers_if_emergency(self)

    def on_submit(self):
        # Issue path: sinh AC Stock Movement (movement_type=Issue),
        # link reference_type="IMM Spare Allocation", reference_name=self.name
        from assetcore.services.imm15 import allocation_service
        sm = allocation_service.create_ac_stock_movement_for_issue(self)  # creates + submits
        self.db_set("stock_movement_ref", sm.name)
        allocation_service.write_audit_trail(self, action="ISSUED", payload={"movement": sm.name})

    def on_cancel(self):
        from assetcore.services.imm15 import allocation_service
        allocation_service.cancel_ac_stock_movement(self)  # cancel referenced movement
        allocation_service.write_audit_trail(self, action="CANCELLED")
```

### 5.2 IMM Stock Cycle Count controller

```python
class IMMStockCycleCount(Document):
    def validate(self):
        from assetcore.services.imm15 import cycle_count_service
        cycle_count_service.vr_04_variance_capa_per_item(self)
        cycle_count_service.vr_11_segregation_check(self)
        cycle_count_service.compute_variance_summary(self)

    def on_submit(self):  # Posted
        from assetcore.services.imm15 import cycle_count_service
        sm = cycle_count_service.post_to_ac_stock_movement(self)  # movement_type=Adjustment
        self.db_set("posted_movement_ref", sm.name)
        cycle_count_service.write_audit_trail(self, action="POSTED")
        cycle_count_service.seed_capa_for_variance(self)
```

### 5.3 Service layer entry points

`assetcore/services/imm15.py` (PLANNED):

| Module | Functions |
|---|---|
| `allocation_service` | `create_ac_stock_movement_for_issue`, `cancel_ac_stock_movement`, `process_return`, `check_emergency_override`, `reserve_for_pm/cm/repair`, `vr_*` |
| `cycle_count_service` | `post_to_ac_stock_movement`, `snapshot_system_qty`, `seed_capa_for_variance`, `compute_variance` |
| `forecast_service` | `generate_forecast_moving_avg`, `generate_forecast_pm_driven`, `generate_forecast_failure_rate`, `reclassify_abc` |
| `inventory_query` | wrap `services.inventory.get_available_qty`, `check_part_availability_bulk` |
| `watchlist_service` | `evaluate_breach`, `seed_capa_for_breach`, `flag_obsolete_on_decommission` |
| `audit_writer` | `log(actor, action, ref, payload)` |

> Mọi cập nhật `AC Spare Part Stock` phải đi qua `services.inventory._upsert_stock` HOẶC qua submit `AC Stock Movement` (mặc định, vì `apply_stock_movement` là hook on_submit của `AC Stock Movement` và đã có sẵn).

---

## 6. API Layer

Xem `IMM-15_API_Interface.md`. Module Python:

- `assetcore/api/inventory.py` — **LIVE** (30 ep). IMM-15 UI **tái sử dụng** cho master + giao dịch.
- `assetcore/api/imm15.py` — **PLANNED** (~16 ep transaction-level).

Constants quan trọng (PLANNED):

```python
_DOCTYPE_ALLOCATION = "IMM Spare Allocation"
_DOCTYPE_CYCLE = "IMM Stock Cycle Count"
_DOCTYPE_FORECAST = "IMM Spare Part Forecast"
_DOCTYPE_WATCHLIST = "IMM Critical Spare Watchlist"

_APPROVE_ALLOCATION_ROLES = {"IMM Workshop Lead", "IMM Operations Manager", "IMM System Admin"}
_ISSUE_ROLES = {"IMM Storekeeper", "IMM Operations Manager", "IMM System Admin"}
_OVERRIDE_ROLES = {"IMM Workshop Lead", "IMM Operations Manager", "IMM System Admin"}
_FORECAST_APPROVE_ROLES = {"IMM Workshop Lead", "IMM Operations Manager", "IMM System Admin"}

_PART_CLASSES = ("Critical", "Major", "Consumable", "Tool")
_VARIANCE_PCT_THRESHOLD = 5.0
_VARIANCE_VALUE_THRESHOLD = 5_000_000
```

---

## 7. Schedulers

File: `assetcore/tasks.py`

### 7.1 `check_low_stock_alerts()` — Daily 02:00 (extend LIVE)

```
# Extend services.inventory.check_low_stock (LIVE)
For each AC Spare Part WHERE is_active=1 AND min_stock_level>0:
    For each (warehouse, qty_on_hand) IN AC Spare Part Stock:
        If qty_on_hand < (min_stock_override OR min_stock_level):
            If LowStock Alert (spare_part, warehouse, alert_date=today) đã có: skip
            Else: tạo Low-Stock Alert
            Email Storekeeper + Workshop Lead (gom theo warehouse)
        # NEW: nếu spare_part nằm trong IMM Critical Spare Watchlist → also escalate
```

### 7.2 `check_critical_spare_breach()` — Daily 02:30

```
For each Watchlist entry WHERE active=1:
    qty_on_hand = AC Spare Part Stock.qty_on_hand(spare_part, warehouse)
    If qty_on_hand < min_required_on_hand:
        Tạo Critical Breach Alert (idempotent (spare_part, asset, date))
        watchlist.last_breach_date = now()
        watchlist.breach_count_30d += 1
        seed CAPA (link IMM-16) nếu chưa có open CAPA
        Email khẩn Workshop Lead + Operations Manager + System Admin
```

### 7.3 `check_expiring_batches()` — Daily 03:00 (gated)

Chỉ chạy nếu `IMM Spare Batch` đã build & có dữ liệu. Nếu không: log "no-op (gated)" và return.

```
For each milestone IN (90, 60, 30, 0) days:
    Query IMM Spare Batch WHERE expiry_date = today + milestone
    For each batch:
        Idempotent log; milestone=0 → set flag block-issue
        Email Storekeeper + Biomed Engineer
```

### 7.4 `generate_spare_demand_forecast()` — Monthly 1st 02:00

```
quarter = upcoming_quarter()
forecast = new IMM Spare Part Forecast(method="Moving_Avg")
For each AC Spare Part is_active=1:
    consumption_12m = SELECT SUM(qty) FROM AC Stock Movement Item smi
                      JOIN AC Stock Movement sm
                      WHERE sm.movement_type='Issue' AND sm.docstatus=1
                        AND sm.movement_date BETWEEN now-12m AND now
                        AND smi.spare_part = this.spare_part
    fc_qty = avg_monthly * 3
    safety = ceil(lead_time_days/30 * monthly_avg + sigma)
    reorder = safety + lead_time_days/30 * monthly_avg
    append forecast.items
forecast.save()  # Draft
Email Workshop Lead, Operations Manager
```

### 7.5 `compute_inventory_kpis()` — Daily 04:00

Snapshot KPI vào `IMM Inventory KPI Snapshot` (one-row-per-day):

- stock_turnover_year, days_on_hand_avg, stockout_incidents_30d,
  critical_breach_hours_30d, cycle_accuracy_pct (60d window),
  forecast_mape_q (quý gần nhất)

---

## 8. Workflow JSON

### 8.1 `imm_15_allocation_workflow.json`

**States (6):**

| state | doc_status | type |
|---|---|---|
| Requested | 0 | Warning |
| Approved | 0 | Success |
| Picked | 0 | Success |
| Issued | 1 | Success |
| Returned | 1 | Default |
| Cancelled | 2 | Danger |

**Transitions (9):**

| action | from → to | allowed |
|---|---|---|
| Phê duyệt | Requested → Approved | IMM Workshop Lead, IMM Operations Manager, IMM System Admin |
| Pick | Approved → Picked | IMM Storekeeper, IMM System Admin |
| Issue | Picked → Issued | IMM Storekeeper, IMM Operations Manager, IMM System Admin |
| Issue (Emergency) | Requested → Issued | IMM Workshop Lead + IMM Operations Manager (double) |
| Trả phụ tùng | Issued → Returned | IMM Storekeeper |
| Đóng phiếu | Returned → Issued | IMM Storekeeper (nếu còn dùng) |
| Hủy | Requested → Cancelled | IMM Workshop Lead, IMM System Admin |
| Hủy | Approved → Cancelled | IMM Workshop Lead, IMM System Admin |
| Hủy | Picked → Cancelled | IMM Workshop Lead, IMM System Admin |

`workflow_state_field = "workflow_state"`. `is_active = 1`.

### 8.2 `imm_15_cycle_count_workflow.json`

**States (4):**

| state | doc_status | type |
|---|---|---|
| Planned | 0 | Default |
| Counting | 0 | Warning |
| Reviewed | 0 | Success |
| Posted | 1 | Success |

**Transitions (5):**

| action | from → to | allowed |
|---|---|---|
| Bắt đầu đếm | Planned → Counting | IMM Storekeeper, IMM System Admin |
| Hoàn tất đếm | Counting → Reviewed | IMM Workshop Lead, IMM QA Officer, IMM System Admin |
| Sửa đếm lại | Reviewed → Counting | IMM Storekeeper, IMM System Admin |
| Post | Reviewed → Posted | IMM Workshop Lead, IMM Operations Manager, IMM System Admin |
| (force cancel) | Planned → Posted | IMM System Admin only |

---

## 9. Fixtures & hooks.py

### 9.1 Required fixtures

| File | Nội dung |
|---|---|
| `fixtures/imm15_custom_fields.json` | 7 CF + 1 child `IMM Spare Alternative` trên `AC Spare Part` + Property Setter mở rộng `reference_type` của `AC Stock Movement` thêm option `IMM Spare Allocation` / `IMM Stock Cycle Count` |
| `fixtures/imm15_workflows.json` | 2 workflows |
| `fixtures/imm15_critical_watchlist_seed.json` | Seed Watchlist cho TOP-50 critical asset (sau khi IMM-04/05 có dữ liệu) |

### 9.2 hooks.py registration (extend hooks hiện có)

```python
scheduler_events = {
    "daily": [
        # LIVE (Wave 1) — đã có
        "assetcore.services.inventory.check_low_stock",
        # NEW — IMM-15
        "assetcore.tasks.check_low_stock_alerts",          # extend với watchlist escalation
        "assetcore.tasks.check_critical_spare_breach",
        "assetcore.tasks.check_expiring_batches",          # gated
        "assetcore.tasks.compute_inventory_kpis",
    ],
    "monthly": [
        "assetcore.tasks.generate_spare_demand_forecast",
    ]
}

doc_events = {
    "IMM PM Work Order": {
        "before_submit": "assetcore.services.imm15.allocation_service.reserve_for_pm",
    },
    "IMM CM Work Order": {
        "before_submit": "assetcore.services.imm15.allocation_service.reserve_for_cm",
    },
    "Asset Repair": {
        "before_submit": "assetcore.services.imm15.allocation_service.reserve_for_repair",
    },
    "AC Asset": {
        "on_update": "assetcore.services.imm15.watchlist_service.flag_obsolete_on_decommission",
    },
}
```

---

## 10. Database Indexes

| Bảng | Cột | Lý do |
|---|---|---|
| `tabIMM Spare Allocation` | `workflow_state`, `asset`, `work_order_ref`, `warehouse_from` | Filter list, dashboard, by-asset/wo report |
| `tabIMM Spare Allocation` | `stock_movement_ref` | Reverse lookup từ AC Stock Movement |
| `tabIMM Stock Cycle Count` | `warehouse`, `count_date`, `posted_movement_ref` | Filter, trend |
| `tabIMM Critical Spare Watchlist` | `critical_asset`, `spare_part`, `active` | Watchlist lookup, breach scheduler |
| `tabAC Spare Part Stock` (LIVE) | `spare_part`, `warehouse` | Đã có (key field `stock_key` = combo) |

**Composite index (manual SQL, áp khi deploy):**

```sql
CREATE INDEX idx_alc_state_wo
  ON `tabIMM Spare Allocation` (workflow_state, work_order_ref);
CREATE INDEX idx_alc_asset_date
  ON `tabIMM Spare Allocation` (asset, requested_date);
CREATE INDEX idx_cyc_wh_date
  ON `tabIMM Stock Cycle Count` (warehouse, count_date);
CREATE INDEX idx_watch_active_part
  ON `tabIMM Critical Spare Watchlist` (active, spare_part, warehouse);
```

---

## 11. Migration Notes

| Version | Migration cần |
|---|---|
| Wave 1 (LIVE) | `AC Spare Part`, `AC Spare Part Stock`, `AC Stock Movement`, `AC Warehouse`, `AC UOM` đã deploy |
| Wave 2 (PLANNED) | (1) Apply `imm15_custom_fields.json` (7 CF + child + Property Setter mở rộng reference_type); (2) Deploy 6 IMM DocType + 2 child; (3) Apply 2 workflow; (4) Đăng ký scheduler vào `hooks.py`; (5) Seed Watchlist top-50 critical asset; (6) Set `imm_part_class` mặc định cho `AC Spare Part is_active=1` (Critical nếu `is_critical=1`, ngược lại Major) |

**Backfill scripts:**

```python
# Set imm_part_class mặc định
frappe.db.sql("""
  UPDATE `tabAC Spare Part`
  SET imm_part_class = CASE WHEN is_critical=1 THEN 'Critical' ELSE 'Major' END
  WHERE is_active=1 AND (imm_part_class IS NULL OR imm_part_class='')
""")

# Default ABC=C, XYZ=Z
frappe.db.sql("""
  UPDATE `tabAC Spare Part`
  SET imm_abc_class='C', imm_xyz_class='Z'
  WHERE is_active=1 AND (imm_abc_class IS NULL OR imm_abc_class='')
""")
```

Sau migrate, chạy `assetcore.services.imm15.forecast_service.reclassify_abc()` lần đầu (cần ≥ 6 tháng dữ liệu consumption).

---

## 12. ERD

```
┌────────────────┐         ┌────────────────────────────┐
│  AC Asset      │ 1───*   │ IMM Critical Spare         │
│ (IMM-05/04)    │◀────────┤ Watchlist (master)         │
└────────┬───────┘         │   spare_part, min, wh      │
         │                 └──────────────┬─────────────┘
         │                                │ * (spare_part)
         │ 1                              │
         │                                ▼
         │ *                       ┌────────────────────┐
┌────────┴────────────────┐        │   AC Spare Part    │
│ IMM Spare Allocation    │ *──1   │ (LIVE) + 7 imm_*   │
│   work_order_ref (Dyn), │        │   custom fields    │
│   asset, urgency,       │        └────────┬───────────┘
│   stock_movement_ref ──┐│                 │
└────────────┬────────────┘                 │ 1
             │ 1                            │
             │                              │ *
             ▼                              ▼
   ┌──────────────────────────┐    ┌──────────────────────┐
   │ IMM Spare Allocation Item│    │ AC Spare Part Stock  │
   │ spare_part, qty_*,       │    │ (LIVE)               │
   │ batch/serial             │    │ qty_on_hand,         │
   └──────────────────────────┘    │ reserved_qty,        │
             │                      │ available_qty        │
             │ ref                  └──────────┬───────────┘
             ▼                                 ▲
   ┌──────────────────────┐   apply_stock_     │
   │ AC Stock Movement    │   movement (LIVE)  │
   │ (LIVE, submittable)  │ ───────────────────┘
   │ reference_type=      │
   │ "IMM Spare Alloc..." │
   └──────────────────────┘

┌──────────────────────────┐         ┌──────────────────────┐
│ IMM Stock Cycle Count    │ 1───*   │ IMM Cycle Count Item │
│   warehouse, count_date  │─────────┤ system_qty, counted  │
│   posted_movement_ref ──┐│         │ root_cause, capa_ref │
└──────────────────────────┘│        └──────────────────────┘
                            │
                            ▼
                  ┌──────────────────────┐
                  │ AC Stock Movement    │
                  │ (Adjustment)         │
                  │ reference_type=      │
                  │ "IMM Stock Cycle..." │
                  └──────────────────────┘

┌────────────────────────────┐
│ IMM Spare Part Forecast    │ 1───* IMM Spare Forecast Item
│   period, method, items    │       spare_part, fc_qty,
│ (DISTINCT từ IMM Demand    │       reorder, recommended_action
│  Forecast của IMM-01)      │
└────────────────────────────┘
```

---

## 13. State Diagram — Allocation Workflow

```
          ┌───────────┐
          │ Requested │ ◀── create_allocation
          └─────┬─────┘
                │ "Phê duyệt" (Workshop Lead)
                ▼
          ┌──────────┐
          │ Approved │
          └─────┬────┘
                │ "Pick" (Storekeeper)
                ▼
          ┌────────┐
          │ Picked │
          └────┬───┘
               │ "Issue" (Storekeeper)
               │  └─ on_submit creates AC Stock Movement (Issue) submitted
               │  └─ apply_stock_movement → AC Spare Part Stock.qty_on_hand -=
               ▼
          ┌────────┐
          │ Issued │
          └────┬───┘
               │ "Trả phụ tùng" (partial OK)
               ▼
          ┌──────────┐
          │ Returned │ — sinh AC Stock Movement (Receipt) (hoặc to_warehouse=QC Hold nếu Damaged)
          └──────────┘

  Emergency path:
     Requested ──"Issue (Emergency)"──▶ Issued
     Yêu cầu: 2 approver (Workshop Lead + Operations Manager)
              audit_flags = "EMERGENCY_OVERRIDE"

  Cancel path:
     {Requested|Approved|Picked} ──"Hủy"──▶ Cancelled
     (Sau Issued không cancel — phải Return)
```

---

## 14. State Diagram — Cycle Count Workflow

```
       ┌─────────┐
       │ Planned │ ◀── create_cycle_count
       └────┬────┘    (snapshot system_qty từ AC Spare Part Stock)
            │ "Bắt đầu đếm"
            ▼
       ┌──────────┐
       │ Counting │
       └────┬─────┘
            │ "Hoàn tất đếm"
            ▼
       ┌──────────┐         ┌──────────┐
       │ Reviewed │ ◀──"Sửa"┤ Counting │
       └────┬─────┘         └──────────┘
            │ "Post" (Workshop Lead)
            │  └─ on_submit creates AC Stock Movement (Adjustment)
            │  └─ apply_stock_movement → qty_on_hand := counted_qty
            │  └─ seed CAPA cho item capa_required=1
            ▼
       ┌────────┐
       │ Posted │  (terminal)
       └────────┘
```

---

## 15. Testing Strategy

| Test type | Target | Coverage |
|---|---|---|
| Unit (service) | 12 VR + 6 service modules | 90% |
| Unit (controller) | lifecycle hooks 3 DocType | 85% |
| API | ~16 new endpoints (success + error path) + regression cho 30 endpoint LIVE | 100% endpoints mới + critical path LIVE |
| Workflow | 9 + 5 transitions với từng role | 100% |
| Scheduler | 5 jobs idempotent | Manual run + assertion |
| E2E | IMM-08 PM → reserve → issue → return; Emergency override; Cycle count → AC Stock Movement Adjustment; Forecast → reorder list | UAT script |
| Concurrency | Issue allocation song song trên cùng spare_part | `AC Spare Part Stock.qty_on_hand` consistent (FOR UPDATE) |
| Performance | check_part_availability P95 < 300ms | k6 load test |
| Regression (LIVE) | `submit_stock_movement` (LIVE) — verify backward compat khi reference_type mở rộng | smoke test |

Test files (PLANNED):
- `assetcore/assetcore/doctype/imm_spare_allocation/test_imm_spare_allocation.py`
- `assetcore/assetcore/doctype/imm_stock_cycle_count/test_imm_stock_cycle_count.py`
- `assetcore/assetcore/doctype/imm_spare_part_forecast/test_imm_spare_part_forecast.py`
- `tests/test_imm15_services.py`
- `tests/test_imm15_api.py`
