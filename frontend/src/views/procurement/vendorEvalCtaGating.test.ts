// TDD / regression guard — GATE-8 / LL-FE-51: server-driven CTA cho Đánh giá nhà
// cung cấp (IMM-03 Vendor Evaluation).
//
// Nút chuyển-trạng-thái ở VendorEvalDetailView gate theo `allowed_transitions` do BE
// emit (SoT = get_evaluation → _EVAL_VALID_TRANSITIONS, parity get_decision, khớp
// fixture 'IMM-03 Vendor Eval Workflow') — KHÔNG hardcode `workflow_state === 'X'`
// và KHÔNG còn hằng client TRANSITIONS_BY_STATE (từng khiến QTV/Commissioning
// Manager thấy/bấm action không đúng quyền hoặc lệch khi workflow đổi).
//
// Ánh xạ action (khớp EXACT workflow.json):
//   Draft              --Mở RFQ------------> Open RFQ
//   Open RFQ           --Nhận báo giá xong-> Quotation Received
//   Open RFQ           --Huỷ Eval----------> Cancelled
//   Quotation Received --Hoàn tất chấm điểm-> Evaluated
//   Quotation Received --Huỷ Eval----------> Cancelled
//   Evaluated / Cancelled → [] (trạng thái cuối, KHÔNG nút)
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import type { EvalDoc } from '@/types/imm03'
// eslint-disable-next-line @typescript-eslint/no-explicit-any
import viewSource from './VendorEvalDetailView.vue?raw'

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { id: 'VE-2026-00001' } }),
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
const getEvaluationSpy = vi.fn()
const transitionSpy = vi.fn().mockResolvedValue({ name: 'VE-2026-00001', workflow_state: 'Cancelled', docstatus: 0 })
vi.mock('@/api/imm03', () => ({
  // store.fetchEvaluation → api.getEvaluation
  getEvaluation: (...a: unknown[]) => getEvaluationSpy(...a),
  // direct imports trong view
  transitionEvalWorkflow: (...a: unknown[]) => transitionSpy(...a),
  scoreEvaluation: vi.fn().mockResolvedValue({ weighted_scores: {}, recommended: '' }),
  addCandidate: vi.fn().mockResolvedValue({ row_count: 0, in_avl: 0 }),
  submitQuotations: vi.fn().mockResolvedValue({ quotations_count: 0 }),
  getVendorScorecard: vi.fn().mockResolvedValue({}),
  listVendorProfiles: vi.fn().mockResolvedValue({ items: [], total: 0, page: 1, page_size: 100 }),
}))

import VendorEvalDetailView from './VendorEvalDetailView.vue'

function makeEval(over: Partial<EvalDoc> = {}): EvalDoc {
  return {
    name: 'VE-2026-00001', spec_ref: 'TS-1', draft_date: '2026-06-01',
    candidates: [], quotations: [], criteria: [],
    workflow_state: 'Quotation Received', docstatus: 0,
    allowed_transitions: [],
    ...over,
  } as EvalDoc
}

async function mountDetail(evalDoc: EvalDoc) {
  getEvaluationSpy.mockResolvedValue(evalDoc)
  const w = mount(VendorEvalDetailView, {
    props: { id: 'VE-2026-00001' },
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
  getEvaluationSpy.mockReset()
  transitionSpy.mockClear()
  confirmSpy.mockClear()
})

describe('IMM-03 VendorEvalDetailView — CTA server-driven theo allowed_transitions', () => {
  it('(a) Quotation Received + allowed=[Hoàn tất chấm điểm, Huỷ Eval] → render đúng 2 nút', async () => {
    const w = await mountDetail(makeEval({
      workflow_state: 'Quotation Received',
      allowed_transitions: ['Hoàn tất chấm điểm', 'Huỷ Eval'],
    }))
    expect(workflowActionValues(w)).toEqual(['Hoàn tất chấm điểm', 'Huỷ Eval'])
  })

  // GATE-6c (chống dead-control): param transition phát đi == UI-selection (raw
  // action value, KHÔNG nhãn hiển thị suy diễn).
  it('(b) click nút "Huỷ Eval" → transitionEvalWorkflow(name, "Huỷ Eval")', async () => {
    const w = await mountDetail(makeEval({
      workflow_state: 'Quotation Received',
      allowed_transitions: ['Hoàn tất chấm điểm', 'Huỷ Eval'],
    }))
    const btn = w.findAll('[data-testid="workflow-action"]').find(
      (b) => b.attributes('data-action') === 'Huỷ Eval')
    expect(btn).toBeTruthy()
    await btn!.trigger('click')
    await flushPromises()
    expect(confirmSpy).toHaveBeenCalledTimes(1)
    expect(transitionSpy).toHaveBeenCalledWith('VE-2026-00001', 'Huỷ Eval')
  })

  it('(c) Evaluated + allowed=[] → 0 nút transition (trạng thái cuối)', async () => {
    const w = await mountDetail(makeEval({
      workflow_state: 'Evaluated', allowed_transitions: [], docstatus: 1,
    }))
    expect(workflowActionValues(w)).toEqual([])
  })

  it('(d) allowed_transitions vắng (BE chưa reload) → 0 nút (degrade an toàn, KHÔNG client-map)', async () => {
    const e = makeEval({ workflow_state: 'Quotation Received' })
    delete (e as { allowed_transitions?: string[] }).allowed_transitions
    const w = await mountDetail(e)
    expect(workflowActionValues(w)).toEqual([])
  })

  // Chống tái phát: component KHÔNG gate action bằng `workflow_state === 'X'`,
  // KHÔNG còn hằng client TRANSITIONS_BY_STATE.
  it('(e) source KHÔNG hardcode gate workflow_state === và KHÔNG còn TRANSITIONS_BY_STATE', () => {
    const src = viewSource as string
    expect(src).not.toMatch(/TRANSITIONS_BY_STATE/)
    expect(src).not.toMatch(/workflow_state\s*===/)
  })
})
