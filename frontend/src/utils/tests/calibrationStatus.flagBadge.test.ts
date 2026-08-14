// Badge hạn hiệu chuẩn TỪ CỜ SERVER is_overdue/is_due_soon — server-flag SSoT (CR-02).
//
// Chứng minh consumer FE (CalibrationListView + CalibrationDetailView) CHỈ render cờ
// derive từ BE (list_calibrations / get_calibration qua CHUNG helper
// is_calibration_overdue / is_calibration_due_soon), KHÔNG so next_calibration_date với
// client-clock (memory: overdue_server_flag_ssot). Mirror BE parity list==detail +
// None-guard (test_imm11: test_calibration_overdue_parity_list_vs_detail /
// test_get_calibration_not_due None-case).
import { describe, it, expect, vi, afterEach } from 'vitest'
import { calFlagBadge } from '@/utils/calibrationStatus'

describe('calFlagBadge — badge hạn TỪ CỜ SERVER (không client-clock)', () => {
  afterEach(() => vi.useRealTimers())

  it("is_overdue=1 → badge 'Quá hạn' (đỏ), kind 'overdue'", () => {
    const b = calFlagBadge(1, 0)
    expect(b?.kind).toBe('overdue')
    expect(b?.label).toBe('Quá hạn')
    expect(b?.badgeClass).toMatch(/red/)
    expect(b?.textClass).toMatch(/red/)
  })

  it("is_due_soon=1 → badge 'Sắp đến hạn' (cam/vàng), kind 'due_soon'", () => {
    const b = calFlagBadge(0, 1)
    expect(b?.kind).toBe('due_soon')
    expect(b?.label).toBe('Sắp đến hạn')
    expect(b?.badgeClass).toMatch(/yellow|amber/)
  })

  it('cả hai cờ 0 (không tới hạn) → null (không badge)', () => {
    expect(calFlagBadge(0, 0)).toBeNull()
  })

  it('None-guard: undefined/null (chưa có hạn) → null (khớp None-guard BE)', () => {
    expect(calFlagBadge(undefined, undefined)).toBeNull()
    expect(calFlagBadge(null, null)).toBeNull()
  })

  it('overdue ưu tiên due_soon khi cả hai =1 (khớp biên BE)', () => {
    expect(calFlagBadge(1, 1)?.kind).toBe('overdue')
  })

  it("coerce Number(x)===1 — chống string '1' (envelope integer enum[0,1])", () => {
    expect(calFlagBadge('1' as unknown as number, 0)?.kind).toBe('overdue')
    expect(calFlagBadge(0, '1' as unknown as number)?.kind).toBe('due_soon')
    // giá trị lạ (2, '' , 'yes') KHÔNG match → null (chỉ nhận đúng cờ 1)
    expect(calFlagBadge(2 as unknown as number, 0)).toBeNull()
  })

  it("KHÔNG leak tiếng Anh ('Overdue'/'Due Soon') ra nhãn hiển thị", () => {
    expect(calFlagBadge(1, 0)?.label).not.toMatch(/Overdue|Due Soon/)
    expect(calFlagBadge(0, 1)?.label).not.toMatch(/Overdue|Due Soon/)
  })

  it('server-flag SSoT: kết quả BẤT BIẾN theo client-clock (không phụ thuộc Date)', () => {
    // Giả lập client-clock lệch xa: cờ server vẫn quyết định badge (không so ngày FE).
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2099-01-01T00:00:00Z'))
    expect(calFlagBadge(1, 0)?.kind).toBe('overdue')
    vi.setSystemTime(new Date('1990-01-01T00:00:00Z'))
    expect(calFlagBadge(1, 0)?.kind).toBe('overdue')
  })
})
