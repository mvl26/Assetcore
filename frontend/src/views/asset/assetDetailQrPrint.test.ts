// Copyright (c) 2026, AssetCore Team — AssetDetailView in nhãn QR PDF 60×100mm (TDD)
//
// Luồng PDF (ADR-IMM00-LABEL-PDF — phương án A): nút 'In nhãn QR' → openPdfLabelPrint
// → printAssetLabelsPdf([id]) ĐÚNG 1 lần (KHÔNG window.print legacy) → preview modal
// embed PDF Blob → iframe.print(). markLabelPrinted([id]) CHỈ gọi qua 'Đã in xong' /
// onafterprint — KHÔNG gọi khi chỉ mở-rồi-huỷ. Gate can('asset.print').
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'

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
// D6: nút 'In nhãn QR' gate asset.PRINT. canCaps set ngoài test để giả lập persona.
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
const printPdfSpy = vi.fn()
const markPrintedSpy = vi.fn().mockResolvedValue({ printed: ['AC-ASSET-2026-00042'], event_count: 1 })
vi.mock('@/api/imm00', () => ({
  getAssetTimeline: vi.fn().mockResolvedValue({ items: [] }),
  getAssetKpi: vi.fn().mockResolvedValue(null),
  verifyChain: vi.fn().mockResolvedValue(null),
  deleteAsset: vi.fn(),
  getAssetLabelData: vi.fn().mockResolvedValue(null),
  markLabelPrinted: (assets: string[]) => markPrintedSpy(assets),
  printAssetLabelsPdf: (names: string[]) => printPdfSpy(names),
}))
vi.mock('@/api/imm04', () => ({ getCommissioningOrigin: vi.fn().mockResolvedValue(null) }))
vi.mock('@/api/imm14', () => ({ createDecommission: vi.fn(), approveDecommission: vi.fn() }))
vi.mock('@/api/errors', () => ({ toApiError: (e: unknown) => e }))
vi.mock('qrcode', () => ({ default: { toDataURL: vi.fn().mockResolvedValue('data:image/png;base64,QR==') } }))

// ── Mock composable usePdfLabelPrint ────────────────────────────────────────────
// printLabels(names, opts) → giả lập tải PDF thành công (set previewUrl), GIỮ
// opts.onAfterPrint để test trigger onafterprint thủ công.
const printLabelsSpy = vi.fn()
const revokeSpy = vi.fn()
const previewUrl = ref<string | null>(null)
const printing = ref(false)
const pdfError = ref<unknown>(null)
let capturedOnAfterPrint: ((names: string[]) => void | Promise<void>) | undefined
vi.mock('@/composables/usePdfLabelPrint', () => ({
  usePdfLabelPrint: () => ({
    printLabels: (names: string[], opts: { onAfterPrint?: (n: string[]) => void } = {}) => {
      capturedOnAfterPrint = opts.onAfterPrint
      previewUrl.value = 'blob:mock-pdf'
      return printLabelsSpy(names, opts)
    },
    previewUrl, printing, error: pdfError, revoke: revokeSpy,
  }),
}))

import AssetDetailView from './AssetDetailView.vue'

const stubs = { PageHeader: true, teleport: true, SmartSelect: true,
  AssetDowntimeWidget: true, AssetDepreciationSchedule: true, BaseModal: false }

function findByText(w: ReturnType<typeof mount>, txt: string) {
  return w.findAll('button').find(b => b.text().includes(txt))
}

