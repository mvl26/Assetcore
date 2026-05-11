# IMM-15 — Theo dõi tồn kho phụ tùng (Spare Parts Inventory Tracking)

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-15 — Spare Parts Inventory Tracking |
| Phiên bản | 0.3 — re-aligned via WAVE2_ALIGNMENT_BLOCK23 |
| Ngày cập nhật | 2026-05-05 |
| **Source of truth** | **`docs/WAVE2_ALIGNMENT_BLOCK23.md` v1.0.0 — đọc trước**. Ghi đè: naming series là **mã dữ liệu domain** (`SAL-…`, `CYC-…`, `SFC-…`, `BAT-…` — KHÔNG nhúng số module); Property Setter mở rộng `AC Stock Movement.reference_type` (thêm `IMM Spare Allocation`, `IMM Stock Cycle Count`); patches `v3_2.00x`; scheduler quarterly dùng `cron`. |
| Trạng thái | PARTIAL — backbone (AC *) LIVE, transaction layer (IMM *) PLANNED |
| Wave / Block | Wave 2 · Block 3 — Operations & Maintenance |
| Tác giả | AssetCore Team |

> **Phiên bản 0.2 (2026-05-04) — Re-alignment**
> - Bỏ giả định "extend ERPNext core Stock". AssetCore đã có sẵn lớp inventory riêng (`AC Spare Part`, `AC Spare Part Stock`, `AC Stock Movement`, `AC Warehouse`, `AC UOM`) cùng `assetcore/api/inventory.py` (~30 endpoints) và `assetcore/services/inventory.py`.
> - 14 Custom Field "imm_*" trên `Item` được thay bằng 7 Custom Field thật sự cần thêm vào `AC Spare Part` (loại bỏ trùng lặp với field đã có: min/max stock, manufacturer, shelf_life, is_critical…).
> - Quy ước RULE-F01..F03 cập nhật: AC * = lớp extension chính thức; IMM-15 LINK vào AC * (không tạo bảng tồn song song).
> - DocType mới được giữ nguyên về số lượng (6) nhưng schema link sang AC Spare Part / AC Warehouse / AC Stock Movement thay vì Item / Warehouse / Stock Entry / Stock Reconciliation.
> - `IMM Spare Demand Forecast` (part-level, IMM-15) phân biệt rõ với `IMM Demand Forecast` đã có (category-level, dùng cho IMM-01).
> - Numbering BR/VR/TC giữ nguyên — nội dung phụ thuộc vào DocType core đã được dịch sang AC tương đương.

---

## 1. Mục đích

IMM-15 là **module quản lý tồn kho phụ tùng chiến lược** cho thiết bị y tế (HTM). Mục tiêu:

- **Kiểm soát tồn kho phụ tùng chiến lược** (Critical / Major / Consumable / Tool)
- **Truy nguyên cấp phát theo Work Order** (PM IMM-08, Repair IMM-09, CM IMM-12) — không cấp ngoài WO
- **Kiểm kê** (cycle count) định kỳ theo ABC, đối soát chênh lệch và phát sinh CAPA
- **Dự báo nhu cầu** (part-level demand forecast) dựa trên PM schedule + failure rate + moving average
- **Cảnh báo** Critical Spare Watchlist breach + low-stock + expiring batch (nếu bật batch tracking)

| Đặc tính | Nội dung |
|---|---|
| Vai trò trong WHO HTM | Parts & supplies management (HTM 4.5), CMMS support (HTM 5) |
| Liên kết module | IMM-08/09/12 (cấp phát), IMM-13/14 (obsolete review), IMM-16 (compliance), IMM-17 (predictive) |
| Nguyên tắc kiến trúc | **EXTEND lớp AssetCore (`AC *`)** — KHÔNG đụng ERPNext Stock core, KHÔNG tạo bảng tồn song song với `AC Spare Part Stock` |
| Compliance | ISO 13485:2016 §7.5.8, §6.3, WHO HTM 4.5, NĐ 98/2021 |
| Phạm vi audit | Mọi allocation, count, override, exception ghi `IMM Audit Trail` + Frappe Version |

---

