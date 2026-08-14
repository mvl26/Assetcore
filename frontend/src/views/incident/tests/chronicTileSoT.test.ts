// TDD — Core Doc §06 IMM-12 (BR-12-12): KPI 'Mãn tính'/'Lặp lại (Chronic)' bám
// SoT LIVE rolling-window 90d = SỐ NHÓM (asset,fault_code) (== chronic_failure_count
// / len(get_chronic_failures()) ở BE), KHÔNG đếm cờ stale chronic_failure_flag.
//
// Mục tiêu chứng minh (kill divergence tile-vs-panel trên CÙNG 1 màn hình):
//   FE TC-IMM12-CHRONIC-FE-01: IMM12DashboardView tile 'Mãn tính' = stats.chronic
//     (số live từ payload mock), KHÔNG hardcode, KHÔNG đếm flag. Trên cùng payload
//     {stats.chronic: 2, chronic_failures: [g1,g2]} → tile '2' == panel rows (2).
//     RED-prove: nếu tile bind sai (vd chronic_failures.length nhưng panel cap [:5],
//     hoặc literal/0/đếm cờ) → assert tile==stats.chronic FAIL.
//   FE TC-IMM12-CHRONIC-FE-02: IncidentListView KPI strip 'Lặp lại (Chronic)' =
//     stats.chronic mới (live) + badge per-row '⚠ Lặp lại' theo ir.chronic_failure_flag
//     GIỮ NGUYÊN (row có flag=1 → badge hiện) — no-regression.
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises, type VueWrapper } from '@vue/test-utils'
import { ref } from 'vue'

const mounted: VueWrapper[] = []
function mountTracked(...args: Parameters<typeof mount>): VueWrapper {
  const w = mount(...args) as VueWrapper
  mounted.push(w)
  return w
}
afterEach(() => { while (mounted.length) mounted.pop()!.unmount() })

// ── Mocks dùng chung ────────────────────────────────────────────────────────
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useRoute: () => ({ query: {} }),
}))
vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({ can: () => true }),
}))

// Store config được per-test.
const dashboard = ref<Record<string, unknown> | null>(null)
const listStats = ref<Record<string, unknown> | null>(null)
const listItems = ref<Record<string, unknown>[]>([])
const fetchDashboardSpy = vi.fn().mockResolvedValue(undefined)
const fetchListSpy = vi.fn().mockResolvedValue(undefined)
const fetchStatsSpy = vi.fn().mockResolvedValue(undefined)
vi.mock('@/stores/imm12', () => ({
  useImm12Store: () => ({
    // Dashboard view surface
    get dashboard() { return dashboard.value },
    dashboardLoading: false,
    dashboardError: null,
    fetchDashboard: fetchDashboardSpy,
    // List view surface
    get incidents() { return listItems.value },
    pagination: { page: 1, page_size: 20, total: listItems.value.length, total_pages: 1 },
    loading: false,
    error: null,
    get stats() { return listStats.value },
    fetchList: fetchListSpy,
    fetchStats: fetchStatsSpy,
  }),
}))

import IMM12DashboardView from '@/views/incident/IMM12DashboardView.vue'
import IncidentListView from '@/views/incident/IncidentListView.vue'

const dashStubs = { PageHeader: true, SlaBreachBadge: true }
const listStubs = {
  PageHeader: true, FilterToggleButton: true, ListFilterBar: true,
  BasePagination: true, StatusBadge: true, SkeletonLoader: true,
  SlaBreachBadge: true, RouterLink: true,
}

function baseStats(over: Record<string, unknown> = {}) {
  return {
    total: 9, open: 3, open_total: 4, investigating: 1, resolved: 0,
    closed: 1, cancelled: 0, critical: 1, high: 1,
    critical_open: 1, high_open: 1,
    rca_pending: 0, chronic: 0,
    sla_response_breached: 0, sla_resolution_breached: 0, ...over,
  }
}

