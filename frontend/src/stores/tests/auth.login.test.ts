// Copyright (c) 2026, AssetCore Team
//
// Regression guard — auth store login() failure/success invariants (IMM-00).
// Pin lại hành vi đã có để không hồi quy:
//   - /api/method/login 401 → login() trả false, loading về false, error≠null.
//   - success path → trả true, gọi fetchSession() rồi loadCapabilities().

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

// ── Mock collaborators ─────────────────────────────────────────────────────
const apiPost = vi.fn()
vi.mock('@/api/axios', () => ({
  default: { post: (...a: unknown[]) => apiPost(...a) },
  setCsrfToken: vi.fn(),
}))

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

describe('auth store login() — failure/success invariants (IMM-00)', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
    setActivePinia(createPinia())
  })

  it('AUTH-STORE-01: /api/method/login ném 401 → login()=false, loading=false, error≠null', async () => {
    apiPost.mockRejectedValue(new Error('Request failed with status code 401'))

    const auth = useAuthStore()
    const ok = await auth.login('user@x.test', 'wrongpass')

    expect(ok).toBe(false)
    expect(auth.loading).toBe(false) // finally đã reset — KHÔNG kẹt spinner
    expect(auth.error).not.toBeNull()
    // không gọi tiếp fetchSession khi /login đã ném
    expect(getUserContextMock).not.toHaveBeenCalled()
    expect(fetchCapabilitiesMock).not.toHaveBeenCalled()
  })

  it('AUTH-STORE-02: success path → login()=true, gọi fetchSession() rồi loadCapabilities()', async () => {
    apiPost.mockResolvedValue({ data: { csrf_token: 'tok-123' } })
    getUserContextMock.mockResolvedValue({
      user: 'user@x.test',
      full_name: 'User X',
      user_image: null,
      roles: ['AssetCore Technician'],
      role_profile_name: 'KTV Xưởng',
    } as never)
    fetchCapabilitiesMock.mockResolvedValue({ 'pm.write': true })

    const auth = useAuthStore()
    const ok = await auth.login('user@x.test', 'goodpass')

    expect(ok).toBe(true)
    expect(getUserContextMock).toHaveBeenCalledTimes(1) // fetchSession
    expect(fetchCapabilitiesMock).toHaveBeenCalled()    // loadCapabilities
    expect(auth.isAuthenticated).toBe(true)
    expect(auth.loading).toBe(false)
    expect(auth.can('pm.write')).toBe(true)
  })

  it('AUTH-STORE-03: login OK nhưng fetchSession fail → login()=false, KHÔNG load caps', async () => {
    apiPost.mockResolvedValue({ data: {} })
    getUserContextMock.mockRejectedValue(new Error('403 Forbidden'))

    const auth = useAuthStore()
    const ok = await auth.login('user@x.test', 'goodpass')

    expect(ok).toBe(false)
    expect(fetchCapabilitiesMock).not.toHaveBeenCalled()
    expect(auth.loading).toBe(false)
    expect(auth.isAuthenticated).toBe(false)
  })
})
