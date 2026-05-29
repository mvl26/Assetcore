# 06 — Thiết kế Frontend — IMM-08 Bảo trì định kỳ (PM)

| Mục | Giá trị |
|---|---|
| Module | IMM-08 — Preventive Maintenance |
| Phạm vi | Per-module |
| Owner | FE Lead + Designer |
| Module accent | `emerald-600` |

---

## 1. Sitemap / Route map

| Route | Tên trang | Archetype | Role | Component chính |
|---|---|---|---|---|
| `/pm` | Redirect → Dashboard | — | — | — |
| `/pm/dashboard` | Dashboard Bảo trì PM | Dashboard | Workshop Head, VP Block2, CMMS Admin | `PMDashboardView.vue` |
| `/pm/calendar` | Lịch bảo trì PM | Calendar | Workshop Head, HTM Technician | `PMCalendarView.vue` |
| `/pm/work-orders` | Danh sách phiếu PM | List | All IMM roles | `PMWorkOrderListView.vue` |
| `/pm/work-orders/create` | Tạo phiếu PM thủ công | Form | Workshop Head, CMMS Admin | `PMWorkOrderCreateView.vue` |
| `/pm/work-orders/:id` | Chi tiết phiếu PM | Detail+Form | Workshop Head, Kỹ thuật viên (assigned) | `PMWorkOrderDetailView.vue` |
| `/pm/schedules` | Danh sách lịch PM | List | Workshop Head, CMMS Admin | `PmScheduleListView.vue` |
| `/pm/templates` | Checklist Template PM | List | Workshop Head, CMMS Admin | `PmTemplateListView.vue` |

> **Ghi chú:** `PmScheduleListView.vue` và `PmTemplateListView.vue` dùng API từ `@/api/imm00` (not `imm08`) — các endpoint Schedule/Template được expose qua `imm08` BE nhưng FE có thể dùng imm00 wrapper tùy routing.

---

## 2. Sidebar nav module

```ts
"imm-08": {
  title: "IMM-08 · Bảo trì định kỳ",
  accent: "emerald-600",
  items: [
    { icon: "layout-dashboard", label: "Dashboard PM",    to: "/pm/dashboard" },
    { icon: "calendar",         label: "Lịch bảo trì",   to: "/pm/calendar" },
    { icon: "clipboard-list",   label: "Phiếu bảo trì",  to: "/pm/work-orders" },
    { icon: "alert-triangle",   label: "Quá hạn",        to: "/pm/work-orders?filter=status:Overdue" },
  ],
}
```

---

## 3. Thiết kế giao diện

### 3.a. UI Mockup

**Mockup 1 — PM Dashboard:**

```
┌────────────────────────────────────────────────────────────────────┐
│  Dashboard Bảo trì PM                         [Tháng 4/2026 ▼]    │
├────────────┬───────────┬───────────┬───────────┬───────────────────┤
│  87.5%     │    16     │    14     │     2     │   3.5 ngày        │
│ Compliance │  Tổng lịch│  Đúng hạn │  Quá hạn  │  Trễ trung bình   │
│  rate      │           │           │           │                   │
├────────────┴───────────┴───────────┴───────────┴───────────────────┤
│  TREND COMPLIANCE 6 THÁNG                                          │
│  100% ─────●───────●─────●                                        │
│   75%   ●        ●     ●                                          │
│        T11  T12   T1    T2   T3   T4                               │
├────────────────────────────────────────────────────────────────────┤
│  THIẾT BỊ QUÁ HẠN                                                  │
│  🔴 PM-WO-2026-00007  Monitor Philips  Quá hạn 8 ngày   [Xem]     │
│  🔴 PM-WO-2026-00012  Máy thở Drager   Quá hạn 3 ngày   [Xem]     │
└────────────────────────────────────────────────────────────────────┘
```

**Mockup 2 — PM Calendar:**

