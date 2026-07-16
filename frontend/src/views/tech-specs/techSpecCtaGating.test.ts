// Copyright (c) 2026, AssetCore Team
//
// IMM-02 — TechSpecDetailView: 3 CTA duyệt (Chốt hồ sơ / Rút hồ sơ / Phát hành lại)
// gate theo SSoT server-driven `can_lock` / `can_withdraw` / `can_reissue` (BE
// get_tech_spec DERIVE từ guard-state THỰC ∧ vai trò duyệt) — KHÔNG hardcode
// `workflow_state === 'X'` (GATE-8 / LL-FE-51).
//
// RED trước fix: canLock = workflow_state === 'Pending Approval' (không role) ⇒ MỌI
// user login thấy + bấm "Chốt hồ sơ". Sau fix: nút CHỈ hiện khi cờ server=true —
// cùng state nhưng cờ false ⇒ nút ẩn (chứng minh gate theo cờ, không theo status).
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn(), back: vi.fn() }),
  useRoute: () => ({ params: { id: 'TS-26-00001' } }),
}))

// API side-effects (chỉ gọi khi bấm nút) — mock để không kéo axios thật.
vi.mock('@/api/imm02', () => ({
  submitBenchmark: vi.fn().mockResolvedValue({ name: 'MB', recommended: '' }),
  submitLockInAssessment: vi.fn().mockResolvedValue({ name: 'LR', lock_in_score: 0, threshold: 2.5 }),
}))

// Store mock — currentSpec điều khiển được qua storeState (getter → đọc mới mỗi render).
const storeState: { currentSpec: Record<string, unknown> | null } = { currentSpec: null }
vi.mock('@/stores/imm02', () => ({
  useImm02Store: () => ({
    get currentSpec() { return storeState.currentSpec },
    loading: false,
    error: null as string | null,
    clearError: vi.fn(),
    fetchOne: vi.fn().mockResolvedValue(undefined),
    lock: vi.fn().mockResolvedValue(undefined),
    withdraw: vi.fn().mockResolvedValue(undefined),
    reissue: vi.fn().mockResolvedValue({ name: 'TS-26-00002' }),
  }),
}))

import TechSpecDetailView from './TechSpecDetailView.vue'

// Child components nặng → stub để test cô lập phần CTA.
const stubs = {
  RequirementTable: true,
  CurrencyInput: true,
}

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
    workflow_state: 'Pending Approval',
    // Cờ server-driven — mặc định TẮT (đúng "worker cũ / thiếu quyền").
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

function has(w: Awaited<ReturnType<typeof render>>, testid: string) {
  return w.find(`[data-testid="${testid}"]`).exists()
}

beforeEach(() => {
  vi.clearAllMocks()
  storeState.currentSpec = null
})

describe('TechSpecDetailView — CTA gating server-driven (can_lock/can_withdraw/can_reissue)', () => {
  it("can_lock=true → 'Chốt hồ sơ' HIỆN; can_withdraw=true → 'Rút hồ sơ' HIỆN", async () => {
    const w = await render(spec({
      workflow_state: 'Pending Approval',
      can_lock: true,
      can_withdraw: true,
      can_reissue: false,
      allowed_transitions: ['Locked', 'Withdrawn'],
    }))
    expect(has(w, 'cta-lock')).toBe(true)
    expect(has(w, 'cta-withdraw')).toBe(true)
    expect(has(w, 'cta-reissue')).toBe(false)
  })

  it("PROOF server-driven: can_lock=false NHƯNG workflow_state='Pending Approval' → 'Chốt hồ sơ' KHÔNG render (gate theo cờ, không theo status)", async () => {
    const w = await render(spec({
      workflow_state: 'Pending Approval', // status hợp lệ để Lock…
      can_lock: false,                    // …nhưng cờ server TẮT (user không có vai trò duyệt)
      can_withdraw: false,
      can_reissue: false,
    }))
    expect(has(w, 'cta-lock')).toBe(false)
    expect(has(w, 'cta-withdraw')).toBe(false)
    expect(has(w, 'cta-reissue')).toBe(false)
  })

  it("state 'Locked' + can_withdraw=true → chỉ 'Rút hồ sơ' HIỆN (parity guard withdraw cho Locked)", async () => {
    const w = await render(spec({
      workflow_state: 'Locked',
      docstatus: 1,
      can_lock: false,
      can_withdraw: true,
      can_reissue: false,
      allowed_transitions: ['Withdrawn'],
    }))
    expect(has(w, 'cta-withdraw')).toBe(true)
    expect(has(w, 'cta-lock')).toBe(false)
    expect(has(w, 'cta-reissue')).toBe(false)
  })

  it("state 'Withdrawn' + can_reissue=true → chỉ 'Phát hành lại' HIỆN", async () => {
    const w = await render(spec({
      workflow_state: 'Withdrawn',
      docstatus: 1,
      withdrawal_reason: 'Sai cấu hình',
      can_lock: false,
      can_withdraw: false,
      can_reissue: true,
      allowed_transitions: ['Draft'],
    }))
    expect(has(w, 'cta-reissue')).toBe(true)
    expect(has(w, 'cta-lock')).toBe(false)
    expect(has(w, 'cta-withdraw')).toBe(false)
  })

  it('tất cả cờ false → không nút CTA nào render (không vỡ layout)', async () => {
    const w = await render(spec({
      workflow_state: 'Draft',
      can_lock: false,
      can_withdraw: false,
      can_reissue: false,
    }))
    expect(has(w, 'cta-lock')).toBe(false)
    expect(has(w, 'cta-withdraw')).toBe(false)
    expect(has(w, 'cta-reissue')).toBe(false)
    // action-bar vẫn tồn tại (không crash), chỉ rỗng nút.
    expect(w.find('.action-bar').exists()).toBe(true)
  })

  it('cờ VẮNG (worker cũ / field thiếu) → CTA ẩn, KHÔNG crash console', async () => {
    const raw = spec({ workflow_state: 'Pending Approval' })
    delete (raw as Record<string, unknown>).can_lock
    delete (raw as Record<string, unknown>).can_withdraw
    delete (raw as Record<string, unknown>).can_reissue
    delete (raw as Record<string, unknown>).allowed_transitions
    const w = await render(raw)
    expect(has(w, 'cta-lock')).toBe(false)
    expect(has(w, 'cta-withdraw')).toBe(false)
    expect(has(w, 'cta-reissue')).toBe(false)
  })
})
