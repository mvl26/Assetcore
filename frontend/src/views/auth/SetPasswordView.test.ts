// Copyright (c) 2026, AssetCore Team
//
// ISS-002 — màn hình tự đặt mật khẩu của AssetCore (thay form /update-password
// của Frappe desk). Acceptance:
//   - Link hợp lệ  → chào đúng tên user + hiện form đặt mật khẩu.
//   - Link hỏng/hết hạn → banner lỗi tiếng Việt, KHÔNG hiện form (không để user
//     gõ xong mới biết link chết).
//   - Nhập lại không khớp → chặn tại FE, KHÔNG gọi API.
//   - Đặt thành công → màn hình xác nhận + lối vào trang đăng nhập.
//   - BE từ chối (mật khẩu yếu) → surface đúng message của BE.

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

vi.mock('@/api/auth', () => ({
  verifyPasswordKey: vi.fn(),
  setPasswordWithKey: vi.fn(),
}))

const routerPush = vi.fn()
let routeQuery: Record<string, string> = {}
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: routerPush }),
  useRoute: () => ({ query: routeQuery }),
  RouterLink: { template: '<a><slot /></a>' },
}))

vi.mock('@/assets/logo-miyano.png', () => ({ default: 'logo.png' }))

import SetPasswordView from './SetPasswordView.vue'
import { verifyPasswordKey, setPasswordWithKey } from '@/api/auth'

const verifyMock = vi.mocked(verifyPasswordKey)
const setMock = vi.mocked(setPasswordWithKey)

const OK_IDENTITY = {
  user: 'ktv@benhvien.vn',
  full_name: 'Nguyễn Văn Kỹ Thuật',
  login_url: 'http://site/assetcore/login',
}

async function mountView() {
  const wrapper = mount(SetPasswordView)
  await flushPromises()
  return wrapper
}

async function fill(wrapper: Awaited<ReturnType<typeof mountView>>, pw: string, confirm: string) {
  await wrapper.get('#new-password').setValue(pw)
  await wrapper.get('#confirm-password').setValue(confirm)
  await wrapper.get('form').trigger('submit')
  await flushPromises()
}

describe('SetPasswordView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    routeQuery = { key: 'key-hop-le' }
  })

  it('kiểm tra link và chào đúng tên người dùng', async () => {
    verifyMock.mockResolvedValue(OK_IDENTITY)
    const wrapper = await mountView()

    expect(verifyMock).toHaveBeenCalledWith('key-hop-le')
    expect(wrapper.text()).toContain('Nguyễn Văn Kỹ Thuật')
    expect(wrapper.text()).toContain(OK_IDENTITY.user)
    expect(wrapper.find('#new-password').exists()).toBe(true)
  })

  it('link hết hạn → banner lỗi, KHÔNG hiện form', async () => {
    verifyMock.mockRejectedValue(new Error('Liên kết đặt mật khẩu đã hết hạn.'))
    const wrapper = await mountView()

    expect(wrapper.text()).toContain('hết hạn')
    expect(wrapper.find('#new-password').exists()).toBe(false)
  })

  it('thiếu key trong URL → báo lỗi, KHÔNG gọi API', async () => {
    routeQuery = {}
    const wrapper = await mountView()

    expect(verifyMock).not.toHaveBeenCalled()
    expect(wrapper.find('#new-password').exists()).toBe(false)
    expect(wrapper.text().toLowerCase()).toContain('không hợp lệ')
  })

  it('nhập lại không khớp → chặn tại FE, không gọi API', async () => {
    verifyMock.mockResolvedValue(OK_IDENTITY)
    const wrapper = await mountView()
    await fill(wrapper, 'Kt#Bv2026$Ngoc', 'Kt#Bv2026$Khac')

    expect(setMock).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('không khớp')
  })

  it('mật khẩu quá ngắn → chặn tại FE, không gọi API', async () => {
    verifyMock.mockResolvedValue(OK_IDENTITY)
    const wrapper = await mountView()
    await fill(wrapper, 'ngan', 'ngan')

    expect(setMock).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('8 ký tự')
  })

  it('đặt mật khẩu thành công → màn xác nhận + lối vào đăng nhập', async () => {
    verifyMock.mockResolvedValue(OK_IDENTITY)
    setMock.mockResolvedValue({
      user: OK_IDENTITY.user,
      login_url: OK_IDENTITY.login_url,
      message: 'Đặt mật khẩu thành công. Bạn có thể đăng nhập ngay.',
    })
    const wrapper = await mountView()
    await fill(wrapper, 'Kt#Bv2026$Ngoc', 'Kt#Bv2026$Ngoc')

    expect(setMock).toHaveBeenCalledWith('key-hop-le', 'Kt#Bv2026$Ngoc')
    expect(wrapper.text()).toContain('thành công')
    expect(wrapper.find('[data-test="go-login"]').exists()).toBe(true)
    expect(wrapper.find('#new-password').exists()).toBe(false)
  })

  it('BE từ chối mật khẩu yếu → surface message của BE, giữ form', async () => {
    verifyMock.mockResolvedValue(OK_IDENTITY)
    setMock.mockRejectedValue(new Error('Mật khẩu quá yếu — hãy dùng mật khẩu dài hơn.'))
    const wrapper = await mountView()
    await fill(wrapper, 'Kt#Bv2026$Ngoc', 'Kt#Bv2026$Ngoc')

    expect(wrapper.text()).toContain('quá yếu')
    expect(wrapper.find('#new-password').exists()).toBe(true)
  })
})
