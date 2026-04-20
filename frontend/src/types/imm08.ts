export type PMStatus =
  | 'Open'
  | 'In Progress'
  | 'Pending–Device Busy'
  | 'Overdue'
  | 'Completed'
  | 'Halted–Major Failure'
  | 'Cancelled'

export type PMChecklistResult = 'Pass' | 'Fail–Minor' | 'Fail–Major' | 'N/A' | null

export interface PMKPIs {
  compliance_rate_pct: number
  total_scheduled: number
  completed_on_time: number
  overdue: number
  avg_days_late: number
}

export type { PMWorkOrder, ChecklistResult, PMCalendarEvent, PMDashboardStats, PMListResponse } from '@/api/imm08'
