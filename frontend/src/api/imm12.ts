// Copyright (c) 2026, AssetCore Team
// IMM-12 — Incident workflow API client

import { frappeGet, frappePost } from './helpers'

const BASE = '/api/method/assetcore.api.imm12'

export interface IncidentDetail {
  name: string
  asset: string
  asset_name?: string
  incident_type: string
  severity: 'Low' | 'Medium' | 'High' | 'Critical'
  status: 'Open' | 'Under Investigation' | 'Resolved' | 'Closed'
  description: string
  immediate_action?: string
  resolution_notes?: string
  root_cause_summary?: string
  reported_by?: string
  reported_at?: string
  patient_affected?: number
  patient_impact_description?: string
  reported_to_byt?: number
  byt_report_date?: string
  linked_repair_wo?: string
  linked_capa?: string
  closed_date?: string
  docstatus?: number
  allowed_transitions?: string[]
  fault_code?: string
  workaround_applied?: number
  rca_required?: number
  rca_record?: string
  chronic_failure_flag?: number
  clinical_impact?: string
  rca?: { name: string; status: string; root_cause?: string }
}

export interface RCADetail {
  name: string
  incident_report: string
  asset?: string
  status: 'RCA Required' | 'RCA In Progress' | 'Completed'
  rca_method?: string
  assigned_to?: string
  root_cause?: string
  corrective_action_summary?: string
  preventive_action_summary?: string
  contributing_factors?: string
  rca_notes?: string
  linked_capa?: string
  completed_date?: string
  incident_severity?: string
  five_why_steps?: Array<{ why_number: number; why_question: string; why_answer: string }>
}

export interface ChronicFailure {
  asset: string
  asset_name?: string
  fault_code: string
  incident_count: number
  first_reported?: string
  last_reported?: string
}

export interface IncidentStats {
  open: number
  investigating: number
  resolved: number
  closed: number
  critical_open: number
  high_open: number
}

export function listIncidents(params: {
  status?: string
  severity?: string
  asset?: string
  page?: number
  page_size?: number
} = {}) {
  return frappeGet<{ pagination: { total: number; page: number; page_size: number; total_pages: number }; items: IncidentDetail[] }>(
    `${BASE}.list_incidents`, params as Record<string, unknown>,
  )
}

export function getIncident(name: string) {
  return frappeGet<IncidentDetail>(`${BASE}.get_incident`, { name })
}

export function acknowledgeIncident(name: string, notes = '', assigned_to = '') {
  return frappePost<{ name: string; status: string }>(
    `${BASE}.acknowledge_incident`, { name, notes, assigned_to },
  )
}

export function resolveIncident(name: string, resolution_notes: string, root_cause = '') {
  return frappePost<{ name: string; status: string; linked_capa?: string }>(
    `${BASE}.resolve_incident`, { name, resolution_notes, root_cause },
  )
}

export function closeIncident(name: string, verification_notes = '') {
  return frappePost<{ name: string; status: string; closed_date?: string }>(
    `${BASE}.close_incident`, { name, verification_notes },
  )
}

export function getIncidentStats() {
  return frappeGet<IncidentStats>(`${BASE}.get_incident_stats`)
}

export interface ReportIncidentPayload {
  asset: string
  incident_type: string
  severity: string
  description: string
  fault_code?: string
  workaround_applied?: number
  clinical_impact?: string
  patient_affected?: number
  patient_impact_description?: string
  immediate_action?: string
  linked_repair_wo?: string
}

export function reportIncident(data: ReportIncidentPayload) {
  return frappePost<{ name: string; status: string; severity: string }>(
    `${BASE}.report_incident`, data as unknown as Record<string, unknown>,
  )
}

export function cancelIncident(name: string, reason: string) {
  return frappePost<{ name: string; status: string }>(
    `${BASE}.cancel_incident`, { name, reason },
  )
}

export function createRca(incident_name: string, rca_method = '5-Why') {
  return frappePost<{ name: string; status: string }>(
    `${BASE}.create_rca`, { incident_name, rca_method },
  )
}

export function getRca(name: string) {
  return frappeGet<RCADetail>(`${BASE}.get_rca`, { name })
}

export interface SubmitRcaPayload {
  name: string
  root_cause: string
  corrective_action: string
  preventive_action?: string
  five_why_steps?: Array<{ why_number: number; why_question: string; why_answer: string }>
  rca_notes?: string
}

export function submitRca(data: SubmitRcaPayload) {
  const { five_why_steps, ...rest } = data
  return frappePost<{ name: string; status: string; linked_capa?: string }>(
    `${BASE}.submit_rca`,
    { ...rest, five_why_steps: JSON.stringify(five_why_steps ?? []) } as unknown as Record<string, unknown>,
  )
}

export function getAssetIncidentHistory(asset: string, limit = 10) {
  return frappeGet<{ asset: string; items: IncidentDetail[] }>(
    `${BASE}.get_asset_incident_history`, { asset, limit },
  )
}

export function getChronicFailures() {
  return frappeGet<{ items: ChronicFailure[] }>(`${BASE}.get_chronic_failures`)
}

export function getDashboard() {
  return frappeGet<{
    total: number; open: number; investigating: number; resolved: number; closed: number
    critical: number; high: number; rca_pending: number; chronic: number
    recent: IncidentDetail[]; chronic_list: ChronicFailure[]
  }>(`${BASE}.get_dashboard`)
}
