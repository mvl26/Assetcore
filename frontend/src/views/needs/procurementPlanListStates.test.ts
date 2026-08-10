// TC-UX3-10 (AC-UX-041/044/046) — /procurement-plans: 4 trạng thái + «Thử lại» (biến thể Pinia).
//
// Bug gốc đo trên đĩa 2026-07-31: dải lỗi `.alert-error` có nút «×» gọi `store.clearError()`
// — nút GIẢ DẠNG thử lại: chỉ xoá dải lỗi, KHÔNG nạp lại gì; danh sách vẫn rỗng nên màn
// tụt xuống «Không có kế hoạch nào phù hợp» ⇒ lỗi giả dạng rỗng.
// Đây là biến thể store-Pinia (đối trọng với 3 màn dùng ref cục bộ) — chứng minh cùng một
// khuôn ListPageShell dùng được cho cả hai kiểu quản lý trạng thái.
//
// ⚠️ Dải KPI: theo docs/ui-ux/02_LIST_PAGE_SHELL.md §2.2, `#summary` ẨN ở trạng thái lỗi —
// số 0 tính từ tập rỗng là *tín hiệu giả* cùng lớp với false-empty. Bộ lọc thì BẮT BUỘC
// còn (A6). Test dưới khoá đúng quyết định đó.
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { reactive } from 'vue'
import { mount, flushPromises, enableAutoUnmount } from '@vue/test-utils'

enableAutoUnmount(afterEach)

vi.mock('@/api/imm01', () => ({
  createProcurementPlan: vi.fn(),
  listNeedsRequests: vi.fn().mockResolvedValue({ items: [], total: 0, page: 1, page_size: 100 }),
}))

const fakeStore = reactive({
  plans: [] as unknown[],
  loading: false,
  error: null as string | null,
  fetchPlans: vi.fn(),
  clearError: vi.fn(() => { fakeStore.error = null }),
})
vi.mock('@/stores/imm01', () => ({ useImm01Store: () => fakeStore }))
vi.mock('@/composables/useCapabilities', () => ({ useCapabilities: () => ({ can: () => true }) }))
vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())

import ProcurementPlanListView from './ProcurementPlanListView.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'

const PLANS = [
  { name: 'PP-2026-0001', plan_year: 2026, plan_period: 'Q1', budget_envelope: 5_000_000_000,
    allocated_capex: 1_000_000_000, utilization_pct: 20, workflow_state: 'Draft' },
  { name: 'PP-2026-0002', plan_year: 2026, plan_period: 'Q2', budget_envelope: 3_000_000_000,
    allocated_capex: 2_400_000_000, utilization_pct: 80, workflow_state: 'Active' },
]

const stubs = { PageHeader: true, FilterToggleButton: true, StatusBadge: true, CurrencyInput: true }

async function mountView() {
  const w = mount(ProcurementPlanListView, { global: { stubs } })
  await flushPromises()
  return w
}

function state(w: ReturnType<typeof mount>) {
  return w.find('[data-testid="list-page-shell"]').attributes('data-state')
}
function retryControls(w: ReturnType<typeof mount>) {
  return w.findAll('button').filter((b) => (b.attributes('aria-label') ?? b.text()).trim() === 'Thử lại')
}

describe('/procurement-plans — 4 trạng thái loại trừ + thử lại (TC-UX3-10)', () => {
  beforeEach(() => {
    fakeStore.plans = []
    fakeStore.error = null
    fakeStore.loading = false
    fakeStore.clearError.mockClear()
    fakeStore.fetchPlans.mockReset().mockImplementation(async () => { fakeStore.plans = PLANS })
  })

  it('(a) đang tải ⇒ KHUNG XƯƠNG (cờ loading do VIEW giữ, store không set — AC-UX-044)', async () => {
    fakeStore.fetchPlans.mockImplementation(() => new Promise(() => {}))
    const w = await mountView()
    expect(state(w)).toBe('loading')
    expect(w.find('[data-testid="list-skeleton"]').exists()).toBe(true)
    expect(w.text()).not.toContain('Đang tải...')
    expect(w.findAll('table')).toHaveLength(0)
  })

  it('(b) lỗi ⇒ ui-error thay cho banner alert-error; 0 chuỗi rỗng cũ', async () => {
    fakeStore.fetchPlans.mockImplementation(async () => { fakeStore.error = 'Máy chủ trả về 500.' })
    const w = await mountView()
    expect(state(w)).toBe('error')
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(true)
    expect(w.find('.alert-error').exists()).toBe(false)
    expect(w.find('[data-testid="ui-empty"]').exists()).toBe(false)
    expect(w.html()).not.toContain('Không có kế hoạch nào phù hợp')
    expect(w.html()).not.toContain('Không có dữ liệu')
    expect(retryControls(w)).toHaveLength(1)
  })

  it('(c) rỗng ⇒ ui-empty có câu hướng dẫn + lối tạo kế hoạch đầu tiên', async () => {
    fakeStore.fetchPlans.mockImplementation(async () => { fakeStore.plans = [] })
    const w = await mountView()
    expect(state(w)).toBe('empty')
    const empty = w.find('[data-testid="ui-empty"]')
    expect(empty.exists()).toBe(true)
    expect(empty.text()).toContain('Chưa có kế hoạch mua sắm nào')
    expect(empty.text()).toMatch(/Hãy|Bấm|Nhấn|Tạo /)
    expect(empty.findAll('button').some((b) => b.text().includes('Tạo kế hoạch'))).toBe(true)
  })

  it('(d) có dữ liệu ⇒ đúng N dòng, 0 ui-empty, 0 ui-error', async () => {
    const w = await mountView()
    expect(state(w)).toBe('content')
    expect(w.findAll('tbody tr')).toHaveLength(PLANS.length)
    expect(w.find('[data-testid="ui-empty"]').exists()).toBe(false)
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(false)
  })

  it('(e) bấm «Thử lại» ⇒ store.fetchPlans gọi lần 2 (KHÔNG phải chỉ clearError)', async () => {
    fakeStore.fetchPlans
      .mockImplementationOnce(async () => { fakeStore.error = 'Mất kết nối.' })
      .mockImplementationOnce(async () => { fakeStore.plans = PLANS })
    const w = await mountView()
    expect(fakeStore.fetchPlans).toHaveBeenCalledTimes(1)
    await retryControls(w)[0].trigger('click')
    await flushPromises()
    expect(fakeStore.fetchPlans).toHaveBeenCalledTimes(2)
    expect(state(w)).toBe('content')
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(false)
  })

  it('(f) bộ lọc KHÔNG biến mất khi lỗi', async () => {
    fakeStore.fetchPlans.mockImplementation(async () => { fakeStore.error = 'Bộ lọc không hợp lệ.' })
    const w = await mountView()
    expect(w.find('[data-testid="list-filters"]').exists()).toBe(true)
    expect(w.findComponent(ListFilterBar).exists()).toBe(true)
  })

  it('(g) dải KPI: hiện khi có dữ liệu/rỗng, ẨN khi lỗi (§2.2 — số 0 từ tập rỗng là tín hiệu giả)', async () => {
    const ok = await mountView()
    const summary = ok.find('[data-testid="list-summary"]')
    expect(summary.exists()).toBe(true)
    expect(summary.text()).toContain('Tổng kế hoạch')

    fakeStore.fetchPlans.mockImplementation(async () => { fakeStore.error = 'Máy chủ trả về 500.' })
    const bad = await mountView()
    expect(bad.find('[data-testid="list-summary"]').exists()).toBe(false)
  })
})
