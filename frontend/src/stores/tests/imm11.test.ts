// Copyright (c) 2026, AssetCore Team
// Sprint Notification vòng 4 — store IMM-11 phải capture lastApiError (hydrated)
// trên path lỗi, và KHÔNG set trên path thành công.

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { ApiError, ErrorCode } from '@/api/errors'

vi.mock('@/api/imm11', () => ({
  listCalibrations: vi.fn(),
  listCalibrationSchedules: vi.fn(),
  getCalibrationKpis: vi.fn(),
  getDueCalibrations: vi.fn(),
  createCalibration: vi.fn(),
  submitCalibration: vi.fn(),
  cancelCalibration: vi.fn(),
  sendToLab: vi.fn(),
  receiveCertificate: vi.fn(),
}))

import * as api from '@/api/imm11'
import { useImm11Store } from '@/stores/imm11'

const CANCEL_REASON_REQUIRED = new ApiError('Bắt buộc nhập lý do khi huỷ phiếu hiệu chuẩn.', {
  code: ErrorCode.BUSINESS_RULE,
  httpStatus: 422,
  messageCode: 'IMM11-CANCEL-REASON-REQUIRED',
  severity: 'warning',
  title: 'Thiếu lý do huỷ',
  actionHint: 'Nhập lý do huỷ rồi thử lại.',
})

const CAL_NOT_FOUND = new ApiError('Không tìm thấy phiếu hiệu chuẩn: CAL-X.', {
  code: ErrorCode.NOT_FOUND,
  httpStatus: 404,
  messageCode: 'IMM11-CAL-NOT-FOUND',
  severity: 'warning',
  title: 'Không tìm thấy phiếu hiệu chuẩn',
  actionHint: 'Kiểm tra lại mã phiếu trong danh sách hiệu chuẩn.',
})

describe('imm11 store — notification contract', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('fetchList lỗi giữ lastApiError đã hydrate (message_code/severity/title)', async () => {
    vi.mocked(api.listCalibrations).mockRejectedValueOnce(CAL_NOT_FOUND)
    const store = useImm11Store()
    await store.fetchList({})
    expect(store.lastApiError).not.toBeNull()
    expect(store.lastApiError?.messageCode).toBe('IMM11-CAL-NOT-FOUND')
    expect(store.lastApiError?.severity).toBe('warning')
    expect(store.lastApiError?.title).toBe('Không tìm thấy phiếu hiệu chuẩn')
    expect(store.error).toBe(CAL_NOT_FOUND.message)
  })

  it('doCancel lỗi → lastApiError set + trả null', async () => {
    vi.mocked(api.cancelCalibration).mockRejectedValueOnce(CANCEL_REASON_REQUIRED)
    const store = useImm11Store()
    const res = await store.doCancel('CAL-X', '')
    expect(res).toBeNull()
    expect(store.lastApiError?.messageCode).toBe('IMM11-CANCEL-REASON-REQUIRED')
  })

  it('doSubmit thành công → trả data + KHÔNG set lastApiError', async () => {
    vi.mocked(api.submitCalibration).mockResolvedValueOnce({
      name: 'CAL-1', status: 'Passed', overall_result: 'Passed', next_calibration_date: '2027-05-29',
    } as unknown as Awaited<ReturnType<typeof api.submitCalibration>>)
    const store = useImm11Store()
    const res = await store.doSubmit('CAL-1')
    expect(res).not.toBeNull()
    expect(store.lastApiError).toBeNull()
  })
})
