// CR-18 — PMWorkOrderListView: free-text search phía SERVER (mã phiếu / mã thiết
// bị / tên thiết bị). Gõ ô tìm → store.fetchWorkOrders được gọi với param `search`
// (refetch server, reset trang 1). KHÔNG còn lọc client-side page-limited: mock
// server trả rows ⇒ hiển thị dù chuỗi search KHÔNG khớp theo bộ lọc-cũ-client.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { resetRouteMock } from '@/test/vueRouterMock'

vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())

// Rows server trả về — dùng chung cho cả 2 nhóm test (spy + render).
const serverRows = [
  { name: 'PM-WO-2026-00042', asset_ref: 'ACC-ASS-2026-0001', asset_name: 'Máy thở Dräger', pm_type: 'Quarterly', status: 'Open', due_date: '2026-07-20', is_late: 0, assigned_to: 'a@x.vn', assigned_to_name: 'Anh A' },
]
const fetchWOSpy = vi.fn().mockResolvedValue(undefined)
vi.mock('@/stores/imm08', () => ({
  useImm08Store: () => ({
    workOrders: serverRows,
    dashboardStats: null,
    pagination: { page: 1, page_size: 20, total: 1, total_pages: 1 },
    loading: false,
    error: null,
    fetchWorkOrders: fetchWOSpy,
    fetchDashboardStats: vi.fn().mockResolvedValue(undefined),
  }),
}))

vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({ can: () => true }),
}))

import PMWorkOrderListView from './PMWorkOrderListView.vue'

// ListFilterBar stub: cho phép mô phỏng gõ ô tìm (update:search) + debounce-apply.
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
// BasePagination stub: phát page-change để verify search phủ mọi trang.
const BasePaginationStub = {
  props: ['pagination'],
  emits: ['page-change'],
  template: `<button class="page2-btn" @click="$emit('page-change', 2)"></button>`,
}
const stubs = {
  PageHeader: true, FilterToggleButton: true, BasePagination: BasePaginationStub,
  StatusBadge: true, SkeletonLoader: true, WorkOrderKpiStrip: true,
  DateInput: true, RouterLink: true, ListFilterBar: ListFilterBarStub,
}

describe('PMWorkOrderListView — CR-18 server-side search', () => {
  beforeEach(() => { fetchWOSpy.mockClear(); resetRouteMock() })

  it('gõ ô tìm → fetchWorkOrders gọi với param search (arg thứ 3) + reset trang 1', async () => {
    const w = mount(PMWorkOrderListView, { global: { stubs } })
    await flushPromises()
    // onMounted fetch baseline — KHÔNG kèm search.
    expect(fetchWOSpy.mock.calls[0][2]).toBeUndefined()
    fetchWOSpy.mockClear()

    await w.find('.search-box').setValue('Dräger')   // update:search → ref='Dräger'
    await w.find('.apply-btn').trigger('click')        // apply (post-debounce) → reload(1)
    await flushPromises()

    expect(fetchWOSpy).toHaveBeenCalled()
    const call = fetchWOSpy.mock.calls.at(-1)!
    expect(call[1]).toBe(1)             // reset về trang 1
    expect(call[2]).toBe('Dräger')      // param search phát đi == UI-selection (GATE-6c)
  })

  it('search KHÔNG khớp text-cũ-client vẫn HIỂN THỊ rows server (đã gỡ lọc client-side)', async () => {
    const w = mount(PMWorkOrderListView, { global: { stubs } })
    await flushPromises()
    // Trước CR-18: matchesQuery lọc client → gõ 'zzz-no-match' ẩn hết rows đã tải.
    await w.find('.search-box').setValue('zzz-khong-khop-client')
    await flushPromises()
    // Server là nguồn sự thật: rows vẫn render (KHÔNG bị computed client cắt).
    expect(w.text()).toContain('PM-WO-2026-00042')
    expect(w.text()).toContain('Máy thở Dräger')
  })

  it('chip search hiển thị khi có search + xóa chip → reload server không search', async () => {
    const w = mount(PMWorkOrderListView, { global: { stubs } })
    await flushPromises()
    await w.find('.search-box').setValue('PM-2026')
    await w.find('.apply-btn').trigger('click')
    await flushPromises()
    const chips = (w.vm as unknown as { activeChips: { key: string; label: string }[] }).activeChips
    expect(chips.some(c => c.key === 'search')).toBe(true)

    fetchWOSpy.mockClear()
    await w.find('.clear-search-btn').trigger('click')   // clear-chip 'search'
    await flushPromises()
    const call = fetchWOSpy.mock.calls.at(-1)!
    expect(call[2]).toBeUndefined()   // reload không kèm search sau khi xóa chip
  })

  it('paginate giữ search: đổi trang → fetchWorkOrders kèm search hiện tại', async () => {
    const w = mount(PMWorkOrderListView, { global: { stubs } })
    await flushPromises()
    await w.find('.search-box').setValue('Dräger')
    await w.find('.apply-btn').trigger('click')
    await flushPromises()
    fetchWOSpy.mockClear()
    await w.find('.page2-btn').trigger('click')   // @page-change=2 → reload(2)
    await flushPromises()
    const call = fetchWOSpy.mock.calls.at(-1)!
    expect(call[1]).toBe(2)
    expect(call[2]).toBe('Dräger')   // search phủ TOÀN tập mọi trang
  })
})
