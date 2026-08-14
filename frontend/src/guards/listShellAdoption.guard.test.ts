// Copyright (c) 2026, AssetCore Team
// AC-UX-070 (docs/ui-ux/02 §14.8) — NGÂN SÁCH ADOPTION `ListPageShell`: CHỈ-GIẢM, theo BẢN ĐỒ per-file.
//
// Vấn đề nó chặn — «phép đo cũ không nhìn thấy nợ này»:
// Bộ dò `ui-audit-inventory.mjs` chấm cột «Lỗi+Thử lại» theo **sự có mặt** của một lối nạp lại
// (`@retry` / control mang chữ «Thử lại») ở đâu đó trong file. Nó KHÔNG thấy được hai khối cùng
// render. Hệ quả thật: `/audit-trail` in banner «Không tải được nhật ký kiểm toán» **và** ngay dưới
// đó là minh hoạ «Không có bản ghi kiểm toán nào phù hợp» — người dùng đọc câu thứ hai và tin là
// KHÔNG CÓ BẢN GHI. Cùng lỗi ở `/needs-requests`. Cả hai vẫn được bộ dò chấm ✅, nên lô 2 tuyên bố
// nhầm «12 route DANH SÁCH CUỐI CÙNG» trong khi còn 12 màn danh sách chưa áp khuôn (ADR-UX-23).
//
// PHÉP ĐO (docs/ui-ux/02 §14.8) — cặp `(file *ListView.vue, adopter true/false)`, dấu vân tay là
// import SSoT `@/components/ui/ListPageShell.vue`. Đây là thứ ép 4 trạng thái loại trừ nhau bằng
// CẤU TRÚC (một chuỗi v-if/v-else-if/v-else nằm trong 1 file), không phải bằng quy ước từng màn.
//
// CHỈ-GIẢM HAI CHIỀU:
//   · thêm `*ListView.vue` mới KHÔNG có khuôn  ⇒ ĐỎ (nợ không được mọc thêm)
//   · file trong sổ mà ĐÃ áp khuôn             ⇒ ĐỎ (trả nợ thì phải hạ sổ trong CÙNG lượt)
// ⇒ khi lô 3 land xong, `NON_ADOPTER_BUDGET` phải RỖNG và non-adopter = 0 vĩnh viễn.
import { describe, it, expect } from 'vitest'
import { readFileSync, readdirSync, statSync, existsSync } from 'node:fs'
import { dirname, resolve, relative, sep, basename } from 'node:path'
import { DOCS, SRC, VIEWS } from '@/test/paths'

const SPEC_PATH = resolve(DOCS, 'ui-ux/02_LIST_PAGE_SHELL.md')

/** Dấu vân tay adoption — import SSoT, không phải chuỗi `ListPageShell` xuất hiện trong chú thích. */
const SHELL_IMPORT = /from\s+'@\/components\/ui\/ListPageShell\.vue'/

/**
 * SỔ NỢ ADOPTION — **RỖNG kể từ 2026-08-04** (lô 3 đã land, đo lại từ đĩa: non-adopter = 0,
 * adopter = 40/40; docs/ui-ux/02 §14.1).
 *
 * 12 dòng cuối cùng (`audit/AuditTrail` · `cm/CMWorkOrder` · `commissioning/Commissioning` ·
 * `eol/Decommission` · `inventory/CycleCount` · `needs/NeedsRequest` · `pm/PMWorkOrder` ·
 * `pm/PmSchedule` · `purchase/ServiceContract` · `training/{Competency,Program,Session}`) đã
 * được áp khuôn trong lô 3 và bị XOÁ khỏi sổ trong CÙNG lượt land.
 *
 * ⇒ Guard nay ở chế độ **ĐÓNG BĂNG 0**: bất kỳ `*ListView.vue` nào không dùng
 * `ui/ListPageShell.vue` — cũ hay mới — đều làm ĐỎ. Nợ này không được phép mọc lại.
 *
 * ⚠️ Chỉ được XOÁ dòng. Muốn THÊM một dòng vào đây thì việc cần làm là sửa mã, không phải sửa sổ.
 */
const NON_ADOPTER_BUDGET: readonly string[] = []

/** Tổng số màn danh sách hôm nay — đổi số này = đổi phạm vi họ `*ListView`, phải cố ý. */
const TOTAL_LIST_VIEWS = 40

function listViewFiles(dir = VIEWS, out: string[] = []): string[] {
  for (const entry of readdirSync(dir)) {
    if (entry === 'node_modules' || entry.startsWith('.')) continue
    const full = resolve(dir, entry)
    if (statSync(full).isDirectory()) listViewFiles(full, out)
    else if (/ListView\.vue$/.test(entry)) out.push(full)
  }
  return out
}

/** Đường dẫn tương đối `src/` với dấu `/` — ổn định trên mọi HĐH. */
const rel = (full: string): string => relative(SRC, full).split(sep).join('/')

const files = listViewFiles().sort()
const pairs = files.map((full) => ({
  path: rel(full),
  adopter: SHELL_IMPORT.test(readFileSync(full, 'utf8')),
}))
const nonAdopters = pairs.filter((p) => !p.adopter).map((p) => p.path)
const adopters = pairs.filter((p) => p.adopter).map((p) => p.path)

