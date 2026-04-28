<script setup lang="ts">
import { onMounted, computed } from 'vue'
import { useImm09Store } from '@/stores/imm09'
import { useRouter } from 'vue-router'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'

const store  = useImm09Store()
const router = useRouter()

onMounted(async () => {
  await Promise.all([
    store.fetchKPIs(),
    store.fetchWorkOrders({ status: ['Open', 'Assigned', 'Diagnosing', 'Pending Parts', 'In Repair'] }),
  ])
})

const kpis       = computed(() => store.kpis?.kpis)
const rootCauses = computed(() => store.kpis?.root_cause_breakdown ?? [])
const maxRoot    = computed(() => Math.max(...rootCauses.value.map((r) => r.count), 1))

function slaColor(rate: number): string {
  if (rate >= 90) return '#059669'
  if (rate >= 70) return '#d97706'
  return '#dc2626'
}

function priorityStyle(priority: string): string {
  const map: Record<string, string> = {
    Emergency: 'background:#fee2e2;color:#991b1b;font-weight:600',
    Urgent:    'background:#ffedd5;color:#9a3412',
    Normal:    'background:#f1f5f9;color:#475569',
  }
  return map[priority] ?? 'background:#f1f5f9;color:#475569'
}

function slaPercent(wo: Record<string, unknown>): number {
  if (!wo.open_datetime || !wo.sla_target_hours) return 0
  const elapsed = (Date.now() - new Date(wo.open_datetime as string).getTime()) / 3_600_000
  return Math.min(100, Math.round(((elapsed as number) / (wo.sla_target_hours as number)) * 100))
}

function slaBarColor(pct: number): string {
  if (pct >= 100) return '#ef4444'
  if (pct >= 75)  return '#f97316'
  if (pct >= 50)  return '#f59e0b'
  return '#10b981'
}

const woStatusMap: Record<string, string> = {
  Open:           'Open',
  Assigned:       'Assigned',
  Diagnosing:     'Diagnosing',
  'Pending Parts':'Pending_Parts',
  'In Repair':    'In_Repair',
}
</script>

<template>
  <div class="page-container animate-fade-in">
<!-- Header -->
    <div class="flex items-start justify-between mb-7">
      <div>
        <h1 class="text-2xl font-bold text-slate-900">Tổng quan Sửa chữa Khắc phục</h1>
        <p class="text-sm text-slate-500 mt-1">Theo dõi sửa chữa thiết bị theo thời gian thực</p>
      </div>
      <div class="flex gap-2.5 shrink-0">
        <button class="btn-primary" @click="router.push('/cm/create')">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          Tạo phiếu mới
        </button>
        <button class="btn-secondary" @click="router.push('/cm/work-orders')">Danh sách phiếu</button>
      </div>
    </div>

    <!-- KPI skeleton -->
    <SkeletonLoader v-if="store.loading && !kpis" variant="kpi-cards" class="mb-7" />

    <!-- KPI cards -->
    <div v-else-if="kpis" class="grid grid-cols-2 lg:grid-cols-5 gap-4 mb-7">
      <div class="kpi-card p-5" style="--kpi-color: #334155">
        <p class="text-xs font-medium text-slate-500 mb-2">Đã hoàn thành</p>
        <p class="text-3xl font-bold text-slate-800">{{ kpis.total_completed }}</p>
      </div>
      <div class="kpi-card p-5" style="--kpi-color: #2563eb">
        <p class="text-xs font-medium text-slate-500 mb-2">Thời gian sửa chữa trung bình</p>
        <p class="text-3xl font-bold text-brand-700">{{ kpis.mttr_avg_hours }}<span class="text-base font-normal text-slate-400 ml-0.5">h</span></p>
      </div>
      <div
class="kpi-card p-5"
           :style="`--kpi-color: ${slaColor(kpis.sla_compliance_pct)}`">
        <p class="text-xs font-medium text-slate-500 mb-2">SLA Compliance</p>
        <p class="text-3xl font-bold" :style="`color: ${slaColor(kpis.sla_compliance_pct)}`">
          {{ kpis.sla_compliance_pct }}%
        </p>
        <div class="w-full h-1 rounded-full bg-slate-100 mt-2">
          <div
