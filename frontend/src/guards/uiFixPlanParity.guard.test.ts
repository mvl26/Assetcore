// Guard parity — phương án sửa TOÀN BỘ (docs/ui-ux/04 §12, INV-UX5PLAN-1..8).
//
// Vấn đề nó chặn: một tài liệu tên là «phương án sửa toàn bộ» mà bỏ sót 1 màn thì không
// còn là «toàn bộ» — và sai sót kiểu đó không ai nhìn ra bằng mắt trên bảng 135 dòng.
// Guard đọc BA nguồn và bắt chúng khớp nhau:
//   (1) bảng route THẬT (`routes` từ ./index — không regex file nguồn),
//   (2) bảng hiện trạng `00_AUDIT_HIEN_TRANG.md §3.1`,
//   (3) bảng phân hoạch `04_PHUONG_AN_SUA_TOAN_BO.md §11`.
//
// CỐ Ý KHÔNG cross-check cột «Đau» giữa (2) và (3): hai bảng lệch 14 ô có chủ đích
// (ADR-UX-10 — §11 lấy theo BỘ DÒ, §3.1 là bảng tay). Assert bằng nhau sẽ đỏ oan.
import { describe, it, expect } from 'vitest'
import { readFileSync, existsSync } from 'node:fs'
import { resolve } from 'node:path'
import { REPO_ROOT } from '@/test/paths'
import type { RouteRecordRaw } from 'vue-router'
import { routes } from '@/router/index'

// src/router → src → frontend → <repo root>
const AUDIT_PATH = resolve(REPO_ROOT, 'docs/ui-ux/00_AUDIT_HIEN_TRANG.md')
const PLAN_PATH = resolve(REPO_ROOT, 'docs/ui-ux/04_PHUONG_AN_SUA_TOAN_BO.md')

const GROUPS = ['Danh sách', 'Chi tiết', 'Biểu mẫu', 'Bảng điều khiển', 'Khác'] as const
const WAVES = new Set(['A', 'B', 'C', 'D', 'E'])
const PAINS = new Set(['P0', 'P1', 'P2'])
const REDIRECT_CELL = '— *(redirect)*'

const auditDoc = readFileSync(AUDIT_PATH, 'utf-8')
const planDoc = readFileSync(PLAN_PATH, 'utf-8')

/** Khuôn parse dùng lại nguyên `uiAuditDocParity.test.ts` — KHÔNG viết bộ parse thứ hai. */
function section(doc: string, startMarker: string, endMarker: string): string {
  const a = doc.indexOf(startMarker)
  expect(a, `không tìm thấy mốc "${startMarker}"`).toBeGreaterThan(-1)
  const b = doc.indexOf(endMarker, a + startMarker.length)
  expect(b, `không tìm thấy mốc "${endMarker}" sau "${startMarker}"`).toBeGreaterThan(-1)
  return doc.slice(a, b)
}

function cellsOf(line: string): string[] {
  const parts = line.split('|')
  return parts.slice(1, parts.length - 1).map((c) => c.trim())
}

const unquote = (s: string): string => s.replace(/^`|`$/g, '')

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

type PlanRow = { index: number; path: string; file: string; group: string; wave: string; pain: string }

function parsePlanRows(): PlanRow[] {
  const body = section(planDoc, '## §11.', '## §12.')
  const rows: PlanRow[] = []
  for (const line of body.split('\n')) {
    if (!line.startsWith('|')) continue
    const c = cellsOf(line)
    if (c.length !== 7) continue
    if (!/^\d+$/.test(c[0])) continue
    rows.push({
      index: Number(c[0]),
      path: unquote(c[1]),
      file: unquote(c[2]),
      group: c[3],
      wave: c[4],
      pain: c[5],
    })
  }
  return rows
}

type AuditRow = { path: string; file: string }

function parseAuditRows(): AuditRow[] {
  const body = section(auditDoc, '### 3.1 Bảng đầy đủ', '### 3.2')
  const rows: AuditRow[] = []
  for (const line of body.split('\n')) {
    if (!line.startsWith('|')) continue
    const c = cellsOf(line)
    if (c.length !== 11) continue
    if (!/^\d+$/.test(c[0])) continue
    rows.push({ path: unquote(c[1]), file: c[2] })
  }
  return rows
}

