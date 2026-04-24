// Copyright (c) 2026, AssetCore Team
// API client cho IMM-00 — AC Asset foundation module

import { frappeGet, frappePost, type ApiResponse } from './helpers'
import type {
  AcAsset, AcAssetListItem, AcSupplier, AcLocation, AcDepartment,
  AcAssetCategory, ImmDeviceModel, ImmSlaPolicy, ImmAuditTrail,
  ImmCapaRecord, AssetLifecycleEvent, IncidentReport,
  AssetListParams, PaginatedResponse, AssetKpi, ChainVerifyResult,
} from '@/types/imm00'

const BASE = '/api/method/assetcore.api.imm00'

// ─── AC Asset ─────────────────────────────────────────────────────────────────

export async function listAssets(params: AssetListParams = {}): Promise<ApiResponse<PaginatedResponse<AcAssetListItem>>> {
  return frappeGet(`${BASE}.list_assets`, params as Record<string, unknown>)
}

export async function getAsset(name: string): Promise<ApiResponse<AcAsset>> {
  return frappeGet(`${BASE}.get_asset`, { name })
}

export async function createAsset(data: Partial<AcAsset>): Promise<ApiResponse<{ name: string }>> {
  return frappePost(`${BASE}.create_asset`, data as Record<string, unknown>)
}

export async function updateAsset(name: string, data: Partial<AcAsset>): Promise<ApiResponse<{ name: string }>> {
  return frappePost(`${BASE}.update_asset`, { name, ...data } as Record<string, unknown>)
}

export async function transitionStatus(name: string, to_status: string, reason = ''): Promise<ApiResponse<{ name: string; lifecycle_status: string }>> {
  return frappePost(`${BASE}.transition_status`, { name, to_status, reason })
}

export async function updateGmdnStatus(name: string, gmdn_status: string, reason: string): Promise<ApiResponse<{ name: string; gmdn_status: string; previous: string }>> {
  return frappePost(`${BASE}.update_gmdn_status`, { name, gmdn_status, reason })
}

export async function toggleGmdnStatus(name: string): Promise<ApiResponse<{ name: string; gmdn_status: string; previous: string }>> {
  return frappePost(`${BASE}.toggle_gmdn_status`, { name })
}

export async function getAssetTimeline(name: string, page = 1, page_size = 50): Promise<ApiResponse<PaginatedResponse<AssetLifecycleEvent>>> {
  return frappeGet(`${BASE}.get_asset_timeline`, { name, page, page_size })
}

export async function getAssetKpi(name: string): Promise<ApiResponse<AssetKpi>> {
  return frappeGet(`${BASE}.get_asset_kpi`, { name })
}

export async function validateForOperations(name: string): Promise<ApiResponse<{ valid: boolean; reason?: string }>> {
  return frappeGet(`${BASE}.validate_for_operations`, { name })
}

// ─── AC Supplier ──────────────────────────────────────────────────────────────

export async function listSuppliers(page = 1, page_size = 50, search = ''): Promise<ApiResponse<PaginatedResponse<AcSupplier>>> {
  return frappeGet(`${BASE}.list_suppliers`, { page, page_size, search })
}

// ─── Reference data ───────────────────────────────────────────────────────────

export async function listLocations(parent = ''): Promise<ApiResponse<AcLocation[]>> {
  return frappeGet(`${BASE}.list_locations`, { parent })
}

export async function listDepartments(parent = ''): Promise<ApiResponse<AcDepartment[]>> {
  return frappeGet(`${BASE}.list_departments`, { parent })
}

export async function listAssetCategories(): Promise<ApiResponse<AcAssetCategory[]>> {
  return frappeGet(`${BASE}.list_asset_categories`)
}

export async function listDeviceModels(page = 1, page_size = 50, search = ''): Promise<ApiResponse<PaginatedResponse<ImmDeviceModel>>> {
  return frappeGet(`${BASE}.list_device_models`, { page, page_size, search })
}

export async function listSlaPolicies(): Promise<ApiResponse<ImmSlaPolicy[]>> {
  return frappeGet(`${BASE}.list_sla_policies`)
}

// ─── IMM Audit Trail ──────────────────────────────────────────────────────────

export async function listAuditTrail(asset: string, page = 1, page_size = 50): Promise<ApiResponse<PaginatedResponse<ImmAuditTrail>>> {
  return frappeGet(`${BASE}.list_audit_trail`, { asset, page, page_size })
}