## 2. Phạm vi thay đổi vs hệ thống hiện tại

### 2.1 Đã có (reuse — không sửa schema)

**Master & Stock DocType (LIVE):**

| DocType | Vai trò | File JSON |
|---|---|---|
| `AC Spare Part` | Master phụ tùng (part_code, part_name, part_category, manufacturer, manufacturer_part_no, preferred_supplier, unit_cost, stock_uom, purchase_uom, min_stock_level, max_stock_level, shelf_life_months, uom_conversions, is_critical, is_active, specifications). Naming `AC-SP-.YYYY.-.####`. | `assetcore/assetcore/doctype/ac_spare_part/ac_spare_part.json` |
| `AC Spare Part Stock` | Tồn per `(warehouse, spare_part)` — qty_on_hand, reserved_qty, available_qty, last_movement_date, min_stock_override. Tương đương `Bin` của ERPNext nhưng độc lập. | `…/ac_spare_part_stock/ac_spare_part_stock.json` |
| `AC Stock Movement` (submittable) | Phiếu giao dịch: movement_type (Receipt/Issue/Transfer/Adjustment), reference_type + reference_name (Asset Repair / PM Work Order / AC Purchase / Manual), items (table). Naming `AC-SM-.YYYY.-.#####`. | `…/ac_stock_movement/ac_stock_movement.json` |
| `AC Stock Movement Item` (child) | Dòng giao dịch: spare_part, qty, unit_cost, total_cost, conversion_factor, stock_qty, serial_no. | `…/ac_stock_movement_item/ac_stock_movement_item.json` |
| `AC Warehouse` | Kho: warehouse_code, warehouse_name, location, department, manager, is_active. Naming `AC-WH-{####}`. | `…/ac_warehouse/ac_warehouse.json` |
| `AC UOM` + `AC UOM Conversion` | Bảng đơn vị + quy đổi nội bộ. | `…/ac_uom/*` |
| `IMM Device Spare Part` (child trong IMM Device Model) | "Recommended spare list" theo model: part_name, manufacturer_part_no, recommended_stock_level. | `…/imm_device_spare_part/imm_device_spare_part.json` |
| `Spare Parts Used` (child trong Asset Repair / IMM-09 WO) | Dòng phụ tùng đã dùng khi sửa: item_code (soft ref), qty, uom, unit_cost, stock_entry_ref. | `…/spare_parts_used/spare_parts_used.json` |

**API & Service đã có (LIVE):**

| File | Nội dung |
|---|---|
| `assetcore/api/inventory.py` (~991 LOC, 30 endpoint) | `list_warehouses`, `get_warehouse`, `create_warehouse`, `update_warehouse`, `delete_warehouse`, `list_spare_parts`, `get_spare_part`, `create_spare_part`, `update_spare_part`, `delete_spare_part`, `search_parts_autocomplete`, `get_stock_overview`, `list_stock_levels`, `list_stock_movements`, `get_stock_movement`, `create_stock_movement`, `submit_stock_movement`, `cancel_stock_movement`, `update_stock_movement`, `delete_stock_movement`, `search_reference_docs`, `get_uom_info`, `convert_qty`, `list_parts_uom`, `list_uoms` / `list_uoms_full`, `get_uom`, `create_uom`, `update_uom`, `delete_uom`, `list_parts_missing_uom`, `update_part_uom`, `bulk_assign_default_uom`, `upsert_uom_conversion`, `remove_uom_conversion`, `seed_ac_uoms`. |
| `assetcore/services/inventory.py` | `get_stock_row`, `get_available_qty`, `get_total_stock`, `_upsert_stock`, `validate_stock_movement`, `apply_stock_movement`, `reverse_stock_movement`, `check_low_stock`, `get_stock_overview`, `search_parts`. |

**Frontend đã có (LIVE) — `frontend/src/views/inventory/`:** `InventoryDashboardView`, `SparePartListView`, `SparePartDetailView`, `StockLevelView`, `StockMovementListView`, `StockMovementDetailView`, `StockMovementCreateView`, `StockMovementEditView`, `WarehouseListView`, `WarehouseDetailView`, `UomConversionView`.

