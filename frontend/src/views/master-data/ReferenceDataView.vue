<script setup lang="ts">
import { useToast } from '@/composables/useToast'
import { ref, computed, onMounted, watch } from 'vue'
import {
  listLocations, getLocation, createLocation, updateLocation, deleteLocation,
  listDepartments, getDepartment, createDepartment, updateDepartment, deleteDepartment,
  listAssetCategories, getAssetCategory, createAssetCategory, updateAssetCategory, deleteAssetCategory,
  bulkRegenerateScheduleByCategory,
  type BulkRegenerateResult,
} from '@/api/imm00'
import BaseModal from '@/components/common/BaseModal.vue'
import {
  previewRefImport, importRefData, buildErrorReport,
  getExportUrl, getTemplateUrl, initImportFolders,
} from '@/api/importData'
import type { AcLocation, AcDepartment, AcAssetCategory } from '@/types/imm00'
import type { ImportPreviewResult, ImportResult, ImportStep, ImportMode, RefDataDoctype } from '@/types/import'
import { translateDepreciationMethod } from '@/utils/formatters'
import api from '@/api/axios'
import SmartSelect from '@/components/common/SmartSelect.vue'
const toast = useToast()

type Tab = 'location' | 'department' | 'category'
type FormData = Record<string, string | number | null | undefined>

const tab = ref<Tab>('location')
const locations = ref<AcLocation[]>([])
const departments = ref<AcDepartment[]>([])
const categories = ref<AcAssetCategory[]>([])
const loading = ref(false)
const loadError = ref('')
let loadSeq = 0

const showForm = ref(false)
const editingName = ref<string | null>(null)
const form = ref<FormData>({})
const err = ref('')

async function load() {
  const seq = ++loadSeq
  loading.value = true
  loadError.value = ''
  try {
    if (tab.value === 'location') {
      const r = await listLocations()
      if (seq === loadSeq) locations.value = r
    } else if (tab.value === 'department') {
      const r = await listDepartments()
      if (seq === loadSeq) departments.value = r
    } else {
      const r = await listAssetCategories()
      if (seq === loadSeq) categories.value = r
    }
  } catch (e: unknown) {
    if (seq === loadSeq) loadError.value = e instanceof Error ? e.message : 'Lỗi tải dữ liệu'
  } finally {
    if (seq === loadSeq) loading.value = false
  }
}

function openCreate() {
  editingName.value = null
  phoneFetchState.value = 'idle'
  skipPhoneFetch = true
  form.value = tab.value === 'location'
    ? { location_name: '', location_code: '', parent_location: '', is_group: 0,
        clinical_area_type: '', infection_control_level: '',
        power_backup_available: 0,
        dept_head: '', contact_phone: '', notes: '' }
    : tab.value === 'department'
    ? { department_name: '', department_code: '', parent_department: '', is_group: 0,
        dept_head: '', phone: '', email: '', is_active: 1 }
    : { category_name: '', category_code: '', description: '',
        gmdn_code: '', gmdn_term: '',
        default_pm_required: 1, default_pm_interval_days: 180,
        default_calibration_required: 0, default_calibration_interval_days: 365,
        default_depreciation_method: 'Straight Line',
        total_depreciation_months: 60,
        depreciation_frequency: 'Monthly',
        default_residual_value_pct: 0,
        has_radiation: 0, is_active: 1 }
  err.value = ''; showForm.value = true
  // Mở khoá auto-fetch sau khi form đã set xong
  setTimeout(() => { skipPhoneFetch = false }, 0)
}

function normChecks(doc: Record<string, unknown>, fields: string[]): FormData {
  const d = { ...doc } as FormData
  for (const f of fields) d[f] = d[f] ? 1 : 0
  return d
}

// Trạng thái fetch mobile_no → hiển thị hint trong modal
const phoneFetchState = ref<'idle' | 'loading' | 'found' | 'empty'>('idle')
// Flag chặn auto-fetch khi đang load dữ liệu edit (tránh ghi đè contact_phone đã lưu trong DB)
let skipPhoneFetch = false

async function fetchUserMobile(userEmail: string): Promise<string> {
  const res = await api.get<{ message: { phone?: string; mobile_no?: string } | null }>(
    '/api/method/frappe.client.get_value',
    {
      params: {
        doctype: 'User',
        filters: JSON.stringify({ name: userEmail }),
        fieldname: JSON.stringify(['phone', 'mobile_no']),
      },
    },
  )
  // Ưu tiên phone, fallback mobile_no nếu phone trống
  const m = res.data?.message
  return m?.phone || m?.mobile_no || ''
}

// Khi đổi người phụ trách → tự fetch mobile_no, ghi đè contact_phone.
// Chỉ chạy ở tab location, khi modal mở, không phải đang load edit data.
watch(() => form.value.dept_head, async (newUser) => {
  if (tab.value !== 'location' || !showForm.value) return
  if (skipPhoneFetch) return
  if (!newUser) {
    phoneFetchState.value = 'idle'
    form.value.contact_phone = ''
    return
  }
  phoneFetchState.value = 'loading'
  try {
    const mobile = await fetchUserMobile(newUser as string)
    if (mobile) {
      form.value.contact_phone = mobile
      phoneFetchState.value = 'found'
    } else {
      form.value.contact_phone = ''
      phoneFetchState.value = 'empty'
    }
  } catch {
    phoneFetchState.value = 'empty'
  }
})

