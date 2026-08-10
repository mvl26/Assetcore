<script setup lang="ts">
import { onMounted, ref, computed, watch } from 'vue'
import { useImm09Store } from '@/stores/imm09'
import { useRouter, useRoute } from 'vue-router'
import { priorityLabel, priorityClass, repairTypeLabel, REPAIR_PRIORITY_OPTIONS } from '@/constants/labels'
import { translateStatus, getStatusColor, formatDateTime } from '@/utils/formatters'
import PageHeader from '@/components/common/PageHeader.vue'
import FilterToggleButton from '@/components/common/FilterToggleButton.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'
import BasePagination from '@/components/common/BasePagination.vue'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
import WorkOrderKpiStrip, { type WoKpiItem } from '@/components/common/WorkOrderKpiStrip.vue'
import ListPageShell from '@/components/ui/ListPageShell.vue'
import { useCapabilities } from '@/composables/useCapabilities'

const store = useImm09Store()
const router = useRouter()
const route = useRoute()
// Read-only oversight (opsmgr): chỉ user có repair.create mới thấy nút Tạo lệnh.
const { can } = useCapabilities()
// Core Doc §9.3 — pre-apply filter từ route.query (drill-down từ dashboard).
const statusFilter = ref<string>((route.query.status as string) || '')
const priorityFilter = ref<string>((route.query.priority as string) || '')
const assetFilter = ref<string>((route.query.asset as string) || '')
// R8 §9.4.6 — drill từ bar-card MTTR/SLA opsmgr: ?sla_breached=1 / ?is_repeat_failure=1.
const slaBreached = ref<boolean>(route.query.sla_breached === '1')
const repeatFailure = ref<boolean>(route.query.is_repeat_failure === '1')
// BR-09-08 — cờ ảo "đang mở" (open=1) drill từ thẻ 'WO mở' / 'Phiếu đang mở'.
// Áp SoT BE open_repair_filter (NOT IN terminal, gồm Pending Inspection) →
// list trả CÙNG tập với card (INVARIANT card == drill). KHÔNG hardcode
// positive-list ở FE. `status` đơn lẻ ƯU TIÊN hơn open (mutually-exclusive).
const openFilter = ref<boolean>(route.query.open === '1')
const search = ref('')
const showFilters = ref<boolean>(!!(route.query.status || route.query.priority || route.query.asset || route.query.sla_breached || route.query.is_repeat_failure || route.query.open))

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

// BE Asset Repair.priority enum = Normal | Urgent | Emergency (asset_repair.json).
// Trước đây dropdown dùng Critical/High/Medium/Low → filter KHÔNG bao giờ khớp record.
// Dùng single-source REPAIR_PRIORITY_OPTIONS (WAVE2: status/enum sync với BE).
const PRIORITIES = REPAIR_PRIORITY_OPTIONS

interface Chip { key: 'status' | 'priority' | 'asset' | 'search' | 'slaBreached' | 'repeatFailure' | 'open'; label: string }
const activeChips = computed<Chip[]>(() => {
  const chips: Chip[] = []
  if (slaBreached.value) chips.push({ key: 'slaBreached', label: 'Vi phạm cam kết dịch vụ' })
  if (repeatFailure.value) chips.push({ key: 'repeatFailure', label: 'Lỗi lặp lại' })
  // open chip chỉ hiện khi KHÔNG có status đơn lẻ (status ưu tiên hơn).
  if (openFilter.value && !statusFilter.value) chips.push({ key: 'open', label: 'Đang mở' })
  if (statusFilter.value) {
    const s = CM_STATUSES.find(x => x.value === statusFilter.value)
    chips.push({ key: 'status', label: s?.label ?? statusFilter.value })
  }
  if (priorityFilter.value) {
    const p = PRIORITIES.find(x => x.value === priorityFilter.value)
    chips.push({ key: 'priority', label: p?.label ?? priorityFilter.value })
  }
  if (assetFilter.value) chips.push({ key: 'asset', label: `Thiết bị: ${assetFilter.value}` })
  if (search.value.trim()) chips.push({ key: 'search', label: `"${search.value.trim()}"` })
  return chips
})

