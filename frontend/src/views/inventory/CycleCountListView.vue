<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
// IMM-15 · Kiểm kê tồn kho (Cycle Count) — danh sách phiếu.
import { ref, onMounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useImm15Store } from '@/stores/imm15'
import { listWarehouses } from '@/api/inventory'
import type { Warehouse } from '@/types/inventory'
import PageHeader from '@/components/common/PageHeader.vue'
import FilterToggleButton from '@/components/common/FilterToggleButton.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import { formatCurrency, formatDate } from '@/utils/formatters'
import {
  cycleCountTypeLabel, cycleCountStateLabel, CYCLE_COUNT_STATE_OPTIONS,
} from '@/constants/cycleCountLabels'

const router = useRouter()
const store = useImm15Store()
const { cycleCounts, cycleCountsPagination, cycleCountsLoading, error } = storeToRefs(store)

const PAGE_SIZE = 20
const page = ref(1)
const showFilters = ref(false)
const statusFilter = ref('')
const warehouseFilter = ref('')
const warehouses = ref<Warehouse[]>([])

const total = computed(() => cycleCountsPagination.value.total)

interface Chip { key: 'status' | 'warehouse'; label: string }
const activeChips = computed<Chip[]>(() => {
  const chips: Chip[] = []
  if (statusFilter.value)
    chips.push({ key: 'status', label: cycleCountStateLabel(statusFilter.value) })
  if (warehouseFilter.value) {
    const wh = warehouses.value.find(w => w.name === warehouseFilter.value)
    chips.push({ key: 'warehouse', label: wh?.warehouse_name || warehouseFilter.value })
  }
  return chips
})
const activeFilterCount = computed(() => activeChips.value.length)

function load() {
  store.fetchCycleCounts({
    page: page.value, page_size: PAGE_SIZE,
    status: statusFilter.value, warehouse: warehouseFilter.value,
  })
}

function clearChip(key: string) {
  if (key === 'status') statusFilter.value = ''
  else warehouseFilter.value = ''
}
function resetFilters() {
  statusFilter.value = ''
  warehouseFilter.value = ''
}

watch([statusFilter, warehouseFilter], () => { page.value = 1; load() })

function prevPage() { if (page.value > 1) { page.value--; load() } }
function nextPage() { if (page.value * PAGE_SIZE < total.value) { page.value++; load() } }

function goDetail(name: string) {
  router.push({ name: 'CycleCountDetail', params: { name } })
}

onMounted(async () => {
  load()
  try {
    const r = await listWarehouses({ page: 1, page_size: 100, active_only: 1 })
    warehouses.value = r?.items || []
  } catch { /* filter chỉ là tiện ích — lỗi không chặn danh sách */ }
})
</script>

