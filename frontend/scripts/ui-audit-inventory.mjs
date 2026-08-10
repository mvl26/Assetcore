#!/usr/bin/env node
// ui-audit-inventory.mjs — bộ kiểm kê UI/UX toàn FE, CHỈ ĐỌC (read-only).
//
// Vì sao có file này: `docs/ui-ux/00_AUDIT_HIEN_TRANG.md` là ảnh chụp nợ UI/UX của TOÀN BỘ
// frontend và là đầu vào ghim cho các vòng sau. Nếu phép đo chỉ nằm trong đầu người đo thì
// vòng 5 không thể chấm DELTA — nên §1.2 của tài liệu được cài đặt lại ở đây thành mã chạy
// được, tất định (cùng input ⇒ cùng output, không phụ thuộc thứ tự file hay đồng hồ).
//
// Script KHÔNG sửa bất kỳ file `.vue` nào. Nó chỉ đọc `src/router/index.ts` + các file view.
//
// Cách dùng:
//   node frontend/scripts/ui-audit-inventory.mjs                # bảng markdown ra stdout
//   node frontend/scripts/ui-audit-inventory.mjs --json         # JSON đầy đủ (máy đọc)
//   node frontend/scripts/ui-audit-inventory.mjs --summary      # chỉ §2.1 + §2.2
//   node frontend/scripts/ui-audit-inventory.mjs --check        # đối chiếu với bảng §3.1 trong doc
//
// Giới hạn đã biết (ghi rõ để không ai tưởng số này là chân lý):
//   - Bộ dò là REGEX trên mã nguồn, không phải render thật. Nó bắt được "có/không có khuôn",
//     KHÔNG bắt được "khuôn có đúng không" (vd nút «Thử lại» tồn tại nhưng gọi sai hàm).
//     Vì thế tài liệu bắt buộc hiệu đính TAY các dòng đã render bằng Playwright (§5).
//   - Cột "nhãn tiếng Việt" chạy theo blacklist viết tắt EN + từ EN thường gặp ở lớp hiển thị;
//     nó cố ý BỎ QUA `{{ ... }}` (dữ liệu, không phải chữ do FE viết) và mã bản ghi.

import { readFileSync, existsSync, readdirSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve, relative } from 'node:path'

const HERE = dirname(fileURLToPath(import.meta.url))
const FRONTEND = resolve(HERE, '..')
const REPO_ROOT = resolve(FRONTEND, '..')
const SRC = resolve(FRONTEND, 'src')
const ROUTER = resolve(SRC, 'router/index.ts')
const DOC = resolve(REPO_ROOT, 'docs/ui-ux/00_AUDIT_HIEN_TRANG.md')

const CRITERIA = ['loading', 'skeleton', 'empty', 'error', 'responsive', 'vi', 'a11y']
// §1.4 — trọng số cố định, KHÔNG cảm tính.
const WEIGHT = { empty: 2, error: 2, responsive: 2, vi: 2, loading: 1, skeleton: 1, a11y: 1 }

// ───────────────────────── 1. Parse router → danh sách route ─────────────────────────

/**
 * Đọc `router/index.ts` và trả về [{ path, name, importSpec, isRedirect }].
 *
 * Bẫy đã gặp (DELTA 149 → 148): `grep -c "path: '"` cho 149 nhưng route THẬT là 148 vì có
 * `redirect: (to) => ({ path: '/documents', query: … })` — chuỗi `path:` nằm TRONG thân hàm
 * chuyển hướng, không phải khai báo route. Đếm thô ⇒ `/documents` bị tính 2 lần và mọi thống
 * kê lệch theo. Quy tắc: bỏ mọi `path:` mà cùng dòng phía trước đã có `redirect` hoặc `=>`.
 */
