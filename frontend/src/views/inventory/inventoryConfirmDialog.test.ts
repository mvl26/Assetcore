// TC-UX065-2 / -3 / -8 / -10 — lô 1 nhánh kho: `UomConversionView` (4 call-site) và
// `StockMovementDetailView` (3 call-site) di trú `confirm()` trần → `useModal()`.
//
// Cả hai màn cùng tiêu thụ `@/api/inventory` nên dùng CHUNG một lần giả lập module.
// Bộ test chứng minh 3 điều mà giả lập `confirm` cũ không chứng minh được: hộp thoại
// hiện thật · «Huỷ» ⇒ 0 lời gọi API · «Xác nhận» ⇒ đúng 1 lời gọi với payload cũ.
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mountWithConfirm, resetModalQueue, currentModal } from '@/test/confirmHarness'
import { ref } from 'vue'

vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())

// ── Giả lập @/api/inventory (dùng cho CẢ hai màn) ────────────────────────────
const deleteUom = vi.fn().mockResolvedValue({ soft_deleted: 0 })
const seedAcUoms = vi.fn().mockResolvedValue({ count: 12 })
const bulkAssignDefaultUom = vi.fn().mockResolvedValue({ assigned: 5 })
const removeUomConversion = vi.fn().mockResolvedValue({})
const submitStockMovement = vi.fn().mockResolvedValue({ name: 'MOV-2026-0001' })
const cancelStockMovement = vi.fn().mockResolvedValue({ name: 'MOV-2026-0001' })
const deleteStockMovement = vi.fn().mockResolvedValue({ deleted: 'MOV-2026-0001' })

const uomRows = [{ name: 'Cái', uom_name: 'Cái', symbol: 'c', is_active: 1, use_count: 0, description: '' }]
const currentMovement = ref<Record<string, unknown> | null>(null)

vi.mock('@/api/inventory', () => ({
  listUomsFull: vi.fn(async () => ({ items: uomRows, total: uomRows.length })),
  createUom: vi.fn(), updateUom: vi.fn(),
  deleteUom: (...a: unknown[]) => deleteUom(...a),
  seedAcUoms: (...a: unknown[]) => seedAcUoms(...a),
  listPartsUom: vi.fn(async () => ({ items: [], total: 0 })),
  listPartsMissingUom: vi.fn(async () => ({ items: [], total: 0 })),
  updatePartUom: vi.fn(),
  bulkAssignDefaultUom: (...a: unknown[]) => bulkAssignDefaultUom(...a),
  getUomInfo: vi.fn(async () => ({ conversions: [] })),
  upsertUomConversion: vi.fn(),
  removeUomConversion: (...a: unknown[]) => removeUomConversion(...a),
  getStockMovement: vi.fn(async () => currentMovement.value),
  submitStockMovement: (...a: unknown[]) => submitStockMovement(...a),
  cancelStockMovement: (...a: unknown[]) => cancelStockMovement(...a),
  deleteStockMovement: (...a: unknown[]) => deleteStockMovement(...a),
}))

import UomConversionView from './UomConversionView.vue'
import StockMovementDetailView from './StockMovementDetailView.vue'

const ALL_APIS = [
  deleteUom, seedAcUoms, bulkAssignDefaultUom, removeUomConversion,
  submitStockMovement, cancelStockMovement, deleteStockMovement,
]

// eslint-disable-next-line @typescript-eslint/no-explicit-any
let harness: any = null
afterEach(() => { resetModalQueue(); harness?.unmount(); harness = null })
beforeEach(() => { harness = null; vi.clearAllMocks() })

/** Bấm nút đầu tiên có text khớp — các màn này chưa gắn `data-testid` cho hành động. */
function btnByText(w: { findAll: (s: string) => { text: () => string }[] }, text: string) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const found = (w.findAll('button') as any[]).find((b) => b.text().trim() === text)
  if (!found) throw new Error(`không tìm thấy nút có nhãn «${text}»`)
  return found
}

