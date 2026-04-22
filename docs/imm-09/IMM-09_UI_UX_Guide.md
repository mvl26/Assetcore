# IMM-09 — UI/UX Guide
## Frontend Specification (Vue 3 + Frappe UI)

**Module:** IMM-09  
**Version:** 1.0  
**Ngày:** 2026-04-17  
**Trạng thái:** Draft

---

## 1. Sitemap & Routes

```
/imm-09/                          → Repair Dashboard (Workshop Manager / PTP view)
/imm-09/list                      → Danh sách Asset Repair WO (filterable, searchable)
/imm-09/create                    → Tạo Repair WO mới
/imm-09/:name                     → Chi tiết Repair WO (view + action theo status)
/imm-09/:name/diagnose            → Form chẩn đoán (KTV only, status = Diagnosing)
/imm-09/:name/parts               → Quản lý vật tư (status = Pending Parts / In Repair)
/imm-09/:name/checklist           → Repair Checklist (status = Pending Inspection)
/imm-09/firmware-change/:fcr_name → Chi tiết Firmware Change Request
/imm-09/reports/mttr              → MTTR Report (PTP / Manager)
/imm-09/reports/backlog           → Repair Backlog Report
```

### Route Guards

```typescript
// router/imm09.ts
const routes: RouteRecordRaw[] = [
  {
    path: '/imm-09',
    component: RepairDashboard,
    meta: { roles: ['Workshop Manager', 'PTP Khối 2', 'CMMS Admin'] },
  },
  {
    path: '/imm-09/list',
    component: RepairList,
    meta: { roles: ['Workshop Manager', 'KTV HTM', 'PTP Khối 2', 'CMMS Admin'] },
  },
  {
    path: '/imm-09/create',
    component: RepairCreate,
    meta: { roles: ['Workshop Manager', 'CMMS Admin'] },
  },
  {
    path: '/imm-09/:name',
    component: RepairDetail,
    meta: { roles: ['Workshop Manager', 'KTV HTM', 'Trưởng khoa', 'PTP Khối 2', 'CMMS Admin'] },
  },
  {
    path: '/imm-09/:name/diagnose',
    component: RepairDiagnose,
    meta: { roles: ['KTV HTM', 'Workshop Manager', 'CMMS Admin'] },
  },
  {
    path: '/imm-09/:name/parts',
    component: RepairParts,
    meta: { roles: ['KTV HTM', 'Workshop Manager', 'Kho vật tư', 'CMMS Admin'] },
  },
  {
    path: '/imm-09/:name/checklist',
    component: RepairChecklist,
    meta: { roles: ['KTV HTM', 'Workshop Manager', 'CMMS Admin'] },
  },
  {
    path: '/imm-09/reports/mttr',
    component: MttrReport,
    meta: { roles: ['Workshop Manager', 'PTP Khối 2', 'CMMS Admin'] },
  },
]
```

---

## 2. Component Architecture

