// TDD-7 (FE regression guard) — Core Doc §9.4.5 (R7) / BUG-15-03.
//
// Predicate "dưới định mức" honour min_stock_override per-bin là BE-only
// (effective_min = COALESCE(NULLIF(s.min_stock_override,0), p.min_stock_level, 0)).
// FE KHÔNG tự tính/đếm — chỉ render count + list BE trả. Test này PIN lại bất biến:
//   KPI card 'Cảnh báo tồn thấp' (low_stock_count) === độ dài danh sách drill
// khi dataset có min_stock_override → count/list KHÔNG bao giờ lệch ở tầng FE.
//
// Đồng thời chặn raw leak: bin có override hiển thị min_stock_level = effective_min
// (vd 80), KHÔNG phải part-min thô (50).
import { describe, it, expect, vi, beforeEach } from 'vitest'
// CR-AFFORD: view giờ gọi useCapabilities() ở setup (gate nút Tạo) → mock để mount không cần Pinia.
vi.mock('@/composables/useCapabilities', () => ({ useCapabilities: () => ({ can: () => true }) }))
import { mount, flushPromises } from '@vue/test-utils'

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
}))

// Dataset acceptance: 1 part min=50, 2 bin —
//   binA qty=40 (low theo part-min) · binB qty=60 override=80 (low CHỈ theo override)
// → BE canonical: low_stock_count = 2, low_stock_items có 2 bin, binB.min=80.
const OVERVIEW = {
  total_parts: 1,
  total_warehouses: 2,
  total_value: 1000,
  low_stock_count: 2, // BE-computed (canonical effective_min) — FE chỉ render
  low_stock_items: [
    {
      bin: 'BIN-A', spare_part: 'SP-1', part_name: 'Phụ tùng A',
      warehouse: 'WH-A', warehouse_name: 'Kho A',
      min_stock_level: 50, total_qty: 40, // low theo part-min
    },
    {
      bin: 'BIN-B', spare_part: 'SP-1', part_name: 'Phụ tùng A',
      warehouse: 'WH-B', warehouse_name: 'Kho B',
      min_stock_level: 80, total_qty: 60, // effective_min = override 80 (KHÔNG phải 50)
    },
  ],
  movement_30d: {},
}

const overviewSpy = vi.fn().mockResolvedValue(OVERVIEW)
vi.mock('@/api/inventory', () => ({
  getInventoryOverview: () => overviewSpy(),
}))

import InventoryDashboardView from './InventoryDashboardView.vue'

const stubs = { PageHeader: true, RouterLink: true }

describe('InventoryDashboardView — low-stock count/list divergence guard (§9.4.5)', () => {
  beforeEach(() => { overviewSpy.mockClear() })

  it('KPI card low_stock_count === độ dài danh sách drill khi có min_stock_override', async () => {
    const wrapper = mount(InventoryDashboardView, { global: { stubs } })
    await flushPromises()

    // Card hiển thị ĐÚNG count BE trả (FE không recompute → không thể lệch).
    expect(wrapper.text()).toContain('2')

    // Danh sách drill render đúng số bin BE trả; card count === list length.
    const rows = wrapper.findAll('[class*="bg-red-50"]')
    expect(rows.length).toBe(OVERVIEW.low_stock_count)
    expect(rows.length).toBe(OVERVIEW.low_stock_items.length)
  })

  it('bin có override hiển thị effective_min (80), KHÔNG leak part-min thô (50)', async () => {
    const wrapper = mount(InventoryDashboardView, { global: { stubs } })
    await flushPromises()
    const text = wrapper.text()
    // Override bin: tồn 60 / định mức 80 (effective_min). Part-min bin: 40 / 50.
    expect(text).toContain('60 / 80')
    expect(text).toContain('40 / 50')
    // KHÔNG được render "60 / 50" (override bị bỏ qua → leak part-min).
    expect(text).not.toContain('60 / 50')
  })

  it('không leak raw status/code tiếng Anh trong card tồn thấp', async () => {
    const wrapper = mount(InventoryDashboardView, { global: { stubs } })
    await flushPromises()
    const text = wrapper.text()
    expect(text).not.toMatch(/min_stock_override|min_stock_level|low_stock/)
    expect(text).not.toMatch(/\b(Active|Pending|Draft|Low Stock)\b/)
  })
})
