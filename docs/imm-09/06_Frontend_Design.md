# IMM-09 — Frontend Design

| Thuộc tính | Giá trị |
|---|---|
| Module | **IMM-09 — Corrective Maintenance / Repair** |
| Phiên bản tài liệu | 1.0 |
| Ngày cập nhật | 2026-05-08 |
| Trạng thái | Chuẩn hóa từ IMM-09_UI_UX_Guide.md |
| Stack | Vue 3 + TypeScript + Pinia + TanStack Vue Query + TailwindCSS |

---

## §I Sitemap & Routes

```
/imm-09/                        → CMDashboard   (Workshop Manager / PTP)
/imm-09/list                    → CMList        (Danh sách WO, filter, tìm kiếm)
/imm-09/create                  → CMCreate      (Tạo WO mới)
/imm-09/:name                   → CMDetail      (Chi tiết WO, action theo status)
/imm-09/:name/diagnose          → CMDiagnose    (Form chẩn đoán, status = Diagnosing)
/imm-09/:name/parts             → CMParts       (Quản lý vật tư, Pending Parts / In Repair)
/imm-09/:name/checklist         → CMChecklist   (Nghiệm thu sau sửa, Pending Inspection)
/imm-09/reports/mttr            → CMMttr        (MTTR Dashboard)
```

### Route Guards

```typescript
// router/imm09.ts — component paths match actual file locations in views/cm/
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/imm-09',
    component: () => import('@/views/cm/CMDashboardView.vue'),
    meta: { roles: ['Workshop Manager', 'PTP Khối 2', 'CMMS Admin'] },
  },
  {
    path: '/imm-09/list',
    component: () => import('@/views/cm/CMWorkOrderListView.vue'),
    meta: { roles: ['Workshop Manager', 'KTV HTM', 'PTP Khối 2', 'CMMS Admin'] },
  },
  {
    path: '/imm-09/create',
    component: () => import('@/views/cm/CMCreateView.vue'),
    meta: { roles: ['Workshop Manager', 'CMMS Admin'] },
  },
  {
    path: '/imm-09/:name',
    component: () => import('@/views/cm/CMWorkOrderDetailView.vue'),
    meta: { roles: ['Workshop Manager', 'KTV HTM', 'Trưởng khoa', 'PTP Khối 2', 'CMMS Admin'] },
  },
  {
    path: '/imm-09/:name/diagnose',
    component: () => import('@/views/cm/CMDiagnoseView.vue'),
    meta: { roles: ['KTV HTM', 'Workshop Manager', 'CMMS Admin'] },
  },
  {
    path: '/imm-09/:name/parts',
    component: () => import('@/views/cm/CMPartsView.vue'),
    meta: { roles: ['KTV HTM', 'Workshop Manager', 'Kho vật tư', 'CMMS Admin'] },
  },
  {
    path: '/imm-09/:name/checklist',
    component: () => import('@/views/cm/CMChecklistView.vue'),
    meta: { roles: ['KTV HTM', 'Workshop Manager', 'CMMS Admin'] },
  },
  {
    path: '/imm-09/reports/mttr',
    component: () => import('@/views/cm/CMMttrView.vue'),
    meta: { roles: ['Workshop Manager', 'PTP Khối 2', 'CMMS Admin'] },
  },
]

export default routes
```

### Sidebar Navigation

```typescript
// sidebar config (accent = rose-600 — màu cảnh báo phân biệt với PM)
{
  label: 'Sửa chữa (IMM-09)',
  icon: 'wrench',
  accent: 'rose-600',
  children: [
    { label: 'Dashboard', path: '/imm-09' },
    { label: 'Danh sách WO', path: '/imm-09/list' },
    { label: 'Tạo phiếu mới', path: '/imm-09/create', roles: ['Workshop Manager', 'CMMS Admin'] },
    { label: 'Báo cáo MTTR', path: '/imm-09/reports/mttr', roles: ['Workshop Manager', 'PTP Khối 2', 'CMMS Admin'] },
  ],
}
```

---

## §II Mockups

### CMCreate — Tạo Phiếu Sửa Chữa

