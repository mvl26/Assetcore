// TC-UX3-16 (AC-UX-047 · lô 1) — /spare-parts: 4 trạng thái danh sách + «Thử lại».
//
// Bug gốc đo trên đĩa 2026-08-03: `load()` (`SparePartListView.vue:80`) có `try … finally`
// nhưng **0 `catch`** ⇒ API hỏng ⇒ in «Chưa có phụ tùng phù hợp.» ⇒ người dùng tin là
// KHO RỖNG (nguy hiểm: quyết định mua sắm dựa trên số 0 giả). Đây là *lỗi giả dạng rỗng*.
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises, enableAutoUnmount } from '@vue/test-utils'
import { resetRouteMock } from '@/test/vueRouterMock'

enableAutoUnmount(afterEach)

const listSparePartsSpy = vi.fn()
vi.mock('@/api/inventory', () => ({
  listSpareParts: (...a: unknown[]) => listSparePartsSpy(...a),
  createSparePart: vi.fn(),
}))
vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())

import SparePartListView from '@/views/inventory/SparePartListView.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'

const ROWS = [
  { name: 'SP-0001', part_code: 'SP-0001', part_name: 'Bộ lọc HEPA', part_category: 'Filter',
    unit_cost: 500_000, stock_uom: 'Cái', total_stock: 10, min_stock_level: 2, is_low_stock: 0, is_critical: 0 },
  { name: 'SP-0002', part_code: 'SP-0002', part_name: 'Ắc-quy dự phòng', part_category: 'Battery',
    unit_cost: 1_200_000, stock_uom: 'Cái', total_stock: 1, min_stock_level: 3, is_low_stock: 1, is_critical: 1 },
]

const stubs = { PageHeader: true, FilterToggleButton: true, SmartSelect: true, CurrencyInput: true }

async function mountView() {
  const w = mount(SparePartListView, { global: { stubs } })
  await flushPromises()
  return w
}

function state(w: ReturnType<typeof mount>) {
  return w.find('[data-testid="list-page-shell"]').attributes('data-state')
}
function retryControls(w: ReturnType<typeof mount>) {
  return w.findAll('button').filter((b) => (b.attributes('aria-label') ?? b.text()).trim() === 'Thử lại')
}

describe('/spare-parts — 4 trạng thái loại trừ + thử lại (TC-UX3-16)', () => {
  beforeEach(() => {
    resetRouteMock()
    listSparePartsSpy.mockReset().mockResolvedValue({ items: ROWS, pagination: { total: ROWS.length } })
  })

  it('(a) đang tải ⇒ khung xương, 0 nội dung, 0 nút «Thử lại»', async () => {
    listSparePartsSpy.mockReturnValue(new Promise(() => {}))
    const w = await mountView()
    expect(state(w)).toBe('loading')
    expect(w.find('[data-testid="list-skeleton"]').exists()).toBe(true)
    expect(w.findAll('[data-testid="list-content"]')).toHaveLength(0)
    expect(retryControls(w)).toHaveLength(0)
  })

  it('(b) lỗi ⇒ ui-error + đúng 1 «Thử lại», KHÔNG còn chuỗi rỗng cũ', async () => {
    listSparePartsSpy.mockRejectedValue(new Error('Máy chủ trả về 500.'))
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
    listSparePartsSpy.mockResolvedValue({ items: [], pagination: { total: 0 } })
    const w = await mountView()
    expect(state(w)).toBe('empty')
    expect(w.find('[data-testid="ui-empty-title"]').text()).toBe('Chưa có phụ tùng nào')
    expect(w.find('[data-testid="ui-empty-description"]').exists()).toBe(true)
    expect(retryControls(w)).toHaveLength(0)
  })

  it('(d) có dữ liệu ⇒ đúng N dòng trong list-data', async () => {
    const w = await mountView()
    expect(state(w)).toBe('content')
    expect(w.find('[data-testid="list-data"]').exists()).toBe(true)
    expect(w.findAll('tbody tr')).toHaveLength(ROWS.length)
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(false)
  })

  it('(e) «Thử lại» gọi lại đúng hàm nạp 1 lần ⇒ error → content', async () => {
    listSparePartsSpy.mockRejectedValueOnce(new Error('Mất kết nối.'))
    const w = await mountView()
    expect(listSparePartsSpy).toHaveBeenCalledTimes(1)
    await retryControls(w)[0].trigger('click')
    await flushPromises()
    expect(listSparePartsSpy).toHaveBeenCalledTimes(2)
    expect(state(w)).toBe('content')
  })

  it('(f) loại trừ cấu trúc: đúng 1 shell, đúng 1 trạng thái; bộ lọc còn sống', async () => {
    listSparePartsSpy.mockRejectedValue(new Error('X'))
    const w = await mountView()
    expect(w.findAll('[data-testid="list-page-shell"]')).toHaveLength(1)
    const present = ['list-loading', 'ui-error', 'ui-empty', 'list-content']
      .filter((t) => w.find(`[data-testid="${t}"]`).exists())
    expect(present).toEqual(['ui-error'])
    expect(w.findComponent(ListFilterBar).exists()).toBe(true)
  })
})
