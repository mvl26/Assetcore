// TDD-FE-12 (AC-CR-83 / AC-9) — lỗi hồ sơ RCA phải hiện ĐÚNG Ô, không phải toast chung.
//
// BỐI CẢNH: `submit_rca` trước đây để 3 ràng buộc hồ sơ (5-Why · phân công · hoàn
// tất) thoát ra HTTP-417 THÔ (frappe.throw trần trong controller) ⇒ FE chỉ nhận 1
// câu chung, người dùng KHÔNG biết ô nào sai. Sau AC-CR-83 lỗi về trong envelope
// kèm `fields = {<khoá>: <câu tiếng Việt>}`.
//
// Test này RENDER THẬT (mount) — không phải unit computed (LL-FE-46):
//   • `five_why_steps.3` → câu VI nằm ngay dòng «Why 3» (liên kết qua aria-describedby)
//   • sửa ô Why 3 ⇒ lỗi biến mất
//   • `root_cause` → dưới ô Nguyên nhân gốc, KHÔNG dưới dòng Why nào
//   • `corrective_action` (TÊN THAM SỐ GHI, không phải `corrective_action_summary`)
//   • `assigned_to` → banner (màn này không có ô phân công)
//   • khoá LẠ vẫn hiện (banner gom) — không nuốt im lặng
//   • DOM KHÔNG chứa 'Traceback' / 'ValidationError' / '_server_messages'
//   • nút «Hoàn thành» KHÔNG biến mất sau lỗi
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises, type VueWrapper } from '@vue/test-utils'
import { ref } from 'vue'
import { ApiError, ErrorCode } from '@/api/errors'
import { MSG } from '@/locales/messages'

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { id: 'RCA-2026-0001' }, query: {}, path: '/rca/RCA-2026-0001' }),
  useRouter: () => ({ push: vi.fn() }),
}))

type Rca = Record<string, unknown>
const currentRca = ref<Rca | null>(null)
const getRcaMock = vi.fn(() => Promise.resolve(currentRca.value))
const submitRcaMock = vi.fn()
const startRcaMock = vi.fn()
const cancelRcaMock = vi.fn()
vi.mock('@/api/imm12', () => ({
  getRca: (...a: unknown[]) => getRcaMock(...(a as [])),
  submitRca: (...a: unknown[]) => submitRcaMock(...(a as [])),
  startRca: (...a: unknown[]) => startRcaMock(...(a as [])),
  cancelRca: (...a: unknown[]) => cancelRcaMock(...(a as [])),
}))

import RCADetailView from '@/views/incident/RCADetailView.vue'

// Câu tiếng Việt do BE curate (registry MSG) — FE chỉ hiển thị lại nguyên văn.
const VI_WHY_3 = 'Bước Why 3 chưa có câu trả lời — vui lòng điền trước khi hoàn tất.'
const VI_STEPS = 'Hồ sơ 5-Why cần đủ 5 bước, hiện chỉ có 3 bước.'
const VI_ROOT = 'Cần nhập nguyên nhân gốc rễ để hoàn thành phân tích nguyên nhân gốc.'
const VI_CORRECTIVE = 'Cần nhập hành động khắc phục để hoàn thành phân tích nguyên nhân gốc.'
const VI_ASSIGNEE = 'Hồ sơ chưa được phân công người phụ trách phân tích.'

/** Envelope lỗi Decision-B đã hydrate (helpers.ts) — đúng shape FE nhận thật. */
function envelopeError(
  messageCode: string,
  fields: Record<string, string>,
  message = 'Hồ sơ phân tích nguyên nhân gốc chưa hợp lệ.',
): ApiError {
  return new ApiError(message, {
    code: ErrorCode.BUSINESS_RULE,
    httpStatus: 422,
    messageCode,
    fields,
  })
}

