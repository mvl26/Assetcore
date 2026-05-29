<script setup lang="ts">
// Dashboard — Trưởng phòng VT-TTBYT (opsmgr). Core Doc §5.2.
import { computed } from 'vue'
import { usePersonaDashboard } from '@/composables/useDashboard'
import { sectionRows, sectionObject } from '@/api/dashboard'
import { translateStatus } from '@/utils/formatters'
import PersonaDashboardShell from '@/components/dashboard/PersonaDashboardShell.vue'
import StatusDonutChart from '@/components/dashboard/StatusDonutChart.vue'
import BarsCard from '@/components/dashboard/BarsCard.vue'
import TimelineCard from '@/components/dashboard/TimelineCard.vue'

const { data, isLoading, error, refetch } = usePersonaDashboard('opsmgr')
const kpis = computed(() => data.value?.kpis ?? [])
const sec = computed(() => data.value?.sections)
const recentEvents = computed(() => sectionRows(sec.value, 'recent_events'))
const recentPm = computed(() => sectionRows(sec.value, 'recent_pm'))

const donut = computed(() => {
  const rows = sectionRows(sec.value, 'asset_status_breakdown')
  return {
    labels: rows.map((r) => translateStatus(String(r.state ?? ''))),
    series: rows.map((r) => Number(r.count ?? 0)),
    colors: ['#10b981', '#3b82f6', '#ef4444', '#8b5cf6', '#64748b', '#94a3b8'],
  }
})
const mkBars = computed(() => {
  const m = sectionObject(sec.value, 'maintenance_kpi')
  return [
    { label: 'MTTR (h)', value: Number(m.mttr_avg_hours ?? 0) },
    { label: 'SLA (%)', value: Number(m.sla_compliance_pct ?? 0), suffix: '%' },
    { label: 'WO mở', value: Number(m.open_wos ?? 0) },
    { label: 'Lặp lỗi', value: Number(m.repeat_failure_count ?? 0) },
  ]
})
</script>

<template>
  <PersonaDashboardShell
    title="Bảng điều khiển — Trưởng phòng VT-TTBYT"
    subtitle="Tổng quan thiết bị, bảo trì, sự cố, tuân thủ"
    :kpis="kpis"
    :loading="isLoading"
    :error="error ? String(error.message ?? error) : null"
    @retry="refetch"
  >
    <div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <div class="rounded-xl border border-neutral-200 bg-white p-4">
        <h3 class="mb-3 text-sm font-semibold text-neutral-800">Tình trạng thiết bị</h3>
        <StatusDonutChart :labels="donut.labels" :series="donut.series" :colors="donut.colors" />
      </div>
      <BarsCard title="KPI bảo trì kỳ này" :bars="mkBars" />
    </div>
    <div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <TimelineCard title="Sự cố gần đây" :rows="recentEvents" />
      <TimelineCard title="PM sắp tới" :rows="recentPm" empty-text="Không có PM" />
    </div>
  </PersonaDashboardShell>
</template>
