<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
import { ref, onMounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { listStockMovements } from '@/api/inventory'
import type { StockMovement, MovementType, MovementStatus } from '@/types/inventory'

const router = useRouter()
const rows = ref<StockMovement[]>([])
const total = ref(0)
const page = ref(1)
const PAGE_SIZE = 30
const loading = ref(false)
const showFilters = ref(false)

const typeFilter = ref<MovementType | ''>('')
const statusFilter = ref<MovementStatus | ''>('')

const TYPE_LABELS: Record<string, string> = {
  Receipt: 'Nhập kho', Issue: 'Xuất kho', Transfer: 'Chuyển kho', Adjustment: 'Điều chỉnh',
}
const TYPE_COLORS: Record<string, string> = {
  Receipt:    'bg-emerald-50 text-emerald-700',
  Issue:      'bg-red-50 text-red-700',
  Transfer:   'bg-blue-50 text-blue-700',
  Adjustment: 'bg-amber-50 text-amber-700',
}
const STATUS_LABELS: Record<string, string> = {
  Draft: 'Nháp', Submitted: 'Đã duyệt', Cancelled: 'Đã huỷ',
}
const STATUS_COLORS: Record<string, string> = {
  Draft:     'bg-slate-100 text-slate-600',
  Submitted: 'bg-emerald-50 text-emerald-700',
  Cancelled: 'bg-red-50 text-red-700',
}

interface Chip { key: 'type' | 'status'; label: string }
const activeChips = computed<Chip[]>(() => {
  const chips: Chip[] = []
  if (typeFilter.value) chips.push({ key: 'type', label: TYPE_LABELS[typeFilter.value] ?? typeFilter.value })
  if (statusFilter.value) chips.push({ key: 'status', label: STATUS_LABELS[statusFilter.value] ?? statusFilter.value })
  return chips
})
const activeFilterCount = computed(() => activeChips.value.length)

function clearChip(key: Chip['key']) {
  if (key === 'type') typeFilter.value = ''
  else statusFilter.value = ''
  page.value = 1; load()
}

function resetFilters() {
  typeFilter.value = ''
  statusFilter.value = ''
  page.value = 1; load()
}

function quickFilter(key: 'type' | 'status', value: string) {
  if (!value) return
  if (key === 'type') typeFilter.value = value as MovementType
  else statusFilter.value = value as MovementStatus
  showFilters.value = false
  page.value = 1; load()
}

async function load() {
  loading.value = true
  try {
    const r = await listStockMovements({
      page: page.value, page_size: PAGE_SIZE,
      movement_type: typeFilter.value,
      status: statusFilter.value,
    })
    rows.value = r?.items || []
    total.value = r?.pagination?.total || 0
  } finally { loading.value = false }
}

watch([typeFilter, statusFilter], () => { page.value = 1; load() })

function prevPage() { if (page.value > 1) { page.value--; load() } }
function nextPage() { if (page.value * PAGE_SIZE < total.value) { page.value++; load() } }

function vnd(v?: number) {
  if (!v) return '—'
  return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(v)
}
function formatDt(d?: string) { return d ? new Date(d).toLocaleString('vi-VN') : '—' }

onMounted(load)
</script>

<template>
  <div class="page-container animate-fade-in">
<!-- Header -->
    <div class="flex items-start justify-between mb-5">
      <div>
        <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">Inventory</p>
        <h1 class="text-2xl font-bold text-slate-900">Phiếu xuất / nhập kho</h1>
        <p class="text-sm text-slate-500 mt-1">Tổng <strong class="text-slate-700">{{ total }}</strong> phiếu</p>
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
        <button class="btn-primary shrink-0" @click="router.push('/stock-movements/new')">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          Tạo phiếu mới
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
        <button class="text-xs text-slate-400 hover:text-red-500 underline underline-offset-2" @click="resetFilters">Xóa tất cả</button>
      </div>
    </Transition>

    <!-- Collapsible filter panel -->
    <Transition
      enter-active-class="transition-all duration-200 ease-out overflow-hidden"
      enter-from-class="opacity-0 max-h-0"
      enter-to-class="opacity-100 max-h-40"
      leave-active-class="transition-all duration-150 ease-in overflow-hidden"
      leave-from-class="opacity-100 max-h-40"
      leave-to-class="opacity-0 max-h-0"
    >
      <div v-show="showFilters" class="card p-4 mb-4 space-y-3">
        <div class="flex flex-wrap gap-3 items-center">
          <div class="flex items-center gap-2">
            <label for="sm-type" class="text-sm text-slate-600 shrink-0">Loại GD:</label>
            <select id="sm-type" v-model="typeFilter" class="form-select text-sm">
              <option value="">Tất cả</option>
              <option value="Receipt">Nhập kho</option>
              <option value="Issue">Xuất kho</option>
              <option value="Transfer">Chuyển kho</option>
              <option value="Adjustment">Điều chỉnh</option>
            </select>
          </div>
          <div class="flex items-center gap-2">
            <label for="sm-status" class="text-sm text-slate-600 shrink-0">Trạng thái:</label>
            <select id="sm-status" v-model="statusFilter" class="form-select text-sm">
              <option value="">Tất cả</option>
              <option value="Draft">Nháp</option>
              <option value="Submitted">Đã duyệt</option>
              <option value="Cancelled">Đã huỷ</option>
            </select>
          </div>
          <button class="btn-ghost text-sm" @click="resetFilters">Đặt lại</button>
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
        </div>
      </div>
    </Transition>

    <div class="card overflow-hidden">
      <!-- Info row -->
      <div class="flex items-center justify-between px-4 py-2.5 border-b border-slate-100 bg-slate-50/60 text-xs text-slate-500">
        <span>Hiển thị <strong class="text-slate-700">{{ rows.length }}</strong> / {{ total }} phiếu</span>
        <button v-if="activeFilterCount > 0" class="text-red-500 hover:text-red-700 font-medium" @click="resetFilters">Xóa tất cả</button>
      </div>

      <div v-if="loading && !rows.length" class="text-center py-12 text-slate-400">Đang tải...</div>
      <div v-else-if="rows.length === 0" class="flex flex-col items-center justify-center py-16 text-slate-400">
        <p class="text-sm">Chưa có phiếu nào.</p>
        <button v-if="activeFilterCount > 0" class="text-xs text-blue-500 hover:text-blue-700 underline mt-2" @click="resetFilters">
          Xóa bộ lọc để xem tất cả
        </button>
      </div>

      <div v-else class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-slate-50 border-b border-slate-100">
            <tr>
              <th class="px-4 py-3 text-left text-xs font-semibold text-slate-500">Mã phiếu</th>
              <th class="px-4 py-3 text-left text-xs font-semibold text-slate-500">Loại</th>
              <th class="px-4 py-3 text-left text-xs font-semibold text-slate-500 hidden md:table-cell">Ngày</th>
              <th class="px-4 py-3 text-left text-xs font-semibold text-slate-500">Kho</th>
              <th class="px-4 py-3 text-right text-xs font-semibold text-slate-500 hidden md:table-cell">Giá trị</th>
              <th class="px-4 py-3 text-left text-xs font-semibold text-slate-500 hidden lg:table-cell">Chứng từ</th>
              <th class="px-4 py-3 text-center text-xs font-semibold text-slate-500">Trạng thái</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-50">
            <tr
v-for="m in rows" :key="m.name"
              class="hover:bg-slate-50/70 cursor-pointer transition-all hover:translate-x-0.5"
              @click="router.push(`/stock-movements/${m.name}`)"
            >
              <td class="px-4 py-3 font-mono text-xs font-medium text-slate-700">{{ m.name }}</td>
              <td class="px-4 py-3">
                <button
                  class="text-xs px-2 py-0.5 rounded-full font-medium transition-all hover:ring-2 hover:ring-offset-1 hover:ring-current/50"
                  :class="TYPE_COLORS[m.movement_type] || 'bg-slate-100 text-slate-600'"
                  :title="`Lọc: ${TYPE_LABELS[m.movement_type] || m.movement_type}`"
                  @click.stop="quickFilter('type', m.movement_type)"
                >
{{ TYPE_LABELS[m.movement_type] || m.movement_type }}
</button>
              </td>
              <td class="px-4 py-3 text-xs text-slate-500 hidden md:table-cell">{{ formatDt(m.movement_date) }}</td>
              <td class="px-4 py-3 text-xs text-slate-600">
                <template v-if="m.from_warehouse || m.to_warehouse">
                  <span v-if="m.from_warehouse" :title="m.from_warehouse" class="font-medium">
                    {{ m.from_warehouse_code || m.from_warehouse_name || m.from_warehouse }}
                  </span>
                  <span v-if="m.from_warehouse && m.to_warehouse" class="text-slate-400 mx-1">→</span>
                  <span v-if="m.to_warehouse" :title="m.to_warehouse" class="font-medium">
                    {{ m.to_warehouse_code || m.to_warehouse_name || m.to_warehouse }}
                  </span>
                </template>
                <span v-else class="text-slate-400">—</span>
              </td>
              <td class="px-4 py-3 text-right text-sm text-slate-700 hidden md:table-cell">{{ vnd(m.total_value) }}</td>
              <td class="px-4 py-3 text-xs text-slate-500 hidden lg:table-cell">
                <span v-if="m.reference_type">{{ m.reference_type }}</span>
                <span v-if="m.reference_name" class="text-slate-400">· {{ m.reference_name }}</span>
                <span v-if="!m.reference_type" class="text-slate-300">—</span>
              </td>
              <td class="px-4 py-3 text-center">
                <button
                  class="text-xs px-2 py-0.5 rounded-full font-medium transition-all hover:ring-2 hover:ring-offset-1 hover:ring-current/50"
                  :class="STATUS_COLORS[m.status] || 'bg-slate-100 text-slate-600'"
                  :title="`Lọc: ${STATUS_LABELS[m.status] || m.status}`"
                  @click.stop="quickFilter('status', m.status)"
                >
{{ STATUS_LABELS[m.status] || m.status }}
</button>
              </td>
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
