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
  // HR / Employee fields (optional — chỉ có khi User được liên kết Employee)
  hr_docname?: string      // Employee.name (docname), VD: "HR-EMP-00001"
  hr_full_name?: string    // Employee.employee_name
  designation?: string
  erp_department?: string
  has_employee?: boolean
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

export interface FrappeUserItem {
  name: string
  full_name: string
  email: string
  user_image?: string | null
}

interface Paginated<T> {
  items: T[]
  pagination: { page: number; page_size: number; total: number; total_pages: number }
}

// ── Endpoints ──────────────────────────────────────────────────────────────────

export const listUsers = (params: {
  search?: string
  department?: string
  is_active?: number
  approval_status?: string
  page?: number
  page_size?: number
} = {}) => frappeGet<Paginated<IMMUserListItem>>(`${BASE}.list_users`, params as Record<string, unknown>)

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
  frappePost<{ user: string; full_name: string }>(`${BASE}.create_system_user`, {
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

export const getAvailableImmRoles = () =>
  frappeGet<Array<{ name: string; label: string }>>(`${BASE}.get_available_imm_roles`)

export const listFrappeUsers = (search: string = '', limit = 30) =>
  frappeGet<FrappeUserItem[]>(`${BASE}.list_frappe_users`, { search, limit })
