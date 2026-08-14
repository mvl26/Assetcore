// Copyright (c) 2026, AssetCore Team
// AC-UX-069 (docs/ui-ux/07 §6) — ngân sách THANH TAB TỰ CHẾ: CHỈ-GIẢM, theo BẢN ĐỒ per-file.
//
// Vấn đề nó chặn: mỗi màn tự vẽ thanh tab của mình ⇒ 9 bản fork, 8 trong số đó KHÔNG có
// `role="tablist"`/`role="tab"`/`aria-selected` (trình đọc màn hình không biết đó là tab)
// và không cuộn ngang được trên mobile (tab cuối bị cắt — hợp đồng TC-RWD-07). SSoT là
// `components/common/DetailTabBar.vue`: sửa a11y một nơi, mọi màn hưởng.
//
// Vì sao cần GUARD chứ không phải một dòng trong tài liệu: nợ này đã sống 3 vòng dưới dạng
// MỘT CÂU VĂN SAI («27/32 màn») — câu văn không đỏ được. Con số ấy đếm *màn không import
// DetailTabBar*, trong khi 24 màn trong đó không có tab nào cả. Và bản thân việc mọc thêm
// một thanh tab tự chế rất rẻ để tái phạm: 8 dòng `<button>` là xong.
//
// PHÉP ĐO (docs/ui-ux/07 §1.2) — dấu vân tay TÍCH CỰC, không phải triệu chứng vắng mặt:
//   «một `<button>` có ràng buộc `:class` đọc biến trạng thái tab».
// Đây là thứ mọi thanh tab tự chế BẮT BUỘC có (nút phải tự tô đậm khi đang mở), trong khi
// 3 tín hiệu khác đều dò sai: `role="tablist"` bắt 1/9 · `grep -L import` đếm cả màn không
// có tab · `@click="tab = …"` bỏ sót 3 màn điều hướng bằng hàm/route.
//
// Quét CẢ HAI cây `src/views` + `src/components`: 3 bản fork đã trốn được vào `components/`
// nơi mọi bộ dò trước chỉ nhìn `src/views` (ADR-UX-21).
import { describe, it, expect } from 'vitest'
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { resolve, relative, sep } from 'node:path'
import { SRC, listFiles } from '@/test/paths'
import { stripComments } from '@/test/stripComments'

// src/views → src

const SCAN_DIRS = ['views', 'components'] as const

/** Nút tab tự chế: `<button …>` có `:class` so sánh biến trạng thái tab. */
const SELF_DRAWN_TAB_RE = /<button\b[^>]*?:class\s*=\s*"[^"]*\b(?:activeTab|tab)\s*===/g

/** File DUY NHẤT được phép chứa markup thanh tab trong toàn repo. */
const SSOT_PATH = 'components/common/DetailTabBar.vue'

function listVueFiles(dir: string, out: string[] = []): string[] {
  for (const entry of readdirSync(dir)) {
    if (entry === 'node_modules' || entry.startsWith('.')) continue
    const full = resolve(dir, entry)
    if (statSync(full).isDirectory()) listVueFiles(full, out)
    else if (entry.endsWith('.vue')) out.push(full)
  }
  return out
}

/** Đường dẫn tương đối `src/` với dấu `/` — ổn định trên mọi HĐH. */
function rel(full: string): string {
  return relative(SRC, full).split(sep).join('/')
}

function readStripped(relPath: string): string {
  return stripComments(readFileSync(resolve(SRC, relPath), 'utf8'))
}

function countSelfDrawn(full: string): number {
  const src = stripComments(readFileSync(full, 'utf8'))
  return (src.match(SELF_DRAWN_TAB_RE) ?? []).length
}

