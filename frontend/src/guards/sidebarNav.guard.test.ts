// TDD — Core Doc §2.1 + §9 (docs/architecture/FE_Persona_Navigation.md)
// Sidebar visibility logic: persona → grouped nav, capability-filtered, hide empty groups.
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { SRC } from '@/test/paths'
import { describe, it, expect } from 'vitest'
import {
  MODULE_NAV,
  buildSidebarGroups,
  buildSidebarGroupsForRoles,
  itemVisible,
  FINANCE_READ_CAPS,
  type CanFn,
} from '@/constants/sidebarNav'
import { getPersona, derivePersonas, PERSONAS } from '@/constants/personas'

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
    // Guard chống trùng path khi 1 persona gộp nhiều module (vd /assets ở master
    // + nhiều nơi). workshop persona: đảm bảo không có path lặp sau khi UNION module.
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

describe('buildSidebarGroupsForRoles — union from real roles (Core Doc §7.ter)', () => {
  it('T23: superuser → union of every module with ≥1 item (= admin Phase 1.1 set)', () => {
    const personas = derivePersonas(['AssetCore Super Admin'])
    const union = buildSidebarGroupsForRoles(personas, () => true, true)
    const adminOnly = buildSidebarGroups(persona('admin'), () => true, true)
    const unionPaths = new Set(union.flatMap((g) => g.items.map((i) => i.path)))
    const adminPaths = new Set(adminOnly.flatMap((g) => g.items.map((i) => i.path)))
    // Superuser union must include everything admin persona already showed.
    for (const p of adminPaths) expect(unionPaths.has(p)).toBe(true)
  })

  it('T24: single-persona [tech] == buildSidebarGroups(tech) (back-compat)', () => {
    const can = canOnly('pm.read', 'repair.read', 'calibration.read')
    const single = buildSidebarGroupsForRoles([persona('tech')], can, false)
    const ref = buildSidebarGroups(persona('tech'), can, false)
    expect(single.map((g) => g.title)).toEqual(ref.map((g) => g.title))
    expect(single.flatMap((g) => g.items.map((i) => i.path)))
      .toEqual(ref.flatMap((g) => g.items.map((i) => i.path)))
  })

  it('T25: [tech, store] → UNION has both maintenance AND inventory groups', () => {
    const can = canOnly('pm.read', 'repair.read', 'calibration.read', 'inventory.read')
    const groups = buildSidebarGroupsForRoles(
      [persona('tech'), persona('store')], can, false,
    )
    const labels = groups.flatMap((g) => g.items.map((i) => i.label))
    expect(labels.some((l) => /Bảo trì|sửa chữa/i.test(l))).toBe(true) // tech
    expect(labels.some((l) => /Tồn kho|Phụ tùng/i.test(l))).toBe(true) // store
  })

  it('T26: global path dedupe across personas (/asset-transfers once)', () => {
    const personas = derivePersonas(['AssetCore Super Admin'])
    const groups = buildSidebarGroupsForRoles(personas, () => true, true)
    const paths = groups.flatMap((g) => g.items.map((i) => i.path))
    const dupes = paths.filter((p, i) => paths.indexOf(p) !== i)
    expect(dupes).toEqual([])
  })

  it('T27: empty personas → no nav', () => {
    expect(buildSidebarGroupsForRoles([], () => true, false)).toEqual([])
    expect(buildSidebarGroupsForRoles(derivePersonas([]), () => true, false)).toEqual([])
  })

  it('union derives from real-role personas: PM User + Inventory Manager sees both domains', () => {
    const personas = derivePersonas(['PM User', 'Inventory Manager'])
    const can = canOnly('pm.read', 'repair.read', 'calibration.read', 'inventory.read', 'inventory.write')
    const groups = buildSidebarGroupsForRoles(personas, can, false)
    const labels = groups.flatMap((g) => g.items.map((i) => i.label))
    expect(labels).toContain('Lệnh bảo trì')   // tech persona (PM User)
    expect(labels).toContain('Tồn kho')         // store persona (Inventory Manager)
  })
})

