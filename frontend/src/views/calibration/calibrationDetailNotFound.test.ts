// Copyright (c) 2026, AssetCore Team
// TDD (FE regression guard) — IMM-11: màn chi tiết phiếu hiệu chuẩn KHÔNG được
// dead-end khi mã phiếu không tồn tại.
//
// Bug gốc (RED): `/calibration/CAL-2026-04591` (phiếu đã bị xoá / mã sai) →
// `load()` KHÔNG catch ⇒ ApiError 404 nổi lên console (unhandled rejection) và
// trang render KHUNG CHI TIẾT RỖNG (tiêu đề trống, mọi field '—', panel nhập kết
// quả vẫn hiện) — người dùng tưởng phiếu tồn tại nhưng "mất dữ liệu".
//
// Test khoá 3 bất biến:
//   1. load() nuốt lỗi 404 → KHÔNG unhandled rejection (mount không throw).
//   2. Render empty-state VI có mã phiếu + lối thoát về danh sách (không dead-end).
//   3. KHÔNG render thân chi tiết (khối 'Thông tin chung') khi phiếu không tồn tại.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const push = vi.fn()
vi.mock('vue-router', () => ({ useRouter: () => ({ push }) }))
vi.mock('@/composables/useNotify', () => ({
  useNotify: () => ({ show: vi.fn(), fromError: vi.fn() }),
}))
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ success: vi.fn(), warning: vi.fn(), error: vi.fn() }),
}))
vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({ can: () => true }),
}))
vi.mock('@/stores/imm11', () => ({
  useImm11Store: () => ({
    doSendToLab: vi.fn(), doReceiveCertificate: vi.fn(), doCancel: vi.fn(), doSubmit: vi.fn(),
    _captureError: vi.fn(), error: null, lastApiError: null,
  }),
}))
vi.mock('@/api/imm05', () => ({ uploadDocumentFile: vi.fn() }))
vi.mock('@/api/imm11', () => ({ getCalibration: vi.fn(), updateCalibration: vi.fn() }))

import { getCalibration } from '@/api/imm11'
import { ApiError, ErrorCode } from '@/api/errors'
import CalibrationDetailView from './CalibrationDetailView.vue'

const stubs = { DateInput: true, StatusBadge: true, WorkflowStepper: true }

describe('CalibrationDetailView — phiếu không tồn tại (404)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(getCalibration).mockRejectedValue(
      new ApiError('Không tìm thấy phiếu hiệu chuẩn: CAL-2026-04591.', {
        code: ErrorCode.NOT_FOUND,
        httpStatus: 404,
        messageCode: 'IMM11_CAL_NOT_FOUND',
      }),
    )
  })

  it('không văng unhandled rejection + render empty-state có mã phiếu và lối về danh sách', async () => {
    const wrapper = mount(CalibrationDetailView, {
      props: { id: 'CAL-2026-04591' },
      global: { stubs },
    })
    await flushPromises()

    const text = wrapper.text()
    expect(text).toContain('Không tìm thấy phiếu hiệu chuẩn')
    expect(text).toContain('CAL-2026-04591')

    // Lối thoát: nút quay về danh sách hiệu chuẩn (KHÔNG dead-end).
    const backBtns = wrapper.findAll('button').filter(b => /danh sách|Quay lại/i.test(b.text()))
    expect(backBtns.length).toBeGreaterThan(0)
    await backBtns[backBtns.length - 1].trigger('click')
    expect(push).toHaveBeenCalledWith('/calibration')
  })

  it('KHÔNG render thân chi tiết rỗng khi phiếu không tồn tại', async () => {
    const wrapper = mount(CalibrationDetailView, {
      props: { id: 'CAL-2026-04591' },
      global: { stubs },
    })
    await flushPromises()

    expect(wrapper.text()).not.toContain('Thông tin chung')
  })
})
