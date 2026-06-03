// TDD — IMM-05 Document list filter builders (pure logic)
// Core Doc docs/imm-05/06_Frontend_Design.md §3 (expiry filter dropdown) + §8.
// docs/fe/05-document/documents-list.html (Hết hạn: Mọi/Đã expired/30/60/90 ngày).
//
// These pure builders construct the `DocumentFilters` payload sent to the
// existing BE `assetcore.api.imm05.list_documents`. BE remains the security
// chokepoint (visibility enforced server-side); FE only shapes query intent.
import { describe, it, expect } from 'vitest'
import {
  EXPIRY_OPTIONS,
  KPI_FILTERS,
  buildExpiryFilter,
  buildKpiFilter,
  composeFilters,
  isoDate,
} from './documentFilters'

// Fixed reference date so the date math is deterministic.
const REF = new Date('2026-05-29T00:00:00Z')

describe('isoDate', () => {
  it('formats a Date as yyyy-MM-dd (API transfer format, Core Doc §7.1)', () => {
    expect(isoDate(REF)).toBe('2026-05-29')
  })
  it('offsets by N days', () => {
    expect(isoDate(REF, 30)).toBe('2026-06-28')
    expect(isoDate(REF, 90)).toBe('2026-08-27')
  })
})

describe('EXPIRY_OPTIONS', () => {
  it('matches the Core Doc / docs-fe dropdown set', () => {
    expect(EXPIRY_OPTIONS.map((o) => o.value)).toEqual(['', 'expired', '30', '60', '90'])
  })
  it('every option has a Vietnamese label (LL: 100% Vietnamese UI)', () => {
    for (const o of EXPIRY_OPTIONS) expect(o.label.length).toBeGreaterThan(0)
  })
})

describe('buildExpiryFilter', () => {
  it('returns {} for the "all" option (no expiry constraint)', () => {
    expect(buildExpiryFilter('', REF)).toEqual({})
  })

  it('"expired" maps to workflow_state = Expired (Core Doc §3 + vocab map)', () => {
    expect(buildExpiryFilter('expired', REF)).toEqual({ workflow_state: 'Expired' })
  })

  it('"30" returns Active docs expiring within the next 30 days (between today..today+30)', () => {
    expect(buildExpiryFilter('30', REF)).toEqual({
      workflow_state: 'Active',
      expiry_date: ['between', ['2026-05-29', '2026-06-28']],
    })
  })

  it('"90" widens the upper bound to today+90', () => {
    const f = buildExpiryFilter('90', REF)
    expect((f.expiry_date as [string, [string, string]])[1][1]).toBe('2026-08-27')
  })

  it('ignores unknown options safely (returns {})', () => {
    expect(buildExpiryFilter('999', REF)).toEqual({})
  })
})

describe('KPI_FILTERS / buildKpiFilter', () => {
  it('exposes the four dashboard KPI kinds', () => {
    expect(KPI_FILTERS.map((k) => k.kind)).toEqual([
      'active',
      'expiring',
      'expired',
      'missing',
    ])
  })

  it('"active" filters by workflow_state Active', () => {
    expect(buildKpiFilter('active', REF)).toEqual({ workflow_state: 'Active' })
  })

  it('"expired" filters by workflow_state Expired', () => {
    expect(buildKpiFilter('expired', REF)).toEqual({ workflow_state: 'Expired' })
  })

  it('"expiring" reuses the 90-day expiry window (no dead-end)', () => {
    expect(buildKpiFilter('expiring', REF)).toEqual(buildExpiryFilter('90', REF))
  })

  it('"missing" is not a list filter — returns null (tile render tĩnh, không điều hướng)', () => {
    expect(buildKpiFilter('missing', REF)).toBeNull()
  })

  it('non-list-filter tiles are flagged clickable:false (no misleading navigation)', () => {
    // Mọi tile có buildKpiFilter === null PHẢI clickable:false, và ngược lại.
    for (const tile of KPI_FILTERS) {
      const hasFilter = buildKpiFilter(tile.kind, REF) !== null
      expect(tile.clickable).toBe(hasFilter)
    }
    // 'missing' cụ thể: tĩnh + có hint thống kê.
    const missing = KPI_FILTERS.find((k) => k.kind === 'missing')!
    expect(missing.clickable).toBe(false)
    expect(missing.hint).toBeTruthy()
  })
})

describe('composeFilters', () => {
  it('drops empty-string values so BE does not receive blank filters', () => {
    expect(composeFilters({ doc_category: '', workflow_state: 'Active', asset_ref: '' })).toEqual({
      workflow_state: 'Active',
    })
  })

  it('keeps non-string structured filters (e.g. expiry_date tuple)', () => {
    const f = composeFilters({
      workflow_state: 'Active',
      expiry_date: ['between', ['2026-05-29', '2026-06-28']],
    })
    expect(f).toEqual({
      workflow_state: 'Active',
      expiry_date: ['between', ['2026-05-29', '2026-06-28']],
    })
  })

  it('merges later sources over earlier ones', () => {
    const f = composeFilters({ workflow_state: 'Active' }, { workflow_state: 'Expired' })
    expect(f.workflow_state).toBe('Expired')
  })

  it('returns {} when everything is empty', () => {
    expect(composeFilters({ doc_category: '', asset_ref: '' }, {})).toEqual({})
  })
})
