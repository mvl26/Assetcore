// Copyright (c) 2026, AssetCore Team
//
// IMM-16 — InternalAuditDetailView: CTA vòng đời (Bắt đầu / Bảng kiểm→Báo cáo /
// Đóng) gate theo SSoT server-driven `allowed_transitions` (BE
// _AUDIT_VALID_TRANSITIONS, services/imm16.py) + cờ capability server
// `can_operate`/`can_close` — KHÔNG hardcode `audit.status === 'X'`
// (GATE-8 / LL-FE-51 / GATE-6c anti-dead-control).
//
// RED trước fix: canStart=status==='Planned'; canChecklist=status==='In Progress';
// canClose=['In Progress','Reporting'].includes(status) → desync cho Đóng NGAY ở
// In Progress (jump-skip). Fix: allowed_transitions.includes('start'|'complete_checklist'
// |'close') + cờ, degrade an toàn khi thiếu allowed_transitions (0 CTA).
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import type { VueWrapper } from '@vue/test-utils'

vi.mock('vue-router', () => ({ useRouter: () => ({ push: vi.fn() }) }))

// useApi.run call-through: click CTA → store action thật (verify param == UI selection).
vi.mock('@/composables/useApi', () => ({
  useApi: () => ({
    run: vi.fn((fn: () => unknown) => fn()),
    loading: { value: false },
  }),
}))

// get_audit trả fixture điều khiển được.
const auditState: { value: Record<string, unknown> | null } = { value: null }
const getAudit = vi.fn(async (..._a: unknown[]) => auditState.value)
vi.mock('@/api/imm16', () => ({ getAudit: (...a: unknown[]) => getAudit(...a) }))

// Store actions — spy để assert param phát đi.
const actionStartAudit = vi.fn().mockResolvedValue({ name: 'AUD-2026-00001' })
const actionCompleteChecklist = vi.fn().mockResolvedValue({ findings_created: 0 })
const actionCloseAudit = vi.fn().mockResolvedValue({ name: 'AUD-2026-00001' })
vi.mock('@/stores/imm16', () => ({
  useImm16Store: () => ({ actionStartAudit, actionCompleteChecklist, actionCloseAudit }),
}))

import InternalAuditDetailView from '@/views/compliance/InternalAuditDetailView.vue'

// PageHeader/BaseModal chứa CTA trong slot → stub PHẢI render slot đó, nếu không
// nút biến mất và test xanh giả (false-negative).
const stubs = {
  PageHeader: { template: '<div><slot /><slot name="actions" /></div>' },
  BaseModal: { template: '<div><slot /><slot name="footer" /></div>' },
  StatusBadge: true,
  SkeletonLoader: true,
}

function aud(over: Record<string, unknown> = {}) {
  return {
    name: 'AUD-2026-00001',
    audit_code: 'AUD-2026-00001',
    audit_type: 'Internal',
    planned_start: '2026-01-01',
    planned_end: '2026-01-10',
    lead_auditor: 'auditor@benhvien.vn',
    lead_auditor_name: 'KTV Nguyễn Văn A',
    status: 'Planned',
    findings_count: 0,
    allowed_transitions: [] as string[],
    can_operate: false,
    can_close: false,
    ...over,
  }
}

async function render(fixture: Record<string, unknown>) {
  auditState.value = fixture
  const w = mount(InternalAuditDetailView, {
    props: { id: 'AUD-2026-00001' },
    global: { stubs },
  })
  await flushPromises()
  return w
}

function has(w: VueWrapper, testid: string) {
  return w.find(`[data-testid="${testid}"]`).exists()
}

async function openChecklistTab(w: VueWrapper) {
  const btn = w.findAll('button').find((b) => b.text() === 'Bảng kiểm')
  if (btn) await btn.trigger('click')
  await flushPromises()
}

beforeEach(() => {
  vi.clearAllMocks()
  auditState.value = null
})

