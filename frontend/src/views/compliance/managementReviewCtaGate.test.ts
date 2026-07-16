// TDD — IMM-16 ManagementReviewDetailView server-driven CTA gate (ADR-IMM-16-03 /
// GATE-8 / LL-FE-51). Client-map NEXT_LABEL không còn vai trò GATE và
// `canClose = status === 'Minutes Approved'` đã bị GỠ: nút vòng đời render THEO
// `mr.allowed_transitions` (get_management_review emit từ CÙNG SoT _MR_TRANSITIONS
// mà advance_mr_state/finalize_management_review enforce) + cờ can_advance/can_close
// (= rbac.can('compliance.submit')). Parity CapaRecord/InternalAudit — đóng nốt
// workflow IMM-16 thứ 4/4.
//
//   - matrix status × {allowed_transitions, can_advance, can_close} → đúng tập nút.
//   - MR 'Minutes Approved' nhưng can_close=false → KHÔNG hiện nút Đóng
//     (chứng minh gỡ hardcode status==='Minutes Approved').
//   - user KHÔNG capability → 0 nút CTA + no-actions-hint (không dead-control 403).
//   - degrade an toàn: allowed_transitions/cờ undefined (BE cũ) → 0 nút CTA + hint.
//   - anti-dead-control: click 'Đánh dấu Đã họp' → actionAdvanceMr(name,'Held');
//     click 'Đóng và xuất biên bản' → (modal) → actionFinalizeReview(name,...).
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import type { ManagementReview } from '@/api/imm16'

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { id: 'MR-2099-Q1' } }),
  useRouter: () => ({ push: vi.fn(), back: vi.fn() }),
}))

vi.mock('@/composables/useApi', () => ({
  useApi: () => ({
    loading: { value: false },
    run: (fn: () => Promise<unknown>) => fn(),
  }),
}))

const getManagementReviewSpy = vi.fn<() => Promise<ManagementReview>>()
vi.mock('@/api/imm16', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/imm16')>()
  return { ...actual, getManagementReview: () => getManagementReviewSpy() }
})

const actionAdvanceMrSpy = vi.fn().mockResolvedValue({ status: 'Held' })
const actionFinalizeReviewSpy = vi.fn().mockResolvedValue({ status: 'Closed' })
vi.mock('@/stores/imm16', () => ({
  useImm16Store: () => ({
    actionAdvanceMr: actionAdvanceMrSpy,
    actionFinalizeReview: actionFinalizeReviewSpy,
    actionUpdateReview: vi.fn(),
  }),
}))

import ManagementReviewDetailView from './ManagementReviewDetailView.vue'

const stubs = {
  BaseModal: { template: '<div class="modal-stub"><slot /><slot name="footer" /></div>' },
  SkeletonLoader: true,
  RouterLink: true,
  // RecordHistory expose reload() — refreshAll() gọi historyRef.value?.reload();
  // stub trần thiếu method → unhandled rejection.
  RecordHistory: { template: '<div />', methods: { reload() {} } },
}

function baseMr(overrides: Partial<ManagementReview>): ManagementReview {
  return {
    name: 'MR-2099-Q1',
    quarter: 'Q1-2099',
    review_date: '2099-01-15',
    chair: 'Administrator',
    status: 'Draft',
    workflow_state: 'Draft',
    ...overrides,
  } as ManagementReview
}

async function mountWith(overrides: Partial<ManagementReview>) {
  getManagementReviewSpy.mockResolvedValue(baseMr(overrides))
  const wrapper = mount(ManagementReviewDetailView, { global: { stubs } })
  await flushPromises()
  return wrapper
}

