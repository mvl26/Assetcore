// Copyright (c) 2026, AssetCore Team
// API client cho Module IMM-16 — Compliance Monitoring & CAPA
//
// Mirror BE: assetcore/api/imm16.py
// Spec:     docs/imm-16/05_API_Specification.md

import { frappeGet, frappePost } from './helpers'

const BASE = '/api/method/assetcore.api.imm16'

// ─── Types ────────────────────────────────────────────────────────────────────

export type FindingSeverity = 'Low' | 'Medium' | 'High' | 'Critical'

export type FindingStatus =
  | 'Open'
  | 'Under Review'
  | 'Confirmed NC'
  | 'False Positive'
  | 'Resolved'
  | 'Waived'
  | 'Closed'

export interface ComplianceRule {
  name: string
  rule_code: string
  rule_name: string
  source_module: string
  category: string
  severity: FindingSeverity
  evaluation_frequency: string
  is_active: 0 | 1
  version?: string
  previous_version?: string
  threshold_definition?: string
  data_source_doctype?: string
  data_source_field?: string
  owner_role?: string
  qms_doc_ref?: string
  regulatory_reference?: string
  effective_date?: string
  change_summary?: string
}

export interface ComplianceFinding {
  name: string
  rule: string
  detected_date: string
  asset: string | null
  asset_name?: string
  rule_name?: string
  responsible_dept: string | null
  responsible_dept_name?: string
  notes?: string
  severity: FindingSeverity
  current_value: string | null
  threshold_value: string | null
  status: FindingStatus
  capa_ref: string | null
  evaluation_date: string
  workflow_state?: string
}

export interface InternalAudit {
  name: string
  audit_code: string
  audit_type: string
  planned_start: string
  planned_end: string
  actual_start?: string
  actual_end?: string
  lead_auditor: string
  status: 'Planned' | 'In Progress' | 'Reporting' | 'Closed'
  findings_count: number
}

export type CapaWorkflowState =
  | 'Open'
  | 'Investigating'
  | 'Action Plan'
  | 'Implementation'
  | 'Verification'
  | 'Closed'
  | 'Re-opened'

export interface CapaRecord {
  name: string
  asset: string
  severity: string
  status: string
  workflow_state: CapaWorkflowState
  source_type: string
  source_ref: string | null
  due_date: string | null
  closed_date: string | null
  effectiveness_check: 'Effective' | 'Partially Effective' | 'Not Effective' | null
  imm_root_cause_method?: string | null
  imm_risk_level?: 'Low' | 'Medium' | 'High' | 'Critical'
  imm_reopen_count?: number
  imm_compliance_finding_ref?: string | null
}

export interface ComplianceScorecard {
  name: string
  period_year: number
  period_month: number
  scope: string
  score_pct: number
  trend_vs_prev_month: number
  capa_open_count: number
  capa_overdue_count: number
  is_published: 0 | 1
  published_at?: string | null
  approved_by_for_review?: string | null
}

export type MRStatus = 'Draft' | 'Held' | 'Minutes Approved' | 'Closed'

export interface MRAttendee {
  user: string
  user_name?: string
  role_title?: string
  present?: 0 | 1 | boolean
  signed?: 0 | 1 | boolean
}

export interface MROutputActionRow {
  action_description: string
  responsible: string
  responsible_name?: string
  due_date?: string
  priority?: 'High' | 'Medium' | 'Low'
  status?: 'Open' | 'In Progress' | 'Closed'
  notes?: string
}

export interface ManagementReview {
  name: string
  quarter: string
  review_date: string
  chair: string
  chair_name?: string
  status: MRStatus
  workflow_state?: string
  scorecard_ref?: string
  scorecard_score_pct?: number
  scorecard_period?: string
  scorecard_published?: 0 | 1
  next_review_date?: string
  minutes_doc?: string
  inputs_summary?: string
  audit_summary?: string
  capa_summary?: string
  capa_effectiveness?: string
  training_compliance?: string
  risk_review?: string
  qms_changes_decided?: string
  attendees?: MRAttendee[]
  output_actions?: MROutputActionRow[]
}

