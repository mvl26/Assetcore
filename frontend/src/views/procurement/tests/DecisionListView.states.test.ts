// TC-UX3-34 (AC-UX-047 · lô 2) — /procurement-decisions: 4 trạng thái danh sách + «Thử lại».
//
// Bug gốc đo trên đĩa 2026-08-04: banner `.alert-error` (`:252`) hiện SONG SONG với khối
// rỗng «Không có quyết định mua sắm phù hợp» (`:352`), và banner bind thẳng `store.error`
// — ô dùng CHUNG cho `fetchDecisions` VÀ `fetchKpis` (`stores/imm03.ts:110`) ⇒ chỉ-số
// hỏng cũng dựng banner trên danh sách đang có dữ liệu. Thêm mã chết: «Không có dữ liệu»
// (`:287`) nằm TRONG nhánh CÓ dữ liệu.
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises, enableAutoUnmount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { resetRouteMock } from '@/test/vueRouterMock'

enableAutoUnmount(afterEach)

const listDecisionsSpy = vi.fn()
const getDashboardKpisSpy = vi.fn()
// `importOriginal` + ghi đè ĐÚNG hàm nạp: `stores/imm03.ts` dùng `import * as api` nên
// module phải giữ đủ mọi export; liệt kê tay sẽ trôi lệch khi lớp API thêm hàm mới.
vi.mock('@/api/imm03', async (importOriginal) => ({
  ...(await importOriginal<Record<string, unknown>>()),
  listDecisions: (...a: unknown[]) => listDecisionsSpy(...a),
  getDashboardKpis: (...a: unknown[]) => getDashboardKpisSpy(...a),
}))
vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())

import DecisionListView from '@/views/procurement/DecisionListView.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'

const ROWS = [
  { name: 'PD-2026-0001', spec_ref: 'TS-2026-0001', winner_supplier: 'SUP-2026-00001',
    vendor_name: 'Công ty A', awarded_price: 1200000000, envelope_check_pct: 88,
    workflow_state: 'Awarded' },
  { name: 'PD-2026-0002', spec_ref: 'TS-2026-0002', winner_supplier: 'SUP-2026-00002',
    vendor_name: 'Công ty B', awarded_price: 850000000, envelope_check_pct: 101,
    workflow_state: 'PO Issued' },
]
const ok = (rows: unknown[]) => ({ items: rows, total: rows.length, page: 1, page_size: 20 })
const KPIS = { decision_states: { Awarded: 1, 'Pending Approval': 0, 'PO Issued': 1 } }

const stubs = { PageHeader: true, FilterToggleButton: true, KpiCard: true }

async function mountView() {
  const w = mount(DecisionListView, { global: { stubs } })
  await flushPromises()
  return w
}
function state(w: ReturnType<typeof mount>) {
  return w.find('[data-testid="list-page-shell"]').attributes('data-state')
}
function retryControls(w: ReturnType<typeof mount>) {
  return w.findAll('button').filter((b) => (b.attributes('aria-label') ?? b.text()).trim() === 'Thử lại')
}

