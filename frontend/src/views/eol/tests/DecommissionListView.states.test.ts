// TC-UX3-38 (AC-UX-047 · lô 3) — /decommissions: 4 trạng thái danh sách + «Thử lại».
//
// Nợ đo trên đĩa 2026-08-04 (loại γ — docs/ui-ux/02 §14.4): màn ĐÃ tri-branch đúng
// (`:216-222` lỗi ⇄ `:223-237` rỗng loại trừ nhau), nhưng tự cài lại máy trạng thái nên nút
// «Thử lại» là `btn-secondary` tự chế — khác nhãn SSoT của `ui/ErrorState` — và câu rỗng nằm
// ngoài bảng copy. Áp khuôn để MỘT nơi giữ hợp đồng cho cả 40 màn danh sách.
//
// `load()` dùng `useApi` với `silentError: true`; khung xương bám `api.loading && !rows.length`
// (giữ nguyên ngữ nghĩa: nạp lại trang khác KHÔNG xoá bảng đang xem).
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises, enableAutoUnmount } from '@vue/test-utils'
import { resetRouteMock } from '@/test/vueRouterMock'

enableAutoUnmount(afterEach)

const listDecommissionsSpy = vi.fn()

vi.mock('@/api/imm14', async (importOriginal) => ({
  ...(await importOriginal<Record<string, unknown>>()),
  listDecommissions: (...a: unknown[]) => listDecommissionsSpy(...a),
}))
vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())

import DecommissionListView from '@/views/eol/DecommissionListView.vue'

const ROWS = [
  {
    name: 'DEC-2026-0001', asset: 'AC-ASSET-2026-00001', asset_name_snapshot: 'Máy thở Hamilton C1',
    disposal_method: 'Scrap', workflow_state: 'Approved', decommissioned_on: '2026-06-01',
    responsible_name: 'Nguyễn Văn A',
  },
  {
    name: 'DEC-2026-0002', asset: 'AC-ASSET-2026-00002', asset_name_snapshot: 'Máy siêu âm GE Logiq',
    disposal_method: 'Donation', workflow_state: 'Draft', decommissioned_on: '',
    responsible_name: 'Trần Thị B',
  },
]
const ok = (rows: unknown[]) => ({
  data: rows,
  pagination: { page: 1, page_size: 20, total: rows.length, total_pages: rows.length ? 1 : 0 },
})

const stubs = { PageHeader: true }

async function mountView() {
  const w = mount(DecommissionListView, { global: { stubs } })
  await flushPromises()
  return w
}
function state(w: ReturnType<typeof mount>) {
  return w.find('[data-testid="list-page-shell"]').attributes('data-state')
}
function retryControls(w: ReturnType<typeof mount>) {
  return w.findAll('button').filter((b) => (b.attributes('aria-label') ?? b.text()).trim() === 'Thử lại')
}

describe('/decommissions — 4 trạng thái loại trừ + thử lại (TC-UX3-38)', () => {
  beforeEach(() => {
    resetRouteMock()
    listDecommissionsSpy.mockReset().mockResolvedValue(ok(ROWS))
  })

  it('(a) đang tải ⇒ khung xương, 0 nội dung, 0 nút «Thử lại»', async () => {
    listDecommissionsSpy.mockReturnValue(new Promise(() => {}))
    const w = await mountView()
    expect(state(w)).toBe('loading')
    expect(w.find('[data-testid="list-skeleton"]').exists()).toBe(true)
    expect(w.findAll('[data-testid="list-content"]')).toHaveLength(0)
    expect(w.findAll('table')).toHaveLength(0)
    expect(retryControls(w)).toHaveLength(0)
  })

  it('(b) lỗi ⇒ ui-error + ĐÚNG 1 «Thử lại», 0 khối rỗng (:213 ⇄ :223)', async () => {
    listDecommissionsSpy.mockRejectedValue(new Error('Máy chủ trả về 500.'))
    const w = await mountView()
    expect(state(w)).toBe('error')
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(true)
    expect(w.findAll('[data-testid="list-content"]')).toHaveLength(0)
    expect(w.find('[data-testid="ui-empty"]').exists()).toBe(false)
    expect(w.text()).not.toContain('Chưa có biên bản giải nhiệm nào')
    expect(w.text()).not.toContain('Không có biên bản giải nhiệm nào phù hợp')
    expect(retryControls(w)).toHaveLength(1)
  })

  it('(c) rỗng thật ⇒ ui-empty có câu hướng dẫn tiếng Việt + lối đi tiếp', async () => {
    listDecommissionsSpy.mockResolvedValue(ok([]))
    const w = await mountView()
    expect(state(w)).toBe('empty')
    expect(w.findAll('[data-testid="ui-empty"]')).toHaveLength(1)
    expect(w.find('[data-testid="ui-empty-title"]').text()).toBe('Chưa có biên bản giải nhiệm nào')
    expect(w.find('[data-testid="ui-empty-description"]').text()).toBe(
      'Biên bản giải nhiệm được lập từ hồ sơ thiết bị (nút «Giải nhiệm»).',
    )
    expect(
      w.findAll('button').some((b) => b.text().trim() === 'Đến danh sách thiết bị'),
      'màn rỗng phải có lối đi tiếp (biên bản chỉ lập được từ hồ sơ thiết bị)',
    ).toBe(true)
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(false)
    expect(retryControls(w)).toHaveLength(0)
  })

  it('(d) có dữ liệu ⇒ đúng N dòng, 0 rỗng/lỗi', async () => {
    const w = await mountView()
    expect(state(w)).toBe('content')
    expect(w.find('[data-testid="list-data"]').exists()).toBe(true)
    expect(w.findAll('tbody tr')).toHaveLength(ROWS.length)
    expect(w.find('[data-testid="ui-empty"]').exists()).toBe(false)
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(false)
  })

  it('(e) «Thử lại» gọi lại đúng hàm nạp 1 lần ⇒ error → content', async () => {
    listDecommissionsSpy.mockRejectedValueOnce(new Error('Mất kết nối.'))
    const w = await mountView()
    expect(state(w)).toBe('error')
    expect(listDecommissionsSpy).toHaveBeenCalledTimes(1)
    await retryControls(w)[0].trigger('click')
    await flushPromises()
    expect(listDecommissionsSpy).toHaveBeenCalledTimes(2)
    expect(state(w)).toBe('content')
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(false)
  })

  it('(f) loại trừ cấu trúc: đúng 1 shell, đúng 1 trạng thái; bộ lọc còn sống', async () => {
    listDecommissionsSpy.mockRejectedValue(new Error('X'))
    const w = await mountView()
    expect(w.findAll('[data-testid="list-page-shell"]')).toHaveLength(1)
    const present = ['list-loading', 'ui-error', 'ui-empty', 'list-content'].filter((t) =>
      w.find(`[data-testid="${t}"]`).exists(),
    )
    expect(present).toEqual(['ui-error'])
    const filters = w.find('[data-testid="list-filters"]')
    expect(filters.exists()).toBe(true)
    expect(filters.find('#decom-state-filter').exists()).toBe(true)
  })
})
