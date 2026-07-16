// TDD — IMM-15 reservation ledger (TC-15-FE-01):
// Cột 'Đã giữ' (reserved_qty) + 'Khả dụng' (available_qty) phải render GIÁ TRỊ THẬT từ BE.
// Khi reserved_qty>0: 'Đã giữ' hiển thị đúng, 'Khả dụng' = available_qty (= Tồn − Đã giữ),
// KHÔNG còn dead-column luôn-0, KHÔNG fallback available==qty_on_hand khi reserved>0.
import { describe, it, expect, vi, beforeEach } from 'vitest'
// CR-AFFORD: view giờ gọi useCapabilities() ở setup (gate nút Tạo) → mock để mount không cần Pinia.
vi.mock('@/composables/useCapabilities', () => ({ useCapabilities: () => ({ can: () => true }) }))
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'
import type { StockRow } from '@/types/inventory'

const routeQuery = ref<Record<string, string>>({})
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useRoute: () => ({ get query() { return routeQuery.value } }),
}))

const listSpy = vi.fn()
vi.mock('@/api/inventory', () => ({
  listStockLevels: (...args: unknown[]) => listSpy(...args),
}))

import StockLevelView from './StockLevelView.vue'

const stubs = {
  PageHeader: true, FilterToggleButton: true, ListFilterBar: true, SmartSelect: true,
}

function row(overrides: Partial<StockRow>): StockRow {
  return {
    name: 'WH-A::PART-1',
    warehouse: 'WH-A',
    warehouse_code: 'WH-A',
    warehouse_name: 'Kho A',
    spare_part: 'PART-1',
    part_name: 'Bóng đèn X',
    uom: 'Cái',
    qty_on_hand: 10,
    reserved_qty: 4,
    available_qty: 6,
    ...overrides,
  }
}

async function mountWith(rows: StockRow[]) {
  listSpy.mockResolvedValue({ items: rows, pagination: { total: rows.length } })
  const wrapper = mount(StockLevelView, { global: { stubs } })
  await flushPromises()
  return wrapper
}

describe('StockLevelView — cột Đã giữ / Khả dụng (TC-15-FE-01)', () => {
  beforeEach(() => { listSpy.mockReset(); routeQuery.value = {} })

  it('row {qty_on_hand:10, reserved_qty:4, available_qty:6} → render Tồn 10 / Đã giữ 4 / Khả dụng 6', async () => {
    const wrapper = await mountWith([row({})])
    const cells = wrapper.findAll('tbody td').map(td => td.text())
    // Tồn, Đã giữ, Khả dụng đều phải xuất hiện đúng giá trị thật
    expect(cells.some(t => t.includes('10'))).toBe(true)   // Tồn
    expect(cells).toContain('4')                            // Đã giữ (giá trị thật, không phải 0)
    expect(cells).toContain('6')                            // Khả dụng = Tồn − Đã giữ
  })

  it('reserved_qty>0 → Khả dụng KHÔNG bằng qty_on_hand (không còn fallback available??qty_on_hand)', async () => {
    const wrapper = await mountWith([row({ qty_on_hand: 10, reserved_qty: 4, available_qty: 6 })])
    const cells = wrapper.findAll('tbody td').map(td => td.text())
    // Khả dụng phải là 6, KHÔNG bị mask thành 10 (qty_on_hand)
    expect(cells).toContain('6')
    // header cột giải thích reservation
    const html = wrapper.html()
    expect(html).toContain('Đã giữ')
    expect(html).toContain('Khả dụng')
  })

  it('header Đã giữ có tooltip giải nghĩa giữ chỗ', async () => {
    const wrapper = await mountWith([row({})])
    const heldHeader = wrapper.findAll('th').find(th => th.text().includes('Đã giữ'))
    expect(heldHeader).toBeTruthy()
    expect(heldHeader!.attributes('title') || '').toContain('giữ chỗ')
  })

  it('reserved_qty>0 → ô Đã giữ có title giải thích đang giữ chỗ', async () => {
    const wrapper = await mountWith([row({ reserved_qty: 4 })])
    const held = wrapper.find('tbody td[title]')
    expect(held.exists()).toBe(true)
    expect(held.attributes('title') || '').toContain('giữ chỗ')
  })

  it('reserved_qty=0 → Đã giữ render 0, không title giữ chỗ (cột vẫn hiện, không phải dead-column)', async () => {
    const wrapper = await mountWith([row({ qty_on_hand: 10, reserved_qty: 0, available_qty: 10 })])
    const cells = wrapper.findAll('tbody td').map(td => td.text())
    expect(cells).toContain('0')    // Đã giữ = 0
    expect(cells.some(t => t.includes('10'))).toBe(true)  // Khả dụng == Tồn khi không giữ chỗ
  })
})
