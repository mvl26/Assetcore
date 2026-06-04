// Copyright (c) 2026, AssetCore Team — IMM-14 cổng giải nhiệm (pure predicates)
//
// Tách logic quyết định của cổng "Hồ sơ giải nhiệm" ra hàm thuần để:
//   1. View (AssetDetailView) và test dùng CHUNG một nguồn (no drift).
//   2. RED-prove được bằng vitest mà không phải mount cả SFC.
//
// KHÔNG chứa I/O — chỉ logic mirror BE BR-14-W2-* (defense-in-depth FE-side; BE là SoT).
import type { DisposalMethod } from './imm14'

export const DECOM_REASON_MIN_LEN = 20

/** Risk class C/D (WHO §3.6) trên AC Asset = High/Critical → bắt buộc xác nhận PHI. */
export function requiresPatientDataConfirm(riskClassification?: string | null): boolean {
  return riskClassification === 'High' || riskClassification === 'Critical'
}

/**
 * Nút "Giải nhiệm thiết bị" có hiện không.
 * - hasAsset: đã load asset
 * - lifecycleStatus: đọc từ asset (KHÔNG hardcode 'Active') — chỉ ẩn khi terminal
 * - canDecommissionCap: capability Department Head (commissioning.submit) — cap có thật
 */
export function showDecommissionButton(
  hasAsset: boolean,
  lifecycleStatus: string | undefined,
  canDecommissionCap: boolean,
): boolean {
  if (!hasAsset) return false
  if (lifecycleStatus === 'Decommissioned') return false
  return canDecommissionCap
}

export interface DecomFormState {
  disposal_method: DisposalMethod | ''
  patient_data_sanitized: boolean
  decommission_reason: string
  responsible: string
  confirm_name: string
}

/**
 * Nút "Xác nhận giải nhiệm" trong modal có cho bấm không (mirror BE BR-14-W2-02..05).
 * - disposal_method bắt buộc
 * - reason ≥ DECOM_REASON_MIN_LEN ký tự (trim)
 * - responsible bắt buộc
 * - C/D → patient_data_sanitized BẮT BUỘC tick
 * - confirm_name phải khớp assetName (xác nhận 2 bước hành động không đảo ngược)
 */
export function canSubmitDecommission(
  form: DecomFormState,
  assetName: string,
  riskClassification?: string | null,
): boolean {
  if (!form.disposal_method) return false
  if (form.decommission_reason.trim().length < DECOM_REASON_MIN_LEN) return false
  if (!form.responsible) return false
  if (requiresPatientDataConfirm(riskClassification) && !form.patient_data_sanitized) return false
  if (form.confirm_name.trim() !== assetName.trim()) return false
  return true
}
