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

export function approveRegistration(
  profileName: string,
  roles?: string[],
  rejectionReason?: string,
): Promise<{ profile: string; status: string }> {
  return frappePost(`${BASE}.approve_registration`, {
    profile_name: profileName,
    roles,
    rejection_reason: rejectionReason,
  })
}
