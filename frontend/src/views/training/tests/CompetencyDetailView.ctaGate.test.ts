// TDD (FE regression guard) — GATE-8 / LL-FE-51: server-driven CTA cho Năng lực.
//
// CompetencyDetailView gate 100% nút vòng đời (Phê duyệt / Thu hồi / Tái chứng nhận)
// theo `allowed_transitions` (BE derive từ SSoT _COMPETENCY_VALID_TRANSITIONS đã
// enforce) + cờ can_signoff/can_revoke/can_recertify (đã lọc theo capability
// `training.submit` của caller) — KHÔNG hardcode `workflow_state === 'X'`.
//
// RED trước fix (dead-gate): nút gate bằng `workflow_state === 'Pending Assessment'`
// và list `['Active','Expiring',...]` → lộ nút sai pha / phụ thuộc state suy client.
// Sau fix: nút chỉ render khi allowed_transitions.includes(action) && (can_* ??
// can('training.submit')). Load qua getCompetency(name) (server-driven).
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'

// useApi.run = passthrough (chạy fn thật để verify param phát đi == UI-selection).
const runSpy = vi.fn(async (fn: () => Promise<unknown>) => await fn())
vi.mock('@/composables/useApi', () => ({
  useApi: () => ({ run: runSpy, loading: ref(false), lastError: ref(null) }),
}))

// Capability caller — cấu hình được qua canValue.
let canValue = true
vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({ can: (_cap: string | readonly string[]) => canValue }),
}))

type Comp = Record<string, unknown>
const currentComp = ref<Comp | null>(null)
const getCompetency = vi.fn(async () => {
  if (currentComp.value === null) throw new Error('not found')
  return currentComp.value
})
const signoffCompetency = vi.fn().mockResolvedValue({ name: 'COMP-0001' })
const revokeCompetency = vi.fn().mockResolvedValue({ name: 'COMP-0001' })
const recertifyCompetency = vi.fn().mockResolvedValue({ name: 'COMP-0001' })
const suspendCompetency = vi.fn().mockResolvedValue({ name: 'COMP-0001' })
const restoreCompetency = vi.fn().mockResolvedValue({ name: 'COMP-0001' })
vi.mock('@/api/imm06', () => ({
  getCompetency: () => getCompetency(),
  signoffCompetency: (...a: unknown[]) => signoffCompetency(...a),
  revokeCompetency: (...a: unknown[]) => revokeCompetency(...a),
  recertifyCompetency: (...a: unknown[]) => recertifyCompetency(...a),
  suspendCompetency: (...a: unknown[]) => suspendCompetency(...a),
  restoreCompetency: (...a: unknown[]) => restoreCompetency(...a),
}))

import CompetencyDetailView from '@/views/training/CompetencyDetailView.vue'

function makeComp(over: Comp = {}): Comp {
  return {
    name: 'COMP-0001', user: 'ktv@benhvien.vn', user_full_name: 'Nguyễn Văn A',
    device_model: 'IMM-MDL-0001', device_model_name: 'Dräger Evita V500',
    training_program: 'TRP-0001', competency_level: 'Operator',
    achieved_date: '2026-01-01', expiry_date: '2028-01-01', days_until_expiry: 500,
    workflow_state: 'Active', recertification_due_date: null,
    department_at_assessment: null, last_assessment_score: 88,
    theory_score: 90, practical_score: 86, supervisor_signoff: null,
    signoff_date: null, is_expired: 0,
    allowed_transitions: [], can_signoff: false, can_revoke: false, can_recertify: false,
    can_suspend: false, can_restore: false,
    ...over,
  }
}

// PageHeader stub PHẢI render #actions slot (CTA nằm trong slot đó).
const PageHeaderStub = {
  template: '<div><slot /><slot name="actions" /></div>',
}

async function mountDetail() {
  const w = mount(CompetencyDetailView, {
    props: { name: 'COMP-0001' },
    global: {
      stubs: { PageHeader: PageHeaderStub, StatusBadge: true, RouterLink: true, Transition: false },
      mocks: { $t: (k: string) => k },
    },
  })
  await flushPromises()
  return w
}

