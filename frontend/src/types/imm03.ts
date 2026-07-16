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
  supplier_name?: string
  in_avl?: 0 | 1
  sign_off_non_avl?: string
  scores?: string  // JSON
  weighted_score?: number
  notes?: string
}

export interface VendorQuotationLine {
  name?: string; idx?: number
  candidate_supplier: string
  candidate_supplier_name?: string
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
  vendor_name?: string
  tech_spec_ref_name?: string
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
  // INV-VE-TIE (§IV.7): BE đặt cờ khi ≥2 candidate đồng hạng nhất (cùng weighted_score
  // tối đa) ⇒ recommended_candidate rỗng. `tied_candidates` = CSV supplier (sorted asc).
  // FE chỉ ĐỌC verbatim 2 field này, KHÔNG tự tính tie từ điểm.
  has_top_tie?: 0 | 1
  tied_candidates?: string
  workflow_state?: EvalState
  docstatus?: 0 | 1 | 2
  // Server-driven CTA (GATE-8 / LL-FE-51): tập ACTION workflow hợp lệ cho state
  // hiện tại (SoT = BE `_EVAL_VALID_TRANSITIONS`, parity get_decision). FE gate nút
  // CTA theo tập này, KHÔNG hardcode client-map TRANSITIONS_BY_STATE. Optional: BE
  // cũ chưa reload → undefined → degrade an toàn (0 nút transition).
  allowed_transitions?: string[]
}

export interface AvlListItem {
  name: string
  supplier: string
  vendor_name?: string
  device_category: string
  device_category_name?: string
  workflow_state: AvlState
  valid_from: string
  valid_to: string
  // Server-driven CTA (GATE-8 / LL-FE-51): tập ACTION workflow hợp lệ cho state
  // hiện tại — SoT = BE `_AVL_VALID_TRANSITIONS` (parity get_decision/get_evaluation),
  // đã LỌC theo capability/role của caller. FE gate nút Phê duyệt / Đình chỉ /
  // Phục hồi Approved theo tập này — KHÔNG hardcode `workflow_state === 'X'`.
  // Optional: BE cũ chưa reload → undefined → degrade an toàn (0 nút, không dead-control).
  allowed_transitions?: string[]
}

export interface DecisionListItem {
  name: string
  spec_ref: string
  winner_supplier?: string
  winner_supplier_name?: string
  vendor_name?: string
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
  // Server-driven CTA (GATE-8 / LL-FE-51): tập ACTION workflow hợp lệ cho state
  // hiện tại (SoT = BE `_DECISION_VALID_TRANSITIONS`). FE gate nút theo tập này,
  // KHÔNG hardcode `workflow_state === 'X'`. Optional: BE cũ chưa reload → undefined.
  allowed_transitions?: string[]
}

export interface DashboardKpis {
  eval_states: Record<string, number>
  decision_states: Record<string, number>
  avl_active: number
  avl_expiring_30d: number
}
