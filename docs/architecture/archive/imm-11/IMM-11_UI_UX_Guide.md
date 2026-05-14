# IMM-11 — UI/UX Guide
## Frontend Design — Vue 3 + Pinia

**Module:** IMM-11
**Version:** 1.0
**Ngày:** 2026-04-17
**Trạng thái:** Draft

---

## 1. Sitemap & Routes

```
/imm-11/                              → CalibrationDashboard (tổng quan KPI)
/imm-11/list                          → CalibrationList (danh sách CAL records)
/imm-11/create                        → CalibrationForm (tạo mới)
/imm-11/:id                           → CalibrationDetail (xem chi tiết)
/imm-11/:id/edit                      → CalibrationForm (chỉnh sửa, trước submit)
/imm-11/schedule                      → CalibrationSchedule (lịch calibration calendar view)
/imm-11/capa                          → CAPAList (danh sách CAPA records)
/imm-11/capa/:id                      → CAPADetail
/imm-11/report/compliance             → ComplianceReport (báo cáo KPI)
/imm-11/asset/:assetId/history        → AssetCalibrationHistory (lịch sử hiệu chuẩn của 1 thiết bị)
```

**Route guards:**
- KTV HTM: tất cả routes trừ `/report/compliance` (read-only)
- Workshop Manager: full access
- QA Officer: `/imm-11/capa/*` (write), các route còn lại (read-only)
- PTP Khối 2: `/imm-11/`, `/imm-11/report/compliance` (read-only)

---

## 2. Component Architecture

```
src/
└── views/imm11/
    ├── CalibrationDashboard.vue          ← KPI summary + due soon widget
    ├── CalibrationList.vue               ← Table với filter/search
    ├── CalibrationForm.vue               ← Form tạo/chỉnh sửa
    ├── CalibrationDetail.vue             ← Chi tiết record (submitted)
    ├── CalibrationSchedule.vue           ← Calendar view
    ├── CAPAList.vue                      ← Danh sách CAPA
    ├── CAPADetail.vue                    ← Chi tiết CAPA + actions
    └── ComplianceReport.vue              ← KPI charts

└── components/imm11/
    ├── MeasurementTable.vue              ← Child table với tolerance indicator
    ├── CertificateUploader.vue           ← PDF upload + preview
    ├── CAPACreateModal.vue               ← Modal mở CAPA (manual, nếu cần)
    ├── LookbackPanel.vue                 ← Panel hiển thị thiết bị cùng model
    ├── CalibrationStatusBadge.vue        ← Badge màu trạng thái
    ├── CalibraitonStickerUpload.vue      ← Upload ảnh sticker
    ├── CalibrationTimeline.vue           ← Timeline lịch sử cal của asset
    └── ComplianceKPICard.vue             ← Card KPI (compliance rate, OOT rate)
```

---

## 3. Form Specs

### 3.1 CalibrationForm.vue

**Header Section:**
```
┌─────────────────────────────────────────────────────────────────┐
│ [← Back]  Phiếu Hiệu chuẩn  CAL-2026-00001  [SCHEDULED badge]  │
│                                              [Save] [Submit]    │
└─────────────────────────────────────────────────────────────────┘
```

**Section 1 — Thông tin chung:**
```
┌─────────────────────────────────────────────────────────────────┐
│ Thiết bị *          [ACC-ASS-2026-00101 🔍]  Model: Sysmex XN  │
│ Loại hiệu chuẩn *   ( ) External  ( ) In-House                 │
│ KTV thực hiện *     [Nguyễn Văn A 🔍]                           │
│ Người phân công     [Trần Thị B 🔍]                              │
│ PM Work Order       [Tùy chọn — liên kết IMM-08 🔍]             │
│ Ngày đến hạn        [2026-05-01] (read-only, từ Asset)          │
│ Chu kỳ (ngày)       [365] (auto từ Device Model)                │
└─────────────────────────────────────────────────────────────────┘
```