describe('InternalAuditDetailView — CTA server-driven (allowed_transitions + can_operate/can_close)', () => {
  it("Planned + can_operate → chỉ 'Bắt đầu', KHÔNG 'Đóng', KHÔNG hint", async () => {
    const w = await render(aud({ status: 'Planned', allowed_transitions: ['start'], can_operate: true }))
    expect(has(w, 'cta-start')).toBe(true)
    expect(has(w, 'cta-close')).toBe(false)
    expect(has(w, 'no-actions-hint')).toBe(false)
    await openChecklistTab(w)
    expect(has(w, 'checklist-editor')).toBe(false)
  })

  it("In Progress → checklist-editor + KHÔNG 'Đóng' + KHÔNG 'Bắt đầu' + hint dẫn tới Báo cáo", async () => {
    const w = await render(aud({
      status: 'In Progress', allowed_transitions: ['complete_checklist'],
      can_operate: true, can_close: false,
    }))
    expect(has(w, 'cta-start')).toBe(false)
    expect(has(w, 'cta-close')).toBe(false)
    expect(has(w, 'no-actions-hint')).toBe(true)
    expect(w.find('[data-testid="no-actions-hint"]').text()).toContain('Hoàn tất bảng kiểm')
    await openChecklistTab(w)
    expect(has(w, 'checklist-editor')).toBe(true)
  })

  it("Reporting + can_close → 'Đóng' HIỆN, KHÔNG 'Bắt đầu', KHÔNG hint", async () => {
    const w = await render(aud({
      status: 'Reporting', allowed_transitions: ['close'], can_operate: true, can_close: true,
    }))
    expect(has(w, 'cta-close')).toBe(true)
    expect(has(w, 'cta-start')).toBe(false)
    expect(has(w, 'no-actions-hint')).toBe(false)
    await openChecklistTab(w)
    expect(has(w, 'checklist-editor')).toBe(false)
  })

  it('Closed (terminal) → 0 CTA, KHÔNG hint, KHÔNG editor', async () => {
    const w = await render(aud({
      status: 'Closed', allowed_transitions: [], can_operate: true, can_close: true,
    }))
    expect(has(w, 'cta-start')).toBe(false)
    expect(has(w, 'cta-close')).toBe(false)
    expect(has(w, 'no-actions-hint')).toBe(false)
    await openChecklistTab(w)
    expect(has(w, 'checklist-editor')).toBe(false)
  })

  it('allowed_transitions VẮNG (worker cũ) → 0 CTA, degrade an toàn, KHÔNG crash', async () => {
    const raw = aud({ status: 'In Progress', can_operate: true })
    delete (raw as Record<string, unknown>).allowed_transitions
    const w = await render(raw)
    expect(has(w, 'cta-start')).toBe(false)
    expect(has(w, 'cta-close')).toBe(false)
    expect(has(w, 'no-actions-hint')).toBe(false)
    await openChecklistTab(w)
    expect(has(w, 'checklist-editor')).toBe(false)
  })

  it("Reporting + can_close=false → KHÔNG 'Đóng' (thiếu quyền) + hint quyền", async () => {
    const w = await render(aud({
      status: 'Reporting', allowed_transitions: ['close'], can_operate: true, can_close: false,
    }))
    expect(has(w, 'cta-close')).toBe(false)
    expect(has(w, 'no-actions-hint')).toBe(true)
    expect(w.find('[data-testid="no-actions-hint"]').text()).toContain('không có quyền đóng')
  })

  it("Planned + can_operate=false → KHÔNG 'Bắt đầu' (thiếu quyền) + hint quyền", async () => {
    const w = await render(aud({ status: 'Planned', allowed_transitions: ['start'], can_operate: false }))
    expect(has(w, 'cta-start')).toBe(false)
    expect(has(w, 'no-actions-hint')).toBe(true)
    expect(w.find('[data-testid="no-actions-hint"]').text()).toContain('không có quyền bắt đầu')
  })
})

