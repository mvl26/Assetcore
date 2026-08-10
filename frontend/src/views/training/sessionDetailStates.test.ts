// Copyright (c) 2026, AssetCore Team
// TC-UX4-52 (docs/ui-ux/03 §13.6) — SessionDetailView áp khuôn `DetailPageShell`
// (lô 2, nhóm N1 + LƯỠNG DỤNG tạo/sửa).
//
// RED trước fix: 7 CTA vòng đời («Xác nhận» … «Hủy buổi») nằm trong `PageHeader #actions` — vùng
// hiện ở MỌI trạng thái ⇒ bản ghi 403/404 vẫn phơi nguyên dải nút. Sau fix chúng nằm trong slot
// `#actions` của shell, tắt bằng CẤU TRÚC; `loadErrorKind` cục bộ thay bằng SSoT `useDetailAccess`.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { setRouteParams, resetRouteMock, routerPushSpy } from '@/test/vueRouterMock'
import type { TrainingSession } from '@/api/imm06'
import { describeDetailStates } from '@/test/detailStatesHarness'

vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn(), info: vi.fn(), warning: vi.fn() }),
}))
vi.mock('@/composables/useNotify', () => ({
  useNotify: () => ({ show: vi.fn(), fromError: vi.fn(), fromOk: vi.fn(), confirm: vi.fn() }),
}))

const getSessionSpy = vi.fn()
vi.mock('@/api/imm06', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/imm06')>()
  return { ...actual, getSession: () => getSessionSpy() }
})

import SessionDetailView from './SessionDetailView.vue'

const stubs = {
  StatusBadge: true,
  SmartSelect: true,
  DateInput: true,
  ApproverSelect: true,
  BaseModal: { template: '<div><slot /><slot name="footer" /></div>' },
  RouterLink: true,
}

function sessionFixture(): TrainingSession {
  return {
    name: 'TS-2026-0042',
    training_program: 'TP-2026-0007',
    session_date: '2026-08-10',
    session_type: 'Onsite',
    workflow_state: 'Scheduled',
    location: 'Phòng đào tạo 2',
    attendees: [],
    can_confirm: true,
  } as unknown as TrainingSession
}

function mountEdit() {
  setActivePinia(createPinia())
  resetRouteMock()
  setRouteParams({ name: 'TS-2026-0042' })
  return mount(SessionDetailView, { props: { name: 'TS-2026-0042' }, global: { stubs } })
}

describeDetailStates({
  view: 'SessionDetailView',
  tc: 'TC-UX4-52',
  mount: () => mountEdit() as never,
  pending: () => getSessionSpy.mockReturnValue(new Promise(() => {})),
  fail: (e) => getSessionSpy.mockRejectedValue(e),
  empty: () => getSessionSpy.mockResolvedValue(null),
  ok: () => getSessionSpy.mockResolvedValue(sessionFixture()),
  loadCalls: () => getSessionSpy.mock.calls.length,
  reset: () => {
    getSessionSpy.mockReset()
    routerPushSpy().mockClear()
  },
  recordId: 'TS-2026-0042',
  ctaTestIds: [
    'cta-confirm', 'cta-start', 'cta-complete', 'cta-verify', 'cta-close', 'cta-cancel', 'cta-create',
  ],
  routerPush: routerPushSpy() as never,
})

describe("SessionDetailView — (g') chế độ TẠO MỚI không bị shell nuốt (§13.4.3)", () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    resetRouteMock()
    getSessionSpy.mockReset()
  })

  it('/imm06/sessions/new ⇒ content, 0 empty-state, biểu mẫu tạo còn nguyên', async () => {
    const w = mount(SessionDetailView, { props: {}, global: { stubs } })
    await flushPromises()
    expect(w.attributes('data-state')).toBe('content')
    expect(w.find('[data-testid="detail-load-error"]').exists()).toBe(false)
    expect(w.find('[data-testid="cta-create"]').exists()).toBe(true)
    expect(w.text()).toContain('Thông tin buổi đào tạo')
    expect(getSessionSpy).not.toHaveBeenCalled()
  })
})
