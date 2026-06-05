// Copyright (c) 2026, AssetCore Team — AssetListView chọn nhiều + in hàng loạt (A4/V5, TDD)
//
// RED-prove (task A4):
//   • có checkbox chọn nhiều asset; chọn 3 → nút 'In nhãn hàng loạt' enabled;
//     bấm → router.push tới AssetLabelPrint với 3 names THEO THỨ TỰ đã chọn.
//   • chưa chọn asset nào → nút disabled + hint VI (empty-state).
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'

const routeQuery = ref<Record<string, string>>({})
const pushSpy = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: pushSpy }),
  useRoute: () => ({ get query() { return routeQuery.value } }),
}))

const assets = [
  { name: 'A1', asset_name: 'TB 1', lifecycle_status: 'Active' },
  { name: 'A2', asset_name: 'TB 2', lifecycle_status: 'Active' },
  { name: 'A3', asset_name: 'TB 3', lifecycle_status: 'Active' },
]
vi.mock('@/stores/imm00', () => ({
  useAssetStore: () => ({
    assets,
    pagination: { page: 1, page_size: 20, total: 3, total_pages: 1 },
    loading: false, error: null,
    fetchList: vi.fn().mockResolvedValue(undefined),
  }),
  useRefDataStore: () => ({
    categories: [], departments: [], locations: [],
    fetchAll: vi.fn().mockResolvedValue(undefined),
  }),
}))
vi.mock('@/composables/useImportWizard', () => ({
  useImportWizard: () => ({ open: vi.fn(), doExport: vi.fn() }),
}))
// B (siết RBAC): nút 'In nhãn hàng loạt' + cột checkbox gate asset.WRITE.
// `canCaps` set ngoài test để giả lập user write / user chỉ-đọc.
const canCaps = new Set<string>(['asset.write'])
vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({
    can: (c: string | readonly string[]) =>
      Array.isArray(c) ? c.some((x) => canCaps.has(x)) : canCaps.has(c as string),
  }),
}))

import AssetListView from './AssetListView.vue'
import { MAX_LABEL_BATCH } from '@/constants/label'

const stubs = {
  PageHeader: false, FilterToggleButton: true, ListFilterBar: true,
  BasePagination: true, StatusBadge: true, SkeletonLoader: true,
  ImportWizardModal: true, RouterLink: true,
}

describe('AssetListView — chọn nhiều + in nhãn hàng loạt (A4)', () => {
  beforeEach(() => {
    pushSpy.mockClear()
    routeQuery.value = {}
    // mặc định: user CÓ asset.write (write user) cho các case batch bên dưới.
    canCaps.clear()
    canCaps.add('asset.write')
  })

  it("B — user CHỈ-ĐỌC (asset.read, KHÔNG asset.write) → nút 'In nhãn hàng loạt' KHÔNG render", async () => {
    canCaps.clear()
    canCaps.add('asset.read')
    const w = mount(AssetListView, { global: { stubs } })
    await flushPromises()
    expect(w.findAll('button').find(b => b.text().includes('In nhãn hàng loạt'))).toBeFalsy()
    // cột checkbox chọn-hàng-loạt cũng KHÔNG render cho user chỉ-đọc.
    expect(w.find('input[type="checkbox"]').exists()).toBe(false)
  })

  it('chưa chọn asset → nút In hàng loạt disabled + hint VI (empty-state)', async () => {
    const w = mount(AssetListView, { global: { stubs } })
    await flushPromises()
    const btn = w.findAll('button').find(b => b.text().includes('In nhãn hàng loạt'))
    expect(btn).toBeTruthy()
    expect(btn!.attributes('disabled')).toBeDefined()
  })

  it('chọn 3 asset → nút enabled; bấm → router.push AssetLabelPrint với 3 names THEO THỨ TỰ', async () => {
    const w = mount(AssetListView, { global: { stubs } })
    await flushPromises()
    // Chọn qua API expose (selectedNames) để độc lập với layout checkbox.
    const vm = w.vm as unknown as { toggleSelect: (n: string) => void; selectedNames: string[] }
    vm.toggleSelect('A1')
    vm.toggleSelect('A2')
    vm.toggleSelect('A3')
    await flushPromises()
    const btn = w.findAll('button').find(b => b.text().includes('In nhãn hàng loạt'))
    expect(btn!.attributes('disabled')).toBeUndefined()
    await btn!.trigger('click')
    await flushPromises()
    expect(pushSpy).toHaveBeenCalledTimes(1)
    const arg = pushSpy.mock.calls[0][0]
    expect(arg.name).toBe('AssetLabelPrint')
    expect(arg.query.names).toBe('A1,A2,A3')
  })

  // ── Vòng B (BR-00-33) — CAP batch-size: nút disabled khi chọn > giới hạn ──────
  it('B — chọn ĐÚNG MAX_LABEL_BATCH → nút enabled (biên dưới PASS)', async () => {
    const w = mount(AssetListView, { global: { stubs } })
    await flushPromises()
    const vm = w.vm as unknown as { selectedNames: string[] }
    vm.selectedNames.splice(0, vm.selectedNames.length,
      ...Array.from({ length: MAX_LABEL_BATCH }, (_, i) => `A${i}`))
    await flushPromises()
    const btn = w.findAll('button').find(b => b.text().includes('In nhãn hàng loạt'))
    expect(btn!.attributes('disabled')).toBeUndefined()
  })

  it('B — chọn > MAX_LABEL_BATCH → nút disabled + hint VI; bấm KHÔNG điều hướng', async () => {
    const w = mount(AssetListView, { global: { stubs } })
    await flushPromises()
    const vm = w.vm as unknown as { selectedNames: string[] }
    vm.selectedNames.splice(0, vm.selectedNames.length,
      ...Array.from({ length: MAX_LABEL_BATCH + 1 }, (_, i) => `A${i}`))
    await flushPromises()
    const btn = w.findAll('button').find(b => b.text().includes('In nhãn hàng loạt'))
    expect(btn!.attributes('disabled')).toBeDefined()
    // Hint VI cảnh báo giới hạn (role=alert), nêu số giới hạn.
    const alert = w.find('[role="alert"]')
    expect(alert.exists()).toBe(true)
    expect(alert.text()).toContain(String(MAX_LABEL_BATCH))
    expect(alert.text()).toContain('tối đa')
    // Bấm nút (force) → KHÔNG điều hướng (request chắc-chắn-413 bị chặn ở FE).
    await btn!.trigger('click')
    await flushPromises()
    expect(pushSpy).not.toHaveBeenCalled()
  })
})
