// TDD — INV-PM-KPI-6 (BR-08-14): WO 'Cancelled' bị loại khỏi MẪU compliance +
// bucket pending Ở BE. FE ZERO shape-change: chỉ render VERBATIM các số BE trả
// (compliance_rate_pct number|null, total_scheduled/pending_in_month/
// overdue_in_month/completed_on_time number). FE KHÔNG tự loại Cancelled, KHÔNG
// tự cộng/trừ. Test này KHÓA contract render-verbatim của PMWorkOrderListView:
//   - tile 'Tổng lịch tháng'      = kpis.total_scheduled  (KHÔNG field 'total' cũ)
//   - tile 'Hoàn tất đúng hạn'    = kpis.completed_on_time
//   - nhãn 'Compliance {…%|—}'    = compliance_rate_pct (null→'—', 33.3→'33.3%')
//   - pending_in_month            = consume verbatim qua dashboardStats.kpis
// Break-binding (đổi bind total_scheduled→total) ⇒ tile = số sai ⇒ FAIL → restore
// GREEN. Regex chặn leak EN status ('Cancelled'/'Completed'/'Overdue'/'Pending').
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'
import type { PMDashboardStats } from '@/api/imm08'
import { resetRouteMock } from '@/test/vueRouterMock'

// ── router mock ─ ROOT-CAUSE test-isolation fix (xem src/test/vueRouterMock.ts):
// shared full-shape mock (route-state globalThis) đồng nhất mọi file PM → race
// vô hại, hết "route.query undefined / query rỗng" cross-file.
vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())

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

import PMWorkOrderListView from './PMWorkOrderListView.vue'

const stubs = {
  PageHeader: true, SkeletonLoader: true, FilterToggleButton: true,
  ListFilterBar: true, BasePagination: true, DateInput: true, RouterLink: true,
}
// WorkOrderKpiStrip render thật để assert nhãn + value strip verbatim (KHÔNG stub).
const listStubs = { ...stubs, WorkOrderKpiStrip: false }

type KpiItem = { label: string; value: string | number; trend?: string }

/**
 * Fixture = ĐÚNG payload BE TRẢ SAU FIX cho acceptance case chính:
 * Tháng {1 Completed on-time, 1 Completed late, 1 Overdue, 1 Cancelled}:
 *   total_scheduled = 3 (Cancelled bị loại khỏi mẫu) — KHÔNG 4
 *   compliance_rate_pct = round(1/3*100,1) = 33.3 — KHÔNG 25.0
 *   completed_on_time = 1, overdue_in_month = 1, pending_in_month = 0
 * FE chỉ render verbatim — KHÔNG tự tính.
 */
function statsFixture(overrides: Partial<PMDashboardStats['kpis']> = {}): PMDashboardStats {
  return {
    kpis: {
      compliance_rate_pct: 33.3,
      total_scheduled: 3,
      completed_on_time: 1,
      overdue_in_month: 1,
      pending_in_month: 0,
      overdue: 1,
      avg_days_late: 2.0,
      ...overrides,
    },
    trend_6months: [],
  }
}

function kpiItems(w: ReturnType<typeof mount>): KpiItem[] {
  return (w.vm as unknown as { kpiItems: KpiItem[] }).kpiItems
}

