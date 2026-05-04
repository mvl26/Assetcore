// Copyright (c) 2026, AssetCore Team
// API calls — IMM-01 Đánh giá nhu cầu & dự toán (Wave 2)

import { frappeGet, frappePost } from './helpers'
import type {
  NeedsRequestDoc, NeedsRequestListResponse, NeedsRequestFilters,
  NeedsPriorityScoringRow, BudgetEstimateLineRow,
  ProcurementPlanListItem, DemandForecastItem, DashboardKpis, FundingSource,
} from '@/types/imm01'

const BASE = '/api/method/assetcore.api.imm01'

// ─── Needs Request ────────────────────────────────────────────────────────────

export function listNeedsRequests(
  filters: NeedsRequestFilters = {},
  page = 1,
  page_size = 20,
  order_by = 'request_date desc',
): Promise<NeedsRequestListResponse> {
  return frappeGet(`${BASE}.list_needs_requests`, {
    filters: JSON.stringify(filters), page, page_size, order_by,
  })
}

export function getNeedsRequest(name: string): Promise<NeedsRequestDoc> {
  return frappeGet(`${BASE}.get_needs_request`, { name })
}

export function createNeedsRequest(payload: Partial<NeedsRequestDoc>): Promise<{
  name: string; workflow_state: string
}> {
  return frappePost(`${BASE}.create_needs_request`, { payload: JSON.stringify(payload) })
}

export function updateNeedsRequest(name: string, payload: Partial<NeedsRequestDoc>): Promise<{
  name: string; workflow_state: string
}> {
  return frappePost(`${BASE}.update_needs_request`, { name, payload: JSON.stringify(payload) })
}

export function submitNeedsRequest(name: string): Promise<{ name: string; workflow_state: string }> {
  return frappePost(`${BASE}.submit_needs_request`, { name })
}

export function transitionWorkflow(name: string, action: string): Promise<{
  name: string; workflow_state: string; docstatus: number
}> {
  return frappePost(`${BASE}.transition_workflow`, { name, action })
}

export function scoreNeedsRequest(
  name: string, scoring_rows: NeedsPriorityScoringRow[],
): Promise<{ weighted_score: number; priority_class: string }> {
  return frappePost(`${BASE}.score_needs_request`, {
    name, scoring_rows: JSON.stringify(scoring_rows),
  })
}

export function submitBudgetEstimate(
  name: string,
  budget_lines: BudgetEstimateLineRow[],
  funding_source?: FundingSource,
  funding_evidence?: string,
): Promise<{ total_capex: number; total_opex_5y: number; tco_5y: number }> {
  return frappePost(`${BASE}.submit_budget_estimate`, {
    name, budget_lines: JSON.stringify(budget_lines),
    funding_source, funding_evidence,
  })
}

export function approveNeedsRequest(name: string, board_approver: string, remarks = ''): Promise<{
  name: string; workflow_state: string
}> {
  return frappePost(`${BASE}.approve_needs_request`, { name, board_approver, remarks })
}

export function rejectNeedsRequest(name: string, rejection_reason: string): Promise<{
  name: string; workflow_state: string
}> {
  return frappePost(`${BASE}.reject_needs_request`, { name, rejection_reason })
}

// ─── Procurement Plan ─────────────────────────────────────────────────────────

export function listProcurementPlans(filters: Record<string, unknown> = {}, page = 1, page_size = 20):
    Promise<{ items: ProcurementPlanListItem[]; total: number; page: number; page_size: number }> {
  return frappeGet(`${BASE}.list_procurement_plans`, {
    filters: JSON.stringify(filters), page, page_size,
  })
}

export function rollIntoPlan(plan_year: number, plan_period: string, needs_requests: string[]): Promise<{ name: string }> {
  return frappePost(`${BASE}.roll_into_plan`, {
    plan_year, plan_period, needs_requests: JSON.stringify(needs_requests),
  })
}

// ─── Demand Forecast & Dashboard ──────────────────────────────────────────────

export function getDemandForecast(forecast_year: number, device_category?: string):
    Promise<{ items: DemandForecastItem[] }> {
  return frappeGet(`${BASE}.get_demand_forecast`, { forecast_year, device_category })
}

export function getDashboardKpis(period?: string): Promise<DashboardKpis> {
  return frappeGet(`${BASE}.dashboard_kpis`, { period })
}
