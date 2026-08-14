// TC-UX3-30 (AC-UX-047 · lô 2) — /compliance/mr: 4 trạng thái danh sách + «Thử lại».
//
// Bug gốc đo trên đĩa 2026-08-04: `load()` không có ĐƯỜNG BÁO LỖI nào — `stores/imm16.ts`
// nuốt lỗi vào ô `error` dùng CHUNG cho 5 danh sách và KHÔNG dọn ô đó ở đầu lượt. View
// chỉ có 2 nhánh (`loading` / `!items.length`) ⇒ API hỏng rơi thẳng vào khối rỗng
// «Chưa có cuộc soát xét quản lý phù hợp.» — *lỗi giả dạng rỗng*, không đường thử lại.
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises, enableAutoUnmount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { resetRouteMock } from '@/test/vueRouterMock'

enableAutoUnmount(afterEach)

const listManagementReviewsSpy = vi.fn()
// `importOriginal` + ghi đè ĐÚNG hàm nạp: `stores/imm16.ts` import tĩnh 28 hàm từ module
// này, liệt kê tay sẽ trôi lệch ngay khi lớp API thêm hàm mới ("No export named …").
vi.mock('@/api/imm16', async (importOriginal) => ({
  ...(await importOriginal<Record<string, unknown>>()),
  listManagementReviews: (...a: unknown[]) => listManagementReviewsSpy(...a),
}))
vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())

import ManagementReviewListView from '@/views/compliance/ManagementReviewListView.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'

const ROWS = [
  { name: 'MR-2026-00001', quarter: 'Q1-2026', review_date: '2026-03-31', chair: 'a@x.vn',
    chair_name: 'Nguyễn Văn A', status: 'Draft', scorecard_ref: 'SCR-2026-0001', next_review_date: '2026-06-30' },
  { name: 'MR-2026-00002', quarter: 'Q2-2026', review_date: '2026-06-30', chair: 'b@x.vn',
    chair_name: 'Trần Thị B', status: 'Held', scorecard_ref: '', next_review_date: '2026-09-30' },
]
const ok = (rows: unknown[]) => ({ items: rows, pagination: { total: rows.length, page: 1, page_size: 20, total_pages: 1 } })

const stubs = { PageHeader: true, FilterToggleButton: true, BaseModal: true, DateInput: true, ApproverSelect: true }

async function mountView() {
  const w = mount(ManagementReviewListView, { global: { stubs } })
  await flushPromises()
  return w
}
function state(w: ReturnType<typeof mount>) {
  return w.find('[data-testid="list-page-shell"]').attributes('data-state')
}
function retryControls(w: ReturnType<typeof mount>) {
  return w.findAll('button').filter((b) => (b.attributes('aria-label') ?? b.text()).trim() === 'Thử lại')
}

describe('/compliance/mr — 4 trạng thái loại trừ + thử lại (TC-UX3-30)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    resetRouteMock()
    listManagementReviewsSpy.mockReset().mockResolvedValue(ok(ROWS))
  })

  it('(a) đang tải ⇒ khung xương, 0 nội dung, 0 nút «Thử lại»', async () => {
    listManagementReviewsSpy.mockReturnValue(new Promise(() => {}))
    const w = await mountView()
    expect(state(w)).toBe('loading')
    expect(w.find('[data-testid="list-skeleton"]').exists()).toBe(true)
    expect(w.findAll('[data-testid="list-content"]')).toHaveLength(0)
    expect(w.findAll('table')).toHaveLength(0)
    expect(retryControls(w)).toHaveLength(0)
  })

  it('(b) lỗi ⇒ ui-error + ĐÚNG 1 «Thử lại», KHÔNG còn câu rỗng cũ', async () => {
    listManagementReviewsSpy.mockRejectedValue(new Error('Máy chủ trả về 500.'))
    const w = await mountView()
    expect(state(w)).toBe('error')
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(true)
    expect(w.findAll('.alert-error')).toHaveLength(0)
    expect(w.findAll('[data-testid="list-content"]')).toHaveLength(0)
    expect(w.find('[data-testid="ui-empty"]').exists()).toBe(false)
    expect(w.text()).not.toContain('Chưa có cuộc soát xét quản lý phù hợp')
    expect(w.text()).toContain('Máy chủ trả về 500.')
    expect(retryControls(w)).toHaveLength(1)
  })

  it('(c) rỗng thật ⇒ ui-empty có câu hướng dẫn tiếng Việt, 0 nút «Thử lại»', async () => {
    listManagementReviewsSpy.mockResolvedValue(ok([]))
    const w = await mountView()
    expect(state(w)).toBe('empty')
    expect(w.find('[data-testid="ui-empty-title"]').text()).toBe('Chưa có cuộc soát xét quản lý nào')
    expect(w.find('[data-testid="ui-empty-description"]').text())
      .toBe('Hãy tạo cuộc soát xét mới hoặc xoá bộ lọc để xem tất cả.')
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
    listManagementReviewsSpy.mockRejectedValueOnce(new Error('Mất kết nối.'))
    const w = await mountView()
    expect(state(w)).toBe('error')
    expect(listManagementReviewsSpy).toHaveBeenCalledTimes(1)
    await retryControls(w)[0].trigger('click')
    await flushPromises()
    expect(listManagementReviewsSpy).toHaveBeenCalledTimes(2)
    expect(state(w)).toBe('content')
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(false)
  })

  it('(f) loại trừ cấu trúc: đúng 1 shell, đúng 1 trạng thái; bộ lọc còn sống', async () => {
    listManagementReviewsSpy.mockRejectedValue(new Error('X'))
    const w = await mountView()
    expect(w.findAll('[data-testid="list-page-shell"]')).toHaveLength(1)
    const present = ['list-loading', 'ui-error', 'ui-empty', 'list-content']
      .filter((t) => w.find(`[data-testid="${t}"]`).exists())
    expect(present).toEqual(['ui-error'])
    expect(w.find('[data-testid="list-filters"]').exists()).toBe(true)
    expect(w.findComponent(ListFilterBar).exists()).toBe(true)
  })

  it('(g) lỗi KHÔNG dính giữa 2 lượt nạp: ô `error` dùng chung được dọn đầu lượt', async () => {
    // stores/imm16.ts dùng CHUNG 1 ref `error` cho rules/findings/audits/mr và không tự
    // dọn ⇒ nếu view không clear đầu lượt, lỗi màn trước rò sang màn sau (INV-UX3-4).
    listManagementReviewsSpy.mockRejectedValueOnce(new Error('Lỗi lượt trước.'))
    const w = await mountView()
    expect(state(w)).toBe('error')
    listManagementReviewsSpy.mockResolvedValue(ok(ROWS))
    await retryControls(w)[0].trigger('click')
    await flushPromises()
    expect(state(w)).toBe('content')
    expect(w.text()).not.toContain('Lỗi lượt trước.')
  })
})
