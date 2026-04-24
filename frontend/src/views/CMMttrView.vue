<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useImm09Store } from '@/stores/imm09'

const store = useImm09Store()

const now = new Date()
const selectedYear = ref(now.getFullYear())
const selectedMonth = ref(now.getMonth() + 1)

const MONTHS = [
  'Tháng 1', 'Tháng 2', 'Tháng 3', 'Tháng 4', 'Tháng 5', 'Tháng 6',
  'Tháng 7', 'Tháng 8', 'Tháng 9', 'Tháng 10', 'Tháng 11', 'Tháng 12',
]

async function loadData() {
  await store.fetchMttrReport(selectedYear.value, selectedMonth.value)
}

onMounted(loadData)
watch([selectedYear, selectedMonth], loadData)

const report = computed(() => store.mttrReport)
const loading = computed(() => store.loading)

const trendMax = computed(() => {
  if (!report.value?.mttr_trend?.length) return 30
  return Math.max(...report.value.mttr_trend.map(t => t.value), 1)
})

const deptMax = computed(() => {
  if (!report.value?.backlog_by_dept?.length) return 1
  return Math.max(...report.value.backlog_by_dept.map(d => d.count), 1)
})

function formatHours(h: number): string {
  return h.toFixed(1)
}
</script>

<template>
  <div class="page-container animate-fade-in">
    <!-- Header -->
    <div class="flex items-start justify-between mb-7">
      <div>
        <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">IMM-09 / Báo cáo</p>
        <h1 class="text-2xl font-bold text-slate-900">Thời gian Sửa chữa Trung bình</h1>
        <p class="text-sm text-slate-500 mt-1">Phân tích hiệu suất sửa chữa thiết bị</p>
      </div>
      <div class="flex items-center gap-3 shrink-0">
        <!-- Month selector -->
        <select
          v-model="selectedMonth"
          class="form-select w-36"
        >
          <option v-for="(label, i) in MONTHS" :key="i + 1" :value="i + 1">{{ label }}</option>
        </select>
        <select v-model="selectedYear" class="form-select w-28">
          <option v-for="y in [2025, 2026, 2027]" :key="y" :value="y">{{ y }}</option>
        </select>
        <!-- Export buttons (UI only) -->
        <button disabled class="px-4 py-2 border border-gray-300 rounded-lg text-sm text-gray-400 cursor-not-allowed">
          Xuất PDF
        </button>
        <button disabled class="px-4 py-2 border border-gray-300 rounded-lg text-sm text-gray-400 cursor-not-allowed">
          Xuất Excel
        </button>
      </div>
    </div>

    <!-- KPI Skeleton -->
    <div v-if="loading && !report" class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-7">
      <div v-for="i in 4" :key="i" class="kpi-card p-5 animate-pulse">
        <div class="h-3 bg-slate-200 rounded w-24 mb-3"/>
        <div class="h-8 bg-slate-200 rounded w-16"/>
      </div>
    </div>

    <!-- KPI Cards -->
    <div v-else-if="report" class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-7">
      <div class="kpi-card p-5 slide-up-enter-active" style="--kpi-color: #2563eb; animation-delay: 0ms">
        <p class="text-xs font-medium text-slate-500 mb-1">Thời gian sửa TB</p>
        <p class="text-3xl font-bold text-blue-600">
          {{ formatHours(report.mttr_avg) }}<span class="text-base font-normal text-slate-400 ml-0.5">h</span>
        </p>
        <p class="text-xs text-slate-400 mt-1">Mục tiêu: ≤ 24h (Class III)</p>
      </div>
      <div class="kpi-card p-5" style="--kpi-color: #059669; animation-delay: 60ms">
        <p class="text-xs font-medium text-slate-500 mb-1">Tỷ lệ sửa đúng lần đầu</p>
        <p class="text-3xl font-bold text-emerald-600">
          {{ report.first_fix_rate }}<span class="text-base font-normal text-slate-400 ml-0.5">%</span>
        </p>
        <div class="w-full h-1.5 rounded-full bg-slate-100 mt-2">
          <div
            class="h-full rounded-full transition-all duration-500"
            :style="`width: ${report.first_fix_rate}%; background: #059669`"
          />
        </div>
      </div>
      <div class="kpi-card p-5" style="--kpi-color: #d97706; animation-delay: 120ms">
        <p class="text-xs font-medium text-slate-500 mb-1">Backlog WO</p>
        <p class="text-3xl font-bold text-amber-600">{{ report.backlog_count }}</p>
        <p class="text-xs text-slate-400 mt-1">phiếu chưa đóng</p>
      </div>
      <div class="kpi-card p-5" style="--kpi-color: #7c3aed; animation-delay: 180ms">
        <p class="text-xs font-medium text-slate-500 mb-1">Chi phí / Sửa</p>
        <p class="text-3xl font-bold text-violet-600">
          {{ (report.cost_per_repair / 1000).toFixed(0) }}<span class="text-base font-normal text-slate-400 ml-0.5">Kđ</span>
        </p>
      </div>
    </div>

    <div v-if="report" class="grid md:grid-cols-5 gap-6">
      <!-- MTTR Trend Chart (col-span-3) -->
      <div class="md:col-span-3 card animate-slide-up" style="animation-delay: 200ms">
        <div class="flex items-center justify-between mb-5">
          <h3 class="text-sm font-semibold text-slate-800">Biến động thời gian sửa chữa TB — 6 tháng gần nhất</h3>
          <div class="flex items-center gap-2 text-xs text-slate-400">
            <span class="inline-block w-3 h-0.5 bg-blue-500"></span> Thời gian sửa chữa TB
            <span class="inline-block w-3 h-0.5 bg-red-400 border-dashed ml-2"></span> SLA 24h
          </div>
        </div>

        <div v-if="!report.mttr_trend?.length" class="text-center text-slate-400 text-sm py-10">
          Chưa có dữ liệu trend
        </div>
        <div v-else class="flex items-end gap-3 h-40">
          <div
            v-for="item in report.mttr_trend"
            :key="item.month"
            class="flex-1 flex flex-col items-center gap-1"
          >
            <span class="text-xs font-semibold text-slate-700 tabular-nums">{{ item.value }}h</span>
            <div class="relative w-full">
              <div
                class="w-full rounded-t transition-all duration-500"
                :style="{
                  height: `${Math.round((item.value / trendMax) * 120)}px`,
                  background: item.value > 24 ? '#ef4444' : '#3b82f6',
                  minHeight: '4px'
                }"
              />
            </div>
            <span class="text-[10px] text-slate-400 text-center">{{ item.month }}</span>
          </div>
        </div>
        <!-- SLA reference line note -->
        <p class="text-xs text-slate-400 mt-3">SLA target Class III: 24h</p>
      </div>

      <!-- Backlog by dept (col-span-2) -->
      <div class="md:col-span-2 card animate-slide-up" style="animation-delay: 260ms">
        <h3 class="text-sm font-semibold text-slate-800 mb-5">Backlog theo Khoa/Phòng</h3>
        <div v-if="!report.backlog_by_dept?.length" class="text-center text-slate-400 text-sm py-10">
          Không có backlog
        </div>
        <div v-else class="space-y-3">
          <div
            v-for="dept in report.backlog_by_dept"
            :key="dept.dept"
            class="flex items-center gap-3"
          >
            <span class="w-20 text-xs text-slate-500 text-right shrink-0 truncate" :title="dept.dept">
              {{ dept.dept }}
            </span>
            <div class="flex-1 h-2.5 rounded-full overflow-hidden bg-slate-100">
              <div
                class="h-full rounded-full bg-orange-400 transition-all duration-500"
                :style="`width: ${(dept.count / deptMax) * 100}%`"
              />
            </div>
            <span class="text-xs font-semibold text-slate-700 w-6 text-right shrink-0 tabular-nums">
              {{ dept.count }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- Empty state -->
    <div v-else-if="!loading" class="card text-center py-16 text-slate-400">
      <svg class="w-12 h-12 mx-auto mb-3 text-slate-300" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>
      </svg>
      <p class="text-sm">Chưa có dữ liệu thời gian sửa chữa cho tháng {{ selectedMonth }}/{{ selectedYear }}</p>
    </div>
  </div>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

.slide-up-enter-active { transition: all 0.3s ease-out; }
.slide-up-enter-from { transform: translateY(8px); opacity: 0; }
</style>
