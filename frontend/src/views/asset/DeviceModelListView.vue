<script setup lang="ts">
import { useToast } from '@/composables/useToast'
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { listDeviceModels, deleteDeviceModel } from '@/api/imm00'
import type { ImmDeviceModel } from '@/types/imm00'
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
const models = ref<ImmDeviceModel[]>([])
const loading = ref(false)
const error = ref('')
const totalCount = ref(0)
const PAGE_SIZE = 30
const showFilters = ref(false)

const filters = ref<{ search: string; medical_device_class: string; manufacturer: string; page: number }>({
  search: '',
  medical_device_class: '',
  manufacturer: '',
  page: 1,
})

const CLASS_OPTIONS = ['Class I', 'Class II', 'Class III']
const CLASS_LABEL: Record<string, string> = {
  'Class I': 'Loại I — Rủi ro thấp',
  'Class II': 'Loại II — Rủi ro trung bình',
  'Class III': 'Loại III — Rủi ro cao',
}
const CLASS_COLOR: Record<string, string> = {
  'Class I': 'bg-green-100 text-green-700',
  'Class II': 'bg-yellow-100 text-yellow-700',
  'Class III': 'bg-red-100 text-red-700',
}

// Lightbox preview
const previewUrl = ref('')
const previewName = ref('')
function openPreview(url: string, label: string, e: Event) {
  e.stopPropagation()
  previewUrl.value = url
  previewName.value = label
}
function closePreview() { previewUrl.value = ''; previewName.value = '' }
function onImgError(e: Event) { (e.target as HTMLImageElement).dataset.failed = '1' }

interface FilterChip { key: 'search' | 'medical_device_class' | 'manufacturer'; label: string }
const activeChips = computed<FilterChip[]>(() => {
  const chips: FilterChip[] = []
  if (filters.value.medical_device_class) {
    chips.push({ key: 'medical_device_class', label: CLASS_LABEL[filters.value.medical_device_class] || filters.value.medical_device_class })
  }
  if (filters.value.manufacturer) chips.push({ key: 'manufacturer', label: `Hãng: ${filters.value.manufacturer}` })
  if (filters.value.search.trim()) chips.push({ key: 'search', label: `"${filters.value.search.trim()}"` })
  return chips
})
const activeFilterCount = computed(() => activeChips.value.length)

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await listDeviceModels(filters.value.page, PAGE_SIZE, filters.value.search) as unknown as
      { items: ImmDeviceModel[]; pagination: { total: number } }
    let items = res?.items || []
    if (filters.value.medical_device_class) {
      items = items.filter(m => m.medical_device_class === filters.value.medical_device_class)
    }
    if (filters.value.manufacturer) {
      const q = filters.value.manufacturer.toLowerCase()
      items = items.filter(m => (m.manufacturer || '').toLowerCase().includes(q))
    }
    models.value = items
    totalCount.value = res?.pagination?.total || 0
  } catch (e: unknown) {
    error.value = (e as Error).message || 'Lỗi tải dữ liệu'
  } finally {
    loading.value = false
  }
}

function applyFilters() { filters.value.page = 1; load() }
function quickFilter(key: 'medical_device_class' | 'manufacturer', value: string) {
  if (!value || filters.value[key] === value) return
  filters.value[key] = value
  filters.value.page = 1
  showFilters.value = false
  load()
}
function clearChip(key: string) {
  (filters.value as Record<string, unknown>)[key] = ''
  applyFilters()
}
function resetFilters() {
  filters.value = { search: '', medical_device_class: '', manufacturer: '', page: 1 }
  load()
}
function prevPage() { if (filters.value.page > 1) { filters.value.page--; load() } }
function nextPage() { if (filters.value.page * PAGE_SIZE < totalCount.value) { filters.value.page++; load() } }

async function remove(name: string, ev: Event) {
  ev.stopPropagation()
  if (!confirm(`Xóa Model thiết bị "${name}"?`)) return
  try { await deleteDeviceModel(name); await load() }
  catch (e: unknown) { toast.error((e as Error).message || 'Không thể xóa — có thể đang được tham chiếu') }
}

onMounted(load)

// ── Import / Export ──────────────────────────────────────────────────────────

const IMPORT_DOCTYPE = 'IMM Device Model' as const

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
    importFolder.value = await initImportFolders(IMPORT_DOCTYPE)
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
    previewData.value = await previewRefImport(IMPORT_DOCTYPE, uploadedFileUrl.value)
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
    importResult.value = await importRefData(IMPORT_DOCTYPE, uploadedFileUrl.value)
    importStep.value = 'result'
  } catch (e: unknown) {
    importErr.value = e instanceof Error ? e.message : 'Lỗi import'
  } finally {
    importLoading.value = false
  }
}

