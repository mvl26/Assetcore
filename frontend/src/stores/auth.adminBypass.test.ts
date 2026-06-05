// Copyright (c) 2026, AssetCore Team
//
// B (hardening / RBAC SSoT — affordance↔route parity):
// Thống nhất SSoT phân quyền FE — admin-bypass nhất quán giữa route-guard
// (resolveRouteAccess rule #1) và button-gate (auth.can / useCapabilities.can).
//
// Split-brain trước fix: `routeAccess.ts` admin-bypass (isFrappeAdmin → allow)
// NHƯNG `auth.can(cap) = capabilities[cap]===true` KHÔNG bypass → Super Admin với
// cap-set rỗng `asset.*` VÀO được route (AssetLabelPrint/AssetDetail) nhưng nút
// QR/print BỊ ẨN (can('asset.write')=false). Nav-vào-được nhưng action biến mất.
//
// Fix (1 SSoT): auth.can(cap) = isFrappeAdmin || capabilities[cap]===true.
// Tiêu chí admin-role dùng CHUNG hằng FRAPPE_ADMIN_ROLES (constants/roles.ts) với
// router/index.ts → KHÔNG lặp literal mảng role 2 nơi (chống drift).

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('@/api/layout', () => ({ getUserContext: vi.fn() }))
vi.mock('@/api/auth', () => ({ fetchCapabilities: vi.fn(), logout: vi.fn() }))

import { useAuthStore } from '@/stores/auth'
import { resolveRouteAccess } from '@/router/routeAccess'
import { FRAPPE_ADMIN_ROLES } from '@/constants/roles'

/** Bơm trực tiếp state (roles + cap-set) — test thuần hành vi can(), bỏ nhiễu stale/localStorage. */
function withUser(roles: string[], caps: Record<string, boolean> = {}) {
  const auth = useAuthStore()
  auth.user = {
    name: 'u@assetcore.test', full_name: 'U', email: 'u@assetcore.test',
    roles, role_profile_name: null,
  } as never
  auth.capabilities = caps
  return auth
}

describe('auth.can — admin-bypass SSoT (B affordance↔route parity)', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
    setActivePinia(createPinia())
  })

  // [RED trước fix] user 'AssetCore Super Admin' + caps={} → can('asset.write')===true
  it('Super Admin (role) + cap-set rỗng → can(asset.write)=true (admin-bypass)', () => {
    const auth = withUser(['AssetCore Super Admin'], {})
    expect(auth.can('asset.write')).toBe(true)
  })

  it('System Manager + cap-set rỗng → mọi cap bypass (read & delete)', () => {
    const auth = withUser(['System Manager'], {})
    expect(auth.can('asset.read')).toBe(true)
    expect(auth.can('asset.delete')).toBe(true)
    expect(auth.can('pm.write')).toBe(true)
    expect(auth.can('anything.at.all')).toBe(true)
  })

  it('Administrator (Frappe core) + cap-set rỗng → bypass', () => {
    const auth = withUser(['Administrator'], {})
    expect(auth.can('asset.write')).toBe(true)
  })

  // Regression: non-admin vẫn THUẦN-CAP (KHÔNG nới quyền).
  it('non-admin (asset.read only) → can(asset.read)=true, can(asset.write)=false', () => {
    const auth = withUser(['Data User'], { 'asset.read': true })
    expect(auth.can('asset.read')).toBe(true)
    expect(auth.can('asset.write')).toBe(false)
    expect(auth.can('asset.delete')).toBe(false)
  })

  it('non-admin có asset.write → giữ nguyên (true) + write-only KHÔNG kéo theo cap khác', () => {
    const auth = withUser(['Data Manager'], { 'asset.write': true })
    expect(auth.can('asset.write')).toBe(true)
    expect(auth.can('asset.delete')).toBe(false) // chỉ true cap mới true
  })

  // Parity meta-test: 2 SSoT đồng thuận cho CÙNG (user, capability).
  describe('SSoT parity — route-gate VÀ button-gate trả CÙNG decision', () => {
    function routeCtx(auth: ReturnType<typeof useAuthStore>) {
      const isFrappeAdmin = auth.hasAnyRole(FRAPPE_ADMIN_ROLES)
      return {
        isFrappeAdmin,
        can: (cap: string) => auth.can(cap),
        hasAnyRole: (r: readonly string[]) => auth.hasAnyRole(r),
      }
    }

    it('admin-role + 0 cap: route AssetLabelPrint=allow VÀ can(asset.write)=true (đồng thuận)', () => {
      const auth = withUser(['AssetCore Super Admin'], {})
      const route = resolveRouteAccess({ requiredCapabilities: ['asset.write'] }, routeCtx(auth))
      expect(route).toBe('allow')
      expect(auth.can('asset.write')).toBe(true)
      // 2 cổng đồng thuận (chống tái phát split-brain)
      expect(route === 'allow').toBe(auth.can('asset.write'))
    })

    it('non-admin chỉ-đọc: route AssetLabelPrint=unauthorized VÀ can(asset.write)=false (đồng thuận)', () => {
      const auth = withUser(['Data User'], { 'asset.read': true })
      const route = resolveRouteAccess({ requiredCapabilities: ['asset.write'] }, routeCtx(auth))
      expect(route).toBe('unauthorized')
      expect(auth.can('asset.write')).toBe(false)
      expect(route === 'allow').toBe(auth.can('asset.write'))
    })

    it('non-admin có asset.write: route=allow VÀ can(asset.write)=true (đồng thuận, regression)', () => {
      const auth = withUser(['Data Manager'], { 'asset.write': true })
      const route = resolveRouteAccess({ requiredCapabilities: ['asset.write'] }, routeCtx(auth))
      expect(route).toBe('allow')
      expect(auth.can('asset.write')).toBe(true)
      expect(route === 'allow').toBe(auth.can('asset.write'))
    })
  })
})
