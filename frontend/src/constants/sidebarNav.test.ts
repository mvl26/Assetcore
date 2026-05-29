// TDD — Core Doc §2.1 + §9 (docs/architecture/FE_Persona_Navigation.md)
// Sidebar visibility logic: persona → grouped nav, capability-filtered, hide empty groups.
import { describe, it, expect } from 'vitest'
import { MODULE_NAV, buildSidebarGroups, type CanFn } from './sidebarNav'
import { getPersona } from './personas'

// Helper: build a `can(cap)` predicate that returns true only for the given caps.
function canOnly(...caps: string[]): CanFn {
  const set = new Set(caps)
  return (cap) => {
    const list = Array.isArray(cap) ? cap : [cap]
    return list.some((c) => set.has(c))
  }
}
const canNone: CanFn = () => false

const persona = (code: string) => {
  const p = getPersona(code)
  if (!p) throw new Error(`persona ${code} not found`)
  return p
}

describe('MODULE_NAV catalog integrity', () => {
  it('every NavItem has label, path, icon; cap (if present) is string or string[]', () => {
    for (const mod of Object.values(MODULE_NAV)) {
      expect(mod.title.length).toBeGreaterThan(0)
      for (const item of mod.items) {
        expect(item.label.length).toBeGreaterThan(0)
        expect(item.path.startsWith('/')).toBe(true)
        expect(item.icon.length).toBeGreaterThan(0)
        if (item.cap !== undefined) {
          const ok = typeof item.cap === 'string' || Array.isArray(item.cap)
          expect(ok).toBe(true)
        }
      }
    }
  })

  it('NO NavItem references a ROLES_* empty stub (cap is the only gate)', () => {
    // Catalog must not carry a `roles` property anymore — capability-only.
    for (const mod of Object.values(MODULE_NAV)) {
      for (const item of mod.items) {
        expect('roles' in (item as unknown as Record<string, unknown>)).toBe(false)
      }
    }
  })
})

describe('buildSidebarGroups — capability filter + grouping (Core Doc §2.1)', () => {
  it('T9: tech caps (pm/repair/calibration read) → PM/CM/Calibration items, NOT compliance/admin/needs', () => {
    const can = canOnly('pm.read', 'repair.read', 'calibration.read')
    const groups = buildSidebarGroups(persona('tech'), can, false)
    const labels = groups.flatMap((g) => g.items.map((i) => i.label))
    // Has maintenance modules
    expect(labels.some((l) => /Bảo trì|sửa chữa|Hiệu chuẩn/i.test(l))).toBe(true)
    // Does NOT leak compliance / admin / needs
    expect(labels.some((l) => /tuân thủ|Quy tắc tuân thủ/i.test(l))).toBe(false)
    expect(labels.some((l) => /Người dùng|Dữ liệu tham chiếu/i.test(l))).toBe(false)
    expect(labels.some((l) => /Đề xuất nhu cầu/i.test(l))).toBe(false)
  })

  it('T10 anti-leak: item with cap the user lacks is hidden', () => {
    // workshop persona includes imm16-less modules; pick PM "Kế hoạch bảo trì" (cap pm.write/create)
    const noWrite = canOnly('pm.read') // read only
    const groups = buildSidebarGroups(persona('workshop'), noWrite, false)
    const labels = groups.flatMap((g) => g.items.map((i) => i.label))
    // "Kế hoạch bảo trì" requires manage-cap → must be hidden when only pm.read
    expect(labels).not.toContain('Kế hoạch bảo trì')
    // but read-level "Lệnh bảo trì" (no cap or pm.read) stays
    expect(labels).toContain('Lệnh bảo trì')
  })

  it('T11: a group with no visible items after filter is not rendered', () => {
    // admin persona has a "system" module group; with no caps + not superuser,
    // capability-gated items vanish; any fully-gated group must drop out.
    const groups = buildSidebarGroups(persona('admin'), canNone, false)
    for (const g of groups) {
      expect(g.items.length).toBeGreaterThan(0) // never an empty group
    }
  })

  it('T12: superuser sees every item of the persona regardless of capability', () => {
    const groupsSuper = buildSidebarGroups(persona('admin'), canNone, true)
    const totalSuper = groupsSuper.reduce((n, g) => n + g.items.length, 0)
    const groupsNone = buildSidebarGroups(persona('admin'), canNone, false)
    const totalNone = groupsNone.reduce((n, g) => n + g.items.length, 0)
    expect(totalSuper).toBeGreaterThan(totalNone)
  })

  it('T13: dedupe item by path across multiple modules of one persona', () => {
    // workshop includes both imm15 and master which both list "/asset-transfers".
    const groups = buildSidebarGroups(persona('workshop'), () => true, true)
    const paths = groups.flatMap((g) => g.items.map((i) => i.path))
    const dupes = paths.filter((p, i) => paths.indexOf(p) !== i)
    expect(dupes).toEqual([])
  })

  it('items WITHOUT cap are visible to any authenticated user (e.g. dashboards, QR scan)', () => {
    const groups = buildSidebarGroups(persona('tech'), canNone, false)
    const labels = groups.flatMap((g) => g.items.map((i) => i.label))
    // QR scan (master) has no cap → visible even with zero caps
    expect(labels.some((l) => /Quét mã QR/i.test(l))).toBe(true)
  })

  it('group order follows persona.modules order', () => {
    const p = persona('workshop') // modules: imm08, imm09, imm11, imm12, master, imm15
    const groups = buildSidebarGroups(p, () => true, true)
    const titles = groups.map((g) => g.title)
    const idxPM = titles.findIndex((t) => /PM|Bảo trì định kỳ/i.test(t))
    const idxMaster = titles.findIndex((t) => /Tài sản|Đối tác/i.test(t))
    expect(idxPM).toBeGreaterThanOrEqual(0)
    expect(idxMaster).toBeGreaterThan(idxPM)
  })
})
