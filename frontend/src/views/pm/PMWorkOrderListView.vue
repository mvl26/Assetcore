<script setup lang="ts">
import DateInput from '@/components/common/DateInput.vue'
import { onMounted, ref, computed, watch } from 'vue'
import { useImm08Store } from '@/stores/imm08'
import { useRouter, useRoute } from 'vue-router'
import { formatAssetDisplay, translateStatus, getStatusColor } from '@/utils/formatters'
import PageHeader from '@/components/common/PageHeader.vue'
import FilterToggleButton from '@/components/common/FilterToggleButton.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'
import BasePagination from '@/components/common/BasePagination.vue'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
import WorkOrderKpiStrip, { type WoKpiItem } from '@/components/common/WorkOrderKpiStrip.vue'
import { useCapabilities } from '@/composables/useCapabilities'

const store = useImm08Store()
const router = useRouter()
const route = useRoute()
// Read-only oversight (opsmgr): chỉ user có pm.create mới thấy nút Tạo phiếu.
const { can } = useCapabilities()
// Core Doc §9.3 — pre-apply filter từ route.query (drill-down từ dashboard).
const statusFilter = ref<string>((route.query.status as string) || '')
const search = ref('')
const dateFrom = ref('')
const dateTo = ref('')
const assetFilter = ref<string>((route.query.asset as string) || '')
// R6 §9.4.3 — date-window drill từ KPI pm_due_7d (?due_before) / overdue (?overdue=1).
const dueBefore = ref<string>((route.query.due_before as string) || '')
const overdueOnly = ref<boolean>(route.query.overdue === '1')
const showFilters = ref<boolean>(!!(route.query.status || route.query.asset || route.query.due_before || route.query.overdue))

const PM_STATUSES = [
  { value: 'Open',                label: 'Mở' },
  { value: 'In Progress',         label: 'Đang thực hiện' },
  { value: 'Overdue',             label: 'Quá hạn' },
  { value: 'Completed',           label: 'Hoàn thành' },
  { value: 'Halted–Major Failure',label: 'Dừng — Lỗi nặng' },
  { value: 'Pending–Device Busy', label: 'Chờ — Thiết bị bận' },
  { value: 'Cancelled',           label: 'Đã hủy' },
]

function buildFilters() {
  const f: Record<string, string | string[]> = {}
  // R6: overdue/due_before là virtual key — BE imm08._normalize_filters dịch sang
  // status=Overdue / due_date<=X (SSOT, list khớp KPI). overdue thắng due_before.
  if (overdueOnly.value) f.overdue = '1'
  else if (dueBefore.value) f.due_before = dueBefore.value
  if (statusFilter.value && !overdueOnly.value) f.status = [statusFilter.value]
  if (dateFrom.value) f.due_date_from = [dateFrom.value]
  if (dateTo.value) f.due_date_to = [dateTo.value]
  if (assetFilter.value) f.asset_ref = assetFilter.value
  return f
}

onMounted(() => {
  store.fetchWorkOrders(buildFilters())
  store.fetchDashboardStats()
})

// KPI strip (docs/fe/08-pm/pm-list.html) — nguồn: dashboard stats thật từ BE.
const kpiItems = computed<WoKpiItem[]>(() => {
  const s = store.dashboardStats?.kpis
  if (!s) return []
  return [
    { label: 'Tổng lịch tháng', value: s.total_scheduled, color: 'primary' },
    { label: 'Quá hạn', value: s.overdue, color: 'danger', trend: s.overdue > 0 ? 'Cần escalate' : 'Đúng tiến độ' },
    { label: 'Hoàn tất đúng hạn', value: s.completed_on_time, color: 'success', trend: `Compliance ${s.compliance_rate_pct}%` },
    { label: 'Trễ trung bình', value: `${s.avg_days_late} ngày`, color: 'warning' },
  ]
})

watch([statusFilter, dateFrom, dateTo, assetFilter, dueBefore, overdueOnly], () => {
  store.fetchWorkOrders(buildFilters())
})

// Sync when navigating from AssetDetail / dashboard drill-down (§9.3)
watch(() => route.query.asset, (val) => {
  assetFilter.value = (val as string) || ''
})
watch(() => route.query.status, (val) => {
  statusFilter.value = (val as string) || ''
})
watch(() => route.query.due_before, (val) => {
  dueBefore.value = (val as string) || ''
})
watch(() => route.query.overdue, (val) => {
  overdueOnly.value = val === '1'
})

const filteredWOs = computed(() => {
  if (!search.value) return store.workOrders
  const q = search.value.toLowerCase()
  return store.workOrders.filter(w =>
    w.name.toLowerCase().includes(q) ||
    (w.asset_name || '').toLowerCase().includes(q) ||
    (w.asset_ref || '').toLowerCase().includes(q)
  )
})

