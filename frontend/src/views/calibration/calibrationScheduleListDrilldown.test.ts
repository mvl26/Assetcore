// TDD — IMM-11 server-side filter/search/overdue drill + pagination.
// Cùng lớp lỗi /audit-trail: trước fix view lọc CLIENT-SIDE trên 1 trang 50 →
// divergence total vs rows + miss rows >50. Sau fix: filters gửi xuống BE,
// pagination control truy cập trang >1. Mô phỏng frontend/src/views/pm/
// pmListDrilldown.test.ts (PMWorkOrder).
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'

const routeQuery = ref<Record<string, string>>({})
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useRoute: () => ({ get query() { return routeQuery.value } }),
}))

// listCalibrationSchedules là điểm round-trip server. Spy để assert filters/page.
const listSpy = vi.fn().mockResolvedValue({
  data: [],
  pagination: { page: 1, page_size: 20, total: 0, total_pages: 0 },
})
vi.mock('@/api/imm11', () => ({
  listCalibrationSchedules: (...a: unknown[]) => listSpy(...a),
  createCalibrationSchedule: vi.fn(),
  updateCalibrationSchedule: vi.fn(),
  deleteCalibrationSchedule: vi.fn(),
}))

// Store chỉ dùng cho _captureError/notify — stub mỏng.
vi.mock('@/stores/imm11', () => ({
  useImm11Store: () => ({ _captureError: vi.fn(), lastApiError: null }),
}))
vi.mock('@/composables/useNotify', () => ({
  useNotify: () => ({ show: vi.fn(), fromError: vi.fn() }),
}))
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ error: vi.fn(), success: vi.fn() }),
}))

const stubs = {
  PageHeader: true, FilterToggleButton: true, ListFilterBar: true,
  BasePagination: true, SkeletonLoader: true, SmartSelect: true, DateInput: true,
}

import CalibrationScheduleListView from './CalibrationScheduleListView.vue'

// Last filters arg passed to the API (server round-trip payload).
function lastFilters(): Record<string, unknown> {
  const call = listSpy.mock.calls[listSpy.mock.calls.length - 1]
  return call?.[0] as Record<string, unknown>
}
function lastPage(): number {
  const call = listSpy.mock.calls[listSpy.mock.calls.length - 1]
  return call?.[1] as number
}

describe('CalibrationScheduleListView — drill-down query (server-side)', () => {
  beforeEach(() => { listSpy.mockClear(); routeQuery.value = {} })

  it('query.overdue=1 → listCalibrationSchedules gọi với filters.overdue=1 (KHÔNG lọc client-side)', async () => {
    routeQuery.value = { overdue: '1' }
    mount(CalibrationScheduleListView, { global: { stubs } })
    await flushPromises()
    expect(listSpy).toHaveBeenCalled()
    expect(lastFilters().overdue).toBe(1)
  })

  it('query.due_soon=1 → filters.due_soon=1 (card calib_due 2-biên, KHÔNG due_before)', async () => {
    routeQuery.value = { due_soon: '1' }
    mount(CalibrationScheduleListView, { global: { stubs } })
    await flushPromises()
    const f = lastFilters()
    expect(f.due_soon).toBe(1)
    // due-soon là param riêng — KHÔNG fallback về due_before cutoff-tập-bao.
    expect(f.due_before).toBeUndefined()
    expect(f.overdue).toBeUndefined()
  })

  it('query.due_before=X → filters.due_before=X (virtual key server-side)', async () => {
    routeQuery.value = { due_before: '2026-06-09' }
    mount(CalibrationScheduleListView, { global: { stubs } })
    await flushPromises()
    expect(lastFilters().due_before).toBe('2026-06-09')
  })

  it('không có query → filters KHÔNG kèm overdue/due_soon/due_before', async () => {
    routeQuery.value = {}
    mount(CalibrationScheduleListView, { global: { stubs } })
    await flushPromises()
    const f = lastFilters()
    expect(f.overdue).toBeUndefined()
    expect(f.due_soon).toBeUndefined()
    expect(f.due_before).toBeUndefined()
  })
})

describe('CalibrationScheduleListView — filters round-trip server', () => {
  beforeEach(() => { listSpy.mockClear(); routeQuery.value = {} })

  it('đổi calibration_type → reload server với filters.calibration_type + page reset=1', async () => {
    const w = mount(CalibrationScheduleListView, { global: { stubs } })
    await flushPromises()
    // filters là ref expose qua setup — test-utils unwrap trên vm.
    ;(w.vm as any).filters.calibration_type = 'External'
    await flushPromises()
    expect(lastFilters().calibration_type).toBe('External')
    expect(lastPage()).toBe(1)
  })

  it('đổi is_active → reload server với filters.is_active (số)', async () => {
    const w = mount(CalibrationScheduleListView, { global: { stubs } })
    await flushPromises()
    ;(w.vm as any).filters.is_active = '1'
    await flushPromises()
    expect(lastFilters().is_active).toBe(1)
  })

  it('gõ search rồi load(1) → gọi BE với filters.search + page=1', async () => {
    const w = mount(CalibrationScheduleListView, { global: { stubs } })
    await flushPromises()
    ;(w.vm as any).filters.search = 'ZZNEEDLE'
    await (w.vm as any).load(1)
    await flushPromises()
    expect(lastFilters().search).toBe('ZZNEEDLE')
    expect(lastPage()).toBe(1)
  })
})

describe('CalibrationScheduleListView — pagination next/prev', () => {
  beforeEach(() => { listSpy.mockClear(); routeQuery.value = {} })

  it('load(2) gọi BE với page=2 (truy cập rows >page_size)', async () => {
    listSpy.mockResolvedValue({
      data: [], pagination: { page: 1, page_size: 20, total: 55, total_pages: 3 },
    })
    const w = mount(CalibrationScheduleListView, { global: { stubs } })
    await flushPromises()
    await (w.vm as any).load(2)
    await flushPromises()
    expect(lastPage()).toBe(2)
  })

  it('paginationMeta.total_pages tính từ pagination.total BE trả về', async () => {
    listSpy.mockResolvedValue({
      data: [], pagination: { page: 1, page_size: 20, total: 55, total_pages: 3 },
    })
    const w = mount(CalibrationScheduleListView, { global: { stubs } })
    await flushPromises()
    expect((w.vm as any).paginationMeta.total_pages).toBe(3)
    expect((w.vm as any).paginationMeta.total).toBe(55)
  })
})
