// Copyright (c) 2026, AssetCore Team
// Guard chống LINK CHẾT: mọi đường dẫn khai trong DOCTYPE_ROUTE phải tồn tại thật trong
// router. Không có guard này, một ô "Bản ghi liên quan" bấm vào ra trang 404 mà chẳng
// test nào đỏ — đúng loại lỗi câm mà toàn bộ đợt refactor này đang tìm cách triệt.
import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { DOCTYPE_ROUTE, routeForDoctype } from './connections'

function routerPaths(): Set<string> {
  // Đọc từ gốc project (vitest chạy với cwd = frontend/) — `import.meta.url` dưới
  // jsdom không phải scheme file nên không dùng được.
  const src = readFileSync(resolve(process.cwd(), 'src/router/index.ts'), 'utf-8')
  return new Set([...src.matchAll(/path:\s*'([^']+)'/g)].map(m => m[1]))
}

describe('DOCTYPE_ROUTE', () => {
  it('mọi đường dẫn đều tồn tại trong router (không link chết)', () => {
    const paths = routerPaths()
    const dead = Object.entries(DOCTYPE_ROUTE).filter(([, p]) => !paths.has(p))
    expect(dead, `Đường dẫn không có trong router: ${JSON.stringify(dead)}`).toEqual([])
  })

  it('doctype chưa có màn hình trả null thay vì đoán đường dẫn', () => {
    expect(routeForDoctype('Asset Lifecycle Event')).toBeNull()
    expect(routeForDoctype('Doctype Bịa Ra')).toBeNull()
  })

  it('doctype đã có màn hình trả đúng đường dẫn', () => {
    expect(routeForDoctype('AC Asset')).toBe('/assets')
    expect(routeForDoctype('PM Work Order')).toBe('/pm/work-orders')
  })
})
