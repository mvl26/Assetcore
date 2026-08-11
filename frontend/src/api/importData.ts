// Copyright (c) 2026, AssetCore Team
import { frappeGet, frappePost } from './helpers'
import type {
  RefDataDoctype,
  ImportIssue,
  ImportPreviewResult,
  ImportResult,
  ImportMode,
  ImportSkippedRow,
  ErrorReportResult,
} from '@/types/import'

const BASE = '/api/method/assetcore.api.import_data'

/** Dạng lỗi thô từ BE — snake_case, `source_row`/`label` có thể vắng (BE cũ). */
interface RawIssue {
  row: number
  source_row?: number
  field: string
  label?: string
  message: string
  severity: string
}

/**
 * BE đánh số theo dòng dữ liệu (bỏ dòng trống); người dùng chỉ biết số hàng in
 * ở lề trái Excel. `source_row` là số hàng thật — thiếu thì suy ra theo layout
 * template (5 hàng khung ở đầu file) để không bao giờ hiện "Dòng 1" cho hàng 6.
 */
const HEADER_ROWS = 5

function toIssue(r: RawIssue): ImportIssue {
  return {
    row: r.row,
    sourceRow: r.source_row ?? r.row + HEADER_ROWS,
    field: r.field,
    label: r.label || r.field,
    message: r.message,
    severity: r.severity as ImportIssue['severity'],
  }
}

export async function previewRefImport(
  doctype: RefDataDoctype,
  fileUrl: string,
): Promise<ImportPreviewResult> {
  const raw = await frappePost<{
    doctype: string
    total_rows: number
    valid_rows: number
    preview: Record<string, unknown>[]
    fieldnames: string[]
    field_labels?: Record<string, string>
    errors: RawIssue[]
    warnings: RawIssue[]
    cascade_count?: number
  }>(`${BASE}.preview_ref_data`, { doctype, file_url: fileUrl })

  return {
    doctype: raw.doctype as RefDataDoctype,
    totalRows: raw.total_rows,
    validRows: raw.valid_rows,
    preview: raw.preview,
    fieldnames: raw.fieldnames,
    fieldLabels: raw.field_labels ?? {},
    errors: (raw.errors ?? []).map(toIssue),
    warnings: (raw.warnings ?? []).map(toIssue),
    cascadeCount: raw.cascade_count ?? 0,
  }
}

export async function importRefData(
  doctype: RefDataDoctype,
  fileUrl: string,
  mode: ImportMode = 'strict',
): Promise<ImportResult> {
  const raw = await frappePost<{
    total: number
    success: number
    failed: number
    skipped?: number
    errors: RawIssue[]
    skipped_rows?: (RawIssue & { reason: string })[]
  }>(`${BASE}.import_ref_data`, {
    doctype,
    file_url: fileUrl,
    skip_invalid: mode === 'skip_invalid',
  })

  return {
    total: raw.total,
    success: raw.success,
    failed: raw.failed,
    skipped: raw.skipped ?? 0,
    errors: (raw.errors ?? []).map(toIssue),
    skippedRows: (raw.skipped_rows ?? []).map((r): ImportSkippedRow => ({
      row: r.row,
      sourceRow: r.source_row ?? r.row + HEADER_ROWS,
      reason: r.reason as ImportSkippedRow['reason'],
      field: r.field,
      label: r.label || r.field,
      message: r.message,
    })),
  }
}

export async function buildErrorReport(
  doctype: RefDataDoctype,
  fileUrl: string,
): Promise<ErrorReportResult> {
  const raw = await frappePost<{ file_url: string; error_count: number }>(
    `${BASE}.build_error_report`,
    { doctype, file_url: fileUrl },
  )
  return { fileUrl: raw.file_url, errorCount: raw.error_count }
}

export function getExportUrl(doctype: RefDataDoctype): string {
  return `${BASE}.export_ref_data?doctype=${encodeURIComponent(doctype)}`
}

export function getTemplateUrl(doctype: RefDataDoctype): string {
  return `${BASE}.download_template?doctype=${encodeURIComponent(doctype)}`
}

export async function initImportFolders(doctype: RefDataDoctype): Promise<string> {
  const raw = await frappeGet<{ folder: string }>(
    `${BASE}.init_import_folders`,
    { doctype },
  )
  return raw.folder
}
