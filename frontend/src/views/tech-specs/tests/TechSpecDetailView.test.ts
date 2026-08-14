// Copyright (c) 2026, AssetCore Team
//
// IMM-02 — TechSpecDetailView: nút CTA workflow TRUNG GIAN server-driven từ
// `store.currentSpec.allowed_actions` (BE get_tech_spec → spec_allowed_actions đã
// LỌC theo vai trò). Đóng bug "Spec kẹt ở Draft/Reviewing/Benchmarked/Risk Assessed
// dù đủ quyền" — endpoint transition_workflow LIVE nhưng FE 0 nút render.
//
// Bất biến kiểm ở đây:
//  - render ĐÚNG 1 nút cta-wf / mỗi entry allowed_actions (label = action VI trực tiếp).
//  - click → store.transitionWorkflow(props.id, action) (KHÔNG hardcode action ở call-site).
//  - allowed_actions=[] hoặc VẮNG → 0 nút cta-wf (cụm tự ẩn, không crash).
//  - 3 nút lock/withdraw/reissue cũ GIỮ độc lập (can_lock=true vẫn render) — no regress.
//  - ZERO so-sánh `workflow_state ===` cho nút wf: cùng state, allowed_actions khác →
//    số nút wf khác (chứng minh nguồn DUY NHẤT là server, không phải status).
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn(), back: vi.fn() }),
  useRoute: () => ({ params: { id: 'TS-26-00001' } }),
}))

// API side-effects (chỉ gọi khi bấm benchmark/lock-in) — mock để không kéo axios thật.
vi.mock('@/api/imm02', () => ({
  submitBenchmark: vi.fn().mockResolvedValue({ name: 'MB', recommended: '' }),
  submitLockInAssessment: vi.fn().mockResolvedValue({ name: 'LR', lock_in_score: 0, threshold: 2.5 }),
}))

// notify — mock để assert phản hồi contract (success show / lỗi fromError).
const notifyShow = vi.fn()
const notifyFromError = vi.fn()
vi.mock('@/composables/useNotify', () => ({
  useNotify: () => ({ show: notifyShow, fromError: notifyFromError, confirm: vi.fn(), fromOk: vi.fn() }),
}))

// Store mock — currentSpec + lastApiError điều khiển qua storeState (getter → đọc mới
// mỗi render). transitionWorkflow là spy để assert đối số + số lần gọi.
const transitionWorkflow = vi.fn().mockResolvedValue(true)
const storeState: {
  currentSpec: Record<string, unknown> | null
  lastApiError: unknown
} = { currentSpec: null, lastApiError: null }

vi.mock('@/stores/imm02', () => ({
  useImm02Store: () => ({
    get currentSpec() { return storeState.currentSpec },
    get lastApiError() { return storeState.lastApiError },
    loading: false,
    error: null as string | null,
    clearError: vi.fn(),
    fetchOne: vi.fn().mockResolvedValue(undefined),
    transitionWorkflow,
    lock: vi.fn().mockResolvedValue(undefined),
    withdraw: vi.fn().mockResolvedValue(undefined),
    reissue: vi.fn().mockResolvedValue({ name: 'TS-26-00002' }),
  }),
}))

import TechSpecDetailView from '@/views/tech-specs/TechSpecDetailView.vue'

const stubs = { RequirementTable: true, CurrencyInput: true }

function spec(over: Record<string, unknown> = {}) {
  return {
    name: 'TS-26-00001',
    version: '1.0',
    device_model_ref: 'IMM-MDL-0001',
    device_model_name: 'Dräger Evita V500',
    device_category: null,
    quantity: 1,
    source_plan: 'PP-2026-0001',
    source_needs_request: 'NR-2026-0001',
    total_mandatory: 0,
    total_optional: 0,
    requirements: [] as unknown[],
    infra_compat: [] as unknown[],
    infra_status_overall: '',
    lock_in_score: null,
    mitigation_plan: null,
    approver: null,
    approval_date: null,
    withdrawal_reason: null,
    docstatus: 0,
    workflow_state: 'Draft',
    allowed_actions: [] as string[],
    allowed_transitions: [] as string[],
    can_lock: false,
    can_withdraw: false,
    can_reissue: false,
    ...over,
  }
}

async function render(fixture: Record<string, unknown>) {
  storeState.currentSpec = fixture
  const w = mount(TechSpecDetailView, { props: { id: 'TS-26-00001' }, global: { stubs } })
  await flushPromises()
  return w
}

function wfButtons(w: Awaited<ReturnType<typeof render>>) {
  return w.findAll('[data-testid^="cta-wf-"]')
}
function has(w: Awaited<ReturnType<typeof render>>, testid: string) {
  return w.find(`[data-testid="${testid}"]`).exists()
}

beforeEach(() => {
  vi.clearAllMocks()
  storeState.currentSpec = null
  storeState.lastApiError = null
  transitionWorkflow.mockResolvedValue(true)
})

