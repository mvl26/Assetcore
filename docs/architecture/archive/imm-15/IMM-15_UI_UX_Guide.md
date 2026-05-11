# IMM-15 — UI/UX Guide

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-15 — Spare Parts Inventory Tracking |
| Phiên bản | 1.0.0-draft |
| Ngày cập nhật | 2026-05-04 |
| Trạng thái | PLANNED (Wave 2) |
| Tác giả | AssetCore Team |

---

## 0. Tổng quan màn hình

| # | Trang | Frontend Route (Vue) | Frappe Desk URL | Component |
|---|---|---|---|---|
| 1 | Spare Items List | `/imm15/spares` | `/app/item?imm_is_medical_spare=1` | `views/SpareItemsList.vue` |
| 2 | Spare Item Detail | `/imm15/spares/:item_code` | `/app/item/{name}` | `views/SpareItemDetail.vue` |
| 3 | Allocation List | `/imm15/allocations` | `/app/imm-spare-part-allocation` | `views/AllocationList.vue` |
| 4 | Allocation Detail | `/imm15/allocations/:name` | `/app/imm-spare-part-allocation/{name}` | `views/AllocationDetail.vue` |
| 5 | Allocation Create | `/imm15/allocations/new` | `/app/imm-spare-part-allocation/new` | `views/AllocationCreate.vue` |
| 6 | Cycle Count List | `/imm15/cycle-counts` | `/app/imm-stock-cycle-count` | `views/CycleCountList.vue` |
| 7 | Cycle Count Detail / Counting | `/imm15/cycle-counts/:name` | `/app/imm-stock-cycle-count/{name}` | `views/CycleCountDetail.vue` |
| 8 | Demand Forecast | `/imm15/forecasts/:period` | `/app/imm-spare-demand-forecast` | `views/ForecastView.vue` |
| 9 | Critical Watchlist | `/imm15/watchlist` | `/app/imm-critical-spare-watchlist` | `views/WatchlistView.vue` |
| 10 | Dashboard IMM-15 | `/imm15/dashboard` | `/app/imm15-dashboard` | `views/InventoryDashboard.vue` |
| 11 | Emergency Override Modal | (modal) | — | `components/imm15/EmergencyOverrideModal.vue` |
| 12 | Asset Spare Tab | `/assets/:name/spares` | `/app/asset/{name}` (tab) | (embed in Asset detail) |

State management: `frontend/src/stores/imm15Store.ts`.

---

## 1. Spare Items List (`SpareItemsList.vue`)

### 1.1 Route & Component

| Item | Value |
|---|---|
| Route | `/imm15/spares` |
| Component | `views/SpareItemsList.vue` |
| API call | `imm15.list_spare_items` |
| Permission | All authenticated |

### 1.2 Layout wireframe

```
┌──────────────────────────────────────────────────────────────────────────┐
│ Phụ tùng Y tế                                              [+ Thêm Item] │
│ ──────────────────────────────────────────────────────────────────────── │
│  Filter: [Part Class ▼] [ABC ▼] [XYZ ▼] [☑ Chỉ Low-stock] [Warehouse ▼] │
│         [Tìm kiếm theo OEM / item_code / tên...]                         │
│                                                                          │
│ ┌──────────────────────────────────────────────────────────────────────┐│
│ │ Mã           | Tên                | Class    | ABC | Tồn   | Min  | Lead││
│ ├──────────────────────────────────────────────────────────────────────┤│
│ │ SPARE-CT-T01 | X-ray Tube Phil... | Critical | A   | 1 ⚠   | 1    | 90d ││
│ │ SPARE-MON-B  | Battery Monitor... | Major    | B   | 12 ✅ | 6    | 30d ││
│ │ SPARE-FILT01 | HEPA Filter        | Consum.  | C   | 0 🔴  | 4    | 14d ││
│ └──────────────────────────────────────────────────────────────────────┘│
│  ◀ 1 2 3 ▶   Hiển thị 1-20/412                                           │
└──────────────────────────────────────────────────────────────────────────┘
```

### 1.3 State (Pinia)

| Field | Kiểu | Nguồn |
|---|---|---|
| `items` | Array | `list_spare_items.items` |
| `pagination` | Object | — |
| `filters` | Object | UI (part_class, abc, xyz, low_stock_only, warehouse, search) |
| `loading` | Boolean | — |

