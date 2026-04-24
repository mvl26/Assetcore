# IMM-14 — Giải nhiệm Thiết bị: Đóng Hồ sơ & Lưu trữ Vĩnh viễn
## UI/UX Guide — Vue 3 + TypeScript + Tailwind CSS

| Thuộc tính       | Giá trị                                                              |
|------------------|----------------------------------------------------------------------|
| Module           | IMM-14 — UI/UX Guide                                                 |
| Phiên bản        | 2.0.0                                                                |
| Ngày cập nhật    | 2026-04-24                                                           |
| Stack            | Vue 3 (Composition API) · TypeScript · Tailwind CSS · Pinia · Lucide |

---

## 1. Screen Map — 5 Màn hình

| Screen | Route                              | Component                    | Mô tả                                         |
|--------|------------------------------------|------------------------------|-----------------------------------------------|
| S1     | `/imm14/archives`                  | `ArchiveListView.vue`         | Danh sách hồ sơ lưu trữ, search, filter       |
| S2     | `/imm14/archives/:id`              | `ArchiveDetailView.vue`       | Chi tiết + document list + workflow actions    |
| S3     | `/imm14/archives/:id/timeline`     | `LifecycleTimelineView.vue`   | Visual timeline từ commissioning → archived   |
| S4     | `/imm14/archives/:id/verify`       | `DocumentVerificationView.vue`| Checklist tài liệu + upload + waive          |
| S5     | `/imm14/dashboard`                 | `EolDashboardView.vue`        | KPI EOL dashboard                             |

---

## 2. Vue Router Configuration

```typescript
// router/imm14.ts

import { RouteRecordRaw } from 'vue-router'

export const imm14Routes: RouteRecordRaw[] = [
  {
    path: '/imm14',
    component: () => import('@/layouts/ModuleLayout.vue'),
    meta: { module: 'IMM-14', roles: ['IMM HTM Manager', 'IMM CMMS Admin', 'IMM QA Officer'] },
    children: [
      {
        path: 'archives',
        name: 'ArchiveList',
        component: () => import('@/views/imm14/ArchiveListView.vue'),
      },
      {
        path: 'archives/:id',
        name: 'ArchiveDetail',
        component: () => import('@/views/imm14/ArchiveDetailView.vue'),
        props: true,
      },
      {
        path: 'archives/:id/timeline',
        name: 'LifecycleTimeline',
        component: () => import('@/views/imm14/LifecycleTimelineView.vue'),
        props: true,
      },
      {
        path: 'archives/:id/verify',
        name: 'DocumentVerification',
        component: () => import('@/views/imm14/DocumentVerificationView.vue'),
        props: true,
      },
      {
        path: 'dashboard',
        name: 'EolDashboard',
        component: () => import('@/views/imm14/EolDashboardView.vue'),
      },
    ],
  },
]
```

---

## 3. Pinia Store — `useImm14Store.ts`

