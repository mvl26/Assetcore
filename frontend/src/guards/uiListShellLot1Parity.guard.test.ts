// Guard parity — adoption `ListPageShell` (AC-UX-047), spec `docs/ui-ux/02_LIST_PAGE_SHELL.md §12` (lô 1) + `§13` (lô 2).
//
// Vấn đề nó chặn — «doc nói dối về đĩa», và «guard nói dối về doc»:
//   1) Vòng 3 áp `ListPageShell` cho 4 màn thật nhưng QUÊN lật ô «Lỗi+Thử lại» ở `00 §3.1` ⇒ tài liệu ĐO
//      khẳng định sai về 4 route suốt 3 ngày, không ai thấy bằng mắt trên bảng 148 dòng.
//   2) Bản ĐẦU của guard này (lô 1) chỉ ép `token == 89 − số ô lô 1 đã lật` — tức **so tài liệu với chính
//      tài liệu**. Mốc 89 đo 2026-08-03; ngay hôm sau lô 1 lớp CHI TIẾT (`AC-UX-048`, `DetailPageShell`)
//      đã trả nợ thêm 8 route mà phép trừ không hề biết ⇒ ba con số cùng "xanh" mà lệch nhau:
//      bảng tay §3.1 = 64 · bộ dò = 69 · token = 77. Lệch 15 ô giữa §3.1 và bộ dò đi CẢ HAI CHIỀU
//      (10 ô doc lạc quan hơn đĩa, 5 ô doc bi quan hơn đĩa) ⇒ chỉ ép TỔNG cũng không bắt được.
//
// Cách chữa (ADR-UX-22, `00 §9`): **mọi con số neo vào BỘ DÒ đo LIVE**, không vào phép trừ tay.
// Test tự chạy `node frontend/scripts/ui-audit-inventory.mjs --json` — một cài đặt đo duy nhất, không
// có "bộ parse thứ hai" để lệch. Chi phí 0,15 s/lượt, chấp nhận.
//
// Bất biến:
//   INV-UX3L-1 — sổ lô 1 (`02 §12.2`) ĐÚNG 12 dòng · sổ lô 2 (`02 §13.2`) ĐÚNG 12 dòng · sổ lô 3
//                (`02 §14.2`) ĐÚNG 12 dòng; mã TC liên tục TC-UX3-11…22, 23…34, 35…46, không trùng.
//   INV-UX3L-2 — mọi route trong 3 sổ là route THẬT; view file có trên đĩa và TRÙNG ô view file ở `00 §3.1`.
//   INV-UX3L-3 — parity 2 CHIỀU cho 24 route lô 1+2: `view import ListPageShell` ⟺ ô «Lỗi+Thử lại» = ✅.
//                ⚠️ LÔ 3 KHÔNG vào phép ⟺ này: cả 12 route lô 3 đã ✅ SẴN từ trước khi áp khuôn (chúng có
//                nút «Thử lại», chỉ thiếu tính LOẠI TRỪ) ⇒ chiều "✅ ⇒ phải import" sai với chúng. Adoption
//                của lô 3 được khoá bằng guard riêng `views/listShellAdoption.test.ts` (AC-UX-070, ADR-UX-23);
//                ở đây chỉ ép ô của 12 route đó **giữ ✅** (INV-UX3L-8).
//   INV-UX3L-4 — view đã áp khuôn ⇒ PHẢI có file `*ListStates.test.ts` khai ở `§12.6`/`§13.6`/`§14.6`.
//   INV-UX3L-5 — token `[NO-CON=N]` (`00 §6`) == số ô ❌ cột «Lỗi+Thử lại» do BỘ DÒ đo LIVE (KHÔNG phép trừ).
//   INV-UX3L-6 — parity TỪNG Ô cột «Lỗi+Thử lại» giữa `00 §3.1` và bộ dò trên CẢ 148 dòng.
//   INV-UX3L-7 — chiều toàn cục: MỌI view `.vue` import `ListPageShell` ⇒ ô route của nó ở `§3.1` = ✅.
//
//   INV-UX3L-8 — 12 route lô 3 (`02 §14.2`): ô «Lỗi+Thử lại» phải GIỮ ✅ ở cả hai đầu (trước và sau khi áp
//                khuôn) — chống ca "áp khuôn xong làm mất lối nạp lại".
//
// Prove-It (A6): sửa tay 1 ô cột này ở §3.1 ⇒ INV-UX3L-6 ĐỎ. Gỡ 1 `import ListPageShell` ⇒ INV-UX3L-3
// (route trong sổ) hoặc INV-UX3L-6/7 ĐỎ. Xanh ở CẢ HAI đầu vòng: trước khi FE land lô 3 (28/40 adopter)
// và sau khi FE land (40/40); token NO-CON=57 KHÔNG đổi ở lô 3 (lô 3 vô hình với bộ dò — ADR-UX-23).
import { describe, it, expect } from 'vitest'
import { readFileSync, existsSync, readdirSync, statSync } from 'node:fs'
import { execFileSync } from 'node:child_process'
import { resolve, relative } from 'node:path'
import { REPO_ROOT, VIEWS, listFiles } from '@/test/paths'
import type { RouteRecordRaw } from 'vue-router'
import { routes } from '@/router/index'

