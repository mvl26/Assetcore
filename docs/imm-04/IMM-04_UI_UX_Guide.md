# IMM-04 — UI/UX Guide
## Frontend Specification: Vue 3 + Pinia

**Module:** IMM-04  
**Version:** 1.0  
**Ngày:** 2026-04-17  
**Trạng thái:** Draft

---

## 1. Sitemap / Vue Routes

```
/imm-04/
├── /                          → CommissioningListPage    (Danh sách phiếu)
├── /new                       → CommissioningFormPage    (Tạo mới)
├── /:id                       → CommissioningDetailPage  (Chi tiết / Edit)
├── /:id/checklist             → ChecklistPage            (Nhập baseline results)
├── /:id/documents             → DocumentsPage            (Upload tài liệu)
├── /:id/nc                    → NonConformancePage       (Quản lý NC)
├── /:id/timeline              → TimelinePage             (Lifecycle event log)
└── /:id/handover              → HandoverPreviewPage      (Preview biên bản bàn giao)
```

**Route Config (`src/router/imm04.ts`):**

```typescript
import { RouteRecordRaw } from 'vue-router'

export const imm04Routes: RouteRecordRaw[] = [
  {
    path: '/imm-04',
    component: () => import('@/layouts/ModuleLayout.vue'),
    meta: { module: 'IMM-04', title: 'Nghiệm Thu & Bàn Giao' },
    children: [
      {
        path: '',
        name: 'commissioning-list',
        component: () => import('@/pages/imm04/CommissioningListPage.vue'),
        meta: { requiresRole: ['TBYT Officer', 'Biomed Engineer', 'Workshop Manager'] },
      },
      {
        path: 'new',
        name: 'commissioning-new',
        component: () => import('@/pages/imm04/CommissioningFormPage.vue'),
        meta: { requiresRole: ['TBYT Officer'] },
      },
      {
        path: ':id',
        name: 'commissioning-detail',
        component: () => import('@/pages/imm04/CommissioningDetailPage.vue'),
        props: true,
      },
      {
        path: ':id/checklist',
        name: 'commissioning-checklist',
        component: () => import('@/pages/imm04/ChecklistPage.vue'),
        props: true,
        meta: { requiresRole: ['Biomed Engineer'] },
      },
      {
        path: ':id/documents',
        name: 'commissioning-documents',
        component: () => import('@/pages/imm04/DocumentsPage.vue'),
        props: true,
      },
      {
        path: ':id/nc',
        name: 'commissioning-nc',
        component: () => import('@/pages/imm04/NonConformancePage.vue'),
        props: true,
      },
      {
        path: ':id/timeline',
        name: 'commissioning-timeline',
        component: () => import('@/pages/imm04/TimelinePage.vue'),
        props: true,
      },
      {
        path: ':id/handover',
        name: 'commissioning-handover',
        component: () => import('@/pages/imm04/HandoverPreviewPage.vue'),
        props: true,
        meta: { requiresRole: ['Biomed Engineer', 'Clinical Head', 'Board'] },
      },
    ],
  },
]
```

---

## 2. Component Architecture

### 2.1 Component Tree

```
CommissioningDetailPage
├── PageHeader
│   ├── StatusBadge (props: status)
│   └── ActionBar (props: status, userRole → emits: action)
├── CommissioningFormPanel
│   ├── BasicInfoSection
│   │   ├── POLinkField
│   │   ├── ItemLinkField
│   │   └── RiskClassBadge (props: riskClass — auto-highlight if C/D/Radiation)
│   ├── VendorSection
│   └── LocationSection
├── TabsContainer
│   ├── Tab: DocumentsTab
│   │   └── DocumentRecordTable
│   │       ├── DocumentRow (per doc)
│   │       │   ├── StatusPill
│   │       │   └── UploadButton → FileUploader
│   │       └── AddDocumentButton
│   ├── Tab: ChecklistTab
│   │   └── BaselineChecklistTable
│   │       ├── ChecklistRow (per item)
│   │       │   ├── ResultSelect (Pass/Fail/N/A)
│   │       │   ├── MeasuredValueInput (conditional: Numeric)
│   │       │   └── CriticalBadge (if is_critical)
│   │       └── OverallResultSummary
│   ├── Tab: NonConformanceTab
│   │   ├── NCTable
│   │   │   └── NCRow → NCDetailModal
│   │   └── ReportNCButton
│   └── Tab: TimelineTab
│       └── LifecycleTimeline (read-only, immutable display)
└── BarcodePanel (visible at Identification state)
    ├── BarcodeScanner (uses camera or USB HID)
    ├── InternalTagInput
    └── GenerateBarcodeButton
```

