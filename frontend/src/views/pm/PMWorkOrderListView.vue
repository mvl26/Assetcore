<script setup lang="ts">
import DateInput from '@/components/common/DateInput.vue'
import { onMounted, ref, computed, watch } from 'vue'
import { useImm08Store } from '@/stores/imm08'
import { useRouter, useRoute } from 'vue-router'
import { formatAssetDisplay, translateStatus, getStatusColor, formatDate } from '@/utils/formatters'
import PageHeader from '@/components/common/PageHeader.vue'
import FilterToggleButton from '@/components/common/FilterToggleButton.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'
import BasePagination from '@/components/common/BasePagination.vue'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
import WorkOrderKpiStrip, { type WoKpiItem } from '@/components/common/WorkOrderKpiStrip.vue'
import ListPageShell from '@/components/ui/ListPageShell.vue'
import { useCapabilities } from '@/composables/useCapabilities'
import { pmTypeLabel } from '@/constants/labels'

const store = useImm08Store()
const router = useRouter()
const route = useRoute()
// Read-only oversight (opsmgr): chỉ user có pm.create mới thấy nút Tạo phiếu.
const { can } = useCapabilities()
// Core Doc §9.3 — pre-apply filter từ route.query (drill-down từ dashboard).
const statusFilter = ref<string>((route.query.status as string) || '')
const search = ref('')
const dateFrom = ref('')
const dateTo = ref('')
const assetFilter = ref<string>((route.query.asset as string) || '')
// R6 §9.4.3 — date-window drill từ KPI pm_due_7d (?due_before) / overdue (?overdue=1).
const dueBefore = ref<string>((route.query.due_before as string) || '')
const overdueOnly = ref<boolean>(route.query.overdue === '1')
const showFilters = ref<boolean>(!!(route.query.status || route.query.asset || route.query.due_before || route.query.overdue))

// Nhãn cửa-sổ due-soon (IMM-08 SoT round): KPI pm_due_7d == drill ?due_before=today+7,
// cận dưới = HÔM NAY do BE (_normalize_filters → due_date BETWEEN [today, X]). Chip chỉ
// đổi NHÃN cho khớp ngữ nghĩa cửa-sổ — KHÔNG inline-compute membership (vẫn forward
// due_before verbatim). PM quá hạn (due_date < today) thuộc thẻ "PM quá hạn", disjoint.
function _today(): string {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}
function _addDays(iso: string, days: number): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  d.setDate(d.getDate() + days)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}
// dueBefore == today+7 → nhãn ngắn "Đến hạn trong 7 ngày"; ngược lại nêu rõ cận dưới.
const dueSoonLabel = computed<string>(() =>
  dueBefore.value === _addDays(_today(), 7)
    ? 'Đến hạn trong 7 ngày'
    : `Đến hạn ≤ ${formatDate(dueBefore.value)}, từ hôm nay`
)

const PM_STATUSES = [
  { value: 'Open',                label: 'Mở' },
  { value: 'In Progress',         label: 'Đang thực hiện' },
  { value: 'Overdue',             label: 'Quá hạn' },
  { value: 'Completed',           label: 'Hoàn thành' },
  { value: 'Halted–Major Failure',label: 'Dừng — Lỗi nặng' },
  { value: 'Pending–Device Busy', label: 'Chờ — Thiết bị bận' },
  { value: 'Cancelled',           label: 'Đã hủy' },
]

function buildFilters() {
  const f: Record<string, unknown> = {}
  // R6: overdue/due_before là virtual key — BE imm08._normalize_filters dịch sang
  // status=Overdue / due_date BETWEEN [today, X] (due_soon_filter, cận dưới = hôm
  // nay để WO quá hạn KHÔNG leak vào drill — SSOT, list khớp KPI). overdue thắng
  // due_before.
  if (overdueOnly.value) f.overdue = '1'
  else if (dueBefore.value) f.due_before = dueBefore.value
  if (statusFilter.value && !overdueOnly.value) f.status = [statusFilter.value]
  // AC-CR-79 — SỬA BUG THẬT: 2 khoá `due_date_from`/`due_date_to` là do FE tự bịa,
  // BE CHƯA TỪNG có (không phải cột `PM Work Order`, không được `_normalize_filters`
  // dịch) ⇒ rơi thẳng xuống SQL: `Unknown column 'tabPM Work Order.due_date_from'`
  // = HTTP-500. Nghĩa là bộ lọc "Từ ngày / Đến ngày" của màn này CHƯA BAO GIỜ chạy.
  // Dạng ĐÚNG (ADR-IMM08-FILTERKEY-03): cột THẬT `due_date` + toán tử Frappe —
  // `_normalize_filters` giữ nguyên cặp [op, value] khi op ∈ _OP_TOKENS.
  // KHÔNG gửi kèm `due_before`: nhánh due_before của BE GHI ĐÈ `due_date` ⇒ khoảng
  // ngày sẽ bị nuốt IM LẶNG. Với `overdue` thì an toàn (BE chỉ set `status`).
  const sendingDueBefore = !overdueOnly.value && !!dueBefore.value
  if (!sendingDueBefore) {
    if (dateFrom.value && dateTo.value) f.due_date = ['between', [dateFrom.value, dateTo.value]]
    else if (dateFrom.value) f.due_date = ['>=', dateFrom.value]
    else if (dateTo.value) f.due_date = ['<=', dateTo.value]
  }
  if (assetFilter.value) f.asset_ref = assetFilter.value
  return f
}