function chronicGroup(asset: string, fault: string, count: number) {
  return { asset, asset_name: asset, fault_code: fault, count, last_reported: '2026-06-01 10:00:00' }
}

// Tìm tile dashboard theo NHÃN (robust với reorder) — KpiCard render label+value.
function dashTileText(w: VueWrapper, label: string): string | null {
  const cards = w.findAll('.kpi-card')
  for (const c of cards) {
    if (c.text().includes(label)) return c.text()
  }
  return null
}

// Trích value tile KPI strip (list view) theo label.
function stripTileValue(w: VueWrapper, label: string): string | null {
  const strip = w.find('[data-testid="wo-kpi-strip"]')
  if (!strip.exists()) return null
  const cards = strip.element.querySelectorAll('div')
  for (const card of Array.from(cards)) {
    const text = card.textContent ?? ''
    if (text.includes(label)) {
      const m = text.replace(label, '').match(/\d[\d.,]*/)
      if (m) return m[0]
    }
  }
  return null
}

// ── FE TC-IMM12-CHRONIC-FE-01: dashboard tile == stats.chronic == panel rows ────
describe('IMM12DashboardView — tile "Mãn tính" = stats.chronic live-SoT (BR-12-12)', () => {
  beforeEach(() => {
    fetchDashboardSpy.mockClear()
    dashboard.value = null
  })

  it('FE-01: tile bám stats.chronic (2) từ payload + KHỚP số nhóm panel chronic_failures (2)', async () => {
    const groups = [chronicGroup('AC-ASSET-A', 'E01', 4), chronicGroup('AC-ASSET-B', 'E02', 3)]
    dashboard.value = {
      stats: baseStats({ chronic: 2 }),
      active_incidents: [], open_rcas: [],
      chronic_failures: groups,
    }
    const w = mountTracked(IMM12DashboardView, { global: { stubs: dashStubs } })
    await flushPromises()

    const tile = dashTileText(w, 'Mãn tính')
    expect(tile, 'phải có tile "Mãn tính"').toBeTruthy()
    // tile render đúng stats.chronic=2 (số live từ payload), KHÔNG hardcode/0.
    expect(tile).toContain('2')

    // INVARIANT count==panel: tile == số nhóm hiển thị ở panel "Hỏng hóc mãn tính".
    // (payload có ≤5 nhóm ⇒ so trực tiếp stats.chronic với số dòng panel.)
    const chronicTableRows = w.findAll('tbody tr')
    expect(chronicTableRows.length).toBe(2)
    expect(Number(dashboard.value!.stats && (dashboard.value!.stats as Record<string, number>).chronic))
      .toBe(chronicTableRows.length)
  })

  it('FE-01 RED-prove: nếu stats.chronic=6 (số nhóm tổng) còn panel cap [:5]=1 → tile theo PAYLOAD (6), KHÔNG theo length panel', async () => {
    // Mô phỏng BE: >5 nhóm → panel cap top-5 (ở đây mock panel 1 dòng để tương phản),
    // nhưng count tile = TỔNG nhóm (stats.chronic). Tile PHẢI hiện 6 (payload), nếu
    // ai đó đổi binding sang chronic_failures.length (=1) → test này FAIL ⇒ bắt bug.
    dashboard.value = {
      stats: baseStats({ chronic: 6 }),
      active_incidents: [], open_rcas: [],
      chronic_failures: [chronicGroup('AC-ASSET-C', 'E09', 5)],
    }
    const w = mountTracked(IMM12DashboardView, { global: { stubs: dashStubs } })
    await flushPromises()
    const tile = dashTileText(w, 'Mãn tính')
    expect(tile).toContain('6')
    // chứng minh KHÔNG bind nhầm sang length panel (1).
    expect(tile).not.toMatch(/\b1\b/)
  })

  it('FE-01 lifecycle: hết nhóm live (aged-out >90d) → stats.chronic=0 → tile hiện 0 (KHÔNG stale >0)', async () => {
    // BE đã trả chronic=0 (không còn nhóm live) dù cờ chronic_failure_flag có thể vẫn
    // =1 trên các incident cũ. Tile phải hiện 0 — không có "phantom chronic".
    dashboard.value = {
      stats: baseStats({ chronic: 0 }),
      active_incidents: [], open_rcas: [],
      chronic_failures: [],
    }
    const w = mountTracked(IMM12DashboardView, { global: { stubs: dashStubs } })
    await flushPromises()
    const tile = dashTileText(w, 'Mãn tính')
    expect(tile).toContain('0')
    // panel cũng rỗng → empty state, KHÔNG còn divergence tile>0 vs panel rỗng.
    expect(w.text()).toContain('Không phát hiện hỏng hóc mãn tính')
  })

  it('FE-01: tile chronic KHÔNG vỡ khi stats.chronic thiếu (forward-compat) → 0', async () => {
    dashboard.value = {
      stats: baseStats({ chronic: undefined }),
      active_incidents: [], open_rcas: [], chronic_failures: [],
    }
    const w = mountTracked(IMM12DashboardView, { global: { stubs: dashStubs } })
    await flushPromises()
    expect(dashTileText(w, 'Mãn tính')).toContain('0')
  })
})