describe('ManagementReviewDetailView — server-driven CTA gate (allowed_transitions)', () => {
  beforeEach(() => {
    getManagementReviewSpy.mockReset()
    actionAdvanceMrSpy.mockClear()
    actionFinalizeReviewSpy.mockClear()
  })

  // Matrix: Draft + allowed=[Held] + can_advance → chỉ nút "Đánh dấu Đã họp".
  it('Draft + allowed=[Held] + can_advance → nút "Đánh dấu Đã họp"', async () => {
    const w = await mountWith({
      status: 'Draft', allowed_transitions: ['Held'], can_advance: true,
    })
    const cta = w.find('[data-testid="cta-advance"]')
    expect(cta.exists()).toBe(true)
    expect(cta.text()).toBe('Đánh dấu Đã họp')
    expect(w.find('[data-testid="cta-close"]').exists()).toBe(false)
    expect(w.find('[data-testid="no-actions-hint"]').exists()).toBe(false)
  })

  it('Held + allowed=[Minutes Approved] + can_advance → nút "Phê duyệt Biên bản"', async () => {
    const w = await mountWith({
      status: 'Held', workflow_state: 'Held',
      allowed_transitions: ['Minutes Approved'], can_advance: true,
    })
    const cta = w.find('[data-testid="cta-advance"]')
    expect(cta.exists()).toBe(true)
    expect(cta.text()).toBe('Phê duyệt Biên bản')
    expect(w.find('[data-testid="cta-close"]').exists()).toBe(false)
  })

  it('Minutes Approved + allowed=[Closed] + can_close → nút "Đóng và xuất biên bản"', async () => {
    const w = await mountWith({
      status: 'Minutes Approved', workflow_state: 'Minutes Approved',
      allowed_transitions: ['Closed'], can_close: true,
    })
    expect(w.find('[data-testid="cta-close"]').exists()).toBe(true)
    expect(w.find('[data-testid="cta-advance"]').exists()).toBe(false)
    expect(w.find('[data-testid="no-actions-hint"]').exists()).toBe(false)
  })

  // Gỡ hardcode: Minutes Approved nhưng can_close=false → KHÔNG hiện nút Đóng.
  it('Minutes Approved + can_close=false → KHÔNG nút Đóng + hiện hint (gỡ hardcode status)', async () => {
    const w = await mountWith({
      status: 'Minutes Approved', workflow_state: 'Minutes Approved',
      allowed_transitions: ['Closed'], can_close: false,
    })
    expect(w.find('[data-testid="cta-close"]').exists()).toBe(false)
    expect(w.find('[data-testid="cta-advance"]').exists()).toBe(false)
    expect(w.find('[data-testid="no-actions-hint"]').exists()).toBe(true)
  })

  // User KHÔNG capability: allowed emit nhưng can_advance=false → 0 nút + hint.
  it('Draft + allowed=[Held] + can_advance=false → 0 nút CTA + hint (không dead-control)', async () => {
    const w = await mountWith({
      status: 'Draft', allowed_transitions: ['Held'], can_advance: false,
    })
    expect(w.find('[data-testid="cta-advance"]').exists()).toBe(false)
    expect(w.find('[data-testid="cta-close"]').exists()).toBe(false)
    expect(w.find('[data-testid="no-actions-hint"]').exists()).toBe(true)
  })

  // Degrade an toàn: allowed_transitions + cờ undefined (BE cũ) → 0 nút CTA + hint.
  it('allowed_transitions/cờ undefined (BE cũ) → 0 nút CTA + hint (degrade an toàn)', async () => {
    const w = await mountWith({ status: 'Draft' })
    expect(w.find('[data-testid="cta-advance"]').exists()).toBe(false)
    expect(w.find('[data-testid="cta-close"]').exists()).toBe(false)
    expect(w.find('[data-testid="no-actions-hint"]').exists()).toBe(true)
  })

  // Closed terminal → 0 nút CTA, KHÔNG hint.
  it('Closed → 0 nút CTA, KHÔNG hint', async () => {
    const w = await mountWith({
      status: 'Closed', workflow_state: 'Closed', allowed_transitions: [],
      can_advance: true, can_close: true,
    })
    expect(w.find('[data-testid="cta-advance"]').exists()).toBe(false)
    expect(w.find('[data-testid="cta-close"]').exists()).toBe(false)
    expect(w.find('[data-testid="no-actions-hint"]').exists()).toBe(false)
  })

  // Anti-desync: server emit khác client-map — status Draft nhưng server chỉ cho
  // 'Closed' (không 'Held') → render THEO server (nút Đóng), KHÔNG nút advance.
  it('anti-desync: Draft nhưng server allowed=[Closed] → nút Đóng (theo server), KHÔNG advance', async () => {
    const w = await mountWith({
      status: 'Draft', allowed_transitions: ['Closed'], can_advance: true, can_close: true,
    })
    expect(w.find('[data-testid="cta-advance"]').exists()).toBe(false)
    expect(w.find('[data-testid="cta-close"]').exists()).toBe(true)
  })

  // Anti-dead-control (advance): click "Đánh dấu Đã họp" → actionAdvanceMr(name,'Held').
  it("click 'Đánh dấu Đã họp' → store.actionAdvanceMr(name,'Held')", async () => {
    const w = await mountWith({
      status: 'Draft', allowed_transitions: ['Held'], can_advance: true,
    })
    await w.find('[data-testid="cta-advance"]').trigger('click')
    await flushPromises()
    expect(actionAdvanceMrSpy).toHaveBeenCalledTimes(1)
    expect(actionAdvanceMrSpy.mock.calls[0][0]).toBe('MR-2099-Q1')
    expect(actionAdvanceMrSpy.mock.calls[0][1]).toBe('Held')
  })

  // Anti-dead-control (close): click "Đóng và xuất biên bản" → modal → xác nhận
  // gọi actionFinalizeReview(name, minutes, actions).
  it("click 'Đóng và xuất biên bản' → xác nhận gọi store.actionFinalizeReview(name,...)", async () => {
    const w = await mountWith({
      status: 'Minutes Approved', workflow_state: 'Minutes Approved',
      allowed_transitions: ['Closed'], can_close: true,
      minutes_doc: 'https://files/mr.pdf',
      output_actions: [{ action_description: 'Cải tiến PM', responsible: 'u@h.vn' }],
    })
    await w.find('[data-testid="cta-close"]').trigger('click')
    await flushPromises()
    await w.find('[data-testid="cta-close-confirm"]').trigger('click')
    await flushPromises()
    expect(actionFinalizeReviewSpy).toHaveBeenCalledTimes(1)
    expect(actionFinalizeReviewSpy.mock.calls[0][0]).toBe('MR-2099-Q1')
  })
})
