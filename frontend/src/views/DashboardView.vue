<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { getDashboardStats } from '@/api/imm04'
import StatusBadge from '@/components/common/StatusBadge.vue'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
import { formatDate } from '@/utils/docUtils'
import type { DashboardStats, CommissioningListItem, WorkflowState } from '@/types/imm04'

const router = useRouter()
const stats  = ref<DashboardStats | null>(null)
const loading = ref(false)
const error   = ref<string | null>(null)
const stateFilter = ref<WorkflowState | ''>('')

const filteredRecent = computed<CommissioningListItem[]>(() => {
  if (!stats.value) return []
  if (!stateFilter.value) return stats.value.recent_list
  return stats.value.recent_list.filter((r) => r.workflow_state === stateFilter.value)
})

const uniqueStates = computed<WorkflowState[]>(() => {
  if (!stats.value) return []
  return [...new Set(stats.value.recent_list.map((r) => r.workflow_state))]
})

const maxStateCount = computed(() =>
  Math.max(...(stats.value?.states_breakdown.map((s) => s.count) ?? [1]), 1),
)

interface KpiCard {
  key:    'pending_count' | 'hold_count' | 'open_nc_count' | 'released_this_month' | 'overdue_sla'
  label:  string
  color:  string
  filter?: WorkflowState
}

const kpiCards: KpiCard[] = [
  { key: 'pending_count',       label: 'Đang xử lý',           color: '#2563eb' },
  { key: 'hold_count',          label: 'Clinical Hold',         color: '#dc2626', filter: 'Clinical_Hold' },
  { key: 'open_nc_count',       label: 'NC chưa xử lý',        color: '#d97706' },
  { key: 'released_this_month', label: 'Phát hành tháng này',  color: '#059669', filter: 'Clinical_Release' },
]

function kpiValue(key: string): number {
  if (!stats.value) return 0
  return (stats.value.kpis as Record<string, number>)[key] ?? 0
}

async function fetchStats() {
  loading.value = true
  error.value   = null
  try {
    const res = await getDashboardStats()
    if (res.success && res.data) stats.value = res.data
    else error.value = res.error ?? 'Không thể tải Dashboard'
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Lỗi không xác định'
  } finally {
    loading.value = false
  }
}

function goToList(filter?: WorkflowState) {
  const query = filter ? { workflow_state: filter } : {}
  router.push({ path: '/commissioning', query })
}

onMounted(fetchStats)
</script>

