// TC-UX3-17 (AC-UX-047 · lô 1) — /documents/requests: 4 trạng thái danh sách + «Thử lại».
//
// Bug gốc đo trên đĩa 2026-08-03: `load()` (`DocumentRequestListView.vue:90`) có
// `try … finally` nhưng **0 `catch`** ⇒ API hỏng ⇒ in «Chưa có yêu cầu hồ sơ.». Biến `err`
// sẵn có KHÔNG dùng lại được: nó thuộc HỘP THOẠI lưu biểu mẫu (`:141`) — nối vào danh sách
// thì một lần lưu hỏng sẽ xoá trắng cả bảng (INV-UX3-13).
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises, enableAutoUnmount } from '@vue/test-utils'
import { resetRouteMock } from '@/test/vueRouterMock'

enableAutoUnmount(afterEach)

const listDocumentRequestsSpy = vi.fn()
vi.mock('@/api/imm00', () => ({
  listDocumentRequests: (...a: unknown[]) => listDocumentRequestsSpy(...a),
  getDocumentRequest: vi.fn(),
  createDocumentRequest: vi.fn(),
  updateDocumentRequest: vi.fn(),
  deleteDocumentRequest: vi.fn(),
}))
vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())

import DocumentRequestListView from '@/views/document/DocumentRequestListView.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'

const ROWS = [
  { name: 'DR-2026-0001', asset_ref: 'AC-ASSET-1', asset_name: 'Máy thở A', doc_type_required: 'Giấy phép nhập khẩu',
    doc_category: 'Legal', priority: 'High', status: 'Open', due_date: '2026-08-10' },
  { name: 'DR-2026-0002', asset_ref: 'AC-ASSET-2', asset_name: 'Monitor B', doc_type_required: 'Chứng nhận hiệu chuẩn',
    doc_category: 'Certification', priority: 'Medium', status: 'Fulfilled', due_date: '2026-08-20' },
]

const stubs = { PageHeader: true, FilterToggleButton: true, SmartSelect: true, ApproverSelect: true, DateInput: true }

async function mountView() {
  const w = mount(DocumentRequestListView, { global: { stubs } })
  await flushPromises()
  return w
}

function state(w: ReturnType<typeof mount>) {
  return w.find('[data-testid="list-page-shell"]').attributes('data-state')
}
function retryControls(w: ReturnType<typeof mount>) {
  return w.findAll('button').filter((b) => (b.attributes('aria-label') ?? b.text()).trim() === 'Thử lại')
}

describe('/documents/requests — 4 trạng thái loại trừ + thử lại (TC-UX3-17)', () => {
  beforeEach(() => {
    resetRouteMock()
    listDocumentRequestsSpy.mockReset().mockResolvedValue({ items: ROWS, total: ROWS.length })
  })

  it('(a) đang tải ⇒ khung xương, 0 nội dung, 0 nút «Thử lại»', async () => {
    listDocumentRequestsSpy.mockReturnValue(new Promise(() => {}))
    const w = await mountView()
    expect(state(w)).toBe('loading')
    expect(w.find('[data-testid="list-skeleton"]').exists()).toBe(true)
    expect(w.findAll('[data-testid="list-content"]')).toHaveLength(0)
    expect(retryControls(w)).toHaveLength(0)
  })

  it('(b) lỗi ⇒ ui-error + đúng 1 «Thử lại», KHÔNG còn chuỗi rỗng cũ', async () => {
    listDocumentRequestsSpy.mockRejectedValue(new Error('Máy chủ trả về 500.'))
    const w = await mountView()
    expect(state(w)).toBe('error')
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(true)
    expect(w.findAll('[data-testid="list-content"]')).toHaveLength(0)
    expect(w.text()).not.toContain('Chưa có')
    expect(retryControls(w)).toHaveLength(1)
  })

  it('(c) rỗng thật ⇒ ui-empty có câu hướng dẫn tiếng Việt, 0 nút «Thử lại»', async () => {
    listDocumentRequestsSpy.mockResolvedValue({ items: [], total: 0 })
    const w = await mountView()
    expect(state(w)).toBe('empty')
    expect(w.find('[data-testid="ui-empty-title"]').text()).toBe('Chưa có yêu cầu hồ sơ nào')
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
    listDocumentRequestsSpy.mockRejectedValueOnce(new Error('Mất kết nối.'))
    const w = await mountView()
    expect(listDocumentRequestsSpy).toHaveBeenCalledTimes(1)
    await retryControls(w)[0].trigger('click')
    await flushPromises()
    expect(listDocumentRequestsSpy).toHaveBeenCalledTimes(2)
    expect(state(w)).toBe('content')
  })

  it('(f) loại trừ cấu trúc: đúng 1 shell, đúng 1 trạng thái; bộ lọc còn sống', async () => {
    listDocumentRequestsSpy.mockRejectedValue(new Error('X'))
    const w = await mountView()
    expect(w.findAll('[data-testid="list-page-shell"]')).toHaveLength(1)
    const present = ['list-loading', 'ui-error', 'ui-empty', 'list-content']
      .filter((t) => w.find(`[data-testid="${t}"]`).exists())
    expect(present).toEqual(['ui-error'])
    expect(w.findComponent(ListFilterBar).exists()).toBe(true)
  })
})