async function openEdit(row: Record<string, unknown>) {
  const name = row.name as string
  editingName.value = name
  err.value = ''
  phoneFetchState.value = 'idle'
  skipPhoneFetch = true
  try {
    let doc: Record<string, unknown>
    if (tab.value === 'location') {
      doc = await getLocation(name) as unknown as Record<string, unknown>
      form.value = normChecks(doc, ['is_group', 'power_backup_available'])
    } else if (tab.value === 'department') {
      doc = await getDepartment(name) as unknown as Record<string, unknown>
      form.value = normChecks(doc, ['is_group', 'is_active'])
    } else {
      doc = await getAssetCategory(name) as unknown as Record<string, unknown>
      form.value = normChecks(doc, ['default_pm_required', 'default_calibration_required', 'has_radiation', 'is_active'])
    }
  } catch {
    form.value = { ...row } as FormData
  }
  showForm.value = true
  // Mở khoá auto-fetch sau khi modal hiển thị + form đã sync vào DOM
  await new Promise(r => setTimeout(r, 0))
  skipPhoneFetch = false
}

async function save() {
  err.value = ''
  try {
    if (tab.value === 'location') {
      if (editingName.value) await updateLocation(editingName.value, form.value as Partial<AcLocation>)
      else await createLocation(form.value as Partial<AcLocation>)
    } else if (tab.value === 'department') {
      if (editingName.value) await updateDepartment(editingName.value, form.value as Partial<AcDepartment>)
      else await createDepartment(form.value as Partial<AcDepartment>)
    } else {
      if (editingName.value) await updateAssetCategory(editingName.value, form.value as Partial<AcAssetCategory>)
      else await createAssetCategory(form.value as Partial<AcAssetCategory>)
    }
    showForm.value = false
    await load()
  } catch (e: unknown) { err.value = e instanceof Error ? e.message : 'Lỗi lưu' }
}

// Áp dụng luật khấu hao của Danh mục cho tất cả tài sản — KHÔNG dùng window.confirm
// (skill rule WAVE2 pattern): mở BaseModal xác nhận, chỉ khi xác nhận mới gọi API.
const applyConfirmOpen = ref(false)
const applyRunning = ref(false)
const applyResult = ref<BulkRegenerateResult | null>(null)

function openApplyConfirm() {
  if (!editingName.value) return
  applyConfirmOpen.value = true
}

async function confirmApplyToExistingAssets() {
  if (!editingName.value) return
  applyConfirmOpen.value = false
  applyRunning.value = true
  try {
    const res = await bulkRegenerateScheduleByCategory(editingName.value)
    applyResult.value = res
    toast.success(
      `Kế thừa luật ${res.inherited} TS · Sinh lịch ${res.regenerated} TS · ` +
      `Giữ lịch sử ${res.skipped_has_history} · Thiếu luật ${res.skipped_no_rule}` +
      (res.errors ? ` · Lỗi ${res.errors}` : ''),
    )
  } catch (e: unknown) {
    err.value = e instanceof Error ? e.message : 'Lỗi áp dụng'
    toast.error(err.value)
  } finally {
    applyRunning.value = false
  }
}

function closeApplyResult() {
  applyResult.value = null
}

async function remove(name: string) {
  if (!confirm(`Xóa "${name}"?`)) return
  try {
    if (tab.value === 'location') await deleteLocation(name)
    else if (tab.value === 'department') await deleteDepartment(name)
    else await deleteAssetCategory(name)
    await load()
  } catch (e: unknown) { toast.error(e instanceof Error ? e.message : 'Lỗi xóa — có thể đang được tham chiếu') }
}


const currentRows = computed(() =>
  tab.value === 'location' ? locations.value
  : tab.value === 'department' ? departments.value
  : categories.value,
)

const tabLabel = computed(() =>
  tab.value === 'location' ? 'Vị trí' : tab.value === 'department' ? 'Khoa/Phòng' : 'Danh mục tài sản',
)

function switchTab(t: Tab) { tab.value = t; showForm.value = false; load() }
onMounted(load)

// ── Import / Export ──────────────────────────────────────────────────────────

const showImport = ref(false)
const importStep = ref<ImportStep>('upload')
const uploading = ref(false)
const importLoading = ref(false)
const uploadedFileUrl = ref('')
const uploadedFileName = ref('')
const importFolder = ref('Home/Attachments')
const previewData = ref<ImportPreviewResult | null>(null)
const importResult = ref<ImportResult | null>(null)
const importErr = ref('')
const isDragOver = ref(false)
const importMode = ref<ImportMode>('strict')

function currentDoctype(): RefDataDoctype {
  if (tab.value === 'location') return 'AC Location'
  if (tab.value === 'department') return 'AC Department'
  return 'AC Asset Category'
}

async function openImport() {
  showImport.value = true
  importStep.value = 'upload'
  uploadedFileUrl.value = ''
  uploadedFileName.value = ''
  previewData.value = null
  importResult.value = null
  importErr.value = ''
  importMode.value = 'strict'
  try {
    importFolder.value = await initImportFolders(currentDoctype())
  } catch {
    importFolder.value = 'Home/Attachments'
  }
}

function closeImport() {
  showImport.value = false
  if (importStep.value === 'result' && (importResult.value?.success ?? 0) > 0) load()
}

async function handleFileChange(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (file) await _uploadAndPreview(file)
}

async function handleDrop(event: DragEvent) {
  isDragOver.value = false
  const file = event.dataTransfer?.files?.[0]
  if (file) await _uploadAndPreview(file)
}

async function _uploadAndPreview(file: File) {
  uploading.value = true
  importErr.value = ''
  try {
    const fd = new FormData()
    fd.append('file', file)
    fd.append('is_private', '1')
    fd.append('folder', importFolder.value)
    const res = await api.post<{ message: { file_url: string } }>(
      '/api/method/upload_file', fd,
      { headers: { 'Content-Type': undefined as unknown as string } },
    )
    uploadedFileUrl.value = res.data.message.file_url
    uploadedFileName.value = file.name
    await runPreview()
  } catch (e: unknown) {
    importErr.value = e instanceof Error ? e.message : 'Lỗi upload file'
  } finally {
    uploading.value = false
  }
}

async function runPreview() {
  importLoading.value = true
  importErr.value = ''
  try {
    previewData.value = await previewRefImport(currentDoctype(), uploadedFileUrl.value)
    importStep.value = 'preview'
  } catch (e: unknown) {
    importErr.value = e instanceof Error ? e.message : 'Lỗi đọc file'
  } finally {
    importLoading.value = false
  }
}

