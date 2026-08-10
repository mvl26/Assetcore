// TDD/regression — IMM-03 DecisionListView KPI tile → drill (INVARIANT card==drill).
//
// Hợp đồng FE: 3 KPI tile ("Đã trao thầu" / "Chờ phê duyệt" / "Đã phát hành đơn
// hàng") là affordance click → lọc list theo workflow_state tương ứng. Click tile
// gọi store.fetchDecisions({workflow_state: <state>}) ĐÚNG giá trị BE; click tile
// đang active (toggle) → bỏ lọc, fetchDecisions() không filter. Tile value=0 vẫn
// click được, list rỗng + empty-state, KHÔNG lỗi. KHÔNG leak nhãn EN.
//
// Map nhãn↔state (khớp wave2Labels.stateLabel + BE workflow_state):
//   'Đã trao thầu'            → Awarded
//   'Chờ phê duyệt'           → Pending Approval
//   'Đã phát hành đơn hàng'   → PO Issued
import { describe, it, expect, vi, beforeEach, afterEach, type MockInstance } from 'vitest'
import { reactive } from 'vue'
import { mount, flushPromises, enableAutoUnmount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import type { DashboardKpis, DecisionListItem } from '@/types/imm03'

// URL-sync watch theo dõi `mockRoute` (module-level, dùng chung): nếu component
// các test trước KHÔNG unmount, watcher cũ vẫn fire khi mockRoute đổi → nhiễu
// fetchSpy giữa các test. Auto-unmount sau mỗi test để cách ly sạch.
enableAutoUnmount(afterEach)

// ─── API mocks ──────────────────────────────────────────────────────────────
// listDecisions resolve theo filters để total/items phản ánh state; getDashboardKpis
// trả decision_states cho 3 tile (gồm 1 state value=0 để test TC-FE-03-TILE-04).
const listDecisionsSpy = vi.fn()
const getKpisSpy = vi.fn()

vi.mock('@/api/imm03', () => ({
  listDecisions: (...a: unknown[]) => listDecisionsSpy(...a),
  getDashboardKpis: () => getKpisSpy(),
}))

// ─── router mock (URL sync) ───────────────────────────────────────────────────
// route.query phải REACTIVE để watch(route.query.state) re-fire khi đổi (drill lần 2).
// router.replace là spy ổn định để assert canonical query (TC-03-URL-02/03).
const mockRoute = reactive<{ query: Record<string, unknown> }>({ query: {} })
const routerReplaceSpy = vi.fn((loc: { query?: Record<string, unknown> }) => {
  // mô phỏng router thật: cập nhật route.query để watch re-fire (drill lần 2)
  mockRoute.query = { ...(loc.query ?? {}) }
  return Promise.resolve()
})
const routerPushSpy = vi.fn()

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: routerPushSpy, back: vi.fn(), replace: routerReplaceSpy }),
  useRoute: () => mockRoute,
}))

import DecisionListView from './DecisionListView.vue'
import { useImm03Store } from '@/stores/imm03'

const KPIS: DashboardKpis = {
  eval_states: {},
  decision_states: {
    'Awarded': 5,
    'Pending Approval': 3,
    'PO Issued': 0,  // value=0 — vẫn click được (TC-FE-03-TILE-04)
  },
  avl_active: 0,
  avl_expiring_30d: 0,
} as unknown as DashboardKpis

function makeDecisions(state: string, n: number): DecisionListItem[] {
  return Array.from({ length: n }, (_, i) => ({
    name: `PD-${state}-${i}`,
    spec_ref: `TS-${i}`,
    winner_supplier: '',
    workflow_state: state,
    creation: '2026-06-01',
  } as unknown as DecisionListItem))
}

// Tổng theo state khớp tile (INV card==drill): Awarded=5, Pending=3, PO Issued=0.
const TOTAL_BY_STATE: Record<string, number> = {
  'Awarded': 5, 'Pending Approval': 3, 'PO Issued': 0,
}

