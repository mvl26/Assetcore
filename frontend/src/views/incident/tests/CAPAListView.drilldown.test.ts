// TDD — Core Doc §9.4.8 (R10): CAPAListView pre-applies route.query (status/not_closed/overdue).
// Drill từ KPI qa: capa_open → ?not_closed=1; capa_overdue → ?overdue=1.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'

const routeQuery = ref<Record<string, string>>({})
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useRoute: () => ({ get query() { return routeQuery.value } }),
}))

const fetchListSpy = vi.fn().mockResolvedValue(undefined)
vi.mock('@/stores/imm00', () => ({
  useCapaStore: () => ({
    capas: [],
    pagination: { page: 1, page_size: 20, total: 0, total_pages: 0 },
    loading: false,
    error: null,
    fetchList: fetchListSpy,
  }),
}))

import CAPAListView from '@/views/incident/CAPAListView.vue'

const stubs = {
  PageHeader: true, FilterToggleButton: true, ListFilterBar: true,
  BasePagination: true, SkeletonLoader: true, RouterLink: true,
}

describe('CAPAListView drill-down query (Core Doc §9.4.8)', () => {
  beforeEach(() => { fetchListSpy.mockClear(); routeQuery.value = {} })

  it('query.not_closed=1 → fetchList gọi với not_closed=1', async () => {
    routeQuery.value = { not_closed: '1' }
    mount(CAPAListView, { global: { stubs } })
    await flushPromises()
    const saw = fetchListSpy.mock.calls.some(
      (c) => (c[0] as Record<string, unknown> | undefined)?.not_closed === 1)
    expect(saw).toBe(true)
  })

  it('query.overdue=1 → fetchList gọi với overdue=1', async () => {
    routeQuery.value = { overdue: '1' }
    mount(CAPAListView, { global: { stubs } })
    await flushPromises()
    const saw = fetchListSpy.mock.calls.some(
      (c) => (c[0] as Record<string, unknown> | undefined)?.overdue === 1)
    expect(saw).toBe(true)
  })

  it('không có query → fetchList không kèm not_closed/overdue', async () => {
    routeQuery.value = {}
    mount(CAPAListView, { global: { stubs } })
    await flushPromises()
    const arg = fetchListSpy.mock.calls[0][0] as Record<string, unknown> | undefined
    expect(arg?.not_closed).toBeUndefined()
    expect(arg?.overdue).toBeUndefined()
  })

  // TDD-7 (BR-00-16 conjoin guard): status=CODE + not_closed/overdue gửi ĐỒNG THỜI.
  // Drill từ KPI capa_open rồi user thu hẹp bằng chip status=Overdue → FE PHẢI forward
  // CẢ HAI để BE conjoin (AND) → count == số dòng render, KHÔNG còn 'chọn Quá hạn vẫn 117'.
  it('query.not_closed=1 + status=Overdue → fetchList gửi CẢ HAI (conjoin)', async () => {
    routeQuery.value = { not_closed: '1', status: 'Overdue' }
    mount(CAPAListView, { global: { stubs } })
    await flushPromises()
    const saw = fetchListSpy.mock.calls.some((c) => {
      const a = c[0] as Record<string, unknown> | undefined
      return a?.not_closed === 1 && a?.status === 'Overdue'
    })
    expect(saw).toBe(true)
  })

  it('query.overdue=1 + status=Open → fetchList gửi CẢ HAI (conjoin)', async () => {
    routeQuery.value = { overdue: '1', status: 'Open' }
    mount(CAPAListView, { global: { stubs } })
    await flushPromises()
    const saw = fetchListSpy.mock.calls.some((c) => {
      const a = c[0] as Record<string, unknown> | undefined
      return a?.overdue === 1 && a?.status === 'Open'
    })
    expect(saw).toBe(true)
  })
})
