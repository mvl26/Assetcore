<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
import { ref, reactive, computed, onMounted } from 'vue'
import { useImm01Store } from '@/stores/imm01'
import type { ProcurementPlanState } from '@/types/imm01'
import { stateLabel, stateSlug, formatVnd } from '@/utils/wave2Labels'
import ListFilterBar, { type FilterChip } from '@/components/common/ListFilterBar.vue'
import FilterToggleButton from '@/components/common/FilterToggleButton.vue'
import PageHeader from '@/components/common/PageHeader.vue'

const store = useImm01Store()

const PLAN_STATES: ProcurementPlanState[] = ['Draft', 'Approved', 'Active', 'Closed']
const PLAN_PERIODS = ['Q1', 'Q2', 'Q3', 'Q4', 'Annual'] as const
const currentYear = new Date().getFullYear()
const YEARS = [currentYear - 1, currentYear, currentYear + 1, currentYear + 2]

const showFilters = ref(false)
const filters = reactive<{
  workflow_state: ProcurementPlanState | ''
  plan_period: typeof PLAN_PERIODS[number] | ''
  plan_year: number | ''
  search: string
}>({
  workflow_state: '',
  plan_period: '',
  plan_year: '',
  search: '',
})

function planPeriodLabel(p?: string): string {
  return ({ Q1: 'Quý 1', Q2: 'Quý 2', Q3: 'Quý 3', Q4: 'Quý 4', Annual: 'Cả năm' } as Record<string, string>)[p || ''] || (p || '')
}
function utilClass(pct?: number): string {
  if ((pct || 0) >= 100) return 'over'
  if ((pct || 0) >= 80)  return 'warn'
  return ''
}

const activeChips = computed<FilterChip[]>(() => {
  const c: FilterChip[] = []
  if (filters.workflow_state) c.push({ key: 'workflow_state', label: stateLabel(filters.workflow_state) })
  if (filters.plan_period)    c.push({ key: 'plan_period', label: planPeriodLabel(filters.plan_period) })
  if (filters.plan_year !== '') c.push({ key: 'plan_year', label: `Năm ${filters.plan_year}` })
  if (filters.search.trim())  c.push({ key: 'search', label: `"${filters.search.trim()}"` })
  return c
})

function buildPayload(): Record<string, unknown> {
  const f: Record<string, unknown> = {}
  if (filters.workflow_state) f.workflow_state = filters.workflow_state
  if (filters.plan_period)    f.plan_period = filters.plan_period
  if (filters.plan_year !== '') f.plan_year = filters.plan_year
  if (filters.search.trim())  f.search = filters.search.trim()
  return f
}
function applyFilters() { store.fetchPlans(buildPayload()) }
function resetFilters() {
  filters.workflow_state = ''
  filters.plan_period = ''
  filters.plan_year = ''
  filters.search = ''
  store.fetchPlans()
}
function clearChip(key: string) {
  if (key === 'plan_year') filters.plan_year = ''
  else (filters as Record<string, string>)[key] = ''
  applyFilters()
}
function quickFilter(key: 'workflow_state' | 'plan_period' | 'plan_year', value: string | number) {
  ;(filters as Record<string, string | number>)[key] = value
  showFilters.value = false
  applyFilters()
}

onMounted(() => store.fetchPlans())
</script>

