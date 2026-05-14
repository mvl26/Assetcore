# 04 — Thiết kế Backend — IMM-15 Theo dõi tồn kho phụ tùng

> ✅ Implemented — Wave 2 (feature/hieuc/wave-2). AC Inventory Backbone LIVE; IMM transaction layer (Allocation / Cycle Count / Forecast / Watchlist) đã merge và đang chờ UAT. Naming series `ac_*` đã được dùng cho master backbone — xem §I.

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-15 — Spare Parts Inventory Tracking |
| Phiên bản | 0.2.0 |
| Ngày | 2026-05-14 |
| Trạng thái | IMPLEMENTED (Wave 2) |

---

## I. DocType Catalog

### I.1 LIVE — AC Backbone (Wave 1, không sửa schema)

| DocType | Naming | Submittable | Status |
|---|---|---|---|
| `AC Spare Part` | `AC-SP-.YYYY.-.####` | No | LIVE |
| `AC Spare Part Stock` | `field:stock_key` | No | LIVE |
| `AC Stock Movement` | `AC-SM-.YYYY.-.#####` | Yes | LIVE |
| `AC Stock Movement Item` | — | — (child) | LIVE |
| `AC Warehouse` | `AC-WH-{####}` | No | LIVE |
| `AC UOM` / `AC UOM Conversion` | — | No | LIVE |
| `IMM Device Spare Part` | — | — (child) | LIVE |
| `Spare Parts Used` | — | — (child) | LIVE |

### I.2 LIVE — IMM-15 Layer (merged Wave 2)

| # | DocType | Naming | Submittable | Mô tả |
|---|---|---|---|---|
| 1 | `IMM Spare Allocation` | `SAL-.YYYY.-.#####` | Yes | Phiếu cấp phát phụ tùng per WO |
| C1 | `IMM Spare Allocation Item` | — | — (child) | Dòng allocation |
| 2 | `IMM Stock Cycle Count` | `CYC-.YYYY.-.#####` | Yes | Phiên kiểm kê |
| C2 | `IMM Stock Cycle Count Item` | — | — (child) | Dòng kiểm kê (folder `imm_stock_cycle_count_item`) |
| 3 | `IMM Spare Part Forecast` | `SFC-.YYYY.-.#####` | Yes | Forecast part-level (≠ IMM Demand Forecast IMM-01) |
| C3 | `IMM Spare Forecast Item` | — | — (child) | Dòng forecast |
| 4 | `IMM Critical Spare Watchlist` | `field:watchlist_name` | No | Mapping critical asset → spare |
| C4 | `IMM Spare Alternative` | — | — (child) | Alt parts (child CF trên AC Spare Part) |
| 5 | `IMM Spare Batch` | `BAT-.YYYY.-.#####` | No | Lot/expiry tracking (gated qua scheduler `check_expiring_batches`) |
| 6 | `IMM Device Spare Part` | — | — (child) | Mapping device → recommended spare |

> Tất cả DocType trên đã có folder JSON dưới `assetcore/assetcore/doctype/imm_*` và service code tương ứng trong `assetcore/services/imm15.py`.

---

## II. Custom Fields trên AC Spare Part

File: `assetcore/fixtures/imm15_custom_fields.json`

Thêm vào section break `imm_section_strategic` sau section `section_flags`:

| # | fieldname | Label | Type | Options | Default | Note |
|---|---|---|---|---|---|---|
| SB | `imm_section_strategic` | Phân loại chiến lược (IMM-15) | Section Break | — | — | — |
| 1 | `imm_part_class` | Hạng phụ tùng | Select | `Critical\nMajor\nConsumable\nTool` | Major | Chi tiết hơn is_critical boolean |
| 2 | `imm_abc_class` | Hạng ABC | Select | `A\nB\nC` | C | Recompute hàng quý |
| 3 | `imm_xyz_class` | Hạng XYZ | Select | `X\nY\nZ` | Z | Phân hạng biến động |
| 4 | `imm_lead_time_days` | Lead time (ngày) | Int | — | 30 | Cho safety stock & forecast |
| 5 | `imm_safety_stock_days` | Safety stock (ngày) | Int | — | 14 | — |
| 6 | `imm_traceability_required` | Bắt buộc truy nguyên | Check | — | 0 | batch_no/serial_no reqd khi issue |
| 7 | `imm_storage_condition` | Điều kiện lưu trữ | Select | `Normal\nCold_Chain\nESD\nHazardous` | Normal | Alert nếu kho không phù hợp |
| 8 | `imm_alternative_parts` | Phụ tùng thay thế | Table | `IMM Spare Alternative` | — | — |
| 9 | `imm_obsolete_review_required` | Cần review obsolete | Check | — | 0 | Set bởi IMM-13/14 hook |

