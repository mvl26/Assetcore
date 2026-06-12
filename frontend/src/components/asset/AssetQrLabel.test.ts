// Copyright (c) 2026, AssetCore Team — AssetQrLabel (A4/V5, TDD)
//
// RED-prove (task A4):
//   • render payload hợp lệ → QRCode.toDataURL gọi với ĐÚNG label.qr_url (KHÔNG
//     asset_code / KHÔNG token / KHÔNG mã hoá chuỗi tag).
//   • hiển thị field định danh (asset_code, asset_name, manufacturer_sn, model, location, status).
//   • ADR-IMM00-ASSETCODE D1/D5: asset_code == name (PK) → CHỈ 1 hàng "Mã tài sản"
//     (KHÔNG còn hàng "Mã hệ thống" tách biệt = name trùng giá trị).
//   • lifecycle_status render qua formatter VI (KHÔNG chuỗi EN gốc 'Active').
//   • item lỗi (error: 'AC-E001') → ô lỗi VI, KHÔNG render QR, KHÔNG throw.
//   • No-leak: KHÔNG mã trạng thái EN, KHÔNG token hex thô lộ trên nhãn.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const toDataURLSpy = vi.fn().mockResolvedValue('data:image/png;base64,QRMOCK==')
vi.mock('qrcode', () => ({
  default: { toDataURL: (...args: unknown[]) => toDataURLSpy(...args) },
}))

import AssetQrLabel from './AssetQrLabel.vue'
import type { AssetLabelData } from '@/api/imm00'

// Invariant production (ADR-IMM00-ASSETCODE D5): asset_code == name (PK). Fixture
// phản ánh đúng thực tế — name KHÔNG còn là giá trị thứ-2 khác asset_code.
// manufacturer_sn (Số serial NSX) VẪN khác asset_code → 2 hàng định danh tách bạch.
const VALID: AssetLabelData = {
  name: 'AC-ASSET-2026-00042',
  asset_code: 'AC-ASSET-2026-00042',
  asset_name: 'Máy X-quang DR',
  manufacturer_sn: 'SN-NSX-009',
  device_model_name: 'Dräger V500',
  location_name: 'ICU - P.301',
  lifecycle_status: 'Active',
  qr_url: 'http://miyano/a/tok_abc123XYZ',
}