function parseRoutes() {
  const lines = readFileSync(ROUTER, 'utf-8').split('\n')
  const routes = []
  let cur = null

  const flush = () => {
    if (cur && cur.path !== null) routes.push(cur)
    cur = null
  }

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]
    const pathMatch = line.match(/path:\s*'([^']+)'/)
    if (pathMatch) {
      const before = line.slice(0, pathMatch.index)
      const insideRedirectFn = /redirect|=>/.test(before)
      if (!insideRedirectFn) {
        flush()
        cur = { path: pathMatch[1], name: null, importSpec: null, isRedirect: false, line: i + 1 }
      }
    }
    if (!cur) continue
    const nameMatch = line.match(/^\s*name:\s*'([^']+)'/)
    if (nameMatch && !cur.name) cur.name = nameMatch[1]
    const impMatch = line.match(/component:\s*\(\)\s*=>\s*import\('([^']+)'\)/)
    if (impMatch && !cur.importSpec) cur.importSpec = impMatch[1]
    // Route rút gọn 1 dòng `{ path: '/pm', redirect: '/pm/dashboard' },` cũng phải bắt được —
    // neo `^\s*redirect:` bỏ sót 9/13 route chuyển hướng (đếm ra "unresolved" giả).
    if (/[\s{,]redirect\s*:/.test(line)) cur.isRedirect = true
  }
  flush()
  return routes
}

/** `@/views/x/Y.vue` → đường dẫn tuyệt đối; null nếu không giải được trên đĩa. */
function resolveImport(spec) {
  if (!spec) return null
  const rel = spec.replace(/^@\//, '')
  const abs = resolve(SRC, rel)
  return existsSync(abs) ? abs : null
}

// ───────────────────────── 2. Bộ dò 7 tiêu chí trên file .vue ─────────────────────────

const templateOf = (src) => {
  const a = src.indexOf('<template>')
  if (a === -1) return src
  const b = src.lastIndexOf('</template>')
  return b === -1 ? src.slice(a) : src.slice(a, b)
}

const stripComments = (s) => s.replace(/<!--[\s\S]*?-->/g, '')

/** Component con được TRUYỀN trạng thái từ cha (`:loading` / `:error` / `@retry`) — ADR-UX-03. */
function delegatedChildren(tpl) {
  const out = new Set()
  const tagRe = /<([A-Z][A-Za-z0-9]*)\b([^>]*)>/g
  let m
  while ((m = tagRe.exec(tpl))) {
    const [, tag, attrs] = m
    if (/(^|\s)(:|v-bind:)(loading|is-loading|isLoading|error|pending)\b/.test(attrs) ||
        /(^|\s)@retry\b/.test(attrs)) {
      out.add(tag)
    }
  }
  return [...out]
}

/**
 * Delegate của shell view `<component :is="...">` — §1.2.
 *
 * Bắt CẢ HAI kiểu khai báo: `import()` động VÀ `import X from '…'` tĩnh — `DashboardView.vue`
 * dùng kiểu TĨNH (`import AdminDashboardView from './personas/AdminDashboardView.vue'`), nếu chỉ
 * dò `import(` thì shell bị coi là màn tĩnh ⇒ 4 ô trạng thái-tải rơi về `n/a` sai.
 */
function shellDelegates(src, selfAbs) {
  if (!/<component\s+:is=/.test(src)) return []
  const out = new Set()
  const push = (spec) => {
    const abs = spec.startsWith('@/')
      ? resolve(SRC, spec.slice(2))
      : resolve(dirname(selfAbs), spec)
    if (existsSync(abs)) out.add(abs)
  }
  let m
  const dyn = /import\(['"]([^'"]+\.vue)['"]\)/g
  while ((m = dyn.exec(src))) push(m[1])
  const stat = /^\s*import\s+[A-Za-z0-9_$]+\s+from\s+['"]([^'"]+\.vue)['"]/gm
  while ((m = stat.exec(src))) push(m[1])
  return [...out].filter((p) => p !== selfAbs)
}

const COMPONENT_DIRS = [resolve(SRC, 'components'), resolve(SRC, 'views')]
const componentIndex = (() => {
  const idx = new Map()
  const walk = (dir) => {
    for (const e of readdirSync(dir, { withFileTypes: true })) {
      const p = resolve(dir, e.name)
      if (e.isDirectory()) walk(p)
      else if (e.name.endsWith('.vue') && !idx.has(e.name.replace(/\.vue$/, ''))) {
        idx.set(e.name.replace(/\.vue$/, ''), p)
      }
    }
  }
  for (const d of COMPONENT_DIRS) if (existsSync(d)) walk(d)
  return idx
})()

// ── tiêu chí 1: loading ──
const hasLoading = (tpl) =>
  /v-(if|else-if|show)="[^"]*\b(isLoading|loading|pending|isFetching|isPending)\b/.test(tpl) ||
  /<(LoadingSpinner|SkeletonLoader)\b/.test(tpl)

