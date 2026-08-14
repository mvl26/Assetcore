// Copyright (c) 2026, AssetCore Team
// AC-UX-071 (docs/ui-ux/03 §13.7.1) — NGÂN SÁCH ADOPTION `DetailPageShell`: CHỈ-GIẢM, bản đồ per-file.
//
// Vấn đề nó chặn — «con số trong câu văn không đỏ được». Nợ adoption của lớp CHI TIẾT đã sống 4 vòng
// dưới dạng một dòng chữ («còn ~20 màn»), và lớp DANH SÁCH đã trả giá đúng cho lỗi ấy: đóng «12 route
// cuối cùng» theo CỘT BỘ DÒ rồi phát hiện còn 12 màn chưa áp khuôn, phải mở thêm lô 3 (ADR-UX-23).
//
// PHÉP ĐO (docs/ui-ux/03 §13.1) — KHÔNG phải cột «Lỗi+Thử lại» của bộ dò, mà là **dấu vân tay IMPORT**
// `from '@/components/common/DetailPageShell.vue'` trên họ `*DetailView.vue`. Đây đúng là thứ ép 4 trạng
// thái loại trừ nhau bằng CẤU TRÚC (một chuỗi v-if/v-else-if/v-else nằm trong shell), không phải bằng
// quy ước từng màn. `grep -c DetailPageShell` đếm cả chú thích ⇒ vô dụng (bẫy 13.9.12).
//
// CHỈ-GIẢM HAI CHIỀU:
//   · thêm `*DetailView.vue` mới KHÔNG có khuôn  ⇒ ĐỎ (nợ không được mọc thêm)
//   · file trong sổ mà ĐÃ áp khuôn               ⇒ ĐỎ (trả nợ thì phải hạ sổ trong CÙNG lượt)
// ⇒ khi lô 2 land xong, `NON_ADOPTER_BUDGET` RỖNG và non-adopter = 0 vĩnh viễn.
import { describe, it, expect } from 'vitest'
import { readFileSync, readdirSync, statSync, existsSync } from 'node:fs'
import { dirname, resolve, relative, sep, basename } from 'node:path'
import { DOCS, GUARDS, SRC, VIEWS } from '@/test/paths'
import { stripComments } from '@/test/stripComments'

const SPEC_PATH = resolve(DOCS, 'ui-ux/03_DETAIL_PAGE_SHELL.md')
const ROUTER_PATH = resolve(SRC, 'router/index.ts')

/** Dấu vân tay adoption — import SSoT, KHÔNG phải chuỗi `DetailPageShell` trong chú thích. */
const SHELL_IMPORT = /from\s+'@\/components\/common\/DetailPageShell\.vue'/

/**
 * SỔ NỢ ADOPTION — **RỖNG kể từ 2026-08-04**: lô 2 mở với 21 dòng (đo từ đĩa: adopter 11/32) và
 * mỗi dòng đã bị XOÁ trong CÙNG lượt land của màn tương ứng ⇒ adoption đóng hẳn **32/32**.
 *
 * Guard nay ở chế độ **ĐÓNG BĂNG 0**: bất kỳ `*DetailView.vue` nào không dùng
 * `common/DetailPageShell.vue` — cũ hay mới — đều làm ĐỎ.
 *
 * ⚠️ Chỉ được XOÁ dòng. Muốn THÊM một dòng vào đây thì việc cần làm là sửa mã, không phải sửa sổ.
 */
const NON_ADOPTER_BUDGET: readonly string[] = []

/** Tổng số màn chi tiết hôm nay — đổi số này = đổi phạm vi họ `*DetailView`, phải cố ý. */
const TOTAL_DETAIL_VIEWS = 32

function detailViewFiles(dir = VIEWS, out: string[] = []): string[] {
  for (const entry of readdirSync(dir)) {
    if (entry === 'node_modules' || entry.startsWith('.')) continue
    const full = resolve(dir, entry)
    if (statSync(full).isDirectory()) detailViewFiles(full, out)
    else if (/DetailView\.vue$/.test(entry)) out.push(full)
  }
  return out
}