---

### 2.2 Key Component Specs

#### `ActionBar.vue`
```typescript
// Props
interface Props {
  status: CommissioningStatus
  userRole: string[]
  hasOpenNc: boolean
  allDocsReceived: boolean
  allChecklistPass: boolean
  boardApprover: string | null
}

// Emits
type Emits = {
  action: [actionName: WorkflowAction]
}

// WorkflowAction union type
type WorkflowAction =
  | 'proceed_to_installation'   // Draft → To_Be_Installed (G01)
  | 'start_installation'        // To_Be_Installed → Installing
  | 'complete_installation'     // Installing → Identification
  | 'assign_identification'     // Identification → Initial_Inspection
  | 'submit_baseline'           // Initial_Inspection → Clinical_Release | Clinical_Hold
  | 'clear_clinical_hold'       // Clinical_Hold → Clinical_Release
  | 'approve_release'           // Pending → Clinical_Release (Board)
  | 'report_nc'                 // Any → Non_Conformance
  | 'report_doa'                // Installing → Return_To_Vendor
  | 'resolve_nc'                // Non_Conformance → [back to flow]
  | 'return_to_vendor'          // Non_Conformance → Return_To_Vendor
```

#### `StatusBadge.vue`
```typescript
interface Props {
  status: CommissioningStatus
  size?: 'sm' | 'md' | 'lg'
}

// Color mapping
const STATUS_COLORS: Record<CommissioningStatus, string> = {
  Draft_Reception:    'gray',
  Pending_Doc_Verify: 'yellow',
  To_Be_Installed:    'blue',
  Installing:         'blue',
  Identification:     'purple',
  Initial_Inspection: 'purple',
  Clinical_Hold:      'red',
  Re_Inspection:      'orange',
  Non_Conformance:    'red',
  Clinical_Release:   'green',
  Return_To_Vendor:   'gray',
}
```

#### `BarcodeScanner.vue`
```typescript
interface Props {
  mode: 'camera' | 'usb-hid'
  expectedFormat?: 'QR' | 'CODE128' | 'CODE39' | 'auto'
}

// Emits
type Emits = {
  scanned: [value: string]
  error: [message: string]
}

// Camera mode uses @zxing/browser
// USB HID mode listens to keydown events from scanner (fast keydown sequence ending in Enter)
```

#### `DocumentRecordTable.vue`
```typescript
interface Props {
  documents: DocumentRecord[]
  readonly: boolean
  commissioningId: string
}

type Emits = {
  upload: [docIndex: number, file: File]
  statusChange: [docIndex: number, newStatus: DocumentStatus]
}
```

---

## 3. Form Specs — Commissioning Form

### 3.1 Section: Thông Tin Cơ Bản

| Field Label | Type | Required | Validation | Help Text | Conditional Display |
|---|---|---|---|---|---|
| Đơn Mua Hàng | Link (Purchase Order) | Yes | PO phải tồn tại và không Cancelled | Chọn PO từ IMM-03 — số item sẽ tự điền | Luôn hiển thị |
| Thiết Bị (Item) | Link (Item) | Yes | is_fixed_asset = True | Mã thiết bị từ Item master | Auto-fill từ PO khi chỉ có 1 item |
| Nhà Cung Cấp | Link (Supplier) | Yes | Phải tồn tại | Đơn vị giao thiết bị | Auto-fill từ PO |
| Loại Thiết Bị | Link (Asset Category) | Yes | Read-only | Danh mục tài sản | Auto-fill từ Item |
| Phân Loại Rủi Ro | Select (A/B/C/D/Radiation) | Yes | Auto-fill; Warning nếu edit | Xem NĐ98/2021 Phụ lục I | Auto-fill từ Item; highlight đỏ nếu C/D/Radiation |
| Ngày Nhận Hàng | Date | Yes | Không được là tương lai | Ngày thiết bị về kho / bệnh viện | Luôn hiển thị |
| Địa Điểm Lắp Đặt | Link (Location) | Yes | Phải là Location active | Khoa/phòng sẽ đặt máy | Luôn hiển thị |

### 3.2 Section: Thông Tin Vendor

