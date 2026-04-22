<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { listStockMovements } from '@/api/inventory'
import type { StockMovement, MovementType, MovementStatus } from '@/types/inventory'

const router = useRouter()
const rows = ref<StockMovement[]>([])
const total = ref(0)
const page = ref(1)
const PAGE_SIZE = 30
const loading = ref(false)

const typeFilter = ref<MovementType | ''>('')
const statusFilter = ref<MovementStatus | ''>('')

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

const TYPE_LABELS: Record<string, string> = {
  Receipt: 'Nhập kho', Issue: 'Xuất kho', Transfer: 'Chuyển kho', Adjustment: 'Điều chỉnh',
}
const TYPE_COLORS: Record<string, string> = {
  Receipt: 'bg-emerald-50 text-emerald-700',
  Issue: 'bg-red-50 text-red-700',
  Transfer: 'bg-blue-50 text-blue-700',
  Adjustment: 'bg-amber-50 text-amber-700',
}
const STATUS_COLORS: Record<string, string> = {
  Draft: 'bg-slate-100 text-slate-600',
  Submitted: 'bg-emerald-50 text-emerald-700',
  Cancelled: 'bg-red-50 text-red-700',
}

onMounted(load)
</script>

<template>
  <div class="page-container animate-fade-in">
    <div class="flex items-start justify-between mb-6">
      <div>
        <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">IMM-00 · Inventory</p>
        <h1 class="text-2xl font-bold text-slate-900">Phiếu xuất / nhập kho</h1>
        <p class="text-sm text-slate-500 mt-1">{{ total }} phiếu</p>
      </div>
      <button class="btn-primary" @click="router.push('/stock-movements/new')">+ Tạo phiếu mới</button>
    </div>

    <!-- Filters -->
    <div class="card p-4 mb-4">
      <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div>
          <label for="sm-type" class="form-label">Loại giao dịch</label>
          <select id="sm-type" v-model="typeFilter" class="form-select w-full">
            <option value="">Tất cả</option>
            <option value="Receipt">Nhập kho</option>
            <option value="Issue">Xuất kho</option>
            <option value="Transfer">Chuyển kho</option>
            <option value="Adjustment">Điều chỉnh</option>
          </select>
        </div>
        <div>
          <label for="sm-status" class="form-label">Trạng thái</label>
          <select id="sm-status" v-model="statusFilter" class="form-select w-full">
            <option value="">Tất cả</option>
            <option value="Draft">Nháp</option>
            <option value="Submitted">Đã duyệt</option>
            <option value="Cancelled">Đã huỷ</option>
          </select>
        </div>
      </div>
    </div>

    <div class="card overflow-hidden">
      <div v-if="loading && !rows.length" class="text-center py-12 text-slate-400">Đang tải...</div>
      <div v-else-if="rows.length === 0" class="text-center py-12 text-slate-400">Chưa có phiếu nào.</div>

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
            <tr v-for="m in rows" :key="m.name" class="hover:bg-slate-50/70 cursor-pointer"
                @click="router.push(`/stock-movements/${m.name}`)">
              <td class="px-4 py-3 font-mono text-xs font-medium text-slate-700">{{ m.name }}</td>
              <td class="px-4 py-3">
                <span class="text-xs px-2 py-0.5 rounded-full font-medium"
                      :class="TYPE_COLORS[m.movement_type] || 'bg-slate-100 text-slate-600'">
                  {{ TYPE_LABELS[m.movement_type] || m.movement_type }}
                </span>
              </td>
              <td class="px-4 py-3 text-xs text-slate-500 hidden md:table-cell">{{ formatDt(m.movement_date) }}</td>
              <td class="px-4 py-3 text-xs font-mono text-slate-500">
                <span v-if="m.from_warehouse">{{ m.from_warehouse }}</span>
                <span v-if="m.from_warehouse && m.to_warehouse" class="text-slate-400"> → </span>
                <span v-if="m.to_warehouse">{{ m.to_warehouse }}</span>
                <span v-if="!m.from_warehouse && !m.to_warehouse" class="text-slate-400">—</span>
              </td>
              <td class="px-4 py-3 text-right text-sm text-slate-700 hidden md:table-cell">{{ vnd(m.total_value) }}</td>
              <td class="px-4 py-3 text-xs text-slate-500 hidden lg:table-cell">
                <span v-if="m.reference_type">{{ m.reference_type }}</span>
                <span v-if="m.reference_name" class="text-slate-400">· {{ m.reference_name }}</span>
                <span v-if="!m.reference_type" class="text-slate-300">—</span>
              </td>
              <td class="px-4 py-3 text-center">
                <span class="text-xs px-2 py-0.5 rounded-full font-medium"
                      :class="STATUS_COLORS[m.status] || 'bg-slate-100 text-slate-600'">
                  {{ m.status === 'Draft' ? 'Nháp' : m.status === 'Submitted' ? 'Đã duyệt' : 'Đã huỷ' }}
                </span>
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
