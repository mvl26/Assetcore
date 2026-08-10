// Guard adoption vùng lỗi inline trong hộp thoại — CHỈ-GIẢM (AC-UX-062, docs/ui-ux/05 §6).
//
// Vấn đề nó chặn: hộp thoại từ chối thao tác mà lý do chỉ đến bằng toast tự tắt sau 4s
// (`composables/useToast.ts:33/:45`) trong khi hộp thoại vẫn mở ⇒ người dùng quay lại
// hộp thoại thì không còn dấu vết vì sao hỏng. Vòng 6 cài hợp đồng ĐÚNG 1 LẦN tại SSoT
// (`BaseModal.vue` prop `error` + `ModalInlineError.vue`); guard này giữ cho khoản đầu tư
// đó không rò: màn mới KHÔNG được sinh nợ mới, nợ cũ chỉ được GIẢM.
//
// Khuôn quét đi theo `modalOverlayHygiene.test.ts` (readdir + stripComments + đường dẫn
// tương đối) — KHÔNG viết bộ đếm thứ hai.
//
// ⚠️ ĐÍNH CHÍNH ĐO ĐẠC so với `05 §6.2` (đo lại từ đĩa 2026-08-03, trước khi sửa mã):
// vị ngữ §6.1 (lỗi gắn vào ĐÚNG hộp thoại) loại **19 − 5 = 14** file, không phải 15 —
// vì 4 file (`AssetDetailView` · `AssetLabelPrintView` · `CAPADetailView` · `RCADetailView`)
// có `role="alert"` NHƯNG là vùng lỗi NGOÀI hộp thoại (`05 §1` tự ghi nhận điều đó).
// Doc đếm 15 theo phép đo «0 `role="alert"` VÀ 0 `modal-error`» nên 4 file kia rơi khỏi sổ.
// Giữ ĐÚNG cả hai con số bằng HAI allowlist trên CÙNG một lần quét:
//   • ALLOWLIST_NO_INLINE_ERROR  — đúng phép đo của doc, ĐÓNG BĂNG 15 → nay **10**.
//   • ALLOWLIST_ALERT_OUTSIDE_DIALOG — 4 file có `role="alert"` ngoài hộp thoại, ĐÓNG BĂNG 4.
// Hai allowlist bịt luôn lỗ hổng: thêm một `role="alert"` lạc chỗ KHÔNG cho thoát guard.
import { describe, it, expect } from 'vitest'
import { readFileSync, readdirSync, statSync, existsSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve, relative, sep } from 'node:path'
// NO-FORK: bộ bỏ comment dùng chung (`src/test/stripComments.ts`) — AC-UX-065.
import { stripComments } from '@/test/stripComments'

const HERE = dirname(fileURLToPath(import.meta.url))
// src/components/common → src/components → src
const SRC = resolve(HERE, '../..')

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

function read(full: string): string {
  return stripComments(readFileSync(full, 'utf8'))
}

/**
 * Vị ngữ `05 §6.1` — vùng lỗi CHẶN gắn vào ĐÚNG hộp thoại.
 * Soi `:error=` TRONG THẺ MỞ `<BaseModal …>`, không grep cả file: `:error=` của một
 * component khác không được tính là đã đạt.
 */
function hasDialogScopedError(src: string): boolean {
  if (src.includes('data-testid="modal-error"')) return true
  if (src.includes('<ModalInlineError')) return true
  const tags = src.match(/<BaseModal\b[\s\S]*?>/g) ?? []
  return tags.some((t) => t.includes(':error=') || t.includes('v-bind:error='))
}

/** ĐÓNG BĂNG 15 (doc `05 §6.2`) — sau lô 1 phải còn ĐÚNG 10. Chỉ được xoá dòng. */
const ALLOWLIST_NO_INLINE_ERROR: readonly string[] = [
  'views/asset/DepreciationView.vue',
  'views/compliance/ComplianceRuleDetailView.vue',
  'views/compliance/ComplianceRuleListView.vue',
  'views/compliance/FindingDetailView.vue',
  'views/compliance/InternalAuditDetailView.vue',
  'views/compliance/InternalAuditListView.vue',
  'views/compliance/ManagementReviewDetailView.vue',
  'views/compliance/ManagementReviewListView.vue',
  'views/document/FirmwareCrDetailView.vue',
  'views/procurement/AvlListView.vue',
]

