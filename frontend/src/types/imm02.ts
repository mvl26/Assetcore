// Copyright (c) 2026, AssetCore Team
// Types — IMM-02 Tech Spec & Market Analysis

export type SpecState =
  | 'Draft' | 'Reviewing' | 'Benchmarked' | 'Risk Assessed'
  | 'Pending Approval' | 'Locked' | 'Withdrawn'

export type RequirementGroup =
  | 'Performance' | 'Safety' | 'Connectivity' | 'Power'
  | 'Mechanical' | 'Software' | 'Service' | 'Compliance'

export interface TechSpecRequirement {
  name?: string
  idx?: number
  seq?: number
  group: RequirementGroup
  parameter: string
  value_or_range?: string
  unit?: string
  is_mandatory: 0 | 1
  weight?: number
  test_method?: string
  evidence?: string
  remark?: string
}

export interface InfraDomain {
  name?: string
  idx?: number
  domain: 'Electrical' | 'Medical Gas' | 'Network/IT' | 'HIS-PACS-LIS' | 'HVAC' | 'Space-Layout'
  current_state?: string
  required_state?: string
  compatibility_status: 'Compatible' | 'Need Upgrade' | 'Need Major Upgrade' | 'N/A'
  upgrade_owner?: string
  upgrade_eta?: string
  upgrade_cost_estimate?: number
  evidence?: string
}

export interface TechSpecListItem {
  name: string
  device_model_ref: string
  version: string
  candidate_count: number
  lock_in_score?: number
  workflow_state: SpecState
  source_plan?: string
  source_needs_request: string
  draft_date: string
  total_mandatory?: number
}

export interface TechSpecDoc {
  name?: string
  draft_date: string
  version: string
  parent_spec?: string
  source_plan: string
  source_plan_line?: string
  source_needs_request: string
  device_model_ref: string
  device_category?: string
  quantity: number
  spec_template_ref?: string
  total_mandatory?: number
  total_optional?: number
  requirements: TechSpecRequirement[]
  documents?: { name?: string; doc_type: string; version?: string; issued_date?: string; file_attachment: string }[]
  benchmark_ref?: string
  candidate_count?: number
  infra_compat: InfraDomain[]
  infra_status_overall?: string
  lock_in_risk_ref?: string
  lock_in_score?: number
  mitigation_plan?: string
  mitigation_evidence?: string
  approver?: string
  approval_date?: string
  withdrawal_reason?: string
  workflow_state?: SpecState
  docstatus?: 0 | 1 | 2
}

export interface DashboardKpis {
  by_state: Record<string, number>
  avg_lock_in_score: number
  backlog_over_30d: number
}
