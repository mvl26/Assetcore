// Copyright (c) 2026, AssetCore Team
// API calls cho Module IMM-02 — Procurement Plan

import { frappeGet, frappePost } from './helpers'

const BASE = '/api/method/assetcore.api.imm02'

// ─── Types ────────────────────────────────────────────────────────────────────

export interface ProcurementPlanItem {
  name: string
  needs_assessment: string | null
  device_model: string | null
  equipment_description: string
  quantity: number
  estimated_unit_cost: number
  total_cost: number
  priority: string
  planned_quarter: string | null
  vendor_shortlist: string | null
  status: string
  por_reference: string | null
}

export interface ProcurementPlanDoc {
  name: string
  plan_year: number
  approved_budget: number
  allocated_budget: number
  remaining_budget: number
  status: string
  approved_by: string | null
  approval_date: string | null
  approval_notes: string | null
  items: ProcurementPlanItem[]
}

export interface ProcurementPlanListItem {
  name: string
  plan_year: number
  approved_budget: number
  allocated_budget: number
  remaining_budget: number
  status: string
}

export interface ProcurementPlanListResult {
  items: ProcurementPlanListItem[]
  total: number
  page: number
}

export interface ApprovedNA {
  name: string
  requesting_dept: string
  equipment_type: string
  quantity: number
  estimated_budget: number
  approved_budget: number
  priority: string
}

// ─── Endpoints ────────────────────────────────────────────────────────────────

export async function createProcurementPlan(
  plan_year: number,
  approved_budget: number,
): Promise<{ name: string; status: string }> {
  return frappePost(`${BASE}.create_procurement_plan`, { plan_year, approved_budget })
}

export async function getProcurementPlan(name: string): Promise<ProcurementPlanDoc> {
  return frappeGet<ProcurementPlanDoc>(`${BASE}.get_procurement_plan`, { name })
}

export async function listProcurementPlans(params: {
  status?: string
  year?: string
  page?: number
  page_size?: number
}): Promise<ProcurementPlanListResult> {
  return frappeGet<ProcurementPlanListResult>(
    `${BASE}.list_procurement_plans`,
    params as Record<string, unknown>,
  )
}

export async function addNaToPlan(params: {
  plan_name: string
  needs_assessment: string
  planned_quarter?: string
  estimated_unit_cost?: number
}): Promise<ProcurementPlanDoc> {
  return frappePost(`${BASE}.add_na_to_plan`, params as Record<string, unknown>)
}

export async function submitPlanForReview(
  name: string,
  approver: string,
): Promise<{ name: string; status: string }> {
  return frappePost(`${BASE}.submit_plan_for_review`, { name, approver })
}

export async function approvePlan(
  name: string,
  notes?: string,
): Promise<{ name: string; status: string }> {
  return frappePost(`${BASE}.approve_plan`, { name, notes: notes || '' })
}

export async function lockBudget(name: string): Promise<{ name: string; status: string }> {
  return frappePost(`${BASE}.lock_budget`, { name })
}

export async function getApprovedNasForPlan(year: number): Promise<ApprovedNA[]> {
  return frappeGet(`${BASE}.get_approved_nas_for_plan`, { year })
}
