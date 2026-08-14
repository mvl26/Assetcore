// Copyright (c) 2026, AssetCore Team
//
// TDD — Core Doc §9.8 (R4): admin pillar "Người dùng · Phân quyền · Master data ·
// Audit chain" từ subtitle trang trí → nav tiles THẬT (RouterLink). Tile gate
// canAccessDrill: thiếu cap → ẩn tile (không link dead-end).
import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

import AdminShortcutTiles from '@/components/dashboard/AdminShortcutTiles.vue'
import { useAuthStore } from '@/stores/auth'

const RouterLinkStub = {
  name: 'RouterLink',
  props: ['to'],
  template: '<a class="router-link-stub"><slot /></a>',
}
const mountOpts = { global: { stubs: { RouterLink: RouterLinkStub } } }

function seedCaps(caps: Record<string, boolean>): void {
  useAuthStore().capabilities = caps
}

beforeEach(() => setActivePinia(createPinia()))

describe('AdminShortcutTiles (R4 §9.8)', () => {
  it('D-FE-36: admin đủ quyền → render tile nav RouterLink (user-profiles, admin/roles, master, audit)', () => {
    seedCaps({ 'data.admin': true, 'audit.read': true })
    const w = mount(AdminShortcutTiles, mountOpts)
    const links = w.findAllComponents(RouterLinkStub)
    const paths = links.map((l) => (l.props('to') as { path?: string }).path ?? l.props('to'))
    expect(paths).toContain('/user-profiles')
    expect(paths).toContain('/admin/roles')
    expect(paths).toContain('/audit-trail')
    // ít nhất 1 master-data tile.
    expect(paths.some((p) => ['/device-models', '/suppliers', '/service-contracts'].includes(String(p)))).toBe(true)
    expect(w.text()).toContain('Người dùng')
    expect(w.text()).toContain('Phân quyền')
  })

  it('D-FE-37: thiếu data.admin → ẩn tile Người dùng/Phân quyền (không dead-end), không crash', () => {
    seedCaps({ 'data.read': true })
    const w = mount(AdminShortcutTiles, mountOpts)
    const links = w.findAllComponents(RouterLinkStub)
    const paths = links.map((l) => (l.props('to') as { path?: string }).path ?? l.props('to'))
    expect(paths).not.toContain('/user-profiles')
    expect(paths).not.toContain('/admin/roles')
  })
})
