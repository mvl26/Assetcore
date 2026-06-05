// Copyright (c) 2026, AssetCore Team — IMM-14 Giải nhiệm thiết bị (Decommission)
//
// API client cho cổng "Hồ sơ giải nhiệm" (Asset Decommission closure record).
// Naming contract khớp BE: path = `assetcore.api.imm14.<function_name>`
// (refer docs/imm-14/05_API_Specification.md §6 — MVP 2 endpoint CHỐT).
//
// frappeGet/frappePost ĐÃ unwrap envelope { message: { success, data } } và throw
// ApiError khi success=false → return type là Promise<T>, KHÔNG Promise<ApiResponse<T>>.
import { frappeGet, frappePost } from './helpers'

const BASE = '/api/method/assetcore.api.imm14'

/**
 * Phương thức xử lý thiết bị khi giải nhiệm (WHO §3.8 / NĐ98).
 * Union literal PHẢI khớp EXACT Select options của DocType `Asset Decommission`
 * (disposal_method). KHÔNG dùng `as any`.
 */
export type DisposalMethod =
  | 'Huỷ'
  | 'Điều chuyển/Donation'
  | 'Bán/Trade-in'
  | 'Lưu trữ'

/** Trạng thái workflow của hồ sơ giải nhiệm (mirror BE). */
export type DecommissionState = 'Draft' | 'Approved'

export interface DecommissionRecord {
  name: string
  asset: string
  disposal_method: DisposalMethod
  decommission_reason: string
  patient_data_sanitized: boolean
  responsible: string
  sanitization_note?: string
  workflow_state: DecommissionState
  docstatus: number
}

/** Payload tạo hồ sơ giải nhiệm — mirror body BE create_decommission. */
export interface CreateDecommissionPayload {
  asset: string
  disposal_method: DisposalMethod
  decommission_reason: string
  patient_data_sanitized: boolean
  responsible: string
  sanitization_note?: string
}

/** Response create_decommission (docstatus=0, asset GIỮ NGUYÊN lifecycle). */
export interface CreateDecommissionResult {
  name: string
  asset: string
  workflow_state: DecommissionState
  docstatus: number
}

/**
 * Response approve_decommission — sau khi duyệt, asset chuyển Decommissioned.
 * lifecycle_status trả về để FE refresh badge (qua label map, KHÔNG render raw EN).
 */
export interface ApproveDecommissionResult {
  name: string
  asset: string
  workflow_state: DecommissionState
  docstatus: number
  lifecycle_status: string
  decommissioned_on: string | null
}

/**
 * POST create_decommission — tạo hồ sơ giải nhiệm docstatus=0.
 * KHÔNG đổi lifecycle_status asset (chỉ tạo record).
 * Lỗi: BAD_STATE (asset đã Decommissioned), CONFLICT (đã có record active),
 * BUSINESS_RULE (thiếu/sai field bắt buộc), NOT_FOUND.
 */
export function createDecommission(
  payload: CreateDecommissionPayload,
): Promise<CreateDecommissionResult> {
  // BE nhận patient_data_sanitized: int (0/1) — gửi int rõ ràng thay vì boolean.
  return frappePost(`${BASE}.create_decommission`, {
    asset: payload.asset,
    disposal_method: payload.disposal_method,
    decommission_reason: payload.decommission_reason,
    patient_data_sanitized: payload.patient_data_sanitized ? 1 : 0,
    responsible: payload.responsible,
    sanitization_note: payload.sanitization_note ?? '',
  })
}

/**
 * POST approve_decommission — validate đủ field + submit (docstatus 0→1) →
 * hook gọi transition_asset_status(asset, Decommissioned). Atomic: nếu gate/NEG-09
 * raise → roll-back, lifecycle_status GIỮ NGUYÊN.
 * Lỗi: BUSINESS_RULE (sanitization gate C/D), BAD_STATE (NEG-09 / terminal).
 */
export function approveDecommission(name: string): Promise<ApproveDecommissionResult> {
  return frappePost(`${BASE}.approve_decommission`, { name })
}

/** GET get_decommission — lấy chi tiết hồ sơ giải nhiệm của 1 record. */
export function getDecommission(name: string): Promise<DecommissionRecord> {
  return frappeGet(`${BASE}.get_decommission`, { name })
}