```
┌─────────────────────────────────────────────────────────────────┐
│  Tạo Phiếu Sửa Chữa                                 [Hủy] [Tạo]│
├─────────────────────────────────────────────────────────────────┤
│  Thông tin thiết bị                                             │
│  ┌────────────────────────────┐  ┌──────────────────────────┐  │
│  │ Thiết bị *                 │  │ Số Serial               │  │
│  │ [Link Search: Asset    ▼] │  │ [Auto-fill, read-only]  │  │
│  └────────────────────────────┘  └──────────────────────────┘  │
│  ┌────────────────────────────┐  ┌──────────────────────────┐  │
│  │ Phân loại nguy cơ          │  │ Khoa / Phòng            │  │
│  │ [Auto-fill: Class III]     │  │ [Auto-fill from Asset]  │  │
│  └────────────────────────────┘  └──────────────────────────┘  │
│  ── AssetInfoCard: model, manufacturer, warranty status ──      │
│                                                                 │
│  Nguồn sửa chữa (tùy chọn — BR-09-01 đã nới)                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  ○ Sự cố (Incident):  [IR-2026-XXXXX         ▼ Search] │   │
│  │  ○ Phiếu PM dừng:     [PM-WO-2026-XXXXX      ▼ Search] │   │
│  │  ○ Độc lập (Standalone) — không gắn nguồn               │   │
│  └─────────────────────────────────────────────────────────┘   │
│  Ghi chú: từ patch BR-09-01, repair có thể tạo độc lập           │
│  (standalone) không cần Incident/PM. Nguồn chỉ optional.         │
│                                                                 │
│  Loại & Ưu tiên                                                 │
│  ┌────────────────────────────┐  ┌──────────────────────────┐  │
│  │ Loại sửa chữa *            │  │ Ưu tiên *               │  │
│  │ [Corrective         ▼]    │  │ [Normal            ▼]   │  │
│  └────────────────────────────┘  └──────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Mô tả sự cố ban đầu *                                   │   │
│  │ [Text area — mô tả triệu chứng hỏng hóc]               │   │
│  └─────────────────────────────────────────────────────────┘   │
│  [⚠ Banner repeat failure nếu thiết bị hỏng trong 30 ngày]    │
└─────────────────────────────────────────────────────────────────┘
```

### CMDetail — Chi tiết WO (layout 60/40)

```
┌─────────────────────────────────────────────────────────────────┐
│  WO-CM-2026-00042  [RepairStatusBadge: IN REPAIR]               │
│  Máy thở Drager Evita V800 — ICU 3                              │
├───────────────────────────────────┬─────────────────────────────┤
│  LEFT (60%)                       │  RIGHT (40%)                │
│                                   │                             │
│  [AssetInfoCard]                  │  [RepairSlaIndicator]       │
│  Model, Serial, Risk Class        │  Đã trôi: 6h 23m / 24h SLA│
│  Khoa phòng, Vị trí              │  [████████░░] 67%           │
│                                   │                             │
│  [RepairSourceBadge]              │  [DurationTimer]            │
│  📋 IR-2026-00123                 │  ⏱ 06:23:15                │
│                                   │                             │
│  [RepairRepeatFailureBanner]      │  Kỹ thuật viên: Nguyễn V.A │
│  (nếu is_repeat_failure = true)   │  Phân công: 14/04 08:30     │
│                                   │                             │
│  Chẩn đoán                        │  Vật tư: 3 mục / 1.25Mđ    │
│  ┌──────────────────────────────┐ │  Checklist: 0 / 5 Pass     │
│  │ Nguyên nhân: Điện            │ │                             │
│  │ Mô tả: Tụ điện board nguồn  │ │  [RepairActionBar]          │
│  │ bị cháy                      │ │  [Cập nhật chẩn đoán]      │
│  └──────────────────────────────┘ │  [Quản lý vật tư]          │
│                                   │  [Bắt đầu sửa chữa]       │
│  [RepairStatusTimeline]           │                             │
│  ● Open — 14/04 07:15             │                             │
│  ● Assigned — 14/04 08:30         │                             │
│  ● In Repair — 14/04 10:00 ←      │                             │
│  [LifecycleEventLog — collapsible]│                             │
└───────────────────────────────────┴─────────────────────────────┘
```

### CMDiagnose — Form Chẩn Đoán

