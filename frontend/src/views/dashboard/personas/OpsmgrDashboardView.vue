<script setup lang="ts">
// Dashboard — Trưởng phòng VT-TTBYT (opsmgr). Core Doc §5.2 + §9.4.
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { usePersonaDashboard } from '@/composables/useDashboard'
import { sectionRows, sectionObject } from '@/api/dashboard'
import { translateStatus } from '@/utils/formatters'
import PersonaDashboardShell from '@/components/dashboard/PersonaDashboardShell.vue'
import DashboardSection from '@/components/dashboard/DashboardSection.vue'
import StatusDonutChart from '@/components/dashboard/StatusDonutChart.vue'
import BarsCard from '@/components/dashboard/BarsCard.vue'
import TimelineCard from '@/components/dashboard/TimelineCard.vue'
import { useSectionDrill } from '@/composables/useSectionDrill'

const drill = useSectionDrill()
const router = useRouter()
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
    // Core Doc §9.2 — canonical code (English) cho drill query; fallback state.
    codes: rows.map((r) => String(r.code ?? r.state ?? '')),
  }
})

// Core Doc §9.4 — click segment donut → /assets?lifecycle_status=<canonical code>.
function onStatusSegment(p: { label: string; code: string; value: number }): void {
  if (!p.code) return
  router.push({ path: '/assets', query: { lifecycle_status: p.code } })
}

// R8 §9.4.6 — donut severity: phân bổ severity của incident MỞ → click segment
// route /incidents/list?severity=<canonical code>.
const severityDonut = computed(() => {
  const rows = sectionRows(sec.value, 'incident_severity_breakdown')
  const SEV_COLOR: Record<string, string> = {
    Critical: '#ef4444', High: '#f59e0b', Medium: '#3b82f6', Low: '#10b981',
  }
  return {
    labels: rows.map((r) => String(r.label_vi ?? r.code ?? '')),
    series: rows.map((r) => Number(r.count ?? 0)),
    colors: rows.map((r) => SEV_COLOR[String(r.code ?? '')] ?? '#94a3b8'),
    codes: rows.map((r) => String(r.code ?? '')),
  }
})
// open=1 → list áp SoT open_incident_filter() (incident đang mở) khớp donut count:
// donut-segment count == số dòng list sau drill (cùng severity, cùng open-set).
function onSeveritySegment(p: { label: string; code: string; value: number }): void {
  if (!p.code) return
  router.push({ path: '/incidents/list', query: { severity: p.code, open: '1' } })
}

type BarDrill = { route: string; query: Record<string, string> } | null | undefined
const mkBars = computed(() => {
  const m = sectionObject(sec.value, 'maintenance_kpi')
  const d = (m.drills ?? {}) as Record<string, BarDrill>
  // R8 §9.4.6 — bar drill từ BE descriptor. MTTR là metric thời lượng (không có
  // list 1-1) → KHÔNG drill (canonical-value rule §9.5 #10).
  return [
    { label: 'Thời gian sửa chữa trung bình (h)', value: Number(m.mttr_avg_hours ?? 0), drill: null },
    { label: 'Cam kết mức dịch vụ (%)', value: Number(m.sla_compliance_pct ?? 0), suffix: '%', drill: d.sla_compliance_pct ?? null },
    { label: 'Lệnh công việc mở', value: Number(m.open_wos ?? 0), drill: d.open_wos ?? null },
    { label: 'Lặp lỗi', value: Number(m.repeat_failure_count ?? 0), drill: d.repeat_failure_count ?? null },
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
    <div class="grid grid-cols-1 gap-5 xl:grid-cols-5">
      <DashboardSection
        class="xl:col-span-2"
        title="Tình trạng thiết bị"
        hint="Nhấp vào một phần để xem danh sách thiết bị tương ứng"
      >
        <StatusDonutChart
          :labels="donut.labels"
          :series="donut.series"
          :colors="donut.colors"
          :codes="donut.codes"
          drill-route="/assets"
          @segment-click="onStatusSegment"
        />
      </DashboardSection>
      <div class="xl:col-span-3">
        <BarsCard title="Chỉ số hiệu suất bảo trì kỳ này" :bars="mkBars" />
      </div>
    </div>
    <div class="grid grid-cols-1 gap-5 xl:grid-cols-5">
      <DashboardSection
        class="xl:col-span-2"
        title="Sự cố theo mức độ"
        hint="Nhấp vào một phần để xem danh sách sự cố tương ứng"
      >
        <StatusDonutChart
          :labels="severityDonut.labels"
          :series="severityDonut.series"
          :colors="severityDonut.colors"
          :codes="severityDonut.codes"
          drill-route="/incidents/list"
          @segment-click="onSeveritySegment"
        />
      </DashboardSection>
      <div class="xl:col-span-3 grid grid-cols-1 gap-5 lg:grid-cols-2">
        <TimelineCard title="Sự cố gần đây" :rows="recentEvents" :row-to="drill.incident" />
        <TimelineCard
          title="Bảo trì định kỳ sắp tới"
          :rows="recentPm"
          empty-text="Không có bảo trì định kỳ"
          :row-to="(r) => drill.pmWo({ name: r.name })"
        />
      </div>
    </div>
  </PersonaDashboardShell>
</template>
