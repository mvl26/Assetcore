// Copyright (c) 2026, AssetCore Team
// TDD (FE regression guard) — IMM-06: chi tiết Chương trình / Buổi đào tạo khi mã
// bản ghi không tồn tại (404). Cùng họ lỗi CalibrationDetailView (CAL-2026-04591).
//
// Trước: store nuốt lỗi thành chuỗi ⇒ view chỉ hiện banner đỏ + nút "Thử lại" —
// với mã sai/đã xoá thì retry vô nghĩa và KHÔNG có lối về danh sách (dead-end).
// Nay: phân loại 404 ⇒ empty-state chuẩn (DetailLoadError) nêu mã + nút về danh sách.
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { setRouteParams, resetRouteMock, routerPushSpy } from '@/test/vueRouterMock'
import { ApiError, ErrorCode } from '@/api/errors'

vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn(), info: vi.fn(), warning: vi.fn() }),
}))
vi.mock('@/composables/useNotify', () => ({
  useNotify: () => ({ show: vi.fn(), fromError: vi.fn(), fromOk: vi.fn(), confirm: vi.fn() }),
}))

const getProgram = vi.fn()
const getSession = vi.fn()
vi.mock('@/api/imm06', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/imm06')>()
  return { ...actual, getProgram: () => getProgram(), getSession: () => getSession() }
})

import ProgramDetailView from './ProgramDetailView.vue'
import SessionDetailView from './SessionDetailView.vue'

const stubs = { PageHeader: true, StatusBadge: true, BaseModal: true, SkeletonLoader: true, DateInput: true, ApproverSelect: true, SmartSelect: true }

function notFound(msg: string): ApiError {
  return new ApiError(msg, { code: ErrorCode.NOT_FOUND, httpStatus: 404 })
}

describe('IMM-06 *DetailView — bản ghi không tồn tại (404)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    resetRouteMock()
    vi.clearAllMocks()
    getProgram.mockRejectedValue(notFound('Không tìm thấy chương trình: TP-2026-99999.'))
    getSession.mockRejectedValue(notFound('Không tìm thấy buổi đào tạo: TS-2026-99999.'))
  })
  afterEach(() => resetRouteMock())

  it('ProgramDetailView → empty-state nêu mã + về danh sách chương trình', async () => {
    setRouteParams({ name: 'TP-2026-99999' })
    const wrapper = mount(ProgramDetailView, {
      props: { name: 'TP-2026-99999' },
      global: { stubs },
    })
    await flushPromises()
    expect(wrapper.text()).toContain('Không tìm thấy chương trình đào tạo')
    expect(wrapper.text()).toContain('TP-2026-99999')

    const back = wrapper.findAll('button').find(b => /danh sách/i.test(b.text()))!
    await back.trigger('click')
    expect(routerPushSpy()).toHaveBeenCalledWith('/imm06/programs')
  })

  it('SessionDetailView → empty-state nêu mã + về danh sách buổi đào tạo', async () => {
    setRouteParams({ name: 'TS-2026-99999' })
    const wrapper = mount(SessionDetailView, {
      props: { name: 'TS-2026-99999' },
      global: { stubs },
    })
    await flushPromises()
    expect(wrapper.text()).toContain('Không tìm thấy buổi đào tạo')
    expect(wrapper.text()).toContain('TS-2026-99999')

    const back = wrapper.findAll('button').find(b => /danh sách/i.test(b.text()))!
    await back.trigger('click')
    expect(routerPushSpy()).toHaveBeenCalledWith('/imm06/sessions')
  })
})