/** Đường dẫn tương đối `src/` với dấu `/` — ổn định trên mọi HĐH. */
const rel = (full: string): string => relative(SRC, full).split(sep).join('/')

const files = detailViewFiles().sort()
const pairs = files.map((full) => ({
  path: rel(full),
  adopter: SHELL_IMPORT.test(readFileSync(full, 'utf8')),
}))
const nonAdopters = pairs.filter((p) => !p.adopter).map((p) => p.path)
const adopters = pairs.filter((p) => p.adopter).map((p) => p.path)

// ── Sổ lô 2 đọc TỪ Core Doc §13.2 (SSoT) ───────────────────────────────────────────────
interface LotRow {
  idx: number
  route: string
  file: string
  status: string
  tc: string
}

const spec = readFileSync(SPEC_PATH, 'utf8')

function parseLotTable(): LotRow[] {
  const section = spec.slice(spec.indexOf('### 13.2'), spec.indexOf('### 13.3'))
  const rows: LotRow[] = []
  for (const line of section.split('\n')) {
    const cells = line.split('|').map((c) => c.trim())
    // | # | Route | View file | Hàm nạp | Nguồn lỗi sau sửa | Nhóm | Trạng thái | TC |
    if (cells.length < 10) continue
    const idx = Number(cells[1])
    if (!Number.isInteger(idx) || idx < 1) continue
    const file = (cells[3].match(/`([^`]+)`/) ?? [])[1] ?? ''
    const route = (cells[2].match(/`([^`]+)`/) ?? [])[1] ?? ''
    const tc = (cells[8].match(/TC-UX4-\d+/) ?? [])[0] ?? ''
    rows.push({ idx, route, file, status: cells[7].replace(/\*/g, '').trim(), tc })
  }
  return rows
}

