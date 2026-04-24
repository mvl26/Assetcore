// Copyright (c) 2026, AssetCore Team
// API layer cho IMM-06 — Bàn giao & Đào tạo

import { frappeGet, frappePost } from './helpers'

const BASE = '/api/method/assetcore.api.imm06'

// ─── Interfaces ───────────────────────────────────────────────────────────────

export interface TrainingTrainee {
  trainee_user: string
  full_name?: string
  role?: string
  attendance?: 'Present' | 'Absent'
  score?: number | null
  passed?: 0 | 1
}

export interface TrainingSessionSummary {
  name: string
  training_type: string
  training_date: string
  trainer: string
  trainer_type?: string
  status: 'Scheduled' | 'Completed' | 'Cancelled'
  competency_confirmed?: 0 | 1
  duration_hours?: number | null
  trainees_count?: number
  passed_count?: number
}

export interface LifecycleEvent {
  name: string
  event_type: string
  timestamp: string
  actor: string
  from_status: string
  to_status: string
  notes?: string
}

export interface HandoverRecord {
  name: string
  asset: string
  commissioning_ref: string
  clinical_dept: string
  handover_date: string
  received_by: string
  handover_type: 'Full' | 'Conditional' | 'Temporary'
  conditions_if_conditional?: string | null
  htm_engineer_signoff?: string | null
  dept_head_signoff?: string | null
  handover_notes?: string | null
  status: string
  workflow_state?: string
  training_sessions?: TrainingSessionSummary[]
  lifecycle_events?: LifecycleEvent[]
}

export interface HandoverListItem {
  name: string
  asset: string
  clinical_dept: string
  handover_date: string
  received_by: string
  handover_type: string
  status: string
  modified: string
}

export interface HandoverListResult {
  items: HandoverListItem[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface DashboardStats {
  total_pending_handover: number
  completed_this_month: number
  training_scheduled: number
  avg_days_to_handover: number
  training_pass_rate: number
}

export interface TrainingResult {
  name: string
  status: string
  competency_confirmed: boolean
  passed_count: number
  total_trainees: number
}

export interface AssetTrainingHistory {
  asset: string
  sessions: TrainingSessionSummary[]
  total_sessions: number
  total_trained: number
}

// ─── Read API ─────────────────────────────────────────────────────────────────

export async function getHandoverRecord(name: string): Promise<HandoverRecord> {
  return frappeGet<HandoverRecord>(`${BASE}.get_handover_record`, { name })
}

export async function listHandoverRecords(params: {
  status?: string
  dept?: string
  asset?: string
  page?: number
  page_size?: number
}): Promise<HandoverListResult> {
  return frappeGet<HandoverListResult>(`${BASE}.list_handover_records`, params as Record<string, unknown>)
}

export async function getDashboardStats(): Promise<DashboardStats> {
  return frappeGet<DashboardStats>(`${BASE}.get_dashboard_stats`, {})
}

export async function getAssetTrainingHistory(asset_name: string): Promise<AssetTrainingHistory> {
  return frappeGet<AssetTrainingHistory>(`${BASE}.get_asset_training_history`, { asset_name })
}

// ─── Write API ────────────────────────────────────────────────────────────────

export async function createHandoverRecord(params: {
  commissioning_ref: string
  clinical_dept: string
  handover_date: string
  received_by: string
  handover_type?: string
}): Promise<{ name: string; asset: string; status: string }> {
  return frappePost(`${BASE}.create_handover_record`, params as Record<string, unknown>)
}

export async function scheduleTraining(params: {
  handover_name: string
  training_type: string
  trainer: string
  training_date: string
  duration_hours?: number
  trainees?: Array<{ trainee_user: string; role?: string }>
}): Promise<{ name: string; handover_ref: string; status: string }> {
  return frappePost(`${BASE}.schedule_training`, {
    ...params,
    trainees: JSON.stringify(params.trainees ?? []),
  } as Record<string, unknown>)
}

export async function completeTraining(params: {
  training_session_name: string
  scores?: Array<{ trainee_user: string; score: number; passed: boolean }>
  notes?: string
}): Promise<TrainingResult> {
  return frappePost(`${BASE}.complete_training`, {
    ...params,
    scores: JSON.stringify(params.scores ?? []),
  } as Record<string, unknown>)
}

export async function confirmHandover(params: {
  name: string
  dept_head_signoff: string
  notes?: string
}): Promise<{ name: string; status: string; docstatus: number; lifecycle_event?: string }> {
  return frappePost(`${BASE}.confirm_handover`, params as Record<string, unknown>)
}
