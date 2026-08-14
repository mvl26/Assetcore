// TDD — Responsive DoD static guards (ADR-IMM00-RESPONSIVE D1/D5 + F6/F7).
// TC-RWD-01 : grep 'min-[|max-[' trong src/views = 0 (không ad-hoc breakpoint px).
// F6 (static): ListCard.vue <table> có ancestor .overflow-x-auto.
// F7 (static): PersonaDashboardShell KPI grid container chứa md:grid-cols-*.
// TC-RWD-10 (doc grep): lessons-learned.md chứa 'LL-FE-34'; component-patterns.md chứa '## Responsive'.
import { describe, it, expect } from 'vitest'
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { resolve } from 'node:path'
import { FRONTEND_ROOT, VIEWS, listFiles } from '@/test/paths'

const SRC = resolve(FRONTEND_ROOT, 'src')

function walk(dir: string, acc: string[] = []): string[] {
  for (const entry of readdirSync(dir)) {
    const full = resolve(dir, entry)
    if (statSync(full).isDirectory()) walk(full, acc)
    else if (full.endsWith('.vue')) acc.push(full)
  }
  return acc
}

describe('TC-RWD-01 — no ad-hoc px breakpoints in src/views (D1 guard)', () => {
  it('grep min-[ / max-[ trong src/views = 0', () => {
    const viewFiles = walk(resolve(SRC, 'views'))
    const offenders: string[] = []
    // Ad-hoc breakpoint = arbitrary-value width prefix: `min-[Npx]:` / `max-[Npx]:`.
    // Tailwind arbitrary-value media-query prefix syntax. Touch-target utilities
    // như `min-h-[44px]` / `min-w-[44px]` KHÔNG phải breakpoint (không có dấu `:` media-prefix).
    const adHocBreakpoint = /\b(?:min|max)-\[[^\]]+\]:/
    for (const f of viewFiles) {
      const txt = readFileSync(f, 'utf8')
      if (adHocBreakpoint.test(txt)) offenders.push(f.replace(SRC, 'src'))
    }
    expect(offenders).toEqual([])
  })

  it('tailwind.config KHÔNG khai theme.screens (giữ default sm/md/lg/xl)', () => {
    const cfg = readFileSync(resolve(FRONTEND_ROOT, 'tailwind.config.js'), 'utf8')
    expect(/screens\s*:/.test(cfg)).toBe(false)
  })

  it('KHÔNG có PWA artifact (manifest.webmanifest / sw.ts)', () => {
    const files = walk(SRC).concat(
      readdirSync(FRONTEND_ROOT)
        .filter((e) => !statSync(resolve(FRONTEND_ROOT, e)).isDirectory())
        .map((e) => resolve(FRONTEND_ROOT, e)),
    )
    const pwa = files.filter((f) => /manifest\.webmanifest$|(^|\/)sw\.ts$/.test(f))
    expect(pwa).toEqual([])
  })
})

describe('F6 — ListCard <table> bọc overflow-x-auto (P3)', () => {
  it('table có ancestor div.overflow-x-auto', () => {
    const src = readFileSync(resolve(SRC, 'components/dashboard/ListCard.vue'), 'utf8')
    // Cấu trúc mong đợi: <div class="overflow-x-auto"> ... <table ...> ... </div>
    const wrapIdx = src.indexOf('overflow-x-auto')
    const tableIdx = src.indexOf('<table')
    expect(wrapIdx).toBeGreaterThan(-1)
    expect(tableIdx).toBeGreaterThan(wrapIdx)
  })
})

describe('F7 — PersonaDashboardShell KPI grid có bước tablet md (P2)', () => {
  it('KPI grid container chứa md:grid-cols-*', () => {
    const src = readFileSync(resolve(SRC, 'components/dashboard/PersonaDashboardShell.vue'), 'utf8')
    expect(/md:grid-cols-\d/.test(src)).toBe(true)
    // mobile-first base 1-col
    expect(/grid-cols-1/.test(src)).toBe(true)
  })
})

describe('TC-RWD-10 — DoD ghi vào skill FE (D5)', () => {
  const SKILL = resolve(FRONTEND_ROOT, '..', '.claude', 'skills', 'assetcore-fe', 'references')
  it('lessons-learned.md chứa LL-FE-34 Responsive DoD', () => {
    const ll = readFileSync(resolve(SKILL, 'lessons-learned.md'), 'utf8')
    expect(ll.includes('LL-FE-34')).toBe(true)
    expect(/Responsive DoD/i.test(ll)).toBe(true)
  })
  it('component-patterns.md chứa ## Responsive', () => {
    const cp = readFileSync(resolve(SKILL, 'component-patterns.md'), 'utf8')
    expect(cp.includes('## Responsive')).toBe(true)
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
