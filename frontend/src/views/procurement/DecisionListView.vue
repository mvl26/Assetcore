<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute, type LocationQueryRaw } from 'vue-router'
import { useImm03Store } from '@/stores/imm03'
import type { DecisionState } from '@/types/imm03'
import { stateLabel, formatVnd } from '@/utils/wave2Labels'
import PageHeader from '@/components/common/PageHeader.vue'
import FilterToggleButton from '@/components/common/FilterToggleButton.vue'
import ListFilterBar, { type FilterChip } from '@/components/common/ListFilterBar.vue'
import KpiCard from '@/components/common/KpiCard.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'

const router = useRouter()
const route  = useRoute()
const store  = useImm03Store()

const DECISION_STATES: DecisionState[] = [
  'Draft', 'Method Selected', 'Negotiation', 'Award Recommended',
  'Pending Approval', 'Awarded', 'Contract Signed', 'PO Issued', 'Cancelled',
]

// Canonical query param 'state' ↔ filters.workflow_state (precedent AssetListView §9.3).
// Chỉ 3 state có tile-drill được phép deep-link (shareable + refresh-safe). State lạ
// → bỏ qua an toàn (load all, no tile pressed). URL chỉ chứa code chuẩn (KHÔNG nhãn VI).
const URL_DRILL_STATES: DecisionState[] = ['Awarded', 'Pending Approval', 'PO Issued']
const ENVELOPE_BUCKETS = [
  { value: 'within',  label: 'Trong ngân sách (≤ 90%)' },
  { value: 'tight',   label: 'Sát ngân sách (90–105%)' },
  { value: 'over',    label: 'Vượt ngân sách (> 105%)' },
] as const
type EnvBucket = typeof ENVELOPE_BUCKETS[number]['value']

const showFilters = ref(false)
const filters = reactive<{
  workflow_state: DecisionState | ''
  winner_supplier: string
  spec_ref: string
  envelope_bucket: EnvBucket | ''
  search: string
}>({
  workflow_state: '',
  winner_supplier: '',
  spec_ref: '',
  envelope_bucket: '',
  search: '',
})

const activeChips = computed<FilterChip[]>(() => {
  const c: FilterChip[] = []
  if (filters.workflow_state)   c.push({ key: 'workflow_state', label: stateLabel(filters.workflow_state) })
  if (filters.winner_supplier)  c.push({ key: 'winner_supplier', label: `Nhà cung cấp: ${filters.winner_supplier}` })
  if (filters.spec_ref)         c.push({ key: 'spec_ref', label: `Hồ sơ: ${filters.spec_ref}` })
  if (filters.envelope_bucket) {
    const b = ENVELOPE_BUCKETS.find(x => x.value === filters.envelope_bucket)
    c.push({ key: 'envelope_bucket', label: b?.label ?? filters.envelope_bucket })
  }
  if (filters.search.trim())    c.push({ key: 'search', label: `"${filters.search.trim()}"` })
  return c
})

function buildPayload(): Record<string, unknown> {
  const f: Record<string, unknown> = {}
  if (filters.workflow_state)  f.workflow_state = filters.workflow_state
  if (filters.winner_supplier) f.winner_supplier = filters.winner_supplier
  if (filters.spec_ref)        f.spec_ref = filters.spec_ref
  if (filters.search.trim())   f.search = filters.search.trim()
  return f
}
function applyFilters() { store.fetchDecisions(buildPayload()) }
function resetFilters() {
  filters.workflow_state = ''
  filters.winner_supplier = ''
  filters.spec_ref = ''
  filters.envelope_bucket = ''
  filters.search = ''
  syncStateToUrl('')  // xoá ?state khỏi URL
  store.fetchDecisions()
}
function clearChip(key: string) {
  ;(filters as Record<string, string>)[key] = ''
  if (key === 'workflow_state') syncStateToUrl('')
  applyFilters()
}
function quickFilter(key: keyof typeof filters, value: string) {
  ;(filters as Record<string, string>)[key] = value
  if (key === 'workflow_state') syncStateToUrl(value)
  showFilters.value = false
  applyFilters()
}

