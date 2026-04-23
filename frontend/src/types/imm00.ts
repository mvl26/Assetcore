// Copyright (c) 2026, AssetCore Team
// TypeScript types cho IMM-00 foundation module

export type LifecycleStatus =
  | 'Commissioned' | 'Active' | 'Under Repair' | 'Calibrating'
  | 'Out of Service' | 'Decommissioned'

export type RiskClass = 'Low' | 'Medium' | 'High' | 'Critical'
export type MedicalDeviceClass = 'Class I' | 'Class II' | 'Class III'
export type CapaSeverity = 'Minor' | 'Major' | 'Critical'
export type CapaStatus = 'Open' | 'In Progress' | 'Pending Verification' | 'Closed' | 'Overdue'
export type IncidentSeverity = 'Low' | 'Medium' | 'High' | 'Critical'
export type GmdnStatus = 'In Use' | 'Not Use'

export interface PaginatedResponse<T> {
  pagination: {
    page: number
    page_size: number
    total: number
    total_pages: number
    offset: number
  }
  items: T[]
}

// ─── AC Asset ─────────────────────────────────────────────────────────────────

export interface AcAssetListItem {
  name: string
  asset_name: string
  asset_code?: string
  lifecycle_status: LifecycleStatus
  asset_category?: string
  category_name?: string
  location?: string
  gmdn_status?: GmdnStatus
  location_name?: string
  department?: string
  department_name?: string
  responsible_technician?: string
  next_pm_date?: string
  next_calibration_date?: string
  byt_reg_expiry?: string
}

export interface AcAsset extends AcAssetListItem {
  naming_series?: string
  item_code?: string
  image?: string
  status?: string
  custodian?: string
  supplier?: string
  supplier_name?: string
  purchase_date?: string
  gross_purchase_amount?: number
  warranty_expiry_date?: string
  device_model?: string
  device_model_name?: string
  responsible_technician_name?: string
  medical_device_class?: MedicalDeviceClass
  risk_classification?: RiskClass
  manufacturer_sn?: string
  udi_code?: string
  gmdn_code?: string
  gmdn_status?: GmdnStatus
  byt_reg_no?: string
  commissioning_date?: string
  commissioning_ref?: string
  calibration_status?: string
  is_pm_required?: 0 | 1
  pm_interval_days?: number
  last_pm_date?: string
  is_calibration_required?: 0 | 1
  calibration_interval_days?: number
  last_calibration_date?: string
  uptime_pct?: number
  mtbf_days?: number
  mttr_hours?: number
  pm_compliance_pct?: number
  total_repair_cost?: number
  notes?: string
  authorized_technicians?: AcAuthorizedTechnician[]
  spare_parts?: ImmDeviceSparePart[]
}

export interface AcAuthorizedTechnician {
  technician: string
  technician_name?: string
  certification?: string
  expiry_date?: string
}

export interface ImmDeviceSparePart {
  part_name: string
  part_number?: string
  quantity?: number
  unit?: string
}

export interface AssetKpi {
  name: string
  lifecycle_status: LifecycleStatus
  uptime_pct?: number
  mtbf_days?: number
  mttr_hours?: number
  pm_compliance_pct?: number
  total_repair_cost?: number
  next_pm_date?: string
  next_calibration_date?: string
  byt_reg_expiry?: string
  gmdn_code?: string
  gmdn_status?: GmdnStatus
}

export interface AssetListParams {
  page?: number
  page_size?: number
  lifecycle_status?: string
  department?: string
  location?: string
  asset_category?: string
  search?: string
  gmdn_status?: GmdnStatus | ''
}

// ─── AC Supplier ──────────────────────────────────────────────────────────────

export type VendorType = 'Manufacturer' | 'Distributor' | 'Service Provider' | 'Calibration Lab'

export interface AcSupplier {
  name: string
  supplier_name: string
  supplier_code?: string
  supplier_group?: string
  vendor_type?: VendorType
  country?: string
  tax_id?: string
  website?: string
  address?: string
  phone?: string
  mobile_no?: string
  email_id?: string
  technical_email?: string
  support_hotline?: string
  local_representative?: string
  iso_17025_cert?: string
  iso_17025_expiry?: string
  iso_13485_cert?: string
  iso_13485_expiry?: string
  contract_start?: string
  contract_end?: string
  contract_value?: number
  is_active?: 0 | 1
}

// ─── AC Location / Department / Category ─────────────────────────────────────

export interface AcLocation {
  name: string
  location_name: string
  location_code?: string
  parent_location?: string
  is_group?: 0 | 1
  clinical_area_type?: string
  infection_control_level?: string
  power_backup_available?: 0 | 1
  emergency_contact?: string
  dept_head?: string
  technical_contact?: string
  notes?: string
}