```
┌────────────────────────────────────────────────────────────────────┐
│  Lịch PM Tháng 4/2026                [◀]  [Tháng] [Tuần]  [▶]    │
│  Filter: [Kỹ thuật viên ▼] [Asset ▼]                               │
├───────┬───────┬───────┬───────┬───────┬───────┬───────┬───────────┤
│  T2   │  T3   │  T4   │  T5   │  T6   │  T7   │  CN   │           │
│  14   │  15   │  16   │  17   │  18   │  19   │  20   │           │
│       │       │       │🟡PM-1 │       │🔴PM-7 │       │           │
│       │       │       │Máy thở│       │Monitor│       │           │
└───────┴───────┴───────┴───────┴───────┴───────┴───────┴───────────┘
```

**Mockup 3 — PM Work Order List:**

```
┌────────────────────────────────────────────────────────────────────┐
│ Phiếu Bảo trì PM                           [+ Tạo PM thủ công]     │
│ Filter: [Trạng thái ▼] [Kỹ thuật viên ▼] [Asset...] [Từ] [Đến]    │
├──────────┬──────────────┬──────────┬──────────┬────────────┬───────┤
│ Mã WO    │ Thiết bị     │ Loại PM  │ Đến hạn  │ Kỹ thuật viên │ TT │
├──────────┼──────────────┼──────────┼──────────┼────────┼───────────┤
│ PM-00001 │ Máy thở DC   │ Quarterly│ 17/04    │ ktv1   │🔴 Quá hạn │
│ PM-00003 │ Monitor PH   │ Annual   │ 22/04    │ ktv2   │🟢 Hoàn thành│
└──────────┴──────────────┴──────────┴──────────┴────────┴───────────┘
                                          Trang 1/3   [← →]
```

**Mockup 4 — PM Work Order Detail (Checklist):**

```
┌────────────────────────────────────────────────────────────────────┐
│ ← PM-WO-2026-00001 — Máy thở Drager Evita V500    🟡 Đang thực hiện│
├────────────────────────────────────────────────────────────────────┤
│ THÔNG TIN CHUNG                                                    │
│ Thiết bị: AC-ASSET-2026-0003    │ Đến hạn: 17/04/2026             │
│ Kỹ thuật viên: ktv1@bv.vn       │ Loại PM: Quarterly              │
│ Khoa:     ICU                   │ Class:   III ⚠ Cần ảnh          │
├────────────────────────────────────────────────────────────────────┤
│ CHECKLIST  (4 / 10 đã điền)    ▓▓▓▓░░░░░░ 40%                     │
│                                                                    │
│ [1] Kiểm tra điện áp đầu vào (210–240V)         [CRITICAL]        │
│     ○ Pass  ● Fail-Minor  ○ Fail-Major  ○ N/A                     │
│     Giá trị đo: [225] V    Notes: [..rò rỉ van..] *bắt buộc       │
├────────────────────────────────────────────────────────────────────┤
│ KẾT QUẢ TỔNG THỂ                                                   │
│ Tóm tắt kỹ thuật viên: [..............................]            │
│ Đã gắn sticker PM: ☐   Thời gian: [__] phút                       │
├────────────────────────────────────────────────────────────────────┤
│  [Báo lỗi Major 🔴]  [Hoãn lịch]  [Lưu nháp]  [Hoàn thành ✓]    │
└────────────────────────────────────────────────────────────────────┘
```

### 3.b. UI Screenshot (post-build)

Screenshots thực tế lưu tại: `docs/imm-08/screenshots/` (thêm sau khi build xong).

### 3.c. Trang chi tiết theo archetype

#### 3.1. Dashboard (`/pm/dashboard`)

> Bám `design-frontend.md §3.Dashboard`.

| KPI Card | API | Cache TTL |
|---|---|---|
| Compliance Rate (%) | `get_pm_dashboard_stats` | 5 phút |
| Tổng lịch / Đúng hạn / Quá hạn | Same | Same |
| Trễ trung bình (ngày) | Same | Same |
| Trend 6 tháng (line chart) | Same | Same |

**Action buttons:** Nút "Xuất báo cáo" (Workshop Head) — planned.

