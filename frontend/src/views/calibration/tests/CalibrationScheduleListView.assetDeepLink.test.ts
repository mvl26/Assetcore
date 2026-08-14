// TC-CONNFE6-5/6 (AC-CR-94) — deep-link «Xem tất cả» ĐẾN ĐÍCH cho màn Lịch hiệu chuẩn.
//
// Màn này ĐÃ đọc `overdue|due_soon|due_before` nhưng KHÔNG đọc `asset` ⇒ ô «Lịch hiệu
// chuẩn» của một thiết bị báo N mà nút «Xem tất cả» dẫn tới lịch của cả viện. Ba điều
// được khoá ở đây:
//   (a) `filters` gửi lên CÓ khoá `asset` (server-side, không lọc client trên trang cắt);
//   (b) dòng `is_active = 0` VẪN hiện — nếu view tự thêm `is_active: 1` thì count ô
//       (không lọc trạng thái) ≠ số dòng drill;
//   (c) `asset` GIAO (AND) với ưu tiên overdue > due_soon > due_before — không nhánh nào
//       clobber nhánh kia (bug kinh điển: nhét asset vào cùng nhánh else-if ⇒ mất một
//       trong hai điều kiện tuỳ thứ tự).
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'

const routeQuery = ref<Record<string, string>>({})
const replaceSpy = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn(), replace: (...a: unknown[]) => replaceSpy(...a) }),
  useRoute: () => ({ get query() { return routeQuery.value } }),
}))

const ASSET = 'AC-ASSET-X'
// 2 lịch CÙNG thiết bị: 1 đang hoạt động + 1 tạm dừng ⇒ chứng minh view KHÔNG tự lọc is_active.
const ROWS = [
  {
    name: 'CAL-SCH-2026-00001', asset: ASSET, asset_name: 'Máy xét nghiệm sinh hoá',
    calibration_type: 'External', interval_days: 365, next_due_date: '2026-11-30', is_active: 1,
  },
  {
    name: 'CAL-SCH-2026-00002', asset: ASSET, asset_name: 'Máy xét nghiệm sinh hoá',
    calibration_type: 'In-House', interval_days: 180, next_due_date: '2027-02-28', is_active: 0,
  },
]

const listSpy = vi.fn().mockResolvedValue({
  data: ROWS, pagination: { page: 1, page_size: 20, total: ROWS.length, total_pages: 1 },
})
vi.mock('@/api/imm11', () => ({
  listCalibrationSchedules: (...a: unknown[]) => listSpy(...a),
  createCalibrationSchedule: vi.fn(),
  updateCalibrationSchedule: vi.fn(),
  deleteCalibrationSchedule: vi.fn(),
}))
vi.mock('@/stores/imm11', () => ({
  useImm11Store: () => ({ _captureError: vi.fn(), lastApiError: null, error: null }),
}))
vi.mock('@/composables/useNotify', () => ({
  useNotify: () => ({ show: vi.fn(), fromError: vi.fn() }),
}))
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ error: vi.fn(), success: vi.fn() }),
}))

// ListFilterBar để THẬT — chip là DOM cần assert.
const stubs = {
  PageHeader: true, FilterToggleButton: true, BasePagination: true,
  SkeletonLoader: true, SmartSelect: true, DateInput: true, BaseModal: true,
}

import CalibrationScheduleListView from '@/views/calibration/CalibrationScheduleListView.vue'

function lastFilters(): Record<string, unknown> {
  const call = listSpy.mock.calls[listSpy.mock.calls.length - 1]
  return (call?.[0] ?? {}) as Record<string, unknown>
}

