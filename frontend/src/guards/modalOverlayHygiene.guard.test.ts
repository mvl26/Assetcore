// Guard vệ sinh hộp thoại — CHỈ-GIẢM (docs/ui-ux/04 §5).
//
// Vấn đề nó chặn: hộp thoại tự vẽ (`fixed inset-0` + card tự dựng, không qua `BaseModal`)
// không có `role=dialog`, không bẫy focus, không trả focus, Escape không đóng. Vòng 5 cài
// hợp đồng a11y ĐÚNG 1 LẦN tại SSoT `BaseModal.vue`; nếu màn mới vẫn tự vẽ overlay thì
// khoản đầu tư đó rò ngay. Con số đóng băng dưới đây là TRẦN, không phải mục tiêu:
//   • thêm file tự vẽ overlay  ⇒ ĐỎ (tên file lạ hiện trong thông báo)
//   • di trú 1 file sang BaseModal ⇒ xoá 1 dòng allowlist (số GIẢM) ⇒ vẫn xanh
//
// Kèm 3 bất biến NO-FORK khoá A6 bằng mã (không bằng lời hứa): logic Tab-wrap + return-focus
// chỉ được tồn tại ở `composables/useFocusTrap.ts`.
import { describe, it, expect } from 'vitest'
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { resolve, relative, sep } from 'node:path'
import { COMPONENTS, FRONTEND_ROOT, GUARDS, SRC, listFiles } from '@/test/paths'
// NO-FORK: bộ bỏ comment dùng chung (`src/test/stripComments.ts`) — chú thích
// «KHÔNG dùng BaseModal» của CommandPalette không được đếm. Trước đây hàm này bị
// chép ở 3 guard; mỗi bản sao là một thước đo khác nhau (AC-UX-065).
import { stripComments } from '@/test/stripComments'

// src/components/common → src/components → src → frontend

function listVueFiles(dir: string, out: string[] = []): string[] {
  for (const entry of readdirSync(dir)) {
    if (entry === 'node_modules' || entry.startsWith('.')) continue
    const full = resolve(dir, entry)
    if (statSync(full).isDirectory()) listVueFiles(full, out)
    else if (entry.endsWith('.vue')) out.push(full)
  }
  return out
}

/** Đường dẫn tương đối `frontend/` với dấu `/` — ổn định trên mọi HĐH. */
function rel(full: string): string {
  return relative(FRONTEND_ROOT, full).split(sep).join('/')
}

function read(full: string): string {
  return stripComments(readFileSync(full, 'utf8'))
}

/**
 * 4 file khung: overlay của chúng KHÔNG phải hộp thoại (nền tải, khung ứng dụng, thanh trên)
 * ⇒ nằm ngoài phép đếm, không phải "được tha".
 */
const CHROME_FILES = new Set([
  'src/components/common/BaseModal.vue',
  'src/components/common/LoadingSpinner.vue',
  'src/components/common/AppLayout.vue',
  'src/components/common/AppTopBar.vue',
])

/** ĐÓNG BĂNG ở 29 — CHỈ-GIẢM. Xoá dòng khi di trú xong; THÊM dòng là sai (phải sửa mã).
 *  30 → 29: `NotificationModal.vue` đã render qua BaseModal (AC-UX-064). */
const ALLOWLIST_SELF_DRAWN: readonly string[] = [
  'src/components/commissioning/SubmitForApprovalModal.vue',
  'src/components/commissioning/WorkflowActions.vue',
  'src/components/import/ImportWizardModal.vue',
  'src/views/asset/AssetTransferDetailView.vue',
  'src/views/asset/DeviceModelFormView.vue',
  'src/views/asset/DeviceModelListView.vue',
  'src/views/audit/AuditTrailListView.vue',
  'src/views/calibration/CalibrationDetailView.vue',
  'src/views/cm/CMWorkOrderDetailView.vue',
  'src/views/commissioning/CommissioningDetailView.vue',
  'src/views/document/DocumentDetailView.vue',
  'src/views/document/DocumentRequestListView.vue',
  'src/views/document/FirmwareCrListView.vue',
  'src/views/incident/IncidentDetailView.vue',
  'src/views/inventory/SparePartDetailView.vue',
  'src/views/inventory/SparePartListView.vue',
  'src/views/inventory/UomConversionView.vue',
  'src/views/inventory/WarehouseDetailView.vue',
  'src/views/inventory/WarehouseListView.vue',
  'src/views/inventory/WatchlistView.vue',
  'src/views/master-data/SlaPolicyListView.vue',
  'src/views/needs/ProcurementPlanListView.vue',
  'src/views/pm/PMCalendarView.vue',
  'src/views/pm/PmScheduleListView.vue',
  'src/views/pm/PmTemplateListView.vue',
  'src/views/pm/PMWorkOrderDetailView.vue',
  'src/views/purchase/PurchaseDetailView.vue',
  'src/views/training/CompetencyDetailView.vue',
  'src/views/training/SessionDetailView.vue',
]

/**
 * ĐÓNG BĂNG ở 4 — CHỈ-GIẢM. File VỪA import `BaseModal` VỪA tự vẽ overlay.
 * Không khoá riêng thì cứ thêm 1 dòng `import BaseModal` là thoát guard ở trên.
 */
const ALLOWLIST_HYBRID: readonly string[] = [
  'src/views/asset/AssetDetailView.vue',
  'src/views/asset/DepreciationView.vue',
  'src/views/calibration/CalibrationScheduleListView.vue',
  'src/views/master-data/ReferenceDataView.vue',
]

