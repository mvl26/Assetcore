// TDD — Core Doc §9 (docs/architecture/FE_Persona_Navigation.md)
import { describe, it, expect } from 'vitest'
import {
  PERSONAS,
  derivePersonas,
  derivePrimaryPersona,
  resolveCurrentPersona,
  getPersona,
  roleProfileForPersona,
  personaForRoleProfile,
  type Persona,
} from './personas'

const codes = (ps: Persona[]) => ps.map((p) => p.code)

describe('derivePersonas — RBAC inference (Core Doc §3)', () => {
  it('T1: AssetCore Super Admin → all 8 personas', () => {
    const ps = derivePersonas(['AssetCore Super Admin'])
    expect(ps).toHaveLength(8)
    expect(codes(ps)).toEqual(
      expect.arrayContaining(['admin', 'opsmgr', 'workshop', 'tech', 'clinical', 'doc', 'store', 'qa']),
    )
  })

  it('T1b: Frappe-native System Manager / Administrator also → all 8', () => {
    expect(derivePersonas(['System Manager'])).toHaveLength(8)
    expect(derivePersonas(['Administrator'])).toHaveLength(8)
  })

  it('T2: only PM User → contains tech, NOT workshop/admin', () => {
    const c = codes(derivePersonas(['PM User']))
    expect(c).toContain('tech')
    expect(c).not.toContain('workshop')
    expect(c).not.toContain('admin')
  })

  it('T3: Inventory Manager → contains store', () => {
    expect(codes(derivePersonas(['Inventory Manager']))).toContain('store')
  })

  it('T3b: Compliance/Auditor → qa; Document Manager → doc; Corrective User → clinical', () => {
    expect(codes(derivePersonas(['AssetCore Auditor']))).toContain('qa')
    expect(codes(derivePersonas(['Document Manager']))).toContain('doc')
    expect(codes(derivePersonas(['Corrective User']))).toContain('clinical')
  })

  it('T4: no matching role → empty array', () => {
    expect(derivePersonas([])).toEqual([])
    expect(derivePersonas(['Some Random Role', 'AssetCore System User'])).toEqual([])
  })

  it('inference source is roles (imm_roles legacy / empty) — union still works', () => {
    // imm_roles is the legacy "IMM "-prefixed filter (empty for current roles);
    // passing roles via the second arg must still resolve.
    expect(codes(derivePersonas([], ['PM Manager']))).toContain('workshop')
  })

  it('result is sorted by rank descending', () => {
    const ps = derivePersonas(['AssetCore Super Admin'])
    const ranks = ps.map((p) => p.rank)
    expect(ranks).toEqual([...ranks].sort((a, b) => b - a))
  })

  it('Vendor Engineer has NO persona (kept isolated)', () => {
    expect(derivePersonas(['Vendor Engineer'])).toEqual([])
  })
})

describe('resolveCurrentPersona — persistence + fallback (Core Doc §4)', () => {
  const avail = derivePersonas(['AssetCore Super Admin']) // all 8

  it('T5a: valid persisted code is kept', () => {
    expect(resolveCurrentPersona('tech', avail)?.code).toBe('tech')
  })

  it('T5b: invalid persisted → fallback highest rank (admin=100)', () => {
    expect(resolveCurrentPersona('nonsense', avail)?.code).toBe('admin')
    expect(resolveCurrentPersona(null, avail)?.code).toBe('admin')
  })

  it('T8 anti-leak: persisted=admin but user only PM User → resolves to tech, never admin', () => {
    const techOnly = derivePersonas(['PM User'])
    const current = resolveCurrentPersona('admin', techOnly)
    expect(current?.code).toBe('tech')
    expect(current?.code).not.toBe('admin')
  })

  it('empty available → null (shell minimal)', () => {
    expect(resolveCurrentPersona('admin', [])).toBeNull()
  })
})

describe('derivePrimaryPersona — Phase 1.2 (Core Doc §7.ter)', () => {
  it('T20: superuser → primary persona admin (rank 100)', () => {
    expect(derivePrimaryPersona(derivePersonas(['AssetCore Super Admin']))?.code).toBe('admin')
  })

  it('T21: empty → null', () => {
    expect(derivePrimaryPersona([])).toBeNull()
    expect(derivePrimaryPersona(derivePersonas([]))).toBeNull()
  })

  it('T22: multi-role picks highest rank (tech 40 > store 35)', () => {
    expect(derivePrimaryPersona(derivePersonas(['Inventory User', 'PM User']))?.code).toBe('tech')
  })

  it('order-independent: result is rank-max regardless of input order', () => {
    const a = derivePrimaryPersona(derivePersonas(['PM User', 'Inventory User']))
    const b = derivePrimaryPersona(derivePersonas(['Inventory User', 'PM User']))
    expect(a?.code).toBe(b?.code)
  })

  // ── Role Profile precedence — regression 2026-06-02 ────────────────────────
  // Bug: Corrective Manager ∈ inferenceRoles của CẢ workshop (rank 60) lẫn
  // clinical (rank 30). User "Trưởng khoa lâm sàng" (role profile = clinical)
  // bị gắn nhãn SAI "Trưởng xưởng kỹ thuật" vì rank thuần thắng.
  it('T23: role profile khớp chính xác thắng rank (clinical, không phải workshop)', () => {
    const avail = derivePersonas(['Corrective Manager', 'Corrective User'])
    // không có role profile → rank-winner = workshop (bug cũ)
    expect(derivePrimaryPersona(avail)?.code).toBe('workshop')
    // có role profile clinical → đúng persona clinical
    expect(derivePrimaryPersona(avail, 'Trưởng khoa lâm sàng')?.code).toBe('clinical')
  })

  it('T24: role profile không khớp / null → fallback rank cao nhất', () => {
    const avail = derivePersonas(['Corrective Manager'])
    expect(derivePrimaryPersona(avail, null)?.code).toBe('workshop')
    expect(derivePrimaryPersona(avail, 'Profile Không Tồn Tại')?.code).toBe('workshop')
  })

  it('T25: role profile khớp nhưng persona KHÔNG trong available → fallback (không leak)', () => {
    // user chỉ có role tech, nhưng profile name trỏ admin → KHÔNG được nhảy lên admin
    const techOnly = derivePersonas(['PM User'])
    expect(derivePrimaryPersona(techOnly, 'Quản trị viên IT')?.code).toBe('tech')
  })
})