const lot2 = parseLotTable()
/** `frontend/src/views/x/Y.vue` → `views/x/Y.vue` */
const toSrcRel = (docPath: string): string => docPath.replace(/^frontend\/src\//, '')

describe('AC-UX-071 phần A — quét họ *DetailView và chấm cặp (file, adopter)', () => {
  it('tìm thấy đúng số màn chi tiết đã công bố', () => {
    expect(
      files.length,
      `số file *DetailView.vue đổi (${files.length} ≠ ${TOTAL_DETAIL_VIEWS}) — thêm/bớt màn chi tiết phải ` +
        'cập nhật docs/ui-ux/03 §13.1 và hằng TOTAL_DETAIL_VIEWS trong CÙNG lượt',
      // [K8] dân số: khoá BẰNG NHAU tổng màn chi tiết — mạnh hơn ngưỡng tối thiểu.
    ).toBe(TOTAL_DETAIL_VIEWS)
  })

  it('mọi dòng trong sổ nợ trỏ file CÓ THẬT trên đĩa', () => {
    const dead = NON_ADOPTER_BUDGET.filter((p) => !existsSync(resolve(SRC, p)))
    expect(dead, 'sổ nợ trỏ file đã xoá/đổi tên — dọn sổ trong cùng lượt').toEqual([])
  })

  it('nợ KHÔNG được mọc thêm: mọi *DetailView.vue chưa áp khuôn phải nằm trong sổ', () => {
    const budget = new Set(NON_ADOPTER_BUDGET)
    const newDebt = nonAdopters.filter((p) => !budget.has(p))
    expect(
      newDebt,
      'màn chi tiết không dùng common/DetailPageShell.vue — 4 trạng thái sẽ lại được cài tay, ' +
        '«lỗi giả dạng rỗng» + «panel thao tác trên bản ghi không tồn tại» quay lại. ' +
        'Áp khuôn (docs/ui-ux/03 §13.4), đừng thêm dòng vào sổ.',
    ).toEqual([])
  })

  it('trả nợ thì phải HẠ SỔ: không dòng nào trong sổ đã áp khuôn mà vẫn còn trong sổ', () => {
    const adopted = new Set(adopters)
    const stale = NON_ADOPTER_BUDGET.filter((p) => adopted.has(p))
    expect(
      stale,
      'file đã dùng DetailPageShell nhưng vẫn nằm trong sổ nợ — xoá dòng khỏi NON_ADOPTER_BUDGET ' +
        'trong CÙNG lượt land (nếu không, sổ hết là ngân sách và thành lời nói dối như «27/32» của AC-UX-052)',
    ).toEqual([])
  })

  it('sổ nợ == tập non-adopter đo từ đĩa (không thừa, không thiếu)', () => {
    expect([...NON_ADOPTER_BUDGET].sort()).toEqual([...nonAdopters].sort())
  })
})

describe('AC-UX-071 phần B — sổ lô 2 (§13.2) khớp đĩa, parity 2 chiều', () => {
  it('sổ có đúng 21 dòng, đánh số liên tục 1…21', () => {
    expect(lot2, 'không đọc được bảng §13.2 của docs/ui-ux/03').toHaveLength(21)
    expect(lot2.map((r) => r.idx)).toEqual(Array.from({ length: 21 }, (_, i) => i + 1))
  })

  it('mã TC liên tục TC-UX4-32…52, không trùng', () => {
    const tcs = lot2.map((r) => r.tc)
    expect(new Set(tcs).size, 'mã TC bị trùng trong sổ §13.2').toBe(21)
    expect(tcs).toEqual(Array.from({ length: 21 }, (_, i) => `TC-UX4-${32 + i}`))
  })

  it('mọi view file trong sổ có THẬT trên đĩa và thuộc họ *DetailView', () => {
    const missing = lot2
      .map((r) => toSrcRel(r.file))
      .filter((p) => !existsSync(resolve(SRC, p)) || !/DetailView\.vue$/.test(p))
    expect(missing, 'sổ §13.2 trỏ file không tồn tại / không thuộc họ *DetailView').toEqual([])
  })

  it('mọi route trong sổ là route THẬT trong router/index.ts', () => {
    const router = readFileSync(ROUTER_PATH, 'utf8')
    const missing = lot2
      .map((r) => r.route.split(' ')[0]) // bỏ chú thích «(+ /new)»
      .filter((route) => {
        // `/imm06/programs/:name` → path segment cuối được khai riêng trong `children`.
        const segs = route.split('/').filter(Boolean)
        const last = segs[segs.length - 1]
        return !router.includes(route) && !router.includes(`'${last}'`) && !router.includes(`/${last}`)
      })
    expect(missing, 'route trong sổ §13.2 không tìm thấy trong router').toEqual([])
  })

  it('parity 2 chiều: import DetailPageShell ⟺ ô «Trạng thái» = ĐÃ ĐÓNG', () => {
    const adopted = new Set(adopters)
    const drift: string[] = []
    for (const row of lot2) {
      const p = toSrcRel(row.file)
      const closedInDoc = row.status === 'ĐÃ ĐÓNG'
      const closedOnDisk = adopted.has(p)
      if (closedInDoc !== closedOnDisk) {
        drift.push(`${p}: doc=${row.status || '(rỗng)'} ⇄ đĩa=${closedOnDisk ? 'ĐÃ ĐÓNG' : 'CHƯA'}`)
      }
    }
    expect(
      drift,
      'Sổ §13.2 lệch đĩa. Land mã thì lật ô «Trạng thái» sang ĐÃ ĐÓNG trong CÙNG lượt — ' +
        'doc không được ghi con số không đo được từ đĩa.',
    ).toEqual([])
  })
})

describe('AC-UX-071 phần C — adoption phải kèm test trạng thái', () => {
  it('mỗi view đã áp khuôn có <tên>DetailStates.test.ts đặt cạnh nó', () => {
    const missing: string[] = []
    for (const p of adopters) {
      // Quy ước 2026-08-13 (user chốt): file test nằm trong thư mục con `tests/`
      // của chính thư mục nguồn — KHÔNG đặt ngang hàng file nguồn nữa.
      const dir = resolve(dirname(resolve(SRC, p)), 'tests')
      // Quy ước SPEC §5.1 (chuẩn hoá 2026-08-13): `<Nguồn>.<khiaCanh>.test.ts` — tên
      // nguồn khớp CHÍNH XÁC. `AssetDetailView.vue` → `AssetDetailView.states.test.ts`.
      // (Trước đây là `assetDetailStates.test.ts` — tên không nói ra nó kiểm file nào.)
      const want = `${basename(p, '.vue')}.states.test.ts`.toLowerCase()
      const found = existsSync(dir) && readdirSync(dir).some((e) => e.toLowerCase() === want)
      // Nhà thứ hai hợp lệ: `src/guards/`. Một số test 4-trạng-thái còn đối chiếu
      // file nguồn ở thư mục KHÁC (vd `capaDetailStates` đọc `views/compliance/*`),
      // nên theo SPEC §5.1 chúng ở `guards/<chuDe>.guard.test.ts`. Yêu cầu nghiệp vụ
      // là "có test 4 trạng thái", KHÔNG phải "test nằm đúng thư mục này".
      const wantGuard =
        `${basename(p, '.vue').replace(/DetailView$/, '')}DetailStates.guard.test.ts`.toLowerCase()
      const foundGuard = readdirSync(GUARDS).some((e) => e.toLowerCase() === wantGuard)
      if (!found && !foundGuard) missing.push(`${p} → thiếu ${want} (hoặc guards/${wantGuard})`)
    }
    expect(
      missing,
      'áp khuôn mà không có test 4 trạng thái = chưa chứng minh được tính LOẠI TRỪ (docs/ui-ux/03 §13.6)',
    ).toEqual([])
  })

  it('21 file test của lô 2 được khai đủ ở §13.6', () => {
    const declared = spec.slice(spec.indexOf('### 13.6'), spec.indexOf('### 13.7'))
    const missing = lot2
      .map((r) => toSrcRel(r.file).replace(/^views\//, '').split('/'))
      .map(([dir, f]) => `${dir}/tests/${basename(f, '.vue')}.states.test.ts`)
      .filter((p) => !declared.toLowerCase().includes(p.toLowerCase()))
    expect(missing, '§13.6 thiếu khai file test cho màn của lô 2').toEqual([])
  })
})

describe('AC-UX-071 phần D — hình dạng file đã áp khuôn (INV-UX4L2-5)', () => {
  for (const p of [...adopters].sort()) {
    it(`${p} — shell là thẻ gốc, 0 page-container, 0 text-red-500, 0 nhánh tải tự chế`, () => {
      const raw = readFileSync(resolve(SRC, p), 'utf8')
      const src = stripComments(raw)
      const tpl = src.slice(src.indexOf('<template>'))

      // Thẻ gốc: phần tử đầu tiên sau `<template>` phải là `<DetailPageShell`.
      const firstTag = (tpl.match(/<template>\s*<([A-Za-z][\w.-]*)/) ?? [])[1]
      expect(firstTag, `${p}: thẻ gốc của <template> phải là <DetailPageShell> (INV-UX4-11)`).toBe(
        'DetailPageShell',
      )

      expect(
        (src.match(/page-container/g) ?? []).length,
        `${p}: shell đã mang lớp bao — lồng page-container thứ hai làm padding/max-width nhân đôi (13.9.5)`,
      ).toBe(0)

      expect(
        (src.match(/text-red-500/g) ?? []).length,
        `${p}: dùng token danh nghĩa text-danger-500 thay cho hex-nghĩa text-red-500 (13.9.6)`,
      ).toBe(0)

      const homemade = tpl.match(/v-(?:if|else-if)="[^"]*\bloading\b[^"]*"/g) ?? []
      expect(
        homemade,
        `${p}: nhánh trạng thái TẢI tự chế — shell đã quyết định 4 trạng thái bằng cấu trúc`,
      ).toEqual([])
    })
  }
})
