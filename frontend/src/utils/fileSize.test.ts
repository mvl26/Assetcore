// Copyright (c) 2026, AssetCore Team
// AC-CR-81 — SSoT format kích thước tệp (VI). Đứng riêng khỏi `formatters.test.ts`
// để tránh đụng file dùng-chung khi nhiều phiên cùng chạy.
//
// Hợp đồng: dấu THẬP PHÂN tiếng Việt là dấu PHẨY ("1,2 MB"), KHÔNG dấu chấm;
// đơn vị giữ ký hiệu chuẩn B/KB/MB/GB (LL-FE-53 mục "GIỮ NGUYÊN" — ký hiệu đơn
// vị, không phải từ tiếng Anh). Chuỗi 'bytes' KHÔNG bao giờ được rò ra UI.
import { describe, it, expect } from 'vitest'

import { formatFileSize } from '@/utils/formatters'

describe('formatFileSize — AC-CR-81', () => {
  it('0 / null / undefined ⇒ chuỗi rỗng (gọi nơi khác tự quyết cách hiển thị)', () => {
    expect(formatFileSize(0)).toBe('')
    expect(formatFileSize(null)).toBe('')
    expect(formatFileSize(undefined)).toBe('')
  })

  it('dưới 1 KB ⇒ số nguyên byte kèm ký hiệu B (KHÔNG chữ "bytes")', () => {
    expect(formatFileSize(512)).toBe('512 B')
    expect(formatFileSize(1)).toBe('1 B')
    expect(formatFileSize(512)).not.toContain('bytes')
  })

  it('KB/MB/GB dùng dấu PHẨY thập phân kiểu Việt Nam', () => {
    expect(formatFileSize(1024)).toBe('1 KB')
    expect(formatFileSize(1536)).toBe('1,5 KB')
    expect(formatFileSize(1_258_291)).toBe('1,2 MB')
    expect(formatFileSize(5 * 1024 * 1024)).toBe('5 MB')
    expect(formatFileSize(2.5 * 1024 * 1024 * 1024)).toBe('2,5 GB')
  })

  it('không rò dấu chấm thập phân kiểu Anh–Mỹ', () => {
    expect(formatFileSize(1_258_291)).not.toContain('1.2')
  })

  it('giá trị rác (âm / NaN / vô hạn) ⇒ rỗng, KHÔNG in "NaN" ra UI', () => {
    expect(formatFileSize(-10)).toBe('')
    expect(formatFileSize(Number.NaN)).toBe('')
    expect(formatFileSize(Number.POSITIVE_INFINITY)).toBe('')
  })
})
