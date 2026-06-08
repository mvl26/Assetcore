// Copyright (c) 2026, AssetCore Team — AssetDetailView no-raw-token regression (task B)
//
// CONTEXT (ADR-001 §D4 rule 9 — no-raw-token):
//   BE strips `qr_token` từ payload as_dict ở MỌI đường đọc AC Asset
//   (get_asset / get_asset_timeline / get_asset_kpi). Strip phải TRONG SUỐT với FE.
//
// Mục tiêu test (FE regression — lock no-hidden-dependency):
//   • AssetDetailView render ĐẦY ĐỦ với payload KHÔNG có key `qr_token`
//     (mock store.currentAsset bỏ field) → 0 lỗi, không white-screen.
//   • Các field cốt lõi VẪN render: asset_name, name, lifecycle_status (nhãn VI),
//     category_name, device_model_name, location_name, supplier_name.
//   • Khẳng định FE KHÔNG có chỗ phụ thuộc ngầm vào `qr_token`
//     (payload bỏ field mà view vẫn xanh) → BE strip an toàn.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

// ── Mock router (router-link stub + useRouter) ──────────────────────────────────
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
}))

// ── Payload AC Asset ĐẦY ĐỦ field hiển thị, CỐ TÌNH KHÔNG có `qr_token` ──────────
// (Mô phỏng đúng shape BE trả SAU khi _strip_qr_token: token thô không rời BE.)
const currentAsset = {
  name: 'AC-ASSET-2026-00042',
  asset_name: 'Máy thở Dräger Evita V600',
  asset_code: 'AC-VENT-0042',
  lifecycle_status: 'Active',
  asset_category: 'CAT-0007',
  category_name: 'Thiết bị hỗ trợ hô hấp',
  device_model: 'DM-DRAGER-V600',
  device_model_name: 'Dräger Evita V600',
  supplier: 'SUP-2026-00011',
  supplier_name: 'Công ty TNHH Dräger Việt Nam',
  department: 'DEP-ICU',
  department_name: 'Khoa Hồi sức tích cực',
  location: 'LOC-ICU-01',
  location_name: 'ICU - Giường 01',
  responsible_technician: 'tech@miyano.com.vn',
  responsible_technician_name: 'Nguyễn Văn Kỹ',
  manufacturer_sn: 'SN-DRG-998877',
  udi_code: '(01)04054566000123(21)998877',
  gmdn_code: '12345',
  risk_classification: 'High',
  purchase_date: '2025-01-10',
  gross_purchase_amount: 1200000000,
  // ⛔ KHÔNG có `qr_token` ở đây — token thô đã bị strip ở BE.
}

const fetchOneSpy = vi.fn().mockResolvedValue(undefined)
vi.mock('@/stores/imm00', () => ({
  useAssetStore: () => ({
    currentAsset,
    loading: false,
    error: null,
    fetchOne: fetchOneSpy,
    transition: vi.fn(),
  }),
}))
vi.mock('@/stores/auth', () => ({ useAuthStore: () => ({ user: 'tester' }) }))

// Quyền đầy đủ để render mọi affordance (read+write) — không ảnh hưởng no-token.
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

describe('AssetDetailView — no-raw-token regression (B)', () => {
  beforeEach(() => {
    fetchOneSpy.mockClear()
  })

  it('payload KHÔNG có key qr_token (đúng shape BE sau _strip_qr_token)', () => {
    // Self-check fixture: nếu ai vô tình thêm qr_token vào mock, test này đỏ ngay.
    expect('qr_token' in currentAsset).toBe(false)
  })

  it('render ĐẦY ĐỦ — không white-screen dù payload thiếu qr_token', async () => {
    const w = mount(AssetDetailView, { props: { id: 'AC-ASSET-2026-00042' }, global: { stubs } })
    await flushPromises()
    const html = w.html()
    // View thực sự render khối chi tiết (không kẹt ở loading/error).
    expect(html).toContain('Máy thở Dräger Evita V600')
    expect(w.text()).not.toContain('Đang tải')
  })

  it('các field cốt lõi VẪN hiển thị sau khi BE bỏ qr_token', async () => {
    const w = mount(AssetDetailView, { props: { id: 'AC-ASSET-2026-00042' }, global: { stubs } })
    await flushPromises()
    const text = w.text()
    // Định danh + mã
    expect(text).toContain('Máy thở Dräger Evita V600')
    expect(text).toContain('AC-ASSET-2026-00042')
    // Trạng thái hiển thị nhãn tiếng Việt (KHÔNG để lộ 'Active' EN thô làm nhãn chính)
    expect(text).toContain('Đang hoạt động')
    // Thông tin chung — display name (không leak mã)
    expect(text).toContain('Thiết bị hỗ trợ hô hấp') // category_name
    expect(text).toContain('Công ty TNHH Dräger Việt Nam') // supplier_name
    expect(text).toContain('Khoa Hồi sức tích cực') // department_name
    expect(text).toContain('ICU - Giường 01') // location_name
    expect(text).toContain('Nguyễn Văn Kỹ') // responsible_technician_name
    // Thông tin HTM
    expect(text).toContain('SN-DRG-998877') // manufacturer_sn
  })

  it('HTML render KHÔNG chứa chuỗi qr_token (token thô không lọt ra UI)', async () => {
    const w = mount(AssetDetailView, { props: { id: 'AC-ASSET-2026-00042' }, global: { stubs } })
    await flushPromises()
    expect(w.html()).not.toContain('qr_token')
  })

  // [V1-E] Smoke: payload no-token VẪN render đúng nhãn VI serial (không EN leak).
  // Coverage chi tiết ở describe "định danh card …" bên dưới (cùng file → self-contained).
  it('card "Thông tin HTM" dùng nhãn VI "Số serial NSX" — KHÔNG leak EN "Serial No"', async () => {
    const w = mount(AssetDetailView, { props: { id: 'AC-ASSET-2026-00042' }, global: { stubs } })
    await flushPromises()
    const text = w.text()
    expect(text).toContain('Số serial NSX')
    expect(text).not.toContain('Serial No')
  })
})

