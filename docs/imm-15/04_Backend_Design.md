# 04 — Thiết kế Backend — IMM-15 Theo dõi tồn kho phụ tùng

> ✅ Implemented — Wave 2 (feature/hieuc/wave-2). AC Inventory Backbone LIVE; IMM transaction layer (Allocation / Cycle Count / Forecast / Watchlist) đã merge và đang chờ UAT. Naming series `ac_*` đã được dùng cho master backbone — xem §I.

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-15 — Spare Parts Inventory Tracking |
| Phiên bản | 0.0.3 |
| Ngày | 2026-06-03 |
| Trạng thái | IMPLEMENTED (Wave 2) · reservation ledger §III-bis (vòng 34, chờ BE wire) |

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

### II.A — Predicate CANONICAL "dưới định mức" (R7 §9.4.5 / BUG-15-03)

Định mức áp dụng cho mỗi điểm tồn (bin = `spare_part` × `warehouse`) là **effective_min**:
ưu tiên `min_stock_override` per-bin (trên `AC Spare Part Stock`), fallback `min_stock_level`
của part (trên `AC Spare Part`). Một bin được coi là "dưới định mức" khi effective_min > 0
và `qty_on_hand` < effective_min:

```
effective_min(bin) = COALESCE(NULLIF(s.min_stock_override, 0), p.min_stock_level, 0)
low(bin)           ⟺ effective_min > 0 AND s.qty_on_hand < effective_min
```

- Đánh giá **per-bin** — KHÔNG `SUM(qty_on_hand)` toàn kho (sẽ che bin riêng lẻ dưới
  định mức, đặc biệt bin có `min_stock_override` cao hơn part-min).
- **Một nguồn sự thật duy nhất**: fragment SQL `LOW_STOCK_COND` + `EFFECTIVE_MIN_EXPR`
  định nghĩa tại `services/inventory.py`; mọi nơi đếm/liệt kê (KPI `get_dashboard_stats`,
  dashboard `get_inventory_dashboard`/`get_stock_overview`, danh sách `list_stock_levels`,
  drill `list_spare_parts(low_stock=1)`, alerts `get_low_stock_alerts`, scheduler email
  `check_low_stock`) đều import chung — KHÔNG nhân bản predicate.
- `get_low_stock_alerts` trả `min_stock_level` = effective_min (vd bin override 80 trả 80,
  không phải part-min 50) để FE hiển thị đúng định mức áp dụng cho bin.

---

## III. Field Tables — IMM-15 Layer DocTypes

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
| `line_value` | Currency (read_only) | N | value_qty × unit_value (controller writer — §III-bis.8 BR-15-16) |
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

## III-bis. Reservation Ledger (soft-reservation) — SoT `reserved_qty` ⟶ `available_qty`

> 🔧 **Self-Correction (vòng 34, 2026-06-03):** Thiết kế gốc nói `get_available_qty = qty_on_hand − reserved_qty` và VR-15-03 chặn theo `available_qty`, **nhưng KHÔNG module nào ghi `reserved_qty`** — toàn codebase chỉ set `reserved_qty = 0` (4 chỗ seed/create: `inventory.py:102`, `api/imm15.py:257`, 2 script seed). Hệ quả: `available_qty == qty_on_hand` LUÔN LUÔN → VR-15-03 cho **2 allocation open cùng bin double-issue** (oversell). Section này là phần thiết kế thiếu, **chốt** writer + invariant + release.

### III-bis.1 Invariant (Single Source of Truth)

Cho mỗi **bin** = cặp (`warehouse` × `spare_part`), `name = "{warehouse}::{spare_part}"`:

```
reserved_qty(bin) = Σ qty_giữ-chỗ của MỌI dòng allocation đang ở trạng thái HOLDING cho bin đó
available_qty(bin) = MAX(0, qty_on_hand − reserved_qty)        # before_save, clamp tại 0
```