**State:**
- Loading: skeleton 4 KPI card + chart placeholder
- Empty: "Chưa có dữ liệu PM trong tháng này"
- Error: toast đỏ

#### 3.2. Calendar (`/pm/calendar`)

| Filter | Type | Default |
|---|---|---|
| Tháng/Năm | date picker | tháng hiện tại |
| Kỹ thuật viên | LinkSearch User | — |
| Asset | LinkSearch Asset | — |

**API:** `get_pm_calendar?year&month&technician?&asset_ref?`

**State:**
- Loading: skeleton grid
- Click event: open right drawer → lazy load `get_pm_work_order`

#### 3.3. List (`/pm/work-orders`)

| Cột | Type | Render |
|---|---|---|
| Mã WO | text/link | → `/pm/work-orders/{name}` |
| Thiết bị | text | asset_name |
| Loại PM | badge | pm_type |
| Đến hạn | date | dd/MM/yyyy |
| Kỹ thuật viên | text | assigned_to |
| Trạng thái | StatusChip | màu theo state |

**Filter bar:** Trạng thái · Kỹ thuật viên · Asset (free text) · Từ ngày – Đến ngày.

#### 3.4. Detail — PM Work Order (`:id`)

**Left panel (60%):** Thông tin WO + Checklist items (one per row, radio Pass/Fail/N/A).
**Right panel (40%):** SLA countdown + Kỹ thuật viên info + action buttons.

---

## 4. Component custom của module

| Component | Mục đích | Props |
|---|---|---|
| `PMStatusChip` | Badge màu theo PM WO status | `status: PMStatus` |
| `ChecklistProgress` | Thanh tiến trình X/N items có result | `filled: number, total: number` |
| `PMTimeline` | Timeline trạng thái WO | `history: TimelineEntry[]` |
| `SLACountdown` | Hiển thị ngày còn lại đến due_date | `dueDate: string, status: PMStatus` |
| `OverdueAlert` | Banner đỏ khi WO Overdue + ngày trễ | `daysOverdue: number` |

Đặt tại `frontend/src/components/pm/`.

---

## 5. Pinia store

File: `frontend/src/stores/imm08.ts`

```ts
// State (actual — stores/imm08.ts)
workOrders: PMWorkOrder[]
currentWO: PMWorkOrder | null
calendarEvents: PMCalendarEvent[]
calendarSummary: { total: number; completed: number; overdue: number; pending: number }
dashboardStats: PMDashboardStats | null
pmHistory: any[]
pagination: { page: number; total: number; total_pages: number; page_size: number }
loading: boolean
error: string | null

// Computed (getters)
overdueWOs: PMWorkOrder[]          // filter status === 'Overdue'
openWOs: PMWorkOrder[]             // filter status === 'Open'
checklistComplete: boolean         // every checklist result !== null
hasMinorFailure: boolean           // any result === 'Fail–Minor'
hasMajorFailure: boolean           // any result === 'Fail–Major'

// Actions (tên chính xác trong code)
fetchWorkOrders(filters?, page?): Promise<void>
fetchWorkOrder(name: string): Promise<void>
updateChecklistResult(idx: number, updates: Partial<ChecklistResult>): void
doAssignTechnician(name, technician, scheduledDate?): Promise<boolean>
doSubmitResult(summary, stickerAttached, durationMin): Promise<{ success: boolean; cmWoCreated?: string | null }>
doReportMajorFailure(description: string): Promise<string | null>
fetchCalendar(year: number, month: number): Promise<void>
fetchDashboardStats(year?, month?): Promise<void>
doReschedule(name, newDate, reason): Promise<boolean>
fetchPMHistory(assetRef: string): Promise<void>
```

**Persist policy:** Chỉ persist `pagination.page_size` và filter state — KHÔNG persist data record.

---

## 6. Vue Query keys

```ts
const keys = {
  dashboard: (year: number, month: number) => ['imm08', 'dashboard', year, month],
  list: (filters: Record<string, any>) => ['imm08', 'list', filters],
  detail: (name: string) => ['imm08', 'detail', name],
  calendar: (year: number, month: number) => ['imm08', 'calendar', year, month],
  history: (assetRef: string) => ['imm08', 'history', assetRef],
}
```

