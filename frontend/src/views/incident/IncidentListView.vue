<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team Incident List
import { ref, onMounted, computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useImm12Store } from '@/stores/imm12'
import PageHeader from '@/components/common/PageHeader.vue'
import FilterToggleButton from '@/components/common/FilterToggleButton.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'
import BasePagination from '@/components/common/BasePagination.vue'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
import ListPageShell from '@/components/ui/ListPageShell.vue'
import WorkOrderKpiStrip, { type WoKpiItem } from '@/components/common/WorkOrderKpiStrip.vue'
import SlaBreachBadge from '@/components/incident/SlaBreachBadge.vue'
// SSoT nhãn IMM-12 (R20): status badge dùng incidentStatusLabel/Class — KHÔNG
// generic StatusBadge (translateStatus→STATUS_MAP) vì map đó drift cho domain này
// (Open='Đang mở' vs 'Mới mở', In Progress='Đang thực hiện' vs 'Đang điều tra').
// Cùng nguồn với IncidentDetailView + IMM12DashboardView → list==detail==donut.
import { incidentSeverityLabel, incidentStatusLabel, incidentStatusClass, INCIDENT_OPEN_FILTER_LABEL } from '@/constants/labels'
import { useCapabilities } from '@/composables/useCapabilities'

const router = useRouter()
const route = useRoute()
const store = useImm12Store()
// Read-only oversight (opsmgr): chỉ user có corrective.create mới thấy nút Báo cáo sự cố.
const { can } = useCapabilities()

/**
 * Core Doc §9.3 / §9.4.6 — đọc route.query (drill-down từ dashboard) → áp vào filter.
 * Keys hỗ trợ: severity, status, open, asset. Trả true nếu có filter set từ query.
 *
 * open=1 (cờ ảo "đang mở", SoT BE open_incident_filter) chỉ áp khi KHÔNG có status
 * đơn lẻ — status ưu tiên hơn open (mutually-exclusive, khớp BE _build_incident_filters).
 *
 * `asset` (AC-CR-91 — «Xem tất cả» từ tab «Bản ghi liên quan» của một thiết bị) là
 * khoá ĐỘC LẬP: cộng dồn (AND) với severity/status/open, KHÔNG loại trừ nhau.
 */
function applyQueryToFilters(): boolean {
  let touched = false
  const sev = route.query.severity
  const st = route.query.status
  const op = route.query.open
  const at = route.query.asset
  const sevVal = Array.isArray(sev) ? sev[0] : sev
  const stVal = Array.isArray(st) ? st[0] : st
  const opVal = Array.isArray(op) ? op[0] : op
  const atVal = Array.isArray(at) ? at[0] : at
  openFilter.value = false
  assetFilter.value = ''
  if (typeof sevVal === 'string' && sevVal) { severityFilter.value = sevVal; touched = true }
  if (typeof stVal === 'string' && stVal) { statusFilter.value = stVal; touched = true }
  // open=1 chỉ có hiệu lực khi không kèm status đơn lẻ (status ưu tiên hơn).
  if (opVal === '1' && !(typeof stVal === 'string' && stVal)) { openFilter.value = true; touched = true }
  if (typeof atVal === 'string' && atVal) { assetFilter.value = atVal; touched = true }
  if (touched) showFilters.value = true
  return touched
}

// KPI strip (mockup docs/fe/12-incident/incidents-list.html — 4 ô trên filter bar).
// Tile severity bind OPEN-SET SoT (critical_open/high_open qua open_incident_filter())
// — KHÔNG global critical/high (gồm Closed/Cancelled/Resolved) → strip khớp số dòng
// severity trong bảng khi drill ?open=1 / ?severity=. Label nêu rõ "đang mở" để không
// hiểu nhầm là tổng toàn cục. `?? 0` forward-compat khi BE chưa ship field mới.
const kpiItems = computed<WoKpiItem[]>(() => {
  const s = store.stats
  if (!s) return []
  const criticalOpen = 'critical_open' in s ? s.critical_open ?? 0 : 0
  const highOpen = 'high_open' in s ? s.high_open ?? 0 : 0
  // BR-12-12: s.chronic = SỐ NHÓM (asset,fault_code) đang lặp lại LIVE trong 90 ngày
  // (SoT get_chronic_failures → chronic_failure_count ở BE), KHÔNG đếm cờ stale
  // chronic_failure_flag. Binding GIỮ NGUYÊN — chỉ ngữ nghĩa giá trị đổi (live thay
  // stale). Badge per-row '⚠ Lặp lại' (:317) vẫn theo ir.chronic_failure_flag (mục
  // đích lifecycle riêng: đánh dấu incident từng thuộc cụm chronic) — KHÔNG đổi.
  const chronic = 'chronic' in s ? s.chronic : 0
  const closed = 'closed' in s ? s.closed : 0
  return [
    { label: 'Sự cố nghiêm trọng đang mở', value: criticalOpen, color: 'danger' },
    { label: 'Sự cố mức cao đang mở', value: highOpen, color: 'warning' },
    { label: 'Lặp lại (Chronic)', value: chronic, color: 'info' },
    { label: 'Đã đóng', value: closed, color: 'success' },
  ]
})

