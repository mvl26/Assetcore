// Copyright (c) 2026, AssetCore Team — SSoT khổ tem (print fidelity, roadmap B, TDD)
import { describe, it, expect } from 'vitest'
import {
  LABEL_FORMATS, DEFAULT_LABEL_FORMAT_KEY, getLabelFormat, pageRuleFor,
} from '@/constants/labelFormats'

describe('LABEL_FORMATS — SSoT khổ tem in nhãn QR', () => {
  it('có đủ 3 format: a4-multi / tem-50x30 / tem-70x40', () => {
    const keys = LABEL_FORMATS.map((f) => f.key)
    expect(keys).toEqual(['a4-multi', 'tem-50x30', 'tem-70x40'])
  })

  it('mặc định = a4-multi (giữ hành vi cũ)', () => {
    expect(DEFAULT_LABEL_FORMAT_KEY).toBe('a4-multi')
    expect(getLabelFormat(DEFAULT_LABEL_FORMAT_KEY).physical).toBe(false)
  })

  it('a4-multi: KHÔNG ép @page (pageSizeCss=null), 2 cột, nhãn không vật lý', () => {
    const a4 = getLabelFormat('a4-multi')
    expect(a4.pageSizeCss).toBeNull()
    expect(a4.gridCols).toBe(2)
    expect(a4.physical).toBe(false)
    // KHÔNG sinh @page rule cho A4 (regression — giữ lưới cũ).
    expect(pageRuleFor('a4-multi')).toBe('')
  })

  it('tem-50x30: @page size "50mm 30mm" + 1 nhãn/trang (1 cột)', () => {
    const t = getLabelFormat('tem-50x30')
    expect(t.pageSizeCss).toBe('50mm 30mm')
    expect(t.gridCols).toBe(1)
    expect(t.physical).toBe(true)
    expect(pageRuleFor('tem-50x30')).toContain('size: 50mm 30mm')
    expect(pageRuleFor('tem-50x30')).toContain('@page')
  })

  it('tem-70x40: @page size "70mm 40mm" + 1 nhãn/trang', () => {
    const t = getLabelFormat('tem-70x40')
    expect(t.pageSizeCss).toBe('70mm 40mm')
    expect(t.gridCols).toBe(1)
    expect(pageRuleFor('tem-70x40')).toContain('size: 70mm 40mm')
  })

  it('tem vật lý dùng QR > 120px cũ KHÔNG cố định (đủ lớn camera quét)', () => {
    // QR không còn pixel cố định 120px khi in tem vật lý — qrSizePx > 0 + có chênh lệch theo khổ.
    expect(getLabelFormat('tem-50x30').qrSizePx).toBeGreaterThan(0)
    expect(getLabelFormat('tem-70x40').qrSizePx).toBeGreaterThan(getLabelFormat('tem-50x30').qrSizePx)
  })

  it('getLabelFormat key lạ → fallback a4-multi (an toàn)', () => {
    // @ts-expect-error — test runtime fallback với key ngoài union
    expect(getLabelFormat('khong-ton-tai').key).toBe('a4-multi')
  })
})
