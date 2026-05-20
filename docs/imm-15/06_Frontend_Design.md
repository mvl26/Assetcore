# IMM-15 — Frontend Design

> ✅ Implemented — Wave 2. Routes/views/store đều LIVE. Wireframes & component spec dưới đây giữ nguyên làm thiết kế tham chiếu; bảng route ở §I.1 đã sync với `frontend/src/router/index.ts`.

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-15 — Spare Parts Inventory Tracking |
| Phiên bản | 1.1.0 |
| Template | 06 Frontend_Design |
| Ngày cập nhật | 2026-05-14 |
| Trạng thái | IMPLEMENTED (Wave 2) |
| Phụ thuộc | AC Spare Part, AC Stock Movement, AC Warehouse (Wave 1 LIVE) |

---

## §I — Sitemap & Routes

### I.1 Route Catalog (sync với `frontend/src/router/index.ts`, kiểm tra 2026-05-14)

| # | Route | Component | meta.moduleId | Roles meta |
|---|---|---|---|---|
| 1 | `/inventory` | `views/inventory/InventoryDashboardView.vue` | imm15 | `ROLES_SPARE_VIEW` |
| 2 | `/warehouses` | `views/inventory/WarehouseListView.vue` | imm15 | `ROLES_SPARE_VIEW` |
| 3 | `/warehouses/:name` | `views/inventory/WarehouseDetailView.vue` | imm15 | `ROLES_SPARE_VIEW` |
| 4 | `/spare-parts` | `views/inventory/SparePartListView.vue` | imm15 | `ROLES_SPARE_VIEW` |
| 5 | `/spare-parts/:name` | `views/inventory/SparePartDetailView.vue` | imm15 | `ROLES_SPARE_VIEW` |
| 6 | `/stock` | `views/inventory/StockLevelView.vue` | imm15 | `ROLES_SPARE_VIEW` |
| 7 | `/stock-movements` | `views/inventory/StockMovementListView.vue` | imm15 | `ROLES_SPARE_VIEW` |
| 8 | `/stock-movements/new` | `views/inventory/StockMovementCreateView.vue` | imm15 | `ROLES_STOCK_MANAGE` |
| 9 | `/stock-movements/:name` | `views/inventory/StockMovementDetailView.vue` | imm15 | `ROLES_SPARE_VIEW` |
| 10 | `/stock-movements/:name/edit` | `views/inventory/StockMovementEditView.vue` | imm15 | `ROLES_STOCK_MANAGE` |
| 11 | `/inventory/uom` | `views/inventory/UomConversionView.vue` | imm15 | `ROLES_STOCK_MANAGE` |
| 12 | `/inventory/forecasts` | `views/inventory/SpareForecastView.vue` | imm15 | `ROLES_STOCK_MANAGE` |
| 13 | `/inventory/watchlist` | `views/inventory/WatchlistView.vue` | imm15 | `ROLES_STOCK_MANAGE` |

> Quyết định wave-2: dùng path domain (`/inventory`, `/spare-parts`, `/stock-movements`, `/warehouses`) thay vì prefix `/imm15/*` — sync với pattern các module khác (`/cm`, `/pm`, `/compliance`). Sidebar mapping qua regex `[/^\/inventory/, 'imm15']`, `[/^\/spare-parts/, 'imm15']`, `[/^\/stock/, 'imm15']`, `[/^\/warehouses/, 'imm15']` trong `router/index.ts`.
>
> Allocation / Cycle Count UI hiện chưa có route riêng — store action có sẵn (`useImm15Store.fetchAllocations`, `fetchCycleCounts`) chờ FE phát triển trong sprint kế. Wireframes §II.3–II.8 dưới đây giữ làm spec tham chiếu.

### I.2 Navigation Structure (`MODULE_NAV['imm15']`)

```
IMM-15 Sidebar (Storekeeper)
├── Tổng quan kho (/inventory)
├── Danh mục phụ tùng (/spare-parts)
├── Tồn kho (/stock)
├── Phiếu xuất nhập kho (/stock-movements)
├── Danh sách kho (/warehouses)
├── Đơn vị tính (/inventory/uom)
├── Dự báo phụ tùng (/inventory/forecasts)
└── Critical Watchlist (/inventory/watchlist)
```

---

## §II — Component Catalog

### II.1 SpareItemsList.vue

**Route**: `/imm15/spares`  
**Guard**: All authenticated  
**API**: `imm15.list_spare_items`

```
┌──────────────────────────────────────────────────────────────────────────┐
│ Phụ tùng Y tế                                              [+ Thêm Item] │
│ ──────────────────────────────────────────────────────────────────────── │
│  Filter: [Part Class ▼] [ABC ▼] [XYZ ▼] [☑ Chỉ Low-stock] [Warehouse ▼] │
│         [Tìm kiếm theo OEM / item_code / tên...]                         │
│                                                                          │
│ ┌──────────────────────────────────────────────────────────────────────┐ │
│ │ Mã           | Tên                | Class    | ABC | Tồn   | Min  | Lead│ │
│ ├──────────────────────────────────────────────────────────────────────┤ │
│ │ SPARE-CT-T01 | X-ray Tube Phil... | Critical | A   | 1 ⚠   | 1    | 90d│ │
│ │ SPARE-MON-B  | Battery Monitor... | Major    | B   | 12 ✅ | 6    | 30d│ │
│ │ SPARE-FILT01 | HEPA Filter        | Consum.  | C   | 0 🔴  | 4    | 14d│ │
│ └──────────────────────────────────────────────────────────────────────┘ │
│  ◀ 1 2 3 ▶   Hiển thị 1-20/412                                           │
└──────────────────────────────────────────────────────────────────────────┘
```

**Stock badge logic:**

