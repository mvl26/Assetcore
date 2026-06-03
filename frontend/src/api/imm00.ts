// Copyright (c) 2026, AssetCore Team
// API client cho IMM-00 — AC Asset foundation module
//
// NOTE: frappeGet/frappePost đã unwrap Frappe envelope ({ message: { success, data } })
// và throw ApiError khi success === false. Các hàm ở đây trả thẳng kiểu dữ liệu T,
// KHÔNG wrap thêm ApiResponse<T>.

import { frappeGet, frappePost } from './helpers'
import type {
  AcAsset, AcAssetListItem, AcSupplier, AcLocation, AcDepartment,
  AcAssetCategory, ImmDeviceModel, ImmSlaPolicy, ImmAuditTrail,
  ImmCapaRecord, AssetLifecycleEvent, IncidentReport,
  AssetListParams, PaginatedResponse, AssetKpi, ChainVerifyResult,
} from '@/types/imm00'

const BASE = '/api/method/assetcore.api.imm00'

// ─── AC Asset ─────────────────────────────────────────────────────────────────

export function listAssets(params: AssetListParams = {}): Promise<PaginatedResponse<AcAssetListItem>> {
  return frappeGet(`${BASE}.list_assets`, params as Record<string, unknown>)
}

export function getAsset(name: string): Promise<AcAsset> {
  return frappeGet(`${BASE}.get_asset`, { name })
}

export function createAsset(data: Partial<AcAsset>): Promise<{ name: string }> {
  return frappePost(`${BASE}.create_asset`, data as Record<string, unknown>)
}

export function updateAsset(name: string, data: Partial<AcAsset>): Promise<{ name: string }> {
  return frappePost(`${BASE}.update_asset`, { name, ...data } as Record<string, unknown>)
}

export function transitionStatus(name: string, to_status: string, reason = ''): Promise<{ name: string; lifecycle_status: string }> {
  return frappePost(`${BASE}.transition_status`, { name, to_status, reason })
}

export function getAssetTimeline(name: string, page = 1, page_size = 50): Promise<PaginatedResponse<AssetLifecycleEvent>> {
  return frappeGet(`${BASE}.get_asset_timeline`, { name, page, page_size })
}

export function getAssetKpi(name: string): Promise<AssetKpi> {
  return frappeGet(`${BASE}.get_asset_kpi`, { name })
}

export function validateForOperations(name: string): Promise<{ valid: boolean; reason?: string }> {
  return frappeGet(`${BASE}.validate_for_operations`, { name })
}

// ─── AC Supplier ──────────────────────────────────────────────────────────────

export function listSuppliers(page = 1, page_size = 50, search = ''): Promise<PaginatedResponse<AcSupplier>> {
  return frappeGet(`${BASE}.list_suppliers`, { page, page_size, search })
}

// ─── Reference data ───────────────────────────────────────────────────────────

export function listLocations(parent = ''): Promise<AcLocation[]> {
  return frappeGet(`${BASE}.list_locations`, { parent })
}

export function listDepartments(parent = ''): Promise<AcDepartment[]> {
  return frappeGet(`${BASE}.list_departments`, { parent })
}

export function listAssetCategories(): Promise<AcAssetCategory[]> {
  return frappeGet(`${BASE}.list_asset_categories`)
}

export function listDeviceModels(page = 1, page_size = 50, search = ''): Promise<PaginatedResponse<ImmDeviceModel>> {
  return frappeGet(`${BASE}.list_device_models`, { page, page_size, search })
}

export function listSlaPolicies(): Promise<ImmSlaPolicy[]> {
  return frappeGet(`${BASE}.list_sla_policies`)
}

// ─── IMM Audit Trail ──────────────────────────────────────────────────────────

export function listAuditTrail(asset: string, page = 1, page_size = 50): Promise<PaginatedResponse<ImmAuditTrail>> {
  return frappeGet(`${BASE}.list_audit_trail`, { asset, page, page_size })
}

export function verifyChain(asset: string): Promise<ChainVerifyResult> {
  return frappeGet(`${BASE}.verify_chain`, { asset })
}

// ─── IMM CAPA Record ──────────────────────────────────────────────────────────

