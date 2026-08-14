// Copyright (c) 2026, AssetCore Team
//
// Guard TĨNH chống HỒI SINH hợp đồng đã nghỉ hưu — AC-CR-92 (`06 §VIII.12.3` · ADR §17).
//
// Ô của `get_connections` có ĐÚNG 10 khoá (9 từ AC-CR-92 + `create_prefill` từ AC-CR-105,
// tất cả BẮT BUỘC); bốn khoá LEGACY của bản card cũ đã
// gỡ ở CẢ backend lẫn frontend trong cùng một vòng, kèm hai hàm chỉ tồn tại để phục vụ
// chúng. Kiểu TypeScript một mình KHÔNG chặn được đường quay lại: `vue-tsc` bắt khoá thừa
// trong object literal có kiểu, nhưng KHÔNG bắt `(item as any).count`, không bắt chuỗi
// trong test helper, và không bắt một hàm chết được import lại. "Tạm cast cho qua" chính
// là đường hồi sinh — nên guard này quét NGUỒN và đòi 0 hit trên MỌI file `.ts`/`.vue`.
//
// Hồi sinh nghĩa là gì (vì sao đáng một guard riêng): FE đọc số theo hợp đồng cũ trong khi
// backend đã ngừng gửi ⇒ badge im lặng về 0 hoặc mất dấu '+' của ca chạm trần — đúng lớp
// lỗi "cắt câm" mà CR-69 sinh ra để xoá, và lần này KHÔNG có test hành vi nào đỏ.
//
// Allowlist DUY NHẤT: `api/imm00.ts` — `totals_uncapped` là khoá KHÁC của endpoint KHÁC
// (trùng chữ, không trùng hợp đồng). Allowlist chỉ-GIẢM: thêm file vào đây là sai chiều.

import { describe, it, expect } from 'vitest'
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { join, relative, resolve } from 'node:path'
import { SRC, listFiles } from '@/test/paths'

// vitest chạy với cwd = frontend/ (jsdom không có URL scheme file).

/** Chính file guard này được phép nhắc tên đã nghỉ hưu — nó là nơi KHAI điều cấm. */
const SELF = 'guards/connectionsLegacyKeys.guard.test.ts'

/** File thuộc hợp đồng KHÁC mà chuỗi trùng chữ. */
const ALLOWLIST = new Set<string>(['api/imm00.ts'])

const FORBIDDEN: Array<{ re: RegExp; why: string }> = [
  // `\b` không đứng giữa `_` và `c` ⇒ `total_capped` (khoá HỢP LỆ) không khớp.
  { re: /\.capped\b/, why: '`capped` bool đã thay bằng `total_capped` (int 0|1)' },
  { re: /\bitem\.count\b/, why: '`count` đã gỡ — đọc `total`' },
  { re: /\bitem\.filters\b/, why: '`filters` đã gỡ — đọc `deep_link_filters`' },
  { re: /\bscalarFilters\b/, why: 'hàm chiếu `filters` legacy đã XOÁ' },
  { re: /\blinkFilters\b/, why: 'hàm đã XOÁ — `listTarget` là đường DUY NHẤT dựng deep-link' },
]

function walk(dir: string, out: string[] = []): string[] {
  for (const entry of readdirSync(dir)) {
    const p = join(dir, entry)
    if (statSync(p).isDirectory()) walk(p, out)
    else if (/\.(ts|vue)$/.test(entry)) out.push(p)
  }
  return out
}