// KPI tile drill (INV card==drill): click tile → lọc workflow_state = state;
// click lại tile đang active → bỏ lọc (toggle). Value=0 vẫn click được (list rỗng).
function toggleStateFilter(state: DecisionState) {
  const next = filters.workflow_state === state ? '' : state
  filters.workflow_state = next
  syncStateToUrl(next)
  showFilters.value = false
  applyFilters()
}
function isActiveState(state: DecisionState): boolean {
  return filters.workflow_state === state
}

// ── URL sync (deep-link/refresh-safe/shareable) ───────────────────────────────
// Phản ánh filters.workflow_state vào ?state qua router.replace (KHÔNG đẩy history
// rác). URL chỉ chứa code canonical; xoá key state khi clear/toggle-off.
// `selfNav` đánh dấu thay đổi URL do CHÍNH view gây ra → watch bỏ qua (tránh
// double-fetch); chỉ navigation NGOÀI (drill lần 2 từ nơi khác) mới re-apply.
let selfNav = false
function syncStateToUrl(state: string) {
  const query: LocationQueryRaw = { ...route.query }
  if (state) query.state = state
  else delete query.state
  selfNav = true
  router.replace({ query })
}

// Đọc ?state → áp vào filters + fetch. State hợp lệ (∈ URL_DRILL_STATES) → set
// filter + fetch có filter; state lạ/rỗng → bỏ qua an toàn (load all, no tile).
// `force=false` (từ watch): bỏ qua nếu filter đã khớp URL — tránh double-fetch khi
// chính các hàm filter của view đã đẩy state lên URL (toggle/quick/reset gọi fetch
// trực tiếp). `force=true` (onMounted): luôn fetch lần đầu (deep-link/refresh).
function applyQueryToFilters(force = false) {
  const raw = route.query.state
  const val = Array.isArray(raw) ? raw[0] : raw
  const next = (typeof val === 'string' && (URL_DRILL_STATES as string[]).includes(val))
    ? (val as DecisionState)
    : ''
  if (!force && next === filters.workflow_state) return  // đã đồng bộ — no-op
  filters.workflow_state = next
  if (next) store.fetchDecisions(buildPayload())
  else store.fetchDecisions()  // load all (no filter)
}

const filteredDecisions = computed(() => {
  if (!filters.envelope_bucket) return store.decisions
  return store.decisions.filter(d => {
    const v = d.envelope_check_pct ?? 0
    if (filters.envelope_bucket === 'within') return v > 0 && v <= 90
    if (filters.envelope_bucket === 'tight')  return v > 90 && v <= 105
    if (filters.envelope_bucket === 'over')   return v > 105
    return true
  })
})

// INV card==drill: số hiển thị bám `total` server-side (== tile) khi không có
// bộ lọc client envelope_bucket. envelope_bucket lọc thuần FE → dùng độ dài đã lọc.
const displayCount = computed(() =>
  filters.envelope_bucket ? filteredDecisions.value.length : store.decisionTotal,
)

function envClass(pct?: number): string {
  if (pct == null) return ''
  if (pct > 105) return 'over'
  if (pct > 90)  return 'warn'
  return 'ok'
}

function goDetail(n: string) { router.push({ name: 'ProcurementDecisionDetail', params: { id: n } }) }

onMounted(() => { applyQueryToFilters(true); store.fetchKpis() })

// Drill lần 2 cùng route (?state khác) → re-apply filter không cần reload trang
// (parity AssetListView watch route.query). Chỉ theo dõi key 'state' canonical.
// Bỏ qua thay đổi URL do chính view đẩy lên (selfNav) — đã fetch trực tiếp rồi.
watch(() => route.query.state, () => {
  if (selfNav) { selfNav = false; return }
  applyQueryToFilters()
})
</script>

