// Copyright (c) 2026, AssetCore Team
import { describe, it, expect } from 'vitest'
import {
  emailError,
  dateOrderError,
  notFutureError,
  nonNegativeError,
  firstError,
} from '@/utils/formValidation'

describe('emailError', () => {
  it('passes blank (optional field)', () => {
    expect(emailError('')).toBe('')
    expect(emailError(null)).toBe('')
    expect(emailError(undefined)).toBe('')
  })
  it('passes a valid address', () => {
    expect(emailError('sales@drager.com.vn')).toBe('')
  })
  it('rejects malformed addresses with a VI message + the bad value', () => {
    expect(emailError('not-an-email', 'Email liên hệ')).toContain('không hợp lệ')
    expect(emailError('not-an-email', 'Email liên hệ')).toContain('not-an-email')
    expect(emailError('a@b')).toContain('không hợp lệ')
    expect(emailError('a @b.com')).toContain('không hợp lệ')
  })
})

describe('dateOrderError', () => {
  const MSG = 'Ngày kết thúc phải >= ngày bắt đầu'
  it('passes when either side blank', () => {
    expect(dateOrderError('', '2026-01-01', MSG)).toBe('')
    expect(dateOrderError('2026-01-01', '', MSG)).toBe('')
  })
  it('passes equal / ascending', () => {
    expect(dateOrderError('2026-01-01', '2026-01-01', MSG)).toBe('')
    expect(dateOrderError('2026-01-01', '2026-02-01', MSG)).toBe('')
  })
  it('rejects reversed', () => {
    expect(dateOrderError('2026-02-01', '2026-01-01', MSG)).toBe(MSG)
  })
})

describe('notFutureError', () => {
  const MSG = 'Ngày mua không được ở tương lai'
  it('passes blank and past', () => {
    expect(notFutureError('', MSG)).toBe('')
    expect(notFutureError('2020-01-01', MSG)).toBe('')
  })
  it('rejects a clearly future date', () => {
    expect(notFutureError('2099-12-31', MSG)).toBe(MSG)
  })
})

describe('nonNegativeError', () => {
  const MSG = 'Giá mua không được âm'
  it('passes blank / zero / positive', () => {
    expect(nonNegativeError('', MSG)).toBe('')
    expect(nonNegativeError(0, MSG)).toBe('')
    expect(nonNegativeError(5_000_000, MSG)).toBe('')
  })
  it('rejects negative', () => {
    expect(nonNegativeError(-1, MSG)).toBe(MSG)
    expect(nonNegativeError('-100', MSG)).toBe(MSG)
  })
})

describe('firstError', () => {
  it('returns the first non-empty error', () => {
    expect(firstError('', '', 'boom', 'later')).toBe('boom')
  })
  it('returns empty when all pass', () => {
    expect(firstError('', '', '')).toBe('')
  })
})
