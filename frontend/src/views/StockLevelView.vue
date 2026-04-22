<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { listStockLevels } from '@/api/inventory'
import type { StockRow } from '@/types/inventory'
import SmartSelect from '@/components/common/SmartSelect.vue'

const route = useRoute()
const router = useRouter()

const rows = ref<StockRow[]>([])
const total = ref(0)
const page = ref(1)
const PAGE_SIZE = 50
const loading = ref(false)

const warehouseFilter = ref('')
const lowOnly = ref(route.query.low === '1')

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
    <div class="flex items-start justify-between mb-6">
      <div>
        <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">IMM-00 · Inventory</p>
        <h1 class="text-2xl font-bold text-slate-900">Tồn kho</h1>
        <p class="text-sm text-slate-500 mt-1">{{ total }} dòng tồn kho (phụ tùng × kho)</p>
      </div>
      <button class="btn-primary" @click="router.push('/stock-movements/new')">+ Phiếu mới</button>
    </div>

    <!-- Filters -->
    <div class="card p-4 mb-4">
      <div class="grid grid-cols-1 md:grid-cols-3 gap-3 items-end">
        <div>
          <label class="form-label">Kho</label>
          <SmartSelect v-model="warehouseFilter" doctype="AC Warehouse" placeholder="Tất cả..." />
        </div>
        <div class="flex items-center gap-3 pt-6">
          <input id="low-only" v-model="lowOnly" type="checkbox" class="h-4 w-4 text-red-600 rounded" />
          <label for="low-only" class="text-sm text-slate-700">Chỉ hiển thị phụ tùng dưới mức min</label>
        </div>
      </div>
    </div>

    <div class="card overflow-hidden">
      <div v-if="loading && !rows.length" class="text-center py-12 text-slate-400">Đang tải...</div>
      <div v-else-if="rows.length === 0" class="text-center py-12 text-slate-400">Không có dữ liệu tồn.</div>

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
            <tr v-for="r in rows" :key="r.name"
                :class="['hover:bg-slate-50/70 cursor-pointer',
                         r.is_low ? 'bg-red-50/30' : '']"
                @click="router.push(`/spare-parts/${r.spare_part}`)">
              <td class="px-4 py-3">
                <p class="text-sm text-slate-700">{{ r.warehouse_name }}</p>
                <p class="text-[10px] text-slate-400 font-mono">{{ r.warehouse }}</p>
              </td>
              <td class="px-4 py-3">
                <p class="font-medium text-slate-800">{{ r.part_name }}</p>
                <div class="flex items-center gap-1 mt-0.5">
                  <p class="text-[11px] text-slate-400 font-mono">{{ r.spare_part }}</p>
                  <span v-if="r.is_critical" class="text-[9px] px-1 py-0 rounded bg-red-50 text-red-700 font-bold">!</span>
                </div>
              </td>
              <td class="px-4 py-3 text-right font-semibold"
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
