<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useCapabilities } from '@/composables/useCapabilities'
import { useImm11Store } from '@/stores/imm11'
import { formatAssetDisplay, formatDate } from '@/utils/formatters'
import { calFlagBadge } from '@/utils/calibrationStatus'
import PageHeader from '@/components/common/PageHeader.vue'
import FilterToggleButton from '@/components/common/FilterToggleButton.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'
import BasePagination from '@/components/common/BasePagination.vue'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import ListPageShell from '@/components/ui/ListPageShell.vue'

const router = useRouter()
const { can } = useCapabilities()
const route = useRoute()
const store = useImm11Store()

const items = computed(() => store.calibrations)
// Mỗi phiếu augment sẵn badge hạn TỪ CỜ SERVER (is_overdue/is_due_soon) — server-flag
// SSoT: derive 1 lần/hàng qua calFlagBadge, KHÔNG so next_calibration_date client-clock.
const rows = computed(() =>
  items.value.map((c) => ({ ...c, dueFlag: calFlagBadge(c.is_overdue, c.is_due_soon) })),
)
const pagination = computed(() => store.pagination)
const kpis = computed(() => store.kpis?.kpis ?? null)
const loading = computed(() => store.loading)
// Core Doc §9.3 — pre-apply filter từ route.query (drill-down từ dashboard).
const filterStatus = ref<string>((route.query.status as string) || '')
const filterType = ref('')
const filterResult = ref<string>((route.query.result as string) || '')
const assetFilter = ref<string>((route.query.asset as string) || '')
const showFilters = ref<boolean>(!!(route.query.status || route.query.result || route.query.asset))

const CAL_TYPES = [
  { value: 'External', label: 'Bên ngoài (ISO 17025)' },
  { value: 'In-House', label: 'Nội bộ' },
]
const CAL_TYPE_LABEL: Record<string, string> = { External: 'Bên ngoài', 'In-House': 'Nội bộ' }
function calTypeLabel(t?: string) { return CAL_TYPE_LABEL[t ?? ''] ?? (t || '—') }
const CAL_RESULTS = [
  { value: 'Passed', label: 'Đạt' },
  { value: 'Conditionally Passed', label: 'Đạt có điều kiện' },
  { value: 'Failed', label: 'Không đạt' },
]

const CAL_STATUSES = [
  { value: 'Scheduled',            label: 'Đã lên lịch' },
  { value: 'Sent to Lab',          label: 'Đã gửi phòng hiệu chuẩn' },
  { value: 'In Progress',          label: 'Đang thực hiện' },
  { value: 'Certificate Received', label: 'Đã nhận chứng nhận' },
  { value: 'Passed',               label: 'Đạt' },
  { value: 'Failed',               label: 'Không đạt' },
  { value: 'Conditionally Passed', label: 'Đạt có điều kiện' },
  { value: 'Cancelled',            label: 'Đã hủy' },
]

interface Chip { key: 'status' | 'asset' | 'type' | 'result'; label: string }
const activeChips = computed<Chip[]>(() => {
  const chips: Chip[] = []
  if (filterStatus.value) {
    const s = CAL_STATUSES.find(x => x.value === filterStatus.value)
    chips.push({ key: 'status', label: s?.label ?? filterStatus.value })
  }
  if (filterType.value) {
    const t = CAL_TYPES.find(x => x.value === filterType.value)
    chips.push({ key: 'type', label: t?.label ?? filterType.value })
  }
  if (filterResult.value) {
    const r = CAL_RESULTS.find(x => x.value === filterResult.value)
    chips.push({ key: 'result', label: r?.label ?? filterResult.value })
  }
  if (assetFilter.value) chips.push({ key: 'asset', label: `Thiết bị: ${assetFilter.value}` })
  return chips
})
const activeFilterCount = computed(() => activeChips.value.length)

function clearChip(key: string) {
  if (key === 'status') filterStatus.value = ''
  else if (key === 'type') filterType.value = ''
  else if (key === 'result') filterResult.value = ''
  else assetFilter.value = ''
  load(1)
}

function resetFilters() {
  filterStatus.value = ''
  filterType.value = ''
  filterResult.value = ''
  assetFilter.value = ''
  load(1)
}

function quickFilter(_key: 'status', value: string) {
  if (!value) return
  filterStatus.value = value
  showFilters.value = false
  load(1)
}

// ── Trạng thái nạp danh sách (AC-UX-047 lô 2 · biến thể D — 02 §13.2) ──
// `stores/imm11.ts` dùng CHUNG một ô `error` (`_captureError`) cho MỌI lời gọi — danh
// sách, chỉ-số, lịch, transition ⇒ bind thẳng thì một lần nạp chỉ-số hỏng sẽ xoá trắng
// danh sách. Phải CHỤP lỗi ngay sau `await` của lượt nạp DANH SÁCH rồi trả ô về sạch.
const loadError = ref<string | null>(null)
const currentPage = ref(1)