| Điều kiện | Màu | Icon |
|---|---|---|
| `actual_qty >= min_qty * 2` | Xanh | ✅ |
| `min_qty <= actual_qty < min_qty * 2` | Vàng | ⚠ |
| `0 < actual_qty < min_qty` | Cam | 🟠 |
| `actual_qty == 0` | Đỏ | 🔴 |
| Critical Watchlist breach | Đỏ + viền đậm | 🚨 |

**Actions:**

| Element | Guard | Action |
|---|---|---|
| `+ Thêm Item` | Workshop Head, CMMS Admin | Navigate `/app/item/new?imm_is_medical_spare=1` |
| Click row | — | Navigate `/imm15/spares/:item_code` |
| Filter change | — | Re-call `list_spare_items` |

---

### II.2 SpareItemDetail.vue

**Route**: `/imm15/spares/:item_code`

```
┌──────────────────────────────────────────────────────────────────────┐
│ SPARE-CT-TUBE-01 — X-ray Tube Philips MX                  [Sửa Item] │
│ ────────────────────────────────────────────────────────────────────  │
│ ┌── Phân loại IMM ──────────────────────────────────────────────┐    │
│ │ Class:    🔴 Critical     ABC: A      XYZ: Y                  │    │
│ │ OEM:      MX-2027-TBE-01    Lead time: 90 ngày               │    │
│ │ Min/Max:  1 / 3   Safety: 30d  Traceability: ☑               │    │
│ │ Storage:  Normal           Shelf-life: 36 tháng               │    │
│ │ Compatible Models: [CT Philips iCT 256, Brilliance 64]        │    │
│ │ Alternatives: [SPARE-CT-TUBE-01-ALT]                          │    │
│ └───────────────────────────────────────────────────────────────┘    │
│                                                                      │
│ [Info] [Inventory] [Transactions] [Forecast]                         │
│                                                                      │
│ ── Tab: Inventory ───────────────────────────────────────────────── │
│ ┌── Tồn kho theo kho ───────────────────────────────────────────┐    │
│ │ Kho                  | Actual | Reserved | Valuation          │    │
│ │ Kho trung tâm        |   1    |    0     | 250.000.000        │    │
│ │ Kho phân xưởng       |   0    |    0     |     0              │    │
│ └───────────────────────────────────────────────────────────────┘    │
│ ┌── Watchlist Critical Asset (3) ───────────────────────────────┐    │
│ │ AC-ASSET-CT-01 (ICU)  min=1   ⚠ Breach 02/05                 │    │
│ │ AC-ASSET-CT-02 (CC)   min=1   ✅ OK                           │    │
│ └───────────────────────────────────────────────────────────────┘    │
│                                                                      │
│ ── Tab: Transactions ─────────────────────────────────────────────── │
│ ┌── Giao dịch gần đây (20) ─────────────────────────────────────┐    │
│ │ 2026-04-22 | Issue   | -1 | SAL-2026-0042 | WO               │    │
│ │ 2026-03-15 | Receipt | +2 | SE-RECV-2026-0011    | -          │    │
│ └───────────────────────────────────────────────────────────────┘    │
│                                                                      │
│ KPI: Days-on-hand 45  ·  Consumption 12m: 4  ·  ABC value share 18%  │
└──────────────────────────────────────────────────────────────────────┘
```

**Tabs:**

| Tab | Nội dung |
|---|---|
| Info | 14 imm_* fields: class, ABC, XYZ, OEM, lead_time, min/max, safety_stock, traceability, storage, shelf_life, alternatives |
| Inventory | Bins per warehouse + Watchlist asset entries + Reorder suggestion |
| Transactions | Phân trang 50 latest AC Stock Movement entries |
| Forecast | Nội suy biểu đồ consumption + reorder line (từ IMM Spare Part Forecast) |

---

### II.3 AllocationList.vue

**Route**: `/imm15/allocations`

```
┌──────────────────────────────────────────────────────────────────────┐
│ Phiếu cấp phát phụ tùng                          [+ Tạo Phiếu mới]   │
│ ────────────────────────────────────────────────────────────────────  │
│  Filter: [Trạng thái ▼] [Urgency ▼] [Asset ▼] [Work Order ▼] [Tìm]   │
│                                                                      │
│ ┌────────────────────────────────────────────────────────────────┐  │
│ │ #  | Số phiếu     | WO           | Asset        | Urg  | Status│  │
│ ├────────────────────────────────────────────────────────────────┤  │
│ │ 1  | SAL-2026-... | WO-PM-...    | AC-ASSET-... | Rout | Issued│  │
│ │ 2  | SAL-2026-... | WO-CM-...    | AC-ASSET-... | Emer | Issued│  │
│ │ 3  | SAL-2026-... | WO-PM-...    | AC-ASSET-... | Urg  | Approved│ │
│ └────────────────────────────────────────────────────────────────┘  │
│  Hiển thị 1-20/137                                                   │
└──────────────────────────────────────────────────────────────────────┘
```

**Status badges:**

| State | Badge |
|---|---|
| Requested | Yellow "⏳ Yêu cầu" |
| Approved | Blue "📝 Đã duyệt" |
| Picked | Cyan "📦 Đã pick" |
| Issued | Green "✅ Đã cấp" |
| Returned | Gray "↩️ Đã trả" |
| Cancelled | Red "❌ Đã hủy" |
| Emergency flag | Thêm 🚨 sau badge status |

---

### II.4 AllocationCreate.vue

**Route**: `/imm15/allocations/new`

