// Copyright (c) 2026, AssetCore Team — axios interceptor 429 mapping (IMM-00 B, TDD)
//
// RED-prove (task B — rotate hardening + resolve/scan Vòng 12): khi BE @rate_limit
// trip → HTTP 429 với message TIẾNG ANH của Frappe ("You hit the rate limit because
// of too many requests..."). Interceptor PHẢI:
//   • map code → ErrorCode.RATE_LIMITED (KHÔNG UNKNOWN)
//   • thay message bằng VI verbatim 'Bạn thao tác quá nhanh...' (0 EN-leak)
//   • KHÔNG leak raw status/code ("429" / "RATE_LIMITED") ra message hiển thị.
import { describe, it, expect, vi } from 'vitest'

// navigation utils chạm window.location → stub để import axios không nổ trong jsdom.
vi.mock('@/utils/navigation', () => ({
  loginPath: (p?: string) => `/login?next=${p ?? ''}`,
  isOnLoginPage: () => false,
}))

import api from './axios'
import { ApiError, ErrorCode } from './errors'

// Custom adapter: ép api trả 429 với body Frappe-style (message EN) để chạy QUA
// response interceptor THẬT (không stub interceptor).
function rateLimitAdapter() {
  return () =>
    Promise.reject({
      config: {},
      response: {
        status: 429,
        data: {
          message: 'You hit the rate limit because of too many requests. Please try after sometime.',
        },
        headers: {},
        config: {},
      },
    })
}

describe('axios interceptor — 429 rate limit', () => {
  it('429 → ApiError code RATE_LIMITED + message VI, 0 EN-leak/raw-code', async () => {
    api.defaults.adapter = rateLimitAdapter()
    await expect(api.post('/api/method/assetcore.api.imm00.regenerate_asset_qr_token', { asset: 'X' }))
      .rejects.toMatchObject({ code: ErrorCode.RATE_LIMITED, httpStatus: 429 })

    let caught: ApiError | null = null
    try {
      await api.post('/api/method/assetcore.api.imm00.regenerate_asset_qr_token', { asset: 'X' })
    } catch (e) {
      caught = e as ApiError
    }
    expect(caught).toBeInstanceOf(ApiError)
    expect(caught!.code).toBe(ErrorCode.RATE_LIMITED)
    expect(caught!.httpStatus).toBe(429)
    // Message VI verbatim — KHÔNG leak EN từ Frappe, KHÔNG raw status/code.
    expect(caught!.message).toContain('thao tác quá nhanh')
    expect(/rate limit|too many requests/i.test(caught!.message)).toBe(false)
    expect(caught!.message).not.toContain('429')
    expect(caught!.message).not.toContain('RATE_LIMITED')
  })
})
