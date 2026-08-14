// Copyright (c) 2026, AssetCore Team
// AC-UX-072 (docs/ui-ux/03 §13.7.2, ADR-UX-27) — SSoT phân loại LỖI NẠP của màn chi tiết.
//
// Vấn đề nó chặn: `loadErrorKind()` là hợp đồng CR-74 (3 kind: mạng / 403-in-envelope / 404).
// Khi mỗi màn tự gọi nó rồi tự lắp `ref`/`computed` quanh nó, ta có N bản sao của cùng một logic
// phân loại — và bản sao thứ N+1 luôn quên đúng một thứ: hoặc quên `message` thật của server
// (403 hiện «Lỗi không xác định»), hoặc quên `blocked` (CTA vẫn render trên bản ghi không đọc
// được ⇒ NÚT CHẾT), hoặc lẫn dispatcher-403 với 403-in-envelope rồi ĐĂNG XUẤT người dùng đang
// đăng nhập hợp lệ. `composables/useDetailAccess.ts` gói cả ba thứ đó vào một nơi.
//
// PHÉP ĐO: cặp (file `*DetailView.vue` đã import `DetailPageShell`, có import `useDetailAccess`).
// Nợ cũ đóng băng theo SỔ `LEGACY_LOCAL_KIND_BUDGET` — **CHỈ ĐƯỢC XOÁ DÒNG**.
import { describe, it, expect } from 'vitest'
import { readFileSync, readdirSync, statSync, existsSync } from 'node:fs'
import { resolve, relative, sep } from 'node:path'
import { SRC, VIEWS, listFiles } from '@/test/paths'
import { stripComments } from '@/test/stripComments'

// src/views → src

