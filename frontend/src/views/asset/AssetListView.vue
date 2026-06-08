<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
import { ref, onMounted, computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAssetStore, useRefDataStore } from '@/stores/imm00'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import FilterToggleButton from '@/components/common/FilterToggleButton.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'
import BasePagination from '@/components/common/BasePagination.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import type { LifecycleStatus, AssetListParams } from '@/types/imm00'
import { BYT_EXPIRY_CHIP_LABEL } from '@/constants/labels'
import { MAX_LABEL_BATCH } from '@/constants/label'
import { useImportWizard } from '@/composables/useImportWizard'
import ImportWizardModal from '@/components/import/ImportWizardModal.vue'
import { useCapabilities } from '@/composables/useCapabilities'

const router = useRouter()
const route = useRoute()
const store = useAssetStore()
const refData = useRefDataStore()
const { can } = useCapabilities()
// D6 (ADR-IMM00-QR-SCAN-ACTION, phương án B): in nhãn = quyền PRINT (DocPerm
// print=1 sẵn cho KTV/QL vật tư) → gate asset.PRINT, KHÔNG còn asset.write (chỉ
// Super Admin). Mirror route AssetLabelPrint requiredCapabilities:['asset.print']
// + BE get_asset_label_data_batch/mark_label_printed require('asset.print').
const canPrintLabel = computed(() => can('asset.print'))

const showFilters = ref(false)

// Core Doc §9.3 — keys cho phép pre-apply từ route.query (drill-down từ dashboard).
// byt_status (BR-00-17, NĐ98): drill tile "ĐK Bộ Y tế sắp/đã hết hạn" → list lọc.
const QUERY_FILTER_KEYS = ['lifecycle_status', 'department', 'asset_category', 'gmdn_code', 'search', 'byt_status'] as const

/**
 * Đọc route.query → áp vào filters (Core Doc §9.3). Trả true nếu có filter nào
 * được set từ query (để quyết định mở panel + dùng cleanParams khi fetch).
 */
function applyQueryToFilters(): boolean {
  let touched = false
  const f = filters.value as Record<string, unknown>
  for (const key of QUERY_FILTER_KEYS) {
    const raw = route.query[key]
    const val = Array.isArray(raw) ? raw[0] : raw
    if (typeof val === 'string' && val) {
      f[key] = val
      touched = true
    }
  }
  if (touched) {
    filters.value.page = 1
    showFilters.value = true // hiện chip filter để user thấy + xoá được
  }
  return touched
}