describe('AC-CR-92 — khoá/hàm LEGACY của «Bản ghi liên quan» không được hồi sinh', () => {
  it('0 hit trên MỌI file src/**/*.{ts,vue} — kể cả *.test.ts và chú thích', () => {
    const offenders: string[] = []
    for (const file of walk(SRC)) {
      const rel = relative(SRC, file)
      if (rel === SELF || ALLOWLIST.has(rel)) continue
      readFileSync(file, 'utf8').split('\n').forEach((line, i) => {
        for (const { re, why } of FORBIDDEN) {
          if (re.test(line)) offenders.push(`${rel}:${i + 1} — ${why}`)
        }
      })
    }
    expect(offenders).toEqual([])
  })

  // Guard của guard: mẫu cấm phải KHÔNG bắt khoá hợp lệ, nếu không cả bộ test đỏ oan và
  // người sửa tiếp theo sẽ nới allowlist cho xong việc — tức tự tay mở lại cửa.
  it('mẫu cấm không bắt nhầm `total_capped` / `pagination.count`', () => {
    const [capped, count, filters] = FORBIDDEN.map(f => f.re)
    expect(capped.test('return item.total_capped === 1')).toBe(false)
    expect(capped.test('total_capped: 0,')).toBe(false)
    expect(capped.test('return item.capped ? n : 0')).toBe(true)
    expect(count.test('res.pagination.count')).toBe(false)
    expect(count.test('item.total ?? item.count')).toBe(true)
    expect(filters.test('item.deep_link_filters')).toBe(false)
    expect(filters.test('scalarFilters(item.filters)')).toBe(true)
  })

  // `api/connections.ts` là HỢP ĐỒNG: khai lại khoá đã gỡ ở đây là gốc của mọi lần hồi
  // sinh, nên chốt luôn TẬP khoá (so sánh tập, không `toContain`) — thêm khoá lén cũng đỏ.
  it('`ConnectionItem` khai ĐÚNG 10 khoá (AC-CR-105: `create_prefill` là khoá thứ 10)', () => {
    const iface = interfaceBody()
    const decls = [...iface.matchAll(/^ {2}([a-z_]+)\??:/gm)].map(m => m[1])
    expect([...decls].sort()).toEqual([
      'can_create', 'create_prefill', 'create_route_hint', 'deep_link_filters',
      'doctype', 'items', 'label_vi', 'total', 'total_capped', 'truncated',
    ])
    for (const dead of ['label', 'count', 'capped', 'filters']) {
      expect(decls, `khoá LEGACY '${dead}' được khai lại`).not.toContain(dead)
    }
  })

  // A7 (AC-CR-92) mở rộng thành A1 (AC-CR-105): **0 khoá optional**. Mỗi khoá optional là
  // một nhánh fallback, và mỗi nhánh fallback là một chỗ để hợp đồng lệch âm thầm.
  // `create_prefill` từng là ngoại lệ DUY NHẤT vì backend chưa cài; nay backend luôn phát
  // (`{}` khi không có gì điền sẵn) nên dấu `?` bị gỡ — tập ngoại lệ RỖNG, và thêm lại một
  // dấu `?` vào hợp đồng ô sẽ ĐỎ ngay ở đây.
  it('`ConnectionItem` có 0 khoá optional — tập ngoại lệ RỖNG', () => {
    const optional = [...interfaceBody().matchAll(/^ {2}([a-z_]+)\?:/gm)].map(m => m[1])
    expect(optional).toEqual([])
  })
})

/** Thân khai báo `ConnectionItem` (đọc nguồn, không import — đây là guard TĨNH). */
function interfaceBody(): string {
  const src = readFileSync(join(SRC, 'api/connections.ts'), 'utf8')
  const start = src.indexOf('export interface ConnectionItem')
  const end = src.indexOf('export interface ConnectionGroup')
  expect(start, 'không tìm thấy khai báo ConnectionItem').toBeGreaterThan(-1)
  expect(end).toBeGreaterThan(start)
  return src.slice(start, end)
}

// [K8] dân số: chốt tối thiểu cho thư mục guard này quét (SPEC §5.2 N6).
// Không có khối này thì thư mục bị dời ⇒ quét ra 0 file ⇒ mọi khẳng định
// "không tìm thấy vi phạm" thành đúng-rỗng-tuếch mà suite vẫn XANH.
describe('[K8] chốt dân số thư mục quét', () => {
  it('src/**/*.{vue,ts} còn ít nhất 600 file — nếu không, guard đã ngừng canh', () => {
    expect(listFiles(SRC, { ext: ['.ts', '.vue'], min: 600 }).length).toBeGreaterThanOrEqual(600)
  })
})
