// Copyright (c) 2026, AssetCore Team

export type RefDataDoctype =
  | 'AC Asset Category'
  | 'AC Department'
  | 'AC Location'
  | 'AC Supplier'
  | 'IMM Device Model'
  | 'Service Contract'
  | 'User'
  | 'AC Asset'
  | 'PM Checklist Template'

export interface ImportIssue {
  /** Thứ tự dòng dữ liệu (bỏ dòng trống) — dùng nội bộ để đối chiếu. */
  row: number
  /** Số hàng THẬT trong file người dùng — cái phải hiện ra màn hình. */
  sourceRow: number
  field: string
  /** Nhãn tiếng Việt của cột (BE trả); rỗng khi lỗi thuộc cả dòng. */
  label: string
  message: string
  severity: 'error' | 'warning'
}

export type ImportMode = 'strict' | 'skip_invalid'

/**
 * Một BẢN GHI CHA sẽ được tạo/cập nhật từ nhiều dòng của file phẳng (vd một mẫu
 * bảng kiểm gom nhiều hạng mục). Đếm dòng không nói lên điều người dùng cần
 * biết — họ điền 30 hàng và muốn biết ra mấy mẫu, mẫu nào đã có sẵn.
 */
export interface ImportGroupSummary {
  /** Khoá nhóm đã chuẩn hoá — dùng làm `key` khi render danh sách. */
  key: string
  /** Giá trị cột "tên" của bản ghi cha (lấy theo hàng đầu nhóm). */
  nameValue: string
  /** Số hàng trong file thuộc nhóm này. */
  rows: number
  /** Số dòng con sẽ nhập thật (đã trừ hàng lỗi). */
  items: number
  /** Số hàng thật trong file của hàng đầu nhóm — để người dùng mở đúng chỗ. */
  firstSourceRow: number
  exists: boolean
  /** Số dòng con bản ghi hiện có — cho biết cập nhật sẽ thay mất bao nhiêu. */
  existingItems: number
  action: 'create' | 'update' | 'blocked'
  /** Nhãn khoá đã dịch sang chữ người dùng đọc được (vd category, pmType). */
  category?: string
  pmType?: string
}

export interface ImportPreviewResult {
  doctype: RefDataDoctype
  totalRows: number
  validRows: number
  preview: Record<string, unknown>[]
  fieldnames: string[]
  /** fieldname → nhãn tiếng Việt, để bảng xem trước không hiện tên cột tiếng Anh. */
  fieldLabels: Record<string, string>
  errors: ImportIssue[]
  warnings: ImportIssue[]
  cascadeCount: number   // Tree DocType: rows skipped because parent is invalid
  /** Chỉ có với DocType cha + bảng con. Rỗng/absent với loại dữ liệu phẳng. */
  groups?: ImportGroupSummary[]
  groupsTotal?: number
  /** Loại dữ liệu phẳng: số dòng sẽ TẠO MỚI / sẽ CẬP NHẬT bản ghi đã có. */
  willCreate?: number
  willUpdate?: number
  /**
   * Số dòng trùng bản ghi đã có, ĐẾM CẢ KHI công tắc cập nhật đang tắt — nếu chỉ
   * nhìn `willUpdate` thì lúc tắt sẽ không bao giờ mời chào bật lên được.
   */
  existingRows?: number
}

export interface ImportSkippedRow {
  row: number
  sourceRow: number
  reason: 'pre_validate' | 'cascade_parent_skipped'
  field: string
  label: string
  message: string
}

export interface ImportResult {
  total: number
  success: number
  failed: number
  skipped: number
  errors: ImportIssue[]
  skippedRows: ImportSkippedRow[]
  /**
   * DocType nhập theo nhóm (cha + bảng con, vd mẫu bảng kiểm): số bản ghi CHA
   * đã tạo. `success` vẫn đếm theo DÒNG file nên nếu không có số này người dùng
   * đọc "12/12 dòng" mà không biết đã tạo mấy mẫu.
   */
  groupsCreated?: number
  /** Số bản ghi cha đã CẬP NHẬT (chỉ khi bật 'cập nhật bản ghi đã có'). */
  groupsUpdated?: number
  /** Loại dữ liệu phẳng: số bản ghi đã có được cập nhật (nằm trong `success`). */
  updated?: number
}

export interface ErrorReportResult {
  fileUrl: string
  errorCount: number
}

export type ImportStep = 'upload' | 'preview' | 'result'
