// TDD — CommandPalette a11y + keyboard (ADR-IMM00-CMDK D5). TC-CMDK-09/10.
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import type { CommandItem } from '@/types/command'

const routerPush = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: routerPush }),
}))

// Admin bypass → mọi command hiện (tách gate ra test store riêng).
const state = { isFrappeAdmin: true, caps: new Set<string>() }
vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({ can: () => state.isFrappeAdmin }),
}))
vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({
    get isFrappeAdmin() { return state.isFrappeAdmin },
    can: () => state.isFrappeAdmin,
    hasAnyRole: () => state.isFrappeAdmin,
  }),
}))

import CommandPalette from './CommandPalette.vue'
import { useCommandPaletteStore } from '@/stores/commandPalette'

const REG: CommandItem[] = [
  { id: '/dashboard', title: 'Bảng điều khiển', to: '/dashboard', source: 'nav' },
  { id: '/pm/work-orders', title: 'Lệnh bảo trì', to: '/pm/work-orders', source: 'nav' },
  { id: '/cm/work-orders', title: 'Lệnh sửa chữa', to: '/cm/work-orders', source: 'nav' },
]

async function openWith(): Promise<{ wrapper: ReturnType<typeof mount>; store: ReturnType<typeof useCommandPaletteStore> }> {
  const wrapper = mount(CommandPalette, { attachTo: document.body })
  const store = useCommandPaletteStore()
  store.setRegistry(REG)
  store.openPalette()
  await flushPromises()
  return { wrapper, store }
}

function dialog(): HTMLElement {
  return document.body.querySelector('[role="dialog"]') as HTMLElement
}

// Teleport → query document; dispatch keydown trên dialog node thật.
async function press(key: string, shiftKey = false): Promise<void> {
  const d = dialog()
  d.dispatchEvent(new KeyboardEvent('keydown', { key, shiftKey, bubbles: true, cancelable: true }))
  await flushPromises()
}

beforeEach(() => {
  setActivePinia(createPinia())
  localStorage.clear()
  document.body.innerHTML = ''
  routerPush.mockClear()
  state.isFrappeAdmin = true
})

describe('CommandPalette — a11y roles (TC-CMDK-09)', () => {
  it('container role=dialog aria-modal aria-label', async () => {
    await openWith()
    const d = dialog()
    expect(d).toBeTruthy()
    expect(d.getAttribute('aria-modal')).toBe('true')
    expect(d.getAttribute('aria-label')).toBeTruthy()
  })

  it('input role=combobox + aria-controls + aria-activedescendant + aria-expanded', async () => {
    await openWith()
    const input = document.body.querySelector('input[role="combobox"]') as HTMLInputElement
    expect(input).toBeTruthy()
    expect(input.getAttribute('aria-expanded')).toBe('true')
    expect(input.getAttribute('aria-controls')).toBe('ac-cmdk-listbox')
    expect(input.getAttribute('aria-activedescendant')).toBe('ac-cmdk-option-0')
  })

  it('kết quả role=listbox; mỗi item role=option + aria-selected', async () => {
    await openWith()
    const listbox = document.body.querySelector('[role="listbox"]')
    expect(listbox).toBeTruthy()
    const options = document.body.querySelectorAll('[role="option"]')
    expect(options.length).toBeGreaterThanOrEqual(3)
    // option đầu được chọn mặc định.
    expect(options[0].getAttribute('aria-selected')).toBe('true')
  })
})

describe('CommandPalette — keyboard (TC-CMDK-10)', () => {
  it('ArrowDown/Up đổi active (wrap)', async () => {
    await openWith()
    // active=0; ArrowUp wrap → cuối.
    await press('ArrowUp')
    let active = document.body.querySelector('[aria-selected="true"]') as HTMLElement
    expect(active.id).toBe('ac-cmdk-option-2')
    // ArrowDown wrap → đầu.
    await press('ArrowDown')
    active = document.body.querySelector('[aria-selected="true"]') as HTMLElement
    expect(active.id).toBe('ac-cmdk-option-0')
  })

  it('Enter → router.push đích active + đóng', async () => {
    const { store } = await openWith()
    await press('ArrowDown') // active=1
    await press('Enter')
    expect(routerPush).toHaveBeenCalledWith('/pm/work-orders')
    expect(store.open).toBe(false)
  })

  it('Escape → đóng palette', async () => {
    const { store } = await openWith()
    await press('Escape')
    expect(store.open).toBe(false)
  })

  it('Enter sau khi chọn → ghi recent', async () => {
    const { store } = await openWith()
    await press('Enter')
    expect(store.recent).toContain('/dashboard')
  })
})
