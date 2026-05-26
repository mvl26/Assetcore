<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAssetStore, useRefDataStore } from '@/stores/imm00'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import FilterToggleButton from '@/components/common/FilterToggleButton.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'
import BasePagination from '@/components/common/BasePagination.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import type { LifecycleStatus, AssetListParams } from '@/types/imm00'
import {
  previewRefImport, importRefData, buildErrorReport,
  getExportUrl, getTemplateUrl, initImportFolders,
} from '@/api/importData'
import type { ImportPreviewResult, ImportResult, ImportStep } from '@/types/import'
import api from '@/api/axios'
import { useToast } from '@/composables/useToast'

const router = useRouter()
const store = useAssetStore()
const refData = useRefDataStore()

const showFilters = ref(false)

const filters = ref<AssetListParams>({
  lifecycle_status: '',
  department: '',
  location: '',
  asset_category: '',
  gmdn_code: '',
  search: '',
  page: 1,
  page_size: 20,
})

// Danh sách mã GMDN distinct từ Asset Category (source of truth)
const gmdnOptions = computed(() => {
  const seen = new Set<string>()
  return refData.categories
    .filter(c => c.gmdn_code && !seen.has(c.gmdn_code) && (seen.add(c.gmdn_code), true))
    .map(c => ({ value: c.gmdn_code as string, label: `${c.gmdn_code} — ${c.gmdn_term || c.category_name}` }))
})

const LIFECYCLE_STATUSES: { value: LifecycleStatus | ''; label: string }[] = [
  { value: '', label: 'Tất cả trạng thái' },
  { value: 'Commissioned', label: 'Đã đưa vào sử dụng' },
  { value: 'Active', label: 'Đang hoạt động' },
  { value: 'Under Repair', label: 'Đang sửa chữa' },
  { value: 'Calibrating', label: 'Đang hiệu chuẩn' },
  { value: 'Out of Service', label: 'Ngừng hoạt động' },
  { value: 'Decommissioned', label: 'Đã thanh lý' },
]


const cleanParams = computed<AssetListParams>(() => {
  const p: AssetListParams = { page: filters.value.page, page_size: filters.value.page_size }
  if (filters.value.lifecycle_status) p.lifecycle_status = filters.value.lifecycle_status
  if (filters.value.department) p.department = filters.value.department
  if (filters.value.location) p.location = filters.value.location
  if (filters.value.asset_category) p.asset_category = filters.value.asset_category
  if (filters.value.gmdn_code) p.gmdn_code = filters.value.gmdn_code
  if (filters.value.search?.trim()) p.search = filters.value.search.trim()
  return p
})

// Active filter chips — luôn hiển thị kể cả khi panel đóng
interface FilterChip { key: keyof AssetListParams; label: string }
const activeChips = computed<FilterChip[]>(() => {
  const chips: FilterChip[] = []
  if (filters.value.lifecycle_status) {
    const s = LIFECYCLE_STATUSES.find(x => x.value === filters.value.lifecycle_status)
    chips.push({ key: 'lifecycle_status', label: s?.label ?? String(filters.value.lifecycle_status) })
  }
  if (filters.value.asset_category) {
    const c = refData.categories.find(x => x.name === filters.value.asset_category)
    chips.push({ key: 'asset_category', label: c?.category_name ?? String(filters.value.asset_category) })
  }
  if (filters.value.department) {
    const d = refData.departments.find(x => x.name === filters.value.department)
    chips.push({ key: 'department', label: d?.department_name ?? String(filters.value.department) })
  }
  if (filters.value.location) {
    const l = refData.locations.find(x => x.name === filters.value.location)
    chips.push({ key: 'location', label: l?.location_name ?? String(filters.value.location) })
  }
  if (filters.value.gmdn_code) {
    chips.push({ key: 'gmdn_code', label: `GMDN: ${filters.value.gmdn_code}` })
  }
  if (filters.value.search?.trim()) {
    chips.push({ key: 'search', label: `"${filters.value.search.trim()}"` })
  }
  return chips
})

const activeFilterCount = computed(() => activeChips.value.length)

function applyFilters() {
  filters.value.page = 1
  store.fetchList(cleanParams.value)
}

// Nhấp vào giá trị trong bảng → tự thêm vào bộ lọc (giống ERPNext)
function quickFilter(key: keyof AssetListParams, value: string) {
  if (!value) return
  const f = filters.value as Record<string, unknown>
  if (f[key] === value) return // đã lọc rồi, bỏ qua
  f[key] = value
  filters.value.page = 1
  showFilters.value = false
  store.fetchList(cleanParams.value)
}

function clearChip(key: string) {
  (filters.value as Record<string, unknown>)[key] = ''
  applyFilters()
}