// src/router → src → frontend → <repo root>
const AUDIT_PATH = resolve(REPO_ROOT, 'docs/ui-ux/00_AUDIT_HIEN_TRANG.md')
const SPEC_PATH = resolve(REPO_ROOT, 'docs/ui-ux/02_LIST_PAGE_SHELL.md')
const DETECTOR = resolve(REPO_ROOT, 'frontend/scripts/ui-audit-inventory.mjs')
const VIEWS_DIR = VIEWS

/** 12 route lô 1 — chốt bởi PM/BA; hardcode để việc đổi phạm vi là TAMPER-EVIDENT. */
const LOT1_ROUTES = [
  '/stock-movements',
  '/asset-transfers',
  '/warehouses',
  '/device-models',
  '/suppliers',
  '/spare-parts',
  '/documents/requests',
  '/pm/templates',
  '/cm/firmware',
  '/sla-policies',
  '/incidents/list',
  '/rca',
] as const

/** 12 route lô 2 — họ `*ListView` ĐÓNG HẲN (`02 §13.2`). */
const LOT2_ROUTES = [
  '/assets',
  '/calibration',
  '/calibration/schedules',
  '/capas',
  '/compliance/rules',
  '/compliance/findings',
  '/compliance/audits',
  '/compliance/mr',
  '/tech-specs',
  '/vendor-evaluations',
  '/approved-vendors',
  '/procurement-decisions',
] as const

/** 12 route lô 3 — họ `*ListView` đóng theo phép đo ADOPTION (`02 §14.2`, ADR-UX-23). */
const LOT3_ROUTES = [
  '/audit-trail',
  '/cm/work-orders',
  '/service-contracts',
  '/decommissions',
  '/inventory/cycle-counts',
  '/pm/work-orders',
  '/pm/schedules',
  '/needs-requests',
  '/commissioning',
  '/imm06/programs',
  '/imm06/sessions',
  '/imm06/competencies',
] as const

const auditDoc = readFileSync(AUDIT_PATH, 'utf-8')
const specDoc = readFileSync(SPEC_PATH, 'utf-8')

// ── Bộ dò: MỘT lần chạy, dùng cho mọi phép so ────────────────────────────────
type DetectorRow = {
  index: number
  path: string
  file: string | null
  kind: string
  cells?: Record<string, string>
}
const detectorRows: DetectorRow[] = JSON.parse(
  execFileSync('node', [DETECTOR, '--json'], { maxBuffer: 1e8 }).toString(),
).rows
/** Ô «Lỗi+Thử lại» theo bộ dò; dòng redirect không có tiêu chí ⇒ 'n/a' (khớp cách ghi của §3.1). */
const detectorErrorCell = (r: DetectorRow): string => (r.kind === 'view' ? (r.cells?.error ?? 'n/a') : 'n/a')
const detectorDebt = detectorRows.filter((r) => detectorErrorCell(r) === '❌').length

/** Khuôn parse dùng lại `uiAuditDocParity.test.ts` — KHÔNG viết bộ parse thứ hai. */
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

type LedgerRow = { index: number; path: string; file: string; tc: string; lot: 1 | 2 | 3 }