// ── tiêu chí 2: skeleton ──
const hasSkeleton = (tpl) =>
  /<SkeletonLoader\b/.test(tpl) || /animate-pulse/.test(tpl) || /class="[^"]*\bskeleton\b/.test(tpl)

// ── tiêu chí 3: empty-state CÓ HƯỚNG DẪN ──
const EMPTY_PHRASE = /(Chưa có|Không có|Không tìm thấy|Trống|chưa có dữ liệu)/i
const GUIDE_WORD = /(Hãy|Bấm|Nhấn|Tạo |Thử |Xoá bộ lọc|Xóa bộ lọc|Chọn |Đổi bộ lọc|đợi)/i
function hasEmptyWithGuidance(tpl) {
  const lines = tpl.split('\n')
  for (let i = 0; i < lines.length; i++) {
    if (!EMPTY_PHRASE.test(lines[i])) continue
    const from = Math.max(0, i - 12)
    const to = Math.min(lines.length, i + 13)
    const win = lines.slice(from, to).join('\n')
    if (/<button\b|<RouterLink\b|<router-link\b/.test(win) || GUIDE_WORD.test(win)) return true
  }
  return false
}
const hasEmptyBranch = (tpl) => EMPTY_PHRASE.test(tpl)

// ── tiêu chí 4: error-state có nút thử lại ──
const hasRetry = (tpl) =>
  /(Thử lại|Tải lại|Thử lại ngay)/.test(tpl) && /@click/.test(tpl) ||
  /<DetailLoadError\b/.test(tpl) ||
  /<RouteErrorBoundary\b/.test(tpl) ||
  /@retry\b/.test(tpl)
const hasErrorBlock = (tpl) => /\berror\b/i.test(tpl)

