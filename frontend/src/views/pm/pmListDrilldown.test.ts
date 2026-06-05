// TDD — Core Doc §9.4.2: PMWorkOrderListView pre-applies route.query.status.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { resetRouteMock, setRouteQuery } from '@/test/vueRouterMock'

// ROOT-CAUSE test-isolation fix (xem src/test/vueRouterMock.ts): shared full-shape
// router mock (route-state trên globalThis) đồng nhất mọi file PM → khi pool tái
// dùng worker + đổi thứ tự file, factory nào "thắng" race cũng đọc cùng state →
// hết "route.query undefined / query rỗng" cross-file (vd preflight chỉ mock useRouter).
vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())

const fetchWOSpy = vi.fn().mockResolvedValue(undefined)
vi.mock('@/stores/imm08', () => ({
  useImm08Store: () => ({
    workOrders: [],
    dashboardStats: null,
    pagination: { page: 1, page_size: 20, total: 0, total_pages: 0 },
    loading: false,
    error: null,
    fetchWorkOrders: fetchWOSpy,
    fetchDashboardStats: vi.fn().mockResolvedValue(undefined),
  }),
}))

// Capability stub — đổi giữa các test để verify gating nút Tạo phiếu.
let canImpl: (cap: string) => boolean = () => true
vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({ can: (c: string) => canImpl(c) }),
}))

import PMWorkOrderListView from './PMWorkOrderListView.vue'

// PageHeader KHÔNG stub ở nhóm test gating — cần render slot #actions để thấy nút.
const stubs = {
  PageHeader: true, FilterToggleButton: true, ListFilterBar: true,
  BasePagination: true, StatusBadge: true, SkeletonLoader: true,
  WorkOrderKpiStrip: true, RouterLink: true,
}
// PageHeader render slot actions (để test thấy nút Tạo trong template #actions).
const PageHeaderSlotStub = {
  template: '<div><slot name="actions" /></div>',
}

describe('PMWorkOrderListView drill-down query (Core Doc §9.4.2)', () => {
  beforeEach(() => { fetchWOSpy.mockClear(); resetRouteMock(); canImpl = () => true })

  it('query.status=Overdue → fetchWorkOrders gọi với status=[Overdue]', async () => {
    setRouteQuery({ status: 'Overdue' })
    mount(PMWorkOrderListView, { global: { stubs } })
    await flushPromises()
    expect(fetchWOSpy).toHaveBeenCalled()
    const arg = fetchWOSpy.mock.calls[0][0]
    expect(arg?.status).toEqual(['Overdue'])
  })

  it('không có query → fetchWorkOrders không kèm status', async () => {
    resetRouteMock()
    mount(PMWorkOrderListView, { global: { stubs } })
    await flushPromises()
    const arg = fetchWOSpy.mock.calls[0][0]
    expect(arg?.status).toBeUndefined()
  })

  // R6 §9.4.3 — date-window drill từ KPI pm_due_7d.
  it('query.due_before=X → fetchWorkOrders gọi với due_before=X (virtual key)', async () => {
    setRouteQuery({ due_before: '2026-06-09' })
    mount(PMWorkOrderListView, { global: { stubs } })
    await flushPromises()
    const arg = fetchWOSpy.mock.calls[0][0]
    // FE forward verbatim — cận dưới (hôm nay) do BE _normalize_filters lo. KHÔNG inline-compute.
    expect(arg?.due_before).toBe('2026-06-09')
  })

  // IMM-08 SoT round — chip due-soon đổi NHÃN sang ngữ nghĩa cửa-sổ. KHÔNG còn
  // "Đến hạn trước" (gây hiểu nhầm gồm cả quá hạn). dueBefore == today+7 → "trong 7 ngày".
  it('chip due_before == today+7 → nhãn "Đến hạn trong 7 ngày" (không còn "Đến hạn trước")', async () => {
    const d = new Date()
    d.setDate(d.getDate() + 7)
    const next7 = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
    setRouteQuery({ due_before: next7 })
    const w = mount(PMWorkOrderListView, { global: { stubs } })
    await flushPromises()
    const chips = (w.vm as unknown as { activeChips: { key: string; label: string }[] }).activeChips
    const chip = chips.find(c => c.key === 'dueBefore')
    expect(chip).toBeDefined()
    expect(chip?.label).toBe('Đến hạn trong 7 ngày')
    expect(chip?.label).not.toContain('Đến hạn trước')
  })

  it('chip due_before != today+7 → nhãn nêu rõ cận dưới "từ hôm nay"', async () => {
    setRouteQuery({ due_before: '2030-01-15' })
    const w = mount(PMWorkOrderListView, { global: { stubs } })
    await flushPromises()
    const chips = (w.vm as unknown as { activeChips: { key: string; label: string }[] }).activeChips
    const chip = chips.find(c => c.key === 'dueBefore')
    expect(chip?.label).toContain('từ hôm nay')
    expect(chip?.label).not.toContain('Đến hạn trước')
  })

  it('query.overdue=1 → fetchWorkOrders gọi với overdue=1 (BE dịch status=Overdue)', async () => {
    setRouteQuery({ overdue: '1' })
    mount(PMWorkOrderListView, { global: { stubs } })
    await flushPromises()
    const args = fetchWOSpy.mock.calls.map(c => c[0])
    expect(args.some(a => a?.overdue === '1')).toBe(true)
  })
})

// Read-only oversight (opsmgr 2026-06-02): nút "Tạo phiếu bảo trì" gated bằng
// can('pm.create'). opsmgr (read-only) KHÔNG có pm.create → KHÔNG thấy nút.
describe('PMWorkOrderListView — nút Tạo phiếu gated bằng pm.create', () => {
  beforeEach(() => { fetchWOSpy.mockClear(); resetRouteMock() })
  const gateStubs = { ...stubs, PageHeader: PageHeaderSlotStub }

  it('có pm.create → render nút Tạo phiếu bảo trì', async () => {
    canImpl = () => true
    const w = mount(PMWorkOrderListView, { global: { stubs: gateStubs } })
    await flushPromises()
    expect(w.text()).toContain('Tạo phiếu bảo trì')
  })

  it('KHÔNG pm.create (opsmgr read-only) → ẨN nút Tạo phiếu', async () => {
    canImpl = (c: string) => c !== 'pm.create'
    const w = mount(PMWorkOrderListView, { global: { stubs: gateStubs } })
    await flushPromises()
    expect(w.text()).not.toContain('Tạo phiếu bảo trì')
  })
})
