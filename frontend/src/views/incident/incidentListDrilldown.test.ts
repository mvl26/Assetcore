// TDD — Core Doc §9.4.1: IncidentListView pre-applies route.query (severity/status).
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises, type VueWrapper } from '@vue/test-utils'
import { ref } from 'vue'

// Theo dõi mọi wrapper đã mount để unmount sau mỗi test — tránh watch(route.query)
// của component cũ còn sống bắn fetchList khi test sau đổi routeQuery (shared ref).
const mounted: VueWrapper[] = []
function mountTracked(...args: Parameters<typeof mount>): VueWrapper {
  const w = mount(...args) as VueWrapper
  mounted.push(w)
  return w
}

afterEach(() => {
  while (mounted.length) mounted.pop()!.unmount()
})

const routeQuery = ref<Record<string, string>>({})
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useRoute: () => ({ get query() { return routeQuery.value } }),
}))

const fetchListSpy = vi.fn().mockResolvedValue(undefined)
const fetchStatsSpy = vi.fn().mockResolvedValue(undefined)
// Rows có thể thay đổi theo từng test (label-render test cần incidents thực).
const storeIncidents = ref<Record<string, unknown>[]>([])
vi.mock('@/stores/imm12', () => ({
  useImm12Store: () => ({
    get incidents() { return storeIncidents.value },
    pagination: { page: 1, page_size: 20, total: storeIncidents.value.length, total_pages: 1 },
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
    storeIncidents.value = []
    canImpl = () => true
  })

  it('query.severity=Critical → fetchList gọi với severity Critical', async () => {
    routeQuery.value = { severity: 'Critical' }
    mountTracked(IncidentListView, { global: { stubs } })
    await flushPromises()
    expect(fetchListSpy).toHaveBeenCalled()
    const arg = fetchListSpy.mock.calls[0][0]
    expect(arg?.severity).toBe('Critical')
  })

  it('không có query → fetchList gọi không kèm severity', async () => {
    routeQuery.value = {}
    mountTracked(IncidentListView, { global: { stubs } })
    await flushPromises()
    expect(fetchListSpy).toHaveBeenCalled()
    const arg = fetchListSpy.mock.calls[0][0]
    expect(arg?.severity).toBeUndefined()
  })

  it('đổi query lần 2 → watch re-apply', async () => {
    routeQuery.value = { severity: 'Critical' }
    mountTracked(IncidentListView, { global: { stubs } })
    await flushPromises()
    fetchListSpy.mockClear()
    routeQuery.value = { status: 'Open' }
    await flushPromises()
    expect(fetchListSpy).toHaveBeenCalled()
    const arg = fetchListSpy.mock.calls[0][0]
    expect(arg?.status).toBe('Open')
  })

  it('query {severity:Critical, open:"1"} → fetchList gọi với severity + open=1', async () => {
    routeQuery.value = { severity: 'Critical', open: '1' }
    mountTracked(IncidentListView, { global: { stubs } })
    await flushPromises()
    expect(fetchListSpy).toHaveBeenCalled()
    const arg = fetchListSpy.mock.calls[0][0]
    expect(arg?.severity).toBe('Critical')
    expect(arg?.open).toBe(1)
    // open=1 (filter ảo) KHÔNG được gửi kèm status đơn lẻ.
    expect(arg?.status).toBeUndefined()
  })

  it('chip "Đang mở" render khi open=1', async () => {
    routeQuery.value = { open: '1' }
    const w = mountTracked(IncidentListView, { global: { stubs: { ...stubs, ListFilterBar: false } } })
    await flushPromises()
    expect(w.text()).toContain('Đang mở')
  })

  it('status đơn lẻ override open (mutually-exclusive)', async () => {
    routeQuery.value = { status: 'Cancelled', open: '1' }
    mountTracked(IncidentListView, { global: { stubs } })
    await flushPromises()
    const arg = fetchListSpy.mock.calls[0][0]
    expect(arg?.status).toBe('Cancelled')
    // status đơn lẻ ưu tiên → KHÔNG gửi open.
    expect(arg?.open).toBeUndefined()
  })
})

// Read-only oversight (opsmgr 2026-06-02): nút "Báo cáo sự cố" gated bằng corrective.create.
describe('IncidentListView — nút Báo cáo sự cố gated bằng corrective.create', () => {
  beforeEach(() => { fetchListSpy.mockClear(); fetchStatsSpy.mockClear(); routeQuery.value = {} })
  const gateStubs = { ...stubs, PageHeader: PageHeaderSlotStub }

  it('có corrective.create → render nút Báo cáo sự cố', async () => {
    canImpl = () => true
    const w = mountTracked(IncidentListView, { global: { stubs: gateStubs } })
    await flushPromises()
    expect(w.text()).toContain('Báo cáo sự cố')
  })

  it('KHÔNG corrective.create (opsmgr read-only) → ẨN nút Báo cáo sự cố', async () => {
    canImpl = (c: string) => c !== 'corrective.create'
    const w = mountTracked(IncidentListView, { global: { stubs: gateStubs } })
    await flushPromises()
    expect(w.text()).not.toContain('Báo cáo sự cố')
  })
})

// ─── TDD round-20: status/severity LABEL render trên list (SSoT, no raw-EN leak) ──
// StatusBadge KHÔNG stub — phải render nhãn THẬT để bắt leak/drift.
// RED trước fix: list dùng StatusBadge → translateStatus thiếu 'Acknowledged'/'RCA
// Required' (leak raw-EN) + Open='Đang mở'/In Progress='Đang thực hiện' (drift với
// detail). GREEN sau fix: list dùng incidentStatusLabel (canonical SSoT).
describe('IncidentListView — nhãn status/severity SSoT (round-20)', () => {
  // StatusBadge bỏ stub để render label thật; còn lại stub cho gọn.
  const labelStubs = {
    PageHeader: true, FilterToggleButton: true, ListFilterBar: true,
    BasePagination: true, SkeletonLoader: true,
    WorkOrderKpiStrip: true, RouterLink: true, SlaBreachBadge: true,
  }
  beforeEach(() => {
    fetchListSpy.mockClear(); fetchStatsSpy.mockClear()
    routeQuery.value = {}; canImpl = () => true
  })

  function row(over: Record<string, unknown> = {}) {
    return {
      name: 'INC-2026-0001', status: 'Open', severity: 'Critical',
      asset: 'ACC-ASS-001', asset_name: 'Máy thở', description: 'Lỗi nguồn',
      reported_at: '2026-06-01 10:00:00', patient_affected: 0,
      chronic_failure_flag: 0, response_breached: 0, resolution_breached: 0,
      ...over,
    }
  }

  it("status='Acknowledged' → DOM hiển thị 'Đã tiếp nhận', KHÔNG 'Acknowledged'", async () => {
    storeIncidents.value = [row({ status: 'Acknowledged' })]
    const w = mountTracked(IncidentListView, { global: { stubs: labelStubs } })
    await flushPromises()
    expect(w.text()).toContain('Đã tiếp nhận')
    expect(w.text()).not.toMatch(/\bAcknowledged\b/)
  })

  it("status='RCA Required' → DOM hiển thị 'Cần phân tích nguyên nhân gốc', KHÔNG 'RCA Required'", async () => {
    storeIncidents.value = [row({ status: 'RCA Required' })]
    const w = mountTracked(IncidentListView, { global: { stubs: labelStubs } })
    await flushPromises()
    expect(w.text()).toContain('Cần phân tích nguyên nhân gốc')
    expect(w.text()).not.toMatch(/\bRCA Required\b/)
  })

  it("status='Open' → 'Mới mở' (SSoT incident), KHÔNG 'Đang mở' (drift STATUS_MAP)", async () => {
    storeIncidents.value = [row({ status: 'Open' })]
    const w = mountTracked(IncidentListView, { global: { stubs: labelStubs } })
    await flushPromises()
    expect(w.text()).toContain('Mới mở')
    expect(w.text()).not.toContain('Đang mở')
  })

  it("status='In Progress' → 'Đang điều tra', KHÔNG 'Đang thực hiện'", async () => {
    storeIncidents.value = [row({ status: 'In Progress' })]
    const w = mountTracked(IncidentListView, { global: { stubs: labelStubs } })
    await flushPromises()
    expect(w.text()).toContain('Đang điều tra')
    expect(w.text()).not.toContain('Đang thực hiện')
  })

  it("severity='Critical' → 'Nghiêm trọng' (incident domain), KHÔNG 'Khẩn cấp'", async () => {
    storeIncidents.value = [row({ severity: 'Critical' })]
    const w = mountTracked(IncidentListView, { global: { stubs: labelStubs } })
    await flushPromises()
    expect(w.text()).toContain('Nghiêm trọng')
    expect(w.text()).not.toContain('Khẩn cấp')
  })

  it('List↔Detail consistency: nhãn list == incidentStatusLabel cho cả 7 status', async () => {
    const { incidentStatusLabel } = await import('@/constants/labels')
    for (const s of ['Open', 'Acknowledged', 'In Progress', 'RCA Required', 'Resolved', 'Closed', 'Cancelled']) {
      storeIncidents.value = [row({ status: s })]
      const w = mountTracked(IncidentListView, { global: { stubs: labelStubs } })
      await flushPromises()
      expect(w.text(), `list phải render nhãn detail cho "${s}"`).toContain(incidentStatusLabel(s))
    }
  })
})