**KHÔNG thêm** các field sau (đã có tương đương trên AC Spare Part):
- `imm_min_strategic_stock` → dùng `min_stock_level`
- `imm_max_strategic_stock` → dùng `max_stock_level`
- `imm_oem_part_number` → dùng `manufacturer_part_no`
- `imm_shelf_life_months` → dùng `shelf_life_months`

---

## III. Field Tables — PLANNED DocTypes

### III.1 IMM Spare Allocation

| Field | Label | Type | Req | Permlevel | Note |
|---|---|---|---|---|---|
| `naming_series` | — | Select | Y | 0 | `SAL-.YYYY.-.#####` |
| `workflow_state` | Trạng thái | Workflow State | Y | 0 | Allocation workflow |
| `work_order_doctype` | Loại WO | Select | C | 0 | IMM PM Work Order / IMM CM Work Order / Asset Repair |
| `work_order_ref` | Work Order | Dynamic Link | C | 0 | Bắt buộc trừ Emergency (VR-15-01) |
| `asset` | Thiết bị | Link → AC Asset | Y | 0 | — |
| `warehouse_from` | Kho xuất | Link → AC Warehouse | Y | 0 | VR-15-13: must be active |
| `requested_by` | Người yêu cầu | Link → User | Y | 0 | Auto: session.user |
| `requested_date` | Ngày yêu cầu | Date | Y | 0 | Auto: today |
| `required_date` | Ngày cần | Date | N | 0 | Default: today + 3 |
| `urgency` | Mức độ khẩn | Select | Y | 0 | Routine/Urgent/Emergency |
| `allocation_status` | Trạng thái | Select | Y | 0 | Mirror workflow_state |
| `items` | Phụ tùng | Table → IMM Spare Allocation Item | Y | 0 | — |
| `total_value` | Tổng giá trị | Currency | N | 0 | Auto |
| `approval_required` | Cần phê duyệt | Check | N | 0 | read-only |
| `approved_by` | Người duyệt | Link → User | N | 0 | read-only |
| `approval_date` | Ngày duyệt | Datetime | N | 0 | read-only |
| `override_approver_2` | Người duyệt Emergency 2 | Link → User | C | 0 | Emergency only; read-only |
| `override_reason` | Lý do override | Small Text | C | 0 | Emergency only |
| `stock_movement_ref` | AC Stock Movement (Issue) | Link → AC Stock Movement | N | 0 | read-only; auto sau Issue |
| `stock_movement_return_ref` | AC Stock Movement (Return) | Link → AC Stock Movement | N | 0 | read-only |
| `notes` | Ghi chú | Text Editor | N | 0 | — |
| `audit_flags` | Audit flags | Small Text | N | 0 | read-only; VD: "EMERGENCY_OVERRIDE" |
| `docstatus` | Doc Status | Int | Y | 0 | 0/1/2 |

### III.2 IMM Spare Allocation Item (child)

