<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { Activity, Gauge } from 'lucide-vue-next'

const router = useRouter()

interface AssetStatus {
  asset: string
  name: string
  status: string
}

interface DashboardData {
  date: string
  dept: string
  total_assets: number
  running: number
  standby: number
  fault: number
  under_maintenance: number
  not_used: number
  total_runtime_hours_today: number
  anomaly_count_today: number
  assets_by_status: AssetStatus[]
}

const data = ref<DashboardData | null>(null)
const loading = ref(true)
const deptFilter = ref('')
let refreshInterval: ReturnType<typeof setInterval> | null = null

function statusColor(status: string): string {
  const map: Record<string, string> = {
    'Running': 'border-green-400 bg-green-50',
    'Standby': 'border-yellow-400 bg-yellow-50',
    'Fault': 'border-red-400 bg-red-50',
    'Under Maintenance': 'border-orange-400 bg-orange-50',
    'Not Used': 'border-slate-200 bg-slate-50',
  }
  return map[status] ?? 'border-slate-200 bg-slate-50'
}

function statusBadge(status: string): string {
  const map: Record<string, string> = {
    'Running': 'bg-green-100 text-green-700',
    'Standby': 'bg-yellow-100 text-yellow-700',
    'Fault': 'bg-red-100 text-red-700',
    'Under Maintenance': 'bg-orange-100 text-orange-700',
    'Not Used': 'bg-slate-100 text-slate-500',
  }
  return map[status] ?? 'bg-slate-100 text-slate-500'
}

async function fetchDashboard() {
  try {
    const params = new URLSearchParams({ dept: deptFilter.value })
    const res = await fetch(`/api/method/assetcore.api.imm07.get_dashboard_stats?${params}`)
    const json = await res.json()
    if (json.message?.success) data.value = json.message.data
  } catch { /* silent */ } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchDashboard()
  refreshInterval = setInterval(fetchDashboard, 5 * 60 * 1000) // refresh every 5 min
})

onUnmounted(() => {
  if (refreshInterval) clearInterval(refreshInterval)
})
</script>

<template>
  <div class="page-container animate-fade-in">

    <!-- Header -->
    <div class="flex items-start justify-between mb-7">
      <div>
        <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">IMM-07</p>
        <h1 class="text-2xl font-bold text-slate-900">Vận hành hôm nay</h1>
        <p class="text-sm text-slate-500 mt-1">{{ data?.date ?? '—' }}</p>
      </div>
      <div class="flex gap-2 shrink-0">
        <input v-model="deptFilter" type="text" class="form-input w-40 text-sm" placeholder="Lọc theo khoa..."
               @keyup.enter="fetchDashboard" />
        <button class="btn-primary" @click="router.push('/daily-ops/log')">Ghi nhật ký ca</button>
      </div>
    </div>

    <div v-if="loading" class="card py-16 text-center text-slate-400">Đang tải...</div>

    <template v-else-if="data">

      <!-- KPI Cards -->
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-7">
        <div class="kpi-card p-5">
          <div class="flex items-center gap-2 mb-2">
            <span class="w-2.5 h-2.5 rounded-full bg-green-500" />
            <p class="text-xs font-medium text-slate-500">Running</p>
          </div>
          <p class="text-3xl font-bold text-green-600">{{ data.running }}</p>
          <p class="text-xs text-slate-400 mt-1">thiết bị đang hoạt động</p>
        </div>
        <div class="kpi-card p-5">
          <div class="flex items-center gap-2 mb-2">
            <span class="w-2.5 h-2.5 rounded-full bg-yellow-400" />
            <p class="text-xs font-medium text-slate-500">Standby / Không dùng</p>
          </div>
          <p class="text-3xl font-bold text-yellow-600">{{ data.standby + data.not_used }}</p>
        </div>
        <div class="kpi-card p-5">
          <div class="flex items-center gap-2 mb-2">
            <span class="w-2.5 h-2.5 rounded-full bg-red-500 animate-pulse" />
            <p class="text-xs font-medium text-slate-500">Fault / Bảo trì</p>
          </div>
          <p class="text-3xl font-bold text-red-600">{{ data.fault + data.under_maintenance }}</p>
        </div>
        <div class="kpi-card p-5">
          <div class="flex items-center gap-2 mb-2">
            <Gauge class="w-3.5 h-3.5 text-blue-500" />
            <p class="text-xs font-medium text-slate-500">Tổng giờ chạy hôm nay</p>
          </div>
          <p class="text-3xl font-bold text-blue-600">{{ data.total_runtime_hours_today }}h</p>
        </div>
      </div>

      <!-- Fault Alert -->
      <div v-if="data.fault > 0"
           class="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl flex items-start gap-3">
        <span class="w-2.5 h-2.5 rounded-full bg-red-500 animate-pulse mt-1 shrink-0" />
        <div>
          <p class="text-sm font-semibold text-red-700">
            {{ data.fault }} thiết bị đang bị lỗi — cần kiểm tra ngay!
          </p>
          <p class="text-xs text-red-500 mt-0.5">
            {{ data.assets_by_status.filter(a => a.status === 'Fault').map(a => a.name || a.asset).join(', ') }}
          </p>
        </div>
      </div>

      <!-- Asset Grid -->
      <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
        <div
          v-for="asset in data.assets_by_status"
          :key="asset.asset"
          class="rounded-xl border-2 p-4 cursor-pointer hover:shadow-md transition-shadow"
          :class="statusColor(asset.status)"
          @click="router.push(`/daily-ops/logs?asset=${asset.asset}`)"
        >
          <div class="flex items-start justify-between mb-2">
            <span class="text-xs font-semibold px-2 py-0.5 rounded-full" :class="statusBadge(asset.status)">
              {{ asset.status }}
            </span>
            <Activity v-if="asset.status === 'Running'" class="w-4 h-4 text-green-500" />
          </div>
          <p class="text-sm font-semibold text-slate-800 leading-snug truncate">{{ asset.name || asset.asset }}</p>
          <p class="text-xs font-mono text-slate-400 mt-0.5 truncate">{{ asset.asset }}</p>
        </div>

        <div v-if="!data.assets_by_status.length"
             class="col-span-full card py-12 text-center text-slate-400 text-sm">
          Không có dữ liệu vận hành hôm nay.
        </div>
      </div>

    </template>

  </div>
</template>