interface PMChip { key: 'status' | 'dateFrom' | 'dateTo' | 'asset' | 'search' | 'overdue' | 'dueBefore'; label: string }
const activeChips = computed<PMChip[]>(() => {
  const chips: PMChip[] = []
  if (overdueOnly.value) chips.push({ key: 'overdue', label: 'Quá hạn' })
  else if (dueBefore.value) chips.push({ key: 'dueBefore', label: `Đến hạn trước ${dueBefore.value}` })
  if (statusFilter.value && !overdueOnly.value) {
    const s = PM_STATUSES.find(x => x.value === statusFilter.value)
    chips.push({ key: 'status', label: s?.label ?? statusFilter.value })
  }
  if (dateFrom.value) chips.push({ key: 'dateFrom', label: `Từ ${dateFrom.value}` })
  if (dateTo.value) chips.push({ key: 'dateTo', label: `Đến ${dateTo.value}` })
  if (assetFilter.value) chips.push({ key: 'asset', label: `Thiết bị: ${assetFilter.value}` })
  if (search.value.trim()) chips.push({ key: 'search', label: `"${search.value.trim()}"` })
  return chips
})
const activeFilterCount = computed(() => activeChips.value.length)

function clearChip(key: string) {
  if (key === 'status') statusFilter.value = ''
  else if (key === 'dateFrom') dateFrom.value = ''
  else if (key === 'dateTo') dateTo.value = ''
  else if (key === 'asset') assetFilter.value = ''
  else if (key === 'overdue') overdueOnly.value = false
  else if (key === 'dueBefore') dueBefore.value = ''
  else search.value = ''
}

function resetFilters() {
  statusFilter.value = ''
  dateFrom.value = ''
  dateTo.value = ''
  assetFilter.value = ''
  dueBefore.value = ''
  overdueOnly.value = false
  search.value = ''
  store.fetchWorkOrders({})
}

function applyFilters() {
  store.fetchWorkOrders(buildFilters())
}

function quickFilter(_key: 'status', value: string) {
  if (!value) return
  statusFilter.value = value
  showFilters.value = false
}
</script>