- **HOLDING set = {Requested, Approved}** — đây là trạng thái "giữ chỗ chưa xuất". Lượng giữ của một dòng = `qty_approved` nếu > 0, ngược lại `qty_requested` (số lượng đang chờ xuất).
- `Issued`, `Returned`, `Cancelled` = **terminal/released** → KHÔNG còn giữ chỗ (đã trừ `qty_on_hand` thật khi Issue, hoặc đã hủy).
- `Picked` (enum tồn tại nhưng CHƯA có transition nào set — `OPEN` tuple trong code liệt kê nó): **NẾU** sau này wire transition `Approve → Pick`, `Picked` cũng thuộc HOLDING (vẫn giữ chỗ, chưa xuất). Hiện tại không phát sinh → recompute bỏ qua một cách tự nhiên vì không có dòng `Picked` nào.

> ⚠️ Quy ước số lượng giữ chỗ: dùng `COALESCE(NULLIF(qty_approved,0), qty_requested)` để khi Approve có điều chỉnh `qty_approved` thì reserved phản ánh số đã duyệt; khi mới Requested (chưa có `qty_approved`) thì giữ theo `qty_requested`.

### III-bis.2 SoT recompute — `services/inventory.py::recompute_reserved`

**MỘT** hàm canonical, MỌI transition allocation gọi chung. **KHÔNG** inline cộng/trừ `reserved_qty` rải rác (cấm `reserved_qty += qty` trong imm15.py).

```python
# services/inventory.py
_HOLDING_ALLOCATION_STATES = ("Requested", "Approved", "Picked")  # giữ chỗ, chưa xuất

def recompute_reserved(warehouse: str, spare_part: str) -> float:
    """SoT: tính lại reserved_qty cho 1 bin = Σ qty giữ-chỗ của allocation HOLDING.

    Quét MỌI dòng IMM Spare Allocation Item thuộc các phiếu (warehouse_from=warehouse,
    allocation_status ∈ HOLDING) có spare_part khớp; reserved = Σ COALESCE(NULLIF(qty_approved,0), qty_requested).
    Ghi reserved_qty vào AC Spare Part Stock (tạo bin nếu chưa có với qty_on_hand=0);
    available_qty được before_save tính lại (clamp ≥ 0). Idempotent — gọi nhiều lần cùng kết quả.

    Returns: reserved_qty mới (float).
    """
```

- **Idempotent + tuyệt đối** (recompute từ DB, KHÔNG cộng dồn delta) → tự lành nếu một transition crash giữa chừng.
- Gọi `recompute_reserved(warehouse_from, spare_part)` cho **mọi spare_part trong phiếu** tại CUỐI mỗi transition: `create_allocation` (Requested), `approve_allocation` (Approved, có thể đổi qty_approved), `issue_allocation` (→ Issued, release), `cancel_allocation` (→ Cancelled, release), `return_items` (→ Returned, release). Đặt SAU khi `allocation_status` đã đổi & commit-an-toàn.
- Concurrency: bọc recompute trong `SELECT ... FOR UPDATE` trên dòng `AC Spare Part Stock` của bin (khóa bi-level) để 2 issue song song không cùng đọc available cũ — xem §III-bis.5.

### III-bis.3 RELEASE on terminal (chống double-count)

Khi allocation → `Issued`: `_create_stock_movement_for_issue` trừ `qty_on_hand` THẬT. Đồng thời dòng rời HOLDING → `recompute_reserved` đưa reserved của phần đã xuất về 0. **KHÔNG** double-count (vừa trừ qty_on_hand vừa còn giữ reserved). Sau Issue: `reserved_qty == 0` cho phần đã xuất, `available_qty == qty_on_hand` (mới, đã trừ).

Khi `Cancelled`/`Returned`: `qty_on_hand` không bị trừ (Cancel) hoặc được cộng lại (Return qua Receipt movement) — dòng rời HOLDING → reserved giải phóng.