describe('/procurement-decisions — 4 trạng thái loại trừ + thử lại (TC-UX3-34)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    resetRouteMock()
    listDecisionsSpy.mockReset().mockResolvedValue(ok(ROWS))
    getDashboardKpisSpy.mockReset().mockResolvedValue(KPIS)
  })

  it('(a) đang tải ⇒ khung xương, 0 nội dung, 0 nút «Thử lại»', async () => {
    listDecisionsSpy.mockReturnValue(new Promise(() => {}))
    const w = await mountView()
    expect(state(w)).toBe('loading')
    expect(w.find('[data-testid="list-skeleton"]').exists()).toBe(true)
    expect(w.findAll('[data-testid="list-content"]')).toHaveLength(0)
    expect(w.findAll('table')).toHaveLength(0)
    expect(retryControls(w)).toHaveLength(0)
  })

  it('(b) lỗi ⇒ ui-error + ĐÚNG 1 «Thử lại», KHÔNG còn banner alert-error song song', async () => {
    listDecisionsSpy.mockRejectedValue(new Error('Máy chủ trả về 500.'))
    const w = await mountView()
    expect(state(w)).toBe('error')
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(true)
    expect(w.findAll('.alert-error')).toHaveLength(0)
    expect(w.findAll('[data-testid="list-content"]')).toHaveLength(0)
    expect(w.find('[data-testid="ui-empty"]').exists()).toBe(false)
    expect(w.text()).not.toContain('Không có quyết định mua sắm phù hợp')
    expect(w.text()).not.toContain('Không có dữ liệu')
    expect(w.text()).toContain('Máy chủ trả về 500.')
    expect(retryControls(w)).toHaveLength(1)
  })

  it('(c) rỗng thật ⇒ ui-empty có câu hướng dẫn tiếng Việt, 0 nút «Thử lại»', async () => {
    listDecisionsSpy.mockResolvedValue(ok([]))
    const w = await mountView()
    expect(state(w)).toBe('empty')
    expect(w.find('[data-testid="ui-empty-title"]').text()).toBe('Chưa có quyết định mua sắm nào')
    expect(w.find('[data-testid="ui-empty-description"]').text())
      .toBe('Quyết định mua sắm được tạo sau khi chốt đánh giá nhà cung cấp.')
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(false)
    expect(retryControls(w)).toHaveLength(0)
  })

  it('(d) có dữ liệu ⇒ đúng N dòng trong list-data', async () => {
    const w = await mountView()
    expect(state(w)).toBe('content')
    expect(w.find('[data-testid="list-data"]').exists()).toBe(true)
    expect(w.findAll('tbody tr')).toHaveLength(ROWS.length)
    expect(w.find('[data-testid="ui-empty"]').exists()).toBe(false)
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(false)
  })

  it('(e) «Thử lại» gọi lại đúng hàm nạp 1 lần; lời gọi chỉ-số KHÔNG tăng', async () => {
    listDecisionsSpy.mockRejectedValueOnce(new Error('Mất kết nối.'))
    const w = await mountView()
    expect(state(w)).toBe('error')
    expect(listDecisionsSpy).toHaveBeenCalledTimes(1)
    const kpiCallsBefore = getDashboardKpisSpy.mock.calls.length
    await retryControls(w)[0].trigger('click')
    await flushPromises()
    expect(listDecisionsSpy).toHaveBeenCalledTimes(2)
    expect(getDashboardKpisSpy).toHaveBeenCalledTimes(kpiCallsBefore) // INV-UX3-21
    expect(state(w)).toBe('content')
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(false)
  })

  it('(f) loại trừ cấu trúc: đúng 1 shell, đúng 1 trạng thái; bộ lọc còn sống', async () => {
    listDecisionsSpy.mockRejectedValue(new Error('X'))
    const w = await mountView()
    expect(w.findAll('[data-testid="list-page-shell"]')).toHaveLength(1)
    const present = ['list-loading', 'ui-error', 'ui-empty', 'list-content']
      .filter((t) => w.find(`[data-testid="${t}"]`).exists())
    expect(present).toEqual(['ui-error'])
    expect(w.find('[data-testid="list-filters"]').exists()).toBe(true)
    expect(w.findComponent(ListFilterBar).exists()).toBe(true)
  })

  it('(f2) lỗi nạp CHỈ-SỐ không cướp trạng thái danh sách (INV-UX3-20)', async () => {
    // `fetchKpis` dùng CHUNG ô `store.error` với `fetchDecisions` (stores/imm03.ts:110).
    getDashboardKpisSpy.mockRejectedValue(new Error('Chỉ số hỏng.'))
    const w = await mountView()
    expect(state(w)).toBe('content')
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(false)
    expect(w.findAll('tbody tr')).toHaveLength(ROWS.length)
  })

  it('(g) «Xóa bộ lọc» khi ĐANG LỖI phải thoát được lỗi, không kẹt vĩnh viễn', async () => {
    // Dải bộ lọc còn sống ở trạng thái lỗi ⇒ `resetFilters` phải đi qua CÙNG đường
    // chụp lỗi, nếu không người dùng bấm reset xong vẫn thấy màn lỗi cũ.
    listDecisionsSpy.mockRejectedValueOnce(new Error('Mất kết nối.'))
    const w = await mountView()
    expect(state(w)).toBe('error')
    w.findComponent(ListFilterBar).vm.$emit('reset')
    await flushPromises()
    expect(state(w)).toBe('content')
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(false)
  })
})
