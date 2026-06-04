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
  // Khớp _STATUS_* trong services/imm12.py (ground truth).
  status: 'Open' | 'Acknowledged' | 'In Progress' | 'RCA Required' | 'Resolved' | 'Closed' | 'Cancelled'
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
  // BR-12-09: cờ vi phạm SLA THÔ (stamped-by-scheduler, bền DB). GIỮ cho write-path
  // + escalation idempotent (BR-12-08/09). KHÔNG dùng trực tiếp để render badge —
  // undercount trong cửa-sổ-trễ-scheduler (quá hạn nhưng cờ chưa stamp = 0).
  response_breached?: number
  resolution_breached?: number
  // BR-12-13: cờ vi phạm SLA DERIVED LIVE từ BE (_row_is_breached) = (cờ-thô=1) OR
  // (đang-mở ∧ quá-hạn). FE badge ĐỌC field này thay cờ thô → hiện cho incident
  // currently-overdue-open kể cả khi cờ DB còn 0. Badge live == tile (cùng SoT
  // sla_breach_filter ở get_incident_stats). optional: forward-compat khi BE chưa ship.
  is_response_breached?: number
  is_resolution_breached?: number
  rca?: { name: string; status: string; root_cause?: string }
}

export interface RCADetail {
  name: string
  incident_report: string
  asset?: string
  status: 'RCA Required' | 'RCA In Progress' | 'Completed' | 'Cancelled'
  rca_method?: string
  trigger_type?: string
  assigned_to?: string
  due_date?: string
  incident_count?: number
  root_cause?: string
  corrective_action_summary?: string
  preventive_action_summary?: string
  contributing_factors?: string
  rca_notes?: string
  linked_capa?: string
  completed_by?: string
  completed_date?: string
  incident_severity?: string
  five_why_steps?: Array<{ why_number: number; why_question: string; why_answer: string }>
}

export interface ChronicFailure {
  asset: string
  asset_name?: string
  fault_code: string
  count: number
  incident_count?: number
  last_reported?: string
}

// Khớp services/imm12.py::get_incident_stats (ground truth).
export interface IncidentStats {
  total: number
  open: number
  // BR-12-11 (round-21): tổng incident ở MỌI state mở của SoT open_incident_filter()
  // {Open, Acknowledged, In Progress, RCA Required} — KHÁC `open` (chỉ status=='Open').
  // optional: forward-compat khi BE chưa ship; card "Đang mở" fallback 0.
  open_total?: number
  investigating: number
  resolved: number
  closed: number
  cancelled: number
  critical: number
  high: number
  // Open-set severity (KPI strip worklist): == _count(open_incident_filter() ∧
  // {severity}) — loại Closed/Cancelled/Resolved. optional: forward-compat khi BE
  // chưa ship → strip fallback `?? 0`. KHÁC critical/high global (mọi status).
  critical_open?: number
  high_open?: number
  rca_pending: number
  // BR-12-12: SỐ NHÓM (asset,fault_code) đang lặp lại LIVE trong cửa sổ 90 ngày
  // (== len(get_chronic_failures()) qua chronic_failure_count() ở BE), KHÔNG đếm cờ
  // stale chronic_failure_flag. Shape giữ `number` — chỉ NGỮ NGHĨA đổi (live thay stale).
  // Invariant get_dashboard(): stats.chronic == len(chronic_failures) (cùng SoT).
  chronic: number
  // BR-12-09: số incident có cờ vi phạm SLA (cùng predicate cờ với badge ở list).
  sla_response_breached: number
  sla_resolution_breached: number
}

export interface RcaListItem {
  name: string
  incident_report?: string
  asset?: string
  asset_name?: string
  rca_method?: string
  trigger_type?: string
  status: string
  assigned_to?: string
  assigned_to_name?: string
  due_date?: string
  linked_capa?: string
  completed_date?: string
}

export function listIncidents(params: {
  status?: string
  severity?: string
  asset?: string
  // open=1 áp SoT open_incident_filter() (incident đang mở) cho drill-down từ
  // dashboard donut/card → count == số dòng list. status đơn lẻ ưu tiên hơn open.
  open?: 0 | 1
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

// D3: Acknowledged → In Progress ("Bắt đầu xử lý")
export function startWork(name: string, notes = '') {
  return frappePost<{ name: string; status: string }>(
    `${BASE}.start_work`, { name, notes },
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

export function listRcas(params: {
  method?: string
  status?: string
  asset?: string
  page?: number
  page_size?: number
} = {}) {
  return frappeGet<{ pagination: { total: number; page: number; page_size: number; total_pages: number }; items: RcaListItem[] }>(
    `${BASE}.list_rcas`, params as Record<string, unknown>,
  )
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

export interface DashboardStats {
  total: number
  open: number
  // BR-12-11 (round-21): xem IncidentStats.open_total. get_dashboard().stats ==
  // get_incident_stats() nên cùng shape.
  open_total?: number
  investigating: number
  resolved: number
  closed: number
  cancelled: number
  critical: number
  high: number
  // Open-set severity — xem IncidentStats.critical_open. get_dashboard().stats ==
  // get_incident_stats() nên cùng shape (strip có thể đọc từ dashboard payload).
  critical_open?: number
  high_open?: number
  rca_pending: number
  // BR-12-12: xem IncidentStats.chronic — số nhóm chronic LIVE 90d (chronic_failure_count).
  // get_dashboard().stats == get_incident_stats() ⇒ stats.chronic == len(chronic_failures).
  chronic: number
  // BR-12-09: số incident vi phạm SLA (get_dashboard.stats = get_incident_stats).
  sla_response_breached: number
  sla_resolution_breached: number
}

export interface DashboardData {
  stats: DashboardStats
  active_incidents: IncidentDetail[]
  open_rcas: RCADetail[]
  chronic_failures: ChronicFailure[]
}

export function getDashboard() {
  return frappeGet<DashboardData>(`${BASE}.get_dashboard`)
}