**Invalidate sau mutation:**
- `submitResult` → invalidate `list`, `detail(name)`, `dashboard`
- `assignTech` → invalidate `list`, `detail(name)`, `calendar`
- `reschedulePM` → invalidate `list`, `detail(name)`, `calendar`

---

## 6b. API call pattern — useApi().run()

```ts
import { useApi } from '@/composables/useApi'
import { submitPmResult } from '@/api/imm08'
import { useQueryClient } from '@tanstack/vue-query'

const api = useApi()
const qc = useQueryClient()
const formErrors = reactive<Record<string, string>>({})

async function onSubmitResult() {
  formErrors.value = {}
  const result = await api.run(
    () => submitPmResult({ name: wo.name, checklist_results: results, overall_result }),
    {
      successMessage: 'Đã hoàn thành phiếu bảo trì',
      onFieldError: (fields) => Object.assign(formErrors, fields),
    }
  )
  if (result) {
    qc.invalidateQueries({ queryKey: ['imm08', 'list'] })
    router.push('/pm/work-orders')
  }
}
```

---

## 7. Quy tắc ngôn ngữ FE

### 7.a. Nguyên tắc cứng
- 100% tiếng Việt mọi label, button, toast, error, placeholder
- KHÔNG dùng mã WO làm tiêu đề chính — hiển thị tên thiết bị trước
- Mã WO đặt nhỏ phía dưới, font-mono, `text-xs text-slate-500`

### 7.b. Entity display pattern

```
┌──────────────────────────────────────────┐
│ Máy thở Drager Evita V500 — ICU Khối A   │  ← H3 tên tự nhiên
│ PM-WO-2026-00001 · Quarterly             │  ← Mã code phụ
└──────────────────────────────────────────┘
```

### 7.c. Bảng từ ngữ chuẩn hóa

| Khái niệm | Tiếng Việt | Tránh từ |
|---|---|---|
| PM Work Order | Phiếu bảo trì | "WO", "Order" |
| PM Status: Open | Chờ thực hiện | "Open" |
| PM Status: In Progress | Đang thực hiện | "In Progress" |
| PM Status: Overdue | Quá hạn | "Overdue" |
| PM Status: Completed | Hoàn thành | "Completed" |
| PM Status: Halted–Major Failure | Dừng — Lỗi nghiêm trọng | "Halted" |
| PM Status: Cancelled | Đã hủy | "Cancelled" |
| PM Status: Pending–Device Busy | Chờ — Thiết bị bận | "Pending Busy" |
| overall_result: Pass | Đạt | "Pass" |
| overall_result: Fail | Không đạt | "Fail" |
| result: Fail–Minor | Lỗi nhỏ | "Fail-Minor" |
| result: Fail–Major | Lỗi nghiêm trọng | "Fail-Major" |
| Submit PM | Hoàn thành / Nộp kết quả | "Submit" |

### 7.c.bis Reconcile với mockup `docs/fe/08-pm/` (BE = source of truth)

> Mockup HTML trong `docs/fe/08-pm/` dùng nhãn marketing (**Scheduled, Assigned**)
> KHÔNG khớp `PMStatus` enum thật trong `services/imm08.py`. **BE thắng.**
> FE PHẢI map theo BE enum, KHÔNG copy nhãn mockup làm `value`.

| Mockup label | PMStatus thật (BE) | Nhãn VI render |
|---|---|---|
| "Scheduled" / "Đã phân công" | `Open` (+ `assigned_to` != null) | Chờ thực hiện / Đã phân công |
| "Assigned" | KHÔNG tồn tại state riêng → vẫn `Open` | — |
| "In Progress" / "Đang thực hiện" | `In Progress` | Đang thực hiện |
| "Overdue" | `Overdue` (hoặc `is_late=true`) | Quá hạn |
| "Completed" / "Hoàn tất" | `Completed` | Hoàn thành |
| "Pending Device Busy" | `Pending–Device Busy` | Chờ — Thiết bị bận |
| "Halted" / "Major Failure → CM" | `Halted–Major Failure` | Dừng — Lỗi nghiêm trọng |

