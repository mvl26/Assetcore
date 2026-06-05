// Copyright (c) 2026, AssetCore Team — IMM-16 ∩ IMM-00
// RED-prove FE: api/imm00.closeCapaRecord (path LEGACY) PHẢI surface cổng hiệu quả
// VR-06/VR-07 của BE (ServiceError FIN-007 ↦ envelope { success:false, code:'VALIDATION' }).
//
// AC-6: khi BE từ chối đóng vì chưa 'Effective' → closeCapaRecord KHÔNG nuốt lỗi thành
// 'thành công'; nó throw ApiError mang message VI BE trả (caller hiển thị qua
// notification-contract). Không leak code thô/EN. Happy path ('Effective') trả {name,status}.
//
// Test ở tầng API client vì path legacy hiện CHƯA có view caller (UX đóng CAPA chính đi
// qua imm16.advance_capa_state đã gate). Đây là cổng chống false-claim của transport.

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ApiError, ErrorCode } from '@/api/errors'

// frappePost = unwrap(message): success===false → throw hydrateApiError. Mock ở tầng
// helpers để mô phỏng envelope BE thật mà KHÔNG cần axios.
const postSpy = vi.fn()
vi.mock('@/api/helpers', () => ({
  frappeGet: vi.fn(),
  frappePost: (endpoint: string, body?: Record<string, unknown>) => postSpy(endpoint, body),
}))

import { closeCapaRecord } from '@/api/imm00'

// Mô phỏng đúng hành vi helpers.unwrap: success===false → ném ApiError(code, message VI).
function rejectFin007(message: string) {
  return new ApiError(message, { code: ErrorCode.VALIDATION, httpStatus: 422 })
}

const VR06_MSG = 'VR-06: bắt buộc xác minh hiệu quả trước khi đóng CAPA'
const VR07_MSG = "VR-07: xác minh hiệu quả phải = 'Hiệu quả' mới được đóng CAPA"

const PAYLOAD = {
  root_cause: 'Hỏng cảm biến',
  corrective_action: 'Thay cảm biến',
  preventive_action: 'PM định kỳ',
}

describe('closeCapaRecord — cổng hiệu quả VR-06/VR-07 (AC-6, no false-claim)', () => {
  beforeEach(() => { postSpy.mockReset() })

  it('TC-CAPA-FE-01 effectiveness_check thiếu → throw ApiError VR-06, KHÔNG resolve "đã đóng"', async () => {
    postSpy.mockRejectedValue(rejectFin007(VR06_MSG))
    const call = closeCapaRecord('CAPA-2026-00001', { ...PAYLOAD })
    await expect(call).rejects.toBeInstanceOf(ApiError)
    await call.catch((e: ApiError) => {
      // Message VI BE trả — surface để view hiển thị; KHÔNG nuốt thành success.
      expect(e.message).toContain('xác minh hiệu quả')
      expect(e.isBusinessError).toBe(true) // VALIDATION → yellow toast, không phải success
      // KHÔNG leak code thô FIN-007 / token EN ra message hiển thị.
      expect(e.message).not.toMatch(/FIN-007|Effective|Not Effective|Closed/)
    })
  })

  it("TC-CAPA-FE-02 effectiveness_check='Not Effective' → throw ApiError VR-07", async () => {
    postSpy.mockRejectedValue(rejectFin007(VR07_MSG))
    await expect(
      closeCapaRecord('CAPA-2026-00001', { ...PAYLOAD, effectiveness_check: 'Not Effective' }),
    ).rejects.toMatchObject({ code: ErrorCode.VALIDATION })
  })

  it("TC-CAPA-FE-02b effectiveness_check='Partially Effective' → throw ApiError VR-07", async () => {
    postSpy.mockRejectedValue(rejectFin007(VR07_MSG))
    await expect(
      closeCapaRecord('CAPA-2026-00001', { ...PAYLOAD, effectiveness_check: 'Partially Effective' }),
    ).rejects.toBeInstanceOf(ApiError)
  })

  it("TC-CAPA-FE-03 happy path effectiveness_check='Effective' → resolve { name, status:'Closed' }", async () => {
    postSpy.mockResolvedValue({ name: 'CAPA-2026-00001', status: 'Closed' })
    const res = await closeCapaRecord('CAPA-2026-00001', { ...PAYLOAD, effectiveness_check: 'Effective' })
    expect(res).toEqual({ name: 'CAPA-2026-00001', status: 'Closed' })
    // Endpoint + payload KHỚP signature BE (close_capa_record(name, ...data)).
    expect(postSpy).toHaveBeenCalledWith(
      '/api/method/assetcore.api.imm00.close_capa_record',
      expect.objectContaining({
        name: 'CAPA-2026-00001',
        root_cause: 'Hỏng cảm biến',
        effectiveness_check: 'Effective',
      }),
    )
  })
})