export interface DashboardKpis {
  overall_compliance_pct: number
  findings_open: number
  findings_critical: number
  capa_open: number
  capa_overdue: number
  audits_in_progress: number
  mr_quarterly_status: 'Done' | 'Pending' | 'Overdue'
}

export interface DashboardStats {
  kpis: DashboardKpis
  trend_12m: { month: string; score_pct: number }[]
  top_modules_low: { module: string; score: number }[]
  recent_findings: ComplianceFinding[]
}

export interface HeatmapCell {
  module: string
  dept: string
  module_label?: string
  dept_label?: string
  score: number
  findings_count: number
}

export interface ComplianceHeatmap {
  modules: string[]
  departments: string[]
  module_labels?: Record<string, string>
  department_labels?: Record<string, string>
  matrix: HeatmapCell[]
}

export interface GateReason {
  type: 'CAPA_CRITICAL_OPEN'
  ref: string
  status: string
  workflow_state: string
  message: string
}

export interface ComplianceGateResult {
  blocked: boolean
  asset?: string
  reasons: GateReason[]
  active_findings_count: number
  active_capas_count: number
  blocking_findings: string[]
}

interface ListResp<T> {
  items?: T[]
  data?: T[]
  pagination: { page: number; page_size: number; total: number; total_pages: number }
}

// ─── Rule ─────────────────────────────────────────────────────────────────────

export const listRules = (filters = {}, page = 1, pageSize = 20) =>
  frappeGet<ListResp<ComplianceRule>>(`${BASE}.list_rules`, {
    filters: JSON.stringify(filters), page, page_size: pageSize,
  })

export const getRule = (name: string) =>
  frappeGet<ComplianceRule>(`${BASE}.get_rule`, { name })

export const createRule = (rule_data: Partial<ComplianceRule>) =>
  frappePost<{ name: string; rule_code: string }>(`${BASE}.create_rule`, {
    rule_data: JSON.stringify(rule_data),
  })

export const updateRule = (name: string, rule_data: Partial<ComplianceRule>, change_summary = '') =>
  frappePost<{ name: string; version: string; previous_version: string }>(
    `${BASE}.update_rule`,
    { name, rule_data: JSON.stringify(rule_data), change_summary },
  )

export const deactivateRule = (name: string) =>
  frappePost<{ name: string; is_active: 0 }>(`${BASE}.deactivate_rule`, { name })

export const reactivateRule = (name: string) =>
  frappePost<{ name: string; is_active: 1 }>(`${BASE}.reactivate_rule`, { name })

// ─── Record history (audit trail) ─────────────────────────────────────────────

export interface RecordHistoryEntry {
  name: string
  event_type: string
  timestamp: string
  actor: string
  actor_name?: string
  from_status?: string | null
  to_status?: string | null
  change_summary?: string
}

export const getRecordHistory = (ref_doctype: string, ref_name: string, limit = 50) =>
  frappeGet<{ items: RecordHistoryEntry[]; total: number }>(
    `${BASE}.get_record_history`,
    { ref_doctype, ref_name, limit },
  )

// ─── Compliance evaluation engine trigger (BUG-16-03/09) ─────────────────────

export const runComplianceEvaluation = () =>
  frappePost<{ message: string }>(`${BASE}.run_compliance_evaluation`, {})

export const generateScorecard = (module_ref = '', period = '') =>
  frappePost<{ name?: string; score_pct?: number } & Record<string, unknown>>(
    `${BASE}.generate_scorecard`,
    { module_ref, period },
  )

// ─── Finding ──────────────────────────────────────────────────────────────────

export const listFindings = (filters = {}, page = 1, pageSize = 20) =>
  frappeGet<ListResp<ComplianceFinding>>(`${BASE}.list_findings`, {
    filters: JSON.stringify(filters), page, page_size: pageSize,
  })

export const getFinding = (name: string) =>
  frappeGet<ComplianceFinding>(`${BASE}.get_finding`, { name })

