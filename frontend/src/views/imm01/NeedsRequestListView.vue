<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
import { ref, reactive, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useImm01Store } from '@/stores/imm01'
import { useRefDataStore } from '@/stores/imm00'
import type { NeedsRequestFilters, RequestType, NeedsRequestState, PriorityClass } from '@/types/imm01'
import {
  stateLabel, stateSlug, requestTypeLabel, priorityBadge, formatVnd,
} from '@/utils/wave2Labels'
import ListFilterBar, { type FilterChip } from '@/components/common/ListFilterBar.vue'
import FilterToggleButton from '@/components/common/FilterToggleButton.vue'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'

const router = useRouter()
const store  = useImm01Store()
const refData = useRefDataStore()

const WORKFLOW_STATES: NeedsRequestState[] = [
  'Draft', 'Submitted', 'Reviewing', 'Prioritized',
  'Budgeted', 'Pending Approval', 'Approved', 'Rejected',
]
const REQUEST_TYPES: RequestType[] = ['New', 'Replacement', 'Upgrade', 'Add-on']
const PRIORITY_CLASSES: PriorityClass[] = ['P1', 'P2', 'P3', 'P4']

const showFilters = ref(false)
const filters = reactive<{
  workflow_state: NeedsRequestState | ''
  request_type: RequestType | ''
  priority_class: PriorityClass | ''
  requesting_department: string
  search: string
}>({
  workflow_state: '',
  request_type: '',
  priority_class: '',
  requesting_department: '',
  search: '',
})

const totalPages    = computed(() => Math.max(1, Math.ceil(store.total / store.pageSize)))
const totalApproved = computed(() => store.kpis?.by_state?.['Approved'] ?? 0)

const activeChips = computed<FilterChip[]>(() => {
  const chips: FilterChip[] = []
  if (filters.workflow_state)
    chips.push({ key: 'workflow_state', label: stateLabel(filters.workflow_state) })
  if (filters.request_type)
    chips.push({ key: 'request_type', label: requestTypeLabel(filters.request_type) })
  if (filters.priority_class)
    chips.push({ key: 'priority_class', label: `${filters.priority_class} • ${priorityBadge(filters.priority_class)}` })
  if (filters.requesting_department) {
    const d = refData.departments.find(x => x.name === filters.requesting_department)
    chips.push({ key: 'requesting_department', label: d?.department_name ?? filters.requesting_department })
  }
  if (filters.search.trim())
    chips.push({ key: 'search', label: `"${filters.search.trim()}"` })
  return chips
})

function buildPayload(): NeedsRequestFilters & { search?: string } {
  const f: NeedsRequestFilters & { search?: string } = {}
  if (filters.workflow_state) f.workflow_state = filters.workflow_state
  if (filters.request_type) f.request_type = filters.request_type
  if (filters.priority_class) f.priority_class = filters.priority_class
  if (filters.requesting_department) f.requesting_department = filters.requesting_department
  if (filters.search.trim()) f.search = filters.search.trim()
  return f
}

function applyFilters() { store.fetchNeedsRequests(buildPayload(), 1, store.pageSize) }
function clearChip(key: string) {
  ;(filters as Record<string, string>)[key] = ''
  applyFilters()
}
function resetFilters() {
  filters.workflow_state = ''
  filters.request_type = ''
  filters.priority_class = ''
  filters.requesting_department = ''
  filters.search = ''
  store.fetchNeedsRequests({}, 1, store.pageSize)
}
function quickFilter(key: keyof typeof filters, value: string) {
  if (!value) return
  if ((filters as Record<string, string>)[key] === value) return
  ;(filters as Record<string, string>)[key] = value
  showFilters.value = false
  applyFilters()
}

function goCreate()          { router.push({ name: 'NeedsRequestCreate' }) }
function goDetail(n: string) { router.push({ name: 'NeedsRequestDetail', params: { id: n } }) }
function goPage(p: number)   { store.fetchNeedsRequests(buildPayload(), p, store.pageSize) }

onMounted(() => {
  store.fetchNeedsRequests()
  store.fetchKpis()
  refData.fetchAll()
})
</script>

