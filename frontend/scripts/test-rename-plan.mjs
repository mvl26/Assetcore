#!/usr/bin/env node
// test-rename-plan.mjs — sinh BẢNG ÁNH XẠ đổi tên file test FE. CHỈ ĐỌC, KHÔNG sửa gì.
//
// Vì sao có file này (SPEC §8): đổi tên ~190 file test KHÔNG miễn phí — mỗi tên còn bị
// nhắc trong `docs/` và `.claude/`, và một số doc có guard parity đối chiếu. Bảng phải
// được NGƯỜI duyệt trước khi `git mv` + sweep, và phải tái lập được.
//
// Quy ước đích (SPEC §5.1): test của MỘT file nguồn nằm trong `tests/` cạnh nguồn, tên
//   `<thư-mục-nguồn>/tests/<Nguồn>.test.ts`            — nếu là test duy nhất của nguồn đó
//   `<thư-mục-nguồn>/tests/<Nguồn>.<khiaCanh>.test.ts` — nếu tách nhiều khía cạnh
// `<Nguồn>` khớp CHÍNH XÁC tên file nguồn; `<khiaCanh>` camelCase, đã lược tiền tố
// trùng tên nguồn.
//
// Cách dùng:
//   node frontend/scripts/test-rename-plan.mjs           # bảng người đọc
//   node frontend/scripts/test-rename-plan.mjs --csv     # cũ,mới,sốTríchDẫn,nhóm
//   node frontend/scripts/test-rename-plan.mjs --group 4a
import { readFileSync, readdirSync, existsSync, statSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve, relative } from 'node:path'

function findFrontendRoot() {
  let dir = dirname(fileURLToPath(import.meta.url))
  for (let i = 0; i < 12; i += 1) {
    if (existsSync(resolve(dir, 'package.json')) && existsSync(resolve(dir, 'vite.config.ts'))) return dir
    const up = dirname(dir)
    if (up === dir) break
    dir = up
  }
  throw new Error('[test-rename-plan] không tìm thấy gốc frontend/')
}

const FRONTEND = findFrontendRoot()
const REPO_ROOT = resolve(FRONTEND, '..')
const SRC = resolve(FRONTEND, 'src')

/** Nhà riêng — đã chuẩn hoá ở lô L2/L3, không đụng tới. */
const OWN_HOUSES = new Set(['guards', 'integration', 'test'])

/**
 * Đặt tay khi thuật toán ra TRÙNG ĐÍCH (hai test cùng một nguồn, khía cạnh bị rút
 * gọn về cùng một chữ). Người đặt tên, không phải máy.
 */
const OVERRIDES = {
  // cả hai đều kiểm CTA của CMWorkOrderDetailView nhưng theo HAI hợp đồng khác nhau
  'views/cm/cmDetailCtaGating.test.ts': 'CMWorkOrderDetailView.availableActions.test.ts',
  'views/cm/cmWorkOrderCtaGating.test.ts': 'CMWorkOrderDetailView.allowedTransitions.test.ts',
}

function walk(dir, out = []) {
  for (const e of readdirSync(dir)) {
    const p = resolve(dir, e)
    if (statSync(p).isDirectory()) walk(p, out)
    else if (e.endsWith('.test.ts')) out.push(p)
  }
  return out
}

/**
 * Import nguồn thuộc "thư mục nguồn" của file test.
 * Test nằm ở `<X>/tests/` ⇒ thư mục nguồn là `<X>`; nếu chưa dời thì là chính `<X>`.
 */
