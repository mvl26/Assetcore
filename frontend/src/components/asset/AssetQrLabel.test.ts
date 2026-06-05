// Copyright (c) 2026, AssetCore Team — AssetQrLabel (A4/V5, TDD)
//
// RED-prove (task A4):
//   • render payload hợp lệ → QRCode.toDataURL gọi với ĐÚNG label.qr_url (KHÔNG
//     asset_code / KHÔNG token / KHÔNG mã hoá chuỗi tag).
//   • hiển thị 6 field (name, asset_code, device_model_name, location_name, lifecycle_status, qr_url).
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

const VALID: AssetLabelData = {
  name: 'AC-ASSET-2026-00042',
  asset_code: 'A-042',
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
    expect(encoded).not.toBe('A-042')
    expect(encoded).not.toBe('tok_abc123XYZ')
  })

  it('hiển thị đủ 6 field cấp tài sản', async () => {
    const w = mount(AssetQrLabel, { props: { label: VALID } })
    await flushPromises()
    const text = w.text()
    expect(text).toContain('AC-ASSET-2026-00042')
    expect(text).toContain('A-042')
    expect(text).toContain('Dräger V500')
    expect(text).toContain('ICU - P.301')
    // QR ảnh render.
    expect(w.find('img').exists()).toBe(true)
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
})
