<script setup lang="ts">
import { useToast } from '@/composables/useToast'
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { listSuppliers, deleteSupplier } from '@/api/imm00'
import type { AcSupplier } from '@/types/imm00'
import {
  previewRefImport, importRefData, buildErrorReport,
  getExportUrl, getTemplateUrl, initImportFolders,
} from '@/api/importData'
import type { ImportPreviewResult, ImportResult, ImportStep } from '@/types/import'
import api from '@/api/axios'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import FilterToggleButton from '@/components/common/FilterToggleButton.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'
const toast = useToast()

const router = useRouter()
const suppliers = ref<AcSupplier[]>([])
const loading = ref(false)
const error = ref('')
const totalCount = ref(0)
const showFilters = ref(false)
const PAGE_SIZE = 30

const filters = ref({
  search: '',
  vendor_type: '',
  country: '',
  is_active: '' as '' | '1' | '0',
  page: 1,
})

const VENDOR_TYPES: { value: string; label: string }[] = [
  { value: 'Manufacturer', label: 'Nhà sản xuất' },
  { value: 'Distributor', label: 'Nhà phân phối' },
  { value: 'Service Provider', label: 'Dịch vụ' },
  { value: 'Calibration Lab', label: 'Phòng hiệu chuẩn' },
]
const VENDOR_TYPE_LABEL: Record<string, string> = Object.fromEntries(
  VENDOR_TYPES.map(v => [v.value, v.label]),
)

const VENDOR_TYPE_COLORS: Record<string, string> = {
  Manufacturer: 'bg-purple-100 text-purple-700',
  Distributor: 'bg-blue-100 text-blue-700',
  'Service Provider': 'bg-green-100 text-green-700',
  'Calibration Lab': 'bg-yellow-100 text-yellow-700',
}

interface FilterChip { key: 'search' | 'vendor_type' | 'country' | 'is_active'; label: string }
const activeChips = computed<FilterChip[]>(() => {
  const chips: FilterChip[] = []
  if (filters.value.vendor_type) {
    chips.push({ key: 'vendor_type', label: VENDOR_TYPE_LABEL[filters.value.vendor_type] || filters.value.vendor_type })
  }
  if (filters.value.country) chips.push({ key: 'country', label: filters.value.country })
  if (filters.value.is_active === '1') chips.push({ key: 'is_active', label: 'Đang hoạt động' })
  if (filters.value.is_active === '0') chips.push({ key: 'is_active', label: 'Ngừng hoạt động' })
  if (filters.value.search?.trim()) chips.push({ key: 'search', label: `"${filters.value.search.trim()}"` })
  return chips
})
const activeFilterCount = computed(() => activeChips.value.length)

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await listSuppliers(filters.value.page, PAGE_SIZE, filters.value.search) as unknown as
      { items: AcSupplier[]; pagination: { total: number } }
    let items = res?.items || []
    if (filters.value.vendor_type) items = items.filter(s => s.vendor_type === filters.value.vendor_type)
    if (filters.value.country) items = items.filter(s => (s.country || '').toLowerCase().includes(filters.value.country.toLowerCase()))
    if (filters.value.is_active === '1') items = items.filter(s => s.is_active === 1)
    if (filters.value.is_active === '0') items = items.filter(s => s.is_active === 0)
    suppliers.value = items
    totalCount.value = res?.pagination?.total || 0
  } catch (e: unknown) {
    error.value = (e as Error).message || 'Lỗi tải dữ liệu'
  } finally {
    loading.value = false
  }
}

function applyFilters() { filters.value.page = 1; load() }
function quickFilter(key: 'vendor_type' | 'country', value: string) {
  if (!value) return
  if (filters.value[key] === value) return
  filters.value[key] = value
  filters.value.page = 1
  showFilters.value = false
  load()
}
function clearChip(key: string) {
  if (key === 'is_active') filters.value.is_active = ''
  else (filters.value as Record<string, unknown>)[key] = ''
  applyFilters()
}
function resetFilters() {
  filters.value = { search: '', vendor_type: '', country: '', is_active: '', page: 1 }
  load()
}
function prevPage() { if (filters.value.page > 1) { filters.value.page--; load() } }
function nextPage() { if (filters.value.page * PAGE_SIZE < totalCount.value) { filters.value.page++; load() } }

async function remove(s: AcSupplier, ev: Event) {
  ev.stopPropagation()
  if (!confirm(`Xóa nhà cung cấp "${s.supplier_name}" (${s.name})?`)) return
  try {
    await deleteSupplier(s.name)
    await load()
  } catch (e: unknown) {
    toast.error((e as Error).message || 'Không thể xóa — có thể đang được tham chiếu')
  }
}

