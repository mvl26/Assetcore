// Copyright (c) 2026, AssetCore Team
//
// TDD T3 — Panel "Khấu hao theo danh mục" (quản lý tập trung).
// Guard hành vi:
//   (a) mount → gọi getDepreciationByCategory, render 1 dòng / danh mục + tổng.
//   (b) click "Xem thiết bị" → emit `drill` {categoryId, category} (parent lọc TS).
//   (c) click "Áp dụng luật" → gọi bulkRegenerateScheduleByCategory(categoryId),
//       hiện kết quả, reload danh sách + emit `applied`.
//   (d) nhóm "Chưa phân loại" (category_id='') KHÔNG có nút "Áp dụng luật".
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import type {
  DepreciationByCategoryResult, BulkRegenerateResult,
} from '@/api/imm00'

const byCatSpy = vi.fn<() => Promise<DepreciationByCategoryResult>>()
const bulkSpy = vi.fn<(c: string) => Promise<BulkRegenerateResult>>()

vi.mock('@/api/imm00', () => ({
  getDepreciationByCategory: () => byCatSpy(),
  bulkRegenerateScheduleByCategory: (c: string) => bulkSpy(c),
}))

import DepreciationByCategoryPanel from './DepreciationByCategoryPanel.vue'

const RESULT: DepreciationByCategoryResult = {
  categories: [
    {
      category_id: 'CAT-0001', category: 'Máy chẩn đoán',
      asset_count: 42, configured_count: 40, fully_depreciated: 3,
      total_gross: 12_400_000_000, total_accumulated: 4_100_000_000,
      total_book_value: 8_300_000_000, pct_depreciated: 33.1,
    },
    {
      category_id: 'CAT-0002', category: 'Thiết bị mổ',
      asset_count: 18, configured_count: 18, fully_depreciated: 0,
      total_gross: 6_000_000_000, total_accumulated: 2_700_000_000,
      total_book_value: 3_300_000_000, pct_depreciated: 45.0,
    },
    {
      category_id: '', category: 'Chưa phân loại',
      asset_count: 5, configured_count: 0, fully_depreciated: 0,
      total_gross: 0, total_accumulated: 0, total_book_value: 0, pct_depreciated: 0,
    },
  ],
  totals: {
    total_assets: 65, total_gross: 18_400_000_000,
    total_accumulated: 6_800_000_000, total_book_value: 11_600_000_000,
    overall_pct: 37.0,
  },
}

function freshResult(): DepreciationByCategoryResult {
  return JSON.parse(JSON.stringify(RESULT))
}

const stubs = { RouterLink: true }

describe('DepreciationByCategoryPanel', () => {
  beforeEach(() => {
    byCatSpy.mockReset()
    bulkSpy.mockReset()
    byCatSpy.mockResolvedValue(freshResult())
  })

  it('(a) render 1 dòng / danh mục + gọi endpoint', async () => {
    const w = mount(DepreciationByCategoryPanel, { global: { stubs } })
    await flushPromises()

    expect(byCatSpy).toHaveBeenCalledTimes(1)
    const rows = w.findAll('[data-testid="depr-cat-row"]')
    expect(rows).toHaveLength(3)
    expect(w.text()).toContain('Máy chẩn đoán')
    expect(w.text()).toContain('Thiết bị mổ')
    // đếm thiết bị + độ phủ cấu hình
    expect(rows[0].text()).toContain('42')
    expect(rows[0].text()).toContain('40')
  })

  it('(b) click "Xem thiết bị" emit drill với categoryId', async () => {
    const w = mount(DepreciationByCategoryPanel, { global: { stubs } })
    await flushPromises()

    await w.findAll('[data-testid="depr-cat-drill"]')[0].trigger('click')
    const ev = w.emitted('drill')
    expect(ev).toBeTruthy()
    expect(ev![0][0]).toMatchObject({ categoryId: 'CAT-0001', category: 'Máy chẩn đoán' })
  })

  it('(c) "Áp dụng luật" gọi bulk + reload + emit applied', async () => {
    bulkSpy.mockResolvedValue({
      category: 'CAT-0001', total_assets: 42, inherited: 2, regenerated: 5,
      skipped_has_history: 35, skipped_no_rule: 0, errors: 0,
    } as BulkRegenerateResult)
    const w = mount(DepreciationByCategoryPanel, { global: { stubs } })
    await flushPromises()

    await w.findAll('[data-testid="depr-cat-apply"]')[0].trigger('click')
    await flushPromises()

    expect(bulkSpy).toHaveBeenCalledWith('CAT-0001')
    // reload sau khi áp dụng (mount=1 + reload=1)
    expect(byCatSpy).toHaveBeenCalledTimes(2)
    expect(w.emitted('applied')).toBeTruthy()
  })

  it('(d) nhóm "Chưa phân loại" KHÔNG có nút Áp dụng luật', async () => {
    const w = mount(DepreciationByCategoryPanel, { global: { stubs } })
    await flushPromises()

    const rows = w.findAll('[data-testid="depr-cat-row"]')
    // dòng thứ 3 = 'Chưa phân loại' (category_id='')
    const uncategorized = rows[2]
    expect(uncategorized.text()).toContain('Chưa phân loại')
    expect(uncategorized.find('[data-testid="depr-cat-apply"]').exists()).toBe(false)
  })
})
