// Copyright (c) 2026, AssetCore Team — httpStatusToCode mapping (IMM-00 B-hardening, TDD)
//
// RED-prove (task B — rotate endpoint hardening): httpStatusToCode(429) PHẢI trả
// ErrorCode.RATE_LIMITED. Hiện THIẾU `case 429` → 429 fallthrough → UNKNOWN, làm
// mis-bucket MỌI 429 (kể cả resolve/scan đã throttle từ Vòng 12). Khi đóng bất đối
// xứng read-throttled/write-unthrottled (regenerate_asset_qr_token + @rate_limit),
// FE cần map 429 sang bucket đúng để render thông báo VI 'thao tác quá nhanh'.
import { describe, it, expect } from 'vitest'
import { httpStatusToCode, ErrorCode } from './errors'

describe('httpStatusToCode — rate-limit (429)', () => {
  it('429 → RATE_LIMITED (KHÔNG fallthrough UNKNOWN)', () => {
    expect(httpStatusToCode(429)).toBe(ErrorCode.RATE_LIMITED)
  })

  it('429 KHÔNG còn rơi về UNKNOWN', () => {
    expect(httpStatusToCode(429)).not.toBe(ErrorCode.UNKNOWN)
  })

  // Regression — các mapping cũ KHÔNG đổi hành vi.
  it('giữ nguyên các mapping precedent', () => {
    expect(httpStatusToCode(400)).toBe(ErrorCode.VALIDATION_ERROR)
    expect(httpStatusToCode(401)).toBe(ErrorCode.UNAUTHORIZED)
    expect(httpStatusToCode(403)).toBe(ErrorCode.FORBIDDEN)
    expect(httpStatusToCode(404)).toBe(ErrorCode.NOT_FOUND)
    expect(httpStatusToCode(409)).toBe(ErrorCode.CONFLICT)
    expect(httpStatusToCode(413)).toBe(ErrorCode.PAYLOAD_TOO_LARGE)
    expect(httpStatusToCode(422)).toBe(ErrorCode.BUSINESS_RULE)
    expect(httpStatusToCode(500)).toBe(ErrorCode.INTERNAL_ERROR)
    expect(httpStatusToCode(418)).toBe(ErrorCode.UNKNOWN) // chưa map → UNKNOWN
  })
})
