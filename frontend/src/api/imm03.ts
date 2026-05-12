// Copyright (c) 2026, AssetCore Team
// API — IMM-03 Vendor Eval & Procurement Decision

import { frappeGet, frappePost } from './helpers'
import type {
  EvalListItem, EvalDoc, AvlListItem, DecisionListItem, DecisionDoc,
  DashboardKpis, VendorQuotationLine, ProcurementMethod,
} from '@/types/imm03'

const BASE = '/api/method/assetcore.api.imm03'

// ─── Vendor Profile (BE-03-01) ────────────────────────────────────────────────

export interface VendorProfileListItem {
  name: string
  supplier_name?: string
  imm_avl_status?: string
  imm_avl_categories?: string
  imm_overall_score?: number
  imm_last_audit_date?: string
  imm_next_audit_date?: string
  cert_count?: number
  cert_expiring_soon?: number
}

export function listVendorProfiles(
  filters: Record<string, unknown> = {}, page = 1, page_size = 20,
): Promise<{ items: VendorProfileListItem[]; total: number; page: number; page_size: number }> {
  return frappeGet(`${BASE}.list_vendor_profiles`, {
    filters: JSON.stringify(filters), page, page_size,
  })
}

export function getVendorProfile(name: string): Promise<Record<string, unknown>> {
  return frappeGet(`${BASE}.get_vendor_profile`, { name })
}

export function createVendorProfile(payload: Record<string, unknown>):
    Promise<{ name: string; supplier: string }> {
  return frappePost(`${BASE}.create_vendor_profile`, {
    payload: JSON.stringify(payload),
  })
}

export function addVendorCert(
  supplier: string, cert_type: string, cert_number: string,
  issued_by = '', issued_date = '', expiry_date = '', attachment = '',
): Promise<{ cert_row: string; cert_type: string; status: string }> {
  return frappePost(`${BASE}.add_vendor_cert`, {
    supplier, cert_type, cert_number, issued_by, issued_date, expiry_date, attachment,
  })
}

// ─── Vendor Evaluation ────────────────────────────────────────────────────────

export function listEvaluations(filters: Record<string, unknown> = {}, page = 1, page_size = 20):
    Promise<{ items: EvalListItem[]; total: number }> {
  return frappeGet(`${BASE}.list_evaluations`, { filters: JSON.stringify(filters), page, page_size })
}
export function getEvaluation(name: string): Promise<EvalDoc> {
  return frappeGet(`${BASE}.get_evaluation`, { name })
}
export function createEvaluation(spec_ref: string, weighting_scheme: Record<string, unknown> = {}): Promise<{ name: string; workflow_state: string }> {
  return frappePost(`${BASE}.create_evaluation`, { spec_ref, weighting_scheme: JSON.stringify(weighting_scheme) })
}
export function addCandidate(name: string, supplier: string, sign_off_non_avl = ''): Promise<{ row_count: number; in_avl: 0 | 1; warning?: string | null }> {
  return frappePost(`${BASE}.add_candidate`, { name, supplier, sign_off_non_avl })
}
export function submitQuotations(name: string, quotations: VendorQuotationLine[]): Promise<{ quotations_count: number }> {
  return frappePost(`${BASE}.submit_quotations`, { name, quotations: JSON.stringify(quotations) })
}
export function scoreEvaluation(name: string, scorer_role: string, scores_by_supplier: Record<string, Record<string, number>>):
    Promise<{ weighted_scores: Record<string, number>; recommended: string }> {
  return frappePost(`${BASE}.score_evaluation`, {
    name, scorer_role, scores_by_supplier: JSON.stringify(scores_by_supplier),
  })
}
export function transitionEvalWorkflow(name: string, action: string): Promise<{ name: string; workflow_state: string; docstatus: number }> {
  return frappePost(`${BASE}.transition_eval_workflow`, { name, action })
}

// ─── AVL ──────────────────────────────────────────────────────────────────────

export function listAvl(filters: Record<string, unknown> = {}): Promise<{ items: AvlListItem[] }> {
  return frappeGet(`${BASE}.list_avl`, { filters: JSON.stringify(filters) })
}
export function getAvl(name: string): Promise<AvlListItem> {
  return frappeGet(`${BASE}.get_avl`, { name })
}
export function createAvlEntry(supplier: string, device_category: string, validity_years = 2, valid_from = ''):
    Promise<{ name: string; valid_to: string }> {
  return frappePost(`${BASE}.create_avl_entry`, { supplier, device_category, validity_years, valid_from })
}
export function approveAvl(name: string, approver: string, approval_doc = ''): Promise<{ name: string; workflow_state: string }> {
  return frappePost(`${BASE}.approve_avl`, { name, approver, approval_doc })
}
export function suspendAvl(name: string, suspension_reason: string): Promise<{ name: string; workflow_state: string }> {
  return frappePost(`${BASE}.suspend_avl`, { name, suspension_reason })
}

// ─── Procurement Decision ─────────────────────────────────────────────────────

export function listDecisions(filters: Record<string, unknown> = {}, page = 1, page_size = 20):
    Promise<{ items: DecisionListItem[]; total: number }> {
  return frappeGet(`${BASE}.list_decisions`, { filters: JSON.stringify(filters), page, page_size })
}
export function getDecision(name: string): Promise<DecisionDoc> {
  return frappeGet(`${BASE}.get_decision`, { name })
}
export function createDecision(evaluation_ref: string, procurement_method: ProcurementMethod, method_legal_basis = ''):
    Promise<{ name: string; workflow_state: string }> {
  return frappePost(`${BASE}.create_decision`, { evaluation_ref, procurement_method, method_legal_basis })
}
export function awardDecision(
  name: string, winner_supplier: string, awarded_price: number,
  funding_source: string, board_approver: string,
  contract_doc = '', remarks = '',
): Promise<{ name: string; workflow_state: string; ac_purchase_ref?: string; envelope_check_pct?: number }> {
  return frappePost(`${BASE}.award_decision`, {
    name, winner_supplier, awarded_price, funding_source, board_approver, contract_doc, remarks,
  })
}
export function recordContract(name: string, contract_no: string, contract_doc = '', signed_date = ''):
    Promise<{ name: string; workflow_state: string }> {
  return frappePost(`${BASE}.record_contract`, { name, contract_no, contract_doc, signed_date })
}
export function transitionDecisionWorkflow(name: string, action: string): Promise<{ name: string; workflow_state: string; docstatus: number }> {
  return frappePost(`${BASE}.transition_decision_workflow`, { name, action })
}

// ─── Dashboard & Scorecard ────────────────────────────────────────────────────

export function getDashboardKpis(): Promise<DashboardKpis> {
  return frappeGet(`${BASE}.dashboard_kpis`)
}

export function getVendorScorecard(supplier: string, year: number, quarter: number): Promise<unknown> {
  return frappeGet(`${BASE}.get_vendor_scorecard`, { supplier, year, quarter })
}
