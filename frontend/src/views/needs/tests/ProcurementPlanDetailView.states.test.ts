// Copyright (c) 2026, AssetCore Team
// TC-UX4-43 (docs/ui-ux/03 §13.6) — ProcurementPlanDetailView áp khuôn `DetailPageShell` (lô 2, nhóm N3).
//
// RED trước fix: 0 lối nạp lại (chỉ `.alert-error` in chuỗi, không nút «Thử lại», không lối về danh
// sách ⇒ ngõ cụt) và `error` dùng CHUNG với 5 hành động (gom đề xuất / duyệt / kích hoạt / đóng kỳ /
// đặt ngân sách) ⇒ một cú bấm hỏng xoá trắng cả kế hoạch đang xem (bẫy 13.9.7). Kèm **2** lần
// `page-container` (view + `<style scoped>`) chồng lên lớp bao của shell (bẫy 13.9.5).
//
// NGOÀI phạm vi lô này: 5 chỗ gate `workflow_state === 'Draft'` (AC-UX-049) — cần cờ server
// `can_edit`, là hard-dependency BE.
import { vi } from 'vitest'
import { mount } from '@vue/test-utils'
import type { ProcurementPlanDetail } from '@/api/imm01'
import { describeDetailStates } from '@/test/detailStatesHarness'

const pushSpy = vi.fn()
vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { id: 'PP-2026-0003' } }),
  useRouter: () => ({ push: pushSpy, back: vi.fn() }),
}))

const getProcurementPlanSpy = vi.fn()
vi.mock('@/api/imm01', () => ({
  getProcurementPlan: (...a: unknown[]) => getProcurementPlanSpy(...(a as [])),
  rollIntoPlan: vi.fn(),
  listNeedsRequests: vi.fn().mockResolvedValue({ items: [] }),
  approvePlan: vi.fn(),
  activatePlan: vi.fn(),
  closePlan: vi.fn(),
  setBudgetEnvelope: vi.fn(),
  removeFromPlan: vi.fn(),
}))

import ProcurementPlanDetailView from '@/views/needs/ProcurementPlanDetailView.vue'

const stubs = { CurrencyInput: true, RouterLink: true }

function planFixture(): ProcurementPlanDetail {
  return {
    name: 'PP-2026-0003',
    plan_period: 'Quý 3',
    plan_year: 2026,
    workflow_state: 'Draft',
    budget_envelope: 5_000_000_000,
    plan_items: [],
    allowed_actions: ['Phê duyệt kế hoạch'],
  } as unknown as ProcurementPlanDetail
}

describeDetailStates({
  view: 'ProcurementPlanDetailView',
  tc: 'TC-UX4-43',
  mount: () => mount(ProcurementPlanDetailView, { props: { id: 'PP-2026-0003' }, global: { stubs } }) as never,
  pending: () => getProcurementPlanSpy.mockReturnValue(new Promise(() => {})),
  fail: (e) => getProcurementPlanSpy.mockRejectedValue(e),
  empty: () => getProcurementPlanSpy.mockResolvedValue(null),
  ok: () => getProcurementPlanSpy.mockResolvedValue(planFixture()),
  loadCalls: () => getProcurementPlanSpy.mock.calls.length,
  reset: () => {
    getProcurementPlanSpy.mockReset()
    pushSpy.mockClear()
  },
  recordId: 'PP-2026-0003',
  ctaTestIds: ['cta-approve', 'cta-activate', 'cta-close', 'cta-roll-in', 'cta-back'],
  routerPush: pushSpy,
})
