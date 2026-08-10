<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useCapabilities } from '@/composables/useCapabilities'
import { useCommissioningStore } from '@/stores/imm04'
import StatusBadge from '@/components/common/StatusBadge.vue'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import WorkOrderKpiStrip from '@/components/common/WorkOrderKpiStrip.vue'
import { commissioningKpiItems, type CommissioningKpiItem } from './commissioningKpi'
import FilterToggleButton from '@/components/common/FilterToggleButton.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'
import BasePagination from '@/components/common/BasePagination.vue'
import ListPageShell from '@/components/ui/ListPageShell.vue'
import { formatDate } from '@/utils/docUtils'
import type { CommissioningFilters, WorkflowState } from '@/types/imm04'

const router = useRouter()
const { can } = useCapabilities()
const route  = useRoute()
const store  = useCommissioningStore()

const showFilters = ref(false)
// AC-CR-95 — deep-link «Xem tất cả» từ tab «Bản ghi liên quan» của một thiết bị:
// `/commissioning?asset=<mã>`. Khoá URL là `asset` (khớp
// `DOCTYPE_LIST_TARGET['Asset Commissioning'].queryKey`) nhưng khoá BE là `final_asset`
// — ĐÂY LÀ PHÉP DỊCH, không phải trùng tên: `final_asset` mới là Link → AC Asset trên
// `Asset Commissioning`, và nó đã nằm trong `services/imm04._ALLOWED_FILTER_KEYS`.
// Seed NGAY tại khai báo: `onMounted` gọi `cleanFilters()` nên lần nạp ĐẦU đã lọc.
const filters = ref<CommissioningFilters>({
  workflow_state: (route.query.workflow_state as WorkflowState) || '',
  vendor_serial_no: '',
  master_item:  '',
  clinical_dept: '',
  final_asset: (route.query.asset as string) || '',
  overdue: route.query.filter === 'overdue',
})

const WORKFLOW_STATES: { value: WorkflowState | ''; label: string }[] = [
  { value: '', label: 'Tất cả trạng thái' },
  { value: 'Draft', label: 'Nháp' },
  { value: 'Pending Doc Verify', label: 'Chờ kiểm tra tài liệu' },
  { value: 'To Be Installed', label: 'Chờ lắp đặt' },
  { value: 'Installing', label: 'Đang lắp đặt' },
  { value: 'Identification', label: 'Nhận dạng' },
  { value: 'Initial Inspection', label: 'Kiểm tra ban đầu' },
  { value: 'Non Conformance', label: 'Không phù hợp' },
  { value: 'Clinical Hold', label: 'Tạm giữ lâm sàng' },
  { value: 'Re Inspection', label: 'Kiểm tra lại' },
  { value: 'Clinical Release', label: 'Phát hành lâm sàng' },
  { value: 'Return To Vendor', label: 'Trả nhà cung cấp' },
]

type ChipKey = 'workflow_state' | 'vendor_serial_no' | 'master_item' | 'clinical_dept'
  | 'final_asset' | 'overdue'
interface Chip { key: ChipKey; label: string }
const activeChips = computed<Chip[]>(() => {
  const chips: Chip[] = []
  // Nhãn chip thiết bị = MÃ thiết bị (BE list chưa enrich tên cho `final_asset`).
  // TUYỆT ĐỐI không in chữ `final_asset` ra giao diện (LL-FE-53).
  if (filters.value.final_asset?.trim()) {
    chips.push({ key: 'final_asset', label: `Thiết bị: ${filters.value.final_asset.trim()}` })
  }
  if (filters.value.workflow_state) {
    const s = WORKFLOW_STATES.find(x => x.value === filters.value.workflow_state)
    chips.push({ key: 'workflow_state', label: s?.label ?? filters.value.workflow_state })
  }
  if (filters.value.vendor_serial_no?.trim()) chips.push({ key: 'vendor_serial_no', label: `Số serial: ${filters.value.vendor_serial_no.trim()}` })
  if (filters.value.master_item?.trim()) chips.push({ key: 'master_item', label: `Mẫu thiết bị: ${filters.value.master_item.trim()}` })
  if (filters.value.clinical_dept?.trim()) chips.push({ key: 'clinical_dept', label: `Khoa: ${filters.value.clinical_dept.trim()}` })
  // BR-04-10: chip ảo "Quá hạn" cho cờ overdue (drill từ KPI card). Nhãn VI, không leak raw EN.
  if (filters.value.overdue) chips.push({ key: 'overdue', label: 'Quá hạn' })
  return chips
})
const activeFilterCount = computed(() => activeChips.value.length)

