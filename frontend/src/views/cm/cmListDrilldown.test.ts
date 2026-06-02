// TDD — Core Doc §9.4.2: CMWorkOrderListView pre-applies route.query (status/priority).
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'

const routeQuery = ref<Record<string, string>>({})
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useRoute: () => ({ get query() { return routeQuery.value } }),
}))

const fetchWOSpy = vi.fn().mockResolvedValue(undefined)
vi.mock('@/stores/imm09', () => ({
  useImm09Store: () => ({
    workOrders: [],
    kpis: null,
    pagination: { page: 1, page_size: 20, total: 0, total_pages: 0 },
    loading: false,
    error: null,
    fetchWorkOrders: fetchWOSpy,
    fetchKPIs: vi.fn().mockResolvedValue(undefined),
  }),
}))

let canImpl: (cap: string) => boolean = () => true
vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({ can: (c: string) => canImpl(c) }),
}))

import CMWorkOrderListView from './CMWorkOrderListView.vue'

const stubs = {
  PageHeader: true, FilterToggleButton: true, ListFilterBar: true,
  BasePagination: true, StatusBadge: true, SkeletonLoader: true,
  WorkOrderKpiStrip: true, RouterLink: true,
}
const PageHeaderSlotStub = { template: '<div><slot name="actions" /></div>' }

describe('CMWorkOrderListView drill-down query (Core Doc §9.4.2)', () => {
  beforeEach(() => { fetchWOSpy.mockClear(); routeQuery.value = {}; canImpl = () => true })

  it('query.status=In Repair → fetchWorkOrders gọi với status', async () => {
    routeQuery.value = { status: 'In Repair' }
    mount(CMWorkOrderListView, { global: { stubs } })
    await flushPromises()
    expect(fetchWOSpy).toHaveBeenCalled()
    const arg = fetchWOSpy.mock.calls[0][0]
    expect(arg?.status).toBe('In Repair')
  })

  it('query.priority=Urgent → fetchWorkOrders gọi với priority', async () => {
    routeQuery.value = { priority: 'Urgent' }
    mount(CMWorkOrderListView, { global: { stubs } })
    await flushPromises()
    // priority phải xuất hiện trong ít nhất 1 call (mount + watch có thể tạo nhiều call)
    const sawPriority = fetchWOSpy.mock.calls.some(
      (c) => (c[0] as Record<string, unknown> | undefined)?.priority === 'Urgent',
    )
    expect(sawPriority).toBe(true)
  })

  it('không có query → fetchWorkOrders không kèm status', async () => {
    routeQuery.value = {}
    mount(CMWorkOrderListView, { global: { stubs } })
    await flushPromises()
    const arg = fetchWOSpy.mock.calls[0][0]
    expect(arg?.status).toBeUndefined()
  })

  // R8 §9.4.6 — bar-card SLA / repeat-failure drill từ opsmgr dashboard.
  it('query.sla_breached=1 → fetchWorkOrders gọi với sla_breached=1', async () => {
    routeQuery.value = { sla_breached: '1' }
    mount(CMWorkOrderListView, { global: { stubs } })
    await flushPromises()
    const saw = fetchWOSpy.mock.calls.some(
      (c) => (c[0] as Record<string, unknown> | undefined)?.sla_breached === '1')
    expect(saw).toBe(true)
  })

  it('query.is_repeat_failure=1 → fetchWorkOrders gọi với is_repeat_failure=1', async () => {
    routeQuery.value = { is_repeat_failure: '1' }
    mount(CMWorkOrderListView, { global: { stubs } })
    await flushPromises()
    const saw = fetchWOSpy.mock.calls.some(
      (c) => (c[0] as Record<string, unknown> | undefined)?.is_repeat_failure === '1')
    expect(saw).toBe(true)
  })
})

// Read-only oversight (opsmgr 2026-06-02): nút "Tạo lệnh mới" gated bằng repair.create.
describe('CMWorkOrderListView — nút Tạo lệnh gated bằng repair.create', () => {
  beforeEach(() => { fetchWOSpy.mockClear(); routeQuery.value = {} })
  const gateStubs = { ...stubs, PageHeader: PageHeaderSlotStub }

  it('có repair.create → render nút Tạo lệnh mới', async () => {
    canImpl = () => true
    const w = mount(CMWorkOrderListView, { global: { stubs: gateStubs } })
    await flushPromises()
    expect(w.text()).toContain('Tạo lệnh mới')
  })

  it('KHÔNG repair.create (opsmgr read-only) → ẨN nút Tạo lệnh', async () => {
    canImpl = (c: string) => c !== 'repair.create'
    const w = mount(CMWorkOrderListView, { global: { stubs: gateStubs } })
    await flushPromises()
    expect(w.text()).not.toContain('Tạo lệnh mới')
  })
})
