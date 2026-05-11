<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { listStockLevels } from '@/api/inventory'
import type { StockRow } from '@/types/inventory'
import SmartSelect from '@/components/common/SmartSelect.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import FilterToggleButton from '@/components/common/FilterToggleButton.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'

const route = useRoute()
const router = useRouter()

const rows = ref<StockRow[]>([])
const total = ref(0)
const page = ref(1)
const PAGE_SIZE = 50
const loading = ref(false)
const showFilters = ref(false)

const warehouseFilter = ref('')
const warehouseName = ref('')
const lowOnly = ref(route.query.low === '1')

interface Chip { key: 'warehouse' | 'low'; label: string }
const activeChips = computed<Chip[]>(() => {
  const chips: Chip[] = []
  if (warehouseFilter.value) chips.push({ key: 'warehouse', label: `Kho: ${warehouseName.value || warehouseFilter.value}` })
  if (lowOnly.value) chips.push({ key: 'low', label: 'Dưới mức min' })
  return chips
})
const activeFilterCount = computed(() => activeChips.value.length)

function clearChip(key: string) {
  if (key === 'warehouse') { warehouseFilter.value = ''; warehouseName.value = '' }
  else lowOnly.value = false
  page.value = 1; load()
}

function resetFilters() {
  warehouseFilter.value = ''
  warehouseName.value = ''
  lowOnly.value = false
  page.value = 1; load()
}

function quickFilterWarehouse(warehouse: string, name: string) {
  if (!warehouse) return
  warehouseFilter.value = warehouse
  warehouseName.value = name
  showFilters.value = false
  page.value = 1; load()
}

async function load() {
  loading.value = true
  try {
    const r = await listStockLevels({
      page: page.value, page_size: PAGE_SIZE,
      warehouse: warehouseFilter.value,
      low_only: lowOnly.value ? 1 : 0,
    })
    rows.value = r?.items || []
    total.value = r?.pagination?.total || 0
  } finally { loading.value = false }
}

watch([warehouseFilter, lowOnly], () => { page.value = 1; load() })

function vnd(v?: number) {
  if (!v) return '—'
  return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(v)
}
function formatDt(d?: string) { return d ? new Date(d).toLocaleString('vi-VN') : '—' }

function prevPage() { if (page.value > 1) { page.value--; load() } }
function nextPage() { if (page.value * PAGE_SIZE < total.value) { page.value++; load() } }

onMounted(load)
</script>

<template>
  <div class="page-container animate-fade-in">
    <PageHeader title="Tồn kho" :subtitle="`Tổng ${total} dòng tồn (phụ tùng × kho)`">
      <template #actions>
        <FilterToggleButton v-model="showFilters" :count="activeFilterCount" />
        <button class="btn-primary shrink-0" @click="router.push('/stock-movements/new')">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          Phiếu mới
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
          <label for="sl-warehouse-filter" class="form-label">Kho</label>
          <SmartSelect id="sl-warehouse-filter" v-model="warehouseFilter" doctype="AC Warehouse" placeholder="Tất cả kho..." />
        </div>
        <div class="form-group">
          <label class="form-label">&nbsp;</label>
          <div class="flex items-center gap-3">
            <input id="low-only" v-model="lowOnly" type="checkbox" class="h-4 w-4 text-red-600 rounded" />
            <label for="low-only" class="text-sm text-slate-700">Chỉ tồn dưới mức min</label>
          </div>
        </div>
      </template>
    </ListFilterBar>

    <div class="card overflow-hidden">
      <!-- Info row -->
      <div class="flex items-center justify-between px-4 py-2.5 border-b border-slate-100 bg-slate-50/60 text-xs text-slate-500">
        <span>Hiển thị <strong class="text-slate-700">{{ rows.length }}</strong> / {{ total }} dòng</span>
        <button v-if="activeFilterCount > 0" class="text-red-500 hover:text-red-700 font-medium" @click="resetFilters">Xóa tất cả</button>
      </div>

      <div v-if="loading && !rows.length" class="text-center py-12 text-slate-400">Đang tải...</div>
      <div v-else-if="rows.length === 0" class="flex flex-col items-center justify-center py-16 text-slate-400">
        <p class="text-sm">Không có dữ liệu tồn.</p>
        <button v-if="activeFilterCount > 0" class="text-xs text-blue-500 hover:text-blue-700 underline mt-2" @click="resetFilters">
          Xóa bộ lọc để xem tất cả
        </button>
      </div>

      <div v-else class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-slate-50 border-b border-slate-100">
            <tr>
              <th class="px-4 py-3 text-left text-xs font-semibold text-slate-500">Kho</th>
              <th class="px-4 py-3 text-left text-xs font-semibold text-slate-500">Phụ tùng</th>
              <th class="px-4 py-3 text-right text-xs font-semibold text-slate-500">Tồn</th>
              <th class="px-4 py-3 text-right text-xs font-semibold text-slate-500 hidden md:table-cell">Giữ chỗ</th>
              <th class="px-4 py-3 text-right text-xs font-semibold text-slate-500">Còn lại</th>
              <th class="px-4 py-3 text-right text-xs font-semibold text-slate-500 hidden lg:table-cell">Min</th>
              <th class="px-4 py-3 text-right text-xs font-semibold text-slate-500 hidden lg:table-cell">Giá trị</th>
              <th class="px-4 py-3 text-left text-xs font-semibold text-slate-500 hidden md:table-cell">Giao dịch cuối</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-50">
            <tr