### 1.4 Stock badge

| Trạng thái | Màu | Icon |
|---|---|---|
| `actual_qty ≥ min × 2` | Xanh | ✅ |
| `min ≤ actual_qty < min × 2` | Vàng | ⚠ |
| `0 < actual_qty < min` | Cam | 🟠 |
| `actual_qty = 0` | Đỏ | 🔴 |
| Critical breach (Watchlist) | Đỏ + viền đậm | 🚨 |

### 1.5 Actions

| Button | Action |
|---|---|
| `+ Thêm Item` | Navigate `/app/item/new?imm_is_medical_spare=1` (chỉ Workshop Head, CMMS Admin) |
| Click row | Navigate `/imm15/spares/:item_code` |
| Filter change | Re-call `list_spare_items` |

---

## 2. Spare Item Detail (`SpareItemDetail.vue`)

### 2.1 Layout

```
┌──────────────────────────────────────────────────────────────────────┐
│ SPARE-CT-TUBE-01 — X-ray Tube Philips MX                  [Sửa Item]│
│ ──────────────────────────────────────────────────────────────────── │
│ ┌── Phân loại IMM ───────────────────────────────────────┐           │
│ │ Class:    🔴 Critical     ABC: A      XYZ: Y           │           │
│ │ OEM:      MX-2027-TBE-01    Lead time: 90 ngày        │           │
│ │ Min/Max:  1 / 3   Safety: 30d  Traceability: ☑        │           │
│ │ Storage:  Normal           Shelf-life: 36 tháng        │           │
│ │ Compatible Models: [CT Philips iCT 256, Brilliance 64] │           │
│ │ Alternatives: [SPARE-CT-TUBE-01-ALT]                   │           │
│ └────────────────────────────────────────────────────────┘           │
│                                                                      │
│ ┌── Tồn kho theo kho ────────────────────────────────────┐           │
│ │ Kho                  | Actual | Reserved | Valuation    │           │
│ │ Kho trung tâm        |   1    |    0     | 250.000.000  │           │
│ │ Kho phân xưởng       |   0    |    0     |     0        │           │
│ └────────────────────────────────────────────────────────┘           │
│                                                                      │
│ ┌── Watchlist Critical Asset (3) ────────────────────────┐           │
│ │ AC-ASSET-CT-01 (ICU)  min=1   ⚠ Breach 02/05          │           │
│ │ AC-ASSET-CT-02 (CC)   min=1   ✅ OK                    │           │
│ └────────────────────────────────────────────────────────┘           │
│                                                                      │
│ ┌── Giao dịch gần đây (20) ──────────────────────────────┐           │
│ │ 2026-04-22 | Issue   | -1 | SAL-2026-0042 | WO  │           │
│ │ 2026-03-15 | Receipt | +2 | SE-RECV-2026-0011    |  -  │           │
│ │ 2026-02-08 | Issue   | -1 | SAL-2026-0011 | WO  │           │
│ └────────────────────────────────────────────────────────┘           │
│                                                                      │
│ KPI: Days-on-hand 45  ·  Consumption 12m: 4  ·  ABC value share 18% │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.2 Tabs

- **Info**: 14 imm_* fields (như trên)
- **Inventory**: Bins + Watchlist + Reorder suggestion
- **Transactions**: Phân trang 50 latest
- **Forecast**: Nội suy biểu đồ consumption + reorder line

---

## 3. Allocation List (`AllocationList.vue`)

### 3.1 Layout wireframe

```
┌──────────────────────────────────────────────────────────────────────┐
│ Phiếu cấp phát phụ tùng                          [+ Tạo Phiếu mới]   │
│ ──────────────────────────────────────────────────────────────────── │
│  Filter: [Trạng thái ▼] [Urgency ▼] [Asset ▼] [Work Order ▼] [Tìm]   │
│                                                                      │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │ # | Số phiếu          | WO        | Asset      | Urg  | Status   ││
│ ├──────────────────────────────────────────────────────────────────┤│
│ │ 1 | SAL-2026.. | WO-PM-..  | AC-ASSET-..| Rout | Issued ✅ ││
│ │ 2 | SAL-2026.. | WO-CM-..  | AC-ASSET-..| Emer | Issued 🚨 ││
│ │ 3 | SAL-2026.. | WO-PM-..  | AC-ASSET-..| Urg  | Approved ⏳││
│ └──────────────────────────────────────────────────────────────────┘│
│  Hiển thị 1-20/137                                                  │
└──────────────────────────────────────────────────────────────────────┘
```

### 3.2 Status badge

| State | Badge |
|---|---|
| Requested | Yellow "⏳ Yêu cầu" |
| Approved | Blue "📝 Đã duyệt" |
| Picked | Cyan "📦 Đã pick" |
| Issued | Green "✅ Đã cấp" |
| Returned | Gray "↩️ Đã trả" |
| Cancelled | Red "❌ Đã hủy" |
| Emergency flag | thêm icon 🚨 phía sau |

---

## 4. Allocation Create (`AllocationCreate.vue`)

### 4.1 Layout wireframe

```
┌──────────────────────────────────────────────────────────────────┐
│ Tạo Phiếu cấp phát                              Status: [Requested]│
│ ──────────────────────────────────────────────────────────────── │
│ ┌── Liên kết Work Order ──────────────────────────────────┐     │
│ │ WO Type*: [IMM PM Work Order ▼]                         │     │
│ │ WO Ref*:  [WO-PM-2026-0007 ▼]   (auto-fetch asset)     │     │
│ │ Asset:    [AC-ASSET-2026-0001] (locked)                  │     │
│ └──────────────────────────────────────────────────────────┘     │
│                                                                  │
│ ┌── Yêu cầu ──────────────────────────────────────────────┐     │
│ │ Kho xuất*:  [Kho trung tâm  ▼]                          │     │
│ │ Urgency*:   ⦿ Routine  ○ Urgent  ○ Emergency            │     │
│ │ Required:   [📅 2026-05-10]                              │     │
│ └──────────────────────────────────────────────────────────┘     │
│                                                                  │
│ ┌── Phụ tùng ──────────────────────────────────────────────┐    │
│ │ Item*           | Qty | Used For    | Available | OK?    │    │
│ │ [SPARE-001 ▼]  |  2  | Replacement | 5         | ✅      │    │
│ │ [SPARE-002 ▼]  |  1  | Test        | 0         | ⚠ MR   │    │
│ │ [+ Thêm dòng]                                              │    │
│ └────────────────────────────────────────────────────────────┘   │
│                                                                  │
│ Tổng giá trị: 125.300.000 VND                                    │
│ Ghi chú: [textarea                                            ]  │
│                                                                  │
│ ──────────────────────────────────────────────────────────────── │
│   [Hủy]                              [Lưu Draft] [Tạo & Gửi duyệt]│
└──────────────────────────────────────────────────────────────────┘
```

### 4.2 State

| Field | Kiểu | Validate FE |
|---|---|---|
| `work_order_doctype` | enum | reqd nếu urgency ≠ Emergency (BR-15-01) |
| `work_order_ref` | dynlink | reqd nếu urgency ≠ Emergency |
| `asset` | string | reqd, auto-fetch từ WO |
| `warehouse_from` | string | reqd |
| `urgency` | enum | reqd, default Routine |
| `items[].item` | string | reqd, autocomplete (filter `imm_is_medical_spare=1`) |
| `items[].qty_requested` | number | reqd, > 0 |
| `items[].used_for` | enum | reqd |

Inline call `check_part_availability` debounced 500ms khi user thêm item → hiện cột "Available" và "OK?".

### 4.3 Actions

| Button | Action |
|---|---|
| Lưu Draft | `create_allocation` (state Requested) |
| Tạo & Gửi duyệt | `create_allocation` rồi auto submit → `Approved` nếu user là Workshop Head, ngược lại notification |
| Hủy | Navigate back |

Hiển thị toast lỗi tiếng Việt từ `error.message`.

---

## 5. Allocation Detail (`AllocationDetail.vue`)

### 5.1 Layout — theo state

**Requested:** Form editable + nút [Approve] (Workshop Head), [Hủy], [Sửa].

**Approved:** Read-only + nút [Pick] (Storekeeper), [Hủy] (Workshop Head).

**Picked:** Read-only + nút [Issue] (Storekeeper). Nếu insufficient + Critical + Emergency → mở `EmergencyOverrideModal`.

**Issued:** Badge xanh "✅ Issued". Hiện `stock_entry_ref` link, `audit_flags` (nếu Emergency có icon 🚨). Nút [Trả phụ tùng].

**Returned:** Read-only, hiện return Stock Entry ref + condition mỗi item.

**Cancelled:** Read-only, hiện reason + actor + datetime.

### 5.2 Actions matrix

| Action | Visible khi | Endpoint |
|---|---|---|
| Sửa | state = Requested, role IN {Biomed, HTM Tech, Storekeeper} | `update_allocation` |
| Approve | state = Requested, role IN `_APPROVE_ALLOCATION_ROLES` | `approve_allocation` |
| Pick | state = Approved, role IN `_ISSUE_ROLES` | workflow action |
| Issue | state = Picked, role IN `_ISSUE_ROLES` | `issue_allocation` |
| Issue (Emergency) | state = Requested, urgency=Emergency | mở `EmergencyOverrideModal` |
| Trả phụ tùng | state = Issued | `return_items` (dialog) |
| Hủy | state IN (Requested, Approved, Picked) | `cancel_allocation` |

---

## 6. Emergency Override Modal (`EmergencyOverrideModal.vue`)

### 6.1 Layout

```
┌────────────────────────────────────────────────┐
│ Emergency Override — Cấp phát khẩn          [✕] │
│ ────────────────────────────────────────────── │
│ ⚠ Tồn kho hiện tại không đủ:                  │
│    SPARE-CT-TUBE-01: cần 1, có 0              │
│                                                │
│ Yêu cầu phê duyệt kép (BR-15-03):              │
│   Approver 1*: [Workshop Head] (you)           │
│   Approver 2*: [VP Block 1     ▼]              │
│   (phải khác Approver 1, IN _OVERRIDE_ROLES)   │
│                                                │
│ Lý do khẩn*:    [textarea (≥ 30 ký tự)       ] │
│ Văn bản đính kèm: 📎 [Chọn file...           ] │
│                                                │
│ ⚠ Lưu ý: Hành động ghi audit_flags=             │
│   "EMERGENCY_OVERRIDE", penalty IMM-16          │
│                                                │
│              [Hủy] [Xác nhận Override & Issue] │
└────────────────────────────────────────────────┘
```

API: `issue_allocation` với body.override. VR-15-10 enforce 2 approver khác nhau.

Sau success: toast "Đã Override & Issue. Audit log đã ghi." + navigate detail.

---

## 7. Cycle Count List & Detail

### 7.1 Cycle Count List wireframe

```
┌──────────────────────────────────────────────────────────────────┐
│ Kiểm kê chu kỳ                          [+ Tạo phiên kiểm kê]    │
│ ──────────────────────────────────────────────────────────────── │
│ Filter: [Warehouse ▼] [Type ▼] [Status ▼] [Tháng ▼]              │
│                                                                  │
│ ┌────────────────────────────────────────────────────────────┐  │
│ │ # | Số phiếu       | Kho      | Type    | Date     | Status││
│ ├────────────────────────────────────────────────────────────┤  │
│ │ 1 | CYC-... | KTT      | ABC-A   | 2026-05  | Posted││
│ │ 2 | CYC-... | KPX      | Cycle   | 2026-04  | Posted││
│ └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