<template>
  <div class="page-container animate-fade-in">
    <PageHeader
      title="Kiểm kê tồn kho"
      :subtitle="`IMM-15 · Tồn kho phụ tùng — Tổng ${total} phiếu kiểm kê`"
      :breadcrumb="[{ label: 'IMM-15 · Tồn kho phụ tùng', to: '/inventory' }, { label: 'Kiểm kê tồn kho' }]"
    >
      <template #actions>
        <FilterToggleButton v-model="showFilters" :count="activeFilterCount" />
        <button
          class="btn-primary shrink-0"
          @click="router.push({ name: 'CycleCountCreate' })"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          Tạo phiếu kiểm kê
        </button>
      </template>
    </PageHeader>

    <ListFilterBar
      :show="showFilters"
      :chips="activeChips"
      :show-search="false"
      @reset="resetFilters"
      @clear-chip="clearChip"
      @apply="() => { page = 1; load() }"
    >
      <template #fields>
        <div class="form-group">
          <label class="form-label" for="cc-status-filter">Trạng thái</label>
          <select id="cc-status-filter" v-model="statusFilter" class="form-select text-sm">
            <option value="">Tất cả</option>
            <option v-for="o in CYCLE_COUNT_STATE_OPTIONS" :key="o.value" :value="o.value">{{ o.label }}</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label" for="cc-wh-filter">Kho</label>
          <select id="cc-wh-filter" v-model="warehouseFilter" class="form-select text-sm">
            <option value="">Tất cả</option>
            <option v-for="w in warehouses" :key="w.name" :value="w.name">{{ w.warehouse_name }}</option>
          </select>
        </div>
      </template>
    </ListFilterBar>

    <div class="card overflow-hidden">
      <div class="flex items-center justify-between px-4 py-2.5 border-b border-slate-100 bg-slate-50/60 text-xs text-slate-500">
        <span>Hiển thị <strong class="text-slate-700">{{ cycleCounts.length }}</strong> / {{ total }} phiếu</span>
        <button v-if="activeFilterCount > 0" class="text-red-500 hover:text-red-700 font-medium" @click="resetFilters">Xóa tất cả</button>
      </div>

      <!-- Tri-branch: loading / error / (empty|data) -->
      <div v-if="cycleCountsLoading && !cycleCounts.length" class="p-6">
        <SkeletonLoader variant="table" :rows="6" />
      </div>
      <div v-else-if="error" class="flex flex-col items-center justify-center py-16 gap-3">
        <p class="text-sm text-red-600">{{ error }}</p>
        <button class="btn-secondary" @click="load">Thử lại</button>
      </div>
      <div v-else-if="cycleCounts.length === 0" class="flex flex-col items-center justify-center py-16">
        <p class="text-sm text-slate-500">Chưa có phiếu kiểm kê phù hợp.</p>
        <button v-if="activeFilterCount > 0" class="text-xs text-brand-600 hover:text-brand-700 font-medium underline mt-2" @click="resetFilters">
          Xóa bộ lọc để xem tất cả
        </button>
        <button v-else class="btn-primary mt-3" @click="router.push({ name: 'CycleCountCreate' })">Tạo phiếu kiểm kê đầu tiên</button>
      </div>

      <div v-else class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-slate-50 border-b border-slate-100">
            <tr>
              <th class="table-header">Mã phiếu</th>
              <th class="table-header">Kho</th>
              <th class="table-header hidden md:table-cell">Loại kiểm kê</th>
              <th class="table-header hidden lg:table-cell">Ngày</th>
              <th class="table-header text-right">Số dòng lệch</th>
              <th class="table-header text-right hidden md:table-cell">Giá trị lệch</th>
              <th class="table-header text-center">Trạng thái</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-50">
            <tr
              v-for="c in cycleCounts" :key="c.name"
              class="hover:bg-slate-50/70 cursor-pointer transition-all hover:translate-x-0.5 focus-within:bg-slate-50"
              @click="goDetail(c.name)"
            >
              <td class="px-4 py-3 font-mono text-xs text-brand-700 font-semibold">
                <button
                  class="hover:underline focus-visible:ring-2 focus-visible:ring-emerald-500 rounded"
                  :aria-label="`Mở phiếu kiểm kê ${c.name}`"
                  @click.stop="goDetail(c.name)"
                >{{ c.name }}</button>
              </td>
              <td class="px-4 py-3 text-slate-700">{{ c.warehouse_name || c.warehouse }}</td>
              <td class="px-4 py-3 text-slate-600 hidden md:table-cell">{{ cycleCountTypeLabel(c.count_type) }}</td>
              <td class="px-4 py-3 text-xs text-slate-500 hidden lg:table-cell">{{ formatDate(c.count_date) }}</td>
              <td class="px-4 py-3 text-right tabular-nums" :class="(c.variance_count ?? 0) > 0 ? 'text-amber-700 font-semibold' : 'text-slate-500'">
                {{ c.variance_count ?? 0 }}
              </td>
              <td class="px-4 py-3 text-right tabular-nums text-slate-700 hidden md:table-cell">{{ formatCurrency(c.variance_value) }}</td>
              <td class="px-4 py-3 text-center"><StatusBadge :state="c.status" /></td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="total > PAGE_SIZE" class="flex items-center justify-between px-4 py-3 border-t border-slate-100 text-sm text-slate-500">
        <span>{{ (page - 1) * PAGE_SIZE + 1 }}–{{ Math.min(page * PAGE_SIZE, total) }} / {{ total }}</span>
        <div class="flex gap-2">
          <button :disabled="page === 1" class="px-3 py-1 rounded border border-slate-200 disabled:opacity-40 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-emerald-500" @click="prevPage">Trước</button>
          <button :disabled="page * PAGE_SIZE >= total" class="px-3 py-1 rounded border border-slate-200 disabled:opacity-40 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-emerald-500" @click="nextPage">Sau</button>
        </div>
      </div>
    </div>
  </div>
</template>