export function listCapas(params: { page?: number; page_size?: number; status?: string; asset?: string; not_closed?: number; overdue?: number } = {}): Promise<PaginatedResponse<ImmCapaRecord>> {
  return frappeGet(`${BASE}.list_capas`, params as Record<string, unknown>)
}

export function getCapaOverdue(page = 1, page_size = 20): Promise<PaginatedResponse<ImmCapaRecord>> {
  return frappeGet(`${BASE}.list_overdue_capas`, { page, page_size })
}

export function openCapa(data: {
  asset: string; severity: string; description: string; responsible: string;
  source_type?: string; source_ref?: string; due_days?: number
}): Promise<{ name: string }> {
  return frappePost(`${BASE}.open_capa`, data as Record<string, unknown>)
}

export function getCapa(name: string): Promise<ImmCapaRecord> {
  return frappeGet(`${BASE}.get_capa`, { name })
}

export function closeCapaRecord(name: string, data: {
  root_cause: string
  corrective_action: string
  preventive_action: string
  effectiveness_check?: string
}): Promise<void> {
  return frappePost(`${BASE}.close_capa_record`, { name, ...data })
}

// ─── Incident Report ──────────────────────────────────────────────────────────

export function listIncidents(params: { page?: number; page_size?: number; status?: string; severity?: string; asset?: string } = {}): Promise<PaginatedResponse<IncidentReport>> {
  return frappeGet(`${BASE}.list_incidents`, params as Record<string, unknown>)
}

export function createIncident(data: Partial<IncidentReport>): Promise<{ name: string }> {
  return frappePost(`${BASE}.create_incident`, data as Record<string, unknown>)
}

export function getIncident(name: string): Promise<IncidentReport> {
  return frappeGet(`${BASE}.get_incident`, { name })
}

export function updateIncident(name: string, data: Partial<IncidentReport>): Promise<{ name: string }> {
  return frappePost(`${BASE}.update_incident`, { name, ...data } as Record<string, unknown>)
}

export function submitIncident(name: string): Promise<{ name: string; docstatus: number }> {
  return frappePost(`${BASE}.submit_incident`, { name })
}

export function deleteIncident(name: string): Promise<{ name: string; deleted: boolean }> {
  return frappePost(`${BASE}.delete_incident`, { name })
}

// ─── AC Supplier CRUD ────────────────────────────────────────────────────────

export function getSupplier(name: string): Promise<AcSupplier> {
  return frappeGet(`${BASE}.get_supplier`, { name })
}

export function createSupplier(data: Partial<AcSupplier>): Promise<{ name: string }> {
  return frappePost(`${BASE}.create_supplier`, data as Record<string, unknown>)
}

export function updateSupplier(name: string, data: Partial<AcSupplier>): Promise<{ name: string }> {
  return frappePost(`${BASE}.update_supplier`, { name, ...data } as Record<string, unknown>)
}

export function deleteSupplier(name: string): Promise<{ name: string; deleted: boolean }> {
  return frappePost(`${BASE}.delete_supplier`, { name })
}

// ─── IMM Device Model CRUD ───────────────────────────────────────────────────

export function getDeviceModel(name: string): Promise<ImmDeviceModel> {
  return frappeGet(`${BASE}.get_device_model`, { name })
}

export function createDeviceModel(data: Partial<ImmDeviceModel>): Promise<{ name: string }> {
  return frappePost(`${BASE}.create_device_model`, data as Record<string, unknown>)
}

export function updateDeviceModel(name: string, data: Partial<ImmDeviceModel>): Promise<{ name: string }> {
  return frappePost(`${BASE}.update_device_model`, { name, ...data } as Record<string, unknown>)
}

export function deleteDeviceModel(name: string): Promise<{ name: string; deleted: boolean }> {
  return frappePost(`${BASE}.delete_device_model`, { name })
}

// ─── AC Location / Department / Category CRUD ───────────────────────────────

export function getLocation(name: string): Promise<AcLocation> {
  return frappeGet(`${BASE}.get_location`, { name })
}

export function getDepartment(name: string): Promise<AcDepartment> {
  return frappeGet(`${BASE}.get_department`, { name })
}

