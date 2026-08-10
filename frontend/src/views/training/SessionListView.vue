<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useImm06Store } from '@/stores/imm06'
import { useApi } from '@/composables/useApi'
import { useCapabilities } from '@/composables/useCapabilities'
import PageHeader from '@/components/common/PageHeader.vue'
import BasePagination from '@/components/common/BasePagination.vue'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
import FilterToggleButton from '@/components/common/FilterToggleButton.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'
import ListPageShell from '@/components/ui/ListPageShell.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'

const router = useRouter()
const store = useImm06Store()
const api = useApi()
const { can } = useCapabilities()

const { sessions, sessionPagination, loading } = storeToRefs(store)

const filterState = ref('')
const filterType = ref('')
const showFilters = ref(false)

const canCreate = computed(() => can('training.write'))

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

// ── Trạng thái nạp danh sách (AC-UX-047 lô 3 · biến thể D — 02 §14.2, khuôn §13.2) ─────────
// `stores/imm06.ts:40` dùng CHUNG một ô `error` cho 3 danh sách + MỌI hành động ghi.
// Thêm một bẫy riêng của nhóm IMM-06: `api.run(() => store.fetchXxx())` chỉ bắt được
// EXCEPTION, mà kho trạng thái đã `catch` rồi ⇒ `api.lastError` LUÔN null khi danh sách hỏng.
// Đọc lỗi từ `api.lastError` = luôn thấy "không lỗi". Vì vậy phải CHỤP `store.error` ngay sau
// `await` rồi trả ô dùng chung về sạch (INV-UX3-28).
const loadError = ref<string | null>(null)

function _captureLoadError() {
  loadError.value = store.error ?? null
  if (loadError.value) store.error = null
}

// Chữ trạng thái rỗng — SSoT là bảng copy 02 §14.4 (LL-FE-53: 100% tiếng Việt).
const emptyTitle = computed(() =>
  activeFilterCount.value > 0 ? 'Không có buổi đào tạo nào phù hợp' : 'Chưa có buổi đào tạo nào',
)
const emptyHint = 'Buổi đào tạo được mở từ một chương trình đào tạo và ghi nhận người tham dự.'

async function load(page = 1) {
  loadError.value = null
  store.error = null
  const filters: Record<string, unknown> = {}
  if (filterState.value) filters.workflow_state = filterState.value
  if (filterType.value) filters.session_type = filterType.value
  await api.run(() => store.fetchSessions(filters, page))
  _captureLoadError()
}

function sessionTypeLabel(v: string) {
  return SESSION_TYPES.find(t => t.value === v)?.label ?? v
}

onMounted(() => load())
</script>

<template>
  <div>
    <ListPageShell
      :loading="loading"
      :error-message="loadError"
      :is-empty="!sessions.length"
      :empty-title="emptyTitle"
      :empty-hint="emptyHint"
      @retry="load()">
      <template #header>
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
      </template>

      <template #filters>

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
      </template>

      <template #skeleton><SkeletonLoader variant="table" :rows="6" /></template>

      <template #empty-action>
        <button v-if="activeFilterCount > 0" class="text-xs text-brand-600 hover:text-brand-700 font-medium underline" @click="resetFilters">
          Xóa bộ lọc để xem tất cả
        </button>
        <button v-else-if="canCreate" class="btn-primary" @click="router.push('/imm06/sessions/new')">Tạo buổi đào tạo</button>
      </template>

      <template #toolbar>
      <div class="flex items-center justify-between px-4 py-2.5 border-b border-slate-100 bg-slate-50/60 text-xs text-slate-500">
        <span>Hiển thị <strong class="text-slate-700">{{ sessions?.length ?? 0 }}</strong> / {{ sessionPagination.total }} buổi</span>
        <button v-if="activeFilterCount > 0" class="text-red-500 hover:text-red-700 font-medium" @click="resetFilters">Xóa tất cả</button>
      </div>

      </template>

        <!-- Mobile cards -->
        <div class="mobile-card-list sm:hidden">
          <div
            v-for="s in sessions"
            :key="s.name"
            class="mobile-card"
            @click="router.push(`/imm06/sessions/${s.name}`)"
          >
            <div class="flex items-center justify-between mb-2">
              <span class="font-mono text-sm font-semibold text-brand-700">{{ s.name }}</span>
              <StatusBadge :state="s.workflow_state" />
            </div>
            <p class="text-sm font-medium text-slate-900 truncate">{{ s.program_name || s.training_program }}</p>
            <div class="flex flex-wrap gap-x-2 gap-y-1 mt-1.5 text-xs text-slate-500">
              <span v-if="s.session_date">{{ s.session_date }}</span>
              <span>· {{ sessionTypeLabel(s.session_type) }}</span>
              <span v-if="s.trainer_name || s.instructor_external_name">· {{ s.trainer_name || s.instructor_external_name }}</span>
            </div>
          </div>
        </div>

        <!-- Desktop table -->
        <div class="hidden sm:block overflow-x-auto">
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
                  <div class="font-medium text-slate-900 truncate max-w-[200px]">{{ s.program_name || s.training_program }}</div>
                </td>
                <td class="table-cell text-slate-600 text-sm">{{ s.session_date }}</td>
                <td class="table-cell text-sm">
                  <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-600">
                    {{ sessionTypeLabel(s.session_type) }}
                  </span>
                </td>
                <td class="table-cell text-slate-600 text-sm">
                  {{ s.trainer_name || s.instructor_external_name || '—' }}
                </td>
                <td class="table-cell">
                  <StatusBadge :state="s.workflow_state" />
                </td>
                <td class="table-cell text-right text-sm font-medium text-slate-700">
                  {{ s.attendee_count ?? s.participant_count ?? (s.participants?.length ?? '—') }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>

      <template #pagination>
        <BasePagination :pagination="sessionPagination" @page-change="load" />
      </template>
    </ListPageShell>
  </div>
</template>