```typescript
// stores/useImm14Store.ts

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type {
  ArchiveRecord,
  ArchiveDocumentEntry,
  LifecycleTimeline,
  DashboardMetrics,
  SearchFilters,
  SearchResult,
} from '@/types/imm14'
import * as api from '@/api/imm14'

export const useImm14Store = defineStore('imm14', () => {
  // ── State ────────────────────────────────────────────────────────────────
  const currentArchive   = ref<ArchiveRecord | null>(null)
  const archiveList      = ref<ArchiveRecord[]>([])
  const timeline         = ref<LifecycleTimeline | null>(null)
  const dashboardMetrics = ref<DashboardMetrics | null>(null)
  const searchFilters    = ref<SearchFilters>({ page: 1, page_size: 20 })
  const totalRows        = ref(0)
  const loading          = ref(false)
  const error            = ref<string | null>(null)

  // ── Getters ──────────────────────────────────────────────────────────────
  const missingDocuments = computed(() =>
    currentArchive.value?.documents.filter(d => d.archive_status === 'Missing') ?? []
  )

  const requiredMissingDocuments = computed(() =>
    missingDocuments.value.filter(d => d.is_required)
  )

  const documentCompleteness = computed(() => {
    const docs = currentArchive.value?.documents ?? []
    if (!docs.length) return 0
    const ok = docs.filter(d => d.archive_status !== 'Missing').length
    return Math.round((ok / docs.length) * 100)
  })

  const isReadOnly = computed(() =>
    currentArchive.value?.docstatus === 1
  )

  const canSubmitForVerification = computed(() =>
    currentArchive.value?.status === 'Compiling'
    && currentArchive.value?.reconcile_cmms
    && currentArchive.value?.reconcile_inventory
    && currentArchive.value?.reconcile_finance
    && currentArchive.value?.reconcile_legal
    && requiredMissingDocuments.value.length === 0
  )

  const daysUntilExpiry = computed(() => {
    const rd = currentArchive.value?.release_date
    if (!rd) return null
    const diff = new Date(rd).getTime() - Date.now()
    return Math.ceil(diff / 86400000)
  })

  // ── Actions ──────────────────────────────────────────────────────────────
  async function fetchArchiveList(filters?: SearchFilters) {
    loading.value = true
    error.value = null
    try {
      const res = await api.searchArchivedAssets({ ...searchFilters.value, ...filters })
      archiveList.value = res.data.rows
      totalRows.value = res.data.total
    } catch (e: any) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  async function fetchArchiveRecord(name: string) {
    loading.value = true
    error.value = null
    try {
      const res = await api.getArchiveRecord(name)
      currentArchive.value = res.data
    } catch (e: any) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  async function compileHistory(archiveName: string) {
    loading.value = true
    try {
      await api.compileAssetHistory(archiveName)
      await fetchArchiveRecord(archiveName) // refresh
    } finally {
      loading.value = false
    }
  }

  async function fetchTimeline(assetName: string) {
    loading.value = true
    try {
      const res = await api.getLifecycleTimeline(assetName)
      timeline.value = res.data
    } finally {
      loading.value = false
    }
  }

  async function fetchDashboard(year?: number) {
    const res = await api.getDashboardMetrics(year)
    dashboardMetrics.value = res.data
  }

  return {
    // state
    currentArchive, archiveList, timeline, dashboardMetrics,
    searchFilters, totalRows, loading, error,
    // getters
    missingDocuments, requiredMissingDocuments, documentCompleteness,
    isReadOnly, canSubmitForVerification, daysUntilExpiry,
    // actions
    fetchArchiveList, fetchArchiveRecord, compileHistory,
    fetchTimeline, fetchDashboard,
  }
})
```

---

## 4. Screen S1 — Archive List View

### Layout

```
┌─────────────────────────────────────────────────────────────────────────┐
│  IMM-14  │  Hồ sơ Lưu trữ Thiết bị                    [+ Tạo mới]     │
├─────────────────────────────────────────────────────────────────────────┤
│  Stats Bar (4 cards)                                                    │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐  │
│  │  8           │ │  3           │ │  1           │ │  1           │  │
│  │  Đã lưu trữ │ │  Đang xử lý │ │  Chờ xác minh│ │  Sắp hết hạn│  │
│  │  (năm nay)   │ │              │ │              │ │  (60 ngày)   │  │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘  │
├─────────────────────────────────────────────────────────────────────────┤
│  Filters:  [🔍 Tìm thiết bị...]  [Status ▼]  [Năm ▼]  [Phòng ▼]      │
├────────────┬────────────────┬──────────┬────────────┬──────────┬──────┤
│  Mã AAR    │ Thiết bị       │ Ngày lưu │ Hết hạn    │ Tài liệu │ TT   │
├────────────┼────────────────┼──────────┼────────────┼──────────┼──────┤
│ AAR-26-001 │ MRI 1.5T Siem. │ 25/04/26 │ 25/04/2036 │  36      │[●]  │
│            │ MRI-2024-001   │          │            │          │      │
├────────────┼────────────────┼──────────┼────────────┼──────────┼──────┤
│ AAR-16-012 │ ECG GE         │ 15/05/16 │ 15/05/2026 │  18      │[●]  │
│            │ ECG-2010-001   │          │ ⚠ 21 ngày  │          │      │
└────────────┴────────────────┴──────────┴────────────┴──────────┴──────┘
│  Hiển thị 1-20 trong 45 kết quả           [< 1 2 3 >]                 │
└─────────────────────────────────────────────────────────────────────────┘
```

