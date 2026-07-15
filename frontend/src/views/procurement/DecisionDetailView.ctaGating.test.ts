// TDD / regression guard — GATE-8 / LL-FE-51: server-driven CTA cho Quyết định
// mua sắm (IMM-03).
//
// Nút chuyển-trạng-thái ở DecisionDetailView gate theo `allowed_transitions` do BE
// emit (SoT = get_decision → _DECISION_VALID_TRANSITIONS, khớp fixture 'IMM-03
// Decision Workflow') — KHÔNG hardcode `workflow_state === 'X'` và KHÔNG còn hằng
// client TRANSITIONS_BY_STATE (từng THIẾU nhánh 'Pending Approval' ⇒ nút 'Huỷ
// Decision' không render ⇒ QTV/Procurement Manager không huỷ được dù có quyền).
//
// Ánh xạ action (khớp EXACT workflow.json):
//   Draft            --Chọn phương án-----> Method Selected
//   Pending Approval --Phê duyệt trúng thầu-> Awarded  (form Award riêng)
//   Pending Approval --Huỷ Decision--------> Cancelled (nút workflow chung)
//   Awarded          --Ký HĐ--------------> Contract Signed (form record-contract riêng)
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import type { DecisionDoc } from '@/types/imm03'
// eslint-disable-next-line @typescript-eslint/no-explicit-any
import viewSource from './DecisionDetailView.vue?raw'

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { id: 'PD-2026-00001' } }),
  useRouter: () => ({ push: vi.fn(), back: vi.fn(), replace: vi.fn() }),
}))

// notify.confirm → true (auto-xác nhận) để kiểm param transition phát đi (GATE-6c).
const confirmSpy = vi.fn().mockResolvedValue(true)
vi.mock('@/composables/useNotify', () => ({
  useNotify: () => ({
    show: vi.fn(), fromError: vi.fn(), fromOk: vi.fn(), confirm: confirmSpy,
  }),
}))

// ─── API mocks ─────────────────────────────────────────────────────────────────
const getDecisionSpy = vi.fn()
const transitionSpy = vi.fn().mockResolvedValue({ name: 'PD-2026-00001', workflow_state: 'Cancelled', docstatus: 0 })
vi.mock('@/api/imm03', () => ({
  // store.fetchDecision → api.getDecision
  getDecision: (...a: unknown[]) => getDecisionSpy(...a),
  // direct imports trong view
  getEvaluation: vi.fn().mockResolvedValue({ candidates: [], has_top_tie: false, tied_candidates: '' }),
  awardDecision: vi.fn().mockResolvedValue({ name: 'PD-2026-00001', workflow_state: 'Awarded' }),
  recordContract: vi.fn().mockResolvedValue({ name: 'PD-2026-00001', workflow_state: 'Contract Signed' }),
  transitionDecisionWorkflow: (...a: unknown[]) => transitionSpy(...a),
}))

import DecisionDetailView from './DecisionDetailView.vue'

function makeDecision(over: Partial<DecisionDoc> = {}): DecisionDoc {
  return {
    name: 'PD-2026-00001', spec_ref: 'TS-1', evaluation_ref: 'VE-1',
    workflow_state: 'Draft', creation: '2026-06-01',
    allowed_transitions: [],
    ...over,
  } as DecisionDoc
}

async function mountDetail(decision: DecisionDoc) {
  getDecisionSpy.mockResolvedValue(decision)
  const w = mount(DecisionDetailView, {
    props: { id: 'PD-2026-00001' },
    global: { stubs: { CurrencyInput: true } },
  })
  await flushPromises()
  return w
}

function workflowActionValues(w: Awaited<ReturnType<typeof mountDetail>>): string[] {
  return w.findAll('[data-testid="workflow-action"]').map((b) => b.attributes('data-action') ?? '')
}

beforeEach(() => {
  setActivePinia(createPinia())
  getDecisionSpy.mockReset()
  transitionSpy.mockClear()
  confirmSpy.mockClear()
})

