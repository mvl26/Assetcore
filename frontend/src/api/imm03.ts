// Copyright (c) 2026, AssetCore Team
// API calls cho Module IMM-03 — Technical Specification (+ VE, POR)

import { frappeGet, frappePost } from './helpers'

const BASE = '/api/method/assetcore.api.imm03'

// ─── Technical Specification ──────────────────────────────────────────────────

export interface TechnicalSpecDoc {
  name: string
  needs_assessment: string | null
  device_model: string | null
  status: string
  equipment_description: string
  regulatory_class: string
  mdd_class: string | null
  performance_requirements: string
  safety_standards: string
  accessories_included: string | null
  warranty_terms: string | null
  expected_delivery_weeks: number | null
  installation_requirements: string | null
  training_requirements: string | null
  reference_standard: string | null
  reviewed_by: string | null
  review_date: string | null
  review_notes: string | null
  procurement_method: string | null
  required_by_date: string | null
  delivery_location: string | null
  reference_price_estimate: number | null
  site_requirements: string | null
  lifetime_support_requirements: string | null
  device_evaluation_ref: string | null
}

export interface TechnicalSpecListItem {
  name: string
  equipment_description: string
  regulatory_class: string
  needs_assessment: string
  status: string
  creation: string
}

export interface TechnicalSpecListResult {
  items: TechnicalSpecListItem[]
  total: number
  page: number
}

export async function createTechnicalSpec(params: {
  equipment_description: string
  performance_requirements?: string
  safety_standards?: string
  regulatory_class: string
  needs_assessment?: string
  device_model?: string
  mdd_class?: string
  accessories_included?: string
  warranty_terms?: string
  expected_delivery_weeks?: number
  installation_requirements?: string
  training_requirements?: string
  reference_standard?: string
  procurement_method?: string
  required_by_date?: string
  delivery_location?: string
  reference_price_estimate?: number
  site_requirements?: string
  lifetime_support_requirements?: string
  device_evaluation_ref?: string
}): Promise<TechnicalSpecDoc> {
  return frappePost(`${BASE}.create_technical_spec`, params as Record<string, unknown>)
}

export async function getTechnicalSpec(name: string): Promise<TechnicalSpecDoc> {
  return frappeGet<TechnicalSpecDoc>(`${BASE}.get_technical_spec`, { name })
}

export async function listTechnicalSpecs(params: {
  status?: string
  year?: string
  regulatory_class?: string
  page?: number
  page_size?: number
}): Promise<TechnicalSpecListResult> {
  return frappeGet<TechnicalSpecListResult>(
    `${BASE}.list_technical_specs`,
    params as Record<string, unknown>,
  )
}

export async function submitTsForReview(
  name: string,
  approver: string,
): Promise<{ name: string; status: string }> {
  return frappePost(`${BASE}.submit_ts_for_review`, { name, approver })
}

export async function approveTechnicalSpec(
  name: string,
  review_notes?: string,
): Promise<{ name: string; status: string }> {
  return frappePost(`${BASE}.approve_technical_spec`, { name, notes: review_notes || '' })
}

export async function resubmitTechnicalSpec(
  name: string,
): Promise<{ name: string; status: string }> {
  return frappePost(`${BASE}.resubmit_technical_spec`, { name })
}

// ─── Vendor Evaluation ────────────────────────────────────────────────────────

export interface VendorEvaluationItem {
  name?: string
  vendor: string
  vendor_name?: string
  quoted_price?: number | null
  technical_score: number
  financial_score: number
  profile_score: number
  risk_score: number
  total_score?: number
  score_band?: string
  compliant_with_ts: 0 | 1
  has_nd98_registration: 0 | 1
  is_recommended?: 0 | 1
  notes?: string | null
  bid_compliant: 0 | 1
  quoted_delivery_weeks?: number | null
  offered_payment_terms?: string | null
}

