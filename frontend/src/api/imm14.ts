// Copyright (c) 2026, AssetCore Team
// API client cho Module IMM-14 — Archive & Lifecycle Closure

import { frappeGet, frappePost } from './helpers'

export interface ArchiveDocumentEntry {
  idx: number
  document_type: string
  source_module: string
  document_name: string
  document_date: string | null
  archive_status: 'Included' | 'Missing' | 'Waived'
  notes: string
}

export interface AssetArchiveRecord {
  name: string
  asset: string
  asset_name: string
  decommission_request: string
  archive_date: string | null
  archived_by: string
  retention_years: number
  release_date: string | null
  storage_location: string
  status: 'Draft' | 'Compiling' | 'Pending Verification' | 'Pending Approval' | 'Finalized' | 'Archived'
  workflow_state: string
  total_documents_archived: number
  archive_notes: string
  reconcile_cmms: boolean
  reconcile_inventory: boolean
  reconcile_finance: boolean
  reconcile_legal: boolean
  reconciliation_notes: string
  qa_verified_by: string
  qa_verification_date: string | null
  qa_verification_notes: string
  approved_by: string
  approval_date: string | null
  approval_notes: string
  docstatus: number
  creation: string
  modified: string
  documents: ArchiveDocumentEntry[]
}

export interface ArchiveListResponse {
  rows: Array<Pick<AssetArchiveRecord,
    'name' | 'asset' | 'asset_name' | 'decommission_request' |
    'archive_date' | 'release_date' | 'status' | 'total_documents_archived' | 'modified'
  >>
  total: number
  page: number
  page_size: number
}

export interface ArchiveDashboard {
  archived_ytd: number
  pending_verification: number
  total_archived_all_time: number
}

export interface LifecycleTimelineEvent {
  date: string | null
  event_type: string
  module: string
  record: string
  actor: string
  notes: string
}

export interface LifecycleTimeline {
  asset: string
  asset_name: string
  asset_status: string
  timeline: LifecycleTimelineEvent[]
  total_events: number
}

export interface DocumentCompletenessCheck {
  ready: boolean
  issues: string[]
}

const BASE = '/api/method/assetcore.api.imm14'

export async function getArchiveRecord(name: string): Promise<AssetArchiveRecord> {
  return frappeGet<AssetArchiveRecord>(`${BASE}.get_archive_record`, { name })
}

export async function listArchiveRecords(
  status = '',
  asset = '',
  page = 1,
  pageSize = 20,
): Promise<ArchiveListResponse> {
  return frappeGet<ArchiveListResponse>(`${BASE}.list_archive_records`, {
    status,
    asset,
    page,
    page_size: pageSize,
  })
}

export async function getAssetFullHistory(assetName: string): Promise<LifecycleTimeline> {
  return frappeGet<LifecycleTimeline>(`${BASE}.get_asset_full_history`, { asset_name: assetName })
}

export async function getDashboardStats(): Promise<ArchiveDashboard> {
  return frappeGet<ArchiveDashboard>(`${BASE}.get_dashboard_stats`, {})
}

export async function createArchiveRecord(payload: {
  asset: string
  decommission_request?: string
  archive_date?: string
  storage_location?: string
  retention_years?: number
}): Promise<{ name: string; asset: string; status: string; release_date: string | null }> {
  return frappePost(`${BASE}.create_archive_record`, payload)
}

export async function addDocument(payload: {
  archive_name: string
  document_type: string
  document_name?: string
  document_date?: string
  archive_status?: string
}): Promise<{ archive_name: string; added: { document_type: string; document_name: string } }> {
  return frappePost(`${BASE}.add_document`, payload)
}

export async function compileAssetHistory(
  archiveName: string,
): Promise<{ compiled: number; breakdown: Record<string, number>; missing_count: number }> {
  return frappePost(`${BASE}.compile_asset_history`, { archive_name: archiveName })
}

export async function verifyArchiveRecord(payload: {
  name: string
  verified_by?: string
  notes?: string
}): Promise<{ name: string; status: string }> {
  return frappePost(`${BASE}.verify_archive_record`, payload)
}

export async function approveArchive(payload: {
  name: string
  approved_by?: string
  notes?: string
}): Promise<{ name: string; status: string }> {
  return frappePost(`${BASE}.approve_archive`, payload)
}

export async function finalizeArchive(name: string): Promise<{ name: string; status: string; asset: string }> {
  return frappePost(`${BASE}.finalize_archive`, { name })
}

export async function checkDocumentCompleteness(name: string): Promise<DocumentCompletenessCheck> {
  return frappeGet<DocumentCompletenessCheck>(`${BASE}.check_document_completeness`, { name })
}
