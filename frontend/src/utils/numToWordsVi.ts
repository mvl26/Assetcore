// Copyright (c) 2026, AssetCore Team
// Đọc số tiền VND thành chữ tiếng Việt — bản FE mirror chính xác BE
// `assetcore/services/shared/num_to_words_vi.py`. Dùng để preview trực tiếp
// trên form trước khi BE tính lại (BE vẫn là single source of truth khi lưu).

const DIGITS = ['không', 'một', 'hai', 'ba', 'bốn', 'năm', 'sáu', 'bảy', 'tám', 'chín']
const UNITS = ['', 'nghìn', 'triệu', 'tỷ']

/** Đọc một nhóm 3 chữ số (0..999). `full` = không phải nhóm cao nhất. */
function readThreeDigits(n: number, full: boolean): string {
  const hundred = Math.floor(n / 100)
  const rem = n % 100
  const ten = Math.floor(rem / 10)
  const unit = rem % 10
  const parts: string[] = []

  if (hundred > 0 || full) {
    parts.push(DIGITS[hundred], 'trăm')
  }

  if (ten === 0) {
    if (unit > 0 && (hundred > 0 || full)) parts.push('lẻ')
    if (unit > 0) parts.push(DIGITS[unit])
  } else if (ten === 1) {
    parts.push('mười')
    if (unit === 5) parts.push('lăm')
    else if (unit > 0) parts.push(DIGITS[unit])
  } else {
    parts.push(DIGITS[ten], 'mươi')
    if (unit === 1) parts.push('mốt')
    else if (unit === 5) parts.push('lăm')
    else if (unit > 0) parts.push(DIGITS[unit])
  }

  return parts.join(' ')
}

/**
 * Đọc số tiền VND thành chữ. Hỗ trợ đến hàng tỷ (giống BE).
 * Trả chuỗi rỗng nếu amount <= 0 hoặc không hợp lệ (BE lưu null tương ứng).
 */
export function numToWordsVi(amount: number | null | undefined): string {
  if (amount == null || !Number.isFinite(amount) || amount <= 0) return ''

  let number = Math.round(amount)
  const groups: number[] = []
  while (number > 0) {
    groups.push(number % 1000)
    number = Math.floor(number / 1000)
  }

  const segments: string[] = []
  const highest = groups.length - 1
  for (let idx = highest; idx >= 0; idx--) {
    const grp = groups[idx]
    if (grp === 0) continue
    const text = readThreeDigits(grp, idx !== highest)
    const unit = UNITS[idx] ?? ''
    segments.push(`${text} ${unit}`.trim())
  }

  const result = segments.join(' ').trim()
  return result.charAt(0).toUpperCase() + result.slice(1) + ' đồng'
}