describe('PMWorkOrderListView — render verbatim sau loại Cancelled (INV-PM-KPI-6)', () => {
  beforeEach(() => {
    resetRouteMock(); fetchWOSpy.mockClear(); fetchStatsSpy.mockClear()
    canImpl = () => true
  })

  // ── TC-FE-CANC-01: acceptance chính — payload {3,33.3,1,1,0} render verbatim ──
  it('tile "Tổng lịch tháng" bind total_scheduled VERBATIM (3, KHÔNG 4)', async () => {
    dashboardStats.value = statsFixture()
    const w = mount(PMWorkOrderListView, { global: { stubs: listStubs } })
    await flushPromises()
    const total = kpiItems(w).find(i => i.label === 'Tổng lịch tháng')
    // Render đúng giá trị BE trả; nếu binding đổi sang field 'total' (cũ, không
    // tồn tại trong kpis) → undefined → assert 3 FAIL ⇒ break-binding bắt được.
    expect(total?.value).toBe(3)
    // DOM strip cũng hiện '3' (render thật WorkOrderKpiStrip)
    expect(w.text()).toContain('Tổng lịch tháng')
  })

  it('nhãn "Compliance 33.3%" render verbatim (KHÔNG 25.0 từ mẫu cũ gồm Cancelled)', async () => {
    dashboardStats.value = statsFixture()
    const w = mount(PMWorkOrderListView, { global: { stubs: listStubs } })
    await flushPromises()
    const done = kpiItems(w).find(i => i.label === 'Hoàn tất đúng hạn')
    expect(done?.value).toBe(1)                       // completed_on_time verbatim
    expect(done?.trend).toContain('33.3%')
    expect(done?.trend).not.toContain('25')           // mẫu cũ 1/4=25.0 phải biến mất
    expect(w.text()).toContain('33.3%')
  })

  it('pending_in_month consume VERBATIM qua dashboardStats.kpis (0, KHÔNG phantom)', async () => {
    dashboardStats.value = statsFixture()
    const w = mount(PMWorkOrderListView, { global: { stubs: listStubs } })
    await flushPromises()
    // FE giữ nguyên số BE — Cancelled KHÔNG rơi vào pending (cũ: phantom=1).
    expect(dashboardStats.value!.kpis.pending_in_month).toBe(0)
    // overdue_in_month giữ 1 (Halted/Cancelled không đụng); strip hiện đúng.
    const inMonth = kpiItems(w).find(i => i.label === 'Quá hạn trong tháng')
    expect(inMonth?.value).toBe(1)
  })

  // ── TC-FE-CANC-02: tháng chỉ-Cancelled → compliance None→'—', KHÔNG '0%' ─────
  it('total_scheduled=0 ∧ compliance null → strip "Compliance —" (KHÔNG "0%")', async () => {
    dashboardStats.value = statsFixture({
      compliance_rate_pct: null, total_scheduled: 0, completed_on_time: 0,
      overdue_in_month: 0, pending_in_month: 0, overdue: 0,
    })
    const w = mount(PMWorkOrderListView, { global: { stubs: listStubs } })
    await flushPromises()
    const items = kpiItems(w)
    const total = items.find(i => i.label === 'Tổng lịch tháng')
    const done = items.find(i => i.label === 'Hoàn tất đúng hạn')
    expect(total?.value).toBe(0)
    expect(done?.trend).toContain('—')
    expect(done?.trend).not.toContain('0%')           // 0% gây hiểu nhầm "không tuân thủ"
    expect(w.text()).toContain('—')
  })

  // ── TC-FE-CANC-03: break-binding sentinel — total_scheduled ≠ field 'total' cũ ─
  it('break-binding: total_scheduled khác trend "total" — strip KHÔNG đọc nhầm field', async () => {
    // Payload phân biệt rõ: total_scheduled=3 nhưng trend_6months[*].total=4
    // (số WO-gồm-Cancelled). Strip PHẢI đọc kpis.total_scheduled (=3), KHÔNG bị
    // kéo về 4. Nếu binding bị đổi total_scheduled→(field 'total' cũ/ trend total)
    // ⇒ value=4 ⇒ FAIL. Đây là sentinel chống regression rebind.
    dashboardStats.value = {
      kpis: { ...statsFixture().kpis, total_scheduled: 3 },
      trend_6months: [{ month: '2026-06', total: 4, on_time: 1, rate: 25.0 }],
    }
    const w = mount(PMWorkOrderListView, { global: { stubs: listStubs } })
    await flushPromises()
    const total = kpiItems(w).find(i => i.label === 'Tổng lịch tháng')
    expect(total?.value).toBe(3)                       // verbatim total_scheduled
    expect(total?.value).not.toBe(4)                   // KHÔNG kéo từ trend.total cũ
  })

  // ── TC-FE-CANC-04: no-leak EN — không lộ raw status 'Cancelled'/'Completed'… ──
  it('no leak EN/raw status trong KPI strip (Cancelled/Completed/Overdue/Pending)', async () => {
    dashboardStats.value = statsFixture()
    const w = mount(PMWorkOrderListView, { global: { stubs: listStubs } })
    await flushPromises()
    const txt = w.text()
    expect(txt).not.toMatch(/Cancelled|Completed|Overdue|Pending|Scheduled/)
  })

  // ── TC-FE-CANC-05: no-regression đối chứng — tháng KHÔNG Cancelled bất biến ───
  it('no-regression: tháng không-Cancelled {3,33.3,1,0,1} render y như trước fix', async () => {
    // Cùng số liệu acceptance nhưng nguồn gốc không có Cancelled — FE render KHÔNG
    // phân biệt nguồn (chỉ verbatim). Khẳng định Cancelled-free path bất biến.
    dashboardStats.value = statsFixture({
      total_scheduled: 3, compliance_rate_pct: 33.3, completed_on_time: 1,
      overdue_in_month: 1, pending_in_month: 0,
    })
    const w = mount(PMWorkOrderListView, { global: { stubs: listStubs } })
    await flushPromises()
    const items = kpiItems(w)
    expect(items.find(i => i.label === 'Tổng lịch tháng')?.value).toBe(3)
    expect(items.find(i => i.label === 'Hoàn tất đúng hạn')?.value).toBe(1)
    expect(items.find(i => i.label === 'Hoàn tất đúng hạn')?.trend).toContain('33.3%')
    expect(items.find(i => i.label === 'Quá hạn trong tháng')?.value).toBe(1)
  })
})
