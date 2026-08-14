// TDD — Core Doc §06 IMM-12 (round-21): module dashboard "đang mở" SoT.
// Card "Đang mở" bind stats.open_total (open-set: Open+Acknowledged+In Progress+
// RCA Required), label qua SSoT INCIDENT_OPEN_FILTER_LABEL='Đang mở', drill push
// /incidents/list?open=1 (card count == drill list rows invariant). "Xem tất cả"
// của panel "Sự cố đang xử lý" cũng push /incidents/list?open=1.
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
// CR-AFFORD: view giờ gọi useCapabilities() ở setup (gate nút Tạo) → mock để mount không cần Pinia.
vi.mock('@/composables/useCapabilities', () => ({ useCapabilities: () => ({ can: () => true }) }))
import { mount, flushPromises, type VueWrapper } from '@vue/test-utils'
import { ref } from 'vue'

const mounted: VueWrapper[] = []
function mountTracked(...args: Parameters<typeof mount>): VueWrapper {
  const w = mount(...args) as VueWrapper
  mounted.push(w)
  return w
}
afterEach(() => { while (mounted.length) mounted.pop()!.unmount() })

// Router push spy — assert drill query.
const pushSpy = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: pushSpy }),
  useRoute: () => ({ query: {} }),
}))

// Store dashboard reactive — stats.open_total drives card #1.
const dashboard = ref<Record<string, unknown> | null>(null)
const fetchDashboardSpy = vi.fn().mockResolvedValue(undefined)
vi.mock('@/stores/imm12', () => ({
  useImm12Store: () => ({
    get dashboard() { return dashboard.value },
    dashboardLoading: false,
    dashboardError: null,
    fetchDashboard: fetchDashboardSpy,
  }),
}))

import IMM12DashboardView from '@/views/incident/IMM12DashboardView.vue'
import { INCIDENT_OPEN_FILTER_LABEL } from '@/constants/labels'

const stubs = { PageHeader: true, SlaBreachBadge: true }

function baseStats(over: Record<string, unknown> = {}) {
  return {
    total: 5, open: 3, open_total: 4, investigating: 1, resolved: 0,
    closed: 1, cancelled: 0, critical: 1, high: 1, rca_pending: 0, chronic: 0,
    sla_response_breached: 0, sla_resolution_breached: 0, ...over,
  }
}

describe('IMM12DashboardView — card "Đang mở" open-set SoT (round-21)', () => {
  beforeEach(() => {
    pushSpy.mockClear()
    fetchDashboardSpy.mockClear()
    dashboard.value = { stats: baseStats(), active_incidents: [], open_rcas: [], chronic_failures: [] }
  })

  it('TC-12-FE-01: card hiển thị open_total (4) + nhãn SSoT "Đang mở", KHÔNG bind stats.open (3)', async () => {
    const w = mountTracked(IMM12DashboardView, { global: { stubs } })
    await flushPromises()
    expect(INCIDENT_OPEN_FILTER_LABEL).toBe('Đang mở')
    const cards = w.findAll('.kpi-card')
    const openCard = cards[0]
    // count = open_total=4, KHÔNG phải open=3 (chứng minh đổi binding).
    expect(openCard.text()).toContain('4')
    expect(openCard.text()).not.toContain('3')
    // nhãn qua SSoT 'Đang mở', KHÔNG còn literal cũ 'Mới mở'.
    expect(openCard.text()).toContain('Đang mở')
    expect(openCard.text()).not.toContain('Mới mở')
  })

  it('TC-12-FE-01: click card "Đang mở" → router.push("/incidents/list?open=1") (KHÔNG bare path)', async () => {
    const w = mountTracked(IMM12DashboardView, { global: { stubs } })
    await flushPromises()
    await w.findAll('.kpi-card')[0].trigger('click')
    expect(pushSpy).toHaveBeenCalledWith('/incidents/list?open=1')
    expect(pushSpy).not.toHaveBeenCalledWith('/incidents/list')
  })

  it('TC-12-FE-02: "Xem tất cả" panel "Sự cố đang xử lý" → router.push("/incidents/list?open=1")', async () => {
    const w = mountTracked(IMM12DashboardView, { global: { stubs } })
    await flushPromises()
    // Tìm nút "Xem tất cả" trong panel.
    const seeAll = w.findAll('button').find(b => b.text().includes('Xem tất cả'))
    expect(seeAll, 'phải có nút "Xem tất cả"').toBeTruthy()
    await seeAll!.trigger('click')
    expect(pushSpy).toHaveBeenCalledWith('/incidents/list?open=1')
  })

  it('open_total thiếu (forward-compat BE chưa ship) → card hiện 0, KHÔNG vỡ', async () => {
    dashboard.value = { stats: baseStats({ open_total: undefined }), active_incidents: [], open_rcas: [], chronic_failures: [] }
    const w = mountTracked(IMM12DashboardView, { global: { stubs } })
    await flushPromises()
    expect(w.findAll('.kpi-card')[0].text()).toContain('0')
  })

  it('card "Đang điều tra" GIỮ nguyên (stats.investigating per-state, ngoài scope)', async () => {
    const w = mountTracked(IMM12DashboardView, { global: { stubs } })
    await flushPromises()
    const investCard = w.findAll('.kpi-card')[1]
    expect(investCard.text()).toContain('Đang điều tra')
    expect(investCard.text()).toContain('1')
  })
})
