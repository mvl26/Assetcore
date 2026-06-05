// Copyright (c) 2026, AssetCore Team
//
// IMM-00 / RBAC capability resolution (shared) — đóng USER REWORK IMM-14.
// Stale-safe capability resolution phía FE:
//   - FE-1/AC3: fetchSession() LUÔN gọi loadCapabilities() (không skip khi
//     capabilities.value đã non-empty) → user provisioned trước release không
//     bị kẹt persisted-caps cũ thiếu decommission.*.
//   - FE-2/AC4: version-stamp invalidate — persisted version ≠ current → bỏ
//     persisted caps + ép refetch (SSoT isCapCacheStale).
//   - FE-3: forward-compat — BE chưa trả version → FE vẫn overwrite mỗi
//     ensureFresh, không throw, không blank.

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
import { useAuthStore, isCapCacheStale, CAP_SET_VERSION } from '@/stores/auth'

const getUserContextMock = vi.mocked(getUserContext)
const fetchCapabilitiesMock = vi.mocked(fetchCapabilities)

const SESSION_KEY = 'assetcore.session'
const CAPS_KEY = 'assetcore.capabilities'
const CAPS_VERSION_KEY = 'assetcore.capabilities_version'

function seedSession(roles: string[] = ['AssetCore Ops Manager']) {
  localStorage.setItem(
    SESSION_KEY,
    JSON.stringify({
      user: {
        name: 'ops@assetcore.test',
        full_name: 'Ops',
        email: 'ops@assetcore.test',
        roles,
        role_profile_name: 'Quản lý vận hành',
      },
      cachedAt: Date.now(),
    }),
  )
}

function ctxResolved() {
  getUserContextMock.mockResolvedValue({
    user: 'ops@assetcore.test',
    full_name: 'Ops',
    user_image: null,
    roles: ['AssetCore Ops Manager'],
    role_profile_name: 'Quản lý vận hành',
  } as never)
}

