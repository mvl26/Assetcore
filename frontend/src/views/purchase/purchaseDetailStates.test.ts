// Copyright (c) 2026, AssetCore Team
// TC-UX4-47 (docs/ui-ux/03 §13.6) — PurchaseDetailView áp khuôn `DetailPageShell` (lô 2, nhóm N3).
//
// RED trước fix: (1) lỗi nạp đi `toast` — một dải chữ TỰ TẮT sau 3,5 giây, để lại trang trắng
// không lối thoát; (2) `Promise.all` gộp 3 lời gọi ⇒ 1×403 ở phiếu nhập kho hoặc phiếu tiếp nhận
// (dữ liệu PHỤ) làm TRẮNG cả màn đơn mua hàng (LL-FE-45); (3) 5 CTA duyệt nằm trong `PageHeader`
// thứ hai, vùng hiện ở mọi trạng thái. Sau fix: shell + `allSettled` + slot `#actions`.
import { ref } from 'vue'
import { vi, describe, it, expect } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import type { Purchase } from '@/api/purchase'
import { describeDetailStates, networkError } from '@/test/detailStatesHarness'

const pushSpy = vi.fn()
vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { name: 'PO-2026-0001' } }),
  useRouter: () => ({ push: pushSpy, back: vi.fn() }),
}))

vi.mock('@/composables/useNotify', () => ({
  useNotify: () => ({ show: vi.fn(), fromError: vi.fn(), fromOk: vi.fn(), confirm: vi.fn() }),
}))

const getPurchaseSpy = vi.fn()
const getPurchaseMovementsSpy = vi.fn().mockResolvedValue([])
const getPurchaseCommissioningsSpy = vi.fn().mockResolvedValue([])
vi.mock('@/api/purchase', () => ({
  getPurchase: () => getPurchaseSpy(),
  submitPurchase: vi.fn(),
  markReceived: vi.fn(),
  cancelPurchase: vi.fn(),
  deletePurchase: vi.fn(),
  getPurchaseMovements: () => getPurchaseMovementsSpy(),
  getPurchaseCommissionings: () => getPurchaseCommissioningsSpy(),
  createReceiptMovement: vi.fn(),
}))
vi.mock('@/api/imm04', () => ({ createCommissioningFromPurchase: vi.fn() }))

import PurchaseDetailView from './PurchaseDetailView.vue'

const stubs = { SmartSelect: true, CurrencyInput: true, DateInput: true, RouterLink: true }

function purchaseFixture(): Purchase {
  return {
    name: 'PO-2026-0001',
    po_code: 'PO-2026-0001',
    purchase_date: '2026-07-01',
    status: 'Draft',
    docstatus: 0,
    supplier: 'SUP-2026-00012',
    supplier_name: 'Công ty TNHH Thiết bị Y tế Minh Anh',
    items: [],
    can_submit: true,
  } as unknown as Purchase
}

function mountView() {
  return mount(PurchaseDetailView, { props: { name: 'PO-2026-0001' }, global: { stubs } })
}

describeDetailStates({
  view: 'PurchaseDetailView',
  tc: 'TC-UX4-47',
  mount: () => mountView() as never,
  pending: () => getPurchaseSpy.mockReturnValue(new Promise(() => {})),
  fail: (e) => getPurchaseSpy.mockRejectedValue(e),
  empty: () => getPurchaseSpy.mockResolvedValue(null),
  ok: () => getPurchaseSpy.mockResolvedValue(purchaseFixture()),
  loadCalls: () => getPurchaseSpy.mock.calls.length,
  reset: () => {
    getPurchaseSpy.mockReset()
    getPurchaseMovementsSpy.mockClear().mockResolvedValue([])
    getPurchaseCommissioningsSpy.mockClear().mockResolvedValue([])
    pushSpy.mockClear()
  },
  recordId: 'PO-2026-0001',
  ctaTestIds: ['cta-edit', 'cta-delete', 'cta-submit', 'cta-receive', 'cta-cancel'],
  routerPush: pushSpy,
})

describe('PurchaseDetailView — nguồn PHỤ hỏng KHÔNG làm trắng màn (LL-FE-45)', () => {
  it('403 ở phiếu nhập kho + phiếu tiếp nhận ⇒ vẫn render content của đơn mua hàng', async () => {
    getPurchaseSpy.mockReset().mockResolvedValue(purchaseFixture())
    getPurchaseMovementsSpy.mockReset().mockRejectedValue(networkError('403 phiếu nhập kho'))
    getPurchaseCommissioningsSpy.mockReset().mockRejectedValue(networkError('403 phiếu tiếp nhận'))
    const w = mountView()
    await flushPromises()
    expect(w.attributes('data-state')).toBe('content')
    expect(w.find('[data-testid="detail-load-error"]').exists()).toBe(false)
    expect(w.text()).toContain('PO-2026-0001')
  })
})
