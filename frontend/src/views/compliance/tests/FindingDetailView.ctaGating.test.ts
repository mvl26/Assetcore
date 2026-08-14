// Copyright (c) 2026, AssetCore Team
//
// IMM-16 — FindingDetailView: 6 CTA phân định (Bắt đầu xem xét / Xác nhận NC /
// Đánh dấu sai / Miễn áp dụng / Tạo CAPA / Liên kết CAPA) gate theo SSoT server-driven
// `allowed_transitions` (BE _FINDING_VALID_TRANSITIONS, services/imm16.py) +
// cờ `can_create_capa` + capability `compliance.write` — KHÔNG hardcode
// `finding.status === 'X'` (GATE-8 / LL-FE-51 / ADR-IMM-16-01).
//
// RED trước fix: canConfirm=['Open','Under Review'].includes(status) (loại
// Confirmed NC dù BE ACTIVE gồm nó); "Đánh dấu sai" dùng chung gate canConfirm;
// nút "Liên kết CAPA" hardcode inline `status==='Confirmed NC' && !capa_ref`.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

vi.mock('vue-router', () => ({ useRouter: () => ({ push: vi.fn() }) }))
vi.mock('@/composables/useApi', () => ({
  useApi: () => ({ run: vi.fn(), loading: { value: false } }),
}))

// Capability controllable per test (mặc định: có compliance.write).
let canImpl: (c: string) => boolean = () => true
vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({ can: (c: string) => canImpl(c) }),
}))

// getFinding trả fixture điều khiển được.
const findingState: { value: Record<string, unknown> | null } = { value: null }
const getFinding = vi.fn(async (..._a: unknown[]) => findingState.value)
vi.mock('@/api/imm16', () => ({ getFinding: (...a: unknown[]) => getFinding(...a) }))

vi.mock('@/stores/imm16', () => ({
  useImm16Store: () => ({
    actionStartReview: vi.fn().mockResolvedValue(true),
    actionConfirmFinding: vi.fn().mockResolvedValue(true),
    actionMarkFalsePositive: vi.fn().mockResolvedValue(true),
    actionWaiveFinding: vi.fn().mockResolvedValue(true),
    actionLinkToCapa: vi.fn().mockResolvedValue(true),
    actionCreateCapaFromFinding: vi.fn().mockResolvedValue(true),
  }),
}))

import FindingDetailView from '@/views/compliance/FindingDetailView.vue'

// PageHeader chứa CTA trong slot #actions → stub PHẢI render slot đó, nếu không
// nút biến mất và test luôn xanh giả (false-negative).
const stubs = {
  PageHeader: { template: '<div><slot /><slot name="actions" /></div>' },
  StatusBadge: true,
  BaseModal: true,
  SkeletonLoader: true,
  RecordHistory: true,
}

function fnd(over: Record<string, unknown> = {}) {
  return {
    name: 'FND-2026-00001',
    rule: 'R-IMM08-PM-90',
    rule_name: 'PM đạt 90%',
    detected_date: '2026-01-01',
    evaluation_date: '2026-01-02',
    asset: null,
    asset_name: '',
    responsible_dept: null,
    responsible_dept_name: '',
    severity: 'High',
    current_value: null,
    threshold_value: null,
    status: 'Open',
    capa_ref: null,
    allowed_transitions: [] as string[],
    can_create_capa: 0,
    ...over,
  }
}

async function render(fixture: Record<string, unknown>) {
  findingState.value = fixture
  const w = mount(FindingDetailView, { props: { id: 'FND-2026-00001' }, global: { stubs } })
  await flushPromises()
  return w
}

function has(w: Awaited<ReturnType<typeof render>>, testid: string) {
  return w.find(`[data-testid="${testid}"]`).exists()
}

const ALL_CTA = ['cta-start-review', 'cta-confirm', 'cta-mark-false', 'cta-waive', 'cta-create-capa', 'cta-link-capa']

beforeEach(() => {
  vi.clearAllMocks()
  canImpl = () => true
  findingState.value = null
})