### Status Badge Colors

| Status                 | Classes Tailwind                                      | Icon      |
|------------------------|-------------------------------------------------------|-----------|
| `Draft`                | `bg-slate-100 text-slate-600`                         | `FileText` |
| `Compiling`            | `bg-blue-100 text-blue-700`                           | `RefreshCw`|
| `Pending Verification` | `bg-amber-100 text-amber-700`                         | `Clock`   |
| `Pending Approval`     | `bg-purple-100 text-purple-700`                       | `UserCheck`|
| `Finalized`            | `bg-emerald-100 text-emerald-700`                     | `CheckCircle` |
| `Archived`             | `bg-slate-200 text-slate-600`                         | `Lock`    |

### Expiry Row Highlighting

```typescript
// Row highlight logic
const rowClass = (row: ArchiveRecord) => {
  const days = daysUntilExpiry(row.release_date)
  if (days === null) return ''
  if (days <= 30)  return 'bg-red-50 border-l-4 border-red-400'
  if (days <= 365) return 'bg-amber-50 border-l-4 border-amber-400'
  return ''
}
```

### Empty State

```
┌───────────────────────────────────────────────────────┐
│              📦  Chưa có hồ sơ lưu trữ               │
│  Hồ sơ sẽ được tạo tự động sau khi IMM-13 hoàn tất.  │
│  Hoặc [+ Tạo mới] để tạo thủ công.                   │
└───────────────────────────────────────────────────────┘
```

---

## 5. Screen S2 — Archive Detail View

### Layout — 4 Tab

```
┌─────────────────────────────────────────────────────────────────────────┐
│  [← Danh sách]  AAR-26-00001                         [Archived  🔒]    │
│  MRI 1.5T Siemens Magnetom · MRI-2024-001                               │
├─────────────────────────────────────────────────────────────────────────┤
│  [Thông tin] [Danh mục TL] [Đối soát] [Timeline]                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  TAB 1 — Thông tin Lưu trữ                                             │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Phiếu giải nhiệm    DR-26-04-00001           [→ IMM-13]       │   │
│  │  Ngày lưu trữ        25/04/2026                                 │   │
│  │  Hết hạn             25/04/2036  (còn 3.652 ngày)              │   │
│  │  Vị trí lưu trữ     Server DMS / Tủ P.TBYT Kệ A3              │   │
│  │  Số năm lưu trữ     10 năm (NĐ98/2021 §17)                    │   │
│  │  Tổng tài liệu       36                                         │   │
│  │  QA xác minh bởi    qa.officer@benhviennd1.vn · 26/04/2026    │   │
│  │  Phê duyệt bởi      htm.manager@benhviennd1.vn · 27/04/2026   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  [📄 Tải báo cáo vòng đời (PDF)]  [🔗 Xem Timeline]                  │
│                                                                         │
│  Ghi chú lưu trữ:                                                      │
│  Lưu trữ sau khi hoàn tất giải nhiệm MRI 1.5T Siemens...              │
│                                                                         │
│  ── Workflow Actions (hiển thị theo state) ──────────────────────────  │
│  [Draft]             → [Bắt đầu biên soạn ▶]                          │
│  [Compiling]         → [Biên soạn tự động ↻] [Gửi xác minh ▶]        │
│  [Pending Verif.]    → (QA view) [Xác minh ✓] [Trả lại ✗]            │
│  [Pending Approval]  → (HTM view) [Phê duyệt ✓] [Trả lại ✗]          │
│  [Finalized]         → [Submit & Khóa hồ sơ 🔒]                       │
│  [Archived]          → (read-only, no actions)                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Action Button Spec

```typescript
interface WorkflowAction {
  label: string
  icon: string
  variant: 'primary' | 'danger' | 'ghost'
  apiCall: () => Promise<void>
  confirm?: string       // confirmation dialog text
  requiresNote?: boolean // show note input
}