/**
 * BẢN ĐỒ NỢ — đóng băng theo phép đo từ đĩa 2026-08-04, SAU lô 1 (docs/ui-ux/07 §1.3).
 *
 * Baseline đầu vòng: 12 nút-tab tự chế / 9 file. Lô 1 đóng 5 nút ở 3 file
 * (`AssetDetailView` 1 · `CommissioningDetailView` 3 · `NeedsRequestDetailView` 1)
 * ⇒ còn 7 nút / 6 file.
 *
 * Đơn vị đếm = NÚT-TAB KHAI TRONG NGUỒN, không phải «bar»: một `v-for` = 1, ba nút viết
 * tay = 3 (nên `AssetDashboard` là 2 và `CommissioningDetailView` từng là 3).
 *
 * ⚠️ Chỉ được SỬA XUỐNG. Muốn thêm một dòng vào đây thì việc cần làm là sửa mã, không
 * phải sửa bản đồ.
 */
const TAB_BUDGET: Readonly<Record<string, number>> = {
  'views/tech-specs/TechSpecDetailView.vue': 1,
  'views/procurement/VendorEvalDetailView.vue': 1,
  'views/inventory/UomConversionView.vue': 1,
  'views/master-data/ReferenceDataView.vue': 1,
  'components/commissioning/CommissioningForm.vue': 1,
  'components/commissioning/AssetDashboard.vue': 2,
}

/** 3 file lô 1 — đã trả hết nợ, phải giữ ĐÚNG 0 (chống lùi). */
const LOT1_CLEARED: readonly string[] = [
  'views/asset/AssetDetailView.vue',
  'views/commissioning/CommissioningDetailView.vue',
  'views/needs/NeedsRequestDetailView.vue',
]

/**
 * Màn BẮT BUỘC tiêu thụ SSoT — **GIÁN TIẾP qua `DetailPageShell`** kể từ lô 2 (`ADR-UX-25`,
 * `03 §13.8` mục 1). Phần A (đếm dấu vân tay) MÙ với bản fork điều hướng bằng `router.push` tô
 * đậm theo cách khác, nên vẫn chốt bằng danh sách tường minh — chỉ đổi HÌNH DẠNG được chấp nhận:
 *
 *   trước lô 2:  view `import DetailTabBar` + đúng 1 thẻ `<DetailTabBar>`
 *   từ lô 2:     view **0** import trực tiếp, **0** thẻ cục bộ, truyền `:tabs` + `active-tab`
 *                cho shell — shell là nơi DUY NHẤT vẽ thanh tab, và nó nằm trong nhánh `content`
 *                nên bản ghi bị chặn đọc KHÔNG còn dải tab bấm-không-tới-đâu.
 *
 * 7 màn của lô 2 gộp với `InternalAuditDetailView` (đã đi lối này từ vòng 4, `ADR-UX-07`) ⇒ **8**.
 * Assert độ dài 8 để việc rút ngắn danh sách là TAMPER-EVIDENT.
 *
 * ⚠️ KHÔNG xoá assert nào — chỉ DI TRÚ hình dạng. Đây là điểm khác nhau giữa «đổi khuôn» và
 * «nới guard cho đỡ đỏ».
 */
const MUST_USE_SSOT_VIA_SHELL = [
  'views/asset/AssetDetailView.vue',
  'views/commissioning/CommissioningDetailView.vue',
  'views/needs/NeedsRequestDetailView.vue',
  'views/calibration/CalibrationDetailView.vue',
  'views/cm/CMWorkOrderDetailView.vue',
  'views/incident/IncidentDetailView.vue',
  'views/pm/PMWorkOrderDetailView.vue',
  'views/compliance/InternalAuditDetailView.vue',
] as const

/** Dấu vân tay riêng của bản fork đã gỡ — chống «gỡ nửa vời, để lại gạch chân tự vẽ». */
const FORK_FINGERPRINT: Readonly<Record<string, readonly string[]>> = {
  'views/commissioning/CommissioningDetailView.vue': ['absolute inset-x-0 bottom-0 h-0.5'],
}

const BUDGET_TOTAL = Object.values(TAB_BUDGET).reduce((a, b) => a + b, 0)

const REPRO =
  '\n  Tái lập:  cd frontend && node -e "' +
  'const re=/<button\\\\b[^>]*?:class\\\\s*=\\\\s*\\\\"[^\\\\"]*\\\\b(?:activeTab|tab)\\\\s*===/g" ' +
  '(quét src/views + src/components, strip comment trước khi đếm)\n' +
  '  Cách sửa (docs/ui-ux/07 §4): khai `DetailTab[]` rồi ' +
  '`<DetailTabBar :tabs="TABS" :model-value="activeTab" @update:model-value="…" />`.\n'

