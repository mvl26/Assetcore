// Copyright (c) 2026, AssetCore Team
// Cưỡng chế vị trí & tên file NGUỒN của FE — SSoT văn bản: skill `assetcore-structure`.
//
// ─── Vì sao có file này ───────────────────────────────────────────────────────
// `testFileConvention.guard.test.ts` chỉ canh file TEST. Quy ước file NGUỒN
// (`api/immXX.ts` mirror BE · `stores/immXX.ts` cùng khuôn · `views/<domain>/`
// đặt theo nghiệp vụ) tới nay mới chỉ là văn bản trong skill — mà bài học của cả
// đợt chuẩn hoá này là *rule văn bản luôn bị bỏ qua*.
//
// Guard này khoá:
//   F1 — `api/` và `stores/` dùng cùng một khuôn tên; store của module IMM phải
//        có API client đối ứng (và ngược lại) — lệch là dấu hiệu tầng bị hụt.
//   F2 — `views/` và `components/` chỉ chứa thư mục miền kebab-case, KHÔNG `immXX`.
//   F3 — 4 lớp kiến trúc không bị nhảy cóc: view KHÔNG gọi thẳng `axios`.
//   F4 — `src/test/` là harness, KHÔNG được chứa file `.test.ts`.
//
// Nguyên tắc allowlist: ngoại lệ tồn dư ĐÓNG BĂNG, CHỈ-GIẢM — guard tự đỏ nếu
// allowlist dài ra. Muốn thêm một dòng thì việc cần làm là sửa mã, không sửa sổ.
import { describe, it, expect } from 'vitest'
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { resolve } from 'node:path'
import { API, COMPONENTS, SRC, STORES, VIEWS, listFiles, rel } from '@/test/paths'

const IMM_MODULE = /^imm\d{2}\.ts$/
const KEBAB = /^[a-z0-9]+(-[a-z0-9]+)*$/

/** File `.ts` nguồn (không phải test) ngay trong một thư mục. */
function sourceFilesIn(dir: string): string[] {
  return readdirSync(dir)
    .filter((f) => f.endsWith('.ts') && !f.endsWith('.test.ts'))
    .sort()
}

/**
 * ĐÓNG BĂNG · CHỈ-GIẢM — module IMM có `api/immXX.ts` nhưng CHƯA có store đối ứng.
 * Hợp lệ khi module chỉ đọc (view dùng thẳng API client qua composable), nhưng
 * mỗi dòng ở đây là một chỗ cần rà: có thật sự không cần state dùng chung không?
 */
const F1_NO_STORE_ALLOWLIST: readonly string[] = []

/**
 * ĐÓNG BĂNG · CHỈ-GIẢM — file `.vue` còn gọi thẳng `axios`, nhảy qua tầng `api/`.
 *
 * Hai dòng dưới là nợ ĐO ĐƯỢC 2026-08-14, cần trả sớm:
 *  • `LinkSearch.vue` gọi `assetcore.api.imm04.search_link` bằng axios trần —
 *    thiếu hàm đối ứng trong `api/imm04.ts`. Thêm `searchLink()` rồi xoá dòng này.
 *  • `ReferenceDataView.vue` POST thẳng `/api/method/upload_file` — đúng
 *    anti-pattern GATE-9/LL-FE-54 (SSoT là `api/files.ts::uploadAttachment`).
 *
 * XOÁ dòng khi đã chuyển; TUYỆT ĐỐI không thêm dòng mới.
 */
const F3_ALLOWLIST: readonly string[] = [
  'components/common/LinkSearch.vue',
  'views/master-data/ReferenceDataView.vue',
]
const F3_FROZEN_SIZE = 2

describe('F1 — `api/` và `stores/` cùng khuôn tên IMM-coded', () => {
  it('mọi `stores/immXX.ts` đều có `api/immXX.ts` đối ứng', () => {
    const apis = new Set(sourceFilesIn(API).filter((f) => IMM_MODULE.test(f)))
    const orphanStores = sourceFilesIn(STORES)
      .filter((f) => IMM_MODULE.test(f))
      .filter((f) => !apis.has(f))
    expect(
      orphanStores,
      'store IMM-coded mà không có API client cùng tên — store phải gọi qua `api/`, ' +
        'không tự dựng transport riêng (vi phạm kiến trúc 4 lớp).',
    ).toEqual([])
  })

  it('sổ "API không có store" CHỈ ĐƯỢC GIẢM', () => {
    expect(F1_NO_STORE_ALLOWLIST.length).toBeLessThanOrEqual(0)
  })

  it('mọi dòng trong sổ nợ axios trỏ file CÓ THẬT — dọn sổ cùng lượt sửa', () => {
    const dead = F3_ALLOWLIST.filter((p) => !listFiles(SRC, { ext: '.vue', min: 190 }).some((f) => rel(f) === p))
    expect(dead, 'sổ nợ trỏ file đã xoá/đổi tên').toEqual([])
  })

  it('tên file trong `api/` và `stores/` là camelCase, không dấu chấm', () => {
    const bad: string[] = []
    for (const dir of [API, STORES]) {
      for (const f of sourceFilesIn(dir)) {
        if (!/^[a-z][A-Za-z0-9]*\.ts$/.test(f)) bad.push(`${rel(dir)}/${f}`)
      }
    }
    expect(
      bad,
      'file nguồn `.ts` phải camelCase và KHÔNG có dấu chấm giữa tên — chấm làm mờ ' +
        'ranh giới với quy ước `<Nguồn>.<khiaCanh>.test.ts`.',
    ).toEqual([])
  })
})