export interface VendorEvaluationDoc {
  name: string
  linked_plan: string
  linked_technical_spec?: string | null
  evaluation_date: string
  status: string
  items: VendorEvaluationItem[]
  recommended_vendor?: string | null
  selection_justification?: string | null
  committee_members?: string | null
  tech_reviewed_by?: string | null
  tech_review_date?: string | null
  approved_by?: string | null
  approval_date?: string | null
  approver?: string | null
  bid_issue_date?: string | null
  bid_closing_date?: string | null
  bid_opening_date?: string | null
  bids_received_count?: number | null
  unsuccessful_vendor_notified?: 0 | 1
}

export interface VendorEvaluationListItem {
  name: string
  linked_plan: string
  linked_technical_spec?: string | null
  evaluation_date: string
  recommended_vendor?: string | null
  status: string
  creation: string
}

export interface VendorEvaluationListResult {
  items: VendorEvaluationListItem[]
  total: number
  page: number
}

export interface ApprovedVE {
  name: string
  linked_plan: string
  linked_technical_spec?: string | null
  recommended_vendor?: string | null
  evaluation_date: string
}

export interface LockedPlan {
  name: string
  plan_year: string
  approved_budget: number
}

export interface PpItem {
  name: string
  equipment_description: string
  quantity: number
  total_cost: number | null
  status?: string
  needs_assessment: string | null
  por_reference?: string | null
}

export interface PpItemsForPlan {
  items: PpItem[]
  total: number
  page: number
  page_size: number
}

export interface PpItemsForVe {
  linked_plan: string | null
  recommended_vendor: string | null
  quoted_price: number
  pp_items: PpItem[]
}

// ─── Purchase Order Request ───────────────────────────────────────────────────

export interface PurchaseOrderRequestDoc {
  name: string
  linked_plan_item?: string | null
  procurement_plan?: string | null
  linked_evaluation?: string | null
  linked_technical_spec?: string | null
  vendor: string
  vendor_name?: string | null
  status: string
  requires_director_approval: 0 | 1
  equipment_description: string
  quantity: number
  unit_price: number
  total_amount: number
  delivery_terms?: string | null
  payment_terms?: string | null
  expected_delivery_date?: string | null
  warranty_period_months?: number | null
  incoterms?: string | null
  payment_schedule_notes?: string | null
  waiver_reason?: string | null
  approved_by?: string | null
  approval_date?: string | null
  release_date?: string | null
  released_by?: string | null
  cancellation_reason?: string | null
  approver?: string | null
}

export interface PurchaseOrderRequestListItem {
  name: string
  equipment_description: string
  vendor: string
  vendor_name?: string | null
  total_amount: number
  requires_director_approval: 0 | 1
  status: string
  release_date?: string | null
  creation: string
}

export interface PurchaseOrderRequestListResult {
  items: PurchaseOrderRequestListItem[]
  total: number
  page: number
}

// ─── VE API Functions ─────────────────────────────────────────────────────────

const VE_BASE = '/api/method/assetcore.api.imm03'

export async function getLockedPlans(): Promise<LockedPlan[]> {
  return frappeGet(`${VE_BASE}.get_locked_plans`, {})
}

export async function createVendorEvaluation(params: {
  linked_plan: string
  evaluation_date?: string
  bid_issue_date?: string
  bid_closing_date?: string
  bid_opening_date?: string
  linked_technical_spec?: string
}): Promise<{ name: string; status: string }> {
  return frappePost(`${VE_BASE}.create_vendor_evaluation`, params as Record<string, unknown>)
}

export async function getVendorEvaluation(name: string): Promise<VendorEvaluationDoc> {
  return frappeGet<VendorEvaluationDoc>(`${VE_BASE}.get_vendor_evaluation`, { name })
}

