// Copyright (c) 2026, AssetCore Team
// Pinia store: user session, IMM roles, permission helpers.

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { logout as apiLogout } from '@/api/imm04'
import { getUserContext } from '@/api/layout'
import api, { setCsrfToken } from '@/api/axios'
import type { FrappeUser } from '@/types/imm04'
import {
  Roles,
  ALL_IMM_ROLES,
  ROLES_APPROVE,
  ROLES_CREATE,
  ROLES_MANAGE_DOCS,
} from '@/constants/roles'

// Re-export role constants cho backward compatibility với các component hiện có.
export const ROLE_SYS_ADMIN = Roles.SYS_ADMIN
export const ROLE_QA = Roles.QA
export const ROLE_DEPT_HEAD = Roles.DEPT_HEAD
export const ROLE_OPS_MANAGER = Roles.OPS_MANAGER
export const ROLE_WORKSHOP_LEAD = Roles.WORKSHOP
export const ROLE_TECHNICIAN = Roles.TECHNICIAN
export const ROLE_DOC_OFFICER = Roles.DOC_OFFICER

const SUBMIT_ROLES = [Roles.SYS_ADMIN, Roles.QA, Roles.DEPT_HEAD, Roles.OPS_MANAGER, Roles.WORKSHOP]
const CREATE_ROLES = ROLES_CREATE
const APPROVE_ROLES = ROLES_APPROVE

const REMEMBER_KEY = 'assetcore.remember_usr'
const SESSION_KEY = 'assetcore.session'

interface PersistedSession {
  user: FrappeUser
  cachedAt: number
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref<FrappeUser | null>(loadPersistedUser())
  const loading = ref(false)
  const error = ref<string | null>(null)

  const isAuthenticated = computed(() => user.value !== null)
  const roles = computed<string[]>(() => user.value?.roles ?? [])
  const roleSet = computed(() => new Set(roles.value))

  const hasRole = (role: string) => roleSet.value.has(role)
  const hasAnyRole = (checkRoles: readonly string[]) => checkRoles.some((r) => roleSet.value.has(r))

  const isSystemAdmin = computed(() => hasRole(ROLE_SYS_ADMIN))
  const isQAOfficer = computed(() => hasRole(ROLE_QA))
  const isDeptHead = computed(() => hasRole(ROLE_DEPT_HEAD))
  const isOpsManager = computed(() => hasRole(ROLE_OPS_MANAGER))
  const isWorkshopLead = computed(() => hasRole(ROLE_WORKSHOP_LEAD))
  const isTechnician = computed(() => hasRole(ROLE_TECHNICIAN))
  const isDocOfficer = computed(() => hasRole(ROLE_DOC_OFFICER))
  const hasAnyImmRole = computed(() => hasAnyRole(ALL_IMM_ROLES))

  const canCreate = computed(() => hasAnyRole(CREATE_ROLES))
  const canSubmit = computed(() => hasAnyRole(SUBMIT_ROLES))
  const canApprove = computed(() => hasAnyRole(APPROVE_ROLES))
  const canViewDashboard = computed(() => hasAnyImmRole.value)
  const canManageDocs = computed(() => hasAnyRole(ROLES_MANAGE_DOCS))

  async function login(usr: string, pwd: string, remember = false): Promise<boolean> {
    loading.value = true
    error.value = null
    try {
      const body = new URLSearchParams({ usr, pwd })
      const loginRes = await api.post<{ csrf_token?: string }>('/api/method/login', body, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      })
      if (loginRes.data?.csrf_token) setCsrfToken(loginRes.data.csrf_token)
      if (remember) localStorage.setItem(REMEMBER_KEY, usr)
      else localStorage.removeItem(REMEMBER_KEY)
      return await fetchSession()
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Đăng nhập thất bại'
      return false
    } finally {
      loading.value = false
    }
  }

  async function fetchSession(): Promise<boolean> {
    loading.value = true
    error.value = null
    try {
      // Dùng endpoint AssetCore thay vì gọi trực tiếp frappe.client.get
      const ctx = await getUserContext()
      user.value = {
        name: ctx.user,
        full_name: ctx.full_name,
        email: ctx.user,
        user_image: ctx.user_image,
        roles: ctx.roles,
      }
      persistUser(user.value)
      return true
    } catch (e) {
      user.value = null
      localStorage.removeItem(SESSION_KEY)
      error.value = e instanceof Error ? e.message : 'Lỗi xác thực'
      return false
    } finally {
      loading.value = false
    }
  }

  async function logout(): Promise<void> {
    try {
      await apiLogout()
    } finally {
      user.value = null
      localStorage.removeItem(SESSION_KEY)
      globalThis.location.href = '/login'
    }
  }

  function rememberedUsername(): string {
    return localStorage.getItem(REMEMBER_KEY) ?? ''
  }

  return {
    user, loading, error,
    isAuthenticated, roles,
    isSystemAdmin, isQAOfficer, isDeptHead, isOpsManager,
    isWorkshopLead, isTechnician, isDocOfficer, hasAnyImmRole,
    canCreate, canSubmit, canApprove, canViewDashboard, canManageDocs,
    login, fetchSession, logout,
    hasRole, hasAnyRole, rememberedUsername,
  }
})

function loadPersistedUser(): FrappeUser | null {
  try {
    const raw = localStorage.getItem(SESSION_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as PersistedSession
    const SESSION_TTL_MS = 10 * 60 * 1000  // 10 min — buộc re-verify trước khi Frappe session hết hạn
    if (Date.now() - parsed.cachedAt > SESSION_TTL_MS) return null
    return parsed.user
  } catch {
    return null
  }
}

function persistUser(u: FrappeUser): void {
  const payload: PersistedSession = { user: u, cachedAt: Date.now() }
  localStorage.setItem(SESSION_KEY, JSON.stringify(payload))
}
