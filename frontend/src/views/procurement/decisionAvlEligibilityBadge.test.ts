// TDD/regression — IMM-03 cổng eligibility AVL (VR-03-05 / NĐ98), phía FE.
//
// Hợp đồng FE (ZERO shape-change): `c.in_avl` (0|1) do BE quyết định —
// FE chỉ BIND VERBATIM, KHÔNG tự tính lại eligibility từ valid_to/workflow_state.
//
// Bài test chốt 2 bất biến FE:
//   1. Badge "Đã được duyệt"/"Chưa được duyệt" bám đúng cờ BE — supplier có AVL
//      Approved nhưng valid_to hết hạn (BE trả in_avl=0 nhờ predicate live) phải
//      hiển thị "Chưa được duyệt", KHÔNG hardcode "Đã được duyệt".
//   2. Khi submit trao thầu cho NCC AVL hết hạn → BE raise ServiceError
//      BUSINESS_RULE (VR-03-05). FE surface qua notification-contract
//      (notify.fromError), KHÔNG nuốt lỗi, KHÔNG window.confirm, KHÔNG leak raw
//      'Approved/Conditional/Expired'.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { ApiError, ErrorCode } from '@/api/errors'
import type { DecisionDoc, EvalDoc } from '@/types/imm03'

// ─── API mocks ────────────────────────────────────────────────────────────────
const getDecisionSpy = vi.fn<() => Promise<DecisionDoc>>()
const getEvaluationSpy = vi.fn<() => Promise<EvalDoc>>()
const awardDecisionSpy = vi.fn()

vi.mock('@/api/imm03', () => ({
  getDecision: () => getDecisionSpy(),
  getEvaluation: () => getEvaluationSpy(),
  awardDecision: (...a: unknown[]) => awardDecisionSpy(...a),
  recordContract: vi.fn(),
  transitionDecisionWorkflow: vi.fn(),
}))

// ─── notification-contract mock (confirm + fromError) ───────────────────────────
const confirmSpy = vi.fn<() => Promise<boolean>>()
const fromErrorSpy = vi.fn()
const showSpy = vi.fn()
vi.mock('@/composables/useNotify', () => ({
  useNotify: () => ({
    confirm: () => confirmSpy(),
    fromError: (e: unknown) => fromErrorSpy(e),
    show: showSpy,
    fromOk: vi.fn(),
  }),
}))

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { id: 'PD-0001' } }),
}))

import DecisionDetailView from './DecisionDetailView.vue'

// AVL hết hạn nhưng workflow_state vẫn 'Approved' (chưa bị scheduler flip).
// BE predicate live đã trả in_avl=0 → FE phải bám cờ này.
const DECISION: DecisionDoc = {
  name: 'PD-0001',
  spec_ref: 'TS-0001',
  evaluation_ref: 'VE-0001',
  winner_supplier: '',
  workflow_state: 'Pending Approval',
  procurement_method: 'Đấu thầu rộng rãi',
  creation: '2026-06-01',
}

const EVAL: EvalDoc = {
  name: 'VE-0001',
  spec_ref: 'TS-0001',
  draft_date: '2026-06-01',
  candidates: [
    // S1: AVL còn hiệu lực → BE in_avl=1
    { idx: 1, supplier: 'S-LIVE', supplier_name: 'NCC Còn Hạn', in_avl: 1, weighted_score: 0.9 },
    // S2: AVL Approved NHƯNG valid_to hết hạn → BE in_avl=0 (predicate live)
    { idx: 2, supplier: 'S-STALE', supplier_name: 'NCC Hết Hạn', in_avl: 0, weighted_score: 0.8 },
  ],
  quotations: [],
  criteria: [],
}

const stubs = { teleport: true }

async function mountView() {
  const wrapper = mount(DecisionDetailView, {
    props: { id: 'PD-0001' },
    global: { stubs, mocks: { $router: { back: vi.fn(), push: vi.fn() } } },
  })
  await flushPromises()
  return wrapper
}

