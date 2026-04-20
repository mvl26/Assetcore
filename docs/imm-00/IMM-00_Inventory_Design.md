# IMM-00 Inventory Sub-Domain — Kho vật tư, Phụ tùng, Tồn kho

| Thuộc tính | Giá trị |
|---|---|
| Thuộc | IMM-00 Foundation v4 |
| Phiên bản | 1.0.0 |
| Ngày | 2026-04-20 |
| Trạng thái | **Active** |

---

## 1. Mục đích

Quản lý danh mục phụ tùng thay thế (spare parts), kho vật tư (warehouses), tồn kho thực tế, và mọi giao dịch nhập/xuất/chuyển kho cho toàn bộ hệ thống AssetCore.

**Nghiệp vụ then chốt:**

1. **Master catalog phụ tùng** — một sản phẩm = 1 record, dùng chung toàn hệ thống.
2. **Kho đa vị trí** — mỗi khoa/xưởng có thể có kho riêng.
3. **Tồn kho real-time** — mọi giao dịch cập nhật `qty_on_hand` ngay.
4. **Liên kết nghiệp vụ sửa chữa** — phiếu xuất kho link ngược về Asset Repair / PM Work Order.
5. **Cảnh báo tồn thấp** — tồn < `min_stock_level` → email scheduler.
6. **Audit trail** — mọi Stock Movement là record bất biến sau khi submit (docstatus=1).

---

## 2. Domain Model

```
                ┌─────────────────────────┐
                │      AC Warehouse       │
                │   (kho vật tư master)   │
                └───────────┬─────────────┘
                            │ 1:N
                            ▼
                ┌─────────────────────────┐     N:1      ┌─────────────────────────┐
                │   AC Spare Part Stock   │◄─────────────┤     AC Spare Part       │
                │   (tồn theo kho × SP)   │              │ (master catalog)        │
                └───────────┬─────────────┘              └──────────┬──────────────┘
                            │ cập nhật khi submit                   │ M:N
                            ▼                                       ▼
                ┌─────────────────────────┐              ┌─────────────────────────┐
                │   AC Stock Movement     │──── N:1 ────▶│ IMM Device Model        │
                │   (nhập/xuất/chuyển)    │              │ (qua IMM Device Spare   │
                └───────────┬─────────────┘              │  Part child — BOM)      │
                            │ 1:N                        └─────────────────────────┘
                            ▼
                ┌─────────────────────────┐
                │ AC Stock Movement Item  │
                │ (chi tiết dòng)         │
                └─────────────────────────┘
                            │
                            └── link optional: asset_repair, pm_work_order
```

---

## 3. DocType Specifications

### 3.1 AC Warehouse

Kho vật tư — đơn vị vật lý lưu trữ phụ tùng.

| Field | Type | Reqd | Note |
|---|---|---|---|
| warehouse_code | Data | ✅ | Unique, vd: `WH-XUONG-CHINH` |
| warehouse_name | Data | ✅ | Tên hiển thị |
| location | Link (AC Location) | — | Vị trí vật lý |
| department | Link (AC Department) | — | Khoa quản lý |
| manager | Link (User) | — | Người phụ trách kho |
| is_active | Check | — | Default 1 |
| notes | Text | — | — |

**Naming**: `AC-WH-.####`

---

### 3.2 AC Spare Part

Master catalog phụ tùng chuẩn toàn hệ thống.

| Field | Type | Reqd | Note |
|---|---|---|---|
| part_code | Data | ✅ | Unique, mã nội bộ (autoname field) |
| part_name | Data | ✅ | Tên phụ tùng |
| part_category | Select | — | `Electrical`, `Mechanical`, `Consumable`, `Filter`, `Battery`, `Sensor`, `Other` |
| manufacturer | Data | — | NSX |
| manufacturer_part_no | Data | — | Mã của NSX |
| preferred_supplier | Link (AC Supplier) | — | NCC chính |
| unit_cost | Currency | — | Đơn giá tham khảo (VND) |
| uom | Select | — | `Nos`, `Pcs`, `Set`, `Box`, `Meter`, `Liter`, `Kg` |
| min_stock_level | Int | — | Ngưỡng cảnh báo toàn hệ thống (tổng qua tất cả kho) |
| max_stock_level | Int | — | Tồn trần |
| shelf_life_months | Int | — | Hạn sử dụng (tháng) — áp dụng cho Consumable |
| is_critical | Check | — | Phụ tùng tới hạn (down-time high) |
| is_active | Check | — | Default 1 |
| specifications | Text | — | Thông số kỹ thuật |

**Naming**: `AC-SP-.YYYY.-.####`

**Validate**:
- `min_stock_level >= 0`, `max_stock_level >= min_stock_level` (nếu có cả 2)
- `unit_cost >= 0`

---

### 3.3 AC Spare Part Stock

Tồn kho thực tế — **unique key: (warehouse, spare_part)**.