export function getAssetCategory(name: string): Promise<AcAssetCategory> {
  return frappeGet(`${BASE}.get_asset_category`, { name })
}

export function createLocation(data: Partial<AcLocation>): Promise<{ name: string }> {
  return frappePost(`${BASE}.create_location`, data as Record<string, unknown>)
}

export function updateLocation(name: string, data: Partial<AcLocation>): Promise<{ name: string }> {
  return frappePost(`${BASE}.update_location`, { name, ...data } as Record<string, unknown>)
}

export function deleteLocation(name: string): Promise<{ name: string; deleted: boolean }> {
  return frappePost(`${BASE}.delete_location`, { name })
}

export function createDepartment(data: Partial<AcDepartment>): Promise<{ name: string }> {
  return frappePost(`${BASE}.create_department`, data as Record<string, unknown>)
}

export function updateDepartment(name: string, data: Partial<AcDepartment>): Promise<{ name: string }> {
  return frappePost(`${BASE}.update_department`, { name, ...data } as Record<string, unknown>)
}

export function deleteDepartment(name: string): Promise<{ name: string; deleted: boolean }> {
  return frappePost(`${BASE}.delete_department`, { name })
}

export function createAssetCategory(data: Partial<AcAssetCategory>): Promise<{ name: string }> {
  return frappePost(`${BASE}.create_asset_category`, data as Record<string, unknown>)
}

export function updateAssetCategory(name: string, data: Partial<AcAssetCategory>): Promise<{ name: string }> {
  return frappePost(`${BASE}.update_asset_category`, { name, ...data } as Record<string, unknown>)
}

export function deleteAssetCategory(name: string): Promise<{ name: string; deleted: boolean }> {
  return frappePost(`${BASE}.delete_asset_category`, { name })
}

// ─── IMM SLA Policy CRUD ─────────────────────────────────────────────────────

export function getSlaPolicy(name: string): Promise<ImmSlaPolicy> {
  return frappeGet(`${BASE}.get_sla_policy`, { name })
}

export function createSlaPolicy(data: Partial<ImmSlaPolicy>): Promise<{ name: string }> {
  return frappePost(`${BASE}.create_sla_policy`, data as Record<string, unknown>)
}

export function updateSlaPolicy(name: string, data: Partial<ImmSlaPolicy>): Promise<{ name: string }> {
  return frappePost(`${BASE}.update_sla_policy`, { name, ...data } as Record<string, unknown>)
}

export function deleteSlaPolicy(name: string): Promise<{ name: string; deleted: boolean }> {
  return frappePost(`${BASE}.delete_sla_policy`, { name })
}

// ─── AC Asset delete ─────────────────────────────────────────────────────────

export function deleteAsset(name: string): Promise<{ name: string; deleted: boolean }> {
  return frappePost(`${BASE}.delete_asset`, { name })
}

// ─── Depreciation: List + Stats (Asset Finance Hub) ─────────────────────────

export interface AssetDepreciationRow {
  name: string
  asset_name: string
  asset_category?: string
  department?: string
  location?: string
  purchase_date?: string
  in_service_date?: string
  depreciation_start_date?: string
  gross_purchase_amount?: number
  residual_value?: number
  depreciation_method?: string
  total_depreciation_months?: number
  depreciation_frequency?: string
  accumulated_depreciation?: number
  current_book_value?: number
  lifecycle_status?: string
  configured: boolean
  pct_depreciated: number
  executed_periods: number
  total_periods: number
}

export interface DepreciationStats {
  total_assets: number
  configured_count: number
  unconfigured_count: number
  fully_depreciated: number
  total_gross: number
  total_accumulated: number
  total_book_value: number
  overall_pct: number
  by_method: { method: string; count: number }[]
  by_category: { category: string; book_value: number }[]
}

export interface DepreciationComputeResult {
  name: string
  accumulated: number
  book_value: number
  method: string
  pct_depreciated: number
}

export interface ListAssetsDepreciationParams {
  page?: number
  page_size?: number
  method_filter?: string
  status_filter?: string
  category_filter?: string
  /** Virtual filter (vd 'fully_depreciated') — BE áp SoT is_fully_depreciated SAU enrich.
   *  KHÔNG nhồi value này vào status_filter/lifecycle_status (leak sai field BE). */
  depreciation_filter?: string
}