### III-bis.4 ANTI-OVERSELL (bug nghiệp vụ chính)

Tồn `qty_on_hand = Q`, 2 allocation OPEN đồng thời cùng bin, mỗi cái cần `Q`:

1. Allocation #1 (Requested/Approved) → `recompute_reserved` ⟹ `reserved_qty = Q`, `available_qty = 0`.
2. Allocation #2 issue → VR-15-03 đọc `get_available_qty = 0 < Q` ⟹ **FAIL** `BUSINESS_RULE`. (Trước fix: cả hai cùng pass vì available luôn = Q.)
3. **Emergency + Critical bypass GIỮ NGUYÊN** (`is_emergency and is_critical` → bỏ qua VR-15-03) — không đổi.

### III-bis.5 `AC Spare Part Stock.before_save` — clamp ≥ 0

```python
def before_save(self):
    on_hand  = float(self.qty_on_hand or 0)
    reserved = max(0.0, float(self.reserved_qty or 0))      # guard âm/null
    self.available_qty = max(0.0, on_hand - reserved)       # NEVER âm (reserved có thể tạm > on_hand do điều chỉnh kho)
```

`available_qty` KHÔNG BAO GIỜ âm. `reserved_qty` có thể tạm > `qty_on_hand` (vd điều chỉnh kho giảm tồn trong khi còn phiếu giữ) → available kẹp 0, không phát sinh số âm gây vỡ KPI/UI.

### III-bis.6 Consumers — đọc đúng SoT, KHÔNG hồi quy ngữ nghĩa

| Consumer | Hàm | Sau fix |
|---|---|---|
| VR-15-03 sufficiency gate | `issue_allocation` → `get_available_qty` | Phản ánh reservation thật → chống oversell |
| Critical watchlist breach | `get_critical_watchlist` / `get_dashboard_stats` critical_breach | `get_available_qty` < min → đúng hơn (tính cả giữ chỗ) |
| Tìm phụ tùng còn hàng | `search_parts(show_stock_only)` → `available_qty > 0` | Ẩn bin đã giữ hết |
| Cycle-count baseline | `create_cycle_count` / `submit_cycle_count` system_qty (imm15.py:379/414) | `get_available_qty` |
| **Low-stock predicate** | `LOW_STOCK_COND` / `EFFECTIVE_MIN_EXPR` | **GIỮ NGUYÊN dùng `qty_on_hand`** — định mức so tồn **vật lý**, KHÔNG đổi sang available (giữ semantics đã chốt round-3 SoT) |

> 🚫 KHÔNG đổi `LOW_STOCK_COND` sang `available_qty`. Low-stock = tồn vật lý dưới định mức (đặt hàng bổ sung theo vật lý), độc lập với giữ chỗ.

### III-bis.7 SoT số-lượng-giữ-chỗ = số-lượng-xuất (BR-15-15) — Self-Correction vòng 1

> 🐞 **ROOT-CAUSE thiết kế gốc (lỗi nghiệp vụ):** `reserved_qty` (giữ chỗ) tính theo `COALESCE(NULLIF(qty_approved,0), qty_requested)` (§III-bis.1, đã chốt), NHƯNG `issue_allocation` lại xuất `qty_requested` thuần (`item.qty_issued = qty_requested`). Khi người duyệt CẮT `qty_approved` (vd 10→4), reservation giữ ĐÚNG 4 nhưng issue vẫn phát 10 ⟹ **(a) over-issue vượt số đã duyệt** (điều chỉnh phê duyệt bị bỏ qua âm thầm), **(b) lệch reserved-vs-issued** (giữ 4, xuất 10), **(c) VR-15-03 gate so sai đại lượng** (`qty_needed = qty_requested`, không phải số sẽ thật-sự-xuất). Đặc tả gốc thiếu hẳn quy ước "xuất theo số nào".

