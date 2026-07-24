// Copyright (c) 2026, AssetCore Team
// API client cho Module IMM-11 — Calibration

import { frappeGet, frappePost } from './helpers'

export interface CalibrationSchedule {
  name: string
  asset: string
  asset_name?: string
  device_model: string
  calibration_type: 'External' | 'In-House'
  interval_days: number
  last_calibration_date: string | null
  next_due_date: string | null
  preferred_lab: string | null
  is_active: 0 | 1
}

export interface CalibrationMeasurement {
  idx?: number
  parameter_name: string
  unit: string
  nominal_value: number
  tolerance_positive: number
  tolerance_negative: number
  measured_value: number | null
  out_of_tolerance?: 0 | 1
  pass_fail?: 'Pass' | 'Fail' | null
}

/**
 * Raw measurement fields KTV nhập — tập DUY NHẤT được gửi lên BE khi lưu phiếu.
 * `pass_fail` / `out_of_tolerance` do SERVER tính (SSoT = controller cha
 * `_compute_measurement_results`, imm_asset_calibration.py) → FE KHÔNG BAO GIỜ gửi
 * hai field này (không tin payload client), chỉ render lại sau khi reload. Dùng
 * `Pick` để lệ thuộc DUY NHẤT nguồn field CalibrationMeasurement.
 */
export type CalibrationMeasurementInput = Pick<
  CalibrationMeasurement,
  'parameter_name' | 'unit' | 'nominal_value'
  | 'tolerance_positive' | 'tolerance_negative' | 'measured_value'
>

/**
 * Patch cho update_calibration — CHỈ field scalar editable (mirror BE
 * `_UPDATE_ALLOWED`) + `measurements` child-diff (raw-only). CÓ key `measurements`
 * ⇒ BE replace-set theo parameter_name/idx + tính lại pass_fail server-side;
 * VẮNG key ⇒ backward-compat scalar-only (hành vi cũ, 0 regression caller cũ).
 * Transport: `updateCalibration` JSON.stringify `measurements` theo convention
 * imm08/imm09 (BE `parse_json`).
 */
export interface CalibrationUpdatePatch {
  status?: AssetCalibration['status']
  actual_date?: string | null
  lab_supplier?: string | null
  lab_accreditation_number?: string | null
  lab_contract_ref?: string | null
  sent_date?: string | null
  certificate_number?: string | null
  certificate_date?: string | null
  reference_standard_serial?: string | null
  traceability_reference?: string | null
  technician_notes?: string | null
  amendment_reason?: string | null
  measurements?: CalibrationMeasurementInput[]
}

export interface AssetCalibration {
  name: string
  asset: string
  asset_name?: string
  device_model: string
  calibration_schedule: string | null
  calibration_type: 'External' | 'In-House'
  status: 'Scheduled' | 'Sent to Lab' | 'In Progress' | 'Certificate Received' | 'Passed' | 'Failed' | 'Conditionally Passed' | 'Cancelled'
  scheduled_date: string
  actual_date: string | null
  technician: string
  technician_name?: string
  assigned_by: string | null
  lab_supplier: string | null
  lab_accreditation_number: string | null
  lab_contract_ref: string | null
  sent_date: string | null
  sent_by: string | null
  certificate_file: string | null
  certificate_date: string | null
  certificate_number: string | null
  next_calibration_date: string | null
  overall_result: 'Passed' | 'Failed' | 'Conditionally Passed' | null
  reference_standard_serial: string | null
  traceability_reference: string | null
  measurements: CalibrationMeasurement[]
  pm_work_order: string | null
  capa_record: string | null
  is_recalibration: 0 | 1
  calibration_sticker_attached: 0 | 1
  sticker_photo: string | null
  technician_notes: string | null
  amendment_reason: string | null
  docstatus?: 0 | 1 | 2
  // SoT server-driven CTA: tập trạng-thái-kế hợp lệ per status từ BE
  // (_CAL_VALID_TRANSITIONS, imm11.py:1033). FE gate nút workflow theo list này —
  // KHÔNG hardcode status→button client-side (anti-pattern dead-gate/flow-drift).
  allowed_transitions?: string[]
  // Cờ hạn hiệu chuẩn derive SERVER-SIDE (CR-02 · server-flag SSoT). list_calibrations
  // + get_calibration emit is_overdue/is_due_soon (int 0/1) qua CHUNG helper BE
  // is_calibration_overdue / is_calibration_due_soon (services/imm11.py). Consumer CHỈ
  // render cờ (calFlagBadge), KHÔNG so next_calibration_date với client-clock. Overdue
  // ưu tiên due_soon; None/chưa-có-hạn → cả hai 0. INV parity list==detail (INV-SLA-5).
  is_overdue?: 0 | 1
  is_due_soon?: 0 | 1
}

