// TDD (FE regression guard) — GATE-8 / LL-FE-51 + LL-FE-47: server-driven CTA cho
// IMM-14 biên bản giải nhiệm.
//
// DecommissionDetailView gate nút "Duyệt giải nhiệm" 100% theo cờ BE
// `record.can_approve === 1` (BE dẫn xuất từ CÙNG SoT mà approve_decommission
// enforce) — KHÔNG hardcode docstatus/workflow_state==='X'. can_approve=0/undefined
// → KHÔNG render nút; hiện no-actions-hint với approve_blocked_reason (no dead-control).
//
// Cũng khoá: render tên (asset_name/responsible_name) KHÔNG rò asset-id/User-email;
// nhãn disposal_method + badge trạng thái qua SSoT tiếng Việt.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'

vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())

const notifyShow = vi.fn()
const notifyFromError = vi.fn()
const notifyConfirm = vi.fn().mockResolvedValue(true)
vi.mock('@/composables/useNotify', () => ({
  useNotify: () => ({
    show: notifyShow, fromError: notifyFromError, fromOk: vi.fn(), confirm: notifyConfirm,
  }),
}))

// useApi.run = passthrough (chạy fn thật → verify param phát đi == UI-selection).
const runSpy = vi.fn(async (fn: () => Promise<unknown>) => await fn())
vi.mock('@/composables/useApi', () => ({
  useApi: () => ({ run: runSpy, loading: ref(false), lastError: ref(null) }),
}))

type Rec = Record<string, unknown>
const currentRecord = ref<Rec | null>(null)
const getDecommission = vi.fn(async () => currentRecord.value)
const approveDecommission = vi.fn().mockResolvedValue({
  name: 'DECOM-2026-0007', asset: 'AC-ASSET-2026-00407',
  workflow_state: 'Approved', docstatus: 1,
  lifecycle_status: 'Decommissioned', decommissioned_on: '2026-07-10 10:00:00',
})
vi.mock('@/api/imm14', () => ({
  getDecommission: () => getDecommission(),
  approveDecommission: (...args: unknown[]) => approveDecommission(...args),
}))

import DecommissionDetailView from './DecommissionDetailView.vue'

function makeRecord(over: Rec = {}): Rec {
  return {
    name: 'DECOM-2026-0007', asset: 'AC-ASSET-2026-00407',
    asset_name: 'Máy thở Hamilton C6', asset_name_snapshot: 'Máy thở Hamilton C6',
    responsible: 'nva@benhvien.test', responsible_name: 'Nguyễn Văn A',
    disposal_method: 'Bán/Trade-in',
    decommission_reason: 'Thiết bị hết khấu hao, sửa chữa không kinh tế, đã có QĐ thanh lý.',
    patient_data_sanitized: 1, sanitization_note: 'Đã xoá ổ cứng theo NIST 800-88.',
    risk_classification_snapshot: 'Critical',
    workflow_state: 'Draft', docstatus: 0, lifecycle_status: 'Active',
    decommissioned_on: null,
    can_approve: 1, approve_blocked_reason: '',
    ...over,
  }
}

async function mountDetail() {
  const w = mount(DecommissionDetailView, {
    props: { id: 'DECOM-2026-0007' },
    global: { stubs: { PageHeader: true, SkeletonLoader: true, RouterLink: true, Transition: false } },
  })
  await flushPromises()
  return w
}

beforeEach(() => {
  currentRecord.value = null
  getDecommission.mockClear()
  approveDecommission.mockClear()
  notifyShow.mockClear()
  notifyFromError.mockClear()
  notifyConfirm.mockClear()
  runSpy.mockClear()
})

describe('DecommissionDetail CTA — server-driven can_approve (GATE-8/LL-FE-51)', () => {
  it('can_approve=1 → nút "Duyệt giải nhiệm" HIỂN THỊ', async () => {
    currentRecord.value = makeRecord({ can_approve: 1 })
    const w = await mountDetail()
    expect(w.find('[data-testid="cta-approve"]').exists()).toBe(true)
    expect(w.find('[data-testid="no-actions-hint"]').exists()).toBe(false)
  })

  it('can_approve=0 + approve_blocked_reason → nút ẨN + hiện hint lý do (no dead-control)', async () => {
    currentRecord.value = makeRecord({
      can_approve: 0,
      approve_blocked_reason: 'Bạn không đủ quyền duyệt hồ sơ giải nhiệm.',
      // docstatus vẫn 0 để chứng minh CTA KHÔNG suy từ docstatus thô.
      docstatus: 0, workflow_state: 'Draft',
    })
    const w = await mountDetail()
    expect(w.find('[data-testid="cta-approve"]').exists()).toBe(false)
    const hint = w.find('[data-testid="no-actions-hint"]')
    expect(hint.exists()).toBe(true)
    expect(hint.text()).toContain('Bạn không đủ quyền duyệt hồ sơ giải nhiệm.')
  })

  it('KHÔNG suy nút từ docstatus thô: docstatus=0/Draft nhưng can_approve=0 → nút ẨN', async () => {
    currentRecord.value = makeRecord({
      docstatus: 0, workflow_state: 'Draft', can_approve: 0,
      approve_blocked_reason: 'Đã có hồ sơ khác giải nhiệm thiết bị này.',
    })
    const w = await mountDetail()
    expect(w.find('[data-testid="cta-approve"]').exists()).toBe(false)
  })

  it('can_approve=undefined (BE chưa emit) → nút ẨN + KHÔNG hint thừa (degrade an toàn)', async () => {
    currentRecord.value = makeRecord({ can_approve: undefined, approve_blocked_reason: undefined })
    const w = await mountDetail()
    expect(w.find('[data-testid="cta-approve"]').exists()).toBe(false)
    expect(w.find('[data-testid="no-actions-hint"]').exists()).toBe(false)
  })
})

