<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
import { ref, computed, onMounted } from 'vue'
import {
  getDepreciationSchedule, regenerateDepreciationSchedule, runDueDepreciationNow,
  type DepreciationScheduleResponse, type DepreciationScheduleRow,
} from '@/api/imm00'

const props = defineProps<{ assetName: string }>()

const data    = ref<DepreciationScheduleResponse | null>(null)
const loading = ref(false)
const acting  = ref(false)
const toast   = ref('')
const toastError = ref(false)

async function load() {
  loading.value = true
  try { data.value = await getDepreciationSchedule(props.assetName) }
  catch { data.value = null }
  finally { loading.value = false }
}

onMounted(load)

async function regenerate() {
  if (!confirm('Xóa lịch hiện tại và sinh lại từ đầu?')) return
  acting.value = true
  try {
    const res = await regenerateDepreciationSchedule(props.assetName, 1)
    showToast(res.skipped ? (res.reason || 'Bị bỏ qua') : `Đã sinh ${res.periods} kỳ`, !!res.skipped)
    await load()
  } catch (e) {
    showToast((e as Error).message || 'Lỗi', true)
  } finally { acting.value = false }
}

async function runNow() {
  if (!confirm('Chạy ngay các kỳ khấu hao đến hạn? (chỉ cho phép System Manager)')) return
  acting.value = true
  try {
    const res = await runDueDepreciationNow()
    showToast(`Đã thực thi ${res.executed_rows} dòng, cập nhật ${res.updated_assets} tài sản`)
    await load()
  } catch (e) {
    showToast((e as Error).message || 'Lỗi', true)
  } finally { acting.value = false }
}

function showToast(msg: string, err = false) {
  toast.value = msg; toastError.value = err
  setTimeout(() => { toast.value = '' }, 3500)
}

function vnd(v?: number): string {
  if (!v) return '0 đ'
  return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(v)
}

function formatDate(s?: string): string {
  if (!s) return '—'
  const d = new Date(s)
  if (Number.isNaN(d.getTime())) return s
  return d.toLocaleDateString('vi-VN', { year: 'numeric', month: '2-digit', day: '2-digit' })
}

function statusClass(s: string): string {
  if (s === 'Executed')  return 'bg-emerald-50 text-emerald-700 border-emerald-200'
  if (s === 'Cancelled') return 'bg-slate-100 text-slate-600 border-slate-200'
  return 'bg-amber-50 text-amber-700 border-amber-200'
}

function statusLabel(s: string): string {
  if (s === 'Executed')  return 'Đã khấu hao'
  if (s === 'Cancelled') return 'Đã hủy'
  return 'Chờ xử lý'
}

const progress = computed(() => {
  if (!data.value) return 0
  const s = data.value.summary
  if (!s.total_periods) return 0
  return Math.round((s.executed_periods / s.total_periods) * 100)
})

const nextPendingRow = computed<DepreciationScheduleRow | null>(() =>
  data.value?.rows.find(r => r.status === 'Pending') ?? null,
)
</script>