```
┌─────────────────────────────────────────────────────────────────┐
│  Chẩn đoán — WO-CM-2026-00042         [Hủy] [Lưu chẩn đoán]   │
├─────────────────────────────────────────────────────────────────┤
│  Nguyên nhân gốc rễ *                                           │
│  [Electrical ▼]  [Mechanical ▼]  [Software ▼]                   │
│  [User Error ▼]  [Wear and Tear ▼]  [Unknown ▼]                 │
│                                                                 │
│  Mô tả chi tiết chẩn đoán *                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ [Rich text area — mô tả kỹ thuật, bộ phận bị hỏng]    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Ảnh thiết bị hỏng                                              │
│  [📷 Upload ảnh]  [img1.jpg ×]  [img2.jpg ×]                   │
│                                                                 │
│  Yêu cầu vật tư?                                               │
│  [○ Không cần vật tư → tiếp tục sửa chữa ngay]               │
│  [● Cần vật tư    → chuyển Pending Parts   ]                  │
│                                                                 │
│  Cập nhật Firmware trong lần sửa này?                          │
│  [☐ Có — sẽ yêu cầu tạo Firmware Change Request]             │
│                                                                 │
│  Dự kiến hoàn thành: [Date picker] [Time picker]               │
└─────────────────────────────────────────────────────────────────┘
```

### CMParts — Quản Lý Vật Tư

```
┌─────────────────────────────────────────────────────────────────┐
│  Vật tư sửa chữa — WO-CM-2026-00042              [Lưu vật tư]  │
├─────────────────────────────────────────────────────────────────┤
│  Tìm vật tư: [🔍 Tìm theo mã hoặc tên...                    ]  │
│                                                                 │
│  ┌────┬────────────┬─────────────┬────┬─────┬──────────┬───┐   │
│  │ #  │ Mã vật tư  │ Tên         │ SL │ ĐVT │ Đơn giá  │ × │   │
│  ├────┼────────────┼─────────────┼────┼─────┼──────────┼───┤   │
│  │ 1  │ CAP-100UF  │ Tụ 100uF   │ 2  │ Cái │ 25,000đ  │ × │   │
│  │    │ Phiếu XK: [STE-2026-00456        ] ✓ Hợp lệ   │   │   │
│  ├────┼────────────┼─────────────┼────┼─────┼──────────┼───┤   │
│  │ 2  │ FUSE-5A    │ Cầu chì 5A │ 1  │ Cái │ 15,000đ  │ × │   │
│  │    │ Phiếu XK: [                      ] ⚠ Chưa điền │   │   │
│  └────┴────────────┴─────────────┴────┴─────┴──────────┴───┘   │
│  [+ Thêm vật tư]                                               │
│                                                                 │
│  Tổng chi phí vật tư:                           40,000 VNĐ     │
│  ⚠ Tất cả vật tư phải có phiếu xuất kho (BR-09-02)            │
└─────────────────────────────────────────────────────────────────┘
```

### CMChecklist — Nghiệm Thu Sau Sửa Chữa

```
┌─────────────────────────────────────────────────────────────────┐
│  Nghiệm thu — WO-CM-2026-00042                                  │
│  [ChecklistProgressBar: 3 / 5 mục Pass  ████████░░░░]          │
├─────────────────────────────────────────────────────────────────┤
│  #1 Electrical — Kiểm tra điện áp đầu vào         [Pass ✓]    │
│     Yêu cầu: 220V ± 5%   │ Đo được: [218V         ]           │
│                                                                 │
│  #2 Electrical — Kiểm tra cầu chì thay thế        [Pass ✓]    │
│     Yêu cầu: 5A           │ Đo được: [5A           ]           │
│                                                                 │
│  #3 Safety — Kiểm tra rò điện vỏ thiết bị         [Fail ✗]    │
│     ⚠ Kết quả Fail — không thể hoàn thành         (highlight đỏ)│
│     Ghi chú: [                                             ]   │
│                                                                 │
│  #4 Performance — Test chức năng tạo áp            [─ Chưa]   │
│     [Pass] [Fail] [N/A]    │ Đo được: [             ]          │
│                                                                 │
│  #5 Performance — Test báo động                    [─ Chưa]   │
│     [Pass] [Fail] [N/A]    │ Đo được: [             ]          │
│                                                                 │
│  Xác nhận trưởng khoa phòng                                     │
│  Họ tên: [                      ]  Chức danh: [             ] │
│                                                                 │
│  [Hoàn thành sửa chữa]  ← disabled cho đến khi 100% Pass      │
└─────────────────────────────────────────────────────────────────┘
```

### CMList — Danh Sách WO

