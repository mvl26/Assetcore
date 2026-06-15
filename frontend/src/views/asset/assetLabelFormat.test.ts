// Copyright (c) 2026, AssetCore Team — Khổ tem in nhãn QR (print fidelity, roadmap B, TDD)
//
// Acceptance (roadmap B):
//   • selector khổ tem ở CẢ 2 đường in (batch + modal 1-tem).
//   • 'tem-50x30' → @page size '50mm 30mm' + 1 cột/1 nhãn-mỗi-trang.
//   • 'tem-70x40' → @page size '70mm 40mm'.
//   • mặc định / 'a4-multi' → KHÔNG ép @page tem, giữ lưới 2 cột A4 (regression).
//   • AssetQrLabel: prop qrSize/khổ tem → QR + field scale (tem KHÔNG dùng 120px cố định).
//   • Regression: error-bucket VI cố định + markLabelPrinted chỉ name hợp lệ vẫn nguyên.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises, config } from '@vue/test-utils'
import { ref } from 'vue'

// BaseModal teleports tới <body>; render inline để wrapper.find reach modal PDF.
config.global.stubs = { teleport: true }

// ── AssetLabelPrintView (batch) ───────────────────────────────────────────────
const routeQuery = ref<Record<string, string | string[]>>({ names: 'A1,A2,A3' })
const pushSpy = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: pushSpy }),
  useRoute: () => ({ get query() { return routeQuery.value } }),
}))
const getBatchSpy = vi.fn()
const markPrintedSpy = vi.fn().mockResolvedValue({ printed: [], event_count: 0 })
const printPdfSpy = vi.fn()
vi.mock('@/api/imm00', () => ({
  getAssetLabelDataBatch: (names: string[]) => getBatchSpy(names),
  getAssetLabelData: vi.fn(),
  markLabelPrinted: (assets: string[]) => markPrintedSpy(assets),
  printAssetLabelsPdf: (names: string[], preset?: string) => printPdfSpy(names, preset),
  // SSoT preset khổ tem — AssetLabelPrintView import ở module-level.
  LABEL_PDF_PRESETS: [
    { key: 'tem-60x100', label: 'Tem 60×100mm' },
    { key: 'tem-70x40', label: 'Tem 70×40mm' },
    { key: 'tem-50x30', label: 'Tem 50×30mm' },
  ],
  LABEL_PDF_PRESET: 'tem-60x100',
  labelPdfPresetLabel: (p: string) =>
    ({ 'tem-60x100': 'Tem 60×100mm', 'tem-70x40': 'Tem 70×40mm', 'tem-50x30': 'Tem 50×30mm' } as Record<string, string>)[p] ?? '',
}))
vi.mock('qrcode', () => ({ default: { toDataURL: vi.fn().mockResolvedValue('data:image/png;base64,QR==') } }))

// Mock composable usePdfLabelPrint (DRY iframe in PDF) — giả lập tải Blob OK.
const printLabelsSpy = vi.fn()
const pdfPreviewUrl = ref<string | null>(null)
const pdfPrinting = ref(false)
const pdfErrorRef = ref<unknown>(null)
vi.mock('@/composables/usePdfLabelPrint', () => ({
  usePdfLabelPrint: () => ({
    printLabels: (names: string[], opts: { onAfterPrint?: (n: string[]) => void } = {}) => {
      pdfPreviewUrl.value = 'blob:mock-pdf'
      return printLabelsSpy(names, opts)
    },
    previewUrl: pdfPreviewUrl, printing: pdfPrinting, error: pdfErrorRef, revoke: vi.fn(),
  }),
}))

import AssetLabelPrintView from './AssetLabelPrintView.vue'
import AssetQrLabel from '@/components/asset/AssetQrLabel.vue'
import { getLabelFormat } from '@/constants/label'

function lbl(name: string) {
  return { name, asset_code: name, device_model_name: 'M', location_name: 'L', lifecycle_status: 'Active', qr_url: `http://miyano/a/${name}` }
}

async function selectFormat(w: ReturnType<typeof mount>, key: string) {
  const sel = w.find('select[aria-label="Chọn khổ tem in nhãn"]')
  expect(sel.exists()).toBe(true)
  await sel.setValue(key)
  await flushPromises()
}