### 7.2 Cycle Count Detail — Counting tab (mobile-friendly)

```
┌──────────────────────────────────────────────────────────────┐
│ CYC-2026-0017       Kho: KTT    Type: ABC_A_Monthly   │
│ Status: Counting   ────────  [Hoàn tất đếm]                  │
│ ──────────────────────────────────────────────────────────── │
│ ┌── Items đếm (84) ──────────────────────────────────────┐   │
│ │ Item              | System | Counted    | Δ      | Cause│   │
│ │ SPARE-CT-TUBE-01  |   1    | [_____]    | --     | --   │   │
│ │ SPARE-MON-BAT     |  12    | [12  ]     | 0      | --   │   │
│ │ SPARE-FILT-01     |   6    | [4   ]     | -2 ⚠   | [▼ ] │   │
│ │   └ root_cause: Damage     ☑ CAPA required               │   │
│ │   └ notes: 2 cái ngấm nước sự kiện ngập ...              │   │
│ └──────────────────────────────────────────────────────────┘   │
│                                                              │
│ Variance summary: 1 item, value -650.000 VND                 │
│ ──────────────────────────────────────────────────────────── │
│  [Hoàn tất đếm]                                              │
└──────────────────────────────────────────────────────────────┘
```

### 7.3 Cycle Count Detail — Reviewed/Posted

