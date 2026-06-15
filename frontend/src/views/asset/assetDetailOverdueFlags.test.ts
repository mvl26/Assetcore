// Copyright (c) 2026, AssetCore Team — AssetDetailView SSoT overdue server-flag (Vòng 3 QR)
//
// CONTEXT (BR-00-36 / FR-00-86 — overdue = SERVER-side flag là SSoT):
//   BE get_asset(name) trả 2 cờ bool `pm_overdue` + `calibration_overdue` derive
//   server-side (tz-safe, STRICT <, exempt BLOCKED_FOR_WO). FE admin-detail
//   (AssetDetailView) PHẢI render highlight đỏ theo CỜ SERVER — TUYỆT ĐỐI KHÔNG
//   so ngày bằng client clock (new Date() < new Date()) cho 2 ô PM/hiệu chuẩn.
//
// Mục tiêu test (RED-first → lock):
//   • pm_overdue=true        → ô "Bảo trì tiếp theo"   có class text-red-600.
//   • pm_overdue=false       → ô "Bảo trì tiếp theo"   KHÔNG đỏ (độc lập ngày).
//   • calibration_overdue=true  → ô "Hiệu chuẩn tiếp theo" đỏ.
//   • calibration_overdue=false dù next_calibration_date là NGÀY QUÁ KHỨ → KHÔNG
//     đỏ (chứng minh FE đọc CỜ, KHÔNG so ngày client — Out of Service exempt).
//   • byt_reg_expiry GIỮ highlight theo logic cũ isPmOverdue (regression guard —
//     fix overdue KHÔNG vô tình chạm ô đăng ký Bộ Y tế).
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
}))

// Payload có thể mutate per-test (gán field overdue trước mỗi mount).
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
  // SSoT preset khổ tem (selector 3-preset Vòng 4) — view import ở module-level.
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
  asset_name: 'Máy theo dõi bệnh nhân Overdue',
  asset_code: 'AC-MON-0099',
  lifecycle_status: 'Active',
  category_name: 'Thiết bị theo dõi',
}

/** Lấy class của <dd> cùng hàng với <dt> chứa `label`. */
function ddClassForLabel(html: string, label: string): string {
  // Cấu trúc: <div class="flex justify-between"> <dt ...>label</dt> <dd class="...">value</dd> </div>
  const dtIdx = html.indexOf(`>${label}<`)
  if (dtIdx === -1) return ''
  const ddOpen = html.indexOf('<dd', dtIdx)
  const ddClassMatch = html.slice(ddOpen).match(/^<dd[^>]*class="([^"]*)"/)
  return ddClassMatch ? ddClassMatch[1] : ''
}

async function mountWith(asset: Record<string, unknown>) {
  for (const k of Object.keys(currentAsset)) delete currentAsset[k]
  Object.assign(currentAsset, BASE, asset)
  const w = mount(AssetDetailView, { props: { id: BASE.name }, global: { stubs } })
  await flushPromises()
  return w
}

describe('AssetDetailView — SSoT overdue server-flag (KHÔNG so ngày client)', () => {
  beforeEach(() => {
    for (const k of Object.keys(currentAsset)) delete currentAsset[k]
  })

  it('pm_overdue=true → ô "Bảo trì tiếp theo" highlight đỏ', async () => {
    const w = await mountWith({
      next_pm_date: '2026-06-01',
      pm_overdue: true,
    })
    expect(ddClassForLabel(w.html(), 'Bảo trì tiếp theo')).toContain('text-red-600')
  })

  it('pm_overdue=false → ô "Bảo trì tiếp theo" KHÔNG đỏ (độc lập giá trị ngày)', async () => {
    // next_pm_date là NGÀY QUÁ KHỨ nhưng cờ server=false → KHÔNG đỏ (đọc cờ, không so ngày).
    const w = await mountWith({
      next_pm_date: '2020-01-01',
      pm_overdue: false,
    })
    expect(ddClassForLabel(w.html(), 'Bảo trì tiếp theo')).not.toContain('text-red-600')
  })

  it('calibration_overdue=true → ô "Hiệu chuẩn tiếp theo" highlight đỏ', async () => {
    const w = await mountWith({
      next_calibration_date: '2026-06-01',
      calibration_overdue: true,
    })
    expect(ddClassForLabel(w.html(), 'Hiệu chuẩn tiếp theo')).toContain('text-red-600')
  })

  it('calibration_overdue=false dù next_calibration_date QUÁ KHỨ → KHÔNG đỏ (đọc cờ, không so ngày client)', async () => {
    // Out of Service exempt: BE đã trả calibration_overdue=false dù ngày quá khứ.
    // FE PHẢI tôn trọng cờ — nếu FE so ngày client thì sẽ đỏ SAI → test bắt.
    const w = await mountWith({
      lifecycle_status: 'Out of Service',
      next_calibration_date: '2020-01-01',
      calibration_overdue: false,
    })
    expect(ddClassForLabel(w.html(), 'Hiệu chuẩn tiếp theo')).not.toContain('text-red-600')
  })

  it('byt_reg_expiry GIỮ highlight theo logic cũ (regression guard — không bị fix chạm)', async () => {
    // Hạn đăng ký Bộ Y tế quá khứ → isPmOverdue client-display vẫn đỏ (OUT scope SSoT).
    const w = await mountWith({
      byt_reg_expiry: '2020-01-01',
    })
    expect(ddClassForLabel(w.html(), 'Hạn đăng ký Bộ Y tế')).toContain('text-red-600')
  })
})
