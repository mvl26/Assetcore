// TDD (FE gate) — CR-WF-00-TRANSFER-AUTHZ: server-driven CTA cho Phiếu luân chuyển.
//
// AssetTransferDetailView gate 4 nút 100% theo cờ capability BE trả trong
// get_transfer_full (BE dẫn xuất từ CÙNG SoT mà approve/receive/delete_transfer
// enforce qua rbac.can):
//   • "Phê duyệt" / "Từ chối" chỉ render khi isPending && can_approve.
//   • "Xác nhận tiếp nhận" (+ textarea bàn giao) chỉ khi isApproved && can_receive.
//   • "Hủy phiếu" chỉ render khi can_cancel (CR-WF-00-CANCEL-AUTHZ) — server-driven,
//     KHÔNG còn suy từ isPending thô (base user KHÔNG được hủy dù phiếu Pending).
//   • Cờ undefined (BE chưa emit) → fail-closed: 0 nút (KHÔNG suy nút từ status thô).
// Anti-dead-control (GATE-6c/LL-FE-47): click nút → gọi ĐÚNG endpoint tương ứng.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { id: 'AT-2026-0001' }, query: {}, path: '/asset-transfers/AT-2026-0001' }),
  useRouter: () => ({ push: vi.fn() }),
}))

vi.mock('@/constants/labels', () => ({
  transferTypeLabel: (v: string) => (v === 'Internal' ? 'Nội bộ' : v),
}))

// Payload get_transfer_full — mutate per-test trước mount.
let transferPayload: Record<string, unknown> = {}
const getTransferFullMock = vi.fn((..._a: unknown[]) => Promise.resolve(transferPayload))
const approveTransferMock = vi.fn().mockResolvedValue({ name: 'AT-2026-0001', status: 'Approved' })
const updateTransferMock = vi.fn().mockResolvedValue({ name: 'AT-2026-0001' })
vi.mock('@/api/imm00', () => ({
  getTransferFull: (...a: unknown[]) => getTransferFullMock(...a),
  updateTransfer: (...a: unknown[]) => updateTransferMock(...a),
  approveTransfer: (...a: unknown[]) => approveTransferMock(...a),
}))
const frappePostMock = vi.fn().mockResolvedValue({})
vi.mock('@/api/helpers', () => ({ frappePost: (...a: unknown[]) => frappePostMock(...a) }))

import AssetTransferDetailView from './AssetTransferDetailView.vue'

// Payload tối thiểu — status='Received' terminal ⇒ không editable/không CTA trừ khi
// override. Đủ *_name để không rò Link-id, received_by rỗng để ẩn block xử lý.
function baseTransfer(over: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    name: 'AT-2026-0001',
    asset: 'ACC-ASS-0001',
    asset_name: 'Máy thở Bennett 840',
    transfer_type: 'Internal',
    transfer_date: '2026-07-01',
    status: 'Received',
    reason: 'Điều chuyển phục vụ khoa Hồi sức',
    notes: '',
    approved_by: '', rejected_by: '', received_by: '',
    from_location_name: 'Khoa Cấp cứu', to_location_name: 'Khoa Hồi sức',
    from_department_name: 'Khoa Cấp cứu', to_department_name: 'Khoa Hồi sức tích cực',
    from_custodian_name: 'Nguyễn Văn A', to_custodian_name: 'Trần Thị B',
    ...over,
  }
}

async function mountWith(extra: Record<string, unknown>) {
  transferPayload = baseTransfer(extra)
  const wrapper = mount(AssetTransferDetailView, {
    global: { stubs: { SmartSelect: true, ApproverSelect: true, DateInput: true } },
  })
  await flushPromises()
  return wrapper
}

beforeEach(() => {
  getTransferFullMock.mockClear()
  approveTransferMock.mockClear()
  updateTransferMock.mockClear()
  frappePostMock.mockClear()
  // View dùng window.confirm() trước khi gọi API — mặc định cho phép để test click.
  vi.stubGlobal('confirm', vi.fn(() => true))
})

describe('AssetTransferDetail CTA — Phê duyệt/Từ chối (isPending && can_approve)', () => {
  it('can_approve=1 + Pending → "Phê duyệt" & "Từ chối" HIỂN THỊ', async () => {
    const w = await mountWith({ status: 'Pending Approval', can_approve: 1, can_receive: 0 })
    expect(w.find('[data-testid="cta-approve"]').exists()).toBe(true)
    expect(w.find('[data-testid="cta-reject"]').exists()).toBe(true)
    expect(w.find('[data-testid="cta-receive"]').exists()).toBe(false)
  })

  it('can_approve=0 + Pending → "Phê duyệt" & "Từ chối" ẨN (no dead-button)', async () => {
    const w = await mountWith({ status: 'Pending Approval', can_approve: 0, can_receive: 0 })
    expect(w.find('[data-testid="cta-approve"]').exists()).toBe(false)
    expect(w.find('[data-testid="cta-reject"]').exists()).toBe(false)
    // "Hủy phiếu" cũng server-driven: can_cancel chưa set → fail-closed, nút ẨN
    // (base user Pending KHÔNG còn tự động thấy nút Hủy).
    expect(w.find('[data-testid="cta-cancel"]').exists()).toBe(false)
  })

  it('can_approve=1 nhưng can_cancel chưa set → nút Hủy vẫn ẨN (độc lập với approve)', async () => {
    const w = await mountWith({ status: 'Pending Approval', can_approve: 1 })
    expect(w.find('[data-testid="cta-approve"]').exists()).toBe(true)
    expect(w.find('[data-testid="cta-cancel"]').exists()).toBe(false)
  })

  it('can_approve=undefined (BE chưa emit) + Pending → ẨN (fail-closed)', async () => {
    const w = await mountWith({ status: 'Pending Approval' })
    expect(w.find('[data-testid="cta-approve"]').exists()).toBe(false)
    expect(w.find('[data-testid="cta-reject"]').exists()).toBe(false)
  })
})