**Section 2 — Thông tin Lab (hiển thị khi External):**
```
┌─────────────────────────────────────────────────────────────────┐
│ Tên tổ chức kiểm định *   [Trung tâm Đo lường Chất lượng 3]    │
│ Số công nhận ISO 17025 *  [VLAS-T-028]                          │
│ Số hợp đồng               [HĐ-2026-KĐ-015]                     │
│ Ngày gửi thiết bị         [2026-04-20] 📅                       │
│ Người bàn giao            [KTV Nguyễn A]                        │
│ Ngày nhận về              [2026-04-25] 📅                       │
│ Ngày cấp chứng chỉ *      [2026-04-24] 📅                       │
│ Số chứng chỉ              [2026-KĐ-01234]                       │
└─────────────────────────────────────────────────────────────────┘
```

**Section 3 — Upload Chứng chỉ (hiển thị khi External):**
```
┌─────────────────────────────────────────────────────────────────┐
│ Calibration Certificate *                                       │
│ ┌──────────────────────────────────────────────┐               │
│ │                                              │               │
│ │   📄 Drag & Drop PDF hoặc Click để chọn file │               │
│ │                                              │               │
│ └──────────────────────────────────────────────┘               │
│ [2026-KĐ-01234_Sysmex-XN.pdf ✓]  [Xem trước] [Xóa]           │
└─────────────────────────────────────────────────────────────────┘
```

**Section 4 — Kết quả Đo lường (MeasurementTable component):**
```
┌─────────────────────────────────────────────────────────────────┐
│ Kết quả Đo lường Hiệu chuẩn                                    │
│ [+ Thêm tham số]                                                │
│                                                                  │
│  Tham số      ĐV    Danh định  Tol(+)  Tol(-)  Đo được  Kết quả│
│  ──────────── ────  ─────────  ──────  ──────  ────────  ───────│
│  CBC WBC      10³/µ  7.5       ±3%     ±3%     [7.6]    ✅ Pass │
│  PLT Count    10³/µ  250       ±5%     ±5%     [245]    ✅ Pass │
│  HGB          g/dL   14.0      ±3%     ±3%     [14.8]   ⚠️ Fail│
│  ──────────── ────  ─────────  ──────  ──────  ────────  ───────│
│                                         Kết quả tổng: ❌ FAILED │
└─────────────────────────────────────────────────────────────────┘
```

**Section 5 — Thông tin bổ sung:**
```
┌─────────────────────────────────────────────────────────────────┐
│ Đã gắn sticker hiệu chuẩn  [✓]                                 │
│ Ảnh sticker                 [Upload ảnh] 📷                     │
│ Ghi chú KTV                 [Textarea...]                       │
│ [Thiết bị chuẩn (In-House)] Serial: ___  Traceability: ___     │
└─────────────────────────────────────────────────────────────────┘
```

**Submit Dialog (khi overall_result = Fail):**
```
┌─────────────────────────────────────────────────────────────────┐
│ ⚠️  CẢNH BÁO — Calibration FAIL                                │
│                                                                  │
│ Kết quả: 1/3 tham số NGOÀI DUNG SAI                            │
│                                                                  │
│ Khi Submit:                                                      │
│ • Thiết bị sẽ bị chuyển sang "Out of Service"                   │
│ • CAPA Record sẽ được tạo tự động                               │
│ • Lookback assessment cho 3 thiết bị cùng model sẽ bắt đầu    │
│ • Thông báo gửi QA Officer và PTP Khối 2                       │
│                                                                  │
│                          [Hủy]  [Xác nhận Submit]              │
└─────────────────────────────────────────────────────────────────┘
```

---

### 3.2 MeasurementTable.vue — Chi tiết

**Props:**
```typescript
interface Props {
  measurements: CalibrationMeasurement[];
  readonly: boolean;
  showTolerance: boolean;
}
```