| Field Label | Type | Required | Validation | Help Text | Conditional Display |
|---|---|---|---|---|---|
| Người Liên Hệ Vendor | Data | No | Không có | Tên + SĐT kỹ thuật viên | Luôn hiển thị |
| Mã Installation (Vendor) | Data | No | Không có | Số biên bản lắp đặt của nhà cung cấp | Hiển thị từ S04 (Installing) |

### 3.3 Section: Định Danh Thiết Bị

| Field Label | Type | Required | Validation | Help Text | Conditional Display |
|---|---|---|---|---|---|
| Serial Number (Nhà Sản Xuất) | Data + Barcode Scan | Yes | VR-01: Unique; Real-time check on blur | SN in trên thân máy hoặc quét barcode | Hiển thị từ S05 (Identification) |
| Mã Nội Bộ | Data | No | Unique; auto-gen nếu blank | Mã bệnh viện gắn cho thiết bị (vd: BVNK-MRI-001) | Hiển thị từ S05 |
| Barcode / QR | Image (generated) | No | Read-only | QR code tự động tạo sau khi gán SN | Hiển thị sau khi generate |
| Số Giấy Phép Phóng Xạ | Data | Conditional | Bắt buộc nếu Radiation | Số giấy phép từ Cục ATBXHN | Chỉ khi risk_class = Radiation |

### 3.4 Section: Kiểm Tra Cơ Sở Hạ Tầng

| Field Label | Type | Required | Validation | Help Text | Conditional Display |
|---|---|---|---|---|---|
| Cơ Sở Hạ Tầng Đạt | Checkbox | Yes (at G02) | Phải tick trước khi → Installing | Xác nhận điện, khí nén, nước đạt yêu cầu | Hiển thị từ S03 (To_Be_Installed) |

### 3.5 Section: Phê Duyệt

| Field Label | Type | Required | Validation | Help Text | Conditional Display |
|---|---|---|---|---|---|
| Kỹ Thuật Viên Phụ Trách | Link (User) | Yes | role = Biomed Engineer | KTV thực hiện baseline test | Luôn hiển thị |
| Trưởng Khoa | Link (User) | Yes | role = Clinical Head | Trưởng khoa xác nhận site | Luôn hiển thị |
| Nhân Viên QA | Link (User) | Conditional | role = QA Officer | Bắt buộc nếu Class C/D/Radiation | Chỉ khi risk_class ∈ {C, D, Radiation} |
| Người Phê Duyệt (BGĐ) | Link (User) | Conditional | role = Board / CEO | Bắt buộc trước Clinical Release | Chỉ khi status → Clinical_Release; highlight |
| Biên Bản Bàn Giao | File (PDF) | No (system-generated) | Read-only | Tự động tạo khi Release | Hiển thị tại S10 |

### 3.6 Section: Ghi Chú

| Field Label | Type | Required | Validation | Help Text | Conditional Display |
|---|---|---|---|---|---|
| Ghi Chú | Textarea | No | Không có | Ghi chú tự do về quá trình commissioning | Luôn hiển thị |

---

## 4. Pinia Store — `useImm04Store`

**File:** `src/stores/imm04Store.ts`