### 2.2 Mở rộng custom field (extend `AC Spare Part`) — fixture mới

Thêm 7 trường (chỉ những field thật sự thiếu so với cần dùng cho IMM-15). KHÔNG trùng lặp với field đã có (`min_stock_level`, `max_stock_level`, `manufacturer_part_no`, `preferred_supplier`, `shelf_life_months`, `is_critical` — reuse).

| # | Field | Kiểu | Mục đích |
|---|---|---|---|
| 1 | `imm_part_class` | Select (Critical/Major/Consumable/Tool) | Phân hạng chiến lược (chi tiết hơn `is_critical` boolean — `is_critical` giữ làm shortcut) |
| 2 | `imm_abc_class` | Select (A/B/C) | Phân hạng giá trị tiêu thụ — recompute hàng quý |
| 3 | `imm_xyz_class` | Select (X/Y/Z) | Phân hạng biến động cầu — recompute hàng quý |
| 4 | `imm_lead_time_days` | Int | Lead time mua hàng (cho safety stock & forecast) |
| 5 | `imm_safety_stock_days` | Int | Số ngày safety stock |
| 6 | `imm_traceability_required` | Check | Bắt buộc batch_no/serial_no khi Issue |
| 7 | `imm_storage_condition` | Select (Normal/Cold_Chain/ESD/Hazardous) | Điều kiện lưu trữ (alert nếu kho không phù hợp) |
| 8 (table) | `imm_alternative_parts` | Table → `IMM Spare Alternative` (child mới) | Phụ tùng thay thế tương đương (`alt_spare_part` Link → AC Spare Part) |

> Fixture: `assetcore/fixtures/imm15_custom_fields.json`. Audit child: `IMM Spare Alternative` (mới, đơn giản: `alt_spare_part` Link → AC Spare Part, `priority`, `notes`).

### 2.3 Thêm mới (new — Wave 2 deliverables)

**6 DocType nghiệp vụ + 2 child:**

| DocType | Loại | Naming | Vai trò |
|---|---|---|---|
| `IMM Spare Allocation` | Transaction (submittable) | `SAL-.YYYY.-.#####` | Phiếu yêu cầu/cấp phát phụ tùng cho 1 Work Order; submit → tạo `AC Stock Movement` (Issue) |
| `IMM Spare Allocation Item` | Child | — | Dòng allocation: `spare_part`, qty_requested/approved/issued/returned, batch_no, serial_no, used_for |
| `IMM Stock Cycle Count` | Transaction (submittable) | `CYC-.YYYY.-.#####` | Phiên kiểm kê (Full/ABC-A Monthly/Cycle/Spot); post → tạo `AC Stock Movement` (Adjustment) |
| `IMM Cycle Count Item` | Child | — | Dòng kiểm kê: spare_part, system_qty (snapshot từ AC Spare Part Stock), counted_qty, variance, root_cause, capa_required |
| `IMM Critical Spare Watchlist` | Master | `field:watchlist_name` | Mapping critical asset → critical spare + min on-hand |
| `IMM Spare Part Forecast` (note: tên rõ để phân biệt `IMM Demand Forecast` của IMM-01) | Snapshot | `SFC-.YYYY.-.#####` | Forecast PART-level theo quý: forecast_qty + reorder_point + safety_stock + recommended_action |
| `IMM Spare Forecast Item` | Child | — | Dòng forecast theo phụ tùng |
| `IMM Spare Alternative` | Child (cho `imm_alternative_parts` trong AC Spare Part) | — | Map alt parts |
| `IMM Spare Batch` | (Optional, gated) | `BAT-.YYYY.-.#####` | Lot/expiry tracking — chỉ build khi có spare bật `imm_traceability_required=1` (giai đoạn 2) |

**2 Workflow mới:**

- `imm_15_allocation_workflow.json`: Requested → Approved → Picked → Issued → Returned (+ Cancelled) — 6 states / 9 transitions
- `imm_15_cycle_count_workflow.json`: Planned → Counting → Reviewed → Posted — 4 states / 5 transitions

**Scheduler mới (đăng ký trong `hooks.py`):**

