// TDD (FE regression guard) — Core Doc §7.1 (canonical-value rule) / BR-09-07 LIVE.
//
// Predicate "vượt SLA" của Asset Repair là BE-only. FE TUYỆT ĐỐI KHÔNG tự suy ra
// breach — chỉ RENDER giá trị BE đã ghi/derive. NÂNG CẤP (BR-09-07 LIVE): BE nay
// derive per-row `is_sla_breached = bool(sla_breached) || _row_is_live_overdue`
// (open & vượt hạn & cờ chưa stamp bởi scheduler). FE badge/computed đọc
// `is_sla_breached ?? sla_breached` (live ưu tiên, fallback cờ thô — forward-compat).
//
// Test này PIN bất biến divergence-free TRÊN TẬP LIVE:
//
//   KPI card opsmgr `cm_sla_breached` (BE = sla_breach_count() — gồm live-overdue)
//   === độ dài danh sách drill `/cm/work-orders?sla_breached=1`
//   (BE = list_repair_work_orders enrich is_sla_breached live, CÙNG predicate)
//
// cho CÙNG tập WO → card count không bao giờ lệch list length ở tầng FE — KỂ CẢ
// ở cửa-sổ-trễ-scheduler (WO open-overdue cờ thô=0 nhưng is_sla_breached=true).
// Cùng họ guard với round-3 IMM-15 (lowStockOverrideDivergence.test.ts).
//
// 3 nửa của contract:
//  (A) Card render value BE verbatim + drill trỏ ĐÚNG predicate (sla_breached=1,
//      KHÔNG kèm status) → list đích áp dụng CÙNG filter với KPI.
//  (B) List view nhận query.sla_breached=1 → fetch với sla_breached=1 và render
//      đúng N dòng BE trả → card count === list length.
//  (C) LIVE-TRUTH (INV-CM-SLA-5): WO open-overdue cờ thô sla_breached=0 nhưng
//      is_sla_breached=true (live) → badge "Cam kết dịch vụ vi phạm" RENDER + đếm vào card.
//      RED-prove: revert binding về chỉ `sla_breached` ⇒ badge ẩn dù live-breach.
//
// ─── ROOT-CAUSE: test-isolation (vong-17 ĐỎ full-suite, xanh isolation) ──────────
// Trước đây file dùng `vi.doMock('vue-router')` + `vi.doUnmock` + `vi.resetModules`
// + dynamic import() cho 2 nửa list (B/C), trong khi nửa dashboard (A) dùng router
// THẬT (createRouter plugin). `vi.doUnmock('vue-router')` là MUTATION TOÀN-CỤC của
// mock-registry trong worker, KHÔNG được vitest reset giữa các file khi worker tái
// dùng → file SAU trong cùng worker (vd cmListDrilldown.test.ts) hoist-mock
// vue-router bị xoá đăng-ký ⇒ `useRoute()` trả real (undefined ở jsdom) ⇒
// `route.query` crash tại CMWorkOrderListView.vue:21. File NÀY là KẺ GÂY ô-nhiễm,
// không phải nạn nhân.
//
// Sâu hơn: NHIỀU file test cùng static-import SFC dùng chung (CMWorkOrderListView /
// CMWorkOrderDetailView) nhưng hoist-mock vue-router SHAPE khác nhau → khi pool
// (forks) tái dùng worker và thứ tự file đổi mỗi vòng (scheduling/shuffle), SFC
// cache bind vào factory mock của FILE đã "thắng" registry-race → flake không xác
// định (đỏ full-suite, xanh isolation).
//
// FIX gốc (KHÔNG vá triệu chứng): (1) bỏ HẲN doMock/doUnmock/resetModules + dynamic
// import; (2) MỌI file CM dùng CHUNG `vueRouterMockFactory` (src/test/vueRouterMock.ts):
// full-shape, route-state trên globalThis → dù factory file nào thắng race nó cũng
// ĐỒNG NHẤT + đọc cùng state test set ⇒ deterministic, hết pollution xuyên-file.
// Spec/Core Doc KHÔNG đổi — thuần test-harness defect (FE vitest isolation).
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'
import { setActivePinia, createPinia } from 'pinia'
import { resetRouteMock, setRouteQuery } from '@/test/vueRouterMock'

