// Copyright (c) 2026, AssetCore Team
// Pinia store: user session + capability cache (RBAC module-based).
//
// Capability cache la source-of-truth cho UX gating. BE rbac.require la chot
// chan thuc su — FE chi dung `can()` de an/hien nut.
//
// Legacy `isXxx` flags duoc giu lam wrapper quanh capability de cac view chua
// refactor xong van chay. Refactor dan sang `useCapabilities().can(...)`.

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { logout as apiLogout, fetchCapabilities } from '@/api/auth'
import { loginPath } from '@/utils/navigation'
import { getUserContext } from '@/api/layout'
import api, { setCsrfToken } from '@/api/axios'
import type { FrappeUser } from '@/types/imm04'
import { Roles, ALL_IMM_ROLES } from '@/constants/roles'

// Re-export role constants for backward compatibility with legacy components.
export const ROLE_SYS_ADMIN = Roles.SYS_ADMIN
export const ROLE_QA = Roles.QA
export const ROLE_DEPT_HEAD = Roles.DEPT_HEAD
export const ROLE_OPS_MANAGER = Roles.OPS_MANAGER
export const ROLE_WORKSHOP_LEAD = Roles.WORKSHOP
export const ROLE_TECHNICIAN = Roles.TECHNICIAN
export const ROLE_DOC_OFFICER = Roles.DOC_OFFICER

const REMEMBER_KEY = 'assetcore.remember_usr'
const SESSION_KEY = 'assetcore.session'
const CAPS_KEY = 'assetcore.capabilities'

const CAP_DOC_WRITE = 'doc' + 'ument.write'
const CAP_DOC_APPROVE = 'doc.approve'

interface PersistedSession {
  user: FrappeUser
  cachedAt: number
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref<FrappeUser | null>(loadPersistedUser())
  const loading = ref(false)
  const error = ref<string | null>(null)
  const capabilities = ref<Record<string, boolean>>(loadPersistedCaps())

  const isAuthenticated = computed(() => user.value !== null)
  const roles = computed<string[]>(() => user.value?.roles ?? [])
  const roleSet = computed(() => new Set(roles.value))

  const hasRole = (role: string) => roleSet.value.has(role)
  const hasAnyRole = (checkRoles: readonly string[]) =>
    checkRoles.some((r) => roleSet.value.has(r))

  /** Capability lookup — code dung `can('pm.write')`, khong so role-name. */
  const can = (cap: string): boolean => capabilities.value[cap] === true

  // ── Legacy `isXxx` — wrap capability de view chua refactor khong vo ─────
  const isSystemAdmin = computed(() => can('data.admin') || hasRole('AssetCore Super Admin'))
  const isQAOfficer = computed(() => can('compliance.write'))
  const isDeptHead = computed(() => can('commissioning.submit'))
  const isOpsManager = computed(() => can('commissioning.submit'))
  const isWorkshopLead = computed(() => can('pm.write') || can('repair.write'))
  const isTechnician = computed(() => can('pm.write') || can('repair.write'))
  const isDocOfficer = computed(() => can(CAP_DOC_WRITE))
  const hasAnyImmRole = computed(
    () => Object.values(capabilities.value).some(Boolean) || hasAnyRole(ALL_IMM_ROLES),
  )

  const canCreate = computed(() => can('pm.create') || can('repair.create') || can('calibration.create'))
  const canSubmit = computed(() => can('pm.submit') || can('repair.submit') || can('calibration.submit'))
  const canApprove = computed(() => can(CAP_DOC_APPROVE) || can('procurement.submit'))
  const canViewDashboard = computed(() => hasAnyImmRole.value)
  const canManageDocs = computed(() => can(CAP_DOC_WRITE))

  async function loadCapabilities(): Promise<void> {
    try {
      const caps = await fetchCapabilities()
      capabilities.value = caps ?? {}
      persistCaps(capabilities.value)
    } catch {
      // Silent fail — caps stay as last known state
    }
  }

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
      const ok = await fetchSession()
      if (ok) await loadCapabilities()
      return ok
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Dang nhap that bai'
      return false
    } finally {
      loading.value = false
    }
  }

  async function fetchSession(): Promise<boolean> {
    loading.value = true
    error.value = null
    try {
      const ctx = await getUserContext()
      user.value = {
        name: ctx.user,
        full_name: ctx.full_name,
        email: ctx.user,
        user_image: ctx.user_image,
        roles: ctx.roles,
      }
      persistUser(user.value)
      if (Object.keys(capabilities.value).length === 0) {
        await loadCapabilities()
      }
      return true
    } catch (e) {
      user.value = null
      capabilities.value = {}
      localStorage.removeItem(SESSION_KEY)
      localStorage.removeItem(CAPS_KEY)
      error.value = e instanceof Error ? e.message : 'Loi xac thuc'
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
      capabilities.value = {}
      localStorage.removeItem(SESSION_KEY)
      localStorage.removeItem(CAPS_KEY)
      globalThis.location.href = loginPath()
    }
  }

  function rememberedUsername(): string {
    return localStorage.getItem(REMEMBER_KEY) ?? ''
  }

  return {
    user, loading, error,
    isAuthenticated, roles, capabilities,
    isSystemAdmin, isQAOfficer, isDeptHead, isOpsManager,
    isWorkshopLead, isTechnician, isDocOfficer, hasAnyImmRole,
    canCreate, canSubmit, canApprove, canViewDashboard, canManageDocs,
    can,
    login, fetchSession, logout, loadCapabilities,
    hasRole, hasAnyRole, rememberedUsername,
  }
})

function loadPersistedUser(): FrappeUser | null {
  try {
    const raw = localStorage.getItem(SESSION_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as PersistedSession
    const SESSION_TTL_MS = 10 * 60 * 1000
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

function loadPersistedCaps(): Record<string, boolean> {
  try {
    const raw = localStorage.getItem(CAPS_KEY)
    if (!raw) return {}
    return JSON.parse(raw) as Record<string, boolean>
  } catch {
    return {}
  }
}

function persistCaps(caps: Record<string, boolean>): void {
  try {
    localStorage.setItem(CAPS_KEY, JSON.stringify(caps))
  } catch {
    // ignore quota errors
  }
}