**Workflow button → state matrix (PM Detail):** nút chỉ hiện khi state khớp.

| State hiện tại | Nút khả dụng | API |
|---|---|---|
| `Open` (chưa assign) | Phân công KTV | `assignTechnician` |
| `Open` (đã assign) / `In Progress` | Lưu tiến độ · Hoàn tất PM · Báo lỗi nghiêm trọng → CM · Tạm dừng (thiết bị bận) | `submitPMResult` / `reportMajorFailure` / `reschedulePM` |
| `Overdue` | giống `Open` + cảnh báo escalate | — |
| `Completed` / `Halted–Major Failure` / `Cancelled` | (terminal — không nút action) | — |

### 7d. Linked / Cascade fields

**Cascade PM Work Order Detail:**
- `asset_ref` chọn → auto-fill `asset_category`, `risk_class`, `serial_no`
- `pm_schedule` chọn → auto-fill `pm_type`, `checklist_template`, `due_date`

```ts
watch(assetRef, () => {
  pmSchedule.value = null
  // reload PM Schedules for this asset
})
```

---

## 8. Empty / Error / Loading copy

| Tình huống | Copy |
|---|---|
| List empty (no filter) | "Không có phiếu bảo trì nào. Scheduler sẽ tạo tự động khi đến hạn." |
| List empty (with filter) | "Không tìm thấy kết quả với bộ lọc hiện tại." |
| Checklist 0 items | "Checklist chưa được tạo. Vui lòng kiểm tra PM Checklist Template." |
| Submit success | "Đã hoàn thành phiếu bảo trì PM-WO-XXXX" |
| Loading list | Skeleton 5 dòng bảng |
| Loading detail | Skeleton 2 cột |
| Server error | "Lỗi hệ thống. Vui lòng thử lại hoặc liên hệ Admin." |
| Concurrent error | "Phiếu bảo trì đã được cập nhật bởi người khác. Vui lòng tải lại." |

---

## 9. Accessibility checklist module

- [ ] Nút "Hoàn thành PM" có `aria-label="Hoàn thành và nộp kết quả phiếu bảo trì"`
- [ ] Radio buttons checklist có `aria-describedby` link sang error text khi Fail-* thiếu notes
- [ ] Status badge có `role="status"` + text
- [ ] SLA countdown có `aria-live="polite"` — không announce mỗi giây
- [ ] `<html lang="vi">`
- [ ] Tap target ≥ 48px trên mobile (checklist radio buttons)
- [ ] Focus ring 2px emerald trên tất cả button/input

---

## 10. Responsive matrix

| Màn | Mobile (<640) | Tablet (640–1024) | Desktop (>1024) |
|---|---|---|---|
| Dashboard | KPI 1 cột | 2–3 cột | 5 cột + chart full |
| Calendar | Day view list | Week view | Month grid |
| List | Card list | Table 5 cột | Table full + filter sidebar |
| Detail | Checklist one-per-screen, swipe | Single column | 2 cột (info + checklist) |

---

## DoD — File 06 hoàn chỉnh

- [x] Sitemap đủ 8 route (dashboard + calendar + list + create + detail + schedules + templates)
- [x] 4 UI Mockup ASCII chính
- [x] Mỗi route có archetype + component chính
- [x] Sidebar nav config đầy đủ
- [x] Component custom liệt kê với props
- [x] Type definitions TypeScript đầy đủ trong §5 store
- [x] Vue Query keys chuẩn hóa + invalidate rule
- [x] API call pattern useApi().run()
- [x] Quy tắc ngôn ngữ 100% tiếng Việt
- [x] Bảng từ ngữ chuẩn hóa
- [x] Cascade fields khai báo
- [x] Empty / Error / Loading copy đủ
- [x] Accessibility checklist module
- [x] Responsive matrix