describe('IMM-03 DecisionDetailView — CTA server-driven theo allowed_transitions', () => {
  it('(a) Pending Approval + allowed=[Phê duyệt trúng thầu, Huỷ Decision] → form Award + nút Huỷ Decision', async () => {
    const w = await mountDetail(makeDecision({
      workflow_state: 'Pending Approval',
      allowed_transitions: ['Phê duyệt trúng thầu', 'Huỷ Decision'],
    }))
    // form "Phê duyệt trao thầu" hiển thị (canAward)
    expect(w.find('[data-testid="cta-award"]').exists()).toBe(true)
    // nút workflow chung: đúng 'Huỷ Decision' (khôi phục — trước đây client-map bỏ sót)
    expect(workflowActionValues(w)).toEqual(['Huỷ Decision'])
    // record-contract KHÔNG hiện ở pha này
    expect(w.find('[data-testid="cta-record-contract"]').exists()).toBe(false)
  })

  it('(b) Awarded + allowed=[Ký HĐ] → form record-contract; Award ẩn; 0 nút workflow chung', async () => {
    const w = await mountDetail(makeDecision({
      workflow_state: 'Awarded', allowed_transitions: ['Ký HĐ'],
    }))
    expect(w.find('[data-testid="cta-record-contract"]').exists()).toBe(true)
    expect(w.find('[data-testid="cta-award"]').exists()).toBe(false)
    // 'Ký HĐ' có form riêng → KHÔNG render như nút workflow chung
    expect(workflowActionValues(w)).toEqual([])
  })

  it('(c) PO Issued/Cancelled + allowed=[] → KHÔNG nút action nào (terminal)', async () => {
    const w = await mountDetail(makeDecision({
      workflow_state: 'PO Issued', allowed_transitions: [],
    }))
    expect(w.find('[data-testid="cta-award"]').exists()).toBe(false)
    expect(w.find('[data-testid="cta-record-contract"]').exists()).toBe(false)
    expect(workflowActionValues(w)).toEqual([])
  })

  it('(d) Draft + allowed=[Chọn phương án] → 1 nút workflow chung "Chọn phương án"', async () => {
    const w = await mountDetail(makeDecision({
      workflow_state: 'Draft', allowed_transitions: ['Chọn phương án'],
    }))
    expect(workflowActionValues(w)).toEqual(['Chọn phương án'])
    expect(w.find('[data-testid="cta-award"]').exists()).toBe(false)
  })

  it('(e) allowed_transitions vắng (BE chưa reload) → canDo=false mọi action, KHÔNG crash', async () => {
    const d = makeDecision({ workflow_state: 'Pending Approval' })
    delete (d as { allowed_transitions?: string[] }).allowed_transitions
    const w = await mountDetail(d)
    expect(w.find('[data-testid="cta-award"]').exists()).toBe(false)
    expect(workflowActionValues(w)).toEqual([])
  })

  // GATE-6c (chống dead-control): param transition phát đi == UI-selection (raw
  // action value, KHÔNG nhãn Việt-hoá hiển thị).
  it('(f) click nút Huỷ Decision → transitionDecisionWorkflow(name, "Huỷ Decision") — value gửi BE = action gốc', async () => {
    const w = await mountDetail(makeDecision({
      workflow_state: 'Pending Approval',
      allowed_transitions: ['Phê duyệt trúng thầu', 'Huỷ Decision'],
    }))
    const btn = w.findAll('[data-testid="workflow-action"]').find(
      (b) => b.attributes('data-action') === 'Huỷ Decision')
    expect(btn).toBeTruthy()
    await btn!.trigger('click')
    await flushPromises()
    expect(confirmSpy).toHaveBeenCalledTimes(1)
    expect(transitionSpy).toHaveBeenCalledWith('PD-2026-00001', 'Huỷ Decision')
  })

  // Chống tái phát: component KHÔNG gate action bằng `workflow_state === 'X'`,
  // KHÔNG còn hằng client TRANSITIONS_BY_STATE.
  it('(g) source KHÔNG hardcode gate workflow_state === và KHÔNG còn TRANSITIONS_BY_STATE', () => {
    const src = viewSource as string
    expect(src).not.toMatch(/TRANSITIONS_BY_STATE/)
    expect(src).not.toMatch(/workflow_state\s*===/)
  })
})
