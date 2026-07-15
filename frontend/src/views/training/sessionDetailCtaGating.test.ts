// TDD (FE regression guard) — GATE-8 / LL-FE-51: server-driven CTA cho Training Session.
//
// 6 nút workflow ở SessionDetailView (Xác nhận / Bắt đầu / Hoàn thành / Nghiệm thu /
// Đóng / Huỷ) gate theo `allowed_transitions` do BE emit (SSoT =
// _SESSION_VALID_TRANSITIONS trong services/imm06.py) — KHÔNG hardcode
// `state === 'X'`. FE = (capability && allowedTransitions.includes(target)).
//
// RED trước fix (2026-07-09): canStart = state === 'Confirmed' → 'Bắt đầu' ẩn khi
// buổi ở 'Planned' DÙ BE start_training_session cho phép Planned→In Progress
// (= "BE cho phép nhưng UI chặn"). Sau fix: canStart = includes('In Progress') →
// hiện ngay ở Planned.
//
// SSoT map (mirror _SESSION_VALID_TRANSITIONS, khớp workflow JSON "IMM-06 Session
// Workflow" + guard service):
//   Planned      → [Confirmed, In Progress, Cancelled]
//   Confirmed    → [In Progress, Cancelled]
//   In Progress  → [Completed]
//   Completed    → [Verified]
//   Verified     → [Closed]
//   Closed / Cancelled → []  (terminal → 0 CTA)
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'

vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())

// storeToRefs → identity: store mock đã cấp sẵn ref cho currentSession/loading/error.
vi.mock('pinia', async (importOriginal) => {
  const actual = await importOriginal<typeof import('pinia')>()
  return { ...actual, storeToRefs: (s: unknown) => s }
})

// useApi: no-op run + loading tĩnh (test chỉ soi gating, không chạy action).
vi.mock('@/composables/useApi', () => ({
  useApi: () => ({ run: vi.fn(), loading: { value: false } }),
}))

// Capability controllable per test (mặc định: đủ mọi quyền training).
// canManage = can('training.submit'); canConduct = can('training.write').
let canImpl: (c: string) => boolean = () => true
vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({ can: (c: string) => canImpl(c) }),
}))

