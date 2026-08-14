// TDD — IMM-12 BR-12-09: badge "Vi phạm SLA" trên Incident list + dashboard.
// Đọc cờ response_breached / resolution_breached; nhãn VI qua SSoT; KHÔNG leak English.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'
import SlaBreachBadge from '@/components/incident/SlaBreachBadge.vue'
import { SLA_BREACH_LABEL } from '@/constants/labels'

// ─── Unit: component SlaBreachBadge ────────────────────────────────────────────
describe('SlaBreachBadge — render theo cờ breach', () => {
  it('resolution_breached=1 → badge "Vi phạm SLA xử lý", không loại tiếp nhận', () => {
    const w = mount(SlaBreachBadge, { props: { resolutionBreached: 1, responseBreached: 0 } })
    expect(w.text()).toContain(SLA_BREACH_LABEL.resolution)
    expect(w.text()).not.toContain(SLA_BREACH_LABEL.response)
  })

  it('response_breached=1 → badge "Vi phạm SLA tiếp nhận"', () => {
    const w = mount(SlaBreachBadge, { props: { responseBreached: 1, resolutionBreached: 0 } })
    expect(w.text()).toContain(SLA_BREACH_LABEL.response)
    expect(w.text()).not.toContain(SLA_BREACH_LABEL.resolution)
  })

  it('cả 2 cờ =1 → render cả 2 badge', () => {
    const w = mount(SlaBreachBadge, { props: { responseBreached: 1, resolutionBreached: 1 } })
    expect(w.text()).toContain(SLA_BREACH_LABEL.response)
    expect(w.text()).toContain(SLA_BREACH_LABEL.resolution)
  })

  it('không cờ nào set → KHÔNG render gì (v-if)', () => {
    const w = mount(SlaBreachBadge, { props: { responseBreached: 0, resolutionBreached: 0 } })
    expect(w.text().trim()).toBe('')
  })

  it('nhãn KHÔNG leak chữ "breached"/English', () => {
    const w = mount(SlaBreachBadge, { props: { responseBreached: 1, resolutionBreached: 1 } })
    const t = w.text().toLowerCase()
    expect(t).not.toContain('breach')
    expect(t).not.toContain('breached')
    expect(t).not.toContain('response')
    expect(t).not.toContain('resolution')
  })
})

// ─── Integration: IncidentListView render badge cho incident có cờ ─────────────
const routeQuery = ref<Record<string, string>>({})
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useRoute: () => ({ get query() { return routeQuery.value } }),
}))

const breachedIncident = {
  name: 'IR-2026-0042',
  asset: 'AC-ASSET-2026-0012',
  asset_name: 'Máy thở Drager Evita',
  severity: 'High',
  status: 'In Progress',
  incident_type: 'Failure',
  description: 'Alarm áp lực cao',
  reported_at: '2026-04-18 08:12:00',
  response_breached: 0,
  resolution_breached: 1,
}

vi.mock('@/stores/imm12', () => ({
  useImm12Store: () => ({
    incidents: [breachedIncident],
    pagination: { page: 1, page_size: 20, total: 1, total_pages: 1 },
    loading: false,
    error: null,
    stats: null,
    fetchList: vi.fn().mockResolvedValue(undefined),
    fetchStats: vi.fn().mockResolvedValue(undefined),
  }),
}))

vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({ can: () => true }),
}))

import IncidentListView from '@/views/incident/IncidentListView.vue'

const stubs = {
  PageHeader: true, FilterToggleButton: true, ListFilterBar: true,
  BasePagination: true, StatusBadge: true, SkeletonLoader: true,
  WorkOrderKpiStrip: true, RouterLink: true,
  // KHÔNG stub SlaBreachBadge — muốn assert label render thật.
}

describe('IncidentListView — badge SLA (BR-12-09)', () => {
  beforeEach(() => { routeQuery.value = {} })

  it('incident resolution_breached=1 → hiển thị "Vi phạm SLA xử lý"', async () => {
    const w = mount(IncidentListView, { global: { stubs } })
    await flushPromises()
    expect(w.text()).toContain(SLA_BREACH_LABEL.resolution)
    // KHÔNG leak chữ tiếng Anh thô.
    expect(w.text().toLowerCase()).not.toContain('breached')
  })
})
