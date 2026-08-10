// Copyright (c) 2026, AssetCore Team
// normalizeFieldErrors — sống được với CẢ HAI dạng `fields` mà BE đang phát:
// dict {field: msg} (khuôn utils/response.py) và list ['field'] (op mới chỉ đánh dấu ô).
import { describe, it, expect } from 'vitest'
import { ApiError, ErrorCode } from '@/api/errors'
import { normalizeFieldErrors } from './fieldErrors'

describe('normalizeFieldErrors', () => {
  it('fields dạng LIST ⇒ mỗi ô nhận NGUYÊN VĂN message VI của server', () => {
    const err = new ApiError('Lý do dời lịch phải có ít nhất 5 ký tự.', {
      code: ErrorCode.VALIDATION_ERROR,
      fields: ['reason'] as unknown as Record<string, string>,
    })
    expect(normalizeFieldErrors(err)).toEqual({
      reason: 'Lý do dời lịch phải có ít nhất 5 ký tự.',
    })
  })

  it('fields dạng DICT ⇒ giữ message riêng của từng ô', () => {
    const err = new ApiError('Dữ liệu không hợp lệ.', {
      code: ErrorCode.VALIDATION_ERROR,
      fields: { new_date: 'Ngày mới không hợp lệ.', reason: 'Thiếu lý do.' },
    })
    expect(normalizeFieldErrors(err)).toEqual({
      new_date: 'Ngày mới không hợp lệ.',
      reason: 'Thiếu lý do.',
    })
  })

  it('DICT có value rỗng ⇒ fallback về message chung (không để ô lỗi câm)', () => {
    const err = new ApiError('Không thể dời lịch.', {
      code: ErrorCode.BAD_STATE,
      fields: { scheduled_date: '' },
    })
    expect(normalizeFieldErrors(err)).toEqual({ scheduled_date: 'Không thể dời lịch.' })
  })

  it('không có fields / err null ⇒ {} (lỗi hiển thị ở banner chung)', () => {
    expect(normalizeFieldErrors(new ApiError('X', { code: ErrorCode.BAD_STATE }))).toEqual({})
    expect(normalizeFieldErrors(null)).toEqual({})
    expect(normalizeFieldErrors(undefined)).toEqual({})
  })
})
