# IMM-08 — UI/UX Design
## Layout, Interactions & Mobile Experience

**Module:** IMM-08  
**Version:** 1.0  
**Ngày:** 2026-04-17  
**Trạng thái:** Draft

---

## 1. Vị trí trong Navigation Sidebar

```
┌─────────────────────────┐
│  AC  AssetCore          │
├─────────────────────────┤
│ ■ Tổng quan             │
│   └─ Dashboard          │
├─────────────────────────┤
│ ■ IMM-04 Lắp đặt        │
│   ├─ Danh sách phiếu    │
│   └─ Tạo phiếu mới      │
├─────────────────────────┤
│ ■ IMM-05 Hồ sơ          │
│   ├─ Quản lý Hồ sơ      │
│   └─ Tải lên tài liệu   │
├─────────────────────────┤
│ ■ IMM-08 Bảo trì PM  ◄  │  ← NEW
│   ├─ Lịch bảo trì       │
│   ├─ Phiếu bảo trì      │
│   └─ Dashboard PM        │
└─────────────────────────┘
```

**Routes:**
- `/pm` → PM Dashboard (redirect)
- `/pm/calendar` → Lịch bảo trì tháng/tuần
- `/pm/work-orders` → Danh sách PM WO
- `/pm/work-orders/:id` → Chi tiết / Điền checklist
- `/pm/dashboard` → KPI Dashboard

---

## 2. Màn hình 1: PM Dashboard (`/pm/dashboard`)

**Target user:** Workshop Manager, PTP Khối 2  
**Mục đích:** Overview nhanh tình trạng PM toàn bộ hệ thống

```
┌──────────────────────────────────────────────────────────────────┐
│  Dashboard Bảo trì Định kỳ (PM)           [Tháng 4 / 2026 ▼]    │
├────────────┬────────────┬────────────┬────────────┬──────────────┤
│ 🟢 87.5%   │ 16         │ 14         │ 2          │ 3.5 ngày     │
│ Compliance │ Tổng lên   │ Hoàn thành │ Quá hạn    │ Trễ TB       │
│ Rate       │ lịch       │ đúng hạn   │ (đỏ)       │              │
├────────────┴────────────┴────────────┴────────────┴──────────────┤
│                                                                  │
│  TRẠNG THÁI PM THÁNG NÀY           TREND 6 THÁNG               │
│  ┌──────────────────┐               100% ─────────────          │
│  │ ██████ 87.5%     │                75% ──────── ░░░░          │
│  │ ██ Minor Issues  │                50%                        │
│  │ ░ Overdue        │                   Jan Feb Mar Apr May Jun  │
│  └──────────────────┘                                           │
│                                                                  │
├──────────────────────────────────────────────────────────────────┤
│  THIẾT BỊ QUÁ HẠN PM                                            │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ 🔴 ACC-ASS-2026-00003  Máy siêu âm  Quá hạn 8 ngày        │  │
│  │ 🔴 ACC-ASS-2026-00007  Máy thở      Quá hạn 3 ngày        │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  PM ĐẾN HẠN TRONG 7 NGÀY TỚI                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ 🟡 ACC-ASS-2026-00012  Monitor     Còn 2 ngày   [Xem WO]   │  │
│  │ 🟡 ACC-ASS-2026-00015  ECG         Còn 5 ngày   [Xem WO]   │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

**Component map:**
- `KpiCard.vue` × 5 — số liệu tổng quan
- `ComplianceDonut.vue` — pie chart compliance
- `TrendLine.vue` — sparkline 6 tháng
- `OverdueTable.vue` — danh sách quá hạn
- `UpcomingTable.vue` — danh sách sắp đến hạn

---

## 3. Màn hình 2: Lịch bảo trì (`/pm/calendar`)

**Target user:** Workshop Manager  
**Mục đích:** Xem và điều phối lịch PM theo tuần/tháng

```
┌──────────────────────────────────────────────────────────────────┐
│  Lịch PM Tháng 4/2026                    [◀ Tháng] [Tháng ▶]    │
│                                    [Tháng] [Tuần] [Ngày]         │
├───────┬───────┬───────┬───────┬───────┬───────┬───────┤
│  T2   │  T3   │  T4   │  T5   │  T6   │  T7   │  CN   │
│  14   │  15   │  16   │  17   │  18   │  19   │  20   │
├───────┼───────┼───────┼───────┼───────┼───────┼───────┤
│       │       │       │ 🟡    │       │ 🔴    │       │
│       │       │       │PM-003 │       │PM-007 │       │
│       │       │       │Máy thở│       │S/â    │       │
│       │       │       │09:00  │       │OVERDUE│       │
├───────┼───────┼───────┼───────┼───────┼───────┼───────┤
│  21   │  22   │  23   │  24   │  25   │  26   │  27   │
│       │ 🟢    │       │       │ 🟡    │       │       │
│       │PM-012 │       │       │PM-015 │       │       │
│       │Monitor│       │       │ECG    │       │       │
└───────┴───────┴───────┴───────┴───────┴───────┴───────┘