```typescript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type {
  AssetCommissioning,
  CommissioningListItem,
  CommissioningStatus,
  DocumentRecord,
  ChecklistItem,
  NonConformance,
  LifecycleEvent,
} from '@/types/imm04'
import { imm04Api } from '@/api/imm04'

export const useImm04Store = defineStore('imm04', () => {
  // ─── State ────────────────────────────────────────────────────────────────

  // List view
  const list = ref<CommissioningListItem[]>([])
  const listTotal = ref(0)
  const listFilters = ref<Record<string, string>>({})
  const listPage = ref(1)
  const listPageSize = ref(20)

  // Detail view
  const current = ref<AssetCommissioning | null>(null)
  const currentId = ref<string | null>(null)

  // UI state
  const loading = ref(false)
  const saving = ref(false)
  const error = ref<string | null>(null)
  const successMessage = ref<string | null>(null)

  // Barcode scanner
  const scannerActive = ref(false)
  const lastScannedValue = ref<string | null>(null)

  // ─── Getters ──────────────────────────────────────────────────────────────

  const currentStatus = computed<CommissioningStatus | null>(
    () => current.value?.status ?? null
  )

  const isEditable = computed<boolean>(() => {
    const nonEditableStatuses: CommissioningStatus[] = ['Clinical_Release', 'Return_To_Vendor']
    return current.value !== null && !nonEditableStatuses.includes(current.value.status)
  })

  const allDocumentsReceived = computed<boolean>(() => {
    if (!current.value) return false
    return current.value.documents
      .filter(d => d.is_mandatory)
      .every(d => d.status === 'Received')
  })

  const allChecklistPass = computed<boolean>(() => {
    if (!current.value) return false
    const items = current.value.checklist_items
    if (items.length === 0) return false
    return items.every(item => item.result === 'Pass' || item.result === 'N/A')
  })

  const hasOpenNc = computed<boolean>(() => {
    if (!current.value) return false
    return current.value.non_conformances.some(
      nc => nc.status === 'Open' || nc.status === 'Under Review'
    )
  })

  const isHighRisk = computed<boolean>(() => {
    return ['C', 'D', 'Radiation'].includes(current.value?.risk_class ?? '')
  })

  const pendingDocCount = computed<number>(() => {
    if (!current.value) return 0
    return current.value.documents.filter(
      d => d.is_mandatory && d.status === 'Pending'
    ).length
  })

  const failedChecklistCount = computed<number>(() => {
    if (!current.value) return 0
    return current.value.checklist_items.filter(i => i.result === 'Fail').length
  })

  const openNcCount = computed<number>(() => {
    if (!current.value) return 0
    return current.value.non_conformances.filter(
      nc => nc.status === 'Open' || nc.status === 'Under Review'
    ).length
  })

  // Available workflow actions based on current status and user role
  const availableActions = computed<string[]>(() => {
    // Delegated to ActionBar component which receives status + role props
    // Store exposes raw data; ActionBar handles display logic
    return []
  })

  // ─── Actions ──────────────────────────────────────────────────────────────

  async function fetchList(filters?: Record<string, string>) {
    loading.value = true
    error.value = null
    try {
      if (filters) listFilters.value = filters
      const res = await imm04Api.getList({
        filters: listFilters.value,
        page: listPage.value,
        page_size: listPageSize.value,
      })
      list.value = res.data.items
      listTotal.value = res.data.total
    } catch (e: any) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  async function fetchDetail(id: string) {
    loading.value = true
    error.value = null
    try {
      currentId.value = id
      const res = await imm04Api.getDetail(id)
      current.value = res.data
    } catch (e: any) {
      error.value = e.message
      current.value = null
    } finally {
      loading.value = false
    }
  }

  async function save() {
    if (!current.value) return
    saving.value = true
    error.value = null
    try {
      const res = await imm04Api.save(current.value)
      current.value = res.data
      successMessage.value = 'Đã lưu thành công.'
    } catch (e: any) {
      error.value = e.message
    } finally {
      saving.value = false
    }
  }

  async function executeAction(action: string, payload?: Record<string, unknown>) {
    if (!currentId.value) return
    saving.value = true
    error.value = null
    try {
      const res = await imm04Api.action(currentId.value, action, payload ?? {})
      current.value = res.data
      successMessage.value = res.message ?? 'Thao tác thành công.'
    } catch (e: any) {
      error.value = e.message
    } finally {
      saving.value = false
    }
  }

  async function uploadDocument(docIndex: number, file: File) {
    if (!currentId.value) return
    saving.value = true
    try {
      const res = await imm04Api.uploadDocument(currentId.value, docIndex, file)
      // Refresh current doc record
      if (current.value) {
        current.value.documents[docIndex] = res.data
      }
      successMessage.value = 'Tài liệu đã được upload.'
    } catch (e: any) {
      error.value = e.message
    } finally {
      saving.value = false
    }
  }

  async function submitBaseline(checklistResults: ChecklistItem[]) {
    if (!currentId.value) return
    saving.value = true
    try {
      const res = await imm04Api.submitBaseline(currentId.value, checklistResults)
      current.value = res.data
      successMessage.value = 'Kết quả kiểm tra đã được ghi nhận.'
    } catch (e: any) {
      error.value = e.message
    } finally {
      saving.value = false
    }
  }

  async function reportNonConformance(nc: Partial<NonConformance>) {
    if (!currentId.value) return
    saving.value = true
    try {
      const res = await imm04Api.reportNc(currentId.value, nc)
      current.value = res.data
      successMessage.value = 'Phiếu Không Phù Hợp đã được tạo.'
    } catch (e: any) {
      error.value = e.message
    } finally {
      saving.value = false
    }
  }

  function setScannerActive(active: boolean) {
    scannerActive.value = active
  }

  function onBarcodeScanned(value: string) {
    lastScannedValue.value = value
    if (current.value) {
      current.value.vendor_sn = value
    }
  }

  function clearMessages() {
    error.value = null
    successMessage.value = null
  }

  function reset() {
    current.value = null
    currentId.value = null
    error.value = null
    successMessage.value = null
  }

  return {
    // State
    list, listTotal, listFilters, listPage, listPageSize,
    current, currentId,
    loading, saving, error, successMessage,
    scannerActive, lastScannedValue,
    // Getters
    currentStatus, isEditable,
    allDocumentsReceived, allChecklistPass,
    hasOpenNc, isHighRisk,
    pendingDocCount, failedChecklistCount, openNcCount,
    availableActions,
    // Actions
    fetchList, fetchDetail, save, executeAction,
    uploadDocument, submitBaseline, reportNonConformance,
    setScannerActive, onBarcodeScanned,
    clearMessages, reset,
  }
})
```