describe('DecommissionDetail CTA — anti-dead-control: click phát đúng approveDecommission', () => {
  it('bấm Duyệt → approveDecommission(name) gọi ĐÚNG 1 lần + refetch', async () => {
    currentRecord.value = makeRecord({ can_approve: 1 })
    const w = await mountDetail()
    expect(getDecommission).toHaveBeenCalledTimes(1)
    await w.find('[data-testid="cta-approve"]').trigger('click')
    await flushPromises()
    expect(notifyConfirm).toHaveBeenCalledTimes(1)        // BaseModal confirm, KHÔNG window.confirm
    expect(approveDecommission).toHaveBeenCalledTimes(1)
    expect(approveDecommission).toHaveBeenCalledWith('DECOM-2026-0007')
    expect(notifyShow).toHaveBeenCalled()                 // success qua useNotify (registry MSG)
    expect(getDecommission).toHaveBeenCalledTimes(2)      // refetch sau duyệt
  })

  it('user huỷ hộp thoại xác nhận → KHÔNG gọi approveDecommission', async () => {
    notifyConfirm.mockResolvedValueOnce(false)
    currentRecord.value = makeRecord({ can_approve: 1 })
    const w = await mountDetail()
    await w.find('[data-testid="cta-approve"]').trigger('click')
    await flushPromises()
    expect(approveDecommission).not.toHaveBeenCalled()
  })
})

describe('DecommissionDetail render — nhãn VI + KHÔNG rò id/email', () => {
  it('hiển thị asset_name + responsible_name, KHÔNG rò asset-id/User-email thô', async () => {
    currentRecord.value = makeRecord()
    const w = await mountDetail()
    const txt = w.text()
    expect(txt).toContain('Máy thở Hamilton C6')      // asset_name
    expect(txt).toContain('Nguyễn Văn A')             // responsible_name
    expect(txt).not.toContain('nva@benhvien.test')    // KHÔNG email
    expect(txt).not.toContain('@')
    expect(txt).not.toContain('AC-ASSET-2026-00407')  // KHÔNG asset-id thô
  })

  it('disposal_method render nhãn VI qua SSoT (dịch phần EN Trade-in), KHÔNG leak EN', async () => {
    currentRecord.value = makeRecord({ disposal_method: 'Bán/Trade-in' })
    const w = await mountDetail()
    const disposal = w.find('[data-testid="decom-disposal"]')
    expect(disposal.text()).toBe('Bán/Thu cũ đổi mới')
    expect(w.text()).not.toContain('Trade-in')
    expect(w.text()).not.toContain('Donation')
  })

  it('badge trạng thái: Draft → "Chờ duyệt" (KHÔNG "Bản nháp"/"Draft")', async () => {
    currentRecord.value = makeRecord({ workflow_state: 'Draft' })
    const w = await mountDetail()
    const badge = w.find('[data-testid="decom-state-badge"]')
    expect(badge.text()).toBe('Chờ duyệt')
    expect(w.text()).not.toMatch(/\bDraft\b/)
  })

  it('badge trạng thái: Approved → "Đã giải nhiệm"', async () => {
    currentRecord.value = makeRecord({ workflow_state: 'Approved', can_approve: 0, docstatus: 1 })
    const w = await mountDetail()
    expect(w.find('[data-testid="decom-state-badge"]').text()).toBe('Đã giải nhiệm')
    expect(w.text()).not.toContain('Approved')
  })

  it('a11y: nút Duyệt có aria-describedby (mô tả hậu quả không hoàn tác)', async () => {
    currentRecord.value = makeRecord({ can_approve: 1 })
    const w = await mountDetail()
    expect(w.find('[data-testid="cta-approve"]').attributes('aria-describedby')).toBeTruthy()
  })
})