**CHỐT (1 SoT đại lượng):** Đại lượng giữ-chỗ VÀ đại lượng xuất của một dòng allocation là **CÙNG MỘT** giá trị canonical:

```
effective_hold_qty(line) = COALESCE(NULLIF(qty_approved, 0), qty_requested)
```

- Helper canonical `effective_alloc_qty(item) -> float` trong `services/imm15.py` (module-level, pure): `float(item.qty_approved or 0) or float(item.qty_requested or 0)`. ĐÂY là SoT đại lượng cho cả issue lẫn gate; `recompute_reserved` (SQL) đã dùng đúng công thức tương đương — KHÔNG inline lại biểu thức ở `issue_allocation`.
- `issue_allocation` (§3.4): `qty_needed = effective_alloc_qty(item)` (KHÔNG còn `qty_requested` thuần); `item.qty_issued = qty_needed`; `own_hold = effective_alloc_qty(item)` (dùng chung helper, bỏ biểu thức lặp ở dòng own_hold). ⟹ **INVARIANT: số đã xuất == số đã giữ chỗ** cho mọi dòng; sau Issue, `reserved` của dòng về 0 và `qty_on_hand` chỉ trừ đúng phần đã duyệt.
- **Backward-compat:** khi `qty_approved` chưa set (0/NULL — vd luồng Emergency issue thẳng từ Requested, hoặc Approve không điều chỉnh) → `effective_alloc_qty` trả `qty_requested` ⟹ hành vi cũ giữ nguyên, KHÔNG hồi quy.
- VR-15-03 anti-oversell (§III-bis.4) KHÔNG đổi cấu trúc: vẫn `avail_excl_self = on_hand − max(0, reserved − own_hold)`, chỉ thay `qty_needed`/`own_hold` về cùng helper ⟹ gate giờ so đúng số sẽ-thật-sự-xuất.
- Emergency + Critical bypass (§III-bis.4.3) GIỮ NGUYÊN.

| Tình huống | qty_requested | qty_approved | reserved (giữ) | qty_issued (xuất) — SAU FIX | TRƯỚC FIX (bug) |
|---|---|---|---|---|---|
| Approve cắt số | 10 | 4 | 4 | **4** | 10 (over-issue) |
| Approve không đổi | 10 | 0/NULL | 10 | 10 | 10 |
| Approve tăng (hiếm) | 4 | 6 | 6 | 6 | 4 |

### III-bis.8 SoT giá trị dòng/phiếu — `line_value` & `total_value` (BR-15-16) — Self-Correction vòng 2

> 🐞 **ROOT-CAUSE thiết kế gốc (2 lỗi):**
> 1. **Đại lượng sai + clobber:** controller `IMM Spare Allocation.validate()` tính `total_value = Σ(qty_requested × unit_value)` chạy trên MỌI save. Service `issue_allocation` tính `total_value = Σ(qty_issued × unit_value)` rồi `save()` → `validate()` chạy lại → **clobber** giá trị issued-based về requested-based. ⟹ sau Issue (đặc biệt khi approver cắt số — BR-15-15), `total_value` phản ánh số YÊU CẦU, KHÔNG phải số đã xuất → sai giá trị tài chính.
> 2. **Dead column:** `line_value` (Thành tiền/dòng, read_only) KHÔNG có writer nào trong Python ⟹ luôn rỗng → cột FE/report bind vào nó hiển thị trống.

**CHỐT (1 SoT giá trị, lifecycle-aware):** Đại lượng định giá của một dòng = đại lượng theo VÒNG ĐỜI:

```
value_qty(line) = qty_issued       nếu allocation đã Issued/Returned (qty_issued > 0)
                = effective_alloc_qty(line)   ngược lại (Requested/Approved — số cam kết)
line_value(line)  = value_qty(line) × unit_value
total_value(doc)  = Σ line_value(line)
```

