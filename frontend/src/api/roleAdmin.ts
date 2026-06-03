// Copyright (c) 2026, AssetCore Team
// API client cho trang /admin/roles — catalog 30 role + gán role cho user.
//
// BE gate: capability `data.admin` (AssetCore Super Admin / Frappe System
// Manager qua umbrella). Mọi method dưới đều có thể bị BE 403 nếu user thiếu
// quyền — FE chỉ ẩn nút cho UX, gọi vẫn ổn vì BE chốt chặn.

import { frappeGet, frappePost } from './helpers'
import api from './axios'

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

/** Liệt kê System Users (enabled, không phải Website User). */
export async function listUsers(): Promise<SimpleUser[]> {
  const res = await api.get<{ message: SimpleUser[] }>(
    '/api/method/frappe.client.get_list',
    {
      params: {
        doctype: 'User',
        filters: JSON.stringify([
          ['enabled', '=', 1],
          ['user_type', '!=', 'Website User'],
        ]),
        fields: JSON.stringify(['name', 'full_name']),
        order_by: 'full_name asc',
        limit_page_length: 0,
      },
    },
  )
  return res.data.message ?? []
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
