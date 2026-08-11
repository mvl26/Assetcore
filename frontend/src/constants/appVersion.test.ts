// Guard đồng bộ PHIÊN BẢN toàn hệ thống (AC-VER-01).
//
// Bối cảnh: trước đây `AppSidebar.vue` hardcode chuỗi "AssetCore v0.1.0" nên mỗi
// lần release phải sửa tay (commit `1dedba9 chore(release): show version ... in
// sidebar`); quên một lần là UI báo sai version. Đồng thời `__APP_VERSION__` đã
// được Vite bơm sẵn nhưng KHÔNG file nào tiêu thụ, và fallback kẹt ở '0.0.3'.
//
// Bộ test này khoá 3 bất biến:
//   1. `frontend/package.json::version` == `assetcore/__init__.py::__version__`
//      (FE và BE không được lệch — BE là SSoT sản phẩm).
//   2. `define` được khai ở CẢ vite.config.ts lẫn vitest.config.ts (hai config
//      độc lập; thiếu bên nào thì môi trường đó vỡ hoặc ship sai version).
//   3. Không file nào trong `src/` hardcode lại chuỗi version.
import { readFileSync, readdirSync } from 'node:fs'
import { resolve, dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, it, expect } from 'vitest'
import { APP_VERSION, APP_VERSION_LABEL, APP_VERSION_FULL_LABEL } from './appVersion'

const HERE = dirname(fileURLToPath(import.meta.url))
const FRONTEND_ROOT = resolve(HERE, '../..')
const REPO_ROOT = resolve(FRONTEND_ROOT, '..')
const SRC_ROOT = resolve(FRONTEND_ROOT, 'src')

const pkg = JSON.parse(readFileSync(resolve(FRONTEND_ROOT, 'package.json'), 'utf-8')) as {
  version: string
}

/** Đọc `__version__ = "x.y.z"` từ `assetcore/__init__.py` (SSoT sản phẩm). */
function readBackendVersion(): string {
  const src = readFileSync(resolve(REPO_ROOT, 'assetcore/__init__.py'), 'utf-8')
  const m = src.match(/^__version__\s*=\s*["']([^"']+)["']/m)
  if (!m) throw new Error('Không tìm thấy __version__ trong assetcore/__init__.py')
  return m[1]
}

/** Duyệt đệ quy `src/`, trả về mọi file .ts/.vue (bỏ qua chính SSoT + test này). */
function walkSrc(dir: string, acc: string[] = []): string[] {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = join(dir, entry.name)
    if (entry.isDirectory()) walkSrc(full, acc)
    else if (/\.(ts|vue)$/.test(entry.name)) acc.push(full)
  }
  return acc
}

const SSOT_FILES = new Set([
  resolve(SRC_ROOT, 'constants/appVersion.ts'),
  resolve(SRC_ROOT, 'constants/appVersion.test.ts'),
])

describe('AC-VER-01 — phiên bản đồng bộ FE ↔ BE', () => {
  it('AC-VER-01a: package.json khớp assetcore/__init__.py', () => {
    expect(pkg.version).toBe(readBackendVersion())
  })

  it('AC-VER-01b: version đúng dạng semver x.y.z', () => {
    expect(pkg.version).toMatch(/^\d+\.\d+\.\d+(?:[-+].+)?$/)
  })

  it('AC-VER-01c: APP_VERSION lấy từ define, không phải sentinel 0.0.0', () => {
    // Nếu `define` thiếu trong vitest.config.ts thì APP_VERSION rơi về '0.0.0'.
    expect(APP_VERSION).toBe(pkg.version)
    expect(APP_VERSION).not.toBe('0.0.0')
  })

  it('AC-VER-01d: nhãn hiển thị dẫn xuất từ APP_VERSION', () => {
    expect(APP_VERSION_LABEL).toBe(`v${pkg.version}`)
    expect(APP_VERSION_FULL_LABEL).toBe(`AssetCore v${pkg.version}`)
  })
})

describe('AC-VER-02 — không hardcode version ở nơi khác', () => {
  it('AC-VER-02a: define __APP_VERSION__ khai ở CẢ hai config, đọc từ package.json', () => {
    for (const cfg of ['vite.config.ts', 'vitest.config.ts']) {
      const src = readFileSync(resolve(FRONTEND_ROOT, cfg), 'utf-8')
      expect(src, `${cfg} phải khai define __APP_VERSION__`).toContain('__APP_VERSION__')
      expect(src, `${cfg} phải đọc version từ package.json`).toMatch(
        /JSON\.stringify\(pkg\.version\)/,
      )
    }
  })

  it('AC-VER-02b: không file nào trong src/ hardcode "AssetCore v<số>"', () => {
    const offenders = walkSrc(SRC_ROOT)
      .filter((f) => !SSOT_FILES.has(f))
      .filter((f) => /AssetCore\s+v\d/.test(readFileSync(f, 'utf-8')))
      .map((f) => f.slice(FRONTEND_ROOT.length + 1))
    expect(offenders, 'Dùng APP_VERSION_FULL_LABEL từ @/constants/appVersion').toEqual([])
  })

  it('AC-VER-02c: sidebar bind SSoT, không phải chuỗi cứng', () => {
    const sidebar = readFileSync(
      resolve(SRC_ROOT, 'components/common/AppSidebar.vue'),
      'utf-8',
    )
    expect(sidebar).toContain("from '@/constants/appVersion'")
    expect(sidebar).toMatch(/\{\{\s*APP_VERSION_FULL_LABEL\s*\}\}/)
  })
})