<template>
  <div class="page-container animate-fade-in">
    <PageHeader
      title="Phiếu Bảo trì định kỳ"
      :subtitle="`Tổng ${store.pagination.total ?? filteredWOs.length} phiếu`"
      :breadcrumb="[{ label: 'IMM-08 · Bảo trì', to: '/pm/dashboard' }, { label: 'Danh sách' }]"
    >
      <template #actions>
        <FilterToggleButton v-model="showFilters" :count="activeFilterCount" />
        <button v-if="can('pm.create')" class="btn-primary" @click="router.push('/pm/work-orders/new')">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          Tạo phiếu bảo trì
        </button>
      </template>
    </PageHeader>

    <WorkOrderKpiStrip :items="kpiItems" />

    <ListFilterBar
      :show="showFilters"
      :chips="activeChips"
      v-model:search="search"
      search-placeholder="Tìm theo mã WO, tên thiết bị..."
      @reset="resetFilters"
      @clear-chip="clearChip"
      @apply="applyFilters"
    >
      <template #fields>
        <div class="form-group">
          <label class="form-label">Trạng thái</label>
          <select v-model="statusFilter" class="form-select">
            <option value="">Tất cả</option>
            <option v-for="s in PM_STATUSES" :key="s.value" :value="s.value">{{ s.label }}</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Từ ngày</label>
          <DateInput v-model="dateFrom" class="form-input" />
        </div>
        <div class="form-group">
          <label class="form-label">Đến ngày</label>
          <DateInput v-model="dateTo" class="form-input" />
        </div>
        <div class="form-group">
          <label class="form-label">Thiết bị</label>
          <input v-model="assetFilter" placeholder="Mã AC Asset..." class="form-input" />
        </div>
      </template>
    </ListFilterBar>

    <!-- Loading skeleton -->
    <div v-if="store.loading" class="table-wrapper">
      <SkeletonLoader variant="table" :rows="6" />
    </div>

    <!-- Error -->
    <div v-else-if="store.error" class="alert-error">
      <svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <span class="flex-1">{{ store.error }}</span>
      <button class="text-xs font-semibold underline hover:no-underline" @click="store.fetchWorkOrders(buildFilters())">Thử lại</button>
    </div>

    <!-- Table -->
    <template v-else>
      <!-- Mobile cards (< sm) -->
      <div class="mobile-card-list sm:hidden">
        <div class="flex items-center justify-between text-xs text-slate-500 pb-1">
          <span>Hiển thị <strong class="text-slate-700">{{ filteredWOs.length }}</strong> phiếu</span>
          <button v-if="activeFilterCount > 0" class="text-red-500 font-medium" @click="resetFilters">Xóa tất cả</button>
        </div>
        <div
          v-for="wo in filteredWOs"
          :key="wo.name"
          class="mobile-card"
          @click="router.push(`/pm/work-orders/${wo.name}`)"
        >
          <div class="flex items-center justify-between mb-2">
            <span class="font-mono text-sm font-semibold text-brand-700">{{ wo.name }}</span>
            <button
              :class="['px-2.5 py-0.5 rounded-full text-xs font-medium', getStatusColor(wo.status)]"
              @click.stop="quickFilter('status', wo.status)"
            >{{ translateStatus(wo.status) }}</button>
          </div>
          <p class="text-sm font-medium text-slate-900 truncate">{{ formatAssetDisplay(wo.asset_name, wo.asset_ref).main }}</p>
          <div class="flex flex-wrap items-center gap-x-2 gap-y-1 mt-1.5 text-xs text-slate-500">
            <span v-if="wo.pm_type">{{ wo.pm_type }}</span>
            <span class="text-slate-300">·</span>
            <span :class="wo.is_late ? 'text-red-600 font-semibold' : ''">{{ wo.due_date || '—' }}</span>
            <span v-if="wo.is_late" class="text-red-500">Quá hạn</span>
          </div>
        </div>
        <div v-if="filteredWOs.length === 0" class="py-12 text-center text-slate-400">
          <p class="text-sm font-medium">Không tìm thấy phiếu bảo trì</p>
        </div>
      </div>

      <!-- Desktop table (sm+) -->
      <div class="hidden sm:block table-wrapper">
        <table class="min-w-full divide-y divide-slate-100">
          <thead>
            <tr>
              <th class="table-header">Mã WO</th>
              <th class="table-header">Thiết bị</th>
              <th class="table-header">Loại PM</th>
              <th class="table-header">Đến hạn</th>
              <th class="table-header">Kỹ thuật viên</th>
              <th class="table-header">Trạng thái</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-50">
            <tr
              v-for="wo in filteredWOs"
              :key="wo.name"
              class="hover:bg-slate-50 cursor-pointer transition-all hover:translate-x-0.5"
              @click="router.push(`/pm/work-orders/${wo.name}`)"
            >
              <td class="table-cell">
                <div class="font-mono text-sm font-semibold text-brand-700">{{ wo.name }}</div>
              </td>
              <td class="table-cell">
                <div class="font-medium text-slate-900 truncate max-w-[240px]">
                  {{ formatAssetDisplay(wo.asset_name, wo.asset_ref).main }}
                </div>
                <div
                  v-if="formatAssetDisplay(wo.asset_name, wo.asset_ref).hasBoth"
                  class="text-xs text-slate-400 font-mono mt-0.5">
                  {{ formatAssetDisplay(wo.asset_name, wo.asset_ref).sub }}
                </div>
              </td>
              <td class="table-cell text-slate-600">{{ wo.pm_type || '—' }}</td>
              <td class="table-cell">
                <span :class="wo.is_late ? 'text-red-600 font-semibold' : 'text-slate-600'">
                  {{ wo.due_date || '—' }}
                </span>
                <div v-if="wo.is_late" class="text-xs text-red-500 mt-0.5">Quá hạn</div>
              </td>
              <td class="table-cell">
                <div class="text-slate-700">{{ wo.assigned_to_name || wo.assigned_to || '—' }}</div>
                <div v-if="wo.assigned_to && wo.assigned_to_name" class="text-xs text-slate-400">{{ wo.assigned_to }}</div>
              </td>
              <td class="table-cell">
                <button
                  :class="['inline-block px-2.5 py-1 rounded-full text-xs font-medium transition-all hover:ring-2 hover:ring-offset-1 hover:ring-current/50', getStatusColor(wo.status)]"
                  :title="`Lọc: ${translateStatus(wo.status)}`"
                  @click.stop="quickFilter('status', wo.status)"
                >{{ translateStatus(wo.status) }}</button>
              </td>
            </tr>

            <!-- Empty state -->
            <tr v-if="filteredWOs.length === 0">
              <td colspan="6" class="py-16 text-center">
                <div class="flex flex-col items-center gap-3 text-slate-400">
                  <svg class="w-12 h-12 text-slate-200" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                  </svg>
                  <p class="text-sm font-medium text-slate-500">Không tìm thấy phiếu bảo trì</p>
                  <p class="text-xs text-slate-400">Thử thay đổi bộ lọc hoặc từ khóa tìm kiếm</p>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <BasePagination :pagination="store.pagination" @page-change="p => store.fetchWorkOrders({}, p)" />
  </div>
</template>

<style scoped>
/* Fade transition for table rows on filter change */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
