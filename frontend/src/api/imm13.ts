// Copyright (c) 2026, AssetCore Team
// API client cho Module IMM-13 — Suspension & Transfer Gateway

import { frappeGet, frappePost } from './helpers'

export interface SuspensionChecklistItem {
  idx: number
  task_name: string
  task_category: string
  completed: boolean
  completion_date: string | null
  notes: string
}

export interface TransferDetail {
  transfer_to_location: string
  transfer_to_department: string
  receiving_officer: string
  transfer_start_date: string | null
  economic_justification: string
}

export interface DecommissionRequest {
  name: string
  asset: string
  asset_name: string
  suspension_reason: string
  reason_details: string
  outcome: 'Suspend' | 'Transfer' | 'Retire' | ''
  workflow_state: string
  condition_at_suspension: string
  current_book_value: number
  biological_hazard: boolean
  bio_hazard_clearance: string
  data_destruction_required: boolean
  data_destruction_confirmed: boolean
  regulatory_clearance_required: boolean
  regulatory_clearance_doc: string
  technical_reviewer: string
  tech_review_notes: string
  tech_review_date: string | null
  residual_risk_level: string
  residual_risk_notes: string
  estimated_remaining_life: number | null
  replacement_needed: boolean
  transfer_to_location: string
  transfer_to_department: string
  receiving_officer: string
  transfer_start_date: string | null
  economic_justification: string
  approved: boolean
  approved_by: string
  approval_date: string | null
  approval_notes: string
  rejection_reason: string
  docstatus: number
  creation: string
  modified: string
  suspension_checklist: SuspensionChecklistItem[]
}

export interface DecommissionListResponse {
  rows: Array<Pick<DecommissionRequest,
    'name' | 'asset' | 'asset_name' | 'suspension_reason' | 'outcome' |
    'workflow_state' | 'current_book_value' | 'creation' | 'modified'
  >>
  total: number
  page: number
  page_size: number
}

export interface DecommissionMetrics {
  suspended_ytd: number
  transferred_ytd: number
  retirement_candidates_count: number
  pending_approval_count: number
  open_by_state: Record<string, number>
}

export interface RetirementCandidate {
  name: string
  asset_name: string
  status: string
  retirement_flag_reason: string
  retirement_flagged_date: string | null
  device_model: string
}

export interface SuspensionEligibility {
  eligible: boolean
  reasons: string[]
  open_work_orders: string[]
  asset_status: string
  asset_name: string
}

const BASE = '/api/method/assetcore.api.imm13'

export async function getDecommissionRequest(name: string): Promise<DecommissionRequest> {
  return frappeGet<DecommissionRequest>(`${BASE}.get_decommission_request`, { name })
}

export async function listDecommissionRequests(
  workflowState = '',
  asset = '',
  page = 1,
  pageSize = 20,
): Promise<DecommissionListResponse> {
  return frappeGet<DecommissionListResponse>(`${BASE}.list_decommission_requests`, {
    workflow_state: workflowState,
    asset,
    page,
    page_size: pageSize,
  })
}

export async function getAssetSuspensionEligibility(assetName: string): Promise<SuspensionEligibility> {
  return frappeGet<SuspensionEligibility>(`${BASE}.get_asset_suspension_eligibility`, {
    asset_name: assetName,
  })
}

export async function getRetirementCandidates(): Promise<RetirementCandidate[]> {
  const res = await frappeGet<RetirementCandidate[]>(`${BASE}.get_retirement_candidates`, {})
  return res ?? []
}

export async function getDashboardMetrics(): Promise<DecommissionMetrics> {
  return frappeGet<DecommissionMetrics>(`${BASE}.get_dashboard_metrics`, {})
}

export async function createDecommissionRequest(payload: {
  asset: string
  suspension_reason: string
  reason_details?: string
  condition_at_suspension?: string
  current_book_value?: number
  biological_hazard?: number
  data_destruction_required?: number
  regulatory_clearance_required?: number
}): Promise<{ name: string; asset: string; workflow_state: string; creation: string }> {
  return frappePost(`${BASE}.create_decommission_request`, payload)
}

export async function submitTechReview(payload: {
  name: string
  technical_reviewer?: string
  tech_review_notes?: string
  residual_risk_level?: string
  residual_risk_notes?: string
  estimated_remaining_life?: number
}): Promise<{ name: string; workflow_state: string }> {
  return frappePost(`${BASE}.submit_tech_review`, payload)
}

export async function completeTechReview(payload: {
  name: string
  technical_reviewer?: string
  tech_review_notes?: string
  residual_risk_level?: string
  residual_risk_notes?: string
}): Promise<{ name: string; workflow_state: string }> {
  return frappePost(`${BASE}.complete_tech_review`, payload)
}

export async function setReplacementDecision(payload: {
  name: string
  outcome: string
  replacement_needed?: number
  transfer_to_location?: string
  receiving_officer?: string
  transfer_to_department?: string
  economic_justification?: string
}): Promise<{ name: string; workflow_state: string; outcome: string }> {
  return frappePost(`${BASE}.set_replacement_decision`, payload)
}

export async function approveSuspension(payload: {
  name: string
  approved_by?: string
  approval_notes?: string
}): Promise<{ name: string; approved: boolean; approved_by: string }> {
  return frappePost(`${BASE}.approve_suspension`, payload)
}

export async function rejectSuspension(payload: {
  name: string
  rejection_reason?: string
}): Promise<{ name: string; workflow_state: string }> {
  return frappePost(`${BASE}.reject_suspension`, payload)
}

export async function startTransfer(name: string): Promise<{ name: string; workflow_state: string }> {
  return frappePost(`${BASE}.start_transfer`, { name })
}

export async function completeTransfer(name: string): Promise<{ name: string; workflow_state: string; asset: string }> {
  return frappePost(`${BASE}.complete_transfer`, { name })
}

export async function completeChecklistItem(
  name: string,
  checklistItemIdx: number,
  notes = '',
): Promise<{ name: string; checklist_item_idx: number; completed: boolean }> {
  return frappePost(`${BASE}.complete_checklist_item`, {
    name,
    checklist_item_idx: checklistItemIdx,
    notes,
  })
}