const severityFilter = ref('')
const statusFilter = ref('')
// Cờ ảo "đang mở" (open=1) — drill-down từ dashboard donut/card. Khác status đơn lẻ.
const openFilter = ref(false)
// Lọc theo thiết bị — drill từ «Xem tất cả» trong tab «Bản ghi liên quan» của một
// thiết bị (?asset=<mã>). Truyền thẳng xuống BE list_incidents(asset=…).
const assetFilter = ref('')
const showFilters = ref(false)

const SEVERITIES = [
  { value: '', label: 'Tất cả mức độ' },
  { value: 'Low', label: 'Thấp' },
  { value: 'Medium', label: 'Trung bình' },
  { value: 'High', label: 'Cao' },
  { value: 'Critical', label: 'Nghiêm trọng' },
]

const STATUSES = [
  { value: '', label: 'Tất cả trạng thái' },
  { value: 'Open', label: 'Mới mở' },
  { value: 'Acknowledged', label: 'Đã tiếp nhận' },
  { value: 'In Progress', label: 'Đang điều tra' },
  { value: 'RCA Required', label: 'Cần phân tích nguyên nhân gốc' },
  { value: 'Resolved', label: 'Đã giải quyết' },
  { value: 'Closed', label: 'Đã đóng' },
  { value: 'Cancelled', label: 'Đã hủy' },
]

const SEV_COLOR: Record<string, string> = {
  Low: 'bg-green-100 text-green-700',
  Medium: 'bg-yellow-100 text-yellow-700',
  High: 'bg-orange-100 text-orange-700',
  Critical: 'bg-red-100 text-red-700',
}

function formatDateTime(d?: string) {
  if (!d) return '—'
  return new Date(d).toLocaleString('vi-VN')
}

interface Chip { key: 'severity' | 'status' | 'open' | 'asset'; label: string }
const activeChips = computed<Chip[]>(() => {
  const chips: Chip[] = []
  if (severityFilter.value) {
    const s = SEVERITIES.find(x => x.value === severityFilter.value)
    chips.push({ key: 'severity', label: s?.label ?? severityFilter.value })
  }
  if (statusFilter.value) {
    const s = STATUSES.find(x => x.value === statusFilter.value)
    chips.push({ key: 'status', label: s?.label ?? statusFilter.value })
  }
  // Chip "Đang mở" (nhãn SSoT) chỉ khi cờ open bật VÀ không có status đơn lẻ.
  if (openFilter.value && !statusFilter.value) {
    chips.push({ key: 'open', label: INCIDENT_OPEN_FILTER_LABEL })
  }
  // Người dùng phải THẤY mình đang ở trạng thái lọc theo thiết bị và thoát ra được —
  // danh sách lọc câm trông y hệt "hệ thống mất dữ liệu" (ADR D-CR5-7 vế 3).
  if (assetFilter.value) {
    chips.push({ key: 'asset', label: `Thiết bị: ${assetFilter.value}` })
  }
  return chips
})

const activeFilterCount = computed(() => activeChips.value.length)

// AC-UX-047 (lô 1, biến thể C) — nguồn lỗi là `store.error` của `stores/imm12.ts`
// (đã xoá đầu lượt tại `:64`, gán tại `:72`) ⇒ KHÔNG sửa kho. Dải `.alert-error` cũ
// đã bỏ: nó hiện SONG SONG với «Không có sự cố nào được báo cáo» + dải KPI in số 0.
const emptyTitle = computed(() =>
  activeFilterCount.value > 0 ? 'Không có sự cố nào phù hợp' : 'Không có sự cố nào được báo cáo')
const EMPTY_HINT = 'Hãy báo cáo sự cố mới hoặc xoá bộ lọc để xem tất cả.'

function clearChip(key: string) {
  if (key === 'severity') severityFilter.value = ''
  else if (key === 'open') openFilter.value = false
  else if (key === 'asset') assetFilter.value = ''
  else statusFilter.value = ''
  applyFilter()
}

function resetFilters() {
  severityFilter.value = ''
  statusFilter.value = ''
  openFilter.value = false
  assetFilter.value = ''
  store.fetchList()
}