const actual = new Map<string, number>()
for (const dir of SCAN_DIRS) {
  for (const full of listVueFiles(resolve(SRC, dir))) {
    const n = countSelfDrawn(full)
    if (n > 0) actual.set(rel(full), n)
  }
}
const actualTotal = [...actual.values()].reduce((a, b) => a + b, 0)

describe('AC-UX-069 phần A — ngân sách nút-tab tự chế (CHỈ-GIẢM, bản đồ per-file)', () => {
  it('bản đồ khớp con số công bố: 7 nút-tab / 6 file (sau lô 1)', () => {
    expect(BUDGET_TOTAL).toBe(7)
    expect(Object.keys(TAB_BUDGET)).toHaveLength(6)
  })

  // (b) file LẠ — chống né guard bằng cách đẻ file `.vue` mới / trốn vào `components/`.
  it('KHÔNG có file lạ: mọi file còn nút-tab tự chế đều nằm trong bản đồ', () => {
    const strangers = [...actual.keys()].filter((p) => !(p in TAB_BUDGET)).sort()
    expect(
      strangers,
      'File KHÔNG có trong bản đồ mà vẫn tự vẽ thanh tab. Ngân sách CHỈ-GIẢM: ' +
        'màn mới phải dùng `DetailTabBar` ngay từ đầu, không được thêm dòng vào bản đồ.' + REPRO,
    ).toEqual([])
  })

  // (c) từng file không vượt hạn mức riêng — chặn «trả chỗ dễ, vay chỗ khó».
  it('KHÔNG file nào vượt hạn mức riêng của nó', () => {
    const over = [...actual.entries()]
      .filter(([p, n]) => p in TAB_BUDGET && n > TAB_BUDGET[p])
      .map(([p, n]) => `${p}: ${n} > ${TAB_BUDGET[p]}`)
      .sort()
    expect(over, 'Số nút-tab tự chế TĂNG so với bản đồ.' + REPRO).toEqual([])
  })

  // (a) tổng không tăng.
  it('tổng nút-tab tự chế ≤ tổng bản đồ', () => {
    expect(actualTotal, `Tổng ${actualTotal} > ngân sách ${BUDGET_TOTAL}.` + REPRO).toBeLessThanOrEqual(
      BUDGET_TOTAL,
    )
  })

  // (d) giảm rồi thì PHẢI hạ bản đồ — nếu không, nợ đã trả bị "vay lại" âm thầm.
  it('bản đồ không có mục MA: mọi mục đều còn nút-tab tự chế thật trên đĩa', () => {
    const ghosts = Object.keys(TAB_BUDGET).filter((p) => !actual.has(p)).sort()
    expect(
      ghosts,
      'Các file này đã hết thanh tab tự chế — HẠ bản đồ xuống (xoá dòng tương ứng) ' +
        'để phần nợ đã trả không bị vay lại ở vòng sau.',
    ).toEqual([])
  })

  it('3 file lô 1 (AC-UX-068) giữ ĐÚNG 0 — chống lùi', () => {
    for (const p of LOT1_CLEARED) {
      expect(actual.get(p) ?? 0, `${p} đã di trú sang DetailTabBar ở lô 1, không được quay lại.`).toBe(0)
      expect(p in TAB_BUDGET, `${p} không được nằm trong bản đồ nợ nữa.`).toBe(false)
    }
  })
})

