// Copyright (c) 2026, AssetCore Team
// API client cho Module IMM-08 — Preventive Maintenance

import { frappeGet, frappePost, type ApiResponse } from './helpers'

export interface PMWorkOrder {
  name: string
  asset_ref: string
  asset_name: string
  asset_category: string
  risk_class: string
  pm_type: string
  wo_type: 'Preventive' | 'Corrective'
  status: 'Open' | 'In Progress' | 'Pending–Device Busy' | 'Overdue' | 'Completed' | 'Halted–Major Failure' | 'Cancelled'
  due_date: string | null
  scheduled_date: string | null
  completion_date: string | null
  assigned_to: string | null
  overall_result: 'Pass' | 'Pass with Minor Issues' | 'Fail' | null
  technician_notes: string
  pm_sticker_attached: boolean
  is_late: boolean
  duration_minutes: number | null
  source_pm_wo: string | null
  checklist_results: ChecklistResult[]
}

export interface ChecklistResult {
  idx: number
  checklist_item_idx: number
  description: string
  measurement_type: 'Pass/Fail' | 'Numeric' | 'Text'
  unit: string
  result: 'Pass' | 'Fail–Minor' | 'Fail–Major' | 'N/A' | null
  measured_value: number | null
  notes: string
  photo: string | null
}

export interface PMCalendarEvent {
  name: string
  asset_ref: string
  asset_name: string
  pm_type: string
  due_date: string
  status: string
  assigned_to: string | null
  is_late: boolean
}

export interface PMDashboardStats {
  kpis: {
    compliance_rate_pct: number
    total_scheduled: number
    completed_on_time: number
    overdue: number
    avg_days_late: number
  }
  trend_6months: Array<{
    month: string
    total: number
    on_time: number
    rate: number
  }>
}

export interface PMListResponse {
  data: PMWorkOrder[]
  pagination: { page: number; page_size: number; total: number; total_pages: number }
}

const BASE = '/api/method/assetcore.api.imm08'

export async function listPMWorkOrders(filters = {}, page = 1, pageSize = 20): Promise<PMListResponse> {
  const res = await frappeGet<ApiResponse<PMListResponse>>(`${BASE}.list_pm_work_orders`, {
    filters: JSON.stringify(filters),
    page,
    page_size: pageSize,
  })
  return res.data
}

export async function getPMWorkOrder(name: string): Promise<PMWorkOrder> {
  const res = await frappeGet<ApiResponse<PMWorkOrder>>(`${BASE}.get_pm_work_order`, { name })
  return res.data
}

export async function assignTechnician(
  name: string,
  technician: string,
  scheduledDate?: string,
): Promise<{ name: string; status: string }> {
  const res = await frappePost<ApiResponse<{ name: string; status: string }>>(
    `${BASE}.assign_technician`,
    { name, technician, scheduled_date: scheduledDate },
  )
  return res.data
}

export async function submitPMResult(payload: {
  name: string
  checklist_results: ChecklistResult[]
  overall_result: string
  technician_notes: string
  pm_sticker_attached: boolean
  duration_minutes: number
}): Promise<{ name: string; new_status: string; is_late: boolean; next_pm_date: string; cm_wo_created: string | null }> {
  const res = await frappePost<ApiResponse<{ name: string; new_status: string; is_late: boolean; next_pm_date: string; cm_wo_created: string | null }>>(
    `${BASE}.submit_pm_result`,
    {
      ...payload,
      checklist_results: JSON.stringify(payload.checklist_results),
      pm_sticker_attached: payload.pm_sticker_attached ? 1 : 0,
    },
  )
  return res.data
}

export async function reportMajorFailure(
  pmWoName: string,
  failureDescription: string,
): Promise<{ pm_wo: string; cm_wo_created: string; asset_status: string }> {
  const res = await frappePost<ApiResponse<{ pm_wo: string; cm_wo_created: string; asset_status: string }>>(
    `${BASE}.report_major_failure`,
    { pm_wo_name: pmWoName, failure_description: failureDescription },
  )
  return res.data
}

export async function getPMCalendar(
  year: number,
  month: number,
  assetRef?: string,
): Promise<{
  month: string
  events: PMCalendarEvent[]
  summary: { total: number; completed: number; overdue: number; pending: number }
}> {
  const res = await frappeGet<ApiResponse<{
    month: string
    events: PMCalendarEvent[]
    summary: { total: number; completed: number; overdue: number; pending: number }
  }>>(`${BASE}.get_pm_calendar`, { year, month, asset_ref: assetRef })
  return res.data
}

export async function getPMDashboardStats(year?: number, month?: number): Promise<PMDashboardStats> {
  const res = await frappeGet<ApiResponse<PMDashboardStats>>(`${BASE}.get_pm_dashboard_stats`, { year, month })
  return res.data
}

export async function reschedulePM(
  name: string,
  newDate: string,
  reason: string,
): Promise<{ name: string; old_date: string; new_date: string }> {
  const res = await frappePost<ApiResponse<{ name: string; old_date: string; new_date: string }>>(
    `${BASE}.reschedule_pm`,
    { name, new_date: newDate, reason },
  )
  return res.data
}

export async function getAssetPMHistory(
  assetRef: string,
  limit = 10,
): Promise<{ asset_ref: string; total: number; history: PMWorkOrder[] }> {
  const res = await frappeGet<ApiResponse<{ asset_ref: string; total: number; history: PMWorkOrder[] }>>(
    `${BASE}.get_asset_pm_history`,
    { asset_ref: assetRef, limit },
  )
  return res.data
}