/** Sổ lô — `02 §12.2` / `§13.2` / `§14.2` (7 cột: # · Route · View file · Hàm nạp · Nguồn lỗi · Module mock · TC). */
function parseLedger(startMarker: string, endMarker: string, lot: 1 | 2 | 3): LedgerRow[] {
  const body = section(specDoc, startMarker, endMarker)
  const rows: LedgerRow[] = []
  for (const line of body.split('\n')) {
    if (!line.startsWith('|')) continue
    const c = cellsOf(line)
    if (c.length !== 7) continue
    if (!/^\d+$/.test(c[0])) continue
    rows.push({ index: Number(c[0]), path: unquote(c[1]), file: unquote(c[2]), tc: unquote(c[6]), lot })
  }
  return rows
}

/** Bảng file test trạng thái — `02 §12.6` / `§13.6` (2 cột: TC · file). */
function parseTestPlan(startMarker: string): Map<string, string> {
  const body = section(specDoc, startMarker, '**Sub-case bắt buộc')
  const out = new Map<string, string>()
  for (const line of body.split('\n')) {
    if (!line.startsWith('|')) continue
    const c = cellsOf(line)
    if (c.length !== 2) continue
    const tc = unquote(c[0])
    if (!/^TC-UX3-\d+$/.test(tc)) continue
    out.set(tc, unquote(c[1]))
  }
  return out
}

type AuditRow = { index: number; path: string; file: string; errorCell: string }

/** Bảng hiện trạng — `00 §3.1` (11 cột; ô «Lỗi+Thử lại» là tiêu chí thứ 4 ⇒ chỉ số 6). */
function parseAuditRows(): AuditRow[] {
  const body = section(auditDoc, '### 3.1 Bảng đầy đủ', '### 3.2')
  const rows: AuditRow[] = []
  for (const line of body.split('\n')) {
    if (!line.startsWith('|')) continue
    const c = cellsOf(line)
    if (c.length !== 11) continue
    if (!/^\d+$/.test(c[0])) continue
    rows.push({ index: Number(c[0]), path: unquote(c[1]), file: unquote(c[2]), errorCell: c[6] })
  }
  return rows
}

const lot1 = parseLedger('### 12.2 Sổ lô 1', '### 12.3', 1)
const lot2 = parseLedger('### 13.2 Sổ lô 2', '### 13.3', 2)
const lot3 = parseLedger('### 14.2 Sổ lô 3', '### 14.3', 3)
/** Tập vào phép ⟺ 2 chiều của INV-UX3L-3 — CHỈ lô 1+2 (xem chú thích đầu file). */
const ledger = [...lot1, ...lot2]
/** Cả 3 lô — dùng cho các bất biến không phụ thuộc chiều "✅ ⇒ phải import". */
const allLots = [...lot1, ...lot2, ...lot3]
const testPlan = new Map([
  ...parseTestPlan('### 12.6 Bộ test'),
  ...parseTestPlan('### 13.6 Bộ test'),
  ...parseTestPlan('### 14.6 Bộ test'),
])
const auditRows = parseAuditRows()
const auditByPath = new Map(auditRows.map((r) => [r.path, r]))
const routePaths = new Set(allRoutePaths(routes))

/** View đã áp khuôn? Đọc ĐĨA, không tin tài liệu. */
const SHELL_IMPORT = /from\s+'@\/components\/ui\/ListPageShell\.vue'/
function importsShell(relFile: string): boolean {
  const abs = resolve(REPO_ROOT, relFile)
  if (!existsSync(abs)) return false
  return SHELL_IMPORT.test(readFileSync(abs, 'utf-8'))
}

/** Mọi file `.vue` dưới `src/views` (đệ quy) — để ép chiều toàn cục INV-UX3L-7. */
function allViewFiles(dir = VIEWS_DIR): string[] {
  const out: string[] = []
  for (const name of readdirSync(dir)) {
    const abs = resolve(dir, name)
    if (statSync(abs).isDirectory()) out.push(...allViewFiles(abs))
    else if (name.endsWith('.vue')) out.push(abs)
  }
  return out
}