function resolveList(args: unknown[]) {
  const filters = (args[0] ?? {}) as Record<string, unknown>
  const st = filters.workflow_state as string | undefined
  if (st) {
    const total = TOTAL_BY_STATE[st] ?? 0
    return Promise.resolve({ items: makeDecisions(st, total), total })
  }
  // không filter → "full" list (5+3+0)
  const all = [...makeDecisions('Awarded', 5), ...makeDecisions('Pending Approval', 3)]
  return Promise.resolve({ items: all, total: all.length })
}

const stubs = { teleport: true, PageHeader: true, FilterToggleButton: true, ListFilterBar: true }

async function mountView(query: Record<string, unknown> = {}) {
  mockRoute.query = { ...query }
  const wrapper = mount(DecisionListView, { global: { stubs } })
  await flushPromises()
  return wrapper
}

function tileButton(wrapper: Awaited<ReturnType<typeof mountView>>, ariaLabel: string) {
  return wrapper.findAll('button').find(b => b.attributes('aria-label') === ariaLabel)
}

describe('IMM-03 DecisionListView — KPI tile drill (card==drill)', () => {
  let store: ReturnType<typeof useImm03Store>
  let fetchSpy: MockInstance<(filters?: Record<string, unknown>) => Promise<void>>

  beforeEach(async () => {
    setActivePinia(createPinia())
    listDecisionsSpy.mockReset().mockImplementation((...a: unknown[]) => resolveList(a))
    getKpisSpy.mockReset().mockResolvedValue(KPIS)
    mockRoute.query = {}
    routerReplaceSpy.mockClear()
    routerPushSpy.mockClear()
    store = useImm03Store()
    fetchSpy = vi.spyOn(store, 'fetchDecisions')
  })

  // ── TC-FE-03-TILE-01 ────────────────────────────────────────────────────────
  it('click tile "Đã trao thầu" → fetchDecisions({workflow_state:"Awarded"})', async () => {
    const wrapper = await mountView()
    fetchSpy.mockClear()
    const btn = tileButton(wrapper, 'Lọc quyết định đã trao thầu')
    expect(btn).toBeTruthy()
    await btn!.trigger('click')
    await flushPromises()
    expect(fetchSpy).toHaveBeenCalledTimes(1)
    expect(fetchSpy).toHaveBeenCalledWith({ workflow_state: 'Awarded' })
  })

  // ── TC-FE-03-TILE-02 ────────────────────────────────────────────────────────
  it('click tile "Chờ phê duyệt" và "Đã phát hành đơn hàng" map đúng Pending Approval / PO Issued', async () => {
    const wrapper = await mountView()
    fetchSpy.mockClear()
    await tileButton(wrapper, 'Lọc quyết định chờ phê duyệt')!.trigger('click')
    await flushPromises()
    expect(fetchSpy).toHaveBeenLastCalledWith({ workflow_state: 'Pending Approval' })

    await tileButton(wrapper, 'Lọc quyết định đã phát hành đơn hàng')!.trigger('click')
    await flushPromises()
    expect(fetchSpy).toHaveBeenLastCalledWith({ workflow_state: 'PO Issued' })
  })

  // ── TC-FE-03-TILE-03 (toggle off) ────────────────────────────────────────────
  it('click tile đang active → bỏ lọc, fetchDecisions() KHÔNG filter', async () => {
    const wrapper = await mountView()
    fetchSpy.mockClear()
    const awardedLabel = 'Lọc quyết định đã trao thầu'
    // bật lọc
    await tileButton(wrapper, awardedLabel)!.trigger('click')
    await flushPromises()
    expect(fetchSpy).toHaveBeenLastCalledWith({ workflow_state: 'Awarded' })
    // tile đang active được tô sáng (aria-pressed=true)
    expect(tileButton(wrapper, awardedLabel)!.attributes('aria-pressed')).toBe('true')
    // click lại → toggle off → fetchDecisions() không filter ({})
    await tileButton(wrapper, awardedLabel)!.trigger('click')
    await flushPromises()
    expect(fetchSpy).toHaveBeenLastCalledWith({})
    expect(tileButton(wrapper, awardedLabel)!.attributes('aria-pressed')).toBe('false')
  })

  // ── TC-FE-03-TILE-04 (value=0 click được, empty-state, không lỗi) ────────────
  it('tile value=0 (PO Issued) click được → list rỗng + total=0, không lỗi', async () => {
    const wrapper = await mountView()
    fetchSpy.mockClear()
    const btn = tileButton(wrapper, 'Lọc quyết định đã phát hành đơn hàng')
    expect(btn).toBeTruthy()
    await btn!.trigger('click')
    await flushPromises()
    expect(fetchSpy).toHaveBeenCalledWith({ workflow_state: 'PO Issued' })
    expect(store.decisionTotal).toBe(0)
    expect(store.decisions.length).toBe(0)
    expect(store.error).toBeNull()
    // empty-state hiển thị (không crash)
    // AC-UX-047 lô 2: khối rỗng tự chế đã nhường cho `EmptyState` của `ListPageShell`;
    // câu rỗng-có-lọc là SSoT ở `02 §13.4` ⇒ chuỗi đổi theo, ngữ nghĩa giữ nguyên.
    expect(wrapper.find('[data-testid="ui-empty-title"]').text())
      .toBe('Không có quyết định mua sắm nào phù hợp')
  })

  // ── card == drill: total store khớp số tile sau khi click ─────────────────────
  it('INV card==drill: decisionTotal khớp số tile sau khi click từng tile', async () => {
    const wrapper = await mountView()
    await tileButton(wrapper, 'Lọc quyết định đã trao thầu')!.trigger('click')
    await flushPromises()
    expect(store.decisionTotal).toBe(KPIS.decision_states['Awarded'])  // 5

    await tileButton(wrapper, 'Lọc quyết định chờ phê duyệt')!.trigger('click')
    await flushPromises()
    expect(store.decisionTotal).toBe(KPIS.decision_states['Pending Approval'])  // 3
  })

  // ── no-leak nhãn EN trên tile/active-state ────────────────────────────────────
  it('KHÔNG leak raw EN state (Awarded/Pending Approval/PO Issued) ra UI tile', async () => {
    const wrapper = await mountView()
    const html = wrapper.html()
    expect(html).toContain('Đã trao thầu')
    expect(html).toContain('Chờ phê duyệt')
    expect(html).toContain('Đã phát hành đơn hàng')
    // nhãn EN không xuất hiện dạng text hiển thị (chỉ trong aria/title là chấp nhận
    // được vì không phải nội dung user đọc trên tile) — kiểm phần text các tile.
    const tileTexts = wrapper.findAll('button.kpi-drill').map(b => b.text())
    for (const t of tileTexts) {
      expect(t).not.toMatch(/\bAwarded\b/)
      expect(t).not.toMatch(/\bPending Approval\b/)
      expect(t).not.toMatch(/\bPO Issued\b/)
    }
  })
})

