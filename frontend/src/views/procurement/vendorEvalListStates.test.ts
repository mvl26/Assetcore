// TC-UX3-32 (AC-UX-047 · lô 2) — /vendor-evaluations: 4 trạng thái danh sách + «Thử lại».
//
// Bug gốc đo trên đĩa 2026-08-04: banner `.alert-error` (`:139`) hiện SONG SONG với khối
// rỗng «Không có phiếu đánh giá nào phù hợp» (`:226`) — không loại trừ nhau, và banner
// bind thẳng `store.error` là ô dùng CHUNG cho mọi lời gọi imm03 (danh sách + transition).
// Thêm mã chết: khối «Không có dữ liệu» (`:173`) nằm TRONG nhánh CÓ dữ liệu.
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises, enableAutoUnmount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { resetRouteMock } from '@/test/vueRouterMock'

enableAutoUnmount(afterEach)

const listEvaluationsSpy = vi.fn()
const createEvaluationSpy = vi.fn()
const listTechSpecsSpy = vi.fn()
// `importOriginal` + ghi đè ĐÚNG hàm nạp: `stores/imm03.ts` dùng `import * as api` nên
// module phải giữ đủ mọi export; liệt kê tay sẽ trôi lệch khi lớp API thêm hàm mới.
vi.mock('@/api/imm03', async (importOriginal) => ({
  ...(await importOriginal<Record<string, unknown>>()),
  listEvaluations: (...a: unknown[]) => listEvaluationsSpy(...a),
  createEvaluation: (...a: unknown[]) => createEvaluationSpy(...a),
}))
vi.mock('@/api/imm02', async (importOriginal) => ({
  ...(await importOriginal<Record<string, unknown>>()),
  listTechSpecs: (...a: unknown[]) => listTechSpecsSpy(...a),
}))
vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())

import VendorEvalListView from './VendorEvalListView.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'

const ROWS = [
  { name: 'VE-2026-0001', spec_ref: 'TS-2026-0001', workflow_state: 'Draft',
    draft_date: '2026-05-01', recommended_candidate: '', vendor_name: '' },
  { name: 'VE-2026-0002', spec_ref: 'TS-2026-0002', workflow_state: 'Evaluated',
    draft_date: '2026-05-10', recommended_candidate: 'SUP-2026-00001', vendor_name: 'Công ty A' },
]
const ok = (rows: unknown[]) => ({ items: rows, total: rows.length, page: 1, page_size: 20 })

// `PageHeader` phải render slot `#actions` — nút «+ Tạo phiếu đánh giá» nằm trong đó và
// sub-case (f2) cần bấm nó thật. Stub `true` nuốt slot ⇒ nút biến mất khỏi DOM.
const stubs = {
  PageHeader: { template: '<div><slot name="actions" /></div>' },
  FilterToggleButton: true,
}

async function mountView() {
  const w = mount(VendorEvalListView, { global: { stubs } })
  await flushPromises()
  return w
}
function state(w: ReturnType<typeof mount>) {
  return w.find('[data-testid="list-page-shell"]').attributes('data-state')
}
function retryControls(w: ReturnType<typeof mount>) {
  return w.findAll('button').filter((b) => (b.attributes('aria-label') ?? b.text()).trim() === 'Thử lại')
}

