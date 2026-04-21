// Copyright (c) 2026, AssetCore Team
// API calls cho Module IMM-05 — Asset Document Repository

import { frappeGet, frappePost } from './helpers'

const BASE = '/api/method/assetcore.api.imm05'

// ─────────────────────────────────────────────────────────────────────────────
// TYPES
// ─────────────────────────────────────────────────────────────────────────────

export interface Pagination {
  page: number
  page_size: number
  total: number
  total_pages: number
}

export interface AssetDocumentItem {
  name: string
  asset_ref: string
  asset_name?: string
  doc_category: string
  doc_type_detail: string
  doc_number: string
  version: string
  workflow_state: string
  expiry_date: string | null
  days_until_expiry: number | null
  visibility: 'Public' | 'Internal_Only'
  is_exempt: 0 | 1
  modified: string
}

export interface AssetDocumentDetail extends AssetDocumentItem {
  model_ref: string | null
  issued_date: string
  issuing_authority: string | null
  file_attachment: string
  approved_by: string | null
  approval_date: string | null
  rejection_reason: string | null
  change_summary: string | null
  is_expired: 0 | 1
  source_commissioning: string | null
  source_module: string | null
  exempt_reason: string | null
  exempt_proof: string | null
  notes: string | null
}

export interface DocumentFilters {
  doc_category?: string
  workflow_state?: string
  asset_ref?: string
  visibility?: string
  [key: string]: unknown
}

export interface DocumentRequest {
  name: string
  asset_ref: string
  doc_type_required: string
  doc_category: string
  assigned_to: string
  due_date: string
  status: 'Open' | 'In_Progress' | 'Overdue' | 'Fulfilled' | 'Cancelled'
  priority: 'Low' | 'Medium' | 'High' | 'Critical'
  escalation_sent: 0 | 1
  source_type: string
  fulfilled_by: string | null
}

export interface DashboardStats {
  kpis: {
    total_active: number
    expiring_90d: number
    expired_not_renewed: number
    assets_missing_docs: number
  }
  expiry_timeline: Array<{
    name: string
    asset_ref: string
    doc_type_detail: string
    expiry_date: string
    days_until_expiry: number
  }>
  compliance_by_dept: Array<{
    dept: string
    total_assets: number
    compliant: number
    pct: number
  }>
}

// ─────────────────────────────────────────────────────────────────────────────
// 1. LIST DOCUMENTS
// ─────────────────────────────────────────────────────────────────────────────

export function listDocuments(
  filters: DocumentFilters = {},
  page = 1,
  pageSize = 20,
) {
  return frappeGet<{ items: AssetDocumentItem[]; pagination: Pagination }>(
    `${BASE}.list_documents`,
    { filters: JSON.stringify(filters), page, page_size: pageSize },
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// 2. GET DOCUMENT
// ─────────────────────────────────────────────────────────────────────────────

export function getDocument(name: string) {
  return frappeGet<AssetDocumentDetail>(`${BASE}.get_document`, { name })
}

// ─────────────────────────────────────────────────────────────────────────────
// 3. CREATE DOCUMENT
// ─────────────────────────────────────────────────────────────────────────────

export function createDocument(docData: Partial<AssetDocumentDetail>) {
  return frappePost<{ name: string; workflow_state: string }>(
    `${BASE}.create_document`,
    { doc_data: JSON.stringify(docData) },
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// 4. UPDATE DOCUMENT
// ─────────────────────────────────────────────────────────────────────────────

export function updateDocument(name: string, docData: Partial<AssetDocumentDetail>) {
  return frappePost<{ name: string; modified: string }>(
    `${BASE}.update_document`,
    { name, doc_data: JSON.stringify(docData) },
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// 5. APPROVE / 6. REJECT
// ─────────────────────────────────────────────────────────────────────────────

export function approveDocument(name: string) {
  return frappePost<{ name: string; new_state: string }>(
    `${BASE}.approve_document`,
    { name },
  )
}

export function rejectDocument(name: string, rejectionReason: string) {
  return frappePost<{ name: string; new_state: string }>(
    `${BASE}.reject_document`,
    { name, rejection_reason: rejectionReason },
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// 7. GET ASSET DOCUMENTS (grouped)
// ─────────────────────────────────────────────────────────────────────────────

export function getAssetDocuments(asset: string) {
  return frappeGet<{
    asset: string
    completeness_pct: number
    document_status: string
    documents: Record<string, AssetDocumentItem[]>
    missing_required: string[]
  }>(`${BASE}.get_asset_documents`, { asset })
}

// ─────────────────────────────────────────────────────────────────────────────
// 8. DASHBOARD STATS
// ─────────────────────────────────────────────────────────────────────────────

export function getDashboardStats() {
  return frappeGet<DashboardStats>(`${BASE}.get_dashboard_stats`)
}

// ─────────────────────────────────────────────────────────────────────────────
// 9. EXPIRING DOCUMENTS
// ─────────────────────────────────────────────────────────────────────────────

export function getExpiringDocuments(days = 90) {
  return frappeGet<{ days: number; count: number; items: AssetDocumentItem[] }>(
    `${BASE}.get_expiring_documents`,
    { days },
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// 11. DOCUMENT HISTORY
// ─────────────────────────────────────────────────────────────────────────────

export function getDocumentHistory(name: string) {
  return frappeGet<{
    name: string
    history: Array<{
      timestamp: string
      user: string
      action: string
      from_state: string | null
      to_state: string | null
      changes: Array<{ field: string; old: unknown; new: unknown }>
    }>
  }>(`${BASE}.get_document_history`, { name })
}

// ─────────────────────────────────────────────────────────────────────────────
// 12. CREATE DOCUMENT REQUEST
// ─────────────────────────────────────────────────────────────────────────────

export function createDocumentRequest(payload: {
  asset_ref: string
  doc_type_required: string
  doc_category?: string
  assigned_to?: string
  due_date?: string
  priority?: string
  request_note?: string
  source_type?: string
}) {
  return frappePost<{ name: string; status: string }>(
    `${BASE}.create_document_request`,
    payload,
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// 13. GET DOCUMENT REQUESTS
// ─────────────────────────────────────────────────────────────────────────────

export function getDocumentRequests(assetRef = '', status = '') {
  return frappeGet<{ count: number; items: DocumentRequest[] }>(
    `${BASE}.get_document_requests`,
    { asset_ref: assetRef, status },
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// 14. MARK EXEMPT
// ─────────────────────────────────────────────────────────────────────────────

export function markExempt(payload: {
  asset_ref: string
  doc_type_detail: string
  exempt_reason: string
  exempt_proof: string
}) {
  return frappePost<{
    document_name: string
    is_exempt: boolean
    new_asset_document_status: string
  }>(`${BASE}.mark_exempt`, payload)
}