describe('CalibrationScheduleListView — deep-link ?asset= (TC-CONNFE6-5)', () => {
  beforeEach(() => {
    listSpy.mockClear()
    replaceSpy.mockClear()
    listSpy.mockResolvedValue({
      data: ROWS, pagination: { page: 1, page_size: 20, total: ROWS.length, total_pages: 1 },
    })
    routeQuery.value = {}
  })

  it('(a) filters gửi lên CÓ khoá asset (server-side)', async () => {
    routeQuery.value = { asset: ASSET }
    mount(CalibrationScheduleListView, { global: { stubs } })
    await flushPromises()

    expect(listSpy).toHaveBeenCalled()
    expect(lastFilters().asset).toBe(ASSET)
  })

  it('(b) render đủ 2 dòng — gồm dòng is_active=0 (view KHÔNG tự thêm is_active)', async () => {
    routeQuery.value = { asset: ASSET }
    const w = mount(CalibrationScheduleListView, { global: { stubs } })
    await flushPromises()

    expect(lastFilters().is_active, 'view tự lọc is_active ⇒ count ô ≠ số dòng drill').toBeUndefined()
    const rows = w.findAll('tbody tr')
    expect(rows.length).toBe(2)
    expect(w.text()).toContain('Tạm dừng')
    for (const r of rows) expect(r.text()).toContain('Máy xét nghiệm sinh hoá')
  })

  it('(c) chip tiếng Việt «Thiết bị: …» hiện ra', async () => {
    routeQuery.value = { asset: ASSET }
    const w = mount(CalibrationScheduleListView, { global: { stubs } })
    await flushPromises()

    const chip = w.findAll('button').map((b) => b.text()).find((t) => t.includes('Thiết bị'))
    expect(chip).toBeTruthy()
    expect(chip).toContain('Máy xét nghiệm sinh hoá')
    expect(chip?.toLowerCase()).not.toMatch(/\basset\b/)
  })

  it('không có query.asset ⇒ filters KHÔNG kèm asset', async () => {
    routeQuery.value = {}
    mount(CalibrationScheduleListView, { global: { stubs } })
    await flushPromises()
    expect(lastFilters().asset).toBeUndefined()
  })

  it('bỏ chip «Thiết bị» ⇒ router.replace xoá query.asset + fetch kế KHÔNG còn asset', async () => {
    routeQuery.value = { asset: ASSET, overdue: '1' }
    const w = mount(CalibrationScheduleListView, { global: { stubs } })
    await flushPromises()
    expect(lastFilters().asset).toBe(ASSET)

    const chipBtn = w.findAll('button').find((b) => b.text().includes('Thiết bị'))
    expect(chipBtn).toBeTruthy()
    await chipBtn!.trigger('click')
    await flushPromises()

    expect(replaceSpy).toHaveBeenCalled()
    const arg = replaceSpy.mock.calls[replaceSpy.mock.calls.length - 1][0] as { query: Record<string, string> }
    expect(arg.query.asset).toBeUndefined()
    expect(arg.query.overdue, 'bỏ chip thiết bị KHÔNG được dọn luôn drill quá hạn').toBe('1')
    expect(lastFilters().asset, '0 lọc ẩn còn treo sau khi user bỏ chip').toBeUndefined()
    expect(lastFilters().overdue, 'ưu tiên overdue phải giữ nguyên').toBe(1)
  })
})

describe('CalibrationScheduleListView — asset GIAO ưu tiên hiện có (TC-CONNFE6-6)', () => {
  beforeEach(() => {
    listSpy.mockClear()
    listSpy.mockResolvedValue({
      data: ROWS, pagination: { page: 1, page_size: 20, total: ROWS.length, total_pages: 1 },
    })
    routeQuery.value = {}
  })

  it('?asset + ?overdue=1 ⇒ filters có CẢ HAI (không nhánh nào clobber)', async () => {
    routeQuery.value = { asset: ASSET, overdue: '1' }
    mount(CalibrationScheduleListView, { global: { stubs } })
    await flushPromises()

    const f = lastFilters()
    expect(f.asset).toBe(ASSET)
    expect(f.overdue).toBe(1)
  })

  it('?asset + ?due_soon=1 ⇒ filters có CẢ HAI, KHÔNG kèm overdue/due_before', async () => {
    routeQuery.value = { asset: ASSET, due_soon: '1' }
    mount(CalibrationScheduleListView, { global: { stubs } })
    await flushPromises()

    const f = lastFilters()
    expect(f.asset).toBe(ASSET)
    expect(f.due_soon).toBe(1)
    expect(f.overdue).toBeUndefined()
    expect(f.due_before).toBeUndefined()
  })

  it('?asset + ?due_before=X ⇒ filters có CẢ HAI', async () => {
    routeQuery.value = { asset: ASSET, due_before: '2026-12-31' }
    mount(CalibrationScheduleListView, { global: { stubs } })
    await flushPromises()

    const f = lastFilters()
    expect(f.asset).toBe(ASSET)
    expect(f.due_before).toBe('2026-12-31')
  })

  it('đổi loại hiệu chuẩn khi đang deep-link ⇒ asset KHÔNG bị rơi', async () => {
    routeQuery.value = { asset: ASSET }
    const w = mount(CalibrationScheduleListView, { global: { stubs } })
    await flushPromises()
    ;(w.vm as unknown as { filters: { calibration_type: string } }).filters.calibration_type = 'External'
    await flushPromises()

    const f = lastFilters()
    expect(f.calibration_type).toBe('External')
    expect(f.asset).toBe(ASSET)
  })
})
