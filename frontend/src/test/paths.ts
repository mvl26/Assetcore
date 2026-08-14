// Copyright (c) 2026, AssetCore Team
// SSoT đường dẫn cho MỌI guard đọc đĩa của FE.
//
// ─── Vì sao có file này (đọc trước khi sửa) ───────────────────────────────────
// Class-of-bug đóng ở đây là **guard xanh giả**: một guard quét `src/views` bằng
// đường dẫn tính theo ĐỘ SÂU (`resolve(HERE, '../..')`). Khi file guard bị dời
// sâu thêm một cấp — hoặc khi thư mục bị quét đổi tên — đường dẫn trỏ vào chỗ
// không tồn tại, bộ quét đệ quy trả về **0 file**, mọi khẳng định dạng "không có
// vi phạm nào" thành đúng một cách rỗng tuếch, và suite vẫn **XANH** trong khi
// guard đã ngừng canh. Không có lỗi biên dịch nào bắt được chuyện này:
// `vue-tsc` chỉ phủ đồ thị import, còn lớp guard đọc VĂN BẢN mã nguồn thì nằm
// ngoài tầm compiler.
//
// Hai lớp phòng thủ ở file này:
//   1. `FRONTEND_ROOT` neo bằng cách **đi ngược lên tìm mốc** (`package.json` +
//      `vite.config.ts`), KHÔNG đếm số cấp `..`. File này có bị dời đi đâu thì
//      đường dẫn vẫn đúng.
//   2. `requireDir()` **ném lỗi ngay lúc import** nếu thư mục neo biến mất, và
//      `listFiles()` ném lỗi nếu quét ra ít file hơn ngưỡng. Thư mục dời đi ⇒
//      suite ĐỎ ầm ĩ, không bao giờ "đếm 0 rồi PASS".
//
// ─── Quy tắc bắt buộc (SPEC §5.2 N5/N6) ──────────────────────────────────────
//   • Mọi guard đọc đĩa PHẢI lấy đường dẫn từ file này. CẤM `resolve(HERE, '../..')`.
//   • Mọi guard quét thư mục PHẢI chốt dân số tối thiểu — dùng `listFiles(..., { min })`
//     hoặc `expect(files.length).toBeGreaterThanOrEqual(N)`.
import { existsSync, readdirSync, statSync } from 'node:fs'
import { dirname, join, relative, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

/** Đi ngược lên tìm gốc `frontend/` bằng MỐC, không bằng số cấp `..`. */
function findFrontendRoot(): string {
  let dir = dirname(fileURLToPath(import.meta.url))
  for (let i = 0; i < 12; i += 1) {
    if (existsSync(join(dir, 'package.json')) && existsSync(join(dir, 'vite.config.ts'))) {
      return dir
    }
    const parent = dirname(dir)
    if (parent === dir) break
    dir = parent
  }
  throw new Error(
    '[test/paths.ts] Không tìm thấy gốc `frontend/` (mốc: package.json + vite.config.ts). ' +
      'Cây thư mục đã đổi — sửa file này, ĐỪNG quay lại đường dẫn tính theo độ sâu.',
  )
}

/** Trả về `p` nếu là thư mục có thật; ném lỗi ầm ĩ nếu không — chống xanh giả. */
function requireDir(p: string, label: string): string {
  if (!existsSync(p) || !statSync(p).isDirectory()) {
    throw new Error(
      `[test/paths.ts] Thư mục neo ${label} không tồn tại: ${p}\n` +
        'Thư mục đã bị dời/đổi tên. Sửa paths.ts + guard liên quan. ' +
        'KHÔNG được để guard quét vào hư vô rồi báo PASS.',
    )
  }
  return p
}

export const FRONTEND_ROOT = findFrontendRoot()
/** Gốc app Frappe (`apps/assetcore/`) — cha của `frontend/`. */
export const REPO_ROOT = dirname(FRONTEND_ROOT)

export const SRC = requireDir(join(FRONTEND_ROOT, 'src'), 'SRC')
export const DOCS = requireDir(join(REPO_ROOT, 'docs'), 'DOCS')

export const API = requireDir(join(SRC, 'api'), 'API')
export const COMPONENTS = requireDir(join(SRC, 'components'), 'COMPONENTS')
export const COMPOSABLES = requireDir(join(SRC, 'composables'), 'COMPOSABLES')
export const CONSTANTS = requireDir(join(SRC, 'constants'), 'CONSTANTS')
export const LOCALES = requireDir(join(SRC, 'locales'), 'LOCALES')
export const ROUTER = requireDir(join(SRC, 'router'), 'ROUTER')
export const STORES = requireDir(join(SRC, 'stores'), 'STORES')
export const TYPES = requireDir(join(SRC, 'types'), 'TYPES')
export const UTILS = requireDir(join(SRC, 'utils'), 'UTILS')
export const VIEWS = requireDir(join(SRC, 'views'), 'VIEWS')

/** Nhà của guard đọc đĩa (dựng ở lô L2). */
export const GUARDS = requireDir(join(SRC, 'guards'), 'GUARDS')
/** Nhà của test tích hợp / khởi động / luồng chéo (dựng ở lô L3). */
export const INTEGRATION = requireDir(join(SRC, 'integration'), 'INTEGRATION')

/** Đường dẫn tương đối so với `src/` — dùng cho thông điệp lỗi đọc được. */
export function rel(absPath: string): string {
  return relative(SRC, absPath).split('\\').join('/')
}

/** Đường dẫn tương đối so với gốc app — dùng khi thông điệp vượt ra ngoài `frontend/`. */
export function relRepo(absPath: string): string {
  return relative(REPO_ROOT, absPath).split('\\').join('/')
}

export interface ListFilesOptions {
  /** Chỉ lấy file có phần mở rộng này (vd `.vue`, `.test.ts`). Bỏ trống = mọi file. */
  ext?: string | readonly string[]
  /**
   * Dân số TỐI THIỂU. Quét ra ít hơn ⇒ NÉM LỖI.
   * Đây là chốt chặn xanh giả — luôn truyền cho mọi lần quét thư mục.
   */
  min: number
  /** Mặc định true (đệ quy xuống thư mục con). */
  recursive?: boolean
  /** Bỏ qua file/thư mục khớp predicate. */
  skip?: (absPath: string) => boolean
}

/**
 * Quét thư mục và **chốt dân số tối thiểu**.
 *
 * Ném lỗi nếu `dir` không tồn tại hoặc số file quét được `< min`, thay vì trả
 * mảng rỗng — mảng rỗng là cách mọi khẳng định "không có vi phạm" trở thành
 * đúng-một-cách-rỗng-tuếch.
 */
export function listFiles(dir: string, opts: ListFilesOptions): string[] {
  const { ext, min, recursive = true, skip } = opts
  if (!existsSync(dir) || !statSync(dir).isDirectory()) {
    throw new Error(
      `[test/paths.ts] listFiles: thư mục không tồn tại: ${dir}\n` +
        'Guard đang trỏ vào hư vô — sửa đường dẫn, KHÔNG hạ ngưỡng min.',
    )
  }
  const exts = ext === undefined ? null : (Array.isArray(ext) ? ext : [ext as string])
  const out: string[] = []

  const walk = (current: string): void => {
    for (const entry of readdirSync(current, { withFileTypes: true })) {
      const abs = resolve(current, entry.name)
      if (skip?.(abs)) continue
      if (entry.isDirectory()) {
        if (recursive) walk(abs)
      } else if (!exts || exts.some((e) => entry.name.endsWith(e))) {
        out.push(abs)
      }
    }
  }
  walk(dir)
  out.sort()

  if (out.length < min) {
    throw new Error(
      `[test/paths.ts] listFiles(${relRepo(dir)}) chỉ ra ${out.length} file, ` +
        `dưới ngưỡng tối thiểu ${min}.\n` +
        'Thư mục đã bị dời/đổi tên/rỗng đi ⇒ guard đã NGỪNG CANH. ' +
        'Sửa đường dẫn hoặc cập nhật ngưỡng CÓ CHỦ Ý — đừng để guard đếm 0 rồi PASS.',
    )
  }
  return out
}
