// AC-CR-83 / FE-1 — `fields` (lỗi field-level) phải sống sót QUA CẢ HAI đường về:
//
//   (a) in-envelope Decision-B: HTTP-200 + `{message:{success:false, …, fields}}`
//       → `helpers.ts::hydrateApiError` (đã có sẵn).
//   (b) status-line 417/422: hook backstop `nthrow_in_hook` ghi message_code vào
//       `frappe.local.response` → axios interceptor. Nhánh này TRƯỚC ĐÂY LÀM RƠI
//       `fields` ⇒ form mất khả năng trỏ đúng ô khi lỗi đi qua hook DocType.
//
// FE chỉ ĐỌC khoá đã có trong hợp đồng — không sinh contract mới.
import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('@/utils/navigation', () => ({
  loginPath: (p?: string) => `/login?next=${p ?? ''}`,
  isOnLoginPage: () => false,
}))

import api from './axios'
import { frappePost } from './helpers'
import { ApiError, ErrorCode } from './errors'
import { MSG, MESSAGES } from '@/i18n/messages'

const SUBMIT_RCA = '/api/method/assetcore.api.imm12.submit_rca'
const VI_WHY_3 = 'Bước Why 3 chưa có câu trả lời — vui lòng điền trước khi hoàn tất.'

function okAdapter(message: unknown) {
  return () => Promise.resolve({
    data: { message }, status: 200, statusText: 'OK', headers: {}, config: {} as never,
  })
}

function statusAdapter(status: number, data: Record<string, unknown>) {
  return () => Promise.reject({ config: {}, response: { status, data, headers: {}, config: {} } })
}

async function catchApiError(run: () => Promise<unknown>): Promise<ApiError> {
  try {
    await run()
  } catch (e) {
    return e as ApiError
  }
  throw new Error('Kỳ vọng ApiError nhưng lời gọi lại thành công')
}

describe('submit_rca — envelope Decision-B (HTTP-200) mang fields tới FE', () => {
  beforeEach(() => { api.defaults.adapter = undefined })

  it('success=false + fields → ApiError.fields giữ nguyên khoá bước 5-Why', async () => {
    api.defaults.adapter = okAdapter({
      success: false,
      error: 'Hồ sơ 5-Why chưa đầy đủ.',
      code: 'BUSINESS_RULE',
      http_status: 422,
      message_code: MSG.IMM12_RCA_FIVE_WHY_INCOMPLETE,
      fields: { 'five_why_steps.3': VI_WHY_3 },
    })
    const err = await catchApiError(() => frappePost(SUBMIT_RCA, { name: 'RCA-2026-0001' }))
    expect(err).toBeInstanceOf(ApiError)
    expect(err.code).toBe(ErrorCode.BUSINESS_RULE)
    expect(err.httpStatus).toBe(422)
    expect(err.messageCode).toBe(MSG.IMM12_RCA_FIVE_WHY_INCOMPLETE)
    expect(err.fields).toEqual({ 'five_why_steps.3': VI_WHY_3 })
  })
})

describe('submit_rca — hook backstop 417/422 (status-line) KHÔNG được đánh rơi fields', () => {
  beforeEach(() => { api.defaults.adapter = undefined })

  it.each([417, 422])('HTTP %i kèm fields → ApiError.fields có mặt', async (status) => {
    api.defaults.adapter = statusAdapter(status, {
      message: 'Hồ sơ 5-Why chưa đầy đủ.',
      message_code: MSG.IMM12_RCA_FIVE_WHY_INCOMPLETE,
      fields: { 'five_why_steps.3': VI_WHY_3 },
    })
    const err = await catchApiError(() => api.post(SUBMIT_RCA, {}))
    expect(err.code).toBe(ErrorCode.BUSINESS_RULE)
    expect(err.fields).toEqual({ 'five_why_steps.3': VI_WHY_3 })
  })

  // Nhánh KHÁC của makeBusinessRuleError: message_code CÓ trong registry `MESSAGES`
  // (đã generate từ BE) → ApiError dựng từ entry. Nhánh này cũng phải giữ `fields`,
  // nếu không 2 mã RCA cũ (root-cause/corrective) sẽ mất khả năng trỏ ô.
  it('417 với message_code CÓ trong registry vẫn giữ fields (nhánh hydrate entry)', async () => {
    api.defaults.adapter = statusAdapter(417, {
      message: 'Cần nhập nguyên nhân gốc rễ.',
      message_code: MSG.IMM12_RCA_ROOT_CAUSE_REQUIRED,
      fields: { root_cause: 'Cần nhập nguyên nhân gốc rễ.' },
    })
    const err = await catchApiError(() => api.post(SUBMIT_RCA, {}))
    expect(err.messageCode).toBe(MSG.IMM12_RCA_ROOT_CAUSE_REQUIRED)
    // message render từ registry VI (không phải chuỗi thô của Frappe)
    expect(err.message).toContain('nguyên nhân gốc rễ')
    expect(err.fields).toEqual({ root_cause: 'Cần nhập nguyên nhân gốc rễ.' })
  })

  it('417 KHÔNG kèm fields → fields undefined (không bịa object rỗng)', async () => {
    api.defaults.adapter = statusAdapter(417, { message: 'Không hợp lệ.' })
    const err = await catchApiError(() => api.post(SUBMIT_RCA, {}))
    expect(err.fields).toBeUndefined()
  })

  it('fields rỗng {} → coi như KHÔNG có (form không vào nhánh field-level)', async () => {
    api.defaults.adapter = statusAdapter(422, { message: 'Không hợp lệ.', fields: {} })
    const err = await catchApiError(() => api.post(SUBMIT_RCA, {}))
    expect(err.fields).toBeUndefined()
  })
})

// FE-4 — `i18n/messages.ts` là file GENERATED từ `assetcore/utils/messages.py`.
// Guard chống QUÊN regen: 5 mã lỗi hồ sơ RCA phải có mặt + có câu tiếng Việt.
describe('parity registry — 5 mã lỗi RCA đã regen sang FE', () => {
  const RCA_CODES = [
    MSG.IMM12_RCA_FIVE_WHY_INCOMPLETE,
    MSG.IMM12_RCA_ASSIGNEE_REQUIRED,
    MSG.IMM12_RCA_ROOT_CAUSE_REQUIRED,
    MSG.IMM12_RCA_CORRECTIVE_REQUIRED,
    MSG.IMM12_RCA_ALREADY_COMPLETED,
  ]

  it.each(RCA_CODES)('%s có entry VI trong MESSAGES', (code) => {
    const entry = MESSAGES[code]
    expect(entry).toBeDefined()
    expect(entry.template.trim().length).toBeGreaterThan(0)
    expect(entry.title.trim().length).toBeGreaterThan(0)
    // Không lộ mã kỹ thuật ra câu hiển thị.
    expect(entry.template).not.toContain('IMM12-RCA')
  })
})
