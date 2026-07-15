// Copyright (c) 2026, AssetCore Team
//
// IMM-01 — NeedsRequestDetailView: nút CTA Phê duyệt / Bác đề xuất gate theo SSoT
// `allowed_transitions` do BE emit (get_needs_request → get_transitions trên IMM
// Needs Request, api/imm01.py). KHÔNG hardcode isBoardApprover role-list HAY
// workflow_state === 'Pending Approval' literal (GATE-8 / LL-FE-51).
//
// Khoá 3 hành vi:
//   1. Hết dead-gate: Procurement Manager (KHÔNG có Dept Head/Ops Manager/System
//      Manager) THẤY cả 2 nút — chứng minh hết phụ thuộc isBoardApprover.
//   2. Hết false-permissive: allowed=[] (hoặc thiếu action) → nút tương ứng ẩn.
//   3. Parity guard: visibility quyết định bằng allowed_transitions, KHÔNG bằng
//      workflow_state literal hay role name.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { id: 'NR-2026-00001' } }),
  useRouter: () => ({ push: vi.fn(), back: vi.fn() }),
}))
vi.mock('@/composables/useApi', () => ({
  useApi: () => ({ run: vi.fn(async (fn: () => unknown) => fn()) }),
}))
// Auth KHÔNG cấp Dept Head / Ops Manager / System Manager → chứng minh nút render
// độc lập với isBoardApprover (dead-gate cũ).
vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({
    hasRole: () => false,
    hasAnyRole: () => false,
    isSystemAdmin: false,
    user: { name: 'proc.mgr@test.local' },
  }),
}))

const getNeedsRequest = vi.fn()
const getAllowedTransitions = vi.fn()
vi.mock('@/api/imm01', () => ({
  // View + store cùng import từ đây → khai đủ để không undefined.
  getNeedsRequest: (...a: unknown[]) => getNeedsRequest(...a),
  getAllowedTransitions: (...a: unknown[]) => getAllowedTransitions(...a),
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
  PageHeader: true, CurrencyInput: true, StatusBadge: true,
  BaseModal: true, SkeletonLoader: true, ApproverSelect: true,
}

const APPROVE = 'Phê duyệt'
const REJECT = 'Bác đề xuất'

function nrFixture(over: Record<string, unknown> = {}) {
  return {
    name: 'NR-2026-00001',
    request_type: 'New',
    requesting_department: 'AC-DEPT-1928',
    requesting_department_name: 'Phòng Vật tư - Thiết bị y tế',
    quantity: 1,
    target_year: 2027,
    clinical_justification: 'Lý do lâm sàng test.',
    workflow_state: 'Pending Approval',
    scoring_rows: [],
    budget_lines: [],
    allowed_transitions: [] as string[],
    ...over,
  }
}

/**
 * Mount detail với fixture. `docTransitions` (nếu truyền) đặt vào
 * currentDoc.allowed_transitions (nguồn ưu tiên). `fetchTransitions` mô phỏng
 * fallback getAllowedTransitions.
 */
async function render(
  over: Record<string, unknown> = {},
  fetchTransitions: string[] = [],
) {
  getNeedsRequest.mockResolvedValue(nrFixture(over))
  getAllowedTransitions.mockResolvedValue({
    workflow_state: (over.workflow_state as string) ?? 'Pending Approval',
    transitions: fetchTransitions.map((a) => ({ action: a, next_state: 'X' })),
  })
  const w = mount(NeedsRequestDetailView, {
    props: { id: 'NR-2026-00001' },
    global: { stubs },
  })
  await flushPromises()
  return w
}

function hasBtn(w: Awaited<ReturnType<typeof render>>, txt: string) {
  return w.findAll('button').some((b) => b.text().trim().includes(txt))
}

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
})

describe('NeedsRequestDetailView — CTA Phê duyệt/Bác đề xuất gate theo allowed_transitions', () => {
  it('Pending Approval + allowed=[Phê duyệt, Bác đề xuất] → render CẢ 2 nút (KHÔNG cần Dept Head/Ops Manager)', async () => {
    const w = await render({
      workflow_state: 'Pending Approval',
      allowed_transitions: [APPROVE, REJECT],
    })
    expect(hasBtn(w, APPROVE)).toBe(true)
    expect(hasBtn(w, REJECT)).toBe(true)
  })

  it('allowed=[] → KHÔNG render Phê duyệt/Bác đề xuất (hết false-permissive)', async () => {
    const w = await render({
      workflow_state: 'Pending Approval',
      allowed_transitions: [],
    })
    expect(hasBtn(w, APPROVE)).toBe(false)
    expect(hasBtn(w, REJECT)).toBe(false)
  })

  it('allowed chỉ [Phê duyệt] → nút Phê duyệt hiện, Bác đề xuất ẩn (gate từng action)', async () => {
    const w = await render({
      workflow_state: 'Pending Approval',
      allowed_transitions: [APPROVE],
    })
    expect(hasBtn(w, APPROVE)).toBe(true)
    expect(hasBtn(w, REJECT)).toBe(false)
  })

  it('PARITY: Pending Approval nhưng allowed=[] → 0 nút (gate là allowed_transitions, KHÔNG workflow_state literal)', async () => {
    const w = await render({
      workflow_state: 'Pending Approval',
      allowed_transitions: [],
    })
    expect(hasBtn(w, APPROVE)).toBe(false)
    expect(hasBtn(w, REJECT)).toBe(false)
  })

  it('PARITY nghịch: state KHÔNG phải Pending Approval nhưng allowed chứa Phê duyệt → nút vẫn render (chứng minh không khoá bằng status literal)', async () => {
    const w = await render({
      workflow_state: 'Budgeted',
      allowed_transitions: [APPROVE, REJECT],
    })
    expect(hasBtn(w, APPROVE)).toBe(true)
    expect(hasBtn(w, REJECT)).toBe(true)
  })

  it('Fallback: payload thiếu allowed_transitions → dùng getAllowedTransitions (không flash mất nút)', async () => {
    const fx = nrFixture({ workflow_state: 'Pending Approval' })
    delete (fx as Record<string, unknown>).allowed_transitions
    getNeedsRequest.mockResolvedValue(fx)
    getAllowedTransitions.mockResolvedValue({
      workflow_state: 'Pending Approval',
      transitions: [
        { action: APPROVE, next_state: 'Approved' },
        { action: REJECT, next_state: 'Rejected' },
      ],
    })
    const w = mount(NeedsRequestDetailView, { props: { id: 'NR-2026-00001' }, global: { stubs } })
    await flushPromises()
    expect(hasBtn(w, APPROVE)).toBe(true)
    expect(hasBtn(w, REJECT)).toBe(true)
  })

  it('Terminal (Approved) + allowed=[] → 0 nút Phê duyệt/Bác đề xuất', async () => {
    const w = await render({
      workflow_state: 'Approved',
      allowed_transitions: [],
    })
    expect(hasBtn(w, APPROVE)).toBe(false)
    expect(hasBtn(w, REJECT)).toBe(false)
  })
})
