<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getSparePart } from '@/api/inventory'
import type { SparePart, StockRow, StockMovement } from '@/types/inventory'

const props = defineProps<{ name: string }>()
const router = useRouter()

type PartDetail = SparePart & {
  stock_by_warehouse: StockRow[]
  total_stock: number
  recent_movements: Array<Partial<StockMovement> & { qty: number; unit_cost: number }>
}

const part = ref<PartDetail | null>(null)
const loading = ref(false)

async function load() {
  loading.value = true
  try { part.value = await getSparePart(props.name) as PartDetail }
  finally { loading.value = false }
}

function vnd(v?: number) {
  if (v == null) return '—'
  return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(v)
}
function formatDt(d?: string) { return d ? new Date(d).toLocaleString('vi-VN') : '—' }

const TYPE_LABELS: Record<string, string> = {
  Receipt: 'Nhập', Issue: 'Xuất', Transfer: 'Chuyển', Adjustment: 'ĐC',
}
const TYPE_COLORS: Record<string, string> = {
  Receipt: 'bg-emerald-50 text-emerald-700',
  Issue: 'bg-red-50 text-red-700',
  Transfer: 'bg-blue-50 text-blue-700',
  Adjustment: 'bg-amber-50 text-amber-700',
}

onMounted(load)
</script>

<template>
  <div class="page-container animate-fade-in max-w-5xl">
    <button class="btn-ghost mb-4" @click="router.push('/spare-parts')">← Quay lại</button>

    <div v-if="loading && !part" class="text-center py-20 text-slate-400">Đang tải...</div>

    <div v-else-if="part">
      <!-- Header -->
      <div class="mb-6">
        <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">{{ part.part_code }}</p>
        <h1 class="text-2xl font-bold text-slate-900">{{ part.part_name }}</h1>
        <div class="flex items-center gap-2 mt-2">
          <span v-if="part.part_category" class="text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">{{ part.part_category }}</span>
          <span v-if="part.is_critical" class="text-xs px-2 py-0.5 rounded-full bg-red-50 text-red-700 font-medium">Quan trọng</span>
          <span v-if="!part.is_active" class="text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-500">Ngừng SD</span>
        </div>
      </div>

      <!-- Summary card -->
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div class="card p-4">
          <p class="text-xs text-slate-500 mb-1">Tổng tồn</p>
          <p class="text-xl font-bold text-slate-900">{{ part.total_stock || 0 }} <span class="text-sm font-normal text-slate-400">{{ part.uom }}</span></p>
        </div>
        <div class="card p-4">
          <p class="text-xs text-slate-500 mb-1">Đơn giá</p>
          <p class="text-xl font-bold text-emerald-600">{{ vnd(part.unit_cost) }}</p>
        </div>
        <div class="card p-4">
          <p class="text-xs text-slate-500 mb-1">Tồn min / max</p>
          <p class="text-xl font-bold text-slate-700">{{ part.min_stock_level || 0 }} / {{ part.max_stock_level || '∞' }}</p>
        </div>
        <div class="card p-4">
          <p class="text-xs text-slate-500 mb-1">NSX</p>
          <p class="text-sm font-medium text-slate-700">{{ part.manufacturer || '—' }}</p>
          <p class="text-xs text-slate-400 font-mono">{{ part.manufacturer_part_no || '' }}</p>
        </div>
      </div>

      <!-- Stock by warehouse -->
      <div class="card p-5 mb-6">
        <h3 class="text-sm font-semibold text-slate-700 mb-4">Tồn theo kho</h3>
        <div v-if="part.stock_by_warehouse.length === 0" class="text-center py-6 text-sm text-slate-400">
          Chưa có tồn ở bất kỳ kho nào
        </div>
        <div v-else class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="text-xs text-slate-400 border-b border-slate-100">
                <th class="py-2 text-left font-medium">Kho</th>
                <th class="py-2 text-right font-medium">Tồn</th>
                <th class="py-2 text-right font-medium">Giữ chỗ</th>
                <th class="py-2 text-right font-medium">Còn lại</th>
                <th class="py-2 text-left font-medium">Giao dịch cuối</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="s in part.stock_by_warehouse" :key="s.warehouse" class="border-b border-slate-50">
                <td class="py-2.5">
                  <p class="font-medium text-slate-800 text-sm">{{ s.warehouse_name || s.warehouse }}</p>
                  <p class="text-[11px] text-slate-400 font-mono">{{ s.warehouse }}</p>
                </td>
                <td class="py-2.5 text-right font-semibold">{{ s.qty_on_hand }}</td>
                <td class="py-2.5 text-right text-slate-500">{{ s.reserved_qty }}</td>
                <td class="py-2.5 text-right text-emerald-600 font-medium">{{ s.available_qty }}</td>
                <td class="py-2.5 text-xs text-slate-500">{{ formatDt(s.last_movement_date) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Recent movements -->
      <div class="card p-5">
        <h3 class="text-sm font-semibold text-slate-700 mb-4">Giao dịch gần nhất (20 phiếu)</h3>
        <div v-if="part.recent_movements.length === 0" class="text-center py-6 text-sm text-slate-400">
          Chưa có giao dịch nào
        </div>
        <div v-else class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="text-xs text-slate-400 border-b border-slate-100">
                <th class="py-2 text-left font-medium">Phiếu</th>
                <th class="py-2 text-left font-medium">Loại</th>
                <th class="py-2 text-left font-medium">Ngày</th>
                <th class="py-2 text-left font-medium">Từ kho</th>
                <th class="py-2 text-left font-medium">Đến kho</th>
                <th class="py-2 text-right font-medium">SL</th>
                <th class="py-2 text-right font-medium">Đơn giá</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="m in part.recent_movements" :key="m.name" class="border-b border-slate-50 hover:bg-slate-50 cursor-pointer"
                  @click="router.push(`/stock-movements/${m.name}`)">
                <td class="py-2 font-mono text-xs text-slate-600">{{ m.name }}</td>
                <td class="py-2">
                  <span class="text-xs px-2 py-0.5 rounded-full font-medium"
                        :class="TYPE_COLORS[m.movement_type as string] || 'bg-slate-100 text-slate-600'">
                    {{ TYPE_LABELS[m.movement_type as string] || m.movement_type }}
                  </span>
                </td>
                <td class="py-2 text-xs text-slate-500">{{ formatDt(m.movement_date) }}</td>
                <td class="py-2 text-xs font-mono text-slate-500">{{ m.from_warehouse || '—' }}</td>
                <td class="py-2 text-xs font-mono text-slate-500">{{ m.to_warehouse || '—' }}</td>
                <td class="py-2 text-right font-medium">{{ m.qty }}</td>
                <td class="py-2 text-right text-xs text-slate-500">{{ vnd(m.unit_cost) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Specs -->
      <div v-if="part.specifications" class="card p-5 mt-6">
        <h3 class="text-sm font-semibold text-slate-700 mb-2">Thông số kỹ thuật</h3>
        <p class="text-sm text-slate-600 whitespace-pre-wrap">{{ part.specifications }}</p>
      </div>
    </div>
  </div>
</template>
