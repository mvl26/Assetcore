<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
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
import { competencyEffectiveState, EXPIRY_WINDOW_DAYS } from './competencyStatus'

const route = useRoute()
const router = useRouter()
const store = useImm06Store()
const api = useApi()
const { can } = useCapabilities()

const canCreateSession = computed(() => can('training.write'))

const { competencies, competencyPagination, loading } = storeToRefs(store)

const filterState = ref('')
const filterModel = ref('')
const showFilters = ref(false)

// Drill từ TrainingDashboard: query window = 'expiring' | 'expired'.
// 'expiring' → dùng CHUNG predicate SoT với tile (get_expiring_competencies(60))
// ⇒ INVARIANT card == drill. 'expired' → lọc list_competencies theo state Expired.
const drillWindow = computed<string>(() => String(route.query.window ?? ''))
const drillLabel = computed<string>(() => {
  if (drillWindow.value === 'expiring') return `Sắp hết hạn (trong ${EXPIRY_WINDOW_DAYS} ngày)`
  if (drillWindow.value === 'expired') return 'Đã hết hạn'
  return ''
})

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
  activeFilterCount.value > 0 ? 'Không có bản ghi năng lực nào phù hợp' : 'Chưa có bản ghi năng lực nào',
)
const emptyHint = 'Bản ghi năng lực sinh ra khi người dùng hoàn thành buổi đào tạo và đạt điểm yêu cầu.'

async function load(page = 1) {
  loadError.value = null
  store.error = null
  // Drill 'expiring': dùng predicate SoT của tile (get_expiring_competencies(60))
  // ⇒ số dòng list == giá trị tile (INVARIANT card == drill, BR-06-14).
  if (drillWindow.value === 'expiring') {
    await api.run(() => store.fetchExpiringCompetencies(EXPIRY_WINDOW_DAYS))
    _captureLoadError()
    return
  }
  const filters: Record<string, unknown> = {}
  if (drillWindow.value === 'expired') filters.workflow_state = 'Expired'
  if (filterState.value) filters.workflow_state = filterState.value
  if (filterModel.value) filters.device_model = filterModel.value
  await api.run(() => store.fetchCompetencies(filters, page))
  _captureLoadError()
}

function clearDrill() {
  router.replace({ path: '/imm06/competencies' })
  load(1)
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
  <div>
    <ListPageShell
      :loading="loading"
      :error-message="loadError"
      :is-empty="!competencies.length"
      :empty-title="emptyTitle"
      :empty-hint="emptyHint"
      @retry="load()">
      <template #header>
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
      </template>

      <template #filters>

    <!-- Process hint: explain how competencies are generated -->
    <div class="card border border-blue-200 bg-blue-50 px-4 py-3 text-xs text-blue-700 flex items-start gap-3">
      <svg class="w-4 h-4 shrink-0 mt-0.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M13 16h-1v-4h-1m1-4h.01M12 2a10 10 0 100 20 10 10 0 000-20z" />
      </svg>
      <div class="flex-1">
        <p class="font-medium">Hồ sơ năng lực được sinh tự động.</p>
        <p class="mt-0.5">
          Khi một <strong>Buổi đào tạo</strong> hoàn thành (trạng thái Đang diễn ra → Hoàn thành) và học viên đạt điểm,
          hệ thống tự tạo bản ghi năng lực ở trạng thái <em>Chờ đánh giá</em>, đợi Quản lý phê duyệt.
          Dùng các thao tác ở trang chi tiết để Phê duyệt / Tái chứng nhận / Thu hồi.
        </p>
      </div>
    </div>

    <!-- Drill banner từ TrainingDashboard (window=expiring|expired) -->
    <div
      v-if="drillWindow"
      class="card border border-amber-200 bg-amber-50 px-4 py-2.5 text-sm text-amber-800 flex items-center gap-3"
    >
      <span class="flex-1">
        Đang lọc theo: <strong>{{ drillLabel }}</strong>
      </span>
      <button class="text-xs underline hover:text-amber-900" @click="clearDrill">
        Bỏ lọc
      </button>
    </div>

    <ListFilterBar
      v-if="!drillWindow"
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
      </template>

      <template #skeleton><SkeletonLoader variant="table" :rows="6" /></template>

      <template #empty-action>
        <!-- Rỗng vì đang drill theo thời hạn (?window=expiring|expired) là một NGUYÊN NHÂN
             khác với rỗng-do-lọc: lối ra phải là bỏ đúng cái drill đó (02 §14.4 dòng 12). -->
        <button v-if="drillWindow" class="btn-secondary text-sm" @click="clearDrill">Bỏ lọc thời hạn</button>
        <button v-else-if="activeFilterCount > 0" class="text-xs text-brand-600 hover:text-brand-700 font-medium underline" @click="resetFilters">
          Xóa bộ lọc để xem tất cả
        </button>
        <button v-else-if="canCreateSession" class="btn-primary" @click="router.push('/imm06/sessions/new')">Tạo buổi đào tạo</button>
      </template>

      <template #toolbar>
      <div class="flex items-center justify-between px-4 py-2.5 border-b border-slate-100 bg-slate-50/60 text-xs text-slate-500">
        <span>Hiển thị <strong class="text-slate-700">{{ competencies?.length ?? 0 }}</strong> / {{ competencyPagination.total }} bản ghi</span>
        <button v-if="activeFilterCount > 0" class="text-red-500 hover:text-red-700 font-medium" @click="resetFilters">Xóa tất cả</button>
      </div>

      </template>

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
              <StatusBadge :state="competencyEffectiveState(c.workflow_state, c.days_until_expiry)" />
            </div>
            <p class="text-sm font-medium text-slate-900 truncate">{{ c.user_full_name ?? c.user }}</p>
            <div class="flex flex-wrap gap-x-2 gap-y-1 mt-1.5 text-xs text-slate-500">
              <span :title="c.device_model">{{ c.device_model_name ?? c.device_model }}</span>
              <span>· <span class="px-1.5 py-0.5 rounded bg-blue-50 text-blue-700">{{ levelLabel(c.competency_level) }}</span></span>
              <span :class="expiryClass(c.days_until_expiry)">· {{ formatDaysUntilExpiry(c.days_until_expiry) }}</span>
            </div>
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
                  <StatusBadge :state="competencyEffectiveState(c.workflow_state, c.days_until_expiry)" />
                </td>
              </tr>
            </tbody>
          </table>
        </div>

      <template #pagination>
        <BasePagination :pagination="competencyPagination" @page-change="load" />
      </template>
    </ListPageShell>
  </div>
</template>
