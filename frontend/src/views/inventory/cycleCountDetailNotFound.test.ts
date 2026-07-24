// Copyright (c) 2026, AssetCore Team
// TDD (FE regression guard) — IMM-15: chi tiết phiếu kiểm kê khi mã không tồn tại
// (404). Trước: chỉ banner đỏ + "Thử lại" (retry vô nghĩa với mã sai/đã xoá, không
// có lối về danh sách). Nay: empty-state chuẩn nêu mã + nút về danh sách kiểm kê.
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

const getCycleCount = vi.fn()
vi.mock('@/api/imm15', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/imm15')>()
  return { ...actual, getCycleCount: () => getCycleCount() }
})

import CycleCountDetailView from './CycleCountDetailView.vue'

const stubs = { PageHeader: true, StatusBadge: true, BaseModal: true, SkeletonLoader: true }

describe('CycleCountDetailView — phiếu kiểm kê không tồn tại (404)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    resetRouteMock()
    vi.clearAllMocks()
    getCycleCount.mockRejectedValue(
      new ApiError('Không tìm thấy phiếu kiểm kê: CYC-2026-99999.', {
        code: ErrorCode.NOT_FOUND, httpStatus: 404,
      }),
    )
  })
  afterEach(() => resetRouteMock())

  it('empty-state nêu mã phiếu + nút về danh sách kiểm kê', async () => {
    setRouteParams({ name: 'CYC-2026-99999' })
    const wrapper = mount(CycleCountDetailView, { global: { stubs } })
    await flushPromises()
    expect(wrapper.text()).toContain('Không tìm thấy phiếu kiểm kê')
    expect(wrapper.text()).toContain('CYC-2026-99999')

    const back = wrapper.findAll('button').find(b => /danh sách/i.test(b.text()))!
    await back.trigger('click')
    expect(routerPushSpy()).toHaveBeenCalledWith('/inventory/cycle-counts')
  })
})