export async function listVendorEvaluations(params: {
  status?: string
  year?: string
  page?: number
  page_size?: number
}): Promise<VendorEvaluationListResult> {
  return frappeGet<VendorEvaluationListResult>(`${VE_BASE}.list_vendor_evaluations`, params as Record<string, unknown>)
}

export async function addVendorToEvaluation(params: {
  ve_name: string
  vendor: string
  technical_score: number
  financial_score: number
  profile_score: number
  risk_score: number
  quoted_price?: number
  compliant_with_ts?: 0 | 1
  has_nd98_registration?: 0 | 1
  notes?: string
  bid_compliant?: 0 | 1
  quoted_delivery_weeks?: number
  offered_payment_terms?: string
}): Promise<VendorEvaluationDoc> {
  return frappePost(`${VE_BASE}.add_vendor_to_evaluation`, params as Record<string, unknown>)
}

export async function approveVeTechnical(name: string, notes?: string): Promise<{ name: string; status: string }> {
  return frappePost(`${VE_BASE}.approve_ve_technical`, { name, notes: notes || '' })
}

export async function approveVeFinancial(params: {
  name: string
  recommended_vendor: string
  selection_justification?: string
  committee_members?: string
}): Promise<{ name: string; status: string; recommended_vendor: string; created_pors: string[] }> {
  return frappePost(`${VE_BASE}.approve_ve_financial`, params as Record<string, unknown>)
}

export async function getPpItemsForPlan(
  plan_name: string,
  page = 1,
  page_size = 10,
): Promise<PpItemsForPlan> {
  return frappeGet(`${VE_BASE}.get_pp_items_for_plan`, { plan_name, page, page_size })
}

export async function getPpItemsForVe(ve_name: string): Promise<PpItemsForVe> {
  return frappeGet(`${VE_BASE}.get_pp_items_for_ve`, { ve_name })
}

export async function getApprovedVes(plan_name?: string): Promise<ApprovedVE[]> {
  return frappeGet(`${VE_BASE}.get_approved_ves`, { plan_name: plan_name || '' })
}

// ─── POR API Functions ────────────────────────────────────────────────────────

export async function createPurchaseOrderRequest(params: {
  linked_plan_item?: string
  linked_evaluation: string
  linked_technical_spec?: string
  vendor: string
  equipment_description: string
  quantity: number
  unit_price: number
  delivery_terms?: string
  payment_terms?: string
  expected_delivery_date?: string
  warranty_period_months?: number
  waiver_reason?: string
  incoterms?: string
  payment_schedule_notes?: string
}): Promise<{ name: string; status: string; total_amount: number; requires_director_approval: number }> {
  return frappePost(`${VE_BASE}.create_purchase_order_request`, params as Record<string, unknown>)
}

export async function getPurchaseOrderRequest(name: string): Promise<PurchaseOrderRequestDoc> {
  return frappeGet<PurchaseOrderRequestDoc>(`${VE_BASE}.get_purchase_order_request`, { name })
}

export async function listPurchaseOrderRequests(params: {
  status?: string
  year?: string
  page?: number
  page_size?: number
}): Promise<PurchaseOrderRequestListResult> {
  return frappeGet<PurchaseOrderRequestListResult>(`${VE_BASE}.list_purchase_order_requests`, params as Record<string, unknown>)
}

export async function submitPorForReview(name: string, approver: string): Promise<{ name: string; status: string }> {
  return frappePost(`${VE_BASE}.submit_por_for_review`, { name, approver })
}

export async function approvePor(name: string): Promise<{ name: string; status: string }> {
  return frappePost(`${VE_BASE}.approve_por`, { name })
}

export async function releasePor(name: string): Promise<{ name: string; status: string }> {
  return frappePost(`${VE_BASE}.release_por`, { name })
}

export async function confirmPorDelivery(name: string, delivery_notes?: string): Promise<{ name: string; status: string }> {
  return frappePost(`${VE_BASE}.confirm_por_delivery`, { name, delivery_notes: delivery_notes || '' })
}