| Job | Lịch | Ghi chú |
|---|---|---|
| `check_low_stock_alerts` | Daily 02:00 | **Wrap/extend `services.inventory.check_low_stock` đã có**, thêm logic email escalation và linkup với watchlist |
| `check_critical_spare_breach` | Daily 02:30 | Quét `IMM Critical Spare Watchlist` |
| `check_expiring_batches` | Daily 03:00 | Chỉ chạy nếu `IMM Spare Batch` đã build — nếu không, no-op |
| `generate_spare_demand_forecast` | Monthly 1st 02:00 | Tạo `IMM Spare Part Forecast` Draft |
| `compute_inventory_kpis` | Daily 04:00 | Snapshot KPI |

**API mới — `assetcore/api/imm15.py` (~16 endpoint mới):**

`list_allocations`, `get_allocation`, `create_allocation`, `approve_allocation`, `issue_allocation`, `return_items`, `cancel_allocation`, `list_cycle_counts`, `create_cycle_count`, `post_cycle_count`, `list_spare_forecasts`, `generate_spare_forecast`, `approve_forecast`, `list_watchlist`, `add_to_watchlist`, `remove_from_watchlist`, `get_dashboard_stats`, `get_low_stock_alerts`, `get_consumption_by_asset`, `get_consumption_by_wo`, `check_part_availability` (wrap `services.inventory.get_available_qty`).

**Service mới:** `assetcore/services/imm15.py` (allocation_service, cycle_count_service, forecast_service, watchlist_service, audit_writer).

### 2.4 Khác biệt cần ghi chú

| Khái niệm | Đã có | Mới |
|---|---|---|
| Demand Forecast | `IMM Demand Forecast` (CATEGORY-level, IMM-01 procurement, `DF-.YYYY.-.#####`) | `IMM Spare Part Forecast` (PART-level, IMM-15, `SFC-.YYYY.-.#####`) — **không gộp**, hai nghiệp vụ khác nhau |
| Spare child trong Repair WO | `Spare Parts Used` (soft-ref `item_code`) | Khi `IMM Spare Allocation` Issued → cập nhật `stock_entry_ref` field thành `AC Stock Movement` ref; `Spare Parts Used` giữ nguyên cho backward compat |
| "Bin" tồn kho | `AC Spare Part Stock` (đã có) | KHÔNG tạo lại |
| "Stock Entry" | `AC Stock Movement` (đã có) | KHÔNG tạo lại |
| Reserve qty | `AC Spare Part Stock.reserved_qty` (đã có field) | IMM-15 chỉ ghi vào field này (không tạo bảng reserve song song) |

---

## 3. Vị trí trong kiến trúc

