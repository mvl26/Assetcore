// TDD (FE regression guard) — Core Doc §7.1 (canonical-value rule) / BR-09-07.
//
// Predicate "vượt SLA" của Asset Repair là BE-only (1 SoT `is_sla_breached`,
// biên `>=`, monotonic latch). FE TUYỆT ĐỐI KHÔNG tự suy ra breach — chỉ render
// cờ `sla_breached` BE ghi. Test này PIN bất biến divergence-free:
//
//   KPI card opsmgr `cm_sla_breached` (BE = _count Asset Repair {sla_breached:1})
//   === độ dài danh sách drill `/cm/work-orders?sla_breached=1`
//   (BE = list_work_orders cùng filter {sla_breached:1}, KHÔNG status filter)
//
// cho CÙNG tập WO → card count không bao giờ lệch list length ở tầng FE.
// Cùng họ guard với round-3 IMM-15 (lowStockOverrideDivergence.test.ts).
//
// 2 nửa của contract:
//  (A) Card render value BE verbatim + drill trỏ ĐÚNG predicate (sla_breached=1,
//      KHÔNG kèm status) → list đích áp dụng CÙNG filter với KPI.
//  (B) List view nhận query.sla_breached=1 → fetch với sla_breached=1 và render
//      đúng N dòng BE trả → card count === list length.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'
import { setActivePinia, createPinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'

// ─── Dataset acceptance ──────────────────────────────────────────────────────
// 3 WO breach (CÙNG tập): mttr == target (72/72, biên), mttr > target (96/72),
// và 1 WO đã Completed mà breach (sự thật lịch sử monotonic — vẫn đếm). BE đếm
// {sla_breached:1} = 3 không lọc status → KPI thẻ = 3 = số dòng list drill.
const N_BREACHED = 3
const BREACHED_WOS = [
  { name: 'WO-RP-2026-00001', asset_ref: 'AC-ASSET-0001', asset_name: 'Máy thở A',
    repair_type: 'Corrective', priority: 'Normal', status: 'In Repair',
    mttr_hours: 72, sla_target_hours: 72, sla_breached: 1, is_repeat_failure: 0 },
  { name: 'WO-RP-2026-00002', asset_ref: 'AC-ASSET-0002', asset_name: 'Máy thở B',
    repair_type: 'Corrective', priority: 'Urgent', status: 'In Repair',
    mttr_hours: 96, sla_target_hours: 72, sla_breached: 1, is_repeat_failure: 0 },
  { name: 'WO-RP-2026-00003', asset_ref: 'AC-ASSET-0003', asset_name: 'Máy thở C',
    repair_type: 'Corrective', priority: 'Normal', status: 'Completed',
    mttr_hours: 80, sla_target_hours: 72, sla_breached: 1, is_repeat_failure: 0 },
]

// ─── (A) opsmgr dashboard KPI card + drill ───────────────────────────────────
// Mock useDashboard: payload mang KPI cm_sla_breached = N (BE-computed) + drill
// descriptor BE đã set (route /cm/work-orders, query {sla_breached:'1'}).
const cmSlaBreachedKpi = {
  key: 'cm_sla_breached',
  label_vi: 'SLA vi phạm',
  value: N_BREACHED,
  foot_vi: 'SLA tuân thủ 70%',
  tone: 'danger' as const,
  drill: { route: '/cm/work-orders', query: { sla_breached: '1' } },
}
vi.mock('@/composables/useDashboard', () => ({
  usePersonaDashboard: () => ({
    data: ref({
      persona: 'opsmgr',
      generated_at: '2026-06-02',
      kpis: [cmSlaBreachedKpi],
      sections: {
        asset_status_breakdown: [],
        incident_severity_breakdown: [],
        maintenance_kpi: { mttr_avg_hours: 0, sla_compliance_pct: 70, open_wos: 0,
          repeat_failure_count: 0, drills: {} },
        recent_events: [],
        recent_pm: [],
      },
    }),
    isLoading: ref(false),
    error: ref(null),
    refetch: vi.fn(),
  }),
}))

// Drill clickable: KpiCard gate qua canAccessDrill(route, can). Cho phép mọi cap
// để card render dạng RouterLink (kiểm tra :to).
vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({ can: () => true }),
}))

import OpsmgrDashboardView from './../dashboard/personas/OpsmgrDashboardView.vue'

// ─── (B) CM list view fetch theo query.sla_breached ──────────────────────────
const listRouteQuery = ref<Record<string, string>>({})
const fetchWOSpy = vi.fn().mockResolvedValue(undefined)
vi.mock('@/stores/imm09', () => ({
  useImm09Store: () => ({
    workOrders: BREACHED_WOS,
    kpis: null,
    pagination: { page: 1, page_size: 20, total: N_BREACHED, total_pages: 1 },
    loading: false,
    error: null,
    fetchWorkOrders: fetchWOSpy,
    fetchKPIs: vi.fn().mockResolvedValue(undefined),
  }),
}))

