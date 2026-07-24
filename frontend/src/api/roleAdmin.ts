// Copyright (c) 2026, AssetCore Team
// API client cho trang /admin/roles — catalog 30 role + gán role cho user.
//
// BE gate: capability `data.admin` (AssetCore Super Admin / Frappe System
// Manager qua umbrella). Mọi method dưới đều có thể bị BE 403 nếu user thiếu
// quyền — FE chỉ ẩn nút cho UX, gọi vẫn ổn vì BE chốt chặn.

import { frappeGet, frappePost } from './helpers'
import api from './axios'
import { listAllUsers as listAllAcUsers } from './user'

export interface AssignableRole {
  name: string
  label?: string
  description?: string
  group?: string
}

export interface SimpleUser {
  name: string
  full_name: string
}

const BASE = '/api/method/assetcore.api.user'

/** Catalog 30 role + metadata để hiển thị trang admin. */
export function listAssignableRoles(): Promise<AssignableRole[]> {
  return frappeGet<AssignableRole[]>(`${BASE}.list_assignable_roles`)
}

/**
 * Liệt kê user AssetCore để gán role.
 *
 * Nguồn = `assetcore.api.user.list_users` (lọc base role `AssetCore System User`)
 * — KHÔNG gọi `frappe.client.get_list doctype=User`: trên site cài chung
 * ERPNext/CRM lối đó xổ cả user không thuộc app (sự cố 2026-07-22).
 */
export async function listUsers(): Promise<SimpleUser[]> {
  const rows = await listAllAcUsers()
  return rows.map((u) => ({ name: u.name, full_name: u.full_name }))
}

/** Roles hiện tại của 1 user (kết quả Has Role trên User). */
export async function getUserRoles(user: string): Promise<string[]> {
  const res = await api.get<{ message: Array<{ role: string }> }>(
    '/api/method/frappe.client.get_list',
    {
      params: {
        doctype: 'Has Role',
        parent: 'User',
        filters: JSON.stringify([
          ['parent', '=', user],
          ['parenttype', '=', 'User'],
        ]),
        fields: JSON.stringify(['role']),
        limit_page_length: 0,
      },
    },
  )
  return (res.data.message ?? []).map((x) => x.role)
}

/** Thay toàn bộ AssetCore role của user (giữ role app khác). */
export function setUserRoles(user: string, roles: string[]): Promise<{ user: string; roles: string[] }> {
  return frappePost<{ user: string; roles: string[] }>(
    `${BASE}.set_user_roles`,
    { user, roles: JSON.stringify(roles) },
  )
}
