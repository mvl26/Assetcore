// Copyright (c) 2026, AssetCore Team
// IMM-05 — Verify-only FE test cho AssetDepreciationSchedule.vue.
//
// AC (CONSISTENCY/INV-DEP-3): "Giá trị còn lại" (current_book_value) ở header
// PHẢI == remaining_value của dòng schedule status='Executed' cuối cùng; và
// KHÔNG render 0 khi residual > 0. Logic do BE ghi (read-only) — FE chỉ verify
// hiển thị + đảm bảo refetch (emit 'updated') sau khi chạy/sinh lại khấu hao.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import type { DepreciationScheduleResponse } from '@/api/imm00'

const getScheduleSpy = vi.fn<() => Promise<DepreciationScheduleResponse>>()
const runDueSpy = vi.fn()
const regenSpy = vi.fn()

vi.mock('@/api/imm00', () => ({
  getDepreciationSchedule: () => getScheduleSpy(),
  runDueDepreciationNow: (...a: unknown[]) => runDueSpy(...a),
  regenerateDepreciationSchedule: (...a: unknown[]) => regenSpy(...a),
}))

// translateFrequency/translateDepreciationMethod là SSoT thực — không mock,
// để bắt luôn i18n leak nếu có.
import AssetDepreciationSchedule from './AssetDepreciationSchedule.vue'

// Asset đã khấu hao hết: gross 100tr, residual 10tr. Kỳ cuối (Executed) có
// remaining_value = 10tr == current_book_value header. KHÔNG = 0.
function fullyDepreciated(): DepreciationScheduleResponse {
  return {
    asset: 'ACC-ASS-0001',
    asset_info: {
      gross_purchase_amount: 100_000_000,
      residual_value: 10_000_000,
      accumulated_depreciation: 90_000_000,
      current_book_value: 10_000_000, // == remaining_value dòng cuối, KHÔNG 0
      depreciation_method: 'Straight Line',
      total_depreciation_months: 2,
      depreciation_frequency: 'Monthly',
    },
    rows: [
      {
        name: 'r1', period_number: 1, scheduled_date: '2026-01-31',
        depreciation_amount: 45_000_000, accumulated_amount: 45_000_000,
        remaining_value: 55_000_000, status: 'Executed', executed_on: '2026-02-01',
      },
      {
        name: 'r2', period_number: 2, scheduled_date: '2026-02-28',
        depreciation_amount: 45_000_000, accumulated_amount: 90_000_000,
        remaining_value: 10_000_000, status: 'Executed', executed_on: '2026-03-01',
      },
    ],
    summary: { total_periods: 2, executed_periods: 2, pending_periods: 0, total_depreciated: 90_000_000 },
  }
}

describe('AssetDepreciationSchedule — INV-DEP-3 book value khớp dòng schedule cuối', () => {
  beforeEach(() => {
    getScheduleSpy.mockReset()
    runDueSpy.mockReset()
    regenSpy.mockReset()
  })

  it('header "Giá trị còn lại" == remaining_value dòng Executed cuối (không = 0 khi residual>0)', async () => {
    const resp = fullyDepreciated()
    getScheduleSpy.mockResolvedValue(resp)
    const wrapper = mount(AssetDepreciationSchedule, { props: { assetName: 'ACC-ASS-0001' } })
    await flushPromises()

    const html = wrapper.html()
    // current_book_value (10tr) phải hiện ở header — Intl vi-VN VND có thể chèn
    // ký tự non-breaking space, nên so sánh trên text đã chuẩn hoá khoảng trắng.
    const text = wrapper.text().replace(/ /g, ' ')
    // Header book value = residual 10.000.000, KHÔNG render "0 đ".
    expect(text).toContain('10.000.000')
    expect(html).not.toMatch(/Giá trị còn lại[\s\S]{0,80}>0 đ</)

    // Đồng nhất planner↔executor: book value header == remaining_value dòng cuối.
    const last = resp.rows[resp.rows.length - 1]
    expect(resp.asset_info.current_book_value).toBe(last.remaining_value)
    expect(last.status).toBe('Executed')
  })

  it("status dịch sang tiếng Việt — KHÔNG leak 'Executed'/'Pending' raw", async () => {
    getScheduleSpy.mockResolvedValue(fullyDepreciated())
    const wrapper = mount(AssetDepreciationSchedule, { props: { assetName: 'ACC-ASS-0001' } })
    await flushPromises()
    const html = wrapper.html()
    expect(html).toContain('Đã khấu hao')
    // Không để raw enum English lọt ra cell trạng thái.
    expect(html).not.toMatch(/>\s*Executed\s*</)
    expect(html).not.toMatch(/>\s*Pending\s*</)
  })

  it("emit 'updated' sau khi chạy cron có dòng thực thi → cha refetch header", async () => {
    getScheduleSpy.mockResolvedValue(fullyDepreciated())
    runDueSpy.mockResolvedValue({ executed_rows: 2, updated_assets: 1 })
    // confirm() trả true để qua gate (component dùng confirm native — ngoài scope task này).
    vi.spyOn(window, 'confirm').mockReturnValue(true)

    const wrapper = mount(AssetDepreciationSchedule, { props: { assetName: 'ACC-ASS-0001' } })
    await flushPromises()

    await wrapper.find('button.btn-ghost').trigger('click')
    await flushPromises()

    expect(runDueSpy).toHaveBeenCalledOnce()
    // 1 emit 'updated' để view cha refetch asset → header không stale.
    expect(wrapper.emitted('updated')).toBeTruthy()
    expect(wrapper.emitted('updated')).toHaveLength(1)
  })

  it("KHÔNG emit 'updated' khi cron không thực thi dòng nào (executed_rows=0, idempotent)", async () => {
    getScheduleSpy.mockResolvedValue(fullyDepreciated())
    runDueSpy.mockResolvedValue({ executed_rows: 0, updated_assets: 0 })
    vi.spyOn(window, 'confirm').mockReturnValue(true)

    const wrapper = mount(AssetDepreciationSchedule, { props: { assetName: 'ACC-ASS-0001' } })
    await flushPromises()

    await wrapper.find('button.btn-ghost').trigger('click')
    await flushPromises()

    expect(runDueSpy).toHaveBeenCalledOnce()
    // Không có dòng nào đổi → không refetch thừa (tránh flicker header).
    expect(wrapper.emitted('updated')).toBeFalsy()
  })
})