| Field | Type | Req | Note |
|---|---|---|---|
| `spare_part` | Link → AC Spare Part (filter: is_active=1) | Y | — |
| `part_name` | Data (fetch_from spare_part.part_name) | N | — |
| `qty_requested` | Float | Y | — |
| `qty_approved` | Float | N | Điền khi Approve |
| `qty_issued` | Float | N | Điền khi Issue |
| `qty_returned` | Float | N | VR-15-08: ≤ qty_issued |
| `uom` | Link → AC UOM (fetch_from spare_part.stock_uom) | N | — |
| `batch_no` | Data / Link → IMM Spare Batch | C | Bắt buộc nếu imm_traceability_required=1 |
| `serial_no` | Data | C | Bắt buộc nếu imm_traceability_required=1 |
| `unit_value` | Currency (fetch_from spare_part.unit_cost) | N | — |
| `line_value` | Currency (read_only) | N | qty_issued × unit_value |
| `used_for` | Select | N | Replacement / Test / Calibration / Spare |
| `return_condition` | Select | C | Good / Damaged / Used (điền khi Return) |

### III.3 IMM Stock Cycle Count

| Field | Label | Type | Req | Note |
|---|---|---|---|---|
| `naming_series` | — | Select | Y | `CYC-.YYYY.-.#####` |
| `workflow_state` | Trạng thái | Workflow State | Y | Cycle Count workflow |
| `warehouse` | Kho | Link → AC Warehouse | Y | — |
| `count_date` | Ngày kiểm kê | Date | Y | — |
| `count_type` | Loại kiểm kê | Select | Y | Full / ABC_A_Monthly / Cycle / Spot |
| `counted_by` | Người kiểm | Link → User | Y | — |
| `verified_by` | Người xác nhận | Link → User | N | VR-15-11: ≠ counted_by |
| `status` | Trạng thái | Select | Y | Planned/Counting/Reviewed/Posted |
| `items` | Phụ tùng | Table → IMM Cycle Count Item | Y | — |
| `variance_count` | Số phụ tùng lệch | Int | N | read-only |
| `variance_value` | Giá trị lệch | Currency | N | read-only |
| `posted_movement_ref` | AC Stock Movement (Adjustment) | Link → AC Stock Movement | N | read-only |
| `notes` | Ghi chú | Text Editor | N | — |
| `docstatus` | Doc Status | Int | Y | 0/1 |

### III.4 IMM Cycle Count Item (child)

| Field | Type | Req | Note |
|---|---|---|---|
| `spare_part` | Link → AC Spare Part | Y | — |
| `system_qty` | Float (read-only) | N | Snapshot từ AC Spare Part Stock tại thời điểm Counting |
| `counted_qty` | Float | Y | Số đếm thực tế |
| `variance_qty` | Float (read-only) | N | counted_qty − system_qty |
| `variance_pct` | Percent (read-only) | N | |variance_qty / system_qty| × 100 |
| `variance_value` | Currency (read-only) | N | variance_qty × unit_cost |
| `root_cause` | Select | C | Damage/Lost/Mis-issue/System_Error/Found_Extra — bắt buộc nếu capa_required |
| `capa_required` | Check (read-only) | N | Auto set nếu variance > threshold |
| `capa_ref` | Link → IMM CAPA | C | Auto sau khi seed CAPA |
| `notes` | Small Text | N | — |

### III.5 IMM Spare Part Forecast

| Field | Label | Type | Req | Note |
|---|---|---|---|---|
| `naming_series` | — | Select | Y | `SFC-.YYYY.-.#####` |
| `forecast_period` | Kỳ dự báo | Data | Y | VD: "2026-Q3" |
| `period_start` | Ngày bắt đầu | Date | Y | — |
| `period_end` | Ngày kết thúc | Date | Y | — |
| `method` | Phương pháp | Select | Y | Moving_Avg/PM_Driven/Failure_Rate/Manual |
| `workflow_state` | Trạng thái | Workflow State | N | Draft/Approved |
| `generated_by` | Người tạo | Link → User | N | read-only |
| `approved_by` | Người duyệt | Link → User | N | read-only |
| `items` | Chi tiết | Table → IMM Spare Forecast Item | Y | — |
| `docstatus` | Doc Status | Int | Y | 0/1 |

### III.6 IMM Spare Forecast Item (child)

| Field | Type | Note |
|---|---|---|
| `spare_part` | Link → AC Spare Part | — |
| `forecast_qty` | Float | Số lượng dự báo cần trong kỳ |
| `reorder_point` | Float | VR-15-07: ≥ safety_stock |
| `safety_stock` | Float | — |
| `current_qty` | Float | Snapshot từ AC Spare Part Stock |
| `historical_consumption_12m` | Float | Tiêu thụ 12 tháng gần nhất |
| `recommended_action` | Select | Hold / Reorder / ReduceMin / Obsolete |