const activeFilterCount = computed(() => activeChips.value.length)

function clearChip(key: string) {
  if (key === 'status') statusFilter.value = ''
  else if (key === 'priority') priorityFilter.value = ''
  else if (key === 'asset') assetFilter.value = ''
  else if (key === 'slaBreached') slaBreached.value = false
  else if (key === 'repeatFailure') repeatFailure.value = false
  else if (key === 'open') openFilter.value = false
  else if (key === 'search') { search.value = ''; reload(1) }  // search KHÔNG có watch → reload thủ công
}

function resetFilters() {
  statusFilter.value = ''
  priorityFilter.value = ''
  assetFilter.value = ''
  slaBreached.value = false
  repeatFailure.value = false
  openFilter.value = false
  search.value = ''
  reload(1)
}

// Nhấp vào badge trong bảng → lọc ngay
function quickFilter(key: 'status' | 'priority', value: string) {
  if (!value) return
  // chọn status đơn lẻ → tắt open-set (mutually-exclusive, status ưu tiên hơn).
  if (key === 'status') { statusFilter.value = value; openFilter.value = false }
  else priorityFilter.value = value
  showFilters.value = false
}

function buildFilters(): Record<string, string> {
  const f: Record<string, string> = {}
  if (statusFilter.value) f.status = statusFilter.value
  if (priorityFilter.value) f.priority = priorityFilter.value
  if (assetFilter.value) f.asset_ref = assetFilter.value
  if (slaBreached.value) f.sla_breached = '1'
  if (repeatFailure.value) f.is_repeat_failure = '1'
  // open=1 chỉ áp khi KHÔNG có status đơn lẻ (status ưu tiên). BE dịch open=1
  // → open_repair_filter (SoT, NOT IN terminal) — không gửi positive-list.
  if (openFilter.value && !statusFilter.value) f.open = '1'
  return f
}

// CR-18: refetch SERVER với column-filters + free-text `search` (mã phiếu / mã
// thiết bị / tên thiết bị). Search phủ TOÀN tập mọi trang — KHÔNG lọc client-side
// page-limited. `search` là param độc lập AND cùng các filter khác. Gửi undefined
// khi rỗng ⇒ baseline byte-identical (BE bỏ qua).
// ── Trạng thái nạp danh sách (AC-UX-047 lô 3 · biến thể D — 02 §14.2, khuôn §13.2) ─────────
// `stores/imm09.ts:160 fetchKPIs` ghi vào CÙNG ô `error` với lượt nạp danh sách ⇒ bind thẳng
// `store.error` sẽ để một lượt nạp thẻ chỉ số hỏng xoá trắng bảng đang xem (INV-UX3-28).
// View sở hữu cờ `listLoading` + ô `loadError` RIÊNG và CHỤP lỗi ngay sau `await`.
// `store.filterError` là CẢNH BÁO bộ lọc (bảng giữ dữ liệu) ⇒ KHÔNG nối vào `:error-message`.
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
    ? 'Không tìm thấy lệnh sửa chữa nào phù hợp'
    : 'Chưa có lệnh sửa chữa nào',
)
const emptyHint = 'Lệnh sửa chữa được mở từ sự cố hoặc tạo trực tiếp khi thiết bị hỏng.'

// ListFilterBar phát `@apply` sau debounce khi user gõ ô tìm → refetch server + reset trang 1.
function applyFilters() {
  reload(1)
}

onMounted(async () => {
  // TUẦN TỰ (02 §14.4): danh sách trước, thẻ chỉ số sau.
  await reload()
  store.fetchKPIs()
})
watch([statusFilter, priorityFilter, assetFilter, slaBreached, repeatFailure, openFilter], () => reload(1))
// §9.3 — drill-down lần 2 từ dashboard (cùng route, query khác) → sync filter.
watch(() => route.query.status, (val) => { statusFilter.value = (val as string) || '' })
watch(() => route.query.priority, (val) => { priorityFilter.value = (val as string) || '' })
watch(() => route.query.sla_breached, (val) => { slaBreached.value = val === '1' })
watch(() => route.query.is_repeat_failure, (val) => { repeatFailure.value = val === '1' })
watch(() => route.query.open, (val) => { openFilter.value = val === '1' })