```
┌─────────────────────────────────────────────────────────────────┐
│  Danh sách Phiếu Sửa Chữa             [+ Tạo WO] [↓ Export]   │
├────────────┬─────────────────┬──────────┬──────────┬───────────┤
│  [Status▼] │ [Dept▼]         │ [Kỹ thuật viên▼] │ [Prior▼] │ [🔍]│
├────────────┴─────────────────┴──────────────────┴──────────┴────┤
│ Số WO          │ Thiết bị      │ Status        │ Kỹ thuật viên │ SLA │ │
├────────────────┼───────────────┼───────────────┼────────┼──────┤ │
│ WO-CM-2026-042 │ Máy thở ICU3  │ 🔴 In Repair  │ Anh    │  67% │ │
│ WO-CM-2026-041 │ Monitor P305  │ 🟡 P.Parts    │ Bình   │  40% │ │
│ WO-CM-2026-040 │ Defib Ward2   │ 🟢 Completed  │ Cường  │ 100% │ │
│ WO-CM-2026-039 │ Infusion P2   │ 🔵 Open       │ —      │  10% │ │
├────────────────┴───────────────┴───────────────┴────────┴──────┘ │
│  Trang 1/3        [← Trước] [1] [2] [3] [Tiếp →]               │
└─────────────────────────────────────────────────────────────────┘
```

**Status badge colors (Tailwind):**

| Status | Class |
|---|---|
| Open | `bg-blue-100 text-blue-700` |
| Assigned | `bg-blue-600 text-white` |
| Diagnosing | `bg-purple-100 text-purple-700` |
| Pending Parts | `bg-amber-100 text-amber-700` |
| In Repair | `bg-orange-100 text-orange-700` |
| Pending Inspection | `bg-sky-100 text-sky-700` |
| Completed | `bg-green-100 text-green-700` |
| Cannot Repair | `bg-red-600 text-white` |
| Cancelled | `bg-gray-100 text-gray-500` |

### CMMttr — MTTR Dashboard

```
┌─────────────────────────────────────────────────────────────────┐
│  MTTR Dashboard — Tháng 4/2026         [Xuất PDF] [Xuất Excel] │
├─────────────────────────────────────────────────────────────────┤
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌──────────┐  │
│  │ MTTR TB    │  │ First Fix  │  │ Backlog    │  │ CP/Sửa  │  │
│  │ 18.5 giờ  │  │ 87.5%      │  │ 12 WO      │  │ 450Kđ   │  │
│  │ ↓2.1h T3  │  │ ↑3% vs T3 │  │ 3 khẩn     │  │         │  │
│  └────────────┘  └────────────┘  └────────────┘  └──────────┘  │
├─────────────────────────────────────────────────────────────────┤
│  [MttrTrendChart — Line chart 6 tháng]                         │
│   T11=22h  T12=19h  T1=25h  T2=21h  T3=20.6h  T4=18.5h        │
│   ── SLA target Class III: 24h ──                              │
├─────────────────────────────────────────────────────────────────┤
│  [BacklogBarChart — Backlog theo Khoa/Phòng]                   │
│  ICU:   ████████ 4    OR:  ████ 2    Radiology: ██ 1           │
├─────────────────────────────────────────────────────────────────┤
│  [FtfrGaugeChart — First-Time Fix Rate: 87.5%  🟢 > mục tiêu] │
└─────────────────────────────────────────────────────────────────┘
```

---

## §III Components

### Component Tree

