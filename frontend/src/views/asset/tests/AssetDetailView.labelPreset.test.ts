// Copyright (c) 2026, AssetCore Team — AssetDetailView selector khổ tem 3-preset (TDD)
//
// Vòng 4 IMM-00/label-pdf: AssetDetailView (in nhãn QR lẻ) có selector 'Khổ tem'
// (data-testid="label-preset-select") liệt kê ĐÚNG 3 option từ SSoT LABEL_PDF_PRESETS
// (tem-60x100 / tem-70x40 / tem-50x30), default = LABEL_PDF_PRESET (tem-60x100).
// printLabels truyền preset ĐANG CHỌN xuống printAssetLabelsPdf([id], selectedPreset).
// Tiêu đề modal + badge + microcopy hết hardcode '60×100mm' → labelPdfPresetLabel.
// Selector + nút In nhãn QR đều gate can('asset.print') — parity với batch view.
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
// D6: selector + nút 'In nhãn QR' gate asset.PRINT. canCaps set ngoài test để giả lập persona.
const canCaps = new Set<string>(['asset.print'])
vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({
    can: (c: string | readonly string[]) =>
      Array.isArray(c) ? c.some((x) => canCaps.has(x)) : canCaps.has(c as string),
  }),
}))
vi.mock('@/composables/useNotify', () => ({ useNotify: () => ({ fromError: vi.fn(), success: vi.fn() }) }))
vi.mock('@/composables/useToast', () => ({ useToast: () => ({ show: vi.fn() }) }))