function formatDate(d?: string) {
  return d ? new Date(d).toLocaleDateString('vi-VN') : '—'
}
function daysUntilExpiry(d?: string) {
  if (!d) return null
  return Math.ceil((new Date(d).getTime() - Date.now()) / 86400000)
}
function expiryClass(d?: string) {
  const days = daysUntilExpiry(d)
  if (days === null) return 'text-slate-400'
  if (days < 0) return 'text-red-700 font-semibold'
  if (days < 30) return 'text-red-600 font-medium'
  if (days < 90) return 'text-yellow-600 font-medium'
  return 'text-slate-600'
}

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

const hasBlockingErrors = computed(
  () => (previewData.value?.errors ?? []).some(e => e.severity === 'error'),
)

async function openImport() {
  showImport.value = true
  importStep.value = 'upload'
  uploadedFileUrl.value = ''
  uploadedFileName.value = ''
  previewData.value = null
  importResult.value = null
  importErr.value = ''
  try {
    importFolder.value = await initImportFolders('AC Supplier')
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
    previewData.value = await previewRefImport('AC Supplier', uploadedFileUrl.value)
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
    importResult.value = await importRefData('AC Supplier', uploadedFileUrl.value)
    importStep.value = 'result'
  } catch (e: unknown) {
    importErr.value = e instanceof Error ? e.message : 'Lỗi import'
  } finally {
    importLoading.value = false
  }
}

async function downloadErrorReport() {
  try {
    const r = await buildErrorReport('AC Supplier', uploadedFileUrl.value)
    globalThis.open(r.fileUrl, '_blank')
  } catch {
    toast.error('Không tạo được báo cáo lỗi')
  }
}

function doExport() { globalThis.location.href = getExportUrl('AC Supplier') }
function doDownloadTemplate() { globalThis.location.href = getTemplateUrl('AC Supplier') }
</script>

