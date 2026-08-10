// Copyright (c) 2026, AssetCore Team — AssetDetailView badge BẢO HÀNH server-flag (CR-38)
//
// CONTEXT (CR-38 — parity get_asset_scan_info; warranty = SERVER-side flag SSoT):
//   BE get_asset(name) trả 2 field parity: `warranty_expired` (bool derive
//   server-side qua CHÍNH _is_warranty_expired, tz-safe STRICT <) + `warranty_expiry_date`
//   (str 'YYYY-MM-DD' | null qua _date_str_or_none). FE admin-detail (AssetDetailView)
//   render badge "Bảo hành: Còn hạn / Hết hạn" theo CỜ SERVER — TUYỆT ĐỐI KHÔNG so
//   ngày bằng client clock. date null → ẩn badge (placeholder '—'), KHÔNG vỡ.
//
// Mục tiêu test (assert render TỪ prop server-flag, KHÔNG mock so-ngày client):
//   • warranty_expired=true  + date  → badge text "Hết hạn" (đỏ).
//   • warranty_expired=false + date  → badge text "Còn hạn" (xanh) — kể cả date QUÁ KHỨ
//     (chứng minh FE đọc CỜ server, KHÔNG so ngày client).
//   • warranty_expiry_date null       → KHÔNG có badge (ẩn), hàng "Bảo hành" hiện '—'.
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
}))

// Payload có thể mutate per-test (gán field warranty trước mỗi mount).
const currentAsset: Record<string, unknown> = {}

vi.mock('@/stores/imm00', () => ({
  useAssetStore: () => ({
    currentAsset,
    loading: false,
    error: null,
    fetchOne: vi.fn().mockResolvedValue(undefined),
    transition: vi.fn(),
  }),
}))
vi.mock('@/stores/auth', () => ({ useAuthStore: () => ({ user: 'tester' }) }))

const canCaps = new Set<string>(['asset.read', 'asset.write'])
vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({
    can: (c: string | readonly string[]) =>
      Array.isArray(c) ? c.some((x) => canCaps.has(x)) : canCaps.has(c as string),
  }),
}))
vi.mock('@/composables/useNotify', () => ({
  useNotify: () => ({ fromError: vi.fn(), success: vi.fn() }),
}))
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ show: vi.fn(), success: vi.fn() }),
}))
vi.mock('@/api/imm00', () => ({
  getAssetTimeline: vi.fn().mockResolvedValue({ items: [] }),
  getAssetKpi: vi.fn().mockResolvedValue(null),
  verifyChain: vi.fn().mockResolvedValue(null),
  deleteAsset: vi.fn(),
  getAssetLabelData: vi.fn().mockResolvedValue({}),
  markLabelPrinted: vi.fn(),
  regenerateAssetQrToken: vi.fn(),
  printAssetLabelsPdf: vi.fn(),
  LABEL_PDF_PRESETS: [
    { key: 'tem-60x100', label: 'Tem 60×100mm' },
    { key: 'tem-70x40', label: 'Tem 70×40mm' },
    { key: 'tem-50x30', label: 'Tem 50×30mm' },
  ],
  LABEL_PDF_PRESET: 'tem-60x100',
  labelPdfPresetLabel: (p: string) =>
    ({ 'tem-60x100': 'Tem 60×100mm', 'tem-70x40': 'Tem 70×40mm', 'tem-50x30': 'Tem 50×30mm' } as Record<string, string>)[p] ?? '',
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

const BASE = {
  name: 'AC-ASSET-2026-00099',
  asset_name: 'Máy theo dõi bệnh nhân Bảo hành',
  asset_code: 'AC-MON-0099',
  lifecycle_status: 'Active',
  category_name: 'Thiết bị theo dõi',
}

async function mountWith(asset: Record<string, unknown>) {
  for (const k of Object.keys(currentAsset)) delete currentAsset[k]
  Object.assign(currentAsset, BASE, asset)
  const w = mount(AssetDetailView, { props: { id: BASE.name }, global: { stubs } })
  await flushPromises()
  return w
}

describe('AssetDetailView — badge BẢO HÀNH server-flag (CR-38, KHÔNG so ngày client)', () => {
  beforeEach(() => {
    for (const k of Object.keys(currentAsset)) delete currentAsset[k]
  })

  it('warranty_expired=true → badge "Hết hạn" (đỏ)', async () => {
    const w = await mountWith({
      warranty_expiry_date: '2020-01-01',
      warranty_expired: true,
    })
    const badge = w.find('[data-testid="warranty-badge"]')
    expect(badge.exists()).toBe(true)
    expect(badge.text()).toContain('Hết hạn')
    expect(badge.classes().join(' ')).toContain('text-red-700')
  })

  it('warranty_expired=false (dù date QUÁ KHỨ) → badge "Còn hạn" (xanh) — đọc cờ, KHÔNG so ngày client', async () => {
    // date quá khứ nhưng cờ server=false → nếu FE so ngày client sẽ ra "Hết hạn" SAI → test bắt.
    const w = await mountWith({
      warranty_expiry_date: '2020-01-01',
      warranty_expired: false,
    })
    const badge = w.find('[data-testid="warranty-badge"]')
    expect(badge.exists()).toBe(true)
    expect(badge.text()).toContain('Còn hạn')
    expect(badge.text()).not.toContain('Hết hạn')
    expect(badge.classes().join(' ')).toContain('text-emerald-700')
  })

  it('warranty_expiry_date null → KHÔNG có badge (ẩn), hàng "Bảo hành" render placeholder', async () => {
    const w = await mountWith({
      warranty_expiry_date: null,
      warranty_expired: false,
    })
    expect(w.find('[data-testid="warranty-badge"]').exists()).toBe(false)
    // Hàng "Bảo hành" vẫn tồn tại (KHÔNG vỡ) — chỉ ẩn badge.
    expect(w.html()).toContain('Bảo hành')
  })
})