function localSources(text, ownDir) {
  const specs = [...text.matchAll(/(?:from|vi\.mock\(|import\()\s*['"]([^'"]+)['"]/g)].map((m) => m[1])
  const found = new Set()
  for (const s of specs) {
    let name = null
    if (s.startsWith('./')) name = s.slice(2)
    else if (s.startsWith('@/')) {
      const rest = s.slice(2)
      const d = rest.includes('/') ? rest.slice(0, rest.lastIndexOf('/')) : ''
      if (d === ownDir) name = rest.slice(rest.lastIndexOf('/') + 1)
    }
    if (!name || name.includes('/')) continue
    for (const cand of [name, `${name}.ts`, `${name}.vue`]) {
      if (cand.endsWith('.test.ts')) continue
      if (existsSync(resolve(SRC, ownDir, cand))) { found.add(cand); break }
    }
  }
  return [...found]
}

const lower1 = (s) => (s ? s.charAt(0).toLowerCase() + s.slice(1) : s)

/** Tách camelCase/PascalCase thành token thường: `assetScanInfoSerial` → [asset,scan,info,serial]. */
const tokens = (s) =>
  s.replace(/[._-]+/g, ' ')
    .replace(/([a-z0-9])([A-Z])/g, '$1 $2')
    .replace(/([A-Z]+)([A-Z][a-z])/g, '$1 $2')
    .split(/\s+/).filter(Boolean).map((t) => t.toLowerCase())

/**
 * Khía cạnh = phần tên test còn lại sau khi LƯỢC các token đầu đã có trong tên nguồn.
 * `smartSelectResilience` ⇄ `SmartSelect`        → `resilience`
 * `assetScanInfoSerial`   ⇄ `AssetScanInfoView`  → `serial`
 * `personaShellResponsive`⇄ `PersonaDashboardShell` → `responsive`
 */
function aspectOf(testStem, sourceStem) {
  const src = new Set(tokens(sourceStem))
  const t = tokens(testStem)
  let i = 0
  while (i < t.length - 1 && src.has(t[i])) i += 1 // giữ lại ÍT NHẤT 1 token
  if (i === 0) return lower1(testStem)
  const rest = t.slice(i)
  return rest.map((w, k) => (k === 0 ? w : w.charAt(0).toUpperCase() + w.slice(1))).join('')
}

const LOT_OF_DIR = (raw) => {
  const d = raw.replace(/\/tests$/, '')
  if (d.startsWith('components')) return '4a'
  if (/^(api|stores|constants|utils|composables|locales|router|directives|types)/.test(d)) return '4b'
  if (d === 'views/asset') return '4e'
  if (/^views\/(settings|admin|audit|eol|system|tech-specs|master-data|dashboard)/.test(d)) return '4c'
  if (d.startsWith('views')) return '4d'
  return '4b'
}

// ── đếm số lần tên bị nhắc ngoài frontend/ ────────────────────────────────────
function citationIndex() {
  const blob = []
  const collect = (dir) => {
    for (const e of readdirSync(dir)) {
      if (e === 'node_modules' || e === '.git') continue
      const p = resolve(dir, e)
      if (statSync(p).isDirectory()) collect(p)
      else if (/\.(md|py|json|mjs|txt)$/.test(e)) {
        try { blob.push(readFileSync(p, 'utf8')) } catch { /* bỏ qua file nhị phân */ }
      }
    }
  }
  for (const d of ['docs', '.claude/skills', '.claude/commands']) {
    const p = resolve(REPO_ROOT, d)
    if (existsSync(p)) collect(p)
  }
  const all = blob.join('\n')
  return (needle) => all.split(needle).length - 1
}

const cites = citationIndex()
const rows = []
for (const abs of walk(SRC).sort()) {
  const rel = relative(SRC, abs).split('\\').join('/')
  const ownDir = rel.includes('/') ? rel.slice(0, rel.lastIndexOf('/')) : ''
  if (OWN_HOUSES.has(ownDir.split('/')[0])) continue
  const base = rel.slice(rel.lastIndexOf('/') + 1)
  const stem = base.replace(/\.test\.ts$/, '')
  // `views/cm/tests/X.test.ts` ⇒ thư mục nguồn là `views/cm`.
  const srcDir = ownDir.endsWith('/tests') ? ownDir.slice(0, -'/tests'.length) : ownDir
  const text = readFileSync(abs, 'utf8')
  const sources = localSources(text, srcDir)

  if (sources.length !== 1) {
    rows.push({ rel, group: sources.length === 0 ? 'C4?' : 'C2', to: '', lot: '', n: 0,
                note: sources.length === 0 ? 'không import nguồn cục bộ' : `chạm ${sources.length} nguồn` })
    continue
  }
  const srcStem = sources[0].replace(/\.(vue|ts)$/, '')
  if (stem === srcStem) { rows.push({ rel, group: 'A', to: '', lot: '', n: 0, note: 'đã đúng' }); continue }
  if (stem.startsWith(`${srcStem}.`)) { rows.push({ rel, group: 'B', to: '', lot: '', n: 0, note: 'đã đúng' }); continue }

  // Tên test trùng HỆT tên nguồn (chỉ khác chữ hoa đầu) ⇒ không có khía cạnh nào,
  // chỉ cần chỉnh hoa/thường cho khớp nguồn.
  const sameName = tokens(stem).join('|') === tokens(srcStem).join('|')
  const aspect = sameName ? '' : aspectOf(stem, srcStem)
  const newBase = OVERRIDES[rel] ?? (aspect ? `${srcStem}.${aspect}.test.ts` : `${srcStem}.test.ts`)
  // Đích luôn nằm trong thư mục con `tests/` (quy ước 2026-08-13).
  const destDir = `${srcDir}/tests`
  rows.push({ rel, group: 'C1', to: `${destDir}/${newBase}`, lot: LOT_OF_DIR(srcDir),
              n: cites(base), note: `nguồn ${sources[0]}` })
}

// ── Phát hiện TRÙNG ĐÍCH: hai test khác nhau không được đổi ra cùng một tên ────
const c1 = rows.filter((r) => r.group === 'C1')
const taken = new Map()
for (const r of rows) if (r.group !== 'C1') taken.set(r.rel, r.rel)
const clash = new Map()
for (const r of c1) {
  const prev = clash.get(r.to)
  if (prev || taken.has(r.to)) {
    r.note += '  ⚠️ TRÙNG ĐÍCH'
    if (prev) prev.note = prev.note.includes('TRÙNG') ? prev.note : `${prev.note}  ⚠️ TRÙNG ĐÍCH`
  }
  clash.set(r.to, r)
}
const clashes = c1.filter((r) => r.note.includes('TRÙNG ĐÍCH'))
if (process.argv.includes('--csv')) {
  console.log('cu,moi,soTrichDan,nhom,lo')
  for (const r of c1) console.log(`${r.rel},${r.to},${r.n},C1,${r.lot}`)
} else {
  const gi = process.argv.indexOf('--group')
  const only = gi === -1 ? '' : (process.argv[gi + 1] || '').trim()
  const show = only ? c1.filter((r) => r.lot === only) : c1
  const w = Math.max(...show.map((r) => r.rel.length), 10)
  for (const lot of ['4a', '4b', '4c', '4d', '4e']) {
    const g = show.filter((r) => r.lot === lot)
    if (!g.length) continue
    console.log(`\n══ Đợt ${lot} — ${g.length} file · ${g.reduce((s, r) => s + r.n, 0)} lần trích dẫn`)
    for (const r of g.sort((a, b) => a.n - b.n)) {
      console.log(`  ${r.rel.padEnd(w)} → ${r.to.slice(r.to.lastIndexOf('/') + 1).padEnd(46)} [${r.n}]`)
    }
  }
  const by = (g) => rows.filter((r) => r.group === g).length
  console.log(`\n── Tổng: A ${by('A')} · B ${by('B')} · C1 ${c1.length} · C2 ${by('C2')} · C4? ${by('C4?')}`)
  console.log(`── Trích dẫn phải sweep: ${c1.reduce((s, r) => s + r.n, 0)}`)
  if (clashes.length) {
    console.log(`\n🔴 ${clashes.length} TRÙNG ĐÍCH — phải đặt tay trước khi chạy:`)
    for (const r of clashes) console.log(`   ${r.rel}  →  ${r.to}`)
  }
}
