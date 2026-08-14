// TC-UX3-33 (AC-UX-047 · lô 2) — /approved-vendors: 4 trạng thái danh sách + «Thử lại».
//
// Bug gốc đo trên đĩa 2026-08-04: banner `.alert-error` (`:250`) hiện SONG SONG với khối
// rỗng «Không có giấy phép nào phù hợp» (`:350`), và banner bind thẳng `store.error` —
// ô dùng CHUNG cho `fetchAvl`, `fetchKpis` VÀ 4 transition (phê duyệt / cấp có điều kiện
// / phục hồi / đình chỉ) ⇒ một lần đình chỉ hỏng cũng xoá trắng danh sách. Thêm mã chết:
// «Không có dữ liệu» (`:291`) nằm TRONG nhánh CÓ dữ liệu.
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises, enableAutoUnmount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { resetRouteMock } from '@/test/vueRouterMock'

enableAutoUnmount(afterEach)

const listAvlSpy = vi.fn()
const getDashboardKpisSpy = vi.fn()
// `importOriginal` + ghi đè ĐÚNG hàm nạp: `stores/imm03.ts` dùng `import * as api` nên
// module phải giữ đủ mọi export; liệt kê tay sẽ trôi lệch khi lớp API thêm hàm mới.
vi.mock('@/api/imm03', async (importOriginal) => ({
  ...(await importOriginal<Record<string, unknown>>()),
  listAvl: (...a: unknown[]) => listAvlSpy(...a),
  getDashboardKpis: (...a: unknown[]) => getDashboardKpisSpy(...a),
}))
vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({ can: () => true }),
}))
vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())

import AvlListView from '@/views/procurement/AvlListView.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'

const ROWS = [
  { name: 'AVL-2026-0001', supplier: 'SUP-2026-00001', vendor_name: 'Công ty A',
    device_category: 'DC-01', device_category_name: 'Chẩn đoán hình ảnh',
    valid_from: '2026-01-01', valid_to: '2027-01-01', workflow_state: 'Approved' },
  { name: 'AVL-2026-0002', supplier: 'SUP-2026-00002', vendor_name: 'Công ty B',
    device_category: 'DC-02', device_category_name: 'Hồi sức cấp cứu',
    valid_from: '2026-02-01', valid_to: '2027-02-01', workflow_state: 'Conditional' },
]
const ok = (rows: unknown[]) => ({ items: rows, total: rows.length, page: 1, page_size: 20 })
const KPIS = { avl_active: 2, avl_expiring_30d: 0 }

const stubs = { PageHeader: true, FilterToggleButton: true, KpiCard: true, BaseModal: true, DateInput: true }

async function mountView() {
  const w = mount(AvlListView, { global: { stubs } })
  await flushPromises()
  return w
}
function state(w: ReturnType<typeof mount>) {
  return w.find('[data-testid="list-page-shell"]').attributes('data-state')
}
function retryControls(w: ReturnType<typeof mount>) {
  return w.findAll('button').filter((b) => (b.attributes('aria-label') ?? b.text()).trim() === 'Thử lại')
}