// ── FE TC-IMM12-CHRONIC-FE-02: list strip = stats.chronic + badge per-row giữ ────
describe('IncidentListView — strip "Lặp lại (Chronic)" = stats.chronic + badge per-row giữ (BR-12-12)', () => {
  beforeEach(() => {
    fetchListSpy.mockClear()
    fetchStatsSpy.mockClear()
    listStats.value = null
    listItems.value = []
  })

  it('FE-02: KPI strip "Lặp lại (Chronic)" bám stats.chronic mới (live=2)', async () => {
    listStats.value = baseStats({ chronic: 2, closed: 5 })
    const w = mountTracked(IncidentListView, { global: { stubs: listStubs } })
    await flushPromises()
    // strip kế thừa số live mới từ stats.chronic, KHÔNG recompute ở FE.
    expect(stripTileValue(w, 'Lặp lại (Chronic)')).toBe('2')
    expect(stripTileValue(w, 'Đã đóng')).toBe('5')
  })

  it('FE-02 no-regression: badge per-row "⚠ Lặp lại" theo ir.chronic_failure_flag (row flag=1 → badge hiện; flag=0 → ẩn)', async () => {
    listStats.value = baseStats({ chronic: 1 })
    listItems.value = [
      {
        name: 'IR-2026-9001', asset: 'AC-ASSET-A', asset_name: 'Máy thở A',
        severity: 'High', status: 'Open', reported_at: '2026-06-01 09:00:00',
        fault_code: 'E01', chronic_failure_flag: 1,
      },
      {
        name: 'IR-2026-9002', asset: 'AC-ASSET-B', asset_name: 'Bơm tiêm B',
        severity: 'Low', status: 'Open', reported_at: '2026-06-01 10:00:00',
        fault_code: 'E02', chronic_failure_flag: 0,
      },
    ]
    const w = mountTracked(IncidentListView, { global: { stubs: listStubs } })
    await flushPromises()
    const rows = w.findAll('tbody tr')
    // ≥1 dòng có badge "Lặp lại", ≥1 dòng KHÔNG (chứng minh badge bám flag per-row,
    // không phải hằng/strip-level).
    const badged = rows.filter(r => r.text().includes('Lặp lại'))
    expect(badged.length).toBe(1)
    // dòng flag=1 (IR-2026-9001) có badge; dòng flag=0 (9002) không.
    expect(badged[0].text()).toContain('IR-2026-9001')
    const flag0Row = rows.find(r => r.text().includes('IR-2026-9002'))
    expect(flag0Row, 'phải có dòng IR-2026-9002').toBeTruthy()
    expect(flag0Row!.text()).not.toContain('Lặp lại')
  })
})