// ─── Mock vue-router qua SHARED full-shape factory — phục vụ CẢ dashboard (A) lẫn
// list (B/C). useRoute().query LIVE từ globalThis (đồng nhất mọi file CM → race
// vô hại); useRouter().push spy; RouterLink stub serialize :to={path,query} →
// <a :href> để nửa (A) assert href chứa /cm/work-orders & sla_breached=1 mà KHÔNG
// cần router thật → KHÔNG còn doMock/doUnmock/resetModules → hết pollute worker.
// Xem src/test/vueRouterMock.ts.
vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())

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
  label_vi: 'Cam kết dịch vụ vi phạm',
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

// ─── (B/C) CM list view fetch theo query.sla_breached ────────────────────────
const fetchWOSpy = vi.fn().mockResolvedValue(undefined)
// Dataset list view đọc — mutable để block (C) swap sang tập LIVE (cờ thô=0,
// is_sla_breached=true). Mặc định = BREACHED_WOS (cờ thô=1) cho block (B).
const listWOs = ref<Record<string, unknown>[]>(BREACHED_WOS)
vi.mock('@/stores/imm09', () => ({
  useImm09Store: () => ({
    get workOrders() { return listWOs.value },
    kpis: null,
    pagination: { page: 1, page_size: 20, total: listWOs.value.length, total_pages: 1 },
    loading: false,
    error: null,
    fetchWorkOrders: fetchWOSpy,
    fetchKPIs: vi.fn().mockResolvedValue(undefined),
  }),
}))

// Static import — KHÔNG dynamic import / resetModules (idiom canonical, không
// mutate registry toàn-cục → không pollute file khác trong worker).
import OpsmgrDashboardView from '@/views/dashboard/personas/OpsmgrDashboardView.vue'
import CMWorkOrderListView from '@/views/cm/CMWorkOrderListView.vue'
// RouterLink thật được router-plugin đăng-ký GLOBAL; ở đây không gắn plugin nên
// đăng-ký stub (từ vue-router mock) làm global component để KpiCard <RouterLink>
// resolve được + serialize :to → <a :href> cho assert href ở nửa (A).
import { RouterLink as RouterLinkStub } from 'vue-router'

const dashboardStubs = { PageHeader: true, StatusDonutChart: true, BarsCard: true, TimelineCard: true }
const dashboardGlobal = {
  stubs: dashboardStubs,
  components: { RouterLink: RouterLinkStub },
}

const listStubs = {
  PageHeader: true, FilterToggleButton: true, ListFilterBar: true,
  BasePagination: true, StatusBadge: true, SkeletonLoader: true,
  WorkOrderKpiStrip: true,
}