describe('InternalAuditDetailView — decoupling proof (gate đọc allowed_transitions, KHÔNG status===)', () => {
  // Feed status MÂU THUẪN với allowed_transitions: nếu gate còn hardcode
  // `status === 'X'` thì các assert dưới FAIL. Server-driven ⇒ gate BÁM
  // allowed_transitions, bỏ qua status. Đây là bằng chứng anti-status-hardcode
  // mạnh nhất (GATE-8 / LL-FE-51) — mạnh hơn case degrade (chỉ phủ checklist).
  it("status='Reporting' NHƯNG allowed_transitions=['start'] → HIỆN 'Bắt đầu', KHÔNG 'Đóng'", async () => {
    const w = await render(aud({
      status: 'Reporting', allowed_transitions: ['start'], can_operate: true, can_close: true,
    }))
    expect(has(w, 'cta-start')).toBe(true) // theo AT, KHÔNG theo status==='Planned'
    expect(has(w, 'cta-close')).toBe(false) // 'close' ∉ AT dù status==='Reporting'
  })

  it("status='Planned' NHƯNG allowed_transitions=['close'] → HIỆN 'Đóng', KHÔNG 'Bắt đầu'", async () => {
    const w = await render(aud({
      status: 'Planned', allowed_transitions: ['close'], can_operate: true, can_close: true,
    }))
    expect(has(w, 'cta-close')).toBe(true) // theo AT, KHÔNG theo status==='Reporting'
    expect(has(w, 'cta-start')).toBe(false) // 'start' ∉ AT dù status==='Planned'
  })

  it("status='Closed' NHƯNG allowed_transitions=['complete_checklist'] → editor HIỆN (gate ⊄ status terminal)", async () => {
    const w = await render(aud({
      status: 'Closed', allowed_transitions: ['complete_checklist'], can_operate: true,
    }))
    await openChecklistTab(w)
    expect(has(w, 'checklist-editor')).toBe(true) // theo AT, KHÔNG khoá bởi status==='Closed'
  })
})

describe('InternalAuditDetailView — anti-dead-control (param phát đi == UI selection)', () => {
  it("click 'Bắt đầu' → actionStartAudit(name)", async () => {
    const w = await render(aud({ status: 'Planned', allowed_transitions: ['start'], can_operate: true }))
    await w.find('[data-testid="cta-start"]').trigger('click')
    await flushPromises()
    expect(actionStartAudit).toHaveBeenCalledWith('AUD-2026-00001')
  })

  it("click 'Hoàn tất bảng kiểm' → actionCompleteChecklist(name, items[])", async () => {
    const w = await render(aud({
      status: 'In Progress', allowed_transitions: ['complete_checklist'], can_operate: true,
    }))
    await openChecklistTab(w)
    const submit = w.findAll('button').find((b) => b.text().includes('Hoàn tất bảng kiểm'))
    expect(submit).toBeTruthy()
    await submit!.trigger('click')
    await flushPromises()
    expect(actionCompleteChecklist).toHaveBeenCalledTimes(1)
    const [name, items] = actionCompleteChecklist.mock.calls[0]
    expect(name).toBe('AUD-2026-00001')
    expect(Array.isArray(items)).toBe(true)
  })

  it("Đóng: click cta-close → nhập báo cáo → xác nhận → actionCloseAudit(name, report)", async () => {
    const w = await render(aud({
      status: 'Reporting', allowed_transitions: ['close'], can_operate: true, can_close: true,
    }))
    await w.find('[data-testid="cta-close"]').trigger('click')
    await flushPromises()
    await w.find('textarea').setValue('Tóm tắt kết quả kiểm toán quý 1')
    await w.find('[data-testid="cta-close-confirm"]').trigger('click')
    await flushPromises()
    expect(actionCloseAudit).toHaveBeenCalledWith('AUD-2026-00001', 'Tóm tắt kết quả kiểm toán quý 1')
  })
})