### III.7 IMM Critical Spare Watchlist

| Field | Label | Type | Req | Note |
|---|---|---|---|---|
| `watchlist_name` | Tên | Data | Y | Naming field |
| `critical_asset` | Thiết bị | Link → AC Asset | Y | — |
| `spare_part` | Phụ tùng | Link → AC Spare Part | Y | VR-15-09: phải là Critical |
| `min_required_on_hand` | Tồn tối thiểu | Float | Y | > 0 |
| `warehouse` | Kho | Link → AC Warehouse | Y | — |
| `last_breach_date` | Thời điểm vi phạm cuối | Datetime | N | read-only |
| `breach_count_30d` | Số lần vi phạm 30d | Int | N | read-only |
| `active` | Hoạt động | Check | N | default: 1 |

---

## IV. Service Layer — Function Signatures

File: `assetcore/services/imm15.py`

```python
from __future__ import annotations
import frappe
from frappe import _
from assetcore.services.shared import ServiceError, ErrorCode
from assetcore.utils.helpers import _ok, _err

# --- allocation_service ---

def vr_01_wo_link_required(doc: "Document") -> None:
    """VR-15-01: work_order_ref bắt buộc trừ Emergency + audit-flagged.

    Raises:
        ServiceError(BUSINESS_RULE, "VR-15-01: Cấp phát phụ tùng phải liên kết Work Order")
    """
    ...

def vr_02_traceability_check_per_item(doc: "Document") -> None:
    """VR-15-02: imm_traceability_required=1 → batch_no/serial_no reqd khi issue.

    Raises:
        ServiceError(VALIDATION, "VR-15-02: Phụ tùng {part} yêu cầu số lô/serial")
    """
    ...

def vr_03_stock_sufficient(spare_part: str, warehouse: str, qty: float,
                            is_emergency: bool = False,
                            is_critical: bool = False) -> None:
    """VR-15-03: qty ≤ available_qty; Emergency + Critical → bypass.

    Raises:
        ServiceError(BUSINESS_RULE, "VR-15-03: Tồn kho không đủ — available: {n}")
    """
    ...

def vr_05_urgency_enum(doc: "Document") -> None:
    """VR-15-05: urgency IN {Routine/Urgent/Emergency}.

    Raises:
        ServiceError(VALIDATION, "VR-15-05: Mức độ khẩn cấp không hợp lệ")
    """
    ...

def vr_08_return_qty_per_item(doc: "Document") -> None:
    """VR-15-08: qty_returned ≤ qty_issued per item.

    Raises:
        ServiceError(VALIDATION, "VR-15-08: Số lượng trả không được vượt số đã xuất")
    """
    ...

def vr_10_override_two_approvers_if_emergency(doc: "Document") -> None:
    """VR-15-10: Emergency: 2 khác nhau, cả hai trong _OVERRIDE_ROLES.

    Raises:
        ServiceError(BUSINESS_RULE, "VR-15-10: Emergency override cần 2 người duyệt khác nhau")
    """
    ...

def vr_13_warehouse_active(doc: "Document") -> None:
    """VR-15-13: AC Warehouse.is_active=1.

    Raises:
        ServiceError(VALIDATION, "VR-15-13: Kho {wh} không còn hoạt động")
    """
    ...

def compute_total_value(doc: "Document") -> None:
    """Tính total_value = Σ(qty_issued × unit_value) per item."""
    ...

def create_ac_stock_movement_for_issue(doc: "Document") -> "Document":
    """Tạo và submit AC Stock Movement (movement_type=Issue).

    Args:
        doc: IMM Spare Allocation đang submit

    Returns:
        Document: AC Stock Movement đã submitted

    Side effects:
        - reference_type=IMM Spare Allocation, reference_name=doc.name
        - submit() → apply_stock_movement() → qty_on_hand -=
        - doc.stock_movement_ref = sm.name

    Raises:
        ServiceError(INTERNAL, "Tạo AC Stock Movement thất bại")
    """
    ...

def cancel_ac_stock_movement(doc: "Document") -> None:
    """Cancel AC Stock Movement khi Allocation bị cancel.

    Side effects:
        - AC Stock Movement.cancel() → reverse_stock_movement() → qty_on_hand +=

    Raises:
        ServiceError(BAD_STATE, "Không thể cancel Allocation đã Issued")
    """
    ...

def process_return(doc: "Document", return_items: list) -> "Document":
    """Tạo AC Stock Movement (Receipt) cho Return; Damaged → QC Hold warehouse.

    Returns:
        Document: AC Stock Movement (Receipt) đã submitted
    """
    ...

def check_emergency_override(doc: "Document") -> bool:
    """Kiểm tra double-approval hợp lệ; set audit_flags=EMERGENCY_OVERRIDE."""
    ...

def reserve_for_pm(wo_doc: "Document") -> str:
    """Hook IMM PM Work Order before_submit: tạo IMM Spare Allocation (Requested).

    Args:
        wo_doc: IMM PM Work Order document (imm_planned_spares table)

    Returns:
        str: tên IMM Spare Allocation mới tạo (hoặc None nếu không có spares)
    """
    ...

def reserve_for_repair(repair_doc: "Document") -> str | None:
    """Hook Asset Repair before_submit: thin wrapper tạo Allocation từ Spare Parts Used."""
    ...

def write_audit_trail(doc: "Document", action: str, payload: dict | None = None) -> None:
    """Ghi IMM Audit Trail cho Allocation action."""
    ...


# --- cycle_count_service ---

def vr_04_variance_capa_per_item(doc: "Document") -> None:
    """VR-15-04: variance_pct > 5% hoặc variance_value > 5M → capa_required=1, root_cause reqd."""
    ...

def vr_11_segregation_check(doc: "Document") -> None:
    """VR-15-11: verified_by ≠ counted_by.

    Raises:
        ServiceError(BUSINESS_RULE, "VR-15-11: Người kiểm tra phải khác người kiểm kê")
    """
    ...

def compute_variance_summary(doc: "Document") -> None:
    """Tính variance_qty, variance_pct, variance_value per item; tổng variance_count, variance_value."""
    ...

def snapshot_system_qty(doc: "Document") -> None:
    """Snapshot qty_on_hand từ AC Spare Part Stock vào items.system_qty tại thời điểm Counting."""
    ...

def post_to_ac_stock_movement(doc: "Document") -> "Document":
    """Tạo AC Stock Movement (Adjustment) khi Posted.

    Returns:
        Document: AC Stock Movement submitted
    """
    ...

def seed_capa_for_variance(doc: "Document") -> None:
    """Tạo IMM CAPA (link IMM-16) cho items có capa_required=1."""
    ...


# --- forecast_service ---

def generate_forecast_moving_avg(spare_part: str, period: dict) -> dict:
    """Dự báo Moving Average 3-period cho 1 spare part.

    Args:
        spare_part: tên AC Spare Part
        period: {"year": int, "quarter": int}

    Returns:
        dict: {"forecast_qty": float, "reorder_point": float, "safety_stock": float}
    """
    ...

def reclassify_abc() -> None:
    """Reclassify ABC cho tất cả AC Spare Part dựa trên consumption value 12m.

    Idempotent: re-run không thay đổi nếu dữ liệu không đổi.
    """
    ...


# --- watchlist_service ---

def evaluate_breach() -> None:
    """Scheduler daily: quét Watchlist, phát hiện breach, ghi log, email, seed CAPA."""
    ...

def seed_capa_for_breach(watchlist_entry: "Document") -> None:
    """Tạo IMM CAPA nếu chưa có open CAPA cho (spare, asset)."""
    ...

def flag_obsolete_on_decommission(asset_doc: "Document") -> None:
    """Hook AC Asset.on_update: nếu status=Decommissioned → flag imm_obsolete_review_required."""
    ...


# --- inventory_query ---

def get_available_qty(spare_part: str, warehouse: str) -> float:
    """Wrap services.inventory.get_available_qty.

    Returns:
        float: qty_on_hand - reserved_qty
    """
    ...

def check_part_availability_bulk(parts: list[dict]) -> dict:
    """Kiểm tra khả năng đáp ứng cho nhiều spare parts cùng lúc.

    Args:
        parts: [{"spare_part": str, "warehouse": str, "qty_needed": float}]

    Returns:
        dict: {spare_part: {"available": float, "sufficient": bool}}
    """
    ...
```

