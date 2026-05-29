// Copyright (c) 2026, AssetCore Team
// Sprint Notification vòng 5 — store IMM-04 (commissioning) phải capture
// lastApiError (hydrated) trên path lỗi, và KHÔNG set trên path thành công.

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { ApiError, ErrorCode } from '@/api/errors'

vi.mock('@/api/imm04', () => ({
  getFormContext: vi.fn(),
  listCommissioning: vi.fn(),
  transitionState: vi.fn(),
  submitCommissioning: vi.fn(),
  saveCommissioning: vi.fn(),
  createCommissioning: vi.fn(),
  checkSnUnique: vi.fn(),
  reportNonConformance: vi.fn(),
  assignIdentification: vi.fn(),
  generateInternalQr: vi.fn(),
  submitBaselineChecklist: vi.fn(),
  clearClinicalHold: vi.fn(),
  approveClinicalRelease: vi.fn(),
  getDashboardStats: vi.fn(),
  closeNonConformance: vi.fn(),
  deleteCommissioning: vi.fn(),
  cancelCommissioning: vi.fn(),
  getPoDetails: vi.fn(),
}))

vi.mock('@/api/helpers', () => ({
  frappeGet: vi.fn(),
  frappePost: vi.fn(),
}))

import * as api from '@/api/imm04'
import { useCommissioningStore } from '@/stores/imm04'

const DUP_SERIAL = new ApiError("VR-01: Serial 'SN-1' đã được gán cho Tài Sản AC-1.", {
  code: ErrorCode.BUSINESS_RULE,
  httpStatus: 422,
  messageCode: 'IMM04-DUP-SERIAL',
  severity: 'warning',
  title: 'Trùng số serial',
  actionHint: 'Kiểm tra lại serial hoặc tra cứu bản ghi hiện hữu trước khi tiếp tục.',
})

const CANCEL_ASSET_ACTIVE = new ApiError("Không thể hủy vì Tài sản 'AC-1' đã được kích hoạt.", {
  code: ErrorCode.CONFLICT,
  httpStatus: 409,
  messageCode: 'IMM04-CANCEL-ASSET-ACTIVE',
  severity: 'warning',
  title: 'Không thể hủy nghiệm thu',
})

describe('imm04 store — notification contract', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('fetchList lỗi giữ lastApiError đã hydrate (message_code/severity/title)', async () => {
    vi.mocked(api.listCommissioning).mockRejectedValueOnce(DUP_SERIAL)
    const store = useCommissioningStore()
    await store.fetchList({})
    expect(store.lastApiError).not.toBeNull()
    expect(store.lastApiError?.messageCode).toBe('IMM04-DUP-SERIAL')
    expect(store.lastApiError?.severity).toBe('warning')
    expect(store.lastApiError?.title).toBe('Trùng số serial')
    expect(store.error).toBe(DUP_SERIAL.message)
  })

  it('cancelDoc lỗi → lastApiError set + trả false', async () => {
    vi.mocked(api.cancelCommissioning).mockRejectedValueOnce(CANCEL_ASSET_ACTIVE)
    const store = useCommissioningStore()
    const ok = await store.cancelDoc('AC-COMM-1')
    expect(ok).toBe(false)
    expect(store.lastApiError?.messageCode).toBe('IMM04-CANCEL-ASSET-ACTIVE')
    expect(store.lastApiError?.severity).toBe('warning')
  })

  it('submitDoc thành công → KHÔNG set lastApiError', async () => {
    vi.mocked(api.submitCommissioning).mockResolvedValueOnce(
      { name: 'AC-COMM-1' } as unknown as Awaited<ReturnType<typeof api.submitCommissioning>>,
    )
    vi.mocked(api.getFormContext).mockResolvedValueOnce(
      { name: 'AC-COMM-1', docstatus: 1 } as unknown as Awaited<ReturnType<typeof api.getFormContext>>,
    )
    const store = useCommissioningStore()
    const ok = await store.submitDoc('AC-COMM-1')
    expect(ok).toBe(true)
    expect(store.lastApiError).toBeNull()
  })

  it('clearError reset cả lastApiError', async () => {
    vi.mocked(api.cancelCommissioning).mockRejectedValueOnce(CANCEL_ASSET_ACTIVE)
    const store = useCommissioningStore()
    await store.cancelDoc('AC-COMM-1')
    expect(store.lastApiError).not.toBeNull()
    store.clearError()
    expect(store.lastApiError).toBeNull()
    expect(store.error).toBeNull()
  })
})
