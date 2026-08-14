// Copyright (c) 2026, AssetCore Team
// TC-UX4-41 (docs/ui-ux/03 §13.6) — CycleCountDetailView áp khuôn `DetailPageShell` (lô 2, nhóm N1).
//
// RED trước fix: 3 CTA workflow («Gửi rà soát» / «Sửa đếm lại» / «Ghi nhận điều chỉnh») nằm trong
// thân bài của thẻ header, tắt bằng `v-if` từng nút chứ không bằng CẤU TRÚC; `loadErrorKind` được
// gọi cục bộ (bản sao thứ N — AC-UX-053). Sau fix: shell quyết định 4 trạng thái loại trừ, CTA vào
// slot `#actions` ⇒ 403/404 ⇒ 0 nút trên phiếu kiểm kê không đọc được.
import { vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { setRouteParams, resetRouteMock, routerPushSpy } from '@/test/vueRouterMock'
import { describeDetailStates } from '@/test/detailStatesHarness'

vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn(), info: vi.fn(), warning: vi.fn() }),
}))
vi.mock('@/composables/useNotify', () => ({
  useNotify: () => ({ show: vi.fn(), fromError: vi.fn(), fromOk: vi.fn(), confirm: vi.fn() }),
}))

const getCycleCountSpy = vi.fn()
vi.mock('@/api/imm15', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/imm15')>()
  return { ...actual, getCycleCount: () => getCycleCountSpy() }
})

import CycleCountDetailView from '@/views/inventory/CycleCountDetailView.vue'

const stubs = { StatusBadge: true, WorkflowStepper: true, ApproverSelect: true, RouterLink: true, BaseModal: { template: '<div><slot /><slot name="footer" /></div>' } }

function cycleCountFixture() {
  return {
    name: 'CYC-2026-00021',
    warehouse: 'WH-01',
    warehouse_name: 'Kho vật tư trung tâm',
    count_type: 'Full',
    count_date: '2026-08-03',
    status: 'Counting',
    allowed_transitions: ['Submit'],
    items: [],
    capa_created: 0,
  }
}

function mountView() {
  setActivePinia(createPinia())
  resetRouteMock()
  setRouteParams({ name: 'CYC-2026-00021' })
  return mount(CycleCountDetailView, { global: { stubs } })
}

describeDetailStates({
  view: 'CycleCountDetailView',
  tc: 'TC-UX4-41',
  mount: () => mountView() as never,
  pending: () => getCycleCountSpy.mockReturnValue(new Promise(() => {})),
  fail: (e) => getCycleCountSpy.mockRejectedValue(e),
  empty: () => getCycleCountSpy.mockResolvedValue(null),
  ok: () => getCycleCountSpy.mockResolvedValue(cycleCountFixture()),
  loadCalls: () => getCycleCountSpy.mock.calls.length,
  reset: () => {
    getCycleCountSpy.mockReset()
    routerPushSpy().mockClear()
  },
  recordId: 'CYC-2026-00021',
  ctaTestIds: ['cta-submit', 'cta-recount', 'cta-post', 'cta-back'],
  routerPush: routerPushSpy() as never,
})
