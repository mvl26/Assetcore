// Copyright (c) 2026, AssetCore Team
// TC-UX4-50 (docs/ui-ux/03 §13.6) — CompetencyDetailView áp khuôn `DetailPageShell` (lô 2, nhóm N3).
//
// RED trước fix: 5 CTA vòng đời («Phê duyệt» … «Thu hồi») nằm trong `PageHeader #actions` — vùng
// hiện ở MỌI trạng thái ⇒ hồ sơ 403/404 vẫn phơi nguyên dải nút, và `error` dùng CHUNG cho cả lỗi
// nạp lẫn lỗi hành động nên một cú «Thu hồi» hỏng cũng thay cả trang bằng banner (bẫy 13.9.7).
import { vi } from 'vitest'
import { mount } from '@vue/test-utils'
import type { UserCompetency } from '@/api/imm06'
import { describeDetailStates } from '@/test/detailStatesHarness'

const pushSpy = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: pushSpy, back: vi.fn() }),
  useRoute: () => ({ params: { name: 'UC-2026-0088' }, query: {} }),
}))

vi.mock('@/composables/useApi', () => ({
  useApi: () => ({ loading: { value: false }, run: (fn: () => Promise<unknown>) => fn() }),
}))

vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({ can: () => true, capabilities: { value: [] } }),
}))

const getCompetencySpy = vi.fn<() => Promise<UserCompetency | null>>()
vi.mock('@/api/imm06', () => ({
  getCompetency: (...a: unknown[]) => getCompetencySpy(...(a as [])),
  signoffCompetency: vi.fn(),
  revokeCompetency: vi.fn(),
  recertifyCompetency: vi.fn(),
  suspendCompetency: vi.fn(),
  restoreCompetency: vi.fn(),
}))

import CompetencyDetailView from '@/views/training/CompetencyDetailView.vue'

const stubs = { StatusBadge: true, SmartSelect: true, RouterLink: true }

function competencyFixture(): UserCompetency {
  return {
    name: 'UC-2026-0088',
    user_full_name: 'Nguyễn Văn Kỹ',
    workflow_state: 'Draft',
    days_until_expiry: 120,
    allowed_transitions: ['Certified'],
    can_signoff: true,
  } as unknown as UserCompetency
}

describeDetailStates({
  view: 'CompetencyDetailView',
  tc: 'TC-UX4-50',
  mount: () => mount(CompetencyDetailView, { props: { name: 'UC-2026-0088' }, global: { stubs } }) as never,
  pending: () => getCompetencySpy.mockReturnValue(new Promise(() => {})),
  fail: (e) => getCompetencySpy.mockRejectedValue(e),
  empty: () => getCompetencySpy.mockResolvedValue(null),
  ok: () => getCompetencySpy.mockResolvedValue(competencyFixture()),
  loadCalls: () => getCompetencySpy.mock.calls.length,
  reset: () => {
    getCompetencySpy.mockReset()
    pushSpy.mockClear()
  },
  recordId: 'UC-2026-0088',
  ctaTestIds: ['cta-signoff', 'cta-recertify', 'cta-restore', 'cta-suspend', 'cta-revoke', 'no-actions-hint'],
  routerPush: pushSpy,
})