export async function verifyChain(asset: string): Promise<ApiResponse<ChainVerifyResult>> {
  return frappeGet(`${BASE}.verify_chain`, { asset })
}

// ─── IMM CAPA Record ──────────────────────────────────────────────────────────

export async function listCapas(params: { page?: number; page_size?: number; status?: string; asset?: string } = {}): Promise<ApiResponse<PaginatedResponse<ImmCapaRecord>>> {
  return frappeGet(`${BASE}.list_capas`, params as Record<string, unknown>)
}

export async function getCapaOverdue(page = 1, page_size = 20): Promise<ApiResponse<PaginatedResponse<ImmCapaRecord>>> {
  return frappeGet(`${BASE}.list_overdue_capas`, { page, page_size })
}

export async function openCapa(data: {
  asset: string; severity: string; description: string; responsible: string;
  source_type?: string; source_ref?: string; due_days?: number
}): Promise<ApiResponse<{ name: string }>> {
  return frappePost(`${BASE}.open_capa`, data as Record<string, unknown>)
}

// ─── Incident Report ──────────────────────────────────────────────────────────

export async function listIncidents(params: { page?: number; page_size?: number; status?: string; severity?: string; asset?: string } = {}): Promise<ApiResponse<PaginatedResponse<IncidentReport>>> {
  return frappeGet(`${BASE}.list_incidents`, params as Record<string, unknown>)
}

export async function createIncident(data: Partial<IncidentReport>): Promise<ApiResponse<{ name: string }>> {
  return frappePost(`${BASE}.create_incident`, data as Record<string, unknown>)
}

export async function getIncident(name: string): Promise<ApiResponse<IncidentReport>> {
  return frappeGet(`${BASE}.get_incident`, { name })
}

export async function updateIncident(name: string, data: Partial<IncidentReport>): Promise<ApiResponse<{ name: string }>> {
  return frappePost(`${BASE}.update_incident`, { name, ...data } as Record<string, unknown>)
}

export async function submitIncident(name: string): Promise<ApiResponse<{ name: string; docstatus: number }>> {
  return frappePost(`${BASE}.submit_incident`, { name })
}

export async function deleteIncident(name: string): Promise<ApiResponse<{ name: string; deleted: boolean }>> {
  return frappePost(`${BASE}.delete_incident`, { name })
}

// ─── AC Supplier CRUD ────────────────────────────────────────────────────────

export async function getSupplier(name: string): Promise<ApiResponse<AcSupplier>> {
  return frappeGet(`${BASE}.get_supplier`, { name })
}

export async function createSupplier(data: Partial<AcSupplier>): Promise<ApiResponse<{ name: string }>> {
  return frappePost(`${BASE}.create_supplier`, data as Record<string, unknown>)
}

export async function updateSupplier(name: string, data: Partial<AcSupplier>): Promise<ApiResponse<{ name: string }>> {
  return frappePost(`${BASE}.update_supplier`, { name, ...data } as Record<string, unknown>)
}

export async function deleteSupplier(name: string): Promise<ApiResponse<{ name: string; deleted: boolean }>> {
  return frappePost(`${BASE}.delete_supplier`, { name })
}

// ─── IMM Device Model CRUD ───────────────────────────────────────────────────

export async function getDeviceModel(name: string): Promise<ApiResponse<ImmDeviceModel>> {
  return frappeGet(`${BASE}.get_device_model`, { name })
}

export async function createDeviceModel(data: Partial<ImmDeviceModel>): Promise<ApiResponse<{ name: string }>> {
  return frappePost(`${BASE}.create_device_model`, data as Record<string, unknown>)
}

export async function updateDeviceModel(name: string, data: Partial<ImmDeviceModel>): Promise<ApiResponse<{ name: string }>> {
  return frappePost(`${BASE}.update_device_model`, { name, ...data } as Record<string, unknown>)
}

export async function deleteDeviceModel(name: string): Promise<ApiResponse<{ name: string; deleted: boolean }>> {
  return frappePost(`${BASE}.delete_device_model`, { name })
}

// ─── AC Location / Department / Category CRUD ───────────────────────────────

export async function getLocation(name: string): Promise<ApiResponse<AcLocation>> {
  return frappeGet(`${BASE}.get_location`, { name })
}