const SHELL_IMPORT = /from\s+'@\/components\/common\/DetailPageShell\.vue'/
const ACCESS_IMPORT = /from\s+'@\/composables\/useDetailAccess'/
/** Gọi TRỰC TIẾP hàm phân loại — thứ mà `useDetailAccess` sinh ra để không ai phải gọi nữa. */
const DIRECT_KIND_CALL = /\bloadErrorKind\s*\(/

/**
 * 11 màn đã áp shell từ vòng 4 / lô 1 nhưng còn `loadErrorKind` CỤC BỘ — **ĐÓNG BĂNG**.
 *
 * Vì sao không di trú luôn trong lô 2 (ADR-UX-27): lô 2 đã đổi 21/32 màn: thêm 11 màn nữa là
 * đổi cả họ trong một vòng, và quan trọng hơn — `AC-UX-072` sẽ mất chính cái mốc CHỈ-GIẢM mà
 * nó sinh ra để đo. Đóng dần bằng cách XOÁ DÒNG ở vòng riêng.
 *
 * ⚠️ CHỈ ĐƯỢC XOÁ DÒNG. Thêm một dòng vào đây = hợp thức hoá một bản sao logic mới.
 */
const LEGACY_LOCAL_KIND_BUDGET: readonly string[] = [
  'views/asset/AssetTransferDetailView.vue',
  'views/compliance/FindingDetailView.vue',
  'views/compliance/InternalAuditDetailView.vue',
  'views/compliance/ManagementReviewDetailView.vue',
  'views/document/FirmwareCrDetailView.vue',
  'views/incident/CAPADetailView.vue',
  'views/inventory/SparePartDetailView.vue',
  'views/inventory/StockMovementDetailView.vue',
  'views/inventory/WarehouseDetailView.vue',
  'views/procurement/DecisionDetailView.vue',
  'views/purchase/SupplierDetailView.vue',
]

/** Đích công bố ở §13.10 (b) — ĐÍNH CHÍNH 1 của BA: 21, KHÔNG phải 24. */
const ACCESS_ADOPTION_TARGET = 21

function detailViewFiles(dir = VIEWS, out: string[] = []): string[] {
  for (const entry of readdirSync(dir)) {
    if (entry === 'node_modules' || entry.startsWith('.')) continue
    const full = resolve(dir, entry)
    if (statSync(full).isDirectory()) detailViewFiles(full, out)
    else if (/DetailView\.vue$/.test(entry)) out.push(full)
  }
  return out
}

const rel = (full: string): string => relative(SRC, full).split(sep).join('/')

const rows = detailViewFiles()
  .sort()
  .map((full) => {
    const raw = readFileSync(full, 'utf8')
    const src = stripComments(raw)
    return {
      path: rel(full),
      shell: SHELL_IMPORT.test(raw),
      access: ACCESS_IMPORT.test(raw),
      directKind: DIRECT_KIND_CALL.test(src),
    }
  })

const legacy = new Set(LEGACY_LOCAL_KIND_BUDGET)

describe('AC-UX-072 phần A — adopter shell PHẢI lấy lỗi từ SSoT', () => {
  it('mọi màn đã áp DetailPageShell import useDetailAccess (trừ sổ legacy)', () => {
    const offenders = rows
      .filter((r) => r.shell && !r.access && !legacy.has(r.path))
      .map((r) => r.path)
    expect(
      offenders,
      'Màn đã áp khuôn nhưng tự dựng trạng thái lỗi: `:error-kind`/`:error-message` phải đến từ ' +
        '`composables/useDetailAccess.ts` (docs/ui-ux/03 §13.4.0). Bản sao thứ N+1 luôn quên một ' +
        'trong ba thứ: message thật của server, cờ `blocked` (⇒ nút chết), hoặc phân biệt 2 loại 403.',
    ).toEqual([])
  })

  it('màn NGOÀI sổ legacy có 0 lần gọi trực tiếp loadErrorKind(', () => {
    const offenders = rows.filter((r) => r.directKind && !legacy.has(r.path)).map((r) => r.path)
    expect(
      offenders,
      'Gọi thẳng `loadErrorKind(` = mọc lại nợ SSoT. Dùng `useDetailAccess(() => <ref lỗi nạp>)`.',
    ).toEqual([])
  })
})

describe('AC-UX-072 phần B — sổ legacy CHỈ-GIẢM', () => {
  it('mọi dòng trong sổ trỏ file CÓ THẬT trên đĩa', () => {
    const dead = LEGACY_LOCAL_KIND_BUDGET.filter((p) => !existsSync(resolve(SRC, p)))
    expect(dead, 'sổ legacy trỏ file đã xoá/đổi tên — dọn sổ trong cùng lượt').toEqual([])
  })

  it('trả nợ thì phải HẠ SỔ: dòng legacy đã dùng useDetailAccess ⇒ phải xoá khỏi sổ', () => {
    const migrated = rows.filter((r) => legacy.has(r.path) && r.access).map((r) => r.path)
    expect(
      migrated,
      'File đã di trú sang useDetailAccess nhưng vẫn nằm trong LEGACY_LOCAL_KIND_BUDGET — ' +
        'xoá dòng trong CÙNG lượt, nếu không sổ hết là mốc đo và thành lời nói dối.',
    ).toEqual([])
  })

  it('sổ == tập màn-shell-còn-kind-cục-bộ đo từ đĩa (không thừa, không thiếu)', () => {
    const measured = rows.filter((r) => r.shell && !r.access).map((r) => r.path).sort()
    expect([...LEGACY_LOCAL_KIND_BUDGET].sort()).toEqual(measured)
  })

  it('sổ đóng băng ở đúng 11 dòng — rút ngắn danh sách là tamper-evident', () => {
    expect(LEGACY_LOCAL_KIND_BUDGET.length).toBeLessThanOrEqual(11)
  })
})

describe('AC-UX-072 phần C — bộ đếm công bố khớp đĩa', () => {
  it(`số màn dùng useDetailAccess == ${ACCESS_ADOPTION_TARGET} (đích ĐÃ ĐÍNH CHÍNH của §13.10 b)`, () => {
    const n = rows.filter((r) => r.access).length
    expect(
      n,
      `đo từ đĩa = ${n}. Đích lô 2 = ${ACCESS_ADOPTION_TARGET} (21 màn lô 2; 11 màn legacy đóng băng). ` +
        'Số 24 trong prompt là phép cộng sai — 3 màn N2 nằm TRONG 21, không ngoài.',
    ).toBe(ACCESS_ADOPTION_TARGET)
  })

  it('mọi màn dùng useDetailAccess đều đã áp shell (không có SSoT lơ lửng)', () => {
    const orphan = rows.filter((r) => r.access && !r.shell).map((r) => r.path)
    expect(
      orphan,
      'Dùng composable mà không áp khuôn = vẫn tự vẽ 4 trạng thái ⇒ chưa đóng được false-empty.',
    ).toEqual([])
  })
})

// ─── Chốt dân số thư mục quét (SPEC §5.2 N6 — chống guard xanh giả) ───────────
// Guard ở trên khẳng định dạng "không tìm thấy vi phạm nào". Khẳng định đó đúng
// một cách RỖNG TUẾCH nếu bộ quét không đọc được file nào — điều xảy ra âm thầm
// khi thư mục bị dời/đổi tên. Chốt dưới đây biến tình huống đó thành ĐỎ.
// Số đo từ đĩa 2026-08-13: 137 file. Ngưỡng đặt thấp hơn có chủ ý để thêm/bớt
// vài file không gây đỏ giả; sửa ngưỡng phải là hành vi CÓ Ý THỨC.
describe('chốt dân số thư mục quét', () => {
  it('src/views/**/*.vue còn ít nhất 120 file — nếu không, guard đã ngừng canh', () => {
    expect(listFiles(VIEWS, { ext: '.vue', min: 120 }).length).toBeGreaterThanOrEqual(120)
  })
})
