<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useImm08Store } from '@/stores/imm08'
import { useRouter } from 'vue-router'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'

const store  = useImm08Store()
const router = useRouter()
const today  = new Date()
const year   = ref(today.getFullYear())
const month  = ref(today.getMonth() + 1)

onMounted(async () => {
  await Promise.all([
    store.fetchDashboardStats(year.value, month.value),
    store.fetchWorkOrders({ status: 'Overdue' }),
  ])
})

const kpis        = computed(() => store.dashboardStats?.kpis)
const trend       = computed(() => store.dashboardStats?.trend_6months ?? [])
const overdueWOs  = computed(() => store.overdueWOs)
const upcomingWOs = computed(() => {
  const sevenDaysLater = new Date()
  sevenDaysLater.setDate(sevenDaysLater.getDate() + 7)
  return store.workOrders.filter((w) => {
    if (!w.due_date || w.status === 'Completed') return false
    const due = new Date(w.due_date)
    return due >= today && due <= sevenDaysLater
  })
})
const monthLabel = computed(() =>
  new Date(year.value, month.value - 1, 1)
    .toLocaleDateString('vi-VN', { month: 'long', year: 'numeric' }),
)

const maxTrendRate = computed(() => Math.max(...trend.value.map((t) => t.rate), 1))

function complianceColor(rate: number): string {
  if (rate >= 90) return '#059669'
  if (rate >= 70) return '#d97706'
  return '#dc2626'
}
function daysUntil(dateStr: string): number {
  return Math.ceil((new Date(dateStr).getTime() - today.getTime()) / (1000 * 60 * 60 * 24))
}
</script>