function resetFilters() {
  filters.value = { lifecycle_status: '', department: '', location: '', asset_category: '', gmdn_code: '', search: '', page: 1, page_size: 20 }
  store.fetchList({})
}

function goToPage(page: number) {
  filters.value.page = page
  store.fetchList({ ...cleanParams.value, page })
}

function formatDate(d?: string) {
  if (!d) return '—'
  return new Date(d).toLocaleDateString('vi-VN')
}

function isPmOverdue(date?: string) {
  if (!date) return false
  return new Date(date) < new Date()
}

onMounted(async () => {
  await Promise.all([store.fetchList(), refData.fetchAll()])
})

// ── Import / Export ──────────────────────────────────────────────────────────
const toast = useToast()
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

async function openImport() {
  showImport.value = true
  importStep.value = 'upload'
  uploadedFileUrl.value = ''
  uploadedFileName.value = ''
  previewData.value = null
  importResult.value = null
  importErr.value = ''
  try {
    importFolder.value = await initImportFolders('AC Asset')
  } catch {
    importFolder.value = 'Home/Attachments'
  }
}

function closeImport() {
  showImport.value = false
  if (importStep.value === 'result' && (importResult.value?.success ?? 0) > 0) {
    store.fetchList(cleanParams.value)
  }
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
    previewData.value = await previewRefImport('AC Asset', uploadedFileUrl.value)
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
    importResult.value = await importRefData('AC Asset', uploadedFileUrl.value)
    importStep.value = 'result'
  } catch (e: unknown) {
    importErr.value = e instanceof Error ? e.message : 'Lỗi import'
  } finally {
    importLoading.value = false
  }
}

async function downloadErrorReport() {
  try {
    const r = await buildErrorReport('AC Asset', uploadedFileUrl.value)
    globalThis.open(r.fileUrl, '_blank')
  } catch {
    toast.error('Không tạo được báo cáo lỗi')
  }
}

function doExport() { globalThis.location.href = getExportUrl('AC Asset') }
function doDownloadTemplate() { globalThis.location.href = getTemplateUrl('AC Asset') }

const hasBlockingErrors = computed(
  () => (previewData.value?.errors ?? []).some(e => e.severity === 'error'),
)
</script>