const actionsMap: Record<string, WorkflowAction[]> = {
  'Draft': [
    { label: 'Bắt đầu biên soạn', icon: 'Play', variant: 'primary',
      apiCall: () => store.startCompiling(id) }
  ],
  'Compiling': [
    { label: 'Biên soạn lịch sử tự động', icon: 'RefreshCw', variant: 'primary',
      apiCall: () => store.compileHistory(id),
      confirm: 'Thao tác này sẽ ghi đè danh sách tài liệu hiện tại. Tiếp tục?' },
    { label: 'Gửi xác minh QA', icon: 'Send', variant: 'primary',
      apiCall: () => store.submitForApproval(id),
      requiresNote: true }
  ],
  'Pending Verification': [
    { label: 'Xác minh đầy đủ', icon: 'CheckCircle', variant: 'primary',
      apiCall: () => store.verifyDocuments(id), requiresNote: true },
    { label: 'Trả lại CMMS Admin', icon: 'RotateCcw', variant: 'danger',
      apiCall: () => store.rejectVerification(id), requiresNote: true }
  ],
  'Pending Approval': [
    { label: 'Phê duyệt', icon: 'CheckCircle2', variant: 'primary',
      apiCall: () => store.approveArchive(id), requiresNote: true },
    { label: 'Trả lại', icon: 'RotateCcw', variant: 'danger',
      apiCall: () => store.rejectApproval(id), requiresNote: true }
  ],
  'Finalized': [
    { label: 'Submit & Khóa hồ sơ vĩnh viễn', icon: 'Lock', variant: 'primary',
      apiCall: () => store.finalizeArchive(id),
      confirm: 'Hành động này KHÔNG THỂ HOÀN TÁC. Hồ sơ sẽ bị khóa vĩnh viễn. Xác nhận?' }
  ],
}
```

---

## 6. Screen S2 — Tab 2: Danh mục Tài liệu

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Danh mục Tài liệu Lưu trữ         36 tài liệu · 1 Missing · 0 Waived │
│  [↻ Biên soạn tự động]  [+ Thêm thủ công]                              │
├───────────────────┬────────────────┬──────────┬────────────────┬───────┤
│  Loại             │ Mã tài liệu    │ Ngày     │ Trạng thái     │       │
├───────────────────┼────────────────┼──────────┼────────────────┼───────┤
│ Commissioning     │ IMM04-11-03-.. │ 15/03/11 │ [✓ Included]   │  [↗] │
│ Registration      │ REG-11-00001   │ 20/03/11 │ [✓ Included]   │  [↗] │
│ PM Record         │ WO-PM-2011-001 │ 15/06/11 │ [✓ Included]   │  [↗] │
│ PM Record         │ WO-PM-2011-002 │ 15/09/11 │ [✓ Included]   │  [↗] │
│ ...               │ ...            │ ...      │ ...             │  ... │
│ Calibration       │ —              │ —        │ [⚠ Missing]    │ [Edit]│
│ Service Contract  │ —              │ —        │ [— Waived]     │  [↗] │
├───────────────────┴────────────────┴──────────┴────────────────┴───────┤
│  Legend: [✓ Included]  [⚠ Missing]  [— Waived]                        │
└─────────────────────────────────────────────────────────────────────────┘
```

### Document Entry Row Colors

| archive_status | Row Class                                | Badge Class                           |
|----------------|------------------------------------------|---------------------------------------|
| `Included`     | `bg-white`                               | `bg-emerald-100 text-emerald-700`     |
| `Missing`      | `bg-amber-50`                            | `bg-red-100 text-red-700`             |
| `Waived`       | `bg-slate-50 opacity-60`                 | `bg-slate-100 text-slate-500`         |

### Missing Document Edit Panel (inline)