**Tolerance Indicator Logic:**
```typescript
function getRowClass(row: CalibrationMeasurement): string {
  if (!row.measured_value) return '';
  
  const dev = row.measured_value - row.nominal_value;
  const tolPlus = (row.tolerance_plus / 100) * Math.abs(row.nominal_value);
  const tolMinus = (row.tolerance_minus / 100) * Math.abs(row.nominal_value);
  
  if (dev > tolPlus || dev < -tolMinus) return 'table-row-fail';   // đỏ
  
  const warnFactor = 0.85; // cảnh báo khi gần biên 85%
  if (Math.abs(dev) > warnFactor * Math.max(tolPlus, tolMinus)) return 'table-row-warn'; // vàng
  
  return 'table-row-pass'; // xanh
}
```

**Visual Indicator:**
- Pass (xanh lá): giá trị trong tolerance + badge ✅
- Warning (vàng): giá trị trong tolerance nhưng gần biên (>85%) + badge ⚠️
- Fail (đỏ): giá trị ngoài tolerance + badge ❌ + ô highlight đỏ

---

### 3.3 CalibrationDashboard.vue

```
┌─────────────────────────────────────────────────────────────────────────┐
│  IMM-11 — Bảng điều khiển Hiệu chuẩn                        Tháng 04/2026│
├──────────────┬──────────────┬──────────────┬──────────────────────────────┤
│ Compliance   │ OOT Rate     │ CAPA Open    │ Avg Days to Cal              │
│ Rate         │              │              │                              │
│  87.5%       │   4.2%       │     3        │    12 ngày                  │
│  ████████▒   │   ▒          │  [!]         │  ←────────→                 │
│  14/16 đúng  │ 2/48 tham số │  cần xử lý  │  gửi → nhận                │
├──────────────┴──────────────┴──────────────┴──────────────────────────────┤
│  Thiết bị đến hạn trong 30 ngày                          [Xem tất cả →] │
│                                                                           │
│  🔴 Overdue (2)                                                           │
│  • Máy thở Drager V500 [ACC-001]  — Quá hạn 15 ngày  [Tạo CAL]         │
│  • Monitor BP Mindray  [ACC-002]  — Quá hạn 3 ngày   [Tạo CAL]         │
│                                                                           │
│  🟡 Due Soon (5)                                                          │
│  • Máy đo SpO2 Masimo  [ACC-005]  — Còn 7 ngày       [Tạo CAL]         │
│  • ECG Nihon Kohden    [ACC-006]  — Còn 14 ngày      [Tạo CAL]         │
│  • ...                                                                    │
├──────────────────────────────────────────────────────────────────────────┤
│  CAPA Đang Mở                                          [Xem tất cả →]   │
│  • CAPA-2026-00015 — ACC-008 Sysmex XN — Lookback Pending  [QA Review] │
│  • CAPA-2026-00012 — ACC-011 Ventilator — Overdue 5d        [Escalate] │
└──────────────────────────────────────────────────────────────────────────┘
```

---

### 3.4 CAPADetail.vue — Panel Lookback

```
┌─────────────────────────────────────────────────────────────────┐
│  Lookback Assessment                        [Trạng thái: PENDING]│
│  ─────────────────────────────────────────────────────────────  │
│  Model ảnh hưởng: Sysmex XN-1000                                │
│  Tham số bị lỗi: HGB (deviation 5.7%)                          │
│                                                                  │
│  Thiết bị cùng model cần kiểm tra:                             │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ # │ Asset       │ Khoa/Phòng    │ Cal gần nhất │ Action   │ │
│  │ 1 │ ACC-ASS-104 │ XN Máu       │ 2025-11-01   │ [Review] │ │
│  │ 2 │ ACC-ASS-105 │ Cấp cứu      │ 2025-10-15   │ [Review] │ │
│  │ 3 │ ACC-ASS-106 │ ICU          │ 2025-12-01   │ [Review] │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  Kết luận Lookback:  ( ) Cleared  ( ) Action Required           │
│  Ghi chú:            [Textarea...]                              │
│                                         [Lưu Lookback Findings] │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Pinia Store (`useImm11Store`)

### 4.1 Store Definition

```typescript
// src/stores/imm11.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { apiCall } from '@/utils/api'

