// Copyright (c) 2026, AssetCore Team
// IMM-00 User Management API — chuẩn Frappe User + Employee

import { frappeGet, frappePost } from '@/api/helpers'

const BASE = '/api/method/assetcore.api.user'

// ── Types ──────────────────────────────────────────────────────────────────────

export interface IMMUser {
  name: string
  full_name: string
  email: string
  phone?: string
  user_image?: string | null
  enabled: number
  is_active?: number
  imm_approval_status: 'Pending' | 'Approved' | 'Rejected'
  imm_approved_by?: string
  imm_approved_at?: string
  imm_rejection_reason?: string
  ac_department?: string
  department_name?: string
  imm_roles?: Array<{ role: string }>
  role_profile_name?: string | null
  // HR / Employee fields (optional — chỉ có khi User được liên kết Employee)
  hr_docname?: string      // Employee.name (docname), VD: "HR-EMP-00001"
  hr_full_name?: string    // Employee.employee_name
  designation?: string
  erp_department?: string
  has_employee?: boolean
}

export interface IMMUserRoleBadge { name: string; label: string; group: string }

export interface RoleProfileOption {
  name: string
  label: string
  roles: IMMUserRoleBadge[]
}

export interface IMMUserListItem {
  name: string
  full_name: string
  email: string
  enabled: number
  is_active?: number
  imm_approval_status?: string
  ac_department?: string
  department_name?: string
  user_image?: string | null
  imm_roles?: IMMUserRoleBadge[]
  role_profile_name?: string | null
}

export interface CreateUserPayload {
  email: string
  first_name: string
  last_name?: string
  password?: string
  phone?: string
  send_welcome_email?: boolean
  ac_department?: string
  imm_roles?: Array<{ role: string }>
}

/** Thông tin hiển thị của 1 user (read-by-id) — `get_ac_user_brief`. */
export interface AcUserBrief {
  name: string
  full_name: string
  email: string
  phone?: string | null
  mobile_no?: string | null
  user_image?: string | null
  enabled: number
  /** false = user cũ không còn thuộc AssetCore → FE gắn badge "(Đã rời AssetCore)". */
  is_ac_user: boolean
}

interface Paginated<T> {
  items: T[]
  pagination: { page: number; page_size: number; total: number; total_pages: number }
}

// ── Endpoints ──────────────────────────────────────────────────────────────────

export const listUsers = (params: {
  search?: string
  department?: string
  role?: string
  is_active?: number
  approval_status?: string
  page?: number
  page_size?: number
} = {}) => frappeGet<Paginated<IMMUserListItem>>(`${BASE}.list_users`, params as Record<string, unknown>)

/** Trần số trang kéo về — chặn vòng lặp vô hạn nếu BE trả `total` bất thường. */
const MAX_USER_PAGES = 50
const USER_PAGE_SIZE = 100

/**
 * Kéo TOÀN BỘ user AssetCore (đi hết các trang, BE cap page_size = 100).
 *
 * Dùng cho màn cần danh sách đầy đủ (gán role, map id → tên hiển thị). Không
 * cắt ngầm: lặp tới khi đủ `pagination.total`.
 */
export async function listAllUsers(): Promise<IMMUserListItem[]> {
  const out: IMMUserListItem[] = []
  for (let page = 1; page <= MAX_USER_PAGES; page++) {
    const res = await listUsers({ page, page_size: USER_PAGE_SIZE })
    out.push(...res.items)
    if (res.items.length === 0 || out.length >= res.pagination.total) break
  }
  return out
}

export const getUserInfo = (user: string) =>
  frappeGet<IMMUser>(`${BASE}.get_user_info`, { user })

export const updateUserInfo = (user: string, data: Partial<IMMUser>) =>
  frappePost<{ user: string }>(`${BASE}.update_user_info`, {
    user,
    ...data,
    imm_roles: data.imm_roles ? JSON.stringify(data.imm_roles) : undefined,
  } as Record<string, unknown>)

export const approveRegistration = (
  user: string,
  action: 'approve' | 'reject',
  roles?: Array<{ role: string }>,
  rejection_reason?: string,
) =>
  frappePost<{ user: string; status: string; enabled: number }>(`${BASE}.approve_registration`, {
    user, action,
    roles: roles ? JSON.stringify(roles) : '[]',
    rejection_reason: rejection_reason || '',
  })

export const createSystemUser = (payload: CreateUserPayload) =>
  frappePost<{
    user: string
    full_name: string
    // ISS-002: trạng thái gửi email chào mừng (chỉ có khi tick "Gửi email chào mừng").
    welcome_email_sent?: boolean
    welcome_email_error?: string
  }>(`${BASE}.create_system_user`, {
    ...payload,
    imm_roles: payload.imm_roles ? JSON.stringify(payload.imm_roles) : '[]',
  } as Record<string, unknown>)

export const updateUserRoles = (user: string, roles: Array<{ role: string }>) =>
  frappePost<{ user: string; imm_roles: string[] }>(`${BASE}.update_user_roles`, {
    user,
    roles: JSON.stringify(roles),
  })

export const resetUserPassword = (user: string, new_password: string) =>
  frappePost<{ user: string }>(`${BASE}.reset_user_password`, { user, new_password })

export const changeMyPassword = (old_password: string, new_password: string) =>
  frappePost<{ user: string }>(`${BASE}.change_my_password`, { old_password, new_password })

export interface ImmRoleOption {
  name: string
  label: string
  description: string
  group: string
}

export const getAvailableImmRoles = () =>
  frappeGet<ImmRoleOption[]>(`${BASE}.get_available_imm_roles`)

export const listRoleProfiles = () =>
  frappeGet<RoleProfileOption[]>(`${BASE}.list_role_profiles`)

export const assignRoleProfile = (user: string, role_profile: string) =>
  frappePost<{ user: string; role_profile: string | null; imm_roles: Array<{ role: string }> }>(
    `${BASE}.assign_role_profile`,
    { user, role_profile },
  )

/**
 * Thông tin hiển thị tối thiểu của 1 user (read-by-id) — thay cho gọi thẳng
 * `frappe.client.get_value` với doctype User ở view.
 *
 * Vẫn trả user KHÔNG còn thuộc AssetCore (record cũ phải render được tên) kèm
 * cờ `is_ac_user=false` để hiện badge "(Đã rời AssetCore)".
 */
export const getAcUserBrief = (user: string) =>
  frappeGet<AcUserBrief>(`${BASE}.get_ac_user_brief`, { user })

/** User AssetCore đủ năng lực cho 1 ngữ cảnh phân công (picker KTV…). */
export interface AssignableUserItem {
  name: string
  full_name: string
  email: string
  user_image?: string | null
}

/**
 * Liệt kê user AssetCore (có base role) ĐỦ NĂNG LỰC cho `context` phân công.
 * `context` = khoá allowlist BE (vd "repair"); BE lọc theo capability/DocPerm
 * (mirror _is_repair_capable) → chỉ hiện người hợp lệ để chọn.
 */
export const listAssignableUsers = (context: string, search = '', limit = 20) =>
  frappeGet<AssignableUserItem[]>(`${BASE}.list_assignable_users`, { context, search, limit })