---

## V. Controller Hooks

Hooks thực tế đang dùng trong `assetcore/hooks.py` (Wave 2 — flat namespace `assetcore.services.imm15.<fn>`):

```python
# hooks.py — IMM-15 wiring (verified 2026-05-14)

doc_events = {
    "IMM PM Work Order": {
        "before_submit": "assetcore.services.imm15.reserve_for_pm",
        # gate + realtime eval do IMM-16 owns:
        # "validate":  "assetcore.services.imm16.gate_wo_submit",
        # "on_submit": "assetcore.services.imm16.eval_imm08_09_realtime",
    },
    "IMM CM Work Order": {
        "before_submit": "assetcore.services.imm15.reserve_for_repair",
    },
    "AC Asset": {
        "on_update": "assetcore.services.imm15.flag_obsolete_on_decommission",
    },
}

scheduler_events = {
    "daily": [
        "assetcore.services.imm15.check_low_stock_and_alert",
        "assetcore.services.imm15.check_critical_spare_breach",
        "assetcore.services.imm15.check_expiring_batches",       # gated (no-op nếu IMM Spare Batch empty)
        "assetcore.services.imm15.compute_inventory_kpis",
    ],
    "monthly": [
        "assetcore.services.imm15.generate_spare_demand_forecast",
    ],
    # ABC reclassification quarterly (cron)
    "cron": {
        "0 3 1 1,4,7,10 *": ["assetcore.services.imm15.reclassify_abc"],
    },
}
```