export const confirmFinding = (name: string, reviewer_note = '') =>
  frappePost<{ name: string; status: FindingStatus }>(
    `${BASE}.confirm_finding`, { name, reviewer_note },
  )

export const markFalsePositive = (name: string, reason: string) =>
  frappePost<{ name: string; status: FindingStatus }>(
    `${BASE}.mark_false_positive`, { name, reason },
  )

export const waiveFinding = (
  name: string,
  waiver_reason: string,
  waiver_evidence: string,
  waiver_expiry: string,
) =>
  frappePost<{ name: string; status: FindingStatus }>(
    `${BASE}.waive_finding`,
    { name, waiver_reason, waiver_evidence, waiver_expiry },
  )

export const linkToCapa = (name: string, capa_ref: string) =>
  frappePost<{ name: string; capa_ref: string }>(`${BASE}.link_to_capa`, { name, capa_ref })

// ─── Audit ────────────────────────────────────────────────────────────────────

export const listAudits = (filters = {}, page = 1, pageSize = 20) =>
  frappeGet<ListResp<InternalAudit>>(`${BASE}.list_audits`, {
    filters: JSON.stringify(filters), page, page_size: pageSize,
  })

export const getAudit = (name: string) =>
  frappeGet<InternalAudit>(`${BASE}.get_audit`, { name })

export const createAudit = (audit_data: Partial<InternalAudit>) =>
  frappePost<{ name: string; status: string }>(`${BASE}.create_audit`, {
    audit_data: JSON.stringify(audit_data),
  })

export const startAudit = (name: string) =>
  frappePost<{ name: string; status: string; actual_start: string }>(
    `${BASE}.start_audit`, { name },
  )

export interface ChecklistItemPayload {
  idx: number
  finding_status: 'Compliant' | 'Minor NC' | 'Major NC' | 'N/A'
  notes?: string
  clause_ref?: string
}

export const completeAuditChecklist = (audit_name: string, items: ChecklistItemPayload[]) =>
  frappePost<{ audit_name: string; items_count: number; findings_created: number }>(
    `${BASE}.complete_audit_checklist`,
    { audit_name, items: JSON.stringify(items) },
  )

export const closeAudit = (name: string, audit_report = '') =>
  frappePost<{ name: string; status: string; actual_end: string }>(
    `${BASE}.close_audit`, { name, audit_report },
  )

// ─── CAPA ─────────────────────────────────────────────────────────────────────

export const createCapaFromFinding = (
  finding_name: string,
  payload: { imm_risk_level?: string; imm_root_cause_method?: string; responsible?: string; due_date?: string } = {},
) =>
  frappePost<{ capa_name: string; finding_name: string; workflow_state: string }>(
    `${BASE}.create_capa_from_finding`,
    { finding_name, ...payload },
  )

export interface CapaDetail extends CapaRecord {
  asset_name?: string
  responsible?: string
  responsible_name?: string
  description?: string
  root_cause?: string
  corrective_action?: string
  preventive_action?: string
  verification_notes?: string
  finding_ref?: string
  finding_rule?: string
  incident_ref?: string
  incident_subject?: string
  linked_incident?: string | null
  opened_date?: string
  creation?: string
}

export const getCapaDetail = (name: string) =>
  frappeGet<CapaDetail>(`${BASE}.get_capa`, { name })

export const updateCapaFields = (name: string, data: Record<string, unknown>) =>
  frappePost<{ name: string; updated_fields: string[]; workflow_state: string }>(
    `${BASE}.update_capa_fields`,
    { name, data: JSON.stringify(data) },
  )

export const advanceCapaState = (
  name: string,
  target_state: CapaWorkflowState,
  payload: Record<string, unknown> = {},
) =>
  frappePost<{ name: string; workflow_state: CapaWorkflowState; status: string }>(
    `${BASE}.advance_capa_state`,
    { name, target_state, payload: JSON.stringify(payload) },
  )

