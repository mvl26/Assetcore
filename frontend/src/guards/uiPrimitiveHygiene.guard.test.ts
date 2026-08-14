// TC-UX2-17/18/19 (AC-UX-034) — Hàng rào chống "lớp mới sinh ra đã mục".
//
// Bối cảnh: `src/views/` hiện có hàng nghìn lần hardcode palette thô (emerald/slate/red…)
// và 87/135 màn thiếu nhãn a11y. Tầng 0 chỉ có giá trị nếu CHÍNH NÓ sạch — nếu primitive
// cũng tự chế màu hoặc lọt chữ tiếng Anh thì mọi màn áp dụng nó sẽ nhân bản nợ.
// Guard đọc trực tiếp file `.vue` trên đĩa (không mount) và khoá 4 bất biến:
//
//   INV-UI-1 (A6a) 0 class palette thô — chỉ token ngữ nghĩa hoặc class @layer sẵn có.
//   INV-UI-2 (A6b) đúng 8 primitive, mỗi file có ĐÚNG 1 test cùng tên, barrel khớp khít.
//                  (vòng 3 thêm ListPageShell — ADR-UX-05; số 8 SUY RA từ EXPECTED_PRIMITIVES,
//                  KHÔNG hardcode ở assert độ dài.)
//   INV-UI-3 (A6c) 0 chuỗi hiển thị tiếng Anh (LL-FE-53) — cả text node lẫn copy mặc định.
//   INV-UI-4       chỉ dùng 3 bậc đã khai {50,500,700} của 5 họ ngữ nghĩa (bẫy deep-merge
//                  palette Tailwind: `neutral-100/200/…` mặc định vẫn "chạy" nhưng lệch tông).
import { describe, it, expect } from 'vitest'
import { readdirSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'
// NO-FORK: bộ bỏ comment dùng chung (`src/test/stripComments.ts`) — để không bắt nhầm
// ví dụ minh hoạ trong chú thích. AC-UX-065.
import { COMPONENTS, GUARDS } from '@/test/paths'
import { stripComments } from '@/test/stripComments'

const UI_DIR = resolve(COMPONENTS, 'ui')

const EXPECTED_PRIMITIVES = [
  'Badge',
  'Button',
  'Card',
  'DataTable',
  'EmptyState',
  'ErrorState',
  'ListPageShell',
  'Skeleton',
] as const

/** Palette thô của Tailwind — cấm tuyệt đối trong tầng 0. */
const RAW_PALETTE_RE = /(emerald|amber|rose|red|green|slate|gray|blue|indigo|teal)-[0-9]{2,3}/g
/** 5 họ ngữ nghĩa đã khai (tailwind.config.js) và 3 bậc hợp lệ. */
const SEMANTIC_CLASS_RE =
  /\b(?:text|bg|border|ring|from|via|to|divide|placeholder|accent)-(success|warning|danger|info|neutral)-(\d{2,3})\b/g
const ALLOWED_SHADES = new Set(['50', '500', '700'])
/** Chuỗi hiển thị tiếng Anh hay lọt ra UI (case-sensitive — chữ thường là tên token/prop). */
const FORBIDDEN_EN_RE =
  /\b(Retry|Loading|No data|Error|Cancel|Save|Close|Submit|Search|Add|Edit|Delete|Confirm|Success|Warning|Failed)\b/
/** Chuỗi tiếng Việt được phép nằm CỨNG trong template (SSoT §6.1). */
const TEXT_ALLOWLIST = new Set(['Thử lại'])

const vueFiles = readdirSync(UI_DIR).filter((f) => f.endsWith('.vue')).sort()
// Test của primitive nay nằm ở `components/ui/tests/` (quy ước 2026-08-13).
const UI_TESTS_DIR = resolve(UI_DIR, 'tests')
const testFiles = readdirSync(UI_TESTS_DIR).filter((f) => f.endsWith('.test.ts')).sort()

function read(file: string): string {
  return readFileSync(resolve(UI_DIR, file), 'utf8')
}

function templateOf(src: string): string {
  const start = src.indexOf('<template>')
  const end = src.lastIndexOf('</template>')
  return start === -1 || end === -1 ? '' : src.slice(start + '<template>'.length, end)
}

/** Text node hiển thị: bỏ comment + bỏ `{{ … }}`, lấy phần chữ nằm giữa `>` và `<`. */
function textNodes(template: string): string[] {
  const cleaned = stripComments(template).replace(/\{\{[\s\S]*?\}\}/g, ' ')
  const out: string[] = []
  for (const m of cleaned.matchAll(/>([^<>]+)</g)) {
    const t = m[1].replace(/\s+/g, ' ').trim()
    if (t) out.push(t)
  }
  return out
}

/** Chuỗi copy khai trong <script setup> — nhận diện bằng "có khoảng trắng bên trong". */
function scriptDisplayStrings(src: string): string[] {
  const script = stripComments(src.slice(0, src.indexOf('<template>') === -1 ? undefined : src.indexOf('<template>')))
  const out: string[] = []
  for (const m of script.matchAll(/'([^'\\\n]{2,})'/g)) {
    if (/\s/.test(m[1])) out.push(m[1])
  }
  return out
}