Legend: 🟢 Completed  🟡 Scheduled  🔴 Overdue  ⚪ Open
```

**Interactions:**
- Click vào WO card → mở drawer chi tiết
- Drag & drop WO sang ngày khác → reschedule với dialog xác nhận lý do
- Filter bar: Khoa phòng | KTV | PM Type | Trạng thái
- Hover card → tooltip: thiết bị, KTV, due date

**Component map:**
- `PmCalendar.vue` — wrapper (tháng/tuần/ngày view)
- `CalendarEvent.vue` — card PM event, color-coded by status
- `PmDetailDrawer.vue` — slide-in panel khi click WO

---

## 4. Màn hình 3: Danh sách PM WO (`/pm/work-orders`)

**Target user:** Workshop Manager, KTV HTM

```
┌──────────────────────────────────────────────────────────────────┐
│  Phiếu Bảo trì PM                           [+ Tạo PM thủ công]  │
├──────────────────────────────────────────────────────────────────┤
│ Bộ lọc: [Trạng thái ▼] [KTV ▼] [Thiết bị...] [Từ ngày] [Đến]   │
├────────┬──────────┬────────────┬──────────┬───────┬─────────────┤
│ Mã WO  │ Thiết bị │ Loại PM    │ Đến hạn  │ KTV   │ Trạng thái  │
├────────┼──────────┼────────────┼──────────┼───────┼─────────────┤
│PM-0001 │ACC-00007 │ Quarterly  │20/04/26  │KTV-01 │🔴 Overdue   │
│PM-0003 │ACC-00003 │ Annual     │17/04/26  │KTV-02 │🟡 Open      │
│PM-0012 │ACC-00012 │ Semi-Annual│22/04/26  │KTV-01 │🔵 In Prog.  │
│PM-0008 │ACC-00008 │ Quarterly  │10/04/26  │KTV-03 │🟢 Completed │
└────────┴──────────┴────────────┴──────────┴───────┴─────────────┘
                                          Trang 1/3  [← →]
