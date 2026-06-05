// Copyright (c) 2026, AssetCore Team
// B (hardening / RBAC SSoT — affordance↔route parity): AssetDetailView QR/print
//
// KHÁC assetDetailQrPrint.test.ts / assetDetailRbacAffordance.test.ts: 2 file đó
// mock thẳng useCapabilities (synthetic canCaps) → KHÔNG chạm auth.can(). File này
// dùng CHUỖI THẬT view → useCapabilities → auth.can để chứng minh admin-bypass:
//   • admin-role (AssetCore Super Admin / System Manager) + cap-set RỖNG asset.*
//     → nút 'In nhãn QR' + 'Sinh lại mã QR' HIỆN (parity với route-bypass).
//   • non-admin chỉ-đọc (asset.read, KHÔNG write, KHÔNG admin-role) → vẫn ẩn
//     (giữ least-privilege B-item-1 — KHÔNG nới lỏng).
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '@/stores/auth'

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
}))

const currentAsset = {
  name: 'AC-ASSET-2026-00042', asset_name: 'Máy thở Dräger',
  lifecycle_status: 'Active', risk_classification: 'Low',
}
vi.mock('@/stores/imm00', () => ({
  useAssetStore: () => ({
    currentAsset, loading: false, error: null,
    fetchOne: vi.fn().mockResolvedValue(undefined),
    transition: vi.fn(), error_set: vi.fn(),
  }),
}))
// KHÔNG mock useCapabilities / @/stores/auth — dùng chuỗi thật để test admin-bypass.
vi.mock('@/composables/useNotify', () => ({ useNotify: () => ({ fromError: vi.fn(), success: vi.fn() }) }))
vi.mock('@/composables/useToast', () => ({ useToast: () => ({ show: vi.fn() }) }))
vi.mock('@/api/imm00', () => ({
  getAssetTimeline: vi.fn().mockResolvedValue({ items: [] }),
  getAssetKpi: vi.fn().mockResolvedValue(null),
  verifyChain: vi.fn().mockResolvedValue(null),
  deleteAsset: vi.fn(),
  getAssetLabelData: vi.fn().mockResolvedValue({}),
  markLabelPrinted: vi.fn(),
  regenerateAssetQrToken: vi.fn(),
}))
vi.mock('@/api/imm04', () => ({ getCommissioningOrigin: vi.fn().mockResolvedValue(null) }))
vi.mock('@/api/imm14', () => ({ createDecommission: vi.fn(), approveDecommission: vi.fn() }))
vi.mock('@/api/errors', () => ({ toApiError: (e: unknown) => e }))
vi.mock('qrcode', () => ({ default: { toDataURL: vi.fn().mockResolvedValue('data:image/png;base64,QR==') } }))
// getUserContext / fetchCapabilities chỉ cần stub (test set state trực tiếp).
vi.mock('@/api/layout', () => ({ getUserContext: vi.fn() }))
vi.mock('@/api/auth', () => ({ fetchCapabilities: vi.fn(), logout: vi.fn() }))

import AssetDetailView from './AssetDetailView.vue'

const stubs = {
  PageHeader: { template: '<div><slot name="actions" /></div>' },
  teleport: true, SmartSelect: true, RouterLink: true,
  AssetDowntimeWidget: true, AssetDepreciationSchedule: true,
}

function findBtn(w: ReturnType<typeof mount>, txt: string) {
  return w.findAll('button').find(b => b.text().includes(txt))
}

function seedAuth(roles: string[], caps: Record<string, boolean>) {
  const auth = useAuthStore()
  auth.user = {
    name: 'u@assetcore.test', full_name: 'U', email: 'u@assetcore.test',
    roles, role_profile_name: null,
  } as never
  auth.capabilities = caps
}

describe('AssetDetailView — admin-bypass QR/print (B parity, chuỗi thật)', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
    setActivePinia(createPinia())
  })

  it('Super Admin + cap-set RỖNG → In nhãn QR + Sinh lại mã QR HIỆN (parity route-bypass)', async () => {
    seedAuth(['AssetCore Super Admin'], {})
    const w = mount(AssetDetailView, { props: { id: 'AC-ASSET-2026-00042' }, global: { stubs } })
    await flushPromises()
    expect(findBtn(w, 'In nhãn QR')).toBeTruthy()
    expect(findBtn(w, 'Sinh lại mã QR')).toBeTruthy()
    expect(findBtn(w, 'Chỉnh sửa')).toBeTruthy()
  })

  it('System Manager + cap-set RỖNG → In nhãn QR HIỆN', async () => {
    seedAuth(['System Manager'], {})
    const w = mount(AssetDetailView, { props: { id: 'AC-ASSET-2026-00042' }, global: { stubs } })
    await flushPromises()
    expect(findBtn(w, 'In nhãn QR')).toBeTruthy()
    expect(findBtn(w, 'Sinh lại mã QR')).toBeTruthy()
  })

  it('non-admin chỉ-đọc (asset.read) → In nhãn QR + Sinh lại mã QR vẫn ẩn (least-privilege)', async () => {
    seedAuth(['Data User'], { 'asset.read': true })
    const w = mount(AssetDetailView, { props: { id: 'AC-ASSET-2026-00042' }, global: { stubs } })
    await flushPromises()
    expect(findBtn(w, 'In nhãn QR')).toBeFalsy()
    expect(findBtn(w, 'Sinh lại mã QR')).toBeFalsy()
    // vẫn thấy thông tin (read OK)
    expect(w.text()).toContain('Máy thở Dräger')
  })

  it('non-admin có asset.write → In nhãn QR HIỆN (regression thuần-cap)', async () => {
    seedAuth(['Data Manager'], { 'asset.write': true })
    const w = mount(AssetDetailView, { props: { id: 'AC-ASSET-2026-00042' }, global: { stubs } })
    await flushPromises()
    expect(findBtn(w, 'In nhãn QR')).toBeTruthy()
  })
})