| State | Hiển thị |
|---|---|
| Reviewed | Read-only counted_qty; nút [Sửa đếm lại] (Storekeeper) + [Post] (Workshop Head) |
| Posted | Read-only; hiện `stock_reconciliation_ref`, `capa_seeded` count, nút [Mở SR] |

VR-15-04 enforce trên FE: khi `|var_pct| > 5%` hoặc `|var_value| > 5M VND` → row highlight đỏ + bắt buộc field `root_cause`.
VR-15-11: dropdown `verified_by` loại trừ user `counted_by`.

---

## 8. Demand Forecast (`ForecastView.vue`)

```
┌──────────────────────────────────────────────────────────────────┐
│ Forecast 2026-Q3   Method: Moving_Avg   Status: Draft            │
│ ──────────────────────────────────────────────────────────────── │
│ Generated by: System (2026-05-01)   Items: 412                   │
│                                                                  │
│ ┌── Items dự báo ────────────────────────────────────────────┐  │
│ │ Item       | FC Qty | Reorder | Safety | Current | Action  │  │
│ │ SPARE-001  |   12   |   6     |   3    |   2 🔴  | Reorder │  │
│ │ SPARE-002  |    4   |   2     |   1    |   3 ✅  | Hold    │  │
│ │ SPARE-003  |    0   |   0     |   0    |   8 ⚠   | Reduce  │  │
│ └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│ KPI: MAPE quý gần nhất 18.4%  · Items cần reorder: 27            │
│                                                                  │
│ [Tạo lại bằng method khác ▼]   [Hủy] [Approve & Auto-MR]         │
└──────────────────────────────────────────────────────────────────┘
```

