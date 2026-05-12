<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useImm06Store } from '@/stores/imm06'
import { useAuthStore } from '@/stores/auth'
import { useApi } from '@/composables/useApi'
import { ROLES_TRAINING_CONDUCT } from '@/constants/roles'
import PageHeader from '@/components/common/PageHeader.vue'
import BasePagination from '@/components/common/BasePagination.vue'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
import FilterToggleButton from '@/components/common/FilterToggleButton.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'

const router = useRouter()
const store = useImm06Store()
const authStore = useAuthStore()
const api = useApi()

const { sessions, sessionPagination, loading } = storeToRefs(store)

const filterState = ref('')
const filterType = ref('')
const showFilters = ref(false)

const canCreate = computed(() => authStore.hasAnyRole(ROLES_TRAINING_CONDUCT))

const WORKFLOW_STATES = [
  { value: 'Planned',     label: 'Đã lên kế hoạch' },
  { value: 'Confirmed',   label: 'Đã xác nhận' },
  { value: 'In Progress', label: 'Đang diễn ra' },
  { value: 'Completed',   label: 'Hoàn thành' },
  { value: 'Verified',    label: 'Đã xác minh' },
  { value: 'Closed',      label: 'Đã đóng' },
  { value: 'Cancelled',   label: 'Đã hủy' },
]

const SESSION_TYPES = [
  { value: 'Onsite', label: 'Tại chỗ' },
  { value: 'Online', label: 'Trực tuyến' },
  { value: 'Hybrid', label: 'Kết hợp' },
]

interface Chip { key: string; label: string }
const activeChips = computed<Chip[]>(() => {
  const chips: Chip[] = []
  if (filterState.value) {
    const s = WORKFLOW_STATES.find(x => x.value === filterState.value)
    chips.push({ key: 'state', label: s?.label ?? filterState.value })
  }
  if (filterType.value) {
    const t = SESSION_TYPES.find(x => x.value === filterType.value)
    chips.push({ key: 'type', label: t?.label ?? filterType.value })
  }
  return chips
})
const activeFilterCount = computed(() => activeChips.value.length)

function clearChip(key: string) {
  if (key === 'state') filterState.value = ''
  else filterType.value = ''
  load(1)
}

function resetFilters() {
  filterState.value = ''
  filterType.value = ''
  load(1)
}

async function load(page = 1) {
  const filters: Record<string, unknown> = {}
  if (filterState.value) filters.workflow_state = filterState.value
  if (filterType.value) filters.session_type = filterType.value
  await api.run(() => store.fetchSessions(filters, page))
}

function sessionTypeLabel(v: string) {
  return SESSION_TYPES.find(t => t.value === v)?.label ?? v
}

function stateClass(state: string): string {
  const map: Record<string, string> = {
    Planned:       'bg-yellow-100 text-yellow-700',
    Confirmed:     'bg-blue-100 text-blue-700',
    'In Progress': 'bg-indigo-100 text-indigo-700',
    Completed:     'bg-emerald-100 text-emerald-700',
    Verified:      'bg-teal-100 text-teal-700',
    Closed:        'bg-slate-100 text-slate-600',
    Cancelled:     'bg-neutral-100 text-neutral-500',
  }
  return map[state] ?? 'bg-neutral-100 text-neutral-600'
}

onMounted(() => load())
</script>