const ALL_CTA = ['cta-signoff', 'cta-suspend', 'cta-restore', 'cta-revoke', 'cta-recertify']
function ctasShown(w: Awaited<ReturnType<typeof mountDetail>>): string[] {
  return ALL_CTA.filter((id) => w.find(`[data-testid="${id}"]`).exists())
}

beforeEach(() => {
  canValue = true
  currentComp.value = null
  runSpy.mockClear()
  getCompetency.mockClear()
  signoffCompetency.mockClear()
  revokeCompetency.mockClear()
  recertifyCompetency.mockClear()
  suspendCompetency.mockClear()
  restoreCompetency.mockClear()
})

describe('Competency CTA gating — matrix state × allowed_transitions + capability', () => {
  it("Pending Assessment + allowed=['Sign-off'] + can_signoff=true → CHỈ nút Phê duyệt", async () => {
    currentComp.value = makeComp({
      workflow_state: 'Pending Assessment', allowed_transitions: ['Sign-off'], can_signoff: true,
    })
    const w = await mountDetail()
    expect(ctasShown(w)).toEqual(['cta-signoff'])
  })

  it("Pending Assessment + can_signoff=false (thiếu quyền) → nút Phê duyệt ẨN + hint 'không đủ quyền'", async () => {
    canValue = false
    currentComp.value = makeComp({
      workflow_state: 'Pending Assessment', allowed_transitions: ['Sign-off'], can_signoff: false,
    })
    const w = await mountDetail()
    expect(ctasShown(w)).toEqual([])
    expect(w.find('[data-testid="no-actions-hint"]').exists()).toBe(true)
  })

  it("Active + allowed=['Suspend','Revoke'] → CẢ Tạm ngưng + Thu hồi (KHÔNG Khôi phục/Tái chứng nhận)", async () => {
    currentComp.value = makeComp({
      workflow_state: 'Active', allowed_transitions: ['Suspend', 'Revoke'],
      can_suspend: true, can_revoke: true,
    })
    const w = await mountDetail()
    expect(ctasShown(w)).toEqual(['cta-suspend', 'cta-revoke'])
    expect(w.find('[data-testid="cta-restore"]').exists()).toBe(false)
    expect(w.find('[data-testid="cta-recertify"]').exists()).toBe(false)
  })

  it("Suspended + allowed=['Restore','Revoke'] → CẢ Khôi phục + Thu hồi (parity acceptance)", async () => {
    currentComp.value = makeComp({
      workflow_state: 'Suspended', allowed_transitions: ['Restore', 'Revoke'],
      can_restore: true, can_revoke: true,
    })
    const w = await mountDetail()
    expect(ctasShown(w)).toEqual(['cta-restore', 'cta-revoke'])
    expect(w.find('[data-testid="cta-suspend"]').exists()).toBe(false)
  })

  it("canSuspend/canRestore CHỈ true theo allowed_transitions, KHÔNG theo state thô", async () => {
    // Suspend chỉ khi allowed chứa 'Suspend' — dù state='Active' mà allowed=['Restore']
    // (giả lập) thì hiện Khôi phục theo allowed, KHÔNG Tạm ngưng theo state.
    currentComp.value = makeComp({
      workflow_state: 'Active', allowed_transitions: ['Restore'], can_restore: true, can_suspend: true,
    })
    const w = await mountDetail()
    expect(w.find('[data-testid="cta-restore"]').exists()).toBe(true)
    expect(w.find('[data-testid="cta-suspend"]').exists()).toBe(false)
  })

  it("Suspend/Restore ẩn khi thiếu quyền dù allowed có action → hint 'không đủ quyền'", async () => {
    canValue = false
    currentComp.value = makeComp({
      workflow_state: 'Active', allowed_transitions: ['Suspend', 'Revoke'],
      can_suspend: false, can_revoke: false,
    })
    const w = await mountDetail()
    expect(ctasShown(w)).toEqual([])
    expect(w.find('[data-testid="no-actions-hint"]').exists()).toBe(true)
  })

  it("Expiring + allowed=['Recertify','Revoke'] → CẢ Tái chứng nhận + Thu hồi", async () => {
    currentComp.value = makeComp({
      workflow_state: 'Expiring', days_until_expiry: 30,
      allowed_transitions: ['Recertify', 'Revoke'], can_recertify: true, can_revoke: true,
    })
    const w = await mountDetail()
    expect(ctasShown(w).sort()).toEqual(['cta-recertify', 'cta-revoke'])
    expect(w.find('[data-testid="cta-signoff"]').exists()).toBe(false)
  })

  it("Expired + allowed=['Recertify','Revoke'] → CẢ Tái chứng nhận + Thu hồi", async () => {
    currentComp.value = makeComp({
      workflow_state: 'Expired', days_until_expiry: -5, is_expired: 1,
      allowed_transitions: ['Recertify', 'Revoke'], can_recertify: true, can_revoke: true,
    })
    const w = await mountDetail()
    expect(ctasShown(w).sort()).toEqual(['cta-recertify', 'cta-revoke'])
  })

  it("Revoked (terminal) + allowed=[] → 0 CTA + no-actions-hint", async () => {
    currentComp.value = makeComp({ workflow_state: 'Revoked', allowed_transitions: [] })
    const w = await mountDetail()
    expect(ctasShown(w)).toEqual([])
    expect(w.find('[data-testid="no-actions-hint"]').exists()).toBe(true)
  })

  it('degrade an toàn: allowed_transitions=undefined (BE chưa emit) → 0 CTA + hint', async () => {
    currentComp.value = makeComp({
      workflow_state: 'Active', allowed_transitions: undefined,
      can_signoff: undefined, can_revoke: undefined, can_recertify: undefined,
    })
    const w = await mountDetail()
    expect(ctasShown(w)).toEqual([])
    expect(w.find('[data-testid="no-actions-hint"]').exists()).toBe(true)
  })

  it("KHÔNG suy nút từ state thô: workflow_state='Active' + allowed=['Sign-off'] (giả BE) → hiện Phê duyệt theo allowed, KHÔNG theo state", async () => {
    // Dead-gate cũ: v-if="workflow_state==='Pending Assessment'" → sẽ ẩn Sign-off ở đây.
    // Server-driven: allowed quyết định, KHÔNG state.
    currentComp.value = makeComp({
      workflow_state: 'Active', allowed_transitions: ['Sign-off'], can_signoff: true,
    })
    const w = await mountDetail()
    expect(ctasShown(w)).toEqual(['cta-signoff'])
  })

  it('capability fallback: cờ can_* vắng nhưng can(training.submit)=true + allowed có action → nút hiện', async () => {
    canValue = true
    currentComp.value = makeComp({
      workflow_state: 'Active', allowed_transitions: ['Revoke'],
      can_revoke: undefined,
    })
    const w = await mountDetail()
    expect(w.find('[data-testid="cta-revoke"]').exists()).toBe(true)
  })
})