Nút [Approve & Auto-MR] chỉ visible với `_FORECAST_APPROVE_ROLES`. Sau approve hiện list MR vừa tạo.

---

## 9. Critical Watchlist (`WatchlistView.vue`)

```
┌──────────────────────────────────────────────────────────────────┐
│ Critical Spare Watchlist                       [+ Thêm entry]    │
│ ──────────────────────────────────────────────────────────────── │
│ Tổng: 47   ·  Đang Breach: 2 🚨                                  │
│                                                                  │
│ ┌────────────────────────────────────────────────────────────┐  │
│ │ Asset            | Spare        | Min | Actual | Status    │  │
│ │ AC-ASSET-CT-01   | SPARE-CT-T01 | 1   | 0      | 🚨 Breach │  │
│ │ AC-ASSET-MRI-01  | SPARE-MRI-COIL | 1 | 1      | ✅ OK      │  │
│ │ AC-ASSET-CCL-01  | SPARE-DEF-PAD | 4   | 2      | ⚠ Low    │  │
│ └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

Click row breach → mở dialog xem CAPA đã seed (link IMM-16).

Nút [+ Thêm entry] mở modal:

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
│                    [Hủy] [Lưu]                  │
└────────────────────────────────────────────────┘
```

VR-15-09 enforce: dropdown chỉ hiện Item có `imm_part_class=Critical`.

---

## 10. Dashboard IMM-15 (`InventoryDashboard.vue`)

### 10.1 Layout

