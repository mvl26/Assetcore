// Copyright (c) 2026, AssetCore Team
// TypeScript interfaces cho Module IMM-04 — Asset Commissioning

// ─────────────────────────────────────────────────────────────────────────────
// API RESPONSE WRAPPER
// ─────────────────────────────────────────────────────────────────────────────

export interface ApiResponse<T> {
  success: boolean
  data?: T
  error?: string
  code?: string
}

// ─────────────────────────────────────────────────────────────────────────────
// WORKFLOW
// ─────────────────────────────────────────────────────────────────────────────

export type WorkflowState =
  | 'Draft'
  | 'Draft_Reception'
  | 'Pending_Doc_Verify'
  | 'To_Be_Installed'
  | 'Installing'
  | 'Identification'
  | 'Initial_Inspection'
  | 'Non_Conformance'
  | 'Clinical_Hold'
  | 'Re_Inspection'
  | 'Clinical_Release'
  | 'Return_To_Vendor'
  | 'Pending_Release'
  | 'DOA_Incident'

export interface WorkflowTransition {
  action: string
  next_state: WorkflowState
  allowed_role: string
}

// ─────────────────────────────────────────────────────────────────────────────
// CHILD TABLE: BASELINE TEST
// ─────────────────────────────────────────────────────────────────────────────

export type TestResult = 'Pass' | 'Fail' | 'N/A' | ''
export type DocStatus = 0 | 1 | 2

export interface BaselineTest {
  idx: number
  parameter: string
  measured_val: string
  unit: string
  test_result: TestResult
  fail_note: string
  is_critical?: 0 | 1
  measurement_type?: 'Numeric' | 'Pass/Fail' | 'Visual'
  expected_min?: number | null
  expected_max?: number | null
  na_applicable?: 0 | 1
}

// ─────────────────────────────────────────────────────────────────────────────
// CHILD TABLE: COMMISSIONING DOCUMENT RECORD
// ─────────────────────────────────────────────────────────────────────────────

export interface DocumentRecord {
  idx: number
  doc_type: string
  status: string
  received_date: string
  remarks: string
  is_mandatory?: 0 | 1
  file_url?: string
  doc_number?: string
  expiry_date?: string
}

// ─────────────────────────────────────────────────────────────────────────────
// MAIN DOC: ASSET COMMISSIONING
// ─────────────────────────────────────────────────────────────────────────────

export interface CommissioningDoc {
  name: string
  workflow_state: WorkflowState
  docstatus: DocStatus

  // Procurement
  po_reference: string
  master_item: string             // IMM Device Model
  vendor: string                  // AC Supplier
  asset_description: string
  delivery_note_no: string
  purchase_price: number | null
  warranty_expiry_date: string

  // Scheduling
  clinical_dept: string           // AC Department
  expected_installation_date: string

  // Installation
  installation_date: string
  vendor_engineer_name: string
  reception_date: string
  installation_location: string   // AC Location
  received_by: string             // User — kho vận
  dept_head_acceptance: string    // User — trưởng khoa
  is_radiation_device: 0 | 1
  radiation_license_no: string
  doa_incident: 0 | 1
  facility_checklist_pass: 0 | 1

  // Risk & Approvers
  risk_class: RiskClass
  clinical_head: string
  qa_officer: string
  board_approver: string

  // Approval flow
  pending_approver: string
  approval_stage: '' | 'Doc Verify' | 'Facility Check' | 'Baseline Review' | 'Clinical Release'
  approval_submitted_at: string
  approval_remarks: string

  // Identification
  vendor_serial_no: string
  internal_tag_qr: string
  custom_moh_code: string

  // QA evidence
  site_photo: string
  installation_evidence: string
  qa_license_doc: string

  // Inspection
  overall_inspection_result: string
  handover_doc: string
  commissioned_by: string
  commissioning_date: string

  // Output
  final_asset: string
  amend_reason: string
  amended_from: string

  // Meta
  modified: string
  owner: string

  // Child tables
  baseline_tests: BaselineTest[]
  commissioning_documents: DocumentRecord[]
  lifecycle_events: LifecycleEvent[]

  // Computed by API
  allowed_transitions: WorkflowTransition[]
  is_locked: boolean
  current_user_roles: string[]
}

// ─────────────────────────────────────────────────────────────────────────────
// LIST VIEW
// ─────────────────────────────────────────────────────────────────────────────

export interface CommissioningListItem {
  name: string
  workflow_state: WorkflowState
  docstatus: DocStatus
  po_reference: string
  master_item: string
  vendor: string
  clinical_dept: string
  expected_installation_date: string
  installation_date: string
  vendor_serial_no: string
  internal_tag_qr: string
  final_asset: string
  modified: string
  asset_name?: string
  master_item_name?: string
  vendor_name?: string
  clinical_dept_name?: string
  commissioning_date?: string
}

export interface Pagination {
  page: number
  page_size: number
  total: number
  total_pages: number
}