describe('AC-UX-069 phần B — SSoT là nơi DUY NHẤT vẽ thanh tab', () => {
  it('danh sách «tiêu thụ SSoT qua shell» có ĐÚNG 8 mục (rút ngắn = tamper-evident)', () => {
    expect(MUST_USE_SSOT_VIA_SHELL).toHaveLength(8)
  })

  // (e) — màn có tab phải tiêu thụ SSoT GIÁN TIẾP qua shell: 0 import trực tiếp, 0 thẻ cục bộ.
  for (const p of MUST_USE_SSOT_VIA_SHELL) {
    it(`${p} — 0 import DetailTabBar, 0 thẻ cục bộ, truyền tabs qua DetailPageShell`, () => {
      const src = readStripped(p)
      expect(/import\s+DetailTabBar\b/.test(src), `${p} còn import TRỰC TIẾP DetailTabBar — thanh tab phải đi qua prop của shell (ADR-UX-25).`).toBe(false)
      expect(src.split('<DetailTabBar').length - 1, `${p} còn thẻ <DetailTabBar> cục bộ ⇒ nguy cơ HAI thanh tab / hai role="tablist".`).toBe(0)
      expect(src, `${p} chưa áp DetailPageShell.`).toContain('DetailPageShell')
      expect(src, `${p} thiếu ràng buộc active-tab cho shell.`).toContain('active-tab')
    })
  }

  // (f) — dấu vân tay fork phải biến mất hẳn, không để lại nửa vời.
  for (const [p, prints] of Object.entries(FORK_FINGERPRINT)) {
    for (const print of prints) {
      it(`${p} — không còn dấu vân tay fork «${print}»`, () => {
        expect(readStripped(p)).not.toContain(print)
      })
    }
  }

  // (g) — markup `role="tablist"` tồn tại ĐÚNG 1 nơi trong repo.
  it('role="tablist" chỉ xuất hiện ở components/common/DetailTabBar.vue', () => {
    const offenders: string[] = []
    for (const dir of SCAN_DIRS) {
      for (const full of listVueFiles(resolve(SRC, dir))) {
        const p = rel(full)
        if (p === SSOT_PATH) continue
        if (stripComments(readFileSync(full, 'utf8')).includes('role="tablist"')) offenders.push(p)
      }
    }
    expect(
      offenders.sort(),
      'Chỉ SSoT được vẽ thanh tab. File dưới đây tự khai role="tablist".' + REPRO,
    ).toEqual([])
    // Và SSoT thì PHẢI còn — chống «xanh rỗng» do đổi tên/xoá file.
    expect(readStripped(SSOT_PATH)).toContain('role="tablist"')
  })

  // (h) — sau lô 2, `InternalAuditDetailView` không còn là NGOẠI LỆ mà là mục thứ 8 của
  // `MUST_USE_SSOT_VIA_SHELL` ở trên; giữ lại phép đo TỔNG để hình dạng ấy là mặc định của
  // MỌI màn chi tiết có tab, không phải đặc ân của một màn.
  it('KHÔNG màn *DetailView nào còn import trực tiếp DetailTabBar', () => {
    const offenders: string[] = []
    for (const full of listVueFiles(resolve(SRC, 'views'))) {
      if (!/DetailView\.vue$/.test(full)) continue
      if (/import\s+DetailTabBar\b/.test(stripComments(readFileSync(full, 'utf8')))) offenders.push(rel(full))
    }
    expect(
      offenders.sort(),
      'Thanh tab của màn chi tiết đi qua prop `:tabs` của DetailPageShell (ADR-UX-25) — ' +
        'import trực tiếp mở lại đường vẽ thứ hai.',
    ).toEqual([])
  })
})

// ─── Chốt dân số thư mục quét (SPEC §5.2 N6 — chống guard xanh giả) ───────────
// Guard ở trên khẳng định dạng "không tìm thấy vi phạm nào". Khẳng định đó đúng
// một cách RỖNG TUẾCH nếu bộ quét không đọc được file nào — điều xảy ra âm thầm
// khi thư mục bị dời/đổi tên. Chốt dưới đây biến tình huống đó thành ĐỎ.
// Số đo từ đĩa 2026-08-13: 209 file. Ngưỡng đặt thấp hơn có chủ ý để thêm/bớt
// vài file không gây đỏ giả; sửa ngưỡng phải là hành vi CÓ Ý THỨC.
describe('chốt dân số thư mục quét', () => {
  it('src/**/*.vue còn ít nhất 190 file — nếu không, guard đã ngừng canh', () => {
    expect(listFiles(SRC, { ext: '.vue', min: 190 }).length).toBeGreaterThanOrEqual(190)
  })
})
