// Copyright (c) 2026, AssetCore Team
// TC-UX4-39 (docs/ui-ux/03 §13.6) — IncidentDetailView áp khuôn `DetailPageShell` (lô 2, nhóm N2).
//
// Màn này ĐÃ dùng `useDetailAccess` từ CR-74 ⇒ lô 2 chỉ NỐI vào shell, KHÔNG viết lại composable.
// Delta thật: (1) `v-if="!loadBlocked"` bọc dải CTA biến mất — điều kiện ấy nay là CẤU TRÚC của
// shell, không còn là thứ mỗi màn phải nhớ; (2) `<DetailTabBar v-if="!loading && form.status">`
// hoisting lên prop shell (ADR-UX-25) ⇒ ĐÚNG 1 thanh tab, không có nguy cơ 2 `role="tablist"`.
import { vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import type { IncidentDetail } from '@/api/imm12'
import { describeDetailStates } from '@/test/detailStatesHarness'

const pushSpy = vi.fn()
vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { id: 'INC-2026-00077' } }),
  useRouter: () => ({ push: pushSpy, back: vi.fn() }),
}))

const getIncidentSpy = vi.fn<() => Promise<IncidentDetail>>()
vi.mock('@/api/imm12', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/imm12')>()
  return {
    ...actual,
    getIncident: () => getIncidentSpy(),
    acknowledgeIncident: vi.fn(),
    startWork: vi.fn(),
    resolveIncident: vi.fn(),
    closeIncident: vi.fn(),
    cancelIncident: vi.fn(),
    reopenIncident: vi.fn(),
    requestRca: vi.fn(),
    createRca: vi.fn(),
    attachIncidentPhoto: vi.fn(),
  }
})
vi.mock('@/api/imm00', () => ({ deleteIncident: vi.fn() }))
vi.mock('@/composables/useNotify', () => ({
  useNotify: () => ({ show: vi.fn(), fromError: vi.fn(), fromOk: vi.fn(), confirm: vi.fn() }),
}))

import IncidentDetailView from '@/views/incident/IncidentDetailView.vue'

const stubs = {
  WorkflowStepper: true,
  SlaCountdown: true,
  RelatedRecordsPanel: true,
  RouterLink: true,
  BaseModal: { template: '<div><slot /><slot name="footer" /></div>' },
}

function incidentFixture(): IncidentDetail {
  return {
    name: 'INC-2026-00077',
    asset: 'ACC-ASS-0001',
    asset_name: 'Máy thở PB980 — Khoa Hồi sức',
    severity: 'Medium',
    status: 'Open',
    incident_type: 'Device Failure',
    reported_at: '2026-08-01 09:00:00',
    allowed_transitions: ['Acknowledged', 'Cancelled'],
    scene_photos: [],
  } as unknown as IncidentDetail
}

describeDetailStates({
  view: 'IncidentDetailView',
  tc: 'TC-UX4-39',
  mount: () => {
    setActivePinia(createPinia())
    return mount(IncidentDetailView, { global: { stubs } }) as never
  },
  pending: () => getIncidentSpy.mockReturnValue(new Promise(() => {})),
  fail: (e) => getIncidentSpy.mockRejectedValue(e),
  empty: () => getIncidentSpy.mockResolvedValue({} as IncidentDetail),
  ok: () => getIncidentSpy.mockResolvedValue(incidentFixture()),
  loadCalls: () => getIncidentSpy.mock.calls.length,
  reset: () => {
    getIncidentSpy.mockReset()
    pushSpy.mockClear()
  },
  recordId: 'INC-2026-00077',
  ctaTestIds: [
    'cta-acknowledge', 'cta-start', 'cta-resolve', 'cta-close',
    'cta-request-rca', 'cta-reopen', 'cta-cancel', 'cta-delete',
  ],
  hasTabs: true,
  routerPush: pushSpy,
})
