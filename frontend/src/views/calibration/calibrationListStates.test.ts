// TC-UX3-24 (AC-UX-047 · lô 2) — /calibration: 4 trạng thái danh sách + «Thử lại».
//
// Bug gốc đo trên đĩa 2026-08-04: `load()` KHÔNG có đường báo lỗi — `stores/imm11.ts`
// nuốt lỗi vào ô `error` dùng CHUNG (`_captureError`) cho danh sách + chỉ-số + lịch +
// transition. View chỉ có 2 nhánh (`loading` / `!items.length`) ⇒ API hỏng rơi thẳng
// vào khối rỗng «Chưa có phiếu hiệu chuẩn nào» — *lỗi giả dạng rỗng*, không thử lại
// được. Thêm mã chết: khối «Không có dữ liệu» (`:262`) nằm TRONG nhánh CÓ dữ liệu.
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises, enableAutoUnmount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { resetRouteMock } from '@/test/vueRouterMock'

enableAutoUnmount(afterEach)

const listCalibrationsSpy = vi.fn()
const getCalibrationKpisSpy = vi.fn()
// `importOriginal` + ghi đè ĐÚNG hàm nạp: `stores/imm11.ts` import tĩnh nhiều hàm từ
// module này; liệt kê tay sẽ trôi lệch khi lớp API thêm hàm mới.
vi.mock('@/api/imm11', async (importOriginal) => ({
  ...(await importOriginal<Record<string, unknown>>()),
  listCalibrations: (...a: unknown[]) => listCalibrationsSpy(...a),
  getCalibrationKpis: (...a: unknown[]) => getCalibrationKpisSpy(...a),
}))
vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({ can: () => true }),
}))
vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())

import CalibrationListView from './CalibrationListView.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'

const ROWS = [
  { name: 'CAL-2026-00001', asset: 'AC-ASSET-2026-00001', asset_name: 'Máy thở Hamilton C1',
    calibration_type: 'In-House', status: 'Scheduled', scheduled_date: '2026-08-10',
    next_calibration_date: '2027-08-10', overall_result: '', is_overdue: 0, is_due_soon: 0 },
  { name: 'CAL-2026-00002', asset: 'AC-ASSET-2026-00002', asset_name: 'Máy siêu âm GE Logiq',
    calibration_type: 'External', status: 'Completed', scheduled_date: '2026-07-01',
    next_calibration_date: '2027-07-01', overall_result: 'Pass', is_overdue: 0, is_due_soon: 1 },
]
const ok = (rows: unknown[]) => ({ data: rows, pagination: { total: rows.length, page: 1, page_size: 20, total_pages: 1 } })
const KPIS = {
  kpis: { total_this_month: 5, completed: 3, failed: 1, pass_rate_pct: 75, overdue_assets: 2, due_soon_assets: 4 },
}

const stubs = { PageHeader: true, FilterToggleButton: true }

async function mountView() {
  const w = mount(CalibrationListView, { global: { stubs } })
  await flushPromises()
  return w
}
function state(w: ReturnType<typeof mount>) {
  return w.find('[data-testid="list-page-shell"]').attributes('data-state')
}
function retryControls(w: ReturnType<typeof mount>) {
  return w.findAll('button').filter((b) => (b.attributes('aria-label') ?? b.text()).trim() === 'Thử lại')
}