describe('TechSpecDetailView — CTA workflow trung gian server-driven (allowed_actions)', () => {
  it("allowed_actions=['Gửi rà soát'] → render ĐÚNG 1 nút cta-wf với đúng nhãn + slug", async () => {
    const w = await render(spec({ workflow_state: 'Draft', allowed_actions: ['Gửi rà soát'] }))
    const btns = wfButtons(w)
    expect(btns).toHaveLength(1)
    expect(btns[0].text()).toBe('Gửi rà soát')
    // slug bỏ dấu tiếng Việt (data-testid ổn định).
    expect(has(w, 'cta-wf-gui-ra-soat')).toBe(true)
  })

  it("click nút cta-wf → store.transitionWorkflow(props.id, action) đúng đối số", async () => {
    const w = await render(spec({ workflow_state: 'Draft', allowed_actions: ['Gửi rà soát'] }))
    await wfButtons(w)[0].trigger('click')
    await flushPromises()
    expect(transitionWorkflow).toHaveBeenCalledTimes(1)
    expect(transitionWorkflow).toHaveBeenCalledWith('TS-26-00001', 'Gửi rà soát')
    // success → notify.show, KHÔNG fromError.
    expect(notifyShow).toHaveBeenCalledTimes(1)
    expect(notifyFromError).not.toHaveBeenCalled()
  })

  it('nhiều allowed_actions → 1 nút / action, đúng thứ tự + nhãn (không hardcode)', async () => {
    const w = await render(spec({
      workflow_state: 'Reviewing',
      allowed_actions: ['Yêu cầu chỉnh spec', 'Hoàn tất benchmark'],
    }))
    const btns = wfButtons(w)
    expect(btns).toHaveLength(2)
    expect(btns.map(b => b.text())).toEqual(['Yêu cầu chỉnh spec', 'Hoàn tất benchmark'])
  })

  it('PROOF server-driven: cùng workflow_state=Reviewing nhưng allowed_actions khác → số nút wf khác', async () => {
    // Spec User ở Reviewing chỉ được 1 action; Needs Manager được 2 — nếu FE gate theo
    // status thì cả 2 phải giống nhau. Số nút khác ⇒ nguồn là allowed_actions (server).
    const wUser = await render(spec({ workflow_state: 'Reviewing', allowed_actions: ['Yêu cầu chỉnh spec'] }))
    expect(wfButtons(wUser)).toHaveLength(1)
    const wMgr = await render(spec({ workflow_state: 'Reviewing', allowed_actions: ['Yêu cầu chỉnh spec', 'Hoàn tất benchmark'] }))
    expect(wfButtons(wMgr)).toHaveLength(2)
  })

  it('allowed_actions=[] → 0 nút cta-wf (cụm tự ẩn), action-bar vẫn tồn tại', async () => {
    const w = await render(spec({ workflow_state: 'Draft', allowed_actions: [] }))
    expect(wfButtons(w)).toHaveLength(0)
    // Lô 2: panel thao tác nay là slot `#actions` của DetailPageShell (selector đổi,
    // KỲ VỌNG giữ nguyên — §13.9.9).
    expect(w.find('[data-testid="detail-actions"]').exists()).toBe(true)
  })

  it('allowed_actions VẮNG (worker cũ / field thiếu) → 0 nút cta-wf, KHÔNG crash', async () => {
    const raw = spec({ workflow_state: 'Reviewing' })
    delete (raw as Record<string, unknown>).allowed_actions
    const w = await render(raw)
    expect(wfButtons(w)).toHaveLength(0)
  })

  it('terminal Locked → allowed_actions=[] → 0 nút wf (workflow-engine terminal)', async () => {
    const w = await render(spec({
      workflow_state: 'Locked', docstatus: 1, allowed_actions: [], can_withdraw: true,
      allowed_transitions: ['Withdrawn'],
    }))
    expect(wfButtons(w)).toHaveLength(0)
    // nhưng nút withdraw (EXCEPTION cờ riêng) vẫn độc lập.
    expect(has(w, 'cta-withdraw')).toBe(true)
  })

  it('KHÔNG double-render Phê duyệt spec / Rút spec: cờ lock/withdraw giữ độc lập với allowed_actions', async () => {
    // Pending Approval: 2 cạnh exception qua can_lock/can_withdraw; allowed_actions chỉ
    // chứa cạnh trung gian còn lại (Yêu cầu chỉnh risk). KHÔNG có nút 'Phê duyệt spec'/'Rút spec'.
    const w = await render(spec({
      workflow_state: 'Pending Approval',
      allowed_actions: ['Yêu cầu chỉnh risk'],
      can_lock: true, can_withdraw: true,
      allowed_transitions: ['Locked', 'Withdrawn', 'Risk Assessed'],
    }))
    expect(wfButtons(w)).toHaveLength(1)
    expect(wfButtons(w)[0].text()).toBe('Yêu cầu chỉnh risk')
    // exception buttons render qua cờ riêng (không double-render dạng cta-wf).
    expect(has(w, 'cta-lock')).toBe(true)
    expect(has(w, 'cta-withdraw')).toBe(true)
    expect(has(w, 'cta-wf-phe-duyet-spec')).toBe(false)
    expect(has(w, 'cta-wf-rut-spec')).toBe(false)
  })

  it('no regress: can_lock=true render nút lock độc lập (song song với cta-wf)', async () => {
    const w = await render(spec({
      workflow_state: 'Pending Approval',
      allowed_actions: ['Yêu cầu chỉnh risk'],
      can_lock: true,
    }))
    expect(has(w, 'cta-lock')).toBe(true)
    expect(wfButtons(w)).toHaveLength(1)
  })

  it('transition thất bại → notify.fromError(store.lastApiError), KHÔNG notify.show', async () => {
    transitionWorkflow.mockResolvedValueOnce(false)
    storeState.lastApiError = { messageCode: 'IMM02-XXX', message: 'Không đủ quyền' }
    const w = await render(spec({ workflow_state: 'Draft', allowed_actions: ['Gửi rà soát'] }))
    await wfButtons(w)[0].trigger('click')
    await flushPromises()
    expect(notifyFromError).toHaveBeenCalledTimes(1)
    expect(notifyFromError).toHaveBeenCalledWith(storeState.lastApiError)
    expect(notifyShow).not.toHaveBeenCalled()
  })
})
