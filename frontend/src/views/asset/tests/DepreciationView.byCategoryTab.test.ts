// Copyright (c) 2026, AssetCore Team
//
// TDD T4 — DepreciationView tích hợp panel "Theo danh mục" (quản lý tập trung).
// Guard:
//   (a) mặc định viewMode='asset' — bảng thiết bị hiện, panel danh mục ẩn.
//   (b) bấm "Theo danh mục" → hiện DepreciationByCategoryPanel, ẩn bảng thiết bị.
//   (c) panel emit `drill` {categoryId} → về mode thiết bị + lọc listAssetsDepreciation
//       theo category_filter=categoryId.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import type { DepreciationStats } from '@/api/imm00'

const listSpy = vi.fn()
const statsSpy = vi.fn<() => Promise<DepreciationStats>>()
vi.mock('@/api/imm00', () => ({
  listAssetsDepreciation: (...a: unknown[]) => listSpy(...a),
  getDepreciationStats: () => statsSpy(),
  computeDepreciation: vi.fn(),
  computeAllDepreciation: vi.fn(),
}))

import DepreciationView from '@/views/asset/DepreciationView.vue'

// Panel stub: cho phép emit drill từ test (không mount panel thật → không cần
// getDepreciationByCategory trong mock).
const PanelStub = {
  name: 'DepreciationByCategoryPanel',
  template: '<div data-testid="cat-panel-stub"></div>',
  emits: ['drill', 'applied'],
}

const stubs = {
  PageHeader: { template: '<div><slot /><slot name="actions" /></div>' },
  AssetDepreciationSchedule: true,
  RouterLink: true,
  DepreciationByCategoryPanel: PanelStub,
}

const emptyStats: DepreciationStats = {
  total_assets: 2, configured_count: 2, unconfigured_count: 0, fully_depreciated: 0,
  total_gross: 0, total_accumulated: 0, total_book_value: 0, overall_pct: 0,
  by_method: [], by_category: [],
}

describe('DepreciationView — tab "Theo danh mục"', () => {
  beforeEach(() => {
    listSpy.mockReset()
    statsSpy.mockReset()
    statsSpy.mockResolvedValue(emptyStats)
    listSpy.mockResolvedValue({ items: [], pagination: { total: 0 } })
  })

  it('(a) mặc định hiện bảng thiết bị, ẩn panel danh mục', async () => {
    const w = mount(DepreciationView, { global: { stubs } })
    await flushPromises()
    expect(w.find('[data-testid="depr-viewmode-category"]').exists()).toBe(true)
    expect(w.find('[data-testid="cat-panel-stub"]').exists()).toBe(false)
  })

  it('(b) bấm "Theo danh mục" → hiện panel, ẩn bảng thiết bị', async () => {
    const w = mount(DepreciationView, { global: { stubs } })
    await flushPromises()

    await w.find('[data-testid="depr-viewmode-category"]').trigger('click')
    await flushPromises()

    expect(w.find('[data-testid="cat-panel-stub"]').exists()).toBe(true)
    // bảng danh sách thiết bị (header "Danh sách thiết bị") không còn hiển thị
    expect(w.text()).not.toContain('Danh sách thiết bị')
  })

  it('(c) panel emit drill → về mode thiết bị + lọc theo category_filter', async () => {
    const w = mount(DepreciationView, { global: { stubs } })
    await flushPromises()

    await w.find('[data-testid="depr-viewmode-category"]').trigger('click')
    await flushPromises()
    listSpy.mockClear()

    w.findComponent(PanelStub).vm.$emit('drill', { categoryId: 'CAT-0007', category: 'Máy X' })
    await flushPromises()

    // quay về mode thiết bị (panel ẩn, bảng hiện lại)
    expect(w.find('[data-testid="cat-panel-stub"]').exists()).toBe(false)
    expect(w.text()).toContain('Danh sách thiết bị')
    // list gọi với category_filter = categoryId
    expect(listSpy).toHaveBeenCalled()
    const params = listSpy.mock.calls.at(-1)![0] as Record<string, unknown>
    expect(params.category_filter).toBe('CAT-0007')
  })
})
