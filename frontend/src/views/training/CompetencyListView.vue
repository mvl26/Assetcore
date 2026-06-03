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
import StatusBadge from '@/components/common/StatusBadge.vue'

const router = useRouter()
const store = useImm06Store()
const api = useApi()
const { can } = useCapabilities()

const canCreateSession = computed(() => can('training.write'))

const { competencies, competencyPagination, loading, error } = storeToRefs(store)

const filterState = ref('')
const filterModel = ref('')
const showFilters = ref(false)

// Phải khớp chính xác BE CompetencyStatus (services/imm06.py)
const WORKFLOW_STATES = [
  { value: 'Pending Assessment', label: 'Chờ đánh giá' },
  { value: 'Active',             label: 'Hiệu lực' },
  { value: 'Expiring',           label: 'Sắp hết hạn' },
  { value: 'Expired',            label: 'Hết hạn' },
  { value: 'Suspended',          label: 'Tạm ngưng' },
  { value: 'Revoked',            label: 'Đã thu hồi' },
]

const COMPETENCY_LEVELS = [
  { value: 'Trainee',         label: 'Học viên' },
  { value: 'Operator',        label: 'Vận hành viên' },
  { value: 'Senior Operator', label: 'Vận hành viên cao cấp' },
  { value: 'Trainer',         label: 'Giảng viên' },
]

interface Chip { key: string; label: string }
const activeChips = computed<Chip[]>(() => {
  const chips: Chip[] = []
  if (filterState.value) {
    const s = WORKFLOW_STATES.find(x => x.value === filterState.value)
    chips.push({ key: 'state', label: s?.label ?? filterState.value })
  }
  if (filterModel.value) chips.push({ key: 'model', label: `Model: ${filterModel.value}` })
  return chips
})
const activeFilterCount = computed(() => activeChips.value.length)

function clearChip(key: string) {
  if (key === 'state') filterState.value = ''
  else filterModel.value = ''
  load(1)
}

function resetFilters() {
  filterState.value = ''
  filterModel.value = ''
  load(1)
}

async function load(page = 1) {
  const filters: Record<string, unknown> = {}
  if (filterState.value) filters.workflow_state = filterState.value
  if (filterModel.value) filters.device_model = filterModel.value
  await api.run(() => store.fetchCompetencies(filters, page))
}

function levelLabel(v: string) {
  return COMPETENCY_LEVELS.find(l => l.value === v)?.label ?? v
}

function expiryClass(days: number | null): string {
  if (days === null) return 'text-slate-400'
  if (days < 30) return 'text-red-600 font-semibold'
  if (days < 60) return 'text-amber-600 font-semibold'
  return 'text-slate-600'
}

function formatDaysUntilExpiry(days: number | null): string {
  if (days === null) return '—'
  if (days < 0) return 'Đã hết hạn'
  if (days === 0) return 'Hôm nay'
  return `${days} ngày`
}

onMounted(() => load())
</script>

