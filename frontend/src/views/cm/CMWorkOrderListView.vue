<script setup lang="ts">
import { onMounted, ref, computed, watch } from 'vue'
import { useImm09Store } from '@/stores/imm09'
import { useRouter } from 'vue-router'
import { priorityLabel, priorityClass, repairTypeLabel } from '@/constants/labels'
import { translateStatus, getStatusColor, formatDateTime } from '@/utils/formatters'
import PageHeader from '@/components/common/PageHeader.vue'
import FilterToggleButton from '@/components/common/FilterToggleButton.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'
import BasePagination from '@/components/common/BasePagination.vue'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'

const store = useImm09Store()
const router = useRouter()
const statusFilter = ref('')
const priorityFilter = ref('')
const search = ref('')
const showFilters = ref(false)

const CM_STATUSES = [
  { value: 'Open',               label: 'Tiếp nhận' },
  { value: 'Assigned',           label: 'Đã phân công' },
  { value: 'Diagnosing',         label: 'Đang chẩn đoán' },
  { value: 'Pending Parts',      label: 'Chờ vật tư' },
  { value: 'In Repair',          label: 'Đang sửa chữa' },
  { value: 'Pending Inspection', label: 'Chờ nghiệm thu' },
  { value: 'Completed',          label: 'Hoàn thành' },
  { value: 'Cannot Repair',      label: 'Không thể sửa' },
  { value: 'Cancelled',          label: 'Đã hủy' },
]

const PRIORITIES = [
  { value: 'Critical', label: 'Khẩn cấp' },
  { value: 'High',     label: 'Cao' },
  { value: 'Medium',   label: 'Trung bình' },
  { value: 'Low',      label: 'Thấp' },
]

interface Chip { key: 'status' | 'priority' | 'search'; label: string }
const activeChips = computed<Chip[]>(() => {
  const chips: Chip[] = []
  if (statusFilter.value) {
    const s = CM_STATUSES.find(x => x.value === statusFilter.value)
    chips.push({ key: 'status', label: s?.label ?? statusFilter.value })
  }
  if (priorityFilter.value) {
    const p = PRIORITIES.find(x => x.value === priorityFilter.value)
    chips.push({ key: 'priority', label: p?.label ?? priorityFilter.value })
  }
  if (search.value.trim()) chips.push({ key: 'search', label: `"${search.value.trim()}"` })
  return chips
})

const activeFilterCount = computed(() => activeChips.value.length)

function clearChip(key: string) {
  if (key === 'status') statusFilter.value = ''
  else if (key === 'priority') priorityFilter.value = ''
  else search.value = ''
}

function resetFilters() {
  statusFilter.value = ''
  priorityFilter.value = ''
  search.value = ''
  store.fetchWorkOrders({})
}

// Nhấp vào badge trong bảng → lọc ngay
function quickFilter(key: 'status' | 'priority', value: string) {
  if (!value) return
  if (key === 'status') statusFilter.value = value
  else priorityFilter.value = value
  showFilters.value = false
}

function applyFilters() {
  const f: Record<string, string> = {}
  if (statusFilter.value) f.status = statusFilter.value
  if (priorityFilter.value) f.priority = priorityFilter.value
  store.fetchWorkOrders(Object.keys(f).length ? f : {})
}

onMounted(() => store.fetchWorkOrders())
watch([statusFilter, priorityFilter], () => applyFilters())

const filteredWOs = computed(() => {
  if (!search.value) return store.workOrders
  const q = search.value.toLowerCase()
  return store.workOrders.filter(w =>
    w.name.toLowerCase().includes(q) || (w.asset_name || '').toLowerCase().includes(q)
  )
})
</script>

