// TDD — IMM-05 DepreciationView: cột "Khấu hao" render nhãn tần suất VI (không leak English).
// depreciation_frequency='Monthly' → DOM 'Hàng tháng' (KHÔNG 'Monthly').
// depreciation_frequency=null → '—' (KHÔNG English literal fallback 'Monthly').
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import type { AssetDepreciationRow, DepreciationStats } from '@/api/imm00'

const listSpy = vi.fn()
const statsSpy = vi.fn<() => Promise<DepreciationStats>>()
vi.mock('@/api/imm00', () => ({
  listAssetsDepreciation: (...a: unknown[]) => listSpy(...a),
  getDepreciationStats: () => statsSpy(),
  computeDepreciation: vi.fn(),
  computeAllDepreciation: vi.fn(),
}))

import DepreciationView from './DepreciationView.vue'

const stubs = {
  PageHeader: true, AssetDepreciationSchedule: true, RouterLink: true,
}

function baseRow(overrides: Partial<AssetDepreciationRow>): AssetDepreciationRow {
  return {
    name: 'ACC-ASS-0001',
    asset_name: 'Máy X',
    total_depreciation_months: 12,
    depreciation_frequency: 'Monthly',
    configured: true,
    pct_depreciated: 0,
    executed_periods: 0,
    total_periods: 12,
    ...overrides,
  } as AssetDepreciationRow
}

const emptyStats: DepreciationStats = {
  total_assets: 1, configured_count: 1, unconfigured_count: 0, fully_depreciated: 0,
  total_gross: 0, total_accumulated: 0, total_book_value: 0, overall_pct: 0,
  by_method: [], by_category: [],
}

describe('DepreciationView — nhãn tần suất khấu hao (i18n leak guard)', () => {
  beforeEach(() => {
    listSpy.mockReset()
    statsSpy.mockReset()
    statsSpy.mockResolvedValue(emptyStats)
  })

  it("depreciation_frequency='Monthly' → DOM 'Hàng tháng', KHÔNG 'Monthly'", async () => {
    listSpy.mockResolvedValue({ items: [baseRow({ depreciation_frequency: 'Monthly' })], pagination: { total: 1 } })
    const wrapper = mount(DepreciationView, { global: { stubs } })
    await flushPromises()
    const html = wrapper.html()
    expect(html).toContain('Hàng tháng')
    expect(html).not.toMatch(/>[^<]*\bMonthly\b[^<]*</)
  })

  it("depreciation_frequency=null → '—' (KHÔNG English literal 'Monthly')", async () => {
    listSpy.mockResolvedValue({
      items: [baseRow({ depreciation_frequency: null as unknown as undefined })],
      pagination: { total: 1 },
    })
    const wrapper = mount(DepreciationView, { global: { stubs } })
    await flushPromises()
    const html = wrapper.html()
    // total_depreciation_months=12 nên cell render "12 tháng · —", không fallback 'Monthly'.
    expect(html).toContain('12 tháng · —')
    expect(html).not.toMatch(/>[^<]*\bMonthly\b[^<]*</)
  })
})

// ── Drill "Hết khấu hao" — count clickable → depreciation_filter (KHÔNG status_filter) ──
describe('DepreciationView — drill "Hết khấu hao" (fully_depreciated SoT)', () => {
  beforeEach(() => {
    listSpy.mockReset()
    statsSpy.mockReset()
    listSpy.mockResolvedValue({ items: [], pagination: { total: 0 } })
  })

  it("click ô 'N hết KH' → gọi listAssetsDepreciation với depreciation_filter='fully_depreciated', KHÔNG set status_filter", async () => {
    statsSpy.mockResolvedValue({ ...emptyStats, total_assets: 5, configured_count: 5, fully_depreciated: 3 })
    listSpy.mockResolvedValue({
      items: [baseRow({ name: 'ACC-ASS-FULL', asset_name: 'Máy hết KH' })],
      pagination: { total: 3 },
    })
    const wrapper = mount(DepreciationView, { global: { stubs } })
    await flushPromises()
    listSpy.mockClear()

    // Nhãn 'N hết KH' phải là phần tử bấm được (button), KHÔNG còn text câm.
    const btn = wrapper.find('button[title*="hết khấu hao"]')
    expect(btn.exists()).toBe(true)
    expect(btn.text()).toContain('3 hết KH')

    await btn.trigger('click')
    await flushPromises()

    expect(listSpy).toHaveBeenCalled()
    const params = listSpy.mock.calls.at(-1)![0] as Record<string, unknown>
    expect(params.depreciation_filter).toBe('fully_depreciated')
    // KHÔNG leak token vào status_filter / lifecycle_status.
    expect(params.status_filter).toBe('')
  })

  it("dropdown có option 'Hết khấu hao' route sang depreciation_filter — KHÔNG status_filter", async () => {
    statsSpy.mockResolvedValue({ ...emptyStats, fully_depreciated: 2 })
    const wrapper = mount(DepreciationView, { global: { stubs } })
    await flushPromises()

    const select = wrapper.find('#depr-status-filter')
    expect(select.exists()).toBe(true)
    const opt = select.findAll('option').find(o => o.text() === 'Hết khấu hao')
    expect(opt).toBeTruthy()
    expect(opt!.attributes('value')).toBe('fully_depreciated')

    listSpy.mockClear()
    await select.setValue('fully_depreciated')
    await flushPromises()
    const params = listSpy.mock.calls.at(-1)![0] as Record<string, unknown>
    expect(params.depreciation_filter).toBe('fully_depreciated')
    expect(params.status_filter).toBe('')
  })

  it('drill ra 0 dòng → empty-state VI, KHÔNG leak raw token "fully_depreciated"', async () => {
    statsSpy.mockResolvedValue({ ...emptyStats, fully_depreciated: 0 })
    listSpy.mockResolvedValue({ items: [], pagination: { total: 0 } })
    const wrapper = mount(DepreciationView, { global: { stubs } })
    await flushPromises()

    await wrapper.find('button[title*="hết khấu hao"]').trigger('click')
    await flushPromises()

    const html = wrapper.html()
    expect(html).toContain('Không có thiết bị nào hết khấu hao')
    // raw token KHÔNG bao giờ hiện lên UI.
    expect(html).not.toMatch(/>[^<]*fully_depreciated[^<]*</)
  })

  it('render drill = verbatim items BE; nhãn chip "Hết khấu hao" VI', async () => {
    statsSpy.mockResolvedValue({ ...emptyStats, fully_depreciated: 1 })
    listSpy.mockResolvedValue({
      items: [baseRow({ name: 'ACC-ASS-DRILL', asset_name: 'Thiết bị đã hết KH' })],
      pagination: { total: 1 },
    })
    const wrapper = mount(DepreciationView, { global: { stubs } })
    await flushPromises()
    await wrapper.find('button[title*="hết khấu hao"]').trigger('click')
    await flushPromises()

    const html = wrapper.html()
    expect(html).toContain('Thiết bị đã hết KH')   // verbatim item
    expect(html).toContain('Hết khấu hao')          // chip nhãn VI
  })
})