<template>
  <div class="page-container animate-fade-in space-y-5">
    <PageHeader
      title="Năng lực nhân viên"
      :subtitle="`Tổng ${competencyPagination.total} bản ghi năng lực`"
      :breadcrumb="[{ label: 'IMM-06 · Đào tạo & Năng lực', to: '/imm06/competencies' }, { label: 'Danh sách năng lực' }]"
    >
      <template #actions>
        <FilterToggleButton v-model="showFilters" :count="activeFilterCount" />
        <button
          class="btn-ghost text-sm"
          title="Xem danh sách buổi đào tạo — hoàn thành buổi đào tạo để hệ thống tự sinh hồ sơ năng lực"
          @click="router.push('/imm06/sessions')"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 012.25-2.25h13.5A2.25 2.25 0 0121 7.5v11.25m-18 0A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75m-18 0v-7.5A2.25 2.25 0 015.25 9h13.5A2.25 2.25 0 0121 11.25v7.5" />
          </svg>
          Buổi đào tạo
        </button>
        <button
          v-if="canCreateSession"
          class="btn-primary"
          title="Tạo buổi đào tạo mới — hoàn thành buổi đào tạo để hệ thống tự sinh năng lực cho học viên đạt"
          @click="router.push('/imm06/sessions/new')"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          Tạo buổi đào tạo
        </button>
      </template>
    </PageHeader>

    <!-- Process hint: explain how competencies are generated -->
    <div class="card border border-blue-200 bg-blue-50 px-4 py-3 text-xs text-blue-700 flex items-start gap-3">
      <svg class="w-4 h-4 shrink-0 mt-0.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M13 16h-1v-4h-1m1-4h.01M12 2a10 10 0 100 20 10 10 0 000-20z" />
      </svg>
      <div class="flex-1">
        <p class="font-medium">Hồ sơ năng lực được sinh tự động.</p>
        <p class="mt-0.5">
          Khi một <strong>Buổi đào tạo</strong> hoàn thành (state In Progress → Completed) và học viên đạt điểm,
          hệ thống tự tạo bản ghi năng lực ở trạng thái <em>Pending Assessment</em> chờ Manager phê duyệt.
          Dùng các action ở trang chi tiết để Phê duyệt / Tái chứng nhận / Thu hồi.
        </p>
      </div>
    </div>

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
          <label class="form-label">Device Model</label>
          <input v-model="filterModel" class="form-input" placeholder="Mã Device Model..." @keyup.enter="load(1)" />
        </div>
      </template>
    </ListFilterBar>

    <div class="table-wrapper">
      <div class="flex items-center justify-between px-4 py-2.5 border-b border-slate-100 bg-slate-50/60 text-xs text-slate-500">
        <span>Hiển thị <strong class="text-slate-700">{{ competencies?.length ?? 0 }}</strong> / {{ competencyPagination.total }} bản ghi</span>
        <button v-if="activeFilterCount > 0" class="text-red-500 hover:text-red-700 font-medium" @click="resetFilters">Xóa tất cả</button>
      </div>

      <div v-if="loading" class="p-4">
        <SkeletonLoader variant="table" :rows="6" />
      </div>
      <div v-else-if="error" class="m-4 rounded border border-rose-200 bg-rose-50 px-4 py-3 text-rose-700 flex items-center gap-3">
        <span class="flex-1">{{ error }}</span>
        <button class="text-sm underline" @click="load()">Thử lại</button>
      </div>
      <div v-else-if="!competencies.length" class="flex flex-col items-center justify-center py-16 text-slate-400">
        <svg class="w-10 h-10 mb-3 text-slate-300" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
        </svg>
        <p class="text-sm font-medium">Chưa có bản ghi năng lực nào</p>
        <p class="text-xs text-slate-500 mt-1 max-w-md text-center">
          Năng lực được sinh khi học viên hoàn thành buổi đào tạo.
        </p>
        <div class="flex gap-2 mt-3">
          <button v-if="activeFilterCount > 0" class="text-xs text-blue-500 hover:text-blue-700 underline" @click="resetFilters">
            Xóa bộ lọc
          </button>
          <button
            v-if="canCreateSession"
            class="text-xs px-3 py-1 rounded-md bg-blue-500 text-white hover:bg-blue-600"
            @click="router.push('/imm06/sessions/new')"
          >
            + Tạo buổi đào tạo
          </button>
          <button
            class="text-xs px-3 py-1 rounded-md border border-slate-300 text-slate-600 hover:bg-slate-50"
            @click="router.push('/imm06/sessions')"
          >
            Xem buổi đào tạo
          </button>
        </div>
      </div>
      <template v-else>
        <!-- Mobile cards -->
        <div class="mobile-card-list sm:hidden">
          <div
            v-for="c in competencies"
            :key="c.name"
            class="mobile-card"
            @click="router.push(`/imm06/competencies/${c.name}`)"
          >
            <div class="flex items-center justify-between mb-2">
              <span class="font-mono text-sm font-semibold text-brand-700">{{ c.name }}</span>
              <StatusBadge :state="c.workflow_state" />
            </div>
            <p class="text-sm font-medium text-slate-900 truncate">{{ c.user_full_name ?? c.user }}</p>
            <div class="flex flex-wrap gap-x-2 gap-y-1 mt-1.5 text-xs text-slate-500">
              <span :title="c.device_model">{{ c.device_model_name ?? c.device_model }}</span>
              <span>· <span class="px-1.5 py-0.5 rounded bg-blue-50 text-blue-700">{{ levelLabel(c.competency_level) }}</span></span>
              <span :class="expiryClass(c.days_until_expiry)">· {{ formatDaysUntilExpiry(c.days_until_expiry) }}</span>
            </div>
          </div>
          <div v-if="competencies.length === 0" class="py-12 text-center text-slate-400">
            <p class="text-sm">Không có dữ liệu</p>
          </div>
        </div>

        <!-- Desktop table -->
        <div class="hidden sm:block overflow-x-auto">
          <table class="min-w-full divide-y divide-slate-100">
            <thead>
              <tr>
                <th class="table-header">Nhân viên</th>
                <th class="table-header">Device Model</th>
                <th class="table-header">Cấp độ</th>
                <th class="table-header">Ngày đạt</th>
                <th class="table-header">Ngày hết hạn</th>
                <th class="table-header text-right">Còn lại</th>
                <th class="table-header">Trạng thái</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              <tr
                v-for="c in competencies"
                :key="c.name"
                class="hover:bg-slate-50 cursor-pointer transition-colors"
                @click="router.push(`/imm06/competencies/${c.name}`)"
              >
                <td class="table-cell">
                  <div class="font-medium text-slate-900">{{ c.user_full_name ?? c.user }}</div>
                  <div v-if="c.user_full_name" class="text-xs text-slate-400 font-mono">{{ c.user }}</div>
                </td>
                <td class="table-cell text-slate-600 text-sm" :title="c.device_model">{{ c.device_model_name ?? c.device_model }}</td>
                <td class="table-cell text-sm">
                  <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-50 text-blue-700">
                    {{ levelLabel(c.competency_level) }}
                  </span>
                </td>
                <td class="table-cell text-slate-600 text-sm">{{ c.achieved_date }}</td>
                <td class="table-cell text-sm" :class="c.is_expired ? 'text-red-500 font-medium' : 'text-slate-600'">
                  {{ c.expiry_date ?? '—' }}
                </td>
                <td class="table-cell text-right text-sm" :class="expiryClass(c.days_until_expiry)">
                  {{ formatDaysUntilExpiry(c.days_until_expiry) }}
                </td>
                <td class="table-cell">
                  <StatusBadge :state="c.workflow_state" />
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
    </div>

    <BasePagination :pagination="competencyPagination" @page-change="load" />
  </div>
</template>
