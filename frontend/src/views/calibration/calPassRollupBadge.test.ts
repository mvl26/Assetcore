// TC-FE-PASS-ROLLUP-01 — BR-11-13 / asset-cache ROLLUP đa-lịch (mirror PASS của
// calFailDueNow.test.ts).
//
// BUG CHÍNH: asset X có 2 active schedule — A (next_due_date quá khứ = OVERDUE) +
// B (vừa Pass). Sau handle_calibration_pass(B), BE rollup asset-cache:
//   AC Asset.calibration_status   = OVERDUE  (worst-of-all active schedules)
//   AC Asset.next_calibration_date = MIN(next_due_date) = A.next_due_date (quá khứ)
// FE PHẢI render badge thiết bị X ở 'Quá hạn'/'Đến hạn' (đỏ/cam) — KHÔNG ép 'Đúng
// lịch' (xanh) chỉ vì schedule B vừa Pass. Derive THUẦN từ next_calibration_date /
// next_due_date (SoT, date-only), TRANSPORT-AGNOSTIC: bất kể BE gửi field gì, badge
// bám ngày MIN-rollup → không tự rớt cảnh báo đỏ khi còn lịch quá hạn.
//
// RED-prove: nếu ai "fix" bằng cách bind badge='Đúng lịch' literal sau submit Pass
// (bỏ qua rollup date), assert `not.toContain('Đúng lịch')` + assert đỏ/cam → FAIL.
// Đây là gương đối xứng của BR-11-08 FAIL-path đã khoá ở calFailDueNow.test.ts.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'
import {
  deriveCalStatus, isCalDueNow, todayIsoDate,
} from '@/utils/calibrationStatus'

// ── Pure SoT derivation — rollup MIN(next_due_date) qua next_calibration_date ────
describe('deriveCalStatus — PASS rollup: badge bám next_calibration_date (MIN), KHÔNG ép Đúng lịch', () => {
  const NOW = new Date('2026-06-04T08:30:00') // local now với giờ → bẫy timezone
  const today = todayIsoDate(NOW) // '2026-06-04'

  it('asset 2-lịch (A overdue + B Pass): cache MIN = A.next_due_date (quá khứ) → overdue (đỏ)', () => {
    // BE rollup đặt next_calibration_date = MIN = A.next_due_date = today-10.
    const minRollup = '2026-05-25' // today-10, lịch A vẫn quá hạn
    const s = deriveCalStatus(minRollup, NOW)
    expect(s.kind).toBe('overdue')
    expect(s.label).toBe('Quá hạn')
    expect(s.badgeClass).toContain('red')
    expect(s.kind).not.toBe('on_schedule') // KHÔNG bị schedule B Pass ép xanh
    expect(isCalDueNow(minRollup, NOW)).toBe(true) // VẪN trong tập due-calibrations
  })

  it('RED-prove: KHÔNG hardcode "Đúng lịch" khi cache MIN còn quá hạn', () => {
    // Nếu code đẩy next_calibration_date về B.next_date (today+180) thay vì MIN(A),
    // badge sẽ on_schedule (xanh) = bug. Khoá: MIN còn quá khứ → KHÔNG xanh.
    const wrongIfHardcoded = deriveCalStatus('2026-12-01', NOW) // B.next_date (sai)
    const correctRollupMin = deriveCalStatus('2026-05-25', NOW) // MIN(A) (đúng)
    expect(wrongIfHardcoded.label).toBe('Đúng lịch') // chứng minh: nếu lấy B → xanh
    expect(correctRollupMin.label).not.toBe('Đúng lịch') // rollup đúng → KHÔNG xanh
    expect(correctRollupMin.label).toBe('Quá hạn')
  })

  it('DUE_SOON rollup: A (today+5) + B Pass → cache MIN = today+5 → due_soon (cam), KHÔNG on_schedule', () => {
    const s = deriveCalStatus('2026-06-09', NOW) // today+5
    expect(s.kind).toBe('due_soon')
    expect(s.label).toBe('Đến hạn')
    expect(s.badgeClass).toContain('orange')
    expect(s.kind).not.toBe('on_schedule')
  })

  it('HAPPY single-schedule bất biến: Pass 1 lịch → cache = basis+interval (tương lai) → on_schedule (xanh)', () => {
    // asset chỉ 1 active schedule, Pass → next_calibration_date = add_days(basis,interval).
    const s = deriveCalStatus('2026-12-01', NOW) // basis(today)+180 > today+30
    expect(s.kind).toBe('on_schedule')
    expect(s.label).toBe('Đúng lịch')
    expect(s.badgeClass).toContain('green')
    expect(isCalDueNow('2026-12-01', NOW)).toBe(false)
  })

  it('KHÔNG leak nhãn tiếng Anh ở mọi nhánh rollup', () => {
    for (const d of ['2026-05-25', today, '2026-06-09', '2026-12-01', null]) {
      const lbl = deriveCalStatus(d, NOW).label
      expect(lbl).not.toMatch(/Overdue|Due Soon|Failed|On Schedule|Scheduled/i)
    }
  })
})

// ── CalibrationScheduleListView render — schedule A (overdue) của asset vừa Pass(B) ─
const routeQuery = ref<Record<string, string>>({})
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useRoute: () => ({ get query() { return routeQuery.value } }),
}))

// Asset X sau Pass(B): schedule A active VẪN overdue (next_due_date = today-10).
const OVERDUE_PAST = '2026-05-25'
const listSpy = vi.fn().mockResolvedValue({
  data: [
    {
      name: 'CAL-SCH-A-PASS', asset: 'ACC-ASS-PASS-01',
      asset_name: 'Máy X-quang PASS', calibration_type: 'External',
      interval_days: 180, next_due_date: OVERDUE_PAST, is_active: 1,
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

import CalibrationScheduleListView from './CalibrationScheduleListView.vue'

describe('CalibrationScheduleListView — schedule A vẫn overdue sau khi asset Pass(B)', () => {
  beforeEach(() => { listSpy.mockClear(); routeQuery.value = {} })

  it('render badge VI quá-hạn — KHÔNG "Đúng lịch", KHÔNG leak EN (rollup không ép xanh)', async () => {
    const w = mount(CalibrationScheduleListView, { global: { stubs } })
    await flushPromises()
    const html = w.html()
    expect(html).toMatch(/Quá hạn/)
    expect(html).not.toContain('Đúng lịch')
    expect(html).not.toMatch(/\bOverdue\b|\bDue Soon\b|\bFailed\b|\bOn Schedule\b/)
  })

  it('cell ngày đến hạn tô màu cảnh báo (đỏ) qua badgeClass derive — KHÔNG bg-green on_schedule', async () => {
    const w = mount(CalibrationScheduleListView, { global: { stubs } })
    await flushPromises()
    const html = w.html()
    expect(html).toMatch(/bg-red-100 text-red-700/)
    expect(html).not.toContain('bg-green-100 text-green-700">\n                    Đúng lịch')
  })
})