// ── tiêu chí 5: responsive ≤768px — đếm HAZARD, không đếm utility ──
// Tailwind mobile-first: nhiều `md:` không chứng minh gì. Chỉ 3 hazard thật mới tính nợ.
function responsiveHazards(tpl) {
  const hz = []
  // (a) grid-cols-N (N≥3) áp NGAY từ mobile (không có tiền tố breakpoint).
  const gridRe = /(^|[\s"'])grid-cols-(\d+)/g
  let m
  while ((m = gridRe.exec(tpl))) {
    const n = Number(m[2])
    const prefixed = /[a-z]{2}:$/.test(tpl.slice(Math.max(0, m.index - 4), m.index + m[1].length))
    if (n >= 3 && !prefixed) hz.push(`grid-cols-${n} từ mobile`)
  }
  // (b) <table> không nằm trong khung overflow-x-*.
  const tableRe = /<table\b/g
  while ((m = tableRe.exec(tpl))) {
    const before = tpl.slice(Math.max(0, m.index - 600), m.index)
    if (!/overflow-x-(auto|scroll)/.test(before)) hz.push('<table> ngoài khung overflow-x')
  }
  // (c) chiều rộng cứng ≥480px.
  const wRe = /\b(?:min-)?w-\[(\d+)px\]/g
  while ((m = wRe.exec(tpl))) if (Number(m[1]) >= 480) hz.push(`chiều rộng cứng ${m[1]}px`)
  return [...new Set(hz)]
}

// ── tiêu chí 6: nhãn tiếng Việt đầy đủ ──
// Blacklist theo LL-FE-53: viết tắt EN PHẢI dịch + từ EN thường gặp ở lớp hiển thị.
// GIỮ NGUYÊN (không tính lỗi): QR, PIN, BHYT, NSNN, KTV, NCC, ISO, GMDN, WHO, VILAS, N/A, VND,
// mã module (IMM/AC), tên DocType, fieldname, value/enum.
const EN_ACRONYMS = [
  'CAPEX', 'OPEX', 'SLA', 'KPI', 'CAPA', 'RCA', 'MTTR', 'MTBF', 'TCO', 'OEE',
  'RTO', 'RPO', 'BOM', 'SOP', 'DOA', 'AVL', 'QMS', 'FCR', 'FTA',
]
const EN_WORDS = [
  'Import', 'Export', 'Submit', 'Cancel', 'Delete', 'Search', 'Filter', 'Loading',
  'Retry', 'Details', 'Settings', 'Dashboard', 'Overview', 'Summary', 'Pending',
  'Approved', 'Rejected', 'Completed', 'Draft', 'Scheduled', 'Overdue', 'downtime',
  'uptime', 'Save', 'Close', 'Update', 'Remove', 'Preview', 'Upload', 'Download',
]
// Mã bản ghi / naming series / MẶT NẠ ID gợi ý là VALUE, không phải copy ⇒ loại trừ trước khi soi.
// (`placeholder="CAPA-XXXX"` là ví dụ định dạng mã, KHÔNG phải viết tắt EN chưa dịch — LL-FE-53
// giữ nguyên ID-mask.)
const RECORD_CODE = /\b[A-Z]{2,}(?:-[A-Z0-9]{1,})*-(?:\d{4}-\d+|X{2,}|#{2,}|\d+)\b/g

function viLeaks(tpl) {
  const display = []
  // text node
  const textRe = />([^<>{}]{2,})</g
  let m
  while ((m = textRe.exec(tpl))) display.push(m[1])
  // Thuộc tính chữ hiển thị. KHÔNG lấy `aria-label` (a11y, không phải copy) và KHÔNG lấy thuộc
  // tính BOUND `:title="expr"` / `v-bind:title` — nội dung đó là BIỂU THỨC JS (tên state EN như
  // 'Pending Approval' là VALUE gửi BE), lấy vào sẽ báo nợ giả cho màn thực ra đã VI hoá.
  const attrRe = /(^|[^:\w-])(placeholder|title|label)="([^"]+)"/g
  while ((m = attrRe.exec(tpl))) display.push(m[3])

  const leaks = new Set()
  for (const raw of display) {
    const s = raw.replace(RECORD_CODE, ' ').trim()
    if (!s) continue
    for (const a of EN_ACRONYMS) {
      if (new RegExp(`(^|[^A-Za-z])${a}([^A-Za-z]|$)`).test(s)) leaks.add(a)
    }
    for (const w of EN_WORDS) {
      if (new RegExp(`(^|[^A-Za-zÀ-ỹ])${w}([^A-Za-zÀ-ỹ]|$)`).test(s)) leaks.add(w)
    }
  }
  return [...leaks]
}

// ── tiêu chí 7: a11y label ──
function a11yStat(tpl) {
  const count = (re) => (tpl.match(re) ?? []).length
  const labels =
    count(/\baria-label(?:ledby)?=/g) + count(/\bsr-only\b/g) + count(/<label[^>]*\bfor=/g)
  const controls = count(/<(input|select|textarea)\b/g)
  // nút CHỈ có icon: <button …> … <SomeIcon/> … </button> không kèm text node có chữ
  const iconButtons = (tpl.match(/<button[\s\S]{0,400}?<\/button>/g) ?? []).filter(
    (b) => /<[A-Z][A-Za-z]*Icon\b|<svg\b/.test(b) && !/>[^<>{}]*[A-Za-zÀ-ỹ]{2,}[^<>{}]*</.test(b),
  ).length
  const labelsMissingFor = count(/<label(?![^>]*\bfor=)[^>]*>/g)
  return { labels, controls, iconButtons, labelsMissingFor }
}

// ───────────────────────── 3. Chấm 1 view ─────────────────────────

function scanFile(abs, depth = 0) {
  const src = readFileSync(abs, 'utf-8')
  const tpl = stripComments(templateOf(src))

  // §1.3 — màn TĨNH: không import @/api/*, @/stores/*, không useQuery ⇒ không có gì để tải.
  let isStatic = !/from ['"]@\/(api|stores)\//.test(src) && !/useQuery|useMutation/.test(src)
  let hasList = /v-for=/.test(tpl)
  const a11y = a11yStat(tpl)

  let flags = {
    loading: hasLoading(tpl),
    skeleton: hasSkeleton(tpl),
    empty: hasEmptyWithGuidance(tpl),
    emptyBranch: hasEmptyBranch(tpl),
    error: hasRetry(tpl),
    errorBlock: hasErrorBlock(tpl),
    hazards: responsiveHazards(tpl),
    viLeaks: viLeaks(tpl),
    a11y,
  }

  // ADR-UX-03 — hợp thành ĐÚNG 1 cấp: cộng trạng thái-tải từ component được truyền
  // :loading/:error/@retry. Component chỉ được render (SmartSelect…) KHÔNG được cộng.
  if (depth === 0) {
    for (const tag of delegatedChildren(tpl)) {
      const child = componentIndex.get(tag)
      if (!child || child === abs) continue
      const c = scanFile(child, depth + 1)
      flags.loading ||= c.flags.loading
      flags.skeleton ||= c.flags.skeleton
      flags.empty ||= c.flags.empty
      flags.emptyBranch ||= c.flags.emptyBranch
      flags.error ||= c.flags.error
      flags.errorBlock ||= c.flags.errorBlock
    }
    // Shell `<component :is>`: ✅ chỉ khi MỌI delegate ✅ (giao, không hợp).
    const shells = shellDelegates(src, abs)
    if (shells.length) {
      const kids = shells.map((p) => scanFile(p, depth + 1))
      // Shell chỉ là bộ định tuyến (`DashboardView` 41 dòng, 0 import @/api) — tính TĨNH và
      // RENDER-TẬP theo delegate, nếu không 4 ô trạng thái-tải của 8 dashboard persona rơi `n/a`.
      isStatic = kids.every((c) => c.isStatic)
      hasList = hasList || kids.some((c) => c.hasList)
      for (const k of ['loading', 'skeleton', 'empty', 'error']) {
        flags[k] = kids.every((c) => c.flags[k])
      }
      flags.hazards = [...new Set([...flags.hazards, ...kids.flatMap((c) => c.flags.hazards)])]
      flags.viLeaks = [...new Set([...flags.viLeaks, ...kids.flatMap((c) => c.flags.viLeaks)])]
      const agg = kids.reduce((s, c) => ({
        labels: s.labels + c.flags.a11y.labels,
        controls: s.controls + c.flags.a11y.controls,
        iconButtons: s.iconButtons + c.flags.a11y.iconButtons,
        labelsMissingFor: s.labelsMissingFor + c.flags.a11y.labelsMissingFor,
      }), { ...a11y })
      flags.a11y = agg
    }
  }

  const cells = {
    loading: isStatic ? 'n/a' : flags.loading ? '✅' : '❌',
    skeleton: isStatic ? 'n/a' : flags.skeleton ? '✅' : '❌',
    empty: !hasList ? 'n/a' : flags.empty ? '✅' : '❌',
    error: isStatic ? 'n/a' : flags.error ? '✅' : '❌',
    responsive: flags.hazards.length === 0 ? '✅' : '❌',
    vi: flags.viLeaks.length === 0 ? '✅' : '❌',
    a11y:
      flags.a11y.controls === 0 && flags.a11y.iconButtons === 0
        ? 'n/a'
        : flags.a11y.labels >= flags.a11y.controls && flags.a11y.labels >= 1
          ? '✅'
          : '❌',
  }
  return { flags, cells, isStatic, hasList }
}

function painOf(cells) {
  let score = 0
  for (const k of CRITERIA) if (cells[k] === '❌') score += WEIGHT[k]
  return { score, level: score >= 7 ? 'P0' : score >= 4 ? 'P1' : 'P2' }
}

// ───────────────────────── 4. Chạy toàn bộ ─────────────────────────

function inventory() {
  const routes = parseRoutes()
  const rows = routes.map((r, i) => {
    const abs = resolveImport(r.importSpec)
    if (!abs) {
      return {
        index: i + 1,
        path: r.path,
        name: r.name,
        file: null,
        kind: r.isRedirect ? 'redirect' : 'unresolved',
        cells: Object.fromEntries(CRITERIA.map((c) => [c, 'n/a'])),
        pain: { score: 0, level: 'P2' },
        evidence: {},
      }
    }
    const s = scanFile(abs)
    return {
      index: i + 1,
      path: r.path,
      name: r.name,
      file: relative(REPO_ROOT, abs),
      kind: 'view',
      cells: s.cells,
      pain: painOf(s.cells),
      evidence: {
        hazards: s.flags.hazards,
        viLeaks: s.flags.viLeaks,
        a11y: s.flags.a11y,
        static: s.isStatic,
        hasList: s.hasList,
      },
    }
  })
  return rows
}

function summarize(rows) {
  const withView = rows.filter((r) => r.kind === 'view')
  const per = {}
  for (const c of CRITERIA) {
    per[c] = { bad: 0, na: 0, ok: 0 }
    for (const r of withView) {
      const v = r.cells[c]
      if (v === '❌') per[c].bad++
      else if (v === 'n/a') per[c].na++
      else per[c].ok++
    }
  }
  const pain = { P0: 0, P1: 0, P2: 0 }
  for (const r of rows) pain[r.pain.level]++
  return {
    routes: rows.length,
    withView: withView.length,
    redirects: rows.filter((r) => r.kind === 'redirect').length,
    unresolved: rows.filter((r) => r.kind === 'unresolved').length,
    distinctFiles: new Set(withView.map((r) => r.file)).size,
    perCriterion: per,
    pain,
  }
}

const LABEL = {
  loading: 'Loading', skeleton: 'Skeleton', empty: 'Rỗng+HD', error: 'Lỗi+Thử lại',
  responsive: '≤768px', vi: 'Nhãn VI', a11y: 'a11y',
}

function printMarkdown(rows) {
  console.log('| # | Route (`path`) | View file | Loading | Skeleton | Rỗng+HD | Lỗi+Thử lại | ≤768px | Nhãn VI | a11y | Đau |')
  console.log('|---|---|---|---|---|---|---|---|---|---|---|')
  for (const r of rows) {
    const file = r.file ? `\`${r.file}\`` : '— *(redirect)*'
    const c = CRITERIA.map((k) => r.cells[k]).join(' | ')
    console.log(`| ${r.index} | \`${r.path}\` | ${file} | ${c} | ${r.pain.level} |`)
  }
}

function printSummary(rows) {
  const s = summarize(rows)
  console.log(`Route thật:            ${s.routes}`)
  console.log(`  ├─ có view:          ${s.withView}`)
  console.log(`  ├─ redirect:         ${s.redirects}`)
  console.log(`  └─ không giải được:  ${s.unresolved}`)
  console.log(`File view distinct:    ${s.distinctFiles}`)
  console.log('')
  console.log(`Nợ theo tiêu chí (mẫu số = ${s.withView} route có view):`)
  const order = [...CRITERIA].sort((a, b) => s.perCriterion[b].bad - s.perCriterion[a].bad)
  for (const c of order) {
    const p = s.perCriterion[c]
    const pct = Math.round((p.bad / s.withView) * 100)
    console.log(`  ${LABEL[c].padEnd(12)} ❌ ${String(p.bad).padStart(3)}  n/a ${String(p.na).padStart(3)}  ✅ ${String(p.ok).padStart(3)}   (${pct}%)`)
  }
  console.log('')
  console.log(`Mức đau: P0 ${s.pain.P0} · P1 ${s.pain.P1} · P2 ${s.pain.P2}`)
}

/** Đối chiếu output bộ dò với bảng §3.1 đang nằm trong tài liệu. */
function check(rows) {
  if (!existsSync(DOC)) {
    console.error(`KHÔNG tìm thấy ${DOC}`)
    process.exitCode = 1
    return
  }
  const doc = readFileSync(DOC, 'utf-8')
  const a = doc.indexOf('### 3.1 Bảng đầy đủ')
  const b = doc.indexOf('### 3.2', a)
  const docRows = []
  for (const line of doc.slice(a, b).split('\n')) {
    if (!line.startsWith('|')) continue
    const cells = line.split('|').slice(1, -1).map((c) => c.trim())
    if (cells.length !== 11 || !/^\d+$/.test(cells[0])) continue
    docRows.push({
      path: cells[1].replace(/^`|`$/g, ''),
      file: cells[2],
      cells: Object.fromEntries(CRITERIA.map((c, i) => [c, cells[3 + i]])),
      pain: cells[10],
    })
  }

  const byPath = new Map(docRows.map((r) => [r.path, r]))
  const missing = rows.filter((r) => !byPath.has(r.path)).map((r) => r.path)
  const extra = docRows.filter((r) => !rows.some((x) => x.path === r.path)).map((r) => r.path)

  console.log(`Route (bộ dò): ${rows.length}   ·   dòng bảng §3.1: ${docRows.length}`)
  console.log(`Thiếu trong doc: ${missing.length ? missing.join(', ') : '(không)'}`)
  console.log(`Thừa trong doc:  ${extra.length ? extra.join(', ') : '(không)'}`)

  const diff = { total: 0, perCriterion: Object.fromEntries(CRITERIA.map((c) => [c, 0])) }
  const painDiff = []
  const cellDiff = []
  for (const r of rows) {
    const d = byPath.get(r.path)
    if (!d) continue
    for (const c of CRITERIA) {
      if (d.cells[c] !== r.cells[c]) {
        diff.perCriterion[c]++
        diff.total++
        cellDiff.push(`${r.path} · ${LABEL[c]}: doc=${d.cells[c]} dò=${r.cells[c]}`)
      }
    }
    if (d.pain !== r.pain.level) painDiff.push(`${r.path}: doc=${d.pain} dò=${r.pain.level}`)
  }
  if (process.argv.includes('--verbose')) {
    console.log('')
    console.log('Ô lệch (doc = bảng đã hiệu đính tay ⇄ dò = regex thuần):')
    for (const c of cellDiff) console.log(`  ${c}`)
  }
  console.log('')
  console.log(`Ô lệch doc ⇄ bộ dò: ${diff.total} / ${rows.length * 7}`)
  for (const c of CRITERIA) console.log(`  ${LABEL[c].padEnd(12)} ${diff.perCriterion[c]}`)
  console.log(`Dòng lệch mức đau: ${painDiff.length}`)
  if (process.argv.includes('--verbose')) for (const p of painDiff) console.log(`  ${p}`)
}

const rows = inventory()
if (process.argv.includes('--json')) console.log(JSON.stringify({ summary: summarize(rows), rows }, null, 2))
else if (process.argv.includes('--summary')) printSummary(rows)
else if (process.argv.includes('--check')) check(rows)
else printMarkdown(rows)