export interface CalibrationKpis {
  kpis: {
    total_this_month: number
    completed: number
    failed: number
    pass_rate_pct: number
    overdue_assets: number
    due_soon_assets: number
  }
}

const BASE = '/api/method/assetcore.api.imm11'

export async function listCalibrationSchedules(filters = {}, page = 1, pageSize = 20) {
  // Tier 2 service trả {data, pagination}
  return frappeGet<{ data: CalibrationSchedule[]; pagination: Record<string, number> }>(
    `${BASE}.list_calibration_schedules`, { filters: JSON.stringify(filters), page, page_size: pageSize },
  )
}

export async function getCalibrationSchedule(name: string) {
  return frappeGet<CalibrationSchedule>(`${BASE}.get_calibration_schedule`, { name })
}

export async function createCalibrationSchedule(payload: Partial<CalibrationSchedule>) {
  return frappePost<{ name: string; next_due_date: string }>(`${BASE}.create_calibration_schedule`, payload as Record<string, unknown>)
}

export async function updateCalibrationSchedule(name: string, data: Partial<CalibrationSchedule>) {
  return frappePost<{ name: string }>(`${BASE}.update_calibration_schedule`, { name, ...data } as Record<string, unknown>)
}

export async function deleteCalibrationSchedule(name: string) {
  return frappePost<{ name: string; deleted: boolean }>(`${BASE}.delete_calibration_schedule`, { name })
}

export async function listCalibrations(filters = {}, page = 1, pageSize = 20) {
  // Tier 2 service trả {data, pagination}
  return frappeGet<{ data: AssetCalibration[]; pagination: Record<string, number> }>(
    `${BASE}.list_calibrations`, { filters: JSON.stringify(filters), page, page_size: pageSize },
  )
}

export async function getCalibration(name: string) {
  return frappeGet<AssetCalibration>(`${BASE}.get_calibration`, { name })
}

export async function createCalibration(payload: {
  asset: string
  calibration_type: string
  scheduled_date: string
  technician: string
  calibration_schedule?: string
  lab_supplier?: string
  is_recalibration?: number
}) {
  return frappePost<{ name: string; status: string }>(`${BASE}.create_calibration`, payload as Record<string, unknown>)
}

export async function updateCalibration(name: string, data: CalibrationUpdatePatch) {
  // Serialize child-diff theo convention imm08/imm09: nested-array param = JSON string,
  // BE `parse_json`. CHỈ stringify khi CÓ key `measurements` ⇒ giữ backward-compat
  // (vắng key = scalar-only, không đụng bảng con) — caller scalar (vd doStartCal chỉ gửi
  // {status}) KHÔNG kèm `measurements`, đi đúng nhánh cũ.
  const body: Record<string, unknown> = { name, ...data }
  if (data.measurements !== undefined) {
    body.measurements = JSON.stringify(data.measurements)
  }
  return frappePost<{ name: string; status: string }>(`${BASE}.update_calibration`, body)
}

export async function submitCalibration(name: string) {
  return frappePost<{ name: string; status: string; overall_result: string; next_calibration_date: string }>(
    `${BASE}.submit_calibration`, { name },
  )
}

export async function getCalibrationKpis(year?: number, month?: number) {
  return frappeGet<CalibrationKpis>(`${BASE}.get_calibration_kpis`, { year, month })
}

export async function getAssetCalibrationHistory(asset: string, limit = 10) {
  return frappeGet<{ asset: string; history: AssetCalibration[] }>(
    `${BASE}.get_asset_calibration_history`, { asset, limit },
  )
}

export async function sendToLab(name: string, payload: {
  sent_date?: string; lab_supplier?: string; lab_contract_ref?: string
} = {}) {
  return frappePost<{ name: string; status: string; sent_date: string }>(
    `${BASE}.send_to_lab`, { name, ...payload } as Record<string, unknown>,
  )
}

export async function receiveCertificate(name: string, payload: {
  certificate_file: string
  certificate_number: string
  certificate_date: string
  traceability_reference?: string
  reference_standard_serial?: string
}) {
  return frappePost<{ name: string; status: string; certificate_number: string }>(
    `${BASE}.receive_certificate`, { name, ...payload } as Record<string, unknown>,
  )
}

export async function cancelCalibration(name: string, reason: string) {
  return frappePost<{ name: string; status: string }>(
    `${BASE}.cancel_calibration`, { name, reason },
  )
}

export interface DueCalibrationItem {
  name: string
  asset_name: string
  device_model: string
  location: string | null
  next_calibration_date: string | null
  calibration_status: string | null
  days_left: number | null
}

export async function getDueCalibrations(days = 30, limit = 50) {
  return frappeGet<{ items: DueCalibrationItem[]; threshold_days: number }>(
    `${BASE}.get_due_calibrations`, { days, limit },
  )
}
