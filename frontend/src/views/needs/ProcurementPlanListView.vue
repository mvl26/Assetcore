<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
import { ref, reactive, computed, onMounted } from 'vue'
import { useImm01Store } from '@/stores/imm01'
import type { ProcurementPlanState, NeedsRequestListItem } from '@/types/imm01'
import { stateLabel, formatVnd } from '@/utils/wave2Labels'
import { createProcurementPlan, listNeedsRequests } from '@/api/imm01'
import { useRouter } from 'vue-router'
import ListFilterBar, { type FilterChip } from '@/components/common/ListFilterBar.vue'
import FilterToggleButton from '@/components/common/FilterToggleButton.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import CurrencyInput from '@/components/common/CurrencyInput.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import KpiCard from '@/components/common/KpiCard.vue'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
import ListPageShell from '@/components/ui/ListPageShell.vue'
import { useCapabilities } from '@/composables/useCapabilities'
import { computeProcurementPlanKpis } from './procurementPlanKpis'

const store = useImm01Store()
const router = useRouter()
const { can } = useCapabilities()

// Gate nút tạo — khớp BE rbac.require('needs.create'). FE chỉ ẩn cho UX.
const canCreatePlan = computed(() => can('needs.create'))

// KPI strip — source-backed từ store.plans, không gọi endpoint KPI riêng.
const planKpis = computed(() => computeProcurementPlanKpis(store.plans))

const showCreateModal = ref(false)
const creating = ref(false)
const createForm = reactive({ plan_year: new Date().getFullYear(), plan_period: 'Q1' as string, budget_envelope: 0 })
const PLAN_PERIODS_LABELS = { Q1: 'Quý 1', Q2: 'Quý 2', Q3: 'Quý 3', Q4: 'Quý 4', Annual: 'Cả năm' }

const createError = ref<string | null>(null)

// Proposal-first: kế hoạch tạo bằng cách CHỌN ≥1 đề xuất (Needs Request đã
// duyệt) — KHÔNG tạo kế hoạch rỗng (khớp BE create_procurement_plan).
const candidateNeeds = ref<NeedsRequestListItem[]>([])
const selectedNrIds = ref(new Set<string>())
const loadingNeeds = ref(false)

async function openCreateModal() {
  showCreateModal.value = true
  createError.value = null
  selectedNrIds.value = new Set()
  loadingNeeds.value = true
  try {
    const res = await listNeedsRequests({ workflow_state: 'Approved' }, 1, 100)
    candidateNeeds.value = res.items
  } catch (e: unknown) {
    createError.value = e instanceof Error ? e.message : String(e)
  } finally {
    loadingNeeds.value = false
  }
}

function toggleNrSelect(id: string) {
  if (selectedNrIds.value.has(id)) selectedNrIds.value.delete(id)
  else selectedNrIds.value.add(id)
}

async function submitCreate() {
  if (selectedNrIds.value.size === 0) {
    createError.value = 'Cần chọn ít nhất một đề xuất (Phiếu đề xuất đã duyệt) để tạo kế hoạch.'
    return
  }
  creating.value = true
  createError.value = null
  try {
    const res = await createProcurementPlan(
      createForm.plan_year, createForm.plan_period, createForm.budget_envelope,
      Array.from(selectedNrIds.value),
    )
    showCreateModal.value = false
    await store.fetchPlans()
    router.push(`/procurement-plans/${res.name}`)
  } catch (e: unknown) {
    createError.value = e instanceof Error ? e.message : String(e)
  } finally {
    creating.value = false
  }
}

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
// AC-UX-044 — `stores/imm01.ts::fetchPlans` KHÔNG set `loading` và KHÔNG xoá `error`
// đầu lượt (nhánh `v-if="store.loading"` cũ là mã chết). Vòng 3 cấm sửa `stores/` ⇒
// view tự giữ cờ nạp và tự xoá lỗi trước mỗi lượt (INV-UX3-3/4).
const listLoading = ref(false)
async function loadPlans() {
  listLoading.value = true
  store.clearError()
  try {
    await store.fetchPlans(buildPayload())
  } finally {
    listLoading.value = false
  }
}