describe('INV-UX3L-1 — sổ lô 1 + lô 2 + lô 3: mỗi lô đúng 12 route, mã TC liên tục', () => {
  it('sổ lô 1 có ĐÚNG 12 dòng, đánh số 1…12, trùng khít 12 route đã chốt', () => {
    expect(lot1.length, 'đổi phạm vi lô = đổi cam kết với PM').toBe(12)
    expect(lot1.map((r) => r.index)).toEqual(Array.from({ length: 12 }, (_, i) => i + 1))
    expect(lot1.map((r) => r.path)).toEqual([...LOT1_ROUTES])
  })

  it('sổ lô 2 có ĐÚNG 12 dòng, đánh số 1…12, trùng khít 12 route danh sách CUỐI CÙNG', () => {
    expect(lot2.length, 'lô 2 phải đóng hẳn họ *ListView — không hơn, không kém').toBe(12)
    expect(lot2.map((r) => r.index)).toEqual(Array.from({ length: 12 }, (_, i) => i + 1))
    expect(lot2.map((r) => r.path)).toEqual([...LOT2_ROUTES])
  })

  it('sổ lô 3 có ĐÚNG 12 dòng, đánh số 1…12, trùng khít 12 route danh sách CÒN LẠI', () => {
    expect(lot3.length, 'lô 3 đóng adoption họ *ListView — không hơn, không kém').toBe(12)
    expect(lot3.map((r) => r.index)).toEqual(Array.from({ length: 12 }, (_, i) => i + 1))
    expect(lot3.map((r) => r.path)).toEqual([...LOT3_ROUTES])
  })

  it('mã TC liên tục TC-UX3-11…22 (lô 1), 23…34 (lô 2), 35…46 (lô 3), không trùng', () => {
    expect(lot1.map((r) => r.tc)).toEqual(Array.from({ length: 12 }, (_, i) => `TC-UX3-${11 + i}`))
    expect(lot2.map((r) => r.tc)).toEqual(Array.from({ length: 12 }, (_, i) => `TC-UX3-${23 + i}`))
    expect(lot3.map((r) => r.tc)).toEqual(Array.from({ length: 12 }, (_, i) => `TC-UX3-${35 + i}`))
    expect(new Set(allLots.map((r) => r.tc)).size).toBe(36)
  })

  it('§12.6 + §13.6 + §14.6 khai đủ 36 file test, khớp mã TC của 3 sổ', () => {
    expect([...testPlan.keys()].sort()).toEqual([...allLots.map((r) => r.tc)].sort())
    // SPEC §5.1: `<Nguồn>.<khiaCanh>.test.ts` — nguồn là `*ListView.vue`/`*DetailView.vue`.
    const bad = [...testPlan.values()].filter((f) => !/(List|Detail)View\.states\.test\.ts$/.test(f))
    expect(bad, 'file test trạng thái phải đặt tên <Nguồn>.states.test.ts').toEqual([])
  })
})

describe('INV-UX3L-2 — sổ ⇄ router ⇄ bảng hiện trạng 00 §3.1', () => {
  it('mọi route trong sổ là route THẬT trong router/index.ts', () => {
    expect(allLots.filter((r) => !routePaths.has(r.path)).map((r) => r.path)).toEqual([])
  })

  it('view file tồn tại trên đĩa', () => {
    const missing = allLots
      .filter((r) => !r.file.endsWith('.vue') || !existsSync(resolve(REPO_ROOT, r.file)))
      .map((r) => `${r.path} → ${r.file}`)
    expect(missing, 'đường dẫn view chết trong sổ lô').toEqual([])
  })

  it('view file trong sổ TRÙNG ô view file tương ứng ở 00 §3.1', () => {
    const mismatch = allLots
      .filter((r) => auditByPath.get(r.path)?.file !== r.file)
      .map((r) => `${r.path}: sổ="${r.file}" vs 00§3.1="${auditByPath.get(r.path)?.file}"`)
    expect(mismatch, '2 tài liệu phải cùng trỏ 1 file view').toEqual([])
  })
})

describe('INV-UX3L-3 — parity 2 CHIỀU: import khuôn ⟺ ô «Lỗi+Thử lại» = ✅', () => {
  it('không màn nào áp khuôn mà doc còn ❌, và không ô ✅ nào không có khuôn đứng sau (24 route)', () => {
    const codeNotDoc: string[] = []
    const docNotCode: string[] = []
    for (const r of ledger) {
      const applied = importsShell(r.file)
      const flipped = auditByPath.get(r.path)?.errorCell === '✅'
      if (applied && !flipped) codeNotDoc.push(`lô ${r.lot} ${r.path}`)
      if (flipped && !applied) docNotCode.push(`lô ${r.lot} ${r.path}`)
    }
    expect(
      codeNotDoc,
      'view ĐÃ dùng ListPageShell nhưng ô «Lỗi+Thử lại» ở 00 §3.1 vẫn ❌ — mã và doc phải land CÙNG lượt (ADR-UX-11)',
    ).toEqual([])
    expect(
      docNotCode,
      'ô ở 00 §3.1 đã lật ✅ nhưng view KHÔNG import ListPageShell — tài liệu ĐO đang nói sai về đĩa',
    ).toEqual([])
  })
})

