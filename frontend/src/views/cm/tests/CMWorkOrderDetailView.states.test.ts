// Copyright (c) 2026, AssetCore Team
// TC-UX4-34 (docs/ui-ux/03 §13.6) — CMWorkOrderDetailView áp khuôn `DetailPageShell` (lô 2, nhóm N2).
//
// Màn này ĐÃ dùng `useDetailAccess` từ CR-74 ⇒ lô 2 chỉ NỐI vào shell, KHÔNG viết lại composable.
// Delta thật: khung xương + nhánh `DetailLoadError` tự chế biến mất (shell sở hữu cả hai), và
// `<DetailTabBar>` hoisting lên prop shell (ADR-UX-25) ⇒ ĐÚNG 1 `[role="tablist"]` trong DOM —
// đúng điều A6 đo. Modal «Phân công kỹ thuật viên» vẫn nằm NGOÀI hai panel `v-show`.
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
vi.mock('@/composables/useCapabilities', () => ({ useCapabilities: () => ({ can: () => true }) }))
vi.mock('@/api/connections', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/api/connections')>()),
  getConnections: vi.fn().mockResolvedValue({ groups: [] }),
}))

type WO = Record<string, unknown>
const currentWO = ref<WO | null>(null)
const storeLoading = ref(false)
const lastApiError = ref<unknown>(null)
const fetchWorkOrder = vi.fn()

vi.mock('@/stores/imm09', () => ({
  useImm09Store: () => ({
    get currentWO() { return currentWO.value },
    get loading() { return storeLoading.value },
    error: null,
    get lastApiError() { return lastApiError.value },
    fetchWorkOrder,
    doAssignTechnician: vi.fn(),
    doConfirmInspection: vi.fn(),
    doCloseWorkOrder: vi.fn(),
  }),
}))

import CMWorkOrderDetailView from '@/views/cm/CMWorkOrderDetailView.vue'

const WO_NAME = 'WO-RP-2026-00099'
const stubs = { RouterLink: true, ApproverSelect: true, RelatedRecords: true, BaseModal: { template: '<div><slot /><slot name="footer" /></div>' } }

function woFixture(): WO {
  return {
    name: WO_NAME, asset_ref: 'AC-ASSET-0099', asset_name: 'Máy thở CTA',
    asset_category: 'Ventilator', risk_class: 'High', serial_no: 'SN-CTA-1',
    repair_type: 'Corrective', priority: 'Urgent', status: 'Open',
    allowed_transitions: ['Assigned', 'Cancelled'],
    open_datetime: '2026-06-01 08:00:00', assigned_datetime: null, completion_datetime: null,
    assigned_to: '', assigned_to_name: '', mttr_hours: null, sla_target_hours: 72,
    sla_breached: false, is_repeat_failure: false, incident_report: null, source_pm_wo: null,
    diagnosis_notes: '', root_cause_category: '', repair_summary: '', firmware_updated: false,
    firmware_change_request: null, dept_head_name: '', total_parts_cost: 0,
    spare_parts_used: [], repair_checklist: [],
  }
}

function setState(wo: WO | null, err: unknown = null, loading = false) {
  currentWO.value = wo
  lastApiError.value = err
  storeLoading.value = loading
}

describeDetailStates({
  view: 'CMWorkOrderDetailView',
  tc: 'TC-UX4-34',
  mount: () => {
    setActivePinia(createPinia())
    resetRouteMock()
    setRouteParams({ id: WO_NAME })
    return mount(CMWorkOrderDetailView, { props: { id: WO_NAME }, global: { stubs } }) as never
  },
  pending: () => {
    setState(null, null, true)
    fetchWorkOrder.mockReturnValue(new Promise(() => {}))
  },
  fail: (e) => {
    setState(null, null, false)
    fetchWorkOrder.mockImplementation(async () => setState(null, e))
  },
  empty: () => fetchWorkOrder.mockImplementation(async () => setState(null, null)),
  ok: () => fetchWorkOrder.mockImplementation(async () => setState(woFixture(), null)),
  loadCalls: () => fetchWorkOrder.mock.calls.length,
  reset: () => {
    fetchWorkOrder.mockReset()
    setState(null, null, false)
    routerPushSpy().mockClear()
  },
  recordId: WO_NAME,
  ctaTestIds: ['cta-assign', 'cta-diagnose', 'cta-parts', 'cta-complete', 'cta-confirm-inspection', 'cta-cannot-repair'],
  hasTabs: true,
  routerPush: routerPushSpy() as never,
})