v-for="r in rows" :key="r.name"
              :class="['hover:bg-slate-50/70 cursor-pointer transition-all hover:translate-x-0.5', r.is_low ? 'bg-red-50/30' : '']"
              @click="router.push(`/spare-parts/${r.spare_part}`)"
            >
              <td class="px-4 py-3">
                <button
                  class="text-sm text-slate-700 hover:underline decoration-dotted underline-offset-2 text-left"
                  :title="`Lọc: ${r.warehouse_name || r.warehouse_code}`"
                  @click.stop="quickFilterWarehouse(r.warehouse, r.warehouse_name || r.warehouse_code || r.warehouse)"
                >
{{ r.warehouse_name || r.warehouse_code }}
</button>
                <p v-if="r.warehouse_code && r.warehouse_code !== r.warehouse_name" class="text-[10px] text-slate-400 font-mono">{{ r.warehouse_code }}</p>
              </td>
              <td class="px-4 py-3">
                <p class="font-medium text-slate-800">{{ r.part_name }}</p>
                <div class="flex items-center gap-1 mt-0.5">
                  <p class="text-[11px] text-slate-400 font-mono">{{ r.spare_part }}</p>
                  <span v-if="r.is_critical" class="text-[9px] px-1 py-0 rounded bg-red-50 text-red-700 font-bold">!</span>
                </div>
              </td>
              <td
class="px-4 py-3 text-right font-semibold"
                  :class="r.is_low ? 'text-red-600' : 'text-slate-800'">
                {{ r.qty_on_hand }} <span class="text-xs font-normal text-slate-400">{{ r.uom }}</span>
              </td>
              <td class="px-4 py-3 text-right text-slate-500 hidden md:table-cell">{{ r.reserved_qty }}</td>
              <td class="px-4 py-3 text-right text-emerald-600 font-medium">{{ r.available_qty }}</td>
              <td class="px-4 py-3 text-right text-xs text-slate-400 hidden lg:table-cell">
                {{ r.min_level || '—' }}
                <span v-if="r.is_low" class="ml-1 text-red-500 font-bold">Low</span>
              </td>
              <td class="px-4 py-3 text-right text-sm text-slate-600 hidden lg:table-cell">{{ vnd(r.stock_value) }}</td>
              <td class="px-4 py-3 text-xs text-slate-400 hidden md:table-cell">{{ formatDt(r.last_movement_date) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="total > PAGE_SIZE" class="flex items-center justify-between px-4 py-3 border-t border-slate-100 text-sm text-slate-500">
        <span>{{ (page - 1) * PAGE_SIZE + 1 }}–{{ Math.min(page * PAGE_SIZE, total) }} / {{ total }}</span>
        <div class="flex gap-2">
          <button :disabled="page === 1" class="px-3 py-1 rounded border border-slate-200 disabled:opacity-40 hover:bg-slate-50" @click="prevPage">‹</button>
          <button :disabled="page * PAGE_SIZE >= total" class="px-3 py-1 rounded border border-slate-200 disabled:opacity-40 hover:bg-slate-50" @click="nextPage">›</button>
        </div>
      </div>
    </div>
  </div>
</template>
