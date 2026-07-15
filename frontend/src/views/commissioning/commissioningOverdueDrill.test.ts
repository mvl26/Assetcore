// TDD — IMM-04 BR-04-10: thẻ KPI "Quá hạn SLA" click-to-drill → filters.overdue=1.
// Cùng lớp lỗi drill-down: card count phải == drill rows (cùng SoT BE). FE chỉ
// chịu trách nhiệm đẩy đúng cờ `overdue` xuống store.fetchList; conjoin/SoT ở BE.
// Mô phỏng calibrationScheduleListDrilldown.test.ts.
import { describe, it, expect, vi, beforeEach } from 'vitest'
// CR-AFFORD: view giờ gọi useCapabilities() ở setup (gate nút Tạo) → mock để mount không cần Pinia.
vi.mock('@/composables/useCapabilities', () => ({ useCapabilities: () => ({ can: () => true }) }))
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'

const routeQuery = ref<Record<string, string>>({})
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useRoute: () => ({ get query() { return routeQuery.value } }),
}))

// store.fetchList là điểm round-trip xuống BE. Spy để assert filters truyền xuống.
const fetchListSpy = vi.fn().mockResolvedValue(undefined)
const fetchDashboardSpy = vi.fn().mockResolvedValue(undefined)
const dashboardStats = ref<{ kpis: Record<string, number> } | null>({
  kpis: { pending_count: 5, hold_count: 1, open_nc_count: 2, released_this_month: 3, overdue_sla: 4 },
})

vi.mock('@/stores/imm04', () => ({
  useCommissioningStore: () => ({
    fetchList: fetchListSpy,
    fetchDashboardStats: fetchDashboardSpy,
    refreshList: vi.fn(),
    get dashboardStats() { return dashboardStats.value },
    list: [],
    listLoading: false,
    error: null,
    pagination: { page: 1, page_size: 20, total: 0, total_pages: 0 },
  }),
}))

const stubs = {
  PageHeader: true, FilterToggleButton: true, ListFilterBar: true,
  BasePagination: true, SkeletonLoader: true, StatusBadge: true,
  WorkOrderKpiStrip: true, 'router-link': true, RouterLink: true,
}

import CommissioningListView from './CommissioningListView.vue'

function lastFilters(): Record<string, unknown> {
  const call = fetchListSpy.mock.calls[fetchListSpy.mock.calls.length - 1]
  return (call?.[0] ?? {}) as Record<string, unknown>
}

describe('CommissioningListView — overdue KPI drill (BR-04-10)', () => {
  beforeEach(() => { fetchListSpy.mockClear(); routeQuery.value = {} })

  it('click thẻ overdue (onKpiClick) → fetchList với filters.overdue=true; chip "Quá hạn" hiện', async () => {
    const w = mount(CommissioningListView, { global: { stubs } })
    await flushPromises()
    // kpiItems: index 4 = "Quá hạn SLA" (overdueFilter). Mô phỏng @kpi-click.
    ;(w.vm as any).onKpiClick(4)
    await flushPromises()
    expect(lastFilters().overdue).toBe(true)
    const chips = (w.vm as any).activeChips as { key: string; label: string }[]
    expect(chips.some(c => c.key === 'overdue' && c.label === 'Quá hạn')).toBe(true)
  })

  it('removeChip("overdue") → filters.overdue=false; fetchList không kèm overdue', async () => {
    const w = mount(CommissioningListView, { global: { stubs } })
    await flushPromises()
    ;(w.vm as any).onKpiClick(4)
    await flushPromises()
    ;(w.vm as any).clearChip('overdue')
    await flushPromises()
    expect((w.vm as any).filters.overdue).toBe(false)
    expect(lastFilters().overdue).toBeUndefined()
  })

  it('resetFilters xóa cờ overdue (fetchList payload rỗng overdue)', async () => {
    const w = mount(CommissioningListView, { global: { stubs } })
    await flushPromises()
    ;(w.vm as any).onKpiClick(4)
    await flushPromises()
    ;(w.vm as any).resetFilters()
    await flushPromises()
    expect((w.vm as any).filters.overdue).toBe(false)
    expect(lastFilters().overdue).toBeUndefined()
  })

  it('không drill → fetchList KHÔNG kèm overdue (cờ tắt mặc định)', async () => {
    mount(CommissioningListView, { global: { stubs } })
    await flushPromises()
    expect(lastFilters().overdue).toBeUndefined()
  })

  it('click thẻ state (index 1 = Clinical Hold) → quickFilter workflow_state, KHÔNG bật overdue', async () => {
    const w = mount(CommissioningListView, { global: { stubs } })
    await flushPromises()
    ;(w.vm as any).onKpiClick(1)
    await flushPromises()
    expect(lastFilters().workflow_state).toBe('Clinical Hold')
    expect(lastFilters().overdue).toBeUndefined()
  })

  it('route.query.filter=overdue → khởi tạo cờ overdue bật, drill ngay khi mount', async () => {
    routeQuery.value = { filter: 'overdue' }
    mount(CommissioningListView, { global: { stubs } })
    await flushPromises()
    expect(lastFilters().overdue).toBe(true)
  })
})