```

---

## 5. Màn hình 4: Chi tiết WO + Điền Checklist (`/pm/work-orders/:id`)

**Target user:** KTV HTM (desktop + mobile)

```
┌──────────────────────────────────────────────────────────────────┐
│ ← Quay lại    PM-WO-2026-00001 — Máy thở Drager Fabius     🟡   │
├──────────────────────────────────────────────────────────────────┤
│ THÔNG TIN PHIẾU                                                  │
│ Thiết bị:  ACC-ASS-2026-00001   │ Đến hạn: 20/04/2026 🟡        │
│ KTV:       Nguyễn Văn A         │ Loại PM:  Quarterly             │
│ Khoa:      ICU Tầng 3           │ Thời gian: —                   │
├──────────────────────────────────────────────────────────────────┤
│ CHECKLIST (4/10 đã hoàn thành)                                   │
│ ▓▓▓▓▓░░░░░░░░░░░░░░░ 40%                                        │
│                                                                  │
│ [1] Kiểm tra điện áp đầu vào (210–240V)        [CRITICAL]       │
│     ○ Pass  ● Fail-Minor  ○ Fail-Major  ○ N/A                   │
│     Giá trị đo: [___] V    Ghi chú: [              ]            │
│                                                                  │
│ [2] Kiểm tra áp suất khí nén (3.5–6 bar)        [CRITICAL]      │
│     ● Pass  ○ Fail-Minor  ○ Fail-Major  ○ N/A                   │
│     Giá trị đo: [4.2] bar  Ghi chú: [Bình thường  ]            │
│                                                                  │
│ [3] Vệ sinh bộ lọc / màng lọc                                   │
│     ● Pass  ○ Fail-Minor  ○ Fail-Major  ○ N/A                   │
│                                                                  │
│ [4] Kiểm tra van an toàn                                         │
│     ○ (chưa điền)                                                │
│                                                                  │
│ ... 6 mục còn lại ...                    [Xem tất cả]           │
├──────────────────────────────────────────────────────────────────┤
│ KẾT QUẢ TỔNG THỂ                                                 │
│ Ghi chú KTV: [                                        ]          │
│ Đã gắn sticker PM: ☐                                             │
│ Upload ảnh:  [📎 Chọn ảnh]                                       │
│ Thời gian thực hiện: [__] phút                                   │
├──────────────────────────────────────────────────────────────────┤
│           [Báo lỗi Major 🔴]    [Lưu nháp]    [Hoàn thành ✓]    │
└──────────────────────────────────────────────────────────────────┘
```

**Validation UI:**
- Progress bar cập nhật real-time khi điền từng mục
- Mục `is_critical = True` có badge đỏ "CRITICAL"
- Nếu bất kỳ mục Critical bị `Fail-Major` → nút "Hoàn thành" bị disable, chỉ còn "Báo lỗi Major"
- Nút "Hoàn thành" disabled cho đến khi 100% checklist điền

---

## 6. Mobile Experience (KTV thực hiện tại khoa)

**Target:** Điện thoại Android/iOS — KTV điền checklist tại chỗ

### Layout mobile (375px)

```
┌───────────────────────┐
│ ← PM-0001  Máy thở    │
│ ━━━━━━━━░░░░░░ 40%    │
├───────────────────────┤
│ [1/10] Điện áp đầu vào│
│                        │
│ Kết quả:              │
│ ┌──────┐ ┌──────────┐ │
│ │ Pass │ │Fail-Minor│ │
│ └──────┘ └──────────┘ │
│ ┌──────────┐          │
│ │Fail-Major│          │
│ └──────────┘          │
│                        │
│ Giá trị: [220____] V  │
│                        │
│ [📷 Chụp ảnh]         │
│                        │
├───────────────────────┤
│ [← Mục trước]  [Tiếp→]│
└───────────────────────┘
```

**Mobile UX principles:**
- One item per screen — không cuộn dài
- Nút lớn (min 48px tap target) cho Pass/Fail
- Camera tích hợp — chụp thẳng vào attachment
- Lưu offline (localStorage) khi mất kết nối, sync lại khi có mạng
- Swipe right/left để chuyển mục checklist

---

## 7. Cảnh báo & Trạng thái (Alert System)

### Badge màu sắc

| Badge | Màu | Điều kiện |
|---|---|---|
| On Schedule | 🟢 xanh | due_date > today + 7 |
| Due Soon | 🟡 vàng | due_date trong 7 ngày tới |
| Overdue | 🔴 đỏ | today > due_date |
| In Progress | 🔵 xanh dương | status = In Progress |
| Completed | ✅ xanh nhạt | status = Completed |
| Major Failure | ⛔ đỏ đậm | status = Halted–Major Failure |

### Slippage Warning

Hiển thị trong chi tiết WO khi `status = Overdue`:

```
┌─────────────────────────────────────────────────────┐
│ ⚠️  PM QUÁ HẠN 8 NGÀY — Đến hạn: 09/04/2026        │
│ Vui lòng hoàn thành hoặc hoãn lịch có ghi lý do     │
│                          [Hoãn lịch]  [Tiếp tục PM] │
└─────────────────────────────────────────────────────┘
```

### In-app Notification

- Workshop Manager: nhận tóm tắt sáng hàng ngày (08:00)
- KTV: nhận notification khi được assign WO
- PTP: nhận alert khi overdue > 7 ngày
- BGĐ: nhận alert khi overdue > 30 ngày

---

## 8. Component Tree

```
views/
├── PmDashboardView.vue          ← /pm/dashboard
├── PmCalendarView.vue           ← /pm/calendar
├── PmWorkOrderListView.vue      ← /pm/work-orders
└── PmWorkOrderDetailView.vue    ← /pm/work-orders/:id

