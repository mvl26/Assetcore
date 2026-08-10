// INV-ROWSCOPE — đối xứng A5/A8 cho IMM-08: "Tổng N phiếu" ở PMWorkOrderListView
// PHẢI đọc `store.pagination.total` (SoT permission-aware của BE), KHÔNG phái sinh
// từ `store.workOrders.length`. Cùng lý do như CM (xem cmListTotalFromServer.test.ts):
// fallback client-count che giấu drift count-vs-rows — chính lớp lỗi INV-ROWSCOPE đóng.
//
// "Hiển thị X phiếu" GIỮ `.length` (số dòng trang hiện tại) — ranh giới không đổi.
// FE KHÔNG thêm predicate phân quyền nào (LL-FE-47); enforcement là server-side.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { resetRouteMock } from '@/test/vueRouterMock'

vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())

interface PmRow {
  name: string
  status: string
  asset_ref: string
  asset_name: string
  pm_type: string
  due_date: string
}

function makeRows(n: number): PmRow[] {
  return Array.from({ length: n }, (_, i) => ({
    name: `WO-PM-2026-${String(i + 1).padStart(5, '0')}`,
    status: 'Open',
    asset_ref: `AC-ASSET-2026-${i + 1}`,
    asset_name: `Máy X-quang ${i + 1}`,
    pm_type: 'Routine',
    due_date: '2026-08-01',
  }))
}

const storeState = {
  workOrders: [] as PmRow[],
  pagination: { page: 1, page_size: 20, total: 0, total_pages: 0 } as {
    page: number
    page_size: number
    total: number | undefined
    total_pages: number
  },
}

vi.mock('@/stores/imm08', () => ({
  useImm08Store: () => ({
    get workOrders() { return storeState.workOrders },
    get pagination() { return storeState.pagination },
    kpis: null,
    loading: false,
    error: null,
    fetchWorkOrders: vi.fn().mockResolvedValue(undefined),
    fetchKPIs: vi.fn().mockResolvedValue(undefined),
    fetchDashboardStats: vi.fn().mockResolvedValue(undefined),
    dashboardStats: null,
  }),
}))

vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({ can: () => true }),
}))

import PMWorkOrderListView from './PMWorkOrderListView.vue'

const PageHeaderStub = {
  props: ['title', 'subtitle', 'breadcrumb'],
  template: '<div><span data-test="page-subtitle">{{ subtitle }}</span><slot name="actions" /></div>',
}

const stubs = {
  PageHeader: PageHeaderStub,
  FilterToggleButton: true,
  ListFilterBar: true,
  BasePagination: true,
  SkeletonLoader: true,
  WorkOrderKpiStrip: true,
  DateInput: true,
  RouterLink: true,
}

async function mountAndReadSubtitle(): Promise<string> {
  const w = mount(PMWorkOrderListView, { global: { stubs } })
  await flushPromises()
  return w.get('[data-test="page-subtitle"]').text()
}

describe('PMWorkOrderListView — "Tổng" lấy từ server (INV-ROWSCOPE A5)', () => {
  beforeEach(() => {
    resetRouteMock()
    storeState.workOrders = []
    storeState.pagination = { page: 1, page_size: 20, total: 0, total_pages: 0 }
  })

  it('pagination.total=57 với 20 dòng ⇒ subtitle "Tổng 57 phiếu"', async () => {
    storeState.workOrders = makeRows(20)
    storeState.pagination = { page: 1, page_size: 20, total: 57, total_pages: 3 }

    const subtitle = await mountAndReadSubtitle()

    expect(subtitle).toContain('Tổng 57')
    expect(subtitle).not.toContain('Tổng 20')
  })

  it('pagination.total=0 với 0 dòng ⇒ "Tổng 0 phiếu" (không undefined/NaN)', async () => {
    const subtitle = await mountAndReadSubtitle()

    expect(subtitle).toContain('Tổng 0')
    expect(subtitle).not.toMatch(/undefined|NaN/)
  })

  it('total undefined với 99 dòng ⇒ "Tổng 0" (fallback client-count đã bị bỏ)', async () => {
    storeState.workOrders = makeRows(99)
    storeState.pagination = { page: 1, page_size: 100, total: undefined, total_pages: 1 }

    const subtitle = await mountAndReadSubtitle()

    expect(subtitle).toContain('Tổng 0')
    expect(subtitle).not.toContain('Tổng 99')
  })

  it('"Hiển thị" vẫn là số dòng trang hiện tại (.length), không phải total', async () => {
    storeState.workOrders = makeRows(20)
    storeState.pagination = { page: 1, page_size: 20, total: 57, total_pages: 3 }

    const w = mount(PMWorkOrderListView, { global: { stubs } })
    await flushPromises()

    expect(w.text()).toMatch(/Hiển thị\s*20/)
  })
})