function makeRca(overrides: Rca = {}): Rca {
  return {
    name: 'RCA-2026-0001',
    incident_report: 'INC-2026-00042',
    asset: 'AC-ASSET-0099',
    status: 'RCA In Progress',
    // Server-driven CTA (GATE-8): 'RCA In Progress' → [Completed, Cancelled].
    allowed_transitions: ['Completed', 'Cancelled'],
    can_manage_rca: 1,
    rca_method: '5-Why',
    root_cause: 'Bo nguồn lão hoá',
    corrective_action_summary: 'Thay bo nguồn, hiệu chuẩn lại',
    preventive_action_summary: '',
    rca_notes: '',
    five_why_steps: Array.from({ length: 5 }, (_, i) => ({
      why_number: i + 1,
      why_question: `Why ${i + 1}?`,
      why_answer: `Câu trả lời ${i + 1}`,
    })),
    ...overrides,
  }
}

let wrapper: VueWrapper | null = null
async function mountDetail(rca: Rca = makeRca()): Promise<VueWrapper> {
  currentRca.value = rca
  wrapper = mount(RCADetailView, {
    global: { stubs: { Transition: false }, mocks: { $t: (k: string) => k } },
  }) as VueWrapper
  await flushPromises()
  return wrapper
}

async function clickComplete(w: VueWrapper): Promise<void> {
  await w.find('[data-testid="cta-complete-rca"]').trigger('click')
  await flushPromises()
}

/** Không có bất kỳ lỗi nào gắn vào các dòng Why. */
function whyErrorIds(w: VueWrapper): string[] {
  return [1, 2, 3, 4, 5].filter(n => w.find(`[data-testid="rca-error-why-${n}"]`).exists())
    .map(n => `why-${n}`)
}

function assertNoTechnicalLeak(w: VueWrapper): void {
  const html = w.html()
  expect(html).not.toContain('Traceback')
  expect(html).not.toContain('ValidationError')
  expect(html).not.toContain('_server_messages')
}

beforeEach(() => {
  currentRca.value = null
  getRcaMock.mockClear()
  submitRcaMock.mockReset()
  submitRcaMock.mockResolvedValue({ name: 'RCA-2026-0001', status: 'Completed' })
  startRcaMock.mockReset()
  cancelRcaMock.mockReset()
})

afterEach(() => {
  wrapper?.unmount()
  wrapper = null
  document.body.replaceChildren()
})

describe('AC-9 — lỗi 5-Why hiện ngay dòng Why tương ứng', () => {
  it('fields["five_why_steps.3"] → câu VI dưới ĐÚNG dòng Why 3 (liên kết aria)', async () => {
    submitRcaMock.mockRejectedValue(
      envelopeError(MSG.IMM12_RCA_FIVE_WHY_INCOMPLETE, { 'five_why_steps.3': VI_WHY_3 }),
    )
    const w = await mountDetail()
    await clickComplete(w)

    const errNode = w.find('[data-testid="rca-error-why-3"]')
    expect(errNode.exists()).toBe(true)
    expect(errNode.text()).toBe(VI_WHY_3)
    // "Ngay dòng Why 3" = ô nhập của bước 3 trỏ tới chính node lỗi đó.
    const ta = w.find('#why-a-3')
    expect(ta.attributes('aria-describedby')).toBe('why-a-err-3')
    expect(ta.attributes('aria-invalid')).toBe('true')
    expect(errNode.attributes('id')).toBe('why-a-err-3')
    // Chỉ dòng 3 — không nhoè sang dòng khác.
    expect(whyErrorIds(w)).toEqual(['why-3'])
  })

  it('nút «Hoàn thành» KHÔNG biến mất sau lỗi + DOM không lộ chuỗi kỹ thuật', async () => {
    submitRcaMock.mockRejectedValue(
      envelopeError(MSG.IMM12_RCA_FIVE_WHY_INCOMPLETE, { 'five_why_steps.3': VI_WHY_3 }),
    )
    const w = await mountDetail()
    await clickComplete(w)

    expect(w.find('[data-testid="cta-complete-rca"]').exists()).toBe(true)
    assertNoTechnicalLeak(w)
  })

  it('sửa ô Why 3 ⇒ lỗi của dòng đó biến mất (không dính lại)', async () => {
    submitRcaMock.mockRejectedValue(
      envelopeError(MSG.IMM12_RCA_FIVE_WHY_INCOMPLETE, { 'five_why_steps.3': VI_WHY_3 }),
    )
    const w = await mountDetail()
    await clickComplete(w)
    expect(w.find('[data-testid="rca-error-why-3"]').exists()).toBe(true)

    await w.find('#why-a-3').setValue('Do tụ lọc phồng sau 6 năm chạy liên tục')
    await flushPromises()
    expect(w.find('[data-testid="rca-error-why-3"]').exists()).toBe(false)
    expect(w.find('#why-a-3').attributes('aria-invalid')).toBeUndefined()
  })

  it('thiếu BƯỚC (khoá trần five_why_steps) → lỗi ở đầu khối, không gán nhầm 1 dòng', async () => {
    submitRcaMock.mockRejectedValue(
      envelopeError(MSG.IMM12_RCA_FIVE_WHY_INCOMPLETE, { five_why_steps: VI_STEPS }),
    )
    const w = await mountDetail()
    await clickComplete(w)

    expect(w.find('[data-testid="rca-error-five-why-steps"]').text()).toBe(VI_STEPS)
    expect(whyErrorIds(w)).toEqual([])
  })
})