async function load(page = 1) {
  currentPage.value = page
  loadError.value = null
  store.error = null
  await store.fetchList({
    page, page_size: 20,
    status: filterStatus.value || undefined,
    asset: assetFilter.value || undefined,
    calibration_type: filterType.value || undefined,
    overall_result: filterResult.value || undefined,
  })
  loadError.value = store.error ?? null
  if (loadError.value) store.error = null
}

/** Điểm vào DUY NHẤT của «Thử lại» — giữ nguyên bộ lọc + trang hiện tại. */
function reload() { return load(currentPage.value) }

async function loadKpis() {
  await store.fetchKpis()
  // chỉ-số dùng CHUNG ô lỗi với danh sách ⇒ dọn để không rò sang lượt nạp sau
  store.error = null
}

const emptyTitle = computed(() =>
  activeFilterCount.value > 0 ? 'Không có phiếu hiệu chuẩn nào phù hợp' : 'Chưa có phiếu hiệu chuẩn nào',
)
const emptyHint = 'Hãy tạo phiếu hiệu chuẩn mới hoặc xoá bộ lọc để xem tất cả.'

watch(() => route.query.asset, (val) => {
  assetFilter.value = (val as string) || ''
  load(1)
})
// §9.3 — drill-down lần 2 từ dashboard (status/result) → re-apply.
watch(() => route.query.status, (val) => { filterStatus.value = (val as string) || ''; load(1) })
watch(() => route.query.result, (val) => { filterResult.value = (val as string) || ''; load(1) })

// TUẦN TỰ, không `Promise.all`: lỗi của `loadKpis` không được cướp trạng thái danh sách.
onMounted(async () => { await load(); loadKpis() })
</script>