```
┌──────────────────────────────────────────────────────────────────┐
│ Tạo Phiếu cấp phát                              Status: Requested │
│ ────────────────────────────────────────────────────────────────  │
│ ┌── Liên kết Work Order ─────────────────────────────────────┐   │
│ │ WO Type*:  [IMM PM Work Order ▼]                           │   │
│ │ WO Ref*:   [WO-PM-2026-0007 ▼]   (auto-fetch asset)       │   │
│ │ Asset:     [AC-ASSET-2026-0001]  (locked)                  │   │
│ └────────────────────────────────────────────────────────────┘   │
│                                                                  │
│ ┌── Yêu cầu ─────────────────────────────────────────────────┐   │
│ │ Kho xuất*:   [Kho trung tâm  ▼]                            │   │
│ │ Urgency*:    ⦿ Routine  ○ Urgent  ○ Emergency              │   │
│ │ Required by: [📅 2026-05-10]                               │   │
│ └────────────────────────────────────────────────────────────┘   │
│                                                                  │
│ ┌── Phụ tùng ────────────────────────────────────────────────┐   │
│ │ Item*           | Qty | Used For    | Available | OK?       │   │
│ │ [SPARE-001 ▼]  |  2  | Replacement | 5         | ✅        │   │
│ │ [SPARE-002 ▼]  |  1  | Test        | 0         | ⚠ MR     │   │
│ │ [+ Thêm dòng]                                              │   │
│ └────────────────────────────────────────────────────────────┘   │
│                                                                  │
│ Tổng giá trị: 125.300.000 VND                                    │
│ Ghi chú: [textarea                                            ]  │
│                                                                  │
│ ────────────────────────────────────────────────────────────────  │
│   [Hủy]                          [Lưu Draft] [Tạo & Gửi duyệt]  │
└──────────────────────────────────────────────────────────────────┘
```

**Field validations (FE):**

| Field | Validate FE |
|---|---|
| `work_order_doctype` | reqd nếu urgency ≠ Emergency (BR-15-01) |
| `work_order_ref` | dynlink; reqd nếu urgency ≠ Emergency |
| `asset` | reqd; auto-fetch từ WO, locked |
| `warehouse_from` | reqd |
| `urgency` | reqd, default Routine |
| `items[].item` | reqd, autocomplete filter `imm_is_medical_spare=1` |
| `items[].qty_requested` | reqd, > 0 |
| `items[].used_for` | reqd |

Khi user thêm/sửa item: gọi `check_part_availability` debounced 500ms → cập nhật cột "Available" và badge "OK?"/"⚠ MR".

**Actions:**

| Button | Action |
|---|---|
| Lưu Draft | `create_allocation` → state Requested |
| Tạo & Gửi duyệt | `create_allocation` → nếu role = Workshop Head: auto-approve, ngược lại gửi notification |
| Hủy | Navigate back |

---

### II.5 AllocationDetail.vue

**Route**: `/imm15/allocations/:name`

**State-based rendering:**

| State | Hiển thị / Actions |
|---|---|
| Requested | Form editable + [Approve] (Workshop Head, VP Block 1) + [Hủy] + [Sửa] |
| Approved | Read-only + [Pick] (Storekeeper) + [Hủy] (Workshop Head) |
| Picked | Read-only + [Issue] (Storekeeper); nếu insufficient + Critical + Emergency → mở `EmergencyOverrideModal` |
| Issued | Badge "✅ Issued" + link `stock_entry_ref` + `audit_flags` (Emergency: 🚨) + [Trả phụ tùng] |
| Returned | Read-only + return Stock Entry ref + condition mỗi item |
| Cancelled | Read-only + reason + actor + datetime |

**Actions matrix:**

| Action | Visible khi | Endpoint |
|---|---|---|
| Sửa | state=Requested, role IN {Biomed, HTM Tech, Storekeeper} | `update_allocation` |
| Approve | state=Requested, role IN `_APPROVE_ALLOCATION_ROLES` | `approve_allocation` |
| Pick | state=Approved, role IN `_ISSUE_ROLES` | workflow action (frappe.workflow) |
| Issue | state=Picked, role IN `_ISSUE_ROLES` | `issue_allocation` |
| Issue Emergency | state=Requested, urgency=Emergency | Mở `EmergencyOverrideModal` |
| Trả phụ tùng | state=Issued | `return_items` (dialog chọn item + condition) |
| Hủy | state IN (Requested, Approved, Picked) | `cancel_allocation` |

---

### II.6 EmergencyOverrideModal.vue

**Trigger**: AllocationDetail khi issued stock không đủ + urgency=Emergency

```
┌────────────────────────────────────────────────┐
│ Emergency Override — Cấp phát khẩn          [✕] │
│ ────────────────────────────────────────────── │
│ ⚠ Tồn kho hiện tại không đủ:                  │
│    SPARE-CT-TUBE-01: cần 1, có 0              │
│                                                │
│ Yêu cầu phê duyệt kép (BR-15-03):             │
│   Approver 1*: [Workshop Head] (you)           │
│   Approver 2*: [VP Block 1     ▼]             │
│   (phải khác Approver 1, IN _OVERRIDE_ROLES)  │
│                                                │
│ Lý do khẩn*:    [textarea (>= 30 ký tự)      ]│
│ Văn bản đính kèm: [Chọn file...              ]│
│                                                │
│ ⚠ Lưu ý: Hành động ghi audit_flags=          │
│   "EMERGENCY_OVERRIDE", penalty IMM-16        │
│                                                │
│              [Hủy] [Xác nhận Override & Issue] │
└────────────────────────────────────────────────┘
```

**Logic:**
- Dropdown Approver 2 chỉ liệt kê users IN `_OVERRIDE_ROLES` AND `user != session.user` (VR-15-10)
- Lý do khẩn phải ≥ 30 ký tự (validate FE)
- API: `issue_allocation` với body `{ override: { approver_2: "...", reason: "...", attachment: "..." } }`
- Sau success: toast "Đã Override & Issue. Audit log đã ghi." + navigate AllocationDetail

---

### II.7 CycleCountList.vue

**Route**: `/imm15/cycle-counts`

