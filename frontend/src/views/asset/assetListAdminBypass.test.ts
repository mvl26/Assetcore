// Copyright (c) 2026, AssetCore Team
// B (hardening / RBAC SSoT — affordance↔route parity): AssetListView batch-print
//
// Chuỗi THẬT view → useCapabilities → auth.can (KHÔNG mock useCapabilities) để
// chứng minh admin-bypass: admin-role + cap-set rỗng asset.* → canPrintLabel=true
// → nút 'In nhãn hàng loạt' + cột checkbox HIỆN (parity route AssetLabelPrint).
// non-admin chỉ-đọc → ẩn (giữ least-privilege, KHÔNG nới lỏng).
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '@/stores/auth'

const routeQuery = ref<Record<string, string>>({})
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useRoute: () => ({ get query() { return routeQuery.value } }),
}))

const assets = [
  { name: 'A1', asset_name: 'TB 1', lifecycle_status: 'Active' },
  { name: 'A2', asset_name: 'TB 2', lifecycle_status: 'Active' },
]
vi.mock('@/stores/imm00', () => ({
  useAssetStore: () => ({
    assets,
    pagination: { page: 1, page_size: 20, total: 2, total_pages: 1 },
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
// KHÔNG mock useCapabilities / @/stores/auth — dùng chuỗi thật.
vi.mock('@/api/layout', () => ({ getUserContext: vi.fn() }))
vi.mock('@/api/auth', () => ({ fetchCapabilities: vi.fn(), logout: vi.fn() }))

import AssetListView from './AssetListView.vue'

const stubs = {
  PageHeader: false, FilterToggleButton: true, ListFilterBar: true,
  BasePagination: true, StatusBadge: true, SkeletonLoader: true,
  ImportWizardModal: true, RouterLink: true,
}

function seedAuth(roles: string[], caps: Record<string, boolean>) {
  const auth = useAuthStore()
  auth.user = {
    name: 'u@assetcore.test', full_name: 'U', email: 'u@assetcore.test',
    roles, role_profile_name: null,
  } as never
  auth.capabilities = caps
}

function batchBtn(w: ReturnType<typeof mount>) {
  return w.findAll('button').find(b => b.text().includes('In nhãn hàng loạt'))
}

describe('AssetListView — admin-bypass batch-print (B parity, chuỗi thật)', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
    routeQuery.value = {}
    setActivePinia(createPinia())
  })

  it('Super Admin + cap-set RỖNG → canPrintLabel=true → nút In hàng loạt + checkbox HIỆN', async () => {
    seedAuth(['AssetCore Super Admin'], {})
    const w = mount(AssetListView, { global: { stubs } })
    await flushPromises()
    expect(batchBtn(w)).toBeTruthy()
    expect(w.find('input[type="checkbox"]').exists()).toBe(true)
  })

  it('System Manager + cap-set RỖNG → nút In hàng loạt HIỆN', async () => {
    seedAuth(['System Manager'], {})
    const w = mount(AssetListView, { global: { stubs } })
    await flushPromises()
    expect(batchBtn(w)).toBeTruthy()
  })

  it('non-admin chỉ-đọc (asset.read) → nút In hàng loạt + checkbox ẩn (least-privilege)', async () => {
    seedAuth(['Data User'], { 'asset.read': true })
    const w = mount(AssetListView, { global: { stubs } })
    await flushPromises()
    expect(batchBtn(w)).toBeFalsy()
    expect(w.find('input[type="checkbox"]').exists()).toBe(false)
  })

  it('non-admin có asset.write → nút In hàng loạt HIỆN (regression thuần-cap)', async () => {
    seedAuth(['Data Manager'], { 'asset.write': true })
    const w = mount(AssetListView, { global: { stubs } })
    await flushPromises()
    expect(batchBtn(w)).toBeTruthy()
  })
})
