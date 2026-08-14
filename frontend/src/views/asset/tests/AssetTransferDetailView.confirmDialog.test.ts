// TC-UX065-4 / -7 / -8 / -10 — lô 1 nhánh tài sản: `AssetTransferDetailView`
// (3 call-site) và `components/asset/AssetDepreciationSchedule.vue` (2 call-site)
// di trú `confirm()` trần → `useModal()`.
//
// Cả hai cùng tiêu thụ `@/api/imm00` nên dùng CHUNG một lần giả lập module.
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mountWithConfirm, resetModalQueue, currentModal } from '@/test/confirmHarness'

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { id: 'AT-2026-0001' }, query: {}, path: '/asset-transfers/AT-2026-0001' }),
  useRouter: () => ({ push: vi.fn() }),
}))
vi.mock('@/constants/labels', () => ({ transferTypeLabel: (v: string) => (v === 'Internal' ? 'Nội bộ' : v) }))

let transferPayload: Record<string, unknown> = {}
const getTransferFull = vi.fn(async () => transferPayload)
const approveTransfer = vi.fn().mockResolvedValue({ name: 'AT-2026-0001', status: 'Approved' })
const updateTransfer = vi.fn().mockResolvedValue({ name: 'AT-2026-0001' })
const regenerateDepreciationSchedule = vi.fn().mockResolvedValue({ periods: 60, skipped: 0 })
const runDueDepreciationNow = vi.fn().mockResolvedValue({ executed_rows: 2, updated_assets: 1 })

vi.mock('@/api/imm00', () => ({
  getTransferFull: (...a: unknown[]) => getTransferFull(...a),
  updateTransfer: (...a: unknown[]) => updateTransfer(...a),
  approveTransfer: (...a: unknown[]) => approveTransfer(...a),
  getDepreciationSchedule: vi.fn(async () => ({
    asset: 'ACC-ASS-0001',
    asset_info: {
      gross_purchase_amount: 100_000_000, residual_value: 0, accumulated_depreciation: 0,
      current_book_value: 100_000_000, depreciation_method: 'Straight Line',
      total_depreciation_months: 60, depreciation_frequency: 'Monthly',
    },
    rows: [{
      name: 'r1', period_number: 1, scheduled_date: '2026-01-31',
      depreciation_amount: 1_000_000, accumulated_amount: 1_000_000,
      remaining_value: 99_000_000, status: 'Pending',
    }],
    summary: { total_periods: 60, executed_periods: 0, pending_periods: 60, total_depreciated: 0 },
  })),
  regenerateDepreciationSchedule: (...a: unknown[]) => regenerateDepreciationSchedule(...a),
  runDueDepreciationNow: (...a: unknown[]) => runDueDepreciationNow(...a),
}))
const frappePost = vi.fn().mockResolvedValue({})
vi.mock('@/api/helpers', () => ({ frappePost: (...a: unknown[]) => frappePost(...a) }))

import AssetTransferDetailView from '@/views/asset/AssetTransferDetailView.vue'
import AssetDepreciationSchedule from '@/components/asset/AssetDepreciationSchedule.vue'

const ALL_APIS = [approveTransfer, updateTransfer, frappePost, regenerateDepreciationSchedule, runDueDepreciationNow]

// eslint-disable-next-line @typescript-eslint/no-explicit-any
let harness: any = null
beforeEach(() => { harness = null; vi.clearAllMocks() })
afterEach(() => { resetModalQueue(); harness?.unmount(); harness = null })

function baseTransfer(over: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    name: 'AT-2026-0001', asset: 'ACC-ASS-0001', asset_name: 'Máy thở Bennett 840',
    transfer_type: 'Internal', transfer_date: '2026-07-01', status: 'Received',
    reason: 'Điều chuyển phục vụ khoa Hồi sức', notes: '',
    approved_by: '', rejected_by: '', received_by: '',
    from_location_name: 'Khoa Cấp cứu', to_location_name: 'Khoa Hồi sức',
    ...over,
  }
}