<template>
  <div class="space-y-4">
    <div v-if="toast"
         class="px-4 py-2 rounded-lg text-sm"
         :class="toastError ? 'bg-red-50 text-red-700' : 'bg-emerald-50 text-emerald-700'">
      {{ toast }}
    </div>

    <div v-if="loading" class="card p-8 text-center text-slate-400">Đang tải...</div>

    <div v-else-if="!data || !data.rows.length" class="card p-6 text-center">
      <p class="text-slate-500 mb-3">Chưa có lịch khấu hao cho tài sản này.</p>
      <button class="btn-primary text-sm" :disabled="acting" @click="regenerate">
        {{ acting ? 'Đang tạo...' : 'Sinh lịch khấu hao' }}
      </button>
    </div>

    <template v-else>
      <!-- Summary + actions -->
      <div class="card p-5">
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4 text-sm">
          <div>
            <p class="text-xs text-slate-500 mb-1">Phương pháp</p>
            <p class="font-semibold text-slate-800">{{ data.asset_info.depreciation_method || '—' }}</p>
            <p class="text-xs text-slate-500 mt-0.5">
              {{ data.asset_info.total_depreciation_months || 0 }} tháng ·
              {{ data.asset_info.depreciation_frequency || 'Monthly' }}
            </p>
          </div>
          <div>
            <p class="text-xs text-slate-500 mb-1">Nguyên giá</p>
            <p class="font-bold text-slate-900">{{ vnd(data.asset_info.gross_purchase_amount) }}</p>
            <p class="text-xs text-slate-500 mt-0.5">
              Thu hồi: {{ vnd(data.asset_info.residual_value) }}
            </p>
          </div>
          <div>
            <p class="text-xs text-slate-500 mb-1">Đã khấu hao</p>
            <p class="font-bold text-red-600">−{{ vnd(data.asset_info.accumulated_depreciation) }}</p>
            <p class="text-xs text-slate-500 mt-0.5">
              {{ data.summary.executed_periods }}/{{ data.summary.total_periods }} kỳ
            </p>
          </div>
          <div>
            <p class="text-xs text-slate-500 mb-1">Giá trị còn lại</p>
            <p class="font-bold text-emerald-600">{{ vnd(data.asset_info.current_book_value) }}</p>
          </div>
        </div>

        <!-- Progress bar -->
        <div class="mt-4">
          <div class="flex items-center justify-between text-xs text-slate-500 mb-1">
            <span>Tiến độ khấu hao</span>
            <span class="font-semibold">{{ progress }}%</span>
          </div>
          <div class="h-2 bg-slate-100 rounded-full overflow-hidden">
            <div class="h-full bg-emerald-500 transition-all" :style="{ width: `${progress}%` }" />
          </div>
        </div>

        <!-- Next pending -->
        <div v-if="nextPendingRow" class="mt-4 p-3 rounded-lg bg-amber-50 border border-amber-200 text-sm">
          <span class="text-xs text-amber-800">Kỳ tiếp theo:</span>
          <span class="font-semibold text-amber-900 ml-2">
            #{{ nextPendingRow.period_number }} — {{ formatDate(nextPendingRow.scheduled_date) }}
            — {{ vnd(nextPendingRow.depreciation_amount) }}
          </span>
        </div>

        <!-- Actions -->
        <div class="flex justify-end gap-2 mt-4 pt-3 border-t border-slate-100">
          <button class="btn-ghost text-xs" :disabled="acting" @click="runNow">
            ⚙ Chạy cron ngay
          </button>
          <button class="btn-secondary text-xs" :disabled="acting" @click="regenerate">
            Sinh lại lịch
          </button>
        </div>
      </div>

      <!-- Schedule table -->
      <div class="card p-0 overflow-hidden">
        <table class="w-full text-sm">
          <thead class="bg-slate-50 border-b border-slate-200">
            <tr>
              <th class="px-4 py-2 text-left text-xs font-medium text-slate-500">Kỳ</th>
              <th class="px-4 py-2 text-left text-xs font-medium text-slate-500">Ngày KH</th>
              <th class="px-4 py-2 text-right text-xs font-medium text-slate-500">Số tiền KH</th>
              <th class="px-4 py-2 text-right text-xs font-medium text-slate-500">Lũy kế</th>
              <th class="px-4 py-2 text-right text-xs font-medium text-slate-500">Còn lại</th>
              <th class="px-4 py-2 text-center text-xs font-medium text-slate-500">Trạng thái</th>
              <th class="px-4 py-2 text-left text-xs font-medium text-slate-500">Ngày thực thi</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr v-for="r in data.rows" :key="r.name"
                :class="r.status === 'Executed' ? 'bg-emerald-50/20' : ''">
              <td class="px-4 py-2 font-mono text-xs text-slate-600">#{{ r.period_number }}</td>
              <td class="px-4 py-2 text-slate-700">{{ formatDate(r.scheduled_date) }}</td>
              <td class="px-4 py-2 text-right font-semibold text-slate-800">{{ vnd(r.depreciation_amount) }}</td>
              <td class="px-4 py-2 text-right text-red-600">−{{ vnd(r.accumulated_amount) }}</td>
              <td class="px-4 py-2 text-right text-emerald-700 font-medium">{{ vnd(r.remaining_value) }}</td>
              <td class="px-4 py-2 text-center">
                <span class="inline-block px-2 py-0.5 rounded-full text-[11px] font-medium border"
                      :class="statusClass(r.status)">
                  {{ statusLabel(r.status) }}
                </span>
              </td>
              <td class="px-4 py-2 text-xs text-slate-500">{{ formatDate(r.executed_on) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>
