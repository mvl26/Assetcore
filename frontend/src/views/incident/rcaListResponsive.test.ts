// TDD — TC-RWD-09 (F5 P3): RCAListView nhánh mobile-card-list (sm:hidden) BÊN CẠNH
// table (hidden sm:block). viewport 375px → render card-list, KHÔNG chỉ table cuộn ngang.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())

const rca = {
  name: 'RCA-2026-00001',
  incident_report: 'IR-2026-00009',
  asset: 'AC-ASSET-2026-00001',
  asset_name: 'Máy thở Dräger',
  rca_method: '5-Why',
  assigned_to: 'tech@x.test',
  assigned_to_name: 'KTV Nguyễn',
  linked_capa: 'CAPA-2026-0003',
  status: 'RCA In Progress',
  trigger_type: 'Critical',
}

vi.mock('@/stores/imm12', () => ({
  useImm12Store: () => ({
    rcaListItems: [rca],
    rcaPagination: { page: 1, page_size: 20, total: 1, total_pages: 1 },
    rcaLoading: false,
    rcaError: null,
    fetchRcas: vi.fn().mockResolvedValue(undefined),
  }),
}))

import RCAListView from './RCAListView.vue'

const stubs = {
  PageHeader: true,
  FilterToggleButton: true,
  ListFilterBar: true,
  BasePagination: true,
  SkeletonLoader: true,
}

describe('TC-RWD-09 — RCAListView mobile card-list (F5)', () => {
  beforeEach(() => vi.clearAllMocks())

  it('render ≥1 .mobile-card-list node', async () => {
    const w = mount(RCAListView, { global: { stubs } })
    await flushPromises()
    expect(w.findAll('.mobile-card-list').length).toBeGreaterThanOrEqual(1)
  })

  it('mobile-card-list có class sm:hidden', async () => {
    const w = mount(RCAListView, { global: { stubs } })
    await flushPromises()
    const cardList = w.find('.mobile-card-list')
    expect(cardList.exists()).toBe(true)
    expect(cardList.attributes('class') || '').toContain('sm:hidden')
  })

  it('table desktop bọc trong nhánh hidden sm:block', async () => {
    const w = mount(RCAListView, { global: { stubs } })
    await flushPromises()
    const table = w.find('table')
    expect(table.exists()).toBe(true)
    // ancestor có hidden sm:block
    expect(w.html()).toContain('hidden sm:block')
  })

  it('card hiển thị mã RCA + tên thiết bị (đọc được, không leak mã)', async () => {
    const w = mount(RCAListView, { global: { stubs } })
    await flushPromises()
    const cardList = w.find('.mobile-card-list')
    expect(cardList.text()).toContain('RCA-2026-00001')
    expect(cardList.text()).toContain('Máy thở Dräger')
  })
})
