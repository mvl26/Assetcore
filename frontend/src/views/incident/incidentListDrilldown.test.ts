// TDD — Core Doc §9.4.1: IncidentListView pre-applies route.query (severity/status).
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'

const routeQuery = ref<Record<string, string>>({})
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useRoute: () => ({ get query() { return routeQuery.value } }),
}))

const fetchListSpy = vi.fn().mockResolvedValue(undefined)
const fetchStatsSpy = vi.fn().mockResolvedValue(undefined)
vi.mock('@/stores/imm12', () => ({
  useImm12Store: () => ({
    incidents: [],
    pagination: { page: 1, page_size: 20, total: 0, total_pages: 0 },
    loading: false,
    error: null,
    stats: null,
    fetchList: fetchListSpy,
    fetchStats: fetchStatsSpy,
  }),
}))

let canImpl: (cap: string) => boolean = () => true
vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({ can: (c: string) => canImpl(c) }),
}))

import IncidentListView from './IncidentListView.vue'

const stubs = {
  PageHeader: true, FilterToggleButton: true, ListFilterBar: true,
  BasePagination: true, StatusBadge: true, SkeletonLoader: true,
  WorkOrderKpiStrip: true, RouterLink: true,
}
const PageHeaderSlotStub = { template: '<div><slot name="actions" /></div>' }

describe('IncidentListView drill-down query (Core Doc §9.4.1)', () => {
  beforeEach(() => {
    fetchListSpy.mockClear()
    fetchStatsSpy.mockClear()
    routeQuery.value = {}
    canImpl = () => true
  })

  it('query.severity=Critical → fetchList gọi với severity Critical', async () => {
    routeQuery.value = { severity: 'Critical' }
    mount(IncidentListView, { global: { stubs } })
    await flushPromises()
    expect(fetchListSpy).toHaveBeenCalled()
    const arg = fetchListSpy.mock.calls[0][0]
    expect(arg?.severity).toBe('Critical')
  })

  it('không có query → fetchList gọi không kèm severity', async () => {
    routeQuery.value = {}
    mount(IncidentListView, { global: { stubs } })
    await flushPromises()
    expect(fetchListSpy).toHaveBeenCalled()
    const arg = fetchListSpy.mock.calls[0][0]
    expect(arg?.severity).toBeUndefined()
  })

  it('đổi query lần 2 → watch re-apply', async () => {
    routeQuery.value = { severity: 'Critical' }
    mount(IncidentListView, { global: { stubs } })
    await flushPromises()
    fetchListSpy.mockClear()
    routeQuery.value = { status: 'Open' }
    await flushPromises()
    expect(fetchListSpy).toHaveBeenCalled()
    const arg = fetchListSpy.mock.calls[0][0]
    expect(arg?.status).toBe('Open')
  })
})

// Read-only oversight (opsmgr 2026-06-02): nút "Báo cáo sự cố" gated bằng corrective.create.
describe('IncidentListView — nút Báo cáo sự cố gated bằng corrective.create', () => {
  beforeEach(() => { fetchListSpy.mockClear(); fetchStatsSpy.mockClear(); routeQuery.value = {} })
  const gateStubs = { ...stubs, PageHeader: PageHeaderSlotStub }

  it('có corrective.create → render nút Báo cáo sự cố', async () => {
    canImpl = () => true
    const w = mount(IncidentListView, { global: { stubs: gateStubs } })
    await flushPromises()
    expect(w.text()).toContain('Báo cáo sự cố')
  })

  it('KHÔNG corrective.create (opsmgr read-only) → ẨN nút Báo cáo sự cố', async () => {
    canImpl = (c: string) => c !== 'corrective.create'
    const w = mount(IncidentListView, { global: { stubs: gateStubs } })
    await flushPromises()
    expect(w.text()).not.toContain('Báo cáo sự cố')
  })
})
