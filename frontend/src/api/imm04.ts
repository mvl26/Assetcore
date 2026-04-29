// Copyright (c) 2026, AssetCore Team
// API calls cho Module IMM-04 — wrapping Frappe whitelist methods

import api from './axios'
import { frappeGet, frappePost } from './helpers'
import type {
  CommissioningDoc,
  CommissioningListResponse,
  CommissioningFilters,
  DashboardStats,
  QrLabelData,
  BarcodeLookupResult,
  SaveResponse,
  PoDetails,
} from '@/types/imm04'

// ─────────────────────────────────────────────────────────────────────────────
// BASE URL
// ─────────────────────────────────────────────────────────────────────────────

const BASE = '/api/method/assetcore.api.imm04'

// ─────────────────────────────────────────────────────────────────────────────
// 1. GET FORM CONTEXT
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Lấy toàn bộ dữ liệu form + workflow state + allowed transitions.
 */
export async function getFormContext(name: string): Promise<CommissioningDoc> {
  return frappeGet<CommissioningDoc>(`${BASE}.get_form_context`, { name })
}

// ─────────────────────────────────────────────────────────────────────────────
// 2. LIST COMMISSIONING
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Paginated list với filters.
 */
export async function listCommissioning(
  filters: CommissioningFilters = {},
  page: number = 1,
  pageSize: number = 20,
): Promise<CommissioningListResponse> {
  return frappeGet<CommissioningListResponse>(`${BASE}.list_commissioning`, {
    filters: JSON.stringify(filters),
    page,
    page_size: pageSize,
  })
}

// ─────────────────────────────────────────────────────────────────────────────
// 3. TRANSITION STATE
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Thực hiện workflow transition.
 */
export async function transitionState(
  name: string,
  action: string,
): Promise<{ name: string; action_applied: string; new_state: string; docstatus: number; message: string }> {
  return frappePost(`${BASE}.transition_state`, { name, action })
}

// ─────────────────────────────────────────────────────────────────────────────
// 4. GENERATE QR LABEL
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Lấy dữ liệu QR để frontend render label.
 */
export async function generateQrLabel(name: string): Promise<QrLabelData> {
  return frappeGet<QrLabelData>(`${BASE}.generate_qr_label`, { name })
}

// ─────────────────────────────────────────────────────────────────────────────
// 5. SUBMIT COMMISSIONING
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Submit phiếu commissioning (chỉ IMM Operations Manager / IMM Workshop Lead).
 */
export async function submitCommissioning(
  name: string,
): Promise<{ name: string; docstatus: number; final_asset: string; message: string }> {
  return frappePost(`${BASE}.submit_commissioning`, { name })
}

// ─────────────────────────────────────────────────────────────────────────────
// 6. BARCODE LOOKUP
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Tìm thiết bị theo barcode hoặc QR.
 */
export async function getBarcodeLookup(barcode: string): Promise<BarcodeLookupResult> {
  return frappeGet<BarcodeLookupResult>(`${BASE}.get_barcode_lookup`, { barcode })
}

// ─────────────────────────────────────────────────────────────────────────────
// 7. DASHBOARD STATS
// ─────────────────────────────────────────────────────────────────────────────

/**
 * KPIs và danh sách gần nhất cho Dashboard.
 */
export async function getDashboardStats(): Promise<DashboardStats> {
  return frappeGet<DashboardStats>(`${BASE}.get_dashboard_stats`)
}

// ─────────────────────────────────────────────────────────────────────────────
// 8. SAVE COMMISSIONING (Inline edit)
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Lưu thay đổi inline trên phiếu Commissioning.
 */
export async function saveCommissioning(
  name: string,
  fields: Record<string, unknown>,
): Promise<SaveResponse> {
  return frappePost(`${BASE}.save_commissioning`, { name, fields: JSON.stringify(fields) })
}

// ─────────────────────────────────────────────────────────────────────────────
// 9. CREATE COMMISSIONING
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Tạo phiếu Commissioning mới.
 */
export async function createCommissioning(
  data: Record<string, unknown>,
): Promise<SaveResponse> {
  return frappePost(`${BASE}.create_commissioning`, { data: JSON.stringify(data) })
}

// ─────────────────────────────────────────────────────────────────────────────
// 10. GET PO DETAILS (Auto-fill)
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Lấy thông tin PO để auto-fill vendor/model.
 */
export async function getPoDetails(poName: string): Promise<PoDetails> {
  return frappeGet<PoDetails>(`${BASE}.get_po_details`, { po_name: poName })
}

// ─────────────────────────────────────────────────────────────────────────────
// SESSION / AUTH
// ─────────────────────────────────────────────────────────────────────────────

export interface FrappeSession {
  name: string
  full_name: string
  roles: string[]
  user_image: string | null
}

