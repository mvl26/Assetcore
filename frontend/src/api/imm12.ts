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