<template>
  <div class="page-container animate-fade-in">
    <!-- Header -->
    <div class="flex items-start justify-between mb-4">
      <div>
        <h1 class="text-2xl font-bold text-slate-900">Đề xuất nhu cầu thiết bị</h1>
        <p class="text-sm text-slate-500 mt-1">
          Tổng <strong class="text-slate-700">{{ store.total }}</strong> đề xuất —
          tiếp nhận, chấm điểm ưu tiên và lập dự toán.
        </p>
      </div>
      <div class="flex items-center gap-2 shrink-0">
        <FilterToggleButton v-model="showFilters" :count="activeChips.length" />
        <button class="btn-primary shrink-0" @click="goCreate">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          Tạo đề xuất
        </button>
      </div>
    </div>

    <ListFilterBar
      :show="showFilters"
      v-model:search="filters.search"
      :chips="activeChips"
      search-placeholder="Tìm theo mã, model, khoa..."
      @apply="applyFilters"
      @reset="resetFilters"
      @clear-chip="clearChip"
    >
      <template #fields>
        <select v-model="filters.workflow_state" class="form-select text-sm" @change="applyFilters">
          <option value="">Tất cả trạng thái</option>
          <option v-for="s in WORKFLOW_STATES" :key="s" :value="s">{{ stateLabel(s) }}</option>
        </select>
        <select v-model="filters.request_type" class="form-select text-sm" @change="applyFilters">
          <option value="">Tất cả loại đề xuất</option>
          <option v-for="t in REQUEST_TYPES" :key="t" :value="t">{{ requestTypeLabel(t) }}</option>
        </select>
        <select v-model="filters.priority_class" class="form-select text-sm" @change="applyFilters">
          <option value="">Tất cả mức ưu tiên</option>
          <option v-for="p in PRIORITY_CLASSES" :key="p" :value="p">{{ p }} — {{ priorityBadge(p) }}</option>
        </select>
        <select v-model="filters.requesting_department" class="form-select text-sm" @change="applyFilters">
          <option value="">Tất cả khoa/phòng</option>
          <option v-for="d in refData.departments" :key="d.name" :value="d.name">{{ d.department_name }}</option>
        </select>
      </template>
    </ListFilterBar>

    <!-- KPI grid -->
    <div v-if="store.kpis" class="kpi-grid mb-4">
      <div class="kpi-card">
        <span class="kpi-value">{{ store.kpis.backlog_over_30d }}</span>
        <span class="kpi-label">Phiếu tồn quá 30 ngày</span>
      </div>
      <div class="kpi-card success">
        <span class="kpi-value">{{ store.kpis.g01_pass_rate.toFixed(1) }}%</span>
        <span class="kpi-label">Tỷ lệ qua kiểm tra ban đầu</span>
      </div>
      <div class="kpi-card info">
        <span class="kpi-value">{{ store.kpis.envelope_utilization.toFixed(1) }}%</span>
        <span class="kpi-label">Tỷ lệ sử dụng ngân sách</span>
      </div>
      <div class="kpi-card">
        <span class="kpi-value">{{ totalApproved }}</span>
        <span class="kpi-label">Đã được duyệt</span>
      </div>
    </div>

    <div v-if="store.error" class="alert-error mb-4">
      <strong>Lỗi:</strong> {{ store.error }}
      <button class="alert-close" @click="store.clearError()">×</button>
    </div>

    <!-- Table -->
    <div class="card overflow-hidden">
      <div class="flex items-center justify-between px-4 py-3 border-b border-slate-100 bg-slate-50/60">
        <span class="text-xs text-slate-500">
          <span v-if="activeChips.length > 0">
            Kết quả lọc: <strong class="text-slate-700">{{ store.total }}</strong> phiếu
          </span>
          <span v-else>
            Hiển thị <strong class="text-slate-700">{{ store.needsRequests.length }}</strong> / {{ store.total }} phiếu
          </span>
        </span>
        <div v-if="activeChips.length > 0" class="flex items-center gap-2">
          <span class="text-xs text-slate-400">{{ activeChips.length }} bộ lọc đang áp dụng</span>
          <button class="text-xs text-red-500 hover:text-red-700 font-medium" @click="resetFilters">Xóa tất cả</button>
        </div>
      </div>

      <div v-if="store.loading" class="p-6">
        <SkeletonLoader v-for="i in 5" :key="i" class="h-10 mb-3" />
      </div>
      <div v-else-if="store.needsRequests.length" class="overflow-x-auto">
        <table class="data-table">
          <thead>
            <tr>
              <th>Mã phiếu</th>
              <th>Loại đề xuất</th>
              <th>Khoa đề xuất</th>
              <th>Model thiết bị</th>
              <th class="num">Số lượng</th>
              <th>Mức ưu tiên</th>
              <th class="num">Tổng chi phí 5 năm</th>
              <th>Trạng thái</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="nr in store.needsRequests" :key="nr.name" class="clickable" @click="goDetail(nr.name)">
              <td>{{ nr.name }}</td>
              <td>
                <button class="link-cell" :title="`Lọc: ${requestTypeLabel(nr.request_type)}`"
                        @click.stop="quickFilter('request_type', nr.request_type)">
                  {{ requestTypeLabel(nr.request_type) }}
                </button>
              </td>
              <td>
                <button v-if="nr.requesting_department" class="link-cell"
                        :title="`Lọc: ${nr.requesting_department}`"
                        @click.stop="quickFilter('requesting_department', nr.requesting_department)">
                  {{ nr.requesting_department }}
                </button>
                <span v-else class="text-slate-400">—</span>
              </td>
              <td>{{ nr.device_model_ref }}</td>
              <td class="num">{{ nr.quantity }}</td>
              <td>
                <button v-if="nr.priority_class"
                        :class="['badge', 'priority-' + nr.priority_class, 'badge-btn']"
                        :title="`Lọc: ${nr.priority_class}`"
                        @click.stop="quickFilter('priority_class', nr.priority_class)">
                  {{ priorityBadge(nr.priority_class) }}
                </button>
                <span v-else class="text-slate-400">—</span>
              </td>
              <td class="num">{{ formatVnd(nr.tco_5y) }}</td>
              <td>
                <button :class="['badge', 'state-' + stateSlug(nr.workflow_state), 'badge-btn']"
                        :title="`Lọc trạng thái: ${stateLabel(nr.workflow_state)}`"
                        @click.stop="quickFilter('workflow_state', nr.workflow_state)">
                  {{ stateLabel(nr.workflow_state) }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else class="flex flex-col items-center justify-center py-16 text-slate-400">
        <p class="text-sm">Không có đề xuất nào phù hợp</p>
        <button v-if="activeChips.length > 0" class="mt-3 text-xs text-blue-500 hover:text-blue-700 underline"
                @click="resetFilters">
          Xóa bộ lọc để xem tất cả
        </button>
      </div>
    </div>

    <!-- Pagination -->
    <div v-if="totalPages > 1" class="flex justify-between items-center mt-4 text-sm text-slate-600">
      <span>Trang {{ store.page }} / {{ totalPages }} — {{ store.total }} phiếu</span>
      <div class="flex gap-2">
        <button class="btn-ghost text-xs" :disabled="store.page <= 1" @click="goPage(store.page - 1)">← Trước</button>
        <button class="btn-ghost text-xs" :disabled="store.page >= totalPages" @click="goPage(store.page + 1)">Sau →</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem; }