/**
 * Rút khoá `asset` khỏi URL; trả `true` khi thật sự đã điều hướng (xem chú thích cùng
 * tên ở `views/incident/CAPAListView.vue`): URL là SSoT của bộ lọc thiết bị, URL đổi thì
 * watcher/remount đã nạp lại — nạp thêm ở call-site = request y hệt lần thứ hai.
 */
function dropAssetQuery(): boolean {
  if (!route.query.asset) return false
  const query = { ...route.query }
  delete query.asset
  router.replace({ query })
  return true
}

function clearChip(key: string) {
  if (key === 'final_asset' && dropAssetQuery()) return
  if (key === 'overdue') filters.value.overdue = false
  else (filters.value as Record<string, unknown>)[key] = ''
  applyFilters()
}

/**
 * Mã thiết bị đang giới hạn danh sách. SSoT là URL (`?asset=`) chứ KHÔNG phải
 * `filters.final_asset`: sau `router.replace` cái ref còn lệch một tick, mà empty-state
 * theo ngữ cảnh phải tắt NGAY khi khoá rời URL (nếu không sẽ nhá lại câu "không có phiếu
 * nào của thiết bị …" trong lúc danh sách đầy đủ đang nạp).
 */
const assetScope = computed(() => ((route.query.asset as string) || '').trim())

/**
 * A9 — 0 dòng VÌ đang giới hạn theo một thiết bị. Từ AC-CR-98/106, Vendor Engineer
 * deep-link một thiết bị NGOÀI phạm vi được giao sẽ ra 0 dòng thật (trước đây rò toàn bộ
 * phiếu của mọi thiết bị được giao); vẽ khối rỗng vô danh ở đây là dựng lại đúng cái
 * "bấm ô đếm → màn trống không nói vì sao" mà vòng này đang diệt.
 */
const isScopedEmpty = computed(() => assetScope.value !== '' && store.list.length === 0)

/**
 * FE-2 — «Xoá bộ lọc thiết bị» đi CÙNG một đường với nút bỏ chip «Thiết bị: …»
 * (`clearChip('final_asset')` → `dropAssetQuery()` → `router.replace` bỏ ĐÚNG khoá
 * `asset`, giữ mọi khoá khác) để không có hai luồng xoá lệch nhau, và nạp lại ĐÚNG một
 * lần: watcher `route.query.asset` là nơi duy nhất phát request sau khi URL đổi.
 */
function clearAssetScope() { clearChip('final_asset') }

function cleanFilters(): CommissioningFilters {
  const f: CommissioningFilters = {}
  if (filters.value.workflow_state)          f.workflow_state   = filters.value.workflow_state
  if (filters.value.vendor_serial_no?.trim()) f.vendor_serial_no = filters.value.vendor_serial_no.trim()
  if (filters.value.master_item?.trim())      f.master_item      = filters.value.master_item.trim()
  if (filters.value.clinical_dept?.trim())    f.clinical_dept    = filters.value.clinical_dept.trim()
  if (filters.value.final_asset?.trim())      f.final_asset      = filters.value.final_asset.trim()
  // Chỉ đính kèm cờ overdue khi bật → AND với các filter khác ở BE (không clobber).
  if (filters.value.overdue)                  f.overdue          = true
  return f
}

