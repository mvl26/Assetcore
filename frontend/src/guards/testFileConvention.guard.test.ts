// Copyright (c) 2026, AssetCore Team
// SSoT CƯỠNG CHẾ vị trí & tên file test FE — `docs/architecture/SPEC_chuan_hoa_cau_truc_frontend.md` §7.1.
//
// ─── Vì sao có file này ───────────────────────────────────────────────────────
// Rule bằng văn bản (skill, CLAUDE.md) dễ bị bỏ qua — người quên, mô hình quên.
// File này là lớp thứ hai: nó ĐỎ khi ai đó tạo file test sai chỗ hoặc sai tên,
// ngay trong lượt chạy suite, không đợi ai đọc tài liệu.
//
// ─── Ba nhà, không có nhà thứ tư ─────────────────────────────────────────────
//   1. `<thư-mục-nguồn>/tests/` — test của MỘT file nguồn nằm trong thư mục con
//      `tests/` của chính thư mục chứa nguồn. Vd `views/cm/CMCreateView.vue` ⇒
//      `views/cm/tests/CMCreateView.test.ts` (hoặc `CMCreateView.<khiaCanh>.test.ts`).
//      `<Nguồn>` khớp CHÍNH XÁC tên file nguồn ở THƯ MỤC CHA.
//   2. `src/guards/`      — test đọc đĩa / cưỡng chế quy ước / parity doc↔mã.
//                            Tên `<chuDe>.guard.test.ts`.
//   3. `src/integration/` — test khởi động app / route / luồng chéo nhiều nguồn.
//                            Tên `<luong>.integration.test.ts`.
//
// ⚠️ Quy ước nhà #1 đổi ngày **2026-08-13** theo yêu cầu user: trước đó test đặt
// NGANG HÀNG file nguồn; nay bắt buộc nằm trong `tests/`. `guards/` và
// `integration/` KHÔNG thêm tầng `tests/` — bản thân chúng đã là nhà test riêng.
//
// ─── Nguyên tắc allowlist ─────────────────────────────────────────────────────
// Mọi ngoại lệ tồn dư nằm trong allowlist **ĐÓNG BĂNG, CHỈ-GIẢM**: guard tự đỏ nếu
// allowlist DÀI RA. Muốn thêm một dòng vào đây thì việc cần làm là đổi tên file,
// không phải sửa sổ.
import { describe, it, expect } from 'vitest'
import { readFileSync, existsSync, statSync, readdirSync } from 'node:fs'
import { resolve, relative, sep } from 'node:path'
import { SRC, GUARDS, INTEGRATION, listFiles } from '@/test/paths'

const rel = (abs: string): string => relative(SRC, abs).split(sep).join('/')

/** Mọi file test của FE — chốt dân số để guard không tự vô hiệu (SPEC §5.2 N6). */
const TEST_FILES = listFiles(SRC, { ext: '.test.ts', min: 380 }).map(rel)
/** Mọi file NGUỒN (không phải test). */
const SOURCE_FILES = listFiles(SRC, { ext: ['.vue', '.ts'], min: 300 })
  .map(rel)
  .filter((p) => !p.endsWith('.test.ts'))

const dirOf = (p: string): string => (p.includes('/') ? p.slice(0, p.lastIndexOf('/')) : '')
const baseOf = (p: string): string => p.slice(p.lastIndexOf('/') + 1)
const inHouse = (p: string, house: string): boolean => p.startsWith(`${house}/`)

const SOURCE_SET = new Set(SOURCE_FILES)

/**
 * ĐÓNG BĂNG · CHỈ-GIẢM — 35 file test co-located mà tên KHÔNG khớp một file nguồn
 * cùng thư mục (thường vì chúng chạm nhiều nguồn, hoặc đặt tên theo hành vi).
 * Đổi tên file để XOÁ dòng; TUYỆT ĐỐI không thêm dòng mới.
 */