describe('AC-3 — 2 lỗi có sẵn giữ message_code + THÊM fields', () => {
  it('root_cause → dưới ô Nguyên nhân gốc, KHÔNG dưới dòng Why nào', async () => {
    submitRcaMock.mockRejectedValue(
      envelopeError(MSG.IMM12_RCA_ROOT_CAUSE_REQUIRED, { root_cause: VI_ROOT }),
    )
    const w = await mountDetail()
    await clickComplete(w)

    const node = w.find('[data-testid="rca-error-root-cause"]')
    expect(node.text()).toBe(VI_ROOT)
    expect(w.find('#rca-root-cause').attributes('aria-describedby')).toBe('rca-root-cause-err')
    expect(whyErrorIds(w)).toEqual([])
    expect(w.find('[data-testid="rca-error-corrective-action"]').exists()).toBe(false)
  })

  it('corrective_action (TÊN THAM SỐ GHI) → dưới ô Hành động khắc phục', async () => {
    submitRcaMock.mockRejectedValue(
      envelopeError(MSG.IMM12_RCA_CORRECTIVE_REQUIRED, { corrective_action: VI_CORRECTIVE }),
    )
    const w = await mountDetail()
    await clickComplete(w)

    expect(w.find('[data-testid="rca-error-corrective-action"]').text()).toBe(VI_CORRECTIVE)
    expect(w.find('#rca-corrective').attributes('aria-describedby')).toBe('rca-corrective-err')
    expect(w.find('[data-testid="rca-error-root-cause"]').exists()).toBe(false)
  })

  it('khoá ĐỌC `corrective_action_summary` (nếu BE lỡ dùng) vẫn PHẢI hiện — không nuốt im lặng', async () => {
    submitRcaMock.mockRejectedValue(
      envelopeError(MSG.IMM12_RCA_CORRECTIVE_REQUIRED, { corrective_action_summary: VI_CORRECTIVE }),
    )
    const w = await mountDetail()
    await clickComplete(w)

    // Không gắn được vào ô nào → banner gom (người dùng vẫn đọc được lý do).
    expect(w.find('[data-testid="rca-error-unmapped"]').text()).toBe(VI_CORRECTIVE)
  })
})

describe('AC-6 — phân công người phụ trách: banner (màn RCA không có ô nhập)', () => {
  it('fields.assigned_to → banner tiếng Việt, KHÔNG rơi vào ô Why/Nguyên nhân', async () => {
    submitRcaMock.mockRejectedValue(
      envelopeError(MSG.IMM12_RCA_ASSIGNEE_REQUIRED, { assigned_to: VI_ASSIGNEE }),
    )
    const w = await mountDetail()
    await clickComplete(w)

    expect(w.find('[data-testid="rca-error-assigned-to"]').text()).toBe(VI_ASSIGNEE)
    expect(whyErrorIds(w)).toEqual([])
    expect(w.find('[data-testid="rca-error-root-cause"]').exists()).toBe(false)
  })
})