```
┌─────────────────────────────────────────────────────────────────────┐
│              Frappe Framework v15 + ERPNext (Asset registry)        │
└──────────────────────────────────┬──────────────────────────────────┘
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          AssetCore App                              │
│                                                                     │
│  ── AC Inventory Backbone (LIVE) ──────────────────────────────┐   │
│  │  AC Spare Part · AC Spare Part Stock · AC Stock Movement   │   │
│  │  AC Warehouse · AC UOM (+ Conversion)                       │   │
│  │  api/inventory.py (30 ep) · services/inventory.py            │   │
│  │  Frontend: views/inventory/ (11 màn hình)                    │   │
│  └──────────────────────────────────┬──────────────────────────┘   │
│                                     ▼  link/ref                    │
│  ── IMM-15 Layer (PLANNED Wave 2) ────────────────────────────┐    │
│  │  Custom Fields trên AC Spare Part: imm_part_class,         │    │
│  │    imm_abc_class, imm_xyz_class, imm_lead_time_days,       │    │
│  │    imm_safety_stock_days, imm_traceability_required,       │    │
│  │    imm_storage_condition, imm_alternative_parts (table)    │    │
│  │                                                            │    │
│  │  Transaction DocTypes:                                     │    │
│  │   • IMM Spare Allocation (+ child)  → AC Stock Movement    │    │
│  │   • IMM Stock Cycle Count (+ child) → AC Stock Movement    │    │
│  │   • IMM Spare Part Forecast (+ child)                      │    │
│  │   • IMM Critical Spare Watchlist                           │    │
│  │   • IMM Spare Batch (optional gated)                       │    │
│  │                                                            │    │
│  │  api/imm15.py (~16 ep mới) · services/imm15.py             │    │
│  │  workflow/imm_15_allocation_workflow.json                  │    │
│  │  workflow/imm_15_cycle_count_workflow.json                 │    │
│  │  schedulers (5)                                            │    │
│  └────────────────────────────────────────────────────────────┘    │
│                                                                     │
│   Tích hợp:                                                         │
│     IMM-08 PM      ──▶ IMM-15  imm_planned_spares (table) + auto   │
│                                IMM Spare Allocation on submit       │
│     IMM-09 Repair  ──▶ IMM-15  thin wrapper request_spare_parts    │
│                                vào allocation flow                  │
│     IMM-12 CM      ──▶ IMM-15  Emergency override path BR-15-03    │
│     IMM-13/14      ──▶ IMM-15  flag obsolete_review_required       │
│     IMM-15 ──▶ IMM-16  scorecard (stock accuracy, breach %)         │
│     IMM-15 ──▶ IMM-17  failure-rate based forecast                  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 4. DocTypes & Custom Fields (tóm tắt — chi tiết Technical Design)

### 4.1 Reuse — AC * (LIVE, không sửa)

| DocType | Status | Note |
|---|---|---|
| `AC Spare Part` | LIVE | Master, đầy đủ field cơ bản; chỉ cần CF mở rộng (§2.2) |
| `AC Spare Part Stock` | LIVE | Bảng tồn per (warehouse, spare_part) — `available_qty = qty_on_hand - reserved_qty` |
| `AC Stock Movement` (+Item) | LIVE | Phiếu giao dịch — `reference_type` đã hỗ trợ Asset Repair / PM Work Order / AC Purchase / Manual |
| `AC Warehouse` | LIVE | Kho |
| `AC UOM` | LIVE | Đơn vị tính |
| `IMM Device Spare Part` | LIVE | Recommended spare per Device Model |
| `Spare Parts Used` | LIVE | Child trong Asset Repair WO |

### 4.2 New — IMM-15 (PLANNED)

| DocType | Naming | Role |
|---|---|---|
| `IMM Spare Allocation` (+ Item) | `SAL-.YYYY.-.#####` | Allocation/reservation request |
| `IMM Stock Cycle Count` (+ Item) | `CYC-.YYYY.-.#####` | Cycle count session |
| `IMM Spare Part Forecast` (+ Item) | `SFC-.YYYY.-.#####` | Part-level forecast (ko trùng `IMM Demand Forecast` IMM-01) |
| `IMM Critical Spare Watchlist` | `field:watchlist_name` | Critical asset → spare mapping |
| `IMM Spare Alternative` (child) | — | Bảng alt parts (cho CF `imm_alternative_parts`) |
| `IMM Spare Batch` (gated) | `BAT-.YYYY.-.#####` | Lot/expiry tracking |

### 4.3 Custom Fields trên `AC Spare Part`

Đã liệt kê đầy đủ tại §2.2. **Không** thêm `imm_min_strategic_stock`, `imm_max_strategic_stock`, `imm_oem_part_number`, `imm_shelf_life_months`, `imm_is_medical_spare` — đã có tương đương trên `AC Spare Part` (`min_stock_level`, `max_stock_level`, `manufacturer_part_no`, `shelf_life_months`, `is_active` + part_category).

---

## 5. Service Functions / API Endpoints (tóm tắt)

### 5.1 Endpoint đã có (`api/inventory.py`) — IMM-15 UI tái sử dụng

`list_spare_parts`, `get_spare_part`, `create_spare_part`, `update_spare_part`, `list_warehouses`, `get_warehouse`, `list_stock_levels`, `get_stock_overview`, `list_stock_movements`, `get_stock_movement`, `create_stock_movement`, `submit_stock_movement`, `cancel_stock_movement`, `search_parts_autocomplete`, `search_reference_docs`, ... (chi tiết §2.1).

### 5.2 Endpoint mới (`api/imm15.py`) — ~16 endpoint