const K2_ALLOWLIST: readonly string[] = [
  'api/tests/axios429.test.ts',
  'api/tests/axios500Traceback.test.ts',
  'api/tests/closeCapaGate.test.ts',
  'api/tests/depreciationByCategory.test.ts',
  'api/tests/detailReadForbiddenEnvelope.test.ts',
  'api/tests/imm08AssignTechnicianVerb.test.ts',
  'api/tests/imm09AttachPhoto.test.ts',
  'api/tests/imm12AttachPhoto.test.ts',
  'api/tests/importRowLabels.test.ts',
  'api/tests/listAssetsCoercion.test.ts',
  'api/tests/printAssetLabelsPdf.test.ts',
  'api/tests/rcaSubmitFieldsEnvelope.test.ts',
  'api/tests/sanitizeBusinessMessage.test.ts',
  'api/tests/userAssignableUsers.test.ts',
  'components/asset/tests/assetQrLabelNoTagPath.test.ts',
  'components/common/tests/BaseModalInlineError.test.ts',
  'components/common/tests/NotificationModalBaseModal.test.ts',
  'components/dashboard/tests/drilldown.test.ts',
  'components/dashboard/tests/rowDrill.test.ts',
  'composables/tests/importGroupedWizard.test.ts',
  'constants/tests/sidebarGroupsD7.test.ts',
  'router/tests/sidebarRouteParity.test.ts',
  'stores/tests/assetHistoryTruncation.test.ts',
  'stores/tests/detailFetchClearsOnError.test.ts',
  'views/asset/tests/deviceModelReadonlyGate.test.ts',
  'views/compliance/tests/complianceDetailNotFound.test.ts',
  'views/compliance/tests/managementReviewStatusLabelParity.test.ts',
  'views/dashboard/personas/tests/adminDashboardBytTiles.test.ts',
  'views/dashboard/personas/tests/personaDashboards.test.ts',
  'views/incident/tests/chronicTileSoT.test.ts',
  'views/incident/tests/connectionsAssetFilterWire.test.ts',
  'views/incident/tests/slaBreachLiveSoT.test.ts',
  'views/inventory/tests/inventoryConfirmDialog.test.ts',
  'views/pm/tests/pmDashboardKpiScope.test.ts',
  'views/training/tests/trainingDetailNotFound.test.ts',
]
const K2_FROZEN_SIZE = 35

// ── K1/K2 ─────────────────────────────────────────────────────────────────────
describe('K1/K2 — mỗi file test có NHÀ hợp lệ và tên nói ra nó kiểm cái gì', () => {
  it('allowlist K2 CHỈ ĐƯỢC GIẢM — không dòng nào được thêm', () => {
    expect(
      K2_ALLOWLIST.length,
      'allowlist dài ra = quy ước đang bị nới. Đổi tên file thay vì thêm dòng.',
    ).toBeLessThanOrEqual(K2_FROZEN_SIZE)
    expect(new Set(K2_ALLOWLIST).size, 'allowlist có dòng trùng').toBe(K2_ALLOWLIST.length)
  })

  it('mọi dòng allowlist trỏ file CÓ THẬT — dọn sổ trong cùng lượt đổi tên', () => {
    const dead = K2_ALLOWLIST.filter((p) => !existsSync(resolve(SRC, p)))
    expect(dead, 'allowlist trỏ file đã đổi tên/xoá').toEqual([])
  })

  it('K1a: test co-located PHẢI nằm trong thư mục con `tests/`, không ngang hàng nguồn', () => {
    const stray = TEST_FILES.filter(
      (p) => !inHouse(p, 'guards') && !inHouse(p, 'integration') && dirOf(p).split('/').pop() !== 'tests',
    )
    expect(
      stray,
      'file test đặt ngang hàng file nguồn — quy ước 2026-08-13 bắt buộc `<thư-mục-nguồn>/tests/`',
    ).toEqual([])
  })

  it('K1b: `tests/` phải nằm cạnh NGUỒN, và tên test khớp một nguồn ở thư mục cha', () => {
    const allow = new Set(K2_ALLOWLIST)
    const homeless = TEST_FILES.filter((p) => {
      if (inHouse(p, 'guards') || inHouse(p, 'integration') || allow.has(p)) return false
      const testsDir = dirOf(p)
      if (testsDir.split('/').pop() !== 'tests') return true // đã báo ở K1a
      const parent = testsDir.slice(0, testsDir.lastIndexOf('/'))
      const source = baseOf(p).replace(/\.test\.ts$/, '').split('.')[0]
      return !SOURCE_SET.has(`${parent}/${source}.vue`) && !SOURCE_SET.has(`${parent}/${source}.ts`)
    })
    expect(
      homeless,
      'tên test không khớp file nguồn nào ở thư mục CHA của `tests/`, và cũng không ở ' +
        'guards/ hay integration/ — không có nhà thứ tư',
    ).toEqual([])
  })

  it('K1c: `tests/` rỗng hoặc `tests/` không có nguồn ở cha = thư mục thừa', () => {
    const orphan: string[] = []
    const walk = (dir: string): void => {
      for (const e of readdirSync(dir, { withFileTypes: true })) {
        if (!e.isDirectory()) continue
        const abs = resolve(dir, e.name)
        if (e.name === 'tests') {
          const files = readdirSync(abs).filter((x) => x.endsWith('.test.ts'))
          const parent = rel(dir)
          const hasSource = SOURCE_FILES.some((s) => dirOf(s) === parent)
          if (files.length === 0) orphan.push(`${rel(abs)} — rỗng`)
          else if (!hasSource) orphan.push(`${rel(abs)} — thư mục cha không có file nguồn nào`)
        } else walk(abs)
      }
    }
    walk(SRC)
    expect(orphan, 'thư mục `tests/` mồ côi — xoá hoặc chuyển nội dung sang guards/·integration/').toEqual([])
  })

  it('K2: tên trong `guards/` và `integration/` đúng hậu tố quy ước', () => {
    const badGuard = TEST_FILES.filter((p) => inHouse(p, 'guards') && !p.endsWith('.guard.test.ts'))
    const badInteg = TEST_FILES.filter(
      (p) => inHouse(p, 'integration') && !p.endsWith('.integration.test.ts'),
    )
    expect(badGuard, 'file trong guards/ phải tên `<chuDe>.guard.test.ts`').toEqual([])
    expect(badInteg, 'file trong integration/ phải tên `<luong>.integration.test.ts`').toEqual([])
  })
})

