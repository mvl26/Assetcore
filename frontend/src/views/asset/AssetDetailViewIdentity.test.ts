// Copyright (c) 2026, AssetCore Team — AssetDetailView identity-display ([V1-E])
//
// SSoT cho ADR-IMM00-ASSETCODE §D1/D4 display layer trên AssetDetailView:
//   • asset_code = "Mã tài sản" (định danh nội bộ = PK) ≠ manufacturer_sn = "Số serial NSX".
//   • Màn read (Detail) hiển thị 2 hàng TÁCH BẠCH, nhãn VI SSoT, KHÔNG leak EN "Serial No".
//   • Invariant asset_code == name ⇒ asset_code rỗng (legacy) → "Mã tài sản" fallback name.
//
// (AssetDetailView.test.ts giữ smoke-check + no-raw-token; file NÀY giữ assertion chi tiết.)
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

vi.mock('vue-router', () => ({ useRouter: () => ({ push: vi.fn() }) }))

// Mutable store fixture — mỗi test set lại currentAsset trước khi mount.
const store = {
  currentAsset: null as Record<string, unknown> | null,
  loading: false,
  error: null as string | null,
  fetchOne: vi.fn().mockResolvedValue(undefined),
  transition: vi.fn(),
}
vi.mock('@/stores/imm00', () => ({ useAssetStore: () => store }))
vi.mock('@/stores/auth', () => ({ useAuthStore: () => ({ user: 'tester' }) }))

const canCaps = new Set<string>(['asset.read', 'asset.write'])
vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({
    can: (c: string | readonly string[]) =>
      Array.isArray(c) ? c.some((x) => canCaps.has(x)) : canCaps.has(c as string),
  }),
}))
vi.mock('@/composables/useNotify', () => ({ useNotify: () => ({ fromError: vi.fn(), success: vi.fn() }) }))
vi.mock('@/composables/useToast', () => ({ useToast: () => ({ show: vi.fn(), success: vi.fn() }) }))
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

import AssetDetailView from './AssetDetailView.vue'

const stubs = {
  PageHeader: true,
  teleport: true,
  SmartSelect: true,
  AssetDowntimeWidget: true,
  AssetDepreciationSchedule: true,
  'router-link': { template: '<a><slot /></a>' },
}

const BASE_ASSET = {
  name: 'TS-2025-USG-001',
  asset_name: 'Máy siêu âm GE LOGIQ E10',
  asset_code: 'TS-2025-USG-001',
  lifecycle_status: 'Active',
  manufacturer_sn: 'SN-ABC-999',
}

function mountWith(asset: Record<string, unknown>) {
  store.currentAsset = asset
  return mount(AssetDetailView, { props: { id: String(asset.name) }, global: { stubs } })
}

describe('AssetDetailView — định danh tài sản (V1-E / ADR-IMM00-ASSETCODE D4)', () => {
  beforeEach(() => {
    store.fetchOne.mockClear()
  })

  it('hiển thị nhãn "Số serial NSX" + giá trị manufacturer_sn, KHÔNG còn "Serial No" (EN)', async () => {
    const w = mountWith({ ...BASE_ASSET })
    await flushPromises()
    const text = w.text()
    expect(text).toContain('Số serial NSX')
    expect(text).toContain('SN-ABC-999')
    // Parity guard chống tái leak EN.
    expect(text).not.toContain('Serial No')
    expect(w.html()).not.toContain('Serial No')
  })

  it('render hàng "Mã tài sản" bind asset_code, TÁCH khỏi hàng serial (2 dt riêng)', async () => {
    const w = mountWith({ ...BASE_ASSET })
    await flushPromises()
    const text = w.text()
    expect(text).toContain('Mã tài sản')
    expect(text).toContain('TS-2025-USG-001') // asset_code
    // 2 nhãn cùng tồn tại, mỗi nhãn đúng 1 lần → user không nhầm.
    const dts = w.findAll('dt').map((d) => d.text())
    expect(dts).toContain('Mã tài sản')
    expect(dts).toContain('Số serial NSX')
    expect(dts.filter((t) => t === 'Mã tài sản')).toHaveLength(1)
    expect(dts.filter((t) => t === 'Số serial NSX')).toHaveLength(1)
  })

  it('edge: asset_code rỗng (legacy) → "Mã tài sản" fallback name', async () => {
    const w = mountWith({ ...BASE_ASSET, asset_code: '' })
    await flushPromises()
    const text = w.text()
    expect(text).toContain('Mã tài sản')
    // Fallback name (invariant asset_code == name).
    expect(text).toContain('TS-2025-USG-001')
  })

  it('edge: manufacturer_sn rỗng → "Số serial NSX" hiển thị "—" (không "undefined")', async () => {
    const w = mountWith({ ...BASE_ASSET, manufacturer_sn: '' })
    await flushPromises()
    const html = w.html()
    expect(w.text()).toContain('Số serial NSX')
    expect(html).not.toContain('undefined')
    const dds = w.findAll('dd').map((d) => d.text())
    expect(dds).toContain('—')
  })
})
