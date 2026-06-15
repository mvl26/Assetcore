// TDD — Core Doc §9.6: D-FE-11/12 AssetListView pre-applies route.query filter.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'

// Mutable route mock — đổi query giữa các test để mô phỏng drill-down.
const routeQuery = ref<Record<string, string>>({})
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useRoute: () => ({ get query() { return routeQuery.value } }),
}))

// Spy fetchList — assert được gọi với filter pre-applied.
const fetchListSpy = vi.fn().mockResolvedValue(undefined)
vi.mock('@/stores/imm00', () => ({
  useAssetStore: () => ({
    assets: [],
    pagination: { page: 1, page_size: 20, total: 0, total_pages: 0 },
    loading: false,
    error: null,
    fetchList: fetchListSpy,
  }),
  useRefDataStore: () => ({
    categories: [], departments: [], locations: [],
    fetchAll: vi.fn().mockResolvedValue(undefined),
  }),
}))

// Import wizard composable — stub (không liên quan drill-down).
vi.mock('@/composables/useImportWizard', () => ({
  useImportWizard: () => ({ open: vi.fn(), doExport: vi.fn() }),
}))
// D6 (ADR-IMM00-QR-SCAN-ACTION, phương án B): AssetListView gate nút in nhãn =
// asset.print. Test drilldown không quan tâm gate in → giả lập user CÓ asset.print.
vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({ can: (c: string | readonly string[]) =>
    Array.isArray(c) ? c.includes('asset.print') : c === 'asset.print' }),
}))

import AssetListView from './AssetListView.vue'

const stubs = {
  PageHeader: true, FilterToggleButton: true, ListFilterBar: true,
  BasePagination: true, StatusBadge: true, SkeletonLoader: true,
  ImportWizardModal: true, RouterLink: true,
}

describe('AssetListView drill-down query (D-FE-11, D-FE-12)', () => {
  beforeEach(() => {
    fetchListSpy.mockClear()
    routeQuery.value = {}
  })

  it('D-FE-11: route.query.lifecycle_status=Active → fetchList được gọi với filter pre-applied', async () => {
    routeQuery.value = { lifecycle_status: 'Active' }
    mount(AssetListView, { global: { stubs } })
    await flushPromises()
    expect(fetchListSpy).toHaveBeenCalled()
    const arg = fetchListSpy.mock.calls[0][0]
    expect(arg).toBeTruthy()
    expect(arg.lifecycle_status).toBe('Active')
  })

  it('D-FE-11b: không có query → fetchList gọi không kèm filter status', async () => {
    routeQuery.value = {}
    mount(AssetListView, { global: { stubs } })
    await flushPromises()
    expect(fetchListSpy).toHaveBeenCalled()
    const arg = fetchListSpy.mock.calls[0][0]
    // undefined hoặc object không chứa lifecycle_status
    expect(arg?.lifecycle_status).toBeUndefined()
  })

  it('D-FE-12: đổi route.query lần 2 → watch re-apply filter mới', async () => {
    routeQuery.value = { lifecycle_status: 'Active' }
    mount(AssetListView, { global: { stubs } })
    await flushPromises()
    fetchListSpy.mockClear()

    routeQuery.value = { lifecycle_status: 'Under Repair' }
    await flushPromises()
    expect(fetchListSpy).toHaveBeenCalled()
    const arg = fetchListSpy.mock.calls[0][0]
    expect(arg.lifecycle_status).toBe('Under Repair')
  })
})