// ── K3/K4/K5 ──────────────────────────────────────────────────────────────────
describe('K3/K4/K5 — cấm mã ticket trong tên · cấm .spec.ts · cấm __tests__/', () => {
  it('K3: 0 mã ticket trong TÊN FILE (mã đi vào describe()/it())', () => {
    const bad = TEST_FILES.filter(
      (p) => /\.(ac|acr|cr)\d+\./i.test(baseOf(p)) || /AC-(CR|UX)/i.test(baseOf(p)),
    )
    expect(
      bad,
      'mã sổ (acr92, AC-CR-…) chết theo vòng phát hành — đưa vào mô tả test, không vào tên file',
    ).toEqual([])
  })

  it('K4: 0 file `*.spec.ts` — chỉ dùng `.test.ts`', () => {
    const spec = listFiles(SRC, { ext: '.spec.ts', min: 0 }).map(rel)
    expect(spec, 'hai đuôi song song = hai quy ước; chỉ giữ `.test.ts`').toEqual([])
  })

  it('K5: 0 thư mục `__tests__`', () => {
    const found: string[] = []
    const walk = (dir: string): void => {
      for (const e of readdirSync(dir, { withFileTypes: true })) {
        if (!e.isDirectory()) continue
        const abs = resolve(dir, e.name)
        if (e.name === '__tests__') found.push(rel(abs))
        else walk(abs)
      }
    }
    walk(SRC)
    expect(found, 'test đi cạnh nguồn, hoặc vào guards/, hoặc integration/').toEqual([])
  })
})

// ── K6 ────────────────────────────────────────────────────────────────────────
/** Neo đường dẫn trỏ RA NGOÀI thư mục của chính file test. */
const CROSS_DIR_ANCHOR =
  /\b(DOCS|REPO_ROOT|FRONTEND_ROOT|VIEWS|COMPONENTS|GUARDS|INTEGRATION|API|STORES|CONSTANTS|UTILS|ROUTER|LOCALES|COMPOSABLES|TYPES)\b/

