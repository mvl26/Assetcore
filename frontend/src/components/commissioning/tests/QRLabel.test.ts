// Copyright (c) 2026, AssetCore Team — QRLabel (commissioning, B dedup QR, TDD)
//
// RED-prove (task B — hội tụ nhãn commissioning về deep-link asset /a/<token>):
//   • res.qr_url có → QRCode.toDataURL ĐƯỢC GỌI với qr_url (deep-link), KHÔNG
//     với qr_value (chuỗi tag BV-... thô) → quét mobile mở AssetScanInfo.
//   • res.qr_url null/absent (phiếu chưa release) → fallback encode qr_value
//     (nhãn KHÔNG vỡ, tương thích ngược).
//   • Component KHÔNG render link desk /app/asset-commissioning/ (no desk-login leak).
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
// SSoT guard: nhãn trạng thái PHẢI đi qua DUY NHẤT formatters.translateStatus
// (anti-pattern A — chống hardcode lại nhãn trong component). Import trực tiếp
// để assert giá trị render == STATUS_MAP[...] thật, không phải nhãn bịa.
import { translateStatus } from '@/utils/formatters'

const toDataURLSpy = vi.fn().mockResolvedValue('data:image/png;base64,QRMOCK==')
vi.mock('qrcode', () => ({
  default: { toDataURL: (...args: unknown[]) => toDataURLSpy(...args) },
}))

const generateQrLabelMock = vi.fn()
vi.mock('@/api/imm04', () => ({
  generateQrLabel: (...args: unknown[]) => generateQrLabelMock(...args),
}))

import QRLabel from '@/components/commissioning/QRLabel.vue'
import type { QrLabelData } from '@/types/imm04'

const DEEP_LINK = 'https://miyano.test/a/tok_OPAQUE123xyz'
const TAG = 'BV-ICU-2026-0042'

function makeLabel(over: Partial<QrLabelData> = {}): QrLabelData {
  return {
    qr_value: TAG,
    qr_url: DEEP_LINK,
    label: {
      title: 'ASSETCORE — NHÃN THIẾT BỊ',
      commissioning_id: 'COMM-2026-0001',
      internal_qr: TAG,
      vendor_serial: 'SN-001',
      model: 'MODEL-A',
      vendor: 'VENDOR-A',
      dept: 'ICU',
      moh_code: 'MOH-1',
      installation_date: '2026-06-01',
      status: 'Clinical Release',
      asset_id: 'AC-ASSET-2026-00042',
      print_date: '2026-06-04',
    },
    docs_url: null,
    ...over,
  }
}

describe('QRLabel (commissioning) — B dedup QR về deep-link asset', () => {
  beforeEach(() => {
    toDataURLSpy.mockClear()
    generateQrLabelMock.mockReset()
  })

  it('encodes_deep_link_when_qr_url_present', async () => {
    generateQrLabelMock.mockResolvedValue(makeLabel({ qr_url: DEEP_LINK }))
    mount(QRLabel, { props: { name: 'COMM-2026-0001' } })
    await flushPromises()
    expect(toDataURLSpy).toHaveBeenCalledTimes(1)
    const encoded = toDataURLSpy.mock.calls[0][0]
    expect(encoded).toBe(DEEP_LINK)
    // KHÔNG mã hoá chuỗi tag thô vào ảnh QR khi đã có deep-link.
    expect(encoded).not.toBe(TAG)
  })

  it('falls_back_to_qr_value_when_no_qr_url', async () => {
    // Phiếu chưa release: qr_url null → fallback encode qr_value (tag cũ).
    generateQrLabelMock.mockResolvedValue(makeLabel({ qr_url: null }))
    mount(QRLabel, { props: { name: 'COMM-2026-0002' } })
    await flushPromises()
    expect(toDataURLSpy).toHaveBeenCalledTimes(1)
    expect(toDataURLSpy.mock.calls[0][0]).toBe(TAG)
  })

  it('renders_no_desk_scan_url', async () => {
    generateQrLabelMock.mockResolvedValue(makeLabel())
    const w = mount(QRLabel, { props: { name: 'COMM-2026-0001' } })
    await flushPromises()
    // KHÔNG render link desk-login /app/asset-commissioning/ trên nhãn.
    expect(w.html()).not.toContain('/app/asset-commissioning/')
    // Cũng không có anchor trỏ desk.
    const hrefs = w.findAll('a').map((a) => a.attributes('href') || '')
    expect(hrefs.some((h) => h.includes('/app/asset-commissioning/'))).toBe(false)
  })
})

describe('QRLabel (commissioning) — B i18n trạng thái qua SSoT translateStatus', () => {
  beforeEach(() => {
    toDataURLSpy.mockClear()
    generateQrLabelMock.mockReset()
  })

  async function mountWithStatus(status: string | null) {
    generateQrLabelMock.mockResolvedValue(
      makeLabel({ label: { ...makeLabel().label, status: status as string } }),
    )
    const w = mount(QRLabel, { props: { name: 'COMM-2026-0001' } })
    await flushPromises()
    return w
  }

  it('renders_status_in_vietnamese_via_SSoT', async () => {
    // workflow_state='Clinical Release' (mã canonical EN BE trả) → nhãn VI.
    const w = await mountWithStatus('Clinical Release')
    const cell = w.get('[data-testid="commissioning-status"]')
    expect(cell.text()).toBe('Phát hành lâm sàng')
    // KHÔNG còn render chuỗi EN thô trên dòng trạng thái.
    expect(cell.text()).not.toContain('Clinical Release')
    // Guard SSoT: giá trị render == đúng STATUS_MAP qua translateStatus (chống
    // hardcode nhãn riêng trong component — anti-pattern A).
    expect(cell.text()).toBe(translateStatus('Clinical Release'))
  })

  it('translates_commissioned_status', async () => {
    const w = await mountWithStatus('Commissioned')
    const cell = w.get('[data-testid="commissioning-status"]')
    expect(cell.text()).toBe('Đã đưa vào sử dụng')
    expect(cell.text()).not.toContain('Commissioned')
    expect(cell.text()).toBe(translateStatus('Commissioned'))
  })

  it('translates_initial_inspection_status', async () => {
    // Phủ thêm 1 state multi-word khác (chống regression khoảng trắng).
    const w = await mountWithStatus('Initial Inspection')
    const cell = w.get('[data-testid="commissioning-status"]')
    expect(cell.text()).toBe('Kiểm tra ban đầu')
    expect(cell.text()).not.toContain('Initial Inspection')
    expect(cell.text()).toBe(translateStatus('Initial Inspection'))
  })

  it('status_empty_falls_back_to_dash', async () => {
    // status rỗng/null → '—', KHÔNG 'undefined'/chuỗi rỗng, nhãn KHÔNG vỡ.
    const w = await mountWithStatus('')
    const cell = w.get('[data-testid="commissioning-status"]')
    expect(cell.text()).toBe('—')
    expect(cell.text()).not.toContain('undefined')
    expect(cell.text().length).toBeGreaterThan(0)
  })
})
