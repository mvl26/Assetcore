// Copyright (c) 2026, AssetCore Team
import { frappeGet, frappePost } from './helpers'
import type {
  RefDataDoctype,
  ImportPreviewResult,
  ImportResult,
  ImportMode,
  ImportSkippedRow,
  ErrorReportResult,
} from '@/types/import'

const BASE = '/api/method/assetcore.api.import_data'

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
    errors: { row: number; field: string; message: string; severity: string }[]
    warnings: { row: number; field: string; message: string; severity: string }[]
    cascade_count?: number
  }>(`${BASE}.preview_ref_data`, { doctype, file_url: fileUrl })

  return {
    doctype: raw.doctype as RefDataDoctype,
    totalRows: raw.total_rows,
    validRows: raw.valid_rows,
    preview: raw.preview,
    fieldnames: raw.fieldnames,
    errors: raw.errors as ImportPreviewResult['errors'],
    warnings: raw.warnings as ImportPreviewResult['warnings'],
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
    errors: { row: number; field: string; message: string; severity: string }[]
    skipped_rows?: { row: number; reason: string; field: string; message: string }[]
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
    errors: raw.errors as ImportResult['errors'],
    skippedRows: (raw.skipped_rows ?? []).map((r): ImportSkippedRow => ({
      row: r.row,
      reason: r.reason as ImportSkippedRow['reason'],
      field: r.field,
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