// ── Spy API — printAssetLabelsPdf nhận (names, preset). SSoT preset re-export THẬT
// (giữ LABEL_PDF_PRESETS/labelPdfPresetLabel thật — view dùng đúng SSoT). ──
const printPdfSpy = vi.fn()
const markPrintedSpy = vi.fn().mockResolvedValue({ printed: ['AC-ASSET-2026-00042'], event_count: 1 })
vi.mock('@/api/imm00', () => ({
  getAssetTimeline: vi.fn().mockResolvedValue({ items: [] }),
  getAssetKpi: vi.fn().mockResolvedValue(null),
  verifyChain: vi.fn().mockResolvedValue(null),
  deleteAsset: vi.fn(),
  getAssetLabelData: vi.fn().mockResolvedValue(null),
  markLabelPrinted: (assets: string[]) => markPrintedSpy(assets),
  printAssetLabelsPdf: (names: string[], preset: string) => printPdfSpy(names, preset),
  // SSoT preset — giữ THẬT (3 preset whitelist + nhãn VI).
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

// ── Mock composable usePdfLabelPrint ────────────────────────────────────────────
// printLabels(names) → gọi fetcher THẬT (view truyền closure đọc selectedPreset)
// để printPdfSpy nhận (names, preset). previewUrl set → modal preview render.
const fetcherSpy = vi.fn()
const revokeSpy = vi.fn()
const previewUrl = ref<string | null>(null)
const printing = ref(false)
const pdfError = ref<unknown>(null)
let capturedFetcher: ((names: string[]) => unknown) | undefined
vi.mock('@/composables/usePdfLabelPrint', () => ({
  usePdfLabelPrint: (fetcher: (names: string[]) => unknown) => {
    capturedFetcher = fetcher
    return {
      printLabels: async (names: string[]) => {
        // Gọi fetcher THẬT → printAssetLabelsPdf(names, selectedPreset.value).
        await fetcher(names)
        previewUrl.value = 'blob:mock-pdf'
        return fetcherSpy(names)
      },
      previewUrl, printing, error: pdfError, revoke: revokeSpy,
    }
  },
}))

import AssetDetailView from '@/views/asset/AssetDetailView.vue'

const stubs = {
  PageHeader: true, teleport: true, SmartSelect: true,
  AssetDowntimeWidget: true, AssetDepreciationSchedule: true, BaseModal: false,
}

function findByText(w: ReturnType<typeof mount>, txt: string) {
  return w.findAll('button').find((b) => b.text().includes(txt))
}

async function mountDetail() {
  const w = mount(AssetDetailView, { props: { id: 'AC-ASSET-2026-00042' }, global: { stubs } })
  await flushPromises()
  return w
}

describe('AssetDetailView — selector khổ tem 3-preset (in nhãn QR lẻ)', () => {
  beforeEach(() => {
    printPdfSpy.mockReset().mockResolvedValue(new Blob(['%PDF'], { type: 'application/pdf' }))
    fetcherSpy.mockReset().mockResolvedValue(new Blob(['%PDF'], { type: 'application/pdf' }))
    markPrintedSpy.mockClear().mockResolvedValue({ printed: ['AC-ASSET-2026-00042'], event_count: 1 })
    revokeSpy.mockClear()
    previewUrl.value = null
    printing.value = false
    pdfError.value = null
    capturedFetcher = undefined
    canCaps.clear()
    canCaps.add('asset.print')
  })

  it('TC-DETAIL-PRESET-01: selector tồn tại, ĐÚNG 3 option khớp LABEL_PDF_PRESETS, default tem-60x100', async () => {
    const w = await mountDetail()
    const sel = w.find('[data-testid="label-preset-select"]')
    expect(sel.exists()).toBe(true)
    const opts = sel.findAll('option')
    expect(opts).toHaveLength(3)
    expect(opts.map((o) => o.attributes('value'))).toEqual(['tem-60x100', 'tem-70x40', 'tem-50x30'])
    // Nhãn VI từ SSoT.
    expect(opts.map((o) => o.text())).toEqual(['Tem 60×100mm', 'Tem 70×40mm', 'Tem 50×30mm'])
    // Default value === 'tem-60x100' (parity cũ).
    expect((sel.element as HTMLSelectElement).value).toBe('tem-60x100')
  })

  it('TC-DETAIL-PRESET-02: chọn tem-70x40 / tem-50x30 rồi in → printAssetLabelsPdf([id], preset)', async () => {
    const w = await mountDetail()
    const sel = w.find('[data-testid="label-preset-select"]')

    await sel.setValue('tem-70x40')
    await findByText(w, 'In nhãn QR')!.trigger('click')
    await flushPromises()
    expect(printPdfSpy).toHaveBeenLastCalledWith(['AC-ASSET-2026-00042'], 'tem-70x40')

    // Đóng + đổi tiếp tem-50x30 → in lại.
    const closeBtn = w.findAll('button').find((b) => b.text().trim() === 'Đóng')
    await closeBtn!.trigger('click')
    await flushPromises()
    await sel.setValue('tem-50x30')
    await findByText(w, 'In nhãn QR')!.trigger('click')
    await flushPromises()
    expect(printPdfSpy).toHaveBeenLastCalledWith(['AC-ASSET-2026-00042'], 'tem-50x30')
  })

  it('TC-DETAIL-PRESET-03: không đổi gì rồi in → printAssetLabelsPdf([id], tem-60x100) (parity cũ — no regression)', async () => {
    const w = await mountDetail()
    await findByText(w, 'In nhãn QR')!.trigger('click')
    await flushPromises()
    expect(printPdfSpy).toHaveBeenCalledWith(['AC-ASSET-2026-00042'], 'tem-60x100')
  })

  it('TC-DETAIL-PRESET-04: tiêu đề modal + badge phản ánh khổ đang chọn — no em-dash/leak', async () => {
    const w = await mountDetail()
    const sel = w.find('[data-testid="label-preset-select"]')
    await sel.setValue('tem-70x40')
    await findByText(w, 'In nhãn QR')!.trigger('click')
    await flushPromises()

    // Badge phản ánh khổ đang chọn.
    const badge = w.find('[data-testid="label-preset-badge"]')
    expect(badge.exists()).toBe(true)
    expect(badge.text()).toContain('Tem 70×40mm')

    // Tiêu đề modal chứa nhãn từ labelPdfPresetLabel (đổi theo khổ).
    // Scope vào MODAL CARD (BaseModal) — KHÔNG cả component HTML (option list luôn có 60×100).
    const modalCard = w.find('[data-testid="modal-card"]')
    expect(modalCard.exists()).toBe(true)
    const modalText = modalCard.text()
    expect(modalText).toContain('70×40mm') // tiêu đề + microcopy phản ánh khổ đang chọn
    expect(modalText).not.toContain('60×100mm') // tiêu đề/microcopy KHÔNG ép cứng 60×100 nữa
    // KHÔNG em-dash placeholder leak trong vùng nhãn khổ.
    expect(badge.text()).not.toContain('—')
  })

  it('TC-DETAIL-PRESET-05: persona thiếu asset.print → selector + nút In nhãn QR đều ABSENT', async () => {
    canCaps.clear()
    canCaps.add('asset.read')
    const w = await mountDetail()
    expect(w.find('[data-testid="label-preset-select"]').exists()).toBe(false)
    expect(w.find('[data-testid="label-preset-badge"]').exists()).toBe(false)
    expect(findByText(w, 'In nhãn QR')).toBeFalsy()
  })

  it('TC-DETAIL-PRESET-06 (anti-leak/i18n): DOM không leak raw key chưa map / qr_token / enum EN', async () => {
    const w = await mountDetail()
    await findByText(w, 'In nhãn QR')!.trigger('click')
    await flushPromises()
    const html = w.html()
    // Nhãn khổ là VI — KHÔNG lộ raw preset key chưa map.
    expect(html).toContain('Tem 60×100mm')
    expect(html).not.toMatch(/>\s*tem-60x100\s*</) // raw key không lọt ra text node nhãn
    // KHÔNG leak qr_token / lifecycle_status enum thô / email.
    expect(html).not.toContain('qr_token')
    expect(html).not.toMatch(/\b(Active|Pending|Draft|Commissioned)\b/) // enum EN thô
  })
})