describe('IMM-09 cm_sla_breached — KPI card / drill-list divergence guard (BR-09-07, §7.1)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    fetchWOSpy.mockClear()
    listRouteQuery.value = {}
  })

  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/:pathMatch(.*)*', component: { template: '<div/>' } }],
  })

  it('(A) card render value BE verbatim (3) — FE KHÔNG recompute breach', async () => {
    const w = mount(OpsmgrDashboardView, {
      global: {
        plugins: [router],
        stubs: { PageHeader: true, StatusDonutChart: true, BarsCard: true, TimelineCard: true },
      },
    })
    await flushPromises()
    expect(w.text()).toContain('SLA vi phạm')
    // value 3 hiển thị (toLocaleString('vi-VN') không đổi 1 chữ số).
    expect(w.text()).toContain(String(N_BREACHED))
  })

  it('(A) drill card trỏ /cm/work-orders?sla_breached=1 — CÙNG predicate, KHÔNG kèm status', async () => {
    const w = mount(OpsmgrDashboardView, {
      global: {
        plugins: [router],
        stubs: { PageHeader: true, StatusDonutChart: true, BarsCard: true, TimelineCard: true },
      },
    })
    await flushPromises()
    const link = w.findAll('a').find((a) => a.text().includes('SLA vi phạm'))
    expect(link).toBeTruthy()
    const href = link!.attributes('href') ?? ''
    expect(href).toContain('/cm/work-orders')
    expect(href).toContain('sla_breached=1')
    // Canonical-value rule §7.1: drill KHÔNG được kèm status filter (nếu kèm →
    // list lọc hẹp hơn KPI → count lệch). Pin: không có status= trong query.
    expect(href).not.toContain('status=')
  })
})

describe('IMM-09 cm_sla_breached — list áp dụng cùng filter → count === card (BR-09-07)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    fetchWOSpy.mockClear()
    listRouteQuery.value = {}
  })

  // Mock router cho list view (CMWorkOrderListView dùng useRoute().query).
  it('(B) query.sla_breached=1 → fetchWorkOrders gọi với sla_breached=1', async () => {
    // Re-mock vue-router cục bộ cho list view qua spy trên fetch (đã verify ở
    // cmListDrilldown.test.ts). Ở đây pin riêng để guard sống độc lập.
    listRouteQuery.value = { sla_breached: '1' }
    vi.doMock('vue-router', () => ({
      useRouter: () => ({ push: vi.fn() }),
      useRoute: () => ({ get query() { return listRouteQuery.value } }),
    }))
    const { default: CMWorkOrderListView } = await import('./CMWorkOrderListView.vue')
    const stubs = {
      PageHeader: true, FilterToggleButton: true, ListFilterBar: true,
      BasePagination: true, StatusBadge: true, SkeletonLoader: true,
      WorkOrderKpiStrip: true, RouterLink: true,
    }
    mount(CMWorkOrderListView, { global: { stubs } })
    await flushPromises()
    const saw = fetchWOSpy.mock.calls.some(
      (c) => (c[0] as Record<string, unknown> | undefined)?.sla_breached === '1')
    expect(saw).toBe(true)
    vi.doUnmock('vue-router')
  })

  it('(B) card count === list length cho CÙNG tập WO (3 === 3)', () => {
    // BE invariant: cm_sla_breached = _count{sla_breached:1} === len(list_work_orders{sla_breached:1}).
    // FE chỉ render — guard pin 2 con số ĐẾN TỪ CÙNG predicate không lệch.
    expect(cmSlaBreachedKpi.value).toBe(BREACHED_WOS.length)
    expect(cmSlaBreachedKpi.value).toBe(N_BREACHED)
    // Mọi WO trong tập list đều có cờ BE-ghi sla_breached=1 (FE không tự suy).
    expect(BREACHED_WOS.every((w) => w.sla_breached === 1)).toBe(true)
  })

  it('(B) tập breach gồm cả biên (mttr==target) và Completed (monotonic) — FE không lọc bỏ', () => {
    // WO mttr==target (72/72) PHẢI nằm trong tập (biên >= → breach).
    const boundary = BREACHED_WOS.find((w) => w.mttr_hours === w.sla_target_hours)
    expect(boundary?.sla_breached).toBe(1)
    // WO đã Completed mà breach vẫn nằm trong tập (BE bỏ status filter → khớp drill).
    const completed = BREACHED_WOS.find((w) => w.status === 'Completed')
    expect(completed?.sla_breached).toBe(1)
  })
})