---

## 5. Client Logic

### 5.1 Workflow Action Buttons Per State

| Trạng Thái | Nút Hiển Thị | Role Cho Phép | Điều Kiện Enable |
|---|---|---|---|
| Draft_Reception | "Bắt Đầu Kiểm Tra Tài Liệu" | TBYT Officer | Luôn enable sau khi điền đủ trường bắt buộc |
| Pending_Doc_Verify | "Tiến Hành Lắp Đặt" | TBYT Officer | `allDocumentsReceived = true` (G01 pass) |
| Pending_Doc_Verify | "Trả Lại Draft" | TBYT Officer | Luôn enable |
| To_Be_Installed | "Bắt Đầu Lắp Đặt" | TBYT Officer, Clinical Head | `facility_checklist_pass = true` |
| To_Be_Installed | "Báo Cáo Không Phù Hợp" | TBYT Officer | Luôn enable |
| Installing | "Hoàn Thành Lắp Đặt" | Vendor Tech, Biomed Engineer | Luôn enable |
| Installing | "Khai Báo DOA / Lỗi" | Vendor Tech, Biomed Engineer | Luôn enable → mở NC modal |
| Identification | "Xác Nhận Định Danh" | Biomed Engineer | `vendor_sn` không trống + unique check pass |
| Initial_Inspection | "Nộp Kết Quả Kiểm Tra" | Biomed Engineer | Tất cả checklist items đã điền result |
| Clinical_Hold | "Gỡ Hold (Upload License)" | QA Officer | License document status = Received |
| Re_Inspection | "Yêu Cầu Kiểm Tra Lại" | Biomed Engineer | Luôn enable |
| Re_Inspection | "Báo Cáo Không Phù Hợp" | Biomed Engineer | Luôn enable |
| Non_Conformance | "NC Đã Giải Quyết — Tiếp Tục" | Biomed Engineer, Workshop Manager | `hasOpenNc = false` |
| Non_Conformance | "Trả Hàng Vendor" | Workshop Manager, Board | Severity = Critical |
| Clinical_Release | "Phê Duyệt Release" | Board, CEO | `!hasOpenNc && allChecklistPass && board_approver ≠ null` |
| Clinical_Release | "In Biên Bản Bàn Giao" | All | Status = Clinical_Release |

---

### 5.2 Conditional Fields Logic

```typescript
// useImm04FormLogic.ts — composable cho conditional display

export function useImm04FormLogic(store: ReturnType<typeof useImm04Store>) {
  const showQaOfficerField = computed(() =>
    ['C', 'D', 'Radiation'].includes(store.current?.risk_class ?? '')
  )

  const showRadiationLicenseField = computed(() =>
    store.current?.risk_class === 'Radiation'
  )

  const showBoardApproverField = computed(() =>
    store.currentStatus === 'Clinical_Release' ||
    store.currentStatus === 'Clinical_Hold'
  )

  const showIdentificationFields = computed(() => {
    const showStates: CommissioningStatus[] = [
      'Identification', 'Initial_Inspection', 'Clinical_Hold',
      'Clinical_Release', 'Re_Inspection',
    ]
    return showStates.includes(store.currentStatus ?? '' as any)
  })

  const showBarcodePanel = computed(() =>
    store.currentStatus === 'Identification'
  )

  const showFacilityCheckbox = computed(() =>
    ['To_Be_Installed', 'Installing', 'Identification',
     'Initial_Inspection', 'Clinical_Hold', 'Clinical_Release'].includes(
       store.currentStatus ?? ''
     )
  )

  const isDocTableReadonly = computed(() =>
    ['Clinical_Release', 'Return_To_Vendor'].includes(store.currentStatus ?? '')
  )

  const isChecklistReadonly = computed(() =>
    store.currentStatus !== 'Initial_Inspection' &&
    store.currentStatus !== 'Re_Inspection'
  )

  // Risk class highlight: đỏ nếu C/D/Radiation
  const riskClassVariant = computed(() => {
    const rc = store.current?.risk_class
    if (!rc) return 'default'
    if (['C', 'D', 'Radiation'].includes(rc)) return 'danger'
    if (rc === 'B') return 'warning'
    return 'success'
  })

  return {
    showQaOfficerField,
    showRadiationLicenseField,
    showBoardApproverField,
    showIdentificationFields,
    showBarcodePanel,
    showFacilityCheckbox,
    isDocTableReadonly,
    isChecklistReadonly,
    riskClassVariant,
  }
}
```