// ── Trạng thái nạp danh sách (AC-UX-047 lô 3 · biến thể D — 02 §14.2, khuôn §13.2) ─────────
// `stores/imm04.ts:73` dùng CHUNG một ô `error` cho ~20 hành động GHI (`_captureError`) ⇒ bind
// thẳng `store.error` sẽ để một lần duyệt/huỷ hỏng xoá trắng danh sách đang xem (INV-UX3-28).
// CHỤP lỗi ngay sau `await` của lượt nạp danh sách rồi trả ô dùng chung về sạch.
const loadError = ref<string | null>(null)

async function load(filters: CommissioningFilters, page = 1, pageSize = store.pagination.page_size) {
  loadError.value = null
  store.error = null
  await store.fetchList(filters, page, pageSize)
  loadError.value = store.error ?? null
  if (loadError.value) store.error = null
}

/** Điểm vào DUY NHẤT của «Thử lại» — giữ nguyên bộ lọc VÀ trang đang xem. */
function reload() { return load(cleanFilters(), store.pagination.page) }

function applyFilters() { return load(cleanFilters(), 1, store.pagination.page_size) }

function resetFilters() {
  filters.value = {
    workflow_state: '', vendor_serial_no: '', master_item: '', clinical_dept: '',
    final_asset: '', overdue: false,
  }
  dropAssetQuery()
  load({}, 1)
}

/** Click KPI card → drill. Overdue card bật cờ overdue + reload; thẻ state khác giữ quickFilter. */
function onKpiClick(index: number) {
  const item = kpiItems.value[index]
  if (!item) return
  if (item.overdueFilter) {
    filters.value.overdue = true
    showFilters.value = false
    applyFilters()
  } else if (item.filterState !== undefined) {
    // Reuse quick-filter cho workflow_state (clear khi filterState === '').
    filters.value.workflow_state = (item.filterState || '') as WorkflowState | ''
    showFilters.value = false
    applyFilters()
  }
}

function quickFilter(key: 'workflow_state' | 'clinical_dept', value: string) {
  if (!value) return
  if (key === 'workflow_state') filters.value.workflow_state = value as WorkflowState
  else if (key === 'clinical_dept') filters.value.clinical_dept = value
  showFilters.value = false
  applyFilters()
}

function goToPage(page: number) { return load(cleanFilters(), page, store.pagination.page_size) }

/**
 * FE-2 / TC-FE-COMM-SE-08 — «đang ở trang 3 mà tổng còn 0» KHÔNG được kẹt.
 *
 * `assetcore/utils/pagination.paginate` (`:45-53`) **echo** tham số `page` và KHÔNG kẹp về
 * `total_pages`, nên khi phạm vi được xem co lại giữa hai lần nạp (phiếu bị huỷ, thiết bị
 * ra ngoài phạm vi được giao — chính ca AC-CR-98/106) máy chủ trả về đúng
 * `{page: 3, total: 0, total_pages: 0}`. Thanh phân trang tự ẩn (`total_pages > 1`), nên
 * con trỏ trang mắc ở 3 mà KHÔNG còn nút nào để về 1: mọi lần nạp sau đó
 * (`refreshList` của nút «Thử lại», hay lần lọc kế) vẫn đọc offset 40 ⇒ danh sách rỗng
 * vĩnh viễn, lối thoát duy nhất là tải lại trang.
 *
 * Vì vậy: hết nạp mà con trỏ trang vượt số trang thật ⇒ nạp lại trang 1, GIỮ nguyên bộ
 * lọc. `pageReclaimed` chặn lặp (đúng MỘT lần cho mỗi lần lệch) và tự mở lại khi con trỏ
 * đã hợp lệ, để lần co dữ liệu sau vẫn được tự sửa.
 */
const pageReclaimed = ref(false)
watch(
  () => [store.listLoading, store.pagination.page, store.pagination.total_pages] as const,
  ([loading, page, totalPages]) => {
    if (loading) return
    if (page <= 1 || page <= totalPages) { pageReclaimed.value = false; return }
    if (pageReclaimed.value) return
    pageReclaimed.value = true
    goToPage(1)
  },
)