export interface AcDepartment {
  name: string
  department_name: string
  department_code?: string
  parent_department?: string
  is_group?: 0 | 1
  dept_head?: string
  phone?: string
  email?: string
  is_active?: 0 | 1
}

export interface AcAssetCategory {
  name: string
  category_name: string
  description?: string
  default_pm_required?: 0 | 1
  default_pm_interval_days?: number
  default_calibration_required?: 0 | 1
  default_calibration_interval_days?: number
  has_radiation?: 0 | 1
  is_active?: 0 | 1
}

// ─── IMM Device Model ─────────────────────────────────────────────────────────

export interface ImmDeviceModel {
  name: string
  model_name: string
  model_version?: string
  manufacturer: string
  asset_category: string
  country_of_origin?: string
  power_supply?: string
  expected_lifespan_years?: number
  medical_device_class: MedicalDeviceClass
  risk_classification?: RiskClass
  gmdn_code?: string
  emdn_code?: string
  hsn_code?: string
  registration_required?: 0 | 1
  is_radiation_device?: 0 | 1
  is_pm_required?: 0 | 1
  pm_interval_days?: number
  pm_alert_days?: number
  is_calibration_required?: 0 | 1
  calibration_interval_days?: number
  calibration_alert_days?: number
  default_calibration_type?: string
  notes?: string
}

// ─── IMM SLA Policy ───────────────────────────────────────────────────────────

export interface ImmSlaPolicy {
  name: string
  policy_name: string
  priority: string
  risk_class?: RiskClass
  is_default?: 0 | 1
  response_time_minutes: number
  resolution_time_hours: number
  working_hours_only?: 0 | 1
  escalation_l1_role?: string
  escalation_l1_hours?: number
  escalation_l2_role?: string
  escalation_l2_hours?: number
  effective_date?: string
  expiry_date?: string
  is_active?: 0 | 1
}

// ─── IMM Audit Trail ──────────────────────────────────────────────────────────

export interface ImmAuditTrail {
  name: string
  asset: string
  asset_name?: string
  event_type: string
  actor: string
  change_summary: string
  from_status?: string
  to_status?: string
  ref_doctype?: string
  ref_name?: string
  timestamp: string
  event_timestamp?: string  // legacy alias
  hash?: string
}

export interface ChainVerifyResult {
  valid: boolean
  count: number
  broken_at?: string
}

// ─── IMM CAPA Record ──────────────────────────────────────────────────────────

export interface ImmCapaRecord {
  name: string
  capa_type?: string
  status: CapaStatus
  asset: string
  asset_name?: string
  title?: string
  severity: CapaSeverity
  due_date?: string
  owner?: string
  creation?: string
  description?: string
}

// ─── Asset Lifecycle Event ────────────────────────────────────────────────────

export interface AssetLifecycleEvent {
  name: string
  event_type: string
  actor: string
  from_status?: string
  to_status?: string
  timestamp: string
  event_timestamp?: string  // legacy alias
  root_doctype?: string
  root_record?: string
  notes?: string
}

// ─── Asset Transfer ───────────────────────────────────────────────────────────

export type TransferType = 'Internal' | 'Loan' | 'External' | 'Return'

export interface AssetTransfer {
  name: string
  asset: string
  asset_name?: string
  transfer_date: string
  transfer_type: TransferType
  status?: string
  from_location?: string
  from_department?: string
  from_custodian?: string
  to_location: string
  to_department?: string
  to_custodian?: string
  reason: string
  approved_by?: string
  approval_date?: string
  received_by?: string
  received_date?: string
  expected_return_date?: string
  notes?: string
}

// ─── Service Contract ─────────────────────────────────────────────────────────

export type ServiceContractType =
  | 'Preventive Maintenance' | 'Calibration' | 'Repair'
  | 'Full Service' | 'Warranty Extension'

export interface ServiceContractAsset {
  asset: string
  asset_name?: string
  coverage_note?: string
}

export interface ServiceContract {
  name: string
  contract_title: string
  supplier: string
  contract_type: ServiceContractType
  contract_start: string
  contract_end: string
  contract_value?: number
  auto_renew?: 0 | 1
  sla_response_hours?: number
  coverage_description?: string
  covered_assets?: ServiceContractAsset[]
}

// ─── Incident Report ──────────────────────────────────────────────────────────

export interface IncidentReport {
  name: string
  severity: IncidentSeverity
  status?: string
  asset: string
  asset_name?: string
  incident_type?: string
  description: string
  reported_at: string
  immediate_action?: string
  patient_affected?: 0 | 1
  patient_impact_description?: string
  reported_to_byt?: 0 | 1
  byt_report_date?: string
  linked_repair_wo?: string
  linked_capa?: string
  root_cause_summary?: string
  resolution_notes?: string
  closed_date?: string
}