const planRows = parsePlanRows()
const auditRows = parseAuditRows()
const auditWithView = auditRows.filter((r) => r.file !== REDIRECT_CELL)
const routePaths = new Set(allRoutePaths(routes))

describe('INV-UX5PLAN-1/2 — §11 phủ kín 135 route có view, không dòng thừa', () => {
  it('bảng §11 đọc được và không rỗng', () => {
    expect(planRows.length).toBeGreaterThan(0)
    expect(auditWithView.length).toBeGreaterThan(0)
  })

  it('0 route MỒ CÔI: mọi route có view trong 00 §3.1 xuất hiện ĐÚNG 1 lần ở §11', () => {
    const count = new Map<string, number>()
    for (const r of planRows) count.set(r.path, (count.get(r.path) ?? 0) + 1)
    const orphans = auditWithView.filter((r) => !count.has(r.path)).map((r) => r.path)
    const duplicated = [...count.entries()].filter(([, n]) => n > 1).map(([p, n]) => `${p} ×${n}`)
    expect(
      orphans,
      'route có giao diện nhưng KHÔNG thuộc nhóm nào trong §11 — "phương án sửa toàn bộ" ' +
        'mà bỏ sót màn thì không còn là toàn bộ',
    ).toEqual([])
    expect(duplicated, 'route bị xếp vào 2 nhóm (dòng lặp) trong §11').toEqual([])
  })

  it('§11 không có dòng thừa (mọi path phải là route thật, và phải có view)', () => {
    const withView = new Set(auditWithView.map((r) => r.path))
    const notRoute = planRows.filter((r) => !routePaths.has(r.path)).map((r) => r.path)
    const notView = planRows.filter((r) => routePaths.has(r.path) && !withView.has(r.path)).map((r) => r.path)
    expect(notRoute, 'dòng §11 không còn route tương ứng trong router/index.ts').toEqual([])
    expect(notView, 'dòng §11 trỏ route chuyển hướng (không có giao diện riêng)').toEqual([])
  })

  it('số dòng §11 == số route có view (135) và đánh số liên tục từ 1', () => {
    expect(planRows.length).toBe(auditWithView.length)
    expect(planRows.map((r) => r.index)).toEqual(
      Array.from({ length: planRows.length }, (_, i) => i + 1),
    )
  })
})

describe('INV-UX5PLAN-3/4 — giá trị hợp lệ + luật đợt A ⟺ P0', () => {
  it('cột Nhóm ∈ 5 khuôn · Đợt ∈ {A..E} · Đau ∈ {P0,P1,P2}', () => {
    const groupSet = new Set<string>(GROUPS)
    const bad: string[] = []
    for (const r of planRows) {
      if (!groupSet.has(r.group)) bad.push(`${r.path} · Nhóm="${r.group}"`)
      if (!WAVES.has(r.wave)) bad.push(`${r.path} · Đợt="${r.wave}"`)
      if (!PAINS.has(r.pain)) bad.push(`${r.path} · Đau="${r.pain}"`)
    }
    expect(bad, 'ô rỗng hoặc giá trị lạ trong §11').toEqual([])
  })

  it('Đợt == "A" ⟺ Đau == "P0" (kiểm 2 CHIỀU — luật §9.3 phải là luật, không phải mô tả)', () => {
    const aButNotP0 = planRows.filter((r) => r.wave === 'A' && r.pain !== 'P0').map((r) => r.path)
    const p0ButNotA = planRows.filter((r) => r.pain === 'P0' && r.wave !== 'A').map((r) => r.path)
    expect(aButNotP0, 'route xếp đợt A nhưng mức đau không phải P0').toEqual([])
    expect(p0ButNotA, 'route P0 nhưng không nằm ở làn ưu tiên (đợt A)').toEqual([])
  })
})

