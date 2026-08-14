// TDD — Core Doc §7.bis (docs/architecture/FE_Persona_Navigation.md)
// Sidebar collapsible grouping: persist closed-group titles, active-group override,
// default-open, graceful localStorage.
import { describe, it, expect, beforeEach, vi } from 'vitest'
import {
  isGroupOpen,
  readClosedGroups,
  writeClosedGroups,
  toggleClosedGroup,
  GROUPS_STORAGE_KEY,
} from '@/constants/sidebarGroups'
import type { SidebarGroup } from '@/constants/sidebarNav'

function grp(title: string): SidebarGroup {
  return { code: '', title, icon: 'cog', items: [] }
}

describe('isGroupOpen — open/closed decision', () => {
  const pm = grp('Bảo trì định kỳ (PM)')

  it('T14: no persist yet → open (default expanded)', () => {
    expect(isGroupOpen(pm, [], null)).toBe(true)
  })

  it('T15: group in closed list → closed', () => {
    expect(isGroupOpen(pm, [pm.title], null)).toBe(false)
  })

  it('T16: group closed BUT is active → open (active override)', () => {
    expect(isGroupOpen(pm, [pm.title], pm.title)).toBe(true)
  })

  it('group not in closed list, another group active → still open', () => {
    expect(isGroupOpen(pm, ['Sửa chữa (CM)'], 'Sửa chữa (CM)')).toBe(true)
  })
})

describe('persist round-trip', () => {
  beforeEach(() => { localStorage.clear() })

  it('T17: toggle writes then removes title; reload reads it back', () => {
    const title = 'Tồn kho phụ tùng'
    expect(readClosedGroups()).toEqual([])

    // close it
    let next = toggleClosedGroup(title)
    expect(next).toContain(title)
    expect(readClosedGroups()).toContain(title)

    // re-open it
    next = toggleClosedGroup(title)
    expect(next).not.toContain(title)
    expect(readClosedGroups()).not.toContain(title)
  })

  it('writeClosedGroups persists exact array', () => {
    writeClosedGroups(['A', 'B'])
    expect(readClosedGroups()).toEqual(['A', 'B'])
    expect(localStorage.getItem(GROUPS_STORAGE_KEY)).toBe(JSON.stringify(['A', 'B']))
  })
})

describe('graceful localStorage', () => {
  beforeEach(() => { localStorage.clear() })

  it('T18: garbage JSON → returns [] (all groups open), no throw', () => {
    localStorage.setItem(GROUPS_STORAGE_KEY, '{not json')
    expect(() => readClosedGroups()).not.toThrow()
    expect(readClosedGroups()).toEqual([])
  })

  it('non-array JSON → returns []', () => {
    localStorage.setItem(GROUPS_STORAGE_KEY, JSON.stringify({ a: 1 }))
    expect(readClosedGroups()).toEqual([])
  })

  it('array with non-string entries → filtered to strings', () => {
    localStorage.setItem(GROUPS_STORAGE_KEY, JSON.stringify(['A', 1, null, 'B']))
    expect(readClosedGroups()).toEqual(['A', 'B'])
  })

  it('write failure (quota) is swallowed, does not throw', () => {
    const spy = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('quota')
    })
    expect(() => writeClosedGroups(['X'])).not.toThrow()
    spy.mockRestore()
  })
})
