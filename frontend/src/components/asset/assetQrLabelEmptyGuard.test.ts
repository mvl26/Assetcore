// Copyright (c) 2026, AssetCore Team — AssetQrLabel empty-qr_url guard (Vòng 30, TDD revert-proof)
//
// Đề mục Vòng 30 (IMM-00 / label-pdf — BR-00-49 / FR-00-100 / ADR §D20, TC-LABEL-QREMPTY-06):
// Bất đối xứng BE↔FE — server-side PDF `_label_block` thiếu guard `qr_url` rỗng (junk-QR
// dán lên thiết bị). FE ĐÃ AN TOÀN từ trước: `AssetQrLabel.vue:73` guard
// `const value = props.label.qr_url; if (!value) { qrFailed.value = true; return }` →
// `qr_url` rỗng/null/undefined → KHÔNG gọi `QRCode.toDataURL` → render ô-fallback VI
// `Không tạo được mã QR` (parity nhãn VI với BE-PDF fix §D20). Fix mới CHỈ ở BE.
//
// File này = re-verify guard CÒN RĂNG + revert-proof (LL-TEST-26):
//   (a) qr_url '' / null / undefined → qrFailed=true, KHÔNG toDataURL, DOM ô-fallback VI;
//   (b) qr_url '/a/TOKEN' hợp lệ → qrFailed=false, QR render (no-regression);
//   (c) revert-proof source-grep: guard `if (!value)` PHẢI tồn tại ở source — xoá → đỏ.
//
// KHÔNG đổi 1 dòng logic FE (DoD §II.3f-PDF-QREMPTY). FE-only — KHÔNG reload/HTTP.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const toDataURLSpy = vi.fn().mockResolvedValue('data:image/png;base64,QRMOCK==')
vi.mock('qrcode', () => ({
  default: { toDataURL: (...args: unknown[]) => toDataURLSpy(...args) },
}))

import AssetQrLabel from './AssetQrLabel.vue'
import type { AssetLabelData } from '@/api/imm00'

// Payload hợp lệ baseline (asset thật) — chỉ đổi qr_url theo từng case.
const VALID: AssetLabelData = {
  name: 'AC-ASSET-2026-00777',
  asset_code: 'AC-ASSET-2026-00777',
  asset_name: 'Máy thở Servo-u',
  manufacturer_sn: 'SN-NSX-777',
  device_model_name: 'Getinge Servo-u',
  location_name: 'ICU - P.512',
  lifecycle_status: 'Active',
  qr_url: 'http://miyano/a/tok_valid_777',
}

const FALLBACK_VI = 'Không tạo được mã QR'

