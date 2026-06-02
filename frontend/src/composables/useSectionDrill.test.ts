// Copyright (c) 2026, AssetCore Team
//
// TDD — Core Doc §9.7/§9.9: useSectionDrill map row→detail record nguồn, gate
// canAccessDrill. R5–R9 dùng chung helper này cho mọi persona section.
import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useSectionDrill } from '@/composables/useSectionDrill'
import { useAuthStore } from '@/stores/auth'

function seedCaps(caps: Record<string, boolean>): void {
  useAuthStore().capabilities = caps
}

beforeEach(() => setActivePinia(createPinia()))

describe('useSectionDrill (R5-R9 §9.7/§9.9)', () => {
  it('D-FE-40: pmWo/cmWo có quyền → route detail đúng name', () => {
    seedCaps({ 'pm.read': true, 'repair.read': true })
    const d = useSectionDrill()
    expect(d.pmWo({ name: 'PM-001' })).toEqual({ path: '/pm/work-orders/PM-001' })
    expect(d.cmWo({ name: 'CM-001' })).toEqual({ path: '/cm/work-orders/CM-001' })
  })

  it('D-FE-41: thiếu cap route đích → null (row tĩnh, không dead-end)', () => {
    seedCaps({ 'data.read': true }) // không pm.read/repair.read
    const d = useSectionDrill()
    expect(d.pmWo({ name: 'PM-001' })).toBeNull()
    expect(d.cmWo({ name: 'CM-001' })).toBeNull()
  })

  it('D-FE-42: id rỗng → null (không bịa link)', () => {
    seedCaps({ 'pm.read': true })
    const d = useSectionDrill()
    expect(d.pmWo({ name: '' })).toBeNull()
    expect(d.pmWo({})).toBeNull()
  })

  it('D-FE-43: document → /documents/view/:name (gate /documents = document.read)', () => {
    seedCaps({ 'document.read': true })
    const d = useSectionDrill()
    expect(d.document({ name: 'DOC-001' })).toEqual({ path: '/documents/view/DOC-001' })
  })

  it('D-FE-44: incident gate /incidents/list (corrective.read) → /incidents/:name', () => {
    seedCaps({ 'corrective.read': true })
    const d = useSectionDrill()
    expect(d.incident({ name: 'INC-001' })).toEqual({ path: '/incidents/INC-001' })
    seedCaps({ 'data.read': true })
    expect(useSectionDrill().incident({ name: 'INC-001' })).toBeNull()
  })

  it('D-FE-45: sparePart đọc field spare_part (không phải name)', () => {
    seedCaps({ 'inventory.read': true })
    const d = useSectionDrill()
    expect(d.sparePart({ spare_part: 'SP-001', name: 'ALLOC-1' })).toEqual({ path: '/spare-parts/SP-001' })
  })

  it('D-FE-46: commissioning + needs route detail (master/system → cho phép)', () => {
    seedCaps({ 'commissioning.read': true })
    const d = useSectionDrill()
    expect(d.commissioning({ name: 'COMM-1' })).toEqual({ path: '/commissioning/COMM-1' })
    expect(d.needs({ name: 'NR-1' })).toEqual({ path: '/needs-requests/NR-1' })
  })

  it('D-FE-47: encode id có ký tự đặc biệt (email)', () => {
    seedCaps({ 'pm.read': true })
    const d = useSectionDrill()
    expect(d.custom('/user-profiles', 'name', '/user-profiles')).toBeTypeOf('function')
  })
})
