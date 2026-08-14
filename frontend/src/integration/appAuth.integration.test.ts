// Copyright (c) 2026, AssetCore Team
//
// INTEGRATION regression guard — IMM-00 auth bootstrap vs login-submit (APP-AUTH).
//
// Vá false-green: LoginView.test.ts MOCK store nên KHÔNG bắt được lỗi lifecycle
// "App.vue full-screen spinner đè /login khi đang submit → LoginView remount →
// mất field + banner". Test này mount App.vue với STORE THẬT (createPinia, KHÔNG
// mock @/stores/auth) + axios mock ở biên transport, qua router THẬT.
//
// Acceptance:
//   APP-AUTH-01: submit wrong-pwd → banner 'Sai email hoặc mật khẩu' tồn tại VÀ
//                #login-email/#login-password GIỮ giá trị đã gõ (không remount).
//   APP-AUTH-02: auth.loading=true (đang submit) trên /login chưa auth → App.vue
//                KHÔNG render full-screen spinner 'Đang khởi tạo...'.
//   APP-AUTH-03: auth.bootstrapping=true (App.vue onMounted fetchSession lần đầu)
//                chưa auth → full-screen spinner 'Đang khởi tạo...' CÓ render.

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import {
  createRouter,
  createMemoryHistory,
  type Router,
  type RouteRecordRaw,
} from 'vue-router'

// ── Mock biên transport (axios instance). Store/helpers/api THẬT chạy phía trên ─
//   - login(): api.post('/api/method/login', ...) đọc res.data.csrf_token.
//   - getUserContext()/accountState() qua frappeGet/frappePost → res.data.message.
const apiGet = vi.fn()
const apiPost = vi.fn()
vi.mock('@/api/axios', () => ({
  default: {
    get: (...a: unknown[]) => apiGet(...a),
    post: (...a: unknown[]) => apiPost(...a),
  },
  setCsrfToken: vi.fn(),
  getCsrfToken: vi.fn(() => ''),
}))

// Stub asset import — Vitest không resolve PNG.
vi.mock('@/assets/logo-miyano.png', () => ({ default: 'logo.png' }))

// Phẳng hoá các con nặng của App.vue không liên quan kịch bản auth.
vi.mock('@/components/common/NotificationModal.vue', () => ({
  default: { name: 'NotificationModal', template: '<div />' },
}))
vi.mock('@/components/common/ToastContainer.vue', () => ({
  default: { name: 'ToastContainer', template: '<div />' },
}))
vi.mock('@/components/common/AppLayout.vue', () => ({
  default: { name: 'AppLayout', template: '<div><slot /></div>' },
}))

import App from '@/App.vue'
import { useAuthStore } from '@/stores/auth'

const LoginRouteStub: RouteRecordRaw = {
  path: '/login',
  name: 'Login',
  component: () => import('@/views/auth/LoginView.vue'),
  meta: { requiresAuth: false },
}
const HomeRouteStub: RouteRecordRaw = {
  path: '/',
  name: 'Home',
  component: { template: '<div>home</div>' },
  meta: { requiresAuth: true },
}

function makeRouter(): Router {
  return createRouter({
    history: createMemoryHistory(),
    routes: [LoginRouteStub, HomeRouteStub, {
      path: '/dashboard', name: 'Dashboard',
      component: { template: '<div>dash</div>' }, meta: { requiresAuth: true },
    }],
  })
}

async function mountApp(router: Router) {
  const wrapper = mount(App, {
    global: {
      plugins: [router],
      stubs: { RouterLink: { template: '<a><slot /></a>', props: ['to'] } },
    },
  })
  await flushPromises()
  return wrapper
}

const SPINNER_LABEL = 'Đang khởi tạo...'
const CRED_BANNER = 'Sai email hoặc mật khẩu. Vui lòng thử lại.'