components/pm/
├── PmKpiGrid.vue                ← 5 KPI cards
├── PmComplianceChart.vue        ← Donut + trend
├── PmOverdueTable.vue           ← Danh sách quá hạn
├── PmCalendarGrid.vue           ← Tháng/Tuần/Ngày view
├── PmCalendarEvent.vue          ← Card event
├── PmDetailDrawer.vue           ← Slide-in từ calendar
├── PmChecklist.vue              ← Checklist wrapper
├── PmChecklistItem.vue          ← Single checklist item
├── PmChecklistProgress.vue      ← Progress bar
└── PmMajorFailureDialog.vue     ← Dialog báo lỗi major

composables/
└── usePmStore.ts                ← Pinia store IMM-08

api/
└── imm08.ts                     ← API calls
```

---

## 9. Router Additions

```typescript
// Thêm vào router/index.ts
{
  path: '/pm',
  redirect: '/pm/dashboard',
},
{
  path: '/pm/dashboard',
  name: 'PmDashboard',
  component: () => import('@/views/PmDashboardView.vue'),
  meta: { requiresAuth: true, title: 'Dashboard PM — IMM-08' },
},
{
  path: '/pm/calendar',
  name: 'PmCalendar',
  component: () => import('@/views/PmCalendarView.vue'),
  meta: { requiresAuth: true, title: 'Lịch Bảo trì — IMM-08' },
},
{
  path: '/pm/work-orders',
  name: 'PmWorkOrderList',
  component: () => import('@/views/PmWorkOrderListView.vue'),
  meta: { requiresAuth: true, title: 'Phiếu Bảo trì PM — IMM-08' },
},
{
  path: '/pm/work-orders/:id',
  name: 'PmWorkOrderDetail',
  component: () => import('@/views/PmWorkOrderDetailView.vue'),
  props: true,
  meta: { requiresAuth: true, title: 'Chi tiết PM Work Order' },
},
```

---

## 10. Sidebar Update

Thêm nhóm IMM-08 vào `AppSidebar.vue`:

```typescript
{
  title: 'IMM-08 Bảo trì PM',
  items: [
    { label: 'Lịch bảo trì', path: '/pm/calendar', icon: 'calendar' },
    { label: 'Phiếu bảo trì', path: '/pm/work-orders', icon: 'list' },
    { label: 'Dashboard PM', path: '/pm/dashboard', icon: 'chart' },
  ],
},

---

## Pinia Store — useImm08Store

