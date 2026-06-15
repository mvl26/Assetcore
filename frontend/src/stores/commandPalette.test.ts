// TDD — Command Palette store (ADR-IMM00-CMDK D2 + D6).
// TC-CMDK-03 (gate predicate), TC-CMDK-04 (anti-leak rỗng), TC-CMDK-11 (recent
// persist+dedupe+≤5), TC-CMDK-12 (recent/pinned vẫn gate).
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import type { CommandItem } from '@/types/command'

// ── Mock capability + auth — điều khiển từng test qua state.caps ─────────────
const state = {
  caps: new Set<string>(),
  isFrappeAdmin: false,
}
vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({
    can: (cap: string | readonly string[]) => {
      const list = Array.isArray(cap) ? cap : [cap]
      return state.isFrappeAdmin || list.some((c) => state.caps.has(c as string))
    },
  }),
}))
vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({
    get isFrappeAdmin() { return state.isFrappeAdmin },
    can: (cap: string) => state.isFrappeAdmin || state.caps.has(cap),
    hasAnyRole: () => state.isFrappeAdmin,
  }),
}))

import { useCommandPaletteStore } from './commandPalette'

const REG: CommandItem[] = [
  { id: '/dashboard', title: 'Bảng điều khiển', to: '/dashboard', source: 'nav' }, // cap undefined → mở
  { id: '/qr-scan', title: 'Quét mã QR', to: '/qr-scan', source: 'nav' },           // cap undefined → mở
  { id: '/pm/work-orders', title: 'Lệnh bảo trì', to: '/pm/work-orders', cap: 'pm.read', source: 'nav' },
  { id: '/incidents/new', title: 'Tạo báo hỏng', to: '/incidents/new', cap: ['corrective.create'], source: 'route', moduleId: 'imm12' },
  { id: '/compliance/rules', title: 'Quy tắc tuân thủ', to: '/compliance/rules', cap: 'compliance.write', source: 'nav' },
]

beforeEach(() => {
  setActivePinia(createPinia())
  localStorage.clear()
  state.caps = new Set()
  state.isFrappeAdmin = false
})

