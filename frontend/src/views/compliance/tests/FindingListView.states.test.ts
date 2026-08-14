// TC-UX3-28 (AC-UX-047 · lô 2) — /compliance/findings: 4 trạng thái danh sách + «Thử lại».
//
// Bug gốc đo trên đĩa 2026-08-04: `load()` không có ĐƯỜNG BÁO LỖI nào — `stores/imm16.ts`
// nuốt lỗi vào ô `error` dùng CHUNG cho 5 danh sách và KHÔNG dọn ô đó ở đầu lượt. View
// chỉ có 2 nhánh (`loading` / `!items.length`) ⇒ API hỏng rơi thẳng vào khối rỗng
// «Chưa có phát hiện phù hợp.» — *lỗi giả dạng rỗng*, không đường thử lại.
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises, enableAutoUnmount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { resetRouteMock } from '@/test/vueRouterMock'

enableAutoUnmount(afterEach)

const listFindingsSpy = vi.fn()
const runComplianceEvaluationSpy = vi.fn()
// `importOriginal` + ghi đè ĐÚNG hàm nạp: `stores/imm16.ts` import tĩnh 28 hàm từ module
// này, liệt kê tay sẽ trôi lệch ngay khi lớp API thêm hàm mới ("No export named …").
vi.mock('@/api/imm16', async (importOriginal) => ({
  ...(await importOriginal<Record<string, unknown>>()),
  listFindings: (...a: unknown[]) => listFindingsSpy(...a),
  runComplianceEvaluation: (...a: unknown[]) => runComplianceEvaluationSpy(...a),
}))
vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())

import FindingListView from '@/views/compliance/FindingListView.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'

const ROWS = [
  { name: 'CF-2026-00001', rule: 'CR-CAL-EXPIRED', asset: 'AC-ASSET-2026-00001',
    asset_name: 'Máy thở Hamilton C1', severity: 'High', status: 'Open',
    capa_ref: '', detected_date: '2026-07-01' },
  { name: 'CF-2026-00002', rule: 'CR-PM-OVERDUE', asset: 'AC-ASSET-2026-00002',
    asset_name: 'Máy siêu âm GE Logiq', severity: 'Medium', status: 'Under Review',
    capa_ref: 'CAPA-2026-0007', detected_date: '2026-07-02' },
  { name: 'CF-2026-00003', rule: 'CR-DOC-MISSING', asset: 'AC-ASSET-2026-00003',
    asset_name: 'Máy X-quang Siemens', severity: 'Low', status: 'Closed',
    capa_ref: '', detected_date: '2026-07-03' },
]
const ok = (rows: unknown[]) => ({ items: rows, pagination: { total: rows.length, page: 1, page_size: 20, total_pages: 1 } })

// `PageHeader` phải render slot `#actions` — nút «Chạy đánh giá tuân thủ» nằm trong đó và
// sub-case (f2) cần bấm nó thật. Stub `true` nuốt slot ⇒ nút biến mất khỏi DOM.
const stubs = {
  PageHeader: { template: '<div><slot name="actions" /></div>' },
  FilterToggleButton: true,
}

async function mountView() {
  const w = mount(FindingListView, { global: { stubs } })
  await flushPromises()
  return w
}
function state(w: ReturnType<typeof mount>) {
  return w.find('[data-testid="list-page-shell"]').attributes('data-state')
}
function retryControls(w: ReturnType<typeof mount>) {
  return w.findAll('button').filter((b) => (b.attributes('aria-label') ?? b.text()).trim() === 'Thử lại')
}

