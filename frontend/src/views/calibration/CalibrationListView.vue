<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useImm11Store } from '@/stores/imm11'
import { formatAssetDisplay, formatDate } from '@/utils/formatters'
import PageHeader from '@/components/common/PageHeader.vue'
import FilterToggleButton from '@/components/common/FilterToggleButton.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'
import BasePagination from '@/components/common/BasePagination.vue'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'

const router = useRouter()
const route = useRoute()
const store = useImm11Store()

const items = computed(() => store.calibrations)
const pagination = computed(() => store.pagination)
const kpis = computed(() => store.kpis?.kpis ?? null)
const loading = computed(() => store.loading)
const filterStatus = ref('')
const assetFilter = ref<string>((route.query.asset as string) || '')
const showFilters = ref(false)

const CAL_STATUSES = [
  { value: 'Scheduled',            label: 'Đã lên lịch' },
  { value: 'Sent to Lab',          label: 'Đã gửi phòng HC' },
  { value: 'In Progress',          label: 'Đang thực hiện' },
  { value: 'Certificate Received', label: 'Đã nhận chứng nhận' },
  { value: 'Passed',               label: 'Đạt' },
  { value: 'Failed',               label: 'Không đạt' },
  { value: 'Conditionally Passed', label: 'Đạt có điều kiện' },
  { value: 'Cancelled',            label: 'Đã hủy' },
]

interface Chip { key: 'status' | 'asset'; label: string }
const activeChips = computed<Chip[]>(() => {
  const chips: Chip[] = []
  if (filterStatus.value) {
    const s = CAL_STATUSES.find(x => x.value === filterStatus.value)
    chips.push({ key: 'status', label: s?.label ?? filterStatus.value })
  }
  if (assetFilter.value) chips.push({ key: 'asset', label: `TB: ${assetFilter.value}` })
  return chips
})
const activeFilterCount = computed(() => activeChips.value.length)

function clearChip(key: string) {
  if (key === 'status') filterStatus.value = ''
  else assetFilter.value = ''
  load(1)
}

function resetFilters() {
  filterStatus.value = ''
  assetFilter.value = ''
  load(1)
}

function quickFilter(_key: 'status', value: string) {
  if (!value) return
  filterStatus.value = value
  showFilters.value = false
  load(1)
}

async function load(page = 1) {
  await store.fetchList({
    page, page_size: 20,
    status: filterStatus.value || undefined,
    asset: assetFilter.value || undefined,
  })
}

async function loadKpis() {
  await store.fetchKpis()
}

function isOverdue(date: string | null) {
  return date && new Date(date) < new Date()
}

watch(() => route.query.asset, (val) => {
  assetFilter.value = (val as string) || ''
  load(1)
})

onMounted(() => { load(); loadKpis() })
</script>