```
┌──────────────────────────────────────────────────────────────────────┐
│ IMM-15 Inventory Dashboard                                            │
│ ──────────────────────────────────────────────────────────────────── │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐    │
│ │ Turnover │ │ Days-on  │ │ Stock-out│ │ Crit     │ │ Cycle    │    │
│ │  /year   │ │  Hand    │ │  30d     │ │ Breach h │ │ Accuracy │    │
│ │   4.2    │ │   47d    │ │    1     │ │    0     │ │  98.6%   │    │
│ └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘    │
│                                                                      │
│ ┌────── Top 10 Low-stock 🔴 ─────────┐ ┌───── Critical Breach 🚨 ──┐ │
│ │ Item            Actual  Min  Lead   │ │ SPARE-CT-T01  AC-CT-01    │ │
│ │ SPARE-FILT-01     0      4    14d   │ │ SPARE-MRI-COIL AC-MRI-01  │ │
│ │ SPARE-CT-T01      1      1    90d   │ │                            │ │
│ │ ...                                  │ │                            │ │
│ └──────────────────────────────────────┘ └────────────────────────────┘ │
│                                                                      │
│ ┌────── Consumption Trend 90 ngày (PM/CM/Repair stack) ─────────┐    │
│ │  ▆▆▆▇▆▇▇▆▇█▇▇▇▆▇▆█▆▇▇▆▇▇▆▇▇█▆▆▆▇  (PM xanh, CM cam, R đỏ)   │    │
│ └────────────────────────────────────────────────────────────────┘    │
│                                                                      │
│ ┌── ABC distribution ─┐  ┌── Forecast MAPE Q ─┐                     │
│ │ A: ████ 84 items    │  │ 18.4% ✅ (target ≤25)│                     │
│ │ B: ██████ 126       │  └─────────────────────┘                     │
│ │ C: ████████ 202     │                                              │
│ └─────────────────────┘                                              │
└──────────────────────────────────────────────────────────────────────┘
```

### 10.2 KPIs

| KPI | API field | Click action |
|---|---|---|
| Turnover/year | `kpis.stock_turnover_year` | Trang report tài chính |
| Days-on-Hand | `kpis.days_on_hand_avg` | Filter low days-on-hand |
| Stock-out 30d | `kpis.stockout_incidents_30d` | List allocation bị block |
| Critical Breach h | `kpis.critical_breach_hours_30d` | Watchlist breach |
| Cycle Accuracy % | `kpis.cycle_accuracy_pct` | Cycle count list filter Posted |
| Forecast MAPE | `kpis.forecast_mape_q` | Forecast trang chi tiết |

Realtime subscribe `imm15:Workshop Head` → KPI tile update khi có `critical_breach_detected` / `allocation_issued` event.

---

## 11. Asset Spare Tab (Asset detail)

### 11.1 Layout

```
┌─────────────────────────────────────────────────────────────────┐
│ Asset: AC-ASSET-CT-01 (CT Philips iCT)                          │
│ Khoa: ICU                                                       │
│ ──────────────────────────────────────────────────────────────  │
│ [Thông tin] [Hồ sơ] [Bảo trì] [Phụ tùng ●] [Lịch sử]            │
│                                                                 │
│ ──── Critical Watchlist (2) ────                                │
│   🔴 SPARE-CT-TUBE-01    min=1   actual=0   🚨 Breach           │
│   ✅ SPARE-CT-DET-01     min=2   actual=3                       │
│                                                                 │
│ ──── Cấp phát gần đây (10) ────                                 │
│   2026-04-22  SAL-2026-0042  WO-PM-...  Issued ✅ 1×T01  │
│   2026-02-08  SAL-2026-0011  WO-CM-...  Issued ✅ 1×T01  │
│                                                                 │
│ ──── Tiêu thụ 12 tháng ────                                     │
│   Tổng giá trị: 510.000.000 VND                                 │
│   Top 3 spare: SPARE-CT-TUBE-01 (3), SPARE-CT-DET-01 (2)...     │
│                                                                 │
│ [+ Tạo Phiếu cấp phát mới]   [Quản lý Watchlist Asset này]      │
└─────────────────────────────────────────────────────────────────┘
```

### 11.2 Actions

| Button | Action |
|---|---|
| `+ Tạo Phiếu cấp phát mới` | Navigate AllocationCreate với asset pre-fill |
| `Quản lý Watchlist` | Mở WatchlistView filter theo asset |

---

## 12. UX Patterns chung

### 12.1 Toast / Notification

| Loại | Màu | Nội dung mẫu |
|---|---|---|
| Success | Xanh | "✅ Đã tạo phiếu SAL-..." |
| Warning | Vàng | "⚠️ Tồn kho thấp: SPARE-001 còn 1 (min 2)" |
| Critical | Đỏ + sticky | "🚨 Critical Breach: SPARE-CT-TUBE-01 cho AC-ASSET-CT-01" |
| Error | Đỏ | Hiển thị `response.error.message` (tiếng Việt từ VR/`_err`) |

### 12.2 Empty states

