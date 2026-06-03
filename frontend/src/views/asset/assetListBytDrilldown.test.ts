// TDD — BR-00-17 (NĐ98): AssetListView pre-applies route.query.byt_status drill.
//
// SoT predicate sống ở BE (byt_expiry_filter). FE chỉ FORWARD byt_status xuống
// list_assets + hiển thị chip VI (SSoT label BYT_STATUS_LABEL). count==drill được
// đảm bảo BE; test này PIN contract FE: query → fetchList({byt_status}), chip VI,
// clear chip → param mất, header 'Tổng N' == số rows store trả.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'
import { BYT_EXPIRY_CHIP_LABEL } from '@/constants/labels'

const routeQuery = ref<Record<string, string>>({})
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useRoute: () => ({ get query() { return routeQuery.value } }),
}))

const fetchListSpy = vi.fn().mockResolvedValue(undefined)
const storeState = {
  assets: [] as Record<string, unknown>[],
  pagination: { page: 1, page_size: 20, total: 0, total_pages: 0 },
  loading: false,
  error: null as string | null,
  fetchList: fetchListSpy,
}
vi.mock('@/stores/imm00', () => ({
  useAssetStore: () => storeState,
  useRefDataStore: () => ({
    categories: [], departments: [], locations: [],
    fetchAll: vi.fn().mockResolvedValue(undefined),
  }),
}))
vi.mock('@/composables/useImportWizard', () => ({
  useImportWizard: () => ({ open: vi.fn(), doExport: vi.fn() }),
}))

import AssetListView from './AssetListView.vue'

const stubs = {
  PageHeader: true, FilterToggleButton: true, ListFilterBar: true,
  BasePagination: true, StatusBadge: true, SkeletonLoader: true,
  ImportWizardModal: true, RouterLink: true,
}

describe('AssetListView BYT drill-down (BR-00-17, NĐ98)', () => {
  beforeEach(() => {
    fetchListSpy.mockClear()
    routeQuery.value = {}
    storeState.assets = []
    storeState.pagination = { page: 1, page_size: 20, total: 0, total_pages: 0 }
  })

  it('route.query.byt_status=expired → fetchList({byt_status:expired})', async () => {
    routeQuery.value = { byt_status: 'expired' }
    mount(AssetListView, { global: { stubs } })
    await flushPromises()
    expect(fetchListSpy).toHaveBeenCalled()
    const arg = fetchListSpy.mock.calls[0][0]
    expect(arg?.byt_status).toBe('expired')
  })

  it('route.query.byt_status=expiring → fetchList({byt_status:expiring})', async () => {
    routeQuery.value = { byt_status: 'expiring' }
    mount(AssetListView, { global: { stubs } })
    await flushPromises()
    const arg = fetchListSpy.mock.calls[0][0]
    expect(arg?.byt_status).toBe('expiring')
  })

  it('không có query → fetchList KHÔNG kèm byt_status', async () => {
    routeQuery.value = {}
    mount(AssetListView, { global: { stubs } })
    await flushPromises()
    const arg = fetchListSpy.mock.calls[0][0]
    expect(arg?.byt_status).toBeUndefined()
  })

  it('chip VI SSoT hiển thị khi byt_status set; nhãn KHÔNG hardcode', async () => {
    routeQuery.value = { byt_status: 'expired' }
    const wrapper = mount(AssetListView, { global: { stubs } })
    await flushPromises()
    // activeChips (computed) phải chứa chip byt_status với nhãn SSoT, KHÔNG raw-EN.
    const vm = wrapper.vm as unknown as { activeChips: { key: string; label: string }[] }
    const chip = vm.activeChips.find((c) => c.key === 'byt_status')
    expect(chip).toBeTruthy()
    expect(chip!.label).toBe(BYT_EXPIRY_CHIP_LABEL.expired)
    expect(chip!.label).not.toContain('expired')  // không leak raw enum
  })

  it('clear chip byt_status → param bị bỏ (fetchList không còn byt_status)', async () => {
    routeQuery.value = { byt_status: 'expiring' }
    const wrapper = mount(AssetListView, { global: { stubs } })
    await flushPromises()
    fetchListSpy.mockClear()
    // gọi clearChip('byt_status') qua component instance (như nút X chip)
    const vm = wrapper.vm as unknown as { clearChip: (k: string) => void }
    vm.clearChip('byt_status')
    await flushPromises()
    expect(fetchListSpy).toHaveBeenCalled()
    const arg = fetchListSpy.mock.calls[fetchListSpy.mock.calls.length - 1][0]
    expect(arg?.byt_status).toBeUndefined()
  })

  it("header 'Tổng N' == pagination.total store trả (count==drill mặt FE)", async () => {
    routeQuery.value = { byt_status: 'expired' }
    storeState.pagination = { page: 1, page_size: 20, total: 7, total_pages: 1 }
    // PageHeader render subtitle 'Tổng N' qua prop → mount thật để đọc.
    const wrapper = mount(AssetListView, {
      global: { stubs: { ...stubs, PageHeader: false } },
    })
    await flushPromises()
    expect(wrapper.text()).toContain('Tổng 7')
  })
})
