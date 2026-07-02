// Copyright (c) 2026, AssetCore Team
// API client cho Module IMM-09 — Corrective Maintenance

import { frappeGet, frappePost } from './helpers'

export interface AssetRepair {
  name: string
  asset_ref: string
  asset_name: string
  asset_category: string
  risk_class: string
  department_name?: string
  location_name?: string
  asset_info?: AssetInfo
  serial_no: string
  repair_type: 'Corrective' | 'Breakdown' | 'Warranty Repair'
  priority: 'Normal' | 'Urgent' | 'Emergency'
  status: 'Open' | 'Assigned' | 'Diagnosing' | 'Pending Parts' | 'In Repair' | 'Pending Inspection' | 'Completed' | 'Cannot Repair' | 'Cancelled'
  open_datetime: string | null
  assigned_datetime: string | null
  completion_datetime: string | null
  assigned_to: string | null
  assigned_to_name?: string | null
  assigned_by: string | null
  mttr_hours: number | null
  sla_target_hours: number | null
  sla_breached: boolean
  /**
   * BR-09-10 / INV-CM-HOLD — đồng hồ SLA/MTTR DỪNG khi WO nằm 'Pending Parts'
   * (chờ phụ tùng hết kho — blocker cung ứng ngoài tầm đội sửa). BE là SoT:
   * `repair_elapsed_hours = (until − open) − parts_hold_hours`. FE chỉ RENDER
   * verbatim (KHÔNG tự tính lại): `mttr_hours` ở trên đã = elapsed-trừ-hold do BE chốt.
   *
   * `parts_hold_hours`   = tổng số giờ WO đã nằm Pending Parts (cộng dồn mọi chu kỳ hold).
   * `parts_hold_started` = mốc VÀO Pending Parts của chu kỳ hold đang mở (null nếu không hold).
   *
   * Cả 2 read-only + optional (forward-compat: trước khi BE enrich → undefined,
   * badge "Chờ phụ tùng — SLA tạm dừng" vẫn render vì gate theo `status`, KHÔNG vỡ).
   */
  parts_hold_hours?: number
  parts_hold_started?: string | null
  /**
   * Live-truth vượt SLA (BR-09-07 LIVE) — BE `list_repair_work_orders` enrich
   * per-row: `bool(sla_breached) || _row_is_live_overdue(open & vượt hạn & cờ chưa stamp)`.
   * Badge/computed đọc `is_sla_breached ?? sla_breached` (live ưu tiên, fallback cờ thô —
   * forward-compat: trước khi BE enrich, undefined → fallback cờ thô, KHÔNG vỡ). Optional.
   */
  is_sla_breached?: boolean
  is_repeat_failure: boolean
  incident_report: string | null
  source_pm_wo: string | null
  diagnosis_notes: string
  root_cause_category: string
  repair_summary: string
  firmware_updated: boolean
  firmware_change_request: string | null
  dept_head_name: string
  total_parts_cost: number
  spare_parts_used: SparePartRow[]
  repair_checklist: RepairChecklistRow[]
  /**
   * SSoT server-driven CTA (GATE-8 / LL-FE-51): danh sách trạng thái-đích hợp lệ
   * kế tiếp mà BE cho phép, do `get_repair_work_order` emit =
   * `_REPAIR_VALID_TRANSITIONS.get(status, [])` (imm09.py:778). FE gate nút workflow
   * bằng `capability && allowed_transitions.includes('<đích>')` — KHÔNG tự suy diễn
   * theo `status === 'X'`. Terminal (Completed/Cannot Repair/Cancelled) → []. Optional
   * (forward-compat: trước khi BE enrich → undefined → 0 nút CTA, KHÔNG vỡ).
   */
  allowed_transitions?: string[]
}

/**
 * Snapshot thông tin tài sản kèm trong detail (`get_repair_work_order` → `asset_info`).
 * `lifecycle_status` = trạng thái vòng đời THỰC của AC Asset tại thời điểm fetch
 * (SoT do nhiều process quản: repair / calibration-fail / incident / decommission).
 * BR-09-09 / INV-09-RESTORE-1: sau khi đóng WO, `complete_repair` CHỈ đưa asset về
 * 'Active' khi trước đó là 'Under Repair' — nếu asset đang giữ hold governance khác
 * (vd 'Out of Service' do calib-fail/CAPA) thì WO=Completed NHƯNG asset KHÔNG về Active.
 * → FE PHẢI bind badge/banner theo giá trị THỰC này, KHÔNG hardcode 'Active'.
 */
export interface AssetInfo {
  asset_name?: string
  asset_category?: string
  lifecycle_status?: string
  risk_classification?: string
  manufacturer_sn?: string
  department?: string
  location?: string
  [key: string]: unknown
}

export interface SparePartRow {
  idx: number
  item_code: string
  item_name: string
  qty: number
  uom: string
  unit_cost: number
  total_cost: number
  stock_entry_ref: string
  notes: string
}

