// Copyright (c) 2026, AssetCore Team
// API calls cho Module IMM-04 — wrapping Frappe whitelist methods

import api from './axios'
import type {
  ApiResponse,
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
// HELPER
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Frappe whitelist trả về {message: <actual_data>}.
 * Hàm này unwrap lớp message ra.
 */
async function frappeGet<T>(endpoint: string, params?: Record<string, unknown>): Promise<T> {
  const response = await api.get<{ message: T }>(endpoint, { params })
  return response.data.message
}

async function frappePost<T>(endpoint: string, body?: Record<string, unknown>): Promise<T> {
  const response = await api.post<{ message: T }>(endpoint, body)
  return response.data.message
}

// ─────────────────────────────────────────────────────────────────────────────
// 1. GET FORM CONTEXT
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Lấy toàn bộ dữ liệu form + workflow state + allowed transitions.
 */
export async function getFormContext(name: string): Promise<ApiResponse<CommissioningDoc>> {
  return frappeGet<ApiResponse<CommissioningDoc>>(`${BASE}.get_form_context`, { name })
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
): Promise<ApiResponse<CommissioningListResponse>> {
  return frappeGet<ApiResponse<CommissioningListResponse>>(`${BASE}.list_commissioning`, {
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
): Promise<ApiResponse<{ name: string; action_applied: string; new_state: string; docstatus: number; message: string }>> {
  return frappePost(`${BASE}.transition_state`, { name, action })
}

// ─────────────────────────────────────────────────────────────────────────────
// 4. GENERATE QR LABEL
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Lấy dữ liệu QR để frontend render label.
 */
export async function generateQrLabel(name: string): Promise<ApiResponse<QrLabelData>> {
  return frappeGet<ApiResponse<QrLabelData>>(`${BASE}.generate_qr_label`, { name })
}

// ─────────────────────────────────────────────────────────────────────────────
// 5. SUBMIT COMMISSIONING
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Submit phiếu commissioning (chỉ VP Block2 / Workshop Head).
 */
export async function submitCommissioning(
  name: string,
): Promise<ApiResponse<{ name: string; docstatus: number; final_asset: string; message: string }>> {
  return frappePost(`${BASE}.submit_commissioning`, { name })
}

// ─────────────────────────────────────────────────────────────────────────────
// 6. BARCODE LOOKUP
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Tìm thiết bị theo barcode hoặc QR.
 */
export async function getBarcodeLookup(barcode: string): Promise<ApiResponse<BarcodeLookupResult>> {
  return frappeGet<ApiResponse<BarcodeLookupResult>>(`${BASE}.get_barcode_lookup`, { barcode })
}

// ─────────────────────────────────────────────────────────────────────────────
// 7. DASHBOARD STATS
// ─────────────────────────────────────────────────────────────────────────────

/**
 * KPIs và danh sách gần nhất cho Dashboard.
 */
export async function getDashboardStats(): Promise<ApiResponse<DashboardStats>> {
  return frappeGet<ApiResponse<DashboardStats>>(`${BASE}.get_dashboard_stats`)
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
): Promise<ApiResponse<SaveResponse>> {
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
): Promise<ApiResponse<SaveResponse>> {
  return frappePost(`${BASE}.create_commissioning`, { data: JSON.stringify(data) })
}

// ─────────────────────────────────────────────────────────────────────────────
// 10. GET PO DETAILS (Auto-fill)
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Lấy thông tin PO để auto-fill vendor/model.
 */
export async function getPoDetails(poName: string): Promise<ApiResponse<PoDetails>> {
  return frappeGet<ApiResponse<PoDetails>>(`${BASE}.get_po_details`, { po_name: poName })
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
