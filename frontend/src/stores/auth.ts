// Copyright (c) 2026, AssetCore Team
// Pinia store: user session và roles

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getCurrentSession, logout as apiLogout } from '@/api/imm04'
import api, { setCsrfToken } from '@/api/axios'
import type { FrappeUser } from '@/types/imm04'

export const useAuthStore = defineStore('auth', () => {
  // ─── State ──────────────────────────────────────────────────────────────────
  const user = ref<FrappeUser | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  // ─── Getters ────────────────────────────────────────────────────────────────

  const isAuthenticated = computed(() => user.value !== null)

  const roles = computed<string[]>(() => user.value?.roles ?? [])

  const isHTMTechnician = computed(() => roles.value.includes('HTM Technician'))
  const isBiomedEngineer = computed(() => roles.value.includes('Biomed Engineer'))
  const isWorkshopHead = computed(() => roles.value.includes('Workshop Head'))
  const isVPBlock2 = computed(() => roles.value.includes('VP Block2'))
  const isQARiskTeam = computed(() => roles.value.includes('QA Risk Team'))
  const isCMMSAdmin = computed(() => roles.value.includes('CMMS Admin'))

  /** Có thể Submit phiếu (VP Block2 hoặc Workshop Head) */
  const canSubmit = computed(() => isVPBlock2.value || isWorkshopHead.value)

  /** Có thể tạo phiếu (HTM Technician) */
  const canCreate = computed(() => isHTMTechnician.value)

  /** Có quyền xem dashboard đầy đủ */
  const canViewDashboard = computed(
    () => isWorkshopHead.value || isVPBlock2.value || isQARiskTeam.value || isCMMSAdmin.value,
  )

  // ─── Actions ────────────────────────────────────────────────────────────────

  async function login(usr: string, pwd: string): Promise<boolean> {
    loading.value = true
    error.value = null
    try {
      // Frappe login endpoint yêu cầu form-encoded, không phải JSON
      const body = new URLSearchParams({ usr, pwd })
      const loginRes = await api.post<{ csrf_token?: string }>('/api/method/login', body, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      })
      // Frappe trả csrf_token trong response body — cache để dùng cho các POST tiếp theo
      if (loginRes.data?.csrf_token) {
        setCsrfToken(loginRes.data.csrf_token)
      }
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
      const session = await getCurrentSession()
      user.value = {
        name: session.name,
        full_name: session.full_name,
        email: session.name, // Frappe dùng email làm user name
        user_image: session.user_image,
        roles: session.roles,
      }
      return true
    } catch (e) {
      user.value = null
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
      globalThis.location.href = '/login'
    }
  }

  function hasRole(role: string): boolean {
    return roles.value.includes(role)
  }

  function hasAnyRole(checkRoles: string[]): boolean {
    return checkRoles.some((r) => roles.value.includes(r))
  }

  return {
    // State
    user,
    loading,
    error,
    // Getters
    isAuthenticated,
    roles,
    isHTMTechnician,
    isBiomedEngineer,
    isWorkshopHead,
    isVPBlock2,
    isQARiskTeam,
    isCMMSAdmin,
    canSubmit,
    canCreate,
    canViewDashboard,
    // Actions
    login,
    fetchSession,
    logout,
    hasRole,
    hasAnyRole,
  }
})
