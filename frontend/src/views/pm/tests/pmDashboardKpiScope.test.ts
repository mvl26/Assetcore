// TDD — INV-PM-KPI-1..6: KPI dashboard PM phải ĐỒNG NHẤT PHẠM VI.
// Tách 'Quá hạn trong tháng' (overdue_in_month, đối-soát strip tháng) khỏi
// 'Quá hạn (toàn hệ thống)' (overdue, RC-10, drill ?overdue=1). compliance null
// → render '—' (KHÔNG '0%'). Số strip PMWorkOrderListView khớp PMDashboardView.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'
import type { PMDashboardStats } from '@/api/imm08'
import { resetRouteMock, routerPushSpy } from '@/test/vueRouterMock'

// ── router mock ─ ROOT-CAUSE test-isolation fix (xem src/test/vueRouterMock.ts):
// shared full-shape mock (route-state + push-spy trên globalThis) đồng nhất mọi
// file PM → race vô hại. push-spy lấy qua routerPushSpy() để verify drill ?overdue=1.
vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())
const pushSpy = () => routerPushSpy()

// ── store mock — dashboardStats mutable giữa các test ───────────────────────
const dashboardStats = ref<PMDashboardStats | null>(null)
const fetchWOSpy = vi.fn().mockResolvedValue(undefined)
const fetchStatsSpy = vi.fn().mockResolvedValue(undefined)
vi.mock('@/stores/imm08', () => ({
  useImm08Store: () => ({
    get dashboardStats() { return dashboardStats.value },
    get overdueWOs() { return [] },
    workOrders: [],
    pagination: { page: 1, page_size: 20, total: 0, total_pages: 0 },
    loading: false,
    error: null,
    fetchWorkOrders: fetchWOSpy,
    fetchDashboardStats: fetchStatsSpy,
  }),
}))

let canImpl: (cap: string) => boolean = () => true
vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({ can: (c: string) => canImpl(c) }),
}))

import PMDashboardView from '@/views/pm/PMDashboardView.vue'
import PMWorkOrderListView from '@/views/pm/PMWorkOrderListView.vue'

const stubs = {
  PageHeader: true, SkeletonLoader: true, FilterToggleButton: true,
  ListFilterBar: true, BasePagination: true, DateInput: true, RouterLink: true,
}
// WorkOrderKpiStrip render thật để assert nhãn + value strip (KHÔNG stub).
const listStubs = { ...stubs, WorkOrderKpiStrip: false }

function statsFixture(overrides: Partial<PMDashboardStats['kpis']> = {}): PMDashboardStats {
  return {
    kpis: {
      compliance_rate_pct: 75,
      total_scheduled: 4,
      completed_on_time: 3,
      overdue_in_month: 1,
      pending_in_month: 0,
      overdue: 2,
      avg_days_late: 1.5,
      ...overrides,
    },
    trend_6months: [],
  }
}

// ── TC-FE-PM-KPI-01: payload overdue_in_month=0 & overdue=5 → 2 tile riêng ───
describe('PMDashboardView — tách tile Quá hạn (trong tháng vs toàn hệ thống)', () => {
  beforeEach(() => {
    resetRouteMock(); fetchStatsSpy.mockClear()
    canImpl = () => true
    dashboardStats.value = statsFixture({ overdue_in_month: 0, overdue: 5 })
  })

  it('render 2 tile riêng: "Quá hạn trong tháng: 0" + "Quá hạn (toàn hệ thống): 5"', async () => {
    const w = mount(PMDashboardView, { global: { stubs } })
    await flushPromises()

    const monthTile = w.find('[data-testid="pm-kpi-overdue-month"]')
    const globalTile = w.find('[data-testid="pm-kpi-overdue-global"]')
    expect(monthTile.exists()).toBe(true)
    expect(globalTile.exists()).toBe(true)

    // Nhãn phân biệt rõ
    expect(monthTile.text()).toContain('Quá hạn trong tháng')
    expect(globalTile.text()).toContain('Quá hạn (toàn hệ thống)')
    // Giá trị đúng nguồn — đọc CHÍNH XÁC số lớn trong tile (text-3xl <p>).
    // RED-prove: nếu gộp 2 tile về 1 bind 'overdue' thì big-number tile tháng = 5
    // → assert '0' FAIL.
    const monthNum = monthTile.find('p.text-3xl').text()
    const globalNum = globalTile.find('p.text-3xl').text()
    expect(monthNum).toBe('0')   // overdue_in_month
    expect(globalNum).toBe('5')  // overdue global
  })

  it('tile "Toàn hệ thống" wire drill ?overdue=1 (RC-10, INV-PM-KPI-6)', async () => {
    const w = mount(PMDashboardView, { global: { stubs } })
    await flushPromises()
    await w.find('[data-testid="pm-kpi-overdue-global"]').trigger('click')
    expect(pushSpy()).toHaveBeenCalledWith({ path: '/pm/work-orders', query: { overdue: '1' } })
  })

  it('aria-label 2 tile overdue phân biệt cho screen-reader (a11y)', async () => {
    const w = mount(PMDashboardView, { global: { stubs } })
    await flushPromises()
    const monthAria = w.find('[data-testid="pm-kpi-overdue-month"]').attributes('aria-label')
    const globalAria = w.find('[data-testid="pm-kpi-overdue-global"]').attributes('aria-label')
    expect(monthAria).toContain('Quá hạn trong tháng')
    expect(globalAria).toContain('toàn hệ thống')
    expect(monthAria).not.toBe(globalAria)
  })

  it('nhãn phạm vi: tile tháng gắn "Phạm vi: tháng M/Y", global gắn "Toàn hệ thống"', async () => {
    const w = mount(PMDashboardView, { global: { stubs } })
    await flushPromises()
    expect(w.find('[data-testid="pm-kpi-total"]').text()).toContain('Phạm vi: tháng')
    expect(w.find('[data-testid="pm-kpi-overdue-month"]').text()).toContain('Phạm vi: tháng')
    expect(w.find('[data-testid="pm-kpi-overdue-global"]').text()).toContain('Toàn hệ thống')
  })

  it('no leak EN/raw status trong KPI strip', async () => {
    const w = mount(PMDashboardView, { global: { stubs } })
    await flushPromises()
    const txt = w.text()
    expect(txt).not.toMatch(/Overdue|Pending|Completed|Scheduled/)
  })
})

