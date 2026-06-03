// Copyright (c) 2026, AssetCore Team
// API client: đăng ký, profile, đổi mật khẩu, duyệt user.

import api from './axios'
import { frappeGet, frappePost } from './helpers'

/**
 * Logout khỏi Frappe session (Frappe core endpoint).
 */
export async function logout(): Promise<void> {
  await api.get('/api/method/logout')
}

export interface RegisterPayload {
  email: string
  full_name: string
  password: string
  phone?: string
  department?: string
  employee_code?: string
  job_title?: string
}

export interface RegisterResult {
  user: string
  pending_approval: boolean
  message: string
}

export interface UserProfileResult {
  user: { name: string; full_name: string; email: string; user_image?: string | null }
  roles: string[]
  profile: {
    user: string
    full_name: string
    email: string
    phone?: string
    ac_department?: string
    department_name?: string
    imm_approval_status: 'Pending' | 'Approved' | 'Rejected'
    designation?: string
    hr_docname?: string
  } | null
  permissions: {
    is_admin: boolean
    can_create_wo: boolean
    can_approve: boolean
    can_manage_docs: boolean
  }
}

const BASE = '/api/method/assetcore.api.auth'

export function registerUser(payload: RegisterPayload): Promise<RegisterResult> {
  return frappePost<RegisterResult>(`${BASE}.register_user`, payload as unknown as Record<string, unknown>)
}

export function getUserProfile(): Promise<UserProfileResult> {
  return frappeGet<UserProfileResult>(`${BASE}.get_user_profile`)
}

export function updateMyProfile(updates: Record<string, string>): Promise<{ updated_fields: string[] }> {
  return frappePost(`${BASE}.update_my_profile`, updates)
}

export function changePassword(oldPassword: string, newPassword: string): Promise<{ message: string }> {
  return frappePost(`${BASE}.change_password`, { old_password: oldPassword, new_password: newPassword })
}

/**
 * Resolve toàn bộ capability cho user hiện tại — FE cache 1 lần sau login.
 * Trả map { 'pm.read': true, 'incident.acknowledge': false, ... }.
 * BE chốt chặn (rbac.require) — FE chỉ ẩn/hiện cho UX.
 */
export function fetchCapabilities(): Promise<Record<string, boolean>> {
  return frappeGet<Record<string, boolean>>(`${BASE}.get_capabilities`)
}

/**
 * BR-00-USR-02 (security 2026-06-01): tra trạng thái tài khoản — PASSWORD-GATED.
 *
 * Sau khi `/api/method/login` fail, LoginView gọi endpoint này với CHÍNH mật
 * khẩu user vừa nhập. BE chỉ lộ pending/rejected/disabled/active SAU KHI mật
 * khẩu đúng; sai mật khẩu HOẶC email không tồn tại → 'invalid_credentials'
 * (không phân biệt được → đóng user enumeration).
 *   - 'pending'             → tài khoản chờ quản trị viên duyệt
 *   - 'rejected'            → tài khoản đã bị từ chối
 *   - 'disabled'           → tài khoản bị vô hiệu hoá
 *   - 'active'             → mật khẩu đúng, tài khoản bình thường (login fail vì
 *                            lý do khác: 2FA / IP / giờ login)
 *   - 'invalid_credentials' → sai email/mật khẩu (message trung lập)
 * BE không trả mật khẩu/role/dữ liệu nhạy cảm — chỉ 1 nhãn coarse-grained.
 */
export type AccountState = 'pending' | 'rejected' | 'disabled' | 'active' | 'invalid_credentials'

export function accountState(usr: string, pwd: string): Promise<{ status: AccountState }> {
  return frappePost<{ status: AccountState }>(`${BASE}.account_state`, { usr, pwd })
}