// ─────────────────────────────────────────────────────────────────────────────
describe('TC-UX065-2 — UomConversionView: 4 call-site qua hộp thoại SSoT', () => {
  async function mountUom() {
    harness = mountWithConfirm(UomConversionView, {
      global: { stubs: { PageHeader: { template: '<div><slot /><slot name="actions" /></div>' } } },
    })
    await flushPromises()
    return harness.wrapper
  }

  const CASES = [
    { label: 'Tạo đơn vị chuẩn', api: seedAcUoms, args: [] as unknown[], danger: false },
    { label: 'Xoá', api: deleteUom, args: ['Cái'], danger: true },
  ] as const

  for (const { label, api, args, danger } of CASES) {
    it(`[${label}] hộp thoại hiện tiếng Việt, CHƯA gọi API`, async () => {
      const w = await mountUom()
      await btnByText(w, label).trigger('click')
      await flushPromises()

      const req = currentModal()
      expect(req, 'không có hộp thoại ⇒ vẫn dùng confirm() trần').toBeTruthy()
      expect(req!.title.length).toBeGreaterThan(0)
      expect(`${req!.title} ${req!.body}`).not.toMatch(/\b(Confirm|Cancel|Delete|OK|UOM)\b/)
      expect(api).not.toHaveBeenCalled()
    })

    it(`[${label}] «Huỷ» ⇒ 0 lời gọi API`, async () => {
      const w = await mountUom()
      await btnByText(w, label).trigger('click')
      await flushPromises()
      await harness.answerConfirm(false)
      for (const spy of ALL_APIS) expect(spy).not.toHaveBeenCalled()
    })

    it(`[${label}] «Xác nhận» ⇒ ĐÚNG 1 lời gọi, payload cũ`, async () => {
      const w = await mountUom()
      await btnByText(w, label).trigger('click')
      await flushPromises()
      await harness.answerConfirm(true)
      expect(api).toHaveBeenCalledTimes(1)
      if (args.length) expect(api).toHaveBeenCalledWith(...args)
    })

    it(`[${label}] tone ${danger ? "= 'error'" : "≠ 'error'"} (TC-UX065-8)`, async () => {
      const w = await mountUom()
      await btnByText(w, label).trigger('click')
      await flushPromises()
      const tone = currentModal()!.tone
      if (danger) expect(tone).toBe('error')
      else expect(tone).not.toBe('error')
    })
  }
})

// ─────────────────────────────────────────────────────────────────────────────
describe('TC-UX065-3 — StockMovementDetailView: 3 call-site qua hộp thoại SSoT', () => {
  function makeMovement(over: Record<string, unknown> = {}) {
    return {
      name: 'MOV-2026-0001', movement_type: 'Receipt', movement_date: '2026-07-01',
      docstatus: 0, status: 'Draft', items: [], warehouse: 'KHO-1', warehouse_name: 'Kho chính',
      ...over,
    }
  }

  async function mountMovement(over: Record<string, unknown> = {}) {
    currentMovement.value = makeMovement(over)
    harness = mountWithConfirm(StockMovementDetailView, {
      props: { name: 'MOV-2026-0001' },
      global: { stubs: { PageHeader: { template: '<div><slot /><slot name="actions" /></div>' }, StatusBadge: true } },
    })
    await flushPromises()
    return harness.wrapper
  }

  const CASES = [
    { label: 'Xoá', api: deleteStockMovement, over: { docstatus: 0 }, danger: true },
    { label: 'Huỷ phiếu', api: cancelStockMovement, over: { docstatus: 1 }, danger: true },
  ] as const

  it('[Duyệt] hộp thoại hiện · «Huỷ» ⇒ 0 API · «Xác nhận» ⇒ 1 API đúng tên phiếu', async () => {
    let w = await mountMovement({ docstatus: 0 })
    // Nút duyệt chứa cả nhãn động ⇒ tìm theo tiền tố.
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const submitBtn = (w.findAll('button') as any[]).find((b) => b.text().includes('Duyệt'))
    expect(submitBtn, 'không tìm thấy nút Duyệt').toBeTruthy()
    await submitBtn.trigger('click')
    await flushPromises()
    expect(currentModal()).toBeTruthy()
    expect(submitStockMovement).not.toHaveBeenCalled()
    await harness.answerConfirm(false)
    expect(submitStockMovement).not.toHaveBeenCalled()

    harness.unmount(); resetModalQueue()
    w = await mountMovement({ docstatus: 0 })
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    await (w.findAll('button') as any[]).find((b) => b.text().includes('Duyệt'))!.trigger('click')
    await flushPromises()
    await harness.answerConfirm(true)
    expect(submitStockMovement).toHaveBeenCalledTimes(1)
    expect(submitStockMovement).toHaveBeenCalledWith('MOV-2026-0001')
  })

  for (const { label, api, over, danger } of CASES) {
    it(`[${label}] hộp thoại hiện tiếng Việt, tone ${danger ? "'error'" : 'thường'}, CHƯA gọi API`, async () => {
      const w = await mountMovement(over)
      await btnByText(w, label).trigger('click')
      await flushPromises()

      const req = currentModal()
      expect(req).toBeTruthy()
      expect(`${req!.title} ${req!.body}`).not.toMatch(/\b(Confirm|Cancel|Delete|Submit|OK)\b/)
      if (danger) expect(req!.tone).toBe('error')
      expect(api).not.toHaveBeenCalled()
    })

    it(`[${label}] «Huỷ» ⇒ 0 lời gọi API`, async () => {
      const w = await mountMovement(over)
      await btnByText(w, label).trigger('click')
      await flushPromises()
      await harness.answerConfirm(false)
      for (const spy of ALL_APIS) expect(spy).not.toHaveBeenCalled()
    })

    it(`[${label}] «Xác nhận» ⇒ ĐÚNG 1 lời gọi với tên phiếu cũ`, async () => {
      const w = await mountMovement(over)
      await btnByText(w, label).trigger('click')
      await flushPromises()
      await harness.answerConfirm(true)
      expect(api).toHaveBeenCalledTimes(1)
      expect(api).toHaveBeenCalledWith('MOV-2026-0001')
    })
  }
})