- Helper SoT `value_qty(item) -> float` trong controller (hoặc service shared) = `float(item.qty_issued or 0) or effective_alloc_qty(item)`. Lý do: trước Issue chưa có qty_issued → hiển thị giá trị CAM KẾT theo số đã duyệt (KHÔNG 0); sau Issue dùng số thực xuất.
- **MỘT writer duy nhất:** controller `validate()` tính CẢ `line_value` (mỗi dòng) LẪN `total_value = Σ line_value`. Service `issue_allocation` KHÔNG còn tự set `total_value` (xoá block Σ cục bộ) — để controller (chạy trong cùng `save()`) là chủ duy nhất ⟹ KHÔNG clobber, KHÔNG 2 công thức song song.
- INVARIANT: `total_value == Σ line_value`; sau Issue với approver cắt số → `total_value` theo số đã xuất (KHỚP BR-15-15), KHÔNG theo qty_requested.
- Backward-compat: dòng chưa duyệt/chưa xuất (qty_approved=0, qty_issued=0) → value_qty = qty_requested ⟹ giá trị cam kết hiển thị như cũ.

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
    """Controller validate(): tính line_value mỗi dòng + total_value = Σ line_value.

    value_qty(line) = qty_issued nếu đã xuất, ngược lại effective_alloc_qty(line)
    (lifecycle-aware — BR-15-16 §III-bis.8). MỘT writer duy nhất; service KHÔNG tự
    set total_value (tránh clobber). line_value KHÔNG còn dead column.
    """
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

def cancel_allocation(allocation: str) -> dict:
    """Hủy phiếu: {Requested, Approved, Picked} → Cancelled (§3.6 / §III-bis.3).

    KHÔNG cho hủy khi đã Issued (BAD_STATE). Sau khi set Cancelled → dòng rời HOLDING →
    gọi recompute_reserved cho mọi spare_part trong phiếu → reserved giải phóng.
    Audit CANCELLED. qty_on_hand KHÔNG đổi (chưa từng trừ).

    Raises:
        ServiceError(BAD_STATE, "Không thể hủy Allocation đã Issued/Returned")
    Returns: {"name", "workflow_state": "Cancelled"}
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

def recompute_reserved(warehouse: str, spare_part: str) -> float:
    """SoT: tính lại reserved_qty cho 1 bin (xem §III-bis.2).

    Σ qty giữ-chỗ của allocation HOLDING {Requested, Approved, Picked} cho bin →
    ghi reserved_qty vào AC Spare Part Stock; before_save tính lại available_qty (clamp ≥0).
    Idempotent (tuyệt đối, từ DB — KHÔNG cộng dồn delta). Bọc FOR UPDATE bin row.

    Returns: reserved_qty mới (float).
    """
    ...

def get_available_qty(spare_part: str, warehouse: str) -> float:
    """Wrap services.inventory.get_available_qty.

    Returns:
        float: MAX(0, qty_on_hand - reserved_qty)
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
# hooks.py — IMM-15 wiring (verified 2026-05-18)