describe('FindingDetailView — CTA gating server-driven (allowed_transitions + can_create_capa + capability)', () => {
  it("allowed=[Confirmed NC, Waived] + compliance.write → 'Xác nhận NC' + 'Miễn áp dụng' HIỆN, 'Tạo CAPA' ẩn", async () => {
    const w = await render(fnd({
      status: 'Confirmed NC',
      allowed_transitions: ['Confirmed NC', 'Waived'],
      can_create_capa: 0,
    }))
    expect(has(w, 'cta-confirm')).toBe(true)
    expect(has(w, 'cta-waive')).toBe(true)
    // 'False Positive' KHÔNG trong allowed → Đánh dấu sai ẩn.
    expect(has(w, 'cta-mark-false')).toBe(false)
    // can_create_capa=0 → Tạo CAPA + Liên kết CAPA ẩn.
    expect(has(w, 'cta-create-capa')).toBe(false)
    expect(has(w, 'cta-link-capa')).toBe(false)
  })

  it('allowed_transitions=[] (terminal) → tất cả CTA ẩn', async () => {
    const w = await render(fnd({
      status: 'Waived',
      allowed_transitions: [],
      can_create_capa: 0,
    }))
    for (const t of ALL_CTA) {
      expect(has(w, t), `nút ${t} KHÔNG được render ở trạng thái cuối`).toBe(false)
    }
  })

  it('thiếu capability compliance.write → tất cả CTA ẩn dù allowed_transitions có phần tử', async () => {
    canImpl = (c: string) => c !== 'compliance.write'
    const w = await render(fnd({
      status: 'Open',
      allowed_transitions: ['Confirmed NC', 'False Positive', 'Waived'],
      can_create_capa: 0,
    }))
    for (const t of ALL_CTA) {
      expect(has(w, t), `nút ${t} phải ẩn khi thiếu compliance.write`).toBe(false)
    }
  })

  it('Open + write + allowed=[Confirmed NC, False Positive, Waived] → 3 CTA phân định HIỆN, CAPA ẩn', async () => {
    const w = await render(fnd({
      status: 'Open',
      allowed_transitions: ['Confirmed NC', 'False Positive', 'Waived'],
      can_create_capa: 0,
    }))
    expect(has(w, 'cta-confirm')).toBe(true)
    expect(has(w, 'cta-mark-false')).toBe(true)
    expect(has(w, 'cta-waive')).toBe(true)
    expect(has(w, 'cta-create-capa')).toBe(false)
    expect(has(w, 'cta-link-capa')).toBe(false)
    // 'Under Review' KHÔNG trong allowed → 'Bắt đầu xem xét' ẩn.
    expect(has(w, 'cta-start-review')).toBe(false)
  })

  // round 14 (CR-WF-16-FIND / ADR-IMM-16-06): surface phantom Open→Under Review.
  it("Open (round 14) + write + allowed=[Under Review, Confirmed NC, False Positive, Waived] → 'Bắt đầu xem xét' HIỆN cùng 3 CTA phân định (không regress)", async () => {
    const w = await render(fnd({
      status: 'Open',
      allowed_transitions: ['Under Review', 'Confirmed NC', 'False Positive', 'Waived'],
      can_create_capa: 0,
    }))
    expect(has(w, 'cta-start-review')).toBe(true)
    // 3 CTA phân định cũ KHÔNG regress — nút mới chỉ THÊM.
    expect(has(w, 'cta-confirm')).toBe(true)
    expect(has(w, 'cta-mark-false')).toBe(true)
    expect(has(w, 'cta-waive')).toBe(true)
    expect(has(w, 'cta-create-capa')).toBe(false)
  })

  it("Under Review + write + allowed=[Confirmed NC, False Positive, Waived] → 'Bắt đầu xem xét' ẩn (đã trong review), 3 CTA phân định hiện", async () => {
    const w = await render(fnd({
      status: 'Under Review',
      allowed_transitions: ['Confirmed NC', 'False Positive', 'Waived'],
      can_create_capa: 0,
    }))
    expect(has(w, 'cta-start-review')).toBe(false)
    expect(has(w, 'cta-confirm')).toBe(true)
    expect(has(w, 'cta-mark-false')).toBe(true)
    expect(has(w, 'cta-waive')).toBe(true)
  })

  it('Confirmed NC chưa gắn CAPA (can_create_capa=1) → Tạo + Liên kết CAPA HIỆN, Xác nhận NC ẩn', async () => {
    const w = await render(fnd({
      status: 'Confirmed NC',
      allowed_transitions: ['Waived'],
      can_create_capa: 1,
    }))
    expect(has(w, 'cta-create-capa')).toBe(true)
    expect(has(w, 'cta-link-capa')).toBe(true)
    expect(has(w, 'cta-waive')).toBe(true)
    // 'Confirmed NC' KHÔNG trong allowed của state Confirmed NC → Xác nhận NC ẩn (hết desync).
    expect(has(w, 'cta-confirm')).toBe(false)
  })

  it("fallback: allowed_transitions/can_create_capa VẮNG (worker cũ) → CTA ẩn, KHÔNG crash", async () => {
    const raw = fnd({ status: 'Open' }) as Record<string, unknown>
    delete raw.allowed_transitions
    delete raw.can_create_capa
    const w = await render(raw)
    for (const t of ALL_CTA) {
      expect(has(w, t)).toBe(false)
    }
  })
})