/**
 * ĐÓNG BĂNG 4 — có `role="alert"` nhưng vùng lỗi nằm NGOÀI hộp thoại (banner trang).
 * Đây là nợ lô 2, KHÔNG phải "đã đạt": thêm file mới vào nhóm này ⇒ ĐỎ.
 */
const ALLOWLIST_ALERT_OUTSIDE_DIALOG: readonly string[] = [
  'views/asset/AssetDetailView.vue',
  'views/asset/AssetLabelPrintView.vue',
  'views/incident/CAPADetailView.vue',
  'views/incident/RCADetailView.vue',
]

/**
 * LOẠI TRỪ CẤU TRÚC — KHÔNG phải "được tha nợ" (đối chiếu `CHROME_FILES` của
 * `modalOverlayHygiene.test.ts`).
 *
 * `NotificationModal.vue` là bản RENDER của hàng đợi `useModal()` (AC-UX-064). Nó không
 * gọi API, không gửi biểu mẫu, nên KHÔNG bao giờ nhận được "lỗi chặn thao tác" để mà
 * hiện inline. Ngược lại: chính nó LÀ bề mặt hiển thị lỗi (`useNotify` → `alert({tone:
 * 'critical'})`). Bind `:error` lên nó = lỗi lồng trong lỗi.
 *
 * Đưa vào `ALLOWLIST_NO_INLINE_ERROR` sẽ SAI theo hai hướng cùng lúc: (a) làm số nợ
 * đóng băng TĂNG 10 → 11 trên một allowlist CHỈ-GIẢM, (b) ghi một khoản nợ không tồn tại
 * để rồi vòng sau có người đi "trả".
 */
const RENDERER_FILES = new Set(['components/common/NotificationModal.vue'])

type Scan = { path: string; dialogScoped: boolean; hasAlertRole: boolean }

const scans: Scan[] = listVueFiles(SRC)
  .map((full) => ({ full, src: read(full) }))
  .filter(({ full, src }) => /import\s+BaseModal\b/.test(src) && !RENDERER_FILES.has(rel(full)))
  .map(({ full, src }) => ({
    path: rel(full),
    dialogScoped: hasDialogScopedError(src),
    hasAlertRole: src.includes('role="alert"'),
  }))

const consumers = scans.map((s) => s.path).sort()
const missing = scans.filter((s) => !s.dialogScoped).map((s) => s.path).sort()
const noInlineAtAll = scans
  .filter((s) => !s.dialogScoped && !s.hasAlertRole)
  .map((s) => s.path)
  .sort()
const alertOutsideDialog = scans
  .filter((s) => !s.dialogScoped && s.hasAlertRole)
  .map((s) => s.path)
  .sort()

describe('INV-UXMODERR-1/2 — nợ «0 vùng lỗi inline» CHỈ-GIẢM (15 → 10 sau lô 1)', () => {
  it('quét được tập file tiêu thụ BaseModal và không rỗng', () => {
    expect(consumers.length).toBeGreaterThanOrEqual(19)
  })

  it('allowlist đóng băng đúng 10 đường dẫn sau lô 1, không trùng', () => {
    expect(ALLOWLIST_NO_INLINE_ERROR).toHaveLength(10)
    expect(new Set(ALLOWLIST_NO_INLINE_ERROR).size).toBe(10)
  })

  it('KHÔNG có file mới thiếu vùng lỗi inline ngoài allowlist (tập con)', () => {
    const allowed = new Set(ALLOWLIST_NO_INLINE_ERROR)
    expect(
      noInlineAtAll.filter((p) => !allowed.has(p)),
      'Hộp thoại mới mà không có đường lỗi inline ⇒ lý do từ chối chỉ đến bằng toast tự ' +
        'tắt sau 4s. Bind `:error` trên <BaseModal> (hoặc dùng <ModalInlineError> cho overlay lai).',
    ).toEqual([])
  })

  it('CHỈ-GIẢM: số file «0 vùng lỗi inline» == 10 (từ 15 trước lô 1)', () => {
    expect(noInlineAtAll.length, `còn nợ: ${noInlineAtAll.join(', ')}`).toBe(10)
  })

  it('5 file lô 1 đã RỜI danh sách nợ', () => {
    const lot1 = [
      'views/inventory/CycleCountDetailView.vue',
      'views/needs/NeedsRequestDetailView.vue',
      'views/calibration/CalibrationScheduleListView.vue',
      'views/master-data/ReferenceDataView.vue',
      'views/auth/UserProfileFormView.vue',
    ]
    expect(missing.filter((p) => lot1.includes(p))).toEqual([])
  })
})