<template>
  <div class="page-container animate-fade-in space-y-5">
    <PageHeader
      title="Buổi đào tạo"
      :subtitle="`Tổng ${sessionPagination.total} buổi`"
      :breadcrumb="[{ label: 'IMM-06 · Đào tạo & Năng lực', to: '/imm06/sessions' }, { label: 'Danh sách buổi đào tạo' }]"
    >
      <template #actions>
        <FilterToggleButton v-model="showFilters" :count="activeFilterCount" />
        <button
          v-if="canCreate"
          class="btn-primary"
          @click="router.push('/imm06/sessions/new')"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          Tạo mới
        </button>
      </template>
    </PageHeader>

    <ListFilterBar
      :show="showFilters"
      :chips="activeChips"
      :show-search="false"
      @reset="resetFilters"
      @clear-chip="clearChip"
      @apply="load(1)"
    >
      <template #fields>
        <div class="form-group">
          <label class="form-label">Trạng thái</label>
          <select v-model="filterState" class="form-select" @change="load(1)">
            <option value="">Tất cả trạng thái</option>
            <option v-for="s in WORKFLOW_STATES" :key="s.value" :value="s.value">{{ s.label }}</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Hình thức</label>
          <select v-model="filterType" class="form-select" @change="load(1)">
            <option value="">Tất cả hình thức</option>
            <option v-for="t in SESSION_TYPES" :key="t.value" :value="t.value">{{ t.label }}</option>
          </select>
        </div>
      </template>
    </ListFilterBar>

    <div class="table-wrapper">
      <div class="flex items-center justify-between px-4 py-2.5 border-b border-slate-100 bg-slate-50/60 text-xs text-slate-500">
        <span>Hiển thị <strong class="text-slate-700">{{ sessions?.length ?? 0 }}</strong> / {{ sessionPagination.total }} buổi</span>
        <button v-if="activeFilterCount > 0" class="text-red-500 hover:text-red-700 font-medium" @click="resetFilters">Xóa tất cả</button>
      </div>

      <div v-if="loading" class="p-4">
        <SkeletonLoader variant="table" :rows="6" />
      </div>
      <div v-else-if="!sessions.length" class="flex flex-col items-center justify-center py-16 text-slate-400">
        <svg class="w-10 h-10 mb-3 text-slate-300" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 012.25-2.25h13.5A2.25 2.25 0 0121 7.5v11.25m-18 0A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75m-18 0v-7.5A2.25 2.25 0 015.25 9h13.5A2.25 2.25 0 0121 11.25v7.5" />
        </svg>
        <p class="text-sm font-medium">Chưa có buổi đào tạo nào</p>
        <button v-if="activeFilterCount > 0" class="text-xs text-blue-500 hover:text-blue-700 underline mt-2" @click="resetFilters">
          Xóa bộ lọc để xem tất cả
        </button>
      </div>
      <div v-else class="overflow-x-auto">
        <table class="min-w-full divide-y divide-slate-100">
          <thead>
            <tr>
              <th class="table-header">Mã</th>
              <th class="table-header">Chương trình</th>
              <th class="table-header">Ngày</th>
              <th class="table-header">Hình thức</th>
              <th class="table-header">Giảng viên</th>
              <th class="table-header">Trạng thái</th>
              <th class="table-header text-right">Số học viên</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr
              v-for="s in sessions"
              :key="s.name"
              class="hover:bg-slate-50 cursor-pointer transition-colors"
              @click="router.push(`/imm06/sessions/${s.name}`)"
            >
              <td class="table-cell font-mono text-xs text-slate-500">{{ s.name }}</td>
              <td class="table-cell">
                <div class="font-medium text-slate-900 truncate max-w-[200px]">{{ (s as any).program_name || s.training_program }}</div>
              </td>
              <td class="table-cell text-slate-600 text-sm">{{ s.session_date }}</td>
              <td class="table-cell text-sm">
                <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-600">
                  {{ sessionTypeLabel(s.session_type) }}
                </span>
              </td>
              <td class="table-cell text-slate-600 text-sm">
                {{ (s as any).trainer_name || s.instructor_external_name || '—' }}
              </td>
              <td class="table-cell">
                <span
                  class="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-medium"
                  :class="stateClass(s.workflow_state)"
                >
                  {{ s.workflow_state === 'Planned' ? 'Đã lên kế hoạch'
                    : s.workflow_state === 'Confirmed' ? 'Đã xác nhận'
                    : s.workflow_state === 'In Progress' ? 'Đang diễn ra'
                    : s.workflow_state === 'Completed' ? 'Hoàn thành'
                    : s.workflow_state === 'Verified' ? 'Đã xác minh'
                    : s.workflow_state === 'Closed' ? 'Đã đóng'
                    : s.workflow_state === 'Cancelled' ? 'Đã hủy'
                    : s.workflow_state }}
                </span>
              </td>
              <td class="table-cell text-right text-sm font-medium text-slate-700">
                {{ (s as any).attendee_count ?? s.participant_count ?? (s.participants?.length ?? '—') }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <BasePagination :pagination="sessionPagination" @page-change="load" />
  </div>
</template>
