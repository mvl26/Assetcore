// AC-UX-066 — ngân sách `confirm()` trần: CHỈ-GIẢM, theo BẢN ĐỒ per-file.
//
// Vấn đề nó chặn: `window.confirm` CHẶN vòng lặp sự kiện (từng làm treo trình duyệt khi
// chạy tự động — xem chú thích `ProcurementPlanDetailView.vue:38`), không bẫy focus,
// không trả focus, không đổi được nhãn nút sang tiếng Việt («OK»/«Cancel» do trình duyệt
// vẽ, LL-FE-53 không với tới), và không hiện được lý do chặn dạng inline. SSoT thay thế
// là `useNotify().confirm()` → `useModal` → `NotificationModal` → `BaseModal` (AC-UX-064).
//
// Vì sao BẢN ĐỒ per-file chứ không phải một con số tổng: một con số tổng cho phép "trả nợ
// chỗ dễ, vay chỗ khó" mà vẫn xanh. Bản đồ khoá cả ba chiều:
//   (a) tổng KHÔNG được tăng,
//   (b) file LẠ (không có trong bản đồ) có `confirm(` ⇒ ĐỎ — chống né guard bằng cách đẻ
//       file mới,
//   (c) một file vượt hạn mức RIÊNG của nó ⇒ ĐỎ.
// Giảm được thì PHẢI hạ bản đồ xuống (assert (d) tự nhắc) — nếu không, nợ đã trả sẽ âm
// thầm được "vay lại" ở vòng sau.
//
// Phép đo dùng `stripComments` DÙNG CHUNG (`src/test/stripComments.ts`): chú thích mô tả
// `confirm()` KHÔNG phải là `confirm()`. Chính vì trước đây đếm không strip comment mà
// `docs/ui-ux/04` ghi 44/31 trong khi đĩa là 42/28.
import { describe, it, expect } from 'vitest'
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { resolve, relative, sep } from 'node:path'
import { SRC, listFiles } from '@/test/paths'
import { stripComments } from '@/test/stripComments'

// src/components/common → src/components → src

/** Chỉ quét 2 cây có UI người dùng chạm vào. */
const SCAN_DIRS = ['views', 'components'] as const

/**
 * `confirm(` KHÔNG đứng sau dấu chấm / ký tự định danh.
 *
 * Loại được `notify.confirm(` / `modal.confirm(` (SSoT — thứ ta ĐANG chuyển sang), `window.confirm(`,
 * `confirmReceipt(`, `showConfirm(`. Bắt được `confirm('…')` và `!confirm(`.
 * Khớp đúng công thức grep ghi trong `docs/ui-ux/04 §5`, để số trong doc và số trong
 * guard không bao giờ trôi khỏi nhau.
 */