// ── [V1-E] Đồng bộ định danh trên card "Thông tin HTM" (ADR-IMM00-ASSETCODE §D1/D4) ──
// FE-TDD RED→GREEN. asset_code="Mã tài sản"(PK) ≠ manufacturer_sn="Số serial NSX".
// Màn read PHẢI tách bạch 2 hàng + nhãn VI SSoT; KHÔNG leak EN "Serial No". Coverage
// đặt CÙNG file (không phụ thuộc file chuyên-biệt có thể vắng) → đảm bảo regression-lock.
async function mountIdentity(patch: Partial<typeof currentAsset> = {}) {
  Object.assign(currentAsset, patch)
  const w = mount(AssetDetailView, { props: { id: 'AC-ASSET-2026-00042' }, global: { stubs } })
  await flushPromises()
  return w
}

describe('AssetDetailView — định danh card "Thông tin HTM" [ADR-IMM00-ASSETCODE D4 / V1-E]', () => {
  beforeEach(() => {
    // Reset 2 field định danh về giá trị "đầy đủ" trước mỗi case (case edit chúng).
    currentAsset.asset_code = 'AC-VENT-0042'
    currentAsset.manufacturer_sn = 'SN-DRG-998877'
  })

  it('hiển thị nhãn "Số serial NSX" + giá trị serial, KHÔNG còn EN "Serial No"', async () => {
    const w = await mountIdentity({ asset_code: 'TS-2025-USG-001', manufacturer_sn: 'SN-ABC-999' })
    const text = w.text()
    expect(text).toContain('Số serial NSX')
    expect(text).toContain('SN-ABC-999')
    expect(text).not.toContain('Serial No')
    expect(w.html()).not.toContain('Serial No')
  })

  it('render hàng "Mã tài sản" bind asset_code, TÁCH bạch khỏi hàng serial (dt/dd riêng)', async () => {
    const w = await mountIdentity({ asset_code: 'TS-2025-USG-001', manufacturer_sn: 'SN-ABC-999' })
    const text = w.text()
    expect(text).toContain('Mã tài sản')
    expect(text).toContain('TS-2025-USG-001')
    const dts = w.findAll('dt').map((d) => d.text())
    expect(dts).toContain('Mã tài sản')
    expect(dts).toContain('Số serial NSX')
    expect(dts.filter((t) => t === 'Mã tài sản')).toHaveLength(1)
    expect(dts.filter((t) => t === 'Số serial NSX')).toHaveLength(1)
  })

  it('edge: asset_code rỗng (legacy) → hàng "Mã tài sản" fallback hiển thị name', async () => {
    const w = await mountIdentity({ asset_code: '', manufacturer_sn: 'SN-ABC-999' })
    const dts = w.findAll('dt').map((d) => d.text())
    expect(dts).toContain('Mã tài sản')
    expect(w.text()).toContain('AC-ASSET-2026-00042') // fallback name (invariant asset_code==name)
  })

  it('edge: manufacturer_sn rỗng → "Số serial NSX" hiển thị "—" (KHÔNG "undefined")', async () => {
    const w = await mountIdentity({ manufacturer_sn: '' })
    const snRow = w.findAll('dt').find((d) => d.text() === 'Số serial NSX')
    expect(snRow).toBeTruthy()
    const dd = snRow!.element.parentElement?.querySelector('dd')
    expect(dd?.textContent?.trim()).toBe('—')
    expect(w.text()).not.toContain('undefined')
  })
})