async function runImport() {
  importLoading.value = true
  importErr.value = ''
  try {
    importResult.value = await importRefData(
      currentDoctype(), uploadedFileUrl.value, importMode.value,
    )
    importStep.value = 'result'
  } catch (e: unknown) {
    importErr.value = e instanceof Error ? e.message : 'Lỗi import'
  } finally {
    importLoading.value = false
  }
}

async function downloadErrorReport() {
  try {
    const r = await buildErrorReport(currentDoctype(), uploadedFileUrl.value)
    globalThis.open(r.fileUrl, '_blank')
  } catch {
    toast.error('Không tạo được báo cáo lỗi')
  }
}

function doExport() { globalThis.location.href = getExportUrl(currentDoctype()) }
function doDownloadTemplate() { globalThis.location.href = getTemplateUrl(currentDoctype()) }

const hasBlockingErrors = computed(
  () => (previewData.value?.errors ?? []).some(e => e.severity === 'error'),
)

const totalSkip = computed(() => {
  const p = previewData.value
  if (!p) return 0
  return p.errors.length + (p.cascadeCount ?? 0)
})

const skipRatio = computed(() => {
  const p = previewData.value
  if (!p || p.totalRows === 0) return 0
  return totalSkip.value / p.totalRows
})

const allRowsInvalid = computed(
  () => previewData.value !== null && totalSkip.value >= previewData.value.totalRows,
)

const canImport = computed(() => {
  if (!previewData.value || importLoading.value) return false
  if (allRowsInvalid.value) return false
  if (!hasBlockingErrors.value) return true
  return importMode.value === 'skip_invalid'
})
</script>

<template>
  <div class="page-container animate-fade-in space-y-5">
    <div class="flex items-center justify-between">
      <h1 class="text-xl font-semibold text-gray-800">Dữ liệu tham chiếu</h1>
      <div class="flex items-center gap-2">
        <button
          class="px-3 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 text-gray-600 flex items-center gap-1.5"
          title="Tải dữ liệu hiện tại về Excel"
          @click="doExport"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
          Xuất Excel
        </button>
        <button
          class="px-3 py-2 text-sm border border-emerald-300 rounded-lg hover:bg-emerald-50 text-emerald-700 flex items-center gap-1.5"
          @click="openImport"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
          </svg>
          Import
        </button>
        <button class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium" @click="openCreate">
          + Thêm {{ tabLabel }}
        </button>
      </div>
    </div>

    <div class="border-b border-gray-200 flex gap-1">
      <button
