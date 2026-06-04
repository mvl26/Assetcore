// TDD — IMM-12 BR-12-13: KPI/badge "Vi phạm SLA tiếp nhận/xử lý" theo SoT LIVE.
// Badge per-row đọc field DERIVED is_response_breached / is_resolution_breached (BE
// _row_is_breached = cờ-thô OR đang-mở-quá-hạn) thay cờ thô response_breached/
// resolution_breached → hiện cho incident đang-quá-hạn-mở kể cả khi cờ DB còn 0
// (scheduler chưa stamp). Tile dashboard đọc stats.sla_*_breached (BE đổi sang live).
// Nhãn VI giữ; KHÔNG leak English/raw status.
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises, type VueWrapper } from '@vue/test-utils'
import { ref } from 'vue'
import { SLA_BREACH_LABEL } from '@/constants/labels'

const mounted: VueWrapper[] = []
function mountTracked(...args: Parameters<typeof mount>): VueWrapper {
  const w = mount(...args) as VueWrapper
  mounted.push(w)
  return w
}
afterEach(() => { while (mounted.length) mounted.pop()!.unmount() })

// ─── Router + capabilities mocks (shared) ──────────────────────────────────────
const routeQuery = ref<Record<string, string>>({})
const pushSpy = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: pushSpy }),
  useRoute: () => ({ get query() { return routeQuery.value } }),
}))
vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({ can: () => true }),
}))

// ─── Store mock (list) ─────────────────────────────────────────────────────────
const listIncidents = ref<Record<string, unknown>[]>([])
const listStats = ref<Record<string, unknown> | null>(null)
const fetchListSpy = vi.fn().mockResolvedValue(undefined)
const fetchStatsSpy = vi.fn().mockResolvedValue(undefined)

// ─── Store mock (dashboard) ────────────────────────────────────────────────────
const dashboard = ref<Record<string, unknown> | null>(null)
const fetchDashboardSpy = vi.fn().mockResolvedValue(undefined)

vi.mock('@/stores/imm12', () => ({
  useImm12Store: () => ({
    get incidents() { return listIncidents.value },
    pagination: { page: 1, page_size: 20, total: listIncidents.value.length, total_pages: 1 },
    loading: false,
    error: null,
    get stats() { return listStats.value },
    get dashboard() { return dashboard.value },
    dashboardLoading: false,
    dashboardError: null,
    fetchList: fetchListSpy,
    fetchStats: fetchStatsSpy,
    fetchDashboard: fetchDashboardSpy,
  }),
}))

import IncidentListView from './IncidentListView.vue'
import IMM12DashboardView from './IMM12DashboardView.vue'

const listStubs = {
  PageHeader: true, FilterToggleButton: true, ListFilterBar: true,
  BasePagination: true, StatusBadge: true, SkeletonLoader: true,
  WorkOrderKpiStrip: true, RouterLink: true,
  // KHÔNG stub SlaBreachBadge — assert label render thật.
}
const dashStubs = { PageHeader: true } // KHÔNG stub SlaBreachBadge

// ════════════════════════════════════════════════════════════════════════════
// IncidentListView — badge đọc DERIVED is_*_breached, KHÔNG cờ thô
// ════════════════════════════════════════════════════════════════════════════
describe('IncidentListView — SLA badge theo field derived live (BR-12-13)', () => {
  beforeEach(() => {
    routeQuery.value = {}
    fetchListSpy.mockClear()
    listStats.value = null
  })

  it('TC-SLA-FE-01: is_resolution_breached=1 dù resolution_breached(thô)=0 → vẫn render "Vi phạm SLA xử lý"', async () => {
    listIncidents.value = [{
      name: 'IR-2026-0101', asset: 'AC-ASSET-2026-0001', asset_name: 'Máy thở',
      severity: 'High', status: 'In Progress', incident_type: 'Failure',
      description: 'Quá hạn xử lý, scheduler chưa stamp',
      reported_at: '2026-04-01 08:00:00',
      // Cờ thô CÒN 0 (scheduler trễ) — derived live = 1.
      response_breached: 0, resolution_breached: 0,
      is_response_breached: 0, is_resolution_breached: 1,
    }]
    const w = mountTracked(IncidentListView, { global: { stubs: listStubs } })
    await flushPromises()
    expect(w.text()).toContain(SLA_BREACH_LABEL.resolution)
    expect(w.text()).not.toContain(SLA_BREACH_LABEL.response)
  })

  it('TC-SLA-FE-02: is_response_breached=1 dù response_breached(thô)=0 → render "Vi phạm SLA tiếp nhận"', async () => {
    listIncidents.value = [{
      name: 'IR-2026-0102', asset: 'AC-ASSET-2026-0002', asset_name: 'Bơm tiêm',
      severity: 'Medium', status: 'Open', incident_type: 'Failure',
      description: 'Chưa tiếp nhận, quá hạn response',
      reported_at: '2026-04-02 08:00:00',
      response_breached: 0, resolution_breached: 0,
      is_response_breached: 1, is_resolution_breached: 0,
    }]
    const w = mountTracked(IncidentListView, { global: { stubs: listStubs } })
    await flushPromises()
    expect(w.text()).toContain(SLA_BREACH_LABEL.response)
    expect(w.text()).not.toContain(SLA_BREACH_LABEL.resolution)
  })

  it('TC-SLA-FE-03: trong hạn (cả thô & derived =0) → KHÔNG render badge nào', async () => {
    listIncidents.value = [{
      name: 'IR-2026-0103', asset: 'AC-ASSET-2026-0003', asset_name: 'Monitor',
      severity: 'Low', status: 'Open', incident_type: 'Failure',
      description: 'Còn trong hạn',
      reported_at: '2026-04-03 08:00:00',
      response_breached: 0, resolution_breached: 0,
      is_response_breached: 0, is_resolution_breached: 0,
    }]
    const w = mountTracked(IncidentListView, { global: { stubs: listStubs } })
    await flushPromises()
    expect(w.text()).not.toContain(SLA_BREACH_LABEL.response)
    expect(w.text()).not.toContain(SLA_BREACH_LABEL.resolution)
  })

  it('TC-SLA-FE-04: forward-compat — BE chưa ship derived, chỉ có cờ thô=1 → fallback vẫn render badge', async () => {
    listIncidents.value = [{
      name: 'IR-2026-0104', asset: 'AC-ASSET-2026-0004', asset_name: 'Máy X-quang',
      severity: 'Critical', status: 'In Progress', incident_type: 'Failure',
      description: 'Cờ lịch sử đã stamp, BE bản cũ chưa enrich derived',
      reported_at: '2026-04-04 08:00:00',
      // is_*_breached vắng (undefined) → ?? fallback về cờ thô.
      resolution_breached: 1,
    }]
    const w = mountTracked(IncidentListView, { global: { stubs: listStubs } })
    await flushPromises()
    expect(w.text()).toContain(SLA_BREACH_LABEL.resolution)
  })

  it('TC-SLA-FE-05: badge KHÔNG leak chữ English/"breached" thô', async () => {
    listIncidents.value = [{
      name: 'IR-2026-0105', asset: 'AC-ASSET-2026-0005', asset_name: 'ECG',
      severity: 'High', status: 'In Progress', incident_type: 'Failure',
      description: 'Quá hạn cả 2', reported_at: '2026-04-05 08:00:00',
      response_breached: 0, resolution_breached: 0,
      is_response_breached: 1, is_resolution_breached: 1,
    }]
    const w = mountTracked(IncidentListView, { global: { stubs: listStubs } })
    await flushPromises()
    const t = w.text().toLowerCase()
    expect(t).not.toContain('breached')
    expect(t).not.toContain('resolution_breached')
    expect(t).not.toContain('response_breached')
  })
})