.kpi-card { background: white; border: 1px solid #e5e7eb; border-radius: 8px; padding: 1rem; display: flex; flex-direction: column; }
.kpi-card .kpi-value { font-size: 1.75rem; font-weight: 700; color: #111827; }
.kpi-card .kpi-label { color: #6b7280; font-size: 0.85rem; margin-top: 0.25rem; }
.kpi-card.success { border-left: 4px solid #10b981; }
.kpi-card.info    { border-left: 4px solid #3b82f6; }

.alert-close { background: none; border: none; cursor: pointer; font-size: 1.25rem; float: right; }

.data-table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
.data-table th, .data-table td { padding: 0.75rem 1rem; text-align: left; border-bottom: 1px solid #f1f5f9; }
.data-table th { background: #f9fafb; font-weight: 600; font-size: 0.85rem; color: #475569; }
.data-table .num { text-align: right; }
.data-table tr.clickable { cursor: pointer; transition: background 0.1s; }
.data-table tr.clickable:hover { background: #f9fafb; }

.link-cell { background: none; border: none; padding: 0; color: #334155; cursor: pointer; text-align: left; }
.link-cell:hover { color: #2563eb; text-decoration: underline; text-decoration-style: dotted; text-underline-offset: 2px; }

.badge { display: inline-block; padding: 0.15rem 0.6rem; border-radius: 999px; font-size: 0.75rem; font-weight: 600; }
.badge-btn { border: none; cursor: pointer; }
.badge-btn:hover { box-shadow: 0 0 0 2px rgba(0,0,0,0.06); }
.badge.priority-P1 { background: #fee2e2; color: #b91c1c; }
.badge.priority-P2 { background: #fed7aa; color: #c2410c; }
.badge.priority-P3 { background: #fef9c3; color: #a16207; }
.badge.priority-P4 { background: #e5e7eb; color: #4b5563; }
.badge.state-draft { background: #e5e7eb; color: #374151; }
.badge.state-submitted, .badge.state-reviewing { background: #fef3c7; color: #92400e; }
.badge.state-prioritized, .badge.state-budgeted { background: #dbeafe; color: #1e40af; }
.badge.state-pending-approval { background: #fce7f3; color: #9d174d; }
.badge.state-approved { background: #d1fae5; color: #065f46; }
.badge.state-rejected { background: #fee2e2; color: #b91c1c; }
</style>
