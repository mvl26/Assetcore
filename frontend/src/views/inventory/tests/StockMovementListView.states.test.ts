// TC-UX3-11 (AC-UX-047 · lô 1) — /stock-movements: 4 trạng thái danh sách + «Thử lại».
//
// Bug gốc đo trên đĩa 2026-08-03: `load()` (`StockMovementListView.vue:73`) có
// `try … finally` nhưng **0 `catch`** ⇒ API 500 để `rows` = [] ⇒ view rơi vào nhánh
// `v-else-if="rows.length === 0"` và in «Chưa có phiếu kho phù hợp.». Người dùng tin
// là kho KHÔNG có phiếu nào, và không có đường thử lại — *lỗi giả dạng rỗng*.
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises, enableAutoUnmount } from '@vue/test-utils'
import { resetRouteMock } from '@/test/vueRouterMock'

enableAutoUnmount(afterEach)

const listStockMovementsSpy = vi.fn()
vi.mock('@/api/inventory', () => ({
  listStockMovements: (...a: unknown[]) => listStockMovementsSpy(...a),
}))
vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({ can: () => true }),
}))
vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())

import StockMovementListView from '@/views/inventory/StockMovementListView.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'

const ROWS = [
  { name: 'SM-2026-0001', movement_type: 'Receipt', status: 'Draft', movement_date: '2026-07-01',
    from_warehouse: '', to_warehouse: 'WH-A', to_warehouse_name: 'Kho A', total_value: 1_000_000 },
  { name: 'SM-2026-0002', movement_type: 'Issue', status: 'Submitted', movement_date: '2026-07-02',
    from_warehouse: 'WH-A', from_warehouse_name: 'Kho A', to_warehouse: '', total_value: 2_000_000 },
]

const stubs = { PageHeader: true, FilterToggleButton: true }

async function mountView() {
  const w = mount(StockMovementListView, { global: { stubs } })
  await flushPromises()
  return w
}

/** Trạng thái khuôn đang render — đọc từ thẻ gốc của ListPageShell. */
function state(w: ReturnType<typeof mount>) {
  return w.find('[data-testid="list-page-shell"]').attributes('data-state')
}

function retryControls(w: ReturnType<typeof mount>) {
  return w.findAll('button').filter((b) => (b.attributes('aria-label') ?? b.text()).trim() === 'Thử lại')
}

describe('/stock-movements — 4 trạng thái loại trừ + thử lại (TC-UX3-11)', () => {
  beforeEach(() => {
    resetRouteMock()
    listStockMovementsSpy.mockReset().mockResolvedValue({ items: ROWS, pagination: { total: ROWS.length } })
  })

  it('(a) đang tải ⇒ khung xương, 0 nội dung, 0 nút «Thử lại»', async () => {
    listStockMovementsSpy.mockReturnValue(new Promise(() => {}))
    const w = await mountView()
    expect(state(w)).toBe('loading')
    expect(w.find('[data-testid="list-skeleton"]').exists()).toBe(true)
    expect(w.findAll('[data-testid="list-content"]')).toHaveLength(0)
    expect(retryControls(w)).toHaveLength(0)
  })

  it('(b) lỗi ⇒ ui-error + đúng 1 «Thử lại», KHÔNG còn chuỗi rỗng cũ', async () => {
    listStockMovementsSpy.mockRejectedValue(new Error('Máy chủ trả về 500.'))
    const w = await mountView()
    expect(state(w)).toBe('error')
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(true)
    expect(w.findAll('[data-testid="list-content"]')).toHaveLength(0)
    expect(w.find('[data-testid="ui-empty"]').exists()).toBe(false)
    expect(w.text()).not.toContain('Chưa có')
    expect(w.text()).not.toContain('Không có dữ liệu')
    expect(w.text()).toContain('Máy chủ trả về 500.')
    expect(retryControls(w)).toHaveLength(1)
  })

  it('(c) rỗng thật ⇒ ui-empty có câu hướng dẫn tiếng Việt, 0 nút «Thử lại»', async () => {
    listStockMovementsSpy.mockResolvedValue({ items: [], pagination: { total: 0 } })
    const w = await mountView()
    expect(state(w)).toBe('empty')
    expect(w.find('[data-testid="ui-empty-title"]').text()).toBe('Chưa có phiếu kho nào')
    expect(w.find('[data-testid="ui-empty-description"]').exists()).toBe(true)
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

  it('(e) «Thử lại» gọi lại đúng hàm nạp 1 lần ⇒ error → content', async () => {
    listStockMovementsSpy.mockRejectedValueOnce(new Error('Mất kết nối.'))
    const w = await mountView()
    expect(state(w)).toBe('error')
    expect(listStockMovementsSpy).toHaveBeenCalledTimes(1)
    await retryControls(w)[0].trigger('click')
    await flushPromises()
    expect(listStockMovementsSpy).toHaveBeenCalledTimes(2)
    expect(state(w)).toBe('content')
  })

  it('(f) loại trừ cấu trúc: đúng 1 shell, đúng 1 trạng thái tại mọi thời điểm', async () => {
    listStockMovementsSpy.mockRejectedValue(new Error('X'))
    const w = await mountView()
    expect(w.findAll('[data-testid="list-page-shell"]')).toHaveLength(1)
    const present = ['list-loading', 'ui-error', 'ui-empty', 'list-content']
      .filter((t) => w.find(`[data-testid="${t}"]`).exists())
    expect(present).toEqual(['ui-error'])
    // bộ lọc PHẢI sống khi lỗi — người dùng cần sửa bộ lọc gây lỗi
    expect(w.find('[data-testid="list-filters"]').exists()).toBe(true)
    expect(w.findComponent(ListFilterBar).exists()).toBe(true)
  })
})