describe('/approved-vendors — 4 trạng thái loại trừ + thử lại (TC-UX3-33)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    resetRouteMock()
    listAvlSpy.mockReset().mockResolvedValue(ok(ROWS))
    getDashboardKpisSpy.mockReset().mockResolvedValue(KPIS)
  })

  it('(a) đang tải ⇒ khung xương, 0 nội dung, 0 nút «Thử lại»', async () => {
    listAvlSpy.mockReturnValue(new Promise(() => {}))
    const w = await mountView()
    expect(state(w)).toBe('loading')
    expect(w.find('[data-testid="list-skeleton"]').exists()).toBe(true)
    expect(w.findAll('[data-testid="list-content"]')).toHaveLength(0)
    expect(w.findAll('table')).toHaveLength(0)
    expect(retryControls(w)).toHaveLength(0)
  })

  it('(b) lỗi ⇒ ui-error + ĐÚNG 1 «Thử lại», KHÔNG còn banner alert-error song song', async () => {
    listAvlSpy.mockRejectedValue(new Error('Máy chủ trả về 500.'))
    const w = await mountView()
    expect(state(w)).toBe('error')
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(true)
    expect(w.findAll('.alert-error')).toHaveLength(0)
    expect(w.findAll('[data-testid="list-content"]')).toHaveLength(0)
    expect(w.find('[data-testid="ui-empty"]').exists()).toBe(false)
    expect(w.text()).not.toContain('Không có giấy phép nào phù hợp')
    expect(w.text()).not.toContain('Không có dữ liệu')
    expect(w.text()).toContain('Máy chủ trả về 500.')
    expect(retryControls(w)).toHaveLength(1)
  })

  it('(c) rỗng thật ⇒ ui-empty có câu hướng dẫn tiếng Việt, 0 nút «Thử lại»', async () => {
    // Màn này mở kèm bộ lọc mặc định `workflow_state: 'Approved'` ⇒ lúc mount ĐANG CÓ
    // lọc, nên câu rỗng đúng là biến thể «có lọc». Bỏ lọc mới ra biến thể «chưa có gì».
    listAvlSpy.mockResolvedValue(ok([]))
    const w = await mountView()
    expect(state(w)).toBe('empty')
    expect(w.find('[data-testid="ui-empty-title"]').text()).toBe('Không có giấy phép nào phù hợp')
    expect(w.find('[data-testid="ui-empty-description"]').text())
      .toBe('Hãy thêm nhà cung cấp vào danh sách được duyệt hoặc xoá bộ lọc để xem tất cả.')
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(false)
    expect(retryControls(w)).toHaveLength(0)

    // bỏ hết bộ lọc ⇒ đổi sang câu «chưa có gì», chứng minh computed phân biệt 2 nhánh
    w.findComponent(ListFilterBar).vm.$emit('reset')
    await flushPromises()
    expect(state(w)).toBe('empty')
    expect(w.find('[data-testid="ui-empty-title"]').text()).toBe('Chưa có giấy phép nhà cung cấp nào')
  })

  it('(d) có dữ liệu ⇒ đúng N dòng trong list-data', async () => {
    const w = await mountView()
    expect(state(w)).toBe('content')
    expect(w.find('[data-testid="list-data"]').exists()).toBe(true)
    expect(w.findAll('tbody tr')).toHaveLength(ROWS.length)
    expect(w.find('[data-testid="ui-empty"]').exists()).toBe(false)
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(false)
  })

  it('(e) «Thử lại» gọi lại đúng hàm nạp 1 lần, GIỮ bộ lọc mặc định `Approved`', async () => {
    listAvlSpy.mockRejectedValueOnce(new Error('Mất kết nối.'))
    const w = await mountView()
    expect(state(w)).toBe('error')
    expect(listAvlSpy).toHaveBeenCalledTimes(1)
    const kpiCallsBefore = getDashboardKpisSpy.mock.calls.length
    await retryControls(w)[0].trigger('click')
    await flushPromises()
    expect(listAvlSpy).toHaveBeenCalledTimes(2)
    // bộ lọc mặc định `workflow_state: 'Approved'` phải được giữ nguyên khi nạp lại
    expect(listAvlSpy.mock.calls[1][0]).toMatchObject({ workflow_state: 'Approved' })
    expect(getDashboardKpisSpy).toHaveBeenCalledTimes(kpiCallsBefore) // INV-UX3-21
    expect(state(w)).toBe('content')
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(false)
  })

  it('(f) loại trừ cấu trúc: đúng 1 shell, đúng 1 trạng thái; bộ lọc còn sống', async () => {
    listAvlSpy.mockRejectedValue(new Error('X'))
    const w = await mountView()
    expect(w.findAll('[data-testid="list-page-shell"]')).toHaveLength(1)
    const present = ['list-loading', 'ui-error', 'ui-empty', 'list-content']
      .filter((t) => w.find(`[data-testid="${t}"]`).exists())
    expect(present).toEqual(['ui-error'])
    expect(w.find('[data-testid="list-filters"]').exists()).toBe(true)
    expect(w.findComponent(ListFilterBar).exists()).toBe(true)
  })

  it('(f2) lỗi nạp CHỈ-SỐ không cướp trạng thái danh sách (INV-UX3-20)', async () => {
    // `fetchKpis` dùng CHUNG ô `store.error` với `fetchAvl` (stores/imm03.ts:110).
    getDashboardKpisSpy.mockRejectedValue(new Error('Chỉ số hỏng.'))
    const w = await mountView()
    expect(state(w)).toBe('content')
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(false)
    expect(w.findAll('tbody tr')).toHaveLength(ROWS.length)
  })
})
