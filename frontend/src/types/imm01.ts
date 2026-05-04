// Copyright (c) 2026, AssetCore Team
// TypeScript interfaces — IMM-01 Đánh giá nhu cầu & dự toán (Wave 2)

export type RequestType = 'New' | 'Replacement' | 'Upgrade' | 'Add-on'
export type PriorityClass = '' | 'P1' | 'P2' | 'P3' | 'P4'
export type FundingSource = '' | 'NSNN' | 'Tài trợ' | 'Xã hội hóa' | 'BHYT' | 'Khác'

export type NeedsRequestState =
  | 'Draft' | 'Submitted' | 'Reviewing' | 'Prioritized'
  | 'Budgeted' | 'Pending Approval' | 'Approved' | 'Rejected'

export type ProcurementPlanState = 'Draft' | 'Approved' | 'Active' | 'Closed'

export type ScoringCriterion =
  | 'clinical_impact' | 'risk' | 'utilization_gap'
  | 'replacement_signal' | 'compliance_gap' | 'budget_fit'

export interface NeedsPriorityScoringRow {
  name?: string
  idx?: number
  criterion: ScoringCriterion
  score: number  // 1-5
  weight_pct?: number
  weighted?: number
  evidence?: string
}

export interface BudgetEstimateLineRow {
  name?: string
  idx?: number
  budget_section: 'CAPEX' | 'OPEX'
  line_type: string
  year_offset?: number
  qty?: number
  unit_cost: number
  amount?: number
  benchmark_source?: string
  notes?: string
}

export interface NeedsRequestListItem {
  name: string
  request_type: RequestType
  device_model_ref: string
  requesting_department: string
  quantity: number
  weighted_score?: number
  priority_class?: PriorityClass
  workflow_state: NeedsRequestState
  request_date: string
  total_capex?: number
  tco_5y?: number
}

export interface NeedsRequestListResponse {
  items: NeedsRequestListItem[]
  total: number
  page: number
  page_size: number
}

export interface NeedsRequestDoc {
  name?: string
  request_type: RequestType
  request_date: string
  requesting_department: string
  clinical_head: string
  device_model_ref: string
  device_category?: string
  quantity: number
  target_year: number
  priority_class?: PriorityClass
  weighted_score?: number
  clinical_justification: string
  replacement_for_asset?: string
  utilization_pct_12m?: number
  downtime_hr_12m?: number
  compliance_driven?: 0 | 1
  scoring_rows: NeedsPriorityScoringRow[]
  budget_lines: BudgetEstimateLineRow[]
  total_capex?: number
  total_opex_5y?: number
  tco_5y?: number
  funding_source?: FundingSource
  funding_evidence?: string
  board_approver?: string
  approval_date?: string
  rejection_reason?: string
  procurement_plan?: string
  workflow_state?: NeedsRequestState
  docstatus?: 0 | 1 | 2
}

export interface NeedsRequestFilters {
  workflow_state?: NeedsRequestState | NeedsRequestState[]
  requesting_department?: string
  request_type?: RequestType
  priority_class?: PriorityClass
  target_year?: number
}

export interface ProcurementPlanLineRow {
  name?: string
  idx?: number
  needs_request: string
  priority_rank?: number
  weighted_score?: number
  allocated_budget: number
  target_quarter?: '' | 'Q1' | 'Q2' | 'Q3' | 'Q4'
  status?: 'Pending Spec' | 'In Spec' | 'In Procurement' | 'Awarded' | 'Cancelled'
}

export interface ProcurementPlanListItem {
  name: string
  plan_period: 'Q1' | 'Q2' | 'Q3' | 'Q4' | 'Annual'
  plan_year: number
  budget_envelope: number
  allocated_capex?: number
  utilization_pct?: number
  workflow_state: ProcurementPlanState
}

export interface DemandForecastItem {
  name: string
  forecast_year: number
  horizon_years: number
  device_category?: string
  projected_qty?: number
  projected_capex?: number
  accuracy_prev?: number
}

export interface DashboardKpis {
  backlog_over_30d: number
  by_state: Record<string, number>
  g01_pass_rate: number
  envelope_utilization: number
}
