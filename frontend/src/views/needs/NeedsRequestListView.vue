<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
import { ref, reactive, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useImm01Store } from '@/stores/imm01'
import { useRefDataStore } from '@/stores/imm00'
import type { NeedsRequestFilters, RequestType, NeedsRequestState, PriorityClass } from '@/types/imm01'
import {
  stateLabel, requestTypeLabel, priorityBadge, formatVnd,
} from '@/utils/wave2Labels'
import PageHeader from '@/components/common/PageHeader.vue'
import FilterToggleButton from '@/components/common/FilterToggleButton.vue'
import ListFilterBar, { type FilterChip } from '@/components/common/ListFilterBar.vue'
import BasePagination from '@/components/common/BasePagination.vue'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
import KpiCard from '@/components/common/KpiCard.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'

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
    <PageHeader
      title="Đề xuất nhu cầu thiết bị"
      :subtitle="`Tổng ${store.total} đề xuất — tiếp nhận, chấm điểm ưu tiên và lập dự toán.`"
    >
      <template #actions>
        <FilterToggleButton v-model="showFilters" :count="activeChips.length" />
        <button class="btn-primary shrink-0" @click="goCreate">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          Tạo đề xuất
        </button>
      </template>
    </PageHeader>

    <ListFilterBar
      v-model:search="filters.search"
      :show="showFilters"
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

    <!-- KPI strip -->
    <div v-if="store.kpis" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
      <KpiCard
        :label="'Phiếu tồn quá 30 ngày'"
        :value="store.kpis.backlog_over_30d"
        :color="store.kpis.backlog_over_30d > 0 ? 'warning' : 'neutral'"
      />
      <KpiCard
        :label="'Tỷ lệ qua kiểm tra ban đầu'"
        :value="`${store.kpis.g01_pass_rate.toFixed(1)}%`"
        color="success"
      />
      <KpiCard
        :label="'Tỷ lệ sử dụng ngân sách'"
        :value="`${store.kpis.envelope_utilization.toFixed(1)}%`"
        color="primary"
      />
      <KpiCard
        :label="'Đã được duyệt'"
        :value="totalApproved"
        color="success"
      />
    </div>

    <div v-if="store.error" class="alert-error mb-4">
      <span><strong>Lỗi:</strong> {{ store.error }}</span>
      <div class="flex items-center gap-2">
        <button class="text-sm underline text-red-700" @click="applyFilters">Thử lại</button>
        <button class="alert-close" @click="store.clearError()">×</button>
      </div>
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
        <SkeletonLoader variant="table" :rows="6" />
      </div>
      <div v-else-if="store.needsRequests.length" class="overflow-x-auto animate-fade-in">
        <table class="w-full">
          <thead>
            <tr>
              <th class="table-header">Mã phiếu</th>
              <th class="table-header">Loại đề xuất</th>
              <th class="table-header">Khoa đề xuất</th>
              <th class="table-header">Model thiết bị</th>
              <th class="table-header text-right">Số lượng</th>
              <th class="table-header">Mức ưu tiên</th>
              <th class="table-header text-right">Tổng chi phí 5 năm</th>
              <th class="table-header">Trạng thái</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(nr, idx) in store.needsRequests"
              :key="nr.name"
              class="table-row animate-fade-in"
              :class="[`stagger-${Math.min(idx + 1, 8)}`]"
              @click="goDetail(nr.name)"
            >
              <td class="table-cell">
                <span class="font-mono text-xs bg-slate-100 px-1.5 py-0.5 rounded text-slate-700">{{ nr.name }}</span>
              </td>
              <td class="table-cell">
                <button
class="link-cell" :title="`Lọc: ${requestTypeLabel(nr.request_type)}`"
                        @click.stop="quickFilter('request_type', nr.request_type)">
                  {{ requestTypeLabel(nr.request_type) }}
                </button>
              </td>
              <td class="table-cell">
                <button
v-if="nr.requesting_department" class="link-cell"
                        :title="`Lọc: ${nr.requesting_department}`"
                        @click.stop="quickFilter('requesting_department', nr.requesting_department)">
                  {{ nr.department_name || nr.requesting_department }}
                </button>
                <span v-else class="text-slate-400">—</span>
              </td>
              <td class="table-cell">{{ nr.device_model_name || nr.device_model_ref }}</td>
              <td class="table-cell text-right">{{ nr.quantity }}</td>
              <td class="table-cell">
                <button
                  v-if="nr.priority_class"
                  type="button"
                  :class="['priority-pill', `priority-${nr.priority_class}`]"
                  :title="`Lọc: ${nr.priority_class}`"
                  @click.stop="quickFilter('priority_class', nr.priority_class)"
                >
{{ priorityBadge(nr.priority_class) }}
</button>
                <span v-else class="text-slate-400">—</span>
              </td>
              <td class="table-cell text-right">{{ formatVnd(nr.tco_5y) }}</td>
              <td class="table-cell">
                <button
                  type="button"
                  class="bg-transparent border-0 p-0 cursor-pointer"
                  :title="`Lọc trạng thái: ${stateLabel(nr.workflow_state)}`"
                  @click.stop="quickFilter('workflow_state', nr.workflow_state)"
                >
                  <StatusBadge :state="nr.workflow_state" />
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else class="flex flex-col items-center justify-center py-16 text-slate-400">
        <p class="text-sm">Không có đề xuất nào phù hợp</p>
        <button
v-if="activeChips.length > 0" class="mt-3 text-xs text-brand-600 hover:text-brand-700 underline"
                @click="resetFilters">
          Xóa bộ lọc để xem tất cả
        </button>
      </div>
    </div>

    <BasePagination :pagination="{ page: store.page, total_pages: totalPages, total: store.total, page_size: store.pageSize }" @page-change="goPage" />
  </div>
</template>

<style scoped>
.alert-close { background: none; border: none; cursor: pointer; font-size: 1.25rem; }
.link-cell { background: none; border: none; padding: 0; color: #334155; cursor: pointer; text-align: left; font: inherit; }
.link-cell:hover { color: #2563eb; text-decoration: underline; text-decoration-style: dotted; text-underline-offset: 2px; }

/* Priority pills (4 levels) — DS semantic palette */
.priority-pill {
  display: inline-flex; align-items: center;
  padding: 2px 8px; border-radius: 9999px;
  font-size: 11px; font-weight: 600;
  border: 0; cursor: pointer;
  transition: box-shadow 120ms;
}
.priority-pill:hover { box-shadow: 0 0 0 2px rgba(0,0,0,0.06); }
.priority-P1 { background: #fef2f2; color: #b91c1c; }
.priority-P2 { background: #fffbeb; color: #a16207; }
.priority-P3 { background: #eff6ff; color: #1d4ed8; }
.priority-P4 { background: #f1f5f9; color: #475569; }
</style>

<style>
.alert-error {
  display: flex; align-items: center; justify-content: space-between; gap: 0.5rem;
  background: #fef2f2; border: 1px solid #fecaca; padding: 0.75rem 1rem;
  border-radius: 8px; color: #b91c1c; font-size: 0.875rem;
}
</style>
