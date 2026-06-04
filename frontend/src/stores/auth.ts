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
const CAPS_VERSION_KEY = 'assetcore.capabilities_version'

const CAP_DOC_WRITE = 'doc' + 'ument.write'
const CAP_DOC_APPROVE = 'doc.approve'

// CAP_SET_VERSION = version-stamp của cap-catalog mà FE hiện biết. PHẢI KHỚP
// giá trị BE phát ra ở `__cap_version` (rbac.CAP_SET_VERSION = `vN.<sha256[:12]>`
// của sorted(CAPABILITY_MAP)). Khi cap-set BE đổi (thêm/đổi tên capability — vd
// decommission.* cho IMM-14) → BE version đổi → cập nhật hằng số NÀY cho khớp.
// Init-time: persisted-version (do lần BE response trước lưu) khác hằng số NÀY →
// coi là stale → bỏ persisted caps + ép loadCapabilities() (AC4). Khớp → giữ
// cache (không refetch thừa). Khi BE response tới, FE luôn persist version BE gửi
// (forward-compat FE-3); nếu BE chưa wire → fallback hằng số NÀY.
// SoT: assetcore/services/shared/rbac.py::CAP_SET_VERSION (bench execute
// assetcore.services.shared.rbac._compute_cap_set_version để lấy giá trị hiện tại).
export const CAP_SET_VERSION = 'v89.2df4c16c2bbd'

/**
 * SSoT cho quyết định invalidate cache caps theo version-stamp (FE-2/AC4).
 *
 * - persisted khác current  → stale → bỏ persisted caps, ép refetch.
 * - BE chưa trả version (current undefined) hoặc chưa từng persist version
 *   (undefined) → coi như STALE (forward-compat FE-3): luôn refetch, không throw.
 * - cùng version (cả 2 cùng giá trị, khác undefined) → KHÔNG stale (giữ cache,
 *   tránh refetch thừa khi version ổn định).
 */
export function isCapCacheStale(
  persistedVersion: string | undefined,
  currentVersion: string | undefined,
): boolean {
  if (persistedVersion === undefined || currentVersion === undefined) return true
  return persistedVersion !== currentVersion
}

interface PersistedSession {
  user: FrappeUser
  cachedAt: number
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref<FrappeUser | null>(loadPersistedUser())
  // `loading` = CHỈ phục vụ login-submit (spinner nút "Đăng nhập" + disable input
  // trong LoginView). KHÔNG dùng cho bootstrap/session-restore — nếu gộp chung,
  // full-screen overlay App.vue sẽ đè /login khi đang submit → LoginView remount
  // → mất field + banner (regression APP-AUTH-01).
  const loading = ref(false)
  // `bootstrapping` = CHỈ phục vụ phiên khôi phục lần đầu (App.vue onMounted →
  // fetchSession/ensureFresh). App.vue full-screen spinner "Đang khởi tạo..." chỉ
  // bật theo cờ này, KHÔNG theo `loading`. Tách 2 lifecycle khác nhau ra 2 cờ.
  const bootstrapping = ref(false)
  const error = ref<string | null>(null)
  // FE-2/AC4: nếu cap-set version đã đổi so với bản đã cache trong localStorage,
  // bỏ persisted caps NGAY lúc khởi tạo store — component đọc `can()` trước khi
  // loadCapabilities() chạy sẽ không dùng cap-set cũ (vd thiếu decommission.*).
  const capabilities = ref<Record<string, boolean>>(
    isCapCacheStale(loadPersistedVersion(), CAP_SET_VERSION) ? {} : loadPersistedCaps(),
  )

