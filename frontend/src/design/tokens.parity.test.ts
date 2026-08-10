// AC-UX-032 — Guard parity 2 chiều: token ngữ nghĩa Tailwind ⇄ CSS var `--ac-color-*`.
//
// Bối cảnh (docs/ui-ux/01_DESIGN_SYSTEM.md §2): trước vòng này FE có 0 token màu ngữ nghĩa
// (`tailwind.config.js` chỉ có `brand` + `ink`) ⇒ mỗi màn tự chế `emerald-600`/`red-500`…
// (6119 lần hardcode trong `views/`). Khai token ở MỘT nơi là chưa đủ: nếu Tailwind có
// `success.500` mà `:root` không có `--ac-color-success-500` thì lớp CSS thuần (hoặc ngược
// lại) sẽ trôi màu âm thầm. Guard này khoá 6 bất biến:
//
//   INV-DS-1  5 họ ngữ nghĩa có mặt, mỗi họ ĐÚNG tập bậc {50,500,700}.
//   INV-DS-2  (xuôi)  ∀ token trong config ⇒ có `--ac-color-<họ>-<bậc>` cùng hex.
//   INV-DS-3  (ngược) ∀ `--ac-color-*` trong main.css ⇒ có token trong config (0 var mồ côi).
//   INV-DS-4  Pin "0 đổi màu hiển thị": bậc 500 ≡ biến `--color-*` đang chạy.
//   INV-DS-5  Hex lowercase 6 ký tự; 5 hex bậc 500 đôi một khác nhau (chống copy-paste nhầm họ).
//   INV-DS-6  Regression: `brand`/`ink` (2 họ cũ) KHÔNG bị đụng.
//
// Guard đọc OBJECT THẬT của `tailwind.config.js` (import ESM) chứ không regex file nguồn.
import { describe, it, expect, beforeAll } from 'vitest'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const HERE = dirname(fileURLToPath(import.meta.url))
// src/design → src → frontend
const FRONTEND_ROOT = resolve(HERE, '../..')
const MAIN_CSS = resolve(FRONTEND_ROOT, 'src/assets/styles/main.css')

/** 5 họ ngữ nghĩa đã chốt (01_DESIGN_SYSTEM.md §2.1). */
const FAMILIES = ['success', 'warning', 'danger', 'info', 'neutral'] as const
/** Tập bậc đã chốt — thêm bậc mới phải hỏi BA (§0 "Ask first"). */
const SHADES = ['50', '500', '700'] as const

/** Bậc 500 phải trùng byte-per-byte với biến `--color-*` đang chạy ⇒ 0 đổi màu. */
const PIN_500: Record<string, string> = {
  success: '--color-success',
  warning: '--color-warning',
  danger: '--color-danger',
  info: '--color-info',
  neutral: '--color-neutral',
}

const HEX_RE = /^#[0-9a-f]{6}$/

type ColorScale = Record<string, string>
type TailwindColors = Record<string, ColorScale | string>

let colors: TailwindColors
let css: string
/** `success.500` → `#059669` (từ tailwind.config.js) */
let configTokens: Map<string, string>
/** `success.500` → `#059669` (từ `--ac-color-success-500` trong main.css) */
let cssTokens: Map<string, string>
/** `--color-success` → `#059669` (biến cũ, dùng cho INV-DS-4) */
let legacyVars: Map<string, string>

