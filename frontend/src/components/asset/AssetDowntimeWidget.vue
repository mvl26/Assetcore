<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { frappeGet } from '@/api/helpers'

interface DowntimeLog {
  name: string
  reason: string
  start_time: string
  end_time: string | null
  downtime_hours: number
  is_open: 0 | 1
  reference_doctype?: string
  reference_name?: string
}

interface Metrics {
  asset: string
  year: number
  total_hours: number
  breakdown_count: number
  mttr_hours: number
  by_reason: Record<string, number>
  current_open: (DowntimeLog & { downtime_hours_so_far: number }) | null
  logs: DowntimeLog[]
}

const props = defineProps<{ assetName: string; year?: number }>()

const metrics = ref<Metrics | null>(null)
const loading = ref(false)
const err = ref('')

async function load() {
  loading.value = true; err.value = ''
  try {
    const res = await frappeGet<Metrics>(
      '/api/method/assetcore.api.imm00.get_asset_downtime_metrics',
      { asset_name: props.assetName, year: props.year ?? '' },
    )
    metrics.value = res
  } catch (e: unknown) {
    err.value = (e as Error).message || 'Không tải được thống kê dừng máy'
  } finally {
    loading.value = false
  }
}

function fmtHours(h: number): string {
  if (!h) return '0 giờ'
  if (h < 1) return `${Math.round(h * 60)} phút`
  if (h < 24) return `${h.toFixed(1)} giờ`
  return `${Math.floor(h / 24)} ngày ${Math.round(h % 24)} giờ`
}

function fmtDate(s: string | null): string {
  if (!s) return '—'
  return new Date(s).toLocaleString('vi-VN', { hour12: false })
}

onMounted(load)
watch(() => [props.assetName, props.year], load)
</script>

<template>
  <div class="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
    <div class="flex items-center justify-between mb-4">
      <h3 class="text-sm font-semibold text-gray-800">Thống kê dừng máy {{ metrics?.year ? `(${metrics.year})` : '' }}</h3>
      <button class="text-xs text-blue-600 hover:underline" :disabled="loading" @click="load">
        {{ loading ? 'Đang tải...' : 'Làm mới' }}
      </button>
    </div>

    <div v-if="err" class="text-red-600 text-sm bg-red-50 px-3 py-2 rounded">{{ err }}</div>
    <div v-else-if="loading && !metrics" class="text-sm text-gray-400">Đang tải...</div>
    <template v-else-if="metrics">
      <!-- Alert: Đang dừng máy -->
      <div v-if="metrics.current_open" class="mb-4 bg-red-50 border border-red-200 rounded-lg px-3 py-2 text-sm">
        <div class="flex items-center justify-between">
          <div>
            <span class="font-semibold text-red-700">Đang dừng máy:</span>
            <span class="ml-1 text-red-700">{{ metrics.current_open.reason }}</span>
          </div>
          <div class="text-xs text-red-600 font-mono">
            {{ fmtHours(metrics.current_open.downtime_hours_so_far) }}
          </div>
        </div>
        <div class="text-xs text-red-500 mt-1">Bắt đầu: {{ fmtDate(metrics.current_open.start_time) }}</div>
      </div>

      <!-- KPI grid -->
      <div class="grid grid-cols-3 gap-3 mb-4">
        <div class="text-center bg-gray-50 rounded-lg py-3">
          <div class="text-xl font-semibold text-gray-800">{{ fmtHours(metrics.total_hours) }}</div>
          <div class="text-xs text-gray-500 mt-1">Tổng downtime</div>
        </div>
        <div class="text-center bg-gray-50 rounded-lg py-3">
          <div class="text-xl font-semibold text-gray-800">{{ metrics.breakdown_count }}</div>
          <div class="text-xs text-gray-500 mt-1">Số lần dừng</div>
        </div>
        <div class="text-center bg-gray-50 rounded-lg py-3">
          <div class="text-xl font-semibold text-gray-800">{{ fmtHours(metrics.mttr_hours) }}</div>
          <div class="text-xs text-gray-500 mt-1">Thời gian sửa chữa TB</div>
        </div>
      </div>

      <!-- By reason -->
      <div v-if="Object.keys(metrics.by_reason).length" class="mb-4">
        <div class="text-xs font-medium text-gray-500 mb-2">Theo nguyên nhân</div>
        <div class="space-y-1.5">
          <div v-for="(h, reason) in metrics.by_reason" :key="reason" class="flex items-center gap-2 text-xs">
            <div class="w-28 text-gray-600">{{ reason }}</div>
            <div class="flex-1 bg-gray-100 rounded h-2 overflow-hidden">
              <div class="bg-blue-500 h-full" :style="{ width: `${Math.min(100, (h / (metrics.total_hours || 1)) * 100)}%` }" />
            </div>
            <div class="w-20 text-right font-mono text-gray-700">{{ fmtHours(h) }}</div>
          </div>
        </div>
      </div>

      <!-- Recent logs -->
      <div v-if="metrics.logs.length">
        <div class="text-xs font-medium text-gray-500 mb-2">Lịch sử gần đây</div>
        <div class="divide-y divide-gray-100 text-xs">
          <div v-for="log in metrics.logs" :key="log.name" class="py-2 flex items-center justify-between">
            <div>
              <div class="font-medium text-gray-800">{{ log.reason }}</div>
              <div class="text-gray-500">{{ fmtDate(log.start_time) }} → {{ log.is_open ? 'đang mở' : fmtDate(log.end_time) }}</div>
            </div>
            <div class="font-mono" :class="log.is_open ? 'text-red-600' : 'text-gray-700'">
              {{ log.is_open ? '...' : fmtHours(log.downtime_hours) }}
            </div>
          </div>
        </div>
      </div>
      <div v-else class="text-xs text-gray-400 text-center py-4">Chưa có lần dừng máy nào trong năm.</div>
    </template>
  </div>
</template>