describe('INV-UXMODERR-1b — `role="alert"` NGOÀI hộp thoại không được dùng để lách guard', () => {
  it('allowlist nhóm này đóng băng đúng 4', () => {
    expect(ALLOWLIST_ALERT_OUTSIDE_DIALOG).toHaveLength(4)
  })

  it('KHÔNG có file mới rơi vào nhóm «có role=alert nhưng lỗi nằm ngoài hộp thoại»', () => {
    const allowed = new Set(ALLOWLIST_ALERT_OUTSIDE_DIALOG)
    expect(
      alertOutsideDialog.filter((p) => !allowed.has(p)),
      'Banner lỗi của TRANG nằm dưới lớp phủ hộp thoại ⇒ người dùng trong hộp thoại không ' +
        'bao giờ đọc được. Đưa lỗi vào chính hộp thoại.',
    ).toEqual([])
  })

  it('CHỈ-GIẢM: nhóm này ≤ 4', () => {
    expect(alertOutsideDialog.length).toBeLessThanOrEqual(4)
  })

  it('tổng nợ theo vị ngữ §6.1 == 14 (10 + 4) và ≤ số file tiêu thụ', () => {
    expect(missing.length).toBe(ALLOWLIST_NO_INLINE_ERROR.length + ALLOWLIST_ALERT_OUTSIDE_DIALOG.length)
    expect(missing.length).toBeLessThan(consumers.length)
  })
})

describe('INV-UXMODERR-3 — allowlist không có mục ma', () => {
  it('mọi mục tồn tại trên đĩa và THẬT SỰ tiêu thụ BaseModal', () => {
    const known = new Set(consumers)
    const bad: string[] = []
    for (const p of [...ALLOWLIST_NO_INLINE_ERROR, ...ALLOWLIST_ALERT_OUTSIDE_DIALOG]) {
      if (!existsSync(resolve(SRC, p))) bad.push(`${p} (không tồn tại)`)
      else if (!known.has(p)) bad.push(`${p} (không tiêu thụ BaseModal)`)
    }
    expect(bad).toEqual([])
  })
})

describe('INV-UXMODERR-4 — vùng lỗi KHÔNG tự tắt (0 hẹn giờ ở SSoT)', () => {
  it('BaseModal.vue và ModalInlineError.vue: 0 lần setTimeout', () => {
    for (const f of ['BaseModal.vue', 'ModalInlineError.vue']) {
      const src = readFileSync(resolve(HERE, f), 'utf8')
      expect((src.match(/setTimeout/g) ?? []).length, f).toBe(0)
    }
  })

  it('ModalInlineError.vue giữ đủ ngữ nghĩa alert trong mã nguồn', () => {
    const src = readFileSync(resolve(HERE, 'ModalInlineError.vue'), 'utf8')
    expect(src).toContain('data-testid="modal-error"')
    expect(src).toContain('role="alert"')
    expect(src).toContain('aria-live="assertive"')
  })
})