| # | Endpoint | Method | Caller |
|---|---|---|---|
| 1 | `list_allocations` | GET | UI list |
| 2 | `get_allocation` | GET | UI detail |
| 3 | `create_allocation` | POST | UI / IMM-08/09/12 hook |
| 4 | `approve_allocation` | POST | Workshop Head |
| 5 | `issue_allocation` | POST | Storekeeper — sinh `AC Stock Movement` (Issue) |
| 6 | `return_items` | POST | QC gate |
| 7 | `cancel_allocation` | POST | — |
| 8 | `list_cycle_counts` | GET | UI |
| 9 | `create_cycle_count` | POST | snapshot system_qty từ `AC Spare Part Stock` |
| 10 | `post_cycle_count` | POST | Sinh `AC Stock Movement` (Adjustment) |
| 11 | `list_spare_forecasts` | GET | — |
| 12 | `generate_spare_forecast` | POST | Manual trigger |
| 13 | `approve_forecast` | POST | Approve → gợi ý reorder |
| 14 | `list_watchlist` / `add_to_watchlist` / `remove_from_watchlist` | GET/POST | Critical mapping |
| 15 | `get_dashboard_stats`, `get_low_stock_alerts`, `get_consumption_by_asset`, `get_consumption_by_wo` | GET | Reports |
| 16 | `check_part_availability` | GET | IMM-08/09/12 inline check (wrap `services.inventory.get_available_qty`) |

---

## 6. Workflows & Schedulers

### 6.1 `IMM-15 Allocation Workflow` (6 states · 9 transitions)

| State | doc_status | Type | Allow Edit |
|---|---|---|---|
| Requested | 0 | Warning | Biomed/HTM Tech |
| Approved | 0 | Success | Storekeeper |
| Picked | 0 | Success | Storekeeper |
| Issued | 1 | Success | (read-only sau Issue) — đã sinh `AC Stock Movement` |
| Returned | 1 | Default | Storekeeper (partial return) |
| Cancelled | 2 | Danger | — |

### 6.2 `IMM-15 Cycle Count Workflow` (4 states · 5 transitions)

| State | doc_status | Type |
|---|---|---|
| Planned | 0 | Default |
| Counting | 0 | Warning |
| Reviewed | 0 | Success |
| Posted | 1 | Success — sinh `AC Stock Movement` (Adjustment) |

### 6.3 Scheduler — `assetcore/tasks.py`

| Job | Lịch | Status | Hành vi |
|---|---|---|---|
| `check_low_stock_alerts` | Daily 02:00 | NEW (wrap LIVE `services.inventory.check_low_stock`) | So sánh `AC Spare Part Stock.qty_on_hand` vs `AC Spare Part.min_stock_level` → tạo alert + email |
| `check_critical_spare_breach` | Daily 02:30 | NEW | Watchlist breach → red alert + CAPA seed |
| `check_expiring_batches` | Daily 03:00 | NEW (gated) | Quét `IMM Spare Batch` (nếu có); no-op nếu chưa build |
| `generate_spare_demand_forecast` | Monthly 1st 02:00 | NEW | Tạo `IMM Spare Part Forecast` Draft |
| `compute_inventory_kpis` | Daily 04:00 | NEW | Snapshot KPI: turnover, days-on-hand, stock-out |

---

## 7. Roles & Permissions

| Role | AC Spare Part (CF) | Allocation | Cycle Count | Forecast | Watchlist |
|---|---|---|---|---|---|
| IMM Storekeeper | R/W (CF) | R/W/C, Pick, Issue | R/W/C, Count | R | R |
| IMM Workshop Lead | R/W | R/W/C/Cancel/Amend, Approve | R/W/C, Review | R/W, Approve | R/W/C |
| IMM Biomed Technician | R | R/W/C (request) | — | R | R |
| IMM Technician | R | R/W/C (request) | R (count assist) | — | — |
| IMM QA Officer / Auditor | R | R | R, Verify | R | R |
| IMM Operations Manager | R/W | R/W/C/Cancel, Approve | R/W/C, Post | R/W/Approve | R/W |
| IMM System Admin | Full | Full | Full | Full | Full |
| IMM Department Head / Deputy | R | R | R | R | R |