<template>
  <div class="page-container animate-fade-in">

    <!-- Page header -->
    <div class="flex items-start justify-between mb-7">
      <div>
        <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">Tổng quan</p>
        <h1 class="text-2xl font-bold text-slate-900 leading-tight">Dashboard IMM-04</h1>
        <p class="text-sm text-slate-500 mt-1">Quy trình Đưa vào sử dụng Thiết bị Y tế</p>
      </div>
      <div class="flex gap-2.5 shrink-0">
        <button
          class="btn-secondary"
          :disabled="loading"
          @click="fetchStats"
        >
          <svg class="w-4 h-4" :class="loading ? 'animate-spin-slow' : ''"
               fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round"
                  d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Làm mới
        </button>
        <button class="btn-primary" @click="goToList()">
          Xem tất cả phiếu
        </button>
      </div>
    </div>

    <!-- Loading: KPI skeleton -->
    <template v-if="loading && !stats">
      <SkeletonLoader variant="kpi-cards" class="mb-7" />
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <SkeletonLoader variant="card" :rows="6" />
        <SkeletonLoader variant="table" :rows="5" class="lg:col-span-2" />
      </div>
    </template>

    <!-- Error -->
    <div v-else-if="error && !stats" class="card text-center py-14">
      <div class="w-12 h-12 rounded-full bg-red-50 flex items-center justify-center mx-auto mb-4">
        <svg class="w-6 h-6 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
      </div>
      <p class="text-sm font-medium text-slate-700 mb-1">Không thể tải Dashboard</p>
      <p class="text-xs text-red-500 mb-5">{{ error }}</p>
      <button class="btn-primary" @click="fetchStats">Thử lại</button>
    </div>

    <template v-else-if="stats">

      <!-- SLA overdue alert -->
      <Transition
        enter-active-class="transition duration-300 ease-out"
        enter-from-class="opacity-0 -translate-y-2"
        enter-to-class="opacity-100 translate-y-0"
      >
        <div
          v-if="stats.kpis.overdue_sla > 0"
          class="flex items-center gap-3 p-4 mb-6 rounded-xl border"
          style="background: #fff1f2; border-color: #fecdd3"
        >
          <div class="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
               style="background: #fee2e2">
            <svg class="w-4 h-4 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <p class="text-sm text-red-700 flex-1">
            <strong>{{ stats.kpis.overdue_sla }} phiếu</strong> đã quá hạn SLA 30 ngày và chưa được Phát hành.
          </p>
          <button
            class="text-xs font-semibold text-red-600 hover:text-red-800 transition-colors shrink-0"
            @click="goToList()"
          >
            Xem ngay →
          </button>
        </div>
      </Transition>

      <!-- KPI Cards -->
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-5 mb-7">
        <button
          v-for="(card, idx) in kpiCards"
          :key="card.key as string"
          class="kpi-card text-left p-5 animate-slide-up"
          :style="`--kpi-color: ${card.color}; animation-delay: ${idx * 60}ms`"
          @click="card.filter ? goToList(card.filter) : goToList()"
        >
          <p class="text-xs font-medium text-slate-500 mb-3">{{ card.label }}</p>
          <p class="text-3xl font-bold leading-none" :style="`color: ${card.color}`">
            {{ kpiValue(card.key as string) }}
          </p>
          <div class="mt-3 flex items-center gap-1 text-xs text-slate-400">
            <span>Xem chi tiết</span>
            <svg class="w-3 h-3" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
            </svg>
          </div>
        </button>
      </div>

      <!-- Charts + Recent list -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">

        <!-- State breakdown -->
        <div class="card animate-slide-up" style="animation-delay: 260ms">
          <h3 class="text-sm font-semibold text-slate-800 mb-5">Phân bố theo Trạng thái</h3>
          <div class="space-y-3">
            <div
              v-for="s in stats.states_breakdown"
              :key="s.workflow_state"
              class="flex items-center gap-3"
            >
              <div class="w-36 shrink-0">
                <StatusBadge :state="s.workflow_state" size="xs" />
              </div>
              <div class="flex-1 h-1.5 rounded-full overflow-hidden bg-slate-100">
                <div
                  class="h-full rounded-full bg-brand-500 animate-bar-fill"
                  :style="{ width: `${(s.count / maxStateCount) * 100}%` }"
                />
              </div>
              <span class="text-xs font-semibold text-slate-600 w-6 text-right tabular-nums">
                {{ s.count }}
              </span>
            </div>
            <div v-if="!stats.states_breakdown.length" class="text-center py-6 text-sm text-slate-400">
              Chưa có dữ liệu
            </div>
          </div>
        </div>

        <!-- Recent list -->
        <div class="card p-0 overflow-hidden lg:col-span-2 animate-slide-up" style="animation-delay: 300ms">
          <div class="flex items-center justify-between px-6 py-4 border-b border-slate-100">
            <h3 class="text-sm font-semibold text-slate-800">Phiếu gần đây</h3>
            <select v-model="stateFilter" class="form-select text-xs w-44 py-1.5">
              <option value="">Tất cả trạng thái</option>
              <option v-for="state in uniqueStates" :key="state" :value="state">{{ state }}</option>
            </select>
          </div>

          <div class="overflow-x-auto">
            <table class="min-w-full">
              <thead>
                <tr>
                  <th class="table-header">Phiếu</th>
                  <th class="table-header">Model</th>
                  <th class="table-header">Khoa</th>
                  <th class="table-header">Trạng thái</th>
                  <th class="table-header">Cập nhật</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100">
                <tr
                  v-for="(item, i) in filteredRecent"
                  :key="item.name"
                  class="table-row animate-slide-up"
                  :style="`animation-delay: ${320 + i * 40}ms`"
                  @click="router.push(`/commissioning/${item.name}`)"
                >
                  <td class="table-cell">
                    <span class="text-mono text-[12px] font-medium text-brand-600">{{ item.name }}</span>
                  </td>
                  <td class="table-cell text-slate-600 max-w-36 truncate">{{ item.master_item }}</td>
                  <td class="table-cell text-slate-600">{{ item.clinical_dept }}</td>
                  <td class="px-5 py-3.5">
                    <StatusBadge :state="item.workflow_state" />
                  </td>
                  <td class="table-cell text-slate-400 text-xs">{{ formatDate(item.modified) }}</td>
                </tr>
                <tr v-if="!filteredRecent.length">
                  <td colspan="5" class="px-5 py-12 text-center text-slate-400 text-sm">
                    Không có phiếu nào.
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="px-6 py-3 border-t border-slate-100">
            <button
              class="text-xs font-medium text-brand-600 hover:text-brand-700 transition-colors"
              @click="goToList()"
            >
              Xem tất cả phiếu →
            </button>
          </div>
        </div>

      </div>
    </template>

  </div>
</template>
