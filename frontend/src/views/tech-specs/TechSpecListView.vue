<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useImm02Store } from '@/stores/imm02'
import type { SpecState } from '@/types/imm02'
import { stateLabel, stateSlug } from '@/utils/wave2Labels'
import PageHeader from '@/components/common/PageHeader.vue'
import FilterToggleButton from '@/components/common/FilterToggleButton.vue'
import ListFilterBar, { type FilterChip } from '@/components/common/ListFilterBar.vue'

const router = useRouter()
const store  = useImm02Store()

const SPEC_STATES: SpecState[] = ['Draft', 'Reviewing', 'Benchmarked', 'Risk Assessed', 'Pending Approval', 'Locked', 'Withdrawn']
const LOCK_IN_BUCKETS = [
  { value: 'low',    label: 'Thấp (≤ 2,5)' },
  { value: 'medium', label: 'Trung bình (2,5–3,5)' },
  { value: 'high',   label: 'Cao (> 3,5)' },
] as const
type LockInBucket = typeof LOCK_IN_BUCKETS[number]['value']

const showFilters = ref(false)
const filters = reactive<{
  workflow_state: SpecState | ''
  lock_in_bucket: LockInBucket | ''
  device_model_ref: string
  search: string
}>({
  workflow_state: '',
  lock_in_bucket: '',
  device_model_ref: '',
  search: '',
})

const totalLocked = computed(() => store.kpis?.by_state?.['Locked'] ?? 0)

const activeChips = computed<FilterChip[]>(() => {
  const c: FilterChip[] = []
  if (filters.workflow_state)    c.push({ key: 'workflow_state', label: stateLabel(filters.workflow_state) })
  if (filters.lock_in_bucket) {
    const b = LOCK_IN_BUCKETS.find(x => x.value === filters.lock_in_bucket)
    c.push({ key: 'lock_in_bucket', label: `Phụ thuộc: ${b?.label ?? filters.lock_in_bucket}` })
  }
  if (filters.device_model_ref)  c.push({ key: 'device_model_ref', label: filters.device_model_ref })
  if (filters.search.trim())     c.push({ key: 'search', label: `"${filters.search.trim()}"` })
  return c
})

function buildPayload(): Record<string, unknown> {
  const f: Record<string, unknown> = {}
  if (filters.workflow_state)   f.workflow_state = filters.workflow_state
  if (filters.device_model_ref) f.device_model_ref = filters.device_model_ref
  if (filters.search.trim())    f.search = filters.search.trim()
  // lock_in_bucket áp dụng filter phía client trên kết quả
  return f
}
function applyFilters() { store.fetchList(buildPayload()) }
function resetFilters() {
  filters.workflow_state = ''
  filters.lock_in_bucket = ''
  filters.device_model_ref = ''
  filters.search = ''
  store.fetchList()
}
function clearChip(key: string) {
  ;(filters as Record<string, string>)[key] = ''
  applyFilters()
}
function quickFilter(key: keyof typeof filters, value: string) {
  ;(filters as Record<string, string>)[key] = value
  showFilters.value = false
  applyFilters()
}

const filteredSpecs = computed(() => {
  const items = store.specs
  if (!filters.lock_in_bucket) return items
  return items.filter(s => {
    const v = s.lock_in_score ?? 0
    if (filters.lock_in_bucket === 'low')    return v <= 2.5
    if (filters.lock_in_bucket === 'medium') return v > 2.5 && v <= 3.5
    if (filters.lock_in_bucket === 'high')   return v > 3.5
    return true
  })
})

function lockInClass(score?: number): string {
  if (score == null) return ''
  if (score > 3.5) return 'over'
  if (score > 2.5) return 'warn'
  return 'ok'
}

function goDetail(n: string) { router.push({ name: 'TechSpecDetail', params: { id: n } }) }
function goCreate() { router.push({ name: 'TechSpecCreate' }) }

onMounted(() => { store.fetchList(); store.fetchKpis() })
</script>