export interface CalibrationRecord {
  name: string
  asset_ref: string
  asset_name: string
  device_model: string
  calibration_type: 'External' | 'In-House'
  status: string
  overall_result?: string
  certificate_date?: string
  next_calibration_date?: string
  lab_name?: string
  lab_accreditation_number?: string
  measurements: CalibrationMeasurement[]
  due_date?: string
  is_overdue?: boolean
}

export interface CalibrationMeasurement {
  parameter_name: string
  unit: string
  nominal_value: number
  tolerance_plus: number
  tolerance_minus: number
  measured_value?: number
  out_of_tolerance?: boolean
  result?: 'Pass' | 'Fail'
  notes?: string
}

export interface CAPARecord {
  name: string
  asset_ref: string
  calibration_ref: string
  status: string
  lookback_required: boolean
  lookback_status: string
  lookback_assets?: string[]
  root_cause_analysis?: string
}

export interface DashboardStats {
  compliance_rate_pct: number
  total_scheduled: number
  completed_on_time: number
  out_of_tolerance_rate: number
  capa_open_count: number
  avg_days_to_calibration: number
  overdue_list: CalibrationRecord[]
  due_soon_list: CalibrationRecord[]
}

export const useImm11Store = defineStore('imm11', () => {
  // State
  const calibrations = ref<CalibrationRecord[]>([])
  const currentCal = ref<CalibrationRecord | null>(null)
  const capaRecords = ref<CAPARecord[]>([])
  const dashboardStats = ref<DashboardStats | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Getters
  const overdueList = computed(() =>
    calibrations.value.filter(c => c.is_overdue)
  )

  const failedCalibrations = computed(() =>
    calibrations.value.filter(c => c.overall_result === 'Failed')
  )

  const openCAPAs = computed(() =>
    capaRecords.value.filter(c => c.status === 'Open')
  )

  const pendingLookback = computed(() =>
    capaRecords.value.filter(c => c.lookback_status === 'Pending')
  )

  // Actions

  async function fetchCalibrationList(filters?: Record<string, unknown>) {
    loading.value = true
    error.value = null
    try {
      const res = await apiCall('assetcore.api.imm11.get_calibration_list', filters)
      calibrations.value = res.data
    } catch (e: unknown) {
      error.value = (e as Error).message
    } finally {
      loading.value = false
    }
  }

  async function fetchCalibrationDetail(name: string) {
    loading.value = true
    try {
      const res = await apiCall('assetcore.api.imm11.get_calibration_detail', { name })
      currentCal.value = res.data
    } finally {
      loading.value = false
    }
  }

  async function createCalibration(payload: Partial<CalibrationRecord>) {
    loading.value = true
    try {
      const res = await apiCall('assetcore.api.imm11.create_calibration', payload)
      calibrations.value.unshift(res.data)
      return res.data
    } finally {
      loading.value = false
    }
  }

  async function sendToLab(name: string, payload: { lab_name: string; lab_accreditation_number: string; sent_date: string }) {
    const res = await apiCall('assetcore.api.imm11.send_to_lab', { name, ...payload })
    _updateCalInList(res.data)
    return res.data
  }

  async function submitCalibrationResults(name: string, payload: {
    measurements: CalibrationMeasurement[]
    certificate_date?: string
    certificate_number?: string
    certificate_file?: string
    calibration_sticker_attached: boolean
    technician_notes?: string
  }) {
    const res = await apiCall('assetcore.api.imm11.submit_calibration_results', { name, ...payload })
    _updateCalInList(res.data)
    if (currentCal.value?.name === name) {
      currentCal.value = res.data
    }
    // Nếu Fail, fetch CAPA list
    if (res.data.overall_result === 'Failed') {
      await fetchCAPAList()
    }
    return res.data
  }

  async function fetchCAPAList(filters?: Record<string, unknown>) {
    const res = await apiCall('assetcore.api.imm11.get_capa_list', filters)
    capaRecords.value = res.data
  }

  async function resolveCAPALookback(capaName: string, payload: {
    lookback_status: 'Cleared' | 'Action Required'
    lookback_findings: string
  }) {
    const res = await apiCall('assetcore.api.imm11.resolve_capa_lookback', { name: capaName, ...payload })
    _updateCAPAInList(res.data)
    return res.data
  }

  async function closeCAPARecord(capaName: string, payload: {
    root_cause_analysis: string
    corrective_action: string
    preventive_action: string
  }) {
    const res = await apiCall('assetcore.api.imm11.close_capa', { name: capaName, ...payload })
    _updateCAPAInList(res.data)
    return res.data
  }

  async function fetchDashboardStats(year: number, month: number) {
    const res = await apiCall('assetcore.api.imm11.get_calibration_compliance_report', { year, month })
    dashboardStats.value = res.data
  }

  // Utilities
  function computeMeasurementResult(m: CalibrationMeasurement): { out_of_tolerance: boolean; result: 'Pass' | 'Fail'; warn: boolean } {
    if (m.measured_value === undefined || m.measured_value === null) {
      return { out_of_tolerance: false, result: 'Pass', warn: false }
    }
    const base = Math.abs(m.nominal_value)
    const tolPlus = (m.tolerance_plus / 100) * base
    const tolMinus = (m.tolerance_minus / 100) * base
    const dev = m.measured_value - m.nominal_value
    const out = dev > tolPlus || dev < -tolMinus
    const warn = !out && Math.abs(dev) > 0.85 * Math.max(tolPlus, tolMinus)
    return { out_of_tolerance: out, result: out ? 'Fail' : 'Pass', warn }
  }

  function _updateCalInList(updated: CalibrationRecord) {
    const idx = calibrations.value.findIndex(c => c.name === updated.name)
    if (idx >= 0) calibrations.value[idx] = updated
  }

  function _updateCAPAInList(updated: CAPARecord) {
    const idx = capaRecords.value.findIndex(c => c.name === updated.name)
    if (idx >= 0) capaRecords.value[idx] = updated
  }

  return {
    // State
    calibrations, currentCal, capaRecords, dashboardStats, loading, error,
    // Getters
    overdueList, failedCalibrations, openCAPAs, pendingLookback,
    // Actions
    fetchCalibrationList, fetchCalibrationDetail, createCalibration,
    sendToLab, submitCalibrationResults, fetchCAPAList,
    resolveCAPALookback, closeCAPARecord, fetchDashboardStats,
    // Utilities
    computeMeasurementResult,
  }
})
```

---

## 5. Client Logic — Key Behaviors

### 5.1 MeasurementTable — Real-time Tolerance Indicator

```typescript
// Trong MeasurementTable.vue — watch measured_value, tự tính result
watch(
  () => measurements.value.map(m => m.measured_value),
  () => {
    measurements.value.forEach(m => {
      const { out_of_tolerance, result, warn } = store.computeMeasurementResult(m)
      m.out_of_tolerance = out_of_tolerance
      m.result = result
      m._warn = warn
    })
    // Tính overall_result
    overallResult.value = measurements.value.some(m => m.result === 'Fail') ? 'Failed' : 'Passed'
  },
  { deep: true }
)
```

### 5.2 Submit Confirmation Dialog — Fail Path

```typescript
async function handleSubmit() {
  if (overallResult.value === 'Failed') {
    const confirmed = await showConfirmDialog({
      title: 'Calibration FAIL — Xác nhận Submit',
      message: buildFailWarningMessage(),  // HTML warning với danh sách ảnh hưởng
      confirmLabel: 'Xác nhận Submit',
      confirmVariant: 'danger',
    })
    if (!confirmed) return
  }
  await store.submitCalibrationResults(calName.value, buildPayload())
}