// CR-18: refetch SERVER với column-filters + free-text `search` (mã phiếu / mã
// thiết bị / tên thiết bị). Search phủ TOÀN tập mọi trang — KHÔNG lọc client-side
// page-limited. `search` là param độc lập AND cùng các filter khác (status/asset/
// overdue). Gửi undefined khi rỗng ⇒ baseline byte-identical (BE bỏ qua).
// ── Trạng thái nạp danh sách (AC-UX-047 lô 3 · biến thể D — 02 §14.2, khuôn §13.2) ─────────
// `stores/imm08.ts:205 fetchDashboardStats` ghi vào CÙNG ô `error` VÀ CÙNG cờ `loading` với
// lượt nạp danh sách. Bind thẳng `store.error`/`store.loading` ⇒ một lượt nạp thẻ chỉ số hỏng
// sẽ xoá trắng bảng đang xem, và cờ `loading` của nó làm bảng nháy về khung xương
// (INV-UX3-28). Vì vậy view sở hữu cờ + ô lỗi RIÊNG cho lượt nạp danh sách và CHỤP lỗi ngay
// sau `await` rồi trả ô dùng chung về sạch. `store.filterError` KHÔNG vào đây — đó là CẢNH
// BÁO bộ lọc, bảng vẫn giữ dữ liệu (INV-UX3-13).
const listLoading = ref(false)
const loadError = ref<string | null>(null)
const currentPage = ref(1)

async function reload(page = 1) {
  currentPage.value = page
  listLoading.value = true
  loadError.value = null
  store.error = null
  await store.fetchWorkOrders(buildFilters(), page, search.value.trim() || undefined)
  loadError.value = store.error ?? null
  if (loadError.value) store.error = null
  listLoading.value = false
}

/** Điểm vào DUY NHẤT của «Thử lại» — giữ nguyên bộ lọc VÀ trang đang xem. */
function retryLoad() { return reload(currentPage.value) }

// Chữ trạng thái rỗng — SSoT là bảng copy 02 §14.4 (LL-FE-53: 100% tiếng Việt).
const emptyTitle = computed(() =>
  activeFilterCount.value > 0
    ? 'Không tìm thấy phiếu bảo trì định kỳ nào phù hợp'
    : 'Chưa có phiếu bảo trì định kỳ nào',
)
const emptyHint =
  'Phiếu bảo trì định kỳ được sinh từ lịch bảo trì hoặc tạo thủ công cho một thiết bị.'

onMounted(async () => {
  // TUẦN TỰ (02 §14.4): danh sách trước, thẻ chỉ số sau — chạy song song thì cờ `loading`
  // dùng chung của lượt nạp chỉ số làm nháy trạng thái danh sách.
  await reload()
  store.fetchDashboardStats()
})

