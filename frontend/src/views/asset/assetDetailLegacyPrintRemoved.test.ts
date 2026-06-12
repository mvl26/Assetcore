// Copyright (c) 2026, AssetCore Team — AssetDetailView legacy HTML-print REMOVED (TDD, Vòng 24)
//
// Đề mục Vòng 24 / IMM-00 label-pdf: KHAI TỬ đường in nhãn cũ window.print() HTML ở
// AssetDetailView — chỉ còn DUY NHẤT 1 lối in = đường PDF khổ tem (openPdfLabelPrint).
// Test này viết TRƯỚC (TDD) để KHOÁ việc gỡ legacy:
//   • Persona có asset.print → KHÔNG còn nút 'In tem' legacy.
//   • KHÔNG còn data-testid=label-page-rule trong DOM (chỉ-legacy ở view này).
//   • Không có opener top-level nào mở modal legacy (showLabelModal không bật được qua UI).
//   • Spy window.print → đi trọn đường PDF ('In nhãn QR' → 'Đã in xong') → window.print
//     KHÔNG được gọi (đường PDF dùng iframe.print qua composable, KHÔNG window.print legacy).
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

vi.mock('vue-router', () => ({ useRouter: () => ({ push: vi.fn() }) }))

const currentAsset = {
  name: 'AC-ASSET-2026-00042', asset_name: 'Máy thở Dräger',
  lifecycle_status: 'Active', risk_classification: 'Low',
}
vi.mock('@/stores/imm00', () => ({
  useAssetStore: () => ({
    currentAsset, loading: false, error: null,
    fetchOne: vi.fn().mockResolvedValue(undefined),
    transition: vi.fn(),
  }),
}))
vi.mock('@/stores/auth', () => ({ useAuthStore: () => ({ user: 'tester' }) }))

// Persona có asset.print (đủ điều kiện hiện đường in) — chứng minh legacy đã biến mất
// KHÔNG phải vì thiếu quyền, mà vì code không còn entry-point legacy.
const canCaps = new Set<string>(['asset.print'])
vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({
    can: (c: string | readonly string[]) =>
      Array.isArray(c) ? c.some((x) => canCaps.has(x)) : canCaps.has(c as string),
  }),
}))
vi.mock('@/composables/useNotify', () => ({ useNotify: () => ({ fromError: vi.fn(), success: vi.fn() }) }))
vi.mock('@/composables/useToast', () => ({ useToast: () => ({ show: vi.fn(), success: vi.fn() }) }))

const markPrintedSpy = vi.fn().mockResolvedValue({ printed: ['AC-ASSET-2026-00042'], event_count: 1 })
vi.mock('@/api/imm00', () => ({
  getAssetTimeline: vi.fn().mockResolvedValue({ items: [] }),
  getAssetKpi: vi.fn().mockResolvedValue(null),
  verifyChain: vi.fn().mockResolvedValue(null),
  deleteAsset: vi.fn(),
  markLabelPrinted: (assets: string[]) => markPrintedSpy(assets),
  printAssetLabelsPdf: vi.fn(),
  regenerateAssetQrToken: vi.fn(),
  LABEL_PDF_PRESETS: [
    { key: 'tem-60x100', label: 'Tem 60×100mm' },
    { key: 'tem-70x40', label: 'Tem 70×40mm' },
    { key: 'tem-50x30', label: 'Tem 50×30mm' },
  ],
  LABEL_PDF_PRESET: 'tem-60x100',
  labelPdfPresetLabel: (preset: string) =>
    ({ 'tem-60x100': 'Tem 60×100mm', 'tem-70x40': 'Tem 70×40mm', 'tem-50x30': 'Tem 50×30mm' } as Record<string, string>)[preset] ?? '',
}))
vi.mock('@/api/imm04', () => ({ getCommissioningOrigin: vi.fn().mockResolvedValue(null) }))
vi.mock('@/api/imm14', () => ({ createDecommission: vi.fn(), approveDecommission: vi.fn() }))
vi.mock('@/api/errors', () => ({ toApiError: (e: unknown) => e }))
vi.mock('qrcode', () => ({ default: { toDataURL: vi.fn().mockResolvedValue('data:image/png;base64,QR==') } }))

// Composable PDF — giả lập tải Blob OK (set previewUrl), giữ onAfterPrint để bắn thủ công.
const printLabelsSpy = vi.fn()
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
    previewUrl, printing, error: pdfError, revoke: vi.fn(),
  }),
}))

import AssetDetailView from './AssetDetailView.vue'

const stubs = { PageHeader: true, teleport: true, SmartSelect: true,
  AssetDowntimeWidget: true, AssetDepreciationSchedule: true, BaseModal: false }

function findByText(w: ReturnType<typeof mount>, txt: string) {
  return w.findAll('button').find(b => b.text().trim() === txt)
}

