// TC-UX065-1 / -8 / -10 — `PurchaseDetailView` di trú `confirm()` trần → `useModal()`.
//
// 5 call-site (nặng nhất lô 1): tạo phiếu tiếp nhận · duyệt · nhận hàng · huỷ đơn · xoá nháp.
// Điều bộ test này chứng minh — thứ mà `vi.stubGlobal('confirm', () => true)` cũ KHÔNG
// bao giờ chứng minh được:
//   (a) hộp thoại THẬT SỰ hiện, tiêu đề + nội dung tiếng Việt đọc được;
//   (b) bấm «Huỷ» ⇒ KHÔNG có lời gọi API nào (trước đây chỉ là niềm tin);
//   (c) bấm «Xác nhận» ⇒ ĐÚNG 1 lời gọi, payload y như cũ.
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mountWithConfirm, resetModalQueue, currentModal } from '@/test/confirmHarness'
import { ref } from 'vue'

vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())

type Purchase = Record<string, unknown>
const currentDoc = ref<Purchase | null>(null)

const getPurchase = vi.fn(async () => currentDoc.value)
const submitPurchase = vi.fn().mockResolvedValue({ name: 'PO-2026-0001', status: 'Submitted' })
const markReceived = vi.fn().mockResolvedValue({ name: 'PO-2026-0001', status: 'Received' })
const cancelPurchase = vi.fn().mockResolvedValue({ name: 'PO-2026-0001', status: 'Cancelled' })
const deletePurchase = vi.fn().mockResolvedValue({ deleted: 'PO-2026-0001' })

vi.mock('@/api/purchase', () => ({
  getPurchase: () => getPurchase(),
  submitPurchase: (...a: unknown[]) => submitPurchase(...a),
  markReceived: (...a: unknown[]) => markReceived(...a),
  cancelPurchase: (...a: unknown[]) => cancelPurchase(...a),
  deletePurchase: (...a: unknown[]) => deletePurchase(...a),
  getPurchaseMovements: () => Promise.resolve([]),
  getPurchaseCommissionings: () => Promise.resolve([]),
  createReceiptMovement: vi.fn(),
}))
vi.mock('@/api/imm04', () => ({ createCommissioningFromPurchase: vi.fn() }))
vi.mock('@/constants/labels', () => ({ formatStatus: (s: string) => s }))

import PurchaseDetailView from './PurchaseDetailView.vue'

const ALL_APIS = [submitPurchase, markReceived, cancelPurchase, deletePurchase]

function makePurchase(over: Purchase = {}): Purchase {
  return {
    name: 'PO-2026-0001', po_code: 'PO-2026-0001', purchase_date: '2026-07-01',
    supplier: 'SUP-2026-0001', supplier_name: 'Nhà cung cấp A',
    status: 'Draft', docstatus: 0, total_value: 1_000_000,
    items: [], devices: [],
    can_submit: false, can_receive: false, can_cancel: false, can_delete: false,
    ...over,
  }
}

let harness: ReturnType<typeof mountWithConfirm<typeof PurchaseDetailView>> | null = null

async function mountDetail() {
  harness = mountWithConfirm(PurchaseDetailView, {
    props: { name: 'PO-2026-0001' },
    global: {
      stubs: {
        PageHeader: { template: '<div><slot /><slot name="actions" /></div>' },
        SmartSelect: true,
      },
      mocks: { $t: (k: string) => k },
    },
  })
  await flushPromises()
  return harness.wrapper
}

beforeEach(() => { currentDoc.value = null; harness = null; vi.clearAllMocks() })
// TC-UX065-9 — hàng đợi hộp thoại là SINGLETON: không dọn ⇒ test sau thấy "hộp thoại ma".
afterEach(() => { resetModalQueue(); harness?.unmount(); harness = null })

/** Mọi hành động: [testid nút, mock API, kỳ vọng payload, có phá huỷ không]. */
const ACTIONS = [
  { cta: 'cta-submit', api: submitPurchase, doc: { can_submit: true }, danger: false },
  {
    cta: 'cta-receive', api: markReceived,
    doc: { status: 'Submitted', docstatus: 1, can_receive: true }, danger: false,
  },
  {
    cta: 'cta-cancel', api: cancelPurchase,
    doc: { status: 'Submitted', docstatus: 1, can_cancel: true }, danger: true,
  },
  { cta: 'cta-delete', api: deletePurchase, doc: { can_delete: true }, danger: true },
] as const