export interface CommissioningListResponse {
  items: CommissioningListItem[]
  pagination: Pagination
}

// ─────────────────────────────────────────────────────────────────────────────
// DASHBOARD STATS
// ─────────────────────────────────────────────────────────────────────────────

export interface KpiStats {
  pending_count: number
  hold_count: number
  open_nc_count: number
  released_this_month: number
  overdue_sla: number
}

export interface StateBreakdown {
  workflow_state: WorkflowState
  count: number
}

export interface DashboardStats {
  kpis: KpiStats
  states_breakdown: StateBreakdown[]
  recent_list: CommissioningListItem[]
}

// ─────────────────────────────────────────────────────────────────────────────
// QR LABEL
// ─────────────────────────────────────────────────────────────────────────────

export interface QrLabelData {
  qr_value: string
  label: {
    title: string
    commissioning_id: string
    internal_qr: string
    vendor_serial: string
    model: string
    vendor: string
    dept: string
    moh_code: string
    installation_date: string
    status: WorkflowState
    asset_id: string
    print_date: string
  }
  scan_url: string
}

// ─────────────────────────────────────────────────────────────────────────────
// BARCODE LOOKUP
// ─────────────────────────────────────────────────────────────────────────────

export interface BarcodeLookupResult {
  commissioning_id: string
  workflow_state: WorkflowState
  docstatus: DocStatus
  is_released: boolean
  device: {
    model: string
    vendor: string
    dept: string
    installation_date: string
    vendor_serial: string
    internal_qr: string
    is_radiation: boolean
    doa_incident: boolean
  }
  asset_id: string
  baseline_tests: Pick<BaselineTest, 'parameter' | 'measured_val' | 'unit' | 'test_result'>[]
}

// ─────────────────────────────────────────────────────────────────────────────
// LIST FILTERS
// ─────────────────────────────────────────────────────────────────────────────

// ─────────────────────────────────────────────────────────────────────────────
// PO DETAILS (auto-fill)
// ─────────────────────────────────────────────────────────────────────────────

export interface PoItem {
  item_code: string
  item_name: string
  qty: number
  is_radiation: boolean
}

export interface PoDetails {
  po_name: string
  supplier: string
  supplier_name: string
  transaction_date: string
  items: PoItem[]
}

// ─────────────────────────────────────────────────────────────────────────────
// SAVE / CREATE RESPONSE
// ─────────────────────────────────────────────────────────────────────────────

export interface SaveResponse {
  name: string
  workflow_state: WorkflowState
  message: string
}

// ─────────────────────────────────────────────────────────────────────────────
// LINK SEARCH
// ─────────────────────────────────────────────────────────────────────────────

export interface LinkItem {
  value: string
  label: string
  description: string
}

export interface DeviceModelDetails {
  name: string
  model_name: string
  manufacturer: string
  medical_device_class: 'Class I' | 'Class II' | 'Class III' | ''
  risk_classification: 'Low' | 'Medium' | 'High' | 'Critical' | ''
  is_radiation_device: 0 | 1
  is_pm_required: 0 | 1
  pm_interval_days: number
  is_calibration_required: 0 | 1
  calibration_interval_days: number
}

// ─────────────────────────────────────────────────────────────────────────────
// LIST FILTERS
// ─────────────────────────────────────────────────────────────────────────────

export interface CommissioningFilters {
  workflow_state?: WorkflowState | ''
  po_reference?: string
  master_item?: string
  vendor?: string
  clinical_dept?: string
  docstatus?: 0 | 1 | ''
  vendor_serial_no?: string
}

// ─────────────────────────────────────────────────────────────────────────────
// AUTH / SESSION
// ─────────────────────────────────────────────────────────────────────────────

export interface FrappeUser {
  name: string
  full_name: string
  email: string
  user_image: string | null
  roles: string[]
}

// ─────────────────────────────────────────────────────────────────────────────
// RISK CLASS
// ─────────────────────────────────────────────────────────────────────────────

export type RiskClass = 'A' | 'B' | 'C' | 'D' | 'Radiation' | ''

// ─────────────────────────────────────────────────────────────────────────────
// NON CONFORMANCE
// ─────────────────────────────────────────────────────────────────────────────

export type NCStatus = 'Open' | 'Under Review' | 'Resolved' | 'Closed' | 'Transferred'

export interface NonConformance {
  name: string
  nc_type: string
  severity: 'Minor' | 'Major' | 'Critical' | ''
  description: string
  resolution_status: NCStatus
  resolution_note?: string
  root_cause?: string
  reported_by?: string
  closed_by?: string
  closed_date?: string
  damage_proof?: string
}

// ─────────────────────────────────────────────────────────────────────────────
// LIFECYCLE EVENT
// ─────────────────────────────────────────────────────────────────────────────

export interface LifecycleEvent {
  event_type: string
  from_status: string
  to_status: string
  actor: string
  event_timestamp: string
  ip_address?: string
  remarks?: string
}