// KPI strip (Core Doc docs/imm-04/06_Frontend_Design.md §3.1 · docs/fe/04-commissioning/commissioning-list.html)
// Source: get_dashboard_stats (store.fetchDashboardStats). Display-only, reuses WorkOrderKpiStrip (IMM-08/09 pattern).
const kpiItems = computed<CommissioningKpiItem[]>(() => commissioningKpiItems(store.dashboardStats?.kpis))

// Chữ trạng thái rỗng — SSoT là bảng copy 02 §14.4 (LL-FE-53: 100% tiếng Việt).
// BA nhánh: rỗng-theo-ngữ-cảnh-thiết-bị (A9) ≠ rỗng-do-lọc ≠ rỗng-thật. Ba câu KHÁC nhau vì
// ba nguyên nhân khác nhau; gộp lại là dựng lại đúng cái «màn trống không nói vì sao».
const emptyTitle = computed(() => {
  if (isScopedEmpty.value) {
    return `Không có phiếu nghiệm thu lắp đặt nào của thiết bị ${assetScope.value} trong phạm vi bạn được xem.`
  }
  return activeFilterCount.value > 0
    ? 'Không tìm thấy phiếu nào phù hợp'
    : 'Chưa có phiếu nghiệm thu lắp đặt nào'
})
const emptyHint = computed(() =>
  isScopedEmpty.value
    ? 'Thiết bị này có thể chưa có phiếu nào, hoặc phiếu của nó nằm ngoài phạm vi bạn được giao.'
    : 'Phiếu nghiệm thu lắp đặt được lập khi nhà cung cấp bàn giao thiết bị tại khoa.',
)

onMounted(() => {
  load(cleanFilters(), 1)
  // KPI fetch is non-blocking: store.fetchDashboardStats swallows its own errors
  // (no shared error.value pollution) so a KPI failure can't hide/hijack the list.
  store.fetchDashboardStats()
})

watch(() => route.query.workflow_state, (val) => {
  filters.value.workflow_state = (val as WorkflowState) || ''
  applyFilters()
})

// Drill lần 2 CÙNG route (bấm «Xem tất cả» ở thiết bị KHÁC) không remount component ⇒
// đồng bộ query → ref rồi nạp lại; `applyFilters` đã reset về trang 1.
watch(() => route.query.asset, (val) => {
  const next = (val as string) || ''
  if ((filters.value.final_asset || '') === next) return
  filters.value.final_asset = next
  applyFilters()
})
</script>

