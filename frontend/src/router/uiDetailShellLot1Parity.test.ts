// Guard parity — LÔ 1 adoption `DetailPageShell` (AC-UX-048), spec `docs/ui-ux/03_DETAIL_PAGE_SHELL.md §12`.
//
// Vấn đề nó chặn — «doc nói dối về đĩa», bản lớp CHI TIẾT:
//   Vòng 3 áp `ListPageShell` cho 4 màn nhưng QUÊN lật ô «Lỗi+Thử lại» ở `00 §3.1` ⇒ tài liệu ĐO nói sai
//   về 4 route suốt 3 ngày. Lô 1 lớp danh sách đã đóng lỗ đó bằng `uiListShellLot1Parity.test.ts`; guard
//   này là bản đối xứng cho lớp chi tiết (8 route, rồi lô 2, lô 3…).
//
// Khác biệt với guard lớp danh sách — ADR-UX-12 (`00 §9`): parity 2 CHIỀU bám **cột «Trạng thái» của sổ lô**
// (`03 §12.2`), KHÔNG bám ô §3.1. Lý do đo được: dòng 134 `/procurement-decisions/:id` của §3.1 đang chấm ✅
// nhưng đĩa 2026-08-03 có 0 hit `DetailLoadError|@retry|Thử lại` ⇒ ô ✅ đó sai từ bảng tay vòng 1. Ép 2 chiều
// lên §3.1 sẽ ĐỎ ngay từ bước BA vì một lỗi chấm tay có trước, và cách chữa duy nhất là chấm-tay-lại — đúng
// hành vi ADR-UX-10 cấm. Chiều được ép: `ĐÃ ĐÓNG` ⇒ ô §3.1 phải là ✅.
//
// Bất biến (`03 §12.5`):
//   INV-UX4L1-1 — sổ lô 1 (`03 §12.2`) có ĐÚNG 8 dòng, đánh số 1…8, trùng khít 8 route đã chốt.
//   INV-UX4L1-2 — mã TC là TC-UX4-24…31 (nối tiếp max 23 trên đĩa); `03 §12.6` khai đủ 8 file *DetailStates.
//   INV-UX4L1-3 — route THẬT trong router; view file có trên đĩa và TRÙNG ô view file ở `00 §3.1`.
//   INV-UX4L1-4 — parity 2 CHIỀU: `import DetailPageShell` ⟺ «Trạng thái» = ĐÃ ĐÓNG;
//                 + 1 chiều: ĐÃ ĐÓNG ⇒ ô «Lỗi+Thử lại» ở `00 §3.1` = ✅ và file test trạng thái tồn tại.
//   INV-UX4L1-5 — token `[NO-DET=N]` của AC-UX-048 (`00 §6`) == 20 − số ĐÃ ĐÓNG == số đo lại TỪ ĐĨA.
//   INV-UX4L1-6 — view ĐÃ ĐÓNG: shell ≥ 1 · `text-red-500` == 0 · 0 chuỗi trạng thái tự chế · 0 page-container.
//
// Hôm nay (0 adoption · 8 ô CHƯA · NO-DET=20) guard XANH. Áp khuôn mà quên doc ⇒ ĐỎ ngay, và ngược lại.
import { describe, it, expect } from 'vitest'
import { readFileSync, existsSync, readdirSync, statSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve, join } from 'node:path'
import type { RouteRecordRaw } from 'vue-router'
import { routes } from './index'

const HERE = dirname(fileURLToPath(import.meta.url))
// src/router → src → frontend → <repo root>
const REPO_ROOT = resolve(HERE, '../../..')
const AUDIT_PATH = resolve(REPO_ROOT, 'docs/ui-ux/00_AUDIT_HIEN_TRANG.md')
const SPEC_PATH = resolve(REPO_ROOT, 'docs/ui-ux/03_DETAIL_PAGE_SHELL.md')
const VIEWS_DIR = resolve(REPO_ROOT, 'frontend/src/views')

/**
 * Số màn `*DetailView.vue` KHÔNG có bất kỳ lối nạp lại nào, đo TỪ ĐĨA ngày 2026-08-03 TRƯỚC khi lô 1
 * bắt đầu (`03 §12.1`). Đây là mốc DELTA của lô 1 — đổi con số này = đổi mốc, phải đo lại và ghi vào
 * `03 §12.1` trong cùng một lượt.
 */
const DETAIL_DEBT_BEFORE_LOT1 = 20