```
views/cm/                              ← thư mục thực tế
├── CMDashboardView.vue        — KPI cards + backlog + SLA alerts
├── CMWorkOrderListView.vue    — Danh sách WO có filter + phân trang
├── CMCreateView.vue           — Tạo WO mới
├── CMWorkOrderDetailView.vue  — Hub chính, routing theo status
├── CMDiagnoseView.vue         — Form chẩn đoán
├── CMPartsView.vue            — Quản lý vật tư
├── CMChecklistView.vue        — Form nghiệm thu
└── CMMttrView.vue             — MTTR dashboard + charts

components/repair/
├── RepairStatusBadge.vue         — Badge màu theo status
├── RepairStatusTimeline.vue      — Timeline lịch sử trạng thái
├── RepairActionBar.vue           — Nút hành động thay đổi theo status
├── RepairSlaIndicator.vue        — Progress bar SLA + màu động
├── RepairSummaryCard.vue         — Card tóm tắt WO
├── RepairSourceBadge.vue         — Badge IR / PM WO nguồn
└── RepairRepeatFailureBanner.vue — Banner cảnh báo tái hỏng

components/parts/
├── SparePartsTable.vue         — Bảng vật tư + thêm/xóa
├── PartSearchCombobox.vue      — Tìm kiếm Item, debounce 300ms
└── StockEntryLinkField.vue     — Link phiếu xuất kho + validate real-time

components/checklist/
├── ChecklistForm.vue           — Form điền từng mục
├── ChecklistProgressBar.vue    — Progress X/Y Pass
└── ChecklistResultBadge.vue    — Badge Pass / Fail / N/A

components/firmware/
├── FirmwareFcrCard.vue         — Hiển thị FCR linked
└── FirmwareFcrCreate.vue       — Form tạo FCR mới

components/shared/
├── AssetInfoCard.vue           — Thông tin thiết bị (model, serial, risk class)
├── DurationTimer.vue           — Đồng hồ thời gian sửa chữa realtime
└── LifecycleEventLog.vue       — Danh sách Asset Lifecycle Event

components/charts/
├── MttrTrendChart.vue          — Line chart MTTR theo tháng
├── BacklogBarChart.vue         — Bar chart backlog theo dept
└── FtfrGaugeChart.vue          — Gauge chart First-Time Fix Rate
```

### Component Archetype Detail

| Component | Props | Events | Mô tả |
|---|---|---|---|
| `RepairStatusBadge` | `status: RepairStatus` | — | Pill badge màu Tailwind |
| `RepairStatusTimeline` | `transitions: AleRecord[]` | — | Vertical timeline từ ALE |
| `RepairActionBar` | `status`, `roles`, `disabled` | `action(event)` | Nút hành động theo ACTION_MAP |
| `RepairSlaIndicator` | `slaPercent`, `targetHours` | — | Progress bar màu động (green/yellow/orange/red) |
| `DurationTimer` | `openDatetime`, `status` | — | Đồng hồ realtime, dừng khi terminal state |
| `PartSearchCombobox` | `query` | `select(item)` | Combobox với debounce 300ms |
| `StockEntryLinkField` | `value`, `valid` | `change(ref)` | Input + validate icon ✓ / ⚠ |
| `ChecklistProgressBar` | `passed`, `total` | — | Thanh tiến trình Pass / total |

---

## §IV Pinia Store

File: `frontend/src/stores/imm09.ts` — dùng direct API function imports (không dùng `api.run(string)`).

```typescript
// stores/imm09.ts — tên state/action chính xác
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  listRepairWorkOrders, getRepairWorkOrder, assignTechnician,
  submitDiagnosis, closeWorkOrder, getRepairKPIs, getAssetRepairHistory,
  requestSpareParts, startRepair, getMttrReport, createRepairWorkOrder,
  searchSpareParts,
  type AssetRepair, type RepairKPIs, type MttrReport, type SparePartRow,
} from '@/api/imm09'

export const useImm09Store = defineStore('imm09', () => {
  // ── State ─────────────────────────────────────────────────────
  const workOrders  = ref<AssetRepair[]>([])    // tên thực tế: workOrders (không phải woList)
  const currentWO   = ref<AssetRepair | null>(null)
  const kpis        = ref<RepairKPIs | null>(null)
  const repairHistory = ref<any[]>([])
  const mttrReport  = ref<MttrReport | null>(null)
  const loading     = ref(false)                // tên thực tế: loading (không phải isLoading)
  const error       = ref<string | null>(null)
  const pagination  = ref({ page: 1, total: 0, total_pages: 0, page_size: 20 })

  // ── Computed ──────────────────────────────────────────────────
  const openWOs = computed(() => workOrders.value.filter(w => w.status === 'Open'))
  const breachedWOs = computed(() => workOrders.value.filter(w => w.sla_breached))
  const checklistComplete = computed(() => {
    if (!currentWO.value) return false
    return currentWO.value.repair_checklist.every(r => r.result !== null)
  })

  // ── Actions (tên chính xác) ───────────────────────────────────
  async function fetchWorkOrders(filters = {}, page = 1): Promise<void>
  async function fetchWorkOrder(name: string): Promise<void>
  function updateChecklistResult(idx: number, updates: Partial<AssetRepair['repair_checklist'][0]>): void
  async function doAssignTechnician(name: string, technician: string, priority?: string): Promise<boolean>
  async function doSubmitDiagnosis(diagnosisNotes: string, needsParts: boolean): Promise<boolean>
  async function doCloseWorkOrder(payload: Parameters<typeof closeWorkOrder>[0]): Promise<boolean>
  async function fetchKPIs(year?: number, month?: number): Promise<void>
  async function fetchRepairHistory(assetRef: string): Promise<void>
  async function fetchMttrReport(year: number, month: number): Promise<void>
  async function doSaveParts(woName: string, parts: SparePartRow[]): Promise<boolean>
  async function doStartRepair(woName: string): Promise<boolean>
  async function doCreateRepairWorkOrder(payload: Parameters<typeof createRepairWorkOrder>[0]): Promise<string | null>
  function doSearchSpareParts(query: string): Promise<SparePartRow[]>

  return {
    workOrders, currentWO, kpis, repairHistory, mttrReport, loading, error, pagination,
    openWOs, breachedWOs, checklistComplete,
    fetchWorkOrders, fetchWorkOrder, updateChecklistResult,
    doAssignTechnician, doSubmitDiagnosis, doCloseWorkOrder,
    fetchKPIs, fetchRepairHistory, fetchMttrReport, doSaveParts, doStartRepair,
    doCreateRepairWorkOrder, doSearchSpareParts,
  }
})
```

