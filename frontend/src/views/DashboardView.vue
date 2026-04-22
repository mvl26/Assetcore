<script setup lang="ts">
// HTM Command Center — Dashboard tổng quan AssetCore.
// Gom 4 khối (KPI / Donut chart / Active repairs / Upcoming maintenance)
// từ một API duy nhất: assetcore.api.dashboard.get_dashboard_data
import { onMounted, computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useRouter } from 'vue-router'
import { useDashboardStore } from '@/stores/useDashboardStore'
import StatusDonutChart from '@/components/dashboard/StatusDonutChart.vue'
import ActiveRepairsList from '@/components/dashboard/ActiveRepairsList.vue'
import UpcomingMaintenanceList from '@/components/dashboard/UpcomingMaintenanceList.vue'

const router = useRouter()
const store  = useDashboardStore()
const { data, loading, error } = storeToRefs(store)

onMounted(() => store.load())

const kpi = computed(() => data.value?.kpi_metrics ?? null)
const chart = computed(() => data.value?.asset_status_chart ?? { labels: [], series: [], colors: [] })
const repairs = computed(() => data.value?.active_repairs ?? [])
const upcoming = computed(() => data.value?.upcoming_maintenance ?? [])

function fmt(n?: number): string {
  return (n ?? 0).toLocaleString('vi-VN')
}

function refresh() { store.load({ force: true }) }

interface KpiCard {
  label: string
  value: number
  accent: string
  bg: string
  icon: string
  to: string
}

const kpiCards = computed<KpiCard[]>(() => {
  const m = kpi.value
  if (!m) return []
  return [
    {
      label: 'Tổng thiết bị',
      value: m.total_assets,
      accent: 'text-blue-700',
      bg: 'bg-blue-50',
      icon: 'M4 7h16M4 12h16M4 17h16',
      to: '/assets',
    },
    {
      label: 'Đang sửa chữa',
      value: m.under_repair,
      accent: 'text-red-700',
      bg: 'bg-red-50',
      icon: 'M11.42 15.17L17.25 21A2.652 2.652 0 0021 17.25l-5.877-5.877M11.42 15.17l2.496-3.03c.317-.384.74-.626 1.208-.766M11.42 15.17l-4.655 5.653a2.548 2.548 0 11-3.586-3.586l6.837-5.63m5.108-.233c.55-.164 1.163-.188 1.743-.14a4.5 4.5 0 004.486-6.336l-3.276 3.277a3.004 3.004 0 01-2.25-2.25l3.276-3.276a4.5 4.5 0 00-6.336 4.486c.091 1.076-.071 2.264-.904 2.95l-.102.085m-1.745 1.437L5.909 7.5H4.5L2.25 3.75l1.5-1.5L7.5 4.5v1.409l4.26 4.26m-1.745 1.437l1.745-1.437m6.615 8.206L15.75 15.75M4.867 19.125h.008v.008h-.008v-.008z',
      to: '/cm/work-orders',
    },
    {
      label: 'Đang bảo trì',
      value: m.under_maintenance,
      accent: 'text-amber-700',
      bg: 'bg-amber-50',
      icon: 'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z M15 12a3 3 0 11-6 0 3 3 0 016 0z',
      to: '/pm/work-orders',
    },
    {
      label: 'Phiếu chờ duyệt',
      value: m.pending_commissioning,
      accent: 'text-purple-700',
      bg: 'bg-purple-50',
      icon: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z',
      to: '/commissioning',
    },
  ]
})
</script>

<template>
  <div class="page-container animate-fade-in">

    <!-- Page header -->
    <div class="flex items-start justify-between mb-6">
      <div>
        <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">AssetCore · HTM</p>
        <h1 class="text-2xl font-bold text-slate-900">Tổng quan quản trị thiết bị</h1>
        <p class="text-sm text-slate-500 mt-1" v-if="data">
          Cập nhật lần cuối: <span class="font-mono">{{ data.generated_at.slice(0, 19) }}</span>
        </p>
      </div>
      <button class="btn-secondary flex items-center gap-2" :disabled="loading" @click="refresh">
        <svg class="w-4 h-4" :class="{ 'animate-spin': loading }" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round"
                d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
        </svg>
        {{ loading ? 'Đang tải...' : 'Làm mới' }}
      </button>
    </div>

    <div v-if="error" class="alert-error mb-6">{{ error }}</div>

    <!-- ═════════ DÒNG 1: KPI CARDS ═════════ -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      <button v-for="(c, i) in kpiCards" :key="i"
              class="card p-5 flex items-start gap-4 text-left hover:shadow-md hover:-translate-y-0.5 transition-all"
              @click="router.push(c.to)">
        <div class="w-11 h-11 rounded-xl flex items-center justify-center shrink-0" :class="c.bg">
          <svg class="w-5 h-5" :class="c.accent" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" :d="c.icon" />
          </svg>
        </div>
        <div class="flex-1 min-w-0">
          <p class="text-xs font-medium text-slate-500 truncate">{{ c.label }}</p>
          <p class="text-2xl font-bold tabular-nums mt-0.5" :class="c.accent">{{ fmt(c.value) }}</p>
        </div>
      </button>
      <!-- Skeleton -->
      <template v-if="!kpi && loading">
        <div v-for="i in 4" :key="i" class="card p-5">
          <div class="animate-pulse space-y-3">
            <div class="h-4 w-24 bg-slate-200 rounded" />
            <div class="h-6 w-16 bg-slate-200 rounded" />
          </div>
        </div>
      </template>
    </div>

    <!-- ═════════ DÒNG 2: DONUT + ACTIVE REPAIRS ═════════ -->
    <div class="grid grid-cols-1 lg:grid-cols-5 gap-4 mb-6">
      <!-- Donut chart — 40% -->
      <div class="lg:col-span-2 card p-5">
        <h3 class="text-sm font-semibold text-slate-800 mb-5">
          Tổng quan Trạng thái Thiết bị
        </h3>
        <div v-if="loading && !data" class="animate-pulse flex items-center justify-center h-48">
          <div class="w-36 h-36 rounded-full bg-slate-100" />
        </div>
        <StatusDonutChart v-else
                         :labels="chart.labels"
                         :series="chart.series"
                         :colors="chart.colors" />
      </div>

      <!-- Active repairs — 60% -->
      <div class="lg:col-span-3">
        <ActiveRepairsList :repairs="repairs" />
      </div>
    </div>

    <!-- ═════════ DÒNG 3: UPCOMING MAINTENANCE ═════════ -->
    <UpcomingMaintenanceList :items="upcoming" />

  </div>
</template>