describe('AssetQrLabel — A4 in nhãn QR cấp tài sản', () => {
  beforeEach(() => {
    toDataURLSpy.mockClear()
  })

  it('QRCode.toDataURL gọi với ĐÚNG label.qr_url (KHÔNG asset_code/token)', async () => {
    mount(AssetQrLabel, { props: { label: VALID } })
    await flushPromises()
    expect(toDataURLSpy).toHaveBeenCalledTimes(1)
    const encoded = toDataURLSpy.mock.calls[0][0]
    expect(encoded).toBe('http://miyano/a/tok_abc123XYZ')
    // KHÔNG mã hoá asset_code hay token thô.
    expect(encoded).not.toBe('AC-ASSET-2026-00042')
    expect(encoded).not.toBe('tok_abc123XYZ')
  })

  it('hiển thị đủ field cấp tài sản (gồm Tên tài sản + Số serial NSX)', async () => {
    const w = mount(AssetQrLabel, { props: { label: VALID } })
    await flushPromises()
    const text = w.text()
    expect(text).toContain('AC-ASSET-2026-00042')
    expect(text).toContain('Máy X-quang DR')
    expect(text).toContain('SN-NSX-009')
    expect(text).toContain('Dräger V500')
    expect(text).toContain('ICU - P.301')
    // QR ảnh render.
    expect(w.find('img').exists()).toBe(true)
  })

  // D5 — Số serial NSX + Tên tài sản render với nhãn VI, TÁCH khỏi Mã tài sản.
  it('render hàng Số serial NSX + Tên tài sản với nhãn VI (KHÔNG leak EN)', async () => {
    const w = mount(AssetQrLabel, { props: { label: VALID } })
    await flushPromises()
    const text = w.text()
    expect(text).toContain('Số serial NSX')
    expect(text).toContain('SN-NSX-009')
    expect(text).toContain('Tên tài sản')
    expect(text).toContain('Máy X-quang DR')
    // KHÔNG leak nhãn EN.
    expect(text).not.toContain('Serial No')
    expect(text).not.toContain('Manufacturer SN')
    expect(text).not.toContain('Serial Number')
    expect(text).not.toContain('undefined')
  })

  // Parity: Mã tài sản (asset_code) và Số serial NSX (manufacturer_sn) là 2 hàng
  // RIÊNG, giá trị khác nhau → chống trộn 2 khái niệm định danh.
  it('Mã tài sản và Số serial NSX là 2 hàng riêng, giá trị khác nhau', async () => {
    const w = mount(AssetQrLabel, { props: { label: VALID } })
    await flushPromises()
    const dts = w.findAll('dt').map(d => d.text())
    expect(dts).toContain('Mã tài sản')
    expect(dts).toContain('Số serial NSX')
    expect(dts).toContain('Tên tài sản')
    // asset_code != manufacturer_sn → 2 giá trị tách bạch cùng hiện diện.
    const text = w.text()
    expect(text).toContain('AC-ASSET-2026-00042')
    expect(text).toContain('SN-NSX-009')
    expect(VALID.asset_code).not.toBe(VALID.manufacturer_sn)
  })

  // ADR-IMM00-ASSETCODE D1/D5: asset_code == name (PK) → KHÔNG còn hàng "Mã hệ thống"
  // trùng giá trị; CHỈ DUY NHẤT 1 hàng định danh PK "Mã tài sản".
  it('KHÔNG render hàng "Mã hệ thống"; chỉ DUY NHẤT 1 hàng "Mã tài sản"', async () => {
    const w = mount(AssetQrLabel, { props: { label: VALID } })
    await flushPromises()
    const dts = w.findAll('dt').map(d => d.text())
    expect(dts).not.toContain('Mã hệ thống')
    expect(dts.filter(d => d === 'Mã tài sản')).toHaveLength(1)
  })

  // Legacy: asset_code rỗng + name set → hàng "Mã tài sản" fallback = name (KHÔNG '—',
  // KHÔNG hiện "Mã hệ thống").
  it('asset_code rỗng + name set (legacy) → "Mã tài sản" render = name (fallback)', async () => {
    const w = mount(AssetQrLabel, {
      props: { label: { ...VALID, asset_code: '', name: 'AC-ASSET-2026-09999' } },
    })
    await flushPromises()
    const dts = w.findAll('dt').map(d => d.text())
    expect(dts).not.toContain('Mã hệ thống')
    expect(dts).toContain('Mã tài sản')
    expect(w.text()).toContain('AC-ASSET-2026-09999')
  })

  // Cả asset_code và name rỗng → hàng "Mã tài sản" render '—', component KHÔNG vỡ.
  it('asset_code + name đều rỗng → "Mã tài sản" render "—", KHÔNG vỡ', async () => {
    const w = mount(AssetQrLabel, {
      props: { label: { ...VALID, asset_code: '', name: '' } },
    })
    await flushPromises()
    const dts = w.findAll('dt').map(d => d.text())
    expect(dts).toContain('Mã tài sản')
    expect(dts).not.toContain('Mã hệ thống')
    expect(w.text()).toContain('—')
    expect(w.text()).not.toContain('undefined')
  })

  // Rỗng → '—', KHÔNG vỡ, KHÔNG 'undefined'.
  it('manufacturer_sn/asset_name rỗng → render "—", KHÔNG vỡ', async () => {
    const w = mount(AssetQrLabel, {
      props: { label: { ...VALID, manufacturer_sn: '', asset_name: '' } },
    })
    await flushPromises()
    const text = w.text()
    expect(text).toContain('Số serial NSX')
    expect(text).toContain('Tên tài sản')
    expect(text).toContain('—')
    expect(text).not.toContain('undefined')
  })

  it('lifecycle_status render qua formatter VI (KHÔNG leak chuỗi EN gốc)', async () => {
    const w = mount(AssetQrLabel, { props: { label: VALID } })
    await flushPromises()
    const text = w.text()
    expect(text).toContain('Đang hoạt động')
    expect(text).not.toContain('Active')
  })

  it('item lỗi AC-E001 → ô lỗi VI, KHÔNG render QR, KHÔNG throw', async () => {
    const w = mount(AssetQrLabel, { props: { label: { name: 'BAD-ID', error: 'AC-E001' } } })
    await flushPromises()
    const text = w.text()
    // Ô lỗi VI tại đúng vị trí — KHÔNG nhãn trắng.
    expect(text).toContain('Không tìm thấy thiết bị')
    expect(text).toContain('BAD-ID')
    // KHÔNG gọi QR encode cho item lỗi.
    expect(toDataURLSpy).not.toHaveBeenCalled()
    expect(w.find('img').exists()).toBe(false)
  })

  it('No-leak: KHÔNG mã trạng thái EN, KHÔNG token hex thô riêng trên nhãn', async () => {
    const w = mount(AssetQrLabel, { props: { label: VALID } })
    await flushPromises()
    const text = w.text()
    // Token chỉ nằm trong qr_url (ảnh) — KHÔNG in token trần như 1 field riêng.
    expect(text).not.toMatch(/\btok_abc123XYZ\b(?!.*\/a\/)/)
    expect(text).not.toContain('Active')
    expect(text).not.toContain('Decommissioned')
  })

  // ── Vòng 30 — parity BE _label_block: qr_url rỗng/whitespace (non-error) → guard
  //   AssetQrLabel.vue:73 `if(!value){qrFailed=true;return}` → KHÔNG encode + fallback
  //   an toàn 'Không tạo được mã QR'. REVERT-PROOF: xoá guard :73 → 2 test này ĐỎ
  //   (toDataURL bị gọi với '' / '   ', không còn fallback). Khôi phục → XANH. ──────
  it('TC7: qr_url="" (non-error) → KHÔNG gọi QRCode.toDataURL, fallback an toàn', async () => {
    const w = mount(AssetQrLabel, { props: { label: { ...VALID, qr_url: '' } } })
    await flushPromises()
    // KHÔNG encode chuỗi rỗng thành QR (chống junk-QR).
    expect(toDataURLSpy).not.toHaveBeenCalled()
    // KHÔNG render ảnh QR; CÓ ô fallback VI an toàn.
    expect(w.find('img').exists()).toBe(false)
    expect(w.text()).toContain('Không tạo được mã QR')
    // KHÔNG vỡ component (vẫn render field định danh).
    expect(w.text()).toContain('AC-ASSET-2026-00042')
    expect(w.text()).not.toContain('undefined')
  })

  it('TC8 parity: qr_url="   " (whitespace) → fallback an toàn, KHÔNG encode whitespace', async () => {
    const w = mount(AssetQrLabel, { props: { label: { ...VALID, qr_url: '   ' } } })
    await flushPromises()
    // PARITY BE .strip(): whitespace-only → trim rỗng → KHÔNG encode (KHÔNG biến
    // dấu cách thành QR). REVERT-PROOF: đổi guard về `if(!value)` (bỏ .trim) → đỏ.
    expect(toDataURLSpy).not.toHaveBeenCalled()
    expect(w.find('img').exists()).toBe(false)
    expect(w.text()).toContain('Không tạo được mã QR')
    expect(w.text()).not.toContain('undefined')
  })

  // ── Vòng 41 — parity BE services/imm00.py::_lifecycle_vi: dòng 'Trạng thái' với
  //   lifecycle_status rỗng/lạ → nhãn SSoT VI 'Chưa rõ' (KHÔNG '—' câm, KHÔNG leak
  //   mã EN thô). 8 mã canonical GIỮ nhãn cũ. REVERT-PROOF: bỏ safe-fallback ở
  //   AssetQrLabel.vue → dòng status về '—'/raw-code → 3 test này ĐỎ. ─────────────
  it('TC41a: lifecycle_status="" → dòng Trạng thái = "Chưa rõ" (KHÔNG "—")', async () => {
    const w = mount(AssetQrLabel, { props: { label: { ...VALID, lifecycle_status: '' } } })
    await flushPromises()
    const dd = w.find('[data-testid="lifecycle-status"]')
    expect(dd.exists()).toBe(true)
    expect(dd.text()).toBe('Chưa rõ')
    // KHÔNG '—' câm trên dòng status.
    expect(dd.text()).not.toBe('—')
  })

  it('TC41b: lifecycle_status="WeirdDrift" (mã lạ) → "Chưa rõ", KHÔNG leak "WeirdDrift"', async () => {
    const w = mount(AssetQrLabel, {
      props: { label: { ...VALID, lifecycle_status: 'WeirdDrift' } },
    })
    await flushPromises()
    const dd = w.find('[data-testid="lifecycle-status"]')
    expect(dd.text()).toBe('Chưa rõ')
    // No-EN-leak: mã thô KHÔNG xuất hiện trên nhãn.
    expect(w.text()).not.toContain('WeirdDrift')
  })

  it('TC41c: lifecycle_status="Active" → nhãn VI "Đang hoạt động" (no-regress canonical)', async () => {
    const w = mount(AssetQrLabel, { props: { label: { ...VALID, lifecycle_status: 'Active' } } })
    await flushPromises()
    const dd = w.find('[data-testid="lifecycle-status"]')
    expect(dd.text()).toBe('Đang hoạt động')
    expect(dd.text()).not.toBe('Chưa rõ')
    expect(w.text()).not.toContain('Active')
  })
})
