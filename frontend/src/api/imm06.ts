// Copyright (c) 2026, AssetCore Team
// API client cho Module IMM-06 — Training & Competency Management

import { frappeGet, frappePost } from './helpers'

export interface TrainingProgram {
  name: string
  program_name: string
  program_code?: string
  training_type: 'Initial' | 'Refresher' | 'Advanced' | 'Certification'
  target_device_model: string | null
  target_device_category: string | null
  duration_hours: number
  validity_period_months: number
  passing_score_pct: number
  assessment_method: 'Theory' | 'Practical' | 'Both'
  is_mandatory_for_operation: 0 | 1
  is_active: 0 | 1
  content_outline: string
  instructor_qualification_required: string
  qms_doc_ref: string | null
  modified: string
  /** Enriched by BE get_program */
  target_device_model_name?: string
}

export interface TrainingParticipant {
  /** Child row name (Frappe) — dùng cho removeParticipant, không hiển thị */
  name?: string
  user: string
  user_full_name?: string
  department_name?: string
  department: string | null
  role_at_session: string
  attendance_pct: number | null
  theory_score: number | null
  practical_score: number | null
  overall_result: 'Pass' | 'Fail' | 'Conditional' | null
  certificate_issued: 0 | 1
  retake_required: 0 | 1
  competency_record: string | null
  remarks: string
}

export interface TrainingSession {
  name: string
  training_program: string
  session_date: string
  session_type: 'Onsite' | 'Online' | 'Hybrid'
  location: string
  instructor: string | null
  instructor_external_name: string
  instructor_external_org: string
  evaluation_method?: 'Lý thuyết' | 'Thực hành' | 'Cả hai'
  trainer_ref?: string | null
  trainer_ref_name?: string | null
  duration_planned_hours: number
  duration_actual_hours: number | null
  workflow_state: string
  participant_count?: number
  participants?: TrainingParticipant[]
  modified: string
  /** Enriched by BE list_sessions / get_session — không phải DocType field */
  program_name?: string
  training_program_name?: string
  instructor_full_name?: string
  trainer_name?: string
  attendee_count?: number
  allowed_transitions?: string[]
}

export interface UserCompetency {
  name: string
  user: string
  user_full_name?: string
  device_model: string
  training_program: string
  competency_level: 'Trainee' | 'Operator' | 'Senior Operator' | 'Trainer'
  achieved_date: string
  expiry_date: string | null
  days_until_expiry: number | null
  workflow_state: string
  recertification_due_date: string | null
  department_at_assessment: string | null
  last_assessment_score: number | null
  theory_score: number | null
  practical_score: number | null
  supervisor_signoff: string | null
  signoff_date: string | null
  is_expired: 0 | 1
}

export interface Imm06ListResponse<T> {
  data: T[]
  pagination: { page: number; page_size: number; total: number; total_pages: number }
}

const BASE = '/api/method/assetcore.api.imm06'

export async function listPrograms(
  filters = {},
  page = 1,
  pageSize = 20,
): Promise<Imm06ListResponse<TrainingProgram>> {
  return frappeGet<Imm06ListResponse<TrainingProgram>>(`${BASE}.list_programs`, {
    filters: JSON.stringify(filters),
    page,
    page_size: pageSize,
  })
}

export async function getProgram(name: string): Promise<TrainingProgram> {
  return frappeGet<TrainingProgram>(`${BASE}.get_program`, { name })
}

export async function createProgram(
  data: Partial<TrainingProgram>,
): Promise<{ name: string }> {
  return frappePost<{ name: string }>(`${BASE}.create_program`, { program_data: JSON.stringify(data) })
}

export async function updateProgram(
  name: string,
  data: Partial<TrainingProgram>,
): Promise<{ name: string; recert_triggered: boolean; affected_competencies_count: number }> {
  return frappePost<{ name: string; recert_triggered: boolean; affected_competencies_count: number }>(
    `${BASE}.update_program`,
    { name, program_data: JSON.stringify(data) },
  )
}

export async function listSessions(
  filters = {},
  page = 1,
  pageSize = 20,
): Promise<Imm06ListResponse<TrainingSession>> {
  return frappeGet<Imm06ListResponse<TrainingSession>>(`${BASE}.list_sessions`, {
    filters: JSON.stringify(filters),
    page,
    page_size: pageSize,
  })
}

