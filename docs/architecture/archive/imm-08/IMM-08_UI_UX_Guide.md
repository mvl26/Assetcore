# IMM-08 — UI/UX Guide

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-08 — Preventive Maintenance |
| Phiên bản | 2.0.0 |
| Ngày cập nhật | 2026-04-18 |
| Trạng thái | LIVE |
| Tác giả | AssetCore Team |

---

## 0. Tổng quan

IMM-08 ship **4 màn hình Vue 3** (đã code) bám theo design system AssetCore (Vue 3 + TypeScript + Tailwind + Frappe UI). Tất cả gọi API qua Pinia store `useImm08Store` (`frontend/src/stores/imm08.ts`).

| Screen | Route | Component | Target user |
|---|---|---|---|
| PM Dashboard | `/pm/dashboard` | `PMDashboardView.vue` | Workshop Head, VP Block2 |
| PM Calendar | `/pm/calendar` | `PMCalendarView.vue` | Workshop Head |
| PM Work Order List | `/pm/work-orders` | `PMWorkOrderListView.vue` | Workshop Head, HTM Technician |
| PM Work Order Detail | `/pm/work-orders/:id` | `PMWorkOrderDetailView.vue` | HTM Technician (mobile + desktop) |

Sidebar group: **"IMM-08 Bảo trì PM"** với 3 entry (Calendar / List / Dashboard).

---

## 1. Navigation & Routing

### 1.1 Router entries (`frontend/src/router/index.ts`)

```ts
{ path: '/pm', redirect: '/pm/dashboard' },
{ path: '/pm/dashboard',     name: 'PMDashboard',      component: () => import('@/views/PMDashboardView.vue') },
{ path: '/pm/calendar',      name: 'PMCalendar',       component: () => import('@/views/PMCalendarView.vue') },
{ path: '/pm/work-orders',   name: 'PMWorkOrderList',  component: () => import('@/views/PMWorkOrderListView.vue') },
{ path: '/pm/work-orders/:id', name: 'PMWorkOrderDetail', component: () => import('@/views/PMWorkOrderDetailView.vue'), props: true },
```

Tất cả route có `meta.requiresAuth: true`.

### 1.2 Sidebar entry

```
■ IMM-08 Bảo trì PM
  ├─ Lịch bảo trì     → /pm/calendar
  ├─ Phiếu bảo trì    → /pm/work-orders
  └─ Dashboard PM      → /pm/dashboard
```

---

## 2. Color & Status mapping

| Trạng thái WO | Màu | Chip | Icon |
|---|---|---|---|
| Open | neutral-600 | outline | `circle` |
| In Progress | info-500 (xanh dương) | soft | `play` |
| Pending–Device Busy | warning-300 | soft | `pause` |
| Overdue | danger-500 | solid | `alert-triangle` |
| Completed | success-500 | solid | `check-circle` |
| Halted–Major Failure | danger-700 | solid + ring | `octagon-x` |
| Cancelled | neutral-400 | outline dashed | `x` |

| `is_late` | True → badge đỏ "Trễ {N} ngày" cạnh status |
| `overall_result` | Pass=success · Pass with Minor Issues=warning · Fail=danger |
| `risk_class` Class III | Badge đỏ "CRITICAL" trước description checklist item |

---

## 3. Screen — PM Dashboard

| Thuộc tính | Giá trị |
|---|---|
| Route | `/pm/dashboard` |
| Component | `PMDashboardView.vue` |
| Permissions | Workshop Head, VP Block2, CMMS Admin |

### 3.1 Layout