/**
 * Phần đóng góp của **lô 2** (`AC-UX-048` LÔ 2, `03 §13`) vào cùng token `[NO-DET=N]` — **ADR-UX-26**.
 *
 * Vì sao phải khai TƯỜNG MINH thay vì bỏ vế số học: `INV-UX4L1-5` ép HAI đẳng thức cùng lúc —
 * `N == 20 − đã-đóng` (bắt lỗi «doc quên cập nhật khi lô đóng») và `N == đo lại từ đĩa` (bắt lỗi
 * «doc ghi số không đo được»). Lô 2 kéo vế-đĩa về **0** trong khi vế số học đông cứng ở 12 ⇒ guard
 * ĐỎ dù mã hoàn toàn đúng. Bỏ vế số học là mất một nửa khả năng phát hiện; đổi mốc 20 thành số mới
 * là đúng loại «mốc sẽ lại stale» mà `ADR-UX-22` đã bác. Nên: **nới bằng một số hạng mới**.
 *
 * 12 đường dẫn dưới đây là các màn thuộc nhóm 0-lối-nạp-lại TRƯỚC lô 2 (`03 §13.8` mục 2). Mỗi lô
 * chi tiết về sau phải khai phần đóng góp của mình theo cùng cách.
 */
const LOT2_NO_RECOVERY: readonly string[] = [
  'asset/AssetDetailView.vue',
  'commissioning/CommissioningDetailView.vue',
  'document/DocumentDetailView.vue',
  'incident/RCADetailView.vue',
  'needs/NeedsRequestDetailView.vue',
  'needs/ProcurementPlanDetailView.vue',
  'procurement/VendorEvalDetailView.vue',
  'procurement/VendorProfileDetailView.vue',
  'purchase/PurchaseDetailView.vue',
  'purchase/ServiceContractDetailView.vue',
  'tech-specs/TechSpecDetailView.vue',
  'training/CompetencyDetailView.vue',
]

/** 8 route của lô 1 — chốt bởi PM/BA; hardcode để việc đổi phạm vi là TAMPER-EVIDENT. */
const LOT1_ROUTES = [
  '/stock-movements/:name',
  '/warehouses/:name',
  '/spare-parts/:name',
  '/asset-transfers/:id',
  '/cm/firmware/:id',
  '/compliance/findings/:id',
  '/suppliers/:id',
  '/procurement-decisions/:id',
] as const

const STATUS_DONE = 'ĐÃ ĐÓNG'
const STATUS_TODO = 'CHƯA'

const auditDoc = readFileSync(AUDIT_PATH, 'utf-8')
const specDoc = readFileSync(SPEC_PATH, 'utf-8')

/** Khuôn parse dùng lại `uiAuditDocParity` / `uiListShellLot1Parity` — KHÔNG viết bộ parse thứ ba. */
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

type LedgerRow = { index: number; path: string; file: string; status: string; tc: string }

/** Sổ lô 1 — `03 §12.2` (8 cột: # · Route · View file · Hàm nạp · Nguồn lỗi · Module mock · Trạng thái · TC). */
function parseLedger(): LedgerRow[] {
  const body = section(specDoc, '### 12.2 Sổ lô 1', '### 12.3')
  const rows: LedgerRow[] = []
  for (const line of body.split('\n')) {
    if (!line.startsWith('|')) continue
    const c = cellsOf(line)
    if (c.length !== 8) continue
    if (!/^\d+$/.test(c[0])) continue
    rows.push({ index: Number(c[0]), path: unquote(c[1]), file: unquote(c[2]), status: c[6], tc: unquote(c[7]) })
  }
  return rows
}

/** Bảng file test trạng thái — `03 §12.6` (2 cột: TC · file). */
function parseTestPlan(): Map<string, string> {
  const body = section(specDoc, '### 12.6 Bộ test', '**Sub-case bắt buộc')
  const out = new Map<string, string>()
  for (const line of body.split('\n')) {
    if (!line.startsWith('|')) continue
    const c = cellsOf(line)
    if (c.length !== 2) continue
    const tc = unquote(c[0])
    if (!/^TC-UX4-\d+$/.test(tc)) continue
    out.set(tc, unquote(c[1]))
  }
  return out
}

type AuditRow = { path: string; file: string; errorCell: string }

/** Bảng hiện trạng — `00 §3.1` (11 cột; ô «Lỗi+Thử lại» là tiêu chí thứ 4 ⇒ chỉ số 6). */
function parseAuditRows(): AuditRow[] {
  const body = section(auditDoc, '### 3.1 Bảng đầy đủ', '### 3.2')
  const rows: AuditRow[] = []
  for (const line of body.split('\n')) {
    if (!line.startsWith('|')) continue
    const c = cellsOf(line)
    if (c.length !== 11) continue
    if (!/^\d+$/.test(c[0])) continue
    rows.push({ path: unquote(c[1]), file: unquote(c[2]), errorCell: c[6] })
  }
  return rows
}