// ════════════════════════════════════════════════════════════════════════════
// IMM12DashboardView — tile đọc stats live + active_incidents badge derived
// ════════════════════════════════════════════════════════════════════════════
function baseStats(over: Record<string, unknown> = {}) {
  return {
    total: 5, open: 3, open_total: 4, investigating: 1, resolved: 0,
    closed: 1, cancelled: 0, critical: 1, high: 1, rca_pending: 0, chronic: 0,
    sla_response_breached: 0, sla_resolution_breached: 0, ...over,
  }
}

describe('IMM12DashboardView — tile SLA live + badge active_incidents derived (BR-12-13)', () => {
  beforeEach(() => {
    pushSpy.mockClear()
    fetchDashboardSpy.mockClear()
  })

  it('TC-SLA-FE-06: tile bind stats.sla_resolution_breached (live=2) — giữ nhãn VI "Vi phạm SLA xử lý"', async () => {
    dashboard.value = {
      stats: baseStats({ sla_response_breached: 1, sla_resolution_breached: 2 }),
      active_incidents: [], open_rcas: [], chronic_failures: [],
    }
    const w = mountTracked(IMM12DashboardView, { global: { stubs: dashStubs } })
    await flushPromises()
    const cards = w.findAll('.kpi-card')
    const resCard = cards.find(c => c.text().includes('Vi phạm SLA xử lý'))
    const respCard = cards.find(c => c.text().includes('Vi phạm SLA tiếp nhận'))
    expect(resCard, 'phải có tile "Vi phạm SLA xử lý"').toBeTruthy()
    expect(respCard, 'phải có tile "Vi phạm SLA tiếp nhận"').toBeTruthy()
    expect(resCard!.text()).toContain('2')
    expect(respCard!.text()).toContain('1')
    // Nhãn VI giữ nguyên, không leak English.
    expect(w.text()).not.toMatch(/SLA breach|breached/i)
  })

  it('TC-SLA-FE-07: active_incidents badge đọc is_*_breached (derived) dù cờ thô=0', async () => {
    dashboard.value = {
      stats: baseStats({ sla_resolution_breached: 1 }),
      active_incidents: [{
        name: 'IR-2026-0201', asset: 'AC-ASSET-2026-0009', asset_name: 'Máy thở',
        severity: 'High', status: 'In Progress',
        reported_at: '2026-04-09 08:00:00',
        response_breached: 0, resolution_breached: 0,
        is_response_breached: 0, is_resolution_breached: 1,
      }],
      open_rcas: [], chronic_failures: [],
    }
    const w = mountTracked(IMM12DashboardView, { global: { stubs: dashStubs } })
    await flushPromises()
    expect(w.text()).toContain(SLA_BREACH_LABEL.resolution)
  })

  it('TC-SLA-FE-08: stats thiếu (BE bản cũ) → tile 0, KHÔNG vỡ', async () => {
    dashboard.value = {
      stats: baseStats({ sla_response_breached: undefined, sla_resolution_breached: undefined }),
      active_incidents: [], open_rcas: [], chronic_failures: [],
    }
    const w = mountTracked(IMM12DashboardView, { global: { stubs: dashStubs } })
    await flushPromises()
    const respCard = w.findAll('.kpi-card').find(c => c.text().includes('Vi phạm SLA tiếp nhận'))
    expect(respCard!.text()).toContain('0')
  })
})
