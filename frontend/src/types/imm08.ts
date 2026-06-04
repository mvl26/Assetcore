export type PMStatus =
  | 'Open'
  | 'In Progress'
  | 'Pending–Device Busy'
  | 'Overdue'
  | 'Completed'
  | 'Halted–Major Failure'
  | 'Cancelled'

export type PMChecklistResult = 'Pass' | 'Fail–Minor' | 'Fail–Major' | 'N/A' | null

// SoT type cho KPI tile: KHÔNG khai báo lại shape ở đây (drift trap). Lấy thẳng
// từ PMDashboardStats['kpis'] (api/imm08.ts) — gồm compliance_rate_pct number|null
// + các field phạm-vi-tháng total_scheduled/overdue_in_month/pending_in_month
// (INV-PM-KPI-1..6). Cancelled bị loại khỏi mẫu Ở BE; FE chỉ render verbatim.
import type { PMDashboardStats } from '@/api/imm08'
export type PMKPIs = PMDashboardStats['kpis']

export type { PMWorkOrder, ChecklistResult, PMCalendarEvent, PMDashboardStats, PMListResponse } from '@/api/imm08'