function buildFailWarningMessage(): string {
  const failedParams = measurements.value.filter(m => m.result === 'Fail')
  return `
    <p><strong>${failedParams.length}</strong> tham số ngoài dung sai:</p>
    <ul>${failedParams.map(m => `<li>${m.parameter_name}: đo ${m.measured_value} ${m.unit} (danh định ${m.nominal_value} ± ${m.tolerance_plus}%)</li>`).join('')}</ul>
    <p>Sau khi Submit:</p>
    <ul>
      <li>Thiết bị → <strong>Out of Service</strong></li>
      <li>CAPA Record tự động mở</li>
      <li>Lookback assessment bắt đầu</li>
    </ul>
  `
}
```

### 5.3 CertificateUploader.vue — PDF Upload & Preview

```typescript
// Giới hạn file type + size
const ACCEPTED_TYPES = ['application/pdf']
const MAX_SIZE_MB = 20

async function handleFileSelect(file: File) {
  if (!ACCEPTED_TYPES.includes(file.type)) {
    toast.error('Chỉ chấp nhận file PDF cho Calibration Certificate')
    return
  }
  if (file.size > MAX_SIZE_MB * 1024 * 1024) {
    toast.error(`File quá lớn. Tối đa ${MAX_SIZE_MB}MB`)
    return
  }
  // Upload to Frappe file manager
  const fileDoc = await uploadFile(file)
  emit('uploaded', fileDoc.file_url)
  // Hiển thị PDF preview inline (iframe)
  pdfUrl.value = fileDoc.file_url
}
```

### 5.4 Calibration Status Badge Color Mapping

```typescript
const STATUS_CONFIG: Record<string, { label: string; variant: string; icon: string }> = {
  'Scheduled':             { label: 'Đã lên lịch',       variant: 'blue',   icon: '📅' },
  'Sent to Lab':           { label: 'Đang tại Lab',       variant: 'purple', icon: '🚚' },
  'In Progress':           { label: 'Đang thực hiện',     variant: 'yellow', icon: '⚙️' },
  'Certificate Received':  { label: 'Nhận chứng chỉ',     variant: 'teal',   icon: '📄' },
  'Passed':                { label: 'Đạt',                variant: 'green',  icon: '✅' },
  'Failed':                { label: 'Không đạt',          variant: 'red',    icon: '❌' },
  'Conditionally Passed':  { label: 'Đạt có điều kiện',   variant: 'orange', icon: '⚠️' },
  'Cancelled':             { label: 'Đã hủy',             variant: 'gray',   icon: '🚫' },
  'On Hold':               { label: 'Tạm dừng',           variant: 'gray',   icon: '⏸️' },
}
```

### 5.5 Dynamic Form — Conditional Fields

```typescript
// Computed visibility dựa trên calibration_type
const showLabFields = computed(() => form.calibration_type === 'External')
const showInHouseFields = computed(() => form.calibration_type === 'In-House')
const showCertificateUpload = computed(() => form.calibration_type === 'External' && form.status === 'Certificate Received')

// Auto-populate device_model khi chọn asset
watch(() => form.asset_ref, async (newAsset) => {
  if (newAsset) {
    const assetData = await fetchAssetInfo(newAsset)
    form.device_model = assetData.device_model
    form.calibration_interval_days = assetData.custom_calibration_interval_days
    form.due_date = assetData.custom_next_calibration_date
  }
})
```

---

## 6. Responsive & Accessibility

- **Mobile-first**: MeasurementTable trên mobile dùng card view thay cho table (màn hình < 768px)
- **WCAG 2.1 AA**: All form fields có `aria-label`, error messages liên kết với `aria-describedby`
- **Tolerance indicator**: Không chỉ dùng màu — kết hợp icon + text để hỗ trợ color-blind users
- **Keyboard navigation**: Tab order logic, Enter để confirm submit dialog
- **Loading states**: Skeleton loader khi fetch data, spinner trên buttons khi submit