```
pages/
├── RepairDashboard.vue         # KPI cards + backlog list + SLA alerts
├── RepairList.vue              # Paginated filterable WO list
├── RepairCreate.vue            # Tạo WO mới (source validation)
├── RepairDetail.vue            # Hub chính — routing theo status
├── RepairDiagnose.vue          # Form chẩn đoán root cause
├── RepairParts.vue             # Spare parts management
├── RepairChecklist.vue         # Post-repair acceptance checklist
└── MttrReport.vue              # MTTR dashboard & charts

components/
├── repair/
│   ├── RepairStatusBadge.vue       # Badge màu theo status (Open→Completed→Cannot Repair)
│   ├── RepairStatusTimeline.vue    # Timeline hiển thị lịch sử trạng thái
│   ├── RepairActionBar.vue         # Nút hành động thay đổi theo status
│   ├── RepairSlaIndicator.vue      # Đồng hồ đếm giờ + SLA progress bar
│   ├── RepairSummaryCard.vue       # Card tóm tắt WO (số, thiết bị, KTV, MTTR)
│   ├── RepairSourceBadge.vue       # Badge PM WO / Incident Report nguồn
│   └── RepairRepeatFailureBanner.vue # Banner cảnh báo tái hỏng
├── parts/
│   ├── SparePartsTable.vue         # Bảng linh kiện + nút thêm/xóa
│   ├── PartSearchCombobox.vue      # Tìm kiếm Item với debounce
│   └── StockEntryLinkField.vue     # Link phiếu xuất kho + validate
├── checklist/
│   ├── ChecklistForm.vue           # Form điền từng mục checklist
│   ├── ChecklistProgressBar.vue    # Progress: X/Y mục đã Pass
│   └── ChecklistResultBadge.vue    # Badge Pass/Fail/N/A
├── firmware/
│   ├── FirmwareFcrCard.vue         # Card hiển thị FCR linked
│   └── FirmwareFcrCreate.vue       # Form tạo FCR mới
├── shared/
│   ├── AssetInfoCard.vue           # Thông tin thiết bị (model, serial, risk class)
│   ├── DurationTimer.vue           # Đồng hồ thời gian sửa chữa realtime
│   └── LifecycleEventLog.vue       # Danh sách Asset Lifecycle Event
└── charts/
    ├── MttrTrendChart.vue          # Line chart MTTR theo tháng
    ├── BacklogBarChart.vue         # Bar chart backlog theo dept
    └── FtfrGaugeChart.vue          # Gauge chart First-Time Fix Rate
```

---

## 3. Form Specifications