> Lưu ý: spec gốc dùng tên module `allocation_service` / `watchlist_service` / `forecast_service` cho clarity. Code thực tế đặt tất cả ở module phẳng `services.imm15` — function name giữ nguyên (`reserve_for_pm`, `reserve_for_repair`, `flag_obsolete_on_decommission`, `reclassify_abc`, …).

---

## VI. Workflow State Machines

### VI.1 IMM Spare Allocation (6 states / 9 transitions)

| From | Action (tiếng Việt) | To | Role |
|---|---|---|---|
| — | (create) | `Requested` | IMM Biomed Technician / IMM Technician |
| `Requested` | Phê duyệt | `Approved` | IMM Workshop Lead / IMM Operations Manager |
| `Approved` | Pick | `Picked` | IMM Storekeeper |
| `Picked` | Issue | `Issued` | IMM Storekeeper (sinh AC Stock Movement) |
| `Requested` | Issue (Emergency) | `Issued` | IMM Workshop Lead + IMM Operations Manager (double) |
| `Issued` | Trả phụ tùng | `Returned` | IMM Storekeeper |
| `Returned` | Đóng phiếu | `Issued` | IMM Storekeeper (nếu còn dùng) |
| `Requested` | Hủy | `Cancelled` | IMM Workshop Lead / IMM System Admin |
| `Approved` | Hủy | `Cancelled` | IMM Workshop Lead / IMM System Admin |
| `Picked` | Hủy | `Cancelled` | IMM Workshop Lead / IMM System Admin |

### VI.2 IMM Stock Cycle Count (4 states / 5 transitions)

| From | Action (tiếng Việt) | To | Role |
|---|---|---|---|
| — | (create) | `Planned` | IMM Storekeeper / IMM System Admin |
| `Planned` | Bắt đầu đếm | `Counting` | IMM Storekeeper |
| `Counting` | Hoàn tất đếm | `Reviewed` | IMM Workshop Lead / IMM QA Officer |
| `Reviewed` | Sửa đếm lại | `Counting` | IMM Storekeeper |
| `Reviewed` | Post | `Posted` | IMM Workshop Lead / IMM Operations Manager (sinh AC Stock Movement Adjustment) |