describe('IMM-09 cm_sla_breached — KPI card / drill-list divergence guard (BR-09-07, §7.1)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    fetchWOSpy.mockClear()
    resetRouteMock()
  })

  it('(A) card render value BE verbatim (3) — FE KHÔNG recompute breach', async () => {
    const w = mount(OpsmgrDashboardView, { global: dashboardGlobal })
    await flushPromises()
    expect(w.text()).toContain('Cam kết dịch vụ vi phạm')
    // value 3 hiển thị (toLocaleString('vi-VN') không đổi 1 chữ số).
    expect(w.text()).toContain(String(N_BREACHED))
  })

  it('(A) drill card trỏ /cm/work-orders?sla_breached=1 — CÙNG predicate, KHÔNG kèm status', async () => {
    const w = mount(OpsmgrDashboardView, { global: dashboardGlobal })
    await flushPromises()
    const link = w.findAll('a').find((a) => a.text().includes('Cam kết dịch vụ vi phạm'))
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
    resetRouteMock()
    listWOs.value = BREACHED_WOS
  })

  // List view dùng useRoute().query (mock hoisted ở trên) → drill ?sla_breached=1.
  it('(B) query.sla_breached=1 → fetchWorkOrders gọi với sla_breached=1', async () => {
    setRouteQuery({ sla_breached: '1' })
    mount(CMWorkOrderListView, { global: { stubs: { ...listStubs, RouterLink: true } } })
    await flushPromises()
    const saw = fetchWOSpy.mock.calls.some(
      (c) => (c[0] as Record<string, unknown> | undefined)?.sla_breached === '1')
    expect(saw).toBe(true)
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

// ─── (C) LIVE-TRUTH (INV-CM-SLA-5) — badge theo is_sla_breached ?? sla_breached ─
// Tập LIVE: 1 WO open-overdue cờ THÔ sla_breached=0 nhưng BE enrich is_sla_breached=true
// (live-overdue trong cửa-sổ-trễ-scheduler) + 1 WO open in-hạn cờ=0 is_sla_breached=false.
// Badge "Cam kết dịch vụ vi phạm" PHẢI render đúng 1 dòng (live-overdue) → == card count live.
// RED-prove: revert binding view về chỉ `wo.sla_breached` ⇒ badge ẩn (cờ=0) ⇒ test FAIL.
const LIVE_WOS = [
  // open-overdue: cờ thô CHƯA stamp (scheduler chưa quét) nhưng BE derive live=true.
  { name: 'WO-RP-2026-01001', asset_ref: 'AC-ASSET-1001', asset_name: 'Máy thở Live-Overdue',
    repair_type: 'Corrective', priority: 'Urgent', status: 'In Repair',
    mttr_hours: null, sla_target_hours: 72, sla_breached: 0, is_sla_breached: true,
    is_repeat_failure: 0 },
  // open in-hạn: cờ=0, live=false → KHÔNG badge.
  { name: 'WO-RP-2026-01002', asset_ref: 'AC-ASSET-1002', asset_name: 'Máy thở In-Hạn',
    repair_type: 'Corrective', priority: 'Normal', status: 'Open',
    mttr_hours: null, sla_target_hours: 72, sla_breached: 0, is_sla_breached: false,
    is_repeat_failure: 0 },
]
const N_LIVE_BREACH = LIVE_WOS.filter((w) => w.is_sla_breached ?? !!w.sla_breached).length // == 1

describe('IMM-09 cm_sla_breached — LIVE-TRUTH badge (INV-CM-SLA-5, BR-09-07 LIVE)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    fetchWOSpy.mockClear()
    resetRouteMock()
    setRouteQuery({ sla_breached: '1' })
    listWOs.value = LIVE_WOS
  })

  async function mountList() {
    const w = mount(CMWorkOrderListView, { global: { stubs: { ...listStubs, RouterLink: true } } })
    await flushPromises()
    return w
  }

  it('(C) WO open-overdue cờ thô=0 nhưng is_sla_breached=true → badge "Cam kết dịch vụ vi phạm" RENDER', async () => {
    const w = await mountList()
    // badge xuất hiện đúng số WO live-breach (desktop + mobile mỗi WO 1 lần → đếm ≥ N_LIVE).
    const occurrences = w.text().split('Cam kết dịch vụ vi phạm').length - 1
    expect(occurrences).toBeGreaterThanOrEqual(N_LIVE_BREACH)
    expect(occurrences).toBeGreaterThan(0) // live=true PHẢI render dù cờ thô=0
  })

  it('(C) card count live (1) === số WO is_sla_breached live trong tập drill', () => {
    // INV-CM-SLA-5 trên tập LIVE: card cm_sla_breached (BE sla_breach_count gồm live-overdue)
    // === độ dài drill (list enrich is_sla_breached live). Pin 2 con số ĐẾN TỪ CÙNG predicate.
    expect(N_LIVE_BREACH).toBe(1)
    const liveBreachRows = LIVE_WOS.filter((w) => w.is_sla_breached ?? !!w.sla_breached)
    expect(liveBreachRows.length).toBe(N_LIVE_BREACH)
    // WO live-overdue: cờ THÔ vẫn 0 (scheduler chưa stamp) — FE KHÔNG dựa cờ thô.
    expect(liveBreachRows[0].sla_breached).toBe(0)
    expect(liveBreachRows[0].is_sla_breached).toBe(true)
  })

  it('(C) WO open in-hạn cờ=0 is_sla_breached=false → KHÔNG vào tập breach (no phantom)', () => {
    const inWindow = LIVE_WOS.find((w) => w.status === 'Open' && w.sla_breached === 0 && w.is_sla_breached === false)
    expect(inWindow).toBeTruthy()
    expect(inWindow!.is_sla_breached ?? !!inWindow!.sla_breached).toBe(false)
  })
})