describe('INV-UXMODERR-5 — 8 hộp thoại lô 1: nhánh lỗi không đóng hộp thoại, một kênh duy nhất', () => {
  /** 8 hộp thoại lô 1 (`05 §5`) — soi ĐÚNG thân handler, không quét cả file. */
  const LOT1_HANDLERS: readonly [file: string, fn: string][] = [
    ['views/inventory/CycleCountDetailView.vue', 'doPost'],          // L1
    ['views/inventory/CycleCountDetailView.vue', 'doRecount'],       // L2
    ['views/needs/NeedsRequestDetailView.vue', 'doApprove'],         // L3
    ['views/needs/NeedsRequestDetailView.vue', 'doReject'],          // L4
    ['views/needs/NeedsRequestDetailView.vue', 'doRollIntoPlan'],    // L5
    ['views/calibration/CalibrationScheduleListView.vue', 'save'],   // L6 (đường B)
    ['views/master-data/ReferenceDataView.vue', 'save'],             // L7 (đường B)
    ['views/auth/UserProfileFormView.vue', 'confirmReject'],         // L8
  ]

  /** Cắt thân hàm `function <name>(…) { … }` bằng đếm ngoặc. */
  function bodyOf(src: string, fn: string): string {
    const m = new RegExp(`function\\s+${fn}\\s*\\(`).exec(src)
    if (!m) return ''
    const open = src.indexOf('{', m.index)
    if (open === -1) return ''
    let depth = 0
    for (let i = open; i < src.length; i++) {
      if (src[i] === '{') depth++
      else if (src[i] === '}') {
        depth--
        if (depth === 0) return src.slice(open, i + 1)
      }
    }
    return ''
  }

  const bodies = LOT1_HANDLERS.map(([file, fn]) => ({
    label: `${file} → ${fn}()`,
    body: bodyOf(read(resolve(SRC, file)), fn),
  }))

  it('đọc được thân của đủ 8 handler (chống guard rỗng khi hàm bị đổi tên)', () => {
    expect(bodies.filter((b) => b.body === '').map((b) => b.label)).toEqual([])
    expect(bodies).toHaveLength(8)
  })

  it('nhánh lỗi KHÔNG đóng hộp thoại (`show*.value = false` chỉ ở nhánh thành công)', () => {
    const CLOSE_RE = /\bshow[A-Za-z]*\s*\.\s*value\s*=\s*false/
    const offenders: string[] = []
    for (const { label, body } of bodies) {
      // Nhánh lỗi = khối `catch (…) { … }` và khối `if (!res) { … }` bên trong handler.
      for (const re of [/catch\s*\([^)]*\)\s*/g, /if\s*\(\s*!\s*res\s*\)\s*/g]) {
        let m: RegExpExecArray | null
        while ((m = re.exec(body)) !== null) {
          const open = body.indexOf('{', m.index)
          if (open === -1) continue
          let depth = 0
          for (let i = open; i < body.length; i++) {
            if (body[i] === '{') depth++
            else if (body[i] === '}') {
              depth--
              if (depth === 0) {
                if (CLOSE_RE.test(body.slice(open, i + 1))) offenders.push(label)
                break
              }
            }
          }
        }
      }
    }
    expect(
      offenders,
      'Đóng hộp thoại ở nhánh lỗi = người dùng mất cả ngữ cảnh lẫn dữ liệu vừa nhập.',
    ).toEqual([])
  })

  it('MỘT kênh duy nhất: thân handler không còn `toast.*` / `notify.fromError`', () => {
    const offenders: string[] = []
    for (const { label, body } of bodies) {
      if (/\btoast\s*\.\s*\w+\s*\(/.test(body)) offenders.push(`${label} — còn toast.*`)
      if (/notify\s*\.\s*fromError\s*\(/.test(body)) offenders.push(`${label} — còn notify.fromError`)
    }
    expect(
      offenders,
      'Lỗi CHẶN ra 2 kênh (inline + toast) ⇒ người dùng đọc 1, bỏ 1. Toast chỉ cho ' +
        'thông báo KHÔNG chặn (docs/ui-ux/05 §3).',
    ).toEqual([])
  })

  it('mỗi handler có đường lỗi inline: `silentError: true` hoặc ghi vào biến lỗi của hộp thoại', () => {
    const bad: string[] = []
    for (const { label, body } of bodies) {
      const pathA = body.includes('silentError: true')
      const pathB = /\b(err|\w*[Ee]rror)\s*\.\s*value\s*=/.test(body)
      if (!pathA && !pathB) bad.push(label)
    }
    expect(bad).toEqual([])
  })
})