<template>
  <div class="page-container animate-fade-in">
    <PageHeader title="Kế hoạch mua sắm" :subtitle="`Tổng ${store.plans.length} kế hoạch — gom đề xuất đã duyệt theo quý/năm.`">
      <template #actions>
        <FilterToggleButton v-model="showFilters" :count="activeChips.length" />
      </template>
    </PageHeader>

    <ListFilterBar
      :show="showFilters"
      v-model:search="filters.search"
      :chips="activeChips"
      search-placeholder="Tìm theo mã kế hoạch..."
      @apply="applyFilters"
      @reset="resetFilters"
      @clear-chip="clearChip"
    >
      <template #fields>
        <select v-model="filters.workflow_state" class="form-select text-sm" @change="applyFilters">
          <option value="">Tất cả trạng thái</option>
          <option v-for="s in PLAN_STATES" :key="s" :value="s">{{ stateLabel(s) }}</option>
        </select>
        <select v-model="filters.plan_period" class="form-select text-sm" @change="applyFilters">
          <option value="">Tất cả kỳ</option>
          <option v-for="p in PLAN_PERIODS" :key="p" :value="p">{{ planPeriodLabel(p) }}</option>
        </select>
        <select v-model.number="filters.plan_year" class="form-select text-sm" @change="applyFilters">
          <option value="">Tất cả năm</option>
          <option v-for="y in YEARS" :key="y" :value="y">{{ y }}</option>
        </select>
      </template>
    </ListFilterBar>

    <div v-if="store.error" class="alert-error mb-4">
      <strong>Lỗi:</strong> {{ store.error }}
      <button class="alert-close" @click="store.clearError()">×</button>
    </div>

    <div class="card overflow-hidden">
      <div class="flex items-center justify-between px-4 py-3 border-b border-slate-100 bg-slate-50/60">
        <span class="text-xs text-slate-500">
          <span v-if="activeChips.length > 0">Kết quả lọc: <strong class="text-slate-700">{{ store.plans.length }}</strong> kế hoạch</span>
          <span v-else>Hiển thị <strong class="text-slate-700">{{ store.plans.length }}</strong> kế hoạch</span>
        </span>
        <button v-if="activeChips.length > 0" class="text-xs text-red-500 hover:text-red-700 font-medium" @click="resetFilters">Xóa tất cả</button>
      </div>

      <div v-if="store.loading" class="p-6 text-sm text-slate-500">Đang tải...</div>
      <div v-else-if="store.plans.length" class="overflow-x-auto">
        <table class="data-table">
          <thead>
            <tr>
              <th>Mã kế hoạch</th>
              <th>Kỳ kế hoạch</th>
              <th class="num">Năm</th>
              <th class="num">Tổng ngân sách</th>
              <th class="num">Đã phân bổ</th>
              <th class="num">Tỷ lệ sử dụng</th>
              <th>Trạng thái</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="p in store.plans" :key="p.name">
              <td>{{ p.name }}</td>
              <td>
                <button class="link-cell" :title="`Lọc: ${planPeriodLabel(p.plan_period)}`"
                        @click="quickFilter('plan_period', p.plan_period)">
                  {{ planPeriodLabel(p.plan_period) }}
                </button>
              </td>
              <td class="num">
                <button class="link-cell" :title="`Lọc năm: ${p.plan_year}`"
                        @click="quickFilter('plan_year', p.plan_year)">
                  {{ p.plan_year }}
                </button>
              </td>
              <td class="num">{{ formatVnd(p.budget_envelope) }}</td>
              <td class="num">{{ formatVnd(p.allocated_capex || 0) }}</td>
              <td class="num">
                <span :class="utilClass(p.utilization_pct)">{{ (p.utilization_pct || 0).toFixed(1) }}%</span>
              </td>
              <td>
                <button :class="['badge', 'state-' + stateSlug(p.workflow_state), 'badge-btn']"
                        :title="`Lọc trạng thái: ${stateLabel(p.workflow_state)}`"
                        @click="quickFilter('workflow_state', p.workflow_state)">
                  {{ stateLabel(p.workflow_state) }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else-if="!store.plans.length" class="flex flex-col items-center justify-center py-16 text-slate-400">
        <p class="text-sm">Không có kế hoạch nào phù hợp</p>
        <button v-if="activeChips.length > 0" class="mt-3 text-xs text-blue-500 hover:text-blue-700 underline" @click="resetFilters">
          Xóa bộ lọc để xem tất cả
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.alert-close { background: none; border: none; cursor: pointer; font-size: 1.25rem; float: right; }
.data-table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
.data-table th, .data-table td { padding: 0.75rem 1rem; text-align: left; border-bottom: 1px solid #f1f5f9; }
.data-table th { background: #f9fafb; font-weight: 600; font-size: 0.85rem; color: #475569; }
.data-table .num { text-align: right; }
.link-cell { background: none; border: none; padding: 0; color: #334155; cursor: pointer; }
.link-cell:hover { color: #2563eb; text-decoration: underline; text-decoration-style: dotted; text-underline-offset: 2px; }
.over { color: #b91c1c; font-weight: 600; }
.warn { color: #c2410c; font-weight: 600; }
.badge { display: inline-block; padding: 0.15rem 0.6rem; border-radius: 999px; font-size: 0.75rem; font-weight: 600; }
.badge-btn { border: none; cursor: pointer; }
.badge-btn:hover { box-shadow: 0 0 0 2px rgba(0,0,0,0.06); }
.badge.state-draft { background: #e5e7eb; color: #374151; }
.badge.state-approved, .badge.state-active { background: #d1fae5; color: #065f46; }
.badge.state-closed { background: #dbeafe; color: #1e40af; }
</style>
