// Copyright (c) 2026, AssetCore Team
// Sprint Notification vòng 5 — store IMM-05 (document repository) phải capture
// lastApiError (hydrated) trên path lỗi, và KHÔNG set trên path thành công.

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { ApiError, ErrorCode } from '@/api/errors'

vi.mock('@/api/imm05', () => ({
  listDocuments: vi.fn(),
  getAssetDocuments: vi.fn(),
  getDashboardStats: vi.fn(),
  approveDocument: vi.fn(),
  rejectDocument: vi.fn(),
  createDocumentRequest: vi.fn(),
  getDocumentRequests: vi.fn(),
  getExpiringDocuments: vi.fn(),
  getDocument: vi.fn(),
  updateDocument: vi.fn(),
  createDocument: vi.fn(),
  getDocumentHistory: vi.fn(),
}))

import * as api from '@/api/imm05'
import { useImm05Store } from '@/stores/imm05'

const FORBIDDEN_APPROVE = new ApiError('Bạn không có quyền duyệt/từ chối tài liệu này.', {
  code: ErrorCode.FORBIDDEN,
  httpStatus: 403,
  messageCode: 'IMM05-FORBIDDEN-APPROVE',
  severity: 'error',
  title: 'Không đủ quyền duyệt',
  actionHint: 'Liên hệ Tổ HC-QLCL để được cấp quyền duyệt hồ sơ.',
})

const DOC_NOT_FOUND = new ApiError('Không tìm thấy tài liệu: DOC-X.', {
  code: ErrorCode.NOT_FOUND,
  httpStatus: 404,
  messageCode: 'IMM05-DOC-NOT-FOUND',
  severity: 'warning',
  title: 'Không tìm thấy tài liệu',
})

describe('imm05 store — notification contract', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('fetchDocuments lỗi giữ lastApiError đã hydrate', async () => {
    vi.mocked(api.listDocuments).mockRejectedValueOnce(DOC_NOT_FOUND)
    const store = useImm05Store()
    await store.fetchDocuments({})
    expect(store.lastApiError).not.toBeNull()
    expect(store.lastApiError?.messageCode).toBe('IMM05-DOC-NOT-FOUND')
    expect(store.lastApiError?.severity).toBe('warning')
    expect(store.error).toBe(DOC_NOT_FOUND.message)
  })

  it('approveDocument lỗi forbidden → lastApiError set (severity error) + trả false', async () => {
    vi.mocked(api.approveDocument).mockRejectedValueOnce(FORBIDDEN_APPROVE)
    const store = useImm05Store()
    const ok = await store.approveDocument('DOC-1')
    expect(ok).toBe(false)
    expect(store.lastApiError?.messageCode).toBe('IMM05-FORBIDDEN-APPROVE')
    expect(store.lastApiError?.severity).toBe('error')
  })

  it('rejectDocument thành công → KHÔNG set lastApiError', async () => {
    vi.mocked(api.rejectDocument).mockResolvedValueOnce(
      { name: 'DOC-1', new_state: 'Rejected' } as unknown as Awaited<ReturnType<typeof api.rejectDocument>>,
    )
    const store = useImm05Store()
    const ok = await store.rejectDocument('DOC-1', 'Sai mẫu')
    expect(ok).toBe(true)
    expect(store.lastApiError).toBeNull()
  })

  it('clearError reset cả lastApiError', async () => {
    vi.mocked(api.approveDocument).mockRejectedValueOnce(FORBIDDEN_APPROVE)
    const store = useImm05Store()
    await store.approveDocument('DOC-1')
    expect(store.lastApiError).not.toBeNull()
    store.clearError()
    expect(store.lastApiError).toBeNull()
    expect(store.error).toBeNull()
  })
})