describe('App.vue — bootstrap vs login-submit loading (APP-AUTH, integration, store THẬT)', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
    setActivePinia(createPinia())
    // Mặc định: account_state trả invalid_credentials (sai mật khẩu).
    apiPost.mockImplementation((url: string) => {
      if (typeof url === 'string' && url.includes('/api/method/login')) {
        return Promise.reject(new Error('Request failed with status code 401'))
      }
      // account_state qua frappePost → envelope { message: { success, data } }
      if (typeof url === 'string' && url.includes('account_state')) {
        return Promise.resolve({ data: { message: { success: true, data: { status: 'invalid_credentials' } } } })
      }
      return Promise.resolve({ data: { message: { success: true, data: {} } } })
    })
    // getUserContext (bootstrap chưa auth) → 403 → fetchSession trả false.
    apiGet.mockRejectedValue(new Error('Request failed with status code 403'))
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  // ── APP-AUTH-01 (vá false-green chính) ───────────────────────────────────
  it('APP-AUTH-01: submit wrong-pwd → banner hiện VÀ LoginView KHÔNG remount (field giữ nguyên)', async () => {
    const router = makeRouter()
    await router.push('/login')
    await router.isReady()
    const wrapper = await mountApp(router)

    // Đang ở /login (chưa auth) → LoginView render, KHÔNG có full-screen spinner.
    expect(wrapper.text()).not.toContain(SPINNER_LABEL)
    const emailInput = wrapper.find('#login-email')
    const pwdInput = wrapper.find('#login-password')
    expect(emailInput.exists()).toBe(true)

    // User gõ email + mật khẩu SAI.
    await emailInput.setValue('user@x.test')
    await pwdInput.setValue('wrongpass')

    // Submit → login() POST /api/method/login bị 401 → trả false; account_state
    // trả invalid_credentials → banner credential.
    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()

    // Banner credential tồn tại trong DOM.
    expect(wrapper.text()).toContain(CRED_BANNER)
    // role=alert để screen-reader đọc.
    expect(wrapper.find('[role="alert"]').exists()).toBe(true)

    // LoginView KHÔNG remount → giá trị 2 ô GIỮ NGUYÊN (không bắt gõ lại).
    expect((wrapper.find('#login-email').element as HTMLInputElement).value).toBe('user@x.test')
    expect((wrapper.find('#login-password').element as HTMLInputElement).value).toBe('wrongpass')
    // Viền đỏ 2 input (errorType=credential).
    expect(wrapper.find('#login-email').classes()).toContain('border-red-400')
    expect(wrapper.find('#login-password').classes()).toContain('border-red-400')
    // Full-screen overlay KHÔNG xuất hiện trong suốt submit.
    expect(wrapper.text()).not.toContain(SPINNER_LABEL)
  })

  // ── APP-AUTH-02: loading (submit) KHÔNG bật full-screen overlay ───────────
  it('APP-AUTH-02: auth.loading=true trên /login chưa auth → KHÔNG render full-screen spinner', async () => {
    const router = makeRouter()
    await router.push('/login')
    await router.isReady()
    const wrapper = await mountApp(router)

    const auth = useAuthStore()
    expect(auth.isAuthenticated).toBe(false)
    // Mô phỏng đang submit form login.
    auth.loading = true
    await flushPromises()

    // App.vue full-screen overlay gắn cờ `bootstrapping`, KHÔNG phải `loading`.
    expect(auth.bootstrapping).toBe(false)
    expect(wrapper.text()).not.toContain(SPINNER_LABEL)
    // LoginView vẫn mounted (RouterView v-else).
    expect(wrapper.find('#login-email').exists()).toBe(true)
  })

  // ── APP-AUTH-03: bootstrapping bật full-screen overlay ────────────────────
  it('APP-AUTH-03: auth.bootstrapping=true chưa auth → CÓ render full-screen spinner', async () => {
    const router = makeRouter()
    await router.push('/login')
    await router.isReady()
    const wrapper = await mountApp(router)

    const auth = useAuthStore()
    expect(auth.isAuthenticated).toBe(false)
    auth.bootstrapping = true
    await flushPromises()

    expect(wrapper.text()).toContain(SPINNER_LABEL)
  })

  // ── APP-AUTH-03b: bootstrap() bật cờ trong fetchSession, hạ khi xong ──────
  it('APP-AUTH-03b: bootstrap() bật bootstrapping trong fetchSession rồi hạ về false', async () => {
    const auth = useAuthStore()
    expect(auth.bootstrapping).toBe(false)

    let resolveCtx: (v: unknown) => void = () => {}
    apiGet.mockImplementationOnce(
      () => new Promise((res) => { resolveCtx = res }),
    )

    const p = auth.bootstrap()
    await flushPromises()
    // Trong khi fetchSession đang chạy → bootstrapping=true.
    expect(auth.bootstrapping).toBe(true)

    // Hoàn tất với 403-shape (reject) → fetchSession trả false.
    resolveCtx({ data: { message: {} } })
    await p
    await flushPromises()
    expect(auth.bootstrapping).toBe(false)
  })
})
