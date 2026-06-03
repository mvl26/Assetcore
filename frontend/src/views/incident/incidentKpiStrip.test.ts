// TDD — IMM-12 KPI strip (worklist): tile severity bind OPEN-SET SoT
// (critical_open / high_open qua open_incident_filter()), KHÔNG global critical/high.
// Kill mâu thuẫn thị giác strip-vs-table khi drill ?open=1 / ?severity=.
// RED trước fix: binding còn s.critical (=2) → tile 'nghiêm trọng' render 2, không 1.
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises, type VueWrapper } from '@vue/test-utils'
import { ref } from 'vue'

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
// stats cấu hình được per-test (mock KPI strip binding).
const storeStats = ref<Record<string, unknown> | null>(null)
vi.mock('@/stores/imm12', () => ({
  useImm12Store: () => ({
    get incidents() { return [] },
    pagination: { page: 1, page_size: 20, total: 0, total_pages: 1 },
    loading: false,
    error: null,
    get stats() { return storeStats.value },
    fetchList: fetchListSpy,
    fetchStats: fetchStatsSpy,
  }),
}))

vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({ can: () => true }),
}))

import IncidentListView from './IncidentListView.vue'

// KPI strip (WorkOrderKpiStrip + KpiCard) KHÔNG stub → label + value render thật.
const stubs = {
  PageHeader: true, FilterToggleButton: true, ListFilterBar: true,
  BasePagination: true, StatusBadge: true, SkeletonLoader: true,
  SlaBreachBadge: true, RouterLink: true,
}

// Trích value của tile theo label (KpiCard render label + value cùng card).
function tileValue(w: VueWrapper, label: string): string | null {
  const strip = w.find('[data-testid="wo-kpi-strip"]')
  if (!strip.exists()) return null
  const cards = strip.element.querySelectorAll('div')
  for (const card of Array.from(cards)) {
    const text = card.textContent ?? ''
    if (text.includes(label)) {
      // số trong card (loại bỏ label chữ) — match cụm digit đầu tiên.
      const m = text.replace(label, '').match(/\d[\d.,]*/)
      if (m) return m[0]
    }
  }
  return null
}

describe('IncidentListView — KPI strip severity OPEN-SET (TC-12-STAT FE)', () => {
  beforeEach(() => {
    fetchListSpy.mockClear()
    fetchStatsSpy.mockClear()
    routeQuery.value = {}
    storeStats.value = null
  })

  it("tile 'nghiêm trọng đang mở' bind critical_open (1), KHÔNG critical global (2)", async () => {
    storeStats.value = {
      total: 5, open: 3, open_total: 4, investigating: 0, resolved: 0,
      closed: 1, cancelled: 0,
      critical: 2, high: 2, critical_open: 1, high_open: 2,
      rca_pending: 0, chronic: 0, sla_response_breached: 0, sla_resolution_breached: 0,
    }
    const w = mountTracked(IncidentListView, { global: { stubs } })
    await flushPromises()
    // Label nêu rõ open-set semantics.
    expect(w.text()).toContain('Sự cố nghiêm trọng đang mở')
    expect(w.text()).toContain('Sự cố mức cao đang mở')
    // Value bám open-set, KHÔNG global (2).
    expect(tileValue(w, 'Sự cố nghiêm trọng đang mở')).toBe('1')
    expect(tileValue(w, 'Sự cố mức cao đang mở')).toBe('2')
  })

  it('forward-compat: stats KHÔNG có critical_open/high_open (undefined) → tile render 0, KHÔNG vỡ', async () => {
    storeStats.value = {
      total: 5, open: 3, open_total: 4, investigating: 0, resolved: 0,
      closed: 1, cancelled: 0,
      critical: 2, high: 2,           // KHÔNG có critical_open/high_open
      rca_pending: 0, chronic: 0, sla_response_breached: 0, sla_resolution_breached: 0,
    }
    const w = mountTracked(IncidentListView, { global: { stubs } })
    await flushPromises()
    expect(tileValue(w, 'Sự cố nghiêm trọng đang mở')).toBe('0')
    expect(tileValue(w, 'Sự cố mức cao đang mở')).toBe('0')
  })

  it('chronic/closed tile KHÔNG đổi (regression round-18/21)', async () => {
    storeStats.value = {
      total: 5, open: 3, open_total: 4, investigating: 0, resolved: 0,
      closed: 7, cancelled: 0,
      critical: 2, high: 2, critical_open: 1, high_open: 2,
      rca_pending: 0, chronic: 3, sla_response_breached: 0, sla_resolution_breached: 0,
    }
    const w = mountTracked(IncidentListView, { global: { stubs } })
    await flushPromises()
    expect(tileValue(w, 'Lặp lại (Chronic)')).toBe('3')
    expect(tileValue(w, 'Đã đóng')).toBe('7')
  })
})