// ─── §7.septies.3 — mục Khấu hao gate bằng finance OR-cap (VĐ2) ──────────────
describe('§7.septies.3 — /depreciation finance-gate (bịt over-grant doc/training)', () => {
  const depItem = MODULE_NAV.master.items.find((i) => i.path === '/depreciation')!

  it('mục Khấu hao tồn tại trong group master', () => {
    expect(depItem).toBeDefined()
  })

  it('cap mục Khấu hao = FINANCE_READ_CAPS (KHÔNG còn data.read đơn)', () => {
    expect(depItem.cap).toEqual(FINANCE_READ_CAPS)
    // Chốt: data.read KHÔNG đủ một mình (vì mọi user có data.read).
    expect(depItem.cap).not.toBe('data.read')
    expect(FINANCE_READ_CAPS).not.toContain('data.read')
  })

  it('NAV-DEP-1: persona doc (chỉ document/training.read + data.read) → ẩn Khấu hao', () => {
    const can = canOnly('document.read', 'training.read', 'data.read')
    expect(itemVisible(depItem, can, false)).toBe(false)
  })

  it('NAV-DEP-2: opsmgr (needs.read) / tech (pm.read) → hiện Khấu hao', () => {
    expect(itemVisible(depItem, canOnly('needs.read'), false)).toBe(true)
    expect(itemVisible(depItem, canOnly('procurement.read'), false)).toBe(true)
    expect(itemVisible(depItem, canOnly('pm.read'), false)).toBe(true)
    expect(itemVisible(depItem, canOnly('calibration.read'), false)).toBe(true)
  })

  it('store (inventory.read) / clinical (corrective.read) → ẩn Khấu hao', () => {
    expect(itemVisible(depItem, canOnly('inventory.read', 'data.read'), false)).toBe(false)
    expect(itemVisible(depItem, canOnly('corrective.read', 'data.read'), false)).toBe(false)
  })

  it('superuser → hiện (bypass)', () => {
    expect(itemVisible(depItem, canNone, true)).toBe(true)
  })
})

// NAV-SUP-1: group master với can chỉ data.read → /suppliers vẫn hiện (gate data.read)
// nhưng /depreciation ẩn (cần finance cap). Chống regression VĐ2.
describe('§7.septies — master group: suppliers giữ, depreciation ẩn cho data.read-only', () => {
  it('NAV-SUP-1: persona doc với chỉ data.read → thấy NCC, KHÔNG thấy Khấu hao', () => {
    const can = canOnly('data.read', 'document.read', 'training.read')
    const groups = buildSidebarGroups(persona('doc'), can, false)
    const labels = groups.flatMap((g) => g.items.map((i) => i.label))
    expect(labels).toContain('Nhà cung cấp')       // data.read → hiện
    expect(labels).not.toContain('Khấu hao tài sản') // finance cap thiếu → ẩn
  })

  it('persona opsmgr (data.read + needs.read) → thấy CẢ NCC và Khấu hao', () => {
    const can = canOnly('data.read', 'needs.read', 'procurement.read')
    const groups = buildSidebarGroups(persona('opsmgr'), can, false)
    const labels = groups.flatMap((g) => g.items.map((i) => i.label))
    expect(labels).toContain('Nhà cung cấp')
    expect(labels).toContain('Khấu hao tài sản')
  })
})

