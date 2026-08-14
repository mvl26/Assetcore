// TDD — Core Doc §9.4.5 (R7): SparePartListView pre-applies route.query.low_stock.
// Drill từ KPI store 'low_stock' → /spare-parts?low_stock=1 → list chỉ parts dưới định mức.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'

const routeQuery = ref<Record<string, string>>({})
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useRoute: () => ({ get query() { return routeQuery.value } }),
}))

const listSpy = vi.fn().mockResolvedValue({ items: [], pagination: { total: 0 } })
vi.mock('@/api/inventory', () => ({
  listSpareParts: (...args: unknown[]) => listSpy(...args),
  createSparePart: vi.fn(),
}))

import SparePartListView from '@/views/inventory/SparePartListView.vue'

const stubs = {
  PageHeader: true, FilterToggleButton: true, ListFilterBar: true,
  SkeletonLoader: true, SmartSelect: true, RouterLink: true,
}

describe('SparePartListView low-stock drill (Core Doc §9.4.5)', () => {
  beforeEach(() => { listSpy.mockClear(); routeQuery.value = {} })

  it('query.low_stock=1 → listSpareParts gọi với low_stock=1', async () => {
    routeQuery.value = { low_stock: '1' }
    mount(SparePartListView, { global: { stubs } })
    await flushPromises()
    const args = listSpy.mock.calls.map(c => c[0])
    expect(args.some(a => a?.low_stock === 1)).toBe(true)
  })

  it('không có query → listSpareParts không kèm low_stock', async () => {
    routeQuery.value = {}
    mount(SparePartListView, { global: { stubs } })
    await flushPromises()
    const arg = listSpy.mock.calls[0][0]
    expect(arg?.low_stock).toBeUndefined()
  })
})