<template>
  <div class="page-container animate-fade-in space-y-5">
    <PageHeader
      title="Hiệu chuẩn thiết bị"
      :subtitle="`Tổng ${pagination.total ?? items.length} phiếu`"
      :breadcrumb="[{ label: 'IMM-11 · Hiệu chuẩn', to: '/calibration/dashboard' }, { label: 'Danh sách' }]"
    >
      <template #actions>
        <FilterToggleButton v-model="showFilters" :count="activeFilterCount" />
        <button class="btn-ghost text-sm" @click="router.push('/calibration/schedules')">Lịch hiệu chuẩn</button>
        <button class="btn-primary" @click="router.push('/calibration/new')">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          Tạo phiếu
        </button>
      </template>
    </PageHeader>

    <ListFilterBar
      :show="showFilters"
      :chips="activeChips"
      :show-search="false"
      @reset="resetFilters"
      @clear-chip="clearChip"
      @apply="load(1)"
    >
      <template #fields>
        <div class="form-group">
          <label class="form-label">Trạng thái</label>
          <select v-model="filterStatus" class="form-select" @change="load(1)">
            <option value="">Tất cả trạng thái</option>
            <option v-for="s in CAL_STATUSES" :key="s.value" :value="s.value">{{ s.label }}</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Thiết bị</label>
          <input v-model="assetFilter" placeholder="Mã AC Asset..." class="form-input" @keyup.enter="load(1)" />
        </div>
      </template>
    </ListFilterBar>

    <!-- KPI Cards -->
    <div v-if="kpis" class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
      <div class="kpi-card p-4 text-center" style="--kpi-color: #334155">
        <p class="text-xs text-slate-400 mb-1">Tháng này</p>
        <p class="text-2xl font-bold font-display tabular-nums text-slate-700">{{ kpis.total_this_month }}</p>
      </div>
      <div class="kpi-card p-4 text-center" style="--kpi-color: #059669">
        <p class="text-xs text-slate-400 mb-1">Đã qua</p>
        <p class="text-2xl font-bold font-display tabular-nums text-emerald-600">{{ kpis.completed }}</p>
      </div>
      <div class="kpi-card p-4 text-center" style="--kpi-color: #dc2626">
        <p class="text-xs text-slate-400 mb-1">Thất bại</p>
        <p class="text-2xl font-bold font-display tabular-nums text-red-600">{{ kpis.failed }}</p>
      </div>
      <div class="kpi-card p-4 text-center" style="--kpi-color: #2563eb">
        <p class="text-xs text-slate-400 mb-1">Pass rate</p>
        <p class="text-2xl font-bold font-display tabular-nums text-brand-600">{{ kpis.pass_rate_pct }}%</p>
      </div>
      <div class="kpi-card p-4 text-center" style="--kpi-color: #dc2626">
        <p class="text-xs text-slate-400 mb-1">Quá hạn</p>
        <p class="text-2xl font-bold font-display tabular-nums text-red-500">{{ kpis.overdue_assets }}</p>
      </div>
      <div class="kpi-card p-4 text-center" style="--kpi-color: #d97706">
        <p class="text-xs text-slate-400 mb-1">Sắp đến hạn</p>
        <p class="text-2xl font-bold font-display tabular-nums text-amber-600">{{ kpis.due_soon_assets }}</p>
      </div>
    </div>

    <!-- Table -->
    <div class="table-wrapper">
      <!-- Info row -->
      <div class="flex items-center justify-between px-4 py-2.5 border-b border-slate-100 bg-slate-50/60 text-xs text-slate-500">
        <span>Hiển thị <strong class="text-slate-700">{{ items.length }}</strong> / {{ pagination.total }} phiếu</span>
        <button v-if="activeFilterCount > 0" class="text-red-500 hover:text-red-700 font-medium" @click="resetFilters">Xóa tất cả</button>
      </div>
      <div v-if="loading" class="p-4">
        <SkeletonLoader variant="table" :rows="6" />
      </div>
      <div v-else-if="!items.length" class="flex flex-col items-center justify-center py-16 text-slate-400">
        <p class="text-sm font-medium">Chưa có phiếu hiệu chuẩn nào</p>
        <button v-if="activeFilterCount > 0" class="text-xs text-blue-500 hover:text-blue-700 underline mt-2" @click="resetFilters">
          Xóa bộ lọc để xem tất cả
        </button>
      </div>
      <template v-else>
        <!-- Mobile cards (< sm) -->
        <div class="mobile-card-list sm:hidden">
          <div
            v-for="c in items"
            :key="c.name"
            class="mobile-card"
            @click="router.push(`/calibration/${c.name}`)"
          >
            <div class="flex items-center justify-between mb-2">
              <span class="font-mono text-sm font-semibold text-brand-700">{{ c.name }}</span>
              <button @click.stop="quickFilter('status', c.status)">
                <StatusBadge :state="c.status" />
              </button>
            </div>
            <p class="text-sm font-medium text-slate-900 truncate">{{ formatAssetDisplay(c.asset_name, c.asset).main }}</p>
            <div class="flex flex-wrap items-center gap-x-2 gap-y-1 mt-1.5 text-xs text-slate-500">
              <span>{{ c.calibration_type }}</span>
              <span class="text-slate-300">·</span>
              <span>{{ formatDate(c.scheduled_date) }}</span>
              <span v-if="c.overall_result" class="text-slate-300">·</span>
              <StatusBadge v-if="c.overall_result" :state="c.overall_result" />
            </div>
          </div>
          <div v-if="items.length === 0" class="py-12 text-center text-slate-400">
            <p class="text-sm font-medium">Không có dữ liệu</p>
          </div>
        </div>

        <!-- Desktop table (sm+) -->
        <div class="hidden sm:block overflow-x-auto">
          <table class="min-w-full divide-y divide-slate-100">
            <thead>
              <tr>
                <th class="table-header">Mã</th>
                <th class="table-header">Thiết bị</th>
                <th class="table-header">Loại</th>
                <th class="table-header">Trạng thái</th>
                <th class="table-header">Ngày dự kiến</th>
                <th class="table-header">Kết quả</th>
                <th class="table-header">Ngày cal tiếp</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              <tr
                v-for="c in items" :key="c.name"
                class="hover:bg-slate-50 cursor-pointer transition-colors"
                @click="router.push(`/calibration/${c.name}`)"
              >
                <td class="table-cell font-mono text-xs text-slate-500">{{ c.name }}</td>
                <td class="table-cell">
                  <div class="font-medium text-slate-900 truncate max-w-[240px]">
                    {{ formatAssetDisplay(c.asset_name, c.asset).main }}
                  </div>
                  <div v-if="formatAssetDisplay(c.asset_name, c.asset).hasBoth" class="text-xs text-slate-400 font-mono mt-0.5">
                    {{ formatAssetDisplay(c.asset_name, c.asset).sub }}
                  </div>
                </td>
                <td class="table-cell text-slate-600">{{ c.calibration_type }}</td>
                <td class="table-cell">
                  <button @click.stop="quickFilter('status', c.status)">
                    <StatusBadge :state="c.status" />
                  </button>
                </td>
                <td class="table-cell text-slate-600">{{ formatDate(c.scheduled_date) }}</td>
                <td class="table-cell">
                  <StatusBadge v-if="c.overall_result" :state="c.overall_result" />
                  <span v-else class="text-slate-300">—</span>
                </td>
                <td class="table-cell text-xs" :class="isOverdue(c.next_calibration_date) ? 'text-red-600 font-semibold' : 'text-slate-500'">
                  {{ formatDate(c.next_calibration_date) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
    </div>

    <BasePagination :pagination="pagination" @page-change="load" />
  </div>
</template>