<template>
  <div>
    <ListPageShell
      :loading="store.listLoading"
      :error-message="loadError"
      :is-empty="!store.list.length"
      :empty-title="emptyTitle"
      :empty-hint="emptyHint"
      @retry="reload">
      <template #header>
    <PageHeader
      title="Phiếu Tiếp nhận và lắp đặt"
      :subtitle="`Tổng ${store.pagination.total} phiếu`"
      :breadcrumb="[{ label: 'IMM-04 · Tiếp nhận', to: '/commissioning' }, { label: 'Danh sách' }]"
    >
      <template #actions>
        <FilterToggleButton v-model="showFilters" :count="activeFilterCount" />
        <router-link v-if="can('commissioning.create')" to="/commissioning/new" class="btn-primary">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          Tạo phiếu mới
        </router-link>
      </template>
    </PageHeader>
      </template>

      <!-- KPI strip: docs/imm-04/06_Frontend_Design.md §3.1 — "Quá hạn SLA" clickable → drill
           overdue. Đặt ở `#summary` ⇒ CHỈ render ở trạng thái rỗng/có-dữ-liệu, hết cảnh in số
           của một lượt nạp hỏng (INV-UX3-27). -->
      <template #summary>
        <WorkOrderKpiStrip :items="kpiItems" @kpi-click="onKpiClick" />
      </template>

      <template #filters>
    <ListFilterBar
      :show="showFilters"
      :chips="activeChips"
      :show-search="false"
      @reset="resetFilters"
      @clear-chip="clearChip"
      @apply="applyFilters"
    >
      <template #fields>
        <div class="form-group">
          <label class="form-label">Trạng thái</label>
          <select v-model="filters.workflow_state" class="form-select" @change="applyFilters">
            <option v-for="s in WORKFLOW_STATES" :key="s.value" :value="s.value">{{ s.label }}</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Số serial</label>
          <input v-model="filters.vendor_serial_no" class="form-input font-mono" placeholder="Nhập số serial..." @keyup.enter="applyFilters" />
        </div>
        <div class="form-group">
          <label class="form-label">Mẫu thiết bị</label>
          <input v-model="filters.master_item" class="form-input" placeholder="Tên model..." @keyup.enter="applyFilters" />
        </div>
        <div class="form-group">
          <label class="form-label">Khoa / Phòng</label>
          <input v-model="filters.clinical_dept" class="form-input" placeholder="Tên khoa..." @keyup.enter="applyFilters" />
        </div>
      </template>
    </ListFilterBar>
      </template>

      <template #skeleton><SkeletonLoader variant="table" :rows="8" /></template>

      <!-- A9 — LỐI THOÁT của trạng thái rỗng. Chữ giải thích nằm ở `empty-title`/`empty-hint`
           (một nguồn duy nhất, INV-UX3-26); ở đây chỉ còn hành động. `list-empty-scoped` giữ
           NGUYÊN tên vì `commissioningScopedEmpty.test.ts` đang khoá nó (02 §14.3). -->
      <template #empty-action>
        <div
          v-if="isScopedEmpty"
          data-testid="list-empty-scoped"
          class="flex flex-wrap items-center justify-center gap-2"
        >
          <button type="button" class="btn-secondary text-sm" @click="clearAssetScope">
            Xoá bộ lọc thiết bị
          </button>
          <button
            v-if="activeFilterCount > 1"
            type="button"
            class="btn-ghost text-sm"
            @click="resetFilters"
          >
            Xoá tất cả bộ lọc
          </button>
        </div>
        <button
          v-else-if="activeFilterCount > 0"
          class="text-xs text-brand-600 hover:text-brand-700 font-medium underline"
          @click="resetFilters"
        >Xóa bộ lọc để xem tất cả</button>
        <router-link
          v-else-if="can('commissioning.create')"
          to="/commissioning/new"
          class="btn-primary"
        >Tạo phiếu nghiệm thu</router-link>
      </template>

    <template #default>
      <!-- Mobile cards (< sm) -->
      <div class="mobile-card-list sm:hidden">
        <div
          v-for="item in store.list"
          :key="item.name"
          class="mobile-card"
          @click="router.push(`/commissioning/${item.name}`)"
        >
          <div class="flex items-center justify-between mb-2">
            <span class="font-mono text-sm font-semibold text-brand-700">{{ item.name }}</span>
            <button
              class="transition-all rounded"
              @click.stop="quickFilter('workflow_state', item.workflow_state || '')"
            >
              <StatusBadge :state="item.workflow_state" />
            </button>
          </div>
          <p class="text-sm font-medium text-slate-900 truncate">{{ item.master_item_name || item.master_item || '—' }}</p>
          <div class="flex flex-wrap items-center gap-x-2 gap-y-1 mt-1.5 text-xs text-slate-500">
            <span>{{ item.vendor_name || item.vendor || '—' }}</span>
            <span class="text-slate-300">·</span>
            <span>{{ item.clinical_dept_name || item.clinical_dept || '—' }}</span>
            <span v-if="item.vendor_serial_no" class="text-slate-300">·</span>
            <span v-if="item.vendor_serial_no" class="font-mono">{{ item.vendor_serial_no }}</span>
          </div>
        </div>
      </div>

      <!-- Desktop table (sm+) -->
      <div class="hidden sm:block table-wrapper animate-slide-up" style="animation-delay: 80ms">
        <table class="min-w-full divide-y divide-slate-100">
          <thead>
            <tr>
              <th class="table-header">Phiếu</th>
              <th class="table-header">Mẫu thiết bị</th>
              <th class="table-header">Nhà cung cấp</th>
              <th class="table-header">Khoa nhận</th>
              <th class="table-header">Số serial NSX</th>
              <th class="table-header">Ngày hẹn</th>
              <th class="table-header">Trạng thái</th>
              <th class="table-header">Tài sản</th>
              <th class="table-header">Cập nhật</th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-slate-100">
            <tr
              v-for="(item, i) in store.list"
              :key="item.name"
              class="table-row animate-fade-in"
              :style="`animation-delay: ${i * 30}ms`"
              @click="router.push(`/commissioning/${item.name}`)"
            >
              <td class="table-cell">
                <span class="font-mono text-[12px] font-semibold text-brand-600">{{ item.name }}</span>
              </td>
              <td class="table-cell max-w-40">
                <div class="text-slate-700 truncate">{{ item.master_item_name || item.master_item || '—' }}</div>
                <div v-if="item.master_item && item.master_item_name" class="text-xs text-slate-400 font-mono truncate">{{ item.master_item }}</div>
              </td>
              <td class="table-cell max-w-32">
                <div class="text-slate-700 truncate">{{ item.vendor_name || item.vendor || '—' }}</div>
              </td>
              <td class="table-cell">
                <button
                  class="text-slate-700 hover:underline decoration-dotted underline-offset-2 text-left"
                  :title="`Lọc: ${item.clinical_dept_name || item.clinical_dept}`"
                  @click.stop="quickFilter('clinical_dept', item.clinical_dept || '')"
                >{{ item.clinical_dept_name || item.clinical_dept || '—' }}</button>
                <div v-if="item.clinical_dept && item.clinical_dept_name" class="text-xs text-slate-400">{{ item.clinical_dept }}</div>
              </td>
              <td class="table-cell">
                <span class="font-mono text-xs text-slate-400">{{ item.vendor_serial_no || '—' }}</span>
              </td>
              <td class="table-cell text-slate-600 text-sm">
                {{ formatDate(item.expected_installation_date) }}
              </td>
              <td class="px-5 py-3.5">
                <button
                  class="transition-all hover:ring-2 hover:ring-offset-1 hover:ring-current/50 rounded"
                  :title="`Lọc: ${item.workflow_state}`"
                  @click.stop="quickFilter('workflow_state', item.workflow_state || '')"
                >
                  <StatusBadge :state="item.workflow_state" />
                </button>
              </td>
              <td class="table-cell">
                <router-link
                  v-if="item.final_asset"
                  :to="`/assets/${item.final_asset}`"
                  class="font-mono text-[11px] text-blue-600 hover:underline"
                  @click.stop
                >{{ item.final_asset }}</router-link>
                <span v-else class="text-slate-300 text-xs">—</span>
              </td>
              <td class="table-cell text-slate-400 text-xs">{{ formatDate(item.modified) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

      <!-- Dòng đếm — `#toolbar` CHỈ render ở trạng thái có dữ liệu. Tổng LUÔN là
           `pagination.total` do máy chủ đếm cùng engine với các dòng
           (`services/imm04.list_commissioning` → `count_with_or`, AC-CR-98) — KHÔNG phải
           `store.list.length` (đó là số dòng của TRANG đang xem). -->
      <template #toolbar>
        <div class="flex items-center justify-between px-4 py-2.5 border-b border-slate-100 bg-slate-50/60 text-xs text-slate-500">
          <span data-testid="list-count">Hiển thị <strong class="text-slate-700">{{ store.list.length }}</strong> / {{ store.pagination.total }} phiếu</span>
          <button v-if="activeFilterCount > 0" class="text-red-500 hover:text-red-700 font-medium" @click="resetFilters">Xóa tất cả</button>
        </div>
      </template>

      <!-- `#pagination` chỉ render ở trạng thái có dữ liệu ⇒ điều kiện `!isScopedEmpty` cũ
           thành thừa, GIỮ để không đổi hành vi khi danh sách có dòng (02 §14.4). -->
      <template #pagination>
        <BasePagination v-if="!isScopedEmpty" :pagination="store.pagination" @page-change="goToPage" />
      </template>
    </ListPageShell>
</div>
</template>