// ─────────────────────────────────────────────────────────────────────────────
describe('TC-UX065-4 — AssetTransferDetailView: 3 call-site qua hộp thoại SSoT', () => {
  async function mountTransfer(over: Record<string, unknown>) {
    transferPayload = baseTransfer(over)
    harness = mountWithConfirm(AssetTransferDetailView, {
      global: { stubs: { SmartSelect: true, ApproverSelect: true, DateInput: true } },
    })
    await flushPromises()
    return harness.wrapper
  }

  const CASES = [
    {
      cta: 'cta-approve', over: { status: 'Pending Approval', can_approve: 1 },
      assertCall: () => {
        expect(approveTransfer).toHaveBeenCalledTimes(1)
        expect(approveTransfer).toHaveBeenCalledWith('AT-2026-0001')
      },
      danger: false,
    },
    {
      cta: 'cta-receive', over: { status: 'Approved', can_receive: 1 },
      assertCall: () => {
        expect(frappePost).toHaveBeenCalledTimes(1)
        expect(frappePost).toHaveBeenCalledWith(
          '/api/method/assetcore.api.imm00.receive_transfer',
          expect.objectContaining({ name: 'AT-2026-0001' }),
        )
      },
      danger: false,
    },
    {
      cta: 'cta-cancel', over: { status: 'Pending Approval', can_cancel: 1 },
      assertCall: () => {
        expect(frappePost).toHaveBeenCalledTimes(1)
        expect(frappePost).toHaveBeenCalledWith(
          '/api/method/assetcore.api.imm00.delete_transfer',
          expect.objectContaining({ name: 'AT-2026-0001' }),
        )
      },
      danger: true,
    },
  ] as const

  for (const { cta, over, assertCall, danger } of CASES) {
    it(`[${cta}] hộp thoại hiện tiếng Việt, CHƯA gọi API`, async () => {
      const w = await mountTransfer(over)
      await w.find(`[data-testid="${cta}"]`).trigger('click')
      await flushPromises()

      const req = currentModal()
      expect(req, 'không có hộp thoại ⇒ vẫn dùng confirm() trần').toBeTruthy()
      expect(req!.title.length).toBeGreaterThan(0)
      expect(`${req!.title} ${req!.body}`).not.toMatch(/\b(Confirm|Cancel|Approve|Delete|OK)\b/)
      for (const spy of ALL_APIS) expect(spy).not.toHaveBeenCalled()
    })

    it(`[${cta}] «Huỷ» ⇒ 0 lời gọi API`, async () => {
      const w = await mountTransfer(over)
      await w.find(`[data-testid="${cta}"]`).trigger('click')
      await flushPromises()
      await harness.answerConfirm(false)
      for (const spy of ALL_APIS) expect(spy).not.toHaveBeenCalled()
    })

    it(`[${cta}] «Xác nhận» ⇒ ĐÚNG 1 lời gọi đúng endpoint + payload cũ`, async () => {
      const w = await mountTransfer(over)
      await w.find(`[data-testid="${cta}"]`).trigger('click')
      await flushPromises()
      await harness.answerConfirm(true)
      assertCall()
    })

    it(`[${cta}] tone ${danger ? "= 'error' (TC-UX065-8)" : "≠ 'error'"}`, async () => {
      const w = await mountTransfer(over)
      await w.find(`[data-testid="${cta}"]`).trigger('click')
      await flushPromises()
      const tone = currentModal()!.tone
      if (danger) expect(tone).toBe('error')
      else expect(tone).not.toBe('error')
    })
  }
})

// ─────────────────────────────────────────────────────────────────────────────
describe('TC-UX065-7 — AssetDepreciationSchedule: 2 call-site qua hộp thoại SSoT', () => {
  async function mountSchedule() {
    harness = mountWithConfirm(AssetDepreciationSchedule, { props: { assetName: 'ACC-ASS-0001' } })
    await flushPromises()
    return harness.wrapper
  }

  // Fixture CÓ dòng lịch ⇒ nhánh `v-else` render: `btn-ghost` = chạy cron,
  // `btn-secondary` = sinh lại. (`btn-primary` chỉ tồn tại ở trạng thái RỖNG.)
  const CASES = [
    { sel: 'button.btn-secondary', api: regenerateDepreciationSchedule, danger: true, name: 'Sinh lại lịch' },
    { sel: 'button.btn-ghost', api: runDueDepreciationNow, danger: false, name: 'Chạy kỳ đến hạn' },
  ] as const

  for (const { sel, api, danger, name } of CASES) {
    it(`[${name}] hộp thoại hiện tiếng Việt, tone ${danger ? "'error'" : 'thường'}, CHƯA gọi API`, async () => {
      const w = await mountSchedule()
      const btn = w.find(sel)
      expect(btn.exists(), `không tìm thấy ${sel}`).toBe(true)
      await btn.trigger('click')
      await flushPromises()

      const req = currentModal()
      expect(req).toBeTruthy()
      expect(`${req!.title} ${req!.body}`).not.toMatch(/\b(Confirm|Cancel|OK|System Manager)\b/)
      if (danger) expect(req!.tone).toBe('error')
      else expect(req!.tone).not.toBe('error')
      expect(api).not.toHaveBeenCalled()
    })

    it(`[${name}] «Huỷ» ⇒ 0 lời gọi API`, async () => {
      const w = await mountSchedule()
      await w.find(sel).trigger('click')
      await flushPromises()
      await harness.answerConfirm(false)
      for (const spy of ALL_APIS) expect(spy).not.toHaveBeenCalled()
    })

    it(`[${name}] «Xác nhận» ⇒ ĐÚNG 1 lời gọi`, async () => {
      const w = await mountSchedule()
      await w.find(sel).trigger('click')
      await flushPromises()
      await harness.answerConfirm(true)
      expect(api).toHaveBeenCalledTimes(1)
    })
  }

  it('[Sinh lại lịch] giữ nguyên signature cũ regenerate(assetName, 1)', async () => {
    const w = await mountSchedule()
    await w.find('button.btn-secondary').trigger('click')
    await flushPromises()
    await harness.answerConfirm(true)
    expect(regenerateDepreciationSchedule).toHaveBeenCalledWith('ACC-ASS-0001', 1)
  })
})
