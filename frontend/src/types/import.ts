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
}

export interface ErrorReportResult {
  fileUrl: string
  errorCount: number
}

export type ImportStep = 'upload' | 'preview' | 'result'