doc_events = {
    # "PM Work Order" là tên DocType thực tế trong hooks.py (không phải "IMM PM Work Order")
    "PM Work Order": {
        "before_submit": "assetcore.services.imm15.reserve_for_pm",
        # IMM-16 owns gate + realtime eval:
        # "validate":  "assetcore.services.imm16.gate_wo_submit",
        # "on_submit": "assetcore.services.imm16.eval_imm08_09_realtime",
    },
    # "Asset Repair" là tên DocType thực tế (không phải "IMM CM Work Order")
    "Asset Repair": {
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

Cột **reserved** = hiệu ứng lên `reserved_qty` qua `recompute_reserved` (SoT §III-bis.2). HOLDING = {Requested, Approved, Picked} giữ chỗ; terminal {Issued, Returned, Cancelled} giải phóng.

| From | Action (tiếng Việt) | To | Role | reserved (SoT) |
|---|---|---|---|---|
| — | (create) | `Requested` | Repair User / Repair User | **+Q giữ chỗ** (recompute) |
| `Requested` | Phê duyệt | `Approved` | Inventory Manager / Inventory Manager | giữ chỗ (recompute theo qty_approved) |
| `Approved` | Pick | `Picked` | Inventory User | giữ chỗ (không đổi lượng) |
| `Picked` | Issue | `Issued` | Inventory User (sinh AC Stock Movement) | **RELEASE** (qty_on_hand−, reserved về 0 phần xuất) |
| `Requested` | Issue (Emergency) | `Issued` | Inventory Manager + Inventory Manager (double) | **RELEASE** |
| `Issued` | Trả phụ tùng | `Returned` | Inventory User | đã release (qty_on_hand+ qua Receipt) |
| `Returned` | Đóng phiếu | `Issued` | Inventory User (nếu còn dùng) | — |
| `Requested` | Hủy | `Cancelled` | Inventory Manager / AssetCore Super Admin | **RELEASE** (qty_on_hand không đổi) |
| `Approved` | Hủy | `Cancelled` | Inventory Manager / AssetCore Super Admin | **RELEASE** |
| `Picked` | Hủy | `Cancelled` | Inventory Manager / AssetCore Super Admin | **RELEASE** |

### VI.2 IMM Stock Cycle Count (4 states / 5 transitions)

| From | Action (tiếng Việt) | To | Role |
|---|---|---|---|
| — | (create) | `Planned` | Inventory User / AssetCore Super Admin |
| `Planned` | Bắt đầu đếm | `Counting` | Inventory User |
| `Counting` | Hoàn tất đếm | `Reviewed` | Inventory Manager / Compliance Manager |
| `Reviewed` | Sửa đếm lại | `Counting` | Inventory User |
| `Reviewed` | Post | `Posted` | Inventory Manager / Inventory Manager (sinh AC Stock Movement Adjustment) |

---

## VII. Schedulers

| Job | File | Lịch | Mô tả |
|---|---|---|---|
| `check_low_stock_and_alert` | `services/imm15.py` | daily | Legacy alias → gọi `check_critical_spare_breach`; mục đích: extend LIVE `services.inventory.check_low_stock` |
| `check_critical_spare_breach` | `services/imm15.py` | daily | Quét Watchlist; breach → CAPA seed + email khẩn |
| `check_expiring_batches` | `services/imm15.py` | daily | Gated: no-op nếu `tabIMM Spare Batch` chưa tồn tại |
| `generate_spare_demand_forecast` | `services/imm15.py` | monthly | Tạo IMM Spare Part Forecast Draft (Moving_Avg default) |
| `compute_inventory_kpis` | `services/imm15.py` | daily | Snapshot KPI: turnover, days-on-hand, stockout, breach, accuracy, MAPE |
| `reclassify_abc` | `services/imm15.py` | cron `0 3 1 1,4,7,10 *` | ABC quarterly reclassification (XYZ reclassification chưa implemented) |

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

Thứ tự bắt buộc (Wave 2 — deployed):

```
# patches.txt (Wave 2 section)
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
| `deploy_imm15_doctypes` | 5 DocType + 4 child (LIVE) | Low (new tables) | Drop new tables |
| `install_imm15_workflows` | 2 Workflow JSON | Low | Delete workflow records |
| `extend_ac_stock_movement_reference_type` | Mở rộng reference_type options: thêm IMM Spare Allocation, IMM Stock Cycle Count | Low (Property Setter, không sửa core JSON) | Remove Property Setter |
| `backfill_imm_part_class` | Set imm_part_class: Critical nếu is_critical=1, còn lại Major | Low (UPDATE, no nulls) | Reset to NULL |
| `backfill_abc_xyz_defaults` | Set imm_abc_class=C, imm_xyz_class=Z | Low | Reset |
| `seed_watchlist_top50` | Seed Watchlist top-50 critical assets (sau khi IMM-04/05 có data) | Low (insert) | Delete seeded |