export function listAssetsDepreciation(params: ListAssetsDepreciationParams = {}): Promise<{ items: AssetDepreciationRow[]; pagination: { page: number; page_size: number; total: number } }> {
  return frappeGet(`${BASE}.list_assets_depreciation`, params as Record<string, unknown>)
}

export function getDepreciationStats(): Promise<DepreciationStats> {
  return frappeGet(`${BASE}.get_depreciation_stats`)
}

export function computeDepreciation(name: string): Promise<DepreciationComputeResult> {
  return frappePost(`${BASE}.compute_depreciation`, { name })
}

export function computeAllDepreciation(): Promise<{
  generated_schedules: number
  skipped: number
  executed_rows: number
  updated_assets: number
}> {
  return frappePost(`${BASE}.compute_all_depreciation`)
}

// ─── Asset Transfer CRUD ─────────────────────────────────────────────────────

export function getTransferFull(name: string): Promise<Record<string, unknown>> {
  return frappeGet(`${BASE}.get_transfer_full`, { name })
}

export function updateTransfer(name: string, data: Record<string, unknown>): Promise<{ name: string }> {
  return frappePost(`${BASE}.update_transfer`, { name, ...data })
}

export function approveTransfer(name: string): Promise<{ name: string; approved_by: string }> {
  return frappePost(`${BASE}.approve_transfer`, { name })
}

// ─── PM Schedule CRUD ────────────────────────────────────────────────────────

