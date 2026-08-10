// TC-UX3-22 (AC-UX-047 · lô 1) — /rca: 4 trạng thái danh sách + «Thử lại».
//
// Biến thể C (kho Pinia): `stores/imm12.ts` ĐÃ xoá `rcaError` đầu lượt (`:112`) và gán
// trong `catch` ⇒ **KHÔNG sửa store**. Bug gốc trên đĩa 2026-08-03: dải `.alert-error`
// (`RCAListView.vue:149`) hiện SONG SONG với khối rỗng «Chưa có hồ sơ phân tích nguyên
// nhân gốc nào» ⇒ *lỗi giả dạng rỗng* trên đúng nhóm hồ sơ bắt buộc theo NĐ98.
// Ghi chú cho QA: «Thử lại» = `applyFilter()` ⇒ nạp lại TRANG 1 (chấp nhận, có chủ đích).
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { mount, flushPromises, enableAutoUnmount } from '@vue/test-utils'
import { resetRouteMock } from '@/test/vueRouterMock'

enableAutoUnmount(afterEach)

const listRcasSpy = vi.fn()
vi.mock('@/api/imm12', () => ({
  listRcas: (...a: unknown[]) => listRcasSpy(...a),
  listIncidents: vi.fn(),
  getIncidentStats: vi.fn(),
  getDashboard: vi.fn(),
  startWork: vi.fn(),
  getAssetIncidentHistory: vi.fn(),
}))
vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())

import RCAListView from './RCAListView.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'

const PAGINATION = { total: 2, page: 1, page_size: 20, total_pages: 1, offset: 0 }
const ROWS = [
  { name: 'RCA-2026-0001', incident_report: 'IR-2026-0001', asset: 'AC-ASSET-1', asset_name: 'Máy thở A',
    rca_method: '5-Why', assigned_to: 'u@x.vn', assigned_to_name: 'Nguyễn Văn A', status: 'RCA In Progress' },
  { name: 'RCA-2026-0002', incident_report: 'IR-2026-0002', asset: 'AC-ASSET-2', asset_name: 'Monitor B',
    rca_method: 'Fishbone', assigned_to: 'b@x.vn', assigned_to_name: 'Trần Thị B', status: 'Completed' },
]

const stubs = { PageHeader: true, FilterToggleButton: true, BasePagination: true }

async function mountView() {
  const w = mount(RCAListView, { global: { stubs } })
  await flushPromises()
  return w
}

function state(w: ReturnType<typeof mount>) {
  return w.find('[data-testid="list-page-shell"]').attributes('data-state')
}
function retryControls(w: ReturnType<typeof mount>) {
  return w.findAll('button').filter((b) => (b.attributes('aria-label') ?? b.text()).trim() === 'Thử lại')
}

describe('/rca — 4 trạng thái loại trừ + thử lại (TC-UX3-22)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    resetRouteMock()
    listRcasSpy.mockReset().mockResolvedValue({ items: ROWS, pagination: PAGINATION })
  })

  it('(a) đang tải ⇒ khung xương, 0 nội dung, 0 nút «Thử lại»', async () => {
    listRcasSpy.mockReturnValue(new Promise(() => {}))
    const w = await mountView()
    expect(state(w)).toBe('loading')
    expect(w.find('[data-testid="list-skeleton"]').exists()).toBe(true)
    expect(w.findAll('[data-testid="list-content"]')).toHaveLength(0)
    expect(retryControls(w)).toHaveLength(0)
  })

  it('(b) lỗi ⇒ ui-error + đúng 1 «Thử lại», KHÔNG còn chuỗi rỗng cũ', async () => {
    listRcasSpy.mockRejectedValue(new Error('Máy chủ trả về 500.'))
    const w = await mountView()
    expect(state(w)).toBe('error')
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(true)
    expect(w.findAll('.alert-error')).toHaveLength(0)
    expect(w.findAll('[data-testid="list-content"]')).toHaveLength(0)
    expect(w.text()).not.toContain('Chưa có')
    expect(retryControls(w)).toHaveLength(1)
  })

  it('(c) rỗng thật ⇒ ui-empty có câu hướng dẫn tiếng Việt, 0 nút «Thử lại»', async () => {
    listRcasSpy.mockResolvedValue({ items: [], pagination: { ...PAGINATION, total: 0 } })
    const w = await mountView()
    expect(state(w)).toBe('empty')
    expect(w.find('[data-testid="ui-empty-title"]').text()).toBe('Chưa có hồ sơ phân tích nguyên nhân gốc nào')
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
    listRcasSpy.mockRejectedValueOnce(new Error('Mất kết nối.'))
    const w = await mountView()
    expect(listRcasSpy).toHaveBeenCalledTimes(1)
    await retryControls(w)[0].trigger('click')
    await flushPromises()
    expect(listRcasSpy).toHaveBeenCalledTimes(2)
    expect(state(w)).toBe('content')
  })

  it('(f) loại trừ cấu trúc: đúng 1 shell, đúng 1 trạng thái; bộ lọc còn sống', async () => {
    listRcasSpy.mockRejectedValue(new Error('X'))
    const w = await mountView()
    expect(w.findAll('[data-testid="list-page-shell"]')).toHaveLength(1)
    const present = ['list-loading', 'ui-error', 'ui-empty', 'list-content']
      .filter((t) => w.find(`[data-testid="${t}"]`).exists())
    expect(present).toEqual(['ui-error'])
    expect(w.findComponent(ListFilterBar).exists()).toBe(true)
  })
})