/** Mọi `*DetailView.vue` dưới `frontend/src/views` (đệ quy). */
function allDetailViews(dir: string = VIEWS_DIR): string[] {
  const out: string[] = []
  for (const entry of readdirSync(dir)) {
    const abs = join(dir, entry)
    if (statSync(abs).isDirectory()) out.push(...allDetailViews(abs))
    else if (entry.endsWith('DetailView.vue')) out.push(abs)
  }
  return out
}

const ledger = parseLedger()
const testPlan = parseTestPlan()
const auditByPath = new Map(parseAuditRows().map((r) => [r.path, r]))
const routePaths = new Set(allRoutePaths(routes))

const readIf = (abs: string): string => (existsSync(abs) ? readFileSync(abs, 'utf-8') : '')

/** View đã áp khuôn? Đọc ĐĨA, không tin tài liệu. */
function importsShell(relFile: string): boolean {
  return /from\s+'@\/components\/common\/DetailPageShell\.vue'/.test(readIf(resolve(REPO_ROOT, relFile)))
}

/** «0 lối nạp lại nào» — cùng phép đo đã sinh ra con số 20 ở `03 §12.1`. */
const RECOVERY_TOKEN = /DetailLoadError|@retry|DetailPageShell/

describe('INV-UX4L1-1 — sổ lô 1 (03 §12.2): đúng 8 dòng, trùng khít 8 route đã chốt', () => {
  it('đọc được sổ và có ĐÚNG 8 dòng, đánh số liên tục 1…8', () => {
    expect(ledger.length, 'sổ lô 1 phải có đúng 8 dòng — đổi phạm vi lô = đổi cam kết với PM').toBe(8)
    expect(ledger.map((r) => r.index)).toEqual(Array.from({ length: 8 }, (_, i) => i + 1))
  })

  it('tập route trong sổ TRÙNG KHÍT 8 route đã chốt (không hơn, không kém)', () => {
    expect(ledger.map((r) => r.path)).toEqual([...LOT1_ROUTES])
  })

  it('cột «Trạng thái» chỉ nhận 2 giá trị ĐÃ ĐÓNG / CHƯA', () => {
    const bad = ledger.filter((r) => r.status !== STATUS_DONE && r.status !== STATUS_TODO)
    expect(bad.map((r) => `${r.path}="${r.status}"`), 'ô trạng thái lạ — guard không suy đoán').toEqual([])
  })
})

describe('INV-UX4L1-2 — mã TC nối tiếp 24…31 và bảng test §12.6 khớp sổ', () => {
  it('mã TC là TC-UX4-24 … TC-UX4-31, không tái dùng 01–23, không trùng', () => {
    const tcs = ledger.map((r) => r.tc)
    expect(tcs).toEqual(Array.from({ length: 8 }, (_, i) => `TC-UX4-${24 + i}`))
    expect(new Set(tcs).size).toBe(8)
  })

  it('§12.6 khai đủ 8 file test, khớp mã TC của sổ, đặt tên *DetailStates.test.ts', () => {
    expect([...testPlan.keys()].sort()).toEqual([...ledger.map((r) => r.tc)].sort())
    const bad = [...testPlan.values()].filter((f) => !/DetailStates\.test\.ts$/.test(f))
    expect(bad, 'file test trạng thái phải đặt tên <ten>DetailStates.test.ts').toEqual([])
  })
})

describe('INV-UX4L1-3 — sổ ⇄ router ⇄ bảng hiện trạng 00 §3.1', () => {
  it('mọi route trong sổ là route THẬT trong router/index.ts', () => {
    const notRoute = ledger.filter((r) => !routePaths.has(r.path)).map((r) => r.path)
    expect(notRoute).toEqual([])
  })

  it('view file tồn tại trên đĩa', () => {
    const missing = ledger
      .filter((r) => !r.file.endsWith('.vue') || !existsSync(resolve(REPO_ROOT, r.file)))
      .map((r) => `${r.path} → ${r.file}`)
    expect(missing, 'đường dẫn view chết trong sổ lô 1').toEqual([])
  })

  it('view file trong sổ TRÙNG ô view file tương ứng ở 00 §3.1', () => {
    const mismatch = ledger
      .filter((r) => auditByPath.get(r.path)?.file !== r.file)
      .map((r) => `${r.path}: sổ="${r.file}" vs 00§3.1="${auditByPath.get(r.path)?.file}"`)
    expect(mismatch, '2 tài liệu phải cùng trỏ 1 file view').toEqual([])
  })
})

