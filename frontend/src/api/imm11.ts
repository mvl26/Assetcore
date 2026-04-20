// Copyright (c) 2026, AssetCore Team
// API client cho Module IMM-11 — Calibration

import { frappeGet, frappePost } from './helpers'

export interface CalibrationSchedule {
  name: string
  asset: string
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

export interface AssetCalibration {
  name: string
  asset: string
  device_model: string
  calibration_schedule: string | null
  calibration_type: 'External' | 'In-House'
  status: 'Scheduled' | 'Sent to Lab' | 'In Progress' | 'Certificate Received' | 'Passed' | 'Failed' | 'Conditionally Passed' | 'Cancelled'
  scheduled_date: string
  actual_date: string | null
  technician: string
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

export async function updateCalibration(name: string, data: Partial<AssetCalibration>) {
  return frappePost<{ name: string; status: string }>(`${BASE}.update_calibration`, { name, ...data } as Record<string, unknown>)
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