describe('commandPalette store — D2 gate + anti-leak', () => {
  it('TC-CMDK-04: capability rỗng → CHỈ command cap===undefined hiện; 0 gated lộ', () => {
    const store = useCommandPaletteStore()
    store.setRegistry(REG)
    const titles = store.visibleCommands.map((c) => c.title)
    expect(titles).toContain('Bảng điều khiển')
    expect(titles).toContain('Quét mã QR')
    expect(titles).not.toContain('Lệnh bảo trì')      // pm.read thiếu
    expect(titles).not.toContain('Tạo báo hỏng')      // corrective.create thiếu
    expect(titles).not.toContain('Quy tắc tuân thủ')  // compliance.write thiếu
  })

  it('TC-CMDK-03: nav lọc qua itemVisible, route lọc qua resolveRouteAccess', () => {
    const store = useCommandPaletteStore()
    store.setRegistry(REG)
    state.caps = new Set(['pm.read', 'corrective.create'])
    const titles = store.visibleCommands.map((c) => c.title)
    expect(titles).toContain('Lệnh bảo trì')   // nav cap pm.read → itemVisible true
    expect(titles).toContain('Tạo báo hỏng')   // route requiredCapabilities corrective.create → allow
    expect(titles).not.toContain('Quy tắc tuân thủ') // compliance.write vẫn thiếu
  })

  it('superuser (isFrappeAdmin) → thấy mọi command (bypass)', () => {
    const store = useCommandPaletteStore()
    store.setRegistry(REG)
    state.isFrappeAdmin = true
    expect(store.visibleCommands.length).toBe(REG.length)
  })

  it('TC-CMDK-11: selectCommand → recent unshift + dedupe + ≤5 + persist', () => {
    const store = useCommandPaletteStore()
    store.setRegistry(REG)
    state.isFrappeAdmin = true
    store.selectCommand('/dashboard')
    store.selectCommand('/qr-scan')
    store.selectCommand('/dashboard') // dedupe → lên đầu, không nhân đôi
    expect(store.recent).toEqual(['/dashboard', '/qr-scan'])
    // persist
    expect(JSON.parse(localStorage.getItem('ac_cmdk_recent') || '[]')).toEqual(['/dashboard', '/qr-scan'])
    // ≤5
    for (const id of ['/a', '/b', '/c', '/d', '/e', '/f']) store.selectCommand(id)
    expect(store.recent.length).toBe(5)
    expect(store.recent[0]).toBe('/f')
  })

  it('TC-CMDK-11: reload (đọc lại localStorage) → recent hiện lại', () => {
    localStorage.setItem('ac_cmdk_recent', JSON.stringify(['/qr-scan', '/dashboard']))
    const store = useCommandPaletteStore()
    store.setRegistry(REG)
    state.isFrappeAdmin = true
    expect(store.recentCommands.map((c) => c.id)).toEqual(['/qr-scan', '/dashboard'])
  })

  it('TC-CMDK-12: recent/pinned VẪN lọc qua D2 — mất quyền → ẩn', () => {
    // user từng ghim + dùng "Lệnh bảo trì" (pm.read) nhưng nay mất pm.read.
    localStorage.setItem('ac_cmdk_recent', JSON.stringify(['/pm/work-orders', '/dashboard']))
    localStorage.setItem('ac_cmdk_pinned', JSON.stringify(['/compliance/rules']))
    const store = useCommandPaletteStore()
    store.setRegistry(REG)
    // caps rỗng → cả 2 gated phải biến mất khỏi recent/pinned.
    expect(store.recentCommands.map((c) => c.id)).toEqual(['/dashboard'])
    expect(store.pinnedCommands).toEqual([])
  })

  it('TC-CMDK-12: có quyền lại → recent/pinned hiện lại', () => {
    localStorage.setItem('ac_cmdk_recent', JSON.stringify(['/pm/work-orders']))
    localStorage.setItem('ac_cmdk_pinned', JSON.stringify(['/compliance/rules']))
    const store = useCommandPaletteStore()
    store.setRegistry(REG)
    state.caps = new Set(['pm.read', 'compliance.write'])
    expect(store.recentCommands.map((c) => c.id)).toEqual(['/pm/work-orders'])
    expect(store.pinnedCommands.map((c) => c.id)).toEqual(['/compliance/rules'])
  })

  it('togglePin persist + isPinned + pinned bỏ khỏi recent (dedupe section)', () => {
    const store = useCommandPaletteStore()
    store.setRegistry(REG)
    state.isFrappeAdmin = true
    store.selectCommand('/dashboard')
    store.togglePin('/dashboard')
    expect(store.isPinned('/dashboard')).toBe(true)
    expect(JSON.parse(localStorage.getItem('ac_cmdk_pinned') || '[]')).toEqual(['/dashboard'])
    // pinned → KHÔNG xuất hiện lại trong recentCommands (tránh trùng section)
    expect(store.recentCommands.map((c) => c.id)).not.toContain('/dashboard')
    expect(store.pinnedCommands.map((c) => c.id)).toContain('/dashboard')
  })

  it('open/close/toggle + clear query khi đóng', () => {
    const store = useCommandPaletteStore()
    store.openPalette(); expect(store.open).toBe(true)
    store.setQuery('bao tri'); expect(store.query).toBe('bao tri')
    store.closePalette(); expect(store.open).toBe(false); expect(store.query).toBe('')
    store.toggle(); expect(store.open).toBe(true)
  })

  it('filteredCommands áp gate + search: caps rỗng + query "bao tri" → KHÔNG lộ "Lệnh bảo trì"', () => {
    const store = useCommandPaletteStore()
    store.setRegistry(REG)
    store.setQuery('bao tri')
    // pm.read thiếu → "Lệnh bảo trì" gated; query khớp nhưng anti-leak ẩn.
    expect(store.filteredCommands.map((c) => c.title)).not.toContain('Lệnh bảo trì')
  })
})