// ─────────────────────────────────────────────────────────────────────────────
// IMM-03 DecisionListView — đồng bộ filter/tile vào URL (deep-link + refresh-safe
// + shareable). canonical query param = 'state' ↔ filters.workflow_state.
// Precedent AssetListView §9.3 (route.query ⇄ filters + watch route.query).
// ─────────────────────────────────────────────────────────────────────────────
describe('IMM-03 DecisionListView — URL sync (deep-link/refresh/shareable)', () => {
  let store: ReturnType<typeof useImm03Store>
  let fetchSpy: MockInstance<(filters?: Record<string, unknown>) => Promise<void>>

  beforeEach(async () => {
    setActivePinia(createPinia())
    listDecisionsSpy.mockReset().mockImplementation((...a: unknown[]) => resolveList(a))
    getKpisSpy.mockReset().mockResolvedValue(KPIS)
    mockRoute.query = {}
    routerReplaceSpy.mockClear()
    routerPushSpy.mockClear()
    store = useImm03Store()
    fetchSpy = vi.spyOn(store, 'fetchDecisions')
  })

  // ── TC-03-URL-01 (deep-link / refresh-safe) ──────────────────────────────────
  it('deep-link ?state=Awarded → fetchDecisions({workflow_state:"Awarded"}) + tile active', async () => {
    const wrapper = await mountView({ state: 'Awarded' })
    // fetch ban đầu PHẢI mang filter từ query (không phải fetch trần load-all)
    expect(fetchSpy).toHaveBeenCalledWith({ workflow_state: 'Awarded' })
    // tile 'Đã trao thầu' active (aria-pressed=true)
    const btn = tileButton(wrapper, 'Lọc quyết định đã trao thầu')
    expect(btn!.attributes('aria-pressed')).toBe('true')
    // INV card==drill: số dòng list == total từ tile Awarded (5)
    expect(store.decisionTotal).toBe(TOTAL_BY_STATE['Awarded'])
  })

  // ── TC-03-URL-02 (click tile → URL canonical code) ───────────────────────────
  it('click tile "Chờ phê duyệt" → router.replace query.state = "Pending Approval" (canonical, KHÔNG nhãn VI)', async () => {
    const wrapper = await mountView()
    routerReplaceSpy.mockClear()
    await tileButton(wrapper, 'Lọc quyết định chờ phê duyệt')!.trigger('click')
    await flushPromises()
    expect(routerReplaceSpy).toHaveBeenCalledTimes(1)
    const arg = routerReplaceSpy.mock.calls[0][0] as { query: Record<string, unknown> }
    expect(arg.query.state).toBe('Pending Approval')
    // KHÔNG leak nhãn VI vào URL
    expect(arg.query.state).not.toBe('Chờ phê duyệt')
  })

  // ── TC-03-URL-03 (toggle-off / clearFilters xoá ?state) ──────────────────────
  it('click tile đang active (toggle-off) → router.replace xoá key state + fetchDecisions() không filter', async () => {
    const wrapper = await mountView({ state: 'Awarded' })
    routerReplaceSpy.mockClear()
    fetchSpy.mockClear()
    // click lại tile Awarded đang active → toggle off
    await tileButton(wrapper, 'Lọc quyết định đã trao thầu')!.trigger('click')
    await flushPromises()
    expect(routerReplaceSpy).toHaveBeenCalled()
    const arg = routerReplaceSpy.mock.calls.at(-1)![0] as { query: Record<string, unknown> }
    expect('state' in arg.query).toBe(false)
    expect(fetchSpy).toHaveBeenLastCalledWith({})
  })

  it('clearFilters (Xóa tất cả) → router.replace xoá key state + fetchDecisions() không filter', async () => {
    const wrapper = await mountView({ state: 'Awarded' })
    routerReplaceSpy.mockClear()
    fetchSpy.mockClear()
    // nút "Xóa tất cả" (resetFilters) trong header bảng
    const clearBtn = wrapper.findAll('button').find(b => b.text() === 'Xóa tất cả')
    expect(clearBtn).toBeTruthy()
    await clearBtn!.trigger('click')
    await flushPromises()
    const arg = routerReplaceSpy.mock.calls.at(-1)![0] as { query: Record<string, unknown> }
    expect('state' in arg.query).toBe(false)
    expect(fetchSpy).toHaveBeenLastCalledWith()
  })

  // ── TC-03-URL-04 (state lạ bị bỏ qua an toàn) ────────────────────────────────
  it('?state=BogusState (không hợp lệ) → load all, KHÔNG set filter, KHÔNG tile active, KHÔNG throw', async () => {
    const wrapper = await mountView({ state: 'BogusState' })
    // fetch trần (không filter) — load all
    expect(fetchSpy).toHaveBeenCalledWith()
    // không có lời gọi fetch nào mang workflow_state
    for (const call of fetchSpy.mock.calls) {
      const arg = call[0] as Record<string, unknown> | undefined
      expect(arg?.workflow_state).toBeUndefined()
    }
    // không tile nào active
    for (const lbl of [
      'Lọc quyết định đã trao thầu',
      'Lọc quyết định chờ phê duyệt',
      'Lọc quyết định đã phát hành đơn hàng',
    ]) {
      expect(tileButton(wrapper, lbl)!.attributes('aria-pressed')).toBe('false')
    }
    expect(store.error).toBeNull()
  })

  // ── TC-03-URL-05 (watch — drill lần 2 cùng route, query khác) ─────────────────
  it('đổi route.query.state Awarded → PO Issued (drill lần 2) → re-fetch {workflow_state:"PO Issued"} không remount', async () => {
    const wrapper = await mountView({ state: 'Awarded' })
    expect(fetchSpy).toHaveBeenCalledWith({ workflow_state: 'Awarded' })
    fetchSpy.mockClear()
    // mô phỏng điều hướng tới cùng route với ?state=PO Issued
    mockRoute.query = { state: 'PO Issued' }
    await flushPromises()
    expect(fetchSpy).toHaveBeenLastCalledWith({ workflow_state: 'PO Issued' })
    // tile PO Issued giờ active, Awarded không còn
    expect(tileButton(wrapper, 'Lọc quyết định đã phát hành đơn hàng')!.attributes('aria-pressed')).toBe('true')
    expect(tileButton(wrapper, 'Lọc quyết định đã trao thầu')!.attributes('aria-pressed')).toBe('false')
  })
})

