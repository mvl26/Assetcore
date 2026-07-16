// CR-18 — CMWorkOrderListView: free-text search phía SERVER (mã phiếu / mã thiết
// bị / tên thiết bị). Đối xứng PMWorkOrderListView.search.test.ts — KHÁC store imm09.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { resetRouteMock } from '@/test/vueRouterMock'

vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())

const serverRows = [
  { name: 'WO-RP-2026-00123', asset_ref: 'ACC-ASS-2026-0009', asset_name: 'Máy X-quang Siemens', repair_type: 'Corrective', priority: 'Normal', status: 'In Repair', open_datetime: '2026-07-01 09:00:00', mttr_hours: 0, sla_breached: 0, is_sla_breached: false, is_repeat_failure: 0, assigned_to: 'a@x.vn', assigned_to_name: 'Anh A', department_name: 'Khoa CĐHA', location_name: 'Tầng 2' },
]
const fetchWOSpy = vi.fn().mockResolvedValue(undefined)
vi.mock('@/stores/imm09', () => ({
  useImm09Store: () => ({
    workOrders: serverRows,
    kpis: null,
    pagination: { page: 1, page_size: 20, total: 1, total_pages: 1 },
    loading: false,
    error: null,
    fetchWorkOrders: fetchWOSpy,
    fetchKPIs: vi.fn().mockResolvedValue(undefined),
  }),
}))

vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({ can: () => true }),
}))

import CMWorkOrderListView from './CMWorkOrderListView.vue'

const ListFilterBarStub = {
  props: ['search', 'chips', 'show', 'searchPlaceholder'],
  emits: ['update:search', 'apply', 'reset', 'clear-chip'],
  template: `<div>
    <input class="search-box" :value="search"
      @input="$emit('update:search', $event.target.value)" />
    <button class="apply-btn" @click="$emit('apply')"></button>
    <button class="clear-search-btn" @click="$emit('clear-chip', 'search')"></button>
  </div>`,
}
const BasePaginationStub = {
  props: ['pagination'],
  emits: ['page-change'],
  template: `<button class="page2-btn" @click="$emit('page-change', 2)"></button>`,
}
const stubs = {
  PageHeader: true, FilterToggleButton: true, BasePagination: BasePaginationStub,
  StatusBadge: true, SkeletonLoader: true, WorkOrderKpiStrip: true,
  RouterLink: true, ListFilterBar: ListFilterBarStub,
}

describe('CMWorkOrderListView — CR-18 server-side search', () => {
  beforeEach(() => { fetchWOSpy.mockClear(); resetRouteMock() })

  it('gõ ô tìm → fetchWorkOrders gọi với param search (arg thứ 3) + reset trang 1', async () => {
    const w = mount(CMWorkOrderListView, { global: { stubs } })
    await flushPromises()
    expect(fetchWOSpy.mock.calls[0][2]).toBeUndefined()   // baseline không search
    fetchWOSpy.mockClear()

    await w.find('.search-box').setValue('Siemens')
    await w.find('.apply-btn').trigger('click')
    await flushPromises()

    const call = fetchWOSpy.mock.calls.at(-1)!
    expect(call[1]).toBe(1)
    expect(call[2]).toBe('Siemens')
  })

  it('search KHÔNG khớp text-cũ-client vẫn HIỂN THỊ rows server (đã gỡ lọc client-side)', async () => {
    const w = mount(CMWorkOrderListView, { global: { stubs } })
    await flushPromises()
    await w.find('.search-box').setValue('zzz-khong-khop-client')
    await flushPromises()
    expect(w.text()).toContain('WO-RP-2026-00123')
    expect(w.text()).toContain('Máy X-quang Siemens')
  })

  it('chip search hiển thị + xóa chip → reload server không search', async () => {
    const w = mount(CMWorkOrderListView, { global: { stubs } })
    await flushPromises()
    await w.find('.search-box').setValue('WO-RP')
    await w.find('.apply-btn').trigger('click')
    await flushPromises()
    const chips = (w.vm as unknown as { activeChips: { key: string; label: string }[] }).activeChips
    expect(chips.some(c => c.key === 'search')).toBe(true)

    fetchWOSpy.mockClear()
    await w.find('.clear-search-btn').trigger('click')
    await flushPromises()
    expect(fetchWOSpy.mock.calls.at(-1)![2]).toBeUndefined()
  })

  it('paginate giữ search: đổi trang → fetchWorkOrders kèm search hiện tại', async () => {
    const w = mount(CMWorkOrderListView, { global: { stubs } })
    await flushPromises()
    await w.find('.search-box').setValue('Siemens')
    await w.find('.apply-btn').trigger('click')
    await flushPromises()
    fetchWOSpy.mockClear()
    await w.find('.page2-btn').trigger('click')
    await flushPromises()
    const call = fetchWOSpy.mock.calls.at(-1)!
    expect(call[1]).toBe(2)
    expect(call[2]).toBe('Siemens')
  })
})
