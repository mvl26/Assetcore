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
</script>

<template>
  <div class="page-container animate-fade-in">
    <PageHeader
      title="Danh sách Thiết bị"
      :subtitle="`Tổng ${store.pagination.total} thiết bị`"
    >
      <template #actions>
        <FilterToggleButton v-model="showFilters" :count="activeFilterCount" />
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
  </div>
</template>
