// AC-UX baseline (2026-07-31) — Guard bất biến: bảng hiện trạng UI/UX ⇔ bảng route THẬT.
//
// Bối cảnh: `docs/ui-ux/00_AUDIT_HIEN_TRANG.md` là bản đồ nợ UI/UX của TOÀN BỘ FE và là
// đầu vào ghim cho các vòng sau. Tài liệu kiểu này mục rất nhanh: thêm 1 route mới mà quên
// bổ sung dòng ⇒ bảng "trông vẫn đúng" nhưng đã bỏ sót màn; sửa 1 ô thành ✅ mà đánh nhầm
// ký tự ⇒ thống kê §2 sai theo. Guard này khoá 3 bất biến đã cam kết trong tài liệu:
//
//   INV-UIAUDIT-1 (A1 — PHỦ KÍN ROUTE): mọi `path` trong bảng route sản xuất xuất hiện ĐÚNG
//     1 lần ở §3.1, và §3.1 không có dòng thừa (route đã xoá phải rời bảng).
//   INV-UIAUDIT-2 (A2 — RUBRIC 7 CỘT): mỗi dòng đủ 7 ô ∈ {✅,❌,n/a} (KHÔNG ô rỗng), cột
//     view file trỏ file CÓ THẬT trên đĩa (trừ dòng redirect), cột mức đau ∈ {P0,P1,P2}.
//   INV-UIAUDIT-3 (A5 — SỔ BACKLOG): AC-UX-* đánh số liên tục từ 001, không trùng, mỗi mục
//     có mức đau ∈ {P0,P1,P2} và vòng xử lý ∈ {2,3,4,5,6}.
//
// Guard đọc bảng route THẬT (`routes` từ ./index) chứ không regex file nguồn — nếu router
// đổi cách khai báo, guard vẫn bám đúng thứ đang chạy.
//
// Vòng 1 CHỈ đo & viết doc: test này là artifact duy nhất được thêm dưới frontend/src.
import { describe, it, expect } from 'vitest'
import { readFileSync, existsSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'
import type { RouteRecordRaw } from 'vue-router'
import { routes } from './index'

const HERE = dirname(fileURLToPath(import.meta.url))
// src/router → src → frontend → <repo root>
const REPO_ROOT = resolve(HERE, '../../..')
const DOC_PATH = resolve(REPO_ROOT, 'docs/ui-ux/00_AUDIT_HIEN_TRANG.md')

const CELL_VALUES = new Set(['✅', '❌', 'n/a'])
const PAIN_VALUES = new Set(['P0', 'P1', 'P2'])
// Vòng 6 (run-6) mở sổ AC-UX-059…063 ⇒ nới miền giá trị hợp lệ của cột «Vòng».
// Vòng xử lý hợp lệ — nới thêm mỗi khi factory mở vòng mới (vòng 7: AC-UX-064/065/066;
// vòng 8: AC-UX-067/068/069 — thanh tab SSoT `DetailTabBar`, xem docs/ui-ux/07;
// vòng 9: AC-UX-070 — guard adoption `ListPageShell`; vòng 10: AC-UX-071/072/073 —
// đóng hẳn adoption `DetailPageShell` 32/32 + SSoT `useDetailAccess` + chống 2 thanh
// tab, xem docs/ui-ux/03 §13).
// ĐÂY LÀ MIỀN GIÁ TRỊ, KHÔNG PHẢI ĐỘ CHẶT: mọi assert khác của file giữ nguyên xi
// (đánh số liên tục từ 001, không trùng, dòng «Tổng: N mục» khớp số đếm được).
const ROUND_VALUES = new Set(['2', '3', '4', '5', '6', '7', '8', '9', '10'])
const REDIRECT_CELL = '— *(redirect)*'

/** Mọi path trong bảng route sản xuất (đệ quy children — hiện chưa dùng nhưng đừng để hở). */
function allRoutePaths(list: readonly RouteRecordRaw[]): string[] {
  const out: string[] = []
  const stack: RouteRecordRaw[] = [...list]
  while (stack.length) {
    const r = stack.shift()!
    out.push(r.path)
    if (r.children) stack.push(...(r.children as RouteRecordRaw[]))
  }
  return out
}

const doc = readFileSync(DOC_PATH, 'utf-8')

/** Lấy khối văn bản giữa 2 mốc heading. */
function section(startMarker: string, endMarker: string): string {
  const a = doc.indexOf(startMarker)
  expect(a, `không tìm thấy mốc "${startMarker}" trong ${DOC_PATH}`).toBeGreaterThan(-1)
  const b = doc.indexOf(endMarker, a + startMarker.length)
  expect(b, `không tìm thấy mốc "${endMarker}" sau "${startMarker}"`).toBeGreaterThan(-1)
  return doc.slice(a, b)
}

/** Tách 1 dòng bảng markdown thành các ô đã trim (bỏ ô rỗng đầu/cuối do dấu | bao ngoài). */
function cellsOf(line: string): string[] {
  const parts = line.split('|')
  return parts.slice(1, parts.length - 1).map((c) => c.trim())
}

type AuditRow = {
  index: number
  path: string
  file: string
  criteria: string[]
  pain: string
  line: string
}

function parseAuditRows(): AuditRow[] {
  const body = section('### 3.1 Bảng đầy đủ', '### 3.2')
  const rows: AuditRow[] = []
  for (const line of body.split('\n')) {
    if (!line.startsWith('|')) continue
    const c = cellsOf(line)
    if (c.length !== 11) continue
    if (c[0] === '#' || /^-+$/.test(c[0])) continue // header + separator
    if (!/^\d+$/.test(c[0])) continue
    rows.push({
      index: Number(c[0]),
      path: c[1].replace(/^`|`$/g, ''),
      file: c[2],
      criteria: c.slice(3, 10),
      pain: c[10],
      line,
    })
  }
  return rows
}

const auditRows = parseAuditRows()
const routePaths = allRoutePaths(routes)

describe('INV-UIAUDIT-1 (A1) — bảng §3.1 phủ kín bảng route thật', () => {
  it('bảng đọc được và không rỗng', () => {
    expect(auditRows.length).toBeGreaterThan(0)
  })

  it('mỗi route xuất hiện ĐÚNG 1 lần trong bảng', () => {
    const count = new Map<string, number>()
    for (const r of auditRows) count.set(r.path, (count.get(r.path) ?? 0) + 1)
    const missing = routePaths.filter((p) => !count.has(p))
    const duplicated = [...count.entries()].filter(([, n]) => n > 1).map(([p, n]) => `${p} ×${n}`)
    expect(
      missing,
      `route có trong router nhưng THIẾU trong docs/ui-ux/00_AUDIT_HIEN_TRANG.md §3.1 — ` +
        `thêm route mới thì phải bổ sung dòng (kèm 7 ô + mức đau)`,
    ).toEqual([])
    expect(duplicated, 'route bị lặp dòng trong §3.1').toEqual([])
  })

  it('bảng không có dòng thừa (route đã xoá phải rời bảng)', () => {
    const known = new Set(routePaths)
    const extra = auditRows.filter((r) => !known.has(r.path)).map((r) => r.path)
    expect(extra, 'dòng trong §3.1 không còn route tương ứng trong router/index.ts').toEqual([])
  })

  it('số dòng bảng == số route thật', () => {
    expect(auditRows.length).toBe(routePaths.length)
  })

  it('§2.2 công bố tổng số route khớp số dòng đã đếm', () => {
    const m = doc.match(/## §2\. Số đo tổng quan[\s\S]*?Phân bố mức đau \((\d+) route\)/)
    expect(m, 'không đọc được tổng số route công bố ở §2.2').not.toBeNull()
    expect(Number(m![1])).toBe(auditRows.length)
  })
})

describe('INV-UIAUDIT-2 (A2) — rubric 7 cột, không ô rỗng', () => {
  it('mọi ô tiêu chí ∈ {✅, ❌, n/a}', () => {
    const bad: string[] = []
    for (const r of auditRows) {
      r.criteria.forEach((cell, i) => {
        if (!CELL_VALUES.has(cell)) bad.push(`${r.path} · cột ${i + 1} = "${cell}"`)
      })
    }
    expect(bad, 'ô rỗng hoặc giá trị lạ — mỗi ô phải là ✅ / ❌ / n/a').toEqual([])
  })

  it('mỗi dòng có đúng 7 ô tiêu chí', () => {
    const bad = auditRows.filter((r) => r.criteria.length !== 7).map((r) => r.path)
    expect(bad).toEqual([])
  })

  it('cột mức đau ∈ {P0, P1, P2}', () => {
    const bad = auditRows.filter((r) => !PAIN_VALUES.has(r.pain)).map((r) => `${r.path} = "${r.pain}"`)
    expect(bad).toEqual([])
  })

  it('cột view file trỏ file CÓ THẬT trên đĩa (trừ dòng redirect)', () => {
    const missing: string[] = []
    for (const r of auditRows) {
      if (r.file === REDIRECT_CELL) continue
      const rel = r.file.replace(/^`|`$/g, '')
      if (!rel.endsWith('.vue') || !existsSync(resolve(REPO_ROOT, rel))) {
        missing.push(`${r.path} → ${rel}`)
      }
    }
    expect(missing, 'đường dẫn view trong §3.1 không tồn tại trên đĩa').toEqual([])
  })

  it('dòng redirect có cả 7 ô = n/a (không có giao diện riêng để chấm)', () => {
    const bad = auditRows
      .filter((r) => r.file === REDIRECT_CELL && r.criteria.some((c) => c !== 'n/a'))
      .map((r) => r.path)
    expect(bad).toEqual([])
  })

  it('mỗi dòng có view thật phải chấm ít nhất 1 ô KHÁC n/a (không được n/a toàn dòng cho có)', () => {
    const bad = auditRows
      .filter((r) => r.file !== REDIRECT_CELL && r.criteria.every((c) => c === 'n/a'))
      .map((r) => r.path)
    expect(bad).toEqual([])
  })
})

describe('INV-UIAUDIT-3 (A5) — sổ backlog AC-UX liên tục, không trùng', () => {
  const body = section('## §6. Sổ backlog AC-UX', '## §7.')
  const entries: { code: string; num: number; pain: string; round: string }[] = []
  for (const line of body.split('\n')) {
    if (!line.startsWith('|')) continue
    const c = cellsOf(line)
    if (c.length !== 6) continue
    const m = c[0].match(/AC-UX-(\d{3})/)
    if (!m) continue
    entries.push({ code: `AC-UX-${m[1]}`, num: Number(m[1]), pain: c[3], round: c[4] })
  }

  it('sổ có ít nhất 12 mục', () => {
    expect(entries.length).toBeGreaterThanOrEqual(12)
  })

  it('đánh số liên tục từ 001, không trùng, không nhảy cóc', () => {
    const nums = entries.map((e) => e.num)
    expect(nums, 'AC-UX phải bắt đầu từ 001 và tăng đều 1').toEqual(
      Array.from({ length: nums.length }, (_, i) => i + 1),
    )
  })

  it('mỗi mục có mức đau ∈ {P0,P1,P2} và vòng xử lý ∈ {2,3,4,5,6}', () => {
    const badPain = entries.filter((e) => !PAIN_VALUES.has(e.pain)).map((e) => `${e.code}=${e.pain}`)
    // vòng có thể ghi "2–3" (khoảng) — chấp nhận nếu MỌI số trong ô đều hợp lệ.
    const badRound = entries
      .filter((e) => {
        const nums = e.round.match(/\d+/g) ?? []
        return nums.length === 0 || nums.some((n) => !ROUND_VALUES.has(n))
      })
      .map((e) => `${e.code}=${e.round}`)
    expect(badPain).toEqual([])
    expect(badRound).toEqual([])
  })

  it('§6 công bố tổng số mục khớp số dòng đã đếm', () => {
    const m = body.match(/\*\*Tổng: (\d+) mục/)
    expect(m, 'không đọc được dòng "Tổng: N mục" ở cuối §6').not.toBeNull()
    expect(Number(m![1])).toBe(entries.length)
  })
})