<template>
  <div class="page-container animate-fade-in">
    <PageHeader
      title="Hồ sơ kỹ thuật"
      :subtitle="`Tổng ${store.specs.length} hồ sơ — quản lý yêu cầu kỹ thuật, so sánh thị trường, đánh giá phụ thuộc nhà cung cấp.`"
    >
      <template #actions>
        <FilterToggleButton v-model="showFilters" :count="activeChips.length" />
        <button class="btn-primary shrink-0" @click="goCreate">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          Sinh từ kế hoạch
        </button>
      </template>
    </PageHeader>

    <ListFilterBar
      :show="showFilters"
      v-model:search="filters.search"
      :chips="activeChips"
      search-placeholder="Tìm theo mã hồ sơ, model..."
      @apply="applyFilters"
      @reset="resetFilters"
      @clear-chip="clearChip"
    >
      <template #fields>
        <select v-model="filters.workflow_state" class="form-select text-sm" @change="applyFilters">
          <option value="">Tất cả trạng thái</option>
          <option v-for="s in SPEC_STATES" :key="s" :value="s">{{ stateLabel(s) }}</option>
        </select>
        <select v-model="filters.lock_in_bucket" class="form-select text-sm" @change="applyFilters">
          <option value="">Tất cả mức phụ thuộc</option>
          <option v-for="b in LOCK_IN_BUCKETS" :key="b.value" :value="b.value">{{ b.label }}</option>
        </select>
      </template>
    </ListFilterBar>

    <div v-if="store.kpis" class="kpi-grid mb-4">
      <div class="kpi-card">
        <span class="kpi-value">{{ totalLocked }}</span>
        <span class="kpi-label">Đã chốt hồ sơ</span>
      </div>
      <div class="kpi-card warn">
        <span class="kpi-value">{{ store.kpis.backlog_over_30d }}</span>
        <span class="kpi-label">Hồ sơ tồn quá 30 ngày</span>
      </div>
      <div class="kpi-card">
        <span class="kpi-value">{{ store.kpis.avg_lock_in_score.toFixed(2) }}</span>
        <span class="kpi-label">Điểm phụ thuộc TB (mục tiêu ≤ 2,5)</span>
      </div>
    </div>

    <div v-if="store.error" class="alert-error mb-4">
      <strong>Lỗi:</strong> {{ store.error }}
      <button class="alert-close" @click="store.clearError()">×</button>
    </div>

    <div class="card overflow-hidden">
      <div class="flex items-center justify-between px-4 py-3 border-b border-slate-100 bg-slate-50/60">
        <span class="text-xs text-slate-500">
          <span v-if="activeChips.length > 0">Kết quả lọc: <strong class="text-slate-700">{{ filteredSpecs.length }}</strong> hồ sơ</span>
          <span v-else>Hiển thị <strong class="text-slate-700">{{ filteredSpecs.length }}</strong> hồ sơ</span>
        </span>
        <button v-if="activeChips.length > 0" class="text-xs text-red-500 hover:text-red-700 font-medium" @click="resetFilters">Xóa tất cả</button>
      </div>

      <div v-if="store.loading" class="p-6 text-sm text-slate-500">Đang tải...</div>
      <div v-else-if="filteredSpecs.length" class="overflow-x-auto">
        <table class="data-table">
          <thead>
            <tr>
              <th>Mã hồ sơ</th>
              <th>Phiên bản</th>
              <th>Mẫu thiết bị</th>
              <th class="num">Yêu cầu bắt buộc</th>
              <th class="num">Số ứng viên</th>
              <th class="num">Điểm phụ thuộc</th>
              <th>Trạng thái</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="s in filteredSpecs" :key="s.name" class="clickable" @click="goDetail(s.name)">
              <td>{{ s.name }}</td>
              <td>{{ s.version }}</td>
              <td>
                <button v-if="s.device_model_ref" class="link-cell" :title="`Lọc: ${s.device_model_ref}`"
                        @click.stop="quickFilter('device_model_ref', s.device_model_ref)">
                  {{ s.device_model_ref }}
                </button>
                <span v-else class="text-slate-400">—</span>
              </td>
              <td class="num">{{ s.total_mandatory ?? 0 }}</td>
              <td class="num">{{ s.candidate_count ?? 0 }}</td>
              <td class="num">
                <span :class="lockInClass(s.lock_in_score)">
                  {{ s.lock_in_score != null ? s.lock_in_score.toFixed(2) : '—' }}
                </span>
              </td>
              <td>
                <button :class="['badge', 'state-' + stateSlug(s.workflow_state), 'badge-btn']"
                        :title="`Lọc trạng thái: ${stateLabel(s.workflow_state)}`"
                        @click.stop="quickFilter('workflow_state', s.workflow_state)">
                  {{ stateLabel(s.workflow_state) }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else class="flex flex-col items-center justify-center py-16 text-slate-400">
        <p class="text-sm">Không có hồ sơ kỹ thuật phù hợp</p>
        <button v-if="activeChips.length > 0" class="mt-3 text-xs text-blue-500 hover:text-blue-700 underline" @click="resetFilters">
          Xóa bộ lọc để xem tất cả
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; }
.kpi-card { background: white; border: 1px solid #e5e7eb; border-radius: 8px; padding: 1rem; display: flex; flex-direction: column; }
.kpi-value { font-size: 1.75rem; font-weight: 700; }
.kpi-label { color: #6b7280; font-size: 0.85rem; }
.kpi-card.warn { border-left: 4px solid #f59e0b; }
.alert-close { background: none; border: none; cursor: pointer; font-size: 1.25rem; float: right; }
.data-table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
.data-table th, .data-table td { padding: 0.75rem 1rem; text-align: left; border-bottom: 1px solid #f1f5f9; }
.data-table th { background: #f9fafb; font-weight: 600; font-size: 0.85rem; color: #475569; }
.data-table .num { text-align: right; }
.data-table tr.clickable { cursor: pointer; }
.data-table tr.clickable:hover { background: #f9fafb; }
.link-cell { background: none; border: none; padding: 0; color: #334155; cursor: pointer; }
.link-cell:hover { color: #2563eb; text-decoration: underline; text-decoration-style: dotted; text-underline-offset: 2px; }
.badge { display: inline-block; padding: 0.15rem 0.6rem; border-radius: 999px; font-size: 0.75rem; font-weight: 600; }
.badge-btn { border: none; cursor: pointer; }
.badge-btn:hover { box-shadow: 0 0 0 2px rgba(0,0,0,0.06); }
.badge.state-draft { background: #e5e7eb; color: #374151; }
.badge.state-reviewing { background: #fef3c7; color: #92400e; }
.badge.state-benchmarked, .badge.state-locked { background: #d1fae5; color: #065f46; }
.badge.state-risk-assessed, .badge.state-pending-approval { background: #fce7f3; color: #9d174d; }
.badge.state-withdrawn { background: #fee2e2; color: #b91c1c; }
.over { color: #b91c1c; font-weight: 700; }
.warn { color: #c2410c; font-weight: 600; }
.ok   { color: #065f46; font-weight: 500; }
</style>