```
┌──────────────────────────────────────────────────────────────────┐
│  Dashboard Bảo trì PM                          [Tháng 4/2026 ▼] │
├──────┬──────┬──────┬──────┬──────────────────────────────────────┤
│ 87.5%│  16  │  14  │   2  │  3.5 ngày                            │
│ Comp.│ Tổng │ On-  │ Quá  │  Trễ trung bình                      │
│ rate │ lịch │ time │ hạn  │                                      │
├──────┴──────┴──────┴──────┴──────────────────────────────────────┤
│  TREND 6 THÁNG                                                   │
│  100% ─────●───────●─────●                                       │
│   75%   ●        ●     ●                                         │
│        Nov Dec Jan Feb Mar Apr                                    │
├──────────────────────────────────────────────────────────────────┤
│  THIẾT BỊ QUÁ HẠN                                                │
│  🔴 PM-WO-2026-00007  Monitor Philips  Quá hạn 8 ngày  [Xem]    │
│  🔴 PM-WO-2026-00012  Máy thở Drager   Quá hạn 3 ngày  [Xem]    │
└──────────────────────────────────────────────────────────────────┘
```

### 3.2 State (Pinia)

```ts
dashboardStats: PMDashboardStats   // { kpis, trend_6months }
loading: boolean
```

### 3.3 Actions

| Action | API | Trigger |
|---|---|---|
| Load stats | `get_pm_dashboard_stats?year&month` | `onMounted`, change month |
| Click KPI card "Quá hạn" | navigate `/pm/work-orders?status=Overdue` | click |
| Click row trong bảng overdue | navigate `/pm/work-orders/{name}` | click |

### 3.4 Permissions UI

- VP Block2: read-only.
- Workshop Head + CMMS Admin: full + có nút "Xuất báo cáo PDF" (planned).

---

## 4. Screen — PM Calendar

| Thuộc tính | Giá trị |
|---|---|
| Route | `/pm/calendar` |
| Component | `PMCalendarView.vue` |
| Permissions | Workshop Head, HTM Technician (xem WO của mình) |

### 4.1 Layout

```
┌──────────────────────────────────────────────────────────────────┐
│  Lịch PM Tháng 4/2026                  [◀]  [Tháng] [Tuần]  [▶] │
│  Filter: [KTV ▼] [Asset ▼]                                       │
├───────┬───────┬───────┬───────┬───────┬───────┬───────┬───────┤
│  T2   │  T3   │  T4   │  T5   │  T6   │  T7   │  CN   │
│  14   │  15   │  16   │  17   │  18   │  19   │  20   │
│       │       │       │ 🟡PM-1│       │ 🔴PM-7│       │
│       │       │       │Máy thở│       │Monitor│       │
│       │       │       │OVERDUE│       │       │       │
├───────┼───────┼───────┼───────┼───────┼───────┼───────┤
│  21   │  22   │  23   │  24   │  25   │  26   │  27   │
│       │ 🟢PM-12│      │       │ 🟡PM15│      │       │
└───────┴───────┴───────┴───────┴───────┴───────┴───────┘
```

### 4.2 State

```ts
calendarEvents: PMCalendarEvent[]
calendarSummary: { total, completed, overdue, pending }
```

### 4.3 Actions

| Action | API | Trigger |
|---|---|---|
| Load month | `get_pm_calendar?year&month&technician?&asset_ref?` | mount, change month |
| Click event | open right drawer detail (lazy GET `get_pm_work_order`) | click |
| (Planned) Drag-drop | `reschedule_pm` với confirm modal | drag |

### 4.4 Permissions UI

- Workshop Head: thấy tất cả.
- HTM Technician: filter `technician=session.user` mặc định.

---

## 5. Screen — PM Work Order List

| Thuộc tính | Giá trị |
|---|---|
| Route | `/pm/work-orders` |
| Component | `PMWorkOrderListView.vue` |
| Permissions | All IMM roles |

### 5.1 Layout