export const performEffectivenessCheck = (
  name: string,
  result: 'Effective' | 'Partially Effective' | 'Not Effective',
  effectiveness_evidence = '',
) =>
  frappePost<{ name: string; new_state: string; imm_reopen_count: number }>(
    `${BASE}.perform_effectiveness_check`,
    { name, result, effectiveness_evidence },
  )

export const reopenCapa = (name: string, reason = '') =>
  frappePost<{ name: string; workflow_state: 'Re-opened' }>(
    `${BASE}.reopen_capa`, { name, reason },
  )

// ─── Scorecard ────────────────────────────────────────────────────────────────

export const listScorecards = (filters = {}, page = 1, pageSize = 20) =>
  frappeGet<ListResp<ComplianceScorecard>>(`${BASE}.list_scorecards`, {
    filters: JSON.stringify(filters), page, page_size: pageSize,
  })

export const getCurrentScorecard = (scope = 'Hospital') =>
  frappeGet<ComplianceScorecard>(`${BASE}.get_current_scorecard`, { scope })

export const getScorecardByPeriod = (year: number, month: number, scope = 'Hospital') =>
  frappeGet<ComplianceScorecard | { exists: false; period_year: number; period_month: number }>(
    `${BASE}.get_scorecard_by_period`,
    { year, month, scope },
  )

export const publishScorecard = (name: string) =>
  frappePost<{ name: string; is_published: 1; published_at: string; approved_by_for_review: string }>(
    `${BASE}.publish_scorecard`, { name },
  )

// ─── Management Review ────────────────────────────────────────────────────────

export const listManagementReviews = (filters = {}, page = 1, pageSize = 20) =>
  frappeGet<ListResp<ManagementReview>>(`${BASE}.list_management_reviews`, {
    filters: JSON.stringify(filters), page, page_size: pageSize,
  })

export const getManagementReview = (name: string) =>
  frappeGet<ManagementReview>(`${BASE}.get_management_review`, { name })

export const createManagementReview = (data: Partial<ManagementReview>) =>
  frappePost<{ name: string; quarter: string; status: string }>(
    `${BASE}.create_management_review`, { data: JSON.stringify(data) },
  )

export const updateManagementReview = (
  name: string,
  data: Partial<ManagementReview> & {
    attendees?: MRAttendee[]
    output_actions?: MROutputActionRow[]
  },
) =>
  frappePost<{ name: string; status: MRStatus; quarter: string }>(
    `${BASE}.update_management_review`,
    { name, data: JSON.stringify(data) },
  )

export const advanceMrState = (name: string, target_state: MRStatus) =>
  frappePost<{ name: string; status: MRStatus; quarter: string }>(
    `${BASE}.advance_mr_state`,
    { name, target_state },
  )

export interface MROutputAction {
  action: string
  owner: string
  due_date?: string
}

export const finalizeManagementReview = (
  name: string,
  minutes_doc: string,
  output_actions: MROutputAction[] = [],
) =>
  frappePost<{ name: string; status: 'Closed'; quarter: string }>(
    `${BASE}.finalize_management_review`,
    { name, minutes_doc, output_actions: JSON.stringify(output_actions) },
  )

// ─── Dashboard / Reports ──────────────────────────────────────────────────────

export const getDashboardStats = () =>
  frappeGet<DashboardStats>(`${BASE}.get_dashboard_stats`)

export const getComplianceHeatmap = (period_year?: number, period_month?: number) =>
  frappeGet<ComplianceHeatmap>(`${BASE}.get_compliance_heatmap`, {
    period_year, period_month,
  })

export const getCapaAging = () =>
  frappeGet<{ buckets: Record<string, number>; total_open: number }>(
    `${BASE}.get_capa_aging`,
  )

export const getOverdueActions = () =>
  frappeGet<{ overdue_findings: ComplianceFinding[]; overdue_capas: CapaRecord[]; total: number }>(
    `${BASE}.get_overdue_actions`,
  )

// ─── Cross-module gate ────────────────────────────────────────────────────────

export const checkAssetComplianceStatus = (asset: string) =>
  frappeGet<ComplianceGateResult>(`${BASE}.check_asset_compliance_status`, { asset })