### 3.1 Create Repair WO (`RepairCreate.vue`)

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
│                                                                 │
│  ⚠ AssetInfoCard: model, manufacturer, warranty status         │
│                                                                 │
│  Nguồn sửa chữa (chọn ít nhất một) *                           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  ○ Incident Report:  [IR-2026-XXXXX          ▼ Search] │   │
│  │  ○ PM Work Order:    [PM-WO-2026-XXXXX       ▼ Search] │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Loại & Ưu tiên                                                 │
│  ┌────────────────────────────┐  ┌──────────────────────────┐  │
│  │ Loại sửa chữa *            │  │ Ưu tiên *               │  │
│  │ [Corrective         ▼]    │  │ [Normal            ▼]   │  │
│  └────────────────────────────┘  └──────────────────────────┘  │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Mô tả sự cố ban đầu *                                   │   │
│  │ [Text area — mô tả ngắn gọn triệu chứng hỏng]          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  [BANNER NẾU REPEAT FAILURE: ⚠ Thiết bị đã hỏng trong 30 ngày]│
└─────────────────────────────────────────────────────────────────┘
```

**Validation on submit:**
- Bắt buộc: `asset_ref`, ít nhất một source field, `repair_type`, `priority`
- Nếu asset đang có WO mở → hiển thị toast error + link đến WO đó
- Nếu `priority = Emergency` → hiển thị confirm dialog "Xác nhận tạo phiếu khẩn cấp?"

---

### 3.2 Repair Detail (`RepairDetail.vue`) — Layout chính

```
┌─────────────────────────────────────────────────────────────────┐
│  WO-CM-2026-00042  [RepairStatusBadge: IN REPAIR]               │
│  Máy thở Drager Evita V800 — ICU 3                              │
├───────────────────────────────────┬─────────────────────────────┤
│  LEFT PANEL (60%)                 │  RIGHT PANEL (40%)          │
│                                   │                             │
│  [AssetInfoCard]                  │  [RepairSlaIndicator]       │
│  Model, Serial, Risk Class        │  Đã trôi: 6h 23m / 24h SLA│
│  Khoa phòng, Vị trí              │  [████████░░] 67%           │
│                                   │                             │
│  [RepairSourceBadge]              │  [DurationTimer]            │
│  📋 IR-2026-00123                 │  ⏱ 06:23:15                │
│                                   │                             │
│  [RepairRepeatFailureBanner]      │  KTV thực hiện:             │
│  (nếu is_repeat_failure = true)   │  Nguyễn Văn A               │
│                                   │  Phân công: 14/04 08:30     │
│  Chẩn đoán                        │                             │
│  ┌──────────────────────────────┐ │  Vật tư:                    │
│  │ Nguyên nhân: Điện            │ │  3 mục | 1,250,000đ         │
│  │ Mô tả: Tụ điện board nguồn  │ │                             │
│  │ bị cháy                      │ │  Checklist:                 │
│  └──────────────────────────────┘ │  0 / 5 mục đã Pass         │
│                                   │                             │
│  [RepairStatusTimeline]           │  [RepairActionBar]          │
│  ● Open — 14/04 07:15             │  [Cập nhật chẩn đoán]      │
│  ● Assigned — 14/04 08:30         │  [Quản lý vật tư]          │
│  ● Diagnosing — 14/04 09:00       │  [Bắt đầu sửa chữa]       │
│  ● In Repair — 14/04 10:00 ←      │                             │
│                                   │                             │
│  [LifecycleEventLog]              │                             │
│  (collapsible)                    │                             │
└───────────────────────────────────┴─────────────────────────────┘
```

---

### 3.3 Diagnose Form (`RepairDiagnose.vue`)

```
┌─────────────────────────────────────────────────────────────────┐
│  Chẩn đoán — WO-CM-2026-00042               [Hủy] [Lưu chẩn đoán]│
├─────────────────────────────────────────────────────────────────┤
│  Nguyên nhân gốc rễ *                                           │
│  [Electrical    ▼]  [Mechanical ▼]  [Software ▼]                │
│  [User Error ▼]  [Wear and Tear ▼]  [Unknown ▼]                 │
│                                                                 │
│  Mô tả chi tiết chẩn đoán *                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ [Rich text area — mô tả kỹ thuật, bộ phận bị hỏng]    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Ảnh thiết bị hỏng                                              │
│  [📷 Upload ảnh]  [ảnh1.jpg ×]  [ảnh2.jpg ×]                   │
│                                                                 │
│  Yêu cầu vật tư?                                               │
│  [○ Không cần vật tư] → tiếp tục sửa chữa ngay               │
│  [● Cần vật tư     ] → chuyển Pending Parts                   │
│                                                                 │
│  Cập nhật Firmware trong lần sửa này?                          │
│  [☐ Có — sẽ yêu cầu tạo Firmware Change Request]             │
│                                                                 │
│  Dự kiến thời gian hoàn thành                                  │
│  [Date picker] [Time picker]                                    │
└─────────────────────────────────────────────────────────────────┘
```

---

### 3.4 Spare Parts Form (`RepairParts.vue`)

```
┌─────────────────────────────────────────────────────────────────┐
│  Vật tư sửa chữa — WO-CM-2026-00042         [Lưu vật tư]       │
├─────────────────────────────────────────────────────────────────┤
│  Tìm vật tư:  [🔍 Tìm theo mã hoặc tên...                   ]   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ #  │ Mã vật tư  │ Tên         │ SL │ ĐVT │ Đơn giá   │  │   │
│  ├────┼────────────┼─────────────┼────┼─────┼───────────┼──┤   │
│  │ 1  │ CAP-100UF  │ Tụ 100uF   │ 2  │ Cái │ 25,000đ  │ × │   │
│  │    │ Phiếu XK: [STE-2026-00456           ] ✓ Hợp lệ  │   │   │
│  ├────┼────────────┼─────────────┼────┼─────┼───────────┼──┤   │
│  │ 2  │ FUSE-5A    │ Cầu chì 5A │ 1  │ Cái │ 15,000đ  │ × │   │
│  │    │ Phiếu XK: [                         ] ⚠ Chưa điền│   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  [+ Thêm vật tư]                                               │
│                                                                 │
│  Tổng chi phí vật tư:                          40,000 VNĐ      │
│                                                                 │
│  ⚠ Tất cả vật tư phải có phiếu xuất kho (BR-09-02)            │
└─────────────────────────────────────────────────────────────────┘
```

**Behavior:**
- `PartSearchCombobox` gọi `/api/method/assetcore.api.imm09.search_spare_parts` với debounce 300ms
- `StockEntryLinkField`: khi nhập mã phiếu → validate real-time qua API
- Hiển thị icon ✓ xanh khi phiếu hợp lệ, ⚠ đỏ khi chưa điền hoặc không tồn tại
- Total cost tính realtime từ child table

---

### 3.5 Repair Checklist Form (`RepairChecklist.vue`)

```
┌─────────────────────────────────────────────────────────────────┐
│  Nghiệm thu sau sửa chữa — WO-CM-2026-00042                    │
│  [ChecklistProgressBar: 3 / 5 mục Pass  ████████░░░]           │
├─────────────────────────────────────────────────────────────────┤
│  #1 Electrical — Kiểm tra điện áp đầu vào         [Pass ✓]    │
│     Yêu cầu: 220V ± 5%  │ Đo được: 218V                       │
│                                                                 │
│  #2 Electrical — Kiểm tra cầu chì thay thế        [Pass ✓]    │
│     Yêu cầu: 5A         │ Đo được: 5A                         │
│                                                                 │
│  #3 Safety — Kiểm tra rò điện vỏ thiết bị         [Fail ✗]    │
│     Yêu cầu: < 0.1mA    │ Đo được: 0.08mA                     │
│     Ghi chú: [                                              ]  │
│     ⚠ Kết quả Fail — không thể hoàn thành                     │
│                                                                 │
│  #4 Performance — Test chức năng tạo áp             [─ Chưa] │
│     [Pass] [Fail] [N/A]                                        │
│                                                                 │
│  #5 Performance — Test chức năng báo động           [─ Chưa] │
│     [Pass] [Fail] [N/A]                                        │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│  Xác nhận trưởng khoa phòng                                     │
│  Họ tên: [                        ]  Chức danh: [           ] │
│                                                                 │
│  [Hoàn thành sửa chữa] ← disabled khi chưa 100% Pass          │
└─────────────────────────────────────────────────────────────────┘
```

**Behavior:**
- Nút "Hoàn thành sửa chữa" chỉ enabled khi tất cả row result = "Pass"
- Mục "Fail" highlight đỏ với warning text
- `ChecklistProgressBar` update realtime khi người dùng thay đổi result
- Trường "Họ tên trưởng khoa" bắt buộc trước khi Complete

---

### 3.6 Repair List (`RepairList.vue`)

```
┌─────────────────────────────────────────────────────────────────┐
│  Danh sách Phiếu Sửa Chữa              [+ Tạo WO] [↓ Export]  │
├──────────┬──────────────────┬──────────┬─────────┬─────────────┤
│  Filters:│ [Status ▼]       │[Dept ▼]  │[KTV ▼]  │[Priority ▼] │
│          │ [Asset Category] │[Date Rng]│[Search ]│             │
├──────────┴──────────────────┴──────────┴─────────┴─────────────┤
│ Số WO         │ Thiết bị     │ Status       │ KTV    │ SLA  │ ⋮ │
├───────────────┼──────────────┼──────────────┼────────┼──────┼───┤
│ WO-CM-2026-042│ Máy thở ICU3 │ 🔴 In Repair │ Anh    │ 67%  │ ⋮ │
│ WO-CM-2026-041│ Monitor P305 │ 🟡 P.Parts   │ Bình   │ 40%  │ ⋮ │
│ WO-CM-2026-040│ Defib Ward2  │ 🟢 Completed │ Cường  │ 100% │ ⋮ │
│ WO-CM-2026-039│ Infusion P2  │ 🔵 Open      │ —      │ 10%  │ ⋮ │
└───────────────┴──────────────┴──────────────┴────────┴──────┴───┘
│ Trang 1/3           [← Trước] [1] [2] [3] [Tiếp →]            │
└─────────────────────────────────────────────────────────────────┘
```

**Status badge colors:**
- Open: xanh dương nhạt
- Assigned: xanh dương đậm
- Diagnosing: tím
- Pending Parts: vàng cam
- In Repair: cam đỏ
- Pending Inspection: xanh lam
- Completed: xanh lá
- Cannot Repair: đỏ đậm
- Cancelled: xám

---

### 3.7 MTTR Report (`MttrReport.vue`)

```
┌─────────────────────────────────────────────────────────────────┐
│  MTTR Dashboard — Tháng 4/2026          [Xuất PDF] [Xuất Excel]│
├─────────────────────────────────────────────────────────────────┤
│  KPI Cards                                                      │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────┐ │
│  │ MTTR TB      │ │ First Fix %  │ │ Backlog      │ │CP/Sửa │ │
│  │ 18.5 giờ    │ │ 87.5%        │ │ 12 WO        │ │ 450Kđ │ │
│  │ ↓2.1h vs T3 │ │ ↑3% vs T3   │ │ 3 khẩn       │ │       │ │
│  └──────────────┘ └──────────────┘ └──────────────┘ └────────┘ │
├─────────────────────────────────────────────────────────────────┤
│  [MttrTrendChart — Line chart MTTR 6 tháng]                    │
│  Tháng:  T11   T12   T1    T2    T3    T4                      │
│  MTTR:   22h   19h   25h   21h   20.6h 18.5h                  │
│                                              ╱▔▔▔╲             │
│  ────────────────────────────────────────────────              │
│  SLA target Class III:  24h                                    │
├─────────────────────────────────────────────────────────────────┤
│  [BacklogBarChart — Backlog theo Khoa/Phòng]                   │
│  ICU:   ████████ 4                                             │
│  Ward2: ████ 2                                                 │
│  OR:    ██ 1                                                   │
├─────────────────────────────────────────────────────────────────┤
│  [FtfrGaugeChart — First-Time Fix Rate]                        │
│  87.5%  🟢 Trên mục tiêu (85%)                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Pinia Store — `useImm09Store`