export interface RepairChecklistRow {
  idx: number
  test_description: string
  test_category: string
  expected_value: string
  measured_value: string
  result: 'Pass' | 'Fail' | 'N/A' | null
  notes: string
}

export interface RepairKPIs {
  kpis: {
    total_completed: number
    mttr_avg_hours: number
    sla_compliance_pct: number
    repeat_failure_count: number
    open_wos: number
  }
  root_cause_breakdown: Array<{ category: string; count: number }>
}

export interface RepairListResponse {
  data: AssetRepair[]
  pagination: { page: number; page_size: number; total: number; total_pages: number }
}

export interface MttrReport {
  mttr_avg: number
  first_fix_rate: number
  backlog_count: number
  cost_per_repair: number
  mttr_trend: Array<{ month: string; value: number }>
  backlog_by_dept: Array<{ dept: string; count: number }>
}

const BASE = '/api/method/assetcore.api.imm09'

export function listRepairWorkOrders(filters = {}, page = 1, pageSize = 20): Promise<RepairListResponse> {
  return frappeGet<RepairListResponse>(`${BASE}.list_repair_work_orders`, {
    filters: JSON.stringify(filters),
    page,
    page_size: pageSize,
  })
}

export function getRepairWorkOrder(name: string): Promise<AssetRepair> {
  return frappeGet<AssetRepair>(`${BASE}.get_repair_work_order`, { name })
}

export function assignTechnician(
  name: string,
  technician: string,
  priority?: string,
): Promise<{ name: string; status: string; assigned_to: string }> {
  return frappePost<{ name: string; status: string; assigned_to: string }>(
    `${BASE}.assign_technician`,
    { name, technician, priority },
  )
}

export function submitDiagnosis(
  name: string,
  diagnosisNotes: string,
  needsParts: boolean,
): Promise<{ name: string; status: string }> {
  return frappePost<{ name: string; status: string }>(
    `${BASE}.submit_diagnosis`,
    { name, diagnosis_notes: diagnosisNotes, needs_parts: needsParts ? 1 : 0 },
  )
}

export function closeWorkOrder(payload: {
  name: string
  repair_summary: string
  root_cause_category: string
  dept_head_name: string
  checklist_results: RepairChecklistRow[]
  cannot_repair?: boolean
  cannot_repair_reason?: string
}): Promise<{ name: string; status: string; mttr_hours: number; sla_breached: boolean }> {
  return frappePost<{ name: string; status: string; mttr_hours: number; sla_breached: boolean }>(
    `${BASE}.close_work_order`,
    {
      ...payload,
      checklist_results: JSON.stringify(payload.checklist_results),
      cannot_repair: payload.cannot_repair ? 1 : 0,
    },
  )
}

export function confirmInspection(
  name: string,
): Promise<{ name: string; status: string; mttr_hours: number; sla_breached: boolean }> {
  return frappePost<{ name: string; status: string; mttr_hours: number; sla_breached: boolean }>(
    `${BASE}.confirm_inspection`,
    { name },
  )
}

export function getRepairKPIs(year?: number, month?: number): Promise<RepairKPIs> {
  return frappeGet<RepairKPIs>(`${BASE}.get_repair_kpis`, { year, month })
}

export function getAssetRepairHistory(
  assetRef: string,
  limit = 10,
): Promise<{ asset_ref: string; history: AssetRepair[] }> {
  return frappeGet<{ asset_ref: string; history: AssetRepair[] }>(
    `${BASE}.get_asset_repair_history`,
    { asset_ref: assetRef, limit },
  )
}

export function createRepairWorkOrder(payload: {
  asset_ref: string
  repair_type: string
  priority: string
  failure_description: string
  /** Ảnh mô tả lỗi (file URL sau khi upload) — optional */
  fault_image?: string
  /** BR-09-01 đã nới — incident/PM giờ optional (standalone repair) */
  incident_report?: string
  source_pm_wo?: string
  sla_target_hours?: number
}): Promise<{ name: string; status: string; sla_target_hours: number }> {
  return frappePost<{ name: string; status: string; sla_target_hours: number }>(
    `${BASE}.create_repair_work_order`,
    payload,
  )
}

export function startRepair(name: string): Promise<{ name: string; status: string }> {
  return frappePost<{ name: string; status: string }>(
    `${BASE}.start_repair`,
    { name },
  )
}

export function requestSpareParts(
  name: string,
  parts: SparePartRow[],
): Promise<{ name: string; updated: number }> {
  return frappePost<{ name: string; updated: number }>(
    `${BASE}.request_spare_parts`,
    { name, parts: JSON.stringify(parts) },
  )
}

export function getMttrReport(year: number, month: number): Promise<MttrReport> {
  return frappeGet<MttrReport>(`${BASE}.get_mttr_report`, { year, month })
}

export async function searchSpareParts(query: string): Promise<SparePartRow[]> {
  const res = await frappeGet<SparePartRow[]>(`${BASE}.search_spare_parts`, { query })
  return res ?? []
}