export interface PmSchedule {
  name: string
  asset_ref: string
  asset_name?: string
  asset_code?: string
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

export interface PmScheduleListResponse {
  data: PmSchedule[]
  pagination: { page: number; page_size: number; total: number; total_pages: number }
}

export function listPmSchedules(params: { page?: number; page_size?: number; asset_ref?: string; status?: string } = {}): Promise<PmScheduleListResponse> {
  return frappeGet(`${BASE}.list_pm_schedules`, params as Record<string, unknown>)
}

export function getPmSchedule(name: string): Promise<PmSchedule> {
  return frappeGet(`${BASE}.get_pm_schedule`, { name })
}

export function createPmSchedule(data: Partial<PmSchedule>): Promise<{ name: string }> {
  return frappePost(`${BASE}.create_pm_schedule`, data as Record<string, unknown>)
}

export function updatePmSchedule(name: string, data: Partial<PmSchedule>): Promise<{ name: string }> {
  return frappePost(`${BASE}.update_pm_schedule`, { name, ...data } as Record<string, unknown>)
}

export function deletePmSchedule(name: string): Promise<{ name: string; deleted: boolean }> {
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
  /** Display name của asset_category (do BE enrich từ AC Asset Category.category_name). */
  category_name?: string
  /** Display name của template (BE thay slug trailing trong template_name bằng category_name). */
  display_template_name?: string
  pm_type?: string
  version?: string
  effective_date?: string
  approved_by?: string
  checklist_items?: PmChecklistItem[]
}

// Endpoints are served by assetcore.api.imm08 (service-based — handles checklist_items JSON)
const _PM_TPL_BASE = '/api/method/assetcore.api.imm08'

export function listPmTemplates(page = 1, page_size = 50): Promise<{ data: PmTemplate[]; pagination: { total: number; page: number; page_size: number } }> {
  return frappeGet(`${_PM_TPL_BASE}.list_pm_templates`, { page, page_size })
}

export function getPmTemplate(name: string): Promise<PmTemplate> {
  return frappeGet(`${_PM_TPL_BASE}.get_pm_template`, { name })
}

export function createPmTemplate(data: Partial<PmTemplate>): Promise<{ name: string }> {
  return frappePost(`${_PM_TPL_BASE}.create_pm_template`, data as Record<string, unknown>)
}

export function updatePmTemplate(name: string, data: Partial<PmTemplate>): Promise<{ name: string }> {
  return frappePost(`${_PM_TPL_BASE}.update_pm_template`, { name, ...data } as Record<string, unknown>)
}

export function deletePmTemplate(name: string): Promise<{ name: string; deleted: boolean }> {
  return frappePost(`${_PM_TPL_BASE}.delete_pm_template`, { name })
}

export interface ApplyPmTemplateResult {
  template: string
  asset_category: string
  total_assets: number
  created: number
  skipped_existing: number
  errors: number
}

export function applyPmTemplateToCategory(templateName: string): Promise<ApplyPmTemplateResult> {
  return frappePost(`${_PM_TPL_BASE}.apply_pm_template_to_category`, { template_name: templateName })
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
  approved_by_name?: string
  approved_datetime?: string
  applied_datetime?: string
  rollback_reason?: string
}

export function listFirmwareCrs(params: { page?: number; page_size?: number; status?: string; asset?: string } = {}): Promise<{ items: FirmwareCR[]; total: number }> {
  return frappeGet(`${BASE}.list_firmware_crs`, params as Record<string, unknown>)
}

export function getFirmwareCr(name: string): Promise<FirmwareCR> {
  return frappeGet(`${BASE}.get_firmware_cr`, { name })
}

export function createFirmwareCr(data: Partial<FirmwareCR>): Promise<{ name: string }> {
  return frappePost(`${BASE}.create_firmware_cr`, data as Record<string, unknown>)
}

export function updateFirmwareCr(name: string, data: Partial<FirmwareCR>): Promise<{ name: string }> {
  return frappePost(`${BASE}.update_firmware_cr`, { name, ...data } as Record<string, unknown>)
}

export function deleteFirmwareCr(name: string): Promise<{ name: string; deleted: boolean }> {
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

export function listDocumentRequests(params: { page?: number; page_size?: number; status?: string; asset?: string } = {}): Promise<{ items: DocumentRequest[]; total: number }> {
  return frappeGet(`${BASE}.list_document_requests`, params as Record<string, unknown>)
}

export function getDocumentRequest(name: string): Promise<DocumentRequest> {
  return frappeGet(`${BASE}.get_document_request`, { name })
}

export function createDocumentRequest(data: Partial<DocumentRequest>): Promise<{ name: string }> {
  return frappePost(`${BASE}.create_document_request`, data as Record<string, unknown>)
}

export function updateDocumentRequest(name: string, data: Partial<DocumentRequest>): Promise<{ name: string }> {
  return frappePost(`${BASE}.update_document_request`, { name, ...data } as Record<string, unknown>)
}

export function deleteDocumentRequest(name: string): Promise<{ name: string; deleted: boolean }> {
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
    `${BASE}.preview_depreciation_schedule`, params as Record<string, unknown>,
  )
}

export async function runDueDepreciationNow(as_of?: string) {
  return frappePost<{ executed_rows: number; updated_assets: number }>(
    `${BASE}.run_due_depreciation_now`, { as_of: as_of || '' },
  )
}

// ─── Device Model file upload ────────────────────────────────────────────────

export interface DeviceModelFileUploadResult {
  name: string
  file_url: string
  file_name: string
  fieldname: string
}

export async function uploadDeviceModelFile(
  file: File,
  fieldname: 'model_image' | 'catalog_file',
  model_name = '',
): Promise<DeviceModelFileUploadResult> {
  const form = new FormData()
  form.append('file', file, file.name)
  form.append('fieldname', fieldname)
  if (model_name) form.append('model_name', model_name)
  // axios v1 auto-fills the multipart boundary when Content-Type is 'multipart/form-data'
  // and data is a FormData instance — overriding the instance default of 'application/json'.
  const { default: api } = await import('./axios')
  const res = await api.post<{ message: { success: boolean; data: DeviceModelFileUploadResult; error?: string } }>(
    `${BASE}.upload_device_model_file`, form,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  )
  const env = res.data?.message
  if (!env?.success || !env.data?.file_url) {
    throw new Error(env?.error || 'Upload thất bại')
  }
  return env.data
}

export async function bulkRegenerateScheduleByCategory(category_name: string) {
  return frappePost<{
    category: string; total_assets: number; regenerated: number;
    skipped_has_history: number; errors: number
  }>(`${BASE}.bulk_regenerate_schedule_by_category`, { category_name })
}