<template>
  <div class="page-container animate-fade-in">

    <!-- Header -->
    <div class="flex items-start justify-between mb-7">
      <div>
        <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">IMM-08</p>
        <h1 class="text-2xl font-bold text-slate-900">Tổng quan Bảo trì Định kỳ</h1>
        <p class="text-sm text-slate-500 mt-1">{{ monthLabel }}</p>
      </div>
      <div class="flex gap-2.5 shrink-0">
        <button class="btn-secondary" @click="router.push('/pm/calendar')">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24">
            <rect x="3" y="4" width="18" height="18" rx="2" />
            <line x1="16" y1="2" x2="16" y2="6" /><line x1="8" y1="2" x2="8" y2="6" />
            <line x1="3" y1="10" x2="21" y2="10" />
          </svg>
          Lịch PM
        </button>
        <button class="btn-primary" @click="router.push('/pm/work-orders')">Danh sách phiếu</button>
      </div>
    </div>

    <!-- KPI Cards -->
    <SkeletonLoader v-if="store.loading && !kpis" variant="kpi-cards" class="mb-7" />

    <div v-else-if="kpis" class="grid grid-cols-2 lg:grid-cols-5 gap-4 mb-7">
      <!-- Compliance rate — large card -->
      <div class="kpi-card p-5 lg:col-span-1 flex flex-col items-start gap-2"
           style="--kpi-color: v-bind('complianceColor(kpis.compliance_rate_pct)')">
        <p class="text-xs font-medium text-slate-500">Tỷ lệ tuân thủ</p>
        <p class="text-4xl font-bold leading-none"
           :style="`color: ${complianceColor(kpis.compliance_rate_pct)}`">
          {{ kpis.compliance_rate_pct }}%
        </p>
        <!-- Mini progress bar -->
        <div class="w-full h-1.5 rounded-full bg-slate-100 mt-1">
          <div class="h-full rounded-full animate-bar-fill"
               :style="`width:${kpis.compliance_rate_pct}%; background:${complianceColor(kpis.compliance_rate_pct)}`" />
        </div>
      </div>
      <div class="kpi-card p-5" style="--kpi-color: #334155">
        <p class="text-xs font-medium text-slate-500 mb-2">Tổng lên lịch</p>
        <p class="text-3xl font-bold text-slate-800">{{ kpis.total_scheduled }}</p>
      </div>
      <div class="kpi-card p-5" style="--kpi-color: #059669">
        <p class="text-xs font-medium text-slate-500 mb-2">Hoàn thành đúng hạn</p>
        <p class="text-3xl font-bold text-emerald-600">{{ kpis.completed_on_time }}</p>
      </div>
      <div class="kpi-card p-5" style="--kpi-color: #dc2626">
        <p class="text-xs font-medium text-slate-500 mb-2">Quá hạn</p>
        <p class="text-3xl font-bold text-red-600">{{ kpis.overdue }}</p>
      </div>
      <div class="kpi-card p-5" style="--kpi-color: #d97706">
        <p class="text-xs font-medium text-slate-500 mb-2">Trễ TB (ngày)</p>
        <p class="text-3xl font-bold text-amber-600">{{ kpis.avg_days_late }}</p>
      </div>
    </div>

    <!-- Trend chart -->
    <div class="card mb-6 animate-slide-up" style="animation-delay: 200ms">
      <h3 class="text-sm font-semibold text-slate-800 mb-5">Xu hướng Compliance 6 tháng</h3>
      <div class="flex items-end gap-2" style="height: 96px">
        <div
          v-for="t in trend"
          :key="t.month"
          class="flex flex-col items-center flex-1 gap-1.5 h-full justify-end"
        >
          <span class="text-[11px] font-semibold tabular-nums"
                :style="`color: ${complianceColor(t.rate)}`">{{ t.rate }}%</span>
          <div
            class="w-full rounded-t-md min-h-[4px] animate-bar-fill"
            :style="`height:${Math.max(4, (t.rate / maxTrendRate) * 72)}px; background:${complianceColor(t.rate)}; opacity:0.75`"
          />
          <span class="text-[10px] text-slate-400">{{ t.month.slice(5) }}/{{ t.month.slice(2, 4) }}</span>
        </div>
        <div v-if="!trend.length"
             class="flex-1 text-center text-slate-400 text-sm self-center">Chưa có dữ liệu</div>
      </div>
    </div>

    <!-- Two-column: overdue + upcoming -->
    <div class="grid md:grid-cols-2 gap-6">

      <!-- Quá hạn -->
      <div class="card p-0 overflow-hidden animate-slide-up" style="animation-delay: 260ms">
        <div class="flex items-center gap-2.5 px-5 py-4 border-b border-slate-100">
          <span class="w-2 h-2 rounded-full bg-red-500 animate-pulse-subtle" />
          <h3 class="text-sm font-semibold text-slate-800">
            Quá hạn PM
            <span class="ml-1 text-xs font-normal text-red-500">({{ overdueWOs.length }})</span>
          </h3>
        </div>
        <div v-if="store.loading" class="p-4">
          <SkeletonLoader variant="list" :rows="4" />
        </div>
        <div v-else-if="overdueWOs.length === 0"
             class="px-5 py-10 text-center text-sm text-slate-400">
          Không có thiết bị quá hạn
        </div>
        <div v-else class="divide-y divide-slate-100">
          <div
            v-for="wo in overdueWOs.slice(0, 8)"
            :key="wo.name"
            class="flex items-center justify-between px-5 py-3 hover:bg-red-50 transition-colors cursor-pointer"
            @click="router.push(`/pm/work-orders/${wo.name}`)"
          >
            <div class="min-w-0">
              <p class="text-sm font-medium text-slate-800 truncate">{{ wo.asset_name || wo.asset_ref }}</p>
              <p class="text-[11px] font-mono text-slate-400 mt-0.5">{{ wo.name }}</p>
            </div>
            <div class="text-right shrink-0 ml-3">
              <span class="text-[11px] font-semibold bg-red-100 text-red-700 px-2 py-0.5 rounded-full">
                Quá hạn
              </span>
              <p class="text-[11px] text-slate-400 mt-1">{{ wo.due_date }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Sắp đến hạn -->
      <div class="card p-0 overflow-hidden animate-slide-up" style="animation-delay: 300ms">
        <div class="flex items-center gap-2.5 px-5 py-4 border-b border-slate-100">
          <span class="w-2 h-2 rounded-full bg-amber-400 animate-pulse-subtle" />
          <h3 class="text-sm font-semibold text-slate-800">
            Đến hạn trong 7 ngày
            <span class="ml-1 text-xs font-normal text-amber-600">({{ upcomingWOs.length }})</span>
          </h3>
        </div>
        <div v-if="upcomingWOs.length === 0"
             class="px-5 py-10 text-center text-sm text-slate-400">
          Không có PM sắp đến hạn
        </div>
        <div v-else class="divide-y divide-slate-100">
          <div
            v-for="wo in upcomingWOs.slice(0, 8)"
            :key="wo.name"
            class="flex items-center justify-between px-5 py-3 hover:bg-amber-50 transition-colors cursor-pointer"
            @click="router.push(`/pm/work-orders/${wo.name}`)"
          >
            <div class="min-w-0">
              <p class="text-sm font-medium text-slate-800 truncate">{{ wo.asset_name || wo.asset_ref }}</p>
              <p class="text-[11px] text-slate-400 mt-0.5">{{ wo.pm_type }}</p>
            </div>
            <div class="text-right shrink-0 ml-3">
              <span class="text-[11px] font-semibold bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full">
                {{ daysUntil(wo.due_date!) }} ngày
              </span>
              <p class="text-[11px] text-slate-400 mt-1">{{ wo.due_date }}</p>
            </div>
          </div>
        </div>
      </div>

    </div>
  </div>
</template>