```
┌──────────────────────────────────────────────────────┐
│  Xử lý tài liệu: Calibration                        │
│  ─────────────────────────────────────────────────  │
│  Trạng thái:  ○ Included  ○ Waived                   │
│                                                      │
│  [Nếu Included] Upload file:                         │
│  [Chọn file...] calibration_cert.pdf          [Upload]│
│                                                      │
│  [Nếu Waived] Lý do: ________________________       │
│                                                      │
│  Ghi chú: __________________________________________ │
│                                                      │
│                      [Hủy]  [Lưu]                    │
└──────────────────────────────────────────────────────┘
```

---

## 7. Screen S2 — Tab 3: Đối soát (Reconciliation)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Đối soát 4 Chiều — Bắt buộc trước khi gửi QA xác minh                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ☑  CMMS/IMMIS — Số serial, model, vị trí đã khớp với AC Asset record │
│     Xác nhận bởi: cmms.admin@benhviennd1.vn  ·  25/04/2026            │
│                                                                         │
│  ☑  Kho vật tư — Phụ tùng tồn kho đã xử lý xong                      │
│     Xác nhận bởi: kho.tbyt@benhviennd1.vn  ·  25/04/2026              │
│                                                                         │
│  ☐  Kế toán / TSCD — Bút toán ghi giảm chưa xác nhận                  │
│     [Tick khi đã xác nhận]                                              │
│                                                                         │
│  ☐  Hồ sơ pháp lý — Giấy tờ thanh lý, giấy phép đã lưu trữ           │
│     [Tick khi đã xác nhận]                                              │
│                                                                         │
│  ── Ghi chú đối soát ──────────────────────────────────────────────── │
│  [Textarea]                                                             │
│                                                                         │
│  Trạng thái: ⚠ Chưa hoàn tất (2/4 mục)                                │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 8. Screen S3 — Lifecycle Timeline View

Visual timeline hiển thị toàn bộ lịch sử từ Commissioned → Archived.

```
┌─────────────────────────────────────────────────────────────────────────┐
│  [← Quay lại]  Timeline Vòng đời: MRI 1.5T Siemens  ·  15.1 năm      │
│  87 sự kiện · IMM04→IMM08→IMM09→IMM11→IMM12→IMM13→IMM14               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  2011                                                                   │
│  │                                                                      │
│  ├── 15/03/2011  ●  commissioned                    [IMM-04]           │
│  │   IMM04-11-03-00001  ·  Lắp đặt tại Khoa CĐHA, tầng 3             │
│  │                                                                      │
│  ├── 15/06/2011  ●  pm_completed                    [IMM-08]           │
│  │   WO-PM-2011-00001  ·  PM quý 1/2011                               │
│  │                                                                      │
│  ├── 15/09/2011  ●  pm_completed                    [IMM-08]           │
│  │   WO-PM-2011-00002  ·  PM quý 2/2011                               │
│  │                                                                      │
│  2018                                                                   │
│  │                                                                      │
│  ├── 22/07/2018  ⚠  incident_reported               [IMM-12]           │
│  │   IR-18-07-00032  ·  Lỗi gradient coil                             │
│  │                                                                      │
│  ├── 25/07/2018  🔧 repaired                        [IMM-09]           │
│  │   REP-18-07-00015  ·  Thay gradient coil, test OK                  │
│  │                                                                      │
│  2026                                                                   │
│  │                                                                      │
│  ├── 21/04/2026  🚫 decommissioned                  [IMM-13]           │
│  │   DR-26-04-00001  ·  Thanh lý EOL - hết khấu hao                  │
│  │                                                                      │
│  └── 25/04/2026  🔒 archived                        [IMM-14]           │
│      AAR-26-00001  ·  Hồ sơ khóa vĩnh viễn. Hết hạn: 25/04/2036     │
│                                                                         │
│  [Tải về PDF]  [Lọc sự kiện ▼]                                        │
└─────────────────────────────────────────────────────────────────────────┘
```

### Lifecycle Timeline Component Spec