describe('auth caps — stale-safe capability resolution (IMM-00 / IMM-14 rework)', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
    setActivePinia(createPinia())
  })

  // TC-FE-CAP-01 (RED-prove): persisted caps non-empty NHƯNG thiếu decommission.*
  // → fetchSession PHẢI vẫn gọi loadCapabilities → caps sau đó CHỨA decommission.*
  it('TC-FE-CAP-01: fetchSession overwrite persisted-caps cũ (thiếu decommission.*) bằng cap-set mới', async () => {
    seedSession()
    // persisted-caps cũ (provisioned trước release IMM-14) — KHÔNG có decommission.*
    localStorage.setItem(CAPS_KEY, JSON.stringify({ 'pm.read': true, 'pm.write': true }))
    localStorage.setItem(CAPS_VERSION_KEY, CAP_SET_VERSION) // version khớp → không bị drop lúc init
    ctxResolved()
    // BE trả cap-set mới có decommission.*
    fetchCapabilitiesMock.mockResolvedValue({
      'pm.read': true,
      'pm.write': true,
      'decommission.read': true,
      'decommission.create': true,
      'decommission.approve': true,
    })

    const auth = useAuthStore()
    // pre: caps cũ KHÔNG có decommission.create
    expect(auth.can('decommission.create')).toBe(false)

    await auth.fetchSession()

    // loadCapabilities ĐÃ chạy dù caps đã non-empty
    expect(fetchCapabilitiesMock).toHaveBeenCalledTimes(1)
    expect(auth.can('decommission.create')).toBe(true)
    expect(auth.can('decommission.approve')).toBe(true)
    // localStorage caps đã overwrite
    const persisted = JSON.parse(localStorage.getItem(CAPS_KEY) as string)
    expect(persisted['decommission.create']).toBe(true)
  })

  // TC-FE-CAP-02: version-stamp invalidate.
  it('TC-FE-CAP-02: isCapCacheStale — version khác → stale; cùng version → không stale', () => {
    expect(isCapCacheStale('v-old', 'v-new')).toBe(true)
    expect(isCapCacheStale(CAP_SET_VERSION, CAP_SET_VERSION)).toBe(false)
  })

  it('TC-FE-CAP-02b: persisted version cũ → caps cũ bị DROP lúc init store (không dùng can() stale)', () => {
    seedSession()
    localStorage.setItem(CAPS_KEY, JSON.stringify({ 'pm.read': true }))
    localStorage.setItem(CAPS_VERSION_KEY, 'v-cu-truoc-imm14') // ≠ CAP_SET_VERSION

    const auth = useAuthStore()
    // caps cũ bị bỏ ngay khi khởi tạo → can() không trả cap stale
    expect(auth.can('pm.read')).toBe(false)
    expect(Object.keys(auth.capabilities)).toHaveLength(0)
  })

  it('TC-FE-CAP-02c: cùng version → giữ persisted caps lúc init (không mất cache, không refetch thừa)', () => {
    seedSession()
    localStorage.setItem(CAPS_KEY, JSON.stringify({ 'pm.read': true }))
    localStorage.setItem(CAPS_VERSION_KEY, CAP_SET_VERSION)

    const auth = useAuthStore()
    expect(auth.can('pm.read')).toBe(true) // giữ cache
    // fetchCapabilities chưa được gọi (chỉ init, chưa ensureFresh)
    expect(fetchCapabilitiesMock).not.toHaveBeenCalled()
  })

  // TC-FE-CAP-03 (forward-compat): BE chưa trả version → FE vẫn overwrite caps,
  // không throw, không blank; persist version = CAP_SET_VERSION (fallback).
  it('TC-FE-CAP-03: BE chưa wire version → ensureFresh overwrite caps an toàn (no-throw)', async () => {
    seedSession()
    ctxResolved()
    // payload KHÔNG có __cap_version (BE-3 chưa land)
    fetchCapabilitiesMock.mockResolvedValue({
      'decommission.create': true,
      'decommission.approve': true,
    })

    const auth = useAuthStore()
    await expect(auth.ensureFresh()).resolves.toBeUndefined() // no-throw
    expect(auth.can('decommission.create')).toBe(true)
    // version fallback persisted
    expect(localStorage.getItem(CAPS_VERSION_KEY)).toBe(CAP_SET_VERSION)
  })

  it('TC-FE-CAP-03b: BE nhúng __cap_version → FE tách version, không lọt vào can()', async () => {
    seedSession()
    ctxResolved()
    fetchCapabilitiesMock.mockResolvedValue({
      __cap_version: 'be-version-99',
      'decommission.create': true,
    } as never)

    const auth = useAuthStore()
    await auth.ensureFresh()

    expect(auth.can('decommission.create')).toBe(true)
    // __cap_version KHÔNG trở thành capability
    expect(auth.can('__cap_version')).toBe(false)
    expect(localStorage.getItem(CAPS_VERSION_KEY)).toBe('be-version-99')
  })

  it('TC-FE-CAP-03c: ensureFresh re-hydrate persisted caps mỗi lần (FE-1 honored qua ensureFresh)', async () => {
    seedSession()
    localStorage.setItem(CAPS_KEY, JSON.stringify({ 'pm.read': true }))
    localStorage.setItem(CAPS_VERSION_KEY, CAP_SET_VERSION)
    ctxResolved()
    fetchCapabilitiesMock.mockResolvedValue({
      'decommission.read': true,
      'decommission.create': true,
      'decommission.approve': true,
    })

    const auth = useAuthStore()
    await auth.ensureFresh()

    // caps mới CHỨA decommission.* (overwrite, không merge cap cũ)
    expect(auth.can('decommission.read')).toBe(true)
    expect(auth.can('pm.read')).toBe(false) // cap cũ bị overwrite, không còn
    const persisted = JSON.parse(localStorage.getItem(CAPS_KEY) as string)
    expect(persisted['decommission.read']).toBe(true)
  })
})
