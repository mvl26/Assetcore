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
  | 'Identification'
  | 'Installing'
  | 'Initial_Inspection'
  | 'Clinical_Hold'
  | 'Re_Inspection'
  | 'Pending_Release'
  | 'Clinical_Release'
  | 'Return_To_Vendor'

export interface WorkflowTransition {
  action: string
  next_state: WorkflowState
  allowed_role: string
}

// ─────────────────────────────────────────────────────────────────────────────
// CHILD TABLE: BASELINE TEST
// ─────────────────────────────────────────────────────────────────────────────

export type TestResult = 'Pass' | 'Fail' | ''

export interface BaselineTest {
  idx: number
  parameter: string
  measured_val: string
  unit: string
  test_result: TestResult
  fail_note: string
}

// ─────────────────────────────────────────────────────────────────────────────
// CHILD TABLE: COMMISSIONING DOCUMENT RECORD
// ─────────────────────────────────────────────────────────────────────────────

export interface DocumentRecord {
  idx: number
  doc_type: string
  status: 'Received' | 'Pending' | string
  received_date: string
  remarks: string
}

// ─────────────────────────────────────────────────────────────────────────────
// MAIN DOC: ASSET COMMISSIONING
// ─────────────────────────────────────────────────────────────────────────────

export interface CommissioningDoc {
  name: string
  workflow_state: WorkflowState
  docstatus: 0 | 1 | 2

  // Procurement
  po_reference: string
  master_item: string
  vendor: string

  // Scheduling
  clinical_dept: string
  expected_installation_date: string

  // Installation
  installation_date: string
  vendor_engineer_name: string
  is_radiation_device: 0 | 1
  doa_incident: 0 | 1

  // Identification
  vendor_serial_no: string
  internal_tag_qr: string
  custom_moh_code: string

  // QA evidence
  site_photo: string
  installation_evidence: string
  qa_license_doc: string

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
  docstatus: 0 | 1 | 2
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
  docstatus: 0 | 1 | 2
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