```typescript
// components/imm14/LifecycleTimeline.vue

interface TimelineEvent {
  date: string
  event_type: 'commissioned' | 'pm_completed' | 'repaired' | 'calibrated'
    | 'incident_reported' | 'decommissioned' | 'archived'
  module: string
  record: string
  actor: string
  notes: string
}

// Event type → color + icon mapping
const eventConfig = {
  'commissioned':      { color: 'emerald', icon: 'Zap',           label: 'Lắp đặt'         },
  'pm_completed':      { color: 'blue',    icon: 'Wrench',        label: 'Bảo trì'          },
  'repaired':          { color: 'indigo',  icon: 'Wrench',        label: 'Sửa chữa'         },
  'calibrated':        { color: 'cyan',    icon: 'Gauge',         label: 'Hiệu chuẩn'       },
  'incident_reported': { color: 'amber',   icon: 'AlertTriangle', label: 'Sự cố'            },
  'decommissioned':    { color: 'orange',  icon: 'PowerOff',      label: 'Giải nhiệm'       },
  'archived':          { color: 'slate',   icon: 'Lock',          label: 'Lưu trữ'          },
}

// Props
const props = defineProps<{
  assetName: string
  events: TimelineEvent[]
  totalEvents: number
  lifecycleYears: number
}>()

// Scroll to bottom (most recent) on mount
onMounted(() => {
  timelineRef.value?.scrollIntoView({ behavior: 'smooth', block: 'end' })
})
```

### Timeline Filter Bar

```typescript
// Filters available in S3
const filterOptions = [
  { value: 'all',      label: 'Tất cả sự kiện' },
  { value: 'pm',       label: 'Bảo trì (PM)' },
  { value: 'repair',   label: 'Sửa chữa' },
  { value: 'incident', label: 'Sự cố' },
  { value: 'milestone',label: 'Milestone (Commissioned / Decommissioned / Archived)' },
]
```

---

## 9. Screen S4 — Document Verification View

Màn hình dành riêng cho QA Officer thực hiện xác minh.

```
┌─────────────────────────────────────────────────────────────────────────┐
│  [← Chi tiết]  Xác minh Tài liệu — AAR-26-00001     [QA Officer]      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Tiến độ hoàn thành:  ████████████████████░░░░░  94%                  │
│  ✓ 34 Included  ·  ⚠ 1 Missing  ·  — 1 Waived  ·  Tổng: 36          │
│                                                                         │
│  ── Tài liệu CHƯA XỬ LÝ (cần hành động) ──────────────────────────── │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  ⚠  Calibration  (Bắt buộc: Không)                             │   │
│  │  Không tìm thấy IMM Asset Calibration cho thiết bị này.        │   │
│  │                                                                  │   │
│  │  [Upload file]  hoặc  [Waive với lý do]                        │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ── Đối soát 4 chiều ─────────────────────────────────────────────── │
│  ✓ CMMS  ✓ Kho  ✗ Kế toán  ✗ Hồ sơ pháp lý                          │
│  ⚠ Cần hoàn tất đối soát trước khi xác minh                           │
│                                                                         │
│  ── Ghi chú xác minh ──────────────────────────────────────────────── │
│  [Textarea — bắt buộc]                                                 │
│  Ví dụ: "Đã kiểm tra đủ 36 tài liệu theo BM-IMMIS-14-01..."          │
│                                                                         │
│  [Hủy]                              [Xác minh đầy đủ ✓]               │
│                           (disabled khi còn issues chưa xử lý)         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 10. Screen S5 — EOL Dashboard

```
┌─────────────────────────────────────────────────────────────────────────┐
│  IMM-14  │  Dashboard Giải nhiệm & Lưu trữ TBYT          [Năm: 2026 ▼]│
├──────────┬──────────┬──────────┬──────────┬──────────┬─────────────────┤
│  8       │  3       │  2       │  94.4%   │  8.3 ng  │  1              │
│ Archived │ Đang xử  │ Chờ xác  │ Đầy đủ   │ Avg      │ Sắp hết hạn    │
│  YTD     │ lý       │ minh     │ TL       │ time     │  (60 ngày)      │
├──────────┴──────────┴──────────┴──────────┴──────────┴─────────────────┤
│                                                                         │
│  ┌─ Archives theo Năm ────────┐  ┌─ Phân bổ theo Khoa ──────────────┐ │
│  │  2024  ██████  5           │  │  CĐHA     ████████  12           │ │
│  │  2025  ████████████  12    │  │  HSTC     ██████  8             │ │
│  │  2026  ██████████  8       │  │  Phòng Mổ ████  5               │ │
│  └────────────────────────────┘  │  Nội nhi  ███  4                │ │
│                                  └───────────────────────────────────┘ │
│                                                                         │
│  ┌─ Sắp hết hạn lưu trữ (60 ngày) ──────────────────────────────────┐ │
│  │  AAR-16-00012  ·  ECG GE  ·  Khoa Nội nhi  ·  Hết: 15/05/2026  │ │
│  │  [Xem chi tiết →]                                                 │ │
│  └─────────────────────────────────────────────────────────────────── │
│                                                                         │
│  ┌─ Chất lượng Hồ sơ ───────────────────────────────────────────────┐ │
│  │  Avg tài liệu / AAR:  32.5                                        │ │
│  │  Missing rate:        5.6%                                         │ │
│  │  Reconciliation rate: 100%                                         │ │
│  └─────────────────────────────────────────────────────────────────── │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 11. Icons Reference (Lucide)

