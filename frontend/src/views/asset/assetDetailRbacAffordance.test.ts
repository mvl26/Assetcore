// Copyright (c) 2026, AssetCore Team — AssetDetailView siết affordance ghi theo capability (B, TDD)
//
// RED-prove (task B — vá UX-leak, defense vẫn ở BE):
//   INVARIANT 1 view: 5 nhóm affordance GHI (Chỉnh sửa, Xóa, In nhãn QR, Sinh lại mã QR,
//   Transition →state) ĐỀU capability-gated — KHÔNG nút nào chỉ gate `store.currentAsset`.
//   • read-only {asset.read} → KHÔNG render bất kỳ nhóm ghi nào (kể cả label "Chuyển trạng thái:").
//   • full {write+delete} + status có TRANSITIONS → render đủ 5 nhóm.
//   • split {write, !delete} → THẤY Sửa/transition/QR, KHÔNG thấy Xóa (delete tách khỏi write).
//   • write + status TRANSITIONS rỗng (Decommissioned) → KHÔNG render khối transition
//     (gate write KHÔNG phá điều kiện length sẵn có).
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

// ── Mock router ────────────────────────────────────────────────────────────────
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
}))

// ── Mock store (asset đã load) — lifecycle_status thay đổi per-test qua mutate ───────
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
vi.mock('@/stores/auth', () => ({ useAuthStore: () => ({ user: 'tester' }) }))

// B: capability set giả lập per-test (write / delete / read-only).
const canCaps = new Set<string>()
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

// PageHeader render-stub: PASS-THROUGH #actions slot (nút Sửa/Xóa nằm trong slot này).
// Stub `true` sẽ NUỐT slot → không assert được; nên dùng template render slot.
const stubs = {
  PageHeader: { template: '<div><slot name="actions" /></div>' },
  teleport: true, SmartSelect: true,
  AssetDowntimeWidget: true, AssetDepreciationSchedule: true,
}

function findBtn(w: ReturnType<typeof mount>, txt: string) {
  return w.findAll('button').find(b => b.text().includes(txt))
}

describe('AssetDetailView — siết affordance ghi theo capability (B)', () => {
  beforeEach(() => {
    canCaps.clear()
    currentAsset.lifecycle_status = 'Active'
  })

  it('RED — read-only {asset.read} → KHÔNG render 5 nhóm nút ghi + KHÔNG khối "Chuyển trạng thái:"', async () => {
    canCaps.add('asset.read') // chỉ đọc, KHÔNG write/delete
    const w = mount(AssetDetailView, { props: { id: 'AC-ASSET-2026-00042' }, global: { stubs } })
    await flushPromises()
    // 5 nhóm affordance ghi đều ẩn.
    expect(findBtn(w, 'Chỉnh sửa')).toBeFalsy()
    expect(findBtn(w, 'Xóa')).toBeFalsy()
    expect(findBtn(w, 'In nhãn QR')).toBeFalsy()
    expect(findBtn(w, 'Sinh lại mã QR')).toBeFalsy()
    // Khối transition (label + các nút →state) ẩn hoàn toàn.
    expect(w.text()).not.toContain('Chuyển trạng thái:')
    expect(w.findAll('button').filter(b => b.text().startsWith('→')).length).toBe(0)
    // Vẫn THẤY thông tin thiết bị (read OK).
    expect(w.text()).toContain('Máy thở Dräger')
  })

  it('full {write+delete+print+rotate} + status có TRANSITIONS → render đủ 5 nhóm (≥1 nút →state)', async () => {
    // D6: In nhãn gate asset.print, Sinh-lại QR gate asset.qr.rotate (tách khỏi write).
    canCaps.add('asset.read'); canCaps.add('asset.write'); canCaps.add('asset.delete')
    canCaps.add('asset.print'); canCaps.add('asset.qr.rotate')
    const w = mount(AssetDetailView, { props: { id: 'AC-ASSET-2026-00042' }, global: { stubs } })
    await flushPromises()
    expect(findBtn(w, 'Chỉnh sửa')).toBeTruthy()
    expect(findBtn(w, 'Xóa')).toBeTruthy()
    expect(findBtn(w, 'In nhãn QR')).toBeTruthy()
    expect(findBtn(w, 'Sinh lại mã QR')).toBeTruthy()
    expect(w.text()).toContain('Chuyển trạng thái:')
    expect(w.findAll('button').filter(b => b.text().startsWith('→')).length).toBeGreaterThanOrEqual(1)
  })

  it('D6 split {print, !rotate, !write} → THẤY In nhãn, KHÔNG thấy Sửa/Sinh-lại QR', async () => {
    // Persona vận hành (KTV): chỉ print → in được NHƯNG KHÔNG sửa/rotate (least-privilege).
    canCaps.add('asset.read'); canCaps.add('asset.print') // KHÔNG write/rotate/delete
    const w = mount(AssetDetailView, { props: { id: 'AC-ASSET-2026-00042' }, global: { stubs } })
    await flushPromises()
    expect(findBtn(w, 'In nhãn QR')).toBeTruthy()
    expect(findBtn(w, 'Sinh lại mã QR')).toBeFalsy()
    expect(findBtn(w, 'Chỉnh sửa')).toBeFalsy()
    expect(findBtn(w, 'Xóa')).toBeFalsy()
  })

  it('split {write, !delete} → THẤY Sửa/transition, KHÔNG thấy Xóa (delete tách khỏi write)', async () => {
    canCaps.add('asset.read'); canCaps.add('asset.write') // KHÔNG delete/print/rotate
    const w = mount(AssetDetailView, { props: { id: 'AC-ASSET-2026-00042' }, global: { stubs } })
    await flushPromises()
    expect(findBtn(w, 'Chỉnh sửa')).toBeTruthy()
    // D6: In nhãn/Sinh-lại QR KHÔNG còn theo write (gate riêng print/rotate).
    expect(findBtn(w, 'In nhãn QR')).toBeFalsy()
    expect(findBtn(w, 'Sinh lại mã QR')).toBeFalsy()
    expect(w.findAll('button').filter(b => b.text().startsWith('→')).length).toBeGreaterThanOrEqual(1)
    // asset.delete=False → nút Xóa ẩn dù được write.
    expect(findBtn(w, 'Xóa')).toBeFalsy()
  })

  it('write=true + TRANSITIONS rỗng (Decommissioned) → KHÔNG render khối transition (length gate giữ nguyên)', async () => {
    canCaps.add('asset.read'); canCaps.add('asset.write')
    currentAsset.lifecycle_status = 'Decommissioned' // TRANSITIONS['Decommissioned'] = []
    const w = mount(AssetDetailView, { props: { id: 'AC-ASSET-2026-00042' }, global: { stubs } })
    await flushPromises()
    expect(w.text()).not.toContain('Chuyển trạng thái:')
    expect(w.findAll('button').filter(b => b.text().startsWith('→')).length).toBe(0)
    // write user vẫn thấy nút Sửa (chứng minh gate write không phá length-gate của transition).
    expect(findBtn(w, 'Chỉnh sửa')).toBeTruthy()
  })
})