beforeAll(async () => {
  const mod = (await import('../../tailwind.config.js')) as {
    default: { theme: { extend: { colors: TailwindColors } } }
  }
  colors = mod.default.theme.extend.colors
  css = readFileSync(MAIN_CSS, 'utf8')

  configTokens = new Map()
  for (const family of FAMILIES) {
    const scale = colors[family]
    if (!scale || typeof scale === 'string') continue
    for (const [shade, hex] of Object.entries(scale)) {
      configTokens.set(`${family}.${shade}`, String(hex))
    }
  }

  cssTokens = new Map()
  for (const m of css.matchAll(/--ac-color-([a-z]+)-(\d{2,3}):\s*(#[0-9a-fA-F]{3,8})\s*;/g)) {
    cssTokens.set(`${m[1]}.${m[2]}`, m[3])
  }

  legacyVars = new Map()
  for (const m of css.matchAll(/(--color-(?:primary|success|warning|danger|info|neutral)):\s*(#[0-9a-fA-F]{3,8})\s*;/g)) {
    legacyVars.set(m[1], m[2])
  }
})

describe('Design tokens — parity Tailwind ⇄ CSS var (AC-UX-032)', () => {
  it('INV-DS-1: 5 họ ngữ nghĩa có mặt, mỗi họ đúng tập bậc {50,500,700}', () => {
    for (const family of FAMILIES) {
      const scale = colors[family]
      expect(scale, `thiếu họ token "${family}" trong theme.extend.colors`).toBeTruthy()
      expect(typeof scale).toBe('object')
      expect(Object.keys(scale as ColorScale).sort()).toEqual([...SHADES].sort())
    }
  })

  it('INV-DS-2 (xuôi): mọi token Tailwind đều có --ac-color-* cùng hex trong main.css', () => {
    const missing: string[] = []
    const mismatched: string[] = []
    for (const [key, hex] of configTokens) {
      const cssHex = cssTokens.get(key)
      if (cssHex === undefined) missing.push(`--ac-color-${key.replace('.', '-')}`)
      else if (cssHex !== hex) mismatched.push(`${key}: tailwind=${hex} css=${cssHex}`)
    }
    expect(missing, 'CSS var còn thiếu').toEqual([])
    expect(mismatched, 'hex lệch giữa 2 nguồn').toEqual([])
  })

  it('INV-DS-3 (ngược): 0 var --ac-color-* mồ côi (không có token Tailwind tương ứng)', () => {
    const orphans: string[] = []
    for (const key of cssTokens.keys()) {
      if (!configTokens.has(key)) orphans.push(`--ac-color-${key.replace('.', '-')}`)
    }
    expect(orphans, 'var CSS không có token Tailwind đối ứng').toEqual([])
    // Hai tập phải bằng nhau về lực lượng (5 họ × 3 bậc = 15).
    expect(cssTokens.size).toBe(configTokens.size)
    expect(configTokens.size).toBe(FAMILIES.length * SHADES.length)
  })

  it('INV-DS-4: bậc 500 ≡ biến --color-* đang chạy ⇒ 0 đổi màu hiển thị', () => {
    for (const family of FAMILIES) {
      const varName = PIN_500[family]
      const legacy = legacyVars.get(varName)
      expect(legacy, `main.css :root thiếu ${varName}`).toBeTruthy()
      expect(configTokens.get(`${family}.500`), `${family}.500 phải bằng ${varName}`).toBe(legacy)
    }
    // `--color-info` là biến MỚI của vòng này (trước đây :root thiếu dù .alert-info đã dùng họ blue).
    expect(legacyVars.get('--color-info')).toBe('#2563eb')
  })

  it('INV-DS-5: hex lowercase 6 ký tự; 5 hex bậc 500 đôi một khác nhau', () => {
    for (const [key, hex] of configTokens) {
      expect(hex, `token ${key} phải khớp ${HEX_RE}`).toMatch(HEX_RE)
    }
    for (const [key, hex] of cssTokens) {
      expect(hex, `var ${key} phải khớp ${HEX_RE}`).toMatch(HEX_RE)
    }
    const five = FAMILIES.map((f) => configTokens.get(`${f}.500`))
    expect(new Set(five).size, `5 màu nền tảng bị trùng: ${five.join(', ')}`).toBe(5)
  })

  it('INV-DS-6: regression — họ brand/ink cũ không bị đụng', () => {
    const brand = colors.brand as ColorScale
    const ink = colors.ink as ColorScale
    expect(brand?.['600']).toBe('#2563eb')
    expect(ink?.['900']).toBe('#0d1117')
  })
})
