// Copyright (c) 2026, AssetCore Team — AssetDetailView in nhãn QR 1 tài sản (A4/V5, TDD)
//
// RED-prove (task A4):
//   • bấm 'In nhãn QR' → getAssetLabelData(id) gọi ĐÚNG 1 lần (preview).
//   • preview mở mà CHƯA bấm 'In' → markLabelPrinted KHÔNG gọi (preview ≠ ghi event).
//   • bấm 'In' → window.print gọi + markLabelPrinted([id]) gọi ĐÚNG 1 lần.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

// ── Mock router ────────────────────────────────────────────────────────────────
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
}))

// ── Mock store (asset đã load) ───────────────────────────────────────────────────
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
// D6 (ADR-IMM00-QR-SCAN-ACTION, phương án B): nút 'In nhãn QR' gate asset.PRINT
// (quyền in nhãn — persona vận hành có; KHÔNG còn asset.write). `canCaps` set ngoài
// test để giả lập user-có-print / user-không-print.
const canCaps = new Set<string>(['asset.print'])
vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({
    can: (c: string | readonly string[]) =>
      Array.isArray(c) ? c.some((x) => canCaps.has(x)) : canCaps.has(c as string),
  }),
}))
vi.mock('@/composables/useNotify', () => ({ useNotify: () => ({ fromError: vi.fn(), success: vi.fn() }) }))
vi.mock('@/composables/useToast', () => ({ useToast: () => ({ show: vi.fn() }) }))

// ── Spy API ──────────────────────────────────────────────────────────────────────
const getLabelSpy = vi.fn()
const markPrintedSpy = vi.fn().mockResolvedValue({ printed: ['AC-ASSET-2026-00042'], event_count: 1 })
vi.mock('@/api/imm00', () => ({
  getAssetTimeline: vi.fn().mockResolvedValue({ items: [] }),
  getAssetKpi: vi.fn().mockResolvedValue(null),
  verifyChain: vi.fn().mockResolvedValue(null),
  deleteAsset: vi.fn(),
  getAssetLabelData: (id: string) => getLabelSpy(id),
  markLabelPrinted: (assets: string[]) => markPrintedSpy(assets),
}))
vi.mock('@/api/imm04', () => ({ getCommissioningOrigin: vi.fn().mockResolvedValue(null) }))
vi.mock('@/api/imm14', () => ({ createDecommission: vi.fn(), approveDecommission: vi.fn() }))
vi.mock('@/api/errors', () => ({ toApiError: (e: unknown) => e }))
vi.mock('qrcode', () => ({ default: { toDataURL: vi.fn().mockResolvedValue('data:image/png;base64,QR==') } }))

import AssetDetailView from './AssetDetailView.vue'

const VALID_LABEL = {
  name: 'AC-ASSET-2026-00042', asset_code: 'A-042',
  device_model_name: 'Dräger V500', location_name: 'ICU',
  lifecycle_status: 'Active', qr_url: 'http://miyano/a/tok42',
}

const stubs = {
  // BaseModal teleports to <body>; teleport:true render inline → wrapper queries reach it.
  PageHeader: true, teleport: true, SmartSelect: true,
  AssetDowntimeWidget: true, AssetDepreciationSchedule: true,
}

function findByText(w: ReturnType<typeof mount>, txt: string) {
  return w.findAll('button').find(b => b.text().includes(txt))
}