describe('AssetQrLabel — guard qr_url rỗng (Vòng 30, revert-proof)', () => {
  beforeEach(() => {
    toDataURLSpy.mockClear()
  })

  // ── (a) qr_url RỖNG → ô-fallback an toàn, KHÔNG encode ──────────────────────
  it('qr_url = "" → qrFailed, KHÔNG gọi QRCode.toDataURL, DOM ô-fallback VI', async () => {
    const w = mount(AssetQrLabel, { props: { label: { ...VALID, qr_url: '' } } })
    await flushPromises()
    // KHÔNG encode chuỗi rỗng thành QR rác (chống junk-QR client-side).
    expect(toDataURLSpy).not.toHaveBeenCalled()
    // Ô-fallback an toàn VI hiện diện (parity nhãn BE-PDF §D20).
    const fallback = w.find('.qr-label__qr-fallback')
    expect(fallback.exists()).toBe(true)
    expect(fallback.text()).toBe(FALLBACK_VI)
    // KHÔNG <img> QR (data-url rỗng → v-else nhánh fallback).
    expect(w.find('.qr-label__qr img').exists()).toBe(false)
    // 5 field chữ VẪN render (degrade an toàn — chỉ ô QR đổi, nhãn không vỡ).
    const text = w.text()
    expect(text).toContain('AC-ASSET-2026-00777')
    expect(text).toContain('Máy thở Servo-u')
    expect(text).toContain('SN-NSX-777')
    expect(text).not.toContain('undefined')
  })

  // null → falsy → CÙNG nhánh guard (lặp theo DoD §II.3f-PDF-QREMPTY (a)).
  it('qr_url = null → qrFailed, KHÔNG encode, ô-fallback VI', async () => {
    const w = mount(AssetQrLabel, {
      // qr_url là string trong type; null/undefined là input drift thực tế từ BE.
      props: { label: { ...VALID, qr_url: null as unknown as string } },
    })
    await flushPromises()
    expect(toDataURLSpy).not.toHaveBeenCalled()
    expect(w.find('.qr-label__qr-fallback').text()).toBe(FALLBACK_VI)
    expect(w.find('.qr-label__qr img').exists()).toBe(false)
  })

  // undefined → falsy → CÙNG nhánh guard.
  it('qr_url = undefined → qrFailed, KHÔNG encode, ô-fallback VI', async () => {
    const w = mount(AssetQrLabel, {
      props: { label: { ...VALID, qr_url: undefined as unknown as string } },
    })
    await flushPromises()
    expect(toDataURLSpy).not.toHaveBeenCalled()
    expect(w.find('.qr-label__qr-fallback').text()).toBe(FALLBACK_VI)
    expect(w.find('.qr-label__qr img').exists()).toBe(false)
  })

  // ── (b) qr_url HỢP LỆ → QR render (no-regression — guard KHÔNG bắt nhầm) ─────
  it('qr_url = "/a/TOKEN" hợp lệ → KHÔNG qrFailed, QR encode + <img> render', async () => {
    const w = mount(AssetQrLabel, {
      props: { label: { ...VALID, qr_url: 'http://miyano/a/tok_valid_777' } },
    })
    await flushPromises()
    // Encode ĐÚNG 1 lần với qr_url (KHÔNG bị guard bắt nhầm).
    expect(toDataURLSpy).toHaveBeenCalledTimes(1)
    expect(toDataURLSpy.mock.calls[0][0]).toBe('http://miyano/a/tok_valid_777')
    // QR ảnh render, KHÔNG ô-fallback.
    expect(w.find('.qr-label__qr img').exists()).toBe(true)
    expect(w.find('.qr-label__qr-fallback').exists()).toBe(false)
  })

  // ── (c) REVERT-PROOF (LL-TEST-26): guard `if (!value)` PHẢI tồn tại ở source ──
  // Đọc source thô + giữ dòng code (loại comment/template) → assert guard `:73`
  // CÒN RĂNG. Xoá `if (!value) { qrFailed... return }` ở component → test này ĐỎ
  // (guard biến mất); khôi phục → XANH. Chống regression silent-revert.
  it('revert-proof: source AssetQrLabel.vue CHỨA guard `if (!value)` trong renderQr', () => {
    const src = readFileSync(
      resolve(process.cwd(), 'src/components/asset/AssetQrLabel.vue'),
      'utf-8',
    )
    // Strip comment dòng (// ...) + block comment để guard so trên CODE thật,
    // không false-positive vì wording trong comment giải thích.
    const codeOnly = src
      .replace(/\/\*[\s\S]*?\*\//g, '')
      .split('\n')
      .map(l => l.replace(/\/\/.*$/, ''))
      .join('\n')
    // Guard rút gọn whitespace để khớp dù format đổi nhẹ.
    const flat = codeOnly.replace(/\s+/g, ' ')
    // `const value = (props.label.qr_url ?? '').trim()` (whitespace-parity .strip() BE
    // §D20) + `if (!value) { qrFailed.value = true; return }`. Regex neo trên
    // `value` GÁN TỪ `props.label.qr_url` (chấp nhận cả dạng thô lẫn `(… ?? '').trim()`)
    // → xoá/đổi guard ở component VẪN ĐỎ (revert-proof CÒN RĂNG).
    expect(flat).toMatch(/const value\s*=.*props\.label\.qr_url/)
    expect(flat).toMatch(/if\s*\(\s*!value\s*\)\s*\{[^}]*qrFailed\.value\s*=\s*true[^}]*return/)
  })
})
