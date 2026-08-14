// TDD — IMM-15 CycleCountCreateView: submit form gọi createCycleCount đúng payload
// {warehouse, count_type, spare_parts} rồi điều hướng sang chi tiết phiếu vừa tạo.
// Chống dead-control (GATE-6c): payload phát đi == lựa chọn trên UI.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { routerPushSpy, resetRouteMock } from '@/test/vueRouterMock'

vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn(), info: vi.fn() }),
}))
vi.mock('@/composables/useNotify', () => ({
  useNotify: () => ({ show: vi.fn(), fromError: vi.fn(), fromOk: vi.fn() }),
}))

const createCycleCount = vi.fn().mockResolvedValue({
  name: 'CYC-2026-00099', workflow_state: 'Planned', items_count: 1,
})
vi.mock('@/api/imm15', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/imm15')>()
  return { ...actual, createCycleCount: (p: unknown) => createCycleCount(p) }
})

const searchParts = vi.fn().mockResolvedValue([
  { name: 'SP-1', part_code: 'SP-001', part_name: 'Cảm biến SpO2' },
])
vi.mock('@/api/inventory', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/inventory')>()
  return {
    ...actual,
    listWarehouses: vi.fn().mockResolvedValue({
      items: [{ name: 'WH-A', warehouse_name: 'Kho Trung tâm', is_active: 1 }],
      pagination: { total: 1 },
    }),
    listStockLevels: vi.fn().mockResolvedValue({ items: [], pagination: { total: 0 } }),
    searchParts: (q: string, l: number, wh: string) => searchParts(q, l, wh),
  }
})

import CycleCountCreateView from '@/views/inventory/CycleCountCreateView.vue'

async function mountCreate() {
  const w = mount(CycleCountCreateView, {
    global: { stubs: { RouterLink: true, Transition: false } },
  })
  await flushPromises()
  return w
}

beforeEach(() => {
  setActivePinia(createPinia())
  resetRouteMock()
  createCycleCount.mockClear()
  searchParts.mockClear()
})

describe('CycleCountCreateView submit', () => {
  it('gửi payload {warehouse,count_type,spare_parts} đúng UI + điều hướng chi tiết', async () => {
    const w = await mountCreate()

    // Chọn kho
    await w.find('#cc-warehouse').setValue('WH-A')
    // count_type mặc định 'Cycle'; đổi rõ ràng cho chắc
    await w.find('#cc-type').setValue('Cycle')

    // Tìm + thêm 1 phụ tùng
    const search = w.find('#cc-part-search')
    await search.setValue('SpO2')
    await search.trigger('input')
    await flushPromises()
    expect(searchParts).toHaveBeenCalled()
    await w.find('[data-testid="cc-part-result"]').trigger('click')
    await flushPromises()

    // Submit
    await w.find('[data-testid="cc-submit"]').trigger('click')
    await flushPromises()

    expect(createCycleCount).toHaveBeenCalledTimes(1)
    expect(createCycleCount).toHaveBeenCalledWith({
      warehouse: 'WH-A', count_type: 'Cycle', spare_parts: ['SP-1'],
    })
    // Điều hướng sang chi tiết phiếu vừa tạo
    expect(routerPushSpy()).toHaveBeenCalledWith({
      name: 'CycleCountDetail', params: { name: 'CYC-2026-00099' },
    })
  })

  it('chưa chọn kho → nút tạo bị vô hiệu (không gọi API)', async () => {
    const w = await mountCreate()
    const btn = w.find('[data-testid="cc-submit"]')
    expect(btn.attributes('disabled')).toBeDefined()
  })
})