// KPI strip (docs/fe/09-repair/repair-list.html) — nguồn: get_repair_kpis thật từ BE.
const kpiItems = computed<WoKpiItem[]>(() => {
  const k = store.kpis?.kpis
  if (!k) return []
  return [
    { label: 'Đang mở', value: k.open_wos, color: 'info', trend: 'Chờ xử lý' },
    { label: 'Hoàn tất tháng', value: k.total_completed, color: 'success' },
    { label: 'Thời gian sửa chữa trung bình', value: `${k.mttr_avg_hours}h`, color: 'primary', trend: `cam kết dịch vụ ${k.sla_compliance_pct}%` },
    { label: 'Tái hỏng', value: k.repeat_failure_count, color: 'warning', trend: k.repeat_failure_count > 0 ? 'Cần theo dõi' : 'Ổn định' },
  ]
})

// Sync khi điều hướng từ AssetDetail (?asset=...)
watch(() => route.query.asset, (val) => {
  assetFilter.value = (val as string) || ''
})

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
    <!-- INV-ROWSCOPE / A8: "Tổng" LUÔN lấy từ pagination.total (SoT permission-aware
         của BE — count và rows nay dùng CÙNG 1 predicate row-scope). Fallback cũ
         `?? store.workOrders.length` che giấu drift count-vs-rows (đếm được N phiếu
         nhưng chỉ đọc được M) ⇒ đã bỏ, chỉ còn `?? 0` chống undefined.
         "Hiển thị X" bên dưới mới là số dòng của TRANG hiện tại (.length). -->
    <PageHeader
      title="Lệnh Sửa chữa"
      :subtitle="`Tổng ${store.pagination.total ?? 0} lệnh`"
      :breadcrumb="[{ label: 'IMM-09 · Sửa chữa', to: '/cm/dashboard' }, { label: 'Danh sách' }]"
    >
      <template #actions>
        <FilterToggleButton v-model="showFilters" :count="activeFilterCount" />
        <button v-if="can('repair.create')" class="btn-primary" @click="router.push(assetFilter ? `/cm/create?asset=${encodeURIComponent(assetFilter)}` : '/cm/create')">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          Tạo lệnh mới
        </button>
      </template>
    </PageHeader>
      </template>

      <!-- Dải chỉ số — `#summary` CHỈ render ở trạng thái rỗng/có-dữ-liệu ⇒ hết cảnh in số
           của một lượt nạp hỏng (INV-UX3-27). -->
      <template #summary><WorkOrderKpiStrip :items="kpiItems" /></template>

      <template #filters>
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

    <!-- AC-CR-79 — Bộ lọc không hợp lệ: BE từ chối khoá lọc lạ bằng lỗi 400 TRONG
         envelope (HTTP-200). Đây là CẢNH BÁO, không phải sự cố nạp dữ liệu ⇒ bảng
         bên dưới GIỮ NGUYÊN dữ liệu đang xem (không trắng trang, không đăng xuất).
         Nội dung hiển thị là message tiếng Việt do BE trả về — FE KHÔNG dựng lại
         danh sách khoá hợp lệ (SSoT nằm ở services/imm09.py). -->
    <div
      v-if="store.filterError"
      class="alert-warning"
      role="alert"
      data-test="cm-filter-error"
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
          v-else-if="can('repair.create')"
          class="btn-primary"
          @click="router.push('/cm/create')"
        >Tạo lệnh sửa chữa</button>
      </template>

      <template #toolbar>
        <div class="flex items-center justify-between px-4 py-2.5 border-b border-slate-100 bg-slate-50/60 text-xs text-slate-500">
          <span>Hiển thị <strong class="text-slate-700">{{ store.workOrders.length }}</strong> / {{ store.pagination.total ?? 0 }} lệnh</span>
          <button v-if="activeFilterCount > 0" class="text-red-500 hover:text-red-700 font-medium" @click="resetFilters">Xóa tất cả</button>
        </div>
      </template>

      <!-- Mobile card list (< sm) -->
      <div class="mobile-card-list sm:hidden">
        <div
          v-for="wo in store.workOrders"
          :key="wo.name"
          class="mobile-card"
          @click="router.push(`/cm/work-orders/${wo.name}`)"
        >
          <!-- Row 1: code + status -->
          <div class="flex items-center justify-between mb-2">
            <span class="font-mono text-sm font-semibold text-brand-700">{{ wo.name }}</span>
            <button
              :class="['px-2.5 py-0.5 rounded-full text-xs font-medium', getStatusColor(wo.status)]"
              @click.stop="quickFilter('status', wo.status)"
            >{{ translateStatus(wo.status) }}</button>
          </div>
          <!-- Row 2: asset -->
          <p class="text-sm font-medium text-slate-900 truncate">{{ wo.asset_name || wo.asset_ref }}</p>
          <p class="text-xs text-slate-400 font-mono">{{ wo.asset_ref }}</p>
          <!-- Row 3: type, priority, date -->
          <div class="flex flex-wrap items-center gap-x-2 gap-y-1 mt-1.5 text-xs text-slate-500">
            <span>{{ repairTypeLabel(wo.repair_type) }}</span>
            <button
              :class="['px-1.5 py-0.5 rounded-full text-[11px] font-medium', priorityClass(wo.priority)]"
              @click.stop="quickFilter('priority', wo.priority)"
            >{{ priorityLabel(wo.priority) }}</button>
            <span class="text-slate-300">·</span>
            <span>{{ formatDateTime(wo.open_datetime) }}</span>
          </div>
          <!-- Row 4: technician + MTTR (if present) -->
          <div v-if="wo.assigned_to_name || wo.mttr_hours" class="flex items-center justify-between mt-2 pt-2 border-t border-slate-100 text-xs">
            <span class="text-slate-600 truncate">{{ wo.assigned_to_name || '—' }}</span>
            <span v-if="wo.mttr_hours" :class="wo.sla_breached ? 'text-red-600 font-semibold' : 'text-slate-500'">
              {{ wo.mttr_hours }}h
            </span>
          </div>
          <!-- Flags -->
          <!-- BR-09-07 LIVE: badge "SLA vi phạm" theo live-truth (is_sla_breached) ưu tiên,
               fallback cờ thô (sla_breached) — kill undercount cửa-sổ-trễ-scheduler. -->
          <div v-if="(wo.is_sla_breached ?? wo.sla_breached) || wo.is_repeat_failure" class="flex gap-2 mt-1">
            <span v-if="wo.is_sla_breached ?? wo.sla_breached" class="text-[10px] text-red-600 font-medium">Cam kết dịch vụ vi phạm</span>
            <span v-if="wo.is_repeat_failure" class="text-[10px] text-amber-700">Tái hỏng</span>
          </div>
        </div>
      </div>

      <!-- Desktop table (sm+) -->
      <div class="hidden sm:block table-wrapper">
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
              v-for="wo in store.workOrders" :key="wo.name"
              class="hover:bg-slate-50 cursor-pointer transition-colors"
              @click="router.push(`/cm/work-orders/${wo.name}`)"
            >
              <td class="table-cell">
                <div class="font-mono text-sm font-semibold text-brand-700">{{ wo.name }}</div>
                <!-- BR-09-07 LIVE: live-truth (is_sla_breached) ưu tiên, fallback cờ thô. -->
                <div v-if="wo.is_sla_breached ?? wo.sla_breached" class="text-xs text-red-600 font-medium mt-0.5">Cam kết dịch vụ vi phạm</div>
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
