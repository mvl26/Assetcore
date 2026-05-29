// Copyright (c) 2026, AssetCore Team
// Sprint Notification vòng 3 — store IMM-08 phải capture lastApiError (hydrated)
// trên path lỗi, và KHÔNG set trên path thành công.

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { ApiError, ErrorCode } from '@/api/errors'

vi.mock('@/api/imm08', () => ({
  listPMWorkOrders: vi.fn(),
  getPMWorkOrder: vi.fn(),
  assignTechnician: vi.fn(),
  submitPMResult: vi.fn(),
  reportMajorFailure: vi.fn(),
  getPMCalendar: vi.fn(),
  getPMDashboardStats: vi.fn(),
  reschedulePM: vi.fn(),
  getAssetPMHistory: vi.fn(),
}))

import * as api from '@/api/imm08'
import { useImm08Store } from '@/stores/imm08'

const WO_NOT_FOUND = new ApiError('Không tìm thấy lệnh bảo trì định kỳ: PM-X.', {
  code: ErrorCode.NOT_FOUND,
  httpStatus: 404,
  messageCode: 'IMM08-WO-NOT-FOUND',
  severity: 'warning',
  title: 'Không tìm thấy lệnh PM',
  actionHint: 'Kiểm tra lại mã lệnh PM trong danh sách.',
})

describe('imm08 store — notification contract', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('lỗi action giữ lastApiError đã hydrate (message_code/severity/title)', async () => {
    vi.mocked(api.getPMWorkOrder).mockRejectedValueOnce(WO_NOT_FOUND)
    const store = useImm08Store()
    await store.fetchWorkOrder('PM-X')
    expect(store.lastApiError).not.toBeNull()
    expect(store.lastApiError?.messageCode).toBe('IMM08-WO-NOT-FOUND')
    expect(store.lastApiError?.severity).toBe('warning')
    expect(store.lastApiError?.title).toBe('Không tìm thấy lệnh PM')
    expect(store.error).toBe(WO_NOT_FOUND.message)
  })

  it('doReschedule lỗi → lastApiError set + trả false', async () => {
    vi.mocked(api.reschedulePM).mockRejectedValueOnce(WO_NOT_FOUND)
    const store = useImm08Store()
    const ok = await store.doReschedule('PM-X', '2026-06-01', 'lý do hợp lệ')
    expect(ok).toBe(false)
    expect(store.lastApiError?.messageCode).toBe('IMM08-WO-NOT-FOUND')
  })

  it('path thành công KHÔNG set lastApiError', async () => {
    vi.mocked(api.listPMWorkOrders).mockResolvedValueOnce({
      data: [],
      pagination: { page: 1, page_size: 20, total: 0, total_pages: 0 },
    })
    const store = useImm08Store()
    await store.fetchWorkOrders({}, 1)
    expect(store.lastApiError).toBeNull()
    expect(store.error).toBeNull()
  })
})
