// TDD — IMM-01 ProcurementPlanList KPI strip (Core Doc 06_Frontend_Design).
// Source-backed math, no fabricated numbers; verifies edge cases (empty list,
// partial utilization_pct) per docs/imm-01.
import { describe, it, expect } from 'vitest'
import { computeProcurementPlanKpis } from './procurementPlanKpis'
import type { ProcurementPlanListItem } from '@/types/imm01'

function plan(p: Partial<ProcurementPlanListItem>): ProcurementPlanListItem {
  return {
    name: p.name ?? 'PP-X',
    plan_period: p.plan_period ?? 'Q1',
    plan_year: p.plan_year ?? 2026,
    budget_envelope: p.budget_envelope ?? 0,
    allocated_capex: p.allocated_capex,
    utilization_pct: p.utilization_pct,
    workflow_state: p.workflow_state ?? 'Draft',
  }
}

describe('computeProcurementPlanKpis', () => {
  it('K1: empty list → all zero (no NaN)', () => {
    const k = computeProcurementPlanKpis([])
    expect(k).toEqual({ total: 0, active: 0, totalBudget: 0, avgUtilization: 0 })
  })

  it('K2: counts total and Active', () => {
    const k = computeProcurementPlanKpis([
      plan({ workflow_state: 'Active' }),
      plan({ workflow_state: 'Active' }),
      plan({ workflow_state: 'Draft' }),
      plan({ workflow_state: 'Closed' }),
    ])
    expect(k.total).toBe(4)
    expect(k.active).toBe(2)
  })

  it('K3: sums budget_envelope', () => {
    const k = computeProcurementPlanKpis([
      plan({ budget_envelope: 1_000_000 }),
      plan({ budget_envelope: 2_500_000 }),
    ])
    expect(k.totalBudget).toBe(3_500_000)
  })

  it('K4: avg utilization ignores items without utilization_pct', () => {
    const k = computeProcurementPlanKpis([
      plan({ utilization_pct: 80 }),
      plan({ utilization_pct: 40 }),
      plan({ utilization_pct: undefined }), // excluded
    ])
    expect(k.avgUtilization).toBe(60) // (80+40)/2, not /3
  })

  it('K5: no utilization data → avg 0, not NaN', () => {
    const k = computeProcurementPlanKpis([plan({ utilization_pct: undefined })])
    expect(k.avgUtilization).toBe(0)
    expect(Number.isNaN(k.avgUtilization)).toBe(false)
  })
})
