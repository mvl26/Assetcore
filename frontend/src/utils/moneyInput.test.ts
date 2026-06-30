// TDD — money input grouping (Vietnamese thousand separator) for CurrencyInput.
// formatThousands/parseThousands are the pure SSoT used by useThousandsInput.
// Separator = '.' (kiểu Việt Nam: 1.000.000) — khớp formatCurrency (display).
import { describe, it, expect } from 'vitest'
import { formatThousands, parseThousands } from './formatters'

describe('formatThousands — nhóm hàng nghìn kiểu Việt Nam (dấu chấm)', () => {
  it('nhóm 3 chữ số bằng dấu chấm', () => {
    expect(formatThousands(1000000)).toBe('1.000.000')
    expect(formatThousands(1234567)).toBe('1.234.567')
    expect(formatThousands(1000)).toBe('1.000')
    expect(formatThousands(999)).toBe('999')
  })

  it('giá trị lớn > 2 tỷ vẫn nhóm đúng (không tràn/không cắt)', () => {
    expect(formatThousands(2_000_000_000)).toBe('2.000.000.000')
    expect(formatThousands(80_000_000_000)).toBe('80.000.000.000')
  })

  it('0 → "0"; null/undefined/"" → "" (ô trống)', () => {
    expect(formatThousands(0)).toBe('0')
    expect(formatThousands(null)).toBe('')
    expect(formatThousands(undefined)).toBe('')
    expect(formatThousands('')).toBe('')
  })

  it('nhận chuỗi đã có nhóm / có ký hiệu → chuẩn hoá lại', () => {
    expect(formatThousands('1.234.567')).toBe('1.234.567')
    expect(formatThousands('1234567 ₫')).toBe('1.234.567')
  })
})

describe('parseThousands — chuỗi nhóm → number sạch', () => {
  it('bỏ dấu phân nhóm, trả number nguyên', () => {
    expect(parseThousands('1.234.567')).toBe(1234567)
    expect(parseThousands('1234567')).toBe(1234567)
    expect(parseThousands('2.000.000.000')).toBe(2000000000)
  })

  it('bỏ ký hiệu tiền tệ / khoảng trắng', () => {
    expect(parseThousands('1.234.567 ₫')).toBe(1234567)
    expect(parseThousands(' 5.000 ')).toBe(5000)
  })

  it('rỗng / không có chữ số / null → null', () => {
    expect(parseThousands('')).toBeNull()
    expect(parseThousands('   ')).toBeNull()
    expect(parseThousands('abc')).toBeNull()
    expect(parseThousands(null)).toBeNull()
    expect(parseThousands(undefined)).toBeNull()
  })

  it('số 0 → 0 (KHÔNG null — phân biệt "đã nhập 0" với "để trống")', () => {
    expect(parseThousands('0')).toBe(0)
  })

  it('round-trip: parse(format(n)) === n', () => {
    for (const n of [0, 999, 1000, 1234567, 2_000_000_000, 80_000_000_000]) {
      expect(parseThousands(formatThousands(n))).toBe(n)
    }
  })
})