| Field | Type | Reqd | Note |
|---|---|---|---|
| warehouse | Link (AC Warehouse) | ✅ | |
| spare_part | Link (AC Spare Part) | ✅ | |
| qty_on_hand | Float | ✅ | Tồn hiện tại, default 0 |
| reserved_qty | Float | — | Đã cấp phát cho repair chưa xuất, default 0 |
| available_qty | Float (calc) | — | `qty_on_hand - reserved_qty` |
| last_movement_date | Datetime | — | Auto-update khi có movement |
| min_stock_override | Int | — | Override min/warehouse (optional) |
| notes | Small Text | — | — |

**Naming**: `by fieldname` → `{warehouse}::{spare_part}` (Frappe autoname pattern).

**Constraint**: UNIQUE INDEX `(warehouse, spare_part)`.

---

### 3.4 AC Stock Movement

Phiếu giao dịch kho. Submittable (docstatus 0/1/2).

| Field | Type | Reqd | Note |
|---|---|---|---|
| movement_type | Select | ✅ | `Receipt` (nhập), `Issue` (xuất), `Transfer` (chuyển), `Adjustment` (điều chỉnh) |
| movement_date | Datetime | ✅ | Default: `now()` |
| from_warehouse | Link (AC Warehouse) | — | Reqd nếu Issue/Transfer/Adjustment |
| to_warehouse | Link (AC Warehouse) | — | Reqd nếu Receipt/Transfer |
| reference_type | Select | — | `Asset Repair`, `PM Work Order`, `Purchase`, `Manual` |
| reference_name | Dynamic Link | — | Link tới chứng từ gốc |
| supplier | Link (AC Supplier) | — | Chỉ Receipt |
| requested_by | Link (User) | ✅ | Auto = `session.user` |
| approved_by | Link (User) | — | Cho giao dịch cần duyệt (cost > threshold) |
| status | Select | ✅ | `Draft`, `Submitted`, `Cancelled` |
| notes | Text | — | — |
| items | Table (AC Stock Movement Item) | ✅ | ≥ 1 dòng |
| total_value | Currency (calc) | — | Σ `items[].total_cost` |

**Naming**: `AC-SM-.YYYY.-.#####`

**Business rules**:
- `BR-INV-01` Receipt: chỉ cần `to_warehouse`. Items[].qty > 0 → tăng stock.
- `BR-INV-02` Issue: chỉ cần `from_warehouse`. Items[].qty > 0 → giảm stock. Validate `available_qty >= qty`.
- `BR-INV-03` Transfer: cần cả `from_warehouse` + `to_warehouse` (khác nhau). Giảm from, tăng to.
- `BR-INV-04` Adjustment: qty có thể âm/dương. Require `notes`.
- `BR-INV-05` Chỉ submit (docstatus=1) mới cập nhật stock. Cancel (docstatus=2) → reverse stock.
- `BR-INV-06` Sau submit không được edit — phải cancel + tạo mới.

---

### 3.5 AC Stock Movement Item (child)

| Field | Type | Reqd | Note |
|---|---|---|---|
| spare_part | Link (AC Spare Part) | ✅ | |
| part_name | Data (fetch) | — | Auto-fetch từ spare_part |
| qty | Float | ✅ | > 0 (trừ Adjustment cho phép âm) |
| uom | Data (fetch) | — | Auto |
| unit_cost | Currency | ✅ | Lấy từ `spare_part.unit_cost`, user có thể override |
| total_cost | Currency (calc) | — | `qty × unit_cost` |
| serial_no | Data | — | Tuỳ chọn, dùng cho phụ tùng có SN |
| notes | Small Text | — | — |

---

## 4. Service Layer

File: `assetcore/services/inventory.py`

| Function | Mô tả |
|---|---|
| `apply_stock_movement(doc)` | Hook `on_submit` → cập nhật `AC Spare Part Stock` (upsert) cho từng dòng |
| `reverse_stock_movement(doc)` | Hook `on_cancel` → reverse tồn |
| `get_stock_level(spare_part, warehouse=None)` | Query tồn theo kho hoặc tổng |
| `check_low_stock()` | Scheduler daily → list (part, total_qty, min_level) → email Storekeeper |
| `reserve_for_repair(repair_name, items)` | Giữ chỗ tồn khi tạo Work Order (chưa xuất) |
| `release_reservation(repair_name)` | Release khi Work Order cancel |
| `search_parts(query)` | Auto-complete cho form CM / PM (thay cho `search_spare_parts` cũ) |

---

## 5. API Layer

File: `assetcore/api/inventory.py`