// UI-SIDEBAR-1 (Core Doc §7.sexies.1): header sidebar (góc trái) KHÔNG render
// NHÃN persona ("Cán bộ hồ sơ" v.v.). Brand tĩnh "AssetCore". Guard chống tái
// xuất nhãn persona ở chrome — source-level (mount nặng + brittle, không cần).
describe('AppSidebar header — không leak nhãn persona', () => {
  // Đường dẫn lấy từ SSoT `src/test/paths.ts` (SPEC §5.2 N5).
  const SIDEBAR_SRC = readFileSync(
    resolve(SRC, 'components/common/AppSidebar.vue'),
    'utf-8',
  )

  it('UI-SIDEBAR-1a: header dùng brand tĩnh, không bind personaTitle', () => {
    // Brand constant phải có; biến personaTitle (label persona) đã bị gỡ.
    expect(SIDEBAR_SRC).toMatch(/BRAND_TITLE\s*=\s*['"]AssetCore['"]/)
    expect(SIDEBAR_SRC).not.toMatch(/\{\{\s*personaTitle\s*\}\}/)
    expect(SIDEBAR_SRC).not.toContain('const personaTitle')
  })

  it('UI-SIDEBAR-1b: không hard-code nhãn persona nào trong template sidebar', () => {
    for (const p of PERSONAS) {
      // label persona (vd "Cán bộ hồ sơ") KHÔNG được xuất hiện literal trong chrome.
      expect(SIDEBAR_SRC).not.toContain(p.label)
    }
  })

  it('UI-SIDEBAR-1c: primaryPersona vẫn dùng cho màu logo (cosmetic), không cho label', () => {
    // primaryPersona còn tồn tại (tô màu + route dashboard) nhưng .label không bind text.
    expect(SIDEBAR_SRC).toContain('primaryPersona')
    expect(SIDEBAR_SRC).toMatch(/personaColor/)
  })
})

// ─── CR-TRF-AUTHZ: link 'Điều chuyển thiết bị' gate theo commissioning.read ─────
// Bug (2026-07-15): NavItem /asset-transfers KHÔNG có `cap` → itemVisible luôn true
// → lọt vào sidebar của persona 'store'/'workshop' (inventory) → click → BE 403.
// BE gate transfer theo Commissioning. Fix: cap='commissioning.read' + chỉ đặt
// item ở group imm13 (bỏ bản sao dưới imm15/Tồn kho). Anti-leak parity FE↔BE.
describe('CR-TRF-AUTHZ — link Điều chuyển gate commissioning.read (anti-leak inventory)', () => {
  const INV_CAPS = ['inventory.read', 'inventory.create', 'inventory.write']
  const transferPaths = (groups: ReturnType<typeof buildSidebarGroupsForRoles>) =>
    groups.flatMap((g) => g.items.map((i) => i.path))

  it('NavItem /asset-transfers gated cap commissioning.read', () => {
    const item = MODULE_NAV.imm13.items.find((i) => i.path === '/asset-transfers')
    expect(item?.cap).toBe('commissioning.read')
  })
  it('/asset-transfers KHÔNG còn nằm trong group imm15 (Tồn kho phụ tùng)', () => {
    expect(MODULE_NAV.imm15.items.some((i) => i.path === '/asset-transfers')).toBe(false)
  })
  it('store persona (inventory-only) KHÔNG thấy /asset-transfers', () => {
    const groups = buildSidebarGroupsForRoles([persona('store')], canOnly(...INV_CAPS), false)
    expect(transferPaths(groups)).not.toContain('/asset-transfers')
  })
  it('workshop persona (không commissioning) KHÔNG thấy /asset-transfers', () => {
    const groups = buildSidebarGroupsForRoles(
      [persona('workshop')],
      canOnly('pm.read', 'repair.read', 'calibration.read', 'corrective.read', ...INV_CAPS),
      false,
    )
    expect(transferPaths(groups)).not.toContain('/asset-transfers')
  })
  it('opsmgr persona (commissioning.read) THẤY /asset-transfers', () => {
    const groups = buildSidebarGroupsForRoles([persona('opsmgr')], canOnly('commissioning.read'), false)
    expect(transferPaths(groups)).toContain('/asset-transfers')
  })
  it('superuser luôn thấy /asset-transfers (bypass cap)', () => {
    const groups = buildSidebarGroupsForRoles([persona('opsmgr')], canNone, true)
    expect(transferPaths(groups)).toContain('/asset-transfers')
  })
})