export async function getDepartment(name: string): Promise<ApiResponse<AcDepartment>> {
  return frappeGet(`${BASE}.get_department`, { name })
}

export async function getAssetCategory(name: string): Promise<ApiResponse<AcAssetCategory>> {
  return frappeGet(`${BASE}.get_asset_category`, { name })
}

export async function createLocation(data: Partial<AcLocation>): Promise<ApiResponse<{ name: string }>> {
  return frappePost(`${BASE}.create_location`, data as Record<string, unknown>)
}

export async function updateLocation(name: string, data: Partial<AcLocation>): Promise<ApiResponse<{ name: string }>> {
  return frappePost(`${BASE}.update_location`, { name, ...data } as Record<string, unknown>)
}

export async function deleteLocation(name: string): Promise<ApiResponse<{ name: string; deleted: boolean }>> {
  return frappePost(`${BASE}.delete_location`, { name })
}

export async function createDepartment(data: Partial<AcDepartment>): Promise<ApiResponse<{ name: string }>> {
  return frappePost(`${BASE}.create_department`, data as Record<string, unknown>)
}

export async function updateDepartment(name: string, data: Partial<AcDepartment>): Promise<ApiResponse<{ name: string }>> {
  return frappePost(`${BASE}.update_department`, { name, ...data } as Record<string, unknown>)
}

export async function deleteDepartment(name: string): Promise<ApiResponse<{ name: string; deleted: boolean }>> {
  return frappePost(`${BASE}.delete_department`, { name })
}

export async function createAssetCategory(data: Partial<AcAssetCategory>): Promise<ApiResponse<{ name: string }>> {
  return frappePost(`${BASE}.create_asset_category`, data as Record<string, unknown>)
}

export async function updateAssetCategory(name: string, data: Partial<AcAssetCategory>): Promise<ApiResponse<{ name: string }>> {
  return frappePost(`${BASE}.update_asset_category`, { name, ...data } as Record<string, unknown>)
}

export async function deleteAssetCategory(name: string): Promise<ApiResponse<{ name: string; deleted: boolean }>> {
  return frappePost(`${BASE}.delete_asset_category`, { name })
}

// ─── IMM SLA Policy CRUD ─────────────────────────────────────────────────────

export async function getSlaPolicy(name: string): Promise<ApiResponse<ImmSlaPolicy>> {
  return frappeGet(`${BASE}.get_sla_policy`, { name })
}

export async function createSlaPolicy(data: Partial<ImmSlaPolicy>): Promise<ApiResponse<{ name: string }>> {
  return frappePost(`${BASE}.create_sla_policy`, data as Record<string, unknown>)
}

export async function updateSlaPolicy(name: string, data: Partial<ImmSlaPolicy>): Promise<ApiResponse<{ name: string }>> {
  return frappePost(`${BASE}.update_sla_policy`, { name, ...data } as Record<string, unknown>)
}

export async function deleteSlaPolicy(name: string): Promise<ApiResponse<{ name: string; deleted: boolean }>> {
  return frappePost(`${BASE}.delete_sla_policy`, { name })
}

// ─── AC Asset delete ─────────────────────────────────────────────────────────

export async function deleteAsset(name: string): Promise<ApiResponse<{ name: string; deleted: boolean }>> {
  return frappePost(`${BASE}.delete_asset`, { name })
}

// ─── Depreciation ────────────────────────────────────────────────────────────

export interface DepreciationResult {
  accumulated: number
  book_value: number
  method?: string
  days_elapsed?: number
  note?: string
}

export async function computeDepreciation(name: string): Promise<ApiResponse<DepreciationResult>> {
  return frappePost(`${BASE}.compute_depreciation`, { name })
}

// ─── Asset Transfer CRUD ─────────────────────────────────────────────────────

export async function getTransferFull(name: string): Promise<ApiResponse<Record<string, unknown>>> {
  return frappeGet(`${BASE}.get_transfer_full`, { name })
}

export async function updateTransfer(name: string, data: Record<string, unknown>): Promise<ApiResponse<{ name: string }>> {
  return frappePost(`${BASE}.update_transfer`, { name, ...data })
}

export async function approveTransfer(name: string): Promise<ApiResponse<{ name: string; approved_by: string }>> {
  return frappePost(`${BASE}.approve_transfer`, { name })
}

// ─── PM Schedule CRUD ────────────────────────────────────────────────────────