// ── TC-FE-PM-KPI-02: total_scheduled=0 → compliance '—' (KHÔNG '0%') ─────────
describe('PMDashboardView — compliance null khi total_scheduled==0', () => {
  beforeEach(() => {
    resetRouteMock(); canImpl = () => true
  })

  it('compliance_rate_pct=null + total=0 → render "—", KHÔNG "0%"', async () => {
    dashboardStats.value = statsFixture({
      compliance_rate_pct: null, total_scheduled: 0, completed_on_time: 0,
      overdue_in_month: 0, pending_in_month: 0, overdue: 5,
    })
    const w = mount(PMDashboardView, { global: { stubs } })
    await flushPromises()
    const tile = w.find('[data-testid="pm-kpi-compliance"]')
    expect(tile.text()).toContain('—')
    expect(tile.text()).not.toContain('0%')
    // counter-example vẫn hiển thị global=5 đúng
    expect(w.find('[data-testid="pm-kpi-overdue-global"]').text()).toContain('5')
    expect(w.find('[data-testid="pm-kpi-overdue-month"]').text()).toContain('0')
  })

  it('compliance có giá trị → render "<v>%" bình thường', async () => {
    dashboardStats.value = statsFixture({ compliance_rate_pct: 88.5 })
    const w = mount(PMDashboardView, { global: { stubs } })
    await flushPromises()
    expect(w.find('[data-testid="pm-kpi-compliance"]').text()).toContain('88.5%')
  })
})

// ── Strip PMWorkOrderListView khớp PMDashboardView (cùng endpoint) ───────────
describe('PMWorkOrderListView — strip đồng nhất phạm vi với dashboard', () => {
  beforeEach(() => {
    resetRouteMock(); fetchWOSpy.mockClear(); canImpl = () => true
    dashboardStats.value = statsFixture({
      total_scheduled: 4, overdue_in_month: 1, overdue: 5, completed_on_time: 3,
      compliance_rate_pct: 75,
    })
  })

  it('strip có "Quá hạn trong tháng" + "Quá hạn (toàn hệ thống)" tách bạch', async () => {
    const w = mount(PMWorkOrderListView, { global: { stubs: listStubs } })
    await flushPromises()
    const txt = w.text()
    expect(txt).toContain('Quá hạn trong tháng')
    expect(txt).toContain('Quá hạn (toàn hệ thống)')
    // Tổng lịch tháng đứng cạnh overdue_in_month (đối-soát: 1 <= 4)
    expect(txt).toContain('Tổng lịch tháng')
  })

  it('số strip khớp dashboard cùng payload: in-month=1, global=5', async () => {
    const w = mount(PMWorkOrderListView, { global: { stubs: listStubs } })
    await flushPromises()
    const vm = w.vm as unknown as { kpiItems: { label: string; value: string | number }[] }
    const items = vm.kpiItems
    const inMonth = items.find(i => i.label === 'Quá hạn trong tháng')
    const global = items.find(i => i.label === 'Quá hạn (toàn hệ thống)')
    expect(inMonth?.value).toBe(1)
    expect(global?.value).toBe(5)
    // Compliance trend dùng giá trị từ cùng payload
    const done = items.find(i => i.label === 'Hoàn tất đúng hạn')
    expect(done?.value).toBe(3)
  })

  it('compliance null trong strip → trend "Compliance —" (KHÔNG "Compliance 0%")', async () => {
    dashboardStats.value = statsFixture({
      compliance_rate_pct: null, total_scheduled: 0, completed_on_time: 0,
      overdue_in_month: 0, overdue: 5,
    })
    const w = mount(PMWorkOrderListView, { global: { stubs: listStubs } })
    await flushPromises()
    const vm = w.vm as unknown as { kpiItems: { label: string; trend?: string }[] }
    const done = vm.kpiItems.find(i => i.label === 'Hoàn tất đúng hạn')
    expect(done?.trend).toContain('—')
    expect(done?.trend).not.toContain('0%')
  })
})
