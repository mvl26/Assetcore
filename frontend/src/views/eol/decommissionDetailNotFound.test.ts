// Copyright (c) 2026, AssetCore Team
// TDD (FE regression guard) — IMM-14: chi tiết biên bản giải nhiệm khi mã không
// tồn tại (404). Trước: card lỗi chỉ có "Thử lại" (vô nghĩa với mã sai/đã xoá,
// không lối thoát). Nay: empty-state chuẩn nêu mã + nút về danh sách giải nhiệm.
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'
import { resetRouteMock, routerPushSpy } from '@/test/vueRouterMock'
import { ApiError, ErrorCode } from '@/api/errors'

vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())
vi.mock('@/composables/useNotify', () => ({
  useNotify: () => ({ show: vi.fn(), fromError: vi.fn(), fromOk: vi.fn(), confirm: vi.fn() }),
}))

// useApi.run: nuốt lỗi (silentError) và ghi lastError — mirror composable thật.
const lastError = ref<ApiError | null>(null)
vi.mock('@/composables/useApi', () => ({
  useApi: () => ({
    loading: ref(false),
    lastError,
    run: async (fn: () => Promise<unknown>) => {
      try { return await fn() } catch (e) { lastError.value = e as ApiError; return null }
    },
  }),
}))

const getDecommission = vi.fn()
vi.mock('@/api/imm14', () => ({
  getDecommission: () => getDecommission(),
  approveDecommission: vi.fn(),
}))

import DecommissionDetailView from './DecommissionDetailView.vue'

const stubs = { PageHeader: true, StatusBadge: true, BaseModal: true, SkeletonLoader: true }

describe('DecommissionDetailView — hồ sơ giải nhiệm không tồn tại (404)', () => {
  beforeEach(() => {
    resetRouteMock()
    vi.clearAllMocks()
    lastError.value = null
    getDecommission.mockRejectedValue(
      new ApiError('Không tìm thấy hồ sơ giải nhiệm: DECOM-2026-9999.', {
        code: ErrorCode.NOT_FOUND, httpStatus: 404,
      }),
    )
  })
  afterEach(() => resetRouteMock())

  it('empty-state nêu mã hồ sơ + nút về danh sách giải nhiệm', async () => {
    const wrapper = mount(DecommissionDetailView, {
      props: { id: 'DECOM-2026-9999' },
      global: { stubs },
    })
    await flushPromises()
    expect(wrapper.text()).toContain('Không tìm thấy hồ sơ giải nhiệm')
    expect(wrapper.text()).toContain('DECOM-2026-9999')

    const back = wrapper.findAll('button').find(b => /danh sách/i.test(b.text()))!
    await back.trigger('click')
    expect(routerPushSpy()).toHaveBeenCalledWith('/decommissions')
  })
})
