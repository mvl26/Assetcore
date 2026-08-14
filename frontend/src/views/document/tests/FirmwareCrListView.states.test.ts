// TC-UX3-19 (AC-UX-047 · lô 1) — /cm/firmware: 4 trạng thái danh sách + «Thử lại».
//
// Bug gốc đo trên đĩa 2026-08-03: `load()` (`FirmwareCrListView.vue:162`) có `try … finally`
// nhưng **0 `catch`** ⇒ API hỏng ⇒ in «Chưa có yêu cầu nào.». Biến `err` thuộc HỘP THOẠI
// (`:230`) — KHÔNG nối vào danh sách (INV-UX3-13).
// Bẫy riêng: `loadAssetMeta()` là lượt nạp KHÁC (tự nuốt lỗi) ⇒ «Thử lại» chỉ gọi `load()`.
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises, enableAutoUnmount } from '@vue/test-utils'
import { resetRouteMock } from '@/test/vueRouterMock'

enableAutoUnmount(afterEach)

const listFirmwareCrsSpy = vi.fn()
const getAssetActionMetaSpy = vi.fn()
vi.mock('@/api/imm00', () => ({
  listFirmwareCrs: (...a: unknown[]) => listFirmwareCrsSpy(...a),
  getFirmwareCr: vi.fn(),
  createFirmwareCr: vi.fn(),
  updateFirmwareCr: vi.fn(),
  deleteFirmwareCr: vi.fn(),
  getAssetActionMeta: (...a: unknown[]) => getAssetActionMetaSpy(...a),
}))
vi.mock('@/api/imm09', () => ({
  listRepairWorkOrders: vi.fn().mockResolvedValue({ data: [] }),
}))
vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())

import FirmwareCrListView from '@/views/document/FirmwareCrListView.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'

const ROWS = [
  { name: 'FCR-2026-0001', asset_ref: 'AC-ASSET-1', asset_name: 'Máy thở A', version_before: 'v1.0',
    version_after: 'v1.1', status: 'Draft' },
  { name: 'FCR-2026-0002', asset_ref: 'AC-ASSET-2', asset_name: 'Monitor B', version_before: 'v2.0',
    version_after: 'v2.1', status: 'Approved', approved_by: 'u@x.vn', approved_by_name: 'Nguyễn Văn A' },
]

const stubs = { PageHeader: true, FilterToggleButton: true, SmartSelect: true }

async function mountView() {
  const w = mount(FirmwareCrListView, { global: { stubs } })
  await flushPromises()
  return w
}

function state(w: ReturnType<typeof mount>) {
  return w.find('[data-testid="list-page-shell"]').attributes('data-state')
}
function retryControls(w: ReturnType<typeof mount>) {
  return w.findAll('button').filter((b) => (b.attributes('aria-label') ?? b.text()).trim() === 'Thử lại')
}

describe('/cm/firmware — 4 trạng thái loại trừ + thử lại (TC-UX3-19)', () => {
  beforeEach(() => {
    resetRouteMock()
    listFirmwareCrsSpy.mockReset().mockResolvedValue({ items: ROWS, total: ROWS.length })
    getAssetActionMetaSpy.mockReset().mockResolvedValue({})
  })

  it('(a) đang tải ⇒ khung xương, 0 nội dung, 0 nút «Thử lại»', async () => {
    listFirmwareCrsSpy.mockReturnValue(new Promise(() => {}))
    const w = await mountView()
    expect(state(w)).toBe('loading')
    expect(w.find('[data-testid="list-skeleton"]').exists()).toBe(true)
    expect(w.findAll('[data-testid="list-content"]')).toHaveLength(0)
    expect(retryControls(w)).toHaveLength(0)
  })

  it('(b) lỗi ⇒ ui-error + đúng 1 «Thử lại», KHÔNG còn chuỗi rỗng cũ', async () => {
    listFirmwareCrsSpy.mockRejectedValue(new Error('Máy chủ trả về 500.'))
    const w = await mountView()
    expect(state(w)).toBe('error')
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(true)
    expect(w.findAll('[data-testid="list-content"]')).toHaveLength(0)
    expect(w.text()).not.toContain('Chưa có')
    expect(retryControls(w)).toHaveLength(1)
  })

  it('(c) rỗng thật ⇒ ui-empty có câu hướng dẫn tiếng Việt, 0 nút «Thử lại»', async () => {
    listFirmwareCrsSpy.mockResolvedValue({ items: [], total: 0 })
    const w = await mountView()
    expect(state(w)).toBe('empty')
    expect(w.find('[data-testid="ui-empty-title"]').text()).toBe('Chưa có yêu cầu thay đổi phần mềm nào')
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

  it('(e) «Thử lại» gọi lại ĐÚNG hàm nạp danh sách (không kéo theo lượt nạp meta)', async () => {
    listFirmwareCrsSpy.mockRejectedValueOnce(new Error('Mất kết nối.'))
    const w = await mountView()
    expect(listFirmwareCrsSpy).toHaveBeenCalledTimes(1)
    const metaCallsBefore = getAssetActionMetaSpy.mock.calls.length
    await retryControls(w)[0].trigger('click')
    await flushPromises()
    expect(listFirmwareCrsSpy).toHaveBeenCalledTimes(2)
    expect(getAssetActionMetaSpy.mock.calls.length).toBe(metaCallsBefore)
    expect(state(w)).toBe('content')
  })

  it('(f) loại trừ cấu trúc: đúng 1 shell, đúng 1 trạng thái; bộ lọc còn sống', async () => {
    listFirmwareCrsSpy.mockRejectedValue(new Error('X'))
    const w = await mountView()
    expect(w.findAll('[data-testid="list-page-shell"]')).toHaveLength(1)
    const present = ['list-loading', 'ui-error', 'ui-empty', 'list-content']
      .filter((t) => w.find(`[data-testid="${t}"]`).exists())
    expect(present).toEqual(['ui-error'])
    expect(w.findComponent(ListFilterBar).exists()).toBe(true)
  })
})
