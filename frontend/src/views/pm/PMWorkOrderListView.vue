<script setup lang="ts">
import DateInput from '@/components/common/DateInput.vue'
import { onMounted, ref, computed, watch } from 'vue'
import { useImm08Store } from '@/stores/imm08'
import { useRouter, useRoute } from 'vue-router'
import { formatAssetDisplay, translateStatus, getStatusColor } from '@/utils/formatters'

const store = useImm08Store()
const router = useRouter()
const route = useRoute()
const statusFilter = ref('')
const search = ref('')
const dateFrom = ref('')
const dateTo = ref('')
const assetFilter = ref<string>((route.query.asset as string) || '')
const showFilters = ref(false)

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
  if (statusFilter.value) f.status = [statusFilter.value]
  if (dateFrom.value) f.due_date_from = [dateFrom.value]
  if (dateTo.value) f.due_date_to = [dateTo.value]
  if (assetFilter.value) f.asset_ref = assetFilter.value
  return f
}

onMounted(() => store.fetchWorkOrders(buildFilters()))

watch([statusFilter, dateFrom, dateTo, assetFilter], () => {
  store.fetchWorkOrders(buildFilters())
})

// Sync when navigating from AssetDetail
watch(() => route.query.asset, (val) => {
  assetFilter.value = (val as string) || ''
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

interface PMChip { key: 'status' | 'dateFrom' | 'dateTo' | 'asset' | 'search'; label: string }
const activeChips = computed<PMChip[]>(() => {
  const chips: PMChip[] = []
  if (statusFilter.value) {
    const s = PM_STATUSES.find(x => x.value === statusFilter.value)
    chips.push({ key: 'status', label: s?.label ?? statusFilter.value })
  }
  if (dateFrom.value) chips.push({ key: 'dateFrom', label: `Từ ${dateFrom.value}` })
  if (dateTo.value) chips.push({ key: 'dateTo', label: `Đến ${dateTo.value}` })
  if (assetFilter.value) chips.push({ key: 'asset', label: `TB: ${assetFilter.value}` })
  if (search.value.trim()) chips.push({ key: 'search', label: `"${search.value.trim()}"` })
  return chips
})
const activeFilterCount = computed(() => activeChips.value.length)

function clearChip(key: PMChip['key']) {
  if (key === 'status') statusFilter.value = ''
  else if (key === 'dateFrom') dateFrom.value = ''
  else if (key === 'dateTo') dateTo.value = ''
  else if (key === 'asset') assetFilter.value = ''
  else search.value = ''
}

function resetFilters() {
  statusFilter.value = ''
  dateFrom.value = ''
  dateTo.value = ''
  assetFilter.value = ''
  search.value = ''
  store.fetchWorkOrders({})
}

function quickFilter(_key: 'status', value: string) {
  if (!value) return
  statusFilter.value = value
  showFilters.value = false
}
</script>

<template>
  <div class="page-container animate-fade-in">
<!-- Header -->
    <div class="flex items-start justify-between mb-5">
      <div>
        <h1 class="text-2xl font-bold text-slate-900">Phiếu Bảo trì định kỳ</h1>
        <p class="text-sm text-slate-500 mt-1">
          Tổng <strong class="text-slate-700">{{ store.pagination.total ?? filteredWOs.length }}</strong> phiếu
        </p>
      </div>
      <div class="flex items-center gap-2 shrink-0">
        <button
          class="relative flex items-center gap-1.5 px-3 py-2 text-sm font-medium rounded-lg border transition-colors"
          :class="showFilters
            ? 'bg-brand-50 border-brand-300 text-brand-700'
            : 'bg-white border-slate-300 text-slate-600 hover:border-slate-400'"
          @click="showFilters = !showFilters"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M3 4h18M7 8h10M11 12h2M9 16h6" />
          </svg>
          Bộ lọc
          <span
v-if="activeFilterCount > 0"
            class="inline-flex items-center justify-center w-4 h-4 text-[10px] font-bold rounded-full bg-blue-500 text-white">
            {{ activeFilterCount }}
          </span>
          <svg
class="w-3.5 h-3.5 transition-transform duration-200" :class="showFilters ? 'rotate-180' : ''"
               fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
          </svg>
        </button>
        <button class="btn-primary shrink-0" @click="router.push('/pm/work-orders/new')">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          Tạo phiếu bảo trì
        </button>
      </div>
    </div>

    <!-- Active chips -->
    <Transition
      enter-active-class="transition-all duration-200 ease-out"
      enter-from-class="opacity-0 -translate-y-1"
      enter-to-class="opacity-100 translate-y-0"
      leave-active-class="transition-all duration-150 ease-in"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div v-if="activeChips.length > 0 && !showFilters" class="flex flex-wrap items-center gap-2 mb-4">
        <span class="text-xs text-slate-400 font-medium">Đang lọc:</span>
        <button
v-for="chip in activeChips" :key="chip.key"
          class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200 hover:bg-blue-100 transition-colors"
          @click="clearChip(chip.key)"
        >
          {{ chip.label }}
          <svg class="w-3 h-3 opacity-60" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
        <button class="text-xs text-slate-400 hover:text-red-500 underline underline-offset-2" @click="resetFilters">
          Xóa tất cả
        </button>
      </div>
    </Transition>

    <!-- Collapsible filter panel -->
    <Transition
      enter-active-class="transition-all duration-200 ease-out overflow-hidden"
      enter-from-class="opacity-0 max-h-0"
      enter-to-class="opacity-100 max-h-60"
      leave-active-class="transition-all duration-150 ease-in overflow-hidden"
      leave-from-class="opacity-100 max-h-60"
      leave-to-class="opacity-0 max-h-0"
    >
      <div v-show="showFilters" class="card mb-5 p-4 space-y-3">
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          <div class="form-group">
            <label for="pm-search" class="form-label">Tìm kiếm</label>
            <input id="pm-search" v-model="search" placeholder="Mã WO, thiết bị..." class="form-input" />
          </div>
          <div class="form-group">
            <label for="pm-status" class="form-label">Trạng thái</label>
            <select id="pm-status" v-model="statusFilter" class="form-select">
              <option value="">Tất cả</option>
              <option v-for="s in PM_STATUSES" :key="s.value" :value="s.value">{{ s.label }}</option>
            </select>
          </div>
          <div class="form-group">
            <label for="pm-date-from" class="form-label">Từ ngày</label>
            <DateInput id="pm-date-from" v-model="dateFrom" class="form-input" />
          </div>
          <div class="form-group">
            <label for="pm-date-to" class="form-label">Đến ngày</label>
            <DateInput id="pm-date-to" v-model="dateTo" class="form-input" />
          </div>
          <div class="form-group">
            <label for="pm-asset" class="form-label">Thiết bị</label>
            <input id="pm-asset" v-model="assetFilter" placeholder="Mã AC Asset..." class="form-input" />
          </div>
        </div>
        <div v-if="activeChips.length > 0" class="flex flex-wrap items-center gap-2 pt-3 border-t border-slate-100">
          <span class="text-xs text-slate-400 font-medium">Đang lọc:</span>
          <button
v-for="chip in activeChips" :key="chip.key"
            class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200 hover:bg-blue-100 transition-colors"
            @click="clearChip(chip.key)"
          >
            {{ chip.label }}
            <svg class="w-3 h-3 opacity-60" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
          <button class="text-xs text-slate-400 hover:text-red-500 underline underline-offset-2" @click="resetFilters">Xóa tất cả</button>
        </div>
      </div>
    </Transition>

    <!-- Loading skeleton -->
    <div v-if="store.loading" class="card">
      <div v-for="i in 6" :key="i" class="flex gap-4 py-3 border-b border-slate-100 last:border-0 animate-pulse">
        <div class="h-4 bg-slate-100 rounded w-28" />
        <div class="h-4 bg-slate-100 rounded flex-1" />
        <div class="h-4 bg-slate-100 rounded w-20" />
        <div class="h-4 bg-slate-100 rounded w-24" />
      </div>
    </div>

    <!-- Table -->
    <div v-else class="table-wrapper">
      <table class="min-w-full divide-y divide-slate-100">
        <thead>
          <tr>
            <th class="table-header">Mã WO</th>
            <th class="table-header">Thiết bị</th>
            <th class="table-header">Loại PM</th>
            <th class="table-header">Đến hạn</th>
            <th class="table-header">KTV</th>
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
              <div class="font-mono text-sm font-semibold text-blue-700">{{ wo.name }}</div>
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
              >
{{ translateStatus(wo.status) }}
</button>
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

    <!-- Pagination -->
    <div v-if="store.pagination.total_pages > 1" class="flex items-center justify-between mt-4">
      <span class="text-sm text-slate-500">Trang {{ store.pagination.page }}/{{ store.pagination.total_pages }}</span>
      <div class="flex gap-1">
        <button
          v-for="p in store.pagination.total_pages"
          :key="p"
          :class="['px-3 py-1 rounded text-sm border transition-colors', p === store.pagination.page ? 'bg-blue-600 text-white border-blue-600' : 'border-slate-300 hover:bg-slate-50']"
          @click="store.fetchWorkOrders({}, p)"
        >
{{ p }}
</button>
      </div>
    </div>
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