---

### 5.3 Barcode Scanner Integration

```typescript
// useBarcodeScanner.ts

import { ref, onMounted, onUnmounted } from 'vue'

export function useBarcodeScanner(onScanned: (value: string) => void) {
  const buffer = ref('')
  const lastKeyTime = ref(0)
  const SCAN_THRESHOLD_MS = 50 // USB HID scanner sends chars very fast

  function handleKeydown(event: KeyboardEvent) {
    const now = Date.now()
    if (event.key === 'Enter') {
      if (buffer.value.length > 3) {
        onScanned(buffer.value)
      }
      buffer.value = ''
      return
    }
    if (now - lastKeyTime.value > 500) {
      // Gap too long — likely manual typing, not scanner
      buffer.value = ''
    }
    buffer.value += event.key
    lastKeyTime.value = now
  }

  function initCameraScanner() {
    // Uses @zxing/browser BrowserMultiFormatReader
    // Configured to scan QR + Code128 + Code39
  }

  onMounted(() => {
    window.addEventListener('keydown', handleKeydown)
  })

  onUnmounted(() => {
    window.removeEventListener('keydown', handleKeydown)
  })

  return { buffer }
}
```

---

### 5.4 Real-Time Serial Number Validation

```typescript
// In CommissioningFormPage.vue

async function onSnBlur(sn: string) {
  if (!sn || sn.length < 3) return
  try {
    const res = await imm04Api.checkSnUnique(sn, store.currentId)
    if (!res.data.is_unique) {
      snError.value = `VR-01: Serial đã được gán cho thiết bị ${res.data.existing_asset}`
      snValid.value = false
    } else {
      snError.value = null
      snValid.value = true
    }
  } catch {
    snError.value = 'Không thể kiểm tra Serial Number. Vui lòng thử lại.'
  }
}
```

---

### 5.5 Clinical Hold — Auto-Transition Alert

Khi Biomed Engineer nộp kết quả Initial Inspection và `risk_class ∈ {C, D, Radiation}`, server trả về `new_status = Clinical_Hold`. Frontend hiển thị:

```vue
<!-- ClinicalHoldAlert.vue -->
<template>
  <div v-if="showAlert" class="alert alert-warning">
    <h4>Thiết bị đã chuyển vào Clinical Hold</h4>
    <p>
      Thiết bị phân loại <strong>{{ riskClass }}</strong> phải được kiểm định/
      cấp phép bởi cơ quan có thẩm quyền trước khi đưa vào sử dụng lâm sàng
      (NĐ98/2021 Điều 35-37).
    </p>
    <p>Nhân viên QA (<strong>{{ qaOfficer }}</strong>) đã được thông báo.</p>
    <ul>
      <li v-for="doc in missingLicenses" :key="doc.doc_type">
        Chờ: {{ doc.doc_label }}
      </li>
    </ul>
  </div>
</template>
```

---

### 5.6 Checklist Page — Baseline Entry UX

- Tất cả items hiển thị dạng table với inline editing
- Items với `is_critical = true` được đánh dấu badge đỏ "QUAN TRỌNG"
- Nếu `measurement_type = Numeric`: hiển thị input số + expected range [min — max]
  - Nếu measured_value nằm ngoài range → cell highlight vàng, result auto-set = Fail
- Progress bar tính % items đã điền
- Nút "Nộp Kết Quả" chỉ enable khi 100% items đã có result
- Sau khi submit: nếu có fail → hiển thị danh sách items fail + transition reason