function applyFilter() {
  // status đơn lẻ ưu tiên hơn open (mutually-exclusive) — khớp BE _build_incident_filters.
  if (statusFilter.value) openFilter.value = false
  store.fetchList({
    severity: severityFilter.value || undefined,
    status: statusFilter.value || undefined,
    open: openFilter.value && !statusFilter.value ? 1 : undefined,
    asset: assetFilter.value || undefined,
  })
}

// Nhấp vào badge trong bảng → lọc ngay
function quickFilter(key: 'severity' | 'status', value: string) {
  if (!value) return
  if (key === 'severity') severityFilter.value = value
  else { statusFilter.value = value; openFilter.value = false }  // status đơn lẻ clear open
  showFilters.value = false
  applyFilter()
}

function goToPage(page: number) {
  store.fetchList({
    severity: severityFilter.value || undefined,
    status: statusFilter.value || undefined,
    open: openFilter.value && !statusFilter.value ? 1 : undefined,
    asset: assetFilter.value || undefined,
    page,
  })
}

onMounted(() => {
  // Core Doc §9.3 — pre-apply filter từ route.query (drill-down) trước khi fetch.
  if (applyQueryToFilters()) applyFilter()
  else store.fetchList()
  store.fetchStats()
})

// §9.3 — drill-down lần 2 (cùng route, query khác) → re-apply.
watch(
  () => route.query,
  () => { if (applyQueryToFilters()) applyFilter() },
)
</script>

