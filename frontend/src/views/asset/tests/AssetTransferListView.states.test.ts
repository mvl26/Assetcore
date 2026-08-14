// TC-UX3-12 (AC-UX-047 · lô 1) — /asset-transfers: 4 trạng thái danh sách + «Thử lại».
//
// Bug gốc đo trên đĩa 2026-08-03: `load()` (`AssetTransferListView.vue:99`) KHÔNG có
// `try/catch/finally`; `loading.value = false` nằm SAU `await` ⇒ API hỏng thì promise
// reject, `loading` KẸT `true` (khung xương quay mãi) + unhandled rejection. Nếu nạp
// xong mà rỗng thì in «Không có dữ liệu chuyển giao.» — lỗi giả dạng rỗng.
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises, enableAutoUnmount } from '@vue/test-utils'
import { resetRouteMock } from '@/test/vueRouterMock'

enableAutoUnmount(afterEach)

const frappeGetSpy = vi.fn()
const frappePostSpy = vi.fn()
vi.mock('@/api/helpers', () => ({
  frappeGet: (...a: unknown[]) => frappeGetSpy(...a),
  frappePost: (...a: unknown[]) => frappePostSpy(...a),
}))
vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({ can: () => true }),
}))
vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())

import AssetTransferListView from '@/views/asset/AssetTransferListView.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'

const ROWS = [
  { name: 'AT-2026-0001', asset: 'AC-ASSET-1', asset_name: 'Máy thở A', transfer_type: 'Internal',
    status: 'Approved', transfer_date: '2026-07-01', from_location_name: 'Khoa A', to_location_name: 'Khoa B', reason: 'Điều phối' },
  { name: 'AT-2026-0002', asset: 'AC-ASSET-2', asset_name: 'Monitor B', transfer_type: 'Loan',
    status: 'Pending Approval', transfer_date: '2026-07-02', from_location_name: 'Khoa B', to_location_name: 'Khoa C', reason: 'Mượn' },
]

const stubs = { PageHeader: true, FilterToggleButton: true }

async function mountView() {
  const w = mount(AssetTransferListView, { global: { stubs } })
  await flushPromises()
  return w
}

function state(w: ReturnType<typeof mount>) {
  return w.find('[data-testid="list-page-shell"]').attributes('data-state')
}
function retryControls(w: ReturnType<typeof mount>) {
  return w.findAll('button').filter((b) => (b.attributes('aria-label') ?? b.text()).trim() === 'Thử lại')
}

describe('/asset-transfers — 4 trạng thái loại trừ + thử lại (TC-UX3-12)', () => {
  beforeEach(() => {
    resetRouteMock()
    frappeGetSpy.mockReset().mockResolvedValue({ items: ROWS, pagination: { total: ROWS.length } })
    frappePostSpy.mockReset().mockResolvedValue(undefined)
  })

  it('(a) đang tải ⇒ khung xương, 0 nội dung, 0 nút «Thử lại»', async () => {
    frappeGetSpy.mockReturnValue(new Promise(() => {}))
    const w = await mountView()
    expect(state(w)).toBe('loading')
    expect(w.find('[data-testid="list-skeleton"]').exists()).toBe(true)
    expect(w.findAll('[data-testid="list-content"]')).toHaveLength(0)
    expect(retryControls(w)).toHaveLength(0)
  })

  it('(b) lỗi ⇒ ui-error + đúng 1 «Thử lại», KHÔNG còn chuỗi rỗng cũ (và không kẹt khung xương)', async () => {
    frappeGetSpy.mockRejectedValue(new Error('Máy chủ trả về 500.'))
    const w = await mountView()
    expect(state(w)).toBe('error')
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(true)
    expect(w.findAll('[data-testid="list-content"]')).toHaveLength(0)
    expect(w.findAll('[data-testid="list-loading"]')).toHaveLength(0)
    expect(w.text()).not.toContain('Chưa có')
    expect(w.text()).not.toContain('Không có dữ liệu')
    expect(retryControls(w)).toHaveLength(1)
  })

  it('(c) rỗng thật ⇒ ui-empty có câu hướng dẫn tiếng Việt, 0 nút «Thử lại»', async () => {
    frappeGetSpy.mockResolvedValue({ items: [], pagination: { total: 0 } })
    const w = await mountView()
    expect(state(w)).toBe('empty')
    expect(w.find('[data-testid="ui-empty-title"]').text()).toBe('Chưa có lượt chuyển giao nào')
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
    frappeGetSpy.mockRejectedValueOnce(new Error('Mất kết nối.'))
    const w = await mountView()
    expect(frappeGetSpy).toHaveBeenCalledTimes(1)
    await retryControls(w)[0].trigger('click')
    await flushPromises()
    expect(frappeGetSpy).toHaveBeenCalledTimes(2)
    expect(state(w)).toBe('content')
  })

  it('(f) loại trừ cấu trúc: đúng 1 shell, đúng 1 trạng thái; bộ lọc còn sống', async () => {
    frappeGetSpy.mockRejectedValue(new Error('X'))
    const w = await mountView()
    expect(w.findAll('[data-testid="list-page-shell"]')).toHaveLength(1)
    const present = ['list-loading', 'ui-error', 'ui-empty', 'list-content']
      .filter((t) => w.find(`[data-testid="${t}"]`).exists())
    expect(present).toEqual(['ui-error'])
    expect(w.findComponent(ListFilterBar).exists()).toBe(true)
  })
})