```
┌──────────────────────────────────────────────────────────────────┐
│ Kiểm kê chu kỳ                          [+ Tạo phiên kiểm kê]    │
│ ────────────────────────────────────────────────────────────────  │
│ Filter: [Warehouse ▼] [Type ▼] [Status ▼] [Tháng ▼]              │
│                                                                  │
│ ┌────────────────────────────────────────────────────────────┐   │
│ │ # | Số phiếu       | Kho      | Type    | Date     | Status│   │
│ ├────────────────────────────────────────────────────────────┤   │
│ │ 1 | CYC-2026-0017  | KTT      | ABC_A   | 2026-05  | Posted│   │
│ │ 2 | CYC-2026-0016  | KPX      | Cycle   | 2026-04  | Posted│   │
│ │ 3 | CYC-2026-0018  | KTT      | Full    | 2026-05  | Counting│ │
│ └────────────────────────────────────────────────────────────┘   │
│  Hiển thị 1-20/48                                                │
└──────────────────────────────────────────────────────────────────┘
```

**Status badges:**

| State | Badge |
|---|---|
| Planned | Gray "📋 Lên kế hoạch" |
| Counting | Blue "🔢 Đang đếm" |
| Reviewed | Yellow "👁 Đã review" |
| Posted | Green "✅ Đã post" |

---

### II.8 CycleCountDetail.vue

**Route**: `/imm15/cycle-counts/:name`

**Tab: Counting (state=Counting) — mobile-friendly layout:**

```
┌──────────────────────────────────────────────────────────────────┐
│ CYC-2026-0017       Kho: KTT     Type: ABC_A_Monthly             │
│ Status: Counting    ─────────    [Hoàn tất đếm]                  │
│ ────────────────────────────────────────────────────────────────  │
│ ┌── Items đếm (84) ─────────────────────────────────────────┐    │
│ │ Item              | System | Counted    | Delta  | Cause   │    │
│ │ SPARE-CT-TUBE-01  |   1    | [      ]   | --     | --      │    │
│ │ SPARE-MON-BAT     |  12    | [  12  ]   |  0     | --      │    │
│ │ SPARE-FILT-01     |   6    | [   4  ]   | -2 ⚠   | [▼]     │    │
│ │   └ root_cause: Damage    ☑ CAPA required                  │    │
│ │   └ notes: 2 cái ngấm nước sự kiện ngập ...               │    │
│ └───────────────────────────────────────────────────────────┘    │
│                                                                  │
│ Variance summary: 1 item, value -650.000 VND                     │
│ ────────────────────────────────────────────────────────────────  │
│  [Hoàn tất đếm]                                                  │
└──────────────────────────────────────────────────────────────────┘
```

**Counting UX rules:**
- Counted_qty input: debounce 800ms → tự tính variance percent
- Khi `|var_pct| > 5%` hoặc `|var_value| > 5.000.000 VND`: row highlight đỏ + bắt buộc `root_cause` (VR-15-04)
- Hỗ trợ scan QR Item (`custom_internal_qr` từ IMM-04) → auto-navigate đến row
- `Enter` trên counted_qty → chuyển focus hàng tiếp

**Tab: Reviewed/Posted:**

| State | Hiển thị |
|---|---|
| Reviewed | Read-only counted_qty; [Sửa đếm lại] (Storekeeper) + [Post] (Workshop Head) |
| Posted | Read-only; link `stock_reconciliation_ref`, `capa_seeded` count; [Mở SR] |

Dropdown `verified_by`: loại trừ user `counted_by` (VR-15-11).

---

### II.9 ForecastView.vue

**Route**: `/imm15/forecasts/:period`

```
┌──────────────────────────────────────────────────────────────────┐
│ Forecast 2026-Q3   Method: Moving_Avg   Status: Draft            │
│ ────────────────────────────────────────────────────────────────  │
│ Generated by: System (2026-05-01)   Items: 412                   │
│                                                                  │
│ ┌── Items dự báo ──────────────────────────────────────────────┐ │
│ │ Item       | FC Qty | Reorder | Safety | Current | Action    │ │
│ │ SPARE-001  |   12   |   6     |   3    |   2 🔴  | Reorder   │ │
│ │ SPARE-002  |    4   |   2     |   1    |   3 ✅  | Hold      │ │
│ │ SPARE-003  |    0   |   0     |   0    |   8 ⚠   | Reduce    │ │
│ └──────────────────────────────────────────────────────────────┘ │
│                                                                  │
│ KPI: MAPE quý gần nhất 18.4%  ·  Items cần reorder: 27          │
│                                                                  │
│ [Tạo lại bằng method khác ▼]   [Hủy]  [Approve & Auto-MR]       │
└──────────────────────────────────────────────────────────────────┘
```

**Actions:**

| Button | Guard | Action |
|---|---|---|
| Tạo lại | Workshop Head, CMMS Admin | `generate_forecast` với method khác |
| Approve & Auto-MR | `_FORECAST_APPROVE_ROLES` | `approve_forecast` → hiện list MR vừa tạo |
| Hủy | CMMS Admin | Navigate back |

---

### II.10 WatchlistView.vue

**Route**: `/imm15/watchlist`