describe('AssetLabelPrintView — selector khổ tem (batch)', () => {
  beforeEach(() => {
    getBatchSpy.mockReset().mockResolvedValue([lbl('A1'), lbl('A2'), lbl('A3')])
    markPrintedSpy.mockClear()
    printPdfSpy.mockReset().mockResolvedValue(new Blob(['%PDF'], { type: 'application/pdf' }))
    printLabelsSpy.mockReset().mockResolvedValue(new Blob(['%PDF'], { type: 'application/pdf' }))
    pdfPreviewUrl.value = null
    pdfPrinting.value = false
    pdfErrorRef.value = null
    pushSpy.mockClear()
    routeQuery.value = { names: 'A1,A2,A3' }
    vi.spyOn(window, 'print').mockImplementation(() => {})
  })

  it("có selector khổ tem = 3 preset PDF SSoT (60×100 / 70×40 / 50×30)", async () => {
    const w = mount(AssetLabelPrintView)
    await flushPromises()
    const sel = w.find('select[aria-label="Chọn khổ tem in nhãn"]')
    expect(sel.exists()).toBe(true)
    const opts = sel.findAll('option')
    // SSoT LABEL_PDF_PRESETS — value khớp key BE, nhãn VI.
    expect(opts.map(o => o.attributes('value'))).toEqual(['tem-60x100', 'tem-70x40', 'tem-50x30'])
    expect(opts.map(o => o.text())).toEqual(['Tem 60×100mm', 'Tem 70×40mm', 'Tem 50×30mm'])
    // Default = tem-60x100 (parity AssetDetailView).
    expect((sel.element as HTMLSelectElement).value).toBe('tem-60x100')
    // Badge tĩnh phản ánh khổ mặc định.
    expect(w.find('[data-testid="label-preset-badge"]').text()).toContain('Tem 60×100mm')
  })

  it("chọn 'tem-50x30' → @page size '50mm 30mm' được inject + sheet 1-nhãn class", async () => {
    const w = mount(AssetLabelPrintView)
    await flushPromises()
    await selectFormat(w, 'tem-50x30')
    const pageRule = w.find('[data-testid="label-page-rule"]')
    expect(pageRule.exists()).toBe(true)
    expect(pageRule.text()).toContain('size: 50mm 30mm')
    // Sheet mang class khổ tem 50x30 (CSS in → 1 nhãn/trang).
    expect(w.find('.qr-label-sheet--tem-50x30').exists()).toBe(true)
  })

  it("chọn 'tem-70x40' → @page size '70mm 40mm'", async () => {
    const w = mount(AssetLabelPrintView)
    await flushPromises()
    await selectFormat(w, 'tem-70x40')
    const pageRule = w.find('[data-testid="label-page-rule"]')
    expect(pageRule.exists()).toBe(true)
    expect(pageRule.text()).toContain('size: 70mm 40mm')
    expect(w.find('.qr-label-sheet--tem-70x40').exists()).toBe(true)
  })

  it("đổi khổ tem (50×30 → 70×40) → @page size + sheet class cập nhật theo preset đang chọn", async () => {
    const w = mount(AssetLabelPrintView)
    await flushPromises()
    await selectFormat(w, 'tem-50x30')
    expect(w.find('[data-testid="label-page-rule"]').text()).toContain('size: 50mm 30mm')
    expect(w.find('.qr-label-sheet--tem-50x30').exists()).toBe(true)
    // Đổi sang 70×40 → @page + sheet class theo khổ mới (không còn ép cứng khổ cũ).
    await selectFormat(w, 'tem-70x40')
    expect(w.find('[data-testid="label-page-rule"]').text()).toContain('size: 70mm 40mm')
    expect(w.find('.qr-label-sheet--tem-70x40').exists()).toBe(true)
    expect(w.find('.qr-label-sheet--tem-50x30').exists()).toBe(false)
  })

  it("tem vật lý → AssetQrLabel nhận format + qrSize từ SSoT (KHÔNG 120px cố định)", async () => {
    const w = mount(AssetLabelPrintView)
    await flushPromises()
    await selectFormat(w, 'tem-70x40')
    const labels = w.findAllComponents(AssetQrLabel)
    expect(labels.length).toBe(3)
    expect(labels[0].props('format')).toBe('tem-70x40')
    expect(labels[0].props('qrSize')).toBe(getLabelFormat('tem-70x40').qrSizePx)
  })

  it("Regression: chọn tem rồi In tất cả → printLabels 1 lần name hợp lệ; 'Đã in xong' → markLabelPrinted name hợp lệ", async () => {
    getBatchSpy.mockResolvedValue([lbl('A1'), { name: 'BAD', error: 'AC-E001' }, lbl('A3')])
    const w = mount(AssetLabelPrintView)
    await flushPromises()
    await selectFormat(w, 'tem-50x30')
    const printBtn = w.findAll('button').find(b => b.text().includes('In tất cả'))
    await printBtn!.trigger('click')
    await flushPromises()
    // Luồng PDF: printLabels 1 lần với CHỈ name hợp lệ (loại AC-E001).
    expect(printLabelsSpy).toHaveBeenCalledTimes(1)
    expect(printLabelsSpy.mock.calls[0][0]).toEqual(['A1', 'A3'])
    // Ghi audit qua 'Đã in xong' — chỉ name hợp lệ.
    await w.find('[data-testid="btn-pdf-printed"]').trigger('click')
    await flushPromises()
    expect(markPrintedSpy).toHaveBeenCalledWith(['A1', 'A3'])
    // Ô lỗi VI vẫn render (preview grid trên màn hình giữ nguyên).
    expect(w.text()).toContain('Không tìm thấy thiết bị')
  })
})

