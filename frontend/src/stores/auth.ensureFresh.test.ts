// Copyright (c) 2026, AssetCore Team
// Vòng 8 (factory 6-10) — backlog #3: chống persona "stale".
//
// Khi phiên được khôi phục từ localStorage (TTL còn hiệu lực), App mount phải
// re-hydrate roles / role_profile / capabilities từ BE qua ensureFresh() —
// KHÔNG chỉ tin localStorage. Nếu phiên đã bị huỷ server-side → user về null.

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('@/api/layout', () => ({
  getUserContext: vi.fn(),
}))
vi.mock('@/api/auth', () => ({
  fetchCapabilities: vi.fn(),
  logout: vi.fn(),
}))

import { getUserContext } from '@/api/layout'
import { fetchCapabilities } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'

const getUserContextMock = vi.mocked(getUserContext)
const fetchCapabilitiesMock = vi.mocked(fetchCapabilities)

function seedSession(roles: string[], roleProfile: string | null) {
  localStorage.setItem(
    'assetcore.session',
    JSON.stringify({
      user: {
        name: 'tech@assetcore.test',
        full_name: 'Tech',
        email: 'tech@assetcore.test',
        roles,
        role_profile_name: roleProfile,
      },
      cachedAt: Date.now(),
    }),
  )
}

describe('auth.ensureFresh — re-hydrate persona/role từ BE', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
    setActivePinia(createPinia())
  })

  it('ghi đè roles/role_profile stale từ localStorage bằng dữ liệu BE', async () => {
    // localStorage: persona cũ (chỉ Technician)
    seedSession(['AssetCore Technician'], 'KTV Xưởng')
    // BE: admin đã nâng role-profile → Workshop Lead
    getUserContextMock.mockResolvedValue({
      user: 'tech@assetcore.test',
      full_name: 'Tech',
      user_image: null,
      roles: ['AssetCore Technician', 'AssetCore Workshop Lead'],
      role_profile_name: 'Trưởng Xưởng',
    } as never)
    fetchCapabilitiesMock.mockResolvedValue({ 'pm.write': true, 'repair.write': true })

    const auth = useAuthStore()
    expect(auth.isAuthenticated).toBe(true) // hydrate từ cache trước
    expect(auth.roles).toEqual(['AssetCore Technician']) // stale

    await auth.ensureFresh()

    expect(getUserContextMock).toHaveBeenCalledTimes(1)
    expect(auth.roles).toContain('AssetCore Workshop Lead') // đã refresh
    expect(auth.roleProfileName).toBe('Trưởng Xưởng')
    expect(auth.can('repair.write')).toBe(true)
  })

  it('phiên bị huỷ server-side → ensureFresh null-hoá user', async () => {
    seedSession(['AssetCore Technician'], 'KTV Xưởng')
    getUserContextMock.mockRejectedValue(new Error('403 Forbidden'))

    const auth = useAuthStore()
    expect(auth.isAuthenticated).toBe(true)

    await auth.ensureFresh()

    expect(auth.isAuthenticated).toBe(false)
    expect(localStorage.getItem('assetcore.session')).toBeNull()
  })

  it('không gọi BE khi chưa đăng nhập (no-op)', async () => {
    const auth = useAuthStore()
    expect(auth.isAuthenticated).toBe(false)
    await auth.ensureFresh()
    expect(getUserContextMock).not.toHaveBeenCalled()
  })
})