| Endpoint | Method | Mô tả |
|---|---|---|
| `list_warehouses` | GET | Paginated, filter by active/department |
| `create_warehouse` | POST | — |
| `update_warehouse` | POST | — |
| `list_spare_parts` | GET | Paginated, search by name/code/manufacturer_part_no |
| `get_spare_part` | GET | Kèm tồn kho theo từng warehouse + lịch sử movement |
| `create_spare_part` | POST | — |
| `update_spare_part` | POST | — |
| `get_stock_overview` | GET | KPIs: total_parts, total_value, low_stock_count, movement_count_30d |
| `list_stock_levels` | GET | Paginated stock của all parts (hoặc filter by warehouse) |
| `list_stock_movements` | GET | Paginated, filter by type/date/warehouse |
| `get_stock_movement` | GET | Full document with items |
| `create_stock_movement` | POST | Draft or auto-submit |
| `submit_stock_movement` | POST | docstatus 0 → 1 |
| `cancel_stock_movement` | POST | docstatus 1 → 2, reverse tồn |
| `search_parts_autocomplete` | GET | Thay `search_spare_parts` cũ |

Tất cả trả về `_ok(data)` / `_err(msg, code)` envelope.

---

## 6. Frontend Views

| Route | View | Mục đích |
|---|---|---|
| `/inventory` | InventoryDashboardView | KPIs + low-stock alerts + recent movements |
| `/warehouses` | WarehouseListView | CRUD kho |
| `/spare-parts` | SparePartListView | Master catalog, filter, search |
| `/spare-parts/:code` | SparePartDetailView | Tồn theo kho + lịch sử movement của part |
| `/stock` | StockLevelView | Tồn tổng: grid (part × warehouse) với cảnh báo low |
| `/stock-movements` | StockMovementListView | Danh sách phiếu nhập/xuất |
| `/stock-movements/new` | StockMovementCreateView | Tạo phiếu: Receipt / Issue / Transfer / Adjustment |
| `/stock-movements/:name` | StockMovementDetailView | Xem chi tiết, submit/cancel |

Sidebar: nhóm mới **"Kho vật tư"** dưới "Vòng đời thiết bị".

---

## 7. Business Rules bổ sung (IMM-00 level)

| ID | Rule | Enforce |
|---|---|---|
| BR-00-11 | Mỗi Stock Movement submit → phải sinh 1 IMM Audit Trail event `Stock` | `AC Stock Movement.on_submit` |
| BR-00-12 | Khi close Asset Repair có `spare_parts_used` → auto tạo Stock Movement `Issue` (reference Asset Repair) | `imm09.close_work_order` |
| BR-00-13 | Không cho Delete AC Spare Part nếu đã có Stock hoặc Movement reference | `AC Spare Part.on_trash` |
| BR-00-14 | Không cho xuất quá `available_qty` | `apply_stock_movement` |

---

## 8. Migration từ hiện trạng

| Legacy | Xử lý |
|---|---|
| `IMM Device Spare Part` (child BOM) | Giữ nguyên; nhưng thêm field `spare_part` Link tới `AC Spare Part` (optional, migrate dần) |
| `Spare Parts Used` (child Asset Repair) | Giữ nguyên cho backward-compat. Thêm field `spare_part` Link optional. Khi Asset Repair close → tạo Stock Movement mới |
| `search_spare_parts()` trong `imm09` | Deprecate, redirect sang `inventory.search_parts` |

---

## 9. Roadmap triển khai

| Sprint | Hạng mục | Trạng thái |
|---|---|---|
| INV-0.1 | 5 DocType JSON + autoname + controllers | 🔜 |
| INV-0.2 | `services/inventory.py` + stock apply/reverse | 🔜 |
| INV-0.3 | `api/inventory.py` full CRUD | 🔜 |
| INV-0.4 | Scheduler `check_low_stock` + email template | 🔜 |
| INV-0.5 | FE: Warehouse, Spare Part, Stock views | 🔜 |
| INV-0.6 | FE: Stock Movement create/detail | 🔜 |
| INV-0.7 | Integration: Asset Repair close_work_order → auto Issue | 🔜 |
| INV-0.8 | Test suite (target 70% coverage) | 🔜 |

---

## 10. Ví dụ nghiệp vụ

**Ex 1 — Nhập mua phụ tùng**:
> Storekeeper tạo `Stock Movement` type=`Receipt`, to_warehouse=`WH-XUONG`, items=[{spare_part: bóng đèn X-quang, qty: 5, unit_cost: 3,500,000}], supplier=`NCC Phillips`. Submit → `AC Spare Part Stock(WH-XUONG, bóng đèn)` tăng 5 → `qty_on_hand: 0 → 5`.

**Ex 2 — Xuất sửa chữa**:
> KTV khi đóng Asset Repair có `spare_parts_used`. System auto tạo `Stock Movement` type=`Issue`, from_warehouse=`WH-XUONG`, reference=Asset Repair, auto-submit → tồn giảm tương ứng.

**Ex 3 — Cảnh báo low stock**:
> Scheduler daily chạy `check_low_stock()`: `bóng đèn X-quang` tổng tồn=2 < min_stock_level=5 → gửi email `IMM Storekeeper` kèm list thiếu.