describe('INV-UX3A-1 — quét được họ *ListView và chấm cặp (file, adopter)', () => {
  it('tìm thấy đúng số màn danh sách đã công bố', () => {
    expect(
      files.length,
      `số file *ListView.vue đổi (${files.length} ≠ ${TOTAL_LIST_VIEWS}) — thêm/bớt màn danh sách phải cập ` +
        'nhật docs/ui-ux/02 §14.1 và hằng TOTAL_LIST_VIEWS trong CÙNG lượt',
      // [K8] dân số: khoá BẰNG NHAU tổng màn danh sách — mạnh hơn ngưỡng tối thiểu.
    ).toBe(TOTAL_LIST_VIEWS)
  })

  it('mọi dòng trong sổ nợ trỏ file CÓ THẬT trên đĩa', () => {
    const dead = NON_ADOPTER_BUDGET.filter((p) => !existsSync(resolve(SRC, p)))
    expect(dead, 'sổ nợ trỏ file đã xoá/đổi tên — dọn sổ trong cùng lượt').toEqual([])
  })
})

describe('INV-UX3A-2 — nợ KHÔNG được mọc thêm', () => {
  it('mọi *ListView.vue chưa áp khuôn phải nằm trong sổ đóng băng', () => {
    const budget = new Set(NON_ADOPTER_BUDGET)
    const newDebt = nonAdopters.filter((p) => !budget.has(p))
    expect(
      newDebt,
      'màn danh sách MỚI không dùng ui/ListPageShell.vue — 4 trạng thái sẽ lại được cài tay và ' +
        '«lỗi giả dạng rỗng» quay lại. Áp khuôn (docs/ui-ux/02 §3, §14.4), đừng thêm dòng vào sổ.',
    ).toEqual([])
  })
})

describe('INV-UX3A-3 — trả nợ thì phải HẠ SỔ (chiều ngược lại)', () => {
  it('không dòng nào trong sổ đã áp khuôn mà vẫn còn trong sổ', () => {
    const adopted = new Set(adopters)
    const stale = NON_ADOPTER_BUDGET.filter((p) => adopted.has(p))
    expect(
      stale,
      'file đã dùng ListPageShell nhưng vẫn nằm trong sổ nợ — xoá dòng khỏi NON_ADOPTER_BUDGET trong ' +
        'CÙNG lượt land (nếu không, sổ hết là ngân sách và thành lời nói dối như con số «27/32» của AC-UX-052)',
    ).toEqual([])
  })

  it('sổ nợ == tập non-adopter đo từ đĩa (không thừa, không thiếu)', () => {
    expect([...NON_ADOPTER_BUDGET].sort()).toEqual([...nonAdopters].sort())
  })
})

describe('INV-UX3A-4 — adoption phải kèm test trạng thái', () => {
  it('mỗi view đã áp khuôn có <Nguồn>.states.test.ts đặt cạnh nó', () => {
    const missing: string[] = []
    for (const p of adopters) {
      // Quy ước 2026-08-13 (user chốt): file test nằm trong thư mục con `tests/`
      // của chính thư mục nguồn — KHÔNG đặt ngang hàng file nguồn nữa.
      const dir = resolve(dirname(resolve(SRC, p)), 'tests')
      // Quy ước SPEC §5.1 (chuẩn hoá 2026-08-13): `<Nguồn>.<khiaCanh>.test.ts`.
      // `AssetListView.vue` → `AssetListView.states.test.ts`.
      const want = `${basename(p, '.vue')}.states.test.ts`.toLowerCase()
      const found = existsSync(dir) && readdirSync(dir).some((e) => e.toLowerCase() === want)
      if (!found) missing.push(`${p} → thiếu ${want}`)
    }
    expect(
      missing,
      'áp khuôn mà không có test 4 trạng thái = chưa chứng minh được tính LOẠI TRỪ (docs/ui-ux/02 §14.6)',
    ).toEqual([])
  })
})

describe('INV-UX3A-5 — bộ đếm công bố trong Core Doc khớp số đo từ đĩa', () => {
  const spec = readFileSync(SPEC_PATH, 'utf8')

  it('02 §14.1 công bố tổng số màn danh sách == số đếm được', () => {
    // Dòng bảng «Số chốt»: | `*ListView.vue` ĐÃ áp khuôn | `grep -l …` | **28** / 40 | **40** / 40 |
    const m = spec.match(/\*\*(\d+)\*\* \/ 40 \| \*\*(\d+)\*\* \/ 40/)
    expect(m, 'không đọc được dòng adoption ở docs/ui-ux/02 §14.1').not.toBeNull()
    expect(Number(m![2]), 'mục tiêu sau lô 3 phải là 40/40').toBe(TOTAL_LIST_VIEWS)
  })

  it('số adopter hiện tại nằm giữa mốc mở lô và mốc đóng lô', () => {
    const m = spec.match(/\*\*(\d+)\*\* \/ 40 \| \*\*(\d+)\*\* \/ 40/)
    const opened = Number(m![1])
    expect(
      adopters.length,
      `adopter đo từ đĩa = ${adopters.length}; Core Doc ghi mốc mở lô ${opened} → đóng lô ${TOTAL_LIST_VIEWS}. ` +
        'Ra ngoài khoảng này nghĩa là có màn bị GỠ khuôn (lùi) hoặc doc đã stale.',
    ).toBeGreaterThanOrEqual(opened)
    expect(adopters.length).toBeLessThanOrEqual(TOTAL_LIST_VIEWS)
  })
})