describe('F2 — `views/` và `components/` chỉ chứa thư mục MIỀN kebab-case', () => {
  it('0 thư mục đặt theo mã IMM (URL là tên miền, không phải mã)', () => {
    const bad: string[] = []
    for (const root of [VIEWS, COMPONENTS]) {
      for (const name of readdirSync(root)) {
        const full = resolve(root, name)
        if (!statSync(full).isDirectory()) continue
        if (/^imm\d{2}$/i.test(name)) bad.push(`${rel(root)}/${name}`)
        else if (!KEBAB.test(name) && name !== 'tests') bad.push(`${rel(root)}/${name}`)
      }
    }
    expect(
      bad,
      'thư mục miền phải kebab-case theo NGHIỆP VỤ (`cm`, `tech-specs`), KHÔNG theo mã ' +
        '`immXX` — đường dẫn URL là tên miền nên thư mục phải khớp URL.',
    ).toEqual([])
  })

  it('mọi thư mục miền có ít nhất 1 file nguồn (không có thư mục rỗng)', () => {
    const empty: string[] = []
    for (const root of [VIEWS, COMPONENTS]) {
      for (const name of readdirSync(root)) {
        const full = resolve(root, name)
        if (!statSync(full).isDirectory() || name === 'tests') continue
        const hasSource = readdirSync(full).some(
          (f) => (f.endsWith('.vue') || (f.endsWith('.ts') && !f.endsWith('.test.ts'))),
        )
        if (!hasSource) empty.push(`${rel(root)}/${name}`)
      }
    }
    expect(empty, 'thư mục miền không có file nguồn nào — xoá hoặc gộp.').toEqual([])
  })
})

describe('F3 — kiến trúc 4 lớp: view/component KHÔNG gọi thẳng axios', () => {
  it('sổ ngoại lệ CHỈ ĐƯỢC GIẢM', () => {
    expect(
      F3_ALLOWLIST.length,
      'sổ nợ axios dài ra = có view MỚI nhảy qua tầng api/',
    ).toBeLessThanOrEqual(F3_FROZEN_SIZE)
  })

  it('0 file `.vue` import axios trực tiếp', () => {
    const allow = new Set(F3_ALLOWLIST)
    const offenders = listFiles(SRC, { ext: '.vue', min: 190 })
      .map((p) => ({ p, r: rel(p) }))
      .filter(({ r }) => !allow.has(r))
      .filter(({ p }) => /from\s+['"](axios|@\/api\/axios)['"]/.test(readFileSync(p, 'utf8')))
      .map(({ r }) => r)
    expect(
      offenders,
      'View gọi thẳng axios ⇒ nhảy qua tầng `api/`: mất bóc envelope Frappe ' +
        '(`{message:{success,data}}`), mất `ApiError`, mất interceptor CSRF/401. ' +
        'Gọi qua `@/api/<module>` hoặc store.',
    ).toEqual([])
  })
})

describe('F4 — `src/test/` là harness, không phải nhà của test', () => {
  it('0 file `.test.ts` trong `src/test/`', () => {
    const stray = readdirSync(resolve(SRC, 'test')).filter((f) => f.endsWith('.test.ts'))
    expect(
      stray,
      '`src/test/` chỉ chứa harness dùng chung (`paths.ts`, `stripComments.ts`…). ' +
        'File test thuộc `<thư-mục-nguồn>/tests/`, `src/guards/` hoặc `src/integration/`.',
    ).toEqual([])
  })

  it('`src/test/paths.ts` tồn tại — mọi guard neo đường dẫn qua nó', () => {
    const files = sourceFilesIn(resolve(SRC, 'test'))
    expect(files, 'thiếu `paths.ts` ⇒ guard sẽ quay lại tính đường dẫn theo độ sâu').toContain(
      'paths.ts',
    )
  })
})
