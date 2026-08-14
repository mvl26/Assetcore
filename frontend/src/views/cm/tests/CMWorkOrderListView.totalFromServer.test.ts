// INV-ROWSCOPE (ADR-IMM00-LIST-SCOPE) — A8/FE-1: "Tổng N lệnh" ở CMWorkOrderListView
// PHẢI đọc từ `store.pagination.total` (SoT permission-aware do BE trả về), KHÔNG
// bao giờ phái sinh từ `store.workOrders.length`.
//
// Vì sao là guard chứ không phải test trang trí: fallback cũ
// `pagination.total ?? store.workOrders.length` CHE GIẤU drift count-vs-rows —
// đúng lớp lỗi mà INV-ROWSCOPE đóng (đếm được N phiếu nhưng chỉ đọc được M vì
// count permission-aware còn rows thì không). Nếu ai đó đưa fallback client-count
// quay lại, case "drift" + case "undefined" dưới đây ĐỎ ngay.
//
// Ranh giới KHÔNG đổi: "Hiển thị X lệnh" (info-row của mobile list + bảng desktop)
// VẪN là `.length` — đó là số dòng của TRANG hiện tại, khác nghĩa với tổng.
// FE KHÔNG thêm bất kỳ predicate phân quyền nào (chống dead-control LL-FE-47);
// enforcement row-scope là server-side.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { resetRouteMock } from '@/test/vueRouterMock'

vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())

interface WoRow {
  name: string
  status: string
  asset_ref: string
  asset_name: string
  repair_type: string
  priority: string
  open_datetime: string
}

function makeRows(n: number): WoRow[] {
  return Array.from({ length: n }, (_, i) => ({
    name: `WO-RP-2026-${String(i + 1).padStart(5, '0')}`,
    status: 'Open',
    asset_ref: `AC-ASSET-2026-${i + 1}`,
    asset_name: `Máy thở ${i + 1}`,
    repair_type: 'Corrective',
    priority: 'Normal',
    open_datetime: '2026-07-01 08:30:00',
  }))
}

// State mutable — mỗi test set trước khi mount.
const storeState = {
  workOrders: [] as WoRow[],
  pagination: { page: 1, page_size: 20, total: 0, total_pages: 0 } as {
    page: number
    page_size: number
    total: number | undefined
    total_pages: number
  },
}

vi.mock('@/stores/imm09', () => ({
  useImm09Store: () => ({
    get workOrders() { return storeState.workOrders },
    get pagination() { return storeState.pagination },
    kpis: null,
    loading: false,
    error: null,
    fetchWorkOrders: vi.fn().mockResolvedValue(undefined),
    fetchKPIs: vi.fn().mockResolvedValue(undefined),
  }),
}))

vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({ can: () => true }),
}))

import CMWorkOrderListView from '@/views/cm/CMWorkOrderListView.vue'

// PageHeader stub render subtitle thật để assert được nội dung "Tổng N lệnh".
const PageHeaderStub = {
  props: ['title', 'subtitle', 'breadcrumb'],
  template: '<div><span data-test="page-subtitle">{{ subtitle }}</span><slot name="actions" /></div>',
}

const stubs = {
  PageHeader: PageHeaderStub,
  FilterToggleButton: true,
  ListFilterBar: true,
  BasePagination: true,
  StatusBadge: true,
  SkeletonLoader: true,
  WorkOrderKpiStrip: true,
  RouterLink: true,
}

async function mountAndReadSubtitle(): Promise<string> {
  const w = mount(CMWorkOrderListView, { global: { stubs } })
  await flushPromises()
  return w.get('[data-test="page-subtitle"]').text()
}

describe('CMWorkOrderListView — "Tổng" lấy từ server (INV-ROWSCOPE A8)', () => {
  beforeEach(() => {
    resetRouteMock()
    storeState.workOrders = []
    storeState.pagination = { page: 1, page_size: 20, total: 0, total_pages: 0 }
  })

  // (a) tổng server > số dòng trang hiện tại → hiện tổng server, không phải 20.
  it('pagination.total=57 với 20 dòng ⇒ subtitle "Tổng 57 lệnh"', async () => {
    storeState.workOrders = makeRows(20)
    storeState.pagination = { page: 1, page_size: 20, total: 57, total_pages: 3 }

    const subtitle = await mountAndReadSubtitle()

    expect(subtitle).toContain('Tổng 57')
    expect(subtitle).not.toContain('Tổng 20')
  })

  // (b) rỗng thật sự → "Tổng 0", KHÔNG 'undefined'/'NaN' lọt ra UI.
  it('pagination.total=0 với 0 dòng ⇒ subtitle "Tổng 0 lệnh" (không undefined/NaN)', async () => {
    storeState.workOrders = []
    storeState.pagination = { page: 1, page_size: 20, total: 0, total_pages: 0 }

    const subtitle = await mountAndReadSubtitle()

    expect(subtitle).toContain('Tổng 0')
    expect(subtitle).not.toMatch(/undefined|NaN/)
  })

  // (c) GUARD chống fallback client-count quay lại: giả lập drift count-vs-rows
  // (server nói 3, store đang giữ 99 dòng) ⇒ UI vẫn phải bám server.
  it('drift: total=3 nhưng workOrders.length=99 ⇒ vẫn "Tổng 3" (không phái sinh .length)', async () => {
    storeState.workOrders = makeRows(99)
    storeState.pagination = { page: 1, page_size: 100, total: 3, total_pages: 1 }

    const subtitle = await mountAndReadSubtitle()

    expect(subtitle).toContain('Tổng 3')
    expect(subtitle).not.toContain('Tổng 99')
  })

  // (c-bis) GUARD trực diện cho `?? 0`: total undefined (BE lỗi/shape cũ) ⇒ "Tổng 0",
  // KHÔNG rơi về .length. Fallback cũ `?? store.workOrders.length` sẽ ra "Tổng 99" ⇒ ĐỎ.
  it('total undefined với 99 dòng ⇒ "Tổng 0" (fallback client-count đã bị bỏ)', async () => {
    storeState.workOrders = makeRows(99)
    storeState.pagination = { page: 1, page_size: 100, total: undefined, total_pages: 1 }

    const subtitle = await mountAndReadSubtitle()

    expect(subtitle).toContain('Tổng 0')
    expect(subtitle).not.toContain('Tổng 99')
    expect(subtitle).not.toMatch(/undefined|NaN/)
  })

  // Ranh giới: "Hiển thị X" (số dòng trang hiện tại) KHÔNG bị đổi theo total.
  it('"Hiển thị" vẫn là số dòng trang hiện tại (.length), không phải total', async () => {
    storeState.workOrders = makeRows(20)
    storeState.pagination = { page: 1, page_size: 20, total: 57, total_pages: 3 }

    const w = mount(CMWorkOrderListView, { global: { stubs } })
    await flushPromises()
    const body = w.text()

    expect(body).toContain('Hiển thị')
    expect(body).toMatch(/Hiển thị\s*20/)
  })
})
