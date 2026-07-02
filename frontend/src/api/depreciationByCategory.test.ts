// Copyright (c) 2026, AssetCore Team
//
// TDD T2 — FE api client cho get_depreciation_by_category (quản lý khấu hao theo
// Danh mục). Wrapper thin-wrap frappeGet (đã unwrap Frappe envelope → trả `data`).
// Guard: (a) gọi ĐÚNG endpoint path; (b) resolve trả nguyên {categories, totals}.
import { describe, it, expect, vi, beforeEach } from 'vitest'

const frappeGet = vi.fn()
vi.mock('./helpers', () => ({
  frappeGet: (...args: unknown[]) => frappeGet(...args),
  frappePost: vi.fn(),
}))

import { getDepreciationByCategory } from './imm00'
import type { DepreciationByCategoryResult } from './imm00'

describe('getDepreciationByCategory() FE api wrapper', () => {
  beforeEach(() => frappeGet.mockReset())

  it('gọi đúng endpoint get_depreciation_by_category', async () => {
    frappeGet.mockResolvedValue({ categories: [], totals: {} })
    await getDepreciationByCategory()
    expect(frappeGet).toHaveBeenCalledWith(
      '/api/method/assetcore.api.imm00.get_depreciation_by_category',
    )
  })

  it('resolve trả nguyên payload {categories, totals} (frappeGet đã unwrap data)', async () => {
    const payload: DepreciationByCategoryResult = {
      categories: [{
        category_id: 'CAT-0001', category: 'Máy chẩn đoán',
        asset_count: 42, configured_count: 40, fully_depreciated: 3,
        total_gross: 12_400_000_000, total_accumulated: 4_100_000_000,
        total_book_value: 8_300_000_000, pct_depreciated: 33.1,
      }],
      totals: {
        total_assets: 42, total_gross: 12_400_000_000,
        total_accumulated: 4_100_000_000, total_book_value: 8_300_000_000,
        overall_pct: 33.1,
      },
    }
    frappeGet.mockResolvedValue(payload)

    const res = await getDepreciationByCategory()

    expect(res.categories).toHaveLength(1)
    expect(res.categories[0].category_id).toBe('CAT-0001')
    expect(res.categories[0].asset_count).toBe(42)
    expect(res.totals.total_gross).toBe(12_400_000_000)
  })
})