---

## VII. Schedulers

| Job | File | Lịch | Mô tả |
|---|---|---|---|
| `check_low_stock_alerts` | `tasks.py` | daily 02:00 | Extend LIVE `services.inventory.check_low_stock`; thêm watchlist escalation email |
| `check_critical_spare_breach` | `tasks.py` | daily 02:30 | Quét Watchlist; breach → CAPA seed + email khẩn |
| `check_expiring_batches` | `tasks.py` | daily 03:00 | Gated: chỉ chạy nếu IMM Spare Batch đã build |
| `generate_spare_demand_forecast` | `tasks.py` | monthly 1st 02:00 | Tạo IMM Spare Part Forecast Draft (Moving_Avg default) |
| `compute_inventory_kpis` | `tasks.py` | daily 04:00 | Snapshot KPI: turnover, days-on-hand, stockout, breach, accuracy, MAPE |
| `reclassify_abc` | `services/imm15.py` | cron `0 3 1 1,4,7,10 *` | ABC/XYZ quarterly reclassification |

---

## VIII. Database Indexes

```sql
-- IMM Spare Allocation
CREATE INDEX idx_sal_state_wo ON `tabIMM Spare Allocation` (workflow_state, work_order_ref);
CREATE INDEX idx_sal_asset_date ON `tabIMM Spare Allocation` (asset, requested_date);
CREATE INDEX idx_sal_sm_ref ON `tabIMM Spare Allocation` (stock_movement_ref);

-- IMM Stock Cycle Count
CREATE INDEX idx_cyc_wh_date ON `tabIMM Stock Cycle Count` (warehouse, count_date);
CREATE INDEX idx_cyc_movement ON `tabIMM Stock Cycle Count` (posted_movement_ref);

-- IMM Critical Spare Watchlist
CREATE INDEX idx_watch_active_part ON `tabIMM Critical Spare Watchlist` (active, spare_part, warehouse);
CREATE INDEX idx_watch_asset ON `tabIMM Critical Spare Watchlist` (critical_asset, active);

-- IMM Spare Part Forecast
CREATE INDEX idx_sfc_period ON `tabIMM Spare Part Forecast` (forecast_period, docstatus);
```

---

## IX. Migration Patches

Thứ tự bắt buộc (Wave 3):

```
# patches.txt (Wave 3 section)
assetcore.patches.v3_2_001.apply_imm15_custom_fields
assetcore.patches.v3_2_002.deploy_imm15_doctypes
assetcore.patches.v3_2_003.install_imm15_workflows
assetcore.patches.v3_2_004.extend_ac_stock_movement_reference_type
assetcore.patches.v3_2_005.backfill_imm_part_class
assetcore.patches.v3_2_006.backfill_abc_xyz_defaults
assetcore.patches.v3_2_007.seed_watchlist_top50
```

**Chi tiết:**

| Patch | Mục đích | Risk | Rollback |
|---|---|---|---|
| `apply_imm15_custom_fields` | 7 CF + IMM Spare Alternative + Property Setter trên AC Spare Part | Medium (alter table) | Remove custom fields |
| `deploy_imm15_doctypes` | 5 DocType + 4 child (PLANNED) | Low (new tables) | Drop new tables |
| `install_imm15_workflows` | 2 Workflow JSON | Low | Delete workflow records |
| `extend_ac_stock_movement_reference_type` | Mở rộng reference_type options: thêm IMM Spare Allocation, IMM Stock Cycle Count | Low (Property Setter, không sửa core JSON) | Remove Property Setter |
| `backfill_imm_part_class` | Set imm_part_class: Critical nếu is_critical=1, còn lại Major | Low (UPDATE, no nulls) | Reset to NULL |
| `backfill_abc_xyz_defaults` | Set imm_abc_class=C, imm_xyz_class=Z | Low | Reset |
| `seed_watchlist_top50` | Seed Watchlist top-50 critical assets (sau khi IMM-04/05 có data) | Low (insert) | Delete seeded |