// KPI strip (docs/fe/08-pm/pm-list.html) — nguồn: dashboard stats thật từ BE.
// ĐỒNG NHẤT PHẠM VI (INV-PM-KPI-1/5): strip này gắn với 'Tổng lịch tháng' (phạm
// vi tháng) → 'Quá hạn' phải dùng overdue_in_month (CÙNG phạm vi, đối-soát được),
// KHÔNG overdue global. Tile 'Quá hạn (toàn hệ thống)' tách riêng, nhãn rõ ràng,
// khớp số PMDashboardView (cùng endpoint get_pm_dashboard_stats).
const kpiItems = computed<WoKpiItem[]>(() => {
  const s = store.dashboardStats?.kpis
  if (!s) return []
  const compliance = s.compliance_rate_pct == null ? '—' : `${s.compliance_rate_pct}%`
  return [
    { label: 'Tổng lịch tháng', value: s.total_scheduled, color: 'primary' },
    { label: 'Quá hạn trong tháng', value: s.overdue_in_month, color: 'warning', trend: s.overdue_in_month > 0 ? 'Cần xử lý' : 'Đúng tiến độ' },
    { label: 'Quá hạn (toàn hệ thống)', value: s.overdue, color: 'danger', trend: s.overdue > 0 ? 'Cần escalate' : 'Đúng tiến độ' },
    { label: 'Hoàn tất đúng hạn', value: s.completed_on_time, color: 'success', trend: `Tuân thủ ${compliance}` },
    { label: 'Trễ trung bình', value: `${s.avg_days_late} ngày`, color: 'warning' },
  ]
})

watch([statusFilter, dateFrom, dateTo, assetFilter, dueBefore, overdueOnly], () => {
  reload(1)
})

// Sync when navigating from AssetDetail / dashboard drill-down (§9.3)
watch(() => route.query.asset, (val) => {
  assetFilter.value = (val as string) || ''
})
watch(() => route.query.status, (val) => {
  statusFilter.value = (val as string) || ''
})
watch(() => route.query.due_before, (val) => {
  dueBefore.value = (val as string) || ''
})
watch(() => route.query.overdue, (val) => {
  overdueOnly.value = val === '1'
})

interface PMChip { key: 'status' | 'dateFrom' | 'dateTo' | 'asset' | 'search' | 'overdue' | 'dueBefore'; label: string }
const activeChips = computed<PMChip[]>(() => {
  const chips: PMChip[] = []
  if (overdueOnly.value) chips.push({ key: 'overdue', label: 'Quá hạn' })
  else if (dueBefore.value) chips.push({ key: 'dueBefore', label: dueSoonLabel.value })
  if (statusFilter.value && !overdueOnly.value) {
    const s = PM_STATUSES.find(x => x.value === statusFilter.value)
    chips.push({ key: 'status', label: s?.label ?? statusFilter.value })
  }
  if (dateFrom.value) chips.push({ key: 'dateFrom', label: `Từ ${dateFrom.value}` })
  if (dateTo.value) chips.push({ key: 'dateTo', label: `Đến ${dateTo.value}` })
  if (assetFilter.value) chips.push({ key: 'asset', label: `Thiết bị: ${assetFilter.value}` })
  if (search.value.trim()) chips.push({ key: 'search', label: `"${search.value.trim()}"` })
  return chips
})
const activeFilterCount = computed(() => activeChips.value.length)

function clearChip(key: string) {
  if (key === 'status') statusFilter.value = ''
  else if (key === 'dateFrom') dateFrom.value = ''
  else if (key === 'dateTo') dateTo.value = ''
  else if (key === 'asset') assetFilter.value = ''
  else if (key === 'overdue') overdueOnly.value = false
  else if (key === 'dueBefore') dueBefore.value = ''
  else if (key === 'search') { search.value = ''; reload(1) }  // search KHÔNG có watch → reload thủ công
}

function resetFilters() {
  statusFilter.value = ''
  dateFrom.value = ''
  dateTo.value = ''
  assetFilter.value = ''
  dueBefore.value = ''
  overdueOnly.value = false
  search.value = ''
  reload(1)
}

// ListFilterBar phát `@apply` sau debounce khi user gõ ô tìm → refetch server + reset trang 1.
function applyFilters() {
  reload(1)
}

function quickFilter(_key: 'status', value: string) {
  if (!value) return
  statusFilter.value = value
  showFilters.value = false
}
</script>