> Tham chiếu role đã định nghĩa trong các DocType `AC *` JSON (xem §2.1).

---

## 8. Business Rules

| ID | Rule | Enforce |
|---|---|---|
| BR-15-01 | Mọi consumption phải link Work Order — không issue ngoài WO trừ Emergency (audit-flagged) | Controller `validate()` allocation |
| BR-15-02 | `imm_traceability_required=1` → batch_no/serial_no bắt buộc khi issue | `before_submit` allocation item |
| BR-15-03 | `qty_issued > AC Spare Part Stock.available_qty` → throw; nếu Emergency và `imm_part_class=Critical` → bypass với double-approval (Workshop Lead + Operations Manager) | `issue_allocation()` |
| BR-15-04 | Critical Watchlist breach → trigger CAPA + email khẩn | Scheduler |
| BR-15-05 | Cycle count variance > 5% hoặc > 5M VND → `capa_required=1`, bắt buộc `root_cause` | VR-15-04 + post handler |
| BR-15-06 | ABC reclassification mỗi quý dựa trên consumption value (12m) | Scheduler quý 1st 03:00 |
| BR-15-07 | Forecast được approve mới được dùng để gợi ý reorder | `approve_forecast()` gate |
| BR-15-08 | Returned items → kiểm tra QC trước khi nhập kho lại (Damaged → kho QC Hold) | Workflow Return |
| BR-15-09 | Asset decommissioned (IMM-13/14) → `AC Spare Part` gắn duy nhất model → flag `imm_obsolete_review_required` | IMM-13 hook |
| BR-15-10 | Audit trail: mọi allocation, count, override, exception ghi `IMM Audit Trail` | Service layer |

---

## 9. Architecture Rules (cập nhật cho AC layer)

| Rule | Nội dung |
|---|---|
| **RULE-F01** | KHÔNG tạo DocType "IMM Spare Item" mới — luôn dùng `AC Spare Part` (đã là lớp extension chính thức). |
| **RULE-F02** | KHÔNG tạo bảng tồn song song — luôn đọc/ghi qua `AC Spare Part Stock` (qua `services.inventory._upsert_stock` hoặc submit `AC Stock Movement`). |
| **RULE-F03** | Mọi movement (Issue/Return/Adjustment) phải sinh `AC Stock Movement` submitted (audit trail của AC layer). |
| **RULE-F04** (mới) | IMM-15 transaction DocType (Allocation, Cycle Count) chỉ LINK vào `AC Stock Movement` qua field `stock_movement_ref`; KHÔNG cập nhật trực tiếp `AC Spare Part Stock`. |
| **RULE-S01** | Logic nghiệp vụ ở `services/imm15.py`, KHÔNG ở controller. |

---

## 10. Dependencies

| Module | Chiều | Liên kết |
|---|---|---|
| AC Inventory backbone | IN | `AC Spare Part`, `AC Spare Part Stock`, `AC Stock Movement`, `AC Warehouse`, `AC UOM` |
| IMM-08 PM | IN | PM WO `imm_planned_spares` table; on submit → auto IMM Spare Allocation Requested |
| IMM-09 Repair | IN | `Spare Parts Used` child + thin wrapper `request_spare_parts` (existing in `services/imm09.py`) gọi vào allocation flow |
| IMM-12 CM | IN | Emergency issue path (BR-15-03 bypass) |
| IMM-13 / IMM-14 | OUT | Obsolete review khi asset retired |
| IMM-16 Compliance | OUT | Stock accuracy %, critical breach hours đóng góp KPI |
| IMM-17 Predictive | BOTH | Failure-rate cho forecast; consumption history về |
| IMM Audit Trail | OUT | Mọi action |

---

## 11. KPIs