| Page | Empty message |
|---|---|
| Spare Items List | "Chưa có phụ tùng nào. [+ Thêm Item]" |
| Allocation List | "Chưa có phiếu cấp phát. Tạo phiếu từ Work Order." |
| Cycle Count List | "Chưa có phiên kiểm kê. [+ Tạo phiên]" |
| Watchlist | "Chưa cấu hình watchlist. Khuyến nghị thêm cho Critical asset." |
| Dashboard | "Chưa đủ dữ liệu KPI (cần ≥ 30 ngày)." |

### 12.3 Loading states

Skeleton loader cho list/grid. Spinner cho actions (approve/issue/post). Cycle count counted_qty input có debounce 800ms trước khi compute variance.

### 12.4 Indicator badges

| Cờ | Icon |
|---|---|
| Emergency override | 🚨 (sau status) |
| Traceability required | 🔖 (cạnh item code) |
| Critical part class | 🔴 (cạnh item name) |
| Cold chain storage | ❄️ (cạnh storage_condition) |
| Hazardous | ☣️ (cạnh storage_condition) |

### 12.5 Responsive

- Desktop ≥ 1280px: Layout 2 column (form + side panel summary)
- Tablet 768-1279px: 1 column, summary collapse — **Cycle Count tối ưu cho tablet** (Storekeeper đếm bằng tablet đi quanh kho)
- Mobile < 768px: Allocation chỉ list + detail; Cycle Count hỗ trợ counted_qty input số lớn để dễ chạm

### 12.6 Bar-code / QR

Cycle Count counted_qty input: hỗ trợ scan QR Item (`custom_internal_qr` từ IMM-04) → tự động navigate row đó.

---

## 13. Permission-driven UI

| UI Element | Hide khi |
|---|---|
| `+ Thêm Item` | role NOT IN {Workshop Head, CMMS Admin} |
| `+ Tạo Phiếu cấp phát` | role NOT IN {Biomed, HTM Tech, Storekeeper, Workshop Head, CMMS Admin} |
| Nút [Approve] allocation | state ≠ Requested hoặc role NOT IN `_APPROVE_ALLOCATION_ROLES` |
| Nút [Issue] allocation | state ≠ Picked hoặc role NOT IN `_ISSUE_ROLES` |
| Modal Emergency Override | urgency ≠ Emergency hoặc tồn kho đủ |
| Approver 2 dropdown | options chỉ user IN `_OVERRIDE_ROLES` AND ≠ session.user |
| `+ Tạo phiên kiểm kê` | role NOT IN {Storekeeper, Workshop Head, CMMS Admin} |
| Nút [Post] cycle count | state ≠ Reviewed hoặc role NOT IN {Workshop Head, CMMS Admin} |
| Nút [Approve forecast] | role NOT IN `_FORECAST_APPROVE_ROLES` |
| Nút [+ Thêm Watchlist] | role NOT IN {Workshop Head, VP Block 1, CMMS Admin} |
| Tab Dashboard | role NOT IN {Storekeeper, Workshop Head, VP Block 1, Tổ HC-QLCL, CMMS Admin, Accountant} |

---

## 14. Accessibility

| Yêu cầu | Implementation |
|---|---|
| Keyboard navigation | Tab order qua form fields; Enter submit; Cycle count Counted_qty input có `Enter` chuyển hàng tiếp theo |
| ARIA labels | Buttons, status badges có `aria-label` tiếng Việt |
| Color contrast | Stock badge đảm bảo WCAG AA (4.5:1) |
| Screen reader | Toast critical + modal sử dụng `role="alert"` / `role="dialog"` |
| Touch targets | Cycle count input ≥ 44×44 pt (mobile) |

---

## 15. Internationalization

Mọi label/error message đi qua `frappe._()`. Chuỗi UI chính:

| Tiếng Việt | English fallback |
|---|---|
| Phụ tùng Y tế | Medical Spare Parts |
| Phiếu cấp phát phụ tùng | Spare Part Allocation |
| Kiểm kê chu kỳ | Stock Cycle Count |
| Watchlist Critical | Critical Spare Watchlist |
| Tồn kho | Stock |
| Cấp phát khẩn | Emergency Override |
| Dự báo nhu cầu | Demand Forecast |
| Tự động đặt hàng | Auto Material Request |