/**
 * Lấy thông tin user hiện tại từ Frappe session.
 * Dùng 2 call:
 *   1. get_logged_user → username
 *   2. frappe.client.get (full doc, không filter fields) → full_name, user_image, roles child table
 */
export async function getCurrentSession(): Promise<FrappeSession> {
  // 1. Lấy username từ session
  const res = await api.get<{ message: string }>('/api/method/frappe.auth.get_logged_user')
  const username = res.data.message

  // 2. Lấy full User doc — KHÔNG dùng fields param vì child table 'roles' không được trả về khi filter
  const userRes = await api.get<{
    message: { full_name: string; user_image: string | null; roles: { role: string }[] }
  }>('/api/method/frappe.client.get', {
    params: {
      doctype: 'User',
      name: username,
    },
  })

  const userData = userRes.data.message
  return {
    name: username,
    full_name: userData.full_name ?? username,
    user_image: userData.user_image ?? null,
    roles: (userData.roles ?? []).map((r: { role: string }) => r.role),
  }
}

/**
 * Logout khỏi Frappe.
 */
export async function logout(): Promise<void> {
  await api.get('/api/method/logout')
}

// ─────────────────────────────────────────────────────────────────────────────
// 11. CHECK SN UNIQUE
// ─────────────────────────────────────────────────────────────────────────────
export async function checkSnUnique(
  vendorSn: string,
  excludeName: string = '',
): Promise<{ is_unique: boolean; existing_commissioning?: string; item?: string }> {
  return frappeGet(`${BASE}.check_sn_unique`, { vendor_sn: vendorSn, exclude_name: excludeName })
}

// ─────────────────────────────────────────────────────────────────────────────
// 12. REPORT NON-CONFORMANCE
// ─────────────────────────────────────────────────────────────────────────────
export async function reportNonConformance(
  commissioningName: string,
  ncData: { nc_type: string; severity: string; description: string },
): Promise<{ name: string; nc_type: string; severity: string }> {
  return frappePost(`${BASE}.report_nonconformance`, {
    commissioning_name: commissioningName,
    nc_data: JSON.stringify(ncData),
  })
}

// ─────────────────────────────────────────────────────────────────────────────
// 13. ASSIGN IDENTIFICATION
// ─────────────────────────────────────────────────────────────────────────────
export async function assignIdentification(
  name: string,
  vendorSerialNo: string,
  internalTagQr: string = '',
  customMohCode: string = '',
): Promise<{ name: string; vendor_serial_no: string; internal_tag_qr: string }> {
  return frappePost(`${BASE}.assign_identification`, {
    name,
    vendor_serial_no: vendorSerialNo,
    internal_tag_qr: internalTagQr,
    custom_moh_code: customMohCode,
  })
}

// ─────────────────────────────────────────────────────────────────────────────
// 14. SUBMIT BASELINE CHECKLIST
// ─────────────────────────────────────────────────────────────────────────────
export async function submitBaselineChecklist(
  name: string,
  results: Array<{ parameter: string; test_result: string; measured_val?: number; fail_note?: string }>,
): Promise<{ name: string; overall_result: string; clinical_hold_required: boolean }> {
  return frappePost(`${BASE}.submit_baseline_checklist`, {
    name,
    results: JSON.stringify(results),
  })
}

// ─────────────────────────────────────────────────────────────────────────────
// 15. CLEAR CLINICAL HOLD
// ─────────────────────────────────────────────────────────────────────────────
export async function clearClinicalHold(
  name: string,
  licenseNo: string = '',
): Promise<{ name: string; license_no: string }> {
  return frappePost(`${BASE}.clear_clinical_hold`, { name, license_no: licenseNo })
}

// ─────────────────────────────────────────────────────────────────────────────
// 16. APPROVE CLINICAL RELEASE
// ─────────────────────────────────────────────────────────────────────────────
export async function approveClinicalRelease(
  commissioning: string,
  boardApprover: string,
  approvalRemarks: string = '',
): Promise<{ commissioning: string; new_status: string; asset_ref: string; commissioning_date: string }> {
  return frappePost(`${BASE}.approve_clinical_release`, {
    commissioning,
    board_approver: boardApprover,
    approval_remarks: approvalRemarks,
  })
}

// ─────────────────────────────────────────────────────────────────────────────
// 17. UPLOAD DOCUMENT (commissioning document row)
// ─────────────────────────────────────────────────────────────────────────────
export async function uploadCommissioningDocument(
  commissioning: string,
  docIndex: number,
  fileUrl: string,
  options: { expiry_date?: string; doc_number?: string } = {},
): Promise<{ commissioning: string; doc_index: number; all_mandatory_received: boolean }> {
  return frappePost(`${BASE}.upload_document`, {
    commissioning,
    doc_index: docIndex,
    file_url: fileUrl,
    expiry_date: options.expiry_date || '',
    doc_number: options.doc_number || '',
  })
}