// api/imm06: stub các hàm action (import tĩnh trong SFC) — không dùng trong gating test.
vi.mock('@/api/imm06', () => ({
  confirmSession: vi.fn(), startSession: vi.fn(), completeSession: vi.fn(),
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

// SSoT transition map (mirror _SESSION_VALID_TRANSITIONS).
const SESSION_TRANSITIONS: Record<string, string[]> = {
  'Planned': ['Confirmed', 'In Progress', 'Cancelled'],
  'Confirmed': ['In Progress', 'Cancelled'],
  'In Progress': ['Completed'],
  'Completed': ['Verified'],
  'Verified': ['Closed'],
  'Closed': [],
  'Cancelled': [],
}

const ALL_CTA = ['cta-confirm', 'cta-start', 'cta-complete', 'cta-verify', 'cta-close', 'cta-cancel']

function makeSession(over: Session = {}): Session {
  const state = (over.workflow_state as string) ?? 'Planned'
  return {
    name: 'TS-2026-00042',
    training_program: 'TPRG-0001',
    training_program_name: 'Vận hành máy thở',
    session_date: '2026-07-10',
    session_type: 'Onsite',
    duration_planned_hours: 8,
    workflow_state: state,
    allowed_transitions: SESSION_TRANSITIONS[state] ?? [],
    participants: [],
    ...over,
  }
}

// PageHeader chứa 6 CTA trong slot #actions → stub PHẢI render slot đó, nếu không
// nút biến mất và test luôn xanh giả (false-negative).
const stubs = {
  PageHeader: { template: '<div><slot /><slot name="actions" /></div>' },
  StatusBadge: true,
  SmartSelect: true,
  ApproverSelect: true,
}

async function mountDetail() {
  const w = mount(SessionDetailView, {
    props: { name: 'TS-2026-00042' },
    global: { stubs, mocks: { $t: (k: string) => k } },
  })
  await flushPromises()
  return w
}

function ctasShown(w: Awaited<ReturnType<typeof mountDetail>>): string[] {
  return ALL_CTA.filter((id) => w.find(`[data-testid="${id}"]`).exists())
}

beforeEach(() => {
  currentSession.value = null
  loading.value = false
  error.value = null
  fetchSession.mockClear()
  canImpl = () => true
})

// ─── FC1: Planned + đủ quyền → Xác nhận + Bắt đầu + Huỷ ───────────────────────
describe('FC1 — Planned (đủ quyền) render đúng tập CTA', () => {
  it('allowed=[Confirmed,In Progress,Cancelled] → cta-confirm + cta-start + cta-cancel; ẩn complete/verify/close', async () => {
    currentSession.value = makeSession({ workflow_state: 'Planned' })
    const w = await mountDetail()
    expect(ctasShown(w).sort()).toEqual(['cta-cancel', 'cta-confirm', 'cta-start'])
    expect(w.find('[data-testid="cta-complete"]').exists()).toBe(false)
    expect(w.find('[data-testid="cta-verify"]').exists()).toBe(false)
    expect(w.find('[data-testid="cta-close"]').exists()).toBe(false)
  })
})

// ─── FC2: desync fix — Bắt đầu hiện ngay ở Planned ───────────────────────────
describe('FC2 — desync fix: "Bắt đầu" gate bằng includes("In Progress")', () => {
  it('buổi Planned (allowed chứa In Progress) + canConduct → cta-start HIỂN THỊ (trước đây ẩn do state!=="Confirmed")', async () => {
    canImpl = (c: string) => c === 'training.write' // chỉ có canConduct
    currentSession.value = makeSession({ workflow_state: 'Planned' })
    const w = await mountDetail()
    expect(w.find('[data-testid="cta-start"]').exists()).toBe(true)
  })

  it('Confirmed cũng cho Bắt đầu (parity không hồi quy)', async () => {
    canImpl = (c: string) => c === 'training.write'
    currentSession.value = makeSession({ workflow_state: 'Confirmed' })
    const w = await mountDetail()
    expect(w.find('[data-testid="cta-start"]').exists()).toBe(true)
  })
})

// ─── FC3: terminal → 0 CTA ───────────────────────────────────────────────────
describe('FC3 — terminal (allowed=[]) → không CTA chuyển-trạng-thái', () => {
  it.each(['Closed', 'Cancelled'])('%s → 0 CTA (read-only)', async (state) => {
    currentSession.value = makeSession({ workflow_state: state })
    const w = await mountDetail()
    expect(ctasShown(w)).toEqual([])
  })
})

// ─── FC4: capability enforce SONG SONG với allowed_transitions ────────────────
describe('FC4 — capability gate song song (không chỉ allowed_transitions)', () => {
  it('In Progress (allowed chứa Completed) NHƯNG thiếu canConduct → cta-complete ẩn', async () => {
    canImpl = (c: string) => c !== 'training.write' // có canManage, thiếu canConduct
    currentSession.value = makeSession({ workflow_state: 'In Progress' })
    const w = await mountDetail()
    expect(w.find('[data-testid="cta-complete"]').exists()).toBe(false)
  })

  it('Completed (allowed chứa Verified) NHƯNG thiếu canManage → cta-verify ẩn', async () => {
    canImpl = (c: string) => c !== 'training.submit' // thiếu canManage
    currentSession.value = makeSession({ workflow_state: 'Completed' })
    const w = await mountDetail()
    expect(w.find('[data-testid="cta-verify"]').exists()).toBe(false)
  })

  it('THIẾU mọi quyền (non-terminal) → 0 CTA', async () => {
    canImpl = () => false
    currentSession.value = makeSession({ workflow_state: 'Planned' })
    const w = await mountDetail()
    expect(ctasShown(w)).toEqual([])
  })
})

// ─── Matrix: tập CTA khớp allowed_transitions cho cả 7 state (đủ quyền) ────────
describe('CTA matrix — khớp _SESSION_VALID_TRANSITIONS (mọi quyền)', () => {
  const EXPECTED: Record<string, string[]> = {
    'Planned': ['cta-confirm', 'cta-start', 'cta-cancel'],
    'Confirmed': ['cta-start', 'cta-cancel'],
    'In Progress': ['cta-complete'],
    'Completed': ['cta-verify'],
    'Verified': ['cta-close'],
    'Closed': [],
    'Cancelled': [],
  }
  for (const [state, expected] of Object.entries(EXPECTED)) {
    it(`${state} → CTA = [${expected.join(', ')}]`, async () => {
      currentSession.value = makeSession({ workflow_state: state })
      const w = await mountDetail()
      expect(ctasShown(w).sort()).toEqual([...expected].sort())
    })
  }
})

// ─── Anti-hardcode guard: không còn biểu thức state === '<StatusString>' ──────
describe('SessionDetailView không hardcode state === "<StatusString>" cho 6 CTA', () => {
  it('source không chứa gating dạng state.value === Confirmed/Completed/Verified/... cho canXxx', async () => {
    const fs = await import('node:fs')
    const path = await import('node:path')
    // process.cwd() = frontend root khi vitest chạy → đọc SFC source trực tiếp.
    const src = fs.readFileSync(
      path.resolve(process.cwd(), 'src/views/training/SessionDetailView.vue'),
      'utf8',
    )
    // 6 computed CTA phải gate bằng allowedTransitions.includes(...), KHÔNG state === '...'.
    const canBlock = src.slice(src.indexOf('const canConfirm'), src.indexOf('const hasAnyAction'))
    expect(canBlock).toContain('allowedTransitions.value.includes')
    expect(/const can(Confirm|Start|Complete|Verify|Close|Cancel)\s*=\s*computed\(\(\)\s*=>\s*state\.value\s*===/.test(canBlock)).toBe(false)
  })
})