```
┌──────────────────────────────────────────────────────────────────┐
│ Phiếu Bảo trì PM                          [+ Tạo PM thủ công]    │
│ Filter: [Status ▼] [KTV ▼] [Asset...] [Từ ngày] [Đến ngày]      │
├──────────┬─────────────┬───────────┬─────────┬───────┬──────────┤
│ Mã WO    │ Thiết bị    │ PM Type   │ Đến hạn │ KTV   │ Trạng thái│
├──────────┼─────────────┼───────────┼─────────┼───────┼──────────┤
│ PM-00001 │ Máy thở DC  │ Quarterly │ 17/04   │ ktv1  │🔴 Overdue │
│ PM-00003 │ Monitor PH  │ Annual    │ 22/04   │ ktv2  │🟢 Done    │
└──────────┴─────────────┴───────────┴─────────┴───────┴──────────┘
                                          Trang 1/3   [← →]
```

### 5.2 State

```ts
workOrders: PMWorkOrder[]
pagination: { page, total, total_pages, page_size }
```

### 5.3 Actions

| Action | API | Trigger |
|---|---|---|
| Load list | `list_pm_work_orders?filters&page&page_size` | mount, change filter |
| Click row | navigate `/pm/work-orders/{name}` | click |
| Bulk assign (planned) | `assign_technician` × N | bulk select |

### 5.4 Permissions UI

- HTM Technician: mặc định filter `assigned_to=session.user` (toggle "Chỉ WO của tôi").
- Workshop Head: full filters + bulk actions.

---

## 6. Screen — PM Work Order Detail (Checklist execution)

| Thuộc tính | Giá trị |
|---|---|
| Route | `/pm/work-orders/:id` |
| Component | `PMWorkOrderDetailView.vue` |
| Permissions | KTV (assigned), Workshop Head, Biomed Engineer |

### 6.1 Desktop layout

```
┌──────────────────────────────────────────────────────────────────┐
│ ← PM-WO-2026-00001 — Máy thở Drager Evita V500    🟡 In Progress│
├──────────────────────────────────────────────────────────────────┤
│ THÔNG TIN                                                        │
│ Thiết bị: AC-ASSET-2026-0003     │ Đến hạn: 17/04/2026                │
│ KTV:      ktv1@bv.vn        │ Loại PM: Quarterly                 │
│ Khoa:     ICU               │ Class:   III ⚠ Cần ảnh             │
├──────────────────────────────────────────────────────────────────┤
│ CHECKLIST  (4 / 10 đã điền)                                      │
│ ▓▓▓▓░░░░░░ 40%                                                   │
│                                                                  │
│ [1] Kiểm tra điện áp đầu vào (210–240V)         [CRITICAL]      │
│     ○ Pass  ● Fail-Minor  ○ Fail-Major  ○ N/A                   │
│     Giá trị đo: [225] V    Notes: [.....rò rỉ.....] *bắt buộc   │
│     [📷 Đính kèm ảnh]                                            │
│                                                                  │
│ [2] Kiểm tra áp suất khí nén (3.5–6 bar)        [CRITICAL]      │
│     ● Pass  ○ Fail-Minor  ○ Fail-Major  ○ N/A                   │
│     Giá trị đo: [4.2] bar                                       │
│ ...                                                              │
├──────────────────────────────────────────────────────────────────┤
│ KẾT QUẢ TỔNG THỂ                                                 │
│ Tóm tắt KTV:  [.................................]                │
│ Đã gắn sticker PM: ☐                                            │
│ Thời gian: [__] phút   Ảnh: [📎 Upload] (≥1 nếu Class III)      │
├──────────────────────────────────────────────────────────────────┤
│  [Báo lỗi Major 🔴]   [Hoãn lịch]   [Lưu nháp]   [Hoàn thành ✓]│
└──────────────────────────────────────────────────────────────────┘
```

### 6.2 Mobile layout (≤ 640px)

One-item-per-screen pattern. Swipe left/right để chuyển checklist item. Nút Pass/Fail tap target ≥ 48px.

### 6.3 State

```ts
currentWO: PMWorkOrder
checklistComplete: computed → all items có result
```

### 6.4 Actions

