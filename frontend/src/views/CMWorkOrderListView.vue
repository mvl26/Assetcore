<script setup lang="ts">
import { onMounted, ref, computed, watch } from 'vue'
import { useImm09Store } from '@/stores/imm09'
import { useRouter } from 'vue-router'
import { priorityLabel, priorityClass, repairTypeLabel } from '@/utils/labels'
import { translateStatus, getStatusColor, formatDateTime } from '@/utils/formatters'

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

function clearChip(key: Chip['key']) {
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

    <!-- Header -->
    <div class="flex items-start justify-between mb-5">
      <div>
        <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">IMM-09 · Sửa chữa CM</p>
        <h1 class="text-2xl font-bold text-slate-900">Danh sách Lệnh Sửa chữa</h1>
        <p class="text-sm text-slate-500 mt-1">
          Tổng <strong class="text-slate-700">{{ store.pagination.total ?? filteredWOs.length }}</strong> lệnh
        </p>
      </div>
      <div class="flex items-center gap-2 shrink-0">
        <button
          class="relative flex items-center gap-1.5 px-3 py-2 text-sm font-medium rounded-lg border transition-colors"
          :class="showFilters
            ? 'bg-brand-50 border-brand-300 text-brand-700'
            : 'bg-white border-slate-300 text-slate-600 hover:border-slate-400'"
          @click="showFilters = !showFilters"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M3 4h18M7 8h10M11 12h2M9 16h6" />
          </svg>
          Bộ lọc
          <span v-if="activeFilterCount > 0"
            class="inline-flex items-center justify-center w-4 h-4 text-[10px] font-bold rounded-full bg-blue-500 text-white">
            {{ activeFilterCount }}
          </span>
          <svg class="w-3.5 h-3.5 transition-transform duration-200" :class="showFilters ? 'rotate-180' : ''"
               fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
          </svg>
        </button>
        <button class="btn-primary shrink-0" @click="router.push('/cm/create')">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          Tạo lệnh mới
        </button>
      </div>
    </div>

    <!-- Active chips (khi panel đóng) -->
    <Transition
      enter-active-class="transition-all duration-200 ease-out"
      enter-from-class="opacity-0 -translate-y-1"
      enter-to-class="opacity-100 translate-y-0"
      leave-active-class="transition-all duration-150 ease-in"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div v-if="activeChips.length > 0 && !showFilters" class="flex flex-wrap items-center gap-2 mb-4">
        <span class="text-xs text-slate-400 font-medium">Đang lọc:</span>
        <button v-for="chip in activeChips" :key="chip.key"
          class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200 hover:bg-blue-100 transition-colors"
          @click="clearChip(chip.key)"
        >
          {{ chip.label }}
          <svg class="w-3 h-3 opacity-60" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
        <button class="text-xs text-slate-400 hover:text-red-500 underline underline-offset-2" @click="resetFilters">
          Xóa tất cả
        </button>
      </div>
    </Transition>

    <!-- Collapsible filter panel -->
    <Transition
      enter-active-class="transition-all duration-200 ease-out overflow-hidden"
      enter-from-class="opacity-0 max-h-0"
      enter-to-class="opacity-100 max-h-40"
      leave-active-class="transition-all duration-150 ease-in overflow-hidden"
      leave-from-class="opacity-100 max-h-40"
      leave-to-class="opacity-0 max-h-0"
    >
      <div v-show="showFilters" class="card mb-5 p-4 space-y-3">
        <div class="flex flex-wrap gap-3">
          <input v-model="search" placeholder="Tìm theo mã lệnh, tên thiết bị..."
            class="form-input flex-1 min-w-48" @keyup.enter="applyFilters" />
          <select v-model="statusFilter" class="form-select w-52">
            <option value="">Tất cả trạng thái</option>
            <option v-for="s in CM_STATUSES" :key="s.value" :value="s.value">{{ s.label }}</option>
          </select>
          <select v-model="priorityFilter" class="form-select w-40">
            <option value="">Tất cả ưu tiên</option>
            <option v-for="p in PRIORITIES" :key="p.value" :value="p.value">{{ p.label }}</option>
          </select>
          <button class="btn-ghost text-sm" @click="resetFilters">Đặt lại</button>
        </div>
        <div v-if="activeChips.length > 0" class="flex flex-wrap items-center gap-2 pt-3 border-t border-slate-100">
          <span class="text-xs text-slate-400 font-medium">Đang lọc:</span>
          <button v-for="chip in activeChips" :key="chip.key"
            class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200 hover:bg-blue-100 transition-colors"
            @click="clearChip(chip.key)"
          >
            {{ chip.label }}
            <svg class="w-3 h-3 opacity-60" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>
    </Transition>

    <!-- Loading -->
    <div v-if="store.loading" class="card">
      <div v-for="i in 6" :key="i" class="flex gap-4 py-3 border-b border-slate-100 last:border-0 animate-pulse">
        <div class="h-4 bg-slate-100 rounded w-28" />
        <div class="h-4 bg-slate-100 rounded flex-1" />
        <div class="h-4 bg-slate-100 rounded w-20" />
        <div class="h-4 bg-slate-100 rounded w-24" />
      </div>
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
            <th class="table-header">MTTR</th>
            <th class="table-header">Trạng thái</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-50">
          <tr v-for="wo in filteredWOs" :key="wo.name"
            class="hover:bg-slate-50 cursor-pointer transition-colors"
            @click="router.push(`/cm/work-orders/${wo.name}`)"
          >
            <td class="table-cell">
              <div class="font-mono text-sm font-semibold text-blue-700">{{ wo.name }}</div>
              <div v-if="wo.sla_breached" class="text-xs text-red-600 font-medium mt-0.5">⚠ SLA vi phạm</div>
              <div v-if="wo.is_repeat_failure" class="text-xs text-orange-500 mt-0.5">↺ Tái hỏng</div>
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
              >{{ priorityLabel(wo.priority) }}</button>
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
              >{{ translateStatus(wo.status) }}</button>
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

    <!-- Pagination -->
    <div v-if="store.pagination.total_pages > 1" class="flex justify-center mt-5 gap-1">
      <button v-for="p in store.pagination.total_pages" :key="p"
        :class="['px-3 py-1.5 rounded-lg text-sm border transition-colors font-medium',
          p === store.pagination.page
            ? 'bg-blue-600 text-white border-blue-600'
            : 'border-slate-300 text-slate-600 hover:bg-slate-50']"
        @click="store.fetchWorkOrders({}, p)"
      >{{ p }}</button>
    </div>
  </div>
</template>