<template>
  <div>
    <ListPageShell
      :loading="loading"
      :error-message="loadError"
      :is-empty="!items.length"
      :empty-title="emptyTitle"
      :empty-hint="emptyHint"
      @retry="reload">
      <template #header>
    <PageHeader
      title="Hiệu chuẩn thiết bị"
      :subtitle="`Tổng ${pagination.total ?? items.length} phiếu`"
      :breadcrumb="[{ label: 'IMM-11 · Hiệu chuẩn', to: '/calibration/dashboard' }, { label: 'Danh sách' }]"
    >
      <template #actions>
        <FilterToggleButton v-model="showFilters" :count="activeFilterCount" />
        <button class="btn-ghost text-sm" @click="router.push('/calibration/schedules')">Lịch hiệu chuẩn</button>
        <button v-if="can('calibration.create')" class="btn-primary" @click="router.push('/calibration/new')">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          Tạo phiếu
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
          <select v-model="filterStatus" class="form-select" @change="load(1)">
            <option value="">Tất cả trạng thái</option>
            <option v-for="s in CAL_STATUSES" :key="s.value" :value="s.value">{{ s.label }}</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Loại</label>
          <select v-model="filterType" class="form-select" @change="load(1)">
            <option value="">Mọi loại</option>
            <option v-for="t in CAL_TYPES" :key="t.value" :value="t.value">{{ t.label }}</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Kết quả</label>
          <select v-model="filterResult" class="form-select" @change="load(1)">
            <option value="">Mọi kết quả</option>
            <option v-for="r in CAL_RESULTS" :key="r.value" :value="r.value">{{ r.label }}</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Thiết bị</label>
          <input v-model="assetFilter" placeholder="Mã AC Asset..." class="form-input" @keyup.enter="load(1)" />
        </div>
      </template>
    </ListFilterBar>
      </template>

      <template #skeleton><SkeletonLoader variant="table" :rows="6" /></template>

      <template #empty-action>
        <button v-if="activeFilterCount > 0" class="text-xs text-brand-600 hover:text-brand-700 font-medium underline" @click="resetFilters">
          Xóa bộ lọc để xem tất cả
        </button>
      </template>

      <!-- Dải chỉ số chỉ render ở trạng thái rỗng/có-dữ-liệu ⇒ hết cảnh in `0` khi API hỏng -->
      <template #summary>
    <div v-if="kpis" class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
      <div class="kpi-card p-4 text-center" style="--kpi-color: #334155">
        <p class="text-xs text-slate-400 mb-1">Tháng này</p>
        <p class="text-2xl font-bold font-display tabular-nums text-slate-700">{{ kpis.total_this_month }}</p>
      </div>
      <div class="kpi-card p-4 text-center" style="--kpi-color: #059669">
        <p class="text-xs text-slate-400 mb-1">Đã qua</p>
        <p class="text-2xl font-bold font-display tabular-nums text-emerald-600">{{ kpis.completed }}</p>
      </div>
      <div class="kpi-card p-4 text-center" style="--kpi-color: #dc2626">
        <p class="text-xs text-slate-400 mb-1">Thất bại</p>
        <p class="text-2xl font-bold font-display tabular-nums text-red-600">{{ kpis.failed }}</p>
      </div>
      <div class="kpi-card p-4 text-center" style="--kpi-color: #2563eb">
        <p class="text-xs text-slate-400 mb-1">Tỷ lệ đạt</p>
        <p class="text-2xl font-bold font-display tabular-nums text-brand-600">{{ kpis.pass_rate_pct }}%</p>
      </div>
      <div class="kpi-card p-4 text-center" style="--kpi-color: #dc2626">
        <p class="text-xs text-slate-400 mb-1">Quá hạn</p>
        <p class="text-2xl font-bold font-display tabular-nums text-red-500">{{ kpis.overdue_assets }}</p>
      </div>
      <div class="kpi-card p-4 text-center" style="--kpi-color: #d97706">
        <p class="text-xs text-slate-400 mb-1">Sắp đến hạn</p>
        <p class="text-2xl font-bold font-display tabular-nums text-amber-600">{{ kpis.due_soon_assets }}</p>
      </div>
    </div>
      </template>

      <template #toolbar>
      <div class="flex items-center justify-between px-4 py-2.5 border-b border-slate-100 bg-slate-50/60 text-xs text-slate-500">
        <span>Hiển thị <strong class="text-slate-700">{{ items.length }}</strong> / {{ pagination.total }} phiếu</span>
        <button v-if="activeFilterCount > 0" class="text-red-500 hover:text-red-700 font-medium" @click="resetFilters">Xóa tất cả</button>
      </div>
      </template>

        <!-- Mobile cards (< sm) -->
        <div class="mobile-card-list sm:hidden">
          <div
            v-for="c in rows"
            :key="c.name"
            class="mobile-card"
            @click="router.push(`/calibration/${c.name}`)"
          >
            <div class="flex items-center justify-between mb-2">
              <span class="font-mono text-sm font-semibold text-brand-700">{{ c.name }}</span>
              <div class="flex items-center gap-1.5">
                <span
                  v-if="c.dueFlag"
                  class="inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-medium leading-none"
                  :class="c.dueFlag.badgeClass"
                >{{ c.dueFlag.label }}</span>
                <button @click.stop="quickFilter('status', c.status)">
                  <StatusBadge :state="c.status" />
                </button>
              </div>
            </div>
            <p class="text-sm font-medium text-slate-900 truncate">{{ formatAssetDisplay(c.asset_name, c.asset).main }}</p>
            <div class="flex flex-wrap items-center gap-x-2 gap-y-1 mt-1.5 text-xs text-slate-500">
              <span>{{ calTypeLabel(c.calibration_type) }}</span>
              <span class="text-slate-300">·</span>
              <span>{{ formatDate(c.scheduled_date) }}</span>
              <span v-if="c.next_calibration_date" class="text-slate-300">·</span>
              <span v-if="c.next_calibration_date" :class="c.dueFlag?.textClass ?? 'text-slate-500'">
                Cal tiếp: {{ formatDate(c.next_calibration_date) }}
              </span>
              <span v-if="c.overall_result" class="text-slate-300">·</span>
              <StatusBadge v-if="c.overall_result" :state="c.overall_result" />
            </div>
          </div>
        </div>

        <!-- Desktop table (sm+) -->
        <div class="hidden sm:block overflow-x-auto">
          <table class="min-w-full divide-y divide-slate-100">
            <thead>
              <tr>
                <th class="table-header">Mã</th>
                <th class="table-header">Thiết bị</th>
                <th class="table-header">Loại</th>
                <th class="table-header">Trạng thái</th>
                <th class="table-header">Ngày dự kiến</th>
                <th class="table-header">Kết quả</th>
                <th class="table-header">Ngày hiệu chuẩn tiếp theo</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              <tr
                v-for="c in rows" :key="c.name"
                class="hover:bg-slate-50 cursor-pointer transition-colors"
                @click="router.push(`/calibration/${c.name}`)"
              >
                <td class="table-cell font-mono text-xs text-slate-500">{{ c.name }}</td>
                <td class="table-cell">
                  <div class="font-medium text-slate-900 truncate max-w-[240px]">
                    {{ formatAssetDisplay(c.asset_name, c.asset).main }}
                  </div>
                  <div v-if="formatAssetDisplay(c.asset_name, c.asset).hasBoth" class="text-xs text-slate-400 font-mono mt-0.5">
                    {{ formatAssetDisplay(c.asset_name, c.asset).sub }}
                  </div>
                </td>
                <td class="table-cell text-slate-600">{{ calTypeLabel(c.calibration_type) }}</td>
                <td class="table-cell">
                  <button @click.stop="quickFilter('status', c.status)">
                    <StatusBadge :state="c.status" />
                  </button>
                </td>
                <td class="table-cell text-slate-600">{{ formatDate(c.scheduled_date) }}</td>
                <td class="table-cell">
                  <StatusBadge v-if="c.overall_result" :state="c.overall_result" />
                  <span v-else class="text-slate-300">—</span>
                </td>
                <td class="table-cell text-xs">
                  <div class="flex items-center gap-1.5">
                    <span :class="c.dueFlag?.textClass ?? 'text-slate-500'">
                      {{ formatDate(c.next_calibration_date) }}
                    </span>
                    <span
                      v-if="c.dueFlag"
                      class="inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-medium leading-none"
                      :class="c.dueFlag.badgeClass"
                    >{{ c.dueFlag.label }}</span>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

      <template #pagination>
        <BasePagination :pagination="pagination" @page-change="load" />
      </template>
    </ListPageShell>
  </div>
</template>