describe('TC-UX065-1 — PurchaseDetailView: hộp thoại xác nhận thay `confirm()` trần', () => {
  for (const { cta, api, doc } of ACTIONS) {
    it(`[${cta}] bấm nút ⇒ hộp thoại hiện tiếng Việt, CHƯA gọi API`, async () => {
      currentDoc.value = makePurchase(doc)
      const w = await mountDetail()
      const btn = w.find(`[data-testid="${cta}"]`)
      expect(btn.exists(), `không tìm thấy nút ${cta}`).toBe(true)

      await btn.trigger('click')
      await flushPromises()

      const req = currentModal()
      expect(req, 'không có hộp thoại nào mở ⇒ nút vẫn dùng confirm() trần').toBeTruthy()
      expect(req!.title.length).toBeGreaterThan(0)
      expect(req!.body.length).toBeGreaterThan(0)
      // TC-UX065-10: chỉ chữ Việt/số/dấu câu — 0 chữ tiếng Anh lọt ra.
      expect(`${req!.title} ${req!.body}`).not.toMatch(/\b(Confirm|Cancel|Delete|Submit|OK)\b/)
      expect(api).not.toHaveBeenCalled()
    })

    it(`[${cta}] «Huỷ» ⇒ 0 lời gọi API (mọi endpoint)`, async () => {
      currentDoc.value = makePurchase(doc)
      const w = await mountDetail()
      await w.find(`[data-testid="${cta}"]`).trigger('click')
      await flushPromises()
      await harness!.answerConfirm(false)

      for (const spy of ALL_APIS) expect(spy).not.toHaveBeenCalled()
    })

    it(`[${cta}] «Xác nhận» ⇒ ĐÚNG 1 lời gọi với payload cũ (tên đơn)`, async () => {
      currentDoc.value = makePurchase(doc)
      const w = await mountDetail()
      await w.find(`[data-testid="${cta}"]`).trigger('click')
      await flushPromises()
      await harness!.answerConfirm(true)

      expect(api).toHaveBeenCalledTimes(1)
      expect(api).toHaveBeenCalledWith('PO-2026-0001')
      // Không có endpoint nào KHÁC bị gọi lây.
      for (const spy of ALL_APIS) if (spy !== api) expect(spy).not.toHaveBeenCalled()
    })
  }
})

describe("TC-UX065-8 — hành động phá huỷ dùng tone 'error'", () => {
  for (const { cta, doc, danger } of ACTIONS) {
    it(`[${cta}] tone ${danger ? "= 'error' (phá huỷ)" : "KHÔNG phải 'error'"}`, async () => {
      currentDoc.value = makePurchase(doc)
      const w = await mountDetail()
      await w.find(`[data-testid="${cta}"]`).trigger('click')
      await flushPromises()

      const tone = currentModal()!.tone
      if (danger) expect(tone).toBe('error')
      else expect(tone).not.toBe('error')
    })
  }

  it('[cta-delete] card mang class danger; nút xác nhận KHÔNG nhận focus đầu tiên', async () => {
    currentDoc.value = makePurchase({ can_delete: true })
    const w = await mountDetail()
    await w.find('[data-testid="cta-delete"]').trigger('click')
    await flushPromises()

    const modal = harness!.modal
    // `danger` của BaseModal ⇒ tiêu đề đỏ + viền đỏ.
    expect(modal.find('[data-testid="modal-card"] h2').classes()).toContain('text-red-700')
    // Nút phá huỷ KHÔNG được là phần tử nhận focus đầu tiên (gõ Enter theo phản xạ = xoá nhầm).
    const confirmBtn = modal.find('[data-testid="modal-confirm"]').element
    expect(document.activeElement).not.toBe(confirmBtn)
  })
})

describe('TC-UX065-9 — rò rỉ singleton giữa các test', () => {
  it('test này để hộp thoại MỞ rồi kết thúc', async () => {
    currentDoc.value = makePurchase({ can_delete: true })
    const w = await mountDetail()
    await w.find('[data-testid="cta-delete"]').trigger('click')
    await flushPromises()
    expect(currentModal()).toBeTruthy()   // cố ý KHÔNG trả lời
  })

  it('test kế tiếp thấy hàng đợi RỖNG (afterEach đã dọn)', () => {
    expect(currentModal(), 'hộp thoại ma rò từ test trước').toBeUndefined()
  })
})