function applyFilters() { loadPlans() }
function resetFilters() {
  filters.workflow_state = ''
  filters.plan_period = ''
  filters.plan_year = ''
  filters.search = ''
  loadPlans()
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

onMounted(() => loadPlans())
</script>

<template>
  <ListPageShell
    :loading="listLoading"
    :error-message="store.error"
    :is-empty="!store.plans.length"
    empty-title="Chưa có kế hoạch mua sắm nào"
    empty-hint="Hãy tạo kế hoạch từ đề xuất đã duyệt, hoặc xoá bộ lọc để xem tất cả."
    @retry="loadPlans"
  >
    <template #header>
      <PageHeader title="Kế hoạch mua sắm" :subtitle="`Tổng ${store.plans.length} kế hoạch — gom đề xuất đã duyệt theo quý/năm.`">
        <template #actions>
          <FilterToggleButton v-model="showFilters" :count="activeChips.length" />
          <button v-if="canCreatePlan" class="btn-primary text-sm" @click="openCreateModal()">+ Tạo kế hoạch</button>
        </template>
      </PageHeader>
    </template>

    <template #summary>
      <!-- KPI strip — tĩnh, tính client-side từ store.plans (Core Doc 06_FE).
           Ẩn ở trạng thái lỗi: số 0 tính từ tập rỗng là tín hiệu giả (§2.2). -->
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
        <KpiCard label="Tổng kế hoạch" :value="planKpis.total" color="primary" />
        <KpiCard
          label="Đang hoạt động"
          :value="planKpis.active"
          :color="planKpis.active > 0 ? 'success' : 'neutral'"
        />
        <KpiCard label="Tổng ngân sách" :value="formatVnd(planKpis.totalBudget)" color="info" />
        <KpiCard
          label="Tỷ lệ sử dụng thiết bị"
          :value="`${planKpis.avgUtilization.toFixed(1)}%`"
          :color="planKpis.avgUtilization >= 80 ? 'warning' : 'primary'"
        />
      </div>
    </template>

    <template #filters>
      <ListFilterBar
        v-model:search="filters.search"
        :show="showFilters"
        :chips="activeChips"
        search-placeholder="Tìm theo mã kế hoạch hoặc kỳ kế hoạch..."
        @apply="applyFilters"
        @reset="resetFilters"
        @clear-chip="clearChip"
      >
        <template #fields>
          <label class="sr-only" for="plan-filter-state">Trạng thái kế hoạch</label>
          <select id="plan-filter-state" v-model="filters.workflow_state" class="form-select text-sm" @change="applyFilters">
            <option value="">Tất cả trạng thái</option>
            <option v-for="s in PLAN_STATES" :key="s" :value="s">{{ stateLabel(s) }}</option>
          </select>
          <label class="sr-only" for="plan-filter-period">Kỳ kế hoạch</label>
          <select id="plan-filter-period" v-model="filters.plan_period" class="form-select text-sm" @change="applyFilters">
            <option value="">Tất cả kỳ</option>
            <option v-for="p in PLAN_PERIODS" :key="p" :value="p">{{ planPeriodLabel(p) }}</option>
          </select>
          <label class="sr-only" for="plan-filter-year">Năm kế hoạch</label>
          <select id="plan-filter-year" v-model.number="filters.plan_year" class="form-select text-sm" @change="applyFilters">
            <option value="">Tất cả năm</option>
            <option v-for="y in YEARS" :key="y" :value="y">{{ y }}</option>
          </select>
        </template>
      </ListFilterBar>
    </template>

    <template #skeleton>
      <SkeletonLoader variant="table" :rows="6" />
    </template>

    <template #empty-action>
      <div class="flex flex-wrap items-center justify-center gap-2">
        <button v-if="activeChips.length > 0" class="btn-ghost text-sm" @click="resetFilters">
          Xóa bộ lọc để xem tất cả
        </button>
        <button
          v-else-if="canCreatePlan"
          class="btn-primary text-sm"
          @click="openCreateModal()"
        >
          + Tạo kế hoạch đầu tiên
        </button>
      </div>
    </template>

    <template #toolbar>
      <div class="flex items-center justify-between px-4 py-3 border-b border-slate-100 bg-slate-50/60">
        <span class="text-xs text-slate-500">
          <span v-if="activeChips.length > 0">Kết quả lọc: <strong class="text-slate-700">{{ store.plans.length }}</strong> kế hoạch</span>
          <span v-else>Hiển thị <strong class="text-slate-700">{{ store.plans.length }}</strong> kế hoạch</span>
        </span>
        <button v-if="activeChips.length > 0" class="text-xs text-red-500 hover:text-red-700 font-medium" @click="resetFilters">Xóa tất cả</button>
      </div>
    </template>

    <!-- Mobile cards -->
        <div class="mobile-card-list sm:hidden">
          <div
            v-for="p in store.plans"
            :key="p.name"
            class="mobile-card"
            @click="$router.push(`/procurement-plans/${p.name}`)"
          >
            <div class="flex items-center justify-between mb-2">
              <span class="font-mono text-sm font-semibold text-brand-700">{{ p.name }}</span>
              <StatusBadge :state="p.workflow_state" />
            </div>
            <p class="text-sm font-medium text-slate-900 truncate">{{ planPeriodLabel(p.plan_period) }} · {{ p.plan_year }}</p>
            <div class="flex flex-wrap gap-x-2 gap-y-1 mt-1.5 text-xs text-slate-500">
              <span>Ngân sách: {{ formatVnd(p.budget_envelope) }}</span>
              <span>· Sử dụng: <span :class="utilClass(p.utilization_pct)">{{ (p.utilization_pct || 0).toFixed(1) }}%</span></span>
            </div>
          </div>
        </div>

        <!-- Desktop table -->
        <div class="hidden sm:block overflow-x-auto">
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
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(p, idx) in store.plans" :key="p.name" class="animate-fade-in" :class="[`stagger-${Math.min(idx + 1, 8)}`]">
                <td>
                  <router-link :to="`/procurement-plans/${p.name}`" class="link-cell">
                    <span class="font-mono text-xs bg-slate-100 px-1.5 py-0.5 rounded text-slate-700">{{ p.name }}</span>
                  </router-link>
                </td>
                <td>
                  <button
  class="link-cell" :title="`Lọc: ${planPeriodLabel(p.plan_period)}`"
                          @click="quickFilter('plan_period', p.plan_period)">
                    {{ planPeriodLabel(p.plan_period) }}
                  </button>
                </td>
                <td class="num">
                  <button
  class="link-cell" :title="`Lọc năm: ${p.plan_year}`"
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
                  <button
                    type="button"
                    class="pill-btn"
                    :title="`Lọc trạng thái: ${stateLabel(p.workflow_state)}`"
                    @click="quickFilter('workflow_state', p.workflow_state)"
                  >
                    <StatusBadge :state="p.workflow_state" />
                  </button>
                </td>
                <td>
                  <router-link :to="`/procurement-plans/${p.name}`" class="text-xs text-brand-600 hover:underline">Chi tiết →</router-link>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
    <!-- Không có phân trang: `fetchPlans` kéo 1 lượt (page_size=50) — vòng 4 mới chuẩn hoá. -->
  </ListPageShell>

  <!-- Create Plan Modal -->
  <div v-if="showCreateModal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40" @click.self="showCreateModal = false">
    <div class="bg-white rounded-xl shadow-xl p-6 w-full max-w-xl space-y-4">
      <h3 class="text-base font-semibold text-slate-800">Tạo kế hoạch mua sắm mới</h3>
      <p class="text-xs text-slate-500">Chọn các đề xuất (Phiếu đề xuất đã duyệt) để gom vào kế hoạch, rồi tạo.</p>
      <div class="space-y-3">
        <div v-if="createError" class="text-xs text-red-600 bg-red-50 border border-red-200 rounded p-2">{{ createError }}</div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="text-xs font-medium text-slate-600 block mb-1">Năm kế hoạch *</label>
            <input v-model.number="createForm.plan_year" type="number" min="2020" max="2100" class="form-input w-full" />
          </div>
          <div>
            <label class="text-xs font-medium text-slate-600 block mb-1">Kỳ kế hoạch *</label>
            <select v-model="createForm.plan_period" class="form-select w-full">
              <option v-for="(label, key) in PLAN_PERIODS_LABELS" :key="key" :value="key">{{ label }}</option>
            </select>
          </div>
        </div>
        <div>
          <label class="text-xs font-medium text-slate-600 block mb-1">Ngân sách phê duyệt (VNĐ)</label>
          <CurrencyInput v-model="createForm.budget_envelope" aria-label="Tổng ngân sách" class="form-input w-full" placeholder="0" />
        </div>
        <div>
          <label class="text-xs font-medium text-slate-600 block mb-1">
            Đề xuất đưa vào kế hoạch * <span class="text-slate-400">(chọn ≥1)</span>
          </label>
          <div v-if="loadingNeeds" class="text-xs text-slate-500 py-2">Đang tải đề xuất đã duyệt...</div>
          <div v-else-if="!candidateNeeds.length" class="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded p-2">
            Chưa có đề xuất nào ở trạng thái "Đã duyệt" để đưa vào kế hoạch. Hãy duyệt đề xuất trước khi tạo kế hoạch.
          </div>
          <div v-else class="max-h-56 overflow-y-auto border border-slate-200 rounded">
            <table class="data-table text-xs">
              <thead>
                <tr><th></th><th>Mã đề xuất</th><th>Khoa</th><th class="num">Điểm</th><th class="num">Đầu tư mua sắm</th></tr>
              </thead>
              <tbody>
                <tr v-for="n in candidateNeeds" :key="n.name">
                  <td>
                    <input
                      type="checkbox"
                      :checked="selectedNrIds.has(n.name)"
                      :aria-label="`Chọn đề xuất ${n.name}`"
                      @change="toggleNrSelect(n.name)"
                    />
                  </td>
                  <td class="font-mono">{{ n.name }}</td>
                  <td>{{ n.department_name || n.requesting_department }}</td>
                  <td class="num">{{ (n.weighted_score || 0).toFixed(2) }}</td>
                  <td class="num">{{ formatVnd(n.total_capex || 0) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p v-if="candidateNeeds.length" class="text-[11px] text-slate-500 mt-1">Đã chọn {{ selectedNrIds.size }} đề xuất.</p>
        </div>
      </div>
      <div class="flex justify-end gap-2 pt-2">
        <button class="btn-ghost text-sm" @click="showCreateModal = false">Hủy</button>
        <button class="btn-primary text-sm" :disabled="creating || selectedNrIds.size === 0" @click="submitCreate">
          {{ creating ? 'Đang tạo...' : 'Tạo kế hoạch' }}
        </button>
      </div>
    </div>
  </div>
</template>

<!-- list-view.css đã cung cấp .data-table, .link-cell, .alert-error, .pill-btn, thresholds. -->