describe('/calibration — 4 trạng thái loại trừ + thử lại (TC-UX3-24)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    resetRouteMock()
    listCalibrationsSpy.mockReset().mockResolvedValue(ok(ROWS))
    getCalibrationKpisSpy.mockReset().mockResolvedValue(KPIS)
  })

  it('(a) đang tải ⇒ khung xương, 0 nội dung, 0 nút «Thử lại»', async () => {
    listCalibrationsSpy.mockReturnValue(new Promise(() => {}))
    const w = await mountView()
    expect(state(w)).toBe('loading')
    expect(w.find('[data-testid="list-skeleton"]').exists()).toBe(true)
    expect(w.findAll('[data-testid="list-content"]')).toHaveLength(0)
    expect(w.findAll('table')).toHaveLength(0)
    expect(retryControls(w)).toHaveLength(0)
  })

  it('(b) lỗi ⇒ ui-error + ĐÚNG 1 «Thử lại», KHÔNG còn câu rỗng cũ', async () => {
    listCalibrationsSpy.mockRejectedValue(new Error('Máy chủ trả về 500.'))
    const w = await mountView()
    expect(state(w)).toBe('error')
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(true)
    expect(w.findAll('.alert-error')).toHaveLength(0)
    expect(w.findAll('[data-testid="list-content"]')).toHaveLength(0)
    expect(w.find('[data-testid="ui-empty"]').exists()).toBe(false)
    expect(w.text()).not.toContain('Chưa có phiếu hiệu chuẩn nào')
    expect(w.text()).not.toContain('Không có dữ liệu')
    expect(w.text()).toContain('Máy chủ trả về 500.')
    expect(retryControls(w)).toHaveLength(1)
  })

  it('(b2) lỗi ⇒ dải CHỈ SỐ biến mất, không in số 0 lên màn hỏng', async () => {
    // Dải 6 thẻ chỉ-số nằm ở slot `#summary` (chỉ render ở empty/content). Trước đây nó
    // nằm ngoài mọi nhánh ⇒ danh sách hỏng mà thẻ vẫn in số như thật.
    listCalibrationsSpy.mockRejectedValue(new Error('Máy chủ trả về 500.'))
    const w = await mountView()
    expect(state(w)).toBe('error')
    expect(w.find('[data-testid="list-summary"]').exists()).toBe(false)
    expect(w.text()).not.toContain('Tỷ lệ đạt')
  })

  it('(c) rỗng thật ⇒ ui-empty có câu hướng dẫn tiếng Việt, 0 nút «Thử lại»', async () => {
    listCalibrationsSpy.mockResolvedValue(ok([]))
    const w = await mountView()
    expect(state(w)).toBe('empty')
    expect(w.find('[data-testid="ui-empty-title"]').text()).toBe('Chưa có phiếu hiệu chuẩn nào')
    expect(w.find('[data-testid="ui-empty-description"]').text())
      .toBe('Hãy tạo phiếu hiệu chuẩn mới hoặc xoá bộ lọc để xem tất cả.')
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

  it('(e) «Thử lại» gọi lại đúng hàm nạp 1 lần; lời gọi chỉ-số KHÔNG tăng', async () => {
    listCalibrationsSpy.mockRejectedValueOnce(new Error('Mất kết nối.'))
    const w = await mountView()
    expect(state(w)).toBe('error')
    expect(listCalibrationsSpy).toHaveBeenCalledTimes(1)
    const kpiCallsBefore = getCalibrationKpisSpy.mock.calls.length
    await retryControls(w)[0].trigger('click')
    await flushPromises()
    expect(listCalibrationsSpy).toHaveBeenCalledTimes(2)
    expect(getCalibrationKpisSpy).toHaveBeenCalledTimes(kpiCallsBefore) // INV-UX3-21
    expect(state(w)).toBe('content')
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(false)
  })

  it('(f) loại trừ cấu trúc: đúng 1 shell, đúng 1 trạng thái; bộ lọc còn sống', async () => {
    listCalibrationsSpy.mockRejectedValue(new Error('X'))
    const w = await mountView()
    expect(w.findAll('[data-testid="list-page-shell"]')).toHaveLength(1)
    const present = ['list-loading', 'ui-error', 'ui-empty', 'list-content']
      .filter((t) => w.find(`[data-testid="${t}"]`).exists())
    expect(present).toEqual(['ui-error'])
    expect(w.find('[data-testid="list-filters"]').exists()).toBe(true)
    expect(w.findComponent(ListFilterBar).exists()).toBe(true)
  })

  it('(f2) lỗi nạp CHỈ-SỐ không cướp trạng thái danh sách (INV-UX3-20)', async () => {
    // `fetchKpis` dùng CHUNG ô `store.error` với `fetchList` (`_captureError`).
    // Bind thẳng ô đó ⇒ chỉ-số hỏng sẽ xoá trắng danh sách đang hiển thị.
    getCalibrationKpisSpy.mockRejectedValue(new Error('Chỉ số hỏng.'))
    const w = await mountView()
    expect(state(w)).toBe('content')
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(false)
    expect(w.findAll('tbody tr')).toHaveLength(ROWS.length)
  })
})
