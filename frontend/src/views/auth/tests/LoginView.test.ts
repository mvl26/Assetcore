// Copyright (c) 2026, AssetCore Team
//
// Regression guard — IMM-00 auth surface (LoginView failure UX).
// Acceptance: mỗi nhánh login-fail PHẢI surface đúng banner; KHÔNG nhánh nào để
// form đứng im không message. Assert qua @vue/test-utils (DOM thật), không chỉ
// assert biến nội bộ.
//
// BE contract (KHÔNG sửa vòng này): account_state(usr,pwd) PASSWORD-GATED trả
// {status: pending|rejected|disabled|active|invalid_credentials}.

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

// ── Mock collaborators ─────────────────────────────────────────────────────
const loginMock = vi.fn()
const rememberedUsernameMock = vi.fn(() => '')
const authState = { loading: false, error: null as string | null, isAuthenticated: false }

vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({
    get loading() { return authState.loading },
    get error() { return authState.error },
    get isAuthenticated() { return authState.isAuthenticated },
    login: loginMock,
    rememberedUsername: rememberedUsernameMock,
  }),
}))

vi.mock('@/api/auth', () => ({
  accountState: vi.fn(),
}))

const routerPush = vi.fn()
let routeQuery: Record<string, string> = {}
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: routerPush }),
  useRoute: () => ({ query: routeQuery }),
}))

// Stub asset import — Vitest không resolve PNG.
vi.mock('@/assets/logo-miyano.png', () => ({ default: 'logo.png' }))

import LoginView from '@/views/auth/LoginView.vue'
import { accountState } from '@/api/auth'

const accountStateMock = vi.mocked(accountState)

const RouterLinkStub = {
  name: 'RouterLink',
  props: ['to'],
  template: '<a><slot /></a>',
}

function mountLogin() {
  return mount(LoginView, { global: { stubs: { RouterLink: RouterLinkStub } } })
}

async function fillAndSubmit(w: ReturnType<typeof mountLogin>, email: string, pwd: string) {
  if (email !== null) await w.find('#login-email').setValue(email)
  if (pwd !== null) await w.find('#login-password').setValue(pwd)
  await w.find('form').trigger('submit.prevent')
  await flushPromises()
}

const banner = (w: ReturnType<typeof mountLogin>) => {
  // Banner = div có v-if="error"; chứa <p> message. Tìm <p> trong block lỗi.
  const ps = w.findAll('p').map((p) => p.text())
  return ps
}

