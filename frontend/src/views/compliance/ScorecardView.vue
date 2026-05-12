<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team — IMM-16
// Compliance Scorecard — current period + history + publish.
import { ref, computed, onMounted } from 'vue'
import { useImm16Store } from '@/stores/imm16'
import { useApi } from '@/composables/useApi'
import { getCurrentScorecard, getScorecardByPeriod } from '@/api/imm16'
import type { ComplianceScorecard } from '@/api/imm16'
import { formatDate } from '@/utils/formatters'
import PageHeader from '@/components/common/PageHeader.vue'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'

const store = useImm16Store()
const api = useApi()

const history = computed(() => store.scorecards)
const historyPagination = computed(() => store.scorecardsPagination)
const historyLoading = computed(() => store.scorecardsLoading)

const current = ref<ComplianceScorecard | null>(null)
const currentLoading = ref(false)
const selectedYear = ref<number>(new Date().getFullYear())
const selectedMonth = ref<number>(new Date().getMonth() + 1)
const scope = ref('Hospital')

function isFullScorecard(x: unknown): x is ComplianceScorecard {
  return !!x && typeof x === 'object' && 'score_pct' in (x as Record<string, unknown>)
}

async function loadCurrent() {
  currentLoading.value = true
  try {
    const res = await getScorecardByPeriod(selectedYear.value, selectedMonth.value, scope.value)
    current.value = isFullScorecard(res) ? res : null
  } catch (e) {
    console.error(e)
    current.value = null
  } finally {
    currentLoading.value = false
  }
}

async function loadLatest() {
  currentLoading.value = true
  try {
    const latest = await getCurrentScorecard(scope.value)
    current.value = isFullScorecard(latest) ? latest : null
    if (current.value) {
      selectedYear.value = current.value.period_year
      selectedMonth.value = current.value.period_month
    }
  } catch (e) {
    current.value = null
  } finally {
    currentLoading.value = false
  }
}

async function loadHistory(page = 1) {
  await store.fetchScorecards({ scope: scope.value }, page, 20)
}

async function publish() {
  if (!current.value) return
  if (!confirm(`Publish scorecard ${current.value.name}? Sau publish sẽ immutable (VR-09).`)) return
  const res = await api.run(() => store.actionPublishScorecard(current.value!.name), {
    successMessage: 'Đã publish scorecard',
  })
  if (res) await loadCurrent()
}

const trendClass = computed(() => {
  if (!current.value) return ''
  const t = current.value.trend_vs_prev_month
  if (t > 0) return 'text-emerald-600'
  if (t < 0) return 'text-red-600'
  return 'text-slate-500'
})
const trendIcon = computed(() => {
  if (!current.value) return ''
  const t = current.value.trend_vs_prev_month
  return t > 0 ? '▲' : t < 0 ? '▼' : '—'
})

onMounted(() => { loadLatest(); loadHistory() })
</script>