```
┌──────────────────────────────────────────────────────────────────┐
│ Critical Spare Watchlist                       [+ Thêm entry]    │
│ ────────────────────────────────────────────────────────────────  │
│ Tổng: 47   ·  Đang Breach: 2 🚨                                  │
│                                                                  │
│ ┌────────────────────────────────────────────────────────────┐   │
│ │ Asset            | Spare          | Min | Actual | Status   │   │
│ │ AC-ASSET-CT-01   | SPARE-CT-T01   |  1  |   0    | 🚨 Breach│   │
│ │ AC-ASSET-MRI-01  | SPARE-MRI-COIL |  1  |   1    | ✅ OK    │   │
│ │ AC-ASSET-CCL-01  | SPARE-DEF-PAD  |  4  |   2    | ⚠ Low   │   │
│ └────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

Click row breach → dialog xem CAPA đã seed (link IMM-16).

**Modal thêm entry:**

```
┌────────────────────────────────────────────────┐
│ Thêm Critical Spare Watchlist            [✕]  │
│ ────────────────────────────────────────────── │
│ Asset Critical*:    [AC-ASSET-CT-01 ▼]         │
│ Spare Item*:        [SPARE-CT-TUBE-01 ▼]       │
│   (filter: imm_part_class=Critical)            │
│ Warehouse*:         [Kho trung tâm ▼]          │
│ Min on-hand*:       [1     ]                   │
│ Lý do (audit):      [textarea               ]  │
│                                                │
│                    [Hủy] [Lưu]                 │
└────────────────────────────────────────────────┘
```

VR-15-09: dropdown Spare Item chỉ hiện `imm_part_class=Critical`.

---

### II.11 InventoryDashboard.vue

**Route**: `/imm15/dashboard`

```
┌──────────────────────────────────────────────────────────────────────┐
│ IMM-15 Inventory Dashboard                                           │
│ ────────────────────────────────────────────────────────────────────  │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │
│ │ Turnover │ │ Days-on  │ │ Stock-out│ │ Critical │ │  Cycle   │   │
│ │  /year   │ │  Hand    │ │   30d    │ │  Breach  │ │ Accuracy │   │
│ │   4.2    │ │   47d    │ │    1     │ │    0     │ │  98.6%   │   │
│ └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘   │
│                                                                      │
│ ┌────── Top 10 Low-stock 🔴 ──────────┐ ┌── Critical Breach 🚨 ───┐  │
│ │ Item          Actual  Min  Lead     │ │ SPARE-CT-T01  AC-CT-01  │  │
│ │ SPARE-FILT-01   0      4    14d    │ │ SPARE-MRI-COIL AC-MRI-01│  │
│ │ SPARE-CT-T01    1      1    90d    │ └─────────────────────────┘  │
│ └─────────────────────────────────────┘                              │
│                                                                      │
│ ┌────── Consumption Trend 90 ngày (PM/CM/Repair stack) ─────────┐   │
│ │  ▆▆▆▇▆▇▇▆▇█▇▇▇▆▇▆█▆▇▇▆▇▇▆▇▇█▆▆▆▇  (PM xanh, CM cam, R đỏ)  │   │
│ └───────────────────────────────────────────────────────────────┘   │
│                                                                      │
│ ┌── ABC distribution ──┐  ┌── Forecast MAPE Q ──┐                   │
│ │ A: ████ 84 items     │  │ 18.4% ✅ (target ≤25)│                   │
│ │ B: ██████ 126        │  └──────────────────────┘                   │
│ │ C: ████████ 202      │                                             │
│ └──────────────────────┘                                             │
└──────────────────────────────────────────────────────────────────────┘
```

**KPI tiles:**

| KPI tile | API field | Click action |
|---|---|---|
| Turnover/year | `kpis.stock_turnover_year` | Report tài chính |
| Days-on-Hand | `kpis.days_on_hand_avg` | Filter low days-on-hand |
| Stock-out 30d | `kpis.stockout_incidents_30d` | List allocation bị block |
| Critical Breach | `kpis.critical_breach_hours_30d` | Watchlist breach filter |
| Cycle Accuracy % | `kpis.cycle_accuracy_pct` | CycleCountList filter Posted |
| Forecast MAPE | `kpis.forecast_mape_q` | ForecastView |

Realtime subscribe `imm15:Workshop Head` → KPI tile update khi có `critical_breach_detected` / `allocation_issued` event.

---

### II.12 AssetSpareTab (embedded)

**Route**: `/assets/:name/spares` (tab trong AC Asset detail)

```
┌─────────────────────────────────────────────────────────────────┐
│ Asset: AC-ASSET-CT-01 (CT Philips iCT)                          │
│ Khoa: ICU                                                       │
│ ──────────────────────────────────────────────────────────────  │
│ [Thông tin] [Hồ sơ] [Bảo trì] [Phụ tùng ●] [Lịch sử]          │
│                                                                 │
│ ──── Critical Watchlist (2) ────                                │
│   🔴 SPARE-CT-TUBE-01    min=1   actual=0   🚨 Breach           │
│   ✅ SPARE-CT-DET-01     min=2   actual=3                       │
│                                                                 │
│ ──── Cấp phát gần đây (10) ────                                 │
│   2026-04-22  SAL-2026-0042  WO-PM-...  Issued ✅ 1×T01        │
│   2026-02-08  SAL-2026-0011  WO-CM-...  Issued ✅ 1×T01        │
│                                                                 │
│ ──── Tiêu thụ 12 tháng ────                                     │
│   Tổng giá trị: 510.000.000 VND                                 │
│   Top 3 spare: SPARE-CT-TUBE-01 (3), SPARE-CT-DET-01 (2)...    │
│                                                                 │
│ [+ Tạo Phiếu cấp phát mới]   [Quản lý Watchlist Asset này]     │
└─────────────────────────────────────────────────────────────────┘
```

---

## §III — Pinia Store

### III.1 useImm15Store

**File**: `frontend/src/stores/imm15.ts`. API client: `frontend/src/api/imm15.ts` + `frontend/src/api/inventory.ts`.

> **Note (2026-05-18)**: Store thực tế dùng **Composition API (setup syntax)** — không phải Options API như pseudocode bên dưới. Pseudocode bên dưới là spec kiến trúc ban đầu; implementation thực tế xem `frontend/src/stores/imm15.ts`. State chunks: `allocations`, `cycleCounts`, `forecasts`, `watchlist`, `dashboard`, `lowStockAlerts`. Actions: `fetchAllocations`, `fetchAllocationDetail`, `submitNewAllocation`, `approveAllocationAction`, `issueAllocationAction`, `returnItemsAction`, `fetchCycleCounts`, `createCycleCountAction`, `submitCycleCountAction`, `postCycleCountAction`, `fetchForecasts`, `generateForecastAction`, `approveForecastAction`, `fetchWatchlist`, `addWatchlistAction`, `fetchDashboard`, `fetchLowStockAlerts`.

```typescript
import { defineStore } from 'pinia'
import { useApi } from '@/composables/useApi'

