<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getStockMovement, submitStockMovement, cancelStockMovement } from '@/api/inventory'
import type { StockMovement } from '@/types/inventory'

const props = defineProps<{ name: string }>()
const router = useRouter()

const doc = ref<StockMovement | null>(null)
const loading = ref(false)
const acting = ref(false)
const toast = ref('')

async function load() {
  loading.value = true
  try { doc.value = await getStockMovement(props.name) }
  finally { loading.value = false }
}

async function doSubmit() {
  if (!doc.value) return
  if (!confirm('Xác nhận duyệt phiếu này? Tồn kho sẽ được cập nhật.')) return
  acting.value = true
  try {
    await submitStockMovement(doc.value.name)
    toast.value = 'Đã duyệt phiếu và cập nhật tồn kho'
    await load()
  } catch (e: unknown) {
    toast.value = (e as Error).message || 'Lỗi duyệt phiếu'
  } finally { acting.value = false; setTimeout(() => { toast.value = '' }, 3000) }
}

async function doCancel() {
  if (!doc.value) return
  if (!confirm('Xác nhận huỷ phiếu? Tồn kho sẽ được hoàn nguyên.')) return
  acting.value = true
  try {
    await cancelStockMovement(doc.value.name)
    toast.value = 'Đã huỷ phiếu và hoàn tồn kho'
    await load()
  } catch (e: unknown) {
    toast.value = (e as Error).message || 'Lỗi huỷ phiếu'
  } finally { acting.value = false; setTimeout(() => { toast.value = '' }, 3000) }
}

function vnd(v?: number) {
  if (!v) return '—'
  return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(v)
}
function formatDt(d?: string) { return d ? new Date(d).toLocaleString('vi-VN') : '—' }

const TYPE_LABELS: Record<string, string> = {
  Receipt: 'Nhập kho', Issue: 'Xuất kho', Transfer: 'Chuyển kho', Adjustment: 'Điều chỉnh',
}

onMounted(load)
</script>