class="h-full rounded-full"
               :style="`width:${kpis.sla_compliance_pct}%; background:${slaColor(kpis.sla_compliance_pct)}`" />
        </div>
      </div>
      <div class="kpi-card p-5" style="--kpi-color: #f97316">
        <p class="text-xs font-medium text-slate-500 mb-2">Tái hỏng (30 ngày)</p>
        <p class="text-3xl font-bold text-orange-500">{{ kpis.repeat_failure_count }}</p>
      </div>
      <div class="kpi-card p-5" style="--kpi-color: #d97706">
        <p class="text-xs font-medium text-slate-500 mb-2">Phiếu đang mở</p>
        <p class="text-3xl font-bold text-amber-600">{{ kpis.open_wos }}</p>
      </div>
    </div>

    <!-- Two-column: root cause + active WOs -->
    <div class="grid md:grid-cols-2 gap-6">
<!-- Root cause breakdown -->
      <div class="card animate-slide-up" style="animation-delay: 200ms">
        <h3 class="text-sm font-semibold text-slate-800 mb-5">Phân tích nguyên nhân hỏng</h3>
        <div class="space-y-3">
          <div v-for="rc in rootCauses" :key="rc.category" class="flex items-center gap-3">
            <div class="w-28 text-xs text-slate-500 text-right shrink-0 truncate" :title="rc.category">
              {{ rc.category }}
            </div>
            <div class="flex-1 h-2 rounded-full overflow-hidden bg-slate-100">
              <div
                class="h-full rounded-full bg-brand-500 animate-bar-fill"
                :style="`width: ${(rc.count / maxRoot) * 100}%`"
              />
            </div>
            <span class="text-xs font-semibold text-slate-700 w-5 text-right tabular-nums shrink-0">
              {{ rc.count }}
            </span>
          </div>
          <div v-if="!rootCauses.length" class="text-center text-slate-400 text-sm py-6">
            Chưa có dữ liệu
          </div>
        </div>
      </div>

      <!-- Active WOs with SLA bars -->
      <div class="card p-0 overflow-hidden animate-slide-up" style="animation-delay: 260ms">
        <div class="px-5 py-4 border-b border-slate-100">
          <h3 class="text-sm font-semibold text-slate-800">
            Phiếu đang xử lý
            <span class="ml-1 text-xs font-normal text-slate-400">({{ store.workOrders.length }})</span>
          </h3>
        </div>
        <div v-if="store.loading" class="p-4">
          <SkeletonLoader variant="list" :rows="5" />
        </div>
        <div
v-else-if="!store.workOrders.length"
             class="px-5 py-10 text-center text-sm text-slate-400">
          Không có phiếu nào đang mở
        </div>
        <div v-else class="divide-y divide-slate-100">
          <div
            v-for="wo in store.workOrders.slice(0, 6)"
            :key="wo.name"
            class="px-5 py-3.5 hover:bg-slate-50 transition-colors cursor-pointer"
            @click="router.push(`/cm/work-orders/${wo.name}`)"
          >
            <div class="flex items-start justify-between gap-2 mb-2">
              <div class="min-w-0">
                <p class="text-sm font-medium text-slate-800 truncate">
                  {{ wo.asset_name || wo.asset_ref }}
                </p>
                <p class="text-[11px] font-mono text-slate-400 mt-0.5">{{ wo.name }}</p>
              </div>
              <div class="flex items-center gap-1.5 shrink-0">
                <span
                  v-if="wo.is_repeat_failure"
                  class="text-[10px] font-semibold bg-orange-100 text-orange-600 px-1.5 py-0.5 rounded"
                >Tái hỏng</span>
                <span
                  class="text-[11px] font-medium px-2 py-0.5 rounded-full"
                  :style="priorityStyle(wo.priority)"
                >{{ wo.priority }}</span>
                <StatusBadge :state="woStatusMap[wo.status] ?? wo.status" size="xs" />
              </div>
            </div>
            <!-- SLA progress -->
            <div class="flex items-center gap-2">
              <div class="flex-1 h-1 rounded-full overflow-hidden bg-slate-100">
                <div
                  class="h-full rounded-full transition-all"
                  :style="`width:${slaPercent(wo)}%; background:${slaBarColor(slaPercent(wo))}`"
                />
              </div>
              <span
                class="text-[10px] font-semibold shrink-0 tabular-nums"
                :style="`color:${slaBarColor(slaPercent(wo))}`"
              >{{ slaPercent(wo) }}% SLA</span>
            </div>
          </div>
        </div>
      </div>
</div>
  </div>
</template>
