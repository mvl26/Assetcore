// Copyright (c) 2026, AssetCore Team
// TC-UX4-42 (docs/ui-ux/03 §13.6) — NeedsRequestDetailView áp khuôn `DetailPageShell` (lô 2, nhóm N4).
//
// RED trước fix: nhánh lỗi tự chế in `store.error` (CHUỖI — không phân loại được 403/404/mạng) kèm
// nút «Thử lại» cho MỌI loại lỗi và KHÔNG có lối về danh sách ⇒ ngõ cụt; `<PageHeader #actions>` —
// vùng hiện ở mọi trạng thái — chứa huy hiệu trạng thái + nút quay lại. Sau fix: kind THẬT từ SSoT
// `useDetailAccess`, thanh tab hoisting lên prop shell (ADR-UX-25), 3 panel GIỮ `v-show` để không
// mất chữ đã gõ ở «Chấm điểm ưu tiên» / «Dự toán».
import { vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { describeDetailStates } from '@/test/detailStatesHarness'

const pushSpy = vi.fn()
vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { id: 'NR-2026-00001' } }),
  useRouter: () => ({ push: pushSpy, back: vi.fn() }),
}))
vi.mock('@/composables/useApi', () => ({
  useApi: () => ({ run: vi.fn(async (fn: () => unknown) => fn()) }),
}))
vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({ hasRole: () => true, hasAnyRole: () => true, isSystemAdmin: true, user: { name: 'qa@test.local' } }),
}))

const getNeedsRequestSpy = vi.fn()
vi.mock('@/api/imm01', () => ({
  getNeedsRequest: (...a: unknown[]) => getNeedsRequestSpy(...a),
  getAllowedTransitions: vi.fn().mockResolvedValue({ transitions: [] }),
  rollIntoPlan: vi.fn(),
  listNeedsRequests: vi.fn(),
  createNeedsRequest: vi.fn(),
  updateNeedsRequest: vi.fn(),
  scoreNeedsRequest: vi.fn(),
  submitBudgetEstimate: vi.fn(),
  transitionWorkflow: vi.fn(),
  approveNeedsRequest: vi.fn(),
  rejectNeedsRequest: vi.fn(),
  listProcurementPlans: vi.fn().mockResolvedValue({ items: [], total: 0, page: 1, page_size: 50 }),
  getDashboardKpis: vi.fn(),
}))

import NeedsRequestDetailView from './NeedsRequestDetailView.vue'

const stubs = {
  CurrencyInput: true, StatusBadge: true, ApproverSelect: true,
  BaseModal: { template: '<div><slot /><slot name="footer" /></div>' },
}

function nrFixture() {
  return {
    name: 'NR-2026-00001',
    request_type: 'New',
    requesting_department: 'AC-DEPT-1928',
    requesting_department_name: 'Phòng Vật tư - Thiết bị y tế',
    quantity: 1,
    target_year: 2027,
    clinical_justification: 'Lý do lâm sàng test.',
    workflow_state: 'Reviewing',
    scoring_rows: [],
    budget_lines: [],
    allowed_transitions: [] as string[],
  }
}

describeDetailStates({
  view: 'NeedsRequestDetailView',
  tc: 'TC-UX4-42',
  mount: () => {
    setActivePinia(createPinia())
    return mount(NeedsRequestDetailView, { global: { stubs } }) as never
  },
  pending: () => getNeedsRequestSpy.mockReturnValue(new Promise(() => {})),
  fail: (e) => getNeedsRequestSpy.mockRejectedValue(e),
  empty: () => getNeedsRequestSpy.mockResolvedValue(null),
  ok: () => getNeedsRequestSpy.mockResolvedValue(nrFixture()),
  loadCalls: () => getNeedsRequestSpy.mock.calls.length,
  reset: () => {
    getNeedsRequestSpy.mockReset()
    pushSpy.mockClear()
  },
  recordId: 'NR-2026-00001',
  ctaTestIds: ['cta-back'],
  hasTabs: true,
  routerPush: pushSpy,
})
