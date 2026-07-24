// TDD (FE) — BR-06-08: chống nghiệm-thu-giả buổi đào tạo ở SessionDetailView.
//
// 3 hành vi bắt buộc (RED-first):
//   1. Nút "Hoàn thành" DISABLED + hint 'Chưa chấm điểm học viên nào' khi buổi
//      In-Progress có học viên nhưng CHƯA nhập điểm (theory/practical) cho ai.
//      Có ≥1 học viên được chấm → nút ENABLED, hint ẩn.
//   2. Complete THÀNH CÔNG → toast phản ánh scored_count/competencies_created THỰC
//      từ BE (KHÔNG số dòng local — anti success-giả); payload chỉ gồm học viên đã
//      chấm (control không dead — GATE-6c: param phát đi == UI-selection).
//   3. Reject-path (BE raise VALIDATION BR-06-08) → surface lỗi qua notify.fromError,
//      KHÔNG toast success, KHÔNG reload/điều hướng (fetchSession không được gọi).
//
// Dùng useApi THẬT (không mock) để kiểm luồng success/error thực; chỉ mock
// useToast + useNotify (spy) + api/imm06.completeSession (controllable).
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'
import { ApiError, ErrorCode } from '@/api/errors'

vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())

vi.mock('pinia', async (importOriginal) => {
  const actual = await importOriginal<typeof import('pinia')>()
  return { ...actual, storeToRefs: (s: unknown) => s }
})

// Đủ mọi quyền training (canManage = training.submit, canConduct = training.write).
vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({ can: () => true }),
}))

// Toast + Notify spy — dùng CHUNG cho cả view (toast.success dynamic) và useApi thật.
const toastSpy = { success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn(), show: vi.fn() }
vi.mock('@/composables/useToast', () => ({ useToast: () => toastSpy }))
const notifySpy = { fromError: vi.fn(), fromOk: vi.fn(), show: vi.fn(), confirm: vi.fn() }
vi.mock('@/composables/useNotify', () => ({ useNotify: () => notifySpy }))

// api/imm06 — completeSession controllable; các action khác no-op.
const completeSessionMock = vi.fn()
vi.mock('@/api/imm06', () => ({
  confirmSession: vi.fn(), startSession: vi.fn(),
  completeSession: (...args: unknown[]) => completeSessionMock(...args),
  cancelSession: vi.fn(), verifySession: vi.fn(), closeSession: vi.fn(),
  createSession: vi.fn(), enrollParticipants: vi.fn(), removeParticipant: vi.fn(),
}))

type Session = Record<string, unknown>
const currentSession = ref<Session | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)
const fetchSession = vi.fn().mockResolvedValue(undefined)
vi.mock('@/stores/imm06', () => ({
  useImm06Store: () => ({ currentSession, loading, error, fetchSession }),
}))

import SessionDetailView from './SessionDetailView.vue'

type Part = Record<string, unknown>
function participant(over: Part = {}): Part {
  return {
    name: 'row-1', user: 'u1', user_full_name: 'Nguyễn A',
    department: null, role_at_session: 'Operator', attendance_pct: 0,
    // CONTRACT THẬT: get_session trả 0 (child DocType Float ⇒ DB NOT NULL DEFAULT 0) +
    // overall_result '' cho học viên CHƯA chấm — KHÔNG null. Dùng 0 (không null) để tránh
    // false-green: gate PHẢI phân biệt default-0 (chưa gõ) với user-entered-0 (đã gõ) qua
    // dirty-tracking, KHÔNG suy "đã chấm" từ giá trị 0.
    theory_score: 0, practical_score: 0, overall_result: '',
    certificate_issued: 0, retake_required: 0, competency_record: null, remarks: '',
    ...over,
  }
}

function makeSession(participants: Part[]): Session {
  return {
    name: 'TS-2026-00042',
    training_program: 'TPRG-0001',
    training_program_name: 'Vận hành máy thở',
    session_date: '2026-07-10',
    session_type: 'Onsite',
    duration_planned_hours: 8,
    workflow_state: 'In Progress',
    allowed_transitions: ['Completed'],
    participants,
  }
}

const stubs = {
  PageHeader: { template: '<div><slot /><slot name="actions" /></div>' },
  StatusBadge: true,
  SmartSelect: true,
  ApproverSelect: true,
  DateInput: true,
}

async function mountDetail() {
  const w = mount(SessionDetailView, {
    props: { name: 'TS-2026-00042' },
    global: { stubs, mocks: { $t: (k: string) => k } },
  })
  await flushPromises()
  return w
}

beforeEach(() => {
  currentSession.value = null
  loading.value = false
  error.value = null
  fetchSession.mockClear()
  completeSessionMock.mockReset()
  toastSpy.success.mockClear()
  notifySpy.fromError.mockClear()
})