export interface PmSchedule {
  name: string
  asset_ref: string
  asset_name?: string
  pm_type?: string
  status?: string
  pm_interval_days?: number
  checklist_template?: string
  responsible_technician?: string
  last_pm_date?: string
  next_due_date?: string
  alert_days_before?: number
  notes?: string
}

export async function listPmSchedules(params: { page?: number; page_size?: number; asset?: string; status?: string } = {}): Promise<ApiResponse<{ items: PmSchedule[]; total: number }>> {
  return frappeGet(`${BASE}.list_pm_schedules`, params as Record<string, unknown>)
}

export async function getPmSchedule(name: string): Promise<ApiResponse<PmSchedule>> {
  return frappeGet(`${BASE}.get_pm_schedule`, { name })
}

export async function createPmSchedule(data: Partial<PmSchedule>): Promise<ApiResponse<{ name: string }>> {
  return frappePost(`${BASE}.create_pm_schedule`, data as Record<string, unknown>)
}

export async function updatePmSchedule(name: string, data: Partial<PmSchedule>): Promise<ApiResponse<{ name: string }>> {
  return frappePost(`${BASE}.update_pm_schedule`, { name, ...data } as Record<string, unknown>)
}

export async function deletePmSchedule(name: string): Promise<ApiResponse<{ name: string; deleted: boolean }>> {
  return frappePost(`${BASE}.delete_pm_schedule`, { name })
}

// ─── PM Checklist Template CRUD ──────────────────────────────────────────────

export interface PmChecklistItem {
  description: string
  measurement_type?: 'Pass/Fail' | 'Numeric' | 'Text'
  unit?: string
  expected_min?: number | null
  expected_max?: number | null
  is_critical?: 0 | 1 | boolean
  reference_section?: string
}

export interface PmTemplate {
  name: string
  template_name: string
  asset_category?: string
  pm_type?: string
  version?: string
  effective_date?: string
  approved_by?: string
  checklist_items?: PmChecklistItem[]
}

// Endpoints are served by assetcore.api.imm08 (service-based — handles checklist_items JSON)
const _PM_TPL_BASE = '/api/method/assetcore.api.imm08'

export async function listPmTemplates(page = 1, page_size = 50): Promise<ApiResponse<{ data: PmTemplate[]; pagination: { total: number; page: number; page_size: number } }>> {
  return frappeGet(`${_PM_TPL_BASE}.list_pm_templates`, { page, page_size })
}

export async function getPmTemplate(name: string): Promise<ApiResponse<PmTemplate>> {
  return frappeGet(`${_PM_TPL_BASE}.get_pm_template`, { name })
}

export async function createPmTemplate(data: Partial<PmTemplate>): Promise<ApiResponse<{ name: string }>> {
  return frappePost(`${_PM_TPL_BASE}.create_pm_template`, data as Record<string, unknown>)
}

export async function updatePmTemplate(name: string, data: Partial<PmTemplate>): Promise<ApiResponse<{ name: string }>> {
  return frappePost(`${_PM_TPL_BASE}.update_pm_template`, { name, ...data } as Record<string, unknown>)
}

export async function deletePmTemplate(name: string): Promise<ApiResponse<{ name: string; deleted: boolean }>> {
  return frappePost(`${_PM_TPL_BASE}.delete_pm_template`, { name })
}

// ─── Firmware Change Request CRUD ────────────────────────────────────────────

export interface FirmwareCR {
  name: string
  asset_ref: string
  asset_name?: string
  asset_repair_wo?: string
  version_before?: string
  version_after?: string
  change_notes?: string
  source_reference?: string
  status?: string
  approved_by?: string
  approved_datetime?: string
  applied_datetime?: string
  rollback_reason?: string
}

export async function listFirmwareCrs(params: { page?: number; page_size?: number; status?: string; asset?: string } = {}): Promise<ApiResponse<{ items: FirmwareCR[]; total: number }>> {
  return frappeGet(`${BASE}.list_firmware_crs`, params as Record<string, unknown>)
}

export async function getFirmwareCr(name: string): Promise<ApiResponse<FirmwareCR>> {
  return frappeGet(`${BASE}.get_firmware_cr`, { name })
}

export async function createFirmwareCr(data: Partial<FirmwareCR>): Promise<ApiResponse<{ name: string }>> {
  return frappePost(`${BASE}.create_firmware_cr`, data as Record<string, unknown>)
}