// ─── State Interfaces (architecture spec — actual impl uses Composition API) ──

interface SpareItemsState {
  items: SparePartWithIMM[]
  total: number
  filters: SpareItemsFilter
  loading: boolean
}

interface AllocationState {
  list: IMMSpareAllocation[]
  current: IMMSpareAllocation | null
  total: number
  filters: AllocationFilter
  loading: boolean
  checkingAvailability: boolean
}

interface CycleCountState {
  list: IMMStockCycleCount[]
  current: IMMStockCycleCount | null
  total: number
  filters: CycleCountFilter
  loading: boolean
  savingCount: boolean
}

interface WatchlistState {
  entries: WatchlistEntry[]
  breachCount: number
  loading: boolean
}

interface ForecastState {
  current: IMMSparePartForecast | null
  loading: boolean
  approving: boolean
}

interface DashboardState {
  kpis: Imm15DashboardStats | null
  loading: boolean
  lastRefresh: Date | null
}

// ─── Store ────────────────────────────────────────────────────────────────────

export const useImm15Store = defineStore('imm15', {
  state: (): {
    spareItems: SpareItemsState
    allocation: AllocationState
    cycleCount: CycleCountState
    watchlist: WatchlistState
    forecast: ForecastState
    dashboard: DashboardState
  } => ({
    spareItems: {
      items: [],
      total: 0,
      filters: { part_class: null, abc: null, xyz: null, low_stock_only: false, warehouse: null, search: '' },
      loading: false,
    },
    allocation: {
      list: [],
      current: null,
      total: 0,
      filters: { status: null, urgency: null, asset: null, work_order: null, search: '' },
      loading: false,
      checkingAvailability: false,
    },
    cycleCount: {
      list: [],
      current: null,
      total: 0,
      filters: { warehouse: null, count_type: null, status: null, month: null },
      loading: false,
      savingCount: false,
    },
    watchlist: {
      entries: [],
      breachCount: 0,
      loading: false,
    },
    forecast: {
      current: null,
      loading: false,
      approving: false,
    },
    dashboard: {
      kpis: null,
      loading: false,
      lastRefresh: null,
    },
  }),

  actions: {
    // ── Spare Items ──────────────────────────────────────────────────────────

    async fetchSpareItems(filters?: Partial<SpareItemsFilter>) {
      this.spareItems.loading = true
      const { run } = useApi()
      const result = await run('imm15.list_spare_items', {
        filters: { ...this.spareItems.filters, ...filters },
      })
      if (result.success) {
        this.spareItems.items = result.data.items
        this.spareItems.total = result.data.total
        if (filters) Object.assign(this.spareItems.filters, filters)
      }
      this.spareItems.loading = false
      return result
    },

    async fetchSpareItem(item_code: string) {
      const { run } = useApi()
      return run('imm15.get_spare_item', { item_code })
    },

    // ── Allocations ──────────────────────────────────────────────────────────

    async fetchAllocations(filters?: Partial<AllocationFilter>) {
      this.allocation.loading = true
      const { run } = useApi()
      const result = await run('imm15.list_allocations', {
        filters: { ...this.allocation.filters, ...filters },
      })
      if (result.success) {
        this.allocation.list = result.data.items
        this.allocation.total = result.data.total
        if (filters) Object.assign(this.allocation.filters, filters)
      }
      this.allocation.loading = false
      return result
    },

    async fetchAllocation(name: string) {
      this.allocation.loading = true
      const { run } = useApi()
      const result = await run('imm15.get_allocation', { name })
      if (result.success) this.allocation.current = result.data
      this.allocation.loading = false
      return result
    },

    async createAllocation(payload: CreateAllocationPayload) {
      const { run } = useApi()
      const result = await run('imm15.create_allocation', payload)
      if (result.success) this.allocation.list.unshift(result.data)
      return result
    },

    async approveAllocation(name: string) {
      const { run } = useApi()
      const result = await run('imm15.approve_allocation', { name })
      if (result.success && this.allocation.current?.name === name) {
        this.allocation.current = result.data
      }
      return result
    },

    async issueAllocation(name: string, override?: EmergencyOverridePayload) {
      const { run } = useApi()
      const payload = override ? { name, override } : { name }
      const result = await run('imm15.issue_allocation', payload)
      if (result.success && this.allocation.current?.name === name) {
        this.allocation.current = result.data
      }
      return result
    },

    async returnItems(name: string, returned_items: ReturnItemPayload[]) {
      const { run } = useApi()
      return run('imm15.return_items', { name, returned_items })
    },

    async cancelAllocation(name: string, reason: string) {
      const { run } = useApi()
      return run('imm15.cancel_allocation', { name, reason })
    },

    async checkPartAvailability(item_code: string, qty: number, warehouse: string) {
      this.allocation.checkingAvailability = true
      const { run } = useApi()
      const result = await run('imm15.check_part_availability', { item_code, qty, warehouse })
      this.allocation.checkingAvailability = false
      return result
    },

    // ── Cycle Count ──────────────────────────────────────────────────────────

    async fetchCycleCounts(filters?: Partial<CycleCountFilter>) {
      this.cycleCount.loading = true
      const { run } = useApi()
      const result = await run('imm15.list_cycle_counts', {
        filters: { ...this.cycleCount.filters, ...filters },
      })
      if (result.success) {
        this.cycleCount.list = result.data.items
        this.cycleCount.total = result.data.total
        if (filters) Object.assign(this.cycleCount.filters, filters)
      }
      this.cycleCount.loading = false
      return result
    },

    async fetchCycleCount(name: string) {
      this.cycleCount.loading = true
      const { run } = useApi()
      const result = await run('imm15.get_cycle_count', { name })
      if (result.success) this.cycleCount.current = result.data
      this.cycleCount.loading = false
      return result
    },

    async createCycleCount(payload: CreateCycleCountPayload) {
      const { run } = useApi()
      return run('imm15.create_cycle_count', payload)
    },

    async saveCountedQty(name: string, counted_items: CountedItem[]) {
      this.cycleCount.savingCount = true
      const { run } = useApi()
      const result = await run('imm15.save_counted_qty', { name, counted_items })
      if (result.success && this.cycleCount.current?.name === name) {
        this.cycleCount.current = result.data
      }
      this.cycleCount.savingCount = false
      return result
    },

    async postCycleCount(name: string) {
      const { run } = useApi()
      return run('imm15.post_cycle_count', { name })
    },

    // ── Watchlist ────────────────────────────────────────────────────────────

    async fetchWatchlist(filters?: Record<string, unknown>) {
      this.watchlist.loading = true
      const { run } = useApi()
      const result = await run('imm15.list_watchlist', filters ?? {})
      if (result.success) {
        this.watchlist.entries = result.data.items
        this.watchlist.breachCount = result.data.breach_count
      }
      this.watchlist.loading = false
      return result
    },

    async addWatchlistEntry(payload: AddWatchlistPayload) {
      const { run } = useApi()
      const result = await run('imm15.add_watchlist_entry', payload)
      if (result.success) {
        this.watchlist.entries.unshift(result.data)
        this.watchlist.breachCount = result.data.breach_count ?? this.watchlist.breachCount
      }
      return result
    },

    // ── Forecast ─────────────────────────────────────────────────────────────

    async fetchForecast(period: string) {
      this.forecast.loading = true
      const { run } = useApi()
      const result = await run('imm15.get_forecast', { period })
      if (result.success) this.forecast.current = result.data
      this.forecast.loading = false
      return result
    },

    async generateForecast(period: string, method: string) {
      this.forecast.loading = true
      const { run } = useApi()
      const result = await run('imm15.generate_forecast', { period, method })
      if (result.success) this.forecast.current = result.data
      this.forecast.loading = false
      return result
    },

    async approveForecast(name: string) {
      this.forecast.approving = true
      const { run } = useApi()
      const result = await run('imm15.approve_forecast', { name })
      if (result.success) this.forecast.current = result.data
      this.forecast.approving = false
      return result
    },

    // ── Dashboard ────────────────────────────────────────────────────────────

    async fetchDashboardKPIs() {
      this.dashboard.loading = true
      const { run } = useApi()
      const result = await run('imm15.get_dashboard_kpis', {})
      if (result.success) {
        this.dashboard.kpis = result.data
        this.dashboard.lastRefresh = new Date()
      }
      this.dashboard.loading = false
      return result
    },
  },
})
```

### III.2 Realtime Subscriptions

```typescript
// In InventoryDashboard.vue setup()
import { frappe } from '@/lib/frappe'
import { useImm15Store } from '@/stores/imm15Store'

