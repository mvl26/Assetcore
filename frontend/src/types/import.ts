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
  row: number
  field: string
  message: string
  severity: 'error' | 'warning'
}

export interface ImportPreviewResult {
  doctype: RefDataDoctype
  totalRows: number
  validRows: number
  preview: Record<string, unknown>[]
  fieldnames: string[]
  errors: ImportIssue[]
  warnings: ImportIssue[]
}

export interface ImportResult {
  total: number
  success: number
  failed: number
  errors: ImportIssue[]
}

export interface ErrorReportResult {
  fileUrl: string
  errorCount: number
}

export type ImportStep = 'upload' | 'preview' | 'result'