| Ngữ cảnh                   | Icon             |
|----------------------------|------------------|
| Page header IMM-14         | `Archive`        |
| Status: Draft              | `FileText`       |
| Status: Compiling          | `RefreshCw`      |
| Status: Pending Verif.     | `Clock`          |
| Status: Pending Approval   | `UserCheck`      |
| Status: Finalized          | `CheckCircle`    |
| Status: Archived           | `Lock`           |
| Document: Included         | `FileCheck`      |
| Document: Missing          | `FileX`          |
| Document: Waived           | `FileMinus`      |
| Timeline                   | `History`        |
| Expiry warning             | `AlertTriangle`  |
| Compile button             | `RefreshCw`      |
| Event: Commissioned        | `Zap`            |
| Event: PM                  | `Wrench`         |
| Event: Repair              | `Wrench`         |
| Event: Calibration         | `Gauge`          |
| Event: Incident            | `AlertTriangle`  |
| Event: Decommissioned      | `PowerOff`       |
| Event: Archived            | `Lock`           |
| Reconciliation OK          | `CheckSquare`    |
| Reconciliation Pending     | `Square`         |
| Dashboard                  | `BarChart3`      |

---

## 12. UX Flows

### Flow A — Auto-creation từ IMM-13

```
User submit IMM-13 (Decommission Request)
        ↓
IMM-13 on_submit → auto-create AAR (Draft)
        ↓
CMMS Admin nhận notification email
        ↓
CMMS Admin mở AAR từ link trong email → S2 ArchiveDetailView
        ↓
CMMS Admin bấm "Biên soạn lịch sử tự động"
        ↓
Hệ thống compile 7 DocTypes → populate documents → status = Compiling
        ↓
CMMS Admin review documents, upload files cho Missing items
CMMS Admin tick 4 reconciliation checkboxes
        ↓
CMMS Admin bấm "Gửi xác minh QA" → status = Pending Verification
        ↓
QA Officer nhận notification → mở S4 DocumentVerificationView
QA Officer review, xử lý Missing còn lại, nhập notes
QA Officer bấm "Xác minh đầy đủ" → status = Pending Approval
        ↓
HTM Manager nhận notification → mở S2 Tab 1
HTM Manager review, nhập approval notes
HTM Manager bấm "Phê duyệt" → status = Finalized
        ↓
CMMS Admin nhận notification → bấm "Submit & Khóa hồ sơ"
Confirm dialog → Submit → status = Archived (docstatus=1)
        ↓
AC Asset.status = "Archived"
ALE "archived" ghi lại
Thông báo cuối gửi tất cả stakeholders
```

### Flow B — Tìm kiếm Hồ sơ Lưu trữ Dài hạn