describe('INV-UX3L-4 — màn đã áp khuôn phải có test trạng thái', () => {
  it('mỗi view đã import ListPageShell có file *ListStates.test.ts khai ở §12.6/§13.6/§14.6', () => {
    const missing: string[] = []
    for (const r of allLots) {
      if (!importsShell(r.file)) continue
      const testFile = testPlan.get(r.tc)
      if (!testFile || !existsSync(resolve(REPO_ROOT, testFile))) {
        missing.push(`${r.path} → ${testFile ?? '(chưa khai)'}`)
      }
    }
    expect(missing, 'adoption không kèm test trạng thái = chưa chứng minh được 4 trạng thái loại trừ').toEqual([])
  })
})

describe('INV-UX3L-5 — token [NO-CON=N] neo vào BỘ DÒ đo LIVE (ADR-UX-22)', () => {
  // CHỈ đếm token mang CON SỐ: `[NO-CON=69]`. Dạng giữ chỗ `[NO-CON=N]` trong văn xuôi/ADR là mô tả
  // cơ chế, không phải nguồn số ⇒ không tính. Hai nơi ghi SỐ = hai nguồn sự thật (đúng lỗi AC-UX-031).
  const tokenLines = auditDoc.split('\n').filter((l) => /\[NO-CON=\d+\]/.test(l))
  const m = tokenLines[0]?.match(/\[NO-CON=(\d+)\]/) ?? null

  it('đọc được ĐÚNG MỘT token [NO-CON=<số>], nằm trong dòng sổ AC-UX-047 của 00 §6', () => {
    expect(tokenLines.length, 'token "[NO-CON=<số>]" phải xuất hiện đúng 1 lần trong 00_AUDIT').toBe(1)
    expect(tokenLines[0], 'token phải nằm trong chính dòng sổ AC-UX-047').toContain('AC-UX-047')
    expect(m).not.toBeNull()
  })

  it('N == số ô ❌ cột «Lỗi+Thử lại» do bộ dò đo LIVE — KHÔNG phải phép trừ tay', () => {
    expect(
      Number(m![1]),
      `bộ dò đo ${detectorDebt} route còn nợ nhưng sổ ghi ${m![1]} — chạy lại ` +
        '`node frontend/scripts/ui-audit-inventory.mjs --summary` rồi cập nhật token trong CÙNG lượt ' +
        '(cấm dùng công thức "mốc − số đã lật": mốc stale ngay khi lô khác trả nợ)',
    ).toBe(detectorDebt)
  })
})

describe('INV-UX3L-6 — parity TỪNG Ô cột «Lỗi+Thử lại»: 00 §3.1 ⇄ bộ dò, cả 148 dòng', () => {
  it('bảng §3.1 và bộ dò cùng đếm 148 dòng, khớp path theo số thứ tự', () => {
    expect(auditRows.length).toBe(detectorRows.length)
    const misaligned = detectorRows
      .filter((r, i) => auditRows[i]?.index !== r.index || auditRows[i]?.path !== r.path)
      .map((r) => `#${r.index} ${r.path}`)
    expect(misaligned, 'thứ tự dòng §3.1 phải trùng thứ tự khai báo route').toEqual([])
  })

  it('mọi ô của cột này khớp bộ dò (chặn ca 2 lỗi ngược chiều triệt tiêu nhau ở phép đếm tổng)', () => {
    const diff = detectorRows
      .map((r, i) => ({ r, doc: auditRows[i]?.errorCell }))
      .filter(({ r, doc }) => doc !== detectorErrorCell(r))
      .map(({ r, doc }) => `#${r.index} ${r.path}: doc=${doc} dò=${detectorErrorCell(r)}`)
    expect(
      diff,
      'cột «Lỗi+Thử lại» của §3.1 đã ĐỐI SOÁT TOÀN CỘT (ADR-UX-22) — lệch nghĩa là hoặc mã vừa đổi mà quên ' +
        'cập nhật doc, hoặc ai đó chấm tay lại ô. Chạy `node frontend/scripts/ui-audit-inventory.mjs --check`.',
    ).toEqual([])
  })

  it('số ô ❌ ở §3.1 == số bộ dò == token (ba số bằng nhau — INV-UX3-23)', () => {
    const docDebt = auditRows.filter((r) => r.errorCell === '❌').length
    const token = Number(auditDoc.match(/\[NO-CON=(\d+)\]/)![1])
    expect([docDebt, token]).toEqual([detectorDebt, detectorDebt])
  })
})