v-for="t in (['location','department','category'] as Tab[])" :key="t"
        :class="['px-4 py-2 text-sm font-medium border-b-2 -mb-px',
          tab === t ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700']"
        @click="switchTab(t)">
        {{ t === 'location' ? 'Vị trí' : t === 'department' ? 'Khoa/Phòng' : 'Danh mục tài sản' }}
      </button>
    </div>

    <div class="bg-white rounded-xl border border-gray-200 overflow-x-auto">
      <div v-if="loading" class="text-center text-gray-400 py-12">Đang tải...</div>
      <div v-else-if="loadError" class="text-center text-red-500 py-12 text-sm">{{ loadError }}</div>
      <div v-else-if="currentRows.length === 0" class="text-center text-gray-400 py-12 text-sm">Không có dữ liệu.</div>
      <table v-else class="w-full text-sm">
        <thead class="bg-gray-50 border-b border-gray-200">
          <tr v-if="tab === 'location'">
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Mã</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Tên vị trí</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Khu vực lâm sàng</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Vị trí cha</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Is Group</th>
            <th class="px-4 py-3 text-right"></th>
          </tr>
          <tr v-else-if="tab === 'department'">
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Mã</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Tên khoa</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Khoa cha</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Trưởng khoa</th>
            <th class="px-4 py-3 text-right"></th>
          </tr>
          <tr v-else>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Mã danh mục</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Tên danh mục</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">GMDN Code</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Phương pháp KH</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Số tháng KH</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Bảo trì (ngày)</th>
            <th class="px-4 py-3 text-right"></th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
          <tr v-for="r in (currentRows as Record<string, unknown>[])" :key="r.name as string" class="hover:bg-gray-50">
            <td class="px-4 py-3 font-mono text-xs text-gray-500">
              {{ tab === 'category' ? (r.category_code || r.name) : r.name }}
            </td>
            <template v-if="tab === 'location'">
              <td class="px-4 py-3 font-medium text-gray-800">{{ r.location_name }}</td>
              <td class="px-4 py-3 text-gray-500">{{ r.clinical_area_type || '—' }}</td>
              <td class="px-4 py-3 text-gray-500">{{ r.parent_location || '—' }}</td>
              <td class="px-4 py-3">
                <span :class="r.is_group ? 'text-green-600' : 'text-gray-400'">{{ r.is_group ? '✓' : '—' }}</span>
              </td>
            </template>
            <template v-else-if="tab === 'department'">
              <td class="px-4 py-3 font-medium text-gray-800">{{ r.department_name }}</td>
              <td class="px-4 py-3 text-gray-500">{{ r.parent_department || '—' }}</td>
              <td class="px-4 py-3 text-gray-500">{{ r.dept_head || '—' }}</td>
            </template>
            <template v-else>
              <td class="px-4 py-3 font-medium text-gray-800">{{ r.category_name }}</td>
              <td class="px-4 py-3">
                <span v-if="r.gmdn_code" class="inline-flex items-center gap-1">
                  <span class="font-mono text-xs font-semibold text-blue-700 bg-blue-50 border border-blue-200 px-1.5 py-0.5 rounded">{{ r.gmdn_code }}</span>
                  <span v-if="r.gmdn_term" class="text-xs text-gray-500 truncate max-w-[120px]" :title="r.gmdn_term as string">{{ r.gmdn_term }}</span>
                </span>
                <span v-else class="text-gray-400">—</span>
              </td>
              <td class="px-4 py-3 text-gray-600 text-xs">{{ translateDepreciationMethod(r.default_depreciation_method as string) }}</td>
              <td class="px-4 py-3 text-gray-500">
                <span v-if="r.total_depreciation_months">
                  {{ r.total_depreciation_months }} tháng
                  <span class="text-gray-400">({{ (Number(r.total_depreciation_months) / 12).toFixed(1) }}y)</span>
                </span>
                <span v-else>—</span>
              </td>
              <td class="px-4 py-3 text-gray-500">{{ r.default_pm_required ? (r.default_pm_interval_days || '—') : '—' }}</td>
            </template>
            <td class="px-4 py-3 text-right space-x-2">
              <button class="text-blue-600 hover:text-blue-800 text-xs font-medium" @click="openEdit(r)">Sửa</button>
              <button class="text-red-600 hover:text-red-800 text-xs font-medium" @click="remove(r.name as string)">Xóa</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Modal Form -->
    <div v-if="showForm" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4" @click.self="showForm = false">
      <div class="bg-white rounded-xl p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto space-y-4">
        <h2 class="text-lg font-semibold">{{ editingName ? 'Sửa' : 'Thêm' }} {{ tabLabel }}</h2>
        <div v-if="err" class="bg-red-50 text-red-700 text-sm p-3 rounded">{{ err }}</div>

        <div v-if="tab === 'location'" class="space-y-3">
          <div class="grid grid-cols-2 gap-3">
            <div class="col-span-2">
              <label class="block text-sm font-medium text-gray-700 mb-1">Tên vị trí <span class="text-red-500">*</span></label>
              <input v-model="form.location_name" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">
                Mã vị trí
                <span v-if="!editingName" class="text-xs text-gray-400 font-normal">(để trống → tự sinh)</span>
                <span v-else class="text-xs text-gray-400 font-normal">(không đổi sau khi tạo)</span>
              </label>
              <input
                v-model="form.location_code"
                :disabled="!!editingName"
                :placeholder="editingName ? '' : 'VD: ICU-3F (tùy chọn)'"
                class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm disabled:bg-gray-100 disabled:text-gray-500 disabled:cursor-not-allowed"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Vị trí cha</label>
              <SmartSelect
                v-model="form.parent_location as string"
                doctype="AC Location"
                :filters="{ is_group: 1 }"
                placeholder="Chọn vị trí cha (chỉ nhóm)..."
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Khu vực lâm sàng</label>
              <select v-model="form.clinical_area_type" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
                <option value="">— Chọn —</option>
                <option value="ICU">ICU</option>
                <option value="OR">Phòng mổ (OR)</option>
                <option value="Lab">Xét nghiệm (Lab)</option>
                <option value="Imaging">Chẩn đoán hình ảnh</option>
                <option value="General Ward">Khoa thường</option>
                <option value="Storage">Kho</option>
                <option value="Office">Văn phòng</option>
              </select>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Mức kiểm soát nhiễm khuẩn</label>
              <select v-model="form.infection_control_level" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
                <option value="">— Chọn —</option>
                <option value="Standard">Chuẩn</option>
                <option value="Enhanced">Tăng cường</option>
                <option value="Isolation">Cách ly</option>
              </select>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Người phụ trách</label>
              <SmartSelect
                v-model="form.dept_head as string"
                doctype="User"
                placeholder="Chọn người dùng..."
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">
                Số liên hệ
                <span v-if="phoneFetchState === 'loading'" class="ml-1 text-[10px] font-normal text-blue-500">(đang lấy số...)</span>
                <span v-else-if="phoneFetchState === 'found'" class="ml-1 text-[10px] font-normal text-green-600">(đã lấy từ người phụ trách)</span>
                <span v-else-if="phoneFetchState === 'empty'" class="ml-1 text-[10px] font-normal text-amber-600">(người phụ trách chưa có số — nhập tay)</span>
              </label>
              <input
                v-model="form.contact_phone"
                placeholder="Tự điền từ mobile_no, có thể sửa"
                class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
              />
            </div>
            <div class="col-span-2">
              <label class="block text-sm font-medium text-gray-700 mb-1">Ghi chú</label>
              <textarea v-model="form.notes" rows="2" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"></textarea>
            </div>
          </div>
          <label class="flex items-center gap-2 text-sm">
            <input v-model="form.power_backup_available" type="checkbox" :true-value="1" :false-value="0" /> Có nguồn điện dự phòng
          </label>
          <label class="flex items-center gap-2 text-sm">
            <input v-model="form.is_group" type="checkbox" :true-value="1" :false-value="0" /> Là nhóm (tree group)
          </label>
        </div>

        <div v-else-if="tab === 'department'" class="space-y-3">
          <div class="grid grid-cols-2 gap-3">
            <div class="col-span-2">
              <label class="block text-sm font-medium text-gray-700 mb-1">Tên khoa/phòng <span class="text-red-500">*</span></label>
              <input v-model="form.department_name" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">
                Mã khoa
                <span v-if="!editingName" class="text-xs text-gray-400 font-normal">(để trống → tự sinh)</span>
                <span v-else class="text-xs text-gray-400 font-normal">(không đổi sau khi tạo)</span>
              </label>
              <input
                v-model="form.department_code"
                :disabled="!!editingName"
                :placeholder="editingName ? '' : 'VD: HSCC (tùy chọn)'"
                class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm disabled:bg-gray-100 disabled:text-gray-500 disabled:cursor-not-allowed"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Khoa cha</label>
              <SmartSelect
                v-model="form.parent_department as string"
                doctype="AC Department"
                :filters="{ is_group: 1 }"
                placeholder="Chọn khoa cha (chỉ nhóm)..."
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Trưởng khoa</label>
              <SmartSelect v-model="form.dept_head as string" doctype="User" placeholder="Chọn người dùng..." />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Điện thoại</label>
              <input v-model="form.phone" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            </div>
            <div class="col-span-2">
              <label class="block text-sm font-medium text-gray-700 mb-1">Email</label>
              <input v-model="form.email" type="email" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            </div>
          </div>
          <label class="flex items-center gap-2 text-sm">
            <input v-model="form.is_group" type="checkbox" :true-value="1" :false-value="0" /> Là nhóm (tree group)
          </label>
          <label class="flex items-center gap-2 text-sm">
            <input v-model="form.is_active" type="checkbox" :true-value="1" :false-value="0" /> Đang hoạt động
          </label>
        </div>

        <div v-else class="space-y-4">
          <!-- Thông tin cơ bản -->
          <div class="grid grid-cols-2 gap-3">
            <div class="col-span-2">
              <label class="block text-sm font-medium text-gray-700 mb-1">Tên danh mục <span class="text-red-500">*</span></label>
              <input v-model="form.category_name" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">
                Mã danh mục
                <span v-if="!editingName" class="text-xs text-gray-400 font-normal">(để trống → tự sinh)</span>
                <span v-else class="text-xs text-gray-400 font-normal">(không đổi sau khi tạo)</span>
              </label>
              <input
                v-model="form.category_code"
                :disabled="!!editingName"
                :placeholder="editingName ? '' : 'VD: Thiet-bi-Chuyen-dung (tùy chọn)'"
                class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono disabled:bg-gray-100 disabled:text-gray-500 disabled:cursor-not-allowed"
              />
              <p v-if="!editingName" class="text-[10px] text-gray-400 mt-1">Chỉ dùng chữ cái, số, dấu . _ -</p>
            </div>
            <div class="col-span-2">
              <label class="block text-sm font-medium text-gray-700 mb-1">Mô tả</label>
              <textarea v-model="form.description" rows="2" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"></textarea>
            </div>
          </div>

          <!-- GMDN -->
          <div class="pt-3 border-t border-gray-200">
            <p class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
              Mã GMDN
              <span class="text-[10px] font-normal text-blue-500 ml-1">(nguồn kế thừa → Model thiết bị → Tài sản)</span>
            </p>
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="block text-xs text-gray-600 mb-1">GMDN Code</label>
                <input
                  v-model="form.gmdn_code"
                  placeholder="VD: 35943"
                  class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono"
                />
                <p class="text-[10px] text-gray-400 mt-1">5–6 chữ số theo chuẩn GMDN</p>
              </div>
              <div>
                <label class="block text-xs text-gray-600 mb-1">GMDN Term (tên danh mục)</label>
                <input
                  v-model="form.gmdn_term"
                  placeholder="VD: Infusion pump, general-purpose"
                  class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                />
                <p class="text-[10px] text-gray-400 mt-1">Tên thuật ngữ GMDN quốc tế</p>
              </div>
            </div>
          </div>

          <!-- PM / Hiệu chuẩn -->
          <div class="pt-3 border-t border-gray-200">
            <p class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">PM & Hiệu chuẩn mặc định</p>
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="flex items-center gap-2 text-sm mb-2">
                  <input v-model="form.default_pm_required" type="checkbox" :true-value="1" :false-value="0" /> Mặc định yêu cầu PM
                </label>
                <input
                  v-model.number="form.default_pm_interval_days" type="number" min="0"
                  :disabled="form.default_pm_required !== 1"
                  placeholder="Chu kỳ PM (ngày)"
                  class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm disabled:bg-gray-100 disabled:text-gray-400 disabled:cursor-not-allowed"
                />
              </div>
              <div>
                <label class="flex items-center gap-2 text-sm mb-2">
                  <input v-model="form.default_calibration_required" type="checkbox" :true-value="1" :false-value="0" /> Mặc định yêu cầu hiệu chuẩn
                </label>
                <input
                  v-model.number="form.default_calibration_interval_days" type="number" min="0"
                  :disabled="form.default_calibration_required !== 1"
                  placeholder="Chu kỳ hiệu chuẩn (ngày)"
                  class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm disabled:bg-gray-100 disabled:text-gray-400 disabled:cursor-not-allowed"
                />
              </div>
            </div>
          </div>

          <!-- Khấu hao -->
          <div class="pt-3 border-t border-gray-200">
            <p class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
              Luật khấu hao <span class="text-[10px] font-normal text-gray-400">(áp dụng cho mọi Asset thuộc danh mục)</span>
            </p>
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="block text-xs text-gray-600 mb-1">Phương pháp khấu hao</label>
                <!-- GIỮ NGUYÊN value=EN: đây là form input ghi DB, value PHẢI khớp option BE
                     (Straight Line / Double Declining / Units of Production). Nhãn hiển thị đã
                     song ngữ. Chỉ phần read-only (cột bảng dòng ~465) mới qua translateDepreciationMethod. -->
                <select v-model="form.default_depreciation_method" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
                  <option value="">—</option>
                  <option value="Straight Line">Đường thẳng (Straight Line)</option>
                  <option value="Double Declining">Số dư giảm dần (Double Declining)</option>
                  <option value="Units of Production">Theo sản lượng (Units of Production)</option>
                </select>
              </div>
              <div>
                <label class="block text-xs text-gray-600 mb-1">Tần suất khấu hao</label>
                <select v-model="form.depreciation_frequency" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
                  <option value="Monthly">Hàng tháng</option>
                  <option value="Quarterly">Hàng quý</option>
                  <option value="Yearly">Hàng năm</option>
                </select>
              </div>
              <div>
                <label class="block text-xs text-gray-600 mb-1">Tổng số tháng khấu hao</label>
                <input
                  v-model.number="form.total_depreciation_months" type="number" min="0" step="1"
                  placeholder="VD: 120 cho thiết bị y tế"
                  class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                />
                <p v-if="form.total_depreciation_months" class="text-[10px] text-gray-500 mt-1">
                  ≈ {{ (Number(form.total_depreciation_months) / 12).toFixed(1) }} năm
                </p>
              </div>
              <div>
                <label class="block text-xs text-gray-600 mb-1">Giá trị thu hồi (%)</label>
                <input
                  v-model.number="form.default_residual_value_pct" type="number" min="0" max="100" step="0.5"
                  placeholder="Thường là 0 hoặc 5"
                  class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                />
                <p class="text-[10px] text-gray-500 mt-1">% giá trị còn lại khi hết vòng đời</p>
              </div>
            </div>
          </div>

          <!-- Cờ quy định -->
          <div class="pt-3 border-t border-gray-200 flex gap-6">
            <label class="flex items-center gap-2 text-sm">
              <input v-model="form.has_radiation" type="checkbox" :true-value="1" :false-value="0" /> Chứa nguồn bức xạ
            </label>
            <label class="flex items-center gap-2 text-sm">
              <input v-model="form.is_active" type="checkbox" :true-value="1" :false-value="0" /> Đang hoạt động
            </label>
          </div>
        </div>

        <div v-if="tab === 'category' && editingName" class="pt-2">
          <button
            data-testid="apply-depr-btn"
            class="w-full text-xs px-3 py-2 rounded-lg border border-indigo-200 bg-indigo-50 text-indigo-700 hover:bg-indigo-100 transition-colors disabled:opacity-60"
            :disabled="applyRunning"
            @click="openApplyConfirm"
          >
            🔄 {{ applyRunning ? 'Đang áp dụng…' : 'Áp dụng luật khấu hao này cho tất cả tài sản thuộc danh mục' }}
          </button>
          <p class="text-[10px] text-gray-500 mt-1 text-center">
            Chỉ regenerate với tài sản chưa có kỳ nào đã chạy (bảo vệ lịch sử khấu hao)
          </p>
        </div>

        <div class="flex justify-end gap-2 pt-2">
          <button class="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50" @click="showForm = false">Hủy</button>
          <button class="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700" @click="save">Lưu</button>
        </div>
      </div>
    </div>

    <!-- ── Import Modal ──────────────────────────────────────────────────── -->
    <div
      v-if="showImport"
      class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4"
      @click.self="closeImport"
    >
      <div class="bg-white rounded-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <!-- Header -->
        <div class="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <div>
            <h2 class="text-base font-semibold text-gray-800">Import {{ tabLabel }}</h2>
            <p class="text-xs text-gray-500 mt-0.5">
              {{ importStep === 'upload' ? 'Tải file Excel / CSV lên' : importStep === 'preview' ? 'Kiểm tra dữ liệu trước khi import' : 'Kết quả import' }}
            </p>
          </div>
          <button class="text-gray-400 hover:text-gray-600 p-1" @click="closeImport">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <!-- Step indicator -->
        <div class="flex gap-0 border-b border-gray-100">
          <div v-for="(label, idx) in ['1. Upload', '2. Kiểm tra', '3. Kết quả']" :key="idx"
            :class="['flex-1 text-center py-2 text-xs font-medium',
              (importStep === 'upload' && idx === 0) || (importStep === 'preview' && idx === 1) || (importStep === 'result' && idx === 2)
                ? 'text-blue-600 border-b-2 border-blue-600 -mb-px'
                : 'text-gray-400']">
            {{ label }}
          </div>
        </div>

        <div class="p-6 space-y-4">
          <!-- Error banner -->
          <div v-if="importErr" class="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-lg">
            {{ importErr }}
          </div>

          <!-- STEP 1: UPLOAD ─────────────────────────────────────────────── -->
          <template v-if="importStep === 'upload'">
            <div class="flex items-center justify-between">
              <p class="text-sm text-gray-600">
                Tải template, điền dữ liệu rồi upload lại:
              </p>
              <button class="text-xs text-blue-600 hover:underline flex items-center gap-1" @click="doDownloadTemplate">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                    d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                Tải template Excel
              </button>
            </div>

            <!-- Drop zone -->
            <label
              :class="['block border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-colors',
                isDragOver ? 'border-blue-400 bg-blue-50' : 'border-gray-300 hover:border-gray-400 hover:bg-gray-50']"
              @dragover.prevent="isDragOver = true"
              @dragleave.prevent="isDragOver = false"
              @drop.prevent="handleDrop"
            >
              <input type="file" class="hidden" accept=".xlsx,.xls,.csv" @change="handleFileChange" />
              <div v-if="uploading || importLoading" class="text-gray-500 text-sm">
                <div class="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
                {{ uploading ? 'Đang tải file...' : 'Đang đọc dữ liệu...' }}
              </div>
              <div v-else>
                <svg class="w-10 h-10 text-gray-300 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                    d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
                <p class="text-sm text-gray-600 font-medium">Kéo thả file vào đây hoặc click để chọn</p>
                <p class="text-xs text-gray-400 mt-1">Chấp nhận .xlsx, .xls, .csv</p>
              </div>
            </label>
          </template>

          <!-- STEP 2: PREVIEW ────────────────────────────────────────────── -->
          <template v-else-if="importStep === 'preview' && previewData">
            <!-- Summary bar -->
            <div class="flex items-center gap-4 text-sm">
              <span class="text-gray-600">Tổng: <strong>{{ previewData.totalRows }}</strong> dòng</span>
              <span class="text-green-700">Hợp lệ: <strong>{{ previewData.validRows }}</strong></span>
              <span v-if="previewData.errors.length" class="text-red-600">
                Lỗi: <strong>{{ previewData.errors.length }}</strong>
              </span>
              <span v-if="previewData.warnings.length" class="text-amber-600">
                Cảnh báo: <strong>{{ previewData.warnings.length }}</strong>
              </span>
              <span class="text-xs text-gray-400">{{ uploadedFileName }}</span>
            </div>

            <!-- Error list -->
            <div v-if="previewData.errors.length || previewData.warnings.length" class="space-y-1 max-h-48 overflow-y-auto">
              <div
                v-for="(issue, i) in [...previewData.errors, ...previewData.warnings].slice(0, 50)"
                :key="i"
                :class="['flex gap-3 text-xs px-3 py-2 rounded-lg',
                  issue.severity === 'error' ? 'bg-red-50 text-red-700' : 'bg-amber-50 text-amber-700']"
              >
                <span class="font-bold shrink-0">Dòng {{ issue.row }}</span>
                <span class="font-medium shrink-0">{{ issue.field || '—' }}</span>
                <span>{{ issue.message }}</span>
              </div>
              <p v-if="previewData.errors.length + previewData.warnings.length > 50"
                class="text-xs text-gray-400 text-center pt-1">
                Chỉ hiển thị 50 vấn đề đầu tiên — tải báo cáo để xem đầy đủ.
              </p>
            </div>
            <div v-else class="bg-green-50 text-green-700 text-sm px-4 py-3 rounded-lg flex items-center gap-2">
              <svg class="w-4 h-4 shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
              </svg>
              Dữ liệu hợp lệ, sẵn sàng import.
            </div>

            <!-- Preview table -->
            <div v-if="previewData.preview.length" class="border border-gray-200 rounded-lg overflow-x-auto">
              <p class="text-xs text-gray-500 px-3 pt-2 pb-1 font-medium">Xem trước 10 dòng đầu:</p>
              <table class="w-full text-xs">
                <thead class="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th v-for="fn in previewData.fieldnames.slice(0, 6)" :key="fn"
                      class="px-3 py-2 text-left font-medium text-gray-500 whitespace-nowrap">
                      {{ fn }}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(row, ri) in previewData.preview" :key="ri"
                    class="border-t border-gray-100 hover:bg-gray-50">
                    <td v-for="fn in previewData.fieldnames.slice(0, 6)" :key="fn"
                      class="px-3 py-1.5 text-gray-700 max-w-[120px] truncate" :title="String(row[fn] ?? '')">
                      {{ row[fn] ?? '—' }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <!-- Skip-Invalid mode picker (only when there are blocking errors) -->
            <div
              v-if="hasBlockingErrors && !allRowsInvalid"
              class="rounded-lg border border-amber-200 bg-amber-50 p-4 space-y-3"
            >
              <p class="text-sm font-medium text-amber-900">
                File có {{ previewData.errors.length }} dòng lỗi
                <span v-if="previewData.cascadeCount">
                  + {{ previewData.cascadeCount }} dòng phụ thuộc (cha bị bỏ qua)
                </span>
                — chọn cách xử lý:
              </p>
              <fieldset class="space-y-2">
                <label class="flex items-start gap-2 cursor-pointer">
                  <input type="radio" v-model="importMode" value="strict" class="mt-1" />
                  <div>
                    <p class="text-sm font-medium text-gray-800">Huỷ import, sửa file trước (mặc định)</p>
                    <p class="text-xs text-gray-600">An toàn — đảm bảo file sạch trước khi import.</p>
                  </div>
                </label>
                <label class="flex items-start gap-2 cursor-pointer">
                  <input type="radio" v-model="importMode" value="skip_invalid" class="mt-1" />
                  <div>
                    <p class="text-sm font-medium text-gray-800">
                      Bỏ qua {{ totalSkip }} dòng lỗi, import
                      {{ previewData.totalRows - totalSkip }} dòng hợp lệ
                    </p>
                    <p class="text-xs text-gray-600">
                      Tải báo cáo lỗi sau khi import xong để sửa &amp; import lại các dòng đã bỏ qua.
                    </p>
                  </div>
                </label>
              </fieldset>
              <div
                v-if="importMode === 'skip_invalid' && skipRatio > 0.3"
                class="text-xs text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2"
              >
                ⚠ Cảnh báo: hơn {{ Math.round(skipRatio * 100) }}% dòng sẽ bị bỏ qua —
                kiểm tra lại file gốc trước khi tiếp tục.
              </div>
            </div>

            <div
              v-if="allRowsInvalid"
              class="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700"
            >
              Không có dòng hợp lệ nào — toàn bộ file bị lỗi. Hãy sửa file và thử lại.
            </div>

            <!-- Actions -->
            <div class="flex items-center justify-between pt-2">
              <div class="flex gap-2">
                <button class="text-xs text-gray-500 hover:text-gray-700 underline" @click="importStep = 'upload'">
                  ← Đổi file
                </button>
                <button
                  v-if="previewData.errors.length"
                  class="text-xs text-red-600 hover:text-red-800 underline"
                  @click="downloadErrorReport"
                >
                  Tải báo cáo lỗi (.xlsx)
                </button>
              </div>
              <button
                :disabled="!canImport"
                :class="['px-4 py-2 text-sm rounded-lg font-medium transition-colors flex items-center gap-2',
                  !canImport
                    ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                    : 'bg-emerald-600 hover:bg-emerald-700 text-white']"
                @click="runImport"
              >
                <div v-if="importLoading" class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                {{ importLoading
                    ? 'Đang import...'
                    : importMode === 'skip_invalid'
                      ? `Import ${previewData.totalRows - totalSkip} dòng (bỏ qua ${totalSkip}) ▶`
                      : 'Bắt đầu Import ▶' }}
              </button>
            </div>
          </template>

          <!-- STEP 3: RESULT ──────────────────────────────────────────────── -->
          <template v-else-if="importStep === 'result' && importResult">
            <div :class="['p-5 rounded-xl text-center',
              importResult.failed === 0 && importResult.skipped === 0 ? 'bg-green-50' : importResult.success === 0 ? 'bg-red-50' : 'bg-amber-50']">
              <p class="text-3xl font-bold mb-1"
                :class="importResult.failed === 0 && importResult.skipped === 0 ? 'text-green-700' : importResult.success === 0 ? 'text-red-700' : 'text-amber-700'">
                {{ importResult.success }} / {{ importResult.total }}
              </p>
              <p class="text-sm text-gray-600">
                dòng import thành công
                <span v-if="importResult.failed"> — <span class="text-red-600 font-medium">{{ importResult.failed }} lỗi</span></span>
                <span v-if="importResult.skipped"> — <span class="text-amber-700 font-medium">{{ importResult.skipped }} bỏ qua</span></span>
              </p>
            </div>

            <!-- Failed rows -->
            <div v-if="importResult.errors.length" class="space-y-1 max-h-40 overflow-y-auto">
              <p class="text-xs font-medium text-gray-500">Chi tiết lỗi:</p>
              <div v-for="(e, i) in importResult.errors" :key="i"
                class="flex gap-3 text-xs px-3 py-2 bg-red-50 text-red-700 rounded-lg">
                <span class="font-bold shrink-0">Dòng {{ e.row }}</span>
                <span>{{ e.message }}</span>
              </div>
            </div>

            <!-- Skipped rows (skip_invalid mode) -->
            <div v-if="importResult.skippedRows.length" class="space-y-2">
              <div class="flex items-center justify-between">
                <p class="text-xs font-medium text-gray-500">
                  Đã bỏ qua {{ importResult.skipped }} dòng:
                </p>
                <button
                  class="text-xs text-amber-700 hover:text-amber-900 underline"
                  @click="downloadErrorReport"
                >
                  Tải file dòng bị bỏ qua (.xlsx)
                </button>
              </div>
              <div class="space-y-1 max-h-40 overflow-y-auto">
                <div v-for="(s, i) in importResult.skippedRows" :key="i"
                  class="flex gap-3 text-xs px-3 py-2 bg-amber-50 text-amber-800 rounded-lg">
                  <span class="font-bold shrink-0">Dòng {{ s.row }}</span>
                  <span class="font-medium shrink-0">{{ s.field || '—' }}</span>
                  <span class="flex-1">{{ s.message }}</span>
                  <span
                    v-if="s.reason === 'cascade_parent_skipped'"
                    class="shrink-0 px-1.5 py-0.5 rounded bg-amber-200 text-amber-900 text-[10px] font-medium"
                  >phụ thuộc</span>
                </div>
              </div>
            </div>

            <div class="flex justify-between pt-2">
              <button
                v-if="importResult.failed > 0"
                class="text-xs text-gray-500 hover:text-gray-700 underline"
                @click="importStep = 'upload'"
              >
                ← Import lô khác
              </button>
              <button class="ml-auto px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700" @click="closeImport">
                Đóng
              </button>
            </div>
          </template>
        </div>
      </div>
    </div>

    <!-- Xác nhận áp dụng luật khấu hao cho danh mục (thay window.confirm) -->
    <BaseModal
      v-if="applyConfirmOpen"
      title="Áp dụng luật khấu hao cho danh mục"
      size="md"
      @close="applyConfirmOpen = false"
    >
      <p class="text-sm text-gray-600" data-testid="apply-confirm-body">
        Hệ thống sẽ kế thừa luật khấu hao của danh mục
        <strong>"{{ editingName }}"</strong> cho những tài sản đang thiếu (số tháng /
        phương pháp / giá trị thu hồi), rồi sinh lịch khấu hao còn thiếu.
        <br />
        Tài sản đã có kỳ chạy được giữ nguyên (bảo vệ lịch sử khấu hao); giá trị
        bạn đã nhập tay sẽ KHÔNG bị ghi đè.
      </p>
      <template #footer>
        <button class="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50"
                data-testid="apply-cancel-btn"
                @click="applyConfirmOpen = false">Huỷ</button>
        <button class="px-4 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
                data-testid="apply-confirm-btn"
                @click="confirmApplyToExistingAssets">Xác nhận áp dụng</button>
      </template>
    </BaseModal>

    <!-- Kết quả áp dụng luật khấu hao -->
    <BaseModal
      v-if="applyResult"
      title="Kết quả áp dụng khấu hao"
      size="md"
      @close="closeApplyResult"
    >
      <div class="grid grid-cols-2 gap-3">
        <div class="rounded-lg border border-gray-200 p-3">
          <p class="text-xs text-gray-500">Đã kế thừa luật</p>
          <p class="text-xl font-bold text-emerald-600" data-testid="apply-result-inherited">{{ applyResult.inherited }}</p>
        </div>
        <div class="rounded-lg border border-gray-200 p-3">
          <p class="text-xs text-gray-500">Sinh lịch khấu hao</p>
          <p class="text-xl font-bold text-gray-900" data-testid="apply-result-regenerated">{{ applyResult.regenerated }}</p>
        </div>
        <div class="rounded-lg border border-gray-200 p-3">
          <p class="text-xs text-gray-500">Bỏ qua — đã có lịch sử</p>
          <p class="text-xl font-bold text-amber-600" data-testid="apply-result-skipped-history">{{ applyResult.skipped_has_history }}</p>
        </div>
        <div class="rounded-lg border border-gray-200 p-3">
          <p class="text-xs text-gray-500">Bỏ qua — chưa có luật</p>
          <p class="text-xl font-bold text-rose-500" data-testid="apply-result-skipped-no-rule">{{ applyResult.skipped_no_rule }}</p>
        </div>
        <div class="rounded-lg border border-gray-200 p-3 col-span-2">
          <p class="text-xs text-gray-500">Lỗi</p>
          <p class="text-xl font-bold text-rose-600" data-testid="apply-result-errors">{{ applyResult.errors }}</p>
        </div>
      </div>
      <template #footer>
        <button class="px-4 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
                data-testid="apply-result-close-btn"
                @click="closeApplyResult">Đóng</button>
      </template>
    </BaseModal>
  </div>
</template>