<template>
  <!--
    AC-UX-047 (lô 1) — khuôn 4 trạng thái loại trừ (ui/ListPageShell). Dải KPI nằm ở
    `#summary` nên KHÔNG render ở trạng thái lỗi: số 0 tính từ tập rỗng là tín hiệu
    giả cùng lớp với lỗi-giả-dạng-rỗng.
  -->
  <ListPageShell
    :loading="store.loading"
    :error-message="store.error"
    :is-empty="!store.incidents.length"
    :empty-title="emptyTitle"
    :empty-hint="EMPTY_HINT"
    @retry="applyFilter">
    <template #header>
      <PageHeader
        title="Sự cố thiết bị"
        :subtitle="`Tổng ${store.pagination.total} sự cố`"
        :breadcrumb="[{ label: 'IMM-12 · Sự cố', to: '/incidents/dashboard' }, { label: 'Danh sách' }]"
      >
        <template #actions>
          <FilterToggleButton v-model="showFilters" :count="activeFilterCount" />
          <button v-if="can('corrective.create')" class="btn-primary" @click="router.push('/incidents/new')">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
            </svg>
            Báo cáo sự cố
          </button>
        </template>
      </PageHeader>
    </template>

    <template #summary>
      <WorkOrderKpiStrip :items="kpiItems" />
      <div class="flex items-center justify-between text-xs text-slate-500 pb-1">
        <span>Hiển thị <strong class="text-slate-700">{{ store.incidents.length }}</strong> / {{ store.pagination.total }} sự cố</span>
        <button v-if="activeFilterCount > 0" class="text-red-500 hover:text-red-700 font-medium" @click="resetFilters">Xóa tất cả</button>
      </div>
    </template>

    <template #filters>
      <ListFilterBar
      :show="showFilters"
      :chips="activeChips"
      :show-search="false"
      @reset="resetFilters"
      @clear-chip="clearChip"
      @apply="applyFilter"
    >
      <template #fields>
        <div class="form-group">
          <label class="form-label" for="ir-filter-severity">Mức độ</label>
          <select id="ir-filter-severity" v-model="severityFilter" class="form-select">
            <option v-for="s in SEVERITIES" :key="s.value" :value="s.value">{{ s.label }}</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label" for="ir-filter-status">Trạng thái</label>
          <select id="ir-filter-status" v-model="statusFilter" class="form-select">
            <option v-for="s in STATUSES" :key="s.value" :value="s.value">{{ s.label }}</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label" for="ir-filter-asset">Thiết bị</label>
          <input
            id="ir-filter-asset"
            v-model="assetFilter"
            class="form-input"
            placeholder="Mã thiết bị…"
          />
        </div>
      </template>
      </ListFilterBar>
    </template>

    <template #skeleton>
      <SkeletonLoader variant="table" :rows="6" />
    </template>

    <template #empty-action>
      <button v-if="activeFilterCount > 0" class="text-xs text-blue-500 hover:text-blue-700 underline" @click="resetFilters">
        Xóa bộ lọc để xem tất cả
      </button>
      <button v-else-if="can('corrective.create')" class="btn-ghost text-xs" @click="router.push('/incidents/new')">
        + Báo cáo sự cố đầu tiên
      </button>
    </template>

      <!-- Mobile cards (< sm) -->
      <div class="mobile-card-list sm:hidden">
        <div
          v-for="ir in store.incidents"
          :key="ir.name"
          class="mobile-card"
          @click="router.push(`/incidents/${ir.name}`)"
        >
          <div class="flex items-center justify-between mb-2">
            <span class="font-mono text-sm font-semibold text-brand-700">{{ ir.name }}</span>
            <button
              class="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium leading-none whitespace-nowrap"
              :class="incidentStatusClass(ir.status || '')"
              @click.stop="quickFilter('status', ir.status || '')"
            >
{{ incidentStatusLabel(ir.status || '') }}
</button>
          </div>
          <p class="text-sm font-medium text-slate-900 truncate">{{ ir.asset_name || ir.asset || '—' }}</p>
          <div class="flex flex-wrap items-center gap-x-2 gap-y-1 mt-1.5 text-xs text-slate-500">
            <button
              class="px-1.5 py-0.5 rounded text-[11px] font-medium"
              :class="SEV_COLOR[ir.severity] || 'bg-slate-100 text-slate-600'"
              @click.stop="quickFilter('severity', ir.severity)"
            >
{{ incidentSeverityLabel(ir.severity) }}
</button>
            <span class="text-slate-300">·</span>
            <span>{{ formatDateTime(ir.reported_at) }}</span>
            <span v-if="ir.patient_affected" class="text-red-600 font-semibold">BN: Có</span>
            <span v-if="ir.chronic_failure_flag" class="text-amber-600 font-semibold">Lặp lại</span>
            <SlaBreachBadge
              size="xs"
              :response-breached="ir.is_response_breached ?? ir.response_breached"
              :resolution-breached="ir.is_resolution_breached ?? ir.resolution_breached"
            />
          </div>
        </div>
      </div>

      <!-- Desktop table (sm+) -->
      <div class="hidden sm:block">
        <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-slate-100">
            <thead>
              <tr>
                <th class="table-header">Sự cố</th>
                <th class="table-header">Thiết bị</th>
                <th class="table-header">Mức độ</th>
                <th class="table-header">Trạng thái</th>
                <th class="table-header">Thời gian</th>
                <th class="table-header">BN</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              <tr
                v-for="ir in store.incidents" :key="ir.name"
                class="hover:bg-slate-50 cursor-pointer transition-colors"
                @click="router.push(`/incidents/${ir.name}`)"
              >
                <td class="table-cell">
                  <p class="font-medium text-slate-800 truncate max-w-xs">
                    {{ ir.description?.replace(/<[^>]+>/g, '').slice(0, 70) || '—' }}
                  </p>
                  <p class="font-mono text-xs text-slate-400 mt-0.5">{{ ir.name }}</p>
                </td>
                <td class="table-cell">
                  <div class="text-slate-700">{{ ir.asset_name || ir.asset || '—' }}</div>
                  <div v-if="ir.asset && ir.asset_name" class="text-xs text-slate-400 font-mono mt-0.5">{{ ir.asset }}</div>
                  <div v-if="ir.chronic_failure_flag" class="text-[11px] text-amber-600 font-semibold mt-0.5">⚠ Lặp lại (Chronic)</div>
                </td>
                <td class="table-cell">
                  <button
                    class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium transition-all hover:ring-2 hover:ring-offset-1 hover:ring-current/50"
                    :class="SEV_COLOR[ir.severity] || 'bg-slate-100 text-slate-600'"
                    @click.stop="quickFilter('severity', ir.severity)"
                  >
{{ incidentSeverityLabel(ir.severity) }}
</button>
                </td>
                <td class="table-cell">
                  <button
                    class="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium leading-none whitespace-nowrap transition-all hover:ring-2 hover:ring-offset-1 hover:ring-current/50"
                    :class="incidentStatusClass(ir.status || '')"
                    @click.stop="quickFilter('status', ir.status || '')"
                  >
{{ incidentStatusLabel(ir.status || '') }}
</button>
                  <div
                    v-if="(ir.is_response_breached ?? ir.response_breached) || (ir.is_resolution_breached ?? ir.resolution_breached)"
                    class="flex flex-wrap gap-1 mt-1"
                  >
                    <SlaBreachBadge
                      size="xs"
                      :response-breached="ir.is_response_breached ?? ir.response_breached"
                      :resolution-breached="ir.is_resolution_breached ?? ir.resolution_breached"
                    />
                  </div>
                </td>
                <td class="table-cell text-slate-500 text-xs whitespace-nowrap">{{ formatDateTime(ir.reported_at) }}</td>
                <td class="table-cell">
                  <span v-if="ir.patient_affected" class="text-xs font-semibold text-red-600">Có</span>
                  <span v-else class="text-xs text-slate-400">—</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

    <template #pagination>
      <BasePagination :pagination="store.pagination" @page-change="goToPage" />
    </template>
  </ListPageShell>
</template>