<template>
  <div class="page-container animate-fade-in">
    <PageHeader
      title="Danh sách Thiết bị"
      :subtitle="`Tổng ${store.pagination.total} thiết bị`"
    >
      <template #actions>
        <FilterToggleButton v-model="showFilters" :count="activeFilterCount" />
        <button
          class="px-3 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 text-gray-600 flex items-center gap-1.5"
          title="Tải toàn bộ danh sách thiết bị về Excel"
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
        <button class="btn-primary" @click="router.push('/assets/new')">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          Thêm thiết bị
        </button>
      </template>
    </PageHeader>

    <ListFilterBar
      :show="showFilters"
      :chips="activeChips"
      v-model:search="filters.search"
      search-placeholder="Tìm theo tên, mã, serial hoặc mã GMDN..."
      @reset="resetFilters"
      @clear-chip="clearChip"
      @apply="applyFilters"
    >
      <template #fields>
        <div class="form-group">
          <label class="form-label">Trạng thái</label>
          <select v-model="filters.lifecycle_status" class="form-select" @change="applyFilters">
            <option v-for="s in LIFECYCLE_STATUSES" :key="s.value" :value="s.value">{{ s.label }}</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Danh mục</label>
          <select v-model="filters.asset_category" class="form-select" @change="applyFilters">
            <option value="">Tất cả danh mục</option>
            <option v-for="c in refData.categories" :key="c.name" :value="c.name">{{ c.category_name }}</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Khoa/Phòng</label>
          <select v-model="filters.department" class="form-select" @change="applyFilters">
            <option value="">Tất cả khoa/phòng</option>
            <option v-for="d in refData.departments" :key="d.name" :value="d.name">{{ d.department_name }}</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Vị trí</label>
          <select v-model="filters.location" class="form-select" @change="applyFilters">
            <option value="">Tất cả vị trí</option>
            <option v-for="l in refData.locations" :key="l.name" :value="l.name">{{ l.location_name }}</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">GMDN Code</label>
          <select v-model="filters.gmdn_code" class="form-select" @change="applyFilters">
            <option value="">Tất cả mã GMDN</option>
            <option v-for="g in gmdnOptions" :key="g.value" :value="g.value">{{ g.label }}</option>
          </select>
        </div>
      </template>
    </ListFilterBar>

    <!-- Error -->
    <div v-if="store.error" class="alert-error mb-4">{{ store.error }}</div>

    <!-- Loading -->
    <div v-if="store.loading" class="table-wrapper">
      <SkeletonLoader variant="table" :rows="6" />
    </div>

    <!-- Data -->
    <template v-else>
      <!-- Mobile cards (< sm) -->
      <div class="mobile-card-list sm:hidden">
        <div class="flex items-center justify-between text-xs text-slate-500 pb-1">
          <span>Hiển thị <strong class="text-slate-700">{{ store.assets.length }}</strong> / {{ store.pagination.total }} thiết bị</span>
          <button v-if="activeFilterCount > 0" class="text-red-500 font-medium" @click="resetFilters">Xóa tất cả</button>
        </div>
        <div
          v-for="asset in store.assets"
          :key="asset.name"
          class="mobile-card"
          @click="router.push(`/assets/${asset.name}`)"
        >
          <div class="flex items-center justify-between mb-2">
            <span class="font-mono text-sm font-semibold text-brand-700">{{ asset.name }}</span>
            <button @click.stop="quickFilter('lifecycle_status', asset.lifecycle_status)">
              <StatusBadge :state="asset.lifecycle_status" />
            </button>
          </div>
          <p class="text-sm font-medium text-slate-900 truncate">{{ asset.asset_name }}</p>
          <div class="flex flex-wrap items-center gap-x-2 gap-y-1 mt-1.5 text-xs text-slate-500">
            <span v-if="asset.asset_category_name || asset.category_name || asset.asset_category">
              {{ asset.asset_category_name || asset.category_name || asset.asset_category }}
            </span>
            <span v-if="asset.department_name || asset.department" class="text-slate-300">·</span>
            <span>{{ asset.department_name || asset.department }}</span>
            <span v-if="isPmOverdue(asset.next_pm_date)" class="text-red-600 font-semibold">PM quá hạn</span>
          </div>
        </div>
        <div v-if="store.assets.length === 0" class="py-12 text-center text-slate-400">
          <p class="text-sm font-medium">Không có thiết bị nào phù hợp</p>
          <button v-if="activeFilterCount > 0" class="text-xs text-blue-500 underline mt-2" @click="resetFilters">Xóa bộ lọc để xem tất cả</button>
        </div>
      </div>

      <!-- Desktop table (sm+) -->
      <div class="hidden sm:block table-wrapper">
        <div class="flex items-center justify-between px-4 py-2.5 border-b border-slate-100 bg-slate-50/60 text-xs text-slate-500">
          <span>Hiển thị <strong class="text-slate-700">{{ store.assets.length }}</strong> / {{ store.pagination.total }} thiết bị</span>
          <button v-if="activeFilterCount > 0" class="text-red-500 hover:text-red-700 font-medium" @click="resetFilters">Xóa tất cả</button>
        </div>
        <div v-if="store.assets.length" class="overflow-x-auto">
          <table class="min-w-full divide-y divide-slate-100">
            <thead>
              <tr>
                <th class="table-header">Tên / Mã</th>
                <th class="table-header">Danh mục</th>
                <th class="table-header">Trạng thái</th>
                <th class="table-header">GMDN</th>
                <th class="table-header">Khoa/Phòng</th>
                <th class="table-header text-right">Giá trị còn lại</th>
                <th class="table-header">Bảo trì tiếp</th>
                <th class="table-header">ĐK Bộ Y tế hết hạn</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              <tr
                v-for="asset in store.assets"
                :key="asset.name"
                class="hover:bg-slate-50 cursor-pointer transition-colors"
                @click="router.push(`/assets/${asset.name}`)"
              >
                <td class="table-cell">
                  <p class="font-medium text-slate-900">{{ asset.asset_name }}</p>
                  <p class="text-xs text-slate-400 font-mono mt-0.5">{{ asset.name }}</p>
                </td>
                <td class="table-cell">
                  <button
                    v-if="asset.asset_category"
                    class="text-left text-slate-700 hover:text-blue-600 hover:underline decoration-dotted underline-offset-2 transition-colors"
                    @click.stop="quickFilter('asset_category', asset.asset_category!)"
                  >{{ asset.asset_category_name || asset.category_name || asset.asset_category }}</button>
                  <span v-else class="text-slate-400">—</span>
                </td>
                <td class="table-cell">
                  <button @click.stop="quickFilter('lifecycle_status', asset.lifecycle_status)">
                    <StatusBadge :state="asset.lifecycle_status" />
                  </button>
                </td>
                <td class="table-cell">
                  <button
                    v-if="asset.gmdn_code"
                    class="font-mono text-sm text-slate-700 hover:text-blue-600 hover:underline decoration-dotted underline-offset-2"
                    :title="asset.gmdn_term || ''"
                    @click.stop="quickFilter('gmdn_code', asset.gmdn_code!)"
                  >{{ asset.gmdn_code }}</button>
                  <span v-else class="text-slate-400">—</span>
                </td>
                <td class="table-cell">
                  <button
                    v-if="asset.department"
                    class="text-left text-slate-700 hover:text-blue-600 hover:underline decoration-dotted underline-offset-2 transition-colors"
                    @click.stop="quickFilter('department', asset.department)"
                  >{{ asset.department_name || asset.department }}</button>
                  <span v-else class="text-slate-400">—</span>
                </td>
                <td class="table-cell text-right tabular-nums font-mono text-sm">
                  <div v-if="asset.current_book_value || asset.gross_purchase_amount">
                    <p class="font-semibold text-emerald-700">
                      {{ (asset.current_book_value ?? asset.gross_purchase_amount ?? 0).toLocaleString('vi-VN') }}
                    </p>
                    <p v-if="asset.accumulated_depreciation" class="text-xs text-slate-400">
                      −{{ asset.accumulated_depreciation.toLocaleString('vi-VN') }} đã khấu hao
                    </p>
                  </div>
                  <span v-else class="text-slate-400">—</span>
                </td>
                <td class="table-cell text-sm" :class="isPmOverdue(asset.next_pm_date) ? 'text-red-600 font-semibold' : 'text-slate-600'">
                  {{ formatDate(asset.next_pm_date) }}
                </td>
                <td class="table-cell text-sm" :class="isPmOverdue(asset.byt_reg_expiry) ? 'text-red-600 font-semibold' : 'text-slate-600'">
                  {{ formatDate(asset.byt_reg_expiry) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-else class="flex flex-col items-center justify-center py-16 text-slate-400">
          <svg class="w-12 h-12 mb-3 opacity-40" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M20 7H4a2 2 0 00-2 2v9a2 2 0 002 2h16a2 2 0 002-2V9a2 2 0 00-2-2z" />
          </svg>
          <p class="text-sm">Không có thiết bị nào phù hợp</p>
          <button v-if="activeFilterCount > 0" class="mt-3 text-xs text-blue-500 hover:text-blue-700 underline" @click="resetFilters">
            Xóa bộ lọc để xem tất cả
          </button>
        </div>
      </div>
    </template>

    <BasePagination :pagination="store.pagination" @page-change="goToPage" />

    <!-- ── Import Modal ──────────────────────────────────────────────────── -->
    <div
      v-if="showImport"
      class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4"
      @click.self="closeImport"
    >
      <div class="bg-white rounded-xl w-full max-w-3xl max-h-[90vh] overflow-y-auto">
        <!-- Header -->
        <div class="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <div>
            <h2 class="text-base font-semibold text-gray-800">Import Thiết bị</h2>
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
          <div v-if="importErr" class="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-lg">
            {{ importErr }}
          </div>

          <!-- STEP 1: UPLOAD -->
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

            <div class="text-xs text-gray-500 bg-blue-50 border border-blue-100 rounded-lg px-3 py-2">
              <p class="font-medium text-blue-700 mb-1">Lưu ý trước khi import:</p>
              <ul class="list-disc pl-4 space-y-0.5">
                <li>Các tham chiếu Danh mục / Khoa / Vị trí / Model / NCC phải đã được nhập sẵn (xem trang Dữ liệu tham chiếu).</li>
                <li>Mã tài sản (nội bộ) phải duy nhất — để trống nếu muốn hệ thống tự sinh theo naming_series.</li>
                <li>Mặc định trạng thái vòng đời = <strong>Draft</strong> nếu bỏ trống.</li>
              </ul>
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
            <div class="flex items-center gap-4 text-sm flex-wrap">
              <span class="text-gray-600">Tổng: <strong>{{ previewData.totalRows }}</strong> dòng</span>
              <span class="text-green-700">Hợp lệ: <strong>{{ previewData.validRows }}</strong></span>
              <span v-if="previewData.errors.length" class="text-red-600">
                Lỗi: <strong>{{ previewData.errors.length }}</strong>
              </span>
              <span v-if="previewData.warnings.length" class="text-amber-600">
                Cảnh báo: <strong>{{ previewData.warnings.length }}</strong>
              </span>
              <span class="text-xs text-gray-400 truncate">{{ uploadedFileName }}</span>
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
                    <th v-for="fn in previewData.fieldnames.slice(0, 7)" :key="fn"
                      class="px-3 py-2 text-left font-medium text-gray-500 whitespace-nowrap">
                      {{ fn }}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(row, ri) in previewData.preview" :key="ri"
                    class="border-t border-gray-100 hover:bg-gray-50">
                    <td v-for="fn in previewData.fieldnames.slice(0, 7)" :key="fn"
                      class="px-3 py-1.5 text-gray-700 max-w-[140px] truncate" :title="String(row[fn] ?? '')">
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
                tài sản import thành công
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
  </div>
</template>
