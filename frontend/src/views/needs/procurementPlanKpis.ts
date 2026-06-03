// Copyright (c) 2026, AssetCore Team
// IMM-01 — KPI strip math for ProcurementPlanListView (Core Doc 06_Frontend_Design).
// Pure, source-backed: tính trực tiếp từ list items đã có sẵn (list_procurement_plans),
// KHÔNG gọi endpoint KPI riêng, KHÔNG bịa số. Tiles tĩnh (không dead-end nav).
import type { ProcurementPlanListItem } from '@/types/imm01'

export interface ProcurementPlanKpis {
  total: number
  active: number
  totalBudget: number
  avgUtilization: number
}

/**
 * Derive 4 KPI từ danh sách kế hoạch:
 * - total: tổng số kế hoạch
 * - active: số kế hoạch ở workflow_state 'Active'
 * - totalBudget: tổng budget_envelope
 * - avgUtilization: trung bình utilization_pct (chỉ tính item có giá trị số)
 */
export function computeProcurementPlanKpis(
  plans: ProcurementPlanListItem[],
): ProcurementPlanKpis {
  const total = plans.length
  const active = plans.filter((p) => p.workflow_state === 'Active').length
  const totalBudget = plans.reduce((s, p) => s + (Number(p.budget_envelope) || 0), 0)

  const utils = plans
    .map((p) => p.utilization_pct)
    .filter((u): u is number => typeof u === 'number' && !Number.isNaN(u))
  const avgUtilization = utils.length
    ? utils.reduce((s, u) => s + u, 0) / utils.length
    : 0

  return { total, active, totalBudget, avgUtilization }
}