| Action | API | Trigger | Validation |
|---|---|---|---|
| Load detail | `get_pm_work_order?name` | mount | — |
| Update item result | local mutation (auto-save planned) | radio click | `notes` required khi Fail-* (VR-08-06) |
| Upload ảnh | Frappe File Upload | click attach | Max 10MB / ảnh |
| Submit Hoàn thành | `submit_pm_result` | click | Disabled cho đến `checklistComplete` (BR-08-08) + ảnh nếu Class III (BR-08-06) |
| Báo lỗi Major | `report_major_failure` | click + confirm modal | Description ≥ 10 ký tự |
| Hoãn lịch | `reschedule_pm` | modal với date + reason | reason ≥ 5 ký tự (VR-08-09) |

### 6.5 UI guards

- Nút **Hoàn thành** disabled nếu checklist chưa 100%.
- Khi user chọn `Fail-Major` trên item `is_critical=true` → toast warning, focus chuyển sang nút "Báo lỗi Major" (mở modal xác nhận).
- Khi `risk_class=III` mà chưa upload ảnh → tooltip đỏ trên nút Hoàn thành.

---

## 7. Pinia Store — `useImm08Store`

File: `frontend/src/stores/imm08.ts`. Exports:

| State | Type |
|---|---|
| `workOrders` | `PMWorkOrder[]` |
| `currentWO` | `PMWorkOrder \| null` |
| `calendarEvents` | `PMCalendarEvent[]` |
| `calendarSummary` | `{ total, completed, overdue, pending }` |
| `dashboardStats` | `PMDashboardStats \| null` |
| `pmHistory` | `PMTaskLog[]` |
| `pagination` | `{ page, total, total_pages, page_size }` |
| `loading`, `error` | — |

| Action | Wraps API |
|---|---|
| `fetchWorkOrders(filters, page, pageSize)` | `list_pm_work_orders` |
| `fetchWorkOrder(name)` | `get_pm_work_order` |
| `assignTech(name, tech, date)` | `assign_technician` |
| `submitResult(name, payload)` | `submit_pm_result` |
| `reportMajor(name, desc, indexes)` | `report_major_failure` |
| `fetchCalendar(year, month, ...)` | `get_pm_calendar` |
| `fetchDashboard(year, month)` | `get_pm_dashboard_stats` |
| `reschedule(name, newDate, reason)` | `reschedule_pm` |
| `fetchHistory(assetRef, limit)` | `get_asset_pm_history` |

API client: `frontend/src/api/imm08.ts` (axios wrapper, parse `message.success/data/error/code`).

---

## 8. Notifications

| Event | Channel | Recipient |
|---|---|---|
| WO mới được assign | Toast + (planned) Frappe Notification | KTV |
| WO Overdue daily | Email | Workshop Head + (>7d) VP Block2 |
| Major Failure | Email khẩn HTML | Workshop Head + VP Block2 |
| Tóm tắt WO mới hôm nay | Email | Workshop Head |

---

## 9. Accessibility

| # | Yêu cầu |
|---|---|
| 1 | Contrast text/background ≥ 4.5:1 (WCAG AA) |
| 2 | Tap target mobile ≥ 48px |
| 3 | Focus ring 2px primary trên tất cả button/input |
| 4 | ARIA label cho icon-only button (vd "Báo lỗi Major", "Đính kèm ảnh") |
| 5 | `<html lang="vi">` |
| 6 | Form error có `aria-describedby` link sang error text |

---

## 10. Responsive matrix

| Màn | Mobile (<640) | Tablet (640–1024) | Desktop (>1024) |
|---|---|---|---|
| Dashboard | KPI 1 cột | 3 cột | 5 cột + chart full width |
| Calendar | Day view list | Week view | Month grid |
| List | Card list | Table 5 cột | Table full + filter sidebar |
| Detail | One-item-per-screen, swipe | Single column | 2 cột (info + checklist) |

---

*End of UI/UX Guide v2.0.0 — IMM-08 Preventive Maintenance*
