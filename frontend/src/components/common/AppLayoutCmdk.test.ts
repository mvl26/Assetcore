// TDD — ⌘K/Ctrl+K bind toàn cục ở AppLayout (ADR-IMM00-CMDK D4). TC-CMDK-07.
// keydown ⌘K/Ctrl+K ở mọi route → store.open=true; preventDefault gọi
// (chặn browser bookmark default). Dùng useMagicKeys (KHÔNG addEventListener tay).
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('vue-router', () => ({
  useRoute: () => ({ meta: {}, path: '/', query: {} }),
  useRouter: () => ({ push: vi.fn(), getRoutes: () => [] }),
}))
vi.mock('@/composables/useSidebar', () => ({
  useSidebar: () => ({ mainClass: { value: '' }, mobileOpen: { value: false }, closeMobile: vi.fn() }),
}))
vi.mock('@/composables/useCommandRegistry', async () => {
  const { ref } = await import('vue')
  return { useCommandRegistry: () => ({ registry: ref([]) }) }
})

import AppLayout from './AppLayout.vue'
import { useCommandPaletteStore } from '@/stores/commandPalette'

const STUBS = {
  AppSidebar: { template: '<div />' },
  AppTopBar: { template: '<div />' },
  CommandPalette: { template: '<div data-cmdk />' },
}

beforeEach(() => {
  setActivePinia(createPinia())
})

function dispatchKey(key: string, mods: { metaKey?: boolean; ctrlKey?: boolean }): KeyboardEvent {
  const ev = new KeyboardEvent('keydown', { key, bubbles: true, cancelable: true, ...mods })
  const spy = vi.spyOn(ev, 'preventDefault')
  document.dispatchEvent(ev)
  // gắn spy lên ev để assert sau.
  ;(ev as unknown as { _pdSpy: typeof spy })._pdSpy = spy
  return ev
}

describe('AppLayout — ⌘K / Ctrl+K toggle store (TC-CMDK-07)', () => {
  it('Meta+K (mac) → store.open=true + preventDefault', async () => {
    const wrapper = mount(AppLayout, { global: { stubs: STUBS } })
    await flushPromises()
    const store = useCommandPaletteStore()
    expect(store.open).toBe(false)
    const ev = dispatchKey('k', { metaKey: true })
    await flushPromises()
    expect(store.open).toBe(true)
    expect((ev as unknown as { _pdSpy: { mock: { calls: unknown[] } } })._pdSpy.mock.calls.length).toBeGreaterThan(0)
    wrapper.unmount()
  })

  it('Ctrl+K (win) → store.open=true + preventDefault', async () => {
    const wrapper = mount(AppLayout, { global: { stubs: STUBS } })
    await flushPromises()
    const store = useCommandPaletteStore()
    const ev = dispatchKey('k', { ctrlKey: true })
    await flushPromises()
    expect(store.open).toBe(true)
    expect((ev as unknown as { _pdSpy: { mock: { calls: unknown[] } } })._pdSpy.mock.calls.length).toBeGreaterThan(0)
    wrapper.unmount()
  })

  it('mount <CommandPalette/> ở shell', async () => {
    const wrapper = mount(AppLayout, { global: { stubs: STUBS } })
    await flushPromises()
    expect(wrapper.find('[data-cmdk]').exists()).toBe(true)
    wrapper.unmount()
  })
})