describe('/vendor-evaluations — 4 trạng thái loại trừ + thử lại (TC-UX3-32)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    resetRouteMock()
    listEvaluationsSpy.mockReset().mockResolvedValue(ok(ROWS))
    createEvaluationSpy.mockReset().mockResolvedValue({ name: 'VE-2026-0003' })
    listTechSpecsSpy.mockReset().mockResolvedValue(ok([]))
  })

  it('(a) đang tải ⇒ khung xương, 0 nội dung, 0 nút «Thử lại»', async () => {
    listEvaluationsSpy.mockReturnValue(new Promise(() => {}))
    const w = await mountView()
    expect(state(w)).toBe('loading')
    expect(w.find('[data-testid="list-skeleton"]').exists()).toBe(true)
    expect(w.findAll('[data-testid="list-content"]')).toHaveLength(0)
    expect(w.findAll('table')).toHaveLength(0)
    expect(retryControls(w)).toHaveLength(0)
  })

  it('(b) lỗi ⇒ ui-error + ĐÚNG 1 «Thử lại», KHÔNG còn banner alert-error song song', async () => {
    listEvaluationsSpy.mockRejectedValue(new Error('Máy chủ trả về 500.'))
    const w = await mountView()
    expect(state(w)).toBe('error')
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(true)
    expect(w.findAll('.alert-error')).toHaveLength(0)
    expect(w.findAll('[data-testid="list-content"]')).toHaveLength(0)
    expect(w.find('[data-testid="ui-empty"]').exists()).toBe(false)
    expect(w.text()).not.toContain('Không có phiếu đánh giá nào phù hợp')
    expect(w.text()).not.toContain('Không có dữ liệu')
    expect(w.text()).toContain('Máy chủ trả về 500.')
    expect(retryControls(w)).toHaveLength(1)
  })

  it('(c) rỗng thật ⇒ ui-empty có câu hướng dẫn tiếng Việt, 0 nút «Thử lại»', async () => {
    listEvaluationsSpy.mockResolvedValue(ok([]))
    const w = await mountView()
    expect(state(w)).toBe('empty')
    expect(w.find('[data-testid="ui-empty-title"]').text()).toBe('Chưa có phiếu đánh giá nhà cung cấp nào')
    expect(w.find('[data-testid="ui-empty-description"]').text())
      .toBe('Phiếu đánh giá được tạo từ hồ sơ kỹ thuật đã chốt.')
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
    listEvaluationsSpy.mockRejectedValueOnce(new Error('Mất kết nối.'))
    const w = await mountView()
    expect(state(w)).toBe('error')
    expect(listEvaluationsSpy).toHaveBeenCalledTimes(1)
    await retryControls(w)[0].trigger('click')
    await flushPromises()
    expect(listEvaluationsSpy).toHaveBeenCalledTimes(2)
    expect(listTechSpecsSpy).not.toHaveBeenCalled() // lời gọi phụ không ăn theo (INV-UX3-21)
    expect(state(w)).toBe('content')
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(false)
  })

  it('(f) loại trừ cấu trúc: đúng 1 shell, đúng 1 trạng thái; bộ lọc còn sống', async () => {
    listEvaluationsSpy.mockRejectedValue(new Error('X'))
    const w = await mountView()
    expect(w.findAll('[data-testid="list-page-shell"]')).toHaveLength(1)
    const present = ['list-loading', 'ui-error', 'ui-empty', 'list-content']
      .filter((t) => w.find(`[data-testid="${t}"]`).exists())
    expect(present).toEqual(['ui-error'])
    expect(w.find('[data-testid="list-filters"]').exists()).toBe(true)
    expect(w.findComponent(ListFilterBar).exists()).toBe(true)
  })

  it('(f2) lỗi của HỘP THOẠI TẠO ở lại trong hộp thoại, không cướp danh sách (INV-UX3-20)', async () => {
    // `createError` là lỗi BIỂU MẪU — phải hiện TRONG hộp thoại và KHÔNG được nối vào
    // `:error-message` của khung trang (một lần tạo hỏng không xoá trắng danh sách).
    listTechSpecsSpy.mockRejectedValue(new Error('Không tải được hồ sơ kỹ thuật.'))
    const w = await mountView()
    expect(state(w)).toBe('content')

    const openBtn = w.findAll('button').find((b) => b.text().includes('Tạo phiếu đánh giá'))!
    await openBtn.trigger('click')
    await flushPromises()

    // lỗi ĐÃ hiện thật trong hộp thoại (chứng minh đường lỗi biểu mẫu còn sống)…
    expect(w.text()).toContain('Không tải được hồ sơ kỹ thuật.')
    // …nhưng khung trang vẫn ở trạng thái có dữ liệu
    expect(state(w)).toBe('content')
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(false)
    expect(w.findAll('tbody tr')).toHaveLength(ROWS.length)
  })
})