```typescript
// frontend/src/stores/imm08.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { frappeGet, frappePost } from '@/api/helpers'

export interface PMWorkOrder {
  name: string
  asset_ref: string
  asset_name: string
  pm_type: 'Annual' | 'Quarterly' | 'Monthly' | 'Biennial'
  assigned_to: string | null
  due_date: string
  start_date: string | null
  completion_date: string | null
  status: 'Open' | 'In Progress' | 'Overdue' | 'Completed' | 'Halted – Major Failure' | 'Pending – Device Busy'
  is_late: boolean
  failure_type: 'None' | 'Minor' | 'Major' | null
  result_summary: string
  checklist: ChecklistItem[]
}

export interface ChecklistItem {
  idx: number
  item_code: string
  description: string
  expected_value: string
  unit: string
  actual_value: string
  result: 'Pass' | 'Fail – Minor' | 'Fail – Major' | null
  is_mandatory: boolean
  failure_note: string
}

export interface PMCalendarEntry {
  wo_name: string
  asset_name: string
  due_date: string
  assigned_to: string
  status: string
  pm_type: string
}

export interface PMComplianceKPIs {
  total_scheduled: number
  completed_on_time: number
  completed_late: number
  overdue: number
  compliance_rate_pct: number
  mttr_avg_hours: number
}

export const useImm08Store = defineStore('imm08', () => {
  // --- State ---
  const workOrders = ref<PMWorkOrder[]>([])
  const currentWO = ref<PMWorkOrder | null>(null)
  const calendarEntries = ref<PMCalendarEntry[]>([])
  const kpis = ref<PMComplianceKPIs>({
    total_scheduled: 0,
    completed_on_time: 0,
    completed_late: 0,
    overdue: 0,
    compliance_rate_pct: 0,
    mttr_avg_hours: 0,
  })
  const loading = ref(false)
  const error = ref<string | null>(null)

  // --- Getters ---
  const overdueWOs = computed(() => workOrders.value.filter(w => w.status === 'Overdue'))
  const openWOs = computed(() => workOrders.value.filter(w => w.status === 'Open'))
  const checklistComplete = computed(() => {
    if (!currentWO.value) return false
    return currentWO.value.checklist.every(item => item.result !== null)
  })

  // --- Actions ---
  async function fetchWorkOrders(filters?: Record<string, unknown>) {
    loading.value = true
    try {
      const res = await frappeGet<PMWorkOrder[]>(
        '/api/method/assetcore.api.imm08.list_work_orders',
        filters
      )
      workOrders.value = res
    } catch (e: any) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  async function fetchWorkOrder(woName: string) {
    loading.value = true
    try {
      const res = await frappeGet<PMWorkOrder>(
        '/api/method/assetcore.api.imm08.get_work_order',
        { wo_name: woName }
      )
      currentWO.value = res
    } finally {
      loading.value = false
    }
  }

  async function updateChecklistItem(idx: number, data: Partial<ChecklistItem>) {
    if (!currentWO.value) return
    const item = currentWO.value.checklist.find(c => c.idx === idx)
    if (item) Object.assign(item, data)
  }

  async function submitWorkOrder(woName: string, summary: string): Promise<boolean> {
    try {
      await frappePost('/api/method/assetcore.api.imm08.submit_work_order', {
        wo_name: woName, result_summary: summary
      })
      await fetchWorkOrder(woName)
      return true
    } catch (e: any) {
      error.value = e.message
      return false
    }
  }

  async function reportMajorFailure(woName: string, description: string): Promise<boolean> {
    try {
      await frappePost('/api/method/assetcore.api.imm08.report_major_failure', {
        wo_name: woName, failure_description: description
      })
      return true
    } catch (e: any) {
      error.value = e.message
      return false
    }
  }

  async function fetchCalendar(month: string, year: number) {
    try {
      const res = await frappeGet<PMCalendarEntry[]>(
        '/api/method/assetcore.api.imm08.get_pm_calendar',
        { month, year }
      )
      calendarEntries.value = res
    } catch (e: any) {
      error.value = e.message
    }
  }

  async function fetchKPIs(dateRange?: { from: string; to: string }) {
    try {
      const res = await frappeGet<PMComplianceKPIs>(
        '/api/method/assetcore.api.imm08.get_compliance_kpis',
        dateRange
      )
      kpis.value = res
    } catch (e: any) {
      error.value = e.message
    }
  }

  return {
    workOrders, currentWO, calendarEntries, kpis, loading, error,
    overdueWOs, openWOs, checklistComplete,
    fetchWorkOrders, fetchWorkOrder, updateChecklistItem,
    submitWorkOrder, reportMajorFailure, fetchCalendar, fetchKPIs,
  }
})
```