// ─────────────────────────────────────────────────────────────────────────────
// 18. CLOSE NON-CONFORMANCE
// ─────────────────────────────────────────────────────────────────────────────
export async function closeNonConformance(
  ncName: string,
  rootCause: string,
  correctiveAction: string,
): Promise<{ name: string; status: string }> {
  return frappePost(`${BASE}.close_nonconformance`, {
    nc_name: ncName,
    root_cause: rootCause,
    corrective_action: correctiveAction,
  })
}

// ─────────────────────────────────────────────────────────────────────────────
// 20. DELETE COMMISSIONING (Draft only)
// ─────────────────────────────────────────────────────────────────────────────
export async function deleteCommissioning(
  name: string,
): Promise<{ deleted: string }> {
  return frappePost(`${BASE}.delete_commissioning`, { name })
}

// ─────────────────────────────────────────────────────────────────────────────
// 21. CANCEL COMMISSIONING (Submitted → Cancelled, role-gated)
// ─────────────────────────────────────────────────────────────────────────────
export async function cancelCommissioning(
  name: string,
): Promise<{ name: string; docstatus: number; cancelled_by: string }> {
  return frappePost(`${BASE}.cancel_commissioning`, { name })
}

// ─────────────────────────────────────────────────────────────────────────────
// 19. GENERATE HANDOVER PDF
// ─────────────────────────────────────────────────────────────────────────────
export async function generateHandoverPdf(
  name: string,
): Promise<{ pdf_url: string; name: string }> {
  return frappeGet(`${BASE}.generate_handover_pdf`, { name })
}

// ─────────────────────────────────────────────────────────────────────────────
// 22. GET USERS BY ROLE
// ─────────────────────────────────────────────────────────────────────────────
export const getUsersByRole = (role: string, search = '', limit = 20) =>
  frappeGet<Array<{ name: string; full_name: string; email: string; user_image?: string }>>(
    '/api/method/assetcore.api.imm04.get_users_by_role', { role, search, limit }
  )

// ─────────────────────────────────────────────────────────────────────────────
// 23. GET GATE STATUS
// ─────────────────────────────────────────────────────────────────────────────
export interface GateStatus {
  g01_docs: boolean
  g02_facility: boolean
  g03_baseline: boolean
  g04_radiation: boolean
  g05_nc: boolean
  g06_approver: boolean
}

export const getGateStatus = (name: string) =>
  frappeGet<GateStatus>('/api/method/assetcore.api.imm04.get_gate_status', { name })

// ─── Submit-for-approval flow ────────────────────────────────────────────────

export interface PendingApprovalRow {
  name: string
  workflow_state: string
  master_item: string
  vendor: string
  clinical_dept: string
  approval_stage: string
  approval_submitted_at: string
  approval_remarks: string
  owner: string
  modified: string
}

export const submitForApproval = (commissioning: string, approver: string,
                                   stage = '', remarks = '') =>
  frappePost<{ name: string; pending_approver: string; approval_stage: string; approval_submitted_at: string }>(
    '/api/method/assetcore.api.imm04.submit_for_approval',
    { commissioning, approver, stage, remarks }
  )

export const approvePending = (commissioning: string, decision: 'Approve' | 'Reject', remarks = '') =>
  frappePost<{ name: string; decision: string; workflow_state: string }>(
    '/api/method/assetcore.api.imm04.approve_pending',
    { commissioning, decision, remarks }
  )

export const listMyPendingApprovals = () =>
  frappeGet<PendingApprovalRow[]>('/api/method/assetcore.api.imm04.list_my_pending_approvals')

// ─── Purchase → Commissioning linkage (Wave 1) ────────────────────────────────

export const createCommissioningFromPurchase = (purchase_name: string, device_idx: number) =>
  frappePost<{ name: string; workflow_state: string; purchase: string }>(
    '/api/method/assetcore.api.imm04.create_from_purchase',
    { purchase_name, device_idx }
  )

export interface CommissioningOrigin {
  asset: string
  commissioning: null | {
    name: string
    workflow_state: string
    po_reference: string
    vendor: string
    master_item: string
    reception_date: string
    commissioning_date: string
    vendor_serial_no: string
    purchase_price: number
    warranty_expiry_date: string
    commissioned_by: string
    transferred_doc_count: number
  }
}

export const getCommissioningOrigin = (asset_name: string) =>
  frappeGet<CommissioningOrigin>(
    '/api/method/assetcore.api.imm04.get_commissioning_origin', { asset_name }
  )
