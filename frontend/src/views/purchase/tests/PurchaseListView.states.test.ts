// TC-UX3-07 (AC-UX-041/043) — /purchases: 4 trạng thái danh sách + «Thử lại».
//
// Bug gốc đo trên đĩa 2026-07-31: `load()` có `try … finally` nhưng **0 `catch`**
// ⇒ API 500 để `rows` = [] ⇒ view rơi vào nhánh `v-else-if="!rows.length"` và in
// «Chưa có đơn hàng nào». Người dùng tin là KHÔNG có đơn hàng nào trong hệ thống,
// và không có đường thử lại. Đây là *lỗi giả dạng rỗng* (false-empty) kinh điển.
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises, enableAutoUnmount } from '@vue/test-utils'
import { resetRouteMock } from '@/test/vueRouterMock'

enableAutoUnmount(afterEach)

const listPurchasesSpy = vi.fn()
vi.mock('@/api/purchase', () => ({
  listPurchases: (...a: unknown[]) => listPurchasesSpy(...a),
}))
vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({ can: () => true }),
}))
// Factory dùng CHUNG (chống pollution xuyên-file — xem src/test/vueRouterMock.ts).
vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())

import PurchaseListView from '@/views/purchase/PurchaseListView.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'

const ROWS = [
  { name: 'PO-2026-0001', supplier: 'SUP-1', supplier_name: 'Công ty A', status: 'Draft',
    purchase_date: '2026-07-01', total_value: 1_000_000, device_count: 1, part_count: 0 },
  { name: 'PO-2026-0002', supplier: 'SUP-2', supplier_name: 'Công ty B', status: 'Submitted',
    purchase_date: '2026-07-02', total_value: 2_000_000, device_count: 0, part_count: 2 },
  { name: 'PO-2026-0003', supplier: 'SUP-3', supplier_name: 'Công ty C', status: 'Received',
    purchase_date: '2026-07-03', total_value: 3_000_000, device_count: 0, part_count: 0 },
]

const stubs = { PageHeader: true, FilterToggleButton: true, SmartSelect: true }

async function mountView() {
  const w = mount(PurchaseListView, { global: { stubs } })
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

describe('/purchases — 4 trạng thái loại trừ + thử lại (TC-UX3-07)', () => {
  beforeEach(() => {
    resetRouteMock()
    listPurchasesSpy.mockReset().mockResolvedValue({ data: ROWS, total: ROWS.length })
  })

  it('(a) đang tải ⇒ khung xương, 0 <table> dữ liệu', async () => {
    listPurchasesSpy.mockReturnValue(new Promise(() => {}))
    const w = await mountView()
    expect(state(w)).toBe('loading')
    expect(w.find('[data-testid="list-skeleton"]').exists()).toBe(true)
    expect(w.findAll('table')).toHaveLength(0)
  })

  it('(b) lỗi ⇒ ui-error + «Thử lại», KHÔNG có chuỗi «Chưa có đơn hàng nào»', async () => {
    listPurchasesSpy.mockRejectedValue(new Error('Máy chủ trả về 500.'))
    const w = await mountView()
    expect(state(w)).toBe('error')
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(true)
    expect(w.find('[data-testid="ui-empty"]').exists()).toBe(false)
    expect(w.html()).not.toContain('Chưa có đơn hàng nào')
    expect(w.text()).toContain('Máy chủ trả về 500.')
    expect(retryControls(w)).toHaveLength(1)
  })

  it('(c) rỗng ⇒ ui-empty có câu hướng dẫn', async () => {
    listPurchasesSpy.mockResolvedValue({ data: [], total: 0 })
    const w = await mountView()
    expect(state(w)).toBe('empty')
    const empty = w.find('[data-testid="ui-empty"]')
    expect(empty.exists()).toBe(true)
    expect(empty.text()).toContain('Chưa có đơn hàng nào')
    expect(empty.text()).toMatch(/Hãy|Bấm|Nhấn|Tạo |Xoá bộ lọc|Xóa bộ lọc/)
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(false)
  })

  it('(d) có dữ liệu ⇒ đúng N dòng, 0 ui-empty, 0 ui-error', async () => {
    const w = await mountView()
    expect(state(w)).toBe('content')
    expect(w.findAll('tbody tr')).toHaveLength(ROWS.length)
    expect(w.find('[data-testid="ui-empty"]').exists()).toBe(false)
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(false)
  })

  it('(e) bấm «Thử lại» ⇒ hàm nạp được gọi lần 2; lượt 2 OK ⇒ về trạng thái có dữ liệu', async () => {
    listPurchasesSpy.mockRejectedValueOnce(new Error('Mất kết nối.'))
    const w = await mountView()
    expect(listPurchasesSpy).toHaveBeenCalledTimes(1)
    await retryControls(w)[0].trigger('click')
    await flushPromises()
    expect(listPurchasesSpy).toHaveBeenCalledTimes(2)
    expect(state(w)).toBe('content')
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(false)
  })

  it('(f) bộ lọc KHÔNG biến mất khi lỗi — người dùng phải sửa được bộ lọc gây lỗi', async () => {
    listPurchasesSpy.mockRejectedValue(new Error('Bộ lọc không hợp lệ.'))
    const w = await mountView()
    expect(w.find('[data-testid="list-filters"]').exists()).toBe(true)
    expect(w.findComponent(ListFilterBar).exists()).toBe(true)
  })
})
