// TDD — nút hint ⌘K trên AppTopBar (ADR-IMM00-CMDK D4). TC-CMDK-08.
// Net-new cạnh Notification Bell. min-h/min-w 44px; click → store.open; badge
// '⌘K' hidden sm:inline. Lối vào DUY NHẤT mobile no-keyboard.
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('vue-router', () => ({
  useRoute: () => ({ meta: { title: 'Test' }, path: '/', query: {} }),
  useRouter: () => ({ push: vi.fn() }),
}))
vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({
    user: { full_name: 'Tester', name: 'tester@x.vn' },
    hasAnyRole: () => false,
    can: () => false,
    isFrappeAdmin: false,
    logout: vi.fn(),
  }),
}))
vi.mock('@/composables/useSidebar', () => ({
  useSidebar: () => ({ collapsed: { value: false }, openMobile: vi.fn() }),
}))
vi.mock('@/api/layout', () => ({
  getUnreadNotifications: vi.fn(async () => ({ items: [], count: 0 })),
  listNotifications: vi.fn(async () => ({ items: [] })),
  markNotificationAsRead: vi.fn(),
  markAllAsRead: vi.fn(),
  getUserContext: vi.fn(async () => null),
  logoutUser: vi.fn(),
  resolveNotificationRoute: vi.fn(() => null),
}))
vi.mock('@/utils/sanitizeHtml', () => ({ sanitizeHtml: (s: string) => s }))

import AppTopBar from './AppTopBar.vue'
import { useCommandPaletteStore } from '@/stores/commandPalette'

beforeEach(() => {
  setActivePinia(createPinia())
})

describe('AppTopBar — nút hint ⌘K (TC-CMDK-08)', () => {
  it('nút hint tồn tại với aria-label "Tìm nhanh"', async () => {
    const wrapper = mount(AppTopBar)
    await flushPromises()
    const btn = wrapper.find('button[aria-label="Tìm nhanh"]')
    expect(btn.exists()).toBe(true)
  })

  it('nút có min-h/min-w 44px (touch target)', async () => {
    const wrapper = mount(AppTopBar)
    await flushPromises()
    const btn = wrapper.find('button[aria-label="Tìm nhanh"]')
    const style = btn.attributes('style') || ''
    expect(style).toMatch(/min-height:\s*44px/)
    expect(style).toMatch(/min-width:\s*44px/)
  })

  it('badge "⌘K" có class hidden sm:inline', async () => {
    const wrapper = mount(AppTopBar)
    await flushPromises()
    const kbd = wrapper.find('button[aria-label="Tìm nhanh"] kbd')
    expect(kbd.exists()).toBe(true)
    expect(kbd.text()).toBe('⌘K')
    expect(kbd.classes()).toContain('hidden')
    expect(kbd.classes()).toContain('sm:inline')
  })

  it('click → store.open = true', async () => {
    const wrapper = mount(AppTopBar)
    await flushPromises()
    const store = useCommandPaletteStore()
    expect(store.open).toBe(false)
    await wrapper.find('button[aria-label="Tìm nhanh"]').trigger('click')
    expect(store.open).toBe(true)
  })
})
