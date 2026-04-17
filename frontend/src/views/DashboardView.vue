<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { getDashboardStats } from '@/api/imm04'
import StatusBadge from '@/components/common/StatusBadge.vue'
import { formatDate } from '@/utils/docUtils'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import type { DashboardStats, CommissioningListItem, WorkflowState } from '@/types/imm04'

const router = useRouter()

const stats = ref<DashboardStats | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)
const stateFilter = ref<WorkflowState | ''>('')

const filteredRecent = computed<CommissioningListItem[]>(() => {
  if (!stats.value) return []
  if (!stateFilter.value) return stats.value.recent_list
  return stats.value.recent_list.filter((r) => r.workflow_state === stateFilter.value)
})

async function fetchStats() {
  loading.value = true
  error.value = null
  try {
    const res = await getDashboardStats()
    if (res.success && res.data) {
      stats.value = res.data
    } else {
      error.value = res.error ?? 'Không thể tải Dashboard'
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Lỗi không xác định'
  } finally {
    loading.value = false
  }
}

function goToDetail(name: string) {
  router.push(`/commissioning/${name}`)
}

function goToList(filter?: WorkflowState) {
  const query = filter ? { workflow_state: filter } : {}
  router.push({ path: '/commissioning', query })
}

interface KpiCard {
  key: keyof typeof stats.value.kpis
  label: string
  icon: string
  colorClass: string
  bgClass: string
  filterState?: WorkflowState
}

const kpiCards = computed<KpiCard[]>(() => [
  {
    key: 'pending_count',
    label: 'Phiếu đang xử lý',
    icon: 'clock',
    colorClass: 'text-blue-700',
    bgClass: 'bg-blue-50',
  },
  {
    key: 'hold_count',
    label: 'Clinical Hold',
    icon: 'pause',
    colorClass: 'text-red-700',
    bgClass: 'bg-red-50',
    filterState: 'Clinical_Hold',
  },
  {
    key: 'open_nc_count',
    label: 'NC chưa xử lý',
    icon: 'exclamation',
    colorClass: 'text-orange-700',
    bgClass: 'bg-orange-50',
  },
  {
    key: 'released_this_month',
    label: 'Phát hành tháng này',
    icon: 'check',
    colorClass: 'text-green-700',
    bgClass: 'bg-green-50',
    filterState: 'Clinical_Release',
  },
])

const uniqueStates = computed<WorkflowState[]>(() => {
  if (!stats.value) return []
  return [...new Set(stats.value.recent_list.map((r) => r.workflow_state))]
})

function getKpiValue(key: string): number {
  if (!stats.value) return 0
  return (stats.value.kpis as Record<string, number>)[key] ?? 0
}

onMounted(fetchStats)
</script>

<template>
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
    <!-- Page header -->
    <div class="flex items-center justify-between mb-8">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Dashboard IMM-04</h1>
        <p class="text-sm text-gray-500 mt-1">Tổng quan quy trình Đưa vào sử dụng Thiết bị Y tế</p>
      </div>
      <div class="flex gap-3">
        <button class="btn-secondary" :disabled="loading" @click="fetchStats">
          <svg class="w-4 h-4" :class="loading ? 'animate-spin' : ''" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Làm mới
        </button>
        <button class="btn-primary" @click="goToList()">
          Xem tất cả phiếu
        </button>
      </div>
    </div>

    <LoadingSpinner v-if="loading" size="lg" label="Đang tải Dashboard..." class="py-20" />

    <div v-else-if="error" class="card text-center py-12">
      <p class="text-red-600 mb-4">{{ error }}</p>
      <button class="btn-primary" @click="fetchStats">Thử lại</button>
    </div>

    <template v-else-if="stats">
      <!-- KPI Cards -->
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <button
          v-for="card in kpiCards"
          :key="card.key"
          class="card text-left hover:shadow-md transition-shadow cursor-pointer"
          @click="card.filterState ? goToList(card.filterState) : goToList()"
        >
          <div class="flex items-center justify-between mb-4">
            <div
              :class="['w-10 h-10 rounded-lg flex items-center justify-center', card.bgClass]"
            >
              <!-- Clock icon -->
              <svg v-if="card.icon === 'clock'" :class="['w-5 h-5', card.colorClass]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <!-- Pause icon -->
              <svg v-else-if="card.icon === 'pause'" :class="['w-5 h-5', card.colorClass]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 9v6m4-6v6m7-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <!-- Exclamation icon -->
              <svg v-else-if="card.icon === 'exclamation'" :class="['w-5 h-5', card.colorClass]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              <!-- Check icon -->
              <svg v-else-if="card.icon === 'check'" :class="['w-5 h-5', card.colorClass]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
          </div>

          <p class="text-3xl font-bold text-gray-900 mb-1">{{ getKpiValue(card.key) }}</p>
          <p class="text-sm text-gray-500">{{ card.label }}</p>
        </button>
      </div>

      <!-- SLA Overdue alert -->
      <div
        v-if="stats.kpis.overdue_sla > 0"
        class="flex items-center gap-3 p-4 mb-6 bg-red-50 border border-red-200 rounded-lg"
      >
        <svg class="w-5 h-5 text-red-600 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
        <p class="text-sm text-red-700">
          <strong>{{ stats.kpis.overdue_sla }} phiếu</strong> đã quá hạn SLA 30 ngày và chưa được Phát hành.
        </p>
        <button class="ml-auto text-sm text-red-600 underline hover:no-underline" @click="goToList()">
          Xem ngay
        </button>
      </div>

      <!-- State Breakdown + Recent list -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <!-- State breakdown chart -->
        <div class="card">
          <h3 class="text-base font-semibold text-gray-900 mb-4">Phân bố theo Trạng thái</h3>
          <div class="space-y-3">
            <div
              v-for="s in stats.states_breakdown"
              :key="s.workflow_state"
              class="flex items-center gap-3"
            >
              <StatusBadge :state="s.workflow_state" size="sm" class="flex-shrink-0 w-40 justify-center" />
              <div class="flex-1 bg-gray-100 rounded-full h-2">
                <div
                  class="h-2 bg-blue-500 rounded-full"
                  :style="{ width: `${Math.min((s.count / Math.max(...stats!.states_breakdown.map(x => x.count))) * 100, 100)}%` }"
                />
              </div>
              <span class="text-sm font-semibold text-gray-700 w-8 text-right">{{ s.count }}</span>
            </div>
          </div>
        </div>

        <!-- Recent list -->
        <div class="card lg:col-span-2">
          <div class="flex items-center justify-between mb-4">
            <h3 class="text-base font-semibold text-gray-900">Phiếu gần đây</h3>
            <select v-model="stateFilter" class="form-select text-sm w-48">
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
              <tbody class="divide-y divide-gray-100">
                <tr
                  v-for="item in filteredRecent"
                  :key="item.name"
                  class="table-row cursor-pointer"
                  @click="goToDetail(item.name)"
                >
                  <td class="table-cell font-mono text-blue-600 hover:underline">{{ item.name }}</td>
                  <td class="table-cell max-w-32 truncate">{{ item.master_item }}</td>
                  <td class="table-cell">{{ item.clinical_dept }}</td>
                  <td class="px-6 py-4">
                    <StatusBadge :state="item.workflow_state" />
                  </td>
                  <td class="table-cell text-gray-500 text-xs">
                    {{ formatDate(item.modified) }}
                  </td>
                </tr>
                <tr v-if="!filteredRecent.length">
                  <td colspan="5" class="px-6 py-8 text-center text-gray-400 text-sm">
                    Không có phiếu nào.
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
