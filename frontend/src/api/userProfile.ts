// AssetCore — AC User Profile API client
import { frappeGet, frappePost } from './helpers'
import type { PaginatedResponse } from '@/types/imm00'

export interface ACUserRole {
  role: string
  notes?: string
}

export interface ACUserCertification {
  cert_name: string
  cert_number?: string
  issuer?: string
  issued_date?: string
  expiry_date?: string
}

export interface ACUserProfile {
  name: string
  user: string
  full_name?: string
  email?: string
  employee_code?: string
  job_title?: string
  phone?: string
  department?: string
  location?: string
  is_active?: 0 | 1
  approval_status?: 'Pending' | 'Approved' | 'Rejected'
  notes?: string
  imm_roles?: ACUserRole[]
  certifications?: ACUserCertification[]
  modified?: string
  // Trả về từ get_profile
  is_synth?: 0 | 1   // 1 = User tồn tại nhưng AC User Profile chưa được tạo
  frappe_roles?: string[]
}

export interface FrappeUserItem {
  name: string
  full_name: string
  email: string
  user_image: string | null
  has_profile: 0 | 1
}

export interface ACUserProfileListItem {
  name: string
  user: string
  full_name?: string
  email?: string
  employee_code?: string
  job_title?: string
  department?: string
  department_name?: string
  location?: string
  is_active?: 0 | 1
  modified?: string
}

const BASE = '/api/method/assetcore.api.user_profile'

export function listProfiles(params: {
  search?: string; department?: string; is_active?: number;
  page?: number; page_size?: number
} = {}): Promise<PaginatedResponse<ACUserProfileListItem>> {
  return frappeGet(`${BASE}.list_profiles`, params as Record<string, unknown>)
}

export function getProfile(name: string): Promise<ACUserProfile> {
  return frappeGet(`${BASE}.get_profile`, { name })
}

export function upsertProfile(data: Partial<ACUserProfile>): Promise<{ name: string; user: string }> {
  const payload: Record<string, unknown> = { ...data }
  if (data.imm_roles) payload.imm_roles = JSON.stringify(data.imm_roles)
  if (data.certifications) payload.certifications = JSON.stringify(data.certifications)
  return frappePost(`${BASE}.upsert_profile`, payload)
}

export function getAvailableImmRoles(): Promise<Array<{ name: string; label: string }>> {
  return frappeGet(`${BASE}.get_available_imm_roles`)
}

export function getMyProfile(): Promise<{ user: string; profile: ACUserProfile | null }> {
  return frappeGet(`${BASE}.get_my_profile`)
}

export function listFrappeUsers(search = '', limit = 30): Promise<FrappeUserItem[]> {
  return frappeGet(`${BASE}.list_frappe_users`, { search, limit })
}

export function resetUserPassword(user: string, newPassword: string): Promise<{ user: string; reset_by: string }> {
  return frappePost(`${BASE}.reset_user_password`, { user, new_password: newPassword })
}

export function changeMyPassword(oldPassword: string, newPassword: string): Promise<{ user: string }> {
  return frappePost(`${BASE}.change_my_password`, { old_password: oldPassword, new_password: newPassword })
}
