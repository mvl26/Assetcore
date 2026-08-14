// TC-FE-15-LOW-01 (vitest) — Core Doc §III-bis.6 (R7 v2 / BR-15-17·VR-15-17).
//
// Bối cảnh BE: predicate "dưới định mức" hợp nhất về tồn KHẢ DỤNG
//   available = (qty_on_hand − reserved_qty) < effective_min
// → bin reserved-full (on_hand=100, reserved=100, available=0, min=20) flip sang LOW.
//
// FE ZERO shape-change: tile 'Cảnh báo tồn thấp' (= chỉ tiêu "Dưới định mức") VẪN bind
// VERBATIM con số `low_stock_count` BE gửi. FE KHÔNG tự tính low từ qty_on_hand —
// reserved-full chỉ "thấy được" vì BE đã đếm, KHÔNG vì FE recompute.
//
// Test này PIN 3 bất biến:
//   1. Tile render verbatim BE value ∀ {0, 1, 7} (parametrized) — break binding → FAIL.
//   2. Reserved-full bin (available=0, on_hand≥min) BE đếm → FE hiển thị đúng count + drill.
//   3. No-leak EN regex: 'Reserved / Available / On Hand / Low Stock' KHÔNG lọt UI;
//      raw field key (reserved_qty / available_qty / low_stock_count) KHÔNG lọt UI.
import { describe, it, expect, vi, beforeEach } from 'vitest'
// CR-AFFORD: view giờ gọi useCapabilities() ở setup (gate nút Tạo) → mock để mount không cần Pinia.
vi.mock('@/composables/useCapabilities', () => ({ useCapabilities: () => ({ can: () => true }) }))
import { mount, flushPromises } from '@vue/test-utils'

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
}))

const overviewSpy = vi.fn()
vi.mock('@/api/inventory', () => ({
  getInventoryOverview: () => overviewSpy(),
}))

import InventoryDashboardView from '@/views/inventory/InventoryDashboardView.vue'

const stubs = { PageHeader: true, RouterLink: true }

/** Overview fixture: FE renders whatever BE supplies — no client-side low computation. */
function overview(lowCount: number, items: Array<Record<string, unknown>> = []) {
  return {
    total_parts: 5,
    total_warehouses: 2,
    total_value: 1000,
    low_stock_count: lowCount, // BE-computed (available = on_hand − reserved < effective_min)
    low_stock_items: items,
    movement_30d: {},
  }
}

describe('InventoryDashboardView — tile "Dưới định mức" bind verbatim BE (TC-FE-15-LOW-01)', () => {
  beforeEach(() => { overviewSpy.mockReset() })

  // 1. Verbatim binding ∀ {0, 1, 7} — FE không recompute, render thẳng con số BE.
  it.each([0, 1, 7])('tile render verbatim low_stock_count=%i', async (n) => {
    overviewSpy.mockResolvedValue(overview(n))
    const wrapper = mount(InventoryDashboardView, { global: { stubs } })
    await flushPromises()

    // Bắt đúng ô KPI "Cảnh báo tồn thấp" — không nhặt nhầm số khác trên trang.
    const kpiCards = wrapper.findAll('.kpi-card')
    const lowTile = kpiCards.find(c => c.text().includes('Cảnh báo tồn thấp'))
    expect(lowTile).toBeTruthy()
    expect(lowTile!.find('.t-metric').text()).toBe(String(n))
  })

  // 2. Reserved-full: BE land → bin available=0 (on_hand=100≥min=20) flip LOW.
  //    FE hiển thị count=1 + drill 1 dòng. (Acceptance Core Doc: count==drill, cùng tập.)
  it('reserved-full bin (available=0, on_hand≥min) → count=1 + drill 1 dòng (BE-driven)', async () => {
    overviewSpy.mockResolvedValue(overview(1, [
      {
        bin: 'BIN-RF', spare_part: 'SP-RF', part_name: 'Bơm tiêm điện',
        warehouse: 'WH-1', warehouse_name: 'Kho trung tâm',
        min_stock_level: 20, total_qty: 100, // on_hand 100 ≥ min 20 nhưng available=0 → BE flag low
      },
    ]))
    const wrapper = mount(InventoryDashboardView, { global: { stubs } })
    await flushPromises()

    const lowTile = wrapper.findAll('.kpi-card').find(c => c.text().includes('Cảnh báo tồn thấp'))
    expect(lowTile!.find('.t-metric').text()).toBe('1')

    // Drill: đúng 1 bin red — card count === drill length (no card-vs-drill divergence).
    const rows = wrapper.findAll('[class*="bg-red-50"]')
    expect(rows.length).toBe(1)
    expect(wrapper.text()).toContain('Bơm tiêm điện')
  })

  // 3a. Break-binding sentinel: nếu ai đó đổi template sang hằng số / FE recompute,
  //     test verbatim ở (1) sẽ FAIL. Kiểm tra trực diện: count BE=3 → tile=3, KHÔNG=0.
  it('break-binding guard: BE count=3 → tile hiển thị 3 (không phải 0/hardcode)', async () => {
    overviewSpy.mockResolvedValue(overview(3))
    const wrapper = mount(InventoryDashboardView, { global: { stubs } })
    await flushPromises()
    const lowTile = wrapper.findAll('.kpi-card').find(c => c.text().includes('Cảnh báo tồn thấp'))
    expect(lowTile!.find('.t-metric').text()).toBe('3')
    expect(lowTile!.find('.t-metric').text()).not.toBe('0')
  })

  // 3b. No-leak EN regex — chặn literal kỹ thuật/Anh ngữ lọt UI.
  it('no-leak: không lộ "Reserved/Available/On Hand/Low Stock" hay raw field key', async () => {
    overviewSpy.mockResolvedValue(overview(2, [
      {
        bin: 'BIN-A', spare_part: 'SP-1', part_name: 'Phụ tùng A',
        warehouse: 'WH-A', warehouse_name: 'Kho A', min_stock_level: 50, total_qty: 40,
      },
      {
        bin: 'BIN-B', spare_part: 'SP-2', part_name: 'Phụ tùng B',
        warehouse: 'WH-B', warehouse_name: 'Kho B', min_stock_level: 20, total_qty: 100,
      },
    ]))
    const wrapper = mount(InventoryDashboardView, { global: { stubs } })
    await flushPromises()
    const text = wrapper.text()
    // EN status / column literals
    expect(text).not.toMatch(/\b(Reserved|Available|On Hand|Low Stock|Reorder|Hold)\b/)
    // raw field keys / snake_case payload không được render thô
    expect(text).not.toMatch(/reserved_qty|available_qty|low_stock_count|qty_on_hand|min_stock_level/)
  })
})