<template>
  <div class="page-container animate-fade-in">
    <PageHeader
      title="Nhà cung cấp"
      :subtitle="`Tổng ${totalCount} nhà cung cấp`"
    >
      <template #actions>
        <FilterToggleButton v-model="showFilters" :count="activeFilterCount" />
        <button
          class="px-3 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 text-gray-600 flex items-center gap-1.5 shrink-0"
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
          class="px-3 py-2 text-sm border border-emerald-300 rounded-lg hover:bg-emerald-50 text-emerald-700 flex items-center gap-1.5 shrink-0"
          @click="openImport"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
          </svg>
          Import
        </button>
        <button class="btn-primary shrink-0" @click="router.push('/suppliers/new')">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          Thêm nhà cung cấp
        </button>
      </template>
    </PageHeader>

    <ListFilterBar
      :show="showFilters"
      :chips="activeChips"
      v-model:search="filters.search"
      search-placeholder="Tìm theo mã, tên, email, mã số thuế..."
      @reset="resetFilters"
      @clear-chip="clearChip"
      @apply="applyFilters"
    >
      <template #fields>
        <div class="form-group">
          <label class="form-label">Loại nhà cung cấp</label>
          <select v-model="filters.vendor_type" class="form-select text-sm" @change="applyFilters">
            <option value="">Tất cả loại</option>
            <option v-for="t in VENDOR_TYPES" :key="t.value" :value="t.value">{{ t.label }}</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Quốc gia</label>
          <input v-model="filters.country" placeholder="Quốc gia..." class="form-input text-sm" @keyup.enter="applyFilters" />
        </div>
        <div class="form-group">
          <label class="form-label">Trạng thái</label>
          <select v-model="filters.is_active" class="form-select text-sm" @change="applyFilters">
            <option value="">Tất cả trạng thái</option>
            <option value="1">Đang hoạt động</option>
            <option value="0">Ngừng hoạt động</option>
          </select>
        </div>
      </template>
    </ListFilterBar>

    <div v-if="error" class="alert-error mb-4">{{ error }}</div>

    <div class="card overflow-hidden">
      <div class="flex items-center justify-between px-4 py-3 border-b border-slate-100 bg-slate-50/60">
        <span class="text-xs text-slate-500">
          <span v-if="activeFilterCount > 0">
            Kết quả lọc: <strong class="text-slate-700">{{ suppliers.length }}</strong> nhà cung cấp
          </span>
          <span v-else>
            Hiển thị <strong class="text-slate-700">{{ suppliers.length }}</strong> / {{ totalCount }} nhà cung cấp
          </span>
        </span>
        <button v-if="activeFilterCount > 0" class="text-xs text-red-500 hover:text-red-700 font-medium" @click="resetFilters">
          Xóa tất cả
        </button>
      </div>

      <div v-if="loading" class="p-6">
        <SkeletonLoader v-for="i in 5" :key="i" class="h-10 mb-3" />
      </div>
      <div v-else-if="suppliers.length === 0" class="flex flex-col items-center justify-center py-16 text-slate-400">
        <p class="text-sm">Không có nhà cung cấp nào phù hợp.</p>
        <button v-if="activeFilterCount > 0" class="mt-3 text-xs text-blue-500 hover:text-blue-700 underline" @click="resetFilters">
          Xóa bộ lọc để xem tất cả
        </button>
      </div>
      <template v-else>
        <!-- Mobile cards -->
        <div class="mobile-card-list sm:hidden">
          <div
            v-for="s in suppliers"
            :key="s.name"
            class="mobile-card"
            @click="router.push(`/suppliers/${s.name}`)"
          >
            <div class="flex items-center justify-between mb-2">
              <span class="font-mono text-sm font-semibold text-brand-700">{{ s.name }}</span>
              <span
                class="text-xs px-2 py-0.5 rounded-full font-medium"
                :class="s.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'"
              >{{ s.is_active ? 'Hoạt động' : 'Ngừng' }}</span>
            </div>
            <p class="text-sm font-medium text-slate-900 truncate">{{ s.supplier_name }}</p>
            <div class="flex flex-wrap gap-x-2 gap-y-1 mt-1.5 text-xs text-slate-500">
              <span v-if="s.vendor_type">
                <span :class="['px-1.5 py-0.5 rounded font-medium', VENDOR_TYPE_COLORS[s.vendor_type] || 'bg-gray-100 text-gray-600']">{{ VENDOR_TYPE_LABEL[s.vendor_type] || s.vendor_type }}</span>
              </span>
              <span v-if="s.country">· {{ s.country }}</span>
              <span :class="expiryClass(s.contract_end)">· {{ formatDate(s.contract_end) }}</span>
            </div>
          </div>
        </div>

        <!-- Desktop table -->
        <div class="hidden sm:block overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-slate-50 border-b border-slate-200">
            <tr>
              <th class="table-header">Mã nhà cung cấp</th>
              <th class="table-header">Tên nhà cung cấp</th>
              <th class="table-header">Loại</th>
              <th class="table-header">Quốc gia</th>
              <th class="table-header">Email liên hệ</th>
              <th class="table-header">Hết hạn HĐ</th>
              <th class="table-header text-center">Trạng thái</th>
              <th class="px-4 py-3 text-right"></th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr
              v-for="s in suppliers" :key="s.name"
              class="hover:bg-slate-50 cursor-pointer transition-colors"
              @click="router.push(`/suppliers/${s.name}`)"
            >
              <td class="px-4 py-3 font-mono text-xs text-slate-500">{{ s.name }}</td>
              <td class="px-4 py-3 font-medium text-slate-800">{{ s.supplier_name }}</td>
              <td class="px-4 py-3">
                <button
                  v-if="s.vendor_type"
                  :class="['text-xs px-2 py-0.5 rounded-full font-medium transition-all hover:ring-2 hover:ring-offset-1 hover:ring-current/50', VENDOR_TYPE_COLORS[s.vendor_type] || 'bg-gray-100 text-gray-600']"
                  :title="`Lọc: ${VENDOR_TYPE_LABEL[s.vendor_type] || s.vendor_type}`"
                  @click.stop="quickFilter('vendor_type', s.vendor_type!)"
                >{{ VENDOR_TYPE_LABEL[s.vendor_type] || s.vendor_type }}</button>
                <span v-else class="text-slate-400">—</span>
              </td>
              <td class="px-4 py-3">
                <button
                  v-if="s.country"
                  class="text-left text-slate-700 hover:text-blue-600 hover:underline decoration-dotted underline-offset-2"
                  @click.stop="quickFilter('country', s.country!)"
                >{{ s.country }}</button>
                <span v-else class="text-slate-400">—</span>
              </td>
              <td class="px-4 py-3 text-slate-500">{{ s.email_id || '—' }}</td>
              <td class="px-4 py-3" :class="expiryClass(s.contract_end)">
                {{ formatDate(s.contract_end) }}
              </td>
              <td class="px-4 py-3 text-center">
                <span
                  class="text-xs px-2 py-0.5 rounded-full font-medium"
                  :class="s.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'"
                >{{ s.is_active ? 'Hoạt động' : 'Ngừng' }}</span>
              </td>
              <td class="px-4 py-3 text-right space-x-2 whitespace-nowrap">
                <button
                  class="text-blue-600 hover:text-blue-800 text-xs font-medium"
                  @click.stop="router.push(`/suppliers/${s.name}/edit`)"
                >Sửa</button>
                <button
                  class="text-red-600 hover:text-red-800 text-xs font-medium"
                  @click="(ev) => remove(s, ev)"
                >Xóa</button>
              </td>
            </tr>
          </tbody>
        </table>
        </div>
      </template>

      <div v-if="totalCount > PAGE_SIZE" class="flex items-center justify-between px-4 py-3 border-t border-slate-100 text-sm text-slate-500">
        <span>{{ (filters.page - 1) * PAGE_SIZE + 1 }}–{{ Math.min(filters.page * PAGE_SIZE, totalCount) }} / {{ totalCount }}</span>
        <div class="flex gap-2">
          <button :disabled="filters.page === 1" class="px-3 py-1 rounded border border-slate-300 disabled:opacity-40 hover:bg-slate-50" @click="prevPage">‹ Trước</button>
          <button :disabled="filters.page * PAGE_SIZE >= totalCount" class="px-3 py-1 rounded border border-slate-300 disabled:opacity-40 hover:bg-slate-50" @click="nextPage">Sau ›</button>
        </div>
      </div>
    </div>
  </div>

  <!-- ── Import Modal ──────────────────────────────────────────────────────── -->
  <div
    v-if="showImport"
    class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4"
    @click.self="closeImport"
  >
    <div class="bg-white rounded-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
      <!-- Header -->
      <div class="flex items-center justify-between px-6 py-4 border-b border-gray-200">
        <div>
          <h2 class="text-base font-semibold text-gray-800">Import Nhà cung cấp</h2>
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
        <div
          v-for="(label, idx) in ['1. Upload', '2. Kiểm tra', '3. Kết quả']"
          :key="idx"
          :class="['flex-1 text-center py-2 text-xs font-medium',
            (importStep === 'upload' && idx === 0) || (importStep === 'preview' && idx === 1) || (importStep === 'result' && idx === 2)
              ? 'text-blue-600 border-b-2 border-blue-600 -mb-px'
              : 'text-gray-400']"
        >
          {{ label }}
        </div>
      </div>

      <div class="p-6 space-y-4">
        <!-- Error banner -->
        <div v-if="importErr" class="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-lg">
          {{ importErr }}
        </div>

        <!-- STEP 1: UPLOAD -->
        <template v-if="importStep === 'upload'">
          <div class="flex items-center justify-between">
            <p class="text-sm text-gray-600">Tải template, điền dữ liệu rồi upload lại:</p>
            <button class="text-xs text-blue-600 hover:underline flex items-center gap-1" @click="doDownloadTemplate">
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              Tải template Excel
            </button>
          </div>

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

        <!-- STEP 2: PREVIEW -->
        <template v-else-if="importStep === 'preview' && previewData">
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
              :disabled="hasBlockingErrors || importLoading"
              :class="['px-4 py-2 text-sm rounded-lg font-medium transition-colors flex items-center gap-2',
                hasBlockingErrors || importLoading
                  ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                  : 'bg-emerald-600 hover:bg-emerald-700 text-white']"
              @click="runImport"
            >
              <div v-if="importLoading" class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              {{ importLoading ? 'Đang import...' : 'Bắt đầu Import ▶' }}
            </button>
          </div>
        </template>

        <!-- STEP 3: RESULT -->
        <template v-else-if="importStep === 'result' && importResult">
          <div :class="['p-5 rounded-xl text-center',
            importResult.failed === 0 ? 'bg-green-50' : importResult.success === 0 ? 'bg-red-50' : 'bg-amber-50']">
            <p class="text-3xl font-bold mb-1"
              :class="importResult.failed === 0 ? 'text-green-700' : importResult.success === 0 ? 'text-red-700' : 'text-amber-700'">
              {{ importResult.success }} / {{ importResult.total }}
            </p>
            <p class="text-sm text-gray-600">
              dòng import thành công
              <span v-if="importResult.failed"> — <span class="text-red-600 font-medium">{{ importResult.failed }} lỗi</span></span>
            </p>
          </div>

          <div v-if="importResult.errors.length" class="space-y-1 max-h-40 overflow-y-auto">
            <p class="text-xs font-medium text-gray-500">Chi tiết lỗi:</p>
            <div v-for="(e, i) in importResult.errors" :key="i"
              class="flex gap-3 text-xs px-3 py-2 bg-red-50 text-red-700 rounded-lg">
              <span class="font-bold shrink-0">Dòng {{ e.row }}</span>
              <span>{{ e.message }}</span>
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
</template>