describe('AssetDetailView — in nhãn QR PDF 60×100mm', () => {
  beforeEach(() => {
    printPdfSpy.mockReset().mockResolvedValue(new Blob(['%PDF'], { type: 'application/pdf' }))
    printLabelsSpy.mockReset().mockResolvedValue(new Blob(['%PDF'], { type: 'application/pdf' }))
    markPrintedSpy.mockClear().mockResolvedValue({ printed: ['AC-ASSET-2026-00042'], event_count: 1 })
    revokeSpy.mockClear()
    previewUrl.value = null
    printing.value = false
    pdfError.value = null
    capturedOnAfterPrint = undefined
    canCaps.clear()
    canCaps.add('asset.print')
  })

  it("user KHÔNG có asset.print → nút 'In nhãn QR' KHÔNG render", async () => {
    canCaps.clear()
    canCaps.add('asset.read')
    const w = mount(AssetDetailView, { props: { id: 'AC-ASSET-2026-00042' }, global: { stubs } })
    await flushPromises()
    expect(findByText(w, 'In nhãn QR')).toBeFalsy()
  })

  it("user CÓ asset.print → nút 'In nhãn QR' render", async () => {
    const w = mount(AssetDetailView, { props: { id: 'AC-ASSET-2026-00042' }, global: { stubs } })
    await flushPromises()
    expect(findByText(w, 'In nhãn QR')).toBeTruthy()
  })

  it("bấm 'In nhãn QR' → printLabels([id]) ĐÚNG 1 lần; markLabelPrinted CHƯA gọi (mở ≠ in)", async () => {
    const w = mount(AssetDetailView, { props: { id: 'AC-ASSET-2026-00042' }, global: { stubs } })
    await flushPromises()
    await findByText(w, 'In nhãn QR')!.trigger('click')
    await flushPromises()
    expect(printLabelsSpy).toHaveBeenCalledTimes(1)
    expect(printLabelsSpy.mock.calls[0][0]).toEqual(['AC-ASSET-2026-00042'])
    // Mở-rồi-chưa-in → KHÔNG ghi audit.
    expect(markPrintedSpy).not.toHaveBeenCalled()
  })

  it("bấm 'Đã in xong' → markLabelPrinted([id]) ĐÚNG 1 lần", async () => {
    const w = mount(AssetDetailView, { props: { id: 'AC-ASSET-2026-00042' }, global: { stubs } })
    await flushPromises()
    await findByText(w, 'In nhãn QR')!.trigger('click')
    await flushPromises()
    const doneBtn = w.find('[data-testid="btn-pdf-printed"]')
    expect(doneBtn.exists()).toBe(true)
    await doneBtn.trigger('click')
    await flushPromises()
    expect(markPrintedSpy).toHaveBeenCalledTimes(1)
    expect(markPrintedSpy).toHaveBeenCalledWith(['AC-ASSET-2026-00042'])
  })

  it("onafterprint → markLabelPrinted([id]) (đường bổ trợ); KHÔNG double-ghi với 'Đã in xong'", async () => {
    const w = mount(AssetDetailView, { props: { id: 'AC-ASSET-2026-00042' }, global: { stubs } })
    await flushPromises()
    await findByText(w, 'In nhãn QR')!.trigger('click')
    await flushPromises()
    // Trigger onafterprint do view truyền vào composable.
    expect(capturedOnAfterPrint).toBeTruthy()
    await capturedOnAfterPrint!(['AC-ASSET-2026-00042'])
    await flushPromises()
    expect(markPrintedSpy).toHaveBeenCalledTimes(1)
    // 'Đã in xong' sau đó → KHÔNG double-ghi (idempotent labelMarked).
    const doneBtn = w.find('[data-testid="btn-pdf-printed"]')
    await doneBtn.trigger('click')
    await flushPromises()
    expect(markPrintedSpy).toHaveBeenCalledTimes(1)
  })

  it("đóng modal (huỷ) → revoke gọi + KHÔNG ghi audit", async () => {
    const w = mount(AssetDetailView, { props: { id: 'AC-ASSET-2026-00042' }, global: { stubs } })
    await flushPromises()
    await findByText(w, 'In nhãn QR')!.trigger('click')
    await flushPromises()
    const closeBtn = w.findAll('button').find(b => b.text().trim() === 'Đóng')
    expect(closeBtn).toBeTruthy()
    await closeBtn!.trigger('click')
    await flushPromises()
    expect(revokeSpy).toHaveBeenCalled()
    expect(markPrintedSpy).not.toHaveBeenCalled()
  })

  it("preview modal embed CHÍNH PDF Blob URL (iframe src=previewUrl)", async () => {
    const w = mount(AssetDetailView, { props: { id: 'AC-ASSET-2026-00042' }, global: { stubs } })
    await flushPromises()
    await findByText(w, 'In nhãn QR')!.trigger('click')
    await flushPromises()
    const iframe = w.find('[data-testid="pdf-preview-iframe"]')
    expect(iframe.exists()).toBe(true)
    expect(iframe.attributes('src')).toBe('blob:mock-pdf')
  })

  it("KHÔNG dùng window.print legacy cho đường PDF", async () => {
    const printSpy = vi.spyOn(window, 'print').mockImplementation(() => {})
    const w = mount(AssetDetailView, { props: { id: 'AC-ASSET-2026-00042' }, global: { stubs } })
    await flushPromises()
    await findByText(w, 'In nhãn QR')!.trigger('click')
    await flushPromises()
    expect(printSpy).not.toHaveBeenCalled()
  })
})
