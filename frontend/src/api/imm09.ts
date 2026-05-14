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
  asset_info?: Record<string, unknown>
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
  incident_report?: string
  source_pm_wo?: string
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