<template>
  <div class="page-container animate-fade-in">
    <PageHeader
      title="Quyết định mua sắm"
      :subtitle="`Tổng ${store.decisionTotal} quyết định — trao thầu, ký hợp đồng, phát hành đơn hàng.`"
    >
      <template #actions>
        <FilterToggleButton v-model="showFilters" :count="activeChips.length" />
      </template>
    </PageHeader>

    <ListFilterBar
      v-model:search="filters.search"
      :show="showFilters"
      :chips="activeChips"
      search-placeholder="Tìm theo mã quyết định, mã hồ sơ hoặc tên NCC..."
      @apply="applyFilters"
      @reset="resetFilters"
      @clear-chip="clearChip"
    >
      <template #fields>
        <select v-model="filters.workflow_state" class="form-select text-sm" @change="applyFilters">
          <option value="">Tất cả trạng thái</option>
          <option v-for="s in DECISION_STATES" :key="s" :value="s">{{ stateLabel(s) }}</option>
        </select>
        <select v-model="filters.envelope_bucket" class="form-select text-sm" @change="applyFilters">
          <option value="">Tất cả mức ngân sách</option>
          <option v-for="b in ENVELOPE_BUCKETS" :key="b.value" :value="b.value">{{ b.label }}</option>
        </select>
      </template>
    </ListFilterBar>

    <div v-if="store.kpis" class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
      <button
        type="button"
        class="kpi-drill text-left rounded-[10px] cursor-pointer transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-1"
        :class="isActiveState('Awarded') ? 'ring-2 ring-brand-500 ring-offset-1' : 'hover:ring-2 hover:ring-brand-300'"
        role="button"
        :aria-pressed="isActiveState('Awarded')"
        aria-label="Lọc quyết định đã trao thầu"
        :title="isActiveState('Awarded') ? 'Bấm lại để bỏ lọc' : 'Bấm để lọc: Đã trao thầu'"
        @click="toggleStateFilter('Awarded')"
      >
        <KpiCard label="Đã trao thầu" :value="store.kpis.decision_states['Awarded'] || 0" color="success" />
      </button>
      <button
        type="button"
        class="kpi-drill text-left rounded-[10px] cursor-pointer transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-1"
        :class="isActiveState('Pending Approval') ? 'ring-2 ring-brand-500 ring-offset-1' : 'hover:ring-2 hover:ring-brand-300'"
        role="button"
        :aria-pressed="isActiveState('Pending Approval')"
        aria-label="Lọc quyết định chờ phê duyệt"
        :title="isActiveState('Pending Approval') ? 'Bấm lại để bỏ lọc' : 'Bấm để lọc: Chờ phê duyệt'"
        @click="toggleStateFilter('Pending Approval')"
      >
        <KpiCard
          label="Chờ phê duyệt"
          :value="store.kpis.decision_states['Pending Approval'] || 0"
          :color="(store.kpis.decision_states['Pending Approval'] || 0) > 0 ? 'warning' : 'neutral'"
        />
      </button>
      <button
        type="button"
        class="kpi-drill text-left rounded-[10px] cursor-pointer transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-1"
        :class="isActiveState('PO Issued') ? 'ring-2 ring-brand-500 ring-offset-1' : 'hover:ring-2 hover:ring-brand-300'"
        role="button"
        :aria-pressed="isActiveState('PO Issued')"
        aria-label="Lọc quyết định đã phát hành đơn hàng"
        :title="isActiveState('PO Issued') ? 'Bấm lại để bỏ lọc' : 'Bấm để lọc: Đã phát hành đơn hàng'"
        @click="toggleStateFilter('PO Issued')"
      >
        <KpiCard
          label="Đã phát hành đơn hàng"
          :value="store.kpis.decision_states['PO Issued'] || 0"
          color="primary"
        />
      </button>
    </div>

    <div v-if="store.error" class="alert-error mb-4">
      <strong>Lỗi:</strong> {{ store.error }}
      <button class="alert-close" @click="store.clearError()">×</button>
    </div>

    <div class="card overflow-hidden">
      <div class="flex items-center justify-between px-4 py-3 border-b border-slate-100 bg-slate-50/60">
        <span class="text-xs text-slate-500">
          <span v-if="activeChips.length > 0">Kết quả lọc: <strong class="text-slate-700">{{ displayCount }}</strong> quyết định</span>
          <span v-else>Hiển thị <strong class="text-slate-700">{{ displayCount }}</strong> quyết định</span>
        </span>
        <button v-if="activeChips.length > 0" class="text-xs text-red-500 hover:text-red-700 font-medium" @click="resetFilters">Xóa tất cả</button>
      </div>

      <div v-if="store.loading" class="p-6 text-sm text-slate-500">Đang tải...</div>
      <template v-else-if="filteredDecisions.length">
        <!-- Mobile cards -->
        <div class="mobile-card-list sm:hidden">
          <div
            v-for="d in filteredDecisions"
            :key="d.name"
            class="mobile-card"
            @click="goDetail(d.name)"
          >
            <div class="flex items-center justify-between mb-2">
              <span class="font-mono text-sm font-semibold text-brand-700">{{ d.name }}</span>
              <StatusBadge :state="d.workflow_state" />
            </div>
            <p class="text-sm font-medium text-slate-900 truncate">{{ d.vendor_name || d.winner_supplier || d.spec_ref }}</p>
            <div class="flex flex-wrap gap-x-2 gap-y-1 mt-1.5 text-xs text-slate-500">
              <span>{{ d.spec_ref }}</span>
              <span>· {{ formatVnd(d.awarded_price) }}</span>
              <span v-if="d.envelope_check_pct">· <span :class="envClass(d.envelope_check_pct)">{{ d.envelope_check_pct.toFixed(1) }}%</span></span>
            </div>
          </div>
          <div v-if="filteredDecisions.length === 0" class="py-12 text-center text-slate-400">
            <p class="text-sm">Không có dữ liệu</p>
          </div>
        </div>

        <!-- Desktop table -->
        <div class="hidden sm:block overflow-x-auto">
          <table class="data-table">
            <thead>
              <tr>
                <th>Mã quyết định</th>
                <th>Hồ sơ kỹ thuật</th>
                <th>Nhà cung cấp trúng thầu</th>
                <th class="num">Giá trúng thầu</th>
                <th class="num">So với ngân sách</th>
                <th>Đơn hàng đã tạo</th>
                <th>Trạng thái</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="(d, idx) in filteredDecisions" :key="d.name"
                class="clickable animate-fade-in"
                :class="[`stagger-${Math.min(idx + 1, 8)}`]"
                @click="goDetail(d.name)"
              >
                <td><span class="font-mono text-xs bg-slate-100 px-1.5 py-0.5 rounded text-slate-700">{{ d.name }}</span></td>
                <td>
                  <button v-if="d.spec_ref" class="link-cell" :title="`Lọc: ${d.spec_ref}`" @click.stop="quickFilter('spec_ref', d.spec_ref)">
                    {{ d.spec_ref }}
                  </button>
                  <span v-else class="text-slate-400">—</span>
                </td>
                <td>
                  <button
  v-if="d.winner_supplier" class="link-cell"
                          :title="`Lọc: ${d.winner_supplier}`"
                          @click.stop="quickFilter('winner_supplier', d.winner_supplier)">
                    {{ d.vendor_name || d.winner_supplier }}
                  </button>
                  <span v-else class="text-slate-400">—</span>
                </td>
                <td class="num">{{ formatVnd(d.awarded_price) }}</td>
                <td class="num">
                  <span :class="envClass(d.envelope_check_pct)">
                    {{ d.envelope_check_pct ? d.envelope_check_pct.toFixed(1) + '%' : '—' }}
                  </span>
                </td>
                <td>
                  <span v-if="d.ac_purchase_ref">{{ (d as any).ac_purchase_ref_name || d.ac_purchase_ref }}</span>
                  <span v-else class="text-slate-400">—</span>
                </td>
                <td>
                  <button
  type="button" class="pill-btn"
                          :title="`Lọc trạng thái: ${stateLabel(d.workflow_state)}`"
                          @click.stop="quickFilter('workflow_state', d.workflow_state)">
                    <StatusBadge :state="d.workflow_state" />
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
      <div v-else class="flex flex-col items-center justify-center py-16 text-slate-400">
        <p class="text-sm">Không có quyết định mua sắm phù hợp</p>
        <button v-if="activeChips.length > 0" class="mt-3 text-xs text-blue-500 hover:text-blue-700 underline" @click="resetFilters">
          Xóa bộ lọc để xem tất cả
        </button>
      </div>
    </div>
  </div>
</template>

<!-- styles trong list-view.css -->