describe('K6 — guard đọc đĩa phải ở `src/guards/`', () => {
  it('ngoài guards/: 0 file QUÉT THƯ MỤC (readdirSync / import.meta.glob)', () => {
    const bad = TEST_FILES.filter((p) => !inHouse(p, 'guards')).filter((p) =>
      /readdirSync|import\.meta\s*(?:as\s+any\s*)?\)?\s*\.?\s*glob|\bglob\(/.test(
        readFileSync(resolve(SRC, p), 'utf8'),
      ),
    )
    expect(
      bad,
      'quét thư mục = cưỡng chế quy ước trên cả cây ⇒ là guard ⇒ thuộc src/guards/. ' +
        'Lưu ý `import.meta.glob` cũng là quét đĩa dù không dùng node:fs.',
    ).toEqual([])
  })

  it('ngoài guards/: chỉ được đọc file NGUỒN ở thư mục cha của `tests/`', () => {
    const offenders: string[] = []
    for (const p of TEST_FILES) {
      if (inHouse(p, 'guards')) continue
      const text = readFileSync(resolve(SRC, p), 'utf8')
      if (!/readFileSync/.test(text)) continue
      // Test nằm ở `<X>/tests/` ⇒ file nguồn nó được phép đọc nằm ở `<X>`.
      const testsDir = dirOf(p)
      const ownDir = testsDir.endsWith('/tests') ? testsDir.slice(0, -'/tests'.length) : testsDir

      // `resolve(SRC, 'a/b/C.vue')` — so thư mục đích với thư mục NGUỒN của file test.
      for (const m of text.matchAll(/resolve\(\s*SRC\s*,\s*'([^']+)'/g)) {
        const target = m[1]
        const targetDir = target.includes('/') ? target.slice(0, target.lastIndexOf('/')) : ''
        if (targetDir !== ownDir) offenders.push(`${p} → đọc ${target}`)
      }
      // neo bất kỳ trỏ ra ngoài thư mục
      for (const line of text.split('\n')) {
        if (!/read(File|dir)Sync\(|resolve\(/.test(line)) continue
        if (/^\s*(\/\/|\*)/.test(line)) continue
        if (CROSS_DIR_ANCHOR.test(line)) offenders.push(`${p} → neo ngoài thư mục: ${line.trim().slice(0, 70)}`)
        if (/resolve\([^)]*'\.\.\//.test(line)) offenders.push(`${p} → đường dẫn leo cấp: ${line.trim().slice(0, 70)}`)
      }
    }
    expect(
      [...new Set(offenders)],
      'test co-located chỉ được đọc file NGUỒN CẠNH NÓ. Đọc sang thư mục khác = ' +
        'đối chiếu chéo ⇒ là guard ⇒ chuyển vào src/guards/ (SPEC §5.1).',
    ).toEqual([])
  })
})

// ── K7/K8 ─────────────────────────────────────────────────────────────────────
/**
 * Chính file này chứa các MẪU bị cấm dưới dạng regex literal, nên nó sẽ tự bắt
 * mình nếu quét bằng văn bản. Đây là ngoại lệ có thật và duy nhất — file định
 * nghĩa luật không thể là đối tượng của luật ở tầng văn bản.
 */
const SELF = 'guards/testFileConvention.guard.test.ts'

describe('K7/K8 — guard không dùng đường dẫn theo độ sâu, và phải chốt dân số', () => {
  const guardFiles = TEST_FILES.filter((p) => inHouse(p, 'guards') && p !== SELF)

  it('file tự loại trừ CÓ THẬT — nếu đổi tên phải cập nhật hằng SELF', () => {
    expect(TEST_FILES, 'hằng SELF trỏ file không tồn tại ⇒ K7/K8 đang quét cả chính nó').toContain(SELF)
  })

  it('có ít nhất 30 guard (chốt dân số — chống guard-của-guard tự vô hiệu)', () => {
    expect(guardFiles.length).toBeGreaterThanOrEqual(30)
  })

  it('K7: 0 guard tính đường dẫn theo ĐỘ SÂU — phải lấy từ `src/test/paths.ts`', () => {
    const bad: string[] = []
    for (const p of guardFiles) {
      const text = readFileSync(resolve(SRC, p), 'utf8')
      const code = text
        .split('\n')
        .filter((l) => !/^\s*(\/\/|\*|\/\*)/.test(l))
        .join('\n')
      if (/resolve\(\s*HERE\b/.test(code)) bad.push(`${p} — resolve(HERE, …)`)
      if (/resolve\(\s*__dirname\s*,\s*'\.\./.test(code)) bad.push(`${p} — resolve(__dirname, '..')`)
      if (/dirname\(fileURLToPath\(import\.meta\.url\)\)\s*,\s*'\.\./.test(code)) {
        bad.push(`${p} — dirname(import.meta.url) + '..'`)
      }
      if (/process\.cwd\(\)/.test(code)) bad.push(`${p} — process.cwd() (đổi theo nơi gọi vitest)`)
    }
    expect(
      bad,
      'đường dẫn theo độ sâu gãy ÂM THẦM khi file bị dời: bộ quét trả 0 file và guard ' +
        'vẫn PASS. Dùng anchor từ `@/test/paths` (SPEC §5.2 N5).',
    ).toEqual([])
  })

  it('K8: guard nào QUÉT thư mục thì phải chốt dân số tối thiểu', () => {
    const bad: string[] = []
    for (const p of guardFiles) {
      const text = readFileSync(resolve(SRC, p), 'utf8')
      const scans = /readdirSync|import\.meta\s*(?:as\s+any\s*)?\)?\s*\.?\s*glob|\bglob\(/.test(text)
      if (!scans) continue
      // Dấu hiệu phải TƯỜNG MINH: hoặc dùng `listFiles(..., { min })` (paths.ts tự
      // ném lỗi khi hụt), hoặc đánh dấu `[K8] dân số:` ngay tại chỗ khoá. Không dò
      // `toBeGreaterThan(...)` chung chung — `toBeGreaterThan(-1)` là kiểm CHỈ SỐ,
      // không phải dân số, và đã từng làm 4 guard trông như đã khoá mà thực ra chưa.
      const locked = /listFiles\([^)]*min:\s*\d+/.test(text) || text.includes('[K8] dân số:')
      if (!locked) bad.push(p)
    }
    expect(
      bad,
      'quét thư mục mà không chốt dân số ⇒ thư mục bị dời thì đếm 0 và mọi khẳng định ' +
        '"không có vi phạm" thành đúng-rỗng-tuếch ⇒ XANH GIẢ (SPEC §5.2 N6).',
    ).toEqual([])
  })
})

// ── K9 ────────────────────────────────────────────────────────────────────────
describe('K9 — tên thư mục kebab-case · `.vue` PascalCase · `.ts` nguồn camelCase', () => {
  it('mọi thư mục trong src/ là kebab-case', () => {
    const bad: string[] = []
    const walk = (dir: string): void => {
      for (const e of readdirSync(dir, { withFileTypes: true })) {
        if (!e.isDirectory()) continue
        if (!/^[a-z0-9]+(-[a-z0-9]+)*$/.test(e.name)) bad.push(rel(resolve(dir, e.name)))
        walk(resolve(dir, e.name))
      }
    }
    walk(SRC)
    expect(bad, 'thư mục phải kebab-case (SPEC §5.2 N7)').toEqual([])
  })

  it('mọi `.vue` là PascalCase', () => {
    const bad = SOURCE_FILES.filter((p) => p.endsWith('.vue')).filter(
      (p) => !/^[A-Z][A-Za-z0-9]*\.vue$/.test(baseOf(p)),
    )
    expect(bad, 'component phải PascalCase').toEqual([])
  })

  it('mọi `.ts` nguồn là camelCase và KHÔNG có dấu chấm giữa tên (N4)', () => {
    const bad = SOURCE_FILES.filter((p) => p.endsWith('.ts') && !p.endsWith('.d.ts')).filter(
      (p) => !/^[a-z][A-Za-z0-9]*\.ts$/.test(baseOf(p)),
    )
    expect(
      bad,
      'file nguồn `.ts` phải camelCase, không dấu chấm (`messages.types.ts` ❌ → `messageTypes.ts` ✅). ' +
        'Chấm trong tên nguồn làm mờ ranh giới với quy ước `<Nguồn>.<khiaCanh>.test.ts`.',
    ).toEqual([])
  })
})