const filters = ref<AssetListParams>({
  lifecycle_status: '',
  department: '',
  location: '',
  asset_category: '',
  gmdn_code: '',
  search: '',
  byt_status: undefined,
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
  // BR-00-17: forward byt_status xuống list_assets (param khớp signature BE).
  if (filters.value.byt_status) p.byt_status = filters.value.byt_status
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
  // BR-00-17 (NĐ98): chip ĐK BYT — nhãn VI qua SSoT BYT_EXPIRY_CHIP_LABEL.
  const byt = filters.value.byt_status
  if (byt && byt in BYT_EXPIRY_CHIP_LABEL) {
    chips.push({ key: 'byt_status', label: BYT_EXPIRY_CHIP_LABEL[byt] })
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
  filters.value = { lifecycle_status: '', department: '', location: '', asset_category: '', gmdn_code: '', search: '', byt_status: undefined, page: 1, page_size: 20 }
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
  // Core Doc §9.3 — pre-apply filter từ route.query (drill-down) TRƯỚC khi fetch.
  const hasQueryFilter = applyQueryToFilters()
  await Promise.all([
    store.fetchList(hasQueryFilter ? cleanParams.value : undefined),
    refData.fetchAll(),
  ])
})

// Core Doc §9.3 — điều hướng drill-down lần 2 (cùng route, query khác) → re-apply.
watch(
  () => route.query,
  () => {
    if (applyQueryToFilters()) {
      store.fetchList(cleanParams.value)
    }
  },
)

// ── Import / Export ──────────────────────────────────────────────────────────
const importWizard = useImportWizard('AC Asset', () => store.fetchList(cleanParams.value))
const openImport = importWizard.open
const doExport = importWizard.doExport

const IMPORT_NOTICE = [
  'Các tham chiếu Danh mục / Khoa / Vị trí / Model / NCC phải đã được nhập sẵn (xem trang Dữ liệu tham chiếu).',
  // ADR-IMM00-ASSETCODE D4: nhãn chuẩn "Mã tài sản"; chỉ chữ/số và . _ - /
  // (không khoảng trắng/dấu). Để trống = hệ thống tự sinh.
  '<strong>Mã tài sản</strong> phải duy nhất, chỉ gồm chữ, số và các ký tự . _ - / (không khoảng trắng, không dấu) — để trống nếu muốn hệ thống tự sinh.',
  // V1-D: phân biệt rõ với Số serial NSX để user không nhập serial vào ô mã.
  '<strong>Số serial NSX</strong> là số serial của nhà sản xuất (khác Mã tài sản) — không bắt buộc, nhưng nếu nhập phải duy nhất.',
  'Mặc định trạng thái vòng đời = <strong>Draft</strong> nếu bỏ trống.',
]

// ── A4: chọn nhiều + in nhãn QR hàng loạt ───────────────────────────────────────
// selectedNames giữ ĐÚNG thứ tự bấm chọn (không reorder) → trang in giữ thứ tự.
const selectedNames = ref<string[]>([])
function toggleSelect(name: string) {
  const i = selectedNames.value.indexOf(name)
  if (i >= 0) selectedNames.value.splice(i, 1)
  else selectedNames.value.push(name)
}
function isSelected(name: string): boolean {
  return selectedNames.value.includes(name)
}
function clearSelection() {
  selectedNames.value = []
}
const allOnPageSelected = computed(() =>
  store.assets.length > 0 && store.assets.every(a => selectedNames.value.includes(a.name)),
)
function toggleSelectAllOnPage() {
  if (allOnPageSelected.value) {
    const pageNames = new Set(store.assets.map(a => a.name))
    selectedNames.value = selectedNames.value.filter(n => !pageNames.has(n))
  } else {
    for (const a of store.assets) if (!selectedNames.value.includes(a.name)) selectedNames.value.push(a.name)
  }
}
// Vòng B (BR-00-33): vượt cap → nút disabled + user KHÔNG bao giờ gửi request 413.
// SSoT @/constants/label.MAX_LABEL_BATCH (đồng bộ BE _MAX_LABEL_BATCH).
const overLabelLimit = computed(() => selectedNames.value.length > MAX_LABEL_BATCH)
function printBatchLabels() {
  // disabled-guard: rỗng → no-op; vượt cap → KHÔNG điều hướng (chặn request 413).
  if (!selectedNames.value.length || overLabelLimit.value) return
  router.push({ name: 'AssetLabelPrint', query: { names: selectedNames.value.join(',') } })
}

// Phơi bày cho test (chip drill BYT + batch-select A4).
defineExpose({ clearChip, activeChips, toggleSelect, selectedNames, clearSelection })
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
          v-if="canPrintLabel"
          class="px-3 py-2 text-sm border rounded-lg flex items-center gap-1.5 transition-colors"
          :class="(selectedNames.length && !overLabelLimit)
            ? 'border-emerald-300 text-emerald-700 hover:bg-emerald-50'
            : 'border-gray-200 text-gray-400 cursor-not-allowed'"
          :disabled="!selectedNames.length || overLabelLimit"
          :title="overLabelLimit
            ? `Chỉ in tối đa ${MAX_LABEL_BATCH} nhãn mỗi lần. Vui lòng chọn ít hơn.`
            : (selectedNames.length
              ? `In nhãn QR cho ${selectedNames.length} thiết bị đã chọn`
              : 'Chọn ít nhất 1 thiết bị (ô chọn ở cột đầu) để in nhãn hàng loạt')"
          @click="printBatchLabels"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round"
              d="M4 4h6v6H4V4zm10 0h6v6h-6V4zM4 14h6v6H4v-6zm13 0h3m-3 3h3m-3 3h3" />
          </svg>
          In nhãn hàng loạt<span v-if="selectedNames.length"> ({{ selectedNames.length }})</span>
        </button>
        <!-- Vòng B (BR-00-33): hint VI khi vượt cap số nhãn / lần (role=alert). -->
        <span
          v-if="canPrintLabel && overLabelLimit"
          class="text-xs text-amber-700"
          role="alert"
        >
          Chỉ in tối đa {{ MAX_LABEL_BATCH }} nhãn mỗi lần. Vui lòng chọn ít hơn.
        </span>
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
            <div class="flex items-center gap-2">
              <input
                v-if="canPrintLabel"
                type="checkbox"
                class="h-4 w-4 rounded border-slate-300 text-emerald-600 focus:ring-emerald-500"
                :checked="isSelected(asset.name)"
                :aria-label="`Chọn thiết bị ${asset.asset_name}`"
                @click.stop
                @change="toggleSelect(asset.name)"
              />
              <span class="font-mono text-sm font-semibold text-brand-700">{{ asset.name }}</span>
            </div>
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
                <th v-if="canPrintLabel" class="table-header w-10">
                  <input
                    type="checkbox"
                    class="h-4 w-4 rounded border-slate-300 text-emerald-600 focus:ring-emerald-500"
                    :checked="allOnPageSelected"
                    aria-label="Chọn tất cả thiết bị trên trang"
                    @change="toggleSelectAllOnPage"
                  />
                </th>
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
                :class="isSelected(asset.name) ? 'bg-emerald-50/60' : ''"
                @click="router.push(`/assets/${asset.name}`)"
              >
                <td v-if="canPrintLabel" class="table-cell w-10" @click.stop>
                  <input
                    type="checkbox"
                    class="h-4 w-4 rounded border-slate-300 text-emerald-600 focus:ring-emerald-500"
                    :checked="isSelected(asset.name)"
                    :aria-label="`Chọn thiết bị ${asset.asset_name}`"
                    @change="toggleSelect(asset.name)"
                  />
                </td>
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

    <ImportWizardModal
      :ctx="importWizard"
      title="Import Thiết bị"
      unit="tài sản"
      :notice="IMPORT_NOTICE"
      :preview-columns="7"
    />
  </div>
</template>
