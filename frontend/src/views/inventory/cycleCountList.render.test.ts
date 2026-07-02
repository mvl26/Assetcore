// TDD — IMM-15 CycleCountListView render: rows từ listCycleCounts hiển thị nhãn
// tiếng Việt (StatusBadge + loại kiểm kê VI + tên kho), KHÔNG leak raw EN
// 'Planned/Reviewed/Posted'.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn(), info: vi.fn() }),
}))

const ROWS = [
  { name: 'CYC-2026-00001', warehouse: 'WH-A', warehouse_name: 'Kho Trung tâm',
    count_date: '2026-06-01', count_type: 'Cycle', status: 'Planned',
    variance_count: 0, variance_value: 0 },
  { name: 'CYC-2026-00002', warehouse: 'WH-B', warehouse_name: 'Kho Khoa Nội',
    count_date: '2026-06-02', count_type: 'Full', status: 'Reviewed',
    variance_count: 2, variance_value: 1500000 },
  { name: 'CYC-2026-00003', warehouse: 'WH-C', warehouse_name: 'Kho Khoa Ngoại',
    count_date: '2026-06-03', count_type: 'Spot', status: 'Posted',
    variance_count: 1, variance_value: 750000 },
]

const listCycleCounts = vi.fn().mockResolvedValue({
  data: ROWS, pagination: { total: 3, page: 1, page_size: 20, total_pages: 1 },
})
vi.mock('@/api/imm15', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/imm15')>()
  return { ...actual, listCycleCounts: (p: Record<string, unknown>) => listCycleCounts(p) }
})
vi.mock('@/api/inventory', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/inventory')>()
  return { ...actual, listWarehouses: vi.fn().mockResolvedValue({ items: [], pagination: { total: 0 } }) }
})

import CycleCountListView from './CycleCountListView.vue'

async function mountList() {
  const w = mount(CycleCountListView, {
    global: { stubs: { RouterLink: true, Transition: false } },
  })
  await flushPromises()
  return w
}

beforeEach(() => {
  setActivePinia(createPinia())
  listCycleCounts.mockClear()
})

describe('CycleCountListView render', () => {
  it('gọi listCycleCounts và render đủ 3 phiếu', async () => {
    const w = await mountList()
    expect(listCycleCounts).toHaveBeenCalled()
    expect(w.text()).toContain('CYC-2026-00001')
    expect(w.text()).toContain('CYC-2026-00003')
  })

  it('hiển thị TÊN kho (không phải mã)', async () => {
    const w = await mountList()
    expect(w.text()).toContain('Kho Trung tâm')
    expect(w.text()).toContain('Kho Khoa Nội')
  })

  it('trạng thái + loại kiểm kê render tiếng Việt (StatusBadge + label VI)', async () => {
    const w = await mountList()
    const html = w.text()
    expect(html).toContain('Đã lập kế hoạch')   // Planned
    expect(html).toContain('Đã rà soát')         // Reviewed
    expect(html).toContain('Đã ghi nhận')        // Posted
    expect(html).toContain('Chu kỳ')             // count_type Cycle
    expect(html).toContain('Toàn bộ')            // count_type Full
    expect(html).toContain('Đột xuất')           // count_type Spot
  })

  it('KHÔNG leak raw English status ra UI', async () => {
    const w = await mountList()
    const html = w.text()
    expect(html).not.toContain('Planned')
    expect(html).not.toContain('Reviewed')
    expect(html).not.toContain('Posted')
  })

  it('render số dòng lệch + giá trị lệch định dạng tiền VN', async () => {
    const w = await mountList()
    const html = w.text()
    // giá trị lệch 1.500.000 → định dạng vi-VN có ký hiệu ₫
    expect(html).toMatch(/1[.\s]?500[.\s]?000/)
    expect(html).toContain('₫')
  })
})