<template>
  <div class="page-container animate-fade-in space-y-5">
    <PageHeader
      title="Bảng điểm tuân thủ"
      subtitle="Compliance Scorecard theo kỳ"
      :breadcrumb="[{ label: 'IMM-16 · Tuân thủ' }, { label: 'Scorecard' }]"
    >
      <template #actions>
        <div class="flex items-center gap-2">
          <select v-model="scope" class="form-select text-sm" @change="loadCurrent(); loadHistory()">
            <option value="Hospital">Hospital</option>
            <option value="Department">Department</option>
          </select>
          <input v-model.number="selectedYear" type="number" class="form-input text-sm w-24" min="2020" max="2100" />
          <select v-model.number="selectedMonth" class="form-select text-sm">
            <option v-for="m in 12" :key="m" :value="m">Tháng {{ m }}</option>
          </select>
          <button class="btn-ghost text-sm" @click="loadCurrent">Tải</button>
        </div>
      </template>
    </PageHeader>

    <!-- Current scorecard card -->
    <div class="card p-6">
      <div v-if="currentLoading"><SkeletonLoader variant="form" :rows="4" /></div>
      <div v-else-if="!current" class="text-center py-12 text-slate-400">
        <p class="text-sm">Chưa có scorecard cho kỳ này.</p>
      </div>
      <template v-else>
        <div class="flex items-start justify-between mb-6">
          <div>
            <div class="text-xs text-slate-400 mb-1">{{ current.name }}</div>
            <div class="text-lg font-semibold text-slate-800">
              Kỳ {{ String(current.period_month).padStart(2, '0') }}/{{ current.period_year }}
              <span class="text-xs text-slate-400 font-normal ml-2">· {{ current.scope }}</span>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <span v-if="current.is_published"
                  class="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
              Đã publish · {{ formatDate(current.published_at) }}
            </span>
            <span v-else
                  class="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-slate-100 text-slate-600 border border-slate-200">
              Bản nháp
            </span>
            <button v-if="!current.is_published"
                    class="btn-primary text-sm" :disabled="api.loading.value"
                    @click="publish">
              Publish Scorecard
            </button>
          </div>
        </div>

        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div class="kpi-card p-4" style="--kpi-color: #059669">
            <p class="text-xs text-slate-400 mb-1">Điểm tuân thủ</p>
            <p class="text-3xl font-bold font-display tabular-nums text-emerald-600">
              {{ current.score_pct.toFixed(1) }}%
            </p>
            <p class="text-xs mt-1" :class="trendClass">
              {{ trendIcon }} {{ current.trend_vs_prev_month >= 0 ? '+' : '' }}{{ current.trend_vs_prev_month.toFixed(1) }} pp
            </p>
          </div>
          <div class="kpi-card p-4" style="--kpi-color: #2563eb">
            <p class="text-xs text-slate-400 mb-1">CAPA mở</p>
            <p class="text-3xl font-bold font-display tabular-nums text-blue-600">{{ current.capa_open_count }}</p>
          </div>
          <div class="kpi-card p-4" style="--kpi-color: #dc2626">
            <p class="text-xs text-slate-400 mb-1">CAPA quá hạn</p>
            <p class="text-3xl font-bold font-display tabular-nums text-red-600">{{ current.capa_overdue_count }}</p>
          </div>
          <div class="kpi-card p-4" style="--kpi-color: #334155">
            <p class="text-xs text-slate-400 mb-1">Người duyệt</p>
            <p class="text-sm font-medium text-slate-700 truncate">{{ current.approved_by_for_review || '—' }}</p>
          </div>
        </div>
      </template>
    </div>

    <!-- History list -->
    <div class="table-wrapper">
      <div class="px-4 py-3 border-b border-slate-100 bg-slate-50/60 text-sm font-medium text-slate-700">
        Lịch sử Scorecard ({{ historyPagination.total }})
      </div>
      <div v-if="historyLoading" class="p-4"><SkeletonLoader variant="table" :rows="4" /></div>
      <div v-else-if="!history.length" class="py-10 text-center text-slate-400 text-sm">Chưa có lịch sử</div>
      <div v-else class="overflow-x-auto">
        <table class="min-w-full divide-y divide-slate-100">
          <thead>
            <tr>
              <th class="table-header">Kỳ</th>
              <th class="table-header">Phạm vi</th>
              <th class="table-header">Điểm %</th>
              <th class="table-header">Δ vs trước</th>
              <th class="table-header">CAPA mở</th>
              <th class="table-header">CAPA quá hạn</th>
              <th class="table-header">Trạng thái</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr v-for="s in history" :key="s.name" class="hover:bg-slate-50 cursor-pointer"
                @click="selectedYear = s.period_year; selectedMonth = s.period_month; loadCurrent()">
              <td class="table-cell font-medium text-slate-800">{{ String(s.period_month).padStart(2, '0') }}/{{ s.period_year }}</td>
              <td class="table-cell text-slate-600">{{ s.scope }}</td>
              <td class="table-cell font-semibold tabular-nums">{{ s.score_pct.toFixed(1) }}%</td>
              <td class="table-cell tabular-nums"
                  :class="s.trend_vs_prev_month > 0 ? 'text-emerald-600' : s.trend_vs_prev_month < 0 ? 'text-red-600' : 'text-slate-500'">
                {{ s.trend_vs_prev_month >= 0 ? '+' : '' }}{{ s.trend_vs_prev_month.toFixed(1) }} pp
              </td>
              <td class="table-cell tabular-nums">{{ s.capa_open_count }}</td>
              <td class="table-cell tabular-nums">{{ s.capa_overdue_count }}</td>
              <td class="table-cell">
                <span :class="s.is_published ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-slate-100 text-slate-600 border-slate-200'"
                      class="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium border">
                  {{ s.is_published ? 'Published' : 'Draft' }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
