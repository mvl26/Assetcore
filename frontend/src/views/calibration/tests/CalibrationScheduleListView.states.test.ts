// TC-UX3-25 (AC-UX-047 · lô 2) — /calibration/schedules: 4 trạng thái danh sách + «Thử lại».
//
// Bug gốc đo trên đĩa 2026-08-04: `load()` bắt lỗi rồi CHỈ báo bằng toast tự tắt
// (`notify.fromError`) trong khi `items` giữ nguyên dữ liệu cũ ⇒ sau vài giây người dùng
// nhìn màn hình không còn dấu vết lỗi nào, tưởng dữ liệu đang hiển thị là mới. Nếu lượt
// nạp đầu hỏng thì `items` rỗng ⇒ rơi vào câu «Chưa có lịch hiệu chuẩn.» — *lỗi giả dạng
// rỗng*. Thêm mã chết: «Không có dữ liệu» (`:370`) nằm TRONG nhánh CÓ dữ liệu.
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises, enableAutoUnmount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { resetRouteMock } from '@/test/vueRouterMock'

enableAutoUnmount(afterEach)

const listCalibrationSchedulesSpy = vi.fn()
const notifyFromErrorSpy = vi.fn()
// `importOriginal` + ghi đè ĐÚNG hàm nạp: view import tĩnh 4 hàm từ module này;
// liệt kê tay sẽ trôi lệch khi lớp API thêm hàm mới.
vi.mock('@/api/imm11', async (importOriginal) => ({
  ...(await importOriginal<Record<string, unknown>>()),
  listCalibrationSchedules: (...a: unknown[]) => listCalibrationSchedulesSpy(...a),
}))
vi.mock('@/composables/useNotify', () => ({
  useNotify: () => ({ show: vi.fn(), fromError: (...a: unknown[]) => notifyFromErrorSpy(...a) }),
}))
vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())

import CalibrationScheduleListView from '@/views/calibration/CalibrationScheduleListView.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'

const ROWS = [
  { name: 'CS-2026-0001', asset: 'AC-ASSET-2026-00001', asset_name: 'Máy thở Hamilton C1',
    calibration_type: 'In-House', interval_days: 365, next_due_date: '2027-01-01', is_active: 1 },
  { name: 'CS-2026-0002', asset: 'AC-ASSET-2026-00002', asset_name: 'Máy siêu âm GE Logiq',
    calibration_type: 'External', interval_days: 180, next_due_date: '2026-09-01', is_active: 0 },
]
const ok = (rows: unknown[]) => ({
  data: rows,
  pagination: { total: rows.length, page: 1, page_size: 20, total_pages: 1 },
})

const stubs = { PageHeader: true, FilterToggleButton: true, BaseModal: true, DateInput: true, SmartSelect: true }

async function mountView() {
  const w = mount(CalibrationScheduleListView, { global: { stubs } })
  await flushPromises()
  return w
}
function state(w: ReturnType<typeof mount>) {
  return w.find('[data-testid="list-page-shell"]').attributes('data-state')
}
function retryControls(w: ReturnType<typeof mount>) {
  return w.findAll('button').filter((b) => (b.attributes('aria-label') ?? b.text()).trim() === 'Thử lại')
}

