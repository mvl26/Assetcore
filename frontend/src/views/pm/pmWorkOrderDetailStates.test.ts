// Copyright (c) 2026, AssetCore Team
// TC-UX4-44 (docs/ui-ux/03 §13.6) — PMWorkOrderDetailView áp khuôn `DetailPageShell` (lô 2, nhóm N2).
//
// Màn này ĐÃ dùng `useDetailAccess` từ CR-74 ⇒ lô 2 chỉ NỐI vào shell, KHÔNG viết lại composable.
// Delta thật: khung xương + nhánh `DetailLoadError` tự chế biến mất (shell sở hữu cả hai), và
// `<DetailTabBar>` hoisting lên prop shell (ADR-UX-25) ⇒ ĐÚNG 1 `[role="tablist"]` trong DOM.
import { ref } from 'vue'
import { vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { setRouteParams, resetRouteMock, routerPushSpy } from '@/test/vueRouterMock'
import { describeDetailStates } from '@/test/detailStatesHarness'

vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())
vi.mock('@/composables/useNotify', () => ({
  useNotify: () => ({ show: vi.fn(), fromError: vi.fn(), fromOk: vi.fn(), confirm: vi.fn() }),
}))
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn() }),
}))
vi.mock('@/composables/useCapabilities', () => ({ useCapabilities: () => ({ can: () => true }) }))

type WO = Record<string, unknown>
// Store THẬT nuốt lỗi vào `lastApiError` và để `currentWO=null` ⇒ mock mirror đúng hình dạng ấy:
// đó chính là getter mà `useDetailAccess(() => currentWO ? null : lastApiError)` đọc.
const currentWO = ref<WO | null>(null)
const storeLoading = ref(false)
const lastApiError = ref<unknown>(null)
const fetchWorkOrder = vi.fn()

vi.mock('@/stores/imm08', () => ({
  useImm08Store: () => ({
    get currentWO() { return currentWO.value },
    get loading() { return storeLoading.value },
    error: null,
    get lastApiError() { return lastApiError.value },
    ratedCount: 0,
    checklistComplete: true,
    hasMajorFailure: false,
    hasMinorFailure: false,
    fetchWorkOrder,
    doSubmitResult: vi.fn(),
    doReportMajorFailure: vi.fn(),
    doReschedule: vi.fn(),
    doAssignTechnician: vi.fn(),
    updateChecklistResult: vi.fn(),
  }),
}))

import PMWorkOrderDetailView from './PMWorkOrderDetailView.vue'

const stubs = { RelatedRecordsPanel: true, ApproverSelect: true, RouterLink: true, BaseModal: { template: '<div><slot /><slot name="footer" /></div>' } }

function woFixture(): WO {
  return {
    name: 'WO-PM-2026-00099',
    asset_ref: 'AC-ASSET-0099',
    asset_name: 'Máy thở Dräger Evita V500',
    pm_type: 'Routine',
    wo_type: 'Preventive',
    status: 'In Progress',
    allowed_transitions: ['Completed'],
    available_actions: [],
    due_date: '2026-06-01',
    scheduled_date: '2026-06-01',
    checklist_results: [],
    parts_used: [],
  }
}

function setState(wo: WO | null, err: unknown = null, loading = false) {
  currentWO.value = wo
  lastApiError.value = err
  storeLoading.value = loading
}

describeDetailStates({
  view: 'PMWorkOrderDetailView',
  tc: 'TC-UX4-44',
  mount: () => {
    setActivePinia(createPinia())
    resetRouteMock()
    setRouteParams({ id: 'WO-PM-2026-00099' })
    return mount(PMWorkOrderDetailView, { props: { id: 'WO-PM-2026-00099' }, global: { stubs } }) as never
  },
  pending: () => {
    setState(null, null, true)
    fetchWorkOrder.mockReturnValue(new Promise(() => {}))
  },
  fail: (e) => {
    setState(null, null, false)
    fetchWorkOrder.mockImplementation(async () => { setState(null, e) })
  },
  empty: () => fetchWorkOrder.mockImplementation(async () => setState(null, null)),
  ok: () => fetchWorkOrder.mockImplementation(async () => setState(woFixture(), null)),
  loadCalls: () => fetchWorkOrder.mock.calls.length,
  reset: () => {
    fetchWorkOrder.mockReset()
    setState(null, null, false)
    routerPushSpy().mockClear()
  },
  recordId: 'WO-PM-2026-00099',
  ctaTestIds: ['cta-start', 'cta-complete', 'cta-major', 'cta-reschedule', 'cta-resume'],
  hasTabs: true,
  routerPush: routerPushSpy() as never,
})
