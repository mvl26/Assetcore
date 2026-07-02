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

/**
 * Trạng thái workflow của hồ sơ giải nhiệm (mirror BE DocType `Asset Decommission`
 * field `workflow_state` Select: Draft / Approved / Cancelled). Render qua
 * StatusBadge (translateStatus) — KHÔNG render raw EN ra UI.
 */
export type DecommissionState = 'Draft' | 'Approved' | 'Cancelled'

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

// ─── Danh sách "Biên bản giải nhiệm" (list_decommissions) ────────────────────

/**
 * 1 dòng trong bảng "Biên bản giải nhiệm" — mirror EXACT field BE
 * `list_decommissions` trả (services/imm14.py::_DECOM_LIST_FIELDS + enrich).
 * `responsible_name` = full_name (User) do BE enrich — KHÔNG rò email
 * (LL-FE-53 / user_source policy); có thể null nếu User không có full_name.
 */
export interface DecommissionRow {
  name: string
  asset: string
  asset_name_snapshot: string
  risk_classification_snapshot: string
  workflow_state: DecommissionState
  disposal_method: DisposalMethod
  decommissioned_on: string | null
  responsible: string
  responsible_name: string | null
}

/** Bộ lọc đo được cho list — khớp whitelist BE (_DECOM_FILTER_KEYS). */
export interface DecommissionListFilters {
  workflow_state?: DecommissionState | ''
  disposal_method?: DisposalMethod | ''
  asset?: string
}

/** Metadata phân trang (mirror utils/pagination.paginate). */
export interface DecommissionPagination {
  page: number
  page_size: number
  total: number
  total_pages: number
  offset?: number
}

/** Envelope {data, pagination} — mirror list_compliance_findings/imm16. */
export interface DecommissionListResult {
  data: DecommissionRow[]
  pagination: DecommissionPagination
}

/**
 * GET list_decommissions — danh sách hồ sơ giải nhiệm (read-only, RBAC-scoped).
 * BE áp DocPerm 'Asset Decommission' (KHÔNG ignore_permissions); user thiếu
 * decommission.read → 403 (axios redirect). Sort mặc định decommissioned_on desc
 * (fallback creation desc). `filters` gửi dạng JSON (frappeGet stringify hộ dict
 * lồng KHÔNG an toàn → tự JSON.stringify, khớp signature BE `filters: str`).
 */
export function listDecommissions(
  filters: DecommissionListFilters = {},
  page = 1,
  pageSize = 20,
): Promise<DecommissionListResult> {
  return frappeGet(`${BASE}.list_decommissions`, {
    filters: JSON.stringify(filters),
    page,
    page_size: pageSize,
  })
}
