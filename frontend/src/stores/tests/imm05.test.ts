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

// ─────────────────────────────────────────────────────────────────────────────
// CR-75 — hồ sơ pháp lý theo thiết bị: store phải phơi ĐỦ khoá máy-đọc để view
// không phải so chuỗi `document_status` (nguồn của dead-branch `Expiring_Soon`).
// ─────────────────────────────────────────────────────────────────────────────

type Dossier = Awaited<ReturnType<typeof api.getAssetDocuments>>

const DOSSIER_NON_COMPLIANT = {
  asset: 'AC-ASSET-2026-0001',
  required_total: 4,
  required_satisfied: 2,
  completeness_pct: 50,
  document_status: 'Non-Compliant',
  is_compliant: 0,
  missing_required: ['Hợp đồng bảo trì'],
  expired_required: ['Chứng nhận đăng ký lưu hành'],
  expiring_required: [],
  hidden_count: 1,
  documents: {
    Legal: [
      {
        name: 'DOC-1', doc_category: 'Legal', doc_type_detail: 'Chứng nhận đăng ký lưu hành',
        workflow_state: 'Active', expiry_date: '2026-06-30', days_until_expiry: -26, is_expired: 1,
      },
    ],
  },
} as unknown as Dossier

/** Hợp đồng CŨ (BE chưa deploy CR-75): thiếu toàn bộ khoá mới. */
const DOSSIER_LEGACY = {
  asset: 'AC-ASSET-2026-0002',
  completeness_pct: 0,
  document_status: 'Complete',
  missing_required: [],
  documents: {},
} as unknown as Dossier

describe('imm05 store — fetchAssetDocuments (CR-75)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('phơi is_compliant / expired_required / mẫu số / hidden_count', async () => {
    vi.mocked(api.getAssetDocuments).mockResolvedValueOnce(DOSSIER_NON_COMPLIANT)
    const store = useImm05Store()
    await store.fetchAssetDocuments('AC-ASSET-2026-0001')

    expect(store.assetIsCompliant).toBe(0)
    expect(store.assetExpiredRequired).toEqual(['Chứng nhận đăng ký lưu hành'])
    expect(store.missingRequired).toEqual(['Hợp đồng bảo trì'])
    expect(store.assetRequiredTotal).toBe(4)
    expect(store.assetRequiredSatisfied).toBe(2)
    expect(store.assetCompletenessPct).toBe(50)
    expect(store.assetHiddenCount).toBe(1)
    // Hai tập RỜI NHAU: quá hạn KHÔNG được lẫn vào "thiếu"
    expect(store.missingRequired).not.toContain('Chứng nhận đăng ký lưu hành')
  })

  it('BE chưa deploy CR-75 ⇒ is_compliant = null (CHƯA BIẾT, KHÔNG phải 0)', async () => {
    vi.mocked(api.getAssetDocuments).mockResolvedValueOnce(DOSSIER_LEGACY)
    const store = useImm05Store()
    await store.fetchAssetDocuments('AC-ASSET-2026-0002')

    expect(store.assetIsCompliant).toBeNull()
    expect(store.assetRequiredTotal).toBeNull()
    expect(store.assetExpiredRequired).toEqual([])
    expect(store.assetHiddenCount).toBe(0)
  })

  it('đổi thiết bị: khoá CR-75 KHÔNG giữ giá trị của thiết bị trước (chống stale)', async () => {
    vi.mocked(api.getAssetDocuments)
      .mockResolvedValueOnce(DOSSIER_NON_COMPLIANT)
      .mockResolvedValueOnce(DOSSIER_LEGACY)
    const store = useImm05Store()
    await store.fetchAssetDocuments('AC-ASSET-2026-0001')
    await store.fetchAssetDocuments('AC-ASSET-2026-0002')

    expect(store.assetIsCompliant).toBeNull()
    expect(store.assetExpiredRequired).toEqual([])
    expect(store.assetRequiredSatisfied).toBeNull()
  })

  // ── AC-CR-81 ───────────────────────────────────────────────────────────────
  it('AC-CR-81: 5 khoá tệp đi thẳng từ payload vào store, KHÔNG bị store nắn', async () => {
    vi.mocked(api.getAssetDocuments).mockResolvedValueOnce({
      ...DOSSIER_NON_COMPLIANT,
      documents: {
        Legal: [
          {
            name: 'DOC-1', doc_category: 'Legal', doc_type_detail: 'Giấy phép nhập khẩu',
            workflow_state: 'Active', expiry_date: '2027-01-01', days_until_expiry: 180, is_expired: 0,
            file_url: '/private/files/a.pdf', file_name: 'a.pdf', file_size: 2048,
            is_private: 1, has_file: 1,
          },
          {
            name: 'DOC-2', doc_category: 'Legal', doc_type_detail: 'Hợp đồng bảo trì',
            workflow_state: 'Active', expiry_date: null, days_until_expiry: null, is_expired: 0,
            file_url: '', file_name: '', file_size: 0, is_private: 0, has_file: 0,
          },
        ],
      },
    } as unknown as Dossier)
    const store = useImm05Store()
    await store.fetchAssetDocuments('AC-ASSET-2026-0001')

    const [withFile, without] = store.assetDocuments.Legal
    expect(withFile.has_file).toBe(1)
    expect(withFile.file_url).toBe('/private/files/a.pdf')
    expect(withFile.file_name).toBe('a.pdf')
    expect(withFile.file_size).toBe(2048)
    expect(withFile.is_private).toBe(1)
    // Dòng không có tệp: 5 khoá VẪN hiện diện (assert `in`, không chỉ falsy)
    for (const k of ['file_url', 'file_name', 'file_size', 'is_private', 'has_file']) {
      expect(k in without).toBe(true)
    }
    expect(without.has_file).toBe(0)
    expect(without.file_url).toBe('')
  })

  it('AC-CR-81: đổi thiết bị mà payload thiếu `documents` ⇒ danh sách hồ sơ RESET (không rò tệp thiết bị cũ)', async () => {
    vi.mocked(api.getAssetDocuments)
      .mockResolvedValueOnce(DOSSIER_NON_COMPLIANT)
      .mockResolvedValueOnce({ asset: 'AC-ASSET-2026-0002', completeness_pct: 0, document_status: 'Incomplete', missing_required: [] } as unknown as Dossier)
    const store = useImm05Store()
    await store.fetchAssetDocuments('AC-ASSET-2026-0001')
    expect(Object.keys(store.assetDocuments)).toHaveLength(1)

    await store.fetchAssetDocuments('AC-ASSET-2026-0002')
    expect(store.assetDocuments).toEqual({})
  })
})