const store = useImm15Store()

frappe.realtime.on('critical_breach_detected', async () => {
  await store.fetchDashboardKPIs()
  await store.fetchWatchlist()
})

frappe.realtime.on('allocation_issued', async () => {
  await store.fetchDashboardKPIs()
})

// cleanup onUnmounted
onUnmounted(() => {
  frappe.realtime.off('critical_breach_detected')
  frappe.realtime.off('allocation_issued')
})
```

---

## §IV — i18n Key Table

| Key | Tiếng Việt | English fallback |
|---|---|---|
| `imm15.title` | Quản lý Phụ tùng Y tế | Medical Spare Parts Management |
| `imm15.spare_items` | Phụ tùng Y tế | Medical Spare Parts |
| `imm15.allocations` | Phiếu cấp phát phụ tùng | Spare Part Allocations |
| `imm15.cycle_counts` | Kiểm kê chu kỳ | Stock Cycle Counts |
| `imm15.watchlist` | Critical Spare Watchlist | Critical Spare Watchlist |
| `imm15.forecast` | Dự báo nhu cầu | Demand Forecast |
| `imm15.dashboard` | Dashboard Tồn kho | Inventory Dashboard |
| `imm15.create_allocation` | Tạo Phiếu cấp phát | Create Allocation |
| `imm15.approve_allocation` | Phê duyệt cấp phát | Approve Allocation |
| `imm15.issue_allocation` | Xuất kho cấp phát | Issue Allocation |
| `imm15.return_items` | Trả phụ tùng | Return Items |
| `imm15.cancel_allocation` | Hủy Phiếu cấp phát | Cancel Allocation |
| `imm15.emergency_override` | Cấp phát khẩn (Override) | Emergency Override |
| `imm15.emergency_reason` | Lý do khẩn cấp | Emergency Reason |
| `imm15.dual_approver_required` | Yêu cầu phê duyệt kép | Dual Approver Required |
| `imm15.create_cycle_count` | Tạo phiên kiểm kê | Create Cycle Count |
| `imm15.start_counting` | Bắt đầu đếm | Start Counting |
| `imm15.finish_counting` | Hoàn tất đếm | Finish Counting |
| `imm15.post_cycle_count` | Post kết quả kiểm kê | Post Cycle Count |
| `imm15.variance_root_cause` | Nguyên nhân chênh lệch | Variance Root Cause |
| `imm15.capa_required` | Cần tạo CAPA | CAPA Required |
| `imm15.approve_forecast` | Phê duyệt dự báo | Approve Forecast |
| `imm15.auto_mr` | Tự động tạo MR | Auto Material Request |
| `imm15.add_watchlist_entry` | Thêm vào Watchlist | Add Watchlist Entry |
| `imm15.breach_detected` | Phát hiện Breach! | Breach Detected! |
| `imm15.stock_label` | Tồn kho | Stock |
| `imm15.days_on_hand` | Ngày tồn kho | Days on Hand |
| `imm15.stock_turnover` | Vòng quay tồn kho | Stock Turnover |
| `imm15.cycle_accuracy` | Độ chính xác kiểm kê | Cycle Count Accuracy |
| `imm15.critical_breach` | Critical Breach | Critical Breach |
| `imm15.stockout_incident` | Sự cố hết hàng | Stockout Incident |
| `imm15.part_class_critical` | Phụ tùng Quan trọng | Critical Spare |
| `imm15.part_class_major` | Phụ tùng Chính | Major Spare |
| `imm15.part_class_consumable` | Vật tư tiêu hao | Consumable |
| `imm15.urgency_routine` | Thông thường | Routine |
| `imm15.urgency_urgent` | Khẩn | Urgent |
| `imm15.urgency_emergency` | Khẩn cấp | Emergency |
| `imm15.state_requested` | Yêu cầu | Requested |
| `imm15.state_approved` | Đã duyệt | Approved |
| `imm15.state_picked` | Đã pick | Picked |
| `imm15.state_issued` | Đã cấp | Issued |
| `imm15.state_returned` | Đã trả | Returned |
| `imm15.state_cancelled` | Đã hủy | Cancelled |
| `imm15.state_planned` | Lên kế hoạch | Planned |
| `imm15.state_counting` | Đang đếm | Counting |
| `imm15.state_reviewed` | Đã review | Reviewed |
| `imm15.state_posted` | Đã post | Posted |
| `imm15.err_insufficient_stock` | Tồn kho không đủ để cấp phát | Insufficient stock for allocation |
| `imm15.err_wo_required` | Bắt buộc liên kết Work Order | Work Order link required |
| `imm15.err_dual_approver` | Approver 2 phải khác Approver 1 | Approver 2 must differ from Approver 1 |
| `imm15.err_critical_only_watchlist` | Watchlist chỉ nhận phụ tùng Critical | Watchlist only accepts Critical parts |
| `imm15.err_variance_root_cause` | Chênh lệch lớn: bắt buộc điền nguyên nhân | Large variance: root cause required |

---

## §V — Permission-driven UI Rules

| UI Element | Ẩn khi |
|---|---|
| `+ Thêm Item` | role NOT IN {Workshop Head, CMMS Admin} |
| `+ Tạo Phiếu cấp phát` | role NOT IN {Biomed, HTM Tech, Storekeeper, Workshop Head, CMMS Admin} |
| `[Approve]` (allocation) | state ≠ Requested hoặc role NOT IN `_APPROVE_ALLOCATION_ROLES` |
| `[Issue]` (allocation) | state ≠ Picked hoặc role NOT IN `_ISSUE_ROLES` |
| `EmergencyOverrideModal` | urgency ≠ Emergency hoặc stock đủ |
| Approver 2 dropdown | options chỉ user IN `_OVERRIDE_ROLES` AND ≠ session.user |
| `+ Tạo phiên kiểm kê` | role NOT IN {Storekeeper, Workshop Head, CMMS Admin} |
| `[Post]` (cycle count) | state ≠ Reviewed hoặc role NOT IN {Workshop Head, CMMS Admin} |
| `[Approve forecast]` | role NOT IN `_FORECAST_APPROVE_ROLES` |
| `+ Thêm Watchlist` | role NOT IN {Workshop Head, VP Block 1, CMMS Admin} |
| Tab Dashboard | role NOT IN {Storekeeper, Workshop Head, VP Block 1, QA Officer, CMMS Admin, Accountant} |

---

## §VI — UX Patterns

### VI.1 Toast / Notification

| Loại | Style | Ví dụ nội dung |
|---|---|---|
| Success | Xanh | "Đã tạo phiếu SAL-2026-0042 thành công." |
| Warning | Vàng | "Tồn kho thấp: SPARE-001 còn 1 (min 2)." |
| Critical | Đỏ + sticky | "Critical Breach: SPARE-CT-TUBE-01 cho AC-ASSET-CT-01." |
| Error | Đỏ | Hiển thị `response.error.message` (tiếng Việt từ BE) |

### VI.2 Empty States

| Page | Empty message |
|---|---|
| SpareItemsList | "Chưa có phụ tùng nào. [+ Thêm Item]" |
| AllocationList | "Chưa có phiếu cấp phát. Tạo phiếu từ Work Order." |
| CycleCountList | "Chưa có phiên kiểm kê. [+ Tạo phiên]" |
| WatchlistView | "Chưa cấu hình Watchlist. Khuyến nghị thêm cho Critical asset." |
| InventoryDashboard | "Chưa đủ dữ liệu KPI (cần >= 30 ngày)." |

### VI.3 Loading States

- Skeleton loader: list/grid pages
- Spinner: actions (approve/issue/post)
- CycleCountDetail: debounce 800ms trên counted_qty trước khi tính variance

### VI.4 Responsive Breakpoints

| Viewport | Layout |
|---|---|
| >= 1280px | 2 cột: form + side panel summary |
| 768-1279px | 1 cột, summary collapse; CycleCount tối ưu tablet |
| < 768px | Allocation: chỉ list + detail; CycleCount: input số lớn touch-friendly |

### VI.5 Accessibility

| Yêu cầu | Implementation |
|---|---|
| Keyboard navigation | Tab order form fields; Enter submit; CycleCount Enter→hàng tiếp |
| ARIA labels | Buttons, status badges có `aria-label` tiếng Việt |
| Color contrast | Stock badge WCAG AA (4.5:1) |
| Screen reader | Toast critical + modal dùng `role="alert"` / `role="dialog"` |
| Touch targets | CycleCount input >= 44×44 pt |

### VI.6 QR / Barcode

CycleCount `counted_qty` input hỗ trợ scan QR (`custom_internal_qr` từ IMM-04) → auto-navigate đến row item tương ứng.

---

*IMM-15 Module — Wave 2 IMPLEMENTED. Frontend Design v1.1.0. Cập nhật 2026-05-14.*