// ─── 1. Gate nút Hoàn thành theo "đã chấm điểm ≥1 học viên" ───────────────────
describe('BR-06-08 gate — nút "Hoàn thành" disabled khi chưa chấm điểm ai', () => {
  it('In Progress + học viên điểm mặc-định 0 (CHƯA gõ) → cta-complete disabled + hint hiển thị', async () => {
    // Đây là ca RED-đã-chứng-minh của round-4: dữ liệu THẬT theory_score:0. Trước fix,
    // _isScored(0)===true ⇒ nút KHÔNG disable (gate defeated). Sau fix dirty-tracking ⇒ disable.
    currentSession.value = makeSession([participant(), participant({ name: 'row-2', user: 'u2' })])
    const w = await mountDetail()
    const btn = w.find('[data-testid="cta-complete"]')
    expect(btn.exists()).toBe(true)
    expect(btn.attributes('disabled')).toBeDefined()
    expect(w.find('[data-testid="complete-score-hint"]').exists()).toBe(true)
    expect(w.find('[data-testid="complete-score-hint"]').text()).toContain('Chưa chấm điểm học viên nào')
  })

  it('instructor NHẬP điểm lý thuyết cho 1 học viên → cta-complete ENABLED + hint ẩn', async () => {
    currentSession.value = makeSession([
      participant(),
      participant({ name: 'row-2', user: 'u2' }),
    ])
    const w = await mountDetail()
    // gate mặc-định vẫn disabled (chưa gõ)
    expect(w.find('[data-testid="cta-complete"]').attributes('disabled')).toBeDefined()
    // instructor gõ 80 vào ô lý thuyết của u1 → dirty → ENABLED
    await w.find('[data-testid="theory-score-u1"]').setValue(80)
    expect(w.find('[data-testid="cta-complete"]').attributes('disabled')).toBeUndefined()
    expect(w.find('[data-testid="complete-score-hint"]').exists()).toBe(false)
  })

  it('phân biệt user-entered-0 với default-0: GÕ 0 → đã chấm (ENABLED); 0 mặc-định → chưa chấm (disabled)', async () => {
    currentSession.value = makeSession([participant()])
    const w = await mountDetail()
    // 0 mặc-định (chưa gõ) → disabled
    expect(w.find('[data-testid="cta-complete"]').attributes('disabled')).toBeDefined()
    // instructor GÕ 0 (điểm thật = trượt hoàn toàn) vào ô thực hành → dirty → ENABLED
    await w.find('[data-testid="practical-score-u1"]').setValue(0)
    expect(w.find('[data-testid="cta-complete"]').attributes('disabled')).toBeUndefined()
  })
})

// ─── 2. Complete thành công → toast THỰC + payload chỉ học viên đã chấm ────────
describe('BR-06-08 success — toast phản ánh scored_count/competencies_created THỰC', () => {
  it('gửi CHỈ học viên đã chấm; toast dùng số THỰC từ BE (không phải số dòng local)', async () => {
    currentSession.value = makeSession([
      participant({ user: 'u1' }),
      participant({ name: 'row-2', user: 'u2' }),
      participant({ name: 'row-3', user: 'u3' }), // để nguyên default-0, KHÔNG gõ → KHÔNG gửi
    ])
    // BE trả số THỰC KHÁC số dòng local (2 gửi lên) → chứng minh FE bind giá trị BE.
    completeSessionMock.mockResolvedValue({
      name: 'TS-2026-00042', workflow_state: 'Completed',
      scored_count: 2, competencies_created: ['ACC-UC-2026-0001'],
    })
    const w = await mountDetail()
    // instructor nhập điểm cho u1 + u2; u3 để nguyên default-0 (chưa chấm).
    await w.find('[data-testid="theory-score-u1"]').setValue(80)
    await w.find('[data-testid="practical-score-u1"]').setValue(90)
    await w.find('[data-testid="theory-score-u2"]').setValue(60)
    await w.find('[data-testid="practical-score-u2"]').setValue(50)
    fetchSession.mockClear() // bỏ lần fetch khi onMounted → chỉ đo reload sau complete
    await w.find('[data-testid="cta-complete"]').trigger('click')
    await flushPromises()

    // Payload: chỉ 2 học viên đã chấm (u1, u2) — KHÔNG u3 (default-0, chưa gõ).
    expect(completeSessionMock).toHaveBeenCalledTimes(1)
    const sent = completeSessionMock.mock.calls[0][1] as Part[]
    expect(sent.map((p) => p.user).sort()).toEqual(['u1', 'u2'])

    // Toast dùng scored_count(2) + competencies_created.length(1) từ BE.
    expect(toastSpy.success).toHaveBeenCalledTimes(1)
    const msg = toastSpy.success.mock.calls[0][0] as string
    expect(msg).toContain('2 học viên')
    expect(msg).toContain('1 chứng nhận')
    expect(fetchSession).toHaveBeenCalled()
  })
})

// ─── 3. Reject-path — BE raise VALIDATION → surface lỗi, KHÔNG success-giả ─────
describe('BR-06-08 reject — BE raise VALIDATION → error surfaced, không toast success', () => {
  it('completeSession reject VALIDATION → notify.fromError, KHÔNG toast.success, KHÔNG reload', async () => {
    currentSession.value = makeSession([participant()])
    const berr = new ApiError(
      'Phải chấm điểm ít nhất 1 học viên trước khi hoàn thành buổi học (BR-06-08)',
      ErrorCode.VALIDATION, 400,
    )
    completeSessionMock.mockRejectedValue(berr)
    const w = await mountDetail()
    await w.find('[data-testid="theory-score-u1"]').setValue(75) // gõ điểm → gate mở
    fetchSession.mockClear() // bỏ lần fetch khi onMounted → reject KHÔNG được reload thêm
    await w.find('[data-testid="cta-complete"]').trigger('click')
    await flushPromises()

    expect(notifySpy.fromError).toHaveBeenCalledTimes(1)
    expect((notifySpy.fromError.mock.calls[0][0] as ApiError).message).toContain('BR-06-08')
    expect(toastSpy.success).not.toHaveBeenCalled()
    expect(fetchSession).not.toHaveBeenCalled()
  })
})