describe('LoginView — regression guard surface reject reason (IMM-00)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    authState.loading = false
    authState.error = null
    authState.isAuthenticated = false
    routeQuery = {}
    rememberedUsernameMock.mockReturnValue('')
  })

  it('LV-FE-01: thiếu password → validation banner, KHÔNG gọi auth.login()', async () => {
    const w = mountLogin()
    await w.find('#login-email').setValue('user@x.test')
    // password để trống
    await w.find('form').trigger('submit.prevent')
    await flushPromises()

    expect(loginMock).not.toHaveBeenCalled()
    expect(w.text()).toContain('Vui lòng nhập đầy đủ email và mật khẩu.')
  })

  it('LV-FE-01b: thiếu email → validation banner, KHÔNG gọi auth.login()', async () => {
    const w = mountLogin()
    await w.find('#login-password').setValue('secret')
    await w.find('form').trigger('submit.prevent')
    await flushPromises()

    expect(loginMock).not.toHaveBeenCalled()
    expect(w.text()).toContain('Vui lòng nhập đầy đủ email và mật khẩu.')
  })

  it('LV-FE-02: login false + invalid_credentials → banner sai mật khẩu + viền đỏ 2 input', async () => {
    loginMock.mockResolvedValue(false)
    accountStateMock.mockResolvedValue({ status: 'invalid_credentials' })

    const w = mountLogin()
    await fillAndSubmit(w, 'user@x.test', 'wrongpass')

    expect(w.text()).toContain('Sai email hoặc mật khẩu. Vui lòng thử lại.')
    // viền đỏ cho CẢ email + password
    expect(w.find('#login-email').classes()).toContain('border-red-400')
    expect(w.find('#login-password').classes()).toContain('border-red-400')
  })

  it('LV-FE-03: login false + status pending → banner chờ phê duyệt', async () => {
    loginMock.mockResolvedValue(false)
    accountStateMock.mockResolvedValue({ status: 'pending' })

    const w = mountLogin()
    await fillAndSubmit(w, 'pending@x.test', 'rightpass')

    expect(w.text()).toContain('chờ quản trị viên phê duyệt')
    // pending KHÔNG phải sai-credential → không viền đỏ
    expect(w.find('#login-email').classes()).not.toContain('border-red-400')
  })

  it('LV-FE-04: login false + status rejected → banner bị từ chối', async () => {
    loginMock.mockResolvedValue(false)
    accountStateMock.mockResolvedValue({ status: 'rejected' })

    const w = mountLogin()
    await fillAndSubmit(w, 'rejected@x.test', 'rightpass')

    expect(w.text()).toContain('Đăng ký của bạn đã bị từ chối')
  })

  it('LV-FE-05: login false + status disabled → banner vô hiệu hoá', async () => {
    loginMock.mockResolvedValue(false)
    accountStateMock.mockResolvedValue({ status: 'disabled' })

    const w = mountLogin()
    await fillAndSubmit(w, 'disabled@x.test', 'rightpass')

    expect(w.text()).toContain('Tài khoản của bạn đã bị vô hiệu hoá')
  })

  it('LV-FE-06: accountState() THROW → rơi catch, banner fallback hiện, form KHÔNG đứng im', async () => {
    loginMock.mockResolvedValue(false)
    accountStateMock.mockRejectedValue(new Error('network error / fetch failed'))

    const w = mountLogin()
    await fillAndSubmit(w, 'user@x.test', 'somepass')

    // PHẢI có message nào đó (không nuốt lỗi). classifyError('network...') → network.
    const text = w.text()
    expect(text).toContain('Không kết nối được máy chủ')
    // banner phải tồn tại trong DOM (v-if=error đã render)
    expect(banner(w).some((t) => t.length > 0)).toBe(true)
  })

  it('LV-FE-06b: accountState() throw không-rõ-loại → vẫn có message (không để trống)', async () => {
    loginMock.mockResolvedValue(false)
    authState.error = '' // store error rỗng
    accountStateMock.mockRejectedValue(new Error('???'))

    const w = mountLogin()
    await fillAndSubmit(w, 'user@x.test', 'somepass')

    // classifyError fallback = 'credential' → message credential, KHÔNG rỗng.
    expect(w.text()).toContain('Sai email hoặc mật khẩu. Vui lòng thử lại.')
  })

  it('LV-FE-07: login true → router.push tới redirect (mặc định /dashboard), KHÔNG banner', async () => {
    loginMock.mockResolvedValue(true)

    const w = mountLogin()
    await fillAndSubmit(w, 'user@x.test', 'goodpass')

    expect(routerPush).toHaveBeenCalledWith('/dashboard')
    expect(accountStateMock).not.toHaveBeenCalled()
    expect(w.text()).not.toContain('Sai email hoặc mật khẩu')
  })

  it('LV-FE-07b: login true + redirect query → push tới redirect đó', async () => {
    loginMock.mockResolvedValue(true)
    routeQuery = { redirect: '/incidents' }

    const w = mountLogin()
    await fillAndSubmit(w, 'user@x.test', 'goodpass')

    expect(routerPush).toHaveBeenCalledWith('/incidents')
  })

  // ── Redirect-safety (open-redirect hardening, IMM-00 B / ADR-001 D4) ────────
  // route.query.redirect là untrusted input. Sau login OK HOẶC onMounted khi đã
  // auth, chỉ điều hướng tới path nội bộ HỢP LỆ; mọi giá trị độc hại → /dashboard.

  it('LV-FE-08: login true + redirect độc hại //evil.com → push /dashboard (KHÔNG //evil)', async () => {
    loginMock.mockResolvedValue(true)
    routeQuery = { redirect: '//evil.com' }

    const w = mountLogin()
    await fillAndSubmit(w, 'user@x.test', 'goodpass')

    expect(routerPush).toHaveBeenCalledWith('/dashboard')
    expect(routerPush).not.toHaveBeenCalledWith('//evil.com')
  })

  it('LV-FE-08b: login true + redirect absolute https://phish/a/x → push /dashboard', async () => {
    loginMock.mockResolvedValue(true)
    routeQuery = { redirect: 'https://phish/a/x' }

    const w = mountLogin()
    await fillAndSubmit(w, 'user@x.test', 'goodpass')

    expect(routerPush).toHaveBeenCalledWith('/dashboard')
  })

  it('LV-FE-08c: login true + redirect QR deep-link /a/TOKEN → push y nguyên (giữ luồng QR)', async () => {
    loginMock.mockResolvedValue(true)
    routeQuery = { redirect: '/a/8ePtYlcy2h9DJnLnaRM_lA' }

    const w = mountLogin()
    await fillAndSubmit(w, 'user@x.test', 'goodpass')

    expect(routerPush).toHaveBeenCalledWith('/a/8ePtYlcy2h9DJnLnaRM_lA')
  })

  it('LV-FE-08d: login true + redirect absent → push /dashboard', async () => {
    loginMock.mockResolvedValue(true)
    routeQuery = {}

    const w = mountLogin()
    await fillAndSubmit(w, 'user@x.test', 'goodpass')

    expect(routerPush).toHaveBeenCalledWith('/dashboard')
  })

  it('LV-FE-09: onMounted đã-auth + redirect //evil.com → push /dashboard (KHÔNG //evil)', async () => {
    authState.isAuthenticated = true
    routeQuery = { redirect: '//evil.com' }

    mountLogin()
    await flushPromises()

    expect(routerPush).toHaveBeenCalledWith('/dashboard')
    expect(routerPush).not.toHaveBeenCalledWith('//evil.com')
  })

  it('LV-FE-09b: onMounted đã-auth + redirect /assets/AC-ASSET-2026-00001/info → push y nguyên', async () => {
    authState.isAuthenticated = true
    routeQuery = { redirect: '/assets/AC-ASSET-2026-00001/info' }

    mountLogin()
    await flushPromises()

    expect(routerPush).toHaveBeenCalledWith('/assets/AC-ASSET-2026-00001/info')
  })
})