describe('/calibration/schedules — 4 trạng thái loại trừ + thử lại (TC-UX3-25)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    resetRouteMock()
    listCalibrationSchedulesSpy.mockReset().mockResolvedValue(ok(ROWS))
    notifyFromErrorSpy.mockReset()
  })

  it('(a) đang tải ⇒ khung xương, 0 nội dung, 0 nút «Thử lại»', async () => {
    listCalibrationSchedulesSpy.mockReturnValue(new Promise(() => {}))
    const w = await mountView()
    expect(state(w)).toBe('loading')
    expect(w.find('[data-testid="list-skeleton"]').exists()).toBe(true)
    expect(w.findAll('[data-testid="list-content"]')).toHaveLength(0)
    expect(w.findAll('table')).toHaveLength(0)
    expect(retryControls(w)).toHaveLength(0)
  })

  it('(b) lỗi ⇒ ui-error + ĐÚNG 1 «Thử lại», KHÔNG còn câu rỗng cũ', async () => {
    listCalibrationSchedulesSpy.mockRejectedValue(new Error('Máy chủ trả về 500.'))
    const w = await mountView()
    expect(state(w)).toBe('error')
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(true)
    expect(w.findAll('[data-testid="list-content"]')).toHaveLength(0)
    expect(w.find('[data-testid="ui-empty"]').exists()).toBe(false)
    expect(w.text()).not.toContain('Chưa có lịch hiệu chuẩn.')
    expect(w.text()).not.toContain('Không có lịch phù hợp.')
    expect(w.text()).not.toContain('Không có dữ liệu')
    expect(w.text()).toContain('Máy chủ trả về 500.')
    expect(retryControls(w)).toHaveLength(1)
  })

  it('(b2) lỗi nạp KHÔNG còn chỉ báo bằng toast tự tắt', async () => {
    // Lỗi phải ở LẠI trên khung trang. `notify.fromError` chỉ dành cho save()/xoá.
    listCalibrationSchedulesSpy.mockRejectedValue(new Error('Máy chủ trả về 500.'))
    const w = await mountView()
    expect(state(w)).toBe('error')
    expect(notifyFromErrorSpy).not.toHaveBeenCalled()
  })

  it('(b3) lỗi ⇒ KHÔNG giữ lại dữ liệu cũ bên dưới (INV-UX3-5)', async () => {
    const w = await mountView()
    expect(state(w)).toBe('content')
    expect(w.findAll('tbody tr')).toHaveLength(ROWS.length)
    listCalibrationSchedulesSpy.mockRejectedValue(new Error('Mất kết nối.'))
    w.findComponent(ListFilterBar).vm.$emit('apply')
    await flushPromises()
    expect(state(w)).toBe('error')
    expect(w.findAll('tbody tr')).toHaveLength(0)
    expect(w.text()).not.toContain('CS-2026-0001')
  })

  it('(c) rỗng thật ⇒ ui-empty có câu hướng dẫn tiếng Việt, 0 nút «Thử lại»', async () => {
    listCalibrationSchedulesSpy.mockResolvedValue(ok([]))
    const w = await mountView()
    expect(state(w)).toBe('empty')
    expect(w.find('[data-testid="ui-empty-title"]').text()).toBe('Chưa có lịch hiệu chuẩn nào')
    expect(w.find('[data-testid="ui-empty-description"]').text())
      .toBe('Hãy tạo lịch hiệu chuẩn mới hoặc xoá bộ lọc để xem tất cả.')
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
    listCalibrationSchedulesSpy.mockRejectedValueOnce(new Error('Mất kết nối.'))
    const w = await mountView()
    expect(state(w)).toBe('error')
    expect(listCalibrationSchedulesSpy).toHaveBeenCalledTimes(1)
    await retryControls(w)[0].trigger('click')
    await flushPromises()
    expect(listCalibrationSchedulesSpy).toHaveBeenCalledTimes(2)
    expect(state(w)).toBe('content')
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(false)
  })

  it('(f) loại trừ cấu trúc: đúng 1 shell, đúng 1 trạng thái; bộ lọc còn sống', async () => {
    listCalibrationSchedulesSpy.mockRejectedValue(new Error('X'))
    const w = await mountView()
    expect(w.findAll('[data-testid="list-page-shell"]')).toHaveLength(1)
    const present = ['list-loading', 'ui-error', 'ui-empty', 'list-content']
      .filter((t) => w.find(`[data-testid="${t}"]`).exists())
    expect(present).toEqual(['ui-error'])
    expect(w.find('[data-testid="list-filters"]').exists()).toBe(true)
    expect(w.findComponent(ListFilterBar).exists()).toBe(true)
  })
})