// ── AssetQrLabel — format prop scale ──────────────────────────────────────────
describe('AssetQrLabel — khổ tem → QR/field scale', () => {
  const VALID = {
    name: 'AC-ASSET-2026-00042', asset_code: 'A-042',
    device_model_name: 'Dräger V500', location_name: 'ICU',
    lifecycle_status: 'Active', qr_url: 'http://miyano/a/tok42',
  }

  it("a4-multi (mặc định, không truyền format) → KHÔNG class physical, giữ 120px (CSS)", async () => {
    const w = mount(AssetQrLabel, { props: { label: VALID } })
    await flushPromises()
    expect(w.find('.qr-label--physical').exists()).toBe(false)
    // img KHÔNG có inline style override (giữ 120px từ CSS scoped).
    const img = w.find('img')
    expect(img.attributes('style') ?? '').not.toContain('width')
  })

  it("tem-50x30 → class physical + img có inline width/height theo qrSize (KHÔNG 120px cố định)", async () => {
    const w = mount(AssetQrLabel, { props: { label: VALID, format: 'tem-50x30', qrSize: 96 } })
    await flushPromises()
    expect(w.find('.qr-label--physical').exists()).toBe(true)
    expect(w.find('.qr-label--tem-50x30').exists()).toBe(true)
    const style = w.find('img').attributes('style') ?? ''
    expect(style).toContain('96px')
    expect(style).not.toContain('120px')
  })

  it("tem-70x40 → QR encode width = qrSize (mm-aware, lớn hơn 120 không bắt buộc nhưng theo SSoT)", async () => {
    const w = mount(AssetQrLabel, { props: { label: VALID, format: 'tem-70x40', qrSize: 132 } })
    await flushPromises()
    const style = w.find('img').attributes('style') ?? ''
    expect(style).toContain('132px')
  })

  it("tem vật lý vẫn giữ ô lỗi AC-E001 VI + KHÔNG QR", async () => {
    const w = mount(AssetQrLabel, { props: { label: { name: 'BAD', error: 'AC-E001' }, format: 'tem-50x30', qrSize: 96 } })
    await flushPromises()
    expect(w.text()).toContain('Không tìm thấy thiết bị')
    expect(w.find('img').exists()).toBe(false)
  })

  it("tem vật lý vẫn dịch trạng thái VI (translateStatus SSoT — KHÔNG leak 'Active')", async () => {
    const w = mount(AssetQrLabel, { props: { label: VALID, format: 'tem-70x40', qrSize: 132 } })
    await flushPromises()
    expect(w.text()).toContain('Đang hoạt động')
    expect(w.text()).not.toContain('Active')
  })
})