describe('AssetDetailView — in nhãn QR 1 tài sản (A4)', () => {
  beforeEach(() => {
    getLabelSpy.mockReset().mockResolvedValue(VALID_LABEL)
    markPrintedSpy.mockClear()
    vi.spyOn(window, 'print').mockImplementation(() => {})
    // mặc định: user CÓ asset.print cho happy-path bên dưới.
    canCaps.clear()
    canCaps.add('asset.print')
  })

  it("D6 — user KHÔNG có asset.print (chỉ read) → nút 'In nhãn QR' KHÔNG render", async () => {
    canCaps.clear()
    canCaps.add('asset.read') // chỉ đọc, KHÔNG print
    const w = mount(AssetDetailView, { props: { id: 'AC-ASSET-2026-00042' }, global: { stubs } })
    await flushPromises()
    expect(findByText(w, 'In nhãn QR')).toBeFalsy()
  })

  it("D6 — user CÓ asset.print → nút 'In nhãn QR' render", async () => {
    canCaps.clear()
    canCaps.add('asset.print')
    const w = mount(AssetDetailView, { props: { id: 'AC-ASSET-2026-00042' }, global: { stubs } })
    await flushPromises()
    expect(findByText(w, 'In nhãn QR')).toBeTruthy()
  })

  it("bấm 'In nhãn QR' → getAssetLabelData(id) gọi ĐÚNG 1 lần; markLabelPrinted CHƯA gọi", async () => {
    const w = mount(AssetDetailView, { props: { id: 'AC-ASSET-2026-00042' }, global: { stubs } })
    await flushPromises()
    const btn = findByText(w, 'In nhãn QR')
    expect(btn).toBeTruthy()
    await btn!.trigger('click')
    await flushPromises()
    expect(getLabelSpy).toHaveBeenCalledTimes(1)
    expect(getLabelSpy).toHaveBeenCalledWith('AC-ASSET-2026-00042')
    // Preview-only — CHƯA ghi event.
    expect(markPrintedSpy).not.toHaveBeenCalled()
  })

  it("bấm 'In' (xác nhận) → window.print + markLabelPrinted([id]) ĐÚNG 1 lần", async () => {
    const w = mount(AssetDetailView, { props: { id: 'AC-ASSET-2026-00042' }, global: { stubs } })
    await flushPromises()
    await findByText(w, 'In nhãn QR')!.trigger('click')
    await flushPromises()
    const printBtn = findByText(w, 'In tem')
    expect(printBtn).toBeTruthy()
    await printBtn!.trigger('click')
    await flushPromises()
    expect(window.print).toHaveBeenCalled()
    expect(markPrintedSpy).toHaveBeenCalledTimes(1)
    expect(markPrintedSpy).toHaveBeenCalledWith(['AC-ASSET-2026-00042'])
  })

  // ── B (print fidelity): selector khổ tem trong modal in-1-tem ───────────────
  it("modal có selector khổ tem (A4 / 50×30 / 70×40); mặc định A4 → KHÔNG ép @page", async () => {
    const w = mount(AssetDetailView, { props: { id: 'AC-ASSET-2026-00042' }, global: { stubs } })
    await flushPromises()
    await findByText(w, 'In nhãn QR')!.trigger('click')
    await flushPromises()
    const sel = w.find('select[aria-label="Chọn khổ tem in nhãn"]')
    expect(sel.exists()).toBe(true)
    expect(sel.findAll('option').map(o => o.text())).toEqual(
      ['A4 nhiều-nhãn', 'Tem 50×30mm', 'Tem 70×40mm'],
    )
    // Mặc định A4 → KHÔNG inject @page tem.
    expect(w.find('[data-testid="label-page-rule"]').exists()).toBe(false)
  })

  it("modal chọn 'tem-50x30' → @page size '50mm 30mm' + sheet 1-tem; In tem vẫn markLabelPrinted 1 lần", async () => {
    const w = mount(AssetDetailView, { props: { id: 'AC-ASSET-2026-00042' }, global: { stubs } })
    await flushPromises()
    await findByText(w, 'In nhãn QR')!.trigger('click')
    await flushPromises()
    const sel = w.find('select[aria-label="Chọn khổ tem in nhãn"]')
    await sel.setValue('tem-50x30')
    await flushPromises()
    const pageRule = w.find('[data-testid="label-page-rule"]')
    expect(pageRule.exists()).toBe(true)
    expect(pageRule.text()).toContain('size: 50mm 30mm')
    expect(w.find('.qr-label-sheet--tem-50x30').exists()).toBe(true)
    // In tem vẫn ghi event đúng 1 lần sau window.print (regression).
    await findByText(w, 'In tem')!.trigger('click')
    await flushPromises()
    expect(window.print).toHaveBeenCalled()
    expect(markPrintedSpy).toHaveBeenCalledTimes(1)
    expect(markPrintedSpy).toHaveBeenCalledWith(['AC-ASSET-2026-00042'])
  })

  it("modal chọn 'tem-70x40' → @page size '70mm 40mm'", async () => {
    const w = mount(AssetDetailView, { props: { id: 'AC-ASSET-2026-00042' }, global: { stubs } })
    await flushPromises()
    await findByText(w, 'In nhãn QR')!.trigger('click')
    await flushPromises()
    await w.find('select[aria-label="Chọn khổ tem in nhãn"]').setValue('tem-70x40')
    await flushPromises()
    const pageRule = w.find('[data-testid="label-page-rule"]')
    expect(pageRule.exists()).toBe(true)
    expect(pageRule.text()).toContain('size: 70mm 40mm')
  })
})
