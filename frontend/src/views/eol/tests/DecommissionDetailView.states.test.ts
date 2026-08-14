// Copyright (c) 2026, AssetCore Team
// TC-UX4-38 (docs/ui-ux/03 §13.6) — DecommissionDetailView áp khuôn `DetailPageShell` (lô 2, nhóm N1).
//
// RED trước fix: view đã có `DetailLoadError` nhưng tự dựng chuỗi trạng thái + tự gọi `loadErrorKind`
// (bản sao thứ N của logic phân loại — AC-UX-053), và panel «Duyệt giải nhiệm» nằm trong thân bài nên
// điều kiện tắt phụ thuộc `v-if` từng nhánh chứ không phải CẤU TRÚC. Sau fix: shell quyết định 4 trạng
// thái, CTA vào slot `#actions` ⇒ 403/404 ⇒ 0 nút trên một biên bản không đọc được.
import { ref } from 'vue'
import { vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { ApiError } from '@/api/errors'
import type { DecommissionRecord } from '@/api/imm14'
import { setRouteParams, resetRouteMock, routerPushSpy } from '@/test/vueRouterMock'
import { describeDetailStates } from '@/test/detailStatesHarness'

vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())
vi.mock('@/composables/useNotify', () => ({
  useNotify: () => ({ show: vi.fn(), fromError: vi.fn(), fromOk: vi.fn(), confirm: vi.fn() }),
}))

// `useApi.run` NUỐT lỗi (silentError) và ghi `lastError` — mirror composable thật; đây chính là
// lý do view phải đọc `api.lastError` chứ không bắt được exception.
const lastError = ref<ApiError | null>(null)
vi.mock('@/composables/useApi', () => ({
  useApi: () => ({
    loading: ref(false),
    lastError,
    run: async (fn: () => Promise<unknown>) => {
      try { lastError.value = null; return await fn() } catch (e) { lastError.value = e as ApiError; return null }
    },
  }),
}))

const getDecommissionSpy = vi.fn()
vi.mock('@/api/imm14', () => ({
  getDecommission: () => getDecommissionSpy(),
  approveDecommission: vi.fn(),
}))

import DecommissionDetailView from '@/views/eol/DecommissionDetailView.vue'

const stubs = { StatusBadge: true, BaseModal: true, RouterLink: true }

function recordFixture(): DecommissionRecord {
  return {
    name: 'DEC-2026-0011',
    asset: 'ACC-ASS-0001',
    asset_name: 'Máy thở PB980 — Khoa Hồi sức',
    workflow_state: 'Draft',
    docstatus: 0,
    can_approve: 1,
    approve_blocked_reason: '',
  } as unknown as DecommissionRecord
}

function mountView() {
  resetRouteMock()
  setRouteParams({ id: 'DEC-2026-0011' })
  return mount(DecommissionDetailView, { props: { id: 'DEC-2026-0011' }, global: { stubs } })
}

describeDetailStates({
  view: 'DecommissionDetailView',
  tc: 'TC-UX4-38',
  mount: () => mountView() as never,
  pending: () => getDecommissionSpy.mockReturnValue(new Promise(() => {})),
  fail: (e) => getDecommissionSpy.mockRejectedValue(e),
  empty: () => getDecommissionSpy.mockResolvedValue(null),
  ok: () => getDecommissionSpy.mockResolvedValue(recordFixture()),
  loadCalls: () => getDecommissionSpy.mock.calls.length,
  reset: () => {
    getDecommissionSpy.mockReset()
    lastError.value = null
    routerPushSpy().mockClear()
  },
  recordId: 'DEC-2026-0011',
  ctaTestIds: ['cta-approve', 'cta-open-asset', 'no-actions-hint'],
  routerPush: routerPushSpy() as never,
})