// ─────────────────────────────────────────────────────────────────────────────
// IMM-03 DecisionListView — vá phantom nút lọc spec_ref "Lọc: null".
// Nút lọc cột 'Hồ sơ kỹ thuật' chỉ render khi d.spec_ref có giá trị; null/rỗng → '—'.
// ─────────────────────────────────────────────────────────────────────────────
describe('IMM-03 DecisionListView — spec_ref null guard (no phantom "Lọc: null")', () => {
  beforeEach(async () => {
    setActivePinia(createPinia())
    getKpisSpy.mockReset().mockResolvedValue(KPIS)
    mockRoute.query = {}
    routerReplaceSpy.mockClear()
  })

  // ── TC-03-NULL-01 ────────────────────────────────────────────────────────────
  it('row spec_ref=null → KHÔNG nút lọc spec_ref + hiện "—"; row spec_ref hợp lệ → nút title="Lọc: TS-1"', async () => {
    // 1 row spec_ref hợp lệ + 1 row spec_ref null
    listDecisionsSpy.mockReset().mockResolvedValue({
      items: [
        { name: 'PD-OK', spec_ref: 'TS-1', winner_supplier: '', workflow_state: 'Awarded', creation: '2026-06-01' },
        { name: 'PD-NULL', spec_ref: null, winner_supplier: '', workflow_state: 'Awarded', creation: '2026-06-01' },
      ] as unknown as DecisionListItem[],
      total: 2,
    })
    const wrapper = await mountView()
    // KHÔNG còn phantom button title="Lọc: null"
    const phantom = wrapper.findAll('button').find(b => b.attributes('title') === 'Lọc: null')
    expect(phantom).toBeUndefined()
    // row hợp lệ vẫn có nút lọc spec_ref
    const okBtn = wrapper.findAll('button').find(b => b.attributes('title') === 'Lọc: TS-1')
    expect(okBtn).toBeTruthy()
    // có ít nhất 1 placeholder '—' cho spec_ref null (dùng class text-slate-400)
    expect(wrapper.html()).toContain('text-slate-400')
  })
})