---

## §V Vue Query Keys & Invalidation

```typescript
// queryKeys/imm09.ts
export const imm09Keys = {
  all:              () => ['imm09'] as const,
  woList:           (filters = {}) => ['imm09', 'list', filters] as const,
  woDetail:         (name: string) => ['imm09', 'detail', name] as const,
  kpis:             (year: number, month: number) => ['imm09', 'kpis', year, month] as const,
  mttr:             (year: number, month: number) => ['imm09', 'mttr', year, month] as const,
  repairHistory:    (assetRef: string) => ['imm09', 'history', assetRef] as const,
}
```

**Invalidation rules:**

| Action | Invalidate |
|---|---|
| `create_repair_work_order` | `woList` |
| `assign_technician` | `woDetail(name)`, `woList` |
| `submit_diagnosis` | `woDetail(name)` |
| `request_spare_parts` | `woDetail(name)` |
| `start_repair` | `woDetail(name)` |
| `close_work_order` | `woDetail(name)`, `woList`, `kpis(*)`, `mttr(*)`, `repairHistory(asset_ref)` |

---

## §VI Client Logic

### DurationTimer — Đồng hồ realtime

```typescript
// components/shared/DurationTimer.vue
import { ref, onMounted, onUnmounted, computed } from 'vue'

const TERMINAL_STATUSES = ['Completed', 'Cannot Repair', 'Cancelled']

const props = defineProps<{ openDatetime: string; status: string }>()
const elapsed = ref(0)
let timer: ReturnType<typeof setInterval> | null = null

onMounted(() => {
  const start = new Date(props.openDatetime).getTime()
  const update = () => { elapsed.value = Math.floor((Date.now() - start) / 1000) }
  update()
  if (!TERMINAL_STATUSES.includes(props.status)) {
    timer = setInterval(update, 1000)
  }
})
onUnmounted(() => { if (timer) clearInterval(timer) })

const display = computed(() => {
  const h = Math.floor(elapsed.value / 3600)
  const m = Math.floor((elapsed.value % 3600) / 60)
  const s = elapsed.value % 60
  return `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`
})
```

### RepairActionBar — Action mapping theo status

```typescript
// ACTION_MAP: RepairStatus → list of action buttons
import type { RepairStatus } from '@/types/imm09'

interface ActionButton {
  label: string
  event: string
  roles: string[]
  variant?: 'primary' | 'danger'
}

const ACTION_MAP: Record<RepairStatus, ActionButton[]> = {
  'Open':               [{ label: 'Phân công kỹ thuật viên', event: 'assign',          roles: ['Workshop Manager'] }],
  'Assigned':           [{ label: 'Bắt đầu chẩn đoán',     event: 'diagnose',         roles: ['KTV HTM'] }],
  'Diagnosing':         [{ label: 'Lưu chẩn đoán',          event: 'save_diagnosis',   roles: ['KTV HTM'] }],
  'Pending Parts':      [{ label: 'Xác nhận đã có vật tư', event: 'parts_received',   roles: ['KTV HTM', 'Workshop Manager'] }],
  'In Repair': [
    { label: 'Hoàn thành sửa chữa', event: 'finish_repair', roles: ['KTV HTM'] },
    { label: 'Không thể sửa',       event: 'cannot_repair',  roles: ['KTV HTM', 'Workshop Manager'], variant: 'danger' },
  ],
  'Pending Inspection': [{ label: 'Nộp kết quả nghiệm thu', event: 'submit_checklist', roles: ['KTV HTM'] }],
  'Completed':          [],
  'Cannot Repair':      [],
  'Cancelled':          [],
}
```