export async function updateFirmwareCr(name: string, data: Partial<FirmwareCR>): Promise<ApiResponse<{ name: string }>> {
  return frappePost(`${BASE}.update_firmware_cr`, { name, ...data } as Record<string, unknown>)
}

export async function deleteFirmwareCr(name: string): Promise<ApiResponse<{ name: string; deleted: boolean }>> {
  return frappePost(`${BASE}.delete_firmware_cr`, { name })
}

// ─── Document Request CRUD ───────────────────────────────────────────────────

export interface DocumentRequest {
  name: string
  asset_ref: string
  asset_name?: string
  doc_type_required: string
  doc_category?: string
  status?: string
  priority?: string
  assigned_to?: string
  due_date?: string
  source_type?: string
  request_note?: string
  fulfilled_by?: string
}

export async function listDocumentRequests(params: { page?: number; page_size?: number; status?: string; asset?: string } = {}): Promise<ApiResponse<{ items: DocumentRequest[]; total: number }>> {
  return frappeGet(`${BASE}.list_document_requests`, params as Record<string, unknown>)
}

export async function getDocumentRequest(name: string): Promise<ApiResponse<DocumentRequest>> {
  return frappeGet(`${BASE}.get_document_request`, { name })
}

export async function createDocumentRequest(data: Partial<DocumentRequest>): Promise<ApiResponse<{ name: string }>> {
  return frappePost(`${BASE}.create_document_request`, data as Record<string, unknown>)
}

export async function updateDocumentRequest(name: string, data: Partial<DocumentRequest>): Promise<ApiResponse<{ name: string }>> {
  return frappePost(`${BASE}.update_document_request`, { name, ...data } as Record<string, unknown>)
}

export async function deleteDocumentRequest(name: string): Promise<ApiResponse<{ name: string; deleted: boolean }>> {
  return frappePost(`${BASE}.delete_document_request`, { name })
}

// ─── Depreciation Schedule (Phase 2) ─────────────────────────────────────────

export interface DepreciationScheduleRow {
  name: string
  period_number: number
  scheduled_date: string
  depreciation_amount: number
  accumulated_amount: number
  remaining_value: number
  status: 'Pending' | 'Executed' | 'Cancelled'
  executed_on?: string
  journal_entry?: string
}

export interface DepreciationScheduleResponse {
  asset: string
  asset_info: {
    gross_purchase_amount?: number
    residual_value?: number
    accumulated_depreciation?: number
    current_book_value?: number
    depreciation_method?: string
    total_depreciation_months?: number
    depreciation_frequency?: string
    depreciation_start_date?: string
    in_service_date?: string
  }
  rows: DepreciationScheduleRow[]
  summary: {
    total_periods: number
    executed_periods: number
    pending_periods: number
    total_depreciated: number
  }
}

export async function getDepreciationSchedule(asset_name: string) {
  return frappeGet<DepreciationScheduleResponse>(
    `${BASE}.get_depreciation_schedule`, { asset_name },
  )
}

export async function regenerateDepreciationSchedule(asset_name: string, force: 0 | 1 = 1) {
  return frappePost<{ asset: string; periods: number; total_depreciable?: number; skipped?: boolean; reason?: string }>(
    `${BASE}.regenerate_depreciation_schedule`, { asset_name, force },
  )
}

export interface DepreciationPreviewRow {
  period_number: number
  scheduled_date: string
  depreciation_amount: number
  accumulated_amount: number
  remaining_value: number
}

export async function previewDepreciationSchedule(params: {
  gross: number
  residual: number
  method: string
  total_months: number
  frequency: string
  start_date: string
}) {
  return frappeGet<DepreciationPreviewRow[]>(
    `${BASE}.preview_depreciation_schedule`, params as unknown as Record<string, unknown>,
  )
}

export async function runDueDepreciationNow(as_of?: string) {
  return frappePost<{ executed_rows: number; updated_assets: number }>(
    `${BASE}.run_due_depreciation_now`, { as_of: as_of || '' },
  )
}

export async function bulkRegenerateScheduleByCategory(category_name: string) {
  return frappePost<{
    category: string; total_assets: number; regenerated: number;
    skipped_has_history: number; errors: number
  }>(`${BASE}.bulk_regenerate_schedule_by_category`, { category_name })
}