describe('catalog integrity', () => {
  it('exactly 8 personas with unique codes', () => {
    expect(PERSONAS).toHaveLength(8)
    expect(new Set(PERSONAS.map((p) => p.code)).size).toBe(8)
  })

  it('every persona has Vietnamese label, hex color, ≥1 inferenceRole, ≥1 module', () => {
    for (const p of PERSONAS) {
      expect(p.label.length).toBeGreaterThan(0)
      expect(p.color).toMatch(/^#[0-9A-Fa-f]{6}$/)
      expect(p.inferenceRoles.length).toBeGreaterThan(0)
      expect(p.modules.length).toBeGreaterThan(0)
    }
  })

  it('getPersona resolves by code, null otherwise', () => {
    expect(getPersona('admin')?.code).toBe('admin')
    expect(getPersona('nope')).toBeNull()
    expect(getPersona(null)).toBeNull()
  })
})

describe('persona ↔ Role Profile mapping — Phase 1.4 (Core Doc §7.quinquies)', () => {
  // Tên 8 Role Profile BE seed (ROLE_PROFILE_CATALOG) — khớp CHÍNH XÁC.
  const EXPECTED: Record<string, string> = {
    admin: 'Quản trị viên IT',
    opsmgr: 'Trưởng phòng VT-TTBYT',
    workshop: 'Trưởng xưởng kỹ thuật',
    tech: 'Kỹ thuật viên',
    qa: 'Cán bộ QA / Kiểm toán',
    doc: 'Cán bộ hồ sơ',
    store: 'Thủ kho phụ tùng',
    clinical: 'Trưởng khoa lâm sàng',
  }

  it('TRP15: every persona has a non-empty, unique roleProfile matching BE catalog', () => {
    const profiles = PERSONAS.map((p) => p.roleProfile)
    for (const p of profiles) expect(p.length).toBeGreaterThan(0)
    expect(new Set(profiles).size).toBe(PERSONAS.length) // unique
    for (const p of PERSONAS) expect(p.roleProfile).toBe(EXPECTED[p.code])
  })

  it('TRP16: roleProfileForPersona resolves code → profile name; unknown → null', () => {
    expect(roleProfileForPersona('tech')).toBe('Kỹ thuật viên')
    expect(roleProfileForPersona('store')).toBe('Thủ kho phụ tùng')
    expect(roleProfileForPersona('khongton')).toBeNull()
    expect(roleProfileForPersona(null)).toBeNull()
  })

  it('TRP16b: personaForRoleProfile is the inverse (round-trip)', () => {
    expect(personaForRoleProfile('Kỹ thuật viên')?.code).toBe('tech')
    expect(personaForRoleProfile('Quản trị viên IT')?.code).toBe('admin')
    expect(personaForRoleProfile('Không tồn tại')).toBeNull()
    expect(personaForRoleProfile(null)).toBeNull()
    // round-trip cả 8
    for (const p of PERSONAS) {
      expect(personaForRoleProfile(roleProfileForPersona(p.code))?.code).toBe(p.code)
    }
  })
})

// ─── CR-TRF-AUTHZ: 'Điều chuyển thiết bị' (imm13) thuộc audience Commissioning ──
// Bug (2026-07-15): persona 'store' (Thủ kho, chỉ inventory) được gán module imm13
// → thấy link điều chuyển nhưng BE (commissioning domain) 403. Fix: chuyển module
// điều chuyển sang persona commissioning (opsmgr = Trưởng phòng VT-TTBYT), gỡ khỏi
// store. KHÔNG cấp quyền BE mới — chỉ align nav-audience với BE enforcement.
describe('CR-TRF-AUTHZ — module điều chuyển (imm13) = Commissioning audience', () => {
  it('opsmgr (Trưởng phòng VT-TTBYT) có imm13 (commissioning owns transfers)', () => {
    expect(getPersona('opsmgr')!.modules).toContain('imm13')
  })
  it('store (Thủ kho phụ tùng) KHÔNG có imm13', () => {
    expect(getPersona('store')!.modules).not.toContain('imm13')
  })
})
