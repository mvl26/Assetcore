// TC-UX3-21 (AC-UX-047 · lô 1) — /incidents/list: 4 trạng thái danh sách + «Thử lại».
//
// Biến thể C (kho Pinia): `stores/imm12.ts` ĐÃ xoá lỗi đầu lượt (`error.value = null`,
// `:64`) và gán trong `catch` (`:72`) ⇒ **KHÔNG sửa store**, chỉ nối `store.error` vào
// khuôn. Bug gốc trên đĩa 2026-08-03: dải `.alert-error` (`IncidentListView.vue:260`)
// hiện SONG SONG với bảng rỗng ⇒ vẫn in «Không có sự cố nào được báo cáo» + dải KPI in
// số 0 (tín hiệu giả cùng lớp false-empty), và KHÔNG có nút thử lại.
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { mount, flushPromises, enableAutoUnmount } from '@vue/test-utils'
import { resetRouteMock } from '@/test/vueRouterMock'

enableAutoUnmount(afterEach)

const listIncidentsSpy = vi.fn()
const getIncidentStatsSpy = vi.fn()
vi.mock('@/api/imm12', () => ({
  listIncidents: (...a: unknown[]) => listIncidentsSpy(...a),
  getIncidentStats: (...a: unknown[]) => getIncidentStatsSpy(...a),
  getDashboard: vi.fn(),
  startWork: vi.fn(),
  listRcas: vi.fn(),
  getAssetIncidentHistory: vi.fn(),
}))
vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({ can: () => true }),
}))
vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())

import IncidentListView from './IncidentListView.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'

const PAGINATION = { total: 2, page: 1, page_size: 20, total_pages: 1, offset: 0 }
const ROWS = [
  { name: 'IR-2026-0001', asset: 'AC-ASSET-1', asset_name: 'Máy thở A', severity: 'Critical',
    status: 'Open', reported_at: '2026-07-01T08:00:00', description: 'Máy báo lỗi nguồn', patient_affected: 0 },
  { name: 'IR-2026-0002', asset: 'AC-ASSET-2', asset_name: 'Monitor B', severity: 'High',
    status: 'In Progress', reported_at: '2026-07-02T09:00:00', description: 'Màn hình chớp tắt', patient_affected: 0 },
]

const stubs = { PageHeader: true, FilterToggleButton: true, BasePagination: true, SlaBreachBadge: true }

async function mountView() {
  const w = mount(IncidentListView, { global: { stubs } })
  await flushPromises()
  return w
}

function state(w: ReturnType<typeof mount>) {
  return w.find('[data-testid="list-page-shell"]').attributes('data-state')
}
function retryControls(w: ReturnType<typeof mount>) {
  return w.findAll('button').filter((b) => (b.attributes('aria-label') ?? b.text()).trim() === 'Thử lại')
}

describe('/incidents/list — 4 trạng thái loại trừ + thử lại (TC-UX3-21)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    resetRouteMock()
    listIncidentsSpy.mockReset().mockResolvedValue({ items: ROWS, pagination: PAGINATION })
    getIncidentStatsSpy.mockReset().mockResolvedValue({ critical_open: 1, high_open: 1, chronic: 0, closed: 3 })
  })

  it('(a) đang tải ⇒ khung xương, 0 nội dung, 0 nút «Thử lại»', async () => {
    listIncidentsSpy.mockReturnValue(new Promise(() => {}))
    const w = await mountView()
    expect(state(w)).toBe('loading')
    expect(w.find('[data-testid="list-skeleton"]').exists()).toBe(true)
    expect(w.findAll('[data-testid="list-content"]')).toHaveLength(0)
    expect(retryControls(w)).toHaveLength(0)
  })

  it('(b) lỗi ⇒ ui-error + đúng 1 «Thử lại», KHÔNG còn chuỗi rỗng cũ và KHÔNG còn dải KPI', async () => {
    listIncidentsSpy.mockRejectedValue(new Error('Máy chủ trả về 500.'))
    const w = await mountView()
    expect(state(w)).toBe('error')
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(true)
    expect(w.findAll('.alert-error')).toHaveLength(0)
    expect(w.findAll('[data-testid="list-content"]')).toHaveLength(0)
    expect(w.text()).not.toContain('Không có sự cố nào được báo cáo')
    expect(w.text()).not.toContain('Chưa có')
    // dải KPI nằm ở #summary — shell chỉ render #summary ở empty/content
    expect(w.text()).not.toContain('Sự cố nghiêm trọng đang mở')
    expect(retryControls(w)).toHaveLength(1)
  })

  it('(c) rỗng thật ⇒ ui-empty có câu hướng dẫn tiếng Việt, 0 nút «Thử lại»', async () => {
    listIncidentsSpy.mockResolvedValue({ items: [], pagination: { ...PAGINATION, total: 0 } })
    const w = await mountView()
    expect(state(w)).toBe('empty')
    expect(w.find('[data-testid="ui-empty-title"]').text()).toBe('Không có sự cố nào được báo cáo')
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

  it('(e) «Thử lại» gọi lại danh sách ĐÚNG 1 lần (không kéo theo lượt nạp chỉ số)', async () => {
    listIncidentsSpy.mockRejectedValueOnce(new Error('Mất kết nối.'))
    const w = await mountView()
    expect(state(w)).toBe('error')
    expect(listIncidentsSpy).toHaveBeenCalledTimes(1)
    const statCallsBefore = getIncidentStatsSpy.mock.calls.length
    await retryControls(w)[0].trigger('click')
    await flushPromises()
    expect(listIncidentsSpy).toHaveBeenCalledTimes(2)
    expect(getIncidentStatsSpy.mock.calls.length).toBe(statCallsBefore)
    expect(state(w)).toBe('content')
  })

  it('(f) loại trừ cấu trúc: đúng 1 shell, đúng 1 trạng thái; bộ lọc còn sống', async () => {
    listIncidentsSpy.mockRejectedValue(new Error('X'))
    const w = await mountView()
    expect(w.findAll('[data-testid="list-page-shell"]')).toHaveLength(1)
    const present = ['list-loading', 'ui-error', 'ui-empty', 'list-content']
      .filter((t) => w.find(`[data-testid="${t}"]`).exists())
    expect(present).toEqual(['ui-error'])
    expect(w.findComponent(ListFilterBar).exists()).toBe(true)
  })
})