### PartSearchCombobox — Debounce search

```typescript
// components/parts/PartSearchCombobox.vue
import { useDebounceFn } from '@vueuse/core'
import { useApi } from '@/composables/useApi'

const api = useApi()
const searchResults = ref<{ item_code: string; item_name: string; qty_in_stock: number; unit_cost: number }[]>([])

const searchParts = useDebounceFn(async (query: string) => {
  if (query.length < 2) return
  const res = await api.run('assetcore.api.imm09.search_spare_parts', { query, limit: 20 })
  searchResults.value = res.data
}, 300)
```

### RepairSlaIndicator — Màu progress bar động

```typescript
// Màu progress bar thay đổi theo mức độ SLA
const slaBarColor = computed(() => {
  if (slaPercent.value >= 100) return 'bg-red-500'    // Đã vi phạm
  if (slaPercent.value >= 75)  return 'bg-orange-500' // Nguy hiểm
  if (slaPercent.value >= 50)  return 'bg-yellow-400' // Cảnh báo
  return 'bg-green-500'                               // Bình thường
})
```

### Source Field Validation — CMCreate form

> **BR-09-01 (đã nới — 2026-05):** Nguồn sửa chữa (`incident_report` / `source_pm_wo`)
> giờ **optional**. Cho phép tạo phiếu sửa chữa độc lập (standalone) khi KTV phát hiện
> hỏng hóc không qua Incident/PM. KHÔNG còn block submit khi thiếu nguồn.
> Form chỉ validate `asset_ref`, `repair_type`, `priority`, `failure_description` là bắt buộc.

```typescript
// Nguồn KHÔNG còn bắt buộc. Nếu user chọn radio "Sự cố"/"PM" thì
// field tương ứng mới required; chọn "Độc lập" → bỏ trống cả hai.
const validateSource = (): boolean => {
  if (sourceMode.value === 'incident' && !form.value.incident_report) {
    sourceError.value = 'Vui lòng chọn Sự cố nguồn'
    return false
  }
  if (sourceMode.value === 'pm' && !form.value.source_pm_wo) {
    sourceError.value = 'Vui lòng chọn Phiếu PM nguồn'
    return false
  }
  sourceError.value = null
  return true   // sourceMode === 'standalone' luôn hợp lệ
}
```

---

## §VII i18n — Từ Ngữ Chuẩn Hóa Tiếng Việt

### Bảng thuật ngữ UI

| Tiếng Anh (code) | Tiếng Việt hiển thị |
|---|---|
| Work Order | Phiếu Sửa Chữa |
| Asset | Thiết bị |
| Repair Type | Loại sửa chữa |
| Priority | Ưu tiên |
| Assigned To | Kỹ thuật viên thực hiện |
| Diagnosis Notes | Nội dung chẩn đoán |
| Root Cause Category | Phân loại nguyên nhân |
| Spare Parts | Vật tư / Linh kiện |
| Stock Entry Ref | Phiếu xuất kho |
| Checklist | Danh sách kiểm tra |
| Repair Summary | Tóm tắt kết quả sửa chữa |
| Dept Head Name | Trưởng khoa phòng xác nhận |
| MTTR | MTTR (Thời gian sửa chữa trung bình) |
| SLA Breached | Vi phạm SLA |
| Cannot Repair | Không thể sửa chữa |
| Firmware Change Request | Yêu cầu cập nhật firmware |
| Repeat Failure | Tái hỏng hóc |
| First-Time Fix Rate | Tỷ lệ sửa thành công lần đầu |

### Status label map

| status | Nhãn tiếng Việt |
|---|---|
| Open | Mới mở |
| Assigned | Đã phân công |
| Diagnosing | Đang chẩn đoán |
| Pending Parts | Chờ vật tư |
| In Repair | Đang sửa chữa |
| Pending Inspection | Chờ nghiệm thu |
| Completed | Hoàn thành |
| Cannot Repair | Không thể sửa |
| Cancelled | Đã hủy |