<template>
  <div class="page-container animate-fade-in max-w-4xl">
    <button class="btn-ghost mb-4" @click="router.push('/stock-movements')">← Quay lại</button>

    <div v-if="loading && !doc" class="text-center py-20 text-slate-400">Đang tải...</div>

    <div v-else-if="doc">
      <!-- Header -->
      <div class="flex items-start justify-between mb-6">
        <div>
          <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">IMM-00 · Stock Movement</p>
          <h1 class="text-2xl font-bold text-slate-900">{{ doc.name }}</h1>
          <div class="flex items-center gap-2 mt-2">
            <span class="text-xs px-2.5 py-1 rounded-full font-medium"
                  :class="doc.movement_type === 'Receipt'    ? 'bg-emerald-50 text-emerald-700' :
                          doc.movement_type === 'Issue'      ? 'bg-red-50 text-red-700' :
                          doc.movement_type === 'Transfer'   ? 'bg-blue-50 text-blue-700' :
                                                                'bg-amber-50 text-amber-700'">
              {{ TYPE_LABELS[doc.movement_type] }}
            </span>
            <span class="text-xs px-2.5 py-1 rounded-full font-medium"
                  :class="doc.status === 'Submitted' ? 'bg-emerald-50 text-emerald-700' :
                          doc.status === 'Cancelled' ? 'bg-red-50 text-red-700' :
                                                       'bg-slate-100 text-slate-600'">
              {{ doc.status === 'Draft' ? 'Nháp' : doc.status === 'Submitted' ? 'Đã duyệt' : 'Đã huỷ' }}
            </span>
          </div>
        </div>
        <div class="flex gap-2">
          <button v-if="doc.docstatus === 0" class="btn-primary" :disabled="acting" @click="doSubmit">
            {{ acting ? '...' : 'Duyệt phiếu' }}
          </button>
          <button v-if="doc.docstatus === 1" class="btn-secondary text-red-600" :disabled="acting" @click="doCancel">
            {{ acting ? '...' : 'Huỷ phiếu' }}
          </button>
        </div>
      </div>

      <div v-if="toast" class="mb-4 px-4 py-3 rounded-lg bg-emerald-50 text-emerald-700 text-sm">{{ toast }}</div>

      <!-- Info -->
      <div class="card p-5 mb-4">
        <h2 class="text-sm font-semibold text-slate-700 mb-4 pb-2 border-b border-slate-100">Thông tin chung</h2>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div>
            <p class="text-xs text-slate-500 mb-0.5">Ngày giao dịch</p>
            <p class="font-medium text-slate-800">{{ formatDt(doc.movement_date) }}</p>
          </div>
          <div>
            <p class="text-xs text-slate-500 mb-0.5">Người đề nghị</p>
            <p class="font-medium text-slate-800">{{ doc.requested_by }}</p>
          </div>
          <div v-if="doc.from_warehouse">
            <p class="text-xs text-slate-500 mb-0.5">Kho xuất</p>
            <p class="font-mono text-slate-700">{{ doc.from_warehouse }}</p>
          </div>
          <div v-if="doc.to_warehouse">
            <p class="text-xs text-slate-500 mb-0.5">Kho nhập</p>
            <p class="font-mono text-slate-700">{{ doc.to_warehouse }}</p>
          </div>
          <div v-if="doc.supplier">
            <p class="text-xs text-slate-500 mb-0.5">Nhà cung cấp</p>
            <p class="font-mono text-slate-700">{{ doc.supplier }}</p>
          </div>
          <div v-if="doc.reference_type">
            <p class="text-xs text-slate-500 mb-0.5">Chứng từ nguồn</p>
            <p class="text-slate-700">{{ doc.reference_type }} · <span class="font-mono">{{ doc.reference_name }}</span></p>
          </div>
        </div>
        <div v-if="doc.notes" class="mt-4 pt-3 border-t border-slate-100">
          <p class="text-xs text-slate-500 mb-1">Ghi chú</p>
          <p class="text-sm text-slate-700 whitespace-pre-wrap">{{ doc.notes }}</p>
        </div>
      </div>

      <!-- Items -->
      <div class="card p-5">
        <h2 class="text-sm font-semibold text-slate-700 mb-4 pb-2 border-b border-slate-100">Chi tiết phụ tùng</h2>
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="text-xs text-slate-400 border-b border-slate-100">
                <th class="py-2 text-left font-medium">Phụ tùng</th>
                <th class="py-2 text-right font-medium">SL</th>
                <th class="py-2 text-left font-medium">ĐVT</th>
                <th class="py-2 text-right font-medium">Đơn giá</th>
                <th class="py-2 text-right font-medium">Thành tiền</th>
                <th class="py-2 text-left font-medium hidden md:table-cell">Serial</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(r, i) in (doc.items || [])" :key="i" class="border-b border-slate-50">
                <td class="py-2.5">
                  <p class="font-medium text-slate-800">{{ r.part_name }}</p>
                  <p class="text-[11px] text-slate-400 font-mono">{{ r.spare_part }}</p>
                </td>
                <td class="py-2.5 text-right font-semibold">{{ r.qty }}</td>
                <td class="py-2.5 text-xs text-slate-500">{{ r.uom }}</td>
                <td class="py-2.5 text-right text-slate-600">{{ vnd(r.unit_cost) }}</td>
                <td class="py-2.5 text-right font-medium text-slate-800">{{ vnd(r.total_cost) }}</td>
                <td class="py-2.5 text-xs font-mono text-slate-500 hidden md:table-cell">{{ r.serial_no || '—' }}</td>
              </tr>
            </tbody>
            <tfoot class="border-t-2 border-slate-200">
              <tr>
                <td colspan="4" class="py-3 text-right text-sm font-semibold text-slate-500">Tổng giá trị</td>
                <td class="py-3 text-right text-lg font-bold text-emerald-700">{{ vnd(doc.total_value) }}</td>
                <td />
              </tr>
            </tfoot>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>