const vueFiles = listVueFiles(SRC)

type Scan = { path: string; selfDrawn: boolean; hybrid: boolean }

const scans: Scan[] = vueFiles.map((full) => {
  const path = rel(full)
  const src = read(full)
  const hasOverlay = src.includes('fixed inset-0')
  const usesBaseModal = /import\s+BaseModal\b/.test(src)
  return {
    path,
    selfDrawn: hasOverlay && !usesBaseModal && !CHROME_FILES.has(path),
    hybrid: hasOverlay && usesBaseModal,
  }
})

const selfDrawn = scans.filter((s) => s.selfDrawn).map((s) => s.path).sort()
const hybrid = scans.filter((s) => s.hybrid).map((s) => s.path).sort()

describe('TC-UX5-30 — overlay tự vẽ: allowlist CHỈ-GIẢM (đóng băng 29)', () => {
  it('allowlist đóng băng đúng 29 đường dẫn, không trùng', () => {
    expect(ALLOWLIST_SELF_DRAWN).toHaveLength(29)
    expect(new Set(ALLOWLIST_SELF_DRAWN).size).toBe(29)
  })

  it('KHÔNG có file mới tự vẽ overlay ngoài allowlist', () => {
    const allowed = new Set(ALLOWLIST_SELF_DRAWN)
    const outsiders = selfDrawn.filter((p) => !allowed.has(p))
    expect(
      outsiders,
      'File tự vẽ hộp thoại (`fixed inset-0`) mà KHÔNG qua BaseModal ⇒ mất role=dialog, ' +
        'bẫy focus, Escape, trả focus. Dùng <BaseModal> thay vì dựng overlay tay.',
    ).toEqual([])
  })

  it('CHỈ-GIẢM: số file tự vẽ hiện tại ≤ 29 (di trú xong thì xoá dòng allowlist)', () => {
    expect(selfDrawn.length).toBeLessThanOrEqual(29)
  })
})

describe('TC-UX5-31 — file lai (vừa BaseModal vừa tự vẽ): đóng băng 4', () => {
  it('allowlist lai đúng 4 đường dẫn', () => {
    expect(ALLOWLIST_HYBRID).toHaveLength(4)
  })

  it('KHÔNG có file lai mới ngoài allowlist', () => {
    const allowed = new Set(ALLOWLIST_HYBRID)
    expect(
      hybrid.filter((p) => !allowed.has(p)),
      'File đã import BaseModal thì mọi hộp thoại trong đó phải dùng BaseModal — ' +
        'không được còn overlay tay (lỗ hổng lách guard TC-UX5-30).',
    ).toEqual([])
  })

  it('CHỈ-GIẢM: số file lai ≤ 4', () => {
    expect(hybrid.length).toBeLessThanOrEqual(4)
  })
})

describe('TC-UX5-32 — NO-FORK: logic bẫy focus chỉ tồn tại 1 nơi (A6)', () => {
  const TAB_SELECTOR = '[tabindex]:not([tabindex="-1"])'

  it('selector tabbable chỉ xuất hiện trong composables/useFocusTrap.ts', () => {
    const OWNER = 'src/composables/useFocusTrap.ts'
    const OWNER_TEST = 'src/composables/useFocusTrap.test.ts'
    const offenders: string[] = []
    const walk = (dir: string): void => {
      for (const entry of readdirSync(dir)) {
        if (entry === 'node_modules' || entry.startsWith('.')) continue
        const full = resolve(dir, entry)
        if (statSync(full).isDirectory()) { walk(full); continue }
        if (!/\.(ts|vue)$/.test(entry)) continue
        const path = rel(full)
        if (path === OWNER || path === OWNER_TEST || path === rel(resolve(GUARDS, 'modalOverlayHygiene.guard.test.ts'))) continue
        if (read(full).includes(TAB_SELECTOR)) offenders.push(path)
      }
    }
    walk(SRC)
    expect(
      offenders,
      'Logic Tab-wrap bị nhân bản — dùng `useFocusTrap` / `tabbablesIn` thay vì chép selector.',
    ).toEqual([])
  })
})

describe('TC-UX5-33/34 — dấu vết di trú (A6)', () => {
  const cmdk = read(resolve(SRC, 'components/common/CommandPalette.vue'))
  const baseModal = read(resolve(SRC, 'components/common/BaseModal.vue'))

  it('TC-UX5-33 CommandPalette.vue: 0 hit `function tabbables` · 0 hit `returnFocusEl` · ≥1 `useFocusTrap`', () => {
    expect(cmdk).not.toMatch(/function tabbables/)
    expect(cmdk).not.toMatch(/returnFocusEl/)
    expect(cmdk).toMatch(/useFocusTrap/)
  })

  it('TC-UX5-34 BaseModal.vue: ≥1 `useFocusTrap` · 0 `addEventListener` (ESC do composable lo)', () => {
    expect(baseModal).toMatch(/useFocusTrap/)
    expect(baseModal).not.toMatch(/addEventListener/)
  })

  it('BaseModal.vue giữ nguyên hợp đồng testid + không tự đăng ký phím Escape', () => {
    expect(baseModal).toContain('data-testid="modal-card"')
    expect(baseModal).toContain('data-testid="modal-close"')
    // `@keydown.esc` trên card = handler thứ 2 ⇒ emit close 2 lần (A3 đỏ).
    expect(baseModal).not.toMatch(/keydown\.esc/)
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