describe('/compliance/findings — 4 trạng thái loại trừ + thử lại (TC-UX3-28)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    resetRouteMock()
    listFindingsSpy.mockReset().mockResolvedValue(ok(ROWS))
    runComplianceEvaluationSpy.mockReset().mockResolvedValue({ created: 0 })
  })

  it('(a) đang tải ⇒ khung xương, 0 nội dung, 0 nút «Thử lại»', async () => {
    listFindingsSpy.mockReturnValue(new Promise(() => {}))
    const w = await mountView()
    expect(state(w)).toBe('loading')
    expect(w.find('[data-testid="list-skeleton"]').exists()).toBe(true)
    expect(w.findAll('[data-testid="list-content"]')).toHaveLength(0)
    expect(w.findAll('table')).toHaveLength(0)
    expect(retryControls(w)).toHaveLength(0)
  })

  it('(b) lỗi ⇒ ui-error + ĐÚNG 1 «Thử lại», KHÔNG còn câu rỗng cũ', async () => {
    listFindingsSpy.mockRejectedValue(new Error('Máy chủ trả về 500.'))
    const w = await mountView()
    expect(state(w)).toBe('error')
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(true)
    expect(w.findAll('.alert-error')).toHaveLength(0)
    expect(w.findAll('[data-testid="list-content"]')).toHaveLength(0)
    expect(w.find('[data-testid="ui-empty"]').exists()).toBe(false)
    expect(w.text()).not.toContain('Chưa có phát hiện phù hợp')
    expect(w.text()).toContain('Máy chủ trả về 500.')
    expect(retryControls(w)).toHaveLength(1)
  })

  it('(c) rỗng thật ⇒ ui-empty có câu hướng dẫn tiếng Việt, 0 nút «Thử lại»', async () => {
    listFindingsSpy.mockResolvedValue(ok([]))
    const w = await mountView()
    expect(state(w)).toBe('empty')
    expect(w.find('[data-testid="ui-empty-title"]').text()).toBe('Chưa có phát hiện không phù hợp nào')
    expect(w.find('[data-testid="ui-empty-description"]').text())
      .toBe('Phát hiện được sinh tự động khi chạy đánh giá tuân thủ.')
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
    listFindingsSpy.mockRejectedValueOnce(new Error('Mất kết nối.'))
    const w = await mountView()
    expect(state(w)).toBe('error')
    expect(listFindingsSpy).toHaveBeenCalledTimes(1)
    await retryControls(w)[0].trigger('click')
    await flushPromises()
    expect(listFindingsSpy).toHaveBeenCalledTimes(2)
    // lời gọi PHỤ không được ăn theo nút «Thử lại» (INV-UX3-21)
    expect(runComplianceEvaluationSpy).not.toHaveBeenCalled()
    expect(state(w)).toBe('content')
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(false)
  })

  it('(f) loại trừ cấu trúc: đúng 1 shell, đúng 1 trạng thái; bộ lọc còn sống', async () => {
    listFindingsSpy.mockRejectedValue(new Error('X'))
    const w = await mountView()
    expect(w.findAll('[data-testid="list-page-shell"]')).toHaveLength(1)
    const present = ['list-loading', 'ui-error', 'ui-empty', 'list-content']
      .filter((t) => w.find(`[data-testid="${t}"]`).exists())
    expect(present).toEqual(['ui-error'])
    expect(w.find('[data-testid="list-filters"]').exists()).toBe(true)
    expect(w.findComponent(ListFilterBar).exists()).toBe(true)
  })

  it('(f2) lỗi của HÀNH ĐỘNG GHI không cướp trạng thái danh sách (INV-UX3-20)', async () => {
    // «Chạy đánh giá tuân thủ» là đường GHI, dùng CHUNG ô `store.error`. Nếu view bind
    // thẳng ô đó thì một lần đánh giá hỏng sẽ xoá trắng danh sách đang hiển thị.
    const w = await mountView()
    expect(state(w)).toBe('content')
    runComplianceEvaluationSpy.mockRejectedValue(new Error('Đánh giá hỏng.'))
    const runBtn = w.findAll('button').find((b) => b.text().includes('Chạy đánh giá tuân thủ'))!
    await runBtn.trigger('click')
    await flushPromises()
    expect(state(w)).toBe('content')
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(false)
    expect(w.findAll('tbody tr')).toHaveLength(ROWS.length)
  })
})
