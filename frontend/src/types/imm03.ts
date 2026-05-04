// Copyright (c) 2026, AssetCore Team
// Types — IMM-03 Vendor Eval & Procurement Decision

export type EvalState = 'Draft' | 'Open RFQ' | 'Quotation Received' | 'Evaluated' | 'Cancelled'
export type DecisionState =
  | 'Draft' | 'Method Selected' | 'Negotiation' | 'Award Recommended'
  | 'Pending Approval' | 'Awarded' | 'Contract Signed' | 'PO Issued' | 'Cancelled'
export type AvlState = 'Draft' | 'Approved' | 'Conditional' | 'Suspended' | 'Expired'

export type ProcurementMethod =
  | 'Chỉ định thầu' | 'Chào hàng cạnh tranh' | 'Đấu thầu rộng rãi'
  | 'Mua sắm trực tiếp' | 'Mua sắm tập trung'

export interface VendorEvalCandidate {
  name?: string
  idx?: number
  supplier: string
  in_avl?: 0 | 1
  sign_off_non_avl?: string
  scores?: string  // JSON
  weighted_score?: number
  notes?: string
}

export interface VendorQuotationLine {
  name?: string; idx?: number
  candidate_supplier: string
  quotation_no?: string
  quotation_date?: string
  quotation_validity: string
  price: number
  currency?: string
  payment_terms?: string
  delivery_days?: number
  warranty_months?: number
  attachment?: string
}

export interface EvalListItem {
  name: string
  spec_ref: string
  draft_date: string
  workflow_state: EvalState
  recommended_candidate?: string
}

export interface EvalDoc {
  name?: string
  spec_ref: string
  draft_date: string
  weighting_scheme?: string
  candidates: VendorEvalCandidate[]
  quotations: VendorQuotationLine[]
  criteria: { group: string; criterion: string; weight_pct: number; scorer_role?: string }[]
  recommended_candidate?: string
  workflow_state?: EvalState
  docstatus?: 0 | 1 | 2
}

export interface AvlListItem {
  name: string
  supplier: string
  device_category: string
  workflow_state: AvlState
  valid_from: string
  valid_to: string
}

export interface DecisionListItem {
  name: string
  spec_ref: string
  winner_supplier?: string
  awarded_price?: number
  envelope_check_pct?: number
  workflow_state: DecisionState
  ac_purchase_ref?: string
  creation: string
}

export interface DecisionDoc extends DecisionListItem {
  evaluation_ref: string
  procurement_method?: ProcurementMethod
  method_legal_basis?: string
  plan_ref?: string
  plan_line?: string
  quantity?: number
  funding_source?: string
  funding_evidence?: string
  board_approver?: string
  contract_no?: string
  contract_doc?: string
  awarded_date?: string
}

export interface DashboardKpis {
  eval_states: Record<string, number>
  decision_states: Record<string, number>
  avl_active: number
  avl_expiring_30d: number
}