describe('IMM-03 DecisionDetailView — AVL eligibility badge bám cờ BE (verbatim)', () => {
  let windowConfirmSpy: ReturnType<typeof vi.spyOn>

  beforeEach(() => {
    setActivePinia(createPinia())
    getDecisionSpy.mockReset().mockResolvedValue(DECISION)
    getEvaluationSpy.mockReset().mockResolvedValue(EVAL)
    awardDecisionSpy.mockReset()
    confirmSpy.mockReset().mockResolvedValue(true)
    fromErrorSpy.mockReset()
    showSpy.mockReset()
    windowConfirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true)
  })

  it('option NCC trúng thầu render nhãn AVL VERBATIM theo cờ BE (in_avl)', async () => {
    const wrapper = await mountView()
    const optionTexts = wrapper.findAll('option').map(o => o.text())

    // NCC còn hạn (in_avl=1) → "Đã được duyệt"
    const live = optionTexts.find(t => t.includes('NCC Còn Hạn'))
    expect(live).toBeTruthy()
    expect(live).toContain('Đã được duyệt')

    // NCC Approved-nhưng-hết-hạn (BE đã trả in_avl=0) → "Chưa được duyệt",
    // KHÔNG hardcode "Đã được duyệt" dù workflow_state là Approved.
    const stale = optionTexts.find(t => t.includes('NCC Hết Hạn'))
    expect(stale).toBeTruthy()
    expect(stale).toContain('Chưa được duyệt')
    expect(stale).not.toContain('Đã được duyệt')
  })

  it('KHÔNG leak raw EN state (Approved/Conditional/Expired) ra UI', async () => {
    const wrapper = await mountView()
    const html = wrapper.html()
    expect(html).not.toMatch(/\bApproved\b/)
    expect(html).not.toMatch(/\bConditional\b/)
    expect(html).not.toMatch(/\bExpired\b/)
  })

  it('FE KHÔNG tự tính lại eligibility: badge đảo theo cờ BE chứ không theo state', async () => {
    // Đổi cờ BE: cùng supplier nhưng giờ in_avl=1 → badge phải đổi sang "Đã được duyệt".
    getEvaluationSpy.mockResolvedValue({
      ...EVAL,
      candidates: [{ idx: 1, supplier: 'S-STALE', supplier_name: 'NCC X', in_avl: 1, weighted_score: 0.8 }],
    })
    const wrapper = await mountView()
    const opt = wrapper.findAll('option').map(o => o.text()).find(t => t.includes('NCC X'))
    expect(opt).toContain('Đã được duyệt')
  })
})

describe('IMM-03 DecisionDetailView — VR-03-05 surface qua notification-contract', () => {
  let windowConfirmSpy: ReturnType<typeof vi.spyOn>

  beforeEach(() => {
    setActivePinia(createPinia())
    getDecisionSpy.mockReset().mockResolvedValue(DECISION)
    getEvaluationSpy.mockReset().mockResolvedValue(EVAL)
    awardDecisionSpy.mockReset()
    confirmSpy.mockReset().mockResolvedValue(true)
    fromErrorSpy.mockReset()
    showSpy.mockReset()
    windowConfirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true)
  })

  async function fillAndAward(wrapper: Awaited<ReturnType<typeof mountView>>) {
    // chọn winner = NCC hết hạn + điền form tối thiểu để canSubmitAward = true
    const selects = wrapper.findAll('select')
    const winnerSelect = selects[0]
    await winnerSelect.setValue('S-STALE')
    // awarded_price giờ là <CurrencyInput> (type=text, nhóm hàng nghìn) → tìm theo aria-label
    const priceInput = wrapper.find('input[aria-label="Giá trúng thầu"]')
    await priceInput.setValue('100000000')
    const fundingSelect = selects.find(s => s.findAll('option').some(o => o.text() === 'NSNN'))
    await fundingSelect!.setValue('NSNN')
    const emailInput = wrapper.find('input[type="email"]')
    await emailInput.setValue('giamdoc@benhvien.vn')
    await flushPromises()
    // submit form trao thầu
    const awardForm = wrapper.findAll('form')[0]
    await awardForm.trigger('submit')
    await flushPromises()
  }

  it('submit trao thầu NCC AVL hết hạn → BE raise VR-03-05 → notify.fromError được gọi, KHÔNG window.confirm, KHÔNG nuốt lỗi', async () => {
    const vr0305 = new ApiError(
      'Nhà cung cấp trúng thầu không nằm trong Danh sách NCC được duyệt (AVL) còn hiệu lực (VR-03-05).',
      { code: ErrorCode.BUSINESS_RULE, httpStatus: 422 },
    )
    awardDecisionSpy.mockRejectedValue(vr0305)

    const wrapper = await mountView()
    await fillAndAward(wrapper)

    // dùng BaseModal/notify.confirm — KHÔNG window.confirm
    expect(windowConfirmSpy).not.toHaveBeenCalled()
    expect(confirmSpy).toHaveBeenCalledTimes(1)
    // API thực sự được gọi (cổng nằm ở BE, không phải FE đoán)
    expect(awardDecisionSpy).toHaveBeenCalledTimes(1)
    // lỗi VR-03-05 surface qua notification-contract, KHÔNG bị nuốt
    expect(fromErrorSpy).toHaveBeenCalledTimes(1)
    const passed = fromErrorSpy.mock.calls[0][0] as ApiError
    expect(passed).toBeInstanceOf(ApiError)
    expect(passed.isBusinessError).toBe(true)
  })

  it('happy-path: BE PASS (in_avl hợp lệ) → award gọi 1 lần, KHÔNG fromError', async () => {
    awardDecisionSpy.mockResolvedValue({ name: 'PD-0001', workflow_state: 'Awarded' })
    const wrapper = await mountView()
    await fillAndAward(wrapper)

    expect(awardDecisionSpy).toHaveBeenCalledTimes(1)
    expect(fromErrorSpy).not.toHaveBeenCalled()
    expect(windowConfirmSpy).not.toHaveBeenCalled()
  })

  it('hủy ở modal xác nhận → KHÔNG gọi award', async () => {
    confirmSpy.mockResolvedValue(false)
    awardDecisionSpy.mockResolvedValue({ name: 'PD-0001', workflow_state: 'Awarded' })
    const wrapper = await mountView()
    await fillAndAward(wrapper)

    expect(confirmSpy).toHaveBeenCalledTimes(1)
    expect(awardDecisionSpy).not.toHaveBeenCalled()
  })
})
