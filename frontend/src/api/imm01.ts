// Copyright (c) 2026, AssetCore Team
// API calls cho Module IMM-01 — Needs Assessment

import { frappeGet, frappePost } from './helpers'

const BASE = '/api/method/assetcore.api.imm01'

export interface NeedsAssessmentItem {
  name: string
  requesting_dept: string
  equipment_type: string
  priority: string
  estimated_budget: number
  approved_budget: number | null
  status: string
  request_date: string
}

export interface NeedsAssessmentDoc extends NeedsAssessmentItem {
  requested_by: string
  quantity: number
  clinical_justification: string
  linked_device_model: string | null
  current_equipment_age: number | null
  failure_frequency: string | null
  htmreview_notes: string | null
  finance_notes: string | null
  reject_reason: string | null
  technical_specification: string | null
  approver: string | null
}

export interface NeedsAssessmentListResult {
  items: NeedsAssessmentItem[]
  total: number
  page: number
}

export async function createNeedsAssessment(params: {
  requesting_dept: string
  equipment_type: string
  quantity: number
  estimated_budget: number
  clinical_justification: string
  priority?: string
  linked_device_model?: string
  current_equipment_age?: number
  failure_frequency?: string
  technical_specification?: string
}): Promise<{ name: string; status: string }> {
  return frappePost(`${BASE}.create_needs_assessment`, params as Record<string, unknown>)
}

export async function getNeedsAssessment(name: string): Promise<NeedsAssessmentDoc> {
  return frappeGet<NeedsAssessmentDoc>(`${BASE}.get_needs_assessment`, { name })
}

export async function listNeedsAssessments(params: {
  status?: string
  dept?: string
  year?: string
  page?: number
  page_size?: number
}): Promise<NeedsAssessmentListResult> {
  return frappeGet<NeedsAssessmentListResult>(`${BASE}.list_needs_assessments`, params as Record<string, unknown>)
}

export async function submitForReview(name: string, approver: string): Promise<{ name: string; status: string }> {
  return frappePost(`${BASE}.submit_for_review`, { name, approver })
}

export async function beginTechnicalReview(name: string): Promise<{ name: string; status: string }> {
  return frappePost(`${BASE}.begin_technical_review`, { name })
}

export async function approveNeedsAssessment(
  name: string,
  approved_budget: number,
  notes?: string,
): Promise<{ name: string; status: string; approved_budget: number }> {
  return frappePost(`${BASE}.approve_needs_assessment`, { name, approved_budget, notes: notes || '' })
}

export async function rejectNeedsAssessment(
  name: string,
  reason: string,
): Promise<{ name: string; status: string }> {
  return frappePost(`${BASE}.reject_needs_assessment`, { name, reason })
}

export async function saveHtmReviewNotes(
  name: string,
  notes: string,
): Promise<{ name: string; htmreview_notes: string }> {
  return frappePost(`${BASE}.save_htmreview_notes`, { name, notes })
}

export async function linkTechnicalSpec(
  na_name: string,
  ts_name: string,
): Promise<{ na: string; ts: string }> {
  return frappePost(`${BASE}.link_technical_spec`, { na_name, ts_name })
}

export async function getDashboardStats(year?: string, dept?: string): Promise<{
  total: number
  by_status: Record<string, number>
  total_requested_budget: number
  total_approved_budget: number
  approval_rate: number
}> {
  return frappeGet(`${BASE}.get_dashboard_stats`, { year: year || '', dept: dept || '' })
}