### Reconcile với mockup `docs/fe/09-repair/` (BE = source of truth)

> Mockup HTML `docs/fe/09-repair/` dùng nhãn marketing (**Reported, Acknowledged,
> Diagnosed, Closed**) KHÔNG khớp `RepairStatus` enum thật trong `services/imm09.py`.
> **BE thắng.** FE map theo BE enum, KHÔNG copy nhãn mockup làm `value`.

| Mockup label | RepairStatus thật (BE) | Nhãn VI render |
|---|---|---|
| "Reported" / "Mở · Chờ phân công" | `Open` | Mới mở |
| "Acknowledged" / "Đã phân công" | `Assigned` | Đã phân công |
| "Diagnosed" / "Đã chẩn đoán" | `Diagnosing` | Đang chẩn đoán |
| "Waiting Parts" / "Chờ phụ tùng" | `Pending Parts` | Chờ vật tư |
| "In Progress" / "Đang xử lý" | `In Repair` | Đang sửa chữa |
| "Pending Inspection" / "Chờ nghiệm thu" | `Pending Inspection` | Chờ nghiệm thu |
| "Closed - Completed" / "Hoàn tất" | `Completed` | Hoàn thành |
| "Closed - Cannot Repair" | `Cannot Repair` | Không thể sửa |

**Workflow button → state matrix (CM Detail)** — đồng bộ với `ACTION_MAP` §VI:
nút chỉ hiện khi state khớp. Action terminal (`Completed`/`Cannot Repair`/`Cancelled`)
không có nút. Chi tiết transitions: `assignTechnician → submitDiagnosis →
[requestSpareParts] → startRepair → closeWorkOrder → confirmInspection`.

### Cascade Fields

| Khi chọn | Tự điền |
|---|---|
| `asset_ref` | `serial_no`, `risk_class`, `asset_category`, `location` |
| `incident_report` | Điền sẵn `failure_description` từ IR |
| `risk_class` × `priority` | Hiển thị SLA target dự kiến |
| `needs_parts = 1` | Chuyển hướng sang `/imm-09/:name/parts` sau khi lưu chẩn đoán |

---

## §VIII Empty / Error / Loading States

| Trạng thái | Component | Bản sao UI |
|---|---|---|
| Danh sách rỗng | CMList | "Không có phiếu sửa chữa nào. Nhấn '+ Tạo WO' để tạo mới." |
| Lỗi load WO | CMDetail | "Không thể tải phiếu sửa chữa. Vui lòng thử lại." + nút Thử lại |
| Đang tải | Tất cả | Skeleton loading card (Tailwind `animate-pulse`) |
| Thiết bị không tìm thấy | CMCreate asset field | "Thiết bị không tồn tại trong hệ thống" |
| WO đã có cho thiết bị | CMCreate submit | Toast "Thiết bị đang có phiếu sửa chữa mở: [link WO]" |
| Checklist chưa 100% Pass | CMChecklist | Button "Hoàn thành" disabled, tooltip "Còn X mục chưa Pass" |
| SLA vi phạm | CMDetail, CMList | Badge đỏ `SLA ĐÃ VI PHẠM`, `RepairSlaIndicator` màu đỏ |

---

## §IX Accessibility

- Tất cả interactive element phải có `aria-label` hoặc `aria-labelledby` (tiếng Việt)
- Status badge: dùng `role="status"` + `aria-live="polite"` cho realtime update (DurationTimer, SLA)
- Keyboard navigation: Tab order theo thứ tự tự nhiên trong form
- Focus management: Sau khi submit chẩn đoán → focus vào `RepairActionBar` của bước tiếp theo
- Color contrast: Badge text/background phải đạt WCAG AA (4.5:1)

---

## §X Responsive Matrix

| Breakpoint | CMList | CMDetail | CMCreate |
|---|---|---|---|
| `sm` (< 640px) | 1 cột, ẩn SLA % | Stack dọc, ẩn timeline | Full width inputs |
| `md` (640–1024px) | 2 cột + filter | 2 cột 60/40 | 2 cột grid |
| `lg` (> 1024px) | Bảng đầy đủ | 2 cột + sidebar action | 2 cột + preview |

---

*End of IMM-09 Frontend Design v1.0 — Corrective Maintenance.*