export async function getSession(name: string): Promise<TrainingSession> {
  return frappeGet<TrainingSession>(`${BASE}.get_session`, { name })
}

export async function createSession(
  data: Record<string, unknown>,
): Promise<{ name: string; workflow_state: string }> {
  return frappePost<{ name: string; workflow_state: string }>(`${BASE}.create_session`, { session_data: JSON.stringify(data) })
}

export interface EnrollParticipantInput {
  user: string
  department?: string | null
}

export async function enrollParticipants(
  session: string,
  participants: EnrollParticipantInput[],
): Promise<{ name: string; participant_count: number }> {
  return frappePost<{ name: string; participant_count: number }>(
    `${BASE}.enroll_participants`,
    { name: session, participants: JSON.stringify(participants) },
  )
}

export async function removeParticipant(
  session: string,
  rowName: string,
): Promise<{ name: string; participant_count: number }> {
  return frappePost<{ name: string; participant_count: number }>(
    `${BASE}.remove_participant`,
    { name: session, row_name: rowName },
  )
}

export async function confirmSession(
  name: string,
): Promise<{ name: string; new_state: string }> {
  return frappePost<{ name: string; new_state: string }>(`${BASE}.confirm_session`, { name })
}

export async function startSession(
  name: string,
): Promise<{ name: string; workflow_state: string }> {
  return frappePost<{ name: string; workflow_state: string }>(`${BASE}.start_session`, { name })
}

export async function completeSession(
  name: string,
  participantsResults: TrainingParticipant[],
): Promise<{ name: string; participants_summary: Record<string, unknown>; competencies_created: string[] }> {
  return frappePost<{ name: string; participants_summary: Record<string, unknown>; competencies_created: string[] }>(
    `${BASE}.complete_session`,
    { name, participants_results: JSON.stringify(participantsResults) },
  )
}

export async function cancelSession(
  name: string,
  cancelReason: string,
): Promise<{ name: string; new_state: string }> {
  return frappePost<{ name: string; new_state: string }>(`${BASE}.cancel_session`, {
    name,
    cancel_reason: cancelReason,
  })
}

export async function verifySession(name: string): Promise<{ name: string; workflow_state: string }> {
  return frappePost<{ name: string; workflow_state: string }>(`${BASE}.verify_session`, { name })
}

export async function closeSession(name: string): Promise<{ name: string; workflow_state: string }> {
  return frappePost<{ name: string; workflow_state: string }>(`${BASE}.close_session`, { name })
}

export async function listCompetencies(
  filters = {},
  page = 1,
  pageSize = 20,
): Promise<Imm06ListResponse<UserCompetency>> {
  return frappeGet<Imm06ListResponse<UserCompetency>>(`${BASE}.list_competencies`, {
    filters: JSON.stringify(filters),
    page,
    page_size: pageSize,
  })
}

export async function getUserCompetencies(
  user?: string,
): Promise<{ user: string; competencies: UserCompetency[]; summary: Record<string, unknown> }> {
  return frappeGet<{ user: string; competencies: UserCompetency[]; summary: Record<string, unknown> }>(
    `${BASE}.get_user_competencies`,
    user ? { user } : {},
  )
}

export async function signoffCompetency(name: string): Promise<{ name: string }> {
  return frappePost<{ name: string }>(`${BASE}.signoff_competency`, { name })
}

export async function revokeCompetency(
  name: string,
  reason: string,
  capaRef?: string,
): Promise<{ name: string }> {
  return frappePost<{ name: string }>(`${BASE}.revoke_competency`, {
    name,
    reason,
    ...(capaRef ? { capa_ref: capaRef } : {}),
  })
}

export async function recertifyCompetency(
  name: string,
  newSession: string,
): Promise<{ name: string }> {
  return frappePost<{ name: string }>(`${BASE}.recertify_competency`, {
    name,
    new_session: newSession,
  })
}

export async function getDashboardStats(): Promise<Record<string, unknown>> {
  return frappeGet<Record<string, unknown>>(`${BASE}.get_dashboard_stats`)
}

export async function getCompetencyGapsByDept(): Promise<Record<string, unknown>> {
  return frappeGet<Record<string, unknown>>(`${BASE}.get_competency_gaps_by_dept`)
}

export async function getExpiringCompetencies(days = 60): Promise<UserCompetency[]> {
  const res = await frappeGet<UserCompetency[] | null>(`${BASE}.get_expiring_competencies`, { days })
  return res ?? []
}