const BARE_CONFIRM_RE = /(^|[^.\w$])confirm\s*\(/g

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

function countBare(full: string): number {
  const src = stripComments(readFileSync(full, 'utf8'))
  return (src.match(BARE_CONFIRM_RE) ?? []).length
}

/**
 * BẢN ĐỒ NỢ — đóng băng theo phép đo từ đĩa 2026-08-04, SAU lô 1 (AC-UX-066).
 *
 * Baseline trước lô 1: 42 call-site / 28 file. Lô 1 đóng 21 call-site ở 7 file
 * (`PurchaseDetailView` 5 · `UomConversionView` 4 · `StockMovementDetailView` 3 ·
 * `AssetTransferDetailView` 3 · `PmTemplateListView` 2 · `DocumentDetailView` 2 ·
 * `AssetDepreciationSchedule` 2) ⇒ còn 21 call-site / 21 file.
 *
 * ⚠️ Chỉ được SỬA XUỐNG. Muốn thêm một dòng vào đây thì việc cần làm là sửa mã, không
 * phải sửa bản đồ.
 */
const BUDGET: Readonly<Record<string, number>> = {
  'views/asset/AssetDetailView.vue': 1,
  'views/asset/AssetTransferListView.vue': 1,
  'views/asset/DeviceModelFormView.vue': 1,
  'views/asset/DeviceModelListView.vue': 1,
  'views/compliance/ComplianceRuleListView.vue': 1,
  'views/compliance/ScorecardView.vue': 1,
  'views/document/DocumentManagement.vue': 1,
  'views/document/DocumentRequestListView.vue': 1,
  'views/document/FirmwareCrListView.vue': 1,
  'views/incident/IncidentDetailView.vue': 1,
  'views/inventory/SparePartDetailView.vue': 1,
  'views/inventory/WarehouseDetailView.vue': 1,
  'views/inventory/WarehouseListView.vue': 1,
  'views/master-data/ReferenceDataView.vue': 1,
  'views/master-data/SlaPolicyListView.vue': 1,
  'views/pm/PMWorkOrderDetailView.vue': 1,
  'views/pm/PmScheduleListView.vue': 1,
  'views/purchase/ServiceContractDetailView.vue': 1,
  'views/purchase/SupplierDetailView.vue': 1,
  'views/purchase/SupplierFormView.vue': 1,
  'views/purchase/SupplierListView.vue': 1,
}

/** 7 file lô 1 — đã trả hết nợ, phải giữ ở 0 (chống lùi). */
const LOT1_CLEARED: readonly string[] = [
  'views/purchase/PurchaseDetailView.vue',
  'views/inventory/UomConversionView.vue',
  'views/inventory/StockMovementDetailView.vue',
  'views/asset/AssetTransferDetailView.vue',
  'views/pm/PmTemplateListView.vue',
  'views/document/DocumentDetailView.vue',
  'components/asset/AssetDepreciationSchedule.vue',
]

const BUDGET_TOTAL = Object.values(BUDGET).reduce((a, b) => a + b, 0)

/** Lệnh grep tái lập được phép đo — dán vào thông báo lỗi để người sửa không phải đoán. */
const REPRO =
  '\n  Tái lập:  cd frontend && grep -rnE "(^|[^.\\w])confirm\\s*\\(" src/views src/components ' +
  '--include=*.vue\n  (rồi TRỪ các dòng chú thích — guard này strip comment trước khi đếm)\n' +
  '  Cách sửa (ADR-UX-16): `if (!(await notify.confirm({ title, body, tone }))) return` — ' +
  '`useNotify()` từ `@/composables/useNotify`. KHÔNG gọi `useModal()` thẳng từ view.\n'

const actual = new Map<string, number>()
for (const dir of SCAN_DIRS) {
  for (const full of listVueFiles(resolve(SRC, dir))) {
    const n = countBare(full)
    if (n > 0) actual.set(rel(full), n)
  }
}

const actualTotal = [...actual.values()].reduce((a, b) => a + b, 0)

describe('AC-UX-066 — ngân sách `confirm()` trần (CHỈ-GIẢM, bản đồ per-file)', () => {
  it('bản đồ khớp con số công bố: 21 call-site / 21 file (sau lô 1)', () => {
    expect(BUDGET_TOTAL).toBe(21)
    expect(Object.keys(BUDGET)).toHaveLength(21)
  })

  // (b) file LẠ — chống né guard bằng cách đẻ file `.vue` mới.
  it('KHÔNG có file lạ: mọi file còn `confirm(` trần đều nằm trong bản đồ', () => {
    const strangers = [...actual.keys()].filter((p) => !(p in BUDGET)).sort()
    expect(
      strangers,
      'File KHÔNG có trong bản đồ ngân sách mà vẫn dùng `confirm()` trần. ' +
        'Ngân sách CHỈ-GIẢM: mã mới phải dùng `notify.confirm()` ngay từ đầu, ' +
        'không được thêm dòng vào bản đồ.' + REPRO,
    ).toEqual([])
  })

  // (c) từng file không vượt hạn mức riêng.
  it('KHÔNG file nào vượt hạn mức riêng của nó', () => {
    const over = [...actual.entries()]
      .filter(([p, n]) => p in BUDGET && n > BUDGET[p])
      .map(([p, n]) => `${p}: ${n} > ${BUDGET[p]}`)
      .sort()
    expect(over, 'Số lần `confirm()` trần TĂNG so với bản đồ.' + REPRO).toEqual([])
  })

  // (a) tổng không tăng.
  it('tổng số `confirm()` trần ≤ tổng bản đồ', () => {
    expect(
      actualTotal,
      `Tổng ${actualTotal} > ngân sách ${BUDGET_TOTAL}.` + REPRO,
    ).toBeLessThanOrEqual(BUDGET_TOTAL)
  })

  // (d) giảm rồi thì PHẢI hạ bản đồ — nếu không, nợ đã trả bị "vay lại" âm thầm.
  it('bản đồ không có mục MA: mọi mục đều còn `confirm(` thật trên đĩa', () => {
    const ghosts = Object.keys(BUDGET).filter((p) => !actual.has(p)).sort()
    expect(
      ghosts,
      'Các file này đã hết `confirm()` trần — HẠ bản đồ xuống (xoá dòng tương ứng) ' +
        'để phần nợ đã trả không bị vay lại ở vòng sau.',
    ).toEqual([])
  })

  it('7 file lô 1 (AC-UX-065) giữ ĐÚNG 0 — chống lùi', () => {
    for (const p of LOT1_CLEARED) {
      expect(actual.get(p) ?? 0, `${p} đã di trú sang notify.confirm() ở lô 1, không được quay lại.`).toBe(0)
      expect(p in BUDGET, `${p} không được nằm trong bản đồ nợ nữa.`).toBe(false)
    }
  })

  it('phép đo STRIP COMMENT: dòng chú thích chứa `confirm(` KHÔNG được tính', () => {
    // 3 file dưới đây CHỈ nhắc `confirm(` trong chú thích/HTML comment (đo 2026-08-04).
    // Đây chính là chỗ phép đo cũ đếm sai ⇒ doc ghi 44/31 thay vì 42/28.
    const COMMENT_ONLY = [
      'views/needs/ProcurementPlanDetailView.vue',
      'views/calibration/CalibrationDetailView.vue',
      'components/common/NotificationModal.vue',
    ]
    for (const p of COMMENT_ONLY) {
      const raw = readFileSync(resolve(SRC, p), 'utf8')
      expect(raw, `${p} phải còn chú thích nhắc confirm( để TC này có ý nghĩa`).toMatch(/confirm\s*\(/)
      expect(
        actual.get(p) ?? 0,
        `${p}: chú thích mô tả \`confirm()\` bị đếm thành nợ — stripComments không chạy.`,
      ).toBe(0)
    }
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