<template>
  <div class="page-container animate-fade-in">
    <PageHeader
      title="Lệnh Sửa chữa"
      :subtitle="`Tổng ${store.pagination.total ?? filteredWOs.length} lệnh`"
      :breadcrumb="[{ label: 'IMM-09 · Sửa chữa', to: '/cm/dashboard' }, { label: 'Danh sách' }]"
    >
      <template #actions>
        <FilterToggleButton v-model="showFilters" :count="activeFilterCount" />
        <button class="btn-primary" @click="router.push('/cm/create')">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          Tạo lệnh mới
        </button>
      </template>
    </PageHeader>

    <ListFilterBar
      :show="showFilters"
      :chips="activeChips"
      v-model:search="search"
      search-placeholder="Tìm theo mã lệnh, tên thiết bị..."
      @reset="resetFilters"
      @clear-chip="clearChip"
      @apply="applyFilters"
    >
      <template #fields>
        <div class="form-group">
          <label class="form-label">Trạng thái</label>
          <select v-model="statusFilter" class="form-select">
            <option value="">Tất cả trạng thái</option>
            <option v-for="s in CM_STATUSES" :key="s.value" :value="s.value">{{ s.label }}</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Ưu tiên</label>
          <select v-model="priorityFilter" class="form-select">
            <option value="">Tất cả ưu tiên</option>
            <option v-for="p in PRIORITIES" :key="p.value" :value="p.value">{{ p.label }}</option>
          </select>
        </div>
      </template>
    </ListFilterBar>

    <!-- Loading -->
    <div v-if="store.loading" class="table-wrapper">
      <SkeletonLoader variant="table" :rows="6" />
    </div>

    <!-- Error -->
    <div v-else-if="store.error" class="alert-error">
      <svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <span class="flex-1">{{ store.error }}</span>
      <button class="text-xs font-semibold underline hover:no-underline" @click="store.fetchWorkOrders()">Thử lại</button>
    </div>

    <!-- Table -->
    <div v-else class="table-wrapper">
      <!-- Info row -->
      <div class="flex items-center justify-between px-4 py-2.5 border-b border-slate-100 bg-slate-50/60 text-xs text-slate-500">
        <span>Hiển thị <strong class="text-slate-700">{{ filteredWOs.length }}</strong> lệnh</span>
        <button v-if="activeFilterCount > 0" class="text-red-500 hover:text-red-700 font-medium" @click="resetFilters">Xóa tất cả</button>
      </div>
      <table class="min-w-full divide-y divide-slate-100">
        <thead>
          <tr>
            <th class="table-header">Mã lệnh</th>
            <th class="table-header">Thiết bị</th>
            <th class="table-header">Loại / Ưu tiên</th>
            <th class="table-header">Ngày tiếp nhận</th>
            <th class="table-header">Kỹ thuật viên</th>
            <th class="table-header">Thời gian sửa chữa TB</th>
            <th class="table-header">Trạng thái</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-50">
          <tr
v-for="wo in filteredWOs" :key="wo.name"
            class="hover:bg-slate-50 cursor-pointer transition-colors"
            @click="router.push(`/cm/work-orders/${wo.name}`)"
          >
            <td class="table-cell">
              <div class="font-mono text-sm font-semibold text-brand-700">{{ wo.name }}</div>
              <div v-if="wo.sla_breached" class="text-xs text-red-600 font-medium mt-0.5">SLA vi phạm</div>
              <div v-if="wo.is_repeat_failure" class="text-xs text-amber-700 mt-0.5">Tái hỏng</div>
            </td>
            <td class="table-cell">
              <div class="font-medium text-slate-900">{{ wo.asset_name || wo.asset_ref }}</div>
              <div class="text-xs text-slate-400 font-mono mt-0.5">{{ wo.asset_ref }}</div>
              <div v-if="wo.department_name || wo.location_name" class="text-xs text-slate-500 mt-0.5">
                {{ [wo.department_name, wo.location_name].filter(Boolean).join(' · ') }}
              </div>
            </td>
            <td class="table-cell">
              <div class="text-sm text-slate-700">{{ repairTypeLabel(wo.repair_type) }}</div>
              <!-- Priority badge — click để lọc -->
              <button
                :class="['inline-block mt-1 px-2 py-0.5 rounded-full text-xs font-medium transition-all hover:ring-2 hover:ring-offset-1 hover:ring-current/50', priorityClass(wo.priority)]"
                :title="`Lọc: ${priorityLabel(wo.priority)}`"
                @click.stop="quickFilter('priority', wo.priority)"
              >
{{ priorityLabel(wo.priority) }}
</button>
            </td>
            <td class="table-cell text-sm text-slate-600">{{ formatDateTime(wo.open_datetime) }}</td>
            <td class="table-cell">
              <div class="text-slate-700 text-sm">{{ wo.assigned_to_name || wo.assigned_to || '—' }}</div>
              <div v-if="wo.assigned_to && wo.assigned_to_name" class="text-xs text-slate-400">{{ wo.assigned_to }}</div>
            </td>
            <td class="table-cell">
              <span v-if="wo.mttr_hours" :class="wo.sla_breached ? 'text-red-600 font-semibold' : 'text-slate-600'">
                {{ wo.mttr_hours }}h
              </span>
              <span v-else class="text-slate-400">—</span>
            </td>
            <td class="table-cell">
              <!-- Status badge — click để lọc -->
              <button
                :class="['inline-block px-2.5 py-1 rounded-full text-xs font-medium transition-all hover:ring-2 hover:ring-offset-1 hover:ring-current/50', getStatusColor(wo.status)]"
                :title="`Lọc: ${translateStatus(wo.status)}`"
                @click.stop="quickFilter('status', wo.status)"
              >
{{ translateStatus(wo.status) }}
</button>
            </td>
          </tr>
          <tr v-if="filteredWOs.length === 0">
            <td colspan="7" class="py-16 text-center text-slate-400">
              <p class="text-sm font-medium">Không tìm thấy lệnh sửa chữa nào</p>
              <button v-if="activeFilterCount > 0" class="text-xs text-blue-500 hover:text-blue-700 underline mt-2" @click="resetFilters">
                Xóa bộ lọc để xem tất cả
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <BasePagination :pagination="store.pagination" @page-change="p => store.fetchWorkOrders({}, p)" />
  </div>
</template>