describe('INV-UX4L1-4 — parity 2 CHIỀU: import khuôn ⟺ «Trạng thái» = ĐÃ ĐÓNG', () => {
  it('không có màn nào áp khuôn mà sổ còn CHƯA, và không có ô ĐÃ ĐÓNG nào không có khuôn đứng sau', () => {
    const codeNotDoc: string[] = []
    const docNotCode: string[] = []
    for (const r of ledger) {
      const applied = importsShell(r.file)
      const closed = r.status === STATUS_DONE
      if (applied && !closed) codeNotDoc.push(r.path)
      if (closed && !applied) docNotCode.push(r.path)
    }
    expect(
      codeNotDoc,
      'view ĐÃ dùng DetailPageShell nhưng sổ 03 §12.2 vẫn CHƯA — mã và doc phải land CÙNG lượt (ADR-UX-12)',
    ).toEqual([])
    expect(
      docNotCode,
      'sổ ghi ĐÃ ĐÓNG nhưng view KHÔNG import DetailPageShell — tài liệu đang nói sai về đĩa',
    ).toEqual([])
  })

  it('ĐÃ ĐÓNG ⇒ ô «Lỗi+Thử lại» của route đó ở 00 §3.1 phải là ✅ (một chiều — ADR-UX-12)', () => {
    const notFlipped = ledger
      .filter((r) => r.status === STATUS_DONE && auditByPath.get(r.path)?.errorCell !== '✅')
      .map((r) => `${r.path} (ô hiện tại: "${auditByPath.get(r.path)?.errorCell}")`)
    expect(notFlipped, 'đóng route trong lô mà quên lật ô §3.1 — bảng ĐO lại nói sai về đĩa').toEqual([])
  })

  it('ĐÃ ĐÓNG ⇒ file test trạng thái khai ở §12.6 phải TỒN TẠI trên đĩa', () => {
    const missing: string[] = []
    for (const r of ledger) {
      if (r.status !== STATUS_DONE) continue
      const testFile = testPlan.get(r.tc)
      if (!testFile || !existsSync(resolve(REPO_ROOT, testFile))) {
        missing.push(`${r.path} → ${testFile ?? '(chưa khai)'}`)
      }
    }
    expect(missing, 'adoption không kèm test trạng thái = chưa chứng minh được 4 trạng thái loại trừ').toEqual([])
  })
})

describe('INV-UX4L1-5 — token nợ [NO-DET=N] của AC-UX-048 khớp tiến độ VÀ khớp đĩa', () => {
  // Token phải DUY NHẤT trong tài liệu — 2 nơi ghi số nợ là 2 nguồn sự thật (đúng nguyên nhân AC-UX-031).
  // Dòng chứa token bắt buộc là dòng sổ của AC-UX-048 ⇒ không thể "ghi nhờ" ở chỗ khác cho dễ.
  const tokenLines = auditDoc.split('\n').filter((l) => l.includes('[NO-DET='))
  const m = tokenLines[0]?.match(/\[NO-DET=(\d+)\]/) ?? null

  it('đọc được ĐÚNG MỘT token [NO-DET=N], nằm trong dòng sổ AC-UX-048 của 00 §6', () => {
    expect(tokenLines.length, 'token "[NO-DET=N]" phải xuất hiện đúng 1 lần trong 00_AUDIT').toBe(1)
    expect(tokenLines[0], 'token phải nằm trong chính dòng sổ AC-UX-048').toContain('AC-UX-048')
    expect(m).not.toBeNull()
  })

  it('N == 20 − (lô 1 ĐÃ ĐÓNG) − (lô 2 ĐÃ ĐÓNG) — ADR-UX-26', () => {
    const closedLot1 = ledger.filter((r) => r.status === STATUS_DONE).length
    // Lô 2 đọc cột «Trạng thái» của `03 §13.2` (SSoT của lô đó) và CHỈ tính những màn thuộc
    // nhóm 0-lối-nạp-lại — 9 màn khác của lô 2 vốn đã có `DetailLoadError`, không nằm trong token.
    const lot2Section = section(specDoc, '### 13.2', '### 13.3')
    const closedLot2 = LOT2_NO_RECOVERY.filter((suffix) =>
      lot2Section
        .split('\n')
        .some((l) => l.includes(suffix) && l.includes(STATUS_DONE)),
    ).length
    const expected = DETAIL_DEBT_BEFORE_LOT1 - closedLot1 - closedLot2
    expect(
      Number(m![1]),
      `lô 1 đóng ${closedLot1}/8 · lô 2 đóng ${closedLot2}/${LOT2_NO_RECOVERY.length} ⇒ NO-DET phải là ${expected}`,
    ).toBe(expected)
  })

  it('N == số *DetailView.vue trên đĩa KHÔNG có lối nạp lại nào (đo lại, không tin doc)', () => {
    const noRecovery = allDetailViews().filter((abs) => !RECOVERY_TOKEN.test(readFileSync(abs, 'utf-8')))
    expect(
      noRecovery.length,
      `đĩa còn ${noRecovery.length} màn 0-lối-nạp-lại nhưng sổ ghi ${m![1]} — cập nhật token trong CÙNG lượt`,
    ).toBe(Number(m![1]))
  })
})