```typescript
// stores/imm09.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { callApi } from '@/utils/api'

export interface RepairWO {
  name: string
  asset_ref: string
  asset_name: string
  risk_class: string
  serial_no: string
  incident_report: string | null
  source_pm_wo: string | null
  status: RepairStatus
  priority: 'Normal' | 'Urgent' | 'Emergency'
  repair_type: string
  open_datetime: string
  completion_datetime: string | null
  mttr_hours: number | null
  sla_target_hours: number
  sla_breached: boolean
  assigned_to: string | null
  diagnosis_notes: string | null
  root_cause_category: string | null
  spare_parts_used: SparePartRow[]
  total_parts_cost: number
  firmware_updated: boolean
  firmware_change_request: string | null
  repair_checklist: ChecklistRow[]
  is_repeat_failure: boolean
  is_warranty_claim: boolean
  dept_head_name: string | null
}

export type RepairStatus =
  | 'Open'
  | 'Assigned'
  | 'Diagnosing'
  | 'Pending Parts'
  | 'In Repair'
  | 'Pending Inspection'
  | 'Completed'
  | 'Cannot Repair'
  | 'Cancelled'

export interface SparePartRow {
  idx: number
  item_code: string
  item_name: string
  qty: number
  uom: string
  unit_cost: number
  total_cost: number
  stock_entry_ref: string | null
}

export interface ChecklistRow {
  idx: number
  test_description: string
  test_category: string
  result: 'Pass' | 'Fail' | 'N/A' | null
  measured_value: string | null
  expected_value: string | null
  notes: string | null
}

export const useImm09Store = defineStore('imm09', () => {
  // State
  const currentWO = ref<RepairWO | null>(null)
  const woList = ref<RepairWO[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  const mttrReport = ref<MttrReport | null>(null)

  // Computed
  const checklistPassCount = computed(() => {
    if (!currentWO.value) return 0
    return currentWO.value.repair_checklist.filter(r => r.result === 'Pass').length
  })

  const checklistTotal = computed(() => currentWO.value?.repair_checklist.length ?? 0)

  const isChecklistComplete = computed(() =>
    checklistTotal.value > 0 &&
    checklistPassCount.value === checklistTotal.value
  )

  const elapsedWorkingHours = computed(() => {
    if (!currentWO.value?.open_datetime) return 0
    // Calculated client-side for display — authoritative value from server on submit
    const now = new Date()
    const open = new Date(currentWO.value.open_datetime)
    return Math.round((now.getTime() - open.getTime()) / 1000 / 3600 * 10) / 10
  })

  const slaPercent = computed(() => {
    if (!currentWO.value) return 0
    return Math.min(100, Math.round((elapsedWorkingHours.value / currentWO.value.sla_target_hours) * 100))
  })

  const isSlaAtRisk = computed(() => slaPercent.value >= 75)
  const isSlaBreached = computed(() => slaPercent.value >= 100)

  const partsAllHaveStockEntry = computed(() =>
    currentWO.value?.spare_parts_used.every(p => !!p.stock_entry_ref) ?? true
  )

  // Actions
  async function fetchWO(name: string) {
    isLoading.value = true
    error.value = null
    try {
      const res = await callApi('assetcore.api.imm09.get_repair_wo', { name })
      currentWO.value = res.data
    } catch (e: any) {
      error.value = e.message
    } finally {
      isLoading.value = false
    }
  }

  async function fetchWOList(filters: Record<string, any> = {}) {
    isLoading.value = true
    try {
      const res = await callApi('assetcore.api.imm09.get_repair_list', filters)
      woList.value = res.data.items
    } finally {
      isLoading.value = false
    }
  }

  async function createRepairWO(payload: Partial<RepairWO>) {
    const res = await callApi('assetcore.api.imm09.create_repair_wo', payload)
    return res.data
  }

  async function assignTechnician(name: string, assigned_to: string) {
    const res = await callApi('assetcore.api.imm09.assign_technician', { name, assigned_to })
    if (currentWO.value) currentWO.value.status = 'Assigned'
    return res.data
  }

  async function submitDiagnosis(name: string, payload: {
    diagnosis_notes: string
    root_cause_category: string
    needs_parts: boolean
    firmware_update_needed: boolean
    eta?: string
  }) {
    const res = await callApi('assetcore.api.imm09.submit_diagnosis', { name, ...payload })
    await fetchWO(name)
    return res.data
  }

  async function submitRepairResult(name: string, payload: {
    spare_parts_used: SparePartRow[]
    firmware_updated: boolean
    firmware_change_request?: string
    repair_summary: string
  }) {
    const res = await callApi('assetcore.api.imm09.submit_repair_result', { name, ...payload })
    await fetchWO(name)
    return res.data
  }

  async function completeRepair(name: string, payload: {
    repair_checklist: ChecklistRow[]
    dept_head_name: string
    dept_head_confirmation_datetime: string
  }) {
    const res = await callApi('assetcore.api.imm09.complete_repair', { name, ...payload })
    if (currentWO.value) {
      currentWO.value.status = 'Completed'
      currentWO.value.mttr_hours = res.data.mttr_hours
    }
    return res.data
  }

  async function fetchMttrReport(year: number, month: number) {
    const res = await callApi('assetcore.api.imm09.get_mttr_report', { year, month })
    mttrReport.value = res.data
    return res.data
  }

  function resetCurrentWO() {
    currentWO.value = null
    error.value = null
  }

  return {
    currentWO, woList, isLoading, error, mttrReport,
    checklistPassCount, checklistTotal, isChecklistComplete,
    elapsedWorkingHours, slaPercent, isSlaAtRisk, isSlaBreached,
    partsAllHaveStockEntry,
    fetchWO, fetchWOList, createRepairWO, assignTechnician,
    submitDiagnosis, submitRepairResult, completeRepair,
    fetchMttrReport, resetCurrentWO,
  }
})
```