  const isAuthenticated = computed(() => user.value !== null)
  const roles = computed<string[]>(() => user.value?.roles ?? [])
  const roleProfileName = computed<string | null>(() => user.value?.role_profile_name ?? null)
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
      // FE-3 forward-compat: BE-3 có thể nhúng version-stamp vào payload qua key
      // `__cap_version`. Tách ra khỏi map boolean trước khi lưu để không lọt vào
      // can(); nếu BE chưa wire → version = FE constant (vẫn overwrite caps).
      const { version, map } = splitCapVersion(caps ?? {})
      capabilities.value = map
      persistCaps(map)
      persistVersion(version ?? CAP_SET_VERSION)
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
        role_profile_name: ctx.role_profile_name ?? null,
      }
      persistUser(user.value)
      // FE-1/AC3: LUÔN refresh caps khi khôi phục phiên — KHÔNG skip khi
      // capabilities.value đã non-empty. User được cấp quyền trước release (vd
      // IMM-14 decommission.*) đang giữ persisted-caps cũ sẽ được overwrite bằng
      // cap-set mới nhất từ BE (loadCapabilities đã overwrite+persist + version).
      await loadCapabilities()
      return true
    } catch (e) {
      user.value = null
      capabilities.value = {}
      localStorage.removeItem(SESSION_KEY)
      localStorage.removeItem(CAPS_KEY)
      localStorage.removeItem(CAPS_VERSION_KEY)
      error.value = e instanceof Error ? e.message : 'Loi xac thuc'
      return false
    } finally {
      loading.value = false
    }
  }

  /**
   * Re-hydrate roles / role_profile / capabilities từ BE cho phiên đã được
   * khôi phục từ localStorage. Chống persona "thiu" (stale) khi admin đổi
   * role-profile server-side trong khi cache FE (TTL 10') còn hiệu lực.
   *
   * KHÔNG block render: gọi không-await ở App mount. fetchSession sẽ tự null
   * user + bounce về login nếu phiên đã bị huỷ server-side.
   */
  async function ensureFresh(): Promise<void> {
    if (!isAuthenticated.value) return
    // fetchSession() đã LUÔN gọi loadCapabilities() (FE-1) → không refetch lần 2.
    await fetchSession()
  }

  /**
   * Bootstrap phiên lúc App mount (App.vue onMounted). Bật cờ `bootstrapping`
   * (KHÔNG phải `loading`) để full-screen spinner "Đang khởi tạo..." chỉ hiển thị
   * trong giai đoạn này — KHÔNG đè màn /login khi user đang submit form login.
   *
   * - Chưa auth → cố khôi phục phiên server-side (cookie) qua fetchSession().
   * - Đã có phiên cache (localStorage) → re-hydrate role/persona/caps ở nền.
   *
   * Trả về true nếu kết thúc ở trạng thái đã xác thực, false nếu cần về Login.
   */
  async function bootstrap(): Promise<boolean> {
    bootstrapping.value = true
    try {
      if (!isAuthenticated.value) {
        return await fetchSession()
      }
      await ensureFresh()
      return isAuthenticated.value
    } finally {
      bootstrapping.value = false
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
      localStorage.removeItem(CAPS_VERSION_KEY)
      globalThis.location.href = loginPath()
    }
  }

  function rememberedUsername(): string {
    return localStorage.getItem(REMEMBER_KEY) ?? ''
  }

  return {
    user, loading, bootstrapping, error,
    isAuthenticated, roles, roleProfileName, capabilities,
    isSystemAdmin, isQAOfficer, isDeptHead, isOpsManager,
    isWorkshopLead, isTechnician, isDocOfficer, hasAnyImmRole,
    canCreate, canSubmit, canApprove, canViewDashboard, canManageDocs,
    can,
    login, fetchSession, ensureFresh, bootstrap, logout, loadCapabilities,
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

function loadPersistedVersion(): string | undefined {
  return localStorage.getItem(CAPS_VERSION_KEY) ?? undefined
}

function persistVersion(version: string): void {
  try {
    localStorage.setItem(CAPS_VERSION_KEY, version)
  } catch {
    // ignore quota errors
  }
}

/**
 * Tách version-stamp khỏi cap-map. BE-3 (forward-compat) có thể nhúng version
 * vào payload qua key dành riêng `__cap_version` (kiểu string). Mọi key còn lại
 * coi là capability boolean. Nếu không có version → version = undefined (caller
 * fallback CAP_SET_VERSION). Không throw khi BE chưa wire (FE-3).
 */
function splitCapVersion(
  raw: Record<string, unknown>,
): { version: string | undefined; map: Record<string, boolean> } {
  const map: Record<string, boolean> = {}
  let version: string | undefined
  for (const [k, v] of Object.entries(raw)) {
    if (k === '__cap_version') {
      version = typeof v === 'string' ? v : undefined
      continue
    }
    map[k] = v === true
  }
  return { version, map }
}
