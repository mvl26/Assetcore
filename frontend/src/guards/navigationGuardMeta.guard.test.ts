// Copyright (c) 2026, AssetCore Team
//
// Meta-guard chống tái diễn open-redirect (IMM-00 B / ADR-001 D4).
// Quét toàn bộ src/ và đảm bảo KHÔNG còn chỗ nào router.push thẳng giá trị
// untrusted route.query.redirect mà không qua SSoT isSafeInternalRedirect.

import { describe, it, expect } from 'vitest'
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { join } from 'node:path'
import { SRC, listFiles } from '@/test/paths'


function walk(dir: string): string[] {
  const out: string[] = []
  for (const name of readdirSync(dir)) {
    const full = join(dir, name)
    if (statSync(full).isDirectory()) {
      out.push(...walk(full))
    } else if (/\.(vue|ts)$/.test(name) && !/\.test\.ts$/.test(name)) {
      out.push(full)
    }
  }
  return out
}

describe('meta-guard: open-redirect (IMM-00)', () => {
  it('không có site nào router.push(route.query.redirect) thô (phải qua isSafeInternalRedirect)', () => {
    const offenders: string[] = []
    // Bắt mọi router.push(...) mà arg chứa route.query.redirect trực tiếp.
    const rawPush = /router\.push\([^)]*route\.query\.redirect[^)]*\)/
    for (const file of walk(SRC)) {
      const src = readFileSync(file, 'utf8')
      if (rawPush.test(src)) offenders.push(file)
    }
    expect(offenders).toEqual([])
  })
})

// ─── Chốt dân số thư mục quét (SPEC §5.2 N6 — chống guard xanh giả) ───────────
// Guard ở trên khẳng định dạng "không tìm thấy vi phạm nào". Khẳng định đó đúng
// một cách RỖNG TUẾCH nếu bộ quét không đọc được file nào — điều xảy ra âm thầm
// khi thư mục bị dời/đổi tên. Chốt dưới đây biến tình huống đó thành ĐỎ.
// Số đo từ đĩa 2026-08-13: 736 file. Ngưỡng đặt thấp hơn có chủ ý để thêm/bớt
// vài file không gây đỏ giả; sửa ngưỡng phải là hành vi CÓ Ý THỨC.
describe('chốt dân số thư mục quét', () => {
  it('src/**/*.{vue,ts} còn ít nhất 600 file — nếu không, guard đã ngừng canh', () => {
    expect(listFiles(SRC, { ext: ['.vue', '.ts'], min: 600 }).length).toBeGreaterThanOrEqual(600)
  })
})