---

## 5. Client Logic

### 5.1 DurationTimer — Đồng hồ thời gian sửa chữa realtime

```typescript
// components/shared/DurationTimer.vue
// Hiển thị thời gian đã trôi từ open_datetime của WO
// Cập nhật mỗi giây — dừng khi status = Completed

import { ref, onMounted, onUnmounted, computed } from 'vue'

const props = defineProps<{ openDatetime: string; status: string }>()
const elapsed = ref(0)
let timer: number | null = null

onMounted(() => {
  const start = new Date(props.openDatetime).getTime()
  const update = () => {
    elapsed.value = Math.floor((Date.now() - start) / 1000)
  }
  update()
  if (!['Completed', 'Cannot Repair', 'Cancelled'].includes(props.status)) {
    timer = window.setInterval(update, 1000)
  }
})

onUnmounted(() => { if (timer) clearInterval(timer) })

const display = computed(() => {
  const h = Math.floor(elapsed.value / 3600)
  const m = Math.floor((elapsed.value % 3600) / 60)
  const s = elapsed.value % 60
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
})
```

### 5.2 RepairActionBar — Nút hành động theo status

```typescript
// Mapping status → danh sách action buttons
const ACTION_MAP: Record<RepairStatus, ActionButton[]> = {
  'Open':               [{ label: 'Phân công KTV', event: 'assign', roles: ['Workshop Manager'] }],
  'Assigned':           [{ label: 'Bắt đầu chẩn đoán', event: 'diagnose', roles: ['KTV HTM'] }],
  'Diagnosing':         [{ label: 'Lưu chẩn đoán', event: 'save_diagnosis', roles: ['KTV HTM'] }],
  'Pending Parts':      [{ label: 'Xác nhận đã có vật tư', event: 'parts_received', roles: ['KTV HTM', 'Workshop Manager'] }],
  'In Repair':          [
    { label: 'Hoàn thành sửa chữa', event: 'finish_repair', roles: ['KTV HTM'] },
    { label: 'Không thể sửa', event: 'cannot_repair', roles: ['KTV HTM', 'Workshop Manager'], variant: 'danger' },
  ],
  'Pending Inspection': [{ label: 'Nộp kết quả nghiệm thu', event: 'submit_checklist', roles: ['KTV HTM'] }],
  'Completed':          [],
  'Cannot Repair':      [],
  'Cancelled':          [],
}
```