<template>
  <div>
    <ListPageShell
      :loading="listLoading"
      :error-message="loadError"
      :is-empty="!store.workOrders.length"
      :empty-title="emptyTitle"
      :empty-hint="emptyHint"
      @retry="retryLoad">
      <template #header>
    <!-- INV-ROWSCOPE / A5 (đối xứng CM): "Tổng" LUÔN từ pagination.total (SoT
         permission-aware của BE). Fallback cũ `?? store.workOrders.length` che giấu
         drift count-vs-rows (đếm N nhưng chỉ đọc được M) ⇒ bỏ, chỉ còn `?? 0`.
         "Hiển thị X" bên dưới vẫn là số dòng TRANG hiện tại (.length). -->
    <PageHeader
      title="Phiếu Bảo trì định kỳ"
      :subtitle="`Tổng ${store.pagination.total ?? 0} phiếu`"
      :breadcrumb="[{ label: 'IMM-08 · Bảo trì', to: '/pm/dashboard' }, { label: 'Danh sách' }]"
    >
      <template #actions>
        <FilterToggleButton v-model="showFilters" :count="activeFilterCount" />
        <button v-if="can('pm.create')" class="btn-primary" @click="router.push('/pm/work-orders/new')">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          Tạo phiếu bảo trì
        </button>
      </template>
    </PageHeader>
      </template>

      <!-- Dải chỉ số — `#summary` CHỈ render ở trạng thái rỗng/có-dữ-liệu ⇒ hết cảnh in
           `0`/«Đúng tiến độ» khi lượt nạp danh sách hỏng (INV-UX3-27). -->
      <template #summary><WorkOrderKpiStrip :items="kpiItems" /></template>

      <template #filters>
    <!-- Hint cửa-sổ due-soon: khớp invariant disjoint (drill == KPI pm_due_7d).
         PM quá hạn KHÔNG nằm trong danh sách này — xem thẻ "PM quá hạn". -->
    <div
      v-if="dueBefore && !overdueOnly"
      class="flex items-start gap-2 rounded-lg bg-amber-50 border border-amber-200 px-3 py-2 text-xs text-amber-800"
    >
      <svg class="w-4 h-4 shrink-0 mt-0.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <span>Danh sách phiếu đến hạn trong 7 ngày tới (tính từ hôm nay) — không gồm bảo trì định kỳ quá hạn (xem thẻ "Bảo trì định kỳ quá hạn").</span>
    </div>

    <ListFilterBar
      :show="showFilters"
      :chips="activeChips"
      v-model:search="search"
      search-placeholder="Tìm theo mã lệnh công việc, tên thiết bị..."
      @reset="resetFilters"
      @clear-chip="clearChip"
      @apply="applyFilters"
    >
      <template #fields>
        <div class="form-group">
          <label class="form-label">Trạng thái</label>
          <select v-model="statusFilter" class="form-select">
            <option value="">Tất cả</option>
            <option v-for="s in PM_STATUSES" :key="s.value" :value="s.value">{{ s.label }}</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Từ ngày</label>
          <DateInput v-model="dateFrom" class="form-input" />
        </div>
        <div class="form-group">
          <label class="form-label">Đến ngày</label>
          <DateInput v-model="dateTo" class="form-input" />
        </div>
        <div class="form-group">
          <label class="form-label">Thiết bị</label>
          <input v-model="assetFilter" placeholder="Mã AC Asset..." class="form-input" />
        </div>
      </template>
    </ListFilterBar>

    <!-- AC-CR-79 — Bộ lọc không hợp lệ: BE từ chối khoá lọc lạ bằng lỗi 400 TRONG
         envelope (HTTP-200). Đây là CẢNH BÁO, không phải sự cố nạp dữ liệu ⇒ bảng
         bên dưới GIỮ NGUYÊN dữ liệu đang xem (không trắng trang, không đăng xuất).
         Nội dung hiển thị là message tiếng Việt do BE trả về — FE KHÔNG dựng lại
         danh sách khoá hợp lệ (SSoT nằm ở services/imm08.py). -->
    <div
      v-if="store.filterError"
      class="alert-warning"
      role="alert"
      data-test="pm-filter-error"
    >
      <svg class="w-4 h-4 shrink-0" aria-hidden="true" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
      </svg>
      <span class="flex-1">{{ store.filterError }}</span>
      <button
        type="button"
        class="text-xs font-semibold underline hover:no-underline rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-500"
        @click="resetFilters"
      >
        Đặt lại bộ lọc
      </button>
    </div>
      </template>

      <template #skeleton><SkeletonLoader variant="table" :rows="6" /></template>

      <template #empty-action>
        <button
          v-if="activeFilterCount > 0"
          class="text-xs text-brand-600 hover:text-brand-700 font-medium underline"
          @click="resetFilters"
        >Xóa bộ lọc để xem tất cả</button>
        <button
          v-else-if="can('pm.create')"
          class="btn-primary"
          @click="router.push('/pm/work-orders/new')"
        >Tạo phiếu bảo trì định kỳ</button>
      </template>

      <template #toolbar>
        <div class="flex items-center justify-between px-4 py-2.5 border-b border-slate-100 bg-slate-50/60 text-xs text-slate-500">
          <span>Hiển thị <strong class="text-slate-700">{{ store.workOrders.length }}</strong> / {{ store.pagination.total ?? 0 }} phiếu</span>
          <button v-if="activeFilterCount > 0" class="text-red-500 hover:text-red-700 font-medium" @click="resetFilters">Xóa tất cả</button>
        </div>
      </template>

      <!-- Mobile cards (< sm) -->
      <div class="mobile-card-list sm:hidden">
        <div
          v-for="wo in store.workOrders"
          :key="wo.name"
          class="mobile-card"
          @click="router.push(`/pm/work-orders/${wo.name}`)"
        >
          <div class="flex items-center justify-between mb-2">
            <span class="font-mono text-sm font-semibold text-brand-700">{{ wo.name }}</span>
            <button
              :class="['px-2.5 py-0.5 rounded-full text-xs font-medium', getStatusColor(wo.status)]"
              @click.stop="quickFilter('status', wo.status)"
            >{{ translateStatus(wo.status) }}</button>
          </div>
          <p class="text-sm font-medium text-slate-900 truncate">{{ formatAssetDisplay(wo.asset_name, wo.asset_ref).main }}</p>
          <div class="flex flex-wrap items-center gap-x-2 gap-y-1 mt-1.5 text-xs text-slate-500">
            <span v-if="wo.pm_type">{{ pmTypeLabel(wo.pm_type) }}</span>
            <span class="text-slate-300">·</span>
            <span :class="wo.is_late ? 'text-red-600 font-semibold' : ''">{{ wo.due_date || '—' }}</span>
            <span v-if="wo.is_late" class="text-red-500">Quá hạn</span>
          </div>
        </div>
      </div>

      <!-- Desktop table (sm+) -->
      <div class="hidden sm:block table-wrapper">
        <table class="min-w-full divide-y divide-slate-100">
          <thead>
            <tr>
              <th class="table-header">Mã lệnh công việc</th>
              <th class="table-header">Thiết bị</th>
              <th class="table-header">Loại bảo trì định kỳ</th>
              <th class="table-header">Đến hạn</th>
              <th class="table-header">Kỹ thuật viên</th>
              <th class="table-header">Trạng thái</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-50">
            <tr
              v-for="wo in store.workOrders"
              :key="wo.name"
              class="hover:bg-slate-50 cursor-pointer transition-all hover:translate-x-0.5"
              @click="router.push(`/pm/work-orders/${wo.name}`)"
            >
              <td class="table-cell">
                <div class="font-mono text-sm font-semibold text-brand-700">{{ wo.name }}</div>
              </td>
              <td class="table-cell">
                <div class="font-medium text-slate-900 truncate max-w-[240px]">
                  {{ formatAssetDisplay(wo.asset_name, wo.asset_ref).main }}
                </div>
                <div
                  v-if="formatAssetDisplay(wo.asset_name, wo.asset_ref).hasBoth"
                  class="text-xs text-slate-400 font-mono mt-0.5">
                  {{ formatAssetDisplay(wo.asset_name, wo.asset_ref).sub }}
                </div>
              </td>
              <td class="table-cell text-slate-600">{{ pmTypeLabel(wo.pm_type) }}</td>
              <td class="table-cell">
                <span :class="wo.is_late ? 'text-red-600 font-semibold' : 'text-slate-600'">
                  {{ wo.due_date || '—' }}
                </span>
                <div v-if="wo.is_late" class="text-xs text-red-500 mt-0.5">Quá hạn</div>
              </td>
              <td class="table-cell">
                <div class="text-slate-700">{{ wo.assigned_to_name || wo.assigned_to || '—' }}</div>
                <div v-if="wo.assigned_to && wo.assigned_to_name" class="text-xs text-slate-400">{{ wo.assigned_to }}</div>
              </td>
              <td class="table-cell">
                <button
                  :class="['inline-block px-2.5 py-1 rounded-full text-xs font-medium transition-all hover:ring-2 hover:ring-offset-1 hover:ring-current/50', getStatusColor(wo.status)]"
                  :title="`Lọc: ${translateStatus(wo.status)}`"
                  @click.stop="quickFilter('status', wo.status)"
                >{{ translateStatus(wo.status) }}</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <template #pagination>
        <BasePagination :pagination="store.pagination" @page-change="p => reload(p)" />
      </template>
    </ListPageShell>
  </div>
</template>

<style scoped>
/* Fade transition for table rows on filter change */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
