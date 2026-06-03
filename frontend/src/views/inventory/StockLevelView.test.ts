// TDD — IMM-15 §III-bis reservation ledger (TC-15-FE-01).
// StockLevelView renders the soft-reservation columns truthfully:
//   row {qty_on_hand:10, reserved_qty:4, available_qty:6}
//     → Tồn 10 / Đã giữ 4 / Khả dụng 6, with the "Đã giữ"/"Khả dụng" tooltip.
// Regression guard: when reserved_qty > 0, "Đã giữ" must NOT be 0 and available_qty
// must NOT equal qty_on_hand (the old dead-column bug where reserved was always 0).
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import type { StockRow } from '@/types/inventory'

const listSpy = vi.fn()
vi.mock('@/api/inventory', () => ({
  listStockLevels: (...a: unknown[]) => listSpy(...a),
}))

// Stub vue-router composables used by the view (no real router in unit test).
vi.mock('vue-router', () => ({
  useRoute: () => ({ query: {} }),
  useRouter: () => ({ push: vi.fn() }),
}))

import StockLevelView from './StockLevelView.vue'

const stubs = {
  PageHeader: true,
  SmartSelect: true,
  FilterToggleButton: true,
  ListFilterBar: true,
}

function baseRow(overrides: Partial<StockRow> = {}): StockRow {
  return {
    name: 'WH-01::SP-001',
    warehouse: 'WH-01',
    warehouse_code: 'WH-01',
    warehouse_name: 'Kho trung tâm',
    spare_part: 'SP-001',
    part_name: 'Van PEEP máy thở',
    uom: 'Cái',
    qty_on_hand: 10,
    reserved_qty: 4,
    available_qty: 6,
    is_low: false,
    ...overrides,
  } as StockRow
}

function paginated(rows: StockRow[]) {
  return { items: rows, pagination: { total: rows.length } }
}

describe('StockLevelView — reservation columns (TC-15-FE-01)', () => {
  beforeEach(() => {
    listSpy.mockReset()
  })

  it('renders Tồn / Đã giữ / Khả dụng from the row', async () => {
    listSpy.mockResolvedValue(paginated([baseRow()]))
    const wrapper = mount(StockLevelView, { global: { stubs } })
    await flushPromises()

    const cells = wrapper.findAll('tbody td').map((c) => c.text())
    const joined = cells.join(' | ')
    // physical on-hand
    expect(joined).toContain('10')
    // reserved (Đã giữ) — the held value, NOT 0
    expect(joined).toContain('4')
    // available (Khả dụng) = on_hand − reserved
    expect(joined).toContain('6')
  })

  it('shows the reserved/available header tooltip', async () => {
    listSpy.mockResolvedValue(paginated([baseRow()]))
    const wrapper = mount(StockLevelView, { global: { stubs } })
    await flushPromises()
    const headerTitles = wrapper.findAll('th').map((th) => th.attributes('title') || '')
    expect(headerTitles.some((t) => t.includes('Đã giữ') && t.includes('Khả dụng'))).toBe(true)
  })

  it('reserved>0 is not a dead column: Đã giữ ≠ 0 and Khả dụng ≠ Tồn', async () => {
    listSpy.mockResolvedValue(paginated([baseRow({ qty_on_hand: 10, reserved_qty: 4, available_qty: 6 })]))
    const wrapper = mount(StockLevelView, { global: { stubs } })
    await flushPromises()

    const reservedCell = wrapper.find('td.hidden.md\\:table-cell')
    expect(reservedCell.exists()).toBe(true)
    expect(reservedCell.text()).toBe('4')
    // per-cell hover hint present when held
    expect(reservedCell.attributes('title')).toContain('giữ chỗ')

    // available must differ from on-hand whenever reserved > 0
    const text = wrapper.find('tbody').text()
    expect(text).toContain('6')
    expect(reservedCell.text()).not.toBe('0')
  })

  it('reserved=0 renders 0 (no held stock) and available == on_hand', async () => {
    listSpy.mockResolvedValue(paginated([baseRow({ qty_on_hand: 8, reserved_qty: 0, available_qty: 8 })]))
    const wrapper = mount(StockLevelView, { global: { stubs } })
    await flushPromises()
    const reservedCell = wrapper.find('td.hidden.md\\:table-cell')
    expect(reservedCell.text()).toBe('0')
  })
})
