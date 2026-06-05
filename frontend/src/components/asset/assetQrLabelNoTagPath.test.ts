// Copyright (c) 2026, AssetCore Team — Guard regression (A4/V5)
//
// AssetQrLabel PHẢI encode URL qr_url BE trả (đường mới), KHÔNG đi đường tag cũ:
// KHÔNG IMPORT generateQrLabel / QRLabel commissioning (encode chuỗi internal_tag).
// Assert trên IMPORT statement (KHÔNG bắt nhầm chữ trong comment — comment giải
// thích "không dùng đường cũ" là hợp lệ).
import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

// Đọc source thô — resolve từ cwd (vitest root = frontend/). import.meta.url
// không là file:// scheme trong setup này.
const SRC = readFileSync(
  resolve(process.cwd(), 'src/components/asset/AssetQrLabel.vue'), 'utf-8',
)

// Chỉ giữ dòng IMPORT (loại comment/template) để guard không false-positive.
const IMPORT_LINES = SRC.split('\n').filter(l => /^\s*import\b/.test(l)).join('\n')

describe('AssetQrLabel — guard KHÔNG dùng đường tag cũ', () => {
  it('KHÔNG import từ @/api/imm04 (đường generateQrLabel commissioning)', () => {
    expect(IMPORT_LINES).not.toContain('@/api/imm04')
    expect(IMPORT_LINES).not.toMatch(/import[^;\n]*generateQrLabel/)
  })

  it('KHÔNG import QRLabel commissioning component', () => {
    expect(IMPORT_LINES).not.toContain('commissioning/QRLabel')
  })

  it('encode qr_url (đường mới) chứ không phải chuỗi tag', () => {
    // Component dùng prop label.qr_url làm value encode (đường BE A4).
    expect(SRC).toContain('qr_url')
  })
})