| KPI | Công thức | Target |
|---|---|---|
| Stock Turnover (year) | `consumed_value_year / avg_inventory_value` | ≥ 4 |
| Days-on-Hand | `(avg_qty_on_hand / daily_consumption) days` | 30–60 (Critical: 60–90) |
| Stock-out Incidents | Số WO bị block do thiếu spare / tháng | ≤ 2 |
| Critical Breach Hours | Tổng giờ Watchlist breach / tháng | 0 |
| Cycle Count Accuracy % | `1 - sum(|variance_qty|) / sum(system_qty)` | ≥ 98% |
| Forecast MAPE | `mean(|actual - forecast| / actual) × 100` | ≤ 25% |
| Emergency Override Count | Số lần bypass BR-15-03 / tháng | ≤ 3 |
| Spare Cost per Asset | `consumed_value_asset / asset_count` | Trend monitor |

---

## 12. Trạng thái triển khai

| Hạng mục | Trạng thái | Ghi chú |
|---|---|---|
| `AC Spare Part` / `AC Spare Part Stock` / `AC Stock Movement` / `AC Warehouse` / `AC UOM` | **LIVE** | Wave 1 deliverable — backbone |
| `api/inventory.py` (30 ep) | **LIVE** | — |
| `services/inventory.py` | **LIVE** | `check_low_stock` hiện hữu, IMM-15 sẽ extend |
| Frontend `views/inventory/` (11 màn) | **LIVE** | Master + giao dịch — IMM-15 thêm màn Allocation/Cycle Count/Watchlist/Forecast |
| 7 Custom Fields + 1 child trên `AC Spare Part` | **PLANNED** | Wave 2 — fixture `imm15_custom_fields.json` |
| 6 IMM DocType + 2 child mới | **PLANNED** | Wave 2 |
| 2 Workflow (Allocation, Cycle Count) | **PLANNED** | JSON spec sẵn |
| `api/imm15.py` (~16 ep) | **PLANNED** | Wrap inventory.py cho phần master + ep mới cho transaction |
| 5 Scheduler jobs | **PLANNED** | 1 wrap LIVE, 4 mới |
| Frontend mới (Allocation, Cycle Count, Watchlist, Forecast, Dashboard IMM-15) | **PLANNED** | Wave 2 sprint 3-4 |
| Hook IMM-08/09/12 | **PLANNED** | Sau khi IMM-08/09/12 ổn định |
| QMS document set (PR/WI/BM/HS) | **PLANNED** | §13 |
| UAT script | **DRAFT 0.2** | File `IMM-15_UAT_Script.md` |

---

## 13. QMS Mapping

| Yêu cầu | Nguồn | Cách đáp ứng |
|---|---|---|
| Identification & Traceability | ISO 13485 §7.5.8 | `imm_traceability_required` + batch_no/serial_no enforce; Allocation link WO + `AC Stock Movement` |
| Infrastructure | ISO 13485 §6.3 | `imm_storage_condition`, shelf-life alert |
| Parts & Supplies | WHO HTM 4.5 | Critical Spare Watchlist + min stock + lead-time |
| CAPA Trigger | ISO 13485 §8.5 | BR-15-04 (critical breach), BR-15-05 (variance) |
| Audit Trail | ISO 13485 §4.2.5 | `IMM Audit Trail` + Frappe Version + `AC Stock Movement` (submitted) |
| Compliance NĐ98 | NĐ 98/2021 | Spare gắn asset có ĐK lưu hành: kế thừa qua `IMM Device Spare Part` (recommended per model) |

**Document set:**

| Loại | Mã | Tên |
|---|---|---|
| Procedure | PR-IMMIS-15-01 | Quy trình quản lý phụ tùng chiến lược |
| Procedure | PR-IMMIS-15-02 | Quy trình cấp phát phụ tùng theo Work Order |
| Procedure | PR-IMMIS-15-03 | Quy trình kiểm kê chu kỳ |
| Procedure | PR-IMMIS-15-04 | Quy trình dự báo nhu cầu & tái đặt hàng |
| Work Instruction | WI-IMMIS-15-01..05 | HDCV thao tác từng phiên kiểm, allocation, return, override, ABC review |
| Form | BM-IMMIS-15-01 | Biểu mẫu phiếu kiểm kê |
| Record | HS-LOG/REC/REP-IMMIS-15 | Hồ sơ log/record/report tồn kho |
| KPI | KPI-DASH-IMMIS-15 | Dashboard KPI tồn kho |