### 5.3 PartSearchCombobox — Tìm kiếm vật tư với debounce

```typescript
// Gọi API tìm kiếm Item với debounce 300ms
// Hiển thị tồn kho hiện tại cạnh mỗi kết quả

const searchParts = useDebounceFn(async (query: string) => {
  if (query.length < 2) return
  const res = await callApi('assetcore.api.imm09.search_spare_parts', {
    query,
    filters: { item_group: 'Medical Device Parts' },
  })
  searchResults.value = res.data
}, 300)
```

### 5.4 RepairSlaIndicator — Progress bar màu động

```typescript
// Màu progress bar thay đổi theo mức độ SLA
const slaBarColor = computed(() => {
  if (slaPercent.value >= 100) return 'red'       // Đã vi phạm SLA
  if (slaPercent.value >= 75)  return 'orange'    // Đang nguy hiểm
  if (slaPercent.value >= 50)  return 'yellow'    // Cảnh báo vừa
  return 'green'                                   // Bình thường
})
```

### 5.5 Source Field Validation — Create Form

```typescript
// Validate ít nhất một source field được điền
// Chạy real-time khi user rời khỏi các field source

const validateSource = () => {
  if (!form.value.incident_report && !form.value.source_pm_wo) {
    sourceError.value = 'Phải có nguồn sửa chữa: Incident Report hoặc PM Work Order gốc'
    return false
  }
  sourceError.value = null
  return true
}
```
