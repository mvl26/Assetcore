// TC-UX3-09 (AC-UX-041/045/046) — /vendor-profiles: 4 trạng thái danh sách + «Thử lại».
//
// Bug gốc đo trên đĩa 2026-07-31:
//   • có `catch` nhưng banner `.alert-error` KHÔNG có nút thử lại, và `items` vẫn [] ⇒
//     banner lỗi VÀ «Chưa có nhà cung cấp nào.» hiện CÙNG LÚC (double-state).
//   • trạng thái tải chỉ là chữ «Đang tải...» trần, không phải khung xương.
//   • nhánh «Không có dữ liệu» (:116-118) là MÃ CHẾT — nằm trong `v-else-if="items.length"`.
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises, enableAutoUnmount } from '@vue/test-utils'

enableAutoUnmount(afterEach)

const listVendorProfilesSpy = vi.fn()
vi.mock('@/api/imm03', () => ({
  listVendorProfiles: (...a: unknown[]) => listVendorProfilesSpy(...a),
}))

import VendorProfileListView from '@/views/procurement/VendorProfileListView.vue'

const ITEMS = [
  { name: 'SUP-2026-0001', supplier_name: 'Công ty Thiết bị Y tế A', imm_avl_status: 'Approved',
    imm_avl_categories: 'Chẩn đoán hình ảnh', imm_overall_score: 4.2, cert_count: 3, cert_expiring_soon: 1 },
  { name: 'SUP-2026-0002', supplier_name: 'Công ty Thiết bị Y tế B', imm_avl_status: 'Conditional',
    imm_avl_categories: 'Xét nghiệm', imm_overall_score: 3.1, cert_count: 1, cert_expiring_soon: 0 },
]

const stubs = { PageHeader: true, RouterLink: true }
const mocks = { $router: { push: vi.fn() } }

async function mountView() {
  const w = mount(VendorProfileListView, { global: { stubs, mocks } })
  await flushPromises()
  return w
}

function state(w: ReturnType<typeof mount>) {
  return w.find('[data-testid="list-page-shell"]').attributes('data-state')
}
function retryControls(w: ReturnType<typeof mount>) {
  return w.findAll('button').filter((b) => (b.attributes('aria-label') ?? b.text()).trim() === 'Thử lại')
}

describe('/vendor-profiles — 4 trạng thái loại trừ + thử lại (TC-UX3-09)', () => {
  beforeEach(() => {
    listVendorProfilesSpy.mockReset()
      .mockResolvedValue({ items: ITEMS, total: ITEMS.length, page: 1, page_size: 100 })
  })

  it('(a) đang tải ⇒ KHUNG XƯƠNG, không còn chữ «Đang tải...» trần', async () => {
    listVendorProfilesSpy.mockReturnValue(new Promise(() => {}))
    const w = await mountView()
    expect(state(w)).toBe('loading')
    expect(w.find('[data-testid="list-skeleton"]').exists()).toBe(true)
    expect(w.text()).not.toContain('Đang tải...')
    expect(w.findAll('table')).toHaveLength(0)
  })

  it('(b) lỗi ⇒ ui-error + «Thử lại», 0 chuỗi rỗng cũ, 0 banner alert-error song song', async () => {
    listVendorProfilesSpy.mockRejectedValue(new Error('Máy chủ trả về 500.'))
    const w = await mountView()
    expect(state(w)).toBe('error')
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(true)
    expect(w.find('[data-testid="ui-empty"]').exists()).toBe(false)
    expect(w.html()).not.toContain('Chưa có nhà cung cấp nào')
    expect(w.html()).not.toContain('Không có dữ liệu')
    expect(w.find('.alert-error').exists()).toBe(false)   // 1 bề mặt lỗi duy nhất
    expect(retryControls(w)).toHaveLength(1)
  })

  it('(c) rỗng ⇒ ui-empty có câu hướng dẫn (không còn câu cụt «Không có dữ liệu»)', async () => {
    listVendorProfilesSpy.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 100 })
    const w = await mountView()
    expect(state(w)).toBe('empty')
    const empty = w.find('[data-testid="ui-empty"]')
    expect(empty.exists()).toBe(true)
    expect(empty.text()).toContain('Chưa có nhà cung cấp nào')
    expect(empty.text()).toMatch(/Hãy|Bấm|Nhấn|Xoá bộ lọc|Xóa bộ lọc/)
    expect(w.html()).not.toContain('Không có dữ liệu')
  })

  it('(d) có dữ liệu ⇒ đúng N dòng, 0 ui-empty, 0 ui-error', async () => {
    const w = await mountView()
    expect(state(w)).toBe('content')
    expect(w.findAll('tbody tr')).toHaveLength(ITEMS.length)
    expect(w.find('[data-testid="ui-empty"]').exists()).toBe(false)
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(false)
  })

  it('(e) bấm «Thử lại» ⇒ hàm nạp được gọi lần 2; lượt 2 OK ⇒ về trạng thái có dữ liệu', async () => {
    listVendorProfilesSpy.mockRejectedValueOnce(new Error('Mất kết nối.'))
    const w = await mountView()
    expect(listVendorProfilesSpy).toHaveBeenCalledTimes(1)
    await retryControls(w)[0].trigger('click')
    await flushPromises()
    expect(listVendorProfilesSpy).toHaveBeenCalledTimes(2)
    expect(state(w)).toBe('content')
  })

  it('(f) bộ lọc KHÔNG biến mất khi lỗi — ô lọc trạng thái duyệt còn trong DOM', async () => {
    listVendorProfilesSpy.mockRejectedValue(new Error('Bộ lọc không hợp lệ.'))
    const w = await mountView()
    const filters = w.find('[data-testid="list-filters"]')
    expect(filters.exists()).toBe(true)
    expect(filters.findAll('select').length).toBeGreaterThan(0)
    expect(filters.find('input[type="checkbox"]').exists()).toBe(true)
  })
})