describe('INV-UX4L1-6 — view ĐÃ ĐÓNG phải sạch ngõ cụt tự chế', () => {
  /**
   * Nhánh trạng thái TẢI do view tự viết. CHỈ soi từ khoá `loading`, KHÔNG soi «định danh trần»:
   * `v-else-if="showReadOnlyHint"` (`AssetTransferDetailView.vue:295`) và
   * `v-else-if="doc.reference_name"` (`StockMovementDetailView.vue:160`) là logic NGHIỆP VỤ hợp lệ —
   * một guard bắt định danh trần sẽ ĐỎ oan và ép FE viết vòng vo. Nhánh `!<record>` được chặn gián
   * tiếp và chắc chắn hơn bằng phép «shell là thẻ gốc duy nhất» ở `it` kế tiếp (INV-UX4-11).
   */
  const DIY_LOADING = /v-(?:if|else-if)="[^"]*\bloading\b[^"]*"/

  /** Dòng nội dung đầu tiên sau `<template>` cột 0 — bỏ qua dòng trống và chú thích. */
  function firstTemplateTag(src: string): string {
    const lines = src.split('\n')
    const at = lines.findIndex((l) => l === '<template>')
    if (at < 0) return '(không tìm thấy khối <template> cột 0)'
    for (let i = at + 1; i < lines.length; i++) {
      const t = lines[i].trim()
      if (!t || t.startsWith('<!--')) continue
      return t.slice(0, 60)
    }
    return '(khối <template> rỗng)'
  }

  it('mỗi view ĐÃ ĐÓNG: shell ≥ 1 · text-red-500 == 0 · page-container == 0', () => {
    const bad: string[] = []
    for (const r of ledger) {
      if (r.status !== STATUS_DONE) continue
      const src = readIf(resolve(REPO_ROOT, r.file))
      const shell = (src.match(/DetailPageShell/g) ?? []).length
      const red = (src.match(/text-red-500/g) ?? []).length
      const pc = (src.match(/page-container/g) ?? []).length
      if (shell < 1 || red !== 0 || pc !== 0) bad.push(`${r.file}: shell=${shell} red500=${red} pageContainer=${pc}`)
    }
    expect(bad, 'ĐÃ ĐÓNG nhưng còn màu thô / khung lồng / thiếu khuôn').toEqual([])
  })

  it('mỗi view ĐÃ ĐÓNG: 0 nhánh `v-if/v-else-if` tự quyết trạng thái TẢI', () => {
    const bad: string[] = []
    for (const r of ledger) {
      if (r.status !== STATUS_DONE) continue
      const offenders = readIf(resolve(REPO_ROOT, r.file))
        .split('\n')
        .filter((l) => DIY_LOADING.test(l))
        .map((l) => l.trim().slice(0, 80))
      if (offenders.length) bad.push(`${r.file}: ${offenders.join(' ⏎ ')}`)
    }
    expect(bad, 'trạng thái tải phải do shell quyết (prop `:loading`), không phải nhánh v-if tự chế').toEqual([])
  })

  it('mỗi view ĐÃ ĐÓNG: `DetailPageShell` là THẺ GỐC DUY NHẤT của template (INV-UX4-11)', () => {
    const bad: string[] = []
    for (const r of ledger) {
      if (r.status !== STATUS_DONE) continue
      const first = firstTemplateTag(readIf(resolve(REPO_ROOT, r.file)))
      if (!first.startsWith('<DetailPageShell')) bad.push(`${r.file}: thẻ gốc = ${first}`)
    }
    expect(
      bad,
      'còn thẻ bọc ngoài shell ⇒ view vẫn tự quyết được trạng thái (và padding/max-width nhân đôi)',
    ).toEqual([])
  })
})