describe('AssetDetailView — đường in nhãn HTML legacy ĐÃ BỊ GỠ (chỉ còn PDF)', () => {
  beforeEach(() => {
    printLabelsSpy.mockReset().mockResolvedValue(new Blob(['%PDF'], { type: 'application/pdf' }))
    markPrintedSpy.mockClear().mockResolvedValue({ printed: ['AC-ASSET-2026-00042'], event_count: 1 })
    previewUrl.value = null
    printing.value = false
    pdfError.value = null
    capturedOnAfterPrint = undefined
    canCaps.clear()
    canCaps.add('asset.print')
  })

  it("persona có asset.print → KHÔNG còn nút 'In tem' legacy", async () => {
    const w = mount(AssetDetailView, { props: { id: 'AC-ASSET-2026-00042' }, global: { stubs } })
    await flushPromises()
    // Nút legacy 'In tem' (confirmPrintLabel) đã xoá — chỉ còn 'In nhãn QR' (đường PDF).
    expect(findByText(w, 'In tem')).toBeFalsy()
    expect(w.findAll('button').find(b => b.text().includes('In nhãn QR'))).toBeTruthy()
  })

  it('KHÔNG còn data-testid=label-page-rule (CSS @page chỉ-legacy) trong DOM', async () => {
    const w = mount(AssetDetailView, { props: { id: 'AC-ASSET-2026-00042' }, global: { stubs } })
    await flushPromises()
    expect(w.find('[data-testid="label-page-rule"]').exists()).toBe(false)
  })

  it('KHÔNG có opener top-level nào mở modal legacy (qr-modal-chrome không render)', async () => {
    const w = mount(AssetDetailView, { props: { id: 'AC-ASSET-2026-00042' }, global: { stubs } })
    await flushPromises()
    // Bấm mọi nút khả kiến (trừ đường PDF/regen/decom) — không nút nào dựng modal legacy.
    expect(w.find('.qr-modal-chrome').exists()).toBe(false)
    // Cũng không có preview-sheet legacy 1-tem.
    expect(w.find('.qr-label-sheet').exists()).toBe(false)
    // Tiêu đề modal legacy 'Nhãn QR thiết bị' không tồn tại.
    expect(w.html()).not.toContain('Nhãn QR thiết bị')
  })

  it("đi trọn đường PDF ('In nhãn QR' → 'Đã in xong') → window.print KHÔNG được gọi", async () => {
    const printSpy = vi.spyOn(window, 'print').mockImplementation(() => {})
    const w = mount(AssetDetailView, { props: { id: 'AC-ASSET-2026-00042' }, global: { stubs } })
    await flushPromises()
    const open = w.findAll('button').find(b => b.text().includes('In nhãn QR'))
    expect(open).toBeTruthy()
    await open!.trigger('click')
    await flushPromises()
    const done = w.find('[data-testid="btn-pdf-printed"]')
    expect(done.exists()).toBe(true)
    await done.trigger('click')
    await flushPromises()
    // Đường PDF dùng iframe.print qua composable → window.print legacy KHÔNG được gọi.
    expect(printSpy).not.toHaveBeenCalled()
    // Ghi audit đi qua đường PDF (markLabelPrinted) — chứng minh đường in DUY NHẤT hoạt động.
    expect(markPrintedSpy).toHaveBeenCalledTimes(1)
    expect(markPrintedSpy).toHaveBeenCalledWith(['AC-ASSET-2026-00042'])
  })

  it('onafterprint (đường PDF) cũng KHÔNG gọi window.print legacy', async () => {
    const printSpy = vi.spyOn(window, 'print').mockImplementation(() => {})
    const w = mount(AssetDetailView, { props: { id: 'AC-ASSET-2026-00042' }, global: { stubs } })
    await flushPromises()
    const open = w.findAll('button').find(b => b.text().includes('In nhãn QR'))
    await open!.trigger('click')
    await flushPromises()
    expect(capturedOnAfterPrint).toBeTruthy()
    await capturedOnAfterPrint!(['AC-ASSET-2026-00042'])
    await flushPromises()
    expect(printSpy).not.toHaveBeenCalled()
    expect(markPrintedSpy).toHaveBeenCalledTimes(1)
  })
})

// ── Source-level guard (TDD red→green) ────────────────────────────────────────────
// DOM-test không đủ: modal legacy là v-if="showLabelModal" (mặc định false) → trang
// đã không render nó dù code còn. Để KHOÁ việc gỡ THẬT, grep nguồn SFC: không còn
// symbol/entry-point legacy nào. KHÔNG dùng window.print( legacy; markLabelPrinted GIỮ
// (đường PDF markPrintedOnce dùng) nên KHÔNG ban — chỉ ban các symbol chỉ-legacy.
describe('AssetDetailView.vue (nguồn) — đã xoá hết symbol đường in HTML legacy', () => {
  // process.cwd() = frontend/ khi chạy vitest → resolve tới SFC nguồn.
  const src = readFileSync(
    resolve(process.cwd(), 'src/views/asset/AssetDetailView.vue'), 'utf8',
  )

  it.each([
    ['window.print('],         // đường in legacy (PDF dùng iframe.print qua composable)
    ['showLabelModal'],        // state modal legacy
    ['openLabelPreview'],      // opener legacy
    ['confirmPrintLabel'],     // ghi audit qua bản in sai khổ (đường thứ 2 — phải biến mất)
    ['label-page-rule'],       // <style data-testid> chỉ-legacy
    ['qr-modal-chrome'],       // CSS chrome modal legacy
    ['In tem'],                // nhãn nút legacy (đường in sai khổ)
  ])('KHÔNG còn chuỗi legacy "%s" trong AssetDetailView.vue', (needle) => {
    expect(src).not.toContain(needle)
  })

  it("GIỮ markLabelPrinted (đường PDF markPrintedOnce vẫn dùng) + nút 'In nhãn QR' (lối in DUY NHẤT)", () => {
    expect(src).toContain('markLabelPrinted')
    expect(src).toContain('openPdfLabelPrint')
    expect(src).toContain('In nhãn QR')
  })
})