describe('INV-UX5PLAN-5/6 — cột view file khớp 00 §3.1 và có thật trên đĩa', () => {
  it('view file của mỗi route khớp ĐÚNG ô tương ứng ở 00 §3.1 (135/135)', () => {
    const auditFile = new Map(auditWithView.map((r) => [r.path, unquote(r.file)]))
    const mismatch = planRows
      .filter((r) => auditFile.get(r.path) !== r.file)
      .map((r) => `${r.path}: §11="${r.file}" vs 00§3.1="${auditFile.get(r.path)}"`)
    expect(mismatch, '2 bảng phải cùng trỏ 1 file view').toEqual([])
  })

  it('view file trỏ file CÓ THẬT trên đĩa', () => {
    const missing = planRows
      .filter((r) => !r.file.endsWith('.vue') || !existsSync(resolve(REPO_ROOT, r.file)))
      .map((r) => `${r.path} → ${r.file}`)
    expect(missing, 'đường dẫn view chết trong §11').toEqual([])
  })
})

describe('INV-UX5PLAN-7 — §10 có đủ 5 nhóm × (ước lượng + ưu tiên + DoD)', () => {
  const headings = [...planDoc.matchAll(/^### 10\.(\d) Nhóm «([^»]+)»/gm)].map((m) => ({
    num: Number(m[1]),
    name: m[2],
  }))

  it('đúng 5 mục §10.1…§10.5, tên nhóm trùng khít tập giá trị cột Nhóm', () => {
    expect(headings.map((h) => h.num)).toEqual([1, 2, 3, 4, 5])
    expect(new Set(headings.map((h) => h.name))).toEqual(new Set<string>(GROUPS))
    // Tập nhóm dùng thật trong bảng == tập nhóm có mục mô tả (không nhóm nào bị bỏ quên).
    expect(new Set(planRows.map((r) => r.group))).toEqual(new Set(headings.map((h) => h.name)))
  })

  it('mỗi nhóm có đủ 3 dòng: Ước lượng · Thứ tự ưu tiên · DoD', () => {
    const missing: string[] = []
    for (let i = 1; i <= 5; i += 1) {
      const end = i === 5 ? '### 10.6' : `### 10.${i + 1}`
      const body = section(planDoc, `### 10.${i} Nhóm «`, end)
      for (const key of ['- **Ước lượng**', '- **Thứ tự ưu tiên**', '- **DoD**']) {
        if (!body.includes(key)) missing.push(`§10.${i} thiếu "${key}"`)
      }
    }
    expect(missing).toEqual([])
  })
})

describe('INV-UX5PLAN-8 — dòng tổng khớp phân bố đếm được', () => {
  const totals = planDoc.match(
    /\*\*Tổng: (\d+) route có view — Danh sách (\d+) · Chi tiết (\d+) · Biểu mẫu (\d+) · Bảng điều khiển (\d+) · Khác (\d+)\. Đợt A (\d+) · B (\d+) · C (\d+) · D (\d+) · E (\d+)\.\*\*/,
  )

  it('đọc được dòng tổng ở cuối §11', () => {
    expect(totals, 'thiếu dòng "**Tổng: N route có view — …**" ở cuối §11').not.toBeNull()
  })

  it('tổng + phân bố nhóm khớp số dòng đếm được', () => {
    const n = totals!.map(Number)
    expect(n[1]).toBe(planRows.length)
    const byGroup = (g: string): number => planRows.filter((r) => r.group === g).length
    expect([byGroup('Danh sách'), byGroup('Chi tiết'), byGroup('Biểu mẫu'), byGroup('Bảng điều khiển'), byGroup('Khác')])
      .toEqual([n[2], n[3], n[4], n[5], n[6]])
  })

  it('phân bố đợt khớp số dòng đếm được', () => {
    const n = totals!.map(Number)
    const byWave = (w: string): number => planRows.filter((r) => r.wave === w).length
    expect([byWave('A'), byWave('B'), byWave('C'), byWave('D'), byWave('E')])
      .toEqual([n[7], n[8], n[9], n[10], n[11]])
  })
})