async function downloadErrorReport() {
  try {
    const r = await buildErrorReport(IMPORT_DOCTYPE, uploadedFileUrl.value)
    globalThis.open(r.fileUrl, '_blank')
  } catch {
    toast.error('Không tạo được báo cáo lỗi')
  }
}

function doExport() { globalThis.location.href = getExportUrl(IMPORT_DOCTYPE) }
function doDownloadTemplate() { globalThis.location.href = getTemplateUrl(IMPORT_DOCTYPE) }
</script>

<template>
  <div class="page-container animate-fade-in">
    <PageHeader title="Model thiết bị" :subtitle="`Tổng ${totalCount} model`">
      <template #actions>
        <FilterToggleButton v-model="showFilters" :count="activeFilterCount" />
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
        <button class="btn-primary" @click="router.push('/device-models/new')">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          Thêm model thiết bị
        </button>
      </template>
    </PageHeader>

    <ListFilterBar
      :show="showFilters"
      :chips="activeChips"
      v-model:search="filters.search"
      search-placeholder="Tìm theo mã, tên, phiên bản, GMDN..."
      @reset="resetFilters"
      @clear-chip="clearChip"
      @apply="applyFilters"
    >
      <template #fields>
        <div class="form-group">
          <label class="form-label">Phân loại</label>
          <select v-model="filters.medical_device_class" class="form-select" @change="applyFilters">
            <option value="">Tất cả phân loại</option>
            <option v-for="c in CLASS_OPTIONS" :key="c" :value="c">{{ CLASS_LABEL[c] }}</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Hãng sản xuất</label>
          <input v-model="filters.manufacturer" placeholder="Hãng sản xuất..." class="form-input" @keyup.enter="applyFilters" />
        </div>
      </template>
    </ListFilterBar>

    <div v-if="error" class="alert-error mb-4">{{ error }}</div>

    <!-- Table -->
    <div class="card overflow-hidden">
      <div class="flex items-center justify-between px-4 py-3 border-b border-slate-100 bg-slate-50/60">
        <span class="text-xs text-slate-500">
          <span v-if="activeFilterCount > 0">
            Kết quả lọc: <strong class="text-slate-700">{{ models.length }}</strong> model
          </span>
          <span v-else>
            Hiển thị <strong class="text-slate-700">{{ models.length }}</strong> / {{ totalCount }} model
          </span>
        </span>
        <button v-if="activeFilterCount > 0" class="text-xs text-red-500 hover:text-red-700 font-medium" @click="resetFilters">Xóa tất cả</button>
      </div>

      <div v-if="loading" class="p-6">
        <SkeletonLoader v-for="i in 5" :key="i" class="h-12 mb-3" />
      </div>
      <div v-else-if="models.length === 0" class="flex flex-col items-center justify-center py-16 text-slate-400">
        <p class="text-sm">Không tìm thấy model thiết bị nào.</p>
        <button v-if="activeFilterCount > 0" class="mt-3 text-xs text-blue-500 hover:text-blue-700 underline" @click="resetFilters">
          Xóa bộ lọc để xem tất cả
        </button>
      </div>
      <template v-else>
        <!-- Mobile cards -->
        <div class="mobile-card-list sm:hidden">
          <div
            v-for="m in models"
            :key="m.name"
            class="mobile-card"
            @click="router.push(`/device-models/${m.name}`)"
          >
            <div class="flex items-center justify-between mb-2">
              <span class="font-mono text-sm font-semibold text-brand-700">{{ m.name }}</span>
              <span
                v-if="m.medical_device_class"
                :class="['text-xs px-2 py-0.5 rounded-full font-medium', CLASS_COLOR[m.medical_device_class] || 'bg-gray-100 text-gray-600']"
              >{{ m.medical_device_class }}</span>
            </div>
            <p class="text-sm font-medium text-slate-900 truncate">{{ m.model_name }}</p>
            <div class="flex flex-wrap gap-x-2 gap-y-1 mt-1.5 text-xs text-slate-500">
              <span v-if="m.manufacturer">{{ m.manufacturer }}</span>
              <span v-if="m.gmdn_code">· {{ m.gmdn_code }}</span>
            </div>
          </div>
        </div>

        <!-- Desktop table -->
        <div class="hidden sm:block overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-slate-50 border-b border-slate-200">
            <tr>
              <th class="px-4 py-3 text-left text-xs font-medium text-slate-500 w-12"></th>
              <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Mã</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Tên model</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Hãng sản xuất</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Phiên bản</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Phân loại</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">GMDN</th>
              <th class="px-4 py-3 text-right"></th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr v-for="m in models" :key="m.name" class="hover:bg-slate-50 cursor-pointer transition-colors" @click="router.push(`/device-models/${m.name}`)">
              <td class="px-4 py-3">
                <button
                  v-if="m.model_image" type="button"
                  class="block w-12 h-12 rounded-lg border border-slate-200 bg-slate-50 overflow-hidden hover:ring-2 hover:ring-blue-400 transition"
                  :title="`Xem ảnh — ${m.model_name}`"
                  @click="openPreview(m.model_image as string, m.model_name || m.name, $event)"
                >
                  <img :src="m.model_image" alt="" loading="lazy" class="w-full h-full object-cover data-[failed=1]:hidden" @error="onImgError" />
                </button>
                <div v-else class="w-12 h-12 rounded-lg border border-dashed border-slate-200 bg-slate-50/60 flex items-center justify-center text-slate-300">
                  <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909m-18 3.75h16.5a1.5 1.5 0 001.5-1.5V6a1.5 1.5 0 00-1.5-1.5H3.75A1.5 1.5 0 002.25 6v12a1.5 1.5 0 001.5 1.5z" />
                  </svg>
                </div>
              </td>
              <td class="px-4 py-3 font-mono text-xs text-slate-500">{{ m.name }}</td>
              <td class="px-4 py-3 font-medium text-slate-800">
                {{ m.model_name }}
                <p v-if="m.asset_category" class="text-[10px] text-slate-400 font-normal mt-0.5">{{ (m as any).asset_category_name || (m as any).category_name || m.asset_category }}</p>
              </td>
              <td class="px-4 py-3">
                <button
                  v-if="m.manufacturer"
                  class="text-left text-slate-700 hover:text-blue-600 hover:underline decoration-dotted underline-offset-2"
                  @click.stop="quickFilter('manufacturer', m.manufacturer!)"
                >{{ m.manufacturer }}</button>
                <span v-else class="text-slate-400">—</span>
              </td>
              <td class="px-4 py-3 text-slate-500">{{ m.model_version || '—' }}</td>
              <td class="px-4 py-3">
                <button
                  v-if="m.medical_device_class"
                  :class="['text-xs px-2 py-1 rounded-full font-medium transition-all hover:ring-2 hover:ring-offset-1 hover:ring-current/50', CLASS_COLOR[m.medical_device_class] || 'bg-gray-100 text-gray-600']"
                  :title="`Lọc: ${CLASS_LABEL[m.medical_device_class] || m.medical_device_class}`"
                  @click.stop="quickFilter('medical_device_class', m.medical_device_class!)"
                >{{ m.medical_device_class }}</button>
                <span v-else class="text-slate-400">—</span>
              </td>
              <td class="px-4 py-3 text-slate-500 font-mono text-xs">{{ m.gmdn_code || '—' }}</td>
              <td class="px-4 py-3 text-right space-x-2 whitespace-nowrap">
                <button class="text-blue-600 hover:text-blue-800 text-xs font-medium" @click.stop="router.push(`/device-models/${m.name}`)">Sửa</button>
                <button class="text-red-600 hover:text-red-800 text-xs font-medium" @click="(ev) => remove(m.name, ev)">Xóa</button>
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

    <!-- Import Modal -->
    <div
      v-if="showImport"
      class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4"
      @click.self="closeImport"
    >
      <div class="bg-white rounded-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div class="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <div>
            <h2 class="text-base font-semibold text-gray-800">Import Model thiết bị</h2>
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
                <button v-if="previewData.errors.length" class="text-xs text-red-600 hover:text-red-800 underline" @click="downloadErrorReport">
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
              <button v-if="importResult.failed > 0" class="text-xs text-gray-500 hover:text-gray-700 underline" @click="importStep = 'upload'">
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

    <!-- Lightbox preview -->
    <div
      v-if="previewUrl"
      class="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-6 cursor-zoom-out"
      @click="closePreview"
      @keydown.esc="closePreview"
    >
      <div class="relative max-w-5xl max-h-[90vh] flex flex-col items-center" @click.stop>
        <img :src="previewUrl" :alt="previewName" class="max-w-full max-h-[80vh] object-contain rounded-lg shadow-2xl bg-white" />
        <div class="mt-3 flex items-center gap-3 text-white text-sm">
          <span class="font-medium">{{ previewName }}</span>
          <a :href="previewUrl" target="_blank" rel="noopener" class="text-blue-200 hover:text-white underline-offset-4 hover:underline">Mở tab mới</a>
          <button type="button" class="ml-2 px-3 py-1 rounded-md bg-white/10 hover:bg-white/20 border border-white/20" @click="closePreview">Đóng (Esc)</button>
        </div>
      </div>
    </div>
  </div>
</template>