describe('AssetTransferDetail CTA — Xác nhận tiếp nhận (isApproved && can_receive)', () => {
  it('can_receive=1 + Approved → "Xác nhận tiếp nhận" + textarea bàn giao HIỂN THỊ', async () => {
    const w = await mountWith({ status: 'Approved', can_approve: 0, can_receive: 1 })
    expect(w.find('[data-testid="cta-receive"]').exists()).toBe(true)
    // textarea bàn giao đi kèm quyền tiếp nhận
    expect(w.text()).toContain('Ghi chú bàn giao')
    expect(w.find('[data-testid="transfer-no-actions-hint"]').exists()).toBe(false)
  })

  it('can_receive=0 + Approved → "Xác nhận tiếp nhận" ẨN + hiện hint (no dead-button)', async () => {
    const w = await mountWith({ status: 'Approved', can_approve: 0, can_receive: 0 })
    expect(w.find('[data-testid="cta-receive"]').exists()).toBe(false)
    expect(w.text()).not.toContain('Ghi chú bàn giao')
    const hint = w.find('[data-testid="transfer-no-actions-hint"]')
    expect(hint.exists()).toBe(true)
    expect(hint.text()).toContain('Bạn không có quyền thao tác phiếu này')
  })

  it('can_receive=undefined (BE chưa emit) + Approved → ẨN (fail-closed)', async () => {
    const w = await mountWith({ status: 'Approved' })
    expect(w.find('[data-testid="cta-receive"]').exists()).toBe(false)
  })

  it('KHÔNG suy nút từ status thô: Approved nhưng can_receive=0 → nút ẨN', async () => {
    const w = await mountWith({ status: 'Approved', can_receive: 0 })
    expect(w.find('[data-testid="cta-receive"]').exists()).toBe(false)
  })
})

describe('AssetTransferDetail CTA — Hủy phiếu (server-driven can_cancel)', () => {
  it('can_cancel=1 + Pending → nút "Hủy phiếu" HIỂN THỊ', async () => {
    const w = await mountWith({ status: 'Pending Approval', can_approve: 0, can_cancel: 1 })
    expect(w.find('[data-testid="cta-cancel"]').exists()).toBe(true)
  })

  it('can_cancel=1 + Rejected → nút "Hủy phiếu" HIỂN THỊ (không suy từ isPending)', async () => {
    const w = await mountWith({ status: 'Rejected', can_cancel: 1 })
    expect(w.find('[data-testid="cta-cancel"]').exists()).toBe(true)
  })

  it('can_cancel=0 + Pending → nút "Hủy phiếu" ẨN (base user, no dead-button)', async () => {
    const w = await mountWith({ status: 'Pending Approval', can_approve: 0, can_cancel: 0 })
    expect(w.find('[data-testid="cta-cancel"]').exists()).toBe(false)
  })

  it('can_cancel=undefined (BE chưa emit) + Pending → ẨN (fail-closed)', async () => {
    const w = await mountWith({ status: 'Pending Approval' })
    expect(w.find('[data-testid="cta-cancel"]').exists()).toBe(false)
  })

  it('bấm "Hủy phiếu" → frappePost delete_transfer đúng param', async () => {
    const w = await mountWith({ status: 'Pending Approval', can_cancel: 1 })
    await w.find('[data-testid="cta-cancel"]').trigger('click')
    await flushPromises()
    expect(frappePostMock).toHaveBeenCalledTimes(1)
    expect(frappePostMock).toHaveBeenCalledWith(
      '/api/method/assetcore.api.imm00.delete_transfer',
      expect.objectContaining({ name: 'AT-2026-0001' }),
    )
  })
})

describe('AssetTransferDetail CTA — anti-dead-control: click phát đúng endpoint', () => {
  it('bấm "Phê duyệt" → approveTransfer(name) gọi 1 lần + refetch', async () => {
    const w = await mountWith({ status: 'Pending Approval', can_approve: 1 })
    expect(getTransferFullMock).toHaveBeenCalledTimes(1)
    await w.find('[data-testid="cta-approve"]').trigger('click')
    await flushPromises()
    expect(approveTransferMock).toHaveBeenCalledTimes(1)
    expect(approveTransferMock).toHaveBeenCalledWith('AT-2026-0001')
    expect(getTransferFullMock).toHaveBeenCalledTimes(2) // refetch sau duyệt
  })

  it('bấm "Xác nhận tiếp nhận" → frappePost receive_transfer đúng param', async () => {
    const w = await mountWith({ status: 'Approved', can_receive: 1 })
    await w.find('[data-testid="cta-receive"]').trigger('click')
    await flushPromises()
    expect(frappePostMock).toHaveBeenCalledTimes(1)
    expect(frappePostMock).toHaveBeenCalledWith(
      '/api/method/assetcore.api.imm00.receive_transfer',
      expect.objectContaining({ name: 'AT-2026-0001' }),
    )
  })
})
