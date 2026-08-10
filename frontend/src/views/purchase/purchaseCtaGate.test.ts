// TDD (FE regression guard) — GATE-8 / LL-FE-51: server-driven CTA cho Đơn mua hàng.
//
// PurchaseDetailView gate 100% nút hành động đổi-trạng-thái (Duyệt đơn / Xác nhận
// nhận hàng / Huỷ đơn + "+ Tạo phiếu nhập kho") theo cờ SERVER-derived
// can_submit / can_receive / can_cancel (get_purchase derive từ capability +
// docstatus + status) — KHÔNG hardcode docstatus===0 / status==='Submitted'.
//
// RED trước fix (dead-gate + RBAC bypass): nút render bằng v-if="docstatus===0"
// v.v. → MỌI user login thấy nút "Duyệt đơn" rồi bấm → BE cũ db_set/ignore_permissions
// cho qua (leo quyền). Sau fix: nút chỉ render khi can_* === true; thiếu cờ (BE cũ
// chưa emit) → 0 nút (degrade an toàn, KHÔNG dead-control 403-khi-bấm).
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { mountWithConfirm, resetModalQueue } from '@/test/confirmHarness'
import { ref } from 'vue'

vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())

type Purchase = Record<string, unknown>
const currentDoc = ref<Purchase | null>(null)

const getPurchase = vi.fn(async () => currentDoc.value)
const submitPurchase = vi.fn().mockResolvedValue({ name: 'PO-2026-0001', status: 'Submitted' })
const markReceived = vi.fn().mockResolvedValue({ name: 'PO-2026-0001', status: 'Received' })
const cancelPurchase = vi.fn().mockResolvedValue({ name: 'PO-2026-0001', status: 'Cancelled' })
const deletePurchase = vi.fn().mockResolvedValue({ deleted: 'PO-2026-0001' })
const getPurchaseMovements = vi.fn().mockResolvedValue([])
const getPurchaseCommissionings = vi.fn().mockResolvedValue([])
const createReceiptMovement = vi.fn().mockResolvedValue({ movement_name: 'MOV-2026-0001', status: 'Draft' })

vi.mock('@/api/purchase', () => ({
  getPurchase: () => getPurchase(),
  submitPurchase: (...a: unknown[]) => submitPurchase(...a),
  markReceived: (...a: unknown[]) => markReceived(...a),
  cancelPurchase: (...a: unknown[]) => cancelPurchase(...a),
  deletePurchase: (...a: unknown[]) => deletePurchase(...a),
  getPurchaseMovements: () => getPurchaseMovements(),
  getPurchaseCommissionings: () => getPurchaseCommissionings(),
  createReceiptMovement: (...a: unknown[]) => createReceiptMovement(...a),
}))
vi.mock('@/api/imm04', () => ({
  createCommissioningFromPurchase: vi.fn().mockResolvedValue({ name: 'COM-2026-0001' }),
}))
vi.mock('@/constants/labels', () => ({ formatStatus: (s: string) => s }))

import PurchaseDetailView from './PurchaseDetailView.vue'

function makePurchase(over: Purchase = {}): Purchase {
  return {
    name: 'PO-2026-0001', po_code: 'PO-2026-0001', purchase_date: '2026-07-01',
    supplier: 'SUP-2026-0001', supplier_name: 'Nhà cung cấp A',
    status: 'Draft', docstatus: 0, total_value: 1000000,
    items: [{ spare_part: 'SP-1', part_name: 'Phụ tùng 1', qty: 1 }], devices: [],
    can_submit: false, can_receive: false, can_cancel: false,
    ...over,
  }
}

// AC-UX-066: view đã bỏ hộp thoại `confirm()` của trình duyệt → dùng `useModal()`. Hàng đợi hộp thoại là
// SINGLETON module-level, nên mount view ĐƠN LẺ sẽ treo ở `await modal.confirm(...)`
// (không ai render để bấm trả lời) ⇒ API không bao giờ được gọi và test "xanh" giả.
// `mountWithConfirm` mount kèm `NotificationModal`; `answerConfirm` bấm nút THẬT.
let harness: ReturnType<typeof mountWithConfirm<typeof PurchaseDetailView>> | null = null

async function mountDetail() {
  harness = mountWithConfirm(PurchaseDetailView, {
    props: { name: 'PO-2026-0001' },
    global: {
      // PageHeader phải render slot #actions (nút Duyệt/Nhận hàng/Huỷ nằm trong đó).
      stubs: {
        PageHeader: { template: '<div><slot /><slot name="actions" /></div>' },
        SmartSelect: true,
        Teleport: true,
      },
      mocks: { $t: (k: string) => k },
    },
  })
  await flushPromises()
  return harness.wrapper
}

/** Trả lời hộp thoại xác nhận đang mở (bấm «Xác nhận» / «Huỷ» thật trong DOM). */
async function answerConfirm(ok: boolean) {
  if (!harness) throw new Error('mountDetail() chưa chạy')
  await harness.answerConfirm(ok)
}

const APPROVAL_CTA = ['cta-submit', 'cta-receive', 'cta-cancel']
function approvalCtasShown(w: Awaited<ReturnType<typeof mountDetail>>): string[] {
  return APPROVAL_CTA.filter((id) => w.find(`[data-testid="${id}"]`).exists())
}

beforeEach(() => {
  currentDoc.value = null
  harness = null
  vi.clearAllMocks()
})
afterEach(() => {
  // KHÔNG reset ⇒ hộp thoại của test trước còn treo trong hàng đợi singleton và test
  // sau trả lời nhầm nó ("hộp thoại ma").
  resetModalQueue()
  harness?.unmount()
  harness = null
})