describe('Vệ sinh primitive tầng 0 (TC-UX2-17..19)', () => {
  it('TC-UX2-17 / INV-UI-1: 0 class palette thô trong bất kỳ ui/*.vue', () => {
    const violations: string[] = []
    for (const f of vueFiles) {
      for (const m of stripComments(read(f)).matchAll(RAW_PALETTE_RE)) {
        violations.push(`${f}: ${m[0]}`)
      }
    }
    expect(violations, 'primitive phải dùng token ngữ nghĩa hoặc class @layer sẵn có').toEqual([])
  })

  it('TC-UX2-18 / INV-UI-2: đúng 8 primitive, mỗi file có đúng 1 test cùng tên, barrel khớp', () => {
    // 3 vế phải khớp khít: số export == số file .vue == số file test.
    expect(EXPECTED_PRIMITIVES).toHaveLength(8)
    // [K8] dân số: khoá BẰNG NHAU danh sách file quét được — mạnh hơn ngưỡng tối thiểu.
    expect(vueFiles).toEqual(EXPECTED_PRIMITIVES.map((n) => `${n}.vue`))
    // Test của primitive có HAI nhà hợp lệ (SPEC §5.1): cạnh nguồn, hoặc `src/guards/`
    // nếu nó còn đối chiếu file ở thư mục KHÁC (vd `errorState` đọc
    // `components/common/DetailLoadError.vue`). Yêu cầu là "mỗi primitive có đúng 1
    // test", KHÔNG phải "test nằm trong components/ui".
    const guardTests = readdirSync(GUARDS).filter((f) => f.endsWith('.guard.test.ts'))
    const lower = (s: string) => s.charAt(0).toLowerCase() + s.slice(1)
    for (const name of EXPECTED_PRIMITIVES) {
      const matches = [
        ...testFiles.filter((t) => t === `${name}.test.ts`),
        ...guardTests.filter((t) => t === `${lower(name)}.guard.test.ts`),
      ]
      expect(matches, `primitive ${name} phải có đúng 1 file test (cạnh nguồn hoặc guards/)`).toHaveLength(1)
    }
    // trong components/ui chỉ còn test primitive — guard đã dọn sang src/guards/
    expect(testFiles.length + guardTests.filter((t) =>
      EXPECTED_PRIMITIVES.some((n) => t === `${lower(n)}.guard.test.ts`)).length,
    ).toBe(EXPECTED_PRIMITIVES.length)

    const barrel = read('index.ts')
    const exported = [...barrel.matchAll(/export \{ default as (\w+) \} from '\.\/(\w+)\.vue'/g)]
    expect(exported.map((m) => m[1])).toEqual([...EXPECTED_PRIMITIVES])
    for (const m of exported) expect(m[1], 'tên export phải trùng tên file').toBe(m[2])
  })

  it('TC-UX2-19 / INV-UI-3: 0 chuỗi hiển thị tiếng Anh trong template + copy mặc định', () => {
    const badNodes: string[] = []
    const badStrings: string[] = []
    for (const f of vueFiles) {
      const src = read(f)
      for (const t of textNodes(templateOf(src))) {
        if (!TEXT_ALLOWLIST.has(t)) badNodes.push(`${f}: "${t}"`)
      }
      for (const s of [...textNodes(templateOf(src)), ...scriptDisplayStrings(src)]) {
        if (FORBIDDEN_EN_RE.test(s)) badStrings.push(`${f}: "${s}"`)
      }
    }
    expect(badNodes, 'chữ cứng trong template phải nằm trong allowlist tiếng Việt').toEqual([])
    expect(badStrings, 'copy hiển thị phải là tiếng Việt (LL-FE-53)').toEqual([])
  })

  it('INV-UI-4: chỉ dùng 3 bậc đã khai {50,500,700} của 5 họ ngữ nghĩa (bẫy deep-merge)', () => {
    const violations: string[] = []
    for (const f of vueFiles) {
      for (const m of stripComments(read(f)).matchAll(SEMANTIC_CLASS_RE)) {
        if (!ALLOWED_SHADES.has(m[2])) violations.push(`${f}: ${m[0]}`)
      }
    }
    expect(violations, 'bậc chưa khai sẽ rơi về palette mặc định của Tailwind ⇒ lệch tông').toEqual([])
  })
})
