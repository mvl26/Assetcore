// TC-UX3-26 (AC-UX-047 · lô 2) — /capas: 4 trạng thái danh sách + «Thử lại».
//
// Bug gốc đo trên đĩa 2026-08-04: banner `.alert-error` (`:180`) hiện SONG SONG với khối
// rỗng «Không có hành động khắc phục/phòng ngừa nào» (`:192`) — API hỏng ⇒ người dùng
// đọc câu rỗng và tin là KHÔNG có hồ sơ nào, không có đường nạp lại. Thêm mã chết:
// khối «Không có dữ liệu» (`:223`) nằm TRONG nhánh CÓ dữ liệu.
//
// Đây là biến thể C: `useCapaStore` có ô `error` RIÊNG cho danh sách và tự dọn đầu lượt
// (`stores/imm00.ts:111`, `:116`) ⇒ view bind THẲNG `store.error`, không cần chụp.
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises, enableAutoUnmount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { resetRouteMock } from '@/test/vueRouterMock'

enableAutoUnmount(afterEach)

const listCapasSpy = vi.fn()
// `importOriginal` + ghi đè ĐÚNG hàm nạp: `stores/imm00.ts` dùng `import * as api` nên
// module phải giữ đủ mọi export; liệt kê tay sẽ trôi lệch khi lớp API thêm hàm mới.
vi.mock('@/api/imm00', async (importOriginal) => ({
  ...(await importOriginal<Record<string, unknown>>()),
  listCapas: (...a: unknown[]) => listCapasSpy(...a),
}))
vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())

import CAPAListView from '@/views/incident/CAPAListView.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'

const ROWS = [
  { name: 'CAPA-2026-0001', asset: 'AC-ASSET-2026-00001', asset_name: 'Máy thở Hamilton C1',
    severity: 'High', status: 'Open', due_date: '2026-09-01' },
  { name: 'CAPA-2026-0002', asset: 'AC-ASSET-2026-00002', asset_name: 'Máy siêu âm GE Logiq',
    severity: 'Medium', status: 'In Progress', due_date: '2026-10-01' },
]
const ok = (rows: unknown[]) => ({ items: rows, pagination: { total: rows.length, page: 1, page_size: 20, total_pages: 1 } })

const stubs = { PageHeader: true, FilterToggleButton: true }

async function mountView() {
  const w = mount(CAPAListView, { global: { stubs } })
  await flushPromises()
  return w
}
function state(w: ReturnType<typeof mount>) {
  return w.find('[data-testid="list-page-shell"]').attributes('data-state')
}
function retryControls(w: ReturnType<typeof mount>) {
  return w.findAll('button').filter((b) => (b.attributes('aria-label') ?? b.text()).trim() === 'Thử lại')
}

describe('/capas — 4 trạng thái loại trừ + thử lại (TC-UX3-26)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    resetRouteMock()
    listCapasSpy.mockReset().mockResolvedValue(ok(ROWS))
  })

  it('(a) đang tải ⇒ khung xương, 0 nội dung, 0 nút «Thử lại»', async () => {
    listCapasSpy.mockReturnValue(new Promise(() => {}))
    const w = await mountView()
    expect(state(w)).toBe('loading')
    expect(w.find('[data-testid="list-skeleton"]').exists()).toBe(true)
    expect(w.findAll('[data-testid="list-content"]')).toHaveLength(0)
    expect(w.findAll('table')).toHaveLength(0)
    expect(retryControls(w)).toHaveLength(0)
  })

  it('(b) lỗi ⇒ ui-error + ĐÚNG 1 «Thử lại», KHÔNG còn banner alert-error song song', async () => {
    listCapasSpy.mockRejectedValue(new Error('Máy chủ trả về 500.'))
    const w = await mountView()
    expect(state(w)).toBe('error')
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(true)
    expect(w.findAll('.alert-error')).toHaveLength(0)
    expect(w.findAll('[data-testid="list-content"]')).toHaveLength(0)
    expect(w.find('[data-testid="ui-empty"]').exists()).toBe(false)
    expect(w.text()).not.toContain('Không có hành động khắc phục/phòng ngừa nào')
    expect(w.text()).not.toContain('Không có dữ liệu')
    expect(w.text()).toContain('Máy chủ trả về 500.')
    expect(retryControls(w)).toHaveLength(1)
  })

  it('(c) rỗng thật ⇒ ui-empty có câu hướng dẫn tiếng Việt, 0 nút «Thử lại»', async () => {
    listCapasSpy.mockResolvedValue(ok([]))
    const w = await mountView()
    expect(state(w)).toBe('empty')
    expect(w.find('[data-testid="ui-empty-title"]').text()).toBe('Chưa có hành động khắc phục/phòng ngừa nào')
    expect(w.find('[data-testid="ui-empty-description"]').text()).toBe(
      'Hành động khắc phục/phòng ngừa được mở từ sự cố, phát hiện không phù hợp hoặc kết quả hiệu chuẩn không đạt.',
    )
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
    listCapasSpy.mockRejectedValueOnce(new Error('Mất kết nối.'))
    const w = await mountView()
    expect(state(w)).toBe('error')
    expect(listCapasSpy).toHaveBeenCalledTimes(1)
    await retryControls(w)[0].trigger('click')
    await flushPromises()
    expect(listCapasSpy).toHaveBeenCalledTimes(2)
    expect(state(w)).toBe('content')
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(false)
  })

  it('(f) loại trừ cấu trúc: đúng 1 shell, đúng 1 trạng thái; bộ lọc còn sống', async () => {
    listCapasSpy.mockRejectedValue(new Error('X'))
    const w = await mountView()
    expect(w.findAll('[data-testid="list-page-shell"]')).toHaveLength(1)
    const present = ['list-loading', 'ui-error', 'ui-empty', 'list-content']
      .filter((t) => w.find(`[data-testid="${t}"]`).exists())
    expect(present).toEqual(['ui-error'])
    expect(w.find('[data-testid="list-filters"]').exists()).toBe(true)
    expect(w.findComponent(ListFilterBar).exists()).toBe(true)
  })

  it('(g) «Thử lại» GIỮ bộ lọc hiện tại, không nạp lại toàn bộ danh sách', async () => {
    // `buildParams()` mang `status`/`asset` từ URL; nút nạp lại phải gửi ĐÚNG bộ tham số
    // đó, nếu không người dùng bấm «Thử lại» lại thấy dữ liệu của bộ lọc khác.
    listCapasSpy.mockRejectedValueOnce(new Error('Mất kết nối.'))
    const w = await mountView()
    const firstParams = listCapasSpy.mock.calls[0][0]
    await retryControls(w)[0].trigger('click')
    await flushPromises()
    expect(listCapasSpy.mock.calls[1][0]).toEqual(firstParams)
  })
})