describe('INV-UX3L-8 — lô 3: ô «Lỗi+Thử lại» GIỮ ✅ ở cả hai đầu (ADR-UX-23)', () => {
  // 12 route lô 3 đã ✅ TRƯỚC khi áp khuôn (chúng có nút «Thử lại», chỉ thiếu tính LOẠI TRỪ giữa
  // nhánh lỗi và nhánh rỗng). Vì vậy phép ⟺ của INV-UX3L-3 không áp được cho chúng; thứ phải khoá
  // là "áp khuôn xong KHÔNG được đánh mất lối nạp lại".
  it('cả 12 dòng lô 3 có ô = ✅ trong 00 §3.1', () => {
    const bad = lot3
      .map((r) => ({ path: r.path, cell: auditByPath.get(r.path)?.errorCell }))
      .filter((x) => x.cell !== '✅')
      .map((x) => `${x.path}: "${x.cell}"`)
    expect(
      bad,
      'route lô 3 mất ✅ ⇒ việc áp ListPageShell đã làm hỏng lối nạp lại (hoặc ai đó chấm tay lại ô)',
    ).toEqual([])
  })

  it('adoption lô 3 ĐÃ ĐÓNG: cả 12 route áp khuôn, không route nào được quay lại', () => {
    // Siết từ `<= 12` sang `=== 12` khi FE land (2026-08-04, `02 §14.11`): lô đã đóng thì bộ đếm
    // phải là ngưỡng CỨNG, nếu không nó chỉ ghi nhận mà không chặn được ai gỡ khuôn ra.
    // Ràng buộc «mọi *ListView phải có khuôn» là của guard AC-UX-070; ở đây khoá riêng 12 route
    // của lô 3 để việc lùi hiện ra ĐÚNG tại sổ lô, kèm tên route.
    const missing = lot3.filter((r) => !importsShell(r.file)).map((r) => r.path)
    expect(
      missing,
      'route lô 3 mất `ui/ListPageShell` — adoption đã đóng thì chỉ được đi một chiều',
    ).toEqual([])
  })
})

describe('INV-UX3L-7 — chiều toàn cục: mọi view dùng khuôn ⇒ ô §3.1 = ✅', () => {
  it('không view nào ngoài 2 sổ áp khuôn mà doc còn ❌', () => {
    const auditByFile = new Map(auditRows.map((r) => [unquote(r.file), r]))
    const offenders: string[] = []
    for (const abs of allViewFiles()) {
      if (!SHELL_IMPORT.test(readFileSync(abs, 'utf-8'))) continue
      const rel = relative(REPO_ROOT, abs)
      const row = auditByFile.get(rel)
      if (!row) continue // view không gắn route (component phụ) — ngoài phạm vi bảng
      if (row.errorCell !== '✅') offenders.push(`${row.path} (${rel}): ô hiện tại "${row.errorCell}"`)
    }
    expect(offenders, 'view đã áp ListPageShell mà ô §3.1 chưa ✅ — doc nói sai về đĩa').toEqual([])
  })
})

// [K8] dân số: chốt tối thiểu cho thư mục guard này quét (SPEC §5.2 N6).
// Không có khối này thì thư mục bị dời ⇒ quét ra 0 file ⇒ mọi khẳng định
// "không tìm thấy vi phạm" thành đúng-rỗng-tuếch mà suite vẫn XANH.
describe('[K8] chốt dân số thư mục quét', () => {
  it('src/views/**/*.vue còn ít nhất 120 file — nếu không, guard đã ngừng canh', () => {
    expect(listFiles(VIEWS, { ext: '.vue', min: 120 }).length).toBeGreaterThanOrEqual(120)
  })
})
