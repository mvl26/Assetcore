// TC-CAL-FAIL-DUE (FE) — BR-11-08 / NĐ98.
// Sau khi IMM Asset Calibration FAIL, BE đặt IMM Calibration Schedule.next_due_date
// về NGÀY HIỆN TẠI (due-now, <= today). FE PHẢI render hàng/badge thiết bị FAIL ở
// trạng thái 'Quá hạn'/'Đến hạn' (đỏ/cam) — KHÔNG 'Đúng lịch' (xanh), KHÔNG leak EN
// ('Overdue'/'Failed'). Derive THUẦN từ next_due_date (SoT), date-only.
//
// RED-prove TRƯỚC fix: code cũ tô màu bằng `new Date(date) < new Date()` (strict-LT,
// kèm giờ) → next_due_date == today (FAIL due-now) KHÔNG được tô đỏ/cam + KHÔNG có
// nhãn trạng thái VI → có thể hiện như "đúng lịch". Test này khoá hành vi đúng.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'
import {
  deriveCalStatus, isCalDueNow, todayIsoDate, CAL_DUE_SOON_WINDOW_DAYS,
} from '@/utils/calibrationStatus'

// ── Pure SoT derivation ──────────────────────────────────────────────────────
describe('deriveCalStatus — derive thuần từ next_due_date (SoT, date-only)', () => {
  const NOW = new Date('2026-06-04T08:30:00') // local now với giờ → bẫy timezone
  const today = todayIsoDate(NOW) // '2026-06-04'

  it('FAIL due-now: next_due_date == today → due_soon (cam), KHÔNG on_schedule', () => {
    const s = deriveCalStatus(today, NOW)
    expect(s.kind).toBe('due_soon')
    expect(s.label).toBe('Đến hạn')
    expect(s.kind).not.toBe('on_schedule')
    expect(isCalDueNow(today, NOW)).toBe(true)
  })

  it('next_due_date < today (quá hạn) → overdue (đỏ)', () => {
    const s = deriveCalStatus('2026-05-01', NOW)
    expect(s.kind).toBe('overdue')
    expect(s.label).toBe('Quá hạn')
    expect(s.badgeClass).toContain('red')
    expect(isCalDueNow('2026-05-01', NOW)).toBe(true)
  })

  it('next_due_date trong cửa sổ 30 ngày → due_soon (cam)', () => {
    const s = deriveCalStatus('2026-06-20', NOW)
    expect(s.kind).toBe('due_soon')
    expect(s.badgeClass).toContain('orange')
  })

  it('next_due_date > today+30 → on_schedule (xanh)', () => {
    const s = deriveCalStatus('2026-09-01', NOW)
    expect(s.kind).toBe('on_schedule')
    expect(s.label).toBe('Đúng lịch')
    expect(s.badgeClass).toContain('green')
    expect(isCalDueNow('2026-09-01', NOW)).toBe(false)
  })

  it('null/không hợp lệ → unscheduled (xám), không crash', () => {
    expect(deriveCalStatus(null, NOW).kind).toBe('unscheduled')
    expect(deriveCalStatus(undefined, NOW).kind).toBe('unscheduled')
    expect(deriveCalStatus('', NOW).kind).toBe('unscheduled')
  })

  it('datetime ISO có giờ vẫn so theo NGÀY (cắt 10 ký tự)', () => {
    // next_due_date == today nhưng kèm 00:00:00 — vẫn due_soon, KHÔNG on_schedule.
    expect(deriveCalStatus(`${today} 00:00:00`, NOW).kind).toBe('due_soon')
  })

  it('window khớp BE CAL_DUE_SOON_WINDOW_DAYS = 30', () => {
    expect(CAL_DUE_SOON_WINDOW_DAYS).toBe(30)
  })

  it('KHÔNG leak nhãn tiếng Anh', () => {
    for (const d of ['2026-05-01', today, '2026-06-20', '2026-09-01', null]) {
      const lbl = deriveCalStatus(d, NOW).label
      expect(lbl).not.toMatch(/Overdue|Due|Failed|On Schedule|Scheduled/i)
    }
  })
})

// ── CalibrationScheduleListView render (FAIL due-now row) ─────────────────────
const routeQuery = ref<Record<string, string>>({})
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useRoute: () => ({ get query() { return routeQuery.value } }),
}))

// FAIL asset: schedule active với next_due_date == today (due-now sau BE FAIL handler).
const TODAY = todayIsoDate()
const listSpy = vi.fn().mockResolvedValue({
  data: [
    {
      name: 'CAL-SCH-FAIL-01', asset: 'ACC-ASS-FAIL-01',
      asset_name: 'Máy thở FAIL', calibration_type: 'External',
      interval_days: 180, next_due_date: TODAY, is_active: 1,
    },
  ],
  pagination: { page: 1, page_size: 20, total: 1, total_pages: 1 },
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

const stubs = {
  PageHeader: true, FilterToggleButton: true, ListFilterBar: true,
  BasePagination: true, SkeletonLoader: true, SmartSelect: true, DateInput: true,
  BaseModal: true,
}

import CalibrationScheduleListView from '@/views/calibration/CalibrationScheduleListView.vue'

describe('CalibrationScheduleListView — hàng FAIL due-now (next_due_date == today)', () => {
  beforeEach(() => { listSpy.mockClear(); routeQuery.value = {} })

  it('render badge trạng thái VI quá-hạn/đến-hạn — KHÔNG "Đúng lịch", KHÔNG leak EN', async () => {
    const w = mount(CalibrationScheduleListView, { global: { stubs } })
    await flushPromises()
    const html = w.html()
    // due-now phải hiện 'Đến hạn' (hoặc 'Quá hạn' nếu lệch ngày) — KHÔNG 'Đúng lịch'.
    expect(html).toMatch(/Đến hạn|Quá hạn/)
    expect(html).not.toContain('Đúng lịch')
    // KHÔNG leak nhãn EN của trạng thái hiệu chuẩn.
    expect(html).not.toMatch(/\bOverdue\b|\bDue Soon\b|\bFailed\b|\bOn Schedule\b/)
  })

  it('cell ngày đến hạn của hàng FAIL tô màu cảnh báo (đỏ/cam) qua badgeClass derive', async () => {
    const w = mount(CalibrationScheduleListView, { global: { stubs } })
    await flushPromises()
    const html = w.html()
    // Badge trạng thái lịch của due-now: bg cảnh báo (đỏ overdue / cam due_soon),
    // KHÔNG bg-green (on_schedule). Scope theo badge class derive, không bắt nhầm
    // 'text-red-600' của nút Xóa.
    expect(html).toMatch(/bg-red-100 text-red-700|bg-orange-100 text-orange-700/)
    expect(html).not.toContain('bg-green-100 text-green-700">\n                    Đúng lịch')
  })
})