```
User vào S1 ArchiveListView
        ↓
User nhập từ khóa / chọn filter năm / department
        ↓
Hiển thị kết quả tức thì (debounce 300ms)
        ↓
User click vào hàng → S2 ArchiveDetailView
        ↓
User xem Tab 1 (thông tin) + Tab 2 (tài liệu) + Tab 4 (timeline)
        ↓
User tải PDF báo cáo vòng đời
Access log ghi lại: {user, aar_name, timestamp}
```

### Flow C — Expiry Alert

```
Scheduler monthly chạy check_retention_expiry()
        ↓
Tìm AAR release_date <= 60 ngày từ hôm nay
        ↓
Email gửi HTM Manager với danh sách AAR sắp hết hạn
        ↓
HTM Manager vào S5 Dashboard → thấy card "Sắp hết hạn"
        ↓
HTM Manager click → S1 filter status + expiry
        ↓
HTM Manager quyết định: gia hạn (tăng retention_years) hoặc tiêu hủy
```

---

## 13. TypeScript Types

```typescript
// types/imm14.ts

export interface ArchiveRecord {
  name: string
  asset: string
  asset_name: string
  asset_serial_no: string
  device_model: string
  department: string
  decommission_request: string | null
  archive_date: string
  release_date: string
  retention_years: number
  storage_location: string
  status: ArchiveStatus
  docstatus: 0 | 1 | 2
  total_documents_archived: number
  reconcile_cmms: 0 | 1
  reconcile_inventory: 0 | 1
  reconcile_finance: 0 | 1
  reconcile_legal: 0 | 1
  reconciliation_notes: string
  qa_verified_by: string | null
  qa_verification_date: string | null
  qa_verification_notes: string | null
  approved_by: string | null
  approval_date: string | null
  approval_notes: string | null
  archive_notes: string
  summary_report_url: string | null
  documents: ArchiveDocumentEntry[]
}

export type ArchiveStatus =
  | 'Draft'
  | 'Compiling'
  | 'Pending Verification'
  | 'Pending Approval'
  | 'Finalized'
  | 'Archived'

export interface ArchiveDocumentEntry {
  name: string
  document_type: string
  source_module: string
  document_name: string | null
  document_ref_url: string | null
  document_date: string | null
  archive_status: 'Included' | 'Missing' | 'Waived'
  is_required: 0 | 1
  waive_reason: string | null
  verified_by: string | null
  notes: string
}

export interface TimelineEvent {
  date: string
  event_type: string
  module: string
  record: string
  actor: string
  notes: string
}

export interface LifecycleTimeline {
  asset: string
  asset_name: string
  serial_no: string
  lifecycle_years: number
  total_events: number
  timeline: TimelineEvent[]
}

export interface DashboardMetrics {
  year: number
  summary: {
    archived_ytd: number
    total_archived_all_time: number
    pending_verification: number
    pending_approval: number
    in_progress: number
    expiring_within_30_days: number
    expiring_within_60_days: number
  }
  quality: {
    avg_documents_per_archive: number
    document_completeness_rate: number
    missing_document_rate: number
    reconciliation_closure_rate: number
  }
  performance: {
    avg_time_to_archive_days: number
    max_time_to_archive_days: number
    min_time_to_archive_days: number
  }
  expiring_soon: Array<{
    name: string
    asset: string
    asset_name: string
    release_date: string
    days_until_expiry: number
  }>
  by_department: Array<{ department: string; count: number }>
  by_year: Array<{ year: number; count: number }>
}

export interface SearchFilters {
  asset?: string
  status?: ArchiveStatus
  year?: number
  device_model?: string
  department?: string
  page: number
  page_size: number
}

export interface SearchResult {
  rows: ArchiveRecord[]
  total: number
  page: number
  page_size: number
}
```

---

*IMM-14 UI/UX Guide v2.0.0 — AssetCore / Bệnh viện Nhi Đồng 1*
*Vue 3 · TypeScript · Tailwind CSS · Pinia · Lucide Icons*
