// TDD (FE gate) — CR-WF-00-EDIT-AUTHZ: server-driven edit-authz cho Phiếu luân chuyển.
//
// AssetTransferDetailView.isEditable gate 100% theo cờ `can_edit` BE trả trong
// get_transfer_full (BE dẫn xuất từ CÙNG SoT — rbac.require(commissioning.write) +
// status-gate 422 — mà update_transfer enforce). Hoàn tất bộ-ba/bốn transfer-authz
// (approve/receive/cancel/edit) → nút "Lưu thay đổi" + ô nhập hiển thị ⇔ hành động
// thực sự được phép:
//   • can_edit=1 → form mở (ô nhập bật) + nút "Lưu thay đổi" HIỂN THỊ.
//   • can_edit=0/undefined → form khóa (ô nhập disabled) + nút "Lưu thay đổi" ẨN
//     (fail-closed) — KHÔNG suy editable từ status thô (Pending mà thiếu quyền vẫn khóa).
//   • Pending + can_edit=0 → hiện read-only hint (no dead-affordance câm).
//   • Non-Pending (Approved/Received…) → khóa-đọc mặc nhiên, KHÔNG hint thừa.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { resetModalQueue } from '@/test/confirmHarness'

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { id: 'AT-2026-0001' }, query: {}, path: '/asset-transfers/AT-2026-0001' }),
  useRouter: () => ({ push: vi.fn() }),
}))

vi.mock('@/constants/labels', () => ({
  transferTypeLabel: (v: string) => (v === 'Internal' ? 'Nội bộ' : v),
}))

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

// status='Received' terminal ⇒ không editable trừ khi override. Đủ *_name để không rò
// Link-id; received_by rỗng để ẩn block xử lý.
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
})

// Hành động DUY NHẤT mà file này bấm là «Lưu thay đổi» (`save()`), vốn KHÔNG hỏi xác
// nhận — nên không cần harness hộp thoại. lệnh giả lập `confirm` cũ ở đây là
// tàn dư, gỡ đi để không ai tưởng view còn dùng hộp thoại `confirm()` của trình duyệt (AC-UX-066).
afterEach(() => { resetModalQueue() })

describe('AssetTransferDetail — isEditable server-driven (can_edit)', () => {
  it('can_edit=1 + Pending → nút "Lưu thay đổi" HIỂN THỊ + ô "Lý do" bật', async () => {
    const w = await mountWith({ status: 'Pending Approval', can_edit: 1 })
    expect(w.find('[data-testid="transfer-save"]').exists()).toBe(true)
    // ô nhập bật (không disabled) → form mở để sửa
    expect(w.find('[data-testid="field-reason"]').attributes('disabled')).toBeUndefined()
    // không hint read-only khi đang cho sửa
    expect(w.find('[data-testid="transfer-readonly-hint"]').exists()).toBe(false)
  })

  it('can_edit=0 + Pending → "Lưu thay đổi" ẨN + ô "Lý do" disabled + hiện read-only hint', async () => {
    const w = await mountWith({ status: 'Pending Approval', can_edit: 0 })
    expect(w.find('[data-testid="transfer-save"]').exists()).toBe(false)
    // form khóa: ô nhập disabled (fail-closed) — KHÔNG suy editable từ status Pending thô
    expect(w.find('[data-testid="field-reason"]').attributes('disabled')).toBeDefined()
    const hint = w.find('[data-testid="transfer-readonly-hint"]')
    expect(hint.exists()).toBe(true)
    expect(hint.text()).toContain('Bạn không có quyền chỉnh sửa')
  })

  it('can_edit=undefined (BE chưa emit) + Pending → ẨN nút + khóa form (fail-closed)', async () => {
    const w = await mountWith({ status: 'Pending Approval' })
    expect(w.find('[data-testid="transfer-save"]').exists()).toBe(false)
    expect(w.find('[data-testid="field-reason"]').attributes('disabled')).toBeDefined()
    // Pending mà không có quyền → vẫn hiện hint (không im lặng câm)
    expect(w.find('[data-testid="transfer-readonly-hint"]').exists()).toBe(true)
  })

  it('KHÔNG suy editable từ status thô: Approved nhưng can_edit=1 → theo cờ (editable)', async () => {
    // BE status-gate đảm bảo can_edit=0 cho Approved; test này chứng minh FE bám CỜ,
    // KHÔNG hardcode status → nếu cờ khác status, FE theo cờ (server là SoT duy nhất).
    const w = await mountWith({ status: 'Approved', can_edit: 1 })
    expect(w.find('[data-testid="transfer-save"]').exists()).toBe(true)
  })

  it('Non-Pending khóa-đọc mặc nhiên: Received + can_edit=0 → ẨN nút, KHÔNG hint thừa', async () => {
    const w = await mountWith({ status: 'Received', can_edit: 0 })
    expect(w.find('[data-testid="transfer-save"]').exists()).toBe(false)
    expect(w.find('[data-testid="field-reason"]').attributes('disabled')).toBeDefined()
    // read-only hint chỉ cho Pending (phiếu đã xử lý khóa-đọc là mặc nhiên)
    expect(w.find('[data-testid="transfer-readonly-hint"]').exists()).toBe(false)
  })

  it('anti-dead-control: can_edit=1 → bấm "Lưu thay đổi" gọi updateTransfer(name, data) 1 lần', async () => {
    const w = await mountWith({ status: 'Pending Approval', can_edit: 1 })
    await w.find('[data-testid="transfer-save"]').trigger('click')
    await flushPromises()
    expect(updateTransferMock).toHaveBeenCalledTimes(1)
    expect(updateTransferMock.mock.calls[0][0]).toBe('AT-2026-0001')
  })
})