describe('Purchase CTA gating — hiển thị nút theo can_* server flags', () => {
  it('draft authorized (can_submit=true) → nút "Duyệt đơn" HIỂN THỊ, receive/cancel ẨN', async () => {
    currentDoc.value = makePurchase({ status: 'Draft', docstatus: 0, can_submit: true })
    const w = await mountDetail()
    expect(w.find('[data-testid="cta-submit"]').exists()).toBe(true)
    expect(w.find('[data-testid="cta-receive"]').exists()).toBe(false)
    expect(w.find('[data-testid="cta-cancel"]').exists()).toBe(false)
  })

  it('submitted authorized (can_receive+can_cancel=true) → nút Nhận hàng + Huỷ HIỂN THỊ, Duyệt ẨN', async () => {
    currentDoc.value = makePurchase({
      status: 'Submitted', docstatus: 1, can_submit: false, can_receive: true, can_cancel: true,
    })
    const w = await mountDetail()
    expect(w.find('[data-testid="cta-submit"]').exists()).toBe(false)
    expect(w.find('[data-testid="cta-receive"]').exists()).toBe(true)
    expect(w.find('[data-testid="cta-cancel"]').exists()).toBe(true)
    // Nút "+ Tạo phiếu nhập kho" theo canCreateReceipt (fallback can_receive)
    expect(w.find('[data-testid="cta-create-receipt"]').exists()).toBe(true)
  })

  it('auditor (chỉ xem, mọi cờ false) → 0 nút duyệt', async () => {
    currentDoc.value = makePurchase({
      status: 'Submitted', docstatus: 1, can_submit: false, can_receive: false, can_cancel: false,
    })
    const w = await mountDetail()
    expect(approvalCtasShown(w)).toEqual([])
    expect(w.find('[data-testid="cta-create-receipt"]').exists()).toBe(false)
  })
})

describe('Purchase CTA — anti-dead-control (chống hardcode docstatus/status)', () => {
  it('docstatus===1 & status==="Submitted" NHƯNG can_receive=false → KHÔNG render nút Nhận hàng', async () => {
    // Trước đây hardcode v-if="docstatus===1 && status==='Submitted'" → luôn hiện →
    // 403 khi bấm. Giờ gate theo can_receive server flag.
    currentDoc.value = makePurchase({
      status: 'Submitted', docstatus: 1, can_submit: false, can_receive: false, can_cancel: true,
    })
    const w = await mountDetail()
    expect(w.find('[data-testid="cta-receive"]').exists()).toBe(false)
    expect(w.find('[data-testid="cta-create-receipt"]').exists()).toBe(false)
    // can_cancel vẫn true → nút Huỷ hiển thị (gate độc lập theo từng cờ)
    expect(w.find('[data-testid="cta-cancel"]').exists()).toBe(true)
  })

  it('docstatus===0 NHƯNG can_submit=false (Procurement User không quyền submit) → KHÔNG render nút Duyệt', async () => {
    currentDoc.value = makePurchase({ status: 'Draft', docstatus: 0, can_submit: false })
    const w = await mountDetail()
    expect(w.find('[data-testid="cta-submit"]').exists()).toBe(false)
  })
})

describe('Purchase CTA — degrade an toàn khi BE cũ chưa emit cờ', () => {
  it('thiếu can_* (undefined) → 0 nút duyệt render', async () => {
    currentDoc.value = makePurchase({
      status: 'Submitted', docstatus: 1,
      can_submit: undefined, can_receive: undefined, can_cancel: undefined, can_create_receipt: undefined,
    })
    const w = await mountDetail()
    expect(approvalCtasShown(w)).toEqual([])
    expect(w.find('[data-testid="cta-create-receipt"]').exists()).toBe(false)
  })
})

describe('Purchase CTA — click phát đúng action tới đúng endpoint (param == UI)', () => {
  it('bấm "Duyệt đơn" → submitPurchase(name)', async () => {
    currentDoc.value = makePurchase({ status: 'Draft', docstatus: 0, can_submit: true })
    const w = await mountDetail()
    await w.find('[data-testid="cta-submit"]').trigger('click')
    await flushPromises()
    // Hộp thoại xác nhận mở TRƯỚC, API chưa được gọi.
    expect(submitPurchase).not.toHaveBeenCalled()
    await answerConfirm(true)
    expect(submitPurchase).toHaveBeenCalledTimes(1)
    expect(submitPurchase).toHaveBeenCalledWith('PO-2026-0001')
  })

  it('bấm "Xác nhận nhận hàng" → markReceived(name)', async () => {
    currentDoc.value = makePurchase({
      status: 'Submitted', docstatus: 1, can_submit: false, can_receive: true, can_cancel: true,
    })
    const w = await mountDetail()
    await w.find('[data-testid="cta-receive"]').trigger('click')
    await flushPromises()
    // Hộp thoại xác nhận mở TRƯỚC, API chưa được gọi.
    expect(markReceived).not.toHaveBeenCalled()
    await answerConfirm(true)
    expect(markReceived).toHaveBeenCalledTimes(1)
    expect(markReceived).toHaveBeenCalledWith('PO-2026-0001')
  })

  it('bấm "Huỷ đơn" → cancelPurchase(name)', async () => {
    currentDoc.value = makePurchase({
      status: 'Submitted', docstatus: 1, can_submit: false, can_receive: false, can_cancel: true,
    })
    const w = await mountDetail()
    await w.find('[data-testid="cta-cancel"]').trigger('click')
    await flushPromises()
    // Hộp thoại xác nhận mở TRƯỚC, API chưa được gọi.
    expect(cancelPurchase).not.toHaveBeenCalled()
    await answerConfirm(true)
    expect(cancelPurchase).toHaveBeenCalledTimes(1)
    expect(cancelPurchase).toHaveBeenCalledWith('PO-2026-0001')
  })
})