describe('Competency CTA — anti-dead-control: click phát đúng action tới đúng endpoint', () => {
  it('bấm Phê duyệt → signoffCompetency(name) — không endpoint khác', async () => {
    currentComp.value = makeComp({
      workflow_state: 'Pending Assessment', allowed_transitions: ['Sign-off'], can_signoff: true,
    })
    const w = await mountDetail()
    await w.find('[data-testid="cta-signoff"]').trigger('click')
    await flushPromises()
    expect(signoffCompetency).toHaveBeenCalledTimes(1)
    expect(signoffCompetency).toHaveBeenCalledWith('COMP-0001')
    expect(revokeCompetency).not.toHaveBeenCalled()
    expect(recertifyCompetency).not.toHaveBeenCalled()
  })

  it('bấm Thu hồi → mở modal → nhập lý do → xác nhận → revokeCompetency(name, reason)', async () => {
    currentComp.value = makeComp({
      workflow_state: 'Active', allowed_transitions: ['Revoke'], can_revoke: true,
    })
    const w = await mountDetail()
    await w.find('[data-testid="cta-revoke"]').trigger('click')
    await w.find('textarea').setValue('Vi phạm quy trình vận hành')
    await w.find('[data-testid="confirm-revoke"]').trigger('click')
    await flushPromises()
    expect(revokeCompetency).toHaveBeenCalledTimes(1)
    expect(revokeCompetency).toHaveBeenCalledWith('COMP-0001', 'Vi phạm quy trình vận hành', undefined)
  })

  it('bấm Tái chứng nhận → mở modal → nhập buổi học → xác nhận → recertifyCompetency(name, session)', async () => {
    currentComp.value = makeComp({
      workflow_state: 'Expired', days_until_expiry: -5, is_expired: 1,
      allowed_transitions: ['Recertify', 'Revoke'], can_recertify: true, can_revoke: true,
    })
    const w = await mountDetail()
    await w.find('[data-testid="cta-recertify"]').trigger('click')
    await w.find('input[type="text"]').setValue('TRN-2026-00042')
    await w.find('[data-testid="confirm-recertify"]').trigger('click')
    await flushPromises()
    expect(recertifyCompetency).toHaveBeenCalledTimes(1)
    expect(recertifyCompetency).toHaveBeenCalledWith('COMP-0001', 'TRN-2026-00042')
  })

  it('bấm Tạm ngưng → mở modal → nhập lý do → xác nhận → suspendCompetency(name, reason)', async () => {
    currentComp.value = makeComp({
      workflow_state: 'Active', allowed_transitions: ['Suspend', 'Revoke'],
      can_suspend: true, can_revoke: true,
    })
    const w = await mountDetail()
    await w.find('[data-testid="cta-suspend"]').trigger('click')
    await w.find('#suspend-reason').setValue('Nghi ngờ thao tác sai gây sự cố')
    await w.find('[data-testid="confirm-suspend"]').trigger('click')
    await flushPromises()
    expect(suspendCompetency).toHaveBeenCalledTimes(1)
    expect(suspendCompetency).toHaveBeenCalledWith('COMP-0001', 'Nghi ngờ thao tác sai gây sự cố')
    expect(restoreCompetency).not.toHaveBeenCalled()
    expect(revokeCompetency).not.toHaveBeenCalled()
  })

  it('Tạm ngưng: lý do rỗng → nút xác nhận disabled, KHÔNG gọi suspendCompetency', async () => {
    currentComp.value = makeComp({
      workflow_state: 'Active', allowed_transitions: ['Suspend', 'Revoke'],
      can_suspend: true, can_revoke: true,
    })
    const w = await mountDetail()
    await w.find('[data-testid="cta-suspend"]').trigger('click')
    const confirm = w.find('[data-testid="confirm-suspend"]')
    expect(confirm.attributes('disabled')).toBeDefined()
    await confirm.trigger('click')
    await flushPromises()
    expect(suspendCompetency).not.toHaveBeenCalled()
  })

  it('bấm Khôi phục → mở modal xác nhận → restoreCompetency(name) — không endpoint khác', async () => {
    currentComp.value = makeComp({
      workflow_state: 'Suspended', allowed_transitions: ['Restore', 'Revoke'],
      can_restore: true, can_revoke: true,
    })
    const w = await mountDetail()
    await w.find('[data-testid="cta-restore"]').trigger('click')
    await w.find('[data-testid="confirm-restore"]').trigger('click')
    await flushPromises()
    expect(restoreCompetency).toHaveBeenCalledTimes(1)
    expect(restoreCompetency).toHaveBeenCalledWith('COMP-0001')
    expect(suspendCompetency).not.toHaveBeenCalled()
    expect(revokeCompetency).not.toHaveBeenCalled()
  })
})
