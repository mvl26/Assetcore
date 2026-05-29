// TDD — Core Doc §9 (docs/architecture/FE_Persona_Navigation.md)
import { describe, it, expect } from 'vitest'
import {
  PERSONAS,
  derivePersonas,
  resolveCurrentPersona,
  getPersona,
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