describe('FE-3 — pre-gate client MIRROR predicate BE (không phải luật thứ hai)', () => {
  it('còn ô Why trống ⇒ nút «Hoàn thành» disabled + lý do VI hiện rõ (không chỉ tooltip)', async () => {
    const rca = makeRca()
    const steps = rca.five_why_steps as Array<{ why_number: number; why_answer: string }>
    steps[2].why_answer = ''
    const w = await mountDetail(rca)

    const btn = w.find('[data-testid="cta-complete-rca"]')
    expect(btn.exists()).toBe(true)
    expect(btn.attributes('disabled')).toBeDefined()
    const hint = w.find('[data-testid="rca-complete-blocked-hint"]')
    expect(hint.exists()).toBe(true)
    expect(hint.text()).toContain('Why 3')
    // Tooltip mirror lý do (a11y: đã có text hiện hình + aria-describedby).
    expect(btn.attributes('title')).toContain('Why 3')
    expect(btn.attributes('aria-describedby')).toBe('rca-complete-blocked-hint')

    await btn.trigger('click')
    await flushPromises()
    expect(submitRcaMock).not.toHaveBeenCalled()
  })

  it('điền nốt ô Why trống ⇒ nút mở lại và submitRca ĐƯỢC gọi (không dead-control)', async () => {
    const rca = makeRca()
    const steps = rca.five_why_steps as Array<{ why_number: number; why_answer: string }>
    steps[2].why_answer = ''
    const w = await mountDetail(rca)

    await w.find('#why-a-3').setValue('Tụ lọc phồng')
    await flushPromises()
    const btn = w.find('[data-testid="cta-complete-rca"]')
    expect(btn.attributes('disabled')).toBeUndefined()
    await btn.trigger('click')
    await flushPromises()
    expect(submitRcaMock).toHaveBeenCalledTimes(1)
    const payload = submitRcaMock.mock.calls[0][0] as { five_why_steps: Array<{ why_answer: string }> }
    expect(payload.five_why_steps[2].why_answer).toBe('Tụ lọc phồng')
  })

  it('phương pháp KHÁC 5-Why ⇒ KHÔNG chặn theo ô Why (server vẫn là SSoT)', async () => {
    const rca = makeRca({ rca_method: 'Fishbone' })
    const steps = rca.five_why_steps as Array<{ why_number: number; why_answer: string }>
    for (const s of steps) s.why_answer = ''
    const w = await mountDetail(rca)

    const btn = w.find('[data-testid="cta-complete-rca"]')
    expect(btn.attributes('disabled')).toBeUndefined()
    await btn.trigger('click')
    await flushPromises()
    expect(submitRcaMock).toHaveBeenCalledTimes(1)
  })
})

describe('AC-8/AC-10 — không có lỗi thì KHÔNG vẽ ô lỗi (chống vacuous)', () => {
  it('submit thành công ⇒ không banner tóm tắt, không lỗi ô nào', async () => {
    const w = await mountDetail()
    await clickComplete(w)

    expect(submitRcaMock).toHaveBeenCalledTimes(1)
    expect(w.find('[data-testid="rca-field-error-summary"]').exists()).toBe(false)
    expect(whyErrorIds(w)).toEqual([])
    expect(w.find('[data-testid="rca-error-root-cause"]').exists()).toBe(false)
  })

  it('lỗi KHÔNG kèm fields (BE cũ/stale) ⇒ vẫn hiện banner chung, không ô nào bị bôi đỏ', async () => {
    submitRcaMock.mockRejectedValue(
      new ApiError('Máy chủ đang bận, vui lòng thử lại.', {
        code: ErrorCode.BUSINESS_RULE, httpStatus: 422,
      }),
    )
    const w = await mountDetail()
    await clickComplete(w)

    expect(w.text()).toContain('Máy chủ đang bận, vui lòng thử lại.')
    expect(w.find('[data-testid="rca-field-error-summary"]').exists()).toBe(false)
    expect(whyErrorIds(w)).toEqual([])
    assertNoTechnicalLeak(w)
  })
})
